"""
Script for changing site open & close hour.

This script import the excel named 'change_site_info.xlsx' as DataFrame.
Then update all infos in DataFrame to database.

History:
2021/05/17 Created by Patrick
"""

import pandas as pd
import click
from configparser import ConfigParser
from sqlalchemy import create_engine
import logging
import logging.config

logger = logging.getLogger(__name__)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
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
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    }
}
logging.config.dictConfig(LOGGING_CONFIG)


def update_site_info(engine, df_site_info: pd.DataFrame) -> None:
    for _, j in df_site_info.iterrows():
        sql = f"""
            UPDATE site_info
            SET open_hour = '{j.open_hour}',
            closed_hour = '{j.closed_hour}',
            open_hour_wend = '{j.open_hour_wend}',
            closed_hour_wend = '{j.closed_hour_wend}'
            WHERE site_id = '{j.site_id}'
        """
        engine.execute(sql)
        logger.info(f"site_id: {j.site_id} update open & close hour success.")


def get_db_url(artichoke_base_service_config_file_path: str) -> str:
    """
    Get Database Url from local config.
    """
    config = ConfigParser()
    config.read([artichoke_base_service_config_file_path])
    db_url = config['ARTICHOKE']['DB_URL_ADMIN']
    return db_url


if __name__ == '__main__':
    @click.command()
    @click.option('--artichoke_base_service_config_file_path', default='./config/artichoke_base_service.ini', help='請填寫 artichoke_base_service.ini 檔案位置')
    @click.option('--site_info_file_path', default='change_site_info.xlsx', help='site_info_file_path')

    def run(artichoke_base_service_config_file_path, site_info_file_path):
        db_url = get_db_url(artichoke_base_service_config_file_path)
        df_site_info = pd.read_excel(site_info_file_path)
        engine = create_engine(db_url)
        update_site_info(engine, df_site_info)

    run()
