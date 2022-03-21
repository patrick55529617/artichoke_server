CREATE OR REPLACE FUNCTION public.counter_weight(
	_antenna text,
	_rssi integer,
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	),
	_android_oui character[] DEFAULT taiwan_android_oui(
	),
	_android_ratio double precision DEFAULT 0.55,
	_wifi_ratio double precision DEFAULT 0.66,
	_random_rssi integer DEFAULT '-90'::integer,
	_new_weight double precision DEFAULT 0,
	_new_rssi integer DEFAULT '-90'::integer,
	_new_android_ratio double precision DEFAULT 0.55,
	_new_random_rssi integer DEFAULT '-90'::integer)
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

DECLARE
new_weight double precision := LEAST(GREATEST(_new_weight,0),1);
-- limit weight between 0 and 1
BEGIN

RETURN QUERY SELECT t.time, (new_weight*count_new + (1-new_weight)*count_old)::bigint AS "customers"
	           -- bigint due to historical glitches of counter family
    	       FROM (
      	       SELECT OLD.time AS "time",
      	              OLD.customers AS "count_old",
      	              NEW.customers AS "count_new"
      	       FROM public.counter(_antenna, _rssi, _timefrom, _timeto,
      	         	           _android_oui, _android_ratio, _wifi_ratio, _random_rssi) AS OLD,
                    public.counter(_antenna, _new_rssi, _timefrom, _timeto,
      	         	           _android_oui, _new_android_ratio, _wifi_ratio, _new_random_rssi) AS NEW
      	       WHERE OLD.time = NEW.time) t;
END;

$BODY$;
