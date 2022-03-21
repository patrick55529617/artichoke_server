CREATE TABLE "74da38cd2d89".rawdata
(
    rt timestamp with time zone NOT NULL,
    sa character(12) NOT NULL,
    da character(12) NOT NULL,
    rssi smallint NOT NULL,
    seqno integer NOT NULL,
    cname character varying(16) DEFAULT ''::character varying,
    pkt_type smallint NOT NULL,
    pkt_subtype smallint NOT NULL,
    ssid character varying(32) DEFAULT ''::character varying,
    channel smallint NOT NULL
) 
PARTITION BY RANGE (rt)
WITH (
    OIDS = TRUE
);

CREATE TABLE "74da38cd2d89".rawdata_2017 PARTITION OF "74da38cd2d89".rawdata
    FOR VALUES FROM ('2017-01-01 00:00:00+08') TO ('2018-01-01 00:00:00+8')
    PARTITION BY RANGE (rt)
    WITH ( OIDS = TRUE );

CREATE TABLE "74da38cd2d89".rawdata_2017_11 PARTITION OF "74da38cd2d89".rawdata_2017
    FOR VALUES FROM ('2017-11-01 00:00:00+08') TO ('2017-12-01 00:00:00+08')
    WITH ( OIDS = TRUE );
ALTER TABLE "74da38cd2d89".rawdata_2017_11 ADD PRIMARY KEY (rt, sa);

CREATE TABLE "74da38cd2d89".rawdata_2017_12 PARTITION OF "74da38cd2d89".rawdata_2017
    FOR VALUES FROM ('2017-12-01 00:00:00+08') TO ('2018-12-01 00:00:00+08')
    WITH ( OIDS = TRUE );
ALTER TABLE "74da38cd2d89".rawdata_2017_12 ADD PRIMARY KEY (rt, sa);
