import os
from typing import Generator
import time
from sqlalchemy import create_engine
from datetime import date, datetime, timedelta
from sqlalchemy.orm import sessionmaker, Session
import logging
logger = logging.getLogger()


def db_session(engine) -> Generator[Session, None, None]:
    """
    Return database session.

    This is a wrapper of sessionmaker.
    It is convenience to execute sql statement, if that is necessary.
    For db health-checking example:
        db = get_db_session()
        res = db.execute('select 1')
        # response 1 from db means that the db is working well
        res.fetchall()
        res.close()
    """
    make_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = make_session()
    try:
        yield db
    except Exception as e:
        db.rollback()


class RawdataInfo:
    def __init__(self, rt: datetime, sa: str):
        self._rt = rt
        self._sa = sa

    def get_rt(self):
        return self._rt

    def get_sa(self):
        return self._sa


class SiteWithSnifferInfo:

    OUI_LIST = ['SamsungE', 'Htc', 'HTC', 'SonyMobi', 'AsustekC', 'ASUSTekC', 'Guangdon', 'XiaomiCo', 'LgElectr', 'LGElectr',
                'HuaweiTe', 'Zte', 'zte', 'MurataMa', 'vivoMobi', 'HMDGloba', 'Motorola', 'RealmeCh', 'Sony']

    def __init__(self, site_info: tuple, start_date: date, end_date: date, conn, sp_dt=False):
        self._site_id, open_hour, closed_hour, open_hour_wend, closed_hour_wend, \
        self._alg_version, self._android_rate, self._wifi_rate, self._alg_params, self._sniffer_id, self._rssi = site_info
        self._unique_cnames, self._random_cnames = list(), list()
        self._unique_period_counts, self._random_period_counts = [0]*24, [0]*24
        self._conn = conn
        self._start_date = start_date
        self._end_date = end_date
        self._sp_dt = sp_dt
        self._date_now = datetime.now() if not self._sp_dt else self._start_date
        if self._date_now.weekday() < 5:
            self._open_hour, self._closed_hour = open_hour, closed_hour
        else:
            self._open_hour, self._closed_hour = open_hour_wend, closed_hour_wend

    def main_proc(self):
        self._insert_rawdata_lists()
        self._calculate_hour_counts()
        self._upsert_to_database()

    def _get_result(self):
        l = []
        for s, rssi in zip(self._sniffer_id, self._rssi):
            sql = f"""
                SET SESSION time zone 'Asia/Taipei';
                SELECT rt, sa, cname, pkt_type FROM rawdata_{s}
                WHERE rssi >= {rssi}
                AND rt BETWEEN '{self._start_date}' AND '{self._end_date}' ORDER BY rt
            """
            res = self._conn.execute(sql)
            l.append(res.fetchall())
        return l

    def _insert_rawdata_lists(self):
        all_rawdata_sniffers = self._get_result()
        excluded_samsung_random_rawdata = self._exclude_samsung_random_rawdata(all_rawdata_sniffers)
        for raw in excluded_samsung_random_rawdata:
            rt, sa, cname, pkt_type = raw
            if cname in self.OUI_LIST:
                self._unique_cnames.append(RawdataInfo(rt, sa))
            elif cname in ("Google_Random", None) and (pkt_type == 0) and len(self._sniffer_id) == 1:
                if self._alg_version == 1:
                    # Algorithm ver1 needn't deal with random cnames.
                    continue
                self._random_cnames.append(RawdataInfo(rt, sa))
        if len(self._sniffer_id) > 1:
            self._unique_cnames = sorted(self._unique_cnames, key=lambda s: s.get_rt())
        sa_set, real_unique_devices = set(), list()
        for raw in self._unique_cnames:
            if raw.get_sa() not in sa_set:
                real_unique_devices.append(raw)
                sa_set.add(raw.get_sa())
        self._unique_cnames = real_unique_devices

    def _exclude_samsung_random_rawdata(self, all_rawdata_sniffers):
        """
        all_rawdatas format: [(rt, sa, cname, pkytype)]

        The purpose of this function is to exclude samsung random rawdata.
        This function will do the following tasks:
        1. Sort all rawdatas by sa and rt.
        2. Filter all rawdata by pkt_type = 0.
        3. Group rawdata by prefix of sa.
        4. For each prefix group, find the samsung random sa case.
        5. Delete all samsung random sa in rawdata.
        """
        all_rawdatas = list()
        for rd in all_rawdata_sniffers:
            all_rawdatas.extend(rd)
        all_rawdatas = sorted(all_rawdatas, key=lambda s: (s[1], s[0])) # s[1]: sa, s[0]: rt
        excluded_random_rawdatas = all_rawdatas[:]
        excluded_random_rawdatas = [rw for rw in excluded_random_rawdatas if rw[2] in self.OUI_LIST and rw[3] == 0]
        mac_addr_prefix = set(map(lambda x:x[1][:6], excluded_random_rawdatas))
        group_by_sa = [[y for y in excluded_random_rawdatas if y[1][:6] == x] for x in mac_addr_prefix]
        final_excluded_sa = list()
        for value, sa in zip(mac_addr_prefix, group_by_sa):
            mac_addr_list = [s[1] for s in sa]
            excluded_sa = [
                mac_addr for mac_addr in mac_addr_list
                if mac_addr_list.count(mac_addr) > len(self._sniffer_id)
            ]
            candidate_exclude_sas = [s for s in mac_addr_list if s not in excluded_sa]
            sa = [s for s in sa if s[1] in candidate_exclude_sas]
            for idx, s in enumerate(sa):
                try:
                    if sa[idx+4][0] - s[0] <= timedelta(minutes=20):
                        final_excluded_sa.extend(candidate_exclude_sas)
                        break
                except IndexError:
                    break
        return [rw for rw in all_rawdatas if rw[1] not in final_excluded_sa]

    def _calculate_hour_counts(self):
        for raw in self._unique_cnames:
            self._unique_period_counts[raw.get_rt().hour] += 1
        if self._alg_version == 1:
            # Algorithm ver1 needn't deal with random cnames.
            return
        if len(self._sniffer_id) == 1:
            for raw in self._random_cnames:
                self._random_period_counts[raw.get_rt().hour] += 1
        else:
            self._clear_random_cnames_for_multiple_sniffers()

    def _get_final_customer_counts(self):
        if self._alg_version == 1:
            # Algorithm ver1 needn't deal with random cnames.
            return [i / (self._android_rate*self._wifi_rate) for i in self._unique_period_counts]
        res = list()
        model_slope, manual_slope, model_intercept, model_upper_limit = self._alg_params.values()
        for unique, random in zip(self._unique_period_counts, self._random_period_counts):
            m = min(random, model_slope*unique+model_upper_limit)
            final_count = (max(0, (m-model_intercept)/manual_slope) + unique) / (self._android_rate*self._wifi_rate)
            res.append(round(final_count))
        return res

    def _get_output_subsql(self):
        output_list = list()
        ts = datetime.combine(self._start_date, datetime.min.time())
        if self._sp_dt:
            # Cover records before, use 22:00 as time.
            end_hour, hour_shift = 22, 0
        elif self._closed_hour.hour >= self._date_now.hour:
            # Means the site hasn't closed yet.
            end_hour = self._date_now.hour
            hour_shift = 1 if self._date_now.minute == 0 else 0
        else:
            end_hour = self._closed_hour.hour
            hour_shift = 1 if self._closed_hour.minute == 0 else 0
        for idx, count in enumerate(self._get_final_customer_counts()):
            if self._open_hour.hour <= idx <= end_hour - hour_shift:
                output_list.append(f"('{self._site_id}', '{ts}', {count})")
            ts += timedelta(hours=1)
        return ",".join(output_list)

    def _upsert_to_database(self):
        output_str = self._get_output_subsql()
        if not output_str:
            return
        sql = f"""SET session time zone 'Asia/Taipei';
            INSERT INTO customer_count VALUES {output_str} ON CONFLICT (site_id, ts_hour) DO UPDATE SET count = EXCLUDED.count
        """
        sql = sql.replace('"', "")
        self._conn.execute(sql)
        self._conn.commit()

    def _clear_random_cnames_for_multiple_sniffers(self):
        sub_sql_a, sub_sql_b = self._get_sub_sql_stmt_for_random_count()
        sql = f"""SET session time zone 'Asia/Taipei';
            SELECT date_part('hour', coalesce(a.rt, b.rt))::int as time,
                   count(1) AS AR_pkts -- Total
            FROM
            (
                {sub_sql_a}
            ) a
            FULL JOIN
            (
                {sub_sql_b}
            ) b
            ON a.sa = b.sa
            AND a.rt - b.rt BETWEEN interval '-00:01' AND interval '00:01'
            GROUP BY 1
            ORDER BY 1
        """
        res = self._conn.execute(sql)
        result = res.fetchall()
        for idx, random_count in result:
            self._random_period_counts[idx] = random_count

    def _get_sub_sql_stmt_for_random_count(self):

        template = """
            SELECT rt, sa FROM public.rawdata_{sniffer}
            WHERE rt BETWEEN '{start_date}' AND '{end_date}'
            AND rssi BETWEEN {rssi} AND 0
            AND pkt_type = 0
            AND (cname IS NULL or cname = 'Google_Random')
        """
        return [template.format(sniffer=sniffer, start_date=self._start_date, end_date=self._end_date, rssi=rssi)
            for sniffer, rssi in zip(self._sniffer_id, self._rssi)
        ]


def setup_logger(logger):
    """Logger format setting"""
    LOG_MSG_FORMAT = "[%(asctime)s][%(levelname)s] %(module)s %(funcName)s(): %(message)s"
    LOG_FILENAME = "worker.log"
    LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=logging.INFO, format=LOG_MSG_FORMAT, datefmt=LOG_TIME_FORMAT, filename=LOG_FILENAME)


def worker_run_db_routine(specific_date: str):
    setup_logger(logger)
    engine = create_engine(os.environ['db_url'])
    conn = next(db_session(engine))
    res = conn.execute("""
    SET session time zone 'Asia/Taipei';
    SELECT si_i.site_id, si_i.open_hour, si_i.closed_hour, si_i.open_hour_wend, si_i.closed_hour_wend,
           si_i.alg_version, si_i.android_rate, si_i.wifi_rate, si_i.alg_params, sn_i.sniffer_id, sn_i.rssi
           FROM site_info AS si_i
           INNER JOIN (SELECT site_id, array_agg(sniffer_id) AS sniffer_id, array_agg(rssi) AS rssi FROM sniffer_info
                       WHERE is_active GROUP BY site_id)
           AS sn_i ON si_i.site_id = sn_i.site_id
    """)
    a = res.fetchall()
    l = []
    dt = datetime.strptime(specific_date, '%Y-%m-%d').date()
    for i in a:
        l.append(SiteWithSnifferInfo(i, dt, dt+timedelta(days=1), conn, sp_dt=True))
    for x in l:
        x.main_proc()
    conn.close()


def worker_run_db_routine_one_site(specific_date: str, site_id: str):
    setup_logger(logger)
    engine = create_engine(os.environ['db_url'])
    conn = next(db_session(engine))
    res = conn.execute(f"""
    SET session time zone 'Asia/Taipei';
    SELECT si_i.site_id, si_i.open_hour, si_i.closed_hour, si_i.open_hour_wend, si_i.closed_hour_wend,
           si_i.alg_version, si_i.android_rate, si_i.wifi_rate, si_i.alg_params, sn_i.sniffer_id, sn_i.rssi
           FROM site_info AS si_i
           INNER JOIN (SELECT site_id, array_agg(sniffer_id) AS sniffer_id, array_agg(rssi) AS rssi FROM sniffer_info
                       WHERE is_active GROUP BY site_id)
           AS sn_i ON si_i.site_id = sn_i.site_id
    WHERE si_i.site_id = '{site_id}'
    """)
    site_info = res.fetchone()
    dt = datetime.strptime(specific_date, '%Y-%m-%d').date()
    proc = SiteWithSnifferInfo(site_info, dt, dt+timedelta(days=1), conn, sp_dt=True)
    proc.main_proc()
    conn.close()


if __name__ == '__main__':
    setup_logger(logger)
    engine = create_engine(os.environ['db_url'])

    start_time = time.time()
    conn = next(db_session(engine))
    res = conn.execute("""
    SET session time zone 'Asia/Taipei';
    SELECT si_i.site_id, si_i.open_hour, si_i.closed_hour, si_i.open_hour_wend, si_i.closed_hour_wend,
           si_i.alg_version, si_i.android_rate, si_i.wifi_rate, si_i.alg_params, sn_i.sniffer_id, sn_i.rssi
           FROM site_info AS si_i
           INNER JOIN (SELECT site_id, array_agg(sniffer_id) AS sniffer_id, array_agg(rssi) AS rssi FROM sniffer_info
                       WHERE is_active GROUP BY site_id)
           AS sn_i ON si_i.site_id = sn_i.site_id
    """)
    a = res.fetchall()
    l = []
    for i in a:
        l.append(SiteWithSnifferInfo(i, date.today(), date.today()+timedelta(days=1), conn))
    for x in l:
        x.main_proc()
    end_time = time.time()
    conn.close()
    logger.info(f"Execution time: {end_time-start_time}")
