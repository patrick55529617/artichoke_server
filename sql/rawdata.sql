﻿CREATE TABLE rawdata
(
    rt timestamp with time zone NOT NULL,
    sa character(12) COLLATE pg_catalog."default" NOT NULL,
    da character(12) COLLATE pg_catalog."default" NOT NULL,
    rssi smallint NOT NULL,
    seqno integer NOT NULL,
    cname character varying(16) COLLATE pg_catalog."default" DEFAULT ''::character varying,
    pkt_type smallint NOT NULL,
    pkt_subtype smallint NOT NULL,
    ssid character varying(32) COLLATE pg_catalog."default" DEFAULT ''::character varying,
    channel smallint NOT NULL,
    upload_time timestamp with time zone,
    delivery_time timestamp with time zone,
    sniffer character(12) COLLATE pg_catalog."default" NOT NULL
) PARTITION BY LIST (sniffer)


GRANT SELECT ON TABLE public.rawdata TO dw;
