-- FUNCTION: public.distinct_mac(character[], character[])

-- DROP FUNCTION public.distinct_mac(character[], character[]);

CREATE OR REPLACE FUNCTION public.distinct_mac(
	_antenna character[],
	_android_oui character[] DEFAULT taiwan_android_oui(
	))
    RETURNS TABLE(mac character, first_visit timestamp with time zone, last_visit timestamp with time zone)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

DECLARE
BEGIN
RETURN QUERY EXECUTE
    format('
    SELECT DISTINCT(sa) as mac,
		min(rt) as first_visit,
		max(rt) as last_visit
    FROM rawdata
    WHERE sniffer=ANY(%L) AND
           cname NOT LIKE ''%%Random%%'' AND
           (cname LIKE ''%%Apple%%'' OR cname=ANY(%L) )
    GROUP BY sa;',
    _antenna, _android_oui);
END;

$BODY$;

