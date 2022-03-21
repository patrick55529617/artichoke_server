-- FUNCTION: public.counter_union_base(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision)

-- DROP FUNCTION public.counter_union_base(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision);

CREATE OR REPLACE FUNCTION public.counter_union_base(
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
    WITH RAW AS(
        SELECT
        date_trunc(''day'',rt) AS rt_day, min(date_trunc(''hour'', rt)) as rt_hour, sa
        FROM (
              (SELECT * FROM rawdata_%s WHERE rssi BETWEEN %s AND 0)
              UNION ALL
              (SELECT * FROM rawdata_%s WHERE rssi BETWEEN %s AND 0)
             ) as UNION_rawdata
        WHERE rt BETWEEN ''%s'' AND ''%s''
        AND cname = ANY(%L)
        group by rt_day, sa
    ), TAB1 AS(
        SELECT rt_hour as time, cast(count(1)/%s/%s as INT) as customers
        FROM RAW
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
    start_time, end_time, _android_oui,
    _android_ratio, _wifi_ratio);
END;

$BODY$;
