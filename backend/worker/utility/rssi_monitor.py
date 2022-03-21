import logging.handlers
import os
import smtplib
import click
from datetime import date, timedelta, datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from configparser import ConfigParser
from sqlalchemy import create_engine

import pandas as pd
import pytz

LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s,ln %(lineno)d: %(message)s'
LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)

# Service settings
tz_tw = pytz.timezone('Asia/Taipei')


def get_db_url(config_path: str) -> str:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    url = config['DATABASE']['MASTER_URL']
    return url


def to_recipients(config_path: str) -> [str, str, str]:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    recipients = config['RECIPIENTS']['rssi_monitor']
    cc = config['RECIPIENTS']['rssi_monitor_cc']
    sender = config['MAIL_SENDER']['artichoke']
    return recipients, cc, sender


def params(db_url: str):
    engine = create_engine(db_url)
    sql_stmt = """
        SELECT site_id, sname, day_from, array_agg(rssi) AS rssi, android_rate, wifi_rate,
        array_agg(sniffer_id) AS sniffer_id, array_agg(rssi_group) AS rssi_group
        FROM (
	        SELECT A.site_id, A.sname, B.rssi, A.android_rate, A.wifi_rate, A.day_from, B.sniffer_id, B.rssi_group
	        FROM rssi_monitor_site_info AS A JOIN (
		        SELECT X.site_id, X.sniffer_id, Y.rssi, X.rssi_group
		        FROM rssi_monitor_sniffer_info AS X JOIN sniffer_info AS Y ON X.sniffer_id = Y.sniffer_id
	        ) AS B ON A.site_id = B.site_id
        ) AS foo GROUP BY site_id, sname, android_rate, wifi_rate, day_from
    """
    res = engine.execute(sql_stmt)
    result = res.fetchall()
    return_rssis = list()
    for site in result:
        site_id, sname, day_from, rssi, android_rate, wifi_rate, sniffer_ids, rssi_groups = site
        rssi_list = [site_id, sname, day_from, rssi, android_rate, wifi_rate]
        for sniffer_id, rssi_group in zip(sniffer_ids, rssi_groups):
            rssi_list.append({"sniffer_id": sniffer_id, "rssi_group": rssi_group.split(",")})
        if len(sniffer_ids) == 1:
            rssi_list.append(None)
        return_rssis.append(rssi_list)
    return return_rssis


class CheckRssiMonitor:
    NEED_SEND_MAIL_DAY = [1, 2, 3, 4, 5, 6, 7, 14, 21, 28]

    def __init__(self, nday: int, config_path: str):
        self._db_url = get_db_url(config_path)
        self._iso_date = (date.today() - timedelta(nday)).strftime("%Y-%m-%d")
        self._recipients, self._cc, self._sender = to_recipients(config_path)

    def check_rssi_monitor(self):
        for site in params(self._db_url):
            site_id, site_name, day_from, rssi_usage, android_ratio, wifi_ratio, sniffer1, sniffer2 = site
            if self._not_in_time_period(day_from):
                continue
            # multi sniffer
            if sniffer2 is not None:
                self._send_rssi_monitor_report_multi(site_id=site_id, site_name=site_name,
                                               target_date=None,
                                               sniffer=sniffer1['sniffer_id'],
                                               rssi_group=sniffer1['rssi_group'],
                                               sniffer2=sniffer2['sniffer_id'],
                                               rssi2_group=sniffer2['rssi_group'],
                                               ratio=android_ratio,
                                               wifi_ratio=wifi_ratio,
                                               used_rssi=rssi_usage,
                                               day_from=day_from, day_to=self._iso_date)

            # single sniffer
            else:
                self._send_rssi_monitor_report_single(site_id=site_id, site_name=site_name,
                                                target_date=None,
                                                sniffer=sniffer1['sniffer_id'],
                                                rssi_group=sniffer1['rssi_group'],
                                                ratio=android_ratio,
                                                wifi_ratio=wifi_ratio,
                                                used_rssi=rssi_usage,
                                                day_from=day_from, day_to=self._iso_date)

    def _not_in_time_period(self, day_from: str) -> bool:
        day_from = datetime.strptime(day_from, "%Y-%m-%d").date()
        day_now = date.today()
        if (day_now - day_from).days not in self.NEED_SEND_MAIL_DAY:
            return True
        else:
            return False

    def _send_rssi_monitor_report_multi(self, site_id='id', site_name='name', target_date=None,
                                       sniffer=None, rssi_group=None, sniffer2=None, rssi2_group=None,
                                       ratio=0.55, wifi_ratio=0.7, used_rssi=[-90],
                                       day_from=None, day_to=None, config=None):
        logger.info(f'Check {target_date} rawdata')

        if sniffer is None or rssi_group is None:
            logger.warning('Sniffer/rssi not set! Please check input values')
            return

        info = {
            'sniffer': sniffer,
            'rssi': used_rssi[0],
            'sniffer2': sniffer2,
            'rssi2': used_rssi[1],
            'Android Ratio': ratio,
            'WiFi Ratio': wifi_ratio
        }

        if target_date is not None and (day_from is None or day_to is None):
            day_from = target_date
            day_to = target_date

        # For output filename
        file_dayfrom = day_from.replace('-', '')
        file_dayto = day_to.replace('-', '')

        data_all = None
        for rssi in rssi_group:
            for rssi2 in rssi2_group:
                df = self._get_hourly_ppl_union(sniffer, rssi, sniffer2, rssi2, day_from, day_to, ratio, wifi_ratio)
                df.columns = ['time', f'RSSI({rssi},{rssi2})']
                if data_all is None:
                    data_all = df
                    data_all.set_index(['time'], inplace=True)
                else:
                    data_all = pd.concat([data_all, df.set_index(['time'])], axis=1)
                logger.info('Done')

        data_all.reset_index(inplace=True)
        logger.info(data_all.head())
        data_all['time'] = data_all.time.dt.tz_convert('Asia/Taipei')
        data_all['Week'] = data_all.time.apply(lambda x: x.week)
        data_all['Date'] = data_all.time.apply(lambda x: x.date())
        data_all['Weekday'] = data_all.time.apply(lambda x: x.weekday() + 1)
        data_all['Hour'] = data_all.time.apply(lambda x: x.hour)

        data_open = data_all.copy()
        data_open.drop(['time'], axis=1, inplace=True)

        data_daily = data_open.groupby('Date', axis=0).sum()
        data_epos = self._get_daily_epos(site_id, day_from, day_to)
        data_daily = pd.concat([data_daily, data_epos[['Date', 'tickets', ]].set_index('Date')], axis=1)

        for rssi in rssi_group:
            for rssi2 in rssi2_group:
                data_daily[f'Rate({rssi},{rssi2})'] = data_daily['tickets'] / data_daily[
                    f'RSSI({rssi},{rssi2})']

        df_html_output = data_daily.reset_index().drop(['Week', 'Weekday', 'Hour'], axis=1).to_html(na_rep="", index=False)
        msg_params = f'Current used parameters: <br/>{info}'

        subject = f"{site_name} RSSI Monitor {day_to}"
        content = f'<html><body>{df_html_output}<br/>{msg_params}</body></html>'

        self._send_edt_alert_mail(subject, content, config)

    def _send_rssi_monitor_report_single(self, site_id='id', site_name='name', target_date=None,
                                        sniffer=None, rssi_group=None,
                                        ratio=0.55, wifi_ratio=0.7, used_rssi=[-90],
                                        day_from=None, day_to=None, config=None):
        logger.info(f'Check {target_date} rawdata')

        if sniffer is None or rssi_group is None:
            logger.warning('Sniffer/rssi not set! Please check input values')
            return

        info = {
            'sniffer': sniffer,
            'rssi': used_rssi[0],
            'Android Ratio': ratio,
            'WiFi Ratio': wifi_ratio
        }

        if target_date is not None and (day_from is None or day_to is None):
            day_from = target_date
            day_to = target_date

        # For output filename
        file_dayfrom = day_from.replace('-', '')
        file_dayto = day_to.replace('-', '')

        data_all = None

        for rssi in rssi_group:
            df = self._get_hourly_ppl_single(sniffer, rssi, day_from, day_to, ratio, wifi_ratio)
            df.columns = ['time', f'RSSI({rssi})']
            logger.info(df.head())
            if data_all is None:
                data_all = df
                data_all.set_index(['time'], inplace=True)
            else:
                data_all = pd.concat([data_all, df.set_index(['time'])], axis=1)
            logger.info('Done')

        data_all.reset_index(inplace=True)
        logger.info(data_all.head())
        data_all['time'] = data_all.time.dt.tz_convert('Asia/Taipei')
        data_all['Week'] = data_all.time.apply(lambda x: x.week)
        data_all['Date'] = data_all.time.apply(lambda x: x.date())
        data_all['Weekday'] = data_all.time.apply(lambda x: x.weekday() + 1)
        data_all['Hour'] = data_all.time.apply(lambda x: x.hour)

        data_open = data_all.copy()
        data_open.drop(['time'], axis=1, inplace=True)

        data_daily = data_open.groupby('Date', axis=0).sum()
        data_epos = self._get_daily_epos(site_id, day_from, day_to)
        data_daily = pd.concat([data_daily, data_epos[['Date', 'tickets', ]].set_index('Date')], axis=1)

        for rssi in rssi_group:
            data_daily[f'Rate({rssi})'] = data_daily['tickets'] / data_daily[f'RSSI({rssi})']

        df_html_output = data_daily.reset_index().drop(['Week', 'Weekday', 'Hour'], axis=1).to_html(na_rep="", index=False)
        msg_params = f'Current used parameters: <br/>{info}'

        subject = f"{site_name} RSSI Monitor {day_to}"
        content = f'<html><body>{df_html_output}<br/>{msg_params}</body></html>'

        self._send_edt_alert_mail(subject, content, config)

    def _get_daily_epos(self, site_id, start_date, end_date):
        sql = f"""set session time zone 'Asia/Taipei';
        select site_id, sl_date as time, count as "tickets-all", count_unique as tickets from epos_daily where site_id='{site_id}'
        and sl_date>='{start_date}' and sl_date<='{end_date} 23:59:59'
        """
        logger.info(sql)
        df = pd.read_sql(con=self._db_url, sql=sql)
        df['time'] = df.time.dt.tz_convert('Asia/Taipei')
        df['Week'] = df.time.apply(lambda x: x.week)
        df['Date'] = df.time.apply(lambda x: x.date())
        df['Weekday'] = df.time.apply(lambda x: x.weekday() + 1)
        return df

    def _get_hourly_ppl_union(self, sniffer, rssi, sniffer2, rssi2, start_date, end_date, ratio=0.55, wifi_ratio=0.66):
        sql = f"""Set session time zone 'Asia/Taipei';
        SELECT * FROM public.counter_union_optim('{sniffer}', {rssi}, '{sniffer2}', {rssi2}, '{start_date}', '{end_date}', taiwan_android_oui(), {ratio}, _wifi_ratio:={wifi_ratio})
        where date_part('hour', time) between 10 and 21
        """
        logger.info(sql)
        return pd.read_sql(con=self._db_url, sql=sql)

    def _get_hourly_ppl_single(self, sniffer, rssi, start_date, end_date, ratio=0.55, wifi_ratio=0.66):
        sql = f"""Set session time zone 'Asia/Taipei';
        SELECT * FROM public.counter_optim('{sniffer}', {rssi}, '{start_date}', '{end_date}', taiwan_android_oui(), {ratio}, _wifi_ratio:={wifi_ratio})
        where date_part('hour', time) between 10 and 21
        """
        logger.info(sql)
        return pd.read_sql(con=self._db_url, sql=sql)

    def _send_edt_alert_mail(self, title, content, config=None):
        recipients, cc_recipients = self._recipients.split(','), self._cc.split(',')
        receivers = recipients
        message_content = MIMEText(content, 'html', 'utf-8')

        message = MIMEMultipart()
        message['Subject'] = Header(title, 'utf-8')
        message['To'] = ','.join(receivers)
        message['Cc'] = ','.join(cc_recipients)
        message.attach(message_content)

        try:
            smtpObj = smtplib.SMTP('rs1.testritegroup.com')
            logger.info(f"sender : {self._sender}")
            logger.info(f"receivers : {receivers}")
            logger.info(f"cc_receivers : {cc_recipients}")
            smtpObj.sendmail(self._sender, receivers + cc_recipients, message.as_string())
            smtpObj.close()
            logger.info("Successfully sent email")
        except smtplib.SMTPException:
            logger.info("Error: unable to send email")


def worker_run_rssi_monitor(config_path: str):
    """
    This function is used for worker call function.
    """
    rssi_monitor = CheckRssiMonitor(1, config_path)
    rssi_monitor.check_rssi_monitor()


if __name__ == '__main__':
    @click.command()
    @click.option('--nday', '-n', default=1, help='n days ago. Default is yesterday.')
    @click.option('--config_path', default='./config/artichoke_base_service.ini', help='artichoke_base_service.ini file path')
    def run(nday=1, config_path='./config/artichoke_base_service.ini', *args, **kwargs):
        rssi_monitor = CheckRssiMonitor(nday, config_path)
        rssi_monitor.check_rssi_monitor()

    run()
