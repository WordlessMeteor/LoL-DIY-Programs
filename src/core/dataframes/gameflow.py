from lcu_driver.connection import Connection
import os, pandas, sys
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.utils.logger import LogManager
from src.utils.patch import Patch
from src.utils.summoner import get_info
from src.utils.format import optimize_bool_display
from src.utils.webRequest import SGPSession
from src.core.config.const import BOT_UUID
from src.core.config.localization import team_colors_int, krarities, augment_rarity, subteam_colors, positions
from src.core.config.headers import TFTGame_summary_header, champSelect_player_header, inGame_player_header, eog_playerstat_data_lol_header, eog_stat_data_tft_header, LoLGame_summary_header, LoLGame_summary_sgp_header
from src.core.dataframes.matchHistory import get_LoLGame_summary, get_game_summary_sgp, sort_LoLGame_summary, sort_LoLGame_summary_sgp, sort_TFTGame_summary

def isChampSelectSession(session: Any) -> bool:
    return isinstance(session, dict) and all(key in session for key in ["actions", "allowBattleBoost", "allowDuplicatePicks", "allowLockedEvents", "allowRerolling", "allowSkinSelection", "allowSubsetChampionPicks", "bans", "benchChampions", "benchEnabled", "boostableSkinCount", "chatDetails", "counter", "disallowBanningTeammateHoveredChampions", "gameId", "hasSimultaneousBans", "hasSimultaneousPicks", "id", "isCustomGame", "isLegacyChampSelect", "isSpectating", "localPlayerCellId", "lockedEventIndex", "myTeam", "pickOrderSwaps", "positionSwaps", "queueId", "rerollsRemaining", "showQuitButton", "skipChampionSelect", "theirTeam", "timer", "trades"]) and all(map(lambda key: isinstance(session[key], list), ["actions", "benchChampions", "myTeam", "pickOrderSwaps", "positionSwaps", "theirTeam", "trades"])) and all(map(lambda key: isinstance(session[key], bool), ["allowBattleBoost", "allowDuplicatePicks", "allowLockedEvents", "allowPlayerPickSameChampion", "allowRerolling", "allowSkinSelection", "allowSubsetChampionPicks", "benchEnabled", "disallowBanningTeammateHoveredChampions", "hasSimultaneousBans", "hasSimultaneousPicks", "isCustomGame", "isLegacyChampSelect", "isSpectating", "showQuitButton", "skipChampionSelect"])) and all(map(lambda key: isinstance(session[key], dict), ["chatDetails", "timer"])) and all(map(lambda key: isinstance(session[key], int), ["boostableSkinCount", "counter", "gameId", "localPlayerCellId", "lockedEventIndex", "queueId", "rerollsRemaining"])) and all(map(lambda key: isinstance(session[key], str), ["id"]))

async def get_gameflow_phase(connection: Connection) -> str: #设计该函数的原因是通过“GET lol-gameflow/v1/gameflow-phase”获得的游戏状态不一定真实，特别是在调用“POST /lol-lobby/v1/lobby/custom/cancel-champ-select”之后（The reason why this function is designed is that the in-game status returned by the API "GET /lol-gameflow/v1/gameflow-phase" may be unreal, especially when "POST /lol-lobby/v1/lobby/custom/cancel-champ-select" is called）
    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase in {"None", "Lobby", "Matchmaking"}:
        lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        search_info: dict[str, Any] = await (await connection.request("GET", "/lol-matchmaking/v1/search")).json()
        champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        champ_select_session_teamBuilder: dict[str, Any] = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/session")).json()
        gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json() #从2026赛季开始，在完成一局游戏后，通过“再来一局”进入小队并在进入下一局游戏之前，游戏会话不会更新。因此，本函数不再依赖游戏会话来判断主召唤师的游戏阶段（Starting from Season 2026, after the summoner finishes a game and clicks "PLAY AGAIN" button, before he enters the next game, gameflow session won't update. Therefore, this function no longer relies on this session to judge the main summoner's gameflow phase）
        inLobby: bool = not "errorCode" in lobby_information
        inQueue: bool = not "errorCode" in search_info and search_info["searchState"] == "Searching"
        inChampSelect: bool = not "errorCode" in champ_select_session or not "errorCode" in champ_select_session_teamBuilder
        # inGame: bool = not "errorCode" in gameflow_session
        if inChampSelect:
            gameflow_phase = "ChampSelect"
        # elif inGame and len(gameflow_session["gameData"]["playerChampionSelections"]) > 0:
        #     gameflow_phase = "Reconnect"
        elif inQueue:
            gameflow_phase = "Matchmaking"
        elif inLobby:
            gameflow_phase = "Lobby"
    return gameflow_phase

async def get_champ_select_session(connection: Connection) -> dict[str, Any]: #设计该函数的原因是在创建随机自定义房间然后通过接口删除房间和匹配状态后，用户会仍然处于英雄选择阶段，但是无法在客户端内进行操作。这时，往往通过传统的接口获取不到英雄选择会话，而通过阵容匹配接口可以获取到。另一方面，传统自定义对局的英雄选择阶段无法通过阵容匹配接口获取其会话，不然清一色地用阵容匹配接口就完事了（The reason why this function is designed is that when the user creates an all random custom lobby, starts the champ select stage and then delete this lobby and the matchmaking state through API, the user is still in a champ select stage, but can't do anything through the client. In that case, the champ select session can't be obtained by the legacy endpoint, but can be obtained by the team-builder endpoint. On the other hand, the champ select session of a legacy custom game can't be obtained through the team-builder endpoint, or I would simply use that endpoint）
    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/session")).json()
    if "errorCode" in champ_select_session and champ_select_session["httpStatus"] == 404 and champ_select_session["message"] == "No champ select session in progress.":
        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    return champ_select_session

async def update_champ_select_session(connection: Connection, old_session: dict[str, Any], force_update: bool = False, max_retry: Optional[int] = None) -> dict[str, Any]:
    '''
    更新英雄选择会话。<br>Update the champ select session.
    
    :param connection: 通过lcu_driver库创建的连接对象。<br>A Connection object created through lcu-driver library.
    :type connection: lcu_driver.connection.Connection
    :param old_session: 旧的英雄选择会话。<br>The old champ select session.<br>如果旧的会话是异常会话，则直接返回，因为没有更新的必要。<br>If the old session is an error session, then it'll be directly returned, for there's no need to update it.
    :type old_session: dict[str, Any]
    :param force_update: 是否通过交换两个召唤师技能的顺序来强制更新英雄选择会话。默认为假。<br>Whether to force the champ select session to update by swapping the order of two summoner spells. False by default.
    :type force_update: bool
    :param max_retry: 最大尝试次数。如果未指定，则始终尝试更新。<br>The limit of attempts. If unspecified, the function will insist on updating.
    :type max_retry: int
    :return: 新的英雄选择会话，或者旧的异常会话。<br>The new champ select session or an old error session.
    :rtype: dict[str, Any]
    '''
    if "errorCode" in old_session:
        return old_session
    if force_update:
        mySelection: dict[str, int] = await (await connection.request("GET", "/lol-champ-select/v1/session/my-selection")).json()
        body: dict[str, int] = {"spell1Id": mySelection["spell2Id"], "spell2Id": mySelection["spell1Id"]}
        response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-champ-select/v1/session/my-selection", data = body)).json() #通过更新召唤师技能来更新英雄选择会话（Update the champ select session by updating the summoner spells）
        body = {"spell1Id": mySelection["spell1Id"], "spell2Id": mySelection["spell2Id"]}
        response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-champ-select/v1/session/my-selection", data = body)).json() #还原召唤师技能顺序（Restore the original order of summoner spells）
        count: int = 0 #尝试次数（Number of attempts）
        while True:
            count += 1
            new_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            if new_session != old_session or max_retry != None and count > max_retry:
                break
    else:
        new_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    return new_session

async def get_champSelect_localPlayer(connection: Connection, current_puuid: str) -> dict[str, Any]: #已弃用（Deprecated）
    champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
    players: list[dict[str, Any]] = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
    for player in players:
        if player["puuid"] == current_puuid:
            return player
    else:
        return {}

async def get_champSelect_player(connection: Connection, cellId: Optional[int] = None) -> dict[str, Any]:
    '''
    从英雄选择会话中提取某个槽位的玩家信息。<br>Get the information of a player with some `cellId` from the champ select session.
    
    :param connection: 通过lcu_driver库创建的连接对象。<br>A Connection object created through lcu-driver library.
    :type connection: lcu_driver.connection.Connection
    :param cellId: 同extract_champSelect_player函数。<br>Same as in `extract_champSelect_player` function.
    :type cellId: int
    :return: 同extract_champSelect_player函数。<br>Same as in `extract_champSelect_player` function.
    :rtype: dict[str, Any]
    '''
    champ_select_session: dict[str, Any] = await get_champ_select_session(connection)
    if "errorCode" in champ_select_session:
        return {}
    else:
        #参数预处理（Parameter pre-process）
        if cellId == None:
            cellId = champ_select_session["localPlayerCellId"]
        return extract_champSelect_player(champ_select_session, cellId = cellId)

def extract_champSelect_player(champ_select_session: dict[str, Any], cellId: Optional[int] = None) -> dict[str, Any]:
    '''
    从英雄选择会话中提取某个槽位的玩家信息。离线使用。<br>Get the information of a player with some `cellId` from the champ select session. For offline use.
    
    :param champ_select_session: 英雄选择会话。<br>Champ select session.
    :type champ_select_session: dict[str, Any]
    :param cellId: 待提取信息的玩家的槽位序号。<br>The cellId of the player to extract the information.<br>如果不指定，则默认获取用户的信息。<br>If unspecified, the function will return the information of the user itself.
    :type cellId: int
    :return: 指定槽位序号的玩家信息。<br>Information of the player with specified `cellId`.
    :rtype: dict[str, Any]
    '''
    #参数预处理（Parameter pre-process）
    if cellId == None:
        cellId = champ_select_session["localPlayerCellId"]
    players: list[dict[str, Any]] = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
    player_cellId_map: dict[int, dict[str, Any]] = {player["cellId"]: player for player in players}
    if cellId in player_cellId_map:
        return player_cellId_map[cellId]
    else:
        return {}

async def sort_ChampSelect_players(connection: Connection, champ_select_session: dict[str, Any], LoLChampions: dict[int, dict[str, Any]], championSkins: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], wardSkins: dict[int, dict[str, Any]], playerMode: int = 1, skipBot: bool = True, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame: #以下代码来自聊天服务脚本（The following code come from Customized Program 16）
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    champSelect_player_header_keys: list[str] = list(champSelect_player_header.keys())
    champSelect_player_data: dict[str, list[Any]] = {key: [] for key in champSelect_player_header_keys}
    #格式校验（Format verification）
    if isChampSelectSession(champ_select_session):
        #所需数据初始化（Initialization of needed data）
        if playerMode == 1:
            players: list[dict[str, Any]] = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
        elif playerMode == 2:
            players = champ_select_session["myTeam"]
        elif playerMode == 3:
            players = champ_select_session["theirTeam"]
        else:
            players = []
        #数据整理核心部分（Data assignment - core part）
        for player in players:
            if player["isHumanoid"] and skipBot:
                continue
            player_info: dict[str, Any] = {}
            if not player["isHumanoid"] and player["nameVisibilityType"] != "HIDDEN":
                player_info_recapture: int = 0
                player_info: dict[str, Any] = await get_info(connection, player["puuid"])
                while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                    logPrint(player_info["message"], verbose = verbose)
                    player_info_recapture += 1
                    logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s, cellId: %d) capture failed! Recapturing this player's information ... Times tried: %d" %(player["cellId"], player["puuid"], player_info_recapture, player["puuid"], player["cellId"], player_info_recapture), verbose = verbose)
                    player_info = await get_info(connection, player["puuid"])
                if not player_info["info_got"]:
                    logPrint(player_info["message"], verbose = verbose)
                    logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s, cellId: %d) capture failed!" %(player["cellId"], player["puuid"], player["puuid"], player["cellId"]), verbose = verbose)
            for i in range(len(champSelect_player_header_keys)):
                key: str = champSelect_player_header_keys[i]
                if i <= 22:
                    if i in {4, 5, 20}: #召唤师信息相关键（Summoner information-related keys）
                        to_append: Any = player[key] if player["nameVisibilityType"] == "HIDDEN" or player["isHumanoid"] else player_info["body"][key] if player_info["info_got"] else ""
                    else:
                        to_append = player[key]
                else:
                    if i == 23: #阵营名称（`team_color`）
                        to_append = team_colors_int[player["team"]]
                    elif i <= 25: #选用英雄相关键（Champion-related keys）
                        to_append = LoLChampions[player["championId"]][key.split()[1]] if player["championId"] in LoLChampions else ""
                    elif i <= 27: #声明英雄相关键（Champion pick intent-related keys）
                        to_append = LoLChampions[player["championPickIntent"]][key.split()[1]] if player["championPickIntent"] in LoLChampions else ""
                    elif i <= 37: #选用皮肤相关键（selected skin-related keys）
                        selectedSkinId = player["selectedSkinId"]
                        if selectedSkinId in championSkins and key.split()[1] in championSkins[selectedSkinId]:
                            if i == 35:
                                to_append = krarities[championSkins[selectedSkinId][key.split()[1]]]
                            else:
                                to_append = championSkins[selectedSkinId][key.split()[1]]
                        else:
                            to_append = ""
                    elif i <= 39: #召唤师技能1相关键（Summoner spell 1-related keys）
                        to_append = spells[player["spell1Id"]][key.split()[1]] if player["spell1Id"] in spells else ""
                    elif i <= 41: #召唤师技能2相关键（Summoner spell 2-related keys）
                        to_append = spells[player["spell2Id"]][key.split()[1]] if player["spell2Id"] in spells else ""
                    else: #饰品相关键（Ward-related keys）
                        if player["wardSkinId"] in wardSkins:
                            if i == 47:
                                to_append = wardSkins[player["wardSkinId"]]["rarities"][0]["rarity"]
                            else:
                                to_append = wardSkins[player["wardSkinId"]][key.split()[1]]
                        else:
                            to_append = ""
                champSelect_player_data[key].append(to_append)
    else:
        logPrint("英雄选择会话格式有误！将生成空表。\nChamp select session format error! An empty dataframe will be returned instead.", verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    champSelect_player_statistics_output_order: list[int] = [21, 23, 1, 4, 20, 5, 13, 19, 15, 10, 9, 8, 7, 0, 6, 2, 24, 25, 3, 26, 27, 17, 38, 39, 18, 40, 41, 16, 28, 29, 35, 30, 31, 32, 33, 34, 36, 37, 22, 42, 43, 47, 46, 44, 45, 14, 11, 12]
    champSelect_player_data_organized: dict[str, list[Any]] = {champSelect_player_header_keys[i]: champSelect_player_data[champSelect_player_header_keys[i]] for i in champSelect_player_statistics_output_order}
    champSelect_player_df: pandas.DataFrame = pandas.DataFrame(data = champSelect_player_data_organized)
    optimize_bool_display(champSelect_player_df)
    champSelect_player_df = pandas.concat([pandas.DataFrame([champSelect_player_header])[champSelect_player_df.columns], champSelect_player_df], ignore_index = True)
    return champSelect_player_df

async def sort_multiChampSelect_players(connection: Connection, sessions: list[dict[str, Any]], queues: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], championSkins: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], wardSkins: dict[int, dict[str, Any]], playerMode: int = 1, skipBot: bool = True, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame:
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    champSelect_player_statistics_output_order: list[int] = [21, 23, 1, 4, 20, 5, 13, 19, 15, 10, 9, 8, 7, 0, 6, 2, 24, 25, 3, 26, 27, 17, 38, 39, 18, 40, 41, 16, 28, 29, 35, 30, 31, 32, 33, 34, 36, 37, 22, 42, 43, 47, 46, 44, 45, 14, 11, 12]
    error_count: int = 0
    if isinstance(sessions, list):
        champSelect_player_dfs: list[pandas.DataFrame] = []
        for champ_select_session in sessions:
            if isChampSelectSession(champ_select_session):
                champSelect_player_df: pandas.DataFrame = await sort_ChampSelect_players(connection, champ_select_session, LoLChampions, championSkins, spells, wardSkins, playerMode = playerMode, skipBot = skipBot, log = log, verbose = verbose)
                matchId: int = champ_select_session["gameId"]
                queueId: int = champ_select_session["queueId"]
                gameModeName: str = queues[queueId]["name"] if queueId in queues else ""
                champSelect_metaDf: pandas.DataFrame = pandas.DataFrame(data = {"gameId": ["对局序号"] + (len(champSelect_player_df) - 1) * [matchId], "queueId": ["队列序号"] + (len(champSelect_player_df) - 1) * [queueId], "gameModeName": ["游戏模式名称"] + (len(champSelect_player_df) - 1) * [gameModeName]})
                champSelect_player_df = pandas.concat([champSelect_metaDf, champSelect_player_df], axis = 1)
                champSelect_player_dfs.append(champSelect_player_df)
            else:
                error_count += 1
        if len(champSelect_player_dfs) > 0:
            if error_count > 0:
                logPrint(f"警告：检测到{error_count}个格式不正确的会话。\nWarning: {error_count} invalid sessions detected.")
            multiChampSelect_player_df: pandas.DataFrame = pandas.concat([champSelect_player_dfs[0].iloc[:1, :]] + list(map(lambda df: df.iloc[1:, :], champSelect_player_dfs)), ignore_index = True)
        else:
            logPrint("未检测到有效会话。程序将返回空表。\nNo valid session detected. An empty table will be returned instead.")
            multiChampSelect_player_df = pandas.DataFrame(champSelect_player_header, index = [0]).iloc[:, champSelect_player_statistics_output_order]
            champSelect_metaDf = pandas.DataFrame(data = {"gameId": ["对局序号"], "queueId": ["队列序号"], "gameModeName": ["游戏模式名称"]})
            multiChampSelect_player_df = pandas.concat([champSelect_metaDf, multiChampSelect_player_df], axis = 1)
    else:
        logPrint("会话列表格式错误。程序将返回空表。\nSession list format error. An empty table will be returned instead.")
        multiChampSelect_player_df = pandas.DataFrame(champSelect_player_header, index = [0]).iloc[:, champSelect_player_statistics_output_order]
        champSelect_metaDf = pandas.DataFrame(data = {"gameId": ["对局序号"], "queueId": ["队列序号"], "gameModeName": ["游戏模式名称"]})
        multiChampSelect_player_df = pandas.concat([champSelect_metaDf, multiChampSelect_player_df], axis = 1)
    return multiChampSelect_player_df

async def sort_inGame_players(connection: Connection, LoLChampions: dict[int, dict[str, Any]], championSkins: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], skipBot: bool = False, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame:
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    inGame_player_header_keys: list[str] = list(inGame_player_header.keys())
    inGame_player_data: dict[str, list[Any]] = {key: [] for key in inGame_player_header_keys}
    gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase in {"InProgress", "Reconnect"}:
        gameflow_session: dict[str, Any] = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
        playerChampionSelections: dict[str, dict[str, Any]] = {player["puuid"]: player for player in gameflow_session["gameData"]["playerChampionSelections"]}
        teamOne: list[dict[str, Any]] = gameflow_session["gameData"]["teamOne"]
        teamTwo: list[dict[str, Any]] = gameflow_session["gameData"]["teamTwo"]
        for player in teamOne + teamTwo:
            player_info: dict[str, Any] = {}
            loadout: dict[str, Any] = {}
            if "puuid" in player and bool(player["puuid"]): #主播模式的玩家的玩家通用唯一识别码是null（The puuid of the player who enables Streamer Mode is null）
                player_info_recapture: int = 0
                player_info = await get_info(connection, player["puuid"])
                while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                    logPrint(player_info["message"], verbose = verbose)
                    player_info_recapture += 1
                    logPrint("参与者序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s, teamParticipantId: %d) capture failed! Recapturing this player's information ... Times tried: %d" %(player["teamParticipantId"], player["puuid"], player_info_recapture, player["puuid"], player["teamParticipantId"], player_info_recapture), verbose = verbose)
                    player_info = await get_info(connection, player["puuid"])
                if not player_info["info_got"]:
                    logPrint(player_info["message"], verbose = verbose)
                    logPrint("参与者序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s, teamParticipantId: %d) capture failed!" %(player["teamParticipantId"], player["puuid"], player["puuid"], player["teamParticipantId"]), verbose = verbose)
                loadout_got: bool = player["puuid"] in playerChampionSelections
                if loadout_got:
                    loadout = playerChampionSelections[player["puuid"]]
            else:
                loadout_got = False
                if skipBot:
                    continue
            for i in range(len(inGame_player_header_keys)):
                key: str = inGame_player_header_keys[i]
                if i <= 29:
                    if i == 4: #选用分路（`selectedPosition`）
                        to_append = positions[player["selectedPosition"]]
                    elif i == 11 or i == 12: #阵营代号和阵营（`teamId` and `team_color`）
                        teamId: int = 100 if player in teamOne else 200 if player in teamTwo else 0
                        to_append: Any = teamId if i == 11 else team_colors_int[teamId]
                    elif i == 13 or i == 14: #英雄相关键（Champion-related keys）
                        to_append = LoLChampions[player["championId"]][key.split()[1]] if player["championId"] in LoLChampions else ""
                    elif i >= 15 and i <= 24: #上次选用皮肤相关键（Last selected skin-related keys）
                        lastSelectedSkinIndex: int = 0 if player["lastSelectedSkinIndex"] == 0 else player["championId"] * 1000 + player["lastSelectedSkinIndex"] #仅考虑非经典皮肤。下同（Only considering non-classic skins. So does the following）
                        if lastSelectedSkinIndex != 0 and lastSelectedSkinIndex in championSkins and key.split()[1] in championSkins[lastSelectedSkinIndex]:
                            if i == 22: #上次选用皮肤品质（`lastSelectedSkin rarity`）
                                to_append = krarities[championSkins[lastSelectedSkinIndex][key.split()[1]]]
                            else:
                                to_append = championSkins[lastSelectedSkinIndex][key.split()[1]]
                        else:
                            to_append = ""
                    elif i == 25 or i == 26: #召唤师图标相关键（Profile icon-related keys）
                        to_append = summonerIcons[player["profileIconId"]].get(key.split()[1], "") if player["profileIconId"] in summonerIcons else ""
                    elif i == 27 or i == 28: #召唤师信息相关键（Summoner information-related keys）
                        to_append = player_info["body"][key] if "puuid" in player and player_info["info_got"] else ""
                    elif i == 29: #电脑玩家（`isHumanoid`）
                        to_append = not "puuid" in player or player["puuid"] == BOT_UUID
                    else:
                        to_append = player.get(key, "") #人类玩家和电脑玩家的数据格式不同（The formats of human and bot players' data aren't the same）
                else:
                    if loadout_got:
                        if i >= 33 and i <= 42: #选用皮肤相关键（Selected skin-related keys）
                            selectedSkinIndex: int = 0 if loadout["selectedSkinIndex"] == 0 else player["championId"] * 1000 + loadout["selectedSkinIndex"]
                            if selectedSkinIndex != 0 and selectedSkinIndex in championSkins and key.split()[1] in championSkins[selectedSkinIndex]:
                                if i == 40: #上次选用皮肤品质（`selectedSkin rarity`）
                                    to_append = krarities[championSkins[selectedSkinIndex][key.split()[1]]]
                                else:
                                    to_append = championSkins[selectedSkinIndex][key.split()[1]]
                            else:
                                to_append = ""
                        elif i >= 43: #召唤师技能相关键（Summoner spell-related keys）
                            spellId: int = loadout["%sId" %(key.split()[0])]
                            to_append = spells[spellId][key.split()[1]] if spellId in spells else ""
                        else:
                            to_append = loadout[key]
                    else:
                        to_append = ""
                inGame_player_data[key].append(to_append)
    inGame_player_statistics_output_order: list[int] = [11, 12, 27, 28, 7, 3, 25, 9, 10, 29, 13, 14, 43, 45, 4, 5, 16, 34]
    inGame_player_data_organized: dict[str, list[Any]] = {inGame_player_header_keys[i]: inGame_player_data[inGame_player_header_keys[i]] for i in inGame_player_statistics_output_order}
    inGame_player_df: pandas.DataFrame = pandas.DataFrame(data = inGame_player_data_organized)
    optimize_bool_display(inGame_player_df)
    inGame_player_df = pandas.concat([pandas.DataFrame([inGame_player_header])[inGame_player_df.columns], inGame_player_df], ignore_index = True)
    return inGame_player_df

async def sort_eog_playerstat_lol_data(connection: Connection, summonerIcons: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], skipBot: bool = False) -> pandas.DataFrame:
    eog_playerstat_data_lol_header_keys: list[str] = list(eog_playerstat_data_lol_header.keys())
    eog_playerstat_data_lol: dict[str, list[Any]] = {key: [] for key in eog_playerstat_data_lol_header_keys}
    eog_stats_block: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/eog-stats-block")).json()
    if not (isinstance(eog_stats_block, dict) and "errorCode" in eog_stats_block):
        for team in eog_stats_block["teams"]:
            for player in team["players"]:
                if player["botPlayer"] and skipBot:
                    continue
                stats: dict[str, Any] = player["stats"]
                for i in range(len(eog_playerstat_data_lol_header_keys)):
                    key: str = eog_playerstat_data_lol_header_keys[i]
                    if i <= 46:
                        if i == 6: #本人标记（`isLocalPlayer`）
                            to_append: Any = "☆" if player["isLocalPlayer"] else ""
                        elif i == 16: #选择角色定位（`selectedPosition`）
                            to_append = positions[player["selectedPosition"]]
                        elif i >= 26 and i <= 39: #装备相关键（Item-related keys）
                            itemId: int = player["items"][int(key.split("_")[0][4:])]
                            to_append = "" if itemId == 0 else LoLItems[itemId][key.split("_")[1]] if itemId in LoLItems else itemId if i <= 32 else ""
                        elif i == 40 or i == 41: #召唤师图标相关键（Summoner icon-related keys）
                            profileIconId: int = player["profileIconId"]
                            to_append = summonerIcons[profileIconId][key.split("_")[1]] if profileIconId in summonerIcons and key.split("_")[1] in summonerIcons[profileIconId] else profileIconId if i == 40 else ""
                        elif i >= 42 and i <= 45: #召唤师技能相关键（Summoner spell-related keys）
                            spellId: int = player[key.split("_")[0] + "Id"]
                            to_append = spells[spellId][key.split("_")[1]] if spellId in spells else spellId if i <= 43 else ""
                        elif i == 46: #阵营（`team_color`）
                            to_append = team_colors_int[player["teamId"]]
                        else:
                            to_append = player[key]
                    else:
                        if i in [50, 51, 57, 121, 145, 146]:
                            to_append = bool(stats.get(key.split()[1], 0))
                        elif i == 147: #击杀得分（`stats KDA`）
                            to_append = "%d/%d/%d" %(stats["CHAMPIONS_KILLED"], stats["NUM_DEATHS"], stats["ASSISTS"]) if all(map(lambda x: x in stats, ["CHAMPIONS_KILLED", "NUM_DEATHS", "ASSISTS"])) else ""
                        elif i >= 148 and i <= 151: #符文系相关键（Perkstyle-related keys）
                            if key.split()[1] in stats:
                                perkstyleId: int = stats[key.split()[1]]
                                to_append = perkstyles[perkstyleId][key.split()[2]] if perkstyleId in perkstyles else perkstyleId if i == 148 or i == 150 else ""
                            else:
                                to_append = ""
                        elif i >= 152 and i <= 169: #符文相关键（Perk-related keys）
                            if key.split()[1] in stats:
                                perkId = stats[key.split()[1]]
                                if perkId in perks:
                                    if i <= 157:
                                        perk_EndOfGameStatDescs: str = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key.split()[1] + "_VAR1"]))
                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key.split()[1] + "_VAR2"]))
                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key.split()[1] + "_VAR3"]))
                                        to_append = perk_EndOfGameStatDescs
                                    else:
                                        to_append = perks[perkId][key.split()[2]]
                                else:
                                    to_append = perkId if i >= 158 and i <= 163 else ""
                            else:
                                to_append = ""
                        elif i >= 170 and i <= 187: #强化符文相关键（Augment-related keys）
                            if key.split()[1] in stats:
                                playerAugmentId: int = stats[key.split()[1]]
                                if playerAugmentId == 0:
                                    to_append = ""
                                elif playerAugmentId in CherryAugments:
                                    if i >= 182:
                                        to_append = augment_rarity[CherryAugments[playerAugmentId][key.split()[2]]]
                                    else:
                                        to_append = CherryAugments[playerAugmentId][key.split()[2]]
                                else:
                                    to_append = playerAugmentId if i >= 170 and i <= 175 else ""
                            else:
                                to_append = ""
                        elif i == 188: #子阵营（`playerSubteamColor`）
                            to_append = subteam_colors[stats["PLAYER_SUBTEAM"]] if "PLAYER_SUBTEAM" in stats else ""
                        elif i == 189 or i == 190: #角色绑定装备相关键（`ROLE_BOUND_ITEM`-related keys）
                            roleBoundItemId: int = stats.get("ROLE_BOUND_ITEM", 0)
                            to_append = "" if roleBoundItemId == 0 else LoLItems[roleBoundItemId][key.split(" ")[2]] if roleBoundItemId in LoLItems else roleBoundItemId if i <= 32 else ""
                        else:
                            to_append = stats.get(key.split()[1], "")
                    eog_playerstat_data_lol[key].append(to_append)
    eog_playerstat_data_lol_statistics_output_order: list[int] = [24, 46, 115, 188, 6, 23, 14, 15, 22, 13, 12, 40, 41, 10, 0, 8, 9, 25, 11, 1, 2, 3, 18, 17, 19, 16, 4, 56, 20, 42, 44, 21, 43, 45, 7, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 117, 189, 190, 147, 99, 170, 182, 176, 100, 171, 183, 177, 101, 172, 184, 178, 102, 173, 185, 179, 103, 174, 186, 180, 104, 175, 187, 181, 49, 69, 47, 54, 55, 134, 123, 126, 97, 59, 137, 124, 96, 58, 136, 53, 125, 127, 128, 132, 133, 130, 131, 98, 60, 138, 129, 141, 144, 143, 118, 142, 52, 61, 62, 64, 63, 139, 48, 122, 65, 66, 67, 68, 135, 70, 148, 149, 71, 150, 151, 72, 73, 74, 75, 158, 164, 152, 76, 77, 78, 79, 159, 165, 153, 80, 81, 82, 83, 160, 166, 154, 84, 85, 86, 87, 161, 167, 155, 88, 89, 90, 91, 162, 168, 156, 92, 93, 94, 95, 163, 169, 157, 119, 120, 145, 121, 50, 51, 146, 57, 116, 140, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]
    eog_playerstat_data_lol_organized: dict[str, list[Any]] = {eog_playerstat_data_lol_header_keys[i]: eog_playerstat_data_lol[eog_playerstat_data_lol_header_keys[i]] for i in eog_playerstat_data_lol_statistics_output_order}
    eog_playerstat_df_lol: pandas.DataFrame = pandas.DataFrame(data = eog_playerstat_data_lol_organized)
    optimize_bool_display(eog_playerstat_df_lol)
    eog_playerstat_df_lol = pandas.concat([pandas.DataFrame([eog_playerstat_data_lol_header])[eog_playerstat_df_lol.columns], eog_playerstat_df_lol], ignore_index = True)
    return eog_playerstat_df_lol

async def sort_eog_stat_tft_data(connection: Connection, summonerIcons: dict[int, dict[str, Any]]) -> pandas.DataFrame: #云顶之弈的电脑玩家无法与人类玩家进行区分（Bot players in TFT can't be distinguished from human players）
    eog_stat_data_tft_header_keys: list[str] = list(eog_stat_data_tft_header.keys())
    eog_stat_data_tft: dict[str, Any] = {key: [] for key in eog_stat_data_tft_header_keys}
    tft_eog_stats: dict[str, Any] = await (await connection.request("GET", "/lol-end-of-game/v1/tft-eog-stats")).json()
    if not (isinstance(tft_eog_stats, dict) and "errorCode" in tft_eog_stats):
        for player in tft_eog_stats["players"]:
            for i in range(len(eog_stat_data_tft_header_keys)):
                key: str = eog_stat_data_tft_header_keys[i]
                if i <= 16:
                    if i == 6: #本人标记（`isLocalPlayer`）
                        to_append: Any = "☆" if player["isLocalPlayer"] else ""
                    elif i >= 15: #召唤师图标相关键（Summoner icon-related keys）
                        to_append = summonerIcons[player["iconId"]][key.split()[1]] if player["iconId"] in summonerIcons and key.split()[1] in summonerIcons[player["iconId"]] else player["iconId"] if i == 15 else ""
                    else:
                        to_append = player[key]
                elif i <= 28: #强化符文相关键（Augment-related keys）
                    if "augments" in player:
                        augment_index: int = int(key.split()[0][7:]) - 1
                        to_append = player["augments"][augment_index][key.split()[1]] if augment_index < len(player["augments"]) else ""
                    else:
                        to_append = ""
                elif i <= 94: #棋子相关键（TFT champion-related keys）
                    unit_index: int = int(key.split()[0][4:])
                    to_append = player["boardPieces"][unit_index][key.split()[1]] if unit_index < len(player["boardPieces"]) else ""
                elif i <= 226: #装备相关键（Item-related keys）
                    unit_index = int(key.split()[0][4:])
                    item_index: int = int(key.split()[1][4:]) - 1
                    to_append = player["boardPieces"][unit_index]["items"][item_index][key.split()[2]] if unit_index < len(player["boardPieces"]) and item_index < len(player["boardPieces"][unit_index]["items"]) else ""
                else:
                    value = player
                    for subkey in key.split():
                        if value == None or not subkey in value:
                            value = ""
                            break
                        else:
                            value = value[subkey]
                    to_append = value
                eog_stat_data_tft[key].append(to_append)
    eog_stat_data_tft_statistics_output_order: list[int] = [6, 14, 10, 11, 13, 8, 4, 15, 16, 12, 5, 7, 229, 227, 228, 3, 2, 9, 235, 236, 234, 230, 231, 232, 233, 0, 20, 26, 23, 17, 21, 27, 24, 18, 22, 28, 25, 19, 1, 29, 32, 33, 31, 30, 34, 96, 98, 97, 95, 100, 102, 101, 99, 104, 106, 105, 103, 35, 38, 39, 37, 36, 40, 108, 110, 109, 107, 112, 114, 113, 111, 116, 118, 117, 115, 41, 44, 45, 43, 42, 46, 120, 122, 121, 119, 124, 126, 125, 123, 128, 130, 129, 127, 47, 50, 51, 49, 48, 52, 132, 134, 133, 131, 136, 138, 137, 135, 140, 142, 141, 139, 53, 56, 57, 55, 54, 58, 144, 146, 145, 143, 148, 150, 149, 147, 152, 154, 153, 151, 59, 62, 63, 61, 60, 64, 156, 158, 157, 155, 160, 162, 161, 159, 164, 166, 165, 163, 65, 68, 69, 67, 66, 70, 168, 170, 169, 167, 172, 174, 173, 171, 176, 178, 177, 175, 71, 74, 75, 73, 72, 76, 180, 182, 181, 179, 184, 186, 185, 183, 188, 190, 189, 187, 77, 80, 81, 79, 78, 82, 192, 194, 193, 191, 196, 198, 197, 195, 200, 202, 201, 199, 83, 86, 87, 85, 84, 88, 204, 206, 205, 203, 208, 210, 209, 207, 212, 214, 213, 211, 89, 92, 93, 91, 90, 94, 216, 218, 217, 215, 220, 222, 221, 219, 224, 226, 225, 223]
    eog_stat_data_tft_organized: dict[str, list[Any]] = {eog_stat_data_tft_header_keys[i]: eog_stat_data_tft[eog_stat_data_tft_header_keys[i]] for i in eog_stat_data_tft_statistics_output_order}
    eog_stat_df_tft: pandas.DataFrame = pandas.DataFrame(data = eog_stat_data_tft_organized)
    optimize_bool_display(eog_stat_df_tft)
    eog_stat_df_tft = pandas.concat([pandas.DataFrame([eog_stat_data_tft_header])[eog_stat_df_tft.columns], eog_stat_df_tft], ignore_index = True)
    return eog_stat_df_tft

async def sort_postgame_players_lol(connection: Connection, sgpSession: SGPSession, matchId: int, queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], puuid: str | list[str] = "", use_sgp: bool = False, useAllVersions: bool = False, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[int, dict[str, Any], pandas.DataFrame]:
    '''
    在已知一场英雄联盟对局序号的情况下，给定辅助数据资源，返回对局数据框。<br>Given a LoL matchId, with auxillary data resources provided, return a match dataframe.
    '''
    if versionList == None:
        versionList = []
    if log == None:
        log = LogManager()
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    match_id: str = f"{platformId}_{matchId}"
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    if use_sgp:
        status, LoLGame_summary = await get_game_summary_sgp(connection, sgpSession, match_id, skipTFT = True)
        if status == 200:
            LoLGame_summary_df: pandas.DataFrame = sort_LoLGame_summary_sgp(LoLGame_summary, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = 1, current_puuid = puuidList, useAllVersions = useAllVersions, versionList = versionList, locale = locale, current_versions = current_versions, unmapped_keys = unmapped_keys, sortStats = False, log = log, verbose = verbose)[0]
        else:
            LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_sgp_header.keys())
            LoLGame_summary_data: dict[str, list[Any]] = {key: [] for key in LoLGame_summary_header_keys}
            LoLGame_summary_statistics_output_order: list[int] = [219, 210, 110, 583, 144, 128, 129, 142, 125, 143, 67, 21, 176, 53, 580, 581, 94, 130, 80, 147, 51, 50, 54, 215, 216, 178, 179, 180, 181, 182, 183, 184, 213, 192, 204, 193, 205, 194, 206, 195, 207, 196, 208, 197, 209, 93, 63, 45, 222, 223, 226, 227, 96, 92, 97, 49, 71, 70, 73, 72, 65, 162, 126, 111, 169, 148, 159, 152, 113, 100, 164, 151, 112, 99, 163, 95, 60, 59, 57, 58, 156, 157, 161, 153, 154, 114, 101, 165, 61, 171, 174, 173, 132, 172, 64, 77, 224, 78, 225, 91, 56, 158, 103, 150, 155, 166, 167, 81, 82, 104, 106, 168, 83, 105, 66, 47, 107, 108, 98, 48, 55, 76, 127, 124, 109, 43, 44, 102, 68, 69, 170, 62, 46, 79, 149, 160, 133, 135, 137, 138, 220, 140, 141, 557, 571, 563, 559, 564, 560, 565, 561, 566, 562, 575, 573, 576, 574, 553, 551, 552, 145, 74, 75, 228, 115, 139, 627, 613, 598, 683, 629, 626, 630, 602, 615, 670, 647, 642, 676, 656, 667, 660, 644, 633, 672, 659, 643, 632, 671, 628, 610, 609, 607, 608, 664, 665, 669, 661, 662, 645, 634, 673, 611, 678, 681, 680, 649, 679, 614, 620, 621, 625, 606, 666, 636, 658, 663, 684, 674, 675, 623, 624, 637, 638, 616, 600, 639, 640, 631, 601, 605, 619, 648, 646, 641, 596, 597, 635, 617, 618, 677, 612, 599, 622, 657, 668, 650, 651, 652, 653, 682, 654, 655, 757, 705, 704, 728, 714, 699, 785, 786, 788, 730, 727, 731, 703, 716, 772, 748, 743, 778, 758, 769, 762, 745, 734, 774, 761, 744, 733, 773, 729, 711, 710, 708, 709, 766, 767, 771, 763, 764, 746, 735, 775, 712, 780, 783, 782, 750, 781, 715, 721, 722, 789, 726, 707, 768, 737, 765, 760, 787, 776, 777, 724, 725, 717, 701, 740, 741, 738, 739, 732, 702, 706, 720, 749, 747, 742, 697, 698, 736, 718, 719, 779, 713, 700, 723, 759, 770, 751, 752, 753, 754, 784, 755, 756, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 372, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 373, 274, 275, 276, 374, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 375, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 376, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521]
            LoLGame_summary_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: LoLGame_summary_data[LoLGame_summary_header_keys[i]] for i in LoLGame_summary_statistics_output_order}
            LoLGame_summary_df = pandas.DataFrame(data = LoLGame_summary_data_organized)
            LoLGame_summary_df = pandas.concat([pandas.DataFrame([LoLGame_summary_sgp_header])[LoLGame_summary_df.columns], LoLGame_summary_df], ignore_index = True)
    else:
        status, LoLGame_summary = await get_LoLGame_summary(connection, matchId, log = log)
        if status == 200:
            LoLGame_summary_df = sort_LoLGame_summary(LoLGame_summary, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = 1, current_puuid = puuidList, useAllVersions = useAllVersions, versionList = versionList, locale = locale, current_versions = current_versions, unmapped_keys = unmapped_keys, sortStats = False, log = log, verbose = verbose)[0]
        else:
            LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
            LoLGame_summary_data: dict[str, list[Any]] = {key: [] for key in LoLGame_summary_header_keys}
            #数据框列排序（Dataframe column sorting）
            LoLGame_summary_statistics_output_order: list[int] = [42, 211, 16, 228, 26, 20, 27, 25, 24, 22, 19, 31, 35, 36, 223, 224, 226, 227, 45, 38, 39, 157, 158, 159, 160, 161, 162, 163, 212, 193, 205, 194, 206, 195, 207, 196, 208, 197, 209, 198, 210, 72, 50, 43, 215, 216, 219, 220, 46, 142, 143, 74, 71, 75, 54, 53, 58, 57, 56, 55, 51, 146, 131, 84, 151, 136, 144, 138, 112, 78, 148, 137, 111, 77, 147, 73, 48, 47, 140, 145, 139, 113, 79, 149, 49, 152, 155, 154, 133, 153, 61, 217, 62, 218, 141, 80, 82, 81, 150, 63, 76, 189, 191, 177, 171, 178, 172, 179, 173, 180, 174, 181, 175, 182, 176, 44, 52, 135, 59, 60, 221, 134, 240, 234, 229, 287, 230, 274, 242, 239, 243, 235, 277, 266, 252, 282, 268, 275, 270, 254, 246, 279, 269, 253, 245, 278, 241, 232, 231, 272, 276, 271, 255, 247, 280, 233, 283, 286, 285, 267, 284, 236, 237, 273, 248, 250, 249, 288, 281, 238, 244, 290, 301, 295, 289, 348, 349, 351, 291, 335, 303, 300, 304, 296, 338, 327, 313, 343, 329, 336, 331, 315, 307, 340, 330, 314, 306, 339, 302, 293, 292, 333, 337, 332, 316, 308, 341, 294, 344, 347, 346, 328, 345, 297, 298, 352, 334, 309, 310, 311, 350, 342, 299, 305]
            LoLGame_summary_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: LoLGame_summary_data[LoLGame_summary_header_keys[i]] for i in LoLGame_summary_statistics_output_order}
            LoLGame_summary_df = pandas.DataFrame(data = LoLGame_summary_data_organized)
            LoLGame_summary_df = pandas.concat([pandas.DataFrame([LoLGame_summary_header])[LoLGame_summary_df.columns], LoLGame_summary_df], ignore_index = True)
    LoLGame_summary_df = LoLGame_summary_df.transpose()
    return (status, LoLGame_summary, LoLGame_summary_df)

async def sort_postgame_players_tft(connection: Connection, sgpSession: SGPSession, matchId: int, queues: dict[int, dict[str, Any]], TFTAugments: dict[str, dict[str, Any]], TFTChampions: dict[str, dict[str, Any]], TFTItems: dict[str, dict[str, Any]], TFTCompanions: dict[str, dict[str, Any]], TFTTraits: dict[str, dict[str, Any]], puuid: str | list[str] = "", useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[int, dict[str, Any], pandas.DataFrame]:
    if versionList == None:
        versionList = []
    if log == None:
        log = LogManager()
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    match_id: str = f"{platformId}_{matchId}"
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    status, TFTGame_summary = await get_game_summary_sgp(connection, sgpSession, match_id, checkLoL = False)
    if status == 200:
        TFTGame_summary_df: pandas.DataFrame = (await sort_TFTGame_summary(connection, TFTGame_summary, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = 1, current_puuid = puuidList, useAllVersions = useAllVersions, versionList = versionList, locale = locale, current_versions = current_versions, unmapped_keys = unmapped_keys, sortStats = False, log = log, verbose = verbose))[0]
    else:
        TFTGame_summary_header_keys: list[str] = list(TFTGame_summary_header.keys())
        TFTGame_summary_data: dict[str, list[Any]] = {key: [] for key in TFTGame_summary_header_keys}
        #数据框列排序（Dataframe column sorting）
        TFTGame_summary_statistics_output_order: list[int] = [40, 19, 55, 46, 47, 43, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 150, 148, 149, 203, 206, 209, 155, 153, 154, 212, 215, 218, 160, 158, 159, 221, 224, 227, 165, 163, 164, 230, 233, 236, 170, 168, 169, 239, 242, 245, 175, 173, 174, 248, 251, 254, 180, 178, 179, 257, 260, 263, 185, 183, 184, 266, 269, 272, 190, 188, 189, 275, 278, 281, 195, 193, 194, 284, 287, 290, 200, 198, 199, 293, 296, 299, 61, 57, 58, 59, 60, 68, 64, 65, 66, 67, 75, 71, 72, 73, 74, 82, 78, 79, 80, 81, 89, 85, 86, 87, 88, 96, 92, 93, 94, 95, 103, 99, 100, 101, 102, 110, 106, 107, 108, 109, 117, 113, 114, 115, 116, 124, 120, 121, 122, 123, 131, 127, 128, 129, 130, 138, 134, 135, 136, 137, 145, 141, 142, 143, 144]
        TFTGame_summary_data_organized: dict[str, list[Any]] = {TFTGame_summary_header_keys[i]: TFTGame_summary_data[TFTGame_summary_header_keys[i]] for i in TFTGame_summary_statistics_output_order}
        TFTGame_summary_df = pandas.DataFrame(data = TFTGame_summary_data_organized)
        TFTGame_summary_df = pandas.concat([pandas.DataFrame([TFTGame_summary_header])[TFTGame_summary_df.columns], TFTGame_summary_df], ignore_index = True)
    TFTGame_summary_df = TFTGame_summary_df.transpose()
    return (status, TFTGame_summary, TFTGame_summary_df)
