CREATE OR REPLACE FUNCTION public.mobile_oui(
	)
    RETURNS character[]
    LANGUAGE 'plpgsql'

AS $BODY$

DECLARE
BEGIN
    RETURN ARRAY[
        'Apple_iOS',
        'Apple',
        'SamsungE',
        'Htc',
        'SonyMobi',
        'AsustekC',
        'Guangdon',
        'XiaomiCo',
        'LgElectr',
        'HuaweiTe',
        'Zte',
        'Guangdon',
	    'VivoMobi',
	    'Motorola',
	    'Zte',
	    'MeizuTec',
	    'LenovoMo',
	    'OneplusT',
	    'GioneeCo',
	    'LetvMobi',
	    'Smartisa',
	    'Lemobile'];
END;

$BODY$
