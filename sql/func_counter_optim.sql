CREATE OR REPLACE FUNCTION public.counter_optim(
	_antenna text,
	_rssi integer,
	_timefrom timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_timeto timestamp with time zone DEFAULT now(
	),
	_android_oui character[] DEFAULT taiwan_android_oui(
	),
	_android_ratio double precision DEFAULT 0.55,
	_wifi_ratio double precision DEFAULT 0.66,
	_random_rssi integer DEFAULT '-90'::integer,
	_seamless boolean DEFAULT false,
	_seamless_diff double precision DEFAULT 0,
	_seamless_start_time timestamp with time zone DEFAULT '2017-01-01 00:00:00+00'::timestamp with time zone,
	_seamless_new_rssi integer DEFAULT '-90'::integer,
	_seamless_new_ratio double precision DEFAULT 0.55)
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

BEGIN
	/*
	2019/10/17
	簡單優化法：每天計算在合併，避免大量資料使用硬碟做排序 (I/O慢)
	主要適用於：計算超過一周資料
	輸出入變數：同 counter 函數
	*/
  RETURN QUERY
    WITH COUNT_TAB AS (
        SELECT s.*
        FROM generate_series(_timefrom::date, _timeto::date, '1 day') t,
        LATERAL (
          SELECT *
            FROM public.counter(_antenna, _rssi, t, t,
                                _android_oui, _android_ratio, _wifi_ratio, _random_rssi,
                                _seamless, _seamless_diff, _seamless_start_time, _seamless_new_rssi, _seamless_new_ratio)) as s
    )

    -- Fill zero and sort
    SELECT t.time, sum(t.customers)::bigint as customers
      FROM (
         SELECT * FROM COUNT_TAB
         UNION ALL
         SELECT generate_series(min(s.time), max(s.time), '1 hour') as time, 0
           FROM COUNT_TAB s -- use TAB1 would be faster
      ) t
    group by t.time
    order by t.time ASC;

END;

$BODY$;
