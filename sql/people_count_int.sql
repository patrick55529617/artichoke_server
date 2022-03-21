﻿-- Table: public.people_count_int

-- DROP TABLE public.people_count_int;

CREATE TABLE public.people_count_int
(
    site_id text COLLATE pg_catalog."default" NOT NULL,
    "time" timestamp with time zone NOT NULL,
    count bigint,
    CONSTRAINT people_count_int_pkey PRIMARY KEY (site_id, "time")
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.people_count_int
    OWNER to artichoke;
