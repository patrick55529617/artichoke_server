import pandas as pd
import sys
import click
import os.path
import logging.handlers
from datetime import date, timedelta, datetime
from os.path import basename
from configparser import ConfigParser
from sqlalchemy import create_engine
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

logger = logging.getLogger(__name__)


def db_url(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    dburl = config['DATABASE']['MASTER_URL']
    return dburl


def to_recipients(config_path: str) -> [dict, str]:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    recipients = config['RECIPIENTS']
    cc = config['RECIPIENTS']['daily_report_cc']
    return recipients, cc


def site_list(config_path: str) -> list:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    sites_status_list = config['SITE_REPORT']['sites_status_list']
    sites_status_list = sites_status_list.split(',')
    sites_status_daily_list = config['SITE_REPORT']['sites_status_daily_list']
    sites_status_daily_list = sites_status_daily_list.split(",")
    return sites_status_list, sites_status_daily_list


def get_site_info(site: str, config_path: str) -> str:
    engine = create_engine(db_url(config_path))
    sql = f"""SELECT site_id, sname FROM public.site_info WHERE site_id ~~ '{site}%%'"""
    site_name = engine.execute(sql).fetchall()
    site_in, site_out = site_name
    return site_in, site_out


def sites_dict(sites_list: list, config_path: str) -> list:
    dict_name = list()
    for site in sites_list:
        site_in, site_out = get_site_info(site, config_path)
        dict_name.append(
            {'site_id': {site_in[0]: site_in[1] + '-進店', site_out[0]: site_out[1]}, 'site_sid': site_in[0],
             'site_name': site_in[1]})
    return dict_name


class SendDailyReport:
    def __init__(self, config_path: str, nday: int, target_date=None):
        self._db_url = db_url(config_path)
        self._recipients, self._cc = to_recipients(config_path)
        self._iso_date = self._get_iso_date(target_date, nday)
        self._str_date = self._iso_date.replace('-', '')
        self.filedir = '/worker/daily_report'
        self.sender = 'artichoke@edt.testritegroup.com'
        self.sites_status_list, self.sites_status_daily_list = site_list(config_path)
        self.sites_status_list_dict = sites_dict(self.sites_status_list, config_path)
        self.sites_status_daily_list_dict = sites_dict(self.sites_status_daily_list, config_path)

    def main_proc(self):
        self._get_site_status_file()
        self._get_site_status_daily_file()
        self._send_daily_report()

    @staticmethod
    def _get_iso_date(target_date, nday: int) -> str:
        return (date.today() - timedelta(nday)).strftime("%Y-%m-%d") if not target_date else target_date

    def _get_site_status_file(self):
        for idx, site in enumerate(self.sites_status_list):
            try:
                df = self._get_site_stats(idx)
                writer = pd.ExcelWriter(os.path.join(self.filedir,
                                                     f"人流統計_{self._str_date}_{self.sites_status_list_dict[idx]['site_name']}.xlsx"),
                                        engine='xlsxwriter')
                df.to_excel(writer, sheet_name=self.sites_status_list_dict[idx]['site_name'], index=False,
                            columns=['date', 'site', 'hour', 'customers'])
                writer.save()
            except Exception as error:
                logger.error(f"_get_site_status_file error: {error}")
                continue

    def _get_site_status_daily_file(self):
        for idx, site in enumerate(self.sites_status_daily_list):
            try:
                iso_date = datetime.strptime(self._iso_date, "%Y-%m-%d").date()
                iso_start_date = datetime(iso_date.year, iso_date.month, 1).date()
                df = self._get_site_stats_daily(iso_start_date, idx)
                writer = pd.ExcelWriter(os.path.join(self.filedir,
                                                     f"人流統計_{self._str_date}_{self.sites_status_daily_list_dict[idx]['site_name']}.xlsx"),
                                        engine='xlsxwriter')
                df.to_excel(writer, sheet_name=self.sites_status_daily_list_dict[idx]['site_name'], index=False,
                            columns=['date', 'site', 'customers'])
                writer.save()
            except Exception as error:
                logger.error(f"get_site_status_daily_file error: {error}")
                pass

    def _send_daily_report(self):
        for idx, site in enumerate(self.sites_status_list):
            try:
                self._send_mail(title=f"人流統計日報 - {self.sites_status_list_dict[idx]['site_name']} {self._iso_date}",
                                content=f"人流統計日報 - {self.sites_status_list_dict[idx]['site_name']} {self._iso_date}",
                                to_recipients=list(
                                    self._recipients[self.sites_status_list_dict[idx]['site_sid']].split(',')),
                                cc_recipients=list(self._cc.split(",")),
                                files=[os.path.join(self.filedir,
                                                    f"人流統計_{self._str_date}_{self.sites_status_list_dict[idx]['site_name']}.xlsx")])
            except Exception as error:
                logger.error(f"send_daily_report sites_status error:{error}")
                continue
        for idx, site in enumerate(self.sites_status_daily_list):
            try:
                self._send_mail(
                    title=f"人流統計日報 - {self.sites_status_daily_list_dict[idx]['site_name']} {self._iso_date}",
                    content=f"人流統計日報 - {self.sites_status_daily_list_dict[idx]['site_name']} {self._iso_date}",
                    to_recipients=list(self._recipients[self.sites_status_daily_list_dict[idx]['site_sid']].split(',')),
                    cc_recipients=list(self._cc.split(",")),
                    files=[os.path.join(self.filedir,
                                        f"人流統計_{self._str_date}_{self.sites_status_daily_list_dict[idx]['site_name']}.xlsx")])
            except Exception as error:
                logger.error(f"send_daily_report sites_status_daily error:{error}")
                continue

    def _get_site_stats(self, idx, table='customer_count'):
        try:
            sites_dict = self.sites_status_list_dict[idx]['site_id']
            df_sites = self._read_site_info(sites_dict)
            logger.debug(df_sites)
            df_all = pd.DataFrame(columns=['date', 'site', 'hour', 'customers'])
            for sid in sites_dict:
                df = self._read_hourly_stats_from_table(table, sid)
                df['site'] = sites_dict[sid]
                df['date'] = self._iso_date
                df['hour'] = [x.hour for x in df['time'].dt.tz_convert('Asia/Taipei')]
                df_all = df_all.append(df.drop('time', axis=1))
            return df_all
        except Exception as error:
            logger.error(f"get_site_stats error: {error}")
            self._send_mail(title=f"[ERROR]Daily Report {sid} {sites_dict[sid]} {self._iso_date}",
                            content=f"{sid} _get_site_stats()：{error}",
                            to_recipients=list(self._cc.split(",")))

    def _read_site_info(self, sites):
        sql = """SELECT * FROM site_info """
        if sites is not None and len(sites) > 0:
            sql += f"""WHERE site_id in ('{"', '".join(sites)}') """
        sql += """ORDER BY site_id"""
        logger.debug(sql)
        data = pd.read_sql(sql=sql, con=self._db_url).set_index('site_id')
        return data

    def _read_hourly_stats_from_table(self, table: str, site_id: str) -> pd.DataFrame:
        sql = f"""
                SET SESSION time zone 'Asia/Taipei';
                SELECT date_trunc('hour', time) AS time, SUM (customers) AS customers
                FROM (
                    SELECT ts_hour AS time, count as customers
                    FROM {table}
                    WHERE site_id='{site_id}'
                    AND ts_hour BETWEEN '{self._iso_date} 00:00:00+08' and '{self._iso_date} 23:59:59+08'
                    UNION (SELECT generate_series(timestamp '{self._iso_date} 00:00:00+08', timestamp'{self._iso_date} 23:59:59+08', '1 hour') as date, 0)
                ) A
                JOIN site_info B
                ON B.site_id = '{site_id}'
                AND (
                    (NOT date_part('isodow', time) IN (6,7)
                     AND time::timetz >= B.open_hour
                     AND time::timetz < B.closed_hour
                    )
                    OR
                    (date_part('isodow', time) IN (6,7)
                     AND time::timetz >= B.open_hour_wend
                     AND time::timetz < B.closed_hour_wend
                    )
                )
                GROUP BY 1
                ORDER BY 1
                """
        logger.debug(sql)
        return pd.read_sql(sql=sql, con=self._db_url)

    def _get_site_stats_daily(self, iso_start_date, idx, table='customer_count'):
        try:
            sites_dict = self.sites_status_daily_list_dict[idx]['site_id']
            df_sites = self._read_site_info(sites_dict)
            logger.debug(df_sites)
            df_all = pd.DataFrame(columns=['date', 'site', 'customers'])
            for sid in sites_dict:
                df = self._read_daily_stats_from_table(table, iso_start_date, sid)
                df['site'] = sites_dict[sid]
                df['date'] = df['date'].dt.tz_convert('Asia/Taipei')
                df['date'] = df['date'].apply(lambda x: x.date())
                df_all = df_all.append(df)
            return df_all
        except Exception as error:
            logger.error(f"_get_site_stats_daily error: {error}")
            self._send_mail(title=f"[ERROR]Daily Report {sid} {sites_dict[sid]} {self._iso_date}",
                            content=f"{sid} _get_site_stats_daily()：{error}",
                            to_recipients=list(self._cc.split(",")))

    def _read_daily_stats_from_table(self, table, iso_start_date, site_id):
        sql = f"""
                SET SESSION time zone 'Asia/Taipei';
                WITH hour_people_count AS (
                    SELECT ts_hour, count as customers FROM {table}
                      WHERE site_id='{site_id}'
                      AND ts_hour BETWEEN '{iso_start_date} 00:00:00+08' and '{self._iso_date} 23:59:59+08'
                      UNION (SELECT generate_series(timestamptz '{iso_start_date}', timestamptz '{self._iso_date} 23:59:59+08', '1 hour') as date, 0)
                      ORDER BY ts_hour ASC
                )
                SELECT date_trunc('day',ts_hour) AS date, '{site_id}' as site, SUM(customers) AS customers
                FROM hour_people_count
                GROUP BY date_trunc('day',ts_hour)
                ORDER BY date_trunc('day',ts_hour)
              """
        logger.debug(sql)
        return pd.read_sql(sql=sql, con=self._db_url)

    def _send_mail(self, title, content, to_recipients, cc_recipients=[], files=[]):
        message_content = MIMEText(content, 'plain')
        message = MIMEMultipart()
        message['Subject'] = Header(title, 'utf-8')
        message['To'] = ','.join(to_recipients)
        message['Cc'] = ','.join(cc_recipients)
        message.attach(message_content)
        for filepath in files:
            with open(filepath, "rb") as file:
                part = MIMEApplication(
                    file.read(),
                    Name=basename(filepath)
                )
            # After the file is closed
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(filepath)
            message.attach(part)
        try:
            smtpObj = smtplib.SMTP('rs1.testritegroup.com')
            logger.info(f"sender : {self.sender}")
            logger.info(f"receivers : {to_recipients}")
            logger.info(f"cc_receivers : {cc_recipients}")
            # raise
            smtpObj.sendmail(self.sender, to_recipients + cc_recipients, message.as_string())
            smtpObj.close()
            logger.info("Successfully sent email")
        except smtplib.SMTPException:
            logger.info("Error: unable to send email")
            logger.info("Unexpected error:", sys.exc_info()[0])


def send_daily_report(config_path: str, nday: int, target_date: str):
    """
    This function is used for worker call function.
    """
    if not os.path.exists('log'):
        os.makedirs('log')
    if not os.path.exists('/worker/daily_report'):
        os.makedirs('/worker/daily_report')
    SendDailyReport(config_path, nday, target_date).main_proc()


if __name__ == '__main__':
    @click.command()
    @click.option('--config_path', default='./config/artichoke_base_service.ini',
                  help='artichoke_base_service.ini file path')
    @click.option('-t', '--target_date', help='target date, format: 2021-07-07')
    @click.option('-n', '--nday', default=1, help='calculate how many days', type=int)
    def main(nday=1, target_date=None, config_path='./config/artichoke_base_service.ini'):
        if not os.path.exists('log'):
            os.makedirs('log')
        daily_report = SendDailyReport(config_path, nday, target_date)
        daily_report.main_proc()


    main()
