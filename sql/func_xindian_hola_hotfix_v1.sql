-- FUNCTION: public.xindian_hola_rpi_hotfix_v1(timestamp with time zone, timestamp with time zone)

-- DROP FUNCTION public.xindian_hola_rpi_hotfix_v1(timestamp with time zone, timestamp with time zone);

CREATE OR REPLACE FUNCTION public.xindian_hola_rpi_hotfix_v1(
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
WITH TMP AS(
  SELECT hola.*
  FROM
      (SELECT
      to_timestamp(floor((extract('epoch' from rt) / 300 )) * 300) AS rt_minute, sa, max(rssi) as rssi
      FROM  rawdata_74da38b99297 -- TLW
      WHERE rt BETWEEN date_trunc('day', _timefrom) AND _timeto AND
      rssi BETWEEN -90 AND 0 AND
      cname IN (SELECT * FROM unnest(taiwan_android_oui()))
      group by rt_minute, sa ) as tlw
  RIGHT JOIN
      (SELECT
      to_timestamp(floor((extract('epoch' from rt) / 300 )) * 300) AS rt_minute, sa, max(rssi) as rssi
      FROM  rawdata_74da38b9929c -- HOLA
      WHERE rt BETWEEN date_trunc('day', _timefrom) AND _timeto AND
      rssi BETWEEN -90 AND 0 AND
      cname IN (SELECT * FROM unnest(taiwan_android_oui()))
      group by rt_minute, sa) as hola
  ON tlw.rt_minute = hola.rt_minute AND tlw.sa = hola.sa
  WHERE tlw.rssi <= hola.rssi OR tlw.rssi IS NULL
), SAMSUNG_CANDIDATE AS(
    SELECT date_trunc('hour',rt) AS rt_hour, sa, substring(sa,0,7) as OUI
    FROM rawdata_74da38b9929c
    WHERE rt BETWEEN date_trunc('day', _timefrom) AND _timeto
    AND cname = 'SamsungE'
    AND rssi BETWEEN -90 AND 0
    AND pkt_type = 0
    group by rt_hour, sa
    having count(1) < 2
), SAMSUNG_FACTOR AS(
    SELECT rt_hour, OUI, (
    CASE WHEN count(1) < 10 THEN 1
         WHEN count(1) >= 10 AND count(1) < 20 THEN 0.4
         WHEN count(1) >= 20 AND count(1) < 30 THEN 0.3
         WHEN count(1) >= 30 AND count(1) < 40 THEN 0.2
         WHEN count(1) >= 40 AND count(1) < 50 THEN 0.1
         ELSE 0
         END) AS factor
    FROM SAMSUNG_CANDIDATE
    group by rt_hour, OUI
), SAMSUNG_RATIO AS (
    SELECT A.rt_hour, A.sa, B.factor
    FROM SAMSUNG_CANDIDATE AS A
    LEFT JOIN SAMSUNG_FACTOR AS B
    ON A.rt_hour = B.rt_hour AND A.oui = B.oui
    WHERE B.factor != 1
), RAW AS(
    SELECT
    date_trunc('day',rt_minute) AS rt_day, min(date_trunc('hour', rt_minute)) as rt_hour, sa, 1 AS factor
    FROM TMP
    group by rt_day, sa
    ), TAB1 AS (
    SELECT A.rt_hour AS time, cast(
        SUM(CASE WHEN A.factor > B.factor THEN B.factor
        	ELSE A.factor
        	END)/0.55/0.7 as INT) as customers
    FROM RAW AS A
    LEFT JOIN SAMSUNG_RATIO AS B
    ON A.rt_hour = B.rt_hour AND A.sa = B.sa
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
order by time ASC;

$BODY$;
