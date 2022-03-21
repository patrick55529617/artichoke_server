﻿-- FUNCTION: public.chamtime_hola_rpi(timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION public.chamtime_hola_rpi(timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION public.chamtime_hola_rpi(
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	))
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'sql'

AS $BODY$

SELECT * FROM public.counter_union(
	'74da38b99298', -90,
    '74da38b99282', -90,
    _timefrom, _timeto,
    china_android_oui()) as t

$BODY$;

