from lcu_driver import Connector
from lcu_driver.connection import Connection
import argparse, copy, json, numpy, os, pandas, pickle, psutil, pyperclip, random, re, requests, shutil, subprocess, time, traceback, urllib3, unicodedata, uuid
from urllib.parse import quote, unquote, urljoin
from typing import Any, Optional
from src.utils.logger import aInput, LogManager
from src.utils.summoner import get_summoner_data, get_info, get_info_name
from src.utils.format import optimize_bool_display, format_df, addDefaultStyle, lcuTime, getISOTime, verify_uuid, normalize_file_name
from src.utils.runtimeDebug import send_commands
from src.utils.webRequest import SGPSession, requestUrl
from src.core.config.const import ALL_GAMEFLOW_PHASES, BOT_DIFFICULTY_LIST, BOT_UUID, SPECTATOR_POLICY_LIST, GLOBAL_RESPONSE_LAG, REPORT_CATEGORY_LIST_CHAMPSELECT, REPORT_CATEGORY_LIST_POSTGAME
from src.core.config.headers import champSelect_player_header, custom_lobby_header, skin_header, conversation_header, grid_champion_header, chat_mutedPlayer_header, invid_header, perkPage_header, social_leaderboard_header, availableBot_header, member_header, inGame_playerAbility_header, inGame_championStat_header, inGame_allPlayer_header, inGame_event_header, inGame_metadata_header, ballot_player_header, eog_mastery_update_header, eog_stat_metadata_lol_header, eog_teamstat_data_lol_header, eog_playerstat_data_lol_header, eog_stat_metadata_tft_header, eog_stat_data_tft_header
from src.core.config.headers import LoLChampion_inventory_header as LoLChampion_header
from src.core.config.localization import gamemodes, gamemaps, ARAMmaps, gameTypes_config, spectatorPolicies, report_categories, tiers_all, team_colors_int, subteam_colors, rarities, krarities, augment_rarity, skinClassifications, damageTypes, conversationTypes, messageTypes, invidStates, invidTypes, slotTypes, availabilities, inventoryType_dict, ownershipTypes, botDifficulty_dict, roles, positions, eventTypes_liveclient, DragonTypes, team_colors_str, honorType_tooltip_headers, honorType_tooltip_bodies, zoom_scale_dict
from src.core.config.conditional_formatting import addFormat_inGame_allPlayer_wb
from src.core.dataframes.gameflow import get_gameflow_phase, get_champ_select_session, get_champSelect_player, sort_ChampSelect_players, sort_inGame_players, sort_eog_playerstat_lol_data, sort_eog_stat_tft_data
from src.core.dataframes.champions import test_bot, sort_inventory_champions
from src.core.dataframes.gameMode import check_available_queue
from src.core.dataframes.matchHistory import get_game_info_sgp, sort_LoLGame_info_sgp, sort_TFTGame_info

urllib3.disable_warnings() #忽略访问游戏数据时产生的警告（Neglect warnings produced when the program is accessing the in-game data）
parser = argparse.ArgumentParser()
parser.add_argument("-cp", "--cert_path", help = "指定游戏客户端接口的证书路径（Specify the path of the root certificate for game client API access", action = "store", type = str, default = "")
args = parser.parse_args()

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN & AwesomeABC
# 更新（Last update）：     2026/03/06
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

QUIT_UX_WARNING: str = '''警告：此操作将彻底清除与本次会话相关的英雄联盟客户端进程。（正在进行中的游戏不受影响。）这个操作是不可逆的。您确定要继续吗？（输入“quit”以继续，否则取消本次操作。）\nWarning: This operation will terminate all League Client processes related to this session. (On-going games won't be affected.) This operation is irreversible. Do you really want to continue? (Submit "quit" to continue, otherwise cancel this operation.)'''
message_hint_printed: bool = False
ballot_endpoint_notavailable_hint_printed: bool = False
expand_matchHistory_hint_printed: bool = False
gameClientApi_port_warning_printed: bool = False
gameClientApi_cert_not_specified_warning_printed: bool = False
collection_df_refresh: bool = False
skin_df_refresh: bool = False
current_cwd: str = os.getcwd()
session: requests.Session = requests.Session()
sgpSession: SGPSession = SGPSession()
platformId: str = ""
current_info: dict[str, Any] = {}
queues: dict[int, dict[str, Any]] = {}
summonerIcons: dict[int, dict[str, Any]] = {}
LoLChampions: dict[int, dict[str, Any]] = {}
recommended_position_for_champion: dict[str, dict[str, Any]] = {}
skins_flat: dict[int, dict[str, Any]] = {}
championSkins: dict[int, dict[str, Any]] = {}
skinlines: dict[int, dict[str, Any]] = {}
spells: dict[int, dict[str, Any]] = {}
available_spell_dict: dict[str, list[int]] = {}
LoLItems: dict[int, dict[str, Any]] = {}
perks: dict[int, dict[str, Any]] = {}
perkstyles: dict[int, dict[str, Any]] = {}
CherryAugments: dict[int, dict[str, Any]] = {}
TFTAugments: dict[str, dict[str, Any]] = {}
TFTCompanions: dict[str, dict[str, Any]] = {}
TFTTraits: dict[str, dict[str, Any]] = {}
TFTChampions: dict[str, dict[str, Any]] = {}
TFTItems: dict[str, dict[str, Any]] = {}
TFTDamageSkins: dict[str, dict[str, Any]] = {}
TFTMapSkins: dict[str, dict[str, Any]] = {}
strawberryMaps: dict[int, dict[str, Any]] = {}
wardSkins: dict[int, dict[str, Any]] = {}
collection_df: pandas.DataFrame = pandas.DataFrame()
skin_df: pandas.DataFrame = pandas.DataFrame()
log: LogManager = LogManager()

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 定义全局变量（Define global variables）
#-----------------------------------------------------------------------------
async def check_account_ready(connection: Connection) -> bool:
    platform_config: dict[str, Any] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
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
            logPrint("未知错误。\nUnknown error.")
        return False
    LoLChampions_source: list[dict[str, Any]] | dict[str, Any] = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
    if isinstance(LoLChampions_source, dict) and "errorCode" in LoLChampions_source:
        logPrint(LoLChampions_source)
        if LoLChampions_source["httpStatus"] == 404 and LoLChampions_source["message"] == "Champion data has not yet been received.":
            logPrint("未接收到英雄数据。请稍后再试。\nChampion data hasn't been received yet. Please try again later.")
        else:
            logPrint("未知错误。\nUnknown error.")
        return False
    return True

async def prepare_data_resources(connection: Connection) -> None:
    #准备数据资源（Prepare data resources）
    global session, platformId, current_info, queues, summonerIcons, LoLChampions, recommended_position_for_champion, skins_flat, championSkins, skinlines, spells, available_spell_dict, LoLItems, perks, perkstyles, CherryAugments, TFTAugments, TFTCompanions, TFTTraits, TFTChampions, TFTItems, TFTDamageSkins, TFTMapSkins, strawberryMaps, wardSkins, collection_df_refresh, collection_df, skin_df_refresh, skin_df
    ##大区信息（Platform information）
    logPrint("正在准备大区信息……\nPreparing platform information ...")
    platformId = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    ##自己的信息（Self info）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    ##队列（Queue）
    logPrint("正在加载队列信息……\nLoading queue information ...")
    queues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/queues.json")).json()
    queues = {queue["id"]: queue for queue in queues_source}
    ##召唤师图标（Summoner icon）
    logPrint("正在加载召唤师图标信息……\nLoading summoner icon information ...")
    summonerIcons_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcons_source}
    ##英雄（LoL champion）
    logPrint("正在加载英雄信息……\nLoading champion information ...")
    LoLChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
    LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampions_source}
    skins_flat = {}
    for champion in LoLChampions_source:
        for skin in champion["skins"]:
            skins_flat[skin["id"]] = skin
            for chroma in skin["chromas"]:
                skins_flat[chroma["id"]] = chroma
            for tier in skin["questSkinInfo"]["tiers"]:
                if not tier["id"] in skins_flat: #圣堂皮肤和终极皮肤中的系列与主皮肤存在重复的序号（There're redundant ids between the tier and the parent ultimate skin）
                    skins_flat[tier["id"]] = tier
    recommended_position_for_champion = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    ##皮肤（Champion skin）
    logPrint("正在加载皮肤信息……\nLoading skin information ...")
    championSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
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
    skinlines_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/skinlines.json")).json()
    skinlines = {skinline["id"]: skinline for skinline in skinlines_source}
    ##召唤师技能（Summoner spell）
    logPrint("正在加载召唤师技能信息……\nLoading summoner spell information")
    spells_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
    spells = {int(spell_iter["id"]): spell_iter for spell_iter in spells_source}
    gameModes: set[str] = set()
    for spell in spells_source:
        gameModes |= set(spell["gameModes"])
    available_spell_dict = {}
    for gameMode in sorted(gameModes):
        available_spell_dict[gameMode] = []
    for spell in spells_source:
        for gameMode in spell["gameModes"]:
            available_spell_dict[gameMode].append(spell["id"])
    ##英雄联盟装备（LoL item）
    logPrint("正在加载英雄联盟装备信息……\nLoading LoL item information ...")
    LoLItems_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/items.json")).json()
    LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItems_source}
    ##符文（Perk）
    logPrint("正在加载符文信息……\nLoading perk information ...")
    perks_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/perks.json")).json()
    perks = {int(perk_iter["id"]): perk_iter for perk_iter in perks_source}
    ##符文系（Perkstyle）
    logPrint("正在加载符文系信息……\nLoading perkstyle information ...")
    perkstyles_source: dict[str, Any] = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
    perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyles_source["styles"]}
    ##斗魂竞技场强化符文（Arena augment）
    logPrint("正在加载斗魂竞技场强化符文信息……\nLoading Arena augment information ...")
    CherryAugments_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/cherry-augments.json")).json()
    CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugments_source}
    ##云顶之弈基础信息（TFT basic）
    logPrint("正在加载云顶之弈基础信息……\nLoading TFT basic information ...")
    region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    locale: str = region_locale["locale"]
    URLPatch = "pbe" if platformId == "PBE1" or platformId == "PBE" else "latest"
    TFTBasic_url: str = "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(URLPatch, locale.lower())
    response, status, session = requestUrl("GET", TFTBasic_url, session = session, log = log)
    if status != 200:
        if status == 404:
            logPrint("云顶之弈基础信息获取失败！请检查以下链接的可用性。\nTFT basic information capture failure! Please check the URL availability. The program will skip this map.\n%s" %(TFTBasic_url))
        else:
            logPrint("云顶之弈基础信息获取失败！请检查系统网络状况和代理设置。\nTFT basic information capture failure! Please check the system network condition and proxy configuration.")
        TFTBasic_source: dict[str, Any] = {"items": []}
    else:
        TFTBasic_source = response.json()
    TFTAugments = {item["apiName"]: item for item in TFTBasic_source["items"]}
    ##云顶之弈小小英雄（TFT companion）
    logPrint("正在加载云顶之弈小小英雄信息……\nLoading TFT companion information ...")
    TFTCompanions_source: dict[str, Any] = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
    TFTCompanions = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanions_source}
    ##云顶之弈羁绊（TFT Trait）
    logPrint("正在加载云顶之弈羁绊信息……\nLoading TFT trait information ...")
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
    logPrint("正在加载云顶之弈棋子信息……\nLoading TFT champion information ...")
    TFTChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftchampions.json")).json()
    TFTChampions = {TFTChampion_iter["name"]: TFTChampion_iter["character_record"] for TFTChampion_iter in TFTChampions_source}
    ##云顶之弈装备（TFT items）
    logPrint("正在加载云顶之弈装备信息……\nLoading TFT item information ...")
    TFTItems_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftitems.json")).json()
    TFTItems = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItems_source}
    ##云顶之弈攻击特效（Damage skin）
    logPrint("正在加载云顶之弈攻击特效信息……\nLoading TFT damage skin information ...")
    TFTDamageSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftdamageskins.json")).json()
    TFTDamageSkins = {TFTDamageSkin_iter["itemId"]: TFTDamageSkin_iter for TFTDamageSkin_iter in TFTDamageSkins_source}
    ##云顶之弈棋盘皮肤（TFT map skin）
    logPrint("正在加载云顶之弈棋盘皮肤信息……\nLoading TFT map skin information ...")
    TFTMapSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftmapskins.json")).json()
    TFTMapSkins = {TFTMapSkin_iter["itemId"]: TFTMapSkin_iter for TFTMapSkin_iter in TFTMapSkins}
    ##无尽狂潮基础信息（Strawberry basics）
    logPrint("正在加载无尽狂潮基础信息……\nLoading Swarm basic information ...")
    strawberryHub_source: dict[str, Any] = await (await connection.request("GET", "/lol-game-data/assets/v1/strawberry-hub.json")).json()
    strawberryMaps = {strawberryMap_iter["value"]["Map"]["ItemId"]: strawberryMap_iter for strawberryMap_iter in strawberryHub_source[0]["MapDisplayInfoList"]}
    ##饰品（Ward skin）
    logPrint("正在加载守卫（眼）皮肤信息……\nLoading ward skin information ...")
    wardSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    wardSkins = {wardSkin_iter["id"]: wardSkin_iter for wardSkin_iter in wardSkins_source}
    ##藏品数据框（Collection dataframe）
    os.makedirs("cache", exist_ok = True)
    logPrint("正在加载藏品信息……\nLoading collections ...")
    collection_df_json_relpath: str = "cache/collection_df_json.pkl"
    collection_df_json_exist: bool = os.path.exists(collection_df_json_relpath)
    if collection_df_json_exist: #下面的注释适用于皮肤数据的获取，下文不再赘述（The following comments apply to skin data acquisition and won't be repeated below）
        with open(collection_df_json_relpath, "rb") as fp: #如果本地缓存存在，首先加载缓存（If the local cache exists, load it first）
            collection_df_json: dict[str, dict[str, dict[str, Any]]] = pickle.load(fp)
        if platformId in collection_df_json and current_info["puuid"] in collection_df_json[platformId] and isinstance(collection_df_json[platformId][current_info["puuid"]]["data"], pandas.DataFrame) and collection_df_json[platformId][current_info["puuid"]]["timestamp"] > time.time() - 86400: #本地缓存格式检查（Local cache format check）
            collection_df = collection_df_json[platformId][current_info["puuid"]]["data"] #严格地讲，这里应该设置一个数据框格式校验（Strictly speaking, here needs a dataframe format check）
        else: #如果本地缓存的上次更新日期是一天前，或者本地缓存格式不正确，则需要重新获取数据（If the local cache was updated over a day ago, or the format isn't correct, it needs to be refreshed）
            collection_df_refresh = True
    else:
        collection_df_json = {} #本地缓存不存在时，初始化空的缓存字典（When the local cache doesn't exist, initialize an empty cache dictionary）
    if collection_df_refresh or not collection_df_json_exist: #当用户需要更新数据或者本地缓存不存在时，更新数据（When the user asks to update data or the local cache doesn't exist, refresh the data）
        collection_df = await get_collection(connection) #更新数据（Update data）
        collection_df_json_update: dict[str, Any] = {"gameName": current_info["gameName"], "tagLine": current_info["tagLine"], "data": collection_df, "timestamp": time.time()}
        if not platformId in collection_df_json:
            collection_df_json[platformId] = {}
        if not current_info["puuid"] in collection_df_json[platformId]:
            collection_df_json[platformId][current_info["puuid"]] = {}
        collection_df_json[platformId][current_info["puuid"]] = collection_df_json_update #更新缓存（Update cache）
        with open(collection_df_json_relpath, "wb") as fp: #将更新后的缓存写入本地文件（Write the updated cache to the local file）
            pickle.dump(collection_df_json, fp)
        collection_df_refresh = collection_df_json_exist = False #后续更新数据时，需要重置这两个逻辑变量。下同（When the user updates the data, these two variables need to be reset. Same below）
        logPrint("已更新藏品数据缓存。\nCollection data cache has been updated.")
    else:
        logPrint("已加载藏品数据缓存。\nCollection data cache has been loaded.")
    ##皮肤数据框（Skin dataframe）
    logPrint("正在整理皮肤数据……\nOrganizing skin data ...")
    skin_df_json_relpath: str = "cache/skin_df_json.pkl"
    skin_df_json_exist: bool = os.path.exists(skin_df_json_relpath)
    if skin_df_json_exist:
        with open(skin_df_json_relpath, "rb") as fp:
            skin_df_json: dict[str, dict[str, dict[str, Any]]] = pickle.load(fp)
        if platformId in skin_df_json and current_info["puuid"] in skin_df_json[platformId] and isinstance(skin_df_json[platformId][current_info["puuid"]]["data"], pandas.DataFrame) and skin_df_json[platformId][current_info["puuid"]]["timestamp"] > time.time() - 86400:
            skin_df = skin_df_json[platformId][current_info["puuid"]]["data"]
        else:
            skin_df_refresh = True
    else:
        skin_df_json = {}
    if skin_df_refresh or not skin_df_json_exist:
        skin_df = await sort_skin_data(connection)
        skin_df_json_update: dict[str, Any] = {"gameName": current_info["gameName"], "tagLine": current_info["tagLine"], "data": skin_df, "timestamp": time.time()}
        if not platformId in skin_df_json:
            skin_df_json[platformId] = {}
        if not current_info["puuid"] in skin_df_json[platformId]:
            skin_df_json[platformId][current_info["puuid"]] = {}
        skin_df_json[platformId][current_info["puuid"]] = skin_df_json_update
        with open(skin_df_json_relpath, "wb") as fp:
            pickle.dump(skin_df_json, fp)
        skin_df_refresh = skin_df_json_exist = False
        logPrint("已更新皮肤数据缓存。\nSkin data cache has been updated.")
    else:
        logPrint("已加载皮肤数据缓存。\nSkin data cache has been loaded.")

#-----------------------------------------------------------------------------
# 通用行为（Generic actions）
#-----------------------------------------------------------------------------
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

async def handle_invitations(connection: Connection) -> None:
    receivedInvitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
    if len(receivedInvitations) == 0:
        logPrint("您还没有收到邀请。\nYou've not received any invitation.")
    else:
        logPrint("您收到的邀请信息如下：\nYour received invitations:")
        invid_df: pandas.DataFrame = await sort_received_invitations(connection)
        invid_fields_to_print: list[str] = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
        print(format_df(invid_df.loc[:, invid_fields_to_print], print_index = True)[0])
        log.write(format_df(invid_df.loc[:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
        logPrint("请选择一个邀请以接受：\nPlease select an invitation to accept:")
        while True:
            invid_index_str: str = logInput()
            if invid_index_str == "":
                continue
            elif invid_index_str == "0":
                break
            elif invid_index_str in list(map(str, range(1, len(invid_df)))):
                invid_index: int = int(invid_index_str)
                invitationId: str = invid_df["invitationId"][invid_index]
                invid_owner: str = invid_df["fromSummonerName"][invid_index]
                response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/accept")).json()
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

async def join_party(connection: Connection, partyId: str, data: Optional[dict[str, Any]] = None) -> tuple[Optional[dict[str, Any]], str]:
    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join", data = data)).json()
    if isinstance(response, dict) and "errorCode" in response:
        if response["httpStatus"] == 400:
            if response["message"] == "PARTY_SIZE_LIMIT":
                message = "你试图加入的小队已经满员。\nThe open party you attempted to join is full."
            elif response["message"] == "PARTY_NOT_FOUND":
                message = "没有激活的游戏。\nActive game was not found."
            elif response["message"] == "INVALID_ROLE_TRANSITION":
                message = "你已被移出小队。你必须收到邀请才能重新加入。\nYou have been removed from the party. You must receive an invite to rejoin."
            elif response["message"] == "INVALID_WHILE_PARTY_IN_ACTION":
                message = "你无法加入该小队，因为该小队正在队列中。\nYou were not able to join the party because the party is now in queue."
            elif response["message"] == "INVALID_PERMISSIONS":
                message = "加入游戏时发生错误。请检查密码。\nThere was an error in joining this game. Please check the lobby password."
            else:
                message = "你无法加入该小队。\nYou were not able to join the party."
        else:
            message = "你无法加入该小队。\nYou were not able to join the party."
    else:
        message = ""
    return (response, message)

async def join_game(connection: Connection) -> bool:
    logPrint("您想要加入小队还是自定义房间？\nWhich kind do you want to join, party or lobby?\n1\t小队（Party）\n2\t自定义房间（Custom lobby）\n3\t冠军杯赛（Clash）")
    while True:
        suboption: str = logInput()
        if suboption == "":
            continue
        elif suboption[0] == "0":
            return False
        elif suboption[0] == "1":
            logPrint("请输入小队编号：\nPlease input the partyId:")
            while True:
                partyId: str = logInput()
                if partyId == "":
                    continue
                elif partyId == "0":
                    break
                else:
                    response, message = await join_party(connection, partyId)
                    if isinstance(response, dict) and "errorCode" in response:
                        logPrint(response)
                        logPrint(message)
                    else:
                        lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                        if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                            logPrint("加入失败。\nJoin failed.")
                        else:
                            logPrint("您成功加入该小队！\nYou successfully joined this party.")
                            return True
                logPrint("请输入小队编号：\nPlease input the partyId:")
        elif suboption[0] == "2":
            custom_lobby_df: pandas.DataFrame = await sort_custom_lobbies(connection)
            custom_lobby_df_fields_to_print: list[str] = ["id", "partyId", "lobbyName", "ownerDisplayName", "mapId", "mapName", "hasPassword", "spectatorPolicy", "filledPlayerRatio", "filledSpectatorRatio"]
            if len(custom_lobby_df) == 1:
                logPrint("当前无自定义房间。\nThere's not any custom lobby for now.")
            else:
                logPrint("该大区的所有自定义房间如下：\nAll custom lobbies on this server are as follows:")
                print(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], print_index = True)[0])
                log.write(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                logPrint("请选择一个房间：\nPlease select a lobby:")
                while True:
                    lobby_index_str: str = logInput()
                    if lobby_index_str == "":
                        continue
                    elif lobby_index_str == "0":
                        break
                    elif lobby_index_str in list(map(str, range(1, len(custom_lobby_df)))):
                        lobby_index: int = int(lobby_index_str)
                        lobbyId: int = custom_lobby_df["id"][lobby_index]
                        partyId: str = custom_lobby_df["partyId"][lobby_index]
                        lobbyOwnerName: str = custom_lobby_df["ownerDisplayName"][lobby_index]
                        if custom_lobby_df["hasPassword"][lobby_index] == "√":
                            logPrint("请输入密码。\nPlease input the password.")
                            lobbyPassword: str = logInput()
                        else:
                            lobbyPassword = ""
                        if lobbyId == 0 and verify_uuid(partyId): #新版自定义房间接口不支持直接观战。这里假设有朝一日能够同时通过新版和旧版接口加入小队（New custom lobby API doesn't support spectating directly. Suppose one can join a custom game through both new and old APIs one day）
                            body: dict[str, Any] = {"lobbyPassword": lobbyPassword, "team": None} #从日志中查到team参数为空（Log trace shows that `team` is null）
                            response, message = await join_party(connection, partyId, data = body)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint(response)
                                logPrint(message)
                            else:
                                lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                    logPrint("加入失败。\nJoin failed.")
                                else:
                                    logPrint("您成功加入该房间！\nYou successfully joined this lobby.")
                                    return True
                        else: #旧版自定义房间接口（Old custom lobby API）
                            logPrint("输入任意键以观战，否则不观战。\nSubmit any non-empty string to spectate, or null to refuse spectating.")
                            asSpectator_str: str = logInput()
                            asSpectator: bool = bool(asSpectator_str)
                            body: dict[str, str | bool] = {"asSpectator": asSpectator} if lobbyPassword == "" else {"password": lobbyPassword, "asSpectator": asSpectator}
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v1/custom-games/{lobbyId}/join", data = body)).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                if response["httpStatus"] == 500 and response["message"] == "Error response for POST /lol-login/v1/session/invoke: LCDS invoke to gameService.observeGameV4 failed: Server.Processing, com.riotgames.platform.game.GameObserverModeNotEnabledException : null":
                                    logPrint("该自定义房间不允许观战。\nThis custom lobby doesn't allow spectating.")
                                elif response["httpStatus"] == 403 and response["message"] == "Error response for POST /lol-login/v1/session/invoke: LCDS invoke to gameService.joinGameV4 failed: Server.Processing, com.riotgames.platform.game.IncorrectPasswordException : null":
                                    logPrint("验证失败。如果该房间设置了密码，请检查密码是否有误。\nVerification failed. If this lobby has password, please check if the password is correct.")
                                elif response["httpStatus"] == 404 and response["message"] == f"Error response for POST /lol-login/v1/session/invoke: LCDS invoke to gameService.observeGameV4 failed: Server.Processing, com.riotgames.platform.game.GameNotFoundException : Game {lobbyId} was not found to join.":
                                    logPrint("没有激活的游戏。\nActive game was not found.")
                                else:
                                    logPrint(f"您未能加入{lobbyOwnerName}的自定义房间。\nYou failed to join {lobbyOwnerName}'s custom lobby.")
                            else:
                                logPrint("您加入了该房间。\nYou joined this lobby.")
                                return True
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    custom_lobby_df = await sort_custom_lobbies(connection)
                    if len(custom_lobby_df) == 1:
                        logPrint("当前无自定义房间。\nThere's not any custom lobby for now.")
                        break
                    else:
                        print(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], print_index = True)[0])
                        log.write(format_df(custom_lobby_df.loc[:, custom_lobby_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        logPrint("请选择一个房间：\nPlease select a lobby:")
        elif suboption[0] == "3":
            logPrint("请输入冠军杯赛代码：\nPlease enter the tournament code:")
            while True:
                tournament_code: str = logInput()
                if tournament_code == "":
                    continue
                elif tournament_code == "0":
                    break
                else:
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v1/tournaments/{tournament_code}/join")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        if response["message"] == "Failed to join tournament game":
                            logPrint("加入失败。\nFailed to join.")
                        else:
                            logPrint("加入失败。\nFailed to join.")
                    else:
                        logPrint("加入成功。\nSuccessfully joined.")
                        return True
                logPrint("请输入冠军杯赛代码：\nPlease enter the tournament code:")
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            continue
        logPrint("您想要加入小队还是自定义房间？\nWhich kind do you want to join, party or lobby?\n1\t小队（Party）\n2\t自定义房间（Custom lobby）\n3\t冠军杯赛（Clash）")

async def manage_ux(connection: Connection) -> None:
    logPrint("请选择您想要对英雄联盟客户端执行的操作：\nPlease select an operation you want to do with LeagueClientUx.exe:\n1\t窗口管理（Window management）\n2\t进程管理（Process management）")
    while True:
        option: str = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('''请选择一个拳头客户端相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a riot client-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t删除英雄联盟客户端的CPU亲和性配置（Deletes the current runtime affinity of the application）\n2\t查看英雄联盟客户端的CPU亲和性配置（Get the current runtime affinity of the application）\n3\t设置英雄联盟客户端的CPU亲和性（Sets the current runtime affinity of the application）\n4\t获取应用名称（Get the application name without file extension）\n5\t查看应用程序端口（Get the TCP port number that the remoting server is listening on）\n6\t查看英雄联盟客户端认证令牌（Return the auth token used by the remoting server）\n7\t查看可用于英雄联盟对话的剪贴板（Check the clipboard which applies in conversations in League of Legends）\n8\t复制一段文字（Copy a string）\n9\t查看英雄联盟进程的命令行变量（Get the command line parameters for the application）\n10\t重新启动用户体验进程（Kill the ux process and restarts it. Used only when the ux process crashes）\n!11\t关闭英雄联盟用户体验界面（Kill the ux process）\n12\t启动英雄联盟用户体验界面（Launch the ux process）\n13\t查看机器码（Get base64 encoded uuid identifying the user's machine）\n14\t设置新的命令行变量（Set a new endpoint for passing in new data）\n15\t在浏览器中处理用户体验界面请求（Opens a URL in the player's system browser）\n16\t查看当前地区和语言设置（Check the current region and language）\n17\t在浏览器中打开LCU API的Swagger格式化说明文档（Open swagger in the default browser）\n18\t隐藏启动时的闪屏界面（Hide the splash screen when starting）\n19\t显示启动时的闪屏界面（Show the splash screen when starting）\n20\t查看当前操作系统信息（Get basic system information: OS, memory, processor speed, and number of physical cores）\n21\t追踪客户端运行情况（Retrieve a completed scheduler trace）\n!22\t注销当前登录用户（Unload the UX process）\n23\t一次性将当前英雄联盟客户端窗口置顶（Allow the background process to launch the game into the foregound）\n24\t检查用户体验进程是否崩溃（Returns whether the ux has crashed or not）\n25\t使英雄联盟客户端的任务栏图标闪烁（Flash the ux process' main window and the taskbar/dock icon, if they exist）\n26\t设置英雄联盟用户体验界面加载为已完成（Send a ux notification that it has completed loading the main window.）\n27\t最小化英雄联盟客户端窗口（Minimize the ux process and all its windows if it exists. This does not kill the ux）\n28\t呈现英雄联盟客户端窗口（Shows the ux process if it exists; create and show if it does not）\n29\t查看用户体验界面状态（Get the current Ux state）\n30\t确认用户体验界面状态更新（Acknowledges the update to the Ux state）\n31\t注销当前认证令牌（Unregister an existing auth token）\n32\t设置一个认证令牌（Register an auth token. This is any alpha-numeric string that will be used as a password with the riot user when making requests）\n33\t查看崩溃报告的标识信息（Get the crash reporting environment identifier）\n34\t设置崩溃报告环境（Tag the crash with an environment so it can be filtered more easily）\n35\t添加崩溃日志信息（Add the enclosed log to the app's crash report）\n36\t启用故障修复（Enable crash repair）\n37\t查看英雄联盟客户端的窗口尺寸（Get the last known posted zoom-scale value）\n38\t设置英雄联盟客户端的窗口尺寸（Handle changing the zoom scale value）\n39\t查看当前用户体验进程状态（Return information about the process-control）\n!40\t结束英雄联盟客户端进程（Quit the application）''')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection, log = log)
                elif suboption == "0":
                    break
                elif suboption in list(map(str, range(1, 40))):
                    if suboption == "1":
                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/riotclient/affinity")).json()
                    elif suboption == "2":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/affinity")).json()
                    elif suboption == "3":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"string"\nnewAffinity = ', end = "")
                        try:
                            body_str: str = logInput()
                            body = eval(body_str)
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/affinity", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "4":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/app-name")).json()
                    elif suboption == "5":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/app-port")).json()
                    elif suboption == "6":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/auth-token")).json()
                    elif suboption == "7":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/clipboard")).json()
                    elif suboption == "8":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n"string"\nwriteString = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/clipboard", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "9":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
                    elif suboption == "10":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/kill-and-restart-ux")).json()
                    elif suboption == "11":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/kill-ux")).json()
                    elif suboption == "12":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/launch-ux")).json()
                    elif suboption == "13":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/machine-id")).json()
                    elif suboption == "14":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n["string"]\nargs = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/new-args", data = body)).json()
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
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/open-url-in-browser", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "16":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/region-locale")).json()
                    elif suboption == "17":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/show-swagger")).json()
                    elif suboption == "18":
                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/riotclient/splash")).json()
                    elif suboption == "19":
                        logPrint('请输入一个插画字符串：\nPlease input a splash string:\nsplash = ', end = "")
                        splash = logInput()
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/riotclient/splash?splash={splash}")).json()
                    elif suboption == "20":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/system-info/v1/basic-info")).json()
                    elif suboption == "21":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/trace")).json()
                    elif suboption == "22":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/unload")).json()
                    elif suboption == "23":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/ux-allow-foreground")).json()
                    elif suboption == "24":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/ux-crash-count")).json()
                    elif suboption == "25":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/ux-flash")).json()
                    elif suboption == "26":
                        response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/riotclient/ux-load-complete")).json()
                    elif suboption == "27":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/ux-minimize")).json()
                    elif suboption == "28":
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/ux-show")).json()
                    elif suboption == "29":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/ux-state")).json()
                    elif suboption == "30":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n0\nrequestId = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/riotclient/ux-state/ack", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "31":
                        logPrint("请输入当前认证令牌：\nPlease input the current auth token:\nauthToken = ", end = "")
                        authToken = logInput()
                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/riotclient/v1/auth-tokens/{authToken}")).json()
                    elif suboption == "32":
                        logPrint("请输入一个认证令牌：\nPlease input an auth token:\nauthToken = ", end = "")
                        authToken = logInput()
                        response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/riotclient/v1/auth-tokens/{authToken}")).json()
                    elif suboption == "33":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/v1/crash-reporting/environment")).json()
                    elif suboption == "34":
                        logPrint('请输入请求主体：\nPlease input the request body:\n格式（Format）：\n{"environment": "string", "userName": "string", "userId": "string"}\nenvironment = ', end = "")
                        try:
                            body_str = logInput()
                            body = eval(body_str)
                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/riotclient/v1/crash-reporting/environment", data = body)).json()
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
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/v1/crash-reporting/logs", data = body)).json()
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("格式错误！\nFormat error!")
                            continue
                    elif suboption == "36":
                        body = {"action": "FixBrokenPermissions"}
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/v1/elevation-requests", data = body)).json()
                    elif suboption == "37":
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/riotclient/zoom-scale")).json()
                    elif suboption == "38":
                        logPrint("请输入新的窗口尺寸：\nPlease input a new zoom scale:\nnewZoomScale = ", end = "")
                        newZoomScale = logInput()
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/zoom-scale?newZoomScale={newZoomScale}")).json()
                    else:
                        response: Optional[dict[str, Any]] = await (await connection.request("GET", "/process-control/v1/process")).json()
                    logPrint(response)
                elif suboption == "40":
                    logPrint(QUIT_UX_WARNING)
                    quit_str: str = logInput()
                    quit: bool = quit_str == "quit"
                    if quit:
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/process-control/v1/process/quit")).json()
                        logPrint(response)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option[0] == "0":
            break
        elif option[0] == "1":
            logPrint("请选择一个操作：\nPlease select an action on the window:\n1\t显示窗口（Show the window）\n2\t最小化窗口（Minimize the window）\n3\t显示高亮通知（Enable taskbar flashing）\n4\t设置窗口尺寸（Resize the window）")
            while True:
                action: str = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/ux-show")).json()
                    logPrint(response)
                elif action[0] == "2":
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/ux-minimize")).json()
                    logPrint(response)
                elif action[0] == "3":
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/ux-flash")).json()
                    logPrint(response)
                elif action[0] == "4":
                    logPrint("请选择一个窗口尺寸：\nPlease select a window size:\n1\t0.8\t1024 × 576\n2\t1\t1280 × 720\n3\t1.25\t1600 × 900\n4\t1.5\t1920 × 1080\n5\t自定义（Customize）")
                    current_zoomScale = await (await connection.request("GET", "/riotclient/zoom-scale")).json()
                    if isinstance(current_zoomScale, float):
                        current_window_size = zoom_scale_dict.get(current_zoomScale, "")
                        print(f"当前窗口尺寸：\t{current_window_size}")
                    while True:
                        zoomScale_got: bool = False
                        scale_option: str = logInput()
                        if scale_option == "":
                            continue
                        elif scale_option[0] == "0":
                            zoomScale_got = False
                            break
                        elif scale_option[0] in list(map(str, range(1, 5))):
                            update_zoomScale: float = list(zoom_scale_dict.keys())[int(scale_option[0]) - 1]
                            zoomScale_got = True
                            break
                        elif scale_option[0] == "5":
                            logPrint("提示：您可以在客户端内按Ctrl和上下方向键以切换窗口尺寸。\nHint: You can press Ctrl + ↑/↓ to toggle the client window size.")
                            logPrint("请输入窗口尺寸比例：\nPlease input a window size:")
                            while True:
                                update_zoomScale_str: str = logInput()
                                if update_zoomScale_str == "":
                                    continue
                                elif update_zoomScale_str == "0":
                                    zoomScale_got = False
                                    break
                                else:
                                    try:
                                        tmp = eval(update_zoomScale_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入格式有误！请重新输入。\nERROR format! Please try again.")
                                    else:
                                        if isinstance(tmp, (int, float)):
                                            update_zoomScale = tmp
                                            zoomScale_got = True
                                            break
                                        else:
                                            logPrint("请输入一个小数。\nPlease input a float.")
                            if zoomScale_got:
                                break
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            continue
                        logPrint("请选择一个窗口尺寸：\nPlease select a window size:\n1\t0.8\t1024 × 576\n2\t1\t1280 × 720\n3\t1.25\t1600 × 900\n4\t1.5\t1920 × 1080\n5\t自定义（Customize）")
                    if zoomScale_got:
                        time.sleep(GLOBAL_RESPONSE_LAG)
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/riotclient/zoom-scale?newZoomScale={update_zoomScale}")).json()
                        logPrint(response)
                        if isinstance(response, dict) and "errorCode" in response:
                            logPrint("未知错误。\nUnknown error.")
                        else:
                            new_zoomScale: float = await (await connection.request("GET", "/riotclient/zoom-scale")).json()
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
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/launch-ux")).json()
                    logPrint(response)
                elif action[0] == "2":
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/kill-ux")).json()
                    logPrint(response)
                    if not (isinstance(response, dict) and "errorCode" in response):
                        logPrint("已发送关闭窗口的请求。请勿退出本程序，否则后续将无法再对当前的客户端会话进行操作。\nA request to kill the ux has been sent. Please don't exit this program, otherwise you won't be able to perform any operations on the current League Client session.")
                elif action[0] == "3":
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/riotclient/kill-and-restart-ux")).json()
                    logPrint(response)
                elif action[0] == "4":
                    logPrint(QUIT_UX_WARNING)
                    quit_str: str = logInput()
                    quit: bool = quit_str == "quit"
                    if quit:
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/process-control/v1/process/quit")).json()
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

async def chat(connection: Connection) -> None:
    global message_hint_printed
    if not message_hint_printed:
        logPrint("（提示：编辑好内容后，在终端中按Ctrl-D以插入结束字符，再按回车键发送消息。插入两个Ctrl-D以取消对话。插入三个Ctrl-D以刷新消息。如果终端不支持插入Ctrl-D字符，新建一个Python工作台，引入pyperclip库后使用pyperclip.copy(chr(4))以复制Ctrl-D实际代表的字符，再粘贴在聊天终端中，按回车键发送消息。）\n(Hint: If you finished editing the message, you must press Ctrl-D to insert the ending character and then press Enter to send the message. Append double Ctrl-D to cancel chatting. Append triple Ctrl-D to refresh messages. If the current terminal doesn't support inserting Ctrl-D character, please create a Python console, import pyperclip library and then use `pyperclip.copy(chr(4))` to copy the character that Ctrl-D actually represents. Finally, paste it into the current terminal and press Enter to send the message.)")
        message_hint_printed = True
    while True:
        back: bool = False
        conversations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
        if len(conversations) != 0:
            logPrint("请选择对话：\nPlease select a conversation:")
            conversation_df: pandas.DataFrame = await sort_conversation_metadata(connection)
            print(format_df(conversation_df, print_index = True)[0])
            log.write(format_df(conversation_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
            while True:
                conversation_index_str: str = logInput()
                if conversation_index_str == "":
                    continue
                elif conversation_index_str == "0":
                    back = True
                    break
                elif conversation_index_str in list(map(str, range(1, len(conversation_df)))):
                    conversation_index: int = int(conversation_index_str)
                    chatId: str = conversation_df["id"][conversation_index]
                    messages: list[dict[str, Any]] = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                    if "errorCode" in messages and messages["httpStatus"] == 404:
                        logPrint("该对话尚未激活。请在客户端右边的好友列表中点击该好友，或者直接发送一条聊天类消息，以激活对话。\nThis conversation hasn't been activated yet. Please click this friend in the friend list at the right side of the client, or send a chat message directly to activate the conversation.")
                    mTypeDict: dict[str, str] = {"1": "chat", "2": "groupchat", "3": "system", "4": "information", "5": "celebration"}
                    logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                    while True:
                        mType: str = logInput()
                        if mType == "":
                            continue
                        elif mType[0] == "0":
                            break
                        elif mType[0] in mTypeDict:
                            messageType: str = mTypeDict[mType[0]]
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
                                    timestamp: str = message["timestamp"][:10] + " " + message["timestamp"][11:23]
                                    fromInfo: dict[str, Any] = await get_info(connection, message["fromPuuid"])
                                    from_summonerName: str = get_info_name(fromInfo["body"]) if fromInfo["info_got"] else ""
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
                                logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                                break
                            else:
                                body: dict[str, str] = {"type": messageType, "body": text}
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-chat/v1/conversations/{chatId}/messages", data = body)).json()
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

async def debug_gameflow_phase(connection: Connection) -> str:
    gameflow_phase_dict: dict[int, str] = {1: "None", 2: "Lobby", 3: "Matchmaking", 4: "ReadyCheck", 5: "ChampSelect", 6: "InProgress", 7: "Reconnect", 8: "WaitingForStats", 9: "PreEndOfGame", 10: "EndOfGame"}
    gameflow_phase_df: pandas.DataFrame = pandas.DataFrame(data = {"Index": list(range(1, 11)), "游戏状态": ["无", "房间内", "阵容匹配", "就绪确认", "英雄选择", "游戏中", "重连", "等待数据", "赛后预结算", "赛后结算"], "GameflowPhase": ["None", "Lobby", "Matchmaking", "ReadyCheck", "ChampSelect", "InProgress", "Reconnect", "WaitingForStats", "PreEndOfGame", "EndOfGame"]})
    while True:
        logPrint("请选择要调试的游戏状态：\nPlease select a gameflow phase to debug:")
        logPrint(format_df(gameflow_phase_df, print_header = False, align = "<")[0], write_time = False)
        option: str = logInput()
        if option == "0":
            return ""
            break
        elif option in set(map(str, range(1, 11))):
            return gameflow_phase_dict[int(option)]
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")

async def toggle_nonfriend_game_invite(connection: Connection) -> None:
    lol_notifications: dict[str, Any] = await (await connection.request("GET", "/lol-settings/v2/account/LCUPreferences/lol-notifications")).json()
    nonfriend_invitation_blocked: bool = isinstance(lol_notifications, dict) and "blockNonFriendGameInvites" in lol_notifications["data"] and lol_notifications["data"]["blockNonFriendGameInvites"]
    if nonfriend_invitation_blocked:
        logPrint('''您已勾选“只接受好友邀请”选项。是否取消该选项以接受所有人邀请？（输入任意键以修改设置，否则保持原设置。）\nYou've checked the "Allow game invites only from friends" option. Do you want to uncheck this, so that you'll receive any other's invitation? (Submit any non-empty string to change the setting, or null to reserve it.)''')
    else:
        logPrint('''您未勾选“只接受好友邀请”选项。是否勾选该选项以只接受好友邀请？（输入任意键以修改设置，否则保持原设置。）\nYou've unchecked the "Allow game invites only from friends" option. Do you want to check this, so that you'll receive only your friends' invitation? (Submit any non-empty string to change the setting, or null to reserve it.)''')
    settings_change_str: str = logInput()
    settings_change: bool = bool(settings_change_str)
    if settings_change:
        body: dict[str, dict[str, bool] | int] = {"data": {"blockNonFriendGameInvites": not nonfriend_invitation_blocked}, "schemaVersion": lol_notifications["schemaVersion"]} #注意：schemaVersion一旦增加就不可减少（Warning: Once schemaVersion increases, it can't be decreased）
        response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-settings/v2/account/LCUPreferences/lol-notifications", data = body)).json()
        logPrint(response)
        if nonfriend_invitation_blocked:
            logPrint('已禁用“只接受好友游戏邀请”选项。您现在应当能够收到来自陌生人的游戏邀请了。\nDisabled "Allow game invites only from friends" option. You should be able to receive an invitation from a stranger.')
        else:
            logPrint('''已启用“只接受好友游戏邀请”选项。您将屏蔽所有来自陌生人的游戏邀请。\nEnabled "Allow game invites only from friends" option. You'll block any invitation from strangers.''')

async def expand_match_history(connection: Connection) -> None:
    global expand_matchHistory_hint_printed
    if not expand_matchHistory_hint_printed:
        logPrint("请确保您从未点击过要查询的玩家的对局记录。如果您已经点击过，则程序只能获取到目前客户端接收到的对局，请等待该信息过期后再重新使用此功能。\nPlease make sure you haven't clicked the MATCH HISTORY tab of the summoner you want to search for. If you happen to have clicked it, then the program can only get the matches already received, and you need to wait for that information to expire and then use this function.\n")
        expand_matchHistory_hint_printed = True
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    logPrint('请输入要查询的召唤师名称，退出请输入“0”：\nPlease input the summoner name to be searched. Submit "0" to exit.')
    while True:
        summoner_name: str = logInput()
        if summoner_name == "":
            continue
        elif summoner_name == "0":
            break
        else:
            info: dict[str, Any] = await get_info(connection, summoner_name)
        if info["info_got"]:
            info_body: dict[str, Any] = info["body"]
            displayName: str = get_info_name(info_body)
            current_puuid: str = info_body["puuid"]
            logPrint("开始获取英雄联盟对局记录。\nBegin to get the LoL match history.")
            LoLHistory_get: bool = False
            while True:
                LoLHistory: dict[str, Any] = await (await connection.request("GET", f"/lol-match-history/v1/products/lol/{current_puuid}/matches?begIndex=0&endIndex=500")).json()
                count: int = 0
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
                        LoLHistory_url: str = "%s/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=200" %(connection.address, info_body["puuid"])
                        logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续（Please open the following website, type in the username and password accordingly and press Enter to continue）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和上限。\nOr submit two nonnegative integers split by space to respecify the begIndex and endIndex." %(LoLHistory_url, connection.auth_key))
                        cont: str = logInput()
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
                gameCount: int = LoLHistory["games"]["gameCount"]
                if gameCount <= 20:
                    logPrint(f"程序只获取到{displayName}的{gameCount}场英雄联盟对局。这可能是因为您之前点击过该玩家的对局记录页签，或者该玩家近期只进行过少于20场英雄联盟对局。\nThe program only gets {displayName}'s {gameCount} LoL match(es). Maybe this is because you clicked this summoner's MATCH HISTORY tab before, or this player has played fewer than 20 LoL matches.")
                else:
                    logPrint(f"已经将{displayName}的英雄联盟对局记录扩展到{gameCount}场对局。请点击该玩家的对局记录页签查看。\nExpanded {displayName}'s LoL match history to {gameCount} matches. Please click this summoner's MATCH HISTORY tab to check it out.")
            else:
                logPrint(f"{displayName}的英雄联盟对局记录获取失败。\nThe program failed to get {displayName}'s LoL match history.")
            logPrint("开始获取云顶之弈对局记录。\nBegin to get the TFT match history.")
            TFTHistory_get: bool = False
            while True:
                TFTHistory: dict[str, Any] = await (await connection.request("GET", f"/lol-match-history/v1/products/tft/{current_puuid}/matches?begin=0&count=500")).json()
                count: int = 0
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
                        TFTHistory_url: str = "%s/lol-match-history/v1/products/lol/%s/matches?begin=0&count=200" %(connection.address, info_body["puuid"])
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
                gameCount: int = len(TFTHistory["games"])
                if gameCount <= 20:
                    logPrint(f"程序只获取到{displayName}的{gameCount}场云顶之弈对局。这可能是因为您之前点击过该玩家的对局记录页签，或者该玩家近期只进行过少于20场云顶之弈对局。\nThe program only gets {displayName}'s {gameCount} TFT match(es). Maybe this is because you clicked this summoner's MATCH HISTORY tab before, or this player has played fewer than 20 TFT matches.")
                else:
                    logPrint(f"已经将{displayName}的云顶之弈对局记录扩展到{gameCount}场对局。请点击该玩家的对局记录页签查看。\nExpanded {displayName}'s TFT match history to {gameCount} matches. Please click this summoner's MATCH HISTORY tab to check it out.")
            else:
                logPrint(f"{displayName}的云顶之弈对局记录获取失败。\nThe program failed to get {displayName}'s TFT match history.")
        else:
            logPrint(info["message"])
        logPrint('请输入要查询的召唤师名称，退出请输入“0”：\nPlease input the summoner name to be searched. Submit "0" to exit.')

async def display_current_info(connection: Connection) -> None:
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    logPrint(json.dumps(current_info, indent = 4, ensure_ascii = False), write_time = False)

def select_report_categories(gameflow_phase: str, summoner_name: str = "") -> list[str]:
    if gameflow_phase == "ChampSelect":
        logPrint(f"举报{summoner_name}，理由是：\nReport {summoner_name} for: \n1\t玩家水平过低（Unskilled Play）\n2\t滥用聊天工具（Comms Abuse）\n3\t抢位置（Refusing to play position）\n4\t态度恶劣/威胁（Griefing / Hostage taking）\n5\t滥用小队语音聊天工具（Team Voice Comms Abuse）\n6\t不当的用户名（Inappropriate Name）\n7\t其它（Other）")
        report_category_list: list[str] = REPORT_CATEGORY_LIST_CHAMPSELECT
        nCategory: int = 7
    else:
        logPrint("请尽可能详尽地告诉我们这位玩家都做了些什么。如果需要的话，可以在下方选择最多三项分类。\nAs accurately as you can, please tell us what happened with this player. Choose up to three reporting categories if you need to.\n*****************************************************************************\n为赢而玩。\nPLAY TO WIN.\n1\t中途退出/挂机（LEAVING THE GAME / AFK）\n\t断开连接，不积极参与游戏\n\tDisconnected, not actively participating\n2\t团队破坏（TEAM SABOTAGE）\n\t故意送人头、扰乱队友、不与队友协作\n\tIntentional feeding, disrupting teammates, assisting enemy team\n*****************************************************************************\n公平地玩。\nPLAY FAIR.\n3\t作弊（CHEATING）\n\t使用脚本、使用未经许可的第三方程序\n\tScripting, using unapproved third-party programs\n4\t排位操控（RANK MANIPULATION）\n\t演员行为、故意送分、炸鱼、代练\n\tSmurfing, boosting, win-trading, deranking\n5\t自动脚本刷级（BOTTING）\n\t对局行为反常，机械性地参与游戏或不公平地获取进度\n\tUtilizing AFK or leveling bots to inactively participate or unfairly earn progress\n*****************************************************************************\n尊重地玩。\nPLAY WITH RESPECT.\n6\t滥用聊天工具（COMMS ABUSE）\n\t霸凌、骚扰、威胁、仇恨言论、聊天/信号刷屏\n\tBullying, harassment, threats, hate speech, chat/ping spam\n7\t有攻击性的名称（OFFENSIVE NAME）\n\t不当或有攻击性的用户名称、名称编号、战队名称\n\tInappropriate or offensive account name, tagline, team name")
        logPrint("示例（Example）：\n[1, 2, 3]\t#中途退出/挂机（LEAVING THE GAME / AFK）、消极态度（TEAM SABOTAGE）、作弊（CHEATING）")
        report_category_list: list[str] = REPORT_CATEGORY_LIST_POSTGAME
        nCategory = 7
    while True:
        category_indices: list[int] = []
        category_index_str: str = logInput()
        if category_index_str == "":
            continue
        elif category_index_str[0] == "0":
            category_indices = []
            break
        else:
            try:
                tmp = eval(category_index_str)
            except:
                traceback_info = traceback.format_exc()
                logPrint(traceback_info)
                logPrint("语法错误！请重新输入。\nSyntax ERROR! Please try again.")
            else:
                if isinstance(tmp, int):
                    if tmp >= 1 and tmp <= nCategory:
                        category_indices = [tmp]
                        break
                    else:
                        logPrint(f"请输入1和{nCategory}之间的一个正整数。\nPlease input a positive integer between 1 and {nCategory}.")
                elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int), tmp)):
                    if all(map(lambda x: x >= 1 and x <= nCategory, tmp)):
                        category_indices = sorted(set(tmp))
                        break
                    else:
                        logPrint(f"请输入1和{nCategory}之间的正整数。\nPlease input positive integers between 1 and {nCategory}.")
                else:
                    logPrint("请输入一个由正整数组成的列表。\nPlease input a list of positive integers.")
    report_categoryList: list[str] = [report_category_list[i - 1] for i in category_indices]
    if len(report_categoryList) > 0:
        logPrint("您已选择以下情况：\nYou selected the following situations:")
        for report_category in report_categoryList:
            logPrint("- %s（%s）" %(report_categories[report_category]["zh_CN"], report_categories[report_category]["en_US"]))
    return report_categoryList

async def send_report_request(connection: Connection, resource: dict[str, Any], endpoint_type: int = 1) -> Optional[dict[str, Any]]:
    '''
    发送举报请求。<br>Send report request.
    
    :param resource: 请求主体。<br>Request body.
    :type resource: dict[str, Any]
    :param endpoint_type: 接口类型代号。有以下四种情形：<br>Endpoint Uri type id. There're 4 cases:
    
        - ☆1: 从对局记录中举报。<br>Report from match history.
        - 2: 在英雄选择阶段举报。<br>Report a player in the current champ select session.
        - 3: 在游戏内举报。<br>Report a player in a running game.
        - 4: 在赛后结算界面举报。<br>Report a player in the end of game.
    :type endpoint_type: int
    '''
    if endpoint_type == 1:
        report_endpoint: str = "/lol-player-report-sender/v1/match-history-reports"
    elif endpoint_type == 2:
        report_endpoint = "/lol-player-report-sender/v1/champ-select-reports"
    elif endpoint_type == 3:
        report_endpoint = "/lol-player-report-sender/v1/in-game-reports"
    elif endpoint_type == 4:
        report_endpoint = "/lol-player-report-sender/v1/end-of-game-reports"
    else:
        print("无效接口类型！\nInvalid endpoint type!")
        return
    response: Optional[dict[str, Any]] = await (await connection.request("POST", report_endpoint, data = resource)).json()
    if response == None:
        logPrint("审核用的举报已经发送。感谢您的反馈。\nA report has been sent for review. Thank you.")
    else:
        logPrint(response)
        if response == {"errorCode": "RPC_ERROR", "httpStatus": 404, "implementationDetails": {}, "message": "Retrieved match token from honor is empty."}:
            logPrint("玩家对局令牌获取异常。请确保您正在举报您所在的一场匹配对局中的一名人类玩家。\nPlayer match token capture failed. Please make sure you're reporting a human player in a matched game of yours.")
        elif response["httpStatus"] == 400 and "Failed to submit match-history report for player" in response["message"]:
            logPrint("在发送举报请求时出现了一个异常。\nAn error occurred when the program was trying to send a report request.")
        else:
            logPrint("发送失败。\nFailed to send the report.")
    return response

async def report_player_champSelect(connection: Connection) -> None:
    gameflow_phase: str = await get_gameflow_phase(connection)
    if gameflow_phase == "ChampSelect":
        champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        if "errorCode" in champ_select_session:
            logPrint("程序检测到您正在英雄选择阶段，但是未能如期获取到英雄选择会话。请重试。\nThe program detected that you're during the champ select stage, but failed to get the champ select session. Please try again.")
        elif champ_select_session["isSpectating"]:
            logPrint("举报功能不适用于观战的英雄选择阶段。\nReport isn't supported when you're during the champ select stage of spectating a game.")
        else:
            humanPlayers: list[dict[str, Any]] = [player for player in champ_select_session["myTeam"] + champ_select_session["theirTeam"] if not player["isHumanoid"]]
            if len(humanPlayers) == 1: #只有自己的情况下（Only the user itself）
                logPrint("本场英雄选择阶段无其他人类玩家。\nNo more human players are found during this champ select stage.")
            else:
                player_df: pandas.DataFrame = await sort_ChampSelect_players(connection, LoLChampions, championSkins, spells, wardSkins, playerMode = 1, log = log)
                player_df_fields_to_print: list[str] = ["cellId", "gameName", "tagLine", "playerAlias", "assignedPosition", "champion name", "champion alias"]
                logPrint("已获取到玩家信息。\nParticipant information has been fetched successfully.")
                while True:
                    logPrint("按回车键以开启一个新的举报流程，或者输入任意非空字符串以返回上一层。\nPress Enter to start a new report process, or submit any non-empty string to return to the last step.")
                    quit_str: str = logInput()
                    quit: bool = bool(quit_str)
                    if quit:
                        break
                    player_index: int = -1
                    #下面初始化举报接口的请求主体相关变量（Initialize variables related to the request body of the report endpoint）
                    player_puuid: str = ""
                    player_obfuscatedPuuid: str = ""
                    report_categories: list[str] = []
                    gameId: int = champ_select_session["gameId"]
                    comment: str = ""
                    step: int = 1
                    body_ready: bool = False #表示请求主体是否准备就绪（Marks whether the request body is ready）
                    while True:
                        if step == 0:
                            break
                        elif step == 1:
                            logPrint("第一步：请选择一名玩家：\nStep 1: Please select a player:")
                            logPrint(format_df(player_df.loc[:, player_df_fields_to_print], print_index = True)[0], write_time = False)
                            while True:
                                player_index_str: str = logInput()
                                if player_index_str == "":
                                    continue
                                elif player_index_str[0] == "0":
                                    step -= 2
                                    break
                                elif player_index_str in list(map(str, range(1, len(player_df)))):
                                    player_index = int(player_index_str)
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        elif step == 2:
                            player_championName: str = player_df["champion name"][player_index]
                            player_championAlias: str = player_df["champion alias"][player_index]
                            player_puuid: str = player_df["puuid"][player_index]
                            player_obfuscatedPuuid: str = player_df["obfuscatedPuuid"][player_index]
                            player_cellId: int = player_df["cellId"][player_index]
                            player_summonerName: str = ""
                            if player_df["nameVisibilityType"][player_index] == "HIDDEN":
                                player_info_got: bool = False
                            else:
                                player_info_recapture: int = 0
                                player_info: dict[str, Any] = await get_info(connection, player_puuid)
                                while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                                    logPrint(player_info["message"])
                                    player_info_recapture += 1
                                    logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s, cellId: %d) capture failed! Recapturing this player's information ... Times tried: %d" %(player_cellId, player_puuid, player_info_recapture, player_puuid, player_cellId, player_info_recapture))
                                    player_info = await get_info(connection, player_puuid)
                                if not player_info["info_got"]:
                                    logPrint(player_info["message"])
                                    logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s, cellId: %d) capture failed!" %(player_cellId, player_puuid, player_puuid, player_cellId))
                                player_info_got = player_info["info_got"]
                            if player_info_got:
                                player_summonerName = get_info_name(player_info["body"])
                                logPrint("第二步：举报玩家：%s（槽位序号：%d）\nStep 2: REPORT PLAYER: %s (CellId: %d)" %(player_summonerName, player_cellId, player_summonerName, player_cellId))
                            else:
                                logPrint("第二步：举报玩家：%s %s（槽位序号：%d）\nStep 2: REPORT PLAYER: %s %s (CellId: %d)" %(player_championName, player_championAlias, player_cellId, player_championName, player_championAlias, player_cellId))
                            report_categories: list[str] = select_report_categories(gameflow_phase, summoner_name = player_summonerName)
                            if len(report_categories) == 0:
                                step -= 2
                        elif step == 3:
                            logPrint("第三步：请输入一段描述。按回车键以直接提交。输入Ctrl-D字符以返回上一步。\nStep 3: Please input some description. Press Enter to submit. Enter Ctrl-D to return to the last step.")
                            comment: str = logInput()
                            if comment.endswith(chr(4)):
                                step -= 2
                        elif step == 4:
                            body_ready = True
                            break
                        else:
                            logPrint("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
                            break
                        step += 1
                    if body_ready:
                        body: dict[str, Any] = {"offenderPuuid": player_puuid, "obfuscatedOffenderPuuid": player_obfuscatedPuuid, "categories": report_categories, "gameId": gameId, "comment": comment}
                        response: Optional[dict[str, Any]] = await send_report_request(connection, body, endpoint_type = 2)
    else:
        logPrint("您目前不在英雄选择阶段。\nYou're not duing the champ select stage.")

async def report_player_inGame(connection: Connection) -> None:
    gameflow_phase: str = await get_gameflow_phase(connection)
    if gameflow_phase in {"FailedToLaunch", "InProgress", "Reconnect"}:
        gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        if "errorCode" in gameflow_session:
            logPrint("程序检测到您正在游戏中，但是未能如期获取到游戏会话。请重试。\nThe program detected that you're in a game, but failed to get the gameflow session. Please try again.")
        else:
            humanPlayers: list[dict[str, Any]] = [player for player in gameflow_session["playerChampionSelections"] if "puuid" in player]
            if len(humanPlayers) == 0: #房间内和英雄选择阶段（In lobby and during champ select stage）
                logPrint("您目前不在游戏内。\nYou're currently not in a game.")
            elif len(humanPlayers) == 1: #只有自己的情况下（Only the user itself）
                logPrint("本场对局无其他人类玩家。\nNo more human players are found in this game.")
            else:
                player_df: pandas.DataFrame = await sort_inGame_players(connection, LoLChampions, championSkins, summonerIcons, spells, skipBot = True, log = log)
                player_df_fields_to_print: list[str] = ["team_color", "teamParticipantId", "gameName", "tagLine", "selectedPosition", "champion name", "champion alias"]
                logPrint("已获取到玩家信息。\nParticipant information has been fetched successfully.")
                while True:
                    logPrint("按回车键以开启一个新的举报流程，或者输入任意非空字符串以返回上一层。\nPress Enter to start a new report process, or submit any non-empty string to return to the last step.")
                    quit_str: str = logInput()
                    quit: bool = bool(quit_str)
                    if quit:
                        break
                    player_index: int = 0
                    #下面初始化举报接口的请求主体相关变量（Initialize variables related to the request body of the report endpoint）
                    player_puuid: str = ""
                    player_obfuscatedPuuid: str = "" #游戏会话中没有加密的玩家通用唯一识别码（Obfuscated puuid isn't displayed in the gameflow session）
                    report_categories: list[str] = []
                    gameId: int = gameflow_session["gameData"]["gameId"]
                    comment: str = ""
                    step: int = 1
                    body_ready: bool = False #表示请求主体是否准备就绪（Marks whether the request body is ready）
                    while True:
                        if step == 0:
                            break
                        elif step == 1:
                            logPrint("第一步：请选择一名玩家：\nStep 1: Please select a player:")
                            logPrint(format_df(player_df.loc[:, player_df_fields_to_print], print_index = True)[0], write_time = False)
                            while True:
                                player_index_str: str = logInput()
                                if player_index_str == "":
                                    continue
                                elif player_index_str[0] == "0":
                                    step -= 2
                                    break
                                elif player_index_str in list(map(str, range(1, len(player_df)))):
                                    player_index = int(player_index_str)
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        elif step == 2:
                            player_championName: str = player_df["champion name"][player_index]
                            player_championAlias: str = player_df["champion alias"][player_index]
                            player_puuid: str = player_df["puuid"][player_index]
                            player_teamId: int = player_df["teamId"][player_index]
                            player_summonerName: str = ""
                            if bool(player_puuid):
                                player_info_got: bool = False
                            else:
                                player_info_recapture: int = 0
                                player_info: dict[str, Any] = await get_info(connection, player_puuid)
                                while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                                    logPrint(player_info["message"])
                                    player_info_recapture += 1
                                    logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(player_puuid, player_info_recapture, player_puuid, player_info_recapture))
                                    player_info = await get_info(connection, player_puuid)
                                if not player_info["info_got"]:
                                    logPrint(player_info["message"])
                                    logPrint("的玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) capture failed!" %(player_puuid, player_puuid))
                                player_info_got = player_info["info_got"]
                            if player_info_got:
                                player_summonerName = get_info_name(player_info["body"])
                                logPrint("第二步：举报玩家：%s\nStep 2: REPORT PLAYER: %s" %(player_summonerName, player_summonerName))
                            else:
                                logPrint("第二步：举报玩家：%s %s（阵营代号：%d）\nStep 2: REPORT PLAYER: %s %s (TeamId: %d)" %(player_championName, player_championAlias, player_teamId, player_championName, player_championAlias, player_teamId))
                            report_categories: list[str] = select_report_categories(gameflow_phase)
                            if len(report_categories) == 0:
                                step -= 2
                        elif step == 3:
                            logPrint("对刚才发生的事情进行补充描述。可以包括在英雄选择阶段或赛后结算阶段期间发生的事情。\nGive additional context on what happened in this game. Include events in champion select or post-game if applicable.")
                            logPrint("第三步：请输入一段描述。按回车键以直接提交。输入Ctrl-D字符以返回上一步。\nStep 3: Please input some description. Press Enter to submit. Enter Ctrl-D to return to the last step.")
                            comment: str = logInput()
                            if comment.endswith(chr(4)):
                                step -= 2
                        elif step == 4:
                            body_ready = True
                            break
                        else:
                            logPrint("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
                            break
                        step += 1
                    if body_ready:
                        body: dict[str, Any] = {"offenderPuuid": player_puuid, "obfuscatedOffenderPuuid": player_obfuscatedPuuid, "categories": report_categories, "gameId": gameId, "comment": comment}
                        response: Optional[dict[str, Any]] = await send_report_request(connection, body, endpoint_type = 3)
    else:
        logPrint("您目前不在游戏内。\nYou're currently not in a game.")

async def report_player_endOfGame(connection: Connection) -> None:
    gameflow_phase: str = await get_gameflow_phase(connection)
    if gameflow_phase == "PreEndOfGame" or gameflow_phase == "EndOfGame":
        gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        if "errorCode" in gameflow_session:
            logPrint("程序检测到您已完成对局，但是未能如期获取到游戏会话。请重试。\nThe program detected that you've just finished a game, but failed to get the gameflow session. Please try again.")
        else:
            eog_stats_block: dict[str, Any] = {}
            tft_eog_stats: dict[str, Any] = {}
            eog_stats_got: bool = False
            isTFT: bool = gameflow_session["map"]["mapStringId"] == "TFT"
            if isTFT:
                tft_eog_stats: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
                if isinstance(tft_eog_stats, dict) and "errorCode" in tft_eog_stats:
                    logPrint(tft_eog_stats)
                    if tft_eog_stats["httpStatus"] == 404 and tft_eog_stats["message"] == "Game Client stats not found":
                        logPrint("当前游戏模式无法查看云顶之弈对局数据。\nThe current game mode doesn't provide TFT game stats.")
                    else:
                        logPrint("程序检测到您已完成一场云顶之弈对局，但是未能如期获取到赛后结算数据。请重试。\nThe program detected that you've just finished a TFT game, but failed to get the end-of-game stats. Please try again.")
                else:
                    eog_stats_got = True
            else:
                eog_stats_block: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
                if isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block:
                    logPrint(eog_stats_block)
                    if eog_stats_block["httpStatus"] == 404 and eog_stats_block["message"] == "No end of game stats available.":
                        logPrint("当前游戏模式无法查看英雄联盟对局数据。\nThe current game mode doesn't provide LoL game stats.")
                    else:
                        logPrint("程序检测到您已完成一场英雄联盟对局，但是未能如期获取到赛后结算数据。请重试。\nThe program detected that you've just finished a LoL game, but failed to get the end-of-game stats. Please try again.")
                else:
                    eog_stats_got = True
            if eog_stats_got:
                if isTFT:
                    humanPlayers: list[dict[str, Any]] = tft_eog_stats["players"] #虽然在国服会出现电脑玩家，但是这些电脑玩家被赋予了独立的玩家名称和名称编号，因此这里把他们当成人类玩家来对待（Although bot players may appear in Tencent region's TFT games, these bot players are always assigned independent gameNames and tagLines, so they're regarded as normal human players here）
                else:
                    humanPlayers = [player for player in team for team in eog_stats_block["teams"] if not player["botPlayer"]]
                if len(humanPlayers) == 1: #只有自己的情况下（Only the user itself）
                    logPrint("本场对局无其他人类玩家。\nNo more human players are found in this game.")
                else:
                    if isTFT:
                        player_df: pandas.DataFrame = await sort_eog_playerstat_lol_data(connection, summonerIcons, spells, perks, perkstyles, CherryAugments, skipBot = True)
                        player_df_fields_to_print: list[str] = ["team_color", "riotIdGameName", "riotIdTagLine", "selectedPosition", "championName"]
                    else:
                        player_df = await sort_eog_stat_tft_data(connection, summonerIcons)
                        player_df_fields_to_print = ["partnerGroupId", "riotIdGameName", "riotIdTagLine", "ffaStanding", "rank"]
                    logPrint("已获取到玩家信息。\nParticipant information has been fetched successfully.")
                    while True:
                        logPrint("按回车键以开启一个新的举报流程，或者输入任意非空字符串以返回上一层。\nPress Enter to start a new report process, or submit any non-empty string to return to the last step.")
                        quit_str: str = logInput()
                        quit: bool = bool(quit_str)
                        if quit:
                            break
                        player_index: int = 0
                        #下面初始化举报接口的请求主体相关变量（Initialize variables related to the request body of the report endpoint）
                        player_puuid: str = ""
                        player_obfuscatedPuuid: str = "" #赛后结算数据中没有加密的玩家通用唯一识别码。而且实际上，赛后结算数据不会隐藏玩家的玩家的玩家通用唯一识别码（Obfuscated puuid isn't displayed in the end-of-game data. And actually, end-of-game data shouldn't hide a player's puuid）
                        report_categories: list[str] = []
                        gameId: int = tft_eog_stats["gameId"] if isTFT else eog_stats_block["gameId"]
                        comment: str = ""
                        step: int = 1
                        body_ready: bool = False #表示请求主体是否准备就绪（Marks whether the request body is ready）
                        while True:
                            if step == 0:
                                break
                            elif step == 1:
                                logPrint("第一步：请选择一名玩家：\nStep 1: Please select a player:")
                                logPrint(format_df(player_df.loc[:, player_df_fields_to_print], print_index = True)[0], write_time = False)
                                while True:
                                    player_index_str: str = logInput()
                                    if player_index_str == "":
                                        continue
                                    elif player_index_str[0] == "0":
                                        step -= 2
                                        break
                                    elif player_index_str in list(map(str, range(1, len(player_df)))):
                                        player_index = int(player_index_str)
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            elif step == 2:
                                player_puuid = player_df["puuid"][player_index]
                                player_summonerName: str = player_df["riotIdGameName"][player_index] + "#" + player_df["riotIdTagLine"][player_index]
                                if player_summonerName == "#":
                                    if isTFT:
                                        player_companionName: str = player_df["companion speciesName"][player_index]
                                        player_rank: int = player_df["rank"][player_index]
                                        logPrint("第二步：举报玩家：%s（最终名次：%d）\nStep 2: REPORT PLAYER: %s (Rank: %d)" %(player_companionName, player_rank, player_companionName, player_rank))
                                    else:
                                        player_championName: str = player_df["championName"][player_index]
                                        player_teamId: int = player_df["teamId"][player_index]
                                        logPrint("第二步：举报玩家：%s（阵营代号：%d）\nStep 2: REPORT PLAYER: %s (TeamId: %d)" %(player_championName, player_teamId, player_championName, player_teamId))
                                else:
                                    logPrint("第二步：举报玩家：%s\nStep 2: REPORT PLAYER: %s" %(player_summonerName, player_summonerName))
                                report_categories: list[str] = select_report_categories(gameflow_phase)
                                if len(report_categories) == 0:
                                    step -= 2
                            elif step == 3:
                                logPrint("对刚才发生的事情进行补充描述。可以包括在英雄选择阶段或赛后结算阶段期间发生的事情。\nGive additional context on what happened in this game. Include events in champion select or post-game if applicable.")
                                logPrint("第三步：请输入一段描述。按回车键以直接提交。输入Ctrl-D字符以返回上一步。\nStep 3: Please input some description. Press Enter to submit. Enter Ctrl-D to return to the last step.")
                                comment: str = logInput()
                                if comment.endswith(chr(4)):
                                    step -= 2
                            elif step == 4:
                                body_ready = True
                                break
                            else:
                                logPrint("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
                                break
                            step += 1
                        if body_ready:
                            body: dict[str, Any] = {"offenderPuuid": player_puuid, "obfuscatedOffenderPuuid": player_obfuscatedPuuid, "categories": report_categories, "gameId": gameId, "comment": comment}
                            response: Optional[dict[str, Any]] = await send_report_request(connection, body, endpoint_type = 3)
    else:
        logPrint("您目前不在游戏内。\nYou're currently not in a game.")

async def report_player_matchHistory(connection: Connection) -> None:
    gameId: int = 0
    game_info: dict[str, Any] = {}
    LoLGame_info: dict[str, Any] = {}
    TFTGame_info: dict[str, Any] = {}
    logPrint('请输入对局序号。输入“0”以返回上一层。\nPlease input gameId. Submit "0" to return to the last step.')
    while True:
        isTFT: bool = False
        gameId_str: str = logInput()
        fetched_info: bool = False
        if gameId_str == "":
            continue
        elif gameId_str == "0":
            break
        else:
            try:
                gameId = int(gameId_str)
            except ValueError:
                logPrint("请输入整数类型的对局序号！\nPlease enter the gameId of integer type!")
            else:
                if gameId > 0:
                    match_id: str = f"{platformId}_{gameId}"
                    status, game_info = await get_game_info_sgp(connection, sgpSession, match_id, log = log)
                    if status == 200:
                        fetched_info = True
                        isTFT = game_info["metadata"]["product"] == "TFT"
                    else:
                        logPrint("请求失败！请切换一个对局序号或稍后重试。\nRequest failed! Please change a gameId or try it again later.")
                else:
                    logPrint("请输入一个正整数！\nPlease enter a positive integer.")
        if fetched_info:
            if isTFT and game_info.get("json"):
                TFTGame_info = game_info
                humanPlayers: list[dict[str, Any]] = TFTGame_info["json"]["participants"] #同上，云顶之弈中无法判断一名玩家是否电脑玩家（Same as above, we can't tell whether a player is a bot here）
                player_df: pandas.DataFrame = (await sort_TFTGame_info(connection, TFTGame_info, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = 1, current_puuid = current_info["puuid"], useAllVersions = False, sortStats = False, log = log))[0]
                player_df_fields_to_print = ["partner_group_id", "riotIdGameName", "riotIdTagline", "placement"]
            elif not isTFT: #为了简化程序，这里直接用SGP API来查询对局信息，没有设置LCU API的选项。这是因为在本脚本中，仅此处会用到对局记录查询接口，而因为这一个场景设置一个命令行参数有些小题大做了（To simplify the program, here only SGP API is used to search for a match. LCU API isn't enabled as another option. This is because in this program, only this place uses the match history endpoint, so it's not necessary to set command line arguments）
                LoLGame_info = game_info
                humanPlayers = [player for player in LoLGame_info["json"]["participants"] if player != BOT_UUID]
                player_df = sort_LoLGame_info_sgp(LoLGame_info, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = 1, current_puuid = current_info["puuid"], sortStats = False, log = log)[0]
                # player_df.insert(player_df.shape[1], "K/D/A", ["击杀得分"] + list(map(lambda i: "%d/%d/%d" %(player_df["kills"][i], player_df["deaths"][i], player_df["assists"][i]), range(1, len(player_df)))))
                player_df = pandas.concat([player_df, pandas.DataFrame({"K/D/A": ["击杀得分"] + list(map(lambda i: "%d/%d/%d" %(player_df["kills"][i], player_df["deaths"][i], player_df["assists"][i]), range(1, len(player_df))))})], axis = 1)
                player_df_fields_to_print: list[str] = [("playerSubteamColor" if LoLGame_info["json"]["gameMode"] == "CHERRY" else "team_color"), "riotIdGameName", "riotIdTagline", "champion_name", "K/D/A", "CS"]
            else:
                logPrint("未获取到有效的玩家信息。请切换其它对局。\nNo valid participant information detected. Please change another game.")
                continue
            if len(humanPlayers) == 1: #只有自己的情况下（Only the user itself）
                logPrint("本场对局无其他人类玩家。\nNo more human players are found in this game.")
            else:
                logPrint("已获取到玩家信息。\nParticipant information has been fetched successfully.")
                while True:
                    logPrint("按回车键以开启一个新的举报流程，或者输入任意非空字符串以返回上一层。\nPress Enter to start a new report process, or submit any non-empty string to return to the last step.")
                    quit_str: str = logInput()
                    quit: bool = bool(quit_str)
                    if quit:
                        break
                    player_index: int = 0
                    #下面初始化举报接口的请求主体相关变量（Initialize variables related to the request body of the report endpoint）
                    player_puuid: str = ""
                    player_obfuscatedPuuid: str = "" #赛后结算数据中没有加密的玩家通用唯一识别码。而且实际上，赛后结算数据不会隐藏玩家的玩家的玩家通用唯一识别码（Obfuscated puuid isn't displayed in the end-of-game data. And actually, end-of-game data shouldn't hide a player's puuid）
                    report_categories: list[str] = []
                    gameId: int = TFTGame_info["json"]["gameId"] if isTFT else LoLGame_info["json"]["gameId"]
                    comment: str = ""
                    step: int = 1
                    body_ready: bool = False #表示请求主体是否准备就绪（Marks whether the request body is ready）
                    while True:
                        if step == 0:
                            break
                        elif step == 1:
                            logPrint("第一步：请选择一名玩家：\nStep 1: Please select a player:")
                            logPrint(format_df(player_df.loc[:, player_df_fields_to_print], print_index = True)[0], write_time = False)
                            while True:
                                player_index_str: str = logInput()
                                if player_index_str == "":
                                    continue
                                elif player_index_str[0] == "0":
                                    step -= 2
                                    break
                                elif player_index_str in list(map(str, range(1, len(player_df)))):
                                    player_index = int(player_index_str)
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        elif step == 2:
                            player_puuid = player_df["puuid"][player_index]
                            player_summonerName: str = player_df["riotIdGameName"][player_index] + "#" + player_df["riotIdTagline"][player_index]
                            if player_summonerName == "#":
                                if isTFT:
                                    player_companionName: str = player_df["companion speciesName"][player_index]
                                    player_rank: int = player_df["rank"][player_index]
                                    logPrint("第二步：举报玩家：%s（最终名次：%d）\nStep 2: REPORT PLAYER: %s (Rank: %d)" %(player_companionName, player_rank, player_companionName, player_rank))
                                else:
                                    player_championName: str = player_df["championName"][player_index]
                                    player_team: str = player_df["team_color"][player_index]
                                    logPrint("第二步：举报玩家：%s（阵营：%s）\nStep 2: REPORT PLAYER: %s (Team: %s)" %(player_championName, player_team, player_championName, player_team))
                            else:
                                logPrint("第二步：举报玩家：%s\nStep 2: REPORT PLAYER: %s" %(player_summonerName, player_summonerName))
                            report_categories: list[str] = select_report_categories("None")
                            if len(report_categories) == 0:
                                step -= 2
                        elif step == 3:
                            logPrint("对刚才发生的事情进行补充描述。可以包括在英雄选择阶段或赛后结算阶段期间发生的事情。\nGive additional context on what happened in this game. Include events in champion select or post-game if applicable.")
                            logPrint("第三步：请输入一段描述。按回车键以直接提交。输入Ctrl-D字符以返回上一步。\nStep 3: Please input some description. Press Enter to submit. Enter Ctrl-D to return to the last step.")
                            comment: str = logInput()
                            if comment.endswith(chr(4)):
                                step -= 2
                        elif step == 4:
                            body_ready = True
                            break
                        else:
                            logPrint("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
                            break
                        step += 1
                    if body_ready:
                        body: dict[str, Any] = {"offenderPuuid": player_puuid, "obfuscatedOffenderPuuid": player_obfuscatedPuuid, "categories": report_categories, "gameId": gameId, "comment": comment}
                        response: Optional[dict[str, Any]] = await send_report_request(connection, body, endpoint_type = 1)
            logPrint('请输入对局序号。输入“0”以返回上一层。\nPlease input gameId. Submit "0" to return to the last step.')
    else:
        logPrint("您目前不在游戏内。\nYou're currently not in a game.")

#-----------------------------------------------------------------------------
# 未登录状态（Unlogged state）
#-----------------------------------------------------------------------------
async def unlogged_actions(connection: Connection) -> None:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n-1\t调试自定义接口（Debug custom endpoints）\n1\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option == "-1":
            await send_commands(connection, log = log)
        elif option[0] == "1":
            await manage_ux(connection)

#-----------------------------------------------------------------------------
# 创建房间（Create a lobby）
#-----------------------------------------------------------------------------
async def create_queue_lobby(connection: Connection, loop_test: bool = False) -> int: #返回值为0代表请求正确发送，为1代表返回异常请求，为2代表中途退出。自定义房间创建函数同理（The returned value is 0 if the request is sent properly, 1 if an error message is returned and 2 if the user exits the function halfway. So as `create_custom_lobby` function）
    '''
    创建小队。现在适用于所有游戏模式。<br>Create a party. Now applies to any game mode.
    
    :param loop_test: 是否启用循环测试。在启用时，用户可以连续输入队列序号以连续创建不同房间。默认为假。<br>Whether to enable loop test. When it's enabled, the user may input queueIds continuously to create different lobbies. False by default.
    :type loop_test: bool
    '''
    game_version: str = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_source}
    enabled_queueIds: list[int] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/ClientSystemStates/enabledQueueIdsList")).json()
    ARAMmaps_zh: dict[str, str] = {key: ARAMmaps[key]["zh_CN"] for key in ARAMmaps}
    ARAMmaps_en: dict[str, str] = {key: ARAMmaps[key]["en_US"] for key in ARAMmaps}
    region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    custom_game_setup_name_default_dict: dict[str, str] = {"ar_AE": "مباراة {{summonerName}}", "cs_CZ": "Hra uživatele {{summonerName}}", "el_GR": "Παιχνίδι του {{summonerName}}", "pl_PL": "Rozgrywka gracza {{summonerName}}", "ro_RO": "Jocul lui {{summonerName}}", "hu_HU": "{{summonerName}} játéka", "en_GB": "{{summonerName}}'s Game", "de_DE": "Spiel von {{summonerName}}", "es_ES": "Partida de {{summonerName}}", "it_IT": "Partita di {{summonerName}}", "fr_FR": "Partie de {{summonerName}}", "ja_JP": "{{summonerName}}の試合", "ko_KR": "{{summonerName}} 님의 게임", "es_MX": "Partida de {{summonerName}}", "es_AR": "Partida de {{summonerName}}", "pt_BR": "Partida de {{summonerName}}", "en_US": "{{summonerName}}'s Game", "en_AU": "{{summonerName}}'s Game", "ru_RU": "Игра {{summonerName}}", "tr_TR": "{{summonerName}} oyunu", "en_PH": "{{summonerName}}'s Game", "en_SG": "{{summonerName}}'s Game", "th_TH": "เกมของ {{summonerName}}", "vi_VN": "Trận của {{summonerName}}", "id_ID": "Game {{summonerName}}", "zh_MY": "{{summonerName}} 的房间", "zh_CN": "{{summonerName}}的对局", "zh_TW": "{{summonerName}} 的房間"} #来自（From）：plugins/rcp-fe-lol-parties/global/{locale}/trans.json
    defaultLobbyName: str = custom_game_setup_name_default_dict.get(region_locale["locale"], "{{summonerName}}的对局").replace("{{summonerName}}", current_info["gameName"])
    for i in range(len(enabled_queueIds)):
        enabled_queueIds[i] = int(enabled_queueIds[i])
    enabled_queueIds.sort()
    logPrint("当前可用队列房间序号：\nCurrently enabled QueueIds:")
    available_queue_df: pandas.DataFrame = await check_available_queue(connection)
    logPrint("*****************************************************************************")
    print(format_df(available_queue_df)[0])
    log.write(format_df(available_queue_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
    logPrint("*****************************************************************************")
    logPrint("(%s\t%s\t%s)" %(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), platformId, game_version))
    status: int = 0 #返回值（Returned value）
    logPrint('请输入队列房间序号：（输入“0”以刷新可用队列信息。输入负数以退出创建。）\nPlease enter the queueId: (Enter "0" to refresh available queue information. Enter any negative number to exit creation.)')
    while True:
        valid_queueId: bool = False
        queueId: int = -1
        queueId_str: str = logInput()
        if queueId_str == "":
            continue
        elif queueId_str == "0":
            available_queue_df = await check_available_queue(connection)
            logPrint("*****************************************************************************")
            print(format_df(available_queue_df)[0])
            log.write(format_df(available_queue_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
            logPrint("*****************************************************************************")
            logPrint("(%s\t%s\t%s)" %(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), platformId, game_version))
            logPrint('请输入队列房间序号：（输入“0”以刷新可用队列信息。输入负数以退出创建。）\nPlease enter the queueId: (Enter "0" to refresh available queue information. Enter any negative number to exit creation.)')
            continue
        else:
            try:
                queueId = int(queueId_str)
            except ValueError:
                logPrint("请输入整数！\nPlease submit an integer!")
            else:
                if queueId < 0: #在启用循环测试时，只能通过这个分支退出函数（When `loop_test` is True, the user can exit the function only through this branch）
                    status = 2
                    break
                elif not queueId in gameQueues:
                    logPrint("未找到该队列！请重新输入。\nQueue not found! Please try again.")
                else:
                    valid_queueId = True
        if valid_queueId:
            lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            if "gameConfig" in lobby_information and not (queueId in gameQueues and gameQueues[queueId]["isCustom"]):
                response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-lobby/v1/parties/queue", data = str(queueId))).json()
                logPrint(response)
            else:
                lobbyName: str = defaultLobbyName
                lobbyPassword: str = ""
                aramMapMutator: str = "NONE"
                teamsize: int = 5
                spectatorPolicy: str = "AllAllowed"
                spectatorDelayEnabled: bool = False
                hidePublicly: bool = False
                if queueId in gameQueues and gameQueues[queueId]["isCustom"]:
                    if gameQueues[queueId]["gameMode"] == "ARAM" or gameQueues[queueId]["gameMode"] == "KIWI":
                        logPrint("请选择一个地图：\nPlease select a map:")
                        for i in range(len(ARAMmaps.keys())):
                            key: str = list(ARAMmaps.keys())[i]
                            logPrint("%d\t%s（%s）" %(i + 1, ARAMmaps_zh[key], ARAMmaps_en[key]))
                        while True:
                            back: bool = False
                            ARAMmapIndex: str = logInput()
                            if ARAMmapIndex == "":
                                continue
                            elif ARAMmapIndex[0] == "0":
                                if loop_test:
                                    back = True
                                    break
                                else:
                                    return 2
                            elif ARAMmapIndex in set(map(str, range(1, len(ARAMmaps) + 1))):
                                aramMapMutator = list(ARAMmaps.keys())[int(ARAMmapIndex) - 1]
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if back:
                            logPrint('请输入队列房间序号：（输入“0”以刷新可用队列信息。输入负数以退出创建。）\nPlease enter the queueID: (Enter "0" to refresh available queue information. Enter any negative number to exit creation.)')
                            continue
                    logPrint("请依次输入对局名、队伍规模、密码（可选）：\nPlease enter the lobby's name, team size and password (optional):")
                    logPrint("对局名（Lobby Name）：", end = "")
                    lobbyName: str = logInput()
                    if lobbyName == "":
                        lobbyName = defaultLobbyName
                    logPrint("队伍规模（Team Size）：", end = "")
                    while True:
                        back: bool = False
                        teamsize_str: str = logInput()
                        if teamsize_str == "":
                            teamsize = 5
                            break
                        elif teamsize_str == "0":
                            if loop_test:
                                back = True
                                break
                            else:
                                return 2
                        elif teamsize_str in list(map(str, range(1, 6))):
                            teamsize = int(teamsize_str)
                            break
                        else:
                            logPrint("队伍规模输入错误！请重新输入：\nError input of team size! Please try again:")
                    if back:
                        logPrint('请输入队列房间序号：（输入“0”以刷新可用队列信息。输入负数以退出创建。）\nPlease enter the queueID: (Enter "0" to refresh available queue information. Enter any negative number to exit creation.)')
                        continue
                    logPrint("密码（Password）：", end = "")
                    lobbyPassword = logInput()
                    logPrint("请选择自定义房间的允许观战策略：\nPlease select a spectator policy:\n1\t只允许房间内玩家（Lobby Only）\n2\t只允许好友（Friends List Only）\n☆3\t所有人（All）\n4\t无（None）")
                    while True:
                        customSpectatorPolicyTypeNumber_str: str = logInput()
                        if customSpectatorPolicyTypeNumber_str == "":
                            spectatorPolicy = "AllAllowed"
                            break
                        elif customSpectatorPolicyTypeNumber_str[0] == "0":
                            if loop_test:
                                back = True
                                break
                            else:
                                return 2
                        elif customSpectatorPolicyTypeNumber_str[0] in set(map(str, range(1, 5))):
                            if customSpectatorPolicyTypeNumber_str[0] == "1":
                                spectatorPolicy = "LobbyAllowed"
                            elif customSpectatorPolicyTypeNumber_str[0] == "2":
                                spectatorPolicy = "FriendsAllowed"
                            elif customSpectatorPolicyTypeNumber_str[0] == "3":
                                spectatorPolicy = "AllAllowed"
                            else:
                                spectatorPolicy = "NotAllowed"
                            break
                        else:
                            logPrint("允许观战策略输入错误！请重新输入：\nError input of spectator policy! Please try again:")
                    logPrint("是否添加观战延迟？（输入任意键以添加，否则不添加。）\nAdd spectating delay? (Submit any non-empty string to add delay, or null to refuse addition.)")
                    spectatorDelayEnabled_str = logInput()
                    spectatorDelayEnabled = bool(spectatorDelayEnabled_str)
                    print("是否从公开的房间列表中隐藏此房间？（输入任意键以隐藏，否则不隐藏。）\nHide this lobby from public lobby list? (Submit any non-empty string to hide, or null to show.)")
                    hidePublicly_str = logInput()
                    hidePublicly = bool(hidePublicly_str)
                queue: dict[str, Any] = {
                    "queueId": queueId,
                    "isCustom": False,
                    "customGameLobby": {
                        "lobbyName": lobbyName,
                        "lobbyPassword": lobbyPassword,
                        "configuration": {
                            "mapId": 0,
                            "aramMapMutator": aramMapMutator,
                            "gameMode": "",
                            "mutators": {
                                "id": 0
                            },
                            "spectatorPolicy": spectatorPolicy,
                            "teamSize": teamsize,
                            "maxPlayerCount": 0,
                            "gameServerRegion": "",
                            "spectatorDelayEnabled": spectatorDelayEnabled,
                            "hidePublicly": hidePublicly
                        }
                    }
                }
                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = queue)).json()
                logPrint(response)
            if isinstance(response, dict) and "errorCode" in response:
                if response["httpStatus"] == 400:
                    if response["message"] == "INVALID_REQUEST": #由队列更换接口返回（Returned by queue changing endpoint）
                        logPrint("队列更换请求无效！\nQueue change request invalid!")
                    elif response["message"] == "INVALID_PERMISSIONS": #由队列更换接口返回（Returned by queue changing endpoint）
                        logPrint("必须是小队拥有者才能更改模式！\nMust be party owner to change mode.")
                        logPrint("是否单独创建小队？（输入任意键以离开该小队并创建一个新小队，否则留在该小队。）\nDo you want to create another party? (Submit any non-empty string to leave this party and create another party, or null to stay in the current party.)")
                        create_party_str: str = logInput()
                        create_party: bool = bool(create_party_str)
                        if create_party:
                            response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/lol-lobby/v2/lobby")).json()
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = queue)).json()
                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                            if "gameConfig" in lobby_information:
                                logPrint(lobby_information)
                            else:
                                logPrint("此房间序号尚不可用。请选择其它序号。\nThis queueId isn't available yet. Please select another ID.")
                        else:
                            logPrint("已取消本次操作。\nCancelled this operation.")
                    elif response["message"] == "PARTY_SIZE_LIMIT":
                        logPrint("玩家过多，无法加入这条队列！\nThere are too many players for this mode!")
                    elif response["message"] == "INVALID_PARTY_STATE":
                        logPrint("小队状态无效！您可能目前正处于英雄选择阶段或游戏内。如果这个问题持续存在，请重启您的客户端。\nInvalid party state! You might be during a champ select stage or in a game. If this problem persists, please restart your League Client.")
                elif response["httpStatus"] == 423:
                    if response["message"] == "Gameflow prevented a lobby.": #由房间创建接口返回（Returned by lobby creation endpoint）
                        logPrint("您当前的状态不可创建房间！\nYou're not allowed to create a party/lobby at the moment.")
                elif response["httpStatus"] == 500:
                    if response["message"] == "INVALID_LOBBY": #由房间创建接口返回（Returned by lobby creation endpoint）
                        logPrint("房间信息无效！\nInvalid lobby configuration!")
                    elif response["message"] == "UNHANDLED_SERVER_SIDE_ERROR":
                        logPrint("服务器错误。请换一个队列序号并重试。\nUnhandled server side error. Please switch to another queueId and try again.")
                status = 1
                if not loop_test:
                    break
            else:
                status = 0
                if not loop_test:
                    break
    return status

async def create_custom_lobby(connection: Connection) -> int:
    practiceGameTypeConfigIds_source: list[float] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/ClientSystemStates/practiceGameTypeConfigIdList")).json()
    practiceGameTypeConfigIds: list[int] = sorted(map(int, practiceGameTypeConfigIds_source))
    gameTypeConfigs_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/gameTypeConfigs")).json()
    gameTypeConfigs: dict[int, dict[str, Any]] = {int(config["id"]): config for config in gameTypeConfigs_source}
    enabledModes: list[str] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/Mutators/EnabledModes")).json()
    gamemodes_zh: dict[str, str] = {key: gamemodes[key]["zh_CN"] for key in gamemodes}
    gamemodes_en: dict[str, str] = {key: gamemodes[key]["en_US"] for key in gamemodes}
    gamemaps_zh: dict[str, str] = {key: gamemaps[key]["zh_CN"] for key in gamemaps}
    gamemaps_en: dict[str, str] = {key: gamemaps[key]["en_US"] for key in gamemaps}
    ARAMmaps_zh: dict[str, str] = {key: ARAMmaps[key]["zh_CN"] for key in ARAMmaps}
    ARAMmaps_en: dict[str, str] = {key: ARAMmaps[key]["en_US"] for key in ARAMmaps}
    availableMapIds: dict[str, list[int]] = {"ARAM": [12], "ARAM_BOT": [12], "ARAM_UNRANKED_5x5": [12], "ARSR": [11], "ASCENSION": [8], "ASSASSINATE": [11], "BILGEWATER": [11], "BOT": [11], "BOT_3x3": [10], "BRAWL": [35], "CHERRY": [30], "CHERRY_UNRANKED": [30], "CHONCC_TREASURE_TFT": [22], "CLASH": [11], "CLASSIC": [11, 12, 21, 22], "COUNTER_PICK": [11], "DARKSTAR": [16], "DOOMBOTSTEEMO": [11], "FIRSTBLOOD": [4], "FIRSTBLOOD_1x1": [4], "FIRSTBLOOD_2x2": [4], "FIVE_YEAR_ANNIVERSARY_TFT": [22], "GAMEMODEX": [21, 11, 12, 22], "HEXAKILL": [10], "KINGPORO": [12], "KING_PORO": [12], "LNY23_TFT": [22], "LNY24_TFT": [22], "LNY25_TFT": [22], "NEXUSBLITZ": [21], "NIGHTMARE_BOT": [11], "NORMAL": [11], "NORMAL_3x3": [11], "NORMAL_TFT": [22], "ODIN": [8], "ODIN_UNRANKED": [8], "ODYSSEY": [20], "ONEFORALL": [11], "ONEFORALL_5x5": [11], "PRACTICETOOL": [11], "PROJECT": [19], "PVE_PUZZLE_TFT": [22], "RANKED_FLEX_SR": [11], "RANKED_FLEX_SR_5x5": [11], "RANKED_FLEX_TT": [11], "RANKED_PREMADE-3x3": [10], "RANKED_SOLO_5x5": [11], "RANKED_TEAM_3x3": [10], "RANKED_TEAM_5x5": [11], "RANKED_TFT": [22], "RANKED_TFT_DOUBLE_UP": [22], "RANKED_TFT_PAIRS": [22], "RANKED_TFT_TURBO": [22], "RIOTSCRIPT_BOT": [11], "SET_REVIVAL_5_5_TFT": [22], "SET_REVIVAL_TFT": [22], "SF_TFT": [22], "SIEGE": [11], "SNOWURF": [11], "SOLO_DUO_RANKED_5x5": [11], "SR_6x6": [11], "STARGUARDIAN": [18], "STRAWBERRY": [33], "SWIFTPLAY": [11], "TFT": [22], "TUTORIAL": [11, 12, 21, 22], "TUTORIAL_MODULE_1": [11], "TUTORIAL_MODULE_2": [11], "TUTORIAL_MODULE_3": [11], "ULTBOOK": [11], "URF": [11], "URF_BOT": [11]}
    gameTypes_zh: dict[str, str] = {key: gameTypes_config[key]["zh_CN"] for key in gameTypes_config}
    gameTypes_en: dict[str, str] = {key: gameTypes_config[key]["en_US"] for key in gameTypes_config}
    region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    custom_game_setup_name_default_dict: dict[str, str] = {"ar_AE": "مباراة {{summonerName}}", "cs_CZ": "Hra uživatele {{summonerName}}", "el_GR": "Παιχνίδι του {{summonerName}}", "pl_PL": "Rozgrywka gracza {{summonerName}}", "ro_RO": "Jocul lui {{summonerName}}", "hu_HU": "{{summonerName}} játéka", "en_GB": "{{summonerName}}'s Game", "de_DE": "Spiel von {{summonerName}}", "es_ES": "Partida de {{summonerName}}", "it_IT": "Partita di {{summonerName}}", "fr_FR": "Partie de {{summonerName}}", "ja_JP": "{{summonerName}}の試合", "ko_KR": "{{summonerName}} 님의 게임", "es_MX": "Partida de {{summonerName}}", "es_AR": "Partida de {{summonerName}}", "pt_BR": "Partida de {{summonerName}}", "en_US": "{{summonerName}}'s Game", "en_AU": "{{summonerName}}'s Game", "ru_RU": "Игра {{summonerName}}", "tr_TR": "{{summonerName}} oyunu", "en_PH": "{{summonerName}}'s Game", "en_SG": "{{summonerName}}'s Game", "th_TH": "เกมของ {{summonerName}}", "vi_VN": "Trận của {{summonerName}}", "id_ID": "Game {{summonerName}}", "zh_MY": "{{summonerName}} 的房间", "zh_CN": "{{summonerName}}的对局", "zh_TW": "{{summonerName}} 的房間"} #来自（From）：plugins/rcp-fe-lol-parties/global/{locale}/trans.json
    defaultLobbyName: str = custom_game_setup_name_default_dict.get(region_locale["locale"], "{{summonerName}}的对局").replace("{{summonerName}}", current_info["gameName"])
    logPrint("请选择自定义房间的游戏模式：\nPlease select a game mode of the lobby:")
    for i in range(len(enabledModes)):
        logPrint("%d\t%s%s%s%s" %(i + 1, gamemodes_zh[enabledModes[i].upper()], "【" if "(" in gamemodes_en[enabledModes[i].upper()] else "（", gamemodes_en[enabledModes[i].upper()], "】" if "(" in gamemodes_en[enabledModes[i].upper()] else "）"), write_time = False)
    while True:
        gameModeTypeNumber: str = logInput()
        if gameModeTypeNumber == "":
            continue
        elif gameModeTypeNumber == "0":
            return 2
        elif gameModeTypeNumber in list(map(str, range(1, len(enabledModes) + 1))):
            selectedMode: str = enabledModes[int(gameModeTypeNumber) - 1].upper()
            break
        else:
            logPrint("游戏模式输入错误！请重新输入：\nError input of game mode! Please try again:")
    logPrint("请输入地图序号：\nPlease enter a mapID:")
    for i in sorted(gamemaps_zh.keys()):
        logPrint("%s%d\t%s%s%s%s" %("☆" if i in availableMapIds[selectedMode] else "", i, gamemaps_zh[i], "【" if "(" in gamemaps_en[i] else "（", gamemaps_en[i], "】" if "(" in gamemaps_en[i] else "）"), write_time = False)
    while True:
        mapId_str: str = logInput()
        if mapId_str == "" and len(availableMapIds[selectedMode]) > 0:
            mapId: int = availableMapIds[selectedMode][0]
            break
        elif mapId_str == "0":
            return 2
        elif mapId_str in list(map(str, gamemaps_zh.keys())):
            mapId = int(mapId_str)
            break
        else:
            logPrint("地图序号输入错误！请重新输入：\nError input of mapID! Please try again:")
    if (selectedMode == "ARAM" or selectedMode == "KIWI") and mapId == 12:
        logPrint("请选择一个极地大乱斗地图：\nPlease select an ARAM map:")
        for i in range(len(ARAMmaps.keys())):
            key: str = list(ARAMmaps.keys())[i]
            logPrint("%d\t%s（%s）" %(i + 1, ARAMmaps_zh[key], ARAMmaps_en[key]))
        while True:
            ARAMmapIndex: str = logInput()
            if ARAMmapIndex == "":
                continue
            elif ARAMmapIndex[0] == "0":
                return 2
            elif ARAMmapIndex in set(map(str, range(1, len(ARAMmaps) + 1))):
                aramMapMutator: str = list(ARAMmaps.keys())[int(ARAMmapIndex) - 1]
                break
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
    else:
        aramMapMutator = "NONE"
    print("请选择自定义房间的游戏类型：\nPlease select a game type of the lobby:")
    for i in practiceGameTypeConfigIds:
        config: str = gameTypeConfigs[i]
        print("%d\t%s%s%s%s" %(i, gameTypes_zh[config["name"]], "【" if "(" in gameTypes_en[config["name"]] else "（", gameTypes_en[config["name"]], "】" if "(" in gameTypes_en[config["name"]] else "）"))
    while True:
        mutatorId_str: str = logInput()
        if mutatorId_str == "":
            continue
        elif mutatorId_str == "0":
            return 2
        elif mutatorId_str in list(map(str, practiceGameTypeConfigIds)):
            mutatorId: int = int(mutatorId_str)
            break
        else:
            logPrint("游戏类型输入错误！请重新输入：\nError input of game type! Please try again:")
    logPrint("请选择自定义房间的允许观战策略：\nPlease select a spectator policy:\n1\t只允许房间内玩家（Lobby Only）\n2\t只允许好友（Friends List Only）\n3\t所有人（All）\n4\t无（None）")
    while True:
        customSpectatorPolicyTypeNumber_str: str = logInput()
        if customSpectatorPolicyTypeNumber_str == "":
            continue
        elif customSpectatorPolicyTypeNumber_str[0] == "0":
            return 2
        elif customSpectatorPolicyTypeNumber_str[0] in set(map(str, range(1, 5))):
            customSpectatorPolicyTypeNumber: int = int(customSpectatorPolicyTypeNumber_str[0])
            break
        else:
            logPrint("允许观战策略输入错误！请重新输入：\nError input of spectator policy! Please try again:")
    logPrint("请依次输入对局名、队伍规模、密码（可选）：\nPlease enter the lobby's name, team size and password (optional):")
    logPrint("对局名（Lobby Name）：", end = "")
    lobbyName: str = logInput()
    if lobbyName == "":
        lobbyName = defaultLobbyName
    logPrint("队伍规模（Team Size）：", end = "")
    while True:
        teamsize_str: str = logInput()
        if teamsize_str == "":
            teamsize: int = 5
            break
        elif teamsize_str == "0":
            return 2
        elif teamsize_str in list(map(str, range(1, 6))):
            teamsize = int(teamsize_str)
            break
        else:
            logPrint("队伍规模输入错误！请重新输入：\nError input of team size! Please try again:")
    logPrint("密码（Password）：", end = "")
    lobbyPassword: str = logInput()
    logPrint("是否添加观战延迟？（输入任意键以添加，否则不添加。）\nAdd spectating delay? (Submit any non-empty string to add delay, or null to refuse addition.)")
    spectatorDelayEnabled_str: str = logInput()
    spectatorDelayEnabled: bool = bool(spectatorDelayEnabled_str)
    print("是否从公开的房间列表中隐藏此房间？（输入任意键以隐藏，否则不隐藏。）\nHide this lobby from public lobby list? (Submit any non-empty string to hide, or null to show.)")
    hidePublicly_str: str = logInput()
    hidePublicly: bool = bool(hidePublicly_str)
    custom: dict[str, Any] = {
        "queueId": 0,
        "isCustom": True,
        "customGameLobby": {
            "lobbyName": lobbyName,
            "lobbyPassword": lobbyPassword,
            "configuration": {
                "mapId": mapId,
                "aramMapMutator": aramMapMutator,
                "gameMode": selectedMode,
                "gameTypeConfig": {
                    "id": mutatorId
                },
                "spectatorPolicy": SPECTATOR_POLICY_LIST[customSpectatorPolicyTypeNumber - 1],
                "teamSize": teamsize,
                "maxPlayerCount": 0,
                "gameServerRegion": "",
                "spectatorDelayEnabled": spectatorDelayEnabled,
                "hidePublicly": hidePublicly
            }
        }
    }
    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)).json()
    logPrint(response)
    if isinstance(response, dict) and "errorCode" in response:
        if response["httpStatus"] == 423 and response["message"] == "Gameflow prevented a lobby.":
            logPrint("您当前的状态不可创建房间！\nYou're not allowed to create a party/lobby at the moment.")
        elif response["httpStatus"] == 437 and response["message"] == "INVALID_LOBBY_NAME":
            logPrint("您设置的房间名不合法！请换一个房间名后重试。\nThe lobby name you submitted is invalid. Please change the name.")
        elif response["httpStatus"] == 500 and response["message"] == "INVALID_LOBBY":
            logPrint("房间信息无效！\nInvalid lobby configuration!")
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

async def sort_custom_lobbies(connection: Connection) -> pandas.DataFrame:
    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/custom-games/refresh")).json()
    custom_lobbies: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v1/custom-games")).json()
    custom_lobby_header_keys: list[str] = list(custom_lobby_header.keys())
    custom_lobby_data: dict[str, list[Any]] = {key: [] for key in custom_lobby_header_keys}
    if not (isinstance(custom_lobbies, dict) and "errorCode" in custom_lobbies):
        for lobby in custom_lobbies:
            for i in range(len(custom_lobby_header_keys)):
                key: str = custom_lobby_header_keys[i]
                if i == 12: #观战策略（`spectatorPolicy`）
                    to_append: Any = spectatorPolicies[lobby["spectatorPolicy"]]
                elif i == 13: #地图名称（`mapName`）
                    to_append = gamemaps[lobby["mapId"]]["zh_CN"]
                elif i == 14: #玩家比例（`filledPlayerRatio`）
                    to_append = "%d/%d" %(lobby["filledPlayerSlots"], lobby["maxPlayerSlots"])
                elif i == 15: #观战者比例（`filledSpectatorRatio`）
                    to_append = "%d/%d" %(lobby["filledSpectatorSlots"], lobby["maxSpectatorSlots"])
                else:
                    to_append = lobby[key]
                custom_lobby_data[key].append(to_append)
    custom_lobby_statistics_output_order: list[int] = [4, 5, 9, 2, 6, 13, 0, 7, 14, 12, 1, 8, 15, 3, 11, 10]
    custom_lobby_data_organized: dict[str, list[Any]] = {custom_lobby_header_keys[i]: custom_lobby_data[custom_lobby_header_keys[i]] for i in custom_lobby_statistics_output_order}
    custom_lobby_df: pandas.DataFrame = pandas.DataFrame(data = custom_lobby_data_organized)
    optimize_bool_display(custom_lobby_df)
    custom_lobby_df = pandas.concat([pandas.DataFrame([custom_lobby_header])[custom_lobby_df.columns], custom_lobby_df], ignore_index = True)
    return custom_lobby_df

async def create_lobby_json(connection: Connection) -> int:
    logPrint('请输入用于创建房间的json代码：\nPlease input the json code to create the custom lobby:\n格式（Format）：\n{"queueId": 0, "isCustom": True, "customGameLobby": {"lobbyName": "string", "lobbyPassword": "string", "configuration": {"mapId": 0, "aramMapMutator": "string", "gameMode": "string", "mutators": {"id": 0}, "spectatorPolicy": "AllAllowed", "teamSize": 0, "gameServerRegion": "string", "spectatorDelayEnabled": True, "hidePublicly": True}}}\nlobbyChange = ', end = "")
    while True:
        s: str = logInput()
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
    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = body)).json()
    logPrint(response)
    if isinstance(response, dict) and "errorCode" in response:
        return 1
    else:
        return 0

async def create_lobby(connection: Connection) -> bool:
    while True:
        logPrint("选择一个房间类型：\nSelect a type of lobby:\n1\t创建小队（Create a party）\n2\t创建自定义房间（Create a custom lobby）\n3\t通过json创建（Create through json）")
        method: str = logInput()
        if method == "":
            continue
        elif method[0] == "0":
            return False
        elif method[0] in ["1", "2", "3"]:
            if method[0] == "1":
                result: int = await create_queue_lobby(connection)
            elif method[0] == "2":
                result = await create_custom_lobby(connection)
            else:
                result = await create_lobby_json(connection)
            if result == 0:
                gameflow_phase: str = await get_gameflow_phase(connection)
                if gameflow_phase == "Lobby":
                    logPrint("房间创建成功。\nLobby/Party created successfully.")
                    return True
                else:
                    logPrint("房间创建失败。\nLobby/Party failed to be created.")
            elif result == 1 or result == 2:
                pass

async def add_bots_team(connection: Connection, teamId: str = "200") -> None:
    if not os.path.exists("available-bots.xlsx"):
        logPrint("未在同目录下发现可用电脑玩家工作簿。请使用查英雄脚本生成该工作簿。\nAvailable bot workbook isn't found under the same directory. Please generate it through Customized Program 04.")
        return
    try:
        localdata: pandas.DataFrame = pandas.read_excel("available-bots.xlsx", sheet_name = "Sheet2", usecols = list(range(1, 5)), skiprows = [1]) #Sheet2存储的是所有可用的电脑模型（Sheet2 stores all available AI models）
    except ValueError:
        logPrint("未找到工作表Sheet2。请使用查英雄脚本重新生成一次。\nSheet2 isn't found. Please generate one more time using Customized Program 04.")
        return
    allBotChampionIds: list[int] = localdata["id"].to_list()
    #准备一些数据资源（Prepare some data resources）
    lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    maxTeamSize: int = lobby_information["gameConfig"]["maxTeamSize"]
    roles: dict[str, str] = {"assassin": "刺客", "fighter": "战士", "mage": "法师", "marksman": "射手", "support": "辅助", "tank": "坦克", "arbitrary": "任意"}
    ##英雄的推荐路线（Recommended positions for champions）
    recommended_position_for_champion: dict[str, dict[str, list[str]]] = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    recommended_position_for_champion_keys: list[str] = list(recommended_position_for_champion.keys())
    for championId in recommended_position_for_champion_keys:
        if not int(championId) in allBotChampionIds:
            del recommended_position_for_champion[championId]
    ##可用的路线（Available lanes）
    botPositions_set: set[str] = set()
    for champion in recommended_position_for_champion.values():
        botPositions_set |= set(champion["recommendedPositions"])
    botPositions: list[str] = list(botPositions_set)
    botPositions_tmp: list[str] = []
    for position in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]: #将可用角色定位按照一定的顺序排列（Arrange the available lanes in a certain order）
        if position in botPositions:
            botPositions.remove(position)
            botPositions_tmp.append(position)
    botPositions = botPositions_tmp + botPositions
    botPositions_bulkLane: list[str] = list(botPositions_set)
    botPositions_tmp: list[str] = []
    for position in ["TOP", "MIDDLE", "BOTTOM", "UTILITY", "JUNGLE"]:
        if position in botPositions_bulkLane:
            botPositions_bulkLane.remove(position)
            botPositions_tmp.append(position)
    botPositions_bulkLane = botPositions_tmp + botPositions_bulkLane
    del botPositions_tmp
    #botPositions: list[str] = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    #botPositions_bulkLane: list[str] = ["TOP", "MIDDLE", "BOTTOM", "UTILITY", "JUNGLE"]
    ##各分路的英雄（Champions on each lane）
    recommended_champion_for_position: dict[str, list[int]] = {} #用于生成某条分路的随机英雄（Used to generate random champions of specific positions respectively）
    for position in botPositions:
        recommended_champion_for_position[position] = []
    for championId in recommended_position_for_champion:
        for position in recommended_position_for_champion[championId]["recommendedPositions"]:
            recommended_champion_for_position[position].append(int(championId))
    for position in recommended_champion_for_position:
        recommended_champion_for_position[position].sort()
    ##角色定位（Champion roles）
    roles_set: set[str] = set()
    for champion in LoLChampions.values():
        roles_set |= set(champion["roles"])
    roleList: list[str] = list(roles_set)
    roles_tmp: list[str] = []
    for role in ["assassin", "fighter", "mage", "marksman", "support", "tank"]: #将可用角色定位按照一定的顺序排列（Arrange the available positions in a certain order）
        if role in roleList:
            roleList.remove(role)
            roles_tmp.append(role)
    roleList = roles_tmp + roleList
    #roleList: list[str] = ["assassin", "fighter", "mage", "marksman", "support", "tank"]
    ##各角色定位的英雄（Champions of each role）
    recommended_champion_for_role: dict[str, list[int]] = {} #用于生成某个角色定位的随机英雄（Used to generate random champions of specific roles respectively）
    for role in roleList:
        recommended_champion_for_role[role] = []
    for championId in LoLChampions:
        for role in LoLChampions[championId]["roles"]:
            recommended_champion_for_role[role].append(championId)
    ##可用的电脑玩家难度（Available bot difficulty）
    botDifficulties: list[str] = ["EASY", "MEDIUM", "HARD", "RSWARMINTRO", "RSINTRO", "RSBEGINNER", "RSINTERMEDIATE"]
    #先生成电脑玩家的英雄序号（First, generate the bot championIds）
    botPositions_add: list[str] = []
    logPrint("队伍%s：请选择自选电脑玩家或者随机生成电脑玩家：\nTeam %s: Please select the option to generate bot players:\n0\t跳过该队伍（Skip this team）\n1\t完全随机生成（Completely Randomly）\n2\t按照分路随机生成（Randomly according to Positions）\n3\t自选（By Picking）" %(teamId[0], teamId[0]))
    while True:
        option: str = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            return
        elif option[0] == "1":
            logPrint("请输入电脑玩家数量：\nPlease enter the number of bot players:")
            while True:
                nBot_str: str = logInput()
                if nBot_str == "":
                    continue
                elif nBot_str in map(str, range(1, maxTeamSize + 1)):
                    nBot: int = int(nBot_str)
                    while True:
                        team: list[int] = random.sample(allBotChampionIds, nBot)
                        logPrint("程序为您分配到以下英雄：\nYou have been distributed the following bot champions:\n*****************************************************************************")
                        for championId in team:
                            logPrint("{0:<14}".format(LoLChampions[championId]["name"]) + "\t" + "{0:<14}".format(LoLChampions[championId]["alias"]) + "\t" + json.dumps(recommended_position_for_champion[str(championId)]["recommendedPositions"], ensure_ascii = False), write_time = False)
                        logPrint("*****************************************************************************\n是否重新随机英雄？（输入任意键以重新随机，否则进行下一步）\nDo you want to regenerate the champions? (Input anything to reroll, or null to enter the next step)", write_time = False)
                        reroll_str: str = logInput()
                        reroll: bool = bool(reroll_str)
                        if not reroll:
                            break
                    break
                else:
                    logPrint("电脑玩家数量不合法！请重新输入：\nIllegal bot players number! Please try again:")
        elif option[0] == "2":
            logPrint(f'请输入分路，以空格为分隔符。（默认使用全分路。）\nPlease enter the bot positions split by space (among {botPositions}, all of which are taken by default.)')
            while True:
                botPositions_add_str: str = logInput()
                botPositions_add = botPositions_add_str.split()
                if botPositions_add == []:
                    botPositions_add = botPositions_bulkLane[:]
                if all(map(lambda x: x in botPositions_bulkLane, botPositions_add)):
                    botPositions_add = botPositions_add[:maxTeamSize]
                    break
                else:
                    logPrint(f"电脑玩家路线错误！请选择{botPositions}中的一个：\nError input of botDifficulty! Please choose among {botPositions}:")
            while True:
                logPrint("您想要对战什么样的阵容？\nWhat comp do you want to fight against?\n1\t清一色阵容（Pure comp）\n2\t自定义阵容（Customized comp）\n3\t任意阵容（Arbitrary comp）")
                back: bool = False
                # comp_specified: bool = False
                comp_option: str = logInput()
                if comp_option != "" and comp_option[0] == "1":
                    logPrint("请选择角色定位类型：\nPlease select a role type:\n1\t纯刺客（All assassin）\n2\t纯战士（All fighters）\n3\t纯法师（All mages）\n4\t纯射手（All marksmen）\n5\t纯辅助（All supports）\n6\t纯坦克（All tanks）")
                    while True:
                        fullcomp_role_option: str = logInput()
                        if fullcomp_role_option in list(map(str, range(1, len(roleList) + 1))):
                            # comp_specified = True
                            comp_role: str = roleList[int(fullcomp_role_option) - 1]
                            logPrint("您选择了纯%s阵容。\nYou chose all-%s comp." %(roles[comp_role], comp_role))
                            break
                        elif fullcomp_role_option == "0":
                            back = True
                            comp_role = "" #占位（Dummy）
                            break
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if back:
                        continue
                    comp_roles: list[str] = [comp_role] * len(botPositions_add)
                    role_specific_championIds: list[list[int]] = [recommended_champion_for_role[comp_role]] * len(botPositions_add)
                elif comp_option != "" and comp_option[0] == "2":
                    logPrint("请依次为上路、打野、中路、下路和辅助位置指定英雄角色定位，以空格为分隔符。\nPlease specify the roles for TOP, JUNGLE, MIDDLE, BOTTOM and UTILITY champions, respectively, split by space.\n1\t刺客（Assassin）\n2\t战士（Fighter）\n3\t法师（Mage）\n4\t射手（Marksman）\n5\t辅助（Support）\n6\t坦克（Tank）\n示例输入（Example）：\n2 2 3 4 6\n4 6 1 3 5")
                    while True:
                        comp_role_numbers_str: str = logInput()
                        try:
                            comp_role_numbers: list[int] = list(map(int, comp_role_numbers_str.split()))
                        except ValueError:
                            logPrint("您的输入有误！请输入整数。\nERROR input! Please enter integers.")
                        else:
                            if comp_role_numbers == [0]:
                                back = True
                                break
                            elif len(comp_role_numbers) != len(botPositions_add):
                                logPrint("数量不符！请输入%d个位置的英雄角色定位。\nLength mismatch! Please enter %d champion roles." %(len(botPositions_add), len(botPositions_add)))
                            elif any(map(lambda x: x < 1 or x > 6, comp_role_numbers)):
                                logPrint("您的输入有误！请输入1～6之间的正整数。\nERROR input! Please enter positive integers between 1 and 6.")
                            else:
                                # comp_specified = True
                                comp_roles = list(map(lambda x: roleList[x - 1], comp_role_numbers))
                                comp_role_str_zh: str = "、".join(list(map(lambda x: roles[roleList[x - 1]], comp_role_numbers)))
                                comp_role_str_en: str = ", ".join(list(map(lambda x: roleList[x - 1], comp_role_numbers)))
                                logPrint(f"您为上路、打野、中路、下路和辅助位置分别指定了{comp_role_str_zh}英雄。\nYou specified {comp_role_str_en} champions for TOP, JUNGLE, MIDDLE, BOTTOM and UTILITY champions, respectively.")
                                break
                    if back:
                        continue
                    role_specific_championIds = [recommended_champion_for_role[roleList[i - 1]] for i in comp_role_numbers]
                else:
                    comp_roles = ["arbitrary"] * len(botPositions_add)
                    role_specific_championIds = [allBotChampionIds] * len(botPositions_add)
                break
            sample_notfound_hints_printed = {position: False for position in botPositions_add} #有些分路可能没有特定的角色。这样的提示只需要输出一遍（Some lanes might be lack of certain roles. Such hints only need to be printed once）
            while True:
                team = []
                for i in range(len(botPositions_add)):
                    position: str = botPositions_add[i]
                    role: str = comp_roles[i]
                    candidate_champions: list[int] = sorted(set(recommended_champion_for_position[position]) & set(role_specific_championIds[i]))
                    if len(candidate_champions) == 0:
                        if not sample_notfound_hints_printed[position]:
                            logPrint("%s位置无%s英雄。将不再限定角色定位。\nNo %s champions found for %s. The program will use another arbitrary role." %(positions[position], roles[role], role, position))
                            sample_notfound_hints_printed[position] = True
                        candidate_champions = recommended_champion_for_position[position]
                        comp_roles[i] = "arbitrary"
                    team += random.sample(candidate_champions, 1)
                logPrint("程序为您分配到以下英雄：\nYou have been distributed the following bot champions:\n*****************************************************************************")
                for i in range(len(team)):
                    logPrint("{0:<14}".format(LoLChampions[team[i]]["name"]) + "\t" + "{0:<14}".format(LoLChampions[team[i]]["alias"]) + "\t" + botPositions_add[i] + "\t" + comp_roles[i], write_time = False)
                logPrint("*****************************************************************************\n是否重新随机英雄？（输入任意非空字符串以重新随机，否则进行下一步。）\nDo you want to regenerate the champions? (Input any non-empty string to reroll, or null to enter the next step.)", write_time = False)
                tmp: str = logInput()
                if tmp == "" or tmp[0] == "s":
                    break
            if tmp != "" and tmp[0] == "s": #隐藏功能：自行指定（Hidden function: manually specify the champions）
                logPrint('''请按照“上路—打野—中路—下路—辅助”的顺序逐行输入电脑玩家的英雄序号：\nPlease input the bot championIds in the "TOP-JUNGLE-MIDDLE-BOTTOM-UTILITY" order, one bot per line:''')
                team: list[int] = []
                for position in botPositions:
                    while True:
                        try:
                            championId_str: str = logInput()
                            if championId_str == "":
                                continue
                            else:
                                championId: int = int(championId_str)
                                if championId in recommended_champion_for_position[position]:
                                    team.append(championId)
                                    logPrint("您已选择以下英雄：\nYou have selected the bot champions as follows:\n*****************************************************************************")
                                    for i in range(len(team)):
                                        logPrint("{0:<14}".format(LoLChampions[team[i]]["name"]) + "\t" + "{0:<14}".format(LoLChampions[team[i]]["alias"]) + "\t" + botPositions[i], write_time = False)
                                    logPrint("*****************************************************************************", write_time = False)
                                    break
                                elif championId in allBotChampionIds:
                                    recommended_position_str_zh: str = "、".join(list(map(lambda x: positions[x], recommended_position_for_champion[str(championId)]["recommendedPositions"])))
                                    recommended_position_str_en: str = ", ".join(recommended_position_for_champion[str(championId)]["recommendedPositions"])
                                    logPrint("%s的推荐路线是%s。请选择一位适合%s的英雄，或者在选择%s位英雄时输入该英雄的序号。\nThe recommended positions for %s include %s. Please select a champion whose recommended positions include %s, or input this championId when selecting champions of the following lane(s): %s." %(LoLChampions[championId]["name"], recommended_position_str_zh, positions[position], recommended_position_str_zh, LoLChampions[championId]["alias"], recommended_position_str_en, position, recommended_position_str_en))
                                elif championId in LoLChampions:
                                    logPrint("没有名为%s的电脑玩家。请对照可用电脑玩家工作簿的第一张工作表选择一个%s英雄。\nThere's not a bot named %s. Please refer to Sheet1 of the available-bots workbook and select a %s champion." %(LoLChampions[championId]["name"], positions[position], LoLChampions[championId]["alias"], position))
                                else:
                                    logPrint(f"没有序号为{championId}的英雄。请重新输入！\nNo champion with championId {championId}. Please try again!")
                        except ValueError:
                            logPrint("您的输入有误！请输入一个正整数。\nERROR input of championId! Please submit a positive integer.")
        else:
            logPrint("请输入电脑玩家的id，以空格为分隔符：\nPlease input the ids of bot players, split by space:")
            while True:
                team_str: str = logInput()
                try:
                    team: list[int] = list(map(int, team_str.split()))
                except ValueError:
                    logPrint("您的输入有误，请重新输入！\nInput ERROR! Please try again!")
                else:
                    break
            logPrint("您已选择以下英雄：\nYou have selected the bot champions as follows:\n*****************************************************************************")
            for championId in team:
                logPrint("{0:<14}".format(LoLChampions[championId]["name"]) + "\t" + "{0:<14}".format(LoLChampions[championId]["alias"]) + "\t" + str(recommended_position_for_champion[str(championId)]["recommendedPositions"]))
            logPrint("*****************************************************************************")
        break
    #再确定每个电脑玩家的难度（Then, determine the difficulty for each bot）
    botUuid_team: list[str] = []
    logPrint("是否设定电脑玩家难度一致？（输入任意非空字符串设定为不一致，否则一致。）\nSet all botDifficulties identical? (Any non-empty string for N, or null for Y.)")
    botDifficulty_consistency_str: str = logInput()
    botDifficulty_consistency: bool = not bool(botDifficulty_consistency_str)
    if botDifficulty_consistency:
        logPrint(f"请输入电脑玩家的难度：\nPlease enter the botDifficulty: (among {botDifficulties})")
        while True:
            botDifficulty_team: str = logInput()
            if botDifficulty_team == "":
                botDifficulty_team = "RSINTERMEDIATE"
                break
            elif botDifficulty_team in botDifficulties:
                break
            else:
                logPrint(f"电脑玩家难度输入错误！请选择{botDifficulties}中的一个：\nError input of botDifficulty! Please choose among {botDifficulties}:")
        if option[0] == "2": #在按照分路随机生成英雄序号时，分路已经确定（When championIds are generated based on lanes respectively, lanes are already determined）
            botPositions_team: list[str] = botPositions_add[:]
            for i in range(len(team)):
                Id: int = team[i]
                botUuid: str = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                bot: dict[str, int | str] = {"championId": Id, "botDifficulty": botDifficulty_team, "teamId": teamId, "position": botPositions_add[i], "botUuid": botUuid}
                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
        else:
            logPrint(f"请依次输入电脑玩家路线：\nPlease enter the botPositions: (among {botPositions})")
            botPositions_team: list[str] = []
            for i in range(len(team)):
                Id = team[i]
                botUuid = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                while True:
                    botPosition_tmp: str = logInput()
                    if botPosition_tmp == "":
                        continue
                    elif botPosition_tmp in botPositions:
                        botPositions_team.append(botPosition_tmp)
                        bot: dict[str, int | str] = {"championId": Id, "botDifficulty": botDifficulty_team, "teamId": teamId, "position": botPosition_tmp, "botUuid": botUuid}
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
                        break
                    else:
                        logPrint(f"电脑玩家路线错误！请选择{botPositions}中的一个：\nError input of botDifficulty! Please choose among {botPositions}:")
        logPrint("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
        for i in range(len(team)):
            logPrint("{0:<14}".format(LoLChampions[team[i]]["name"]) + "\t" + "{0:<14}".format(LoLChampions[team[i]]["alias"]) + "\t" + botDifficulty_team + "\t" + botPositions_team[i] + "\t" + botUuid_team[i], write_time = False)
        logPrint("*****************************************************************************\n", write_time = False)
    else:
        if option[0] == "2":
            logPrint(f"请依次输入电脑玩家的难度：\nPlease enter the botDifficulty: (among {botDifficulties})")
            botDifficulties_team: list[str] = []
            botPositions_team: list[str] = botPositions_add[:]
            for i in range(len(team)):
                Id = team[i]
                botUuid = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                botPosition_tmp = botPositions_add[i]
                while True:
                    botDifficulty_tmp = logInput()
                    if botDifficulty_tmp == "":
                        continue
                    elif botDifficulty_tmp in botDifficulties:
                        botDifficulties_team.append(botDifficulty_tmp)
                        bot: dict[str, int | str] = {"championId": Id, "botDifficulty": botDifficulty_tmp, "teamId": teamId, "position": botPosition_tmp, "botUuid": botUuid}
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
                        break
                    else:
                        logPrint(f"电脑玩家难度输入错误！请选择{botDifficulties}中的一个：\nError input of botDifficulty! Please choose among {botDifficulties}:")
        else:
            logPrint(f"请依次输入电脑玩家的难度和路线，以空格为分隔符：\nPlease enter the botDifficulty (among {botDifficulties}) and role (among {botPositions}), split by space:")
            botDifficulties_team: list[str] = []
            botPositions_team: list[str] = []
            for i in range(len(team)):
                Id = team[i]
                botUuid = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                while True:
                    tmp: str = logInput()
                    if tmp == "":
                        continue
                    else:
                        try:
                            botDifficulty_tmp, botPosition_tmp = tmp.split()
                        except ValueError:
                            logPrint("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
                        else:
                            if botDifficulty_tmp in botDifficulties and botPosition_tmp in botPositions:
                                botDifficulties_team.append(botDifficulty_tmp)
                                botPositions_team.append(botPosition_tmp)
                                bot: dict[str, int | str] = {"championId": Id, "botDifficulty": botDifficulty_tmp, "teamId": teamId, "position": botPosition_tmp, "botUuid": botUuid}
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
                                break
                            elif not botDifficulty_tmp in botDifficulties and botPosition_tmp in botPositions:
                                logPrint(f"电脑玩家难度输入错误！请选择{botDifficulties}中的一个：\nError input of botDifficulty! Please choose among {botDifficulties}:")
                            elif botDifficulty_tmp in botDifficulties and not botPosition_tmp in botPositions:
                                logPrint(f"电脑玩家路线输入错误！请选择{botPositions}中的一个：\nError input of botPositions! Please choose among {botPositions}:")
                            else:
                                logPrint(f"电脑玩家难度和路线输入错误！\nError input of botDifficulty!\n请选择{botDifficulties}中的一个作为电脑玩家难度。\nPlease choose among {botDifficulties} as botDifficulty.\n请选择{botPositions}中的一个作为电脑玩家路线。\nPlease choose among {botDifficulties} as botPositions.")
        logPrint("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
        for i in range(len(team)):
            logPrint("{0:<14}".format(LoLChampions[team[i]]["name"]) + "\t" + "{0:<14}".format(LoLChampions[team[i]]["alias"]) + "\t" + botDifficulties_team[i] + "\t" + botPositions_team[i] + "\t" + botUuid_team[i], write_time = False)
        logPrint("*****************************************************************************\n", write_time = False)

async def sort_received_invitations(connection: Connection) -> None:
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_source}
    receivedInvitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
    invid_header_keys: list[str] = list(invid_header.keys())
    invid_data: dict[str, list[Any]] = {key: [] for key in invid_header_keys}
    for invid in receivedInvitations:
        inviter_info_recapture: int = 0
        inviter_info: dict[str, Any] = await get_info(connection, invid["fromSummonerId"])
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
                        invid_timestamp: int = int(invid["timestamp"])
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

async def gameflow_phase_transition(connection: Connection) -> str:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t创建房间（Create a lobby）\n2\t处理邀请（Handle invitations）\n3\t加入小队或自定义房间（Join party/lobby）\n4\t观战（Spectate a game）\n5\t聊天（Chat）\n6\t举报一名玩家（Report a player）\n7\t其它（Others）\n8\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option == "-1":
            await send_commands(connection, log = log)
        elif option[0] == "1":
            lobby_created: bool = await create_lobby(connection)
            if lobby_created:
                break
        elif option[0] == "2":
            await handle_invitations(connection)
        elif option[0] == "3":
            lobby_created = await join_game(connection)
            if lobby_created:
                break
        elif option[0] == "4":
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase == "None":
                logPrint('请输入您想要观看的玩家召唤师名。输入“0”以返回上一层。\nPlease input the summonerName of the player to spectate. Submit "0" to return to the last step.')
                spectatorKey: str = str(uuid.uuid4())
                while True:
                    spectating_summonerName: str = logInput()
                    if spectating_summonerName == "":
                        continue
                    elif spectating_summonerName == "0":
                        break
                    else:
                        spectating_summoner_info: dict[str, Any] = await get_info(connection, spectating_summonerName)
                        if spectating_summoner_info["info_got"]:
                            if spectating_summoner_info["body"]["puuid"] == current_info["puuid"]:
                                logPrint("你不能观战自己。战斗！爽！————\nYou can't spectate yourself. Battle... YES!!!!")
                                continue
                            dropInSpectateGameId: int = 0
                            gameQueueType: str = ""
                            allowObserveMode: str = ""
                            spectate_puuid: str = spectating_summoner_info["body"]["puuid"]
                            spectating_summonerName: str = get_info_name(spectating_summoner_info["body"])
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
                                elif gsm_spectate_info == {"status": {"message": "Method Not Allowed", "status_code": 405}}:
                                    logPrint("当前大区不支持通过玩家通用唯一识别码获取观战密钥。请在客户端内右键点击一名好友观战。\nThis server doesn't support obtaining spectator key from puuid. Please right click on a friend to spectate it in the League Client.")
                                else:
                                    dropInSpectateGameId = gsm_spectate_info["playerCredentials"]["gameId"]
                                    gameQueueType = gsm_spectate_info["playerCredentials"]["queueType"]
                                    allowObserveMode = "AllAllowed"
                                    spectatorKey: str = gsm_spectate_info["playerCredentials"]["spectatorKey"]
                                    spectatorKey_got = True
                            #如果gsm接口失效，则要求用户自行输入观战密钥（If the gsm endpoint doesn't work, as the user to provide the spectatorKey）
                            if not spectatorKey_got:
                                logPrint('''如果您能够获取该玩家的观战密钥的话，您可以在下方输入观战密钥。不输入任何内容以放弃观战。\nIf you can access this player's spectatorKey, please input it below. Enter nothing to quit spectating.''')
                                spectatorKey = logInput()
                                if spectatorKey != "":
                                    spectatorKey_got = True
                            if spectatorKey_got:
                                body: dict[str, Any] = {"dropInSpectateGameId": str(dropInSpectateGameId), "gameQueueType": gameQueueType, "allowObserveMode": allowObserveMode, "puuid": spectate_puuid, "spectatorKey": spectatorKey}
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-spectator/v1/spectate/launch", data = body)).json()
                                logPrint(response)
                                if isinstance(response, dict) and "errorCode" in response:
                                    if response["httpStatus"] == 400 and response["message"] == "SpectatorPlugin_NOT_AVAILABLE":
                                        logPrint("您所在的服务器不支持玩家可观战性检测。请自行判断玩家是否可观战。\nThe server or platform you're currently on doesn't support this endpoint. Please judge by yourself whether a player is observable.")
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
                                else:
                                    time.sleep(1) #发送指令后客户端不一定马上进入英雄选择或游戏中（The client won't immediately enter the champ select or in game stage after the program posts the spectating requests）
                                    gameflow_phase = await get_gameflow_phase(connection)
                                    if gameflow_phase in {"ChampSelect", "InProgress"}:
                                        gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                                        gameModeName: str = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameflow_session["gameData"]["queue"]["id"]) if gameflow_session["gameData"]["queue"]["name"] == "" else gameflow_session["gameData"]["queue"]["name"]
                                        logPrint("启动观战成功！您正在观看%s的对局。\nLaunched spectating successfully. You'll be spectating the game of %s soon.\n对局序号（MatchId）：\t%d\n队列序号（QueueId）：\t%d\n游戏模式名称（Game mode name）：\t%s" %(spectating_summonerName, spectating_summonerName, gameflow_session["gameData"]["gameId"], gameflow_session["gameData"]["queue"]["id"], gameModeName))
                                        logPrint("观战信息如下：\nSpectate information is as follows:")
                                        spectate_body: dict[str, str] = await (await connection.request("GET", "/lol-spectator/v1/spectate")).json() #退出观战不会更新该接口的返回结果，所以只在观战成功时使用此接口（Exit spectating won't update the result this endpoint returns, so this endpoint is only used here）
                                        logPrint(spectate_body)
                                        break
                                    else:
                                        logPrint("这场对局现在不可观战。它也许已经结束了。\nThe game isn't available for spectate now. It might have ended.")
                        else:
                            logPrint(spectating_summoner_info["message"])
                    logPrint('请输入您想要观看的玩家召唤师名。输入“0”以返回上一层。\nPlease input the summonerName of the player to spectate. Submit "0" to return to the last step.')
            else:
                logPrint("您目前的状态不可观战。请等待游戏结束或者退出房间来进行观战。\nYou're not allowed to spectate for now. Please wait for the current game to end or exit the party or lobby to spectate any game.")
        elif option[0] == "5":
            await chat(connection)
        elif option[0] == "6":
            await report_player_matchHistory(connection)
        elif option[0] == "7":
            logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n3\t扩展对局记录（Expand match history）\n4\t循环测试房间创建（Test lobby creation iteratively）\n5\t调试游戏状态（Debug a gameflow phase）''')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await display_current_info(connection)
                elif suboption[0] == "2":
                    await toggle_nonfriend_game_invite(connection)
                elif suboption[0] == "3":
                    await expand_match_history(connection)
                elif suboption[0] == "4":
                    await create_queue_lobby(connection, loop_test = True)
                elif suboption[0] == "5":
                    return await debug_gameflow_phase(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n3\t扩展对局记录（Expand match history）\n4\t循环测试房间创建（Test lobby creation iteratively）\n5\t调试游戏状态（Debug a gameflow phase）''')
        elif option[0] == "8":
            await manage_ux(connection)
    return "" #返回值为空字符串，表示未调试游戏状态（An empty string returned means the user isn't debugging any gameflow phase）

#-----------------------------------------------------------------------------
# 房间内行为模拟（Lobby action simulation）
#-----------------------------------------------------------------------------
async def get_perk_page(connection: Connection) -> pandas.DataFrame:
    current_summonerId: int = current_info["summonerId"]
    perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
    perkPage_header_keys: list[str] = list(perkPage_header.keys())
    perkPage_data: dict[str, list[Any]] = {key: [] for key in perkPage_header_keys}
    for page in perkPages:
        for i in range(len(perkPage_header_keys)):
            key: str = perkPage_header_keys[i]
            if i <= 26:
                if i == 24: #上次修改时间（`lastModifiedTime`）
                    to_append: Any = getISOTime(page["lastModified"] / 1000)
                elif i == 25: #快速模式英雄名称列表（`quickPlayChampionNames`）
                    to_append = list(map(lambda x: LoLChampions[x]["name"], page["quickPlayChampionIds"]))
                elif i == 26: #推荐英雄名称（`recommendationChampionName`）
                    to_append = "" if page["recommendationChampionId"] == 0 else LoLChampions[page["recommendationChampionId"]]["name"]
                else:
                    to_append = page[key]
            elif i <= 31:
                if i == 30: #基石槽位类型（`pageKeystone slotType`）
                    to_append = slotTypes[page[key.split()[0]][key.split()[1]]]
                else:
                    to_append = page[key.split()[0]][key.split()[1]]
            else: #已选择的符文（`uiPerksNames`）
                to_append = list(map(lambda x: x["name"], page["uiPerks"]))
            perkPage_data[key].append(to_append)
    perkPage_statistics_output_order: list[int] = [2, 10, 11, 1, 3, 7, 5, 4, 8, 6, 13, 14, 12, 22, 20, 19, 28, 29, 30, 31, 27, 32, 21, 23, 24, 15, 25, 16, 26, 18]
    perkPage_data_organized: dict[str, list[Any]] = {perkPage_header_keys[i]: perkPage_data[perkPage_header_keys[i]] for i in perkPage_statistics_output_order}
    perkPage_df: pandas.DataFrame = pandas.DataFrame(data = perkPage_data_organized)
    optimize_bool_display(perkPage_df)
    perkPage_df = pandas.concat([pandas.DataFrame([perkPage_header])[perkPage_df.columns], perkPage_df], ignore_index = True)
    return perkPage_df

async def sort_social_leaderboard(connection: Connection, queueType: str, ignore_warning: bool = False) -> pandas.DataFrame:
    social_leaderboard_header_keys: list[str] = list(social_leaderboard_header.keys())
    social_leaderboard: dict[str, Any] = await (await connection.request("GET", f"/lol-social-leaderboard/v1/social-leaderboard-data?queueType={queueType}")).json()
    social_leaderboard_data: dict[str, list[Any]] = {key: [] for key in social_leaderboard_header_keys}
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
                key: str = social_leaderboard_header_keys[i]
                if i == 0: #可用性（`availability`）
                    to_append: Any = availabilities[player[key]]
                elif i == 1: #段位分级（`division`）
                    to_append = "" if player[key] == "NA" else player[key]
                elif i == 14: #段位（`tier`）
                    to_append = tiers_all[player[key]]
                elif i >= 16: #召唤师图标相关键（Summoner icon-related keys）
                    if player["profileIconId"] in summonerIcons and key.split("_")[1] in summonerIcons[player["profileIconId"]] :
                        to_append = summonerIcons[player["profileIconId"]][key.split("_")[1]]
                    else:
                        to_append = player["profileIconId"] if i == 16 else ""
                else:
                    to_append = player[key]
                social_leaderboard_data[key].append(to_append)
    social_leaderboard_statistics_output_order: list[int] = [5, 12, 2, 13, 10, 9, 7, 16, 17, 11, 4, 8, 14, 1, 6, 15, 0, 3]
    social_leaderboard_data_organized: dict[str, list[Any]] = {social_leaderboard_header_keys[i]: social_leaderboard_data[social_leaderboard_header_keys[i]] for i in social_leaderboard_statistics_output_order}
    social_leaderboard_df: pandas.DataFrame = pandas.DataFrame(data = social_leaderboard_data_organized).sort_values(by = "leaderboardPosition", ascending = True, ignore_index = True)
    optimize_bool_display(social_leaderboard_df)
    social_leaderboard_df = pandas.concat([pandas.DataFrame([social_leaderboard_header])[social_leaderboard_df.columns], social_leaderboard_df], ignore_index = True)
    return social_leaderboard_df

async def get_collection(connection: Connection, verbose: bool = True) -> pandas.DataFrame: #这部分代码根据商品藏品信息脚本改写而成（This part of code is drafted according to Customized Program 07）
    #准备数据资源（Prepare data resources）
    logPrint("[get_collection]正在准备藏品相关数据资源…… | Preparing collection-related data resources ...", print_time = True, verbose = verbose)
    championSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
    companions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
    nexusfinishers_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/nexusfinishers.json")).json()
    statstones_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/statstones.json")).json()
    strawberryHub_source: dict[str, Any] = await (await connection.request("GET", "/lol-game-data/assets/v1/strawberry-hub.json")).json()
    summonerEmotes_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-emotes.json")).json()
    summonerIcons_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    tftdamageskins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftdamageskins.json")).json()
    tftmapskins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftmapskins.json")).json()
    tftplaybooks_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftplaybooks.json")).json()
    tftzoomskins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftzoomskins.json")).json()
    wardSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    lolinventorytype_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/lolinventorytype.json")).json()
    #获取商品和藏品数据（Get store and collection data）
    logPrint("[get_collection]正在获取商品和藏品数据…… | Fetching store and collection data ...", print_time = True, verbose = verbose)
    riot_client_info: list[str] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info: dict[str, str] = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region: str = client_info["--region"]
    locale: str = client_info["--locale"]
    lolinventorytypes: dict[str, dict[str, Any]] = {x["inventoryTypeId"]: x for x in lolinventorytype_source}
    inventoryTypes: str = sorted(list(map(lambda x: x["inventoryTypeId"], lolinventorytype_source)))
    collection = await (await connection.request("GET", "/lol-inventory/v1/inventory?inventoryTypes=%s" %(json.dumps(inventoryTypes).replace(" ", "")))).json()
    catalogDicts: dict[str, list[dict[str, Any]]] = {}
    catalogList: list[dict[str, Any]] = []
    for inventoryType in inventoryTypes:
        catalogDicts[inventoryType] = await (await connection.request("GET", "/lol-catalog/v1/items/" + inventoryType)).json()
        catalogDicts[inventoryType] = sorted(catalogDicts[inventoryType], key = lambda x: x["itemId"])
        catalogList += catalogDicts[inventoryType]
    store: list[dict[str, Any]] = await (await connection.request("GET", "/lol-store/v1/catalog")).json()
    #下面定义对应关系表（The following code define the table for mapping）
    logPrint("[get_collection]建立对应关系表…… | Build the map table ...", print_time = True, verbose = verbose)
    collection_hashtable: dict[tuple[str, int], str] = {(item["inventoryType"], item["itemId"]): item["name"] for item in catalogList}
    if isinstance(store, dict) and "errorCode" in store:
        logPrint(store)
        if store["httpStatus"] == 500 and store["message"] == "Unsuccessful request to catalog: ":
            logPrint("获取商品数据的请求失败。请检查客户端连接是否正常，以及服务器是否维护。将跳过该商品数据。\nFailed to get store data. Please check the client network connection and whether the server is under maintenance. The program is going to skip store data.")
    else:
        collection_hashtable |= {(item["inventoryType"], item["itemId"]): item["localizations"][locale]["name"] for item in store if item["localizations"] != None} #原本的藏品信息中没有记录名称，所以需要借用商品信息中的名称。之所以不考虑使用识别码作为键，是因为在从`lol-store`接口获取的商品信息中，存在识别码重复的两件商品，而道具类型和道具序号的组合应当能够唯一确定一件商品。另外，从`lol-catalog`和`lol-store`接口获取的商品信息可以互相补充（The original collection information doesn't contain the names, so they're cited from the catalog information. The reason why `itemInstanceId` isn't taken as the key is that there're two items with the same `itemInstanceId` in the items obtaned from `lol-store` API. However, the combination of `inventoryType` and `itemId` should uniquely correspond to an item. Besides, item information obtained from `lol-catalog` API and that from `lol-store` API can supplement each other）
    championSkins_hashtable: dict[int, dict[str, str]] = {} #对于特定道具类型的商品，道具序号可唯一确定一件商品。下同（As for an item of specific inventory type, the itemId can uniquely correspond to that item. So can the following）
    for skin in championSkins_source.values():
        championSkins_hashtable[skin["id"]] = {"name": skin["name"], "description": skin["description"]}
        if "chromas" in skin:
            for chroma in skin["chromas"]:
                championSkins_hashtable[chroma["id"]] = {"name": chroma["name"], "description": ""}
                for desc in chroma["descriptions"]:
                    if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1:
                        championSkins_hashtable[chroma["id"]]["description"] = desc["description"]
                        break
        if "questSkinInfo" in skin:
            for tier in skin["questSkinInfo"]["tiers"]:
                championSkins_hashtable[tier["id"]] = {"name": tier["name"], "description": tier["description"]}
    companions_hashtable: dict[str, dict[str, str]] = {companion["itemId"]: {"name": companion["name"], "description": companion["description"]} for companion in companions_source}
    nexusfinishers_hashtable: dict[int, dict[str, str]] = {nexusfinisher["itemId"]: {"name": nexusfinisher["name"], "description": nexusfinisher["translatedDescription"]} for nexusfinisher in nexusfinishers_source}
    statstones_hashtable: dict[int, dict[str, str]] = {statstone["itemId"]: {"name": statstone["name"], "description": statstone["description"]} for statstone in statstones_source["packData"]}
    strawberryBoons_hashtable: dict[str, dict[str, str]] = {} #注意，PVE模式的相关索引都是识别码（Note that index of PBE mode data is itemInstanceId）
    strawberryLoadoutItems_hashtable: dict[str, dict[str, str]] = {}
    strawberryMaps_hashtable: dict[str, dict[str, str]] = {}
    for strawberryMap in strawberryHub_source[0]["MapDisplayInfoList"]:
        strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]] = {"name": strawberryMap["value"]["Name"], "description": strawberryMap["value"]["Bark"]}
    for ProgressGroup in strawberryHub_source[0]["ProgressGroups"]:
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
                                strawberryBoons_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": Property["Name"]}
                        elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                                if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                                    strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                            else:
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": Property["Name"]}
                        elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                                if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here suppose an empty dictionary has been created for this map before）
                                    strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryMaps_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                                else:
                                    strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + Property["Name"]
                            else:
                                strawberryMaps_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": Property["Name"]}
    for PowerUpGroup in strawberryHub_source[0]["PowerUpGroups"]:
        for Boon in PowerUpGroup["value"]["Boons"]:
            if Boon["value"]["ContentId"] in strawberryBoons_hashtable:
                if not "name" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] == "":
                    strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] = PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"]
                if not "description" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] == "":
                    strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] = PowerUpGroup["value"]["Description"]
            else:
                strawberryBoons_hashtable[Boon["value"]["ContentId"]] = {"name": PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"], "description": PowerUpGroup["value"]["Description"]}
    for EoGNarrativeBark in strawberryHub_source[0]["EoGNarrativeBarks"]:
        for Reward in EoGNarrativeBark["value"]["RewardGroup"]["Rewards"]:
            if all(key in Reward for key in ["Title", "Details", "ItemId", "ItemType"]) and "CapInventoryTypeId" in Reward["ItemType"]:
                if Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_BOON"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryBoons_hashtable:
                        if not "name" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["name"] == "":
                            strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryBoons_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryBoons_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": EoGNarrativeBark["value"]["RewardGroup"]["name"]}
                elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                        if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                            strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": EoGNarrativeBark["value"]["RewardGroup"]["name"]}
                elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                        if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here suppose an empty dictionary has been created for this map before）
                            strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryMaps_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                        # else: #实际上在遍历模式进程分组时已经添加过地图激活要求信息了（Actually, when traversing the ProgressGroups, the program has added information of the requirement to activate maps）
                        #     strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryMaps_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": EoGNarrativeBark["value"]["RewardGroup"]["name"]}
    summonerEmotes_hashtable: dict[int, dict[str, str]] = {emote["id"]: {"name": emote["name"], "description": emote["description"]} for emote in summonerEmotes_source}
    summonerIcons_hashtable: dict[int, dict[str, str]] = {}
    for icon in summonerIcons_source:
        summonerIcons_hashtable[icon["id"]] = {}
        summonerIcons_hashtable[icon["id"]]["name"] = icon["title"]
        for desc in icon["descriptions"]:
            if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1: #为简化代码，目前仅统计守卫（眼）在拳头大区的简介。有些简介是非空字符串，但是实际上是一堆空格（To simplify the code, only riot descriptions of wards are counted. Some descriptions are indeed non-empty strings but actually a bunch of spaces）
                summonerIcons_hashtable[icon["id"]]["description"] = desc["description"]
                break
        else:
            summonerIcons_hashtable[icon["id"]]["description"] = ""
    tftdamageskins_hashtable: dict[str, dict[str, str]] = {skin["itemId"]: {"name": skin["name"], "description": skin["description"]} for skin in tftdamageskins_source}
    tftmapskins_hashtable: dict[str, dict[str, str]] = {skin["itemId"]: {"name": skin["name"], "description": skin["description"]} for skin in tftmapskins_source}
    tftplaybooks_hashtable: dict[str, dict[str, str]] = {tftplaybook["itemId"]: {"name": tftplaybook["translatedName"], "description": tftplaybook["translatedDescription"]} for tftplaybook in tftplaybooks_source}
    tftzoomskins_hashtable: dict[str, dict[str, str]] = {tftzoomskin["itemId"]: {"name": tftzoomskin["name"], "description": tftzoomskin["description"]} for tftzoomskin in tftzoomskins_source}
    wardSkins_hashtable: dict[int, dict[str, str]] = {skin["id"]: {"name": skin["name"], "description": skin["description"]} for skin in wardSkins_source}
    ##以下类型的藏品在商品中也没有记录名称，需要借助其它接口来获取其名称（Collection items of the following types aren't recorded the names in catalog, so other APIs are required to get their names）
    titles_all: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-challenges/v2/titles/all")).json()
    titles_hashtable: dict[int, dict[str, Any]] = {title["itemId"]: {"name": title["name"], "description": title["challengeTitleData"]["challengeDescription"] if title["challengeTitleData"] != None and "challengeDescription" in title["challengeTitleData"] else ""} for title in titles_all.values()}
    regaliaBanners: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_BANNER")).json()
    regaliaBanners_hashtable: dict[int, dict[str, str]] = {int(regaliaBanners[bannerId]["items"][0]["id"]): {"name": regaliaBanners[bannerId]["items"][0]["localizedName"], "description": regaliaBanners[bannerId]["items"][0]["localizedDescription"]} for bannerId in regaliaBanners}
    regaliaCrests: dict[str, Any] = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_CREST")).json()
    hashtable_dicts: dict[str, dict[Any, dict[str, str]]] = {"CHAMPION_SKIN": championSkins_hashtable, "COMPANION": companions_hashtable, "NEXUS_FINISHER": nexusfinishers_hashtable, "STATSTONE": statstones_hashtable, "STRAWBERRY_BOON": strawberryBoons_hashtable, "STRAWBERRY_LOADOUT_ITEM": strawberryLoadoutItems_hashtable, "STRAWBERRY_MAP": strawberryMaps_hashtable, "EMOTE": summonerEmotes_hashtable, "SUMMONER_ICON": summonerIcons_hashtable, "TFT_DAMAGE_SKIN": tftdamageskins_hashtable, "TFT_MAP_SKIN": tftmapskins_hashtable, "TFT_PLAYBOOK": tftplaybooks_hashtable, "TFT_ZOOM_SKIN": tftzoomskins_hashtable, "WARD_SKIN": wardSkins_hashtable, "ACHIEVEMENT_TITLE": titles_hashtable, "REGALIA_BANNER": regaliaBanners_hashtable}
    #定义藏品数据结构（Define the collection item data structure）
    collection_header: dict[str, str] = {"expirationDate": "租赁到期时间", "f2p": "免费使用", "inventoryType": "道具类型", "itemId": "序号", "loyalty": "", "loyaltySources": "", "owned": "已拥有", "ownershipType": "拥有权", "purchaseDate": "购买时间", "quantity": "数量", "rental": "租借中", "usedInGameDate": "上次使用时间", "uuid": "唯一识别码", "wins": "使用该道具可获得增益的胜场数", "isVintage": "典藏皮肤", "name": "名称"}
    collection_header_keys: list[str] = list(collection_header.keys())
    collection_data: dict[str, list[Any]] = {key: [] for key in collection_header_keys}
    #数据整理核心部分（Data assignment - core part）
    logPrint("[get_collection]正在整理数据…… | Organizing data ...", print_time = True, verbose = verbose)
    for item_index in range(len(collection)):
        item: dict[str, Any] = collection[item_index]
        # logPrint("数据整理进度（Data organization process）：%d/%d" %(item_index + 1, len(collection)), end = "\r", print_time = True, verbose = verbose)
        for i in range(len(collection_header_keys)):
            key: str = collection_header_keys[i]
            if i in {0, 8, 11}: #时间字符串相关键（Time string-related keys）
                if item[key] == "":
                    to_append: Any = ""
                elif "-" in item[key] and ":" in item[key]:
                    to_append = "%s-%s-%s %s-%s-%s" %(item[key][:4], item[key][5:7], item[key][8:10], item[key][11:13], item[key][14:16], item[key][17:19])
                else:
                    to_append = "%s-%s-%s %s-%s-%s" %(item[key][:4], item[key][4:6], item[key][6:8], item[key][9:11], item[key][11:13], item[key][13:15])
            # elif i == 2: #道具类型（`inventoryType`）
            #     to_append = inventoryType_dict[item[key]]
            elif i == 5: #奖励计划来源（`loyaltySources`）
                to_append = item["loyaltySources"]
                if to_append == []:
                    to_append = ""
            # elif i == 7: #拥有权（`ownershipType`）
            #     to_append = ownershipTypes[item[key]]
            elif i == 14: #典藏皮肤（带边框）（`isVintage`）
                to_append = item["payload"] and "isVintage" in item["payload"] and item["payload"]["isVintage"] #没有“是否典藏”选项的默认不是典藏（An item without the "isVintage" key can't be vintage）
            elif i == 15: #名称（`name`）
                if (item["inventoryType"], item["itemId"]) in collection_hashtable:
                    name: str = collection_hashtable[(item["inventoryType"], item["itemId"])]
                elif item["inventoryType"] in hashtable_dicts: #商品中可能不包含藏品（A collection item may not be contained in the collection）
                    if item["inventoryType"] in {"STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP"} and item["uuid"] in hashtable_dicts[item["inventoryType"]]:
                        name = hashtable_dicts[item["inventoryType"]][item["uuid"]]["name"]
                    elif item["itemId"] in hashtable_dicts[item["inventoryType"]]:
                        name = hashtable_dicts[item["inventoryType"]][item["itemId"]]["name"]
                    else:
                        name = ""
                else:
                    name = ""
                to_append = name
            else:
                to_append = item[key]
            collection_data[key].append(to_append)
    #数据框列序整理（Dataframe column ordering）
    collection_statistics_output_order: list[int] = [15, 9, 3, 2, 12, 6, 10, 1, 4, 5, 7, 8, 0, 14, 13, 11]
    collection_data_organized: dict[str, list[Any]] = {collection_header_keys[i]: collection_data[collection_header_keys[i]] for i in collection_statistics_output_order}
    logPrint("[get_collection]正在构建数据框…… | Creating the dataframe ...", print_time = True, verbose = verbose)
    collection_df: pandas.DataFrame = pandas.DataFrame(data = collection_data_organized)
    logPrint("[get_collection]正在优化逻辑值显示…… | Optimizing the display of boolean values ...", print_time = True, verbose = verbose)
    optimize_bool_display(collection_df)
    collection_df = pandas.concat([pandas.DataFrame([collection_header])[collection_df.columns], collection_df], ignore_index = True)
    logPrint("[get_collection]数据框构建完成。 | Dataframe created.", print_time = True, verbose = verbose)
    return collection_df

async def sort_available_bots(connection: Connection) -> pandas.DataFrame:
    availableBot_header_keys: list[str] = list(availableBot_header.keys())
    available_bots: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")).json()
    availableBot_data: dict[str, list[Any]] = {key: [] for key in availableBot_header_keys}
    for bot in available_bots:
        for i in range(len(availableBot_header_keys)):
            key: str = availableBot_header_keys[i]
            if i <= 2:
                to_append: Any = bot[key]
            else:
                to_append = LoLChampions[bot["id"]][key] if bot["id"] in LoLChampions else ""
            collection_data[key].append(to_append)
    availableBot_statistics_output_order: list[imt] = [2, 3, 5, 4, 1]
    availableBot_data_organized: dict[str, list[Any]] = {availableBot_header_keys[i]: availableBot_data[availableBot_header_keys[i]] for i in availableBot_statistics_output_order}
    availableBot_df: pandas.DataFrame = pandas.DataFrame(data = availableBot_data_organized)
    optimize_bool_display(availableBot_df)
    availableBot_df = pandas.concat([pandas.DataFrame([availableBot_header])[availableBot_df.columns], availableBot_df], ignore_index = True)
    return availableBot_df

async def sort_lobby_members(connection: Connection) -> pandas.DataFrame:
    member_header_keys: list[str] = list(member_header.keys())
    member_data: dict[str, list[Any]] = {key: [] for key in member_header_keys}
    lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    if not (isinstance(lobby_information, dict) and "errorCode" in lobby_information):
        members: list[dict[str, Any]] = []
        humans: dict[str, Any] = {member["puuid"]: member for member in lobby_information["members"]} #房间信息的“members”键的值都是人类玩家（The value of the key "members" of `lobby_information` is composed of only human players）
        #思考下面为什么要这样处理成员顺序（Think why the members are ordered in the following pattern）
        for member in lobby_information["gameConfig"]["customTeam100"]:
            if member["puuid"] in humans:
                if not humans[member["puuid"]] in members: #这个条件实际上是多余的（This condition is actually redundant）
                    members.append(humans[member["puuid"]])
            else:
                members.append(member)
        for member in lobby_information["gameConfig"]["customTeam200"]:
            if member["puuid"] in humans:
                if not humans[member["puuid"]] in members:
                    members.append(humans[member["puuid"]])
            else:
                members.append(member)
        for member in lobby_information["members"]:
            if not member in members:
                members.append(member)
        for member in members:
            if not member["isBot"]:
                member_info_recapture: int = 0
                member_info: dict[str, Any] = await get_info(connection, member["puuid"])
                while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                    logPrint(member_info["message"])
                    member_info_recapture += 1
                    logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of member (puuid: %s) capture failed! Recapturing this member's information ... Times tried: %d" %(member["puuid"], member_info_recapture, member["puuid"], member_info_recapture))
                    member_info = await get_info(connection, member["puuid"])
                if not member_info["info_got"]:
                    logPrint(member_info["message"])
                    logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！\nInformation of member (puuid: %s) capture failed!" %(member["puuid"], member["puuid"]))
            for i in range(len(member_header_keys)):
                key: str = member_header_keys[i]
                if i >= 34 and i <= 36: #电脑玩家英雄相关键（Bot champion-related keys）
                    to_append: Any = LoLChampions[member["botChampionId"]][key.split("_")[1]] if member["botChampionId"] in LoLChampions else ""
                elif i == 37: #电脑玩家难度等级（`botDifficulty_localized`）
                    to_append = botDifficulty_dict[member["botDifficulty"]]
                elif i == 38: #电脑玩家分路（`botPosition_localized`）
                    to_append = positions[member["botPosition"]]
                elif i == 39: #首选（`primaryPosition`）
                    to_append = positions[member["firstPositionPreference"]]
                elif i == 40: #次选（`secondaryPosition`）
                    to_append = positions[member["secondPositionPreference"]]
                elif i == 41: #无尽狂潮地图名称（`strawberryMapName`）
                    to_append = strawberryMaps[member["strawberryMapId"]]["value"]["name"] if member["strawberryMapId"] in strawberryMaps else ""
                elif i in [42, 43]: #召唤师图标相关键（Summoner icon-related keys）
                    to_append = summonerIcons[member["summonerIconId"]].get(key.split("_")[1], "") if member["summonerIconId"] in summonerIcons else ""
                elif i >= 44: #召唤师信息相关键（Summoner information-related keys）
                    to_append = member_info["body"][key] if not member["isBot"] and member_info["info_got"] else ""
                else:
                    to_append = member[key]
                member_data[key].append(to_append)
    member_statistics_output_order: list[int] = [32, 30, 44, 45, 29, 22, 31, 28, 42, 43, 18, 19, 33, 15, 39, 24, 40, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 27, 16, 21, 26, 41, 23, 25, 20, 17, 10, 12, 14, 34, 36, 35, 11, 37, 13, 38]
    member_data_organized: dict[str, list[Any]] = {member_header_keys[i]: member_data[member_header_keys[i]] for i in member_statistics_output_order}
    member_df: pandas.DataFrame = pandas.DataFrame(data = member_data_organized)
    optimize_bool_display(member_df)
    member_df = pandas.concat([pandas.DataFrame([member_header])[member_df.columns], member_df], ignore_index = True)
    return member_df

async def print_search_error(connection: Connection, response: dict, lobbyInfo: dict) -> None:
    if response["httpStatus"] == 400:
        if response["message"] == "INVALID_PERMISSIONS":
            logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the party owner and thus can't perform this operation.")
        elif response["message"] == "GATEKEEPER_RESTRICTED":
            if bool(lobbyInfo["restrictions"]):
                logPrint("无法寻找对局。请检查小队限制。\nUnable to find match. Please check the party restrictions.")
                logPrint(lobbyInfo["restrictions"])
            search_state: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
            if not (isinstance(search_state, dict) and "errorCode" in search_state):
                if search_state["searchState"] in {"ServiceShutdown", "ServiceError", "Error", "AbandonedLowPriorityQueue"}:
                    logPrint(search_state)
                for error in search_state["errors"]:
                    if error["errorType"] == "QUEUE_DODGER":
                        penalty_time_remaining: float = int(error["penaltyTimeRemaining"])
                        penalizedSummoner_recapture: int = 0
                        penalizedSummoner: dict[str, Any] = await get_info(connection, error["penalizedSummonerId"])
                        while not penalizedSummoner["info_got"] and penalizedSummoner["body"]["httpStatus"] != 404 and penalizedSummoner_recapture < 3:
                            logPrint(penalizedSummoner["message"])
                            penalizedSummoner_recapture += 1
                            logPrint("小队成员信息（召唤师序号：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of a lobby member (summonerId: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(error["penalizedSummonerId"], penalizedSummoner_recapture, penalizedSummoner_recapture, error["penalizedSummonerId"]))
                            penalizedSummoner = await get_info(connection, error["penalizedSummonerId"])
                        if penalizedSummoner["info_got"]:
                            penalizedSummonerName: str = get_info_name(penalizedSummoner["body"])
                            penalty_time_remaining_text_zh: str = ""
                            penalty_time_remaining_text_en: str = ""
                            penalty_hour: int = penalty_time_remaining // 3600
                            penalty_minute: int = penalty_time_remaining % 3600 // 60
                            penalty_second: int = penalty_time_remaining % 60
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
                    penalizedSummoners: list[dict[str, Any]] = []
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
                    penalizedSummonerNames: list[str] = list(map(get_info_name, penalizedSummoners))
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
        elif response["message"] == "UNKNOWN":
            logPrint("不能进入英雄选择。由于服务器处于高限制状态，自定义游戏暂时要求有至少1个玩家才能开始。\nUnable to start champion selection. Due to high server demand, custom games temporarily require a minimum of 1 player.")
        elif response["message"] == "CHAMPION_SELECT_ALREADY_STARTED":
            logPrint("您已在英雄选择阶段内。如果您的界面异常，请重启客户端或者使用本脚本执行英雄选择动作。\nYou're already in the champ select stage. If an error occurs to your League Client, please restart the client or perform champ select actions with this program.")
        elif response["message"] == "INVALID_PLAYER_STATE":
            logPrint("所有成员都必须选好位置才能进入队列。\nAll member(s) must select their positions before entering queue.")
        elif response["message"] == "NOT_A_MATCHMADE_QUEUE":
            logPrint("当前队列不是匹配队列。\nThe current queue isn't a matchmade queue.")
        else:
            logPrint("未知错误。\nUnknown error.")
    else:
        logPrint("未知错误。\nUnknown error.")

async def lobby_simulation(connection: Connection) -> str:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t管理小队（Manage a party）\n2\t管理自定义房间（Manage a custom lobby）\n3\t邀请玩家（Invite to game）\n4\t聊天（Chat）\n5\t成员管理（Manage members）\n6\t输出房间信息（Print lobby information）\n7\t处理邀请（Handle invitations）\n8\t加入小队或自定义房间（Join party/lobby）\n9\t退出房间（Exit the party/lobby）\n10\t举报一名玩家（Report a player）\n11\t其它（Others）\n12\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option == "-1": #查看接口返回结果，用于内部调试（Check endpoint results, used for debugging）
            logPrint('''请选择一个房间相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a lobby-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t检查房间是否呈现自动补位提示（Check if the lobby displays the autofill tolltip）\n2\t设置房间是否呈现自动补位提示（Set whether the lobby displays the autofill tooltip）\n3\t退出冠军杯赛队伍（Quit a Clash party）\n4\t加入冠军杯赛队伍（Join a Clash party）\n5\t获取所有公开的自定义房间数据（Get all public custom lobby data）\n6\t获取某个公开的自定义房间数据（Get data of a public custom lobby）\n7\t加入一个公开的自定义房间（Join a public custom lobby）\n8\t刷新公开自定义房间数据（Refresh public custom lobby data）\n9\t检查当前房间是否可用（Check if the current lobby is available）\n10\t查看当前房间的倒计时（Check the current lobby's countdown）\n11\t添加一名电脑玩家（Add a bot player）\n12\t编辑一名电脑玩家的参数（Edit a bot player's parameters）\n13\t删除一名电脑玩家（Remove a bot player）\n14\t强制退出英雄选择阶段（Force to leave the champ select stage）\n15\t进入自定义对局的英雄选择阶段（Enter a custom game's champ select stage）\n16\t加入自定义房间的另外一支队伍（Join another team of a custom lobby）\n17\t查看当前房间发出的所有邀请信息（Check all invitations sent out from the current lobby）\n18\t向一名玩家发送邀请（Send an invitation to a player）\n19\t获取一个邀请信息（Get an invitation's information）\n20\t获取用户的快速模式配置（Get the user's swiftplay loadout）\n21\t设置用户的快速模式配置（Set the user's switfplay loadout）\n22\t设置用户的符文（Set the user's perks）\n23\t设置用户的首选和次选位置（Set the user's primary and secondary positions）\n24\t更改小队成员的身份（Change the role of a member in a party）\n25\t更改小队可用性（Change the availability of a party）\n26\t查看小队的游戏模式（Change the party's game mode）\n27\t批量修改小队配置（Configure party settings in batches）\n28\t获取小队成员信息（Get party member information）\n29\t更改队列游戏模式（Change a queue）\n30\t重新准备就绪（Prepare for queue entry again）\n31\t查看小队奖励（Check party rewards）\n32\t加入冠军杯赛队伍（Join a Clash party）\n33\t获取小队聊天成员信息（Get the party member information for communication）\n34\t获取小队聊天密钥（Get the token for party communication）\n35\t获取用户加入游戏队列资格验证哈希值（Get the hash value of the user's eligilbility to join the queue）\n36\t检查用户游戏队列资格初始化进度（Check the progress of lobby eligibility configuration initialization）\n37\t查看所有游戏模式的小队可用性（Check availability of parties of all game modes）\n38\t查看所有游戏模式的小队可用性（Check availability of parties of all game modes）\n39\t在对局结算阶段邀请玩家至小队（Invite players to party at the end of a game）\n40\t退出当前房间（Exit the current lobby）\n☆41\t获取当前房间信息（Get the current lobby information）\n42\t创建房间（Create a lobby）\n43\t获取当前房间可以添加的电脑玩家（Get bot champions available to add into the current lobby）\n44\t查看当前房间是否允许添加电脑玩家（Check if the current lobby allows addition of bot players）\n45\t查看当前房间发出的所有邀请信息（Check all invitations sent out from the current lobby）\n46\t邀请玩家至房间（Invite players to game）\n47\t停止寻找对局（Stop finding match）\n48\t寻找对局（Find match）\n49\t获取寻找对局状态（Get match finding state）\n50\t设置快速模式就绪状态（Toggle ready or not in swiftplay mode）\n51\t查看房间内成员信息（Check the information of members in the current lobby）\n52\t为一名小队成员提供房间邀请权限（Grant invite priviledge for a party member）\n53\t将一名成员移出房间（Kick a member out of the party）\n54\t将成员晋升为小队拥有者（Promote a member as the party owner）\n55\t撤回一名小队成员的邀请权限（Revoke invite priviledge from a party member）\n56\t设置用户的首选和次选位置（Set the user's primary and secondary positions）\n57\t设置小队可见性（Toggle party open or closed）\n58\t设置用户的快速模式配置（Set the user's switfplay loadout）\n59\t选择无尽狂潮地图（Select a strawberry map）\n60\t选择斗魂竞技场槽位（Select an Arena lobby slot）\n61\t切换队伍（Switch team）\n62\t快速寻找对局（Quickly find match）\n63\t查看房间内的通知（Check notifications in the lobby）\n64\t向房间内发送通知（Send notifications into the lobby）\n65\t移除房间内的通知（Delete a piece of notification from the lobby）\n!66\t（未知）激活阵容匹配队列重载【(Unknown) Activate game mode override for team builder queues】\n67\t检查当前队列是否可用（Check if the current party can be started）\n68\t加入一个小队（Join a party）\n69\t查看小队成员在对局结算阶段的状态（Check the status of party members at the end of a game）\n70\t再来一局（Play again）\n71\t返回大厅（Return to the home page）\n72\t查看收到的邀请（Check received invitations）\n73\t接受一个小队/房间邀请（Accept a party/lobby invitation）\n74\t拒绝一个小队/房间邀请（Decline a party/lobby invitation）\n75\t查看账号注册进度（Check account registration progress）''')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection, log = log)
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
                        clashId_str: str = logInput()
                        response = await (await connection.request("POST", "/lol-lobby/v1/clash", data = clashId_str)).json()
                    elif suboption == "5":
                        response = await (await connection.request("GET", "/lol-lobby/v1/custom-games")).json()
                    elif suboption == "6":
                        logPrint("请输入小队编号：\nPlease input the partyId:")
                        partyId: str = logInput()
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
                            body_str: str = logInput()
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
                        summonerInternalName: str = logInput()
                        logPrint("请输入要删除的电脑玩家通用唯一识别码：\nPlease input the botUuid of the bot to remove:\nbotUuidToDelete = ", end = "")
                        botUuidToDelete: str = logInput()
                        logPrint("请输入要删除的电脑玩家所在阵营代号：\nPlease input the teamId of the bot to remove:\nteamId = ", end = "")
                        teamId: str = logInput()
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
                        invitationId: str = logInput()
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
                        slotsIndex: str = logInput()
                        logPrint("请输入含有符文信息的字符串：\nPlease input a string that contains perk information:\nperksString = ", end = "")
                        perksString: str = logInput()
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
                        member_summonerId_str: str = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId_str}/grant-invite")).json()
                    elif suboption == "53":
                        logPrint("请输入房间内成员的召唤师序号：\nPlease input the summonerId of a member in the lobby:\nsummonerId", end = "")
                        member_summonerId_str = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId_str}/kick")).json()
                    elif suboption == "54":
                        logPrint("请输入房间内成员的召唤师序号：\nPlease input the summonerId of a member in the lobby:\nsummonerId", end = "")
                        member_summonerId_str = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId_str}/promote")).json()
                    elif suboption == "55":
                        logPrint("请输入房间内成员的召唤师序号：\nPlease input the summonerId of a member in the lobby:\nsummonerId", end = "")
                        member_summonerId_str = logInput()
                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId_str}/revoke-invite")).json()
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
                        teamId: str = logInput()
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
                        notificationId: str = input()
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
            gameflow_phase: str = await get_gameflow_phase(connection) #每一个操作都需要保证房间信息是可用的（Each operation requires the lobby information to be available）
            if gameflow_phase == "Lobby":
                lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                if option == "1":
                    if lobby_information["gameConfig"]["queueId"] == -1:
                        logPrint("自定义房间不支持此选项。\nCustom lobby doesn't support this option.")
                    else:
                        logPrint("请选择一个小队操作：\nPlease select a party operation:\n1\t入队准备（Prepare before in queue）\n2\t查看社交排行榜（Check friends leaderboard）\n3\t改变小队公开性（Toggle party open/closed）\n4\t更换模式（Change mode）\n5\t寻找对局（Find match）")
                        while True:
                            suboption: str = logInput()
                            if suboption == "":
                                continue
                            elif suboption[0] == "0":
                                break
                            elif suboption[0] == "1":
                                logPrint("请选择一项个人配置：\nPlease select a personal configuration to change:\n1\t选择位置（Select positions）\n2\t设置快速模式英雄选择（Configure quickplay slot）\n3\t设置子阵营（Configure subteam data）\n4\t切换就绪状态（Toggle ready）\n5\t云顶之弈赛前配置（TFT loadouts）")
                                while True:
                                    config: str = logInput()
                                    if config == "":
                                        continue
                                    elif config[0] == "0":
                                        break
                                    elif config[0] == "1":
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase == "Lobby":
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            # if lobby_information["gameConfig"]["showPositionSelector"]: #在2026赛季的自定义房间中，需要选定位置，但是房间信息的“showPositionSelector”键的值为假。因此禁用此条件筛选（In the custom lobby in Season 2026, position is required, but the value of "showPositionSelector" key in lobby information is False. Therefore, this condition is currently disabled）
                                            slotPositions: list[str] = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY", "FILL"]
                                            logPrint("请选择首选位置：\nPlease select your primary position:\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路/线上（Bottom/Lane）\n5\t辅助（Support）\n6\t补位（Fill）")
                                            back: bool = False
                                            while True:
                                                position_index: str = logInput()
                                                if position_index[0] == "0":
                                                    back = True
                                                    break
                                                elif position_index == "-1":
                                                    firstPreference: str = "UNSELECTED" #这里也可以是空字符串（An empty string also works here）
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
                                            body: dict[str, str] = {"firstPreference": firstPreference, "secondPreference": secondPreference}
                                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-lobby/v2/lobby/members/localMember/position-preferences", data = body)).json()
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
                                                    if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                        logPrint("您还未创建任何房间。请创建一个排位小队后再检查位置。\nYou're not in any lobby. Please first create a ranked party and then check the positions.")
                                                    else:
                                                        logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                else:
                                                    if lobby_information["localMember"]["firstPositionPreference"] == firstPreference and lobby_information["localMember"]["secondPositionPreference"] == secondPreference:
                                                        logPrint("位置设置成功。\nPosition configuration succeeded.")
                                                    else:
                                                        logPrint("位置设置失败。请检查小队是否支持位置选择器。\nPosition configuration failed. Please check if the current party supports position selector.")
                                            # else:
                                            #     logPrint("当前模式不支持位置选择。\nThe current mode doesn't support position selection.")
                                        else:
                                            logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                                    elif config[0] == "2":
                                        gameflow_phase = await get_gameflow_phase(connection)
                                        if gameflow_phase == "Lobby":
                                            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                            if lobby_information["gameConfig"]["showQuickPlaySlotSelection"]:
                                                skin_df_fields_to_print: list[str] = ["id", "name"]
                                                logPrint('请按照以下步骤完成英雄选择。在后续任何步骤，输入“0”以返回上一步。\nPlease follow the steps below to determine the quickplay slots. Submit "0" to return to the last step at any subsequent step.')
                                                slotId: int = 1
                                                body: dict[str, Any] = []
                                                while slotId <= 2:
                                                    if slotId == 0:
                                                        break
                                                    elif slotId == 1:
                                                        logPrint("按回车键以设置第一个英雄。\nPress Enter to set Slot 1.")
                                                        tmp: str = logInput()
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
                                                    slot_got: bool = False
                                                    step: int = 1
                                                    while step <= 5:
                                                        if step == 0:
                                                            if slotId > 1:
                                                                body.pop() #在第二步返回上一层，意味着要重新设置第一个英雄（To return to the last step of Step 2, the first slot should be reset）
                                                            slotId -= 2
                                                            break
                                                        elif step == 1:
                                                            logPrint("第一步：请选择一个英雄。\nStep 1: Please select a champion.")
                                                            LoLChampion_df, count = sort_inventory_champions(LoLChampions, recommended_position_for_champion, log = log, verbose = False)
                                                            LoLChampion_fields_to_print: list[str] = ["id", "name", "title", "alias"]
                                                            LoLChampion_df_selected: pandas.DataFrame = pandas.concat([LoLChampion_df.iloc[:1, :], LoLChampion_df[(LoLChampion_df["freeToPlay"] == "√") | (LoLChampion_df["ownership: owned"] == "√") | (LoLChampion_df["ownership: rental: rented"] == "√")]], ignore_index = True)
                                                            LoLChampion_df_query: pandas.DataFrame = LoLChampion_df.loc[:, LoLChampion_fields_to_print]
                                                            LoLChampion_df_query["id"] = LoLChampion_df["id"].astype(str) #方便检索（For convenience of retrieval）
                                                            LoLChampion_df_query = LoLChampion_df_query.map(lambda x: x.lower() if isinstance(x, str) else x)
                                                            print(format_df(LoLChampion_df_selected.loc[:, LoLChampion_fields_to_print])[0]) #虽然输出的是筛选后的表格，但实际上用户仍然可以尝试选择不可用的英雄（Although the selected table is output, users can still try choosing unavailable champions）
                                                            log.write(format_df(LoLChampion_df_selected.loc[:, LoLChampion_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                            while True:
                                                                champion_queryStr: str = logInput()
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
                                                                    query_positions = numpy.where(LoLChampion_df_query == champion_queryStr.lower()) #使用numpy.where检索的前提是数据框中每个单元格的值都不一样（The premise of query by `numpy.where` is that no two cells are the same）
                                                                    if len(query_positions[0]) == 0:
                                                                        logPrint("没有找到该英雄。请重新输入。\nChampion not found. Please try again.")
                                                                    else:
                                                                        resultRow = query_positions[0]
                                                                        result_champion_df = LoLChampion_df.loc[resultRow, LoLChampion_fields_to_print].reset_index(drop = True)
                                                                        championId = LoLChampion_df["id"][resultRow[0]]
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
                                                            available_spells: list[int] = available_spell_dict[lobby_information["gameConfig"]["gameMode"]]
                                                            for spellId in sorted(available_spells):
                                                                spell = spells[spellId]
                                                                logPrint("%d\t%s" %(spellId, spell["name"]))
                                                            logPrint("请依次输入两个召唤师技能的序号，以空格为分隔符：\nPlease input the two spellIds, split by space:")
                                                            while True:
                                                                spell_str: str = logInput()
                                                                if spell_str == "":
                                                                    continue
                                                                elif spell_str == "0":
                                                                    step -= 2
                                                                    break
                                                                elif spell_str == "0 0":
                                                                    spell1Id: int = 0
                                                                    spell2Id: int = 0
                                                                    break
                                                                else:
                                                                    selectedSpellIds: list[str] = spell_str.split()
                                                                    if len(selectedSpellIds) != 2:
                                                                        logPrint("请输入两个召唤师技能的序号！\nPlease submit two spellIds!")
                                                                    else:
                                                                        try:
                                                                            selectedSpellIds: list[int] = list(map(int, selectedSpellIds))
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
                                                            perkPage_df: pandas.DataFrame = await get_perk_page(connection)
                                                            perkPage_df_fields_to_print: list[str] = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
                                                            if len(perkPage_df) == 1:
                                                                logPrint("您还未创建任何符文页。\nYou've not created any page yet.")
                                                            else:
                                                                logPrint("您的符文页如下：\nYou perk pages are listed below:")
                                                                print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                                                                log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                            wd: str = os.getcwd()
                                                            subscript_path: str = os.path.join(wd, "Customized Program 19 - Configure Perks.py")
                                                            logPrint("是否需要修改符文页？（输入任意键以修改，否则不修改。）\nDo you want to change any page? (Submit any non-empty string to change, or null to refuse changing.)\n请确保本程序同目录下存在符文脚本，否则无法配置相关符文。\nPlease ensure the perk program is under the same directory as this program, otherwise perk configuration can't be implemented through this program.\n文件名（File name）： Customized Program 19 - Configure Perks.py\n完整路径（Complete path）： %s" %(subscript_path))
                                                            change_page_str: str = logInput()
                                                            change_page: bool = bool(change_page_str)
                                                            if change_page:
                                                                if os.path.exists(subscript_path):
                                                                    logPrint(f"正在打开（Opening）： {subscript_path}")
                                                                    subprocess.run(["python", subscript_path])
                                                                else:
                                                                    logPrint('''在同目录下未发现符文脚本。取消该操作。请自行在客户端内修改。\n"Customized Program 19 - Configure Perks.py" isn't found under the same directory. This operation is cancelled. Please change inside the League Client.''')
                                                            logPrint("输入左侧的索引以选择一个符文页。\nSelect a page index.")
                                                            perkPage_df: pandas.DataFrame = await get_perk_page(connection)
                                                            print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                                                            log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                            while True:
                                                                page_index: str = logInput()
                                                                if page_index == "":
                                                                    continue
                                                                elif page_index == "-1":
                                                                    perkStr: str = ""
                                                                    break
                                                                elif page_index == "0":
                                                                    step -= 2
                                                                    break
                                                                elif page_index in list(map(str, range(1, len(perkPage_df)))):
                                                                    page_index: int = int(page_index)
                                                                    isValid: bool = perkPage_df["isValid"][page_index] == "√"
                                                                    primaryPerkStyleName: str = perkPage_df["primaryStyleName"][page_index]
                                                                    primaryPerkStyleId: int = perkPage_df["primaryStyleId"][page_index]
                                                                    secondaryPerkStyleName: str = perkPage_df["secondaryStyleName"][page_index]
                                                                    secondaryPerkStyleId: int = perkPage_df["subStyleId"][page_index]
                                                                    keystoneId: int = perkPage_df["pageKeystone id"][page_index]
                                                                    keystoneName: str = perkPage_df["pageKeystone name"][page_index]
                                                                    perkIds: list[int] = perkPage_df["selectedPerkIds"][page_index]
                                                                    perkNames: list[str] = perkPage_df["uiPerksNames"][page_index]
                                                                    if isValid:
                                                                        logPrint("您选择了以下符文页：\nYou selected the following perk page:")
                                                                        logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
                                                                        logPrint("输入任意非空字符串以确认选择，否则重新选择。\nSubmit any non-empty string to comfirm selection, or null to select another page.")
                                                                        page_confirm_str: str = logInput()
                                                                        page_confirm: int = bool(page_confirm_str)
                                                                        if page_confirm:
                                                                            perks_param: dict[str, list[int] | int] = {"perkIds": perkIds, "perkStyle": primaryPerkStyleId, "perkSubStyle": secondaryPerkStyleId}
                                                                            perkStr = json.dumps(perks_param).replace(" ", "")
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
                                                            skin_df_selected: pandas.DataFrame = pandas.concat([skin_df.iloc[:1, :], skin_df[(skin_df["disabled"] == "") & ((skin_df["ownership owned"] == "√") | (skin_df["ownership rental rented"] == "√")) & (skin_df["championId"] == championId)]], ignore_index = True)
                                                            if len(skin_df_selected) == 1:
                                                                logPrint("无可用皮肤。将使用默认皮肤。\nThere's not any available skin. The default skin will be used.")
                                                                selectedSkinId: int = 0 if championId == -1 else championId * 1000
                                                                slot_got = True
                                                            else:
                                                                logPrint("%s的可用皮肤如下：\nPickable skins of %s are as follows:" %(LoLChampions[championId]["title"], LoLChampions[championId]["alias"]))
                                                                print(format_df(skin_df_selected.loc[:, skin_df_fields_to_print], print_index = True)[0])
                                                                log.write(format_df(skin_df_selected.loc[:, skin_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                                logPrint("请选择一个皮肤：\nPlease select a skin:")
                                                                while True:
                                                                    skin_index_str: str = logInput()
                                                                    if skin_index_str == "":
                                                                        continue
                                                                    elif skin_index_str == "-1":
                                                                        selectedSkinId = 0
                                                                        slot_got = True
                                                                        break
                                                                    elif skin_index_str == "0":
                                                                        step -= 2
                                                                        break
                                                                    elif skin_index_str in list(map(str, range(1, len(skin_df_selected)))):
                                                                        skin_index: int = int(skin_index_str)
                                                                        selectedSkinId = skin_df_selected["id"][skin_index]
                                                                        slot_got = True
                                                                        break
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        else:
                                                            logPrint("发现异常步骤！请联系开发人员检查和调试代码。\nAn unexpected step is found! Please contact the developer to check and debug the code.")
                                                            break
                                                        step += 1
                                                    if slot_got:
                                                        playerSlot: dict[str, str | int] = {"championId": championId, "perks": perkStr, "positionPreference": position, "skinId": selectedSkinId, "spell1": spell1Id, "spell2": spell2Id}
                                                        body.append(playerSlot)
                                                    slotId += 1
                                                if len(body) > 0:
                                                    logPrint(body)
                                                    response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-lobby/v1/lobby/members/localMember/player-slots", data = body)).json()
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
                                                memberSlots: list[dict[str, Any]] = []
                                                for member in lobby_information["members"]:
                                                    member_info_recapture: int = 0
                                                    member_info: dict[str, Any] = await get_info(connection, member["puuid"])
                                                    while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                                                        logPrint(member_info["message"])
                                                        member_info_recapture += 1
                                                        logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of member (puuid: %s) capture failed! Recapturing this member's information ... Times tried: %d" %(member["puuid"], member_info_recapture, member["puuid"], member_info_recapture))
                                                        member_info = await get_info(connection, member["puuid"])
                                                    if not member_info["info_got"]:
                                                        logPrint(member_info["message"])
                                                        logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！\nInformation of member (puuid: %s) capture failed!" %(member["puuid"], member["puuid"]))
                                                    memberSlot: dict[str, Any] = {"slot": (member["subteamIndex"], member["intraSubteamPosition"]), "puuid": member["puuid"], "summonerName": get_info_name(member_info["body"]) if member_info["info_got"] else "", "selfTag": "☆" if member["puuid"] == current_info["puuid"] else ""}
                                                    memberSlots.append(memberSlot)
                                                memberSlots = sorted(memberSlots, key = lambda x: x["slot"]) #将成员关于子阵营槽位排序（Sort the members according to the subteam slot order）
                                                logPrint('请依次输入您的子阵营序号和位置，以空格为分隔符：（输入“0”以返回上一层。）\nPlease enter the subteamIndex and intraSubteamPosition one by one, split by space: (Submit "0" to return to the last step.)')
                                                for memberSlot in memberSlots:
                                                    print("%s%s\t%s\t%s" %(memberSlot["selfTag"], memberSlot["slot"], memberSlot["puuid"], memberSlot["summonerName"]))
                                                logPrint("例如，如果想要恢复您现在的位置，您可以输入：\nFor example, if you want to return to your current slot, you may input:\n%d %d" %(lobby_information["localMember"]["subteamIndex"], lobby_information["localMember"]["intraSubteamPosition"]))
                                                while True:
                                                    slot_str: str = logInput()
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
                                                            body: dict[str, int] = {"subteamIndex": subteamIndex, "intraSubteamPosition": intraSubteamPosition}
                                                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-lobby/v2/lobby/subteamData", data = body)).json()
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
                                                                    if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                                        logPrint("您还未创建任何房间。请创建一个斗魂竞技场小队后再设置子阵营。\nYou're not in any lobby. Please first create a Arena party and then configure your subteam.")
                                                                    else:
                                                                        logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                                else:
                                                                    current_subteamIndex: int = lobby_information["localMember"]["subteamIndex"]
                                                                    current_intraSubteamPosition: int = lobby_information["localMember"]["intraSubteamPosition"]
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
                                            ready: bool = isinstance(lobby_information["localMember"]["memberData"], dict) and lobby_information["localMember"]["memberData"].get("isPlayerReady", "") == "true"
                                            logPrint("请选择一个操作：\nPlease select an operation:\n%s1\t准备就绪（Toggle ready）\n%s2\t取消就绪（Toggle not ready）" %("☆" if not ready else "", "☆" if ready else ""))
                                            while True:
                                                operation: str = logInput()
                                                if operation == "":
                                                    operation = "2" if ready else "1"
                                                if operation[0] == "0":
                                                    break
                                                elif operation[0] in {"1", "2"}:
                                                    body: dict[str, str] = {"isPlayerReady": "true" if operation[0] == "1" else ""}
                                                    response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-lobby/v2/lobby/memberData", data = body)).json()
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
                                                            if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
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
                                                loadout_scope: dict[str, Any] = await (await connection.request("GET", "/lol-loadouts/v4/loadouts/scope/account")).json()
                                                if isinstance(loadout_scope, dict) and "errorCode" in loadout_scope:
                                                    logPrint(loadout_scope)
                                                    logPrint("未知错误！\nUnknown error!")
                                                else:
                                                    if len(loadout_scope) == 0:
                                                        logPrint("无可用赛前配置方案。请重启英雄联盟客户端后再运行本程序。\nNo available loadouts. Please restart the League Client and then run this program.")
                                                    else:
                                                        loadoutId: str = loadout_scope[0]["id"] #因为赛前配置在每次退出英雄联盟客户端后就没了，所以随便取一个赛前配置就行。这里取了第一个列表元素（Because loadouts aren't reserved as the user exits the League Client, any loadout is OK to use. Here the first element of the loadout scope list is used）
                                                        loadoutName: str = loadout_scope[0]["name"]
                                                    collection_df_fields_to_print: list[str] = ["inventoryType", "itemId", "name", "ownershipType"]
                                                    logPrint("请选择一项赛前配置：\nPlease select a loadout:\n1\t小小英雄（Tacticians）\n2\t进攻特效（Booms）\n3\t棋盘皮肤（Arena skins）\n4\t传送门（Portals）")
                                                    while True:
                                                        loadout_option: str = logInput()
                                                        if loadout_option == "":
                                                            continue
                                                        elif loadout_option[0] == "0":
                                                            break
                                                        elif loadout_option[0] in list(map(str, range(1, 5))):
                                                            inventoryTypes: dict[str, str] = {"1": "COMPANION", "2": "TFT_DAMAGE_SKIN", "3": "TFT_MAP_SKIN", "4": "TFT_ZOOM_SKIN"}
                                                            inventoryType: str = inventoryTypes[loadout_option[0]]
                                                            collection_df_selected: pandas.DataFrame = pandas.concat([collection_df.iloc[:1, :], collection_df[collection_df["inventoryType"] == inventoryType]], ignore_index = True)
                                                            if len(collection_df_selected) == 1:
                                                                logPrint("您目前没有该类道具的使用权。\nYou don't have permissions to use any item of this inventoryType.")
                                                            else:
                                                                logPrint('请选择您想要使用的道具：（输入-1以初始化当前选择。）\nPlease select an item to use: (Submit "-1" to initialize the current choice.)')
                                                                print(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], print_index = True)[0])
                                                                log.write(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                                while True:
                                                                    index_got = False
                                                                    item_index_str: str = logInput()
                                                                    if item_index_str == "":
                                                                        continue
                                                                    elif item_index_str == "0":
                                                                        index_got = False
                                                                        break
                                                                    elif item_index_str == "-1" or item_index_str in list(map(str, range(1, len(collection_df_selected)))):
                                                                        item_index: int = int(item_index_str)
                                                                        index_got = True
                                                                        break
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                if index_got:
                                                                    contentId: str = "" if item_index == -1 else collection_df_selected["uuid"][item_index]
                                                                    itemId: int = 0 if item_index == -1 else collection_df_selected["itemId"][item_index]
                                                                    loadout_key: str = f"{inventoryType}_SLOT" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                                                    body: dict[str, Any] = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                                                    response: Optional[dict[str, Any]] = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
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
                                    queueId: int = lobby_information["gameConfig"]["queueId"]
                                    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
                                    gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_source}
                                    social_leaderboard_df_fields_to_print: list[str] = ["leaderboardPosition", "gameName", "tagLine", "tier", "division", "wins"]
                                    if queueId in gameQueues and gameQueues[queueId]["isRanked"]:
                                        queueType: str = gameQueues[queueId]["type"]
                                        if queueType in ["RANKED_TFT_DOUBLE_UP", "RANKED_TFT_PAIRS"]:
                                            logPrint("查询该游戏模式的好友排行榜会导致英雄联盟崩溃。您确定要继续吗？（输入任意键以继续，否则拒绝。）\nFetching friends leaderboard of this mode will result in a crash of League of Legends. Do you really want to continue? (Submit any non-empty string to continue, or null to take a risk.)")
                                            leaderboard_crash_continue_str: str = logInput()
                                            leaderboard_crash_continue: bool = bool(leaderboard_crash_continue_str)
                                            if leaderboard_crash_continue:
                                                social_leaderboard_df: pandas.DataFrame = await sort_social_leaderboard(connection, queueType)
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
                                        operation: str = logInput()
                                        if operation == "":
                                            operation = "1" if lobby_information["partyType"] == "open" else "2"
                                        if operation[0] == "0":
                                            break
                                        elif operation[0] in {"1", "2"}:
                                            response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-lobby/v2/lobby/partyType", data = "closed" if operation[0] == "1" else "open")).json()
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
                                                    if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
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
                                    lobby_changed: bool = await create_lobby(connection)
                                    if lobby_changed:
                                        return ""
                                else:
                                    logPrint("您目前不在房间内，或者正处于队列中或英雄选择阶段。\nYou're currently not in a party/lobby, in queue or during a champ select stage.")
                            elif suboption[0] == "5":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        await print_search_error(connection, response, lobby_information)
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
                        logPrint("请选择一个自定义房间操作：\nPlease select a lobby operation:\n1\t添加电脑玩家（Add a bot）\n2\t批量添加电脑玩家（Add bots）\n3\t移除电脑玩家（Remove bots）\n4\t交换队伍（Switch team）\n5\t更换模式（Change mode）\n6\t开始游戏（Start game）")
                        while True:
                            suboption: str = logInput()
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
                                        championId_got: bool = False
                                        botDifficulty_got: bool = False
                                        teamId_got: bool = False
                                        position_got: bool = False
                                        botUuid_got: bool = False
                                        step: int = 1
                                        while step <= 5:
                                            if step == 0:
                                                break
                                            elif step == 1:
                                                logPrint("第一步：请选择一个英雄。\nStep 1: Please select a champion.")
                                                logPrint("请选择可用电脑玩家范围：\n1\t当前房间可用电脑英雄（Available bot champions in this lobby）\n2\t所有电脑英雄（All bot champions）")
                                                while True:
                                                    championId_got = False
                                                    strategy: str = logInput()
                                                    if strategy == "":
                                                        continue
                                                    elif strategy[0] == "0":
                                                        championId_got = False
                                                        break
                                                    elif strategy[0] == "1":
                                                        gameflow_phase = await get_gameflow_phase(connection)
                                                        if gameflow_phase == "Lobby":
                                                            availableBot_df: pandas.DataFrame = await sort_available_bots(connection)
                                                            availableBot_df_fields_to_print: list[str] = ["id", "name", "title", "alias", "botDifficulties"]
                                                            if len(availableBot_df) == 1:
                                                                logPrint("当前房间无可用电脑玩家。\nThere's not any available bot player in this lobby.")
                                                            else:
                                                                print(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print])[0])
                                                                log.write(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                                logPrint("请输入您想要添加的电脑玩家英雄序号：\nPlease select a championId of the bot player you want to add:")
                                                                while True:
                                                                    championId_str: str = logInput()
                                                                    if championId_str == "":
                                                                        continue
                                                                    elif championId_str == "0":
                                                                        break
                                                                    elif championId_str in list(map(str, availableBot_df["id"][1:])):
                                                                        championId: int = int(championId_str)
                                                                        championId_got = True
                                                                        break
                                                                    elif championId_str in list(map(str, LoLChampions.keys())):
                                                                        #logPrint("您输入的英雄没有电脑模型。请重新选择一个英雄。\nThe champion you pick doesn't have a bot enabled. Please select another champion.")
                                                                        championId = int(championId_str)
                                                                        championId_got = True
                                                                        break
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        else:
                                                            logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                                                    elif strategy[0] == "2":
                                                        wd: str = os.getcwd()
                                                        excel_path: str = os.path.join(wd, "available-bots.xlsx")
                                                        if os.path.exists(excel_path):
                                                            try:
                                                                availableBot_df = pandas.read_excel(excel_path, sheet_name = "Sheet2", index_col = 0, usecols = list(range(5)))
                                                            except:
                                                                traceback_info = traceback.format_exc()
                                                                logPrint(traceback_info)
                                                                logPrint("读取可用电脑玩家工作簿的过程出现了问题。\nAn error occurred when reading the available bot workbook.")
                                                            else:
                                                                if all(i in availableBot_df.columns for i in ["id", "name", "title", "alias"]) and all(map(lambda x: isinstance(x, int), availableBot_df["id"][1:])):
                                                                    print(format_df(availableBot_df)[0])
                                                                    log.write(format_df(availableBot_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                                    logPrint("请输入您想要添加的电脑玩家英雄序号：\nPlease select a championId of the bot player you want to add:")
                                                                    while True:
                                                                        championId_str = logInput()
                                                                        if championId_str == "":
                                                                            continue
                                                                        elif championId_str == "0":
                                                                            break
                                                                        elif championId_str in list(map(str, availableBot_df["id"][1:])):
                                                                            championId = int(championId_str)
                                                                            championId_got = True
                                                                            break
                                                                        elif championId_str in list(map(str, LoLChampions.keys())):
                                                                            #logPrint("您输入的英雄没有电脑模型。请重新选择一个英雄。\nThe champion you pick doesn't have a bot enabled. Please select another champion.")
                                                                            championId = int(championId_str)
                                                                            championId_got = True
                                                                            break
                                                                        else:
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                else:
                                                                    logPrint('可用电脑玩家工作簿格式错误。请通过查英雄脚本重新导出。\nAvailable bot workbook format error. Please re-export this workbook through "Customized Program 04 - Count Champion Number.py".')
                                                        else:
                                                            logPrint('''在同目录下未发现可用电脑玩家工作簿。是否需要自行测试所有可用电脑玩家？注意，这样会导致您退出当前房间。此过程需要花费几分钟时间。（输入任意键以开始测试，否则不测试。）\n"available-bots.xlsx" isn't found under the same directory. Do you want to traverse all champions to find all bot-enabled champions? Note: This operation will cause you to leave the current lobby. This process may take several minutes. (Submit any non-empty string to start the test, or null to refuse testing.)''')
                                                            botTest_str: str = logInput()
                                                            botTest: bool = bool(botTest_str)
                                                            if botTest:
                                                                available_bot_championIds: list[int] = list((await test_bot(connection, LoLChampions))[0].keys())
                                                                LoLChampion_df, count = sort_inventory_champions(LoLChampions, recommended_position_for_champion, log = log, verbose = False)
                                                                if len(available_bot_championIds) == 0:
                                                                    logPrint("没有获取到可用的电脑玩家。\nNo available bot champions found.")
                                                                else:
                                                                    availableBot_df = pandas.concat([LoLChampion_df.iloc[:1, :], LoLChampion_df[LoLChampion_df["id"].isin(available_bot_championIds)]], ignore_index = True)
                                                                    availableBot_df_fields_to_print = ["id", "name", "title", "alias"]
                                                                    print(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print])[0])
                                                                    log.write(format_df(availableBot_df.loc[:, availableBot_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                                    logPrint("请输入您想要添加的电脑玩家英雄序号：\nPlease select a championId of the bot player you want to add:")
                                                                    while True:
                                                                        championId_str = logInput()
                                                                        if championId_str == "":
                                                                            continue
                                                                        elif championId_str == "0":
                                                                            break
                                                                        elif championId_str in list(map(str, availableBot_df["id"][1:])):
                                                                            championId = int(championId_str)
                                                                            championId_got = True
                                                                            break
                                                                        elif championId_str in list(map(str, LoLChampions.keys())):
                                                                            #logPrint("您输入的英雄没有电脑模型。请重新选择一个英雄。\nThe champion you pick doesn't have a bot enabled. Please select another champion.")
                                                                            championId = int(championId_str)
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
                                                    botDifficulty_index_str: str = logInput()
                                                    if botDifficulty_index_str == "":
                                                        continue
                                                    elif botDifficulty_index_str == "-1":
                                                        botDifficulty = "NONE"
                                                        botDifficulty_got = True
                                                        break
                                                    elif botDifficulty_index_str == "0":
                                                        botDifficulty_got = False
                                                        break
                                                    elif botDifficulty_index_str in list(map(str, range(1, 11))):
                                                        botDifficulty_index: int = int(botDifficulty_index_str)
                                                        botDifficulty = BOT_DIFFICULTY_LIST[botDifficulty_index]
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
                                                    teamId_str: str = logInput()
                                                    if teamId_str == "":
                                                        continue
                                                    elif teamId_str[0] == "0":
                                                        teamId_got = False
                                                        break
                                                    elif teamId_str in ["1", "2"]:
                                                        teamId: str = f"{teamId_str}00"
                                                        teamId_got = True
                                                        break
                                                    else:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                if not teamId_got:
                                                    step -= 2
                                            elif step == 4:
                                                candidatePositions: list[str] = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
                                                recommended_position_for_champion: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
                                                recommended_lanes: dict[str, bool] = {}
                                                for position_iter in candidatePositions:
                                                    recommended_lanes[position_iter] = position_iter in recommended_position_for_champion[str(championId)]["recommendedPositions"]
                                                logPrint("第四步：请选择电脑玩家分路。\nStep 4: Please select a position for this bot player.\n%s1\t上路（Top）\n%s2\t打野（Jungle）\n%s3\t中路（Middle）\n%s4\t下路（Bottom）\n%s5\t辅助（Support）" %("☆" if recommended_lanes["TOP"] else "", "☆" if recommended_lanes["JUNGLE"] else "", "☆" if recommended_lanes["MIDDLE"] else "", "☆" if recommended_lanes["BOTTOM"] else "", "☆" if recommended_lanes["UTILITY"] else "", ))
                                                while True:
                                                    position_got = False
                                                    position_index_str: str = logInput()
                                                    if position_index_str == "":
                                                        continue
                                                    elif position_index_str[0] == "0":
                                                        position_got = False
                                                        break
                                                    elif position_index_str[0] in list(map(str, range(1, 6))):
                                                        position_index: int = int(position_index_str[0])
                                                        position: str = candidatePositions[position_index - 1]
                                                        position_got = True
                                                        break
                                                    else:
                                                        break
                                                if not position_got:
                                                    step -= 2
                                            elif step == 5:
                                                logPrint("第五步：指定电脑玩家通用唯一识别码。\nStep 5: Specify the bot uuid.")
                                                logPrint('是否随机生成电脑玩家通用唯一识别码？（输入任意键以自行指定，否则随机生成。输入“0”以返回上一步。）\nDo you want a random bot uuid? (Submit any non-empty string to manually specify the bot uuid, or null to randomize it. Submit "0" to return to the last step.)')
                                                botUuid_strategy: str = logInput()
                                                botUuid_got = botUuid_strategy != "0"
                                                botUuid_randomize: bool = botUuid_got and not bool(botUuid_strategy)
                                                if botUuid_got:
                                                    if botUuid_randomize:
                                                        botUuid: str = str(uuid.uuid4())
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
                                            body: dict[str, int | str] = {"championId": championId, "botDifficulty": botDifficulty, "teamId": teamId, "position": position, "botUuid": botUuid}
                                            logPrint(body)
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = body)).json()
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
                                                    if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                        logPrint("您还未创建任何房间。请创建一个自定义房间后再添加电脑玩家。\nYou're not in any lobby. Please first create a custom lobby and then add a bot player.")
                                                    else:
                                                        logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    break
                                                else:
                                                    bot_added: bool = False
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
                                if gameflow_phase == "Lobby" or gameflow_phase == "ChampSelect":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if lobby_information["localMember"]["isLeader"]:
                                        if os.path.exists("available-bots.xlsx"):
                                            await add_bots_team(connection, teamId = "100")
                                            await add_bots_team(connection, teamId = "200")
                                        else:
                                            logPrint("未在同目录下发现可用电脑玩家工作簿。请使用查英雄脚本生成该工作簿。\nAvailable bot workbook isn't found under the same directory. Please generate it through Customized Program 04.")
                                    else:
                                        logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the lobby owner and thus can't perform this operation.")
                                else:
                                    logPrint("您目前不在房间内。\nYou're currently not in a lobby.")
                            elif suboption[0] == "3":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby" or gameflow_phase == "ChampSelect":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if lobby_information["localMember"]["isLeader"]:
                                        member_df: pandas.DataFrame = await sort_lobby_members(connection)
                                        member_df_fields_to_print: list[str] = ["teamId", "botChampionId", "botChampion_name", "botChampion_alias", "botPosition", "botDifficulty", "botUuid"]
                                        member_df_selected: pandas.DataFrame = pandas.concat([member_df.iloc[:1, :], member_df[member_df["isBot"] == "√"]], ignore_index = True)
                                        if len(member_df_selected) == 1:
                                            logPrint("房间内无任何电脑玩家。\nThere's not any bot player in this lobby.")
                                        else:
                                            logPrint("房间内的电脑玩家如下：\nBot players in the lobby are as follows:")
                                            print(format_df(member_df_selected.loc[:, member_df_fields_to_print], print_index = True)[0])
                                            log.write(format_df(member_df_selected.loc[:, member_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                            logPrint("请选择您想要删除的电脑玩家：\nPlease select the bot players you want to remove:")
                                            while True:
                                                index_got = False
                                                bot_index_str: str = logInput()
                                                bot_indices: list[int] = []
                                                if bot_index_str == "":
                                                    continue
                                                elif bot_index_str[0] == "0":
                                                    break
                                                elif bot_index_str == "all":
                                                    bot_indices = list(range(1, len(member_df_selected)))
                                                    index_got = True
                                                    break
                                                else:
                                                    try:
                                                        tmp = eval(bot_index_str)
                                                    except:
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    else:
                                                        if isinstance(tmp, int):
                                                            if tmp >= 1 and tmp < len(member_df_selected):
                                                                bot_indices = [tmp]
                                                                index_got = True
                                                                break
                                                            else:
                                                                logPrint("请输入一个小于%d的正整数。\nPlease input a positive integer less than %d." %(len(member_df_selected), len(member_df_selected)))
                                                        elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int), tmp)):
                                                            if all(map(lambda x: x >= 1 and x < len(member_df_selected), tmp)):
                                                                bot_indices = sorted(set(tmp))
                                                                index_got = True
                                                                break
                                                            else:
                                                                logPrint("请输入小于%d的正整数。\nPlease input positive integers less than %d." %(len(member_df_selected), len(member_df_selected)))
                                                        else:
                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            if index_got:
                                                for bot_index in bot_indices:
                                                    summonerInternalName: str = member_df_selected["botId"][bot_index]
                                                    botUuidToDelete: str = member_df_selected["botUuid"][bot_index]
                                                    botTeamId: str = member_df_selected["teamId"][bot_index]
                                                    botChampion_name: str = member_df_selected["botChampion_name"][bot_index]
                                                    botChampion_alias: str = member_df_selected["botChampion_alias"][bot_index]
                                                    response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/lol-lobby/v1/lobby/custom/bots/{summonerInternalName}/{botUuidToDelete}/{botTeamId}")).json()
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
                                                        break
                                                    else:
                                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                                        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                        if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                            logPrint(lobby_information)
                                                            if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                                logPrint("您还未创建任何房间。请创建一个自定义房间后再尝试删除电脑玩家。\nYou're not in any lobby. Please first create a custom lobby and then try deleting bot players.")
                                                            else:
                                                                logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                            break
                                                        else:
                                                            current_botUuids = set(map(lambda x: x["botUuid"], lobby_information["gameConfig"]["customTeam100"] + lobby_information["gameConfig"]["customTeam200"] + lobby_information["members"]))
                                                            if botUuidToDelete in current_botUuids:
                                                                logPrint("删除%s失败。\nFailed to remove bot %s (%s)." %(botChampion_name, botChampion_alias, botUuidToDelete))
                                                            else:
                                                                logPrint("删除%s成功。\nSuccessfully removed bot %s (%s)."%(botChampion_name, botChampion_alias, botUuidToDelete))
                                    else:
                                        logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the lobby owner and thus can't perform this operation.")
                                else:
                                    logPrint("您目前不在房间内。\nYou're currently not in a lobby.")
                            elif suboption[0] == "4":
                                gameflow_phase = await get_gameflow_phase(connection) #每一个操作都需要保证房间信息是可用的（Each operation requires the lobby information to be available）
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    currentTeam: str = "SPECTATOR" if lobby_information["localMember"]["isSpectator"] else "TEAM1" if current_info["puuid"] in list(map(lambda x: x["puuid"], lobby_information["gameConfig"]["customTeam100"])) else "TEAM2" if current_info["puuid"] in list(map(lambda x: x["puuid"], lobby_information["gameConfig"]["customTeam200"])) else "UNKNOWN"
                                    team1_highlight: bool = (currentTeam == "SPECTATOR" or currentTeam == "TEAM2") and len(lobby_information["gameConfig"]["customTeam100"]) < lobby_information["gameConfig"]["maxTeamSize"]
                                    team2_highlight: bool = currentTeam == "TEAM1" and len(lobby_information["gameConfig"]["customTeam200"]) < lobby_information["gameConfig"]["maxTeamSize"]
                                    logPrint("请选择您想要加入的队伍：\nPlease select a team to join:\n%s1\t队伍1（TEAM1）\n%s2\t队伍2（TEAM2）\n3\t观战者（SPECTATOR）" %("☆" if team1_highlight else "", "☆" if team2_highlight else ""))
                                    while True:
                                        switch_team: bool = False
                                        team_option: str = logInput()
                                        if team_option == "":
                                            if team1_highlight:
                                                targetTeam: str = "TEAM1"
                                                switch_team = True
                                                break
                                            elif team2_highlight:
                                                targetTeam = "TEAM2"
                                                switch_team = True
                                                break
                                            else:
                                                continue
                                        elif team_option[0] == "0":
                                            break
                                        elif team_option[0] in list(map(str, range(1, 4))):
                                            targetTeam = "TEAM1" if team_option[0] == "1" else "TEAM2" if team_option[0] == "2" else "SPECTATOR"
                                            switch_team = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    if switch_team:
                                        if lobby_information["gameConfig"]["isCustom"] and lobby_information["multiUserChatId"].endswith("-team-select"): #旧版本自定义房间接口的特征（A feature of the old custom lobby API）
                                            if targetTeam == "SPECTATOR":
                                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/switch-teams?team=spectator")).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["httpStatus"] == 500:
                                                        if response["message"] == "NOT_SUPPORTED":
                                                            logPrint("当前游戏状态或者接口版本不支持此操作。\nYour current gameflow phase or API version don't support this operation.")
                                                        elif response["message"] == "Failed to switch to observer: Error response for POST /lol-login/v1/session/invoke: LCDS invoke to gameService.switchPlayerToObserverV2 failed: Server.Processing, com.riotgames.platform.messaging.UnexpectedServiceException : Last player in game cannot switch to observer!":
                                                            logPrint("在自定义游戏没有其他玩家的情况下你无法观战。\nYou cannot become a spectator if there are no other players in this custom game.")
                                                        else:
                                                            logPrint("未知错误。\nUnknown error.")
                                                    elif response["httpStatus"] == 400 and response["message"] == "TEAM_SIZE_LIMIT":
                                                        logPrint("观战人数已满。\nSpectator number has reached the limit.")
                                                    else:
                                                        logPrint("观战失败。\nSpectate failed.")
                                                else:
                                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                    if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                        logPrint(lobby_information)
                                                        if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                            logPrint("您还未创建任何房间。请创建一个自定义房间后再更换队伍。\nYou're not in any lobby. Please first create a custom lobby and then switch the team.")
                                                        else:
                                                            logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    else:
                                                        if current_info["puuid"] in set(map(lambda x: x["puuid"], lobby_information["gameConfig"]["customSpectators"])):
                                                            logPrint("您已成为观战者。\nYou're now a spectator.")
                                                        else:
                                                            logPrint("观战失败。\nSpectate failed.")
                                            else:
                                                preTeamId: str = lobby_information["localMember"]["teamId"]
                                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/switch-teams")).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["httpStatus"] == 500:
                                                        if response["message"] == "NOT_SUPPORTED":
                                                            logPrint("当前游戏状态或者接口版本不支持此操作。\nYour current gameflow phase or API version don't support this operation.")
                                                        elif response["message"] == "Failed to switch team: Error response for POST /lol-login/v1/session/invoke: LCDS invoke to gameService.switchTeamsV2 failed: Server.Processing, com.riotgames.platform.game.InvalidGameStateException : null":
                                                            logPrint("您已在英雄选择阶段。\nYou're already during a champ select stage.")
                                                        elif response["message"] == "Couldn't switch team, invalid team argument":
                                                            logPrint("您目前正在观战。请尝试加入一个队伍再使用此操作。\nYou're now a spectator. Please join a team before using this operation.")
                                                        else:
                                                            logPrint("未知错误。\nUnknown error.")
                                                    else:
                                                        logPrint("未知错误。\nUnknown error.")
                                                else:
                                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                    if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                        logPrint(lobby_information)
                                                        if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                            logPrint("您还未创建任何房间。请创建一个自定义房间后再更换队伍。\nYou're not in any lobby. Please first create a custom lobby and then switch the team.")
                                                        else:
                                                            logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                    else:
                                                        postTeamId: str = lobby_information["localMember"]["teamId"]
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
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/lobby/team/{targetTeam}")).json()
                                            logPrint(response)
                                            if isinstance(response, dict) and "errorCode" in response:
                                                if response["httpStatus"] == 400:
                                                    if response["message"] == "INVALID_REQUEST":
                                                        logPrint("请求无效！请确保您目前正在自定义房间内。\nInvalid request! Please make sure you're in a custom lobby now.")
                                                    elif response["message"] == "TEAM_SIZE_LIMIT":
                                                        logPrint("更换队伍失败。请检查%s是否满员。\nTeam switch failed. Please check if %s is full." %("队伍1" if targetTeam == "TEAM1" else "队伍2" if targetTeam == "TEAM2" else "观战者队伍", "TEAM 1" if targetTeam == "TEAM1" else "TEAM 2" if targetTeam == "TEAM2" else "the SPECTATORS team"))
                                                    else:
                                                        logPrint("未知错误。\nUnknown error.")
                                                elif response["httpStatus"] == 500:
                                                    if response["message"] == "INVALID_LOBBY":
                                                        logPrint("房间类型不正确。\nIncorrect lobby type.")
                                                    else:
                                                        logPrint("未知错误。\nUnknown error.")
                                                else:
                                                    logPrint("未知错误。\nUnknown error.")
                                            else:
                                                time.sleep(GLOBAL_RESPONSE_LAG)
                                                lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                                if isinstance(lobby_information, dict) and "errorCode" in lobby_information:
                                                    logPrint(lobby_information)
                                                    if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
                                                        logPrint("您还未创建任何房间。请创建一个自定义房间后再更换队伍。\nYou're not in any lobby. Please first create a custom lobby and then switch the team.")
                                                    else:
                                                        logPrint("您的房间状态出现未知异常。\nAn unknown error occurred to your lobby status.")
                                                else:
                                                    if targetTeam == "TEAM1" and current_info["puuid"] in set(map(lambda x: x["puuid"], lobby_information["gameConfig"]["customTeam100"])) or targetTeam == "TEAM2" and current_info["puuid"] in set(map(lambda x: x["puuid"], lobby_information["gameConfig"]["customTeam200"])) or targetTeam == "SPECTATOR" and current_info["puuid"] in set(map(lambda x: x["puuid"], lobby_information["gameConfig"]["customSpectators"])):
                                                        logPrint("您已加入%s。\nYou joined %s." %("队伍1" if targetTeam == "TEAM1" else "队伍2" if targetTeam == "TEAM2" else "观战者队伍", "TEAM 1" if targetTeam == "TEAM1" else "TEAM 2" if targetTeam == "TEAM2" else "the SPECTATORS team"))
                                                    else:
                                                        logPrint("更换队伍失败。请检查%s是否满员，或者等待一段时间再观察是否更换成功。\nTeam switch failed. Please check if %s is full, or wait a moment to see if this switch will succeed." %("队伍1" if targetTeam == "TEAM1" else "队伍2" if targetTeam == "TEAM2" else "观战者队伍", "TEAM 1" if targetTeam == "TEAM1" else "TEAM 2" if targetTeam == "TEAM2" else "the SPECTATORS team"))
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                            elif suboption[0] == "5": #自定义房间内没有更换模式的按钮，一旦通过鼠标点击退出房间，后续再创建新房间时，房间内就只会有自己一个人。但是在不退出原房间的情况下，房主在通过接口创建一个新的自定义房间时，旧房间的玩家会收到邀请，可视为更换模式（In the custom lobby, there's not a button to change the mode, so once the user exits the lobby by clicking the button and then creates a lobby, there'll be only the user itself in the new lobby. However, without exiting the old lobby, if the party owner creates a new custom lobby through the lobby creating endpoint, each player in the old lobby will receive an invitation, and for that reason this part may resemble "Change Mode"）
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    lobby_changed: bool = await create_lobby(connection)
                                    if lobby_changed:
                                        return ""
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                            elif suboption[0] == "6":
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "Lobby":
                                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if lobby_information["localMember"]["isLeader"]:
                                        if lobby_information["gameConfig"]["isCustom"] and lobby_information["multiUserChatId"].endswith("-team-select"):
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/start-champ-select")).json()
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
                                                    return ""
                                                else:
                                                    logPrint("游戏开始失败。\nGame failed to start.")
                                        else:
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                                            logPrint(response)
                                            if isinstance(response, dict) and "errorCode" in response:
                                                await print_search_error(connection, response, lobby_information)
                                            else:
                                                time.sleep(GLOBAL_RESPONSE_LAG)
                                                gameflow_phase = await get_gameflow_phase(connection)
                                                if gameflow_phase == "ChampSelect":
                                                    logPrint("您已进入英雄选择阶段。\nYou entered the champ select stage.")
                                                    return ""
                                                else:
                                                    logPrint("进入英雄选择阶段失败。\nYou failed to enter the champ select stage.")
                                    else:
                                        logPrint("你不是对局的拥有者，无法执行此操作。\nYou're not the party owner and thus can't perform this operation.")
                                else:
                                    logPrint("您目前不在房间内，或者正处于英雄选择阶段。\nYou're currently not in a lobby, or during a champ select stage.")
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            logPrint("请选择一个自定义房间操作：\nPlease select a lobby operation:\n1\t添加电脑玩家（Add a bot）\n2\t批量添加电脑玩家（Add bots）\n3\t移除电脑玩家（Remove bots）\n4\t交换队伍（Switch team）\n5\t更换模式（Change mode）\n6\t开始游戏（Start game）")
                    else:
                        logPrint("小队不支持此选项。\nParty doesn't support this option.")
                elif option == "3": #相比聊天脚本，这里设计的很简约。因为本脚本所要实现的目的是实现每个接口的用法，不追求在此基础上对输入输出做进一步的优化。换句话说，聊天脚本中的对应功能可视为此处的一个升级版（Compared with the similar function in Customized Program 16, the design here is fairly simple. This is because this program only aims at implementing each endpoint, but not optimize I/O further. In other words, the corresponding function in Customized Program 16 may be regarded as an upgraded version of here）
                    lobbyMember_summonerIds: list[int] = list(map(lambda x: x["summonerId"], lobby_information["members"]))
                    logPrint('请输入您想要邀请的玩家的召唤师名。输入“-1”以退出。\nPlease submit the summoner name of the player you want to invite. Submit "-1" to exit.')
                    while True:
                        invite_str: str = logInput()
                        if invite_str == "":
                            continue
                        elif invite_str == "-1":
                            break
                        else:
                            invitee_info: dict[str, Any] = await get_info(connection, invite_str)
                            if invitee_info["info_got"]:
                                if invitee_info["selfInfo"]:
                                    logPrint("你不能邀请你自己，亲～\nYou can't invite yourself, silly xD")
                                else:
                                    invitee_summonerName: str = get_info_name(invitee_info["body"])
                                    invitee_summonerId: int = invitee_info["body"]["summonerId"]
                                    if invitee_summonerId in lobbyMember_summonerIds:
                                        logPrint(f"{invitee_summonerName}已在房间内。\n{invitee_summonerName} is already in the lobby.")
                                    else:
                                        body: list[dict[str, int]] = [{"toSummonerId": invitee_summonerId}]
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby/invitations", data = body)).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            logPrint("邀请失败。\nFailed to send the invitation.")
                                        else:
                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                            lobby_invitations: dict[str, Any] | list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/lobby/invitations")).json()
                                            if isinstance(lobby_invitations, dict) and "errorCode" in lobby_invitations:
                                                if lobby_invitations["httpStatus"] == 404 and lobby_invitations["message"] == "LOBBY_NOT_FOUND":
                                                    logPrint("您已离开房间。\nYou've left the original lobby.")
                                                    break
                                            else:
                                                accepted_invitations: list[dict[str, Any]] = filter(lambda x: x["state"] == "Accepted", lobby_invitations)
                                                pending_invitations: list[dict[str, Any]] = filter(lambda x: x["state"] == "Pending", lobby_invitations)
                                                accepted_summonerIds: list[str] = list(map(lambda x: x["toSummonerId"], accepted_invitations))
                                                pending_summonerIds: list[str] = list(map(lambda x: x["toSummonerId"], pending_invitations))
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
                        member_df: pandas.DataFrame = await sort_lobby_members(connection)
                        member_df_fields_to_print: list[str] = ["gameName", "tagLine", "summonerLevel", "summonerIcon_title"]
                        member_df_selected: pandas.DataFrame = pandas.concat([member_df.iloc[:1, :], member_df[member_df["isBot"] == ""]], ignore_index = True)
                        if len(member_df_selected) == 2:
                            logPrint("当前房间内无其它人类成员。\nThere's not any other human member in this party/lobby.")
                        else:
                            logPrint("当前房间内的人类玩家如下：\nHuman players in this lobby are as follows:")
                            print(format_df(member_df_selected.loc[:, member_df_fields_to_print], print_index = True)[0])
                            log.write(format_df(member_df_selected.loc[:, member_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                            logPrint("请选择一名成员：\nPlease select a member:")
                            while True:
                                index_got = False
                                member_index_str: str = logInput()
                                if member_index_str == "":
                                    continue
                                elif member_index_str == "0":
                                    index_got = False
                                    break
                                elif member_index_str in list(map(str, range(1, len(member_df_selected)))):
                                    member_index: int = int(member_index_str)
                                    index_got = True
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if index_got:
                                    member_summonerId: int = member_df_selected["summonerId"][member_index]
                                    member_summonerName: str = member_df_selected["gameName"][member_index] + "#" + member_df_selected["tagLine"][member_index]
                                    logPrint(f"您选择了{member_summonerName}.\nYou selected {member_summonerName}.")
                                    logPrint("请选择一项操作：\nPlease select an operation:\n0\t返回上一层（Return to the last step）\n1\t晋升为小队拥有者（Promote to party owner）\n2\t将玩家移出小队（Kick player from party）\n3\t更改邀请权限（Change invite priviledge）")
                                    while True:
                                        operation: str = logInput()
                                        if operation == "":
                                            continue
                                        elif operation[0] == "0":
                                            break
                                        elif operation[0] == "1":
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/promote")).json()
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
                                                    if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
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
                                            logPrint(f"你真的想移出{member_summonerName}吗？（输入任意非空字符串以移出，否则取消操作。）\nDo you really want to kick {member_summonerName}? (Submit any non-empty string to kick, or null to cancel.)")
                                            kick_confirm_str: str = logInput()
                                            kick_confirm: bool = bool(kick_confirm_str)
                                            if kick_confirm:
                                                response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/kick")).json()
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
                                                        if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
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
                                                suboperation: str = logInput()
                                                if suboperation == "":
                                                    continue
                                                elif suboperation[0] == "0":
                                                    break
                                                elif suboperation[0] == "1":
                                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/grant-invite")).json()
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
                                                            if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
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
                                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{member_summonerId}/grant-invite")).json()
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
                                                            if lobby_information["httpStatus"] == 404 and lobby_information["message"] == "LOBBY_NOT_FOUND":
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
                                    member_df = await sort_lobby_members(connection)
                                    member_df_fields_to_print = ["gameName", "tagLine", "summonerLevel", "summonerIcon_title"]
                                    member_df_selected = pandas.concat([member_df.iloc[:1, :], member_df[member_df["isBot"] == ""]], ignore_index = True)
                                    logPrint("当前房间内的人类玩家如下：\nHuman players in this lobby are as follows:")
                                    print(format_df(member_df_selected.loc[:, member_df_fields_to_print], print_index = True)[0])
                                    log.write(format_df(member_df_selected.loc[:, member_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                    logPrint("请选择一名成员：\nPlease select a member:")
                    else:
                        logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the party/lobby owner and thus can't perform this operation.")
                elif option == "9":
                    response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/lol-lobby/v2/lobby")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        logPrint("退出房间失败。\nExit failed.")
                    else:
                        time.sleep(GLOBAL_RESPONSE_LAG)
                        gameflow_phase = await get_gameflow_phase(connection)
                        if gameflow_phase == "None":
                            logPrint("您已成功退出房间。\nYou've exited the lobby successfully.")
                            break
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
            lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            logPrint(lobby_information)
            with open("lobby-information.json", "w", encoding = "utf-8") as fp:
                json.dump(lobby_information, fp, indent = 4, ensure_ascii = False)
            logPrint('房间信息已导出到同目录下的“lobby-information.json”。\nLobby information has been exported into "lobby-information.json" under the same directory.')
        elif option == "7":
            await handle_invitations(connection)
        elif option == "8":
            lobby_changed: bool = await join_game(connection)
            if lobby_changed:
                break
        elif option == "10":
            await report_player_matchHistory(connection)
        elif option == "11":
            logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n3\t扩展对局记录（Expand match history）\n4\t循环测试房间创建（Test lobby creation iteratively）\n5\t调试游戏状态（Debug a gameflow phase）\n6\t输出并复制小队编号（Output and copy the partyId）''')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await display_current_info(connection)
                elif suboption[0] == "2":
                    await toggle_nonfriend_game_invite(connection)
                elif suboption[0] == "3":
                    await expand_match_history(connection)
                elif suboption[0] == "4":
                    await create_queue_lobby(connection, loop_test = True)
                elif suboption[0] == "5":
                    return await debug_gameflow_phase(connection)
                elif suboption[0] == "6":
                    currentParty: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
                    partyId: str = currentParty["currentParty"]["partyId"]
                    logPrint(f"当前小队编号（Current partyId）： {partyId}")
                    try:
                        pyperclip.copy(partyId)
                    except Exception as e:
                        traceback_info = traceback.format_exc()
                        logPrint(traceback_info)
                        logPrint("复制失败！\nCopy ERROR!")
                    else:
                        logPrint("小队编号已复制到剪贴板。\nPartyId has been copied to clipboard.")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n3\t扩展对局记录（Expand match history）\n4\t循环测试房间创建（Test lobby creation iteratively）\n5\t调试游戏状态（Debug a gameflow phase）\n6\t输出并复制小队编号（Output and copy the partyId）''')
        elif option == "12":
            await manage_ux(connection)
    return ""

#-----------------------------------------------------------------------------
# 队列阶段模拟（In-queue stage simulation）
#-----------------------------------------------------------------------------
async def inQueue_simulation(connection: Connection) -> str:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t输出寻找对局信息（Print matchmaking information）\n2\t聊天（Chat）\n3\t处理邀请（Handle invitations）\n4\t加入小队或自定义房间（Join party/lobby）\n5\t退出队列（Quit the queue）\n6\t举报一名玩家（Report a player）\n7\t其它（Others）\n8\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('''请选择一个寻找对局相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a matchmaking-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n1\t查看就位确认信息（Check ready-check information）\n2\t接受对局（Accept the match）\n3\t拒绝对局（Decline the match）\n4\t退出对局寻找（Exit finding match）\n5\t查看寻找对局过程（Check the process of finding match）\n6\t（无效）寻找对局（(Invalid) Find match）\n!7\t强制修改对局寻找信息（Force to change matchmaking search information）\n8\t查看寻找对局过程中的错误（Check errors during the matchmaking phase）\n9\t查看一条寻找对局过程中的错误（Check an error during the matchmaking phase）''')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection, log = log)
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
                            body_str: str = logInput()
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
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase in ["Matchmaking", "ReadyCheck"]:
                matchmaking_information: dict[str, Any] = await (await connection.request("GET", "/lol-matchmaking/v1/search")).json()
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
            lobby_changed: bool = await join_game(connection)
            if lobby_changed:
                break
        elif option[0] == "5":
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase == "Matchmaking":
                response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/lol-lobby/v2/lobby/matchmaking/search")).json()
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
            await report_player_matchHistory(connection)
        elif option[0] == "7":
            logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n3\t扩展对局记录（Expand match history）\n4\t调试游戏状态（Debug a gameflow phase）''')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await display_current_info(connection)
                elif suboption[0] == "2":
                    await toggle_nonfriend_game_invite(connection)
                elif suboption[0] == "3":
                    await expand_match_history(connection)
                elif suboption[0] == "4":
                    return await debug_gameflow_phase(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t更改“只接受好友邀请”选项（Toggle "allow game invites only from friends"）\n3\t扩展对局记录（Expand match history）\n4\t调试游戏状态（Debug a gameflow phase）''')
        elif option[0] == "8":
            await manage_ux(connection)
    return ""

#-----------------------------------------------------------------------------
# 就位确认阶段模拟（Match accept stage simulation）
#-----------------------------------------------------------------------------
async def readyCheck_simulation(connection: Connection) -> str:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t接受（Accept）\n2\t拒绝（Decline）\n3\t输出就位确认阶段信息（Print the ready check information）\n4\t其它（Others）\n5\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] in list(map(str, range(1, 4))):
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase == "ReadyCheck":
                if option[0] == "1":
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-matchmaking/v1/ready-check/accept")).json()
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
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-matchmaking/v1/ready-check/decline")).json()
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
                            if readyCheck_information["playerResponse"] == "Declined" or readyCheck_information["playerResponse"] == "None":
                                logPrint("拒绝对局成功。\nMatch declined successfully.")
                            else:
                                logPrint("拒绝对局失败。\nFailed to decline ready check.")
                else:
                    readyCheck_information: dict[str, Any] = await (await connection.request("GET", "/lol-matchmaking/v1/ready-check")).json()
                    logPrint(readyCheck_information)
                    with open("readyCheck.json", "w", encoding = "utf-8") as fp:
                        json.dump(readyCheck_information, fp, indent = 4, ensure_ascii = False)
                    logPrint('就位确认信息已导出到同目录下的“readyCheck.json”。\nReady check information has been exported into "readyCheck.json" under the same directory.')
            else:
                logPrint("您目前不在就位确认阶段。\nYou're currently not at the ready check stage.")
        elif option[0] == "4":
            logPrint("请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）")
            while True:
                suboption: str = logInput()
                if suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await display_current_info(connection)
                elif suboption[0] == "2":
                    return await debug_gameflow_phase(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）")
        elif option[0] == "5":
            await manage_ux(connection)
    return ""

#-----------------------------------------------------------------------------
# 英雄选择阶段模拟（Champ select stage simulation）
#-----------------------------------------------------------------------------
async def sort_grid_champions(connection: Connection) -> pandas.DataFrame:
    grid_champions: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champ-select/v1/all-grid-champions")).json()
    grid_champion_header_keys: list[str] = list(grid_champion_header.keys())
    grid_champion_data: dict[str, list[Any]] = {key: [] for key in grid_champion_header_keys}
    for champion in grid_champions:
        for i in range(len(grid_champion_header_keys)):
            key: str = grid_champion_header_keys[i]
            if i <= 17:
                if i >= 13: #最爱位置相关键（`positionsFavorited`-related keys）
                    to_append: Any = key.split("_")[1].lower() in list(map(lambda x: x.lower(), champion["positionsFavorited"]))
                else:
                    to_append = champion[key]
            else:
                to_append = champion["selectionStatus"][key]
            grid_champion_data[key].append(to_append)
    grid_champion_statistics_output_order: list[int] = [3, 7, 5, 6, 8, 10, 4, 12, 1, 2, 0, 9, 13, 14, 15, 16, 17, 11, 18, 19, 20, 21, 22, 23, 24, 25]
    grid_champion_data_organized: dict[str, list[Any]] = {grid_champion_header_keys[i]: grid_champion_data[grid_champion_header_keys[i]] for i in grid_champion_statistics_output_order}
    grid_champion_df: pandas.DataFrame = pandas.DataFrame(data = grid_champion_data_organized)
    optimize_bool_display(grid_champion_df)
    grid_champion_df = pandas.concat([pandas.DataFrame([grid_champion_header])[grid_champion_df.columns], grid_champion_df], ignore_index = True)
    return grid_champion_df

async def sort_swaps_info(connection: Connection, swap_typeId: int) -> pandas.DataFrame:
    champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
    swap_types: dict[int, str] = {1: "pickOrderSwaps", 2: "positionSwaps", 3: "trades"}
    swaps: list[dict[str, Any]] = sorted(champ_select_session[swap_types[swap_typeId]], key = lambda x: x["cellId"])
    swap_header: dict[str, str] = {"cellId": "槽位序号", "id": "交换代码", "state": "可交换性"}
    swap_header_keys: list[str] = list(swap_header.keys())
    swap_data: dict[str, list[Any]] = {key: [] for key in swap_header_keys}
    for swap in swaps:
        for i in range(len(swap_header_keys)):
            key: str = swap_header_keys[i]
            to_append: Any = swap[key]
            swap_data[key].append(to_append)
    swap_statistics_output_order: list[int] = [1, 0, 2]
    swap_data_organized: dict[str, list[Any]] = {swap_header_keys[i]: swap_data[swap_header_keys[i]] for i in swap_statistics_output_order}
    swap_df: pandas.DataFrame = pandas.DataFrame(data = swap_data_organized)
    swap_df = pandas.concat([pandas.DataFrame([swap_header])[swap_df.columns], swap_df], ignore_index = True)
    #下面将玩家信息附加到数据框右侧（The following code appends player information to the right of the dataframe）
    player_df: pandas.DataFrame = await sort_ChampSelect_players(connection, LoLChampions, championSkins, spells, wardSkins, playerMode = 2, log = log) #默认交换动作只能发生在队友之间。这是因为在极地大乱斗中，双方的槽位序号竟然是相同的（By default, swaps should happen among teammates. Another thing worth mentioning is that in the champ select session of an ARAM game, both teams' cellIds are the same）
    merged_df: pandas.DataFrame = pandas.merge(swap_df, player_df, how = "inner", on = "cellId")
    return merged_df

async def sort_skin_data(connection: Connection, verbose: bool = True) -> pandas.DataFrame:
    logPrint("[sort_skin_data]正在获取英雄和皮肤数据…… | Preparing champion and skin data ...", print_time = True, verbose = verbose)
    LoLChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
    LoLChampions: dict[int, dict[str, Any]] = {champion["id"]: champion for champion in LoLChampions_source}
    skins_flat: dict[int, dict[str, Any]] = {}
    for champion in LoLChampions_source:
        for skin in champion["skins"]:
            skins_flat[skin["id"]] = skin
            for chroma in skin["chromas"]:
                skins_flat[chroma["id"]] = chroma
            for tier in skin["questSkinInfo"]["tiers"]:
                if not tier["id"] in skins_flat: #圣堂皮肤和终极皮肤中的系列与主皮肤存在重复的序号（There're redundant ids between the tier and the parent ultimate skin）
                    skins_flat[tier["id"]] = tier
    #静态皮肤数据的定义代码放在数据资源导入函数中（Static skin data related code are put under `prepare_data_resources` function）
    skin_header_keys: list[str] = list(skin_header.keys())
    skin_data: dict[str, list[Any]] = {key: [] for key in skin_header_keys}
    logPrint("[sort_skin_data]正在整理数据…… | Organizing data ...", print_time = True, verbose = verbose)
    skinIds: list[int] = sorted(set(championSkins.keys()) & set(skins_flat.keys())) #在2025年8月15日，美测服在`/lol-champions/v1/inventories/{summonerId}/champions`接口中删除了德邦总管 赵信及其所有皮肤信息，导致下面出现键错误。考虑到当天有玩家反馈无法选用赵信，所以这里取`championSkins`和`skins_flat`的键的交集（On Aug. 15th, 2025, Xin Zhao is removed from the response body of the endpoint `lol-champions/v1/inventories/{summonerId}/champions`. Considering some player reported that Xin Zhao can't be selected on that day, here we take the intersection of the keys of `championSkins` and `skins_flat`）
    for skin_index in range(len(skinIds)):
        skinId: int = skinIds[skin_index]
        # logPrint("数据整理进度（Data organization process）：%d/%d" %(skin_index + 1, len(skinIds)), end = "\r", print_time = True, verbose = verbose)
        skin: dict[str, Any] = championSkins[skinId]
        skin_flat: dict[str, Any] = skins_flat[skinId]
        for i in range(len(skin_header_keys)):
            key: str = skin_header_keys[i]
            if i <= 40: #来自（From）：`/lol-game-data/assets/v1/skins.json`
                if i <= 28:
                    if i == 15: #品质（`rarity`）
                        to_append: Any = krarities[skin[key]] if key in skin else ""
                    elif i == 20: #皮肤类别（`skinClassification`）
                        to_append = skinClassifications[skin[key]] if key in skin else ""
                    elif i == 22: #皮肤套装（`skinLines`）
                        to_append = "" if not key in skin or skin[key] == None else list(map(lambda x: skinlines[x["id"]]["name"], skin[key]))
                    else:
                        to_append = skin.get(key, False if i in [8, 9] else "")
                elif i <= 32: #标志相关键（Emblem-related keys）
                    if not "emblems" in skin or skin["emblems"] == None:
                        to_append = ""
                    else:
                        if i <= 30:
                            to_append = skin["emblems"][0][key.split("_")[1]]
                        else:
                            to_append = skin["emblems"][0]["emblemPath"][key.split("_")[1]]
                else: #任务皮肤信息相关键（QuestSkinInfo-related keys）
                    to_append = skin[key.split()[0]][key.split()[1]] if key.split()[0] in skin else ""
            else: #来自（From）：`/lol-champions/v1/inventories/{summonerId}/champions`
                if i <= 47:
                    if i >= 45: #英雄相关键（Champion-related keys）
                        to_append = LoLChampions[skin_flat["championId"]][key.split("_")[1]] if "championId" in skin_flat and skin_flat["championId"] in LoLChampions else ""
                    else:
                        to_append = skin_flat.get(key, False if i in [42, 43, 44] else "")
                elif i <= 50: #拥有权相关键（Ownership-related keys）
                    to_append = skin_flat[key.split()[0]][key.split()[1]]
                else: #租借相关键（Rental-related keys）
                    if i >= 55: #日期相关键（Date-related keys）
                        timestamp = skin_flat["ownership"]["rental"]["endDate"] if i == 55 else skin_flat["ownership"]["rental"]["purchaseDate"]
                        to_append = "" if timestamp == 0 else "∞" if timestamp == 18446744073709550616 else getISOTime(timestamp / 1000)
                    else:
                        to_append = skin_flat[key.split()[0]][key.split()[1]][key.split()[2]]
            skin_data[key].append(to_append)
    skin_statistics_output_order: list[int] = [7, 12, 18, 41, 45, 46, 47, 42, 4, 5, 6, 21, 19, 8, 43, 23, 20, 22, 9, 15, 17, 14, 49, 48, 50, 53, 52, 56, 51, 55, 54, 44, 36, 37, 34, 35, 39, 38, 40, 33, 27, 10, 11, 24, 28, 25, 13, 0, 1, 3, 2, 16, 26, 29, 30, 32, 31]
    skin_data_organized: dict[str, list[Any]] = {skin_header_keys[i]: skin_data[skin_header_keys[i]] for i in skin_statistics_output_order}
    logPrint("[sort_skin_data]正在构建数据框…… | Creating the dataframe ...", print_time = True, verbose = verbose)
    skin_df: pandas.DataFrame = pandas.DataFrame(data = skin_data_organized)
    logPrint("[sort_skin_data]正在优化逻辑值显示…… | Optimizing the display of boolean values ...", print_time = True, verbose = verbose)
    optimize_bool_display(skin_df)
    skin_df = pandas.concat([pandas.DataFrame([skin_header])[skin_df.columns], skin_df], ignore_index = True)
    logPrint("[sort_skin_data]数据框构建完成。 | Dataframe created.", print_time = True, verbose = verbose)
    return skin_df

async def sort_mutedPlayers_chat(connection: Connection) -> pandas.DataFrame:
    muted_players: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
    chat_mutedPlayer_header_keys: list[str] = list(chat_mutedPlayer_header.keys())
    muted_player_data: dict[str, list[Any]] = {key: [] for key in chat_mutedPlayer_header_keys}
    for player in muted_players:
        player_info_recapture: int = 0
        player_info: dict[str, Any] = await get_info(connection, player["puuid"])
        while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
            logPrint(player_info["message"])
            player_info_recapture += 1
            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture))
            player_info = await get_info(connection, player["puuid"])
        if not player_info["info_got"]:
            logPrint(player_info["message"])
            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) capture failed!" %(player["puuid"], player["puuid"]))
        for i in range(len(chat_mutedPlayer_header_keys)):
            key: str = chat_mutedPlayer_header_keys[i]
            if i <= 3:
                to_append: Any = player[key]
            else:
                to_append = player_info["body"][key] if player_info["info_got"] else ""
            muted_player_data[key].append(to_append)
    muted_player_statistics_output_order: list[int] = [4, 5, 0, 1, 2, 3]
    muted_player_data_organized: dict[str, list[Any]] = {chat_mutedPlayer_header_keys[i]: muted_player_data[chat_mutedPlayer_header_keys[i]] for i in muted_player_statistics_output_order}
    muted_player_df: pandas.DataFrame = pandas.DataFrame(data = muted_player_data_organized)
    muted_player_df = pandas.concat([pandas.DataFrame([chat_mutedPlayer_header])[muted_player_df.columns], muted_player_df], ignore_index = True)
    return muted_player_df

async def champ_select_simulation(connection: Connection) -> str:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t交换（Swap）\n2\t英雄选择（Select a champion）\n3\t准备赛前配置（Prepare loadouts）\n4\t静音玩家（Mute players）\n5\t聊天（Chat）\n6\t举报一名玩家（Report a player）\n7\t其它（Others）\n8\t输出英雄选择会话（Output the champ select session）\n9\t客户端任务管理（Manage the League Client task）")
        option = logInput()
        if option == "":
            pass
        elif option == "-1": #查看接口返回结果，用于内部调试（Check endpoint results, used for debugging）
            logPrint('请选择一个英雄选择相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a champ select-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t查看所有网格化英雄信息（Check all grid champions）\n2\t查看所有可禁用的英雄（Check all bannable championIds）\n3\t启动训练场（Launch battle training）\n4\t查看当前选用的英雄序号（Check the current picked championId）\n5\t查看服务器禁用的英雄序号（Check ids of champions disabled serverside）\n6\t查看某个英雄的网格化信息（Check the grid information of one champion）\n7\t查看静音玩家信息（Check muted player information）\n8\t查看正在进行的英雄交换（Check the ongoing champion swap）\n9\t取消正在进行的英雄交换（Cancel the ongoing champion swap）\n10\t查看正在进行的选用顺序交换（Check the ongoing pick order swap）\n11\t取消正在进行的选用顺序交换（Cancel the ongoing pick order swap）\n12\t查看正在进行的分路交换（Check the ongoing position swap）\n13\t取消正在进行的分路交换（Cancel the ongoing position swap）\n14\t查看所有可选用的英雄序号（Check all pickable championIds）\n15\t查看所有可选用的皮肤序号（Check all pickable skinIds）\n16\t查看槽位信息（Check cell information）\n17\t重新获取英雄选择数据（Retrieve champ select data）\n☆18\t获取英雄选择会话（Get champ select session）\n19\t执行英雄选择动作（Perform an action during champ select stage）\n20\t完成英雄选择动作（Complete an action during champ select stage）\n21\t换用可用英雄池的英雄（Take a champion from the bench）\n22\t获取可用英雄交换信息（Get all champion swap information）\n23\t获取某个英雄交换信息（Get some champion swap information）\n24\t接受一个英雄交换请求（Accept a champion swap request）\n25\t忽略一个英雄交换请求（Neglect a champion swap request）\n26\t拒绝一个英雄交换请求（Decline a champion swap request）\n27\t发送一个英雄交换请求（Send a champion swap request）\n28\t获取赛前配置信息（Get loadout information）\n29\t修改赛前配置信息（Change loadout information）\n30\t发送重随请求（Send a reroll request）\n31\t获取可用选用顺序交换信息（Get all pick order swap information）\n32\t获取某个选用顺序交换信息（Get some pick order swap information）\n33\t接受一个选用顺序交换请求（Accept a pick order swap request）\n34\t忽略一个选用顺序交换请求（Cancel a pick order swap request）\n35\t拒绝一个选用顺序交换请求（Decline a pick order swap request）\n36\t发送一个选用顺序交换请求（Send a pick order swap request）\n37\t获取可用分路交换信息（Get all position swap information）\n38\t获取某个分路交换信息（Get some position swap information）\n39\t接受一个分路交换请求（Accept a position swap request）\n40\t忽略一个分路交换请求（Cancel a position swap request）\n41\t拒绝一个分路交换请求（Decline a position swap request）\n42\t发送一个分路交换请求（Send a position swap request）\n43\t获取当前会话计时器（Get the current session timer）\n44\t获取音效通知（Get sound effect notifications）\n45\t查看当前皮肤轮盘（Check skins on the current carousel）\n46\t查看已选用的皮肤信息（Check skin selector information）\n47\t查看某个槽位的玩家信息（Check information of a player on some slot）\n48\t查看全队战斗加成状态（Check battle boost status）\n49\t激活全队战斗加成（Enable battle boost）\n50\t切换最爱英雄（Toggle favorite champions）\n51\t切换玩家静音状态（Toggle player mute status）')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection, log = log)
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
                        championId_str: str = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/grid-champions/{championId_str}")).json()
                    elif suboption == "7":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                    elif suboption == "8":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/ongoing-champion-swap")).json()
                    elif suboption == "9":
                        logPrint("请输入当前正在进行的英雄交换行为的序号：\nPlease input the id of the ongoing champion swap action:")
                        swap_id_str: str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/ongoing-champion-swap/{swap_id_str}/clear")).json()
                    elif suboption == "10":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/ongoing-pick-order-swap")).json()
                    elif suboption == "11":
                        logPrint("请输入当前正在进行的选用顺序交换行为的序号：\nPlease input the id of the ongoing pick order swap action:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/ongoing-pick-order-swap/{swap_id_str}/clear")).json()
                    elif suboption == "12":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/ongoing-position-swap")).json()
                    elif suboption == "13":
                        logPrint("请输入当前正在进行的分路交换行为的序号：\nPlease input the id of the ongoing position swap action:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/ongoing-position-swap/{swap_id_str}/clear")).json()
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
                            body_str: str = logInput()
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
                        championId_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/bench/swap/{championId_str}")).json()
                    elif suboption == "22":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session/champion-swaps")).json()
                    elif suboption == "23":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/session/champion-swaps/{swap_id_str}")).json()
                    elif suboption == "24":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id_str}/accept")).json()
                    elif suboption == "25":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id_str}/cancel")).json()
                    elif suboption == "26":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id_str}/decline")).json()
                    elif suboption == "27":
                        logPrint("请输入一个英雄交换序号：\nPlease input a champion swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/champion-swaps/{swap_id_str}/request")).json()
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
                        swap_id_str = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id_str}")).json()
                    elif suboption == "33":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id_str}/accept")).json()
                    elif suboption == "34":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id_str}/cancel")).json()
                    elif suboption == "35":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id_str}/decline")).json()
                    elif suboption == "36":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/pick-order-swaps/{swap_id_str}/request")).json()
                    elif suboption == "37":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/session/position-swaps")).json()
                    elif suboption == "38":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id_str}/accept")).json()
                    elif suboption == "39":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id_str}/cancel")).json()
                    elif suboption == "40":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id_str}/decline")).json()
                    elif suboption == "41":
                        logPrint("请输入一个选用顺序交换序号：\nPlease input a pick order swap id:")
                        swap_id_str = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/session/position-swaps/{swap_id_str}/request")).json()
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
                        slotId_str: str = logInput()
                        response = await (await connection.request("GET", f"/lol-champ-select/v1/summoners/{slotId_str}")).json()
                    elif suboption == "48":
                        response = await (await connection.request("GET", "/lol-champ-select/v1/team-boost")).json()
                    elif suboption == "49":
                        response = await (await connection.request("POST", "/lol-champ-select/v1/team-boost/purchase")).json()
                    elif suboption == "50":
                        logPrint("请输入英雄序号：\nPlease input a championId:")
                        championId_str = logInput()
                        logPrint('请输入分路：\nPlease input a position:\n取值范围（Available values）：\n["top", "jungle", "middle", "bottom", "support"]')
                        position = logInput()
                        response = await (await connection.request("POST", f"/lol-champ-select/v1/toggle-favorite/{championId_str}/{position}")).json()
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
            tooltip1_zh: dict[str, str] = {"1": "选用顺序", "2": "分路", "3": "英雄"}
            tooltip1_en_lowercase: dict[str, str] = {"1": "pick order", "2": "position", "3": "champion"}
            tooltip1_en_capitalize: dict[str, str] = {key: value.capitalize() for (key, value) in tooltip1_en_lowercase.items()}
            session_keys: dict[str, str] = {"1": "pickOrderSwaps", "2": "positionSwaps", "3": "trades"}
            endpoint1_dict1: dict[str, str] = {"1": "pick-order", "2": "position", "3": "champion"}
            tooltip2_zh: dict[str, str] = {"1": "接受", "2": "拒绝", "3": "取消"}
            tooltip2_en_noun_capitalize: dict[str, str] = {"1": "Acceptation", "2": "Decline", "3": "Cancellation"}
            tooltip2_en_verb_perfect_capitalize: dict[str, str] = {"1": "Accepted", "2": "Declined", "3": "Cancelled"}
            endpoint1_dict2: dict[str, str] = {"1": "accept", "2": "decline", "3": "cancel"}
            logPrint("请选择交换对象：\nPlease select an object to swap:\n1\t选用顺序（Pick order）\n2\t分路（Position）\n3\t队友英雄（Ally champions）\n4\t可用英雄池（替补席）【Available champion pool (Bench)】")
            while True:
                obj: str = logInput()
                if obj == "":
                    continue
                elif obj[0] == "0":
                    break
                elif obj[0] in {"1", "2", "3"}:
                    logPrint("请选择动作：\nPlease select an action:\n1\t查看（Check）\n2\t发送（Send）")
                    while True:
                        action: str = logInput()
                        if action == "":
                            continue
                        elif action[0] == "0":
                            break
                        elif action[0] == "1":
                            gameflow_phase: str = await get_gameflow_phase(connection) #每一个操作都需要保证英雄选择会话是可用的（Each operation requires the champ select session to be available）
                            if gameflow_phase == "ChampSelect":
                                champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
                                swaps: dict[str, Any] = champ_select_session[session_keys[obj[0]]]
                                swap_cellId_map: dict[int, dict[str, Any]] = {swap["cellId"]: swap for swap in swaps}
                                player_df: pandas.DataFrame = await sort_ChampSelect_players(connection, LoLChampions, championSkins, spells, wardSkins, playerMode = 1, log = log)
                                player_df_fields_to_print: list[str] = ["cellId", "gameName", "tagLine", "playerAlias", "assignedPosition", "champion name", "champion alias"]
                                target_cellId: int = -1
                                for swap in swaps:
                                    if swap["state"] == "SENT" or swap["state"] == "RECEIVED": #以前可以通过/lol-champ-select/v1/ongoing-%s-swap接口来查看正在进行的交换（Previously, one could check the on-going swap by the endpoint `/lol-champ-select/v1/ongoing-%s-swap`）
                                        target_cellId = swap["cellId"]
                                        break #一次只检查一个交换请求。并且一般情况下，最多只允许一个交换请求同时存在（One swap request to check at a time. And in normal cases, there's at most one swap request simultaneously）
                                if target_cellId == -1:
                                    logPrint("在当前英雄选择会话中没有找到任何正在进行的%s交换请求。\nThere's not any on-going %s swap in the current champ select session." %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                else:
                                    ongoing_swap: dict[str, Any] = swap_cellId_map[target_cellId]
                                    swap_id: int = ongoing_swap["id"]
                                    player_df_selected: bool = player_df[player_df["cellId"] == target_cellId]
                                    print(format_df(player_df_selected.loc[:, player_df_fields_to_print], print_index = False)[0])
                                    log.write(format_df(player_df_selected.loc[:, player_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = False)[0] + "\n")
                                    if ongoing_swap["state"] == "SENT":
                                        logPrint("是否取消该交换请求？（输入任意键以取消，否则不取消。）\nDo you want to cancel this swap request? (Submit any non-empty string to cancel, or null to refuse cancelling.)")
                                        clear_str: str = logInput()
                                        clear: bool = bool(clear_str)
                                        if clear:
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/%s-swaps/%d/cancel" %(endpoint1_dict1[obj[0]], swap_id))).json()
                                            logPrint(response)
                                            if isinstance(response, dict) and "errorCode" in response: #本脚本中，大部分反馈都用了`isinstance(response, dict) and "errorCode" in response`作为请求成功与否的判断标准。这是因为如果要知道每个接口在请求成功时具体返回什么信息，必须在实战中测定。但是实际上不需要知道具体返回什么信息（In this program, the feedback parts use `isinstance(response, dict) and "errorCode" in response` as the criterion to judge whether a request is successfully post. This is because, one can only know what exactly a champ select endpoint returns in practical matches. But actually, that exact information isn't necessary）
                                                logPrint("取消失败！\nCancellation failed!")
                                            else:
                                                logPrint("已取消%s交换请求。\nCancelled current %s swap." %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                    else:
                                        logPrint("请选择处理方式：\nPlease select how you'd like to deal with this swap:\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）\n3\t取消（Cancel）")
                                        while True:
                                            strategy: str = logInput()
                                            if strategy == "":
                                                continue
                                            elif strategy[0] == "0":
                                                pass
                                            elif strategy[0] in {"1", "2", "3"}:
                                                if champ_select_session["isLegacyChampSelect"]:
                                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/%s-swaps/%d/%s" %(endpoint1_dict1[obj[0]], swap_id, endpoint1_dict2[strategy[0]]))).json()
                                                else:
                                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/%s-swaps/%d/%s" %(endpoint1_dict1[obj[0]], swap_id, endpoint1_dict2[strategy[0]]))).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    logPrint("%s失败！\n%s failed!" %(tooltip2_zh[strategy[0]], tooltip2_en_noun_capitalize[strategy[0]]))
                                                else:
                                                    logPrint("已%s%s交换请求。\n%s current %s swap." %(tooltip2_zh[strategy[0]], tooltip1_zh[obj[0]], tooltip2_en_verb_perfect_capitalize[strategy[0]], tooltip1_en_lowercase[obj[0]]))
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            break
                            else:
                                logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                        elif action[0] == "2":
                            gameflow_phase = await get_gameflow_phase(connection)
                            if gameflow_phase == "ChampSelect":
                                champ_select_session = await get_champ_select_session(connection)
                                swaps: list[dict[str, Any]] = champ_select_session[session_keys[obj[0]]]
                                if len(swaps) == 0:
                                    logPrint("%s交换不可用。请切换游戏模式后再试。\n%s swap isn't available. Please switch to another game mode and try again." %(tooltip1_zh[obj[0]], tooltip1_en_capitalize[obj[0]]))
                                elif any(map(lambda x: x["state"] == "AVAILABLE", swaps)):
                                    swap_df: pandas.DataFrame = await sort_swaps_info(connection, swap_typeId = int(obj[0]))
                                    swap_df_fields_to_print: list[str] = ["id", "cellId", "gameName", "tagLine", "assignedPosition", "champion name", "champion alias"]
                                    swap_df_selected: pandas.DataFrame = pandas.concat([swap_df.iloc[:1, :], swap_df[swap_df["state"] == "AVAILABLE"]], ignore_index = True)
                                    logPrint("请选择一名玩家以交换%s：\nPlease select a player to swap %s:" %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                    print(format_df(swap_df_selected.loc[:, swap_df_fields_to_print], print_index = True)[0])
                                    log.write(format_df(swap_df_selected.loc[:, swap_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0])
                                    while True:
                                        index_got: bool = False
                                        swap_index_str: str = logInput()
                                        if swap_index_str == "":
                                            continue
                                        elif swap_index_str == "0":
                                            break
                                        elif swap_index_str in list(map(str, range(1, len(swap_df_selected)))):
                                            swap_index: int = int(swap_index_str)
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    if index_got:
                                        # logPrint("是否确认与以下玩家交换%s？（输入任意键确认，否则取消。）\nDo you want to swap %s with the following player? (Submit any non-empty string to confirm, or null to cancel.)" %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
                                        # print(format_df(swap_df_selected.loc[[swap_index], swap_df_fields_to_print], print_index = True, reserve_index = True)[0])
                                        # log.write(format_df(swap_df_selected.loc[[swap_index], swap_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0])
                                        # swap_confirm_str: str = logInput()
                                        # swap_confirm: bool = bool(swap_confirm_str)
                                        # if swap_confirm:
                                        swap_id: int = swap_df_selected["id"][swap_index]
                                        if champ_select_session["isLegacyChampSelect"]:
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/%s-swaps/%d/request" %(endpoint1_dict1[obj[0]], swap_id))).json()
                                        else:
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/%s-swaps/%d/request" %(endpoint1_dict1[obj[0]], swap_id))).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            logPrint("交换%s的请求发送失败。\n%s swap request failed to be sent." %(tooltip1_zh[obj[0]], tooltip1_en_capitalize[obj[0]]))
                                        else:
                                            logPrint("交换%s的请求发送成功。请等待对方回应。\n%s swap request is sent successfully. Please wait for response." %(tooltip1_zh[obj[0]], tooltip1_en_capitalize[obj[0]]))
                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                            localPlayer: dict[str, Any] = await get_champSelect_player(connection)
                                            if localPlayer != {}:
                                                logPrint("当前槽位序号（Current cell id）：%d" %(localPlayer["cellId"]))
                                else:
                                    if any(map(lambda x: x["state"] == "RECEIVED" or x["state"] == "SENT", swaps)):
                                        logPrint("您正在和一名玩家交换%s。请先完成该交换后再尝试发起下一次交换。\nYou're currently swapping %s with a player. Please finish this swap and then trying initiating another swap." %(tooltip1_zh[obj[0]], tooltip1_en_lowercase[obj[0]]))
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
                        champ_select_session = await get_champ_select_session(connection)
                        if champ_select_session["benchEnabled"]:
                            benchedChampionIds: list[int] = list(map(lambda x: x["championId"], champ_select_session["benchChampions"]))
                            if len(benchedChampionIds) == 0:
                                logPrint("还没有人重随过。\nNobody has rerolled.")
                            else:
                                logPrint("可用英雄池如下：\nAvailable champion pool:")
                                LoLChampion_df, count = sort_inventory_champions(LoLChampions, recommended_position_for_champion, log = log, verbose = False)
                                LoLChampion_df_fields_to_print: list[str] = ["id", "name", "title", "alias", "freeToPlay", "ownership: owned", "ownership: rental: rented"]
                                LoLChampion_df_selected: pandas.DataFrame = pandas.concat([LoLChampion_df.iloc[:1, :], LoLChampion_df[LoLChampion_df["id"].isin(benchedChampionIds)]], ignore_index = True)
                                print(format_df(LoLChampion_df_selected.loc[:, LoLChampion_df_fields_to_print], print_index = True)[0])
                                log.write(format_df(LoLChampion_df_selected.loc[:, LoLChampion_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                logPrint("请选择一个英雄：\nPlease select a champion:")
                                while True:
                                    index_got: bool = False
                                    swap_index_str = logInput()
                                    if swap_index_str == "":
                                        continue
                                    elif swap_index_str[0] == "0":
                                        index_got = False
                                        break
                                    elif swap_index_str in list(map(str, range(1, len(LoLChampion_df_selected)))):
                                        swap_index: int = int(swap_index_str)
                                        index_got = True
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if index_got:
                                    logPrint("您选择交换以下英雄：\nYou selected the following champion to swap:")
                                    print(format_df(LoLChampion_df_selected.loc[[swap_index], LoLChampion_df_fields_to_print], print_index = True, reserve_index = True)[0])
                                    log.write(format_df(LoLChampion_df_selected.loc[[swap_index], LoLChampion_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                    swap_championId: int = LoLChampion_df_selected["id"][swap_index]
                                    swap_championName: str = LoLChampion_df_selected["name"][swap_index]
                                    if champ_select_session["isLegacyChampSelect"]:
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-champ-select/v1/session/bench/swap/{swap_championId}")).json()
                                    else:
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby-team-builder/champ-select/v1/session/bench/swap/{swap_championId}")).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        if response["httpStatus"] == 500 and response["message"] == f"Unable to swap with ChampionBench champion {swap_championId}: Received status Error: INVALID_CHAMP_SELECTION instead of expected status of OK from request to teambuilder-draft:championBenchSwapV1":
                                            logPrint(f"您目前尚未持有{swap_championName}。\nYou don't own {swap_championName} for now.")
                                        else:
                                            logPrint("交换失败。\nSwap failed.")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        localPlayer = await get_champSelect_player(connection)
                                        if localPlayer == {}:
                                            logPrint("游戏状态异常。\nAbnormal gameflow phase.")
                                        else:
                                            if localPlayer["championId"] == swap_championId:
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
            logPrint("请选择行为类型：\nPlease select an action:\n1\t禁用（Ban）\n2\t选择（Pick）\n3\t重随（Reroll）\n4\t投票（Vote）")
            while True:
                action: str = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] in {"1", "2", "4"}:
                    gameflow_phase: str = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
                        action_type: str = "ban" if action[0] == "1" else "pick" if action[0] == "2" else "vote"
                        if action_type == "ban":
                            if champ_select_session["isLegacyChampSelect"]:
                                selectable_champion_ids: list[int] = await (await connection.request("GET", "/lol-champ-select/v1/bannable-champion-ids")).json()
                            else:
                                selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/bannable-champion-ids")).json()
                        else:
                            if champ_select_session["allowSubsetChampionPicks"]:
                                selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/subset-champion-list")).json()
                            else:
                                if champ_select_session["isLegacyChampSelect"]:
                                    selectable_champion_ids = await (await connection.request("GET", "/lol-champ-select/v1/pickable-champion-ids")).json()
                                else:
                                    selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/pickable-champion-ids")).json()
                        logPrint("请输入英雄序号：\nPlease enter a champion id:") #这部分代码复制于符文脚本（This part of code is copied from Customized Program 19）
                        LoLChampion_df, count = sort_inventory_champions(LoLChampions, recommended_position_for_champion, log = log, verbose = False)
                        LoLChampion_fields_to_print: list[str] = ["id", "name", "title", "alias"]
                        LoLChampion_df_selected: pandas.DataFrame = pandas.concat([LoLChampion_df.iloc[:1, :], LoLChampion_df[LoLChampion_df["id"].isin(selectable_champion_ids)]], ignore_index = True)
                        LoLChampion_df_query: pandas.DataFrame = LoLChampion_df.loc[:, LoLChampion_fields_to_print]
                        LoLChampion_df_query["id"] = LoLChampion_df["id"].astype(str) #方便检索（For convenience of retrieval）
                        LoLChampion_df_query = LoLChampion_df_query.map(lambda x: x.lower() if isinstance(x, str) else x)
                        print(format_df(LoLChampion_df_selected.loc[:, LoLChampion_fields_to_print])[0]) #虽然输出的是筛选后的表格，但实际上用户仍然可以尝试选择不可用的英雄（Although the selected table is output, users can still try choosing unavailable champions）
                        log.write(format_df(LoLChampion_df_selected.loc[:, LoLChampion_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                        back: bool = False
                        while True:
                            champion_queryStr: str = logInput()
                            if champion_queryStr == "":
                                continue
                            elif champion_queryStr == "0":
                                back = True
                                break
                            elif champion_queryStr == "-3":
                                pick_championId: int = -3
                                break
                            else:
                                query_positions = numpy.where(LoLChampion_df_query == champion_queryStr.lower()) #使用numpy.where检索的前提是数据框中每个单元格的值都不一样（The premise of query by `numpy.where` is that no two cells are the same）
                                if len(query_positions[0]) == 0:
                                    logPrint("没有找到该英雄。请重新输入。\nChampion not found. Please try again.")
                                else:
                                    resultRow = query_positions[0]
                                    result_champion_df = LoLChampion_df.loc[resultRow, LoLChampion_fields_to_print].reset_index(drop = True)
                                    pick_championId = LoLChampion_df["id"][resultRow[0]] #如果碰巧有多个单元格匹配用户的输入，取第一个。请向作者汇报该问题（If multiple cells happen to match the user input, the first cell is taken. Please report this issue to the author）
                                    logPrint("您选择了以下英雄：\nYou selected the following champion:")
                                    print(format_df(result_champion_df)[0])
                                    log.write(format_df(result_champion_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                                    break
                        if back:
                            logPrint("请选择行为类型：\nPlease select an action:\n1\t禁用（Ban）\n2\t选择（Pick）\n3\t重随（Reroll）\n4\t投票（Vote）")
                            continue
                        logPrint("是否直接锁定选择？（输入任意键直接锁定，否则不锁定。）\nDo you want to lock in? (Submit any non-empty string to lock in, or null to refuse locking in.)")
                        complete_str: str = logInput()
                        complete: bool = bool(complete_str)
                        gameflow_phase = await get_gameflow_phase(connection)
                        if gameflow_phase == "ChampSelect":
                            champ_select_session = await get_champ_select_session(connection)
                            if champ_select_session["isSpectating"]:
                                logPrint("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                            else:
                                #首先获取用户的槽位序号（First, get the user's cellId）
                                localPlayerCellId: int = champ_select_session["localPlayerCellId"]
                                #下面获取用户选英雄时的行为序号（Get the user's actionId when he/she's picking a champion）
                                selfKey_pick: str = str(localPlayerCellId) + " pick" #只选择类型为“选英雄”的行为（Only do operations on a pick action）
                                selfKey_ban: str = str(localPlayerCellId) + " ban" #只选择类型为“禁英雄”的行为（Only do operations on a ban action）
                                selfKey_vote: str = str(localPlayerCellId) + " vote" #只选择类型为“投票”的行为（Only do operations on a vote action）
                                selfKey: str = selfKey_ban if action_type == "ban" else selfKey_pick if action_type == "pick" else selfKey_vote
                                actions: dict[str, dict[str, Any]] = {}
                                for stage in champ_select_session["actions"]:
                                    for action in stage:
                                        key: str = str(action["actorCellId"]) + " " + action["type"]
                                        # if key in actions and action["type"] != "ban": #在旧版征召模式中，由同一个人来禁英雄，因此在禁用期间，这个人的行为的槽位序号和行为类型是一样的。这样的键重复无关紧要，因为后面的禁用行为序号一定比前面的禁用行为序号大，所以程序总是能追踪到最新的禁用行为（In old draft mode, one player bans multiple champions, so during the ban phase, the actorCellIds and types are both the same among this player's actions. In this case, the key duplicate doesn't matter, for the id of the later ban action is always greater than that of the earlier ban action, which means the program will always track the latest ban action）
                                        #     logPrint("检测到重复键（%s）。请修改代码。\nDetected the same key (%s). Please fix the code." %(key, key))
                                        actions[key] = action
                                if selfKey in actions:
                                    current_actionId: int = actions[selfKey]["id"]
                                    #下面通过LCU API选择英雄（Pick a champion through LCU API)
                                    body: dict[str, Any] = {"id": current_actionId, "actorCellId": localPlayerCellId, "championId": pick_championId, "type": action_type, "completed": complete, "isAllyAction": True, "isInProgress": True, "pickTurn": 0}
                                    logPrint(body)
                                    if champ_select_session["isLegacyChampSelect"]:
                                        response: Optional[dict[str, Any]] = await (await connection.request("PATCH", f"/lol-champ-select/v1/session/actions/{current_actionId}", data = body)).json()
                                    else:
                                        response: Optional[dict[str, Any]] = await (await connection.request("PATCH", f"/lol-lobby-team-builder/champ-select/v1/session/actions/{current_actionId}", data = body)).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        if response["httpStatus"] == 500:
                                            if response["message"] == "Unable to process action change: Received status Error: CHAMPION_ALREADY_BANNED instead of expected status of OK from request to teambuilder-draft:updateActionV1":
                                                logPrint("该英雄已被禁用。请切换一个英雄后重试。\nThis champion is already banned. Please switch to another champion and try again.")
                                            elif response["message"] == "Unable to process action change: Received status Error: INVALID_CHAMP_SELECTION instead of expected status of OK from request to teambuilder-draft:updateActionV1":
                                                logPrint("选用方式不合法。请检查该英雄是否被平台禁用。\nIllegal pick method. Please check whether this champion is disabled by platform.")
                                            elif response["message"] == "Unable to process action change: Received status Error: INVALID_STATE instead of expected status of OK from request to teambuilder-draft:updateActionV1":
                                                logPrint("选用状态不匹配。请核对当前阶段。\nInvalid champ select state. Please check the current stage.")
                                            elif response["message"] == "Error response for PATCH /lol-lobby-team-builder/champ-select/v1/session/actions/0: Unable to process action change: Received status Error: CHAMPION_ALREADY_PICKED instead of expected status of OK from request to teambuilder-draft:updateActionV1":
                                                logPrint("该英雄已被选用。\nThis champion is already picked.")
                                            else:
                                                logPrint("在选择英雄时出现了一个错误。\nThere was a problem selecting your champion.")
                                        else:
                                            logPrint("选择失败！\nPick failed.")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        champ_select_session = await get_champ_select_session(connection)
                                        current_actions: dict[int, dict[str, Any]] = {}
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
                elif action[0] == "3":
                    gameflow_phase = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await get_champ_select_session(connection)
                        if champ_select_session["isSpectating"]:
                            logPrint("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                        elif champ_select_session["allowRerolling"]:
                            if champ_select_session["rerollsRemaining"] == 0:
                                logPrint("您的重随次数不足。\nYou don't have any rerolls.")
                            else:
                                if champ_select_session["isLegacyChampSelect"]:
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/my-selection/reroll")).json()
                                else:
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/my-selection/reroll")).json()
                                logPrint(response)
                                if isinstance(response, dict) and "errorCode" in response:
                                    if response["httpStatus"] == 404 and response["message"] == "No active delegate":
                                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                                    elif response["httpStatus"] == 500 and (response["message"] == "Error response for POST /lol-lobby-team-builder/champ-select/v1/session/my-selection/reroll: Unable to reroll: Received status Error: NO_REROLLS_REMAINING instead of expected status of OK from request to teambuilder-draft:rerollV1" or response["message"] == "Unable to reroll: Received status Error: NO_REROLLS_REMAINING instead of expected status of OK from request to teambuilder-draft:rerollV1"):
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
                logPrint("请选择行为类型：\nPlease select an action:\n1\t禁用（Ban）\n2\t选择（Pick）\n3\t重随（Reroll）\n4\t投票（Vote）")
        elif option[0] == "3":
            collection_df_fields_to_print: list[str] = ["inventoryType", "itemId", "name", "ownershipType"]
            skin_df_fields_to_print: list[str] = ["id", "name"]
            logPrint("请选择要修改的赛前配置：\nPlease select a loadout:\n1\t符文（Perks）\n2\t召唤师技能（Summoner spells）\n3\t皮肤（Skin）\n4\t守卫（眼）皮肤（Ward skin）\n5\t表情（Emotes）\n6\t召唤师图标（Summoner icon）\n7\t水晶枢纽终结特效（Nexus finisher）\n8\t旗帜（Banner）\n9\t徽章（Crest）\n10\t冠军杯赛奖杯（Tournament trophy）")
            while True:
                loadout_option: str = logInput()
                if loadout_option == "":
                    continue
                elif loadout_option[0] == "0":
                    break
                elif loadout_option == "1":
                    wd: str = os.getcwd()
                    subscript_path: str = os.path.join(wd, "Customized Program 19 - Configure Perks.py")
                    if os.path.exists(subscript_path):
                        logPrint(f"正在打开（Opening）： {subscript_path}")
                        subprocess.run(["python", subscript_path])
                    else:
                        logPrint('''在同目录下未发现符文脚本。取消该操作。请自行在客户端内修改。\n"Customized Program 19 - Configure Perks.py" isn't found under the same directory. This operation is cancelled. Please change inside the League Client.''')
                elif loadout_option in {"2", "3"}:
                    gameflow_phase: str = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
                        if champ_select_session["isSpectating"]:
                            logPrint("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                        else:
                            if loadout_option == "2":
                                logPrint("该模式可用召唤师技能如下：\nAvailable summoner spells of this game mode are as follows:")
                                gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
                                gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_source}
                                if champ_select_session["queueId"] == 0: #对于传统的自定义房间，通过获取游戏会话来确定游戏模式（For a traditional custom lobby, determine the game mode by the gameflow session）
                                    gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                                    available_spells: list[int] = available_spell_dict[gameflow_session["gameData"]["queue"]["gameMode"]]
                                else: #对于阵容匹配的英雄选择阶段，通过队列序号来确定游戏模式（For team builder managed champ select stage, determine the game mode by queueId）
                                    available_spells = available_spell_dict[gameQueues[champ_select_session["queueId"]]["gameMode"]]
                                for spellId in sorted(available_spells):
                                    spell: dict[str, Any] = spells[spellId]
                                    logPrint("%d\t%s" %(spellId, spell["name"]))
                                logPrint("请依次输入两个召唤师技能的序号，以空格为分隔符：\nPlease input the two spellIds, split by space:")
                                while True:
                                    index_got: bool = False
                                    spell_str: str = logInput()
                                    if spell_str == "":
                                        continue
                                    elif spell_str == "0":
                                        index_got = False
                                        break
                                    else:
                                        selectedSpellIds: list[str] = spell_str.split()
                                        if len(selectedSpellIds) != 2:
                                            logPrint("请输入两个召唤师技能的序号！\nPlease submit two spellIds!")
                                        else:
                                            try:
                                                selectedSpellIds: list[int] = list(map(int, selectedSpellIds))
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
                                    body: dict[str, int] = {"spell1Id": selectedSpellIds[0], "spell2Id": selectedSpellIds[1]}
                                    if champ_select_session["isLegacyChampSelect"]:
                                        response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-champ-select/v1/session/my-selection", data = body)).json()
                                    else:
                                        response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-lobby-team-builder/champ-select/v1/session/my-selection", data = body)).json()
                                    logPrint(response)
                                    if isinstance(response, dict) and "errorCode" in response:
                                        if response["httpStatus"] == 400 and response["message"] == "Not an active participant in a champ select session":
                                            logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                                        else:
                                            logPrint("召唤师技能更换失败！\nSummoner spell change failed!")
                                    else:
                                        time.sleep(GLOBAL_RESPONSE_LAG)
                                        localPlayer: dict[str, Any] = await get_champSelect_player(connection)
                                        if [localPlayer["spell1Id"], localPlayer["spell2Id"]] == selectedSpellIds:
                                            logPrint("召唤师技能更换成功！\nSummoner spell change succeeded!")
                                        else:
                                            logPrint("召唤师技能更换失败！\nSummoner spell change failed!")
                            else:
                                if champ_select_session["isLegacyChampSelect"]:
                                    pickable_skin_ids: list[int] = await (await connection.request("GET", "/lol-champ-select/v1/pickable-skin-ids")).json()
                                else:
                                    pickable_skin_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/pickable-skin-ids")).json()
                                localPlayer = await get_champSelect_player(connection)
                                championId_pick_or_intent: int = localPlayer["championPickIntent"] or localPlayer["championId"]
                                skin_df_selected: pandas.DataFrame = pandas.concat([skin_df.iloc[:1, :], skin_df[(skin_df["id"].isin(pickable_skin_ids)) & (skin_df["championId"] == championId_pick_or_intent)]], ignore_index = True)
                                if len(skin_df_selected) == 1:
                                    logPrint("无可用皮肤。\nThere's not any available skin.")
                                else:
                                    logPrint("%s的可用皮肤如下：\nPickable skins of %s are as follows:" %(LoLChampions[championId_pick_or_intent]["title"], LoLChampions[championId_pick_or_intent]["alias"]))
                                    print(format_df(skin_df_selected.loc[:, skin_df_fields_to_print], print_index = True)[0])
                                    log.write(format_df(skin_df_selected.loc[:, skin_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                    logPrint("请选择一个皮肤：\nPlease select a skin:")
                                    while True:
                                        skin_index_str: str = logInput()
                                        if skin_index_str == "" or skin_index_str == "0":
                                            break
                                        elif skin_index_str == "-1" or skin_index_str in list(map(str, range(1, len(skin_df_selected)))):
                                            skin_index: int = int(skin_index_str)
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            continue
                                        selectedSkinId: int = championId_pick_or_intent * 1000 if skin_index == -1 else skin_df_selected["id"][skin_index]
                                        body: dict[str, int] = {"selectedSkinId": selectedSkinId}
                                        if champ_select_session["isLegacyChampSelect"]:
                                            response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-champ-select/v1/session/my-selection", data = body)).json()
                                        else:
                                            response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-lobby-team-builder/champ-select/v1/session/my-selection", data = body)).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            logPrint("皮肤更换失败！\nChampion skin change failed!")
                                        else:
                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                            localPlayer = await get_champSelect_player(connection)
                                            if localPlayer == {}:
                                                logPrint("游戏状态异常。\nAbnormal gameflow phase.")
                                            else:
                                                if localPlayer["selectedSkinId"] == selectedSkinId:
                                                    logPrint("皮肤更换成功！\nChampion skin change succeeded!")
                                                else:
                                                    logPrint("皮肤更换失败！请在锁定英雄后检查是否更换成功。\nChampion skin change failed! Please check if the skin is changed after locking in.")
                                            break
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                elif loadout_option in list(map(str, range(4, 11))):
                    loadout_scope: dict[str, Any] = await (await connection.request("GET", "/lol-loadouts/v4/loadouts/scope/account")).json()
                    if isinstance(loadout_scope, dict) and "errorCode" in loadout_scope:
                        logPrint(loadout_scope)
                        logPrint("未知错误！\nUnknown error!")
                    else:
                        if len(loadout_scope) == 0:
                            logPrint("无可用赛前配置方案。请重启英雄联盟客户端后再运行本程序。\nNo available loadouts. Please restart the League Client and then run this program.")
                        else:
                            loadoutId = loadout_scope[0]["id"] #因为赛前配置在每次退出英雄联盟客户端后就没了，所以随便取一个赛前配置就行。这里取了第一个列表元素（Because loadouts aren't reserved as the user exits the League Client, any loadout is OK to use. Here the first element of the loadout scope list is used）
                            loadoutName = loadout_scope[0]["name"]
                    inventoryTypes: dict[str, str] = {"4": "WARD_SKIN", "5": "EMOTE", "6": "SUMMONER_ICON", "7": "NEXUS_FINISHER", "8": "REGALIA_BANNER", "9": "REGALIA_CREST", "10": "TOURNAMENT_TROPHY"}
                    inventoryType: str = inventoryTypes[loadout_option]
                    collection_df_selected: pandas.DataFrame = pandas.concat([collection_df.iloc[:1, :], collection_df[collection_df["inventoryType"] == inventoryType]], ignore_index = True)
                    if len(collection_df_selected) == 1:
                        logPrint("您目前没有该类道具的使用权。\nYou don't have permissions to use any item of this inventoryType.")
                    else:
                        if inventoryType == "EMOTE":
                            logPrint("请选择您想要配置的表情种类：\nPlease select the category of emotes:\n1\t表情轮盘（Emote wheel）\n2\t回应（Reactions）")
                            while True:
                                category: str = logInput()
                                if category == "":
                                    continue
                                elif category[0] == "0":
                                    break
                                elif category[0] == "1":
                                    logPrint("请选择方位：\nPlease select a direction:\n1\t中央（Center）\n2\t左（Left）\n3\t右（Right）\n4\t上（Upper）\n5\t下（Lower）\n6\t左上（Upper-Left）\n7\t右上（Upper-Right）\n8\t左下（Lower-Left）\n9\t右下（Lower-Right）")
                                    directions: dict[str, str] = {"1": "CENTER", "2": "LEFT", "3": "RIGHT", "4": "UPPER", "5": "LOWER", "6": "UPPER_LEFT", "7": "UPPER_RIGHT", "8": "LOWER_LEFT", "9": "LOWER_RIGHT"}
                                    while True:
                                        direction_index_str: str = logInput()
                                        if direction_index_str == "":
                                            continue
                                        elif direction_index_str[0] == "0":
                                            break
                                        elif direction_index_str[0] in list(map(str, range(1, 10))):
                                            direction: str = directions[direction_index_str[0]]
                                            logPrint('请选择您想要使用的道具：（输入-1以初始化当前选择。）\nPlease select an item to use: (Submit "-1" to initialize the current choice.)')
                                            print(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], print_index = True)[0])
                                            log.write(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                            while True:
                                                index_got: bool = False
                                                item_index_str: str = logInput()
                                                if item_index_str == "":
                                                    continue
                                                elif item_index_str == "0":
                                                    index_got = False
                                                    break
                                                elif item_index_str == "-1" or item_index_str in list(map(str, range(1, len(collection_df_selected)))):
                                                    item_index: int = int(item_index_str)
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            if index_got:
                                                contentId: str = "" if item_index == -1 else collection_df_selected["uuid"][item_index]
                                                itemId: int = 0 if item_index == -1 else collection_df_selected["itemId"][item_index]
                                                loadout_key: str = f"{inventoryType}_WHEEL_{direction}" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                                body: dict[str, Any] = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                                response: Optional[dict[str, Any]] = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
                                                logPrint(response)
                                                if isinstance(response, dict) and "errorCode" in response:
                                                    if response["message"] == "UpdateLoadout Failed - Loadout does not exist in cache.":
                                                        logPrint("更新赛前配置失败。请检查代码为%s的赛前配置是否存在。如果不存在，请返回到选择赛前配置之前的步骤，再重试。\nLoadout update failed. Please check if the loadout of id %s still exists. If it doesn't exist, please return to the step before selecting to configure the TFT loadouts and then try again.")
                                                    else:
                                                        logPrint("未知错误！\nUnknown error!")
                                                else:
                                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                                    loadout: dict[str, Any] = await (await connection.request("GET", f"/lol-loadouts/v4/loadouts/{loadoutId}")).json()
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
                                        reaction_index_str: str = logInput()
                                        if reaction_index_str == "":
                                            continue
                                        elif reaction_index_str[0] == "0":
                                            break
                                        elif reaction_index_str[0] in list(map(str, range(1, 5))):
                                            reaction: str = reactions[reaction_index_str[0]]
                                            logPrint('请选择您想要使用的道具：（输入-1以初始化当前选择。）\nPlease select an item to use: (Submit "-1" to initialize the current choice.)')
                                            print(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], print_index = True)[0])
                                            log.write(format_df(collection_df_selected.loc[:, collection_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0])
                                            while True:
                                                index_got: bool = False
                                                item_index_str: str = logInput()
                                                if item_index_str == "":
                                                    continue
                                                elif item_index_str == "0":
                                                    index_got = False
                                                    break
                                                elif item_index_str == "-1" or item_index_str in list(map(str, range(1, len(collection_df_selected)))):
                                                    item_index: int = int(item_index_str)
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                            if index_got:
                                                contentId: str = "" if item_index == -1 else collection_df_selected["uuid"][item_index]
                                                itemId: int = 0 if item_index == -1 else collection_df_selected["itemId"][item_index]
                                                loadout_key: str = f"{inventoryType}_{reaction}" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                                body: dict[str, Any] = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                                response: Optional[dict[str, Any]] = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
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
                                index_got: bool = False
                                item_index_str: str = logInput()
                                if item_index_str == "":
                                    continue
                                elif item_index_str == "0":
                                    index_got = False
                                    break
                                elif item_index_str == "-1" or item_index_str in list(map(str, range(1, len(collection_df_selected)))):
                                    item_index: int = int(item_index_str)
                                    index_got = True
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                contentId: str = "" if item_index == -1 else collection_df_selected["uuid"][item_index]
                                itemId: int = 0 if item_index == -1 else collection_df_selected["itemId"][item_index]
                                if inventoryType == "SUMMONER_ICON":
                                    body: dict[str, int] = {"profileIconId": itemId}
                                    response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-summoner/v1/current-summoner/icon", data = body)).json()
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
                                    loadout_key: str = f"{inventoryType}_SLOT" #不是所有的配置键都符合道具类型后缀“_SLOT”的格式。比如表情（EMOTE）的配置键包括“EMOTE_WHEEL_PANEL”。但是这个格式适用于这里的四个道具类型（Not all loadout keys follows the pattern where an inventoryType is followed by "_SLOT". For example, the loadout key for EMOTE may be "EMOTE_WHEEL_PANEL". Nevertheless, this pattern applies to all of the four inventoryTypes here）
                                    body: dict[str, Any] = {"id": loadoutId, "name": loadoutName, "loadout": {loadout_key: {"inventoryType": inventoryType, "contentId": contentId, "itemId": itemId}}}
                                    response: Optional[dict[str, Any]] = await (await connection.request("PATCH", f"/lol-loadouts/v4/loadouts/{loadoutId}", data = body)).json()
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
                back: bool = False
                muted_players: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                muted_player_puuids: list[str] = list(map(lambda x: x["puuid"], muted_players))
                muted_player_obfuscatedPuuids: list[str] = list(map(lambda x: x["obfuscatedPuuid"], muted_players))
                gameflow_phase: str = await get_gameflow_phase(connection)
                if gameflow_phase == "ChampSelect":
                    player_df: pandas.DataFrame = await sort_ChampSelect_players(connection, LoLChampions, championSkins, spells, wardSkins, playerMode = 1, log = log)
                    player_df["muted"] = ["已静音"] + (len(player_df) - 1) * [""]
                    for i in range(1, len(player_df)):
                        for muted_player in muted_players:
                            if player_df["puuid"][i] == muted_player["puuid"] or player_df["obfuscatedPuuid"][i] == muted_player["obfuscatedPuuid"]:
                                player_df["muted"][i] = "√"
                    player_df_fields_to_print: list[str] = ["cellId", "gameName", "tagLine", "playerAlias", "muted", "assignedPosition", "champion name", "champion alias"]
                    player_df_selected: pandas.DataFrame = pandas.concat([player_df.iloc[:1, :], player_df[(player_df["isHumanoid"] == "") & ~((player_df["gameName"] == "") & (player_df["tagLine"] == "") & (player_df["playerAlias"] == ""))]], ignore_index = True)
                    if len(player_df_selected) > 1:
                        logPrint("请选择一个要切换静音状态的玩家：\nPlease select a player to toggle mute/unmute status:")
                        print(format_df(player_df_selected.loc[:, player_df_fields_to_print], print_index = True)[0])
                        log.write(format_df(player_df_selected.loc[:, player_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        while True:
                            index_got: bool = False
                            mute_index_str: str = logInput()
                            if mute_index_str == "":
                                continue
                            elif mute_index_str[0] == "0":
                                index_got = False
                                back = True
                                break
                            elif mute_index_str in list(map(str, range(1, len(player_df_selected)))):
                                mute_index: int = int(mute_index_str)
                                index_got = True
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if index_got:
                            selected_player_puuid: str = player_df_selected["puuid"][mute_index]
                            selected_player_obfuscatedPuuid: str = player_df_selected["obfuscatedPuuid"][mute_index]
                            selected_player_name: str = player_df_selected["playerAlias"][mute_index] if player_df_selected["gameName"][mute_index] == "" and player_df_selected["tagLine"][mute_index] == "" else player_df_selected["gameName"][mute_index] + "#" + player_df_selected["tagLine"][mute_index]
                            muted: bool = player_df_selected["muted"][mute_index] == "√"
                            if muted:
                                logPrint("您选择解除静音以下玩家：\nYou selected the following player to unmute:")
                            else:
                                logPrint("您选择静音以下玩家：\nYou selected the following player to mute:")
                            print(format_df(player_df_selected.loc[[mute_index], player_df_fields_to_print])[0])
                            log.write(format_df(player_df_selected.loc[[mute_index], player_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0])
                            body: dict[str, str] = {"puuid": selected_player_puuid, "obfuscatedPuuid": selected_player_obfuscatedPuuid}
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/toggle-player-muted", data = body)).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                if muted:
                                    logPrint(f"解除静音{selected_player_name}失败。\nFailed to unmute {selected_player_name}.")
                                else:
                                    logPrint(f"静音{selected_player_name}失败。\nFailed to mute {selected_player_name}.")
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                muted_players = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                                muted_player_puuids = list(map(lambda x: x["puuid"], muted_players))
                                muted_player_obfuscatedPuuids = list(map(lambda x: x["obfuscatedPuuid"], muted_players))
                                if muted:
                                    if selected_player_puuid in muted_player_puuids or selected_player_obfuscatedPuuid in muted_player_obfuscatedPuuids:
                                        logPrint(f"解除静音{selected_player_name}失败。\nFailed to unmute {selected_player_name}.")
                                    else:
                                        logPrint(f"解除静音{selected_player_name}成功。\nSuccessfully unmuted {selected_player_name}.")
                                else:
                                    if selected_player_puuid in muted_player_puuids or selected_player_obfuscatedPuuid in muted_player_obfuscatedPuuids:
                                        logPrint(f"静音{selected_player_name}成功。\nSuccessfully muted {selected_player_name}.")
                                    else:
                                        logPrint(f"静音{selected_player_name}失败。\nFailed to mute {selected_player_name}.")
                    else:
                        break
                else:
                    logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.\n请输入您想要切换静音状态的召唤师名。\nPlease enter the name of the summoner you want to toggle mute/unmute status.")
                    while True:
                        summonerName_to_mute: str = logInput()
                        if summonerName_to_mute == "":
                            continue
                        elif summonerName_to_mute == "0":
                            back = True
                            break
                        else:
                            player_info: dict[str, Any] = await get_info(connection, summonerName_to_mute)
                            if player_info["info_got"]:
                                player_puuid: str = player_info["body"]["puuid"]
                                player_name: str = get_info_name(player_info["body"])
                                muted: bool = player_puuid in muted_player_puuids
                                body: dict[str, str] = {"puuid": player_puuid}
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/toggle-player-muted", data = body)).json()
                                logPrint(response)
                                if isinstance(response, dict) and "errorCode" in response:
                                    if muted:
                                        logPrint(f"解除静音{player_name}失败。\nFailed to unmute {player_name}.")
                                    else:
                                        logPrint(f"静音{player_name}失败。\nFailed to mute {player_name}.")
                                else:
                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                    muted_players = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                                    muted_player_puuids = list(map(lambda x: x["puuid"], muted_players))
                                    muted_player_obfuscatedPuuids = list(map(lambda x: x["obfuscatedPuuid"], muted_players))
                                    if muted:
                                        if player_puuid in muted_player_puuids:
                                            logPrint(f"解除静音{player_name}失败。\nFailed to unmute {player_name}.")
                                        else:
                                            logPrint(f"解除静音{player_name}成功。\nSuccessfully unmuted {player_name}.")
                                    else:
                                        if player_puuid in muted_player_puuids:
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
            await report_player_champSelect(connection)
        elif option[0] == "7":
            logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t解锁全员战斗加成（Unlock battle boost）\n2\t设置最爱的分路英雄（Toggle favorite champions on different positions）\n3\t清空静音玩家（Clear muted players）\n4\t退出英雄选择阶段（Exit the champ select stage）\n5\t显示当前召唤师信息（Display current summoner's information）\n6\t调试游戏状态（Debug a gameflow phase）''')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    gameflow_phase: str = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
                        if champ_select_session["allowBattleBoost"]:
                            if champ_select_session["isLegacyChampSelect"]:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/team-boost/purchase")).json()
                            else:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/team-boost/purchase")).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                if response["httpStatus"] == 400:
                                    if response["message"] == "Error response for POST /lol-champ-select-legacy/v1/team-boost/purchase: Invalid function":
                                        logPrint("自定义模式不支持全员战斗加成。\nBattle boost isn't supported in a custom game.")
                                    else:
                                        logPrint("全员战斗加成解锁失败。\nBattle boost unlock failed.")
                                elif response["httpStatus"] == 500:
                                    if response["message"] == "Unable to purchase team boost: Received status Error: BATTLE_BOOST_NOT_ENOUGH_RP instead of expected status of OK from request to teambuilder-draft:activateBattleBoostV1":
                                        logPrint("你没有足够的点券来购买一次全员战斗加成。\nYou don't have enough RP to purchase a Battle Boost.")
                                    elif response["message"] == "Unable to purchase team boost: Received status Error: BATTLE_BOOST_ALREADY_ACTIVATED instead of expected status of OK from request to teambuilder-draft:activateBattleBoostV1":
                                        logPrint("您的队伍已经解锁了全员战斗加成。\nYour team has already unlocked the Battle Boost.")
                                    elif response["message"] == "Unable to purchase team boost: Received status Error: INVALID_STATE instead of expected status of OK from request to teambuilder-draft:activateBattleBoostV1":
                                        logPrint("在购买全员战斗加成时发生了一个错误。请检查您的英雄选择状态。\nThere was an error purchasing the Battle Boost. Please check your champion select status.")
                                    else:
                                        logPrint("全员战斗加成解锁失败。\nBattle boost unlock failed.")
                                else:
                                    logPrint("全员战斗加成解锁失败。\nBattle boost unlock failed.")
                            else:
                                logPrint("全员战斗加成已解锁！\nBattle boost unlocked!")
                        else:
                            logPrint("当前游戏模式不支持全员战斗加成。请切换游戏模式或大区后再试。\nBattle boost isn't supported in this game mode. Please switch to another game mode or server and try again.")
                    else:
                        logPrint("您目前不在英雄选择阶段。\nYou're not during a champ select stage.")
                elif suboption[0] == "2":
                    grid_champions: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champ-select/v1/all-grid-champions")).json() #该接口在自定义对局中不会及时更新，因此在使用该功能时不能完全依赖于程序提示，需要结合客户端来进行判断（The result from this endpoint doesn't update in time, so when using this function, users shouldn't completely rely on the program prompts. Instead, it's highly suggested to judge with the help of League Client）
                    grid_champions: dict[int, dict[str, Any]] = {champion["id"]: champion for champion in grid_champions}
                    candidatePositions: list[str] = ["top", "jungle", "middle", "bottom", "support"]
                    positions_zh: list[str] = ["上路", "打野", "中路", "下路", "辅助"]
                    favoriteChampions: dict[str, list[int]] = {"top": [], "jungle": [], "middle": [], "bottom": [], "support": []}
                    for champion in grid_champions.values():
                        for position in champion["positionsFavorited"]:
                            favoriteChampions[position].append(champion["id"])
                    logPrint("请选择一条分路：\nPlease choose a position:\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路（Bottom）\n5\t辅助（Support）")
                    while True:
                        position_index_str: str = logInput()
                        if position_index_str == "":
                            continue
                        elif position_index_str[0] == "0":
                            break
                        elif position_index_str[0] in list(map(str, range(1, 6))):
                            position_index: int = int(position_index_str[0])
                            current_position: str = candidatePositions[position_index - 1]
                            current_position_zh: str = positions_zh[position_index - 1]
                            logPrint("全英雄选用偏好情况如下：\nChampion priority is as follows:")
                            grid_champion_df: pandas.DataFrame = await sort_grid_champions(connection)
                            grid_champion_df_fields_to_print: list[str] = ["id", "name", "favorite_top", "favorite_jungle", "favorite_middle", "favorite_bottom", "favorite_support"]
                            print(format_df(grid_champion_df.loc[:, grid_champion_df_fields_to_print])[0])
                            log.write(format_df(grid_champion_df.loc[:, grid_champion_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                            logPrint("请输入您想要设为最爱或取消设为最爱的英雄序号：\nPlease enter the ids of champions you want to favorite or unfavorite:")
                            while True:
                                index_got: bool = False
                                champion_index_str: str = logInput()
                                if champion_index_str == "":
                                    continue
                                elif champion_index_str == "0":
                                    index_got = False
                                    break
                                elif champion_index_str == "all":
                                    champion_indices: list[int] = list(grid_champion_df["id"][1:])
                                    index_got = True
                                    break
                                else:
                                    try:
                                        tmp = eval(champion_index_str)
                                    except:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        if isinstance(tmp, int) and tmp in grid_champion_df["id"][1:]:
                                            champion_indices = [tmp]
                                            index_got = True
                                            break
                                        elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x in grid_champion_df["id"][1:], tmp)) and len(tmp) == len(set(tmp)):
                                            champion_indices = tmp
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                logPrint("您选择了以下英雄：\nYou selected the following champions:")
                                grid_champion_df_selected: pandas.DataFrame = pandas.concat([grid_champion_df.iloc[:1, :], grid_champion_df[grid_champion_df["id"].isin(champion_indices)]])
                                print(format_df(grid_champion_df_selected.loc[:, grid_champion_df_fields_to_print])[0])
                                log.write(format_df(grid_champion_df_selected.loc[:, grid_champion_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                logPrint("是否确认将以上英雄设为或取消设为您最爱的%s英雄？（输入任意键以确认，否则取消。）\nDo you want to favorite or unfavorite the above champions as %s? (Submit any non-empty string to confirm, or null to cancel.)" %(current_position_zh, current_position))
                                favor_confirm_str: str = logInput()
                                favor_confirm: bool = bool(favor_confirm_str)
                                if favor_confirm:
                                    for championId in champion_indices:
                                        current_championName: str = grid_champions[championId]["name"]
                                        positionFavorited: bool = current_position in grid_champions[championId]["positionsFavorited"]
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/toggle-favorite/%d/%s" %(championId, candidatePositions[position_index - 1]))).json()
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
                        candidatePositions = ["top", "jungle", "middle", "bottom", "support"]
                        positions_zh = ["上路", "打野", "中路", "下路", "辅助"]
                        favoriteChampions = {"top": [], "jungle": [], "middle": [], "bottom": [], "support": []}
                        for champion in grid_champions.values():
                            for position in champion["positionsFavorited"]:
                                favoriteChampions[position].append(champion["id"])
                        logPrint("请选择一条分路：\nPlease choose a position:\n1\t上路（Top）\n2\t打野（Jungle）\n3\t中路（Middle）\n4\t下路（Bottom）\n5\t辅助（Support）")
                elif suboption[0] == "3":
                    muted_players: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                    if len(muted_players) == 0:
                        logPrint("当前无静音玩家。\nThere's not any muted player.")
                    else:
                        logPrint("静音玩家如下：\nMuted players:")
                        muted_player_df: pandas.DataFrame = await sort_mutedPlayers_chat(connection)
                        print(format_df(muted_player_df, print_index = True)[0])
                        log.write(format_df(muted_player_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        for i in range(len(muted_players)):
                            player: dict[str, Any] = muted_players[i]
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/toggle-player-muted", data = player)).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint("解除玩家%d静音失败。\nFailed to unmute Player %d." %(i + 1, i + 1))
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                muted_players_new: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/muted-players")).json()
                                if player in muted_players_new:
                                    logPrint("解除玩家%d静音失败。\nFailed to unmute Player %d." %(i + 1, i + 1))
                                else:
                                    logPrint("解除玩家%d静音成功。\nSuccessfully unmuted Player %d." %(i + 1, i + 1))
                elif suboption[0] == "4":
                    gameflow_phase: str = await get_gameflow_phase(connection)
                    if gameflow_phase == "ChampSelect":
                        champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
                        if champ_select_session["isCustomGame"]:
                            if champ_select_session["isLegacyChampSelect"]:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/cancel-champ-select")).json() #这个接口在任何情况下都返回None，并且用户会返回至主页大厅（This endpoint returns None in any case, and the user should return to the home hub after this request）
                            else:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/quit")).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                if response["httpStatus"] == 400 and response["message"] == "Current champ select does not allow quitting":
                                    logPrint("当前英雄选择阶段不支持早退。\nCurrent champ select doesn't allow dodging.")
                                elif response["httpStatus"] == 404 and response["message"] == "No champ select session in progress.":
                                    logPrint("您不在英雄选择阶段，或者您正在进行传统的英雄选择。\nYou're not during the champ select stage, or you're in a legacy champ select.")
                                else:
                                    logPrint('退出英雄阶段的过程发生了异常。请尝试手动点击客户端右下角的“退出”按钮，或者重启客户端。\nAn error occurred when the program is trying to quit the champ select stage. Please try manually clicking the "Quit" button on the bottom-right corner of League Client, or restart the client.')
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "None":
                                    logPrint("您已退出英雄选择阶段。\nYou've quited the champ select stage.")
                                    return ""
                                else:
                                    logPrint("退出失败。\nExit failed.")
                        else:
                            logPrint("当前游戏模式不支持早退。强行退出英雄选择阶段可能导致客户端界面异常，实际英雄选择阶段将继续进行且游戏将正常启动。您确定要继续吗？（输入任意非空字符串以继续退出英雄选择阶段，否则取消本次操作。）\nEarly exit isn't supported in this game mode. Force to cancel champ select may cause the client not to display correctly, whereas the champ select stage will be going on and the game will start as normal. Do you really want to continue? (Submit any non-empty string to continue to cancel champ select stage, or null to cancel this operation.)")
                            cancel_str: str = logInput()
                            cancel: bool = bool(cancel_str)
                            if cancel:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/cancel-champ-select")).json()
                                logPrint(response)
                                if isinstance(response, dict) and "errorCode" in response:
                                    logPrint('退出英雄阶段的过程发生了异常。\nAn error occurred when the program is trying to quit the champ select stage.')
                                else:
                                    time.sleep(GLOBAL_RESPONSE_LAG)
                                    gameflow_phase = await get_gameflow_phase(connection)
                                    if gameflow_phase == "None":
                                        logPrint("您已退出英雄选择阶段。\nYou've quited the champ select stage.")
                                        return ""
                                    else:
                                        logPrint("退出失败。\nExit failed.")
                    else:
                        logPrint("您目前不在英雄选择阶段，但是您可以通过此方法来返回主页大厅。这可能会带来一些问题。是否继续？（输入任意非空字符串以继续退出英雄选择阶段，否则取消本次操作。）\nYou're not during a champ select stage, but doing this will lead to the home hub. This may lead to some potential problems. Do you want to continue? (Submit any non-empty string to continue to cancel champ select stage, or null to cancel this operation.)")
                        cancel_str = logInput()
                        cancel = bool(cancel_str)
                        if cancel:
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/cancel-champ-select")).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint('退出英雄阶段的过程发生了异常。\nAn error occurred when the program is trying to quit the champ select stage.')
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                gameflow_phase = await get_gameflow_phase(connection)
                                if gameflow_phase == "None":
                                    logPrint("您已返回大厅。\nYou've returned to the home hub.")
                                else:
                                    logPrint("退出失败。\nExit failed.")
                elif suboption[0] == "5":
                    await display_current_info(connection)
                elif suboption[0] == "6":
                    return await debug_gameflow_phase(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t解锁全员战斗加成（Unlock battle boost）\n2\t设置最爱的分路英雄（Toggle favorite champions on different positions）\n3\t清空静音玩家（Clear muted players）\n4\t退出英雄选择阶段（Exit the champ select stage）\n5\t显示当前召唤师信息（Display current summoner's information）\n6\t调试游戏状态（Debug a gameflow phase）''')
        elif option[0] == "8":
            champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
            logPrint(champ_select_session)
            with open("champ-select-session.json", "w", encoding = "utf-8") as fp:
                json.dump(champ_select_session, fp, indent = 4, ensure_ascii = False)
            logPrint('英雄选择会话已导出到同目录下的“champ-select-session.json”。\nChamp select session has been exported into "champ-select-session.json" under the same directory.')
        elif option[0] == "9":
            await manage_ux(connection)
    return ""

#-----------------------------------------------------------------------------
# 游戏内模拟（In-game simulation）
#-----------------------------------------------------------------------------
def sort_player_abilities(allgamedata: dict[str, Any]) -> pandas.DataFrame:
    abilities: list[dict[str, Any]] = allgamedata["activePlayer"]["abilities"]
    inGame_playerAbility_header_keys: list[str] = list(inGame_playerAbility_header.keys())
    inGame_playerAbility_data: dict[str, list[Any]] = {key: [] for key in inGame_playerAbility_header_keys}
    for hotkey in abilities:
        ability: dict[str, Any] = abilities[hotkey]
        for i in range(len(inGame_playerAbility_header_keys)):
            key: str = inGame_playerAbility_header_keys[i]
            if i == 0: #热键（`key`）
                to_append: Any = hotkey
            else:
                to_append = ability.get(key, "")
            inGame_playerAbility_data[key].append(to_append)
    inGame_playerAbility_statistics_output_order: list[int] = [0, 3, 2, 1]
    inGame_playerAbility_data_organized: dict[str, list[Any]] = {inGame_playerAbility_header_keys[i]: inGame_playerAbility_data[inGame_playerAbility_header_keys[i]] for i in inGame_playerAbility_statistics_output_order}
    inGame_playerAbility_df: pandas.DataFrame = pandas.DataFrame(data = inGame_playerAbility_data_organized)
    hotkey_order: list[str] = ["Passive", "Q", "W", "E", "R"]
    inGame_playerAbility_df["key"] = pandas.Categorical(inGame_playerAbility_df["key"], categories = hotkey_order, ordered = True)
    inGame_playerAbility_df = inGame_playerAbility_df.sort_values("key", ignore_index = True)
    inGame_playerAbility_df = pandas.concat([pandas.DataFrame([inGame_playerAbility_header])[inGame_playerAbility_df.columns], inGame_playerAbility_df], ignore_index = True)
    return inGame_playerAbility_df

def sort_inGame_championStats(allgamedata: dict[str, Any]) -> pandas.DataFrame:
    championStats: dict[str, Any] = allgamedata["activePlayer"]["championStats"]
    inGame_championStat_data: dict[str, list[Any]] = {"项目": list(inGame_championStat_header.values()), "Items": list(inGame_championStat_header.keys()), "值": list(map(lambda x: championStats[x], inGame_championStat_header))}
    inGame_championStat_statistics_output_order: list[int] = [12, 20, 27, 28, 25, 5, 1, 2, 19, 7, 0, 10, 11, 21, 14, 26, 13, 3, 4, 17, 18, 15, 24, 29, 22, 6, 30]
    inGame_championStat_df: pandas.DataFrame = pandas.DataFrame(data = inGame_championStat_data).iloc[inGame_championStat_statistics_output_order, :].reset_index(drop = True)
    return inGame_championStat_df

def sort_inGame_allplayers(allgamedata: dict[str, Any]) -> pandas.DataFrame:
    inGame_allPlayer_header_keys: list[str] = list(inGame_allPlayer_header.keys())
    inGame_allPlayer_data: dict[str, list[Any]] = {key: [] for key in inGame_allPlayer_header_keys}
    for player in allgamedata["allPlayers"]:
        scores: dict[str, int] = player["scores"]
        for i in range(len(inGame_allPlayer_header_keys)):
            key: str = inGame_allPlayer_header_keys[i]
            if i <= 20:
                if i == 12 or i == 13: #屏幕底部坐标和屏幕中央坐标（`screenPositionBottom` and `screenPositionCenter`）
                    to_append: Any = player.get(key, "")
                elif i == 18: #装备名称（`itemNames`）
                    to_append = "" if isinstance(player["items"], dict) and "error" in player["items"] else list(map(lambda x: x["displayName"], player["items"]))
                elif i == 19: #装备金币（`itemTotalGold`）
                    to_append = "" if isinstance(player["items"], dict) and "error" in player["items"] else sum(map(lambda x: x["count"] * (LoLItems[x["itemID"]]["priceTotal"] if x["itemID"] in LoLItems else x["price"]), player["items"])) #游戏内数据的装备价格是合成价格。其总价格需要调用装备数据资源。需要注意，游戏客户端不一定隶属于当前联盟客户端。例如，如果是在观看若干年前的回放，则有些装备可能在当前装备数据资源中找不到（The in-game data about item prices are synthetic prices. Item data resource is needed to get the total price. Note that the game client doesn't necessarily belong to the current League Client. For example, if the user is watching a replay created several years ago, then chances are that some items aren't in the current item data resource）
                elif i == 20: #阵营（`teamName`）
                    to_append = team_colors_str[player["team"]]
                else:
                    to_append = player[key]
            elif i <= 32: #符文和符文系相关键（Perk and perkstyle related keys）
                to_append = "" if isinstance(player["runes"], dict) and "error" in player["runes"] else player["runes"][key.split()[0]][key.split()[1]]
            elif i <= 40: #得分相关键（Score-related keys）
                if isinstance(player["scores"], dict) and "error" in player["scores"]:
                    to_append = ""
                else:
                    if i == 38: #击杀得分（`K/D/A`）
                        to_append = "%d/%d/%d" %(scores["kills"], scores["deaths"], scores["assists"])
                    elif i == 39: #战损比（`KDA`）
                        to_append = (scores["kills"] + scores["assists"]) / max(1, scores["deaths"])
                    elif i == 40: #分均补刀（`CSPM`）
                        to_append = scores["creepScore"] * 60 / allgamedata["gameData"]["gameTime"]
                    else:
                        to_append = scores[key]
            else: #召唤师技能相关键（Summoner spell-related keys）
                to_append = "" if isinstance(player["summonerSpells"], dict) and "error" in player["summonerSpells"] else player["summonerSpells"][key.split()[0]][key.split()[1]]
            inGame_allPlayer_data[key].append(to_append)
    inGame_allPlayer_statistics_output_order: list[int] = [20, 9, 10, 11, 16, 1, 0, 14, 15, 4, 5, 2, 8, 17, 18, 19, 41, 44, 38, 36, 35, 33, 39, 34, 40, 37, 25, 29, 21]
    inGame_allPlayer_data_organized: dict[str, list[Any]] = {inGame_allPlayer_header_keys[i]: inGame_allPlayer_data[inGame_allPlayer_header_keys[i]] for i in inGame_allPlayer_statistics_output_order}
    inGame_allPlayer_df: pandas.DataFrame = pandas.DataFrame(data = inGame_allPlayer_data_organized)
    optimize_bool_display(inGame_allPlayer_df)
    inGame_allPlayer_df = pandas.concat([pandas.DataFrame([inGame_allPlayer_header])[inGame_allPlayer_df.columns], inGame_allPlayer_df], ignore_index = True)
    return inGame_allPlayer_df

def sort_inGame_events(allgamedata: dict[str, Any]) -> pandas.DataFrame:
    championName_riotId_map: dict[str, str] = {}
    for player in allgamedata["allPlayers"]:
        if player["riotIdGameName"] in championName_riotId_map and championName_riotId_map[player["riotIdGameName"]] != player["championName"]: #解决克隆大作战中多名玩家具有相同的召唤师名称和选用英雄名称的问题（Solve the problem where more than one player has not only the same summonerName but also the same championName）
            championName_riotId_map[player["riotIdGameName"]] = championName_riotId_map[player["riodIdGameName"]] + " | " + player["championName"] #当多名玩家具有相同的召唤师名称时，仅通过游戏客户端接口无法区分之。直接删除这个召唤师名称又不太好，索性就标记为二者合并后的结果（When more than one player has the same summonerName, they can't be distinguished through game client API. Deleting this summonerName seems not the way, so I took the merged result）
        else:
            championName_riotId_map[player["riotIdGameName"]] = player["championName"]
    inGame_event_header_keys: list[str] = list(inGame_event_header.keys())
    inGame_event_data: dict[str, list[Any]] = {key: [] for key in inGame_event_header_keys}
    for event in allgamedata["events"]["Events"]:
        for i in range(len(inGame_event_header_keys)):
            key: str = inGame_event_header_keys[i]
            if i == 3: #亚龙类型（`DragonType`）
                to_append: Any = DragonTypes[event["DragonType"]] if "DragonType" in event else ""
            elif i == 12: #抢到资源（`Stolen`）
                to_append = "" if not "Stolen" in event else "√" if event["Stolen"] == "True" else "×"
            elif i in {15, 17, 20, 21, 22}:
                subkey_dict = {15: "Acer", 17: "Assisters", 20: "KillerName", 21: "Recipient", 22: "VictimName"}
                subkey: str = subkey_dict[i]
                if subkey in event:
                    if i == 17: #助攻者英雄名称（`AssisterChampionNames`）
                        to_append = list(map(lambda x: championName_riotId_map.get(x, x), event[subkey]))
                    else:
                        to_append = championName_riotId_map.get(event[subkey], event[subkey])
                else:
                    to_append = ""
            elif i == 16: #团战胜方阵营（`AcingTeamName`）
                to_append = team_colors_str[event["AcingTeam"]] if "AcingTeam" in event else ""
            elif i == 18: #事件类型（`EventType`）
                to_append = eventTypes_liveclient[event["EventName"]]
            elif i == 19: #事件时间（`EventTime_norm`）
                to_append = "%d:%02d" %(round(event["EventTime"]) // 60, round(event["EventTime"]) % 60)
            else:
                to_append = event.get(key, "")
            inGame_event_data[key].append(to_append)
    inGame_event_statistics_output_order: list[int] = [4, 5, 18, 6, 19, 10, 21, 9, 20, 8, 14, 22, 2, 17, 0, 15, 1, 16, 13, 7, 3, 12, 11]
    inGame_event_data_organized: dict[str, list[Any]] = {inGame_event_header_keys[i]: inGame_event_data[inGame_event_header_keys[i]] for i in inGame_event_statistics_output_order}
    inGame_event_df: pandas.DataFrame = pandas.DataFrame(data = inGame_event_data_organized)
    optimize_bool_display(inGame_event_df)
    inGame_event_df = pandas.concat([pandas.DataFrame([inGame_event_header])[inGame_event_df.columns], inGame_event_df], ignore_index = True)
    return inGame_event_df

def sort_inGame_metadata(allgamedata: dict[str, Any]) -> pandas.DataFrame:
    gameData: dict[str, Any] = allgamedata["gameData"]
    gameTime_norm: str = "%d:%02d" %(round(gameData["gameTime"]) // 60, round(gameData["gameTime"]) % 60)
    inGame_metadata: dict[str, list[Any]] = {"项目": list(inGame_metadata_header.values()), "Items": list(inGame_metadata_header.keys()), "值": list(map(lambda x: gameData[x], list(inGame_metadata_header.keys())[:5])) + [gameTime_norm]}
    inGame_metadata_statistics_output_order: list[int] = [0, 1, 5, 2, 3, 4]
    inGame_metaDf = pandas.DataFrame(data = inGame_metadata).iloc[inGame_metadata_statistics_output_order, :].reset_index(drop = True)
    return inGame_metaDf

async def inGame_simulation(connection: Connection) -> str:
    global gameClientApi_port_warning_printed, gameClientApi_cert_not_specified_warning_printed
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t查看英雄信息（Check champion information）\n2\t访问游戏客户端接口（Access game client API）\n3\t输出游戏会话（Output the gameflow session）\n4\t向好友发送密语（Chat with friends）\n5\t举报一名玩家（Report a player）\n6\t其它（Others）\n7\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] == "1":
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase in {"InProgress", "Reconnect"}:
                gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                gameData: dict[str, Any] = gameflow_session["gameData"]
                gameModeName: str = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameData["queue"]["id"]) if gameData["queue"]["name"] == "" else gameData["queue"]["name"]
                excel_name: str = "Player Stats in Match %s-%s (%s).xlsx" %(platformId, gameData["gameId"], normalize_file_name(gameModeName))
                players_metaDf: pandas.DataFrame = await sort_inGame_players(connection, LoLChampions, championSkins, summonerIcons, spells, log = log)
                print(format_df(players_metaDf)[0])
                try:
                    with (pandas.ExcelWriter(path = excel_name, engine = "openpyxl", mode = "a", if_sheet_exists = "replace") if os.path.exists(excel_name) else pandas.ExcelWriter(path = excel_name, engine = "openpyxl")) as writer:
                        addDefaultStyle(players_metaDf).to_excel(excel_writer = writer, sheet_name = "MemberComposition (InProgress)")
                except PermissionError:
                    logPrint(f"无写入权限！请确保{excel_name}未被打开且非只读状态！\nPermission denied! Please ensure {excel_name} isn't opened right now or read-only!")
                else:
                    logPrint(f'游戏内的成员构成已导出到同目录下的“{excel_name}”。\nMember composition in the game has been exported into {excel_name} under the same directory.')
            else:
                logPrint("您目前不在游戏内。\nYou're currently not in a game.")
        elif option[0] == "2": #此部分可离线运行（This part can run in an offline environment）
            if not gameClientApi_port_warning_printed:
                logPrint("英雄联盟游戏客户端默认使用2999端口。请确保没有其它应用程序占用该端口。\nLeague of Legends game client API uses Port 2999. Please make sure it's not occupied by other programs.")
                gameClientApi_port_warning_printed = True
            gameClientFound: bool = False
            allgamedata_fetched: bool = False
            for process in psutil.process_iter():
                if process.name() == "League of Legends.exe":
                    gameClientFound = True
                    break
            if gameClientFound:
                if args.cert_path == "":
                    if not gameClientApi_cert_not_specified_warning_printed:
                        logPrint("您未指定游戏客户端接口访问证书路径。程序将忽略警告。如果想要下载证书，请访问https://static.developer.riotgames.com/docs/lol/riotgames.pem链接。\nYou didn't specify the path of the root certificate for game client API access. Warnings will be disabled. To download the certificate, please visit https://static.developer.riotgames.com/docs/lol/riotgames.pem.")
                        gameClientApi_cert_not_specified_warning_printed = True
                if args.cert_path != "":
                    if os.path.exists(args.cert_path):
                        try:
                            allgamedata: dict[str, Any] = requests.get("https://127.0.0.1:2999/liveclientdata/allgamedata", verify = args.cert_path).json()
                        except requests.exceptions.SSLError:
                            logPrint("游戏客户端接口访问证书不正确。程序将跳过认证，并忽略警告。\nInvalid root certificate for game client API access. The program will skip the certificate identification and neglect warnings.")
                            args.cert_path = ""
                            gameClientApi_cert_not_specified_warning_printed = True
                        except requests.exceptions.ConnectionError:
                            logPrint("连接失败。请确保您目前仍在游戏中。\nConnection ERROR! Please make sure you're still in the game.")
                        else:
                            if "errorCode" in allgamedata:
                                logPrint(allgamedata)
                                if allgamedata["httpStatus"] == 404 and allgamedata["message"] == "Invalid URI format":
                                    logPrint("资源尚未加载完成。请等待全员进入游戏后再试一次。\nResources not loaded completely. Please wait until all players enter the game and try again afterwards.")
                            else:
                                allgamedata_fetched = True
                    else:
                        logPrint("游戏客户端接口访问证书路径不正确。程序将跳过认证，并忽略警告。\nInvalid path of the root certificate for game client API access. The program will skip the certificate identification and neglect warnings.")
                        args.cert_path = ""
                        gameClientApi_cert_not_specified_warning_printed = True
                if args.cert_path == "": #在通过命令行参数指定游戏客户端接口访问证书的情况下，只有请求出现问题才会将该命令行参数置为空字符串。如果请求正常，则不会再执行这一步（If the root certificate for game client API access is specified via the command line argument, then only when an error occurs to this request will this argument be set as an empty string. Otherwise, this if-statement block won't executed）
                    try:
                        allgamedata = requests.get("https://127.0.0.1:2999/liveclientdata/allgamedata", verify = False).json()
                    except requests.exceptions.ConnectionError:
                        logPrint("连接失败。请确保您目前仍在游戏中。\nConnection ERROR! Please make sure you're still in the game.")
                    else:
                        if "errorCode" in allgamedata:
                            logPrint(allgamedata)
                            if allgamedata["httpStatus"] == 404 and allgamedata["message"] == "Invalid URI format":
                                logPrint("资源尚未加载完成。请等待全员进入游戏后再试一次。\nResources not loaded completely. Please wait until all players enter the game and try again afterwards.")
                        else:
                            allgamedata_fetched = True
                if allgamedata_fetched:
                    logPrint("请选择要查看的内容：\nPlease select the content to check:\n0\t返回上一层（Return to the last step）\n1\t当前玩家信息（Current player's information）\n2\t所有玩家信息（All players' information）\n3\t事件（Events）\n4\t游戏模式（Game mode）\n5\t导出所有游戏信息（Export all game data）")
                    while True:
                        suboption: str = logInput()
                        if suboption == "":
                            continue
                        elif suboption[0] == "0":
                            break
                        elif suboption[0] == "1":
                            activePlayer = allgamedata["activePlayer"]
                            if "error" in activePlayer and activePlayer["error"] == "Spectator mode doesn't currently support this feature":
                                logPrint("您不在该对局内。\nYou're not in this match.")
                            else:
                                logPrint("召唤师名（summonerName）：%s" %(activePlayer["summonerName"]))
                                logPrint("英雄等级（Champion level）：%d" %(activePlayer["level"]))
                                logPrint("英雄技能（Champion abilities）：")
                                inGame_playerAbility_df: pandas.DataFrame = sort_player_abilities(allgamedata)
                                print(format_df(inGame_playerAbility_df)[0])
                                log.write(format_df(inGame_playerAbility_df)[0] + "\n")
                                logPrint("基础属性（Basic stats）：")
                                inGame_championStat_df: pandas.DataFrame = sort_inGame_championStats(allgamedata)
                                print(format_df(inGame_championStat_df, align = "^^>")[0])
                                log.write(format_df(inGame_championStat_df, align = "^^>")[0] + "\n")
                                logPrint("按回车键以继续……\nPress Enter to continue ...")
                                logInput()
                                logPrint("当前金币（Current gold）：%f" %(activePlayer["currentGold"]))
                                logPrint("符文配置（Perk configuration）：")
                                fullRunes: dict[str, Any] = activePlayer["fullRunes"]
                                logPrint("主系（Primary perkstyle）：%s（%d）" %(fullRunes["primaryRuneTree"]["displayName"], fullRunes["primaryRuneTree"]["id"]))
                                logPrint("副系（Secondary perkstyle）：%s（%d）" %(fullRunes["secondaryRuneTree"]["displayName"], fullRunes["secondaryRuneTree"]["id"]))
                                logPrint("基石符文（Keystone）：%s（%d）" %(fullRunes["keystone"]["displayName"], fullRunes["keystone"]["id"]))
                                logPrint("符文（Perks）：%s" %("、".join(list(map(lambda x: "%s（%d）" %(x["displayName"], x["id"]), fullRunes["generalRunes"])))))
                                logPrint("符文属性（Rune stats）：%s" %("、".join(list(map(lambda x: "%s（%d）" %(perks[x["id"]]["name"], x["id"]), fullRunes["statRunes"])))))
                                logPrint("启用队伍相关联颜色（Team relative color enabled）：%s" %("√" if activePlayer["teamRelativeColors"] else "×"))
                        elif suboption[0] == "2":
                            inGame_allPlayer_df: pandas.DataFrame = sort_inGame_allplayers(allgamedata)
                            excel_name: str = "inGame_data.xlsx"
                            try:
                                with (pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") if os.path.exists(excel_name) else pandas.ExcelWriter(path = excel_name)) as writer:
                                    addDefaultStyle(inGame_allPlayer_df).to_excel(excel_writer = writer, sheet_name = "AllPlayers")
                                    worksheet = writer.sheets["AllPlayers"]
                                    worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                                    addFormat_inGame_allPlayer_wb(worksheet, inGame_allPlayer_df)
                            except PermissionError:
                                logPrint(f"无写入权限！请确保{excel_name}未被打开且非只读状态！\nPermission denied! Please ensure {excel_name} isn't opened right now or read-only!")
                            else:
                                logPrint(f'所有玩家信息已导出到同目录下的“{excel_name}”。\nAll player information has been exported into {excel_name} under the same directory.')
                        elif suboption[0] == "3":
                            inGame_event_df: pandas.DataFrame = sort_inGame_events(allgamedata)
                            excel_name: str = "inGame_data.xlsx"
                            try:
                                with (pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") if os.path.exists(excel_name) else pandas.ExcelWriter(path = excel_name)) as writer:
                                    addDefaultStyle(inGame_event_df).to_excel(excel_writer = writer, sheet_name = "Events")
                            except PermissionError:
                                logPrint(f"无写入权限！请确保{excel_name}未被打开且非只读状态！\nPermission denied! Please ensure {excel_name} isn't opened right now or read-only!")
                            else:
                                logPrint(f'所有事件已导出到同目录下的“{excel_name}”。\nAll events have been exported into {excel_name} under the same directory.')
                        elif suboption[0] == "4":
                            inGame_metaDf: pandas.DataFrame = sort_inGame_metadata(allgamedata)
                            logPrint("游戏元数据如下：\nGame metadata is as follows:")
                            print(format_df(inGame_metaDf)[0])
                            log.write(format_df(inGame_metaDf)[0] + "\n")
                        elif suboption[0] == "5":
                            logPrint(allgamedata)
                            with open("allgamedata.json", "w", encoding = "utf-8") as fp:
                                json.dump(allgamedata, fp, indent = 4, ensure_ascii = False)
                            logPrint('游戏内数据已导出到同目录下的“allgamedata.json”。\nGame data has been exported into "allgamedata.json" under the same directory.')
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            continue
                        logPrint("请选择要查看的内容：\nPlease select the content to check:\n0\t返回上一层（Return to the last step）\n1\t当前玩家信息（Current player's information）\n2\t所有玩家信息（All players' information）\n3\t事件（Events）\n4\t游戏模式（Game mode）\n5\t导出所有游戏信息（Export all game data）")
            else:
                logPrint("未检测到运行中的游戏。\nNo running game detected.")
        elif option[0] == "3":
            gameflow_session: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            logPrint(gameflow_session)
            with open("gameflow-session.json", "w", encoding = "utf-8") as fp:
                json.dump(gameflow_session, fp, indent = 4, ensure_ascii = False)
            logPrint('游戏会话已导出到同目录下的“gameflow-session.json”。\nGameflow session has been exported into "gameflow-session.json" under the same directory.')
        elif option[0] == "4":
            await chat(connection)
        elif option[0] == "5":
            await report_player_inGame(connection)
        elif option[0] == "6":
            logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）''')
            while True:
                suboption: str = logInput()
                if suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await display_current_info(connection)
                elif suboption[0] == "2":
                    return await debug_gameflow_phase(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）''')
        elif option[0] == "7":
            await manage_ux(connection)
    return ""

#-----------------------------------------------------------------------------
# 赛后预结算阶段模拟（Pre-end-of-game stage simulation）
#-----------------------------------------------------------------------------
async def sort_ballot_players(connection: Connection) -> pandas.DataFrame:
    ballot_player_header_keys: list[str] = list(ballot_player_header.keys())
    ballot_player_data: dict[str, list[Any]] = {key: [] for key in ballot_player_header_keys}
    honor_ballot: dict[str, Any] = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
    honoredPlayers: dict[str, dict[str, str]] = {player["recipientPuuid"]: player for player in honor_ballot["honoredPlayers"]}
    if not(isinstance(honor_ballot, dict) and "errorCode" in honor_ballot):
        for player in honor_ballot["eligibleAllies"] + honor_ballot["eligibleOpponents"]:
            player_info_recapture: int = 0
            player_info: dict[str, Any] = await get_info(connection, player["puuid"])
            while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                logPrint(player_info["message"])
                player_info_recapture += 1
                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture))
                player_info = await get_info(connection, player["puuid"])
            if not player_info["info_got"]:
                logPrint(player_info["message"])
                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) capture failed!" %(player["puuid"], player["puuid"]))
            for i in range(len(ballot_player_header_keys)):
                key: str = ballot_player_header_keys[i]
                if i == 7 or i == 8: #召唤师信息相关键（Summoner information-related keys）
                    to_append: Any = player_info["body"][key] if player_info["info_got"] else ""
                elif i == 9: #是否队友（`ally?`）
                    to_append = player in honor_ballot["eligibleAllies"]
                elif i == 10: #已赞誉（`honored`）
                    to_append = player["puuid"] in honoredPlayers
                elif i == 11: #赞誉类型（`honorType`）
                    to_append = honoredPlayers[player["puuid"]]["honorType"] if player["puuid"] in honoredPlayers else ""
                elif i == 12: #赞誉类型标题（`honorType_tooltip_header`）
                    to_append = honorType_tooltip_headers.get(honoredPlayers[player["puuid"]]["honorType"], "") if player["puuid"] in honoredPlayers else ""
                elif i == 13: #赞誉类型正文（`honorType_tooltip_body`）
                    to_append = honorType_tooltip_bodies.get(honoredPlayers[player["puuid"]]["honorType"], "") if player["puuid"] in honoredPlayers else ""
                else:
                    to_append = player[key]
                ballot_player_data[key].append(to_append)
    ballot_player_statistics_output_order: list[int] = [6, 7, 8, 5, 2, 9, 1, 3, 4, 0, 10, 11, 12, 13]
    ballot_player_data_organized: dict[str, list[Any]] = {ballot_player_header_keys[i]: ballot_player_data[ballot_player_header_keys[i]] for i in ballot_player_statistics_output_order}
    ballot_player_df: pandas.DataFrame = pandas.DataFrame(data = ballot_player_data_organized)
    optimize_bool_display(ballot_player_df)
    ballot_player_df = pandas.concat([pandas.DataFrame([ballot_player_header])[ballot_player_df.columns], ballot_player_df], ignore_index = True)
    return ballot_player_df

async def preEndOfGame_simulation(connection: Connection) -> str:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n!1\t赞誉其他玩家（Honor players）\n2\t查看票数（Check the number of votes）\n3\t这次不行（Not this time）\n4\t输出荣誉投票信息（Print honor ballot information）\n5\t输出当前事件（Print current sequence event）\n6\t聊天（Chat）\n7\t举报一名玩家（Report a player）\n8\t其它（Others）\n9\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('请选择一个对局预结算阶段相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select a PreEndOfGame-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t完成预结算阶段的一个事件（Complete an event before the end of a game）\n2\t查看当前预结算阶段事件（Check the current event before the end of a game）\n3\t删除一个预结算阶段的事件（Delete an event before the end of a game）\n4\t修改一个预结算阶段的事件的显示优先级（Change the display priority of an event before the end of a game）')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection, log = log)
                elif suboption[0] == "0":
                    break
                elif suboption[0] in list(map(str, range(1, 5))):
                    if suboption[0] == "1":
                        logPrint("请输入一个事件名称：\nPlease input the name of the event:\nsequenceEventName = ", end = "")
                        sequenceEventName: str = input()
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
                        priority: str = input()
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
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase == "PreEndOfGame":
                honor_ballot: dict[str, Any] = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
                if honor_ballot["votePool"]["votes"] == 0:
                    logPrint("您已经没有赞誉票了。\nYou've run out of votes.")
                else:
                    ballot_player_df: pandas.DataFrame = await sort_ballot_players(connection)
                    ballot_player_df_fields_to_print: list[str] = ["gameName", "tagLine", "ally?", "championName", "role", "botPlayer"]
                    if len(ballot_player_df) == 1:
                        logPrint("目前没有可以赞誉的玩家。\nThere's not any player to honor for now.")
                    else:
                        logPrint("赞誉那些做出了正面影响、表现了惊人韧性，或相处起来非常有趣的玩家。\nHonor players who made a positive impact, displayed great resilience, or were just fun to play with.")
                        print(format_df(ballot_player_df.loc[:, ballot_player_df_fields_to_print], print_index = True)[0])
                        log.write(format_df(ballot_player_df.loc[:, ballot_player_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        logPrint("请选择一名玩家：\nPlease select a player:")
                        while True:
                            index_got: bool = False
                            player_index_str: str = logInput()
                            if player_index_str == "":
                                continue
                            elif player_index_str == "0":
                                index_got = False
                                break
                            elif player_index_str in list(map(str, range(1, len(ballot_player_df)))):
                                player_index: int = int(player_index_str)
                                index_got = True
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if index_got:
                            player_summonerId: int = ballot_player_df["summonerId"][player_index]
                            player_puuid: str = ballot_player_df["puuid"][player_index]
                            honorType: str = "HEART" #取值（Available values）：COOL、SHOTCALLER、HEART
                            gameId: int = honor_ballot["gameId"]
                            body: dict[str, str | int] = {"summonerId": player_summonerId, "puuid": player_puuid, "honorType": honorType, "gameId": gameId}
                            logPrint(body)
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-honor-v2/v1/honor-player", data = body)).json()
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
            honor_ballot: dict[str, Any] = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
            if isinstance(honor_ballot, dict) and "errorCode" in honor_ballot:
                logPrint("赞誉投票信息获取异常。\nHonor ballot information capture failed.")
            else:
                logPrint("你每局获取1张荣誉投票，并且至多总共储存4张。未使用的投票可用在下一局比赛。\n")
                votes_total: int = honor_ballot["votePool"]["votes"]
                votes_fromGamePlayed: int = honor_ballot["votePool"]["fromGamePlayed"]
                votes_fromHighHonor: int = honor_ballot["votePool"]["fromHighHonor"]
                votes_fromRecentHonors: int = honor_ballot["votePool"]["fromRecentHonors"]
                votes_fromRollover: int = honor_ballot["votePool"]["fromRollover"]
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
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase == "PreEndOfGame":
                response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/lol-honor-v2/v1/ballot")).json()
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
            honor_ballot: dict[str, Any] = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
            logPrint(honor_ballot)
            with open("honor-ballot.json", "w", encoding = "utf-8") as fp:
                json.dump(honor_ballot, fp, indent = 4, ensure_ascii = False)
            logPrint('荣誉投票信息已导出到同目录下的“honor-ballot.json”。\nHonor ballot information has been exported into "honor-ballot.json" under the same directory.')
        elif option[0] == "5":
            currentSequenceEvent: str = await (await connection.request("GET", "/lol-pre-end-of-game/v1/currentSequenceEvent")).json()
            logPrint(currentSequenceEvent)
            with open("currentSequenceEvent.json", "w", encoding = "utf-8") as fp:
                json.dump(currentSequenceEvent, fp, indent = 4, ensure_ascii = False)
            logPrint('当前序列事件信息已导出到同目录下的“currentSequenceEvent.json”。\nCurrent sequence event has been exported into "currentSequenceEvent.json" under the same directory.')
        elif option[0] == "6":
            await report_player_endOfGame(connection)
        elif option[0] == "7":
            await chat(connection)
        elif option[0] == "8":
            logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）''')
            while True:
                suboption: str = logInput()
                if suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    await display_current_info(connection)
                elif suboption[0] == "2":
                    return await debug_gameflow_phase(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）''')
        elif option[0] == "8":
            await manage_ux(connection)
    return ""

#-----------------------------------------------------------------------------
# 赛后结算阶段模拟（End-of-game stage simulation）
#-----------------------------------------------------------------------------
async def sort_eog_champion_mastery_update(connection: Connection) -> pandas.DataFrame:
    mastery_updates = await (await connection.request("GET", "/lol-end-of-game/v1/champion-mastery-updates")).json()
    eog_mastery_update_header_keys: list[str] = list(eog_mastery_update_header.keys())
    eog_mastery_update_data: dict[str, list[Any]] = {"项目": [], "Items": [], "值": []}
    if not (isinstance(mastery_updates, dict) and "errorCode" in mastery_updates):
        player_info_recapture: int = 0
        player_info: dict[str, Any] = await get_info(mastery_updates["puuid"])
        while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
            logPrint(player_info["message"])
            player_info_recapture += 1
            logPrint("当前玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of current player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(mastery_updates["puuid"], player_info_recapture, mastery_updates["puuid"], player_info_recapture))
        if not player_info["info_got"]:
            logPrint(player_info["message"])
            logPrint("当前玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of current player (puuid: %s) capture failed!" %(mastery_updates["puuid"], mastery_updates["puuid"]))
        for i in range(len(eog_mastery_update_header_keys)):
            key: str = eog_mastery_update_header_keys[i]
            eog_mastery_update_data["项目"].append(eog_mastery_update_header[key])
            eog_mastery_update_data["Items"].append(key)
            if i >= 19 and i <= 21: #英雄相关键（Champion-related keys）
                value: Any = LoLChampions[mastery_updates["championId"]][key.split("_")[1]] if mastery_updates["championId"] in LoLChampions else ""
            elif i >= 22: #召唤师信息相关键（Summoner information-related keys）
                value = player_info["body"][key] if player_info["info_got"] else ""
            else:
                value = mastery_updates[key]
            eog_mastery_update_data["值"].append(value)
    eog_mastery_update_statistics_output_order: list[int] = [2, 15, 22, 23, 1, 19, 21, 20, 3, 8, 6, 4, 7, 9, 12, 14, 10, 11, 0, 13, 16, 17, 18]
    eog_mastery_update_data_organized: dict[str, list[Any]] = {"项目": [], "Items": [], "值": []}
    for i in eog_mastery_update_statistics_output_order:
        key: str = eog_mastery_update_header_keys[i]
        value: Any = eog_mastery_update_data["值"][i]
        eog_mastery_update_data_organized["项目"].append(eog_mastery_update_header[key])
        eog_mastery_update_data_organized["Items"].append(key)
        eog_mastery_update_data_organized["值"].append(value)
    eog_mastery_update_df: pandas.DataFrame = pandas.DataFrame(data = eog_mastery_update_data_organized)
    return eog_mastery_update_df

async def sort_eog_stat_lol_metadata(connection: Connection) -> pandas.DataFrame:
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_source}
    eog_stats_block: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
    eog_stat_metadata_lol_header_keys: list[str] = list(eog_stat_metadata_lol_header.keys())
    eog_stat_metadata_lol: dict[str, list[Any]] = {"项目": [], "Items": [], "值": []}
    if not (isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block):
        LoLGame_info: dict[str, Any] = await (await connection.request("GET", "/lol-match-history/v1/games/%d" %(eog_stats_block["gameId"]))).json()
        for i in range(len(eog_stat_metadata_lol_header_keys)):
            key: str = eog_stat_metadata_lol_header_keys[i]
            eog_stat_metadata_lol["项目"].append(eog_stat_metadata_lol_header[key])
            eog_stat_metadata_lol["Items"].append(key)
            if i <= 46:
                if i == 41: #对局结算时间（`endOfGameTime`）
                    value: Any = getISOTime(eog_stats_block["endOfGameTimestamp"] / 1000)
                elif i == 42: #持续时长（`gameLength_norm`）
                    value = lcuTime(eog_stats_block["gameLength"])
                elif i == 43: #新的召唤师技能名称（`newSpellNames`）
                    value = list(map(lambda x: spells[x]["name"] if x in spells else "", eog_stats_block["newSpells"]))
                elif i == 44: #下次首胜剩余时间（`timeUntilNextFirstWinBonus_norm`）
                    cooldown: int = eog_stats_block["timeUntilNextFirstWinBonus"]
                    cooldown_hour: int = cooldown // 3600
                    cooldown_minute: int = cooldown // 3600 % 60
                    cooldown_second: int = cooldown % 60
                    value = "%d:%02d:%02d" %(cooldown_hour, cooldown_minute, cooldown_second)
                elif i == 45: #队列序号（`queueId`）
                    value = "" if isinstance(LoLGame_info, dict) and "errorCode" in LoLGame_info else LoLGame_info["queueId"]
                elif i == 46: #游戏模式名称（`gameModeName`）
                    value = "" if isinstance(LoLGame_info, dict) and "errorCode" in LoLGame_info else "自定义" if LoLGame_info["queueId"] == 0 else gameQueues[LoLGame_info["queueId"]]["name"]
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
    eog_stat_metadata_lol_statistics_output_order: list[int] = [13, 15, 46, 17, 6, 45, 34, 35, 16, 14, 42, 8, 41, 32, 33, 3, 24, 18, 40, 23, 9, 5, 10, 29, 22, 30, 31, 20, 2, 1, 21, 37, 11, 39, 44, 0, 55, 54, 51, 52, 56, 57, 53, 64, 62, 63, 61, 58, 65, 59, 60, 28, 43, 4, 7, 38, 12, 19, 25, 26, 27, 47, 48, 49, 50]
    eog_stat_metadata_lol_organized: dict[str, list[Any]] = {"项目": [], "Items": [], "值": []}
    for i in eog_stat_metadata_lol_statistics_output_order:
        key: str = eog_stat_metadata_lol_header_keys[i]
        value: Any = eog_stat_metadata_lol["值"][i]
        eog_stat_metadata_lol_organized["项目"].append(eog_stat_metadata_lol_header[key])
        eog_stat_metadata_lol_organized["Items"].append(key)
        eog_stat_metadata_lol_organized["值"].append(value)
    eog_stat_metaDf_lol = pandas.DataFrame(data = eog_stat_metadata_lol_organized)
    return eog_stat_metaDf_lol

async def sort_eog_teamstat_lol_data(connection: Connection) -> pandas.DataFrame:
    eog_teamstat_data_lol_header_keys: list[str] = list(eog_teamstat_data_lol_header.keys())
    eog_teamstat_data_lol: dict[str, Any] = {key: [] for key in eog_teamstat_data_lol_header_keys}
    eog_stats_block: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
    if not (isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block):
        for team in eog_stats_block["teams"]:
            stats: dict[str, int] = team["stats"]
            for i in range(len(eog_teamstat_data_lol_header_keys)):
                key: str = eog_teamstat_data_lol_header_keys[i]
                if i <= 8:
                    if i == 8: #阵营（`team`）
                        to_append: Any = team_colors_int[team["teamId"]]
                    else:
                        to_append = team[key]
                else:
                    if i in [12, 13, 19, 83, 107, 108]: #逻辑值键（Keys with boolean values）
                        to_append = False if stats == None else bool(stats.get(key.split()[1], 0))
                    elif i == 109: #队伍击杀得分（`stats KDA`）
                        to_append = "" if stats == None else "%d/%d/%d" %(stats["CHAMPIONS_KILLED"], stats["NUM_DEATHS"], stats["ASSISTS"]) if all(map(lambda x: x in stats, ["CHAMPIONS_KILLED", "NUM_DEATHS", "ASSISTS"])) else ""
                    else:
                        to_append = "" if stats == None else stats.get(key.split()[1], "")
                eog_teamstat_data_lol[key].append(to_append)
    eog_teamstat_data_lol_statistics_output_order: list[int] = [7, 8, 2, 1, 5, 6, 0, 4, 3, 18, 109, 11, 31, 9, 16, 17, 85, 96, 88, 59, 21, 99, 86, 58, 20, 98, 15, 87, 89, 90, 94, 95, 92, 93, 60, 22, 100, 91, 103, 106, 105, 80, 104, 14, 23, 24, 26, 25, 101, 10, 84, 27, 28, 29, 30, 97, 81, 82, 107, 83, 12, 13, 108, 19, 102]
    eog_teamstat_data_lol_organized: dict[str, list[Any]] = {eog_teamstat_data_lol_header_keys[i]: eog_teamstat_data_lol[eog_teamstat_data_lol_header_keys[i]] for i in eog_teamstat_data_lol_statistics_output_order}
    eog_teamstat_df_lol = pandas.DataFrame(data = eog_teamstat_data_lol_organized)
    optimize_bool_display(eog_teamstat_df_lol)
    eog_teamstat_df_lol = pandas.concat([pandas.DataFrame([eog_teamstat_data_lol_header])[eog_teamstat_df_lol.columns], eog_teamstat_df_lol], ignore_index = True)
    return eog_teamstat_df_lol

async def sort_eog_stat_tft_metadata(connection: Connection) -> pandas.DataFrame:
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_source}
    tft_eog_stats: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
    eog_stat_metadata_tft_header_keys: list[str] = list(eog_stat_metadata_tft_header.keys())
    eog_stat_metadata_tft: dict[str, list[Any]] = {"项目": [], "Items": [], "值": []}
    if not (isinstance(tft_eog_stats, dict) and "errorCode" in tft_eog_stats):
        for i in range(len(eog_stat_metadata_tft_header_keys)):
            key: str = eog_stat_metadata_tft_header_keys[i]
            eog_stat_metadata_tft["项目"].append(eog_stat_metadata_tft_header[key])
            eog_stat_metadata_tft["Items"].append(key)
            if i <= 6:
                if i == 2: #排位赛（`isRanked`）
                    value: Any = "√" if tft_eog_stats["isRanked"] else ""
                elif i == 5: #持续时长（`gameLength_norm`）
                    value = lcuTime(tft_eog_stats["gameLength"])
                elif i == 6: #游戏模式名称（`gameModeName`）
                    value = "" if tft_eog_stats["queueId"] == 0 else gameQueues[tft_eog_stats["queueId"]]["name"]
                else:
                    value = tft_eog_stats[key]
            else:
                subkey1, subkey2 = key.split()
                value = tft_eog_stats[subkey1][subkey2]
            eog_stat_metadata_tft["值"].append(value)
    eog_stat_metadata_tft_statistics_output_order: list[int] = [0, 6, 3, 4, 2, 1, 5, 11, 12, 7, 8, 10, 9]
    eog_stat_metadata_tft_organized: dict[str, list[Any]] = {"项目": [], "Items": [], "值": []}
    for i in eog_stat_metadata_tft_statistics_output_order:
        key: str = eog_stat_metadata_tft_header_keys[i]
        value: Any = eog_stat_metadata_tft["值"][i]
        eog_stat_metadata_tft_organized["项目"].append(eog_stat_metadata_tft_header[key])
        eog_stat_metadata_tft_organized["Items"].append(key)
        eog_stat_metadata_tft_organized["值"].append(value)
    eog_stat_metaDf_tft = pandas.DataFrame(data = eog_stat_metadata_tft_organized)
    return eog_stat_metaDf_tft

async def endOfGame_simulation(connection: Connection) -> str:
    while True:
        logPrint("请选择一个操作：\nPlease select an operation:\n1\t查看英雄成就点数更新情况（Check champion mastery updates）\n2\t查看计分板数据（Check stats block）\n3\t聊天（Chat）\n4\t举报一名玩家（Report a player）\n5\t再来一局（Play again）\n6\t离开（Dismiss）\n!7\t唤起赞誉投票界面（Recall honor vote phase）\n8\t其它（Others）\n9\t客户端任务管理（Manage the League Client task）")
        option: str = logInput()
        if option == "":
            continue
        elif option == "-1":
            logPrint('请选择一个对局结算阶段相关的接口。输入“0”以返回上一层。输入“-1”以自定义接口。\nPlease select an EndOfGame-related API. Submit "0" to return to the last step. Submit "-1" to customize the API.\n-1\t自定义接口（Customize API）\n0\t返回上一层（Return to the last step）\n1\t查看英雄联盟对局结算阶段的英雄成就更新情况（Check the champion mastery update at the end of a LoL game）\n2\t查看英雄联盟对局结算阶段的对局统计（Check game stats at the end of a LoL game）\n3\t查看客户端存储的对局结算阶段的对局统计结果（Check the game stats stored client-side at the end of a game）\n4\t修改客户端存储的对局结算阶段的对局统计结果（Change the game stats stored client-side at the end of a game）\n5\t退出对局结算阶段并返回大厅（Exit the end of a game and return to the home page）\n6\t查看云顶之弈对局结算阶段的对局统计（Check the game stats at the end of a TFT game）')
            while True:
                suboption: str = logInput()
                if suboption == "":
                    continue
                elif suboption == "-1":
                    await send_commands(connection, log = log)
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
                            body_str: str = logInput()
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
            gameflow_phase: str = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                mastery_updates: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/champion-mastery-updates")).json()
                if isinstance(mastery_updates, dict) and "errorCode" in mastery_updates:
                    logPrint(mastery_updates)
                    if mastery_updates["httpStatus"] == 404 and mastery_updates["message"] == "Champion mastery data is not currently available.":
                        logPrint("英雄成就更新数据目前不可用。请确保您现在处于匹配对局的结算阶段。\nChampion mastery data isn't available currently. Please make sure you're at the end of a matchmade game.")
                    else:
                        logPrint("未知错误。\nUnknown error.")
                else:
                    logPrint("本场对局的英雄成就数据如下：\nChampion mastery data of this game are as follows:")
                    eog_mastery_update_df: pandas.DataFrame = await sort_eog_champion_mastery_update(connection)
                    print(format_df(eog_mastery_update_df)[0])
                    log.write(format_df(eog_mastery_update_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "2":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase in {"PreEndOfGame", "EndOfGame"}:
                gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                if gameflow_session["map"]["mapStringId"] == "TFT":
                    tft_eog_stats: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
                    if isinstance(tft_eog_stats, dict) and "errorCode" in tft_eog_stats:
                        logPrint(tft_eog_stats)
                        if tft_eog_stats["httpStatus"] == 404 and tft_eog_stats["message"] == "Game Client stats not found":
                            logPrint("当前游戏模式无法查看云顶之弈对局数据。\nThe current game mode doesn't provide TFT game stats.")
                        else:
                            logPrint("未知错误。\nUnknown error.")
                    else:
                        gameId: int = tft_eog_stats["gameId"]
                        eog_stat_metaDf_tft: panads.DataFrame = await sort_eog_stat_tft_metadata(connection)
                        eog_stat_df_tft: pandas.DataFrame = await sort_eog_stat_tft_data(connection, summonerIcons)
                        eog_stat_df_tft_fields_to_export: list[str] = ["isLocalPlayer", "summonerName", "riotIdGameName", "riotIdTagLine", "summonerId", "puuid", "icon title", "setCoreName", "isInteractable", "partnerGroupId", "companion speciesName", "companion colorName", "health", "rank", "playbook name", "customAugmentContainer description", "customAugmentContainer displayName", "augment1 name", "augment2 name", "augment3 name", "unit0 name", "unit0 price", "unit0 level", "unit0 traits", "unit0 item0 name", "unit0 item1 name", "unit0 item2 name", "unit1 name", "unit1 price", "unit1 level", "unit1 traits", "unit1 item0 name", "unit1 item1 name", "unit1 item2 name", "unit2 name", "unit2 price", "unit2 level", "unit2 traits", "unit2 item0 name", "unit2 item1 name", "unit2 item2 name", "unit3 name", "unit3 price", "unit3 level", "unit3 traits", "unit3 item0 name", "unit3 item1 name", "unit3 item2 name", "unit4 name", "unit4 price", "unit4 level", "unit4 traits", "unit4 item0 name", "unit4 item1 name", "unit4 item2 name", "unit5 name", "unit5 price", "unit5 level", "unit5 traits", "unit5 item0 name", "unit5 item1 name", "unit5 item2 name", "unit6 name", "unit6 price", "unit6 level", "unit6 traits", "unit6 item0 name", "unit6 item1 name", "unit6 item2 name", "unit7 name", "unit7 price", "unit7 level", "unit7 traits", "unit7 item0 name", "unit7 item1 name", "unit7 item2 name", "unit8 name", "unit8 price", "unit8 level", "unit8 traits", "unit8 item0 name", "unit8 item1 name", "unit8 item2 name", "unit9 name", "unit9 price", "unit9 level", "unit9 traits", "unit9 item0 name", "unit9 item1 name", "unit9 item2 name", "unit10 name", "unit10 price", "unit10 level", "unit10 traits", "unit10 item0 name", "unit10 item1 name", "unit10 item2 name"]
                        eog_stat_df_tft_export: pandas.DataFrame = eog_stat_df_tft.loc[:, eog_stat_df_tft_fields_to_export].transpose()
                        excel_name: str = "EndOfGame Stats of %s-%d.xlsx" %(platformId, gameId)
                        while True:
                            try:
                                with pandas.ExcelWriter(path = excel_name) as writer:
                                    addDefaultStyle(eog_stat_metaDf_tft).to_excel(excel_writer = writer, sheet_name = "Metadata")
                                    addDefaultStyle(eog_stat_df_tft_export).to_excel(excel_writer = writer, sheet_name = "Player Stats")
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                                logInput()
                            else:
                                break
                        logPrint(f'本场对局结算数据已导出到同目录下的“{excel_name}”中。\nEnd-of-game stats of this match have been exported into {excel_name} under the same folder.')
                else:
                    eog_stats_block: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
                    if isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block:
                        logPrint(eog_stats_block)
                        if eog_stats_block["httpStatus"] == 404 and eog_stats_block["message"] == "No end of game stats available.":
                            logPrint("当前游戏模式无法查看英雄联盟对局数据。\nThe current game mode doesn't provide LoL game stats.")
                        else:
                            logPrint("未知错误。\nUnknown error.")
                    else:
                        gameId: int = eog_stats_block["gameId"]
                        eog_stat_metaDf_lol: pandas.DataFrame = await sort_eog_stat_lol_metadata(connection)
                        eog_teamstat_df_lol: pandas.DataFrame = (await sort_eog_teamstat_lol_data(connection)).transpose()
                        eog_playerstat_df_lol: pandas.DataFrame = await sort_eog_playerstat_lol_data(connection, summonerIcons, spells, perks, perkstyles, CherryAugments)
                        eog_playerstat_df_lol_fields_to_export: list[str] = ["teamId", "team_color", "stats PLAYER_SUBTEAM", "stats playerSubteamColor", "isLocalPlayer", "summonerName", "riotIdGameName", "riotIdTagLine", "summonerId", "puuid", "profileIcon_title", "level", "botPlayer", "leaver", "leaves", "wins", "losses", "championName", "selectedPosition", "detectedTeamPosition", "stats LEVEL", "spell1_name", "spell2_name", "item0_name", "item1_name", "item2_name", "item3_name", "item4_name", "item5_name", "item6_name", "stats role_bound_item name", "stats KDA", "stats PLAYER_AUGMENT_1 nameTRA", "stats PLAYER_AUGMENT_1 rarity", "stats PLAYER_AUGMENT_2 nameTRA", "stats PLAYER_AUGMENT_2 rarity", "stats PLAYER_AUGMENT_3 nameTRA", "stats PLAYER_AUGMENT_3 rarity", "stats PLAYER_AUGMENT_4 nameTRA", "stats PLAYER_AUGMENT_4 rarity", "stats PLAYER_AUGMENT_5 nameTRA", "stats PLAYER_AUGMENT_5 rarity", "stats PLAYER_AUGMENT_6 nameTRA", "stats PLAYER_AUGMENT_6 rarity", "stats CHAMPIONS_KILLED", "stats NUM_DEATHS", "stats ASSISTS", "stats LARGEST_KILLING_SPREE", "stats LARGEST_MULTI_KILL", "stats TOTAL_TIME_CROWD_CONTROL_DEALT", "stats TIME_CCING_OTHERS", "stats TOTAL_DAMAGE_DEALT_TO_CHAMPIONS", "stats PHYSICAL_DAMAGE_DEALT_TO_CHAMPIONS", "stats MAGIC_DAMAGE_DEALT_TO_CHAMPIONS", "stats TRUE_DAMAGE_DEALT_TO_CHAMPIONS", "stats TOTAL_DAMAGE_DEALT", "stats PHYSICAL_DAMAGE_DEALT_PLAYER", "stats MAGIC_DAMAGE_DEALT_PLAYER", "stats TRUE_DAMAGE_DEALT_PLAYER", "stats LARGEST_CRITICAL_STRIKE", "stats TOTAL_DAMAGE_DEALT_TO_BUILDINGS", "stats TOTAL_DAMAGE_DEALT_TO_OBJECTIVES", "stats TOTAL_DAMAGE_DEALT_TO_TURRETS", "stats TOTAL_HEAL", "stats TOTAL_HEAL_ON_TEAMMATES", "stats TOTAL_DAMAGE_SHIELDED_ON_TEAMMATES", "stats TOTAL_DAMAGE_TAKEN", "stats PHYSICAL_DAMAGE_TAKEN", "stats MAGIC_DAMAGE_TAKEN", "stats TRUE_DAMAGE_TAKEN", "stats TOTAL_DAMAGE_SELF_MITIGATED", "stats VISION_SCORE", "stats WARD_PLACED", "stats WARD_KILLED", "stats SIGHT_WARDS_BOUGHT_IN_GAME", "stats VISION_WARDS_BOUGHT_IN_GAME", "stats GOLD_EARNED", "stats MINIONS_KILLED", "stats NEUTRAL_MINIONS_KILLED", "stats NEUTRAL_MINIONS_KILLED_YOUR_JUNGLE", "stats NEUTRAL_MINIONS_KILLED_ENEMY_JUNGLE", "stats TURRETS_KILLED", "stats BARRACKS_KILLED", "stats TEAM_OBJECTIVE", "stats NODE_CAPTURE", "stats NODE_CAPTURE_ASSIST", "stats NODE_NEUTRALIZE", "stats NODE_NEUTRALIZE_ASSIST", "stats TOTAL_TIME_SPENT_DEAD", "stats PERK_PRIMARY_STYLE name", "stats PERK_SUB_STYLE name", "stats PERK0 name", "stats PERK0 EndOfGameStatDescs", "stats PERK1 name", "stats PERK1 EndOfGameStatDescs", "stats PERK2 name", "stats PERK2 EndOfGameStatDescs", "stats PERK3 name", "stats PERK3 EndOfGameStatDescs", "stats PERK4 name", "stats PERK4 EndOfGameStatDescs", "stats PERK5 name", "stats PERK5 EndOfGameStatDescs", "stats SPELL1_CAST", "stats SPELL2_CAST", "stats WAS_AFK", "stats TEAM_EARLY_SURRENDERED", "stats GAME_ENDED_IN_EARLY_SURRENDER", "stats GAME_ENDED_IN_SURRENDER", "stats WIN", "stats LOSE", "stats PLAYER_SUBTEAM_PLACEMENT", "stats VICTORY_POINT_TOTAL"]
                        eog_playerstat_df_lol_export: pandas.DataFrame = eog_playerstat_df_lol.loc[:, eog_playerstat_df_lol_fields_to_export].transpose()
                        excel_name: str = "EndOfGame Stats of %s-%d.xlsx" %(platformId, gameId)
                        while True:
                            try:
                                with pandas.ExcelWriter(path = excel_name) as writer:
                                    addDefaultStyle(eog_stat_metaDf_lol).to_excel(excel_writer = writer, sheet_name = "Metadata")
                                    addDefaultStyle(eog_teamstat_df_lol).to_excel(excel_writer = writer, sheet_name = "Team Stats")
                                    addDefaultStyle(eog_playerstat_df_lol_export).to_excel(excel_writer = writer, sheet_name = "Player Stats")
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                                logInput()
                            else:
                                break
                        logPrint(f'本场对局结算数据已导出到同目录下的“{excel_name}”中。\nEnd-of-game stats of this match have been exported into {excel_name} under the same folder.')
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "3":
            await chat(connection)
        elif option[0] == "4":
            await report_player_endOfGame(connection)
        elif option[0] == "5":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/play-again")).json()
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
                        break
                    else:
                        logPrint("服务器接收到了再来一局的请求，但您的状态似乎发生了异常。\nThe server received your play-again request, but it seems that an error has occurred to your gameflow phase.")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "6":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-end-of-game/v1/state/dismiss-stats")).json() #这个接口比下面注释起来的接口更有效一些（This endpoint is more effective than the following commented one）
                # response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/play-again-decline")).json()
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
                        return ""
                    else:
                        logPrint("服务器接收到了返回大厅的请求，但您的状态似乎发生了异常。\nThe server received your dismiss-stats request, but it seems that an error has occurred to your gameflow phase.")
            else:
                logPrint("您不在对局结算阶段。\nYou're not at the end of a game right now.")
        elif option[0] == "7":
            gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "EndOfGame":
                honor_ballot: dict[str, Any] = await (await connection.request("GET", "/lol-honor-v2/v1/ballot")).json()
                if isinstance(honor_ballot, dict) and "errorCode" in honor_ballot:
                    logPrint(honor_ballot)
                    logPrint("荣誉投票信息获取异常。\nAn error occurred when getting the honor ballot information.")
                else:
                    eligiblePlayers: list[dict[str, Any]] = honor_ballot["eligibleAllies"] + honor_ballot["eligibleOpponents"]
                    if len(eligiblePlayers) == 0:
                        logPrint("目前没有玩家可以赞誉，因此您无法唤起荣誉投票阶段。\nThere's not any player eligible to honor, so you can't recall the honor ballot vote phase.")
                    else:
                        player_summonerId: int = eligiblePlayers[0]["summonerId"]
                        player_puuid: str = eligiblePlayers[0]["puuid"]
                        honorType: str = "HEART" #取值（Available values）：COOL、SHOTCALLER、HEART
                        gameId: int = honor_ballot["gameId"]
                        body: dict[str, Any] = {"summonerId": player_summonerId, "puuid": player_puuid, "honorType": honorType, "gameId": gameId}
                        logPrint(body)
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-honor-v2/v1/honor-player", data = body)).json()
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
        elif option[0] == "8":
            logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）''')
            while True:
                suboption: str = logInput()
                if suboption[0] == "0":
                    break
                elif suboption[0] == "1":
                    return await display_current_info(connection)
                elif suboption[0] == "2":
                    return await debug_gameflow_phase(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint('''请选择一个子操作：\nPlease select a suboption:\n0\t返回上一层（Return to the last step）\n1\t显示当前召唤师信息（Display current summoner's information）\n2\t调试游戏状态（Debug a gameflow phase）''')
        elif option[0] == "9":
            await manage_ux(connection)
    return ""

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    global sgpSession, log, logInput, logPrint, collection_df_refresh, skin_df_refresh
    await sgpSession.init(connection)
    log_folder: str = "日志（Logs）/Customized Program 21 - Manipulate Gameflow"
    os.makedirs(log_folder, exist_ok = True)
    currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log = LogManager(os.path.join(log_folder, currentTime + ".log"), mode = "a+", encoding = "utf-8")
    logInput = log.logInput
    logPrint = log.logPrint
    print("声明：该脚本只作为辅助客户端的工具。您也许在客户端无法正常响应时可以使用该脚本。\nDeclaration: This program is only regarded as an auxillary tool. It may be useful when the League Client doesn't respond as expected.")
    data_resources_prepared: bool = False
    exit_program: bool = False
    gameflow_debug_enabled: bool = False
    gameflow_phase_toggle: str = "" #仅用于在各游戏状态函数内切换游戏状态（Only used for gameflow phase toggle inside each gameflow phase function）
    client_ready: bool = False
    while True:
        if not client_ready: #这里认为当客户端加载完成后，非插件型数据资源——英雄数据不可能失效了。即使失效，从程序认为账号状态已就绪到获取英雄数据资源窗口也非常短暂，基本可以忽略不计（Here we assume that once the client is ready, non-plugin data resources - champion data - can't be invalid anymore. Even if it does, the time window from when the program finds the account is ready to when it sends the request to get champion data is very short and can be basically ignored）
            client_ready = await check_account_ready(connection)
        if client_ready:
            if not data_resources_prepared:
                logPrint("正在准备数据资源……\nPreparing data resources ...")
                await prepare_data_resources(connection)
                data_resources_prepared = True
            if gameflow_debug_enabled:
                gameflow_phase: str = ALL_GAMEFLOW_PHASES[gameflow_phase_index] if gameflow_phase_toggle == "" else gameflow_phase_toggle
                logPrint(f"正在调试的游戏状态（Debugging gameflow phase）：{gameflow_phase}")
            else:
                gameflow_phase = await get_gameflow_phase(connection)
            if gameflow_phase == "None":
                gameflow_phase_toggle = await gameflow_phase_transition(connection)
            elif gameflow_phase == "Lobby":
                logPrint("检测到您在房间内。\nDetected you're currently in a party/lobby.")
                gameflow_phase_toggle = await lobby_simulation(connection)
            elif gameflow_phase == "Matchmaking":
                logPrint("您正在寻找对局。\nYou're searching for a match.")
                gameflow_phase_toggle = await inQueue_simulation(connection)
            elif gameflow_phase == "ReadyCheck":
                logPrint("对局已找到。\nA match has been found.")
                gameflow_phase_toggle = await readyCheck_simulation(connection)
            elif gameflow_phase == "ChampSelect":
                logPrint("您正处于英雄选择阶段。\nYou're during a champ select stage.")
                gameflow_phase_toggle = await champ_select_simulation(connection)
            elif gameflow_phase == "InProgress":
                logPrint("您正在游戏中。\nYou're currently in a game.")
                gameflow_phase_toggle = await inGame_simulation(connection)
            elif gameflow_phase == "WaitingForStats":
                logPrint('''正在等待赛后数据。输入开头不是“0”的字符串以跳过等待，直接开始下一局游戏。\nWaiting for the game stats. Submit any string that doesn't start with "0" to skip waiting for stats.''')
                while True:
                    skip = logInput()
                    if skip == "":
                        continue
                    elif skip[0] == "0":
                        gameflow_phase_toggle = ""
                        break
                    else:
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-end-of-game/v1/state/dismiss-stats")).json()
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
                gameflow_phase_toggle = await preEndOfGame_simulation(connection)
            elif gameflow_phase == "EndOfGame":
                gameflow_phase_toggle = await endOfGame_simulation(connection)
            elif gameflow_phase == "Reconnect" or gameflow_phase == "FailedToLaunch":
                logPrint("检测到您中途退出游戏。输入任意非空字符串以重连，否则不重连。\nThe program detected you're out of game now. Submit any non-empty string to reconnect, or null to refuse reconnecting.")
                reconnect_str: str = logInput()
                reconnect: bool = bool(reconnect_str)
                if reconnect:
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-gameflow/v1/reconnect")).json()
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
                    gameflow_phase_toggle = ""
                else:
                    gameflow_phase_toggle = await inGame_simulation(connection)
            else: #gameflow_phase in {"TerminatedInError", "FailedToLaunch", "GameStart", "CheckedIntoTournament"}
                logPrint(f"当前游戏状态（Current gameflow phase）：{gameflow_phase}")
                gameflow_phase_toggle = ""
                pass
        else:
            logPrint("您的客户端未加载完成。您将只能使用以下操作。\nYour client hasn't been completely loaded. You'll only be allowed to use the following functions.")
            await unlogged_actions(connection)
        gameflow_debug_enabled = False
        if gameflow_phase_toggle == "":
            logPrint('按回车键以继续，输入开头是“0”的字符串以退出程序，或者输入任意其它非空字符串以更新数据资源。\nPress Enter to continue, submit any string that starts with "0" to exit the program, or submit any other non-empty string to reload data resources.')
            exit_program_str: str = logInput()
            exit_program: bool = exit_program_str != "" and exit_program_str[0] == "0"
            if exit_program_str != "" and exit_program_str[0] != "0":
                if exit_program_str.lower() in list(map(lambda x: x.lower(), ALL_GAMEFLOW_PHASES)):
                    data_resources_prepared = True
                    gameflow_phase_index: int = list(map(lambda x: x.lower(), ALL_GAMEFLOW_PHASES)).index(exit_program_str.lower())
                    gameflow_phase_debug: str = ALL_GAMEFLOW_PHASES[gameflow_phase_index]
                    gameflow_debug_enabled = True
                else:
                    data_resources_prepared = False
                    collection_df_refresh = skin_df_refresh = True
            if exit_program:
                break
        else:
            gameflow_debug_enabled = True
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
