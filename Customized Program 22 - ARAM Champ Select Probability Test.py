from lcu_driver import Connector
from lcu_driver.connection import Connection
import argparse, keyboard, pandas, time
from typing_extensions import Any, Literal, Optional
from src.core.config.const import GLOBAL_RESPONSE_LAG
from src.core.dataframes.champions import sort_inventory_champions
from src.core.dataframes.gameflow import get_champSelect_player, extract_champSelect_player, update_champ_select_session
from src.core.dataframes.gameMode import check_available_queue
from src.utils.summoner import print_summoner_info, get_info, get_info_name
from src.utils.logger import LogManager
from src.utils.format import format_df

parser = argparse.ArgumentParser()
parser.add_argument("-q", "--queueId", help = "通过队列序号指定要创建的自定义房间。必须是全随机模式（Specify the custom lobby to create by queueId. Must be all-random）", action = "store", type = int, default = 0)
# parser.add_argument("-c", "--is-custom", help = "是否创建自定义房间（Whether to create a custom lobby）", action = "store_true")
parser.add_argument("-n", "--lobby-name", help = "指定一个自定义房间名称（Specify the lobby name）", action = "store", type = str, default = None)
parser.add_argument("-s", "--lobby-password", help = "指定自定义房间的密码（Specify the lobby password）", action = "store", type = str, default = "")
parser.add_argument("-m", "--aram-map-mutator", help = "指定一个大乱斗地图（Specify the map of ARAM）", action = "store", type = str, choices = ["NONE", "MapSkin_Map12_Bloom", "MapSkin_HA_Bilgewater", "MapSkin_HA_Crepe"], default = "MapSkin_HA_Bilgewater")
parser.add_argument("-sp", "--spectator-policy", help = "指定观战策略（Specify a spectate policy）", action = "store", type = str, choices = ["LobbyAllowed", "FriendsAllowed", "AllAllowed", "NotAllowed"], default = "AllAllowed")
parser.add_argument("-ts", "--team-size", help = "指定队伍规模（Specify the team size）", action = "store", type = int, default = 5)
parser.add_argument("--enable-spectator-delay", help = "是否启用观战延迟（Whether to enable spectator delay）", action = "store_true")
parser.add_argument("--hide-publicly", help = "是否隐藏自定义房间（Whether to hide the custom lobby from being seen publicly）", action = "store_true")
args = parser.parse_args()

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/07/01
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

current_summoner: dict[str, Any] = {}
LoLChampions: dict[int, dict[str, Any]] = {}
LoLChampion_df: pandas.DataFrame = pandas.DataFrame()
gameQueues: dict[int, dict[str, Any]] = {}
log: LogManager = LogManager()

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 定义全局变量（Define global variables）
#-----------------------------------------------------------------------------
async def prepare_data_resources(connection: Connection) -> None:
    '''
    准备全局数据资源。<br>Prepare global data resources.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    global current_summoner, LoLChampions, LoLChampion_df, gameQueues
    current_summoner = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    LoLChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %(current_summoner["summonerId"]))).json()
    LoLChampions = {champion["id"]: champion for champion in LoLChampions_source}
    recommended_position_for_champion: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    logPrint("正在整理英雄数据……\nOrganizing champion data ...")
    LoLChampion_df = sort_inventory_champions(LoLChampions, recommended_position_for_champion)[0]
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues = {queue["id"]: queue for queue in gameQueues_source}

#-----------------------------------------------------------------------------
# 创建房间（Create a lobby）
#-----------------------------------------------------------------------------
async def create_lobby(connection: Connection, queueId: int = 0, isCustom: bool = True, lobbyName: Optional[str] = None, lobbyPassword: str = "", mapId: int = 11, aramMapMutator: Literal["NONE", "MapSkin_Map12_Bloom", "MapSkin_HA_Bilgewater", "MapSkin_HA_Crepe"] = "MapSkin_HA_Bilgewater", gameMode: str = "PRACTICETOOL", mutatorId: int = 1, spectatorPolicy: Literal["LobbyAllowed", "FriendsAllowed", "AllAllowed", "NotAllowed"] = "AllAllowed", teamSize: int = 5, maxPlayerCount: int = 0, gameServerRegion: str = "", spectatorDelayEnabled: bool = False, hidePublicly: bool = False) -> dict[str, Any]:
    '''
    对房间创建接口的封装，支持所有可用参数。<br>An encapsulation of the lobby creation endpoint, which supports all available parameters.
    
    :param queueId: 队列序号，默认取值为0，通过`GET /lol-game-queues/v1/queues`接口获取。<br>QueueId, 0 by default, obtained through `GET /lol-game-queues/v1/queues` endpoint.
    :type queueId: int
    :param lobbyName: 对局名，默认为空，此时采用客户端语言的默认配置。<br>Lobby name, an empty string by default, when client's default value if an empty string is passed.
    :type lobbyName: str
    :param lobbyPassword: 密码，默认为空。<br>Password, an empty string by default.
    :type lobbyPassword: str
    :param aramMapMutator: 极地大乱斗地图，默认为屠夫之桥。有以下取值：<br>ARAM map, Butcher's Bridge by default. It may be one of the following values:
        
        - NONE: 嚎哭深渊（Howling Abyss）
        - MapSkin_HA_Crepe: 进步之桥（Bridge of Progress）
        - MapSkin_Map12_Bloom: 莲华栈桥（Koeshin's Crossing）
        - MapSkin_HA_Bilgewater: 屠夫之桥（Butcher's Bridge）
    :type aramMapMutator: str
    :param spectatorPolicy: 观战策略，默认为AllAllowed，固定取值为LobbyAllowed、FriendsAllowed、AllAllowed和NotAllowed（Spectator policy, "AllAllowed" by default, which has fixed values: "LobbyAllowed" "FriendsAllowed" "AllAllowed" and "NotAllowed"）
    :type spectatorPolicy: str
    :param teamSize: 队伍规模，默认为5（Team size, 5 by default）
    :type teamSize: int
    :param spectatorDelayEnabled: 观战延迟，默认为假。指定为真时为添加延迟（Spectator delay, `False` by default. If it's specified as `True`, delay will be added）
    :type spectatorDelayEnabled: bool
    :param hidePublicly: 从公开的房间列表中隐藏，默认为假。指定为真时隐藏（Hide from public lobby list, `False` by default. If it's specified as `True`, the lobby will be hidden from other players）
    :return: 建房请求的响应主体。<br>The response body of the request to create a lobby.
    :rtype: dict[str, Any]
    '''
    current_summoner: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    custom_game_setup_name_default_dict: dict[str, str] = {"ar_AE": "مباراة {{summonerName}}", "cs_CZ": "Hra uživatele {{summonerName}}", "el_GR": "Παιχνίδι του {{summonerName}}", "pl_PL": "Rozgrywka gracza {{summonerName}}", "ro_RO": "Jocul lui {{summonerName}}", "hu_HU": "{{summonerName}} játéka", "en_GB": "{{summonerName}}'s Game", "de_DE": "Spiel von {{summonerName}}", "es_ES": "Partida de {{summonerName}}", "it_IT": "Partita di {{summonerName}}", "fr_FR": "Partie de {{summonerName}}", "ja_JP": "{{summonerName}}の試合", "ko_KR": "{{summonerName}} 님의 게임", "es_MX": "Partida de {{summonerName}}", "es_AR": "Partida de {{summonerName}}", "pt_BR": "Partida de {{summonerName}}", "en_US": "{{summonerName}}'s Game", "en_AU": "{{summonerName}}'s Game", "ru_RU": "Игра {{summonerName}}", "tr_TR": "{{summonerName}} oyunu", "en_PH": "{{summonerName}}'s Game", "en_SG": "{{summonerName}}'s Game", "th_TH": "เกมของ {{summonerName}}", "vi_VN": "Trận của {{summonerName}}", "id_ID": "Game {{summonerName}}", "zh_MY": "{{summonerName}} 的房间", "zh_CN": "{{summonerName}}的对局", "zh_TW": "{{summonerName}} 的房間"} #来自（From）：plugins/rcp-fe-lol-parties/global/{locale}/trans.json
    if lobbyName == None:
        lobbyName = custom_game_setup_name_default_dict.get(region_locale["locale"], "{{summonerName}}的对局").replace("{{summonerName}}", current_summoner["gameName"])
    custom = {
        "queueId": queueId,
        "isCustom": isCustom,
        "customGameLobby": {
            "lobbyName": lobbyName,
            "lobbyPassword": lobbyPassword,
            "configuration": {
                "mapId": mapId,
                "aramMapMutator": aramMapMutator,
                "gameMode": gameMode,
                "gameTypeConfig": {
                    "id": mutatorId,
                },
                "spectatorPolicy": spectatorPolicy,
                "teamSize": teamSize,
                "maxPlayerCount": maxPlayerCount,
                "gameServerRegion": gameServerRegion,
                "spectatorDelayEnabled": spectatorDelayEnabled,
                "hidePublicly": hidePublicly
            }
        }
    }
    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase == "ChampSelect":
        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/quit")).json()
        logPrint(response)
    #基于是否已在房间中，使用不同的接口（Different endpoints are used based on whether the user is already in a lobby）
    lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    if "gameConfig" in lobby_information and not (queueId in gameQueues and gameQueues[queueId]["isCustom"]):
        response: Optional[dict[str, Any]] = await (await connection.request("PUT", "/lol-lobby/v1/parties/queue", data = str(queueId))).json()
    else:
        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)).json()
    return response

#-----------------------------------------------------------------------------
# 秒选英雄（Instantly pick and lock a champion）
#-----------------------------------------------------------------------------
async def secLock(connection: Connection, championId: int = 11, action_type: str = "pick", completed: bool = True) -> None:
    '''
    秒选一名英雄。<br>Immediately lock a champion.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param championId: 英雄序号。<br>ChampionId.
    :type championId: int
    :param action_type: 行为类型。有以下可用取值。<br>Action type, which has the following available values:
    
        - pick: 选用
        - ban: 禁用
        - vote: 投票
        
        另外还有一个取值，但玩家无法指定为该值。<br>There's another value which can't be specified by the player.
        - ten_bans_reveal: 禁用揭晓
    :type action_type: Literal["pick", "ban", "vote"]
    :param completed: 是否完成动作。相当于在选择英雄后，是否按下“锁定”按钮。<br>Whether to complete this action. That is, whether to press "Lock" button after selecting a champion.
    :type completed: bool
    '''
    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    localPlayerCellId: int = champ_select_session["localPlayerCellId"]
    logPrint(f"用户槽位序号（Local player cellId）：{localPlayerCellId}")
    actions: dict[tuple[int, str], list[dict[str, Any]]] = {(action["id"], action["type"]): action for stage in champ_select_session["actions"] for action in stage}
    actionId: int = actions[(localPlayerCellId, "pick")]["id"]
    logPrint(f"用户行为序号（Local player actionId）：{actionId}")
    body: dict[str, Any] = {
        "id": actionId,
        "actorCellId": localPlayerCellId,
        "championId": championId,
        "type": action_type,
        "completed": completed,
        "isAllyAction": True,
        "isInProgress": True,
        "pickTurn": 0
    }
    response: Optional[dict[str, Any]] = await (await connection.request("PATCH", f"/lol-champ-select/v1/session/actions/{actionId}", data = body)).json()
    logPrint(response)

#-----------------------------------------------------------------------------
# 测试选到候选英雄的概率（Probability test on candidate champions）
#-----------------------------------------------------------------------------
def sort_champion_frequency_table(champion_frequency_dict: dict[int, int]): #将英雄频数数据格式化为一个表格（Format the champion frequency distribution data into a table）
    '''
    将某个随机过程中各英雄的出现次数整理成一个数据框/表格。<br>Sort occurrences of champions during a random process into a dataframe / table.
    
    :param champion_frequency_dict: 英雄出现次数的频数统计字典。<br>The champion occurrence frequency distribution dictionary.
    :type champion_frequency_dict: dict[int, int]
    :return: 英雄出现次数的数据框，按英雄出现次数降序排列。<br>A dataframe that stores the number of times that each champion occurred and follows the descending order of occurrence.
    :rtype: pandas.DataFrame
    '''
    champion_frequency_header: dict[str, str] = {"championId": "英雄序号", "name": "称号", "title": "名称", "alias": "代号", "occurrence": "出现次数"}
    champion_frequency_header_keys: list[str] = list(champion_frequency_header.keys())
    champion_frequency_data: dict[str, list[Any]] = {key: [] for key in champion_frequency_header_keys}
    for championId in champion_frequency_dict:
        occurrence = champion_frequency_dict[championId]
        for i in range(len(champion_frequency_header_keys)):
            key: str = champion_frequency_header_keys[i]
            if championId in LoLChampions:
                if i == 0: #英雄序号（`championId`）
                    to_append: Any = championId
                elif i <= 3:
                    to_append = LoLChampions[championId][key]
                else: #出现次数（`occurrence`）
                    to_append = occurrence
                champion_frequency_data[key].append(to_append)
            elif championId == -3: #仅限斗魂竞技场（Only for Arena）
                champion_frequency_data["championId"].append(-3)
                champion_frequency_data["name"].append("勇敢举动")
                champion_frequency_data["title"].append("")
                champion_frequency_data["alias"].append("BRAVERY")
                champion_frequency_data["occurrence"].append(occurrence)
            else:
                print(f"未找到序号为{championId}的英雄。\nThe champion with id {championId} is not found.")
    champion_frequency_statistics_output_order: list[int] = list(range(len(champion_frequency_header_keys)))
    champion_frequency_data_organized: dict[str, list[Any]] = {champion_frequency_header_keys[i]: champion_frequency_data[champion_frequency_header_keys[i]] for i in champion_frequency_statistics_output_order}
    champion_frequency_df: pandas.DataFrame = pandas.DataFrame(champion_frequency_data_organized)
    champion_frequency_df = champion_frequency_df.sort_values(by = "occurrence", ascending = False, ignore_index = True)
    champion_frequency_df = pandas.concat([pandas.DataFrame([champion_frequency_header])[champion_frequency_df.columns], champion_frequency_df], ignore_index = True)
    return champion_frequency_df

def GetCandidateChampions(candidate_championIds: Optional[list[int]] = None, enable_bravery: bool = True) -> list[int]: #从用户输入读取候选英雄序号列表（Read candidate championId list from user input）
    '''
    提取将用户传入的英雄序号列表中所有合法的英雄序号并返回。<br>Extract all legal championIds from the championId list input by the user and return them.
    
    :param candidate_championIds: 待处理的英雄序号列表，或者是一个英雄序号。未指定时，将在函数内要求用户输入一个英雄序号列表。<br>A list of championIds to process, or a single championId. When it's not specified, the function itself will ask the user to submit a championId list.
    :type candidate_championIds: list[int]
    :param enable_bravery: 允许传入勇敢举动的英雄序号。默认为真。<br>Whether to allow the championId of Bravery passed. True by default.
    :type enable_bravery: bool
    :return: 处理后的合法的英雄序号列表。<br>A list of valid championIds after processing.
    :rtype: list[int]
    '''
    #参数预处理（Parameter preprocess）
    if candidate_championIds == None:
        candidate_championIds = []
    if candidate_championIds == []:
        logPrint("请输入想要选择的英雄的序号：\nPlease select the candidate champions' ids that you'd like to pick.\n示例（Example）：\n11\t# 无极剑圣 易（Master Yi）\n[1, 2, 3, 5]\t#黑暗之女 安妮（Annie）、狂战士 奥拉夫（Olaf）、正义巨像 加里奥（Galio）和德邦总管 赵信（Xin Zhao）中的任意一名英雄，优先级从左至右")
        while True:
            candidate_championIds_str: str = logInput()
            if candidate_championIds_str == "":
                continue
            elif candidate_championIds_str[0] == "0":
                break
            else:
                try:
                    tmp = eval(candidate_championIds_str)
                except:
                    logPrint("语法错误！请重新输入。\nSyntax ERROR! Please try again.")
                else:
                    if isinstance(tmp, int):
                        if tmp in LoLChampions or tmp == -3:
                            candidate_championIds = [tmp]
                            break
                        else:
                            logPrint("您输入的英雄序号有误！请重新输入。\nInvalid championId! Please try again.")
                    elif isinstance(tmp, list):
                        if len(tmp) == 0:
                            logPrint("请至少选择一个英雄！\nPlease choose at least one champion!")
                        elif all(map(lambda x: isinstance(x, int), tmp)):
                            candidate_championIds = tmp
                            break
                        else:
                            logPrint("您输入的英雄序号列表有误！请输入由正整数组成的列表。\nInvalid championId list! Please submit a list of positive integers.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
    else:
        if isinstance(candidate_championIds, int):
            candidate_championIds = [candidate_championIds]
        elif not (isinstance(candidate_championIds, list) and all(map(lambda x: isinstance(x, int), candidate_championIds))):
            candidate_championIds = []
    valid_championIds: list[int] = []
    for championId in candidate_championIds:
        if (championId in LoLChampions or enable_bravery and championId == -3) and not championId in valid_championIds: #这一步实现了候选英雄序号列表去重。使用勇敢举动的英雄序号进行调试，因为自定义房间永远都选不到勇敢举动，但需要按Ctrl-C强行终止程序（This step achieves deduplication of the candidate championId list. The championId of Bravery is allowed for debug, because one can never select it in a custom lobby. However, if -3 is specified, then one has to Press Ctrl-C to cancel the program）
            valid_championIds.append(championId)
    return valid_championIds

def GetCandidateChampionChoices(candidate_championId_options: Optional[list[list[int]]] = None) -> list[list[int]]: #从用户输入读取多个候选英雄选项（Read multiple candidate champion options from user input）
    '''
    通过连续输入英雄序号列表，使得在随机英雄时，匹配其中任意一个选项。<br>By continuously submitting candidate championId lists, the random champions should match one of these options.
    
    :param candidate_championId_options: 由候选英雄序号选项组成的列表。<br>A list of candidate championId options.
    :type candidate_championId_options: list[list[int]]
    '''
    #参数预处理（Parameter preprocess）
    if candidate_championId_options == None:
        candidate_championId_options = [[]]
    if candidate_championId_options == [[]]:
        logPrint('''请按照方案优先级依次输入想要选择的英雄的列表。输入“0”以结束输入。\nPlease submit lists of candidate champions' ids one by one, according to the priority of schemes. Submit "0" to cancel.\n示例（Example）：\n11\t# 无极剑圣 易（Master Yi）\n[1, 2, 3, 5]\t#黑暗之女 安妮（Annie）、狂战士 奥拉夫（Olaf）、正义巨像 加里奥（Galio）和德邦总管 赵信（Xin Zhao）中的任意一名英雄，优先级从左至右''')
        while True:
            candidate_championIds_str: str = logInput()
            if candidate_championIds_str == "":
                continue
            elif candidate_championIds_str[0] == "0":
                break
            else:
                try:
                    tmp = eval(candidate_championIds_str)
                except:
                    logPrint("语法错误！请重新输入。\nSyntax ERROR! Please try again.")
                else:
                    if isinstance(tmp, int):
                        if tmp in LoLChampions:
                            option: list[int] = [tmp]
                            candidate_championId_options.append(option)
                        else:
                            logPrint("您输入的英雄序号有误！请重新输入。\nInvalid championId! Please try again.")
                    elif isinstance(tmp, list):
                        if len(tmp) == 0:
                            logPrint("请至少输入一个英雄！\nPlease input at least one champion!")
                        elif all(map(lambda x: isinstance(x, int) and x in LoLChampions, tmp)): #这一部分相比单选模式较为严格（This part is more serious then the single mode）
                            option = tmp
                            candidate_championId_options.append(option)
                        else:
                            logPrint("您输入的英雄序号列表有误！请输入由正整数组成的列表。\nInvalid championId list! Please submit a list of positive integers.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
    else:
        if not (isinstance(candidate_championId_options, list) and all(map(lambda x: isinstance(x, list) and all(map(lambda y: isinstance(y, int), x)), candidate_championId_options))):
            candidate_championId_options = [[]]
    valid_championId_options: list[list[int]] = []
    valid_championId_optionSets: list[set[int]] = []
    for option in candidate_championId_options:
        option1: list[int] = []
        for championId in option:
            if championId in LoLChampions and not championId in option1: #这一步实现了候选英雄序号列表去重（This step achieves deduplication of the candidate championId list）
                option1.append(championId)
        if option1 != [] and not set(option1) in valid_championId_optionSets: #这一步实现了候选英雄方案去重（This step achieves deduplication of the candidate championId schemes）
            valid_championId_options.append(option1)
            valid_championId_optionSets.append(set(option1))
    if len(valid_championId_options) == 0:
        valid_championId_options.append([]) #保证该列表中至少有一个元素（Ensure there's at least one element in this list）
    return valid_championId_options

async def StartBlindPickCustomAARAM(connection: Connection, premade: bool = False, isCrowd: bool = False, roleType: Literal[1, 2, 3] = 1, queueId: int = 3270, preset_championIds: Optional[list[int]] = None, ally_candidate_championId_options: Optional[list[list[int]]] = None, enemy_candidate_championId_options: Optional[list[list[int]]] = None, interval: Optional[float] = None, champion_frequency_dict: Optional[dict[int, int]] = None) -> tuple[int, pandas.DataFrame]: #以想玩的英雄启动海克斯大乱斗自定义游戏（Start a custom ARAM: Mayhem game with a wanted champion）
    '''
    统计在全随机模式中选到想玩的英雄的频率。在只需要房主选定一名英雄的情况下可使用此函数。<br>Count the frequency of rolling candidate champions in an all-random mode. This function may be used when only the lobby owner needs some specific champions.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param premade: 是否预组队，即用户所在阵营是否有超过1名人类玩家。默认为假。<br>Whether this party is premade, that is, whether there's more than 1 human player in the user's belonging team. False by default.
    
        注意，其他成员需要指定和房主相同的英雄，以便函数输出正确的提示，并正确中止运行。<br>Note that other members should specify the same champions as the lobby owner does, so that the function could give correct hints and cancel correctly.
        
        如果是选择了多选模式，且房主指定了对方的候选英雄序号，则房主的对手在分别指定友军和敌军的候选英雄序号列表时，需要以房主的输入为基准。<br>Note that under crowd mode, if the lobby owner specifies the opponents' championId list, then when the lobby owner's opponents are trying to specify the ally and enemy candidate championId lists, they should follow the lobby owner's input.
        
    :type premade: bool
    :param isCrowd: 是否启用多选模式。默认为假。<br>Whether to enable multiple choices. False by default.
    
        在单选模式下，用户可以传入一个候选英雄序号列表，其中的一个英雄将被房主选择。<br>Under single mode, the user may pass a candidate championId list, from which one champion will be selected for the lobby owner only.
        
        在多选模式下，用户可以传入友方候选英雄序号列表和敌方候选英雄序号列表（如果敌方英雄选择信息可用）。<br>Under crowd mode, the user may pass an ally candidate championId list and an enemy candidate championId list (if enemy selected champions are revealed).
        
    :type isCrowd: bool
    :param roleType: 角色类型。仅在预组队时可用。有以下取值：<br>Player's role. Only available when the party is premade, namely `premade` is True. It may be one of the following values:
    
        - 1: 房主，或者说主播，即能开启游戏的那名玩家。<br>The lobby owner, or the host / streamer, which is the player that can start the game.
        - 2: 一般权限友军。<br>An ally without any priviledge.
        - 3: 一般权限敌军。注意，在全随机模式中，这个信息往往不可见，因此往往用不到这个取值。<br>An enemy without any priviledge. Note that in all-random mode, this information is always invisible, so this always is never used.
        
        两种角色执行的行为如下：<br>Behaviors of these two roles are as follows:
        
        1: 房主/主播。<br>Lobby owner / Host.
        
            - 房主能够开启游戏。<br>The lobby owner can start the game.
            - 房主会在英雄选择阶段扫描所有人的英雄选择状态。<br>The lobby owner will scan every player's seletion status during the champ select stage.
            - 等待所有人选定一名英雄后，房主会扫描所有已选择的英雄以及替补英雄池中的英雄。如果这些英雄和预选英雄有重合，那么一次测试结束；否则，重新启动下一个英雄选择阶段。<br>After everyone's picked a champion, the lobby owner will scan all selected champions and bench champions. If they overlap with the candidate champions, then this test is over; otherwise, start the next champ select stage.
            
        2/3: 普通成员/水友。<br>Member / Audience.
        
            - 水友等待房主开启游戏后，在进入英雄选择阶段的一瞬间，水友迅速选择优先级较低的英雄卡片，以便房主迅速做出决定。<br>After the lobby owner starts the game, at the instance of enter the champ select stage, the member immediately select a champion card with lowest priority, so that the lobby owner can make a decision as quickly as possible.
            - 在任意玩家发起英雄交换请求时，迅速同意之。<br>Once a champion swap request is made, accept it.
        
    :type roleType: int
    :param queueId: 拟创建的自定义房间的对局序号。自定义房间必须是**全随机模式**。默认创建海克斯大乱斗自定义。<br>QueueId of the custom lobby to create. The custom lobby must be **all-random**. ARAM: Mayhem lobby is created by default.
    :type queueId: int
    :param preset_championIds: 指定预选英雄序号列表参数以快速指定英雄。如果不指定，将会在函数体内要求用户输入一个英雄序号列表。<br>Specify this parameter to quickly specify champions. If it's not specified, the function will ask the user to submit a championId list.
    :type preset_championIds: list[int]
    :param ally_candidate_championId_options: 我方候选英雄序号方案。<br>A list of candidate championId schemes of myTeam.
    :type ally_candidate_championId_options: list[int]
    :param enemy_candidate_championId_options: 对方候选英雄序号列表。<br>A list of candidate championId schemes of theirTeam.
    :type enemy_candidate_championId_options: list[int]
    :param interval: 操作间隔。这个参数用于防止请求频繁导致客户端直接卡死。这个间隔依据服务器延迟而定，可设置为0.2～1秒。<br>Interval between operation cycles. This parameter is meant to prevent League Client from being seriously stuck. This interval can be set as a value between 0.2 and 1 second, which depends on the server lag.
    :type interval: float
    :param champion_frequency_dict: 欲补充的英雄出现次数频数统计字典。如果不传入该参数，函数将自动初始化该参数。<br>The champion occurrence frequency distribution dictionary to supplement. If this parameter isn't passed into any value, the function will automatically initialize this parameter.
    :type champion_frequency_dict: dict[int, int]
    :return: 目标英雄序号和在这个过程中随机到的所有英雄的频数统计数据框。<br>The target championId and all champions' frequency distribution dataframe during this process.<br>频数统计数据请以较为流畅的设备为准。<br>Please refer to the result from the device that runs most smoothly.

        当目标英雄序号为-2时，表示更换候选英雄序号列表。<br>When the target championId is -2, it means that the candidate championId list has been changed.
    :rtype: tuple[int, pandas.DataFrame]
    '''
    #参数预处理和变量初始化（Parameter preprocess and variable initialization）
    if preset_championIds == None:
        preset_championIds = []
    if ally_candidate_championId_options == None:
        ally_candidate_championId_options = [[]]
    if enemy_candidate_championId_options == None:
        enemy_candidate_championId_options = [[]]
    if champion_frequency_dict == None:
        champion_frequency_dict = {} #不同英雄序号的频数统计表。键是英雄序号，值是随到的次数（Different champions' frequency distribution table, whose keys are championIds and values are occurrences）
    champion_frequency_dict_singleTest: dict[int, int] = {} #该字典仅存储单次测验中的频数（This dictionary only stores the frequency in a single test）
    if not premade: #如果是自己一个人玩，则为单选模式，且用户一定是房主（If the user is playing a solo custom game, it must be single mode, and the user must be the lobby owner）
        isCrowd = False
        roleType = 1
    if roleType != 2 and roleType != 3:
        roleType = 1
    if interval == None:
        interval = 0
    target_championId: int = -1 #初始化返回值（Initialize the returned value）
    if premade and roleType == 2 and len(preset_championIds) == 0:
        logPrint("请指定候选英雄列表，保持和房主相同：\nPlease specify the candidate championId list, which should be the same as the lobby owner:")
    if not isCrowd or preset_championIds != []: #在多选模式下，未指定该变量时，不用再次询问（Under crowd mode, when this variable isn't specified, don't ask for it again）
        self_candidate_championIds: list[int] = GetCandidateChampions(candidate_championIds = preset_championIds)
    else:
        self_candidate_championIds = []
    if isCrowd or ally_candidate_championId_options != [[]]: #在单选模式下，未指定该变量时，不用再次询问（Under single mode, when this variable isn't specified, don't ask for it again）
        logPrint("正在指定我方候选英雄序号列表……\nSpecifying ally candidate championId list ...")
        ally_candidate_championId_options = GetCandidateChampionChoices(candidate_championId_options = ally_candidate_championId_options)
        if enemy_candidate_championId_options != [[]]: #考虑到目前自定义大乱斗的对方选用英雄信息是不可用的，如果用户没有指定敌方候选英雄序号列表，则不再询问（Considering currently the opponent team's champ select information in custom ARAM isn't available, if the user doesn't specify the enemy candidate championId list, then the function won't ask for it again）
            logPrint("正在指定敌方候选英雄序号列表……\nSpecifying opponent candidate championId list ...")
            enemy_candidate_championId_options = GetCandidateChampionChoices(candidate_championId_options = enemy_candidate_championId_options)
    current_candidate_championIds: list[int] = self_candidate_championIds if not isCrowd else ally_candidate_championId_options[0] if roleType != 3 else enemy_candidate_championId_options[0] #存储用户在实际选择时使用的候选英雄序号列表。在多选模式下，自动取第一个元素作为候选英雄序号列表（Stores the candidate championId list used for user team champion seletion in practice. Under crowd mode, the first element is taken as the candidate championId list）
    opponent_candidate_championIds: list[int] = [] if not isCrowd else enemy_candidate_championId_options[0] if roleType != 3 else ally_candidate_championId_options[0] #存储用户的对手在实际选择时使用的候选英雄序号列表，在确定对手是否选到候选英雄时可能有用（Stores the candidate championId list used for enemy team champion seletion in practice. It may be useful when the program judges whether the opponent has picked the wanted champion）
    enable_enemy_detect: bool = isCrowd and not (len(enemy_candidate_championId_options) == 1 and len(enemy_candidate_championId_options[0]) == 0) #在多选模式下，当敌方候选英雄方案不为空时，此变量为真（Under crowd mode, when the enemy candidate championId scheme isn't empty, this variable is set as True）
    enemy_champion_got: bool = False #在多选模式下，标记对手阵营是否已经选到所有候选英雄。仅在enable_enemy_detect为真时可用（Marks whether the opponent team have selected all candidate champions under crowd mode. Only used when `enable_enemy_detect` is True）
    #执行程序（Main part）
    if not isCrowd and len(self_candidate_championIds) > 0 or isCrowd and len(ally_candidate_championId_options):
        if not isCrowd and len(self_candidate_championIds) > 0:
            logPrint("您的候选英雄按优先级排列如下：\nYour candidate champions are as follows, ordered by priority:", print_time = True)
            for championId in self_candidate_championIds:
                if championId == -3:
                    logPrint("勇敢举动 Bravery", write_time = False)
                else:
                    logPrint(LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"], write_time = False)
        else:
            logPrint("我方候选英雄如下：\nYour team's candidate champions are as follows:")
            for i in range(len(ally_candidate_championId_options)):
                logPrint("方案%d：\nScheme %d:" %(i + 1, i + 1))
                option: list[int] = ally_candidate_championId_options[i]
                for championId in option:
                    if championId == -3:
                        logPrint("勇敢举动 Bravery", write_time = False) #这部分不可能被执行（This part will never be executed）
                    else:
                        logPrint(LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"], write_time = False)
            if not (len(enemy_candidate_championId_options) == 1 and len(enemy_candidate_championId_options[0]) == 0):
                logPrint("敌方候选英雄如下：\nOpponent team's candidate champions are as follows:")
                for i in range(len(enemy_candidate_championId_options)):
                    logPrint("方案%d：\nScheme %d:" %(i + 1, i + 1))
                    option: list[int] = enemy_candidate_championId_options[i]
                    for championId in option:
                        if championId == -3:
                            logPrint("勇敢举动 Bravery", write_time = False) #这部分不可能被执行（This part will never be executed）
                        else:
                            logPrint(LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"], write_time = False)
        if not premade or roleType == 1: #房主（Lobby owner）
            lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            if "gameConfig" in lobby_information and lobby_information["gameConfig"]["queueId"] == queueId:
                logPrint('在所有成员准备就绪后，按回车键继续。输入“0”以返回上一层更换候选英雄。\nAfter all members are ready, press Enter to continue. Submit "0" to return to the last step and change the candidate champions.')
            else:
                response = await create_lobby(connection, queueId = queueId, lobbyName = args.lobby_name, lobbyPassword = args.lobby_password, aramMapMutator = args.aram_map_mutator, spectatorPolicy = args.spectator_policy, teamSize = args.team_size, spectatorDelayEnabled = args.enable_spectator_delay, hidePublicly = args.hide_publicly)
                if "errorCode" in response:
                    logPrint('创建房间失败。请手动创建房间，然后按回车键继续。输入“0”以返回上一层更换候选英雄。\nLobby creation failed. Please manually create a lobby and then Press Enter to continue. Submit "0" to return to the last step and change the candidate champions.')
                else:
                    logPrint('创建房间成功。在所有成员准备就绪后，按回车键继续。输入“0”以返回上一层更换候选英雄。\nLobby creation succeeded. After all members are ready, press Enter to continue. Submit "0" to return to the last step and change the candidate champions.')
            tmp: str = logInput()
            if tmp != "" and tmp[0] == "0":
                return (-2, sort_champion_frequency_table(champion_frequency_dict_singleTest))
            count: int = 0
            #请注意：在以下代码中，selected_priority变量是关键（Note: In the following code, `selected_priority` is the essence）
            while True: #需要提前确保玩家已经创建了一个极地大乱斗或者海克斯大乱斗的房间（The user should make sure in advance that he/she has created an ARAM or ARAM: Mayhem lobby）
                if keyboard.is_pressed("esc"): #用于勇敢举动的调试（For debugging with Bravery）
                    logPrint("您已中断测试。请在准备就绪后开启下一场测试。\nYou've cancelled this test. Please start the next test after you're prepared.", print_time = True)
                    return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                #第一步：保证游戏状态是房间（Step 1: Ensure `gameflow_phase` is "Lobby"）
                while True:
                    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                    if gameflow_phase == "Lobby":
                        break
                    if interval != 0: #延迟响应（Respond after a lag）
                        time.sleep(interval)
                #第二步：开始游戏（Step 2: Start the game）
                while True:
                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                    logPrint(response)
                    if isinstance(response, dict) and "errorCode" in response:
                        if response["httpStatus"] == 400:
                            if response["message"] == "INVALID_PERMISSIONS":
                                logPrint("您不是小队拥有者，无法进行此操作。\nYou're not the party owner and thus can't perform this operation.", print_time = True)
                                return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                            elif response["message"] == "INVALID_PLAYER_STATE":
                                logPrint("所有成员都必须选好位置才能进入队列。\nAll member(s) must select their positions before entering queue.", print_time = True)
                                # logPrint("按回车键继续……\nPress Enter to continue ...")
                                # logInput()
                            # elif response["message"] == "CHAMPION_SELECT_ALREADY_STARTED":
                            #     await connection.request("DELETE", "/lol-lobby/v2/lobby/matchmaking/search")
                    #偶然发现，有时上述接口返回的是None，但是游戏状态仍卡在房间（I happened to find sometimes although the above endpoint returns None, the gameflow_phase is still stuck as "Lobby"）
                    #确保游戏状态是英雄选择阶段且英雄选择会话正常（Ensure `gameflow_phase` is "ChampSelect" and the champ select session is normal）
                    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                    if not "errorCode" in champ_select_session:
                        break
                    if interval != 0:
                        time.sleep(interval)
                #第三步：等待所有成员选一名英雄（Step 3: Wait for all members to pick a champion）
                AllPrepared: bool = False #标记所有成员是否准备就绪（Marks whether all members are prepared）
                champ_select_session_errored: bool = False #标记英雄选择会话是否出现异常。有点像returned_to_lobby（Mark if the champ select session is errored. Kind of like `returned_to_lobby`）
                while True:
                    #第三步：第一阶段：获取可选英雄列表（Step 3: Phase 1: Get the list of pickable champions' ids）
                    pickable_championIds: list[int] = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/subset-champion-list")).json()
                    #程序分支——根据海克斯大乱斗至少有一个英雄卡片来判断当前房间是否正确（Program branch - Judge whether the current lobby is correct according to the fact that there's at least a champion card during the champ select stage of ARAM: Mayhem）
                    if len(pickable_championIds) == 0:
                        logPrint("英雄选择过程异常！请检查您是否处于海克斯大乱斗房间中。如果游戏模式不正确，请检查程序中的相关参数。\nAn unexpected phenomenon was detected during the champ select stage! Please check if you're currently in an ARAM: Mayhem lobby. If the game mode isn't correct, please check the related parameters in the program.")
                        time.sleep(3)
                        return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                    else:
                        #输出对自己可用的所有英雄卡片信息（Output all champion cards available to the user itself）
                        count += 1
                        logPrint("第%d次尝试（%d）：当前可用英雄【Times tried: %d - Currently available champions (%d)】： %s" %(count, champ_select_session["gameId"], count, champ_select_session["gameId"], pickable_championIds), print_time = True)
                        pickable_champion_df: pandas.DataFrame = LoLChampion_df[LoLChampion_df["id"].isin(pickable_championIds)]
                        pickable_champion_df_fields_to_print: list[str] = ["id", "name", "title", "alias"]
                        logPrint(format_df(pickable_champion_df.loc[:, pickable_champion_df_fields_to_print])[0], write_time = False)
                        #第三步：第二阶段：选择一个英雄卡片（Step 3: Phase 2: Select a champion card）
                        selected_priority: int = len(current_candidate_championIds) #初始化当前选用英雄的优先级（Initialize the priority of the currently selected champion）
                        for championId in current_candidate_championIds: #在可选英雄列表中出现了候选英雄的情况下，按优先级选择一名候选英雄（When a candidate champion is present in the pickable championId list, select a candidate champion according to priority）
                            if championId in pickable_championIds:
                                while True:
                                    champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                    if "errorCode" in champ_select_session:
                                        champ_select_session_errored = True
                                        break
                                    localPlayer = extract_champSelect_player(champ_select_session)
                                    if localPlayer["championId"] == championId:
                                        break
                                    else:
                                        await secLock(connection, championId = championId)
                                    if interval != 0:
                                        time.sleep(interval)
                                if not champ_select_session_errored:
                                    logPrint("您已选择（You selected）：%s %s (%d)" %(LoLChampions[championId]["name"], LoLChampions[championId]["title"], championId), print_time = True)
                                    selected_priority = current_candidate_championIds.index(championId)
                                    target_championId = championId
                                break
                        else: #如果可选英雄列表中没有候选英雄，则选择第一个英雄卡片（If there's not any candidate champion in the pickable champion list, then select the first champion card）
                            while True:
                                champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                if "errorCode" in champ_select_session:
                                    champ_select_session_errored = True
                                    break
                                localPlayer = extract_champSelect_player(champ_select_session)
                                if localPlayer["championId"] == pickable_championIds[0]:
                                    break
                                else:
                                    await secLock(connection, championId = pickable_championIds[0])
                                if interval != 0:
                                    time.sleep(interval)
                            logPrint("未从您的英雄卡片中找到一名候选英雄。\nThere's not any candidate champion among those champion cards.\n您已选择（You selected）：%s %s (%d)" %(LoLChampions[pickable_championIds[0]]["name"], LoLChampions[pickable_championIds[0]]["title"], pickable_championIds[0]), print_time = True)
                        if champ_select_session_errored:
                            break
                        if not isCrowd and selected_priority == 0: #在单选模式下，如果已经拿到最高优先级的候选英雄，就不必执行下一步（Under single mode, if the champion with the highest priority is already got, then there's no need to execute the next step）
                            break
                        #偶然发现一个问题：在性能较慢的机器上执行这两个阶段时，性能优良的机器可能已经在执行下一个英雄选择阶段。从而导致一个现象：前面确实选了一个英雄，但是是上一个英雄选择阶段的。结果执行到下面，实际上自己还没有选择英雄，结果导致即使其他成员都选好英雄了，结果却因为自己本次英雄选择阶段还没有选择英雄，导致在人为不干预的情况下，需要等待选英雄倒计时耗尽自动选一名英雄，才视为所有成员选好了英雄（I happened to observe an issue: When a slow machine has finished Phase 2 of Step 3 and is just going to run the third phase, a fast machine may be during the next champ select stage. In that case, a phenomenon will occur: the player using this slow machine indeed picked a champion, but this champion belongs to the last champ select stage. And when this slow machine is going to run Step 5, the player hasn't actually selected a champion. As a result, all players except the player using the slow machine has picked their champions, and thus without human interference, all players will select a champion only after the pick timer runs out）
                        #第三步：第三阶段：等待所有成员选一名英雄（Step 3: Phase 3: Wait for all members to pick a champion）
                        logPrint("正在等待其他成员选择英雄……\nWaiting for other members to select their champions ...", print_time = True)
                        AllPrepared = False
                        while True:
                            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                            if "errorCode" in champ_select_session:
                                logPrint("您已退出英雄选择阶段。\nYou've exited the champ select stage.")
                                return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                            #这里注意不能直接调用get_champSelect_player函数来获取当前玩家信息，因为这个过程会重新获取一次英雄选择会话，而在这个间隙内可能房主会退出英雄选择阶段，进而导致键错误（Note here that `get_champSelect_player` shouldn't be used to get the current player information, for this function will get the champ select session one more time, and during this interval, the lobby owner may quit the champ select session, which will cause a KeyError）
                            localPlayer = extract_champSelect_player(champ_select_session)
                            if localPlayer["championId"] == 0: #说明已经进入下一个英雄选择阶段。实际上，对于房主来说，是不可能出现这个问题的（Implies that now is the next champ select stage. Actually, this issue can't happen on the lobby owner）
                                break
                            AllPrepared = not 0 in set(map(lambda x: x["championId"], champ_select_session["myTeam"]))
                            if AllPrepared:
                                if enable_enemy_detect: #因为对手需要先将高优先级英雄放到替补英雄池中，再按照自己槽位序号的顺序从替补英雄池中交换相应优先级的英雄，所以需要等待一下，让对手能够顺利换到英雄（Because the opponents first put champions with higher priorities into the bench and then swap the champion with the rank corresponding to their cellId order from the bench, the program should wait for a moment here to allow the opponents swap champions）
                                    time.sleep(1)
                                    champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                    if "errorCode" in champ_select_session: #异常处理（Exceptional handling）
                                        logPrint("您已退出英雄选择阶段。\nYou've exited the champ select stage.")
                                        return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                                break
                            if interval != 0:
                                time.sleep(interval)
                        if AllPrepared:
                            break
                if champ_select_session_errored:
                    logPrint("英雄选择阶段出现异常。\nAn error occurred to the champ select stage.", print_time = True)
                    continue
                #英雄出现次数递增（Increment champion occurrences）
                AllChampionIds: list[int] = []
                # logPrint("正在更新各英雄出现次数……\nUpdating champion occurrence data ...")
                for benchChampion in champ_select_session["benchChampions"]:
                    AllChampionIds.append(benchChampion["championId"])
                    if benchChampion["championId"] in champion_frequency_dict_singleTest:
                        champion_frequency_dict_singleTest[benchChampion["championId"]] += 1
                    else:
                        champion_frequency_dict_singleTest[benchChampion["championId"]] = 1
                    if benchChampion["championId"] in champion_frequency_dict:
                        champion_frequency_dict[benchChampion["championId"]] += 1 #在指定了champion_frequency_dict参数的情况下，这一行代码将直接对原参数进行修改。下同（When `champion_frequency_dict` parameter is specified, this piece of code operates directly on the original parameter. So does the following）
                    else:
                        champion_frequency_dict[benchChampion["championId"]] = 1
                for player in champ_select_session["myTeam"] + (champ_select_session["theirTeam"] if enable_enemy_detect else []):
                    if player["championId"] != 0:
                        AllChampionIds.append(player["championId"])
                        if player["championId"] in champion_frequency_dict_singleTest:
                            champion_frequency_dict_singleTest[player["championId"]] += 1
                        else:
                            champion_frequency_dict_singleTest[player["championId"]] = 1
                        if player["championId"] in champion_frequency_dict:
                            champion_frequency_dict[player["championId"]] += 1
                        else:
                            champion_frequency_dict[player["championId"]] = 1
                if not isCrowd and selected_priority == 0:
                    break
                #输出所有英雄信息，以防止频繁操作之后无法看到英雄选择阶段而无法判断程序准确性（Output all champion information, in case after frequent operations, the champ select stage can't be seen, so that users can't judge the correctness of this program）
                logPrint("本局游戏中的所有英雄如下：\nAll champions in this game are as follows:", print_time = True)
                for championId in AllChampionIds:
                    logPrint("%s %s (%d)" %(LoLChampions[championId]["name"], LoLChampions[championId]["title"], championId), write_time = False)
                if isCrowd: #多选模式将直接根据所有英雄进行判断，而不会要求用户具体一定要选什么英雄才能让程序进行下一步（Crowd mode will judge on all available champions, instead of asking players to choose a specific champion before the program goes next）
                    #第四步（仅多选模式）：检查所有英雄是否都已包含，如果包含则完成测试，否则重新开始英雄选择阶段【Step 4 (crowd mode only): Check if all candidate champions are included. If they are, finish the test; otherwise, restart the champ select stage）
                    pickable_championId_set1: set[int] = set(map(lambda x: x["championId"], champ_select_session["benchChampions"] + champ_select_session["myTeam"])) #己方可选英雄（Pickable champions in the lobby owner's team）
                    pickable_championId_set2: set[int] = set(map(lambda x: x["championId"], champ_select_session["theirTeam"])) #对方可选英雄（Pickable champions in the lobby owner's opponent team）
                    AllGot: bool = False #标记是否出现了所有候选英雄（Marks whether all candidate champions appear）
                    for ally_option in ally_candidate_championId_options:
                        break_loop: bool = False #仅用于内层for循环向外层发出退出信号（Only used for the inner for-loop to send an break signal to the outer for-loop）
                        if len(set(pickable_championId_set1) & set(ally_option)) == min(len(champ_select_session["myTeam"]), len(ally_option)):
                            '''
                            如果己方有两名人类玩家，候选英雄序号列表有一个英雄，那么最终可选的候选英雄应该有一个。<br>If the lobby owner's team has two human players and the candidate list has one champion, then the final pickable candidate champions should be one.
                            
                            如果己方有两名人类玩家，候选英雄序号列表有两个英雄，那么最终可选的候选英雄应该有两个。<br>If the lobby owner's team has two human players and the candidate list has two champions, then the final pickable candidate champions should be two.
                            
                            如果己方有两名人类玩家，候选英雄序号列表有三个英雄，那么最终可选的候选英雄应该有两个。<br>If the lobby owner's team has two human players and the candidate list has three champions, then the final pickable candidate champions should be three.
                            '''
                            if enable_enemy_detect:
                                for opponent_option in enemy_candidate_championId_options:
                                    if len(set(pickable_championId_set2) & set(opponent_option)) == min(len(champ_select_session["theirTeam"]), len(opponent_option)):
                                        AllGot = True
                                        target_championId = localPlayer["championId"] #这部分返回内容其实没有完善。正常情况下，多选模式期望返回的应该是所有已选的候选英雄序号组成的列表（This part is actually not well implemented. In normal cases, crowd mode is expected to return a list of all selected candidate championIds）
                                        logPrint("已发现候选英雄。请自行安排各英雄的选用者。\nCandidate champions are found. Please arrange each champion's player on your own.")
                                        break_loop = True
                                        break
                                else:
                                    logPrint("本次英雄选择会话中没有足够的候选英雄。\nThere're not enough candidate champions in this champ select session.")
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/quit")).json()
                                    if interval != 0:
                                        time.sleep(interval)
                                    break
                            else:
                                AllGot = True
                                target_championId = localPlayer["championId"] #这部分返回内容其实没有完善。正常情况下，多选模式期望返回的应该是所有已选的候选英雄序号组成的列表（This part is actually not well implemented. In normal cases, crowd mode is expected to return a list of all selected candidate championIds）
                                logPrint("已发现候选英雄。请自行安排各英雄的选用者。\nCandidate champions are found. Please arrange each champion's player on your own.")
                                break
                            if break_loop:
                                break
                    else:
                        logPrint("本次英雄选择会话中没有足够的候选英雄。\nThere're not enough candidate champions in this champ select session.")
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/quit")).json()
                        if interval != 0:
                            time.sleep(interval)
                    if AllGot:
                        break
                else: #单选模式仅服务于房主，用于房主选择候选英雄列表中能选择的最高优先级的英雄。因此，房主应尽可能选择高优先级的英雄，其它成员应尽可能选择低优先级的英雄（Single mode only serves for the lobby owner; it's designed to allow the lobby owner to select a champion in the candidate champion list with the highest priority. Therefore, the lobby owner must select a champion with highest priority, while all other members should select one with lowest priority）
                    #第四步（仅单选模式）：在所有成员选择一名英雄后，检查所有已选英雄和替补英雄池中是否有候选英雄。如果自己已经选到一名候选英雄，则检查是否有更高优先级的候选英雄【Step 4 (single mode only): After all members select a champion, check if any of the candidate champions is present among all selected champions or all champions in the bench. If the user has selected one, then check if there's any champion with higher priority】
                    ##第四步（仅单选模式）：第一阶段：先检查替补英雄池的英雄【Step 4 (single mode only): Phase 1: First, check champions in the bench】
                    logPrint("正在检查替补英雄池……\nChecking the bench champion ...", print_time = True)
                    benchChampions: list[int] = list(map(lambda x: x["championId"], champ_select_session["benchChampions"]))
                    benchChampionId_priority_map: dict[int, int] = {} #之所以需要通过一个字典记录替补英雄池中的所有出现的候选英雄序号及其优先级，是因为用户可能没有其输入的英雄序号对应英雄的使用权（The reason why a dictionary to record all present candidate championIds and their priorities in the bench is needed here is that the user may not have the right to use the champion corresponding to some candidate championId）
                    for championId in benchChampions:
                        if championId in current_candidate_championIds:
                            bench_champion_priority: int = current_candidate_championIds.index(championId)
                            # bench_championName: str = LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"]
                            benchChampionId_priority_map[bench_champion_priority] = championId #由于GetCandidateChampions函数的去重操作，所以不可能有两个英雄的优先级相同（There can't be more than one champion that has the same priority due to the deduplication in `GetCandidateChampions` function）
                    for current_priority in sorted(benchChampionId_priority_map.keys()): #注意按照正序排列（Note that traversal should be performed following the ascending order of priority）
                        if current_priority < selected_priority:
                            benchChampionId_to_swap: int = benchChampionId_priority_map[current_priority]
                            benchChampion_name: str = LoLChampions[benchChampionId_to_swap]["name"] + " " + LoLChampions[benchChampionId_to_swap]["title"]
                            if champ_select_session["isLegacyChampSelect"]:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/bench/swap/%d" %(benchChampionId_to_swap))).json()
                            else:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/bench/swap/%d" %(benchChampionId_to_swap))).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint("从替补英雄池中交换%s（%d）的过程出现了一个异常。\nAn error occurred when the program is trying to swap %s (%d) from the bench." %(benchChampion_name, benchChampionId_to_swap, benchChampion_name, benchChampionId_to_swap), print_time = True)
                            else:
                                time.sleep(GLOBAL_RESPONSE_LAG)
                                selected_priority = current_priority
                                target_championId = benchChampionId_to_swap
                                localPlayer = await get_champSelect_player(connection)
                                if localPlayer["championId"] == benchChampionId_to_swap:
                                    logPrint("成功从替补英雄池中交换%s（%d）。\nYou've swapped %s (%d) from the bench successfully." %(benchChampion_name, benchChampionId_to_swap, benchChampion_name, benchChampionId_to_swap), print_time = True)
                                else:
                                    logPrint("从替补英雄池中交换%s（%d）的过程出现了一个异常。这可能只是一个显示异常。\nAn error occurred when the program is trying to swap %s (%d) from the bench. This might only be a display issue." %(benchChampion_name, benchChampionId_to_swap, benchChampion_name, benchChampionId_to_swap), print_time = True)
                                break #从替补英雄池中拿到可获取的最高优先级的英雄后，退出循环，进入下一步（After the user has got the most prior champion that is available, exit the for-loop, and go to the next step）
                    if selected_priority == 0:
                        break
                    ##第四步（仅单选模式）：第二阶段：再检查队友已选英雄。这一步不能和上一步交换，因为与队友交换英雄涉及队友的响应【Step 4 (single mode only): Phase 2: Next, check teammates' champions. This step can't be put in front of the last step, for swapping a champion with a teammate involves the response from the teammate】
                    logPrint("正在检查队友英雄……\nChecking champions selected by your teammates ...", print_time = True)
                    champ_select_session = await update_champ_select_session(connection, champ_select_session, force_update = premade) #更新英雄选择会话（Update the champ select session）
                    myTeam: dict[int, dict[str, Any]] = {member["cellId"]: member for member in champ_select_session["myTeam"]}
                    trades: dict[int, dict[str, Any]] = {trade["cellId"]: trade for trade in champ_select_session["trades"]}
                    cellId_priority_map: dict[int, int] = {} #用意类似于benchChampionId_priority_map，以防止交换中途出现异常（The design is similar to `benchChampionId_priority_map`, in case any error would happen）
                    for cellId in sorted(trades.keys()):
                        member_championId: int = myTeam[cellId]["championId"]
                        if member_championId in current_candidate_championIds:
                            #先输出该成员所选用的英雄在候选英雄列表中的优先级信息（First, output the priority information of the champion selected by a member among the candidate champion list）
                            member_selected_priority: int = current_candidate_championIds.index(member_championId)
                            member_championName: str = LoLChampions[member_championId]["name"] + " " + LoLChampions[member_championId]["title"]
                            member_puuid: str = myTeam[cellId]["puuid"]
                            member_summonerName: str = "" #初始化玩家的召唤师名（Initialize the summoner name of the player）
                            member_isVisible: bool = False #标记成员信息是否可见（Marks whether the information of the member is visible）
                            if member_puuid != "": #当玩家未开启主播模式时，输出其召唤师名（When the player hasn't toggled on Streamer Mode, print his/her summoner name）
                                member_info = await get_info(connection, member_puuid)
                                if member_info["info_got"]:
                                    member_summonerName: str = get_info_name(member_info["body"])
                                    member_isVisible = True
                            logPrint("槽位序号为%d的玩家%s选择了候选英雄%s，其优先级为%d。\nPlayer %swith cellId %d selected a candidate champion %s with priority %d." %(cellId, member_summonerName, member_championName, member_selected_priority, member_summonerName + " " if member_isVisible else "", cellId, member_championName, member_selected_priority))
                            #再更新槽位序号和候选英雄优先级之间的映射关系（Next, update the map between cellId and the candidate champion）
                            cellId_priority_map[member_selected_priority] = cellId
                    for current_priority in sorted(cellId_priority_map.keys()): #注意按照正序排列（Note that traversal should be performed following the ascending order of priority）
                        if current_priority < selected_priority: #如果在成员中找到了优先级更高的英雄，则发送交换请求（If a champion with higher priority is found among the members, then send the swap request）
                            cellId_to_trade: int = cellId_priority_map[current_priority]
                            championId_to_trade: int = current_candidate_championIds[current_priority]
                            trade_championName: str = LoLChampions[championId_to_trade]["name"] + " " + LoLChampions[championId_to_trade]["title"]
                            swap_id: int = trades[cellId_to_trade]["id"]
                            if champ_select_session["isLegacyChampSelect"]:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/champion-swaps/%d/request" %(swap_id))).json()
                            else:
                                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/champion-swaps/%d/request" %(swap_id))).json()
                            logPrint(response)
                            if isinstance(response, dict) and "errorCode" in response:
                                logPrint("未能向槽位序号为%d的玩家发送交换英雄的请求。\nFailed to send the request to swap the champion with the player with cellId %d." %(cellId_to_trade, cellId_to_trade), print_time = True)
                            else:
                                logPrint("已向槽位序号为%d的玩家发送了交换英雄的请求。\nSent the request to swap the champion with the player with cellId %d." %(cellId_to_trade, cellId_to_trade), print_time = True)
                                trade_success: bool = False #标记交换是否成功（Marks whether the trade is successful）
                                #下面等待目标玩家回应（Next, wait for the target player to respond）
                                while True:
                                    champion_swaps: dict[str, Any] | list[dict[str, Any]] = await (await connection.request("GET", "/lol-champ-select/v1/session/champion-swaps")).json()
                                    if isinstance(champion_swaps, dict) and "errorCode" in champion_swaps:
                                        logPrint("您已退出英雄选择阶段。\nYou've exited the champ select stage.", print_time = True)
                                        return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                                    else:
                                        championSwap_cellId_map: dict[int, dict[str, Any]] = {swap["cellId"]: swap for swap in champion_swaps}
                                        if championSwap_cellId_map[cellId_to_trade]["state"] == "INVALID": #对方拒绝了交换请求（The target player rejected the swap request）
                                            trade_success = False
                                            break
                                        elif championSwap_cellId_map[cellId_to_trade]["state"] == "AVAILABLE":
                                            localPlayer: dict[str, Any] = await get_champSelect_player(connection)
                                            if localPlayer["championId"] == championId_to_trade: #优先级本身就是候选英雄序号列表的索引（Priority is originally an index of candidate championId list）
                                                trade_success = True
                                                break
                                            else: #对方取消了交换请求。注意，当对方进行了一次与替补英雄池的交换时，也会取消交换请求（The target player ancelled the swap request. Note that when the target swapped a champion in the bench, the request will also be cancelled）
                                                target_player: dict[str, Any] = await get_champSelect_player(connection, cellId = cellId_to_trade)
                                                if target_player["championId"] == championId_to_trade: #表明对方是直接取消了交换请求（Indicates the target player directly cancelled this swap request）
                                                    pass
                                                else: #表明对方和替补英雄池发生了交换（Indicates the target player swapped with the bench）
                                                    logPrint("交换已失效。正在重新搜索替补英雄池……\nThis trade is outdated. Repeating to search the bench ...", print_time = True)
                                                    champ_select_session = await update_champ_select_session(connection, champ_select_session)
                                                    benchChampions: list[int] = list(map(lambda x: x["championId"], champ_select_session["benchChampions"]))
                                                    if championId_to_trade in benchChampions:
                                                        if champ_select_session["isLegacyChampSelect"]:
                                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/bench/swap/%d" %(championId_to_trade))).json()
                                                        else:
                                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/bench/swap/%d" %(championId_to_trade))).json()
                                                        logPrint(response)
                                                        if isinstance(response, dict) and "errorCode" in response:
                                                            logPrint("从替补英雄池中交换%s（%d）的过程出现了一个异常。\nAn error occurred when the program is trying to swap %s (%d) from the bench." %(trade_championName, championId_to_trade, trade_championName, championId_to_trade), print_time = True)
                                                            trade_success = False
                                                            break
                                                        else:
                                                            time.sleep(GLOBAL_RESPONSE_LAG)
                                                            selected_priority = current_priority
                                                            localPlayer = await get_champSelect_player(connection)
                                                            if localPlayer["championId"] == championId_to_trade:
                                                                logPrint("成功从替补英雄池中交换%s（%d）。\nYou've swapped %s (%d) from the bench successfully." %(trade_championName, championId_to_trade, trade_championName, championId_to_trade), print_time = True)
                                                            else:
                                                                logPrint("从替补英雄池中交换%s（%d）的过程出现了一个异常。这可能只是一个显示异常。\nAn error occurred when the program is trying to swap %s (%d) from the bench. This might only be a display issue." %(trade_championName, championId_to_trade, trade_championName, championId_to_trade), print_time = True)
                                                            trade_success = True #从替补英雄池中拿到对方刚刚放上去的目标英雄，视为交换成功（Getting the target champion that the target player has just put into the bench is considered as success）
                                                            break
                                                    else:
                                                        logPrint("出现了一个异常。\nAn error has occurred.", print_time = True)
                                                        trade_success = False
                                                        break
                                        # else:
                                        #     pass
                                    if interval != 0:
                                        time.sleep(interval)
                                if trade_success:
                                    logPrint("成功交换英雄%s（%d）。\nSuccessfully swapped champin %s (%d)." %(trade_championName, championId_to_trade, trade_championName, championId_to_trade))
                                    selected_priority = current_priority
                                    target_championId = championId_to_trade
                                    break
                    else:
                        logPrint("未从队友已选英雄中找到更高优先级的英雄。\nA champion with higher priority isn't found among those selected by teammates.", print_time = True)
                    #第五步（仅单选模式）：检查是否自己已经选到了一个候选英雄【Step 5 (single mode only): Check if the user has selected a candidate champion】
                    if selected_priority == len(current_candidate_championIds): #只有没有找到任何候选英雄时，才会退出英雄选择阶段，进入下一个循环（Only when no candidate champion is found will the lobby owner quit the champ select stage and start the next cycle）
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/quit")).json()
                        if interval != 0:
                            time.sleep(interval)
                    else:
                        break #由此结束程序（Exit the function）
        else: #premade and (roleType == 2 or roleType == 3)
            count: int = 0
            #首先判断自定义房间的房主，因为需要根据房主最终选到的候选英雄来返回相应的英雄序号。注意，预组队是无视主播模式的（First, judge about the custom lobby owner, because this function returns the championId of the candidate champion selected by the lobby owner. Note that the information of a player who has enabled Streamer Mode is still visible to its premade teammates）
            lobbyOwner_puuid: str = ""
            while True:
                if keyboard.is_pressed("esc"): #用于勇敢举动的调试（For debugging with Bravery）
                    logPrint("您已中断测试。请在准备就绪后开启下一场测试。\nYou've cancelled this test. Please start the next test after you're prepared.", print_time = True)
                    return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                lobbyOwner_determine_hint_printed: bool = False
                count += 1
                #在没有进入英雄选择阶段之前，不执行任何操作（Before entering the champ select stage, don't do anything）
                #在此期间，玩家可以进行任何操作，包括接受邀请（At this time, players can do anything, like accepting an invitation）
                logPrint("第%d次尝试：正在等待进入英雄选择阶段……\nTimes tried: %d - Waiting for champ select to start ..." %(count, count), print_time = True)
                while True:
                    if keyboard.is_pressed("esc"): #添加这一段代码的原因见后续对水友端AllPrepared部分的解释（The reason for adding this piece of code can be seen from the subsequent explanation to the `AllPrepared` part of member-side）
                        logPrint("您已中断测试。请在准备就绪后开启下一场测试。\nYou've cancelled this test. Please start the next test after you're prepared.", print_time = True)
                        return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                    if gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck", "ChampSelect"}:
                        lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                        if not "errorCode" in lobby_information:
                            if not lobbyOwner_determine_hint_printed:
                                logPrint("正在确定房主……\nDetermining the lobby owner ...", print_time = True) #在正式开始游戏之前，房主是随时可能变化的（Before the game starts, the lobby owner may change at any time）
                                lobbyOwner_determine_hint_printed = True
                            for member in lobby_information["members"]:
                                if member["isLeader"]:
                                    lobbyOwner_puuid = member["puuid"]
                                    break
                    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                    if not "errorCode" in champ_select_session:
                        break
                    if interval != 0:
                        time.sleep(interval)
                #第一步：等待所有成员选一名英雄（Step 1: Wait for all members to pick a champion）
                AllPrepared: bool = False #标记所有成员是否准备就绪（Marks whether all members are prepared）
                returned_to_lobby: bool = False #标记是否在循环的过程中已退出英雄选择阶段而回到房间（Marks whether the lobby owner has quited the champ select stage during this loop running and therefore the user returns to the lobby）
                while True:
                    #第一步：第一阶段：获取可选英雄列表（Step 1: Phase 1: Get the list of pickable champions' ids）
                    pickable_championIds: list[int] = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/subset-champion-list")).json()
                    #程序分支——根据海克斯大乱斗至少有一个英雄卡片来判断当前房间是否正确（Program branch - Judge whether the current lobby is correct according to the fact that there's at least a champion card during the champ select stage of ARAM: Mayhem）
                    if len(pickable_championIds) == 0:
                        logPrint("英雄选择过程异常！请检查您是否处于海克斯大乱斗房间中。如果游戏模式不正确，请检查程序中的相关参数。\nAn unexpected phenomenon was detected during the champ select stage! Please check if you're currently in an ARAM: Mayhem lobby. If the game mode isn't correct, please check the related parameters in the program.")
                        time.sleep(3)
                        return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                    else:
                        #输出对自己可用的所有英雄卡片信息（Output all champion cards available to the user itself）
                        logPrint("当前对局（%d）可用英雄【Currently available champions (%d)】： %s" %(champ_select_session["gameId"], champ_select_session["gameId"], pickable_championIds), print_time = True)
                        pickable_champion_df: pandas.DataFrame = LoLChampion_df[LoLChampion_df["id"].isin(pickable_championIds)]
                        pickable_champion_df_fields_to_print: list[str] = ["id", "name", "title", "alias"]
                        logPrint(format_df(pickable_champion_df.loc[:, pickable_champion_df_fields_to_print])[0], write_time = False)
                        #第一步：第二阶段：选择最低优先级的英雄卡片，以便高优先级的英雄卡片进入备选英雄池供房主交换（Step 1: Phase 2: Select the first champion card, so that the higher champion cards enter the bench for the lobby owner to swap）
                        ##注意，对于对手阵营来说，也是执行此策略。只不过后面会多一步：依据槽位序号的顺序从替补英雄池中交换得到从高到低对应优先级的英雄（Note that this is the same for `roleType == 3` case, except that there'll be another step in this case: Swap the champion of corresponding priority from the bench according to the cellId order）
                        for championId in pickable_championIds:
                            if not championId in current_candidate_championIds:
                                break
                        else: #如果自己的英雄卡片中全是候选英雄，则选择优先级较低的一个英雄卡片（If the current champion cards are all candidate champions, then pick the champion with lowest priority. Here we pick the first one）
                            for championId in current_candidate_championIds[::-1]:
                                if championId in pickable_championIds:
                                    break
                            else: #不可能执行这一部分（This part is impossible）
                                championId = current_candidate_championIds[0]
                        returned_to_lobby = False
                        while True:
                            localPlayer = await get_champSelect_player(connection)
                            if localPlayer == {}: #有可能在英雄选择会话来得及更新之前，房主已经退出英雄选择阶段回到房间了（Chances are that before the champ select session updates, the lobby owner has already quited the champ select session and returned to lobby）
                                returned_to_lobby = True
                                break
                            elif localPlayer["championId"] == championId: #有可能在发送一次请求后并未成功选择英雄（Chances are that the champion isn't selected after one request）
                                break
                            else:
                                await secLock(connection, championId = championId)
                            if interval != 0:
                                time.sleep(interval)
                        if returned_to_lobby:
                            break
                        logPrint("您已选择（You selected）：%s %s (%d)" %(LoLChampions[championId]["name"], LoLChampions[championId]["title"], championId), print_time = True)
                        #第一步：第三阶段：等待所有成员选一名英雄（Step 1: Phase 3: Wait for all members to pick a champion）
                        logPrint("正在等待其他成员选择英雄……\nWaiting for other members to select their champions ...", print_time = True)
                        AllPrepared = returned_to_lobby = False
                        while True:
                            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                            if "errorCode" in champ_select_session: #存在一种可能性：当房主的电脑非常卡时，英雄选择会话在更新到所有成员准备就绪前已经因为退出英雄选择阶段而不可用了（There's this possibility: before the champ select session is updated to the status where all players are ready, it becomes unavailable because of exiting the champ select stage）
                                logPrint("您已退出英雄选择阶段。\nYou've exited the champ select stage.", print_time = True)
                                returned_to_lobby = True
                                break
                            localPlayer = extract_champSelect_player(champ_select_session)
                            if localPlayer["championId"] == 0: #说明已经进入下一个英雄选择阶段（Implies that now is the next champ select stage）
                                break
                            AllPrepared = not 0 in set(map(lambda x: x["championId"], champ_select_session["myTeam"]))
                            if AllPrepared:
                                if roleType == 2 and enable_enemy_detect: #如果已经是对手，则不执行此部分而直接退出，执行第二步（If the user is an opponent, the break this loop directly instead of executing this part and enter Step 2）
                                    time.sleep(1)
                                    champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                    if "errorCode" in champ_select_session:
                                        logPrint("您已退出英雄选择阶段。\nYou've exited the champ select stage.")
                                        return (-1, sort_champion_frequency_table(champion_frequency_dict_singleTest))
                                break
                            if interval != 0:
                                time.sleep(interval)
                        if AllPrepared or returned_to_lobby:
                            break
                if returned_to_lobby: #如果没有全员准备就绪，有两种情形：①房主的程序自动退出英雄选择阶段，接下来将开启下一个英雄选择阶段，此时水友端应当从房间阶段重新开始尝试；②房主手动点击按钮退出英雄选择阶段，该次测试到此为止，此时水友端应当中断此次测试。而从程序上，水友端无法分辨这两种情形。因此，在前面设置了一个热键，允许水友可以自行退出循环而结束测试（If not all members are prepared, there're two cases: ① The lobby owner's program automatically quits the champ select stage, when the next champ select stage will start and the member-side should restart the attempt from the lobby phase; ② The lobby owner manually quits the program and thus ends the current test, when the member-side should cancel this test as well. However, these two cases can't be distinguished for member-side simply by programmatic means. Therefore, some place in front of this part, a hotkey is set for the member to quit the loop and end the test）
                    continue
                #第二步（仅对手阵营）：按照槽位序号顺序从高到低依次从替补英雄池中替换对应优先级的英雄【Step 2 (Opponent team only): According to the cellId order, swap the champion with corresponding priority from high to low from the bench】
                if roleType == 3:
                    team_cellIds: list[int] = sorted(map(lambda x: x["cellId"], champ_select_session["myTeam"]))
                    localPlayer_cellIdRank: int = team_cellIds.index(champ_select_session["localPlayerCellId"])
                    currentBench_championId_priority_map: dict[int, int] = {current_candidate_championIds.index(champion["championId"]): champion["championId"] for champion in champ_select_session["benchChampions"] if champion["championId"] in current_candidate_championIds} #构建从current_candidate_championIds的下标到其中在替补英雄池中存在的元素的映射（Build a map from the index of `current_candidate_championIds` to the element that exists in the current bench）
                    currentBench_candidateChampions_intersect: list[int] = [currentBench_championId_priority_map[key] for key in sorted(currentBench_championId_priority_map.keys())] #将上述字典中的值按照键（索引）排序，得到候选英雄列表和替补英雄池的有序交集（Order the values of the above dictionary according to its keys (indices) to obtain an ordered intersection between the candidate championIds and the bench championIds）
                    if localPlayer_cellIdRank < len(currentBench_candidateChampions_intersect): #当槽位序号的顺序值超过所有可选的候选英雄时，对应的玩家就不用再和替补英雄池进行交换了（When the order value of a cellId is greater than the length of all available candidate championId list, the corresponding player doesn't need to swap with the bench）
                        benchChampionId_to_swap: int = currentBench_candidateChampions_intersect[localPlayer_cellIdRank]
                        benchChampion_name: str = LoLChampions[benchChampionId_to_swap]["name"] + " " + LoLChampions[benchChampionId_to_swap]["title"]
                        if champ_select_session["isLegacyChampSelect"]:
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/bench/swap/%d" %(benchChampionId_to_swap))).json()
                        else:
                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/bench/swap/%d" %(benchChampionId_to_swap))).json()
                        logPrint(response)
                        if isinstance(response, dict) and "errorCode" in response:
                            logPrint("从替补英雄池中交换%s（%d）的过程出现了一个异常。\nAn error occurred when the program is trying to swap %s (%d) from the bench." %(benchChampion_name, benchChampionId_to_swap, benchChampion_name, benchChampionId_to_swap), print_time = True)
                        else:
                            time.sleep(GLOBAL_RESPONSE_LAG)
                            localPlayer = await get_champSelect_player(connection)
                            if localPlayer["championId"] == benchChampionId_to_swap:
                                logPrint("成功从替补英雄池中交换%s（%d）。\nYou've swapped %s (%d) from the bench successfully." %(benchChampion_name, benchChampionId_to_swap, benchChampion_name, benchChampionId_to_swap), print_time = True)
                            else:
                                logPrint("从替补英雄池中交换%s（%d）的过程出现了一个异常。这可能只是一个显示异常。\nAn error occurred when the program is trying to swap %s (%d) from the bench. This might only be a display issue." %(benchChampion_name, benchChampionId_to_swap, benchChampion_name, benchChampionId_to_swap), print_time = True)
                #英雄出现次数递增（Increment champion occurrences）
                candidate_champion_found: bool = False
                AllChampionIds: list[int] = [] #汇总本局游戏内的所有英雄（Summarize all champions in this game）
                # logPrint("正在更新各英雄出现次数……\nUpdating champion occurrence data ...", print_time = True)
                for benchChampion in champ_select_session["benchChampions"]:
                    AllChampionIds.append(benchChampion["championId"])
                    if benchChampion["championId"] in champion_frequency_dict_singleTest:
                        champion_frequency_dict_singleTest[benchChampion["championId"]] += 1
                    else:
                        champion_frequency_dict_singleTest[benchChampion["championId"]] = 1
                    if benchChampion["championId"] in champion_frequency_dict:
                        champion_frequency_dict[benchChampion["championId"]] += 1
                    else:
                        champion_frequency_dict[benchChampion["championId"]] = 1
                    if benchChampion["championId"] in current_candidate_championIds and not candidate_champion_found:
                        candidate_champion_found = True
                for player in champ_select_session["myTeam"]:
                    if player["championId"] != 0:
                        AllChampionIds.append(player["championId"])
                        if player["championId"] in champion_frequency_dict_singleTest:
                            champion_frequency_dict_singleTest[player["championId"]] += 1
                        else:
                            champion_frequency_dict_singleTest[player["championId"]] = 1
                        if player["championId"] in champion_frequency_dict:
                            champion_frequency_dict[player["championId"]] += 1
                        else:
                            champion_frequency_dict[player["championId"]] = 1
                        if player["championId"] in current_candidate_championIds and not candidate_champion_found:
                            candidate_champion_found = True
                if enable_enemy_detect: #在检测对手选用英雄的情况下，对手通过这一部分也能检测到对手的对手所在阵营选用的英雄。当然，最后总结频数的时候，双方会有差异，因为毕竟双方的替补英雄池是无法互相获取的（When the program detects the enemy team's selected champions, for an enemy user, it'll also check its enemy team's selected champions. Of course, in the end when the program summarizes the frequency distribution table, there'll be differences, because both team doesn't have access to each other's bench, after all）
                    for player in champ_select_session["theirTeam"]:
                        if player["championId"] != 0:
                            AllChampionIds.append(player["championId"])
                            if player["championId"] in champion_frequency_dict_singleTest:
                                champion_frequency_dict_singleTest[player["championId"]] += 1
                            else:
                                champion_frequency_dict_singleTest[player["championId"]] = 1
                            if player["championId"] in champion_frequency_dict:
                                champion_frequency_dict[player["championId"]] += 1
                            else:
                                champion_frequency_dict[player["championId"]] = 1
                #确定本局游戏中的所有英雄中的最高优先级（Determine the highest priority among all champions in this game）
                highest_priority: int = len(current_candidate_championIds)
                for championId in AllChampionIds:
                    logPrint("%s %s (%d)" %(LoLChampions[championId]["name"], LoLChampions[championId]["title"], championId), write_time = False) #输出所有英雄信息（Output all champion information）
                    if championId in current_candidate_championIds and current_candidate_championIds.index(championId) < highest_priority:
                        highest_priority = current_candidate_championIds.index(championId)
                #程序分支——根据是否存在候选英雄来判断下一步行动（Program branch - Decide on the next move according to whether any candidate champion is present）
                if isCrowd: #多选模式同房主（Here the crowd mode works the same as the lobby owner）
                    #第三步（仅多选模式）：检查所有英雄是否都已包含，如果包含则完成测试，否则重新开始英雄选择阶段【Step 3 (crowd mode only): Check if all candidate champions are included. If they are, finish the test; otherwise, restart the champ select stage）
                    pickable_championId_set1: set[int] = set(map(lambda x: x["championId"], champ_select_session["benchChampions"] + champ_select_session["myTeam"]))
                    pickable_championId_set2: set[int] = set(map(lambda x: x["championId"], champ_select_session["theirTeam"]))
                    AllGot: bool = False
                    for ally_option in ally_candidate_championId_options if roleType == 2 else enemy_candidate_championId_options:
                        break_loop: bool = False
                        if len(set(pickable_championId_set1) & set(ally_option)) == min(len(champ_select_session["myTeam"]), len(ally_option)):
                            if enable_enemy_detect:
                                for opponent_option in enemy_candidate_championId_options if roleType == 2 else ally_candidate_championId_options:
                                    if len(set(pickable_championId_set2) & set(opponent_option)) == min(len(champ_select_session["theirTeam"]), len(opponent_option)):
                                        AllGot = True
                                        target_championId = localPlayer["championId"] #这部分返回内容其实没有完善。正常情况下，多选模式期望返回的应该是所有已选的候选英雄序号组成的列表（This part is actually not well implemented. In normal cases, crowd mode is expected to return a list of all selected candidate championIds）
                                        logPrint("已发现候选英雄。请自行安排各英雄的选用者。\nCandidate champions are found. Please arrange each champion's player on your own.")
                                        break_loop = True
                                        break
                                else:
                                    logPrint("本次英雄选择会话中没有足够的候选英雄。\nThere're not enough candidate champions in this champ select session.")
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/quit")).json()
                                    if interval != 0:
                                        time.sleep(interval)
                                    break
                            else:
                                AllGot = True
                                target_championId = localPlayer["championId"] #这部分返回内容其实没有完善。正常情况下，多选模式期望返回的应该是所有已选的候选英雄序号组成的列表（This part is actually not well implemented. In normal cases, crowd mode is expected to return a list of all selected candidate championIds）
                                logPrint("已发现候选英雄。请自行安排各英雄的选用者。\nCandidate champions are found. Please arrange each champion's player on your own.")
                                break
                            if break_loop:
                                break
                    else:
                        logPrint("本次英雄选择会话中没有足够的候选英雄。\nThere're not enough candidate champions in this champ select session.")
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/quit")).json()
                        if interval != 0:
                            time.sleep(interval)
                    if AllGot:
                        break
                else: #在单选模式下，成员等待房主向其发起英雄交换。当房主选到最高优先级的可选候选英雄时，则退出此次尝试（Under single mode, the member keeps waiting for the lobby owner to send a champion swap request to it. When the lobby owner gets the pickable candidate champion with the highest priority, stop this try）
                    if roleType == 2 and candidate_champion_found: #这一个分支的目的主要是为了迅速回应在单选模式下来自房主的英雄交换请求，而对手阵营则不需要考虑这个问题（This branch is mainly designed to immediately respond to a champion swap request from the lobby owner under single mode. The opponent team doesn't need to think about it）
                        highest_priority_selected: bool = False #代表房主是否选到了当前对局中最高优先级的候选英雄（Represents whether the lobby owner has selected the candidate champion with the highest priority in this match）
                        # logPrint('''找到了一个候选英雄。您现在可以执行以下操作：\nA candidate champion is found. Now you may perform the following operations:\n1. 如果您目前选择的是一个优先级高于房主当前优先级的候选英雄，请等待房主向您发送英雄交换指令。\nIf you've selected a candidate champion with higher priority than the current priority of the lobby owner's champion, please wait for the lobby owner to send a champion swap request to you.\n2. 按住“Esc”键以退出循环。\nPress and keep holding [Esc] to exit the loop.''')
                        while True:
                            #按Esc键强制退出循环。谨慎使用，因为即使现在退出循环了，下一次循环也会因为识别到英雄选择阶段而再次执行到此处（Press Esc to force to exit the loop. Watch out, for even if the loop is exited, in the next loop, the user is still during the champ select phase, so the program will execute back to this place）
                            # if keyboard.is_pressed("esc"):
                            #     logPrint("您已退出循环。\nYou've exited the loop.", print_time = True)
                            #     break
                            #如果房主退出英雄选择阶段，则进入下一个循环（If the lobby owner quits the champ select session, then enter the next cycle）
                            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                            if "errorCode" in champ_select_session:
                                break
                            #检查房主是否已经选到了当前英雄选择阶段最高优先级的候选英雄（Check if the lobby owner has selected a candidate champion with the highest priority in the current champ select stage）
                            member_puuid_map: dict[str, dict[str, Any]] = {member["puuid"]: member for member in champ_select_session["myTeam"]} #不用考虑键重复的可能性。原因有两个：①主播模式不适用于自定义房间；②每个电脑玩家会被赋予一个临时的玩家通用唯一识别码（No need to consider any potential redundancy of keys. There're two reasons: ① Stream Mode doesn't take effect in a custom game; ② Each bot player will be assigned with a temporary puuid）
                            if member_puuid_map[lobbyOwner_puuid]["championId"] in current_candidate_championIds and current_candidate_championIds.index(member_puuid_map[lobbyOwner_puuid]["championId"]) == highest_priority:
                                logPrint("房主已选到当前对局中最高优先级的候选英雄。\nThe lobby owner has selected the candidate champion with the highest priority among champions in this match.", print_time = True)
                                target_championId = member_puuid_map[lobbyOwner_puuid]["championId"]
                                highest_priority_selected = True
                                break
                            #第三步：检测是否有向自己发起的英雄交换。如果有，迅速同意（Step 3: Detect if there's any on-going champion swap to the user. If there is, accept it immediately）
                            myTeam: dict[int, dict[str, Any]] = {member["cellId"]: member for member in champ_select_session["myTeam"]}
                            champion_swaps: list[dict[str, Any]] = champ_select_session["trades"]
                            if isinstance(champion_swaps, dict) and "errorCode" in champion_swaps:
                                logPrint("您已退出英雄选择阶段。\nYou've exited the champ select stage.", print_time = True)
                                break
                            else:
                                for swap in champion_swaps:
                                    if swap["state"] == "RECEIVED": #下面假设同时只可能存在一个英雄交换请求（Here we assume that there can be at most one champion swap request simultaneously）
                                        swap_id: int = swap["id"]
                                        from_cellId: int = swap["cellId"]
                                        from_championId: int = myTeam[from_cellId]["championId"]
                                        from_championName: str = LoLChampions[from_championId]["name"] + " " + LoLChampions[from_championId]["title"]
                                        from_puuid: str = myTeam[from_cellId]["puuid"]
                                        from_summonerName: str = ""
                                        sender_isVisible: bool = False
                                        if from_puuid != "":
                                            sender_info = await get_info(connection, from_puuid)
                                            if sender_info["info_got"]:
                                                from_summonerName: str = get_info_name(sender_info["body"])
                                                sender_isVisible = True
                                        if champ_select_session["isLegacyChampSelect"]:
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-champ-select/v1/session/champion-swaps/%d/accept" %(swap_id))).json()
                                        else:
                                            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby-team-builder/champ-select/v1/session/champion-swaps/%d/accept" %(swap_id))).json()
                                        logPrint(response)
                                        if isinstance(response, dict) and "errorCode" in response:
                                            logPrint("在接受来自槽位序号为%d的玩家%s的英雄交换请求出现了一个异常。\nAn error occurred when the program is trying to accept the champion swap request from the player %s with cellId %d." %(from_cellId, from_summonerName, from_summonerName + " " if sender_isVisible else "", from_cellId), print_time = True)
                                        else:
                                            logPrint("成功接受来自槽位序号为%d的玩家%s的英雄交换请求。\nSuccessfully accepted the champion swap request from the player %s with cellId %d." %(from_cellId, from_summonerName, from_summonerName + " " if sender_isVisible else "", from_cellId), print_time = True)
                                        break
                            if interval != 0:
                                time.sleep(interval)
                        if highest_priority_selected:
                            break #由此结束程序（Exit the function）
                    else:
                        if roleType == 2:
                            logPrint("候选英雄不存在。正在等待房主结束英雄选择阶段……\nCandidate champion not found. Waiting for the lobby owner to cancel champ select ...", print_time = True)
                        else:
                            logPrint("完成英雄选择。正在等待房主结束英雄选择阶段……\nChamp select finished. Waiting for the lobby owner to cancel champ select ...", print_time = True)
                        while True:
                            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                            if "errorCode" in champ_select_session:
                                break
                            if interval != 0:
                                time.sleep(interval)
    champion_frequency_df_singleTest: pandas.DataFrame = sort_champion_frequency_table(champion_frequency_dict_singleTest)
    logPrint(champion_frequency_dict_singleTest, verbose = False)
    return (target_championId, champion_frequency_df_singleTest)

async def RotateBlindPickCustomAARAM(connection: Connection, premade: bool = False, isCrowd: bool = False, roleType: Literal[1, 2, 3] = 1, queueId: int = 3270, preset_championIds: Optional[list[int]] = None, ally_candidate_championId_options: Optional[list[list[int]]] = None, enemy_candidate_championId_options: Optional[list[list[int]]] = None, interval: Optional[float] = None, champion_frequency_dict: Optional[dict[int, int]] = None) -> None: #通过连续按回车键以在海克斯大乱斗自定义游戏中连续测试想玩的英雄（Continuously start custom pick ARAM: Mayhem games using wanted champions by continuously pressing Enter）
    '''
    反复启动大乱斗英雄选择概率测试。<br>Repeatedly start the ARAM champ select probability test.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param premade: 是否预组队，即用户所在阵营是否有超过1名人类玩家。默认为假。<br>Whether this party is premade, that is, whether there's more than 1 human player in the user's belonging team. False by default.
    
        注意，其他成员需要指定和房主相同的英雄，以便函数输出正确的提示，并正确中止运行。<br>Note that other members should specify the same champions as the lobby owner does, so that the function could give correct hints and cancel correctly.
        
        如果是选择了多选模式，且房主指定了对方的候选英雄序号，则房主的对手在分别指定友军和敌军的候选英雄序号列表时，需要以房主的输入为基准。<br>Note that under crowd mode, if the lobby owner specifies the opponents' championId list, then when the lobby owner's opponents are trying to specify the ally and enemy candidate championId lists, they should follow the lobby owner's input.
        
    :type premade: bool
    :param isCrowd: 是否启用多选模式。默认为假。<br>Whether to enable multiple choices. False by default.
    
        在单选模式下，用户可以传入一个候选英雄序号列表，其中的一个英雄将被房主选择。<br>Under single mode, the user may pass a candidate championId list, from which one champion will be selected for the lobby owner only.
        
        在多选模式下，用户可以传入友方候选英雄序号列表和敌方候选英雄序号列表（如果敌方英雄选择信息可用）。<br>Under crowd mode, the user may pass an ally candidate championId list and an enemy candidate championId list (if enemy selected champions are revealed).
        
    :type isCrowd: bool
    :param roleType: 角色类型。仅在预组队时可用。有以下取值：<br>Player's role. Only available when the party is premade, namely `premade` is True. It may be one of the following values:
    
        - 1: 房主，或者说主播，即能开启游戏的那名玩家。<br>The lobby owner, or the host / streamer, which is the player that can start the game.
        - 2: 一般权限友军。<br>An ally without any priviledge.
        - 3: 一般权限敌军。注意，在全随机模式中，这个信息往往不可见，因此往往用不到这个取值。<br>An enemy without any priviledge. Note that in all-random mode, this information is always invisible, so this always is never used.
        
        两种角色执行的行为如下：<br>Behaviors of these two roles are as follows:
        
        1: 房主/主播。<br>Lobby owner / Host.
        
            - 房主能够开启游戏。<br>The lobby owner can start the game.
            - 房主会在英雄选择阶段扫描所有人的英雄选择状态。<br>The lobby owner will scan every player's seletion status during the champ select stage.
            - 等待所有人选定一名英雄后，房主会扫描所有已选择的英雄以及替补英雄池中的英雄。如果这些英雄和预选英雄有重合，那么一次测试结束；否则，重新启动下一个英雄选择阶段。<br>After everyone's picked a champion, the lobby owner will scan all selected champions and bench champions. If they overlap with the candidate champions, then this test is over; otherwise, start the next champ select stage.
            
        2/3: 普通成员/水友。<br>Member / Audience.
        
            - 水友等待房主开启游戏后，在进入英雄选择阶段的一瞬间，水友迅速选择优先级较低的英雄卡片，以便房主迅速做出决定。<br>After the lobby owner starts the game, at the instance of enter the champ select stage, the member immediately select a champion card with lowest priority, so that the lobby owner can make a decision as quickly as possible.
            - 在任意玩家发起英雄交换请求时，迅速同意之。<br>Once a champion swap request is made, accept it.
        
    :type roleType: int
    :param queueId: 拟创建的自定义房间的对局序号。自定义房间必须是**全随机模式**。默认创建海克斯大乱斗自定义。<br>QueueId of the custom lobby to create. The custom lobby must be **all-random**. ARAM: Mayhem lobby is created by default.
    :type queueId: int
    :param preset_championIds: 指定预选英雄序号列表参数以快速指定英雄。如果不指定，将会在函数体内要求用户输入一个英雄序号列表。<br>Specify this parameter to quickly specify champions. If it's not specified, the function will ask the user to submit a championId list.
    :type preset_championIds: list[int]
    :param ally_candidate_championId_options: 我方候选英雄序号方案。<br>A list of candidate championId schemes of myTeam.
    :type ally_candidate_championId_options: list[int]
    :param enemy_candidate_championId_options: 对方候选英雄序号列表。<br>A list of candidate championId schemes of theirTeam.
    :type enemy_candidate_championId_options: list[int]
    :param interval: 操作间隔。这个参数用于防止请求频繁导致客户端直接卡死。这个间隔依据服务器延迟而定，可设置为0.2～1秒。<br>Interval between operation cycles. This parameter is meant to prevent League Client from being seriously stuck. This interval can be set as a value between 0.2 and 1 second, which depends on the server lag.
    :type interval: float
    :param champion_frequency_dict: 欲补充的英雄出现次数频数统计字典。如果不传入该参数，函数将自动初始化该参数。<br>The champion occurrence frequency distribution dictionary to supplement. If this parameter isn't passed into any value, the function will automatically initialize this parameter.
    :type champion_frequency_dict: dict[int, int]
    '''
    #参数预处理（Parameter preprocess）
    if preset_championIds == None:
        preset_championIds = []
    if ally_candidate_championId_options == None:
        ally_candidate_championId_options = [[]]
    if enemy_candidate_championId_options == None:
        enemy_candidate_championId_options = [[]]
    if champion_frequency_dict == None:
        champion_frequency_dict = {}
    if not isCrowd or preset_championIds != []:
        self_candidate_championIds = GetCandidateChampions(candidate_championIds = preset_championIds)
    else:
        self_candidate_championIds = []
    if isCrowd:
        logPrint("正在指定我方候选英雄序号列表……\nSpecifying ally candidate championId list ...")
        ally_candidate_championId_options = GetCandidateChampionChoices(candidate_championId_options = ally_candidate_championId_options)
        if enemy_candidate_championId_options != [[]]:
            logPrint("正在指定敌方候选英雄序号列表……\nSpecifying opponent candidate championId list ...")
            enemy_candidate_championId_options = GetCandidateChampionChoices(candidate_championId_options = enemy_candidate_championId_options)
    current_candidate_championIds: list[int] = self_candidate_championIds if not isCrowd else ally_candidate_championId_options[0] if roleType != 3 else enemy_candidate_championId_options[0] #注意，在这个函数中，current_candidate_championIds只作为一个引用，用来指代三者之一（Note that in this function, `current_candidate_championIds` is only used as a reference to update one of the three lists）
    if not isCrowd and len(self_candidate_championIds) > 0 or isCrowd and len(ally_candidate_championId_options) > 0:
        if not isCrowd and len(self_candidate_championIds) > 0:
            logPrint("您想要测试的所有英雄如下：\nAll champions to be tested are as follows:")
            for championId in self_candidate_championIds:
                if championId == -3:
                    logPrint("勇敢举动 Bravery", write_time = False)
                else:
                    logPrint(LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"], write_time = False)
        # else: #敌我候选英雄本身已经是一个列表了，所以在设计时都是一次性的，直接在StartBlindPickCustomAARAM函数中输出一遍即可（The ally or enemy candidate championIds are already a list, so it's designed to be one-time. Therefore, relevant information should only be output once in `StartBlindPickCustomAARAM` funtion）
        #     logPrint("我方候选英雄如下：\nYour team's candidate champions are as follows:")
        #     for i in range(len(ally_candidate_championId_options)):
        #         logPrint("方案%d：\nScheme %d:" %(i + 1, i + 1))
        #         option: list[int] = ally_candidate_championId_options[i]
        #         for championId in option:
        #             if championId == -3: #这部分不可能被执行（This part will never be executed）
        #                 logPrint("勇敢举动 Bravery", write_time = False)
        #             else:
        #                 logPrint(LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"], write_time = False)
        #     if not (len(enemy_candidate_championId_options) == 1 and len(enemy_candidate_championId_options[0]) == 0):
        #         logPrint("敌方候选英雄如下：\nOpponent team's candidate champions are as follows:")
        #         for i in range(len(enemy_candidate_championId_options)):
        #             logPrint("方案%d：\nScheme %d:" %(i + 1, i + 1))
        #             option: list[int] = enemy_candidate_championId_options[i]
        #             for championId in option:
        #                 if championId == -3:
        #                     logPrint("勇敢举动 Bravery", write_time = False) #这部分不可能被执行（This part will never be executed）
        #                 else:
        #                     logPrint(LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"], write_time = False)
        count: int = 0
        while True:
            count += 1
            logPrint("*****************************************************************************", write_time = False)
            logPrint(f"试验{count}（Test No. {count}）：", print_time = True)
            picked_championId, freq_df = await StartBlindPickCustomAARAM(connection, premade = premade, isCrowd = isCrowd, roleType = roleType, queueId = queueId, preset_championIds = self_candidate_championIds, ally_candidate_championId_options = ally_candidate_championId_options, enemy_candidate_championId_options = enemy_candidate_championId_options, interval = interval, champion_frequency_dict = champion_frequency_dict)
            if len(freq_df) > 1:
                logPrint("本次试验过程的英雄出现次数频数统计情况如下：\nThe champion occurrence frequency distribution during this test is as follows:")
                logPrint(format_df(freq_df)[0], write_time = False)
            if not isCrowd and not picked_championId in {-1, -2}: #以上picked_championId返回的是完成测试时房主选用的英雄，而在多选模式中指定的候选英雄在替补英雄池中被发现时，不再执行后续的为房主选最高优先级的英雄这个动作，所以逻辑上讲，在多选模式下，picked_championId不适用于本部分（The above `picked_championId` returns the champion selected by the lobby owner, but in crowd mode, when a candidate champion is found in the bench, the program no longer performs such an action that helps the lobby owner to select the pickable candidate champion with the highest priority. So, logically speaking, under crowd mode, `picked_championId` doesn't apply to this part）
                current_candidate_championIds.remove(picked_championId)
            if len(current_candidate_championIds) == 0:
                logPrint("测试完成。按回车键退出。\nTest finished. Press Enter to exit.")
                logInput()
                break
            else: #多选模式下，current_candidate_championIds永远不可能为空（Under crowd mode, `current_candidate_championIds` can never be empty）
                if picked_championId == -2:
                    if isCrowd:
                        logPrint("正在指定我方候选英雄序号列表……\nSpecifying ally candidate championId list ...")
                        ally_candidate_championId_options = GetCandidateChampionChoices()
                        if enemy_candidate_championId_options != [[]]:
                            logPrint("正在指定敌方候选英雄序号列表……\nSpecifying opponent candidate championId list ...")
                            enemy_candidate_championId_options = GetCandidateChampionChoices()
                    else:
                        self_candidate_championIds = GetCandidateChampions()
                        current_candidate_championIds = self_candidate_championIds #既然重新指定，那就不需要再执行上述复杂的判断了（Since the user re-specifies the candidate championId list, there's no need to perform the above complex judgment）
                logPrint('按回车键以开启下一场测试，或者输入“0”以退出测试序列。\nPress Enter to start the next test, or submit "0" to quit the test sequence.')
                while True:
                    quit: bool = False
                    tmp: str = logInput()
                    if tmp != "" and tmp[0] == "0":
                        quit = True
                        break
                    else:
                        gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                        if gameflow_phase in {"InProgress", "Reconnect"}:
                            logPrint("您还在游戏中。请退出游戏后再试一次。\nYou're still in a game. Please exit the game and try again.")
                        else:
                            break
                if quit:
                    break
        #输出所有统计结果（Output all statistics）
        champion_frequency_df: pandas.DataFrame = sort_champion_frequency_table(champion_frequency_dict)
        logPrint(champion_frequency_dict, verbose = False)
        if len(champion_frequency_df) > 1:
            logPrint("总计英雄出现次数频数统计情况如下：\nTotal champion occurrence frequency distribution is as follows:")
            logPrint(format_df(champion_frequency_df)[0], write_time = False)

async def ARAMBalanceBuffTest(connection: Connection, preset_championIds: Optional[list[int]] = None) -> None: #通过连续按回车键以连续开启不同的嚎哭深渊 自定义 自选模式（Continuously start custom pick ARAM games by continuously pressing Enter）
    '''
    测试极地大乱斗的平衡性增益。<br>Test the champion balance buff in ARAM.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param preset_championIds: 指定预选英雄序号列表参数以快速指定英雄。<br>Specify this parameter to quickly specify champions.
    :type preset_championIds: list[int]
    '''
    if preset_championIds == None:
        preset_championIds = []
    self_candidate_championIds: list[int] = GetCandidateChampions(candidate_championIds = preset_championIds)
    if len(self_candidate_championIds) > 0 and self_candidate_championIds != [-3]:
        logPrint("您的候选英雄如下：\nYour candidate champions are as follows:", print_time = True)
        for championId in self_candidate_championIds:
            logPrint(LoLChampions[championId]["name"] + " " + LoLChampions[championId]["title"], write_time = False)
        for i in range(len(self_candidate_championIds)):
            target_championId: int = self_candidate_championIds[i]
            #创建房间（Create a lobby）
            await create_lobby(connection, queueId = 3200, aramMapMutator = "MapSkin_HA_Bilgewater") #默认使用屠夫之桥地图（Butcher's Bridge map is used by default）
            while True:
                gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                if gameflow_phase == "Lobby":
                    break
            #开始游戏（Start the game）
            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
            while True: #确保进入英雄选择状态，且英雄选择会话正常（Make sure `gameflow_phase` is "ChampSelect" and the champ select session is normal）
                champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                if not "errorCode" in champ_select_session:
                    break
            #选英雄（Pick a champion）
            await secLock(connection, championId = target_championId)
            logPrint("[%d/%d]" %(i + 1, len(self_candidate_championIds)), end = "", print_time = True)
            for player in champ_select_session["myTeam"]:
                if player["puuid"] == current_summoner["puuid"]:
                    if player["championId"] == target_championId:
                        logPrint("您已选择（You selected）：%s %s (%d)" %(LoLChampions[target_championId]["name"], LoLChampions[target_championId]["title"], target_championId), write_time = False)
                    else:
                        logPrint("选择英雄的过程出现了一个异常。\nAn exception occurred while the program is trying to select this champion.", write_time = False)
                    break
            else: #如果没有在当前的英雄选择会话中找到自己，则执行此部分（If the player itself isn't found in the current champ select session, this part will be executed）
                logPrint("当前英雄选择阶段没有找到您的信息。请尝试手动选择以下英雄：\nYour information isn't in the current champ select session. Please try manually picking the following champion:\n%s %s (%d)\n如果这个问题持续存在，请重新启动客户端。\nIf this issue persists, please restart the League Client.", write_time = False)
            logPrint('按回车键以开启下一场测试，或者输入“0”以退出测试序列。\nPress Enter to start the next test, or submit "0" to quit the test sequence.')
            while True:
                quit: bool = False
                tmp: str = logInput()
                if tmp != "" and tmp[0] == "0":
                    quit = True
                    break
                else:
                    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                    if gameflow_phase in {"InProgress", "Reconnect"}:
                        logPrint("您还在游戏中。请退出游戏后再试一次。\nYou're still in a game. Please exit the game and try again.")
                    else:
                        break
            if quit:
                break

async def main(connection: Connection) -> None:
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId: str = current_party["platformId"]
    game_version: str = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    crowd_mode_hine_printed: bool = False
    step: int = 1
    queueId: int = 0 #标记队列序号（Marks the queueId）
    premade: bool = False #标记是否预组队（Marks whether the party is premade）
    isCrowd: bool = False #标记是否启用多选模式（Marks whether to enable crowd mode）
    roleType: Literal[1, 2, 3] = 1 #标记用户的角色类型（Marks the user's role type）
    lagged: bool = False #是否采用延迟（Whether to enable the lag）
    interval: Optional[float] = None
    while True:
        if step == 0: #退出程序（Exit the program）
            break
        elif step == 1:
            logPrint("第一步：选择一个游戏模式。\nStep 1: Select a game mode.")
            if args.queueId in gameQueues and gameQueues[args.queueId]["isCustom"] and gameQueues[args.queueId]["gameTypeConfig"]["id"] == 21 or args.queueId == 3270: #海克斯大乱斗的游戏类型异常显示为自选模式（Game type of ARAM: Mayhem displays as Blind Pick unexpectedly）
                queueId = args.queueId
                logPrint("您已通过命令行变量指定了以下游戏模式：\nYou specified the following game mode through the cmdline argument:\n%d\t%s" %(args.queueId, gameQueues[args.queueId]["name"]))
                args.queueId = 0 #这一步是考虑到当用户指定了正确的队列序号，但是在后续步骤返回该步时，应当重新指定游戏模式（Considering when a correct queueId is provided but the user returns to this step from a subsequent step, the game mode should be specified again）
            else:
                if args.queueId != 0:
                    if not args.queueId in gameQueues:
                        logPrint("队列序号%d无效！请手动指定队列序号。\nInvalid queueId %d! Please specify a queueId manually." %(args.queueId, args.queueId))
                    elif not gameQueues[args.queueId]["isCustom"]:
                        logPrint("以下游戏模式不是自定义房间。请切换一个队列序号。\nThe specified game mode isn't custom. Please change the queueId.\n%d\t%s" %(args.queueId, gameQueues[args.queueId]["name"]))
                    elif not gameQueues[args.queueId]["gameTypeConfig"]["id"] == 21:
                        logPrint("以下游戏模式不是全随机模式。请切换一个队列序号。\nThe specified game mode isn't all-random. Please change the queueId.\n%d\t%s" %(args.queueId, gameQueues[args.queueId]["name"]))
                logPrint('请输入队列序号：（输入“0”以刷新可用队列信息。输入负数以退出程序。）\nPlease enter the queueId: (Enter "0" to refresh available queue information. Enter any negative number to exit the program.)')
                while True:
                    queueId_str: str = logInput()
                    if queueId_str == "":
                        queueId = 3270
                        break
                    elif queueId_str[0] == "0":
                        available_queue_df: pandas.DataFrame = await check_available_queue(connection)
                        logPrint("*****************************************************************************")
                        print(format_df(available_queue_df)[0])
                        log.write(format_df(available_queue_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                        logPrint("*****************************************************************************")
                        logPrint("(%s\t%s\t%s)" %(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), platformId, game_version))
                        logPrint('请输入队列序号：（输入“0”以刷新可用队列信息。输入负数以退出程序。）\nPlease enter the queueId: (Enter "0" to refresh available queue information. Enter any negative number to exit the program.)')
                    else:
                        try:
                            tmp = int(queueId_str)
                        except ValueError:
                            logPrint("请输入一个整数！\nPlease input an integer.")
                        else:
                            queueId = tmp
                            if queueId < 0:
                                step -= 2
                                break
                            elif queueId in gameQueues:
                                if gameQueues[queueId]["isCustom"] and gameQueues[queueId]["gameTypeConfig"]["id"] == 21 or queueId == 3270:
                                    break
                                elif not gameQueues[queueId]["isCustom"]:
                                    logPrint("请选择一个自定义游戏模式。\nPlease select a custom game mode.")
                                else:
                                    logPrint("警告：您输入了一个非随机选择英雄的游戏模式。您确定要继续吗？（输入任意非空字符串以继续，否则重新输入队列序号。）\nWarning: You selected a non-random game mode. Do you really want to continue? (Submit any non-empty string to continue, or null to change the queueId.)")
                                    queueId_change_str: str = logInput()
                                    queueId_change: bool = not bool(queueId_change_str)
                                    if queueId_change:
                                        logPrint('请输入队列序号：（输入“0”以刷新可用队列信息。输入负数以退出程序。）\nPlease enter the queueId: (Enter "0" to refresh available queue information. Enter any negative number to exit the program.)')
                                    else:
                                        break
                            else:
                                logPrint("无效的对局序号。请重新输入。\nInvalid queueId. Please try again.")
        elif step == 2:
            logPrint("第二步：是否预组队？\nStep 2: Premade?\n1\t是（Yes）\n☆2\t否（No）")
            while True:
                premade_str: str = logInput()
                if premade_str == "" or premade_str[0] == "2":
                    premade = False
                    break
                elif premade_str[0] == "1":
                    premade = True
                    break
                elif premade_str[0] == "0":
                    step -= 2
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 3:
            if premade:
                logPrint("第三步：是否启用多选模式？\nStep 3: Do you want to enable crowd mode?\n1\t是（Yes）\n☆2\t否（No）")
                if not crowd_mode_hine_printed:
                    logPrint("注：在多选模式下，可以指定多名玩家同时想要使用的英雄的英雄序号，而不再只为房主一个人选择。\nNote: Under crowd mode, you can specify the championIds of champions that multiple members want to play, instead of only specifying the ones that only the lobby owner wants.")
                    crowd_mode_hine_printed = True
                while True:
                    crowd_str: str = logInput()
                    if crowd_str == "" or crowd_str[0] == "2":
                        isCrowd = False
                        break
                    elif crowd_str[0] == "1":
                        isCrowd = True
                        break
                    elif crowd_str[0] == "0":
                        step -= 2
                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 4:
            if premade:
                logPrint("第四步：请选择您的角色：\nStep 4: Please select your role:\n1\t房主（Owner）\n2\t房主所在阵营成员（Member that allies with Owner）\n3\t房主对方阵营成员（不可用）【Member against Owner (unavailable)】")
                while True:
                    roleType_str: str = input()
                    if roleType_str == "":
                        continue
                    elif roleType_str[0] == "0":
                        step -= 2
                        break
                    elif roleType_str[0] == "1":
                        roleType = 1
                        break
                    elif roleType_str[0] == "2":
                        roleType = 2
                        break
                    elif roleType_str[0] == "3":
                        logPrint("该选项目前不可用。您已被设置为房主。\nThis option isn't available currently. You're set as the lobby owner instead.")
                        roleType = 1
                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 5:
            logPrint("第五步：是否添加适当间隔？\nStep 5: Do you want to add an interval between requests?\n☆1\t是（Yes）\n2\t否（No）")
            while True:
                lagged_str: str = logInput()
                if lagged_str == "" or lagged_str[0] == "1":
                    lagged = True
                    break
                elif lagged_str[0] == "2":
                    lagged = False
                    break
                elif lagged_str[0] == "0":
                    step -= 2 if premade else 4
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 6:
            if lagged:
                logPrint("第六步：请设置延迟（单位：秒），默认为0.2秒。\nStep 6: Please set a lag (in seconds). Default: 0.2 second.")
                while True:
                    interval_str: str = logInput()
                    if interval_str == "":
                        interval = 0.2 #0.2秒是基于响应速度和可观察性的综合考量（0.2 second is a comprehensive value based on response speed and observability）
                        break
                    else:
                        try:
                            interval = float(interval_str)
                        except ValueError:
                            logPrint("请输入一个小数。\nPlease input a float.")
                        else:
                            if interval == 0:
                                step -= 2 if lagged else 5
                            break
        elif step == 7: #执行程序核心部分（Execute the core part）
            break
        else:
            logPrint("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
            break
        step += 1
    if step == 7:
        await RotateBlindPickCustomAARAM(connection, premade = premade, isCrowd = isCrowd, roleType = roleType, interval = interval, queueId = queueId)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    print("警告：该脚本涉及频繁操作。如果出现异常，请尝试通过调试脚本发送重启用户体验界面的指令。如果您不知道如何操作，请重新启动客户端。\nFrequent operations are involved in this program. If an issue happens, please try posting a request to restart ux through Customized Program 03. If you don't know how, restart the League Client instead.\n重启用户体验界面指令（The request to restart ux）：\nPOST /riotclient/kill-and-restart-ux\n")
    global log, logInput, logPrint
    currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log = LogManager(f"日志（Logs）/Customized Program 22 - ARAM Champ Select Probability Test/{currentTime}.log", "w", encoding = "utf-8")
    logInput = log.logInput
    logPrint = log.logPrint
    await print_summoner_info(connection)
    await prepare_data_resources(connection)
    await main(connection)
    # target_championId, champion_frequency_df = await StartBlindPickCustomAARAM(connection, preset_championIds = [13], premade = False, interval = 0.2, queueId = 3270) #以想玩的英雄启动海克斯大乱斗自定义游戏（Start a custom ARAM: Mayhem game with a wanted champion）
    log.close()

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
