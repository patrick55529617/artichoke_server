CREATE OR REPLACE FUNCTION public.counter_model_union(
  _antenna_1 text,
	_rssi_1 integer,
	_antenna_2 text,
	_rssi_2 integer,
	_timefrom timestamp with time zone,
	_timeto timestamp with time zone,
	_model_slope double precision,
	_model_intercept double precision,
	_model_upper_limit double precision,
	_android_oui character[] DEFAULT taiwan_android_oui(),
	_android_ratio double precision DEFAULT 0.55,
	_wifi_ratio double precision DEFAULT 0.66,
	_manual_slope double precision DEFAULT NULL::double precision)
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

DECLARE
-- Avoid divide by zero
slope double precision:= GREATEST(1, coalesce(_manual_slope, _model_slope));

/* SQL structure:
-- Part A: optimator: cheat SQL planer due to unsuitable SQL configs.
WITH COUNT_TAB AS (
  SELECT s.*
    FROM generate_series(date '2020-12-1', date '2020-12-5', ''1 day'') t,
 LATERAL (
    -- Part B: The Core: Model counter
    -- Model Est.
    -- android_mac = unique_mac + max(0, min(random_pkt, slope * unique_mac + upper_limit) - intercept)/slope
    -- model_count = android_mac/android_ratio/wifi_ratio
 ) s
)
-- Part C: Fill zero and sort
*/

BEGIN
set session time zone 'Asia/Taipei';
RETURN QUERY EXECUTE format('
WITH COUNT_TAB AS (
  SELECT s.*
    FROM generate_series(date ''%5$s'', date ''%6$s'', ''1 day'') t,
 LATERAL (
   -- The Core: Model counter
  SELECT time
  	   , (
          (coalesce(unique_mac, 0) +
               GREATEST(0, LEAST(coalesce(AR_pkts, 0), %7$s * coalesce(unique_mac, 0) + %9$s) - %8$s) / %13$s
          ) / %11$s / %12$s
         ) AS customers
    FROM (
    -- X1: unique mac with the auto random rssi
  	SELECT time, customers as unique_mac
      FROM public.counter_union_hotfix_v2_1(''%1$s'', %2$s, ''%3$s'', %4$s, t, t,
                                            _android_ratio:=1, _wifi_ratio:=1,
                                            _android_oui:=%10$L,
                                            _random_rssi_1:=CASE WHEN %2$s <= -90 THEN %2$s ELSE -90 END,
                                            _random_rssi_2:=CASE WHEN %4$s <= -90 THEN %4$s ELSE -90 END)
    ) a
    FULL JOIN (
    -- unrestricted X2: Android random packets (cname is null or Google Random)
      SELECT date_trunc(''hour'', coalesce(a.rt, b.rt))::timestamp as time
           , count(1) AS AR_pkts -- Total
      FROM
      (
      SELECT rt, sa
        FROM public.rawdata_%1$s
       WHERE rt >= t
         AND rt < t + interval ''1 days''
         AND rssi < 0
         AND rssi >= %2$s
         AND pkt_type = 0
         AND (cname IS NULL or cname = ''Google_Random'')
      ) a
      FULL JOIN
      (
      SELECT rt, sa
        FROM public.rawdata_%3$s
       WHERE rt >= t
         AND rt < t + interval ''1 days''
         AND rssi < 0
         AND rssi >= %4$s
         AND pkt_type = 0
         AND (cname IS NULL or cname = ''Google_Random'')
      ) b
      ON a.sa = b.sa
      AND a.rt - b.rt BETWEEN interval ''-00:01'' AND interval ''00:01''
      GROUP BY 1
      ORDER BY 1
   ) b
   USING(time)
   -- End of the core.
 ) s
)

-- Fill zero and sort
SELECT t.time
     , sum(t.customers)::bigint as customers
  FROM (
	 SELECT *
	   FROM COUNT_TAB
	  UNION ALL
	 SELECT generate_series(min(s.time), max(s.time), ''1 hour'') as time, 0
	   FROM COUNT_TAB s
  ) t
 GROUP BY 1
 ORDER BY 1;',
    _antenna_1, _rssi_1, _antenna_2, _rssi_2, _timefrom, _timeto,
    _model_slope, _model_intercept, _model_upper_limit,
    _android_oui, _android_ratio, _wifi_ratio, slope);
END;

$BODY$;
