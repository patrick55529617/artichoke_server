﻿CREATE OR REPLACE FUNCTION public.sniffers_tlw(
	)
    RETURNS character[]
    LANGUAGE 'plpgsql'

AS $BODY$

DECLARE
BEGIN
    RETURN ARRAY['74da38b994b2',
        '74da38cd2ea0',
        '74da38cd2d89',
        '74da38cd2e95',
        '74da38cd3017',
        '74da38cd2ffa',
        '74da38b99297',
        '74da38b992a1'];
END;

$BODY$;
