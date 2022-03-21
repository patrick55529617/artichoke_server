import os
import os.path
import logging
import logging.handlers
import pytz
from datetime import datetime
import click
import pandas as pd
from email.mime.text import MIMEText
from email.header import Header
import smtplib

# E-mail settings
sender = 'artichoke@edt.testritegroup.com'
recipients  = [
	'Yen-Cheng.Lin@testritegroup.com'
]
cc_recipients = [
	'Ivy.Tseng@testritegroup.com'
]

# Database
db_url = 'postgresql+psycopg2://catnip:edt-1234@hoi.edt.testritegroup.com/catnip_multi'

# Set tolerance
tolerance = 40  # minutes

local_tz = pytz.timezone('Asia/Taipei')

# Configure logs
LOG_LEVEL   = logging.INFO
LOG_FORMAT  = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s,ln %(lineno)d: %(message)s'
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


def read_open_site_info(store_type=None, site_id=None):
    col_open_hour = 'open_hour' if datetime.today().weekday()<5 else 'open_hour_wend'
    col_closed_hour = 'closed_hour' if datetime.today().weekday()< 5 else 'closed_hour_wend'
    sql = """select * from site_info
            where --is_active = true
            (current_time at time zone 'Asia/Taipei')>={open_hour}
            and (current_time at time zone 'Asia/Taipei')<={closed_hour}
            """.format(open_hour=col_open_hour, closed_hour=col_closed_hour)
    if store_type:
        sql += """and channel='{}' """.format(store_type)
    if site_id:
        sql += """and site_id='{}' """.format(site_id)
    data = pd.read_sql(sql=sql, con=db_url).set_index('site_id')
    return data


def read_active_camera_info():
    sql = """select * from camera where is_active = true"""
    data = pd.read_sql(sql=sql, con=db_url)
    return data


def send_alert_mail(title, content, isHTML=True):
    logger.info("Send alert mail!")
    send_edt_alert__mail(title, content)


def send_edt_alert__mail(title, content):
    receivers = recipients

    message = MIMEText(content, 'html', 'utf-8')
    message['Subject'] = Header(title, 'utf-8')
    message['To'] = ','.join(recipients)

    try:
        smtpObj = smtplib.SMTP('rs1.testritegroup.com')
        logger.info("message : {0}".format(message))
        smtpObj.sendmail(sender, receivers, message.as_string())
        logger.info("Successfully sent email")
    except smtplib.SMTPException:
        logger.info("Error: unable to send email")
        logger.info("Unexpected error:", sys.exc_info()[0])


def detect_and_send_alert_cameras(store_type=None, site_id=None):
    df_sites = pd.DataFrame()
    try:
        df_sites = read_open_site_info(store_type, site_id)
        df_cameras = read_active_camera_info()
        logger.info('There are {} site(s) to be monitored.'.format(df_sites.shape[0]))
    except Exception as e:
        logger.exception(e)
        send_alert_mail('[Catnip Alert!] Database access error!',
                        'Cannot access database<br/>{}'.format(e))
        return

    if df_sites.shape[0]==0 or df_cameras.shape[0]==0:
        logger.warning('No site to be monitored....')
        return

    if df_cameras.shape[0]==0:
        logger.warning('No camera to be monitored....')
        send_alert_mail('[Catnip Alert!] No camera information',
                        'Check database table "camera"')
        return

    mail_body = ''
    for sid, site in df_sites.iterrows():
        logger.info('Check site: {}'.format(sid))

        for idx, cam in df_cameras.loc[df_cameras['site_id']==sid].iterrows():
            sql = """SELECT time,
                extract(epoch from (now()-time))::INT as diff
                FROM route_path
                WHERE camera_id={} ORDER BY time DESC LIMIT 1""".format(cam['id'])
            data = pd.read_sql(sql=sql, con=db_url)

            logger.info('[{}] {}, Last update: {}'.format(cam['id'], cam['name'], data.iloc[0]['time'].astimezone(local_tz)))
            if data.query('diff > {}*60'.format(tolerance)).shape[0] > 0:
                logger.warning('Missing camera {}, {}, {}, since {}'.format(cam['id'], cam['name'], cam['host'], data.iloc[0]['time'].astimezone(local_tz)))
                mail_body += '<tr><td>' + '</td><td>'.join(
                    [sid, str(cam['id']), cam['name'], cam['host'], str(data.iloc[0]['time'].astimezone(local_tz)), str(round(data.iloc[0]['diff']/60,2))])
                mail_body += '</td></tr>'

    if len(mail_body) > 0:
        mail_body = '<table border="2"><tr><td>Site ID</td><td>Camera ID</td><td>Name</td><td>IP</td><td>Last update time</td><td>minutes ago</td></tr>' + mail_body
        mail_body += '</table><br/>'
        mail_body += "Check camera live view http://ip/VCA/www/index.html#/Heatmap/live"

        send_alert_mail('[Catnip Alert!] Malfunction Catnip Camera(s)', mail_body)


def worker_run_check_rvca_alive():
    detect_and_send_alert_cameras()
