
"""
Main function for artichoke worker.

History:
2021/08/05 Created by Patrick
"""
import os
import sys
import time
import asyncio
import subprocess
from subprocess import PIPE
from crontab import CronTab
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
logger = logging.getLogger()


@contextmanager
def session_scope():
    """
    Yield a session
    """
    db_session = session_maker()
    try:
        yield db_session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


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


def setup_db_routine_cron_job():
    """
    Set up log cleaning cron job
    """
    logger.info("Setting up db routine cron job")
    try:
        with CronTab(user="root") as cron:
            job = cron.new(command="/usr/local/bin/python /worker/worker_tmp_alg.py")
            job.setall('5,15,25,35,45,55 10-21 * * *')
    except Exception as e:
        logger.error("Error setting up log cleaning cron job")
        logger.error(f"Exception details: {e}")
        raise
    else:
        logger.info("Finished setting up log cleaning cron job")


def db_routine_setup():
    """
    Set up db_routine crontab.
    """
    start_cron_service()
    setup_db_routine_cron_job()


def start_rq_worker():
    """
    Run rq server.
    """
    os.system("rq worker -s")


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
    db_routine_setup()
    start_rq_worker()


if __name__ == "__main__":
    main()
