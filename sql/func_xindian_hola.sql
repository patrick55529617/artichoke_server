-- FUNCTION: public.xindian_hola_rpi(timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION public.xindian_hola_rpi(timestamp with time zone, timestamp with time zone);
﻿
CREATE OR REPLACE FUNCTION public.xindian_hola_rpi(
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	))
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'sql'

AS $BODY$
SELECT * FROM public.xindian_hola_rpi_hotfix_v2(_timefrom, _timeto) as t;


$BODY$;
