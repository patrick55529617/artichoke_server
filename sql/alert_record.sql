-- Table: public.alert_severity_info

-- DROP TABLE public.alert_severity_info;

CREATE TABLE public.alert_severity_info
(
    id smallint NOT NULL,
    severity_name character varying(2) NOT NULL,
    description text,
    PRIMARY KEY (id)
);

-- Insert alert_severity_info
INSERT INTO public.alert_severity_info VALUES
    (1, 'L1', 'Critical severity, need to resolve in real time.'),
    (2, 'L2', 'Normal severity, can resolve after working.')
;


-- DROP TABLE public.alert_record;

CREATE TABLE public.alert_record
(
    severity_id smallint NOT NULL,
    sniffer_id character varying(12) NOT NULL,
    alert_report_time timestamp with time zone,
    rawdata json NOT NULL,
    PRIMARY KEY (severity_id, alert_report_time),
    CONSTRAINT fk_severity_id
        FOREIGN KEY(severity_id)
            REFERENCES alert_severity_info(id)
);
