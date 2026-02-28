from lcu_driver import Connector
from lcu_driver.connection import Connection
import argparse, os, pandas, psutil, time, win32com.client
from typing import Any
from src.utils.summoner import get_summoner_data, get_info, get_info_name, sort_summoner_info
from src.utils.logger import LogManager
from src.utils.format import optimize_bool_display, format_df, normalize_file_name, verify_uuid
from src.utils.webRequest import requestUrl, SGPSession
from src.utils.runtimeDebug import subscope
from src.core.config.const import BOT_UUID
from src.core.config.conditional_formatting import addFormat_LoLPlayer_summary_wb, addFormat_LoLGame_info_wb, addFormat_LoLGame_info_wb_transpose
from src.core.config.headers import TFTGame_info_header as TFTGame_stat_header
from src.core.dataframes.matchHistory import get_LoLHistory, get_LoLGame_info, get_game_info_sgp, sort_LoLGame_info, sort_LoLGame_info_sgp, get_TFTHistory, sort_TFTGame_info
from src.core.dataframes.gameflow import sort_ChampSelect_players, sort_inGame_players, sort_postgame_players_lol, sort_eog_playerstat_lol_data, sort_eog_stat_tft_data
from src.core.dataframes.gameMode import sort_queue_data
from src.core.dataframes.ranked import sort_game_leaderboard

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--lol_api", help = "指定通过什么接口获取英雄联盟对局信息和时间轴（Specify the interface used to fetch LoL game information and timeline）", action = "store", type = str, choices = ["lcu", "sgp"], default = "lcu")
parser.add_argument("-c", "--count", help = "指定每个召唤师查询的默认对局数量（Specify the default number of matches to search for each summoner）", action = "store", type = int, default = 20)
parser.add_argument("-e", "--save_early", help = "只导出早于查询对局的对局（Export only the matches whose creation is earlier than the current queried match）", action = "store_true")
parser.add_argument("-l", "--locale", help = "选择非《英雄联盟》本地化内容的显示语言（Choose the display language that isn't part of League of Legends localization content）", action = "store")
parser.add_argument("-os", "--open_after_save", help = "在成功保存文件后，跳过程序询问，直接打开该文件（Once the workbook is saved successfully, directly open this workbook without program asking）", action = "store_true")
parser.add_argument("-q", "--queues", help = "通过队列序号指定要查询的游戏模式（Specify the game modes to query by queueIds）", action = "append", type = int, default = [])
parser.add_argument("--verbose", help = "显示详细加载进度（Display detailed loading process）", action = "store_true")
parser.add_argument("--nonverbose", help = "显示简略加载进度（Display simplified loading process）", action = "store_true")
args = parser.parse_args()
use_sgp: bool = args.lol_api == "sgp"
if use_sgp:
    from src.core.config.headers import LoLGame_info_sgp_header as LoLGame_stat_header
else:
    from src.core.config.headers import LoLGame_info_header as LoLGame_stat_header
if args.locale == "en_US":
    arg_locale = "en_US" #只影响常量字典的本地化（Only influences the localization of the constant dictionaries）
else:
    arg_locale = "zh_CN"
if args.verbose:
    print_detail: bool = True
elif args.nonverbose:
    print_detail = False
else:
    print("是否输出具体加载进度？（输入任意键以输出具体过程，否则输出简略过程。）\nDo you want the program to output the loading process in details? (Submit any non-empty string to output the detailed process, or null to output the simplified process.)")
    print_detail = bool(input())

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/02/14
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

wd: str = os.getcwd()
queueId_options: dict[str, dict[str, str]] = {"#1": {"description": "所有玩家对战（All PvP games）", "expression": '[queue["id"] for queue in queue_souce if queue["category"] == "PvP"]'}, "#2": {"description": "所有英雄联盟玩家对战（All LoL PvP games）", "expression": '[queue["id"] for queue in queue_souce if queue["category"] == "PvP" and queue["mapId"] != 22]'}, "#3": {"description": "所有云顶之弈玩家对战（All TFT PvP games）", "expression": '[queue["id"] for queue in queue_souce if queue["category"] == "PvP" and queue["mapId"] == 22]'}, "#4": {"description": "所有召唤师峡谷排位队列（All Summoner's Rift ranked queues）", "expression": '[queue["id"] for queue in queue_souce if queue["isRanked"] and queue["mapId"] == 11]'}, "#5": {"description": "所有云顶之弈排位队列（All TFT ranked queues）", "expression": '[queue["id"] for queue in queue_souce if queue["isRanked"] and queue["mapId"] == 22]'}}
created_processes: list[psutil.Process] = [] #标记清理残留进程（Stores processes to clear at the end of the program）

sgpSession: SGPSession = SGPSession()
queues: dict[int, dict[str, Any]] = {}
spells: dict[int, dict[str, Any]] = {}
LoLChampions: dict[int, dict[str, Any]] = {}
championSkins: dict[int, dict[str, Any]] = {}
LoLItems: dict[int, dict[str, Any]] = {}
summonerIcons: dict[int, dict[str, Any]] = {}
perks: dict[int, dict[str, Any]] = {}
perkstyles: dict[int, dict[str, Any]] = {}
TFTAugments: dict[str, dict[str, Any]] = {}
TFTChampions: dict[str, dict[str, Any]] = {}
TFTItems: dict[str, dict[str, Any]] = {}
TFTCompanions: dict[str, dict[str, Any]] = {}
TFTTraits: dict[str, dict[str, Any]] = {}
CherryAugments: dict[int, dict[str, Any]] = {}
wardSkins: dict[int, dict[str, Any]] = {}
regaliaBanners: dict[str, dict[str, Any]]
log: LogManager = LogManager()

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 汇总英雄选择阶段或游戏内玩家的战绩（Summarize players' stats in recent matches during champ select stage or in game）
#-----------------------------------------------------------------------------
def check_proc_trees(pids: list[int]) -> pandas.DataFrame: #查看本程序创建的所有进程及其子进程（Check all processes and subprocess created by this program）
    process_header: dict[str, str] = {"No.": "序号", "pid": "进程号", "name": "名称", "createTime": "进程创建时间", "status": "状态"}
    process_header_keys: list[str] = list(process_header.keys())
    process_data: dict[str, list[Any]] = {key: [] for key in process_header_keys}
    for i in range(len(pids)):
        pid: int = pids[i]
        count: int = 0
        try:
            parent: psutil.Process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            pass
        else:
            count += 1
            for j in range(len(process_header_keys)):
                key: str = process_header_keys[j]
                if j == 0: #序号（`No.`）
                    to_append: Any = "%d.%d" %(i + 1, count)
                elif j == 3: #进程创建时间（`createTime`）
                    to_append = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(parent.create_time()))
                else:
                    to_append = eval(f"parent.{key}")
                process_data[key].append(to_append)
            for child in parent.children(recursive = True):
                count += 1
                for j in range(len(process_header_keys)):
                    key = process_header_keys[j]
                    if j == 0: #序号（`No.`）
                        to_append: Any = "%d.%d" %(i + 1, count)
                    elif j == 3: #进程创建时间（`createTime`）
                        to_append = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(child.create_time()))
                    else:
                        to_append = eval(f"child.{key}")
                    process_data[key].append(to_append)
    process_df: pandas.DataFrame = pandas.DataFrame(data = process_data)
    process_df = pandas.concat([pandas.DataFrame([process_header])[process_df.columns], process_df], ignore_index = True)
    return process_df

def kill_proc_tree(pid: int, including_parent: bool = True) -> None: #清理残留进程及其子进程（Clear the remaining processes）
    parent: psutil.Process = psutil.Process(pid)
    for child in parent.children(recursive = True):
        child.kill()
    if including_parent:
        parent.kill()

async def prepare_data_resources(connection: Connection, verbose: bool = True) -> None:
    #准备数据资源（Prepare data resources）
    logPrint("正在准备数据资源……\nPreparing data resources ...")
    global queues, spells, LoLChampions, championSkins, LoLItems, summonerIcons, perks, perkstyles, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, CherryAugments, wardSkins, regaliaBanners
    ##游戏模式（Game mode）
    logPrint("正在加载游戏模式信息……\nLoading game mode information ...", verbose = verbose)
    queue_souce: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/queues.json")).json()
    queues = {int(queue_iter["id"]): queue_iter for queue_iter in queue_souce}
    ##召唤师技能（Summoner spell）
    logPrint("正在加载召唤师技能信息……\nLoading summoner spell information ...", verbose = verbose)
    spells_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
    spells = {int(spell_iter["id"]): spell_iter for spell_iter in spells_source}
    ##英雄（Champion）
    logPrint("正在加载英雄信息……\nLoading champion information ...", verbose = verbose)
    LoLChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/champion-summary.json")).json()
    LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampions_source}
    ##皮肤（Champion skin）
    logPrint("正在加载皮肤信息……\nLoading skin information ...", verbose = verbose)
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
    ##英雄联盟装备（LoL item）
    logPrint("正在加载英雄联盟装备信息……\nLoading LoL item information ...", verbose = verbose)
    LoLItems_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/items.json")).json()
    LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItems_source}
    ##召唤师图标（Summoner icon）
    logPrint("正在加载召唤师图标信息……\nLoading summoner icon information ...", verbose = verbose)
    summonerIcons_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcons_source}
    ##符文（Perk）
    logPrint("正在加载基石符文信息……\nLoading perk information ...", verbose = verbose)
    perks_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/perks.json")).json()
    perks = {int(perk_iter["id"]): perk_iter for perk_iter in perks_source}
    ##符文系（Perkstyle）
    logPrint("正在加载符文系信息……\nLoading perkstyle information ...", verbose = verbose)
    perkstyles_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
    perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyles_source["styles"]}
    ##云顶之弈强化符文（TFT augments）
    logPrint("正在加载云顶之弈基础数据……\nLoading TFT basic data from CommunityDragon ...", verbose = verbose)
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    URLPatch: str = "pbe" if platformId == "PBE1" or platformId == "PBE" else "latest"
    region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    locale: str = region_locale["locale"].lower()
    source, status, session = requestUrl("GET", f"https://raw.communitydragon.org/{URLPatch}/cdragon/tft/{locale}.json")
    if status != 200:
        if status == -1:
            logPrint("云顶之弈基础数据获取失败！请检查系统网络状况和代理设置。程序即将退出。\nTFT basic data capture failure! Please check the system network condition and proxy configuration. The program will exit now.")
        elif status == 404:
            logPrint(f'云顶之弈基础数据获取失败！请检查以下链接的可用性。程序即将退出。\nTFT basic data capture failure! Please check the URL availability. The program will exit now.\nhttps://raw.communitydragon.org/{URLPatch}/cdragon/tft/{locale}.json')
        log.write("\n[Program exited with TFT basic data capture failure!]\n")
        log.close()
        time.sleep(3)
        exit()
    TFTBasic_source: dict[str, Any] = source.json()
    TFTAugments = {item["apiName"]: item for item in TFTBasic_source["items"]}
    ##云顶之弈英雄（TFT champion）
    logPrint("正在加载云顶之弈棋子信息……\nLoading TFT champion information ...", verbose = verbose)
    TFTChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftchampions.json")).json()
    TFTChampions = {TFTChampion_iter["name"]: TFTChampion_iter["character_record"] for TFTChampion_iter in TFTChampions_source}
    ##云顶之弈装备（TFT item）
    logPrint("正在加载云顶之弈装备信息……\nLoading TFT item information ...", verbose = verbose)
    TFTItems_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftitems.json")).json()
    TFTItems = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItems_source}
    ##云顶之弈小小英雄（TFT companion）
    logPrint("正在加载云顶之弈小小英雄信息……\nLoading companion information ...", verbose = verbose)
    TFTCompanions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
    TFTCompanions = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanions_source}
    ##云顶之弈羁绊（TFT Trait）
    logPrint("正在加载云顶之弈羁绊信息……\nLoading TFT trait information ...", verbose = verbose)
    TFTTraits_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tfttraits.json")).json()
    TFTTraits = {}
    for trait_iter in TFTTraits_source:
        trait_id = trait_iter["trait_id"]
        conditional_trait_sets = {}
        for conditional_trait_set in trait_iter["conditional_trait_sets"]:
            style_idx = conditional_trait_set["style_idx"]
            conditional_trait_sets[style_idx] = conditional_trait_set
        trait_iter["conditional_trait_sets"] = conditional_trait_sets
        TFTTraits[trait_id] = trait_iter
    ##斗魂竞技场强化符文（Arena augment）
    logPrint("正在加载斗魂竞技场强化符文信息……\nLoading Arena augment information ...", verbose = verbose)
    CherryAugments_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/cherry-augments.json")).json()
    CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugments_source}
    ##饰品（Ward skin）
    logPrint("正在加载守卫（眼）皮肤信息……\nLoading ward skin information ...", verbose = verbose)
    wardSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    wardSkins = {wardSkin_iter["id"]: wardSkin_iter for wardSkin_iter in wardSkins_source}
    ##旗帜（Regalia banner）
    regaliaBanners = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_BANNER")).json()

async def search_player_match_stats_lol(connection: Connection, puuid: str, begIndex: int = 0, endIndex: int = 20, lol_sgp: bool = True, log: LogManager | None = None, verbose: bool = True) -> pandas.DataFrame: #查询某个玩家的对局记录数据（Search for a player's match history stats）
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    LoLGame_stat_header_keys: list[str] = list(LoLGame_stat_header.keys())
    LoLGame_stat_data: dict[str, list[Any]] = {key: [] for key in LoLGame_stat_header_keys}
    info: dict[str, Any] = await get_info(connection, puuid)
    if info["info_got"]:
        LoLHistory_get, LoLHistory = await get_LoLHistory(connection, puuid, begIndex = begIndex, endIndex = endIndex, log = log)
        if LoLHistory_get:
            unmapped_keys: dict[str, set[int]] = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
            for i in range(len(LoLHistory["games"]["games"])):
                matchId: int = LoLHistory["games"]["games"][i]["gameId"]
                match_id: str = f"{platformId}_{matchId}"
                if lol_sgp:
                    status, LoLGame_info = await get_game_info_sgp(connection, sgpSession, match_id, skipTFT = True, log = log)
                else:
                    status, LoLGame_info = await get_LoLGame_info(connection, matchId, log = log)
                if status == 200:
                    #下一行语句的关键是sortStats和LoLGame_stats_data参数（The key point of the following statement is `sortStats` and `LoLGame_stats_data` parameters）
                    if lol_sgp:
                        LoLGame_info_df: pandas.DataFrame = sort_LoLGame_info_sgp(LoLGame_info, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = i + 1, current_puuid = puuid, useAllVersions = False, unmapped_keys = unmapped_keys, sortStats = True, LoLGame_stat_data = LoLGame_stat_data, log = log, verbose = verbose)[0]
                    else:
                        LoLGame_info_df = sort_LoLGame_info(LoLGame_info, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = i + 1, current_puuid = puuid, useAllVersions = False, unmapped_keys = unmapped_keys, sortStats = True, LoLGame_stat_data = LoLGame_stat_data, log = log, verbose = verbose)[0]
                    logPrint("对局加载进度（Match loading process）：%d/%d\t对局序号（matchID）： %d" %(i + 1, len(LoLHistory["games"]["games"]), matchId), verbose = verbose)
                else:
                    logPrint("对局加载进度（Match loading process）：%d/%d\t对局序号（matchID）： %d (Match not found)" %(i + 1, len(LoLHistory["games"]["games"]), matchId), verbose = verbose)
    if lol_sgp:
        LoLGame_stat_statistics_output_order: list[int] = [0, 13, 25, 11, 26, 22, 14, 29, 20, 30, 19, 219, 210, 176, 53, 580, 581, 94, 130, 80, 147, 51, 50, 54, 215, 216, 178, 179, 180, 181, 182, 183, 184, 213, 192, 204, 193, 205, 194, 206, 195, 207, 196, 208, 197, 209, 93, 63, 45, 221, 222, 223, 226, 227, 96, 92, 97, 49, 71, 70, 73, 72, 65, 162, 126, 111, 169, 148, 159, 152, 113, 100, 164, 151, 112, 99, 163, 95, 60, 59, 57, 58, 156, 157, 161, 153, 154, 114, 101, 165, 61, 171, 174, 173, 132, 172, 64, 77, 224, 78, 225, 91, 56, 158, 103, 150, 155, 166, 167, 81, 82, 104, 106, 168, 83, 105, 66, 47, 107, 108, 98, 48, 55, 76, 127, 124, 109, 43, 44, 102, 68, 69, 170, 62, 46, 79, 149, 160, 133, 135, 137, 138, 220, 140, 141, 557, 571, 563, 559, 564, 560, 565, 561, 566, 562, 575, 573, 576, 574, 553, 551, 552, 145, 74, 75, 228, 115, 139, 627, 613, 598, 683, 629, 626, 630, 602, 615, 670, 647, 642, 676, 656, 667, 660, 644, 633, 672, 659, 643, 632, 671, 628, 610, 609, 607, 608, 664, 665, 669, 661, 662, 645, 634, 673, 611, 678, 681, 680, 649, 679, 614, 620, 621, 625, 606, 666, 636, 658, 663, 684, 674, 675, 623, 624, 637, 638, 616, 600, 639, 640, 631, 601, 605, 619, 648, 646, 641, 596, 597, 635, 617, 618, 677, 612, 599, 622, 657, 668, 650, 651, 652, 653, 682, 654, 655, 757, 705, 704, 728, 714, 699, 785, 786, 788, 730, 727, 731, 703, 716, 772, 748, 743, 778, 758, 769, 762, 745, 734, 774, 761, 744, 733, 773, 729, 711, 710, 708, 709, 766, 767, 771, 763, 764, 746, 735, 775, 712, 780, 783, 782, 750, 781, 715, 721, 722, 789, 726, 707, 768, 737, 765, 760, 787, 776, 777, 724, 725, 717, 701, 740, 741, 738, 739, 732, 702, 706, 720, 749, 747, 742, 697, 698, 736, 718, 719, 779, 713, 700, 723, 759, 770, 751, 752, 753, 754, 784, 755, 756, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 372, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 373, 274, 275, 276, 374, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 375, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 376, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521]
    else:
        LoLGame_stat_statistics_output_order = [0, 5, 3, 4, 13, 11, 6, 14, 10, 15, 9, 16, 42, 211, 35, 36, 223, 224, 38, 39, 45, 226, 227, 157, 158, 159, 160, 161, 162, 163, 212, 193, 205, 194, 206, 195, 207, 196, 208, 197, 209, 198, 210, 72, 50, 43, 214, 215, 216, 219, 220, 46, 142, 143, 74, 71, 75, 54, 53, 58, 57, 56, 55, 51, 146, 131, 84, 151, 136, 144, 138, 112, 78, 148, 137, 111, 77, 147, 73, 48, 47, 140, 145, 139, 113, 79, 149, 49, 152, 155, 154, 133, 153, 61, 217, 62, 218, 141, 80, 82, 81, 150, 63, 76, 189, 191, 177, 171, 178, 172, 179, 173, 180, 174, 181, 175, 182, 176, 44, 52, 135, 59, 60, 221, 134, 240, 234, 229, 287, 230, 274, 242, 239, 243, 235, 277, 266, 252, 282, 268, 275, 270, 254, 246, 279, 269, 253, 245, 278, 241, 232, 231, 272, 276, 271, 255, 247, 280, 233, 283, 286, 285, 267, 284, 236, 237, 273, 248, 250, 249, 288, 281, 238, 244, 290, 301, 295, 289, 348, 349, 351, 291, 335, 303, 300, 304, 296, 338, 327, 313, 343, 329, 336, 331, 315, 307, 340, 330, 314, 306, 339, 302, 293, 292, 333, 337, 332, 316, 308, 341, 294, 344, 347, 346, 328, 345, 297, 298, 352, 334, 309, 310, 311, 350, 342, 299, 305] #和查战绩脚本不同，这里为了节省空间占用并突出重要信息，移除了召唤师身份相关键。云顶之弈同（What's different from Customized Program is that here to save space and stress the important information here, summoner information related keys are removed. So does the TFT one）
    LoLGame_stat_data_organized: dict[str, list[Any]] = {LoLGame_stat_header_keys[i]: LoLGame_stat_data[LoLGame_stat_header_keys[i]] for i in LoLGame_stat_statistics_output_order}
    LoLGame_stat_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_stat_data_organized)
    optimize_bool_display(LoLGame_stat_df)
    LoLGame_stat_df = pandas.concat([pandas.DataFrame([LoLGame_stat_header])[LoLGame_stat_df.columns], LoLGame_stat_df], ignore_index = True)
    return LoLGame_stat_df

async def search_player_match_stats_tft(connection: Connection, puuid: str, begin: int = 0, count: int = 20, log: LogManager | None = None, verbose: bool = True) -> pandas.DataFrame:
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    TFTGame_stat_header_keys: list[str] = list(TFTGame_stat_header.keys())
    TFTGame_stat_data: dict[str, list[Any]] = {key: [] for key in TFTGame_stat_header_keys}
    info: dict[str, Any] = await get_info(connection, puuid)
    if info["info_got"]:
        TFTHistory_get, TFTHistory = await get_TFTHistory(connection, puuid, begin = begin, count = count, log = log)
        if TFTHistory_get:
            unmapped_keys: dict[str, set[Any]] = {"queue": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
            for i in range(len(TFTHistory["games"])):
                matchId: int = int(TFTHistory["games"][i]["metadata"]["match_id"].split("_")[-1])
                TFTGame_info: dict[str, Any] = TFTHistory["games"][i]
                if bool(TFTGame_info["json"]):
                    #下一行语句的关键是sortStats和TFTGame_stats_data参数（The key point of the following statement is `sortStats` and `TFTGame_stats_data` parameters）
                    TFTGame_info_df: pandas.DataFrame = (await sort_TFTGame_info(connection, TFTGame_info, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = i + 1, current_puuid = puuid, save_self = True, useAllVersions = False, unmapped_keys = unmapped_keys, useInfoDict = False, sortStats = True, TFTGame_stat_data = TFTGame_stat_data, log = log, verbose = verbose))[0]
                    logPrint("对局加载进度（Match loading process）：%d/%d\t对局序号（matchID）： %d" %(i + 1, len(TFTHistory["games"]), TFTGame_info["json"]["game_id"]), verbose = verbose)
                else:
                    logPrint("对局加载进度（Match loading process）：%d/%d (Exceptional match neglected)" %(i + 1, len(TFTHistory["games"])), verbose = verbose)
                # match_id: str = f"{platformId}_{matchId}"
                # status, TFTGame_info = await get_game_info_sgp(connection, sgpSession, match_id, checkLoL = False, log = log)
                # if status == 200:
                #     if "json" in TFTGame_info and bool(TFTGame_info["json"]):
                #         TFTGame_info_df: pandas.DataFrame = (await sort_TFTGame_info(connection, TFTHistory["games"][i], queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = i + 1, current_puuid = puuid, save_self = True, useAllVersions = False, unmapped_keys = unmapped_keys, useInfoDict = False, sortStats = True, TFTGame_stat_data = TFTGame_stat_data, log = log, verbose = verbose))[0]
                #         logPrint("对局加载进度（Match loading process）：%d/%d\t对局序号（matchID）： %d" %(i + 1, len(TFTHistory["games"]), matchId), verbose = verbose)
                #     else:
                #         logPrint("对局加载进度（Match loading process）：%d/%d\t对局序号（matchID）： %d (Exceptional match neglected)" %(i + 1, len(TFTHistory["games"]), matchId), verbose = verbose)
                # else:
                #     logPrint("对局加载进度（Match loading process）：%d/%d\t对局序号（matchID）： %d (Match not found)" %(i + 1, len(TFTHistory["games"]), matchId), verbose = verbose)
    TFTGame_stat_statistics_output_order: list[int] = [0, 5, 14, 15, 16, 6, 10, 18, 11, 7, 13, 12, 40, 55, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 150, 148, 149, 203, 206, 209, 155, 153, 154, 212, 215, 218, 160, 158, 159, 221, 224, 227, 165, 163, 164, 230, 233, 236, 170, 168, 169, 239, 242, 245, 175, 173, 174, 248, 251, 254, 180, 178, 179, 257, 260, 263, 185, 183, 184, 266, 269, 272, 190, 188, 189, 275, 278, 281, 195, 193, 194, 284, 287, 290, 200, 198, 199, 293, 296, 299, 61, 57, 58, 59, 60, 68, 64, 65, 66, 67, 75, 71, 72, 73, 74, 82, 78, 79, 80, 81, 89, 85, 86, 87, 88, 96, 92, 93, 94, 95, 103, 99, 100, 101, 102, 110, 106, 107, 108, 109, 117, 113, 114, 115, 116, 124, 120, 121, 122, 123, 131, 127, 128, 129, 130, 138, 134, 135, 136, 137, 145, 141, 142, 143, 144]
    TFTGame_stat_data_organized: dict[str, list[Any]] = {TFTGame_stat_header_keys[i]: TFTGame_stat_data[TFTGame_stat_header_keys[i]] for i in TFTGame_stat_statistics_output_order}
    TFTGame_stat_df: pandas.DataFrame = pandas.DataFrame(data = TFTGame_stat_data_organized)
    optimize_bool_display(TFTGame_stat_df)
    TFTGame_stat_df = pandas.concat([pandas.DataFrame([TFTGame_stat_header])[TFTGame_stat_df.columns], TFTGame_stat_df], ignore_index = True)
    return TFTGame_stat_df

def open_workbook(path: str) -> tuple[Any, Any]:
    try:
        excel = win32com.client.GetActiveObject("Excel.Application")
    except: #pywintypes.com_error: (-2147221021, "操作无法使用", None, None)
        excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = True #确保Excel可见（Make Excel visible）
    try:
        workbook = excel.Workbooks.Open(path)
        logPrint(f"成功打开{path}。\n{path} opened successfully.")
        excel.WindowState = -4137
        if excel.ActiveWindow:
            excel.ActiveWindow.WindowState = -4137
        return (excel, workbook)
    except Exception as e:
        logPrint(f"打开工作簿时出错：{e}")
        return (None, None)

async def Clarke_revival(connection: Connection) -> None:
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues_source = sorted(gameQueues_source, key = lambda x: x["id"]) #将队列按照队列序号正序排列（Sort the queues in the ascending order of queueIds）
    gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_source}
    #定义获取到的玩家信息列表。元素是召唤师信息字典，或者说包含必要键的字典（Define a list of obtained summoner information, or a list of dictionaries that contain enough necessary information to tell a summoner）
    fetched_players: list[dict[str, Any]] = []
    #定义标记是否队友信息的字典。键是玩家通用唯一识别码，值是逻辑值（Define a dictionary to mark whether a summoner is an ally. Keys are puuids, and values are boolean values）
    ally_bool_dict: dict[str, bool] = {}
    #总结性工作表呈现所有玩家的信息（Each summary sheets display all players' stats）
    LoLPlayer_stat_summary_dfs: list[pandas.DataFrame] = []
    TFTPlayer_stat_summary_dfs: list[pandas.DataFrame] = []
    #具体数值工作表呈现每个玩家的信息。键是召唤师名，值是数据框（Each detailed sheets display each player's stats. Keys are summonerNames, and values are dataframes）
    LoLPlayer_stat_details_dfs: dict[str, pandas.DataFrame] = {}
    TFTPlayer_stat_details_dfs: dict[str, pandas.DataFrame] = {}
    #仅用于对局后查询的全局变量（Global variables only used for post-match query）
    gameId: int = 0
    isTFT: bool = False
    game_info: dict[str, Any] = {}
    LoLGame_info: dict[str, Any] = {}
    TFTGame_info: dict[str, Any] = {}
    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    gameflow_ongoing: bool = gameflow_phase in {"ChampSelect", "InProgress", "Reconnect", "PreEndOfGame", "EndOfGame"}
    logPrint("请选择运行模式：\nPlease select a mode:\n%s1\t运行时查询（Runtime query）\n%s2\t对局后查询（Post-match query）" %("☆" if gameflow_ongoing else "", "" if gameflow_ongoing else "☆"))
    while True:
        mode: str = logInput()
        if mode == "":
            mode = "1" if gameflow_ongoing else "2"
            break
        elif mode[0] == "0":
            return
        elif mode[0] == "1" or mode[0] == "2":
            mode = mode[0]
            break
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
    #下一段if-else语句的目的：向fetched_players和ally_bool_dict中追加值（Aim of the following if-else part: append values to `fetched_players` and `ally_bool_dict`）
    if mode == "1":
        current_timestamp_millis: float = 1000 * (time.time() - time.localtime().tm_gmtoff)
        #首先获取会话中的玩家信息，包括是否队友（First, get information of the players in the session, including whether they're allies or not）
        if gameflow_phase == "ChampSelect":
            champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            if "errorCode" in champ_select_session:
                if champ_select_session["message"] == "No active delegate": #在没有英雄选择阶段的游戏模式中，有时gameflow_phase的结果是“ChampSelect”，但是实际上没有可用的英雄选择会话（In game modes without champ select stage, sometimes `gameflow_phase` is "ChampSelect", but there's actually no available champ select session）
                    logPrint("英雄选择会话已过期。\nChamp select session has expired.")
                return
            gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
            gameMode: str = gameflow_session["map"]["gameMode"]
            gameModeName: str = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameflow_session["gameData"]["queue"]["id"]) if gameflow_session["gameData"]["queue"]["name"] == "" else gameflow_session["gameData"]["queue"]["name"]
            excel_name: str = "Player Stats in Match %s-%s (%s).xlsx" %(platformId, champ_select_session["gameId"], normalize_file_name(gameModeName))
            isSpectating: bool = champ_select_session["isSpectating"] #从英雄选择会话信息中可以直接得到用户是否在观战（From the champ select session, it can be inferred directly whether the user is spectating）
            if gameflow_session["gameData"]["queue"]["gameMode"] == "CHERRY":
                myTeam_puuids: list[str] = [player["puuid"] for player in champ_select_session["myTeam"] if (player["nameVisibilityType"] == "VISIBLE" or player["nameVisibilityType"] == "") and verify_uuid(player["puuid"])]
            else:
                myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], champ_select_session["myTeam"]))
            for player in champ_select_session["myTeam"] + champ_select_session["theirTeam"]:
                if not player["puuid"] in {current_info["puuid"], "", BOT_UUID} and (player["nameVisibilityType"] == "VISIBLE" or player["nameVisibilityType"] == ""):
                    player_info_recapture: int = 0
                    player_info: dict[str, Any] = await get_info(connection, player["puuid"])
                    while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                        logPrint(player_info["message"], verbose = print_detail)
                        player_info_recapture += 1
                        logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture), verbose = print_detail)
                        player_info = await get_info(connection, player["puuid"])
                    if player_info["info_got"]:
                        player_info_body: dict[str, Any] = player_info["body"]
                        fetched_players.append(player_info_body)
                        ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids #尽管这里将位于“myTeam”中的玩家标记为队友，实际输出提示信息时，首先还是会判断是否观战（Although here all members in "myTeam" are marked allies, when the program prints prompts, it still judges whether the user is spectating）
                    else:
                        logPrint(player_info["message"], verbose = print_detail)
                        logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an player (puuid: %s) capture failed! The program will ignore this player.")
            teamOneOnly: bool = gameflow_session["gameData"]["queue"]["mapId"] in {22, 30} #在斗魂竞技场和云顶之弈中，所有玩家都归入“teamOne”中。这样就无法判断其是否是队友（In an Arena or TFT match, all players are in "teamOne", so the program can't tell whether a player is an ally）
            players_metaDf: pandas.DataFrame = await sort_ChampSelect_players(connection, LoLChampions, championSkins, spells, wardSkins, playerMode = 1, log = log, verbose = print_detail)
        elif gameflow_phase == "InProgress" or gameflow_phase == "Reconnect":
            gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
            gameData: dict[str, Any] = gameflow_session["gameData"]
            gameMode: str = gameflow_session["map"]["gameMode"]
            gameModeName = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameData["queue"]["id"]) if gameData["queue"]["name"] == "" else gameData["queue"]["name"]
            excel_name = "Player Stats in Match %s-%s (%s).xlsx" %(platformId, gameData["gameId"], normalize_file_name(gameModeName))
            isSpectating = False #设置观战逻辑变量，确定游戏会话是不是观战的（This boolean variable is declared to tell whether the game session is spectating）
            teamOne: list[dict[str, Any]] = []
            for player in gameData["teamOne"]: #这里通过循环而不是用map函数快速获取玩家通用唯一识别码列表，是因为电脑玩家没有玩家通用唯一识别码（Here the puuid list is obtained by a loop instead of `map` function, because bot players don't have puuids）
                if "puuid" in player and bool(player["puuid"]): #开了主播模式的玩家的玩家通用唯一识别码是null（The puuid of a player that enables Streamer Mode is null）
                    teamOne.append(player)
            teamTwo: list[dict[str, Any]] = []
            for player in gameData["teamTwo"]:
                if "puuid" in player and bool(player["puuid"]):
                    teamTwo.append(player)
            if current_info["puuid"] in list(map(lambda x: x["puuid"], teamOne)): #API记录游戏中的玩家时，只会区分红蓝方，不会区分敌我。所以这里需要先判断那个阵营是我方（Players recorded in API only differentiate by blue or red team, instead of my or enemy team. So judging the own team or the enemy team is the first thing to do）
                myTeam: list[dict[str, Any]] = teamOne
                theirTeam: list[dict[str, Any]] = teamTwo
            elif current_info["puuid"] in list(map(lambda x: x["puuid"], teamTwo)):
                myTeam = teamTwo
                theirTeam = teamOne
            else:
                myTeam = []
                theirTeam = teamOne + teamTwo
                isSpectating = True
            myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], myTeam))
            for player in myTeam + theirTeam: #注意到这里并没有排除掉用户自己。这是为了校验程序的正确性，将自己作为空白对照（Note that here the program doesn't exclude the user itself. This is designed to verify the correctness of program execution. The user itself acts as control）
                player_info_recapture = 0
                player_info = await get_info(connection, player["puuid"])
                while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                    logPrint(player_info["message"], verbose = print_detail)
                    player_info_recapture += 1
                    logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture), verbose = print_detail)
                    player_info = await get_info(connection, player["puuid"])
                if player_info["info_got"]:
                    player_info_body = player_info["body"]
                    fetched_players.append(player_info_body)
                    ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids
                else:
                    logPrint(player_info["message"], verbose = print_detail)
                    logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名玩家。\nInformation of an player (puuid: %s) capture failed! The program will ignore this player.")
            teamOneOnly = gameData["queue"]["mapId"] in {22, 30} #玩家在API上的阵营划分随对局模式而不同。云顶之弈和斗魂竞技场虽然有多个阵营，但是都是记录在gameData["teamOne"]中，这需要和其它模式区分开来。该条件语句与“if gameData["queue"]["gameMode"] == "TFT" or gameData["queue"]["gameMode"] == "CHERRY"”等价，但是因为召唤师峡谷还能分成CLASSIC、URF等模式，所以这里直接用地图序号作为判断依据（The team where a player belongs varies by the game mode. Although there're actually more than 2 teams in TFT and Arena, all players are recorded in `gameData["teamOne"]`, which needs ditinguishing from other game modes. This conditional statement is equivalent to `if gameData["queue"]["gameMode"] == "TFT" or gameData["queue"]["gameMode"] == "CHERRY"`, but since there're multiple modes based on one map, like CLASSIC and URF based on Summoner's Rift, the mapId is thus taken as the judgment criterium）
            players_metaDf = await sort_inGame_players(connection, LoLChampions, championSkins, summonerIcons, spells, log = log, verbose = print_detail)
        elif gameflow_phase in {"PreEndOfGame", "EndOfGame"}:
            gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
            gameData: dict[str, Any] = gameflow_session["gameData"]
            gameMode: str = gameflow_session["map"]["gameMode"]
            gameModeName = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameData["queue"]["id"]) if gameData["queue"]["name"] == "" else gameData["queue"]["name"]
            excel_name = "Player Stats in Match %s-%s (%s).xlsx" %(platformId, gameData["gameId"], normalize_file_name(gameModeName))
            if gameMode == "TFT":
                tft_eog_stats: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
                if "errorCode" in tft_eog_stats:
                    isSpectating = current_info["puuid"] in list(map(lambda x: x.get("puuid", ""), gameflow_session["gameData"]["playerChampionSelections"]))
                    teamOneOnly = True #游戏会话中没有存储双人作战的分组信息。因此这里只能认为只存在一支队伍（The gameflow session doesn't store the partner group information in TFT pairs. Therefore, when it comes to this branch, we consider there's only one team）
                    myTeam: list[dict[str, Any]] = []
                    theirTeam: list[dict[str, Any]] = []
                    for player in gameData["teamOne"] + gameData["teamTwo"]:
                        if "puuid" in player and bool(player["puuid"]):
                            if player["puuid"] == current_info["puuid"]:
                                myTeam.append(player["puuid"])
                            else:
                                theirTeam.append(player["puuid"])
                    #下面的部分重复了游戏会话的玩家信息获取代码（The following part repeats the code in the in-game part that get summoner information）
                    myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], myTeam))
                    for player in myTeam + theirTeam:
                        player_info_recapture = 0
                        player_info = await get_info(connection, player["puuid"])
                        while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                            logPrint(player_info["message"], verbose = print_detail)
                            player_info_recapture += 1
                            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture), verbose = print_detail)
                            player_info = await get_info(connection, player["puuid"])
                        if player_info["info_got"]:
                            player_info_body = player_info["body"]
                            fetched_players.append(player_info_body)
                            ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids
                        else:
                            logPrint(player_info["message"], verbose = print_detail)
                            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名玩家。\nInformation of an player (puuid: %s) capture failed! The program will ignore this player.")
                else: #这一部分不需要获取召唤师信息（Summoner information doesn't need to be fetched in this part）
                    fetched_players = tft_eog_stats["players"]
                    for player in fetched_players:
                        currentPlayer_partnerGroupId: int = player["partnerGroupId"]
                        if player["puuid"] == current_info["puuid"]:
                            break
                    else:
                        currentPlayer_partnerGroupId = -1 #一般情况下，一个人的搭档组号是0（In normal cases, a player's partnerGroupId is 0）
                    isSpectating = current_info["puuid"] in list(map(lambda x: x["puuid"], fetched_players))
                    teamOneOnly = all(map(lambda x: x["partnerGroupId"] == 0, fetched_players)) #用于区分双人作战（Designed to tell apart TFT pairs）
                    myTeam: list[dict[str, Any]] = []
                    theirTeam: list[dict[str, Any]] = []
                    for player in fetched_players:
                        if teamOneOnly and player["puuid"] == current_info["puuid"] or not teamOneOnly and player["partnerGroupId"] == currentPlayer_partnerGroupId:
                            myTeam.append(player)
                        else:
                            theirTeam.append(player)
                    myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], myTeam))
                    for player in fetched_players:
                        ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids
                players_metaDf = await sort_eog_stat_tft_data(connection, summonerIcons)
            else:
                eog_stats_block: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
                if "errorCode" in eog_stats_block:
                    isSpectating = current_info["puuid"] in list(map(lambda x: x.get("puuid", ""), gameflow_session["gameData"]["playerChampionSelections"]))
                    teamOneOnly = True #游戏会话中没有存储斗魂竞技场的战队信息。因此这里只能认为只存在一支队伍（The gameflow session doesn't store the player subteam information in Arena. Therefore, when it comes to this branch, we consider there's only one team）
                    myTeam: list[dict[str, Any]] = []
                    theirTeam: list[dict[str, Any]] = []
                    for player in gameData["teamOne"] + gameData["teamTwo"]:
                        if "puuid" in player and bool(player["puuid"]):
                            theirTeam.append(player["puuid"])
                    #下面的部分重复了游戏会话的玩家信息获取代码（The following part repeats the code in the in-game part that get summoner information）
                    for player in myTeam + theirTeam:
                        player_info_recapture = 0
                        player_info = await get_info(connection, player["puuid"])
                        while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                            logPrint(player_info["message"], verbose = print_detail)
                            player_info_recapture += 1
                            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture), verbose = print_detail)
                            player_info = await get_info(connection, player["puuid"])
                        if player_info["info_got"]:
                            player_info_body = player_info["body"]
                            fetched_players.append(player_info_body)
                        else:
                            logPrint(player_info["message"], verbose = print_detail)
                            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名玩家。\nInformation of an player (puuid: %s) capture failed! The program will ignore this player.")
                else:
                    isSpectating = False #设置观战逻辑变量，确定游戏会话是不是观战的（This boolean variable is declared to tell whether the game session is spectating）
                    teamOneOnly = len(eog_stats_block["teams"]) == 1 or eog_stats_block["gameMode"] == "CHERRY"
                    teamOne: list[dict[str, Any]] = eog_stats_block["teams"][0]["players"]
                    teamTwo: list[dict[str, Any]] = eog_stats_block["teams"][1]["players"] if len(eog_stats_block["teams"]) > 1 else []
                    if eog_stats_block["teams"][0]["isPlayerTeam"]:
                        myTeam: list[dict[str, Any]] = teamOne
                        theirTeam: list[dict[str, Any]] = teamTwo
                    elif len(eog_stats_block["teams"]) > 1 and eog_stats_block["teams"][1]["isPlayerTeam"]:
                        myTeam = teamTwo
                        theirTeam = teamOne
                    else:
                        myTeam = []
                        theirTeam = teamOne + teamTwo
                        isSpectating = True
                    myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], myTeam))
                    for player in myTeam + theirTeam:
                        if not player["botPlayer"]:
                            fetched_players.append(player)
                            ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids
                players_metaDf = await sort_eog_playerstat_lol_data(connection, summonerIcons, spells, perks, perkstyles, CherryAugments)
        else: #这部分情形已被后续`len(fetched_players) == 0`部分得到处理（This case is handled by the following `len(fetched_players) == 0` part）
            logPrint("您目前不在英雄选择阶段或者游戏内。\nYou're currently not during a champ select stage or a game.")
            isSpectating = teamOneOnly = True
            gameMode = ""
            excel_name = "Player Stats in Match %s-%s (%s).xlsx" #这就是在此情形下显示的工作簿名称（This is meant to be the name of the workbook to display in this case）
            players_metaDf = pandas.DataFrame()
    else:
        logPrint('请输入对局序号。输入“0”以返回上一层。\nPlease enter the gameId. Submit "0" to return to the last step.')
        while True:
            pastCheck: bool = True
            #首先判断对局是英雄联盟的还是云顶之弈的（First, judge which product the gameId belongs to, LoL or TFT）
            isTFT = False
            gameId_str: str = logInput()
            if gameId_str == "0":
                pastCheck = False
                break
            else:
                try:
                    gameId: int = int(gameId_str)
                except ValueError:
                    logPrint("请输入整数类型的对局序号！\nPlease enter the gameId of integer type!")
                else:
                    if gameId > 0:
                        match_id: str = f"{platformId}_{gameId}"
                        status, game_info = await get_game_info_sgp(connection, sgpSession, match_id, log = log)
                        if status == 200:
                            isTFT = game_info["metadata"]["product"] == "TFT"
                            break
                        else:
                            logPrint("请求失败！请切换一个对局序号或稍后重试。\nRequest failed! Please change a gameId or try it again later.")
                    else:
                        logPrint("请输入一个正整数！\nPlease enter a positive integer.")
        if pastCheck:
            #然后获取对局信息并生成对局信息数据框（Then, get game information and generate game information dataframe）
            if isTFT and bool(game_info["json"]):
                TFTGame_info = game_info
                gameMode: str = "TFT"
                gameModeName = gameQueues[TFTGame_info["json"]["queueId"]]["name"] if TFTGame_info["json"]["queueId"] in gameQueues else "TFT (%d)" %(TFTGame_info["json"]["queueId"])
                players_metaDf: pandas.DataFrame = (await sort_TFTGame_info(connection, TFTGame_info, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = 1, current_puuid = current_info["puuid"], useAllVersions = False, sortStats = False, log = log))[0]
                current_timestamp_millis = TFTGame_info["json"]["gameCreation"]
            elif not isTFT:
                LoLGame_info = game_info
                if use_sgp and bool(LoLGame_info["json"]):
                    gameMode = LoLGame_info["json"]["gameMode"]
                    gameModeName = gameQueues[LoLGame_info["json"]["queueId"]]["name"] if LoLGame_info["json"]["queueId"] in gameQueues else gameMode + " (%d)" %(LoLGame_info["json"]["queueId"])
                    players_metaDf = sort_LoLGame_info_sgp(LoLGame_info, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = 1, current_puuid = current_info["puuid"], useAllVersions = False, sortStats = False, log = log)[0]
                    current_timestamp_millis = LoLGame_info["json"]["gameCreation"]
                else:
                    status, LoLGame_info = await get_LoLGame_info(connection, gameId, log = log)
                    gameMode = LoLGame_info["gameMode"]
                    gameModeName = gameQueues[LoLGame_info["queueId"]]["name"] if LoLGame_info["queueId"] in gameQueues else gameMode + " (%d)" %(LoLGame_info["queueId"])
                    players_metaDf = sort_LoLGame_info(LoLGame_info, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = 1, current_puuid = current_info["puuid"], useAllVersions = False, sortStats = False, log = log, verbose = print_detail)[0]
                    current_timestamp_millis = LoLGame_info["gameCreation"]
            else:
                logPrint("未获取到有效的玩家信息。请切换其它对局。\nNo valid participant information detected. Please change another game.")
                return
            excel_name: str = "Player Stats in Match %s-%s (%s).xlsx" %(platformId, gameId, normalize_file_name(gameModeName))
            isSpectating: bool = False #严格地讲并不算观战，但其作用与其它地方该变量的作用相同（Seriously, this situation can't be regarded as spectating. However, it plays the same role as in other places）
            if isTFT:
                for player in TFTGame_info["json"]["participants"]:
                    currentPlayer_partnerGroupId: int = player.get("partner_group_id", 0)
                    if player["puuid"] == current_info["puuid"]:
                        break
                else:
                    currentPlayer_partnerGroupId = -1
                fetched_players = TFTGame_info["json"]["participants"]
                isSpectating = current_info["puuid"] in list(map(lambda x: x["puuid"], fetched_players))
                teamOneOnly = all(map(lambda x: x.get("partner_group_id", 0) == 0, fetched_players))
                myTeam: list[dict[str, Any]] = []
                theirTeam: list[dict[str, Any]] = []
                for player in fetched_players:
                    if teamOneOnly and player["puuid"] == current_info["puuid"] or not teamOneOnly and player.get("partner_group_id", 0) == currentPlayer_partnerGroupId:
                        myTeam.append(player)
                    else:
                        theirTeam.append(player)
                myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], myTeam))
                for player in fetched_players:
                    ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids
            elif use_sgp:
                #首先列出各阵营的玩家（First, list participants of each team）
                teamOne: list[dict[str, Any]] = []
                teamTwo: list[dict[str, Any]] = []
                for player in LoLGame_info["json"]["participants"]:
                    if player["teamId"] == 100:
                        teamOne.append(player)
                    elif player["teamId"] == 200:
                        teamTwo.append(player)
                #其次，判断两支阵营哪支是我方，哪支是对方（Second, judge which team is allied team and vice versa）
                if LoLGame_info["json"]["gameMode"] == "CHERRY": #斗魂竞技场的对局需要根据子阵营来判断一名玩家是否是队友（To judge whether a player is the ally in an Arena game, the subteam needs to be checked）
                    for player in LoLGame_info["json"]["participants"]: #第一次循环确定自己的子阵营序号（The first loop determines the subteamId of the user itself）
                        mySubteamId: int = player.get("playerSubteamId", 0)
                        if player["puuid"] == current_info["puuid"]:
                            break
                    else:
                        mySubteamId = 0
                    if mySubteamId == 0:
                        myTeam: list[dict[str, Any]] = []
                        theirTeam: list[dict[str, Any]] = teamOne + teamTwo
                        isSpectating = True
                    else:
                        myTeam = []
                        theirTeam = []
                        for player in LoLGame_info["json"]["participants"]: #第二次循环确定己方阵营和敌方阵营（The second loop determines myTeam and theirTeam）
                            if player["playerSubteamId"] == mySubteamId:
                                myTeam.append(player)
                            else:
                                theirTeam.append(player)
                else:
                    if current_info["puuid"] in list(map(lambda x: x["puuid"], teamOne)):
                        myTeam = teamOne
                        theirTeam = teamTwo
                    elif current_info["puuid"] in list(map(lambda x: x["puuid"], teamTwo)):
                        myTeam = teamTwo
                        theirTeam = teamOne
                    else:
                        myTeam = []
                        theirTeam = teamOne + teamTwo
                        isSpectating = True
                #最后确定fetched_players和ally_bool_dict（Last, determine `fetched_players` and `ally_bool_dict`）
                myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], myTeam))
                for player in myTeam + theirTeam:
                    if not player["puuid"] in {"", BOT_UUID}:
                        fetched_players.append(player)
                        ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids
                teamOneOnly: bool = LoLGame_info["json"]["mapId"] == 22 or LoLGame_info["json"]["mapId"] == 30 and isSpectating #在查看自己参与的过往斗魂竞技场对局，则可以推断出队友信息，进而区分敌我双方（The ally of a previous Arena game that the user participated in by himself/herself can be inferred, so that the program can tell myTeam and theirTeam）
            else: #LCU API中的玩家信息被分成“participantIdentities”和“participants”两个键，而最终要形成的fetched_players的有效信息位于“participantIdentities”键的“player”子键下（In LCU API, participant information is divided into "participantIdentities" and "participants" keys. The information we need is located at the "player" subkey of "participantIdentities" key）
                #首先列出各阵营的玩家（First, list participants of each team）
                participantIdentities: dict[int, dict[str, Any]] = {participant["participantId"]: participant["player"] for participant in LoLGame_info["participantIdentities"]}
                teamOne: list[dict[str, Any]] = []
                teamTwo: list[dict[str, Any]] = []
                for player in LoLGame_info["participants"]:
                    if player["teamId"] == 100:
                        teamOne.append(participantIdentities[player["participantId"]])
                    elif player["teamId"] == 200:
                        teamTwo.append(participantIdentities[player["participantId"]])
                #其次，判断两支阵营哪支是我方，哪支是对方（Second, judge which team is allied team and vice versa）
                if LoLGame_info["gameMode"] == "CHERRY":
                    for player in LoLGame_info["participants"]:
                        mySubteamId: int = player["stats"]["playerSubteamId"]
                        if participantIdentities[player["participantId"]]["puuid"] == current_info["puuid"]:
                            break
                    else:
                        mySubteamId = 0
                    if mySubteamId == 0:
                        myTeam: list[dict[str, Any]] = []
                        theirTeam: list[dict[str, Any]] = teamOne + teamTwo
                        isSpectating = True
                    else:
                        myTeam = []
                        theirTeam = []
                        for player in LoLGame_info["participants"]: #第二次循环确定己方阵营和敌方阵营（The second loop determines myTeam and theirTeam）
                            if player["stats"]["playerSubteamId"] == mySubteamId:
                                myTeam.append(participantIdentities[player["participantId"]])
                            else:
                                theirTeam.append(participantIdentities[player["participantId"]])
                else: #其它模式的对局根据阵营来判断一名玩家是否是队友。对于云顶之弈对局，通过`teamOneOnly`变量来指定其该模式下只有一支队伍（To judge whether a player is an ally in a game other than Arena, teamId is used. For a TFT game, `teamOneOnly` declares that only one team exists）
                    if current_info["puuid"] in list(map(lambda x: x["puuid"], teamOne)):
                        myTeam = teamOne
                        theirTeam = teamTwo
                    elif current_info["puuid"] in list(map(lambda x: x["puuid"], teamTwo)):
                        myTeam = teamTwo
                        theirTeam = teamOne
                    else:
                        myTeam = []
                        theirTeam = teamOne + teamTwo
                        isSpectating = True
                #最后确定fetched_players和ally_bool_dict（Last, determine `fetched_players` and `ally_bool_dict`）
                myTeam_puuids: list[str] = list(map(lambda x: x["puuid"], myTeam))
                for player in myTeam + theirTeam:
                    if not player["puuid"] in {"", BOT_UUID}:
                        fetched_players.append(player)
                        ally_bool_dict[player["puuid"]] = player["puuid"] in myTeam_puuids
                teamOneOnly: bool = LoLGame_info["mapId"] == 22 or LoLGame_info["mapId"] == 30 and isSpectating #在查看自己参与的过往斗魂竞技场对局，则可以推断出队友信息，进而区分敌我双方（The ally of a previous Arena game that the user participated in by himself/herself can be inferred, so that the program can tell myTeam and theirTeam）
        else: #这个分支只是为了消除类型检查报错（This branch is only designed to eliminate the errors from type check）
            current_timestamp_millis = 0
            isSpectating = teamOneOnly = True
            gameMode = ""
            excel_name = "Player Stats in Match %s-%s (%s).xlsx"
            players_metaDf = pandas.DataFrame()
    if len(fetched_players) == 0:
        if mode == "1":
            if gameflow_phase in {"ChampSelect", "InProgress", "Reconnect"}:
                logPrint("未在当前对局中发现其它人类玩家。\nThere's not any other human player in this game.")
            else:
                logPrint("请确保您正处于英雄选择阶段或者游戏内。\nPlease confirm you're during a champ select stage or a game.")
        #已经发生的对局中至少有一名玩家，所以`len(fetched_players)`不可能是0（Any match that has ended as normal must have at least one player, so `len(fetched_players)` can't be 0 in this case）
    else:
        fetched_puuids: list[str] = list(map(lambda x: x["puuid"], fetched_players))
        unmapped_keys: dict[str, set[Any]] = {"summonerIcon": set(), "regaliaBanner": set(), "LoLChampion": set()}
        player_info_df: pandas.DataFrame = await sort_summoner_info(connection, fetched_puuids, summonerIcons, LoLChampions, regaliaBanners, unmapped_keys = unmapped_keys, log = log, verbose = print_detail)
        game_leaderboard_df: pandas.DataFrame = await sort_game_leaderboard(connection, puuids = fetched_puuids)
        logPrint("请输入您想要查询的对局数量，默认为最近20场。最大200场。\nPlease enter the number of matches you want to search, 20 by default and 200 at maximum.")
        while True:
            count_str: str = logInput()
            if count_str == "":
                count: int = args.count
                break
            else:
                try:
                    count = int(count_str)
                except ValueError:
                    logPrint("请输入一个整数！\nPlease enter an integer!")
                else:
                    if count > 0:
                        break
                    else:
                        logPrint("请输入一个正整数！\nPlease enter a positive integer!")
        queue_df: pandas.DataFrame = await sort_queue_data(connection)
        queue_df_fields_to_print: list[str] = ["id", "name", "mapId", "category", "pickMode"]
        queue_df_indices_to_select: list[int] = [0] + list(queue_df[(queue_df["queueAvailability"] == "√") | (queue_df["isVisible"] == "√")].index)
        queueIds: list[int] = []
        if len(args.queues) > 0:
            for queueId in args.queues:
                if isinstance(queueId, int) and (queueId == 0 or queueId in list(queue_df["id"][:])):
                    queueIds.append(queueId)
            if len(queueIds) == 0:
                #本来是想要设置一个全局逻辑变量`invalid_cmdline_queueIds_hint_printed`来保证下面的提示只输出一次，但是由于上面在追加队列序号时只会追加有效的队列序号，所以程序下一次运行到这里时，如果`arg.queues`中有元素，那么一定是有效的队列序号（I had intended to set a global boolean variable `invalid_cmdline_queueIds_hint_printed` to ensure the following hint below is printed only once, but since the program only appends valid queueIds above, next time the program is going to execute these code, if `args.queues` has elements, then they must be valid queueIds）
                logPrint("从命令行中变量中没有获取到有效的队列序号！程序将导出所有对局。\nNo valid queueIds are obtained from the command line arguments! The program will export all matches instead.")
                queue_select: bool = False #决定是否在后续输出时对对局的游戏模式进行筛选（Decides whether to select the game modes among the matches subsequently）
            else:
                queue_select = True
        else:
            logPrint("是否需要对游戏队列取子集？（输入任意键以开始打草稿，否则直接开始输入队列序号。）\nDo you want to get a subset of the current game mode data? (Submit any non-empty string to make a draft, or null to input the queue ids directly.)")
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
                        scope: dict[str, Any] = {"format_df": format_df, "df": queue_df.copy(deep = True), "queues": gameQueues_source, "fields": queue_df_fields_to_print}
                        logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["type"] == "URF") & (df["assetMutator"] == "PICKURF")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                        subscope(scope, log = log)
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
            logPrint("请输入队列序号以选择游戏模式。直接按回车键以显示所有对局。\nPlease select a game mode by entering queue ids. Press Enter directly to display all matches.")
            print(format_df(queue_df.loc[queue_df_indices_to_select, queue_df_fields_to_print])[0])
            log.write(format_df(queue_df.loc[queue_df_indices_to_select, queue_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
            logPrint('''变量提示（Variable hint）：\nqueue_df = await sort_queue_data(connection)\n示例（Examples）：\n\nall\n420\n[420, 440]\n#筛选所有英雄联盟队列（Select all LoL queues）\nlist(queue_df[queue_df["mapId"] != 22].loc[1:, "id"])\n#筛选所有云顶之弈队列（Select all TFT queues）\nlist(queue_df[queue_df["mapId"] == 22].loc[:, "id"])\n#筛选召唤师峡谷的排位队列（Select ranked queues in Summoner's Rift）\nlist(queue_df[(queue_df["type"].str.startswith("RANKED")) & (queue_df["mapId"] == 11)].loc[:, "id"])\n输入以“#”开头的序号以使用本程序提供的快捷选项：\nEnter a number starting with "#" to choose a quick option (if any one fits your demand):''')
            for option in queueId_options:
                logPrint("%s\t%s\n\t%s" %(option, queueId_options[option]["description"], queueId_options[option]["expression"]))
            queue_select = True
            while True:
                queueId_str: str = logInput()
                if queueId_str == "" or queueId_str == "all":
                    queue_select = False
                    break
                elif queueId_str == "0":
                    return
                elif queueId_str in queueId_options:
                    queueIds = eval(queueId_options[queueId_str]["expression"])
                    break
                else:
                    try:
                        queueIds: list[int] = eval(queueId_str)
                    except:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    else:
                        if isinstance(queueIds, int) and queueIds in list(queue_df["id"][:]):
                            queueIds = [queueIds]
                            break
                        elif isinstance(queueIds, list) and all(map(lambda x: isinstance(x, int) and (x in {-1, 0} or x in list(queue_df["id"][1:])), queueIds)): #自定义对局的对局序号是0（QueueId of a custom game is 0）
                            break
                        else:
                            logPrint("队列序号不合法！请重新输入一个队列序号列表。\nIllegal queueId list! Please try another queueId list.")
        search_LoL = search_TFT = False #通过用户选择的队列序号来决定查看英雄联盟还是云顶之弈的数据（Decide to check LoL or TFT game stats through the queueIds selected by the user）
        if queue_select:
            args.queues = queueIds #这里的`args.queues`虽然从代码字面意义上代表的是从命令行中获取的队列序号，但实际上在未添加命令行变量时，也可作为一个存储队列序号的容器，从而实现队列序号的记忆功能（Here although `args.queues` literally means the queueIds obtained from command line arguments, it can also be used as a container to store queueIds when no command line arguments are provided, so that queueIds can be stored in some memory）
            for queueId in queueIds:
                if search_LoL and search_TFT: #当从用户输入的队列序号中同时检测到了英雄联盟和云顶之弈队列，就不用再检测了（When the program detects both LoL and TFT game queues, there's no need to detect further）
                    break
                if queueId in gameQueues:
                    if gameQueues[queueId]["gameMode"] == "TFT":
                        search_TFT: bool = True
                    else:
                        search_LoL: bool = True
                elif queueId in {-1, 0}:
                    search_LoL = True
        else:
            args.queues = []
            search_LoL = search_TFT = True
        LoLGame_stat_fields_summary: list[str] = ["queueId", "gameModeName", "champion_name", "K/D/A", "CS", "gameDuration", "win/lose", "KP_percent", "goldEarned", "KDA", "totalDamageDealtToChampions", "totalDamageTaken", "totalHeal", "KP_order", "goldEarned_order", "KDA_order", "totalDamageDealtToChampions_order", "totalDamageTaken_order", "totalHeal_order"]
        LoLPlayer_stat_summary_dfs.append(pandas.concat([pandas.DataFrame(data = {"ally?": "是否队友？", "summonerName": "召唤师名"}, index = [0]), pandas.DataFrame(data = LoLGame_stat_header, index = [0]).loc[:, LoLGame_stat_fields_summary]], axis = 1))
        #LoLGame_stat_fields_details_to_print: list[str] = ["gameIndex", "gameCreationDate", "gameModeName", "champion_name", "champion_alias", "K/D/A", "KDA", "win/lose"]
        TFTGame_stat_fields_summary: list[str] = ["queue_id", "gameModeName", "last_round_format", "total_damage_to_players", "players_eliminated", "placement"]
        TFTPlayer_stat_summary_dfs.append(pandas.concat([pandas.DataFrame(data = {"ally?": "是否队友？", "summonerName": "召唤师名"}, index = [0]), pandas.DataFrame(data = TFTGame_stat_header, index = [0]).loc[:, TFTGame_stat_fields_summary]], axis = 1))
        #TFTGame_stat_fields_details_to_print: list[str] = ["gameIndex", "game_datetime", "gameModeName", "companion name", "last_round", "placement"]
        for i in range(len(fetched_players)):
            player: dict[str, Any] = fetched_players[i]
            player_summonerName: str = get_info_name(player)
            if search_LoL:
                logPrint("[%d/%d]" %((search_LoL + search_TFT) * i + 1, (search_LoL + search_TFT) * len(fetched_players)), end = "")
                logPrint(f"正在获取{player_summonerName}的最近{count}场英雄联盟对局记录……\nLoading the recent {count} LoL match(es) of {player_summonerName} ...")
                LoLGame_stat_df: pandas.DataFrame = await search_player_match_stats_lol(connection, player["puuid"], begIndex = 0, endIndex = count - 1, lol_sgp = use_sgp, log = log, verbose = print_detail)
                #logPrint(f"{player_summonerName}的最近{count}场英雄联盟对局记录获取完成。\nThe recent {count} LoL match(es) of {player_summonerName} have/has been loaded.")
                if queue_select:
                    LoLGame_stat_indices_queueSelected: list[int] = [0] + list(LoLGame_stat_df[LoLGame_stat_df["queueId"].isin(queueIds)].index)
                    LoLGame_stat_df = LoLGame_stat_df.loc[LoLGame_stat_indices_queueSelected, :]
                if args.save_early:
                    LoLGame_stat_indices_timeSelected: list[int] = [0] + list(LoLGame_stat_df.loc[1:, :][LoLGame_stat_df.loc[1:, :]["gameCreation"] <= current_timestamp_millis].index)
                    LoLGame_stat_df = LoLGame_stat_df.loc[LoLGame_stat_indices_timeSelected, :]
                #logPrint(LoLGame_stat_df, write_time = False)
                LoLPlayer_stat_details_dfs[player_summonerName] = LoLGame_stat_df.copy(deep = True)
                LoLPlayer_stat_summary_df: pandas.DataFrame = pandas.concat([pandas.DataFrame(data = {"ally?": ["是否队友？"] + ["" if teamOneOnly else "√" if ally_bool_dict[player["puuid"]] else ""] * (len(LoLGame_stat_df) - 1), "summonerName": ["召唤师名"] + [player_summonerName] * (len(LoLGame_stat_df) - 1)}, index = LoLGame_stat_df.index), LoLGame_stat_df.loc[:, LoLGame_stat_fields_summary]], axis = 1)
                LoLPlayer_stat_summary_dfs.append(LoLPlayer_stat_summary_df.loc[1:, :])
            if search_TFT:
                logPrint("[%d/%d]" %((search_LoL + search_TFT) * i + 1 + search_LoL, (search_LoL + search_TFT) * len(fetched_players)), end = "")
                logPrint(f"正在获取{player_summonerName}的最近{count}场云顶之弈对局记录……\nLoading the recent {count} TFT match(es) of {player_summonerName} ...")
                TFTGame_stat_df: pandas.DataFrame = await search_player_match_stats_tft(connection, player["puuid"], begin = 0, count = count - 1, log = log, verbose = print_detail)
                #logPrint(f"{player_summonerName}的最近{count}场云顶之弈对局记录获取完成。\nThe recent {count} TFT match(es) of {player_summonerName} have/has been loaded.")
                if queue_select:
                    TFTGame_stat_indices_queueSelected: list[int] = [0] + list(TFTGame_stat_df[TFTGame_stat_df["queue_id"].isin(queueIds)].index)
                    TFTGame_stat_df = TFTGame_stat_df.loc[TFTGame_stat_indices_queueSelected, :]
                if args.save_early:
                    TFTGame_stat_indices_timeSelected: list[int] = [0] + list(TFTGame_stat_df.loc[1:, :][TFTGame_stat_df.loc[1:, :]["gameCreation"] <= current_timestamp_millis].index)
                    TFTGame_stat_df = TFTGame_stat_df.loc[TFTGame_stat_indices_timeSelected, :]
                #logPrint(TFTGame_stat_df, write_time = False)
                TFTPlayer_stat_details_dfs[player_summonerName] = TFTGame_stat_df.copy(deep = True)
                TFTPlayer_stat_summary_df: pandas.DataFrame = pandas.concat([pandas.DataFrame(data = {"ally?": ["是否队友？"] + ["" if teamOneOnly else "√" if ally_bool_dict[player["puuid"]] else ""] * (len(TFTGame_stat_df) - 1), "summonerName": ["召唤师名"] + [player_summonerName] * (len(TFTGame_stat_df) - 1)}, index = TFTGame_stat_df.index), TFTGame_stat_df.loc[:, TFTGame_stat_fields_summary]], axis = 1)
                TFTPlayer_stat_summary_dfs.append(TFTPlayer_stat_summary_df.loc[1:, :])
        sheet_headers: dict[str, str] = {get_info_name(player): "" if isSpectating or teamOneOnly else "Ally - " if ally_bool_dict[player["puuid"]] else "Enemy - " for player in fetched_players}
        LoLPlayer_summary_df: pandas.DataFrame = pandas.DataFrame()
        TFTPlayer_summary_df: pandas.DataFrame = pandas.DataFrame()
        if search_LoL:
            LoLPlayer_summary_df = pandas.concat(LoLPlayer_stat_summary_dfs, ignore_index = True)
        if search_TFT:
            TFTPlayer_summary_df = pandas.concat(TFTPlayer_stat_summary_dfs, ignore_index = True)
        #导出玩家战绩（Export player stats）
        logPrint("正在保存玩家战绩……\nSaving player stats ...")
        while True:
            try:
                with pandas.ExcelWriter(path = excel_name, engine = "openpyxl") as writer: #使用openpyxl引擎套用条件格式（Use "openpyxl" engine to add conditional formats）
                    player_info_df.to_excel(excel_writer = writer, sheet_name = "MemberIdentity")
                    logPrint("成员身份信息已导出。\nMember identity information has been exported.")
                    if mode == "1" and gameflow_phase == "ChampSelect":
                        players_metaDf.transpose().to_excel(excel_writer = writer, sheet_name = "MemberComposition (ChampSelect)")
                        logPrint("英雄选择阶段的成员构成已导出。\nMember composition during the champ select stage has been exported.", verbose = print_detail)
                    elif mode == "1" and gameflow_phase in {"InProgress", "Reconnect"}:
                        players_metaDf.transpose().to_excel(excel_writer = writer, sheet_name = "MemberComposition (InProgress)")
                        logPrint("游戏内的成员构成已导出。\nMember composition in the game has been exported.", verbose = print_detail)
                    elif mode == "2":
                        players_metaDf.transpose().to_excel(excel_writer = writer, sheet_name = "MemberComposition (PostGame)")
                        if gameMode != "TFT":
                            worksheet = writer.sheets["MemberComposition (PostGame)"]
                            worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                            participantId_teamId_map: dict[str, list[int]] = {}
                            participantId_subteamId_map: dict[str, list[int]] = {}
                            for i in range(1, len(players_metaDf)):
                                participantId: int = players_metaDf["participantId"][i]
                                team = players_metaDf["team_color"][i]
                                playerSubteam = players_metaDf["playerSubteamColor"][i]
                                if not team in participantId_teamId_map:
                                    participantId_teamId_map[team] = []
                                participantId_teamId_map[team].append(participantId)
                                if not playerSubteam in participantId_subteamId_map:
                                    participantId_subteamId_map[playerSubteam] = []
                                participantId_subteamId_map[playerSubteam].append(participantId)
                            max_numPlayersPerTeam_lol: int = max(map(len, participantId_subteamId_map.values())) if gameMode == "CHERRY" else max(map(len, participantId_teamId_map.values()))
                            addFormat_LoLGame_info_wb_transpose(worksheet, players_metaDf.transpose(), numColorScale_order = max_numPlayersPerTeam_lol)
                        logPrint(f"对局{gameId}的玩家数据已导出。\nPlayer stats in Match {gameId} have been exported.", verbose = print_detail)
                    game_leaderboard_df.to_excel(excel_writer = writer, sheet_name = "Game Leaderboard")
                    logPrint("玩家排位信息已汇总。\nGame leaderboard has been summarized.", verbose = print_detail)
                    if search_LoL:
                        LoLPlayer_summary_df.to_excel(excel_writer = writer, sheet_name = "Player Summary (LoL)")
                        worksheet = writer.sheets["Player Summary (LoL)"]
                        worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                        if len(LoLPlayer_summary_df) > 1:
                            max_numPlayersPerTeam_lol = 5 if len(LoLPlayer_summary_df) <= 1 else max(map(lambda x: 5 if x == 0 else 2 if gameQueues[x]["gameMode"] == "CHERRY" else gameQueues[x]["numPlayersPerTeam"], LoLPlayer_summary_df["queueId"][1:]))
                            addFormat_LoLPlayer_summary_wb(worksheet, LoLPlayer_summary_df, numColorScale_order = max_numPlayersPerTeam_lol)
                        logPrint("英雄联盟战绩已汇总。\nLoL game stats have been summarized.", verbose = print_detail)
                    if search_TFT:
                        TFTPlayer_summary_df.to_excel(excel_writer = writer, sheet_name = "Player Summary (TFT)")
                        logPrint("云顶之弈战绩已汇总。\nTFT game stats have been summarized.", verbose = print_detail)
                    if search_LoL:
                        for summonerName in LoLPlayer_stat_details_dfs:
                            LoLPlayer_stat_details_df = LoLPlayer_stat_details_dfs[summonerName]
                            if len(LoLPlayer_stat_details_df) > 1:
                                LoLPlayer_stat_details_df.to_excel(excel_writer = writer, sheet_name = "%s%s (LoL)" %(sheet_headers[summonerName], summonerName))
                                worksheet = writer.sheets["%s%s (LoL)" %(sheet_headers[summonerName], summonerName)]
                                worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                                max_numPlayersPerTeam_lol = 5 if len(LoLPlayer_stat_details_df) <= 1 else max(map(lambda x: 5 if x == 0 else 2 if gameQueues[x]["gameMode"] == "CHERRY" else gameQueues[x]["numPlayersPerTeam"], LoLPlayer_stat_details_df["queueId"][1:]))
                                addFormat_LoLGame_info_wb(worksheet, LoLPlayer_stat_details_df, numColorScale_order = max_numPlayersPerTeam_lol)
                                logPrint(f"{summonerName}的英雄联盟详细战绩已导出。\n{summonerName}'s detailed LoL game stats have been exported.", verbose = print_detail)
                            else:
                                logPrint(f"{summonerName}从5月1日起就没有进行过任何英雄联盟对局。\n{summonerName} hasn't played LoL game yet since May 1st.", verbose = print_detail)
                    if search_TFT:
                        for summonerName in TFTPlayer_stat_details_dfs:
                            TFTPlayer_stat_details_df = TFTPlayer_stat_details_dfs[summonerName]
                            if len(TFTPlayer_stat_details_df) > 1:
                                TFTPlayer_stat_details_df.to_excel(excel_writer = writer, sheet_name = "%s%s (TFT)" %(sheet_headers[summonerName], summonerName))
                                logPrint(f"{summonerName}的云顶之弈详细战绩已导出。\n{summonerName}'s detailed TFT game stats have been exported.", verbose = print_detail)
                            else:
                                logPrint(f"{summonerName}从5月1日起就没有进行过任何云顶之弈对局。\n{summonerName} hasn't played TFT game yet since May 1st.", verbose = print_detail)
                if gameflow_phase == "ChampSelect":
                    logPrint(f'英雄选择阶段的玩家战绩已导出。请查看同目录下的“{excel_name}”。\nPlayer game stats during champ select have been exported. Please check "{excel_name}" under the same folder.')
                else:
                    logPrint(f'本场对局的玩家战绩已导出。请查看同目录下的“{excel_name}”。\nPlayer game stats in this game have been exported. Please check "{excel_name}" under the same folder.')
            except PermissionError:
                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                logInput()
            #由于上面是覆盖写而不是追加写，而且是在脚本运行目录下生成文件，所以不会出现文件不存在的报错（Because the above writing style is overwriting instead of appending, and the generated file is under the same folder as this program, FileNotFoundError shouldn't happen）
            else:
                if args.open_after_save:
                    open_action: bool = True
                else:
                    logPrint("输入任意非空字符串以打开该文件，或者直接进行下一步。\nSubmit any non-empty string to open this file, or null to begin the next search.")
                    open_action_str: str = logInput()
                    open_action = bool(open_action_str)
                if open_action:
                    #os.system(f'"{excel_name}"') #这个命令有时会引起主程序卡顿（Sometimes this command make the main program stuck）
                    excel_filePath: str = os.path.join(wd, excel_name)
                    open_workbook(excel_filePath)
                break
        #循环后处理（Post-loop operation）
        if queue_select:
            logPrint("是否重置队列序号？（输入任意键以重置，否则不重置。）\nDo you want to reset the queueIds? (Submit any non-empty string to reset, or null to deny.)")
            reset_queueIds_str: str = logInput()
            reset_queueIds: bool = bool(reset_queueIds_str)
            if reset_queueIds:
                args.queues = []

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    global sgpSession, log, logInput, logPrint
    log_folder: str = "日志（Logs）/Customized Program 20 - Clarke Revival"
    os.makedirs(log_folder, exist_ok = True)
    currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log = LogManager(os.path.join(log_folder, currentTime + ".log"), mode = "a+", encoding = "utf-8")
    logInput = log.logInput
    logPrint = log.logPrint
    await sgpSession.init(connection)
    await get_summoner_data(connection)
    await prepare_data_resources(connection, verbose = not args.nonverbose)
    while True:
        logPrint('按回车键以继续，或者输入任意非空字符串以退出程序。\nPress Enter to continue, or submit any non-empty string to exit the program.')
        cont_str: str = logInput()
        cont: bool = bool(cont_str)
        if cont:
            break
        await Clarke_revival(connection)
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
