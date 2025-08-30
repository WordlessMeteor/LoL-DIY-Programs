from lcu_driver import Connector
import copy, json, numpy, os, pandas, pickle, re, shutil, subprocess, time, traceback, unicodedata, uuid, _io
from urllib.parse import quote, unquote, urljoin
from wcwidth import wcswidth

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/08/23
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

current_cwd = os.getcwd()

log_folder = "日志（Logs）/Customized Program 21 - Manipulate Gameflow"
os.makedirs(log_folder, exist_ok = True)
currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
log = open(os.path.join(log_folder, currentTime + ".log"), "a+", encoding = "utf-8")

connector = Connector()

async def get_summoner_data(connection):
    data = await connection.request('GET', '/lol-summoner/v1/current-summoner')
    summoner = await data.json()
    print("displayName:    %s" %(summoner["gameName"] + "#" + summoner["tagLine"]))
    print("summonerId:     %s" %(summoner["summonerId"]))
    print("puuid:          %s" %(summoner["puuid"]))
    print("-")


#-----------------------------------------------------------------------------
#  lockfile
#-----------------------------------------------------------------------------
async def update_lockfile(connection):
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'w+')
        text = "LeagueClient:%d:%d:%s:%s" %(connection.pid, connection.port, connection.auth_key, connection.protocols[0])
        file.write(text)
        file.close()
    return None

async def get_lockfile(connection):
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'r')
        text = file.readline().split(':')
        file.close()
        print(connection.address)
        print(f'riot    {connection.auth_key}')
        return connection.auth_key
    return None

#-----------------------------------------------------------------------------
# 定义全局变量（Define global variables）
#-----------------------------------------------------------------------------
async def check_account_ready(connection) -> bool:
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    if isinstance(platform_config, dict) and "errorCode" in platform_config:
        logPrint(platform_config)
        if platform_config["httpStatus"] == 400 and platform_config["message"] == "PLATFORM_CONFIG_NOT_READY":
            logPrint("大区信息未准备就绪。请检查账号状态和服务器拥挤程度。\nPlatform config not ready. Please check the account status or server congestion.")
        else:
            logPrint("未知错误。\nUnknown error.")
        return False
    if isinstance(current_info, dict) and "errorCode" in current_info:
        logPrint(current_info)
        if current_info["httpStatus"] == 404 and current_info["message"] == "You are not logged in.":
            logPrint("您还未登录。请检查账号状态和服务器拥挤程度。\nYou're not logged in yet. Please check the account status or server congestion.")
        else:
            logPrint("未知错误。程序即将退出。\nUnknown error.")
        return False
    return True

async def prepare_data_resources(connection):
    #准备数据资源（Prepare data resources）
    global game_version, platform_config, platformId, current_info, summonerIcons, LoLChampions, skins_flat, championSkins, skinlines, spells, LoLItems, perks, perkstyles, CherryAugments, available_spell_dict, strawberryMaps, wardSkins, collection_df_refresh, collection_df_json_exist, collection_df, skins_df_refresh, skins_df_json_exist, skins_df
    ##大区信息（Platform information）
    logPrint("正在准备大区信息……\nPreparing platform information ...")
    game_version = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    ##自己的信息（Self info）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    ##召唤师图标（Summoner icon）
    logPrint("正在加载召唤师图标信息……\nLoading summoner icon information ...")
    summonerIcons_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {}
    for icon in summonerIcons_source:
        summonerIcons[icon["id"]] = icon
    ##英雄（LoL champion）
    logPrint("正在加载英雄信息……\nLoading champion information ...")
    LoLChampions_source = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
    LoLChampions = {}
    skins_flat = {}
    for champion in LoLChampions_source:
        LoLChampions[champion["id"]] = champion
        for skin in champion["skins"]:
            skins_flat[skin["id"]] = skin
            for chroma in skin["chromas"]:
                skins_flat[chroma["id"]] = chroma
            for tier in skin["questSkinInfo"]["tiers"]:
                if not tier["id"] in skins_flat: #圣堂皮肤和终极皮肤中的系列与主皮肤存在重复的序号（There're redundant ids between the tier and the parent ultimate skin）
                    skins_flat[tier["id"]] = tier
    ##皮肤（Champion skin）
    logPrint("正在加载皮肤信息……\nLoading skin information ...")
    championSkins_source = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
    championSkins = {}
    for skin in championSkins_source.values():
        championSkins[skin["id"]] = skin
        if "chromas" in skin:
            for chroma in skin["chromas"]:
                championSkins[chroma["id"]] = chroma
        if "questSkinInfo" in skin:
            for tier in skin["questSkinInfo"]["tiers"]:
                if not tier["id"] in championSkins: #圣堂皮肤和终极皮肤中的系列与主皮肤存在重复的序号（There're redundant ids between the tier and the parent ultimate skin）
                    championSkins[tier["id"]] = tier
    ##皮肤套装（Skinline）
    logPrint("正在加载皮肤套装信息……\nLoading skinline data ...")
    skinlines_source = await (await connection.request("GET", "/lol-game-data/assets/v1/skinlines.json")).json()
    skinlines = {skinline["id"]: skinline for skinline in skinlines_source}
    ##召唤师技能（Summoner spell）
    logPrint("正在加载召唤师技能信息……\nLoading summoner spell information")
    spells_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
    spells = {}
    gameModes = set()
    for spell in spells_source:
        spells[spell["id"]] = spell
        gameModes |= set(spell["gameModes"])
    available_spell_dict = {}
    for gameMode in sorted(gameModes):
        available_spell_dict[gameMode] = []
    for spell in spells_source:
        for gameMode in spell["gameModes"]:
            available_spell_dict[gameMode].append(spell["id"])
    ##英雄联盟装备（LoL item）
    logPrint("正在加载英雄联盟装备信息……\nLoading LoL item information ...")
    LoLItem_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/items.json")).json()
    LoLItems = {}
    for LoLItem_iter in LoLItem_initial:
        LoLItem_id = int(LoLItem_iter["id"])
        LoLItems[LoLItem_id] = LoLItem_iter
    ##符文（Perk）
    logPrint("正在加载符文信息……\nLoading perk information ...")
    perk_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/perks.json")).json()
    perks = {}
    for perk_iter in perk_initial:
        perk_id = perk_iter["id"]
        perks[perk_id] = perk_iter
    ##符文系（Perkstyle）
    logPrint("正在加载符文系信息……\nLoading perkstyle information ...")
    perkstyle_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
    perkstyles = {}
    for perkstyle_iter in perkstyle_initial["styles"]:
        perkstyle_id = perkstyle_iter["id"]
        perkstyles[perkstyle_id] = perkstyle_iter
    ##斗魂竞技场强化符文（Arena augment）
    logPrint("正在加载斗魂竞技场强化符文信息……\nLoading Arena augment information ...")
    CherryAugment_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/cherry-augments.json")).json()
    CherryAugments = {}
    for CherryAugment in CherryAugment_initial:
        CherryAugment_id = CherryAugment["id"]
        CherryAugments[CherryAugment_id] = CherryAugment
    ##无尽狂潮基础信息（Strawberry basics）
    logPrint("正在加载无尽狂潮基础信息……\nLoading Swarm basic information ...")
    strawberryHub_source = await (await connection.request("GET", "/lol-game-data/assets/v1/strawberry-hub.json")).json()
    strawberryMaps = {}
    for strawberryMap in strawberryHub_source[0]["MapDisplayInfoList"]:
        strawberryMaps[strawberryMap["value"]["Map"]["ItemId"]] = strawberryMap
    ##饰品（Ward skin）
    logPrint("正在加载守卫（眼）皮肤信息……\nLoading ward skin information ...")
    wardSkins_source = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    wardSkins = {}
    for skin in wardSkins_source:
        wardSkins[skin["id"]] = skin
    ##藏品数据框（Collection dataframe）
    os.makedirs("cache", exist_ok = True)
    logPrint("正在加载藏品信息……\nLoading collections ...")
    collection_df_json_exist = os.path.exists(collection_df_json_relpath)
    if collection_df_json_exist: #下面的注释适用于皮肤数据的获取，下文不再赘述（The following comments apply to skin data acquisition and won't be repeated below）
        with open(collection_df_json_relpath, "rb") as fp: #如果本地缓存存在，首先加载缓存（If the local cache exists, load it first）
            collection_df_json = pickle.load(fp)
        if platformId in collection_df_json and current_info["puuid"] in collection_df_json[platformId] and isinstance(collection_df_json[platformId][current_info["puuid"]]["data"], pandas.DataFrame) and collection_df_json[platformId][current_info["puuid"]]["timestamp"] > time.time() - 86400: #本地缓存格式检查（Local cache format check）
            collection_df = collection_df_json[platformId][current_info["puuid"]]["data"] #严格地讲，这里应该设置一个数据框格式校验（Strictly speaking, here needs a dataframe format check）
        else: #如果本地缓存的上次更新日期是一天前，或者本地缓存格式不正确，则需要重新获取数据（If the local cache was updated over a day ago, or the format isn't correct, it needs to be refreshed）
            collection_df_refresh = True
    else:
        collection_df_json = {} #本地缓存不存在时，初始化空的缓存字典（When the local cache doesn't exist, initialize an empty cache dictionary）
    if collection_df_refresh or not collection_df_json_exist: #当用户需要更新数据或者本地缓存不存在时，更新数据（When the user asks to update data or the local cache doesn't exist, refresh the data）
        collection_df = await get_collection(connection) #更新数据（Update data）
        collection_df_json_update = {"gameName": current_info["gameName"], "tagLine": current_info["tagLine"], "data": collection_df, "timestamp": time.time()}
        if not platformId in collection_df_json:
            collection_df_json[platformId] = {}
        if not current_info["puuid"] in collection_df_json[platformId]:
            collection_df_json[platformId][current_info["puuid"]] = {}
        collection_df_json[platformId][current_info["puuid"]] = collection_df_json_update #更新缓存（Update cache）
        with open(collection_df_json_relpath, "wb") as fp: #将更新后的缓存写入本地文件（Write the updated cache to the local file）
            pickle.dump(collection_df_json, fp)
        collection_df_refresh = collection_df_json_exist = False #`define_global_variables`函数只会运行一次，因此后续更新数据时，需要重置这两个逻辑变量。下同（`define_global_variables` function only runs once at the beginning, so when the user updates the data, these two variables need to be reset. Same below）
        logPrint("已更新藏品数据缓存。\nCollection data cache has been updated.")
    else:
        logPrint("已加载藏品数据缓存。\nCollection data cache has been loaded.")
    ##皮肤数据框（Skin dataframe）
    logPrint("正在整理皮肤数据……\nSorting out skin data ...")
    skins_df_json_exist = os.path.exists(skins_df_json_relpath)
    if skins_df_json_exist:
        with open(skins_df_json_relpath, "rb") as fp:
            skins_df_json = pickle.load(fp)
        if platformId in skins_df_json and current_info["puuid"] in skins_df_json[platformId] and isinstance(skins_df_json[platformId][current_info["puuid"]]["data"], pandas.DataFrame) and skins_df_json[platformId][current_info["puuid"]]["timestamp"] > time.time() - 86400:
            skins_df = skins_df_json[platformId][current_info["puuid"]]["data"]
        else:
            skins_df_refresh = True
    else:
        skins_df_json = {}
    if skins_df_refresh or not skins_df_json_exist:
        skins_df = await sort_skin_data(connection)
        skins_df_json_update = {"gameName": current_info["gameName"], "tagLine": current_info["tagLine"], "data": skins_df, "timestamp": time.time()}
        if not platformId in skins_df_json:
            skins_df_json[platformId] = {}
        if not current_info["puuid"] in skins_df_json[platformId]:
            skins_df_json[platformId][current_info["puuid"]] = {}
        skins_df_json[platformId][current_info["puuid"]] = skins_df_json_update
        with open(skins_df_json_relpath, "wb") as fp:
            pickle.dump(skins_df_json, fp)
        skins_df_refresh = skins_df_json_exist = False
        logPrint("已更新皮肤数据缓存。\nSkin data cache has been updated.")
    else:
        logPrint("已加载皮肤数据缓存。\nSkin data cache has been loaded.")

async def define_global_variables(connection):
    #定义常量字典（Define constant dictionaries）
    global ALL_GAMEFLOW_PHASES, maps, tiers, ratedTiers, tiers_all, team_colors_int, team_colors_str, subteam_color, spectatorPolicies, rarities, krarities, augment_rarity, skinClassifications, damageTypes, conversationTypes, messageTypes, invidStates, invidTypes, slotTypes, availabilities, inventoryType_dict, ownershipType_dict, position_dict, botDifficulty_dict, honorType_tooltip_headers, honorType_tooltip_bodies, zoom_scale_dict
    ALL_GAMEFLOW_PHASES = ["None", "Lobby", "Matchmaking", "ReadyCheck", "CheckedIntoTournament", "ChampSelect", "GameStart", "InProgress", "Reconnect", "WaitingForStats", "PreEndOfGame", "EndOfGame", "FailedToLaunch", "TerminatedInError"]
    maps = {8: "水晶之痕", 10: "扭曲丛林", 11: "召唤师峡谷", 12: "嚎哭深渊", 14: "屠夫之桥", 16: "星界废墟", 18: "瓦洛兰城市公园", 19: "第43区", 20: "飞船坠落点", 21: "百合与莲花的神庙", 22: "聚点危机", 30: "怒火角斗场", 33: "最终都市", 35: "班德尔之森"}
    #maps = {8: "Crystal Scar", 10: "Twisted Treeline", 11: "Summoner's Rift", 12: "Howling Abyss", 14: "Butcher's Bridge", 16: "Cosmic Ruins", 18: "Valoran City Park", 19: "Substructure 43", 20: "Crash Site", 21: "Temple of Lily and Lotus", 22: "Convergence", 30: "Rings of Wrath", 33: "Final City", 35: "The Bandlewood"}
    tiers = {"": "", "NONE": "没有段位", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    #tiers = {"": "", "NONE": "NONE", "IRON": "IRON", "BRONZE": "BRONZE", "SILVER": "SILVER", "GOLD": "GOLD", "PLATINUM": "PLATINUM", "EMERALD": "EMERALD", "DIAMOND": "DIAMOND", "MASTER": "MASTER", "GRANDMASTER": "GRANDMASTER", "CHALLENGER": "CHALLENGER"}
    ratedTiers = {"": "", "NONE": "没有段位", "GRAY": "灰白", "GREEN": "翠绿", "BLUE": "天蓝", "PURPLE": "绛紫", "ORANGE": "耀橙"}
    #ratedTiers = {"": "", "NONE": "NONE", "GRAY": "GRAY", "GREEN": "GREEN", "BLUE": "BLUE", "PURPLE": "PURPLE", "ORANGE": "ORANGE"}
    tiers_all = tiers | ratedTiers
    team_colors_int = {0: "", 1: "蓝方", 2: "红方", 100: "蓝方", 200: "红方"}
    team_colors_str = {"0": "", "1": "蓝方", "2": "红方", "100": "蓝方", "200": "红方"}
    subteam_color = {0: "", 1: "魄罗", 2: "小兵", 3: "迅捷蟹", 4: "石甲虫", 5: "锋喙鸟", 6: "哨卫", 7: "狼", 8: "魔沼蛙"} #仅用于斗魂竞技场（Only for Arena mode）
    #subteam_color = {0: "", 1: "Poro", 2: "Minion", 3: "Scuttle", 4: "Krug", 5: "Raptor", 6: "Sentinel", 7: "Wolf", 8: "Gromp"}
    spectatorPolicies = {"LOBBYONLY": "只允许房间内玩家", "DROPINONLY": "只允许好友", "DROPIN": "只允许好友", "ALL": "所有人", "NONE": "无"}
    rarities = {"Default": "默认", "Common": "常规", "Epic": "史诗", "Legacy": "限定", "Legendary": "传说", "Mythic": "神话", "Rare": "稀有", "Ultimate": "终极", "Exalted": "圣者至尊", "Transcendant": "超凡"}
    krarities = {"kNoRarity": "其它", "kExalted": "圣堂级", "kEpic": "史诗", "kLegendary": "传说", "kMythic": "神话", "kRare": "稀有", "kUltimate": "终极", "kTranscendent": "卓越"}
    augment_rarity = {0: "白银", 1: "黄金", 2: "棱彩", 4: "黄金", 8: "棱彩", "kBronze": "青铜", "kSilver": "白银", "kGold": "黄金", "kPrismatic": "棱彩"}
    #augment_rarity = {0: "Silver", 1: "Gold", 2: "Prismatic", 4: "Gold", 8: "Prismatic", "KBronze": "Bronze", "KSilver": "Silver", "kGold": "Gold", "kPrismatic": "Prismatic"}
    skinClassifications = {"kChampion": "皮肤", "kGeneric": "通用", "kRecolor": "炫彩"}
    damageTypes = {"kPhysical": "物理伤害", "kMagic": "魔法伤害", "kMixed": "混合伤害"}
    conversationTypes = {"chat": "私聊", "customGame": "自定义对局", "championSelect": "英雄选择", "postGame": "结算界面"}
    messageTypes = {"chat": "聊天", "groupchat": "队伍聊天", "system": "系统", "information": "通知", "celebration": "庆祝"}
    invidStates = {"Pending": "等待确定", "OnHold": "搁置"}
    invidTypes = {"party": "小队", "lobby": "自定义房间"}
    slotTypes = {"": "待定", "kKeyStone": "基石", "kMixedRegularSplashable": "符文", "kStatMod": "属性"}
    availabilities = {"available": "可用", "away": "离开", "championSelect": "英雄选择", "chat": "在线", "dnd": "游戏中", "hostingCoopVsAIGame": "正创建人机对战", "hostingFeaturedGame": "正创建特殊模式", "hostingNormalGame": "正创建匹配模式", "hostingPracticeGame": "正创建自定义游戏", "hostingRankedGame": "创建排位赛", "hosting_ARAM_UNRANKED_5x5": "正创建匹配模式", "hosting_BOT": "正创建人机对战", "hosting_BOT_3x3": "正创建人机对战", "hosting_CHERRY": "正创建斗魂竞技场", "hosting_RIOTSCRIPT_BOT": "正创建人机对战", "hosting_Custom": "正创建自定义游戏", "hosting_NEXUSBLITZ": "正创建极限闪击", "hosting_NORMAL": "正创建匹配模式", "hosting_NORMAL_3x3": "正创建匹配模式", "hosting_NORMAL_TFT": "正创建云顶之弈对局", "hosting_PRACTICETOOL": "正创建训练模式", "hosting_RANKED_FLEX_SR": "正创建排位对局", "hosting_RANKED_FLEX_TT": "正创建排位对局", "hosting_RANKED_SOLO_5x5": "正创建排位对局", "hosting_RANKED_TEAM_5x5": "正创建排位对局", "hosting_RANKED_TFT": "正创建云顶之弈对局", "hosting_RANKED_TFT_TURBO": "正创建云顶之弈对局", "hosting_RANKED_TFT_PAIRS": "正创建双人作战对局", "hosting_RANKED_TFT_DOUBLE_UP": "正创建双人作战", "hosting_STRAWBERRY": "正创建【无尽狂潮】对局", "hosting_CHONCC_TREASURE_TFT": "正创建云顶之弈对局", "hosting_LNY23_TFT": "正创建云顶之弈对局", "hosting_LNY24_TFT": "正创建云顶之弈对局", "hosting_LNY25_TFT": "正在创建云顶之弈对局", "hosting_SET_REVIVAL_5_5_TFT": "正在创建云顶之弈对局", "hosting_FIVE_YEAR_ANNIVERSARY_TFT": "正在创建云顶之弈对局", "hosting_SF_TFT": "正创建云顶之弈对局", "hosting_PVE_PUZZLE_TFT": "正创建云顶之弈对局", "hosting_featured": "正创建特殊模式", "inGame": "游戏中", "inQueue": "队列中", "inTeamBuilder": "阵容匹配中", "map_hosting_ARAM_UNRANKED_5x5": "正创建匹配模式（进步之桥）", "map_hosting_NORMAL": "正创建匹配模式（召唤师峡谷）", "map_hosting_NORMAL_3x3": "正创建匹配模式（扭曲丛林）", "map_hosting_RANKED_FLEX_SR": "正创建灵活排位（召唤师峡谷）", "map_hosting_RANKED_FLEX_TT": "正创建灵活排位（扭曲丛林）", "mobile": "在线分组", "offline": "离线", "online": "在线", "spectating": "正在观战中", "teamSelect": "正在选择队伍", "tutorial": "正在新手教程中", "undefined": "待定……", "watchingReplay": "正在观看回放", "outOfGame": "在线"} #来源（Source）：plugins/rcp-fe-lol-social/global/zh_cn
    inventoryType_dict = {"ACHIEVEMENT_BANNER_ACCENT": "旗帜装饰", "ACHIEVEMENT_TITLE": "头衔", "ANNOUNCER_PACK": "播报员语音包", "AUGMENT": "AUGMENT", "AUGMENT_SLOT": "AUGMENT_SLOT", "BOOST": "加成道具", "BUNDLES": "道具包", "CHAMPION": "英雄", "CHAMPION_SKIN": "皮肤", "CHERRY_BOON": "斗魂竞技场赛季旅程奖励", "COMPANION": "小小英雄", "CURRENCY": "货币", "EMOTE": "表情", "EVENT_PASS": "事件通行证", "FANPASS": "粉丝通行证", "GIFT": "礼物", "HEXTECH_CRAFTING": "海克斯科技宝箱", "MODE_PROGRESSION_REWARD": "游戏模式进度奖励", "MYSTERY": "神秘道具", "NEXUS_FINISHER": "终结特效", "PREMIUM_CLUB_MEMBERSHIP": "高级俱乐部会员身份", "PROGRESSION": "通行证升级", "PROVIEW_PASS": "Pro View许可", "PVE_RELIC": "PVE_RELIC", "PVE_SUMMONER_PACKAGE": "PVE_SUMMONER_PACKAGE", "PVE_UPGRADE": "PVE模式战略目标属性增益", "QUEUE_ENTRY": "队列通行证", "REGALIA_BANNER": "旗帜", "REGALIA_BORDER": "排位边框", "REGALIA_CREST": "徽章", "RP": "点券", "RUNE": "符文", "SKIN_AUGMENT": "签名升级", "SKIN_BORDER": "皮肤边框", "SKIN_UPGRADE_GEAR": "皮肤自带服装升级", "SKIN_UPGRADE_HOME_GUARD": "皮肤自带家园卫士特效", "SKIN_UPGRADE_RECALL": "皮肤自带回城特效", "SKIN_UPGRADE_SPAWN": "皮肤自带重生特效", "SPELL_BOOK_PAGE": "符文页", "STATSTONE": "永恒星碑", "STRAWBERRY_BOON": "无尽狂潮增益效果", "STRAWBERRY_LOADOUT_ITEM": "无尽狂潮配置", "STRAWBERRY_MAP": "无尽狂潮地图", "SUMMONER_CUSTOMIZATION": "SUMMONER_CUSTOMIZATION", "SUMMONER_ICON": "召唤师图标", "TEAMPASS": "战队通行证", "TEAM_SKIN_PURCHASE": "TEAM_SKIN_PURCHASE", "TFT_DAMAGE_SKIN": "云顶之弈进攻特效", "TFT_EVENT_SKILLS": "云顶之弈技巧加成", "TFT_MAP_SKIN": "云顶之弈棋盘皮肤", "TFT_PLAYBOOK": "云顶之弈指导手册", "TFT_ZOOM_SKIN": "云顶之弈传送门", "TOURNAMENT_FLAG": "冠军杯赛旗帜", "TOURNAMENT_FRAME": "冠军杯赛旗帜框架", "TOURNAMENT_LOGO": "冠军杯赛标志", "TOURNAMENT_TROPHY": "冠军杯赛奖杯", "TRANSFER": "转区项目", "WARD_SKIN": "守卫（眼）皮肤"}
    ownershipType_dict = {None: "未拥有", "F2P": "免费使用", "RENTED": "租借中", "OWNED": "已拥有"}
    botDifficulty_dict = {"NONE": "无", "TUTORIAL": "新手", "INTRO": "入门", "EASY": "简单", "MEDIUM": "一般", "HARD": "困难", "UBER": "末日", "RSWARMINTRO": "温暖局入门级", "RSINTRO": "入门级", "RSBEGINNER": "新手级", "RSINTERMEDIATE": "一般级"}
    position_dict = {"": "", "NONE": "无", "UNSELECTED": "未定", "TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "UTILITY": "辅助", "FILL": "补位", "LANE": "线上"}
    honorType_tooltip_headers = {"COOL": "护卫大神", "SHOTCALLER": "指挥大神", "HEART": "Carry大神"}
    # honorType_tooltip_headers = {"COOL": "Stayed cool", "SHOTCALLER": "Great shotcalling", "HEART": "GG <3"}
    honorType_tooltip_bodies = {"COOL": "可靠支柱，强大助力", "SHOTCALLER": "战术大师，掌控全局", "HEART": "核心战力，统治战场"}
    # honorType_tooltip_bodies = {"COOL": "Tilt-proof, chill", "SHOTCALLER": "Leadership, strategy", "HEART": "Team player, friendly"}
    zoom_scale_dict = {0.8: "1024 × 576", 1.0: "1280 × 720", 1.25: "1600 × 900", 1.5: "1920 × 1080"}
    #定义常量（Define constant values）
    global GLOBAL_RESPONSE_LAG, QUIT_UX_WARNING, message_hint_printed, ballot_endpoint_notavailable_hint_printed, expand_matchHistory_hint_printed, collection_df_json_relpath, skins_df_json_relpath, collection_df_refresh, collection_df_json_exist, skins_df_refresh, skins_df_json_exist, botDifficulty_list, champSelect_players_header, champSelect_players_header_keys, LoLChampions_header, LoLChampions_header_keys, custom_lobby_header, custom_lobby_header_keys, skins_header, skins_header_keys, conversation_header, conversation_header_keys, grid_champion_header, grid_champion_header_keys, muted_players_header, muted_players_header_keys, invid_header, invid_header_keys, perkPage_header, perkPage_header_keys, social_leaderboard_header, social_leaderboard_header_keys, availableBot_header, availableBot_header_keys, member_header, member_header_keys, ballot_player_header, ballot_player_header_keys, eog_mastery_update_header, eog_mastery_update_header_keys, eog_stat_metadata_lol_header, eog_stat_metadata_lol_header_keys, eog_teamstat_data_lol_header, eog_teamstat_data_lol_header_keys, eog_playerstat_data_lol_header, eog_playerstat_data_lol_header_keys, eog_stat_metadata_tft_header, eog_stat_metadata_tft_header_keys, eog_stat_data_tft_header, eog_stat_data_tft_header_keys
    GLOBAL_RESPONSE_LAG = 0.2
    QUIT_UX_WARNING = '''警告：此操作将彻底清除与本次会话相关的英雄联盟客户端进程。（正在进行中的游戏不受影响。）这个操作是不可逆的。您确定要继续吗？（输入“quit”以继续，否则取消本次操作。）\nWarning: This operation will terminate all League Client processes related to this session. (On-going games won't be affected.) This operation is irreversible. Do you really want to continue? (Submit "quit" to continue, otherwise cancel this operation.)'''
    message_hint_printed = False
    ballot_endpoint_notavailable_hint_printed = False
    expand_matchHistory_hint_printed = False
    collection_df_json_relpath = "cache/collection_df_json.pkl"
    skins_df_json_relpath = "cache/skins_df_json.pkl"
    collection_df_refresh = collection_df_json_exist = False
    skins_df_refresh = skins_df_json_exist = False
    botDifficulty_list = ["NONE", "TUTORIAL", "INTRO", "EASY", "MEDIUM", "HARD", "UBER", "RSWARMINTRO", "RSINTRO", "RSBEGINNER", "RSINTERMEDIATE"]
    champSelect_players_header = {"assignedPosition": "分配路线", "cellId": "槽位序号", "championId": "选用英雄序号", "championPickIntent": "声明英雄序号", "gameName": "玩家昵称", "internalName": "内置名", "isHumanoid": "电脑玩家", "nameVisibilityType": "信息可见性", "obfuscatedPuuid": "隐藏识别码", "obfuscatedSummonerId": "隐藏召唤师序号", "pickMode": "选用模式", "pickTurn": "选用顺序", "playerAlias": "玩家代号", "playerType": "玩家类型", "puuid": "玩家通用唯一识别码", "selectedSkinId": "选用皮肤序号", "spell1Id": "召唤师技能1序号", "spell2Id": "召唤师技能2序号", "summonerId": "召唤师序号", "tagLine": "昵称编号", "team": "阵营", "wardSkinId": "饰品序号", "team_color": "阵营名称", "champion name": "选用英雄名称", "champion alias": "选用英雄代号", "championPickIntent name": "声明英雄名称", "championPickIntent alias": "声明英雄代号", "selectedSkin contentId": "选用（炫彩）皮肤商品编号", "selectedSkin name": "选用（炫彩）皮肤名称", "selectedSkin splashPath": "选用（炫彩）皮肤插画", "selectedSkin uncenteredSplashPath": "选用（炫彩）皮肤原画", "selectedSkin tilePath": "选用（炫彩）皮肤方块图像", "selectedSkin loadScreenPath": "选用（炫彩）皮肤经典加载界面", "selectedSkin loadScreenVintagePath": "选用（炫彩）皮肤带边框加载界面", "selectedSkin rarity": "选用（炫彩）皮肤品质", "selectedSkin splashVideoPath": "选用（炫彩）皮肤视频", "selectedSkin chromaPath": "选用（炫彩）皮肤炫彩", "spell1 name": "召唤师技能1名称", "spell1 iconPath": "召唤师技能1图标", "spell2 name": "召唤师技能2名称", "spell2 iconPath": "召唤师技能2图标", "wardSkin name": "饰品名称", "wardSkin description": "饰品简介", "wardSkin wardImagePath": "饰品图标", "wardSkin wardShadowImagePath": "饰品阴影", "wardSkin isLegacy": "限定饰品", "wardSkin rarity": "饰品品质"}
    champSelect_players_header_keys = list(champSelect_players_header.keys())
    LoLChampions_header = {"active": "可用性", "alias": "英雄代号", "banVoPath": "禁用台词路径", "baseLoadScreenPath": "加载界面图像路径", "baseSplashPath": "英雄封面路径", "botEnabled": "电脑模型激活情况", "chooseVoPath": "锁定台词路径", "disabledQueues": "禁用队列", "freeToPlay": "允许免费使用", "id": "英雄序号", "isVisibleInClient": "藏品可见性", "name": "称号", "purchased": "购买时间戳", "rankedPlayEnabled": "取得排位许可", "squarePortraitPath": "方格头像路径", "stingerSfxPath": "锁定音效路径", "title": "名称", "purchaseDate": "购买日期", "ownership: loyaltyReward": "获取方式：排位赛段奖励", "ownership: owned": "已拥有", "ownership: xboxGPReward": "获取方式：Xbox Game Pass奖励", "ownership: rental: endDate": "租借截止时间戳", "ownership: rental: purchaseDate": "租借时间戳", "ownership: rental: rented": "已租借", "ownership: rented: winCountRemaining": "租借可用胜场数", "ownership: rental: endTime": "租借截止日期", "ownership: rental: purchaseTime": "租借日期", "role: assassin": "角色定位：刺客", "role: fighter": "角色定位：战士", "role: mage": "角色定位：法师", "role: marksman": "角色定位：射手", "role: support": "角色定位：辅助", "role: tank": "角色定位：坦克", "tacticalInfo: damageType": "战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】", "tacticalInfo: difficulty": "战略信息：难度（英雄的使用难度）", "tacticalInfo: style": "战略信息：风格【表明英雄的伤害输出方式的倾向（普攻vs技能）】", "passive: description": "被动技能简介", "passive: name": "被动技能名称", "spell1: description": "技能1简介", "spell1: name": "技能1名称", "spell2: description": "技能2简介", "spell2: name": "技能2名称", "spell3: description": "技能3简介", "spell3: name": "技能3名称", "spell4: description": "技能4简介", "spell4: name": "技能4名称", "recommendedPosition: TOP": "推荐路线：上路", "recommendedPosition: JUNGLE": "推荐路线：打野", "recommendedPosition: MIDDLE": "推荐路线：中路", "recommendedPosition: BOTTOM": "推荐路线：下路", "recommendedPosition: UTILITY": "推荐路线：辅助"}
    LoLChampions_header_keys = list(LoLChampions_header.keys())
    custom_lobby_header = {"filledPlayerSlots": "玩家数量", "filledSpectatorSlots": "观战者数量", "gameType": "游戏类型", "hasPassword": "密码验证", "id": "房间代码", "lobbyName": "房间名", "mapId": "地图序号", "maxPlayerSlots": "最大玩家数量", "maxSpectatorSlots": "最大观战者数量", "ownerDisplayName": "房主显示名", "partyId": "小队序号", "passbackUrl": "回调网址", "spectatorPolicy": "观战策略", "mapName": "地图名称", "filledPlayerRatio": "玩家比例", "filledSpectatorRatio": "观战者比例"}
    custom_lobby_header_keys = list(custom_lobby_header.keys())
    skins_header = {"chromaPath": "炫彩路径", "colors": "颜色配置", "collectionCardHoverVideoPath": "集合悬停卡视频路径", "collectionSplashVideoPath": "集合介绍视频路径", "contentId": "商品编号", "description": "描述", "featuresText": "特征文本", "id": "皮肤序号", "isBase": "经典皮肤", "isLegacy": "限定皮肤", "loadScreenPath": "经典加载界面路径", "loadScreenVintagePath": "带边框加载界面路径", "name": "名称", "previewVideoUrl": "预览视频链接", "rarities": "各地区品质", "rarity": "品质", "rarityGemPath": "品质徽章路径", "regionRarityId": "地区品质级别", "shortName": "简称", "skinAugments": "皮肤强化", "skinClassification": "皮肤类别", "skinFeaturePreviewData": "皮肤特征预览数据", "skinLines": "皮肤套装", "skinType": "皮肤类型", "splashPath": "插画路径", "splashVideoPath": "视频路径", "stage": "获取进度", "tilePath": "方块图像路径", "uncenteredSplashPath": "原画路径", "emblem_name": "标志名称", "emblem_positions": "标志位置坐标", "emblemPath_large": "标志大图路径", "emblemPath_small": "标志小图路径", "questSkinInfo collectionCardPath": "任务皮肤信息：集合卡片路径", "questSkinInfo collectionDescription": "任务皮肤信息：集合描述", "questSkinInfo descriptionInfo": "任务皮肤信息：介绍信息", "questSkinInfo name": "任务皮肤信息：名称", "questSkinInfo productType": "任务皮肤信息：皮肤类型", "questSkinInfo splashPath": "任务皮肤信息：插画路径", "questSkinInfo tilePath": "任务皮肤信息：方块图像路径", "questSkinInfo uncenteredSplashPath": "任务皮肤信息：原画路径", "championId": "对应英雄序号", "disabled": "已禁用", "lastSelected": "上次使用", "stillObtainable": "可获取", "champion_name": "对应英雄称号", "champion_alias": "对应英雄代号", "champion_title": "对应英雄名称", "ownership loyaltyReward": "获取方式：排位赛段奖励", "ownership owned": "已拥有", "ownership xboxGPReward": "获取方式：Xbox Game Pass奖励", "ownership rental endDate": "租借截止时间戳", "ownership rental purchaseDate": "购买时间戳", "ownership rental rented": "已租借", "ownership rental winCountRemaining": "租借可用胜场数", "ownership rental endTime": "租借截止日期", "ownership rental purchaseTime": "购买日期"}
    skins_header_keys = list(skins_header.keys())
    conversation_header = {"gameName": "玩家昵称", "gameTag": "昵称编号", "id": "对话序号", "inviterId": "邀请人序号", "isMuted": "已静音", "name": "召唤师显示名", "password": "密码", "pid": "社交代码", "targetRegion": "目标服务器", "type": "对话类型", "unreadMessageCount": "未读消息数"}
    conversation_header_keys = list(conversation_header.keys())
    grid_champion_header = {"disabled": "已禁用", "freeToPlay": "免费使用", "freeToPlayForQueue": "队列内免费使用", "id": "英雄序号", "loyaltyReward": "通过排位赛奖励获得", "masteryLevel": "成就等级", "masteryPoints": "成就点数", "name": "名称", "owned": "已拥有", "positionsFavorited": "最爱位置", "rented": "已租赁", "squarePortraitPath": "方块头像路径", "xboxGPReward": "通过Xbox Game Pass奖励获得", "favorite_top": "最爱的上路英雄", "favorite_jungle": "最爱的打野英雄", "favorite_middle": "最爱的中路英雄", "favorite_bottom": "最爱的下路英雄", "favorite_support": "最爱的辅助英雄", "banIntented": "禁用声明", "banIntentedByMe": "本人禁用声明", "isBanned": "已禁用", "pickIntented": "选用声明", "pickIntentedByMe": "本人选用声明", "pickIntentedPosition": "选用声明位置", "pickedByOtherOrBanned": "因他人选用或被禁用导致不可用", "selectedByMe": "已选用"}
    grid_champion_header_keys = list(grid_champion_header.keys())
    muted_players_header = {"puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "obfuscatedPuuid": "隐藏玩家通用唯一识别码", "obfuscatedSummonerId": "隐藏召唤师序号", "gameName": "玩家昵称", "tagLine": "昵称编号"}
    muted_players_header_keys = list(muted_players_header.keys())
    invid_header = {"canAcceptInvitation": "允许接受邀请", "fromSummonerId": "邀请人召唤师序号", "fromSummonerName": "邀请人召唤师名", "invitationId": "邀请码", "invitationType": "邀请类型", "restrictions": "限制", "state": "邀请状态", "timestamp": "邀请时间戳", "fromPuuid": "邀请人玩家通用唯一识别码", "time": "邀请时间", "gameMode": "游戏模式", "inviteGameType": "游戏类型", "mapId": "地图序号", "queueId": "队列序号", "queue name": "队列名称"}
    invid_header_keys = list(invid_header.keys())
    perkPage_header = {"autoModifiedSelections": "自动调整选择", "current": "正在使用", "id": "符文页序号", "isActive": "活动中", "isDeletable": "可删除", "isEditable": "可编辑", "isRecommendationOverride": "覆盖系统推荐符文", "isTemporary": "临时创建", "isValid": "可用性", "lastModified": "上次修改时间戳", "name": "符文页名称", "order": "符文页位次", "primaryStyleIconPath": "主系图标路径", "primaryStyleId": "主系序号", "primaryStyleName": "主系名称", "quickPlayChampionIds": "快速模式英雄序号列表", "recommendationChampionId": "推荐英雄序号", "recommendationIndex": "推荐序号", "runeRecommendationId": "推荐号", "secondaryStyleIconPath": "副系图标路径", "secondaryStyleName": "副系名称", "selectedPerkIds": "已选择的符文序号列表", "subStyleId": "副系序号", "tooltipBgPath": "已配置的符文背景图片路径", "lastModifiedTime": "上次修改时间", "quickPlayChampionNames": "快速模式英雄名称列表", "recommendationChampionName": "推荐英雄名称", "pageKeystone iconPath": "基石图标路径", "pageKeystone id": "基石序号", "pageKeystone name": "基石名称", "pageKeystone slotType": "基石槽位类型", "pageKeystone styleId": "基石所属符文系序号", "uiPerksNames": "已选择的符文"}
    perkPage_header_keys = list(perkPage_header.keys())
    social_leaderboard_header = {"availability": "可用性", "division": "段位分级", "gameName": "玩家昵称", "isGiftable": "可赠送礼物", "isProvisional": "定位中", "leaderboardPosition": "排名", "leaguePoints": "胜点", "profileIconId": "召唤师图标序号", "provisionalGamesRemaining": "剩余定位场次", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "summonerLevel": "召唤师等级", "summonerName": "召唤师名", "tagLine": "昵称编号", "tier": "段位", "wins": "胜场", "profileIcon_title": "召唤师图标名称", "profileIcon_imagePath": "召唤师图标路径"}
    social_leaderboard_header_keys = list(social_leaderboard_header.keys())
    availableBot_header = {"active": "可用性", "botDifficulties": "可用难度代码", "id": "英雄序号", "name": "称号", "alias": "代号", "title": "名称"}
    availableBot_header_keys = list(availableBot_header.keys())
    member_header = {"allowedChangeActivity": "允许更改模式", "allowedInviteOthers": "允许邀请玩家", "allowedKickOthers": "允许移出玩家", "allowedStartActivity": "允许开始游戏", "allowedToggleInvite": "允许更改邀请权限", "autoFillEligible": "自动补位已激活", "autoFillProtectedForPromos": "自动补位已保护：晋级赛", "autoFillProtectedForRemedy": "自动补位已保护：不良行为补偿", "autoFillProtectedForSoloing": "自动补位已保护：单排", "autoFillProtectedForStreaking": "自动补位已保护：连胜", "botChampionId": "电脑玩家英雄序号", "botDifficulty": "电脑玩家难度", "botId": "电脑玩家内置名", "botPosition": "电脑玩家角色定位", "botUuid": "电脑玩家通用唯一识别码", "firstPositionPreference": "首选位置", "intraSubteamPosition": "子阵营位置", "isBot": "电脑玩家", "isLeader": "小队拥有者", "isSpectator": "观战者", "memberData": "成员数据", "playerSlots": "快速模式数据", "puuid": "玩家通用唯一识别码", "ready": "准备就绪", "secondPositionPreference": "次选位置", "showGhostedBanner": "未准备就绪提示", "strawberryMapId": "无尽狂潮地图序号", "subteamIndex": "子阵营序号", "summonerIconId": "召唤师图标序号", "summonerId": "召唤师序号", "summonerInternalName": "召唤师内置名", "summonerLevel": "召唤师等级", "summonerName": "召唤师名", "teamId": "队伍序号", "botChampion_name": "电脑玩家英雄称号", "botChampion_alias": "电脑玩家英雄代号", "botChampion_title": "电脑玩家英雄名称", "botDifficulty_localized": "电脑玩家难度等级", "botPosition_localized": "电脑玩家分路", "primaryPosition": "首选", "secondaryPosition": "次选", "strawberryMapName": "无尽狂潮地图名称", "summonerIcon_title": "召唤师图标名称", "summonerIcon_imagePath": "召唤师图标路径", "gameName": "玩家昵称", "tagLine": "昵称编号"}
    member_header_keys = list(member_header.keys())
    ballot_player_header = {"botPlayer": "电脑玩家", "championName": "英雄名称", "puuid": "玩家通用唯一识别码", "role": "角色定位", "skinSplashPath": "皮肤插画路径", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "gameName": "玩家昵称", "tagLine": "昵称编号", "ally?": "是否队友", "honored": "已赞誉", "honorType": "赞誉类型", "honorType_tooltip_header": "赞誉类型标题", "honorType_tooltip_body": "赞誉类型正文"}
    ballot_player_header_keys = list(ballot_player_header.keys())
    eog_mastery_update_header = {"bonusPointsGained": "本场对局额外获取成就点数", "championId": "使用英雄序号", "gameId": "对局序号", "grade": "对局评价", "hasLeveledUp": "升级", "id": "对局序号", "level": "成就等级", "levelUpList": "升级列表", "memberGrades": "成员评价", "pointsBeforeGame": "对局开始前总成就点数", "pointsGained": "本场对局获取成就点数", "pointsGainedIndividualContribution": "个人贡献成就点数", "pointsSinceLastLevelBeforeGame": "对局开始前当前成就点数", "pointsUntilNextLevelAfterGame": "对局结束后下次升级所需成就点数", "pointsUntilNextLevelBeforeGame": "对局开始前下次升级所需成就点数", "puuid": "玩家通用唯一识别码", "score": "分数", "tokenEarnedAfterGame": "对局结束后获取英雄成就标记", "tokensEarned": "获取英雄成就标记数量", "champion_name": "使用英雄称号", "champion_alias": "使用英雄代号", "champion_title": "使用英雄名称", "gameName": "玩家昵称", "tagLine": "昵称编号"}
    eog_mastery_update_header_keys = list(eog_mastery_update_header.keys())
    eog_stat_metadata_lol_header = {"basePoints": "基础胜点", "battleBoostIpEarned": "全员战斗加成提供蓝色精萃", "boostIpEarned": "蓝色精萃加成", "boostXpEarned": "经验值加成", "causedEarlySurrender": "发起提前投降", "currentLevel": "当前召唤师等级", "difficulty": "难度", "earlySurrenderAccomplice": "同意提前投降", "endOfGameTimestamp": "对局结算时间戳", "experienceEarned": "获得经验值", "experienceTotal": "总经验值", "firstWinBonus": "取得首胜奖励", "gameEndedInEarlySurrender": "提前投降导致比赛结束", "gameId": "对局序号", "gameLength": "持续时长（秒）", "gameMode": "游戏模式", "gameMutators": "游戏规则说明", "gameType": "游戏类型", "globalBoostXpEarned": "事件经验值加成", "invalid": "对局结算无效", "ipEarned": "获得蓝色精萃", "ipTotal": "本场对局获得的总蓝色精萃", "leveledUp": "召唤师已升级", "loyaltyBoostXpEarned": "网吧特权经验值加成", "missionsXpEarned": "任务经验值", "multiUserChatId": "聊天室社交代码", "multiUserChatPassword": "聊天室密码", "myTeamStatus": "我方状态", "newSpells": "新的召唤师技能序号", "nextLevelXp": "下次升级所需召唤师经验值", "preLevelUpExperienceTotal": "升级前当前召唤师经验值", "preLevelUpNextLevelXp": "升级前下次升级所需召唤师经验值", "previousLevel": "对局开始前召唤师等级", "previousXpTotal": "对局开始前当前召唤师经验值", "queueType": "队列类型", "ranked": "排位赛", "reportGameId": "报告对局序号", "rpEarned": "点券加成", "teamEarlySurrendered": "队伍提前投降", "timeUntilNextFirstWinBonus": "下次首胜剩余时间（秒）", "xbgpBoostXpEarned": "游戏通行证经验值加成", "endOfGameTime": "对局结算时间", "gameLength_norm": "持续时长", "newSpellNames": "新的召唤师技能名称", "timeUntilNextFirstWinBonus_norm": "下次首胜剩余时间", "queueId": "队列序号", "gameModeName": "游戏模式名称", "mucJwtDto channelClaim": "聊天室声明", "mucJwtDto domain": "聊天室域名", "mucJwtDto jwt": "聊天室令牌", "mucJwtDto targetRegion": "聊天室目标大区", "rerollData pointChangeFromChampionsOwned": "大乱斗重随点数英雄加成", "rerollData pointChangeFromGameplay": "大乱斗重随点数加成", "rerollData pointsUntilNextReroll": "增加一次重随次数所需大乱斗重随点数", "rerollData pointsUsed": "消耗大乱斗重随点数", "rerollData previousPoints": "对局开始前大乱斗重随点数", "rerollData rerollCount": "大乱斗重随次数", "rerollData totalPoints": "大乱斗总重随点数", "teamBoost availableSkins": "战斗加成可用皮肤", "teamBoost ipReward": "战斗加成全队蓝色精萃奖励", "teamBoost ipRewardForPurchaser": "战斗加成激活者蓝色精萃奖励", "teamBoost price": "战斗加成价格", "teamBoost skinUnlockMode": "战斗加成皮肤解锁方式", "teamBoost summonerName": "战斗加成激活者召唤师名称", "teamBoost unlocked": "战斗加成已解锁", "teamBoost availableSkinNames": "战斗加成可用皮肤名称"}
    eog_stat_metadata_lol_header_keys = list(eog_stat_metadata_lol_header.keys())
    eog_teamstat_data_lol_header = {"fullId": "完整代号", "isBottomTeam": "蓝方", "isPlayerTeam": "玩家所在阵营", "isWinningTeam": "胜方", "memberStatusString": "成员状态", "name": "队伍名称", "tag": "队伍尾标", "teamId": "阵营代号", "team": "阵营", "stats ASSISTS": "队伍助攻", "stats BARRACKS_KILLED": "摧毁召唤水晶", "stats CHAMPIONS_KILLED": "队伍击杀", "stats GAME_ENDED_IN_EARLY_SURRENDER": "提前投降导致比赛结束", "stats GAME_ENDED_IN_SURRENDER": "投降导致比赛结束", "stats GOLD_EARNED": "队伍赚取金币", "stats LARGEST_CRITICAL_STRIKE": "最大暴击伤害总和", "stats LARGEST_KILLING_SPREE": "最高连杀总和", "stats LARGEST_MULTI_KILL": "最高多杀总和", "stats LEVEL": "英雄等级总和", "stats LOSE": "失败", "stats MAGIC_DAMAGE_DEALT_PLAYER": "造成的魔法伤害", "stats MAGIC_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的魔法伤害", "stats MAGIC_DAMAGE_TAKEN": "承受的魔法伤害", "stats MINIONS_KILLED": "击杀小兵", "stats NEUTRAL_MINIONS_KILLED": "击杀野怪", "stats NEUTRAL_MINIONS_KILLED_ENEMY_JUNGLE": "击杀敌方野区野怪", "stats NEUTRAL_MINIONS_KILLED_YOUR_JUNGLE": "击杀我方野区野怪", "stats NODE_CAPTURE": "占领据点", "stats NODE_CAPTURE_ASSIST": "协助占领据点", "stats NODE_NEUTRALIZE": "夺回据点", "stats NODE_NEUTRALIZE_ASSIST": "协助夺回据点", "stats NUM_DEATHS": "队伍死亡", "stats PERK_PRIMARY_STYLE": "主系序号", "stats PERK_SUB_STYLE": "副系序号", "stats PERK0": "符文1序号", "stats PERK0_VAR1": "符文1：参数1", "stats PERK0_VAR2": "符文1：参数2", "stats PERK0_VAR3": "符文1：参数3", "stats PERK1": "符文2序号", "stats PERK1_VAR1": "符文2：参数1", "stats PERK1_VAR2": "符文2：参数2", "stats PERK1_VAR3": "符文2：参数3", "stats PERK2": "符文3序号", "stats PERK2_VAR1": "符文3：参数1", "stats PERK2_VAR2": "符文3：参数2", "stats PERK2_VAR3": "符文3：参数3", "stats PERK3": "符文4序号", "stats PERK3_VAR1": "符文4：参数1", "stats PERK3_VAR2": "符文4：参数2", "stats PERK3_VAR3": "符文4：参数3", "stats PERK4": "符文5序号", "stats PERK4_VAR1": "符文5：参数1", "stats PERK4_VAR2": "符文5：参数2", "stats PERK4_VAR3": "符文5：参数3", "stats PERK5": "符文6序号", "stats PERK5_VAR1": "符文6：参数1", "stats PERK5_VAR2": "符文6：参数2", "stats PERK5_VAR3": "符文6：参数3", "stats PHYSICAL_DAMAGE_DEALT_PLAYER": "造成的物理伤害", "stats PHYSICAL_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的物理伤害", "stats PHYSICAL_DAMAGE_TAKEN": "承受的物理伤害", "stats PLAYER_AUGMENT_1": "强化符文1序号", "stats PLAYER_AUGMENT_2": "强化符文2序号", "stats PLAYER_AUGMENT_3": "强化符文3序号", "stats PLAYER_AUGMENT_4": "强化符文4序号", "stats PLAYER_AUGMENT_5": "强化符文5序号", "stats PLAYER_AUGMENT_6": "强化符文6序号", "stats PLAYER_SCORE_0": "玩家得分1", "stats PLAYER_SCORE_1": "玩家得分2", "stats PLAYER_SCORE_2": "玩家得分3", "stats PLAYER_SCORE_3": "玩家得分4", "stats PLAYER_SCORE_4": "玩家得分5", "stats PLAYER_SCORE_5": "玩家得分6", "stats PLAYER_SCORE_6": "玩家得分7", "stats PLAYER_SCORE_7": "玩家得分8", "stats PLAYER_SCORE_8": "玩家得分9", "stats PLAYER_SCORE_9": "玩家得分10", "stats PLAYER_SUBTEAM": "子阵营代号总和", "stats PLAYER_SUBTEAM_PLACEMENT": "队伍排名总和", "stats SIGHT_WARDS_BOUGHT_IN_GAME": "购买洞察之石", "stats SPELL1_CAST": "召唤师技能1施放次数", "stats SPELL2_CAST": "召唤师技能2施放次数", "stats TEAM_EARLY_SURRENDERED": "队伍提前投降", "stats TEAM_OBJECTIVE": "团队夺取战略点数量", "stats TIME_CCING_OTHERS": "控制得分", "stats TOTAL_DAMAGE_DEALT": "造成的伤害总和", "stats TOTAL_DAMAGE_DEALT_TO_BUILDINGS": "对建筑物的总伤害", "stats TOTAL_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的伤害总和", "stats TOTAL_DAMAGE_DEALT_TO_OBJECTIVES": "对战略点的总伤害", "stats TOTAL_DAMAGE_DEALT_TO_TURRETS": "对防御塔的总伤害", "stats TOTAL_DAMAGE_SELF_MITIGATED": "自我缓和的伤害", "stats TOTAL_DAMAGE_SHIELDED_ON_TEAMMATES": "友方护盾", "stats TOTAL_DAMAGE_TAKEN": "承受伤害", "stats TOTAL_HEAL": "治疗伤害", "stats TOTAL_HEAL_ON_TEAMMATES": "友方治疗", "stats TOTAL_TIME_CROWD_CONTROL_DEALT": "控制时间", "stats TOTAL_TIME_SPENT_DEAD": "死亡总时间", "stats TRUE_DAMAGE_DEALT_PLAYER": "造成真实伤害", "stats TRUE_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的真实伤害", "stats TRUE_DAMAGE_TAKEN": "承受的真实伤害", "stats TURRETS_KILLED": "摧毁防御塔", "stats VICTORY_POINT_TOTAL": "总胜利点数", "stats VISION_SCORE": "视野得分", "stats VISION_WARDS_BOUGHT_IN_GAME": "购买控制守卫", "stats WARD_KILLED": "摧毁守卫", "stats WARD_PLACED": "放置守卫", "stats WAS_AFK": "存在中途退出现象", "stats WIN": "胜利", "stats KDA": "队伍击杀得分"}
    eog_teamstat_data_lol_header_keys = list(eog_teamstat_data_lol_header.keys())
    eog_playerstat_data_lol_header = {"botPlayer": "电脑玩家", "championId": "英雄序号", "championName": "英雄称号", "championSquarePortraitPath": "英雄方块头像路径", "detectedTeamPosition": "推测角色定位", "gameId": "对局序号", "isLocalPlayer": "本人标记", "items": "装备序号列表", "leaver": "挂机", "leaves": "早退次数", "level": "召唤师等级", "losses": "模式负场", "profileIconId": "召唤师图标序号", "puuid": "玩家通用唯一识别码", "riotIdGameName": "玩家昵称", "riotIdTagLine": "昵称编号", "selectedPosition": "选择角色定位", "skinEmblemPaths": "皮肤徽章路径", "skinSplashPath": "皮肤插画路径", "skinTilePath": "皮肤小图路径", "spell1Id": "召唤师技能1序号", "spell2Id": "召唤师技能2序号", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "teamId": "阵营代号", "wins": "模式胜场", "item0_name": "装备1", "item1_name": "装备2", "item2_name": "装备3", "item3_name": "装备4", "item4_name": "装备5", "item5_name": "装备6", "item6_name": "饰品", "item0_iconPath": "装备1图标路径", "item1_iconPath": "装备2图标路径", "item2_iconPath": "装备3图标路径", "item3_iconPath": "装备4图标路径", "item4_iconPath": "装备5图标路径", "item5_iconPath": "装备6图标路径", "item6_iconPath": "饰品图标路径", "profileIcon_title": "召唤师图标名称", "profileIcon_imagePath": "召唤师图标路径", "spell1_name": "召唤师技能1", "spell2_name": "召唤师技能2", "spell1_iconPath": "召唤师技能1图标", "spell2_iconPath": "召唤师技能2图标", "team_color": "阵营", "stats ASSISTS": "助攻", "stats BARRACKS_KILLED": "摧毁召唤水晶", "stats CHAMPIONS_KILLED": "击杀", "stats GAME_ENDED_IN_EARLY_SURRENDER": "提前投降导致比赛结束", "stats GAME_ENDED_IN_SURRENDER": "投降导致比赛结束", "stats GOLD_EARNED": "金币获取", "stats LARGEST_CRITICAL_STRIKE": "最大暴击伤害", "stats LARGEST_KILLING_SPREE": "最高连杀", "stats LARGEST_MULTI_KILL": "最高多杀", "stats LEVEL": "英雄等级", "stats LOSE": "失败", "stats MAGIC_DAMAGE_DEALT_PLAYER": "造成的魔法伤害", "stats MAGIC_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的魔法伤害", "stats MAGIC_DAMAGE_TAKEN": "承受的魔法伤害", "stats MINIONS_KILLED": "击杀小兵", "stats NEUTRAL_MINIONS_KILLED": "击杀野怪", "stats NEUTRAL_MINIONS_KILLED_ENEMY_JUNGLE": "击杀敌方野区野怪", "stats NEUTRAL_MINIONS_KILLED_YOUR_JUNGLE": "击杀我方野区野怪", "stats NODE_CAPTURE": "占领据点", "stats NODE_CAPTURE_ASSIST": "协助占领据点", "stats NODE_NEUTRALIZE": "夺回据点", "stats NODE_NEUTRALIZE_ASSIST": "协助夺回据点", "stats NUM_DEATHS": "死亡", "stats PERK_PRIMARY_STYLE": "主系序号", "stats PERK_SUB_STYLE": "副系序号", "stats PERK0": "符文1序号", "stats PERK0_VAR1": "符文1：参数1", "stats PERK0_VAR2": "符文1：参数2", "stats PERK0_VAR3": "符文1：参数3", "stats PERK1": "符文2序号", "stats PERK1_VAR1": "符文2：参数1", "stats PERK1_VAR2": "符文2：参数2", "stats PERK1_VAR3": "符文2：参数3", "stats PERK2": "符文3序号", "stats PERK2_VAR1": "符文3：参数1", "stats PERK2_VAR2": "符文3：参数2", "stats PERK2_VAR3": "符文3：参数3", "stats PERK3": "符文4序号", "stats PERK3_VAR1": "符文4：参数1", "stats PERK3_VAR2": "符文4：参数2", "stats PERK3_VAR3": "符文4：参数3", "stats PERK4": "符文5序号", "stats PERK4_VAR1": "符文5：参数1", "stats PERK4_VAR2": "符文5：参数2", "stats PERK4_VAR3": "符文5：参数3", "stats PERK5": "符文6序号", "stats PERK5_VAR1": "符文6：参数1", "stats PERK5_VAR2": "符文6：参数2", "stats PERK5_VAR3": "符文6：参数3", "stats PHYSICAL_DAMAGE_DEALT_PLAYER": "造成的物理伤害", "stats PHYSICAL_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的物理伤害", "stats PHYSICAL_DAMAGE_TAKEN": "承受的物理伤害", "stats PLAYER_AUGMENT_1": "强化符文1序号", "stats PLAYER_AUGMENT_2": "强化符文2序号", "stats PLAYER_AUGMENT_3": "强化符文3序号", "stats PLAYER_AUGMENT_4": "强化符文4序号", "stats PLAYER_AUGMENT_5": "强化符文5序号", "stats PLAYER_AUGMENT_6": "强化符文6序号", "stats PLAYER_SCORE_0": "玩家得分1", "stats PLAYER_SCORE_1": "玩家得分2", "stats PLAYER_SCORE_2": "玩家得分3", "stats PLAYER_SCORE_3": "玩家得分4", "stats PLAYER_SCORE_4": "玩家得分5", "stats PLAYER_SCORE_5": "玩家得分6", "stats PLAYER_SCORE_6": "玩家得分7", "stats PLAYER_SCORE_7": "玩家得分8", "stats PLAYER_SCORE_8": "玩家得分9", "stats PLAYER_SCORE_9": "玩家得分10", "stats PLAYER_SUBTEAM": "子阵营代号", "stats PLAYER_SUBTEAM_PLACEMENT": "队伍排名", "stats SIGHT_WARDS_BOUGHT_IN_GAME": "购买洞察之石", "stats SPELL1_CAST": "召唤师技能1施放次数", "stats SPELL2_CAST": "召唤师技能2施放次数", "stats TEAM_EARLY_SURRENDERED": "队伍提前投降", "stats TEAM_OBJECTIVE": "团队夺取战略点数量", "stats TIME_CCING_OTHERS": "控制得分", "stats TOTAL_DAMAGE_DEALT": "造成的伤害总和", "stats TOTAL_DAMAGE_DEALT_TO_BUILDINGS": "对建筑物的总伤害", "stats TOTAL_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的伤害总和", "stats TOTAL_DAMAGE_DEALT_TO_OBJECTIVES": "对战略点的总伤害", "stats TOTAL_DAMAGE_DEALT_TO_TURRETS": "对防御塔的总伤害", "stats TOTAL_DAMAGE_SELF_MITIGATED": "自我缓和的伤害", "stats TOTAL_DAMAGE_SHIELDED_ON_TEAMMATES": "友方护盾", "stats TOTAL_DAMAGE_TAKEN": "承受伤害", "stats TOTAL_HEAL": "治疗伤害", "stats TOTAL_HEAL_ON_TEAMMATES": "友方治疗", "stats TOTAL_TIME_CROWD_CONTROL_DEALT": "控制时间", "stats TOTAL_TIME_SPENT_DEAD": "死亡总时间", "stats TRUE_DAMAGE_DEALT_PLAYER": "造成真实伤害", "stats TRUE_DAMAGE_DEALT_TO_CHAMPIONS": "对英雄的真实伤害", "stats TRUE_DAMAGE_TAKEN": "承受的真实伤害", "stats TURRETS_KILLED": "摧毁防御塔", "stats VICTORY_POINT_TOTAL": "总胜利点数", "stats VISION_SCORE": "视野得分", "stats VISION_WARDS_BOUGHT_IN_GAME": "购买控制守卫", "stats WARD_KILLED": "摧毁守卫", "stats WARD_PLACED": "放置守卫", "stats WAS_AFK": "中途退出", "stats WIN": "胜利", "stats KDA": "击杀得分", "stats PERK_PRIMARY_STYLE name": "主系名称", "stats PERK_PRIMARY_STYLE iconPath": "主系图标路径", "stats PERK_SUB_STYLE name": "副系名称", "stats PERK_SUB_STYLE iconPath": "副系图标路径", "stats PERK0 EndOfGameStatDescs": "符文1游戏结算数据", "stats PERK1 EndOfGameStatDescs": "符文2游戏结算数据", "stats PERK2 EndOfGameStatDescs": "符文3游戏结算数据", "stats PERK3 EndOfGameStatDescs": "符文4游戏结算数据", "stats PERK4 EndOfGameStatDescs": "符文5游戏结算数据", "stats PERK5 EndOfGameStatDescs": "符文6游戏结算数据", "stats PERK0 name": "符文1名称", "stats PERK1 name": "符文2名称", "stats PERK2 name": "符文3名称", "stats PERK3 name": "符文4名称", "stats PERK4 name": "符文5名称", "stats PERK5 name": "符文6名称", "stats PERK0 iconPath": "符文1图标路径", "stats PERK1 iconPath": "符文2图标路径", "stats PERK2 iconPath": "符文3图标路径", "stats PERK3 iconPath": "符文4图标路径", "stats PERK4 iconPath": "符文5图标路径", "stats PERK5 iconPath": "符文6图标路径", "stats PLAYER_AUGMENT_1 nameTRA": "强化符文1名称", "stats PLAYER_AUGMENT_2 nameTRA": "强化符文2名称", "stats PLAYER_AUGMENT_3 nameTRA": "强化符文3名称", "stats PLAYER_AUGMENT_4 nameTRA": "强化符文4名称", "stats PLAYER_AUGMENT_5 nameTRA": "强化符文5名称", "stats PLAYER_AUGMENT_6 nameTRA": "强化符文6名称", "stats PLAYER_AUGMENT_1 augmentIconPath": "强化符文1图标路径", "stats PLAYER_AUGMENT_2 augmentIconPath": "强化符文2图标路径", "stats PLAYER_AUGMENT_3 augmentIconPath": "强化符文3图标路径", "stats PLAYER_AUGMENT_4 augmentIconPath": "强化符文4图标路径", "stats PLAYER_AUGMENT_5 augmentIconPath": "强化符文5图标路径", "stats PLAYER_AUGMENT_6 augmentIconPath": "强化符文6图标路径", "stats PLAYER_AUGMENT_1 rarity": "强化符文1等级", "stats PLAYER_AUGMENT_2 rarity": "强化符文2等级", "stats PLAYER_AUGMENT_3 rarity": "强化符文3等级", "stats PLAYER_AUGMENT_4 rarity": "强化符文4等级", "stats PLAYER_AUGMENT_5 rarity": "强化符文5等级", "stats PLAYER_AUGMENT_6 rarity": "强化符文6等级", "stats playerSubteamColor": "子阵营"}
    eog_playerstat_data_lol_header_keys = list(eog_playerstat_data_lol_header.keys())
    eog_stat_metadata_tft_header = {"gameId": "对局序号", "gameLength": "持续时长（秒）", "isRanked": "排位赛", "playerSkillTreeEoG": "对局结算技巧加成", "queueId": "队列序号", "queueType": "队列类型", "gameLength_norm": "持续时长", "gameModeName": "游戏模式名称"}
    eog_stat_metadata_tft_header_keys = list(eog_stat_metadata_tft_header.keys())
    eog_stat_data_tft_header = {"augments": "强化符文", "boardPieces": "备战席", "ffaStanding": "最终排名", "health": "游戏结束时生命值", "iconId": "召唤师图标序号", "isInteractable": "结算界面可交互", "isLocalPlayer": "本人标记", "partnerGroupId": "搭档组号", "puuid": "玩家通用唯一识别码", "rank": "名次", "riotIdGameName": "玩家昵称", "riotIdTagLine": "昵称编号", "setCoreName": "云顶之弈赛季核心名称", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "icon title": "召唤师图标名称", "icon imagePath": "召唤师图标缩略图路径", "augment1 icon": "强化符文1图标", "augment2 icon": "强化符文2图标", "augment3 icon": "强化符文3图标", "augment1 id": "强化符文1序号", "augment2 id": "强化符文2序号", "augment3 id": "强化符文3序号", "augment1 name": "强化符文1名称", "augment2 name": "强化符文2名称", "augment3 name": "强化符文3名称", "augment1 nameId": "强化符文1接口名称", "augment2 nameId": "强化符文2接口名称", "augment3 nameId": "强化符文3接口名称", "unit0 championId": "英雄1：序号", "unit0 icon": "英雄1：图标", "unit0 level": "英雄1：星级", "unit0 name": "英雄1：名称", "unit0 price": "英雄1：卡费", "unit0 traits": "英雄1：所属羁绊", "unit1 championId": "英雄2：序号", "unit1 icon": "英雄2：图标", "unit1 level": "英雄2：星级", "unit1 name": "英雄2：名称", "unit1 price": "英雄2：卡费", "unit1 traits": "英雄2：所属羁绊", "unit2 championId": "英雄3：序号", "unit2 icon": "英雄3：图标", "unit2 level": "英雄3：星级", "unit2 name": "英雄3：名称", "unit2 price": "英雄3：卡费", "unit2 traits": "英雄3：所属羁绊", "unit3 championId": "英雄4：序号", "unit3 icon": "英雄4：图标", "unit3 level": "英雄4：星级", "unit3 name": "英雄4：名称", "unit3 price": "英雄4：卡费", "unit3 traits": "英雄4：所属羁绊", "unit4 championId": "英雄5：序号", "unit4 icon": "英雄5：图标", "unit4 level": "英雄5：星级", "unit4 name": "英雄5：名称", "unit4 price": "英雄5：卡费", "unit4 traits": "英雄5：所属羁绊", "unit5 championId": "英雄6：序号", "unit5 icon": "英雄6：图标", "unit5 level": "英雄6：星级", "unit5 name": "英雄6：名称", "unit5 price": "英雄6：卡费", "unit5 traits": "英雄6：所属羁绊", "unit6 championId": "英雄7：序号", "unit6 icon": "英雄7：图标", "unit6 level": "英雄7：星级", "unit6 name": "英雄7：名称", "unit6 price": "英雄7：卡费", "unit6 traits": "英雄7：所属羁绊", "unit7 championId": "英雄8：序号", "unit7 icon": "英雄8：图标", "unit7 level": "英雄8：星级", "unit7 name": "英雄8：名称", "unit7 price": "英雄8：卡费", "unit7 traits": "英雄8：所属羁绊", "unit8 championId": "英雄9：序号", "unit8 icon": "英雄9：图标", "unit8 level": "英雄9：星级", "unit8 name": "英雄9：名称", "unit8 price": "英雄9：卡费", "unit8 traits": "英雄9：所属羁绊", "unit9 championId": "英雄10：序号", "unit9 icon": "英雄10：图标", "unit9 level": "英雄10：星级", "unit9 name": "英雄10：名称", "unit9 price": "英雄10：卡费", "unit9 traits": "英雄10：所属羁绊", "unit10 championId": "英雄11：序号", "unit10 icon": "英雄11：图标", "unit10 level": "英雄11：星级", "unit10 name": "英雄11：名称", "unit10 price": "英雄11：卡费", "unit10 traits": "英雄11：所属羁绊", "unit0 item0 icon": "英雄1：装备1图标", "unit0 item0 id": "英雄1：装备1序号", "unit0 item0 name": "英雄1：装备1名称", "unit0 item0 nameId": "英雄1：装备1接口名称", "unit0 item1 icon": "英雄1：装备2图标", "unit0 item1 id": "英雄1：装备2序号", "unit0 item1 name": "英雄1：装备2名称", "unit0 item1 nameId": "英雄1：装备2接口名称", "unit0 item2 icon": "英雄1：装备3图标", "unit0 item2 id": "英雄1：装备3序号", "unit0 item2 name": "英雄1：装备3名称", "unit0 item2 nameId": "英雄1：装备3接口名称", "unit1 item0 icon": "英雄2：装备1图标", "unit1 item0 id": "英雄2：装备1序号", "unit1 item0 name": "英雄2：装备1名称", "unit1 item0 nameId": "英雄2：装备1接口名称", "unit1 item1 icon": "英雄2：装备2图标", "unit1 item1 id": "英雄2：装备2序号", "unit1 item1 name": "英雄2：装备2名称", "unit1 item1 nameId": "英雄2：装备2接口名称", "unit1 item2 icon": "英雄2：装备3图标", "unit1 item2 id": "英雄2：装备3序号", "unit1 item2 name": "英雄2：装备3名称", "unit1 item2 nameId": "英雄2：装备3接口名称", "unit2 item0 icon": "英雄3：装备1图标", "unit2 item0 id": "英雄3：装备1序号", "unit2 item0 name": "英雄3：装备1名称", "unit2 item0 nameId": "英雄3：装备1接口名称", "unit2 item1 icon": "英雄3：装备2图标", "unit2 item1 id": "英雄3：装备2序号", "unit2 item1 name": "英雄3：装备2名称", "unit2 item1 nameId": "英雄3：装备2接口名称", "unit2 item2 icon": "英雄3：装备3图标", "unit2 item2 id": "英雄3：装备3序号", "unit2 item2 name": "英雄3：装备3名称", "unit2 item2 nameId": "英雄3：装备3接口名称", "unit3 item0 icon": "英雄4：装备1图标", "unit3 item0 id": "英雄4：装备1序号", "unit3 item0 name": "英雄4：装备1名称", "unit3 item0 nameId": "英雄4：装备1接口名称", "unit3 item1 icon": "英雄4：装备2图标", "unit3 item1 id": "英雄4：装备2序号", "unit3 item1 name": "英雄4：装备2名称", "unit3 item1 nameId": "英雄4：装备2接口名称", "unit3 item2 icon": "英雄4：装备3图标", "unit3 item2 id": "英雄4：装备3序号", "unit3 item2 name": "英雄4：装备3名称", "unit3 item2 nameId": "英雄4：装备3接口名称", "unit4 item0 icon": "英雄5：装备1图标", "unit4 item0 id": "英雄5：装备1序号", "unit4 item0 name": "英雄5：装备1名称", "unit4 item0 nameId": "英雄5：装备1接口名称", "unit4 item1 icon": "英雄5：装备2图标", "unit4 item1 id": "英雄5：装备2序号", "unit4 item1 name": "英雄5：装备2名称", "unit4 item1 nameId": "英雄5：装备2接口名称", "unit4 item2 icon": "英雄5：装备3图标", "unit4 item2 id": "英雄5：装备3序号", "unit4 item2 name": "英雄5：装备3名称", "unit4 item2 nameId": "英雄5：装备3接口名称", "unit5 item0 icon": "英雄6：装备1图标", "unit5 item0 id": "英雄6：装备1序号", "unit5 item0 name": "英雄6：装备1名称", "unit5 item0 nameId": "英雄6：装备1接口名称", "unit5 item1 icon": "英雄6：装备2图标", "unit5 item1 id": "英雄6：装备2序号", "unit5 item1 name": "英雄6：装备2名称", "unit5 item1 nameId": "英雄6：装备2接口名称", "unit5 item2 icon": "英雄6：装备3图标", "unit5 item2 id": "英雄6：装备3序号", "unit5 item2 name": "英雄6：装备3名称", "unit5 item2 nameId": "英雄6：装备3接口名称", "unit6 item0 icon": "英雄7：装备1图标", "unit6 item0 id": "英雄7：装备1序号", "unit6 item0 name": "英雄7：装备1名称", "unit6 item0 nameId": "英雄7：装备1接口名称", "unit6 item1 icon": "英雄7：装备2图标", "unit6 item1 id": "英雄7：装备2序号", "unit6 item1 name": "英雄7：装备2名称", "unit6 item1 nameId": "英雄7：装备2接口名称", "unit6 item2 icon": "英雄7：装备3图标", "unit6 item2 id": "英雄7：装备3序号", "unit6 item2 name": "英雄7：装备3名称", "unit6 item2 nameId": "英雄7：装备3接口名称", "unit7 item0 icon": "英雄8：装备1图标", "unit7 item0 id": "英雄8：装备1序号", "unit7 item0 name": "英雄8：装备1名称", "unit7 item0 nameId": "英雄8：装备1接口名称", "unit7 item1 icon": "英雄8：装备2图标", "unit7 item1 id": "英雄8：装备2序号", "unit7 item1 name": "英雄8：装备2名称", "unit7 item1 nameId": "英雄8：装备2接口名称", "unit7 item2 icon": "英雄8：装备3图标", "unit7 item2 id": "英雄8：装备3序号", "unit7 item2 name": "英雄8：装备3名称", "unit7 item2 nameId": "英雄8：装备3接口名称", "unit8 item0 icon": "英雄9：装备1图标", "unit8 item0 id": "英雄9：装备1序号", "unit8 item0 name": "英雄9：装备1名称", "unit8 item0 nameId": "英雄9：装备1接口名称", "unit8 item1 icon": "英雄9：装备2图标", "unit8 item1 id": "英雄9：装备2序号", "unit8 item1 name": "英雄9：装备2名称", "unit8 item1 nameId": "英雄9：装备2接口名称", "unit8 item2 icon": "英雄9：装备3图标", "unit8 item2 id": "英雄9：装备3序号", "unit8 item2 name": "英雄9：装备3名称", "unit8 item2 nameId": "英雄9：装备3接口名称", "unit9 item0 icon": "英雄10：装备1图标", "unit9 item0 id": "英雄10：装备1序号", "unit9 item0 name": "英雄10：装备1名称", "unit9 item0 nameId": "英雄10：装备1接口名称", "unit9 item1 icon": "英雄10：装备2图标", "unit9 item1 id": "英雄10：装备2序号", "unit9 item1 name": "英雄10：装备2名称", "unit9 item1 nameId": "英雄10：装备2接口名称", "unit9 item2 icon": "英雄10：装备3图标", "unit9 item2 id": "英雄10：装备3序号", "unit9 item2 name": "英雄10：装备3名称", "unit9 item2 nameId": "英雄10：装备3接口名称", "unit10 item0 icon": "英雄11：装备1图标", "unit10 item0 id": "英雄11：装备1序号", "unit10 item0 name": "英雄11：装备1名称", "unit10 item0 nameId": "英雄11：装备1接口名称", "unit10 item1 icon": "英雄11：装备2图标", "unit10 item1 id": "英雄11：装备2序号", "unit10 item1 name": "英雄11：装备2名称", "unit10 item1 nameId": "英雄11：装备2接口名称", "unit10 item2 icon": "英雄11：装备3图标", "unit10 item2 id": "英雄11：装备3序号", "unit10 item2 name": "英雄11：装备3名称", "unit10 item2 nameId": "英雄11：装备3接口名称", "companion colorName": "小小英雄颜色", "companion icon": "小小英雄缩略图路径", "companion speciesName": "小小英雄名称", "customAugmentContainer description": "强化符文供应池描述", "customAugmentContainer displayName": "强化符文供应池显示名", "customAugmentContainer iconPath": "强化符文供应池缩略图路径", "customAugmentContainer nameId": "强化符文供应池接口名称", "playbook iconSmall": "指导手册小图标路径", "playbook itemId": "指导手册序号", "playbook name": "指导手册名称"}
    eog_stat_data_tft_header_keys = list(eog_stat_data_tft_header.keys())

def count_nonASCII(s: str): #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str): #移除一个字符串中的所有C0和C1字符（Remove all C0 and C1 characters from a string）
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc")

def format_df(df: pandas.DataFrame, width_exceed_ask: bool = True, direct_print: bool = False, print_header: bool = True, print_index: bool = False, reserve_index = False, start_index = 0, header_align: str = "^", align: str = "^", align_replicate_rule: str = "all"): #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
    df = df.copy(deep = True)
    old_index = df.index
    df.index = range(start_index, len(df) + start_index)
    maxLens = {}
    maxWidth = shutil.get_terminal_size()[0]
    fields = df.columns.tolist()
    for field in fields:
        maxLens[field] = max(0 if len(df) == 0 else max(map(lambda x: wcswidth(rm_ctrl_char(str(x))), df[field])), wcswidth(rm_ctrl_char(field))) + 2
    index_len = 0 if len(df) == 0 else max(map(lambda x: len(str(x)), old_index)) if reserve_index else max(len(str(start_index)), len(str(start_index + len(df) - 1)))
    if sum(maxLens.values()) + 2 * (len(fields) - 1) > maxWidth or print_index and index_len + sum(maxLens.values()) + 2 * len(fields) > maxWidth:
        if width_exceed_ask:
            print("单行数据字符串输出宽度超过当前终端窗口宽度！是否继续？（输入任意键继续，否则直接打印该数据框。）\nThe output width of each record string exceeds the current width of the terminal window! Continue? (Input anything to continue, or null to directly print this dataframe.)")
            if input() == "":
                #print(df)
                result = str(df)
                return (result, maxLens)
        elif direct_print:
            #print("单行数据字符串输出宽度超过当前终端窗口宽度！将直接打印该数据框！\nThe output width of each record string exceeds the current width of the terminal window! The program is going to directly print this dataframe!")
            result = str(df)
            return (result, maxLens)
        # else:
        #     print("单行数据字符串输出宽度超过当前终端窗口宽度！将继续格式化输出！\nThe output width of each record string exceeds the current width of the terminal window! The program is going on formatted printing!")
    result = ""
    #确定各列的排列方向（Determine the alignments of all columns）
    if isinstance(header_align, str) and isinstance(align, str):
        if not all(map(lambda x: x in {"<", "^", ">"}, header_align)) or not all(map(lambda x: x in {"<", "^", ">"}, align)):
            print('排列方式字符串参数错误！排列方式必须是“<”“^”或者“>”中的一个。请修改排列方式字符串参数。\nParameter ERROR of the alignment string! The alignment value must be one of {"<", "^", ">"}. Please change the alignment string parameter.')
        if len(header_align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            header_alignments = ["^"] * df.shape[1]
        elif len(header_align) == 1:
            header_alignments = [header_align] * df.shape[1]
        else:
            header_alignments_tmp = list(header_align)
            if len(header_align) < df.shape[1]:
                if align_replicate_rule == "last":
                    header_alignments = header_alignments_tmp + [header_alignments_tmp[-1]] * len(df.shape[1] - len(header_align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    header_alignments = header_alignments_tmp * (df.shape[1] // len(header_align)) + header_alignments_tmp[:df.shape[1] % len(header_align)]
            else:
                header_alignments = header_alignments_tmp[:df.shape[1]]
        if len(align) == 0:
            alignments = ["^"] * df.shape[1]
        elif len(align) == 1:
            alignments = [align] * df.shape[1]
        else:
            alignments_tmp = list(align)
            if len(align) < df.shape[1]:
                if align_replicate_rule == "last":
                    alignments = alignments_tmp + [alignments_tmp[-1]] * len(df.shape[1] - len(align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    alignments = alignments_tmp * (df.shape[1] // len(align)) + alignments_tmp[:df.shape[1] % len(align)]
            else:
                alignments = alignments_tmp[:df.shape[1]]
        if print_header:
            if print_index:
                result += " " * (index_len + 2)
            for i in range(df.shape[1]):
                field = fields[i]
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(field), align = header_alignments[i], w = maxLens[field] - count_nonASCII(field))
                result += tmp
                #print(tmp, end = "")
                if i != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            result += "\n"
            #print()
        index = start_index
        for i in range(df.shape[0]):
            if print_index:
                result += "{0:>{w}}".format(old_index[index - start_index] if reserve_index else index, w = index_len) + "  "
            for j in range(df.shape[1]):
                field = fields[j]
                cell = str(list(df[field])[i])
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(cell), align = alignments[j], w = maxLens[field] - count_nonASCII(cell))
                result += tmp
                #print(tmp, end = "")
                if j != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            if i != df.shape[0] - 1:
                result += "\n"
            #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the last line）
            index += 1
    else:
        print("排列方式参数错误！请传入字符串。\nAlignment parameter ERROR! Please pass a string instead.")
    return (result, maxLens)

async def get_info(connection, name: str, searchType: str | int = "riotId"):
    #searchTypes = {0: "selfCheck", 1: "riotId", 2: "puuid", 3: "summonerId"}
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    result = {"searchType": "riotId", "endpoint": "/lol-summoner/v2/summoners/puuid/{puuid}", "info_got": False, "network_error": False, "body": {}, "message": "", "selfInfo": False}
    try:
        name = int(name)
    except ValueError:
        if name == "current-summoner":
            result = {"searchType": "selfCheck", "endpoint": "/lol-summoner/v1/current-summoner", "info_got": True, "network_error": False, "body": current_info, "message": "", "selfInfo": True}
        elif name.count("-") == 4 and len(name.replace(" ", "")) > 22: #拳头规定的玩家昵称不超过16个字符，昵称编号不超过5个字符（Riot game name can't exceed 16 characters. The tagline can't exceed 5 characters）
            result["searchType"] = "puuid"
            result["endpoint"] = "/lol-summoner/v2/summoners/puuid/{puuid}"
            info = await (await connection.request("GET", f"/lol-summoner/v2/summoners/puuid/{name}")).json()
            result["body"] = info
            if "errorCode" in info:
                if info["httpStatus"] == 400:
                    result["message"] = "您输入的玩家通用唯一识别码格式有误！请重新输入！\nPUUID wasn't in UUID format! Please try again!"
                elif info["httpStatus"] == 404:
                    result["message"] = "未找到玩家通用唯一识别码为%s的玩家；请核对识别码并稍后再试。\nA player with puuid %s was not found; verify the puuid and try again." %(name, name)
                else:
                    result["network_error"] = True
                    result["message"] = "网络异常。\nNetwork Error."
            else:
                result["info_got"] = True
                result["selfInfo"] = info["puuid"] == current_info["puuid"]
        else:
            result["searchType"] = "riotId"
            result["endpoint"] = "/lol-summoner/v1/summoners?name={name}"
            if name.count("#") == 0:
                result["message"] = '召唤师名称已变更为拳头ID。请以“{玩家昵称}#{昵称编号}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"])
            elif name.count("#") > 1:
                result["message"] = "该玩家名字包含了无效字符。\nThis player name contains invalid characters."
            else:
                gameName, tagLine = name.split("#")
                if len(gameName) == 0:
                    result["message"] = "缺少玩家昵称。\nGame name is missing."
                elif len(tagLine) == 0:
                    result["message"] = "缺少昵称编号。\nTagline is missing."
                elif len(gameName) < 3:
                    result["message"] = "召唤师昵称过短。\nRiot ID is too short."
                elif len(gameName.replace(" ", "")) > 16:
                    result["message"] = "召唤师昵称过长。\nRiot ID is too long."
                else:
                    info = await (await connection.request("GET", "/lol-summoner/v1/summoners?name=" + quote(name))).json()
                    result["body"] = info
                    if "errorCode" in info:
                        if info["httpStatus"] == 404:
                            result["message"] = "未找到%s；请核对下名字并稍后再试。\n%s was not found; verify the name and try again." %(name, name)
                        else:
                            result["network_error"] = True
                            result["message"] = "网络异常。\nNetwork Error."
                    else:
                        result["info_got"] = True
                        result["selfInfo"] = info["puuid"] == current_info["puuid"]
    else:
        result["searchType"] = "summonerId"
        result["endpoint"] = "/lol-summoner/v1/summoners/{id}"
        info = await (await connection.request("GET", f"/lol-summoner/v1/summoners/{name}")).json()
        result["body"] = info
        if "errorCode" in info:
            if info["httpStatus"] == 400:
                if info["message"] == "Value %d for 'id' of type uint64 is out of range":
                    result["message"] = "您输入的召唤师序号格式有误！请重新输入！\nValue for 'id' of type uint64 is out of range! Please try again!"
                else:
                    result["message"] = "未找到召唤师序号为%s的玩家；请核对召唤师序号并稍后再试。\nA player with summonerId %s was not found; verify the summonerId and try again." %(name, name)
            elif info["httpStatus"] == 404:
                result["message"] = "未找到召唤师序号为%s的玩家；请核对召唤师序号并稍后再试。\nA player with summonerId %s was not found; verify the summonerId and try again." %(name, name)
            else:
                result["network_error"] = True
                result["message"] = "网络异常。\nNetwork Error."
        else:
            result["info_got"] = True
            result["selfInfo"] = info["puuid"] == current_info["puuid"]
    return result

def get_info_name(info: dict, mode = 1) -> str:
    if not isinstance(info, dict) or not all(i in info for i in ["displayName", "gameName", "tagLine"]):
        print("您的召唤师信息格式有误！\nERROR format of summoner information!")
        name = ""
    else:
        if info["displayName"] or info["gameName"]:
            if info["gameName"] and info["tagLine"]:
                name = info["gameName"] + "#" + info["tagLine"]
            elif not info["tagLine"] and info["gameName"]:
                name = info["gameName"]
            else:
                name = info["displayName"]
        else: #新玩家属于这种类型（This case matches new players）
            if mode == 1:
                name = str(info["puuid"])
            elif mode == 2: #仅用于设置召唤师数据保存路径（Designed to set the summoner name directory）
                name = "0. 新玩家\\" + str(info["puuid"])
            elif mode == 3: #仅用于设置召唤师数据保存路径（Designed to set the summoner name directory）
                name = "0. New Player\\" + str(info["puuid"])
    return name

def lcuTimestamp(timestamp): #根据对局时间轴的时间戳返回对局时间（Return the time according to the timestamp in match timeline）
    min = timestamp // 60
    sec = timestamp % 60
    return str(min) + ":" + "{0:0>2}".format(str(sec))

def aInput() -> str: #高级输入模式（Advanced input mode）
    text = ""
    count = 0
    while True:
        try:
            s = input()
        except EOFError: #Jupyter中只输入Ctrl-D会引发报错（A single Ctrl-D character in jupyter will trigger an exception of the input function）
            break
        if count > 0 and not s == chr(4):
            text += "\n"
        count += 1
        if s.endswith(chr(4)): #以Ctrl-D结束
            text += s[:-1]
            break
        else:
            text += s
    return text

async def send_commands(connection):
    method = endpoint = ""
    logPrint('请依次输入方法、统一资源标识符和请求主体（如有），以空格为分隔符：\nPlease enter the method, URI and request body (if needed), split by space:')
    while True:
        request = logInput()
        tmp = request.split()
        if len(tmp) == 2:
            method, endpoint = tmp
            body = None
        elif len(tmp) == 3:
            method, endpoint = tmp[:2]
            logPrint("请求主体（Request body）：")
            while True:
                body_str = logInput()
                if body_str == "":
                    body_str = "None"
                try:
                    body = eval(body_str)
                except:
                    logPrint("请求主体格式错误！\nRequest body format error!")
                else:
                    break
        else:
            break
        if endpoint[0] != "/":
            logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
            continue
        try:
            response = await (await connection.request(method, endpoint, data = body)).json()
        except TypeError:
            logPrint("请求主体格式错误！\nRequest body format error!")
        else:
            logPrint(response)
            with open("temporary data.json", "w", encoding = "utf-8") as fp:
                fp.write(json.dumps(response, indent = 4, ensure_ascii = False))

#-----------------------------------------------------------------------------
# 通用行为（Generic actions）
#-----------------------------------------------------------------------------
def logInput(prompt: str = "", log: _io.TextIOWrapper = log, write_time: bool = True):
    s = input(prompt)
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
            log.write("[%s]%s\n" %(currentTime, prompt + s))
        else:
            log.write(prompt + s + "\n")
    return s

def logPrint(s: str = "", log: _io.TextIOWrapper = log, end: str = "\n", print_time: bool = False, write_time: bool = True):
    currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    if print_time:
        print("[%s]%s" %(currentTime, s), end = end, flush = end == "\r")
    else:
        print(s, end = end, flush = end == "\r")
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            log.write("[%s]%s%s" %(currentTime, str(s), "\n" if end == "\r" else end))
        else:
            log.write("%s%s" %(str(s), "\n" if end == "\r" else end))

async def get_gameflow_phase(connection) -> str: #设计该函数的原因是通过“GET lol-gameflow/v1/gameflow-phase”获得的游戏状态不一定真实，特别是在调用“POST /lol-lobby/v1/lobby/custom/cancel-champ-select”之后（The reason why this function is designed is that the in-game status returned by the API "GET /lol-gameflow/v1/gameflow-phase" may be unreal, especially when "POST /lol-lobby/v1/lobby/custom/cancel-champ-select" is called）
    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase in {"None", "Lobby", "Matchmaking"}:
        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        search_info = await (await connection.request("GET", "/lol-matchmaking/v1/search")).json()
        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        gameflow_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        inLobby = not "errorCode" in lobby_information
        inQueue = not "errorCode" in search_info and search_info["searchState"] == "Searching"
        inChampSelect = not "errorCode" in champ_select_session
        inGame = not "errorCode" in gameflow_session
        if inChampSelect:
            gameflow_phase = "ChampSelect"
        elif inGame:
            gameflow_phase = "Reconnect"
        elif inQueue:
            gameflow_phase = "Matchmaking"
        elif inLobby:
            gameflow_phase = "Lobby"
    return gameflow_phase

async def sort_conversation_metadata(connection) -> pandas.DataFrame:
    conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
    conversation_metadata = {}
    for i in range(len(conversation_header_keys)):
        key = conversation_header_keys[i]
        conversation_metadata[key] = []
    for conversation in conversations:
        for i in range(len(conversation_header_keys)):
            key = conversation_header_keys[i]
            if i == 9:
                conversation_metadata[key].append(conversationTypes[conversation[key]])
            else:
                conversation_metadata[key].append(conversation[key])
    conversation_statistics_output_order = [9, 0, 1, 2]
    conversation_metadata_organized = {}
    for i in conversation_statistics_output_order:
        key = conversation_header_keys[i]
        conversation_metadata_organized[key] = conversation_metadata[key]
    conversation_df = pandas.DataFrame(data = conversation_metadata_organized)
    conversation_df = pandas.concat([pandas.DataFrame([conversation_header])[conversation_df.columns], conversation_df], ignore_index = True)
    return conversation_df

async def handle_invitations(connection):
    receivedInvitations = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
    if len(receivedInvitations) == 0:
        logPrint("您还没有收到邀请。\nYou've not received any invitation.")
    else:
        logPrint("您收到的邀请信息如下：\nYour received invitations:")
        invid_df = await sort_received_invitations(connection)
        invid_fields_to_print = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
        print(format_df(invid_df.loc[:, invid_fields_to_print], print_index = True)[0])
        log.write(format_df(invid_df.loc[:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
        logPrint("请选择一个邀请以接受：\nPlease select an invitation to accept:")
        while True:
            invid_index = logInput()
            if invid_index == "":
                continue
            elif invid_index == "0":
                break
            elif invid_index in list(map(str, range(1, len(invid_df)))):
                invid_index = int(invid_index)
                invitationId = invid_df.loc[invid_index, "invitationId"]
                invid_owner = invid_df.loc[int(invid_index), "fromSummonerName"]
                response = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/accept")).json()
                logPrint(response)
                if isinstance(response, dict) and "errorCode" in response:
                    if response["httpStatus"] == 400:
                        if response["message"] == "PARTY_SIZE_LIMIT":
                            logPrint("你试图加入的小队已经满员。\nThe open party you attempted to join is full.")
                        elif response["message"] == "INVALID_ROLE_TRANSITION":
                            logPrint("你已被移出小队。你必须收到邀请才能重新加入。\nYou have been removed from the party. You must receive an invite to rejoin.")
                        elif response["message"] == "INVALID_WHILE_PARTY_IN_ACTION":
                            logPrint("你无法加入该小队，因为该小队正在队列中。\nYou were not able to join the party because the party is now in queue.")
                        else:
                            logPrint("你无法加入该小队。\nYou were not able to join the party.")
                    elif response["httpStatus"] == 404 and response["message"] == "INVITATION_NOT_FOUND":
                        logPrint("邀请已过期。\nInvite expired.")
                    else:
                        logPrint("你无法加入该小队。\nYou were not able to join the party.")
                else:
                    logPrint("您接受了%s的邀请。\nYou accepted the invitation of %s." %(invid_owner, invid_owner))
                    break
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")

async def join_game(connection):
    logPrint("您想要加入小队还是自定义房间？\nWhich kind do you want to join, party or lobby?\n1\t小队（Party）\n2\t自定义房间（Custom lobby）\n3\t冠军杯赛（Clash）")
    while True:
        suboption = logInput()
        if suboption == "":
            continue
        elif suboption[0] == "0":
            break
        elif suboption[0] == "1":
            logPrint("请输入小队序号：\nPlease input the partyId:")
            while True:
                partyId = logInput()
                if partyId == "":
                    continue
                elif partyId == "0":
                    break
                else:
                    response = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        if response["httpStatus"] == 400:
                            if response["message"] == "PARTY_SIZE_LIMIT":
                                logPrint("你试图加入的小队已经满员。\nThe open party you attempted to join is full.")
                            elif response["message"] == "INVALID_ROLE_TRANSITION":
                                logPrint("你已被移出小队。你必须收到邀请才能重新加入。\nYou have been removed from the party. You must receive an invite to rejoin.")
                            elif response["message"] == "INVALID_WHILE_PARTY_IN_ACTION":
                                logPrint("你无法加入该小队，因为该小队正在队列中。\nYou were not able to join the party because the party is now in queue.")
                            else:
                                logPrint("你无法加入该小队。\nYou were not able to join the party.")
                        else:
                            logPrint("你无法加入该小队。\nYou were not able to join the party.")
                    else:
                        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                        if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                            logPrint("加入失败。\nJoin failed.")
                        else:
                            logPrint("您成功加入该小队！\nYou successfully joined this party.")
                            break
                logPrint("请输入小队序号：\nPlease input the partyId:")
        elif suboption[0] == "2":
            custom_lobby_df = await sort_custom_lobbies(connection)
            custom_lobby_df_fields_to_print = ["id", "lobbyName", "ownerDisplayName", "mapId", "mapName", "hasPassword", "spectatorPolicy", "filledPlayerRatio", "filledSpectatorRatio"]
            if len(custom_lobby_df) == 1:
                logPrint("当前无自定义房间。\nThere's not any custom lobby for now.")
            else:
                logPrint("该大区的所有自定义房间如下：\nAll custom lobbies on this server are as follows:")
                print(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], print_index = True)[0])
                log.write(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                logPrint("请选择一个房间：\nPlease select a lobby:")
                while True:
                    lobby_index = logInput()
                    if lobby_index == "":
                        continue
                    elif lobby_index == "0":
                        break
                    elif lobby_index in list(map(str, range(1, len(custom_lobby_df)))):
                        lobby_index = int(lobby_index)
                        lobbyId = custom_lobby_df.loc[lobby_index, "id"]
                        lobbyOwnerName = custom_lobby_df.loc[lobby_index, "ownerDisplayName"]
                        if custom_lobby_df.loc[lobby_index, "hasPassword"] == "√":
                            logPrint("请输入密码。\nPlease input the password.")
                            lobbyPassword = logInput()
                        else:
                            lobbyPassword = ""
                        logPrint("输入任意键以观战，否则不观战。\nSubmit any non-empty string to spectate, or null to refuse spectating.")
                        asSpectator_str = logInput()
                        asSpectator = bool(asSpectator_str)
                        body = {"asSpectator": asSpectator} if lobbyPassword == "" else {"password": lobbyPassword, "asSpectator": asSpectator}
                        response = await (await connection.request("POST", f"/lol-lobby/v1/custom-games/{lobbyId}/join", data = body)).json()
                        logPrint(response)
                        if isinstance(response, dict) and "errorCode" in response:
                            if response["httpStatus"] == 500 and response["message"] == "Error response for POST /lol-login/v1/session/invoke: LCDS invoke to gameService.observeGameV4 failed: Server.Processing, com.riotgames.platform.game.GameObserverModeNotEnabledException : null":
                                logPrint("该自定义房间不允许观战。\nThis custom lobby doesn't allow spectating.")
                            elif response["httpStatus"] == 403 and response["message"] == "Error response for POST /lol-login/v1/session/invoke: LCDS invoke to gameService.joinGameV4 failed: Server.Processing, com.riotgames.platform.game.IncorrectPasswordException : null":
                                logPrint("验证失败。如果该房间设置了密码，请检查密码是否有误。\nVerification failed. If this lobby has password, please check if the password is correct.")
                            else:
                                logPrint(f"您未能加入{lobbyOwnerName}的自定义房间。\nYou failed to join {lobbyOwnerName}'s custom lobby.")
                        else:
                            logPrint("您加入了该房间。\nYou've entered this lobby.")
                            break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    custom_lobby_df = await sort_custom_lobbies(connection)
                    logPrint("请选择一个房间：\nPlease select a lobby:")
                    print(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], print_index = True)[0])
                    log.write(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
        elif suboption[0] == "3":
            logPrint("请输入冠军杯赛代码：\nPlease enter the tournament code:")
            while True:
                tournament_code = logInput()
                if tournament_code == "":
                    continue
                elif tournament_code == "0":
                    break
                else:
                    response = await (await connection.request("POST", f"/lol-lobby/v1/tournaments/{tournament_code}/join")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        if response["message"] == "Failed to join tournament game":
                            logPrint("加入失败。\nFailed to join.")
                        else:
                            logPrint("加入失败。\nFailed to join.")
                    else:
                        logPrint("加入成功。\nSuccessfully joined.")
                        break
                logPrint("请输入冠军杯赛代码：\nPlease enter the tournament code:")
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            continue
        logPrint("您想要加入小队还是自定义房间？\nWhich kind do you want to join, party or lobby?\n1\t小队（Party）\n2\t自定义房间（Custom lobby）\n3\t冠军杯赛（Clash）")

async def manage_ux(connection):
    logPrint("请选择您想要对英雄联盟客户端执行的操作：\nPlease select an operation you want to do with LeagueClientUx.exe:\n1\t窗口管理（Window management）\n2\t进程管理（Process management）")
    while True:
        option = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('''请选择一个拳头客户端相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a riot client-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t删除英雄联盟客户端的CPU亲和性配置（Deletes the current runtime affinity of the application）\n2\t查看英雄联盟客户端的CPU亲和性配置（Get the current runtime affinity of the application）\n3\t设置英雄联盟客户端的CPU亲和性（Sets the current runtime affinity of the application）\n4\t获取应用名称（Get the application name without file extension）\n5\t查看应用程序端口（Get the TCP port number that the remoting server is listening on）\n6\t查看英雄联盟客户端认证令牌（Return the auth token used by the remoting server）\n7\t查看可用于英雄联盟对话的剪贴板（Check the clipboard which applies in conversations in League of Legends）\n8\t复制一段文字（Copy a string）\n9\t查看英雄联盟进程的命令行变量（Get the command line parameters for the application）\n10\t重新启动用户体验进程（Kill the ux process and restarts it. Used only when the ux process crashes）\n!11\t关闭英雄联盟用户体验界面（Kill the ux process）\n12\t启动英雄联盟用户体验界面（Launch the ux process）\n13\t查看机器码（Get base64 encoded uuid identifying the user's machine）\n14\t设置新的命令行变量（Set a new endpoint for passing in new data）\n15\t在浏览器中处理用户体验界面请求（Opens a URL in the player's system browser）\n16\t查看当前地区和语言设置（Check the current region and language）\n17\t在浏览器中打开LCU API的Swagger格式化说明文档（Open swagger in the default browser）\n18\t隐藏启动时的闪屏界面（Hide the splash screen when starting）\n19\t显示启动时的闪屏界面（Show the splash screen when starting）\n20\t查看当前操作系统信息（Get basic system information: OS, memory, processor speed, and number of physical cores）\n21\t追踪客户端运行情况（Retrieve a completed scheduler trace）\n!22\t注销当前登录用户（Unload the UX process）\n23\t一次性将当前英雄联盟客户端窗口置顶（Allow the background process to launch the game into the foregound）\n24\t检查用户体验进程是否崩溃（Returns whether the ux has crashed or not）\n25\t使英雄联盟客户端的任务栏图标闪烁（Flash the ux process' main window and the taskbar/dock icon, if they exist）\n26\t设置英雄联盟用户体验界面加载为已完成（Send a ux notification that it has completed loading the main window.）\n27\t最小化英雄联盟客户端窗口（Minimize the ux process and all its windows if it exists. This does not kill the ux）\n28\t呈现英雄联盟客户端窗口（Shows the ux process if it exists; create and show if it does not）\n29\t查看用户体验界面状态（Get the current Ux state）\n30\t确认用户体验界面状态更新（Acknowledges the update to the Ux state）\n31\t注销当前认证令牌（Unregister an existing auth token）\n32\t设置一个认证令牌（Register an auth token. This is any alpha-numeric string that will be used as a password with the riot user when making requests）\n33\t查看崩溃报告的标识信息（Get the crash reporting environment identifier）\n34\t设置崩溃报告环境（Tag the crash with an environment so it can be filtered more easily）\n35\t添加崩溃日志信息（Add the enclosed log to the app's crash report）\n36\t启用故障修复（Enable crash repair）\n37\t查看英雄联盟客户端的窗口尺寸（Get the last known posted zoom-scale value）\n38\t设置英雄联盟客户端的窗口尺寸（Handle changing the zoom scale value）\n39\t查看当前用户体验进程状态（Return information about the process-control）\n!40\t结束英雄联盟客户端进程（Quit the application）''')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection)
                elif suboption == "0":
                    break
                elif suboption in list(map(str, range(1, 40))):
                    if suboption == "1":
                        response = await (await connection.request("DELETE", "/riotclient/affinity")).json()
                    elif suboption == "2":
                        response = await (await connection.request("GET", "/riotclient/affinity")).json()
                    elif suboption == "3":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"string"\nnewAffinity = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/riotclient/affinity", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "4":
                        response = await (await connection.request("GET", "/riotclient/app-name")).json()
                    elif suboption == "5":
                        response = await (await connection.request("GET", "/riotclient/app-port")).json()
                    elif suboption == "6":
                        response = await (await connection.request("GET", "/riotclient/auth-token")).json()
                    elif suboption == "7":
                        response = await (await connection.request("GET", "/riotclient/clipboard")).json()
                    elif suboption == "8":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"string"\nwriteString = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/riotclient/clipboard", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "9":
                        response = await (await connection.request("GET", "/riotclient/command-line-args")).json()
                    elif suboption == "10":
                        response = await (await connection.request("POST", "/riotclient/kill-and-restart-ux")).json()
                    elif suboption == "11":
                        response = await (await connection.request("POST", "/riotclient/kill-ux")).json()
                    elif suboption == "12":
                        response = await (await connection.request("POST", "/riotclient/launch-ux")).json()
                    elif suboption == "13":
                        response = await (await connection.request("GET", "/riotclient/machine-id")).json()
                    elif suboption == "14":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n["string"]\nargs = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/riotclient/new-args", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "15":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"string"\nurl = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/riotclient/open-url-in-browser", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "16":
                        response = await (await connection.request("GET", "/riotclient/region-locale")).json()
                    elif suboption == "17":
                        response = await (await connection.request("POST", "/riotclient/show-swagger")).json()
                    elif suboption == "18":
                        response = await (await connection.request("DELETE", "/riotclient/splash")).json()
                    elif suboption == "19":
                        logPrint('请输入一个插画字符串：\nPlease input a splash string:\nsplash = ', end = "")
                        splash = logInput()
                        response = await (await connection.request("POST", f"/riotclient/splash?splash={splash}")).json()
                    elif suboption == "20":
                        response = await (await connection.request("GET", "/riotclient/system-info/v1/basic-info")).json()
                    elif suboption == "21":
                        response = await (await connection.request("GET", "/riotclient/trace")).json()
                    elif suboption == "22":
                        response = await (await connection.request("POST", "/riotclient/unload")).json()
                    elif suboption == "23":
                        response = await (await connection.request("POST", "/riotclient/ux-allow-foreground")).json()
                    elif suboption == "24":
                        response = await (await connection.request("GET", "/riotclient/ux-crash-count")).json()
                    elif suboption == "25":
                        response = await (await connection.request("POST", "/riotclient/ux-flash")).json()
                    elif suboption == "26":
                        response = await (await connection.request("PUT", "/riotclient/ux-load-complete")).json()
                    elif suboption == "27":
                        response = await (await connection.request("POST", "/riotclient/ux-minimize")).json()
                    elif suboption == "28":
                        response = await (await connection.request("POST", "/riotclient/ux-show")).json()
                    elif suboption == "29":
                        response = await (await connection.request("GET", "/riotclient/ux-state")).json()
                    elif suboption == "30":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n0\nrequestId = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("PUT", "/riotclient/ux-state/ack", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "31":
                        logPrint("请输入当前认证令牌：\nPlease input the current auth token:\nauthToken = ", end = "")
                        authToken = logInput()
                        response = await (await connection.request("DELETE", f"/riotclient/v1/auth-tokens/{authToken}")).json()
                    elif suboption == "32":
                        logPrint("请输入一个认证令牌：\nPlease input an auth token:\nauthToken = ", end = "")
                        authToken = logInput()
                        response = await (await connection.request("DELETE", f"/riotclient/v1/auth-tokens/{authToken}")).json()
                    elif suboption == "33":
                        response = await (await connection.request("GET", "/riotclient/v1/crash-reporting/environment")).json()
                    elif suboption == "34":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"environment": "string", "userName": "string", "userId": "string"}\nenvironment = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("PUT", "/riotclient/v1/crash-reporting/environment", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "35":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"string"\nlogFilePath = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/riotclient/v1/crash-reporting/logs", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "36":
                        body = {"action": "FixBrokenPermissions"}
                        response = await (await connection.request("POST", "/riotclient/v1/elevation-requests", data = body)).json()
                    elif suboption == "37":
                        response = await (await connection.request("GET", "/riotclient/zoom-scale")).json()
                    elif suboption == "38":
                        logPrint("请输入新的窗口尺寸：\nPlease input a new zoom scale:\nnewZoomScale = ", end = "")
                        newZoomScale = logInput()
                        response = await (await connection.request("POST", "/riotclient/zoom-scale?newZoomScale={newZoomScale}")).json()
                    else:
                        response = await (await connection.request("GET", "/process-control/v1/process")).json()
                    logPrint(response)
                elif suboption == "40":
                    quit_str = logPrint(QUIT_UX_WARNING)
                    quit = quit_str == "quit"
                    if quit:
                        response = await (await connection.request("POST", "/process-control/v1/process/quit")).json()
                        logPrint(response)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option[0] == "0":
            break
        elif option[0] == "1":
            logPrint("请选择一个操作：\nPlease select an action on the window:\n1\t显示窗口（Show the window）\n2\t最小化窗口（Minimize the window）\n3\t显示高亮通知（Enable taskbar flashing）\n4\t设置窗口尺寸（Resize the window）")
            while True:
                action = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    response = await (await connection.request("POST", "/riotclient/ux-show")).json()
                    logPrint(response)
                elif action[0] == "2":
                    response = await (await connection.request("POST", "/riotclient/ux-minimize")).json()
                    logPrint(response)
                elif action[0] == "3":
                    response = await (await connection.request("POST", "/riotclient/ux-flash")).json()
                    logPrint(response)
                elif action[0] == "4":
                    logPrint("请选择一个窗口尺寸：\nPlease select a window size:\n1\t0.8\t1024 × 576\n2\t1\t1280 × 720\n3\t1.25\t1600 × 900\n4\t1.5\t1920 × 1080\n5\t自定义（Customize）")
                    current_zoomScale = await (await connection.request("GET", "/riotclient/zoom-scale")).json()
                    if isinstance(current_zoomScale, float):
                        current_window_size = zoom_scale_dict.get(current_zoomScale, "")
                        print(f"当前窗口尺寸：\t{current_window_size}")
                    while True:
                        zoomScale_got = False
                        scale_option = logInput()
                        if scale_option == "":
                            continue
                        elif scale_option[0] == "0":
                            zoomScale_got = False
                            break
                        elif scale_option[0] in list(map(str, range(1, 5))):
                            update_zoomScale = list(zoom_scale_dict.keys())[int(scale_option[0]) - 1]
                            zoomScale_got = True
                            break
                        elif scale_option[0] == "5":
                            logPrint("提示：您可以在客户端内按Ctrl和上下方向键以切换窗口尺寸。\nHint: You can press Ctrl + ↑/↓ to toggle the client window size.")
                            logPrint("请输入窗口尺寸比例：\nPlease input a window size:")
                            while True:
                                update_zoomScale_str = logInput()
                                if update_zoomScale_str == "":
                                    continue
                                elif update_zoomScale_str == "0":
                                    zoomScale_got = False
                                    break
                                else:
                                    try:
                                        update_zoomScale = eval(update_zoomScale_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入格式有误！请重新输入。\nERROR format! Please try again.")
                                    else:
                                        zoomScale_got = True
                                        break
                            if zoomScale_got:
                                break
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            continue
                        logPrint("请选择一个窗口尺寸：\nPlease select a window size:\n1\t0.8\t1024 × 576\n2\t1\t1280 × 720\n3\t1.25\t1600 × 900\n4\t1.5\t1920 × 1080\n5\t自定义（Customize）")
                    if zoomScale_got:
                        time.sleep(GLOBAL_RESPONSE_LAG)
                        response = await (await connection.request("POST", f"/riotclient/zoom-scale?newZoomScale={update_zoomScale}")).json()
                        logPrint(response)
                        if isinstance(response, dict) and "errorCode" in response:
                            logPrint("未知错误。\nUnknown error.")
                        else:
                            new_zoomScale = await (await connection.request("GET", "/riotclient/zoom-scale")).json()
                            if isinstance(current_zoomScale, float) and isinstance(new_zoomScale, float):
                                if current_zoomScale == new_zoomScale:
                                    logPrint("窗口尺寸修改成功。\nWindow resized successfully.")
                                else:
                                    logPrint("窗口尺寸未能按照您给定的比例修改。已设置为某个可用值。\nWindow failed to be resized according to the provided value. Another available value is taken instead.")
                            else:
                                logPrint("发送请求成功。\nRequest success.")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("请选择一个操作：\nPlease select an action on the window:\n1\t显示窗口（Show the window）\n2\t最小化窗口（Minimize the window）\n3\t显示高亮通知（Enable taskbar flashing）\n4\t设置窗口尺寸（Resize the window）")
        elif option[0] == "2":
            logPrint("请选择一个操作：\nPlease select an option on the process:\n1\t启动用户体验界面（Launch ux）\n2\t暂时关闭窗口（Temporarily close ux）\n3\t重新加载窗口（Reload ux）\n!4\t结束进程（Terminate ux）")
            while True:
                action = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    response = await (await connection.request("POST", "/riotclient/launch-ux")).json()
                    logPrint(response)
                elif action[0] == "2":
                    response = await (await connection.request("POST", "/riotclient/kill-ux")).json()
                    logPrint(response)
                    if not (isinstance(response, dict) and "errorCode" in response):
                        logPrint("已发送关闭窗口的请求。请勿退出本程序，否则后续将无法再对当前的客户端会话进行操作。\nA request to kill the ux has been sent. Please don't exit this program, otherwise you won't be able to perform any operations on the current League Client session.")
                elif action[0] == "3":
                    response = await (await connection.request("POST", "/riotclient/kill-and-restart-ux")).json()
                    logPrint(response)
                elif action[0] == "4":
                    logPrint(QUIT_UX_WARNING)
                    quit_str = logInput()
                    quit = quit_str == "quit"
                    if quit:
                        response = await (await connection.request("POST", "/process-control/v1/process/quit")).json()
                        logPrint(response)
                        if isinstance(response, dict) and "errorCode" in response:
                            logPrint("退出英雄联盟客户端失败。\nExit failed.")
                        else:
                            logPrint("已发送退出英雄联盟客户端的请求。\nA request to exit the League Client has been posted.")
                            break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("请选择一个操作：\nPlease select an option on the process:\n1\t启动用户体验界面（Launch ux）\n2\t暂时关闭窗口（Temporarily close ux）\n3\t重新加载窗口（Reload ux）\n!4\t结束进程（Terminate ux）")
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            continue
        logPrint("请选择您想要对英雄联盟客户端执行的操作：\nPlease select an operation you want to do with LeagueClientUx.exe:\n1\t窗口管理（Window management）\n2\t进程管理（Process management）")

async def chat(connection):
    global message_hint_printed
    if not message_hint_printed:
        logPrint("（提示：编辑好内容后，在终端中按Ctrl-D以插入结束字符，再按回车键发送消息。插入两个Ctrl-D以取消对话。插入三个Ctrl-D以刷新消息。如果终端不支持插入Ctrl-D字符，新建一个Python工作台，引入pyperclip库后使用pyperclip.copy(chr(4))以复制Ctrl-D实际代表的字符，再粘贴在聊天终端中，按回车键发送消息。）\n(Hint: If you finished editing the message, you must press Ctrl-D to insert the ending character and then press Enter to send the message. Append double Ctrl-D to cancel chatting. Append triple Ctrl-D to refresh messages. If the current terminal doesn't support inserting Ctrl-D character, please create a Python console, import pyperclip library and then use `pyperclip.copy(chr(4))` to copy the character that Ctrl-D actually represents. Finally, paste it into the current terminal and press Enter to send the message.)")
        message_hint_printed = True
    while True:
        back = False
        conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
        if len(conversations) != 0:
            logPrint("请选择对话：\nPlease select a conversation:")
            conversation_df = await sort_conversation_metadata(connection)
            print(format_df(conversation_df, print_index = True)[0])
            log.write(format_df(conversation_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
            while True:
                conversation_index = logInput()
                if conversation_index == "":
                    continue
                elif conversation_index == "0":
                    back = True
                    break
                elif conversation_index in list(map(str, range(1, len(conversation_df)))):
                    conversation_index = int(conversation_index)
                    chatId = conversation_df.loc[conversation_index, "id"]
                    messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                    if "errorCode" in messages and messages["httpStatus"] == 404:
                        logPrint("该对话尚未激活。请在客户端右边的好友列表中点击该好友，或者直接发送一条聊天类消息，以激活对话。\nThis conversation hasn't been activated yet. Please click this friend in the friend list at the right side of the client, or send a chat message directly to activate the conversation.")
                    mTypeDict = {"1": "chat", "2": "groupchat", "3": "system", "4": "information", "5": "celebration"}
                    logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                    while True:
                        mType = logInput()
                        if mType == "":
                            continue
                        elif mType[0] == "0":
                            break
                        elif mType[0] in mTypeDict:
                            messageType = mTypeDict[mType[0]]
                        elif mType[0] == "6":
                            logPrint("请输入您要发送的消息类型：\nPlease input the type of the message you want to send:")
                            while True:
                                messageType = logInput()
                                if messageType != "":
                                    break
                        else:
                            messageType = "chat"
                        while True:
                            messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                            #先输出聊天记录（First output the chat history）
                            if not "errorCode" in messages:
                                logPrint("聊天记录（Chat history）：\n")
                                for message in messages:
                                    timestamp = message["timestamp"][:10] + " " + message["timestamp"][11:23]
                                    fromInfo = await get_info(connection, message["fromSummonerId"])
                                    from_summonerName = get_info_name(fromInfo["body"]) if fromInfo["info_got"] else ""
                                    if message["type"] == "chat" or message["type"] == "groupchat":
                                        logPrint("[%s]%s：\n%s\n" %(timestamp, from_summonerName, message["body"]))
                                    elif message["type"] == "system":
                                        system_messages = {"connecting": "正在连接……", "disconnected": "您已从聊天服务器断开，正在尝试重新连接……", "dropped_message": "由于发言内容或账号环境存在异常，消息发送暂时被限制，请注意账号保护并24小时后再试。", "is_blocked": "{actor}正在你的聊天黑名单中。你将不会看到它们的聊天信息。".format(actor = from_summonerName), "joined_room": "{actor}加入了队伍聊天".format(actor = from_summonerName), "left_room": "{actor}离开了队伍聊天".format(actor = from_summonerName), "no_friends": "看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。", "no_online_friends": "一个小伙伴都没在线。你知道吗，你是可以给离线的玩家发送信息的哟~", "rich_content_replaced": "请查看《英雄联盟》移动端APP里的消息", "TEXT_CHAT_MUTED": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_RESTRICTION": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_MUTED_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。", "TEXT_CHAT_RESTRICTION_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。"}
                                        logPrint("[%s]%s\n" %(timestamp, system_messages.get(message["body"], message["body"])))
                                    else:
                                        logPrint("[%s](%s)%s\n" %(timestamp, messageTypes.get(message["type"], message["type"]), message["body"]))
                            logPrint("▶ ", end = "")
                            text = aInput()
                            log.write(text + "\n")
                            if text.endswith(chr(4) * 2):
                                continue
                            elif text == "" or text.endswith(chr(4)):
                                logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                                break
                            else:
                                body = {"type": messageType, "body": text}
                                response = await (await connection.request("POST", f"/lol-chat/v1/conversations/{chatId}/messages", data = body)).json()
                                logPrint(response)
                                if "errorCode" in response:
                                    if response["httpStatus"] == 404:
                                        logPrint("聊天服务响应失败！请先激活对话。\nERROR response for chat service! Please activate this conversation first.")
                                    else:
                                        logPrint("聊天服务响应失败！\nERROR response for chat service!")
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        else:
            logPrint("未检测到激活的对话。\nNo active conversation detected.")
            back = True
        if back:
            break

async def toggle_nonfriend_game_invite(connection):
    lol_notifications = await (await connection.request("GET", "/lol-settings/v2/account/LCUPreferences/lol-notifications")).json()
    nonfriend_invitation_blocked = isinstance(lol_notifications, dict) and "blockNonFriendGameInvites" in lol_notifications["data"] and lol_notifications["data"]["blockNonFriendGameInvites"]
    if nonfriend_invitation_blocked:
        logPrint('''您已勾选“只接受好友邀请”选项。是否取消该选项以接受所有人邀请？（输入任意键以修改设置，否则保持原设置。）\nYou've checked the "Allow game invites only from friends" option. Do you want to uncheck this, so that you'll receive any other's invitation? (Submit any non-empty string to change the setting, or null to reserve it.)''')
    else:
        logPrint('''您未勾选“只接受好友邀请”选项。是否勾选该选项以只接受好友邀请？（输入任意键以修改设置，否则保持原设置。）\nYou've unchecked the "Allow game invites only from friends" option. Do you want to check this, so that you'll receive only your friends' invitation? (Submit any non-empty string to change the setting, or null to reserve it.)''')
    settings_change_str = logInput()
    settings_change = bool(settings_change_str)
    if settings_change:
        body = {"data": {"blockNonFriendGameInvites": not nonfriend_invitation_blocked}, "schemaVersion": lol_notifications["schemaVersion"]} #注意：schemaVersion一旦增加就不可减少（Warning: Once schemaVersion increases, it can't be decreased）
        response = await (await connection.request("PATCH", "/lol-settings/v2/account/LCUPreferences/lol-notifications", data = body)).json()
        logPrint(response)
        if nonfriend_invitation_blocked:
            logPrint('已禁用“只接受好友游戏邀请”选项。您现在应当能够收到来自陌生人的游戏邀请了。\nDisabled "Allow game invites only from friends" option. You should be able to receive an invitation from a stranger.')
        else:
            logPrint('''已启用“只接受好友游戏邀请”选项。您将屏蔽所有来自陌生人的游戏邀请。\nEnabled "Allow game invites only from friends" option. You'll block any invitation from strangers.''')

async def expand_match_history(connection):
    global expand_matchHistory_hint_printed
    if not expand_matchHistory_hint_printed:
        logPrint("请确保您从未点击过要查询的玩家的对局记录。如果您已经点击过，则程序只能获取到目前客户端接收到的对局，请等待该信息过期后再重新使用此功能。\nPlease make sure you haven't clicked the MATCH HISTORY tab of the summoner you want to search for. If you happen to have clicked it, then the program can only get the matches already received, and you need to wait for that information to expire and then use this function.\n")
        expand_matchHistory_hint_printed = True
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    logPrint('请输入要查询的召唤师名称，退出请输入“0”：\nPlease input the summoner name to be searched. Submit "0" to exit.')
    while True:
        summoner_name = logInput()
        if summoner_name == "":
            continue
        elif summoner_name == "0":
            break
        elif summoner_name == "current-summoner":
            info = {"searchType": "current-summoner", "endpoint": "/lol-summoner/v1/current-summoner", "info_got": True, "network_error": False, "body": current_info.copy(), "message": "", "selfInfo": True}
        else:
            info = await get_info(connection, summoner_name)
        if info["info_got"]:
            info_body = info["body"]
            displayName = get_info_name(info_body)
            current_puuid = info_body["puuid"]
            logPrint("开始获取英雄联盟对局记录。\nBegin to get the LoL match history.")
            LoLHistory_get = False
            while True:
                LoLHistory = await (await connection.request("GET", f"/lol-match-history/v1/products/lol/{current_puuid}/matches?begIndex=0&endIndex=500")).json()
                count = 0
                if "errorCode" in LoLHistory:
                    logPrint(LoLHistory)
                    if "500 Internal Server Error" in LoLHistory["message"]:
                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                        while "errorCode" in LoLHistory and "500 Internal Server Error" in LoLHistory["message"] and count <= 3:
                            logPrint("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                            LoLHistory = await (await connection.request("GET", f"/lol-match-history/v1/products/lol/{current_puuid}/matches?begIndex=0&endIndex=500")).json()
                    elif "body was empty" in LoLHistory["message"]:
                        logPrint("这位召唤师从5月1日起就没有进行过任何英雄联盟对局。\nThis summoner hasn't played any LoL game yet since May 1st.")
                        break
                    elif "Error getting match list for summoner" in LoLHistory["message"]:
                        LoLHistory_url = "%s/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=200" %(connection.address, info_body["puuid"])
                        logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续（Please open the following website, type in the username and password accordingly and press Enter to continue）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和上限。\nOr submit two nonnegative integers split by space to respecify the begIndex and endIndex." %(LoLHistory_url, connection.auth_key))
                        cont = logInput()
                        if cont == "":
                            continue
                        else:
                            try:
                                begIndex_get, endIndex_get = map(int, cont.split())
                            except:
                                break
                            else:
                                continue
                else:
                    LoLHistory_get = True
                    break
            if LoLHistory_get:
                gameCount = LoLHistory["games"]["gameCount"]
                if gameCount <= 20:
                    logPrint(f"程序只获取到{displayName}的{gameCount}场英雄联盟对局。这可能是因为您之前点击过该玩家的对局记录页签，或者该玩家近期只进行过少于20场英雄联盟对局。\nThe program only gets {displayName}'s {gameCount} LoL match(es). Maybe this is because you clicked this summoner's MATCH HISTORY tab before, or this player has played fewer than 20 LoL matches.")
                else:
                    logPrint(f"已经将{displayName}的英雄联盟对局记录扩展到{gameCount}场对局。请点击该玩家的对局记录页签查看。\nExpanded {displayName}'s LoL match history to {gameCount} matches. Please click this summoner's MATCH HISTORY tab to check it out.")
            else:
                logPrint("{displayName}的英雄联盟对局记录获取失败。\nThe program failed to get {displayName}'s LoL match history.")
            logPrint("开始获取云顶之弈对局记录。\nBegin to get the TFT match history.")
            TFTHistory_get = False
            while True:
                TFTHistory = await (await connection.request("GET", f"/lol-match-history/v1/products/tft/{current_puuid}/matches?begin=0&count=500")).json()
                count = 0
                if "errorCode" in TFTHistory:
                    logPrint(TFTHistory)
                    if "500 Internal Server Error" in TFTHistory["message"]:
                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                        while "errorCode" in TFTHistory and "500 Internal Server Error" in TFTHistory["message"] and count <= 3:
                            logPrint("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                            TFTHistory = await (await connection.request("GET", f"/lol-match-history/v1/products/tft/{current_puuid}/matches?begin=0&count=500")).json()
                    elif "body was empty" in TFTHistory["message"]:
                        logPrint("这位召唤师从5月1日起就没有进行过任何英雄联盟对局。\nThis summoner hasn't played any TFT game yet since May 1st.")
                        break
                    elif "Error getting match list for summoner" in TFTHistory["message"]:
                        TFTHistory_url = "%s/lol-match-history/v1/products/lol/%s/matches?begin=0&count=200" %(connection.address, info_body["puuid"])
                        logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续，或输入任意字符以切换召唤师（Please open the following website, type in the username and password accordingly and press Enter to continue or input anything to switch to another summoner）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和对局数。\nOr submit two nonnegative integers split by space to respecify the begin and count." %(TFTHistory_url, connection.auth_key))
                        cont = logInput()
                        if cont == "":
                            continue
                        else:
                            try:
                                begin, count = map(int, cont.split())
                            except:
                                break
                            else:
                                continue
                else:
                    TFTHistory_get = True
                    break
            if TFTHistory_get:
                gameCount = len(TFTHistory["games"])
                if gameCount <= 20:
                    logPrint(f"程序只获取到{displayName}的{gameCount}场云顶之弈对局。这可能是因为您之前点击过该玩家的对局记录页签，或者该玩家近期只进行过少于20场云顶之弈对局。\nThe program only gets {displayName}'s {gameCount} TFT match(es). Maybe this is because you clicked this summoner's MATCH HISTORY tab before, or this player has played fewer than 20 TFT matches.")
                else:
                    logPrint(f"已经将{displayName}的云顶之弈对局记录扩展到{gameCount}场对局。请点击该玩家的对局记录页签查看。\nExpanded {displayName}'s TFT match history to {gameCount} matches. Please click this summoner's MATCH HISTORY tab to check it out.")
            else:
                logPrint("{displayName}的云顶之弈对局记录获取失败。\nThe program failed to get {displayName}'s TFT match history.")
        else:
            logPrint(info["message"])
        logPrint('请输入要查询的召唤师名称，退出请输入“0”：\nPlease input the summoner name to be searched. Submit "0" to exit.')

#-----------------------------------------------------------------------------
# 未登录状态（Unlogged state）
#-----------------------------------------------------------------------------
async def unlogged_actions(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n-1\t调试自定义接口（Debug custom endpoints）\n1\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option == "-1":
            await send_commands(connection)
        elif option[0] == "1":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 创建房间（Create a lobby）
#-----------------------------------------------------------------------------
async def check_available_queue(connection):
    queues = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    map_CN = {8: "水晶之痕", 10: "扭曲丛林", 11: "召唤师峡谷", 12: "嚎哭深渊", 14: "屠夫之桥", 16: "星界废墟", 18: "瓦洛兰城市公园", 19: "第43区", 20: "飞船坠落点", 21: "百合与莲花的神庙", 22: "聚点危机", 30: "怒火角斗场", 33: "最终都市", 35: "班德尔之森"}
    map_EN = {8: "Crystal Scar", 10: "Twisted Treeline", 11: "Summoner's Rift", 12: "Howling Abyss", 14: "Butcher's Bridge", 16: "Cosmic Ruins", 18: "Valoran City Park", 19: "Substructure 43", 20: "Crash Site", 21: "Temple of Lily and Lotus", 22: "Convergence", 30: "Rings of Wrath", 33: "Final City", 35: "The Bandlewood"}
    pickmode_CN = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式", "QuickplayPickStrategy": "快速匹配", "": "待定"}
    pickmode_EN = {"AllRandomPickStrategy": "All Random", "SimulPickStrategy": "Blind Pick", "TeamBuilderDraftPickStrategy": "Draft Mode", "OneTeamVotePickStrategy": "Vote", "TournamentPickStrategy": "Tournament Draft", "QuickplayPickStrategy": "Quickplay", "": "Pending"}
    available_queues = {}
    for queue in queues:
        if queue["queueAvailability"] == "Available" or queue["id"] in platform_config["ClientSystemStates"]["enabledQueueIdsList"]:
            available_queues[queue["id"]] = queue
    queue_dict = {"queueID": [], "mapID": [], "map_CN": [], "map_EN": [], "gameMode": [], "pickType_CN": [], "pickType_EN": []}
    for queue in available_queues.values():
        queue_dict["queueID"].append(queue["id"])
        queue_dict["mapID"].append(queue["mapId"])
        queue_dict["map_CN"].append(map_CN[queue["mapId"]])
        queue_dict["map_EN"].append(map_EN[queue["mapId"]])
        queue_dict["gameMode"].append(queue["name"])
        queue_dict["pickType_CN"].append(pickmode_CN[queue["gameTypeConfig"]["pickMode"]])
        queue_dict["pickType_EN"].append(pickmode_EN[queue["gameTypeConfig"]["pickMode"]])
    available_queue_df = pandas.DataFrame(queue_dict)
    available_queue_df.sort_values(by = "queueID", inplace = True, ascending = True, ignore_index = True)
    return available_queue_df

async def create_queue_lobby(connection): #返回值为0代表请求正确发送，为1代表返回异常请求，为2代表中途退出。自定义房间创建函数同理（The returned value is 0 if the request is sent properly, 1 if an error message is returned and 2 if the user exits the function halfway. So as `create_custom_lobby` function）
    queues_source = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    queues = {}
    for queue in queues_source:
        queues[queue["id"]] = queue
    enabled_queueIds = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/ClientSystemStates/enabledQueueIdsList")).json()
    for i in range(len(enabled_queueIds)):
        enabled_queueIds[i] = int(enabled_queueIds[i])
    enabled_queueIds.sort()
    logPrint("当前可用队列房间序号：\nCurrently enabled QueueIds:")
    available_queue_df = await check_available_queue(connection)
    logPrint("*****************************************************************************")
    print(format_df(available_queue_df)[0])
    log.write(format_df(available_queue_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
    logPrint("*****************************************************************************")
    logPrint("(%s\t%s\t%s)" %(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), platformId, game_version))
    logPrint('请输入队列房间序号：（输入“0”以刷新可用队列信息。输入负数以退出创建。）\nPlease enter the queueID: (Enter "0" to refresh available queue information. Enter any negative number to exit creation.)')
    while True:
        queueId = logInput()
        if queueId == "":
            continue
        elif queueId == "0":
            available_queue_df = await check_available_queue(connection)
            logPrint("*****************************************************************************")
            print(format_df(available_queue_df)[0])
            log.write(format_df(available_queue_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
            logPrint("*****************************************************************************")
            logPrint("(%s\t%s\t%s)" %(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), platformId, game_version))
            logPrint('请输入队列房间序号：（输入“0”以刷新可用队列信息。输入负数以退出创建。）\nPlease enter the queueID: (Enter "0" to refresh available queue information. Enter any negative number to exit creation.)')
            continue
        else:
            try:
                queueId = int(queueId)
            except ValueError:
                logPrint("请输入整数！\nPlease submit an integer!")
            else:
                if queueId < 0:
                    return 2
                else:
                    break
    region_locale = await (await connection.request("GET", "/riotclient/region-locale")).json()
    custom_game_setup_name_default_dict = {"ar_AE": "مباراة {{summonerName}}", "cs_CZ": "Hra uživatele {{summonerName}}", "el_GR": "Παιχνίδι του {{summonerName}}", "pl_PL": "Rozgrywka gracza {{summonerName}}", "ro_RO": "Jocul lui {{summonerName}}", "hu_HU": "{{summonerName}} játéka", "en_GB": "{{summonerName}}'s Game", "de_DE": "Spiel von {{summonerName}}", "es_ES": "Partida de {{summonerName}}", "it_IT": "Partita di {{summonerName}}", "fr_FR": "Partie de {{summonerName}}", "ja_JP": "{{summonerName}}の試合", "ko_KR": "{{summonerName}} 님의 게임", "es_MX": "Partida de {{summonerName}}", "es_AR": "Partida de {{summonerName}}", "pt_BR": "Partida de {{summonerName}}", "en_US": "{{summonerName}}'s Game", "en_AU": "{{summonerName}}'s Game", "ru_RU": "Игра {{summonerName}}", "tr_TR": "{{summonerName}} oyunu", "en_PH": "{{summonerName}}'s Game", "en_SG": "{{summonerName}}'s Game", "th_TH": "เกมของ {{summonerName}}", "vi_VN": "Trận của {{summonerName}}", "id_ID": "Game {{summonerName}}", "zh_MY": "{{summonerName}} 的房间", "zh_CN": "{{summonerName}}的对局", "zh_TW": "{{summonerName}} 的房間"} #来自（From）：plugins/rcp-fe-lol-parties/global/{locale}/trans.json
    lobbyName = custom_game_setup_name_default_dict.get(region_locale["locale"], "{{summonerName}}的对局").replace("{{summonerName}}", current_info["gameName"])
    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    queue = {
        "queueId": queueId,
        "isCustom": False,
        "customGameLobby": {
            "lobbyName": lobbyName,
            "lobbyPassword": "",
            "configuration": {
                "mapId": 0,
                "gameMode": "",
                "gameMutator": "",
                "mutators": {
                    "id": 0
                },
                "spectatorPolicy": "AllAllowed",
                "teamSize": 5,
                "maxPlayerCount": 0,
                "gameServerRegion": "",
                "spectatorDelayEnabled": True,
                "hidePublicly": False
            }
        }
    }
    if "gameConfig" in lobby_information and not queues[queueId]["isCustom"]:
        response = await (await connection.request("PUT", "/lol-lobby/v1/parties/queue", data = str(queueId))).json()
        logPrint(response)
    else:
        response = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = queue)).json()
        logPrint(response)
    if isinstance(response, dict) and "errorCode" in response:
        if response["message"] == "INVALID_LOBBY": #由房间创建接口返回（Returned by lobby creation endpoint）
            logPrint("房间信息无效！\nLobby configuration invalid!")
        elif response["message"] == "INVALID_REQUEST": #由队列更换接口返回（Returned by queue changing endpoint）
            logPrint("队列更换请求无效！\nQueue change request invalid!")
        elif response["message"] == "INVALID_PERMISSIONS": #由队列更换接口返回（Returned by queue changing endpoint）
            logPrint("必须是小队拥有者才能更改模式！\nMust be party owner to change mode.")
            logPrint("是否单独创建小队？（输入任意键以离开该小队并创建一个新小队，否则留在该小队。）\nDo you want to create another party? (Submit any non-empty string to leave this party and create another party, or null to stay in the current party.)")
            create_party_str = logInput()
            create_party = bool(create_party_str)
            if create_party:
                response = await (await connection.request("DELETE", "/lol-lobby/v2/lobby")).json()
                response = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = queue)).json()
                lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                if "gameConfig" in lobby_information:
                    logPrint(lobby_information)
                else:
                    logPrint("此房间序号尚不可用。请选择其它序号。\nThis queueId isn't available yet. Please select another ID.")
            else:
                logPrint("已取消本次操作。\nCancelled this operation.")
        elif response["message"] == "PARTY_SIZE_LIMIT":
            logPrint("玩家过多，无法加入这条队列！\nThere are too many players for this mode!")
        elif response["message"] == "Gameflow prevented a lobby.": #由房间创建接口返回（Returned by lobby creation endpoint）
            logPrint("您当前的状态不可创建房间！\nYou're not allowed to create a party/lobby at the moment.")
        elif response["message"] == "INVALID_PARTY_STATE": #由房间创建接口返回（Returned by lobby creation endpoint）
            logPrint("小队状态无效！您可能目前正处于英雄选择阶段或游戏内。如果这个问题持续存在，请重启您的客户端。\nInvalid party state! You might be during a champ select stage or in a game. If this problem persists, please restart your League Client.")
        else:
            logPrint("未知错误！\nUnknown error!")
        return 1
    else:
        return 0

async def create_custom_lobby(connection):
    practiceGameTypeConfigIds = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/ClientSystemStates/practiceGameTypeConfigIdList")).json()
    practiceGameTypeConfigIds = sorted(map(int, practiceGameTypeConfigIds))
    gameTypeConfigs = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/gameTypeConfigs")).json()
    gameTypeConfigs = {int(config["id"]): config for config in gameTypeConfigs}
    enabledModes = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/Mutators/EnabledModes")).json()
    gamemodes_zh = {"ARAM": "极地大乱斗", "ARAM_BOT": "极地大乱斗 5v5 人机", "ARAM_UNRANKED_5x5": "极地大乱斗", "ARSR": "峡谷大乱斗", "ASCENSION": "飞升争夺战", "ASSASSINATE": "红月决", "BILGEWATER": "佣兵大作战", "BOT": "人机对战", "BOT_3x3": "人机对战 扭曲丛林", "BRAWL": "神木之门", "CHERRY": "斗魂竞技场", "CHERRY_UNRANKED": "斗魂竞技场", "CHONCC_TREASURE_TFT": "云顶之弈 (恭喜发财)", "CLASH": "冠军杯赛", "CLASSIC": "召唤师峡谷", "COUNTER_PICK": "互选征召赛", "DARKSTAR": "暗星：奇点", "DOOMBOTSTEEMO": "末日人工智能", "FIRSTBLOOD": "大对决", "FIRSTBLOOD_1x1": "大对决 1v1", "FIRSTBLOOD_2x2": "大对决 2v2", "FIVE_YEAR_ANNIVERSARY_TFT": "6周年时光机", "GAMEMODEX": "极限闪击", "HEXAKILL": "六杀争夺战 扭曲丛林", "KINGPORO": "魄罗大乱斗", "KING_PORO": "魄罗大乱斗", "LNY23_TFT": "云顶之弈 (恭喜发财)", "LNY24_TFT": "云顶之弈 (恭喜发财)", "LNY25_TFT": "云顶之弈 (恭喜发财)", "NEXUSBLITZ": "极限闪击", "NIGHTMARE_BOT": "末日人工智能", "NORMAL": "匹配模式", "NORMAL_3x3": "匹配模式 3v3", "NORMAL_TFT": "云顶之弈（匹配模式）", "ODIN": "统治战场", "ODIN_UNRANKED": "统治战场", "ODYSSEY": "奥德赛", "ONEFORALL": "克隆大作战", "ONEFORALL_5x5": "克隆大作战 5v5", "PRACTICETOOL": "训练模式", "PROJECT": "超频行动", "PVE_PUZZLE_TFT": "发条鸟的试炼", "RANKED_FLEX_SR": "排位赛 灵活排位", "RANKED_FLEX_SR_5x5": "排位赛 灵活排位 5v5", "RANKED_FLEX_TT": "排位赛 灵活排位 扭曲丛林", "RANKED_PREMADE-3x3": "排位赛 预组队 3v3", "RANKED_SOLO_5x5": "排位赛 单排/双排", "RANKED_TEAM_3x3": "排位赛 战队 扭曲丛林", "RANKED_TEAM_5x5": "排位赛 战队 召唤师峡谷", "RANKED_TFT": "云顶之弈 (排位赛)", "RANKED_TFT_DOUBLE_UP": "云顶之弈 (双人作战)", "RANKED_TFT_PAIRS": "云顶之弈 (双人作战)", "RANKED_TFT_TURBO": "云顶之弈(狂暴模式)", "RIOTSCRIPT_BOT": "人机对战", "SET_REVIVAL_5_5_TFT": "回归赛季：英雄之黎明重现", "SET_REVIVAL_TFT": "回归赛季：瑞兽再闹新春", "SF_TFT": "云顶之弈 (斗魂锦标赛)", "SIEGE": "枢纽攻防战", "SNOWURF": "冰雪无限火力", "SOLO_DUO_RANKED_5x5": "排位赛 单排/双排", "SR_6x6": "六杀争夺战 召唤师峡谷", "STARGUARDIAN": "怪兽入侵", "STRAWBERRY": "无尽狂潮", "SWIFTPLAY": "快速模式", "TFT": "云顶之弈（匹配模式）", "TUTORIAL": "新手教程", "TUTORIAL_MODULE_1": "新手教程 第一部分", "TUTORIAL_MODULE_2": "新手教程 第二部分", "TUTORIAL_MODULE_3": "新手教程 第三部分", "ULTBOOK": "终极魔典", "URF": "无限火力", "URF_BOT": "无限火力 人机对战"}
    gamemodes_en = {"ARAM": "ARAM", "ARAM_BOT": "ARAM 5v5 Bots", "ARAM_UNRANKED_5x5": "ARAM", "ARSR": "All Random Summoner's Rift", "ASCENSION": "Ascension", "ASSASSINATE": "Hunt of the Blood Moon", "BILGEWATER": "Black Market Brawlers", "BOT": "Co-op vs. Ai", "BOT_3x3": "Co-op vs. Ai Twisted Treeline", "BRAWL": "Brawl", "CHERRY": "Arena", "CHERRY_UNRANKED": "Arena", "CHONCC_TREASURE_TFT": "Choncc's Treasure", "CLASH": "Clash", "CLASSIC": "Summoner's Rift", "COUNTER_PICK": "Nemesis Draft", "DARKSTAR": "Dark Star: Singularity", "DOOMBOTSTEEMO": "Doom Bots", "FIRSTBLOOD": "Showdown", "FIRSTBLOOD_1x1": "Showdown 1v1", "FIRSTBLOOD_2x2": "Showdown 2v2", "FIVE_YEAR_ANNIVERSARY_TFT": "Pengu's Party", "GAMEMODEX": "Nexus Blitz (Pre-release)", "HEXAKILL": "Hexakill Twisted Treeline", "KINGPORO": "Legend of the Poro King", "KING_PORO": "Legend of the Poro King", "LNY23_TFT": "Choncc's Treasure", "LNY24_TFT": "Choncc's Treasure", "LNY25_TFT": "Choncc's Treasure", "NEXUSBLITZ": "Nexus Blitz", "NIGHTMARE_BOT": "Doom Bots", "NORMAL": "Normal", "NORMAL_3x3": "Normal 3v3", "NORMAL_TFT": "Normal (TFT)", "ODIN": "Dominion", "ODIN_UNRANKED": "Dominion", "ODYSSEY": "Odyssey: Extraction", "ONEFORALL": "One for All", "ONEFORALL_5x5": "One for All 5v5", "PRACTICETOOL": "Practice Tool", "PROJECT": "Overcharge", "PVE_PUZZLE_TFT": "Tocker's Trials", "RANKED_FLEX_SR": "Ranked Flex", "RANKED_FLEX_SR_5x5": "Ranked Flex 5v5", "RANKED_FLEX_TT": "Ranked Flex Twisted Treeline", "RANKED_PREMADE-3x3": "Ranked Premade 3v3", "RANKED_SOLO_5x5": "Ranked Solo/Duo", "RANKED_TEAM_3x3": "Ranked Team 3v3", "RANKED_TEAM_5x5": "Ranked Team 5v5", "RANKED_TFT": "Teamfight Tactics (Ranked)", "RANKED_TFT_DOUBLE_UP": "Teamfight Tactics (Double Up)", "RANKED_TFT_PAIRS": "Teamfight Tactics (Double Up)", "RANKED_TFT_TURBO": "Teamfight Tactics (Hyper Roll)", "RIOTSCRIPT_BOT": "Co-op vs. Ai", "SET_REVIVAL_5_5_TFT": "Revival: Dawn of Heroes", "SET_REVIVAL_TFT": "Revival: Festival of Beasts", "SF_TFT": "Teamfight Tactics (Soul Brawl)", "SIEGE": "Nexus Siege", "SNOWURF": "Snow Battle ARURF", "SOLO_DUO_RANKED_5x5": "Ranked Solo/Duo", "SR_6x6": "Hexakill Summoner's Rift", "STARGUARDIAN": "Invasion", "STRAWBERRY": "Swarm", "SWIFTPLAY": "Swiftplay", "TFT": "Normal (TFT)", "TUTORIAL": "Tutorial", "TUTORIAL_MODULE_1": "Tutorial Part 1", "TUTORIAL_MODULE_2": "Tutorial Part 2", "TUTORIAL_MODULE_3": "Tutorial Part 3", "ULTBOOK": "Ultimate Spellbook", "URF": "Ultra Rapid Fire", "URF_BOT": "Ultra Rapid Fire Bots 5v5"}
    gamemaps_zh = {1: "召唤师峡谷 夏季怀旧版", 2: "召唤师峡谷 万圣节怀旧版", 3: "试炼之地", 4: "熔岩大厅", 7: "召唤师峡谷", 8: "水晶之痕", 10: "扭曲丛林", 11: "召唤师峡谷", 12: "嚎哭深渊", 13: "召唤师峡谷", 14: "屠夫之桥", 16: "星界废墟", 18: "瓦洛兰城市公园", 19: "第43区", 20: "飞船坠落点", 21: "百合与莲花的神庙", 22: "聚点危机", 30: "怒火角斗场", 33: "最终都市", 35: "班德尔之森", 90: "第五赛季季前赛测试地图"}
    gamemaps_en = {1: "Summoner's Rift Original Summoner Variant", 2: "Summoner's Rift Original Autumn (Harrowing) Variant", 3: "The Proving Grounds", 4: "Magma Chamber", 7: "Summoner's Rift", 8: "Crystal Scar", 10: "Twisted Treeline", 11: "Summoner's Rift", 12: "Howling Abyss", 13: "Summoner's Rift", 14: "Butcher's Bridge", 16: "Cosmic Ruins", 18: "Valoran City Park", 19: "Substructure 43", 20: "Crash Site", 21: "Temple of Lily and Lotus", 22: "Convergence", 30: "Rings of Wrath", 33: "Final City", 35: "The Bandlewood", 90: "Pre-Season 5 Testing Map"}
    availableMapIds = {"ARAM": [12], "ARAM_BOT": [12], "ARAM_UNRANKED_5x5": [12], "ARSR": [11], "ASCENSION": [8], "ASSASSINATE": [11], "BILGEWATER": [11], "BOT": [11], "BOT_3x3": [10], "BRAWL": [35], "CHERRY": [30], "CHERRY_UNRANKED": [30], "CHONCC_TREASURE_TFT": [22], "CLASH": [11], "CLASSIC": [11, 12, 21, 22], "COUNTER_PICK": [11], "DARKSTAR": [16], "DOOMBOTSTEEMO": [11], "FIRSTBLOOD": [4], "FIRSTBLOOD_1x1": [4], "FIRSTBLOOD_2x2": [4], "FIVE_YEAR_ANNIVERSARY_TFT": [22], "GAMEMODEX": [21, 11, 12, 22], "HEXAKILL": [10], "KINGPORO": [12], "KING_PORO": [12], "LNY23_TFT": [22], "LNY24_TFT": [22], "LNY25_TFT": [22], "NEXUSBLITZ": [21], "NIGHTMARE_BOT": [11], "NORMAL": [11], "NORMAL_3x3": [11], "NORMAL_TFT": [22], "ODIN": [8], "ODIN_UNRANKED": [8], "ODYSSEY": [20], "ONEFORALL": [11], "ONEFORALL_5x5": [11], "PRACTICETOOL": [11], "PROJECT": [19], "PVE_PUZZLE_TFT": [22], "RANKED_FLEX_SR": [11], "RANKED_FLEX_SR_5x5": [11], "RANKED_FLEX_TT": [11], "RANKED_PREMADE-3x3": [10], "RANKED_SOLO_5x5": [11], "RANKED_TEAM_3x3": [10], "RANKED_TEAM_5x5": [11], "RANKED_TFT": [22], "RANKED_TFT_DOUBLE_UP": [22], "RANKED_TFT_PAIRS": [22], "RANKED_TFT_TURBO": [22], "RIOTSCRIPT_BOT": [11], "SET_REVIVAL_5_5_TFT": [22], "SET_REVIVAL_TFT": [22], "SF_TFT": [22], "SIEGE": [11], "SNOWURF": [11], "SOLO_DUO_RANKED_5x5": [11], "SR_6x6": [11], "STARGUARDIAN": [18], "STRAWBERRY": [33], "SWIFTPLAY": [11], "TFT": [22], "TUTORIAL": [11, 12, 21, 22], "TUTORIAL_MODULE_1": [11], "TUTORIAL_MODULE_2": [11], "TUTORIAL_MODULE_3": [11], "ULTBOOK": [11], "URF": [11], "URF_BOT": [11]}
    gameTypes_zh = {"GAME_CFG_PICK_BLIND": "自选模式（自定义）", "GAME_CFG_DRAFT_STD": "征召模式（自定义）", "GAME_CFG_DRAFT_NOBAN": "轮选模式", "GAME_CFG_PICK_RANDOM": "全随机模式（自定义）", "GAME_CFG_PICK_SIMUL": "同选模式", "GAME_CFG_DRAFT_TOURNAMENT": "竞技征召模式（自定义）", "GAME_CFG_PICK_SIMUL_TD": "计时征召", "GAME_CFG_BASIC_TUTORIAL": "基础教程", "GAME_CFG_ADV_TUTORIAL": "进阶教程", "GAME_CFG_CAP": "最终教程", "GAME_CFG_BLIND_RANDOM": "盲选随机", "GAME_CFG_BLIND_DUPE": "克隆选择（自定义）", "GAME_CFG_CROSS_DUPE": "全队克隆", "GAME_CFG_BLIND_DRAFT_ST": "自选征召模式（自定义）", "GAME_CFG_COUNTER_PICK": "互选模式（自定义）", "GAME_CFG_TEAM_BUILDER_DRAFT": "征召模式", "GAME_CFG_TEAM_BUILDER_BLIND": "自选模式", "GAME_CFG_TEAM_BUILDER_BLIND_DRAFT": "自选征召", "GAME_CFG_TEAM_BUILDER_RANDOM": "全随机模式", "GAME_CFG_TEAM_BUILDER_BLIND_DUPE": "克隆选择", "GAME_CFG_TEAM_BUILDER_QUICKPLAY": "快速匹配"}
    gameTypes_en = {"GAME_CFG_PICK_BLIND": "Blind Pick (custom)", "GAME_CFG_DRAFT_STD": "Draft Mode (custom)", "GAME_CFG_DRAFT_NOBAN": "Draft Noban (custom)", "GAME_CFG_PICK_RANDOM": "All Random (custom)", "GAME_CFG_PICK_SIMUL": "Simultaneous Pick (custom)", "GAME_CFG_DRAFT_TOURNAMENT": "Tournament Draft (custom)", "GAME_CFG_PICK_SIMUL_TD": "Timed Draft (custom)", "GAME_CFG_BASIC_TUTORIAL": "Basic Tutorial", "GAME_CFG_ADV_TUTORIAL": "Advanced Tutorial", "GAME_CFG_CAP": "Capstone Tutorial", "GAME_CFG_BLIND_RANDOM": "Blind Random (custom)", "GAME_CFG_BLIND_DUPE": "All for one (custom)", "GAME_CFG_CROSS_DUPE": "All for one (cross-team)", "GAME_CFG_BLIND_DRAFT_ST": "Blind Draft Pick (custom)", "GAME_CFG_COUNTER_PICK": "Nemesis Draft (custom)", "GAME_CFG_TEAM_BUILDER_DRAFT": "Draft Pick", "GAME_CFG_TEAM_BUILDER_BLIND": "Blind Pick", "GAME_CFG_TEAM_BUILDER_BLIND_DRAFT": "Blind Draft Pick", "GAME_CFG_TEAM_BUILDER_RANDOM": "All Random", "GAME_CFG_TEAM_BUILDER_BLIND_DUPE": "All for one", "GAME_CFG_TEAM_BUILDER_QUICKPLAY": "Quickplay"}
    spectatorPolicy = ["LobbyAllowed", "FriendsAllowed", "AllAllowed", "NotAllowed"]
    logPrint("请选择自定义房间的游戏模式：\nPlease select a game mode of the lobby:")
    for i in range(len(enabledModes)):
        logPrint("%d\t%s%s%s%s" %(i + 1, gamemodes_zh[enabledModes[i].upper()], "【" if "(" in gamemodes_en[enabledModes[i].upper()] else "（", gamemodes_en[enabledModes[i].upper()], "】" if "(" in gamemodes_en[enabledModes[i].upper()] else "）"), write_time = False)
    while True:
        gameModeTypeNumber = logInput()
        if gameModeTypeNumber == "":
            continue
        elif gameModeTypeNumber == "0":
            return 2
        elif gameModeTypeNumber in list(map(str, range(1, len(enabledModes) + 1))):
            selectedMode = enabledModes[int(gameModeTypeNumber) - 1].upper()
            break
        else:
            logPrint("游戏模式输入错误！请重新输入：\nError input of game mode! Please try again:")
    logPrint("请输入地图序号：\nPlease enter a mapID:")
    for i in sorted(gamemaps_zh.keys()):
        logPrint("%s%d\t%s%s%s%s" %("☆" if i in availableMapIds[selectedMode] else "", i, gamemaps_zh[i], "【" if "(" in gamemaps_en[i] else "（", gamemaps_en[i], "】" if "(" in gamemaps_en[i] else "）"), write_time = False)
    while True:
        mapId = logInput()
        if mapId == "" and len(availableMapIds[selectedMode]) > 0:
            mapId = availableMapIds[selectedMode][0]
            break
        elif mapId == "0":
            return 2
        elif mapId in list(map(str, gamemaps_zh.keys())):
            mapId = int(mapId)
            break
        else:
            logPrint("地图序号输入错误！请重新输入：\nError input of mapID! Please try again:")
    print("请选择自定义房间的游戏类型：\nPlease select a game type of the lobby:")
    for i in practiceGameTypeConfigIds:
        config = gameTypeConfigs[i]
        print("%d\t%s%s%s%s" %(i, gameTypes_zh[config["name"]], "【" if "(" in gameTypes_en[config["name"]] else "（", gameTypes_en[config["name"]], "】" if "(" in gameTypes_en[config["name"]] else "）"))
    while True:
        mutatorId = logInput()
        if mutatorId == "":
            continue
        elif mutatorId == "0":
            return 2
        elif mutatorId in list(map(str, practiceGameTypeConfigIds)):
            mutatorId = int(mutatorId)
            break
        else:
            logPrint("游戏类型输入错误！请重新输入：\nError input of game type! Please try again:")
    logPrint("请选择自定义房间的允许观战策略：\nPlease select a spectator policy:\n1\t只允许房间内玩家（Lobby Only）\n2\t只允许好友（国服不可用）【Friends List Only (Unavailable on Chinese servers)】\n3\t所有人（国服不可用）【All (Unavailable on Chinese servers)】\n4\t无（None）")
    while True:
        customSpectatorPolicyTypeNumber = logInput()
        if customSpectatorPolicyTypeNumber == "":
            continue
        elif customSpectatorPolicyTypeNumber[0] == "0":
            return 2
        elif customSpectatorPolicyTypeNumber[0] in list(map(str, range(1, 5))):
            customSpectatorPolicyTypeNumber = int(customSpectatorPolicyTypeNumber[0])
            break
        else:
            logPrint("允许观战策略输入错误！请重新输入：\nError input of spectator policy! Please try again:")
    logPrint("请依次输入对局名、队伍规模、密码（可选）：\nPlease enter the lobby's name, team size and password (optional):")
    logPrint("对局名（Lobby Name）：", end = "")
    lobbyName = logInput()
    if lobbyName == "":
        region_locale = await (await connection.request("GET", "/riotclient/region-locale")).json()
        custom_game_setup_name_default_dict = {"ar_AE": "مباراة {{summonerName}}", "cs_CZ": "Hra uživatele {{summonerName}}", "el_GR": "Παιχνίδι του {{summonerName}}", "pl_PL": "Rozgrywka gracza {{summonerName}}", "ro_RO": "Jocul lui {{summonerName}}", "hu_HU": "{{summonerName}} játéka", "en_GB": "{{summonerName}}'s Game", "de_DE": "Spiel von {{summonerName}}", "es_ES": "Partida de {{summonerName}}", "it_IT": "Partita di {{summonerName}}", "fr_FR": "Partie de {{summonerName}}", "ja_JP": "{{summonerName}}の試合", "ko_KR": "{{summonerName}} 님의 게임", "es_MX": "Partida de {{summonerName}}", "es_AR": "Partida de {{summonerName}}", "pt_BR": "Partida de {{summonerName}}", "en_US": "{{summonerName}}'s Game", "en_AU": "{{summonerName}}'s Game", "ru_RU": "Игра {{summonerName}}", "tr_TR": "{{summonerName}} oyunu", "en_PH": "{{summonerName}}'s Game", "en_SG": "{{summonerName}}'s Game", "th_TH": "เกมของ {{summonerName}}", "vi_VN": "Trận của {{summonerName}}", "id_ID": "Game {{summonerName}}", "zh_MY": "{{summonerName}} 的房间", "zh_CN": "{{summonerName}}的对局", "zh_TW": "{{summonerName}} 的房間"} #来自（From）：plugins/rcp-fe-lol-parties/global/{locale}/trans.json
        lobbyName = custom_game_setup_name_default_dict.get(region_locale["locale"], "{{summonerName}}的对局").replace("{{summonerName}}", current_info["gameName"])
    logPrint("队伍规模（Team Size）：", end = "")
    while True:
        teamsize = logInput()
        if teamsize == "":
            teamsize = 5
            break
        elif teamsize == "0":
            return 2
        elif teamsize in list(map(str, range(1, 6))):
            teamsize = int(teamsize)
            break
        else:
            logPrint("队伍规模输入错误！请重新输入：\nError input of team size! Please try again:")
    logPrint("密码（Password）：", end = "")
    lobbyPassword = logInput()
    logPrint("是否添加观战延迟？（输入任意键以添加，否则不添加。）\nAdd spectating delay? (Submit any non-empty string to add delay, or null to refuse addition.)")
    spectatorDelayEnabled_str = logInput()
    spectatorDelayEnabled = bool(spectatorDelayEnabled_str)
    custom = {
        "queueId": 0,
        "isCustom": True,
        "customGameLobby": {
            "lobbyName": lobbyName,
            "lobbyPassword": lobbyPassword,
            "configuration": {
                "mapId": mapId,
                "gameMode": selectedMode,
                "gameMutator": "",
                "gameTypeConfig": {
                    "id": mutatorId
                },
                "spectatorPolicy": spectatorPolicy[customSpectatorPolicyTypeNumber - 1],
                "teamSize": teamsize,
                "maxPlayerCount": 0,
                "gameServerRegion": "",
                "spectatorDelayEnabled": spectatorDelayEnabled,
                "hidePublicly": False
            }
        }
    }
    response = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)).json()
    logPrint(response)
    if isinstance(response, dict) and "errorCode" in response:
        if response["message"] == "Gameflow prevented a lobby.":
            logPrint("您当前的状态不可创建房间！\nYou're not allowed to create a party/lobby at the moment.")
        elif "GameModeNotSupportedException" in response["message"]:
            logPrint("该模式目前不支持自定义。\nCustom game of this mode isn't supported currently.")
        elif "GameMapNotFoundException" in response["message"]:
            logPrint("未找到该地图！请切换一个地图。\nGame map not found! Please change a map.")
        elif "NotEnoughPlayersException" in response["message"]:
            logPrint("玩家数量不足！请修改队伍规模。\nNot enough players! Please change the team size.")
        elif "TooManyPlayersException" in response["message"]:
            logPrint("玩家数量过多！请修改队伍规模。\nToo many players! Please change the team size.")
        elif "UnexpectedServiceException" in response["message"]:
            if "Map not enabled" in response["message"]:
                logPrint("该地图不支持当前模式！请更换地图或者游戏模式。\nThis map doesn't support this game mode currently. Please change a game mode or map.")
            elif "Provided game name must not be null or empty" in response["message"]:
                logPrint("房间名不能为空！\nLobby name can't be empty!")
            else:
                logPrint("参数错误！\nParameter error!")
        elif "No game type config found with id" in response["message"]:
            logPrint("游戏模式类型错误！请修改游戏类型。\nGame type error! Please change the game type.")
        elif "out of range" in response["message"]:
            logPrint("参数范围错误！\nParameter out of range!")
        elif "invalid type unsigned" in response["message"]:
            logPrint("参数类型错误！\nInvalid parameter type!")
        else:
            logPrint("未知错误！\nUnknown error!")
        return 1
    else:
        return 0

async def sort_custom_lobbies(connection):
    response = await (await connection.request("POST", "/lol-lobby/v1/custom-games/refresh")).json()
    custom_lobbies = await (await connection.request("GET", "/lol-lobby/v1/custom-games")).json()
    custom_lobby_data = {}
    for i in range(len(custom_lobby_header_keys)):
        key = custom_lobby_header_keys[i]
        custom_lobby_data[key] = []
    if not (isinstance(custom_lobbies, dict) and "errorCode" in custom_lobbies):
        for lobby in custom_lobbies:
            for i in range(len(custom_lobby_header_keys)):
                key = custom_lobby_header_keys[i]
                if i == 12: #观战策略（`spectatorPolicy`）
                    custom_lobby_data[key].append(spectatorPolicies[lobby["spectatorPolicy"]])
                elif i == 13: #地图名称（`mapName`）
                    custom_lobby_data[key].append(maps[lobby["mapId"]])
                elif i == 14: #玩家比例（`filledPlayerRatio`）
                    custom_lobby_data[key].append("%d/%d" %(lobby["filledPlayerSlots"], lobby["maxPlayerSlots"]))
                elif i == 15: #观战者比例（`filledSpectatorRatio`）
                    custom_lobby_data[key].append("%d/%d" %(lobby["filledSpectatorSlots"], lobby["maxSpectatorSlots"]))
                else:
                    custom_lobby_data[key].append(lobby[key])
    custom_lobby_statistics_output_order = [4, 5, 9, 2, 6, 13, 0, 7, 14, 12, 1, 8, 15, 3, 11, 10]
    custom_lobby_data_organized = {}
    for i in custom_lobby_statistics_output_order:
        key = custom_lobby_header_keys[i]
        custom_lobby_data_organized[key] = custom_lobby_data[key]
    custom_lobby_df = pandas.DataFrame(data = custom_lobby_data_organized)
    for column in custom_lobby_df:
        if custom_lobby_df[column].dtype == "bool":
            custom_lobby_df[column] = custom_lobby_df[column].astype(str)
            for i in range(len(custom_lobby_df)):
                custom_lobby_df.loc[i, column] = "√" if custom_lobby_df[column][i] == "True" else ""
    custom_lobby_df = pandas.concat([pandas.DataFrame([custom_lobby_header])[custom_lobby_df.columns], custom_lobby_df], ignore_index = True)
    return custom_lobby_df

async def create_lobby_json(connection):
    logPrint('请输入用于创建房间的json代码：\nPlease input the json code to create the custom lobby:\n格式（Format）：\n{"queueId": 0, "isCustom": True, "customGameLobby": {"lobbyName": "string", "lobbyPassword": "string", "configuration": {"mapId": 0, "gameMode": "string", "mutators": {"id": 0}, "spectatorPolicy": "AllAllowed", "teamSize": 0, "gameServerRegion": "string", "spectatorDelayEnabled": True}}}\nlobbyChange = ', end = "")
    while True:
        s = logInput()
        if s == "":
            continue
        elif s[0] == "0":
            return 2
        else:
            try:
                body = json.loads(s)
            except json.decoder.JSONDecodeError:
                try:
                    body = eval(s)
                except:
                    logPrint("格式错误！\nFormat error!")
                    continue
                else:
                    break
            else:
                break
    response = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = body)).json()
    logPrint(response)
    if isinstance(response, dict) and "errorCode" in response:
        return 1
    else:
        return 0

async def create_lobby(connection):
    while True:
        logPrint("选择一个房间类型：\nSelect a type of lobby:\n1\t创建小队（Create a party）\n2\t创建自定义房间（Create a custom lobby）\n3\t通过json创建（Create through json）")
        method = logInput()
        if method == "":
            continue
        elif method[0] == "0":
            break
        elif method[0] in ["1", "2", "3"]:
            if method[0] == "1":
                result = await create_queue_lobby(connection)
            elif method[0] == "2":
                result = await create_custom_lobby(connection)
            else:
                result = await create_lobby_json(connection)
            if result == 0:
                gameflow_phase = await get_gameflow_phase(connection)
                if gameflow_phase == "Lobby":
                    logPrint("房间创建成功。\nLobby/Party created successfully.")
                    break
                else:
                    logPrint("房间创建失败。\nLobby/Party failed to be created.")
            elif result == 1 or result == 2:
                pass

async def sort_received_invitations(connection):
    queues_source = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    queues = {}
    for queue in queues_source:
        queues[queue["id"]] = queue
    receivedInvitations = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
    invid_data = {}
    for i in range(len(invid_header_keys)):
        key = invid_header_keys[i]
        invid_data[key] = []
    for invid in receivedInvitations:
        inviter_info_recapture = 0
        inviter_info = await get_info(connection, invid["fromSummonerId"])
        while not inviter_info["info_got"] and inviter_info["body"]["httpStatus"] != 404 and inviter_info_recapture < 3:
            logPrint(inviter_info["message"])
            inviter_info_recapture += 1
            logPrint("邀请者信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an inviter (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(invid["fromSummonerId"], inviter_info_recapture, invid["fromSummonerId"], inviter_info_recapture))
            inviter_info = await get_info(connection, invid["fromSummonerId"])
        if not inviter_info["info_got"]:
            logPrint(inviter_info["message"])
            logPrint("邀请者信息（召唤师序号：%d）获取失败！将忽略该邀请者。\nInformation of an inviter (summonerId: %d) capture failed! The program will ignore this inviter.")
        for i in range(len(invid_header_keys)):
            key = invid_header_keys[i]
            if i <= 9:
                if i == 2:
                    invid_data[key].append(get_info_name(inviter_info["body"]) if inviter_info["info_got"] else "")
                elif i == 8:
                    invid_data[key].append(inviter_info["body"]["puuid"] if inviter_info["info_got"] else "")
                elif i == 9:
                    try:
                        invid_timestamp = int(invid["timestamp"])
                    except ValueError: #自定义对局邀请的时间戳是转换好的（Custom game invitation's timestamp has already been transformed）
                        invid_data[key].append(invid["timestamp"])
                    else:
                        invid_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(invid_timestamp // 1000)))
                else:
                    invid_data[key].append(invid[key])
            elif i <= 13:
                invid_data[key].append(invid["gameConfig"][key])
            else:
                invid_data[key].append("自定义" if invid["gameConfig"]["queueId"] == -1 else queues[invid["gameConfig"]["queueId"]][key.split()[1]])
    invid_statistics_output_order = [2, 1, 8, 9, 4, 10, 11, 12, 14, 13, 3, 6, 0, 5]
    invid_data_organized = {}
    for i in invid_statistics_output_order:
        key = invid_header_keys[i]
        invid_data_organized[key] = invid_data[key]
    invid_df = pandas.DataFrame(data = invid_data_organized)
    invid_df = pandas.concat([pandas.DataFrame([invid_header])[invid_df.columns], invid_df], ignore_index = True)
    return invid_df

async def gameflow_phase_transition(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t创建房间（Create a lobby）\n2\t处理邀请（Handle invitations）\n3\t加入小队或自定义房间（Join party/lobby）\n4\t观战（Spectate a game）\n5\t聊天（Chat）\n6\t其它（Others）\n7\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option == "-1":
            await send_commands(connection)
        elif option[0] == "1":
            await create_lobby(connection)
        elif option[0] == "2":
            await handle_invitations(connection)
        elif option[0] == "3":
            await join_game(connection)
        elif option[0] == "4":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "None":
                logPrint('请输入您想要观看的玩家召唤师名。输入“0”以返回上一层。\nPlease input the summonerName of the player to spectate. Submit "0" to return to the last step.')
                while True:
                    spectating_summonerName = logInput()
                    if spectating_summonerName == "":
                        continue
                    elif spectating_summonerName == "0":
                        break
                    else:
                        spectating_summoner_info = await get_info(connection, spectating_summonerName)
                        if spectating_summoner_info["info_got"]:
                            if spectating_summoner_info["body"]["puuid"] == current_info["puuid"]:
                                logPrint("你不能观战自己。战斗！爽！————\nYou can't spectate yourself. Battle... YES!!!!")
                                continue
                            dropInSpectateGameId = gameQueueType = allowObserveMode = ""
                            spectate_puuid = spectating_summoner_info["body"]["puuid"]
                            spectating_summonerName = get_info_name(spectating_summoner_info["body"])
                            body = {"dropInSpectateGameId": str(dropInSpectateGameId), "gameQueueType": gameQueueType, "allowObserveMode": allowObserveMode, "puuid": spectate_puuid}
                            response = await (await connection.request("POST", "/lol-spectator/v1/spectate/launch", data = body)).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                if response["httpStatus"] == 400 and response["message"] == "SpectatorPlugin_NOT_AVAILABLE":
                                    logPrint("您所在的服务器不支持玩家可观战性检测。请自行判断玩家是否可观战。\nThe server or platform you're currently on doesn't support this endpoint. Please judge by yourself whether a player is observable.")
                                elif response["httpStatus"] == 500 and "Couldn't find service in service discovery using ServerLocationEndpointFilter" in response["message"]:
                                    logPrint("观战服务不可用。\nSpectator service unavailable.")
                                else:
                                    if "Game is not able to be spectated" in response["message"]:
                                        logPrint("现在还不能观战这个游戏类型，或者这个自定义对局未对观战者开放。\nThis game type cannot be spectated right now, or this custom game is not open to spectators.")
                                    elif "Player was not found" in response["message"]:
                                        logPrint("该玩家未在游戏中。\nThis player isn't in a game currently.")
                                    elif "Game not found" in response["message"]:
                                        logPrint("游戏已结束。\nThe game has ended.")
                                    elif "Already in gameflow" in response["message"]:
                                        logPrint("您目前的状态不可观战。请等待游戏结束或者退出房间来进行观战。\nYou're not allowed to spectate for now. Please wait for the current game to end or exit the party or lobby to spectate any game.")
                                    else:
                                        logPrint("观战失败。请通过客户端内右键点击一名好友，或者通过第三方工具来进行观战。\nSpectating failed. Please right click on a friend or use another third-party tool to spectate.")
                            else:
                                time.sleep(1) #发送指令后客户端不一定马上进入英雄选择或游戏中（The client won't immediately enter the champ select or in game stage after the program posts the spectating requests）
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase in {"ChampSelect", "InProgress"}:
                                    logPrint("启动观战成功！您正在观看%s的对局。\nLaunched spectating successfully. You'll be spectating the game of %s soon." %(spectating_summonerName, spectating_summonerName))
                                    break
                                else:
                                    logPrint("这场对局现在不可观战。它也许已经结束了。\nThe game isn't available for spectate now. It might have ended.")
                        else:
                            logPrint(spectating_summoner_info["message"])
            else:
                logPrint("您目前的状态不可观战。请等待游戏结束或者退出房间来进行观战。\nYou're not allowed to spectate for now. Please wait for the current game to end or exit the party or lobby to spectate any game.")
        elif option[0] == "5":
            await chat(connection)
        elif option[0] == "6":
            logPrint('请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n2\t扩展对局记录（Expand match history）')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await toggle_nonfriend_game_invite(connection)
                elif suboption[0] == "2":
                    await expand_match_history(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n2\t扩展对局记录（Expand match history）')
        elif option[0] == "7":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 房间内行为模拟（Lobby action simulation）
#-----------------------------------------------------------------------------
async def get_perk_page(connection):
    current_summonerId = current_info["summonerId"]
    perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
    perkPage_data = {}
    for i in range(len(perkPage_header_keys)):
        key = perkPage_header_keys[i]
        perkPage_data[key] = []
    for page in perkPages:
        for i in range(len(perkPage_header_keys)):
            key = perkPage_header_keys[i]
            if i <= 26:
                if i == 24: #上次修改时间（`lastModifiedTime`）
                    perkPage_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(page["lastModified"] // 1000)))
                elif i == 25: #快速模式英雄名称列表（`quickPlayChampionNames`）
                    perkPage_data[key].append(list(map(lambda x: LoLChampions[x]["name"], page["quickPlayChampionIds"])))
                elif i == 26: #推荐英雄名称（`recommendationChampionName`）
                    perkPage_data[key].append("" if page["recommendationChampionId"] == 0 else LoLChampions[page["recommendationChampionId"]]["name"])
                else:
                    perkPage_data[key].append(page[key])
            elif i <= 31:
                if i == 30: #基石槽位类型（`pageKeystone slotType`）
                    perkPage_data[key].append(slotTypes[page[key.split()[0]][key.split()[1]]])
                else:
                    perkPage_data[key].append(page[key.split()[0]][key.split()[1]])
            else: #已选择的符文（`uiPerksNames`）
                perkPage_data[key].append(list(map(lambda x: x["name"], page["uiPerks"])))
    perkPage_statistics_output_order = [2, 10, 11, 1, 3, 7, 5, 4, 8, 6, 13, 14, 12, 22, 20, 19, 28, 29, 30, 31, 27, 32, 21, 23, 24, 15, 25, 16, 26, 18]
    perkPage_data_organized = {}
    for i in perkPage_statistics_output_order:
        key = perkPage_header_keys[i]
        perkPage_data_organized[key] = perkPage_data[key]
    perkPage_df = pandas.DataFrame(data = perkPage_data_organized)
    for column in perkPage_df:
        if perkPage_df[column].dtype == "bool":
            perkPage_df[column] = perkPage_df[column].astype(str)
            for i in range(len(perkPage_df)):
                perkPage_df.loc[i, column] = "√" if perkPage_df[column][i] == "True" else ""
    perkPage_df = pandas.concat([pandas.DataFrame([perkPage_header])[perkPage_df.columns], perkPage_df], ignore_index = True)
    return perkPage_df

async def sort_social_leaderboard(connection, queueType: str, ignore_warning: bool = False):
    social_leaderboard = await (await connection.request("GET", f"/lol-social-leaderboard/v1/social-leaderboard-data?queueType={queueType}")).json()
    social_leaderboard_data = {}
    for i in range(len(social_leaderboard_header_keys)):
        key = social_leaderboard_header_keys[i]
        social_leaderboard_data[key] = []
    if isinstance(social_leaderboard, dict) and "errorCode" in social_leaderboard:
        if not ignore_warning:
            logPrint(social_leaderboard)
            if social_leaderboard["message"] == "Expected value for argument 'queueType'.":
                logPrint("您传入的队列类型是空字符串。\nThe queueType you passed is an empty string.")
            elif "is not a valid LolSocialLeaderboardLeagueQueueType enumeration value for 'queueType'" in social_leaderboard["message"]:
                logPrint("队列类型有误！\nError queueType!")
            else:
                logPrint("未知错误！\nUnknown error!")
    else:
        for player in social_leaderboard["rowData"]:
            for i in range(len(social_leaderboard_header_keys)):
                key = social_leaderboard_header_keys[i]
                if i == 0: #可用性（`availability`）
                    social_leaderboard_data[key].append(availabilities[player[key]])
                elif i == 1: #段位分级（`division`）
                    social_leaderboard_data[key].append("" if player[key] == "NA" else player[key])
                elif i == 14: #段位（`tier`）
                    social_leaderboard_data[key].append(tiers_all[player[key]])
                elif i >= 16: #召唤师图标相关键（Summoner icon-related keys）
                    social_leaderboard_data[key].append(summonerIcons[player["profileIconId"]][key.split("_")[1]] if player["profileIconId"] in summonerIcons and key.split("_")[1] in summonerIcons[player["profileIconId"]] else player["profileIconId"] if i == 16 else "")
                else:
                    social_leaderboard_data[key].append(player[key])
    social_leaderboard_statistics_output_order = [5, 12, 2, 13, 10, 9, 7, 16, 17, 11, 4, 8, 14, 1, 6, 15, 0, 3]
    social_leaderboard_data_organized = {}
    for i in social_leaderboard_statistics_output_order:
        key = social_leaderboard_header_keys[i]
        social_leaderboard_data_organized[key] = social_leaderboard_data[key]
    social_leaderboard_df = pandas.DataFrame(data = social_leaderboard_data_organized).sort_values(by = "leaderboardPosition", ascending = True, ignore_index = True)
    for column in social_leaderboard_df:
        if social_leaderboard_df[column].dtype == "bool":
            social_leaderboard_df[column] = social_leaderboard_df[column].astype(str)
            for i in range(len(social_leaderboard_df)):
                social_leaderboard_df.loc[i, column] = "√" if social_leaderboard_df[column][i] == "True" else ""
    social_leaderboard_df = pandas.concat([pandas.DataFrame([social_leaderboard_header])[social_leaderboard_df.columns], social_leaderboard_df], ignore_index = True)
    return social_leaderboard_df

async def get_collection(connection): #这部分代码根据商品藏品信息脚本改写而成（This part of code is drafted according to Customized Program 07）
    #准备数据资源（Prepare data resources）
    logPrint("[get_collection]正在准备藏品相关数据资源…… | Preparing collection-related data resources ...", print_time = True)
    championSkins_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
    companions_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
    nexusfinishers_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/nexusfinishers.json")).json()
    statstones_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/statstones.json")).json()
    strawberryHub_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/strawberry-hub.json")).json()
    summonerEmotes_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-emotes.json")).json()
    summonerIcons_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    tftdamageskins_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/tftdamageskins.json")).json()
    tftmapskins_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/tftmapskins.json")).json()
    tftplaybooks_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/tftplaybooks.json")).json()
    tftzoomskins_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/tftzoomskins.json")).json()
    wardSkins_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    lolinventorytype_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/lolinventorytype.json")).json()
    #获取商品和藏品数据（Get store and collection data）
    logPrint("[get_collection]正在获取商品和藏品数据 | Fetching store and collection data ...", print_time = True)
    riot_client_info = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region = client_info["--region"]
    locale = client_info["--locale"]
    lolinventorytypes = {x["inventoryTypeId"]: x for x in lolinventorytype_initial}
    inventoryTypes = sorted(list(map(lambda x: x["inventoryTypeId"], lolinventorytype_initial)))
    collection = await (await connection.request("GET", "/lol-inventory/v1/inventory?inventoryTypes=%s" %(str(inventoryTypes).replace(" ", "").replace("'", '"')))).json()
    catalogDicts = {}
    catalogList = []
    for inventoryType in inventoryTypes:
        catalogDicts[inventoryType] = await (await connection.request("GET", "/lol-catalog/v1/items/" + inventoryType)).json()
        catalogDicts[inventoryType] = sorted(catalogDicts[inventoryType], key = lambda x: x["itemId"])
        catalogList += catalogDicts[inventoryType]
    store = await (await connection.request("GET", "/lol-store/v1/catalog")).json()
    #下面定义对应关系表（The following code define the table for mapping）
    logPrint("[get_collection]建立对应关系表 | Build the map table ...", print_time = True)
    collection_hashtable = {(item["inventoryType"], item["itemId"]): item["name"] for item in catalogList} | {(item["inventoryType"], item["itemId"]): item["localizations"][locale]["name"] for item in store if item["localizations"] != None} #原本的藏品信息中没有记录名称，所以需要借用商品信息中的名称。之所以不考虑使用识别码作为键，是因为在从`lol-store`接口获取的商品信息中，存在识别码重复的两件商品，而道具类型和道具序号的组合应当能够唯一确定一件商品。另外，从`lol-catalog`和`lol-store`接口获取的商品信息可以互相补充（The original collection information doesn't contain the names, so they're cited from the catalog information. The reason why `itemInstanceId` isn't taken as the key is that there're two items with the same `itemInstanceId` in the items obtaned from `lol-store` API. However, the combination of `inventoryType` and `itemId` should uniquely correspond to an item. Besides, item information obtained from `lol-catalog` API and that from `lol-store` API can supplement each other）
    championSkins_hashtable = {} #对于特定道具类型的商品，道具序号可唯一确定一件商品。下同（As for an item of specific inventory type, the itemId can uniquely correspond to that item. So can the following）
    for skin in championSkins_initial.values():
        championSkins_hashtable[skin["id"]] = {}
        championSkins_hashtable[skin["id"]]["name"] = skin["name"]
        championSkins_hashtable[skin["id"]]["description"] = skin["description"]
        if "chromas" in skin:
            for chroma in skin["chromas"]:
                championSkins_hashtable[chroma["id"]] = {}
                championSkins_hashtable[chroma["id"]]["name"] = chroma["name"]
                for desc in chroma["descriptions"]:
                    if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1:
                        championSkins_hashtable[chroma["id"]]["description"] = desc["description"]
                        break
                else:
                    championSkins_hashtable[chroma["id"]]["description"] = ""
        if "questSkinInfo" in skin:
            for tier in skin["questSkinInfo"]["tiers"]:
                championSkins_hashtable[tier["id"]] = {}
                championSkins_hashtable[tier["id"]]["name"] = tier["name"]
                championSkins_hashtable[tier["id"]]["description"] = tier["description"]
    companions_hashtable = {}
    for companion in companions_initial:
        companions_hashtable[companion["itemId"]] = {}
        companions_hashtable[companion["itemId"]]["name"] = companion["name"]
        companions_hashtable[companion["itemId"]]["description"] = companion["description"]
    nexusfinishers_hashtable = {}
    for nexusfinisher in nexusfinishers_initial:
        nexusfinishers_hashtable[nexusfinisher["itemId"]] = {}
        nexusfinishers_hashtable[nexusfinisher["itemId"]]["name"] = nexusfinisher["translatedName"]
        nexusfinishers_hashtable[nexusfinisher["itemId"]]["description"] = nexusfinisher["translatedDescription"]
    statstones_hashtable = {}
    for statstone in statstones_initial["packData"]:
        statstones_hashtable[statstone["itemId"]] = {}
        statstones_hashtable[statstone["itemId"]]["name"] = statstone["name"]
        statstones_hashtable[statstone["itemId"]]["description"] = statstone["description"]
    strawberryBoons_hashtable = {} #注意，PVE模式的相关索引都是识别码（Note that index of PBE mode data is itemInstanceId）
    strawberryLoadoutItems_hashtable = {}
    strawberryMaps_hashtable = {}
    for strawberryMap in strawberryHub_initial[0]["MapDisplayInfoList"]:
        strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]] = {}
        strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]]["name"] = strawberryMap["value"]["Name"]
        strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]]["description"] = strawberryMap["value"]["Bark"]
    for ProgressGroup in strawberryHub_initial[0]["ProgressGroups"]:
        for Milestone in ProgressGroup["value"]["Milestones"]:
            for Property in Milestone["value"]["Properties"]:
                for Reward in Property["Rewards"]:
                    if all(key in Reward for key in ["Title", "Details", "ItemId", "ItemType"]) and "CapInventoryTypeId" in Reward["ItemType"]:
                        if Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_BOON"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryBoons_hashtable:
                                if not "name" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["name"] == "":
                                    strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryBoons_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                            else:
                                strawberryBoons_hashtable[Reward["ItemId"]] = {}
                                strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                strawberryBoons_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                        elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                                if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                                    strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                            else:
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {}
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                        elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                                if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here suppose an empty dictionary has been created for this map before）
                                    strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryMaps_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                                else:
                                    strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + Property["Name"]
                            else:
                                strawberryMaps_hashtable[Reward["ItemId"]] = {}
                                strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                strawberryMaps_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
    for PowerUpGroup in strawberryHub_initial[0]["PowerUpGroups"]:
        for Boon in PowerUpGroup["value"]["Boons"]:
            if Boon["value"]["ContentId"] in strawberryBoons_hashtable:
                if not "name" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] == "":
                    strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] = PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"]
                if not "description" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] == "":
                    strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] = PowerUpGroup["value"]["Description"]
            else:
                strawberryBoons_hashtable[Boon["value"]["ContentId"]] = {}
                strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] = PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"]
                strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] = PowerUpGroup["value"]["Description"]
    for EoGNarrativeBark in strawberryHub_initial[0]["EoGNarrativeBarks"]:
        for Reward in EoGNarrativeBark["value"]["RewardGroup"]["Rewards"]:
            if all(key in Reward for key in ["Title", "Details", "ItemId", "ItemType"]) and "CapInventoryTypeId" in Reward["ItemType"]:
                if Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_BOON"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryBoons_hashtable:
                        if not "name" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["name"] == "":
                            strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryBoons_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryBoons_hashtable[Reward["ItemId"]] = {}
                        strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        strawberryBoons_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                        if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                            strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {}
                        strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                        if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here suppose an empty dictionary has been created for this map before）
                            strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryMaps_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                        # else: #实际上在遍历模式进程分组时已经添加过地图激活要求信息了（Actually, when traversing the ProgressGroups, the program has added information of the requirement to activate maps）
                        #     strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryMaps_hashtable[Reward["ItemId"]] = {}
                        strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        strawberryMaps_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
    summonerEmotes_hashtable = {}
    for emote in summonerEmotes_initial:
        summonerEmotes_hashtable[emote["id"]] = {}
        summonerEmotes_hashtable[emote["id"]]["name"] = emote["name"]
        summonerEmotes_hashtable[emote["id"]]["description"] = emote["description"]
    summonerIcons_hashtable = {}
    for icon in summonerIcons_initial:
        summonerIcons_hashtable[icon["id"]] = {}
        summonerIcons_hashtable[icon["id"]]["name"] = icon["title"]
        for desc in icon["descriptions"]:
            if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1: #为简化代码，目前仅统计守卫（眼）在拳头大区的简介。有些简介是非空字符串，但是实际上是一堆空格（To simplify the code, only riot descriptions of wards are counted. Some descriptions are indeed non-empty strings but actually a bunch of spaces）
                summonerIcons_hashtable[icon["id"]]["description"] = desc["description"]
                break
        else:
            summonerIcons_hashtable[icon["id"]]["description"] = ""
    tftdamageskins_hashtable = {}
    for skin in tftdamageskins_initial:
        tftdamageskins_hashtable[skin["itemId"]] = {}
        tftdamageskins_hashtable[skin["itemId"]]["name"] = skin["name"]
        tftdamageskins_hashtable[skin["itemId"]]["description"] = skin["description"]
    tftmapskins_hashtable = {}
    for skin in tftmapskins_initial:
        tftmapskins_hashtable[skin["itemId"]] = {}
        tftmapskins_hashtable[skin["itemId"]]["name"] = skin["name"]
        tftmapskins_hashtable[skin["itemId"]]["description"] = skin["description"]
    tftplaybooks_hashtable = {}
    for tftplaybook in tftplaybooks_initial:
        tftplaybooks_hashtable[tftplaybook["itemId"]] = {}
        tftplaybooks_hashtable[tftplaybook["itemId"]]["name"] = tftplaybook["translatedName"]
        tftplaybooks_hashtable[tftplaybook["itemId"]]["description"] = tftplaybook["translatedDescription"]
    tftzoomskins_hashtable = {}
    for skin in tftzoomskins_initial:
        tftzoomskins_hashtable[skin["itemId"]] = {}
        tftzoomskins_hashtable[skin["itemId"]]["name"] = skin["name"]
        tftzoomskins_hashtable[skin["itemId"]]["description"] = skin["description"]
    wardSkins_hashtable = {}
    for skin in wardSkins_initial:
        wardSkins_hashtable[skin["id"]] = {}
        wardSkins_hashtable[skin["id"]]["name"] = skin["name"]
        wardSkins_hashtable[skin["id"]]["description"] = skin["description"]
    ##以下类型的藏品在商品中也没有记录名称，需要借助其它接口来获取其名称（Collection items of the following types aren't recorded the names in catalog, so other APIs are required to get their names）
    titles_all = await (await connection.request("GET", "/lol-challenges/v2/titles/all")).json()
    titles_hashtable = {}
    for title in titles_all.values():
        titles_hashtable[title["itemId"]] = {}
        titles_hashtable[title["itemId"]]["name"] = title["name"]
        titles_hashtable[title["itemId"]]["description"] = title["challengeTitleData"]["challengeDescription"] if title["challengeTitleData"] != None and "challengeDescription" in title["challengeTitleData"] else ""
    regaliaBanners = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_BANNER")).json()
    regaliaBanners_hashtable = {}
    for bannerId in regaliaBanners:
        regaliaBanners_hashtable[int(regaliaBanners[bannerId]["items"][0]["id"])] = {}
        regaliaBanners_hashtable[int(regaliaBanners[bannerId]["items"][0]["id"])]["name"] = regaliaBanners[bannerId]["items"][0]["localizedName"]
        regaliaBanners_hashtable[int(regaliaBanners[bannerId]["items"][0]["id"])]["description"] = regaliaBanners[bannerId]["items"][0]["localizedDescription"]
    regaliaCrests = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_CREST")).json()
    hashtable_dicts = {"CHAMPION_SKIN": championSkins_hashtable, "COMPANION": companions_hashtable, "NEXUS_FINISHER": nexusfinishers_hashtable, "STATSTONE": statstones_hashtable, "STRAWBERRY_BOON": strawberryBoons_hashtable, "STRAWBERRY_LOADOUT_ITEM": strawberryLoadoutItems_hashtable, "STRAWBERRY_MAP": strawberryMaps_hashtable, "EMOTE": summonerEmotes_hashtable, "SUMMONER_ICON": summonerIcons_hashtable, "TFT_DAMAGE_SKIN": tftdamageskins_hashtable, "TFT_MAP_SKIN": tftmapskins_hashtable, "TFT_PLAYBOOK": tftplaybooks_hashtable, "TFT_ZOOM_SKIN": tftzoomskins_hashtable, "WARD_SKIN": wardSkins_hashtable, "ACHIEVEMENT_TITLE": titles_hashtable, "REGALIA_BANNER": regaliaBanners_hashtable}
    #定义藏品数据结构（Define the collection item data structure）
    collection_header = {"expirationDate": "租赁到期时间", "f2p": "免费使用", "inventoryType": "道具类型", "itemId": "序号", "loyalty": "", "loyaltySources": "", "owned": "已拥有", "ownershipType": "拥有权", "purchaseDate": "购买时间", "quantity": "数量", "rental": "租借中", "usedInGameDate": "上次使用时间", "uuid": "唯一识别码", "wins": "使用该道具可获得增益的胜场数", "isVintage": "典藏皮肤", "name": "名称"}
    collection_header_keys = list(collection_header.keys())
    collection_data = {}
    for i in range(len(collection_header)):
        key = collection_header_keys[i]
        collection_data[key] = []
    #数据整理核心部分（Data assignment - core part）
    logPrint("[get_collection]正在整理数据…… | Sorting data ...", print_time = True)
    for item_index in range(len(collection)):
        item = collection[item_index]
        # logPrint("数据整理进度（Data sorting process）：%d/%d" %(item_index + 1, len(collection)), end = "\r", print_time = True)
        for i in range(len(collection_header)):
            key = collection_header_keys[i]
            if i in {0, 8, 11}: #时间字符串相关键（Time string-related keys）
                collection_data[key].append("") if item[key] == "" else collection_data[key].append("%s-%s-%s %s-%s-%s" %(item[key][:4], item[key][5:7], item[key][8:10], item[key][11:13], item[key][14:16], item[key][17:19])) if "-" in item[key] and ":" in item[key] else collection_data[key].append("%s-%s-%s %s-%s-%s" %(item[key][:4], item[key][4:6], item[key][6:8], item[key][9:11], item[key][11:13], item[key][13:15]))
            # elif i == 2: #道具类型（`inventoryType`）
            #     collection_data[key].append(inventoryType_dict[item[key]])
            # elif i == 7: #拥有权（`ownershipType`）
            #     collection_data[key].append(ownershipType_dict[item[key]])
            elif i == 14: #典藏皮肤（带边框）（`isVintage`）
                collection_data[key].append(item["payload"]["isVintage"]) if item["payload"] and "isVintage" in item["payload"] else collection_data[key].append(False) #没有“是否典藏”选项的默认不是典藏（An item without the "isVintage" key can't be vintage）
            elif i == 15: #名称（`name`）
                if (item["inventoryType"], item["itemId"]) in collection_hashtable:
                    name = collection_hashtable[(item["inventoryType"], item["itemId"])]
                elif item["inventoryType"] in hashtable_dicts: #商品中可能不包含藏品（A collection item may not be contained in the collection）
                    if item["inventoryType"] in {"STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP"} and item["uuid"] in hashtable_dicts[item["inventoryType"]]:
                        name = hashtable_dicts[item["inventoryType"]][item["uuid"]]["name"]
                    elif item["itemId"] in hashtable_dicts[item["inventoryType"]]:
                        name = hashtable_dicts[item["inventoryType"]][item["itemId"]]["name"]
                    else:
                        name = ""
                else:
                    name = ""
                collection_data[key].append(name)
            else:
                collection_data[key].append(item[key])
    #数据框列序整理（Dataframe column ordering）
    collection_statistics_output_order = [15, 9, 3, 2, 12, 6, 10, 1, 7, 8, 0, 14, 13, 11]
    collection_data_organized = {}
    for i in collection_statistics_output_order:
        key = collection_header_keys[i]
        collection_data_organized[key] = collection_data[key]
    logPrint("[get_collection]正在构建数据框…… | Creating the dataframe ...", print_time = True)
    collection_df = pandas.DataFrame(data = collection_data_organized)
    logPrint("[get_collection]正在优化逻辑值显示…… | Optimizing the display of boolean values ...", print_time = True)
    for column in collection_df:
        if collection_df[column].dtype == "bool":
            collection_df[column] = collection_df[column].astype(str)
            for i in range(len(collection_df)):
                collection_df.loc[i, column] = "√" if collection_df[column][i] == "True" else ""
    collection_df = pandas.concat([pandas.DataFrame([collection_header])[collection_df.columns], collection_df], ignore_index = True)
    logPrint("[get_collection]数据框构建完成。 | Dataframe created.", print_time = True)
    return collection_df

async def get_available_bots(connection):
    available_bots = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")).json()
    availableBot_data = {}
    for i in range(len(availableBot_header_keys)):
        key = availableBot_header_keys[i]
        availableBot_data[key] = []
    for bot in available_bots:
        for i in range(len(availableBot_header_keys)):
            key = availableBot_header_keys[i]
            if i <= 3:
                availableBot_data[key].append(bot[key])
            else:
                availableBot_data[key].append(LoLChampions[bot["id"]][key] if bot["id"] in LoLChampions else "")
    availableBot_statistics_output_order = [2, 3, 5, 4, 1]
    availableBot_data_organized = {}
    for i in availableBot_statistics_output_order:
        key = availableBot_header_keys[i]
        availableBot_data_organized[key] = availableBot_data[key]
    availableBot_df = pandas.DataFrame(data = availableBot_data_organized)
    for column in availableBot_df:
        if availableBot_df[column].dtype == "bool":
            availableBot_df[column] = availableBot_df[column].astype(str)
            for i in range(len(availableBot_df)):
                availableBot_df.loc[i, column] = "√" if availableBot_df[column][i] == "True" else ""
    availableBot_df = pandas.concat([pandas.DataFrame([availableBot_header])[availableBot_df.columns], availableBot_df], ignore_index = True)
    return availableBot_df

async def test_bot(connection):
    bot_championIds = []
    logPrint("正在统计具有电脑模型的英雄……请勿退出房间！\nCounting botEnabled champions ... Please don't exit the lobby!\n")
    custom = {
        "customGameLobby": {
            "configuration": {
                "gameMode": "PRACTICETOOL",
                "gameMutator": "",
                "gameServerRegion": "",
                "mapId": 11,
                "mutators": {
                    "id": 1
                },
            "spectatorPolicy": "AllAllowed",
            "teamSize": 5
            },
            "lobbyName": "可用电脑英雄测试（程序结束前请勿退出）",
            "lobbyPassword": ""
        },
        "isCustom": True
    }
    retry = 0
    response = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = custom))
    if isinstance(response, dict) and "errorCode" in response:
        logPrint(response)
        logPrint("测试房间创建失败。请检查您的游戏状态。\nTest lobby creation failed. Please check your gameflow phase.")
    else:
        logPrint("championId\tname\ttitle\talias")
        count = 0
        for championId in LoLChampions:
            botUuid = str(uuid.uuid4())
            bot = {"championId": championId, "botDifficulty": "RSINTERMEDIATE", "teamId": "200", "position": "TOP", "botUuid": botUuid}
            response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
            time.sleep(GLOBAL_RESPONSE_LAG) #由于服务器响应速度原因，从添加电脑到房间信息更新，需要0.2秒的缓冲时间（0.2s buffer time is needed between adding a bot and updating the lobby information due to the server response speed）
            lobby = await(await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            if len(lobby["gameConfig"]["customTeam200"]) == 1 and lobby["gameConfig"]["customTeam200"][0]["botChampionId"] == championId:
                bot_championIds.append(championId)
                logPrint("%d\t%s\t%s\t%s" %(championId, LoLChampions[championId]["name"], LoLChampions[championId]["title"], LoLChampions[championId]["alias"]))
                if championId != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                    count += 1
                response = await (await connection.request("DELETE", "/lol-lobby/v1/lobby/custom/bots/%s/%s/200" %(lobby["gameConfig"]["customTeam200"][0]["botId"], botUuid))).json()
        logPrint("\n统计完毕，共%d名英雄。\nCount finished! There're %d champions in total." %(count, count))
    return bot_championIds

async def sort_lobby_members(connection):
    member_data = {}
    for i in range(len(member_header_keys)):
        key = member_header_keys[i]
        member_data[key] = []
    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    if not (isinstance(lobby_information, dict) and "errorCode" in lobby_information):
        members = []
        #思考下面为什么要这样处理成员顺序（Think why the members are ordered in the following pattern）
        for member in lobby_information["gameConfig"]["customTeam100"]:
            if not member in members:
                members.append(member)
        for member in lobby_information["gameConfig"]["customTeam200"]:
            if not member in members:
                members.append(member)
        for member in lobby_information["members"]:
            if not member in members:
                members.append(member)
        for member in members:
            member_info_recapture = 0
            member_info = await get_info(connection, member["puuid"])
            while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                logPrint(member_info["message"])
                member_info_recapture += 1
                logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of member (puuid: %s) capture failed! Recapturing this member's information ... Times tried: %d" %(member["puuid"], member_info_recapture, member["puuid"], member_info_recapture))
                member_info = await get_info(connection, member["puuid"])
            if not member_info["info_got"]:
                logPrint(member_info["message"])
                logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！\nInformation of member (puuid: %s) capture failed!" %(member["puuid"], member["puuid"]))
            for i in range(len(member_header_keys)):
                key = member_header_keys[i]
                if i >= 34 and i <= 36: #电脑玩家英雄相关键（Bot champion-related keys）
                    member_data[key].append(LoLChampions[member["botChampionId"]][key.split("_")[1]] if member["botChampionId"] in LoLChampions else "")
                elif i == 37: #电脑玩家难度等级（`botDifficulty_localized`）
                    member_data[key].append(botDifficulty_dict[member["botDifficulty"]])
                elif i == 38: #电脑玩家分路（`botPosition_localized`）
                    member_data[key].append(position_dict[member["botPosition"]])
                elif i == 39: #首选（`primaryPosition`）
                    member_data[key].append(position_dict[member["firstPositionPreference"]])
                elif i == 40: #次选（`secondaryPosition`）
                    member_data[key].append(position_dict[member["secondPositionPreference"]])
                elif i == 41: #无尽狂潮地图名称（`strawberryMapName`）
                    member_data[key].append(strawberryMaps[member["strawberryMapId"]]["value"]["name"] if member["strawberryMapId"] in strawberryMaps else "")
                elif i in [42, 43]: #召唤师图标相关键（Summoner icon-related keys）
                    member_data[key].append(summonerIcons[member["summonerIconId"]].get(key.split("_")[1], "") if member["summonerIconId"] in summonerIcons else "")
                elif i >= 44: #召唤师信息相关键（Summoner information-related keys）
                    member_data[key].append(member_info["body"][key] if member_info["info_got"] else "")
                else:
                    member_data[key].append(member[key])
    member_statistics_output_order = [32, 30, 44, 45, 29, 22, 31, 28, 42, 43, 18, 19, 33, 15, 39, 24, 40, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 27, 16, 21, 26, 41, 23, 25, 20, 17, 10, 12, 14, 34, 36, 35, 11, 37, 13, 38]
    member_data_organized = {}
    for i in member_statistics_output_order:
        key = member_header_keys[i]
        member_data_organized[key] = member_data[key]
    member_df = pandas.DataFrame(data = member_data_organized)
    for column in member_df:
        if member_df[column].dtype == "bool":
            member_df[column] = member_df[column].astype(str)
            for i in range(len(member_df)):
                member_df.loc[i, column] = "√" if member_df[column][i] == "True" else ""
    member_df = pandas.concat([pandas.DataFrame([member_header])[member_df.columns], member_df], ignore_index = True)
    return member_df

async def lobby_simulation(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t管理小队（Manage a party）\n2\t管理自定义房间（Manage a custom lobby）\n3\t邀请玩家（Invite to game）\n4\t聊天（Chat）\n5\t成员管理（Manage members）\n6\t输出房间信息（Print lobby information）\n7\t处理邀请（Handle invitations）\n8\t加入小队或自定义房间（Join party/lobby）\n9\t退出房间（Exit the party/lobby）\n10\t其它（Others）\n11\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option == "-1": #查看接口返回结果，用于内部调试（Check endpoint results, used for debugging）
            logPrint('''请选择一个房间相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a lobby-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t检查房间是否呈现自动补位提示（Check if the lobby displays the autofill tolltip）\n2\t设置房间是否呈现自动补位提示（Set whether the lobby displays the autofill tooltip）\n3\t退出冠军杯赛队伍（Quit a Clash party）\n4\t加入冠军杯赛队伍（Join a Clash party）\n5\t获取所有公开的自定义房间数据（Get all public custom lobby data）\n6\t获取某个公开的自定义房间数据（Get data of a public custom lobby）\n7\t加入一个公开的自定义房间（Join a public custom lobby）\n8\t刷新公开自定义房间数据（Refresh public custom lobby data）\n9\t检查当前房间是否可用（Check if the current lobby is available）\n10\t查看当前房间的倒计时（Check the current lobby's countdown）\n11\t添加一名电脑玩家（Add a bot player）\n12\t编辑一名电脑玩家的参数（Edit a bot player's parameters）\n13\t删除一名电脑玩家（Remove a bot player）\n14\t强制退出英雄选择阶段（Force to leave the champ select stage）\n15\t进入自定义对局的英雄选择阶段（Enter a custom game's champ select stage）\n16\t加入自定义房间的另外一支队伍（Join another team of a custom lobby）\n17\t查看当前房间发出的所有邀请信息（Check all invitations sent out from the current lobby）\n18\t向一名玩家发送邀请（Send an invitation to a player）\n19\t获取一个邀请信息（Get an invitation's information）\n20\t获取用户的快速模式配置（Get the user's swiftplay loadout）\n21\t设置用户的快速模式配置（Set the user's switfplay loadout）\n22\t设置用户的符文（Set the user's perks）\n23\t设置用户的首选和次选位置（Set the user's primary and secondary positions）\n24\t更改小队成员的身份（Change the role of a member in a party）\n25\t更改小队可用性（Change the availability of a party）\n26\t查看小队的游戏模式（Change the party's game mode）\n27\t批量修改小队配置（Configure party settings in batches）\n28\t获取小队成员信息（Get party member information）\n29\t更改队列游戏模式（Change a queue）\n30\t重新准备就绪（Prepare for queue entry again）\n31\t查看小队奖励（Check party rewards）\n32\t加入冠军杯赛队伍（Join a Clash party）\n33\t获取小队聊天成员信息（Get the party member information for communication）\n34\t获取小队聊天密钥（Get the token for party communication）\n35\t获取用户加入游戏队列资格验证哈希值（Get the hash value of the user's eligilbility to join the queue）\n36\t检查用户游戏队列资格初始化进度（Check the progress of lobby eligibility configuration initialization）\n37\t查看所有游戏模式的小队可用性（Check availability of parties of all game modes）\n38\t查看所有游戏模式的小队可用性（Check availability of parties of all game modes）\n39\t在对局结算阶段邀请玩家至小队（Invite players to party at the end of a game）\n40\t退出当前房间（Exit the current lobby）\n☆41\t获取当前房间信息（Get the current lobby information）\n42\t创建房间（Create a lobby）\n43\t获取当前房间可以添加的电脑玩家（Get bot champions available to add into the current lobby）\n44\t查看当前房间是否允许添加电脑玩家（Check if the current lobby allows addition of bot players）\n45\t查看当前房间发出的所有邀请信息（Check all invitations sent out from the current lobby）\n46\t邀请玩家至房间（Invite players to game）\n47\t停止寻找对局（Stop finding match）\n48\t寻找对局（Find match）\n49\t获取寻找对局状态（Get match finding state）\n50\t设置快速模式就绪状态（Toggle ready or not in swiftplay mode）\n51\t查看房间内成员信息（Check the information of members in the current lobby）\n52\t为一名小队成员提供房间邀请权限（Grant invite priviledge for a party member）\n53\t将一名成员移出房间（Kick a member out of the party）\n54\t将成员晋升为小队拥有者（Promote a member as the party owner）\n55\t撤回一名小队成员的邀请权限（Revoke invite priviledge from a party member）\n56\t设置用户的首选和次选位置（Set the user's primary and secondary positions）\n57\t设置小队可见性（Toggle party open or closed）\n58\t设置用户的快速模式配置（Set the user's switfplay loadout）\n59\t选择无尽狂潮地图（Select a strawberry map）\n60\t选择斗魂竞技场槽位（Select an Arena lobby slot）\n61\t切换队伍（Switch team）\n62\t快速寻找对局（Quickly find match）\n63\t查看房间内的通知（Check notifications in the lobby）\n64\t向房间内发送通知（Send notifications into the lobby）\n65\t移除房间内的通知（Delete a piece of notification from the lobby）\n!66\t（未知）激活阵容匹配队列重载【(Unknown) Activate game mode override for team builder queues】\n67\t检查当前队列是否可用（Check if the current party can be started）\n68\t加入一个小队（Join a party）\n69\t查看小队成员在对局结算阶段的状态（Check the status of party members at the end of a game）\n70\t再来一局（Play again）\n71\t返回大厅（Return to the home page）\n72\t查看收到的邀请（Check received invitations）\n73\t接受一个小队/房间邀请（Accept a party/lobby invitation）\n74\t拒绝一个小队/房间邀请（Decline a party/lobby invitation）\n75\t查看账号注册进度（Check account registration progress）''')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection)
                elif suboption == "0":
                    break
                elif suboption in list(map(str, range(1, 76))):
                    if suboption == "1":
                        response = await (await connection.request("GET", "/lol-lobby/v1/autofill-displayed")).json()
                    elif suboption == "2":
                        response = await (await connection.request("PUT", "/lol-lobby/v1/autofill-displayed")).json()
                    elif suboption == "3":
                        response = await (await connection.request("DELETE", "/lol-lobby/v1/clash")).json()
                    elif suboption == "4":
                        logInput("请输入要加入的冠军杯赛代码：\nPlease input the clash id to join:\ntoken = ", end = "")
                        body = logInput()
                        response = await (await connection.request("POST", "/lol-lobby/v1/clash", data = body)).json()
                    elif suboption == "5":
                        response = await (await connection.request("GET", "/lol-lobby/v1/custom-games")).json()
                    elif suboption == "6":
                        logPrint("请输入小队编号：\nPlease input the partyId:")
                        partyId = logInput()
                        response = await (await connection.request("GET", f"/lol-lobby/v1/custom-games/{partyId}")).json()
                    elif suboption == "7":
                        logPrint("请输入小队编号：\nPlease input the partyId:")
                        partyId = logInput()
                        response = await (await connection.request("GET", f"/lol-lobby/v1/custom-games/{partyId}/join")).json()
                    elif suboption == "8":
                        response = await (await connection.request("POST", "/lol-lobby/v1/custom-games/refresh")).json()
                    elif suboption == "9":
                        response = await (await connection.request("GET", "/lol-lobby/v1/lobby/availability")).json()
                    elif suboption == "10":
                        response = await (await connection.request("GET", "/lol-lobby/v1/lobby/countdown")).json()
                    elif suboption == "11":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"championId": 0, "botDifficulty": "RSWARMINTRO", "teamId": "string", "position": "string", "botUuid": "string"}\nparameters = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "12":
                        logPrint("请输入要修改的电脑玩家编号：\nPlease input the botId of the bot to change:\nsummonerInternalName = ", end = "")
                        summonerInternalName = logInput()
                        logPrint("请输入要修改的电脑玩家通用唯一识别码：\nPlease input the botUuid of the bot to change:\nbotUuidToDelete = ", end = "")
                        botUuidToDelete = logInput()
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"championId": 0, "botDifficulty": "RSWARMINTRO", "teamId": "string", "position": "string", "botUuid": "string"}\nparameters = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots/{summonerInternalName}/{botUuidToDelete}")).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "13":
                        logPrint("请输入要删除的电脑玩家编号：\nPlease input the botId of the bot to remove:\nsummonerInternalName = ", end = "")
                        summonerInternalName = logInput()
                        logPrint("请输入要删除的电脑玩家通用唯一识别码：\nPlease input the botUuid of the bot to remove:\nbotUuidToDelete = ", end = "")
                        botUuidToDelete = logInput()
                        logPrint("请输入要删除的电脑玩家所在阵营代号：\nPlease input the teamId of the bot to remove:\nteamId = ", end = "")
                        teamId = logInput()
                        response = await (await connection.request("DELETE", f"/lol-lobby/v1/lobby/custom/bots/{summonerInternalName}/{botUuidToDelete}/{teamId}")).json()
                    elif suboption == "14":
                        response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/cancel-champ-select")).json()
                    elif suboption == "15":
                        response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/start-champ-select")).json()
                    elif suboption == "16":
                        response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/switch-teams")).json()
                    elif suboption == "17":
                        response = await (await connection.request("GET", "/lol-lobby/v1/lobby/invitations")).json()
                    elif suboption == "18":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"id": "string", "fromSummonerId": 0, "toSummonerId": 0, "state": "Error", "errorType": "string", "timestamp": "string", "invitationMetaData": {"additionalProp1": {}}, "eligibility": {"queueId": 0, "eligible": True, "restrictions": [{"restrictionCode": "FullPartyUnranked", "restrictionArgs": {"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"}, "expiredTimestamp": 0, "summonerIds": [0], "summonerIdsString": "string", "puuids": ["string"]}]}, "fromSummonerName": "string", "toSummonerName": "string"}\ninvitation = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v1/lobby/invitations")).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "19":
                        logPrint("请输入邀请编号：\nPlease input the id of the invitation:\nid = ", end = "")
                        invitationId = logInput()
                        response = await (await connection.request("GET", f"/lol-lobby/v1/lobby/invitations/{invitationId}")).json()
                    elif suboption == "20":
                        response = await (await connection.request("GET", "/lol-lobby/v1/lobby/members/localMember/player-slots")).json()
                    elif suboption == "21":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n[{"championId": 0, "skinId": 0, "positionPreference": "string", "perks": "string", "spell1": 0, "spell2": 0}]\ninvitation = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v1/lobby/members/localMember/player-slots")).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "22":
                        logPrint("请输入槽位序号：\nPlease input the index of your slot:\nslotsIndex = ", end = "")
                        slotsIndex = logInput()
                        logPrint("请输入含有符文信息的字符串：\nPlease input a string that contains perk information:\nperksString = ", end = "")
                        perksString = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v1/lobby/members/localMember/player-slots/{slotsIndex}/{perksString}")).json()
                    elif suboption == "23":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"firstPreference": "string", "secondPreference": "string"}\npositionPreferences = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v1/lobby/members/localMember/position-preferences", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "24":
                        logPrint("请输入小队编号：\nPlease input the partyId:\npartyId = ", end = "")
                        partyId = logInput()
                        logPrint("请输入要变更身份的玩家通用唯一识别码：\nPlease input the puuid of the player to change role:\npuuid = ", end = "")
                        puuid = logInput()
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"MEMBER"\n"LEADER"\nrole = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", f"/lol-lobby/v1/parties/{partyId}/members/{puuid}/role", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "25":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"0"\nactive = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v1/parties/active", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "26":
                        response = await (await connection.request("GET", "/lol-lobby/v1/parties/gamemode")).json()
                    elif suboption == "27":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"positionPref": ["string"], "properties": {"additionalProp1": {}}, "memberData": {"additionalProp1": {}}, "playerSlots": [{"championId": 0, "skinId": 0, "positionPreference": "string", "perks": "string", "spell1": 0, "spell2": 0}], "subteamData": {"subteamIndex": 0, "intraSubteamPosition": 0}}\nmetadata = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v1/parties/metadata", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "28":
                        response = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
                    elif suboption == "29":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"0"\nqueueId = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v1/parties/queue", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "30":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"0"\nready = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("GET", "/lol-lobby/v1/parties/ready", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "31":
                        response = await (await connection.request("GET", "/lol-lobby/v1/party-rewards")).json()
                    elif suboption == "32":
                        logInput("请输入要加入的冠军杯赛代码：\nPlease input the tournament id to join:\nid = ", end = "")
                        tournamentId = logInput()
                        response = await (await connection.request("GET", f"/lol-lobby/v1/tournaments/{tournamentId}/join")).json()
                    elif suboption == "33":
                        response = await (await connection.request("GET", "/lol-lobby/v2/comms/members")).json()
                    elif suboption == "34":
                        response = await (await connection.request("GET", "/lol-lobby/v2/comms/token")).json()
                    elif suboption == "35":
                        response = await (await connection.request("GET", "/lol-lobby/v2/eligibility/game-select-eligibility-hash")).json()
                    elif suboption == "36":
                        response = await (await connection.request("GET", "/lol-lobby/v2/eligibility/initial-configuration-complete")).json()
                    elif suboption == "37":
                        response = await (await connection.request("POST", "/lol-lobby/v2/eligibility/party")).json()
                    elif suboption == "38":
                        response = await (await connection.request("POST", "/lol-lobby/v2/eligibility/self")).json()
                    elif suboption == "39":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n[{"invitationId": "string", "toSummonerId": 0, "state": "Error", "timestamp": "string", "toSummonerName": "string", "invitationType": "party"}]\ninvitations = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v2/eog-invitations", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "40":
                        response = await (await connection.request("DELETE", "/lol-lobby/v2/lobby")).json()
                    elif suboption == "41":
                        response = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                    elif suboption == "42":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"queueId": 0, "isCustom": True, "customGameLobby": {"lobbyName": "string", "lobbyPassword": "string", "configuration": {"mapId": 0, "gameMode": "string", "mutators": {"id": 0, "name": "string", "maxAllowableBans": 0, "allowTrades": True, "exclusivePick": True, "duplicatePick": True, "teamChampionPool": True, "crossTeamChampionPool": True, "advancedLearningQuests": True, "battleBoost": True, "deathMatch": True, "doNotRemove": True, "learningQuests": True, "onboardCoopBeginner": True, "reroll": True, "mainPickTimerDuration": 0, "postPickTimerDuration": 0, "banTimerDuration": 0, "pickMode": "string", "banMode": "string", "gameModeOverride": "string", "numPlayersPerTeamOverride": 0 }, "gameTypeConfig": {"id": 0, "name": "string", "maxAllowableBans": 0, "allowTrades": True, "exclusivePick": True, "duplicatePick": True, "teamChampionPool": True, "crossTeamChampionPool": True, "advancedLearningQuests": True, "battleBoost": True, "deathMatch": True, "doNotRemove": True, "learningQuests": True, "onboardCoopBeginner": True, "reroll": True, "mainPickTimerDuration": 0, "postPickTimerDuration": 0, "banTimerDuration": 0, "pickMode": "string", "banMode": "string", "gameModeOverride": "string", "numPlayersPerTeamOverride": 0}, "spectatorPolicy": "AllAllowed", "teamSize": 0, "maxPlayerCount": 0, "tournamentGameMode": "string", "tournamentPassbackUrl": "string", "tournamentPassbackDataPacket": "string", "gameServerRegion": "string", "spectatorDelayEnabled": True, "hidePublicly": True}, "teamOne": [{"id": 0, "isOwner": True, "isSpectator": True, "canInviteOthers": True, "positionPreferences": {"firstPreference": "string", "secondPreference": "string"}, "excludedPositionPreference": "string", "summonerInternalName": "string", "showPositionExcluder": True, "autoFillEligible": True, "autoFillProtectedForStreaking": True, "autoFillProtectedForPromos": True, "autoFillProtectedForSoloing": True, "isBot": True, "botDifficulty": "RSWARMINTRO", "botChampionId": 0, "position": "string", "botUuid": "string"}], "teamTwo": [{"id": 0, "isOwner": True, "isSpectator": True, "canInviteOthers": True, "positionPreferences": {"firstPreference": "string", "secondPreference": "string"}, "excludedPositionPreference": "string", "summonerInternalName": "string", "showPositionExcluder": True, "autoFillEligible": True, "autoFillProtectedForStreaking": True, "autoFillProtectedForPromos": True, "autoFillProtectedForSoloing": True, "isBot": True, "botDifficulty":  "RSWARMINTRO", "botChampionId": 0, "position": "string", "botUuid": "string"}], "spectators": [{"id": 0, "isOwner": True, "isSpectator": True, "canInviteOthers": True, "positionPreferences": {"firstPreference": "string", "secondPreference": "string"}, "excludedPositionPreference": "string", "summonerInternalName": "string", "showPositionExcluder": True, "autoFillEligible": True, "autoFillProtectedForStreaking": True, "autoFillProtectedForPromos": True, "autoFillProtectedForSoloing": True, "isBot": True, "botDifficulty": "RSWARMINTRO", "botChampionId": 0, "position": "string", "botUuid": "string"}], "practiceGameRewardsDisabledReasons": ["string"], "gameId": 0}, "gameCustomization": {"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"}}\nlobbyChange = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "43":
                        response = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")).json()
                    elif suboption == "44":
                        response = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/bots-enabled")).json()
                    elif suboption == "45":
                        response = await (await connection.request("GET", "/lol-lobby/v2/lobby/invitations")).json()
                    elif suboption == "46":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n[{"invitationId": "string", "toSummonerId": 0, "state": "Error", "timestamp": "string", "toSummonerName": "string", "invitationType": "party"}]\ninvitations = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v2/lobby/invitations", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "47":
                        response = await (await connection.request("DELETE", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                    elif suboption == "48":
                        response = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                    elif suboption == "49":
                        response = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
                    elif suboption == "50":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"}\nmemberData = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/memberData", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "51":
                        response = await (await connection.request("GET", "/lol-lobby/v2/lobby/members")).json()
                    elif suboption == "52":
                        logPrint("请输入房间内成员的召唤师序号：\nPlease input the summonerId of a member in the lobby:\nsummonerId", end = "")
                        member_summonerId = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/grant-invite")).json()
                    elif suboption == "53":
                        logPrint("请输入房间内成员的召唤师序号：\nPlease input the summonerId of a member in the lobby:\nsummonerId", end = "")
                        member_summonerId = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/kick")).json()
                    elif suboption == "54":
                        logPrint("请输入房间内成员的召唤师序号：\nPlease input the summonerId of a member in the lobby:\nsummonerId", end = "")
                        member_summonerId = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/promote")).json()
                    elif suboption == "55":
                        logPrint("请输入房间内成员的召唤师序号：\nPlease input the summonerId of a member in the lobby:\nsummonerId", end = "")
                        member_summonerId = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/revoke-invite")).json()
                    elif suboption == "56":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"firstPreference": "string", "secondPreference": "string"}\npositionPreferences = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/members/localMember/position-preferences", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "57":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"open"\n"closed"\npartyType = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/partyType", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "58":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"}\nquickplayMemberData = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/quickplayMemberData", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "59":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"contentId": "string", "itemId": 0}\nmapUpdate = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/strawberryMapId", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "60":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"subteamIndex": 0, "intraSubteamPosition": 0}\nsubteamData = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/subteamData", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "61":
                        logPrint("请输入队伍代号：\nPlease input the teamId:\nteam = ", end = "")
                        teamId = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/team/{teamId}")).json()
                    elif suboption == "62":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"queueId": 0, "isCustom": True, "customGameLobby": {"lobbyName": "string", "lobbyPassword": "string", "configuration": {"mapId": 0, "gameMode": "string", "mutators": {"id": 0, "name": "string", "maxAllowableBans": 0, "allowTrades": True, "exclusivePick": True, "duplicatePick": True, "teamChampionPool": True, "crossTeamChampionPool": True, "advancedLearningQuests": True, "battleBoost": True, "deathMatch": True, "doNotRemove": True, "learningQuests": True, "onboardCoopBeginner": True, "reroll": True, "mainPickTimerDuration": 0, "postPickTimerDuration": 0, "banTimerDuration": 0, "pickMode": "string", "banMode": "string", "gameModeOverride": "string", "numPlayersPerTeamOverride": 0 }, "gameTypeConfig": {"id": 0, "name": "string", "maxAllowableBans": 0, "allowTrades": True, "exclusivePick": True, "duplicatePick": True, "teamChampionPool": True, "crossTeamChampionPool": True, "advancedLearningQuests": True, "battleBoost": True, "deathMatch": True, "doNotRemove": True, "learningQuests": True, "onboardCoopBeginner": True, "reroll": True, "mainPickTimerDuration": 0, "postPickTimerDuration": 0, "banTimerDuration": 0, "pickMode": "string", "banMode": "string", "gameModeOverride": "string", "numPlayersPerTeamOverride": 0}, "spectatorPolicy": "AllAllowed", "teamSize": 0, "maxPlayerCount": 0, "tournamentGameMode": "string", "tournamentPassbackUrl": "string", "tournamentPassbackDataPacket": "string", "gameServerRegion": "string", "spectatorDelayEnabled": True, "hidePublicly": True}, "teamOne": [{"id": 0, "isOwner": True, "isSpectator": True, "canInviteOthers": True, "positionPreferences": {"firstPreference": "string", "secondPreference": "string"}, "excludedPositionPreference": "string", "summonerInternalName": "string", "showPositionExcluder": True, "autoFillEligible": True, "autoFillProtectedForStreaking": True, "autoFillProtectedForPromos": True, "autoFillProtectedForSoloing": True, "isBot": True, "botDifficulty": "RSWARMINTRO", "botChampionId": 0, "position": "string", "botUuid": "string"}], "teamTwo": [{"id": 0, "isOwner": True, "isSpectator": True, "canInviteOthers": True, "positionPreferences": {"firstPreference": "string", "secondPreference": "string"}, "excludedPositionPreference": "string", "summonerInternalName": "string", "showPositionExcluder": True, "autoFillEligible": True, "autoFillProtectedForStreaking": True, "autoFillProtectedForPromos": True, "autoFillProtectedForSoloing": True, "isBot": True, "botDifficulty":  "RSWARMINTRO", "botChampionId": 0, "position": "string", "botUuid": "string"}], "spectators": [{"id": 0, "isOwner": True, "isSpectator": True, "canInviteOthers": True, "positionPreferences": {"firstPreference": "string", "secondPreference": "string"}, "excludedPositionPreference": "string", "summonerInternalName": "string", "showPositionExcluder": True, "autoFillEligible": True, "autoFillProtectedForStreaking": True, "autoFillProtectedForPromos": True, "autoFillProtectedForSoloing": True, "isBot": True, "botDifficulty": "RSWARMINTRO", "botChampionId": 0, "position": "string", "botUuid": "string"}], "practiceGameRewardsDisabledReasons": ["string"], "gameId": 0}, "gameCustomization": {"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"}}\nlobbyChange = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v2/matchmaking/quick-search", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "63":
                        response = await (await connection.request("GET", "/lol-lobby/v2/notifications")).json()
                    elif suboption == "64":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"notificationId": "string", "notificationReason": "string", "summonerIds": [0], "timestamp": 0}\nnotification = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v2/notification", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "65":
                        logPrint("请输入要删除的通知编号：\nPlease input the id of the notification to delete:\nnotificationId = ", end = "")
                        notificationId = input()
                        response = await (await connection.request("DELETE", f"/lol-lobby/v2/notification/{notificationId}")).json()
                    elif suboption == "66":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"true"')
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("POST", "/lol-lobby/v2/parties/overrides/EnabledForTeamBuilderQueues", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "67":
                        response = await (await connection.request("GET", "/lol-lobby/v2/party-active")).json()
                    elif suboption == "68":
                        logPrint("请输入您要加入的小队编号：\nPlease input the id of the party you want to join:\npartyId = ", end = "")
                        partyId = input()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                    elif suboption == "69":
                        response = await (await connection.request("GET", "/lol-lobby/v2/party/eog-status")).json()
                    elif suboption == "70":
                        response = await (await connection.request("POST", "/lol-lobby/v2/play-again")).json()
                    elif suboption == "71":
                        response = await (await connection.request("POST", "/lol-lobby/v2/play-again-decline")).json()
                    elif suboption == "72":
                        response = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
                    elif suboption == "73":
                        logPrint("请输入您想要处理的邀请编号：\nPlease input the id of the invitation you want to handle:\ninvitationId = ", end = "")
                        invitationId = input()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/accept")).json()
                    elif suboption == "74":
                        logPrint("请输入您想要处理的邀请编号：\nPlease input the id of the invitation you want to handle:\ninvitationId = ", end = "")
                        invitationId = input()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/decline")).json()
                    else:
                        response = await (await connection.request("GET", "/lol-lobby/v2/registration-status")).json()
                    logPrint(response)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option == "0":
            break
        elif option in ["1", "2", "3", "5", "9"]:
            gameflow_phase = await get_gameflow_phase(connection) #每一个操作都需要保证房间信息是可用的（Each operation requires the lobby information to be available）
            if gameflow_phase == "Lobby":
                lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                if option == "1":
                    if lobby_information["gameConfig"]["isCustom"]:
                        logPrint("自定义房间不支持此选项。\nCustom lobby doesn't support this option.")
                    else:
                        logPrint("请选择一个小队操作：\nPlease select a party operation:\n1\t入队准备（Prepare before in queue）\n2\t查看社交排行榜（Check friends leaderboard）\n3\t改变小队公开性（Toggle party open/closed）\n4\t更换模式（Change mode）\n5\t寻找对局（Find match）")
                        while True:
                            suboption = logInput()
                            if suboption == "":
                                continue
                            elif suboption[0] == "0":
                                break
                            elif suboption[0] == "1":
                                logPrint("请选择一项个人配置：\nPlease select a personal configuration to change:\n1\t选择位置（Select positions）\n2\t设置快速模式英雄选择（Configure quickplay slot）\n3\t设置子阵营（Configure subteam data）\n4\t切换就绪状态（Toggle ready）\n5\t云顶之弈赛前配置（TFT loadouts）")
                                while True:
                                    config = logInput()
                                    if config == "":
                                        continue
                                    elif config[0] == "0":
                                        break
                                    elif config[0] == "1":
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase == "Lobby":
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            if lobby_information["gameConfig"]["showPositionSelector"]:
                                                slotPositions = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY", "FILL"]
                                                logPrint("请选择首选位置：\nPlease select your primary position:\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路/线上（Bottom/Lane）\n5\t辅助（Support）\n6\t补位（Fill）")
                                                back = False
                                                while True:
                                                    position_index = logInput()
                                                    if position_index[0] == "0":
                                                        back = True
                                                        break
                                                    elif position_index == "-1":
                                                        firstPreference = "UNSELECTED" #这里也可以是空字符串（An empty string also works here）
                                                        break
                                                    elif position_index[0] in list(map(str, range(1, 7))):
                                                        position_index = int(position_index[0])
                                                        firstPreference = slotPositions[position_index - 1] #这里也可以是`str(position_index - 1)`（`str(position_index - 1)` also works here）
                                                        break
                                                    else:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                if back:
                                                    logPrint("请选择一项个人配置：\nPlease select a personal configuration to change:\n1\t选择位置（Select positions）\n2\t设置快速模式英雄选择（Configure quickplay slot）\n3\t设置子阵营（Configure subteam data）\n4\t切换就绪状态（Toggle ready）\n5\t云顶之弈赛前配置（TFT loadouts）")
                                                    continue
                                                logPrint("请选择次选位置：\nPlease select your secondary position:\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路/线上（Bottom/Lane）\n5\t辅助（Support）\n6\t补位（Fill）")
                                                while True:
                                                    position_index = logInput()
                                                    if position_index[0] == "0":
                                                        back = True
                                                        break
                                                    elif position_index == "-1":
                                                        secondPreference = "UNSELECTED"
                                                        break
                                                    elif position_index[0] in list(map(str, range(1, 7))):
                                                        position_index = int(position_index[0])
                                                        secondPreference = slotPositions[position_index - 1]
                                                        break
                                                    else:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                if back:
                                                    logPrint("请选择一项个人配置：\nPlease select a personal configuration to change:\n1\t选择位置（Select positions）\n2\t设置快速模式英雄选择（Configure quickplay slot）\n3\t设置子阵营（Configure subteam data）\n4\t切换就绪状态（Toggle ready）\n5\t云顶之弈赛前配置（TFT loadouts）")
                                                    continue
                                                body = {"firstPreference": firstPreference, "secondPreference": secondPreference}
                                                response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/members/localMember/position-preferences", data = body)).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["message"] == "BAD_JSON_FORMAT":
                                                        logPrint("格式错误！\nFormat error!")
                                                    else:
                                                        logPrint("未知错误。\nUnknown error.")
                                                else:
                                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                    if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                        logPrint(lobby_information)
                                                        if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                            logPrint("您还未创建任何房间。请创建一个排位小队后再检查位置。\nYou're not in any lobby. Please first create a ranked party and then check the positions.")
                                                        else:
                                                            logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    else:
                                                        if lobby_information["localMember"]["firstPositionPreference"] == firstPreference and lobby_information["localMember"]["secondPositionPreference"] == secondPreference:
                                                            logPrint("位置设置成功。\nPosition configuration succeeded.")
                                                        else:
                                                            logPrint("位置设置失败。请检查小队是否支持位置选择器。\nPosition configuration failed. Please check if the current party supports position selector.")
                                            else:
                                                logPrint("当前模式不支持位置选择。\nThe current mode doesn't support position selection.")
                                        else:
                                            logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                                    elif config[0] == "2":
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase == "Lobby":
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            if lobby_information["gameConfig"]["showQuickPlaySlotSelection"]:
                                                logPrint("正在整理皮肤数据……\nSorting out skin data ...")
                                                skins_df = await sort_skin_data(connection)
                                                skins_df_fields_to_print = ["id", "name"]
                                                logPrint('请按照以下步骤完成英雄选择。在后续任何步骤，输入“0”以返回上一步。\nPlease follow the steps below to determine the quickplay slots. Submit "0" to return to the last step at any subsequent step.')
                                                slotId = 1
                                                body = []
                                                while slotId <= 2:
                                                    if slotId == 0:
                                                        break
                                                    elif slotId == 1:
                                                        logPrint("按回车键以设置第一个英雄。\nPress Enter to set Slot 1.")
                                                        tmp = logInput()
                                                        if tmp == "0":
                                                            slotId -= 1
                                                            continue
                                                    elif slotId == 2:
                                                        logPrint('按回车键以设置第二个英雄。输入“-1”以跳过该英雄。\nPress Enter to set Slot 2. Submit "-1" to omit this slot.')
                                                        tmp = logInput()
                                                        if tmp == "0":
                                                            slotId -= 1
                                                            continue
                                                        elif tmp == "-1":
                                                            break
                                                    else:
                                                        logPrint("发现异常槽位！请联系开发人员检查和调试代码。\nAn unexpected slot is found! Please contact the developer to check and debug the code.")
                                                        break
                                                    slot_got = False
                                                    step = 1
                                                    while step <= 5:
                                                        if step == 0:
                                                            if slotId > 1:
                                                                body.pop() #在第二步返回上一层，意味着要重新设置第一个英雄（To return to the last step of Step 2, the first slot should be reset）
                                                            slotId -= 2
                                                            break
                                                        elif step == 1:
                                                            logPrint("第一步：请选择一个英雄。\nStep 1: Please select a champion.")
                                                            LoLChampions_df = await get_LoLChampions(connection)
                                                            LoLChampions_fields_to_print = ["id", "name", "title", "alias"]
                                                            LoLChampions_df_selected = pandas.concat([LoLChampions_df.iloc[:1, :], LoLChampions_df[(LoLChampions_df["freeToPlay"] == "√") | (LoLChampions_df["ownership: owned"] == "√") | (LoLChampions_df["ownership: rental: rented"] == "√")]], ignore_index = True)
                                                            LoLChampions_df_query = LoLChampions_df.loc[:, LoLChampions_fields_to_print]
                                                            LoLChampions_df_query["id"] = LoLChampions_df["id"].astype(str) #方便检索（For convenience of retrieval）
                                                            LoLChampions_df_query = LoLChampions_df_query.map(lambda x: x.lower() if isinstance(x, str) else x)
                                                            print(format_df(LoLChampions_df_selected.loc[:, LoLChampions_fields_to_print])[0]) #虽然输出的是筛选后的表格，但实际上用户仍然可以尝试选择不可用的英雄（Although the selected table is output, users can still try choosing unavailable champions）
                                                            log.write(format_df(LoLChampions_df_selected.loc[:, LoLChampions_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                            while True:
                                                                champion_queryStr = logInput()
                                                                if champion_queryStr == "":
                                                                    continue
                                                                elif champion_queryStr == "-1":
                                                                    championId = -1
                                                                    break
                                                                elif champion_queryStr == "0":
                                                                    step -= 2
                                                                    break
                                                                elif champion_queryStr == "-3":
                                                                    championId = -3
                                                                    break
                                                                else:
                                                                    query_positions = numpy.where(LoLChampions_df_query == champion_queryStr.lower()) #使用numpy.where检索的前提是数据框中每个单元格的值都不一样（The premise of query by `numpy.where` is that no two cells are the same）
                                                                    if len(query_positions[0]) == 0:
                                                                        logPrint("没有找到该英雄。请重新输入。\nChampion not found. Please try again.")
                                                                    else:
                                                                        resultRow = query_positions[0]
                                                                        result_champion_df = LoLChampions_df.loc[resultRow, LoLChampions_fields_to_print].reset_index(drop = True)
                                                                        championId = LoLChampions_df.loc[resultRow[0], "id"]
                                                                        logPrint("您选择了以下英雄：\nYou selected the following champion:")
                                                                        print(format_df(result_champion_df)[0])
                                                                        log.write(format_df(result_champion_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                                        break
                                                        elif step == 2:
                                                            logPrint("第二步：请选择一个分路。\nStep 2: Please select a position.\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路（Bottom）\n5\t辅助（Support）")
                                                            slotPositions = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
                                                            while True:
                                                                position_index = logInput()
                                                                if position_index == "":
                                                                    continue
                                                                elif position_index == "-1":
                                                                    position = "UNSELECTED"
                                                                    break
                                                                elif position_index[0] == "0":
                                                                    step -= 2
                                                                    break
                                                                elif position_index in list(map(str, range(1, 6))):
                                                                    position_index = int(position_index)
                                                                    position = slotPositions[position_index - 1]
                                                                    break
                                                                else:
                                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        elif step == 3:
                                                            logPrint("第三步：请选择召唤师技能。\nStep 3: Please select the summoner spells.")
                                                            available_spells = available_spell_dict[lobby_information["gameConfig"]["gameMode"]]
                                                            for spellId in sorted(available_spells):
                                                                spell = spells[spellId]
                                                                logPrint("%d\t%s" %(spellId, spell["name"]))
                                                            logPrint("请依次输入两个召唤师技能的序号，以空格为分隔符：\nPlease input the two spellIds, split by space:")
                                                            while True:
                                                                spell_str = logInput()
                                                                if spell_str == "":
                                                                    continue
                                                                elif spell_str == "0":
                                                                    step -= 2
                                                                    break
                                                                elif spell_str == "0 0":
                                                                    spell1Id = spell2Id = 0
                                                                    break
                                                                else:
                                                                    selectedSpellIds = spell_str.split()
                                                                    if len(selectedSpellIds) != 2:
                                                                        logPrint("请输入两个召唤师技能的序号！\nPlease submit two spellIds!")
                                                                    else:
                                                                        try:
                                                                            selectedSpellIds = list(map(int, selectedSpellIds))
                                                                        except ValueError:
                                                                            logPrint("请输入整数！\nPlease input integers!")
                                                                        else:
                                                                            if len(set(selectedSpellIds)) == 1:
                                                                                logPrint("请输入两个不同的召唤师技能序号！\nPlease input two different spellIds!")
                                                                            elif all(map(lambda x: x in available_spells, selectedSpellIds)):
                                                                                spell1Id, spell2Id = selectedSpellIds
                                                                                break
                                                                            else:
                                                                                logPrint("您输入的召唤师技能序号不可用！请重新输入。\nThe selected summoner spells aren't available. Please try again.")
                                                        elif step == 4:
                                                            logPrint("第四步：请选择符文页。\nStep 4: Please select the perk page.")
                                                            perkPage_df = await get_perk_page(connection)
                                                            perkPage_df_fields_to_print = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
                                                            if len(perkPage_df) == 1:
                                                                logPrint("您还未创建任何符文页。\nYou've not created any page yet.")
                                                            else:
                                                                logPrint("您的符文页如下：\nYou perk pages are listed below:")
                                                                print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                                                                log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                            wd = os.getcwd()
                                                            subscript_path = os.path.join(wd, "Customized Program 19 - Configure Perks.py")
                                                            logPrint("是否需要修改符文页？（输入任意键以修改，否则不修改。）\nDo you want to change any page? (Submit any non-empty string to change, or null to refuse changing.)\n请确保本程序同目录下存在符文脚本，否则无法配置相关符文。\nPlease ensure the perk program is under the same directory as this program, otherwise perk configuration can't be implemented through this program.\n文件名（File name）： Customized Program 19 - Configure Perks.py\n完整路径（Complete path）： %s" %(subscript_path))
                                                            change_page_str = logInput()
                                                            change_page = bool(change_page_str)
                                                            if change_page:
                                                                if os.path.exists(subscript_path):
                                                                    logPrint(f"正在打开（Opening）： {subscript_path}")
                                                                    subprocess.run(["python", subscript_path])
                                                                else:
                                                                    logPrint('''在同目录下未发现符文脚本。取消该操作。请自行在客户端内修改。\n"Customized Program 19 - Configure Perks.py" isn't found under the same directory. This operation is cancelled. Please change inside the League Client.''')
                                                            logPrint("输入左侧的索引以选择一个符文页。\nSelect a page index.")
                                                            perkPage_df = await get_perk_page(connection)
                                                            print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                                                            log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                            while True:
                                                                page_index = logInput()
                                                                if page_index == "":
                                                                    continue
                                                                elif page_index == "-1":
                                                                    perkStr = ""
                                                                    break
                                                                elif page_index == "0":
                                                                    step -= 2
                                                                    break
                                                                elif page_index in list(map(str, range(1, len(perkPage_df)))):
                                                                    page_index = int(page_index)
                                                                    isValid = perkPage_df.loc[page_index, "isValid"] == "√"
                                                                    primaryPerkStyleName = perkPage_df.loc[page_index, "primaryStyleName"]
                                                                    primaryPerkStyleId = perkPage_df.loc[page_index, "primaryStyleId"]
                                                                    secondaryPerkStyleName = perkPage_df.loc[page_index, "secondaryStyleName"]
                                                                    secondaryPerkStyleId = perkPage_df.loc[page_index, "subStyleId"]
                                                                    keystoneId = perkPage_df.loc[page_index, "pageKeystone id"]
                                                                    keystoneName = perkPage_df.loc[page_index, "pageKeystone name"]
                                                                    perkIds = perkPage_df.loc[page_index, "selectedPerkIds"]
                                                                    perkNames = perkPage_df.loc[page_index, "uiPerksNames"]
                                                                    if isValid:
                                                                        logPrint("您选择了以下符文页：\nYou selected the following perk page:")
                                                                        logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
                                                                        logPrint("输入任意非空字符串以确认选择，否则重新选择。\nSubmit any non-empty string to comfirm selection, or null to select another page.")
                                                                        page_confirm_str = logInput()
                                                                        page_confirm = bool(page_confirm_str)
                                                                        if page_confirm:
                                                                            perks_param = {"perkIds": perkIds, "perkStyle": primaryPerkStyleId, "perkSubStyle": secondaryPerkStyleId}
                                                                            perkStr = str(perks_param).replace(" ", "").replace("'", '"')
                                                                            break
                                                                        else:
                                                                            logPrint("输入左侧的索引以选择一个符文页。\nSelect a page index.")
                                                                            perkPage_df = await get_perk_page(connection)
                                                                            print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                                                                            log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                                    else:
                                                                        logPrint("您选择了无效符文页。请重试。\nYou selected an invalid perk page. Please try again.")
                                                                else:
                                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        elif step == 5:
                                                            logPrint("第五步：请设置个性化内容。\nStep 5: Please select cosmetics.")
                                                            skins_df_selected = pandas.concat([skins_df.iloc[:1, :], skins_df[(skins_df["disabled"] == "") & ((skins_df["ownership owned"] == "√") | (skins_df["ownership rental rented"] == "√")) & (skins_df["championId"] == championId)]], ignore_index = True)
                                                            if len(skins_df_selected) == 1:
                                                                logPrint("无可用皮肤。将使用默认皮肤。\nThere's not any available skin. The default skin will be used.")
                                                                selectedSkinId = 0 if championId == -1 else championId * 1000
                                                                slot_got = True
                                                            else:
                                                                logPrint("%s的可用皮肤如下：\nPickable skins of %s are as follows:" %(LoLChampions[championId]["title"], LoLChampions[championId]["alias"]))
                                                                print(format_df(skins_df_selected.loc[:, skins_df_fields_to_print], print_index = True)[0])
                                                                log.write(format_df(skins_df_selected.loc[:, skins_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                                logPrint("请选择一个皮肤：\nPlease select a skin:")
                                                                while True:
                                                                    skin_index = logInput()
                                                                    if skin_index == "":
                                                                        continue
                                                                    elif skin_index == "-1":
                                                                        selectedSkinId = 0
                                                                        slot_got = True
                                                                        break
                                                                    elif skin_index == "0":
                                                                        step -= 2
                                                                        break
                                                                    elif skin_index in list(map(str, range(1, len(skins_df_selected)))):
                                                                        skin_index = int(skin_index)
                                                                        selectedSkinId = skins_df_selected.loc[skin_index, "id"]
                                                                        slot_got = True
                                                                        break
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        else:
                                                            logPrint("发现异常步骤！请联系开发人员检查和调试代码。\nAn unexpected step is found! Please contact the developer to check and debug the code.")
                                                            break
                                                        step += 1
                                                    if slot_got:
                                                        playerSlot = {"championId": championId, "perks": perkStr, "positionPreference": position, "skinId": selectedSkinId, "spell1": spell1Id, "spell2": spell2Id}
                                                        body.append(playerSlot)
                                                    slotId += 1
                                                if len(body) > 0:
                                                    logPrint(body)
                                                    response = await (await connection.request("PUT", "/lol-lobby/v1/lobby/members/localMember/player-slots", data = body)).json()
                                                    logPrint(response)
                                                    if isinstance(response, dict) and "errorCode" in response:
                                                        if response["message"] == "Invalid request line":
                                                            logPrint("请求行无效！\nInvalid request line!")
                                                        elif response["message"] == "BAD_JSON_FORMAT":
                                                            logPrint("格式错误！\nFormat error!")
                                                        elif response["message"] == "INVALID_REQUEST":
                                                            logPrint("请求无效！\nInvalid request!")
                                                        else:
                                                            logPrint("请求失败。\nRequest failed.")
                                                    else:
                                                        logPrint("请求成功。\nRequest succeeded.")
                                            else:
                                                logPrint("当前模式不支持英雄预选。\nThis mode doesn't support slot selection.")
                                        else:
                                            logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                                    elif config[0] == "3":
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase == "Lobby":
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            if lobby_information["gameConfig"]["gameMode"] == "CHERRY":
                                                memberSlots = []
                                                for member in lobby_information["members"]:
                                                    member_info_recapture = 0
                                                    member_info = await get_info(connection, member["puuid"])
                                                    while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                                                        logPrint(member_info["message"])
                                                        member_info_recapture += 1
                                                        logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of member (puuid: %s) capture failed! Recapturing this member's information ... Times tried: %d" %(member["puuid"], member_info_recapture, member["puuid"], member_info_recapture))
                                                        member_info = await get_info(connection, member["puuid"])
                                                    if not member_info["info_got"]:
                                                        logPrint(member_info["message"])
                                                        logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！\nInformation of member (puuid: %s) capture failed!" %(member["puuid"], member["puuid"]))
                                                    memberSlot = {"slot": (member["subteamIndex"], member["intraSubteamPosition"]), "puuid": member["puuid"], "summonerName": get_info_name(member_info["body"]) if member_info["info_got"] else "", "selfTag": "☆" if member["puuid"] == current_info["puuid"] else ""}
                                                    memberSlots.append(memberSlot)
                                                memberSlots = sorted(memberSlots, key = lambda x: x["slot"]) #将成员关于子阵营槽位排序（Sort the members according to the subteam slot order）
                                                logPrint('请依次输入您的子阵营序号和位置，以空格为分隔符：（输入“0”以返回上一层。）\nPlease enter the subteamIndex and intraSubteamPosition one by one, split by space: (Submit "0" to return to the last step.)')
                                                for memberSlot in memberSlots:
                                                    print("%s%s\t%s\t%s" %(memberSlot["selfTag"], memberSlot["slot"], memberSlot["puuid"], memberSlot["summonerName"]))
                                                logPrint("例如，如果想要恢复您现在的位置，您可以输入：\nFor example, if you want to return to your current slot, you may input:\n%d %d" %(lobby_information["localMember"]["subteamIndex"], lobby_information["localMember"]["intraSubteamPosition"]))
                                                while True:
                                                    slot_str = logInput()
                                                    if slot_str == "":
                                                        continue
                                                    elif slot_str == "0":
                                                        break
                                                    else:
                                                        try:
                                                            subteamIndex, intraSubteamPosition = list(map(int, slot_str.split()))
                                                        except Exception as e:
                                                            traceback_info = traceback.format_exc()
                                                            logPrint(traceback_info)
                                                            if isinstance(e, ValueError):
                                                                logPrint("您输入的参数数量不符！请确保您只输入了两个参数。\nNumber of parameters mismatch! Please make sure only two parameters are submitted.")
                                                            elif isinstance(e, TypeError):
                                                                logPrint("类型错误！请输入整数。\nType ERROR! Please submit integers.")
                                                            else:
                                                                logPrint("未知错误。\nUnknown error.")
                                                            continue
                                                        else:
                                                            body = {"subteamIndex": subteamIndex, "intraSubteamPosition": intraSubteamPosition}
                                                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/subteamData", data = body)).json()
                                                            logPrint(response)
                                                            if isinstance(response, dict) and "errorCode" in response:
                                                                if response["httpStatus"] == 400 and response["message"] == "INVALID_REQUEST":
                                                                    logPrint("请求无效。请确保您的小队目前不在队列中。\nInvalid request. Please make sure your party isn't currently in queue.")
                                                                elif response["httpStatus"] == 500 and response["message"] == "INVALID_LOBBY":
                                                                    logPrint("自定义房间不支持设置子阵营。\nSubteam configuration isn't supported in a custom lobby.")
                                                                else:
                                                                    logPrint("未知错误。\nUnknown error.")
                                                                break
                                                            else:
                                                                time.sleep(GLOBAL_RESPONSE_LAG)
                                                                lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                                if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                                    logPrint(lobby_information)
                                                                    if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                                        logPrint("您还未创建任何房间。请创建一个斗魂竞技场小队后再设置子阵营。\nYou're not in any lobby. Please first create a Arena party and then configure your subteam.")
                                                                    else:
                                                                        logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                                else:
                                                                    current_subteamIndex = lobby_information["localMember"]["subteamIndex"]
                                                                    current_intraSubteamPosition = lobby_information["localMember"]["intraSubteamPosition"]
                                                                    if current_subteamIndex == subteamIndex and current_intraSubteamPosition == intraSubteamPosition:
                                                                        logPrint("子阵营设置成功。\nSubteam configuration succeeded.")
                                                                    else:
                                                                        logPrint("子阵营设置失败。当前子阵营参数：(%d, %d)。\nSubteam configuration failed. Current subteam slot parameter: (%d, %d)." %(current_subteamIndex, current_intraSubteamPosition, current_subteamIndex, current_intraSubteamPosition))
                                                    #下面的代码是while循环前的一段的重复（The following code are copied from the piece in front of the while-loop） 
                                                    memberSlots = []
                                                    for member in lobby_information["members"]:
                                                        member_info_recapture = 0
                                                        member_info = await get_info(connection, member["puuid"])
                                                        while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                                                            logPrint(member_info["message"])
                                                            member_info_recapture += 1
                                                            logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of member (puuid: %s) capture failed! Recapturing this member's information ... Times tried: %d" %(member["puuid"], member_info_recapture, member["puuid"], member_info_recapture))
                                                            member_info = await get_info(connection, member["puuid"])
                                                        if not member_info["info_got"]:
                                                            logPrint(member_info["message"])
                                                            logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！\nInformation of member (puuid: %s) capture failed!" %(member["puuid"], member["puuid"]))
                                                        memberSlot = {"slot": (member["subteamIndex"], member["intraSubteamPosition"]), "puuid": member["puuid"], "summonerName": get_info_name(member_info["body"]) if member_info["info_got"] else "", "selfTag": "☆" if member["puuid"] == current_info["puuid"] else ""}
                                                        memberSlots.append(memberSlot)
                                                    memberSlots = sorted(memberSlots, key = lambda x: x["slot"]) #将成员关于子阵营槽位排序（Sort the members according to the subteam slot order）
                                                    logPrint('请依次输入您的子阵营序号和位置，以空格为分隔符：（输入“0”以返回上一层。）\nPlease enter the subteamIndex and intraSubteamPosition one by one, split by space: (Submit "0" to return to the last step.)')
                                                    for memberSlot in memberSlots:
                                                        print("%s%s\t%s\t%s" %(memberSlot["selfTag"], memberSlot["slot"], memberSlot["puuid"], memberSlot["summonerName"]))
                                                    logPrint("例如，如果想要恢复您现在的位置，您可以输入：\nFor example, if you want to return to your current slot, you may input:\n%d %d" %(lobby_information["localMember"]["subteamIndex"], lobby_information["localMember"]["intraSubteamPosition"]))
                                            else:
                                                logPrint("当前模式不支持子阵营选择。\nThis mode doesn't support subteam selection.")
                                        else:
                                            logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                                    elif config[0] == "4":
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase == "Lobby":
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            ready = isinstance(lobby_information["localMember"]["memberData"], dict) and lobby_information["localMember"]["memberData"].get("isPlayerReady", "") == "true"
                                            logPrint("请选择一个操作：\nPlease select an operation:\n%s1\t准备就绪（Toggle ready）\n%s2\t取消就绪（Toggle not ready）" %("☆" if not ready else "", "☆" if ready else ""))
                                            while True:
                                                operation = logInput()
                                                if operation == "":
                                                    operation = "2" if ready else "1"
                                                if operation[0] == "0":
                                                    break
                                                elif operation[0] in {"1", "2"}:
                                                    body = {"isPlayerReady": "true" if operation[0] == "1" else ""}
                                                    response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/memberData", data = body)).json()
                                                    logPrint(response)
                                                    if isinstance(response, dict) and "errorCode" in response:
                                                        if "Couldn't assign value to 'memberData'" in response["message"]:
                                                            logPrint("请求主体格式错误！\nERROR format of the request body.")
                                                        else:
                                                            logPrint("未知错误！\nUnknown error!")
                                                    else:
                                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                                        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                        if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                            logPrint(lobby_information)
                                                            if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                                logPrint("您还未创建任何房间。请创建一个小队后再更改游戏模式。\nYou're not in any lobby. Please first create a party and then change the game mode.")
                                                            else:
                                                                logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                        else:
                                                            ready = isinstance(lobby_information["localMember"]["memberData"], dict) and lobby_information["localMember"]["memberData"].get("isPlayerReady", "") == "true"
                                                            if operation[0] == "1" and ready:
                                                                logPrint("您已准备就绪。\nYou're ready.")
                                                                break
                                                            elif operation[0] == "2" and not ready:
                                                                logPrint("您已取消就绪。\nYou've toggled unready.")
                                                                break
                                                            else:
                                                                logPrint("就绪状态切换失败。\nReadiness toggle failed.")
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择一个操作：\nPlease select an operation:\n%s1\t准备就绪（Toggle ready）\n%s2\t取消就绪（Toggle not ready）" %("☆" if not ready else "", "☆" if ready else ""))
                                        else:
                                            logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                                    elif config[0] == "5":
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase == "Lobby":
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            if lobby_information["gameConfig"]["gameMode"] == "TFT":
                                                loadout_scope = await (await connection.request("GET", "/lol-loadouts/v4/loadouts/scope/account")).json()
                                                if isinstance(loadout_scope, dict) and "errorCode" in loadout_scope:
                                                    logPrint(loadout_scope)
                                                    logPrint("未知错误！\nUnknown error!")
                                                else:
                                                    if len(loadout_scope) == 0:
                                                        logPrint("无可用赛前配置方案。请重启英雄联盟客户端后再运行本程序。\nNo available loadouts. Please restart the League Client and then run this program.")
                                                    else:
                                                        loadoutId = loadout_scope[0]["id"] #因为赛前配置在每次退出英雄联盟客户端后就没了，所以随便取一个赛前配置就行。这里取了第一个列表元素（Because loadouts aren't reserved as the user exits the League Client, any loadout is OK to use. Here the first element of the loadout scope list is used）
                                                        loadoutName = loadout_scope[0]["name"]
                                                    logPrint("正在加载藏品信息……\nLoading collections ...")
                                                    collection_df = await get_collection(connection)
                                                    collection_df_fields_to_print = ["inventoryType", "itemId", "name", "ownershipType"]
                                                    logPrint("请选择一项赛前配置：\nPlease select a loadout:\n1\t小小英雄（Tacticians）\n2\t进攻特效（Booms）\n3\t棋盘皮肤（Arena skins）\n4\t传送门（Portals）")
                                                    while True:
                                                        loadout_option = logInput()
                                                        if loadout_option == "":
                                                            continue
                                                        elif loadout_option[0] == "0":
                                                            break
                                                        elif loadout_option[0] in list(map(str, range(1, 5))):
                                                            inventoryTypes = {"1": "COMPANION", "2": "TFT_DAMAGE_SKIN", "3": "TFT_MAP_SKIN", "4": "TFT_ZOOM_SKIN"}
                                                            inventoryType = inventoryTypes[loadout_option[0]]
                                                            collection_df_selected = pandas.concat([collection_df.iloc[:1, :], collection_df[collection_df["inventoryType"] == inventoryType]], ignore_index = True)
                                                            if len(collection_df_selected) == 1:
                                                                logPrint("您目前没有该类道具的使用权。\nYou don't have permissions to use any item of this inventoryType.")
                                                            else:
                                                                logPrint('请选择您想要使用的道具：（输入-1以初始化当前选择。）\nPlease select an item to use: (Submit "-1" to initialize the current choice.)')
                                                                print(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], print_index = True)[0])
                                                                log.write(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                                while True:
                                                                    index_got = False
                                                                    item_index = logInput()
                                                                    if item_index == "":
                                                                        continue
                                                                    elif item_index == "0":
                                                                        index_got = False
                                                                        break
                                                                    elif item_index == "-1" or item_index in list(map(str, range(1, len(collection_df_selected)))):
                                                                        item_index = int(item_index)
                                                                        index_got = True
                                                                        break
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                if index_got:
                                                                    contentId = "" if item_index == -1 else collection_df_selected.loc[item_index, "uuid"]
                                                                    itemId = 0 if item_index == -1 else collection_df_selected.loc[item_index, "itemId"]
                                                                    loadout_key = f"{inventoryType}_SLOT" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                                                    body = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                                                    response = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
                                                                    logPrint(response)
                                                                    if isinstance(response, dict) and "errorCode" in response:
                                                                        if response["message"] == "UpdateLoadout Failed - Loadout does not exist in cache.":
                                                                            logPrint("更新赛前配置失败。请检查代码为%s的赛前配置是否存在。如果不存在，请返回到选择赛前配置之前的步骤，再重试。\nLoadout update failed. Please check if the loadout of id %s still exists. If it doesn't exist, please return to the step before selecting to configure the TFT loadouts and then try again.")
                                                                        else:
                                                                            logPrint("未知错误！\nUnknown error!")
                                                                    else:
                                                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                                                        loadout = await (await connection.request("GET", f"/lol-loadouts/v4/loadouts/{loadoutId}")).json()
                                                                        if loadout["loadout"][loadout_key] == body["loadout"][loadout_key]:
                                                                            logPrint("更新赛前配置成功。客户端内显示可能有延迟，请尝试关闭相应窗口再打开，观察配置是否更新。进入游戏即可正常使用。\nLoadout update succeeded. The League Client may not display the change properly due to a lag. Please try closing the corresponding window and then open it again to see if loadout is updated. As you enter the game, you should be using the updated loadouts.")
                                                                        else:
                                                                            logPrint("更新赛前配置失败。\nLoadout update failed.")
                                                        else:
                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                            continue
                                                        logPrint("请选择一项赛前配置：\nPlease select a loadout:\n1\t小小英雄（Tacticians）\n2\t进攻特效（Booms）\n3\t棋盘皮肤（Arena skins）\n4\t传送门（Portals）")
                                            else:
                                                logPrint("当前游戏模式不是云顶之弈。请切换到云顶之弈模式并重试。\nThe current game mode isn't TFT. Please switch to a TFT party and try again.")
                                        else:
                                            logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    logPrint("请选择一项个人配置：\nPlease select a personal configuration to change:\n1\t选择位置（Select positions）\n2\t设置快速模式英雄选择（Configure quickplay slot）\n3\t设置子阵营（Configure subteam data）\n4\t切换就绪状态（Toggle ready）\n5\t云顶之弈赛前配置（TFT loadouts）")
                            elif suboption[0] == "2":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase in ["Lobby", "Matchmaking", "ReadyCheck"]:
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    queueId = lobby_information["gameConfig"]["queueId"]
                                    queues_initial = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
                                    queues = {queue["id"]: queue for queue in queues_initial}
                                    social_leaderboard_df_fields_to_print = ["leaderboardPosition", "gameName", "tagLine", "tier", "division", "wins"]
                                    if queueId in queues and queues[queueId]["isRanked"]:
                                        queueType = queues[queueId]["type"]
                                        if queueType in ["RANKED_TFT_DOUBLE_UP", "RANKED_TFT_PAIRS"]:
                                            logPrint("查询该游戏模式的好友排行榜会导致英雄联盟崩溃。您确定要继续吗？（输入任意键以继续，否则拒绝。）\nFetching friends leaderboard of this mode will result in a crash of League of Legends. Do you really want to continue? (Submit any non-empty string to continue, or null to take a risk.)")
                                            leaderboard_crash_continue_str = logInput()
                                            leaderboard_crash_continue = bool(leaderboard_crash_continue_str)
                                            if leaderboard_crash_continue:
                                                social_leaderboard_df = await sort_social_leaderboard(connection, queueType)
                                                if len(social_leaderboard_df) > 1:
                                                    if len(social_leaderboard_df) < 4:
                                                        logPrint("警告：你需要有至少3名《英雄联盟》好友才能查看好友榜。\nWarning: You need at least 3 League friends to view the Friends Board.")
                                                    print(format_df(social_leaderboard_df.loc[:, social_leaderboard_df_fields_to_print], print_index = True)[0])
                                                    log.write(format_df(social_leaderboard_df.loc[:, social_leaderboard_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                else:
                                                    logPrint("无好友排行榜数据。\nNo rowData in Friends Leaderboard.")
                                        else:
                                            social_leaderboard_df = await sort_social_leaderboard(connection, queueType)
                                            if len(social_leaderboard_df) > 1:
                                                if len(social_leaderboard_df) < 4:
                                                    logPrint("警告：你需要有至少3名《英雄联盟》好友才能查看好友榜。\nWarning: You need at least 3 League friends to view the Friends Board.")
                                                print(format_df(social_leaderboard_df.loc[:, social_leaderboard_df_fields_to_print], print_index = True)[0])
                                                log.write(format_df(social_leaderboard_df.loc[:, social_leaderboard_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                            else:
                                                logPrint("无好友排行榜数据。\nNo rowData in Friends Leaderboard.")
                                    else:
                                        logPrint("当前房间不支持查询好友排行榜。\nThis party doesn't support Friends Leaderboard.")
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a party/lobby, or during a champ select stage.")
                            elif suboption[0] == "3":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    logPrint("请选择一个操作：\nPlease select a operation:\n%s1\t让小队仅能通过邀请来进入（Make party invite-only）\n%s2\t将小队公开给好友（Open party to friends）" %("☆" if lobby_information["partyType"] == "open" else "", "☆" if lobby_information["partyType"] == "closed" else ""))
                                    while True:
                                        operation = logInput()
                                        if operation == "":
                                            operation = "1" if lobby_information["partyType"] == "open" else "2"
                                        if operation[0] == "0":
                                            break
                                        elif operation[0] in {"1", "2"}:
                                            response = await (await connection.request("PUT", "/lol-lobby/v2/lobby/partyType", data = "closed" if operation[0] == "1" else "open")).json()
                                            logPrint(response)
                                            if isinstance(response, dict) and "errorCode" in response:
                                                if response["message"] == "INVALID_REQUEST":
                                                    logPrint("请求无效！请检查请求主体是否正确。\nInvalid request! Please check the correctness of the request body.")
                                                elif response["message"] == "INVALID_LOBBY_TYPE":
                                                    logPrint("请求失败！请确保您目前正处于小队而不是自定义房间中。\nRequest failed! Please make sure you're currently in a party instead of a custom lobby.")
                                                elif response["message"] == "PARTY_LEADER_REQUIRED":
                                                    logPrint("只有拥有者可以将小队设置为公开或私密。\nOnly the owner may open or close the party.")
                                                else:
                                                    logPrint("未知错误！\nUnknown error!")
                                            else:
                                                time.sleep(GLOBAL_RESPONSE_LAG)
                                                lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                    logPrint(lobby_information)
                                                    if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                        logPrint("您还未创建任何房间。请创建一个小队后再更改公开性。\nYou're not in any lobby. Please first create a party and then change its publicity.")
                                                    else:
                                                        logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                else:
                                                    if operation[0] == "1" and lobby_information["partyType"] == "closed":
                                                        logPrint("小队已转为私密。您的好友只能通过邀请来进入。\nYour party has become private. They can only join this party through an invitation.")
                                                        break
                                                    elif operation[0] == "2" and lobby_information["partyType"] == "open":
                                                        logPrint("小队已向好友公开。您的好友将能够直接进入小队。\nYour party has been opened to friends. They can directly join this party now.")
                                                        break
                                                    else:
                                                        logPrint("小队公开性切换失败。\nParty publicity toggle failed.")
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        logPrint("请选择一个操作：\nPlease select a operation:\n%s1\t让小队仅能通过邀请来进入（Make party invite-only）\n%s2\t将小队公开给好友（Open party to friends）" %("☆" if lobby_information["partyType"] == "open" else "", "☆" if lobby_information["partyType"] == "closed" else ""))
                                else:
                                    logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                            elif suboption[0] == "4":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    await create_lobby(connection)
                                else:
                                    logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                            elif suboption[0] == "5":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    response = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        if response["httpStatus"] == 400:
                                            if response["message"] == "INVALID_PERMISSIONS":
                                                logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the party owner and thus can't perform this operation.")
                                            elif response["message"] == "GATEKEEPER_RESTRICTED":
                                                if bool(lobby_information["restrictions"]):
                                                    logPrint("无法寻找对局。请检查小队限制。\nUnable to find match. Please check the party restrictions.")
                                                    logPrint(lobby_information["restrictions"])
                                                search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
                                                if not (isinstance(search_state, dict) and "errorCode" in search_state):
                                                    if search_state["searchState"] in {"ServiceShutdown", "ServiceError", "Error", "AbandonedLowPriorityQueue"}:
                                                        logPrint(search_state)
                                                    for error in search_state["errors"]:
                                                        if error["errorType"] == "QUEUE_DODGER":
                                                            penalty_time_remaining = int(error["penaltyTimeRemaining"])
                                                            penalizedSummoner_recapture = 0
                                                            penalizedSummoner = await get_info(connection, error["penalizedSummonerId"])
                                                            while not penalizedSummoner["info_got"] and penalizedSummoner["body"]["httpStatus"] != 404 and penalizedSummoner_recapture < 3:
                                                                logPrint(penalizedSummoner["message"])
                                                                penalizedSummoner_recapture += 1
                                                                logPrint("小队成员信息（召唤师序号：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of a lobby member (summonerId: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(error["penalizedSummonerId"], penalizedSummoner_recapture, penalizedSummoner_recapture, error["penalizedSummonerId"]))
                                                                penalizedSummoner = await get_info(connection, error["penalizedSummonerId"])
                                                            if penalizedSummoner["info_got"]:
                                                                penalizedSummonerName = get_info_name(penalizedSummoner["body"])
                                                                penalty_time_remaining_text_zh = ""
                                                                penalty_time_remaining_text_en = ""
                                                                penalty_hour = penalty_time_remaining // 3600
                                                                penalty_minute = penalty_time_remaining % 3600 // 60
                                                                penalty_second = penalty_time_remaining % 60
                                                                if penalty_hour != 0:
                                                                    penalty_time_remaining_text_zh += str(penalty_hour) + "时"
                                                                    penalty_time_remaining_text_en += str(penalty_hour) + " h "
                                                                if penalty_minute != 0:
                                                                    penalty_time_remaining_text_zh += str(penalty_minute) + "分"
                                                                    penalty_time_remaining_text_en += str(penalty_minute) + " m "
                                                                penalty_time_remaining_text_zh += str(penalty_second) + "秒"
                                                                penalty_time_remaining_text_en += str(penalty_second) + " s"
                                                                logPrint(f"队列秒退计时器：由于{penalizedSummonerName}在英雄选择过程中退出了游戏，或者拒绝了过多场游戏，导致你无法加入队列。剩余时间：{penalty_time_remaining_text_zh}。\nQUEUE DODGE TIMER: Because {penalizedSummonerName} abandoned a recent game during champ selection or declined too many games, you're currently unable to join the queue. Penalty Time Remaining: {penalty_time_remaining_text_en}.")
                                                            else:
                                                                logPrint(penalizedSummoner["message"])
                                                                logPrint("小队成员信息（召唤师序号：%s）获取失败！\nInformation of a lobby member (summonerId: %s) capture failed!" %(error["penalizedSummonerId"], error["penalizedSummonerId"]))
                                                    if search_state["lowPriorityData"]["reason"] == "LEAVER_BUSTED":
                                                        penalty_time_remaining = int(search_state["lowPriorityData"]["penaltyTimeRemaining"])
                                                        penalizedSummoners = []
                                                        for penalizedSummonerId in search_state["lowPriorityData"]["penalizedSummonerIds"]:
                                                            penalizedSummoner_recapture = 0
                                                            penalizedSummoner = await get_info(connection, penalizedSummonerId)
                                                            while not penalizedSummoner["info_got"] and penalizedSummoner["body"]["httpStatus"] != 404 and penalizedSummoner_recapture < 3:
                                                                logPrint(penalizedSummoner["message"])
                                                                penalizedSummoner_recapture += 1
                                                                logPrint("小队成员信息（召唤师序号：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of a lobby member (summonerId: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(error["penalizedSummonerId"], penalizedSummoner_recapture, penalizedSummoner_recapture, error["penalizedSummonerId"]))
                                                                penalizedSummoner = await get_info(connection, penalizedSummonerId)
                                                            if penalizedSummoner["info_got"]:
                                                                penalizedSummoners.append(penalizedSummoner["body"])
                                                            else:
                                                                logPrint(penalizedSummoner["message"])
                                                                logPrint("小队成员信息（召唤师序号：%s）获取失败！\nInformation of a lobby member (summonerId: %s) capture failed!" %(penalizedSummonerId, penalizedSummonerId))
                                                        penalizedSummonerNames = list(map(get_info_name, penalizedSummoners))
                                                        penalty_time_remaining_text_zh = ""
                                                        penalty_time_remaining_text_en = ""
                                                        penalty_hour = penalty_time_remaining // 3600
                                                        penalty_minute = penalty_time_remaining % 3600 // 60
                                                        penalty_second = penalty_time_remaining % 60
                                                        if penalty_hour != 0:
                                                            penalty_time_remaining_text_zh += str(penalty_hour) + "时"
                                                            penalty_time_remaining_text_en += str(penalty_hour) + " h "
                                                        if penalty_minute != 0:
                                                            penalty_time_remaining_text_zh += str(penalty_minute) + "分"
                                                            penalty_time_remaining_text_en += str(penalty_minute) + " m "
                                                        penalty_time_remaining_text_zh += str(penalty_second) + "秒"
                                                        penalty_time_remaining_text_en += str(penalty_second) + " s"
                                                        logPrint(f"低优先级队列：放弃比赛或是挂机，会导致你的队友进行一场不公平的对局，并且会被系统视为应受惩罚的恶劣行为。你的队伍已被放置在一条低优先级队列中。离开该队列、拒绝或未能接受对局将重置这个倒计时。剩余时间：{penalty_time_remaining_text_zh}。\nLow Priority Queue: Abandoning a match or being AFK results in a negative experience for your teammates, and is a punishable offense in League of Legends. You've been placed in a lower priority queue. Leaving the queue, declining or failing to accept a match will reset the timer. Time Remaining: {penalty_time_remaining_text_en}.\n警告玩家（Penalized summoners）：")
                                                        for penalizedSummonerName in penalizedSummonerNames:
                                                            logPrint(penalizedSummonerName)
                                            else:
                                                logPrint("未知错误。\nUnknown error.")
                                        else:
                                            logPrint("未知错误。\nUnknown error.")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase in ["Matchmaking", "ReadyCheck"]:
                                            logPrint("您已加入寻找对局的队列。\nYou joined the matchmaking queue.")
                                        else:
                                            logPrint("加入寻找对局队列失败。\nFailed to join the matchmaking queue.")
                                else:
                                    logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                            else:   
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            logPrint("请选择一个小队操作：\nPlease select a party operation:\n1\t入队准备（Prepare before in queue）\n2\t查看社交排行榜（Check friends leaderboard）\n3\t改变小队公开性（Toggle party open/closed）\n4\t更换模式（Change mode）\n5\t寻找对局（Find match）")
                elif option == "2":
                    if lobby_information["gameConfig"]["isCustom"]:
                        logPrint("请选择一个自定义房间操作：\nPlease select a lobby operation:\n1\t添加电脑玩家（Add a bot）\n2\t移除电脑玩家（Remove a bot）\n3\t交换队伍（Switch team）\n4\t切换观战状态（Switch spectate status）\n5\t更换模式（Change mode）\n6\t开始游戏（Start game）")
                        while True:
                            suboption = logInput()
                            if suboption == "":
                                continue
                            elif suboption[0] == "0":
                                break
                            elif suboption[0] == "1":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby" or gameflow_phase == "ChampSelect":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if lobby_information["localMember"]["isLeader"]:
                                        logPrint('请按照以下步骤添加电脑玩家。在后续任何步骤，输入“0”以返回上一步。\nPlease follow the steps below to add a bot. Submit "0" to return to the last step at any subsequent step.')
                                        championId_got = botDifficulty_got = teamId_got = position_got = botUuid_got = False
                                        step = 1
                                        while step <= 5:
                                            if step == 0:
                                                break
                                            elif step == 1:
                                                logPrint("第一步：请选择一个英雄。\nStep 1: Please select a champion.")
                                                logPrint("请选择可用电脑玩家范围：\n1\t当前房间可用电脑英雄（Available bot champions in this lobby）\n2\t所有电脑英雄（All bot champions）")
                                                while True:
                                                    championId_got = False
                                                    strategy = logInput()
                                                    if strategy == "":
                                                        continue
                                                    elif strategy[0] == "0":
                                                        championId_got = False
                                                        break
                                                    elif strategy[0] == "1":
                                                        gameflow_phase = await get_gameflow_phase(connection)
                                                        if gameflow_phase == "Lobby":
                                                            availableBot_df = await get_available_bots(connection)
                                                            availableBot_df_fields_to_print = ["id", "name", "botDifficulties"]
                                                            if len(availableBot_df) == 1:
                                                                logPrint("当前房间无可用电脑玩家。\nThere's not any available bot player in this lobby.")
                                                            else:
                                                                print(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print])[0])
                                                                log.write(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                                logPrint("请输入您想要添加的电脑玩家英雄序号：\nPlease select a championId of the bot player you want to add:")
                                                                while True:
                                                                    championId = logInput()
                                                                    if championId == "":
                                                                        continue
                                                                    elif championId == "0":
                                                                        break
                                                                    elif championId in list(map(str, availableBot_df.loc[1:, "id"])):
                                                                        championId = int(championId)
                                                                        championId_got = True
                                                                        break
                                                                    elif championId in list(map(str, LoLChampions.keys())):
                                                                        #logPrint("您输入的英雄没有电脑模型。请重新选择一个英雄。\nThe champion you pick doesn't have a bot enabled. Please select another champion.")
                                                                        championId = int(championId)
                                                                        championId_got = True
                                                                        break
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        else:
                                                            logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                                                    elif strategy[0] == "2":
                                                        wd = os.getcwd()
                                                        excel_path = os.path.join(wd, "available-bots.xlsx")
                                                        if os.path.exists(excel_path):
                                                            try:
                                                                availableBot_df = pandas.read_excel(excel_path, sheet_name = "Sheet2", index_col = 0, usecols = list(range(5)))
                                                            except:
                                                                traceback_info = traceback.format_exc()
                                                                logPrint(traceback_info)
                                                                logPrint("读取可用电脑玩家工作簿的过程出现了问题。\nAn error occurred when reading the available bot workbook.")
                                                            else:
                                                                if all(i in availableBot_df.columns for i in ["id", "name", "title", "alias"]) and all(map(lambda x: isinstance(x, int), availableBot_df.loc[1:, "id"])):
                                                                    print(format_df(availableBot_df)[0])
                                                                    log.write(format_df(availableBot_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                                    logPrint("请输入您想要添加的电脑玩家英雄序号：\nPlease select a championId of the bot player you want to add:")
                                                                    while True:
                                                                        championId = logInput()
                                                                        if championId == "":
                                                                            continue
                                                                        elif championId == "0":
                                                                            break
                                                                        elif championId in list(map(str, availableBot_df.loc[1:, "id"])):
                                                                            championId = int(championId)
                                                                            championId_got = True
                                                                            break
                                                                        elif championId in list(map(str, LoLChampions.keys())):
                                                                            #logPrint("您输入的英雄没有电脑模型。请重新选择一个英雄。\nThe champion you pick doesn't have a bot enabled. Please select another champion.")
                                                                            championId = int(championId)
                                                                            championId_got = True
                                                                            break
                                                                        else:
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                else:
                                                                    logPrint('可用电脑玩家工作簿格式错误。请通过查英雄脚本重新导出。\nAvailable bot workbook format error. Please re-export this workbook through "Customized Program 04 - Count Champion Number.py".')
                                                        else:
                                                            logPrint('''在同目录下未发现可用电脑玩家工作簿。是否需要自行测试所有可用电脑玩家？注意，这样会导致您退出当前房间。此过程需要花费几分钟时间。（输入任意键以开始测试，否则不测试。）\n"available-bots.xlsx" isn't found under the same directory. Do you want to traverse all champions to find all bot-enabled champions? Note: This operation will cause you to leave the current lobby. This process may take several minutes. (Submit any non-empty string to start the test, or null to refuse testing.)''')
                                                            botTest_str = logInput()
                                                            botTest = bool(botTest_str)
                                                            if botTest:
                                                                available_bot_championIds = await test_bot(connection)
                                                                LoLChampions_df = await get_LoLChampions(connection)
                                                                if len(available_bot_championIds) == 0:
                                                                    logPrint("没有获取到可用的电脑玩家。\nNo available bot champions found.")
                                                                else:
                                                                    availableBot_df = pandas.concat([LoLChampions_df.iloc[:1, :], LoLChampions_df[LoLChampions_df["id"].isin(available_bot_championIds)]], ignore_index = True)
                                                                    availableBot_df_fields_to_print = ["id", "name", "title", "alias"]
                                                                    print(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print])[0])
                                                                    log.write(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                                    logPrint("请输入您想要添加的电脑玩家英雄序号：\nPlease select a championId of the bot player you want to add:")
                                                                    while True:
                                                                        championId = logInput()
                                                                        if championId == "":
                                                                            continue
                                                                        elif championId == "0":
                                                                            break
                                                                        elif championId in list(map(str, availableBot_df.loc[1:, "id"])):
                                                                            championId = int(championId)
                                                                            championId_got = True
                                                                            break
                                                                        elif championId in list(map(str, LoLChampions.keys())):
                                                                            #logPrint("您输入的英雄没有电脑模型。请重新选择一个英雄。\nThe champion you pick doesn't have a bot enabled. Please select another champion.")
                                                                            championId = int(championId)
                                                                            championId_got = True
                                                                            break
                                                                        else:
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    else:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                                    break
                                                if not championId_got:
                                                    step -= 2
                                            elif step == 2:
                                                logPrint("第二步：请选择电脑玩家难度。\nStep 2: Please select a bot difficulty.\n1\t新手（TUTORIAL）\n2\t入门（INTRO）\n3\t简单（EASY）\n4\t一般（MEDIUM）\n5\t困难（HARD）\n6\t末日（UBER）\n7\t温暖局入门级（RSWARMINTRO）\n8\t入门级（RSINTRO）\n9\t新手级（RSBEGINNER）\n10\t一般级（RSINTERMEDIATE）")
                                                while True:
                                                    botDifficulty_got = False
                                                    botDifficulty_index = logInput()
                                                    if botDifficulty_index == "":
                                                        continue
                                                    elif botDifficulty_index == "-1":
                                                        botDifficulty = "NONE"
                                                        botDifficulty_got = True
                                                        break
                                                    elif botDifficulty_index == "0":
                                                        botDifficulty_got = False
                                                        break
                                                    elif botDifficulty_index in list(map(str, range(1, 11))):
                                                        botDifficulty_index = int(botDifficulty_index)
                                                        botDifficulty = botDifficulty_list[botDifficulty_index]
                                                        botDifficulty_got = True
                                                        break
                                                    else:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                if not botDifficulty_got:
                                                    step -= 2
                                            elif step == 3:
                                                logPrint("第三步：请选择电脑玩家阵营。\nStep 3: Please select a team for this bot player.\n1\t蓝方（Blue）\n2\t红方（Red）")
                                                while True:
                                                    teamId_got = False
                                                    teamId = logInput()
                                                    if teamId == "":
                                                        continue
                                                    elif teamId[0] == "0":
                                                        teamId_got = False
                                                        break
                                                    elif teamId in ["1", "2"]:
                                                        teamId = f"{teamId}00"
                                                        teamId_got = True
                                                        break
                                                    else:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                if not teamId_got:
                                                    step -= 2
                                            elif step == 4:
                                                positions = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
                                                recommended_position_for_champion = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
                                                recommended_lanes = {}
                                                for position_iter in positions:
                                                    recommended_lanes[position_iter] = position_iter in recommended_position_for_champion[str(championId)]["recommendedPositions"]
                                                logPrint("第四步：请选择电脑玩家分路。\nStep 4: Please select a position for this bot player.\n%s1\t上路（Top）\n%s2\t打野（Jungle）\n%s3\t中路（Middle）\n%s4\t下路（Bottom）\n%s5\t辅助（Support）" %("☆" if recommended_lanes["TOP"] else "", "☆" if recommended_lanes["JUNGLE"] else "", "☆" if recommended_lanes["MIDDLE"] else "", "☆" if recommended_lanes["BOTTOM"] else "", "☆" if recommended_lanes["UTILITY"] else "", ))
                                                while True:
                                                    position_got = False
                                                    position_index = logInput()
                                                    if position_index == "":
                                                        continue
                                                    elif position_index[0] == "0":
                                                        position_got = False
                                                        break
                                                    elif position_index[0] in list(map(str, range(1, 6))):
                                                        position_index = int(position_index[0])
                                                        position = positions[position_index - 1]
                                                        position_got = True
                                                        break
                                                    else:
                                                        break
                                                if not position_got:
                                                    step -= 2
                                            elif step == 5:
                                                logPrint("第五步：指定电脑玩家通用唯一识别码。\nStep 5: Specify the bot uuid.")
                                                logPrint('是否随机生成电脑玩家通用唯一识别码？（输入任意键以自行指定，否则随机生成。输入“0”以返回上一步。）\nDo you want a random bot uuid? (Submit any non-empty string to manually specify the bot uuid, or null to randomize it. Submit "0" to return to the last step.)')
                                                botUuid_strategy = logInput()
                                                botUuid_got = botUuid_strategy != "0"
                                                botUuid_randomize = botUuid_got and not bool(botUuid_strategy)
                                                if botUuid_got:
                                                    if botUuid_randomize:
                                                        botUuid = str(uuid.uuid4())
                                                    else:
                                                        logPrint("请输入电脑玩家通用唯一识别码：\nPlease specify this bot's uuid:")
                                                        botUuid = logInput()
                                                else:
                                                    step -= 2
                                            else:
                                                logPrint("发现异常步骤！请联系开发人员检查和调试代码。\nAn unexpected step is found! Please contact the developer to check and debug the code.")
                                                break
                                            step += 1
                                        if championId_got and botDifficulty_got and teamId_got and position_got and botUuid_got:
                                            body = {"championId": championId, "botDifficulty": botDifficulty, "teamId": teamId, "position": position, "botUuid": botUuid}
                                            logPrint(body)
                                            response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = body)).json()
                                            logPrint(response)
                                            if isinstance(response, dict) and "errorCode" in response:
                                                if response["message"] == "CUSTOMS_IN_PARTIES_NOT_ENABLED":
                                                    logPrint("您目前不在自定义房间内。\nYou're currently not in a custom lobby.")
                                                elif f"champ ChampionBase [{championId}] cannot be a bot as it is not enabled" in response["message"]:
                                                    logPrint("您输入的英雄没有电脑模型。\nThe champion you pick doesn't have a bot enabled.")
                                                elif f"championId associated with selected bot could not be loaded. [championId={championId}]" in response["message"]:
                                                    logPrint("英雄序号无效。\nInvalid championId.")
                                                elif response["message"] == "{botDifficulty} is not a valid LolLobbyLobbyBotDifficulty enumeration value for 'botDifficulty'":
                                                    logPrint("难度无效。\nInvalid botDifficulty.")
                                                elif "Server.Processing, com.riotgames.platform.game.TeamFullException" in response["message"]:
                                                    logPrint("%s人数已满。\n%s team is already full." %("蓝方" if teamId == "100" else "红方", "Blue" if teamId == "100" else "Red"))
                                                elif "com.riotgames.platform.messaging.UnexpectedServiceException : You must be the owner of the game to add a bot" in response["message"]:
                                                    logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the lobby owner and thus can't perform this operation.")
                                                else:
                                                    logPrint("未知错误。\nUnknown error.")
                                            else:
                                                time.sleep(GLOBAL_RESPONSE_LAG) #由于服务器响应速度原因，从添加电脑到房间信息更新，需要0.2秒的缓冲时间（0.2s buffer time is needed between adding a bot and updating the lobby information due to the server response speed）
                                                lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json() #在成功发送请求的情况下，这个接口不会出现问题（If the bot adding request was posted successfully, this endpoint should have any problems）
                                                if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                    logPrint(lobby_information)
                                                    if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                        logPrint("您还未创建任何房间。请创建一个自定义房间后再添加电脑玩家。\nYou're not in any lobby. Please first create a custom lobby and then add a bot player.")
                                                    else:
                                                        logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    break
                                                else:
                                                    bot_added = False
                                                    for member in lobby_information["gameConfig"]["customTeam100"] + lobby_information["gameConfig"]["customTeam200"]:
                                                        if member["isBot"] and member["botChampionId"] == championId and member["botDifficulty"] == botDifficulty and member["botPosition"] == position and member["botUuid"] == botUuid:
                                                            bot_added = True
                                                            break
                                                    if bot_added:
                                                        logPrint("电脑玩家添加成功。\nBot added successfully.")
                                                    else:
                                                        logPrint("电脑玩家添加失败。\nBot failed to be added.")
                                    else:
                                        logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the lobby owner and thus can't perform this operation.")
                                else:
                                    logPrint("您目前不在房间内。\nYou're currently not in a lobby.")
                            elif suboption[0] == "2":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby" or gameflow_phase == "ChampSelect":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if lobby_information["localMember"]["isLeader"]:
                                        member_df = await sort_lobby_members(connection)
                                        member_df_fields_to_print = ["teamId", "botChampionId", "botChampion_title", "botChampion_alias", "botPosition", "botDifficulty", "botUuid"]
                                        member_df_selected = pandas.concat([member_df.iloc[:1, :], member_df[member_df["isBot"] == "√"]], ignore_index = True)
                                        if len(member_df_selected) == 1:
                                            logPrint("房间内无任何电脑玩家。\nThere's not any bot player in this lobby.")
                                        else:
                                            logPrint("房间内的电脑玩家如下：\nBot players in the lobby are as follows:")
                                            print(format_df(member_df_selected.loc[:, member_df_fields_to_print], print_index = True)[0])
                                            log.write(format_df(member_df_selected.loc[:, member_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                            logPrint("请选择一个您想要删除的电脑玩家：\nPlease select a bot player you want to remove:")
                                            while True:
                                                index_got = False
                                                bot_index = logInput()
                                                if bot_index == "":
                                                    continue
                                                elif bot_index[0] == "0":
                                                    index_got = False
                                                    break
                                                elif bot_index in list(map(str, range(1, len(member_df_selected)))):
                                                    bot_index = int(bot_index)
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            if index_got:
                                                summonerInternalName = member_df_selected.loc[bot_index, "botId"]
                                                botUuidToDelete = member_df_selected.loc[bot_index, "botUuid"]
                                                botTeamId = member_df_selected.loc[bot_index, "teamId"]
                                                response = await (await connection.request("DELETE", f"/lol-lobby/v1/lobby/custom/bots/{summonerInternalName}/{botUuidToDelete}/{botTeamId}")).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["message"] == "CUSTOMS_IN_PARTIES_NOT_ENABLED":
                                                        logPrint("您目前不在自定义房间内。\nYou're currently not in a custom lobby.")
                                                    elif response["message"] == f"Unable to delete custom bot, cannot find bot with summonerInternalName {summonerInternalName}":
                                                        logPrint("未找到该电脑玩家。\nThis bot isn't found.")
                                                    elif "com.riotgames.platform.messaging.UnexpectedServiceException : You must be the owner of the game to remove a bot" in response["message"]:
                                                        logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the lobby owner and thus can't perform this operation.")
                                                    else:
                                                        logPrint("未知错误。\nUnknown error.")
                                                else:
                                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                    if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                        logPrint(lobby_information)
                                                        if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                            logPrint("您还未创建任何房间。请创建一个自定义房间后再尝试删除电脑玩家。\nYou're not in any lobby. Please first create a custom lobby and then try deleting bot players.")
                                                        else:
                                                            logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    else:
                                                        current_botUuids = set(map(lambda x: x["botUuid"], lobby_information["gameConfig"]["customTeam100"] + lobby_information["gameConfig"]["customTeam200"] + lobby_information["members"]))
                                                        if botUuidToDelete in current_botUuids:
                                                            logPrint("删除失败。\nFailed to remove this bot.")
                                                        else:
                                                            logPrint("删除成功。\nSuccessfully removed this bot.")
                                    else:
                                        logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the lobby owner and thus can't perform this operation.")
                                else:
                                    logPrint("您目前不在房间内。\nYou're currently not in a lobby.")
                            elif suboption[0] == "3":
                                gameflow_phase = await get_gameflow_phase(connection) #每一个操作都需要保证房间信息是可用的（Each operation requires the lobby information to be available）
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    preTeamId = lobby_information["localMember"]["teamId"]
                                    response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/switch-teams")).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        if response["message"] == "NOT_SUPPORTED":
                                            logPrint("当前游戏状态不支持此操作。\nYour current gameflow phase doesn't support this operation.")
                                        elif "com.riotgames.platform.game.InvalidGameStateException" in response["message"]:
                                            logPrint("您已在英雄选择阶段。\nYou're already during a champ select stage.")
                                        elif response["message"] == "Couldn't switch team, invalid team argument":
                                            logPrint("您目前正在观战。请尝试加入一个队伍再使用此操作。\nYou're now a spectator. Please join a team before using this operation.")
                                        else:
                                            logPrint("未知错误。\nUnknown error.")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                        if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                            logPrint(lobby_information)
                                            if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                logPrint("您还未创建任何房间。请创建一个自定义房间后再更换队伍。\nYou're not in any lobby. Please first create a custom lobby and then switch the team.")
                                            else:
                                                logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                        else:
                                            postTeamId = lobby_information["localMember"]["teamId"]
                                            if preTeamId == postTeamId:
                                                logPrint("更换队伍失败。请检查对方是否满员，或者等待一段时间再观察是否更换成功。\nTeam switch failed. Please check if the opponent team is full, or wait a moment to see if this switch will succeed.")
                                            else:
                                                if postTeamId == 0:
                                                    logPrint("小队不支持此操作。\nA party doesn't support this operation.")
                                                elif postTeamId == 100:
                                                    logPrint("您已加入蓝方。\nYou joined the blue team.")
                                                elif postTeamId == 200:
                                                    logPrint("您已加入红方。\nYou joined the red team.")
                                                else:
                                                    logPrint(f"您加入了一个未知阵营。\nYou joined an unknown team ({postTeamId}).")
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                            elif suboption[0] == "4":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if lobby_information["gameConfig"]["isCustom"]:
                                        try:
                                            lobbyId = lobby_information["multiUserChatId"].split("-")[0]
                                        except ValueError:
                                            logPrint("房间序号获取错误。请检查您目前是否处于自定义房间。如果这个问题持续存在，请联系开发人员。\nAn error occurred when the program was getting the lobby's id. Please check if you're still in any custom lobby. If this problem persists, please contact the developer.")
                                        else:
                                            logPrint('''警告：在使用本脚本切换观战状态时，您需要知道该自定义房间的密码。该操作不适用于训练模式，请移步客户端内手动点击“观战”按钮。\nWarning: To toggle spectate status using this program, you need to know this custom lobby's password. This operation doesn't take effect in a Practice Tool game, so you'd better click "Spectate" in the League Client.''')
                                            logPrint("请输入该自定义房间的密码。请注意，如果密码输入错误，则您会直接退出当前房间。\nPlease enter the password of this custom lobby. Note that if the password is wrong, then you'll exit this lobby directly.")
                                            password = logInput()
                                            logPrint("请选择一个角色：\nPlease select a role:\n%s1\t玩家（Player）\n%s2\t观战者（Spectator）" %("☆" if lobby_information["localMember"]["isSpectator"] else "", "" if lobby_information["localMember"]["isSpectator"] else "☆"))
                                            while True:
                                                body_got = False
                                                role_index = logInput()
                                                if role_index == "0":
                                                    body_got = False
                                                    break
                                                elif role_index[0] in ["1", "2"]:
                                                    asSpectator = role_index[0] == "2"
                                                    body_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            if body_got:
                                                response = await (await connection.request("POST", "/lol-lobby/v1/custom-games/refresh")).json()
                                                # if response == None:
                                                #     logPrint("已刷新自定义房间。\nRefreshed custom lobbies.")
                                                custom_games = await (await connection.request("GET", "/lol-lobby/v1/custom-games")).json()
                                                if isinstance(custom_games, dict) and "errorCode" in custom_games:
                                                    logPrint("自定义房间信息获取失败。\nCustom lobby information capture failed.")
                                                else:
                                                    if lobbyId in list(map(lambda x: x["id"], custom_games)): #这个条件可以保证用户在训练模式中不会被踢出房间（This condition ensures that the user should't be forced to leave the current lobby if it's a practice game）
                                                        body = {"password": password, "asSpectator": asSpectator} if bool(password) else {"asSpectator": asSpectator}
                                                        logPrint(body)
                                                        response = await (await connection.request("POST", f"/lol-lobby/v1/custom-games/{lobbyId}/join", data = body)).json()
                                                        logPrint(response)
                                                        if isinstance(response, dict) and "errorCode" in response:
                                                            if "com.riotgames.platform.game.IncorrectPasswordException" in response["message"]:
                                                                logPrint("密码错误。\nIncorrect password.")
                                                            elif "com.riotgames.platform.game.GameNotFoundException" in response["message"]:
                                                                logPrint("该房间不存在。\nThis lobby doesn't exist.")
                                                            else:
                                                                logPrint("未知错误。\nUnknown error.")
                                                        else:
                                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                            if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                                logPrint(lobby_information)
                                                                if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                                    logPrint("您似乎输入了正确的密码，但是并没有加入该自定义房间。\nYou seem to have input the correct password, but failed to join this custom lobby.")
                                                                else:
                                                                    logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                            else:
                                                                if asSpectator == lobby_information["localMember"]["isSpectator"]:
                                                                    if asSpectator:
                                                                        logPrint("您现在是观战者。\nYou're now a spectator.")
                                                                    else:
                                                                        logPrint("您现在是玩家。\nYou're now a player.")
                                                                else:
                                                                    logPrint("角色切换失败。\nRole toggle failed.")
                                                    else:
                                                        logPrint("当前游戏模式不支持通过接口来更换角色。请自行在客户端内点击。\nThis game mode doesn't support changing the role through the endpoint. Please manually click the button by yourself.")
                                    else:
                                        logPrint("您目前不在自定义房间内。\nYou're currently not in a custom lobby.")
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                            elif suboption[0] == "5": #自定义房间内没有更换模式的按钮，一旦通过鼠标点击退出房间，后续再创建新房间时，房间内就只会有自己一个人。但是在不退出原房间的情况下，房主在通过接口创建一个新的自定义房间时，旧房间的玩家会收到邀请，可视为更换模式（In the custom lobby, there's not a button to change the mode, so once the user exits the lobby by clicking the button and then creates a lobby, there'll be only the user itself in the new lobby. However, without exiting the old lobby, if the party owner creates a new custom lobby through the lobby creating endpoint, each player in the old lobby will receive an invitation, and for that reason this part may resemble "Change Mode"）
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    await create_lobby(connection)
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                            elif suboption[0] == "6":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if lobby_information["localMember"]["isLeader"]:
                                        response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/start-champ-select")).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            if response["message"] == "NOT_SUPPORTED":
                                                logPrint("您目前不在自定义房间内。\nYou're currently not in a custonm lobby.")
                                            elif response["message"] == "Custom lobby must be in team select to transition to StartChampSelect":
                                                logPrint("该房间已进入英雄选择阶段。\nThis lobby has already entered the champ select stage.")
                                            elif "com.riotgames.platform.messaging.UnexpectedServiceException : Only the owner of the game can move it into the Champion Selection state!" in response["message"]:
                                                logPrint("你必须等待对局的拥有者开始这场对局。\nYou must wait for the game owner to start the game.")
                                            elif "com.riotgames.platform.game.GameStartChampionSelectionException : Insufficient players in game." in response["message"]:
                                                logPrint("没有足够的玩家来开始游戏。\nNot enough players to start game.")
                                            else:
                                                logPrint("未知错误。\nUnknown error.")
                                        else:
                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                            gameflow_phase = await get_gameflow_phase(connection)
                                            if gameflow_phase == "ChampSelect":
                                                logPrint("您已进入英雄选择阶段。\nYou've started champion select.")
                                            else:
                                                logPrint("游戏开始失败。\nGame failed to start.")
                                    else:
                                        logPrint("你不是对局的拥有者，无法执行此操作。\nYou're not the party owner and thus can't perform this operation.")
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            logPrint("请选择一个自定义房间操作：\nPlease select a lobby operation:\n1\t添加电脑玩家（Add a bot）\n2\t移除电脑玩家（Remove a bot）\n3\t交换队伍（Switch team）\n4\t切换观战状态（Switch spectate status）\n5\t更换模式（Change mode）\n6\t开始游戏（Start game）")
                    else:
                        logPrint("小队不支持此选项。\nParty doesn't support this option.")
                elif option == "3": #相比聊天脚本，这里设计的很简约。因为本脚本所要实现的目的是实现每个接口的用法，不追求在此基础上对输入输出做进一步的优化。换句话说，聊天脚本中的对应功能可视为此处的一个升级版（Compared with the similar function in Customized Program 16, the design here is fairly simple. This is because this program only aims at implementing each endpoint, but not optimize I/O further. In other words, the corresponding function in Customized Program 16 may be regarded as an upgraded version of here）
                    lobbyMember_summonerIds = list(map(lambda x: x["summonerId"], lobby_information["members"]))
                    logPrint('请输入您想要邀请的玩家的召唤师名。输入“-1”以退出。\nPlease submit the summoner name of the player you want to invite. Submit "-1" to exit.')
                    while True:
                        invite_str = logInput()
                        if invite_str == "":
                            continue
                        elif invite_str == "-1":
                            break
                        else:
                            invitee_info = await get_info(connection, invite_str)
                            if invitee_info["info_got"]:
                                if invitee_info["selfInfo"]:
                                    logPrint("你不能邀请你自己，亲～\nYou can't invite yourself, silly xD")
                                else:
                                    invitee_summonerName = get_info_name(invitee_info["body"])
                                    invitee_summonerId = invitee_info["body"]["summonerId"]
                                    if invitee_summonerId in lobbyMember_summonerIds:
                                        logPrint(f"{invitee_summonerName}已在房间内。\n{invitee_summonerName} is already in the lobby.")
                                    else:
                                        body = [{"toSummonerId": invitee_summonerId}]
                                        response = await (await connection.request("POST", "/lol-lobby/v2/lobby/invitations", data = body)).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            logPrint("邀请失败。\nFailed to send the invitation.")
                                        else:
                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                            lobby_invitations = await (await connection.request("GET", "/lol-lobby/v2/lobby/invitations")).json()
                                            if isinstance(lobby_invitations, dict) and "errorCode" in lobby_invitations:
                                                if lobby_invitations["httpStatus"] == 404 and lobby_invitations["message"] == "LOBBY_NOT_FOUND":
                                                    logPrint("您已离开房间。\nYou've left the original lobby.")
                                                    break
                                            else:
                                                accepted_invitations = filter(lambda x: x["state"] == "Accepted", lobby_invitations)
                                                pending_invitations = filter(lambda x: x["state"] == "Pending", lobby_invitations)
                                                accepted_summonerIds = list(map(lambda x: x["toSummonerId"], accepted_invitations))
                                                pending_summonerIds = list(map(lambda x: x["toSummonerId"], pending_invitations))
                                                if invitee_summonerId in accepted_summonerIds:
                                                    logPrint(f"{invitee_summonerName}已在房间内。\n{invitee_summonerName} is already in the party/lobby.")
                                                elif invitee_summonerId in pending_summonerIds:
                                                    logPrint(f"{invitee_summonerName}已收到邀请。\n{invitee_summonerName} received your invitation.")
                                                else:
                                                    logPrint(f"{invitee_summonerName}未能收到邀请。这可能是因为您还没有邀请权限，您的房间已经满员，对方不在线，对方只接受好友游戏邀请，或者对方将您拉入了聊天黑名单。\n{invitee_summonerName} didn't receive your invitation. Maybe you don't have invite priviledges, your lobby is already full, they're offline, they allow game invites only from friends, or they blocked you.")
                            else:
                                logPrint(invitee_info["message"])
                elif option == "5":
                    if lobby_information["localMember"]["isLeader"]:
                        member_df = await sort_lobby_members(connection)
                        member_df_fields_to_print = ["gameName", "tagLine", "summonerLevel", "summonerIcon_title"]
                        member_df_selected = pandas.concat([member_df.iloc[:1, :], member_df[member_df["isBot"] == ""]], ignore_index = True)
                        if len(member_df_selected) == 2:
                            logPrint("当前房间内无其它人类成员。\nThere's not any other human member in this party/lobby.")
                        else:
                            logPrint("当前房间内的人类玩家如下：\nHuman players in this lobby are as follows:")
                            print(format_df(member_df_selected.loc[:, member_df_fields_to_print], print_index = True))
                            log.write(format_df(member_df_selected.loc[:, member_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True) + "\n")
                            logPrint("请选择一名成员：\nPlease select a member:")
                            while True:
                                index_got = False
                                member_index = logInput()
                                if member_index == "":
                                    continue
                                elif member_index == "0":
                                    index_got = False
                                    break
                                elif member_index in list(map(str, range(1, len(member_df_selected)))):
                                    member_index = int(member_index)
                                    index_got = True
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                member_summonerId = member_df_selected.loc[member_index, "summonerId"]
                                member_summonerName = member_df_selected.loc[member_index, "gameName"] + "#" + member_df_selected.loc[member_index, "tagLine"]
                                logPrint(f"您选择了{member_summonerName}.\nYou selected %s.")
                                logPrint("请选择一项操作：\nPlease select an operation:\n0\t返回上一层（Return to the last step）\n1\t晋升为小队拥有者（Promote to party owner）\n2\t将玩家移出小队（Kick player from party）\n3\t更改邀请权限（Change invite priviledge）")
                                while True:
                                    operation = logInput()
                                    if operation == "":
                                        continue
                                    elif operation[0] == "0":
                                        break
                                    elif operation[0] == "1":
                                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/promote")).json()
                                        if isinstance(response, dict) and "errorCode" in response:
                                            if response["message"] == "Cannot promote when not leader":
                                                logPrint("只有小队拥有者才可以将他人晋升为小队拥有者。\nOnly the party owner can promote another member to be the new party owner.")
                                            elif response["message"] == "SUMMONER_NOT_FOUND":
                                                logPrint("未找到该召唤师。或者您已经退出房间。\nSummoner not found. Or you've left the lobby.")
                                            else:
                                                logPrint("未知错误。\nUnknown error.")
                                        else:
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                logPrint(lobby_information)
                                                if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                    logPrint("您还未创建任何房间。请创建一个小队后再更改他人角色。\nYou're not in any lobby. Please first create a party and then change another member's role.")
                                                else:
                                                    logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                            else:
                                                for member in lobby_information["members"]:
                                                    if member["summonerId"] == member_summonerId:
                                                        break
                                                if member["isLeader"]:
                                                    logPrint(f"您已将{member_summonerName}晋升为新的小队拥有者。\nYou promoted {member_summonerName} as the new party owner.")
                                                else:
                                                    logPrint("晋升失败。\nPromotion failed.")
                                    elif operation[0] == "2":
                                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/kick")).json()
                                        if isinstance(response, dict) and "errorCode" in response:
                                            if response["message"] == "INVALID_ROLE_TRANSITION":
                                                logPrint("你不能遣离你自己。\nYou can't kick yourself.")
                                            elif response["message"] == "NOT_AUTHORIZED":
                                                logPrint("只有小队拥有者才可以将他人移出小队。\nOnly the party owner can kick another member from the party/lobby.")
                                            elif response["message"] == "SUMMONER_NOT_FOUND":
                                                logPrint("未找到该召唤师。或者您已经退出房间。\nSummoner not found. Or you've left the lobby.")
                                            else:
                                                logPrint("未知错误。\nUnknown error.")
                                        else:
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                logPrint(lobby_information)
                                                if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                    logPrint("您还未创建任何房间。请创建一个小队后再尝试将他人移出小队。\nYou're not in any lobby. Please first create a party and then try kicking a member.")
                                                else:
                                                    logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                            else:
                                                if member_summonerId in list(map(lambda x: x["summonerId"], lobby_information["members"])):
                                                    logPrint("遣离失败。\nKick failed.")
                                                else:
                                                    logPrint(f"您已将{member_summonerName}移出该小队/房间。\nYou kicked {member_summonerName} from the party/lobby.")
                                    elif operation[0] == "3":
                                        logPrint("您想要提供还是撤回邀请权限？\nDo you want to grant or revoke invites?\n1\t提供邀请权限（Grant invites）\n2\t撤回邀请权限（Revoke invites）")
                                        while True:
                                            suboperation = logInput()
                                            if suboperation == "":
                                                continue
                                            elif suboperation[0] == "0":
                                                break
                                            elif suboperation[0] == "1":
                                                response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/grant-invite")).json()
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["message"] == "INVALID_MEMBER":
                                                        logPrint("你不能更改你自己的邀请权限。\nYou can't change the invite priviledge of yourself.")
                                                    elif response["message"] == "PARTY_LEADER_REQUIRED":
                                                        logPrint("只有小队拥有者才可以为他人提供邀请权限。\nOnly the party owner can grant invites to other members.")
                                                    elif response["message"] == "SUMMONER_NOT_FOUND":
                                                        logPrint("未找到该召唤师。或者您已经退出房间。\nSummoner not found. Or you've left the lobby.")
                                                    else:
                                                        logPrint("未知错误。\nUnknown error.")
                                                else:
                                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                    if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                        logPrint(lobby_information)
                                                        if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                            logPrint("您还未创建任何房间。请创建一个小队后再尝试更改他人的邀请权限。\nYou're not in any lobby. Please first create a party and then try changing another member's invite priviledge.")
                                                        else:
                                                            logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    else:
                                                        for member in lobby_information["members"]:
                                                            if member["summonerId"] == member_summonerId:
                                                                break
                                                        if member["allowedInviteOthers"]:
                                                            logPrint(f"{member_summonerName}可以邀请玩家加入这局游戏。\n{member_summonerName} may invite players to this game.")
                                                        else:
                                                            logPrint("提供邀请权限失败。\nInvite priviledge grant failed.")
                                            elif suboperation[0] == "2":
                                                response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/grant-invite")).json()
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["message"] == "INVALID_MEMBER":
                                                        logPrint("你不能更改你自己的邀请权限。\nYou can't change the invite priviledge of yourself.")
                                                    elif response["message"] == "PARTY_LEADER_REQUIRED":
                                                        logPrint("只有小队拥有者才可以撤回他人的邀请权限。\nOnly the party owner can revoke invites from other members.")
                                                    elif response["message"] == "SUMMONER_NOT_FOUND":
                                                        logPrint("未找到该召唤师。或者您已经退出房间。\nSummoner not found. Or you've left the lobby.")
                                                    else:
                                                        logPrint("未知错误。\nUnknown error.")
                                                else:
                                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                    if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                        logPrint(lobby_information)
                                                        if lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                            logPrint("您还未创建任何房间。请创建一个小队后再尝试更改他人的邀请权限。\nYou're not in any lobby. Please first create a party and then try changing another member's invite priviledge.")
                                                        else:
                                                            logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    else:
                                                        for member in lobby_information["members"]:
                                                            if member["summonerId"] == member_summonerId:
                                                                break
                                                        if member["allowedInviteOthers"]:
                                                            logPrint("撤回邀请权限失败。\nInvite priviledge revoke failed.")
                                                        else:
                                                            logPrint(f"{member_summonerName}不再能邀请玩家加入这局游戏。\n{member_summonerName} may no longer invite players to this game.")
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    logPrint("请选择一项操作：\nPlease select an operation:\n0\t返回上一层（Return to the last step）\n1\t晋升为小队拥有者（Promote to party owner）\n2\t将玩家移出小队（Kick player from party）\n3\t更改邀请权限（Change invite priviledge）")
                    else:
                        logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the party/lobby owner and thus can't perform this operation.")
                elif option == "9":
                    response = await (await connection.request("DELETE", "/lol-lobby/v2/lobby")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        logPrint("退出房间失败。\nExit failed.")
                    else:
                        time.sleep(GLOBAL_RESPONSE_LAG)
                        gameflow_phase = await get_gameflow_phase(connection)
                        if gameflow_phase == "None":
                            logPrint("您已成功退出房间。\nYou've exited the lobby successfully.")
                        elif gameflow_phase == "Lobby":
                            logPrint("退出房间失败。请稍后通过客户端确认游戏状态。\nExit failed. Please check your gameflow phase in the League Client later.")
                        else:
                            logPrint("您的游戏状态发生异常。\nAn error occurred to your gameflow phase.")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
        elif option == "4":
            await chat(connection)
        elif option == "6":
            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            logPrint(lobby_information)
            with open("lobby-information.json", "w", encoding = "utf-8") as fp:
                json.dump(lobby_information, fp, indent = 4, ensure_ascii = False)
            logPrint('房间信息已导出到同目录下的“lobby-information.json”。\nLobby information has been exported into "lobby-information.json" under the same directory.')
        elif option == "7":
            await handle_invitations(connection)
        elif option == "8":
            await join_game(connection)
        elif option == "10":
            logPrint('请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n2\t扩展对局记录（Expand match history）')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await toggle_nonfriend_game_invite(connection)
                elif suboption[0] == "2":
                    await expand_match_history(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n2\t扩展对局记录（Expand match history）')
        elif option == "11":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 队列阶段模拟（In-queue stage simulation）
#-----------------------------------------------------------------------------
async def inQueue_simulation(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t输出寻找对局信息（Print matchmaking information）\n2\t聊天（Chat）\n3\t处理邀请（Handle invitations）\n4\t加入小队或自定义房间（Join party/lobby）\n5\t退出队列（Quit the queue）\n6\t其它（Others）\n7\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('''请选择一个寻找对局相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a matchmaking-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n1\t查看就位确认信息（Check ready-check information）\n2\t接受对局（Accept the match）\n3\t拒绝对局（Decline the match）\n4\t退出对局寻找（Exit finding match）\n5\t查看寻找对局过程（Check the process of finding match）\n6\t（无效）寻找对局（(Invalid) Find match）\n!7\t强制修改对局寻找信息（Force to change matchmaking search information）\n8\t查看寻找对局过程中的错误（Check errors during the matchmaking phase）\n9\t查看一条寻找对局过程中的错误（Check an error during the matchmaking phase）''')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection)
                elif suboption[0] == "0":
                    break
                elif suboption[0] in list(map(str, range(1, 10))):
                    if suboption[0] == "1":
                        response = await (await connection.request("GET", "/lol-matchmaking/v1/ready-check")).json()
                    elif suboption[0] == "2":
                        response = await (await connection.request("POST", "/lol-matchmaking/v1/ready-check/accept")).json()
                    elif suboption[0] == "3":
                        response = await (await connection.request("POST", "/lol-matchmaking/v1/ready-check/decline")).json()
                    elif suboption[0] == "4":
                        response = await (await connection.request("DELETE", "/lol-matchmaking/v1/search")).json()
                    elif suboption[0] == "5":
                        response = await (await connection.request("GET", "/lol-matchmaking/v1/search")).json()
                    elif suboption[0] == "6":
                        response = await (await connection.request("POST", "/lol-matchmaking/v1/search")).json()
                    elif suboption[0] == "7":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"queueId": 0, "isCurrentlyInQueue": True, "lobbyId": "string", "searchState": "ServiceShutdown", "timeInQueue": 0, "estimatedQueueTime": 0, "readyCheck": {"state": "Error", "playerResponse": "Declined", "dodgeWarning": "ConnectionWarning", "timer": 0, "declinerIds": [0], "suppressUx": True}, "dodgeData": {"state": "TournamentDodged", "dodgerId": 0}, "lowPriorityData": {"penalizedSummonerIds": [0], "penaltyTime": 0, "penaltyTimeRemaining": 0, "bustedLeaverAccessToken": "string", "reason": "string"}, "errors": [{"id": 0, "errorType": "string", "penalizedSummonerId": 0, "penaltyTimeRemaining": 0, "message": "string"}]}\nsearch = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                        response = await (await connection.request("PUT", "/lol-matchmaking/v1/search")).json()
                    elif suboption[0] == "8":
                        response = await (await connection.request("GET", "/lol-matchmaking/v1/search/errors")).json()
                    else:
                        logPrint("请输入异常信息序号：\nPlease input the id of the error:\nid = ", end = "")
                        errorId = logInput()
                        response = await (await connection.request("GET", f"/lol-matchmaking/v1/search/errors/{errorId}")).json()
                    logPrint(response)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option[0] == "0":
            break
        elif option[0] == "1":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase in ["Matchmaking", "ReadyCheck"]:
                matchmaking_information = await (await connection.request("GET", "/lol-matchmaking/v1/search")).json()
                logPrint(matchmaking_information)
                with open("matchmaking-search.json", "w", encoding = "utf-8") as fp:
                    json.dump(matchmaking_information, fp, indent = 4, ensure_ascii = False)
                logPrint('寻找队列信息已导出到同目录下的“matchmaking-search.json”。\nMatchmaking information has been exported into "matchmaking-search.json" under the same directory.')
            else:
                logPrint("您目前不在队列中。\nYou're currently not in a matchmaking queue.")
        elif option[0] == "2":
            await chat(connection)
        elif option[0] == "3":
            await handle_invitations(connection)
        elif option[0] == "4":
            await join_game(connection)
        elif option[0] == "5":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "Matchmaking":
                response = await (await connection.request("DELETE", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                logPrint(response)
                if isinstance(response, dict) and "errorCode" in response:
                    if response["message"] == "INVALID_PARTY_STATE":
                        logPrint("当前小队状态不允许退出队列。\nCurrent party state doesn't allow the queue exit action.")
                    else:
                        logPrint("退出队列失败。请检查您的客户端运行状况。如果这个问题持续存在，请重启您的客户端。\nQueue exit failed. Please check your client's running status. If this problem persists, please restart your client.")
                else:
                    time.sleep(GLOBAL_RESPONSE_LAG)
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "Lobby":
                        logPrint("退出队列成功。您已返回房间。\nQueue exit succeeded. You returned to the lobby.")
                    else:
                        logPrint("服务器接收到了退出队列请求，但您的状态似乎还没有更新。\nThe server received your queue exit request, but it seems your gameflow phase hasn't been updated yet.")
            else:
                logPrint("您目前不在队列中，或者已经找到对局。\nYou're currently not in a matchmaking queue, or a match is found.")
        elif option[0] == "6":
            logPrint('请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n2\t扩展对局记录（Expand match history）')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await toggle_nonfriend_game_invite(connection)
                elif suboption[0] == "2":
                    await expand_match_history(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n2\t扩展对局记录（Expand match history）')
        elif option[0] == "7":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 就位确认阶段模拟（Match accept stage simulation）
#-----------------------------------------------------------------------------
async def readyCheck_simulation(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t接受（Accept）\n2\t拒绝（Decline）\n3\t输出就位确认阶段信息（Print the ready check information）\n4\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] in list(map(str, range(1, 4))):
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "ReadyCheck":
                if option[0] == "1":
                    response = await (await connection.request("POST", "/lol-matchmaking/v1/ready-check/accept")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        if response["httpStatus"] == 500 and "Failed to indicate team builder ready check readiness" in response["message"]:
                            logPrint("无法获取阵容匹配就绪状态。请检查服务器是否维护中。\nFailed to get team builder ready-check availability. Please check if the server is under mainteinance.")
                        else:
                            logPrint("接受对局失败。\nFailed to accept ready check.")
                    else:
                        time.sleep(GLOBAL_RESPONSE_LAG)
                        readyCheck_information = await (await connection.request("GET", "/lol-matchmaking/v1/ready-check")).json()
                        if isinstance(readyCheck_information, dict) and "errorCode" in readyCheck_information: #有时，在点“接受”后的一瞬间，就位确认窗口会立刻消失（Sometimes, as soon as the user clicked "Accept", the ready check window disappears）
                            logPrint("发送接受对局的请求过程出现了问题。\nAn error occurred when the program posted the request to accept the match.")
                        else:
                            if readyCheck_information["playerResponse"] == "Accepted":
                                logPrint("接受对局成功。\nMatch accepted successfully.")
                            else:
                                logPrint("接受对局失败。\nFailed to accept ready check.")
                elif option[0] == "2":
                    response = await (await connection.request("POST", "/lol-matchmaking/v1/ready-check/decline")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        if response["httpStatus"] == 500 and "Failed to indicate team builder ready check readiness" in response["message"]:
                            logPrint("无法获取阵容匹配就绪状态。请检查服务器是否维护中。\nFailed to get team builder ready-check availability. Please check if the server is under mainteinance.")
                        else:
                            logPrint("拒绝对局失败。\nFailed to decline ready check.")
                    else:
                        time.sleep(GLOBAL_RESPONSE_LAG)
                        readyCheck_information = await (await connection.request("GET", "/lol-matchmaking/v1/ready-check")).json()
                        if isinstance(readyCheck_information, dict) and "errorCode" in readyCheck_information:
                            logPrint("发送拒绝对局的请求过程出现了问题。\nAn error occurred when the program posted the request to decline the match.")
                        else:
                            if readyCheck_information["playerResponse"] == "Declined":
                                logPrint("拒绝对局成功。\nMatch declined successfully.")
                            else:
                                logPrint("拒绝对局失败。\nFailed to decline ready check.")
                else:
                    readyCheck_information = await (await connection.request("GET", "/lol-matchmaking/v1/ready-check")).json()
                    logPrint(readyCheck_information)
                    with open("readyCheck.json", "w", encoding = "utf-8") as fp:
                        json.dump(readyCheck_information, fp, indent = 4, ensure_ascii = False)
                    logPrint('就位确认信息已导出到同目录下的“readyCheck.json”。\nReady check information has been exported into "readyCheck.json" under the same directory.')
            else:
                logPrint("您目前不在就位确认阶段。\nYou're currently not at the ready check stage.")
        elif option[0] == "4":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 英雄选择阶段模拟（Champ select stage simulation）
#-----------------------------------------------------------------------------
async def get_current_player(connection) -> dict:
    champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    players = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
    for player in players:
        if player["puuid"] == current_info["puuid"]:
            return player
    else:
        return {}

async def sort_ChampSelect_players(connection, playerMode: int = 1) -> pandas.DataFrame: #以下代码来自聊天服务脚本（The following code come from Customized Program 16）
    #所需数据初始化（Initialization of needed data）
    champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    champSelect_players_data = {}
    for i in range(len(champSelect_players_header_keys)):
        key = champSelect_players_header_keys[i]
        champSelect_players_data[key] = []
    if playerMode == 1:
        players = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
    elif playerMode == 2:
        players = champ_select_session["myTeam"]
    elif playerMode == 3:
        players = champ_select_session["theirTeam"]
    else:
        players = []
    #数据整理核心部分（Data assignment - core part）
    for player in players:
        if player["nameVisibilityType"] != "HIDDEN":
            player_info_recapture = 0
            player_info = await get_info(connection, player["puuid"])
            while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                logPrint(player_info["message"])
                player_info_recapture += 1
                logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s, cellId: %d) capture failed! Recapturing this player's information ... Times tried: %d" %(player["cellId"], player["puuid"], player_info_recapture, player["puuid"], player["cellId"], player_info_recapture))
                player_info = await get_info(connection, player["puuid"])
            if not player_info["info_got"]:
                logPrint(player_info["message"])
                logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s, cellId: %d) capture failed!" %(player["cellId"], player["puuid"], player["puuid"], player["cellId"]))
        for i in range(len(champSelect_players_header_keys)):
            key = champSelect_players_header_keys[i]
            if i <= 21:
                if i in {4, 5, 19}: #召唤师信息相关键（Summoner information-related keys）
                    champSelect_players_data[key].append(player[key] if player["nameVisibilityType"] == "HIDDEN" else player_info["body"][key] if player_info["info_got"] else "")
                else:
                    champSelect_players_data[key].append(player[key])
            else:
                if i == 22: #阵营名称（`team_color`）
                    champSelect_players_data[key].append(team_colors_int[player["team"]])
                elif i <= 24: #选用英雄相关键（Champion-related keys）
                    champSelect_players_data[key].append(LoLChampions[player["championId"]][key.split()[1]] if player["championId"] in LoLChampions else "")
                elif i <= 26: #声明英雄相关键（Champion pick intent-related keys）
                    champSelect_players_data[key].append(LoLChampions[player["championPickIntent"]][key.split()[1]] if player["championPickIntent"] in LoLChampions else "")
                elif i <= 36: #选用皮肤相关键（selected skin-related keys）
                    selectedSkinId = player["selectedSkinId"]
                    if selectedSkinId in championSkins and key.split()[1] in championSkins[selectedSkinId]:
                        if i == 27 or i == 28:
                            champSelect_players_data[key].append(championSkins[selectedSkinId][key.split()[1]])
                        elif i == 34:
                            champSelect_players_data[key].append(krarities[championSkins[selectedSkinId][key.split()[1]]])
                        else:
                            iconPath = championSkins[selectedSkinId][key.split()[1]]
                            champSelect_players_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                    else:
                        champSelect_players_data[key].append("")
                elif i <= 38: #召唤师技能1相关键（Summoner spell 1-related keys）
                    if player["spell1Id"] in spells:
                        if i == 37:
                            champSelect_players_data[key].append(spells[player["spell1Id"]][key.split()[1]])
                        else:
                            iconPath = spells[player["spell1Id"]][key.split()[1]]
                            champSelect_players_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                    else:
                        champSelect_players_data[key].append("")
                elif i <= 40: #召唤师技能2相关键（Summoner spell 2-related keys）
                    if player["spell2Id"] in spells:
                        if i == 39:
                            champSelect_players_data[key].append(spells[player["spell2Id"]][key.split()[1]])
                        else:
                            iconPath = spells[player["spell2Id"]][key.split()[1]]
                            champSelect_players_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                    else:
                        champSelect_players_data[key].append("")
                else: #饰品相关键（Ward-related keys）
                    if player["wardSkinId"] in wardSkins:
                        if i == 43 or i == 44:
                            iconPath = wardSkins[player["wardSkinId"]][key.split()[1]]
                            champSelect_players_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                        elif i == 46:
                            champSelect_players_data[key].append(wardSkins[player["wardSkinId"]]["rarities"][0]["rarity"])
                        else:
                            champSelect_players_data[key].append(wardSkins[player["wardSkinId"]][key.split()[1]])
                    else:
                        champSelect_players_data[key].append("")
    #数据框列序整理（Dataframe column ordering）
    champSelect_players_statistics_output_order = [20, 22, 1, 4, 19, 5, 12, 18, 14, 9, 8, 7, 6, 0, 2, 23, 24, 3, 25, 26, 16, 37, 38, 17, 39, 40, 15, 27, 28, 34, 29, 30, 31, 32, 33, 35, 36, 21, 41, 42, 46, 45, 43, 44, 13, 10, 11]
    champSelect_players_data_organized = {}
    for i in champSelect_players_statistics_output_order:
        key = champSelect_players_header_keys[i]
        champSelect_players_data_organized[key] = champSelect_players_data[key]
    champSelect_players_df = pandas.DataFrame(data = champSelect_players_data_organized)
    for column in champSelect_players_df:
        if champSelect_players_df[column].dtype == "bool":
            champSelect_players_df[column] = champSelect_players_df[column].astype(str)
            for i in range(len(champSelect_players_df)):
                champSelect_players_df.loc[i, column] = "√" if champSelect_players_df[column][i] == "True" else ""
    champSelect_players_df = pandas.concat([pandas.DataFrame([champSelect_players_header])[champSelect_players_df.columns], champSelect_players_df], ignore_index = True)
    return champSelect_players_df

async def get_LoLChampions(connection) -> pandas.DataFrame: #以下代码来自查英雄脚本（The following code are from Customized Program 04）
    LoLChampions_data = {}
    recommended_position_for_champion = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    for i in range(len(LoLChampions_header_keys)):
        key = LoLChampions_header_keys[i]
        LoLChampions_data[key] = []
    for i in sorted(LoLChampions.keys()):
        champion = LoLChampions[i]
        for j in range(len(LoLChampions_header_keys)):
            key = LoLChampions_header_keys[j]
            if j <= 17:
                if j == 17: #购买日期（`purchased`）
                    if champion["purchased"] == 0:
                        LoLChampions_data[key].append("")
                    else:
                        try:
                            LoLChampions_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion["purchased"] // 1000)))
                        except OSError: #出现了购买时间戳为18446744073709550616的英雄（There's a champion with the purchased timestamp 18446744073709550616）
                            LoLChampions_data[key].append("")
                else:
                    LoLChampions_data[key].append(champion[key])
            elif j <= 26: #拥有权子键（`ownership`'s subkeys）
                if j <= 20:
                    LoLChampions_data[key].append(champion["ownership"][key.split(": ")[1]])
                else:
                    if j == 25 or j == 26:
                        if champion["ownership"]["rental"][key.split(": ")[2].replace("Time", "Date")] == 0:
                            LoLChampions_data[key].append("")
                        else:
                            try:
                                LoLChampions_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion["ownership"]["rental"][key.split(": ")[2].replace("Time", "Date")] // 1000)))
                            except OSError: #出现了租借时间戳为18446744073709550616的英雄（There's a champion with the rented timestamp 18446744073709550616）
                                LoLChampions_data[key].append("")
                    else:
                        LoLChampions_data[key].append(champion["ownership"]["rental"][key.split(": ")[2]])
            elif j <= 32: #角色定位相关键（Role related keys）
                LoLChampions_data[key].append(key.split(": ")[1] in champion["roles"])
            elif j <= 35: #战略信息子键（`tacticalInfo`'s subkeys）
                if j == 33: #战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】（`tacticalInfo: damageType`）
                    LoLChampions_data[key].append(damageTypes[champion["tacticalInfo"][key.split(": ")[1]]])
                else:
                    LoLChampions_data[key].append(champion["tacticalInfo"][key.split(": ")[1]])
            elif j <= 37: #被动技能子键（`passive`'s subkeys）
                LoLChampions_data[key].append(champion["passive"][key.split(": ")[1]])
            elif j <= 45: #技能相关键（Spell related keys）
                spell_index = int(key[5:6]) - 1
                if spell_index < len(champion["spells"]):
                    LoLChampions_data[key].append(champion["spells"][spell_index][key.split(": ")[1]])
                else:
                    LoLChampions_data[key].append("")
            else:
                if champion["id"] == -1:
                    LoLChampions_data[key].append(False)
                elif key.split(": ")[1] in recommended_position_for_champion[str(champion["id"])]["recommendedPositions"]:
                    LoLChampions_data[key].append(True)
                else:
                    LoLChampions_data[key].append(False)
    LoLChampions_statistics_output_order = [9, 11, 16, 1, 10, 5, 27, 28, 29, 30, 31, 32, 46, 47, 48, 49, 50, 33, 35, 34, 19, 17, 18, 20, 8, 23, 26, 25, 24, 13, 7, 14, 3, 4, 15, 6, 2, 37, 39, 41, 43, 45]
    LoLChampions_data_organized = {}
    for i in LoLChampions_statistics_output_order:
        key = LoLChampions_header_keys[i]
        LoLChampions_data_organized[key] = LoLChampions_data[key]
    LoLChampions_df = pandas.DataFrame(data = LoLChampions_data_organized)
    for column in LoLChampions_df:
        if LoLChampions_df[column].dtype == "bool":
            LoLChampions_df[column] = LoLChampions_df[column].astype(str)
            for i in range(len(LoLChampions_df)):
                LoLChampions_df.loc[i, column] = "√" if LoLChampions_df[column][i] == "True" else ""
    LoLChampions_df = pandas.concat([pandas.DataFrame([LoLChampions_header])[LoLChampions_df.columns], LoLChampions_df], ignore_index = True)
    return LoLChampions_df

async def sort_grid_champions(connection) -> pandas.DataFrame:
    grid_champions = await (await connection.request("GET", "/lol-champ-select/v1/all-grid-champions")).json()
    grid_champion_data = {}
    for i in range(len(grid_champion_header_keys)):
        key = grid_champion_header_keys[i]
        grid_champion_data[key] = []
    for champion in grid_champions:
        for i in range(len(grid_champion_header_keys)):
            key = grid_champion_header_keys[i]
            if i <= 17:
                if i >= 13: #最爱位置相关键（`positionsFavorited`-related keys）
                    grid_champion_data[key].append(key.split("_")[1].lower() in list(map(lambda x: x.lower(), champion["positionsFavorited"])))
                else:
                    grid_champion_data[key].append(champion[key])
            else:
                grid_champion_data[key].append(champion["selectionStatus"][key])
    grid_champion_statistics_output_order = [3, 7, 5, 6, 8, 10, 4, 12, 1, 2, 0, 9, 13, 14, 15, 16, 17, 11, 18, 19, 20, 21, 22, 23, 24, 25]
    grid_champion_data_organized = {}
    for i in grid_champion_statistics_output_order:
        key = grid_champion_header_keys[i]
        grid_champion_data_organized[key] = grid_champion_data[key]
    grid_champion_df = pandas.DataFrame(data = grid_champion_data_organized)
    for column in grid_champion_df:
        if grid_champion_df[column].dtype == "bool":
            grid_champion_df[column] = grid_champion_df[column].astype(str)
            for i in range(len(grid_champion_df)):
                grid_champion_df.loc[i, column] = "√" if grid_champion_df[column][i] == "True" else ""
    grid_champion_df = pandas.concat([pandas.DataFrame([grid_champion_header])[grid_champion_df.columns], grid_champion_df], ignore_index = True)
    return grid_champion_df

async def sort_swaps_info(connection, swap_typeId: int) -> pandas.DataFrame:
    champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    swap_types = {1: "pickOrderSwaps", 2: "positionSwaps", 3: "trades"}
    swaps = sorted(champ_select_session[swap_types[swap_typeId]], key = lambda x: x["cellId"])
    swaps_header = {"cellId": "槽位序号", "id": "交换代码", "state": "可交换性"}
    swaps_header_keys = list(swaps_header.keys())
    swaps_data = {}
    for i in range(len(swaps_header_keys)):
        key = swaps_header_keys[i]
        swaps_data[key] = []
    for swap in swaps:
        for i in range(len(swaps_header_keys)):
            key = swaps_header_keys[i]
            swaps_data[key].append(swap[key])
    swaps_statistics_output_order = [1, 0, 2]
    swaps_data_organized = {}
    for i in swaps_statistics_output_order:
        key = swaps_header_keys[i]
        swaps_data_organized[key] = swaps_data[key]
    swaps_df = pandas.DataFrame(data = swaps_data_organized)
    swaps_df = pandas.concat([pandas.DataFrame([swaps_header])[swaps_df.columns], swaps_df], ignore_index = True)
    #下面将玩家信息附加到数据框右侧（The following code appends player information to the right of the dataframe）
    players_df = await sort_ChampSelect_players(connection, playerMode = 2) #默认交换动作只能发生在队友之间。这是因为在极地大乱斗中，双方的槽位序号竟然是相同的（By default, swaps should happen among teammates. Another thing worth mentioning is that in the champ select session of an ARAM game, both teams' cellIds are the same）
    merged_df = pandas.merge(swaps_df, players_df, how = "inner", on = "cellId")
    return merged_df

async def sort_skin_data(connection) -> pandas.DataFrame:
    logPrint("[sort_skin_data]正在获取英雄和皮肤数据…… | Preparing champion and skin data ...", print_time = True)
    LoLChampions_source = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
    LoLChampions = {}
    skins_flat = {}
    for champion in LoLChampions_source:
        LoLChampions[champion["id"]] = champion
        for skin in champion["skins"]:
            skins_flat[skin["id"]] = skin
            for chroma in skin["chromas"]:
                skins_flat[chroma["id"]] = chroma
            for tier in skin["questSkinInfo"]["tiers"]:
                if not tier["id"] in skins_flat: #圣堂皮肤和终极皮肤中的系列与主皮肤存在重复的序号（There're redundant ids between the tier and the parent ultimate skin）
                    skins_flat[tier["id"]] = tier
    #静态皮肤数据的定义代码放在全局变量函数中（Static skin data related code are put under `define_global_variables` function）
    skins_data = {}
    for i in range(len(skins_header_keys)):
        key = skins_header_keys[i]
        skins_data[key] = []
    logPrint("[sort_skin_data]正在整理数据…… | Sorting data ...", print_time = True)
    skinIds = sorted(set(championSkins.keys()) & set(skins_flat.keys())) #在2025年8月15日，美测服在`/lol-champions/v1/inventories/{summonerId}/champions`接口中删除了德邦总管 赵信及其所有皮肤信息，导致下面出现键错误。考虑到当天有玩家反馈无法选用赵信，所以这里取`championSkins`和`skins_flat`的键的交集（On Aug. 15th, 2025, Xin Zhao is removed from the response body of the endpoint `lol-champions/v1/inventories/{summonerId}/champions`. Considering some player reported that Xin Zhao can't be selected on that day, here we take the intersection of the keys of `championSkins` and `skins_flat`）
    for skin_index in range(len(skinIds)):
        skinId = skinIds[skin_index]
        # logPrint("数据整理进度（Data sorting process）：%d/%d" %(skin_index + 1, len(skinIds)), end = "\r", print_time = True)
        skin = championSkins[skinId]
        skin_flat = skins_flat[skinId]
        for i in range(len(skins_header_keys)):
            key = skins_header_keys[i]
            if i <= 40: #来自（From）：`/lol-game-data/assets/v1/skins.json`
                if i <= 28:
                    if i == 15: #品质（`rarity`）
                        skins_data[key].append(krarities[skin[key]] if key in skin else "")
                    elif i == 20: #皮肤类别（`skinClassification`）
                        skins_data[key].append(skinClassifications[skin[key]] if key in skin else "")
                    elif i == 22: #皮肤套装（`skinLines`）
                        skins_data[key].append("" if not key in skin or skin[key] == None else list(map(lambda x: skinlines[x["id"]]["name"], skin[key])))
                    else:
                        skins_data[key].append(skin.get(key, False if i in [8, 9] else ""))
                elif i <= 32: #标志相关键（Emblem-related keys）
                    if not "emblems" in skin or skin["emblems"] == None:
                        skins_data[key].append("")
                    else:
                        if i <= 30:
                            skins_data[key].append(skin["emblems"][0][key.split("_")[1]])
                        else:
                            skins_data[key].append(skin["emblems"][0]["emblemPath"][key.split("_")[1]])
                else: #任务皮肤信息相关键（QuestSkinInfo-related keys）
                    skins_data[key].append(skin[key.split()[0]][key.split()[1]] if key.split()[0] in skin else "")
            else: #来自（From）：`/lol-champions/v1/inventories/{summonerId}/champions`
                if i <= 47:
                    if i >= 45: #英雄相关键（Champion-related keys）
                        skins_data[key].append(LoLChampions[skin_flat["championId"]][key.split("_")[1]] if "championId" in skin_flat and skin_flat["championId"] in LoLChampions else "")
                    else:
                        skins_data[key].append(skin_flat.get(key, False if i in [42, 43, 44] else ""))
                elif i <= 50: #拥有权相关键（Ownership-related keys）
                    skins_data[key].append(skin_flat[key.split()[0]][key.split()[1]])
                else: #租借相关键（Rental-related keys）
                    if i >= 55: #日期相关键（Date-related keys）
                        timestamp = skin_flat["ownership"]["rental"]["endDate"] if i == 55 else skin_flat["ownership"]["rental"]["purchaseDate"]
                        skins_data[key].append("" if timestamp == 0 else time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(timestamp // 1000)))
                    else:
                        skins_data[key].append(skin_flat[key.split()[0]][key.split()[1]][key.split()[2]])
    skins_statistics_output_order = [7, 12, 18, 41, 45, 46, 47, 42, 4, 5, 6, 21, 19, 8, 43, 23, 20, 22, 9, 15, 17, 14, 49, 48, 50, 53, 52, 56, 51, 55, 54, 44, 36, 37, 34, 35, 39, 38, 40, 33, 27, 10, 11, 24, 28, 25, 13, 0, 1, 3, 2, 16, 26, 29, 30, 32, 31]
    skins_data_organized = {}
    for i in skins_statistics_output_order:
        key = skins_header_keys[i]
        skins_data_organized[key] = skins_data[key]
    logPrint("[sort_skin_data]正在构建数据框…… | Creating the dataframe ...", print_time = True)
    skins_df = pandas.DataFrame(data = skins_data_organized)
    logPrint("[sort_skin_data]正在优化逻辑值显示…… | Optimizing the display of boolean values ...", print_time = True)
    for column in skins_df:
        if skins_df[column].dtype == "bool":
            skins_df[column] = skins_df[column].astype(str)
            for i in range(len(skins_df)):
                skins_df.loc[i, column] = "√" if skins_df[column][i] == "True" else ""
    skins_df = pandas.concat([pandas.DataFrame([skins_header])[skins_df.columns], skins_df], ignore_index = True)
    logPrint("[sort_skin_data]数据框构建完成。 | Dataframe created.", print_time = True)
    return skins_df

async def sort_muted_players(connection) -> pandas.DataFrame:
    muted_players = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
    muted_player_data = {}
    for i in range(len(muted_players_header_keys)):
        key = muted_players_header_keys[i]
        muted_player_data[key] = []
    for player in muted_players:
        player_info_recapture = 0
        player_info = await get_info(connection, player["puuid"])
        while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
            logPrint(player_info["message"])
            player_info_recapture += 1
            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture))
            player_info = await get_info(connection, player["puuid"])
        if not player_info["info_got"]:
            logPrint(player_info["message"])
            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) capture failed!" %(player["puuid"], player["puuid"]))
        for i in range(len(muted_players_header_keys)):
            key = muted_players_header_keys[i]
            if i <= 3:
                muted_player_data[key].append(player[key])
            else:
                muted_player_data[key].append(player_info["body"][key] if player_info["info_got"] else "")
    muted_player_statistics_output_order = [4, 5, 0, 1, 2, 3]
    muted_player_data_organized = {}
    for i in muted_player_statistics_output_order:
        key = muted_players_header_keys[i]
        muted_player_data_organized[key] = muted_player_data[key]
    muted_player_df = pandas.DataFrame(data = muted_player_data_organized)
    muted_player_df = pandas.concat([pandas.DataFrame([muted_players_header])[muted_player_df.columns], muted_player_df], ignore_index = True)
    return muted_player_df

async def champ_select_simulation(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t交换（Swap）\n2\t英雄选择（Select a champion）\n3\t准备赛前配置（Prepare loadouts）\n4\t静音玩家（Mute players）\n5\t聊天（Chat）\n6\t其它（Others）\n7\t输出英雄选择会话（Output the champ select session）\n8\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            pass
        elif option == "-1": #查看接口返回结果，用于内部调试（Check endpoint results, used for debugging）
            logPrint('请选择一个英雄选择相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a champ select-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t查看所有网格化英雄信息（Check all grid champions）\n2\t查看所有可禁用的英雄（Check all bannable championIds）\n3\t启动训练场（Launch battle training）\n4\t查看当前选用的英雄序号（Check the current picked championId）\n5\t查看服务器禁用的英雄序号（Check ids of champions disabled serverside）\n6\t查看某个英雄的网格化信息（Check the grid information of one champion）\n7\t查看静音玩家信息（Check muted player information）\n8\t查看正在进行的英雄交换（Check the ongoing champion swap）\n9\t取消正在进行的英雄交换（Cancel the ongoing champion swap）\n10\t查看正在进行的选用顺序交换（Check the ongoing pick order swap）\n11\t取消正在进行的选用顺序交换（Cancel the ongoing pick order swap）\n12\t查看正在进行的分路交换（Check the ongoing position swap）\n13\t取消正在进行的分路交换（Cancel the ongoing position swap）\n14\t查看所有可选用的英雄序号（Check all pickable championIds）\n15\t查看所有可选用的皮肤序号（Check all pickable skinIds）\n16\t查看槽位信息（Check cell information）\n17\t重新获取英雄选择数据（Retrieve champ select data）\n☆18\t获取英雄选择会话（Get champ selection session）\n19\t执行英雄选择动作（Perform an action during champ select stage）\n20\t完成英雄选择动作（Complete an action during champ select stage）\n21\t换用可用英雄池的英雄（Take a champion from the bench）\n22\t获取可用英雄交换信息（Get all champion swap information）\n23\t获取某个英雄交换信息（Get some champion swap information）\n24\t接受一个英雄交换请求（Accept a champion swap request）\n25\t忽略一个英雄交换请求（Neglect a champion swap request）\n26\t拒绝一个英雄交换请求（Decline a champion swap request）\n27\t发送一个英雄交换请求（Send a champion swap request）\n28\t获取赛前配置信息（Get loadout information）\n29\t修改赛前配置信息（Change loadout information）\n30\t发送重随请求（Send a reroll request）\n31\t获取可用选用顺序交换信息（Get all pick order swap information）\n32\t获取某个选用顺序交换信息（Get some pick order swap information）\n33\t接受一个选用顺序交换请求（Accept a pick order swap request）\n34\t忽略一个选用顺序交换请求（Cancel a pick order swap request）\n35\t拒绝一个选用顺序交换请求（Decline a pick order swap request）\n36\t发送一个选用顺序交换请求（Send a pick order swap request）\n37\t获取可用分路交换信息（Get all position swap information）\n38\t获取某个分路交换信息（Get some position swap information）\n39\t接受一个分路交换请求（Accept a position swap request）\n40\t忽略一个分路交换请求（Cancel a position swap request）\n41\t拒绝一个分路交换请求（Decline a position swap request）\n42\t发送一个分路交换请求（Send a position swap request）\n43\t获取当前会话计时器（Get the current session timer）\n44\t获取音效通知（Get sound effect notifications）\n45\t查看当前皮肤轮盘（Check skins on the current carousel）\n46\t查看已选用的皮肤信息（Check skin selector information）\n47\t查看某个槽位的玩家信息（Check information of a player on some slot）\n48\t查看全队战斗加成状态（Check battle boost status）\n49\t激活全队战斗加成（Enable battle boost）\n50\t切换最爱英雄（Toggle favorite champions）\n51\t切换玩家静音状态（Toggle player mute status）')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection)
                elif suboption == "0":
                    break
                elif suboption in list(map(str, range(1, 52))):
                    if suboption == "1":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/all-grid-champions")).json()
                    elif suboption == "2":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/bannable-champion-ids")).json()
                    elif suboption == "3":
                        response = await (await connection.request("POST", "/lol-champ-select/v1/battle-training/launch")).json()
                    elif suboption == "4":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/current-champion")).json()
                    elif suboption == "5":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/disabled-champion-ids")).json()
                    elif suboption == "6":
                        logPrint("请输入英雄序号：\nPlease input a championId:")
                        championId = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/grid-champions/{championId}")).json()
                    elif suboption == "7":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                    elif suboption == "8":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/ongoing-champion-swap")).json()
                    elif suboption == "9":
                        logPrint("请输入当前正在进行的英雄交换行为的序号：\nPlease input the id of the ongoing champion swap action:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/ongoing-champion-swap/{swap_id}/clear")).json()
                    elif suboption == "10":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/ongoing-pick-order-swap")).json()
                    elif suboption == "11":
                        logPrint("请输入当前正在进行的选用顺序交换行为的序号：\nPlease input the id of the ongoing pick order swap action:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/ongoing-pick-order-swap/{swap_id}/clear")).json()
                    elif suboption == "12":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/ongoing-position-swap")).json()
                    elif suboption == "13":
                        logPrint("请输入当前正在进行的分路交换行为的序号：\nPlease input the id of the ongoing position swap action:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/ongoing-position-swap/{swap_id}/clear")).json()
                    elif suboption == "14":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/pickable-champion-ids")).json()
                    elif suboption == "15":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/pickable-skin-ids")).json()
                    elif suboption == "16":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/pin-drop-notification")).json()
                    elif suboption == "17":
                        response = await (await connection.request("POST", "/lol-champ-select/v1/retrieve-latest-game-dto")).json()
                    elif suboption == "18":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                    elif suboption == "19":
                        logPrint("请输入动作序号：\nPlease input the action's id:")
                        actionId = logInput()
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"id": 0, "actorCellId": 0, "championId": 0, "type": "string", "completed": True, "isAllyAction": True, "isInProgress": True, "pickTurn": 0, "duration": 0}\ndata = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("PATCH", f"/lol-champ-select/v1/session/actions/{actionId}", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "20":
                        logPrint("请输入动作序号：\nPlease input the action's id:")
                        actionId = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/actions/{actionId}/complete")).json()
                    elif suboption == "21":
                        logPrint("请输入可用英雄池中的英雄序号：\nPlease input the id of a champion in the available champion pool:")
                        championId = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/bench/swap/{championId}")).json()
                    elif suboption == "22":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session/champion-swaps")).json()
                    elif suboption == "23":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/session/champion-swaps/{swap_id}")).json()
                    elif suboption == "24":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id}/accept")).json()
                    elif suboption == "25":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id}/cancel")).json()
                    elif suboption == "26":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id}/decline")).json()
                    elif suboption == "27":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id}/request")).json()
                    elif suboption == "28":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session/my-selection")).json()
                    elif suboption == "29":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"selectedSkinId": 0, "spell1Id": 0, "spell2Id": 0}\nselection = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("PATCH", "/lol-champ-select/v1/session/my-selection", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "30":
                        response = await (await connection.request("POST", "/lol-champ-select/v1/session/my-selection/reroll")).json()
                    elif suboption == "31":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session/pick-order-swaps")).json()
                    elif suboption == "32":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id}")).json()
                    elif suboption == "33":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/accept")).json()
                    elif suboption == "34":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/cancel")).json()
                    elif suboption == "35":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/decline")).json()
                    elif suboption == "36":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/request")).json()
                    elif suboption == "37":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session/position-swaps")).json()
                    elif suboption == "38":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id}/accept")).json()
                    elif suboption == "39":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id}/cancel")).json()
                    elif suboption == "40":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id}/decline")).json()
                    elif suboption == "41":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id}/request")).json()
                    elif suboption == "42":
                        response = await (await connection.request("POST", "/lol-champ-select/v1/session/simple-inventory")).json()
                    elif suboption == "43":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session/timer")).json()
                    elif suboption == "44":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/sfx-notifications")).json()
                    elif suboption == "45":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/skin-carousel-skins")).json()
                    elif suboption == "46":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/skin-selector-info")).json()
                    elif suboption == "47":
                        logPrint("请输入槽位序号：\nPlease input a slotId:")
                        slotId = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/summoners/{slotId}")).json()
                    elif suboption == "48":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/team-boost")).json()
                    elif suboption == "49":
                        response = await (await connection.request("POST", "/lol-champ-select/v1/team-boost/purchase")).json()
                    elif suboption == "50":
                        logPrint("请输入英雄序号：\nPlease input a championId:")
                        championId = logInput()
                        logPrint('请输入分路：\nPlease input a position:\n取值范围（Available values）：\n["top", "jungle", "middle", "bottom", "support"]')
                        position = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/toggle-favorite/{championId}/{position}")).json()
                    else:
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"puuid": "string", "summonerId": 0, "obfuscatedPuuid": "string", "obfuscatedSummonerId": 0}\nplayer = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response = await (await connection.request("POST", "/lol-champ-select/v1/toggle-player-muted", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    logPrint(response)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option[0] == "0": #退出函数（Exit the function）
            break
        elif option[0] == "1":
            tooltip1_zh = {"1": "选用顺序", "2": "分路", "3": "英雄"}
            tooltip1_en_lowercase = {"1": "pick order", "2": "position", "3": "champion"}
            tooltip1_en_capitalize = {key: value.capitalize() for (key, value) in tooltip1_en_lowercase.items()}
            session_keys = {"1": "pickOrderSwaps", "2": "positionSwaps", "3": "trades"}
            endpoint1_dict1 = {"1": "pick-order", "2": "position", "3": "champion"}
            tooltip2_zh = {"1": "接受", "2": "拒绝", "3": "取消"}
            tooltip2_en_noun_capitalize = {"1": "Acceptation", "2": "Decline", "3": "Cancellation"}
            tooltip2_en_verb_perfect_capitalize = {"1": "Accepted", "2": "Declined", "3": "Cancelled"}
            endpoint1_dict2 = {"1": "accept", "2": "decline", "3": "cancel"}
            logPrint("请选择交换对象：\nPlease select an object to swap:\n1\t选用顺序（Pick order）\n2\t分路（Position）\n3\t队友英雄（Ally champions）\n4\t可用英雄池（替补席）【Available champion pool (Bench)】")
            while True:
                obj = logInput()
                if obj == "":
                    continue
                elif obj[0] == "0":
                    break
                elif obj[0] in {"1", "2", "3"}:
                    logPrint("请选择动作：\nPlease select an action:\n1\t查看（Check）\n2\t发送（Send）")
                    while True:
                        action = logInput()
                        if action == "":
                            continue
                        elif action[0] == "0":
                            break
                        elif action[0] == "1":
                            gameflow_phase = await get_gameflow_phase(connection) #每一个操作都需要保证英雄选择会话是可用的（Each operation requires the champ select session to be available）
                            if gameflow_phase == "ChampSelect":
                                ongoing_swap = await (await connection.request("GET", "/lol-champ-select/v1/ongoing-%s-swap" %(endpoint1_dict1[obj[0]]))).json()
                                if "errorCode" in ongoing_swap:
                                    logPrint("当前没有进行中的%s交换。\nNo pending %s swap for now." %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                else:
                                    swap_id = ongoing_swap["id"]
                                    champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                    swaps = champ_select_session[session_keys[obj[0]]]
                                    players_df = await sort_ChampSelect_players(connection)
                                    players_df_fields_to_print = ["cellId", "gameName", "tagLine", "playerAlias", "assignedPosition", "champion name", "champion alias"]
                                    for swap in swaps:
                                        if swap["id"] == swap_id:
                                            if ongoing_swap["state"] == "SENT": #该条件理论上等价于`ongoing_swap["initiatedByLocalPlayer"]`（This condition is equivalent to `ongoing_swap["initiatedByLocalPlayer"]` in theory）
                                                logPrint("您向以下玩家发送了%s交换请求：\nYou requested a %s swap to the following player:" %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                            else: #ongoing_swap["state"] == "ACCEPTED":
                                                logPrint("您收到来自以下玩家的%s交换请求：\nYou received a %s swap from the following player:" %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                            target_cellId = swap["cellId"]
                                            players_df_selected = players_df[players_df["cellId"] == target_cellId]
                                            print(format_df(players_df_selected.loc[:, players_df_fields_to_print], print_index = False)[0])
                                            log.write(format_df(players_df_selected.loc[:, players_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = False)[0] + "\n")
                                            if ongoing_swap["state"] == "SENT":
                                                logPrint("是否取消该交换请求？（输入任意键以取消，否则不取消。）\nDo you want to cancel this swap request? (Submit any non-empty string to cancel, or null to refuse cancelling.)")
                                                clear_str = logInput()
                                                clear = bool(clear_str)
                                                if clear:
                                                    response = await (await connection.request("POST", "/lol-champ-select/v1/ongoing-%s-swap/%d/clear" %(endpoint1_dict1[obj[0]], swap_id))).json()
                                                    logPrint(response)
                                                    if isinstance(response, dict) and "errorCode" in response: #本脚本中，大部分反馈都用了`isinstance(response, dict) and "errorCode" in response`作为请求成功与否的判断标准。这是因为如果要知道每个接口在请求成功时具体返回什么信息，必须在实战中测定。但是实际上不需要知道具体返回什么信息（In this program, the feedback parts use `isinstance(response, dict) and "errorCode" in response` as the criterion to judge whether a request is successfully post. This is because, one can only know what exactly a champ select endpoint returns in practical matches. But actually, that exact information isn't necessary）
                                                        logPrint("取消失败！\nCancellation failed!")
                                                    else:
                                                        logPrint("已取消%s交换请求。\nCancelled current %s swap." %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                            else:
                                                logPrint("请选择处理方式：\nPlease select how you'd like to deal with this swap:\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）\n3\t取消（Cancel）")
                                                while True:
                                                    strategy = logInput()
                                                    if strategy == "":
                                                        continue
                                                    elif strategy[0] == "0":
                                                        pass
                                                    elif strategy[0] in {"1", "2", "3"}:
                                                        response = await (await connection.request("POST", "/lol-champ-select/v1/session/%s-swaps/%d/%s" %(endpoint1_dict1[obj[0]], swap_id, endpoint1_dict2[strategy[0]]))).json()
                                                        logPrint(response)
                                                        if isinstance(response, dict) and "errorCode" in response:
                                                            logPrint("%s失败！\n%s failed!" %(tooltip2_zh[strategy[0]], tooltip2_en_noun_capitalize[strategy[0]]))
                                                        else:
                                                            logPrint("已%s%s交换请求。\n%s current %s swap." %(tooltip2_zh[strategy[0]], tooltip1_zh[obj[0]], tooltip2_en_verb_perfect_capitalize[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                                    else:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                                    break
                                            break
                                    else:
                                        logPrint("在当前的英雄选择会话中没有找到序号为%d的%s交换请求。\nThe %s swap with id %d isn't found in the current champ select session." %(swap_id, tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]], swap_id))
                            else:
                                logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                        elif action[0] == "2":
                            gameflow_phase = await get_gameflow_phase(connection)
                            if gameflow_phase == "ChampSelect":
                                champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                swaps = champ_select_session[session_keys[obj[0]]]
                                if len(swaps) == 0:
                                    logPrint("%s交换不可用。请切换游戏模式后再试。\n%s swap isn't available. Please switch to another game mode and try again." %(tooltip1_zh[obj[0]], tooltip1_en_capitalize[obj[0]]))
                                elif any(map(lambda x: x["state"] == "AVAILABLE", swaps)):
                                    swaps_df = await sort_swaps_info(connection, swap_typeId = int(obj[0]))
                                    swaps_df_fields_to_print = ["id", "cellId", "gameName", "tagLine", "assignedPosition", "champion name", "champion alias"]
                                    swaps_df_selected = pandas.concat([swaps_df.iloc[:1, :], swaps_df[swaps_df["state"] == "AVAILABLE"]], ignore_index = True)
                                    logPrint("请选择一名玩家以交换%s：\nPlease select a player to swap %s:" %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                    print(format_df(swaps_df_selected.loc[:, swaps_df_fields_to_print], print_index = True)[0])
                                    log.write(format_df(swaps_df_selected.loc[:, swaps_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0])
                                    while True:
                                        index_got = False
                                        swap_index = logInput()
                                        if swap_index == "":
                                            continue
                                        elif swap_index == "0":
                                            break
                                        elif swap_index in list(map(str, range(1, len(swaps_df_selected)))):
                                            swap_index = int(swap_index)
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    if index_got:
                                        logPrint("是否确认与以下玩家交换%s？（输入任意键确认，否则取消。）\nDo you want to swap %s with the following player? (Submit any non-empty string to confirm, or null to cancel.)" %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                        print(format_df(swaps_df_selected.loc[[swap_index], swaps_df_fields_to_print], print_index = True, reserve_index = True)[0])
                                        log.write(format_df(swaps_df_selected.loc[[swap_index], swaps_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0])
                                        swap_confirm_str = logInput()
                                        swap_confirm = bool(swap_confirm_str)
                                        if swap_confirm:
                                            swap_id = swaps_df_selected.loc[swap_index, "id"]
                                            response = await (await connection.request("POST", "/lol-champ-select/v1/session/%s-swaps/%d/request" %(endpoint1_dict1[obj[0]], swap_id))).json()
                                            logPrint(response)
                                            if isinstance(response, dict) and "errorCode" in response:
                                                logPrint("交换%s失败。\n%s swap failed." %(tooltip1_zh[obj[0]], tooltip1_en_capitalize[obj[0]]))
                                            else:
                                                logPrint("交换%s成功。\n%s swap succeeded." %(tooltip1_zh[obj[0]], tooltip1_en_capitalize[obj[0]]))
                                                time.sleep(GLOBAL_RESPONSE_LAG)
                                                current_player = await get_current_player(connection)
                                                if current_player != {}:
                                                    logPrint("当前槽位序号（Current cell id）：%d" %(current_player["cellId"]))
                                else:
                                    logPrint("%s交换不可用。请检查英雄选择计时阶段。\n%s swap isn't available. Please check the timer phase of the current champ select session.\n当前阶段（Current phase）：%s" %(tooltip1_zh[obj[0]], tooltip1_en_capitalize[obj[0]], champ_select_session["timer"]["phase"]))
                            else:
                                logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        logPrint("请选择动作：\nPlease select an action:\n1\t查看（Check）\n2\t发送（Send）")
                elif obj[0] == "4": #“可用英雄池”的叫法来自极地大乱斗的百度百科（"Available champion pool" comes from https://wiki.leagueoflegends.com/en-us/ARAM）
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        if champ_select_session["benchEnabled"]:
                            benchedChampionIds = list(map(lambda x: x["championId"], champ_select_session["benchChampions"]))
                            if len(benchedChampionIds) == 0:
                                logPrint("还没有人重随过。\nNobody has rerolled.")
                            else:
                                logPrint("可用英雄池如下：\nAvailable champion pool:")
                                LoLChampions_df = await get_LoLChampions(connection)
                                LoLChampions_df_fields_to_print = ["id", "name", "title", "alias", "freeToPlay", "ownership: owned", "ownership: rental: rented"]
                                LoLChampions_df_selected = pandas.concat([LoLChampions_df.iloc[:1, :], LoLChampions_df[LoLChampions_df["id"].isin(benchedChampionIds)]], ignore_index = True)
                                print(format_df(LoLChampions_df_selected.loc[:, LoLChampions_df_fields_to_print], print_index = True)[0])
                                log.write(format_df(LoLChampions_df_selected.loc[:, LoLChampions_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                logPrint("请选择一个英雄：\nPlease select a champion:")
                                while True:
                                    index_got = False
                                    swap_index = logInput()
                                    if swap_index == "":
                                        continue
                                    elif swap_index[0] == "0":
                                        index_got = False
                                        break
                                    elif swap_index in list(map(str, range(1, len(LoLChampions_df_selected)))):
                                        swap_index = int(swap_index)
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if index_got:
                                    logPrint("您选择交换以下英雄：\nYou selected the following champion to swap:")
                                    print(format_df(LoLChampions_df_selected.loc[[swap_index], LoLChampions_df_fields_to_print], print_index = True, reserve_index = True)[0])
                                    log.write(format_df(LoLChampions_df_selected.loc[[swap_index], LoLChampions_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                    swap_championId = LoLChampions_df_selected.loc[swap_index, "id"]
                                    swap_championName = LoLChampions_df_selected.loc[swap_index, "name"]
                                    response = await (await connection.request("POST", f"/lol-champ-select/v1/session/bench/swap/{swap_championId}")).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        logPrint("交换失败。\nSwap failed.")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        current_player = await get_current_player(connection)
                                        if current_player["championId"] == swap_championId:
                                            logPrint("交换成功。\nSwap succeeded.")
                                        else:
                                            logPrint("交换失败。\nSwap failed.")
                        else:
                            logPrint("当前游戏模式不支持可用英雄池。请切换游戏模式后再试。\nAvailable champion pool isn't supported in this game mode. Please switch to another game mode and try again.")
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("请选择交换对象：\nPlease select an object to swap:\n1\t选用顺序（Pick order）\n2\t分路（Position）\n3\t队友英雄（Ally champions）\n4\t可用英雄池（替补席）【Available champion pool (Bench)】")
        elif option[0] == "2": #这部分代码来自克隆脚本（This part of code come from Customized Program 15）
            logPrint("请选择行为类型：\nPlease select an action:\n1\t声明（不可用）【Declare intent (unavailable)】\n2\t禁用（Ban）\n3\t选择（Pick）\n4\t重随（Reroll）\n5\t投票（Vote）")
            while True:
                action = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    logPrint("目前无法通过接口来声明英雄。请尝试在客户端的声明阶段点击一名英雄来声明你想玩的英雄。\nDeclaring an intent champion isn't supported currently through LCU API. Please try clicking a champion in the League Client to declare a champion you want to play instead during PLANNING phase.")
                elif action[0] in {"2", "3", "5"}:
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        action_type = "ban" if action[0] == "2" else "pick" if action[0] == "3" else "vote"
                        if action_type == "ban":
                            selectable_champion_ids = await (await connection.request("GET", "/lol-champ-select/v1/bannable-champion-ids")).json()
                        else:
                            if champ_select_session["allowSubsetChampionPicks"]:
                                selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/subset-champion-list")).json()
                            else:
                                selectable_champion_ids = await (await connection.request("GET", "/lol-champ-select/v1/pickable-champion-ids")).json()
                        logPrint("请输入英雄序号：\nPlease enter a champion id:") #这部分代码复制于符文脚本（This part of code is copied from Customized Program 19）
                        LoLChampions_df = await get_LoLChampions(connection)
                        LoLChampions_fields_to_print = ["id", "name", "title", "alias"]
                        LoLChampions_df_selected = pandas.concat([LoLChampions_df.iloc[:1, :], LoLChampions_df[LoLChampions_df["id"].isin(selectable_champion_ids)]], ignore_index = True)
                        LoLChampions_df_query = LoLChampions_df.loc[:, LoLChampions_fields_to_print]
                        LoLChampions_df_query["id"] = LoLChampions_df["id"].astype(str) #方便检索（For convenience of retrieval）
                        LoLChampions_df_query = LoLChampions_df_query.map(lambda x: x.lower() if isinstance(x, str) else x)
                        print(format_df(LoLChampions_df_selected.loc[:, LoLChampions_fields_to_print])[0]) #虽然输出的是筛选后的表格，但实际上用户仍然可以尝试选择不可用的英雄（Although the selected table is output, users can still try choosing unavailable champions）
                        log.write(format_df(LoLChampions_df_selected.loc[:, LoLChampions_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                        back = False
                        while True:
                            champion_queryStr = logInput()
                            if champion_queryStr == "":
                                continue
                            elif champion_queryStr == "0":
                                back = True
                                break
                            elif champion_queryStr == "-3":
                                pick_championId = -3
                                break
                            else:
                                query_positions = numpy.where(LoLChampions_df_query == champion_queryStr.lower()) #使用numpy.where检索的前提是数据框中每个单元格的值都不一样（The premise of query by `numpy.where` is that no two cells are the same）
                                if len(query_positions[0]) == 0:
                                    logPrint("没有找到该英雄。请重新输入。\nChampion not found. Please try again.")
                                else:
                                    resultRow = query_positions[0]
                                    result_champion_df = LoLChampions_df.loc[resultRow, LoLChampions_fields_to_print].reset_index(drop = True)
                                    pick_championId = LoLChampions_df.loc[resultRow[0], "id"] #如果碰巧有多个单元格匹配用户的输入，取第一个。请向作者汇报该问题（If multiple cells happen to match the user input, the first cell is taken. Please report this issue to the author）
                                    logPrint("您选择了以下英雄：\nYou selected the following champion:")
                                    print(format_df(result_champion_df)[0])
                                    log.write(format_df(result_champion_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                                    break
                        if back:
                            logPrint("请选择行为类型：\nPlease select an action:\n1\t声明（不可用）【Declare intent (unavailable)】\n2\t禁用（Ban）\n3\t选择（Pick）\n4\t重随（Reroll）\n5\t投票（Vote）")
                            continue
                        logPrint("是否直接锁定选择？（输入任意键直接锁定，否则不锁定。）\nDo you want to lock in? (Submit any non-empty string to lock in, or null to refuse locking in.)")
                        complete_str = logInput()
                        complete = bool(complete_str)
                        gameflow_phase = await get_gameflow_phase(connection)
                        if gameflow_phase == "ChampSelect":
                            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                            if champ_select_session["isSpectating"]:
                                logPrint("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                            else:
                                #首先获取用户的槽位序号（First, get the user's cellId）
                                localPlayerCellId = champ_select_session["localPlayerCellId"]
                                #下面获取用户选英雄时的行为序号（Get the user's actionId when he/she's picking a champion）
                                selfKey_pick = str(localPlayerCellId) + " pick" #只选择类型为“选英雄”的行为（Only do operations on a pick action）
                                selfKey_ban = str(localPlayerCellId) + " ban" #只选择类型为“禁英雄”的行为（Only do operations on a ban action）
                                selfKey_vote = str(localPlayerCellId) + " vote" #只选择类型为“投票”的行为（Only do operations on a vote action）
                                selfKey = selfKey_ban if action_type == "ban" else selfKey_pick if action_type == "pick" else selfKey_vote
                                actions = {}
                                for stage in champ_select_session["actions"]:
                                    for action in stage:
                                        key = str(action["actorCellId"]) + " " + action["type"]
                                        # if key in actions and action["type"] != "ban": #在旧版征召模式中，由同一个人来禁英雄，因此在禁用期间，这个人的行为的槽位序号和行为类型是一样的。这样的键重复无关紧要，因为后面的禁用行为序号一定比前面的禁用行为序号大，所以程序总是能追踪到最新的禁用行为（In old draft mode, one player bans multiple champions, so during the ban phase, the actorCellIds and types are both the same among this player's actions. In this case, the key duplicate doesn't matter, for the id of the later ban action is always greater than that of the earlier ban action, which means the program will always track the latest ban action）
                                        #     logPrint("检测到重复键（%s）。请修改代码。\nDetected the same key (%s). Please fix the code." %(key, key))
                                        actions[key] = action
                                if selfKey in actions:
                                    current_actionId = actions[selfKey]["id"]
                                    #下面通过LCU API选择英雄（Pick a champion through LCU API)
                                    body = {"id": current_actionId, "actorCellId": localPlayerCellId, "championId": pick_championId, "type": action_type, "completed": complete, "isAllyAction": True, "isInProgress": True, "pickTurn": 0}
                                    logPrint(body)
                                    response = await (await connection.request("PATCH", f"/lol-champ-select/v1/session/actions/{current_actionId}", data = body)).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        logPrint("选择失败！\nPick failed.")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                        current_actions = {}
                                        for stage in champ_select_session["actions"]:
                                            for action in stage:
                                                current_actions[action["id"]] = action
                                        if current_actionId in current_actions:
                                            if current_actions[current_actionId]["championId"] == pick_championId:
                                                logPrint("选择成功！\nPick succeeded.")
                                            else:
                                                logPrint("选择失败！\nPick failed.")
                                        else:
                                            logPrint("没有找到匹配的行为。请稍后再试。\nNo matched action found. Please try again later.")
                                else:
                                    logPrint("没有找到匹配的行为。请稍后再试。\nNo matched action found. Please try again later.")
                        else:
                            logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                            break
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                        break
                elif action[0] == "4":
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        if champ_select_session["isSpectating"]:
                            logPrint("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                        elif champ_select_session["allowRerolling"]:
                            if champ_select_session["rerollsRemaining"] == 0:
                                logPrint("您的重随次数不足。\nYou don't have any rerolls.")
                            else:
                                response = await (await connection.request("POST", "/lol-champ-select/v1/session/my-selection/reroll")).json()
                                logPrint(response)
                                if isinstance(response, dict) and "errorCode" in response:
                                    if response["message"] == "No active delegate":
                                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                                    elif response["message"] == "Error response for POST /lol-lobby-team-builder/champ-select/v1/session/my-selection/reroll: Unable to reroll: Received status Error: NO_REROLLS_REMAINING instead of expected status of OK from request to teambuilder-draft:rerollV1":
                                        logPrint("您的重随次数不足。\nYou don't have any rerolls.")
                                    else:
                                        logPrint("重随失败。\nReroll failed.")
                                else:
                                    logPrint("重随成功。\nReroll succeeded.")
                        else:
                            logPrint("当前游戏模式不支持重随。\nThe current game mode doesn't support rerolling.")
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                        break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("请选择行为类型：\nPlease select an action:\n1\t声明（不可用）【Declare intent (unavailable)】\n2\t禁用（Ban）\n3\t选择（Pick）\n4\t重随（Reroll）\n5\t投票（Vote）")
        elif option[0] == "3":
            collection_df_fields_to_print = ["inventoryType", "itemId", "name", "ownershipType"]
            skins_df_fields_to_print = ["id", "name"]
            logPrint("请选择要修改的赛前配置：\nPlease select a loadout:\n1\t符文（Perks）\n2\t召唤师技能（Summoner spells）\n3\t皮肤（Skin）\n4\t守卫（眼）皮肤（Ward skin）\n5\t表情（Emotes）\n6\t召唤师图标（Summoner icon）\n7\t水晶枢纽终结特效（Nexus finisher）\n8\t旗帜（Banner）\n9\t徽章（Crest）\n10\t冠军杯赛奖杯（Tournament trophy）")
            while True:
                loadout_option = logInput()
                if loadout_option == "":
                    continue
                elif loadout_option[0] == "0":
                    break
                elif loadout_option == "1":
                    wd = os.getcwd()
                    subscript_path = os.path.join(wd, "Customized Program 19 - Configure Perks.py")
                    if os.path.exists(subscript_path):
                        logPrint(f"正在打开（Opening）： {subscript_path}")
                        subprocess.run(["python", subscript_path])
                    else:
                        logPrint('''在同目录下未发现符文脚本。取消该操作。请自行在客户端内修改。\n"Customized Program 19 - Configure Perks.py" isn't found under the same directory. This operation is cancelled. Please change inside the League Client.''')
                elif loadout_option in {"2", "3"}:
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        if champ_select_session["isSpectating"]:
                            logPrint("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                        else:
                            if loadout_option == "2":
                                logPrint("该模式可用召唤师技能如下：\nAvailable summoner spells of this game mode are as follows:")
                                gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                                available_spells = available_spell_dict[gameflow_session["gameData"]["queue"]["gameMode"]]
                                for spellId in sorted(available_spells):
                                    spell = spells[spellId]
                                    logPrint("%d\t%s" %(spellId, spell["name"]))
                                logPrint("请依次输入两个召唤师技能的序号，以空格为分隔符：\nPlease input the two spellIds, split by space:")
                                while True:
                                    index_got = False
                                    spell_str = logInput()
                                    if spell_str == "":
                                        continue
                                    elif spell_str == "0":
                                        index_got = False
                                        break
                                    else:
                                        selectedSpellIds = spell_str.split()
                                        if len(selectedSpellIds) != 2:
                                            logPrint("请输入两个召唤师技能的序号！\nPlease submit two spellIds!")
                                        else:
                                            try:
                                                selectedSpellIds = list(map(int, selectedSpellIds))
                                            except ValueError:
                                                logPrint("请输入整数！\nPlease input integers!")
                                            else:
                                                if len(set(selectedSpellIds)) == 1:
                                                    logPrint("请输入两个不同的召唤师技能序号！\nPlease input two different spellIds!")
                                                elif all(map(lambda x: x in available_spells, selectedSpellIds)):
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您输入的召唤师技能序号不可用！请重新输入。\nThe selected summoner spells aren't available. Please try again.")
                                if index_got:
                                    body = {"spell1Id": selectedSpellIds[0], "spell2Id": selectedSpellIds[1]}
                                    response = await (await connection.request("PATCH", "/lol-champ-select/v1/session/my-selection", data = body)).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        logPrint("召唤师技能更换失败！\nSummoner spell change failed!")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        current_player = await get_current_player(connection)
                                        if [current_player["spell1Id"], current_player["spell2Id"]] == selectedSpellIds:
                                            logPrint("召唤师技能更换成功！\nSummoner spell change succeeded!")
                                        else:
                                            logPrint("召唤师技能更换失败！\nSummoner spell change failed!")
                            else:
                                pickable_skin_ids = await (await connection.request("GET", "/lol-champ-select/v1/pickable-skin-ids")).json()
                                current_player = await get_current_player(connection)
                                skins_df_selected = pandas.concat([skins_df.iloc[:1, :], skins_df[(skins_df["id"].isin(pickable_skin_ids)) & (skins_df["championId"] == current_player["championId"])]], ignore_index = True)
                                if len(skins_df_selected) == 1:
                                    logPrint("无可用皮肤。\nThere's not any available skin.")
                                else:
                                    logPrint("%s的可用皮肤如下：\nPickable skins of %s are as follows:" %(LoLChampions[current_player["championId"]]["title"], LoLChampions[current_player["championId"]]["alias"]))
                                    print(format_df(skins_df_selected.loc[:, skins_df_fields_to_print], print_index = True)[0])
                                    log.write(format_df(skins_df_selected.loc[:, skins_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                    logPrint("请选择一个皮肤：\nPlease select a skin:")
                                    while True:
                                        index_got = False
                                        skin_index = logInput()
                                        if skin_index == "":
                                            continue
                                        elif skin_index == "0":
                                            index_got = False
                                            break
                                        elif skin_index == "-1" or skin_index in list(map(str, range(1, len(skins_df_selected)))):
                                            skin_index = int(skin_index)
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    if index_got:
                                        selectedSkinId = current_player["championId"] * 1000 if skin_index == -1 else skins_df_selected.loc[skin_index, "id"]
                                        body = {"selectedSkinId": selectedSkinId}
                                        response = await (await connection.request("PATCH", "/lol-champ-select/v1/session/my-selection", data = body)).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            logPrint("皮肤更换失败！\nChampion skin change failed!")
                                        else:
                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                            current_player = await get_current_player(connection)
                                            if current_player["selectedSkinId"] == selectedSkinId:
                                                logPrint("皮肤更换成功！\nChampion skin change succeeded!")
                                            else:
                                                logPrint("皮肤更换失败！请在锁定英雄后检查是否更换成功。\nChampion skin change failed! Please check if the skin is changed after locking in.")
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                elif loadout_option in list(map(str, range(4, 11))):
                    loadout_scope = await (await connection.request("GET", "/lol-loadouts/v4/loadouts/scope/account")).json()
                    if isinstance(loadout_scope, dict) and "errorCode" in loadout_scope:
                        logPrint(loadout_scope)
                        logPrint("未知错误！\nUnknown error!")
                    else:
                        if len(loadout_scope) == 0:
                            logPrint("无可用赛前配置方案。请重启英雄联盟客户端后再运行本程序。\nNo available loadouts. Please restart the League Client and then run this program.")
                        else:
                            loadoutId = loadout_scope[0]["id"] #因为赛前配置在每次退出英雄联盟客户端后就没了，所以随便取一个赛前配置就行。这里取了第一个列表元素（Because loadouts aren't reserved as the user exits the League Client, any loadout is OK to use. Here the first element of the loadout scope list is used）
                            loadoutName = loadout_scope[0]["name"]
                    inventoryTypes = {"4": "WARD_SKIN", "5": "EMOTE", "6": "SUMMONER_ICON", "7": "NEXUS_FINISHER", "8": "REGALIA_BANNER", "9": "REGALIA_CREST", "10": "TOURNAMENT_TROPHY"}
                    inventoryType = inventoryTypes[loadout_option]
                    collection_df_selected = pandas.concat([collection_df.iloc[:1, :], collection_df[collection_df["inventoryType"] == inventoryType]], ignore_index = True)
                    if len(collection_df_selected) == 1:
                        logPrint("您目前没有该类道具的使用权。\nYou don't have permissions to use any item of this inventoryType.")
                    else:
                        if inventoryType == "EMOTE":
                            logPrint("请选择您想要配置的表情种类：\nPlease select the category of emotes:\n1\t表情轮盘（Emote wheel）\n2\t回应（Reactions）")
                            while True:
                                category = logInput()
                                if category == "":
                                    continue
                                elif category[0] == "0":
                                    break
                                elif category[0] == "1":
                                    logPrint("请选择方位：\nPlease select a direction:\n1\t中央（Center）\n2\t左（Left）\n3\t右（Right）\n4\t上（Upper）\n5\t下（Lower）\n6\t左上（Upper-Left）\n7\t右上（Upper-Right）\n8\t左下（Lower-Left）\n9\t右下（Lower-Right）")
                                    directions = {"1": "CENTER", "2": "LEFT", "3": "RIGHT", "4": "UPPER", "5": "LOWER", "6": "UPPER_LEFT", "7": "UPPER_RIGHT", "8": "LOWER_LEFT", "9": "LOWER_RIGHT"}
                                    while True:
                                        direction_index = logInput()
                                        if direction_index == "":
                                            continue
                                        elif direction_index[0] == "0":
                                            break
                                        elif direction_index[0] in list(map(str, range(1, 10))):
                                            direction = directions[direction_index[0]]
                                            logPrint('请选择您想要使用的道具：（输入-1以初始化当前选择。）\nPlease select an item to use: (Submit "-1" to initialize the current choice.)')
                                            print(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], print_index = True)[0])
                                            log.write(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                            while True:
                                                index_got = False
                                                item_index = logInput()
                                                if item_index == "":
                                                    continue
                                                elif item_index == "0":
                                                    index_got = False
                                                    break
                                                elif item_index == "-1" or item_index in list(map(str, range(1, len(collection_df_selected)))):
                                                    item_index = int(item_index)
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            if index_got:
                                                contentId = "" if item_index == -1 else collection_df_selected.loc[item_index, "uuid"]
                                                itemId = 0 if item_index == -1 else collection_df_selected.loc[item_index, "itemId"]
                                                loadout_key = f"{inventoryType}_WHEEL_{direction}" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                                body = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                                response = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["message"] == "UpdateLoadout Failed - Loadout does not exist in cache.":
                                                        logPrint("更新赛前配置失败。请检查代码为%s的赛前配置是否存在。如果不存在，请返回到选择赛前配置之前的步骤，再重试。\nLoadout update failed. Please check if the loadout of id %s still exists. If it doesn't exist, please return to the step before selecting to configure the TFT loadouts and then try again.")
                                                    else:
                                                        logPrint("未知错误！\nUnknown error!")
                                                else:
                                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                                    loadout = await (await connection.request("GET", f"/lol-loadouts/v4/loadouts/{loadoutId}")).json()
                                                    if not loadout_key in loadout["loadout"] or loadout["loadout"][loadout_key] == body["loadout"][loadout_key]:
                                                        logPrint("更新赛前配置成功。客户端内显示可能有延迟，请尝试关闭相应窗口再打开，观察配置是否更新。进入游戏即可正常使用。\nLoadout update succeeded. The League Client may not display the change properly due to a lag. Please try closing the corresponding window and then open it again to see if loadout is updated. As you enter the game, you should be using the updated loadouts.")
                                                    else:
                                                        logPrint("更新赛前配置失败。\nLoadout update failed.")
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            continue
                                        logPrint("请选择方位：\nPlease select a direction:\n1\t中央（Center）\n2\t左（Left）\n3\t右（Right）\n4\t上（Upper）\n5\t下（Lower）\n6\t左上（Upper-Left）\n7\t右上（Upper-Right）\n8\t左下（Lower-Left）\n9\t右下（Lower-Right）")
                                elif category[0] == "2":
                                    logPrint("请选择回应：\nPlease select a reaction:\n1\t开始（Start）\n2\t第一滴血（First blood）\n3\t团灭（Ace）\n4\t胜利（Victory）")
                                    reactions = {"1": "START", "2": "FIRST_BLOOD", "3": "ACE", "4": "VICTORY"}
                                    while True:
                                        reaction_index = logInput()
                                        if reaction_index == "":
                                            continue
                                        elif reaction_index[0] == "0":
                                            break
                                        elif reaction_index[0] in list(map(str, range(1, 5))):
                                            reaction = reactions[reaction_index[0]]
                                            logPrint('请选择您想要使用的道具：（输入-1以初始化当前选择。）\nPlease select an item to use: (Submit "-1" to initialize the current choice.)')
                                            print(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], print_index = True)[0])
                                            log.write(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0])
                                            while True:
                                                index_got = False
                                                item_index = logInput()
                                                if item_index == "":
                                                    continue
                                                elif item_index == "0":
                                                    index_got = False
                                                    break
                                                elif item_index == "-1" or item_index in list(map(str, range(1, len(collection_df_selected)))):
                                                    item_index = int(item_index)
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                            if index_got:
                                                contentId = "" if item_index == -1 else collection_df_selected.loc[item_index, "uuid"]
                                                itemId = 0 if item_index == -1 else collection_df_selected.loc[item_index, "itemId"]
                                                loadout_key = f"{inventoryType}_{reaction}" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                                body = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                                response = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["message"] == "UpdateLoadout Failed - Loadout does not exist in cache.":
                                                        logPrint("更新赛前配置失败。请检查代码为%s的赛前配置是否存在。如果不存在，请返回到选择赛前配置之前的步骤，再重试。\nLoadout update failed. Please check if the loadout of id %s still exists. If it doesn't exist, please return to the step before selecting to configure the TFT loadouts and then try again.")
                                                    else:
                                                        logPrint("未知错误！\nUnknown error!")
                                                else:
                                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                                    loadout = await (await connection.request("GET", f"/lol-loadouts/v4/loadouts/{loadoutId}")).json()
                                                    if loadout["loadout"][loadout_key] == body["loadout"][loadout_key]:
                                                        logPrint("更新赛前配置成功。客户端内显示可能有延迟，请尝试关闭相应窗口再打开，观察配置是否更新。进入游戏即可正常使用。\nLoadout update succeeded. The League Client may not display the change properly due to a lag. Please try closing the corresponding window and then open it again to see if loadout is updated. As you enter the game, you should be using the updated loadouts.")
                                                    else:
                                                        logPrint("更新赛前配置失败。\nLoadout update failed.")
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            continue
                                        logPrint("请选择回应：\nPlease select a reaction:\n1\t开始（Start）\n2\t第一滴血（First blood）\n3\t团灭（Ace）\n4\t胜利（Victory）")
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    continue
                                logPrint("请选择您想要配置的表情种类：\nPlease select the category of emotes:\n1\t表情轮盘（Emote wheel）\n2\t回应（Reactions）")
                        else:
                            logPrint('请选择您想要使用的道具：（输入-1以初始化当前选择。）\nPlease select an item to use: (Submit "-1" to initialize the current choice.)')
                            print(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], print_index = True)[0])
                            log.write(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                            while True:
                                index_got = False
                                item_index = logInput()
                                if item_index == "":
                                    continue
                                elif item_index == "0":
                                    index_got = False
                                    break
                                elif item_index == "-1" or item_index in list(map(str, range(1, len(collection_df_selected)))):
                                    item_index = int(item_index)
                                    index_got = True
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                contentId = "" if item_index == -1 else collection_df_selected.loc[item_index, "uuid"]
                                itemId = 0 if item_index == -1 else collection_df_selected.loc[item_index, "itemId"]
                                if inventoryType == "SUMMONER_ICON":
                                    body = {"profileIconId": itemId}
                                    response = await (await connection.request("PUT", "/lol-summoner/v1/current-summoner/icon", data = body)).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        if response["httpStatus"] == 401 and "Requested summoner profile icon is not free or owned by the player" in response["message"]:
                                            logPrint("您尚未拥有该召唤师图标。\nYou don't own this summoner icon.")
                                        elif response["httpStatus"] == 400 and "invalid profileIconId" in response["message"]:
                                            logPrint("您选择的召唤师图标不存在。\nThe selected summoner icon doesn't exist.")
                                        else:
                                            logPrint("未知错误！\nUnknown error!")
                                    else:
                                        if response["profileIconId"] == itemId:
                                            logPrint("更新赛前配置成功。\nLoadout update succeeded.")
                                        else:
                                            logPrint("更新赛前配置失败。\nLoadout update failed.")
                                else:
                                    loadout_key = f"{inventoryType}_SLOT" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                    body = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                    response = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        if response["message"] == "UpdateLoadout Failed - Loadout does not exist in cache.":
                                            logPrint("更新赛前配置失败。请检查代码为%s的赛前配置是否存在。如果不存在，请返回到选择赛前配置之前的步骤，再重试。\nLoadout update failed. Please check if the loadout of id %s still exists. If it doesn't exist, please return to the step before selecting to configure the TFT loadouts and then try again.")
                                        else:
                                            logPrint("未知错误！\nUnknown error!")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        loadout = await (await connection.request("GET", f"/lol-loadouts/v4/loadouts/{loadoutId}")).json()
                                        if loadout["loadout"][loadout_key] == body["loadout"][loadout_key]:
                                            logPrint("更新赛前配置成功。客户端内显示可能有延迟，请尝试关闭相应窗口再打开，观察配置是否更新。进入游戏即可正常使用。\nLoadout update succeeded. The League Client may not display the change properly due to a lag. Please try closing the corresponding window and then open it again to see if loadout is updated. As you enter the game, you should be using the updated loadouts.")
                                        else:
                                            logPrint("更新赛前配置失败。\nLoadout update failed.")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("请选择要修改的赛前配置：\nPlease select a loadout:\n1\t符文（Perks）\n2\t召唤师技能（Summoner spells）\n3\t皮肤（Skin）\n4\t守卫（眼）皮肤（Ward skin）\n5\t表情（Emotes）\n6\t召唤师图标（Summoner icon）\n7\t水晶枢纽终结特效（Nexus finisher）\n8\t旗帜（Banner）\n9\t徽章（Crest）\n10\t冠军杯赛奖杯（Tournament trophy）")
        elif option[0] == "4":
            while True:
                back = False
                muted_players = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                muted_players_puuids = list(map(lambda x: x["puuid"], muted_players))
                muted_players_obfuscatedPuuids = list(map(lambda x: x["obfuscatedPuuid"], muted_players))
                gameflow_phase = await get_gameflow_phase(connection)
                if gameflow_phase == "ChampSelect":
                    players_df = await sort_ChampSelect_players(connection)
                    players_df["muted"] = ["已静音"] + (len(players_df) - 1) * [""]
                    for i in range(1, len(players_df)):
                        for muted_player in muted_players:
                            if players_df.loc[i, "puuid"] == muted_player["puuid"] or players_df.loc[i, "obfuscatedPuuid"] == muted_player["obfuscatedPuuid"]:
                                players_df.loc[i, "muted"] = "√"
                    players_df_fields_to_print = ["cellId", "gameName", "tagLine", "playerAlias", "muted", "assignedPosition", "champion name", "champion alias"]
                    players_df_selected = pandas.concat([players_df.iloc[:1, :], players_df[(players_df["isHumanoid"] == "") & ~((players_df["gameName"] == "") & (players_df["tagLine"] == "") & (players_df["playerAlias"] == ""))]], ignore_index = True)
                    if len(players_df_selected) > 1:
                        logPrint("请选择一个要切换静音状态的玩家：\nPlease select a player to toggle mute/unmute status:")
                        print(format_df(players_df_selected.loc[:, players_df_fields_to_print], print_index = True)[0])
                        log.write(format_df(players_df_selected.loc[:, players_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        while True:
                            index_got = False
                            mute_index = logInput()
                            if mute_index == "":
                                continue
                            elif mute_index[0] == "0":
                                index_got = False
                                back = True
                                break
                            elif mute_index in list(map(str, range(1, len(players_df_selected)))):
                                mute_index = int(mute_index)
                                index_got = True
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if index_got:
                            selected_player_puuid = players_df_selected.loc[mute_index, "puuid"]
                            selected_player_obfuscatedPuuid = players_df_selected.loc[mute_index, "obfuscatedPuuid"]
                            selected_player_name = players_df_selected.loc[mute_index, "playerAlias"] if players_df_selected.loc[mute_index, "gameName"] == "" and players_df_selected.loc[mute_index, "tagLine"] == "" else players_df_selected.loc[mute_index, "gameName"] + "#" + players_df_selected.loc[mute_index, "tagLine"]
                            muted = players_df_selected.loc[mute_index, "muted"] == "√"
                            if muted:
                                logPrint("您选择解除静音以下玩家：\nYou selected the following player to unmute:")
                            else:
                                logPrint("您选择静音以下玩家：\nYou selected the following player to mute:")
                            print(format_df(players_df_selected.loc[[mute_index], players_df_fields_to_print])[0])
                            log.write(format_df(players_df_selected.loc[[mute_index], players_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0])
                            body = {"puuid": selected_player_puuid, "obfuscatedPuuid": selected_player_obfuscatedPuuid}
                            response = await (await connection.request("POST", "/lol-champ-select/v1/toggle-player-muted", data = body)).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                if muted:
                                    logPrint(f"解除静音{selected_player_name}失败。\nFailed to unmute {selected_player_name}.")
                                else:
                                    logPrint(f"静音{selected_player_name}失败。\nFailed to mute {selected_player_name}.")
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                muted_players = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                                muted_players_puuids = list(map(lambda x: x["puuid"], muted_players))
                                muted_players_obfuscatedPuuids = list(map(lambda x: x["obfuscatedPuuid"], muted_players))
                                if muted:
                                    if selected_player_puuid in muted_players_puuids or selected_player_obfuscatedPuuid in muted_players_obfuscatedPuuids:
                                        logPrint(f"解除静音{selected_player_name}失败。\nFailed to unmute {selected_player_name}.")
                                    else:
                                        logPrint(f"解除静音{selected_player_name}成功。\nSuccessfully unmuted {selected_player_name}.")
                                else:
                                    if selected_player_puuid in muted_players_puuids or selected_player_obfuscatedPuuid in muted_players_obfuscatedPuuids:
                                        logPrint(f"静音{selected_player_name}成功。\nSuccessfully muted {selected_player_name}.")
                                    else:
                                        logPrint(f"静音{selected_player_name}失败。\nFailed to mute {selected_player_name}.")
                    else:
                        break
                else:
                    logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.\n请输入您想要切换静音状态的召唤师名。\nPlease enter the name of the summoner you want to toggle mute/unmute status.")
                    while True:
                        mute_str = logInput()
                        if mute_str == "":
                            continue
                        elif mute_str == "0":
                            back = True
                            break
                        else:
                            player_info = await get_info(connection, mute_str)
                            if player_info["info_got"]:
                                player_puuid = player_info["body"]["puuid"]
                                player_name = get_info_name(player_info["body"])
                                muted = player_puuid in muted_players_puuids
                                body = {"puuid": player_puuid}
                                response = await (await connection.request("POST", "/lol-champ-select/v1/toggle-player-muted", data = body)).json()
                                logPrint(response)
                                if isinstance(response, dict) and "errorCode" in response:
                                    if muted:
                                        logPrint(f"解除静音{player_name}失败。\nFailed to unmute {player_name}.")
                                    else:
                                        logPrint(f"静音{player_name}失败。\nFailed to mute {player_name}.")
                                else:
                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                    muted_players = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                                    muted_players_puuids = list(map(lambda x: x["puuid"], muted_players))
                                    muted_players_obfuscatedPuuids = list(map(lambda x: x["obfuscatedPuuid"], muted_players))
                                    if muted:
                                        if player_puuid in muted_players_puuids:
                                            logPrint(f"解除静音{player_name}失败。\nFailed to unmute {player_name}.")
                                        else:
                                            logPrint(f"解除静音{player_name}成功。\nSuccessfully unmuted {player_name}.")
                                    else:
                                        if player_puuid in muted_players_puuids:
                                            logPrint(f"静音{player_name}成功。\nSuccessfully muted {player_name}.")
                                        else:
                                            logPrint(f"静音{player_name}失败。\nFailed to mute {player_name}.")
                            else:
                                logPrint(player_info["message"])
                        logPrint("请输入您想要切换静音状态的召唤师名。\nPlease enter the name of the summoner you want to toggle mute/unmute status.")
                if back:
                    break
        elif option[0] == "5":
            await chat(connection)
        elif option[0] == "6":
            logPrint("请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t解锁全员战斗加成（Unlock battle boost）\n2\t设置最爱的分路英雄（Toggle favorite champions on different positions）\n3\t清空静音玩家（Clear muted players）\n4\t退出英雄选择阶段（Exit the champ select stage）")
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        if champ_select_session["allowBattleBoost"]:
                            response = await (await connection.request("POST", "/lol-champ-select/v1/team-boost/purchase")).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                if response["message"] == "Error response for POST /lol-champ-select-legacy/v1/team-boost/purchase: Invalid function":
                                    logPrint("自定义模式不支持全员战斗加成。\nBattle boost isn't supported in a custom game.")
                                else:
                                    logPrint("全员战斗加成解锁失败。\nBattle boost unlock failed.")
                            else:
                                logPrint("全员战斗加成已解锁！\nBattle boost unlocked!")
                        else:
                            logPrint("当前游戏模式不支持全员战斗加成。请切换游戏模式或大区后再试。\nBattle boost isn't supported in this game mode. Please switch to another game mode or server and try again.")
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                elif suboption[0] == "2":
                    grid_champions = await (await connection.request("GET", "/lol-champ-select/v1/all-grid-champions")).json() #该接口在自定义对局中不会及时更新，因此在使用该功能时不能完全依赖于程序提示，需要结合客户端来进行判断（The result from this endpoint doesn't update in time, so when using this function, users shouldn't completely rely on the program prompts. Instead, it's highly suggested to judge with the help of League Client）
                    grid_champions = {champion["id"]: champion for champion in grid_champions}
                    positions = ["top", "jungle", "middle", "bottom", "support"]
                    positions_zh = ["上路", "打野", "中路", "下路", "辅助"]
                    favoriteChampions = {"top": [], "jungle": [], "middle": [], "bottom": [], "support": []}
                    for champion in grid_champions.values():
                        for position in champion["positionsFavorited"]:
                            favoriteChampions[position].append(champion["id"])
                    logPrint("请选择一条分路：\nPlease choose a position:\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路（Bottom）\n5\t辅助（Support）")
                    while True:
                        position_index = logInput()
                        if position_index == "":
                            continue
                        elif position_index[0] == "0":
                            break
                        elif position_index[0] in list(map(str, range(1, 6))):
                            position_index = int(position_index[0])
                            current_position = positions[position_index - 1]
                            current_position_zh = positions_zh[position_index - 1]
                            logPrint("全英雄最爱情况如下：\nChampion favoriteness is as follows:")
                            grid_champion_df = await sort_grid_champions(connection)
                            grid_champion_df_fields_to_print = ["id", "name", "favorite_top", "favorite_jungle", "favorite_middle", "favorite_bottom", "favorite_support"]
                            print(format_df(grid_champion_df.loc[:, grid_champion_df_fields_to_print])[0])
                            log.write(format_df(grid_champion_df.loc[:, grid_champion_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                            logPrint("请输入您想要设为最爱或取消设为最爱的英雄序号：\nPlease enter the ids of champions you want to favorite or unfavorite:")
                            while True:
                                index_got = False
                                champion_index = logInput()
                                if champion_index == "":
                                    continue
                                elif champion_index == "0":
                                    index_got = False
                                    break
                                elif champion_index == "all":
                                    champion_indices = list(grid_champion_df.loc[1:, "id"])
                                    index_got = True
                                    break
                                else:
                                    try:
                                        champion_indices = eval(champion_index)
                                    except:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    else:
                                        if isinstance(champion_indices, int):
                                            champion_indices = [champion_indices]
                                        elif not isinstance(champion_indices, list):
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            continue
                                    if all(map(lambda x: isinstance(x, int) and x in grid_champion_df.loc[1:, "id"], champion_indices)) and len(champion_indices) == len(set(champion_indices)):
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                logPrint("您选择了以下英雄：\nYou selected the following champions:")
                                grid_champion_df_selected = pandas.concat([grid_champion_df.iloc[:1, :], grid_champion_df[grid_champion_df["id"].isin(champion_indices)]])
                                print(format_df(grid_champion_df_selected.loc[:, grid_champion_df_fields_to_print])[0])
                                log.write(format_df(grid_champion_df_selected.loc[:, grid_champion_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                logPrint("是否确认将以上英雄设为或取消设为您最爱的%s英雄？（输入任意键以确认，否则取消。）\nDo you want to favorite or unfavorite the above champions as %s? (Submit any non-empty string to confirm, or null to cancel.)" %(current_position_zh, current_position))
                                favor_confirm = logInput()
                                favor_confirm = bool(favor_confirm)
                                if favor_confirm:
                                    for championId in champion_indices:
                                        current_championName = grid_champions[championId]["name"]
                                        positionFavorited = current_position in grid_champions[championId]["positionsFavorited"]
                                        response = await (await connection.request("POST", "/lol-champ-select/v1/toggle-favorite/%d/%s" %(championId, positions[position_index - 1]))).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            if positionFavorited:
                                                logPrint("将%s取消设为您最爱的%s英雄的过程出现了问题。\nAn error occurs when the program unfavorited %s as %s." %(current_championName, current_position_zh, current_championName, current_position))
                                            else:
                                                logPrint("将%s设为您最爱的%s英雄的过程出现了问题。\nAn error occurs when the program favorited %s as %s." %(current_championName, current_position_zh, current_championName, current_position))
                                        else:
                                            if positionFavorited:
                                                logPrint("%s已取消设为您最爱的%s英雄。\n%s is unfavorited as %s." %(current_championName, current_position_zh, current_championName, current_position))
                                            else:
                                                logPrint("%s已设为您最爱的%s英雄。\n%s is favorited as %s." %(current_championName, current_position_zh, current_championName, current_position))
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        grid_champions = await (await connection.request("GET", "/lol-champ-select/v1/all-grid-champions")).json()
                        grid_champions = {champion["id"]: champion for champion in grid_champions}
                        positions = ["top", "jungle", "middle", "bottom", "support"]
                        positions_zh = ["上路", "打野", "中路", "下路", "辅助"]
                        favoriteChampions = {"top": [], "jungle": [], "middle": [], "bottom": [], "support": []}
                        for champion in grid_champions.values():
                            for position in champion["positionsFavorited"]:
                                favoriteChampions[position].append(champion["id"])
                        logPrint("请选择一条分路：\nPlease choose a position:\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路（Bottom）\n5\t辅助（Support）")
                elif suboption[0] == "3":
                    muted_players = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                    if len(muted_players) == 0:
                        logPrint("当前无静音玩家。\nThere's not any muted player.")
                    else:
                        logPrint("静音玩家如下：\nMuted players:")
                        muted_player_df = await sort_muted_players(connection)
                        print(format_df(muted_player_df, print_index = True)[0])
                        log.write(format_df(muted_player_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        for i in range(len(muted_players)):
                            player = muted_players[i]
                            response = await (await connection.request("POST", "/lol-champ-select/v1/toggle-player-muted", data = player)).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint("解除玩家%d静音失败。\nFailed to unmute Player %d." %(i + 1, i + 1))
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                muted_players_new = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                                if player in muted_players_new:
                                    logPrint("解除玩家%d静音失败。\nFailed to unmute Player %d." %(i + 1, i + 1))
                                else:
                                    logPrint("解除玩家%d静音成功。\nSuccessfully unmuted Player %d." %(i + 1, i + 1))
                elif suboption[0] == "4":
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        if champ_select_session["isCustomGame"]:
                            if champ_select_session["isSpectating"]:
                                logPrint('''目前不支持通过接口取消观战。请手动单击客户端的“退出观战”按钮，或者在进入游戏后退出游戏。\nCancelling spectating through LCU API isn't currently supported. Please manually click "Quit Spectating" button, or exit the game after the client launched spectating.''')
                            else:
                                response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/cancel-champ-select")).json()
                                logPrint(response)
                                if isinstance(response, dict) and "errorCode" in response:
                                    logPrint('退出英雄阶段的过程发生了异常。请尝试手动点击客户端右下角的“退出”按钮，或者重启客户端。\nAn error occurred when the program is trying to quit the champ select stage. Please try manually clicking the "Quit" button on the bottom-right corner of League Client, or restart the client.')
                                else:
                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                    gameflow_phase = await get_gameflow_phase(connection)
                                    if gameflow_phase == None:
                                        logPrint("您已退出英雄选择阶段。\nYou've quited the champ select stage.")
                                    else:
                                        logPrint("退出失败。\nExit failed.")
                        else:
                            logPrint("当前游戏模式不支持早退。请切换游戏模式并稍后重试。\nEarly exit isn't supported in this game mode. Please switch to another game mode and try again later.")
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t解锁全员战斗加成（Unlock battle boost）\n2\t设置最爱的分路英雄（Toggle favorite champions on different positions）\n3\t清空静音玩家（Clear muted players）\n4\t退出英雄选择阶段（Exit the champ select stage）")
        elif option[0] == "7":
            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            logPrint(champ_select_session)
            with open("champ-select-session.json", "w", encoding = "utf-8") as fp:
                json.dump(champ_select_session, fp, indent = 4, ensure_ascii = False)
            logPrint('英雄选择会话已导出到同目录下的“champ-select-session.json”。\nChamp select session has been exported into "champ-select-session.json" under the same directory.')
        elif option[0] == "8":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 游戏内模拟（In-game simulation）
#-----------------------------------------------------------------------------
async def inGame_simulation(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t向好友发送密语（Chat with friends）\n2\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] == "1":
            await chat(connection)
        elif option[0] == "2":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 赛后预结算阶段模拟（Pre-end-of-game stage simulation）
#-----------------------------------------------------------------------------
async def sort_ballot_players(connection):
    ballot_player_data = {}
    for i in range(len(ballot_player_header_keys)):
        key = ballot_player_header_keys[i]
        ballot_player_data[key] = []
    honor_ballot = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
    honoredPlayers = {player["recipientPuuid"]: player for player in honor_ballot["honoredPlayers"]}
    if not(isinstance(honor_ballot, dict) and "errorCode" in honor_ballot):
        for player in honor_ballot["eligibleAllies"] + honor_ballot["eligibleOpponents"]:
            player_info_recapture = 0
            player_info = await get_info(connection, player["puuid"])
            while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                logPrint(player_info["message"])
                player_info_recapture += 1
                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture))
                player_info = await get_info(connection, player["puuid"])
            if not player_info["info_got"]:
                logPrint(player_info["message"])
                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) capture failed!" %(player["puuid"], player["puuid"]))
            for i in range(len(ballot_player_header_keys)):
                key = ballot_player_header_keys[i]
                if i == 7 or i == 8: #召唤师信息相关键（Summoner information-related keys）
                    ballot_player_data[key].append(player_info["body"][key] if player_info["info_got"] else "")
                elif i == 9: #是否队友（`ally?`）
                    ballot_player_data[key].append(player in honor_ballot["eligibleAllies"])
                elif i == 10: #已赞誉（`honored`）
                    ballot_player_data[key].append(player["puuid"] in honoredPlayers)
                elif i == 11: #赞誉类型（`honorType`）
                    ballot_player_data[key].append(honoredPlayers[player["puuid"]]["honorType"] if player["puuid"] in honoredPlayers else "")
                elif i == 12: #赞誉类型标题（`honorType_tooltip_header`）
                    ballot_player_data[key].append(honorType_tooltip_headers.get(honoredPlayers[player["puuid"]]["honorType"], "") if player["puuid"] in honoredPlayers else "")
                elif i == 13: #赞誉类型正文（`honorType_tooltip_body`）
                    ballot_player_data[key].append(honorType_tooltip_bodies.get(honoredPlayers[player["puuid"]]["honorType"], "") if player["puuid"] in honoredPlayers else "")
                else:
                    ballot_player_data[key].append(player[key])
    ballot_player_statistics_output_order = [6, 7, 8, 5, 2, 9, 1, 3, 4, 0, 10, 11, 12, 13]
    ballot_player_data_organized = {}
    for i in ballot_player_statistics_output_order:
        key = ballot_player_header_keys[i]
        ballot_player_data_organized[key] = ballot_player_data[key]
    ballot_player_df = pandas.DataFrame(data = ballot_player_data_organized)
    for column in ballot_player_df:
        if ballot_player_df[column].dtype == "bool":
            ballot_player_df[column] = ballot_player_df[column].astype(str)
            for i in range(len(ballot_player_df)):
                ballot_player_df.loc[i, column] = "√" if ballot_player_df[column][i] == "True" else ""
    ballot_player_df = pandas.concat([pandas.DataFrame([ballot_player_header])[ballot_player_df.columns], ballot_player_df], ignore_index = True)
    return ballot_player_df

async def preEndOfGame_simulation(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n!1\t赞誉其他玩家（Honor players）\n2\t查看票数（Check the number of votes）\n3\t这次不行（Not this time）\n4\t输出荣誉投票信息（Print honor ballot information）\n5\t输出当前事件（Print current sequence event）\n6\t聊天（Chat）\n7\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('请选择一个对局预结算阶段相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a PreEndOfGame-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t完成预结算阶段的一个事件（Complete an event before the end of a game）\n2\t查看当前预结算阶段事件（Check the current event before the end of a game）\n3\t删除一个预结算阶段的事件（Delete an event before the end of a game）\n4\t修改一个预结算阶段的事件的显示优先级（Change the display priority of an event before the end of a game）')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection)
                elif suboption[0] == "0":
                    break
                elif suboption[0] in list(map(str, range(1, 5))):
                    if suboption[0] == "1":
                        logPrint("请输入一个事件名称：\nPlease input the name of the event:\nsequenceEventName = ", end = "")
                        sequenceEventName = input()
                        response = await (await connection.request("POST", f"/lol-pre-end-of-game/v1/complete/{sequenceEventName}")).json()
                    elif suboption[0] == "2":
                        response = await (await connection.request("GET", "/lol-pre-end-of-game/v1/currentSequenceEvent")).json()
                    elif suboption[0] == "3":
                        logPrint("请输入一个事件名称：\nPlease input the name of the event:\nsequenceEventName = ", end = "")
                        sequenceEventName = input()
                        response = await (await connection.request("DELETE", f"/lol-pre-end-of-game/v1/registration/{sequenceEventName}")).json()
                    else:
                        logPrint("请输入一个事件名称：\nPlease input the name of the event:\nsequenceEventName = ", end = "")
                        sequenceEventName = input()
                        logPrint("请输入你想要设置的显示优先级：\nPlease input the display priority of the event:\npriority = ", end = "")
                        priority = input()
                        response = await (await connection.request("DELETE", f"/lol-pre-end-of-game/v1/registration/{sequenceEventName}/{priority}")).json()
                    logPrint(response)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option[0] == "0":
            break
        elif option[0] == "1":
            global ballot_endpoint_notavailable_hint_printed
            if not ballot_endpoint_notavailable_hint_printed:
                logPrint("警告：当前操作无法通过程序完成。您可以在输出结果查看所有玩家的信息，但是请在客户端内通过点击来赞誉一名玩家。\nWarning: The current operation can't be accomplished by the program. You may look through the output to check all players' information, but please click in the client to honor a player.")
                ballot_endpoint_notavailable_hint_printed = True
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "PreEndOfGame":
                honor_ballot = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
                if honor_ballot["votePool"]["votes"] == 0:
                    logPrint("您已经没有赞誉票了。\nYou've run out of votes.")
                else:
                    ballot_player_df = await sort_ballot_players(connection)
                    ballot_player_df_fields_to_print = ["gameName", "tagLine", "ally?", "championName", "role", "botPlayer"]
                    if len(ballot_player_df) == 1:
                        logPrint("目前没有可以赞誉的玩家。\nThere's not any player to honor for now.")
                    else:
                        logPrint("赞誉那些做出了正面影响、表现了惊人韧性，或相处起来非常有趣的玩家。\nHonor players who made a positive impact, displayed great resilience, or were just fun to play with.")
                        print(format_df(ballot_player_df.loc[:, ballot_player_df_fields_to_print], print_index = True)[0])
                        log.write(format_df(ballot_player_df.loc[:, ballot_player_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        logPrint("请选择一名玩家：\nPlease select a player:")
                        while True:
                            index_got = False
                            player_index = logInput()
                            if player_index == "":
                                continue
                            elif player_index == "0":
                                index_got = False
                                break
                            elif player_index in list(map(str, range(1, len(ballot_player_df)))):
                                player_index = int(player_index)
                                index_got = True
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if index_got:
                            player_summonerId = ballot_player_df.loc[player_index, "summonerId"]
                            player_puuid = ballot_player_df.loc[player_index, "puuid"]
                            honorType = "HEART" #取值（Available values）：COOL、SHOTCALLER、HEART
                            gameId = honor_ballot["gameId"]
                            body = {"summonerId": player_summonerId, "puuid": player_puuid, "honorType": honorType, "gameId": gameId}
                            logPrint(body)
                            response = await (await connection.request("POST", "/lol-honor-v2/v1/honor-player", data = body)).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint("赞誉失败。\nHonor failed.")
                            elif response == "failed_to_contact_honor_server":
                                logPrint("无法连接到赞誉服务器。请在客户端内手动点击一名玩家以赞誉之。\nFailed to contact honor server. Please manually click on a player to honor it.")
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                honor_ballot = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
                                if player_puuid in list(map(lambda x: x["recipientPuuid"], honor_ballot["honoredPlayers"])):
                                    logPrint("赞誉成功。\nHonor succeeded.")
                                else:
                                    logPrint("赞誉失败。\nHonor failed.")
            else:
                logPrint("赞誉阶段已过。\nThe honor phase has passed.")
        elif option[0] == "2":
            honor_ballot = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
            if isinstance(honor_ballot, dict) and "errorCode" in honor_ballot:
                logPrint("赞誉投票信息获取异常。\nHonor ballot information capture failed.")
            else:
                logPrint("你每局获取1张荣誉投票，并且至多总共储存4张。未使用的投票可用在下一局比赛。\n")
                votes_total = honor_ballot["votePool"]["votes"]
                votes_fromGamePlayed = honor_ballot["votePool"]["fromGamePlayed"]
                votes_fromHighHonor = honor_ballot["votePool"]["fromHighHonor"]
                votes_fromRecentHonors = honor_ballot["votePool"]["fromRecentHonors"]
                votes_fromRollover = honor_ballot["votePool"]["fromRollover"]
                logPrint(f"总票数（Total votes）：{votes_total}")
                if votes_total > 0:
                    logPrint("获取额外投票，来自：")
                    if votes_fromGamePlayed > 0:
                        logPrint(f"- +{votes_fromGamePlayed} 进行一场对局")
                    if votes_fromHighHonor > 0:
                        logPrint(f"- +{votes_fromHighHonor} 达到5级荣誉")
                    if votes_fromRecentHonors > 0:
                        logPrint(f"- +{votes_fromRecentHonors} 上一局被赞誉")
                    if votes_fromRollover > 0:
                        logPrint(f"- +{votes_fromRollover} 未使用的投票")
                    logPrint("Earn additional votes from:")
                    if votes_fromGamePlayed > 0:
                        logPrint(f"- +{votes_fromGamePlayed} Played a game")
                    if votes_fromHighHonor > 0:
                        logPrint(f"- +{votes_fromHighHonor} Being Honor Level 5")
                    if votes_fromRecentHonors > 0:
                        logPrint(f"- +{votes_fromRecentHonors} Being honored last game")
                    if votes_fromRollover > 0:
                        logPrint(f"- +{votes_fromRollover} Unused votes")
        elif option[0] == "3":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "PreEndOfGame":
                response = await (await connection.request("DELETE", "/lol-honor-v2/v1/ballot")).json()
                logPrint(response)
                if isinstance(response, dict) and "errorCode" in response:
                    logPrint("跳过赞誉阶段失败。\nSkipping honor phase failed.")
                else:
                    time.sleep(GLOBAL_RESPONSE_LAG)
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "EndOfGame":
                        logPrint("您已跳过赞誉阶段。\nYou skipped the honor phase.")
                    else:
                        logPrint("跳过赞誉阶段失败。\nSkipping honor phase failed.")
            else:
                logPrint("赞誉阶段已过。\nThe honor phase has passed.")
        elif option[0] == "4":
            honor_ballot = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
            logPrint(honor_ballot)
            with open("honor-ballot.json", "w", encoding = "utf-8") as fp:
                json.dump(honor_ballot, fp, indent = 4, ensure_ascii = False)
            logPrint('荣誉投票信息已导出到同目录下的“honor-ballot.json”。\nHonor ballot information has been exported into "honor-ballot.json" under the same directory.')
        elif option[0] == "5":
            currentSequenceEvent = await (await connection.request("GET", "/lol-pre-end-of-game/v1/currentSequenceEvent")).json()
            logPrint(currentSequenceEvent)
            with open("currentSequenceEvent.json", "w", encoding = "utf-8") as fp:
                json.dump(currentSequenceEvent, fp, indent = 4, ensure_ascii = False)
            logPrint('当前序列事件信息已导出到同目录下的“currentSequenceEvent.json”。\nCurrent sequence event has been exported into "currentSequenceEvent.json" under the same directory.')
        elif option[0] == "6":
            await chat(connection)
        elif option[0] == "7":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 赛后结算阶段模拟（End-of-game stage simulation）
#-----------------------------------------------------------------------------
async def sort_eog_champion_mastery_update(connection):
    eog_mastery_update_data = {"项目": [], "Items": [], "值": []}
    mastery_updates = await (await connection.request("GET", "/lol-end-of-game/v1/champion-mastery-updates")).json()
    if not (isinstance(mastery_updates, dict) and "errorCode" in mastery_updates):
        player_info_recapture = 0
        player_info = await get_info(mastery_updates["puuid"])
        while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
            logPrint(player_info["message"])
            player_info_recapture += 1
            logPrint("当前玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of current player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(mastery_updates["puuid"], player_info_recapture, mastery_updates["puuid"], player_info_recapture))
        if not player_info["info_got"]:
            logPrint(player_info["message"])
            logPrint("当前玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of current player (puuid: %s) capture failed!" %(mastery_updates["puuid"], mastery_updates["puuid"]))
        for i in range(len(eog_mastery_update_header_keys)):
            key = eog_mastery_update_header_keys[i]
            eog_mastery_update_data["项目"].append(eog_mastery_update_header[key])
            eog_mastery_update_data["Items"].append(key)
            if i >= 19 and i <= 21: #英雄相关键（Champion-related keys）
                value = LoLChampions[mastery_updates["championId"]][key.split("_")[1]] if mastery_updates["championId"] in LoLChampions else ""
            elif i >= 22: #召唤师信息相关键（Summoner information-related keys）
                value = player_info["body"][key] if player_info["info_got"] else ""
            else:
                value = mastery_updates[key]
            eog_mastery_update_data["值"].append(value)
    eog_mastery_update_statistics_output_order = [2, 15, 22, 23, 1, 19, 21, 20, 3, 8, 6, 4, 7, 9, 12, 14, 10, 11, 0, 13, 16, 17, 18]
    eog_mastery_update_data_organized = {"项目": [], "Items": [], "值": []}
    for i in eog_mastery_update_statistics_output_order:
        key = eog_mastery_update_header_keys[i]
        value = eog_mastery_update_data["值"][i]
        eog_mastery_update_data_organized["项目"].append(eog_mastery_update_header[key])
        eog_mastery_update_data_organized["Items"].append(key)
        eog_mastery_update_data_organized["值"].append(value)
    eog_mastery_update_df = pandas.DataFrame(data = eog_mastery_update_data_organized)
    return eog_mastery_update_df

async def sort_eog_stat_lol_metadata(connection):
    eog_stat_metadata_lol = {"项目": [], "Items": [], "值": []}
    queues_source = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    queues = {}
    for queue in queues_source:
        queues[queue["id"]] = queue
    eog_stats_block = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
    if not (isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block):
        LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/%d" %(eog_stats_block["gameId"]))).json()
        for i in range(len(eog_stat_metadata_lol_header_keys)):
            key = eog_stat_metadata_lol_header_keys[i]
            eog_stat_metadata_lol["项目"].append(eog_stat_metadata_lol_header[key])
            eog_stat_metadata_lol["Items"].append(key)
            if i <= 46:
                if i == 41: #对局结算时间（`endOfGameTime`）
                    value = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(eog_stats_block["endOfGameTimestamp"] // 1000))
                elif i == 42: #持续时长（`gameLength_norm`）
                    value = lcuTimestamp(eog_stats_block["gameLength"])
                elif i == 43: #新的召唤师技能名称（`newSpellNames`）
                    value = list(map(lambda x: spells[x]["name"] if x in spells else "", eog_stats_block["newSpells"]))
                elif i == 44: #下次首胜剩余时间（`timeUntilNextFirstWinBonus_norm`）
                    cooldown = eog_stats_block["timeUntilNextFirstWinBonus"]
                    cooldown_hour = cooldown // 3600
                    cooldown_minute = cooldown // 3600 % 60
                    cooldown_second = cooldown % 60
                    value = "%d:%02d:%02d" %(cooldown_hour, cooldown_minute, cooldown_second)
                elif i == 45: #队列序号（`queueId`）
                    value = "" if isinstance(LoLGame_info, dict) and "errorCode" in LoLGame_info else LoLGame_info["queueId"]
                elif i == 46: #游戏模式名称（`gameModeName`）
                    value = "" if isinstance(LoLGame_info, dict) and "errorCode" in LoLGame_info else "自定义" if LoLGame_info["queueId"] == 0 else queues[LoLGame_info["queueId"]]["name"]
                else:
                    value = eog_stats_block[key]
            else:
                if i == 65: #战斗加成可用皮肤名称（`teamBoost availableSkinNames`）
                    value = "" if eog_stats_block["teamBoost"] == None else list(map(lambda x: championSkins[x]["name"] if x in championSkins else "", eog_stats_block["teamBoost"]["availableSkins"]))
                else:
                    value = eog_stats_block
                    for subkey in key.split():
                        if value == None or not subkey in value:
                            value = ""
                            break
                        else:
                            value = value[subkey]
            eog_stat_metadata_lol["值"].append(value)
    eog_stat_metadata_lol_statistics_output_order = [13, 15, 46, 17, 6, 45, 34, 35, 16, 14, 42, 8, 41, 32, 33, 3, 24, 18, 40, 23, 9, 5, 10, 29, 22, 30, 31, 20, 2, 1, 21, 37, 11, 39, 44, 0, 55, 54, 51, 52, 56, 57, 53, 64, 62, 63, 61, 58, 65, 59, 60, 28, 43, 4, 7, 38, 12, 19, 25, 26, 27, 47, 48, 49, 50]
    eog_stat_metadata_lol_organized = {"项目": [], "Items": [], "值": []}
    for i in eog_stat_metadata_lol_statistics_output_order:
        key = eog_stat_metadata_lol_header_keys[i]
        value = eog_stat_metadata_lol["值"][i]
        eog_stat_metadata_lol_organized["项目"].append(eog_stat_metadata_lol_header[key])
        eog_stat_metadata_lol_organized["Items"].append(key)
        eog_stat_metadata_lol_organized["值"].append(value)
    eog_stat_metaDf_lol = pandas.DataFrame(data = eog_stat_metadata_lol_organized)
    return eog_stat_metaDf_lol

async def sort_eog_teamstat_lol_data(connection):
    eog_teamstat_data_lol = {}
    for i in range(len(eog_teamstat_data_lol_header_keys)):
        key = eog_teamstat_data_lol_header_keys[i]
        eog_teamstat_data_lol[key] = []
    eog_stats_block = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
    if not (isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block):
        for team in eog_stats_block["teams"]:
            stats = team["stats"]
            for i in range(len(eog_teamstat_data_lol_header_keys)):
                key = eog_teamstat_data_lol_header_keys[i]
                if i <= 8:
                    if i == 8: #阵营（`team`）
                        eog_teamstat_data_lol[key].append(team_colors_int[team["teamId"]])
                    else:
                        eog_teamstat_data_lol[key].append(team[key])
                else:
                    if i in [12, 13, 19, 82, 106, 107]: #逻辑值键（Keys with boolean values）
                        eog_teamstat_data_lol[key].append(False if stats == None else bool(stats.get(key.split()[1], 0)))
                    elif i == 108: #队伍击杀得分（`stats KDA`）
                        eog_teamstat_data_lol[key].append("" if stats == None else "%d/%d/%d" %(stats["CHAMPIONS_KILLED"], stats["NUM_DEATHS"], stats["ASSISTS"]) if all(map(lambda x: x in stats, ["CHAMPIONS_KILLED", "NUM_DEATHS", "ASSISTS"])) else "")
                    else:
                        eog_teamstat_data_lol[key].append("" if stats == None else stats.get(key.split()[1], ""))
    eog_teamstat_data_lol_statistics_output_order = [7, 8, 2, 1, 5, 6, 0, 4, 3, 18, 108, 11, 31, 9, 16, 17, 84, 95, 87, 59, 21, 98, 85, 58, 20, 97, 15, 86, 88, 89, 93, 94, 91, 92, 60, 22, 99, 90, 102, 105, 104, 79, 103, 14, 23, 24, 26, 25, 100, 10, 83, 27, 28, 29, 30, 96, 80, 81, 106, 82, 12, 13, 107, 19, 101]
    eog_teamstat_data_lol_organized = {}
    for i in eog_teamstat_data_lol_statistics_output_order:
        key = eog_teamstat_data_lol_header_keys[i]
        eog_teamstat_data_lol_organized[key] = eog_teamstat_data_lol[key]
    eog_teamstat_df_lol = pandas.DataFrame(data = eog_teamstat_data_lol_organized)
    for column in eog_teamstat_df_lol:
        if eog_teamstat_df_lol[column].dtype == "bool":
            eog_teamstat_df_lol[column] = eog_teamstat_df_lol[column].astype(str)
            for i in range(len(eog_teamstat_df_lol)):
                eog_teamstat_df_lol.loc[i, column] = "√" if eog_teamstat_df_lol[column][i] == "True" else ""
    eog_teamstat_df_lol = pandas.concat([pandas.DataFrame([eog_teamstat_data_lol_header])[eog_teamstat_df_lol.columns], eog_teamstat_df_lol], ignore_index = True)
    return eog_teamstat_df_lol

async def sort_eog_playerstat_lol_data(connection):
    eog_playerstat_data_lol = {}
    for i in range(len(eog_playerstat_data_lol_header_keys)):
        key = eog_playerstat_data_lol_header_keys[i]
        eog_playerstat_data_lol[key] = []
    eog_stats_block = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
    if not (isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block):
        for team in eog_stats_block["teams"]:
            for player in team["players"]:
                stats = player["stats"]
                for i in range(len(eog_playerstat_data_lol_header_keys)):
                    key = eog_playerstat_data_lol_header_keys[i]
                    if i <= 46:
                        if i == 6: #本人标记（`isLocalPlayer`）
                            eog_playerstat_data_lol[key].append("☆" if player["isLocalPlayer"] else "")
                        elif i >= 26 and i <= 39: #装备相关键（Item-related keys）
                            itemId = player["items"][int(key.split("_")[0][4:])]
                            eog_playerstat_data_lol[key].append(LoLItems[itemId][key.split("_")[1]] if itemId in LoLItems else itemId if i <= 32 else "")
                        elif i == 40 or i == 41: #召唤师图标相关键（Summoner icon-related keys）
                            profileIconId = player["profileIconId"]
                            eog_playerstat_data_lol[key].append(summonerIcons[profileIconId][key.split("_")[1]] if profileIconId in summonerIcons and key.split("_")[1] in summonerIcons[profileIconId] else profileIconId if i == 40 else "")
                        elif i >= 42 and i <= 45: #召唤师技能相关键（Summoner spell-related keys）
                            spellId = player[key.split("_")[0] + "Id"]
                            eog_playerstat_data_lol[key].append(spells[spellId][key.split("_")[1]] if spellId in spells else spellId if i <= 43 else "")
                        elif i == 46: #阵营（`team_color`）
                            eog_playerstat_data_lol[key].append(team_colors_int[player["teamId"]])
                        else:
                            eog_playerstat_data_lol[key].append(player[key])
                    else:
                        if i in [50, 51, 57, 120, 144, 145]:
                            eog_playerstat_data_lol[key].append(bool(stats.get(key.split()[1], 0)))
                        elif i == 146: #击杀得分（`stats KDA`）
                            eog_playerstat_data_lol[key].append("%d/%d/%d" %(stats["CHAMPIONS_KILLED"], stats["NUM_DEATHS"], stats["ASSISTS"]) if all(map(lambda x: x in stats, ["CHAMPIONS_KILLED", "NUM_DEATHS", "ASSISTS"])) else "")
                        elif i >= 147 and i <= 150: #符文系相关键（Perkstyle-related keys）
                            if key.split()[1] in stats:
                                perkstyleId = stats[key.split()[1]]
                                eog_playerstat_data_lol[key].append(perkstyles[perkstyleId][key.split()[2]] if perkstyleId in perkstyles else perkstyleId if i == 147 or i == 149 else "")
                            else:
                                eog_playerstat_data_lol[key].append("")
                        elif i >= 151 and i <= 168: #符文相关键（Perk-related keys）
                            if key.split()[1] in stats:
                                perkId = stats[key.split()[1]]
                                if perkId in perks:
                                    if i <= 156:
                                        perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key.split()[1] + "_VAR1"]))
                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key.split()[1] + "_VAR2"]))
                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key.split()[1] + "_VAR3"]))
                                        eog_playerstat_data_lol[key].append(perk_EndOfGameStatDescs)
                                    else:
                                        eog_playerstat_data_lol[key].append(perks[perkId][key.split()[2]])
                                else:
                                    eog_playerstat_data_lol[key].append(perkId if i >= 157 and i <= 162 else "")
                            else:
                                eog_playerstat_data_lol[key].append("")
                        elif i >= 169 and i <= 186: #强化符文相关键（Augment-related keys）
                            if key.split()[1] in stats:
                                playerAugmentId = stats[key.split()[1]]
                                if playerAugmentId == 0:
                                    eog_playerstat_data_lol[key].append("")
                                elif playerAugmentId in CherryAugments:
                                    if i >= 181:
                                        eog_playerstat_data_lol[key].append(augment_rarity[CherryAugments[playerAugmentId][key.split()[2]]])
                                    else:
                                        eog_playerstat_data_lol[key].append(CherryAugments[playerAugmentId][key.split()[2]])
                                else:
                                    eog_playerstat_data_lol[key].append(playerAugmentId if i >= 169 and i <= 174 else "")
                            else:
                                eog_playerstat_data_lol[key].append("")
                        elif i == 187: #子阵营（`playerSubteamColor`）
                            eog_playerstat_data_lol[key].append(subteam_color[stats["PLAYER_SUBTEAM"]] if "PLAYER_SUBTEAM" in stats else "")
                        else:
                            eog_playerstat_data_lol[key].append(stats.get(key.split()[1], ""))
    eog_playerstat_data_lol_statistics_output_order = [24, 46, 115, 187, 6, 23, 14, 15, 22, 13, 12, 40, 41, 10, 0, 8, 9, 25, 11, 1, 2, 3, 18, 17, 19, 16, 4, 56, 20, 42, 44, 21, 43, 45, 7, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 146, 99, 169, 181, 175, 100, 170, 182, 176, 101, 171, 183, 177, 102, 172, 184, 178, 103, 173, 185, 179, 104, 174, 186, 180, 49, 69, 47, 54, 55, 133, 122, 125, 97, 59, 136, 123, 96, 58, 135, 53, 124, 126, 127, 131, 132, 129, 130, 98, 60, 137, 128, 140, 143, 142, 117, 141, 52, 61, 62, 64, 63, 138, 48, 121, 65, 66, 67, 68, 134, 70, 147, 148, 71, 149, 150, 72, 73, 74, 75, 157, 163, 151, 76, 77, 78, 79, 158, 164, 152, 80, 81, 82, 83, 159, 165, 153, 84, 85, 86, 87, 160, 166, 154, 88, 89, 90, 91, 161, 167, 155, 92, 93, 94, 95, 162, 168, 156, 118, 119, 144, 120, 50, 51, 145, 57, 116, 139, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]
    eog_playerstat_data_lol_organized = {}
    for i in eog_playerstat_data_lol_statistics_output_order:
        key = eog_playerstat_data_lol_header_keys[i]
        eog_playerstat_data_lol_organized[key] = eog_playerstat_data_lol[key]
    eog_playerstat_df_lol = pandas.DataFrame(data = eog_playerstat_data_lol_organized)
    for column in eog_playerstat_df_lol:
        if eog_playerstat_df_lol[column].dtype == "bool":
            eog_playerstat_df_lol[column] = eog_playerstat_df_lol[column].astype(str)
            for i in range(len(eog_playerstat_df_lol)):
                eog_playerstat_df_lol.loc[i, column] = "√" if eog_playerstat_df_lol[column][i] == "True" else ""
    eog_playerstat_df_lol = pandas.concat([pandas.DataFrame([eog_playerstat_data_lol_header])[eog_playerstat_df_lol.columns], eog_playerstat_df_lol], ignore_index = True)
    return eog_playerstat_df_lol

async def sort_eog_stat_tft_metadata(connection):
    eog_stat_metadata_tft = {"项目": [], "Items": [], "值": []}
    queues_source = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    queues = {}
    for queue in queues_source:
        queues[queue["id"]] = queue
    tft_eog_stats = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
    if not (isinstance(tft_eog_stats, dict) and "errorCode" in tft_eog_stats):
        for i in range(len(eog_stat_metadata_tft_header_keys)):
            key = eog_stat_metadata_tft_header_keys[i]
            eog_stat_metadata_tft["项目"].append(eog_stat_metadata_tft_header[key])
            eog_stat_metadata_tft["Items"].append(key)
            if i == 6: #持续时长（`gameLength_norm`）
                value = lcuTimestamp(tft_eog_stats["gameLength"])
            elif i == 7: #游戏模式名称（`gameModeName`）
                value = "" if tft_eog_stats["queueId"] == 0 else queues[tft_eog_stats["queueId"]]["name"]
            else:
                value = tft_eog_stats[key]
            eog_stat_metadata_tft["值"].append(value)
    eog_stat_metadata_tft_statistics_output_order = [0, 7, 4, 5, 2, 1, 6, 3]
    eog_stat_metadata_tft_organized = {"项目": [], "Items": [], "值": []}
    for i in eog_stat_metadata_tft_statistics_output_order:
        key = eog_stat_metadata_tft_header_keys[i]
        value = eog_stat_metadata_tft["值"][i]
        eog_stat_metadata_tft_organized["项目"].append(eog_stat_metadata_tft_header[key])
        eog_stat_metadata_tft_organized["Items"].append(key)
        eog_stat_metadata_tft_organized["值"].append(value)
    eog_stat_metaDf_tft = pandas.DataFrame(data = eog_stat_metadata_tft_organized)
    return eog_stat_metaDf_tft

async def sort_eog_stat_tft_data(connection):
    eog_stat_data_tft = {}
    for i in range(len(eog_stat_data_tft_header_keys)):
        key = eog_stat_data_tft_header_keys[i]
        eog_stat_data_tft[key] = []
    tft_eog_stats = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
    if not (isinstance(tft_eog_stats, dict) and "errorCode" in tft_eog_stats):
        for player in tft_eog_stats["players"]:
            for i in range(len(eog_stat_data_tft_header_keys)):
                key = eog_stat_data_tft_header_keys[i]
                if i <= 16:
                    if i == 6: #本人标记（`isLocalPlayer`）
                        eog_stat_data_tft[key].append("☆" if player["isLocalPlayer"] else "")
                    elif i >= 15: #召唤师图标相关键（Summoner icon-related keys）
                        eog_stat_data_tft[key].append(summonerIcons[player["iconId"]][key.split()[1]] if player["iconId"] in summonerIcons and key.split()[1] in summonerIcons[player["iconId"]] else player["iconId"] if i == 15 else "")
                    else:
                        eog_stat_data_tft[key].append(player[key])
                elif i <= 28: #强化符文相关键（Augment-related keys）
                    if "augments" in player:
                        augment_index = int(key.split()[0][7:]) - 1
                        eog_stat_data_tft[key].append(player["augments"][augment_index][key.split()[1]] if augment_index < len(player["augments"]) else "")
                    else:
                        eog_stat_data_tft[key].append("")
                elif i <= 94: #棋子相关键（TFT champion-related keys）
                    unit_index = int(key.split()[0][4:])
                    eog_stat_data_tft[key].append(player["boardPieces"][unit_index][key.split()[1]] if unit_index < len(player["boardPieces"]) else "")
                elif i <= 226: #装备相关键（Item-related keys）
                    unit_index = int(key.split()[0][4:])
                    item_index = int(key.split()[1][4:]) - 1
                    eog_stat_data_tft[key].append(player["boardPieces"][unit_index]["items"][item_index][key.split()[2]] if unit_index < len(player["boardPieces"]) and item_index < len(player["boardPieces"][unit_index]["items"]) else "")
                else:
                    value = player
                    for subkey in key.split():
                        if value == None or not subkey in value:
                            value = ""
                            break
                        else:
                            value = value[subkey]
                    eog_stat_data_tft[key].append(value)
    eog_stat_data_tft_statistics_output_order = [6, 14, 10, 11, 13, 8, 4, 15, 16, 12, 5, 7, 229, 227, 228, 3, 2, 9, 235, 236, 234, 230, 231, 232, 233, 0, 20, 26, 23, 17, 21, 27, 24, 18, 22, 28, 25, 19, 1, 29, 32, 33, 31, 30, 34, 96, 98, 97, 95, 100, 102, 101, 99, 104, 106, 105, 103, 35, 38, 39, 37, 36, 40, 108, 110, 109, 107, 112, 114, 113, 111, 116, 118, 117, 115, 41, 44, 45, 43, 42, 46, 120, 122, 121, 119, 124, 126, 125, 123, 128, 130, 129, 127, 47, 50, 51, 49, 48, 52, 132, 134, 133, 131, 136, 138, 137, 135, 140, 142, 141, 139, 53, 56, 57, 55, 54, 58, 144, 146, 145, 143, 148, 150, 149, 147, 152, 154, 153, 151, 59, 62, 63, 61, 60, 64, 156, 158, 157, 155, 160, 162, 161, 159, 164, 166, 165, 163, 65, 68, 69, 67, 66, 70, 168, 170, 169, 167, 172, 174, 173, 171, 176, 178, 177, 175, 71, 74, 75, 73, 72, 76, 180, 182, 181, 179, 184, 186, 185, 183, 188, 190, 189, 187, 77, 80, 81, 79, 78, 82, 192, 194, 193, 191, 196, 198, 197, 195, 200, 202, 201, 199, 83, 86, 87, 85, 84, 88, 204, 206, 205, 203, 208, 210, 209, 207, 212, 214, 213, 211, 89, 92, 93, 91, 90, 94, 216, 218, 217, 215, 220, 222, 221, 219, 224, 226, 225, 223]
    eog_stat_data_tft_organized = {}
    for i in eog_stat_data_tft_statistics_output_order:
        key = eog_stat_data_tft_header_keys[i]
        eog_stat_data_tft_organized[key] = eog_stat_data_tft[key]
    eog_stat_df_tft = pandas.DataFrame(data = eog_stat_data_tft_organized)
    for column in eog_stat_df_tft:
        if eog_stat_df_tft[column].dtype == "bool":
            eog_stat_df_tft[column] = eog_stat_df_tft[column].astype(str)
            for i in range(len(eog_stat_df_tft)):
                eog_stat_df_tft.loc[i, column] = "√" if eog_stat_df_tft[column][i] == "True" else ""
    eog_stat_df_tft = pandas.concat([pandas.DataFrame([eog_stat_data_tft_header])[eog_stat_df_tft.columns], eog_stat_df_tft], ignore_index = True)
    return eog_stat_df_tft

async def endOfGame_simulation(connection):
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t查看英雄成就点数更新情况（Check champion mastery updates）\n2\t查看计分板数据（Check stats block）\n3\t聊天（Chat）\n4\t再来一局（Play again）\n5\t离开（Dismiss）\n!6\t唤起赞誉投票界面（Recall honor vote phase）\n7\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('请选择一个对局结算阶段相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select an EndOfGame-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t查看英雄联盟对局结算阶段的英雄成就更新情况（Check the champion mastery update at the end of a LoL game）\n2\t查看英雄联盟对局结算阶段的对局统计（Check game stats at the end of a LoL game）\n3\t查看客户端存储的对局结算阶段的对局统计结果（Check the game stats stored client-side at the end of a game）\n4\t修改客户端存储的对局结算阶段的对局统计结果（Change the game stats stored client-side at the end of a game）\n5\t退出对局结算阶段并返回大厅（Exit the end of a game and return to the home page）\n6\t查看云顶之弈对局结算阶段的对局统计（Check the game stats at the end of a TFT game）')
            while True:
                suboption = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection)
                elif suboption[0] == "0":
                    break
                elif suboption[0] in list(map(str, range(1, 7))):
                    if suboption[0] == "1":
                        response = await (await connection.request("GET", "/lol-end-of-game/v1/champion-mastery-updates")).json()
                    elif suboption[0] == "2":
                        response = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
                    elif suboption[0] == "3":
                        response = await (await connection.request("GET", "/lol-end-of-game/v1/gameclient-eog-stats-block")).json()
                    elif suboption[0] == "4":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"gameId": 0, "gameMode": "string", "statsBlock": {"additionalProp1": {}}, "queueId": 0, "queueType": "string", "isRanked": True}\nstats = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body)
                            response = await (await connection.request("PUT", "/lol-end-of-game/v1/gameclient-eog-stats-block")).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption[0] == "5":
                        response = await (await connection.request("POST", "/lol-end-of-game/v1/state/dismiss-stats")).json()
                    else:
                        response = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
                    logPrint(response)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option[0] == "0":
            break
        elif option[0] == "1":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                mastery_updates = await (await connection.request("GET", "/lol-end-of-game/v1/champion-mastery-updates")).json()
                if isinstance(mastery_updates, dict) and "errorCode" in mastery_updates:
                    logPrint(mastery_updates)
                    if mastery_updates["httpStatus"] == 404 and mastery_updates["message"] == "Champion mastery data is not currently available.":
                        logPrint("英雄成就更新数据目前不可用。请确保您现在处于匹配对局的结算阶段。\nChampion mastery data isn't available currently. Please make sure you're at the end of a matchmade game.")
                    else:
                        logPrint("未知错误。\nUnknown error.")
                else:
                    logPrint("本场对局的英雄成就数据如下：\nChampion mastery data of this game are as follows:")
                    eog_mastery_update_df = await sort_eog_champion_mastery_update(connection)
                    print(format_df(eog_mastery_update_df)[0])
                    log.write(format_df(eog_mastery_update_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "2":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                logPrint("请选择本场对局的类型：\nPlease select a type of this match:\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）")
                while True:
                    productType = logInput()
                    if productType == "":
                        continue
                    elif productType[0] == "0":
                        break
                    elif productType[0] == "1":
                        eog_stats_block = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
                        if isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block:
                            logPrint(eog_stats_block)
                            if eog_stats_block["httpStatus"] == 404 and eog_stats_block["message"] == "No end of game stats available.":
                                logPrint("当前游戏模式无法查看英雄联盟对局数据。\nThe current game mode doesn't provide LoL game stats.")
                            else:
                                logPrint("未知错误。\nUnknown error.")
                        else:
                            gameId = eog_stats_block["gameId"]
                            eog_stat_metaDf_lol = await sort_eog_stat_lol_metadata(connection)
                            eog_teamstat_df_lol = (await sort_eog_teamstat_lol_data(connection)).stack().unstack(0)
                            eog_playerstat_df_lol = await sort_eog_playerstat_lol_data(connection)
                            eog_playerstat_df_lol_fields_to_export = ["teamId", "team_color", "stats PLAYER_SUBTEAM", "stats playerSubteamColor", "isLocalPlayer", "summonerName", "riotIdGameName", "riotIdTagLine", "summonerId", "puuid", "profileIcon_title", "level", "botPlayer", "leaver", "leaves", "wins", "losses", "championName", "selectedPosition", "detectedTeamPosition", "stats LEVEL", "spell1_name", "spell2_name", "item0_name", "item1_name", "item2_name", "item3_name", "item4_name", "item5_name", "item6_name", "stats KDA", "stats PLAYER_AUGMENT_1 nameTRA", "stats PLAYER_AUGMENT_1 rarity", "stats PLAYER_AUGMENT_2 nameTRA", "stats PLAYER_AUGMENT_2 rarity", "stats PLAYER_AUGMENT_3 nameTRA", "stats PLAYER_AUGMENT_3 rarity", "stats PLAYER_AUGMENT_4 nameTRA", "stats PLAYER_AUGMENT_4 rarity", "stats PLAYER_AUGMENT_5 nameTRA", "stats PLAYER_AUGMENT_5 rarity", "stats PLAYER_AUGMENT_6 nameTRA", "stats PLAYER_AUGMENT_6 rarity", "stats CHAMPIONS_KILLED", "stats NUM_DEATHS", "stats ASSISTS", "stats LARGEST_KILLING_SPREE", "stats LARGEST_MULTI_KILL", "stats TOTAL_TIME_CROWD_CONTROL_DEALT", "stats TIME_CCING_OTHERS", "stats TOTAL_DAMAGE_DEALT_TO_CHAMPIONS", "stats PHYSICAL_DAMAGE_DEALT_TO_CHAMPIONS", "stats MAGIC_DAMAGE_DEALT_TO_CHAMPIONS", "stats TRUE_DAMAGE_DEALT_TO_CHAMPIONS", "stats TOTAL_DAMAGE_DEALT", "stats PHYSICAL_DAMAGE_DEALT_PLAYER", "stats MAGIC_DAMAGE_DEALT_PLAYER", "stats TRUE_DAMAGE_DEALT_PLAYER", "stats LARGEST_CRITICAL_STRIKE", "stats TOTAL_DAMAGE_DEALT_TO_BUILDINGS", "stats TOTAL_DAMAGE_DEALT_TO_OBJECTIVES", "stats TOTAL_DAMAGE_DEALT_TO_TURRETS", "stats TOTAL_HEAL", "stats TOTAL_HEAL_ON_TEAMMATES", "stats TOTAL_DAMAGE_SHIELDED_ON_TEAMMATES", "stats TOTAL_DAMAGE_TAKEN", "stats PHYSICAL_DAMAGE_TAKEN", "stats MAGIC_DAMAGE_TAKEN", "stats TRUE_DAMAGE_TAKEN", "stats TOTAL_DAMAGE_SELF_MITIGATED", "stats VISION_SCORE", "stats WARD_PLACED", "stats WARD_KILLED", "stats SIGHT_WARDS_BOUGHT_IN_GAME", "stats VISION_WARDS_BOUGHT_IN_GAME", "stats GOLD_EARNED", "stats MINIONS_KILLED", "stats NEUTRAL_MINIONS_KILLED", "stats NEUTRAL_MINIONS_KILLED_YOUR_JUNGLE", "stats NEUTRAL_MINIONS_KILLED_ENEMY_JUNGLE", "stats TURRETS_KILLED", "stats BARRACKS_KILLED", "stats TEAM_OBJECTIVE", "stats NODE_CAPTURE", "stats NODE_CAPTURE_ASSIST", "stats NODE_NEUTRALIZE", "stats NODE_NEUTRALIZE_ASSIST", "stats TOTAL_TIME_SPENT_DEAD", "stats PERK_PRIMARY_STYLE name", "stats PERK_SUB_STYLE name", "stats PERK0 name", "stats PERK0 EndOfGameStatDescs", "stats PERK1 name", "stats PERK1 EndOfGameStatDescs", "stats PERK2 name", "stats PERK2 EndOfGameStatDescs", "stats PERK3 name", "stats PERK3 EndOfGameStatDescs", "stats PERK4 name", "stats PERK4 EndOfGameStatDescs", "stats PERK5 name", "stats PERK5 EndOfGameStatDescs", "stats SPELL1_CAST", "stats SPELL2_CAST", "stats WAS_AFK", "stats TEAM_EARLY_SURRENDERED", "stats GAME_ENDED_IN_EARLY_SURRENDER", "stats GAME_ENDED_IN_SURRENDER", "stats WIN", "stats LOSE", "stats PLAYER_SUBTEAM_PLACEMENT", "stats VICTORY_POINT_TOTAL"]
                            eog_playerstat_df_lol_export = eog_playerstat_df_lol.loc[:, eog_playerstat_df_lol_fields_to_export].stack().unstack(0)
                            excel_name = "EndOfGame Stats of %s-%d.xlsx" %(platformId, gameId)
                            while True:
                                try:
                                    with pandas.ExcelWriter(path = excel_name) as writer:
                                        eog_stat_metaDf_lol.to_excel(excel_writer = writer, sheet_name = "Metadata")
                                        eog_teamstat_df_lol.to_excel(excel_writer = writer, sheet_name = "Team Stats")
                                        eog_playerstat_df_lol_export.to_excel(excel_writer = writer, sheet_name = "Player Stats")
                                except PermissionError:
                                    logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                                    logInput()
                                else:
                                    break
                            logPrint(f'本场对局结算数据已导出到同目录下的“{excel_name}”中。\nEnd-of-game stats of this match have been exported into {excel_name} under the same folder.')
                            break
                    elif productType[0] == "2":
                        tft_eog_stats = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
                        if isinstance(tft_eog_stats, dict) and "errorCode" in tft_eog_stats:
                            logPrint(tft_eog_stats)
                            if tft_eog_stats["httpStatus"] == 404 and tft_eog_stats["message"] == "Game Client stats not found":
                                logPrint("当前游戏模式无法查看云顶之弈对局数据。\nThe current game mode doesn't provide TFT game stats.")
                            else:
                                logPrint("未知错误。\nUnknown error.")
                        else:
                            gameId = tft_eog_stats["gameId"]
                            eog_stat_metaDf_tft = await sort_eog_stat_tft_metadata(connection)
                            eog_stat_df_tft = await sort_eog_stat_tft_data(connection)
                            eog_stat_df_tft_fields_to_export = ["isLocalPlayer", "summonerName", "riotIdGameName", "riotIdTagLine", "summonerId", "puuid", "icon title", "setCoreName", "isInteractable", "partnerGroupId", "companion speciesName", "companion colorName", "health", "rank", "playbook name", "customAugmentContainer description", "customAugmentContainer displayName", "augment1 name", "augment2 name", "augment3 name", "unit0 name", "unit0 price", "unit0 level", "unit0 traits", "unit0 item0 name", "unit0 item1 name", "unit0 item2 name", "unit1 name", "unit1 price", "unit1 level", "unit1 traits", "unit1 item0 name", "unit1 item1 name", "unit1 item2 name", "unit2 name", "unit2 price", "unit2 level", "unit2 traits", "unit2 item0 name", "unit2 item1 name", "unit2 item2 name", "unit3 name", "unit3 price", "unit3 level", "unit3 traits", "unit3 item0 name", "unit3 item1 name", "unit3 item2 name", "unit4 name", "unit4 price", "unit4 level", "unit4 traits", "unit4 item0 name", "unit4 item1 name", "unit4 item2 name", "unit5 name", "unit5 price", "unit5 level", "unit5 traits", "unit5 item0 name", "unit5 item1 name", "unit5 item2 name", "unit6 name", "unit6 price", "unit6 level", "unit6 traits", "unit6 item0 name", "unit6 item1 name", "unit6 item2 name", "unit7 name", "unit7 price", "unit7 level", "unit7 traits", "unit7 item0 name", "unit7 item1 name", "unit7 item2 name", "unit8 name", "unit8 price", "unit8 level", "unit8 traits", "unit8 item0 name", "unit8 item1 name", "unit8 item2 name", "unit9 name", "unit9 price", "unit9 level", "unit9 traits", "unit9 item0 name", "unit9 item1 name", "unit9 item2 name", "unit10 name", "unit10 price", "unit10 level", "unit10 traits", "unit10 item0 name", "unit10 item1 name", "unit10 item2 name"]
                            eog_stat_df_tft_export = eog_stat_df_tft.loc[:, eog_stat_df_tft_fields_to_export].stack().unstack(0)
                            excel_name = "EndOfGame Stats of %s-%d.xlsx" %(platformId, gameId)
                            while True:
                                try:
                                    with pandas.ExcelWriter(path = excel_name) as writer:
                                        eog_stat_metaDf_tft.to_excel(excel_writer = writer, sheet_name = "Metadata")
                                        eog_stat_df_tft_export.to_excel(excel_writer = writer, sheet_name = "Player Stats")
                                except PermissionError:
                                    logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                                    logInput()
                                else:
                                    break
                            logPrint(f'本场对局结算数据已导出到同目录下的“{excel_name}”中。\nEnd-of-game stats of this match have been exported into {excel_name} under the same folder.')
                            break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "3":
            await chat(connection)
        elif option[0] == "4":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                response = await (await connection.request("POST", "/lol-lobby/v2/play-again")).json()
                logPrint(response)
                if isinstance(response, dict) and "errorCode" in response:
                    if response["httpStatus"] == 400 and "Unable to create lobby: couldn't find controller for queue type" in response["message"]:
                        logPrint("当前模式不支持该选项。请切换游戏模式，并确保不是在观战。\nThe current game mode doesn't support this option. Please change another game mode and make sure you're not spectating.")
                    elif response["httpStatus"] == 400 and "Play-again is currently unavailable.":
                        logPrint("再来一局目前不可用。\nPlay-again is currently unavailable.")
                    else:
                        logPrint("未知错误。\nUnknown error.")
                else:
                    time.sleep(GLOBAL_RESPONSE_LAG)
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase in ["None", "Lobby"]:
                        logPrint("已成功发送请求。\nRequest success.")
                    else:
                        logPrint("服务器接收到了再来一局的请求，但您的状态似乎发生了异常。\nThe server received your play-again request, but it seems that an error has occurred to your gameflow phase.")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "5":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                response = await (await connection.request("POST", "/lol-end-of-game/v1/state/dismiss-stats")).json() #这个接口比下面注释起来的接口更有效一些（This endpoint is more effective than the following commented one）
                # response = await (await connection.request("POST", "/lol-lobby/v2/play-again-decline")).json()
                logPrint(response)
                if isinstance(response, dict) and "errorCode" in response:
                    # if response["httpStatus"] == 400 and "Play-again is currently unavailable.":
                    #     logPrint("返回大厅目前不可用。\nPlay-again-decline is currently unavailable.")
                    logPrint("未知错误。\nUnknown error.")
                else:
                    time.sleep(GLOBAL_RESPONSE_LAG)
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "None":
                        logPrint("已成功发送请求。\nRequest success.")
                    else:
                        logPrint("服务器接收到了返回大厅的请求，但您的状态似乎发生了异常。\nThe server received your dismiss-stats request, but it seems that an error has occurred to your gameflow phase.")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "6":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                honor_ballot = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
                if isinstance(honor_ballot, dict) and "errorCode" in honor_ballot:
                    logPrint(honor_ballot)
                    logPrint("荣誉投票信息获取异常。\nAn error occurred when getting the honor ballot information.")
                else:
                    eligiblePlayers = honor_ballot["eligibleAllies"] + honor_ballot["eligibleOpponents"]
                    if len(eligiblePlayers) == 0:
                        logPrint("目前没有玩家可以赞誉，因此您无法唤起荣誉投票阶段。\nThere's not any player eligible to honor, so you can't recall the honor ballot vote phase.")
                    else:
                        player_summonerId = eligiblePlayers[0]["summonerId"]
                        player_puuid = eligiblePlayers[0]["puuid"]
                        honorType = "HEART" #取值（Available values）：COOL、SHOTCALLER、HEART
                        gameId = honor_ballot["gameId"]
                        body = {"summonerId": player_summonerId, "puuid": player_puuid, "honorType": honorType, "gameId": gameId}
                        logPrint(body)
                        response = await (await connection.request("POST", "/lol-honor-v2/v1/honor-player", data = body)).json()
                        logPrint(response)
                        if isinstance(response, dict) and "errorCode" in response:
                            logPrint("赞誉失败。\nHonor failed.")
                        elif response == "failed_to_contact_honor_server":
                            logPrint("无法连接到赞誉服务器。请在客户端内手动点击一名玩家以赞誉之。\nFailed to contact honor server. Please manually click on a player to honor it.")
                        else:
                            time.sleep(GLOBAL_RESPONSE_LAG)
                            honor_ballot = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
                            if player_puuid in list(map(lambda x: x["recipientPuuid"], honor_ballot["honoredPlayers"])):
                                logPrint("赞誉成功。\nHonor succeeded.")
                            else:
                                logPrint("赞誉失败。\nHonor failed.")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "7":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    global collection_df_refresh, skins_df_refresh
    print("声明：该脚本只作为辅助客户端的工具。您也许在客户端无法正常响应时可以使用该脚本。\nDeclaration: This program is only regarded as an auxillary tool. It may be useful when the League Client doesn't respond as expected.")
    await define_global_variables(connection)
    data_resources_prepared = False
    exit_program = False
    gameflow_debug_enabled = False
    while True:
        client_ready = await check_account_ready(connection)
        if client_ready:
            if not data_resources_prepared:
                logPrint("正在准备数据资源……\nPreparing data resources ...")
                await prepare_data_resources(connection)
                data_resources_prepared = True
            if gameflow_debug_enabled:
                gameflow_phase = ALL_GAMEFLOW_PHASES[gameflow_phase_index]
                logPrint(f"正在调试的游戏状态（Debugging gameflow phase）：{gameflow_phase}")
            else:
                gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "None":
                await gameflow_phase_transition(connection)
            elif gameflow_phase == "Lobby":
                logPrint("检测到您在房间内。\nDetected you're currently in a party/lobby.")
                await lobby_simulation(connection)
            elif gameflow_phase == "Matchmaking":
                logPrint("您正在寻找对局。\nYou're searching for a match.")
                await inQueue_simulation(connection)
            elif gameflow_phase == "ReadyCheck":
                logPrint("对局已找到。\nA match has been found.")
                await readyCheck_simulation(connection)
            elif gameflow_phase == "ChampSelect":
                logPrint("您正处于英雄选择阶段。\nYou're during a champ select stage.")
                await champ_select_simulation(connection)
            elif gameflow_phase == "InProgress":
                logPrint("您正在游戏中。\nYou're currently in a game.")
                await inGame_simulation(connection)
            elif gameflow_phase == "WaitingForStats":
                logPrint('''正在等待赛后数据。输入开头不是“0”的字符串以跳过等待，直接开始下一局游戏。\nWaiting for the game stats. Submit any string that doesn't start with "0" to skip waiting for stats.''')
                while True:
                    gameflow_phase = gameflow_phase_debug if gameflow_debug_enabled else await get_gameflow_phase(connection)
                    if gameflow_phase == "WaitingForStats":
                        skip = logInput()
                        if skip == "":
                            continue
                        elif skip[0] == "0":
                            break
                        else:
                            response = await (await connection.request("POST", "/lol-end-of-game/v1/state/dismiss-stats")).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint("跳过等待失败。\nFailed to skip waiting.")
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "None":
                                    logPrint("已跳过赛后数据加载。\nYou skipped loading the postgame stats.")
                                    break
                                else:
                                    logPrint("跳过等待失败。\nFailed to skip waiting.")
            elif gameflow_phase == "PreEndOfGame":
                logPrint("赞誉一名队友。\nHonor a player.")
                await preEndOfGame_simulation(connection)
            elif gameflow_phase == "EndOfGame":
                await endOfGame_simulation(connection)
            elif gameflow_phase == "Reconnect":
                logPrint("检测到您中途退出游戏。输入任意非空字符串以重连，否则不重连。\nThe program detected you're out of game now. Submit any non-empty string to reconnect, or null to refuse reconnecting.")
                reconnect_str = logInput()
                reconnect = bool(reconnect_str)
                if reconnect:
                    response = await (await connection.request("POST", "/lol-gameflow/v1/reconnect")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        if response["message"] == "Reconnect is not available.":
                            logPrint("重连不可用。\nReconnect isn't available.")
                        else:
                            logPrint("重连失败。\nReconnect failed.")
                    else:
                        time.sleep(GLOBAL_RESPONSE_LAG)
                        gameflow_phase = await get_gameflow_phase(connection)
                        if gameflow_phase == "InProgress":
                            logPrint("您已经重新连接。\nYou reconnected to the game.")
                        else:
                            logPrint("重连失败。\nReconnect failed.")
                else:
                    await inGame_simulation(connection)
            else: #gameflow_phase in {"TerminatedInError", "FailedToLaunch", "GameStart", "CheckedIntoTournament"}
                logPrint(f"当前游戏状态（Current gameflow phase）：{gameflow_phase}")
                pass
        else:
            logPrint("您的客户端未加载完成。您将只能使用以下操作。\nYour client hasn't been completely loaded. You'll only be allowed to use the following functions.")
            await unlogged_actions(connection)
        gameflow_debug_enabled = False
        logPrint('按回车键以继续，输入开头是“0”的字符串以退出程序，或者输入任意其它非空字符串以更新数据资源。\nPress Enter to continue, submit any string that starts with "0" to exit the program, or submit any other non-empty string to reload data resources.')
        exit_program_str = logInput()
        exit_program = exit_program_str != "" and exit_program_str[0] == "0"
        if exit_program_str != "" and exit_program_str[0] != "0":
            if exit_program_str.lower() in list(map(lambda x: x.lower(), ALL_GAMEFLOW_PHASES)):
                data_resources_prepared = True
                gameflow_phase_index = list(map(lambda x: x.lower(), ALL_GAMEFLOW_PHASES)).index(exit_program_str.lower())
                gameflow_phase_debug = ALL_GAMEFLOW_PHASES[gameflow_phase_index]
                gameflow_debug_enabled = True
            else:
                data_resources_prepared = False
                collection_df_refresh = skins_df_refresh = True
        if exit_program:
            break
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
