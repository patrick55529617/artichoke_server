#!/usr/bin/env python
# coding: utf-8

import paramiko
import json  
from urllib import request
import pandas as pd
import datetime
import time
from sqlalchemy import create_engine
import sys

LOCAL_PRIVATE_KEY_PATH =  # 請填寫電腦存放 private key 的路徑
FRP_HOST = '10.101.2.108'
SSH_USERNAME = 'edt'
SUDO_PWD =   # 請填寫 sudo 的密碼，如不知道請詢問其他同事夥伴
OUTPUT_PATH = './'
DB_USER = 'artichoke'
DB_PWD =   # 請填寫 db(10.101.2.19) user : artichoke 的密碼，如不知道請詢問其他同事夥伴
FRP_USER = 'admin'
FRP_PWD =   # 請填寫 frp user : admin 的密碼，如不知道請詢問其他同事夥伴

print(f"""
============================================================
= Load config
============================================================
LOCAL_PRIVATE_KEY_PATH : {LOCAL_PRIVATE_KEY_PATH}
FRP_HOST               : {FRP_HOST}
SSH_USERNAME           : {SSH_USERNAME}
SUDO_PWD               : {SUDO_PWD}
OUTPUT_PATH            : {OUTPUT_PATH}
DB_USER                : {DB_USER}
DB_PWD                 : {DB_PWD}
FRP_USER               : {FRP_USER}
FRP_PWD                : {FRP_PWD}



""")

db_url='postgresql+psycopg2://{}:{}@10.101.2.19/artichoke'.format(DB_USER,DB_PWD)
engine = create_engine(db_url)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(LOCAL_PRIVATE_KEY_PATH)

sql = """
WITH site_infos AS (
	SELECT *
	FROM site_info
	WHERE site_id='1A01'
)

SELECT pg_get_functiondef(oid) AS func_def
FROM pg_proc
WHERE proname IN (
	SELECT func[1]
	FROM site_infos
);
"""

# 抓取 FRP 連線清單

url = 'http://10.101.2.108:7500/api/proxy/tcp'
top_level_url = 'http://10.101.2.108:7500'
frp_user = FRP_USER
frp_pwd = FRP_PWD

password_mgr = request.HTTPPasswordMgrWithDefaultRealm()
password_mgr.add_password(None, top_level_url, frp_user, frp_pwd)
handler = request.HTTPBasicAuthHandler(password_mgr)
opener = request.build_opener(handler)
response = opener.open(url)
data = response.read().decode("utf-8")
frpdata = json.loads(data)

artichoke_dev_network_info = []
retry_wait = 1

ssh.close()
for afrp_info in frpdata['proxies']:
    if afrp_info['conf'] != None:
        try:
            print(afrp_info['conf'])

            conn_port = afrp_info['conf']['remote_port']
            ssh.connect(hostname=FRP_HOST, username=SSH_USERNAME, pkey=key, port=conn_port)

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('nmcli dev show | grep wlx')
            dev_name = ssh_stdout.read().decode("utf-8").split(':')[1].strip()

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('systemctl is-active picofssd')
            ups_is_active = ssh_stdout.read().decode("utf-8")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f'nmcli dev show "{dev_name}"')
            network_cfg = ssh_stdout.read().decode("utf-8")

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"sudo cat /etc/NetworkManager/system-connections/101 | grep 'auto'",get_pty=True)
            ssh_stdin.write(f'{SUDO_PWD}\n')
            ssh_stdin.flush()
            ssh_stdout.readline()
            network_101_cfg = ssh_stdout.read().decode("utf-8")

            if 'auto' in network_101_cfg:
                network_101_cfg = 'DHCP'
            else:
                network_101_cfg = 'MANUAL'

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"sudo cat /etc/NetworkManager/system-connections/102 | grep 'auto'",get_pty=True)
            ssh_stdin.write(f'{SUDO_PWD}\n')
            ssh_stdin.flush()
            ssh_stdout.readline()
            network_102_cfg = ssh_stdout.read().decode("utf-8")

            if 'auto' in network_102_cfg:
                network_102_cfg = 'DHCP'
            else:
                network_102_cfg = 'MANUAL'

            ssh.close()
            artichoke_dev_network_info.append({
                'frp_config' : afrp_info['conf'],
                'network_cfg' : network_cfg,
                'network_101_cfg':network_101_cfg,
                'network_102_cfg':network_102_cfg,
                'ups_is_active':ups_is_active
            })
            print(f"{network_cfg}network_101_cfg : {network_101_cfg}\nnetwork_102_cfg : {network_102_cfg}\n")
            
        except:
            print("Unexpected error:", sys.exc_info()[0])
        
tmp_df = pd.DataFrame(artichoke_dev_network_info)
tmp_df['host'] = tmp_df.apply(lambda x : x['frp_config']['proxy_name'][:-3], axis =1)
tmp_df['site_id'] = tmp_df.apply(lambda x : x['host'].split('_')[0], axis =1)
tmp_df['sniffer'] = tmp_df.apply(lambda x : x['host'].split('_')[-1:][0], axis =1)

tmp_df['network_101_cfg'] = tmp_df.apply(lambda x : x['network_101_cfg'], axis =1)
tmp_df['network_102_cfg'] = tmp_df.apply(lambda x : x['network_102_cfg'], axis =1)


def parse_network_cfg(network_cfg_array):
    if len(network_cfg_array) > 7:
        tokens = network_cfg_array[7].split(':') 
        
        if len(tokens) > 1 :
            return tokens[1].strip()
        else :
            return 'None'
    else:
        return 'None'

def parse_network_cfg_wifi_mac(network_cfg_array):
    if len(network_cfg_array) > 2:
        return network_cfg_array[2].split('HWADDR:')[1].strip()
    else:
        return 'None'

def parse_network_cfg_gateway(network_cfg_array):
    if len(network_cfg_array) > 8:
        return network_cfg_array[8].split(':')[1].strip()
    else:
        return 'None'

def parse_network_cfg_conn_ssid(network_cfg_array):
    if len(network_cfg_array) > 5:
        return network_cfg_array[5].split(':')[1].strip()
    else:
        return 'None'
    
def parse_network_cfg_dns(network_cfg_array):
    if len(network_cfg_array) > 1:
        dns_list = []
        for data in network_cfg_array:
            data_token = data.split(':')
            if len(data_token) > 1:
                key = data_token[0].strip()
                val = data_token[1].strip()
                if 'DNS' in key:
                    dns_list.append(val)
        
        return ','.join(dns_list)
    else:
        return 'None'

    
tmp_df['ip'] = tmp_df.apply(lambda x : parse_network_cfg(x['network_cfg'].split('\n')), axis = 1)
tmp_df['mac'] = tmp_df.apply(lambda x : parse_network_cfg_wifi_mac(x['network_cfg'].split('\n')), axis = 1).replace(':','')
tmp_df['gateway'] = tmp_df.apply(lambda x : parse_network_cfg_gateway(x['network_cfg'].split('\n')), axis = 1)
tmp_df['conn_ssid'] = tmp_df.apply(lambda x : parse_network_cfg_conn_ssid(x['network_cfg'].split('\n')), axis = 1)
tmp_df['DNS'] = tmp_df.apply(lambda x : parse_network_cfg_dns(x['network_cfg'].split('\n')), axis = 1)
tmp_df['mac'] = tmp_df.apply(lambda x: x['mac'].replace(':',''),axis=1)

artichoke_device_df = tmp_df
tmp_modify_df = artichoke_device_df[['site_id','sniffer','mac','host','ip','gateway','DNS','network_101_cfg','network_102_cfg','conn_ssid','ups_is_active']]

sql = """
SELECT *
FROM site_info
"""

site_df = pd.read_sql(sql,engine)
tmp_df = site_df

def get_site_name(site_id):
    format_site_id = site_id.split('-')[0]
    tmp_result = tmp_df[tmp_df['site_id'] == format_site_id]
    
    if len(tmp_result) > 0:
        return tmp_result['sname'].iloc[0]
    
    return 'None'

now = datetime.datetime.now()
now_str = now.strftime("_%Y-%m-%d_%H%M%S")

tmp_modify_df['門店'] = tmp_modify_df.apply(lambda x : get_site_name(x['site_id']), axis=1)
tmp_modify_df = tmp_modify_df.sort_values(['site_id'],ascending =True)
tmp_modify_df[['門店','site_id','sniffer','mac','host','ip','gateway','DNS','network_101_cfg','network_102_cfg','conn_ssid','ups_is_active']].to_excel(f'{OUTPUT_PATH}/Artichoke_網路設定清單_{now_str}.xlsx')




