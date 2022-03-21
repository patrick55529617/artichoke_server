-- Table: public.site_info

-- DROP TABLE public.site_info;

CREATE TABLE public.site_info
(
    site_id character varying NOT NULL,
    country character varying(16) NOT NULL,
    sname character varying,
    channel character varying NOT NULL,
    open_hour time with time zone NOT NULL DEFAULT '10:00:00+08'::time with time zone,
    sniffer character varying[],
    city_enc character varying,
    func character varying[],
    is_active boolean NOT NULL DEFAULT false,
    closed_hour time with time zone DEFAULT '22:00:00+08'::time with time zone,
    is_released boolean NOT NULL DEFAULT false,
    CONSTRAINT site_info_pkey PRIMARY KEY (site_id)
)
