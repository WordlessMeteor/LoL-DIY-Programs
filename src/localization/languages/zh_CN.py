#生涯（Profile）
challengeCrystalLevels: dict[str, str] = {
    "": "",
    "NONE": "无",
    "IRON": "黑铁阶",
    "BRONZE": "黄铜阶",
    "SILVER": "白银阶",
    "GOLD": "黄金阶",
    "PLATINUM": "铂金阶",
    "EMERALD": "翡翠阶",
    "DIAMOND": "钻石阶",
    "MASTER": "大师阶",
    "GRANDMASTER": "宗师阶",
    "CHALLENGER": "王者阶"
}
titleAcquisitionTypes: dict[str, str] = {
    "": "",
    "DEFAULT": "默认",
    "CHALLENGE": "成就",
    "CHAMPION_MASTERY": "英雄成就",
    "EVENT": "事件"
}
challengeCategories: dict[str, str] = {
    "ALL": "全部",
    "EXPERTISE": "行家里手",
    "TEAMWORK": "运筹决胜",
    "IMAGINATION": "奇思妙想",
    "VETERANCY": "千锤百炼",
    "COLLECTION": "大收藏家",
    "LEGACY": "限定成就"
} #rcp-fe-lol-shared-components/global/zh_cn/trans-challenges.json
#英雄（Champion）
damageTypes: dict[str, str] = {
    "kPhysical": "物理伤害",
    "kMagic": "魔法伤害",
    "kMixed": "混合伤害"
}
attackTypes: dict[str, str] = {
    "melee": "近战",
    "ranged": "远程"
}
#游戏模式（Game mode）
queueTypes_ranked: dict[str, str] = {
    "JADE_RANKED_SOLO_5x5": "经典模式 5V5",
    "RANKED_PREMADE_5x5": "5V5",
    "RANKED_TFT_DOUBLE_UP": "双人作战",
    "RANKED_TFT_PAIRS": "2V0", #仅美测服可用（Only available on PBE）
    "RANKED_TFT_TURBO": "狂暴模式",
    "RANKED_TFT": "云顶之弈",
    "RANKED_FLEX_TT": "扭曲丛林 灵活 5V5",
    "CHERRY": "斗魂竞技场",
    "RANKED_FLEX_SR": "灵活 5V5",
    "RANKED_SOLO_5x5": "单人/双人",
    "NONE": "无"
} #仅用于排位战区显示（Only designed for ranked league display）
categories: dict[str, str] = {
    "Custom": "自定义对局",
    "PvP": "玩家对战",
    "VersusAi": "人机对战"
}
gameSelectCategories: dict[str, str] = {
    "": "待定",
    "CreateCustom": "创建自定义对局",
    "JoinCustom": "加入自定义对局",
    "kPvP": "玩家对战",
    "kTraining": "训练",
    "kVersusAI": "人机对战"
}
gameSelectModeGroups: dict[str, str] = {
    "": "待定",
    "kARAM": "极地大乱斗",
    "kAlternativeLeagueGameModes": "轮换模式",
    "kSummonersRift": "召唤师峡谷",
    "kTeamfightTactics": "云顶之弈",
    "kJade": "英雄联盟经典"
}
banModes: dict[str, str] = {
    "": "待定",
    "SkipBanStrategy": "无",
    "StandardBanStrategy": "经典策略",
    "TournamentBanStrategy": "竞技策略"
}
pickModes: dict[str, str] = {
    "": "待定",
    "AllRandomPickStrategy": "全随机模式",
    "AllTeamVotePickStrategy": "全队投票",
    "CounterDraftPickStrategy": "互选模式",
    "DraftModeSinglePickStrategy": "传统征召模式",
    "OneTeamVotePickStrategy": "单队投票",
    "QuickplayPickStrategy": "快速匹配",
    "SimulPickStrategy": "自选模式",
    "SkipPickStrategy": "跳过英雄选择",
    "TeamBuilderDraftPickStrategy": "征召模式",
    "TournamentPickStrategy": "竞技征召模式"
}
#排位信息（Ranked）
tiers: dict[str, str] = {
    "": "",
    "NONE": "没有段位",
    "IRON": "坚韧黑铁",
    "BRONZE": "英勇黄铜",
    "SILVER": "不屈白银",
    "GOLD": "荣耀黄金",
    "PLATINUM": "华贵铂金",
    "EMERALD": "流光翡翠",
    "DIAMOND": "璀璨钻石",
    "MASTER": "超凡大师",
    "GRANDMASTER": "傲世宗师",
    "CHALLENGER": "最强王者",
    "SALT": "坚韧盐晶",
    "WOOD": "英勇秀木",
    "LEGEND": "最强传奇"
}
ratedTiers_turbo: dict[str, str] = {
    "": "",
    "NONE": "没有段位",
    "GRAY": "灰白",
    "GREEN": "翠绿",
    "BLUE": "天蓝",
    "PURPLE": "绛紫",
    "ORANGE": "耀橙"
}
ratedTiers_cherry: dict[str, str] = {
    "": "",
    "NONE": "没有段位",
    "GRAY": "木木角斗士",
    "GREEN": "青铜角斗士",
    "BLUE": "白银角斗士",
    "PURPLE": "黄金角斗士",
    "ORANGE": "王者角斗士"
}
#英雄联盟对局记录（LoL match history）
gameTypes_history: dict[str, str] = {
    "MATCHED_GAME": "匹配对局",
    "CUSTOM_GAME": "自定义对局",
    "TUTORIAL_GAME": "新手教程"
}
team_colors_int: dict[int, str] = {
    0: "",
    1: "蓝方",
    2: "红方",
    3: "中立",
    100: "蓝方",
    200: "红方",
    300: "中立" #HN1-10672246102
}
team_colors_str: dict[str, str] = {
    "0": "",
    "1": "蓝方",
    "2": "红方",
    "3": "中立",
    "100": "蓝方",
    "200": "红方",
    "300": "中立",
    "ORDER": "蓝方",
    "CHAOS": "红方"
}
endOfGameResults: dict[str, str] = {
    "": "",
    "GameComplete": "游戏结束",
    "Abort_Unexpected": "意外终止",
    "Abort_TooFewPlayers": "全员提前退出",
    "Abort_AntiCheatExit": "检测到作弊而终止"
}
lanes: dict[str, str] = {
    "TOP": "上路",
    "JUNGLE": "打野",
    "MIDDLE": "中路",
    "BOTTOM": "下路",
    "NONE": ""
}
roles: dict[str, str] = {
    "CARRY": "C位",
    "DUO": "游走",
    "SOLO": "单人",
    "SUPPORT": "辅助",
    "NONE": ""
}
#英雄联盟对局概要（LoL match summary）
subteam_colors: dict[int, str] = {
    0: "",
    1: "魄罗",
    2: "小兵",
    3: "迅捷蟹",
    4: "石甲虫",
    5: "锋喙鸟",
    6: "哨卫",
    7: "狼",
    8: "魔沼蛙"
} #仅用于斗魂竞技场（Only for Arena mode）
augment_rarity: dict[int | str, str] = {
    0: "白银",
    1: "黄金",
    2: "棱彩",
    4: "黄金",
    8: "棱彩",
    "kBronze": "青铜",
    "kSilver": "白银",
    "kGold": "黄金",
    "kPrismatic": "棱彩",
    "kEventChoice": "事件"
}
#英雄联盟事件（LoL events）
eventTypes: dict[str, str] = {
    "BUILDING_KILL": "建筑物击杀",
    "CHAMPION_KILL": "英雄击杀",
    "CHAMPION_SPECIAL_KILL": "特殊击杀事件",
    "CHAMPION_TRANSFORM": "英雄转换",
    "DRAGON_SOUL_GIVEN": "赋予元素龙魂",
    "ELITE_MONSTER_KILL": "史诗级野怪击杀",
    "FEAT_UPDATE": "更新抢占先机进度",
    "GAME_END": "游戏结束",
    "ITEM_DESTROYED": "移除装备",
    "ITEM_PURCHASED": "购买装备",
    "ITEM_SOLD": "销售装备",
    "ITEM_UNDO": "撤回装备",
    "LEVEL_UP": "升级",
    "OBJECTIVE_BOUNTY_FINISH": "结束战略点悬赏",
    "OBJECTIVE_BOUNTY_PRESTART": "等待战略点悬赏",
    "PAUSE_END": "等待结束",
    "SKILL_LEVEL_UP": "技能加点",
    "TURRET_PLATE_DESTROYED": "摧毁防御塔镀层",
    "WARD_KILL": "摧毁守卫",
    "WARD_PLACED": "放置守卫"
}
buildingTypes: dict[str, str] = {
    "": "",
    "INHIBITOR_BUILDING": "召唤水晶",
    "TOWER_BUILDING": "防御塔"
}
featTypes: dict[int, str] = {
    0: "战斗先机", #在抢占先机包含第一滴血先机的时候，时间轴中无先机数据（When Feats of Strength contained Feat of First Blood, timeline didn't hold feat data）
    1: "第一座塔先机",
    2: "野怪击杀先机"
}
laneTypes: dict[str, str] = {
    "": "",
    "TOP_LANE": "上路",
    "MID_LANE": "中路",
    "BOT_LANE": "下路"
}
levelUpTypes: dict[str, str] = {
    "NORMAL": "正常加点",
    "EVOLVE": "进化技能"
}
killTypes: dict[str, str] = {
    "KILL_ACE": "团灭",
    "KILL_FIRST_BLOOD": "第一滴血",
    "KILL_MULTI": "重杀",
}
monsterSubTypes: dict[str, str] = {
    "": "",
    "EARTH_DRAGON": "山脉亚龙",
    "CHEMTECH_DRAGON": "炼金科技亚龙",
    "WATER_DRAGON": "海洋亚龙",
    "HEXTECH_DRAGON": "海克斯科技亚龙",
    "AIR_DRAGON": "云霄亚龙",
    "FIRE_DRAGON": "炼狱亚龙",
    "ELDER_DRAGON": "远古巨龙",
    "RUINED_DRAGON": "破败巨龙",
    "UNKNOWN": "未知"
}
monsterTypes: dict[str, str] = {
    "": "",
    "RIFTHERALD": "峡谷先锋",
    "HORDE": "虚空巢虫",
    "BARON_NASHOR": "纳什男爵",
    "DRAGON": "巨龙",
    "ATAKHAN": "厄塔汗"
}
dragonSoul_names: dict[str, str] = {
    "Infernal": "炼狱龙魂",
    "Mountain": "山脉龙魂",
    "Ocean": "海洋龙魂",
    "Cloud": "云霄龙魂",
    "Chemtech": "炼金科技龙魂",
    "Hextech": "海克斯科技龙魂",
    "Ruined": "破败龙魂",
    "Party": "派对龙魂"
}
towerTypes: dict[str, str] = {
    "": "",
    "OUTER_TURRET": "外防御塔",
    "INNER_TURRET": "内防御塔",
    "BASE_TURRET": "水晶防御塔",
    "NEXUS_TURRET": "枢纽防御塔"
}
transformTypes: dict[str, str] = {
    "ASSASSIN": "影流刺客",
    "SLAYER": "拉亚斯特"
}
wardTypes: dict[str, str] = {
    "BLUE_TRINKET": "远见改造",
    "CONTROL_WARD": "控制守卫",
    "SIGHT_WARD": "洞察之石",
    "UNDEFINED": "未知",
    "VISION_WARD": "真视守卫",
    "YELLOW_TRINKET": "侦察守卫",
    "TEEMO_MUSHROOM": "蘑菇"
}
eventTypes_liveclient: dict[str, str] = {
    "Ace": "团灭",
    "AtakhanKill": "击杀厄塔汗",
    "BaronKill": "击杀纳什男爵",
    "ChampionKill": "击杀英雄",
    "DragonKill": "击杀巨龙",
    "FirstBlood": "第一滴血",
    "FirstBrick": "第一座塔",
    "GameEnd": "游戏结束",
    "GameStart": "游戏开始",
    "HeraldKill": "击败峡谷先锋",
    "HordeKill": "击杀虚空巢虫",
    "InhibKilled": "摧毁召唤水晶",
    "MinionsSpawning": "小兵开始生成",
    "Multikill": "连杀",
    "TurretKilled": "摧毁防御塔"
}
DragonTypes: dict[str, str] = {
    "Air": "云霄亚龙",
    "Earth": "山脉亚龙",
    "Fire": "炼狱亚龙",
    "Water": "海洋亚龙",
    "Chemtech": "炼金科技亚龙",
    "Hextech": "海克斯科技亚龙",
    "Elder": "远古巨龙",
    "Ruined": "破败巨龙",
    "Party": "派对亚龙"
}
#云顶之弈对局记录（TFT match history）
# traitStyles: dict[str, str] = {
#     "kThreat": "威慑",
#     "kBronze": "青铜",
#     "kSilver": "白银",
#     "kGold": "黄金",
#     "kChromatic": "炫金"
# }
traitStyles: dict[int, str] = {
    0: "",
    1: "青铜",
    2: "白银",
    3: "黄金",
    4: "炫金",
    5: "独特"
}
rarities: dict[str, str] = {
    "Default": "默认",
    "NoRarity": "其它",
    "Common": "常规",
    "Epic": "史诗",
    "Legacy": "限定",
    "Legendary": "传说",
    "Mythic": "神话",
    "Rare": "稀有",
    "Ultimate": "终极",
    "Exalted": "圣堂级",
    "Transcendant": "卓越"
}
#自定义房间（Custom lobby）
spectatorPolicies: dict[str, str] = {
    "LOBBYONLY": "只允许房间内玩家",
    "LOBBY": "只允许房间内玩家",
    "DROPINONLY": "只允许好友",
    "DROPIN": "只允许好友",
    "ALL": "所有人",
    "NONE": "无"
}
botDifficulty_dict: dict[str, str] = {
    "NONE": "无",
    "TUTORIAL": "新手",
    "INTRO": "入门",
    "EASY": "简单",
    "MEDIUM": "一般",
    "HARD": "困难",
    "UBER": "末日",
    "RSWARMINTRO": "温暖局入门级",
    "RSINTRO": "入门级",
    "RSBEGINNER": "新手级",
    "RSINTERMEDIATE": "一般级",
    "MLINTRO": "机器学习入门"
}
positions: dict[str, str] = {
    "": "",
    "NONE": "无",
    "Invalid": "", #不可用
    "UNSELECTED": "未定",
    "TOP": "上路",
    "JUNGLE": "打野",
    "MIDDLE": "中路",
    "BOTTOM": "下路",
    "UTILITY": "辅助",
    "FILL": "补位",
    "AFK": "中途退出"
}
#商品藏品（Store and collection）
krarities: dict[str, str] = {
    "kNoRarity": "其它",
    "kExalted": "圣堂级",
    "kEpic": "史诗",
    "kLegendary": "传说",
    "kMythic": "神话",
    "kRare": "稀有",
    "kUltimate": "终极",
    "kTranscendent": "卓越"
}
skinClassifications: dict[str, str] = {
    "": "",
    "kChampion": "皮肤",
    "kGeneric": "通用",
    "kRecolor": "炫彩"
}
inventoryType_dict: dict[str, str] = {
    "ACHIEVEMENT_BANNER_ACCENT": "旗帜装饰",
    "ACHIEVEMENT_TITLE": "头衔",
    "ANNOUNCER_PACK": "播报员语音包",
    "ARAM_BOON": "海克斯大乱斗赛季旅程",
    "AUGMENT": "AUGMENT",
    "AUGMENT_SLOT": "AUGMENT_SLOT",
    "BOOST": "加成道具",
    "BUNDLES": "道具包",
    "CHAMPION": "英雄",
    "CHAMPION_PERMANENT": "永久英雄",
    "CHAMPION_SKIN": "皮肤",
    "CHERRY_BOON": "斗魂竞技场赛季旅程奖励",
    "COMPANION": "小小英雄",
    "CURRENCY": "货币",
    "EMOTE": "表情",
    "EVENT_PASS": "事件通行证",
    "FANPASS": "粉丝通行证",
    "GIFT": "礼物",
    "HEXTECH_CRAFTING": "战利品",
    "JADE_RUNE": "符文",
    "JADE_RUNE_GLYPH": "雕纹",
    "JADE_RUNE_MARK": "印记",
    "JADE_RUNE_PAGE": "符文页（经典）",
    "JADE_RUNE_QUINTESSENCE": "精华",
    "JADE_RUNE_SEAL": "符印",
    "JADE_RUNE_SLOT": "符文槽位",
    "MEGA_BUNDLE": "究极大礼包",
    "MODE_PROGRESSION_REWARD": "游戏模式进度奖励",
    "MYSTERY": "神秘道具",
    "NEXUS_FINISHER": "终结特效",
    "OPAL_ACHIEVEMENT": "《德玛西亚的崛起》小游戏成就",
    "PORTRAIT": "肖像",
    "PREMIUM_CLUB_MEMBERSHIP": "高级俱乐部会员身份",
    "PROGRESSION": "进展",
    "PROVIEW_PASS": "Pro View许可",
    "PVE_RELIC": "PVE_RELIC",
    "PVE_SUMMONER_PACKAGE": "PVE_SUMMONER_PACKAGE",
    "PVE_UPGRADE": "PVE模式战略目标属性增益",
    "QUEUE_ENTRY": "队列通行证",
    "REGALIA_BANNER": "旗帜",
    "REGALIA_BORDER": "排位边框",
    "REGALIA_CREST": "排位徽章",
    "RP": "点券",
    "RUNE": "符文页",
    "SKIN_AUGMENT": "签名升级",
    "SKIN_BORDER": "边框",
    "SKIN_UPGRADE_GEAR": "皮肤自带服装升级",
    "SKIN_UPGRADE_HOME_GUARD": "皮肤自带家园卫士特效",
    "SKIN_UPGRADE_RECALL": "皮肤自带回城特效",
    "SKIN_UPGRADE_SPAWN": "皮肤自带重生特效",
    "SPELL_BOOK_PAGE": "符文页",
    "STATSTONE": "永恒星碑",
    "STRAWBERRY_BOON": "无尽狂潮增益效果",
    "STRAWBERRY_LOADOUT_ITEM": "无尽狂潮配置",
    "STRAWBERRY_MAP": "无尽狂潮地图",
    "SUMMONER_CUSTOMIZATION": "SUMMONER_CUSTOMIZATION",
    "SUMMONER_ICON": "召唤师图标",
    "TEAMPASS": "战队通行证",
    "TEAM_SKIN_PURCHASE": "TEAM_SKIN_PURCHASE",
    "TFT_DAMAGE_SKIN": "进攻特效",
    "TFT_EVENT_HEALTH_BADGE": "云顶之弈事件生命标记",
    "TFT_EVENT_PLAYER_TAG": "云顶之弈事件玩家标签",
    "TFT_EVENT_PVE_BUDDY": "星界之力",
    "TFT_EVENT_PVE_DIFFICULTY": "难度",
    "TFT_EVENT_RIBBON": "云顶之弈事件绶带",
    "TFT_EVENT_SKILLS": "云顶之弈技巧加成",
    "TFT_MAP_SKIN": "棋盘皮肤",
    "TFT_PLAYBOOK": "英雄传说之力",
    "TFT_ZOOM_SKIN": "云顶之弈传送门",
    "TOURNAMENT_FLAG": "冠军杯赛旗帜",
    "TOURNAMENT_FRAME": "冠军杯赛旗帜框架",
    "TOURNAMENT_LOGO": "冠军杯赛标志",
    "TOURNAMENT_TROPHY": "冠军杯赛奖杯",
    "TRANSFER": "转区项目",
    "WARD_SKIN": "守卫皮肤"
}
ownershipTypes: dict[None | str, str] = {
    None: "未拥有",
    "F2P": "免费使用",
    "LOYALTY": "奖励计划",
    "RENTED": "已租赁",
    "OWNED": "已拥有"
}
subInventoryTypes: dict[None | str, str] = {
    None: "",
    "": "",
    "BORDER_SET_BUNDLE": "完全体礼包",
    "CHEST": "海克斯科技宝箱",
    "CHAMPION_BUNDLE": "英雄道具包",
    "CHROMA_BUNDLE": "炫彩大礼包",
    "CURRENCY": "货币",
    "EMOTE_BUNDLE": "表情道具包",
    "HEXTECH_BUNDLE": "海克斯科技宝箱道具包",
    "LOL_EVENT_PASS": "英雄联盟事件通行证",
    "MATERIAL": "材料",
    "RECOLOR": "炫彩",
    "RUNE_PAGE_BUNDLE": "符文页道具包",
    "SKIN_BUNDLE": "皮肤礼包",
    "SKIN_VARIANT_BUNDLE": "幻想级皮肤礼包",
    "TFT_PASS": "云顶之弈事件通行证",
    "TFT_TREASURE_TROVE_TOKEN": "云石",
    "mgs_opal_shield": "银盾",
    "lol_clash_premium_tickets": "豪华版冠军杯赛挑战券",
    "lol_clash_tickets": "冠军杯赛挑战券",
    "lol_blessing_token": "圣堂花火",
    "lol_blue_essence": "蓝色精萃",
    "lol_mythic_essence": "神话精萃",
    "lol_orange_essence": "橙色精萃",
    "lol_rare_gem": "紫色宝石",
    "tft_star_fragments": "星之碎片"
}
#战利品（Loot）
essenceTypes: dict[str, str] = {
    "CURRENCY_champion": "蓝色精萃",
    "CURRENCY_cosmetic": "橙色精萃",
    "": ""
}
lootCategories: dict[str, str] = {
    "": "其它",
    "CHAMPION": "英雄",
    "CHEST": "宝箱",
    "COMPANION": "小小英雄",
    "EMOTE": "表情",
    "ETERNALS": "永恒星碑",
    "SKIN": "皮肤",
    "SUMMONERICON": "图标",
    "WARDSKIN": "守卫皮肤"
}
itemStatus_dict: dict[str, str] = {
    "NONE": "未拥有",
    "FREE": "免费使用",
    "RENTAL": "租借中",
    "OWNED": "已拥有"
}
lootRarities: dict[str, str] = {
    "": "无",
    "DEFAULT": "经典",
    "EPIC": "史诗",
    "LEGENDARY": "传说",
    "MYTHIC": "神话",
    "ULTIMATE": "终极"
}
redeemableStatus_dict: dict[str, str] = {
    "ALREADY_OWNED": "已拥有",
    "ALREADY_RENTED": "已租赁",
    "CHAMPION_NOT_OWNED": "英雄未拥有",
    "NOT_REDEEMABLE": "无法解锁",
    "NOT_REDEEMABLE_RENTAL": "无法激活",
    "REDEEMABLE": "可解锁",
    "REDEEMABLE_RENTAL": "可升级",
    "NOT_UPGRADE": "无可用升级"
}
lootTypes: dict[str, str] = {
    "": "其它",
    "BOOST": "加成卡",
    "BUNDLE": "礼包",
    "CHAMPION": "永久英雄",
    "CHAMPION_RENTAL": "英雄碎片",
    "CHAMPION_TOKEN": "成就代币",
    "CHROMA": "永久炫彩",
    "CHROMA_RENTAL": "炫彩碎片",
    "CHEST": "宝箱",
    "COMPANION": "永久 小小英雄",
    "CURRENCY": "货币",
    "EMOTE": "永久表情",
    "EMOTE_RENTAL": "表情碎片",
    "MATERIAL": "材料",
    "NEXUS_FINISHER": "终结特效",
    "SKIN": "永久皮肤",
    "SKIN_RENTAL": "皮肤碎片",
    "STATSTONE": "永久永恒星碑套装",
    "STATSTONE_SHARD": "永恒星碑套装碎片",
    "SUMMONERICON": "召唤师图标",
    "TFT_DAMAGE_SKIN": "进攻特效",
    "TFT_MAP_SKIN": "棋盘皮肤",
    "TOURNAMENTLOGO": "冠军杯赛标志",
    "WARDSKIN": "永久守卫皮肤",
    "WARDSKIN_RENTAL": "守卫皮肤碎片"
}
#聊天服务（Chat service）
RiotRelationships: dict[str, str] = {
    "friend": "好友"
}
ptyTypes: dict[str, str] = {
    "open": "公开",
    "closed": "私密"
}
conversationTypes: dict[str, str] = {
    "chat": "私聊",
    "customGame": "自定义对局",
    "championSelect": "英雄选择",
    "postGame": "结算界面"
}
messageTypes: dict[str, str] = {
    "chat": "聊天",
    "groupchat": "队伍聊天",
    "system": "系统",
    "information": "通知",
    "celebration": "庆祝"
}
system_messages: dict[str, str] = {
    "starting_soon": "[系统通知] 你的对局即将开始。请等待我们加载你的对局。这个进程应该不会超过几分钟。",
    "connecting": "正在连接……",
    "disconnected": "您已从聊天服务器断开，正在尝试重新连接……",
    "dropped_message": "由于发言内容或账号环境存在异常，消息发送暂时被限制，请注意账号保护并24小时后再试。",
    "is_blocked": "{actor}正在你的聊天黑名单中。你将不会看到它们的聊天信息。",
    "joined_room": "{actor}加入了队伍聊天",
    "left_room": "{actor}离开了队伍聊天",
    "no_friends": "看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。",
    "no_online_friends": "一个小伙伴都没在线。你知道吗，你是可以给离线的玩家发送信息的哟~",
    "rich_content_replaced": "请查看《英雄联盟》移动端APP里的消息",
    "TEXT_CHAT_MUTED": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。",
    "chat_restriction_muted": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。",
    "TEXT_CHAT_RESTRICTION": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。",
    "TEXT_CHAT_MUTED_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。",
    "TEXT_CHAT_RESTRICTION_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。"
}
invidStates: dict[str, str] = {
    "Pending": "等待确定",
    "OnHold": "搁置"
}
invidTypes: dict[str, str] = {
    "party": "小队",
    "lobby": "自定义房间"
}
availabilities: dict[str, str] = {
    "available": "可用",
    "away": "离开",
    "championSelect": "英雄选择",
    "chat": "在线",
    "dnd": "游戏中",
    "hostingCoopVsAIGame": "正创建人机对战",
    "hostingFeaturedGame": "正创建特殊模式",
    "hostingNormalGame": "正创建匹配模式",
    "hostingPracticeGame": "正创建自定义游戏",
    "hostingRankedGame": "创建排位赛",
    "hosting_ARAM_UNRANKED_5x5": "正创建匹配模式",
    "hosting_BOT": "正创建人机对战",
    "hosting_BOT_3x3": "正创建人机对战",
    "hosting_BRAWL": "正创建神木之门对局",
    "hosting_CHERRY": "正创建斗魂竞技场",
    "hosting_KIWI": "正在创建海克斯大乱斗",
    "hosting_RIOTSCRIPT_BOT": "正创建人机对战",
    "hosting_Custom": "正创建自定义游戏",
    "hosting_NEXUSBLITZ": "正创建极限闪击",
    "hosting_NORMAL": "正创建匹配模式",
    "hosting_NORMAL_3x3": "正创建匹配模式",
    "hosting_NORMAL_TFT": "正创建云顶之弈对局",
    "hosting_PRACTICETOOL": "正创建训练模式",
    "hosting_RANKED_FLEX_SR": "正创建排位对局",
    "hosting_RANKED_FLEX_TT": "正创建排位对局",
    "hosting_RANKED_SOLO_5x5": "正创建排位对局",
    "hosting_RANKED_TEAM_5x5": "正创建排位对局",
    "hosting_RANKED_TFT": "正创建云顶之弈对局",
    "hosting_RANKED_TFT_TURBO": "正创建云顶之弈对局",
    "hosting_RANKED_TFT_PAIRS": "正创建双人作战对局",
    "hosting_RANKED_TFT_DOUBLE_UP": "正创建双人作战",
    "hosting_RANKED_PREMADE_5x5": "正创建 5人排位赛 对局",
    "hosting_STRAWBERRY": "正创建【无尽狂潮】对局",
    "hosting_SWIFTPLAY": "正创建【快速模式】对局",
    "hosting_CHONCC_TREASURE_TFT": "正创建云顶之弈对局",
    "hosting_LNY23_TFT": "正创建云顶之弈对局",
    "hosting_LNY24_TFT": "正创建云顶之弈对局",
    "hosting_LNY25_TFT": "正在创建云顶之弈对局",
    "hosting_SET_REVIVAL_5_5_TFT": "正在创建云顶之弈对局",
    "hosting_SET_REVIVAL_TFT": "正在创建云顶之弈对局",
    "hosting_FIVE_YEAR_ANNIVERSARY_TFT": "正在创建云顶之弈对局",
    "hosting_SF_TFT": "正创建云顶之弈对局",
    "hosting_PVE_PUZZLE_TFT": "正创建云顶之弈对局",
    "hosting_featured": "正创建特殊模式",
    "inGame": "游戏中",
    "inQueue": "队列中",
    "inTeamBuilder": "阵容匹配中",
    "map_hosting_ARAM_UNRANKED_5x5": "正创建匹配模式（进步之桥）",
    "map_hosting_NORMAL": "正创建匹配模式（召唤师峡谷）",
    "map_hosting_NORMAL_3x3": "正创建匹配模式（扭曲丛林）",
    "map_hosting_RANKED_FLEX_SR": "正创建灵活排位（召唤师峡谷）",
    "map_hosting_RANKED_PREMADE_5x5": "正创建灵活排位（召唤师峡谷）",
    "map_hosting_RANKED_FLEX_TT": "正创建灵活排位（扭曲丛林）",
    "mobile": "在线分组",
    "offline": "离线",
    "online": "在线",
    "discord": "Discord",
    "spectating": "正在观战中",
    "teamSelect": "正在选择队伍",
    "tutorial": "正在新手教程中",
    "undefined": "待定……",
    "watchingReplay": "正在观看回放",
    "outOfGame": "在线",
    "hosting_PROMETHIUM_TFT": "正创建【敖兴之峰】对局",
    "hosting_URF": "正创建无限火力对局"
} #来源（Source）：plugins/rcp-fe-lol-social/global/zh_cn/trans.json
#目标和任务（Objective and mission）
celebrationTypes: dict[str, str] = {
    "NONE": "无",
    "FULLSCREEN": "全屏",
    "TOAST": "浮标",
    "VIGNETTE": "花饰",
    "VIGNETTE_LARGE_REWARDS_ONLY": "高等奖励专用花饰",
    "VIGNETTE_REWARDS_ONLY": "奖励专用花饰"
}
clientNotifyLevels: dict[str, str] = {
    "ALWAYS": "总是",
    "NONE": "从不"
}
displayTypes: dict[str, str] = {
    "AFTER_COMPLETION": "完成后显示",
    "ALWAYS": "总是显示",
    "CELEBRATION_ONLY": "仅在庆祝时显示",
    "NONE": "不显示",
    "TUTORIAL_ONLY": "仅新手教程显示"
}
missionTypes: dict[str, str] = {
    "ONETIME": "一次性",
    "REPEATING": "可重复"
}
metadataMissionTypes: dict[str, str] = {
    "": "",
    "always": "永久"
}
objectiveStatus_dict: dict[str, str] = {
    "DUMMY": "占位",
    "ELIGIBLE": "具备资格",
    "INELIGIBLE": "没有资格"
}
objectiveTypes: dict[str, str] = {
    "": "",
    "CHAMPION_MASTERY": "英雄成就",
    "EOGDATA": "赛后结算",
    "INGEST": "新手学习",
    "LEGS": "英雄联盟传统玩法",
    "SERIES_COMPLETION": "任务系列",
    "TFT_ELIMINATION": "云顶之弈淘汰任务"
}
rewardGroupStrategies: dict[str, str] = {
    "": "",
    "ALL_GROUPS": "所有分组",
    "SELECT_GROUPS": "选定分组",
    "OBJECTIVE_GROUPS": "目标分组"
}
rewardTypes: dict[str, str] = {
    "BLUE_ESSENCE": "蓝色精萃",
    "BOOST": "金币加成",
    "BUNDLE": "礼包",
    "CHAMPION": "英雄",
    "CHAMPION_CHROMA": "炫彩",
    "CHAMPION_SHARD": "英雄碎片",
    "CHAMPION_SKIN": "英雄皮肤",
    "CHAMPION_SKIN_SHARD": "英雄皮肤碎片",
    "CHAMPION_TOKEN": "英雄成就代币",
    "CLASH_TICKET": "冠军杯赛挑战券",
    "CLIENT_FEATURE": "客户端亮点",
    "EMOTE": "表情",
    "EVENT_MATERAIL": "事件材料",
    "GAME_QUEUE": "游戏队列",
    "GEMSTONE": "宝石",
    "HEXTECH_CHEST": "海克斯科技宝箱",
    "HEXTECH_KEY": "海克斯科技钥匙",
    "HEXTECH_KEY_SHARD": "海克斯科技钥匙碎片",
    "IP": "金币",
    "MISSION_PROGRESS": "其它任务完成进度",
    "MYSTERY_SKIN": "神秘皮肤",
    "ORANGE_ESSENCE": "橙色精粹",
    "PROGRESSION": "通行证进度",
    "PORTAL": "魔法传送门",
    "PORTAL_KEY": "魔法传送门钥匙",
    "PORTAL_KEY_SHARD": "魔法传送门钥匙碎片",
    "REWARD_GROUP": "多重奖励",
    "REWARDS_TITLE": "任务奖励",
    "REWARDS_TITLE_MULTI": "任务奖励（复数）",
    "RIOT_POINTS": "点券",
    "SPELL_BOOK_PAGE": "符文页",
    "SUMMONER_ICON": "召唤师图标",
    "SUMMONER_ICON_SHARD": "召唤师图标碎片",
    "SUMMONER_SPELL": "召唤师技能",
    "WARD_SKIN": "守卫皮肤",
    "WARD_SKIN_SHARD": "守卫皮肤碎片",
    "XP": "经验值"
} #来源（Source）：rcp-fe-lol-navigation/global/zh_cn/trans.json
missionStatus_dict: dict[str, str] = {
    "COMPLETED": "已完成",
    "DUMMY": "用于测试",
    "PENDING": "未完成",
    "SELECT_REWARDS": "选择奖励",
    "UPCOMING": "未激活"
}
gameTypes_mission: dict[str, str] = {
    "lol": "英雄联盟",
    "tft": "云顶之弈"
}
objectivesTypes: dict[str, str] = {
    "kNonPooledObjectives": "非池化目标",
    "kPooledObjectives": "池化目标"
}
lolObjectiveCategoryTypes: dict[str, str] = {
    "kNonPass": "非通行证",
    "kEventHubConfiguration": "事件通行证",
    "kTFTPassData": "云顶之弈通行证"
}
lolEventHubTypes: dict[str, str] = {
    "NON_PASS": "无",
    "SEASON_PASS": "赛季通行证"
}
objectiveCategoryFilter_dict: dict[str, str] = {
    "kNone": "无",
    "kNPE": "新玩家"
}
eventPassTypes: dict[str, str] = {
    "kUnknown": "无",
    "kActivityCenterMilestones": "活动中心里程碑",
    "kBattlePass": "战斗通行证",
    "kDemaciaPass": "经典模式通行证",
    "kEventPass": "事件通行证",
    "kSeasonPass": "赛季通行证"
}
#符文（Perk）
slotTypes: dict[str, str] = {
    "": "待定",
    "kKeyStone": "基石",
    "kMixedRegularSplashable": "符文",
    "kStatMod": "属性"
}
recommendedAttributes: dict[str, str] = {
    "kBurstDamage": "爆发伤害",
    "kCooldown": "冷却时间",
    "kDamagePerSecond": "输出",
    "kDurability": "耐久",
    "kGold": "金币",
    "kHealing": "治疗效果",
    "kMana": "法力",
    "kMoveSpeed": "移动速度",
    "kUtility": "功能"
} #来源（Source）：rcp-fe-lol-collections/global/zh_cn/trans-perks.json
#对局结算（End of game）
honorType_tooltip_headers: dict[str, str] = {
    "COOL": "护卫大神",
    "SHOTCALLER": "指挥大神",
    "HEART": "Carry大神"
}
honorType_tooltip_bodies: dict[str, str] = {
    "COOL": "可靠支柱，强大助力",
    "SHOTCALLER": "战术大师，掌控全局",
    "HEART": "核心战力，统治战场"
}
#装备（Item）
itemCategories: dict[str, str] = {
    "AbilityHaste": "技能急速",
    "Active": "主动",
    "Armor": "护甲",
    "ArmorPenetration": "护甲穿透",
    "AttackSpeed": "攻击速度",
    "Aura": "光环",
    "Bilgewater": "比尔吉沃特",
    "Boots": "鞋子",
    "Consumable": "消耗品",
    "CooldownReduction": "冷却缩减",
    "CriticalStrike": "暴击",
    "Damage": "攻击力",
    "GoldPer": "工资装",
    "Health": "生命值",
    "HealthRegen": "生命回复",
    "Jungle": "打野-起始",
    "Lane": "对线-起始",
    "LifeSteal": "生命偷取",
    "MagicPenetration": "法术穿透",
    "MagicResist": "魔法抗性",
    "Mana": "法力值",
    "ManaRegen": "法力回复",
    "Movement": "移动速度",
    "NonbootsMovement": "其它移动速度物品",
    "OnHit": "攻击特效",
    "Slow": "减速",
    "SpellBlock": "魔法抗性",
    "SpellDamage": "法术强度",
    "SpellVamp": "法术吸血",
    "Stealth": "潜行/隐身",
    "Tenacity": "韧性",
    "Trinket": "饰品",
    "Vision": "视野"
}
#事件通行证（Event pass）
rewardTag_dict: dict[str, str] = {
    "Multiple": "多重",
    "Choice": "选项",
    "Instant": "即时",
    "Free": "免费",
    "Rare": "稀有"
}
lolEventHubRewardTrackItemStates: dict[str, str] = {
    "Selected": "已领取",
    "Unselected": "未领取",
    "Unlocked": "已解锁",
    "Locked": "未解锁"
}
lolEventHubOfferCategories: dict[str, str] = {
    "Currencies": "货币",
    "Tft": "云顶之弈",
    "Loot": "战利品",
    "Borders": "边框",
    "Skins": "皮肤",
    "Chromas": "炫彩",
    "Featured": "精选"
}
cardSizes: dict[str, str] = {
    "kDefault": "默认",
    "kLarge": "大"
}
lolEventHubRewardTrackItemHeaderTypes: dict[str, str] = {
    "NONE": "无",
    "FREE": "免费",
    "PREMIUM": "高级",
}
lolEventHubOfferStates: dict[str, str] = {
    "kPurchasing": "购买",
    "kUnrevealed": "未显示",
    "kUnavailable": "不可用",
    "kAvailable": "可用",
    "kOwned": "已拥有"
}
#进度（Progression）
counterDirections: dict[str, str] = {
    "INCREASING": "增长"
}
milestone_triggerRequirements: dict[str, str] = {
    "": "",
    "ALL": "所有"
}
milestoneSizes: dict[str, str] = {
    "kLarge": "大型"
}
milestoneTriggerTypes: dict[str, str] = {
    "COUNTER": "计数器",
    "ENTITLEMENT_ITEM_ID": "资格道具识别码"
}
