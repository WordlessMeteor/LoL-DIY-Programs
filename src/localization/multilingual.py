'''
本模块收录同时含有多种语言的本地化内容的字典。一级键是要引用的字符串、整数或者浮点数，二级键是语言文化代码，二级值是本地化字符串。<br>This module collects dictionaries that contain localized content in multiple languages. Level 1 keys are strings, integers or floats to cite, Level 2 keys are locales and Level 2 values are localized strings.
'''
gamemodes: dict[str, dict[str, str]] = {
    "ARAM": {
        "zh_CN": "极地大乱斗",
        "en_US": "ARAM"
    },
    "ARAM_BOT": {
        "zh_CN": "极地大乱斗 5v5 人机",
        "en_US": "ARAM 5v5 Bots"
    },
    "ARAM_CLASH": {
        "zh_CN": "极地大乱斗 冠军杯赛",
        "en_US": "ARAM Clash"
    },
    "ARAM_UNRANKED_1x1": {
        "zh_CN": "极地大乱斗 1v1",
        "en_US": "ARAM 1v1"
    },
    "ARAM_UNRANKED_2x2": {
        "zh_CN": "极地大乱斗 2v2",
        "en_US": "ARAM 2v2"
    },
    "ARAM_UNRANKED_3x3": {
        "zh_CN": "极地大乱斗 3v3",
        "en_US": "ARAM 3v3"
    },
    "ARAM_UNRANKED_5x5": {
        "zh_CN": "极地大乱斗",
        "en_US": "ARAM"
    },
    "ARAM_UNRANKED_6x6": {
        "zh_CN": "极地大乱斗 六杀争夺战",
        "en_US": "ARAM Hexakill"
    },
    "ARSR": {
        "zh_CN": "峡谷大乱斗",
        "en_US": "All Random Summoner's Rift"
    },
    "ASCENSION": {
        "zh_CN": "飞升争夺战",
        "en_US": "Ascension"
    },
    "ASSASSINATE": {
        "zh_CN": "红月决",
        "en_US": "Hunt of the Blood Moon"
    },
    "BILGEWATER": {
        "zh_CN": "佣兵大作战",
        "en_US": "Black Market Brawlers"
    },
    "BILGEWATER_ARAM-5x5": {
        "zh_CN": "屠夫之桥",
        "en_US": "Butcher's Bridge"
    },
    "BOT": {
        "zh_CN": "人机对战",
        "en_US": "Co-op vs. Ai"
    },
    "BOT_3x3": {
        "zh_CN": "人机对战 扭曲丛林",
        "en_US": "Co-op vs. Ai Twisted Treeline"
    },
    "BRAWL": {
        "zh_CN": "神木之门",
        "en_US": "Brawl"
    },
    "CAP_1x1": {
        "zh_CN": "新手教程 最终部分",
        "en_US": "Tutorial Capstone"
    },
    "CAP_5x5": {
        "zh_CN": "新手教程 最终部分",
        "en_US": "Tutorial Capstone"
    },
    "CHERRY": {
        "zh_CN": "斗魂竞技场",
        "en_US": "Arena"
    },
    "CHERRY_UNRANKED": {
        "zh_CN": "斗魂竞技场",
        "en_US": "Arena"
    },
    "CHONCC_TREASURE_TFT": {
        "zh_CN": "云顶之弈 (恭喜发财)",
        "en_US": "Choncc's Treasure"
    },
    "CLASH": {
        "zh_CN": "冠军杯赛",
        "en_US": "Clash"
    },
    "CLASSIC": {
        "zh_CN": "召唤师峡谷",
        "en_US": "Summoner's Rift"
    },
    "COUNTER_PICK": {
        "zh_CN": "互选征召赛",
        "en_US": "Nemesis Draft"
    },
    "DARKSTAR": {
        "zh_CN": "暗星：奇点",
        "en_US": "Dark Star: Singularity"
    },
    "DOOMBOTSTEEMO": {
        "zh_CN": "末日人工智能",
        "en_US": "Doom Bots"
    },
    "FIRSTBLOOD": {
        "zh_CN": "大对决",
        "en_US": "Showdown"
    },
    "FIRSTBLOOD_1x1": {
        "zh_CN": "大对决 1v1",
        "en_US": "Showdown 1v1"
    },
    "FIRSTBLOOD_2x2": {
        "zh_CN": "大对决 2v2",
        "en_US": "Showdown 2v2"
    },
    "FIVE_YEAR_ANNIVERSARY_TFT": {
        "zh_CN": "6周年时光机",
        "en_US": "Pengu's Party"
    },
    "GAMEMODEX": {
        "zh_CN": "极限闪击",
        "en_US": "Nexus Blitz (Pre-release)"
    },
    "HEXAKILL": {
        "zh_CN": "六杀争夺战 扭曲丛林",
        "en_US": "Hexakill Twisted Treeline"
    },
    "JADE": {
        "zh_CN": "英雄联盟经典模式",
        "en_US": "League Classic"
    },
    "JADE_BOT": {
        "zh_CN": "英雄联盟经典模式 人机对战",
        "en_US": "League Classic Co-op vs. AI"
    },
    "JADE_RANKED_SOLO_5x5": {
        "zh_CN": "英雄联盟经典模式 排位赛 单排/双排",
        "en_US": "League Classic Ranked Solo / Duo"
    },
    "KINGPORO": {
        "zh_CN": "魄罗大乱斗",
        "en_US": "Legend of the Poro King"
    },
    "KING_PORO": {
        "zh_CN": "魄罗大乱斗",
        "en_US": "Legend of the Poro King"
    },
    "KIWI": {
        "zh_CN": "海克斯大乱斗",
        "en_US": "ARAM: Mayhem"
    },
    "KIWI_JADE": {
        "zh_CN": "海克斯大乱斗 经典模式版",
        "en_US": "ARAM: Mayhem Classic-ish"
    },
    "LNY23_TFT": {
        "zh_CN": "云顶之弈 (恭喜发财)",
        "en_US": "Choncc's Treasure"
    },
    "LNY24_TFT": {
        "zh_CN": "云顶之弈 (恭喜发财)",
        "en_US": "Choncc's Treasure"
    },
    "LNY25_TFT": {
        "zh_CN": "云顶之弈 (恭喜发财)",
        "en_US": "Choncc's Treasure"
    },
    "NEXUSBLITZ": {
        "zh_CN": "极限闪击",
        "en_US": "Nexus Blitz"
    },
    "NIGHTMARE_BOT": {
        "zh_CN": "末日人工智能",
        "en_US": "Doom Bots"
    },
    "NORMAL": {
        "zh_CN": "匹配模式",
        "en_US": "Normal"
    },
    "NORMAL_1x1": {
        "zh_CN": "匹配模式 1v1",
        "en_US": "Normal 1v1"
    },
    "NORMAL_3x3": {
        "zh_CN": "匹配模式 3v3",
        "en_US": "Normal 3v3"
    },
    "NORMAL-QUICKPLAY-SR-TB-5x5": {
        "zh_CN": "快速模式（召唤师峡谷与班德尔之森）",
        "en_US": "Quickplay (Summoner's Rift and The Bandlewood)"
    },
    "NORMAL_TFT": {
        "zh_CN": "云顶之弈（匹配模式）",
        "en_US": "Normal (TFT)"
    },
    "ODIN": {
        "zh_CN": "统治战场",
        "en_US": "Dominion"
    },
    "ODIN_RANKED_TEAM": {
        "zh_CN": "统治战场 排位赛",
        "en_US": "Dominion Ranked"
    },
    "ODIN_RANKED_SOLO": {
        "zh_CN": "统治战场 排位赛 单人",
        "en_US": "Dominion Ranked Solo"
    },
    "ODIN_UNRANKED": {
        "zh_CN": "统治战场",
        "en_US": "Dominion"
    },
    "ODYSSEY": {
        "zh_CN": "奥德赛",
        "en_US": "Odyssey: Extraction"
    },
    "ONEFORALL": {
        "zh_CN": "克隆大作战",
        "en_US": "One for All"
    },
    "ONEFORALL_5x5": {
        "zh_CN": "克隆大作战 5v5",
        "en_US": "One for All 5v5"
    },
    "PRACTICETOOL": {
        "zh_CN": "训练模式",
        "en_US": "Practice Tool"
    },
    "PROJECT": {
        "zh_CN": "超频行动",
        "en_US": "Overcharge"
    },
    "PROMETHIUM_TFT": {
        "zh_CN": "敖兴之峰",
        "en_US": "Ao Shin's Ascent"
    },
    "PVE_PUZZLE_TFT": {
        "zh_CN": "发条鸟的试炼",
        "en_US": "Tocker's Trials"
    },
    "RANKED_FLEX_SR": {
        "zh_CN": "排位赛 灵活排位",
        "en_US": "Ranked Flex"
    },
    "RANKED_FLEX_SR_5x5": {
        "zh_CN": "排位赛 灵活排位 5v5",
        "en_US": "Ranked Flex 5v5"
    },
    "RANKED_FLEX_TT": {
        "zh_CN": "排位赛 灵活排位 扭曲丛林",
        "en_US": "Ranked Flex Twisted Treeline"
    },
    "RANKED_PREMADE-3x3": {
        "zh_CN": "排位赛 预组队 3v3",
        "en_US": "Ranked Premade 3v3"
    },
    "RANKED_SOLO_1x1": {
        "zh_CN": "排位赛 单排/双排 1v1",
        "en_US": "Ranked Solo/Duo 1v1"
    },
    "RANKED_SOLO_5x5": {
        "zh_CN": "排位赛 单排/双排",
        "en_US": "Ranked Solo/Duo"
    },
    "RANKED_TEAM_3x3": {
        "zh_CN": "排位赛 战队 扭曲丛林",
        "en_US": "Ranked Team 3v3"
    },
    "RANKED_TEAMPLAY_TT": {
        "zh_CN": "扭曲丛林 排位赛",
        "en_US": "Twisted Treeline Ranked"
    },
    "RANKED_TEAM_5x5": {
        "zh_CN": "排位赛 战队 召唤师峡谷",
        "en_US": "Ranked Team 5v5"
    },
    "RANKED_TFT": {
        "zh_CN": "云顶之弈 (排位赛)",
        "en_US": "Teamfight Tactics (Ranked)"
    },
    "RANKED_TFT_DOUBLE_UP": {
        "zh_CN": "云顶之弈 (双人作战)",
        "en_US": "Teamfight Tactics (Double Up)"
    },
    "RANKED_TFT_PAIRS": {
        "zh_CN": "云顶之弈 (双人作战)",
        "en_US": "Teamfight Tactics (Double Up)"
    },
    "RANKED_TFT_TURBO": {
        "zh_CN": "云顶之弈(狂暴模式)",
        "en_US": "Teamfight Tactics (Hyper Roll)"
    },
    "RIOTSCRIPT_BOT": {
        "zh_CN": "人机对战",
        "en_US": "Co-op vs. Ai"
    },
    "RUBY": {
        "zh_CN": "末日人工智能",
        "en_US": "Doom Bots"
    },
    "RUBY_TRIAL_1": {
        "zh_CN": "末日人工智能 - 维迦的诅咒！",
        "en_US": "Doom Bots - Veigar's Curse!"
    },
    "RUBY_TRIAL_2": {
        "zh_CN": "末日人工智能 - 维迦的邪咒！",
        "en_US": "Doom Bots - Veigar's Evil!"
    },
    "RUBY_TRIAL_3": {
        "zh_CN": "末日人工智能 - 维迦的末日厄咒！",
        "en_US": "Doom Bots - Veigar's Doom!"
    },
    "SET_REVIVAL_5_5_TFT": {
        "zh_CN": "回归赛季：英雄之黎明重现",
        "en_US": "Revival: Dawn of Heroes"
    },
    "SET_REVIVAL_TFT": {
        "zh_CN": "回归赛季：瑞兽再闹新春",
        "en_US": "Revival: Festival of Beasts"
    },
    "SF_TFT": {
        "zh_CN": "云顶之弈 (斗魂锦标赛)",
        "en_US": "Teamfight Tactics (Soul Brawl)"
    },
    "SIEGE": {
        "zh_CN": "枢纽攻防战",
        "en_US": "Nexus Siege"
    },
    "SNOWURF": {
        "zh_CN": "冰雪无限火力",
        "en_US": "Snow Battle ARURF"
    },
    "SR-BOTS_INTRO-TB-5x5": {
        "zh_CN": "人机对战 入门级（召唤师峡谷和班德尔之森）",
        "en_US": "Co-op vs. AI Intro (Summoner's Rift and The Bandlewood)"
    },
    "SOLO_DUO_RANKED_5x5": {
        "zh_CN": "排位赛 单排/双排",
        "en_US": "Ranked Solo/Duo"
    },
    "SR_6x6": {
        "zh_CN": "六杀争夺战 召唤师峡谷",
        "en_US": "Hexakill Summoner's Rift"
    },
    "STARGUARDIAN": {
        "zh_CN": "怪兽入侵",
        "en_US": "Invasion"
    },
    "STRAWBERRY": {
        "zh_CN": "无尽狂潮",
        "en_US": "Swarm"
    },
    "SWIFTPLAY": {
        "zh_CN": "快速模式",
        "en_US": "Swiftplay"
    },
    "TEAM_BUILDER_BLIND-5x5": {
        "zh_CN": "阵容匹配 自选 5v5",
        "en_US": "Team Builder Blind 5v5"
    },
    "TEAM_BUILDER_DRAFT_UNRANKED_1x1": {
        "zh_CN": "阵容匹配 征召 1v1",
        "en_US": "Team Builder Draft 1v1"
    },
    "TFT": {
        "zh_CN": "云顶之弈（匹配模式）",
        "en_US": "Normal (TFT)"
    },
    "TURBO_TFT": {
        "zh_CN": "云顶之弈(狂暴模式)",
        "en_US": "Teamfight Tactics (Hyper Roll)"
    },
    "TUTORIAL": {
        "zh_CN": "新手教程",
        "en_US": "Tutorial"
    },
    "TUTORIAL_MODULE_1": {
        "zh_CN": "新手教程 第一部分",
        "en_US": "Tutorial Part 1"
    },
    "TUTORIAL_MODULE_2": {
        "zh_CN": "新手教程 第二部分",
        "en_US": "Tutorial Part 2"
    },
    "TUTORIAL_MODULE_3": {
        "zh_CN": "新手教程 第三部分",
        "en_US": "Tutorial Part 3"
    },
    "TUTORIAL_TFT": {
        "zh_CN": "云顶之弈 (新手教程)",
        "en_US": "Teamfight Tactics (Tutorial)"
    },
    "ULTBOOK": {
        "zh_CN": "终极魔典",
        "en_US": "Ultimate Spellbook"
    },
    "URF": {
        "zh_CN": "无限火力",
        "en_US": "Ultra Rapid Fire"
    },
    "URF_BOT": {
        "zh_CN": "无限火力 人机对战",
        "en_US": "Ultra Rapid Fire Bots 5v5"
    },
    "URF_CLASH": {
        "zh_CN": "无限乱斗 冠军杯赛",
        "en_US": "URF Clash"
    }
} #来源（Source）：/lol-platform-config/v1/namespaces/DisabledChampions; /lol-platform-config/v1/namespaces/ChampionMasteryConfig
gamemaps: dict[int, dict[str, str]] = {
    0: {
        "zh_CN": "测试地图0",
        "en_US": "Test Map 0"
    },
    1: {
        "zh_CN": "召唤师峡谷 夏季怀旧版",
        "en_US": "Summoner's Rift Original Summoner Variant"
    },
    2: {
        "zh_CN": "召唤师峡谷 万圣节怀旧版",
        "en_US": "Summoner's Rift Original Autumn (Harrowing) Variant"
    },
    3: {
        "zh_CN": "试炼之地",
        "en_US": "The Proving Grounds"
    },
    4: {
        "zh_CN": "熔岩大厅",
        "en_US": "Magma Chamber"
    },
    7: {
        "zh_CN": "召唤师峡谷",
        "en_US": "Summoner's Rift"
    },
    8: {
        "zh_CN": "水晶之痕",
        "en_US": "Crystal Scar"
    },
    10: {
        "zh_CN": "扭曲丛林",
        "en_US": "Twisted Treeline"
    },
    11: {
        "zh_CN": "召唤师峡谷",
        "en_US": "Summoner's Rift"
    },
    12: {
        "zh_CN": "随机地图",
        "en_US": "Random Map"
    },
    13: {
        "zh_CN": "召唤师峡谷",
        "en_US": "Summoner's Rift"
    },
    14: {
        "zh_CN": "屠夫之桥",
        "en_US": "Butcher's Bridge"
    },
    16: {
        "zh_CN": "星界废墟",
        "en_US": "Cosmic Ruins"
    },
    18: {
        "zh_CN": "瓦洛兰城市公园",
        "en_US": "Valoran City Park"
    },
    19: {
        "zh_CN": "第43区",
        "en_US": "Substructure 43"
    },
    20: {
        "zh_CN": "飞船坠落点",
        "en_US": "Crash Site"
    },
    21: {
        "zh_CN": "百合与莲花的神庙",
        "en_US": "Temple of Lily and Lotus"
    },
    22: {
        "zh_CN": "聚点危机",
        "en_US": "Convergence"
    },
    30: {
        "zh_CN": "怒火角斗场",
        "en_US": "Rings of Wrath"
    },
    33: {
        "zh_CN": "最终都市",
        "en_US": "Final City"
    },
    35: {
        "zh_CN": "班德尔之森",
        "en_US": "The Bandlewood"
    },
    90: {
        "zh_CN": "第五赛季季前赛测试地图",
        "en_US": "Pre-Season 5 Testing Map"
    },
    453: {
        "zh_CN": "经典召唤师峡谷",
        "en_US": "Classic Rift"
    },
    601: {
        "zh_CN": "测试地图601",
        "en_US": "Test Map 601"
    },
    911: {
        "zh_CN": "测试地图911",
        "en_US": "Test Map 911"
    }
}
ARAMmaps: dict[str, dict[str, str]] = {
    "NONE": {
        "zh_CN": "嚎哭深渊",
        "en_US": "Howling Abyss"
    },
    "MapSkin_Map12_Bloom": {
        "zh_CN": "莲华栈桥",
        "en_US": "Koeshin's Crossing"
    },
    "MapSkin_HA_Bilgewater": {
        "zh_CN": "屠夫之桥",
        "en_US": "Butcher's Bridge"
    },
    "MapSkin_HA_Crepe": {
        "zh_CN": "进步之桥",
        "en_US": "Bridge of Progress"
    },
    "MapSkin_Map12_Jade": {
        "zh_CN": "召唤师峡谷？",
        "en_US": "SR?"
    }
}
gameTypes_config: dict[str, dict[str, str]] = {
    "GAME_CFG_PICK_BLIND": {
        "zh_CN": "自选模式（自定义）",
        "en_US": "Blind Pick (custom)"
    },
    "GAME_CFG_DRAFT_STD": {
        "zh_CN": "征召模式（自定义）",
        "en_US": "Draft Mode (custom)"
    },
    "GAME_CFG_DRAFT_NOBAN": {
        "zh_CN": "轮选模式",
        "en_US": "Draft Noban (custom)"
    },
    "GAME_CFG_PICK_RANDOM": {
        "zh_CN": "全随机模式（自定义）",
        "en_US": "All Random (custom)"
    },
    "GAME_CFG_PICK_SIMUL": {
        "zh_CN": "同选模式",
        "en_US": "Simultaneous Pick (custom)"
    },
    "GAME_CFG_DRAFT_TOURNAMENT": {
        "zh_CN": "竞技征召模式（自定义）",
        "en_US": "Tournament Draft (custom)"
    },
    "GAME_CFG_PICK_SIMUL_TD": {
        "zh_CN": "计时征召",
        "en_US": "Timed Draft (custom)"
    },
    "GAME_CFG_BASIC_TUTORIAL": {
        "zh_CN": "基础教程",
        "en_US": "Basic Tutorial"
    },
    "GAME_CFG_ADV_TUTORIAL": {
        "zh_CN": "进阶教程",
        "en_US": "Advanced Tutorial"
    },
    "GAME_CFG_CAP": {
        "zh_CN": "最终教程",
        "en_US": "Capstone Tutorial"
    },
    "GAME_CFG_BLIND_RANDOM": {
        "zh_CN": "盲选随机",
        "en_US": "Blind Random (custom)"
    },
    "GAME_CFG_BLIND_DUPE": {
        "zh_CN": "克隆选择（自定义）",
        "en_US": "All for one (custom)"
    },
    "GAME_CFG_CROSS_DUPE": {
        "zh_CN": "全队克隆",
        "en_US": "All for one (cross-team)"
    },
    "GAME_CFG_BLIND_DRAFT_ST": {
        "zh_CN": "自选征召模式（自定义）",
        "en_US": "Blind Draft Pick (custom)"
    },
    "GAME_CFG_COUNTER_PICK": {
        "zh_CN": "互选模式（自定义）",
        "en_US": "Nemesis Draft (custom)"
    },
    "GAME_CFG_TEAM_BUILDER_DRAFT": {
        "zh_CN": "征召模式",
        "en_US": "Draft Pick"
    },
    "GAME_CFG_TEAM_BUILDER_BLIND": {
        "zh_CN": "自选模式",
        "en_US": "Blind Pick"
    },
    "GAME_CFG_TEAM_BUILDER_BLIND_DRAFT": {
        "zh_CN": "自选征召",
        "en_US": "Blind Draft Pick"
    },
    "GAME_CFG_TEAM_BUILDER_RANDOM": {
        "zh_CN": "全随机模式",
        "en_US": "All Random"
    },
    "GAME_CFG_TEAM_BUILDER_BLIND_DUPE": {
        "zh_CN": "克隆选择",
        "en_US": "All for one"
    },
    "GAME_CFG_TEAM_BUILDER_QUICKPLAY": {
        "zh_CN": "快速匹配",
        "en_US": "Quickplay"
    }
}
gameTypes_configId_map: dict[int, dict[str, str]] = {
    1: {
        "zh_CN": "自选模式（自定义）",
        "en_US": "Blind Pick (custom)"
    },
    2: {
        "zh_CN": "征召模式（自定义）",
        "en_US": "Draft Mode (custom)"
    },
    3: {
        "zh_CN": "轮选模式",
        "en_US": "Draft Noban (custom)"
    },
    4: {
        "zh_CN": "全随机模式（自定义）",
        "en_US": "All Random (custom)"
    },
    5: {
        "zh_CN": "同选模式",
        "en_US": "Simultaneous Pick (custom)"
    },
    6: {
        "zh_CN": "竞技征召模式（自定义）",
        "en_US": "Tournament Draft (custom)"
    },
    7: {
        "zh_CN": "计时征召",
        "en_US": "Timed Draft (custom)"
    },
    10: {
        "zh_CN": "基础教程",
        "en_US": "Basic Tutorial"
    },
    11: {
        "zh_CN": "进阶教程",
        "en_US": "Advanced Tutorial"
    },
    12: {
        "zh_CN": "最终教程",
        "en_US": "Capstone Tutorial"
    },
    13: {
        "zh_CN": "盲选随机",
        "en_US": "Blind Random (custom)"
    },
    14: {
        "zh_CN": "克隆选择（自定义）",
        "en_US": "All for one (custom)"
    },
    15: {
        "zh_CN": "全队克隆",
        "en_US": "All for one (cross-team)"
    },
    16: {
        "zh_CN": "自选征召模式（自定义）",
        "en_US": "Blind Draft Pick (custom)"
    },
    17: {
        "zh_CN": "互选模式（自定义）",
        "en_US": "Nemesis Draft (custom)"
    },
    18: {
        "zh_CN": "征召模式",
        "en_US": "Draft Pick"
    },
    19: {
        "zh_CN": "自选模式",
        "en_US": "Blind Pick"
    },
    20: {
        "zh_CN": "自选征召",
        "en_US": "Blind Draft Pick"
    },
    21: {
        "zh_CN": "全随机模式",
        "en_US": "All Random"
    },
    22: {
        "zh_CN": "克隆选择",
        "en_US": "All for one"
    },
    23: {
        "zh_CN": "快速匹配",
        "en_US": "Quickplay"
    }
}
report_categories: dict[str, dict[str, str]] = {
    "LEAVING_AFK": {
        "zh_CN": "中途退出/挂机",
        "en_US": "LEAVING THE GAME / AFK"
    },
    "ASSISTING_ENEMY_TEAM": {
        "zh_CN": "消极态度",
        "en_US": "TEAM SABOTAGE"
    },
    "THIRD_PARTY_TOOLS": {
        "zh_CN": "作弊",
        "en_US": "CHEATING"
    },
    "RANK_MANIPULATION": {
        "zh_CN": "排位操控",
        "en_US": "RANK MANIPULATION"
    },
    "BOTTING": {
        "zh_CN": "自动脚本刷级",
        "en_US": "BOTTING"
    },
    "VERBAL_ABUSE": {
        "zh_CN": "滥用聊天工具",
        "en_US": "COMMS ABUSE"
    },
    "INAPPROPRIATE_NAME": {
        "zh_CN": "有攻击性的名称",
        "en_US": "OFFENSIVE NAME"
    }
}
