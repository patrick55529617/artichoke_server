--DROP MATERIALIZED VIEW mac_sniffer CASCADE;

CREATE MATERIALIZED VIEW mac_sniffer AS
SELECT DISTINCT(sa) as mac,
		min(rt) as first_visit,
		max(rt) as last_visit,
		count(distinct(date_trunc('day', rt AT TIME ZONE 'Asia/Taipei'))) as visit_count,
		max(rssi) as rssi,
		first_value(cname) over(partition by sa) as oui,
        sniffer
    FROM rawdata
    WHERE
		cname NOT LIKE '%Random%' and
		cname = ANY(mobile_oui())
    GROUP BY sa, sniffer, cname;

CREATE UNIQUE INDEX mac_sniffer_idx ON mac_sniffer (mac, sniffer);

--REFRESH MATERIALIZED VIEW CONCURRENTLY mac_sniffer;
