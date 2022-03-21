CREATE TABLE mqtt_acl (
  id SERIAL primary key,
  allow integer,
  ipaddr character varying(60),
  username character varying(100),
  clientid character varying(100),
  access  integer,
  topic character varying(100)
);

COMMENT ON COLUMN public.mqtt_acl.allow IS '0: deny, 1: allow';
COMMENT ON COLUMN public.mqtt_acl.access IS '1: subscribe, 2: publish, 3: pubsub';
COMMENT ON COLUMN public.mqtt_acl.topic IS 'Topic Filter';
