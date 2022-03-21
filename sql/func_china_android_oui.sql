﻿-- FUNCTION: public.china_android_oui()

-- DROP FUNCTION public.china_android_oui();

CREATE OR REPLACE FUNCTION public.china_android_oui(
	)
    RETURNS character[]
    LANGUAGE 'plpgsql'

AS $BODY$

DECLARE
BEGIN
	RETURN ARRAY['Guangdon',
	    'HuaweiTe',
	    'XiaomiCo',
	    'VivoMobi',
	    'SamsungE',
	    'Motorola',
	    'AsustekC',
	    'Htc',
	    'SonyMobi',
	    'Zte',
	    'MeizuTec',
	    'LenovoMo',
	    'OneplusT',
	    'GioneeCo',
	    'LetvMobi'];
END;

$BODY$;

