CREATE OR REPLACE FUNCTION public.sniffers_hola(
	)
    RETURNS character[]
    LANGUAGE 'plpgsql'

AS $BODY$

DECLARE
BEGIN
    RETURN ARRAY['74da38b994d2',
        		'74da38b992b6',
        		'74da38b994d1',
        		'74da38cd2eae',
        		'74da38cd2d8e',
        		'74da38cd301c',
        		'74da38cd2ffe',
        		'74da38cd3009',
                '74da38b99298',
                '74da38b9929c',
                '74da38b9929a',
                '74da38b99282',
                '74da38b992a3',
                '74da38b99287'];
END;

$BODY$;
