import os.path
import logging
import logging.config
import asyncio
from contextlib import closing
from datetime import datetime, timedelta, date
import smtplib
import random
from email.mime.text import MIMEText
from email.header import Header
from configparser import ConfigParser
from argparse import ArgumentParser
from urllib.parse import urlparse
from utility.get_db_session import db_session

import asyncssh
import pytz
import requests
import pandas as pd
import numpy as np

DEV_MAINTAINER_MAIL = 'Ivy.Tseng@testritegroup.com,patrick.hu@testritegroup.com,Yen-Cheng.Lin@testritegroup.com,ming.lee@testritegroup.com'
LOG_FILE_PATH = '/worker/log'

logger = logging.getLogger(__file__)
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
    },
    'formatters': {
        'simple': {
            'format': "%(asctime)s:%(levelname)s:%(message)s",
        },
        'detailed': {
            'format': '%(asctime)s %(module)-17s line:%(lineno)-4d %(levelname)-8s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file':{
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'detailed',
            'filename': os.path.join(LOG_FILE_PATH, "artichoke_rawdata_missing_alarm.log"),
            'when' : 'midnight',
            'backupCount': 7,
        },
        'smtp': {
            'level': 'ERROR',
            'class': 'logging.handlers.SMTPHandler',
            'formatter': 'detailed',
            'mailhost': 'rs1.testritegroup.com', # IP:172.16.1.9
            'fromaddr': 'noreply-edt@testritegroup.com',
            'toaddrs': DEV_MAINTAINER_MAIL.split(','),
            'subject': '[Artichoke] Alarm Script',
        },
    },
    'root': {
        'handlers': ['file', 'smtp'],
        'level': 'INFO', #'WARNING'
    }
}


class SSHCommandLine:
    DEFAULT_RUN_CMD = {
        # 'hostname': '''hostname''',
        # 時間
        # '設備目前時間': '''date''',
        # '開機時間': '''uptime -s''',
        # '開機多久': '''uptime -p''',
        # '時間校正': '''sudo journalctl | grep "Time has been changed" | cut -c 1-15''',
        # '最後校時時間': '''stat -c '%y' /var/lib/systemd/clock''',
        # WiFi
        'wifi-signal': '''nmcli -f 'SIGNAL,DEVICE,IN-USE' dev wifi list | grep '*' | grep wlx | head -n 1 | awk '{printf $1}' ''',
        'ping-lost-ratio': '''ping 10.101.1.56 -c 10 -i 0.2 -q 2>&1 | grep 'packet loss' | cut -d ',' -f 3 | cut -d ' ' -f 2 | cut -d '%' -f1''',
        # Sys.
        # 'Docker daemon 運作狀態': '''systemctl is-active docker''',
        # 'UPS套件(picofssd) daemon 運作狀態': '''systemctl is-active picofssd''',
        # App.
        # 'Artichoke-client 運作狀態': '''sudo docker container inspect -f '{{.State.Running}}' artichoke-client''',
        # 'Redis 運作狀態': '''sudo docker container inspect -f '{{.State.Running}}' redis''',
        # 'Frp 運作狀態': '''sudo docker container inspect -f '{{.State.Running}}' inspiring_khorana''',
        'redis-queue': '''sudo docker exec redis redis-cli llen artichoke;''',
    }

    def __init__(self, host, port, username, password, keypath, test_cmds):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._keypath = keypath
        self._test_cmds = test_cmds if test_cmds else SSHCommandLine.DEFAULT_RUN_CMD

    async def __run_cmd(self, cmd, conn=None, sudo=False, retry=3):
        assert cmd
        logger.info('cmd(%s is by sudo): %s', sudo, cmd)

        if sudo:
            send_ssh_cmd = 'echo {} | sudo -k  -S '.format(self._password) + cmd
        else:
            send_ssh_cmd = cmd

        for _ in range(1, retry + 1):
            try:
                result = await conn.run(send_ssh_cmd)
                return result
            except Exception as e:
                logger.debug(e, exc_info=True)
                await asyncio.sleep(random.randint(1, 2))

    async def proc_cmd(self, retry=5):
        for _ in range(1, retry + 1):
            try:
                async with asyncssh.connect(
                        self._host,
                        port=self._port,
                        username=self._username,
                        client_keys=self._keypath,
                        known_hosts=None,  # Disable: known hosts checking
                ) as conn:
                    cmd_result = {}

                    for k, cmd in self._test_cmds.items():
                        cmd = cmd.strip()
                        is_sudo = cmd.startswith('sudo')
                        if is_sudo:  # trunc "sudo" string
                            cmd = cmd.replace('sudo ', '', 1)

                        run_result = await self.__run_cmd(cmd, conn=conn, sudo=is_sudo)
                        if run_result is None:
                            run_status = -1
                            run_stdout = None
                        else:
                            run_status = run_result.exit_status
                            run_stdout = run_result.stdout.rstrip() if run_result.exit_status == 0 else None
                        cmd_result[k] = {
                            'exit_code': run_status,
                            'result': run_stdout
                        }

                    return cmd_result
            except asyncssh.misc.ConnectionLost as e:
                await asyncio.sleep(random.randint(1, 2))
            except ConnectionRefusedError:
                await asyncio.sleep(random.randint(1, 2))
            except Exception as e:
                logger.warning(e, exc_info=True)
                await asyncio.sleep(random.randint(10, 30))

    @staticmethod
    def remote_device_fetch_information(l1_l2_df, frp_url, ssh_user, ssh_pwd, ssh_keypath, *args, **kwargs):
        test_cmd = SSHCommandLine.DEFAULT_RUN_CMD
        frp_hostname = urlparse(frp_url).hostname

        mapping_key = 'sniffer'
        device_info = []
        tasks = {}
        with closing(asyncio.get_event_loop()) as loop:
            for _, row in l1_l2_df.iterrows():
                ssh = SSHCommandLine(
                    frp_hostname,
                    row['frp_remote_port'],
                    ssh_user,
                    ssh_pwd,
                    ssh_keypath,
                    test_cmd,
                )
                task = loop.create_task(ssh.proc_cmd())
                tasks[row[mapping_key]] = task

            loop.run_until_complete(asyncio.gather(*tasks.values()))

        cols = [mapping_key] + [col + '.result' for col in test_cmd.keys()]
        for key, task in tasks.items():
            task_result = task.result()
            if task_result:
                device_info.append({
                    mapping_key: key,
                    **task.result(),
                })
            else:
                # Timeout or Unknown client occur exception.
                # fill np.nan value to command result
                device_info.append({
                    mapping_key: key,
                    **{col + '.result': np.nan for col in test_cmd.keys()},
                })

        if device_info:
            device_info_df = pd.io.json.json_normalize(device_info)
        else:
            device_info_df = pd.DataFrame(columns=cols)

        # 將數值轉成數字，若非數字型態就填上 np.nan
        for col in device_info_df.columns.unique():
            if col.endswith('exit_code') or col.endswith('result'):
                device_info_df[col] = pd.to_numeric(device_info_df[col], errors='coerce')

        # 將程式執行結果非 0 (正常執行)，將執行結果填上 np.npn
        for col in device_info_df.columns.unique():
            if col.endswith('exit_code'):
                token, _ = col.rsplit('.', maxsplit=1)
                result_col = f'{token}.result'
                device_info_df.loc[((device_info_df[col].isna()) | (device_info_df[col] != 0)), result_col] = np.nan

        # 留下我們有興趣的欄位
        device_info_df = device_info_df[cols]

        return device_info_df


class MonitorTask:
    def __init__(self,
                 site_type=None,
                 site_id=None,
                 ignore_site_list='',
                 check_sniffer='',
                 # Database 設定.
                 master_db_url=None,
                 slave_db_url=None,
                 # MQTT
                 mqtt_brokers='http://10.101.1.57:18083,http://10.101.1.58:18083',
                 mqtt_api_token=None,
                 # FRP
                 frp_url='http://10.101.2.108:7500',
                 frp_user=None,
                 frp_pwd=None,
                 # SSH
                 ssh_user=None,
                 ssh_pwd=None,
                 ssh_keypath=None,
                 # E-mail settings
                 mail_server='rs1.testritegroup.com',  # IP:172.16.1.9
                 mail_sender='',
                 mail_recipients='',
                 mail_cc_recipients='',
                 send_email='',
                 *args, **kwargs):
        self._site_type = site_type.upper() if site_type else site_type
        self._site_id = site_id
        self._ignore_site_list = ignore_site_list.split(',') if ignore_site_list else []
        self._master_db_url = master_db_url
        self._slave_db_url = slave_db_url
        self._check_sniffer = check_sniffer.split(',') if check_sniffer else []

        self._mqtt_brokers = mqtt_brokers.split(',') if mqtt_brokers else []
        self._mqtt_api_token = mqtt_api_token

        self._frp_url = frp_url
        self._frp_user = frp_user
        self._frp_pwd = frp_pwd

        self._ssh_user = ssh_user
        self._ssh_pwd = ssh_pwd
        self._ssh_keypath = ssh_keypath

        self._mail_server = mail_server
        self._mail_sender = mail_sender
        self._mail_recipients = mail_recipients.split(',') if mail_recipients else []
        self._mail_cc_recipients = mail_cc_recipients.split(',') if mail_cc_recipients else []
        self._send_email = send_email

    def read_open_site_info(self, open_hour_buffer='00:00:00',
                            check_sniffer=None, site_type=None, site_id=None, ignore_site_list=None):
        """ 參考 site-info TABLE 取得有在運作的設備與門店資訊

        Args:
            open_hour_buffer(str): 開店時間的緩衝，營業時間二十分鐘內，我們可以忽略這間門店不檢查。
            check_sniffer (str): 限定哪幾隻 sniffer
            site_type (str): 限定某通路
            site_id (str): 限定單一門店
            ignore_site_list (List(str)): 過濾掉哪些門店
        Returns:
            (pandas.DataFrame): Artichoke site_info 門店資訊
                欄位有: site_id, sniffer, sname, union_sniffer, is_released

        """
        col_open_hour = 'open_hour' if datetime.today().weekday() < 5 else 'open_hour_wend'
        col_closed_hour = 'closed_hour' if datetime.today().weekday() < 5 else 'closed_hour_wend'

        # 將 site_id 一些後綴字樣全剔除 (如: 1A06-TEST, 1A09-UPS, ...)
        sql = f"""SET SESSION TIME ZONE 'Asia/Taipei';
        SELECT site_id, sname, sniffer, union_sniffer, is_released, machine_area, machine_location, sniffer_no, tel
        FROM (
            SELECT si_i.site_id AS site_id, si_i.sname AS sname, si_i.{col_open_hour}, si_i.{col_closed_hour},
            si_i.is_released AS is_released, si_i.tel AS tel,
            sn_i.sniffer_id AS sniffer, sn_i.union_sniffer AS union_sniffer,
            machine_area, machine_location, sniffer_no
            FROM site_info AS si_i
            INNER JOIN (
                SELECT A.site_id, A.sniffer_id, A.machine_area AS machine_area, A.machine_location AS machine_location,
                       A.sniffer_no AS sniffer_no, B.union_sniffer AS union_sniffer
                FROM sniffer_info AS A
                INNER JOIN (
                    SELECT site_id, array_agg(sniffer_id) AS union_sniffer FROM sniffer_info WHERE is_active
                    GROUP BY site_id
                ) AS B
                ON A.site_id = B.site_id WHERE A.is_active
            )
            AS sn_i ON si_i.site_id = sn_i.site_id
        ) as t
        """

        sql += f""" WHERE CURRENT_TIME BETWEEN {col_open_hour} + INTERVAL '{open_hour_buffer}' AND {col_closed_hour}"""
        if site_type:
            sql += """ AND channel~'{}' """.format(site_type)
        if site_id:
            sql += """ AND site_id~'{}' """.format(site_id)
        if ignore_site_list:
            sql += """ AND site_id NOT IN ({}) """.format(
                ','.join([f"'{site_id}'" for site_id in ignore_site_list]))

        data = pd.read_sql(sql=sql, con=self._slave_db_url)
        data.rename(columns={
            'machine_area': '安裝區域',
            'machine_location': '安裝方式',
        }, inplace=True)

        return data

    def get_sniffer_last_rawdata_record_by_sniffer(self, sniffer_list, filter_device_clock_right=False) -> pd.DataFrame:
        """
        Returns:
            (pd.DataFrame): 天線最後一筆收到資料 cols: sniffer, rt, delivery_time, rt_offset, delivery_time_offset
        """

        # artichoke public.rawdata_{sniffer}_{year}_{month} 為 Partition-Table 結構(Partition-key/Primary-key: rt)
        # 這邊邏輯我們想要這些天線最後一筆被寫入 rawdata 資料 (就是 delivery_time 最大的時間)
        # 但因為資料庫 PK 結構關係，直接撈取 delivery_time 最後一筆資料會取不出來
        # 退而求其次，我只能先從逐步抓一些 RT 時間資料，再取出 delivery_time 最近一筆
        # 直到資料庫目前最多儲存三個月資料，實務上應當會把所有資料都抓齊全
        notfound_sniffer_set = set(sniffer_list)
        sniffer_last_rawdata_df_list = []

        # 按照下面規則一次抓一些，實際情況絕大多數 case 應當在 0 就抓完畢
        # 只有少數門店晚開緣故，才會走到 1
        # [0: >= today, 1: >= yesterday,  7: last week, 14: two weeks ago, 30: last month, ...]
        today = date.today()
        for before_interval_day in [0, 1, 7, 14, 30, 60, 90]:
            logger.debug('Try to query last raw-data by %s interval', before_interval_day)
            capture_date = today - timedelta(days=before_interval_day)
            sql = "SET SESSION time zone 'Asia/Taipei';\n"
            sql_list = []
            for sniffer in notfound_sniffer_set:
                sql_list.append("""
                (
                    SELECT sniffer, rt, upload_time, delivery_time
                    FROM rawdata_{sniffer}_{year}_{month}
                    WHERE
                        CURRENT_DATE - INTERVAL '{before_interval_day} DAYS' <= rt
                        {device_rt_ut_dt_is_seq_sql}  -- 是否要限定時序正確的資料
                    ORDER BY delivery_time DESC       -- 今天最後一筆寫入 DB 資料
                    LIMIT 1
                )
                """.format(
                    sniffer=sniffer,
                    before_interval_day=before_interval_day,
                    device_rt_ut_dt_is_seq_sql=' AND rt <= upload_time AND upload_time <= delivery_time ' if filter_device_clock_right else '',
                    year=capture_date.year,
                    month=str(capture_date.month).zfill(2)
                )
            )

            sql += "UNION ALL".join(str(x) for x in sql_list)
            tmp_df = pd.read_sql(sql=sql, con=self._slave_db_url)
            notfound_sniffer_set -= set(tmp_df.sniffer.tolist())

            logger.debug('Interval(s) %s: found %s sniffer(s) and not found %s sniffer(s)',
                         before_interval_day,
                         len(tmp_df.sniffer.tolist()),
                         len(notfound_sniffer_set),
                         )

            sniffer_last_rawdata_df_list.append(tmp_df)

            if len(notfound_sniffer_set) == 0:
                # Get ALL sniffer data.
                break

        sniffer_last_rawdata_df = pd.concat(sniffer_last_rawdata_df_list)
        if notfound_sniffer_set:
            logger.warning('Not found sniffer(s):%s', list(notfound_sniffer_set))

        tz = pytz.timezone('Asia/Taipei')
        # 將時間欄位全部自動轉 Local Time-Zone
        for col, col_type in sniffer_last_rawdata_df.dtypes.items():
            if pd.api.types.is_datetime64_any_dtype(col_type):
                sniffer_last_rawdata_df[col] = sniffer_last_rawdata_df[col].dt.tz_convert(tz)

        now = datetime.now(tz)
        for c in 'rt,delivery_time'.split(','):
            sniffer_last_rawdata_df[c + '_offset'] = now - sniffer_last_rawdata_df[c]

        sniffer_last_rawdata_df['upload_gap'] = sniffer_last_rawdata_df['upload_time'] - sniffer_last_rawdata_df[
            'delivery_time']
        return sniffer_last_rawdata_df

    def get_mqtt_connected_status(self, mqtt_req_timeout=(3, 10)):
        """ 目前與 MQTT 服務連線中的設備清單
        Args:
        Returns:
            (pd.DataFrame): 回傳 MQTT 當前有連線的設備 cols: site_id, sniffer, mqtt_conn
        """
        mqtt_req_header = {
            'Content-type': 'application/json',
            'Authorization': self._mqtt_api_token,
        }

        def get_mqtt_node_hostname(broker_url):
            assert self._mqtt_api_token

            mqtt_req_path = '/api/v2/monitoring/nodes'
            api_url = '{}{}'.format(broker_url, mqtt_req_path)
            try:
                r = requests.get(api_url,
                                 headers=mqtt_req_header,
                                 timeout=mqtt_req_timeout,
                                 )

                r.raise_for_status()
                for node in r.json()['result']:
                    yield node['name']

            except Exception as e:
                logger.error("MQTT API (%s) 查詢失敗", broker_url, exc_info=True)
                raise e

        def fetch_device_info_from_mqtt_node(broker_url, mqtt_node, curr_page=1, mqtt_page_size=200):
            assert self._mqtt_api_token
            api_url = '{}/api/v2/nodes/{}/clients'.format(broker_url, mqtt_node)

            try:
                r = requests.get(api_url,
                                 params={
                                     'page_size': mqtt_page_size,
                                     'curr_page': curr_page,
                                 },
                                 headers=mqtt_req_header,
                                 timeout=mqtt_req_timeout
                                 )

                r.raise_for_status()
                j = r.json()['result']
                total_pages = j['total_page']

                logger.debug('[{}] Total number of clients: {}'.format(broker_url, j['total_num']))
                logger.debug('[{}] Current page: {}/{}'.format(broker_url, j['current_page'], total_pages))

                for device_obj in j['objects']:
                    yield device_obj

                if curr_page < total_pages:
                    yield from fetch_device_info_from_mqtt_node(broker_url, mqtt_node, curr_page + 1)
            except Exception as e:
                logger.error("MQTT API (%s) 查詢失敗", broker_url, exc_info=True)
                raise e

        mqtt_device_status_list = []
        for broker_url in self._mqtt_brokers:
            broker_device = []
            for node_hostname in get_mqtt_node_hostname(broker_url):
                broker_device.extend(list(fetch_device_info_from_mqtt_node(broker_url, node_hostname)))
            logger.debug('[{}] Number of connected clients found: {}'.format(broker_url, len(broker_device)))

            mqtt_device_status_list.extend(broker_device)

        df = pd.DataFrame(mqtt_device_status_list)

        df = df[~df.client_id.str.contains('artichoke_postgresql')]
        df[['site_id', 'city_enc', 'channel', 'sniffer']] = df['client_id'].str.split('_', expand=True)
        df['mqtt_conn'] = 'online'  # MQTT 只會回傳當下 MQTT 還有連線的紀錄
        df = df[['site_id', 'sniffer', 'mqtt_conn']]

        return df

    def get_frp_node(self):
        """
        Args:
        Returns:
            (pd.DataFrame): 回傳 FRP 設備連線狀態 cols: site_id, sniffer, frp_conn, frp_remote_port
        """
        try:
            api_url = '{}{}'.format(self._frp_url, '/api/proxy/tcp')
            r = requests.get(api_url, auth=(self._frp_user, self._frp_pwd))
            r.raise_for_status()
            j = r.json()

            if j['code'] == 0:
                cols = ['name', 'status', 'last_start_time', 'last_close_time', 'conf.remote_port']
                j_proxies = j['proxies']

                if not j_proxies:
                    logger.debug("FRP API Response empty.")
                    return pd.DataFrame(columns=cols)

                df = pd.io.json.json_normalize(j_proxies)
                df = df[cols]

                # FRP Service 會在 deive name 後面加上 .io 字眼，例如: 1A02_Xinzhuang_TLW_08beac0cdb47.io
                # 這樣在跟其他資料會對不上，因此在這邊先將將結尾 .io 字樣去除
                df.loc[:, 'name'] = df['name'].apply(lambda s: s[:-3] if s.endswith('.io') else s)
                df[['site_id', 'city_enc', 'channel', 'sniffer']] = df['name'].str.split('_', expand=True)
                df.rename(columns={'status': 'frp_conn', 'conf.remote_port': 'frp_remote_port'}, inplace=True)
                df = df[['site_id', 'sniffer', 'frp_conn', 'frp_remote_port']]

                return df
            else:
                raise Exception('FRP Service API Error')
        except Exception as e:
            logger.error("FRP API 查詢失敗", exc_info=True)
            raise e

    def transfer_to_email_missing_record_format(self, df):
        sniffer_status_df = df.copy()

        # 將最後一筆時間與時間間距兩個資訊合併
        time_merge_setting = dict(
            rt_display=dict(display_time='rt', delay='rt_offset'),
            delivery_time_display=dict(display_time='delivery_time', delay='delivery_time_offset'),
            device_clock_display=dict(display_time='upload_gap', delay='last_correctly_dt_offset'),
        )

        def transfer_time(t):
            return '沒資料' if pd.isna(t) else t.strftime('%H:%M:%S')

        def transfer_delta_time(delta):
            delta_secs = delta.total_seconds()
            negative_flag = '-' if delta_secs < 0 else ''
            offset_secs = abs(delta_secs)
            t_hour = int(offset_secs // (60 * 60))  # hour
            t_min = int(offset_secs % (60 * 60) // 60)  # minute
            t_sec = int(offset_secs % 60)  # minute

            return '{}{:02}:{:02}:{:02}'.format(negative_flag, t_hour, t_min, t_sec)

        for target_col_name, setting in time_merge_setting.items():
            l = []
            for _, row in sniffer_status_df.iterrows():
                d = {}
                for k, col_name in setting.items():
                    if isinstance(row[col_name], datetime):
                        d[k] = transfer_time(row[col_name])
                    elif isinstance(row[col_name], timedelta):
                        d[k] = transfer_delta_time(row[col_name])
                    else:
                        raise Exception('Not Support type.')

                if target_col_name == 'device_clock_display' \
                        and row['rt'] <= row['upload_time'] <= row['delivery_time']:
                    l.append('{display_time}'.format(**d))
                else:
                    l.append('{display_time} ({delay})'.format(**d))

            sniffer_status_df[target_col_name] = l

        # 將 NAN 填上 Unknown. 其餘直接呈現
        ssh_col_name = list(filter(lambda s: s.endswith('result'), sniffer_status_df.columns.unique().tolist()))
        sniffer_status_df.fillna({col: 'Unknown' for col in ssh_col_name}, inplace=True)

        sniffer_status_df['ping-lost-ratio.result'] = sniffer_status_df['ping-lost-ratio.result'].apply(
            lambda s: s if s == 'Unknown' else f'{s}%')
        sniffer_status_df = sniffer_status_df['site_id,sname,sniffer,' \
                                              'device_clock_display,delivery_time_display,rt_display,' \
                                              'frp_conn,mqtt_conn,' \
                                              'redis-queue.result,wifi-signal.result,ping-lost-ratio.result'.split(',')]

        # Sort by site_id
        sniffer_status_df.sort_values('site_id', inplace=True)
        sniffer_status_df.rename(columns={
            'site_id': '代號',
            'sname': '門店名稱',
            'device_clock_display': '設備時鐘誤差多少/問題持續多久',
            'delivery_time_display': 'Delivery Time/Delay',
            'rt_display': 'Receive Time/Delay',
            'frp_conn': 'FRP conn.',
            'mqtt_conn': 'MQTT conn.',
            'redis-queue.result': 'Redis Queue(*)',
            'wifi-signal.result': 'Wi-FI Signal(*)',
            'ping-lost-ratio.result': 'Ping lost ratio(*)',
        }, inplace=True)

        if len(df) != len(sniffer_status_df):
            raise Exception('Transfer mail format should not cut any data.')

        return sniffer_status_df

    def transfer_to_email_position_format(self, df):
        sniffer_status_df = df.copy()
        sniffer_status_df = sniffer_status_df['site_id,sname,sniffer,sniffer_no,' \
                                              '安裝區域,安裝方式,is_released,union_sniffer,tel'.split(',')]
        # Sort by site_id
        sniffer_status_df.sort_values('site_id', inplace=True)
        del sniffer_status_df['site_id']

        sniffer_status_df.rename(columns={
            'sname': '門店名稱',
            'union_sniffer': '同門店 sniffer union',
            'sniffer_no': 'sniffer 天線編號',
            'tel': '門市電話',
        }, inplace=True)

        if len(df) != len(sniffer_status_df):
            raise Exception('Transfer mail format should not cut any data.')

        return sniffer_status_df

    def send_mail(self, title, content):
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

    def send_alert_mail(self, alert_sniffer_df, prefix_mail_title='[Alert]'):
        if alert_sniffer_df.empty:
            logger.info(f"There is no {prefix_mail_title} in this period.")
            return

        # email title format: [Alert-L1] 3 sniffer(s): TLW羅東店,TLW大墩店-商圈,...
        alert_site_name = alert_sniffer_df.sort_values('site_id').sname.unique().tolist()
        alert_sniffer_cnt = len(alert_sniffer_df)
        alert_mail_title = '{prefix_mail_title}{alert_sniffer_cnt} sniffer(s):{alert_top2_sname}{suffix}'.format(
            prefix_mail_title=prefix_mail_title,
            alert_sniffer_cnt=alert_sniffer_cnt,
            alert_top2_sname=','.join(alert_site_name[:2]),  # 去掉重複的名稱
            suffix=',...' if len(alert_site_name) > 2 else '',
        )

        email_sniffer_missing_record_df = self.transfer_to_email_missing_record_format(alert_sniffer_df)
        device_position_df = self.transfer_to_email_position_format(alert_sniffer_df)

        mail_body = '''
        {missing_record}
        <div>* 星字號欄位: 需透過網路連線到設備才能得知，當設備無法連線欄位會填上"Unknown".</div>
        <br/>
        <div>值日生資訊</div>
        <ul>
            <li>異常設備處理方式:<a href="{l1l2_rule_link}">L1/L2決策樹文件</a></li>
            <li>門店網路AP後台:<a href="{meraki_link}">Meraki 後台</a></li>
            <li>門店聯絡資訊:<a href="{contact_info_link}">有記錄的文件</a> or <a href="{contact_info_by_trplus_link}">TR+網站據點</a></li>
            <li>異常處理記錄文件:<a href="{alert_doc_link}">Alarm 人流異常記錄文件</a></li>
            <li>設備補充資訊:</li>
        </ul>
        {device_position}
        '''.format(
            # FIXME: l1/l2 rule 連結位置要改用正式的
            l1l2_rule_link='https://trgo.sharepoint.com/:x:/r/sites/internaltric1/EDT/Shared%20Documents/Artichoke_Maintain/SOP/%E7%B3%BB%E7%B5%B1%E7%9B%A3%E6%B8%AC%E8%99%95%E7%90%86/Alert-mail%20L1%20L2%20%E6%B1%BA%E7%AD%96%E6%A8%B9%E9%82%8F%E8%BC%AF%E8%88%87%E8%99%95%E7%90%86%E6%96%B9%E5%BC%8F.xlsx?d=w0e8df5aed1914317b6e4c51e6103865b&csf=1&web=1&e=8aAsh6',
            meraki_link='https://n240.meraki.com/',
            contact_info_by_trplus_link='https://www.trplus.com.tw/pages/store?brand=tlw',
            alert_doc_link='https://trgo.sharepoint.com/:x:/r/sites/internaltric1/EDT/Shared%20Documents/Artichoke_Maintain/Resource/Alert%20Mail%E8%99%95%E7%90%86%E7%B4%80%E9%8C%84.xlsx?d=w042f559065344b8f9496efa5c63abdf9&csf=1&web=1&e=LpB4eV',
            contact_info_link='https://trgo.sharepoint.com/:x:/r/sites/internaltric1/EDT/Shared%20Documents/Artichoke_Maintain/Resource/%E7%B6%AD%E9%81%8B%E7%AA%97%E5%8F%A3%E8%81%AF%E7%B5%A1%E6%96%B9%E5%BC%8F.xlsx?d=w6467b57507a84bc38fc05fa92c4a3b22&csf=1&web=1&e=sGRrPe',
            missing_record=email_sniffer_missing_record_df.to_html(
                index=False,
                justify='center',
            ),
            device_position=device_position_df.to_html(
                index=False,
                justify='center',
            ),
        )

        self.send_mail(alert_mail_title, mail_body)

    def collect_various_data(self, delivery_time_offset_thr, rt_offset_thr, clock_delay_thr):
        df = pd.DataFrame()

        # 1. 取得門店資料(site_id, sniffer, sname, union_sniffer, is_released)
        try:
            site_info_df = self.read_open_site_info(delivery_time_offset_thr,
                                                    self._check_sniffer,
                                                    self._site_type,
                                                    self._site_id,
                                                    self._ignore_site_list)

            logger.info('There are %s site(s) to be monitored.', len(site_info_df))
        except Exception as e:
            logger.error('無法連接資料庫')
            self.send_mail('[Alert!] No target clients information', 'Cannot access database<br/>{}'.format(e))
            raise e

        # 沒獲取到任何營業中的門店資訊
        if site_info_df.empty:
            logger.warning('No target clients to be monitored....')
            self.send_mail('[Alert!] No target clients information', 'Check database table "site_info"')
            return

        df = site_info_df

        # 2. 合併 rawdata 資訊(sniffer, rt, upload_time, rt_offset, delivery_time_offset, upload_gap)
        sniffer_last_rawdata_df = self.get_sniffer_last_rawdata_record_by_sniffer(
            site_info_df.sniffer.unique().tolist())
        sniffer_last_rawdata_df = sniffer_last_rawdata_df[['sniffer', 'rt', 'delivery_time', 'upload_time', 'rt_offset',
                                                           'delivery_time_offset', 'upload_gap']]
        df = df.merge(sniffer_last_rawdata_df, on=['sniffer'], how='left')

        # 3. 合併 MQTT 資訊 (site_id, sniffer, mqtt_conn)
        mqtt_client_df = self.get_mqtt_connected_status()
        logger.info('MQTT Service %s online device(s)', len(mqtt_client_df))
        df = df.merge(mqtt_client_df, on=['site_id', 'sniffer'], how='left')
        df.loc[df.mqtt_conn.isna(), 'mqtt_conn'] = 'offline'

        # 4. 合併 FRP 資訊(site_id, sniffer, frp_conn, frp_remote_port)
        frp_device_df = self.get_frp_node()
        logger.info('FRP Server %s online device(s) and %s offline device(s)',
                    len(frp_device_df.query("frp_conn == 'online'")),
                    len(frp_device_df.query("frp_conn == 'offline'")),
                    )
        df = df.merge(frp_device_df, on=['site_id', 'sniffer'], how='left')
        df.loc[df.frp_conn.isna(), 'frp_conn'] = 'offline'

        # 5. 最後一次設備時鐘正確時間
        device_last_clock_correctly_df = self.get_sniffer_last_rawdata_record_by_sniffer(
            df.sniffer.unique().tolist(), filter_device_clock_right=True)
        device_last_clock_correctly_df = device_last_clock_correctly_df[['sniffer', 'delivery_time_offset']]
        device_last_clock_correctly_df.rename(columns={'delivery_time_offset': 'last_correctly_dt_offset'},
                                              inplace=True)
        df = df.merge(device_last_clock_correctly_df, on=['sniffer'], how='left')

        # 6. ssh 進到設備抓資訊
        # SSH 這段時間跑很久，僅跑後續 L1/L2 會使用到的資訊
        l1_l2_error_case = df[
            (df.delivery_time_offset >= delivery_time_offset_thr) |  # DT 延遲超過指定條件
            (df.rt_offset >= rt_offset_thr) |  # RT 延遲超過指定條件
            (df.upload_gap.apply(abs) >= clock_delay_thr)  # 設備時間誤差超過指定條件
            ]

        l1_l2_error_case = l1_l2_error_case[(l1_l2_error_case.frp_conn == 'online')]
        device_info = SSHCommandLine.remote_device_fetch_information(
            l1_l2_error_case,
            self._frp_url,
            self._ssh_user,
            self._ssh_pwd,
            self._ssh_keypath,
        )
        df = df.merge(device_info, on=['sniffer'], how='left')

        return df

    def get_alert_severity_id_using_name(self, session, alert_severity: str, schemas: str = 'imtest'):
        """
        Get severity_id from table alert_severity_info.
        """
        sql_stx = f"""SELECT id FROM {schemas}.alert_severity_info WHERE severity_name = '{alert_severity}'"""
        result = session.execute(sql_stx)
        severity_id = result.fetchall()[0][0]
        return severity_id

    def combine_insert_alert_record_sql_syntax(self, alert_df: pd.DataFrame, alert_severity: str, schemas: str = 'imtest'):
        """
        1. Extract sniffer_id from dataframe.
        2. Combine sql syntax to insert records.
        """
        tz = pytz.timezone('Asia/Taipei')
        session = next(db_session(self._master_db_url))
        severity_id = self.get_alert_severity_id_using_name(session, alert_severity, schemas)
        session.close()
        value_list = []
        for _, row in alert_df.iterrows():
            alert_rawdata = """'{"site_id": "%s", "sname": "%s"}'""" % (row.site_id, row.sname)
            value_list.append(f"""('{severity_id}', '{row.sniffer}', '{datetime.now(tz)}', {alert_rawdata})""")
        sql_stx = f"""INSERT INTO {schemas}.alert_record VALUES {', '.join(value_list)};"""
        return sql_stx

    def save_alert_record_to_database(self, alert_df: pd.DataFrame, alert_severity: str, schemas: str = 'imtest'):
        """
        Save alert records to database.
        """
        if alert_df.empty:
            return
        sql_stx = self.combine_insert_alert_record_sql_syntax(alert_df, alert_severity, schemas)
        try:
            session = next(db_session(self._master_db_url))
            session.execute(sql_stx)
            session.commit()
        except Exception:
            logger.error("Insert alert record to database error.")
        finally:
            session.close()

    def decsion_l1_l2_tree(self, df, delivery_time_offset_thr, rt_offset_thr, clock_delay_thr):
        # 開始根據決策樹邏輯，將有異常的設備分類到 L1 or L2 case
        # 設備時間異常跑掉太久設備時間誤差(>= clock_delay_thr) 且 又持續一長段時間( >= delivery_time_offset_thr)
        device_clock_err_df = df[
            ((df.upload_gap.apply(abs) >= clock_delay_thr)
             & (df.last_correctly_dt_offset >= delivery_time_offset_thr))]
        no_rawdata_err_df = df[df.delivery_time.isna()]

        err_device_pool_df = df[
            (~df.index.isin(device_clock_err_df.index)) &  # 剔除已知時間問題
            (~df.index.isin(no_rawdata_err_df.index))  # 剔除沒三個月資料
            ]

        # 根據 DT 多久沒上傳拆分三組 (0~3, 3~20, 20~)
        dt_0_3_df = err_device_pool_df[('00:00:00' <= err_device_pool_df.delivery_time_offset)
                                       & (err_device_pool_df.delivery_time_offset < '00:03:00')]
        dt_3_20_df = err_device_pool_df[('00:03:00' <= err_device_pool_df.delivery_time_offset)
                                        & (err_device_pool_df.delivery_time_offset < delivery_time_offset_thr)]
        dt_20_df = err_device_pool_df[(delivery_time_offset_thr <= err_device_pool_df.delivery_time_offset)]

        # L2 Error case
        l2_err_df = pd.concat([
            dt_0_3_df[rt_offset_thr <= dt_0_3_df.rt_offset],  # 資料已經延遲超過20分鐘的情況，直接丟 L2
            dt_3_20_df[rt_offset_thr <= dt_3_20_df.rt_offset],  # 資料已經延遲超過20分鐘的情況，直接丟 L2
            dt_20_df[
                (dt_20_df['redis-queue.result'] > 0)  # Redis Queue 有值
                & (
                        (dt_20_df['wifi-signal.result'] < 46)  # WiFi 訊號強度小於 46
                        | (dt_20_df['ping-lost-ratio.result'] > 20)  # Ping 掉封包率大於 20(%)
                )
                ]
        ])

        # L1 Error case
        l1_err_df = pd.concat([
            no_rawdata_err_df,  # 沒 rawdata 的設備
            device_clock_err_df,  # 設備時間誤差飛掉的 case
            dt_20_df[~dt_20_df.index.isin(l2_err_df)],  # DT > 20 分鐘扣掉 L2 的情境(爛網的case)
        ])

        # For Ivy. 觀察哪些門店設備時鐘會出現延遲的 case (時間誤差 > 10 mins, 但僅持續一小段時間)
        l2_err_df = pd.concat([
            l2_err_df,
            err_device_pool_df[
                ((err_device_pool_df.upload_gap.apply(abs) >= clock_delay_thr)
                 & (err_device_pool_df.last_correctly_dt_offset < delivery_time_offset_thr))]
        ])
        l2_err_df.drop_duplicates(subset='sniffer', inplace=True)

        return l1_err_df, l2_err_df

    def run(self, delivery_time_offset_thr='00:20:00', rt_offset_thr='00:20:00', clock_delay_thr='00:10:00', *args,
            **kwargs):
        df = self.collect_various_data(delivery_time_offset_thr, rt_offset_thr, clock_delay_thr)
        l1_err_df, l2_err_df = self.decsion_l1_l2_tree(df, delivery_time_offset_thr, rt_offset_thr, clock_delay_thr)

        self.save_alert_record_to_database(l1_err_df, 'L1', 'public')
        self.save_alert_record_to_database(l2_err_df, 'L2', 'public')

        if self._send_email == 'true':
            self.send_alert_mail(l1_err_df, prefix_mail_title='[Alert-L1] ')
            self.send_alert_mail(l2_err_df, prefix_mail_title='[Alert-L2] ')
        else:
            logger.info("No need to send email, return.")


def combin_multi_setting(config_file='/worker/artichoke_base_service.ini', prog_parms_from_cmdline={}, *args,
                         **kwargs):
    def config_read(config_file: str, file_encoding: str = 'utf-8', *args, **kwargs):
        """ 讀取設定檔(.ini)

        Args:
            config_file(str): 設定檔路徑
            file_encoding(str): 設定檔的檔案編碼
        Returns:
            prog_parms(dict): 從設定檔中要用的資訊
        """
        prog_parms = dict()
        con = ConfigParser()
        con.read(config_file, encoding=file_encoding)

        if 'DATABASE' in con:
            prog_parms['master_db_url'] = con['DATABASE'].get('MASTER_URL', None)
            prog_parms['slave_db_url'] = con['DATABASE'].get('SLAVE_URL', None)

        if 'FRP' in con:
            prog_parms['frp_url'] = con['FRP'].get('URL', None)
            prog_parms['frp_user'] = con['FRP'].get('USER', None)
            prog_parms['frp_pwd'] = con['FRP'].get('PASSWORD', None)

        if 'MQTT' in con:
            prog_parms['mqtt_brokers'] = con['MQTT'].get('BROKERS', None)
            prog_parms['mqtt_api_token'] = con['MQTT'].get('API_TOKEN', None)

        if 'SSH' in con:
            prog_parms['ssh_user'] = con['SSH'].get('USERNAME', None)
            prog_parms['ssh_pwd'] = con['SSH'].get('PASSWORD', None)
            prog_parms['ssh_keypath'] = con['SSH'].get('KEYPATH', None)

        if 'SEND_EMAIL' in con:
            prog_parms['send_email'] = con['SEND_EMAIL'].get('FLAG', None)

        if 'RECIPIENTS' in con:
            prog_parms['mail_recipients'] = con['RECIPIENTS'].get('alert_report', None)
            prog_parms['mail_cc_recipients'] = con['RECIPIENTS'].get('alert_report_cc', None)

        if 'MAIL_SENDER' in con:
            prog_parms['mail_sender'] = con['MAIL_SENDER'].get('artichoke', 'artichoke@edt.testritegroup.com')

        # TODO: 如果 ini 存在但是這邊沒有設定的要加上警告
        return prog_parms

    logger.info('Loading "%s" config-file', config_file)
    if not os.path.isfile(config_file):
        logger.warning('The "%s" config-file not found.', config_file)

    prog_parms_from_config_file = config_read(config_file)
    prog_parms = dict()
    params_priority = [prog_parms_from_config_file, prog_parms_from_cmdline]
    for parms in params_priority:
        # 根據上述定義優先順序，將值非 None 慢慢蓋上
        prog_parms.update(dict(filter(lambda e: e[1] is not None, parms.items())))

    return prog_parms


def worker_send_missing_alarm():
    main()


def main():
    if not os.path.exists(LOG_FILE_PATH):
        os.makedirs(LOG_FILE_PATH)
    logging.config.dictConfig(LOGGING_CONFIG)

    prog_parms = combin_multi_setting()

    MonitorTask(**prog_parms).run(**prog_parms)


if __name__ == '__main__':
    main()
