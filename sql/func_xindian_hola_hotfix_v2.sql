-- FUNCTION: public.xindian_hola_rpi_hotfix_v2(timestamp with time zone, timestamp with time zone, integer, integer)

-- DROP FUNCTION public.xindian_hola_rpi_hotfix_v2(timestamp with time zone, timestamp with time zone, integer, integer);

CREATE OR REPLACE FUNCTION public.xindian_hola_rpi_hotfix_v2(
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	),
	_rolling_minute integer DEFAULT 20,
	_theta integer DEFAULT 5)
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
      FROM rawdata_74da38b99297 -- TLW
      WHERE rt BETWEEN date_trunc('day', _timefrom) AND _timeto AND
      rssi BETWEEN -90 AND 0 AND
      cname = ANY(taiwan_android_oui())
      group by rt_minute, sa ) as tlw
  RIGHT JOIN
      (SELECT
      to_timestamp(floor((extract('epoch' from rt) / 300 )) * 300) AS rt_minute, sa, max(rssi) as rssi
      FROM rawdata_74da38b9929c AS A-- HOLA
      WHERE rt BETWEEN date_trunc('day', _timefrom) AND _timeto AND
      rssi BETWEEN -90 AND 0 AND
      cname = ANY(taiwan_android_oui()) AND
		  NOT EXISTS (SELECT 1
									FROM random_samsung_candidate('74da38b9929c',-90,
												date_trunc('day', _timefrom), _timeto , taiwan_android_oui(), _rolling_minute, _theta) AS B
									WHERE date_trunc('day',A.rt) = B.rt_day AND A.sa = B.sa AND A.pkt_type = 0)
      group by rt_minute, sa) as hola
  ON tlw.rt_minute = hola.rt_minute AND tlw.sa = hola.sa
  WHERE tlw.rssi <= hola.rssi OR tlw.rssi IS NULL
), RAW AS(
	SELECT
    date_trunc('day',rt_minute) AS rt_day, min(date_trunc('hour', rt_minute)) as rt_hour, sa
    FROM TMP
    group by rt_day, sa
),  TAB1 AS(
    SELECT rt_hour as time, cast(count(1)/0.55/0.7 as INT) as customers
    FROM RAW AS A
    group by time
), TAB2 AS(
    SELECT *
    FROM TAB1
    UNION (SELECT generate_series(min(rt_hour), max(rt_hour), '1 hour') as time, 0
           FROM RAW)
)

SELECT time, sum(customers) as customers
FROM TAB2
group by time
order by time ASC

$BODY$;
