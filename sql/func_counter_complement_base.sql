-- FUNCTION: public.counter_complement_base(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer)

-- DROP FUNCTION public.counter_complement_base(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer);

CREATE OR REPLACE FUNCTION public.counter_complement_base(
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
	_wifi_ratio double precision DEFAULT 0.66,
	_window_size integer DEFAULT 5,
	_offset integer DEFAULT 0)
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
		    FROM rawdata_%1$s AS A
		    WHERE rt BETWEEN ''%5$s'' AND ''%6$s''
		    AND rssi BETWEEN %2$s AND 0
		    AND cname = ANY(%7$L)
		    AND NOT EXISTS (SELECT 1
		                    FROM rawdata_%3$s AS B
		                    WHERE B.rt BETWEEN A.rt - interval ''%10$s minutes'' AND A.rt -- rolling back
		                    AND A.sa = B.sa
		                    AND rssi BETWEEN %4$s AND 0
		                    group by B.sa
		                    having max(B.rssi) >= A.rssi + (%11$s) -- offset
		                    )
		    group by rt_day, sa
		),  TAB1 AS(
		    SELECT rt_hour as time, cast(count(1)/%8$s/%9$s as INT) as customers
		    FROM RAW AS A
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
		order by time ASC',
		_antenna_1, _rssi_1, _antenna_2, _rssi_2,
		start_time, end_time, _android_oui,
		_android_ratio, _wifi_ratio,
		_window_size, _offset);
END;

$BODY$;
