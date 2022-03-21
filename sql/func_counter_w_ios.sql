CREATE OR REPLACE FUNCTION public.counter_w_ios(
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
	_model_slope double precision DEFAULT 0,
	_model_intercept double precision DEFAULT 0)
    RETURNS TABLE("time" timestamp with time zone, customers bigint)
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
    ROWS 1000
AS $BODY$

BEGIN
 set session time zone 'Asia/Taipei';
/*
  To use format('...') is worst, but we need to query table, named rawdata_{_antenna}.
  Due the partition table in this server is really stupid and slow,
   we should query the node table directly.
*/
 RETURN QUERY EXECUTE
 format('
  SELECT time,
        --customers_by_android,
        --customers_by_ios,
        GREATEST(customers_by_android, customers_by_ios)::bigint as customers
        /*
        GREATEST would ignore NULL values (NaN).
        bigint due to historical glitches of counter family
        */
  FROM
  (
   -- customers powered by android, disabled seamless method
   SELECT time,
          customers as customers_by_android
     FROM public.counter(''%1$s'', %4$s, ''%2$s'', ''%3$s'',
                         %5$L, %6$s, %7$s, %8$s, _seamless:= false)
  ) android
  FULL OUTER JOIN
  (
   -- customers powered by ios random
   SELECT t.time,
          (ios_people_counts/(1-%6$s)/%7$s)::int as customers_by_ios
          /*
          The patermeters of model do not project the wifi ratio.
          Be carefull when you build the model.
          */
   FROM (
     /*
     Note:
     (a)  customers = slope * ios_packets + intercept if slope * ios_packets >  0
                    = 0                               if slope * ios_packets <= 0
          equivalent to (slope * ios_packets + intercept) * (indicator functions)
          It is faster and simpler than "CASE or IF" in SQL.
     (b) It is a bad sql statement for "rt BETWENN x and y + 1 days",
           but ios method needs to alig the android method.
     (c) Warning: Raw data of ios random only have 3 months, that is,
                    we remove the raw data to save the space.
     */
     SELECT date_trunc(''hour'', rt) as time,
            (%9$s * count(1) + %10$s) * (%9$s * count(1) > 0)::int as ios_people_counts
       FROM public.rawdata_%1$s
      WHERE rt BETWEEN ''%2$s''::date AND ''%3$s''::date + interval ''1 days''
        AND rssi BETWEEN %4$s AND 0
        AND cname = ''iOS_Random''
     group by time
   ) t
  ) ios
  using(time)
  order by time;',
_antenna, _timefrom, _timeto,
_rssi, _android_oui, _android_ratio, _wifi_ratio,
_random_rssi, _model_slope, _model_intercept);

END;

$BODY$;
