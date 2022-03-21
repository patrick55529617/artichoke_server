-- FUNCTION: public.xitun_tlw(timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION public.xitun_tlw(timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION public.xitun_tlw(
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	))
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'sql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

SELECT * FROM public.counter_union(
	'74da38d39b11', -90,
    '74da38db1e1d', -90,
    _timefrom, _timeto) as t;

$BODY$;
