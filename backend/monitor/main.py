
"""
Main function for artichoke monitor.

History:
2021/10/05 Created by Patrick
"""

import os
import subprocess
from subprocess import PIPE
from crontab import CronTab
import logging
import time
logger = logging.getLogger()


def start_cron_service():
    """Start the cron service"""
    svc_path = get_service_cmd_path()
    logger.info("Starting cron service...")

    cmds = [svc_path, 'printenv | grep -v "no_proxy" >> /etc/environment']
    try:
        for cmd in cmds:
            os.system(cmd)
    except subprocess.CalledProcessError as e:
        logger.error("Could not start cron service")
        logger.error(cmd)
        logger.error("stdout: {}".format(e.stdout.decode()))
        logger.error("stderr: {}".format(e.stderr.decode()))
    else:
        logger.info("Finished starting up cron service")


def get_service_cmd_path():
    """
    Retrieve the full path for the service command
    """
    logger.info("Getting service command path...")
    cmd = ["which", "crond"]
    try:
        comp_proc = subprocess.run(cmd, check=True, stdout=PIPE, stderr=PIPE)
        svc_path = comp_proc.stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        logger.error("Error running \"which crond\"")
        logger.error("stdout: {}".format(e.stdout.decode()))
        logger.error("stderr: {}".format(e.stderr.decode()))
        raise
    logger.info("Finished getting service command path")
    return svc_path


def setup_cron_job():
    """
    Set up monitor cron job
    """
    logger.info("Setting up monitor cron job")
    try:
        with CronTab(user="root") as cron:
            job = cron.new(command="/usr/local/bin/python /monitor/monitor_module.py")
            job.setall('*/10 10-21 * * *')
    except Exception as e:
        logger.error("Error setting up monitor cron job")
        logger.error(f"Exception details: {e}")
        raise
    else:
        logger.info("Finished setting up monitor cron job")


def setup_monitor_service():
    """
    Set up db_routine crontab.
    """
    start_cron_service()
    setup_cron_job()


def setup_logger(logger):
    """Logger format setting"""
    LOG_MSG_FORMAT = "[%(asctime)s][%(levelname)s] %(module)s %(funcName)s(): %(message)s"
    LOG_FILENAME = "main.log"
    LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=logging.INFO, format=LOG_MSG_FORMAT, datefmt=LOG_TIME_FORMAT, filename=LOG_FILENAME)


def main():
    """
    Worker main loop
    """
    setup_logger(logger)
    setup_monitor_service()
    while True:
        time.sleep(86400)
        pass


if __name__ == "__main__":
    main()
