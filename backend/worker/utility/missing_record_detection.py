import os
import sys
import click
import bz2
import time
import pytz
import smtplib
import logging.handlers
import logging
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from email.mime.text import MIMEText
from email.header import Header
from configparser import ConfigParser
from typing import Union

logger = logging.getLogger(__name__)
tz_tw = pytz.timezone('Asia/Taipei')


def rotator(source, dest):
    with open(source, 'rb') as f:
        with bz2.BZ2File(dest + '.bz2', 'w') as out:
            out.write(f.read())
    os.remove(source)


def logger_setting():
    """Configure logs"""
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s,ln %(lineno)d: %(' \
                 'message)s '
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
    log_dir = './log'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    formatter = logging.Formatter(LOG_FORMAT)
    handler = logging.handlers.TimedRotatingFileHandler(os.path.join(log_dir, "missing_record.log"), when="midnight",
                                                        backupCount=30)
    handler.setFormatter(formatter)
    handler.rotator = rotator
    logging.getLogger().addHandler(handler)


def db_url(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    dburl = config['DATABASE']['MASTER_URL']
    return dburl


def to_recipients(config_path: str) -> list:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    recipients = config['RECIPIENTS']['missing_record_cc'].split(',')
    return recipients


def ignore_detect_list(config_path: str) -> list:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    ignore_site_list = config['MISSING_RECORD']['ignore'].split(',')
    return ignore_site_list


def get_sender(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    sender = config['MAIL_SENDER']['artichoke']
    return sender


class MissingRecordDetection:
    def __init__(self, config_path: str, site_id: str, target_date: str, nday: int, rday: int, tolerance: int):
        self._db_url = db_url(config_path)
        self._recipients = to_recipients(config_path)
        self._ignore_detect_list = ignore_detect_list(config_path)
        self._sender = get_sender(config_path)
        self._site_id = site_id
        self._nday = nday
        self._rday = rday
        self._target_date = self._get_target_date(target_date, nday)
        self._tolerance = tolerance

    def detect_missing_record(self, is_debug=False):
        logger.info(f'Check {self._target_date} rawdata')
        df_sites = self._read_active_site_info()
        check_date = datetime.strptime(self._target_date, '%Y-%m-%d').weekday()
        is_weekend = datetime.strptime(self._target_date, '%Y-%m-%d').weekday() >= 5
        df_missing = pd.DataFrame(columns=['site_id', 'sname', 'sniffer', 'interval', 'during', 'l1_alerts', 'l2_alerts'])
        for sid, site in df_sites.iterrows():
            open_hour, open_dt, closed_hour, closed_dt = self._get_business_datetime(site, is_weekend)
            sname = site['sname']

            for sniffer in site['sniffer']:
                logger.info(f'Examine rawdata records: {sid}, {sniffer}')
                try:
                    sql = f"""SET session time zone 'Asia/Taipei'; 
                        SELECT distinct(extract(epoch from date_trunc('minute', rt)))::int as ts FROM public.rawdata_{sniffer} 
                        WHERE date_trunc('day',rt)='{self._target_date}' 
                        AND rt BETWEEN '{self._target_date} {open_hour}' and '{self._target_date} {closed_hour}'
                        """
                    logger.debug(sql)
                    df = pd.read_sql(con=self._db_url, sql=sql)

                    # Append timestamp of closed time
                    df = df.append({'ts': int(time.mktime(closed_dt.timetuple()))}, ignore_index=True)

                    # Insert timestamp of open time
                    df.loc[-1] = [int(time.mktime(open_dt.timetuple()))]
                    df.index = df.index + 1  # shifting index
                    df.sort_index(inplace=True)

                    df['diff'] = df.diff(1)
                    missing_records = []
                    for idx in df.query(f"diff > 60*{self._tolerance}").index:
                        missing_records.append((df.iloc[idx - 1, 0], df.iloc[idx, 0]))

                    alerts = self._alert_level_count(sniffer)

                    df_write = pd.DataFrame(columns=['site_id', 'sname', 'sniffer', 'interval', 'during', 'l1_alerts', 'l2_alerts'])
                    for x in missing_records:
                        start_time = datetime.fromtimestamp(x[0]).strftime('%Y-%m-%d %H:%M:%S')
                        end_time = datetime.fromtimestamp(x[1]).strftime('%Y-%m-%d %H:%M:%S')
                        logger.info(f'Missing record found at {x[0]}, {start_time}')
                        df_write = df_write.append({
                            'site_id': sid,
                            'sname': sname,
                            'sniffer': sniffer,
                            'interval': time.strftime("%H:%M:%S", time.gmtime(int(x[1] - x[0]))),
                            'during': f'[{start_time},{end_time})',
                            'l1_alerts': alerts.get('L1', 'NA'),
                            'l2_alerts': alerts.get('L2', 'NA')
                        },
                            ignore_index=True)

                    #Dataframe to sql with UTC timezone
                    df_write_2 = pd.DataFrame(columns=['site_id', 'sname', 'sniffer', 'interval', 'during', 'l1_alerts', 'l2_alerts'])
                    for y in missing_records:
                        start_time_2 = datetime.fromtimestamp(y[0]).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        end_time_2 = datetime.fromtimestamp(y[1]).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        df_write_2 = df_write_2.append({
                            'site_id': sid,
                            'sname': sname,
                            'sniffer': sniffer,
                            'interval': time.strftime("%H:%M:%S", time.gmtime(int(y[1] - y[0]))),
                            'during': f'[{start_time_2},{end_time_2})',
                            'l1_alerts': alerts.get('L1', 'NA'),
                            'l2_alerts': alerts.get('L2', 'NA')
                        },
                            ignore_index=True)

                    if df_write.shape[0] > 0:
                        df_missing = df_missing.append(df_write)

                    if not is_debug:
                        if self._nday == 1:
                            df_write_2.to_sql(con=self._db_url, name='missing_record', if_exists='append', index=False)

                except Exception as e:
                    logger.warning(f'[{sid}] {sniffer}')
                    logger.exception(e)

        logger.debug(df_missing)
        if df_missing.shape[0] > 0:
            df_html_output = df_missing.sort_values(by='site_id').to_html(na_rep="", index=False).replace("\\n", "<br>")
            self._send_edt_alert_mail(f'[Artichoke] Missing Record {self._target_date}', df_html_output)
        else:
            pass
            self._send_edt_alert_mail(f'[Artichoke] Missing Record {self._target_date}', "資料都上傳了，有乖有乖")
        if check_date == 5:
            self.missing_record_weekly()

    def missing_record_weekly(self):
        end_date = datetime.strptime(self._target_date, '%Y-%m-%d').date() + timedelta(1)
        start_date = (end_date - timedelta(self._rday)).strftime("%Y-%m-%d")
        sql = f"""SET session time zone 'Asia/Taipei';
            SELECT site_id, sniffer, during, "interval", sname, l1_alerts, l2_alerts
            FROM public.missing_record
            Where interval >= '00:30:00'
            AND during && '[{start_date}, {end_date})'
            """
        df = pd.read_sql(con=self._db_url, sql=sql)
        df = df[~df['site_id'].str.contains('-area')]
        df = df.drop_duplicates(keep='last')
        df_html_output = df.sort_values(by='during').to_html(na_rep="", index=False).replace("\\n", "<br>")
        self._send_edt_alert_mail(f'[Artichoke] Missing Record Weekly {start_date} ~ {self._target_date}', df_html_output)

    @staticmethod
    def _get_target_date(target_date, nday: int) -> str:
        return (date.today() - timedelta(nday)).strftime("%Y-%m-%d") if not target_date else target_date

    def _get_business_datetime(self, site: pd.DataFrame, is_weekend: bool) -> [str, str, str, str]:
        open_hour = str(site['open_hour_wend']).split('+')[0] if is_weekend else str(site['open_hour']).split('+')[0]
        open_dt = datetime.strptime('{} {}'.format(self._target_date, open_hour), '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz_tw)
        closed_hour = str(site['closed_hour_wend']).split('+')[0] if is_weekend else \
            str(site['closed_hour']).split('+')[0]
        closed_dt = datetime.strptime(f"{self._target_date} {str(closed_hour)}", '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz_tw)
        return open_hour, open_dt, closed_hour, closed_dt

    def _alert_level_count(self, sniffer: str) -> dict:
        """level count of alert"""
        level = self._read_alert_severity_info()
        alert_content = {}
        for i in level:
            sql = f"""SET session time zone 'Asia/Taipei';
                SELECT distinct(extract(epoch from date_trunc('minute', alert_report_time)))::int
                FROM public.alert_record WHERE date_trunc('day', alert_report_time)='{self._target_date}'
                AND severity_id={i} AND sniffer_id = '{sniffer}'
                ORDER BY date_part ASC"""
            df = pd.read_sql(con=self._db_url, sql=sql)
            if df.empty:
                continue
            df.sort_index(inplace=True)
            df['diff'] = df.diff(1)
            result = []
            level_text = ""
            for idx in df.query("diff != 600 ").index:
                result.append([idx, df.iloc[idx, 0]])
            for idx, res in enumerate(result):
                alert_time = datetime.fromtimestamp(res[1]).strftime('%Y-%m-%d %H:%M:%S')
                if idx == len(result) - 1:
                    level_text += f'[{alert_time}, {len(df) - res[0]})'
                elif idx < len(result):
                    level_text += f'[{alert_time}, {result[idx + 1][0] - res[0]})' + '\n'
            alert_content[level[i]] = level_text
        return alert_content

    def _read_alert_severity_info(self) -> dict:
        sql = """SELECT * FROM public.alert_severity_info ORDER BY id ASC """
        data = pd.read_sql(sql=sql, con=self._db_url)
        data = data[['id', 'severity_name']].to_numpy()
        severity_dict = {}
        for idx, name in data:
            severity_dict[str(idx)] = name
        return severity_dict

    def _read_active_site_info(self) -> pd.DataFrame:
        sql = """
            SELECT si_i.site_id, si_i.sname, si_i.open_hour, si_i.closed_hour, si_i.open_hour_wend, si_i.closed_hour_wend, sn_i.sniffer_id AS sniffer
            FROM site_info AS si_i INNER JOIN (
                SELECT site_id, array_agg(sniffer_id) AS sniffer_id, array_agg(rssi) AS rssi FROM sniffer_info WHERE is_active GROUP BY site_id
            ) AS sn_i ON si_i.site_id = sn_i.site_id"""
        sql += f""" WHERE si_i.site_id not in ({", ".join([f"'{ignore_site}'" for ignore_site in self._ignore_detect_list])}) """
        if self._site_id:
            sql += f""" AND si_i.site_id='{self._site_id}' """
        data = pd.read_sql(sql=sql, con=self._db_url).set_index('site_id')
        return data

    def _send_edt_alert_mail(self, title, content) -> None:
        message = MIMEText(content, 'html', 'utf-8')
        message['Subject'] = Header(title, 'utf-8')
        message['To'] = ','.join(self._recipients)

        try:
            smtpObj = smtplib.SMTP('rs1.testritegroup.com')
            logger.info(f"message : {message}")
            smtpObj.sendmail(self._sender, self._recipients, message.as_string())
            logger.info("Successfully sent email")
        except smtplib.SMTPException:
            logger.info("Error: unable to send email")
            logger.info(f"Unexpected error:{sys.exc_info()[0]}")


def send_missing_record_email(
    config_path: str,
    site_id: Union[str, None],
    target_date: Union[str, None],
    nday: int,
    rday: int,
    tolerance: int,
    only_weekly: bool
):
    logger_setting()
    missing_record_detection = MissingRecordDetection(config_path, site_id, target_date, nday, rday, tolerance)
    if only_weekly:
        missing_record_detection.missing_record_weekly()
    else:
        missing_record_detection.detect_missing_record()


if __name__ == '__main__':
    @click.command()
    @click.option('--config_path', default='./config/artichoke_base_service.ini', help='artichoke_base_service.ini file path')
    @click.option('--site_id', help='Site ID')
    @click.option('--target_date', '--td', default=None, help='Target date with format YYYY-MM-DD. eg.2017-12-25')
    @click.option('--nday', '-n', default=1, help='n days ago. Default is yesterday.')
    @click.option('--rday', '-r', default=7, help='r days ago to target date. Default is 7 days')
    @click.option('--tolerance', '-t', default=5, help='Max. tolerance time of missing rawdata, with unit minutes')
    @click.option('--only_weekly', '-o', default=False, help='Only get missing record report in a range.')
    def run(config_path, site_id=None, nday=1, rday=7, target_date=None, tolerance=5, only_weekly=False, *args, **kwargs):
        logger_setting()
        missing_record_detection = MissingRecordDetection(config_path, site_id, target_date, nday, rday, tolerance)
        if only_weekly:
            missing_record_detection.missing_record_weekly()
        else:
            missing_record_detection.detect_missing_record()


    run()
