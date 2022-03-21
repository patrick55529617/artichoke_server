-- FUNCTION: public.counter_hotfix_v1(text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision)

-- DROP FUNCTION public.counter_hotfix_v1(text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision);

CREATE OR REPLACE FUNCTION public.counter_hotfix_v1(
	_antenna text,
	_rssi integer,
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
				SELECT date_trunc(''hour'',rt) AS rt_hour, sa, substring(sa,0,7) as OUI
				FROM rawdata_%s
				WHERE rt BETWEEN ''%s'' AND ''%s''
				AND cname = ''SamsungE''
				AND rssi BETWEEN %s AND 0
				AND pkt_type = 0
				group by rt_hour, sa
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
		), RAW AS(
		    SELECT
		    date_trunc(''day'',rt) AS rt_day, min(date_trunc(''hour'', rt)) as rt_hour, sa, 1 AS factor
		    FROM rawdata_%s
		    WHERE rt BETWEEN ''%s'' AND ''%s''
		    AND rssi BETWEEN ''%s'' AND 0
		    AND cname = ANY(%L)
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
    _antenna, start_time, end_time, _rssi,
		_antenna, start_time, end_time,
    _rssi, _android_oui, _android_ratio, _wifi_ratio
		);
END;

$BODY$;
