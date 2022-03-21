-- FUNCTION: public.counter_hotfix_v2_1(text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer)

-- DROP FUNCTION public.counter_hotfix_v2_1(text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer);

CREATE OR REPLACE FUNCTION public.counter_hotfix_v2_1(
	_antenna text,
	_rssi integer,
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	),
	_android_oui character[] DEFAULT taiwan_android_oui(
	),
	_android_ratio double precision DEFAULT 0.55,
	_wifi_ratio double precision DEFAULT 0.66,
	_rolling_minute integer DEFAULT 20,
	_theta integer DEFAULT 5,
	_random_rssi integer DEFAULT '-90'::integer)
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
    WITH RAW AS(
        SELECT
        date_trunc(''day'',rt) AS rt_day, min(date_trunc(''hour'', rt)) as rt_hour, sa
        FROM rawdata_%1$s
        WHERE rt BETWEEN ''%2$s'' AND ''%3$s''
        AND rssi BETWEEN %4$s AND 0
        AND cname = ANY(%5$L)
        group by rt_day, sa
    ), TAB1 AS(
        SELECT rt_hour as time, cast(count(1)/%6$s/%7$s as INT) as customers
        FROM RAW AS A
        WHERE NOT EXISTS (SELECT 1
                          FROM random_samsung_candidate(''%1$s'',%10$s,''%2$s'',
                                ''%3$s'',%5$L,%8$s,%9$s) AS B
                          WHERE A.rt_day = B.rt_day AND A.sa = B.sa)
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
    _antenna, start_time, end_time,
    _rssi, _android_oui, _android_ratio, _wifi_ratio,
    _rolling_minute, _theta,
    _random_rssi);
END;

$BODY$;
