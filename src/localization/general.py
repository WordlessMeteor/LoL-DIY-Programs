'''
本模块存储各语言内容相同的字典。这类字典的键是要引用的字符串、整数或浮点数，值是本地化内容。<br>This module stores dictionaries whose content is the same in different languages. Such dictionaries' keys are strings, integers and floats to cite and values are localized content）

语言文化代码不符合上述规则，但因为其通用性也放在此模块。<br>Although locales don't fit the above rules, they're put in this module due to universality.
'''
#语言文化代码（Locales）
language_ddragon: dict[str, dict[str, str]] = {
    "ar_AE": {
        "desc_en": "Arabic (United Arab Emirates)",
        "desc_zh": "阿拉伯语（阿拉伯联合酋长国）",
        "desc_local": "العربية (الإمارات العربية المتحدة)",
        "Available CDragon Data Patches": "9.20～10.1, 13.20+"
    },
    "cs_CZ": {
        "desc_en": "Czech (Czech Republic)",
        "desc_zh": "捷克语（捷克共和国）",
        "desc_local": "Čeština (Česká republika)",
        "Available CDragon Data Patches": "7.1+"
    },
    "el_GR": {
        "desc_en": "Greek (Greece)",
        "desc_zh": "希腊语（希腊）",
        "desc_local": "Ελληνικά (Ελλάδα)",
        "Available CDragon Data Patches": "7.1+"
    },
    "pl_PL": {
        "desc_en": "Polish (Poland)",
        "desc_zh": "波兰语（波兰）",
        "desc_local": "Polski (Polska)",
        "Available CDragon Data Patches": "7.1+"
    },
    "ro_RO": {
        "desc_en": "Romanian (Romania)",
        "desc_zh": "罗马尼亚语（罗马尼亚）",
        "desc_local": "Română (România)",
        "Available CDragon Data Patches": "7.1+"
    },
    "hu_HU": {
        "desc_en": "Hungarian (Hungary)",
        "desc_zh": "匈牙利语（匈牙利）",
        "desc_local": "Magyar (Magyarország)",
        "Available CDragon Data Patches": "7.1+"
    },
    "en_GB": {
        "desc_en": "English (United Kingdom)",
        "desc_zh": "英语（英国）",
        "desc_local": "English (United Kingdom)",
        "Available CDragon Data Patches": "7.1+"
    },
    "de_DE": {
        "desc_en": "German (Germany)",
        "desc_zh": "德语（德国）",
        "desc_local": "Deutsch (Deutschland)",
        "Available CDragon Data Patches": "7.1+"
    },
    "es_ES": {
        "desc_en": "Spanish (Spain)",
        "desc_zh": "西班牙语（西班牙）",
        "desc_local": "Español (España)",
        "Available CDragon Data Patches": "7.1+"
    },
    "it_IT": {
        "desc_en": "Italian (Italy)",
        "desc_zh": "意大利语（意大利）",
        "desc_local": "Italiano (Italia)",
        "Available CDragon Data Patches": "7.1+"
    },
    "fr_FR": {
        "desc_en": "French (France)",
        "desc_zh": "法语（法国）",
        "desc_local": "Français (France)",
        "Available CDragon Data Patches": "7.1+"
    },
    "ja_JP": {
        "desc_en": "Japanese (Japan)",
        "desc_zh": "日语（日本）",
        "desc_local": "日本語 (日本)",
        "Available CDragon Data Patches": "7.1+"
    },
    "ko_KR": {
        "desc_en": "Korean (Korea)",
        "desc_zh": "朝鲜语（韩国）",
        "desc_local": "한국어 (대한민국)",
        "Available CDragon Data Patches": "9.7+"
    },
    "es_MX": {
        "desc_en": "Spanish (Mexico)",
        "desc_zh": "西班牙语（墨西哥）",
        "desc_local": "Español (México)",
        "Available CDragon Data Patches": "7.1+"
    },
    "es_AR": {
        "desc_en": "Spanish (Argentina)",
        "desc_zh": "西班牙语（阿根廷）",
        "desc_local": "Español (Argentina)",
        "Available CDragon Data Patches": "9.7+"
    },
    "pt_BR": {
        "desc_en": "Portuguese (Brazil)",
        "desc_zh": "葡萄牙语（巴西）",
        "desc_local": "Português (Brasil)",
        "Available CDragon Data Patches": "7.1+"
    },
    "en_US": {
        "desc_en": "English (United States)",
        "desc_zh": "英语（美国）",
        "desc_local": "English (United States)",
        "Available CDragon Data Patches": "7.1+"
    },
    "en_AU": {
        "desc_en": "English (Australia)",
        "desc_zh": "英语（澳大利亚）",
        "desc_local": "English (Australia)",
        "Available CDragon Data Patches": "7.1+"
    },
    "ru_RU": {
        "desc_en": "Russian (Russia)",
        "desc_zh": "俄语（俄罗斯）",
        "desc_local": "Русский (Россия)",
        "Available CDragon Data Patches": "7.1+"
    },
    "tr_TR": {
        "desc_en": "Turkish (Turkey)",
        "desc_zh": "土耳其语（土耳其）",
        "desc_local": "Türkçe (Türkiye)",
        "Available CDragon Data Patches": "7.1+"
    },
    "ms_MY": {
        "desc_en": "Malay (Malaysia)",
        "desc_zh": "马来语（马来西亚）",
        "desc_local": "Bahasa Melayu (Malaysia)",
        "Available CDragon Data Patches": ""
    },
    "en_PH": {
        "desc_en": "English (Republic of the Philippines)",
        "desc_zh": "英语（菲律宾共和国）",
        "desc_local": "English (Pilipinas)",
        "Available CDragon Data Patches": "10.5+"
    },
    "en_SG": {
        "desc_en": "English (Singapore)",
        "desc_zh": "英语（新加坡）",
        "desc_local": "English (Singapore)",
        "Available CDragon Data Patches": "10.5+"
    },
    "th_TH": {
        "desc_en": "Thai (Thailand)",
        "desc_zh": "泰语（泰国）",
        "desc_local": "ภาษาไทย (ประเทศไทย)",
        "Available CDragon Data Patches": "9.7+"
    },
    "vn_VN": {
        "desc_en": "Vietnamese (Viet Nam)",
        "desc_zh": "越南语（越南）",
        "desc_local": "Tiếng Việt (Việt Nam)",
        "Available CDragon Data Patches": "9.7～13.9"
    },
    "vi_VN": {
        "desc_en": "Vietnamese (Viet Nam)",
        "desc_zh": "越南语（越南）",
        "desc_local": "Tiếng Việt (Việt Nam)",
        "Available CDragon Data Patches": "12.17+"
    },
    "id_ID": {
        "desc_en": "Indonesian (Indonesia)",
        "desc_zh": "印度尼西亚语（印度尼西亚）",
        "desc_local": "Bahasa Indonesia (Indonesia)",
        "Available CDragon Data Patches": "15.5+"
    },
    "zh_MY": {
        "desc_en": "Chinese (Malaysia)",
        "desc_zh": "中文（马来西亚）",
        "desc_local": "中文 (马来西亚)",
        "Available CDragon Data Patches": "10.5+"
    },
    "zh_CN": {
        "desc_en": "Chinese (China)",
        "desc_zh": "中文（中国）",
        "desc_local": "中文 (中国)",
        "Available CDragon Data Patches": "9.7+"
    },
    "zh_TW": {
        "desc_en": "Chinese (Taiwan)",
        "desc_zh": "中文（台湾）",
        "desc_local": "中文 (台灣)",
        "Available CDragon Data Patches": "9.7+"
    }
}
language_cdragon: dict[str, str] = {key: "default" if key == "en_US" else key.lower() for key in language_ddragon} #在CommunityDragon数据库上，美服正式服的数据资源代码是default，而不是小写的en_US（The code for English (US) data resources on CommunityDragon database is "default" instead of the lowercase of "en_US"）
language_dict: dict[str, list[int | str]] = {"No.": list(range(1, len(language_ddragon) + 1)), "CODE": list(language_ddragon.keys()), "LANGUAGE": list(map(lambda x: x["desc_local"], language_ddragon.values())), "Available CDragon Data Patches": list(map(lambda x: x["Available CDragon Data Patches"], language_ddragon.values()))} #本来考虑把可用CDragon数据版本放在第三列，但是后来发现表头名字太长了，索性放在最后了（I had considered putting "Available CDragon Data Patches" at the third column, but then found the header was too long. So I put it at the last column）

#通用字典（General dictionaries）
zoom_scale_dict: dict[float, str] = {
    0.8: "1024 × 576",
    1.0: "1280 × 720",
    1.25: "1600 × 900",
    1.5: "1920 × 1080"
}
queueAvailability_dict: dict[str, str] = {
    "Available": "√",
    "PlatformDisabled": ""
}
