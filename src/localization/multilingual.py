'''
本模块收录同时含有多种语言的本地化内容的字典。一级键是要引用的字符串、整数或者浮点数，二级键是语言文化代码，二级值是本地化字符串。<br>This module collects dictionaries that contain localized content in multiple languages. Level 1 keys are strings, integers or floats to cite, Level 2 keys are locales and Level 2 values are localized strings.
'''
gamemodes: dict[str, dict[str, str]] = {
    "ARAM": {
        "en_US": "ARAM",
        "zh_CN": "极地大乱斗"
    },
    "ARAM_BOT": {
        "en_US": "ARAM 5v5 Bots",
        "zh_CN": "极地大乱斗 5v5 人机"
    },
    "ARAM_CLASH": {
        "en_US": "ARAM Clash",
        "zh_CN": "极地大乱斗 冠军杯赛"
    },
    "ARAM_UNRANKED_1x1": {
        "en_US": "ARAM 1v1",
        "zh_CN": "极地大乱斗 1v1"
    },
    "ARAM_UNRANKED_2x2": {
        "en_US": "ARAM 2v2",
        "zh_CN": "极地大乱斗 2v2"
    },
    "ARAM_UNRANKED_3x3": {
        "en_US": "ARAM 3v3",
        "zh_CN": "极地大乱斗 3v3"
    },
    "ARAM_UNRANKED_5x5": {
        "en_US": "ARAM",
        "zh_CN": "极地大乱斗"
    },
    "ARAM_UNRANKED_6x6": {
        "en_US": "ARAM Hexakill",
        "zh_CN": "极地大乱斗 六杀争夺战"
    },
    "ARSR": {
        "en_US": "All Random Summoner's Rift",
        "zh_CN": "峡谷大乱斗"
    },
    "ASCENSION": {
        "en_US": "Ascension",
        "zh_CN": "飞升争夺战"
    },
    "ASSASSINATE": {
        "en_US": "Hunt of the Blood Moon",
        "zh_CN": "红月决"
    },
    "BILGEWATER": {
        "en_US": "Black Market Brawlers",
        "zh_CN": "佣兵大作战"
    },
    "BILGEWATER_ARAM-5x5": {
        "en_US": "Butcher's Bridge",
        "zh_CN": "屠夫之桥"
    },
    "BOT": {
        "en_US": "Co-op vs. Ai",
        "zh_CN": "人机对战"
    },
    "BOT_3x3": {
        "en_US": "Co-op vs. Ai Twisted Treeline",
        "zh_CN": "人机对战 扭曲丛林"
    },
    "BRAWL": {
        "en_US": "Brawl",
        "zh_CN": "神木之门"
    },
    "CAP_1x1": {
        "en_US": "Tutorial Capstone",
        "zh_CN": "新手教程 最终部分"
    },
    "CAP_5x5": {
        "en_US": "Tutorial Capstone",
        "zh_CN": "新手教程 最终部分"
    },
    "CHERRY": {
        "en_US": "Arena",
        "zh_CN": "斗魂竞技场"
    },
    "CHERRY_UNRANKED": {
        "en_US": "Arena",
        "zh_CN": "斗魂竞技场"
    },
    "CHONCC_TREASURE_TFT": {
        "en_US": "Choncc's Treasure",
        "zh_CN": "云顶之弈 (恭喜发财)"
    },
    "CLASH": {
        "en_US": "Clash",
        "zh_CN": "冠军杯赛"
    },
    "CLASSIC": {
        "en_US": "Summoner's Rift",
        "zh_CN": "召唤师峡谷"
    },
    "COUNTER_PICK": {
        "en_US": "Nemesis Draft",
        "zh_CN": "互选征召赛"
    },
    "DARKSTAR": {
        "en_US": "Dark Star: Singularity",
        "zh_CN": "暗星：奇点"
    },
    "DOOMBOTSTEEMO": {
        "en_US": "Doom Bots",
        "zh_CN": "末日人工智能"
    },
    "FIRSTBLOOD": {
        "en_US": "Showdown",
        "zh_CN": "大对决"
    },
    "FIRSTBLOOD_1x1": {
        "en_US": "Showdown 1v1",
        "zh_CN": "大对决 1v1"
    },
    "FIRSTBLOOD_2x2": {
        "en_US": "Showdown 2v2",
        "zh_CN": "大对决 2v2"
    },
    "FIVE_YEAR_ANNIVERSARY_TFT": {
        "en_US": "Pengu's Party",
        "zh_CN": "6周年时光机"
    },
    "GAMEMODEX": {
        "en_US": "Nexus Blitz (Pre-release)",
        "zh_CN": "极限闪击"
    },
    "HEXAKILL": {
        "en_US": "Hexakill Twisted Treeline",
        "zh_CN": "六杀争夺战 扭曲丛林"
    },
    "JADE": {
        "en_US": "League Classic",
        "zh_CN": "英雄联盟经典模式"
    },
    "JADE_BOT": {
        "en_US": "League Classic Co-op vs. AI",
        "zh_CN": "英雄联盟经典模式 人机对战"
    },
    "JADE_RANKED_SOLO_5x5": {
        "en_US": "League Classic Ranked Solo / Duo",
        "zh_CN": "英雄联盟经典模式 排位赛 单排/双排"
    },
    "KINGPORO": {
        "en_US": "Legend of the Poro King",
        "zh_CN": "魄罗大乱斗"
    },
    "KING_PORO": {
        "en_US": "Legend of the Poro King",
        "zh_CN": "魄罗大乱斗"
    },
    "KIWI": {
        "en_US": "ARAM: Mayhem",
        "zh_CN": "海克斯大乱斗"
    },
    "KIWI_JADE": {
        "en_US": "ARAM: Mayhem Classic-ish",
        "zh_CN": "海克斯大乱斗 经典模式版"
    },
    "LNY23_TFT": {
        "en_US": "Choncc's Treasure",
        "zh_CN": "云顶之弈 (恭喜发财)"
    },
    "LNY24_TFT": {
        "en_US": "Choncc's Treasure",
        "zh_CN": "云顶之弈 (恭喜发财)"
    },
    "LNY25_TFT": {
        "en_US": "Choncc's Treasure",
        "zh_CN": "云顶之弈 (恭喜发财)"
    },
    "NEXUSBLITZ": {
        "en_US": "Nexus Blitz",
        "zh_CN": "极限闪击"
    },
    "NIGHTMARE_BOT": {
        "en_US": "Doom Bots",
        "zh_CN": "末日人工智能"
    },
    "NORMAL": {
        "en_US": "Normal",
        "zh_CN": "匹配模式"
    },
    "NORMAL_1x1": {
        "en_US": "Normal 1v1",
        "zh_CN": "匹配模式 1v1"
    },
    "NORMAL_3x3": {
        "en_US": "Normal 3v3",
        "zh_CN": "匹配模式 3v3"
    },
    "NORMAL-QUICKPLAY-SR-TB-5x5": {
        "en_US": "Quickplay (Summoner's Rift and The Bandlewood)",
        "zh_CN": "快速模式（召唤师峡谷与班德尔之森）"
    },
    "NORMAL_TFT": {
        "en_US": "Normal (TFT)",
        "zh_CN": "云顶之弈（匹配模式）"
    },
    "ODIN": {
        "en_US": "Dominion",
        "zh_CN": "统治战场"
    },
    "ODIN_RANKED_TEAM": {
        "en_US": "Dominion Ranked",
        "zh_CN": "统治战场 排位赛"
    },
    "ODIN_RANKED_SOLO": {
        "en_US": "Dominion Ranked Solo",
        "zh_CN": "统治战场 排位赛 单人"
    },
    "ODIN_UNRANKED": {
        "en_US": "Dominion",
        "zh_CN": "统治战场"
    },
    "ODYSSEY": {
        "en_US": "Odyssey: Extraction",
        "zh_CN": "奥德赛"
    },
    "ONEFORALL": {
        "en_US": "One for All",
        "zh_CN": "克隆大作战"
    },
    "ONEFORALL_5x5": {
        "en_US": "One for All 5v5",
        "zh_CN": "克隆大作战 5v5"
    },
    "PRACTICETOOL": {
        "en_US": "Practice Tool",
        "zh_CN": "训练模式"
    },
    "PROJECT": {
        "en_US": "Overcharge",
        "zh_CN": "超频行动"
    },
    "PROMETHIUM_TFT": {
        "en_US": "Ao Shin's Ascent",
        "zh_CN": "敖兴之峰"
    },
    "PVE_PUZZLE_TFT": {
        "en_US": "Tocker's Trials",
        "zh_CN": "发条鸟的试炼"
    },
    "RANKED_FLEX_SR": {
        "en_US": "Ranked Flex",
        "zh_CN": "排位赛 灵活排位"
    },
    "RANKED_FLEX_SR_5x5": {
        "en_US": "Ranked Flex 5v5",
        "zh_CN": "排位赛 灵活排位 5v5"
    },
    "RANKED_FLEX_TT": {
        "en_US": "Ranked Flex Twisted Treeline",
        "zh_CN": "排位赛 灵活排位 扭曲丛林"
    },
    "RANKED_PREMADE-3x3": {
        "en_US": "Ranked Premade 3v3",
        "zh_CN": "排位赛 预组队 3v3"
    },
    "RANKED_SOLO_1x1": {
        "en_US": "Ranked Solo/Duo 1v1",
        "zh_CN": "排位赛 单排/双排 1v1"
    },
    "RANKED_SOLO_5x5": {
        "en_US": "Ranked Solo/Duo",
        "zh_CN": "排位赛 单排/双排"
    },
    "RANKED_TEAM_3x3": {
        "en_US": "Ranked Team 3v3",
        "zh_CN": "排位赛 战队 扭曲丛林"
    },
    "RANKED_TEAMPLAY_TT": {
        "en_US": "Twisted Treeline Ranked",
        "zh_CN": "扭曲丛林 排位赛"
    },
    "RANKED_TEAM_5x5": {
        "en_US": "Ranked Team 5v5",
        "zh_CN": "排位赛 战队 召唤师峡谷"
    },
    "RANKED_TFT": {
        "en_US": "Teamfight Tactics (Ranked)",
        "zh_CN": "云顶之弈 (排位赛)"
    },
    "RANKED_TFT_DOUBLE_UP": {
        "en_US": "Teamfight Tactics (Double Up)",
        "zh_CN": "云顶之弈 (双人作战)"
    },
    "RANKED_TFT_PAIRS": {
        "en_US": "Teamfight Tactics (Double Up)",
        "zh_CN": "云顶之弈 (双人作战)"
    },
    "RANKED_TFT_TURBO": {
        "en_US": "Teamfight Tactics (Hyper Roll)",
        "zh_CN": "云顶之弈(狂暴模式)"
    },
    "RIOTSCRIPT_BOT": {
        "en_US": "Co-op vs. Ai",
        "zh_CN": "人机对战"
    },
    "RUBY": {
        "en_US": "Doom Bots",
        "zh_CN": "末日人工智能"
    },
    "RUBY_TRIAL_1": {
        "en_US": "Doom Bots - Veigar's Curse!",
        "zh_CN": "末日人工智能 - 维迦的诅咒！"
    },
    "RUBY_TRIAL_2": {
        "en_US": "Doom Bots - Veigar's Evil!",
        "zh_CN": "末日人工智能 - 维迦的邪咒！"
    },
    "RUBY_TRIAL_3": {
        "en_US": "Doom Bots - Veigar's Doom!",
        "zh_CN": "末日人工智能 - 维迦的末日厄咒！"
    },
    "SET_REVIVAL_5_5_TFT": {
        "en_US": "Revival: Dawn of Heroes",
        "zh_CN": "回归赛季：英雄之黎明重现"
    },
    "SET_REVIVAL_TFT": {
        "en_US": "Revival: Festival of Beasts",
        "zh_CN": "回归赛季：瑞兽再闹新春"
    },
    "SF_TFT": {
        "en_US": "Teamfight Tactics (Soul Brawl)",
        "zh_CN": "云顶之弈 (斗魂锦标赛)"
    },
    "SIEGE": {
        "en_US": "Nexus Siege",
        "zh_CN": "枢纽攻防战"
    },
    "SNOWURF": {
        "en_US": "Snow Battle ARURF",
        "zh_CN": "冰雪无限火力"
    },
    "SR-BOTS_INTRO-TB-5x5": {
        "en_US": "Co-op vs. AI Intro (Summoner's Rift and The Bandlewood)",
        "zh_CN": "人机对战 入门级（召唤师峡谷和班德尔之森）"
    },
    "SOLO_DUO_RANKED_5x5": {
        "en_US": "Ranked Solo/Duo",
        "zh_CN": "排位赛 单排/双排"
    },
    "SR_6x6": {
        "en_US": "Hexakill Summoner's Rift",
        "zh_CN": "六杀争夺战 召唤师峡谷"
    },
    "STARGUARDIAN": {
        "en_US": "Invasion",
        "zh_CN": "怪兽入侵"
    },
    "STRAWBERRY": {
        "en_US": "Swarm",
        "zh_CN": "无尽狂潮"
    },
    "SWIFTPLAY": {
        "en_US": "Swiftplay",
        "zh_CN": "快速模式"
    },
    "TEAM_BUILDER_BLIND-5x5": {
        "en_US": "Team Builder Blind 5v5",
        "zh_CN": "阵容匹配 自选 5v5"
    },
    "TEAM_BUILDER_DRAFT_UNRANKED_1x1": {
        "en_US": "Team Builder Draft 1v1",
        "zh_CN": "阵容匹配 征召 1v1"
    },
    "TFT": {
        "en_US": "Normal (TFT)",
        "zh_CN": "云顶之弈（匹配模式）"
    },
    "TURBO_TFT": {
        "en_US": "Teamfight Tactics (Hyper Roll)",
        "zh_CN": "云顶之弈(狂暴模式)"
    },
    "TUTORIAL": {
        "en_US": "Tutorial",
        "zh_CN": "新手教程"
    },
    "TUTORIAL_MODULE_1": {
        "en_US": "Tutorial Part 1",
        "zh_CN": "新手教程 第一部分"
    },
    "TUTORIAL_MODULE_2": {
        "en_US": "Tutorial Part 2",
        "zh_CN": "新手教程 第二部分"
    },
    "TUTORIAL_MODULE_3": {
        "en_US": "Tutorial Part 3",
        "zh_CN": "新手教程 第三部分"
    },
    "TUTORIAL_TFT": {
        "en_US": "Teamfight Tactics (Tutorial)",
        "zh_CN": "云顶之弈 (新手教程)"
    },
    "ULTBOOK": {
        "en_US": "Ultimate Spellbook",
        "zh_CN": "终极魔典"
    },
    "URF": {
        "en_US": "Ultra Rapid Fire",
        "zh_CN": "无限火力"
    },
    "URF_BOT": {
        "en_US": "Ultra Rapid Fire Bots 5v5",
        "zh_CN": "无限火力 人机对战"
    },
    "URF_CLASH": {
        "en_US": "URF Clash",
        "zh_CN": "无限乱斗 冠军杯赛"
    }
} #来源（Source）：/lol-platform-config/v1/namespaces/DisabledChampions; /lol-platform-config/v1/namespaces/ChampionMasteryConfig
gamemaps: dict[int, dict[str, str]] = {
    0: {
        "en_US": "Test Map 0",
        "zh_CN": "测试地图0"
    },
    1: {
        "en_US": "Summoner's Rift Original Summoner Variant",
        "zh_CN": "召唤师峡谷 夏季怀旧版"
    },
    2: {
        "en_US": "Summoner's Rift Original Autumn (Harrowing) Variant",
        "zh_CN": "召唤师峡谷 万圣节怀旧版"
    },
    3: {
        "en_US": "The Proving Grounds",
        "zh_CN": "试炼之地"
    },
    4: {
        "en_US": "Magma Chamber",
        "zh_CN": "熔岩大厅"
    },
    7: {
        "en_US": "Summoner's Rift",
        "zh_CN": "召唤师峡谷"
    },
    8: {
        "en_US": "Crystal Scar",
        "zh_CN": "水晶之痕"
    },
    10: {
        "en_US": "Twisted Treeline",
        "zh_CN": "扭曲丛林"
    },
    11: {
        "en_US": "Summoner's Rift",
        "zh_CN": "召唤师峡谷"
    },
    12: {
        "en_US": "Random Map",
        "zh_CN": "随机地图"
    },
    13: {
        "en_US": "Summoner's Rift",
        "zh_CN": "召唤师峡谷"
    },
    14: {
        "en_US": "Butcher's Bridge",
        "zh_CN": "屠夫之桥"
    },
    16: {
        "en_US": "Cosmic Ruins",
        "zh_CN": "星界废墟"
    },
    18: {
        "en_US": "Valoran City Park",
        "zh_CN": "瓦洛兰城市公园"
    },
    19: {
        "en_US": "Substructure 43",
        "zh_CN": "第43区"
    },
    20: {
        "en_US": "Crash Site",
        "zh_CN": "飞船坠落点"
    },
    21: {
        "en_US": "Temple of Lily and Lotus",
        "zh_CN": "百合与莲花的神庙"
    },
    22: {
        "en_US": "Convergence",
        "zh_CN": "聚点危机"
    },
    23: {
        "en_US": "",
        "zh_CN": ""
    },
    30: {
        "en_US": "Rings of Wrath",
        "zh_CN": "怒火角斗场"
    },
    33: {
        "en_US": "Final City",
        "zh_CN": "最终都市"
    },
    35: {
        "en_US": "The Bandlewood",
        "zh_CN": "班德尔之森"
    },
    53: {
        "en_US": "",
        "zh_CN": ""
    }, # https://raw.communitydragon.org/11.1/game/data/menu/fontconfig_zh_cn.txt.json
    90: {
        "en_US": "Pre-Season 5 Testing Map",
        "zh_CN": "第五赛季季前赛测试地图"
    },
    111: {
        "en_US": "",
        "zh_CN": ""
    },
    120: {
        "en_US": "",
        "zh_CN": ""
    },
    121: {
        "en_US": "",
        "zh_CN": ""
    },
    133: {
        "en_US": "",
        "zh_CN": ""
    },
    140: {
        "en_US": "",
        "zh_CN": ""
    },
    453: {
        "en_US": "Classic Rift",
        "zh_CN": "经典召唤师峡谷"
    },
    520: {
        "en_US": "",
        "zh_CN": ""
    },
    601: {
        "en_US": "",
        "zh_CN": ""
    }, # https://raw.communitydragon.org/latest/game/gameplay.bin.json
    911: {
        "en_US": "",
        "zh_CN": ""
    }
}
ARAMmaps: dict[str, dict[str, str]] = {
    "NONE": {
        "en_US": "Howling Abyss",
        "zh_CN": "嚎哭深渊"
    },
    "MapSkin_Map12_Bloom": {
        "en_US": "Koeshin's Crossing",
        "zh_CN": "莲华栈桥"
    },
    "MapSkin_HA_Bilgewater": {
        "en_US": "Butcher's Bridge",
        "zh_CN": "屠夫之桥"
    },
    "MapSkin_HA_Crepe": {
        "en_US": "Bridge of Progress",
        "zh_CN": "进步之桥"
    },
    "MapSkin_Map12_Jade": {
        "en_US": "SR?",
        "zh_CN": "召唤师峡谷？"
    }
}
gameTypes_config: dict[str, dict[str, str]] = {
    "GAME_CFG_PICK_BLIND": {
        "en_US": "Blind Pick (custom)",
        "zh_CN": "自选模式（自定义）"
    },
    "GAME_CFG_DRAFT_STD": {
        "en_US": "Draft Mode (custom)",
        "zh_CN": "征召模式（自定义）"
    },
    "GAME_CFG_DRAFT_NOBAN": {
        "en_US": "Draft Noban (custom)",
        "zh_CN": "轮选模式"
    },
    "GAME_CFG_PICK_RANDOM": {
        "en_US": "All Random (custom)",
        "zh_CN": "全随机模式（自定义）"
    },
    "GAME_CFG_PICK_SIMUL": {
        "en_US": "Simultaneous Pick (custom)",
        "zh_CN": "同选模式"
    },
    "GAME_CFG_DRAFT_TOURNAMENT": {
        "en_US": "Tournament Draft (custom)",
        "zh_CN": "竞技征召模式（自定义）"
    },
    "GAME_CFG_PICK_SIMUL_TD": {
        "en_US": "Timed Draft (custom)",
        "zh_CN": "计时征召"
    },
    "GAME_CFG_BASIC_TUTORIAL": {
        "en_US": "Basic Tutorial",
        "zh_CN": "基础教程"
    },
    "GAME_CFG_ADV_TUTORIAL": {
        "en_US": "Advanced Tutorial",
        "zh_CN": "进阶教程"
    },
    "GAME_CFG_CAP": {
        "en_US": "Capstone Tutorial",
        "zh_CN": "最终教程"
    },
    "GAME_CFG_BLIND_RANDOM": {
        "en_US": "Blind Random (custom)",
        "zh_CN": "盲选随机"
    },
    "GAME_CFG_BLIND_DUPE": {
        "en_US": "All for one (custom)",
        "zh_CN": "克隆选择（自定义）"
    },
    "GAME_CFG_CROSS_DUPE": {
        "en_US": "All for one (cross-team)",
        "zh_CN": "全队克隆"
    },
    "GAME_CFG_BLIND_DRAFT_ST": {
        "en_US": "Blind Draft Pick (custom)",
        "zh_CN": "自选征召模式（自定义）"
    },
    "GAME_CFG_COUNTER_PICK": {
        "en_US": "Nemesis Draft (custom)",
        "zh_CN": "互选模式（自定义）"
    },
    "GAME_CFG_TEAM_BUILDER_DRAFT": {
        "en_US": "Draft Pick",
        "zh_CN": "征召模式"
    },
    "GAME_CFG_TEAM_BUILDER_BLIND": {
        "en_US": "Blind Pick",
        "zh_CN": "自选模式"
    },
    "GAME_CFG_TEAM_BUILDER_BLIND_DRAFT": {
        "en_US": "Blind Draft Pick",
        "zh_CN": "自选征召"
    },
    "GAME_CFG_TEAM_BUILDER_RANDOM": {
        "en_US": "All Random",
        "zh_CN": "全随机模式"
    },
    "GAME_CFG_TEAM_BUILDER_BLIND_DUPE": {
        "en_US": "All for one",
        "zh_CN": "克隆选择"
    },
    "GAME_CFG_TEAM_BUILDER_QUICKPLAY": {
        "en_US": "Quickplay",
        "zh_CN": "快速匹配"
    }
}
gameTypes_configId_map: dict[int, dict[str, str]] = {
    1: {
        "en_US": "Blind Pick (custom)",
        "zh_CN": "自选模式（自定义）"
    },
    2: {
        "en_US": "Draft Mode (custom)",
        "zh_CN": "征召模式（自定义）"
    },
    3: {
        "en_US": "Draft Noban (custom)",
        "zh_CN": "轮选模式"
    },
    4: {
        "en_US": "All Random (custom)",
        "zh_CN": "全随机模式（自定义）"
    },
    5: {
        "en_US": "Simultaneous Pick (custom)",
        "zh_CN": "同选模式"
    },
    6: {
        "en_US": "Tournament Draft (custom)",
        "zh_CN": "竞技征召模式（自定义）"
    },
    7: {
        "en_US": "Timed Draft (custom)",
        "zh_CN": "计时征召"
    },
    10: {
        "en_US": "Basic Tutorial",
        "zh_CN": "基础教程"
    },
    11: {
        "en_US": "Advanced Tutorial",
        "zh_CN": "进阶教程"
    },
    12: {
        "en_US": "Capstone Tutorial",
        "zh_CN": "最终教程"
    },
    13: {
        "en_US": "Blind Random (custom)",
        "zh_CN": "盲选随机"
    },
    14: {
        "en_US": "All for one (custom)",
        "zh_CN": "克隆选择（自定义）"
    },
    15: {
        "en_US": "All for one (cross-team)",
        "zh_CN": "全队克隆"
    },
    16: {
        "en_US": "Blind Draft Pick (custom)",
        "zh_CN": "自选征召模式（自定义）"
    },
    17: {
        "en_US": "Nemesis Draft (custom)",
        "zh_CN": "互选模式（自定义）"
    },
    18: {
        "en_US": "Draft Pick",
        "zh_CN": "征召模式"
    },
    19: {
        "en_US": "Blind Pick",
        "zh_CN": "自选模式"
    },
    20: {
        "en_US": "Blind Draft Pick",
        "zh_CN": "自选征召"
    },
    21: {
        "en_US": "All Random",
        "zh_CN": "全随机模式"
    },
    22: {
        "en_US": "All for one",
        "zh_CN": "克隆选择"
    },
    23: {
        "en_US": "Quickplay",
        "zh_CN": "快速匹配"
    }
}
report_categories: dict[str, dict[str, str]] = {
    "LEAVING_AFK": {
        "en_US": "LEAVING THE GAME / AFK",
        "zh_CN": "中途退出/挂机"
    },
    "ASSISTING_ENEMY_TEAM": {
        "en_US": "TEAM SABOTAGE",
        "zh_CN": "消极态度"
    },
    "THIRD_PARTY_TOOLS": {
        "en_US": "CHEATING",
        "zh_CN": "作弊"
    },
    "RANK_MANIPULATION": {
        "en_US": "RANK MANIPULATION",
        "zh_CN": "排位操控"
    },
    "BOTTING": {
        "en_US": "BOTTING",
        "zh_CN": "自动脚本刷级"
    },
    "VERBAL_ABUSE": {
        "en_US": "COMMS ABUSE",
        "zh_CN": "滥用聊天工具"
    },
    "INAPPROPRIATE_NAME": {
        "en_US": "OFFENSIVE NAME",
        "zh_CN": "有攻击性的名称"
    }
}
