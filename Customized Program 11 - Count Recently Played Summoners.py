from lcu_driver import Connector
from lcu_driver.connection import Connection
import argparse, json, os, pandas, requests, time, traceback
from typing import Any, Optional
from src.utils.summoner import print_summoner_info, get_info, get_info_name
from src.utils.logger import LogManager
from src.utils.format import format_df, addDefaultStyle, verify_uuid
from src.utils.patch import Patch
from src.utils.webRequest import requestUrl, SGPSession
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.conditional_formatting import addFormat_LoLGame_summary_wb_transpose
from src.core.config.const import BOT_UUID
from src.core.config.servers import valid_platformIds, set_platform_folder, set_summonerInfo_folder, save_platform_info
from src.core.config.headers import LoLGame_summary_header, LoLGame_summary_sgp_header, TFTHistory_header
from src.core.dataframes.matchHistory import get_LoLHistory, get_matchSummary_sgp, sort_LoLHistory, sort_LoLHistory_sgp, sort_LoLGame_stats, sort_LoLGame_stats_sgp, sort_TFTHistory, sort_TFTGame_stats, sort_LoLGame_summary, sort_LoLGame_summary_sgp, sort_TFTGame_summary, get_game_summary_sgp, get_LoLGame_summary
from src.core.dataframes.gameflow import sort_multiChampSelect_players
from src.localization.general import language_ddragon, language_dict, language_cdragon

parser: argparse.ArgumentParser = argparse.ArgumentParser(formatter_class = argparse.RawTextHelpFormatter)
parser.add_argument("-a", "--lol-api", help = "指定通过什么接口获取英雄联盟对局概要和时间轴。\nSpecify the interface used to fetch LoL game summary and timeline.", action = "store", type = str, choices = ["lcu", "sgp"], default = "sgp")
parser.add_argument("-r", "--reserve", help = "在对局不包含主玩家的情况下仍然加载该对局。\nLoad a match even if it doesn't contain the main player.", action = "store_true")
parser.add_argument("-ss", "--save-self", help = "在对局包含主玩家的情况下仍然保存其数据。\nSave the main summoner's data even if they're contained in a match.", action = "store_true")
args: argparse.Namespace = parser.parse_args()
use_sgp: bool = args.lol_api == "sgp"

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN, Awesome丶ABC
# 更新（Last update）：     2026/08/17
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

session: requests.Session = requests.Session()
sgpSession: SGPSession = SGPSession()
URLPatch: str = ""
patches_initial: list[str] = []
bigPatches: list[Patch] = []
queues_initial: dict[int, dict[str, Any]] = {}
spells_initial: dict[int, dict[str, Any]] = {}
LoLChampions_initial: dict[int, dict[str, Any]] = {}
LoLItems_initial: dict[int, dict[str, Any]] = {}
summonerIcons_initial: dict[int, dict[str, Any]] = {}
perks_initial: dict[int, dict[str, Any]] = {}
perkstyles_initial: dict[int, dict[str, Any]] = {}
TFTAugments_initial: dict[str, dict[str, Any]] = {}
TFTChampions_initial: dict[str, dict[str, Any]] = {}
TFTItems_initial: dict[str, dict[str, Any]] = {}
TFTCompanions_initial: dict[str, dict[str, Any]] = {}
TFTTraits_initial: dict[str, dict[str, Any]] = {}
CherryAugments_initial: dict[int, dict[str, Any]] = {}
wardSkins: dict[int, dict[str, Any]] = {}
championSkins: dict[int, dict[str, Any]] = {}
log: LogManager = LogManager()
platformId: str = ""
AllAccounts: list[dict[str, Any]] = []
champ_select_session_cache: dict[int, dict[str, Any]] = {}

error_header = {"errorCode": "异常代码", "httpStatus": "HTTP状态码", "implementationDetails": "细节", "message": "消息"}
error_header_keys = list(error_header.keys())
connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 查找最近一起并肩作战的召唤师并给出统计信息（Find recently played summoners and give statistics of it）
#-----------------------------------------------------------------------------
def prepare_data_resources(platformId: str, locale: str) -> tuple[bool, bool]:
    '''
    准备全局数据资源。<br>Prepare global data resources.
    
    :param platformId: 服务器代号。决定使用正式服还是测试服的数据资源。<br>PlatformId, which determines one of Live and PBE data resources will be used.
    
        服务器代号可以通过以下LCU接口获取：<br>PlatformId can be obtained through the following LCU endpoint:
        - `GET /lol-lobby/v1/parties/player`
    :type platformId: str
    :param locale: 语言文化代码。决定了数据资源的语言。<br>Language code, which determines the language of the data resources.
    :type locale
    :return: 是否切换语言，以及是否退出程序。<br>Whether to switch language and whether to exit the program.
    :rtype: tuple[bool, bool]
    '''
    global session, URLPatch, patches_initial, bigPatches, queues_initial, spells_initial, LoLChampions_initial, LoLItems_initial, summonerIcons_initial, perks_initial, perkstyles_initial, TFTAugments_initial, TFTChampions_initial, TFTItems_initial, TFTCompanions_initial, TFTTraits_initial, CherryAugments_initial
    #下面声明一些数据资源的地址（The following code declare some data resources' URLs）
    URLPatch = "pbe" if platformId == "PBE1" or platformId == "PBE" else "latest"
    patches_url: str = "https://ddragon.leagueoflegends.com/api/versions.json"
    queue_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(URLPatch, language_cdragon[locale]) #CommunityDragon数据库只存储第7赛季及以后的数据（CommunityDragon database only stores data including and after Season 7）
    spell_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(URLPatch, language_cdragon[locale])
    LoLChampion_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(URLPatch, language_cdragon[locale])
    LoLItem_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(URLPatch, language_cdragon[locale])
    summonerIcon_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(URLPatch, language_cdragon[locale])
    perk_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(URLPatch, language_cdragon[locale])
    perkstyle_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(URLPatch, language_cdragon[locale])
    TFTBasic_url: str = "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(URLPatch, locale.lower())
    TFTChampion_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(URLPatch, language_cdragon[locale])
    TFTItem_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(URLPatch, language_cdragon[locale])
    TFTCompanion_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(URLPatch, language_cdragon[locale])
    TFTTrait_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(URLPatch, language_cdragon[locale])
    CherryAugment_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(URLPatch, language_cdragon[locale])
    #下面声明离线数据资源的默认地址（The following code declare the default paths of offline data resources）
    patches_local_default: str = "离线数据（Offline Data）\\versions.json"
    queue_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\queues.json" %(URLPatch, language_cdragon[locale])
    spell_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\summoner-spells.json" %(URLPatch, language_cdragon[locale])
    LoLChampion_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\champion-summary.json" %(URLPatch, language_cdragon[locale])
    LoLItem_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\items.json" %(URLPatch, language_cdragon[locale])
    summonerIcon_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\summoner-icons.json" %(URLPatch, language_cdragon[locale])
    perk_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\perks.json" %(URLPatch, language_cdragon[locale])
    perkstyle_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\perkstyles.json" %(URLPatch, language_cdragon[locale])
    TFTBasic_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\cdragon\\tft\\%s.json" %(URLPatch, locale.lower())
    TFTChampion_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftchampions.json" %(URLPatch, language_cdragon[locale])
    TFTItem_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftitems.json" %(URLPatch, language_cdragon[locale])
    TFTCompanion_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\companions.json" %(URLPatch, language_cdragon[locale])
    TFTTrait_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tfttraits.json" %(URLPatch, language_cdragon[locale])
    CherryAugment_local_default: str = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\cherry-augments.json" %(URLPatch, locale.lower())
    #加载数据（Load data）
    logPrint("请选择数据资源获取模式：\nPlease select the data resource capture mode:\n1\t在线模式（Online）\n2\t离线模式（Offline）")
    prepareMode: str = logInput()
    switch_language: bool = False
    while True:
        if prepareMode != "" and prepareMode[0] == "1":
            switch_prepare_mode: bool = False
            #下面获取版本信息（The following code get the patch data）
            try:
                source, status, session = requestUrl("GET", patches_url, session = session, log = log)
                patches_initial = source.json()
            except requests.exceptions.RequestException:
                logPrint('版本信息获取超时！正在尝试离线加载数据……\nPatch information capture timeout! Trying loading offline data ...\n请输入版本Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the patch Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(patches_local_default, patches_local_default))
                while True:
                    patches_local: str = logInput()
                    if patches_local == "":
                        patches_local = patches_local_default
                    elif patches_local[0] == "0":
                        logPrint("版本信息获取失败！请检查系统网络状况和代理设置。\nPatch information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(patches_local, "r", encoding = "utf-8") as fp:
                            patches_initial = json.load(fp)
                        if isinstance(patches_initial, list) and patches_initial[-1] == "lolpatch_3.7":
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合DataDragon数据库中记录的版本数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the patch data archived in DataDragon database (%s)!" %(patches_url, patches_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的版本Json数据文件路径！\nFile "%s" NOT found! Please input a correct patch Json data file path!' %(patches_local, patches_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有版本信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with patch information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合DataDragon数据库中记录的版本数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the patch data archived in DataDragon database (%s)!" %(patches_url, patches_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            latest_patch: str = patches_initial[0]
            patches_dict: dict[str, list[str]] = {}
            smallPatches: list[str] = []
            bigPatches = []
            for patch in patches_initial:
                if not patch.startswith("lolpatch"):
                    patch_split: str = patch.split(".")
                    smallPatch: str = ".".join(patch_split[:3])
                    smallPatches.append(Patch(smallPatch))
                    bigPatch: str = ".".join(patch_split[:2])
                    bigPatches.append(Patch(bigPatch))
                    patches_dict[bigPatch] = []
            for i in range(len(bigPatches)):
                patches_dict[str(bigPatches[i])].append(str(smallPatches[i]))
            #下面获取游戏模式数据（The following code get game mode data）
            try:
                logPrint("正在加载游戏模式信息……\nLoading game mode information from CommunityDragon...")
                source, status, session = requestUrl("GET", queue_url, session = session, log = log)
                if source.ok:
                    queue_initial: list[str] = source.json() #queue存储游戏模式信息（Variable `queue_initial` stores game mode information）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('游戏模式信息获取超时！正在尝试离线加载数据……\nQueue information capture timeout! Trying loading offline data ...\n请输入游戏模式Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the game mode Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(queue_local_default, queue_local_default))
                while True:
                    queue_local: str = logInput()
                    if queue_local == "":
                        queue_local = queue_local_default
                    elif queue_local[0] == "0":
                        logPrint("游戏模式信息获取失败！请检查系统网络状况和代理设置。\nQueue information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(queue_local, "r", encoding = "utf-8") as fp:
                            queue_initial = json.load(fp)
                        if isinstance(queue_initial, list) and all(map(lambda x: all(i in x for i in ["id", "name", "shortName", "description", "detailedDescription", "gameSelectModeGroup", "gameSelectCategory", "gameSelectPriority", "isSkillTreeQueue", "isLimitedTimeQueue", "isBotHonoringAllowed", "hidePlayerPosition", "viableChampionRoster"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], int) for i in ["id", "gameSelectPriority"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], str) for i in ["name", "shortName", "description", "detailedDescription", "gameSelectModeGroup", "gameSelectCategory"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], bool) for i in ["isSkillTreeQueue", "isLimitedTimeQueue", "isBotHonoringAllowed", "hidePlayerPosition"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], list) or x[i] is None for i in ["viableChampionRoster"]), queue_initial)):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的游戏模式数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the game mode data archived in CommunityDragon database (%s)!" %(queue_url, queue_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的游戏模式Json数据文件路径！\nFile "%s" NOT found! Please input a correct game mode Json data file path!' %(queue_local, queue_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有游戏模式信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with game mode information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的游戏模式数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the game mode data archived in CommunityDragon database (%s)!" %(queue_url, queue_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取召唤师技能数据（The following code get summoner spell data）
            try:
                logPrint("正在加载召唤师技能信息……\nLoading summoner spell information from CommunityDragon...")
                source, status, session = requestUrl("GET", spell_url, session = session, log = log)
                if source.ok:
                    spell_initial: list[dict[str, Any]] = source.json() #spell存储召唤师技能信息（Variable `spell_initial` stores summoner spell information）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('召唤师技能信息获取超时！正在尝试离线加载数据……\nSummoner spell information capture timeout! Trying loading offline data ...\n请输入召唤师技能Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the summoner spell Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(spell_local_default, spell_local_default))
                while True:
                    spell_local: str = logInput()
                    if spell_local == "":
                        spell_local = spell_local_default
                    elif spell_local[0] == "0":
                        logPrint("召唤师技能信息获取失败！请检查系统网络状况和代理设置。\nSummoner spell information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(spell_local, "r", encoding = "utf-8") as fp:
                            spell_initial = json.load(fp)
                        if isinstance(spell_initial, list) and all(i in spell_initial[j] for i in ["id", "name", "description", "summonerLevel", "cooldown", "gameModes", "iconPath"] for j in range(len(spell_initial))):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师技能数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner spell data archived in CommunityDragon database (%s)!" %(spell_url, spell_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的召唤师技能Json数据文件路径！\nFile "%s" NOT found! Please input a correct summoner spell Json data file path!' %(spell_local, spell_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有召唤师技能信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with summoner spell information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师技能数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner spell data archived in CommunityDragon database (%s)!" %(spell_url, spell_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取英雄信息（The following code get LoL champion data）
            try:
                logPrint("正在加载英雄信息……\nLoading LoL champion information from CommunityDragon...")
                source, status, session = requestUrl("GET", LoLChampion_url, session = session, log = log)
                if source.ok:
                    LoLChampion_initial: list[dict[str, Any]] = source.json() #LoLItem存储英雄信息。（Variable `LoLChampion_initial` stores information of LoL champions）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('英雄信息获取超时！正在尝试离线加载数据……\nLoL champion information capture timeout! Trying loading offline data ...\n请输入英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the LoL champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(LoLChampion_local_default, LoLChampion_local_default))
                while True:
                    LoLChampion_local: str = logInput()
                    if LoLChampion_local == "":
                        LoLChampion_local = LoLChampion_local_default
                    elif LoLChampion_local[0] == "0":
                        logPrint("英雄信息获取失败！请检查系统网络状况和代理设置。\nLoL champion information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(LoLChampion_local, "r", encoding = "utf-8") as fp:
                            LoLChampion_initial = json.load(fp)
                        if isinstance(LoLChampion_initial, list) and all(isinstance(LoLChampion_initial[i], dict) for i in range(len(LoLChampion_initial))) and all(j in LoLChampion_initial[i] for i in range(len(LoLChampion_initial)) for j in ["id", "name", "alias", "squarePortraitPath", "roles"]) and all(isinstance(LoLChampion_initial[i]["id"], int) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["name"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["alias"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["squarePortraitPath"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["roles"], list) for i in range(len(LoLChampion_initial))):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL champion data archived in CommunityDragon database (%s)!" %(LoLChampion_url, LoLChampion_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的英雄Json数据文件路径！\nFile "%s" NOT found! Please input a correct LoL champion Json data file path!' %(LoLChampion_local, LoLChampion_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with LoL champion information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL champion data archived in CommunityDragon database (%s)!" %(LoLChampion_url, LoLChampion_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取英雄联盟装备信息（The following code get LoL item data）
            try:
                logPrint("正在加载英雄联盟装备信息……\nLoading LoL item information from CommunityDragon...")
                source, status, session = requestUrl("GET", LoLItem_url, session = session, log = log)
                if source.ok:
                    LoLItem_initial: list[dict[str, Any]] = source.json() #LoLItem存储经典模式的装备信息。（Variable `LoLItem_initial` stores information of LoL items）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('英雄联盟装备信息获取超时！正在尝试离线加载数据……\nLoL item information capture timeout! Trying loading offline data ...\n请输入英雄联盟装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the LoL item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(LoLItem_local_default, LoLItem_local_default))
                while True:
                    LoLItem_local: str = logInput()
                    if LoLItem_local == "":
                        LoLItem_local = LoLItem_local_default
                    elif LoLItem_local[0] == "0":
                        logPrint("英雄联盟装备信息获取失败！请检查系统网络状况和代理设置。\nLoL item information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(LoLItem_local, "r", encoding = "utf-8") as fp:
                            LoLItem_initial = json.load(fp)
                        if isinstance(LoLItem_initial, list) and all(i in LoLItem_initial[j] for i in ["id", "name", "description", "active", "inStore", "from", "to", "categories", "maxStacks", "requiredChampion", "requiredAlly", "requiredBuffCurrencyName", "requiredBuffCurrencyCost", "specialRecipe", "isEnchantment", "price", "priceTotal", "iconPath"] for j in range(len(LoLItem_initial))):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄联盟装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL item data archived in CommunityDragon database (%s)!" %(LoLItem_url, LoLItem_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的英雄联盟装备Json数据文件路径！\nFile "%s" NOT found! Please input a correct LoL item Json data file path!' %(LoLItem_local, LoLItem_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有英雄联盟装备信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with LoL item information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄联盟装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL item data archived in CommunityDragon database (%s)!" %(LoLItem_url, LoLItem_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取召唤师图标信息（The following code get summoner icon data）
            try:
                logPrint("正在加载召唤师图标信息……\nLoading summoner icon information from CommunityDragon...")
                source, status, session = requestUrl("GET", summonerIcon_url, session = session, log = log)
                if source.ok:
                    summonerIcon_initial: list[dict[str, Any]] = source.json() #LoLItem存储召唤师图标信息。（Variable `summonerIcon_initial` stores information of summoner icons）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('召唤师图标信息获取超时！正在尝试离线加载数据……\nSummoner icon information capture timeout! Trying loading offline data ...\n请输入召唤师图标Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the summoner icon Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(summonerIcon_local_default, summonerIcon_local_default))
                while True:
                    summonerIcon_local: str = logInput()
                    if summonerIcon_local == "":
                        summonerIcon_local = summonerIcon_local_default
                    elif summonerIcon_local[0] == "0":
                        logPrint("召唤师图标信息获取失败！请检查系统网络状况和代理设置。\nSummoner icon information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(summonerIcon_local, "r", encoding = "utf-8") as fp:
                            summonerIcon_initial = json.load(fp)
                        if isinstance(summonerIcon_initial, list) and all(map(lambda x: isinstance(x, dict), summonerIcon_initial)) and all(i in j for i in ["id", "title", "yearReleased", "isLegacy", "descriptions", "rarities", "disabledRegions"] for j in summonerIcon_initial):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师图标数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner icon data archived in CommunityDragon database (%s)!" %(summonerIcon_url, summonerIcon_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的召唤师图标Json数据文件路径！\nFile "%s" NOT found! Please input a correct summoner icon Json data file path!' %(summonerIcon_local, summonerIcon_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有召唤师图标信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with summoner icon information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师图标数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner icon data archived in CommunityDragon database (%s)!" %(summonerIcon_url, summonerIcon_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取基石符文信息（The following code get perk data）
            try:
                logPrint("正在加载基石符文信息……\nLoading perk information from CommunityDragon...")
                source, status, session = requestUrl("GET", perk_url, session = session, log = log)
                if source.ok:
                    perk_initial: list[dict[str, Any]] = source.json() #perk存储基石符文信息。（Variable `perk_initial` stores information of perks）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('基石符文信息获取超时！正在尝试离线加载数据……\nPerk information capture timeout! Trying loading offline data ...\n请输入基石符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perk Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(perk_local_default, perk_local_default))
                while True:
                    perk_local: str = logInput()
                    if perk_local == "":
                        perk_local = perk_local_default
                    elif perk_local[0] == "0":
                        logPrint("基石符文信息获取失败！请检查系统网络状况和代理设置。\nPerk information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(perk_local, "r", encoding = "utf-8") as fp:
                            perk_initial = json.load(fp)
                        if isinstance(perk_initial, list) and all(i in perk_initial[j] for i in ["id", "name", "majorChangePatchVersion", "tooltip", "shortDesc", "longDesc", "recommendationDescriptor", "iconPath", "endOfGameStatDescs", "recommendationDescriptorAttributes"] for j in range(len(perk_initial))):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的基石符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perk data archived in CommunityDragon database (%s)!" %(perk_url, perk_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的基石符文Json数据文件路径！\nFile "%s" NOT found! Please input a correct perk Json data file path!' %(perk_local, perk_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有基石符文信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with perk information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的基石符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perk data archived in CommunityDragon database (%s)!" %(perk_url, perk_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取符文系信息（The following code get perkstyle data）
            try:
                logPrint("正在加载符文系信息……\nLoading perkstyle information from CommunityDragon...")
                source, status, session = requestUrl("GET", perkstyle_url, session = session, log = log)
                if source.ok:
                    perkstyle_initial: dict[str, Any] = source.json() #perkstyle存储符文系信息。（Variable `perkstyle_initial` stores information of perkstyles）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('符文系信息获取超时！正在尝试离线加载数据……\nPerkstyle information capture timeout! Trying loading offline data ...\n请输入符文系Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perkstyle Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(perkstyle_local_default, perkstyle_local_default))
                while True:
                    perkstyle_local: str = logInput()
                    if perkstyle_local == "":
                        perkstyle_local = perkstyle_local_default
                    elif perkstyle_local[0] == "0":
                        logPrint("符文系信息获取失败！请检查系统网络状况和代理设置。\nperkstyle information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(perkstyle_local, "r", encoding = "utf-8") as fp:
                            perkstyle_initial = json.load(fp)
                        if isinstance(perkstyle_initial, dict) and all(perkstyle_initial.get(i, 0) for i in ["schemaVersion", "styles"]) and isinstance(perkstyle_initial["styles"], list) and all(j in perkstyle_initial["styles"][i] for i in range(len(perkstyle_initial["styles"])) for j in ["id", "name", "tooltip", "iconPath", "assetMap", "isAdvanced", "allowedSubStyles", "subStyleBonus", "slots", "defaultPageName", "defaultSubStyle", "defaultPerks", "defaultPerksWhenSplashed", "defaultStatModsPerSubStyle"]):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的符文系数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perkstyle data archived in CommunityDragon database (%s)!" %(perkstyle_url, perkstyle_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的符文系Json数据文件路径！\nFile "%s" NOT found! Please input a correct perkstyle Json data file path!' %(perkstyle_local, perkstyle_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有符文系信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with perkstyle information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的符文系数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perkstyle data archived in CommunityDragon database (%s)!" %(perkstyle_url, perkstyle_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取云顶之弈强化符文数据（The following code get TFT augment data）
            try:
                logPrint("正在加载云顶之弈基础数据……\nLoading TFT basic data from CommunityDragon ...")
                source, status, session = requestUrl("GET", TFTBasic_url, session = session, log = log)
                if source.ok:
                    TFTBasic_initial: dict[str, Any] = source.json() #TFT存储云顶之弈中至今为止所有的强化符文、英雄和羁绊信息和各赛季的英雄和羁绊信息（Variable `TFTBasic_initial` stores information of all augments, champions and traits so far and information of champions and traits with respect to season）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('云顶之弈基础信息获取超时！正在尝试离线加载数据……\nTFT basic information capture timeout! Trying loading offline data ...\n请输入云顶之弈基础数据Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT basics Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTBasic_local_default, TFTBasic_local_default))
                while True:
                    TFTBasic_local: str = logInput()
                    if TFTBasic_local == "":
                        TFTBasic_local = TFTBasic_local_default
                    elif TFTBasic_local[0] == "0":
                        logPrint("云顶之弈基础信息获取失败！请检查系统网络状况和代理设置。\nTFT basic information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(TFTBasic_local, "r", encoding = "utf-8") as fp:
                            TFTBasic_initial = json.load(fp)
                        if isinstance(TFTBasic_initial, dict) and all(i in TFTBasic_initial for i in ["items", "setData", "sets"]) and all(isinstance(TFTBasic_initial[i], list) for i in ["items", "setData"]) and all(isinstance(TFTBasic_initial[i], dict) for i in ["sets"]) and all(j in TFTBasic_initial["items"][i] for i in range(len(TFTBasic_initial["items"])) for j in ["apiName", "associatedTraits", "composition", "desc", "effects", "from", "icon", "id", "incompatibleTraits", "name", "tags", "unique"]) and all(isinstance(TFTBasic_initial["items"][i][j], str) or TFTBasic_initial["items"][i][j] == None for i in range(len(TFTBasic_initial["items"])) for j in ["apiName", "desc", "icon", "name"]) and all(isinstance(TFTBasic_initial["items"][i][j], list) for i in range(len(TFTBasic_initial["items"])) for j in ["associatedTraits", "composition", "tags"]) and all(isinstance(TFTBasic_initial["items"][i][j], dict) for i in range(len(TFTBasic_initial["items"])) for j in ["effects"]) and all(isinstance(TFTBasic_initial["items"][i][j], bool) for i in range(len(TFTBasic_initial["items"])) for j in ["unique"]) and all(j in TFTBasic_initial["setData"][i] for i in range(len(TFTBasic_initial["setData"])) for j in ["augments", "champions", "items", "mutator", "name", "number", "traits"]) and all(isinstance(TFTBasic_initial["setData"][i][j], list) for i in range(len(TFTBasic_initial["setData"])) for j in ["augments", "champions", "items", "traits"]) and all(isinstance(TFTBasic_initial["setData"][i][j], str) for i in range(len(TFTBasic_initial["setData"])) for j in ["mutator", "name"]) and all(isinstance(TFTBasic_initial["setData"][i][j], int) for i in range(len(TFTBasic_initial["setData"])) for j in ["number"]) and all(map(lambda x: isinstance(x, str), TFTBasic_initial["setData"][i][j]) for i in range(len(TFTBasic_initial["setData"])) for j in ["augments", "items"]) and all(map(lambda x: isinstance(x, dict), TFTBasic_initial["setData"][i]["champions"]) for i in range(len(TFTBasic_initial["setData"]))) and all(k in TFTBasic_initial["setData"][i]["champions"][j] for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in ["ability", "apiName", "characterName", "cost", "icon", "name", "role", "squareIcon", "stats", "tileIcon", "traits"]) and all(isinstance(TFTBasic_initial["setData"][i]["champions"][j][k], dict) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in ["ability", "stats"]) and all(isinstance(TFTBasic_initial["setData"][i]["champions"][j][k], str) or TFTBasic_initial["setData"][i]["champions"][j][k] == None for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in ["apiName", "characterName", "icon", "name", "squareIcon", "tileIcon"]) and all(isinstance(TFTBasic_initial["setData"][i]["champions"][j][k], int) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in ["cost"]) and all(k in TFTBasic_initial["setData"][i]["champions"][j]["ability"] for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in ["desc", "icon", "name", "variables"]) and all(isinstance(TFTBasic_initial["setData"][i]["champions"][j]["ability"][k], str) or TFTBasic_initial["setData"][i]["champions"][j]["ability"][k] == None for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in ["desc", "icon", "name"]) and all(isinstance(TFTBasic_initial["setData"][i]["champions"][j]["ability"][k], list) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in ["variables"]) and all(map(lambda x: isinstance(x, dict), TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"]) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"]))) and all(l in TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"][k] for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in range(len(TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"])) for l in ["name", "value"]) and all(isinstance(TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"][k][l], str) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in range(len(TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"])) for l in ["name"]) and all(isinstance(TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"][k][l], list) or TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"][k][l] == None for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["champions"])) for k in range(len(TFTBasic_initial["setData"][i]["champions"][j]["ability"]["variables"])) for l in ["value"]) and all(k in TFTBasic_initial["setData"][i]["traits"][j] for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["traits"])) for k in ["apiName", "desc", "effects", "icon", "name"]) and all(isinstance(TFTBasic_initial["setData"][i]["traits"][j][k], str) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["traits"])) for k in ["apiName", "desc", "icon", "name"]) and all(isinstance(TFTBasic_initial["setData"][i]["traits"][j][k], list) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["traits"])) for k in ["effects"]) and all(map(lambda x: isinstance(x, dict), TFTBasic_initial["setData"][i]["traits"][j]["effects"]) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["traits"]))) and all(l in TFTBasic_initial["setData"][i]["traits"][j]["effects"][k] for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["traits"])) for k in range(len(TFTBasic_initial["setData"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style", "variables"]) and all(isinstance(TFTBasic_initial["setData"][i]["traits"][j]["effects"][k][l], int) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["traits"])) for k in range(len(TFTBasic_initial["setData"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style"]) and all(isinstance(TFTBasic_initial["setData"][i]["traits"][j]["effects"][k][l], dict) for i in range(len(TFTBasic_initial["setData"])) for j in range(len(TFTBasic_initial["setData"][i]["traits"])) for k in range(len(TFTBasic_initial["setData"][i]["traits"][j]["effects"])) for l in ["variables"]) and all(j in TFTBasic_initial["sets"][i] for i in TFTBasic_initial["sets"] for j in ["champions", "name", "traits"]) and all(isinstance(TFTBasic_initial["sets"][i][j], list) for i in TFTBasic_initial["sets"] for j in ["champions", "traits"]) and all(isinstance(TFTBasic_initial["sets"][i][j], str) for i in TFTBasic_initial["sets"] for j in ["name"]) and all(k in TFTBasic_initial["sets"][i]["champions"][j] for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in ["ability", "apiName", "characterName", "cost", "icon", "name", "role", "squareIcon", "stats", "tileIcon", "traits"]) and all(isinstance(TFTBasic_initial["sets"][i]["champions"][j][k], dict) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in ["ability", "stats"]) and all(isinstance(TFTBasic_initial["sets"][i]["champions"][j][k], str) or TFTBasic_initial["sets"][i]["champions"][j][k] == None for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in ["apiName", "characterName", "icon", "name", "squareIcon", "tileIcon"]) and all(isinstance(TFTBasic_initial["sets"][i]["champions"][j][k], int) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in ["cost"]) and all(k in TFTBasic_initial["sets"][i]["champions"][j]["ability"] for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in ["desc", "icon", "name", "variables"]) and all(isinstance(TFTBasic_initial["sets"][i]["champions"][j]["ability"][k], str) or TFTBasic_initial["sets"][i]["champions"][j]["ability"][k] == None for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in ["desc", "icon", "name"]) and all(isinstance(TFTBasic_initial["sets"][i]["champions"][j]["ability"][k], list) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in ["variables"]) and all(map(lambda x: isinstance(x, dict), TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"]) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"]))) and all(l in TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"][k] for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in range(len(TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"])) for l in ["name", "value"]) and all(isinstance(TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"][k][l], str) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in range(len(TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"])) for l in ["name"]) and all(isinstance(TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"][k][l], list) or TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"][k][l] == None for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["champions"])) for k in range(len(TFTBasic_initial["sets"][i]["champions"][j]["ability"]["variables"])) for l in ["value"]) and all(k in TFTBasic_initial["sets"][i]["traits"][j] for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["traits"])) for k in ["apiName", "desc", "effects", "icon", "name"]) and all(isinstance(TFTBasic_initial["sets"][i]["traits"][j][k], str) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["traits"])) for k in ["apiName", "desc", "icon", "name"]) and all(isinstance(TFTBasic_initial["sets"][i]["traits"][j][k], list) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["traits"])) for k in ["effects"]) and all(map(lambda x: isinstance(x, dict), TFTBasic_initial["sets"][i]["traits"][j]["effects"]) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["traits"]))) and all(l in TFTBasic_initial["sets"][i]["traits"][j]["effects"][k] for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["traits"])) for k in range(len(TFTBasic_initial["sets"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style", "variables"]) and all(isinstance(TFTBasic_initial["sets"][i]["traits"][j]["effects"][k][l], int) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["traits"])) for k in range(len(TFTBasic_initial["sets"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style"]) and all(isinstance(TFTBasic_initial["sets"][i]["traits"][j]["effects"][k][l], dict) for i in TFTBasic_initial["sets"] for j in range(len(TFTBasic_initial["sets"][i]["traits"])) for k in range(len(TFTBasic_initial["sets"][i]["traits"][j]["effects"])) for l in ["variables"]):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈基础数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT basic data archived in CommunityDragon database (%s)!" %(TFTBasic_url, TFTBasic_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的云顶之弈基础信息Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT basics Json data file path!' %(TFTBasic_local, TFTBasic_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有云顶之弈基础信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT basic information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈基础数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT basic data archived in CommunityDragon database (%s)!" %(TFTBasic_url, TFTBasic_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取云顶之弈英雄数据（The following code get TFT champion data）
            try:
                logPrint("正在加载云顶之弈棋子信息……\nLoading TFT champion information from CommunityDragon ...")
                source, status, session = requestUrl("GET", TFTChampion_url, session = session, log = log)
                if source.ok:
                    TFTChampion_initial: list[dict[str, Any]] = source.json() #TFTChampion存储云顶之弈的棋子信息（Variable `TFTChampion_initial` stores information of TFT champions）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('云顶之弈英雄信息获取超时！正在尝试离线加载数据……\nTFT champion information capture timeout! Trying loading offline data ...\n请输入云顶之弈英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTChampion_local_default, TFTChampion_local_default))
                while True:
                    TFTChampion_local: str = logInput()
                    if TFTChampion_local == "":
                        TFTChampion_local = TFTChampion_local_default
                    elif TFTChampion_local[0] == "0":
                        logPrint("云顶之弈英雄信息获取失败！请检查系统网络状况和代理设置。\nTFT champion information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(TFTChampion_local, "r", encoding = "utf-8") as fp:
                            TFTChampion_initial = json.load(fp)
                        if isinstance(TFTChampion_initial, list) and all(isinstance(TFTChampion_initial[i], dict) for i in range(len(TFTChampion_initial))) and all(TFTChampion_initial[i].get(j, 0) for i in range(len(TFTChampion_initial)) for j in ["name", "character_record"]):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈棋子数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT champion data archived in CommunityDragon database (%s)!" %(TFTChampion_url, TFTChampion_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的云顶之弈棋子Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT champion Json data file path!' %(TFTChampion_local, TFTChampion_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有云顶之弈英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT champion information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈棋子数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT champion data archived in CommunityDragon database (%s)!" %(TFTChampion_url, TFTChampion_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取云顶之弈装备数据（The following code get TFT item information）
            try:
                logPrint("正在加载云顶之弈装备信息……\nLoading TFT item information from CommunityDragon ...")
                source, status, session = requestUrl("GET", TFTItem_url, session = session, log = log)
                if source.ok:
                    TFTItem_initial: list[dict[str, Any]] = source.json() #TFTItem存储云顶之弈的装备信息（Variable `TFTItem_initial` stores information of TFT items）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('云顶之弈装备信息获取超时！正在尝试离线加载数据……\nTFT item information capture timeout! Trying loading offline data ...\n请输入云顶之弈装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTItem_local_default, TFTItem_local_default))
                while True:
                    TFTItem_local: str = logInput()
                    if TFTItem_local == "":
                        TFTItem_local = TFTItem_local_default
                    elif TFTItem_local[0] == "0":
                        logPrint("云顶之弈装备信息获取失败！请检查系统网络状况和代理设置。\nTFT item information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(TFTItem_local, "r", encoding = "utf-8") as fp:
                            TFTItem_initial = json.load(fp)
                        if isinstance(TFTItem_initial, list) and all(isinstance(TFTItem_initial[i], dict) for i in range(len(TFTItem_initial))) and (all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "loadoutsIcon"]) or all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "squareIconPath"])):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT item data archived in CommunityDragon database (%s)!" %(TFTItem_url, TFTItem_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的云顶之弈装备Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT item Json data file path!' %(TFTItem_local, TFTItem_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有云顶之弈装备信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT item data archived in CommunityDragon database (%s)!" %(TFTItem_url, TFTItem_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取云顶之弈小小英雄数据（The following code get TFT companion data）
            try:
                logPrint("正在加载云顶之弈小小英雄信息……\nLoading companion information from CommunityDragon ...")
                source, status, session = requestUrl("GET", TFTCompanion_url, session = session, log = log)
                if source.ok:
                    TFTCompanion_initial: list[dict[str, Any]] = source.json() #TFTChampion存储云顶之弈的小小英雄信息（Variable `TFTChampion_initial` stores information of companions）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('云顶之弈小小英雄信息获取超时！正在尝试离线加载数据……\nTFT companion information capture timeout! Trying loading offline data ...\n请输入云顶之弈小小英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT companion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTCompanion_local_default, TFTCompanion_local_default))
                while True:
                    TFTCompanion_local: str = logInput()
                    if TFTCompanion_local == "":
                        TFTCompanion_local = TFTCompanion_local_default
                    elif TFTCompanion_local[0] == "0":
                        logPrint("云顶之弈小小英雄信息获取失败！请检查系统网络状况和代理设置。\nTFT companion information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(TFTCompanion_local, "r", encoding = "utf-8") as fp:
                            TFTCompanion_initial = json.load(fp)
                        if isinstance(TFTCompanion_initial, list) and all(isinstance(TFTCompanion_initial[i], dict) for i in range(len(TFTCompanion_initial))) and all(j in TFTCompanion_initial[i] for i in range(len(TFTCompanion_initial)) for j in ["contentId", "itemId", "name", "loadoutsIcon", "description", "level", "speciesName", "speciesId", "rarity", "rarityValue", "isDefault", "upgrades", "TFTOnly"]):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈小小英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT companion data archived in CommunityDragon database (%s)!" %(TFTCompanion_url, TFTCompanion_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的云顶之弈小小英雄Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT companion Json data file path!' %(TFTCompanion_local, TFTCompanion_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有云顶之弈小小英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈小小英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT companion data archived in CommunityDragon database (%s)!" %(TFTCompanion_url, TFTCompanion_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取云顶之弈羁绊数据（The following code get TFT trait data）
            try:
                logPrint("正在加载云顶之弈羁绊信息……\nLoading TFT trait information from CommunityDragon ...")
                source, status, session = requestUrl("GET", TFTTrait_url, session = session, log = log)
                if source.ok:
                    TFTTrait_initial: list[dict[str, Any]] = source.json() #TFTTrait存储云顶之弈的羁绊信息（Variable `TFTTrait_initial` stores information of TFT traits）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('云顶之弈羁绊信息获取超时！正在尝试离线加载数据……\nTFT trait information capture timeout! Trying loading offline data ...\n请输入云顶之弈羁绊Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT trait Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTTrait_local_default, TFTTrait_local_default))
                while True:
                    TFTTrait_local: str = logInput()
                    if TFTTrait_local == "":
                        TFTTrait_local = TFTTrait_local_default
                    elif TFTTrait_local[0] == "0":
                        logPrint("云顶之弈羁绊信息获取失败！请检查系统网络状况和代理设置。\nTFT trait information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(TFTTrait_local, "r", encoding = "utf-8") as fp:
                            TFTTrait_initial = json.load(fp)
                        if isinstance(TFTTrait_initial, list) and all(isinstance(TFTTrait_initial[i], dict) for i in range(len(TFTTrait_initial))) and all(j in TFTTrait_initial[i] for i in range(len(TFTTrait_initial)) for j in ["display_name", "trait_id", "set", "icon_path", "tooltip_text", "innate_trait_sets", "conditional_trait_sets"]):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈羁绊数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT trait data archived in CommunityDragon database (%s)!" %(TFTTrait_url, TFTTrait_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的云顶之弈羁绊Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT trait Json data file path!' %(TFTTrait_local, TFTTrait_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有云顶之弈小小英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈羁绊数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT trait data archived in CommunityDragon database (%s)!" %(TFTTrait_url, TFTTrait_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            #下面获取斗魂竞技场强化符文数据（The following code get Arena augment data）
            try:
                logPrint("正在加载斗魂竞技场强化符文信息……\nLoading Arena augment information from CommunityDragon ...")
                source, status, session = requestUrl("GET", CherryAugment_url, session = session, log = log)
                if source.ok:
                    CherryAugment_initial: list[dict[str, Any]] = source.json() #Arena存储斗魂竞技场的强化符文信息（Variable `CherryAugment_initial` stores information of Arena augments）
                else:
                    logPrint(source)
                    logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                    switch_language = True
                    break
            except requests.exceptions.RequestException:
                logPrint('斗魂竞技场强化符文信息获取超时！正在尝试离线加载数据……\nArena augment information capture timeout! Trying loading offline data ...\n请输入斗魂竞技场强化符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the Arena augment Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(CherryAugment_local_default, CherryAugment_local_default))
                while True:
                    CherryAugment_local: str = logInput()
                    if CherryAugment_local == "":
                        CherryAugment_local = CherryAugment_local_default
                    elif CherryAugment_local[0] == "0":
                        logPrint("斗魂竞技场强化符文信息获取失败！请检查系统网络状况和代理设置。\nArena augment information capture failure! Please check the system network condition and proxy configuration.")
                        time.sleep(5)
                        return (switch_language, True)
                    else:
                        switch_prepare_mode = True
                        break
                    try:
                        with open(CherryAugment_local, "r", encoding = "utf-8") as fp:
                            CherryAugment_initial = json.load(fp)
                        if isinstance(CherryAugment_initial, list) and all(isinstance(CherryAugment_initial[i], dict) for i in range(len(CherryAugment_initial))) and all(j in CherryAugment_initial[i] for i in range(len(CherryAugment_initial)) for j in ["id", "nameTRA", "augmentSmallIconPath", "rarity"]) and all(isinstance(CherryAugment_initial[i]["id"], int) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["nameTRA"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["augmentSmallIconPath"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["rarity"], str) for i in range(len(CherryAugment_initial))):
                            break
                        else:
                            logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的斗魂竞技场强化符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the Arena augment data archived in CommunityDragon database (%s)!" %(CherryAugment_url, CherryAugment_url))
                    except FileNotFoundError:
                        logPrint('未找到文件“%s”！请输入正确的斗魂竞技场强化符文Json数据文件路径！\nFile "%s" NOT found! Please input a correct Arena augment Json data file path!' %(CherryAugment_local, CherryAugment_local))
                    except OSError:
                        logPrint("数据文件名不合法！请输入含有斗魂竞技场强化符文信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with Arena augment information.")
                    except json.decoder.JSONDecodeError:
                        logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的斗魂竞技场强化符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the Arena augment data archived in CommunityDragon database (%s)!" %(CherryAugment_url, CherryAugment_url))
            if switch_prepare_mode:
                prepareMode = ""
                continue
            break
        else:
            switch_prepare_mode = False
            logPrint('请在浏览器中打开以下网页，待加载完成后按Ctrl + S保存网页json文件至同目录的“离线数据（Offline Data）”文件夹下，并根据括号内的提示放置和命名文件。\nPlease open the following URLs in a browser, then press Ctrl + S to save the online json files into the folder "离线数据（Offline Data）" under the same directory after the website finishes loading and organize and rename the downloaded files according to the hints in the circle brackets.\n版本信息（%s）： %s\n游戏模式（%s）： %s\n召唤师技能（%s）： %s\n英雄（%s）： %s\n英雄联盟装备（%s）： %s\n召唤师图标（%s）： %s\n基石符文（%s）： %s\n符文系（%s）： %s\n云顶之弈基础信息（%s）： %s\n云顶之弈棋子（%s）： %s\n云顶之弈装备（%s）： %s\n云顶之弈小小英雄（%s）： %s\n云顶之弈羁绊（%s）： %s\n斗魂竞技场强化符文（%s）： %s' %(patches_local_default[19:], patches_url, queue_local_default[19:], queue_url, spell_local_default[19:], spell_url, LoLChampion_local_default[19:], LoLChampion_url, LoLItem_local_default[19:], LoLItem_url, summonerIcon_local_default[19:], summonerIcon_url, perk_local_default[19:], perk_url, perkstyle_local_default[19:], perkstyle_url, TFTBasic_local_default[19:], TFTBasic_url, TFTChampion_local_default[19:], TFTChampion_url, TFTItem_local_default[19:], TFTItem_url, TFTCompanion_local_default[19:], TFTCompanion_url, TFTTrait_local_default[19:], TFTTrait_url, CherryAugment_local_default[19:], CherryAugment_url))
            offline_files_loaded: dict[str, bool] = {"patch": False, "queue": False, "spell": False, "LoLChampion": False, "LoLItem": False, "summonerIcon": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "CherryAugment": False}
            offline_files: dict[str, dict[str, str]] = {"patch": {"file": patches_local_default, "URL": patches_url, "content": "版本信息"}, "queue": {"file": queue_local_default, "URL": queue_url, "content": "游戏模式"}, "spell": {"file": spell_local_default, "URL": spell_url, "content": "召唤师技能"}, "LoLChampion": {"file": LoLChampion_local_default, "URL": LoLChampion_url, "content": "英雄"}, "LoLItem": {"file": LoLItem_local_default, "URL": LoLItem_url, "content": "英雄联盟装备"}, "summonerIcon": {"file": summonerIcon_local_default, "URL": summonerIcon_url, "content": "召唤师图标"}, "perk": {"file": perk_local_default, "URL": perk_url, "content": "基石符文"}, "perkstyle": {"file": perkstyle_local_default, "URL": perkstyle_url, "content": "符文系"}, "TFT": {"file": TFTBasic_local_default, "URL": TFTBasic_url, "content": "云顶之弈基础信息"}, "TFTChampion": {"file": TFTChampion_local_default, "URL": TFTChampion_url, "content": "云顶之弈英雄"}, "TFTItem": {"file": TFTItem_local_default, "URL": TFTItem_url, "content": "云顶之弈装备"}, "TFTCompanion": {"file": TFTCompanion_local_default, "URL": TFTCompanion_url, "content": "云顶之弈小小英雄"}, "TFTTrait": {"file": TFTTrait_local_default, "URL": TFTTrait_url, "content": "云顶之弈羁绊"}, "CherryAugment": {"file": CherryAugment_local_default, "URL": CherryAugment_url, "content": "斗魂竞技场强化符文"}}
            logPrint('按回车键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPress Enter to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
            while any(not i for i in offline_files_loaded.values()):
                offline_files_notfound: dict[str, bool] = {"patch": False, "queue": False, "spell": False, "LoLChampion": False, "LoLItem": False, "summonerIcon": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "CherryAugment": False}
                offline_files_formaterror: dict[str, bool] = {"patch": False, "queue": False, "spell": False, "LoLChampion": False, "LoLItem": False, "summonerIcon": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "CherryAugment": False}
                prepareMode = logInput()
                if prepareMode != "" and prepareMode[0] == "1":
                    switch_prepare_mode = True
                    break
                if prepareMode != "" and prepareMode[0] == "0":
                    return (switch_language, True)
                #下面获取版本信息（The following code get the patch data）
                if not offline_files_loaded["patch"]:
                    try:
                        with open(patches_local_default, "r", encoding = "utf-8") as fp:
                            patches_initial = json.load(fp)
                        if not (isinstance(patches_initial, list) and patches_initial[-1] == "lolpatch_3.7"): #之所以将patches的最后一个元素作为判断版本文件数据格式合法的依据，是因为按照这样的逻辑，代码在一般情况下就不需要频繁变动（The reason why I use the last element of the variable `patches_initial` as the judgment whether the patch file data format is legal is, that under this logic, the code won't need further adjustment as the update goes on）
                            offline_files_formaterror["patch"] = True
                    except FileNotFoundError:
                        offline_files_notfound["patch"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["patch"] = True
                    else:
                        if not offline_files_formaterror["patch"]:
                            offline_files_loaded["patch"] = True
                            latest_patch = patches_initial[0]
                            patches_dict = {}
                            smallPatches = []
                            bigPatches = []
                            for patch in patches_initial:
                                if not patch.startswith("lolpatch"):
                                    patch_split = patch.split(".")
                                    smallPatch = ".".join(patch_split[:3])
                                    smallPatches.append(Patch(smallPatch))
                                    bigPatch = ".".join(patch_split[:2])
                                    bigPatches.append(Patch(bigPatch))
                                    patches_dict[bigPatch] = []
                            for i in range(len(bigPatches)):
                                patches_dict[str(bigPatches[i])].append(str(smallPatches[i]))
                #下面获取游戏模式数据（The following code get game mode data）
                if not offline_files_loaded["queue"]:
                    try:
                        with open(queue_local_default, "r", encoding = "utf-8") as fp:
                            queue_initial = json.load(fp)
                        if not(isinstance(queue_initial, list) and all(map(lambda x: all(i in x for i in ["id", "name", "shortName", "description", "detailedDescription", "gameSelectModeGroup", "gameSelectCategory", "gameSelectPriority", "isSkillTreeQueue", "isLimitedTimeQueue", "isBotHonoringAllowed", "hidePlayerPosition", "viableChampionRoster"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], int) for i in ["id", "gameSelectPriority"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], str) for i in ["name", "shortName", "description", "detailedDescription", "gameSelectModeGroup", "gameSelectCategory"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], bool) for i in ["isSkillTreeQueue", "isLimitedTimeQueue", "isBotHonoringAllowed", "hidePlayerPosition"]), queue_initial)) and all(map(lambda x: all(isinstance(x[i], list) or x[i] is None for i in ["viableChampionRoster"]), queue_initial))):
                            offline_files_formaterror["queue"] = True
                    except FileNotFoundError:
                        offline_files_notfound["queue"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["queue"] = True
                    else:
                        if not offline_files_formaterror["queue"]:
                            offline_files_loaded["queue"] = True
                #下面获取召唤师技能数据（The following code get summoner spell data）
                if not offline_files_loaded["spell"]:
                    try:
                        with open(spell_local_default, "r", encoding = "utf-8") as fp:
                            spell_initial = json.load(fp)
                        if not(isinstance(spell_initial, list) and all(i in spell_initial[j] for i in ["id", "name", "description", "summonerLevel", "cooldown", "gameModes", "iconPath"] for j in range(len(spell_initial)))):
                            offline_files_formaterror["spell"] = True
                    except FileNotFoundError:
                        offline_files_notfound["spell"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["spell"] = True
                    else:
                        if not offline_files_formaterror["spell"]:
                            offline_files_loaded["spell"] = True
                #下面获取英雄信息（The following code get LoL champion data）
                if not offline_files_loaded["LoLChampion"]:
                    try:
                        with open(LoLChampion_local_default, "r", encoding = "utf-8") as fp:
                            LoLChampion_initial = json.load(fp)
                        if not(isinstance(LoLChampion_initial, list) and all(isinstance(LoLChampion_initial[i], dict) for i in range(len(LoLChampion_initial))) and all(j in LoLChampion_initial[i] for i in range(len(LoLChampion_initial)) for j in ["id", "name", "alias", "squarePortraitPath", "roles"]) and all(isinstance(LoLChampion_initial[i]["id"], int) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["name"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["alias"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["squarePortraitPath"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["roles"], list) for i in range(len(LoLChampion_initial)))):
                            offline_files_formaterror["LoLChampion"] = True
                    except FileNotFoundError:
                        offline_files_notfound["LoLChampion"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["LoLChampion"] = True
                    else:
                        if not offline_files_formaterror["LoLChampion"]:
                            offline_files_loaded["LoLChampion"] = True
                #下面获取英雄联盟装备信息（The following code get LoL item data）
                if not offline_files_loaded["LoLItem"]:
                    try:
                        with open(LoLItem_local_default, "r", encoding = "utf-8") as fp:
                            LoLItem_initial = json.load(fp)
                        if not(isinstance(LoLItem_initial, list) and all(i in LoLItem_initial[j] for i in ["id", "name", "description", "active", "inStore", "from", "to", "categories", "maxStacks", "requiredChampion", "requiredAlly", "requiredBuffCurrencyName", "requiredBuffCurrencyCost", "specialRecipe", "isEnchantment", "price", "priceTotal", "iconPath"] for j in range(len(LoLItem_initial)))):
                            offline_files_formaterror["LoLItem"] = True
                    except FileNotFoundError:
                        offline_files_notfound["LoLItem"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["LoLItem"] = True
                    else:
                        if not offline_files_formaterror["LoLItem"]:
                            offline_files_loaded["LoLItem"] = True
                #下面获取召唤师图标信息（The following code get summoner icon data）
                if not offline_files_loaded["summonerIcon"]:
                    try:
                        with open(summonerIcon_local_default, "r", encoding = "utf-8") as fp:
                            summonerIcon_initial = json.load(fp)
                        if not(isinstance(summonerIcon_initial, list) and all(map(lambda x: isinstance(x, dict), summonerIcon_initial)) and all(i in j for i in ["id", "title", "yearReleased", "isLegacy", "descriptions", "rarities", "disabledRegions"] for j in summonerIcon_initial)):
                            offline_files_formaterror["summonerIcon"] = True
                    except FileNotFoundError:
                        offline_files_notfound["summonerIcon"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["summonerIcon"] = True
                    else:
                        if not offline_files_formaterror["summonerIcon"]:
                            offline_files_loaded["summonerIcon"] = True
                #下面获取基石符文信息（The following code get perk data）
                if not offline_files_loaded["perk"]:
                    try:
                        with open(perk_local_default, "r", encoding = "utf-8") as fp:
                            perk_initial = json.load(fp)
                        if not(isinstance(perk_initial, list) and all(i in perk_initial[j] for i in ["id", "name", "majorChangePatchVersion", "tooltip", "shortDesc", "longDesc", "recommendationDescriptor", "iconPath", "endOfGameStatDescs", "recommendationDescriptorAttributes"] for j in range(len(perk_initial)))):
                            offline_files_formaterror["perk"] = True
                    except FileNotFoundError:
                        offline_files_notfound["perk"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["perk"] = True
                    else:
                        if not offline_files_formaterror["perk"]:
                            offline_files_loaded["perk"] = True
                #下面获取符文系信息（The following code get perkstyle data）
                if not offline_files_loaded["perkstyle"]:
                    try:
                        with open(perkstyle_local_default, "r", encoding = "utf-8") as fp:
                            perkstyle_initial = json.load(fp)
                        if not(isinstance(perkstyle_initial, dict) and all(perkstyle_initial.get(i, 0) for i in ["schemaVersion", "styles"]) and isinstance(perkstyle_initial["styles"], list) and all(j in perkstyle_initial["styles"][i] for i in range(len(perkstyle_initial["styles"])) for j in ["id", "name", "tooltip", "iconPath", "assetMap", "isAdvanced", "allowedSubStyles", "subStyleBonus", "slots", "defaultPageName", "defaultSubStyle", "defaultPerks", "defaultPerksWhenSplashed", "defaultStatModsPerSubStyle"])):
                            offline_files_formaterror["perkstyle"] = True
                    except FileNotFoundError:
                        offline_files_notfound["perkstyle"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["perkstyle"] = True
                    else:
                        if not offline_files_formaterror["perkstyle"]:
                            offline_files_loaded["perkstyle"] = True
                #下面获取云顶之弈强化符文数据（The following code get TFT augment data）
                if not offline_files_loaded["TFT"]:
                    try:
                        with open(TFTBasic_local_default, "r", encoding = "utf-8") as fp:
                            TFTBasic_initial = json.load(fp)
                        if not(isinstance(TFTBasic_initial, dict) and all(i in TFTBasic_initial for i in ["items", "setData", "sets"])):
                            offline_files_formaterror["TFT"] = True
                    except FileNotFoundError:
                        offline_files_notfound["TFT"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["TFT"] = True
                    else:
                        if not offline_files_formaterror["TFT"]:
                            offline_files_loaded["TFT"] = True
                #下面获取云顶之弈英雄数据（The following code get TFT champion data）
                if not offline_files_loaded["TFTChampion"]:
                    try:
                        with open(TFTChampion_local_default, "r", encoding = "utf-8") as fp:
                            TFTChampion_initial = json.load(fp)
                        if not(isinstance(TFTChampion_initial, list) and all(isinstance(TFTChampion_initial[i], dict) for i in range(len(TFTChampion_initial))) and all(TFTChampion_initial[i].get(j, 0) for i in range(len(TFTChampion_initial)) for j in ["name", "character_record"])):
                            offline_files_formaterror["TFTChampion"] = True
                    except FileNotFoundError:
                        offline_files_notfound["TFTChampion"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["TFTChampion"] = True
                    else:
                        if not offline_files_formaterror["TFTChampion"]:
                            offline_files_loaded["TFTChampion"] = True
                #下面获取云顶之弈装备数据（The following code get TFT item information）
                if not offline_files_loaded["TFTItem"]:
                    try:
                        with open(TFTItem_local_default, "r", encoding = "utf-8") as fp:
                            TFTItem_initial = json.load(fp)
                        if not(isinstance(TFTItem_initial, list) and all(isinstance(TFTItem_initial[i], dict) for i in range(len(TFTItem_initial))) and (all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "loadoutsIcon"]) or all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "squareIconPath"]))):
                            offline_files_formaterror["TFTItem"] = True
                    except FileNotFoundError:
                        offline_files_notfound["TFTItem"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["TFTItem"] = True
                    else:
                        if not offline_files_formaterror["TFTItem"]:
                            offline_files_loaded["TFTItem"] = True
                #下面获取云顶之弈小小英雄数据（The following code get TFT companion data）
                if not offline_files_loaded["TFTCompanion"]:
                    try:
                        with open(TFTCompanion_local_default, "r", encoding = "utf-8") as fp:
                            TFTCompanion_initial = json.load(fp)
                        if not(isinstance(TFTCompanion_initial, list) and all(isinstance(TFTCompanion_initial[i], dict) for i in range(len(TFTCompanion_initial))) and all(j in TFTCompanion_initial[i] for i in range(len(TFTCompanion_initial)) for j in ["contentId", "itemId", "name", "loadoutsIcon", "description", "level", "speciesName", "speciesId", "rarity", "rarityValue", "isDefault", "upgrades", "TFTOnly"])):
                            offline_files_formaterror["TFTCompanion"] = True
                    except FileNotFoundError:
                        offline_files_notfound["TFTCompanion"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["TFTCompanion"] = True
                    else:
                        if not offline_files_formaterror["TFTCompanion"]:
                            offline_files_loaded["TFTCompanion"] = True
                #下面获取云顶之弈羁绊数据（The following code get TFT trait data）
                if not offline_files_loaded["TFTTrait"]:
                    try:
                        with open(TFTTrait_local_default, "r", encoding = "utf-8") as fp:
                            TFTTrait_initial = json.load(fp)
                        if not(isinstance(TFTTrait_initial, list) and all(isinstance(TFTTrait_initial[i], dict) for i in range(len(TFTTrait_initial))) and all(j in TFTTrait_initial[i] for i in range(len(TFTTrait_initial)) for j in ["display_name", "trait_id", "set", "icon_path", "tooltip_text", "innate_trait_sets", "conditional_trait_sets"])):
                            offline_files_formaterror["TFTTrait"] = True
                    except FileNotFoundError:
                        offline_files_notfound["TFTTrait"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["TFTTrait"] = True
                    else:
                        if not offline_files_formaterror["TFTTrait"]:
                            offline_files_loaded["TFTTrait"] = True
                #下面获取斗魂竞技场强化符文数据（The following code get Arena augment data）
                if not offline_files_loaded["CherryAugment"]:
                    try:
                        with open(CherryAugment_local_default, "r", encoding = "utf-8") as fp:
                            CherryAugment_initial = json.load(fp)
                        if not(isinstance(CherryAugment_initial, list) and all(isinstance(CherryAugment_initial[i], dict) for i in range(len(CherryAugment_initial))) and all(j in CherryAugment_initial[i] for i in range(len(CherryAugment_initial)) for j in ["id", "nameTRA", "augmentSmallIconPath", "rarity"]) and all(isinstance(CherryAugment_initial[i]["id"], int) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["nameTRA"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["augmentSmallIconPath"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["rarity"], str) for i in range(len(CherryAugment_initial)))):
                            offline_files_formaterror["CherryAugment"] = True
                    except FileNotFoundError:
                        offline_files_notfound["CherryAugment"] = True
                    except json.decoder.JSONDecodeError:
                        offline_files_formaterror["CherryAugment"] = True
                    else:
                        if not offline_files_formaterror["CherryAugment"]:
                            offline_files_loaded["CherryAugment"] = True
                #下面总结离线数据加载情况（The following code conclude the result of loading offline data）
                unloaded_offline_files: list[str] = []
                notfound_offline_files: list[str] = []
                formaterror_offline_files: list[str] = []
                if any(offline_files_notfound.values()):
                    for i in offline_files_notfound:
                        if offline_files_notfound[i]:
                            notfound_offline_files.append(i)
                            unloaded_offline_files.append(i)
                    logPrint("以下信息文件不存在：\nNot existing file(s):")
                    for i in notfound_offline_files:
                        logPrint(offline_files[i]["file"] + "\t" + offline_files[i]["content"] + "\t" + offline_files[i]["URL"])
                if any(offline_files_formaterror.values()):
                    for i in offline_files_formaterror:
                        if offline_files_formaterror[i]:
                            formaterror_offline_files.append(i)
                            unloaded_offline_files.append(i)
                    logPrint("以下信息文件格式错误：\nFormatError file(s):")
                    for i in formaterror_offline_files:
                        logPrint(offline_files[i]["file"] + "\t" + offline_files[i]["content"] + "\t" + offline_files[i]["URL"])
                if any(not i for i in offline_files_loaded.values()):
                    logPrint('按回车键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPress Enter to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
            if not switch_prepare_mode:
                break
    if not switch_language:
        ##准备游戏模式数据（Prepare game mode data）
        queues_initial = {int(queue_iter["id"]): queue_iter for queue_iter in queue_initial}
        ##准备召唤师技能数据（Prepare summoner spell data）
        spells_initial = {int(spell_iter["id"]): spell_iter for spell_iter in spell_initial}
        ##准备英雄数据（Prepare champion data）
        LoLChampions_initial = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion_initial}
        ##准备英雄联盟装备数据（Prapare LoL item data）
        LoLItems_initial = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem_initial}
        ##准备召唤师图标数据（Prepare summoner icon data）
        summonerIcons_initial = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon_initial}
        ##准备符文数据（Prepare runes data）
        perks_initial = {int(perk_iter["id"]): perk_iter for perk_iter in perk_initial}
        ##准备符文系数据（Prepare perkstyle data）
        perkstyles_initial = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle_initial["styles"]}
        ##准备云顶之弈强化符文数据（Prepare TFT augment data）
        TFTAugments_initial = {item["apiName"]: item for item in TFTBasic_initial["items"]}
        ##准备云顶之弈英雄数据（Prepare TFT champion data）
        TFTChampions_initial = {TFTChampion_iter["name"]: TFTChampion_iter["character_record"] for TFTChampion_iter in TFTChampion_initial}
        ##准备云顶之弈装备数据（Prepare TFT item data）
        TFTItems_initial = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItem_initial}
        ##准备云顶之弈小小英雄数据（Prepare TFT companion data）
        TFTCompanions_initial = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanion_initial}
        ##准备云顶之弈羁绊数据（Prepare TFT trait data）
        TFTTraits_initial = {} #TFTTraits为嵌套字典，键为羁绊在LCU API上的表达形式，值为羁绊信息字典。一个键值对的示例如右：（Variable `TFTTraits` is a nested dictionary, whose keys are LCU API representation of traits and values are trait information dictionaries. An example of the key-value pairs is shown as follows: ）{"Assassin": {"display_name": "刺客", "set": "TFTSet1", "icon_path": "/lol-game-data/assets/ASSETS/UX/TraitIcons/Trait_Icon_Assassin.png", "tooltip_text": "固有：在战斗环节开始时，刺客们会跃至距离最远的敌人处。<br><br>刺客们会获得额外的暴击伤害和暴击几率。<br><br><expandRow>(@MinUnits@) +@CritAmpPercent@%暴击伤害和+@CritChanceAmpPercent@%暴击几率</expandRow><br>", "innate_trait_sets": [], "conditional_trait_sets": {2: {"effect_amounts": [{"name": "CritAmpPercent", "value": 75.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 5.0, "format_string": ""}], "min_units": 3, "max_units": 5, "style_name": "kBronze"}, 3: {"effect_amounts": [{"name": "CritAmpPercent", "value": 150.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 20.0, "format_string": ""}], "min_units": 6, "max_units": 8, "style_name": "kSilver"}, 4: {"effect_amounts": [{"name": "CritAmpPercent", "value": 225.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 30.0, "format_string": ""}], "min_units": 9, "max_units": 25000, "style_name": "kGold"}}}}
        for trait_iter in TFTTrait_initial:
            trait_id: str = trait_iter["trait_id"]
            conditional_trait_sets = {}
            for conditional_trait_set in trait_iter["conditional_trait_sets"]:
                style_idx: str = conditional_trait_set["style_idx"]
                conditional_trait_sets[style_idx] = conditional_trait_set
            trait_iter["conditional_trait_sets"] = conditional_trait_sets
            TFTTraits_initial[trait_id] = trait_iter
        ##准备斗魂竞技场强化符文数据（Prepare Arena augment data）
        CherryAugments_initial = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment_initial}
    return (switch_language, False)

async def prepare_lcu_plugins(connection: Connection) -> None:
    '''
    从LCU插件中读取实时数据资源。<br>Read real-time data resources from LCU plugin.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    global wardSkins, championSkins
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

async def load_smurf(connection: Connection, current_puuid: str, infos: Optional[dict[str, dict[str, Any]]] = None) -> list[dict[str, Any]]:
    '''
    读取小号信息。<br>Load smurf information.
    
    用户可以手动输入小号，也可以选择从一个本地文件读取。读取完成后，也可以选择更新本地的小号信息。<br>Users may choose to manually input smurf information, or load smurfs from a local file. After loading, the user can decide whether to update the local smurf information.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param current_puuid: 主召唤师的玩家通用唯一识别码。<br>The main summoner's puuid.
    :type current_puuid: str
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :return: 小号信息列表。<br>A list of smurfs.
    :rtype: list[dict[str, Any]]
    '''
    if infos == None:
        infos = {}
    smurfs: list[dict[str, Any]] = []
    logPrint("是否导入其它账号？（输入任意非空字符串以导入，否则不导入。）\nImport other accounts? (Submit any non-empty string to import, or null to refuse importing.)")
    smurfMode_str: str = logInput()
    smurfMode: bool = bool(smurfMode_str)
    if smurfMode:
        smurf_header: dict[str, str] = {"displayName": "显示名", "gameName": "玩家名称", "tagLine": "名称编号", "summonerId": "召唤师序号", "puuid": "玩家通用唯一识别码"}
        smurf_df: pandas.DataFrame = pandas.DataFrame(data = smurf_header, index = [0])
        logPrint("请选择导入方式：\nPlease select an option to import:\n☆1\t读取文件（Read a file）\n2\t手动输入（Manually input）")
        smurf_option: str = logInput()
        if smurf_option != "" and smurf_option[0] == "2":
            smurf_option = "2"
        else:
            smurf_option = "1"
        #在下面的代码中，关键是列表`smurfs`中追加小号信息（The key point of the following code is to append smurf information into the list `smurfs`）
        smurf_file_read: bool = False #标记程序是否成功读取到含有小号信息的数据文件（Marks whether the smurf data file is read successfully）
        smurf_file: str = "Smurf Accounts.json"
        smurf_file_rename: str = "Smurf Accounts (Invalid).json"
        smurf_local: dict[str, dict[str, list[str]]] = {}
        if smurf_option == "1":
            while os.path.exists(smurf_file_rename): #确保下面的重命名操作不会引发报错（Ensure the following renaming operation won't cause an error）
                smurf_file_rename = os.path.splitext(smurf_file_rename)[0] + "(1)." + os.path.splitext(smurf_file_rename)[1]
            if os.path.exists(smurf_file):
                try:
                    with open(smurf_file, "r", encoding = "utf-8") as fp:
                        smurf_local = json.load(fp)
                except json.decoder.JSONDecodeError:
                    os.rename(smurf_file, smurf_file_rename) #上面的while循环保证这里重命名后的文件不可能存在（The above while-loop ensures the result file can't exist）
                    logPrint(f'''在同目录下发现了格式不正确的数据文件。该文件已重命名为“{smurf_file_rename}”。程序将转为手动输入。\nA smurf data file with invalid format is found under the same directory. This file has been renamed into "{smurf_file_rename}". You may need to input the smurfs' names manually.''')
                    smurf_option = "2"
                else:
                    if isinstance(smurf_local, dict) and all(map(lambda x: x in valid_platformIds, smurf_local.keys())) and all(map(lambda x: isinstance(x, dict), smurf_local.values())) and all(len(smurf_local_iter) == 0 or all(map(lambda x: isinstance(x, str) and verify_uuid(x), smurf_local_iter.keys())) and all(map(lambda x: isinstance(x, list) and all(map(lambda y: isinstance(y, str) and verify_uuid(y), x)), smurf_local_iter.values())) for smurf_local_iter in smurf_local.values()): #格式的严格校验（A serious verification of the format）
                        smurf_file_read = True
                        if platformId in smurf_local:
                            if current_puuid in smurf_local[platformId]:
                                count: int = 0 #标识小号的序号（Number the smurfs）
                                valid_puuid_count: int = 0 #记录能查询到玩家的玩家通用唯一识别码的数量（Record the number of puuids that can correspond to players）
                                for smurf_puuid in smurf_local[platformId][current_puuid]:
                                    count += 1
                                    logPrint(f"{count}.\t{smurf_puuid}")
                                    info: dict[str, Any] = await get_info(connection, smurf_puuid)
                                    if info["info_got"]:
                                        info_body: dict[str, Any] = info["body"]
                                        if not info_body["puuid"] in list(map(lambda x: x["puuid"], smurfs)):
                                            valid_puuid_count += 1
                                            logPrint(info_body)
                                            smurfs.append(info_body)
                                            smurf_record: dict[str, Any] = {key: info["body"][key] for key in smurf_header}
                                            smurf_df: pandas.DataFrame = pandas.concat([smurf_df, pandas.DataFrame([smurf_record])], ignore_index = True)
                                            print(format_df(smurf_df, width_exceed_ask = False, direct_print = False, print_index = True)[0], end = "\n\n")
                                            log.write(format_df(smurf_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n\n")
                                            infos[info_body["puuid"]] = info_body
                                    else:
                                        logPrint(info["message"])
                                logPrint(f"从离线文件中读取到了{valid_puuid_count}个小号信息。是否继续输入更多小号？（输入任意键以继续添加小号，否则不添加。）\nThe program has detected {valid_puuid_count} smurf account(s) from the local file. Do you want to continue with more smurf accounts? (Submit any non-empty string to continue, or null to refuse adding.)")
                                input_more_smurf_str: str = logInput()
                                smurf_option = "2" if bool(input_more_smurf_str) else "1"
                            else:
                                logPrint("在同目录下发现了含有小号信息的数据文件，但是没有找到您的小号信息。程序将转为手动输入。\nThe smurf data file is found under the same directory, but without yours. You may need to input the smurfs' names manually.")
                                smurf_option = "2"
                        else:
                            logPrint("在同目录下发现了含有小号信息的数据文件，但是没有找到您的大区信息。如果您确认您的本地文件没有问题，请向作者反馈该问题。\nThe smurf data file is found under the same directory, but without your server's. If you're sure that there's not any problem in your local data file, please file the feedback to the author.\n一个可用的反馈链接：\nAn available feedback link:\nhttps://github.com/WordlessMeteor/LoL-DIY-Programs/issues/new \n程序将转为手动输入。\nYou may need to input the smurfs' names manually.")
                            smurf_option = "2"
                    else:
                        os.rename(smurf_file, smurf_file_rename)
                        logPrint(f'''在同目录下发现了格式不正确的数据文件。该文件已重命名为“{smurf_file_rename}”。程序将转为手动输入。\nA smurf data file with invalid format is found under the same directory. This file has been renamed into "{smurf_file_rename}". You may need to input the smurfs' names manually.''')
                        smurf_option = "2"
            else:
                logPrint("没有找到含有小号信息的数据文件。程序将转为手动输入。\nSmurf data file not found. You may need to input the smurfs' names manually.")
                smurf_option = "2"
        if smurf_option == "2":
            logPrint('请输入小号的召唤师名。输入“0”以清空已经输入的小号。输入-1以结束。\nPlease input the summoner names of the smurf accounts. Submit "0" to clear the entered smurfs. Submit "-1" to finish the importation.')
            while True:
                smurfName: str = logInput()
                if smurfName == "-1":
                    break
                elif smurfName == "0":
                    smurfs = []
                    smurf_df = pandas.DataFrame(data = smurf_header, index = [0])
                    logPrint("已清空小号。\nSmurfs cleared.")
                elif smurfName == "":
                    continue
                else:
                    info: dict[str, Any] = await get_info(connection, smurfName)
                    if info["info_got"]:
                        info_body: dict[str, Any] = info["body"]
                        if info_body["puuid"] == current_puuid:
                            logPrint("您不能把主账号作为小号！请添加其它账号。\nYou're not allowed to add your main account as a smurf account! Please try another account.")
                        elif info_body["puuid"] in list(map(lambda x: x["puuid"], smurfs)):
                            logPrint("您已经输入过该玩家了。\nYou've entered this player.")
                        else:
                            logPrint(info_body)
                            smurfs.append(info_body)
                            smurf_record: dict[str, Any] = {key: info["body"][key] for key in smurf_header}
                            smurf_df: pandas.DataFrame = pandas.concat([smurf_df, pandas.DataFrame([smurf_record])], ignore_index = True)
                            print(format_df(smurf_df, width_exceed_ask = False, direct_print = False, print_index = True)[0])
                            log.write(format_df(smurf_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                            infos[info_body["puuid"]] = info_body
                    else:
                        logPrint(info["message"])
        logPrint("是否需要将小号信息保存到本地，以便日后直接读取文件来添加小号？（输入任意键以确认，否则不保存。）\nDo you want to save the smurf information into a local data file, so that you may read this file directly to load the smurfs? (Submit any non-empty string to confirm, or null to refuse saving.)\n注意：程序会覆盖之前的小号信息，因此如果您不想丢失以前的小号信息，请在不输入任何字符的情况下直接按回车键不保存，然后将原来的小号信息做好备份。\nNote: The old smurf information will be overwritten, so if you expect the previous smurf information not to be lost, please directly press Enter without any other characters entered, and then make a backup of the original smurf information.")
        save_smurf_str: str = logInput()
        save_smurf: bool = bool(save_smurf_str)
        if save_smurf:
            if smurf_file_read:
                if platformId in smurf_local:
                    smurf_local[platformId][current_puuid] = list(map(lambda x: x["puuid"], smurfs)) #之所以考虑用玩家通用唯一识别码，而不用召唤师名或者召唤师序号作为小号信息存储介质的原因有两个方面的考量：从对人类友好的角度上，召唤师名的确更胜一筹，但是缺少唯一性。在调用get_info函数时，两个召唤师名如果只是差几个空格，就很有可能指向同一个召唤师。这样，上面和下面的代码在识别召唤师信息是否添加过时，就不太好实现；从存储格式的角度上来考虑，玩家通用唯一识别码服从通用唯一识别码的格式，相对比较统一，而且是全球统一的，这样在校验数据文件格式时比较方便。而召唤师序号只是整数，而且不同召唤师序号存在长短不一的情况，这样校验起来不够充分（The reason why I consider using puuid as the smurf data storing media, instead of the summoner name or summonerId, has two considerations. On the one hand, in terms of being human-friendly, a summoner name does far outweigh the puuid or summonerId. However, it lacks uniformity. When `get_info` function is called, if two parameters differ only in several spaces, the result might directs to a same summoner. In that case, it's not easy to implement the code to identify whether a summoner's information has been added to the list before, within the context. On the other hand, in terms of the format, a puuid obeys the format of uuids, so it's relatively general, let alone being "universally unqiue", which makes it convenient to verify the format of the smurf data file. Nevertheless, summonerId is just an integer, and different summonerIds may be of different lengths, so it's not sufficient to determine a summoner by summonerId）
                else:
                    smurf_local[platformId] = {current_puuid: list(map(lambda x: x["puuid"], smurfs))}
            else:
                smurf_local: dict[str, dict[str, list[str]]] = {platformId: {current_puuid: list(map(lambda x: x["puuid"], smurfs))}}
            with open(smurf_file, "w", encoding = "utf-8") as fp:
                json.dump(smurf_local, fp, indent = 4, ensure_ascii = False)
            logPrint(f"小号信息已保存到“{smurf_file}”中。\nSmurf information has been saved into {smurf_file}.")
    return smurfs

async def detect_mode(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame, language_code: str, infos: Optional[dict[str, dict[str, Any]]] = None) -> bool:
    '''
    检测模式。由此函数进入各个检测场景。<br>Detect mode. The entry to scenarios.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    :param language_code: 语言文化代码。用于确定数据资源链接。<br>Language code. Used to determine links to data resources.
    :type language_code: str
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :return: 是否更新对局记录数据。<br>Whether to update match history data.
    :rtype: bool
    '''
    if infos == None:
        infos = {}
    #下面根据用户的游戏状态推荐选项（Recommend an option according to the user's gameflow phase）
    option1_highlight: bool = False
    option2_highlight: bool = False
    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase == "None":
        option2_highlight = True
    elif gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck"}:
        lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        if len(lobby_information["members"]) > 1:
            option1_highlight = True
        else:
            option2_highlight = True
    elif gameflow_phase == "ChampSelect":
        champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        if "errorCode" in champ_select_session:
            option2_highlight = True
        else:
            if champ_select_session["isSpectating"] or len(champ_select_session["myTeam"]) + len(champ_select_session["theirTeam"]) > 1: #这里没有对信息可见性作进一步的讨论。将信息不可见的玩家视为新玩家是合理的（Here we don't discuss further based on the information visibility. It's appropriate that we regard an invisible player as a new player）
                option1_highlight = True
            else:
                option2_highlight = True
    elif gameflow_phase in {"InProgress", "Reconnect"}:
        gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        if len(gameflow_session["gameData"]["playerChampionSelections"]) > 1:
            option1_highlight = True
        else:
            option2_highlight = True
    logPrint("请选择检测场景：\nPlease select the scenario to detect:\n%s1\t房间内/英雄选择阶段/游戏中（In-lobby/During champ select/In-game）\n%s2\t过往对局（Previous game）\n3\t过往英雄选择阶段（仅英雄联盟）【Previous champ select (LoL only)】\n4\t好友列表（Friend list）\n5\t好友请求（Friend requests）\n6\t组队邀请（Party invitations）\n7\t聊天黑名单（Block list）\n8\t自定义召唤师名称列表（Custom summoner name list）" %("☆" if option1_highlight else "", "☆" if option2_highlight else ""))
    detect_scene: str = logInput()
    if detect_scene == "":
        detect_scene = "2" if option2_highlight else "1"
    elif detect_scene[0] == "0":
        return True
    elif detect_scene[0] in set(map(str, range(1, 8))):
        detect_scene = detect_scene[0]
    else:
        detect_scene = "7"
    if detect_scene == "1":
        await detect_gameflow(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df, infos = infos)
    elif detect_scene == "2":
        await detect_postgame(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df, language_code, infos = infos)
    elif detect_scene == "3":
        await detect_dodged_champSelect(connection)
    elif detect_scene == "4":
        await detect_friend(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df)
    elif detect_scene == "5":
        await detect_friend_request(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df)
    elif detect_scene == "6":
        await detect_party_invitaion(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df, infos = infos)
    elif detect_scene == "7":
        await detect_blockList(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df)
    elif detect_scene == "8":
        await detect_custom_list(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df, infos = infos)
    logPrint("是否更新数据？（输入任意键以返回上一层更新对局记录信息，否则在不更新对局信息的情况下再次查询近期一起玩过的玩家。）\nUpdate data? (Submit any non-empty string to update match history information, otherwise check the recently played summoners again without updating match history.)")
    update_str: str = logInput()
    update = bool(update_str)
    return update

async def detect_gameflow(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame, infos: Optional[dict[str, dict[str, Any]]] = None) -> None:
    '''
    检测一场对局的各个阶段中遇到过的玩家。<br>Detect recently played summoners in each phase of a game.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    '''
    if infos == None:
        infos = {}
    current_puuid_list: list[str] = list(map(lambda x: x["puuid"], AllAccounts))
    recent_LoLPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"] if use_sgp else ["gameName", "tagLine", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"]
    recent_TFTPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameDate", "gameModeName", "last_round_format"]
    recent_LoLPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_LoLPlayer_fields}
    recent_TFTPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_TFTPlayer_fields}
    member_count: int = 0
    ally_count: int = 0
    enemy_count: int = 0
    player_count: int = 0
    recent_friend_summonerNames: list[str] = []
    LoLMember_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    TFTMember_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    LoLAlly_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    LoLEnemy_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print) #在玩家对战的英雄选择阶段，所有敌方玩家的信息都是不可见的；在人机对战的英雄选择阶段，无敌方玩家。统计敌方信息只适用于自定义对局的英雄选择阶段和任意对局的游戏内（During champ select of PVP games, all enemies' information is hidden; during champ select of PVE games, there're no enemy players. Counting enemy stats only applys in the champ select stage of custom games and the in-game stage of any game）
    LoLPlayer_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    TFTAlly_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    TFTEnemy_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    TFTPlayer_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    recent_LoLPlayer_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    recent_TFTPlayer_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    gameflow_phase: str = "None"
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
    logPrint('''请确保您在房间内、英雄选择阶段或在游戏中，以便本脚本检测是否存在曾经遇到过的队友。按回车键开始检测，或者按“0”以返回上一步。\nPlease confirm you're in lobby, during champ select or in game, so that this script can detect whether there's an ally encountered before. Press Enter to start detection, or press "0" to return to the last step.''')
    while True:
        detect: str = logInput()
        if detect != "" and detect[0] == "0":
            break
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase == "None":
            logPrint("您尚未创建任何房间！请创建房间后再按回车键开始检测。\nYou haven't created any lobby yet! Please create a lobby and then press Enter to start detection.")
            continue
        elif gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck", "ChampSelect", "InProgress", "Reconnect"}:
            # if gameflow_phase == "ChampSelect":
            #     if Vanguard_warning_printed:
            #         logPrint("您已进入英雄选择阶段！请在进入游戏后再按回车键开始检测。\nChamp select stage has started! Please press Enter to start detection after entering the game.")
            #     else:
            #         logPrint("鉴于拳头反作弊系统对于房间内队友信息访问行为的打击，本脚本已停用英雄选择阶段对曾经遇到过的队友的检测。请在进入游戏后再按回车键开始检测。\nIn view of Riot Vanguard's fight against Lobby Reveal behaviors, this program has banned the detection of recently played summoners during champ select stage. Please press Enter to start detection after entering the game.")
            #         Vanguard_warning_printed = True
            #     continue
            break
        elif gameflow_phase in {"WaitingForStats", "EndOfGame", "PreEndOfGame"}:
            logPrint("您已完成对局！请使用生成模式以查看最近一局比赛中遇到的玩家信息，或者开启下一局以查看下一局遇到的队友是否曾经遇到过。\nYou've finished the match! Please use [Generate Mode] to check the information of players encountered in the latest match, or start another game and use [Detect Mode] to check whether an ally has been met before.")
            continue
    if detect != "" and detect[0] == "0":
        return
    if gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck"}:
        lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        logPrint(lobby_information)
        gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        gameModeName: str = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameflow_session["gameData"]["queue"]["id"]) if gameflow_session["gameData"]["queue"]["name"] == "" else gameflow_session["gameData"]["queue"]["name"]
        wb03Name: str = "Recently Played Summoners in Lobby %s-%s (%s).xlsx" %(platformId, lobby_information["partyId"], gameModeName)
        for member in lobby_information["members"]:
            if not member["puuid"] in current_puuid_list: #在大多数情况下，这里不需要改成自己的玩家通用唯一识别码列表。有两个原因：一是一个会话仅属于一名英雄联盟玩家；二是前面整理玩家信息时，小号已经被排除，所以这里不可能会有成员为小号。但是如果用户通过命令行参数指定小号不被删除，那么仍然需要使用列表（In most cases, here the `current_puuid` doesn't need to be replaced by the self puuid list. Two reasons: first, a session only belongs to a single League of Legends player; second, while sorting out the player information before, smurf accounts have been excluded, so it's impossible for any member to correspond to a smurf. But if the user specifies the command line argument so that smurf accounts aren't deleted, then the list is needed）
                member_info_recapture: int = 0
                if member["puuid"] in infos:
                    member_info_body: dict[str, str] = infos[member["puuid"]]
                else:
                    member_info: dict[str, str] = await get_info(connection, member["puuid"])
                    while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                        logPrint(member_info["message"])
                        member_info_recapture += 1
                        logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of a member (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(member["puuid"], member_info_recapture, member["puuid"], member_info_recapture))
                        member_info = await get_info(connection, member["puuid"])
                    if member_info["info_got"]:
                        member_info_body = member_info["body"]
                        infos[member["puuid"]] = member_info_body
                    else:
                        logPrint(member_info["message"])
                        logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！将忽略该名成员。\nInformation of a member (puuid: %s) capture failed! The program will ignore this member.")
                        continue
                LoLMember_index: list[int] = [0]
                TFTMember_index: list[int] = [0]
                if search_LoL:
                    for i in range(len(recent_LoLPlayer_df["puuid"])):
                        if recent_LoLPlayer_df["puuid"][i] == member["puuid"]:
                            LoLMember_index.append(i)
                if search_TFT:
                    for i in range(len(recent_TFTPlayer_df["puuid"])):
                        if recent_TFTPlayer_df["puuid"][i] == member["puuid"]:
                            TFTMember_index.append(i)
                if len(LoLMember_index) + len(TFTMember_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTMember_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTMember_index is defined and its length is at least 1）
                    member_count += 1
                    LoLMember_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLMember_index, :]
                    LoLMember_df_to_print = pandas.concat([LoLMember_df_to_print, LoLMember_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                    TFTMember_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTMember_index, :]
                    TFTMember_df_to_print = pandas.concat([TFTMember_df_to_print, TFTMember_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                    if member["puuid"] in friend_puuids:
                        recent_friend_summonerNames.append(get_info_name(member_info_body))
                    if not os.path.exists(wb03Name):
                        wb03CreateFlag: bool = create_workbook_win32(os.path.abspath(wb03Name))
                    while True:
                        try:
                            with (pandas.ExcelWriter(path = wb03Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb03Name) else pandas.ExcelWriter(path = wb03Name)) as writer:
                                if search_LoL and len(LoLMember_index) > 1:
                                    addDefaultStyle(LoLMember_df).to_excel(excel_writer = writer, sheet_name = get_info_name(member_info_body) + " (LoL)")
                                if search_TFT and len(TFTMember_index) > 1:
                                    addDefaultStyle(TFTMember_df).to_excel(excel_writer = writer, sheet_name = get_info_name(member_info_body) + " (TFT)")
                                logPrint("成员%s曾经与您一同战斗过%d次。\nMember %s has fought with you for %d time(s)." %(get_info_name(member_info_body), len(LoLMember_index) + len(TFTMember_index) - 2, get_info_name(member_info_body), len(LoLMember_index) + len(TFTMember_index) - 2))
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                            logInput()
                        else:
                            break
        if len(lobby_information["members"]) == 1:
            if gameflow_phase == "Lobby":
                logPrint('''房间内无其它玩家。请单击寻找对局或开始游戏按钮，在进入英雄选择阶段后再按回车键开始检测。\nThere's not any other player in the lobby. Please click the "FIND MATCH" or "START GAME" button and press Enter to start detection after entering champ select stage.''')
            elif gameflow_phase == "Matchmaking":
                logPrint("房间内无其它玩家。请在接受对局进入英雄选择阶段后再按回车键开始检测。\nThere's not any other player in the lobby. Please press Enter to start detection after accepting a match and entering champ select stage.")
            elif gameflow_phase == "ReadyCheck":
                logPrint("房间内无其它玩家。请接受对局，并在进入英雄选择阶段后按回车键开始检测。\nThere's not any other player in the lobby. Please accept this match and press Enter to start detection after entering champ select stage.")
        elif member_count == 0:
            if gameflow_phase == "Lobby":
                logPrint('''您目前遇到的都是新的成员。请单击寻找对局或开始游戏按钮，在进入英雄选择阶段后再按回车键开始检测。\nThe members you've met now are all new. Please click the "FIND MATCH" or "START GAME" button and press Enter to start detection after entering champ select stage.''')
            elif gameflow_phase == "Matchmaking":
                logPrint("您目前遇到的都是新的成员。请在接受对局进入英雄选择阶段后再按回车键开始检测。\nThe members you've met now are all new. Please press Enter to start detection after accepting a match and entering champ select stage.")
            elif gameflow_phase == "ReadyCheck":
                logPrint("您目前遇到的都是新的成员。请接受对局，并在进入英雄选择阶段后按回车键开始检测。\nThe members you've met now are all new. Please accept this match and press Enter to start detection after entering champ select stage.")
        else:
            logPrint()
            if search_LoL:
                print(format_df(LoLMember_df_to_print, print_index = True, reserve_index = True)[0])
                log.write(format_df(LoLMember_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            if search_LoL and search_TFT:
                logPrint()
            if search_TFT:
                print(format_df(TFTMember_df_to_print, print_index = True, reserve_index = True)[0])
                log.write(format_df(TFTMember_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            if member_count == 1:
                logPrint('''一名成员曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a member present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb03Name, wb03Name))
            else:
                logPrint('''%d名成员曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d members present in your past matches. Please check the workbook "%s" in the main directory.''' %(member_count, wb03Name, member_count, wb03Name))
        if len(recent_friend_summonerNames) == 1:
            logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friend_summonerNames[0], recent_friend_summonerNames[0]))
        elif len(recent_friend_summonerNames) > 1:
            logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friend_summonerNames), ", ".join(recent_friend_summonerNames)))
    elif gameflow_phase == "ChampSelect":
        champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        logPrint(champ_select_session)
        if "errorCode" in champ_select_session:
            if champ_select_session["message"] == "No active delegate": #在没有英雄选择阶段的游戏模式中，有时gameflow_phase的结果是“ChampSelect”，但是实际上没有可用的英雄选择会话（In game modes without champ select stage, sometimes `gameflow_phase` is "ChampSelect", but there's actually no available champ select session）
                logPrint("英雄选择会话已过期。\nChamp select session has expired.")
            return
        gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        gameModeName = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameflow_session["gameData"]["queue"]["id"]) if gameflow_session["gameData"]["queue"]["name"] == "" else gameflow_session["gameData"]["queue"]["name"]
        wb04Name: str = "Recently Played Summoners in Match %s-%s (%s).xlsx" %(platformId, champ_select_session["gameId"], gameModeName)
        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        skip_lobby_member: bool = False
        lobby_member_puuids: list[str] = []
        if not "errorCode" in lobby_information and len(lobby_information["members"]) > 1:
            logPrint("检测时是否忽略小队成员？（输入任意键忽略，否则不忽略。）\nNeglect lobby members when detecting? (Submit any non-empty string to neglect, or null to refust neglecting.)")
            skip_lobby_member_str: str = logInput()
            skip_lobby_member = bool(skip_lobby_member_str)
            lobby_member_puuids = list(map(lambda x: x["puuid"], lobby_information["members"]))
        for ally in champ_select_session["myTeam"]:
            if not ally["puuid"] in set(current_puuid_list) | {"", BOT_UUID} and (ally["nameVisibilityType"] == "VISIBLE" or ally["nameVisibilityType"] == ""):
                ally_info_recapture: int = 0
                if ally["puuid"] in infos:
                    ally_info_body: dict[str, Any] = infos[ally["puuid"]]
                else:
                    ally_info: dict[str, Any] = await get_info(connection, ally["puuid"])
                    while not ally_info["info_got"] and ally_info["body"]["httpStatus"] != 404 and ally_info_recapture < 3:
                        logPrint(ally_info["message"])
                        ally_info_recapture += 1
                        logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an ally (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                        ally_info = await get_info(connection, ally["puuid"])
                    if ally_info["info_got"]:
                        ally_info_body = ally_info["body"]
                        infos[ally["puuid"]] = ally_info_body
                    else:
                        logPrint(ally_info["message"])
                        logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an ally (puuid: %s) capture failed! The program will ignore this ally.")
                        continue
                LoLAlly_index: list[int] = [0] #第0行是中文表头，所以一开始要包含在内（The 0th line is Chinese header, so it should be contained in the beginning）
                TFTAlly_index: list[int] = [0]
                if search_LoL:
                    for i in range(len(recent_LoLPlayer_df["puuid"])):
                        if recent_LoLPlayer_df["puuid"][i] == ally["puuid"] and not (skip_lobby_member and recent_LoLPlayer_df["puuid"][i] in lobby_member_puuids):
                            LoLAlly_index.append(i)
                if search_TFT:
                    for i in range(len(recent_TFTPlayer_df["puuid"])):
                        if recent_TFTPlayer_df["puuid"][i] == ally["puuid"] and not (skip_lobby_member and recent_TFTPlayer_df["puuid"][i] in lobby_member_puuids):
                            TFTAlly_index.append(i)
                if len(LoLAlly_index) + len(TFTAlly_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTAlly_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTAlly_index is defined and its length is at least 1）
                    ally_count += 1
                    LoLAlly_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLAlly_index, :]
                    LoLAlly_df_to_print = pandas.concat([LoLAlly_df_to_print, LoLAlly_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                    TFTAlly_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTAlly_index, :]
                    TFTAlly_df_to_print = pandas.concat([TFTAlly_df_to_print, TFTAlly_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                    if ally["puuid"] in friend_puuids:
                        recent_friend_summonerNames.append(get_info_name(ally_info_body))
                    if not os.path.exists(wb04Name):
                        wb04CreateFlag: bool = create_workbook_win32(os.path.abspath(wb04Name))
                    while True:
                        try:
                            with (pandas.ExcelWriter(path = wb04Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb04Name) else pandas.ExcelWriter(path = wb04Name)) as writer:
                                if search_LoL and len(LoLAlly_index) > 1:
                                    addDefaultStyle(LoLAlly_df).to_excel(excel_writer = writer, sheet_name = get_info_name(ally_info_body) + " (LoL)")
                                if search_TFT and len(TFTAlly_index) > 1:
                                    addDefaultStyle(TFTAlly_df).to_excel(excel_writer = writer, sheet_name = get_info_name(ally_info_body) + " (TFT)")
                                logPrint("队友%s曾经与您一同战斗过%d次。\nAlly %s has fought with you for %d time(s)." %(get_info_name(ally_info_body), len(LoLAlly_index) + len(TFTAlly_index) - 2, get_info_name(ally_info_body), len(LoLAlly_index) + len(TFTAlly_index) - 2))
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                            logInput()
                        else:
                            break
        if champ_select_session["theirTeam"]: #在人机对战、云顶之弈和斗魂竞技场中，无敌方玩家（There're no enemy players in bot games, TFT and Arena）
            for enemy in champ_select_session["theirTeam"]:
                if not enemy["puuid"] in set(current_puuid_list) | {"", BOT_UUID} and (enemy["nameVisibilityType"] == "VISIBLE" or enemy["nameVisibilityType"] == ""):
                    enemy_info_recapture: int = 0
                    if enemy["puuid"] in infos:
                        enemy_info_body: dict[str, Any] = infos[enemy["puuid"]]
                    else:
                        enemy_info: dict[str, Any] = await get_info(connection, enemy["puuid"])
                        while not enemy_info["info_got"] and enemy_info["body"]["httpStatus"] != 404 and enemy_info_recapture < 3:
                            logPrint(enemy_info["message"])
                            enemy_info_recapture += 1
                            logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an enemy (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(enemy["puuid"], enemy_info_recapture, enemy["puuid"], enemy_info_recapture))
                            enemy_info = await get_info(connection, enemy["puuid"])
                        if enemy_info["info_got"]:
                            enemy_info_body = enemy_info["body"]
                            infos[enemy["puuid"]] = enemy_info_body
                        else:
                            logPrint(enemy_info["message"])
                            logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！将忽略该名对手。\nInformation of an enemy (puuid: %s) capture failed! The program will ignore this enemy.")
                            continue
                    LoLEnemy_index: list[int] = [0]
                    TFTEnemy_index: list[int] = [0]
                    if search_LoL:
                        for i in range(len(recent_LoLPlayer_df["puuid"])):
                            if recent_LoLPlayer_df["puuid"][i] == enemy["puuid"] and not (skip_lobby_member and recent_LoLPlayer_df["puuid"][i] in lobby_member_puuids):
                                LoLEnemy_index.append(i)
                    if search_TFT:
                        for i in range(len(recent_TFTPlayer_df["puuid"])):
                            if recent_TFTPlayer_df["puuid"][i] == enemy["puuid"] and not (skip_lobby_member and recent_TFTPlayer_df["puuid"][i] in lobby_member_puuids):
                                TFTEnemy_index.append(i)
                    if len(LoLEnemy_index) + len(TFTEnemy_index) > 2:
                        enemy_count += 1
                        LoLEnemy_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLEnemy_index, :]
                        LoLEnemy_df_to_print = pandas.concat([LoLEnemy_df_to_print, LoLEnemy_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                        TFTEnemy_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTEnemy_index, :]
                        TFTEnemy_df_to_print = pandas.concat([TFTEnemy_df_to_print, TFTEnemy_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                        if enemy["puuid"] in friend_puuids:
                            recent_friend_summonerNames.append(get_info_name(enemy_info_body))
                        if not os.path.exists(wb04Name):
                            wb04CreateFlag: bool = create_workbook_win32(os.path.abspath(wb04Name))
                        while True:
                            try:
                                with (pandas.ExcelWriter(path = wb04Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb04Name) else pandas.ExcelWriter(path = wb04Name)) as writer:
                                    if search_LoL and len(LoLEnemy_index) > 1:
                                        addDefaultStyle(LoLEnemy_df).to_excel(excel_writer = writer, sheet_name = get_info_name(enemy_info_body) + " (LoL)")
                                    if search_TFT and len(TFTEnemy_index) > 1:
                                        addDefaultStyle(TFTEnemy_df).to_excel(excel_writer = writer, sheet_name = get_info_name(enemy_info_body) + " (TFT)")
                                    logPrint("对手%s曾经与您一同战斗过%d次。\nEnemy %s has fought with you for %d time(s)." %(get_info_name(enemy_info_body), len(LoLEnemy_index) + len(TFTEnemy_index) - 2, get_info_name(enemy_info_body), len(LoLEnemy_index) + len(TFTEnemy_index) - 2))
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            else:
                                break
        if ally_count == 0:
            logPrint("您目前遇到的都是新的队友。尝试拓展人缘吧！\nThe allies you've met now are all new. Try extending your friendship!")
        else:
            logPrint()
            if search_LoL:
                print(format_df(LoLAlly_df_to_print, print_index = True, reserve_index = True)[0])
                log.write(format_df(LoLAlly_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            if search_LoL and search_TFT:
                logPrint()
            if search_TFT:
                print(format_df(TFTAlly_df_to_print, print_index = True, reserve_index = True)[0])
                log.write(format_df(TFTAlly_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            if ally_count == 1:
                logPrint('''一名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an ally present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb04Name, wb04Name))
            else:
                logPrint('''%d名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d allies present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, wb04Name, ally_count, wb04Name))
        if any(map(lambda x: x["nameVisibilityType"] == "VISIBLE" or x["nameVisibilityType"] == "", champ_select_session["theirTeam"])):
            if enemy_count > 0:
                logPrint()
                if search_LoL:
                    print(format_df(LoLEnemy_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(LoLEnemy_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if search_LoL and search_TFT:
                    logPrint()
                if search_TFT:
                    print(format_df(TFTEnemy_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(TFTEnemy_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if enemy_count == 1:
                    logPrint('''一名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an enemy present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb04Name, wb04Name))
                else:
                    logPrint('''%d名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d enemies present in your past matches. Please check the workbook "%s" in the main directory.''' %(enemy_count, wb04Name, enemy_count, wb04Name))
        if len(recent_friend_summonerNames) == 1:
            logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friend_summonerNames[0], recent_friend_summonerNames[0]))
        elif len(recent_friend_summonerNames) > 1:
            logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friend_summonerNames), ", ".join(recent_friend_summonerNames)))
        if not (all(map(lambda x: x["nameVisibilityType"] == "VISIBLE", champ_select_session["theirTeam"])) or all(map(lambda x: x["nameVisibilityType"] == "HIDDEN", champ_select_session["theirTeam"])) or all(map(lambda x: x["nameVisibilityType"] == "", champ_select_session["theirTeam"])) or all(map(lambda x: x["nameVisibilityType"] == "", champ_select_session["theirTeam"]))):
            logPrint("检测到敌方信息可见性异常！请检查之前输出的英雄选择阶段信息。\nDetected enemies' visibility abnormal! Please check the champ select session information printed before.")
        if not champ_select_session["isSpectating"]:
            champ_select_session_cache[champ_select_session["gameId"]] = champ_select_session
    elif gameflow_phase == "InProgress" or gameflow_phase == "Reconnect":
        gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        logPrint(gameflow_session)
        gameData: dict[str, Any] = gameflow_session["gameData"]
        gameModeName = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameData["queue"]["id"]) if gameData["queue"]["name"] == "" else gameData["queue"]["name"]
        wb05Name: str = "Recently Played Summoners in Match %s-%s (%s).xlsx" %(platformId, gameData["gameId"], gameModeName)
        if gameData["queue"]["mapId"] == "22" or gameData["queue"]["mapId"] == "30": #玩家在API上的阵营划分随对局模式而不同。云顶之弈和斗魂竞技场虽然有多个阵营，但是都是记录在gameData["teamOne"]中，这需要和其它模式区分开来。该条件语句与“if gameData["queue"]["gameMode"] == "TFT" or gameData["queue"]["gameMode"] == "CHERRY"”等价，但是因为召唤师峡谷还能分成CLASSIC、URF等模式，所以这里直接用地图序号作为判断依据（The team where a player belongs varies by the game mode. Although there're actually more than 2 teams in TFT and Arena, all players are recorded in `gameData["teamOne"]`, which needs ditinguishing from other game modes. This conditional statement is equivalent to `if gameData["queue"]["gameMode"] == "TFT" or gameData["queue"]["gameMode"] == "CHERRY"`, but since there're multiple modes based on one map, like CLASSIC and URF based on Summoner's Rift, the mapId is thus taken as the judgment criterium）
            for player in gameData["teamOne"]:
                if "puuid" in player and not player["puuid"] in current_puuid_list: #电脑玩家没有玩家通用唯一识别码（Bot players don't have puuids）
                    player_info_recapture: int = 0
                    if player["puuid"] in infos:
                        player_info_body: dict[str, Any] = infos[player["puuid"]]
                    else:
                        player_info: dict[str, Any] = await get_info(connection, player["puuid"])
                        while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                            logPrint(player_info["message"])
                            player_info_recapture += 1
                            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture))
                            player_info = await get_info(connection, player["puuid"])
                        if player_info["info_got"]:
                            player_info_body = player_info["body"]
                            infos[player_info_body["puuid"]] = player_info_body
                        else:
                            logPrint(player_info["message"])
                            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an player (puuid: %s) capture failed! The program will ignore this player.")
                            continue
                    LoLPlayer_index: list[int] = [0] #第0行是中文表头，所以一开始要包含在内（The 0th line is Chinese header, so it should be contained in the beginning）
                    TFTPlayer_index: list[int] = [0]
                    if search_LoL:
                        for i in range(len(recent_LoLPlayer_df["puuid"])):
                            if recent_LoLPlayer_df["puuid"][i] == player["puuid"]:
                                LoLPlayer_index.append(i)
                    if search_TFT:
                        for i in range(len(recent_TFTPlayer_df["puuid"])):
                            if recent_TFTPlayer_df["puuid"][i] == player["puuid"]:
                                TFTPlayer_index.append(i)
                    if len(LoLPlayer_index) + len(TFTPlayer_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTPlayer_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTPlayer_index is defined and its length is at least 1）
                        player_count += 1
                        LoLPlayer_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLPlayer_index, :]
                        LoLPlayer_df_to_print = pandas.concat([LoLPlayer_df_to_print, LoLPlayer_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                        TFTPlayer_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTPlayer_index, :]
                        TFTPlayer_df_to_print = pandas.concat([TFTPlayer_df_to_print, TFTPlayer_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                        if player["puuid"] in friend_puuids:
                            recent_friend_summonerNames.append(get_info_name(player_info_body))
                        if not os.path.exists(wb05Name):
                            wb05CreateFlag: bool = create_workbook_win32(os.path.abspath(wb05Name))
                        while True:
                            try:
                                with (pandas.ExcelWriter(path = wb05Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb05Name) else pandas.ExcelWriter(path = wb05Name)) as writer:
                                    if search_LoL and len(LoLPlayer_index) > 1:
                                        addDefaultStyle(LoLPlayer_df).to_excel(excel_writer = writer, sheet_name = get_info_name(player_info_body) + " (LoL)")
                                    if search_TFT and len(TFTPlayer_index) > 1:
                                        addDefaultStyle(TFTPlayer_df).to_excel(excel_writer = writer, sheet_name = get_info_name(player_info_body) + " (TFT)")
                                    logPrint("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d time(s)." %(get_info_name(player_info_body), len(LoLPlayer_index) + len(TFTPlayer_index) - 2, get_info_name(player_info_body), len(LoLPlayer_index) + len(TFTPlayer_index) - 2))
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            else:
                                break
            if player_count == 0:
                logPrint("您目前遇到的都是新的玩家。尝试拓展人缘吧！\nThe players you've met now are all new. Try extending your friendship!")
            else:
                logPrint()
                if search_LoL:
                    print(format_df(LoLPlayer_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(LoLPlayer_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if search_LoL and search_TFT:
                    logPrint()
                if search_TFT:
                    print(format_df(TFTPlayer_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(TFTPlayer_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if player_count == 1:
                    logPrint('''一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a player present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb05Name, wb05Name))
                else:
                    logPrint('''%d名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d players present in your past matches. Please check the workbook "%s" in the main directory.''' %(player_count, wb05Name, player_count, wb05Name))
            if len(recent_friend_summonerNames) == 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friend_summonerNames[0], recent_friend_summonerNames[0]))
            elif len(recent_friend_summonerNames) > 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friend_summonerNames), ", ".join(recent_friend_summonerNames)))
        else:
            isSpectating: bool = False #设置观战逻辑变量，确定游戏会话是不是观战的（This boolean variable is declared to tell whether the game session is spectating）
            teamOne_puuids: list[str] = []
            for player in gameData["teamOne"]:
                if "puuid" in player:
                    teamOne_puuids.append(player["puuid"])
            teamTwo_puuids: list[str] = []
            for player in gameData["teamTwo"]:
                if "puuid" in player:
                    teamTwo_puuids.append(player["puuid"])
            if len(set(current_puuid_list) & set(teamOne_puuids)) > 0: #API记录游戏中的玩家时，只会区分红蓝方，不会区分敌我。所以这里需要先判断那个阵营是我方（Players recorded in API only differentiate by blue or red team, instead of my or enemy team. So judging the own team or the enemy team is the first thing to do）
                myTeam: list[dict[str, Any]] = gameData["teamOne"]
                theirTeam: list[dict[str, Any]] = gameData["teamTwo"]
            elif len(set(current_puuid_list) & set(teamTwo_puuids)) > 0:
                myTeam = gameData["teamTwo"]
                theirTeam = gameData["teamOne"]
            else:
                myTeam = gameData["teamOne"] + gameData["teamTwo"]
                theirTeam = []
                isSpectating = True
            for ally in myTeam:
                if "puuid" in ally and not ally["puuid"] in current_puuid_list:
                    ally_info_recapture = 0
                    if ally["puuid"] in infos:
                        ally_info_body = infos[ally["puuid"]]
                    else:
                        ally_info = await get_info(connection, ally["puuid"])
                        while not ally_info["info_got"] and ally_info["body"]["httpStatus"] != 404 and ally_info_recapture < 3:
                            logPrint(ally_info["message"])
                            ally_info_recapture += 1
                            if isSpectating:
                                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of a player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                            else:
                                logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an ally (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                            ally_info = await get_info(connection, ally["puuid"])
                        if ally_info["info_got"]:
                            ally_info_body = ally_info["body"]
                            infos[ally_info_body["puuid"]] = ally_info_body
                        else:
                            logPrint(ally_info["message"])
                            if isSpectating:
                                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名玩家。\nInformation of a player (puuid: %s) capture failed! The program will ignore this player.")
                            else:
                                logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an ally (puuid: %s) capture failed! The program will ignore this ally.")
                            continue
                    LoLAlly_index = [0] #第0行是中文表头，所以一开始要包含在内（The 0th line is Chinese header, so it should be contained in the beginning）
                    TFTAlly_index = [0]
                    if search_LoL:
                        for i in range(len(recent_LoLPlayer_df["puuid"])):
                            if recent_LoLPlayer_df["puuid"][i] == ally["puuid"]:
                                LoLAlly_index.append(i)
                    if search_TFT:
                        for i in range(len(recent_TFTPlayer_df["puuid"])):
                            if recent_TFTPlayer_df["puuid"][i] == ally["puuid"]:
                                TFTAlly_index.append(i)
                    if len(LoLAlly_index) + len(TFTAlly_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTAlly_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTAlly_index is defined and its length is at least 1）
                        ally_count += 1
                        LoLAlly_df = recent_LoLPlayer_df.loc[LoLAlly_index, :]
                        LoLAlly_df_to_print = pandas.concat([LoLAlly_df_to_print, LoLAlly_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                        TFTAlly_df = recent_TFTPlayer_df.loc[TFTAlly_index, :]
                        TFTAlly_df_to_print = pandas.concat([TFTAlly_df_to_print, TFTAlly_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                        if ally["puuid"] in friend_puuids:
                            recent_friend_summonerNames.append(get_info_name(ally_info_body))
                        if not os.path.exists(wb05Name):
                            wb05CreateFlag = create_workbook_win32(os.path.abspath(wb05Name))
                        while True:
                            try:
                                with (pandas.ExcelWriter(path = wb05Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb05Name) else pandas.ExcelWriter(path = wb05Name)) as writer:
                                    if search_LoL and len(LoLAlly_index) > 1:
                                        addDefaultStyle(LoLAlly_df).to_excel(excel_writer = writer, sheet_name = get_info_name(ally_info_body) + " (LoL)")
                                    if search_TFT and len(TFTAlly_index) > 1:
                                        addDefaultStyle(TFTAlly_df).to_excel(excel_writer = writer, sheet_name = get_info_name(ally_info_body) + " (TFT)")
                                    if isSpectating:
                                        logPrint("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d time(s)." %(get_info_name(ally_info_body), len(LoLAlly_index) + len(TFTAlly_index) - 2, get_info_name(ally_info_body), len(LoLAlly_index) + len(TFTAlly_index) - 2))
                                    else:
                                        logPrint("队友%s曾经与您一同战斗过%d次。\nAlly %s has fought with you for %d time(s)." %(get_info_name(ally_info_body), len(LoLAlly_index) + len(TFTAlly_index) - 2, get_info_name(ally_info_body), len(LoLAlly_index) + len(TFTAlly_index) - 2))
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            else:
                                break
            for enemy in theirTeam:
                if "puuid" in enemy:
                    if enemy["puuid"] in infos:
                        enemy_info_body = infos[enemy["puuid"]]
                    else:
                        enemy_info_recapture = 0
                        enemy_info = await get_info(connection, enemy["puuid"])
                        while not enemy_info["info_got"] and enemy_info["body"]["httpStatus"] != 404 and enemy_info_recapture < 3:
                            logPrint(enemy_info["message"])
                            enemy_info_recapture += 1
                            logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an enemy (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(enemy["puuid"], enemy_info_recapture, enemy["puuid"], enemy_info_recapture))
                            enemy_info = await get_info(connection, enemy["puuid"])
                        if enemy_info["info_got"]:
                            enemy_info_body = enemy_info["body"]
                            infos[enemy["puuid"]] = enemy_info_body
                        else:
                            logPrint(enemy_info["message"])
                            logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！将忽略该名对手。\nInformation of an enemy (puuid: %s) capture failed! The program will ignore this enemy.")
                            continue
                    LoLEnemy_index = [0]
                    TFTEnemy_index = [0]
                    if search_LoL:
                        for i in range(len(recent_LoLPlayer_df["puuid"])):
                            if recent_LoLPlayer_df["puuid"][i] == enemy["puuid"]:
                                LoLEnemy_index.append(i)
                    if search_TFT:
                        for i in range(len(recent_TFTPlayer_df["puuid"])):
                            if recent_TFTPlayer_df["puuid"][i] == enemy["puuid"]:
                                TFTEnemy_index.append(i)
                    if len(LoLEnemy_index) + len(TFTEnemy_index) > 2:
                        enemy_count += 1
                        LoLEnemy_df = recent_LoLPlayer_df.loc[LoLEnemy_index, :]
                        LoLEnemy_df_to_print = pandas.concat([LoLEnemy_df_to_print, LoLEnemy_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                        TFTEnemy_df = recent_TFTPlayer_df.loc[TFTEnemy_index, :]
                        TFTEnemy_df_to_print = pandas.concat([TFTEnemy_df_to_print, TFTEnemy_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                        if enemy["puuid"] in friend_puuids:
                            recent_friend_summonerNames.append((get_info_name(enemy_info_body)))
                        if not os.path.exists(wb05Name):
                            wb05CreateFlag = create_workbook_win32(os.path.abspath(wb05Name))
                        while True:
                            try:
                                with (pandas.ExcelWriter(path = wb05Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb05Name) else pandas.ExcelWriter(path = wb05Name)) as writer:
                                    if search_LoL and len(LoLEnemy_index) > 1:
                                        addDefaultStyle(LoLEnemy_df).to_excel(excel_writer = writer, sheet_name = get_info_name(enemy_info_body) + " (LoL)")
                                    if search_TFT and len(TFTEnemy_index) > 1:
                                        addDefaultStyle(TFTEnemy_df).to_excel(excel_writer = writer, sheet_name = get_info_name(enemy_info_body) + " (TFT)")
                                    logPrint("对手%s曾经与您一同战斗过%d次。\nEnemy %s has fought with you for %d time(s)." %(get_info_name(enemy_info_body), len(LoLEnemy_index) + len(TFTEnemy_index) - 2, get_info_name(enemy_info_body), len(LoLEnemy_index) + len(TFTEnemy_index) - 2))
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            else:
                                break
            if isSpectating:
                if ally_count == 0:
                    logPrint("您目前遇到的都是新的玩家。尝试拓展人缘吧！\nThe players you've met now are all new. Try extending your friendship!")
                else:
                    logPrint()
                    if search_LoL:
                        print(format_df(LoLAlly_df_to_print, print_index = True, reserve_index = True)[0])
                        log.write(format_df(LoLAlly_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                    if search_LoL and search_TFT:
                        logPrint()
                    if search_TFT:
                        print(format_df(TFTAlly_df_to_print, print_index = True, reserve_index = True)[0])
                        log.write(format_df(TFTAlly_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                    if ally_count == 1:
                        logPrint('''一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a player present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb05Name, wb05Name))
                    else:
                        logPrint('''%d名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d players present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, wb05Name, ally_count, wb05Name))
            else:
                if ally_count == 0:
                    logPrint("您目前遇到的都是新的玩家。尝试拓展人缘吧！\nThe players you've met now are all new. Try extending your friendship!")
                else:
                    logPrint()
                    if search_LoL:
                        print(format_df(LoLAlly_df_to_print, print_index = True, reserve_index = True)[0])
                        log.write(format_df(LoLAlly_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                    if search_LoL and search_TFT:
                        logPrint()
                    if search_TFT:
                        print(format_df(TFTAlly_df_to_print, print_index = True, reserve_index = True)[0])
                        log.write(format_df(TFTAlly_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                    if ally_count == 1:
                        logPrint('''一名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an ally present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb05Name, wb05Name))
                    else:
                        logPrint('''%d名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d allies present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, wb05Name, ally_count, wb05Name))
                if enemy_count > 0:
                    logPrint()
                    if search_LoL:
                        print(format_df(LoLEnemy_df_to_print, print_index = True, reserve_index = True)[0])
                        log.write(format_df(LoLEnemy_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                    if search_LoL and search_TFT:
                        logPrint()
                    if search_TFT:
                        print(format_df(TFTEnemy_df_to_print, print_index = True, reserve_index = True)[0])
                        log.write(format_df(TFTEnemy_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                    if enemy_count == 1:
                        logPrint('''一名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an enemy present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb05Name, wb05Name))
                    else:
                        logPrint('''%d名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d enemies present in your past matches. Please check the workbook "%s" in the main directory.''' %(enemy_count, wb05Name, enemy_count, wb05Name))
            if len(recent_friend_summonerNames) == 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friend_summonerNames[0], recent_friend_summonerNames[0]))
            elif len(recent_friend_summonerNames) > 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friend_summonerNames), ", ".join(recent_friend_summonerNames)))
        champ_select_session_cache.clear() #在进入游戏后，清理所有缓存的英雄选择会话（After the user enters a game, clear all champ select session cache）

async def detect_postgame(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame, language_code: str, infos: Optional[dict[str, dict[str, Any]]] = None) -> None:
    '''
    检测某场过往对局中曾经一起玩过的玩家。<br>Detect recently played summoners in a previous match.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    :param language_code: 语言文化代码。用于确定数据资源链接。<br>Language code. Used to determine links to data resources.
    :type language_code: str
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    '''
    #初始化数据资源（Initialize data resources）
    patches: list[str] = patches_initial.copy()
    queues: dict[int, dict[str, Any]] = queues_initial.copy()
    spells: dict[int, dict[str, Any]] = spells_initial.copy()
    LoLChampions: dict[int, dict[str, Any]] = LoLChampions_initial.copy()
    LoLItems: dict[int, dict[str, Any]] = LoLItems_initial.copy()
    summonerIcons: dict[int, dict[str, Any]] = summonerIcons_initial.copy()
    perks: dict[int, dict[str, Any]] = perks_initial.copy()
    perkstyles: dict[int, dict[str, Any]] = perkstyles_initial.copy()
    TFTAugments: dict[str, dict[str, Any]] = TFTAugments_initial.copy()
    TFTChampions: dict[str, dict[str, Any]] = TFTChampions_initial.copy()
    TFTItems: dict[str, dict[str, Any]] = TFTItems_initial.copy()
    TFTCompanions: dict[str, dict[str, Any]] = TFTCompanions_initial.copy()
    TFTTraits: dict[str, dict[str, Any]] = TFTTraits_initial.copy()
    CherryAugments: dict[int, dict[str, Any]] = CherryAugments_initial.copy()
    #初始化变量（Initialize variables）
    gameId: int = 0
    game_summary: dict[str, Any] = {}
    LoLGame_summary: dict[str, Any] = {}
    TFTGame_summary: dict[str, Any] = {}
    recent_LoLPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"] if use_sgp else ["gameName", "tagLine", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"]
    recent_TFTPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameDate", "gameModeName", "last_round_format"]
    recent_LoLPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_LoLPlayer_fields}
    recent_TFTPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_TFTPlayer_fields}
    current_puuid_list: list[str] = list(map(lambda x: x["puuid"], AllAccounts))
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
    logPrint('请输入对局序号。输入“0”以返回上一层。\nPlease enter the gameId. Submit "0" to return to the last step.')
    while True:
        #首先判断对局是英雄联盟的还是云顶之弈的（First, judge which product the gameId belongs to, LoL or TFT）
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
                    status, game_summary = await get_game_summary_sgp(connection, sgpSession, match_id, log = log)
                    if status == 200:
                        fetched_info = True
                        isTFT = game_summary["metadata"]["product"] == "TFT"
                    else:
                        logPrint("请求失败！请切换一个对局序号或稍后重试。\nRequest failed! Please change a gameId or try it again later.")
                else:
                    logPrint("请输入一个正整数！\nPlease enter a positive integer.")
        if fetched_info:
            #然后获取对局概要并生成对局概要数据框（Then, get game summary and generate game summary dataframe）
            if isTFT and bool(game_summary["json"]):
                TFTGame_summary = game_summary
                gameMode: str = "TFT"
                gameModeName = queues[TFTGame_summary["json"]["queueId"]]["name"] if TFTGame_summary["json"]["queueId"] in queues else "TFT (%d)" %(TFTGame_summary["json"]["queueId"])
                players_metaDf: pandas.DataFrame = (await sort_TFTGame_summary(connection, TFTGame_summary, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = 1, current_puuid = current_puuid_list, useAllVersions = True, versionList = bigPatches, locale = language_code, session = session, useInfoDict = True, infos = infos, sortStats = False, log = log))[0]
            elif not isTFT:
                LoLGame_summary = game_summary
                if use_sgp and bool(LoLGame_summary["json"]):
                    gameMode = LoLGame_summary["json"]["gameMode"]
                    gameModeName = queues[LoLGame_summary["json"]["queueId"]]["name"] if LoLGame_summary["json"]["queueId"] in queues else gameMode + " (%d)" %(LoLGame_summary["json"]["queueId"])
                    players_metaDf = sort_LoLGame_summary_sgp(LoLGame_summary, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = 1, current_puuid = current_puuid_list, useAllVersions = True, versionList = bigPatches, locale = language_code, session = session, sortStats = False, log = log)[0]
                else:
                    status, LoLGame_summary = await get_LoLGame_summary(connection, gameId, log = log)
                    gameMode = LoLGame_summary["gameMode"]
                    gameModeName = queues[LoLGame_summary["queueId"]]["name"] if LoLGame_summary["queueId"] in queues else gameMode + " (%d)" %(LoLGame_summary["queueId"])
                    players_metaDf = sort_LoLGame_summary(LoLGame_summary, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = 1, current_puuid = current_puuid_list, useAllVersions = True, versionList = bigPatches, locale = language_code, session = session, sortStats = False, log = log)[0]
            else:
                logPrint("未获取到有效的玩家信息。请切换其它对局。\nNo valid participant information detected. Please change another game.")
                continue
            #最后比对玩家（Finally, compare participants）
            recent_participant_count: int = 0
            recent_LoLParticipant_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
            recent_TFTParticipant_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
            recent_friend_summonerNames: list[str] = []
            wb06Name: str = "Recently Played Summoners in Match %s-%s (%s).xlsx" %(platformId, gameId, gameModeName)
            players_metaDf_exported: bool = False
            for i in range(1, len(players_metaDf)):
                participant_puuid: str = players_metaDf["puuid"][i]
                if isTFT:
                    participant_summonerName: str = players_metaDf["riotIdGameName"][i] + "#" + players_metaDf["riotIdTagline"][i]
                elif use_sgp:
                    participant_summonerName: str = players_metaDf["puuid"][i] if players_metaDf["riotIdGameName"][i] == "" and players_metaDf["riotIdTagline"][i] == "" else players_metaDf["riotIdGameName"][i] + "#" + players_metaDf["riotIdTagline"][i]
                else:
                    participant_summonerName: str = players_metaDf["puuid"][i] if players_metaDf["gameName"][i] == "" and players_metaDf["tagLine"][i] == "" else players_metaDf["gameName"][i] + "#" + players_metaDf["tagLine"][i]
                LoLParticipant_index: list[int] = [0]
                TFTParticipant_index: list[int] = [0]
                recent_LoLGame_played: int = 0
                recent_TFTGame_played: int = 0
                if search_LoL:
                    for j in range(len(recent_LoLPlayer_df["puuid"])):
                        if recent_LoLPlayer_df["puuid"][j] == participant_puuid:
                            LoLParticipant_index.append(j) #如果导出其战绩，则保持全部记录（If this player's stats are exported, reserve all data）
                            if recent_LoLPlayer_df.at[j, "gameId"] != gameId: #排除刚才查询的对局（Exclude the queried match）
                                recent_LoLGame_played += 1
                if search_TFT:
                    for j in range(len(recent_TFTPlayer_df["puuid"])):
                        if recent_TFTPlayer_df["puuid"][j] == participant_puuid:
                            TFTParticipant_index.append(j)
                            if recent_TFTPlayer_df.at[j, "gameId"] != gameId:
                                recent_TFTGame_played += 1
                if recent_LoLGame_played + recent_TFTGame_played > 0:
                    recent_participant_count += 1
                    recent_LoLParticipant_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLParticipant_index, :]
                    recent_LoLParticipant_df_to_print = pandas.concat([recent_LoLParticipant_df_to_print, recent_LoLParticipant_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                    recent_TFTParticipant_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTParticipant_index, :]
                    recent_TFTParticipant_df_to_print = pandas.concat([recent_TFTParticipant_df_to_print, recent_TFTParticipant_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                    if participant_puuid in friend_puuids:
                        recent_friend_summonerNames.append(participant_summonerName)
                    if not os.path.exists(wb06Name):
                        wb06CreateFlag: bool = create_workbook_win32(os.path.abspath(wb06Name), sheet1_name = f"Match {gameId} - Information")
                    while True:
                        try:
                            with (pandas.ExcelWriter(path = wb06Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb06Name) else pandas.ExcelWriter(path = wb06Name)) as writer:
                                if not players_metaDf_exported:
                                    addDefaultStyle(players_metaDf.transpose()).to_excel(excel_writer = writer, sheet_name = f"Match {gameId} - Information")
                                    if not isTFT:
                                        worksheet = writer.sheets[f"Match {gameId} - Information"]
                                        worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                                        participantId_teamId_map: dict[int, list[int]] = {}
                                        participantId_subteamId_map: dict[int, list[int]] = {}
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
                                        max_numPlayersPerTeam_lol = max(map(len, participantId_subteamId_map.values())) if gameMode == "CHERRY" else max(map(len, participantId_teamId_map.values()))
                                        addFormat_LoLGame_summary_wb_transpose(worksheet, players_metaDf.transpose(), numColorScale_order = max_numPlayersPerTeam_lol)
                                    players_metaDf_exported = True
                                if search_LoL and recent_LoLGame_played > 0:
                                    addDefaultStyle(recent_LoLParticipant_df).to_excel(excel_writer = writer, sheet_name = participant_summonerName + " (LoL)")
                                if search_TFT and recent_TFTGame_played > 0:
                                    addDefaultStyle(recent_TFTParticipant_df).to_excel(excel_writer = writer, sheet_name = participant_summonerName + " (TFT)")
                                logPrint("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d time(s)." %(participant_summonerName, recent_LoLGame_played + recent_TFTGame_played, participant_summonerName, recent_LoLGame_played + recent_TFTGame_played))
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                            logInput()
                        else:
                            break
            if recent_participant_count == 0:
                logPrint("未从该对局中检测到近期一起玩过的玩家。\nNo players detected in this match.")
            else:
                logPrint()
                if search_LoL:
                    print(format_df(recent_LoLParticipant_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(recent_LoLParticipant_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if search_LoL and search_TFT:
                    logPrint()
                if search_TFT:
                    print(format_df(recent_TFTParticipant_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(recent_TFTParticipant_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if recent_participant_count == 1:
                    logPrint('''一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a player present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb06Name, wb06Name))
                else:
                    logPrint('''%d名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d players present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_participant_count, wb06Name, recent_participant_count, wb06Name))
            if len(recent_friend_summonerNames) == 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friend_summonerNames[0], recent_friend_summonerNames[0]))
            elif len(recent_friend_summonerNames) > 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friend_summonerNames), ", ".join(recent_friend_summonerNames)))
            logPrint('请输入对局序号。输入“0”以返回上一层。\nPlease enter the gameId. Submit "0" to return to the last step.')

async def detect_dodged_champSelect(connection: Connection, infos: Optional[dict[str, dict[str, Any]]] = None) -> None:
    '''
    检测过往被秒退的英雄选择阶段中曾经遇到过的队友。<br>Detect allies encountered in dodged champ select stages.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    '''
    if infos == None:
        infos = {}
    #检测前先清理已经存在的对局记录的英雄选择会话缓存（Before detection, clear the champ select sessions whose corresponding matches are already in the history）
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    recent_LoLMatch_ids: list[str] = await sgpSession.request(connection, "GET", f"/match-history-query/v1/products/lol/player/%s?startIndex=0&count=500" %(current_info["puuid"]))
    if isinstance(recent_LoLMatch_ids, list):
        recent_LoLMatchIds: list[int] = list(map(lambda x: int(x.split("_")[1], recent_LoLMatch_ids)))
    else:
        recent_LoLMatchIds = []
    expired_session_matchIds: list[int] = []
    for matchId in champ_select_session_cache:
        if matchId in set(recent_LoLMatchIds):
            expired_session_matchIds.append(matchId)
    for matchId in expired_session_matchIds:
        del champ_select_session_cache[matchId]
    if len(champ_select_session_cache) == 0:
        logPrint("您尚未缓存任何英雄选择会话。\nYou haven't cached any champ select session yet.")
        return
    #准备一些常量（Prepare some constants）
    current_puuid_list: list[str] = list(map(lambda x: x["puuid"], AllAccounts))
    ally_count: int = 0
    enemy_count: int = 0
    recent_friend_summonerNames: list[str] = []
    recent_ChampSelect_player_fields: list[str] = ["gameId", "gameModeName", "team_color", "cellId", "gameName", "tagLine", "champion name"]
    recent_ChampSelect_player_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_ChampSelect_player_fields}
    LoLAlly_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_ChampSelect_player_dict_to_print)
    LoLEnemy_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_ChampSelect_player_dict_to_print)
    gameflow_phase: str = "None"
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
    #启动流程（Start process）
    logPrint('''请确保您在英雄选择阶段中，以便本脚本检测过往英雄选择阶段的玩家。按回车键开始检测，或者按“0”以返回上一步。\nPlease confirm you're during champ select, so that this script can detect whether there's a player encountered before. Press Enter to start detection, or press "0" to return to the last step.''')
    while True:
        detect: str = logInput()
        if detect != "" and detect[0] == "0":
            return
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase == "ChampSelect":
            break
        else:
            logPrint("您不在英雄选择阶段。\nYou're not in champ select.")
    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    logPrint(champ_select_session)
    if "errorCode" in champ_select_session:
        if champ_select_session["message"] == "No active delegate":
            logPrint("英雄选择会话已过期。\nChamp select session has expired.")
        return
    matchId: int = champ_select_session["gameId"]
    if matchId in champ_select_session_cache:
        del champ_select_session_cache[matchId] #查询近期遇到过的玩家不应包括当前对局（The current match should be included when the program searches for recently encountered summoners）
    recent_champSelectPlayer_df: pandas.DataFrame = await sort_multiChampSelect_players(connection, list(champ_select_session_cache.values()), queues_initial, LoLChampions_initial, championSkins, spells_initial, wardSkins, playerMode = 1, log = log) #英雄皮肤和饰品皮肤的语言与客户端相同（The language of champion and ward skins follows the League Client）    
    #比对数据（Compare data）
    gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
    gameModeName = gameflow_session["map"]["gameModeName"] + "(%d)" %(gameflow_session["gameData"]["queue"]["id"]) if gameflow_session["gameData"]["queue"]["name"] == "" else gameflow_session["gameData"]["queue"]["name"]
    wb07Name: str = "Recent ChampSelect Summoners in Match %s-%s (%s).xlsx" %(platformId, matchId, gameModeName)
    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    skip_lobby_member: bool = False
    lobby_member_puuids: list[str] = []
    if not "errorCode" in lobby_information and len(lobby_information["members"]) > 1:
        logPrint("检测时是否忽略小队成员？（输入任意键忽略，否则不忽略。）\nNeglect lobby members when detecting? (Submit any non-empty string to neglect, or null to refust neglecting.)")
        skip_lobby_member_str: str = logInput()
        skip_lobby_member = bool(skip_lobby_member_str)
        lobby_member_puuids = list(map(lambda x: x["puuid"], lobby_information["members"]))
    for ally in champ_select_session["myTeam"]:
        if not ally["puuid"] in set(current_puuid_list) | {"", BOT_UUID} and (ally["nameVisibilityType"] == "VISIBLE" or ally["nameVisibilityType"] == ""):
            ally_info_recapture: int = 0
            if ally["puuid"] in infos:
                ally_info_body: dict[str, Any] = infos[ally["puuid"]]
            else:
                ally_info: dict[str, Any] = await get_info(connection, ally["puuid"])
                while not ally_info["info_got"] and ally_info["body"]["httpStatus"] != 404 and ally_info_recapture < 3:
                    logPrint(ally_info["message"])
                    ally_info_recapture += 1
                    logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an ally (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                    ally_info = await get_info(connection, ally["puuid"])
                if ally_info["info_got"]:
                    ally_info_body = ally_info["body"]
                    infos[ally["puuid"]] = ally_info_body
                else:
                    logPrint(ally_info["message"])
                    logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an ally (puuid: %s) capture failed! The program will ignore this ally.")
                    continue
            LoLAlly_index: list[int] = [0] #第0行是中文表头，所以一开始要包含在内（The 0th line is Chinese header, so it should be contained in the beginning）
            for i in range(len(recent_champSelectPlayer_df["puuid"])):
                if recent_champSelectPlayer_df["puuid"][i] == ally["puuid"] and not (skip_lobby_member and recent_champSelectPlayer_df["puuid"][i] in lobby_member_puuids):
                    LoLAlly_index.append(i)
            if len(LoLAlly_index) > 1:
                ally_count += 1
                LoLAlly_df: pandas.DataFrame = recent_champSelectPlayer_df.loc[LoLAlly_index, :]
                LoLAlly_df_to_print = pandas.concat([LoLAlly_df_to_print, LoLAlly_df.loc[1:, recent_ChampSelect_player_fields]], axis = 0)
                if ally["puuid"] in friend_puuids:
                    recent_friend_summonerNames.append(get_info_name(ally_info_body))
                if not os.path.exists(wb07Name):
                    wb07CreateFlag: bool = create_workbook_win32(os.path.abspath(wb07Name))
                while True:
                    try:
                        with (pandas.ExcelWriter(path = wb07Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb07Name) else pandas.ExcelWriter(path = wb07Name)) as writer:
                            if len(LoLAlly_index) > 1:
                                addDefaultStyle(LoLAlly_df).to_excel(excel_writer = writer, sheet_name = get_info_name(ally_info_body) + " (LoL)")
                            logPrint("队友%s曾经与您一同战斗过%d次。\nAlly %s has fought with you for %d time(s)." %(get_info_name(ally_info_body), len(LoLAlly_index) - 1, get_info_name(ally_info_body), len(LoLAlly_index) - 1))
                    except PermissionError:
                        logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                        logInput()
                    else:
                        break
    if champ_select_session["theirTeam"]:
        for enemy in champ_select_session["theirTeam"]:
            if not enemy["puuid"] in set(current_puuid_list) | {"", BOT_UUID} and (enemy["nameVisibilityType"] == "VISIBLE" or enemy["nameVisibilityType"] == ""):
                enemy_info_recapture: int = 0
                if enemy["puuid"] in infos:
                    enemy_info_body: dict[str, Any] = infos[enemy["puuid"]]
                else:
                    enemy_info: dict[str, Any] = await get_info(connection, enemy["puuid"])
                    while not enemy_info["info_got"] and enemy_info["body"]["httpStatus"] != 404 and enemy_info_recapture < 3:
                        logPrint(enemy_info["message"])
                        enemy_info_recapture += 1
                        logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an enemy (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(enemy["puuid"], enemy_info_recapture, enemy["puuid"], enemy_info_recapture))
                        enemy_info = await get_info(connection, enemy["puuid"])
                    if enemy_info["info_got"]:
                        enemy_info_body = enemy_info["body"]
                        infos[enemy["puuid"]] = enemy_info_body
                    else:
                        logPrint(enemy_info["message"])
                        logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！将忽略该名对手。\nInformation of an enemy (puuid: %s) capture failed! The program will ignore this enemy.")
                        continue
                LoLEnemy_index: list[int] = [0]
                for i in range(len(recent_champSelectPlayer_df["puuid"])):
                    if recent_champSelectPlayer_df["puuid"][i] == enemy["puuid"] and not (skip_lobby_member and recent_champSelectPlayer_df["puuid"][i] in lobby_member_puuids):
                        LoLEnemy_index.append(i)
                if len(LoLEnemy_index) > 1:
                    enemy_count += 1
                    LoLEnemy_df: pandas.DataFrame = recent_champSelectPlayer_df.loc[LoLEnemy_index, :]
                    LoLEnemy_df_to_print = pandas.concat([LoLEnemy_df_to_print, LoLEnemy_df.loc[1:, recent_ChampSelect_player_fields]], axis = 0)
                    if enemy["puuid"] in friend_puuids:
                        recent_friend_summonerNames.append(get_info_name(enemy_info_body))
                    if not os.path.exists(wb07Name):
                        wb07CreateFlag: bool = create_workbook_win32(os.path.abspath(wb07Name))
                    while True:
                        try:
                            with (pandas.ExcelWriter(path = wb07Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb07Name) else pandas.ExcelWriter(path = wb07Name)) as writer:
                                if len(LoLEnemy_index) > 1:
                                    addDefaultStyle(LoLEnemy_df).to_excel(excel_writer = writer, sheet_name = get_info_name(enemy_info_body) + " (LoL)")
                                logPrint("对手%s曾经与您一同战斗过%d次。\nEnemy %s has fought with you for %d time(s)." %(get_info_name(enemy_info_body), len(LoLEnemy_index) - 1, get_info_name(enemy_info_body), len(LoLEnemy_index) - 1))
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                            logInput()
                        else:
                            break
    if ally_count == 0:
        logPrint("您目前遇到的都是新的队友。尝试拓展人缘吧！\nThe allies you've met now are all new. Try extending your friendship!")
    else:
        logPrint()
        print(format_df(LoLAlly_df_to_print, print_index = True, reserve_index = True)[0])
        log.write(format_df(LoLAlly_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if ally_count == 1:
            logPrint('''一名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an ally present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb07Name, wb07Name))
        else:
            logPrint('''%d名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d allies present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, wb07Name, ally_count, wb07Name))
    if any(map(lambda x: x["nameVisibilityType"] == "VISIBLE" or x["nameVisibilityType"] == "", champ_select_session["theirTeam"])):
        if enemy_count > 0:
            logPrint()
            print(format_df(LoLEnemy_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(LoLEnemy_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            if enemy_count == 1:
                logPrint('''一名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an enemy present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb07Name, wb07Name))
            else:
                logPrint('''%d名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d enemies present in your past matches. Please check the workbook "%s" in the main directory.''' %(enemy_count, wb07Name, enemy_count, wb07Name))
    if len(recent_friend_summonerNames) == 1:
        logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friend_summonerNames[0], recent_friend_summonerNames[0]))
    elif len(recent_friend_summonerNames) > 1:
        logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friend_summonerNames), ", ".join(recent_friend_summonerNames)))
    if not (all(map(lambda x: x["nameVisibilityType"] == "VISIBLE", champ_select_session["theirTeam"])) or all(map(lambda x: x["nameVisibilityType"] == "HIDDEN", champ_select_session["theirTeam"])) or all(map(lambda x: x["nameVisibilityType"] == "", champ_select_session["theirTeam"])) or all(map(lambda x: x["nameVisibilityType"] == "", champ_select_session["theirTeam"]))):
        logPrint("检测到敌方信息可见性异常！请检查之前输出的英雄选择阶段信息。\nDetected enemies' visibility abnormal! Please check the champ select session information printed before.")
    if not champ_select_session["isSpectating"]:
        champ_select_session_cache[matchId] = champ_select_session

async def detect_friend(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame) -> None:
    '''
    检测近期一起玩过的好友。<br>Detect recently played friends.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    '''
    recent_friend_count: int = 0
    recent_LoLPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"] if use_sgp else ["gameName", "tagLine", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"]
    recent_TFTPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameDate", "gameModeName", "last_round_format"]
    recent_LoLPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_LoLPlayer_fields}
    recent_TFTPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_TFTPlayer_fields}
    recent_LoLFriend_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    recent_TFTFriend_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_summonerName: str = get_info_name(current_info)
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    wb08Name: str = f"Recently Played Summoners in Friend List of {current_summonerName} - {platformId}.xlsx"
    for friend in friends:
        friend_summonerName: str = get_info_name(friend)
        LoLFriend_index: list[int] = [0]
        TFTFriend_index: list[int] = [0]
        if search_LoL:
            for i in range(len(recent_LoLPlayer_df["puuid"])):
                if recent_LoLPlayer_df["puuid"][i] == friend["puuid"]:
                    LoLFriend_index.append(i)
        if search_TFT:
            for i in range(len(recent_TFTPlayer_df["puuid"])):
                if recent_TFTPlayer_df["puuid"][i] == friend["puuid"]:
                    TFTFriend_index.append(i)
        if len(LoLFriend_index) + len(TFTFriend_index) > 2:
            recent_friend_count += 1
            recent_LoLFriend_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLFriend_index, :]
            # recent_LoLFriend_df.insert(1, "note", ["备注"] + [friend["note"]] * (len(LoLFriend_index) - 1))
            recent_LoLFriend_df = pandas.concat([recent_LoLFriend_df.iloc[:, :1], pandas.DataFrame({"note": ["备注"] + [friend["note"]] * (len(LoLFriend_index) - 1)}, index = LoLFriend_index), recent_LoLFriend_df.iloc[:, 1:]], axis = 1)
            recent_LoLFriend_df_to_print = pandas.concat([recent_LoLFriend_df_to_print, recent_LoLFriend_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
            recent_TFTFriend_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTFriend_index, :]
            # recent_LoLFriend_df.insert(1, "note", ["备注"] + [friend["note"]] * (len(LoLFriend_index) - 1))
            recent_TFTFriend_df = pandas.concat([recent_TFTFriend_df.iloc[:, :1], pandas.DataFrame({"note": ["备注"] + [friend["note"]] * (len(TFTFriend_index) - 1)}, index = TFTFriend_index), recent_TFTFriend_df.iloc[:, 1:]], axis = 1)
            recent_TFTFriend_df_to_print = pandas.concat([recent_TFTFriend_df_to_print, recent_TFTFriend_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
            if not os.path.exists(wb08Name):
                wb08CreateFlag: bool = create_workbook_win32(os.path.abspath(wb08Name))
            while True:
                try:
                    with (pandas.ExcelWriter(path = wb08Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb08Name) else pandas.ExcelWriter(path = wb08Name)) as writer:
                        if search_LoL and len(LoLFriend_index) > 1:
                            addDefaultStyle(recent_LoLFriend_df).to_excel(excel_writer = writer, sheet_name = friend_summonerName + " (LoL)")
                        if search_TFT and len(TFTFriend_index) > 1:
                            addDefaultStyle(recent_TFTFriend_df).to_excel(excel_writer = writer, sheet_name = friend_summonerName + " (TFT)")
                        logPrint("好友%s曾经与您一同战斗过%d次。\nFriend %s has fought with you for %d time(s)." %(friend_summonerName, len(LoLFriend_index) + len(TFTFriend_index) - 2, friend_summonerName, len(LoLFriend_index) + len(TFTFriend_index) - 2))
                except PermissionError:
                    logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                    logInput()
                else:
                    break
    if len(friends) == 0:
        logPrint("您尚未添加任何好友。尝试拓展人缘吧！\nYou haven't added any friend. Try extending your friendship!")
    elif recent_friend_count == 0:
        logPrint("您近期还没有和任何好友一起玩过。这不赶紧开个黑ヽ(*^ｰ^)人(^ｰ^*)ノ\nYou haven't played with any friend recently. Go for a game with one of your friends ...")
    else:
        logPrint()
        if search_LoL:
            print(format_df(recent_LoLFriend_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_LoLFriend_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if search_LoL and search_TFT:
            logPrint()
        if search_TFT:
            print(format_df(recent_TFTFriend_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_TFTFriend_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if recent_friend_count == 1:
            logPrint('''一名好友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a friend present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb08Name, wb08Name))
        else:
            logPrint('''%d名好友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d friends present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_friend_count, wb08Name, recent_friend_count, wb08Name))

async def detect_friend_request(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame) -> None:
    '''
    检测好友请求中近期一起玩过的玩家。<br>Detect recently played summoners in the friend requests.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    '''
    recent_prefriend_count: int = 0
    recent_LoLPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"] if use_sgp else ["gameName", "tagLine", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"]
    recent_TFTPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameDate", "gameModeName", "last_round_format"]
    recent_LoLPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_LoLPlayer_fields}
    recent_TFTPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_TFTPlayer_fields}
    recent_LoLFriend_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    recent_TFTFriend_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    recent_LoLPrefriend_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    recent_TFTPrefriend_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_summonerName: str = get_info_name(current_info)
    friend_requests: list[dict[str, Any]] = await (await (connection.request("GET", "/lol-chat/v2/friend-requests"))).json()
    wb09Name: str = f"Recently Played Summoners in Friend Requests of {current_summonerName} - {platformId}.xlsx"
    for prefriend in friend_requests:
        prefriend_summonerName: str = prefriend["name"] if prefriend["gameName"] == "" and prefriend["tagLine"] == "" else prefriend["gameName"] + "#" + prefriend["tagLine"]
        LoLPrefriend_index: list[int] = [0]
        TFTPrefriend_index: list[int] = [0]
        if search_LoL:
            for i in range(len(recent_LoLPlayer_df["puuid"])):
                if recent_LoLPlayer_df["puuid"][i] == prefriend["puuid"]:
                    LoLPrefriend_index.append(i)
        if search_TFT:
            for i in range(len(recent_TFTPlayer_df["puuid"])):
                if recent_TFTPlayer_df["puuid"][i] == prefriend["puuid"]:
                    TFTPrefriend_index.append(i)
        if len(LoLPrefriend_index) + len(TFTPrefriend_index) > 2:
            recent_prefriend_count += 1
            recent_LoLPrefriend_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLPrefriend_index, :]
            recent_LoLPrefriend_df_to_print = pandas.concat([recent_LoLPrefriend_df_to_print, recent_LoLPrefriend_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
            recent_TFTPrefriend_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTPrefriend_index, :]
            recent_TFTPrefriend_df_to_print = pandas.concat([recent_TFTPrefriend_df_to_print, recent_TFTPrefriend_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
            if not os.path.exists(wb09Name):
                wb09CreateFlag: bool = create_workbook_win32(os.path.abspath(wb09Name))
            while True:
                try:
                    with (pandas.ExcelWriter(path = wb09Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb09Name) else pandas.ExcelWriter(path = wb09Name)) as writer:
                        if search_LoL and len(LoLPrefriend_index) > 1:
                            addDefaultStyle(recent_LoLPrefriend_df).to_excel(excel_writer = writer, sheet_name = prefriend_summonerName + " (" + prefriend["direction"] + ") (LoL)")
                        if search_TFT and len(TFTPrefriend_index) > 1:
                            addDefaultStyle(recent_TFTPrefriend_df).to_excel(excel_writer = writer, sheet_name = prefriend_summonerName + " (" + prefriend["direction"] + ") (TFT)")
                        logPrint("好友请求列表中的%s曾经与您一同战斗过%d次。\nPlayer %s in friend request list has fought with you for %d time(s)." %(prefriend_summonerName, len(LoLPrefriend_index) + len(TFTPrefriend_index) - 2, prefriend_summonerName, len(LoLPrefriend_index) + len(TFTPrefriend_index) - 2))
                except PermissionError:
                    logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                    logInput()
                else:
                    break
    if len(friend_requests) == 0:
        logPrint("您尚未发送或收到任何好友请求。尝试拓展人缘吧！\nYou haven't sent or received any friend request. Try extending your friendship!")
    elif recent_prefriend_count == 0:
        logPrint("您近期未曾和好友请求列表中的玩家一起战斗过。这可能是因为好友请求太久未审核，或者该请求源于朋友或视频推荐，或者该请求不正当。\nYou haven't fought with any player in the friend request list. This may be because this request is put aside for too long, this request results from the recommendation from a friend or a video, or this request isn't sent in a proper manner.")
    else:
        logPrint()
        if search_LoL:
            print(format_df(recent_LoLPrefriend_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_LoLPrefriend_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if search_LoL and search_TFT:
            logPrint()
        if search_TFT:
            print(format_df(recent_TFTPrefriend_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_TFTPrefriend_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if recent_prefriend_count == 1:
            logPrint('''好友请求列表中的一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a friend in the request list that is present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb09Name, wb09Name))
        else:
            logPrint('''好友请求列表中的%d名好友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d friends in the request that is present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_prefriend_count, wb09Name, recent_prefriend_count, wb09Name))

async def detect_party_invitaion(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame, infos: Optional[dict[str, dict[str, Any]]] = None) -> None:
    '''
    检测组队邀请发起人中近期一起玩过的玩家。<br>Detect recently played summoners who send party invitations.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    '''
    if infos == None:
        infos = {}
    invitee_count: int = 0
    inviter_count: int = 0
    recent_friend_summonerNames = []
    recent_LoLPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"] if use_sgp else ["gameName", "tagLine", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"]
    recent_TFTPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameDate", "gameModeName", "last_round_format"]
    recent_LoLPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_LoLPlayer_fields}
    recent_TFTPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_TFTPlayer_fields}
    LoLInvitee_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    TFTInvitee_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    LoLInviter_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    TFTInviter_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_summonerName: str = get_info_name(current_info)
    current_summonerId: int = current_info["summonerId"]
    friends: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    friend_puuids: list[str] = list(map(lambda x: x["puuid"], friends))
    wb10Name: str = f"Recently Played Summoners in Invitations to and from {current_summonerName} - {platformId}.xlsx"
    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    lobbyInvitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/lobby/invitations")).json()
    if not "errorCode" in lobbyInvitations:
        for invid in lobbyInvitations:
            if invid["toSummonerId"] != current_summonerId:
                invitee_info_recapture: int = 0
                invitee_info: dict[str, Any] = await get_info(connection, invid["toSummonerId"])
                while not invitee_info["info_got"] and invitee_info["body"]["httpStatus"] != 404 and invitee_info_recapture < 3:
                    logPrint(invitee_info["message"])
                    invitee_info_recapture += 1
                    logPrint("被邀请者信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an invitee (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(invid["toSummonerId"], invitee_info_recapture, invid["toSummonerId"], invitee_info_recapture))
                    invitee_info = await get_info(connection, invid["toSummonerId"])
                if invitee_info["info_got"]:
                    invitee_info_body: dict[str, Any] = invitee_info["body"]
                    infos[invitee_info_body["puuid"]] = invitee_info_body
                else:
                    logPrint(invitee_info["message"])
                    logPrint("被邀请者信息（召唤师序号：%d）获取失败！将忽略该被邀请者。\nInformation of an invitee (summonerId: %d) capture failed! The program will ignore this invitee.")
                    continue
                LoLInvitee_index: list[int] = [0]
                TFTInvitee_index: list[int] = [0]
                if search_LoL:
                    for i in range(len(recent_LoLPlayer_df["puuid"])):
                        if recent_LoLPlayer_df["puuid"][i] == invitee_info_body["puuid"]:
                            LoLInvitee_index.append(i)
                if search_TFT:
                    for i in range(len(recent_TFTPlayer_df["puuid"])):
                        if recent_TFTPlayer_df["puuid"][i] == invitee_info_body["puuid"]:
                            TFTInvitee_index.append(i)
                if len(LoLInvitee_index) + len(TFTInvitee_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTInvitee_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTInvitee_index is defined and its length is at least 1）
                    invitee_count += 1
                    LoLInvitee_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLInvitee_index, :]
                    LoLInvitee_df_to_print = pandas.concat([LoLInvitee_df_to_print, LoLInvitee_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                    TFTInvitee_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTInvitee_index, :]
                    TFTInvitee_df_to_print = pandas.concat([TFTInvitee_df_to_print, TFTInvitee_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                    if invitee_info_body["puuid"] in friend_puuids:
                        recent_friend_summonerNames.append(get_info_name(invitee_info_body))
                    if not os.path.exists(wb10Name):
                        wb10CreateFlag: bool = create_workbook_win32(os.path.abspath(wb10Name))
                    while True:
                        try:
                            with (pandas.ExcelWriter(path = wb10Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb10Name) else pandas.ExcelWriter(path = wb10Name)) as writer:
                                if search_LoL and len(LoLInvitee_index) > 1:
                                    addDefaultStyle(LoLInvitee_df).to_excel(excel_writer = writer, sheet_name = get_info_name(invitee_info_body) + " (out) (LoL)")
                                if search_TFT and len(TFTInvitee_index) > 1:
                                    addDefaultStyle(TFTInvitee_df).to_excel(excel_writer = writer, sheet_name = get_info_name(invitee_info_body) + " (out) (TFT)")
                                logPrint("被邀请者%s曾经与您一同战斗过%d次。\nInvitee %s has fought with you for %d time(s)." %(get_info_name(invitee_info_body), len(LoLInvitee_index) + len(TFTInvitee_index) - 2, get_info_name(invitee_info_body), len(LoLInvitee_index) + len(TFTInvitee_index) - 2))
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                            logInput()
                        else:
                            break
    receivedInvitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
    for invid in receivedInvitations:
        inviter_info_recapture: int = 0
        inviter_info: dict[str,Any] = await get_info(connection, invid["fromSummonerId"])
        while not inviter_info["info_got"] and inviter_info["body"]["httpStatus"] != 404 and inviter_info_recapture < 3:
            logPrint(inviter_info["message"])
            inviter_info_recapture += 1
            logPrint("邀请者信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an inviter (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(invid["fromSummonerId"], inviter_info_recapture, invid["fromSummonerId"], inviter_info_recapture))
            inviter_info: dict[str, Any] = await get_info(connection, invid["fromSummonerId"])
        if inviter_info["info_got"]:
            inviter_info_body = inviter_info["body"]
            infos[inviter_info_body["puuid"]] = inviter_info_body
        else:
            logPrint(inviter_info["message"])
            logPrint("邀请者信息（召唤师序号：%d）获取失败！将忽略该邀请者。\nInformation of an inviter (summonerId: %d) capture failed! The program will ignore this inviter.")
            continue
        LoLInviter_index: list[int] = [0]
        TFTInviter_index: list[int] = [0]
        if search_LoL:
            for i in range(len(recent_LoLPlayer_df["puuid"])):
                if recent_LoLPlayer_df["puuid"][i] == inviter_info_body["puuid"]:
                    LoLInviter_index.append(i)
        if search_TFT:
            for i in range(len(recent_TFTPlayer_df["puuid"])):
                if recent_TFTPlayer_df["puuid"][i] == inviter_info_body["puuid"]:
                    TFTInviter_index.append(i)
        if len(LoLInviter_index) + len(TFTInviter_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTInviter_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTInviter_index is defined and its length is at least 1）
            inviter_count += 1
            LoLInviter_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLInviter_index, :]
            LoLInviter_df_to_print = pandas.concat([LoLInviter_df_to_print, LoLInviter_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
            TFTInviter_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTInviter_index, :]
            TFTInviter_df_to_print = pandas.concat([TFTInviter_df_to_print, TFTInviter_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
            if inviter_info_body["puuid"] in friend_puuids:
                recent_friend_summonerNames.append(get_info_name(inviter_info_body))
            if not os.path.exists(wb10Name):
                wb10CreateFlag: bool = create_workbook_win32(os.path.abspath(wb10Name))
            while True:
                try:
                    with (pandas.ExcelWriter(path = wb10Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb10Name) else pandas.ExcelWriter(path = wb10Name)) as writer:
                        if search_LoL and len(LoLInviter_index) > 1:
                            addDefaultStyle(LoLInviter_df).to_excel(excel_writer = writer, sheet_name = get_info_name(inviter_info_body) + " (in) (LoL)")
                        if search_TFT and len(TFTInviter_index) > 1:
                            addDefaultStyle(TFTInviter_df).to_excel(excel_writer = writer, sheet_name = get_info_name(inviter_info_body) + " (in) (TFT)")
                        logPrint("邀请者%s曾经与您一同战斗过%d次。\nInviter %s has fought with you for %d time(s)." %(get_info_name(inviter_info_body), len(LoLInviter_index) + len(TFTInviter_index) - 2, get_info_name(inviter_info_body), len(LoLInviter_index) + len(TFTInviter_index) - 2))
                except PermissionError:
                    logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                    logInput()
                else:
                    break
    recent_friend_summonerNames: list[str] = list(set(recent_friend_summonerNames)) #被邀请者和邀请者可能重复（Invitees may overlap with inviters）
    if ("errorCode" in lobbyInvitations or lobby_information["gameConfig"]["isCustom"] and len(lobbyInvitations) == 0 or not lobby_information["gameConfig"]["isCustom"] and len(lobbyInvitations) == 1) and len(receivedInvitations) == 0:
        logPrint("您尚未发送邀请，也未被邀请。\nYou haven't sent any invitation or been invited by anyone.")
    else:
        if invitee_count == 0 and inviter_count == 0:
            logPrint("您近期未曾和您邀请的玩家或者邀请您的玩家一起战斗过。尝试拓展人缘吧！\nYou haven't fought with any inviter or invitee. Try extending your friendship.")
        else:
            logPrint("\n近期一起玩过的被邀请者信息：\nRecently played invitee information:")
            if invitee_count > 0:
                if search_LoL:
                    print(format_df(LoLInvitee_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(LoLInvitee_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if search_LoL and search_TFT:
                    logPrint()
                if search_TFT:
                    print(format_df(TFTInvitee_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(TFTInvitee_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            logPrint("近期一起玩过的邀请者信息：\nRecently played inviter information:")
            if inviter_count > 0:
                if search_LoL:
                    print(format_df(LoLInvitee_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(LoLInvitee_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                if search_LoL and search_TFT:
                    logPrint()
                if search_TFT:
                    print(format_df(TFTInvitee_df_to_print, print_index = True, reserve_index = True)[0])
                    log.write(format_df(TFTInvitee_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            if invitee_count > 0:
                if invitee_count == 1:
                    logPrint('''一名您邀请的玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an invitee present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb10Name, wb10Name))
                else:
                    logPrint('''%d名您邀请的玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d invitees present in your past matches. Please check the workbook "%s" in the main directory.''' %(invitee_count, wb10Name, invitee_count, wb10Name))
            if inviter_count > 0:
                if inviter_count == 1:
                    logPrint('''一名向您发起邀请的玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an inviter present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb10Name, wb10Name))
                else:
                    logPrint('''%d名向您发起邀请的玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d inviters present in your past matches. Please check the workbook "%s" in the main directory.''' %(inviter_count, wb10Name, inviter_count, wb10Name))
            if len(recent_friend_summonerNames) == 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friend_summonerNames[0], recent_friend_summonerNames[0]))
            elif len(recent_friend_summonerNames) > 1:
                logPrint("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friend_summonerNames), ", ".join(recent_friend_summonerNames)))

async def detect_blockList(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame) -> None:
    '''
    检测黑名单中近期一起玩过的玩家。<br>Detect recently played summoners in the block list.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    '''
    recent_blockedPlayer_count: int = 0
    recent_LoLPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"] if use_sgp else ["gameName", "tagLine", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"]
    recent_TFTPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameDate", "gameModeName", "last_round_format"]
    recent_LoLPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_LoLPlayer_fields}
    recent_TFTPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_TFTPlayer_fields}
    recent_LoLBlockedPlayer_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    recent_TFTBlockedPlayer_df_to_print: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_summonerName: str = get_info_name(current_info)
    blockList: list[dict[str, Any]] = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
    wb11Name: str = f"Recently Played Summoners in Block List of {current_summonerName} - {platformId}.xlsx"
    for blockedPlayer in blockList:
        blockedPlayer_summonerName: str = get_info_name(blockedPlayer)
        LoLBlockedPlayer_index: list[int] = [0]
        TFTBlockedPlayer_index: list[int] = [0]
        if search_LoL:
            for i in range(len(recent_LoLPlayer_df["puuid"])):
                if recent_LoLPlayer_df["puuid"][i] == blockedPlayer["puuid"]:
                    LoLBlockedPlayer_index.append(i)
        if search_TFT:
            for i in range(len(recent_TFTPlayer_df["puuid"])):
                if recent_TFTPlayer_df["puuid"][i] == blockedPlayer["puuid"]:
                    TFTBlockedPlayer_index.append(i)
        if len(LoLBlockedPlayer_index) + len(TFTBlockedPlayer_index) > 2:
            recent_blockedPlayer_count += 1
            recent_LoLBlockedPlayer_df: pandas.DataFrame = recent_LoLPlayer_df.loc[LoLBlockedPlayer_index, :]
            recent_LoLBlockedPlayer_df_to_print = pandas.concat([recent_LoLBlockedPlayer_df_to_print, recent_LoLBlockedPlayer_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
            recent_TFTBlockedPlayer_df: pandas.DataFrame = recent_TFTPlayer_df.loc[TFTBlockedPlayer_index, :]
            recent_TFTBlockedPlayer_df_to_print = pandas.concat([recent_TFTBlockedPlayer_df_to_print, recent_TFTBlockedPlayer_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
            if not os.path.exists(wb11Name):
                wb11CreateFlag: bool = create_workbook_win32(os.path.abspath(wb11Name))
            while True:
                try:
                    with (pandas.ExcelWriter(path = wb11Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb11Name) else pandas.ExcelWriter(path = wb11Name)) as writer:
                        if search_LoL and len(LoLBlockedPlayer_index) > 1:
                            addDefaultStyle(recent_LoLBlockedPlayer_df).to_excel(excel_writer = writer, sheet_name = blockedPlayer_summonerName + " (LoL)")
                        if search_TFT and len(TFTBlockedPlayer_index) > 1:
                            addDefaultStyle(recent_TFTBlockedPlayer_df).to_excel(excel_writer = writer, sheet_name = blockedPlayer_summonerName + " (TFT)")
                        logPrint("黑名单玩家%s曾经与您一同战斗过%d次。\nThe blocked player %s has fought with you for %d time(s)." %(blockedPlayer_summonerName, len(LoLBlockedPlayer_index) + len(TFTBlockedPlayer_index) - 2, blockedPlayer_summonerName, len(LoLBlockedPlayer_index) + len(TFTBlockedPlayer_index) - 2))
                except PermissionError:
                    logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                    logInput()
                else:
                    break
    if len(blockList) == 0:
        logPrint("您尚未拉黑过人。恭喜！\nYou haven't blocked any friend. Congratulations!")
    elif recent_blockedPlayer_count == 0:
        logPrint("您近期还没有和任何黑名单玩家一起玩过。\nYou haven't played with any blocked player recently.")
    else:
        logPrint()
        if search_LoL:
            print(format_df(recent_LoLBlockedPlayer_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_LoLBlockedPlayer_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if search_LoL and search_TFT:
            logPrint()
        if search_TFT:
            print(format_df(recent_TFTBlockedPlayer_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_TFTBlockedPlayer_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if recent_blockedPlayer_count == 1:
            logPrint('''一名黑名单玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a blocked player present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb11Name, wb11Name))
        else:
            logPrint('''%d名黑名单玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d blocked players present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_blockedPlayer_count, wb11Name, recent_blockedPlayer_count, wb11Name))

async def detect_custom_list(connection: Connection, search_LoL: bool, search_TFT: bool, recent_LoLPlayer_df: pandas.DataFrame, recent_TFTPlayer_df: pandas.DataFrame, infos: Optional[dict[str, dict[str, Any]]] = None) -> None:
    '''
    检测一个自定义召唤师名称列表中近期一起玩过的玩家。<br>Detect recently played summoners in a custom summoner name list.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param search_LoL: 是否搜索过英雄联盟对局记录。<br>Whether LoL match history has been searched.
    :type search_LoL: bool
    :param search_TFT: 是否搜索过云顶之弈对局记录。<br>Whether TFT match history has been searched.
    :type search_TFT: bool
    :param recent_LoLPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_LoLPlayer_df: pandas.DataFrame
    :param recent_TFTPlayer_df: 近期一起玩过的英雄联盟玩家数据框。<br>Recently played LoL summoner dataframe.
    :type recent_TFTPlayer_df: pandas.DataFrame
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    '''
    if infos == None:
        infos = {}
    current_puuid_list: list[str] = list(map(lambda x: x["puuid"], AllAccounts))
    current_summonerName_list: list[str] = list(map(get_info_name, AllAccounts))
    summoners: list[str] = []
    logPrint(f"请输入一个由召唤师名称或玩家通用唯一识别码组成的列表。注意列表的每个元素都必须用半角引号括起来。示例：\nPlease input a list of summoner names or puuids. Note that each element of the list must be quoted with English quotation marks. Examples:\n%s\n%s" %(json.dumps(current_summonerName_list, ensure_ascii = False), json.dumps(current_puuid_list, ensure_ascii = False))) 
    while True:
        summoners_str: str = logInput()
        if summoners_str == "":
            continue
        elif summoners_str == "0":
            break
        else:
            try:
                tmp = eval(summoners_str)
            except SyntaxError:
                traceback_info = traceback.format_exc()
                logPrint(traceback_info)
                logPrint("语法错误！请重新输入。\nGrammar error! Please try again.")
            else:
                if not isinstance(tmp, list):
                    logPrint("请输入一个列表！\nPlease input a list!")
                elif not all(map(lambda x: isinstance(x, str), tmp)):
                    logPrint("请输入一个元素全为字符串的列表！\nPlease input a list consisting of only string elements.")
                else:
                    summoners = tmp
                    break
    if summoners_str == "0":
        return
    recent_players_count = 0
    recent_LoLPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"] if use_sgp else ["gameName", "tagLine", "gameCreationDate", "gameModeName", "champion_name", "K/D/A"]
    recent_TFTPlayer_fields: list[str] = ["riotIdGameName", "riotIdTagline", "gameDate", "gameModeName", "last_round_format"]
    recent_LoLPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_LoLPlayer_fields}
    recent_TFTPlayer_dict_to_print: dict[str, list[Any]] = {key: [] for key in recent_TFTPlayer_fields}
    recent_LoLPlayer_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
    recent_TFTPlayer_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
    wb12Name: str = f"Recently Played Summoners in Specified Player List - {platformId}.xlsx"
    logPrint("是否呈现非法召唤师名称警告？（输入任意键呈现，否则不呈现。）\nDo you want to display illegal summoner name warning? (Input anything to display the warnings, or null to stop displaying.)")
    illegal_name_warning_str: str = logInput()
    illegal_name_warning: bool = bool(illegal_name_warning_str)
    legal_summoners: dict[str, str] = {}
    for summoner in summoners:
        info_check = await get_info(connection, summoner)
        if info_check["info_got"]:
            info_check_body: dict[str, Any] = info_check["body"]
            infos[info_check_body["puuid"]] = info_check_body
            detect_summonerName: str = get_info_name(info_check_body)
            legal_summoners[info_check_body["puuid"]] = detect_summonerName
            LoLPlayer_index = [0]
            TFTPlayer_index = [0]
            if search_LoL:
                for i in range(len(recent_LoLPlayer_df["puuid"])):
                    if recent_LoLPlayer_df["puuid"][i] == info_check_body["puuid"]:
                        LoLPlayer_index.append(i)
            if search_TFT:
                for i in range(len(recent_TFTPlayer_df["puuid"])):
                    if recent_TFTPlayer_df["puuid"][i] == info_check_body["puuid"]:
                        TFTPlayer_index.append(i)
            if len(LoLPlayer_index) + len(TFTPlayer_index) > 2:
                recent_players_count += 1
                recent_LoLPlayer_df = recent_LoLPlayer_df.loc[LoLPlayer_index, :]
                recent_LoLPlayer_df_to_print = pandas.concat([recent_LoLPlayer_df_to_print, recent_LoLPlayer_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                recent_TFTPlayer_df = recent_TFTPlayer_df.loc[TFTPlayer_index, :]
                recent_TFTPlayer_df_to_print = pandas.concat([recent_TFTPlayer_df_to_print, recent_TFTPlayer_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                if not os.path.exists(wb12Name):
                    wb12CreateFlag: bool = create_workbook_win32(os.path.abspath(wb12Name))
                while True:
                    try:
                        with (pandas.ExcelWriter(path = wb12Name, mode = "a", if_sheet_exists = "replace") if os.path.exists(wb12Name) else pandas.ExcelWriter(path = wb12Name)) as writer:
                            if search_LoL and len(LoLPlayer_index) > 1:
                                addDefaultStyle(recent_LoLPlayer_df).to_excel(excel_writer = writer, sheet_name = detect_summonerName + " (LoL)")
                            if search_TFT and len(TFTPlayer_index) > 1:
                                addDefaultStyle(recent_TFTPlayer_df).to_excel(excel_writer = writer, sheet_name = detect_summonerName + " (TFT)")
                            logPrint("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d time(s)." %(detect_summonerName, len(LoLPlayer_index) + len(TFTPlayer_index) - 2, detect_summonerName, len(LoLPlayer_index) + len(TFTPlayer_index) - 2))
                    except PermissionError:
                        logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                        logInput()
                    else:
                        break
        elif illegal_name_warning:
            logPrint(info_check["message"])
    logPrint("检测到%d名玩家：\nDetected %d player(s):" %(len(legal_summoners), len(legal_summoners)))
    logPrint(pandas.DataFrame({"puuid": legal_summoners.keys(), "summonerName": legal_summoners.values()}), write_time = False)
    if recent_players_count == 0:
        logPrint("未从以上玩家中检测到近期一起玩过的玩家。\nNo players detected in the above summoner list.")
    else:
        logPrint()
        if search_LoL:
            print(format_df(recent_LoLPlayer_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_LoLPlayer_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if search_LoL and search_TFT:
            logPrint()
        if search_TFT:
            print(format_df(recent_TFTPlayer_df_to_print, print_index = True, reserve_index = True)[0])
            log.write(format_df(recent_TFTPlayer_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
        if recent_players_count == 1:
            logPrint('''一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a player present in your past matches. Please check the workbook "%s" in the main directory.''' %(wb12Name, wb12Name))
        else:
            logPrint('''%d名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d players present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_players_count, wb12Name, recent_players_count, wb12Name))

async def search_recent_players(connection: Connection) -> None:
    global session, platformId, AllAccounts
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId = current_party["platformId"]
    riot_client_info: list[str] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info: dict[str, str] = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region: str = client_info["--region"]
    platform_folder: str = set_platform_folder(region, platformId)
    match_folder: str = os.path.join(platform_folder, "1. MatchIDs").replace("\\", "/")
    logPrint("请选择召唤师技能和装备的输出语言【默认为中文（中国）】：\nPlease select a language to output the summoner spells and items (the default option is zh_CN):")
    language_df: pandas.DataFrame = pandas.DataFrame(language_dict)
    print(format_df(language_df)[0])
    log.write(format_df(language_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
    while True:
        language_option: str = logInput()
        if language_option == "" or language_option in [str(i) for i in range(1, 31)]:
            if language_option == "":
                language_option = "29"
            language_code: str = list(language_ddragon.keys())[int(language_option) - 1]
            switch_language, exit_flag = prepare_data_resources(platformId, language_code)
            if exit_flag:
                return
            if switch_language:
                continue
            else:
                break
        elif language_option[0] == "0":
            return
        else:
            logPrint("语言选项输入错误！请重新输入：\nERROR input of language option! Please try again:")
    #首先准备一些数据（First, prepare some data）
    #准备自己的召唤师数据（Prepare the information of the user himself/herself）
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json() #一定要注意，在本脚本中，`current_puuid`和`current_info["puuid"]`不是一回事（Pay attention that `current_puuid` and `current_info["puuid"]` aren't the same thing in this program）
    current_infos: list[dict[str, Any]] = [current_info] #检测模式的小号模式中存在多个自己（There're many selves in Smurf Mode of Detect Mode）
    #准备游戏模式数据（Prepare game mode data）
    gameQueues_initial: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues: dict[int, dict[str, Any]] = {queue["id"]: queue for queue in gameQueues_initial}
    #下面创建一个字典，用来存储程序正在使用的各数据资源的版本（The following code create a dictionary to store the versions of data resources that the program currently uses）
    current_versions: dict[str, str] = {"summonerIcon": URLPatch, "spell": URLPatch, "LoLChampion": URLPatch, "LoLItem": URLPatch, "summonerIcon": URLPatch, "perk": URLPatch, "perkstyle": URLPatch, "TFTAugment": URLPatch, "TFTChampion": URLPatch, "TFTItem": URLPatch, "TFTCompanion": URLPatch, "TFTTrait": URLPatch, "CherryAugment": URLPatch}
    #下面创建一个字典，用来存储程序正在使用的各数据资源的版本下发生错误的键。当某个数据资源更换版本时，其出错的键会被清空（The following code create a dictionary to store the keys that fail to map to the constant dictionaries under certain versions of each kind of data resource. Once the version of a data resource changes, its unmapped keys will be cleared）
    unmapped_keys: dict[str, set[Any]] = {"summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set(), "CherryAugment": set()}
    #控制只输出一遍的提示（Control the hint to be displayed only once）
    # Vanguard_warning_printed: str = False
    #定义全局对局信息缓存（Define global match information caches）
    LoLGame_summary_cache_lcu: dict[int, dict[str, Any]] = {}
    LoLGame_summary_cache_sgp: dict[int, dict[str, Any]] = {}
    TFTGame_summary_cache_sgp: dict[int, dict[str, Any]] = {}
    #然后获取历史记录（Next, fetch the history）
    while True:
        #初始化所有数据资源（Initialize all data resources）
        logPrint("\n正在初始化所有数据资源……\nInitializing all data resources ...\n")
        patches: list[str] = patches_initial.copy()
        queues: dict[int, dict[str, Any]] = queues_initial.copy()
        spells: dict[int, dict[str, Any]] = spells_initial.copy()
        LoLChampions: dict[int, dict[str, Any]] = LoLChampions_initial.copy()
        LoLItems: dict[int, dict[str, Any]] = LoLItems_initial.copy()
        summonerIcons: dict[int, dict[str, Any]] = summonerIcons_initial.copy()
        perks: dict[int, dict[str, Any]] = perks_initial.copy()
        perkstyles: dict[int, dict[str, Any]] = perkstyles_initial.copy()
        TFTAugments: dict[str, dict[str, Any]] = TFTAugments_initial.copy()
        TFTChampions: dict[str, dict[str, Any]] = TFTChampions_initial.copy()
        TFTItems: dict[str, dict[str, Any]] = TFTItems_initial.copy()
        TFTCompanions: dict[str, dict[str, Any]] = TFTCompanions_initial.copy()
        TFTTraits: dict[str, dict[str, Any]] = TFTTraits_initial.copy()
        CherryAugments: dict[int, dict[str, Any]] = CherryAugments_initial.copy()
        current_versions = {"summonerIcon": URLPatch, "spell": URLPatch, "LoLChampion": URLPatch, "LoLItem": URLPatch, "summonerIcon": URLPatch, "perk": URLPatch, "perkstyle": URLPatch, "TFTAugment": URLPatch, "TFTChampion": URLPatch, "TFTItem": URLPatch, "TFTCompanion": URLPatch, "TFTTrait": URLPatch, "CherryAugment": URLPatch}
        unmapped_keys = {"summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set(), "CherryAugment": set()}
        infos: dict[str, dict[str, Any]] = {} #存储程序运行过程中遇到的玩家信息，防止后续程序反复获取已经获取过的玩家信息（Store the summoner information fetched during the program execution, in case the program would keep capturing the summoner information already fetched before）
        #如果检测到正在与他人交互，程序会提供选项，用户可通过输入选项的序号来直接选择某个召唤师（If the user is interacting with someone, the program will offer options, so that the user select one of those summoners by supplying the option index）
        members_to_detect: list[dict[str, Any]] = [current_info]
        gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck", "ChampSelect", "InProgress", "Reconnect"}:
            if gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck"}:
                lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                for member in lobby_information["members"]:
                    if not member["puuid"] in {current_info["puuid"], "", BOT_UUID}:
                        member_info_recapture: int = 0
                        if member["puuid"] in infos:
                            member_info_body: dict[str, Any] = infos[member["puuid"]]
                        else:
                            member_info: dict[str, Any] = await get_info(connection, member["puuid"])
                            while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                                logPrint(member_info["message"])
                                member_info_recapture += 1
                                logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of a member (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(member["puuid"], member_info_recapture, member["puuid"], member_info_recapture))
                                member_info = await get_info(connection, member["puuid"])
                            if member_info["info_got"]:
                                member_info_body = member_info["body"]
                                infos[member["puuid"]] = member_info_body
                            else:
                                logPrint(member_info["message"])
                                logPrint("成员信息（玩家通用唯一识别码：%s）获取失败！将忽略该名成员。\nInformation of a member (puuid: %s) capture failed! The program will ignore this member.")
                                continue
                        members_to_detect.append(member_info_body)
            elif gameflow_phase == "ChampSelect":
                champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                for ally in champ_select_session["myTeam"]:
                    if not ally["puuid"] in {current_info["puuid"], "", BOT_UUID} and (ally["nameVisibilityType"] == "VISIBLE" or ally["nameVisibilityType"] == ""):
                        ally_info_recapture: int = 0
                        if ally["puuid"] in infos:
                            ally_info_body: dict[str, Any] = infos[ally["puuid"]]
                        else:
                            ally_info: dict[str, Any] = await get_info(connection, ally["puuid"])
                            while not ally_info["info_got"] and ally_info["body"]["httpStatus"] != 404 and ally_info_recapture < 3:
                                logPrint(ally_info["message"])
                                ally_info_recapture += 1
                                logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an ally (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                                ally_info = await get_info(connection, ally["puuid"])
                            if ally_info["info_got"]:
                                ally_info_body = ally_info["body"]
                                infos[ally["puuid"]] = ally_info_body
                            else:
                                logPrint(ally_info["message"])
                                logPrint("队友信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an ally (puuid: %s) capture failed! The program will ignore this ally.")
                                continue
                        members_to_detect.append(ally_info_body)
                if champ_select_session["theirTeam"]:
                    for enemy in champ_select_session["theirTeam"]:
                        if not enemy["puuid"] in {current_info["puuid"], "", BOT_UUID} and (enemy["nameVisibilityType"] == "VISIBLE" or enemy["nameVisibilityType"] == ""):
                            enemy_info_recapture: int = 0
                            if enemy["puuid"] in infos:
                                enemy_info_body: dict[str, Any] = infos[enemy["puuid"]]
                            else:
                                enemy_info: dict[str, Any] = await get_info(connection, enemy["puuid"])
                                while not enemy_info["info_got"] and enemy_info["body"]["httpStatus"] != 404 and enemy_info_recapture < 3:
                                    logPrint(enemy_info["message"])
                                    enemy_info_recapture += 1
                                    logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an enemy (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(enemy["puuid"], enemy_info_recapture, enemy["puuid"], enemy_info_recapture))
                                    enemy_info = await get_info(connection, enemy["puuid"])
                                if enemy_info["info_got"]:
                                    enemy_info_body = enemy_info["body"]
                                    infos[enemy["puuid"]] = enemy_info_body
                                else:
                                    logPrint(enemy_info["message"])
                                    logPrint("对手信息（玩家通用唯一识别码：%s）获取失败！将忽略该名对手。\nInformation of an enemy (puuid: %s) capture failed! The program will ignore this enemy.")
                                    continue
                            members_to_detect.append(enemy_info_body)
            else:
                gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                gameData: dict[str, Any] = gameflow_session["gameData"]
                for player in gameData["teamOne"] + gameData["teamTwo"]:
                    if "puuid" in player and player["puuid"] != current_info["puuid"]: #电脑玩家没有玩家通用唯一识别码（Bot players don't have puuids）
                        player_info_recapture: int = 0
                        if player["puuid"] in infos:
                            player_info_body: dict[str, Any] = infos[player["puuid"]]
                        else:
                            player_info: dict[str, Any] = await get_info(connection, player["puuid"])
                            while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                                logPrint(player_info["message"])
                                player_info_recapture += 1
                                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture))
                                player_info = await get_info(connection, player["puuid"])
                            if player_info["info_got"]:
                                player_info_body = player_info["body"]
                                infos[player_info_body["puuid"]] = player_info_body
                            else:
                                logPrint(player_info["message"])
                                logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an player (puuid: %s) capture failed! The program will ignore this player.")
                                continue
                        members_to_detect.append(player_info_body)
        #处理主召唤师（Handle the main summoner）
        if len(members_to_detect) > 1:
            if gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck"}:
                gameflow_desc_zh: str = "房间内"
                gameflow_desc_en: str = "in a lobby"
            elif gameflow_phase == "ChampSelect":
                gameflow_desc_zh = "英雄选择阶段"
                gameflow_desc_en = "in champ select"
            else:
                gameflow_desc_zh = "游戏中"
                gameflow_desc_en = "in a game"
            logPrint(f'''检测到您正在{gameflow_desc_zh}。是否检测其他玩家的近期一起玩过的玩家？（输入下方其他玩家对应的编号以查询其他玩家，或者直接按回车键以查询用户本人。输入“0”以退出程序。）\nThe program detected that you're currently {gameflow_desc_en}. Do you want to detect recently played summoners of another player? (Submit the number corresponding to another player below to search for his/her recently player summoners, or press Enter directly to search for recently played summoners of the user itself. Submit "0" to exit the program.)''')
            for i in range(len(members_to_detect)):
                member_info_body = members_to_detect[i]
                logPrint("%d\t%s\t%s" %(i, member_info_body["puuid"], get_info_name(member_info_body)))
            memberId: str = logInput()
            if memberId == "0":
                break
            elif memberId in list(map(str, range(1, len(members_to_detect)))):
                summoner_name: str = members_to_detect[int(memberId)]["puuid"]
            else:
                summoner_name = memberId
        else:
            logPrint('请输入要查询的召唤师名称，退出请输入“0”。\nPlease input the summoner name to query. Submit "0" to exit.')
            summoner_name: str = logInput()
        if summoner_name == "0":
            break
        else:
            main_info: dict[str, Any] = await get_info(connection, summoner_name or "current-summoner") #当没有检测到用户与其它召唤师的交互，且用户直接按下回车时，表示查询自己的战绩（When no summoner is detected to be interacting with the user, and the user directly pressed Enter, the program will query the match history of the user itself）
            if not main_info["info_got"]:
                logPrint(main_info["message"])
                continue
            else:
                main_info_body: dict[str, Any] = main_info["body"]
                displayName: str = get_info_name(main_info_body) #用于扫描模式定位到某召唤师（Determines the directory which contains the summoner's data）
                current_summonerId: int = main_info_body["summonerId"] #用于排除房间邀请信息中的自己（Defined to exclude the user itself from the lobby invitations）
                current_puuid: str = main_info_body["puuid"] #用于核验对局是否包含该召唤师。此外，还用于扫描模式从对局的所有玩家信息中定位到该玩家（For use of checking whether the searched matches include this summoner. In addition, it's used for localization of this player from all players in a match in "scan" mode）
                current_summonerName: str = main_info_body["displayName"] if main_info_body["gameName"] == "" and main_info_body["tagLine"] == "" else main_info_body["gameName"] + "#" + main_info_body["tagLine"] #作用同上，用于模糊定位，主要应用于玩家通用唯一识别码发生变动的大区且在名称编号引入后注册的主召唤师的对局记录扫描模式（Acts as the same role as the above variable for a rough localization. It's mainly designed for Scan Mode on players that signed up after tagLine was introduced on servers that changed the players' puuids）
                infos[current_puuid] = main_info_body
        #处理小号（Handle the smurfs）
        smurfs: list[dict[str, Any]] = await load_smurf(connection, current_puuid = current_puuid, infos = infos)
        #整理账号信息（Organize accounts）
        AllAccounts = [main_info_body] + smurfs
        current_puuid_list: list[str] = list(map(lambda x: x["puuid"], AllAccounts))
        current_summonerName_list: list[str] = list(map(get_info_name, AllAccounts))
        #下面设置扫描模式的扫描目录（The following code determines the scanning directory for scan mode）
        folder: str = set_summonerInfo_folder(region, platformId, main_info_body)
        saved_LoLMatchIDs: list[int] = []
        json03name: str = f"Matches Saved (LoL) - {displayName}.json"
        json03path: str = os.path.join(folder, json03name).replace("\\", "/")
        os.makedirs(folder, exist_ok = True)
        if os.path.exists(json03path):
            try:
                with open(json03path, "r", encoding = "utf-8") as jsonfile02:
                    saved_LoLMatchIDs = json.load(jsonfile02)
            except:
                logPrint("已存储的英雄联盟对局数据格式错误！\nSaved LoL match data format error!")
            else:
                if not (isinstance(saved_LoLMatchIDs, list) and all(map(lambda x: isinstance(x, int), saved_LoLMatchIDs))):
                    logPrint("已存储的英雄联盟对局数据格式错误！\nSaved LoL match data format error!")
        saved_TFTMatchIDs: list[int] = []
        json04name: str = f"Matches Saved (TFT) - {displayName}.json"
        json04path: str = os.path.join(folder, json04name).replace("\\", "/")
        os.makedirs(folder, exist_ok = True)
        if os.path.exists(json04path):
            try:
                with open(json04path, "r", encoding = "utf-8") as jsonfile03:
                    saved_TFTMatchIDs = json.load(jsonfile03)
            except:
                logPrint("已存储的云顶之弈对局数据格式错误！\nSaved TFT match data format error!")
            else:
                if not (isinstance(saved_TFTMatchIDs, list) and all(map(lambda x: isinstance(x, int), saved_TFTMatchIDs))):
                    logPrint("已存储的云顶之弈对局数据格式错误！\nSaved TFT match data format error!")
        
        #下面获取最近一起玩过的英雄联盟玩家的信息（The following code captures the recently played LoL players' information）
        logPrint("是否查询英雄联盟对局记录？（输入任意键查询，否则不查询）\nSearch LoL matches? (Input anything to search or null to skip searching LoL matches)")
        search_LoL_str: str = logInput()
        search_LoL: bool = bool(search_LoL_str)
        LoLMatchIDs: list[int] = []
        if search_LoL:
            LoLHistory_dfs: list[pandas.DataFrame] = []
            for i in range(len(AllAccounts)):
                queues = queues_initial.copy()
                spells = spells_initial.copy()
                LoLChampions = LoLChampions_initial.copy()
                LoLItems = LoLItems_initial.copy()
                summonerIcons = summonerIcons_initial.copy()
                perks = perks_initial.copy()
                perkstyles = perkstyles_initial.copy()
                CherryAugments = CherryAugments_initial.copy()
                current_versions["queue"] = current_versions["summonerIcon"] = current_versions["spell"] = current_versions["LoLChampion"] = current_versions["LoLItem"] = current_versions["perk"] = current_versions["perkstyle"] = current_versions["CherryAugment"] = URLPatch
                unmapped_keys["queue"], unmapped_keys["summonerIcon"], unmapped_keys["spell"], unmapped_keys["LoLChampion"], unmapped_keys["LoLItem"], unmapped_keys["perk"], unmapped_keys["perkstyle"], unmapped_keys["CherryAugment"] = set(), set(), set(), set(), set(), set(), set(), set()
                info_puuid: str = current_puuid_list[i]
                info_summonerName: str = current_summonerName_list[i]
                logPrint("[%d/%d]正在获取客户端内玩家%s的英雄联盟对局记录……\nGetting LoL match history of player %s in the client ..." %(i + 1, len(AllAccounts), info_summonerName, info_summonerName))
                LoLHistory_lcu: dict[str, Any] = {}
                LoLHistory_sgp: dict[str, Any] = {}
                if use_sgp:
                    LoLHistory_get, LoLHistory_sgp = await get_matchSummary_sgp(connection, sgpSession, info_puuid, "LoL", begin = 0, count = 1000, log = log)
                    for game in LoLHistory_sgp["games"]:
                        matchId: int = int(game["metadata"]["match_id"].split("_")[1])
                        if not matchId in LoLGame_summary_cache_sgp:
                            LoLGame_summary_cache_sgp[matchId] = game
                else:
                    LoLHistory_get, LoLHistory_lcu = await get_LoLHistory(connection, main_info_body["puuid"], log = log)
                if LoLHistory_get:
                    LoLGameCount: int = len(LoLHistory_sgp["games"]) if use_sgp else LoLHistory_lcu["games"]["gameCount"]
                    LoLGamePlayed: bool = LoLGameCount != 0 #标记该玩家是否进行过英雄联盟对局（Mark whether this summoner has played any LoL game）
                    if LoLGamePlayed:
                        logPrint(f"玩家{info_summonerName}共进行{LoLGameCount}场英雄联盟对局。\nPlayer {info_summonerName} has played {LoLGameCount} LoL matches.\n")
                    else:
                        logPrint(f"玩家{info_summonerName}从5月1日起就没有进行过任何英雄联盟对局。\nPlayer {info_summonerName} hasn't played any LoL game yet since May 1st.")
                    if use_sgp:
                        LoLHistory_df: pandas.DataFrame = (sort_LoLHistory_sgp(LoLHistory_sgp, info_puuid, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, useAllVersions = True, versionList = bigPatches, locale = language_code, current_versions = current_versions, unmapped_keys = unmapped_keys, session = session, log = log))[0]
                    else:
                        LoLHistory_df = (sort_LoLHistory(LoLHistory_lcu, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, useAllVersions = True, versionList = bigPatches, locale = language_code, current_versions = current_versions, unmapped_keys = unmapped_keys, session = session, log = log))[0]
                    LoLHistory_dfs.append(LoLHistory_df)
                    #LoLHistory_df.apply(lambda x: pandas.Series([-3], index = ["K/D/A"]))
                    if LoLGamePlayed:
                        logPrint(LoLHistory_df[:min(21, LoLGameCount + 1)], write_time = False)
            LoLHistory_df_all: pandas.DataFrame = pandas.concat([LoLHistory_dfs[0].iloc[:1]] + list(map(lambda x: x.iloc[1:], LoLHistory_dfs)), ignore_index = True) #需要注意数据框的中文表头占用了一行（Note that the Chinese header takes up a record）
            #对局序号去重（Drop duplicates from gameIds）
            gameIds_occurred: set[str | int] = {LoLHistory_df_all["gameId"][0]}
            lines_to_drop: list[int] = []
            for i in range(1, len(LoLHistory_df_all)):
                if LoLHistory_df_all["gameId"][i] in gameIds_occurred:
                    lines_to_drop.append(i)
                else:
                    gameIds_occurred.add(LoLHistory_df_all["gameId"][i])
            LoLHistory_df_all.drop(lines_to_drop, inplace = True)
            LoLHistory_df_all = LoLHistory_df_all.reset_index(drop = True)
            LoLHistory_df_all = pandas.concat([LoLHistory_df_all.iloc[:1], LoLHistory_df_all.iloc[1:].sort_values(by = "gameCreationDate", ascending = False)], ignore_index = True) #这里弃用了根据对局序号排序（Here gameId isn't used to sort the values）
            
            #下面获取最近一起玩过的英雄联盟玩家的信息（The following code captures the recently played LoL players' information）
            logPrint('请输入要查询的英雄联盟对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出英雄联盟对局查询请输入“0”：\nPlease enter the LoL match ID to check. Submit a list containing matchIDs to search in batch. Submit "3" to search the currently stored history in batch. Submit "0" to quit searching for LoL matches.')
            LoLGameIDs: list[int] = LoLHistory_df_all["gameId"][1:].to_list()
            while True:
                matchId_str: str = logInput()
                if matchId_str == "":
                    continue
                elif matchId_str == "0":
                    search_LoL = False
                    LoLMatchIDs = []
                    break
                else:
                    if matchId_str == "3":
                        begIndex: int = 0
                        endIndex: int = 0
                        logPrint("请设置需要查询的对局索引下界和上界，以空格为分隔符（输入空字符以默认查询近20场对局）：\nPlease set the begIndex and endIndex of the matches to be searched, split by space (Enter an empty string to search for the recent 20 matches):") #在13.13版本以前，腾讯代理的服务器只支持近20场对局查询（Before Patch 13.13, Tencent servers only provide search of the latest 20 matches）
                        while True:
                            gameIndex: str = logInput()
                            if gameIndex == "":
                                begIndex, endIndex = 0, 200 * len(AllAccounts)
                                break
                            elif gameIndex == "0":
                                break
                            else:
                                try:
                                    begIndex, endIndex = map(int, gameIndex.split())
                                except ValueError:
                                    logPrint("请以空格为分隔符输入对局索引的自然数类型的下界和上界！\nPlease enter the two nonnegative integers as the begIndex and endIndex of the matches split by space!")
                                    continue
                                else:
                                    break
                        if gameIndex == "0":
                            search_LoL = False
                            LoLMatchIDs = []
                            break
                        LoLMatchIDs = LoLGameIDs[begIndex:endIndex]
                    elif matchId_str == "scan":
                        LoLMatchIDs = LoLGameIDs + saved_LoLMatchIDs
                        if LoLMatchIDs == list():
                            logPrint("尚未保存过该玩家的数据！\nYou haven't saved this summoner's matches yet!\n")
                            break
                        else:
                            LoLMatchIDs = sorted(set(LoLMatchIDs), reverse = True)
                            logPrint("检测到%d场对局。是否继续？（输入任意键以重新输入要查询的对局序号，否则重新获取这些对局的数据）\nDetected %d matches. Continue? (Input any nonempty string to return to the last step of inputting the matchId, or null to recapture those matches' data)" %(len(LoLMatchIDs), len(LoLMatchIDs)))
                            recapture_str: str = logInput()
                            recapture: bool = bool(recapture_str)
                            if recapture:
                                LoLMatchIDs = [] #如果没有这句语句，那么当重新输入对局序号列表时，从本地文件中检测到的对局数量相比上次检测数的基础上会多出本地文件中包含的对局的数量（Without this assignment, when reinputting the matchId list, the number of matches detected from the local files will become more than that of the last time's check）
                                logPrint('请输入要查询的英雄联盟对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出英雄联盟对局查询请输入“0”：\nPlease enter the LoL match ID to check. Submit a list containing matchIDs to search in batch. Submit "3" to search the currently stored history in batch. Submit "0" to quit searching for LoL matches.')
                                continue
                            #在沿用查战绩脚本时，后续对局记录重新生成的代码不再需要了。因为这只是查召唤师信息的脚本，不是查对局记录的脚本（When inheritting code from Customized Program 5, the following code to regenerate match history is no longer needed. That's because this program is just designed to search for recently played summoners, rather than sort out match history）
                    else:
                        try:
                            tmp = eval(matchId_str)
                        except (SyntaxError, NameError):
                            logPrint("您的输入存在语法错误。请重新输入！\nSyntax ERROR detected in this input! Please try again!")
                            continue
                        else:
                            LoLMatchIDs = []
                            if isinstance(tmp, int):
                                LoLMatchIDs.append(tmp)
                            elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int), tmp)):
                                LoLMatchIDs += tmp
                            else:
                                logPrint("数据类型不符。请重新输入！\nData type not matched! Please try again!")
                                continue
                            if len(LoLMatchIDs) == 0:
                                logPrint("您输入的对局序号集不合法！请重新输入。\nThe matchId set you've input is illegal! Please try again.")
                                continue
                    break
        if len(LoLMatchIDs) > 0:
            #开始获取各对局内的玩家信息。数据结构参考/lol-match-history/v1/recently-played-summoners（Begin to capture the players' information in each match. The data structure refers to "/lol-match-history/v1/recently-played-summoners"）
            queues = queues_initial.copy()
            spells = spells_initial.copy()
            LoLChampions = LoLChampions_initial.copy()
            LoLItems = LoLItems_initial.copy()
            summonerIcons = summonerIcons_initial.copy()
            perks = perks_initial.copy()
            perkstyles = perkstyles_initial.copy()
            CherryAugments = CherryAugments_initial.copy()
            current_versions["queue"] = current_versions["summonerIcon"] = current_versions["spell"] = current_versions["LoLChampion"] = current_versions["LoLItem"] = current_versions["perk"] = current_versions["perkstyle"] = current_versions["CherryAugment"] = URLPatch
            unmapped_keys["queue"], unmapped_keys["summonerIcon"], unmapped_keys["spell"], unmapped_keys["LoLChampion"], unmapped_keys["LoLItem"], unmapped_keys["perk"], unmapped_keys["perkstyle"], unmapped_keys["CherryAugment"] = set(), set(), set(), set(), set(), set(), set(), set()
            if use_sgp:
                recent_LoLPlayer_df: pandas.DataFrame = await sort_LoLGame_stats_sgp(connection, sgpSession, LoLMatchIDs, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, puuid = current_puuid_list, excluded_reserve = args.reserve, save_self = args.save_self, save_other = True, save_bot = False, useAllVersions = True, versionList = bigPatches, locale = language_code, current_versions = current_versions, unmapped_keys = unmapped_keys, LoLGame_summary_cache = LoLGame_summary_cache_sgp, session = session, log = log)
            else:
                recent_LoLPlayer_df = await sort_LoLGame_stats(connection, LoLMatchIDs, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, puuid = current_puuid_list, excluded_reserve = args.reserve, save_self = args.save_self, save_other = True, save_bot = False, useAllVersions = True, versionList = bigPatches, locale = language_code, current_versions = current_versions, unmapped_keys = unmapped_keys, LoLGame_summary_cache = LoLGame_summary_cache_lcu, session = session, log = log)
            LoLGamePlayed: bool = len(recent_LoLPlayer_df) > 1
        else:
            if use_sgp:
                LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_sgp_header.keys())
                recent_LoLPlayer_statistics_output_order: list[int] = [0, 112, 148, 131, 132, 146, 128, 147, 68, 21, 16, 13, 25, 26, 11, 18, 22, 14, 29, 15, 20, 30, 19, 24, 227, 218, 628, 184, 54, 625, 626, 96, 133, 125, 82, 152, 135, 52, 51, 55, 223, 224, 186, 187, 188, 189, 190, 191, 192, 221, 200, 212, 201, 213, 202, 214, 203, 215, 204, 216, 205, 217, 95, 64, 45, 229, 230, 231, 234, 235, 98, 94, 99, 49, 72, 71, 74, 73, 66, 167, 129, 113, 174, 153, 164, 157, 115, 102, 169, 156, 114, 101, 168, 97, 61, 60, 58, 59, 161, 162, 166, 158, 159, 116, 103, 170, 62, 176, 179, 178, 136, 177, 65, 79, 232, 80, 233, 93, 57, 163, 105, 155, 160, 171, 172, 83, 84, 106, 108, 173, 85, 107, 67, 47, 109, 110, 100, 48, 56, 78, 130, 127, 111, 43, 44, 104, 69, 70, 175, 63, 46, 81, 154, 165, 137, 139, 141, 142, 228, 144, 145, 602, 616, 608, 604, 609, 605, 610, 606, 611, 607, 620, 618, 621, 619, 598, 596, 597, 50, 149, 150, 75, 76, 77, 182, 181, 180, 236, 117, 143, 672, 658, 643, 728, 674, 671, 675, 647, 660, 715, 692, 687, 721, 701, 712, 705, 689, 678, 717, 704, 688, 677, 716, 673, 655, 654, 652, 653, 709, 710, 714, 706, 707, 690, 679, 718, 656, 723, 726, 725, 694, 724, 659, 665, 666, 670, 651, 711, 681, 703, 708, 729, 719, 720, 668, 669, 682, 683, 661, 645, 684, 685, 676, 646, 650, 664, 693, 691, 686, 641, 642, 680, 662, 663, 722, 657, 644, 667, 702, 713, 695, 696, 697, 698, 727, 699, 700, 802, 750, 749, 773, 759, 744, 830, 831, 833, 775, 772, 776, 748, 761, 817, 793, 788, 823, 803, 814, 807, 790, 779, 819, 806, 789, 778, 818, 774, 756, 755, 753, 754, 811, 812, 816, 808, 809, 791, 780, 820, 757, 825, 828, 827, 795, 826, 760, 766, 767, 834, 771, 752, 813, 782, 810, 805, 832, 821, 822, 769, 770, 762, 746, 785, 786, 783, 784, 777, 747, 751, 765, 794, 792, 787, 742, 743, 781, 763, 764, 824, 758, 745, 768, 804, 815, 796, 797, 798, 799, 829, 800, 801, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 381, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 382, 283, 284, 285, 383, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 384, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 385, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 237]
                recent_LoLPlayer_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: [LoLGame_summary_sgp_header[LoLGame_summary_header_keys[i]]] for i in recent_LoLPlayer_statistics_output_order}
            else:
                LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
                recent_LoLPlayer_statistics_output_order: list[int] = [0, 16, 26, 20, 27, 25, 24, 31, 5, 3, 13, 4, 11, 6, 14, 10, 15, 9, 42, 214, 231, 35, 36, 226, 227, 229, 230, 46, 38, 39, 160, 161, 162, 163, 164, 165, 166, 215, 196, 208, 197, 209, 198, 210, 199, 211, 200, 212, 201, 213, 74, 51, 43, 217, 218, 219, 222, 223, 47, 144, 145, 76, 73, 77, 55, 54, 59, 58, 57, 56, 52, 148, 133, 86, 153, 138, 146, 140, 114, 80, 150, 139, 113, 79, 149, 75, 49, 48, 142, 147, 141, 115, 81, 151, 50, 154, 157, 156, 135, 155, 63, 220, 64, 221, 143, 82, 84, 83, 152, 65, 78, 192, 194, 180, 174, 181, 175, 182, 176, 183, 177, 184, 178, 185, 179, 44, 53, 137, 45, 60, 61, 62, 158, 224, 136, 243, 237, 232, 290, 233, 277, 245, 242, 246, 238, 280, 269, 255, 285, 271, 278, 273, 257, 249, 282, 272, 256, 248, 281, 244, 235, 234, 275, 279, 274, 258, 250, 283, 236, 286, 289, 288, 270, 287, 239, 240, 276, 251, 253, 252, 291, 284, 241, 247, 293, 304, 298, 292, 351, 352, 354, 294, 338, 306, 303, 307, 299, 341, 330, 316, 346, 332, 339, 334, 318, 310, 343, 333, 317, 309, 342, 305, 296, 295, 336, 340, 335, 319, 311, 344, 297, 347, 350, 349, 331, 348, 300, 301, 355, 337, 312, 313, 314, 353, 345, 302, 308]
                recent_LoLPlayer_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: [LoLGame_summary_header[LoLGame_summary_header_keys[i]]] for i in recent_LoLPlayer_statistics_output_order}
            recent_LoLPlayer_df: pandas.DataFrame = pandas.DataFrame(data = recent_LoLPlayer_data_organized)
            LoLGamePlayed = False

        #下面获取最近一起玩过的云顶之弈玩家的信息（The following code captures the recently played TFT players' information）
        logPrint("是否查询云顶之弈对局记录？（输入任意键查询，否则不查询）\nSearch TFT matches? (Input anything to search or null to export data or switch for another summoner)")
        search_TFT_str: str = logInput()
        search_TFT: bool = bool(search_TFT_str)
        TFTMatchIDs: list[int] = []
        if search_TFT:
            TFTHistory_dfs: list[pandas.DataFrame] = []
            TFTHistory_dict: dict[int, dict[str, Any]] = {}
            for i in range(len(AllAccounts)):
                queues = queues_initial.copy()
                TFTAugments = TFTAugments_initial.copy()
                TFTChampions = TFTChampions_initial.copy()
                TFTItems = TFTItems_initial.copy()
                TFTCompanions = TFTCompanions_initial.copy()
                TFTTraits = TFTTraits_initial.copy()
                current_versions["queue"] = current_versions["TFTAugment"] = current_versions["TFTChampion"] = current_versions["TFTItem"] = current_versions["TFTCompanion"] = current_versions["TFTTrait"] = URLPatch
                unmapped_keys["queue"], unmapped_keys["TFTAugment"], unmapped_keys["TFTChampion"], unmapped_keys["TFTItem"], unmapped_keys["TFTCompanion"], unmapped_keys["TFTTrait"] = set(), set(), set(), set(), set(), set()
                main_info_body: dict[str, Any] = AllAccounts[i]
                info_puuid: str = current_puuid_list[i]
                info_summonerName: str = current_summonerName_list[i]
                logPrint("[%d/%d]正在获取客户端内玩家%s的云顶之弈对局记录……\nGetting TFT match history of player %s in the client ..." %(i + 1, len(AllAccounts), info_summonerName, info_summonerName))
                TFTHistory_get, TFTHistory = await get_matchSummary_sgp(connection, sgpSession, info_puuid, "TFT", begin = 0, count = 1000, log = log) #这里之所以把count参数写出来，是因为考虑到后续可能随时要调整这个参数。毕竟1000场数据是非常庞大的（Here the reason I write this `count` parameter is considering its value might be adjusted at some time later. After all, data of 1000 matches can be really big）
                for game in TFTHistory["games"]:
                    matchId: int = int(game["metadata"]["match_id"].split("_")[1])
                    if not matchId in TFTGame_summary_cache_sgp: #由于云顶之弈的对局记录包含所有玩家的信息，所以如果多个玩家的对局记录包含同一场对局，则这些对局的信息一定是相同的（Because TFT match history includes all players' information, if a match is included in multiple players' match histories, then information of the matches recorded in different players' match histories must be the same）
                        TFTGame_summary_cache_sgp[matchId] = game
                if TFTHistory_get:
                    TFTGamePlayed: bool = (TFTGameCount := len(TFTHistory["games"])) > 0 #标记该玩家是否进行过云顶之弈对局（Mark whether this summoner has played any TFT game）
                    if TFTGamePlayed:
                        logPrint(f"玩家{info_summonerName}共进行{TFTGameCount}场云顶之弈对局。\nPlayer {info_summonerName} has played {TFTGameCount} TFT matches.\n")
                    else:
                        logPrint(f"玩家{info_summonerName}从5月1日起就没有进行过任何云顶之弈对局。\nPlayer {info_summonerName} hasn't played any TFT game yet since May 1st.")
                    for game in TFTHistory["games"]:
                        match_id: int = int(game["metadata"]["match_id"].split("_")[-1])
                        if not match_id in TFTHistory_dict: #由于云顶之弈的对局记录包含所有玩家的信息，所以如果多个玩家的对局记录包含同一场对局，则这些对局的信息一定是相同的（Because TFT match history includes all players' information, if a match is included in multiple players' match histories, then information of the matches recorded in different players' match histories must be the same）
                            TFTHistory_dict[match_id] = game
                    TFTHistory_df: pandas.DataFrame = (await sort_TFTHistory(connection, TFTHistory, main_info_body["puuid"], queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, useAllVersions = True, versionList = bigPatches, locale = language_code, current_versions = current_versions, unmapped_keys = unmapped_keys, session = session, useInfoDict = True, infos = infos, log = log))[0]
                    TFTHistory_dfs.append(TFTHistory_df)
                    if TFTGamePlayed:
                        logPrint(TFTHistory_df[:min(21, TFTGameCount + 1)], write_time = False)
            #由于云顶之弈的对局记录包含所有玩家的信息，所以这里考虑先整合所有账号的对局记录，再对总对局记录进行整理。如果先整理再整合，后续排序时玩家顺序的信息会丢失，因为在这种情形下根据对局序号排序，而数据框中不包含玩家序号键，无法按照玩家序号进行升序排列（Because TFT match history includes all players' information, here the program first merges all accounts' match history, and then aggregates match history. Otherwise, if the program first organize the match history respectively and then merge the result dataframe, the participantId order may be lost during the subsequent ordering, for gameId is taken to arrange the aggregate dataframe, but the key `participantId` isn't in the dataframe, and therefore the dataframe can't be arranged in the ascending order of participantId）
            # TFTHistory_all: dict[str, str | list[dict[str, Any]]] = {"active_puuid": "", "games": list(map(lambda x: TFTHistory_dict[x], TFTGameIDs))}
            #构建云顶之弈对局记录数据框（Construct TFT match history dataframe）
            TFTHistory_df_all: pandas.DataFrame = pandas.concat([TFTHistory_dfs[0].iloc[:1]] + list(map(lambda x: x.iloc[1:], TFTHistory_dfs)), ignore_index = True) #需要注意数据框的中文表头占用了一行（Note that the Chinese header takes up a record）
            gameIds_occurred: set[str | int] = {TFTHistory_df_all["game_id"][0]}
            lines_to_drop: list[int] = []
            for i in range(1, len(TFTHistory_df_all)):
                if TFTHistory_df_all["game_id"][i] in gameIds_occurred:
                    lines_to_drop.append(i)
                else:
                    gameIds_occurred.add(TFTHistory_df_all["game_id"][i])
            TFTHistory_df_all.drop(lines_to_drop, inplace = True)
            TFTHistory_df_all = TFTHistory_df_all.reset_index(drop = True)
            TFTHistory_df_all = pandas.concat([TFTHistory_df_all.iloc[:1], TFTHistory_df_all.iloc[1:].sort_values(by = "gameCreationDate", ascending = False)], ignore_index = True) #这里弃用了根据对局序号排序（Here gameId isn't used to sort the values）
            
            #下面获取最近一起玩过的云顶之弈玩家的信息（The following code captures the recently played TFT players' information）
            logPrint('请输入要查询的云顶之弈对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出云顶之弈对局查询请输入“0”：\nPlease enter the TFT match ID to check. Submit a list containing matchIDs to search in batch. Submit "3" to search the currently stored history in batch. Submit "0" to quit searching for TFT matches.')
            TFTGameIDs: list[int] = TFTHistory_df_all["game_id"][1:].to_list()
            while True:
                matchId_str: str = logInput()
                if matchId_str == "":
                    continue
                elif matchId_str == "0":
                    search_TFT = False
                    TFTMatchIDs = []
                    break
                else:
                    if matchId_str == "3":
                        begIndex: int = 0
                        endIndex: int = 10000
                        logPrint("请设置需要查询的对局索引下界和上界，以空格为分隔符（输入空字符以默认查询近20场对局）：\nPlease set the begIndex and endIndex of the matches to be searched, split by space (Enter an empty string to search for the recent 20 matches):") #在13.13版本以前，腾讯代理的服务器只支持近20场对局查询（Before Patch 13.13, Tencent servers only provide search of the latest 20 matches）
                        while True:
                            gameIndex: str = logInput()
                            if gameIndex == "":
                                begIndex, endIndex = 0, 200 * len(AllAccounts)
                                break
                            elif gameIndex == "0":
                                break
                            else:
                                try:
                                    begIndex, endIndex = map(int, gameIndex.split())
                                except ValueError:
                                    logPrint("请以空格为分隔符输入对局索引的自然数类型的下界和上界！\nPlease enter the two nonnegative integers as the begIndex and endIndex of the matches split by space!")
                                    continue
                                else:
                                    break
                        if gameIndex == "0":
                            search_TFT = False
                            TFTMatchIDs = []
                            break
                        TFTMatchIDs = TFTGameIDs[begIndex:endIndex]
                    elif matchId_str == "scan":
                        TFTMatchIDs = TFTGameIDs + saved_TFTMatchIDs
                        if TFTMatchIDs == list():
                            logPrint("尚未保存过该玩家的数据！\nYou haven't saved this summoner's matches yet!\n")
                            break
                        else:
                            TFTMatchIDs = sorted(set(TFTMatchIDs), reverse = True)
                            logPrint("检测到%d场对局。是否继续？（输入任意键以重新输入要查询的对局序号，否则重新获取这些对局的数据）\nDetected %d matches. Continue? (Input any nonempty string to return to the last step of inputting the matchId, or null to recapture those matches' data)" %(len(TFTMatchIDs), len(TFTMatchIDs)))
                            recapture_str: str = logInput()
                            recapture: bool = bool(recapture_str)
                            if recapture:
                                TFTMatchIDs = [] #如果没有这句语句，那么当重新输入对局序号列表时，从本地文件中检测到的对局数量相比上次检测数的基础上会多出本地文件中包含的对局的数量（Without this assignment, when reinputting the matchId list, the number of matches detected from the local files will become more than that of the last time's check）
                                logPrint('请输入要查询的云顶之弈对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出云顶之弈对局查询请输入“0”：\nPlease enter the TFT match ID to check. Submit a list containing matchIDs to search in batch. Submit "3" to search the currently stored history in batch. Submit "0" to quit searching for TFT matches.')
                                continue
                            #在沿用查战绩脚本时，后续对局记录重新生成的代码不再需要了。因为这只是查召唤师信息的脚本，不是查对局记录的脚本（When inheritting code from Customized Program 5, the following code to regenerate match history is no longer needed. That's because this program is just designed to search for recently played summoners, rather than organize match history）
                    else:
                        try:
                            tmp = eval(matchId_str)
                        except (SyntaxError, NameError):
                            logPrint("您的输入存在语法错误。请重新输入！\nSyntax ERROR detected in this input! Please try again!")
                            continue
                        else:
                            TFTMatchIDs = []
                            if isinstance(tmp, int):
                                TFTMatchIDs.append(tmp)
                            elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int), tmp)):
                                TFTMatchIDs += tmp
                            else:
                                logPrint("数据类型不符。请重新输入！\nData type not matched! Please try again!")
                                continue
                            if len(TFTMatchIDs) == 0:
                                logPrint("您输入的对局序号集不合法！请重新输入。\nThe matchId set you've input is illegal! Please try again.")
                                continue
                    break
        if len(TFTMatchIDs) > 0:
            #开始获取各对局内的玩家信息（Begin to capture the players' information in each match）
            queues = queues_initial.copy()
            TFTAugments = TFTAugments_initial.copy()
            TFTChampions = TFTChampions_initial.copy()
            TFTItems = TFTItems_initial.copy()
            TFTCompanions = TFTCompanions_initial.copy()
            TFTTraits = TFTTraits_initial.copy()
            current_versions["queue"] = current_versions["TFTAugment"] = current_versions["TFTChampion"] = current_versions["TFTItem"] = current_versions["TFTCompanion"] = current_versions["TFTTrait"] = URLPatch
            unmapped_keys["queue"], unmapped_keys["TFTAugment"], unmapped_keys["TFTChampion"], unmapped_keys["TFTItem"], unmapped_keys["TFTCompanion"], unmapped_keys["TFTTrait"] = set(), set(), set(), set(), set(), set()
            recent_TFTPlayer_df: pandas.DataFrame = await sort_TFTGame_stats(connection, sgpSession, TFTMatchIDs, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, puuid = current_puuid_list, excluded_reserve = args.reserve, save_self = args.save_self, save_other = True, save_bot = False, useAllVersions = True, versionList = bigPatches, locale = language_code, current_versions = current_versions, unmapped_keys = unmapped_keys, TFTGame_summary_cache = TFTGame_summary_cache_sgp, useInfoDict = True, infos = infos, log = log)
            TFTGamePlayed: bool = len(recent_TFTPlayer_df) > 1
        else:
            TFTHistory_header_keys: list[str] = list(TFTHistory_header.keys())
            recent_TFTPlayer_statistics_output_order: list[int] = [0, 19, 46, 47, 43, 5, 14, 15, 16, 6, 10, 18, 7, 13, 11, 12, 307, 305, 40, 55, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 150, 148, 149, 203, 206, 209, 155, 153, 154, 212, 215, 218, 160, 158, 159, 221, 224, 227, 165, 163, 164, 230, 233, 236, 170, 168, 169, 239, 242, 245, 175, 173, 174, 248, 251, 254, 180, 178, 179, 257, 260, 263, 185, 183, 184, 266, 269, 272, 190, 188, 189, 275, 278, 281, 195, 193, 194, 284, 287, 290, 200, 198, 199, 293, 296, 299, 61, 57, 58, 59, 60, 68, 64, 65, 66, 67, 75, 71, 72, 73, 74, 82, 78, 79, 80, 81, 89, 85, 86, 87, 88, 96, 92, 93, 94, 95, 103, 99, 100, 101, 102, 110, 106, 107, 108, 109, 117, 113, 114, 115, 116, 124, 120, 121, 122, 123, 131, 127, 128, 129, 130, 138, 134, 135, 136, 137, 145, 141, 142, 143, 144]
            recent_TFTPlayer_data_organized: dict[str, list[Any]] = {TFTHistory_header_keys[i]: [TFTHistory_header[TFTHistory_header_keys[i]]] for i in recent_TFTPlayer_statistics_output_order}
            recent_TFTPlayer_df: pandas.DataFrame = pandas.DataFrame(data = recent_TFTPlayer_data_organized)
            TFTGamePlayed = False
        
        if search_LoL and LoLGamePlayed or search_TFT and TFTGamePlayed:
            logPrint("近期一起玩过的玩家数据已加载完成！\nRecently played summoner data loaded successfully!")
            while True:
                update: bool = await detect_mode(connection, search_LoL, search_TFT, recent_LoLPlayer_df, recent_TFTPlayer_df, language_code, infos)
                if update:
                    break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    global sgpSession, log, logInput, logPrint
    log_folder: str = "日志（Logs）/Customized Program 11 - Count Recently Played Summoners"
    os.makedirs(log_folder, exist_ok = True)
    currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log = LogManager(os.path.join(log_folder, currentTime + ".log"), mode = "a+", encoding = "utf-8")
    logInput = log.logInput
    logPrint = log.logPrint
    sgpSession.setLog(log)
    await sgpSession.init(connection)
    await print_summoner_info(connection)
    await save_platform_info(connection)
    await prepare_lcu_plugins(connection)
    await search_recent_players(connection)
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
