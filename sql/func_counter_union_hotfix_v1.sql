-- FUNCTION: public.counter_union_hotfix_v1(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision)

-- DROP FUNCTION public.counter_union_hotfix_v1(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision);

CREATE OR REPLACE FUNCTION public.counter_union_hotfix_v1(
	_antenna_1 text,
	_rssi_1 integer,
	_antenna_2 text,
	_rssi_2 integer,
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	),
	_android_oui character[] DEFAULT taiwan_android_oui(
	),
	_android_ratio double precision DEFAULT 0.55,
	_wifi_ratio double precision DEFAULT 0.66)
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

DECLARE
start_time timestamptz := date_trunc('day', _timefrom);
end_time timestamptz := date_trunc('day', _timeto) + interval '1 day';

BEGIN
set time zone 'Asia/Taipei';
RETURN QUERY EXECUTE
    format('
		WITH SAMSUNG_CANDIDATE AS(
			SELECT date_trunc(''day'',rt) AS rt_day, sa, substring(sa,0,7) as OUI
			FROM (SELECT DISTINCT ON (date_trunc(''minute'', rt), sa, seqno) rt, sa
							FROM (
							      (SELECT * FROM rawdata_%s WHERE rssi BETWEEN %s AND 0)
							      UNION ALL
							      (SELECT * FROM rawdata_%s WHERE rssi BETWEEN %s AND 0)
							     ) as UNION_rawdata
							WHERE rt BETWEEN ''%s'' AND ''%s''
							AND cname = ''SamsungE''
							AND pkt_type = 0)t
			group by rt_day, sa
			having count(1) < 2
		), SAMSUNG_FACTOR AS(
		    SELECT rt_hour, OUI, (
		    CASE WHEN count(1) < 10 THEN 1
		         WHEN count(1) >= 10 AND count(1) < 20 THEN 0.4
		         WHEN count(1) >= 20 AND count(1) < 30 THEN 0.3
		         WHEN count(1) >= 30 AND count(1) < 40 THEN 0.2
		         WHEN count(1) >= 40 AND count(1) < 50 THEN 0.1
		         ELSE 0
		         END) AS factor
		    FROM SAMSUNG_CANDIDATE
		    group by rt_hour, OUI
		), SAMSUNG_RATIO AS (
		    SELECT A.rt_hour, A.sa, B.factor
		    FROM SAMSUNG_CANDIDATE AS A
		    LEFT JOIN SAMSUNG_FACTOR AS B
		    ON A.rt_hour = B.rt_hour AND A.oui = B.oui
		    WHERE B.factor != 1
		), UNION_rawdata AS(
      SELECT rt, sa
       FROM rawdata
       WHERE (sniffer = ''%s'' AND rssi BETWEEN %s AND 0
           OR sniffer = ''%s'' AND rssi BETWEEN %s AND 0)
       AND rt BETWEEN ''%s'' AND ''%s''
       AND cname = ANY(%L)
    ), RAW AS(
        SELECT
        date_trunc(''day'',rt) AS rt_day, min(date_trunc(''hour'', rt)) as rt_hour, sa, 1 AS factor
        FROM UNION_rawdata
        group by rt_day, sa
    ), TAB1 AS(
				SELECT A.rt_hour AS time, cast(
						SUM(CASE WHEN A.factor > B.factor THEN B.factor
							ELSE A.factor
							END)/%s/%s as INT) as customers
				FROM RAW AS A
				LEFT JOIN SAMSUNG_RATIO AS B
				ON A.rt_hour = B.rt_hour AND A.sa = B.sa
				group by time
    ), TAB2 AS(
        SELECT *
        FROM TAB1
        UNION (SELECT generate_series(min(rt_day), max(rt_hour), ''1 hour'') as time, 0
               FROM RAW)
    )
    SELECT time, sum(customers) as customers
    FROM TAB2
    group by time
    order by time ASC;',
    _antenna_1, _rssi_1, _antenna_2, _rssi_2,
    start_time, end_time,
		_antenna_1, _rssi_1, _antenna_2, _rssi_2,
    start_time, end_time, _android_oui,
    _android_ratio, _wifi_ratio);
END;

$BODY$;
