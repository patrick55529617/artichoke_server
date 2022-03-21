-- FUNCTION: public.counter_complement(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer, boolean, double precision, timestamp with time zone, integer, integer, double precision)

-- DROP FUNCTION public.counter_complement(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer, boolean, double precision, timestamp with time zone, integer, integer, double precision);

CREATE OR REPLACE FUNCTION public.counter_complement(
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
	_offset integer DEFAULT 0,
	_random_rssi integer DEFAULT '-90'::integer,
	_seamless boolean DEFAULT false,
	_seamless_diff double precision DEFAULT 0,
	_seamless_start_time timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_seamless_new_rssi_1 integer DEFAULT '-90'::integer,
	_seamless_new_rssi_2 integer DEFAULT '-90'::integer,
	_seamless_new_ratio double precision DEFAULT 0.55)
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

BEGIN

IF NOT _seamless OR _seamless_diff <= 0 THEN
-- disable seamless (default) or seamless diff (d) is not more than 0.
RETURN QUERY SELECT * FROM public.counter_complement_hotfix_v2_1(_antenna_1, _rssi_1, _antenna_2, _rssi_2,
													 _timefrom, _timeto, _android_oui, _android_ratio, _wifi_ratio, _window_size, _offset,
													 _random_rssi:=_random_rssi) as t;
ELSE
RETURN QUERY SELECT * FROM public.counter_complement_seamless(antenna_1, _rssi_1, _antenna_2, _rssi_2,
													 _timefrom, _timeto, _android_oui, _android_ratio, _wifi_ratio, _window_size, _offset,
													 _random_rssi, _seamless_diff, _seamless_start_time,
													 _seamless_new_rssi_1, _seamless_new_rssi_2, _seamless_new_ratio) as t;
END IF;

END;

$BODY$;

ALTER FUNCTION public.counter_complement(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer, boolean, double precision, timestamp with time zone, integer, integer, double precision)
    OWNER TO artichoke;
