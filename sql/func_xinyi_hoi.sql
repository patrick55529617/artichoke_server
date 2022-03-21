CREATE OR REPLACE FUNCTION public.xinyi_hoi(
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	))
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

/*

Version: 20181019 (Fri)
         - Fixed bug for union in the same floor.
Commit : (Full this line in DB)

*/

DECLARE
-- START config 
antenna_1 text := '74da38ebbb42';
rssi_1 integer := -64; -- 2F
antenna_2 text := '74da38ebbb40';
rssi_2 integer := -64; -- 2F
antenna_3 text := '74da38ebb833';
rssi_3 integer := -64; -- 2F
-- DEFAULT configure
android_oui text := taiwan_android_oui();
android_ratio double precision := 0.55;
wifi_ratio double precision := 0.7;
rolling_minute integer := 20;
theta integer := 5;
-- END config
start_time timestamptz := date_trunc('day', _timefrom);
end_time timestamptz := date_trunc('day', _timeto) + interval '1 day';

BEGIN
set time zone 'Asia/Taipei';
RETURN QUERY EXECUTE
    format('
      	WITH UNION_rawdata AS(
            SELECT *
            FROM (
                (SELECT * FROM rawdata_%1$s WHERE rssi BETWEEN %2$s AND 0)
                UNION ALL
                (SELECT * FROM rawdata_%3$s WHERE rssi BETWEEN %4$s AND 0)
                UNION ALL
                (SELECT * FROM rawdata_%5$s WHERE rssi BETWEEN %6$s AND 0)
            	) t
            WHERE rt BETWEEN ''%7s'' AND ''%8s''
            AND cname = ANY(%9$L)
----- DO SAMSUNG RANDOM CANDIDATE
        ), SAMSUNG_TARGET_CANDIDATE AS(
            SELECT date_trunc(''day'',rt) AS rt_day, sa, substring(sa,0,7) as oui, min(rt) as rt
            FROM UNION_rawdata
            group by rt_day, sa
            having sum(pkt_type) = 0 -- probe-req only
               AND count(1) = count(DISTINCT sniffer) -- #packets = #sniffer
               AND max(rt) - min(rt) <= ''5 sec'' -- time difference <= 5 sec (duration is small)
        ), SAMSUNG_TARGET_OUI AS(
            SELECT rt_day, oui
      		FROM SAMSUNG_TARGET_CANDIDATE
      		group by rt_day, oui
      		having count(1) > %13$s
        ), SAMSUNG_CANDIDATE AS(
            SELECT rt_day, rt, sa, oui
    		FROM SAMSUNG_TARGET_CANDIDATE AS A
        	WHERE EXISTS (SELECT 1
                      	  FROM SAMSUNG_TARGET_OUI AS B
                      	  WHERE A.rt_day = B.rt_day AND A.oui = B.oui)
      	), SAMSUNG_OUI_verify AS(
            SELECT rt_day, oui
            FROM (SELECT A.rt_day, A.oui
                  FROM SAMSUNG_CANDIDATE A
                  INNER JOIN SAMSUNG_CANDIDATE B
                  ON B.rt >= A.rt AND B.rt - interval ''%12$s minutes'' <= A.rt AND
                     A.oui = B.oui AND
                     date_trunc(''day'', B.rt - interval ''%12$s minutes'') = date_trunc(''day'', A.rt)
                  group by A.rt_day, A.oui, A.rt
                  having count(1) > %13$s) t
            group by rt_day, oui
        ), SAMSUNG_RANDOM_CANDIDATE AS(
            SELECT rt_day, sa
      		FROM SAMSUNG_CANDIDATE A
      		WHERE EXISTS (SELECT 1
                    	  FROM SAMSUNG_OUI_verify B
                    	  WHERE A.rt_day = B.rt_day AND A.oui = B.oui)
----- END SAMSUNG RANDOM CANDIDATE
----- DO PEOPLE COUNT
			), RAW AS(
	        SELECT date_trunc(''day'',rt) AS rt_day, min(date_trunc(''hour'', rt)) as rt_hour, sa
	        FROM UNION_rawdata
	        group by rt_day, sa
	    ), TAB1 AS(
	        SELECT rt_hour as time, cast(count(1)/%10$s/%11$s as INT) as customers
	        FROM RAW AS A
	        WHERE NOT EXISTS (SELECT 1
	                          FROM SAMSUNG_RANDOM_CANDIDATE AS B
	                          WHERE A.rt_day = B.rt_day AND A.sa = B.sa)
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
	    order by time ASC;
----- END PEOPLE COUNT',
        antenna_1, rssi_1, antenna_2, rssi_2, antenna_3, rssi_3,
	    start_time, end_time, android_oui,
	    android_ratio, wifi_ratio,
	    rolling_minute, theta);
END;

$BODY$;

ALTER FUNCTION public.xinyi_hoi(timestamp with time zone, timestamp with time zone)
    OWNER TO artichoke;

GRANT EXECUTE ON FUNCTION public.xinyi_hoi(timestamp with time zone, timestamp with time zone) TO shiny;

GRANT EXECUTE ON FUNCTION public.xinyi_hoi(timestamp with time zone, timestamp with time zone) TO artichoke;

GRANT EXECUTE ON FUNCTION public.xinyi_hoi(timestamp with time zone, timestamp with time zone) TO PUBLIC;
