from lcu_driver import Connector
from lcu_driver.connection import Connection
import json, os, pandas, requests, time, traceback, uuid
from urllib.parse import urljoin
from typing import Any, Optional
from src.utils.logger import LogManager, aInput
from src.utils.summoner import print_summoner_info, get_info, get_info_name
from src.utils.format import getISOTime, optimize_bool_display, format_df, addDefaultStyle
from src.utils.patch import Patch
from src.utils.runtimeDebug import subscope
from src.utils.webRequest import requestUrl, SGPSession
from src.core.config.localization import availabilities, challengeCrystalLevels, tiers, rarities, spectatorPolicies, titleAcquisitionTypes, krarities, conversationTypes, messageTypes
from src.core.config.headers import friend_hovercard_header, friend_group_header, conversation_header, message_header, friend_request_header, party_header, invid_header, champSelect_mutedPlayer_header, captureDevice_header, voiceSettings_header, participant_record_header, spectate_nonfriend_header, blockList_header, TFTGame_summary_header
from src.core.config.servers import set_summonerInfo_folder, save_platform_info
from src.core.config.const import BOT_UUID
from src.core.dataframes.matchHistory import get_LoLHistory, get_matchSummary_sgp, sort_LoLGame_stats, sort_LoLGame_stats_sgp, generate_TFTGameInfo_records, sort_TFTGame_stats
from src.core.dataframes.gameflow import sort_ChampSelect_players

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN & AwesomeABC
# 更新（Last update）：     2026/03/10
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

session: requests.Session = requests.Session()
sgpSession: SGPSession = SGPSession()
regaliaBanners: dict[str, dict[str, Any]] = {}
challenges: dict[str, dict[str, dict[str, Any]]] = {}
queues: dict[int, dict[str, Any]] = {}
gameQueues: dict[int, dict[str, Any]] = {}
summonerIcons: dict[int, dict[str, Any]] = {}
LoLChampions: dict[int, dict[str, Any]] = {}
titles: dict[str, Any] = {}
wardSkins: dict[int, dict[str, Any]] = {}
championSkins: dict[int, dict[str, Any]] = {}
spells: dict[int, dict[str, Any]] = {}
LoLItems: dict[int, dict[str, Any]] = {}
perks: dict[int, dict[str, Any]] = {}
perkstyles: dict[int, dict[str, Any]] = {}
CherryAugments: dict[int, dict[str, Any]] = {}
TFTBasic_got: bool = False
TFTAugments: dict[str, dict[str, Any]] = {}
TFTCompanions: dict[str, dict[str, Any]] = {}
TFTCompanions_itemIdMap: dict[str, dict[str, Any]] = {}
TFTTraits: dict[str, Any] = {}
TFTChampions: dict[str, dict[str, Any]] = {}
TFTItems: dict[str, dict[str, Any]] = {}
TFTDamageSkins: dict[str, dict[str, Any]] = {}
TFTMapSkins: dict[str, dict[str, Any]] = {}
folder: str = ""
current_info: dict[str, Any] = {}
platformId: str = ""
message_hint_printed: bool = False
spectatorPluginNA_hint_printed: bool = False
spectatorPluginLegacyDisabled_hint_printed: bool = False
log: LogManager = LogManager()

connector = Connector()

#-----------------------------------------------------------------------------
# 好友管理（Friend management）
#-----------------------------------------------------------------------------
async def prepare_data_resources(connection: Connection) -> None:
    logPrint("正在加载数据资源……\nLoading data resources ...")
    global platformId, regaliaBanners, challenges, queues, gameQueues, summonerIcons, LoLChampions, titles, wardSkins, championSkins, spells, LoLItems, perks, perkstyles, CherryAugments, TFTCompanions, TFTCompanions_itemIdMap, TFTTraits, TFTChampions, TFTItems, TFTDamageSkins, TFTMapSkins
    ##大区信息（Platform information）
    platformId = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    ##旗帜（Regalia banner）
    regaliaBanners = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_BANNER")).json()
    ##成就（Challenge）
    challenges = await (await connection.request("GET", "/lol-game-data/assets/v1/challenges.json")).json()
    ##游戏队列（Game queue）
    queues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/queues.json")).json()
    queues = {int(queue_iter["id"]): queue_iter for queue_iter in queues_source}
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues = {queue["id"]: queue for queue in gameQueues_source}
    ##召唤师图标（Summoner icon）
    summonerIcons_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcons_source}
    ##英雄（LoL champion）
    LoLChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/champion-summary.json")).json()
    LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampions_source}
    ##头衔（Title）
    titles = await (await connection.request("GET", "/lol-challenges/v2/titles/all")).json()
    ##饰品（Ward skin）
    wardSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    wardSkins = {wardSkin_iter["id"]: wardSkin_iter for wardSkin_iter in wardSkins_source}
    ##皮肤（Champion skin）
    championSkins_source: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
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
    ##召唤师技能（Summoner spell）
    spells_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
    spells = {int(spell_iter["id"]): spell_iter for spell_iter in spells_source}
    ##英雄联盟装备（LoL item）
    LoLItems_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/items.json")).json()
    LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItems_source}
    ##符文（Perk）
    perks_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/perks.json")).json()
    perks = {int(perk_iter["id"]): perk_iter for perk_iter in perks_source}
    ##符文系（Perkstyle）
    perkstyles_source: dict[str, Any] = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
    perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyles_source["styles"]}
    ##斗魂竞技场强化符文（Arena augment）
    CherryAugments_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/cherry-augments.json")).json()
    CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugments_source}
    ##云顶之弈小小英雄（TFT companion）
    TFTCompanions_source: dict[str, Any] = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
    TFTCompanions = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanions_source}
    TFTCompanions_itemIdMap = {companion_iter["itemId"]: companion_iter for companion_iter in TFTCompanions_source}
    ##云顶之弈羁绊（TFT Trait）
    TFTTraits_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tfttraits.json")).json()
    TFTTraits = {}
    for trait in TFTTraits_source:
        trait_id = trait["trait_id"]
        conditional_trait_sets: dict[str, Any] = {}
        if "conditional_trait_sets" in trait: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
            for conditional_trait_set in trait["conditional_trait_sets"]:
                style_idx: str = conditional_trait_set["style_idx"]
                conditional_trait_sets[style_idx] = conditional_trait_set
        trait["conditional_trait_sets"] = conditional_trait_sets
        TFTTraits[trait_id] = trait
    ##云顶之弈英雄（TFT champion）
    TFTChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftchampions.json")).json()
    TFTChampions = {TFTChampion_iter["name"]: TFTChampion_iter for TFTChampion_iter in TFTChampions_source}
    ##云顶之弈装备（TFT items）
    TFTItems_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftitems.json")).json()
    TFTItems = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItems_source}
    ##云顶之弈攻击特效（Damage skin）
    TFTDamageSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftdamageskins.json")).json()
    TFTDamageSkins = {TFTDamageSkin_iter["itemId"]: TFTDamageSkin_iter for TFTDamageSkin_iter in TFTDamageSkins_source}
    ##云顶之弈棋盘皮肤（TFT map skin）
    TFTMapSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftmapskins.json")).json()
    TFTMapSkins = {TFTMapSkin_iter["itemId"]: TFTMapSkin_iter for TFTMapSkin_iter in TFTMapSkins_source}

#定义整理过程（Define data organization processes）
async def sort_friend_hovercard(connection: Connection) -> pandas.DataFrame:
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    friend_groups: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
    friend_group_priority: dict[int, int] = {group["id"]: group["priority"] for group in friend_groups}
    #定义好友数据结构（Define the friend hovercard data structure）
    friend_hovercard_header_keys: list[str] = list(friend_hovercard_header.keys())
    friend_hovercard_data: dict[str, list[Any]] = {key: [] for key in friend_hovercard_header_keys}
    #数据整理核心部分（Data assignment - core part）
    for friend in friends:
        for i in range(len(friend_hovercard_header_keys)):
            key: str = friend_hovercard_header_keys[i]
            if i <= 29:
                if i == 0: #可用性（`availability`）
                    to_append: Any = availabilities[friend[key]]
                elif i == 25: #分组优先级（`groupPriority`）
                    to_append = friend_group_priority[friend["groupId"]]
                elif i == 26 or i == 27: #非直接导入的召唤师图标相关键（Not directly imported `icon`-related keys）
                    to_append = summonerIcons[friend["icon"]].get(key.split(" ")[1], "") if friend["icon"] in summonerIcons else ""
                elif i == 28: #上次离线时间（`lastSeenOnlineTime`）
                    if friend["lastSeenOnlineTimestamp"] == None:
                        to_append = ""
                    else:
                        to_append = friend["lastSeenOnlineTimestamp"]
                elif i == 29: #登录时间（`loginTime`）
                    to_append = getISOTime(friend["time"] / 1000) if friend["time"] == 0 else ""
                else:
                    to_append = friend[key]
            elif i <= 32:
                to_append = friend["discordInfo"][key.split()[1]] if bool(friend["discordInfo"]) else ""
            elif i <= 108:
                if friend["lol"] == {}:
                    to_append = ""
                else:
                    lol: dict[str, Any] = friend["lol"]
                    if i in {33, 35, 37, 38, 39, 40, 46, 47, 48, 49, 51, 52, 56, 59, 60, 61, 64}: #正整数被转化为字符串的值的键（Keys whose values are originally integers but transformed into strings）
                        to_append = "" if not key in lol or lol[key] == "" else int(lol[key])
                    elif i == 34: #成就等级（`challengeCrystalLevel`）
                        to_append = "" if not key in lol else challengeCrystalLevels[lol[key]]
                    elif i == 36: #选用勋章序号（`challengeTokensSelected`）
                        to_append = "" if not key in lol else json.loads("[%s]" %(lol[key]))
                    elif i == 43: #游戏状态（`gameStatus`）
                        to_append = "" if not key in lol else availabilities[lol[key]]
                    elif i == 45: #可观战范围（`isObservable`）
                        to_append = "" if not key in lol else spectatorPolicies[lol[key]]
                    elif i == 53 or i == 57: #段位分级相关键（Division-related keys）
                        to_append = "" if not key in lol or lol[key] == "NA" else lol[key]
                    elif i == 55 or i == 58: #段位相关键（Tier-related keys）
                        to_append = "" if not key in lol else tiers[lol[key]]
                    elif i == 65 or i == 66: #旗帜相关键（Banner-related keys）
                        if "bannerIdSelected" in lol and lol["bannerIdSelected"] != "":
                            regaliaBanner_item: dict[str, Any] = regaliaBanners[lol["bannerIdSelected"]]["items"][0]
                            to_append = regaliaBanner_item[key.split()[1]]
                        else:
                            to_append = ""
                    elif i == 67: #选用勋章名称（`challengeTokenNamesSelected`）
                        if "challengeTokensSelected" in lol and lol["challengeTokensSelected"] != "":
                            challengeTokensSelected: list[str] = lol["challengeTokensSelected"].split(",")
                            to_append = list(map(lambda x: challenges["challenges"][x]["name"], challengeTokensSelected))
                        else:
                            to_append = ""
                    elif i >= 68 and i <= 70: #英雄相关键（Champion-related keys）
                        if "championId" in lol:
                            if lol["championId"] == "":
                                to_append = ""
                            else:
                                championId: int = int(lol["championId"])
                                if i == 70:
                                    iconPath: str = LoLChampions[championId][key.split()[1]]
                                    to_append = "" if iconPath == "" else urljoin(connection.address, iconPath)
                                else:
                                    to_append = LoLChampions[championId][key.split()[1]]
                        else:
                            to_append = ""
                    elif i >= 71 and i <= 78: #小小英雄相关键（Companion-related keys）
                        if "companionId" in lol:
                            if lol["companionId"] == "":
                                to_append = ""
                            else:
                                companionId = int(lol["companionId"])
                                if i == 73:
                                    iconPath = TFTCompanions_itemIdMap[companionId][key.split()[1]]
                                    to_append = "" if iconPath == "" else urljoin(connection.address, iconPath)
                                elif i == 77:
                                    to_append = rarities[TFTCompanions_itemIdMap[companionId][key.split()[1]]]
                                else:
                                    to_append = TFTCompanions_itemIdMap[companionId][key.split()[1]]
                        else:
                            to_append = ""
                    elif i >= 79 and i <= 86: #云顶之弈攻击特效相关键（TFT damage skin-related keys）
                        if "damageSkinId" in lol:
                            if lol["damageSkinId"] == "":
                                to_append = ""
                            else:
                                damageSkinId: str = int(lol["damageSkinId"])
                                if i == 81:
                                    iconPath = TFTDamageSkins[damageSkinId][key.split()[1]]
                                    to_append = "" if iconPath == "" else urljoin(connection.address, iconPath)
                                if i == 84:
                                    to_append = rarities[TFTDamageSkins[damageSkinId][key.split()[1]]]
                                else:
                                    to_append = TFTDamageSkins[damageSkinId][key.split()[1]]
                        else:
                            to_append = ""
                    elif i == 87: #游戏模式名称（`gameModeName`）
                        if "queueId" in lol and lol["queueId"] != "":
                            queueId: int = int(lol["queueId"])
                            to_append = "自定义" if queueId == -1 or queueId == 0 else gameQueues[queueId]["name"]
                        else:
                            to_append = ""
                    elif i >= 88 and i <= 94: #棋盘皮肤相关键（TFT map skin-related keys）
                        if "mapSkinId" in lol:
                            if lol["mapSkinId"] == "":
                                to_append = ""
                            else:
                                mapSkinId: int = int(lol["mapSkinId"])
                                if i == 90:
                                    iconPath = TFTMapSkins[mapSkinId][key.split()[1]]
                                    to_append = "" if iconPath == "" else urljoin(connection.address, iconPath)
                                if i == 93:
                                    to_append = rarities[TFTMapSkins[mapSkinId][key.split()[1]]]
                                else:
                                    to_append = TFTMapSkins[mapSkinId][key.split()[1]]
                        else:
                            to_append = ""
                    elif i >= 95 and i <= 98: #头衔相关键（Title-related keys）
                        if "playerTitleSelected" in lol:
                            title_contentId: str = lol["playerTitleSelected"]
                            if title_contentId == "":
                                to_append = ""
                            else:
                                if i == 97:
                                    to_append = titleAcquisitionTypes[titles[title_contentId][key.split()[1]]]
                                else:
                                    to_append = titles[title_contentId][key.split()[1]]
                        else:
                            to_append = ""
                    elif i >= 99 and i <= 108: #选用皮肤相关键（`skinVariant`-related keys）
                        if "skinVariant" in lol:
                            if lol["skinVariant"] == "":
                                to_append = ""
                            else:
                                skinId: int = int(lol["skinVariant"])
                                if not key.split()[1] in championSkins[skinId]:
                                    to_append = ""
                                else:
                                    if i >= 101 and i <= 105 or i == 107 or i == 108:
                                        iconPath = championSkins[skinId][key.split()[1]]
                                        to_append = "" if iconPath == "" else urljoin(connection.address, iconPath)
                                    elif i == 106:
                                        to_append = krarities[championSkins[skinId][key.split()[1]]]
                                    else:
                                        to_append = championSkins[skinId][key.split()[1]]
                        else:
                            to_append = ""
                    else:
                        to_append = lol.get(key, "")
            elif i <= 113:
                if friend["lol"] != {} and "pty" in friend and friend["pty"] != "":
                    party: dict[str, Any] = json.loads(friend["lol"]["pty"])
                    if i == 113: #小队召唤师名（`pty summonerNames`）
                        summonerIds: list[int] = party["summoners"]
                        summonerNames: list[Any] = []
                        for summonerId in summonerIds:
                            member_info_recapture: int = 0
                            member_info: dict[str, Any] = await get_info(connection, summonerId)
                            while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                                logPrint(member_info["message"])
                                member_info_recapture += 1
                                logPrint("成员信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an member (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(summonerId, member_info_recapture, summonerId, member_info_recapture))
                                member_info = await get_info(connection, summonerId)
                            if member_info_recapture >= 3:
                                logPrint(member_info["message"])
                                logPrint("成员信息（召唤师序号：%d）获取失败！将忽略该成员。\nInformation of a member (summonerId: %d) capture failed! The program will ignore this member.")
                                summonerNames.append(summonerId)
                                continue
                            summonerNames.append(get_info_name(member_info["body"]))
                        to_append = summonerNames
                    else:
                        to_append = party[key.split()[1]]
                else:
                    to_append = ""
            else:
                if friend["lol"] != {} and friend["lol"]["regalia"] != "":
                    regalia: dict[str, Any] = json.loads(friend["lol"]["regalia"])
                    to_append = regalia[key.split()[1]]
                else:
                    to_append = ""
            friend_hovercard_data[key].append(to_append)
    #数据框列序整理（Dataframe column ordering）
    friend_hovercard_statistics_output_order: list[int] = [13, 5, 6, 23, 20, 16, 7, 8, 25, 26, 0, 11, 21, 14, 28, 29, 30, 1, 2, 32, 31, 47, 54, 55, 53, 60, 56, 58, 57, 59, 66, 34, 35, 46, 95, 96, 97, 98, 67, 43, 111, 113, 110, 41, 42, 52, 87, 48, 40, 68, 69, 100, 106, 72, 74, 75, 77, 80, 86, 83, 84, 89, 92, 93, 45, 63]
    friend_hovercard_data_organized: dict[str, list[Any]] = {friend_hovercard_header_keys[i]: friend_hovercard_data[friend_hovercard_header_keys[i]] for i in friend_hovercard_statistics_output_order}
    friend_hovercard_df: pandas.DataFrame = pandas.DataFrame(data = friend_hovercard_data_organized)
    optimize_bool_display(friend_hovercard_df)
    friend_hovercard_df = pandas.concat([pandas.DataFrame([friend_hovercard_header])[friend_hovercard_df.columns], friend_hovercard_df], ignore_index = True)
    return friend_hovercard_df

async def sort_friend_hovercard_simple(connection: Connection) -> pandas.DataFrame:
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    #定义好友数据结构（Define the friend hovercard data structure）
    friend_hovercard_header_simple: dict[str, str] = {"availability": "可用性", "gameName": "玩家名称", "gameTag": "名称编号", "groupId": "分组序号", "groupName": "分组名称", "name": "显示名", "note": "备注", "pid": "社交代码", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号"}
    friend_hovercard_header_keys_simple: list[str] = list(friend_hovercard_header_simple.keys())
    friend_hovercard_data_simple: dict[str, list[Any]] = {key: [] for key in friend_hovercard_header_keys_simple}
    #数据整理核心部分（Data assignment - core part）
    for friend in friends:
        for i in range(len(friend_hovercard_header_keys_simple)):
            key: str = friend_hovercard_header_keys_simple[i]
            if i == 0:
                to_append: Any = availabilities[friend[key]]
            else:
                to_append = friend[key]
            friend_hovercard_data_simple[key].append(to_append)
    #数据框列序整理（Dataframe column ordering）
    friend_hovercard_statistics_output_order_simple: list[int] = [5, 1, 2, 9, 8, 7, 3, 4, 0, 6]
    friend_hovercard_data_organized_simple: dict[str, list[Any]] = {friend_hovercard_header_keys_simple[i]: friend_hovercard_data_simple[friend_hovercard_header_keys_simple[i]] for i in friend_hovercard_statistics_output_order_simple}
    friend_hovercard_df_simple: pandas.DataFrame = pandas.DataFrame(data = friend_hovercard_data_organized_simple)
    friend_hovercard_df_simple = pandas.concat([pandas.DataFrame([friend_hovercard_header_simple])[friend_hovercard_df_simple.columns], friend_hovercard_df_simple], ignore_index = True)
    return friend_hovercard_df_simple

async def sort_friend_group(connection: Connection) -> pandas.DataFrame:
    friend_groups: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
    if isinstance(friend_groups, list) and all(map(lambda x: isinstance(x, dict), friend_groups)) and all(i in group for i in ["collapsed", "id", "isLocalized", "isMetaGroup", "name", "priority"] for group in friend_groups):
        friend_group_header_keys: list[str] = list(friend_group_header.keys())
        friend_group_data: dict[str, list[Any]] = {key: [] for key in friend_group_header_keys}
        for group in friend_groups:
            for i in range(len(friend_group_header_keys)):
                key: str = friend_group_header_keys[i]
                to_append: Any = group[key]
                friend_group_data[key].append(to_append)
        friend_group_statistics_output_order: list[int] = [1, 4, 5, 0]
        friend_group_data_organized: dict[str, list[Any]] = {friend_group_header_keys[i]: friend_group_data[friend_group_header_keys[i]] for i in friend_group_statistics_output_order}
        friend_group_df: pandas.DataFrame = pandas.DataFrame(data = friend_group_data_organized)
        optimize_bool_display(friend_group_df)
        friend_group_df = pandas.concat([pandas.DataFrame([friend_group_header])[friend_group_df.columns], friend_group_df], ignore_index = True)
    elif isinstance(friend_groups, dict) and all(i in friend_groups for i in ["errorCode", "httpStatus", "implementationDetails", "message"]):
        friend_group_df = pandas.DataFrame(data = friend_group_header, index = [0])
    else:
        logPrint("好友分组数据格式错误！函数只生成空表。\nFriend group data format ERROR! The function will only return an empty table.")
        friend_group_df = pandas.DataFrame(data = friend_group_header, index = [0])
    return friend_group_df

async def sort_conversation_metadata(connection: Connection) -> pandas.DataFrame:
    conversations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
    conversation_header_keys: list[str] = list(conversation_header.keys())
    conversation_metadata: dict[str, list[Any]] = {key: [] for key in conversation_header_keys}
    for conversation in conversations:
        for i in range(len(conversation_header_keys)):
            key: str = conversation_header_keys[i]
            if i == 9:
                to_append: Any = conversationTypes[conversation[key]]
            else:
                to_append = conversation[key]
            conversation_metadata[key].append(to_append)
    conversation_statistics_output_order: list[int] = [9, 0, 1, 2]
    conversation_metadata_organized: dict[str, list[Any]] = {conversation_header_keys[i]: conversation_metadata[conversation_header_keys[i]] for i in conversation_statistics_output_order}
    conversation_df: pandas.DataFrame = pandas.DataFrame(data = conversation_metadata_organized)
    conversation_df = pandas.concat([pandas.DataFrame([conversation_header])[conversation_df.columns], conversation_df], ignore_index = True)
    return conversation_df

async def sort_message_data(connection: Connection, messages: Any) -> pandas.DataFrame:
    if isinstance(messages, list) and all(map(lambda x: isinstance(x, dict), messages)) and all(i in message for i in ["body", "fromId", "fromObfuscatedPuuid", "fromObfuscatedSummonerId", "fromPid", "fromPuuid", "fromSummonerId", "id", "isHistorical", "timestamp", "type"] for message in messages):
        message_header_keys: list[str] = list(message_header.keys())
        message_data: dict[str, list[Any]] = {key: [] for key in message_header_keys}
        for message in messages:
            for i in range(len(message_header_keys)):
                key: str = message_header_keys[i]
                if i == 9: #时间戳（`timestamp`）
                    to_append: Any = message[key][:10] + " " + message[key][11:23]
                elif i == 10: #消息类型（`type`）
                    to_append = messageTypes.get(message[key], message[key])
                elif i == 11: #发送人召唤师名（`fromSummonerName`）
                    fromInfo: dict[str, Any] = await get_info(connection, message["fromPuuid"])
                    to_append = get_info_name(fromInfo["body"])
                else:
                    to_append = message[key]
                message_data[key].append(to_append)
        message_statistics_output_order: list[int] = [7, 9, 11, 10, 0, 6, 3, 4, 1, 5, 2, 8]
        message_data_organized: dict[str, list[Any]] = {message_header_keys[i]: message_data[message_header_keys[i]] for i in message_statistics_output_order}
        message_df: pandas.DataFrame = pandas.DataFrame(data = message_data_organized)
        optimize_bool_display(message_df)
        message_df = pandas.concat([pandas.DataFrame([message_header])[message_df.columns], message_df], ignore_index = True)
    elif isinstance(messages, dict) and all(i in messages for i in ["errorCode", "httpStatus", "implementationDetails", "message"]):
        message_df = pandas.DataFrame(message_header, index = [0])
    else:
        logPrint("消息数据格式错误！函数只生成空表。\nMessage data format ERROR! The function will only return an empty table.")
        message_df = pandas.DataFrame(message_header, index = [0])
    return message_df

async def get_recent_players(connection: Connection, search_mode: int = 2, lol_sgp: bool = True) -> dict[str, pandas.DataFrame]:
    if search_mode == 1:
        search_LoL: bool = True
        search_TFT: bool = True
    elif search_mode == 2:
        search_LoL, search_TFT = True, False
    elif search_mode == 3:
        search_LoL, search_TFT = False, True
    else:
        search_LoL, search_TFT = False, False
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_puuid: str = current_info["puuid"]
    current_summonerId: int = current_info["summonerId"]
    current_summonerName: str = get_info_name(current_info)
    LoLHistory_get: bool = False
    TFTHistory_get: bool = False
    LoLMatchIDs: list[int] = []
    if search_LoL:
        logPrint("开始获取英雄联盟对局记录。\nStart getting LoL match history.")
        LoLHistory_get, LoLHistory = await get_LoLHistory(connection, current_info["puuid"], log = log)
        if LoLHistory_get:
            LoLMatchIDs = list(map(lambda x: x["gameId"], LoLHistory["games"]["games"]))
    if len(LoLMatchIDs) > 0:
        logPrint("开始整理英雄联盟对局数据……\nStart organizing LoL match data ...")
        unmapped_keys1: dict[str, set[int]] = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
        if lol_sgp:
            LoLGame_summary_cache_fromSummary_sgp: dict[int, dict[str, Any]] = {}
            LoLHistory_get, LoLHistory = await get_matchSummary_sgp(connection, sgpSession, current_puuid, "LoL", begin = 0, count = 1000, log = log)
            for game in LoLHistory["games"]:
                matchId: int = int(game["metadata"]["match_id"].split("_")[1])
                if not matchId in LoLGame_summary_cache_fromSummary_sgp:
                    LoLGame_summary_cache_fromSummary_sgp[matchId] = game
            recent_LoLPlayer_df: pandas.DataFrame = await sort_LoLGame_stats_sgp(connection, sgpSession, LoLMatchIDs, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, puuid = current_puuid, save_self = False, save_other = True, save_bot = False, useAllVersions = False, unmapped_keys = unmapped_keys1, LoLGame_summary_cache = LoLGame_summary_cache_fromSummary_sgp, log = log)
        else:
            recent_LoLPlayer_df = await sort_LoLGame_stats(connection, LoLMatchIDs, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, puuid = current_puuid, save_self = False, save_other = True, save_bot = False, useAllVersions = False, unmapped_keys = unmapped_keys1, log = log)
    else:
        recent_LoLPlayer_df = pandas.DataFrame()
    #对于云顶之弈可以作一处优化：直接从对局记录获取全部信息（An optimization can be made on TFT: Get all information from the match history）
    TFTHistory: dict[str, Any] = {}
    if search_TFT:
        logPrint("开始获取云顶之弈对局记录。\nStart getting TFT match history.")
        TFTHistory_get, TFTHistory = await get_matchSummary_sgp(connection, sgpSession, current_info["puuid"], "TFT", begin = 0, count = 1000, log = log)
        if TFTHistory_get:
            logPrint("开始整理云顶之弈对局数据……\nStart organizing TFT match data ...")
            # TFTMatchIDs = list(map(lambda x: int(x["metadata"]["match_id"].split("_")[-1]), TFTHistory["games"]))
            unmapped_keys2: dict[str, set[Any]] = {"queue": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
            TFTGame_summary_header_keys: list[str] = list(TFTGame_summary_header.keys())
            TFTGame_stat_data: dict[str, list[Any]] = {key: [] for key in TFTGame_summary_header_keys}
            for i in range(len(TFTHistory["games"])):
                game: dict[str, Any] = TFTHistory["games"][i]
                if game.get("json"):
                    for j in range(len(game["json"]["participants"])):
                        participant: dict[str, Any] = game["json"]["participants"][j]
                        if not participant["puuid"] in {current_puuid, BOT_UUID}:
                            await generate_TFTGameInfo_records(connection, TFTGame_stat_data, game, j, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = i + 1, current_puuid = current_puuid, unmapped_keys = unmapped_keys2, log = log)
            TFTGame_stat_statistics_output_order: list[int] = [0, 19, 46, 47, 43, 5, 14, 15, 16, 6, 10, 18, 7, 13, 11, 12, 307, 305, 40, 55, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 150, 148, 149, 203, 206, 209, 155, 153, 154, 212, 215, 218, 160, 158, 159, 221, 224, 227, 165, 163, 164, 230, 233, 236, 170, 168, 169, 239, 242, 245, 175, 173, 174, 248, 251, 254, 180, 178, 179, 257, 260, 263, 185, 183, 184, 266, 269, 272, 190, 188, 189, 275, 278, 281, 195, 193, 194, 284, 287, 290, 200, 198, 199, 293, 296, 299, 61, 57, 58, 59, 60, 68, 64, 65, 66, 67, 75, 71, 72, 73, 74, 82, 78, 79, 80, 81, 89, 85, 86, 87, 88, 96, 92, 93, 94, 95, 103, 99, 100, 101, 102, 110, 106, 107, 108, 109, 117, 113, 114, 115, 116, 124, 120, 121, 122, 123, 131, 127, 128, 129, 130, 138, 134, 135, 136, 137, 145, 141, 142, 143, 144]
            TFTGame_stat_data_organized: dict[str, list[Any]] = {TFTGame_summary_header_keys[i]: TFTGame_stat_data[TFTGame_summary_header_keys[i]] for i in TFTGame_stat_statistics_output_order}
            recent_TFTPlayer_df: pandas.DataFrame = pandas.DataFrame(data = TFTGame_stat_data_organized)
            logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...")
            optimize_bool_display(recent_TFTPlayer_df)
            logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!")
            recent_TFTPlayer_df = pandas.concat([pandas.DataFrame([TFTGame_summary_header])[recent_TFTPlayer_df.columns], recent_TFTPlayer_df], ignore_index = True)
        else:
            recent_TFTPlayer_df = pandas.DataFrame()
    else:
        recent_TFTPlayer_df = pandas.DataFrame()
    return {"LoL": recent_LoLPlayer_df, "TFT": recent_TFTPlayer_df}

async def sort_friend_request(connection: Connection) -> pandas.DataFrame:
    friend_requests: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
    friend_request_header_keys: list[str] = list(friend_request_header.keys())
    friend_request_data: dict[str, list[Any]] = {key: [] for key in friend_request_header_keys}
    for friend_request in friend_requests:
        for i in range(len(friend_request_header_keys)):
            key: str = friend_request_header_keys[i]
            if i == 10:
                iconId: int = friend_request["icon"]
                to_append: Any = summonerIcons[iconId]["title"] if iconId in summonerIcons else ""
            else:
                to_append = friend_request[key]
            friend_request_data[key].append(to_append)
    friend_request_statistics_output_order: list[int] = [1, 9, 7, 0, 2, 10, 5]
    friend_request_data_organized: dict[str, list[Any]] = {friend_request_header_keys[i]: friend_request_data[friend_request_header_keys[i]] for i in friend_request_statistics_output_order}
    friend_request_df: pandas.DataFrame = pandas.DataFrame(data = friend_request_data_organized)
    friend_request_df = pandas.concat([pandas.DataFrame([friend_request_header])[friend_request_df.columns], friend_request_df], ignore_index = True)
    return friend_request_df

async def sort_party_data(connection: Connection, parties: Any) -> pandas.DataFrame:
    if isinstance(parties, list) and all(map(lambda x: isinstance(x, dict), parties)) and all(i in party for i in ["maxPlayers", "partyId", "queueId", "summoners"] for party in parties):
        party_header_keys: list[str] = list(party_header.keys())
        party_data: dict[str, list[Any]] = {key: [] for key in party_header_keys}
        for party in parties:
            for i in range(len(party_header_keys)):
                key: str = party_header_keys[i]
                if i >= 4 and i <= 6:
                    to_append: Any = gameQueues[party["queueId"]][key.split()[1]]
                elif i == 7:
                    summonerIds: list[int] = party["summoners"]
                    summonerNames: list[str] = []
                    for summonerId in summonerIds:
                        member_info_recapture: int = 0
                        member_info: dict[str, Any] = await get_info(connection, summonerId)
                        while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                            logPrint(member_info["message"])
                            member_info_recapture += 1
                            logPrint("成员信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an member (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(summonerId, member_info_recapture, summonerId, member_info_recapture))
                            member_info = await get_info(connection, summonerId)
                        if not member_info["info_got"]:
                            logPrint(member_info["message"])
                            logPrint("成员信息（召唤师序号：%d）获取失败！将忽略该成员。\nInformation of a member (summonerId: %d) capture failed! The program will ignore this member.")
                            summonerNames.append("")
                            continue
                        summonerNames.append(get_info_name(member_info["body"]))
                    to_append = summonerNames
                elif i == 8:
                    to_append = party["maxPlayers"] == len(party["summoners"])
                else:
                    to_append = party[key]
                party_data[key].append(to_append)
        party_statistics_output_order: list[int] = [1, 0, 4, 5, 2, 8, 7]  
        party_data_organized: dict[str, list[Any]] = {party_header_keys[i]: party_data[party_header_keys[i]] for i in party_statistics_output_order}
        party_df: pandas.DataFrame = pandas.DataFrame(data = party_data_organized)
        party_df = pandas.concat([pandas.DataFrame([party_header])[party_df.columns], party_df], ignore_index = True)
    else:
        logPrint("小队数据格式错误！函数将生成空表。\nParty data format ERROR! The function will return an empty table instead.")
        party_df = pandas.DataFrame(party_header, index = [0])
    return party_df

async def sort_received_invitations(connection: Connection) -> pandas.DataFrame:
    receivedInvitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
    invid_header_keys: list[str] = list(invid_header.keys())
    invid_data: dict[str, list[Any]] = {key: [] for key in invid_header_keys}
    for invid in receivedInvitations:
        inviter_info_recapture: int = 0
        inviter_info: dict[str, list[Any]] = await get_info(connection, invid["fromSummonerId"])
        while not inviter_info["info_got"] and inviter_info["body"]["httpStatus"] != 404 and inviter_info_recapture < 3:
            logPrint(inviter_info["message"])
            inviter_info_recapture += 1
            logPrint("邀请者信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an inviter (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(invid["fromSummonerId"], inviter_info_recapture, invid["fromSummonerId"], inviter_info_recapture))
            inviter_info = await get_info(connection, invid["fromSummonerId"])
        if not inviter_info["info_got"]:
            logPrint(inviter_info["message"])
            logPrint("邀请者信息（召唤师序号：%d）获取失败！将忽略该邀请者。\nInformation of an inviter (summonerId: %d) capture failed! The program will ignore this inviter.")
        for i in range(len(invid_header_keys)):
            key: str = invid_header_keys[i]
            if i <= 9:
                if i == 2:
                    to_append: Any = get_info_name(inviter_info["body"]) if inviter_info["info_got"] else ""
                elif i == 8:
                    to_append = inviter_info["body"]["puuid"] if inviter_info["info_got"] else ""
                elif i == 9:
                    try:
                        invid_timestamp = int(invid["timestamp"])
                    except ValueError: #自定义对局邀请的时间戳是转换好的（Custom game invitation's timestamp has already been transformed）
                        to_append = invid["timestamp"]
                    else:
                        to_append = getISOTime(invid_timestamp / 1000)
                else:
                    to_append = invid[key]
            elif i <= 13:
                to_append = invid["gameConfig"][key]
            else:
                to_append = "自定义" if invid["gameConfig"]["queueId"] == -1 else gameQueues[invid["gameConfig"]["queueId"]][key.split()[1]]
            invid_data[key].append(to_append)
    invid_statistics_output_order: list[int] = [2, 1, 8, 9, 4, 10, 11, 12, 14, 13, 3, 6, 0, 5]
    invid_data_organized: dict[str, list[Any]] = {invid_header_keys[i]: invid_data[invid_header_keys[i]] for i in invid_statistics_output_order}
    invid_df: pandas.DataFrame = pandas.DataFrame(data = invid_data_organized)
    invid_df = pandas.concat([pandas.DataFrame([invid_header])[invid_df.columns], invid_df], ignore_index = True)
    return invid_df

async def sort_mutedPlayers_champSelect(connection: Connection) -> pandas.DataFrame:
    muted_players: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/player-mutes")).json()
    champSelect_mutedPlayer_header_keys: list[str] = list(champSelect_mutedPlayer_header.keys())
    muted_player_data: dict[str, list[Any]] = {key: [] for key in champSelect_mutedPlayer_header_keys}
    for muted_player_puuid in muted_players:
        muted_player: dict[str, str | bool] = muted_players[muted_player_puuid]
        muted_player_info: dict[str, Any] = await get_info(connection, muted_player_puuid)
        for i in range(len(champSelect_mutedPlayer_header_keys)):
            key: str = champSelect_mutedPlayer_header_keys[i]
            if i >= 5:
                to_append: Any = muted_player_info["body"][key] if muted_player_info["info_got"] else ""
            else:
                to_append = muted_player[key]
            muted_player_data[key].append(to_append)
    muted_player_statistics_output_order: list[int] = [3, 6, 7, 5, 4, 0, 1, 2]
    muted_player_data_organized: dict[str, list[Any]] = {champSelect_mutedPlayer_header_keys[i]: muted_player_data[champSelect_mutedPlayer_header_keys[i]] for i in muted_player_statistics_output_order}
    muted_player_df: pandas.DataFrame = pandas.DataFrame(data = muted_player_data_organized)
    muted_player_df = pandas.concat([pandas.DataFrame([champSelect_mutedPlayer_header])[muted_player_df.columns], muted_player_df], ignore_index = True)
    return muted_player_df

async def sort_capture_devices(connection: Connection) -> pandas.DataFrame:
    captureDevices: list[dict[str, Any]] = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
    captureDevice_header_keys: list[str] = list(captureDevice_header.keys())
    captureDevice_data: dict[str, list[Any]] = {key: [] for key in captureDevice_header_keys}
    for device in captureDevices:
        for i in range(len(captureDevice_header_keys)):
            key: str = captureDevice_header_keys[i]
            to_append: Any = device[key]
            captureDevice_data[key].append(to_append)
    captureDevice_statistics_output_order: list[int] = [3, 4, 1, 2, 0]
    captureDevice_data_organized: dict[str, list[Any]] = {captureDevice_header_keys[i]: captureDevice_data[captureDevice_header_keys[i]] for i in captureDevice_statistics_output_order}
    captureDevice_df: pandas.DataFrame = pandas.DataFrame(data = captureDevice_data_organized)
    optimize_bool_display(captureDevice_df)
    captureDevice_df = pandas.concat([pandas.DataFrame([captureDevice_header])[captureDevice_df.columns], captureDevice_df], ignore_index = True)
    return captureDevice_df

async def sort_voice_settings(connection: Connection) -> pandas.DataFrame:
    voiceSettings: dict[str, Any] = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
    voiceSettings_df: pandas.DataFrame = pandas.concat([pandas.DataFrame(voiceSettings_header, index = [0]), pandas.DataFrame(voiceSettings, index = [1])], axis = 1)
    return voiceSettings_df

async def sort_voice_participants(connection: Connection) -> pandas.DataFrame:
    participant_records: list[dict[str, Any]] = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
    participant_record_header_keys: list[str] = list(participant_record_header.keys())
    participant_record_data: dict[str, list[Any]] = {key: [] for key in participant_record_header_keys}
    for participant in participant_records:
        participant_info: dict[str, Any] = await get_info(connection, participant["puuid"])
        for i in range(len(participant_record_header_keys)):
            key: str = participant_record_header_keys[i]
            if i >= 8:
                to_append: Any = participant_info["body"][key] if participant_info["info_got"] else ""
            else:
                to_append = participant[key]
            participant_record_data[key].append(to_append)
    participant_record_statistics_output_order: list[int] = [8, 9, 6, 5, 4, 2, 7, 3, 1]
    participant_record_data_organized: dict[str, list[Any]] = {participant_record_header_keys[i]: participant_record_data[participant_record_header_keys[i]] for i in participant_record_statistics_output_order}
    participant_record_df: pandas.DataFrame = pandas.DataFrame(data = participant_record_data_organized)
    participant_record_df = pandas.concat([pandas.DataFrame([participant_record_header])[participant_record_df.columns], participant_record_df], ignore_index = True)
    return participant_record_df

#定义客户端操作模拟过程（Define client behavior simulation processes）
async def output_friend_hovercard(connection: Connection, print_index: bool = False, start_index: int = 1) -> pandas.DataFrame:
    friend_hovercard_df: pandas.DataFrame = await sort_friend_hovercard(connection)
    friend_hovercard_fields_to_print: list[str] = ["name", "gameName", "gameTag", "availability", "level"]
    print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = print_index, start_index = start_index)[0], end = "\n\n")
    log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = print_index, start_index = start_index)[0] + "\n\n")
    return friend_hovercard_df

async def output_friend_hovercard_simple(connection: Connection, print_index: bool = False, start_index: int = 1) -> pandas.DataFrame:
    friend_hovercard_df: pandas.DataFrame = await sort_friend_hovercard_simple(connection)
    friend_hovercard_fields_to_print: list[str] = ["name", "gameName", "gameTag", "groupId", "groupName"]
    print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = print_index, start_index = start_index)[0])
    log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = print_index, start_index = start_index)[0] + "\n")
    return friend_hovercard_df

async def check_friend_list(connection: Connection) -> None:
    #输出到终端（Output to Terminal）
    friend_hovercard_df: pandas.DataFrame = await output_friend_hovercard(connection)
    #保存文件（Save file）
    logPrint("是否导出以上好友数据至Excel中？（输入任意键导出，否则不导出）\nDo you want to export the above data into Excel? (Press any key to export or null to refuse exporting)")
    export_str: str = logInput()
    export: bool = bool(export_str)
    if export:
        excel_name: str = "Friend List - %s.xlsx" %(get_info_name(current_info))
        wbPath: str = os.path.join(folder, excel_name)
        os.makedirs(folder, exist_ok = True)
        workbook_exist: bool = os.path.exists(wbPath)
        while True:
            try:
                with (pandas.ExcelWriter(path = wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(path = wbPath)) as writer:
                    currentTime: str = time.strftime("%Y-%m-%d", time.localtime())
                    addDefaultStyle(friend_hovercard_df).to_excel(excel_writer = writer, sheet_name = platformId + "-" + get_info_name(current_info) + " " + currentTime)
            except PermissionError:
                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                logInput()
            else:
                logPrint('好友信息已保存为“%s”！\nFriend information is saved as "%s"!\n' %(wbPath, wbPath))
                break

async def output_friend_group(connection: Connection) -> tuple[list[dict[str, Any]], list[int], pandas.DataFrame]:
    friend_groups: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
    friend_groupIds: list[int] = list(map(lambda x: x["id"], friend_groups))
    logPrint("您一共设置了%d个分组：\nYou have %d group(s):\n" %(len(friend_groups), len(friend_groups)))
    friend_group_df: pandas.DataFrame = await sort_friend_group(connection)
    friend_group_df_to_print: list[str] = friend_group_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
    print(format_df(friend_group_df_to_print)[0], end = "\n\n")
    log.write(format_df(friend_group_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n\n")
    return (friend_groups, friend_groupIds, friend_group_df)

async def manage_friend_group(connection: Connection) -> None:
    friend_groups, friend_groupIds, friend_group_df = await output_friend_group(connection)
    logPrint("请选择好友分组操作：\nPlease select an operation on friend groups:\n0\t返回上一层（Return to the last step）\n1\t添加分组（Add folder）\n2\t折叠/展开分组（Collapse/Expand folder）\n3\t重命名分组（Rename folder）\n*4\t排列分组顺序（Arrange folder order）\n5\t删除分组（Delete folder）\n6\t刷新好友分组（Refresh folders）")
    while True:
        action: str = logInput()
        if action == "":
            continue
        if action[0] == "0":
            break
        elif action[0] == "1":
            logPrint("请输入新分组名称：（输入默认分组名称以退出创建）\nPlease enter the new group name: (Submit the default folder name, namely **Default, to quit creating)")
            while True:
                newGroupName: str = logInput()
                if newGroupName == "":
                    continue
                elif newGroupName == "**Default":
                    break
                elif newGroupName in set(friend_group_df["name"]):
                    logPrint("该分组已存在。请使用其它名称。\nThis folder already exists. Please use another name.")
                else:
                    body: dict[str, str] = {"name": newGroupName}
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-chat/v1/friend-groups", data = body)).json()
                    logPrint(response)
                    if response == None:
                        logPrint("已创建新的分组：%s。\nCreated a new folder: %s" %(newGroupName, newGroupName))
                        friend_groups, friend_groupIds, friend_group_df = await output_friend_group(connection)
                        logPrint("请输入新分组名称：\nPlease enter the new group name:")
                    else:
                        logPrint("创建分组失败。\nThe program failed to create the new folder.")
        elif action[0] == "2":
            logPrint("请选择折叠/展开选项：\nPlease select a collapse/expand option:\n0\t返回上一层（Return to the last step）\n1\t全部展开（Expand all）\n2\t全部折叠（Collaspe all）\n3\t展开/折叠指定分组（Expand/Collapse specific groups）")
            while True:
                strategy: str = logInput()
                if strategy == "":
                    continue
                elif strategy[0] == "0":
                    break
                elif strategy[0] == "1" or strategy[0] == "2":
                    for group in friend_groups:
                        body: dict[str, Any] = {"collapsed": strategy[0] == "2", "name": group["name"], "priority": group["priority"]} #展开/折叠分组时，只要在链接中指定分组序号即可，即使这里没有name键（To expand / collapse a folder, specifiying the following folder id should be enough. It doesn't matter whether the key "name" exists here）
                        response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-chat/v1/friend-groups/%d" %(group["id"]), data = body)).json()
                        logPrint(response)
                        if response == None or "errorCode" in response and response["httpStatus"] == 500:
                            if strategy[0] == "1":
                                logPrint("已展开%s分组。\nFolder %s expanded." %(group["name"], group["name"]))
                            else:
                                logPrint("已折叠%s分组。\nFolder %s collapsed." %(group["name"], group["name"]))
                        elif "errorCode" in response and response["httpStatus"] == 404:
                            logPrint("操作失败！请检查分组%s是否存在。\nAction failed! Please check if the folder %s is still there." %(group["name"], group["name"]))
                elif strategy[0] == "3":
                    logPrint('请输入要更改展开/折叠状态的分组序号。输入“-1”以返回上一层。\nPlease input the group ids to switch the expansion/collapse state. Submit "-1" to return to the last step.')
                    while True:
                        groupId: str = logInput()
                        if groupId == "":
                            continue
                        elif groupId.startswith("-1"):
                            break
                        elif groupId in set(map(str, friend_groupIds)):
                            group: dict[str, Any] = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                            if "errorCode" in group and group["httpStatus"] == 404:
                                logPrint("操作失败！请检查分组是否存在。\nAction failed! Please check if the folder is still there.")
                            else:
                                body: dict[str, Any] = {"collapsed": not(group["collapsed"]), "name": group["name"], "priority": group["priority"]}
                                response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-chat/v1/friend-groups/%d" %(group["id"]), data = body)).json()
                                logPrint(response)
                                if response == None or "errorCode" in response and response["httpStatus"] == 500:
                                    if body["collapsed"]:
                                        logPrint("已折叠%s分组。\nFolder %s collapsed." %(group["name"], group["name"]))
                                    else:
                                        logPrint("已展开%s分组。\nFolder %s expanded." %(group["name"], group["name"]))
                                elif "errorCode" in response and response["httpStatus"] == 404:
                                    logPrint("操作失败！请检查分组%s是否存在。\nAction failed! Please check if the folder %s is still there." %(group["name"], group["name"]))
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                friend_groups, friend_groupIds, friend_group_df = await output_friend_group(connection)
                logPrint("请选择折叠/展开选项：\nPlease select a collapse/expand option:\n1\t全部展开（Expand all）\n2\t全部折叠（Collaspe all）\n3\t展开/折叠指定分组（Expand/Collapse specific folders）")
        elif action[0] == "3":
            logPrint('请输入要重命名的分组序号。输入“-1”以返回上一层。\nPlease input the group ids to rename. Submit "-1" to return to the last step.')
            while True:
                groupId = logInput()
                if groupId == "":
                    continue
                elif groupId.startswith("-1"):
                    break
                elif groupId in set(map(str, friend_groupIds)):
                    group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                    if groupId == "0":
                        logPrint("无法重命名默认分组。请换一个分组重试。\nCan't rename the default folder. Please change another folder and try again.") #重命名默认分组返回的状态值是403（The httpStatus returned by renaming the default folder is 403）
                    else:
                        logPrint("该分组的当前名称是%s。您想要将其修改为：\nThe current name for the selected folder is %s. You want to change it into:" %(group["name"], group["name"]))
                        name: str = logInput()
                        if name == "":
                            logPrint("请输入要重命名的分组序号：\nPlease input the group ids to rename:")
                            continue
                        else:
                            body = {"collapsed": group["collapsed"], "name": name, "priority": group["priority"]}
                            response = await (await connection.request("PUT", "/lol-chat/v1/friend-groups/%d" %(group["id"]), data = body)).json()
                            logPrint(response)
                            if response == None:
                                logPrint("已重命名分组。\nRenamed the group.\n原名称（Old name）：%s新名称（New name）：%s" %(group["name"], name))
                            else:
                                if response["httpStatus"] == 404:
                                    logPrint("新名称已存在。请换个名字再试一次。\nNew name already exists. Please change another name and try again.")
                                else:
                                    logPrint("重命名%s分组失败。\nRenaming the group %s failed." %(group["name"], group["name"]))
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                friend_groups, friend_groupIds, friend_group_df = await output_friend_group(connection)
                logPrint("请输入要重命名的分组序号：\nPlease input the group ids to rename:")
        elif action[0] == "4":
            current_groupOrder_list: list[str] = list(friend_group_df.iloc[1:].sort_values(by = "priority", ascending = False)["id"])
            logPrint("警告：修改好友分组排列顺序涉及较多的优先级运算，因此请不要频繁修改，否则可能导致预期之外的排列顺序。\nWarning: Rearranging friend group order involve involve a lot of priority calculations, so please don't change frequently, otherwise the folders may display in an unexpected order.\n")
            logPrint('''请输入一个您期望的分组序号排列顺序列表，排在前面的代表显示在前，排在后面的代表显示在后。例如，如果想恢复您当前的排序，您可以输入“%s”。\nPlease input a groupId order list, where the group whose groupId index is small will be moved in the front of friend list, and vice versa. For example, if you'd like to recover the current friend group order, you may input "%s".''' %(current_groupOrder_list, current_groupOrder_list))
            while True:
                group_order_str: str = logInput()
                if group_order_str == "":
                    continue
                elif group_order_str[0] == "0":
                    break
                else:
                    try:
                        tmp = eval(group_order_str)
                    except:
                        traceback_info = traceback.format_exc()
                        logPrint(traceback_info)
                        logPrint("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
                    else:
                        if isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x in friend_groupIds, tmp)) and len(tmp) == len(set(tmp)): #这里需要严格控制输入格式：①输入的是一个列表；②列表的元素全是整型，且都是分组序号；③列表元素无重复（Here the input format are strictly controlled: ①the input is a list; ②each element in the list is of integer type and represents a group id; ③the elements are unique）
                            group_order: list[int] = tmp
                            priority: int = max(100, max(map(lambda x: x["priority"], friend_groups))) + len(group_order) #后者是为了防止优先级递减而小于原分组优先级的最大值（The addend is designed to prevent `priority` from being less than the maximum of the original group priority）
                            error_occurred_groupArrange: bool = False
                            for groupId in group_order:
                                group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                                body: dict[str, Any] = {"collapsed": group["collapsed"], "name": group["name"], "priority": priority} #请求主体中没有name键时，不仅请求速度降低，而且还会返回一个500异常信息（If the key "name" isn't in the request body, not only does the request speed slows, but the request also returns an error with a 500 httpStatus）
                                response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-chat/v1/friend-groups/{groupId}", data = body)).json()
                                logPrint(response)
                                if response == None:
                                    logPrint("已将%s分组的优先级设置为%d。\nSet the priority of Group %s as %d." %(group["name"], priority, group["name"], priority))
                                else:
                                    if response["httpStatus"] != 500:
                                        error_occurred_groupArrange = True
                                priority -= 1
                            if error_occurred_groupArrange:
                                logPrint("排序过程发生了异常。请等待客户端刷新分组顺序后，或者对好友列表进行适当操作后手动排序。\nAn error occurred during ordering. Please order manually after League client refreshes the group order or you do some operations on your friend list.")
                            else:
                                logPrint("排序完成。请等待客户端刷新分组顺序，或者对好友列表进行适当操作以立刻刷新分组顺序。\nOrder success. Please wait for the League client to refresh the group order, or make some operations on the friend list to refersh group order immediately.")
                            break
                        else:
                            logPrint("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
        elif action[0] == "5":
            logPrint("警告：删除分组将导致该分组好友全部移至默认分组。您确认要删除分组吗？（输入任意键以确认删除，否则取消删除。）\nWarning: Removing folders will cause the friends under these folders to be moved to the default group. Do you want to continue? (Input anything to confirm removal, or null to cancel.)")
            confirm_str: str = logInput()
            confirm: bool = bool(confirm_str)
            if confirm:
                logPrint('请输入您要删除的分组序号。输入“-1”以退出。\nPlease input the id of the group to remove. Submit "-1" to exit.')
                while True:
                    groupId = logInput()
                    if groupId == "":
                        continue
                    elif groupId.startswith("-1"):
                        break
                    elif groupId in set(map(str, friend_groupIds)):
                        if groupId == "0":
                            logPrint("无法删除默认分组。\nYou can't remove the default folder.")
                        else:
                            group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                            logPrint("是否在删除该分组的同时删除所有好友？（输入任意非空字符串以删除，否则这些好友会移动至默认分组。）\nDo you want to delete all friends in this group? (Submit any non-empty string to delete them, or null to move them to the default group.)")
                            delete_friend_sync_str: str = logInput()
                            delete_friend_sync = bool(delete_friend_sync_str)
                            if delete_friend_sync:
                                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                                if isinstance(friends, dict) and "errorCode" in friends:
                                    logPrint("获取好友列表时出现了一个异常。\nAn error occurred when the program was trying to get the friend list.")
                                else:
                                    for friend in friends:
                                        if friend["groupId"] == group["id"]:
                                            pid: str = friend["id"]
                                            unfriend_summonerName: str = get_info_name(friend)
                                            response = await (await connection.request("DELETE", f"/lol-chat/v1/friends/{pid}")).json()
                                            logPrint(response)
                                            if response == None:
                                                logPrint("您已与%s解除好友关系。\nYou've unfriended %s successfully." %(unfriend_summonerName, unfriend_summonerName))
                                            else:
                                                if response["httpStatus"] == 404:
                                                    logPrint("您未能成功与%s解除好友关系。可能你们已经不是好友了。\nYou failed to unfriend %s. Maybe you're not friends already." %(unfriend_summonerName, unfriend_summonerName))
                                                else:
                                                    logPrint("您未能成功与%s解除好友关系。\nYou failed to unfriend %s." %(unfriend_summonerName, unfriend_summonerName))
                            response = await (await connection.request("DELETE", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                            logPrint(response)
                            if response == None:
                                logPrint("已删除分组%s。\nRemoved folder %s." %(group["name"], group["name"]))
                            else:
                                logPrint("删除分组%s失败。也许它已经被删除了。\nRemoving folder %s failed. Maybe it's already been removed." %(group["name"], group["name"]))
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    friend_groups, friend_groupIds, friend_group_df = await output_friend_group(connection)
                    logPrint('请输入您要删除的分组序号。输入“-1”以退出。\nPlease input the id of the group to remove. Submit "-1" to exit.')
        friend_groups, friend_groupIds, friend_group_df = await output_friend_group(connection)
        logPrint("请选择好友分组操作：\nPlease select an operation on friend groups:\n0\t返回上一层（Return to the last step）\n1\t添加分组（Add folder）\n2\t折叠/展开分组（Collapse/Expand folder）\n3\t重命名分组（Rename folder）\n*4\t排列分组顺序（Arrange folder order）\n5\t删除分组（Delete folder）\n6\t刷新好友分组（Refresh folders）")

async def count_friend_statistics(connection: Connection) -> None:
    friend_counts: dict[str, int] = await (await connection.request("GET", "/lol-chat/v1/friend-counts")).json()
    logPrint("好友在线/离线状态数据如下：\nFriend online/offline status is listed below:\n")
    friend_count_data: dict[str, list[str | int]] = {"项目": ["好友总数", "在线", "闲置", "队列中", "英雄选择", "游戏中", "离开", "在线分组"], "Items": ["numFriends", "numFriendsOnline", "numFriendsAvailable", "numFriendsInQueue", "numFriendsInChampSelect", "numFriendsInGame", "numFriendsAway", "numFriendsMobile"], "值": [friend_counts["numFriends"], friend_counts["numFriendsOnline"], friend_counts["numFriendsAvailable"], friend_counts["numFriendsInQueue"], friend_counts["numFriendsInChampSelect"], friend_counts["numFriendsInGame"], friend_counts["numFriendsAway"], friend_counts["numFriendsMobile"]]}
    friend_count_df: pandas.DataFrame = pandas.DataFrame(data = friend_count_data)
    print(format_df(friend_count_df, align = "><^")[0], end = "\n\n")
    log.write(format_df(friend_count_df, align = "><^", width_exceed_ask = False, direct_print = False)[0] + "\n\n")

async def export_conversation(connection: Connection) -> None:
    logPrint("提示：请在客户端右侧点击你想要导出对话的好友以激活对话。\nHint: Please activate the conversation by clicking the friend whom you want to export the messages from and to at the right side of the client.")
    json1name: str = "Conversations - %s.json" %(get_info_name(current_info))
    if os.path.exists(os.path.join(folder, json1name)):
        with open(os.path.join(folder, json1name), "r", encoding = "utf-8") as fp:
            conversation_json: dict[str, dict[str, Any]] = json.load(fp)
    else:
        conversation_json = {}
    conversations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
    if len(conversations) > 0:
        logPrint("请选择导出对话的模式：\nPlease select a mode to export conversations:\n1\t全部导出（All）\n2\t单个导出（Single）")
        while True:
            conversations_got: bool = False
            conversations_to_export: list[dict[str, Any]] = []
            mode: str = logInput()
            if mode == "":
                continue
            elif mode[0] == "0":
                break
            elif mode[0] == "1" or mode[0] == "2":
                conversations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
                if len(conversations) > 0:
                    if mode[0] == "1":
                        conversations_to_export = conversations
                        conversations_got = True
                    else:
                        logPrint("目前已激活的对话如下：\nCurrently active conversations:")
                        conversation_df: pandas.DataFrame = await sort_conversation_metadata(connection)
                        print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                        log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint("请选择您想要导出的对话序号：\nPlease select a conversation to export messages:")
                        while True:
                            conversationIndex: str = logInput()
                            if conversationIndex == "":
                                continue
                            elif conversationIndex == "-1":
                                logPrint("目前已激活的对话如下：\nCurrently active conversations:")
                                conversation_df = await sort_conversation_metadata(connection)
                                print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                                log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                logPrint("请选择您想要导出的对话序号：\nPlease select a conversation to export messages:")
                                continue
                            elif conversationIndex[0] == "0":
                                break
                            elif conversationIndex in set(map(str, list(range(1, len(conversations) + 1)))):
                                conversations_to_export = [conversations[int(conversationIndex) - 1]]
                                conversations_got = True
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                else:
                    logPrint("未检测到激活的对话。\nNo active conversation detected.")
                    break
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                continue
            if conversations_got:
                #先保存json文件（Save json files）
                exported: bool = False
                for conversation in conversations_to_export:
                    chatId: str = conversation["id"]
                    messages: list[dict[str, Any]] | dict[str, Any] = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                    if "errorCode" in messages and messages["httpStatus"] == 404:
                        continue
                    messages_sorted: list[dict[str, Any]] = sorted(messages, key = lambda x: x["timestamp"])
                    if not chatId in conversation_json:
                        conversation_json[chatId] = []
                    else:
                        old_system_messages: list[dict[str, Any]] = []
                        for message in conversation_json[chatId]:
                            if message["type"] == "system":
                                old_system_messages.append(message)
                        for message in old_system_messages:
                            conversation_json[chatId].remove(message)
                    for message in messages_sorted:
                        if not message in conversation_json[chatId]:
                            conversation_json[chatId].append(message)
                with open(os.path.join(folder, json1name), "w", encoding = "utf-8") as fp:
                    json.dump(conversation_json, fp, indent = 4, ensure_ascii = False)
                #然后导出数据框（Then, export dataframes）
                for conversation in conversations_to_export:
                    chatId = conversation["id"] #有可能获取完对话元数据后，用户把对话关了，然后从对话获取消息就获取不到了（Chances are that the user closes the conversation after the program obtains the conversation metadata, so that the program can't get the messages）
                    if chatId in conversation_json:
                        message_df: pandas.DataFrame = await sort_message_data(connection, conversation_json[chatId])
                        message_df = pandas.concat([message_df.iloc[:1], message_df.iloc[1:].sort_values(by = "timestamp", ascending = True)], ignore_index = True)
                        excel_name: str = "Conversations - %s.xlsx" %(get_info_name(current_info))
                        wbPath: str = os.path.join(folder, excel_name)
                        os.makedirs(folder, exist_ok = True)
                        workbook_exist: bool = os.path.exists(wbPath)
                        sheet_name: str = conversation["gameName"] + "#" + conversation["gameTag"] if conversation["type"] == "chat" else conversation["id"].split("@")[0]
                        while True:
                            try:
                                with (pandas.ExcelWriter(path = wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(path = wbPath)) as writer:
                                    addDefaultStyle(message_df).to_excel(excel_writer = writer, sheet_name = sheet_name)
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            else:
                                logPrint("已导出对话（Conversation exported）： %s\t%s" %(conversation["id"], get_info_name(conversation)))
                                break
                        exported = True
                    else:
                        logPrint("未激活的对话（Inactive conversation）： %s\t%s" %(conversation["id"], get_info_name(conversation)))
                if exported:
                    logPrint('\n对话信息已保存为“%s”！\nConversation messages are saved as "%s"!\n' %(wbPath, wbPath))
                else:
                    logPrint("未检测到激活的对话。\nNo active conversation detected.")
            conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
            if len(conversations) > 0:
                logPrint("请选择导出对话的模式：\nPlease select a mode to export conversations:\n1\t全部导出（All）\n2\t单个导出（Single）")
            else:
                logPrint("未检测到激活的对话。\nNo active conversation detected.")
                break
    else:
        logPrint("未检测到激活的对话。\nNo active conversation detected.")

async def chat(connection: Connection, pid: str) -> None:
    '''
    向目标社交代码的用户或群体发送消息。<br>Send messages to a target or community with the target pid.
    
    :param pid: 社交代码。对于召唤师而言，往往由**玩家通用唯一识别码**和**对战网址后缀**构成。<br>Player id. When it comes to a summoner, this pid is always composed of **puuid** and **PvP net suffix**.
    :type pid: str
    '''
    isFriendPid: bool = pid.endswith("@pvp.net") or pid.endswith("@%s.pvp.net" %(platformId.lower()))
    messages: list[dict[str, Any]] | dict[str, Any] = await (await connection.request("GET", f"/lol-chat/v1/conversations/{pid}/messages")).json()
    if "errorCode" in messages and messages["httpStatus"] == 404:
        logPrint("该对话尚未激活。如果这是一位好友的社交代码，请在客户端右边的好友列表中点击该好友，或者直接发送一条聊天类消息，以激活对话。\nThis conversation hasn't been activated yet. If this is a friend's pid, please click this friend in the friend list at the right side of the client, or send a chat message directly to activate the conversation.")
    mTypeDict = {"1": "chat", "2": "groupchat", "3": "system", "4": "information", "5": "celebration"}
    logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n%s2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（Custom）" %("!" if isFriendPid else ""))
    while True:
        mType: str = logInput()
        if mType == "":
            continue
        elif mType[0] == "0":
            break
        elif mType[0] in mTypeDict:
            if isFriendPid and mType[0] == "2":
                logPrint("小队聊天不适用。请重新选择。\nGroupchat isn't available. Please change for another type.")
                continue
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
            messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{pid}/messages")).json()
            #先输出聊天记录（First output the chat history）
            if not "errorCode" in messages:
                logPrint("聊天记录（Chat history）：\n")
                for message in messages:
                    timestamp = message["timestamp"][:10] + " " + message["timestamp"][11:23]
                    fromInfo = await get_info(connection, message["fromPuuid"])
                    from_summonerName = get_info_name(fromInfo["body"]) if fromInfo["info_got"] else ""
                    if message["type"] == "chat" or message["type"] == "groupchat":
                        logPrint("[%s]%s：\n%s\n" %(timestamp, from_summonerName, message["body"]))
                    elif message["type"] == "system":
                        system_messages = {"connecting": "正在连接……", "disconnected": "您已从聊天服务器断开，正在尝试重新连接……", "dropped_message": "由于发言内容或账号环境存在异常，消息发送暂时被限制，请注意账号保护并24小时后再试。", "is_blocked": "{actor}正在你的聊天黑名单中。你将不会看到它们的聊天信息。".format(actor = from_summonerName), "joined_room": "{actor}加入了队伍聊天".format(actor = from_summonerName), "left_room": "{actor}离开了队伍聊天".format(actor = from_summonerName), "no_friends": "看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。", "no_online_friends": "一个小伙伴都没在线。你知道吗，你是可以给离线的玩家发送信息的哟~", "rich_content_replaced": "请查看《英雄联盟》移动端APP里的消息", "TEXT_CHAT_MUTED": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_RESTRICTION": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_MUTED_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。", "TEXT_CHAT_RESTRICTION_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。"}
                        logPrint("[%s]%s\n" %(timestamp, system_messages.get(message["body"], message["body"])))
                    else:
                        logPrint("[%s](%s)%s\n" %(timestamp, messageTypes.get(message["type"], message["type"]), message["body"]))
            logPrint("▶ ", end = "")
            text: str = aInput()
            log.write(text + "\n")
            if text.endswith(chr(4) * 2):
                continue
            elif text == "" or text.endswith(chr(4)):
                break
            else:
                body = {"type": messageType, "body": text}
                response = await (await connection.request("POST", f"/lol-chat/v1/conversations/{pid}/messages", data = body)).json()
                logPrint(response)
                if "errorCode" in response:
                    if response["httpStatus"] == 404:
                        logPrint("聊天服务响应失败！请先激活对话。\nERROR response for chat service! Please activate this conversation first.")
                    else:
                        logPrint("聊天服务响应失败！\nERROR response for chat service!")
        logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n%s2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（Custom）" %("!" if isFriendPid else ""))

async def send_message(connection: Connection) -> None:
    global message_hint_printed
    if not message_hint_printed:
        logPrint("（提示：编辑好内容后，在终端中按Ctrl-D以插入结束字符，再按回车键发送消息。插入两个Ctrl-D以取消对话。插入三个Ctrl-D以刷新消息。如果终端不支持插入Ctrl-D字符，新建一个Python工作台，引入pyperclip库后使用pyperclip.copy(chr(4))以复制Ctrl-D实际代表的字符，再粘贴在聊天终端中，按回车键发送消息。）\n(Hint: If you finished editing the message, you must press Ctrl-D to insert the ending character and then press Enter to send the message. Append double Ctrl-D to cancel chatting. Append triple Ctrl-D to refresh messages. If the current terminal doesn't support inserting Ctrl-D character, please create a Python console, import pyperclip library and then use `pyperclip.copy(chr(4))` to copy the character that Ctrl-D actually represents. Finally, paste it into the current terminal and press Enter to send the message.)")
        message_hint_printed = True
    messageTypes: dict[str, str] = {"chat": "聊天", "groupchat": "队伍聊天", "system": "系统", "information": "通知", "celebration": "庆祝"}
    escape_sequences: dict[str, str] = {"\\n": ""} #这个变量本来是用于确定在聊天中怎么输入转义字符的。目前仅通过input()函数来输入换行符没有办法做到。参考链接：（This variable is originally intended to determine how to input an escape character in chat. It seems for now that there's no way of inputting a line feed character only using `input` function. Reference: ）https://www.educba.com/escape-sequence-in-c/
    logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")
    while True:
        situation: str = logInput()
        if situation == "":
            continue
        elif situation[0] == "0":
            break
        elif situation[0] == "1":
            friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
            if len(friends) == 0:
                logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
            else:
                logPrint("您的好友信息如下：\nYour friends:")
                friend_hovercard_fields_to_print: list[str] = ["name", "gameName", "gameTag", "availability", "level"]
                friend_hovercard_df: pandas.DataFrame = await output_friend_hovercard(connection, print_index = True, start_index = 1)
                logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                draft_str: str = logInput()
                draft: bool = bool(draft_str)
                if draft:
                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                    while True:
                        draft_option: str = logInput()
                        if draft_option == "":
                            continue
                        elif draft_option[0] == "0":
                            break
                        elif draft_option[0] == "1":
                            scope: dict[str, Any] = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                            logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                            subscope(scope, log = log)
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            continue
                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                logPrint("请选择一位好友：\nPlease select a friend:")
                friend_hovercard_df = await output_friend_hovercard(connection, print_index = True, start_index = 1)
                logPrint("变量提示（Variable hints）：\nfriend_hovercard_df = await sort_friend_hovercard(connection)")
                while True:
                    friend_index_str: str = logInput()
                    if friend_index_str == "":
                        continue
                    elif friend_index_str[0] == "0":
                        break
                    else:
                        try:
                            tmp = eval(friend_index_str)
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        else:
                            if isinstance(tmp, int) and tmp in range(1, len(friend_hovercard_df)):
                                friend_index: int = tmp
                                chatId: str = friend_hovercard_df["pid"][friend_index]
                                await chat(connection, chatId)
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    logPrint("请选择一位好友：\nPlease select a friend:")
                    friend_hovercard_df = await output_friend_hovercard(connection, print_index = True, start_index = 1)
                    logPrint("变量提示（Variable hints）：\nfriend_hovercard_df = await sort_friend_hovercard(connection)")
        elif situation[0] == "2":
            conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
            conversation_df = await sort_conversation_metadata(connection)
            if len(conversation_df) == 1: #筛选后的数据框仍包含中文标题（The filtered dataframe still includes the Chinese header）
                logPrint("未检测到激活的对话。\nNo active conversation detected.")
            else:
                logPrint("请选择对话：\nPlease select a conversation:")
                print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                while True:
                    conversation_index_str = logInput()
                    if conversation_index_str == "":
                        continue
                    elif conversation_index_str == "0":
                        break
                    elif conversation_index_str in set(map(str, range(len(conversation_df)))):
                        chatId = conversation_df["id"][int(conversation_index_str)]
                        await chat(connection, chatId)
                        conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
                        conversation_df = await sort_conversation_metadata(connection)
                        if len(conversation_df) == 1:
                            logPrint("未检测到激活的对话。\nNo active conversation detected.")
                            break
                        else:
                            logPrint("请选择对话：\nPlease select a conversation:")
                            print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                            log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif situation[0] == "3":
            logPrint("请输入社交代码：\nPlease enter the pid:")
            while True:
                pid: str = logInput()
                if pid == "":
                    continue
                elif pid == "0":
                    break
                else:
                    await chat(connection, pid)
                logPrint("请输入社交代码：\nPlease enter the pid:")
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            continue
        logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")

async def add_friend(connection: Connection) -> None:
    logPrint("已经知道好友的玩家名称#名称编号？快给TA发送好友请求吧！请输入您想要添加的玩家名称：\nAlready know your friend’s Riot ID? Send them a friend request! Please submit the Riot IDs of the player(s) you want to make friend with:")
    while True:
        friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
        friend_puuids: list[str] = set(map(lambda x: x["puuid"], friends))
        prefriend_name: str = logInput()
        prefriend_exist: bool = False
        if prefriend_name == "":
            #logPrint("玩家名字不能为空！\nPlayer name cannot be blank!")
            continue
        elif prefriend_name == "0":
            break
        else:
            prefriend_info: dict[str, Any] = await get_info(connection, prefriend_name)
            if prefriend_info["info_got"]:
                if prefriend_info["selfInfo"]:
                    logPrint("你无法把自己加为好友，亲～\nYou cannot friend yourself, silly xD")
                    continue
                elif prefriend_info["body"]["puuid"] in friend_puuids:
                    logPrint("你和%s已经是好友了。\nYou and %s are already friends." %(get_info_name(prefriend_info["body"]), get_info_name(prefriend_info["body"])))
                    continue
                else:
                    if prefriend_info["searchType"] == "puuid":
                        body: dict[str, str] = {"puuid": prefriend_name}
                    elif prefriend_info["searchType"] == "riotId":
                        prefriend_gameName, prefriend_tagLine = prefriend_name.split("#")
                        body = {"gameName": prefriend_gameName, "tagLine": prefriend_tagLine}
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-chat/v2/friend-requests", data = body)).json() #由于该接口的报错信息过于单一，这里只能自己设置报错机制。来源：rcp-fe-lol-social/global/zh_cn/trans.json（Because the error information from endpoint turns out to be too simple, here the error feedback is set manually. Reference: rcp-fe-lol-social/global/zh_cn/trans.json）
                    logPrint(response)
                    if response == None:
                        logPrint("已给这位用户发送了请求。如果该用户接受了你的请求，那么你就可以看到该用户处于在线状态。\nA request has been sent to this user. You will see them online if they accept your request.")
                    else:
                        if response["httpStatus"] == 403:
                            logPrint("你无法把自己加为好友，亲～\nYou cannot friend yourself, silly xD")
                        elif response["httpStatus"] == 404:
                            logPrint("该玩家名字不存在。\nThis player name doesn't exist.")
                        elif response["httpStatus"] == 405:
                            logPrint("该玩家在聊天黑名单中。请将其移出聊天黑名单并重试。\nThis player is blocked. Please unblock his/her and try again.")
                        elif response["httpStatus"] == 409:
                            logPrint("该玩家的好友列表已满——无法发送好友请求。\nThat player's friend list is full - unable to send friend request.")
                        elif response["httpStatus"] == 500:
                            logPrint("内部服务器错误。可能原因如下：\n1. 该玩家名字包含了无效字符。\n2. 您发送和接收的好友请求数量总和已满50个。\n3. 您的好友数量和发送和接受的好友请求数量总和的和已满375个。\n4. 你的账号受限，无法发送好友请求。请稍后再试或联系客服寻求帮助。\nInternal server error. A possible reason may be:\n1. This player name contains invalid characters.\n2. You can't sent and receive more than 50 friend requests at the same time.\n3. The sum of your friend count and the total number of friend requests sent and received has reached 375.\n4. Your account is restricted from sending friend requests. Please try again later or contact customer service for help.")
                        elif response["httpStatus"] == 503:
                            logPrint("发送好友请求的过程响应失败。\nError response for POST /chat/v6/friendrequests: ")
                        else:
                            logPrint(response)
            else:
                logPrint(prefriend_info["message"])

async def manage_friend_request(connection: Connection) -> None:
    friend_requests: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
    if "errorCode" in friend_requests:
        logPrint(friend_requests)
        if friend_requests["httpStatus"] == 503 and friend_requests["message"] == "Error response for GET /chat/v6/friendrequests: ": #获取新玩家的好友请求会返回此信息（Getting a new player's friend request will return this information）
            logPrint("好友请求获取失败！\nError response for GET /chat/v6/friendrequests!")
        else:
            logPrint("好友请求获取失败！\nFriend request data capture failure!")
    else:
        if len(friend_requests) == 0:
            logPrint("您尚未发送或收到任何好友请求。\nYou haven't sent or received any friend request.")
        else:
            logPrint("您的好友请求如下：\nYour friend requests:")
            friend_request_df: pandas.DataFrame = await sort_friend_request(connection)
            friend_request_fields_to_print: list[str] = ["gameName", "tagLine", "direction", "icon title"]
            print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
            log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
            logPrint("请选择好友请求处理模式：\nPlease select a mode to handle friend requests:\n0\t返回上一层（Return to the last step）\n1\t单个处理（Single）\n2\t批量处理（In batches）\n3\t全部处理（All）")
            while True:
                index_got: bool = False
                mode: str = logInput()
                if mode == "":
                    continue
                elif mode == "0":
                    break
                elif mode == "1":
                    logPrint("请选择要处理的好友请求：\nPlease enter the index of the friend request to handle:")
                    while True:
                        handle_str: str = logInput()
                        if handle_str == "":
                            continue
                        elif handle_str == "0":
                            break
                        elif handle_str in set(map(str, range(1, len(friend_request_df)))):
                            handle_indices: list[int] = [int(handle_str)]
                            index_got = True
                            break
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                elif mode == "2":
                    logPrint("是否需要对好友请求取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend request data? (Submit any non-empty string to make a draft, or null to input the friend request index directly.)")
                    draft_str: str = logInput()
                    draft: bool = bool(draft_str)
                    if draft:
                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        while True:
                            draft_option = logInput()
                            if draft_option == "":
                                continue
                            elif draft_option[0] == "0":
                                break
                            elif draft_option[0] == "1":
                                scope: dict[str, Any] = {"format_df": format_df, "df": friend_request_df.copy(deep = True), "fields": friend_request_fields_to_print}
                                logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["direction"] == "out")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                subscope(scope, log = log)
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                    logPrint('请输入要处理的好友请求的索引（见下面好友请求表的索引列）。一些允许的输入格式：\nPlease submit the indices of friend requests to handle (you may refer to the index column of the friend request table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friend_requests)) if friend_requests[i]["gameName"] == "WordlessMeteor"]')
                    print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
                    log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                    logPrint('变量提示（Variable hints）：\nfriend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()\nfriend_request_df = await sort_friend_request(connection)')
                    while True:
                        handle_str = logInput()
                        if handle_str == "":
                            continue
                        elif handle_str[0] == "0":
                            break
                        elif handle_str == "all":
                            handle_indices = list(range(1, len(friend_request_df)))
                            index_got = True
                            break
                        else:
                            try:
                                tmp = eval(handle_str)
                            except:
                                traceback_info = traceback.format_exc()
                                logPrint(traceback_info)
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            else:
                                if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_request_df):
                                    handle_indices = [tmp]
                                    index_got = True
                                    break
                                elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_request_df), tmp)) and len(tmp) == len(set(tmp)):
                                    handle_indices = tmp
                                    index_got = True
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                elif mode == "3":
                    handle_indices = list(range(1, len(friend_request_df)))
                    index_got = True
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                if index_got:
                    logPrint("您选择了以下%d个好友请求：\nYou selected the following %d friend request(s): " %(len(handle_indices), len(handle_indices)))
                    print(format_df(friend_request_df.loc[handle_indices, friend_request_fields_to_print], print_header = True, print_index = True, reserve_index = True)[0])
                    log.write(format_df(friend_request_df.loc[handle_indices, friend_request_fields_to_print], print_header = True, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                    logPrint("请选择对好友请求的处理：\nPlease decide how to deal with this friend request:\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝/取消（Reject/Cancel）\n3\t拉入聊天黑名单（Block）")
                    while True:
                        method: str = logInput()
                        if method == "":
                            continue
                        elif method[0] == "0":
                            break
                        elif method[0] in {"1", "2", "3"}:
                            for requestId in handle_indices:
                                prefriend_summonerName: str = friend_request_df["gameName"][requestId] + "#" + friend_request_df["tagLine"][requestId]
                                prefriend_puuid: str = friend_request_df["puuid"][requestId]
                                friend_request_direction: str = friend_request_df["direction"][requestId]
                                if method[0] == "1":
                                    if friend_request_direction == "in":
                                        body: dict[str, str] = {"puuid": prefriend_puuid} #选用玩家通用唯一识别码作为请求主体，是考虑到它的不变性（Puuid is chosen as the request body, considering its invariability）
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-chat/v2/friend-requests", data = body)).json() #两个人成为好友，等价于两个人互相承认对方为自己的好友。这话说着有点文绉绉的……说白了就是双方都向对方发起好友申请（If two guys become friends, that means they admit the other to be their friends. This may sound obscure ... In brief, that means the two guys both send friend requests to each other）
                                        logPrint(response)
                                        if response == None:
                                            logPrint("您同意了%s的好友请求。\nYou accepted the friend request from %s." %(prefriend_summonerName, prefriend_summonerName))
                                        else:
                                            logPrint("您未能成功同意%s的好友请求。\nYou failed to accept the friend request from %s." %(prefriend_summonerName, prefriend_summonerName))
                                    else:
                                        logPrint("该操作不适用于当前好友请求。\nThis operation doesn't apply to the current friend request.")
                                elif method[0] == "2":
                                    response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/lol-chat/v2/friend-requests/%s" %(prefriend_puuid))).json()
                                    logPrint(response)
                                    if response == None:
                                        if friend_request_direction == "in":
                                            logPrint("您拒绝了%s的好友请求。\nYou rejected the friend request from %s." %(prefriend_summonerName, prefriend_summonerName))
                                        elif friend_request_direction == "out":
                                            logPrint("您取消了对%s发起的好友请求。\nYou canceled the friend request to %s." %(prefriend_summonerName, prefriend_summonerName))
                                    else:
                                        if friend_request_direction == "in":
                                            logPrint("您未能成功拒绝%s的好友请求。也许您已经处理了该玩家的好友请求，或者该玩家取消了对您发起的好友请求。\nYou failed to reject the friend request from %s. Maybe you've already handled this friend request, or he/she canceled it." %(prefriend_summonerName, prefriend_summonerName))
                                        elif friend_request_direction == "out":
                                            logPrint("您未能成功取消对%s发起的好友请求。也许该玩家已经处理了您的好友请求，或者您取消了对该玩家发起的好友请求。\nYou failed to cancel the friend request to %s. Maybe he/she's already handled your friend request, or you canceled it." %(prefriend_summonerName, prefriend_summonerName))
                                else:
                                    logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.)' %(prefriend_summonerName, prefriend_summonerName))
                                    block_confirm_str: str = logInput()
                                    block_confirm: bool = bool(block_confirm_str == "block")
                                    if block_confirm:
                                        body: dict[str, str] = {"puuid": prefriend_puuid}
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-chat/v1/blocked-players", data = body)).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("您已将%s拉入聊天黑名单。\nYou've blocked %s." %(prefriend_summonerName, prefriend_summonerName))
                                        else:
                                            logPrint("您未能成功将%s拉入聊天黑名单。可能TA已经在您的聊天黑名单里了。\nYou failed to block %s. Maybe he/she's been blocked some time before." %(prefriend_summonerName, prefriend_summonerName))
                            logPrint("请选择对好友请求的处理：\nPlease decide how to deal with this friend request:\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝/取消（Reject/Cancel）\n3\t拉入聊天黑名单（Block）")
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                friend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
                if len(friend_requests) == 0:
                    logPrint("您尚未发送或收到任何好友请求。\nYou haven't sent or received any friend request.")
                    break
                else:
                    logPrint("您的好友请求如下：\nYour friend requests:")
                    friend_request_df = await sort_friend_request(connection)
                    friend_request_fields_to_print = ["gameName", "tagLine", "direction", "icon title"]
                    print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
                    log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], width_exceed_ask = False, direct_print = False, print_header = True, print_index = True, start_index = 1)[0] + "\n")
                    logPrint("请选择好友请求处理模式：\nPlease select a mode to handle friend requests:\n0\t返回上一层（Return to the last step）\n1\t单个处理（Single）\n2\t批量处理（In batches）\n3\t全部处理（All）")

async def move_group(connection: Connection) -> None:
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    if len(friends) == 0:
        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
    else:
        logPrint("您的好友分组信息如下：\nFriend group distribution:")
        friend_summonerNames: list[str] = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends)) #这三个列表一定是一一对应的，且列表元素无重复（These three lists must follow one-to-one correspondence, and there must be no repetitive elements in them all）
        friend_summonerIds: list[int] = list(map(lambda x: x["summonerId"], friends))
        friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
        friend_pids: list[str] = list(map(lambda x: x["pid"], friends))
        friend_hovercard_fields_to_print: list[str] = ["name", "gameName", "gameTag", "groupId", "groupName"]
        friend_hovercard_df: pandas.DataFrame = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
        logPrint("请选择移动模式：\nPlease select a moving mode:\n0\t返回上一层（Return to the last step）\n1\t单个移动（Single）\n2\t批量移动（In batches）\n3\t全部移动（All）")
        while True:
            index_got: bool = False
            mode: str = logInput()
            if mode == "":
                continue
            elif mode == "0":
                break
            elif mode == "1":
                logPrint("请输入要移动的好友索引或者名称：\nPlease enter the index or name of the friend to move:")
                while True:
                    move_str: str = logInput()
                    if move_str == "":
                        continue
                    else:
                        try:
                            friend_index: int = int(move_str) - 1
                        except ValueError:
                            friend_summonerName: str = move_str
                            if friend_summonerName in friend_summonerNames:
                                friend_index = friend_summonerNames.index(friend_summonerName)
                            elif friend_summonerName in set(map(str, friend_summonerIds)):
                                friend_index = friend_summonerIds.index(int(friend_summonerName))
                            elif friend_summonerName in friend_puuids:
                                friend_index = friend_puuids.index(friend_summonerName)
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                        else:
                            if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                break
                            elif not friend_index in range(len(friends)):
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                    move_indices: list[int] = [friend_index]
                    index_got = True
                    break
            elif mode == "2":
                logPrint("请选择您输入要移动的好友信息的方式：\nPlease select a method of inputting the information of your friends to be moved to other groups:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                while True:
                    method: str = logInput()
                    if method == "":
                        continue
                    elif method[0] == "0":
                        break
                    elif method[0] == "1":
                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope: dict[str, Any] = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('请输入要移动的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to move (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                        friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
                        logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                        while True:
                            move_str = logInput()
                            if move_str == "":
                                continue
                            elif move_str[0] == "0":
                                break
                            elif move_str == "all":
                                move_indices = list(range(len(friends)))
                                index_got = True
                                break
                            else:
                                try:
                                    tmp = eval(move_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_hovercard_df):
                                        move_indices = [tmp]
                                        index_got = True
                                        break
                                    elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), tmp)) and len(tmp) == len(set(tmp)):
                                        move_indices = list(map(lambda x: x - 1, tmp))
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif method[0] == "2":
                        logPrint('''请输入要移动的好友的召唤师名。每个好友的召唤师名格式为{玩家名称}#{名称编号}。输入“-1”以结束输入。\nPlease submit the names of the friends to be moved. Each friend's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)''')
                        move_indices = []
                        while True:
                            friend_summonerName = logInput()
                            if friend_summonerName == "":
                                continue
                            elif friend_summonerName == "0":
                                index_got = False
                                break
                            elif friend_summonerName == "-1":
                                break
                            else:
                                try:
                                    tmp = eval(friend_summonerName)
                                except:
                                    friend_summonerName_list: list[Any] = [friend_summonerName]
                                else:
                                    if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (str, int)), tmp)):
                                        friend_summonerName_list = tmp
                                    else:    
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                for friend_summonerName_iter in friend_summonerName_list:
                                    if friend_summonerName_iter in friend_summonerNames:
                                        friend_index = friend_summonerNames.index(friend_summonerName_iter)
                                    elif friend_summonerName_iter in friend_summonerIds:
                                        friend_index = friend_summonerIds.index(friend_summonerName_iter)
                                    elif friend_summonerName_iter in set(map(str, friend_summonerIds)):
                                        friend_index = friend_summonerIds.index(int(friend_summonerName_iter))
                                    elif friend_summonerName_iter in friend_puuids:
                                        friend_index = friend_puuids.index(friend_summonerName_iter)
                                    else:
                                        logPrint("%s不是一个合法的召唤师名、召唤师序号或者玩家通用唯一识别码。\n%s isn't a legal summoner name, summonerId or puuid." %(friend_summonerName_iter, friend_summonerName_iter))
                                        continue
                                    if not friend_index in move_indices:
                                        move_indices.append(friend_index)
                                        index_got = True
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    if index_got:
                        break
                    logPrint("请选择您输入要移动的好友信息的方式：\nPlease select a method of inputting the information of your friends to be moved to other groups:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
            elif mode == "3":
                move_indices = list(range(len(friends)))
                index_got = True
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if index_got:
                logPrint("您选择了以下%d名好友：\nYou selected the following %d friend(s):" %(len(move_indices), len(move_indices)))
                print(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, move_indices)), friend_hovercard_fields_to_print], print_index = True, reserve_index = True)[0])
                log.write(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, move_indices)), friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                logPrint("请选择目标分组：\nPlease select a target group:")
                friend_groups: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                friend_group_df: pandas.DataFrame = await sort_friend_group(connection)
                friend_group_df_to_print: pandas.DataFrame = friend_group_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
                print(format_df(friend_group_df_to_print)[0])
                log.write(format_df(friend_group_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n")
                while True:
                    target_groupId: str = logInput()
                    if target_groupId == "":
                        continue
                    elif target_groupId == "-1":
                        logPrint("已取消本次移动。\nThis move has been cancelled.")
                        break
                    elif target_groupId in set(map(str, friend_group_df["id"][1:])):
                        for friend_index in sorted(set(move_indices)):
                            group: dict[str, Any] = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{target_groupId}")).json()
                            move_summonerName: str = friend_summonerNames[friend_index]
                            pid: str = friend_pids[friend_index]
                            note: str = friends[friend_index]["note"]
                            body: dict[str, int | str] = {"groupId": group["id"], "note": note}
                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-chat/v1/friends/{pid}", data = body)).json()
                            logPrint(response)
                            target_groupName: str = group["name"]
                            if response == None:
                                logPrint("您的好友%s已移动到%s分组中。\nYour friend %s has been moved to the group %s." %(move_summonerName, target_groupName, move_summonerName, target_groupName))
                            else:
                                if response["httpStatus"] == 404:
                                    logPrint("您的好友%s未能移动到%s分组中。请检查TA是否是您的好友。\nYour friend %s failed to be moved to the group %s. Please check if he/she's still your friend." %(move_summonerName, target_groupName, move_summonerName, target_groupName))
                                else:
                                    logPrint("您的好友%s未能移动到%s分组中。\nYour friend %s failed to be moved to the group %s." %(move_summonerName, target_groupName, move_summonerName, target_groupName))
                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                if len(friends) == 0:
                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                    break
                else:
                    logPrint("您的好友分组信息如下：\nFriend group distribution:")
                    friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                    friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                    friend_puuids = list(map(lambda x: x["puuid"], friends))
                    friend_pids = list(map(lambda x: x["pid"], friends))
                    friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
            logPrint("请选择移动模式：\nPlease select a moving mode:\n0\t返回上一层（Return to the last step）\n1\t单个移动（Single）\n2\t批量移动（In batches）\n3\t全部移动（All）")

async def edit_friend_note(connection: Connection) -> None:
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    if len(friends) == 0:
        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
    else:
        logPrint("请选择要修改备注的好友：\nPlease select a friend to modify note:")
        friend_summonerNames: list[str] = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
        friend_summonerIds: list[int] = list(map(lambda x: x["summonerId"], friends))
        friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
        friend_pids: list[str] = list(map(lambda x: x["pid"], friends))
        friend_hovercard_df: pandas.DataFrame = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
        while True:
            noteChange_str: str = logInput()
            if noteChange_str == "":
                continue
            else:
                try:
                    friend_index: int = int(noteChange_str) - 1
                except ValueError:
                    friend_summonerName = noteChange_str
                    if friend_summonerName in friend_summonerNames:
                        friend_index = friend_summonerNames.index(friend_summonerName)
                    elif friend_summonerName in set(map(str, friend_summonerIds)):
                        friend_index = friend_summonerIds.index(int(friend_summonerName))
                    elif friend_summonerName in friend_puuids:
                        friend_index = friend_puuids.index(friend_summonerName)
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                else:
                    if friend_index == -1:
                        break
                    elif not friend_index in range(len(friend_hovercard_df)):
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                pid: str = friend_pids[friend_index]
                groupId: int = friends[friend_index]["groupId"]
                logPrint("请输入新备注：\nPlease enter the new note:")
                note: str = logInput()
                body: dict[str, int | str] = {"groupId": groupId, "note": note}
                response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-chat/v1/friends/{pid}", data = body)).json()
                logPrint(response)
                if response == None:
                    logPrint("为%s添加/修改备注成功。\nAdd/Edit note for %s successfully.\n旧备注（Old note）：%s\n新备注（New note）：%s\n" %(friend_summonerNames[friend_index], friend_summonerNames[friend_index], friends[friend_index]["note"], note))
                else:
                    logPrint("为%s添加/修改备注失败。\nFailed to add / modify note for %s." %(friend_summonerNames[friend_index], friend_summonerNames[friend_index]))
            friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
            if len(friends) == 0:
                logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
            else:
                logPrint("请选择要修改备注的好友：\nPlease select a friend to modify note:")
                friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                friend_puuids = list(map(lambda x: x["puuid"], friends))
                friend_pids = list(map(lambda x: x["pid"], friends))
                friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)

async def remove_friend(connection: Connection) -> None:
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    if len(friends) == 0:
        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
    else:
        logPrint("您的好友信息如下：\nYour friends:")
        friend_summonerNames: list[str] = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
        friend_summonerIds: list[int] = list(map(lambda x: x["summonerId"], friends))
        friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
        friend_pids: list[str] = list(map(lambda x: x["pid"], friends))
        friend_hovercard_fields_to_print: list[str] = ["name", "gameName", "gameTag", "groupId", "groupName"]
        friend_hovercard_df: pandas.DataFrame = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
        logPrint("请选择删除模式：\nPlease select an unfriending mode:\n0\t返回上一层（Return to the last step）\n1\t单个删除（Single）\n2\t批量删除（In batches）\n3\t全部删除（All）")
        while True:
            index_got: bool = False
            mode: str = logInput()
            if mode == "":
                continue
            elif mode == "0":
                break
            elif mode == "1":
                logPrint("请输入要删除的好友索引或者名称：\nPlease enter the index or name of the friend to unfriend:")
                while True:
                    unfriend_str: str = logInput()
                    if unfriend_str == "":
                        continue
                    else:
                        try:
                            friend_index: int = int(unfriend_str) - 1
                        except ValueError:
                            friend_summonerName: str = unfriend_str
                            if friend_summonerName in friend_summonerNames:
                                friend_index = friend_summonerNames.index(friend_summonerName)
                            elif friend_summonerName in set(map(str, friend_summonerIds)):
                                friend_index = friend_summonerIds.index(int(friend_summonerName))
                            elif friend_summonerName in friend_puuids:
                                friend_index = friend_puuids.index(friend_summonerName)
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                        else:
                            if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                break
                            elif not friend_index in range(len(friends)):
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                    unfriend_indices: list[int] = [friend_index]
                    index_got = True
                    break
            elif mode == "2":
                logPrint("请选择您输入要删除的好友信息的方式：\nPlease select a method of inputting the information of your friends to be removed:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                while True:
                    method: str = logInput()
                    if method == "":
                        continue
                    elif method[0] == "0":
                        break
                    elif method[0] == "1":
                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('请输入要删除的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to remove (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                        friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
                        logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                        while True:
                            remove_str: str = logInput()
                            if remove_str == "":
                                continue
                            elif remove_str[0] == "0":
                                break
                            elif remove_str == "all":
                                unfriend_indices = list(range(len(friends)))
                                index_got = True
                                break
                            else:
                                try:
                                    tmp = eval(remove_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_hovercard_df):
                                        unfriend_indices = [tmp]
                                        index_got = True
                                        break
                                    elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), tmp)) and len(tmp) == len(set(tmp)):
                                        unfriend_indices = tmp
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif method[0] == "2":
                        logPrint('''请输入要删除的好友的召唤师名。每个好友的召唤师名格式为{玩家名称}#{名称编号}。输入“-1”以结束输入。\nPlease submit the names of the friends to be unfriended. Each friend's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)''')
                        unfriend_indices = []
                        while True:
                            friend_summonerName = logInput()
                            if friend_summonerName == "":
                                continue
                            elif friend_summonerName == "0":
                                index_got = False
                                break
                            elif friend_summonerName == "-1":
                                break
                            else:
                                try:
                                    tmp = eval(friend_summonerName)
                                except:
                                    friend_summonerName_list: list[Any] = [friend_summonerName]
                                else:
                                    if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (str, int)), tmp)):
                                        friend_summonerName_list = tmp
                                    else:    
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                for friend_summonerName_iter in friend_summonerName_list:
                                    if friend_summonerName_iter in friend_summonerNames:
                                        friend_index = friend_summonerNames.index(friend_summonerName_iter)
                                    elif friend_summonerName_iter in friend_summonerIds:
                                        friend_index = friend_summonerIds.index(friend_summonerName_iter)
                                    elif friend_summonerName_iter in set(map(str, friend_summonerIds)):
                                        friend_index = friend_summonerIds.index(int(friend_summonerName_iter))
                                    elif friend_summonerName_iter in friend_puuids:
                                        friend_index = friend_puuids.index(friend_summonerName_iter)
                                    else:
                                        logPrint("%s不是一个合法的召唤师名、召唤师序号或者玩家通用唯一识别码。\n%s isn't a legal summoner name, summonerId or puuid." %(friend_summonerName_iter, friend_summonerName_iter))
                                        continue
                                    if not friend_index in unfriend_indices:
                                        unfriend_indices.append(friend_index)
                                        index_got = True
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    if index_got:
                        break
                    logPrint("请选择您输入要删除的好友信息的方式：\nPlease select a method of inputting the information of your friends to be removed:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
            elif mode == "3":
                unfriend_indices = list(range(len(friends)))
                index_got = True
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if index_got:
                unfriend_summonerNames: list[str] = list(map(lambda x: friend_summonerNames[x], unfriend_indices))
                logPrint('与%s解除好友关系：\n- 将该玩家从你的好友列表移除\n- 清除和该玩家的任何现存的会话\nUnfriending %s: \n- Removes them from your friends list\n- Clears any existing conversations with them\n\n您确定要与该玩家解除好友关系吗？（输入“remove”以确认，否则取消。）\nDo you really want to unfriend this player? (Submit "remove" to confirm, otherwise cancel unfriending.)' %("、".join(unfriend_summonerNames), ", ".join(unfriend_summonerNames)))
                unfriend_confirm_str: str = logInput()
                unfriend_confirm: bool = unfriend_confirm_str == "remove"
                for friend_index in unfriend_indices:
                    pid: str = friend_pids[friend_index]
                    unfriend_summonerName: str = friend_summonerNames[friend_index]
                    if unfriend_confirm:
                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/lol-chat/v1/friends/{pid}")).json()
                        logPrint(response)
                        if response == None:
                            logPrint("您已与%s解除好友关系。\nYou've unfriended %s successfully." %(unfriend_summonerName, unfriend_summonerName))
                        else:
                            if response["httpStatus"] == 404:
                                logPrint("您未能成功与%s解除好友关系。可能你们已经不是好友了。\nYou failed to unfriend %s. Maybe you're not friends already." %(unfriend_summonerName, unfriend_summonerName))
                            else:
                                logPrint("您未能成功与%s解除好友关系。\nYou failed to unfriend %s." %(unfriend_summonerName, unfriend_summonerName))
                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                if len(friends) == 0:
                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                    break
                else:
                    logPrint("您的好友信息如下：\nYour friends:")
                    friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                    friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                    friend_puuids = list(map(lambda x: x["puuid"], friends))
                    friend_pids = list(map(lambda x: x["pid"], friends))
                    friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
            logPrint("请选择删除模式：\nPlease select an unfriending mode:\n0\t返回上一层（Return to the last step）\n1\t单个删除（Single）\n2\t批量删除（In batches）\n3\t全部删除（All）")

async def block_friend(connection: Connection) -> None:
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    if len(friends) == 0:
        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
    else:
        logPrint("您的好友信息如下：\nYour friends:")
        friend_summonerNames: list[str] = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
        friend_summonerIds: list[int] = list(map(lambda x: x["summonerId"], friends))
        friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
        friend_pids: list[str] = list(map(lambda x: x["pid"], friends))
        friend_hovercard_fields_to_print: list[str] = ["name", "gameName", "gameTag", "groupId", "groupName"]
        friend_hovercard_df: pandas.DataFrame = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
        logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t全部拉黑（All）")
        while True:
            index_got: bool = False
            mode: str = logInput()
            if mode == "":
                continue
            elif mode == "0":
                break
            elif mode == "1":
                logPrint("请输入要拉黑的好友索引或者名称：\nPlease enter the index or name of the friend to block:")
                while True:
                    block_str: str = logInput()
                    if block_str == "":
                        continue
                    else:
                        try:
                            friend_index: int = int(block_str) - 1
                        except ValueError:
                            friend_summonerName: str = block_str
                            if friend_summonerName in friend_summonerNames:
                                friend_index = friend_summonerNames.index(friend_summonerName)
                            elif friend_summonerName in set(map(str, friend_summonerIds)):
                                friend_index = friend_summonerIds.index(int(friend_summonerName))
                            elif friend_summonerName in friend_puuids:
                                friend_index = friend_puuids.index(friend_summonerName)
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                        else:
                            if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                break
                            elif not friend_index in range(len(friends)):
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                    block_indices: list[int] = [friend_index]
                    index_got = True
                    break
            elif mode == "2":
                logPrint("请选择您输入要拉黑的好友信息的方式：\nPlease select a method of inputting the information of your friends to be blocked:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                while True:
                    method: str = logInput()
                    if method == "":
                        continue
                    elif method[0] == "0":
                        break
                    elif method[0] == "1":
                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('请输入要拉黑的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to block (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                        friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
                        logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                        while True:
                            block_str: str = logInput()
                            if block_str == "":
                                continue
                            elif block_str[0] == "0":
                                break
                            elif block_str == "all":
                                block_indices = list(range(len(friends)))
                                index_got = True
                                break
                            else:
                                try:
                                    tmp = eval(block_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_hovercard_df):
                                        block_indices = [tmp]
                                        index_got = True
                                        break
                                    elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), tmp)) and len(tmp) == len(set(tmp)):
                                        block_indices = list(map(lambda x: x - 1, block_indices))
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif method[0] == "2":
                        logPrint('''请输入要拉黑的好友的召唤师名。每个好友的召唤师名格式为{玩家名称}#{名称编号}。输入“-1”以结束输入。\nPlease submit the names of the friends to be blocked. Each friend's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)''')
                        block_indices = []
                        while True:
                            friend_summonerName = logInput()
                            if friend_summonerName == "":
                                continue
                            elif friend_summonerName == "0":
                                index_got = False
                                break
                            elif friend_summonerName == "-1":
                                break
                            else:
                                try:
                                    tmp = eval(friend_summonerName)
                                except:
                                    friend_summonerName_list: list[Any] = [friend_summonerName]
                                else:
                                    if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (str, int)), tmp)):
                                        friend_summonerName_list = tmp
                                    else:    
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                for friend_summonerName_iter in friend_summonerName_list:
                                    if friend_summonerName_iter in friend_summonerNames:
                                        friend_index = friend_summonerNames.index(friend_summonerName_iter)
                                    elif friend_summonerName_iter in friend_summonerIds:
                                        friend_index = friend_summonerIds.index(friend_summonerName_iter)
                                    elif friend_summonerName_iter in set(map(str, friend_summonerIds)):
                                        friend_index = friend_summonerIds.index(int(friend_summonerName_iter))
                                    elif friend_summonerName_iter in friend_puuids:
                                        friend_index = friend_puuids.index(friend_summonerName_iter)
                                    else:
                                        logPrint("%s不是一个合法的召唤师名、召唤师序号或者玩家通用唯一识别码。\n%s isn't a legal summoner name, summonerId or puuid." %(friend_summonerName_iter, friend_summonerName_iter))
                                        continue
                                    if not friend_index in block_indices:
                                        block_indices.append(friend_index)
                                        index_got = True
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    if index_got:
                        break
                    logPrint("请选择您输入要拉黑的好友信息的方式：\nPlease select a method of inputting the information of your friends to be blocked to other groups:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
            elif mode == "3":
                block_indices = list(range(len(friends)))
                index_got = True
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if index_got:
                logPrint("您选择了以下%d名好友：\nYou selected the following %d friends:" %(len(block_indices), len(block_indices)))
                print(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, block_indices)), friend_hovercard_fields_to_print], print_index = True, reserve_index = True)[0])
                log.write(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, block_indices)), friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                block_summonerNames: list[str] = list(map(lambda x: friend_summonerNames[x], block_indices))
                logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.' %("、".join(block_summonerNames), ", ".join(block_summonerNames)))
                block_confirm_str: str = logInput()
                block_confirm: bool = block_confirm_str == "block"
                for friend_index in block_indices:
                    pid: str = friend_pids[friend_index]
                    block_summonerName: str = friend_summonerNames[friend_index]
                    if block_confirm:
                        body: dict[str, str] = {"puuid": friend_puuids[friend_index]}
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-chat/v1/blocked-players", data = body)).json()
                        logPrint(response)
                        if response == None:
                            logPrint("%s已被拉入聊天黑名单。你再也不会看到TA的在线状态或是收到来自TA的信息了。\n%s has been blocked. You will no longer see them online or receive their messages." %(block_summonerName, block_summonerName))
                        else:
                            if response["httpStatus"] == 400:
                                logPrint("您未能成功将%s拉入聊天黑名单。也许TA已经在其中了。\nYou failed to block %s. Maybe he/she's already in it." %(block_summonerName, block_summonerName))
                            else:
                                logPrint("您未能成功将%s拉入聊天黑名单。\nYou failed to block %s." %(block_summonerName, block_summonerName))
                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                if len(friends) == 0:
                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                    break
                else:
                    logPrint("您的好友信息如下：\nYour friends:")
                    friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                    friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                    friend_puuids = list(map(lambda x: x["puuid"], friends))
                    friend_pids = list(map(lambda x: x["pid"], friends))
                    friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
            logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t全部拉黑（All）")

async def manage_friend(connection: Connection) -> None:
    logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
    while True:
        action: str = logInput()
        if action == "":
            continue
        elif action[0] == "0":
            break
        elif action[0] == "1":
            await add_friend(connection)
        elif action[0] == "2":
            await manage_friend_request(connection)
        elif action[0] == "3":
            await move_group(connection)
        elif action[0] == "4":
            await edit_friend_note(connection)
        elif action[0] == "5":
            await remove_friend(connection)
        elif action[0] == "6":
            await block_friend(connection)
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            continue
        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")

async def invite(connection: Connection) -> None:
    global TFTBasic_got, session, TFTAugments
    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase == "Lobby":
        friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
        friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupId", "groupName"]
        if len(friends) == 0:
            logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
            friend_hovercard_df: pandas.DataFrame = await sort_friend_hovercard_simple(connection)
        else:
            logPrint("您的好友信息如下：\nYour friends:")
            friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
        logPrint("请选择邀请模式：\nPlease select an inviting mode:\n0\t返回上一层（Return to the last step）\n1\t单个邀请（Single）\n2\t批量邀请（In batches）\n3\t全部在线好友邀请（All available friends）\n4\t按组邀请（By group）")
        while True:
            invitee_obtained: bool = False
            mode: str = logInput()
            if mode == "":
                continue
            elif mode == "0":
                break
            elif mode == "1":
                logPrint("请输入要邀请的好友索引或者玩家名称：\nPlease enter the invitee's friend index or summoner name:")
                while True:
                    invite_str: str = logInput()
                    if invite_str == "":
                        continue
                    else:
                        try:
                            friend_index = int(invite_str) - 1
                        except ValueError:
                            invitee_summonerName: str = invite_str
                            invitee_info: dict[str, Any] = await get_info(connection, invitee_summonerName)
                            if invitee_info["info_got"]:
                                if invitee_info["selfInfo"]:
                                    logPrint("您已经在房间内了。\nYou're already in the lobby.")
                                else:
                                    invitee_summonerIds: list[int] = [invitee_info["body"]["summonerId"]]
                                    invitee_obtained = True
                                    logPrint(invitee_info["body"])
                                    break
                            else:
                                logPrint(invitee_info["message"])
                        else:
                            if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                break
                            elif not friend_index in range(len(friends)):
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            else:
                                invitee_summonerIds = [friends[friend_index]["summonerId"]]
                                invitee_obtained = True
                                break
            elif mode == "2":
                invitee_summonerIds = []
                logPrint("请选择您输入要邀请的玩家信息的方式：\nPlease select a method of inputting the information of invitees:\n0\t返回上一层（Return to the last step）\n1\t好友索引（By friend index）\n2\t近期一起玩过的玩家索引（By recently played summoner index）\n3\t好友请求索引（By friend request index）\n4\t玩家召唤师名（By player summonerName）")
                while True:
                    method = logInput()
                    if method == "":
                        continue
                    elif method[0] == "0":
                        break
                    elif method[0] == "1":
                        if len(friends) == 0:
                            logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                            break
                        else:
                            logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                            draft_str = logInput()
                            draft = bool(draft_str)
                            if draft:
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                while True:
                                    draft_option = logInput()
                                    if draft_option == "":
                                        continue
                                    elif draft_option[0] == "0":
                                        break
                                    elif draft_option[0] == "1":
                                        scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                        logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                        subscope(scope, log = log)
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            logPrint('请输入要邀请的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to invite (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                            friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
                            logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                            while True:
                                invite_str = logInput()
                                if invite_str == "":
                                    continue
                                elif invite_str[0] == "0":
                                    break
                                elif invite_str == "all":
                                    invitee_summonerIds = list(map(lambda x: x["summonerId"], friends))
                                    invitee_obtained = True
                                    break
                                else:
                                    try:
                                        tmp = eval(invite_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_hovercard_df):
                                            invitee_summonerIds = friend[tmp - 1]["summonerId"]
                                            invitee_obtained = True
                                            break
                                        elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), tmp)) and len(tmp) == len(set(tmp)):
                                            invitee_summonerIds = list(map(lambda x: friends[x - 1]["summonerId"], tmp))
                                            invitee_obtained = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif method[0] == "2":
                        #仅在需要云顶之弈基础信息时才去获取，因为这个步骤是决速步骤（Only when TFT basic data are required will the program get it, because this step is rate-determining）
                        if not TFTBasic_got:
                            ##云顶之弈基础信息（TFT basic）
                            logPrint("正在初始化云顶之弈强化符文信息……\nInitializing TFT augment data ...")
                            region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
                            locale: str = region_locale["locale"]
                            URLPatch = "pbe" if platformId == "PBE1" or platformId == "PBE" else "latest"
                            TFTBasic_url: str = "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(URLPatch, locale.lower())
                            source, status, session = requestUrl("GET", TFTBasic_url, session = session, log = log)
                            if status != 200:
                                if status == 404:
                                    logPrint("云顶之弈基础信息获取失败！请检查以下链接的可用性。\nTFT basic information capture failure! Please check the URL availability. The program will skip this map.\n%s" %(TFTBasic_url))
                                else:
                                    logPrint("云顶之弈基础信息获取失败！请检查系统网络状况和代理设置。\nTFT basic information capture failure! Please check the system network condition and proxy configuration.")
                                TFTBasic_source: dict[str, Any] = {"items": []}
                            else:
                                TFTBasic_source = source.json()
                            TFTAugments = {item["apiName"]: item for item in TFTBasic_source["items"]}
                            TFTBasic_got = True
                        logPrint("您想要获取简略信息还是详细信息？（输入任意非空字符串以获取详细信息，否则获取简略信息。）\nDo you want to get brief or detailed information? (Submit any non-empty string to get detailed information, or null to get brief information.)")
                        lol_sgp_str: str = logInput()
                        lol_sgp: bool = bool(lol_sgp_str)
                        recent_player_dfs: dict[str, pandas.DataFrame] = await get_recent_players(connection, search_mode = 1, lol_sgp = lol_sgp)
                        recent_LoLPlayer_df: pandas.DataFrame = recent_player_dfs["LoL"]
                        recent_TFTPlayer_df: pandas.DataFrame = recent_player_dfs["TFT"]
                        recent_LoLPlayer_df = recent_LoLPlayer_df[(recent_LoLPlayer_df["puuid"] != current_info["puuid"]) & (recent_LoLPlayer_df["puuid"] != BOT_UUID)] #邀请玩家，当然指的是不包括自己的人类玩家（Of course, the players invited are human players but not himself / herself）
                        recent_TFTPlayer_df = recent_TFTPlayer_df[(recent_TFTPlayer_df["puuid"] != current_info["puuid"]) & (recent_TFTPlayer_df["puuid"] != BOT_UUID)]
                        recent_LoLPlayer_df.reset_index(drop = True, inplace = True)
                        recent_TFTPlayer_df.reset_index(drop = True, inplace = True)
                        if lol_sgp:
                            recent_LoLPlayer_fields_to_print: list[str] = ["riotIdGameName", "riotIdTagline", "gameModeName", "queueId", "champion_name", "championName", "K/D/A", "isAlly"]
                        else:
                            recent_LoLPlayer_fields_to_print: list[str] = ["gameName", "tagLine", "gameModeName", "queueId", "champion_name", "champion_alias", "K/D/A", "isAlly"]
                        recent_TFTPlayer_fields_to_print: list[str] = ["riotIdGameName", "riotIdTagline", "gameModeName", "queue_id", "last_round_format", "time_eliminated_norm", "placement"]
                        logPrint("是否需要对近期一起玩过的玩家取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current recently played summoner data? (Submit any non-empty string to make a draft, or null to input the recently played summoner index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": recent_player_dfs.copy(), "fields": {"LoL": recent_LoLPlayer_fields_to_print, "TFT": recent_TFTPlayer_fields_to_print}}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df["LoL"][(df["LoL"]["gameName"] == "WordlessMeteor") & (df["LoL"]["gameTag"] == "5071")].loc[1:, fields["LoL"]])[0])\nprint(format_df(df["LoL"].loc[[i for i in range(len(df["LoL"])) if df["LoL"]["totalDamageDealtToChampions"] / sum(df["LoL"][(df["LoL"]["gameId"] == df["LoL"].loc[i, "gameId"]) & (df["LoL"]["isAlly"] == df["LoL"].loc[i, "isAlly"])]["totalDamageDealtToChampions"] > 1 / 3)], fields["LoL"]])[0])\nprint(format_df(df["LoL"].loc[[i for i in range(len(df)) if df["visionScore"] / (int(df["gameDuration"].split(":")[0]) + int(df["gameDuration"].split(":")[1]) / 6) > 2.5], fields["LoL"]])[0])\nprint(format_df(df["TFT"][(df["TFT"]["gameName"] == "WordlessMeteor") & (df["TFT"]["gameTag"] == "5071")].loc[1:, fields["TFT"]])[0])\nprint(format_df(df["TFT"][df["TFT"]["placement"] == 1].loc[1:, fields["TFT"]])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint("请选择您要邀请的近期一起玩过的玩家类型：\nPlease select a type of players:\n0\t返回上一层（Return to the last step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）\n3\t英雄联盟和云顶之弈（LoL and TFT）")
                        while True:
                            product_option: str = logInput()
                            if product_option == "":
                                continue
                            elif product_option[0] == "0":
                                break
                            elif product_option[0] in {"1", "2", "3"}:
                                invitee_summonerIds: list[int] = []
                                if product_option[0] == "1" or product_option[0] == "3":
                                    logPrint('请输入要邀请的英雄联盟玩家的索引（见下面近期一起玩过的玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of recently played LoL summoners to invite (you may refer to the index column of the recently played summoner table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(recent_LoLPlayer_df)) if recent_LoLPlayer_df.loc[i, "gameName"] == "WordlessMeteor"]')
                                    print(format_df(recent_LoLPlayer_df.loc[1:20, recent_LoLPlayer_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(recent_LoLPlayer_df.loc[1:20, recent_LoLPlayer_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint('变量提示（Variable hints）：\nrecent_player_dfs = await get_recent_players(connection, search_mode = 1)\nrecent_LoLPlayer_df = recent_player_dfs["LoL"]')
                                    while True:
                                        invite_str = logInput()
                                        if invite_str == "":
                                            continue
                                        elif invite_str[0] == "0":
                                            invitee_obtained = False
                                            if product_option[0] != "3":
                                                logPrint("请选择您要邀请的近期一起玩过的玩家类型：\nPlease select a type of players:\n0\t返回上一层（Return to the last step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）\n3\t英雄联盟和云顶之弈（LoL and TFT）")
                                            break
                                        elif invite_str == "all":
                                            invitee_summonerIds += list(recent_LoLPlayer_df["summonerId"][1:])
                                            invitee_obtained = True
                                            break
                                        else:
                                            try:
                                                tmp = eval(invite_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            else:
                                                if isinstance(tmp, int) and tmp > 0 and tmp < len(recent_LoLPlayer_df):
                                                    invitee_summonerIds += [recent_LoLPlayer_df["summonerId"][tmp]]
                                                    invitee_obtained = True
                                                    break
                                                elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(recent_LoLPlayer_df), tmp)) and len(tmp) == len(set(tmp)):
                                                    invitee_summonerIds += list(recent_LoLPlayer_df["summonerId"][tmp])
                                                    invitee_obtained = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if product_option[0] == "2" or product_option[0] == "3":
                                    logPrint('请输入要邀请的云顶之弈玩家的索引（见下面近期一起玩过的玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of recently played TFT summoners to invite (you may refer to the index column of the recently played summoner table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(recent_LoLPlayer_df)) if recent_LoLPlayer_df.loc[i, "gameName"] == "WordlessMeteor"]')
                                    print(format_df(recent_TFTPlayer_df.loc[1:20, recent_TFTPlayer_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(recent_TFTPlayer_df.loc[1:20, recent_TFTPlayer_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint('变量提示（Variable hints）：\nrecent_player_dfs = await get_recent_players(connection, search_mode = 1)\nrecent_TFTPlayer_df = recent_player_dfs["TFT"]')
                                    invitee_puuids: list[str] = []
                                    while True:
                                        invite_str = logInput()
                                        if invite_str == "":
                                            continue
                                        elif invite_str[0] == "0":
                                            invitee_obtained = False
                                            logPrint("请选择您要邀请的近期一起玩过的玩家类型：\nPlease select a type of players:\n0\t返回上一层（Return to the last step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）\n3\t英雄联盟和云顶之弈（LoL and TFT）")
                                            break
                                        elif invite_str == "all":
                                            invitee_puuids += list(recent_TFTPlayer_df["puuid"][1:])
                                            invitee_obtained = True
                                            break
                                        else:
                                            try:
                                                tmp = eval(invite_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            else:
                                                if isinstance(tmp, int) and tmp > 0 and tmp < len(recent_TFTPlayer_df):
                                                    invitee_puuids += [recent_TFTPlayer_df["puuid"][tmp]]
                                                    invitee_obtained = True
                                                    break
                                                elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(recent_TFTPlayer_df), player_indices)) and len(player_indices) == len(set(player_indices)):
                                                    invitee_puuids += list(recent_TFTPlayer_df["puuid"][tmp])
                                                    invitee_obtained = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    for invitee_puuid in invitee_puuids:
                                        invitee_info = await get_info(connection, invitee_puuid)
                                        if invitee_info["info_got"]:
                                            invitee_summonerIds.append(invitee_info["body"]["summonerId"])
                                        else:
                                            logPrint(invitee_info["message"])
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if invitee_obtained: #对输入的召唤师去重（Remove the redundancy in the input summoners）
                                tmp_set: set[int] = set()
                                tmp_list: list[int] = []
                                for invitee_summonerId in invitee_summonerIds:
                                    if not invitee_summonerId in tmp_set:
                                        tmp_set.add(invitee_summonerId)
                                        tmp_list.append(invitee_summonerId)
                                invitee_summonerIds = tmp_list[:]
                                break
                    elif method[0] == "3": #部分主播短时间内（48小时）添加好友过于频繁导致操作受限，即可使用该方法，但是需要告知观众取消勾选“只接受好友游戏邀请”（Some hosts may be restricted to add any summoner as friend because they add too many friends with a short time period (48 hours, exactly). In that case they can use this method to invite them to lobby, but they need to inform the audience that they should tick off "Allow game invites only from friends"）
                        friend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
                        if len(friend_requests) == 0:
                            logPrint("您尚未发送或收到任何好友请求。\nYou haven't sent or received any friend request.")
                        else:
                            logPrint("您的好友请求如下：\nYour friend requests:")
                            friend_request_df = await sort_friend_request(connection)
                            friend_request_fields_to_print = ["gameName", "tagLine", "direction", "icon title"]
                            print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
                            log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], width_exceed_ask = False, direct_print = False, print_header = True, print_index = True, start_index = 1)[0] + "\n")
                            logPrint("是否需要对好友请求取子集？（输入任意键以开始打草稿，否则直接开始输入玩家索引。）\nDo you want to get a subset of the current friend request data? (Submit any non-empty string to make a draft, or null to input the player index directly.)")
                            draft_str = logInput()
                            draft = bool(draft_str)
                            if draft:
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                while True:
                                    draft_option = logInput()
                                    if draft_option == "":
                                        continue
                                    elif draft_option[0] == "0":
                                        break
                                    elif draft_option[0] == "1":
                                        scope = {"format_df": format_df, "df": friend_request_df.copy(deep = True), "fields": friend_request_fields_to_print}
                                        logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["tagLine"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                        subscope(scope, log = log)
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            logPrint('请输入要邀请的玩家的索引（见下面好友请求信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of players to invite (you may refer to the index column of the friend request table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friend_requests)) if friend_requests[i]["gameName"] == "WordlessMeteor"]')
                            print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_index = True, start_index = 1)[0])
                            log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            logPrint('变量提示（Variable hints）：\nfriend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()\nfriend_request_df = await sort_friend_request(connection)')
                            while True:
                                invite_str = logInput()
                                if invite_str == "":
                                    continue
                                elif invite_str[0] == "0":
                                    break
                                elif invite_str == "all":
                                    invitee_puuids = list(map(lambda x: x["puuid"], friend_requests)) #好友请求中的召唤师序号都是0（All summonerIds in the friend request list are 0s）
                                    invitee_obtained = True
                                    break
                                else:
                                    try:
                                        tmp = eval(invite_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_request_df):
                                            invitee_puuids = [friend_requests[tmp - 1]["summonerId"]]
                                            invitee_obtained = True
                                            break
                                        elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_request_df), tmp)) and len(tmp) == len(set(tmp)):
                                            invitee_puuids = list(map(lambda x: friend_requests[x - 1]["summonerId"], tmp))
                                            invitee_obtained = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if invitee_obtained:
                                invitee_summonerIds = []
                                for invitee_puuid in invitee_puuids:
                                    invitee_info = await get_info(connection, invitee_puuid)
                                    if invitee_info["info_got"]:
                                        invitee_summonerIds.append(invitee_info["body"]["summonerId"])
                                    else:
                                        logPrint(invitee_info["message"])
                    elif method[0] == "4":
                        logPrint('''请输入要邀请的玩家的召唤师名。每个玩家的召唤师名格式为{玩家名称}#{名称编号}。输入“-1”以结束输入。\nPlease submit the invitees' names. Each invitee's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.''')
                        invitee_summonerIds = []
                        while True:
                            invitee_summonerName = logInput()
                            if invitee_summonerName == "":
                                continue
                            elif invitee_summonerName == "0":
                                invitee_obtained = False
                                break
                            elif invitee_summonerName == "-1":
                                break
                            else:
                                try:
                                    tmp: list[str] = eval(invitee_summonerName)
                                except:
                                    invitee_summonerName_list: list[Any] = [invitee_summonerName]
                                else:
                                    if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (int, str)), tmp)):
                                        invitee_summonerName_list = tmp
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                for invitee_summonerName in invitee_summonerName_list:
                                    invitee_info = await get_info(connection, invitee_summonerName)
                                    if invitee_info["info_got"]:
                                        if invitee_info["body"]["puuid"] == current_info["puuid"]:
                                            logPrint("您已经在房间内了。\nYou're already in the lobby.")
                                        else:
                                            if invitee_info["body"]["summonerId"] in invitee_summonerIds: #如果已经邀请过该玩家且该玩家拒绝邀请，或同意后退出房间，那么用户需要先返回上一层，再进入才能再次邀请该玩家（If the user has invited a summoner but he/she rejects it, or he/she accepts it but exit the lobby afterwards, then the user need to first return to the last step and then select this method to invite this summoner again）
                                                logPrint("您已经邀请过该玩家了。\nYou've already invited this player.")
                                            else:
                                                invitee_summonerIds.append(invitee_info["body"]["summonerId"])
                                                invitee_obtained = True
                                                logPrint(invitee_info["body"])
                                    else:
                                        logPrint("[%s]" %(invitee_summonerName), invitee_info["message"])
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if invitee_obtained:
                        break
                    logPrint("请选择您输入要邀请的玩家信息的方式：\nPlease select a method of inputting the information of invitees:\n0\t返回上一层（Return to the last step）\n1\t好友索引（By friend index）\n2\t近期一起玩过的玩家索引（By recently played summoner index）\n3\t好友请求索引（By friend request index）\n4\t玩家召唤师名（By player summonerName）")
            elif mode == "3":
                if len(friends) == 0:
                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                else:
                    invitee_summonerIds = [friend["summonerId"] for friend in friends if not friend["availability"] in {"offline", "mobile", "dnd"}]
                    invitee_obtained = True
            elif mode == "4":
                if len(friends) == 0:
                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                else:
                    friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                    friend_group_df = await sort_friend_group(connection)
                    friend_group_fields_to_print = ["name", "id"]
                    friend_group_df_to_print = friend_group_df.loc[1:, friend_group_fields_to_print]
                    logPrint("请选择您要邀请的好友分组（见下面的好友分组信息列）。一些允许的输入格式：\nPlease select a group or groups of friends to invite (You may refer to the index column of the friend group table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall")
                    print(format_df(friend_group_df_to_print, print_index = True, start_index = 1)[0])
                    log.write(format_df(friend_group_df_to_print, width_exceed_ask = False, direct_print = True, print_index = True, start_index = 1)[0] + "\n")
                    while True:
                        invite_str = logInput()
                        if invite_str == "":
                            continue
                        elif invite_str[0] == "0":
                            break
                        elif invite_str == "all":
                            invitee_summonerIds = list(map(lambda x: x["summonerId"], friends))
                            invitee_obtained = True
                            break
                        else:
                            try:
                                tmp = eval(invite_str)
                            except:
                                traceback_info = traceback.format_exc()
                                logPrint(traceback_info)
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            else:
                                if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_group_df):
                                    invitee_summonerIds = [friend["summonerId"] for friend in friends if friend["groupId"] == friend_group_df["id"][tmp] and not friend["availability"] in {"offline", "mobile", "dnd"}]
                                    invitee_obtained = True
                                    break
                                elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_group_df), tmp)) and len(tmp) == len(set(tmp)):
                                    invitee_summonerIds = [friend["summonerId"] for friend in friends if friend["groupId"] in set(friend_group_df["id"][tmp]) and not friend["availability"] in {"offline", "mobile", "dnd"}]
                                    invitee_obtained = True
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                continue
            if invitee_obtained:
                logPrint("您邀请了以下%d名玩家：\nYou invited the following %d player(s):" %(len(invitee_summonerIds), len(invitee_summonerIds)))
                for invitee_summonerId in invitee_summonerIds:
                    invitee_info: dict[str, Any] = await get_info(connection, invitee_summonerId)
                    if invitee_info["info_got"]:
                        logPrint(get_info_name(invitee_info["body"]))
                    else:
                        logPrint(invitee_info["message"])
                body: list[dict[str, int]] = list(map(lambda x: {"toSummonerId": x}, invitee_summonerIds))
                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby/invitations", data = body)).json()
                logPrint(response)
                lobby_invitations: list[dict[str, Any]] | dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby/invitations")).json()
                if "errorCode" in lobby_invitations:
                    if lobby_invitations["httpStatus"] == 404 and lobby_invitations["message"] == "LOBBY_NOT_FOUND":
                        logPrint("您已离开房间。\nYou've left the original lobby.")
                    break
                else:
                    accepted_invitations: dict[str, Any] = filter(lambda x: x["state"] == "Accepted", lobby_invitations)
                    pending_invitations: dict[str, Any] = filter(lambda x: x["state"] == "Pending", lobby_invitations)
                    accepted_summonerIds: list[int] = list(map(lambda x: x["toSummonerId"], accepted_invitations))
                    pending_summonerIds: list[int] = list(map(lambda x: x["toSummonerId"], pending_invitations))
                    accepted_summonerNames: list[str] = []
                    pending_summonerNames: list[str] = []
                    uninvited_summonerNames: list[str] = []
                    for invitee_summonerId in invitee_summonerIds:
                        invitee_info = await get_info(connection, invitee_summonerId)
                        if invitee_info["info_got"]:
                            if invitee_summonerId in accepted_summonerIds:
                                accepted_summonerNames.append(get_info_name(invitee_info["body"]))
                            elif invitee_summonerId in pending_summonerIds:
                                pending_summonerNames.append(get_info_name(invitee_info["body"]))
                            else:
                                uninvited_summonerNames.append(get_info_name(invitee_info["body"]))
                    if len(accepted_summonerNames) != 0:
                        if len(accepted_summonerNames) == 1:
                            logPrint("%s已在房间内。\n%s is already in lobby." %("、".join(accepted_summonerNames), ", ".join(accepted_summonerNames)))
                        else:
                            logPrint("%s已在房间内。\n%s are already in lobby." %("、".join(accepted_summonerNames), ", ".join(accepted_summonerNames)))
                    if len(pending_summonerNames) != 0:
                        logPrint("%s已收到邀请。\n%s received your invitation." %("、".join(pending_summonerNames), ", ".join(pending_summonerNames)))
                    if len(uninvited_summonerNames) != 0:
                        logPrint("%s未能收到邀请。这可能是因为您还没有邀请权限，您的房间已经满员，对方不在线，对方只接受好友游戏邀请，或者对方将您拉入了聊天黑名单。\n%s didn't receive your invitation. Maybe you don't have invite priviledges, your lobby is already full, they're offline, they allow game invites only from friends, or they blocked you." %("、".join(uninvited_summonerNames), ", ".join(uninvited_summonerNames)))
            friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
            if len(friends) == 0:
                logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                friend_hovercard_df = await sort_friend_hovercard_simple(connection)
            else:
                logPrint("您的好友信息如下：\nYour friends:")
                friend_hovercard_df = await output_friend_hovercard_simple(connection, print_index = True, start_index = 1)
            logPrint("请选择邀请模式：\nPlease select an inviting mode:\n0\t返回上一层（Return to the last step）\n1\t单个邀请（Single）\n2\t批量邀请（In batches）\n3\t全部在线好友邀请（All available friends）\n4\t按组邀请（By group）")
    elif gameflow_phase == "None":
        logPrint("您尚未创建房间。请创建房间后再尝试邀请。\nYou've not created any lobby. Please try again after a lobby is created.")
    else:
        logPrint("您目前无法邀请玩家。\nYou can't invite any player currently.")

async def configure_nonFriendInvite_setting(connection: Connection, enable: bool = True) -> bool:
    '''
    设置是否接收来自陌生人的游戏邀请。<br>Set whether to receive game invitations from strangers.
    
    如果用户本来就接收，则不做任何处理。否则，修改设置以接受，并标记为选项已变更。<br>If the user has enabled receiving game invitations from strangers, this function will do nothing. Otherwise, change the setting to receive them and mark that the setting is changed.
    
    :param enable: 是否启用接收来自陌生人的游戏邀请。默认为真。<br>Whether to enable receiving game invitations from strangers. True by default.
    :type enable: bool
    :return: 设置是否已变更。主要用于恢复用户原来的设置。如果设置发生了变更，那么恢复原来的设置。<br>Whether this setting is changed. Mainly used to recover the user's original setting. If this setting is changed, then recover the original setting.
    :rtype: bool
    '''
    lol_notifications: Optional[dict[str, Any]] = await (await connection.request("GET", "/lol-settings/v2/account/LCUPreferences/lol-notifications")).json()
    if lol_notifications["data"] == None or not "blockNonFriendGameInvites" in lol_notifications["data"] or lol_notifications["data"]["blockNonFriendGameInvites"]:
        body: dict[str, Any] = {"data": {"blockNonFriendGameInvites": False}, "schemaVersion": lol_notifications["schemaVersion"]} #注意：schemaVersion一旦增加就不可减少（Warning: Once schemaVersion increases, it can't be decreased）
    else:
        body = {"data": {"blockNonFriendGameInvites": True}, "schemaVersion": lol_notifications["schemaVersion"]}
    response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-settings/v2/account/LCUPreferences/lol-notifications", data = body)).json()
    logPrint(response)
    if response == None:
        if enable:
            logPrint('已经关闭“只接受好友游戏邀请”选项。\nDisabled "Allow game invites only from friends" option.')
            return True
        else:
            logPrint('恢复了“只接受好友游戏邀请”选项。\nRecovered "Allow game invites only from friends" option.')
            return False
    else:
        logPrint('“只接受好友游戏邀请”选项切换失败。\n"Allow game invites only from friends" option toggle failed.')
        return False

async def join_game(connection: Connection) -> None:
    while True:
        logPrint("您是要加入好友的公开小队，还是接受邀请？\nDo you want to join a friend's open party or accept an invitation?\n1\t加入公开小队（Join party）\n2\t接受邀请（Accept an invitation）")
        action: str = logInput()
        if action == "":
            continue
        elif action[0] == "0":
            break
        elif action[0] == "1":
            friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
            parties: list[dict[str, Any]] = []
            party_owners: dict[str, str] = {}
            for friend in friends:
                if friend["lol"] != {} and "pty" in friend["lol"] and friend["lol"]["pty"] != "":
                    party: dict[str, str] = eval(friend["lol"]["pty"])
                    if not party["partyId"] in list(map(lambda x: x["partyId"], parties)): #当多个好友在同一个小队中时，需要去重（When multiple friends are in a same party, the repeated records need removing）
                        parties.append(party)
                        party_owners[party["partyId"]] = friend["gameName"] + "#" + friend["gameTag"]
            if len(parties) == 0:
                logPrint("没有公开的小队。\nThere's not any open party.")
                continue
            else:
                party_df: pandas.DataFrame = await sort_party_data(connection, parties)
                party_fields_to_print: list[str] = ["partyId", "maxPlayers", "queue gameMode", "queue name", "summonerNames"]
                logPrint("请选择您要加入的小队：\nPlease select a party to join:")
                print(format_df(party_df.loc[1:, party_fields_to_print], print_index = True, start_index = 1)[0])
                log.write(format_df(party_df.loc[1:, party_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                while True:
                    return_home: str = False
                    partyIndex: str = logInput()
                    if partyIndex == "":
                        continue
                    elif partyIndex == "0":
                        break
                    elif partyIndex in set(map(str, range(1, len(parties) + 1))):
                        partyId: str = parties[int(partyIndex) - 1]["partyId"]
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                        logPrint(response)
                        if response == None:
                            logPrint("您加入了%s的小队。\nYou joined the party of %s." %(party_owners[partyId], party_owners[partyId]))
                            return_home = True
                            break
                        else:
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
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    parties = []
                    party_owners = {}
                    for friend in friends:
                        if friend["lol"] != {} and "pty" in friend["lol"] and friend["lol"]["pty"] != "":
                            party = eval(friend["lol"]["pty"])
                            if not party["partyId"] in list(map(lambda x: x["partyId"], parties)):
                                parties.append(party)
                                party_owners[party["partyId"]] = friend["gameName"] + "#" + friend["gameTag"]
                    if len(parties) == 0:
                        logPrint("没有公开的小队。\nThere's not any open party.")
                        break
                    else:
                        party_df = await sort_party_data(connection, parties)
                        party_fields_to_print = ["partyId", "maxPlayers", "queue gameMode", "queue name", "summonerNames"]
                        logPrint("请选择您要加入的小队：\nPlease select a party to join:")
                        print(format_df(party_df.loc[1:, party_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(party_df.loc[1:, party_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
        elif action[0] == "2":
            receivedInvitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
            if len(receivedInvitations) == 0:
                logPrint("您还没有收到邀请。\nYou've not received any invitation.")
                continue
            else:
                logPrint("您收到的邀请信息如下：\nYour received invitations:")
                invid_df: pandas.DataFrame = await sort_received_invitations(connection)
                invid_fields_to_print: list[str] = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
                print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                logPrint("请选择邀请处理方式：\nPlease select a method of handling the invitation(s):\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）")
                while True:
                    return_home = False
                    method: str = logInput()
                    if method == "":
                        continue
                    elif method[0] == "0":
                        break
                    elif method[0] == "1":
                        logPrint("请选择要接受的邀请序号：\nPlease select the index of the invitation to accept:")
                        while True:
                            invitationIndex_str: str = logInput()
                            if invitationIndex_str == "":
                                continue
                            elif invitationIndex_str == "0":
                                logPrint("请选择邀请处理方式：\nPlease select a method of handling the invitation(s):\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）")
                                break
                            elif invitationIndex_str in set(map(str, range(1, len(invid_df)))):
                                invitationId: str = invid_df["invitationId"][int(invitationIndex_str)] #注意到邀请序号和小队编号的获取方式有所不同。小队编号是从原始的小队数据中获取的，因为小队数据作为静态数据传入小队信息整理函数中，而邀请信息没有传入邀请信息整理函数中，在程序运行前后邀请信息会频繁更新，可能导致原始邀请信息和邀请信息数据框中的内容不符（邀请信息数据框整理过程中的邀请信息和这里的邀请信息不在同一个作用域中）【Note that it differs between getting invitationId and getting partyId. PartyId is obtained from the original party data, in that party data are passed into `sort_party_data` function as static data, while invitation data aren't passed into `sort_received_invitations` function. As a result, invitation information may be frequently updated, which causes the original invitation data not in accordance with data in the invitation dataframe (invitation data here don't belong to the same scope of those during organizing the invitation dataframe)】
                                invid_owner: str = invid_df["fromSummonerName"][int(invitationIndex_str)]
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/accept")).json()
                                logPrint(response)
                                if response == None:
                                    logPrint("您接受了%s的邀请。\nYou accepted the invitation of %s." %(invid_owner, invid_owner))
                                    return_home = True
                                    break
                                else:
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
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            invid_df = await sort_received_invitations(connection)
                            invid_fields_to_print = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
                            logPrint("请选择要接受的邀请序号：\nPlease select the index of the invitation to accept:")
                            print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                            log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                    elif method[0] == "2":
                        logPrint("请选择拒绝模式：\nPlease select a decline mode:\n0\t返回上一层（Return to the last step）\n1\t单个拒绝（Single）\n2\t批量拒绝（In batches）\n3\t全部拒绝（All）")
                        while True:
                            index_got = False
                            mode: str = logInput()
                            if mode == "":
                                continue
                            elif mode == "0":
                                logPrint("请选择邀请处理方式：\nPlease select a method of handling the invitation(s):\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）")
                                break
                            elif mode == "1":
                                logPrint("请选择要拒绝的邀请序号：\nPlease enter the index of the invitation to decline:")
                                while True:
                                    decline_str: str = logInput()
                                    if decline_str == "":
                                        continue
                                    elif decline_str == "0":
                                        break
                                    elif decline_str in set(map(str, range(1, len(invid_df)))):
                                        decline_indices: list[int] = [int(decline_str)]
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            elif mode == "2":
                                logPrint("是否需要对邀请取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current invitation data? (Submit any non-empty string to make a draft, or null to input the invitation index directly.)")
                                draft_str = logInput()
                                draft = bool(draft_str)
                                if draft:
                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    while True:
                                        draft_option = logInput()
                                        if draft_option == "":
                                            continue
                                        elif draft_option[0] == "0":
                                            break
                                        elif draft_option[0] == "1":
                                            scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                            logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                            subscope(scope, log = log)
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                logPrint('请输入要拒绝的邀请的索引（见下面邀请信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of invitations to decline (you may refer to the index column of the above invitation table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(receivedInvitations)) if receivedInvitations[i]["gameConfig"]["queueId"] == -1 or receivedInvitations[i]["gameConfig"]["inviteGameType"] == "RIOTSCRIPT_BOT"]\n[i for i in range(len(invid_df)) if "WordlessMeteor" in invid_df.loc[i, "fromSummonerName"]]')
                                print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                                log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                logPrint('变量提示（Variable hints）：\nreceivedInvitations = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()\ninvid_df = await sort_received_invitations(connection)')
                                while True:
                                    decline_str: str = logInput()
                                    if decline_str == "":
                                        continue
                                    elif decline_str[0] == "0":
                                        break
                                    elif decline_str == "all":
                                        decline_indices = list(range(1, len(invid_df)))
                                        index_got = True
                                        break
                                    else:
                                        try:
                                            tmp = eval(decline_str)
                                        except:
                                            traceback_info = traceback.format_exc()
                                            logPrint(traceback_info)
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        else:
                                            if isinstance(tmp, int) and tmp > 0 and tmp < len(invid_df):
                                                decline_indices = [tmp]
                                                index_got = True
                                                break
                                            elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(invid_df), tmp)) and len(tmp) == len(set(tmp)):
                                                decline_indices = tmp
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            elif mode == "3":
                                decline_indices = list(range(1, len(invid_df)))
                                index_got = True
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            logPrint("您选择了以下%d个组队邀请：\nYou selected the following %d invitation(s):" %(len(decline_indices), len(decline_indices)))
                            print(format_df(invid_df.loc[decline_indices, invid_fields_to_print], print_index = True, reserve_index = True)[0])
                            log.write(format_df(invid_df.loc[decline_indices, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                            if index_got:
                                for invitationIndex in decline_indices:
                                    invitationId: str = invid_df["invitationId"][invitationIndex]
                                    invid_owner: str = invid_df["fromSummonerName"][invitationIndex]
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/decline")).json()
                                    logPrint(response)
                                    if response == None:
                                        logPrint("您拒绝了%s的邀请。\nYou accepted the invitation of %s." %(invid_owner, invid_owner))
                                    else:
                                        if response["httpStatus"] == 404 and response["message"] == "INVITATION_NOT_FOUND":
                                            logPrint("邀请已过期。\nInvite expired.")
                                        else:
                                            logPrint("拒绝邀请失败。\nInvitation decline failure.")
                                logPrint("您收到的邀请信息如下：\nYour received invitations:")
                                invid_df = await sort_received_invitations(connection)
                                if len(invid_df) == 1:
                                    logPrint("您还没有收到邀请。\nYou've not received any invitation.")
                                    return_home = True
                                    break
                                else:
                                    invid_fields_to_print = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
                                    print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            logPrint("请选择拒绝模式：\nPlease select a decline mode:\n0\t返回上一层（Return to the last step）\n1\t单个拒绝（Single）\n2\t批量拒绝（In batches）\n3\t全部拒绝（All）")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if return_home:
                        break
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        if return_home:
            break

async def spectate_compat(connection: Connection) -> None: #带有旧接口兼容性的观战过程（A spectate function compatible with old endpoints）
    global spectatorPluginNA_hint_printed, spectatorPluginLegacyDisabled_hint_printed
    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase == "None":
        exit_loop: bool = False #决定是否退出下面的循环（Determines whether to exit the following loop）
        while not exit_loop:
            friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
            friend_puuids = list(map(lambda x: x["puuid"], friends))
            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-spectator/v3/buddy/spectate", data = [current_info["puuid"]] if len(friends) == 0 else friend_puuids)).json() #在国服，如果这个接口的请求主体不是空列表，那么返回的异常信息是“SpectatorPlugin_NOT_AVAILABLE”。问题在于，如果请求主体是空列表，那么这个接口仍能正常响应。这样看来，似乎下面程序逻辑本应先处理len(friends)是否为0的情形。但是有一个比较巧妙的解法，就是将这个接口的请求主体设置为自己。这样一来，在观战插件可用的时候，如果程序识别到自己不在游戏中，那么自己肯定是不可观战的；如果程序识别到自己在游戏中，那么程序压根就无法运行这里的代码【On Chinese servers, if the request body of this endpoint isn't an empty list, then the error message is "SpectatorPlugin_NOT_AVAILABLE". But the problem is, if the request body is an empty list, then it still responds as normal (Riot servers). In that case, it seems the following program logic should first deal with the case where `len(friends) == 0` or `len(friends) != 0`. But here I provide a relatively clever solution: assign a list containing only the user's puuid as the request body. In this way, when the spectator plugin is available, if the program identifies that the user isn't in game right now, then the user itself can't be observable; if the program identifies the user itself is in game, then the program won't run the code here and hereinafter at all】
            logPrint(response)
            pluginNA: bool = False
            use_pluginNA: bool = False #决定是否在观战可用性插件可用的情况下仍然运行观战可用性插件不可用的情况下的代码（Decides whether to run the code of the case where spectating availability endpoint isn't available when this endpoint is actually available）
            #初始化观战请求主体相关变量（Initialize spectate request related variables）
            dropInSpectateGameId: int = 0
            gameQueueType: str = ""
            allowObserveMode: str = ""
            spectate_puuid: str = ""
            spectating_summonerName: str = ""
            spectate_ready: bool = False
            if "errorCode" in response: #传入空列表也会导致异常（Passing an empty list also causes an error）
                if response["httpStatus"] == 400 and response["message"] == "SpectatorPlugin_NOT_AVAILABLE":
                    pluginNA = True
                    if not spectatorPluginNA_hint_printed:
                        logPrint("您所在的服务器不支持玩家可观战性检测。请自行判断玩家是否可观战。\nThe server or platform you're currently on doesn't support this endpoint. Please judge by yourself whether a player is observable.")
                        spectatorPluginNA_hint_printed = True
                elif response["httpStatus"] == 500 and '{"message":"{\\"httpStatus\\":410,\\"errorCode\\":\\"GONE\\",\\"message\\":\\"Gone\\",\\"implementationDetails\\":\\"this functionality is no longer available\\"}","failureCode_int":410}' in response["message"]:
                    pluginNA = True
                    if not spectatorPluginLegacyDisabled_hint_printed:
                        logPrint("玩家可观战性检测功能已废弃。\nThe functionality of detecting whether a player can be spectated has been deprecated.")
                        spectatorPluginLegacyDisabled_hint_printed = True
                elif response["httpStatus"] == 400 and response["message"] == "Couldn't assign value to 'puuids' of type vector because the input not a collection.":
                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                elif response["httpStatus"] == 500 and "Couldn't find service in service discovery using ServerLocationEndpointFilter" in response["message"]:
                    logPrint("观战服务不可用。\nSpectator service unavailable.")
                else:
                    logPrint("无法获取好友可观战性信息。请通过客户端内右键点击一名好友以观战。\nCan't get friend observability information. Please right click on a friend to spectate.")
            else:
                if len(friends) == 0 or len(response["availableForWatching"]) == 0: #如果len(friends)不是0，那么上面的response就不会是异常，从而导致后面一个条件不会引发键错误（If `len(friends)` isn't 0, then the above `response` isn't an error and thus the latter condition here won't cause a KeyError）
                    logPrint("您尚无可观战的好友。是否观战其它玩家？（输入任意键以搜索其它玩家的观战可用性，否则返回上一层。）\nThere's not any friend available for watching. Do you want to spectate other players? (Submit any non-empty string to search for other players' observability, or null to return to the last step.)")
                    nonfriend_spectate_str = logInput()
                    nonfriend_spectate = bool(nonfriend_spectate_str)
                    if not nonfriend_spectate: #既不观战好友，也不观战其它玩家，那就是不观战（If neither friends nor players are to spectate, then don't spectate）
                        break
                else:
                    logPrint("您有%d个好友允许观战。请选择观战好友还是其它玩家。（输入任意键以观战其它玩家，否则观战好友。）\nThere're %d friend(s) that allow watching. Please select whether you want to spectate a friend or another non-friend player. (Submit any non-empty string to try spectating another non-friend player, or null to spectate friend.)" %(len(response["availableForWatching"]), len(response["availableForWatching"])))
                    nonfriend_spectate_str = logInput()
                    nonfriend_spectate = bool(nonfriend_spectate_str)
                back: bool = False
                if nonfriend_spectate:
                    logPrint('请输入您要检测观战可用性的玩家的召唤师名。输入“-1”以结束输入。\nPlease input the summonerName of the player to detect observability. Submit "-1" to end the input.')
                    spectate_summonerNames: list[str] = []
                    spectate_puuids: list[str] = []
                    spectate_infos: list[dict[str, Any]] = []
                    spectate_availability: list[bool] = []
                    while True:
                        spectate_summonerName: str = logInput()
                        if spectate_summonerName == "":
                            continue
                        elif spectate_summonerName == "0":
                            back = True
                            break
                        elif spectate_summonerName == "-1":
                            break
                        else:
                            if spectate_summonerName in spectate_summonerNames:
                                logPrint("您已经输入过该玩家了。\nYou've alerady added this summoner.")
                            else:
                                spectate_info: dict[str, Any] = await get_info(connection, spectate_summonerName)
                                if spectate_info["info_got"]:
                                    if spectate_info["body"]["puuid"] == current_info["puuid"]:
                                        logPrint("你不能观战你自己。\nYou can't spectate yourself.")
                                    elif spectate_info["body"]["puuid"] in spectate_puuids:
                                        logPrint("您已经输入过该玩家了。\nYou've alerady added this summoner.")
                                    else:
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-spectator/v3/buddy/spectate", data = [spectate_info["body"]["puuid"]])).json()
                                        logPrint(response)
                                        if len(response["availableForWatching"]) == 0:
                                            spectate_availability.append(False)
                                            logPrint("该玩家目前不可观战。\nThis player isn't observable currently.")
                                        else:
                                            spectate_availability.append(True)
                                            logPrint(spectate_info["body"])
                                        spectate_summonerNames.append(spectate_summonerName)
                                        spectate_puuids.append(spectate_info["body"]["puuid"])
                                        spectate_infos.append(spectate_info["body"]) #即使接口返回结果是该玩家目前不可观战，但是由于观战可用性检测接口存在问题，这里还是要保留一下意见（Even if the spectating availability endpoint returns the fact that this player isn't observable currently, because this endpoint may sometimes not work correctly, this player is still a candidate）
                                else:
                                    logPrint(spectate_info["message"])
                    if not back:
                        if len(spectate_puuids) == 0:
                            logPrint("您尚未输入任何玩家。\nYou've not input any player.")
                        else:
                            spectate_nonfriend_header_keys: list[str] = list(spectate_nonfriend_header.keys())
                            spectate_nonfriend_data: dict[str, list[Any]] = {key: [] for key in spectate_nonfriend_header_keys}
                            for spectate_info in spectate_infos:
                                for i in range(len(spectate_nonfriend_header_keys)):
                                    if i <= 2:
                                        key: str = spectate_nonfriend_header_keys[i]
                                        to_append: Any = spectate_info[key]
                                        spectate_nonfriend_data[key].append(to_append)
                            spectate_nonfriend_data["availability"] = spectate_availability
                            spectate_nonfriend_statistics_output_order: list[int] = list(range(len(spectate_nonfriend_header_keys)))
                            spectate_nonfriend_data_organized: dict[str, list[Any]] = {spectate_nonfriend_header_keys[i]: spectate_nonfriend_data[spectate_nonfriend_header_keys[i]] for i in spectate_nonfriend_statistics_output_order}
                            spectate_nonfriend_df: pandas.DataFrame = pandas.DataFrame(data = spectate_nonfriend_data_organized)
                            spectate_nonfriend_df["availability"] = spectate_nonfriend_df["availability"].astype(str)
                            spectate_nonfriend_df[column] = list(map(lambda x: "√" if x == "True" else "", spectate_nonfriend_df[column].to_list()))
                            spectate_nonfriend_df = pandas.concat([pandas.DataFrame([spectate_nonfriend_header])[spectate_nonfriend_df.columns], spectate_nonfriend_df], ignore_index = True)
                            logPrint("请选择一名玩家进行观战：\nPlease select a player to spectate:")
                            print(format_df(spectate_nonfriend_df, print_index = True)[0])
                            log.write(format_df(spectate_nonfriend_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                            while True:
                                index_got: bool = False
                                spectate_str: str = logInput()
                                if spectate_str == "":
                                    continue
                                elif spectate_str == "0":
                                    break
                                else:
                                    try:
                                        tmp: int = eval(spectate_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    else:
                                        if isinstance(tmp, int) and tmp > 0 and tmp < len(spectate_nonfriend_df):
                                            player_index: int = tmp
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            continue
                            if index_got:
                                spectate_puuid: str = spectate_nonfriend_df["puuid"][player_index]
                                spectating_summonerName: str = get_info_name(spectate_infos[player_index - 1])
                                spectate_ready = True
                else:
                    if len(friends) > 0 and len(response["availableForWatching"]) > 0:
                        logPrint("可观战的好友信息如下：\nFriends that allow spectating:")
                        friend_hovercard_df = await sort_friend_hovercard(connection)
                        friend_hovercard_fields_to_print = ["gameName", "gameTag", "gameModeName", "gameId", "champion name", "champion alias"]
                        friend_hovercard_df_to_print: pandas.DataFrame = pandas.concat([friend_hovercard_df.iloc[:1], friend_hovercard_df[friend_hovercard_df["puuid"].isin(response["availableForWatching"])]], ignore_index = True)
                        print(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], print_index = True)[0])
                        log.write(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": friend_hovercard_df_to_print.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\nprint(format_df(df[df["championId"] == 11]].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('''请选择一名好友，或者输入召唤师名进行观战。输入“0”以返回上一层。\nPlease select a friend or enter a summoner's name to spectate. Submit "0" to return to the last step.''')
                        print(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], print_index = True)[0])
                        log.write(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        while True:
                            index_got = False
                            spectate_str = logInput()
                            if spectate_str == "":
                                continue
                            elif spectate_str == "0":
                                exit_loop = True
                                break
                            else:
                                try:
                                    tmp = eval(spectate_str)
                                except:
                                    use_pluginNA = True
                                    break
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(friend_hovercard_df_to_print):
                                        friend_index: int = tmp
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                        if index_got:
                            dropInSpectateGameId, gameQueueType, allowObserveMode, spectate_puuid = friend_hovercard_df_to_print.loc[friend_index, ["gameId", "gameQueueType", "isObservable", "puuid"]]
                            spectating_summonerName = friend_hovercard_df_to_print["gameName"][friend_index] + "#" + friend_hovercard_df_to_print["gameTag"][friend_index]
                            spectate_ready = True
                    #这里对应的情况是nonfriend_spectate为假、好友数量是0且可观看玩家的数量也是0。既没有可观看的玩家，也不观战非好友，那就直接重新开始一个while循环，所以这里不写else语句（In this case, nonfriend_spectate = False, len(friends) = 0 and len(response["availableForWatching"]) = 0. That is, the user doesn't want to spectate the game of either a friend or a non-friend, so the next step should be returning to the start of the while-loop. Therefore, there's no need to write this else-statement）
            if pluginNA or use_pluginNA:
                if pluginNA:
                    logPrint('请输入您想要观看的玩家召唤师名。输入“0”以返回上一层。\nPlease input the summonerName of the player to spectate. Submit "0" to return to the last step.')
                while True:
                    spectating_summonerName = spectate_str if use_pluginNA else logInput()
                    use_pluginNA = False #如果在转到这里之前输入的召唤师名有问题，在本While循环内需要允许用户重新输入召唤师名（If the summoner name input before running here has a problem, the user should be allowed to input the summoner name again in this while-loop）
                    if spectating_summonerName == "":
                        continue
                    elif spectating_summonerName == "0":
                        exit_loop = True
                        break
                    else:
                        spectating_summoner_info: dict[str, Any] = await get_info(connection, spectating_summonerName)
                        if spectating_summoner_info["info_got"]:
                            if spectating_summoner_info["body"]["puuid"] == current_info["puuid"]:
                                logPrint("你不能观战自己。战斗！爽！————\nYou can't spectate yourself. Battle... YES!!!!")
                                continue
                            spectate_puuid = spectating_summoner_info["body"]["puuid"]
                            spectating_summonerName = get_info_name(spectating_summoner_info["body"]) #这一步是为了标准化召唤师名。因为对于查询来说，召唤师名间可以随意加空格，但是对于输出来说，最好统一（This step is designed to normalize the summoner name, because to search for a summoner, one can add whitespace characters wherever it wants, but when it comes to output, it'd better be unified）
                            spectate_ready = True
                            break
                        else:
                            logPrint(spectating_summoner_info["message"])
            if spectate_ready:
                spectatorKey_got: bool = False
                #首先，确定待观战的玩家是否是一名好友。如果是，从好友列表中查找观战密钥（First, determine whether the player to spectate is a friend. If it is, search for its spectatorKey from the friend list）
                friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                friend_dict: dict[str, list[dict[str, Any]]] = {friend["puuid"]: friend for friend in friends}
                if spectate_puuid in friend_dict and "lol" in friend_dict[spectate_puuid] and "spectatorKey" in friend_dict[spectate_puuid]["lol"]: #考虑到部分第三方软件可能伪装玩家状态，因此不用基于好友信息中是否存在“lol”键来进行分类讨论（Considering some third-party softwares may disguise the player's gameflow phase, we don't have to discuss whether "lol" key is in the friend data）
                    spectatorKey: str = friend_dict[spectate_puuid]["lol"]["spectatorKey"]
                    if spectatorKey != "":
                        spectatorKey_got = True
                else: #如果不是好友，则通过gsm接口查询玩家对战信息（If it's not, then search for this player's game information through gsm endpoint）
                    # gsm_spectate_info: dict[str, Any] = (await sgpSession.request(connection, "GET", f"/gsm/v1/ledge/spectator/region/{platformId}/puuid/{spectate_puuid}")).json()
                    gsm_spectate_info: dict[str, Any] = (await sgpSession.request(connection, "GET", f"/gsm/v1/ledge/region/{platformId}/puuid/{spectate_puuid}")).json()
                    if "errorCode" in gsm_spectate_info:
                        logPrint(gsm_spectate_info)
                        if gsm_spectate_info["httpStatus"] == 401 and gsm_spectate_info["message"] == "Access denied for specified puuid.":
                            logPrint("拒绝访问。\nAccess denied.")
                        elif gsm_spectate_info["httpStatus"] == 404 and gsm_spectate_info["message"] == "Player was not found":
                            logPrint("该玩家未在游戏中。\nThis player isn't in a game currently.")
                        elif gsm_spectate_info["httpStatus"] == 400 and gsm_spectate_info["message"] == "Game is not able to be spectated":
                            logPrint("现在还不能观战这个游戏类型，或者这个自定义对局未对观战者开放。\nThis game type cannot be spectated right now, or this custom game is not open to spectators.")
                        elif gsm_spectate_info["httpStatus"] == 409 and gsm_spectate_info["message"] == "Spectator APIs are disabled in the GSM":
                            logPrint("当前大区不支持通过玩家通用唯一识别码获取观战密钥。请在客户端内右键点击一名好友观战。\nThis server doesn't support obtaining spectator key from puuid. Please right click on a friend to spectate it in the League Client.")
                        else:
                            logPrint("确定该玩家观战信息时出现了一个错误。\nAn error occurred when the program was trying to determine this player's spectate information.")
                    elif gsm_spectate_info == {"status": {"message": "Method Not Allowed", "status_code": 405}}: #当前在国际服调用gsm接口时返回此信息（Currently, calling a gsm endpoint on a Riot server will return this information）
                        logPrint("当前大区不支持通过玩家通用唯一识别码获取观战密钥。请在客户端内右键点击一名好友观战。\nThis server doesn't support obtaining spectator key from puuid. Please right click on a friend to spectate it in the League Client.")
                    else:
                        dropInSpectateGameId = gsm_spectate_info["playerCredentials"]["gameId"]
                        gameQueueType = gsm_spectate_info["playerCredentials"]["queueType"]
                        allowObserveMode = "AllAllowed"
                        spectatorKey: str = gsm_spectate_info["playerCredentials"]["spectatorKey"]
                        spectatorKey_got = True
                #如果gsm接口失效，则要求用户自行输入观战密钥（If the gsm endpoint doesn't work, ask the user to provide the spectatorKey）
                if not spectatorKey_got:
                    logPrint('''如果您能够获取该玩家的观战密钥的话，您可以在下方输入观战密钥。不输入任何内容以放弃观战。\nIf you can access this player's spectatorKey, please input it below. Enter nothing to quit spectating.''')
                    spectatorKey = logInput()
                    if spectatorKey != "":
                        spectatorKey_got = True
                if spectatorKey_got:
                    body: dict[str, str] = {"dropInSpectateGameId": str(dropInSpectateGameId), "gameQueueType": gameQueueType, "allowObserveMode": allowObserveMode, "puuid": spectate_puuid, "spectatorKey": spectatorKey}
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-spectator/v1/spectate/launch", data = body)).json()
                    logPrint(response)
                    if response == None:
                        time.sleep(1) #发送指令后客户端不一定马上进入英雄选择或游戏中（The client won't immediately enter the champ select or in game stage after the program posts the spectating requests）
                        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                        if gameflow_phase == "ChampSelect" or gameflow_phase == "InProgress":
                            gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                            gameModeName: str = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameflow_session["gameData"]["queue"]["id"]) if gameflow_session["gameData"]["queue"]["name"] == "" else gameflow_session["gameData"]["queue"]["name"]
                            logPrint("启动观战成功！您正在观看%s的对局。\nLaunched spectating successfully. You'll be spectating the game of %s soon.\n对局序号（MatchId）：\t%d\n队列序号（QueueId）：\t%d\n游戏模式名称（Game mode name）：\t%s" %(spectating_summonerName, spectating_summonerName, gameflow_session["gameData"]["gameId"], gameflow_session["gameData"]["queue"]["id"], gameModeName))
                            logPrint("观战信息如下：\nSpectate information is as follows:")
                            spectate_body: dict[str, str] = await (await connection.request("GET", "/lol-spectator/v1/spectate")).json() #退出观战不会更新该接口的返回结果，所以只在观战成功时使用此接口（Exit spectating won't update the result this endpoint returns, so this endpoint is only used here）
                            logPrint(spectate_body)
                        else:
                            logPrint("这场对局现在不可观战。它也许已经结束了。\nThe game isn't available for spectate now. It might have ended.")
                    else:
                        if response["httpStatus"] == 400 and response["message"] == "SpectatorPlugin_NOT_AVAILABLE":
                            pluginNA = True
                            logPrint("您所在的服务器不支持玩家可观战性检测。请自行判断玩家是否可观战。\nThe server or platform you're currently on doesn't support this endpoint. Please judge by yourself whether a player is observable.")
                            spectatorPluginNA_hint_printed = True
                        elif response["httpStatus"] == 400 and response["message"] == 'Failed to set launch spectator mode: {"message":"Error response for POST /lol-gameflow/v2/spectate/launch: Cannot spectate game because spectator key is missing","failureCode_int":400,"url":"/lol-gameflow/v2/spectate/launch","method":"POST","error":"Cannot spectate game because spectator key is missing"}':
                            logPrint("观战秘钥缺失。请联系开发人员修复程序。\nSpetate key is missing. Please contact the developer to fix the program.")
                            break
                        elif response["httpStatus"] == 400 and "Attempting to spectate player but not in game" in response["message"]:
                            logPrint("该玩家未在游戏中，或者您输入的观战密钥不正确。\nThis player isn't in a game currently, or the spectatorKey isn't correct.")
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
                            elif "Game is private and not able to be spectated" in response["message"]:
                                logPrint("该游戏未对观战者开放。\nThis game isn't open to spectators.")
                            else:
                                logPrint("观战失败。请通过客户端内右键点击一名好友，或者通过第三方工具来进行观战。\nSpectating failed. Please right click on a friend or use another third-party tool to spectate.")
    elif gameflow_phase == "Reconnect":
        gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        inGame_puuids: list[str] = list(map(lambda x: x["puuid"], gameflow_session["gameData"]["playerChampionSelections"]))
        isSpectating: bool = not current_info["puuid"] in inGame_puuids
        logPrint("检测到您正在游戏中。是否重新连接？（输入任意键重新连接，否则不连接。）\nDetected you're currently in a game. Do you want to reconnect? (Submit any non-empty string to reconnect, or null to refuse reconnecting.)")
        reconnect_str: str = logInput()
        reconnect: bool = bool(reconnect_str)
        if reconnect:
            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-gameflow/v1/reconnect")).json()
            logPrint(response)
            if response == None:
                logPrint("重新连接成功。\nReconnect succeeded.")
            else:
                if "errorCode" in response and response["httpStatus"] == 403 and response["message"] == "Reconnect is not available.":
                    logPrint("重新连接不可用。请重启客户端并重试。\nReconnect isn't available. Please restart the client and try again.")
                else:
                    logPrint("重新连接失败。\nReconnect failed.")
    else:
        logPrint("您目前的状态不可观战。请等待游戏结束或者退出房间来进行观战。\nYou're not allowed to spectate for now. Please wait for the current game to end or exit the party or lobby to spectate any game.")

async def switch_capture_device(connection: Connection) -> None:
    captureDevice_df: pandas.DataFrame = await sort_capture_devices(connection)
    if len(captureDevice_df) == 1:
        logPrint("未检测到输入设备。\nNo capture devices detected.")
    else:
        logPrint("您的输入设备信息如下：\nYour capture devices:")
        print(format_df(captureDevice_df, print_index = True)[0])
        log.write(format_df(captureDevice_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
        logPrint("请选择您要使用的输入设备：\nPlease select an capture device to use:")
        while True:
            deviceIndex_str: str = logInput()
            if deviceIndex_str == "":
                continue
            elif deviceIndex_str == "0":
                break
            else:
                try:
                    tmp: int = eval(deviceIndex_str)
                except ValueError:
                    traceback_info = traceback.format_exc()
                    logPrint(traceback_info)
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                else:
                    if isinstance(tmp, int):
                        deviceIndex: int = tmp
                        if deviceIndex in range(1, len(captureDevice_df)):
                            if True or captureDevice_df["usable"][deviceIndex]: #有时用户的确有切换到不可用输入设备的需要（Sometimes the user does get the demand of switching to a capture device that isn't usable）
                                deviceName: str = captureDevice_df["name"][deviceIndex]
                                response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-premade-voice/v1/capturedevices", data = deviceName)).json() #这里的设备名称改成句柄也是可以的（Here the device handle works, too）
                                logPrint(response)
                                if response == None:
                                    captureDevices: list[dict[str, Any]] = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
                                    captureDevices_transformed: dict[str, dict[str, Any]] = {device["name"]: device for device in captureDevices}
                                    if captureDevices_transformed[deviceName]["is_current_device"]:
                                        logPrint("输入设备已切换为%s。\nThe capture device has switched to %s." %(deviceName, deviceName))
                                    else:
                                        logPrint("输入设备切换失败。\nCapture device switch failed.")
                                    break
                                else:
                                    logPrint("输入设备切换失败。\nCapture device switch failed.")
                            else:
                                logPrint("您选择的输入设备不可用。请切换一个设备并重试。\nThe capture device you selected isn't usable. Please switch another device and try again.")
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")

async def test_capture_device(connection: Connection) -> None:
    captureDevices: list[dict[str, Any]] = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
    captureDevices_transformed = {device["name"]: device for device in captureDevices}
    voiceSettings: dict[str, Any] = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
    current_captureDevice_name: str = captureDevices_transformed[voiceSettings["currentCaptureDeviceHandle"]]["name"]
    logPrint("您当前的输入设备是%s。\nThe current capture device is %s." %(current_captureDevice_name, current_captureDevice_name))
    while True:
        logPrint("输入任意非空字符串以开始测试，或者直接按回车键以返回上一层。\nSubmit any non-empty string to start mic-test, or press Enter directly to return to the last step.")
        micTest_str: str = logInput()
        micTest: bool = bool(micTest_str)
        if micTest:
            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-premade-voice/v1/mic-test")).json()
            logPrint(response)
            logPrint("按回车键以结束测试。\nPress Enter to end the test.")
            logInput()
            response: dict[str, Any] = await (await connection.request("DELETE", "/lol-premade-voice/v1/mic-test")).json()
            logPrint(response)
            continue
        else:
            break

async def switch_capture_mode(connection: Connection) -> None:
    logPrint("请选择输入模式：\nPlease select an input mode:\n0\t返回上一层（Return to the last step）\n1\t语音活跃度（Voice activity）\n2\t按住以发言（Push to talk）")
    while True:
        mode: str = logInput()
        if mode == "":
            continue
        elif mode[0] == "0":
            break
        elif mode[0] == "1":
            response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-premade-voice/v1/self/inputMode", data = "voiceActivity")).json()
            logPrint(response)
            if response == None:
                logPrint("输入模式已改为语音活跃度。\nInput mode has switched to Voice Activity.")
            else:
                logPrint("输入模式切换失败。\nInput mode switch failed.")
            break
        elif mode[0] == "2":
            pttAvailable: bool = await (await connection.request("POST", "/lol-premade-voice/v1/push-to-talk/check-available", data = "0")).json() #这里比较神奇的地方是把POST改成其它方法会导致下面的response也会受到影响（Here a magical thing is if "POST" is changed into another HTTP method, then the following `response` will be influenced）
            if pttAvailable:
                response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-premade-voice/v1/self/inputMode", data = "pushToTalk")).json()
                logPrint(response)
                if response == None:
                    logPrint("输入模式已改为按住以发言。\nInput mode has switched to Push to Talk.")
                else:
                    logPrint("输入模式切换失败。\nInput mode switch failed.")
            else:
                logPrint("无法启用按住以发言。如果要启用【按键发言】，你必须提供额外的访问许可。你可以点击MacOS命令符或在系统偏好设置中，在安全及隐私(Security & Privacy) > 隐私(Privacy) > 可访问性(Accessibility)下启用LeagueClient.app的检查框。\nCan't enable Push to Talk. To enable push to talk, you must grant additional accessibility permissions. Either click on the MacOS prompt or in System Preferences, enable the checkbox for LeagueClient.app under Security & Privacy > Privacy > Accessibility.")
            break
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")

async def set_voice_activation_threshold(connection: Connection) -> None:
    logPrint("请输入一个不超过100的自然数。\nPlease enter a nonnegative integer not greater than 100.")
    while True:
        sensitivity_str: str = logInput()
        if sensitivity_str == "":
            continue
        elif sensitivity_str[0] == "q":
            break
        else:
            try:
                sensitivity: int = int(sensitivity_str)
            except ValueError:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-premade-voice/v1/self/activationSensitivity", data = sensitivity_str)).json()
                logPrint(response)
                if response == None:
                    voiceSettings: dict[str, Any] = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                    logPrint("语音激活阈值已设置为%d%%。\nVoice activation threshold is set as %d%%." %(voiceSettings["vadSensitivity"], voiceSettings["vadSensitivity"]))
                    break
                else:
                    if response["httpStatus"] == 400 and response["httpStatus"] == f"Value {sensitivity} for 'sensitivity' of type int32 is out of range":
                        logPrint("您输入的整数过大。请重新输入。\nThe integer you input is too large. Please try again.")
                    else:
                        logPrint("语音激活阈值修改失败。\nVoice activation threshold change failed.")

async def set_pushToTalk_hotkey(connection: Connection) -> None:
    pttAvailable: bool = await (await connection.request("POST", "/lol-premade-voice/v1/push-to-talk/check-available", data = "0")).json() #这里和上面一样神奇（This is just as magical as above）
    if pttAvailable:
        logPrint('请输入按键字符串。按键字符串应为单键或组合键，如“[c]”“[Ctrl][c]”“[Shift][Ctrl][c]”“[<Unbound>]”。\nPlease input the key string. A key string represents either a single key or a combined key, like "[c]", "[Ctrl][c]", "[Shift][Ctrl][c]" or "[<Unbound>]".')
        while True:
            keyStr: str = logInput()
            if keyStr == "0":
                break
            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-premade-voice/v1/gameClientUpdatedPTTKey", data = keyStr)).json()
            logPrint(response)
            if response == None:
                voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                logPrint("【按键发言】热键已设置为%s。\nPush to Talk hotkey is set as %s." %(voiceSettings["pttKey"], voiceSettings["pttKey"]))
                break
            else:
                logPrint("【按键发言】热键设置失败。请检查按键字符串是否规范。\nPush to Talk hotkey change failed. Please check if the key string is standard.")
    else:
        logPrint("按住以发言不可用。如果要启用【按键发言】，你必须提供额外的访问许可。你可以点击MacOS命令符或在系统偏好设置中，在安全及隐私(Security & Privacy) > 隐私(Privacy) > 可访问性(Accessibility)下启用LeagueClient.app的检查框。\nPush to Talk not available. To enable push to talk, you must grant additional accessibility permissions. Either click on the MacOS prompt or in System Preferences, enable the checkbox for LeagueClient.app under Security & Privacy > Privacy > Accessibility.")

async def set_input_volume(connection: Connection) -> None:
    logPrint("请输入一个不超过100的自然数。\nPlease enter a nonnegative integer not greater than 100.")
    while True:
        micLevel_str: str = logInput()
        if micLevel_str == "":
            continue
        elif micLevel_str[0] == "q":
            break
        else:
            try:
                micLevel: int = int(micLevel_str)
            except ValueError:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-premade-voice/v1/self/micLevel", data = micLevel_str)).json()
                logPrint(response)
                if response == None:
                    voiceSettings: dict[str, Any] = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                    logPrint(f"输入音量（增强）已设置为%d%%。\nInput Volume (Gain) is set as %d%%." %(voiceSettings["micLevel"], voiceSettings["micLevel"]))
                    break
                else:
                    if response["httpStatus"] == 400 and response["httpStatus"] == f"Value {micLevel} for 'micLevel' of type int32 is out of range":
                        logPrint("您输入的整数过大。请重新输入。\nThe integer you input is too large. Please try again.")
                    else:
                        logPrint("输入音量（增强）修改失败。\nInput Volume (Gain) change failed.")

async def mute_self(connection: Connection) -> None:
    voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
    if voiceSettings["localMicMuted"]:
        response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-premade-voice/v1/self/mute", data = "0")).json()
        logPrint(response)
        if response == None:
            logPrint("自我静音已解除。\nSelf unmuted.")
        else:
            logPrint("自我静音解除失败。\nSelf unmute failed.")
    else:
        response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-premade-voice/v1/self/mute", data = "1")).json()
        logPrint(response)
        if response == None:
            logPrint("已自我静音。\nSelf muted.")
        else:
            logPrint("自我静音失败。\nSelf mute failed.")

async def output_voice_settings(connection: Connection) -> None:
    captureDevices: list[dict[str, Any]] = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
    captureDevices_transformed: dict[str, dict[str, Any]] = {device["name"]: device for device in captureDevices}
    voiceSettings: list[dict[str, Any]] = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
    logPrint("语音设置如下：\nVoice settings:")
    voiceSettings_data: dict[str, list[Any]] = {"项目": ["自动加入语音频道", "连接时静音", "当前输入设备句柄", "当前输入设备名称", "输入音量", "已自我静音", "输入模式", "语音活跃度已激活", "语音活跃度阈值", "语音检测延迟", "按键发言已激活", "按键发言热键", "允许回环"], "Items": ["autoJoin", "muteOnConnect", "currentCaptureDeviceHandle", "currentCaptureDeviceName", "micLevel", "localMicMuted", "inputMode", "vadActive", "vadSensitivity", "vadHangoverTime", "pttActive", "pttKey", "loopbackEnabled"], "值": [voiceSettings["autoJoin"], voiceSettings["muteOnConnect"], voiceSettings["currentCaptureDeviceHandle"], captureDevices_transformed[voiceSettings["currentCaptureDeviceHandle"]]["name"], voiceSettings["micLevel"], voiceSettings["localMicMuted"], voiceSettings["inputMode"], voiceSettings["vadActive"], voiceSettings["vadSensitivity"], voiceSettings["vadHangoverTime"], voiceSettings["pttActive"], voiceSettings["pttKey"], voiceSettings["loopbackEnabled"]]}
    voiceSettings_df: pandas.DataFrame = pandas.DataFrame(data = voiceSettings_data)
    print(format_df(voiceSettings_df, align = "><^")[0], end = "\n\n")
    log.write(format_df(voiceSettings_df, width_exceed_ask = False, direct_print = False, align = "><^")[0] + "\n\n")

async def manage_voice_inputSettings(connection: Connection) -> None:
    capture_permission: bool = await (await connection.request("GET", "/lol-premade-voice/v1/devices/capture/permission")).json()
    if capture_permission:
        logPrint("请选择具体设置：\nPlease select a detailed setting:\n0\t返回上一层（Return to the last step）\n1\t更改输入设备（Switch the capture device）\n2\t测试当前输入设备（Test the current capture device）\n3\t切换输入模式（Switch the input mode）\n4\t设置语音激活阈值（Change voice activation threshold）\n5\t设置【按键发言】热键（不可用）【Change Push to Talk hotkey (not available)】\n6\t设置输入音量（Set input volume）\n7\t自我静音/解除自我静音（Self mute/unmute）\n8\t输出设置信息（Output settings）")
        while True:
            action: str = logInput()
            if action == "":
                continue
            elif action[0] == "0":
                break
            elif action[0] == "1":
                await switch_capture_device(connection)
            elif action[0] == "2":
                await test_capture_device(connection)
            elif action[0] == "3":
                await switch_capture_mode(connection)
            elif action[0] == "4":
                await set_voice_activation_threshold(connection)
            elif action[0] == "5":
                await set_pushToTalk_hotkey(connection)
            elif action[0] == "6":
                await set_input_volume(connection)
            elif action[0] == "7":
                await mute_self(connection)
            elif action[0] == "8":
                await output_voice_settings(connection)
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            logPrint("请选择具体设置：\nPlease select a detailed setting:\n0\t返回上一层（Return to the last step）\n1\t更改输入设备（Switch the capture device）\n2\t测试当前输入设备（Test the current capture device）\n3\t切换输入模式（Switch the input mode）\n4\t设置语音激活阈值（Change voice activation threshold）\n5\t设置【按键发言】热键（不可用）【Change Push to Talk hotkey (not available)】\n6\t设置输入音量（Set input volume）\n7\t自我静音/解除自我静音（Self mute/unmute）\n8\t输出设置信息（Output settings）")
    else:
        logPrint("您的输入设备没有获得访问许可。\nYour capture devices aren't granted accessibility permissions.")

async def manage_voice_outputSettings(connection: Connection) -> None:
    participant_records: list[dict[str, Any]] = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
    if len(participant_records) == 0:
        logPrint("您尚未加入语音频道。请连接至语音。\nYou haven't joined the voice channel. Please connect to League Voice.")
    else:
        for i in range(len(participant_records)):  #确定自己的编号，因为自己不应该被静音，虽然其实静音自己并不会造成什么影响（Determine the index of the user itself, for he/she shouldn't mute him/herself, although muting itself doesn't make any difference）
            if participant_records[i]["puuid"] == current_info["puuid"]:
                selfIndex: int = i + 1 #数据框的中文表头占用了1个索引位置（The Chinese header of the dataframe takes up an index）
                break
        else:
            selfIndex = -1
        logPrint("语音频道内的玩家音量设置如下：\nVoice settings of participants in the current voice channel:")
        participant_record_df: pandas.DataFrame = await sort_voice_participants(connection)
        participant_record_fields_to_print: list[str] = ["gameName", "tagLine", "isMuted", "volume", "isSpeaking", "energy"]
        print(format_df(participant_record_df.loc[:, participant_record_fields_to_print])[0])
        log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
        logPrint("请选择设置方法：\nPlease select a voice setting:\n0\t返回上一层（Return to the last step）\n1\t静音/解除静音（Mute/Unmute）\n2\t修改音量（Change volume）")
        while True:
            action: str = logInput()
            if action == "":
                continue
            elif action[0] == "0":
                break
            elif action[0] == "1":
                logPrint("请选择静音/解除静音模式：\nPlease select a mute mode:\n0\t返回上一层（Return to the last step）\n1\t单个静音/解除静音（Single）\n2\t批量静音/解除静音（In batches）\n3\t全部静音/解除静音（All）")
                while True:
                    index_got: bool = False
                    mode: str = logInput()
                    if mode == "":
                        continue
                    elif mode[0] == "0":
                        break
                    elif mode[0] == "1":
                        logPrint("请选择要静音的小队玩家的索引：\nPlease select a participant to mute:")
                        print(format_df(participant_record_df.loc[:, participant_record_fields_to_print], print_index = True)[0])
                        log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        while True:
                            mute_str: str = logInput()
                            if mute_str == "":
                                continue
                            elif mute_str == "0":
                                break
                            else:
                                try:
                                    player_index: int = int(mute_str)
                                except ValueError:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if player_index == selfIndex:
                                        logPrint("你不能静音你自己。\nYou can't mute yourself.")
                                    if player_index in range(1, len(participant_record_df)):
                                        mute_indices: list[int] = [player_index]
                                        index_got = True
                                        break
                    elif mode[0] == "2":
                        logPrint("是否需要对小队玩家取子集？（输入任意键以开始打草稿，否则直接开始输入小队玩家索引。）\nDo you want to get a subset of the current participant data? (Submit any non-empty string to make a draft, or null to input the participant index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": participant_record_df.copy(deep = True), "fields": participant_record_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["tagLine"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('请输入要静音/解除静音的小队玩家的索引（见下面小队玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the participants to mute/mute (you may refer to the index column of the participant table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(participant_record_df)) if participant_record_df.loc[i, "gameName"] == "WordlessMeteor"]')
                        print(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0]) + "\n"
                        logPrint('变量提示（Variable hints）：\nparticipant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()\nparticipant_record_df = await sort_voice_participants(connection)\nfor i in range(len(participant_records)):\n    if participant_records[i]["puuid"] == current_info["puuid"]:\n        selfIndex = i\n        break')
                        while True:
                            mute_str = logInput()
                            if mute_str == "":
                                continue
                            elif mute_str[0] == "0":
                                break
                            elif mute_str == "all":
                                mute_indices = list(range(1, len(participant_record_df)))
                                if selfIndex != -1:
                                    mute_indices.remove(selfIndex)
                                index_got = True
                                break
                            else:
                                try:
                                    tmp = eval(mute_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(participant_record_df) and tmp != selfIndex:
                                        mute_indices = [tmp]
                                        index_got = True
                                        break
                                    elif isinstance(mute_indices, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(participant_record_df) and x != selfIndex, mute_indices)) and len(mute_indices) == len(set(mute_indices)):
                                        mute_indices = tmp
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif mode[0] == "3":
                        mute_indices = list(range(1, len(participant_record_df)))
                        if selfIndex != -1:
                            mute_indices.remove(selfIndex)
                        index_got = True
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if index_got:
                        logPrint("您选择了以下%d名玩家：\nYou selected the following %d player(s):" %(len(mute_indices), len(mute_indices)))
                        print(format_df(participant_record_df.loc[mute_indices, participant_record_fields_to_print], print_index = True, reserve_index = True)[0])
                        log.write(format_df(participant_record_df.loc[mute_indices, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                        logPrint("您想要将这些玩家静音，还是解除静音？（输入任意键以静音，否则解除静音。）\nDo you want to mute or unmute these participants? (Submit any non-empty string to mute, or null to unmute.)")
                        isMuted_str: str = logInput()
                        isMuted: bool = bool(isMuted_str)
                        for player_index in mute_indices:
                            player_puuid: str = participant_record_df["puuid"][player_index]
                            player_summonerName: str = participant_record_df["gameName"][player_index] + "#" + participant_record_df["tagLine"][player_index]
                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-premade-voice/v1/participants/{player_puuid}/mute", data = str(int(isMuted)))).json()
                            logPrint(response)
                            if response == None:
                                if isMuted:
                                    logPrint(f"您已将玩家{player_summonerName}静音。\nYou muted the participant {player_summonerName}.")
                                else:
                                    logPrint(f"您已将玩家{player_summonerName}解除静音。\nYou unmuted the participant {player_summonerName}.")
                            else:
                                if isMuted:
                                    logPrint("静音失败。\nMute failed.")
                                else:
                                    logPrint("解除静音失败。\nUnmute failed.")
                        logPrint("语音频道内的玩家音量设置如下：\nVoice settings of participants in the current voice channel:")
                        participant_record_df = await sort_voice_participants(connection)
                        participant_record_fields_to_print = ["gameName", "tagLine", "isMuted", "volume", "isSpeaking", "energy"]
                        print(format_df(participant_record_df.loc[:, participant_record_fields_to_print])[0])
                        log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                    logPrint("请选择静音/解除静音模式：\nPlease select a mute mode:\n0\t返回上一层（Return to the last step）\n1\t单个静音/解除静音（Single）\n2\t批量静音/解除静音（In batches）\n3\t全部静音/解除静音（All）")
            elif action[0] == "2":
                logPrint("请选择音量修改模式：\nPlease select a mode to change volume:\n0\t返回上一层（Return to the last step）\n1\t单个修改音量（Single）\n2\t批量修改音量（In batches）\n3\t全部修改音量（All）\n4\t逐个修改音量（One by one）")
                while True:
                    index_got = False
                    volumeChange_indices: list[int] = []
                    mode: str = logInput()
                    if mode == "":
                        continue
                    elif mode[0] == "0":
                        break
                    elif mode[0] == "1":
                        logPrint("请选择要修改音量的小队玩家的索引：\nPlease select a participant to change volume:")
                        print(format_df(participant_record_df.loc[:, participant_record_fields_to_print], print_index = True)[0])
                        log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        while True:
                            volumeChange_str: str = logInput()
                            if volumeChange_str == "":
                                continue
                            elif volumeChange_str == "0":
                                break
                            else:
                                try:
                                    player_index: int = int(volumeChange_str)
                                except ValueError:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if player_index == selfIndex: #自己看自己的音量始终是50（When the user looks at his/her own volume, it's always 50）
                                        logPrint("你无法修改自己的音量。\nYou can't change the volume of yourself.")
                                    if player_index in range(1, len(participant_record_df)):
                                        volumeChange_indices = [player_index]
                                        index_got = True
                                        break
                    elif mode[0] == "2":
                        logPrint("是否需要对小队玩家取子集？（输入任意键以开始打草稿，否则直接开始输入小队玩家索引。）\nDo you want to get a subset of the current participant data? (Submit any non-empty string to make a draft, or null to input the participant index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": participant_record_df.copy(deep = True), "fields": participant_record_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["tagLine"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('请输入要修改音量的小队玩家的索引（见下面小队玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the participants to change volume (you may refer to the index column of the participant table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(participant_record_df)) if participant_record_df.loc[i, "gameName"] == "WordlessMeteor"]')
                        print(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint('变量提示（Variable hints）：\nparticipant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()\nparticipant_record_df = await sort_voice_participants(connection)\nfor i in range(len(participant_records)):\n    if participant_records[i]["puuid"] == current_info["puuid"]:\n        selfIndex = i\n        break')
                        while True:
                            volumeChange_str: str = logInput()
                            if volumeChange_str == "":
                                continue
                            elif volumeChange_str[0] == "0":
                                break
                            elif volumeChange_str == "all":
                                volumeChange_indices = list(range(1, len(participant_record_df)))
                                if selfIndex != -1:
                                    volumeChange_indices.remove(selfIndex)
                                index_got = True
                                break
                            else:
                                try:
                                    tmp = eval(volumeChange_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(participant_record_df) and tmp != selfIndex:
                                        volumeChange_indices = [tmp]
                                        index_got = True
                                        break
                                    elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(participant_record_df) and x != selfIndex, tmp)) and len(tmp) == len(set(tmp)):
                                        volumeChange_indices = tmp
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif mode[0] == "3":
                        volumeChange_indices = list(range(1, len(participant_record_df)))
                        if selfIndex != -1:
                            volumeChange_indices.remove(selfIndex)
                        index_got = True
                    elif mode[0] == "4":
                        playerVolumes: dict[int, float] = {}
                        logPrint('请依次输入小队玩家的索引和要设置的音量值，以空格为分隔符。输入“-1”以结束输入。\nPlease input the index of the participant and the volume value to set one by one, split by space. Submit "-1" to end the input.')
                        while True:
                            volume_str = logInput()
                            if volume_str == "":
                                continue
                            elif volume_str[0] == "0":
                                index_got = False
                                break
                            elif volume_str == "-1":
                                break
                            else:
                                try:
                                    player_index, volume = map(int, volume_str.split())
                                except ValueError:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if player_index == selfIndex:
                                        logPrint("你无法修改自己的音量。\nYou can't change the volume of yourself.")
                                    if player_index in range(1, len(participant_record_df)):
                                        playerVolumes[player_index] = volume
                                        index_got = True
                                        print(format_df(pandas.concat([participant_record_df.loc[playerVolumes.keys(), participant_record_fields_to_print], pandas.DataFrame(data = {"energy_to_change": playerVolumes.values()}, index = playerVolumes.keys())], axis = 1), print_index = True, reserve_index = True)[0])
                                        log.write(format_df(pandas.concat([participant_record_df.loc[playerVolumes.keys(), participant_record_fields_to_print], pandas.DataFrame(data = {"energy_to_change": playerVolumes.values()}, index = playerVolumes.keys())], axis = 1), width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if index_got:
                        if mode[0] in {"1", "2", "3"}:
                            logPrint("您选择了以下%d名玩家：\nYou selected the following %d player(s):" %(len(volumeChange_indices), len(volumeChange_indices)))
                            print(format_df(participant_record_df.loc[volumeChange_indices, participant_record_fields_to_print], print_index = True, reserve_index = True)[0])
                            log.write(format_df(participant_record_df.loc[volumeChange_indices, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                            logPrint("请输入一个不超过100的自然数以设置音量：\nPlease enter a nonnegative integer not greater than 100 to set the volume:")
                            while True:
                                volume_str: str = logInput()
                                if volume_str == "":
                                    continue
                                elif volume_str[0] == "q":
                                    break
                                else:
                                    try:
                                        volume: int = int(volume_str)
                                    except ValueError:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        for player_index in volumeChange_indices:
                                            player_puuid = participant_record_df["puuid"][player_index]
                                            player_summonerName = participant_record_df["gameName"][player_index] + "#" + participant_record_df["tagLine"][player_index]
                                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-premade-voice/v1/participants/{player_puuid}/volume", data = volume_str)).json()
                                            logPrint(response)
                                            if response == None:
                                                participant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
                                                participant_records_transformed = {}
                                                for participant in participant_records:
                                                    participant_records_transformed[participant["puuid"]] = participant
                                                volume = participant_records_transformed[player_puuid]["volume"]
                                                logPrint(f"您已将{player_summonerName}的音量设置为{volume}.\nYou set the volume of {player_summonerName} as {volume}.")
                                            else:
                                                logPrint(f"{player_summonerName}的音量设置失败。\nVolume of {player_summonerName} change failed.")
                                        break
                        else:
                            for player_index in playerVolumes:
                                player_puuid: str = participant_record_df["puuid"][player_index]
                                player_summonerName: str = participant_record_df["gameName"][player_index] + "#" + participant_record_df["tagLine"][player_index]
                                volume: int = playerVolumes[player_index]
                                response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-premade-voice/v1/participants/{player_puuid}/volume", data = str(volume))).json()
                                logPrint(response)
                                if response == None:
                                    participant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
                                    participant_records_transformed = {}
                                    for participant in participant_records:
                                        participant_records_transformed[participant["puuid"]] = participant
                                    volume = participant_records_transformed[player_puuid]["volume"]
                                    logPrint(f"您已将{player_summonerName}的音量设置为{volume}.\nYou set the volume of {player_summonerName} as {volume}.")
                                else:
                                    logPrint(f"{player_summonerName}的音量设置失败。\nVolume of {player_summonerName} change failed.")
                        logPrint("语音频道内的玩家音量设置如下：\nVoice settings of participants in the current voice channel:")
                        participant_record_df = await sort_voice_participants(connection)
                        participant_record_fields_to_print = ["gameName", "tagLine", "isMuted", "volume", "isSpeaking", "energy"]
                        print(format_df(participant_record_df.loc[:, participant_record_fields_to_print])[0])
                        log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                    logPrint("请选择音量修改模式：\nPlease select a mode to change volume:\n0\t返回上一层（Return to the last step）\n1\t单个修改音量（Single）\n2\t批量修改音量（In batches）\n3\t全部修改音量（All）\n4\t逐个修改音量（One by one）")
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            logPrint("请选择设置方法：\nPlease select a voice setting:\n0\t返回上一层（Return to the last step）\n1\t静音/解除静音（Mute/Unmute）\n2\t修改音量（Change volume）")

async def manage_premade_voice(connection: Connection) -> None:
    voiceAvailability: dict[str, Any] = await (await connection.request("GET", "/lol-premade-voice/v1/availability")).json()
    if voiceAvailability["connectedToVoiceServer"]:
        if voiceAvailability["enabled"]:
            if voiceAvailability["voiceChannelAvailable"]:
                logPrint("请选择要更改的设置类别：\nPlease choose an action:\n0\t返回上一层（Return to the last step）\n1\t更改输入设置（Change input settings）\n2\t更改输出设置（Change output settings）\n3\t重置使用提示（Reset first-experience hints）")
                while True:
                    setting: str = logInput()
                    if setting == "":
                        continue
                    elif setting[0] == "0":
                        break
                    elif setting[0] == "1":
                        await manage_voice_inputSettings(connection)
                    elif setting[0] == "2":
                        await manage_voice_outputSettings(connection)
                    elif setting[0] == "3":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-premade-voice/v1/first-experience/reset")).json()
                        logPrint(response)
                        if response == None:
                            logPrint("小队语音提示已启用。您将在客户端和游戏内看到相关提示。注意，重置提示在一个客户端进程进行时只能生效一次。\nLeague Voice hint enabled. You'll see tooltips both in League Client and in game. Note that tooltip reset can only come into effect once during each process living.")
                        else:
                            logPrint("小队语音提示重置失败。\nLeague Voice first-experience tooltips reset failed.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    logPrint("请选择要更改的设置类别：\nPlease choose an action:\n0\t返回上一层（Return to the last step）\n1\t更改输入设置（Change input settings）\n2\t更改输出设置（Change output settings）\n3\t重置使用提示（Reset first-experience hints）")
            else:
                logPrint("语音频道不可用。加入一个小队来使用语音。\nVoice channel not available. Join a party to use League Voice.")
        else:
            logPrint("语音不可用。请检查麦克风和扬声器是否正确连接。\nVoice not available. Please check if your microphone and speaker has connected properly.")
    else:
        logPrint("您未连接到语音服务。请检查网络情况。如果这个问题持续存在，请重新启动英雄联盟客户端。\nYou're not connected to League Voice service. Please check your network condition. If this problem persists, please restart the League Client.")

async def mute_champSelect_player(connection: Connection) -> None:
    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase == "ChampSelect":
        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        if champ_select_session["isSpectating"]:
            logPrint("您正在观战中。静音操作不适用。\nYou're spectating a game now. Player mute actions aren't applicable.")
        else:
            if len(champ_select_session["myTeam"]) == 1:
                logPrint("没有玩家可以静音。\nNo players to mute.")
            else:
                muted_players: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/player-mutes")).json()
                if len(muted_players) != 0:
                    logPrint("您当前静音的玩家如下：\nCurrently muted players:")
                    muted_player_df: pandas.DataFrame = await sort_mutedPlayers_champSelect(connection)
                    muted_player_fields_to_print: list[str] = ["obfuscatedPuuid", "gameName", "tagLine", "puuid", "isPlayerMuted", "isSettingsMuted", "isSystemMuted"]
                    print(format_df(muted_player_df.loc[1:, muted_player_fields_to_print])[0])
                    log.write(format_df(muted_player_df.loc[1:, muted_player_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                myTeamId: int = champ_select_session["myTeam"][0]["team"]
                champSelect_player_df: pandas.DataFrame = await sort_ChampSelect_players(connection, champ_select_session, LoLChampions, championSkins, spells, wardSkins, playerMode = 1, log = log)
                champSelect_myTeam_df: pandas.DataFrame = pandas.concat([champSelect_player_df.iloc[:1], champSelect_player_df[champSelect_player_df["team"] == myTeamId]], ignore_index = True)
                for i in range(len(champSelect_myTeam_df)): #确定自己的编号，因为自己不应该被静音，虽然其实静音自己相当于不做任何操作（Determine the index of the user itself, for he/she shouldn't mute him/herself, although muting itself means nothing done）
                    if champSelect_myTeam_df["puuid"][i] == current_info["puuid"]:
                        myIndex: int = i
                        break
                else:
                    logPrint("英雄选择数据异常。请确保您正在这场比赛中，且信息可见。\nUnexpected champ select data encountered. Please ensure you're current in this game and your information is visible.")
                logPrint("当前英雄选择阵营数据如下：\nCurrent champ select team data:")
                champSelect_player_fields_to_print: list[str] = ["team_color", "cellId", "obfuscatedPuuid", "assignedPosition", "champion name", "champion alias"]
                champSelect_myTeam_df_to_print: pandas.DataFrame = champSelect_myTeam_df.loc[:, champSelect_player_fields_to_print].reset_index(drop = True)
                print(format_df(champSelect_myTeam_df.loc[1:, champSelect_player_fields_to_print], print_index = True, start_index = 1)[0])
                log.write(format_df(champSelect_myTeam_df.loc[1:, champSelect_player_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                logPrint("请选择静音操作：\nPlease select a mute action:\n0\t返回上一层（Return to the last step）\n1\t单个静音（Single）\n2\t批量静音（In batches）\n3\t全部静音（All）\n4\t解除所有静音（Remove all）")
                while True:
                    index_got = False
                    action: str = logInput()
                    if action == "":
                        continue
                    elif action[0] == "0":
                        break
                    elif action[0] == "1":
                        logPrint("请选择要静音的队友索引：\nPlease select an ally to mute:")
                        print(format_df(champSelect_myTeam_df_to_print, print_index = True)[0])
                        log.write(format_df(champSelect_myTeam_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        while True:
                            mute_str: str = logInput()
                            if mute_str == "":
                                continue
                            elif mute_str == "0":
                                break
                            else:
                                try:
                                    ally_index = int(mute_str)
                                except ValueError:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if ally_index == myIndex:
                                        logPrint("你不能静音你自己。\nYou can't mute yourself.")
                                    if ally_index in range(1, len(champSelect_myTeam_df)):
                                        mute_indices: list[str] = [ally_index]
                                        index_got = True
                                        break
                    elif action[0] == "2":
                        logPrint("是否需要对队友取子集？（输入任意键以开始打草稿，否则直接开始输入队友索引。）\nDo you want to get a subset of the current ally data? (Submit any non-empty string to make a draft, or null to input the ally index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": champSelect_myTeam_df.copy(deep = True), "fields": champSelect_player_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[df["cellId"] == 1].loc[1:, fields])[0])\nprint(format_df(df[df["championId"] == 350].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('请输入要静音的队友的索引（见下面队友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your allies to mute (you may refer to the index column of the ally table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(champSelect_myTeam_df)) if champSelect_myTeam_df.loc[i, "gameName"] == "WordlessMeteor"]')
                        print(format_df(champSelect_myTeam_df.loc[1:, champSelect_player_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(champSelect_myTeam_df.loc[1:, champSelect_player_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint('变量提示（Variable hints）：\nchamp_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()\nmyTeamId = champ_select_session["myTeam"][0]["team"]\nchampSelect_player_df = await sort_champSelect_player(connection)\nchampSelect_myTeam_df = pandas.concat([champSelect_player_df.loc[:1], champSelect_player_df[champSelect_player_df["team"] == myTeamId]], ignore_index = True)\nfor i in range(len(champSelect_myTeam_df)):\n    if champSelect_myTeam_df.loc[i, "puuid"] == current_info["puuid"]:\n        myIndex = i\n        break')
                        while True:
                            mute_str = logInput()
                            if mute_str == "":
                                continue
                            elif mute_str[0] == "0":
                                break
                            elif mute_str == "all":
                                mute_indices = list(range(1, len(champSelect_myTeam_df)))
                                mute_indices.remove(myIndex)
                                index_got = True
                                break
                            else:
                                try:
                                    tmp = eval(mute_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(champSelect_myTeam_df) and tmp != selfIndex:
                                        mute_indices = [tmp]
                                        index_got = True
                                        break
                                    elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(champSelect_myTeam_df) and x != myIndex, mute_indices)) and len(mute_indices) == len(set(mute_indices)):
                                        mute_indices = tmp
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif action[0] == "3":
                        mute_indices = list(range(1, len(champSelect_myTeam_df)))
                        index_got = True
                        mute_indices.remove(myIndex)
                    elif action[0] == "4":
                        index_got = False
                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/lol-chat/v1/player-mutes")).json()
                        logPrint(response)
                        if response == None:
                            logPrint("所有队友被已解除静音。\nYour allies are unmuted.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if index_got:
                        logPrint("您选择了以下%d名队友：\nYou selected the following %d ally/allies:" %(len(mute_indices), len(mute_indices)))
                        print(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_player_fields_to_print], print_index = True, reserve_index = True)[0])
                        log.write(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_player_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                        mute_puuids: list[str] = []
                        for ally_index in mute_indices:
                            ally_nameVisibilityType: str = champSelect_myTeam_df["nameVisibilityType"][ally_index]
                            ally_obfuscatedPuuid: str = champSelect_myTeam_df["obfuscatedPuuid"][ally_index]
                            ally_puuid: str = champSelect_myTeam_df["puuid"][ally_index]
                            mute_puuids.append(ally_obfuscatedPuuid if ally_nameVisibilityType == "HIDDEN" else ally_puuid)
                        logPrint("您想要将这些队友静音，还是解除静音？（输入任意键以静音，否则解除静音。）\nDo you want to mute or unmute these allies? (Submit any non-empty string to mute, or null to unmute.)")
                        isMuted_str: str = logInput()
                        isMuted: bool = bool(isMuted_str)
                        body = {"puuids": mute_puuids, "isMuted": isMuted}
                        logPrint("请选择（解除）静音模式：\nPlease select a(n) (un)mute mode:\n0\t返回上一层（Return to the last step）\n1\t玩家静音（Player mute）\n2\t系统静音（System mute）")
                        while True:
                            mode: str = logInput()
                            if mode == "":
                                continue
                            elif mode[0] == "0":
                                break
                            elif mode[0] == "1":
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-chat/v1/player-mutes", data = body)).json()
                                logPrint(response)
                                if response == None:
                                    if isMuted:
                                        logPrint("您已将以下队友静音。\nYou muted the following allies.")
                                    else:
                                        logPrint("您已将以下队友解除静音。\nYou unmuted the following allies.")
                                    print(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_player_fields_to_print], print_index = True, reserve_index = True)[0])
                                    log.write(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_player_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                    break
                                else:
                                    if isMuted:
                                        logPrint("静音失败。\nMute failed.")
                                    else:
                                        logPrint("解除静音失败。\nUnmute failed.")
                            elif mode[0] == "2":
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-chat/v1/system-mutes", data = body)).json()
                                logPrint(response)
                                if response == None:
                                    if isMuted:
                                        logPrint("您已将以下队友静音。\nYou muted the following allies.")
                                    else:
                                        logPrint("您已将以下队友解除静音。\nYou unmuted the following allies.")
                                    log.write(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_player_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                    break
                                else:
                                    if isMuted:
                                        logPrint("静音失败。\nMute failed.")
                                    else:
                                        logPrint("解除静音失败。\nUnmute failed.")
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        muted_players = await (await connection.request("GET", "/lol-chat/v1/player-mutes")).json()
                        if len(muted_players) != 0:
                            logPrint("您当前静音的玩家如下：\nCurrently muted players:")
                            muted_player_df = await sort_mutedPlayers_champSelect(connection)
                            muted_player_fields_to_print = ["obfuscatedPuuid", "gameName", "tagLine", "puuid", "isPlayerMuted", "isSettingsMuted", "isSystemMuted"]
                            print(format_df(muted_player_df.loc[1:, muted_player_fields_to_print])[0])
                            log.write(format_df(muted_player_df.loc[1:, muted_player_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                    logPrint("请选择静音操作：\nPlease select a mute action:\n0\t返回上一层（Return to the last step）\n1\t单个静音（Single）\n2\t批量静音（In batches）\n3\t全部静音（All）\n4\t解除所有静音（Remove all）")
    else:
        logPrint("提示：以下静音操作仅在英雄选择阶段生效。请确保您目前正在英雄选择阶段。\nHint: The following mute actions only apply in a champ select group chat. Please confirm that you're during champ select.")

async def mute(connection: Connection) -> None:
    logPrint("请选择静音场景：\nPlease select a mute situation:\n0\t返回上一层（Return to the last step）\n1\t预组队语音（Premade voice）\n2\t英雄选择小队聊天（Group chat during champ select）")
    while True:
        situation: str = logInput()
        if situation == "":
            continue
        elif situation[0] == "0":
            break
        elif situation[0] == "1":
            await manage_premade_voice(connection)
        elif situation[0] == "2":
            await mute_champSelect_player(connection)
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            continue
        logPrint("请选择静音场景：\nPlease select a mute situation:\n0\t返回上一层（Return to the last step）\n1\t预组队语音（Premade voice）\n2\t英雄选择小队聊天（Group chat during champ select）")

async def friend_behavior_simulation(connection: Connection) -> None: #在本函数中可以看到一些查战绩脚本中涉及的数据资源。但是这里是通过LCU API来获取的，这是因为该脚本获取的数据一定是实时的，而查战绩脚本和自定义脚本11会涉及过时的数据（This function involves some data resources in Customized Program 05, except that they're obtained through LCU API in this program. This is because the data this program obtains must be real-time, while Customized Program 05 and 11 may get old data）
    global spectatorPluginNA_hint_printed, spectatorPluginLegacyDisabled_hint_printed, current_info, folder
    spectatorPluginNA_hint_printed = False
    spectatorPluginLegacyDisabled_hint_printed = False
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    riot_client_info: list[str] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info: dict[str, str] = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region: str = client_info["--region"]
    #校验客户端是否连接到聊天服务（Verify whether the League Client has connected to Riot Client chat service）
    friends: list[dict[str, Any]] | dict[str, Any] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    if isinstance(friends, dict):
        if friends["errorCode"] == 503 and friends["message"] == "not connected to RC chat yet":
            logPrint("客户端尚未连接到聊天服务。如果这个问题持续存在，请重新登录客户端后再重新运行此脚本。\nNot connected to RC client yet. If this problem persists, please relog in and then rerun this program.")
            return 1
    #下面设置输出文件的位置（The following code determines the output files' location）
    folder = set_summonerInfo_folder(region, platformId, current_info)
    os.makedirs(folder, exist_ok = True)
    while True:
        logPrint("请选择好友操作：\nPlease select an operation on friends:\n0\t返回上一层（Return to the last step）\n1\t查看好友列表（Check the friend list）\n2\t好友分组管理（Manage the friend groups）\n3\t统计好友信息（Count friend statistics）\n4\t导出对话（Export conversations）\n5\t聊天（Chat）\n6\t好友管理（Friend management）\n7\t邀请加入游戏（Invite to game）\n8\t加入游戏（Join a game）\n9\t观战（Spectate）\n10\t玩家静音（Player mute）")
        option: str = logInput()
        if option == "":
            continue
        elif not option in set(map(str, range(1, 11))):
            break
        elif option == "1":
            await check_friend_list(connection)
        elif option == "2":
            await manage_friend_group(connection)
        elif option == "3":
            await count_friend_statistics(connection)
        elif option == "4":
            await export_conversation(connection)
        elif option == "5":
            await send_message(connection)
        elif option == "6": #好友管理涉及添加好友、同意/拒绝好友请求、移动好友、修改好友备注、删除好友、拉黑
            await manage_friend(connection)
        elif option == "7":
            await invite(connection)
        elif option == "8":
            settings_changed: bool = await configure_nonFriendInvite_setting(connection, enable = True)
            await join_game(connection)
            if settings_changed:
                await configure_nonFriendInvite_setting(connection, enable = False)
        elif option == "9":
            await spectate_compat(connection)
        elif option == "10":
            await mute(connection)
        #time.sleep(2) #原意是通过2秒的延迟使得好友数据及时更新，但是好友数据用不着在这里更新，反倒是在各个选项下更深的地方需要更新。然而如果你要取消注释也有说法，因为第一层好友操作的输出很长，可能会瞬间覆盖上一次结果（Originally intended to let the friend data update in time, but it's not necessary for friend data to be updated here. Instead, it needs updating in some deeper hierachies of those if-statements above. It's rather reasonable if you want to uncomment this piece of code, however, because output of the first layer turns out to be too long, so that it may cover the last result）

#-----------------------------------------------------------------------------
# 黑名单管理（Black list management）
#-----------------------------------------------------------------------------
async def sort_blockList_data(connection: Connection, CustomURF_blockList_enabled: bool = False, blockList: Any = None) -> pandas.DataFrame:
    if blockList == None:
        blockList = []
    if CustomURF_blockList_enabled:
        if isinstance(blockList, list) and all(map(lambda x: isinstance(x, dict), blockList)) and all(i in player for player in blockList for i in ["gameName", "gameTag", "icon", "id", "name", "pid", "puuid", "summonerId"]):
            blockList: list[dict[str, Any]] = blockList[:]
        else:
            logPrint("黑名单数据格式错误！函数只生成空表。\nBlock list data format ERROR! The function will only return an empty table.")
            blockList_df: pandas.DataFrame = pandas.DataFrame(data = blockList_header, index = [0])
            return blockList_df
    else:
        blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
        if isinstance(blockList, dict) and "errorCode" in blockList:
            if blockList["httpStatus"] == 503 and blockList["message"] == "Error response for GET /chat/v3/blocked: ":
                logPrint("查看黑名单的请求失败。函数只生成空表。\nThe request to check blocked players failed. The function will only return an empty table.")
            else:
                logPrint("黑名单获取失败！\nThe program failed to get the block list! An empty table will be returned instead.")
            blockList_df = pandas.DataFrame(data = blockList_header, index = [0])
            return blockList_df
    blockList_header_keys: list[str] = list(blockList_header.keys())
    blockList_data: dict[str, list[Any]] = {key: [] for key in blockList_header_keys}
    for player in blockList:
        for i in range(len(blockList_header_keys)):
            key: str = blockList_header_keys[i]
            if i == 8:
                to_append: Any = summonerIcons[player["icon"]][key.split()[1]]
            else:
                to_append = player[key]
            blockList_data[key].append(to_append)
    blockList_statistics_output_order: list[int] = [0, 1, 4, 7, 5, 6, 2, 8]
    blockList_data_organized: dict[str, list[Any]] = {blockList_header_keys[i]: blockList_data[blockList_header_keys[i]] for i in blockList_statistics_output_order}
    blockList_df: pandas.DataFrame = pandas.DataFrame(data = blockList_data_organized)
    blockList_df = pandas.concat([pandas.DataFrame([blockList_header])[blockList_df.columns], blockList_df], ignore_index = True)
    return blockList_df

async def block(connection: Connection) -> None:
    blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
    if isinstance(blockList, dict) and "errorCode" in blockList:
        if blockList["httpStatus"] == 503 and blockList["message"] == "Error response for GET /chat/v3/blocked: ":
            logPrint("黑名单请求失败。\nThe request to check blocked players failed.")
        else:
            logPrint("黑名单获取失败！\nThe program failed to get the block list!")
    else:
        blocked_puuids: list[str] = set(map(lambda x: x["puuid"], blockList))
        logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t从文件中拉黑（From file）")
        while True:
            info_got: bool = False
            mode: str = logInput()
            if mode == "":
                continue
            elif mode == "0":
                break
            elif mode == "1":
                logPrint("请输入要拉黑的玩家名称：\nPlease enter the summonerName of the player to block:")
                while True:
                    blockName: str = logInput()
                    if blockName == "":
                        continue
                    elif blockName == "0":
                        info_got = False
                        break
                    else:
                        block_info: dict[str, Any] = await get_info(connection, blockName)
                        if block_info["info_got"]:
                            block_puuid: str = block_info["body"]["puuid"]
                            if block_puuid == current_info["puuid"]:
                                logPrint("你无法把自己拉入聊天黑名单。\nYou cannot block yourself, silly.")
                            elif block_puuid in blocked_puuids:
                                logPrint("你已经将%s拉入聊天黑名单。\nYou have already blocked %s." %(get_info_name(block_info["body"]), get_info_name(block_info["body"])))
                            else:
                                block_puuids: list[str] = [block_puuid]
                                block_summonerNames: list[str] = [get_info_name(block_info["body"])]
                                info_got = True
                                break
                        else:
                            logPrint(block_info["message"])
            elif mode == "2":
                block_puuids = []
                block_summonerNames = []
                logPrint('请依次输入要拉黑的玩家名称。输入“-1”以结束输入。\nPlease enter the summonerName of the player to block one by one. Submit "-1" to end the input.')
                while True:
                    blockName = logInput()
                    if blockName == "":
                        continue
                    elif blockName == "0":
                        info_got = False
                        break
                    elif blockName == "-1":
                        break
                    else:
                        try:
                            tmp = eval(blockName)
                        except:
                            blockName_list: list[Any] = [blockName]
                        else:
                            if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (str, int)), tmp)):
                                blockName_list = tmp
                            else:    
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                        for blockName in blockName_list:
                            block_info = await get_info(connection, blockName)
                            if block_info["info_got"]:
                                block_puuid = block_info["body"]["puuid"]
                                block_summonerName = get_info_name(block_info["body"])
                                if block_puuid == current_info["puuid"]:
                                    logPrint("你无法把自己拉入聊天黑名单。\nYou cannot block yourself, silly.")
                                elif block_puuid in blocked_puuids:
                                    logPrint("你已经将%s拉入聊天黑名单。\nYou have already blocked %s." %(get_info_name(block_info["body"]), get_info_name(block_info["body"])))
                                elif not block_puuid in block_puuids:
                                    block_puuids.append(block_puuid)
                                    block_summonerNames.append(block_summonerName)
                                    info_got = True
                            else:
                                logPrint(block_info["message"])
            elif mode == "3":
                logPrint("是否需要测试玩家信息的获取？（输入任意键以开始打草稿，否则直接开始输入要拉入聊天黑名单的玩家信息。）\nDo you want to test obtaining player information? (Submit any non-empty string to make a draft, or null to input the index of the players to block directly.)")
                draft_str = logInput()
                draft = bool(draft_str)
                if draft:
                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                    while True:
                        draft_option: str = logInput()
                        if draft_option == "":
                            continue
                        elif draft_option[0] == "0":
                            break
                        elif draft_option[0] == "1":
                            scope: dict[str, Any] = {"get_info_name": get_info_name, "current_info": current_info, "blockList": blockList}
                            logPrint('示例（Examples）：\nprint(dir()) #输出exec函数使用的作用域中的变量名称（Output names of variables to the scope of `exec` function）\nimport os, pandas, pyperclip #引入需要的库（Introduce required libraries）\nos.system("CLS") #清屏（Clear screen）\ndf = pandas.read_excel("black list.xlsx", sheet_name = "Sheet1") #示例：从工作簿中读取黑名单数据（Example: Read black list data from a workbook）\nblock_puuids = set(df.iloc[:, 2])\npyperclip.copy(str(block_puuids)) #将结果复制到全局剪贴板中，用于后续输入黑名单列表（Copy the result to the global clipboard for subsequently inputting the blocked player list）\n输入“-1”以退出测试。\nSubmit "-1" to quit the test.')
                            subscope(scope, log = log)
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                block_puuids = []
                block_summonerNames = []
                logPrint('请输入要拉黑的玩家名称列表。输入“0”以返回上一层。\nPlease submit a list containing summonerNames of players to block. Submit "0" to return to the last step.')
                while True:
                    block_str = logInput()
                    if block_str == "":
                        continue
                    elif block_str[0] == "0":
                        info_got = False
                        break
                    else:
                        try:
                            tmp = eval(block_str)
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        else:
                            if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (int, str)), tmp)):
                                blockNames = tmp
                                for blockName in blockNames:
                                    block_info = await get_info(connection, blockName)
                                    if block_info["info_got"]:
                                        block_puuid = block_info["body"]["puuid"]
                                        block_summonerName = get_info_name(block_info["body"])
                                        if block_puuid == current_info["puuid"]:
                                            logPrint(f"[{blockName}]你无法把自己拉入聊天黑名单。\nYou cannot block yourself, silly.")
                                        elif block_puuid in blocked_puuids:
                                            logPrint(f"[{blockName}]" + "你已经将%s拉入聊天黑名单。\nYou have already blocked %s." %(get_info_name(block_info["body"]), get_info_name(block_info["body"])))
                                        elif not block_puuid in block_puuids:
                                            block_puuids.append(block_puuid)
                                            block_summonerNames.append(block_summonerName)
                                            info_got = True
                                    else:
                                        logPrint(f"[{blockName}]" + block_info["message"])
                                break
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if info_got:
                logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.' %("、".join(block_summonerNames), ", ".join(block_summonerNames)))
                block_confirm_str: str = logInput()
                block_confirm: bool = block_confirm_str == "block"
                if block_confirm:
                    for i in range(len(block_puuids)):
                        body: dict[str, str] = {"puuid": block_puuids[i]}
                        block_summonerName = block_summonerNames[i]
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-chat/v1/blocked-players", data = body)).json()
                        logPrint(response)
                        if response == None:
                            logPrint("%s已被拉入聊天黑名单。你再也不会看到TA的在线状态或是收到来自TA的信息了。\n%s has been blocked. You will no longer see them online or receive their messages." %(block_summonerName, block_summonerName))
                        else:
                            if response["httpStatus"] == 400:
                                logPrint("您未能成功将%s拉入聊天黑名单。也许TA已经在其中了。\nYou failed to block %s. Maybe he/she's already in it." %(block_summonerName, block_summonerName))
                            else:
                                logPrint("您未能成功将%s拉入聊天黑名单。\nYou failed to block %s." %(block_summonerName, block_summonerName))
            blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
            blocked_puuids = set(map(lambda x: x["puuid"], blockList))
            logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t从文件中拉黑（From file）")

async def detect_blockedPlayer_state(connection: Connection, blockList: list[dict[str, Any]], blockList_df: pandas.DataFrame) -> None:
    blockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]
    blockDict: dict[str, dict[str, Any]] = {player["puuid"]: player for player in blockList}
    blocked_puuids = set(map(lambda x: x["puuid"], blockList))
    while True:
        gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase == "None":
            logPrint("您尚未创建任何房间！请创建房间后再按回车键开始检测。\nYou haven't created any lobby yet! Please create a lobby and then start detection.")
        elif gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck"}:
            blockList_df_filtered_lobby: pandas.DataFrame = pandas.DataFrame()
            isLeader: bool = False
            #检测房间/小队内成员有无黑名单成员（Detect whether a blocked player is in the lobby / party）
            lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            blocked_member_puuids: list[str] = []
            for member in lobby_information["members"]:
                if member["puuid"] in blocked_puuids:
                    blocked_member_puuids.append(member["puuid"])
                if member["puuid"] == current_info["puuid"]:
                    isLeader = member["isLeader"]
            if len(blocked_member_puuids) == 0:
                logPrint("小队/房间中无黑名单成员。\nNo blocked member detected in the current party / lobby.")
            else:
                logPrint("小队/房间中发现以下%d名成员在黑名单中：\nFound the following %d blocked member(s) in the lobby:" %(len(blocked_member_puuids), len(blocked_member_puuids)))
                blockList_df_filtered_lobby = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_member_puuids)]], ignore_index = True)
                print(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print])[0])
                log.write(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
            #检测房间邀请中有无向黑名单成员发起的邀请（Detect whether there's any lobby invitation sent to a blocked player）
            lobby_invitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v1/lobby/invitations")).json()
            toSummonerIds: list[dict[str, int]] = list(map(lambda x: x["toSummonerId"], lobby_invitations))
            blocked_invitee_puuids: list[str] = []
            for summonerId in toSummonerIds:
                invitee_info: dict[str, Any] = await get_info(connection, summonerId)
                if invitee_info["info_got"]:
                    invitee_puuid: str = invitee_info["body"]["puuid"]
                    if invitee_puuid in blocked_puuids:
                        blocked_invitee_puuids.append(invitee_puuid)
            if len(blocked_invitee_puuids) == 0:
                logPrint("房间邀请中无黑名单玩家。\nNo blocked invitee detected in the lobby invitations.")
            else:
                logPrint("房间邀请中发现以下%d名玩家在黑名单中：\nFound the following %d blocked invitee(s) in the lobby invitations:" %(len(blocked_invitee_puuids), len(blocked_invitee_puuids)))
                blockList_df_filtered_invid: pandas.DataFrame = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_invitee_puuids)]], ignore_index = True)
                print(format_df(blockList_df_filtered_invid.loc[:, blockList_fields_to_print])[0])
                log.write(format_df(blockList_df_filtered_invid.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
            if len(blocked_member_puuids) > 0 and isLeader and gameflow_phase != "ReadyCheck" and gameflow_phase != "ChampSelect": #房主有权遣离黑名单成员（The lobby owner or party leader has priviledge to kick the blocked members）
                logPrint("检测到您是小队拥有者/房主。是否将黑名单成员移出小队/房间？\nDetected you're the party / lobby owner. Do you want to kick the blocked member(s)?")
                kick_str: str = logInput()
                kick: bool = bool(kick_str)
                if kick:
                    print(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print], print_index = True)[0])
                    log.write(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                    logPrint("请选择遣离方式：\nPlease select a kicking mode:\n0\t退出遣离（Quit kicking）\n1\t单个遣离（Single）\n2\t批量遣离（In batches）\n3\t全部遣离（All）")
                    while isLeader:
                        index_got: bool = False
                        mode: str = logInput()
                        if mode == "":
                            continue
                        elif mode[0] == "0":
                            break
                        elif mode[0] == "1":
                            logPrint("请输入要遣离的成员索引：\nPlease enter the index of the members to kick:")
                            while True:
                                kick_str: str = logInput()
                                if kick_str == "":
                                    continue
                                elif kick_str[0] == "0":
                                    index_got = False
                                    break
                                else:
                                    try:
                                        blocked_index: int = int(kick_str)
                                    except ValueError:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        if blocked_index in range(1, len(blockList_df_filtered_lobby)):
                                            kick_indices: list[int] = [blocked_index]
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        elif mode[0] == "2":
                            logPrint("是否需要对房间中的黑名单成员取子集？（输入任意键以开始打草稿，否则直接开始输入黑名单玩家索引。）\nDo you want to get a subset of the blocked member data? (Submit any non-empty string to make a draft, or null to input the blocked player index directly.)")
                            draft_str = logInput()
                            draft = bool(draft_str)
                            if draft:
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                while True:
                                    draft_option = logInput()
                                    if draft_option == "":
                                        continue
                                    elif draft_option[0] == "0":
                                        break
                                    elif draft_option[0] == "1":
                                        scope = {"format_df": format_df, "df": blockList_df_filtered_lobby.copy(deep = True), "fields": blockList_fields_to_print}
                                        logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[df["gameName"] == "WordlessMeteor"].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                        subscope(scope, log = log)
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            logPrint('请输入要移出的队友的索引（见下面黑名单玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the blocked members to kick (you may refer to the index column of the blocked players below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(blockList_df_filtered_lobby)) if blockList_df_filtered_lobby.loc[i, "gameName"] == "WordlessMeteor"]')
                            print(format_df(blockList_df_filtered_lobby.loc[1:, blockList_fields_to_print], print_index = True, start_index = 1)[0])
                            log.write(format_df(blockList_df_filtered_lobby.loc[1:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            logPrint("是否查看变量提示？（输入任意键已查看，否则不查看。）\nDo you want to refer to the variable hint? (Submit any non-empty string to refer, or null to skip.)")
                            check_hint_str: str = logInput()
                            check_hint: bool = bool(check_hint_str)
                            if check_hint:
                                logPrint('变量提示（Variable hints）：\nblockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()\nblockList_df = await sort_blockList_data(connection)\nblockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]\nblocked_puuids = set(map(lambda x: x["puuid"], blockList))\nblocked_member_puuids = []\nfor member in lobby["members"]:\n    if member["puuid"] in blocked_puuids:\n        blocked_member_puuids.append(member["puuid"])')
                            else:
                                logPrint("索引列表（Index list）：", end = "")
                            while True:
                                kick_str = logInput()
                                if kick_str == "":
                                    continue
                                elif kick_str == "0":
                                    index_got = False
                                    break
                                elif kick_str == "all":
                                    kick_indices = list(range(1, len(blockList_df_filtered_lobby)))
                                    index_got = True
                                    break
                                else:
                                    try:
                                        tmp = eval(kick_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        if isinstance(tmp, int) and tmp > 0 and tmp < len(blockList_df_filtered_lobby):
                                            kick_indices = [tmp]
                                            index_got = True
                                            break
                                        elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(blockList_df_filtered_lobby), tmp)) and len(tmp) == len(set(tmp)):
                                            kick_indices = tmp
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        elif mode[0] == "3":
                            kick_indices = list(range(1, len(blockList_df_filtered_lobby)))
                            index_got = True
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if index_got:
                            for blocked_index in kick_indices:
                                blocked_summonerId: int = blockList_df_filtered_lobby["summonerId"][blocked_index]
                                blocked_summonerName: str = blockList_df_filtered_lobby["gameName"][blocked_index] + "#" + blockList_df_filtered_lobby["gameTag"][blocked_index]
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{blocked_summonerId}/kick")).json()
                                logPrint(response)
                                if response == blocked_summonerId:
                                    logPrint(f"已将{blocked_summonerName}移出小队/房间。\nKicked {blocked_summonerName} from the party / lobby.")
                                else:
                                    if response["httpStatus"] == 400 and response["message"] == "INVALID_ROLE_TRANSITION":
                                        logPrint("遣离失败！对方可能已经离开小队/房间，或者您不再是小队拥有者/房主了。\nKick failed! The member may have left the party / lobby, or you're not the party or lobby owner anymore.")
                                    elif response["httpStatus"] == 400 and response["message"] == "INVALID_PARTY_STATE":
                                        logPrint("小队/房间即将进入或已经进入英雄选择阶段，无法将其移出。\nFailed to kick the member because the party / lobby are going to enter or has entered the champ select stage.")
                                    elif response["httpStatus"] == 404 and response["message"] == "Couldn't kick player: Not found":
                                        logPrint("遣离失败！对方已经离开小队/房间了。\nKick failed! The member has already left the party / lobby.")
                                    elif response["httpStatus"] == 404 and response["message"] == "SUMMONER_NOT_FOUND":
                                        logPrint("您已经不在小队/房间内了。\nYou're no longer in the party / lobby.")
                                    else:
                                        logPrint("遣离失败！\nKick failed!")
                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                            if "errorCode" in lobby_information and lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                logPrint("您已经不在小队/房间内了。\nYou're no longer in the party / lobby.")
                                break
                            else:
                                blocked_member_puuids = []
                                for member in lobby_information["members"]:
                                    if member["puuid"] in blocked_puuids:
                                        blocked_member_puuids.append(member["puuid"])
                                    if member["puuid"] == current_info["puuid"]:
                                        isLeader = member["isLeader"]
                                if len(blocked_member_puuids) == 0:
                                    logPrint("小队/房间中无黑名单成员。\nNo blocked member detected in the current party / lobby.")
                                    break
                                else:
                                    logPrint("小队/房间中发现以下%d名成员在黑名单中：\nFound the following %d blocked member(s) in the lobby:" %(len(blocked_member_puuids), len(blocked_member_puuids)))
                                    blockList_df_filtered_lobby = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_member_puuids)]], ignore_index = True)
                                    logPrint(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print])[0], write_time = False)
                        logPrint("请选择遣离方式：\nPlease select a kicking mode:\n0\t退出遣离（Quit kicking）\n1\t单个遣离（Single）\n2\t批量遣离（In batches）\n3\t全部遣离（All）")
        elif gameflow_phase == "ChampSelect":
            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            team: list[dict[str, Any]] = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
            blocked_player_puuids: list[str] = []
            for player in team:
                if player["puuid"] in blocked_puuids:
                    blocked_player_puuids.append(player["puuid"])
            if len(blocked_player_puuids) == 0:
                logPrint("英雄选择阶段无黑名单成员。\nNo blocked member detected during the champ select stage.")
            else:
                logPrint("英雄选择阶段发现以下%d名成员在黑名单中：\nFound the following %d blocked player(s) during the champ select stage:" %(len(blocked_player_puuids), len(blocked_player_puuids)))
                blockList_df_filtered_champSelect: pandas.DataFrame = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_player_puuids)]], ignore_index = True)
                print(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print])[0])
                log.write(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0])
        elif gameflow_phase in {"InProgress", "Reconnect"}:
            gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
            gameData: dict[str, Any] = gameflow_session["gameData"]
            team = gameData["teamOne"] + gameData["teamTwo"]
            blocked_player_puuids = []
            for player in team:
                if player["puuid"] in blocked_puuids:
                    blocked_player_puuids.append(player["puuid"])
            if len(blocked_player_puuids) == 0:
                logPrint("游戏中无黑名单成员。\nNo blocked member detected in game.")
            else:
                logPrint("游戏中发现以下%d名成员在黑名单中：\nFound the following %d blocked player(s) in game:" %(len(blocked_player_puuids), len(blocked_player_puuids)))
                blockList_df_filtered_champSelect = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_player_puuids)]], ignore_index = True)
                print(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print])[0])
                log.write(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
        logPrint("检测完成！是否重新检测？（输入任意键以退出检测，否则重新检测。）\nDetection finished! Try again? (Submit any non-empty string to quit detection, or null to detect again.)")
        redetect_str: str = logInput()
        redetect: bool = bool(redetect_str)
        if redetect:
            break

async def unblock(connection: Connection) -> None:
    blockList: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
    if isinstance(blockList, dict) and "errorCode" in blockList:
        if blockList["httpStatus"] == 503 and blockList["message"] == "Error response for GET /chat/v3/blocked: ":
            logPrint("查看黑名单的请求失败。\nThe request to check blocked players failed.")
        else:
            logPrint("黑名单获取失败！\nThe program failed to get the block list!")
    elif len(blockList) == 0:
        logPrint("这里什么都没有。你的聊天黑名单是空的。\nNothing to see here. Your block list is empty.")
    else:
        logPrint("聊天黑名单如下：\nBlock list:")
        player_summonerNames: list[str] = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], blockList))
        player_summonerIds: list[int] = list(map(lambda x: x["summonerId"], blockList))
        player_puuids: list[str] = list(map(lambda x: x["puuid"], blockList))
        blockList_df: pandas.DataFrame = await sort_blockList_data(connection)
        blockList_fields_to_print: list[str] = ["gameName", "gameTag", "puuid", "icon title"]
        print(format_df(blockList_df.loc[:, blockList_fields_to_print], print_index = True)[0])
        log.write(format_df(blockList_df.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
        logPrint("请选择取消拉黑模式：\nPlease select an unblocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个移出（Single）\n2\t批量移出（In batches）\n3\t全部移出（All）\n4\t从文件中移出（From file）")
        while True:
            index_got: bool = False
            mode: str = logInput()
            if mode == "":
                continue
            elif mode == "0":
                break
            elif mode == "1":
                logPrint("请输入要移出聊天黑名单的玩家索引或者名称：\nPlease enter the index or name of the blocked player to unblock:")
                print(format_df(blockList_df.loc[1:, blockList_fields_to_print], print_index = True, start_index = 1)[0])
                log.write(format_df(blockList_df.loc[1:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                while True:
                    unblock_str: str = logInput()
                    if unblock_str == "":
                        continue
                    elif unblock_str == "0":
                        break
                    else:
                        try:
                            player_index: int = int(unblock_str) - 1
                        except ValueError:
                            player_summonerName: str = unblock_str
                            if player_summonerName in player_summonerNames:
                                player_index = player_summonerNames.index(player_summonerName)
                            elif player_summonerName in set(map(str, player_summonerIds)):
                                player_index = player_summonerIds.index(int(player_summonerName))
                            elif player_summonerName in player_puuids:
                                player_index = player_puuids.index(player_summonerName)
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        else:
                            if player_index in range(len(blockList)):
                                unblock_indices: list[str] = [player_index]
                                index_got = True
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
            elif mode == "2":
                logPrint("请选择您输入要移出聊天黑名单的玩家信息的方式：\nPlease select a method of inputting the information of the blocked players to be unblocked:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                while True:
                    method: str = logInput()
                    if method == "":
                        continue
                    elif method[0] == "0":
                        break
                    elif method[0] == "1":
                        logPrint("是否需要对黑名单玩家取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current blocked player data? (Submit any non-empty string to make a draft, or null to input the blocked player index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": blockList_df.copy(deep = True), "fields": blockList_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope, log = log)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint('请输入要移出聊天黑名单的好友的索引（见下面聊天黑名单玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the blocked players to unblock (you may refer to the index column of the blocked player table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(blockList)) if blockList[i]["gameName"] == "WordlessMeteor"]')
                        print(format_df(blockList_df.loc[1:, blockList_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(blockList_df.loc[1:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint('变量提示（Variable hints）：\nblockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()\nplayer_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], blockList))\nplayer_summonerIds = list(map(lambda x: x["summonerId"], blockList))\nplayer_puuids = list(map(lambda x: x["puuid"], blockList))\nblockList_df = await sort_blockList_data(connection)')
                        while True:
                            unblock_str = logInput()
                            if unblock_str == "":
                                continue
                            elif unblock_str[0] == "0":
                                break
                            elif unblock_str == "all":
                                unblock_indices = list(range(len(blockList)))
                                index_got = True
                                break
                            else:
                                try:
                                    tmp = eval(unblock_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(tmp, int) and tmp > 0 and tmp < len(blockList_df):
                                        unblock_indices = [tmp - 1]
                                        index_got = True
                                        break
                                    elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(blockList_df), tmp)) and len(tmp) == len(set(tmp)):
                                        unblock_indices = list(map(lambda x: x - 1, unblock_indices))
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    elif method[0] == "2":
                        logPrint('''请输入要移出聊天黑名单的玩家的召唤师名。每个玩家的召唤师名格式为{玩家名称}#{名称编号}。输入“-1”以结束输入。\nPlease submit the names of the blocked players to be unblocked. Each player's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nblockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()\nblockList_df = await sort_blockList_data(connection)''')
                        unblock_indices = []
                        while True:
                            player_summonerName = logInput()
                            if player_summonerName == "":
                                continue
                            elif player_summonerName == "0":
                                index_got = False
                                break
                            elif player_summonerName == "-1":
                                break
                            else:
                                try:
                                    tmp = eval(player_summonerName)
                                except:
                                    player_summonerName_list: list[Any] = [player_summonerName]
                                else:
                                    if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (str, int)), tmp)):
                                        player_summonerName_list = tmp
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                for player_summonerName_iter in player_summonerName_list:
                                    if player_summonerName_iter in player_summonerNames:
                                        player_index = player_summonerNames.index(player_summonerName_iter)
                                    elif player_summonerName_iter in set(map(str, player_summonerIds)):
                                        player_index = player_summonerIds.index(int(player_summonerName_iter))
                                    elif player_summonerName_iter in player_puuids:
                                        player_index = player_puuids.index(player_summonerName_iter)
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    if not player_index in unblock_indices:
                                        unblock_indices.append(player_index)
                                        index_got = True
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    if index_got:
                        break
                    logPrint("请选择您输入要移出聊天黑名单的玩家信息的方式：\nPlease select a method of inputting the information of the blocked players to be unblocked:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
            elif mode == "3":
                unblock_indices = list(range(len(blockList)))
                index_got = True
            elif mode == "4":
                logPrint("是否需要测试玩家信息的获取？（输入任意键以开始打草稿，否则直接开始输入要移出聊天黑名单的玩家信息。）\nDo you want to test obtaining player information? (Submit any non-empty string to make a draft, or null to input the index of the players to unblock directly.)")
                draft_str = logInput()
                draft = bool(draft_str)
                if draft:
                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                    while True:
                        draft_option = logInput()
                        if draft_option == "":
                            continue
                        elif draft_option[0] == "0":
                            break
                        elif draft_option[0] == "1":
                            scope = {"get_info_name": get_info_name, "current_info": current_info, "blockList": blockList}
                            logPrint('示例（Examples）：\nprint(dir()) #输出exec函数使用的作用域中的变量名称（Output names of variables to the scope of `exec` function）\nimport os, pandas, pyperclip #引入需要的库（Introduce required libraries）\nos.system("CLS") #清屏（Clear screen）\ndf = pandas.read_excel("black list.xlsx", sheet_name = "Sheet1") #示例：从工作簿中读取黑名单数据（Example: Read black list data from a workbook）\nblock_puuids = set(df.iloc[:, 2])\nunblock_puuids = []\nfor player_puuid in player_puuids: #确定公示名单中已经解除拉黑的玩家（Determines the unblocked player in the announcement）\n    if not player_puuid in block_puuids:\n        unblock_puuids.append(player_puuid)\npyperclip.copy(str(unblock_puuids)) #将结果复制到全局剪贴板中，用于后续输入黑名单列表（Copy the result to the global clipboard for subsequently inputting the blocked player list）\n输入“-1”以退出测试。\nSubmit "-1" to quit the test.')
                            subscope(scope, log = log)
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                unblock_puuids: list[str] = []
                unblock_summonerNames: list[str] = []
                unblock_indices = []
                logPrint('请输入要拉黑的玩家名称列表。输入“0”以返回上一层。\nPlease submit a list containing summonerNames of players to unblock. Submit "0" to return to the last step.')
                while True:
                    unblock_str = logInput()
                    if unblock_str == "":
                        continue
                    elif unblock_str[0] == "0":
                        index_got = False
                        break
                    else:
                        try:
                            tmp = eval(unblock_str)
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        else:
                            if isinstance(tmp, list) and all(map(lambda x: isinstance(x, (int, str)), tmp)):
                                unblockNames: list[Any] = tmp
                                for unblockName in unblockNames:
                                    unblock_info = await get_info(connection, unblockName)
                                    if unblock_info["info_got"]:
                                        unblock_puuid = unblock_info["body"]["puuid"]
                                        unblock_summonerName: str = get_info_name(unblock_info["body"])
                                        if unblock_puuid == current_info["puuid"]:
                                            logPrint(f"[{unblockName}]你不在自己的聊天黑名单中。以前不在，以后也不会在。\nYou haven't been and will never be blocked by yourself.")
                                        elif not unblock_puuid in player_puuids:
                                            logPrint(f"[{unblockName}]" + "%s不在你的聊天黑名单中。\n%s isn't blocked." %(get_info_name(unblock_info["body"], unblock_info["body"])))
                                        elif not unblock_puuid in unblock_puuids:
                                            unblock_puuids.append(unblock_puuid)
                                            unblock_summonerNames.append(unblock_summonerName)
                                            unblock_indices.append(player_puuids.index(unblock_puuid))
                                            index_got = True
                                    else:
                                        logPrint(f"[{unblockName}]" + unblock_info["message"])
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if index_got:
                unblock_summonerNames = list(map(lambda x: player_summonerNames[x], unblock_indices))
                logPrint('您确定要将%s移出聊天黑名单吗？（输入“unblock”确认移出，否则不移出。）\nAre you sure you want to unblock %s? (Submit "unblock" to unblock those players, or null to cancel.)' %("、".join(unblock_summonerNames), ", ".join(unblock_summonerNames)))
                unblock_confirm_str: str = logInput()
                unblock_confirm = unblock_confirm_str == "unblock"
                if unblock_confirm:
                    for player_index in unblock_indices:
                        unblock_summonerName = player_summonerNames[player_index]
                        unblock_puuid = player_puuids[player_index]
                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/lol-chat/v1/blocked-players/{unblock_puuid}")).json()
                        logPrint(response)
                        if response == None:
                            logPrint("%s已被移出聊天黑名单。\n%s has been unblocked." %(unblock_summonerName, unblock_summonerName))
                        else:
                            if response["httpStatus"] == 400:
                                logPrint("您未能成功将%s移出聊天黑名单。也许TA已经不在其中了。\nYou failed to unblock %s. Maybe he/she's already out of it." %(unblock_summonerName, unblock_summonerName))
                            else:
                                logPrint("您未能成功将%s移出聊天黑名单。\nYou failed to unblock %s." %(unblock_summonerName, unblock_summonerName))
                    blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                    if len(blockList) == 0:
                        logPrint("这里什么都没有。你的聊天黑名单是空的。\nNothing to see here. Your block list is empty.")
                        break
                    else:
                        logPrint("聊天黑名单如下：\nBlock list:")
                        player_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], blockList))
                        player_summonerIds = list(map(lambda x: x["summonerId"], blockList))
                        player_puuids = list(map(lambda x: x["puuid"], blockList))
                        blockList_df = await sort_blockList_data(connection)
                        blockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]
                        print(format_df(blockList_df.loc[:, blockList_fields_to_print])[0])
                        log.write(format_df(blockList_df.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
            logPrint("请选择取消拉黑模式：\nPlease select an unblocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个移出（Single）\n2\t批量移出（In batches）\n3\t全部移出（All）\n4\t从文件中移出（From file）")

async def blacklist_behavior_simulation(connection: Connection) -> None:
    global current_info
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_hovercard: dict[str, Any] = await (await connection.request("GET", "/lol-hovercard/v1/friend-info/%s" %(current_info["puuid"]))).json()
    CustomURF_BlockList_enabled: bool = False
    while True:
        logPrint("请选择黑名单操作：\nPlease select an operation on the block list:\n0\t返回上一层（Return to the last step）\n{0}1\t查看黑名单（Check the block list）\n{0}2\t拉入聊天黑名单（Block）\n{0}3\t检测活跃状态（Detect active state）\n{0}4\t移出聊天黑名单（Unblock）".format("!" if CustomURF_BlockList_enabled else ""))
        option: str = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] == "1":
            if CustomURF_BlockList_enabled:
                blockList: list[dict[str, Any]] = blockList_CustomURF[:]
            else:
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
            if isinstance(blockList, dict) and "errorCode" in blockList:
                if blockList["httpStatus"] == 503 and blockList["message"] == "Error response for GET /chat/v3/blocked: ":
                    logPrint("查看黑名单的请求失败。\nThe request to check blocked players failed.")
                else:
                    logPrint("黑名单获取失败！\nThe program failed to get the block list!")
            elif len(blockList) == 0:
                logPrint("这里什么都没有。你的聊天黑名单是空的。\nNothing to see here. Your block list is empty.")
            else:
                blockList_df: pandas.DataFrame = await sort_blockList_data(connection, CustomURF_BlockList_enabled, blockList)
                blockList_fields_to_print: list[str] = ["gameName", "gameTag", "puuid", "icon title"]
                print(format_df(blockList_df.loc[:, blockList_fields_to_print])[0])
                log.write(format_df(blockList_df.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
        elif option[0] == "2": #这部分代码框架来自好友行为模拟函数中，但是判断行为大大简化（The following code frame come from `friend_behavior_simulation` function, but the judgments are greatly simplified）
            if CustomURF_BlockList_enabled:
                logPrint("该操作目前不可用。\nThis option isn't available for now.")
            else:
                await block(connection)
        elif option[0] == "3":
            if CustomURF_BlockList_enabled:
                blockList = blockList_CustomURF[:]
                blockList_df = await sort_blockList_data(connection, True, blockList)
            else:
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                if isinstance(blockList, dict) and "errorCode" in blockList:
                    if blockList["httpStatus"] == 503 and blockList["message"] == "Error response for GET /chat/v3/blocked: ":
                        logPrint("查看黑名单的请求失败。\nThe request to check blocked players failed.")
                    else:
                        logPrint("黑名单获取失败！\nThe program failed to get the block list!")
                    continue
                blockList_df = await sort_blockList_data(connection)
            await detect_blockedPlayer_state(connection, blockList, blockList_df)
        elif option[0] == "4":
            if CustomURF_BlockList_enabled:
                logPrint("该操作目前不可用。\nThis option isn't available for now.")
            else:
                await unblock(connection)
        elif option[0] == "5":
            #logPrint("警告：该模式会将与自定义无限火力行为无关的黑名单玩家移除。输入任意键以继续，否则退出。\nWarning: This option will unblock the players that are blocked not because of bad Custom URF behaviors. Submit any non-empty string to continue, or null to exit.")
            logPrint("输入任意键以启用自定义无限火力专用黑名单，否则回归到英雄联盟客户端的聊天黑名单。\nSubmit any non-empty string to enable the black list specially designed for Custom URF, or null to return to the normal League of Legends black list.")
            CustomURF_BlockList_enabled_str: str = logInput()
            if bool(CustomURF_BlockList_enabled_str):
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                if isinstance(blockList, dict) and "errorCode" in blockList:
                    if blockList["httpStatus"] == 503 and blockList["message"] == "Error response for GET /chat/v3/blocked: ":
                        logPrint("查看黑名单的请求失败。\nThe request to check blocked players failed.")
                    else:
                        logPrint("黑名单获取失败！\nThe program failed to get the block list!")
                else:
                    blocked_puuids = list(map(lambda x: x["puuid"], blockList))
                    if os.path.exists("自定义无限火力玩家行为记录表.xlsx"):
                        filepath: str = "自定义无限火力玩家行为记录表.xlsx"
                    else:
                        logPrint("请输入自定义无限火力玩家行为记录表的路径：\nPlease input the path of Custom URF player behavior table:")
                        while True:
                            filepath = logInput()
                            if os.path.exists(filepath) and filepath.endswith(".xlsx"):
                                break
                            elif filepath == "0":
                                break
                            else:
                                logPrint(f"没有找到{filepath}。请重新输入。\n{filepath} not found. Please try again.")
                        if filepath == "0":
                            continue
                    try:
                        df: pandas.DataFrame = pandas.read_excel(filepath, sheet_name = "Sheet2")
                        puuids_to_block: list[str] = []
                        for i in range(len(df)):
                            if not pandas.isnull(df["封禁时间"][i]) and not pandas.isnull(df["封禁天数"][i]):
                                if df["封禁时间"][i].timestamp() + 86400 * int(df["封禁天数"][i]) > time.time():
                                    if not pandas.isnull(df["玩家通用唯一识别码"][i]) and not df["玩家通用唯一识别码"][i] in puuids_to_block:
                                        puuids_to_block.append(df["玩家通用唯一识别码"][i])
                    except:
                        traceback_info = traceback.format_exc()
                        logPrint(traceback_info)
                        logPrint("文件格式错误！请从群文件重新导出到与该脚本同目录的位置，且表格内容不要变动。\nFile format ERROR! Please export the Tencent table to the same directory as this program again. Make sure the table content stays unchanged.")
                    else:
                        if len(puuids_to_block) == 0:
                            logPrint("暂无封禁的玩家。\nThere's not any suspended player.")
                        else:
                            blockList_CustomURF: list[str] = []
                            puuids_found: list[str] = []
                            summonerNames_to_block: list[str] = []
                            pid_postfix: str = current_hovercard["id"].split("@")[1]
                            for puuid in puuids_to_block:
                                player_info: dict[str, Any] = await get_info(connection, puuid)
                                if player_info["info_got"]:
                                    player_info_body: dict[str, Any] = player_info["body"]
                                    player = {"gameName": player_info_body["gameName"], "gameTag": player_info_body["tagLine"], "icon": player_info_body["profileIconId"], "id": player_info_body["puuid"] + "@" + pid_postfix, "name": "", "pid": player_info_body["puuid"] + "@" + pid_postfix, "puuid": player_info_body["puuid"], "summonerId": player_info_body["summonerId"]}
                                    blockList_CustomURF.append(player.copy())
                                    puuids_found.append(puuid)
                                    summonerNames_to_block.append(get_info_name(player_info_body))
                            if len(blockList_CustomURF) == 0:
                                logPrint("腾讯文档记录了封禁玩家，但是在该服务器上没有查询到这些玩家。请检查您运行的服务器是否正确。\nTencent table does record the suspended players, but the program failed to find these players on this server. Please check if you're running the client on a correct platform.")
                            else:
                                logPrint("目前处于封禁期的玩家：\nCurrently suspended players:")
                                for i in range(len(puuids_found)):
                                    logPrint(puuids_found[i] + "\t" + summonerNames_to_block[i])
                                CustomURF_BlockList_enabled = True
                        #以下代码将聊天黑名单与自定义无限火力黑名单同步。现已弃用（The following code synchronize the League of Legends block list with Custom URF block list. They're deserted now）
                        puuids_to_unblock: list[str] = []
                        for player in blockList:
                            if not player["puuid"] in blocked_puuids:
                                puuids_to_unblock.append(player["puuid"])
                        summonerNames_to_block = []
                        if len(puuids_to_block) != 0:
                            for puuid in puuids_to_block:
                                player_info = await get_info(connection, puuid)
                                if player_info["info_got"]:
                                    summonerNames_to_block.append(get_info_name(player_info["body"]))
                            if len(summonerNames_to_block) != 0:
                                logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.' %("、".join(summonerNames_to_block), ", ".join(summonerNames_to_block)))
                                block_confirm_str = logInput()
                                block_confirm = block_confirm_str == "block"
                                if block_confirm:
                                    for i in range(len(puuids_to_block)):
                                        puuid_to_block: str = puuids_to_block[i]
                                        summonerName_to_block = summonerNames_to_block[i]
                                        if not puuid_to_block in blocked_puuids:
                                            body = {"puuid": puuids_to_block[i]}
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-chat/v1/blocked-players", data = body)).json()
                                            logPrint(response)
                                            if response == None:
                                                logPrint("%s已被拉入聊天黑名单。你再也不会看到TA的在线状态或是收到来自TA的信息了。\n%s has been blocked. You will no longer see them online or receive their messages." %(summonerName_to_block, summonerName_to_block))
                                            else:
                                                logPrint("您未能成功将%s拉入聊天黑名单。\nYou failed to block %s." %(summonerName_to_block, summonerName_to_block))
                                        else:
                                            logPrint("%s已经在您的聊天黑名单中。\n%s is already blocked." %(summonerName_to_block, summonerName_to_block))
                        summonerNames_to_unblock: list[str] = []
                        if len(puuids_to_unblock) != 0:
                            for puuid in puuids_to_unblock:
                                player_info = await get_info(connection, puuid)
                                if player_info["info_got"]:
                                    summonerNames_to_unblock.append(get_info_name(player_info["body"]))
                            if len(summonerNames_to_unblock) != 0:
                                logPrint('您确定要将%s移出聊天黑名单吗？（输入“unblock”确认移出，否则不移出。）\nAre you sure you want to unblock %s? (Submit "unblock" to unblock those players, or null to cancel.)' %("、".join(summonerNames_to_unblock), ", ".join(summonerNames_to_unblock)))
                                unblock_confirm_str = logInput()
                                unblock_confirm = unblock_confirm_str == "unblock"
                                if unblock_confirm:
                                    for i in range(len(puuids_to_unblock)):
                                        puuid_to_unblock: str = puuids_to_unblock[i]
                                        summonerName_to_unblock: str = summonerNames_to_unblock[i]
                                        body: dict[str, str] = {"puuid": puuids_to_unblock[i]}
                                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/lol-chat/v1/blocked-players/{puuid_to_unblock}")).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("%s已被移出聊天黑名单。\n%s has been unblocked." %(summonerName_to_unblock, summonerName_to_unblock))
                                        else:
                                            logPrint("您未能成功将%s移出聊天黑名单。\nYou failed to unblock %s." %(summonerName_to_unblock, summonerName_to_unblock))
            else:
                CustomURF_BlockList_enabled = False

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    global sgpSession, log, logInput, logPrint
    log_folder = "日志（Logs）/Customized Program 16 - Friend and Blacklist Management"
    os.makedirs(log_folder, exist_ok = True)
    currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log = LogManager(os.path.join(log_folder, currentTime + ".log"), mode = "a+", encoding = "utf-8")
    logInput = log.logInput
    logPrint = log.logPrint
    await sgpSession.init(connection)
    await print_summoner_info(connection)
    await save_platform_info(connection)
    await prepare_data_resources(connection)
    while True:
        logPrint("请选择要模拟的行为类型：\nPlease select the type of behaviors to simulate:\n1\t好友（Friends）\n2\t黑名单（Block list）")
        bType: str = logInput()
        if bType == "" or bType[0] == "1":
            await friend_behavior_simulation(connection)
        elif bType[0] == "2":
            await blacklist_behavior_simulation(connection)
        else:
            break
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
