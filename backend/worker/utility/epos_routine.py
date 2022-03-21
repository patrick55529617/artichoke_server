import pandas as pd
import os.path
import cx_Oracle
from datetime import date, timedelta
import click
import logging
import logging.handlers
from configparser import ConfigParser

logger = logging.getLogger(__name__)


def logger_setting():
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s: %(message)s'
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.handlers.RotatingFileHandler('log/daily.log', maxBytes=1024 * 1024, backupCount=2)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_url(config_path: str) -> [str, str]:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    db_url = config['DATABASE']['MASTER_URL']
    epos_url = config['EPOS']['EPOS_URL']
    return db_url, epos_url


def read_sites(config_path: str) -> [str, str]:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    sites_special = list(config['EPOS']['sites_special'].split(','))
    db_url = config['DATABASE']['MASTER_URL']
    sql = '''SELECT site_id FROM public.site_info WHERE is_released GROUP BY 1 ORDER BY 1;'''
    sites = pd.read_sql(sql, db_url).site_id.unique().tolist()
    return sites, sites_special


class EposRoutine:
    def __init__(self, config_path: str, nday: int, target_date=None, site_id=None):
        self._db_url, self._epos_url = get_url(config_path)
        self._sites, self._sites_special = read_sites(config_path)
        self._iso_date = self._get_iso_date(target_date, nday)
        self._site_id = site_id

    @staticmethod
    def _get_iso_date(target_date, nday: int) -> str:
        return (date.today() - timedelta(nday)).strftime("%Y-%m-%d") if not target_date else target_date

    def main_proc(self):
        self._write_epos_into_db()
        self._write_epos_daily_into_db()

    def _write_epos_into_db(self) -> None:
        try:
            logger.info(f'Query epos data {self._iso_date}')
            if not self._site_id:
                df = self._read_epos_hourly_from_db().append(
                    self._read_epos_hourly_from_db_exclude_parking(),
                    ignore_index=True
                )
            elif self._site_id in self._sites_special:
                df = self._read_epos_hourly_from_db_exclude_parking()
            else:
                df = self._read_epos_hourly_from_db()

            if df.empty:
                logger.warning('No epos data....')
                return
            df['TIME'] = [f'{self._iso_date} {x}:00:00+08' for x in df['TIME_HR']]
            df = df.drop('TIME_HR', axis=1)
            df = df.rename(str.lower, axis='columns')
            logger.debug(df)
            logger.info(f'Insert epos data by {df.shape}')
            df.to_sql(con=self._db_url, name='epos', if_exists='append', index=False)
        except Exception as e:
            logger.exception(e)

    def _write_epos_daily_into_db(self) -> None:
        try:
            logger.info(f'Query epos data {self._iso_date}')
            if not self._site_id:
                df = self._read_epos_daily_from_db().append(
                    self._read_epos_daily_from_db_exclude_parking(),
                    ignore_index=True
                )
            elif self._site_id in self._sites_special:
                df = self._read_epos_daily_from_db_exclude_parking()
            else:
                df = self._read_epos_daily_from_db()

            if df.empty:
                logger.warning('No epos data....')
                return
            df['sl_date'] = f'{self._iso_date} 00:00:00+08'

            logger.info(f'Insert epos_daily data by {df.shape}')
            df.to_sql(con=self._db_url, name='epos_daily', if_exists='append', index=False)
        except Exception as e:
            logger.exception(e)

    def _read_epos_hourly_from_db_exclude_parking(self) -> pd.DataFrame:
        try:
            conn = cx_Oracle.connect(self._epos_url)
            with conn:
                sql = f'''SELECT h.S_NO as site_id, (h.TIME_NO-1) as time_hr, COUNT(*) as count, SUM(h.SL_AMT) as amount, SUM(h.SL_QTY) as quantity 
                        from eposadmin.sale_h h join 
                        (select * from eposadmin.sale_d where RECNO=1) d on (h.SL_KEY=d.SL_KEY)
                        WHERE h.sl_date = to_date('{self._iso_date}', 'YYYY-MM-DD') 
                        AND h.sl_mode='1' AND h.sl_inkind='1' 
                        AND h.S_NO in ('{"','".join(self._sites_special) if not self._site_id else self._site_id}') 
                        AND not (d.P_CLASS1='027' and d.P_CLASS2='011') -- and h.SL_AMT<100)
                        group by h.S_NO, h.TIME_NO order by h.S_NO, h.TIME_NO asc
                      '''
                logger.info(sql)
                df = pd.read_sql(sql=sql, con=conn)
                logger.debug(f'Get {df.shape} data from epos db')
                return df
        except Exception as e:
            logger.exception(e)
        return pd.DataFrame()

    def _read_epos_hourly_from_db(self) -> pd.DataFrame:
        try:
            conn = cx_Oracle.connect(self._epos_url)
            with conn:
                sql = f'''SELECT S_NO as site_id, (TIME_NO-1) as time_hr, COUNT(*) as count, SUM(SL_AMT) as amount, SUM(SL_QTY) as quantity from eposadmin.sale_h 
                        WHERE sl_date = to_date('{self._iso_date}', 'YYYY-MM-DD') 
                        AND sl_mode='1' AND sl_inkind='1' 
                        AND S_NO in ('{"','".join(self._sites) if self._site_id is None else self._site_id}') 
                        group by S_NO, TIME_NO order by S_NO, TIME_NO asc
                      '''
                logger.info(sql)
                df = pd.read_sql(sql=sql, con=conn)
                logger.debug(f'Get {df.shape} data from epos db')
                return df
        except Exception as e:
            logger.exception(e)
        return pd.DataFrame()

    def _read_epos_daily_from_db_exclude_parking(self) -> pd.DataFrame:
        try:
            conn = cx_Oracle.connect(self._epos_url)
            with conn:
                sql = f'''SELECT h.S_NO as "site_id", h.SL_DATE as "sl_date", COUNT(*) as "count", 0 as "count_unique", SUM(h.SL_AMT) as "amount"
                        from eposadmin.sale_h h join 
                        (select * from eposadmin.sale_d where RECNO=1) d on (h.SL_KEY=d.SL_KEY)
                        WHERE h.sl_date = to_date('{self._iso_date}', 'YYYY-MM-DD') 
                        AND h.sl_mode='1' AND h.sl_inkind='1' 
                        AND h.S_NO in ('{"','".join(self._sites_special) if self._site_id is None else self._site_id}') 
                        AND not (d.P_CLASS1='027' and d.P_CLASS2='011') -- and h.SL_AMT<100)
                        group by h.S_NO, h.SL_DATE order by h.S_NO, h.SL_DATE asc
                      '''
                logger.info(sql)
                df = pd.read_sql(sql=sql, con=conn)
                logger.debug(f'Get {df.shape} data from epos db')

                sql = f'''SELECT h.S_NO as "site_id", h.SL_DATE as "sl_date", COUNT(*) as "tickets", count(Distinct(h.VIP_NO)) as "tickets_uni" 
                                    from eposadmin.sale_h h join 
                                    (select * from eposadmin.sale_d where RECNO=1) d on (h.SL_KEY=d.SL_KEY)
                                    WHERE h.sl_date = to_date('{self._iso_date}', 'YYYY-MM-DD') 
                                    AND h.sl_mode='1' AND h.sl_inkind='1' 
                                    AND h.S_NO in ('{"','".join(self._sites_special) if self._site_id is None else self._site_id}') 
                                    AND not (d.P_CLASS1='027' and d.P_CLASS2='011') -- and h.SL_AMT<100)
                                    AND not (C_CARD_NO = '05')
                                    group by h.S_NO, h.SL_DATE order by h.S_NO, h.SL_DATE asc
                                  '''
                logger.info(sql)
                df2 = pd.read_sql(sql=sql, con=conn)

                df['count_unique'] = df['count'] - (df2['tickets'] - df2['tickets_uni'])
                df['count_unique'].fillna(df['count'], inplace=True)
                return df
        except Exception as e:
            logger.exception(e)
        return pd.DataFrame()

    def _read_epos_daily_from_db(self) -> pd.DataFrame:
        try:
            conn = cx_Oracle.connect(self._epos_url)
            with conn:
                sql = f'''SELECT S_NO as "site_id", SL_DATE as "sl_date", COUNT(*) as "count", 0 as "count_unique", SUM(SL_AMT) as "amount" from eposadmin.sale_h 
                        WHERE sl_date = to_date('{self._iso_date}', 'YYYY-MM-DD') 
                        AND sl_mode='1' AND sl_inkind='1' 
                        AND S_NO in ('{"','".join(self._sites) if self._site_id is None else self._site_id}') 
                        group by S_NO, SL_DATE order by S_NO, SL_DATE asc
                      '''
                logger.info(sql)
                df = pd.read_sql(sql=sql, con=conn)
                logger.debug(f'Get {df.shape} data from epos db')

                sql = f'''SELECT S_NO as "site_id", SL_DATE as "sl_date", count(*) as "tickets", count(Distinct(VIP_NO)) as "tickets_uni" from eposadmin.sale_h
                                    WHERE sl_date = to_date('{self._iso_date}', 'YYYY-MM-DD')
                                    AND sl_mode='1' AND sl_inkind='1'
                                    AND S_NO in ('{"','".join(self._sites) if self._site_id is None else self._site_id}')
                                    AND not (C_CARD_NO = '05')
                                    group by S_NO, SL_DATE order by S_NO, SL_DATE asc
                                  '''
                logger.info(sql)
                df2 = pd.read_sql(sql=sql, con=conn)

                df['count_unique'] = df['count'] - (df2['tickets'] - df2['tickets_uni'])
                df['count_unique'].fillna(df['count'], inplace=True)
                return df
        except Exception as e:
            logger.exception(e)
        return pd.DataFrame()


def worker_run_epos_routine(config_path, nday, target_date, site_id):
    if not os.path.exists('log'):
        os.makedirs('log')
    logger_setting()
    EposRoutine(config_path=config_path, nday=nday, target_date=target_date, site_id=site_id).main_proc()


if __name__ == '__main__':
    @click.command()
    @click.option('--config_path', default='./config/artichoke_base_service.ini', help='artichoke_base_service.ini file path')
    @click.option('-n', '--nday', default=1, help='n days ago. Default is yesterday.')
    @click.option('-d', '--target_date', default=None, help='Target date with format YYYY-MM-DD. eg.2017-12-25')
    @click.option('-s', '--site_id', default=None)
    def main(nday=1, target_date=None, site_id=None, config_path='./config/artichoke_base_service.ini'):
        if not os.path.exists('log'):
            os.makedirs('log')
        logger_setting()
        epos_routine = EposRoutine(config_path=config_path, nday=nday, target_date=target_date, site_id=site_id)
        epos_routine.main_proc()

    main()
