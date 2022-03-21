﻿-- FUNCTION: public.taiwan_android_oui()

-- DROP FUNCTION public.taiwan_android_oui();

CREATE OR REPLACE FUNCTION public.taiwan_android_oui(
	)
    RETURNS character[]
    LANGUAGE 'plpgsql'

AS $BODY$

DECLARE
BEGIN
    RETURN ARRAY['SamsungE',
        'Htc',
        'HTC',
        'SonyMobi',
        'AsustekC',
        'ASUSTekC',
        'Guangdon',
        'XiaomiCo',
        'LgElectr',
        'LGElectr',
        'HuaweiTe',
        'Zte',
        'zte',
        -- 2020/10/13 新增村田 (三星獵戶座)
        'MurataMa',
        -- 2020/10/8 新增
        'vivoMobi', -- VIVO 手機
        'HMDGloba', -- NOKIA (HMD global; 鴻海)
        'Motorola', -- MOTO 手機
        'RealmeCh', -- Realme 手機
        -- 2021/7/2 新增 (原 SonyMobi 調整為 Sony)
        'Sony'
        ];
END;

$BODY$;
