-- FUNCTION: public.counter_complement_seamless(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer, double precision, timestamp with time zone, integer, integer, double precision)

-- DROP FUNCTION public.counter_complement_seamless(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer, double precision, timestamp with time zone, integer, integer, double precision);

CREATE OR REPLACE FUNCTION public.counter_complement_seamless(
	_antenna_1 text,
	_rssi_1 integer,
	_antenna_2 text,
	_rssi_2 integer,
	_timefrom timestamp with time zone,
	_timeto timestamp with time zone,
	_android_oui character[],
	_android_ratio double precision,
	_wifi_ratio double precision,
	_window_size integer,
	_offset integer,
	_random_rssi integer,
	_seamless_diff double precision,
	_seamless_start_time timestamp with time zone,
	_seamless_new_rssi_1 integer,
	_seamless_new_rssi_2 integer,
	_seamless_new_ratio double precision)
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

DECLARE
seamless_start_time timestamptz := _seamless_start_time::date;
seamless_interval interval := (1/_seamless_diff)::int * interval '1 days';
seamless_end_time timestamptz := seamless_start_time + seamless_interval;
BEGIN

CASE
WHEN _timefrom::date >= seamless_end_time OR date_part('day', seamless_interval) = 0 THEN
  -- end of seamless or one shot kill, switch to new settings
  RETURN QUERY SELECT * FROM public.counter_complement(_antenna_1, _seamless_new_rssi_1, _antenna_2, _seamless_new_rssi_2,
                                                       _timefrom, _timeto, _android_oui, _seamless_new_ratio, _wifi_ratio,
                                                       _window_size, _offset, _random_rssi);

WHEN _timeto::date < seamless_start_time THEN
  -- not starting seamless
	RETURN QUERY SELECT * FROM public.counter_complement(_antenna_1, _rssi_1, _antenna_2, _rssi_2,
                                                         _timefrom, _timeto, _android_oui, _android_ratio, _wifi_ratio,
                                                         _window_size, _offset, _random_rssi);
ELSE
  RETURN QUERY SELECT t.time, (weight*count_new + (1-weight)*count_old)::bigint AS "customers"
  	           -- bigint due to historical glitches of counter family
      	       FROM (
        	       SELECT OLD.time AS "time",
        	       OLD.customers AS "count_old",
        	       NEW.customers AS "count_new",
      					 LEAST(GREATEST(date_part('day', OLD.time::date - seamless_start_time + interval '1 days')*_seamless_diff,0),1) as "weight"
      					 -- LIMIT weight ratio from 0 to 1
        	       FROM public.counter_complement(_antenna_1, _rssi_1, _antenna_2, _rssi_2,
                                                  _timefrom, _timeto, _android_oui, _android_ratio, _wifi_ratio,
                                                  _window_size, _offset, _random_rssi) AS OLD,
                   public.counter_complement(_antenna_1, _seamless_new_rssi_1, _antenna_2, _seamless_new_rssi_2,
                                             _timefrom, _timeto, _android_oui, _seamless_new_ratio, _wifi_ratio,
                                             _window_size, _offset, _random_rssi) AS NEW
        	       WHERE OLD.time = NEW.time) t;
END CASE;
END;

$BODY$;

ALTER FUNCTION public.counter_complement_seamless(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], double precision, double precision, integer, integer, integer, double precision, timestamp with time zone, integer, integer, double precision)
    OWNER TO artichoke;
