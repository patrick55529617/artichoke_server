import os
import os.path
import logging
import logging.handlers
import bz2
import requests
import json
import pytz
from datetime import datetime
import click
import smtplib
import pandas as pd
import time
import sys
from exchangelib import DELEGATE, IMPERSONATION, Account, Credentials, ServiceAccount, \
    EWSDateTime, EWSTimeZone, Configuration, Message, Mailbox, FileAttachment, HTMLBody
from email.mime.text import MIMEText
from email.header import Header
import traceback

# ignore site id list
ignore_site_list = []

# E-mail settings
sender = 'hi0006@testritegroup.com'
recipients = [sender, 
               'cloude.chiu@testritegroup.com', 
               'Dream.Chang@testritegroup.com',
               'Yen-Cheng.Lin@testritegroup.com'
              ]
cc_recipients = []

# Database
db_url = 'postgresql+psycopg2://artichoke:edt-1234@monitor.wifiprobe.edt.testritegroup.com/artichoke'

# MQTT Broker
brokers = ['http://10.101.1.57:18083', 'http://10.101.1.58:18083']

# Alarm config
detect_interval = 600

# Configure logs
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)-15s %(levelname)s %(processName)s-%(threadName)s,%(module)s,%(funcName)s,ln %(lineno)d: %(message)s'
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

if not os.path.exists('log_prod'):
    os.makedirs('log_prod')
formatter = logging.Formatter(LOG_FORMAT)
handler = logging.handlers.TimedRotatingFileHandler("log_prod/monitor.log", when="midnight", backupCount=30)
handler.setFormatter(formatter)


def rotator(source, dest):
    with open(source, 'rb') as f:
        with bz2.BZ2File(dest + '.bz2', 'w') as out:
            out.write(f.read())
    os.remove(source)


handler.rotator = rotator
logging.getLogger().addHandler(handler)


def get_mqtt_nodes(broker):
    uri = '/api/v2/monitoring/nodes'
    header = {'Content-type': 'application/json',
              'Authorization': 'Basic YWRtaW46cHVibGlj'}
    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.get('{}{}'.format(broker, uri), headers=header, timeout=(3, 10))
    except Exception as e:
        logger.exception(e)
        raise e

    return [node['name'] for node in resp.json()['result']]


def get_mqtt_connected_clients(broker, nodes):
    header = {'Content-type': 'application/json',
              'Authorization': 'Basic YWRtaW46cHVibGlj'}
    result = []
    for node in nodes:
        uri = '/api/v2/nodes/{}/clients?page_size=200'.format(node)
        try:
            resp = requests.get('{}{}'.format(broker, uri), headers=header, timeout=(3, 10))
            resp.raise_for_status()
            result.extend(resp.json()['result'].get('objects', None))

            json_resp = resp.json()['result']
            logger.debug('[{}] Total number of clients: {}'.format(broker, json_resp['total_num']))

            total_pages = json_resp['total_page']
            logger.debug('[{}] Current page: {}/{}'.format(broker, json_resp['current_page'], total_pages))
            if total_pages > 1:
                for page in range(2, total_pages + 1):
                    uri = '/api/v2/nodes/{}/clients?page_size=200&curr_page={}'.format(node, page)
                    resp = requests.get('{}{}'.format(broker, uri), headers=header, timeout=(3, 10))
                    resp.raise_for_status()
                    result.extend(resp.json()['result'].get('objects', None))
                    logger.debug(
                        '[{}] Current page: {}/{}'.format(broker, resp.json()['result']['current_page'], total_pages))
        except Exception as e:
            logger.exception(e)
            raise e
    logger.debug('[{}] Number of connected clients found: {}'.format(broker, len(result)))
    return result


def detect_and_send_offline_clients(conn_clients, store_type=None, site_id=None):
    df_sites = pd.DataFrame()
    try:
        df_sites = read_open_site_info(store_type, site_id)
        logger.info('There are {} site(s) to be monitored.'.format(df_sites.shape[0]))
    except Exception as e:
        logger.exception(e)
        send_alert_mail('[Alert!] No target clients information',
                        'Cannot access database<br/>{}'.format(e))
        return
    if df_sites.shape[0] == 0:
        logger.warning('No target clients to be monitored....')
        send_alert_mail('[Alert!] No target clients information',
                        'Check database table "site_info"')
        return

    mail_body = ''
    candidate_alarm_client = []
    
    conn_sniffer_list = []
    for conn_client in conn_clients:
        conn_sniffer_list.append(conn_client.split('_')[-1:][0])
    logger.warning('Total {} sniffer found.'.format(len(conn_sniffer_list)))
    
    for sid, site in df_sites.iterrows():
        for sniffer in site['sniffer']:
            if sniffer in conn_sniffer_list:
                logger.info('{} is online'.format(sniffer))
            else:
                logger.warning('Sniffer {} is not connected!!'.format(sniffer))
                client_id = '{}_{}_{}_{}'.format(sid, site['city_enc'], site['channel'], sniffer)
                        
                data = {
                    "client_id": client_id,
                    "sid": sid,
                    "sname": site['sname'],
                    "channel": site['channel'],
                    "sniffer": sniffer,
                    "is_released": str(site['is_released'])
                }
                
                logger.info('{}'.format(data))
                candidate_alarm_client.append(data)

    candidate_alarm_client = check_candidate_alarm_client_delivery_time(candidate_alarm_client)
    for alarm_client in candidate_alarm_client:
        mail_body += '<tr><td>' + '</td><td>'.join(
            [alarm_client['sid'],
             alarm_client['sname'],
             alarm_client['channel'],
             alarm_client['client_id'],
             alarm_client['sniffer'],
             alarm_client['interval'],
             alarm_client['is_released']]
        )
        mail_body += '</td></tr>'

    if len(mail_body) > 0:
        mail_body = '''
        <table border="2">
            <tr>
                <td>sid</td>
                <td>site</td>
                <td>channel</td>
                <td>mqtt_id</td>
                <td>mac</td>
                <td>interval(m)</td>
                <td>released</td>
            </tr>
            {0}
        </table>
        <br/>
        '''.format(mail_body)

        send_alert_mail('[Alert!] Missing Artichoke {} Sniffer '.format(len(candidate_alarm_client)), mail_body)
    return


def read_site_info(store_type=None, site_id=None):
    sql = """select * from site_info """
    if site_id:
        sql += """where site_id='{}'""".format(site_id)
    elif store_type:
        sql += """where channel='{}'""".format(store_type)
    
    if len(ignore_site_list) > 0:
        sql += """and site_id not in ({}) """.format(", ".join( ["'{0}'".format(ignore_site) for ignore_site in ignore_site_list] ))

    data = pd.read_sql(sql=sql, con=db_url).set_index('site_id')
    return data


def read_open_site_info(store_type=None, site_id=None):
    col_open_hour = 'open_hour' if datetime.today().weekday() < 5 else 'open_hour_wend'
    col_closed_hour = 'closed_hour' if datetime.today().weekday() < 5 else 'closed_hour_wend'
    sql = """select * from site_info 
            where (is_active = true OR site_id='1S02-area') 
            and (current_time at time zone 'Asia/Taipei')>={open_hour} 
            and (current_time at time zone 'Asia/Taipei')<={closed_hour} 
            and site_id != '1C03-area'
            """.format(open_hour=col_open_hour, closed_hour=col_closed_hour)
    if store_type:
        sql += """and channel='{}' """.format(store_type)
    if site_id:
        sql += """and site_id='{}' """.format(site_id)

    if len(ignore_site_list) > 0:
        sql += """and site_id not in ({}) """.format(", ".join( ["'{0}'".format(ignore_site) for ignore_site in ignore_site_list] ))

    data = pd.read_sql(sql=sql, con=db_url).set_index('site_id')
    return data


def send_alert_mail(title, content, isHTML=True):
    print("Send alert {}".format(datetime.now()))
    # send_tlw_outlook_mail(title, content)
    send_tlw_dev_mail(title, content)
    return


def check_candidate_alarm_client_delivery_time(candidate_alarm_client):
    today = datetime.today()
    sql_list = []

    logger.info("before : \n{}".format(candidate_alarm_client))

    for alarm_client in candidate_alarm_client:
        sql_list.append("""
        (
        SELECT * 
        FROM
        (
            SELECT rt, sniffer, upload_time::time upload_time, delivery_time::time delivery_time, 
                    rt::date rt_date, now()::date now_date,
                    (now()-delivery_time) from_now_interval 
            FROM rawdata_{0}
            ORDER BY rt desc
            LIMIT 1
        ) last_rawdata
        )
        """.format(alarm_client['sniffer']))

    sql = "UNION".join(str(x) for x in sql_list)

    if len(sql):
        logger.info(sql)
        data = pd.read_sql(sql=sql, con=db_url)

        # check time delta for > 10 mins
        logger.info("check query result : \n{0}".format(data[['sniffer', 'from_now_interval']]))
        logger.info("check seconds : \n{0}".format(data['from_now_interval'].dt.seconds))
        hit_data = data[data['from_now_interval'].dt.seconds > detect_interval]

        # remove not hit candidate
        remove_idx_list = []

        try:
            for idx, val in enumerate(candidate_alarm_client):
                if len(hit_data[hit_data['sniffer'] == val['sniffer']]) == 0:
                    remove_idx_list.append(idx)
                else:
                    interval = round(data[data['sniffer'] == val['sniffer']]['from_now_interval'].dt.total_seconds().iloc[0]/60,3)
                    val['interval'] = str(interval)
            candidate_alarm_client = [i for j, i in enumerate(candidate_alarm_client) if j not in remove_idx_list]
        except:
            exception_message = "[Exception] {}".format(traceback.format_exc())
            logger.info("[Exception] {}".format(traceback.format_exc()))
            send_tlw_outlook_mail('[Exception] Artichoke alarm exception', exception_message)

        logger.info("after : \n{0}".format(candidate_alarm_client))
    else:
        logger.info("No offline clients!")
        candidate_alarm_client = []

    return candidate_alarm_client


def send_tlw_outlook_mail(title, content):
    title = "{}".format(title)
    credentials = Credentials(username='hi0006@testritegroup.com', password='Aa654321')
    config = Configuration(server='outlook.office365.com/EWS/Exchange.asmx', credentials=credentials)
    account = Account(primary_smtp_address=sender, config=config, autodiscover=False, access_type=DELEGATE)
    mail = Message(
        account=account,
        subject=title,
        body=HTMLBody('<html><body>{}</body></html>'.format(content)),
        to_recipients=recipients,
        cc_recipients=cc_recipients)
    mail.send()
    return


def send_tlw_dev_mail(title, content):
    sender = 'artichoke@edt.testritegroup.com'
    receivers = recipients

    message = MIMEText(content, 'html', 'utf-8')
    message['Subject'] = Header(title, 'utf-8')
    message['To'] = ','.join(recipients)

    try:
        smtpObj = smtplib.SMTP('rs1.testritegroup.com')
        logger.info("message to : {0}".format(message['To']))
        smtpObj.sendmail(sender, receivers, message.as_string())
        logger.info("Successfully sent email")
    except smtplib.SMTPException:
        logger.info("Error: unable to send email")
        logger.info("Unexpected error:", sys.exc_info()[0])

    return


if __name__ == '__main__':
    @click.command()
    @click.option('-t', '--site_type', default=None, help='Site chaneel: TLW|HOLA')
    @click.option('-s', '--site_id', default=None, help='Site id. e.g.1A02')
    @click.option('--db', default=None, help='e.g. 10.101.26.188')
    @click.option('-b', '--broker', default=None, help='http://10.101.1.57:18083,http://10.101.1.58:18083')
    @click.option('-d', '--debug', is_flag=True)
    def main(site_type=None, site_id=None, debug=False, db=None, broker=None, **kwargs):
        global recipients, recipients_china, cc_recipients, db_url, brokers
        if db is not None:
            db_url = 'postgresql+psycopg2://artichoke:edt-1234@{}/artichoke'.format(db)
        if broker is not None:
            brokers = broker.split(',')

        if debug:
            logging.getLogger(__name__).setLevel(logging.DEBUG)
            recipients = []
            cc_recipients = [sender]

        error = None
        try:
            client_list = []
            for broker in brokers:
                nodes = get_mqtt_nodes(broker)
                clients = get_mqtt_connected_clients(broker, nodes)
                client_list.extend(clients)
        except Exception as e:
            logger.exception(e)
            error = e
        if error or len(nodes) == 0 or len(clients) == 0:
            logger.warning('Cannot get MQTT clients from MQTT Broker! Check if broker works normally...')
            send_alert_mail('[Alert!] Cannot access MQTT Broker',
                            '<p>Fail to query MQTT clients info from MQTT Broker!</p> \
                             <p>Check if MQTT Broker works normally...</p><br/> \
                             <p>{}</p><br/>'.format(error))
            return

        conn_list = []
        for client in client_list:
            conn_list.append(client['client_id'].lower())
        detect_and_send_offline_clients(conn_list, site_type, site_id)

        print(datetime.now())

    main()
