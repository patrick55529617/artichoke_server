-- FUNCTION: public.chamtime_pot_rpi(timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION public.chamtime_pot_rpi(timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION public.chamtime_pot_rpi(
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	))
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'sql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

set session time zone 'Asia/Taipei';
WITH BED_n_JOY AS(
    -- union bed and joy
    SELECT date_trunc('hour',rt) AS rt_hour, sa
    FROM (
          (SELECT * FROM rawdata_74da38b99298 WHERE rssi between -90 and 0)
          UNION ALL
          (SELECT * FROM rawdata_74da38b99282 WHERE rssi between -90 and 0)
    	 ) as UNION_bed_joy
    WHERE rt BETWEEN date_trunc('day', _timefrom) AND _timeto
    AND cname = ANY(china_android_oui())
    group by rt_hour, sa
), RAW AS (
    -- mac in union bed and joy
    SELECT date_trunc('day', POT.rt_hour) AS rt_day, min(POT.rt_hour) as rt_hour, POT.sa as sa
    FROM
    (SELECT date_trunc('hour',rt) AS rt_hour, sa
     FROM rawdata_74da38b9929a
     WHERE rt BETWEEN date_trunc('day', _timefrom) AND _timeto
     AND rssi between -55 and 0
     AND cname = ANY(china_android_oui())
     group by rt_hour, sa
	 ) as POT
    INNER JOIN BED_n_JOY
    ON BED_n_JOY.rt_hour = POT.rt_hour AND BED_n_JOY.sa = POT.sa
    group by rt_day, POT.sa
), TAB1 AS(
  SELECT rt_hour as time, cast(count(1)/0.55/0.7 as INT) as customers
  FROM RAW AS A
	-- hotfix v2
	WHERE NOT EXISTS (SELECT 1
                    FROM random_samsung_candidate('74da38b9929a',-55,
                          date_trunc('day', _timefrom),_timeto,china_android_oui(),20,5) AS B
                    WHERE A.rt_day = B.rt_day AND A.sa = B.sa)
  group by time
), TAB2 AS(
  SELECT *
  FROM TAB1
  UNION (SELECT generate_series(min(rt_day), max(rt_hour), '1 hour') as time, 0
  FROM RAW)
)

SELECT time, sum(customers) as customers
FROM TAB2
group by time
order by time ASC

$BODY$;
