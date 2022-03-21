-- FUNCTION: public.random_samsung_candidate_union(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], integer, integer)

-- DROP FUNCTION public.random_samsung_candidate_union(text, integer, text, integer, timestamp with time zone, timestamp with time zone, character[], integer, integer);

CREATE OR REPLACE FUNCTION public.random_samsung_candidate_union(
	_antenna_1 text,
	_rssi_1 integer,
	_antenna_2 text,
	_rssi_2 integer,
	_start_time timestamp with time zone,
	_end_time timestamp with time zone,
	_android_oui character[],
	_rolling_minute integer,
	_theta integer)
    RETURNS TABLE(rt_day timestamp with time zone, sa character)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

/*
This function used for verifing Android random mac in union site,
but it called random_samsung_candidate_union for some historical reason. :(
** THIS IS NOT USED FOR XINYI HOI! (Hoi has 3 antenna)

Version: 20181019 (Fri)
         - Add comment and example.
         - Fixed bug for union in the same floor.
Commit : (Full this line in DB)

Algorithm: Please see PPT: Random mac - Union

Input:
_antenna_1 text := antenna 1 mac
_rssi_1 integer := RSSI of antenna 1
_antenna_2 text := antenna 2 mac
_rssi_2 integer := RSSI of antenna 2
_start_time timestamp with time zone := start time
_end_time timestamp with time zone : end time (not including)
_android_oui character[] := OUI list
_rolling_minute integer := rolling minute
_theta integer := rolling count

Output: Random mac blacklist for each day
rt_day timestamp with time zone := date
sa character := random mac according rt_day

Example: 2018-10-1 Random mac in Zhonghe TLW
SELECT *
  FROM public.random_samsung_candidate_union(
							'74da38d39b07', -68,
							'74da38db2016', -68,
							'2018-10-1'::date, '2018-10-2'::date,
							 taiwan_android_oui(),20,5)

*/

BEGIN
set time zone 'Asia/Taipei';
RETURN QUERY EXECUTE
    format('
		WITH SAMSUNG_TARGET_CANDIDATE AS(
            /*
            query raw data for candiate list
            (*) sum(pkt_type) = 0 is a mathematical method to query
            		mac address has only probe-req without data type.
            		IF use WHERE pkt_type = 0 could have no info about probe-req / data type.
            */
            SELECT date_trunc(''day'',rt) AS rt_day, sa, substring(sa,0,7) as oui, min(rt) as rt
            FROM (
                  (SELECT * FROM rawdata_%s WHERE rssi BETWEEN %s AND 0)
                  UNION ALL
                  (SELECT * FROM rawdata_%s WHERE rssi BETWEEN %s AND 0)
                 ) as UNION_rawdata
            WHERE rt BETWEEN ''%s'' AND ''%s''
            AND cname = ANY(%L)
            group by rt_day, sa
            having sum(pkt_type) = 0 -- probe-req only
               AND count(1) = count(DISTINCT sniffer) -- #packets = #sniffer
               AND max(rt) - min(rt) <= ''5 sec'' -- time difference <= 5 sec (duration is small)
        ), SAMSUNG_TARGET_OUI AS(
            -- calculate oui and drop out oui less than threshold (for speed)
            SELECT rt_day, oui
            FROM SAMSUNG_TARGET_CANDIDATE
            group by rt_day, oui
            having count(1) > %s -- speed up
        ), SAMSUNG_CANDIDATE AS(
            -- calculate candiate list
            SELECT rt_day, rt, sa, oui
            FROM SAMSUNG_TARGET_CANDIDATE AS A
            WHERE EXISTS (SELECT 1
                          FROM SAMSUNG_TARGET_OUI AS B
                          WHERE A.rt_day = B.rt_day AND A.oui = B.oui)
        ), SAMSUNG_OUI_verify AS(
            -- verify candiate list by rolling count
            -- specially, using self-inner-join to do rolling
            SELECT rt_day, oui
            FROM (SELECT A.rt_day, A.oui
                  FROM SAMSUNG_CANDIDATE A
                  INNER JOIN SAMSUNG_CANDIDATE B
                  ON B.rt >= A.rt AND B.rt - interval ''%s minutes'' <= A.rt AND
                     A.oui = B.oui AND
                     date_trunc(''day'', B.rt - interval ''%s minutes'') = date_trunc(''day'', A.rt)
                  group by A.rt_day, A.oui, A.rt
                  having count(1) > %s) t
            group by rt_day, oui
        )
      -- return Samsung blacklist with verified OUI from candidate list
      SELECT rt_day, sa
      FROM SAMSUNG_CANDIDATE A
      WHERE EXISTS (SELECT 1
                    FROM SAMSUNG_OUI_verify B
                    WHERE A.rt_day = B.rt_day AND A.oui = B.oui)',
    _antenna_1, _rssi_1, _antenna_2, _rssi_2,
	_start_time, _end_time, _android_oui,
	_theta, _rolling_minute, _rolling_minute, _theta);
END;

$BODY$;
