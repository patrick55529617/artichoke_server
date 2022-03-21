import paramiko
import json  
from urllib import request
import pandas as pd
import time
import datetime
import logging
import configparser
import pathlib
import click

config_file_path = './dump_device_info.ini'
print("""
############################################################
Loading config
############################################################
""")
print('Load config path : {}'.format(config_file_path))
config = configparser.ConfigParser()
config.read_file(open(config_file_path))

KEYPATH = config['SSH']['KEYPATH']
REMOTEHOST = config['FRP']['REMOTEHOST']
USERNAME = config['FRP']['USERNAME']
PORT = config['FRP']['PORT']
PWD = config['FRP']['PWD']
LOG_PATH = config['LOG']['LOG_PATH']

print("""
KEYPATH : {KEYPATH}
REMOTEHOST : {REMOTEHOST}
USERNAME : {USERNAME}
PORT : {PORT}
LOG_PATH : {LOG_PATH}
""".format(KEYPATH=KEYPATH,REMOTEHOST=REMOTEHOST,USERNAME=USERNAME,PORT=PORT,PWD=PWD,LOG_PATH=LOG_PATH))

#
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(KEYPATH)

if __name__ == '__main__':
	@click.command()
	@click.option('-p', '--port', default=None, help='frp port. e.g. 9999')
	def main(port=None, **kwargs):
		global PORT
		
		if port is not None :
			PORT = port

		print('## Start process...')

		ssh.connect(hostname=REMOTEHOST, username=USERNAME, pkey=key, port=PORT)

		now = datetime.datetime.now()
		now_str = now.strftime("_%Y-%m-%d_%H%M%S")

		# 抓取 IFNAME
		print('Check network interface...')
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f'nmcli dev show | grep wlx')
		IFNAME = ssh_stdout.read().decode("utf-8").split(':')[1].strip()
		IFNAME

		# 設備資訊
		# boot
		print('Check device boot info...')
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('uptime')
		boot_info = ssh_stdout.read().decode("utf-8")

		# host
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('hostname')
		host_info = ssh_stdout.read().decode("utf-8")
		    
		# rtc
		print('Check device rtc...')

		retry_wait = 1
		rtc_info = ''

		tmp_info = ''
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('sudo journalctl | grep "Booting Linux\|systemd-timesyncd\|Time has been changed"',get_pty=True)
		ssh_stdin.write(f'{PWD}\n')
		ssh_stdin.flush()
		while tmp_info == '':
		    tmp_info = ssh_stdout.read().decode("utf-8")
		    if tmp_info == '':
		        time.sleep(retry_wait)
		    else:
		        rtc_info = rtc_info + tmp_info

		rtc_info = rtc_info.replace(f'{PWD}','')
		rtc_info_filter_noise = ''
		for line in rtc_info.splitlines():
		    if not line.startswith('[sudo]'):
		        rtc_info_filter_noise += line
		        rtc_info_filter_noise += '\n'
		rtc_info = rtc_info_filter_noise
		        
		# 網路資訊
		print('Check network environment...')

		# nmcli -f SSID,BSSID,SIGNAL,BARS dev wifi list ifname
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f'nmcli -f ACTIVE,SSID,BSSID,CHAN,SIGNAL,BARS dev wifi list ifname "{IFNAME}"')
		# ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f'nmcli dev wifi list ifname "{IFNAME}"')
		wifi_strength_info = ssh_stdout.read().decode("utf-8")

		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f'nmcli dev show "{IFNAME}"')
		network_cfg = ssh_stdout.read().decode("utf-8")

		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"sudo cat /etc/NetworkManager/system-connections/101 | grep 'auto'",get_pty=True)
		ssh_stdin.write(f'{PWD}\n')
		ssh_stdin.flush()
		ssh_stdout.readline()
		network_101_cfg = ssh_stdout.read().decode("utf-8")

		if 'auto' in network_101_cfg:
		    network_101_cfg = 'DHCP'
		else:
		    network_101_cfg = 'MANUAL'

		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(f"sudo cat /etc/NetworkManager/system-connections/101 | grep 'auto'",get_pty=True)
		ssh_stdin.write(f'{PWD}\n')
		ssh_stdin.flush()
		ssh_stdout.readline()
		network_102_cfg = ssh_stdout.read().decode("utf-8")

		if 'auto' in network_102_cfg:
		    network_102_cfg = 'DHCP'
		else:
		    network_102_cfg = 'MANUAL'

		# 服務資訊
		print('Check service environment...')

		# docker 
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo docker ps",get_pty=True)
		ssh_stdin.write(f'{PWD}\n')
		ssh_stdin.flush()
		ssh_stdout.readline()
		ssh_stdout.readline()
		docker_run_info = ssh_stdout.read().decode("utf-8")

		# local mqtt
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo docker exec -it redis redis-cli --bigkeys",get_pty=True)
		ssh_stdin.write(f'{PWD}\n')
		ssh_stdin.flush()
		ssh_stdout.readline()
		ssh_stdout.readline()
		mqtt_info = ssh_stdout.read().decode("utf-8")

		# mqtt conn
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('netstat -ntp | grep 1883')
		mqtt_conn_info = ssh_stdout.read().decode("utf-8")

		# UPS
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("systemctl status picofssd",get_pty=False)
		ups_info = ssh_stdout.read().decode("utf-8")
		if ups_info == '':
		    ups_info = ssh_stderr.read().decode("utf-8")

		# cron job
		ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("sudo crontab -l",get_pty=True)
		ssh_stdin.write(f'{PWD}\n')
		ssh_stdin.flush()
		ssh_stdout.readline()
		ssh_stdout.readline()
		cron_info = ssh_stdout.read().decode("utf-8")
		cron_info_filter_comment = ''
		for line in cron_info.splitlines():
		    if not line.startswith('#'):
		        cron_info_filter_comment += line
		        cron_info_filter_comment += '\n'
		cron_info = cron_info_filter_comment

		device_log = f"""
##################################################
## 設備資訊
##################################################
>> Host :
{host_info}
>> 開機時間:
{boot_info}
>> RTC status:
{rtc_info}

##################################################
## 設備服務資訊
##################################################
>> Cron job:
{cron_info}
>> Docker status:
{docker_run_info}
>> MQTT conn status:
{mqtt_conn_info}
>> MQTT data status:
{mqtt_info}
>> UPS status:
{ups_info}

##################################################
## 設備網路資訊
##################################################
>> 網路設定抓取方式:
{network_101_cfg}

>> 網路設定 :
{network_cfg}

>> Wifi 強度與連線 :
{wifi_strength_info}
		"""

		print(device_log)
		with open(f"{LOG_PATH}/{host_info.strip()}_device_dump_{now_str}.log", "w") as text_file:
		    print(device_log, file=text_file)
		    
		ssh.close()

	main()
