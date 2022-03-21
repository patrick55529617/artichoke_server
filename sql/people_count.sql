﻿-- Table: public.people_count

-- DROP TABLE public.people_count;

CREATE TABLE public.people_count
(
    site_id text COLLATE pg_catalog."default" NOT NULL,
    "time" timestamp with time zone NOT NULL,
    count bigint,
    CONSTRAINT people_count_pkey PRIMARY KEY (site_id, "time")
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

ALTER TABLE public.people_count
    OWNER to artichoke;
