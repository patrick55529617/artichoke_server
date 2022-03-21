-- FUNCTION: public.chamtime_joy_rpi(timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION public.chamtime_joy_rpi(timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION public.chamtime_joy_rpi(
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	))
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'sql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

   SELECT * FROM public.counter('74da38b99282',-60, _timefrom, _timeto, public.china_android_oui(), 0.55,0.7) as t;

$BODY$;
