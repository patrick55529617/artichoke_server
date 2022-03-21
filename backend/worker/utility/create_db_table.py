import click
import datetime
import sqlalchemy
import pandas as pd
import sqlalchemy.exc
import logging.handlers
from sqlalchemy import create_engine
from configparser import ConfigParser
from typing import Union


LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s: %(message)s'
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
formatter = logging.Formatter(LOG_FORMAT)


def db_url(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    dburl = config['DATABASE']['MASTER_URL']
    return dburl


class CreateDBTable:
    def __init__(self, schema: str, sniffer: str, year: str, config_path: str):
        self._schema = schema
        self._year = year
        self._sniffer = sniffer
        self._engine = create_engine(db_url(config_path))

    def _get_site_info(self) -> pd.DataFrame:
        sql = f"""SELECT sniffer_id FROM {self._schema}.sniffer_info"""
        site_info = pd.read_sql(sql=sql, con=self._engine)
        return site_info

    def _create_base_rawdata_table(self):
        try:
            sql = f"""CREATE TABLE IF NOT EXISTS {self._schema}.rawdata
                            (
                                rt timestamp with time zone NOT NULL,
                                sa character(12) NOT NULL,
                                da character(12) NOT NULL,
                                rssi smallint NOT NULL,
                                seqno integer NOT NULL,
                                cname character varying(16) DEFAULT ''::character varying,
                                pkt_type smallint NOT NULL,
                                pkt_subtype smallint NOT NULL,
                                ssid character varying(32) DEFAULT ''::character varying,
                                channel smallint NOT NULL,
                                upload_time timestamp with time zone,
                                delivery_time timestamp with time zone,
                                sniffer character(12) COLLATE pg_catalog."default" NOT NULL
                            ) 
                            PARTITION BY LIST (sniffer);
                            """
            logger.info(sql)
            self._engine.execute(sql)
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.warning('[SQL Error] {}'.format(e))
        except Exception as e:
            logger.exception(e)

    def _create_rawdata_yearly_table(self, sniffer, year):
        try:
            next_year = int(year) + 1
            sql = f"""CREATE TABLE IF NOT EXISTS {self._schema}.rawdata_{sniffer}_{year} PARTITION OF {self._schema}.rawdata_{sniffer}
                    FOR VALUES FROM ('{year}-01-01 00:00:00+08') TO ('{next_year}-01-01 00:00:00+8')
                    PARTITION BY RANGE (rt);
                 """
            logger.info(sql)
            self._engine.execute(sql)
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.warning(f'[SQL Error] {e}')
        except Exception as e:
            logger.exception(e)

    def _create_rawdata_monthly_table(self, sniffer, year, month=1):
        try:
            next_month_year = int(year) if month != 12 else int(year) + 1
            next_month = month + 1 if month != 12 else 1
            sql = f"""CREATE TABLE IF NOT EXISTS {self._schema}.rawdata_{sniffer}_{year}_{month:02d} PARTITION OF {self._schema}.rawdata_{sniffer}_{year}
                    FOR VALUES FROM ('{year}-{month:02d}-01 00:00:00+08') TO ('{next_month_year}-{next_month:02d}-01 00:00:00+8'); 
                    ALTER TABLE {self._schema}.rawdata_{sniffer}_{year}_{month:02d} ADD PRIMARY KEY (rt);
                 """
            logger.info(sql)
            self._engine.execute(sql)
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.warning(f'[SQL Error] {e}')
        except Exception as e:
            logger.exception(e)

    def _create_rawdata_table(self, sniffer, year):
        try:
            # Craete rawdata base table
            self._create_base_rawdata_table()
            # Create sniffer partition
            sql = f"""CREATE TABLE IF NOT EXISTS {self._schema}.rawdata_{sniffer} PARTITION OF {self._schema}.rawdata
                    FOR VALUES IN ('{sniffer}')
                    PARTITION BY RANGE (rt);
                    """
            logger.info(sql)
            self._engine.execute(sql)
            # Create nested partition table
            self._create_rawdata_yearly_table(sniffer, year)
            for n in range(1, 13):
                logger.info('-------------------------------')
                logger.info(f'Create {self._year}-{n:02d} {self._schema}.rawdata table')
                self._create_rawdata_monthly_table(sniffer, year, month=n)
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.warning(f'[SQL Error] {e}')
        except Exception as e:
            logger.exception(e)

    def set_privilege(self):
        try:
            sql = '''GRANT SELECT ON ALL TABLES IN SCHEMA public TO dw, echoi;'''
            logger.info(sql)
            self._engine.execute(sql)
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.warning(f'[SQL Error] {e}')
        except Exception as e:
            logger.exception(e)
        return

    def main_proc(self):
        if self._sniffer is None:
            all_sniffer = self._get_site_info()['sniffer_id']
            for sniffer in all_sniffer:
                self._create_rawdata_table(sniffer=sniffer, year=self._year)
        else:
            self._create_rawdata_table(sniffer=self._sniffer, year=self._year)
        self.set_privilege()


def worker_create_db_table(config_path: str, sniffer: Union[str, None], year: Union[str, None]):
    """
    This function is used for worker call function.
    """
    schema = 'public'
    if year is None:
        month = datetime.datetime.now().month
        day = datetime.datetime.now().day
        if month == 12 and day > 28:
            year = (datetime.datetime.now() + datetime.timedelta(days=5)).year
        else:
            year = datetime.datetime.now().year
    create_db = CreateDBTable(schema=schema, sniffer=sniffer, year=year, config_path=config_path)
    create_db.main_proc()


if __name__ == '__main__':
    @click.command()
    @click.option('--sniffer', '-s', default=None, help='Sniffer mac(s) that used for wifi probe')
    @click.option('--year', '-y', help='Year of rawdata table to be created. ex."2021"')
    @click.option('--config_path', '-p', default='./config/artichoke_base_service.ini', help='config path')
    def main(sniffer=None, year=None, config_path='./config/artichoke_base_service.ini'):
        config = ConfigParser()
        config.read(config_path, encoding='UTF-8')
        schema = config['CREATE_DB_TABLE']['schema']
        if year is None:
            month = datetime.datetime.now().month
            day = datetime.datetime.now().day
            if month == 12 and day > 28:
                year = (datetime.datetime.now() + datetime.timedelta(days=5)).year
            else:
                year = datetime.datetime.now().year
        create_db = CreateDBTable(schema=schema, sniffer=sniffer, year=year, config_path=config_path)
        create_db.main_proc()


    main()
