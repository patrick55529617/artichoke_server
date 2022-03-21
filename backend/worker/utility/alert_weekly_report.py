# -*- coding: utf-8 -*-

"""
Script for sending artichoke alert weekly report

History:
2021/03/04 Created by Patrick
"""

import smtplib
import pandas as pd
from typing import List, Union
from configparser import ConfigParser
from email.header import Header
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from utility.get_db_session import db_session
import logging

logger = logging.getLogger(__file__)


def get_params(config_path: str) -> [str, str, str, str]:
    config = ConfigParser()
    config.read(config_path, encoding='UTF-8')
    db_url = config['DATABASE']['MASTER_URL']
    recipients = config['RECIPIENTS']['alert_report']
    cc = config['RECIPIENTS']['alert_report_cc']
    sender = config['MAIL_SENDER']['artichoke']
    return db_url, recipients, cc, sender


class AlertRecord:
    """
    Definition of alert record rawdata.
    """

    def __init__(self, sniffer_id, rawdata):
        """
        Initialization for AlertRecord.
        """
        self._sniffer_id = sniffer_id
        self._site_info = rawdata

    def get_sniffer_id(self):
        return self._sniffer_id

    def get_site_info(self):
        return self._site_info


class AlertWeeklyReport:

    def __init__(
        self,
        slave_db_url=None,
        mail_server='rs1.testritegroup.com',  # IP:172.16.1.9
        mail_sender='',
        mail_recipients='',
        mail_cc_recipients='',
        start_time=None,
        end_time=None
    ):
        self._mail_server = mail_server
        self._mail_sender = mail_sender
        self._mail_recipients = mail_recipients.split(',') if mail_recipients else []
        self._mail_cc_recipients = mail_cc_recipients.split(',') if mail_cc_recipients else []
        self._db_session = next(db_session(slave_db_url))
        self._start_time_utc = start_time if start_time else str(datetime.utcnow() - timedelta(days=7))
        self._end_time_utc = end_time if end_time else str(datetime.utcnow())
        self._start_time = start_time if start_time else str(datetime.now() - timedelta(days=7))
        self._end_time = end_time if end_time else str(datetime.now())

    def main_process(self):
        """
        Main Process for alert record weekly report.

        This function will do the following tasks:
        1. Generate sql for querying alert records in input time interval.
        2. Select result from database using generated sql.
        3. Transfer result to pandas dataframe.
        4. Use above dataframe to send email.
        """
        sql_stx = self._get_sql_for_query_alert_record()
        alert_record_dict = self._query_db_using_sql(sql_stx)
        severity_dict = self._get_alert_severity_dict(list(alert_record_dict.keys()))
        self._db_session.close()
        df_alert_record = self._get_alert_record_df(alert_record_dict, severity_dict)
        self._send_mail(df_alert_record)

    def _get_sql_for_query_alert_record(self) -> str:
        """
        Combine sql syntax for querying alert records in time interval [start_time, end_time].
        """
        sql_stx = f"""
            SELECT severity_id, sniffer_id, rawdata FROM public.alert_record
            WHERE alert_report_time BETWEEN '{self._start_time_utc}' AND '{self._end_time_utc}'
        """
        return sql_stx

    def _query_db_using_sql(self, sql_stx: str) -> dict:
        """
        Query database and return result dictionary.
        """
        result = self._db_session.execute(sql_stx)
        result_dict = {}
        for record in result.fetchall():
            severity_id, sniffer_id, rawdata = record
            alert_record = AlertRecord(sniffer_id=sniffer_id, rawdata=rawdata)
            if not result_dict.get(severity_id):
                result_dict[severity_id] = [alert_record]
            else:
                result_dict[severity_id].append(alert_record)
        return result_dict

    def _get_alert_severity_dict(self, severity_ids: List[int]) -> dict:
        """
        Get alert severtiy name by id.
        """
        sql_stx = f"""
            SELECT id, severity_name FROM public.alert_severity_info
            WHERE id IN ({', '.join([str(i) for i in severity_ids])})
        """
        result = self._db_session.execute(sql_stx)
        severity_dict = {}
        for severity in result.fetchall():
            severity_id, severity_name = severity
            severity_dict[severity_id] = severity_name
        return severity_dict

    def _get_alert_record_df(self, alert_record_dict: dict, severity_dict: dict) -> pd.DataFrame:
        """
        Generate DataFrame for alert records.
        """
        df_transfered_list = list()
        for severity in severity_dict.keys():
            alert_time, unique_sniffer_count, site_name_list = self._gen_statistics(alert_record_dict[severity])
            df_transfered_list.append([severity_dict[severity], alert_time, unique_sniffer_count, site_name_list])
        df_alert_record = pd.DataFrame(df_transfered_list, columns=['severity_name', 'alert_time', 'unique_sniffer_count', 'site_list'])
        return df_alert_record

    def _send_mail(self, df_alert_record: pd.DataFrame):
        """
        Send email using input dataframe.
        """
        title = f"""[Artichoke]{self._start_time} - {self._end_time} alert report statistics"""
        content = df_alert_record.to_html(index=False, justify='center')
        message = MIMEText(content, 'html', 'utf-8')
        message['Subject'] = Header(title, 'utf-8')
        message['To'] = ','.join(self._mail_recipients)
        message['Cc'] = ','.join(self._mail_cc_recipients)

        try:
            smtpObj = smtplib.SMTP(self._mail_server)
            logger.info("message to : %s, cc: %s", self._mail_recipients, self._mail_cc_recipients)
            smtpObj.sendmail(self._mail_sender, self._mail_recipients, message.as_string())
            logger.info("Successfully sent email")
        except smtplib.SMTPException:
            logger.info("Error: unable to send email", exc_info=True)

    def _gen_statistics(self, alert_records: List[AlertRecord]) -> [int, int, List]:
        """
        Calculate the following statistics:

        1. alert_time: Calculate times of receiving alert.
        2. unique_sniffer_count: Count the number of sniffers having triggered alert.
        3. site_name_list: List all site_names having triggered alert.
        """
        alert_time = self._get_alert_time(alert_records)
        unique_sniffer_count = self._get_unique_sniffer_count(alert_records)
        site_list = self._get_site_list(alert_records)
        return alert_time, unique_sniffer_count, site_list

    @staticmethod
    def _get_alert_time(alert_records: List[AlertRecord]) -> int:
        """
        Calculate times of receiving alert.

        The length of alert_records is alert_time.
        """
        return len(alert_records)

    def _get_unique_sniffer_count(self, alert_records: List[AlertRecord]) -> int:
        """
        Calculate the number of sniffers having triggered alert.

        The length of sniffer_set is unique_sniffer_count.
        """
        sniffer_set = self._get_sniffer_set(alert_records)
        return len(sniffer_set)

    def _get_site_list(self, alert_records: List[AlertRecord]) -> List:
        """
        Calculate the number of sniffers having triggered alert.

        The list of site_set is site_info_set.
        """
        site_set = self._get_site_set(alert_records)
        return list(site_set)

    @staticmethod
    def _get_sniffer_set(alert_records: List[AlertRecord]) -> set:
        """
        Get sniffer set.

        Put all sniffers triggered alert to set to get unique sites.
        """
        sniffer_set = set([alert_record.get_sniffer_id() for alert_record in alert_records])
        return sniffer_set

    @staticmethod
    def _get_site_set(alert_records: List[AlertRecord]) -> set:
        """
        Get site info set.

        Put all sites triggered alert to set to get unique sites.
        """
        site_set = set([alert_record.get_site_info().get('sname') for alert_record in alert_records])
        return site_set


def worker_run_alert_weekly_report(config_path: str, start_time: Union[str, None], end_time: Union[str, None]):
    db_url, recipients, cc, sender = get_params(config_path)
    alert_weekly_report = AlertWeeklyReport(
        slave_db_url=db_url,
        mail_sender=sender,
        mail_recipients=recipients,
        mail_cc_recipients=cc,
        start_time=start_time,
        end_time=end_time
    )
    alert_weekly_report.main_process()


def main():
    db_url, recipients, cc, sender = get_params('/root/artichoke_base_service.ini')
    alert_weekly_report = AlertWeeklyReport(
        slave_db_url=db_url,
        mail_sender=sender,
        mail_recipients=recipients,
        mail_cc_recipients=cc
    )
    alert_weekly_report.main_process()


if __name__ == '__main__':
    main()
