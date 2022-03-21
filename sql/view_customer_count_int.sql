﻿-- View: public.customer_count_int

-- DROP VIEW public.customer_count_int;

CREATE OR REPLACE VIEW public.customer_count_int AS
 SELECT tab.site_id,
    tab."time" AS ts_hour,
    tab.count
   FROM ( SELECT people_count_int.site_id,
            people_count_int."time",
            people_count_int.count
           FROM people_count_int
        UNION
         SELECT '1A07'::text AS site_id,
            neihu_tlw_rpi."time" AS ts_hour,
            neihu_tlw_rpi.customers AS count
           FROM neihu_tlw_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) neihu_tlw_rpi("time", customers)
        UNION
         SELECT '1B03'::text AS site_id,
            neihu_hola_rpi."time" AS ts_hour,
            neihu_hola_rpi.customers AS count
           FROM neihu_hola_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) neihu_hola_rpi("time", customers)
        UNION
         SELECT '1A09'::text AS site_id,
            shilin_tlw_rpi."time" AS ts_hour,
            shilin_tlw_rpi.customers AS count
           FROM shilin_tlw_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) shilin_tlw_rpi("time", customers)
        UNION
         SELECT '1B04'::text AS site_id,
            shilin_hola_rpi."time" AS ts_hour,
            shilin_hola_rpi.customers AS count
           FROM shilin_hola_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) shilin_hola_rpi("time", customers)
        UNION
         SELECT '1A19'::text AS site_id,
            xindian_tlw_rpi."time" AS ts_hour,
            xindian_tlw_rpi.customers AS count
           FROM xindian_tlw_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xindian_tlw_rpi("time", customers)
        UNION
         SELECT '1B17'::text AS site_id,
            xindian_hola_rpi."time" AS ts_hour,
            xindian_hola_rpi.customers AS count
           FROM xindian_hola_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xindian_hola_rpi("time", customers)
        UNION
         SELECT '1A02'::text AS site_id,
            xinzhuang_tlw_rpi."time" AS ts_hour,
            xinzhuang_tlw_rpi.customers AS count
           FROM xinzhuang_tlw_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xinzhuang_tlw_rpi("time", customers)
        UNION
         SELECT '1B06'::text AS site_id,
            zhonghe_hola_rpi."time" AS ts_hour,
            zhonghe_hola_rpi.customers AS count
           FROM zhonghe_hola_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) zhonghe_hola_rpi("time", customers)
        UNION
         SELECT '13112'::text AS site_id,
            chamtime_hola_rpi."time" AS ts_hour,
            chamtime_hola_rpi.customers AS count
           FROM chamtime_hola_rpi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) chamtime_hola_rpi("time", customers)
        UNION
         SELECT '13101'::text AS site_id,
            xianxia_hola."time" AS ts_hour,
            xianxia_hola.customers AS count
           FROM xianxia_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xianxia_hola("time", customers)
        UNION
         SELECT '13103'::text AS site_id,
            wujiaochang_hola."time" AS ts_hour,
            wujiaochang_hola.customers AS count
           FROM wujiaochang_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) wujiaochang_hola("time", customers)
        UNION
         SELECT '1K01'::text AS site_id,
            xinyi_cb."time" AS ts_hour,
            xinyi_cb.customers AS count
           FROM xinyi_cb(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xinyi_cb("time", customers)
        UNION
         SELECT '1K01-area'::text AS site_id,
            xinyi_cb_area."time" AS ts_hour,
            xinyi_cb_area.customers AS count
           FROM xinyi_cb_area(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xinyi_cb_area("time", customers)
        UNION
         SELECT '1K02'::text AS site_id,
            taichung_cb."time" AS ts_hour,
            taichung_cb.customers AS count
           FROM taichung_cb(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) taichung_cb("time", customers)
        UNION
         SELECT '1K02-area'::text AS site_id,
            taichung_cb_area."time" AS ts_hour,
            taichung_cb_area.customers AS count
           FROM taichung_cb_area(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) taichung_cb_area("time", customers)


        -- Phase 1
        UNION
         SELECT '1A05'::text AS site_id,
            chiayi_tlw."time" AS ts_hour,
            chiayi_tlw.customers AS count
           FROM chiayi_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) chiayi_tlw("time", customers)
        UNION
         SELECT '1A06'::text AS site_id,
            tainan_tlw."time" AS ts_hour,
            tainan_tlw.customers AS count
           FROM tainan_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) tainan_tlw("time", customers)
        UNION
         SELECT '1A11'::text AS site_id,
            beitun_tlw."time" AS ts_hour,
            beitun_tlw.customers AS count
           FROM beitun_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) beitun_tlw("time", customers)
        UNION
         SELECT '1A36'::text AS site_id,
            xitun_tlw."time" AS ts_hour,
            xitun_tlw.customers AS count
           FROM xitun_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xitun_tlw("time", customers)
        UNION
         SELECT '1B01'::text AS site_id,
            yongkang_hola."time" AS ts_hour,
            yongkang_hola.customers AS count
           FROM yongkang_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) yongkang_hola("time", customers)
        UNION
         SELECT '1B07'::text AS site_id,
            beitun_hola."time" AS ts_hour,
            beitun_hola.customers AS count
           FROM beitun_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) beitun_hola("time", customers)
        UNION
         SELECT '1B12'::text AS site_id,
            zhubei_hola."time" AS ts_hour,
            zhubei_hola.customers AS count
           FROM zhubei_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) zhubei_hola("time", customers)
        UNION
         SELECT '1B23'::text AS site_id,
            chiayi_hola."time" AS ts_hour,
            chiayi_hola.customers AS count
           FROM chiayi_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) chiayi_hola("time", customers)

        -- Phase 2
        UNION
         SELECT '1A14'::text AS site_id,
            jende_tlw."time" AS ts_hour,
            jende_tlw.customers AS count
           FROM jende_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) jende_tlw("time", customers)
        UNION
         SELECT '1A10'::text AS site_id,
            changhua_tlw."time" AS ts_hour,
            changhua_tlw.customers AS count
           FROM changhua_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) changhua_tlw("time", customers)
        UNION
         SELECT '1A13'::text AS site_id,
            fengshan_tlw."time" AS ts_hour,
            fengshan_tlw.customers AS count
           FROM fengshan_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) fengshan_tlw("time", customers)
        UNION
         SELECT '1A12'::text AS site_id,
            yuanlin_tlw."time" AS ts_hour,
            yuanlin_tlw.customers AS count
           FROM yuanlin_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) yuanlin_tlw("time", customers)
        UNION
         SELECT '1B08'::text AS site_id,
            zuoying_hola."time" AS ts_hour,
            zuoying_hola.customers AS count
           FROM zuoying_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) zuoying_hola("time", customers)
        UNION
         SELECT '1B20'::text AS site_id,
            changhua_hola."time" AS ts_hour,
            changhua_hola.customers AS count
           FROM changhua_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) changhua_hola("time", customers)
        UNION
         SELECT '1A32'::text AS site_id,
            fengyuan_tlw."time" AS ts_hour,
            fengyuan_tlw.customers AS count
           FROM fengyuan_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) fengyuan_tlw("time", customers)
        UNION
         SELECT '1A03'::text AS site_id,
            dashun_tlw."time" AS ts_hour,
            dashun_tlw.customers AS count
           FROM dashun_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) dashun_tlw("time", customers)
        UNION
         SELECT '1A04'::text AS site_id,
            taichung_tlw."time" AS ts_hour,
            taichung_tlw.customers AS count
           FROM taichung_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) taichung_tlw("time", customers)
        UNION
         SELECT '1B22'::text AS site_id,
            dreammall_hola."time" AS ts_hour,
            dreammall_hola.customers AS count
           FROM dreammall_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) dreammall_hola("time", customers)
        UNION
         SELECT '1B11'::text AS site_id,
            taichung_hola."time" AS ts_hour,
            taichung_hola.customers AS count
           FROM taichung_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) taichung_hola("time", customers)
        UNION
         SELECT '1B09'::text AS site_id,
            jende_hola."time" AS ts_hour,
            jende_hola.customers AS count
           FROM jende_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) jende_hola("time", customers)
        UNION
         SELECT '1B19'::text AS site_id,
            fengshan_hola."time" AS ts_hour,
            fengshan_hola.customers AS count
           FROM fengshan_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) fengshan_hola("time", customers)
        UNION
         SELECT '1A21'::text AS site_id,
            zuoying_tlw."time" AS ts_hour,
            zuoying_tlw.customers AS count
           FROM zuoying_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) zuoying_tlw("time", customers)

        -- Phase 3
        UNION
         SELECT '1A15'::text AS site_id,
            tucheng_tlw."time" AS ts_hour,
            tucheng_tlw.customers AS count
           FROM tucheng_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) tucheng_tlw("time", customers)
        UNION
         SELECT '1A16'::text AS site_id,
            hsinchu_tlw."time" AS ts_hour,
            hsinchu_tlw.customers AS count
           FROM hsinchu_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) hsinchu_tlw("time", customers)
        UNION
         SELECT '1A23'::text AS site_id,
            luodong_tlw."time" AS ts_hour,
            luodong_tlw.customers AS count
           FROM luodong_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) luodong_tlw("time", customers)
        UNION
         SELECT '1A26'::text AS site_id,
            hualien_tlw."time" AS ts_hour,
            hualien_tlw.customers AS count
           FROM hualien_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) hualien_tlw("time", customers)
        UNION
         SELECT '1A35'::text AS site_id,
            sanxia_tlw."time" AS ts_hour,
            sanxia_tlw.customers AS count
           FROM sanxia_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) sanxia_tlw("time", customers)
        UNION
         SELECT '1B10'::text AS site_id,
            luodong_hola."time" AS ts_hour,
            luodong_hola.customers AS count
           FROM luodong_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) luodong_hola("time", customers)
        UNION
         SELECT '1B13'::text AS site_id,
            tucheng_hola."time" AS ts_hour,
            tucheng_hola.customers AS count
           FROM tucheng_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) tucheng_hola("time", customers)
        UNION
         SELECT '1B16'::text AS site_id,
            hsinchu_hola."time" AS ts_hour,
            hsinchu_hola.customers AS count
           FROM hsinchu_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) hsinchu_hola("time", customers)
        UNION
         SELECT '1B24'::text AS site_id,
            sanxia_hola."time" AS ts_hour,
            sanxia_hola.customers AS count
           FROM sanxia_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) sanxia_hola("time", customers)
        UNION
         SELECT '1A17'::text AS site_id,
            zhonghe_tlw."time" AS ts_hour,
            zhonghe_tlw.customers AS count
           FROM zhonghe_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) zhonghe_tlw("time", customers)
        UNION
         SELECT '1B26'::text AS site_id,
            hualien_hola."time" AS ts_hour,
            hualien_hola.customers AS count
           FROM hualien_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) hualien_hola("time", customers)

        -- Phase 4
        UNION
         SELECT '1A01'::text AS site_id,
            nankan_tlw."time" AS ts_hour,
            nankan_tlw.customers AS count
           FROM nankan_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) nankan_tlw("time", customers)
        UNION
         SELECT '1A08'::text AS site_id,
            pingjhen_tlw."time" AS ts_hour,
            pingjhen_tlw.customers AS count
           FROM pingjhen_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) pingjhen_tlw("time", customers)
        UNION
         SELECT '1A27'::text AS site_id,
            bade_tlw."time" AS ts_hour,
            bade_tlw.customers AS count
           FROM bade_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) bade_tlw("time", customers)
        UNION
         SELECT '1A34'::text AS site_id,
            caotun_tlw."time" AS ts_hour,
            caotun_tlw.customers AS count
           FROM caotun_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) caotun_tlw("time", customers)
        UNION
         SELECT '1A18'::text AS site_id,
            pingtung_tlw."time" AS ts_hour,
            pingtung_tlw.customers AS count
           FROM pingtung_tlw(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) pingtung_tlw("time", customers)
        UNION
         SELECT '1B27'::text AS site_id,
            pingtung_hola."time" AS ts_hour,
            pingtung_hola.customers AS count
           FROM pingtung_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) pingtung_hola("time", customers)
        UNION
         SELECT '1B15'::text AS site_id,
            jhongli_hola."time" AS ts_hour,
            jhongli_hola.customers AS count
           FROM jhongli_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) jhongli_hola("time", customers)
        UNION
         SELECT '1B25'::text AS site_id,
            miaoli_hola."time" AS ts_hour,
            miaoli_hola.customers AS count
           FROM miaoli_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) miaoli_hola("time", customers)
        UNION
         SELECT '1B18'::text AS site_id,
            bade_hola."time" AS ts_hour,
            bade_hola.customers AS count
           FROM bade_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) bade_hola("time", customers)
       UNION
         SELECT '1B21'::text AS site_id,
            nankan_hola."time" AS ts_hour,
            nankan_hola.customers AS count
           FROM nankan_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) nankan_hola("time", customers)
        UNION
         SELECT '1B28'::text AS site_id,
            xitun_hola."time" AS ts_hour,
            xitun_hola.customers AS count
           FROM xitun_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xitun_hola("time", customers)
        UNION
         SELECT '1B29'::text AS site_id,
            xinzhuang_hola."time" AS ts_hour,
            xinzhuang_hola.customers AS count
           FROM xinzhuang_hola(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xinzhuang_hola("time", customers)
        ﻿UNION
         SELECT '1S01'::text AS site_id,
            xinyi_hoi."time" AS ts_hour,
            xinyi_hoi.customers AS count
           FROM xinyi_hoi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xinyi_hoi("time", customers)
        UNION
         SELECT '1S01-onsite'::text AS site_id,
            xinyi_hoi_onsite."time" AS ts_hour,
            xinyi_hoi_onsite.customers AS count
           FROM xinyi_hoi_50(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xinyi_hoi_onsite("time", customers)
        UNION
         SELECT '1S01-area'::text AS site_id,
            xinyi_hoi_area."time" AS ts_hour,
            xinyi_hoi_area.customers AS count
           FROM xinyi_hoi_area(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) xinyi_hoi_area("time", customers)
        UNION
         SELECT '1S02'::text AS site_id,
            neihu_hoi."time" AS ts_hour,
            neihu_hoi.customers AS count
           FROM neihu_hoi(date_trunc('day'::text, timezone('Asia/Taipei'::text, now()))::timestamp with time zone) neihu_hoi("time", customers)
        ) tab
  WHERE date_part('hour'::text, timezone('Asia/Taipei'::text, tab."time"))::integer >= 10 AND date_part('hour'::text, timezone('Asia/Taipei'::text, tab."time"))::integer <= 21;

ALTER TABLE public.customer_count_int
    OWNER TO artichoke;

GRANT SELECT ON TABLE public.customer_count_int TO shiny;
GRANT ALL ON TABLE public.customer_count_int TO artichoke;
GRANT SELECT ON TABLE public.customer_count_int TO echoi;
