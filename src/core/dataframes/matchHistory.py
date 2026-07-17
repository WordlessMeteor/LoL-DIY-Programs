from lcu_driver.connection import Connection
import json, math, os, pandas, re, requests, sys
from urllib.parse import urljoin
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from typing import Any, Optional, Literal
from src.utils.summoner import get_info, get_info_name
from src.utils.logger import LogManager
from src.utils.format import lcuTime, getISOTime, optimize_bool_display, decapitalize
from src.utils.patch import Patch, FindPostPatch
from src.utils.webRequest import requestUrl, SGPSession
from src.core.config.const import BOT_UUID
from src.core.config.headers import LoLHistory_header, LoLGame_summary_header, LoLGame_summary_sgp_header, LoLGame_timeline_header, LoLGame_timeline_sgp_header, LoLGame_event_header, LoLGame_event_sgp_header, TFTHistory_header, TFTGame_summary_header
from src.core.config.localization import language_cdragon, gamemaps, tiers, gameTypes_history, team_colors_int, endOfGameResults, lanes, roles, subteam_colors, augment_rarity, eventTypes, buildingTypes, featTypes, laneTypes, levelUpTypes, killTypes, monsterSubTypes, monsterTypes, dragonSoul_names, transformTypes, towerTypes, wardTypes, traitStyles, rarities, positions

async def get_LoLHistory(connection: Connection, puuid: str, begIndex: int = 0, endIndex: int = 500, retry: int = 3, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[bool, dict[str, Any]]:
    '''
    获取一名召唤师的英雄联盟对局记录。<br>Get a summoner's LoL match history.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param puuid: 要查询的召唤师的玩家通用唯一识别码。<br>Puuid of the summoner to query.
    :type puuid: str
    :param begIndex: 起始索引。默认为0。<br>Beginning index. 0 by default.
    :type begIndex: int
    :param endIndex: 终止索引。默认为500。<br>Ending index. 500 by default.
    
        注：LCU API支持查询最近200场对局。设置成500只是为了规避自然语言和编程语言中的下标差异。<br>Note: LCU API only supports fetching recent 200 matches. Setting this parameter as 500 is just to avoid the difference in the concept of "number" in natural language and "index" in programming language.
    :type endIndex: int
    :param retry: 最大尝试次数。默认为3次。<br>Maximum number of attempts. 3 by default.
    :type retry: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局记录是否成功获取，以及对局记录主体。<br>Whether the match history is successfully fetched, and the match history body.
    :rtype: tuple[bool, dict[str, Any]]
    '''
    if log == None:
        log = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    count: int = 0 #存储内部服务器错误次数（Stores the times of internal server error）
    error_occurred: bool = False
    LoLHistory_get: bool = False
    while True:
        count += 1
        LoLHistory: dict[str, Any] = await (await connection.request("GET", f"/lol-match-history/v1/products/lol/{puuid}/matches?begIndex={begIndex}&endIndex={endIndex}")).json()
        if count > retry:
            logPrint("英雄联盟对局记录获取失败！请等待官方修复对局记录服务！\nLoL match history capture failure! Please wait for Tencent to fix the match history service!", verbose = verbose)
            break
        if "errorCode" in LoLHistory:
            logPrint(LoLHistory, verbose = verbose)
            if LoLHistory["httpStatus"] == 400:
                if "Error getting match list for summoner" in LoLHistory["message"]:
                    LoLHistory_url: str = "%s/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=200" %(connection.address, puuid)
                    logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续。\nPlease open the following website, type in the username and password accordingly and press Enter to continue.\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和上限。\nOr submit two nonnegative integers split by space to respecify the begIndex and endIndex." %(LoLHistory_url, connection.auth_key))
                    cont: str = logInput()
                    if cont == "":
                        continue
                    else:
                        try:
                            begIndex, endIndex = map(int, cont.split())
                        except:
                            break
                        else:
                            continue
                elif "body was empty" in LoLHistory["message"]:
                    logPrint("这位召唤师从5月1日起就没有进行过任何英雄联盟对局。\nThis summoner hasn't played any LoL game yet since May 1st.", verbose = verbose)
                    break
            elif LoLHistory["httpStatus"] == 500:
                if "500 Internal Server Error" in LoLHistory["message"]:
                    if not error_occurred:
                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...", verbose = verbose)
                        error_occurred = True
            logPrint(f"正在进行第{count}次尝试……\nTimes tried: No. {count} ...", verbose = verbose)
        else:
            LoLHistory_get = True
            break
    return (LoLHistory_get, LoLHistory)

async def get_matchIds_sgp(connection: Connection, sgpSession: SGPSession, puuid: str, product: Literal["LoL", "TFT"], begin: int = 0, count: int = 200, batch_size: int = 200, tags: Optional[list[str]] = None, tagsQueryType: Literal["AND", "OR"] = "AND", retry: int = 5, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[bool, list[int]]:
    '''
    获取一名召唤师最近的对局记录的对局序号列表。<br>Get the matchId list of a summoner's recent match history.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param puuid: 要查询的召唤师的玩家通用唯一识别码。<br>Puuid of the summoner to query.
    :type puuid: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）
    :type product: str
    :param begin: 起始索引。默认为0。<br>Beginning index. 0 by default.
    :type begin: int
    :param count: 对局数量。默认为200。<br>Number of matches. 200 by default.
    :type count: int
    :param batch_size: 每一批对局的数量，决定了调用接口的次数。默认为200。<br>The number of matches per batch, which determines the number of times to call API. 200 by default.
    :type batch_size: int
    :param tags: 对局标签。存在于元数据中。<br>Game tags, which exists in the metadata.
    :type tags: list[str]
    :param tagsQueryType: 标签筛选逻辑关系。有以下取值：<br>The logical relationship between the tags to filter matches, which has the following values:
    
        - AND: 且/交
        - OR: 或/并
    :type tagsQueryType: Literal["AND", "OR"]
    :param retry: 最大尝试次数。默认为5次。<br>Maximum number of attempts. 5 by default.
    :type retry: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局序号列表是否成功获取，以及对局序号列表。<br>Whether the matchId list is successfully fetched, and the matchId list.
    :rtype: tuple[bool, list[int]]
    '''
    if log == None:
        log = LogManager()
    if product != "TFT":
        product = "LoL"
    if tags == None:
        tags = []
    logPrint = log.logPrint
    product_lower: str = product.lower()
    uri_tag_part: str = ""
    for tag in tags:
        uri_tag_part += f"&tag={tag}"
    uri_tag_part += f"&tagsQueryType={tagsQueryType}"
    matchIds: list[int] = []
    matchId_get: bool = False #只要一批数据获取成功，那么就算获取到对局序号了（As long as one batch of data is fetched successfully, we consider the matchIds are successfully fetched）
    for i in range(math.ceil(count / batch_size)): #每次调用接口最多获取200场对局。通过多次接口获取对局记录切片，拼接后得到完整的对局记录（Each call of API returns at most 200 matches. By calling the endpoint for multiple times, match history slices are obtained. Merge them to get the complete match history）
        if i * batch_size != count:
            startIndex: int = begin + i * batch_size
            gameCount: int = min(batch_size, count - i * batch_size) #还得是SGP API的count用的地道，通过作差消除了代码上的索引相对自然语言序号的偏移量。怪不得云顶之弈用的也是begin和count（How authentic `count` of SGP API is! Especially because it eliminates the offset between the index spoken in programming and the number spoken in natural language by difference. No wonder TFT match history endpoint uses `begin` and `count`, too）
            match_history_uri: str = f"/match-history-query/v1/products/{product_lower}/player/{puuid}?startIndex={startIndex}&count={gameCount}" + uri_tag_part
            error_count: int = 0 #存储内部服务器错误次数（Stores the times of internal server error）
            stop: bool = False #标记是否放弃后续对局记录的获取（Marks whether to give up fetching subsequent matches）
            # logPrint("正在获取第%d/%d批对局序号……\nFetching matchId Batch %d / %d ..." %(i + 1, math.ceil(count / batch), i + 1, math.ceil(count / batch)))
            while True:
                error_count += 1
                matchIds_slice: list[str] | dict[str, Any] = (await sgpSession.request(connection, "GET", match_history_uri, verbose = verbose)).json()
                if error_count > retry:
                    logPrint("对局序号获取失败！请等待官方修复对局记录服务！\nMatchId capture failure! Please wait for Tencent to fix the match history service!", verbose = verbose)
                    stop = True
                    break
                if isinstance(matchIds_slice, list) and all(map(lambda x: isinstance(x, str), matchIds_slice)):
                    matchId_get = True
                    if len(matchIds_slice) < gameCount: #表明已经到了尽头（Meaning the end is reached）
                        stop = True
                    matchIds += list(map(lambda x: int(x.split("_")[1]), matchIds_slice))
                    break
                else:
                    logPrint(matchIds_slice, verbose = verbose)
                    logPrint(f"正在进行第{error_count}次尝试……\nTimes tried: No. {error_count} ...", verbose = verbose)
            if stop:
                break
        #当`i * batch == count`时，当前切片是0场对局，此时不需要再去调用接口（When `i * batch == count`, the current slice has 0 match, when the API doesn't neet to be called）
    return (matchId_get, matchIds)

async def get_matchSummary_sgp(connection: Connection, sgpSession: SGPSession, puuid: str, product: Literal["LoL", "TFT"], begin: int = 0, count: int = 200, batch_size: int = 200, tags: Optional[list[str]] = None, tagsQueryType: Literal["AND", "OR"] = "AND", retry: int = 5, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[bool, dict[str, Any]]:
    '''
    获取一名召唤师最近的对局记录的概要。<br>Get the summary of a summoner's recent match history.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param puuid: 要查询的召唤师的玩家通用唯一识别码。<br>Puuid of the summoner to query.
    :type puuid: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）
    :type product: str
    :param begin: 起始索引。默认为0。<br>Beginning index. 0 by default.
    :type begin: int
    :param count: 对局数量。默认为200。<br>Number of matches. 200 by default.
    :type count: int
    :param batch_size: 每一批对局的数量，决定了调用接口的次数。默认为200。<br>The number of matches per batch, which determines the number of times to call API. 200 by default.
    :type batch_size: int
    :param tags: 对局标签。存在于元数据中。<br>Game tags, which exists in the metadata.
    :type tags: list[str]
    :param tagsQueryType: 标签筛选逻辑关系。有以下取值：<br>The logical relationship between the tags to filter matches, which has the following values:
    
        - AND: 且/交
        - OR: 或/并
    :type tagsQueryType: Literal["AND", "OR"]
    :param retry: 最大尝试次数。默认为5次。<br>Maximum number of attempts. 5 by default.
    :type retry: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局记录的概要是否成功获取，以及对局概要列表。<br>Whether the match history summary is successfully fetched, and the match summary list.
    :rtype: tuple[bool, dict[Literal["games"], list[dict[str, Any]]]]
    '''
    if log == None:
        log = LogManager()
    if product != "TFT":
        product = "LoL"
    if tags == None:
        tags = []
    logPrint = log.logPrint
    product_lower: str = product.lower()
    uri_tag_part: str = ""
    for tag in tags:
        uri_tag_part += f"&tag={tag}"
    uri_tag_part += f"&tagsQueryType={tagsQueryType}"
    matchSummary: dict[str, list[dict[str, Any]]] = {"games": []}
    matchSummary_get: bool = False
    for i in range(math.ceil(count / batch_size)):
        if i * batch_size != count:
            startIndex: int = begin + i * batch_size
            gameCount: int = min(batch_size, count - i * batch_size)
            match_history_uri: str = f"/match-history-query/v1/products/{product_lower}/player/{puuid}/SUMMARY?startIndex={startIndex}&count={gameCount}" + uri_tag_part
            error_count: int = 0
            stop: bool = False
            logPrint("正在获取第%d/%d批对局记录……\nFetching match history batch %d / %d ..." %(i + 1, math.ceil(count / batch_size), i + 1, math.ceil(count / batch_size)), verbose = verbose)
            while True:
                error_count += 1
                matchSummary_slice: dict[str, list[dict[str, Any]]] = (await sgpSession.request(connection, "GET", match_history_uri, verbose = verbose)).json()
                if error_count > retry:
                    logPrint("对局记录获取失败！请等待官方修复对局记录服务！\nMatch history capture failure! Please wait for Tencent to fix the match history service!", verbose = verbose)
                    stop = True
                    break
                if "games" in matchSummary_slice:
                    matchSummary_get = True
                    if len(matchSummary_slice["games"]) < gameCount:
                        stop = True
                    matchSummary["games"] += matchSummary_slice["games"]
                    break
                else:
                    logPrint(matchSummary_slice, verbose = verbose)
                    logPrint(f"正在进行第{error_count}次尝试……\nTimes tried: No. {error_count} ...", verbose = verbose)
            if stop:
                break
    return (matchSummary_get, matchSummary)

async def get_matchDetails_sgp(connection: Connection, sgpSession: SGPSession, puuid: str, product: Literal["LoL", "TFT"], begin: int = 0, count: int = 200, batch_size: int = 50, tags: Optional[list[str]] = None, tagsQueryType: Literal["AND", "OR"] = "AND", retry: int = 5, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[bool, dict[str, Any]]:
    '''
    获取一名召唤师最近的对局记录的详细信息，即时间轴信息。<br>Get the details of a summoner's recent match history, namely the timeline information.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param puuid: 要查询的召唤师的玩家通用唯一识别码。<br>Puuid of the summoner to query.
    :type puuid: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）
    :type product: str
    :param begin: 起始索引。默认为0。<br>Beginning index. 0 by default.
    :type begin: int
    :param count: 对局数量。默认为200。<br>Number of matches. 200 by default.
    :type count: int
    :param batch_size: 每一批对局的数量，决定了调用接口的次数。默认为50。<br>The number of matches per batch, which determines the number of times to call API. 50 by default.
    :type batch_size: int
    :param tags: 对局标签。存在于元数据中。<br>Game tags, which exists in the metadata.
    :type tags: list[str]
    :param tagsQueryType: 标签筛选逻辑关系。有以下取值：<br>The logical relationship between the tags to filter matches, which has the following values:
    
        - AND: 且/交
        - OR: 或/并
    :type tagsQueryType: Literal["AND", "OR"]
    :param retry: 最大尝试次数。默认为5次。<br>Maximum number of attempts. 5 by default.
    :type retry: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局记录的时间轴信息是否成功获取，以及对局时间轴列表。<br>Whether the match history details are successfully fetched, and the match timeline list.
    :rtype: tuple[bool, dict[Literal["games"], list[dict[str, Any]]]]
    '''
    if log == None:
        log = LogManager()
    if product != "TFT":
        product = "LoL"
    if tags == None:
        tags = []
    logPrint = log.logPrint
    product_lower: str = product.lower()
    uri_tag_part: str = ""
    for tag in tags:
        uri_tag_part += f"&tag={tag}"
    uri_tag_part += f"&tagsQueryType={tagsQueryType}"
    matchDetails: dict[str, list[dict[str, Any]]] = {"games": []}
    matchDetails_get: bool = False
    for i in range(math.ceil(count / batch_size)):
        if i * batch_size != count:
            startIndex: int = begin + i * batch_size
            gameCount: int = min(batch_size, count - i * batch_size)
            match_history_uri: str = f"/match-history-query/v1/products/{product_lower}/player/{puuid}/DETAILS?startIndex={startIndex}&count={gameCount}" + uri_tag_part
            error_count: int = 0
            stop: bool = False
            logPrint("正在获取第%d/%d批对局时间轴……\nFetching match details batch %d / %d ..." %(i + 1, math.ceil(count / batch_size), i + 1, math.ceil(count / batch_size)))
            while True:
                error_count += 1
                matchDetails_slice: dict[str, list[dict[str, Any]]] = (await sgpSession.request(connection, "GET", match_history_uri, verbose = verbose)).json()
                if error_count > retry:
                    logPrint("对局时间轴获取失败！请等待官方修复对局记录服务！\nMatch details capture failure! Please wait for Tencent to fix the match history service!", verbose = verbose)
                    stop = True
                    break
                if "games" in matchDetails_slice:
                    matchDetails_get = True
                    if len(matchDetails_slice["games"]) < gameCount:
                        stop = True
                    matchDetails["games"] += matchDetails_slice["games"]
                    break
                else:
                    logPrint(matchDetails_slice, verbose = verbose)
                    logPrint(f"正在进行第{error_count}次尝试……\nTimes tried: No. {error_count} ...", verbose = verbose)
            if stop:
                break
    return (matchDetails_get, matchDetails)

async def get_LoLGame_summary(connection: Connection, matchId: int, retry: int = 3, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[int, dict[str, Any]]:
    '''
    获取一场对局的概要。<br>Get the summary of a match.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param matchId: 对局序号。<br>GameId.
    :type matchId: int
    :param retry: 最大尝试次数。默认为3次。<br>Maximum number of attempts. 3 by default.
    :type retry: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局概要请求状态码，以及对局概要主体。<br>Status code of the request to get match summary, and the match summary body.
    :rtype: tuple[int, dict[str, Any]]
    '''
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    count: int = 0
    error1_hint_printed: bool = False
    error2_hint_printed: bool = False
    while True:
        count += 1
        LoLGame_summary: dict[str, Any] = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchId}")).json()
        #尝试修复错误（Try to fix the error）
        if "errorCode" in LoLGame_summary:
            logPrint(LoLGame_summary, verbose = verbose)
            status: int = LoLGame_summary["httpStatus"]
            if count > retry:
                logPrint(f"对局{matchId}概要获取失败！\nMatch {matchId} summary capture failure!", verbose = verbose)
                break
            if status == 401: #{'errorCode': 'RPC_ERROR', 'httpStatus': 401, 'implementationDetails': {}, 'message': '{"status":{"message":"Unauthorized","status_code":401}}'}
                logPrint("未授权。请检查服务器状态。\nUnauthorized. Please check the server status.")
                break
            elif status == 403: #{'errorCode': 'RPC_ERROR', 'httpStatus': 403, 'implementationDetails': {}, 'message': '{"status":{"message":"Forbidden","status_code":403}}'}
                logPrint(f"拒绝访问。\nPermission denied.", verbose = verbose)
                break
            elif status == 404:
                logPrint(f"未找到序号为{matchId}的回放文件！将忽略该序号。\nMatch file with matchId {matchId} not found! The program will ignore this matchId.", verbose = verbose)
                break
            elif status == 415:
                if LoLGame_summary["message"] == "could not convert GAMHS data to match-history format":
                    logPrint(f"对局{matchId}概要不可用。请检查该对局是否为云顶之弈对局。\nMatch {matchId} summary not available. Please check if it's a TFT match.", verbose = verbose)
                break
            elif status == 500:
                if "500 Internal Server Error" in LoLGame_summary["message"]:
                    if not error1_hint_printed:
                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...", verbose = verbose)
                        error1_hint_printed = True
            elif status == 503:
                if "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_summary["message"]:
                    if not error2_hint_printed:
                        logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...", verbose = verbose)
                        error2_hint_printed = True
            elif status == 504:
                if "Connection timed out after " in LoLGame_summary["message"]:
                    logPrint("对局概要获取超时！请检查网速状况！\nGame summary fetch operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!", verbose = verbose)
                    break
            logPrint(f"正在第{count}次尝试获取对局{matchId}概要……\nTimes trying to capture Match {matchId}: No. {count} ...", verbose = verbose)
        else:
            status = 200
            break
    return (status, LoLGame_summary)

async def get_LoLGame_timeline(connection: Connection, matchId: int, retry: int = 3, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[int, dict[str, Any]]:
    '''
    获取一场对局的时间轴。<br>Get the timeline of a match.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param matchId: 对局序号。<br>GameId.
    :type matchId: int
    :param retry: 最大尝试次数。默认为3次。<br>Maximum number of attempts. 3 by default.
    :type retry: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局时间轴请求状态码，以及对局时间轴主体。<br>Status code of the request to get match timeline, and the match timeline body.
    :rtype: tuple[int, dict[str, Any]]
    '''
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    count: int = 0
    error1_hint_printed: bool = False
    error2_hint_printed: bool = False
    while True:
        count += 1
        LoLGame_timeline: dict[str, Any] = await (await connection.request("GET", f"/lol-match-history/v1/game-timelines/{matchId}")).json()
        if "errorCode" in LoLGame_timeline:
            logPrint(LoLGame_timeline, verbose = verbose)
            status: int = LoLGame_timeline["httpStatus"]
            if count > retry:
                logPrint(f"对局{matchId}时间轴获取失败！\nMatch {matchId} timeline capture failure!", verbose = verbose)
                break
            if status == 401:
                logPrint("未授权。请检查服务器状态。\nUnauthorized. Please check the server status.")
                break
            elif status == 403:
                logPrint(f"拒绝访问。\nPermission denied.", verbose = verbose)
                break
            elif status == 404:
                logPrint(f"未找到序号为{matchId}的回放文件！将忽略该序号。\nMatch file with matchId {matchId} not found! The program will ignore this matchId.", verbose = verbose)
                break
            elif status == 415:
                if "could not convert GAMHS data to match-history format" in LoLGame_timeline["message"]:
                    # if LoLGame_summary["gameMode"] == "CHERRY":
                    #     logPrint("斗魂竞技场模式不支持查询时间轴！\nTimeline crawling isn't supported in CHERRY matches!", verbose = verbose)
                    # else:
                        logPrint("时间轴加载失败。\nFailed to load timeline.", verbose = verbose)
                break
            elif status == 500:
                if "500 Internal Server Error" in LoLGame_timeline["message"] or "Missing a closing quotation mark in string" in LoLGame_timeline["message"]:
                    if not error1_hint_printed:
                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...", verbose = verbose)
                        error1_hint_printed = True
            elif status == 503:
                if "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_timeline["message"]:
                    if not error2_hint_printed:
                        logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...", verbose = verbose)
                        error2_hint_printed = True
            elif status == 504:
                if "Connection timed out after " in LoLGame_timeline["message"]:
                    logPrint("对局时间轴保存超时！请检查网速状况！\nGame timeline saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!", verbose = verbose)
                    break
            logPrint(f"正在第{count}次尝试获取对局{matchId}时间轴……\nTimes trying to capture Match {matchId} timeline: No. {count} ...", verbose = verbose)
        else:
            status = 200
            break
    return (status, LoLGame_timeline)

async def get_TFTHistory(connection: Connection, puuid: str, begin: int = 0, count: int = 500, retry: int = 3, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[bool, dict[str, Any]]:
    '''
    获取一名召唤师的云顶之弈对局记录。<br>Get a summoner's TFT match history.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param puuid: 要查询的召唤师的玩家通用唯一识别码。<br>Puuid of the summoner to query.
    :type puuid: str
    :param begin: 起始索引。默认为0。<br>Beginning index. 0 by default.
    :type begin: int
    :param count: 对局数量。默认为500。<br>Number of matches. 500 by default.
    :type count: int
    :param retry: 最大尝试次数。默认为3次。<br>Maximum number of attempts. 3 by default.
    :type retry: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局记录是否成功获取，以及对局记录主体。<br>Whether the match history is successfully fetched, and the match history body.
    :rtype: tuple[bool, dict[str, Any]]
    '''
    if log == None:
        log = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    error_count = 0 #存储内部服务器错误次数（Stores the times of internal server error）
    error_occurred = False
    TFTHistory_get = False
    while True:
        error_count += 1
        TFTHistory: dict[str, Any] = await (await connection.request("GET", f"/lol-match-history/v1/products/tft/{puuid}/matches?begin={begin}&count={count}")).json()
        if error_count > retry:
            logPrint("云顶之弈对局记录获取失败！请等待官方修复对局记录服务！\nTFT match history capture failure! Please wait for Tencent to fix the match history service!", verbose = verbose)
            break
        if "errorCode" in TFTHistory:
            logPrint(TFTHistory, verbose = verbose)
            if TFTHistory["httpStatus"] == 400: #以下接口固定返回异常信息（The following endpoint always returns an error）：/lol-match-history/v1/products/tft/current-summoner/matches?begin=0&count=500
                if "Error getting match list for summoner" in TFTHistory["message"]:
                    TFTHistory_url = "%s/lol-match-history/v1/products/tft/%s/matches?begin=0&count=200" %(connection.address, puuid)
                    logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续，或输入任意字符以切换召唤师。\nPlease open the following website, type in the username and password accordingly and press Enter to continue or input anything to switch to another summoner.\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和对局数。\nOr submit two nonnegative integers split by space to respecify the begin and count." %(TFTHistory_url, connection.auth_key))
                    cont = logInput()
                    if cont == "":
                        continue
                    else:
                        try:
                            begin, count = map(int, cont.split())
                        except ValueError:
                            break
                        else:
                            continue
                elif "body was empty" in TFTHistory["message"]:
                    logPrint("这位召唤师从5月1日起就没有进行过任何云顶之弈对局。\nThis summoner hasn't played any TFT game yet since May 1st.", verbose = verbose)
                    break
            elif TFTHistory["httpStatus"] == 500:
                if "500 Internal Server Error" in TFTHistory["message"]:
                    if not error_occurred:
                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...", verbose = verbose)
                        error_occurred = True
            logPrint("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(error_count, error_count), verbose = verbose)
        else:
            TFTHistory_get = True
            break
    return (TFTHistory_get, TFTHistory)

async def get_game_summary_sgp(connection: Connection, sgpSession: SGPSession, match_id: str, checkLoL: bool = True, checkTFT: bool = True, skipTFT: bool = False, retry: int = 3, endpoint_version: int = 1, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[int, dict[str, Any]]:
    '''
    获取一场对局的概要。<br>Get the summary of a match.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param match_id: 大区对局序号。由服务器代号和对局序号通过下划线连接而成。<br>Platform matchId, concatenated from a platformId and a matchId.
    :type match_id: str
    :param checkLoL: 是否核查该对局是否是一场英雄联盟对局。如果为真，则核查，否则跳过英雄联盟对局概要接口。默认为真。<br>Whether to check if a match is a LoL match. If the value is True, then check it, otherwise skip accessing the LoL match summary endpoint. True by default.
    
        仅当用户能够明确一场对局是云顶之弈对局时，才应该将此变量置为假。<br>Only when the match to query is definitely a TFT match should the user set this parameter as False.
    :type checkLoL: bool
    :param checkTFT: 是否核查该对局是否是一场云顶之弈对局。如果为真，则核查，否则跳过云顶之弈对局概要接口。默认为真。<br>Whether to check if a match is a TFT match. If the value is True, then check it, otherwise skip accessing the TFT match summary endpoint. True by default.
    
        该参数在函数体内会被修改：<br>This parameter is prone to change in the function body:
            - 当发现不存在大区对局序号为`match_id`的英雄联盟对局时，该变量会被置为真。<br>When there's not any LoL match with platform matchId `match_id`, this variable is set as True.
            - 当发现`match_id`对应的对局是一场英雄联盟对局时，该变量会被置为假，从而避免程序再次调用云顶之弈对局概要接口。<br>When the match corresponding to `match_id` is a LoL match, this variable is set as False to avoid the program from accessing TFT match summary endpoint.
        
        只有在对局概要网络请求出现文件未找到（404）以外的异常时，用户对此参数做出的选择才能正确生效。<br>Only when an error except FileNotFound (404) occurs will the decision made on this parameter by the user take effect.
    :type checkTFT: bool
    :param skipTFT: 是否强制跳过云顶之弈对局。如果为真，则无论是否成功获取英雄联盟对局概要，都跳过云顶之弈对局概要的获取。默认为假。<br>Whether to force skipping TFT match query. If the value is True, then no matter whether LoL match summary is successfully fetched, the function will skip getting the TFT match summary. False by default.
    
        这个参数在设计上作用相当于`checkLoL`参数。<br>This parameter acts in a similar manner as `checkLoL` parameter by design.
    :type skipTFT: bool
    :param retry: 最大尝试次数。默认为3次。<br>Maximum number of attempts. 3 by default.
    :type retry: int
    :param endpoint_version: 接口版本。有以下取值。<br>Endpoint version, which can be one of the following values:
    
        - （☆）1: GET /match-history-query/v1/products/lol/{match_id}/SUMMARY
        - 3: GET /match-history-query/v3/product/lol/matchId/{match_id}/infoType/summary
    :type endpoint_version: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局概要请求状态码，以及对局概要主体。<br>Status code of the request to get match summary, and the match summary body.
    :rtype: tuple[int, dict[str, Any]]
    '''
    if log == None:
        log = LogManager()
    if endpoint_version != 3:
        endpoint_version = 1
    if endpoint_version == 1:
        game_summary_endpoint_lol: str = f"/match-history-query/v1/products/lol/{match_id}/SUMMARY"
        game_summary_endpoint_tft: str = f"/match-history-query/v1/products/tft/{match_id}/SUMMARY"
    else:
        game_summary_endpoint_lol: str = f"/match-history-query/v3/product/lol/matchId/{match_id}/infoType/summary"
        game_summary_endpoint_tft: str = f"/match-history-query/v3/product/tft/matchId/{match_id}/infoType/summary"
    logPrint = log.logPrint
    status: int = -1
    game_summary: dict[str, Any] = {}
    #检查英雄联盟对局（Check LoL match）
    if checkLoL:
        count: int = 0
        while True:
            count += 1
            source: requests.Response = await sgpSession.request(connection, "GET", game_summary_endpoint_lol, verbose = verbose)
            try:
                game_summary = source.json()
            except requests.exceptions.JSONDecodeError:
                status = source.status_code
                if status == 404: #在使用v3接口时，如果对局未找到，那么会返回一段XML文档（When v3 endpoint is used, if the match isn't found, then an XML document is returned）
                    logPrint(f"未找到序号为{match_id}的英雄联盟回放文件！\nLoL match file with matchId {match_id} not found!", verbose = verbose)
                    checkTFT = True
                    break
                logPrint(f"正在第{count}次尝试获取英雄联盟对局{match_id}概要……\nTimes trying to capture LoL Match {match_id}: No. {count} ...", verbose = verbose)
            else:
                #尝试修复错误（Try to fix the error）
                if "errorCode" in game_summary:
                    logPrint(game_summary, verbose = verbose)
                    status = game_summary["httpStatus"]
                    if count > retry:
                        logPrint(f"英雄联盟对局{match_id}概要获取失败！\nLoL match {match_id} summary capture failure!", verbose = verbose)
                        break
                    if status == 404:
                        if game_summary["errorCode"] == "RESOURCE_NOT_FOUND" and game_summary["message"] == "match file not found" or game_summary == {"httpStatus": 404, "errorCode": "NOT_FOUND", "message": "Not Found", "implementationDetails": "match file not found"}:
                            logPrint(f"未找到序号为{match_id}的英雄联盟回放文件！\nLoL match file with matchId {match_id} not found!", verbose = verbose)
                            checkTFT = True
                            break
                    logPrint(f"正在第{count}次尝试获取英雄联盟对局{match_id}概要……\nTimes trying to capture LoL Match {match_id}: No. {count} ...", verbose = verbose)
                elif "status" in game_summary and isinstance(game_summary["status"], dict) and all(_ in ["message", "status_code"] for _ in game_summary["status"]):
                    logPrint(game_summary, verbose = verbose)
                    status = game_summary["status"]["status_code"]
                    if count > retry:
                        logPrint(f"英雄联盟对局{match_id}概要获取失败！\nLoL match {match_id} summary capture failure!", verbose = verbose)
                        break
                    if status == 503:
                        if game_summary["status"]["message"] == "Service Unavailable - Connection retries limit exceeded. Response timed out.":
                            logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...", verbose = verbose)
                else:
                    status = 200
                    checkTFT = False
                    break
    #检查云顶之弈对局（Check TFT match）
    if not skipTFT and checkTFT:
        count: int = 0
        while True:
            count += 1
            source: requests.Response = await sgpSession.request(connection, "GET", game_summary_endpoint_tft, verbose = verbose)
            try:
                game_summary = source.json()
            except requests.exceptions.JSONDecodeError:
                status = source.status_code
                if status == 404:
                    logPrint(f"未找到序号为{match_id}的云顶之弈回放文件！\nTFT match file with matchId {match_id} not found!", verbose = verbose)
                    break
                logPrint(f"正在第{count}次尝试获取云顶之弈对局{match_id}概要……\nTimes trying to capture TFT Match {match_id}: No. {count} ...", verbose = verbose)
            else:
                #尝试修复错误（Try to fix the error）
                if "errorCode" in game_summary:
                    logPrint(game_summary, verbose = verbose)
                    status = game_summary["httpStatus"]
                    if count > retry:
                        logPrint(f"云顶之弈对局{match_id}概要获取失败！\nTFT match {match_id} summary capture failure!", verbose = verbose)
                        break
                    if status == 404:
                        if game_summary["errorCode"] == "RESOURCE_NOT_FOUND" and game_summary["message"] == "match file not found" or game_summary == {"httpStatus": 404, "errorCode": "NOT_FOUND", "message": "Not Found", "implementationDetails": "match file not found"}:
                            logPrint(f"未找到序号为{match_id}的云顶之弈回放文件！\nTFT match file with matchId {match_id} not found!", verbose = verbose)
                            break
                    logPrint(f"正在第{count}次尝试获取云顶之弈对局{match_id}概要……\nTimes trying to capture TFT Match {match_id}: No. {count} ...", verbose = verbose)
                elif "status" in game_summary and isinstance(game_summary["status"], dict) and all(_ in ["message", "status_code"] for _ in game_summary["status"]):
                    logPrint(game_summary, verbose = verbose)
                    status = game_summary["status"]["status_code"]
                    if count > retry:
                        logPrint(f"云顶之弈对局{match_id}概要获取失败！\nTFT match {match_id} summary capture failure!", verbose = verbose)
                        break
                    if status == 503:
                        if game_summary["status"]["message"] == "Service Unavailable - Connection retries limit exceeded. Response timed out.":
                            logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...", verbose = verbose)
                else:
                    status = 200
                    break
    return (status, game_summary)

async def get_game_timeline_sgp(connection: Connection, sgpSession: SGPSession, match_id: str, checkLoL: bool = True, checkTFT: bool = False, retry: int = 3, endpoint_version: int = 1, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[int, dict[str, Any]]:
    '''
    获取一场对局的时间轴。<br>Get the timeline of a match.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param match_id: 大区对局序号。由服务器代号和对局序号通过下划线连接而成。<br>Platform matchId, concatenated from a platformId and a matchId.
    :type match_id: str
    :param checkLoL: 是否核查该对局是否是一场英雄联盟对局。如果为真，则核查，否则返回空数据。默认为真。<br>Whether to check if a match is a LoL match. If the value is True, then check it, otherwise return empty data. True by default.
    :type checkLoL: bool
    :param checkTFT: 是否核查该对局是否是一场云顶之弈对局。如果为真，则核查，否则跳过云顶之弈对局概要接口。默认为真。<br>Whether to check if a match is a TFT match. If the value is True, then check it, otherwise skip accessing the TFT match summary endpoint. True by default.
    :type checkTFT: bool
    :param retry: 最大尝试次数。默认为3次。<br>Maximum number of attempts. 3 by default.
    :type retry: int
    :param endpoint_version: 接口版本。有以下取值。<br>Endpoint version, which can be one of the following values:
    
        - （☆）1: GET /match-history-query/v1/products/lol/{match_id}/SUMMARY
        - 3: GET /match-history-query/v3/product/lol/matchId/{match_id}/infoType/summary
    :type endpoint_version: int
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局时间轴请求状态码，以及对局时间轴主体。<br>Status code of the request to get match timeline, and the match timeline body.
    :rtype: tuple[int, dict[str, Any]]
    '''
    if log == None:
        log = LogManager()
    if endpoint_version != 3:
        endpoint_version = 1
    if endpoint_version == 1:
        game_timeline_endpoint_lol: str = f"/match-history-query/v1/products/lol/{match_id}/DETAILS"
        game_timeline_endpoint_tft: str = f"/match-history-query/v1/products/tft/{match_id}/DETAILS"
    else:
        game_timeline_endpoint_lol: str = f"/match-history-query/v3/product/lol/matchId/{match_id}/infoType/details"
        game_timeline_endpoint_tft: str = f"/match-history-query/v3/product/tft/matchId/{match_id}/infoType/details"
    logPrint = log.logPrint
    status: int = -1
    game_timeline: dict[str, Any] = {}
    #检查英雄联盟对局（Check LoL match）
    if checkLoL:
        count: int = 0
        while True:
            count += 1
            source: requests.Response = await sgpSession.request(connection, "GET", game_timeline_endpoint_lol, verbose = verbose)
            try:
                game_timeline = source.json()
            except requests.exceptions.JSONDecodeError:
                status = source.status_code
                if status == 404:
                    logPrint(f"未找到序号为{match_id}的英雄联盟回放文件！\nLoL match file with matchId {match_id} not found!", verbose = verbose)
                    break
                logPrint(f"正在第{count}次尝试获取英雄联盟对局{match_id}时间轴……\nTimes trying to capture LoL Match {match_id}: No. {count} ...", verbose = verbose)
            else:
                #尝试修复错误（Try to fix the error）
                if "errorCode" in game_timeline:
                    logPrint(game_timeline, verbose = verbose)
                    status = game_timeline["httpStatus"]
                    if count > retry:
                        logPrint(f"英雄联盟对局{match_id}时间轴获取失败！\nLoL match {match_id} timeline capture failure!", verbose = verbose)
                        break
                    if status == 404:
                        if game_timeline["errorCode"] == "RESOURCE_NOT_FOUND" and game_timeline["message"] == "match file not found" or game_timeline == {"httpStatus": 404, "errorCode": "NOT_FOUND", "message": "Not Found", "implementationDetails": "match file not found"}:
                            logPrint(f"未找到序号为{match_id}的英雄联盟回放文件！\nLoL match file with matchId {match_id} not found!", verbose = verbose)
                            break
                    logPrint(f"正在第{count}次尝试获取英雄联盟对局{match_id}时间轴……\nTimes trying to capture LoL Match {match_id}: No. {count} ...", verbose = verbose)
                elif "status" in game_timeline and isinstance(game_timeline["status"], dict) and all(_ in ["message", "status_code"] for _ in game_timeline["status"]):
                    logPrint(game_timeline, verbose = verbose)
                    status = game_timeline["status"]["status_code"]
                    if count > retry:
                        logPrint(f"英雄联盟对局{match_id}时间轴获取失败！\nLoL match {match_id} information capture failure!", verbose = verbose)
                        break
                    if status == 503:
                        if game_timeline["status"]["message"] == "Service Unavailable - Connection retries limit exceeded. Response timed out.":
                            logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...", verbose = verbose)
                else:
                    status = 200
                    break
    #检查云顶之弈对局（Check TFT match）
    if checkTFT:
        count: int = 0
        while True:
            count += 1
            source: requests.Response = await sgpSession.request(connection, "GET", game_timeline_endpoint_tft, verbose = verbose)
            try:
                game_timeline = source.json()
            except requests.exceptions.JSONDecodeError:
                status = source.status_code
                if status == 404:
                    logPrint(f"未找到序号为{match_id}的云顶之弈回放文件！\nTFT match file with matchId {match_id} not found!", verbose = verbose)
                    break
                logPrint(f"正在第{count}次尝试获取云顶之弈对局{match_id}概要……\nTimes trying to capture TFT Match {match_id}: No. {count} ...", verbose = verbose)
            else:
                #尝试修复错误（Try to fix the error）
                if "errorCode" in game_timeline:
                    logPrint(game_timeline, verbose = verbose)
                    status = game_timeline["httpStatus"]
                    if count > retry:
                        logPrint(f"云顶之弈对局{match_id}概要获取失败！\nTFT match {match_id} summary capture failure!", verbose = verbose) #DETAILS接口返回的内容实际上和SUMMARY接口是一样的（The DETAILS endpoint returns the semantically same content as the SUMMARY endpoint）
                        break
                    if status == 404:
                        if game_timeline["errorCode"] == "RESOURCE_NOT_FOUND" and game_timeline["message"] == "match file not found" or game_timeline == {"httpStatus": 404, "errorCode": "NOT_FOUND", "message": "Not Found", "implementationDetails": "match file not found"}:
                            logPrint(f"未找到序号为{match_id}的云顶之弈回放文件！\nTFT match file with matchId {match_id} not found!", verbose = verbose)
                            break
                    logPrint(f"正在第{count}次尝试获取云顶之弈对局{match_id}概要……\nTimes trying to capture TFT Match {match_id}: No. {count} ...", verbose = verbose)
                elif "status" in game_timeline and isinstance(game_timeline["status"], dict) and all(_ in ["message", "status_code"] for _ in game_timeline["status"]):
                    logPrint(game_timeline, verbose = verbose)
                    status = game_timeline["status"]["status_code"]
                    if count > retry:
                        logPrint(f"云顶之弈对局{match_id}概要获取失败！\nTFT match {match_id} summary capture failure!", verbose = verbose)
                        break
                    if status == 503:
                        if game_timeline["status"]["message"] == "Service Unavailable - Connection retries limit exceeded. Response timed out.":
                            logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...", verbose = verbose)
                else:
                    status = 200
                    break
    return (status, game_timeline)

async def reconstruct_LoLHistory(connection: Connection, LoLMatchIDs: list[int], puuid: str | list[str], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, LoLGame_summary_cache: Optional[dict[int, dict[str, Any]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]: #参数顺序遵循一个原则：首先是连接信息和数据字典，然后是数据资源字典，最后是一些附加参数（The order of parameters follow a principle: first connection and the data dictionary, then data resource dictionaries and finally some supplemental parameters）
    '''
    基于传入的对局序号列表重建英雄联盟对局记录。<br>Reconstruct LoL match history according to LoL matchId list supplied.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param LoLMatchIDs: 英雄联盟对局序号列表。<br>LoL matchId list.
    :type LoLMatchIDs: list[int]
    :param puuid: 玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>Puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type puuid: str
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[int]]
    :param LoLGame_summary_cache: 英雄联盟对局概要缓存。键为对局序号，值为对局概要。<br>LoL match summary cache. Each key is a matchId, and each value is a match summary.
    :type LoLGame_summary_cache: dict[int, dict[str, Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 重建的英雄联盟对局记录数据框，以及游戏队列、召唤师图标、英雄、召唤师技能、英雄联盟装备、符文、符文系和斗魂竞技场强化符文等数据资源的缓存。<br>Reconstructed LoL match history dataframe and data resources like queues, summoner icons, champions, summoner spells, LoL items, perks, perkstyles and Arena augments.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if LoLGame_summary_cache == None or not (isinstance(LoLGame_summary_cache, dict) and all(map(lambda x: isinstance(x, int), LoLGame_summary_cache.keys())) and all(map(lambda x: isinstance(x, dict) and all(map(lambda y: y in {"endOfGameResult", "gameCreation", "gameCreationDate", "gameDuration", "gameId", "gameMode", "gameModeMutators", "gameType", "gameVersion", "mapId", "participantIdentities", "participants", "platformId", "queueId", "seasonId", "teams"}, x.keys())), LoLGame_summary_cache.values()))):
        LoLGame_summary_cache = {}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    LoLHistory_header_keys: list[str] = list(LoLHistory_header.keys())
    LoLHistory_data: dict[str, list[Any]] = {key: [] for key in LoLHistory_header_keys}
    current_puuid_list: list[str] = []
    current_summonerName_list: list[str] = []
    for current_puuid in puuidList:
        info: dict[str, Any] = await get_info(connection, current_puuid)
        if info["info_got"]:
            current_puuid_list.append(info["body"]["puuid"])
            current_summonerName_list.append(get_info_name(info["body"]))
        else:
            logPrint(info["body"], verbose = verbose)
            logPrint(info["message"], verbose = verbose)
    if len(current_puuid_list) == 0:
        logPrint("召唤师信息获取失败。函数将返回空白表。\nSummoner information capture failed! An empty dataframe will be returned instead.", verbose = verbose)
    else:
        #开始赋值（Begin assignment）
        for i in range(len(LoLMatchIDs)): #对于对局记录而言，每场对局对应一条记录（For match history, each record represents a match）
            matchId: int = LoLMatchIDs[i]
            if matchId in LoLGame_summary_cache:
                LoLGame_summary: dict[str, Any] = LoLGame_summary_cache[matchId]
                status: int = 200
            else:
                status, LoLGame_summary = await get_LoLGame_summary(connection, matchId, log = log)
                if status == 200:
                    LoLGame_summary_cache[matchId] = LoLGame_summary
            if status != 200:
                continue
            version: str = LoLGame_summary["gameVersion"]
            bigVersion: str = ".".join(version.split(".")[:2])
            #定位该召唤师（Find the index of this player in a match）
            participantIndices: list[int] = []
            for participantIndex in range(len(LoLGame_summary["participantIdentities"])):
                if LoLGame_summary["participantIdentities"][participantIndex]["player"]["puuid"] in current_puuid_list or LoLGame_summary["participantIdentities"][participantIndex]["player"]["gameName"] + "#" + LoLGame_summary["participantIdentities"][participantIndex]["player"]["tagLine"] in current_summonerName_list:
                    participantIndices.append(participantIndex)
            if len(participantIndices) == 0:
                logPrint("[%d/%d]对局%d不包括主召唤师。已跳过该对局。\nMatch %d doesn't contain the main summoner. Skipped this match." %(i + 1, len(LoLMatchIDs), matchId, matchId), verbose = verbose)
                continue
            #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
            if useAllVersions:
                ##游戏模式（Game mode）
                queueIds_match_list: list[int] = [LoLGame_summary["queueId"]]
                for j in queueIds_match_list:
                    if not j in queues and current_versions["queue"] != bigVersion:
                        queuePatch_adopted: str = bigVersion
                        queue_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, queue_recapture, queuePatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, queuePatch_adopted, queue_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                queue: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                queuePatch_deserted: str = queuePatch_adopted
                                queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                queue_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if queue_recapture < 3:
                                    queue_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                current_versions["queue"] = queuePatch_adopted
                                unmapped_keys["queue"].clear()
                                break
                        break
                ##召唤师图标（Summoner icon）
                summonerIconIds_match_list: list[int] = sorted(set(map(lambda x: LoLGame_summary["participantIdentities"][x]["player"]["profileIcon"], participantIndices)))
                for j in summonerIconIds_match_list:
                    if not j in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                        summonerIconPatch_adopted: str = bigVersion
                        summonerIcon_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, summonerIcon_recapture, summonerIconPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                summonerIcon: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                summonerIconPatch_deserted: str = summonerIconPatch_adopted
                                summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                                summonerIcon_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if summonerIcon_recapture < 3:
                                    summonerIcon_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                                summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                                current_versions["summonerIcon"] = summonerIconPatch_adopted
                                unmapped_keys["summonerIcon"].clear()
                                break
                        break
                ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
                LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: LoLGame_summary["participants"][x]["championId"], participantIndices)))
                for j in LoLChampionIds_match_list:
                    if not j in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                        LoLChampionPatch_adopted: str = bigVersion
                        LoLChampion_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, LoLChampion_recapture, LoLChampionPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                LoLChampion: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                                LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                                LoLChampion_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if LoLChampion_recapture < 3:
                                    LoLChampion_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                                LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                                current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                unmapped_keys["LoLChampion"].clear()
                                break
                        break
                ##召唤师技能（Summoner spells）
                spellIds_match_list: list[int] = sorted(set(map(lambda x: LoLGame_summary["participants"][x]["spell1Id"], participantIndices))) + sorted(set(map(lambda x: LoLGame_summary["participants"][x]["spell2Id"], participantIndices))) #一般情况下，一名玩家不可能带两个相同的召唤师技能（Normally, a player can't take two same spells）
                for j in spellIds_match_list:
                    if not j in spells and current_versions["spell"] != bigVersion and j != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                        spellPatch_adopted: str = bigVersion
                        spell_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, spell_recapture, spellPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, spellPatch_adopted, spell_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                spell: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                spellPatch_deserted: str = spellPatch_adopted
                                spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                                spell_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if spell_recapture < 3:
                                    spell_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                                spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                                current_versions["spell"] = spellPatch_adopted
                                unmapped_keys["spell"].clear()
                                break
                        break
                ##英雄联盟装备（LoL items）
                LoLItemIds_match_list: list[int] = sorted(set(itemId for s in [set(map(lambda x: LoLGame_summary["participants"][x]["stats"].get(key, 0), participantIndices)) for key in ["item0", "item1", "item2", "item3", "item4", "item5", "item6", "roleBoundItem"]] for itemId in s))
                for j in LoLItemIds_match_list:
                    if not j in LoLItems and current_versions["LoLItem"] != bigVersion and j != 0: #空装备序号是0（The itemId of an empty item is 0）
                        LoLItemPatch_adopted: str = bigVersion
                        LoLItem_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, LoLItem_recapture, LoLItemPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                LoLItem: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                LoLItemPatch_deserted: str = LoLItemPatch_adopted
                                LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                                LoLItem_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if LoLItem_recapture < 3:
                                    LoLItem_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                                LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                                current_versions["LoLItem"] = LoLItemPatch_adopted
                                unmapped_keys["LoLItem"].clear()
                                break
                        break
                ##符文（Perks）
                perkIds_match_list: list[int] = sorted(set(perkId for s in [set(map(lambda x: LoLGame_summary["participants"][x]["stats"]["perk" + str(j)], participantIndices)) for j in range(6)] for perkId in s))
                for j in perkIds_match_list:
                    if not j in perks and current_versions["perk"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                        perkPatch_adopted: str = bigVersion
                        perk_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, perk_recapture, perkPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, perkPatch_adopted, perk_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                perk: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                perkPatch_deserted: str = perkPatch_adopted
                                perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                                perk_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if perk_recapture < 3:
                                    perk_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                                perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                                current_versions["perk"] = perkPatch_adopted
                                unmapped_keys["perk"].clear()
                                break
                        break
                ##符文系（Perkstyles）
                perkstyleIds_match_list: list[int] = sorted(list(set(map(lambda x: LoLGame_summary["participants"][x]["stats"]["perkPrimaryStyle"], participantIndices)) | set(map(lambda x: LoLGame_summary["participants"][x]["stats"]["perkSubStyle"], participantIndices))))
                for j in perkstyleIds_match_list:
                    if not j in perkstyles and current_versions["perkstyle"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                        perkstylePatch_adopted: str = bigVersion
                        perkstyle_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, perkstyle_recapture, perkstylePatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                perkstyle: dict[str, Any] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                perkstylePatch_deserted: str = perkstylePatch_adopted
                                perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                                perkstyle_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if perkstyle_recapture < 3:
                                    perkstyle_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                                perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                                current_versions["perkstyle"] = perkstylePatch_adopted
                                unmapped_keys["perkstyle"].clear()
                                break
                        break
                ##斗魂竞技场强化符文（Cherry augments）
                CherryAugmentIds_match_list: list[int] = sorted(set(augmentId for s in [set(map(lambda x: LoLGame_summary["participants"][x]["stats"]["playerAugment" + str(j)], participantIndices)) for j in range(1, 7)] for augmentId in s))
                for j in CherryAugmentIds_match_list:
                    if not j in CherryAugments and current_versions["CherryAugment"] != bigVersion and j != 0:
                        CherryAugmentPatch_adopted: str = bigVersion
                        CherryAugment_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, CherryAugment_recapture, CherryAugmentPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                CherryAugment: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                                CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                                CherryAugment_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if CherryAugment_recapture < 3:
                                    CherryAugment_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                                CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                                current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                unmapped_keys["CherryAugment"].clear()
                                break
                        break
            #下面开始整理数据（Organize data）
            for participantIndex in participantIndices:
                generate_LoLHistory_records(LoLHistory_data, LoLGame_summary, participantIndex, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = i + 1, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
            logPrint("对局记录重查进度（Match history recheck process）：%d/%d\t对局序号（MatchID）： %s" %(i + 1, len(LoLMatchIDs), matchId), print_time = True, verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    LoLHistory_statistics_output_order: list[int] = [0, 25, 19, 26, 5, 3, 13, 4, 11, 6, 14, 10, 15, 9, 35, 36, 46, 38, 39, 160, 161, 162, 163, 164, 165, 166, 215, 217, 219, 63, 224, 136]
    LoLHistory_data_organized: dict[str, list[Any]] = {LoLHistory_header_keys[i]: LoLHistory_data[LoLHistory_header_keys[i]] for i in LoLHistory_statistics_output_order}
    LoLHistory_df: pandas.DataFrame = pandas.DataFrame(data = LoLHistory_data_organized)
    optimize_bool_display(LoLHistory_df)
    LoLHistory_df = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df.columns], LoLHistory_df], ignore_index = True)
    return (LoLHistory_df, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments)

async def reconstruct_LoLHistory_sgp(connection: Connection, sgpSession: SGPSession, LoLMatchIDs: list[int], puuid: str | list[str], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, LoLGame_summary_cache: Optional[dict[int, dict[str, Any]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    '''
    基于传入的对局序号列表重建英雄联盟对局记录。<br>Reconstruct LoL match history according to LoL matchId list supplied.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param LoLMatchIDs: 英雄联盟对局序号列表。<br>LoL matchId list.
    :type LoLMatchIDs: list[int]
    :param puuid: 玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>Puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type puuid: str
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[int]]
    :param LoLGame_summary_cache: 英雄联盟对局概要缓存。键为对局序号，值为对局概要。通过以下接口得到：<br>LoL match summary cache. Each key is a matchId, and each value is a match summary. It's obtained by the following endpoint:
    
        - `GET /match-history-query/v1/products/lol/player/{puuid}/SUMMARY?startIndex={startIndex}&count={count}`
    :type LoLGame_summary_cache: dict[int, dict[str, Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 重建的英雄联盟对局记录数据框，以及游戏队列、召唤师图标、英雄、召唤师技能、英雄联盟装备、符文、符文系和斗魂竞技场强化符文等数据资源的缓存。<br>Reconstructed LoL match history dataframe and data resources like queues, summoner icons, champions, summoner spells, LoL items, perks, perkstyles and Arena augments.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if LoLGame_summary_cache == None or not (isinstance(LoLGame_summary_cache, dict) and all(map(lambda x: isinstance(x, int), LoLGame_summary_cache.keys())) and all(map(lambda x: isinstance(x, dict) and all(map(lambda y: y in {"metadata", "json"}, x.keys())), LoLGame_summary_cache.values()))):
        LoLGame_summary_cache = {}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId: str = current_party["platformId"]
    LoLHistory_header_keys: list[str] = list(LoLHistory_header.keys())
    LoLHistory_data: dict[str, list[Any]] = {key: [] for key in LoLHistory_header_keys}
    current_puuid_list: list[str] = []
    current_summonerName_list: list[str] = []
    for current_puuid in puuidList:
        info: dict[str, Any] = await get_info(connection, current_puuid)
        if info["info_got"]:
            current_puuid_list.append(info["body"]["puuid"])
            current_summonerName_list.append(get_info_name(info["body"]))
        else:
            logPrint(info["body"], verbose = verbose)
            logPrint(info["message"], verbose = verbose)
    if len(current_puuid_list) == 0:
        logPrint("召唤师信息获取失败。函数将返回空白表。\nSummoner information capture failed! An empty dataframe will be returned instead.", verbose = verbose)
    else:
        #开始赋值（Begin assignment）
        for i in range(len(LoLMatchIDs)): #对于对局记录而言，每场对局对应一条记录（For match history, each record represents a match）
            matchId: int = LoLMatchIDs[i]
            match_id: str = f"{platformId}_{matchId}"
            if matchId in LoLGame_summary_cache:
                LoLGame_summary: dict[str, Any] = LoLGame_summary_cache[matchId]
                status: int = 200
            else:
                status, LoLGame_summary = await get_game_summary_sgp(connection, sgpSession, match_id, skipTFT = True, log = log)
                if status == 200:
                    LoLGame_summary_cache[matchId] = LoLGame_summary
            if status != 200 or not LoLGame_summary.get("json"):
                continue
            LoLGame_summary_json: dict[str, Any] = LoLGame_summary["json"]
            #定位该召唤师（Find the index of this player in a match）
            participantIndices: list[int] = []
            for participantIndex in range(len(LoLGame_summary_json["participants"])):
                if LoLGame_summary_json["participants"][participantIndex]["puuid"] in current_puuid_list or LoLGame_summary_json["participants"][participantIndex].get("riotIdGameName", LoLGame_summary_json["participants"][participantIndex].get("riotIdName", "")) + "#" + LoLGame_summary_json["participants"][participantIndex].get("riotIdTagline", "") in current_summonerName_list:
                    participantIndices.append(participantIndex)
            if len(participantIndices) == 0:
                logPrint("[%d/%d]对局%d不包括主召唤师。已跳过该对局。\nMatch %d doesn't contain the main summoner. Skipped this match." %(i + 1, len(LoLMatchIDs), matchId, matchId), verbose = verbose)
                continue
            version: str = LoLGame_summary_json["gameVersion"]
            bigVersion: str = ".".join(version.split(".")[:2])
            #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
            if useAllVersions:
                ##游戏模式（Game mode）
                queueIds_match_list: list[int] = []
                if "queueId" in LoLGame_summary_json:
                    queueIds_match_list.append(LoLGame_summary_json["queueId"])
                for j in queueIds_match_list:
                    if not j in queues and current_versions["queue"] != bigVersion:
                        queuePatch_adopted: str = bigVersion
                        queue_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, queue_recapture, queuePatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, queuePatch_adopted, queue_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                queue: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                queuePatch_deserted: str = queuePatch_adopted
                                queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                queue_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if queue_recapture < 3:
                                    queue_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                current_versions["queue"] = queuePatch_adopted
                                unmapped_keys["queue"].clear()
                                break
                        break
                ##召唤师图标（Summoner icon）
                summonerIconIds_match_set: set[int] = set()
                for participantIndex in participantIndices:
                    participant: dict[str, Any] = LoLGame_summary_json["participants"][participantIndex]
                    if "profileIcon" in participant:
                        summonerIconIds_match_set.add(participant["profileIcon"])
                summonerIconIds_match_list: list[int] = sorted(summonerIconIds_match_set)
                for j in summonerIconIds_match_list:
                    if not j in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                        summonerIconPatch_adopted: str = bigVersion
                        summonerIcon_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, summonerIcon_recapture, summonerIconPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                summonerIcon: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                summonerIconPatch_deserted: str = summonerIconPatch_adopted
                                summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                                summonerIcon_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if summonerIcon_recapture < 3:
                                    summonerIcon_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                                summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                                current_versions["summonerIcon"] = summonerIconPatch_adopted
                                unmapped_keys["summonerIcon"].clear()
                                break
                        break
                ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
                LoLChampionIds_match_set: set[int] = set()
                for participantIndex in participantIndices:
                    participant = LoLGame_summary_json["participants"][participantIndex]
                    if "championId" in participant:
                        LoLChampionIds_match_set.add(participant["championId"])
                LoLChampionIds_match_list: list[int] = sorted(LoLChampionIds_match_set)
                for j in LoLChampionIds_match_list:
                    if not j in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                        LoLChampionPatch_adopted: str = bigVersion
                        LoLChampion_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, LoLChampion_recapture, LoLChampionPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                LoLChampion: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                                LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                                LoLChampion_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if LoLChampion_recapture < 3:
                                    LoLChampion_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                                LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                                current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                unmapped_keys["LoLChampion"].clear()
                                break
                        break
                ##召唤师技能（Summoner spells）
                spellIds_match_set: set[int] = set()
                for participantIndex in participantIndices:
                    participant = LoLGame_summary_json["participants"][participantIndex]
                    for key in ["spell1Id", "spell2Id"]:
                        if key in participant:
                            spellIds_match_set.add(participant[key])
                spellIds_match_list: list[int] = sorted(spellIds_match_set)
                for j in spellIds_match_list:
                    if not j in spells and current_versions["spell"] != bigVersion and j != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                        spellPatch_adopted: str = bigVersion
                        spell_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, spell_recapture, spellPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, spellPatch_adopted, spell_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                spell: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                spellPatch_deserted: str = spellPatch_adopted
                                spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                                spell_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if spell_recapture < 3:
                                    spell_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                                spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                                current_versions["spell"] = spellPatch_adopted
                                unmapped_keys["spell"].clear()
                                break
                        break
                ##英雄联盟装备（LoL items）
                LoLItemIds_match_set: set[int] = set()
                for participantIndex in participantIndices:
                    participant = LoLGame_summary_json["participants"][participantIndex]
                    for key in ["item0", "item1", "item2", "item3", "item4", "item5", "item6", "roleBoundItem"]:
                        if key in participant:
                            LoLItemIds_match_set.add(participant[key])
                LoLItemIds_match_list: list[int] = sorted(LoLItemIds_match_set)
                for j in LoLItemIds_match_list:
                    if not j in LoLItems and current_versions["LoLItem"] != bigVersion and j != 0: #空装备序号是0（The itemId of an empty item is 0）
                        LoLItemPatch_adopted: str = bigVersion
                        LoLItem_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, LoLItem_recapture, LoLItemPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                LoLItem: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                LoLItemPatch_deserted: str = LoLItemPatch_adopted
                                LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                                LoLItem_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if LoLItem_recapture < 3:
                                    LoLItem_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                                LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                                current_versions["LoLItem"] = LoLItemPatch_adopted
                                unmapped_keys["LoLItem"].clear()
                                break
                        break
                ##符文（Perks）
                perkIds_match_set: set[int] = set()
                for participantIndex in participantIndices:
                    participant = LoLGame_summary_json["participants"]
                    if "perks" in participant:
                        if "statPerks" in participant["perks"]:
                            perkIds_match_set |= set(participant["perks"]["statPerks"].values())
                        if "styles" in participant["perks"]:
                            for style in participant["perks"]["styles"]:
                                if "selections" in style:
                                    for perkSelection in style["selections"]:
                                        if "perk" in perkSelection:
                                            perkIds_match_set.add(perkSelection["perk"])
                perkIds_match_list: list[int] = sorted(perkIds_match_set)
                for j in perkIds_match_list:
                    if not j in perks and current_versions["perk"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                        perkPatch_adopted: str = bigVersion
                        perk_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, perk_recapture, perkPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, perkPatch_adopted, perk_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                perk: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                perkPatch_deserted: str = perkPatch_adopted
                                perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                                perk_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if perk_recapture < 3:
                                    perk_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                                perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                                current_versions["perk"] = perkPatch_adopted
                                unmapped_keys["perk"].clear()
                                break
                        break
                ##符文系（Perkstyles）
                perkstyleIds_match_set: set[int] = set()
                for participantIndex in participantIndices:
                    participant = LoLGame_summary_json["participants"][participantIndex]
                    if "perks" in participant and "styles" in participant["perks"]:
                        for style in participant["perks"]["styles"]:
                            if "style" in style:
                                perkstyleIds_match_set.add(style["style"])
                perkstyleIds_match_list: list[int] = sorted(perkstyleIds_match_set)
                for j in perkstyleIds_match_list:
                    if not j in perkstyles and current_versions["perkstyle"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                        perkstylePatch_adopted: str = bigVersion
                        perkstyle_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, perkstyle_recapture, perkstylePatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                perkstyle: dict[str, Any] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                perkstylePatch_deserted: str = perkstylePatch_adopted
                                perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                                perkstyle_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if perkstyle_recapture < 3:
                                    perkstyle_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                                perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                                current_versions["perkstyle"] = perkstylePatch_adopted
                                unmapped_keys["perkstyle"].clear()
                                break
                        break
                ##斗魂竞技场强化符文（Cherry augments）
                CherryAugmentIds_match_set: set[int] = set()
                for participantIndex in participantIndices:
                    participant = LoLGame_summary_json["participants"][participantIndex]
                    for j in range(1, 7):
                        key: str = f"playerAugment{j}"
                        if key in participant:
                            CherryAugmentIds_match_set.add(participant[key])
                CherryAugmentIds_match_list: list[int] = sorted(CherryAugmentIds_match_set)
                for j in CherryAugmentIds_match_list:
                    if not j in CherryAugments and current_versions["CherryAugment"] != bigVersion and j != 0:
                        CherryAugmentPatch_adopted: str = bigVersion
                        CherryAugment_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchId, j, CherryAugment_recapture, CherryAugmentPatch_adopted, j, i + 1, len(LoLMatchIDs), matchId, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                CherryAugment: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                                CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                                CherryAugment_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if CherryAugment_recapture < 3:
                                    CherryAugment_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(LoLMatchIDs), matchId, j, j, i + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                                CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                                current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                unmapped_keys["CherryAugment"].clear()
                                break
                        break
            #下面开始整理数据（Organize data）
            for participantIndex in participantIndices:
                generate_LoLHistory_records_sgp(LoLHistory_data, LoLGame_summary, participantIndex, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = i + 1, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
            logPrint("对局记录重查进度（Match history recheck process）：%d/%d\t对局序号（MatchID）： %s" %(i + 1, len(LoLMatchIDs), matchId), print_time = True, verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    LoLHistory_statistics_output_order: list[int] = [0, 25, 19, 26, 5, 3, 13, 4, 11, 6, 14, 10, 15, 9, 35, 36, 46, 38, 39, 160, 161, 162, 163, 164, 165, 166, 215, 217, 219, 63, 224, 136]
    LoLHistory_data_organized: dict[str, list[Any]] = {LoLHistory_header_keys[i]: LoLHistory_data[LoLHistory_header_keys[i]] for i in LoLHistory_statistics_output_order}
    LoLHistory_df: pandas.DataFrame = pandas.DataFrame(data = LoLHistory_data_organized)
    optimize_bool_display(LoLHistory_df)
    LoLHistory_df = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df.columns], LoLHistory_df], ignore_index = True)
    return (LoLHistory_df, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments)

async def reconstruct_TFTHistory(connection: Connection, sgpSession: SGPSession, TFTMatchIDs: list[int], puuid: str | list[str], queues: dict[int, dict[str, Any]], TFTAugments: dict[str, dict[str, Any]], TFTChampions: dict[str, dict[str, Any]], TFTItems: dict[str, dict[str, Any]], TFTCompanions: dict[str, dict[str, Any]], TFTTraits: dict[str, dict[str, Any]], useAllVersions: bool = False, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[Any]]] = None, TFTGame_summary_cache: Optional[dict[int, dict[str, Any]]] = None, session: Optional[requests.Session] = None, useInfoDict: bool = False, infos: dict[str, dict[str, Any]] = {}, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    '''
    基于传入的对局序号列表重建云顶之弈对局记录。<br>Reconstruct LoL match history according to TFT matchId list supplied.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param TFTMatchIDs: 云顶之弈对局序号列表。<br>TFT matchId list.
    :type TFTMatchIDs: list[int]
    :param puuid: 玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>Puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type puuid: str
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param TFTAugments: 整理后的云顶之弈强化符文数据资源。键是强化符文代码，值是强化符文信息字典。<br>Organized TFT augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始云顶之弈强化符文数据资源可通过以下链接获取：<br>The raw TFT augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/cdragon/tft/en_us.json
    :type TFTAugments: dict[str, dict[str, Any]]
    :param TFTChampions: 整理后的云顶之弈英雄数据资源。键是英雄代码，值是英雄信息字典。<br>Organized TFT champion data resource. Each key is a championid, and each value is a champion information dictionary.
    
        原始云顶之弈英雄数据资源可通过以下链接获取：<br>The raw TFT champion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftchampions.json`
    :type TFTChampions: dict[str, dict[str, Any]]
    :param TFTItems: 整理后的云顶之弈装备信息。键是装备代码，值是装备信息字典。<br>Organized TFT item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始云顶之弈装备数据资源可通过以下链接获取：<br>The raw TFT item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftitems.json`
    :type TFTItems: dict[int, dict[str, Any]]
    :param TFTCompanions: 整理后的小小英雄信息。键是小小英雄代码，值是小小英雄信息字典。<br>Organized companion data resource. Each key is a companionId, and each value is a companion information dictionary.
    
        原始小小英雄数据资源可通过以下链接获取：<br>The raw companion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/companions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/companions.json`
    :type TFTCompanions: dict[str, dict[str, Any]]
    :param TFTTraits: 整理后的云顶之弈羁绊信息。键是羁绊代码，值是羁绊信息字典。<br>Organized TFT trait data resource. Each key is a traitId, and each value is a trait information dictionary.
    
        原始云顶之弈羁绊数据资源可通过以下链接获取：<br>The raw TFT trait data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tfttraits.json`
    :type TFTTraits: dict[str, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param TFTGame_summary_cache: 云顶之弈对局概要缓存。键为对局序号，值为对局概要。通过以下接口得到：<br>TFT match summary cache. Each key is a matchId, and each value is a match summary. It's obtained by the following endpoint:
    
        - `GET /match-history-query/v1/products/tft/player/{puuid}/SUMMARY?startIndex={startIndex}&count={count}`
    :type TFTGame_summary_cache: dict[int, dict[str, Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param useInfoDict: 是否使用召唤师信息缓存字典。默认为否。<br>Whether to use a summoner information cache dictionary. False by default.
    :type useInfoDict: bool
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 重建的云顶之弈对局记录数据框，以及游戏队列、召唤师图标、英雄、召唤师技能、英雄联盟装备、符文、符文系和斗魂竞技场强化符文等数据资源的缓存。<br>Reconstructed TFT match history dataframe and data resources like queues, summoner icons, champions, summoner spells, LoL items, perks, perkstyles and Arena augments.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "TFTAugment": "", "TFTChampion": "", "TFTItem": "", "TFTCompanion": "", "TFTTrait": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
    if TFTGame_summary_cache == None or not (isinstance(TFTGame_summary_cache, dict) and all(map(lambda x: isinstance(x, int), TFTGame_summary_cache.keys())) and all(map(lambda x: isinstance(x, dict) and all(map(lambda y: y in {"metadata", "json"}, x.keys())), TFTGame_summary_cache.values()))):
        TFTGame_summary_cache = {}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    ##注意到infos没有做类似处理。因此，一旦出现不同函数调用间共享了infos参数……这是好事啊！（Note that `infos` parameter isn't processed in this manner. Hence, once it's shared between different function calls ... well, that's exactly what I want）
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId: str = current_party["platformId"]
    logPrint = log.logPrint
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    version_re: re.Pattern[str] = re.compile(r"\d+\.\d+\.\d+\.\d+")
    TFTHistory_header_keys: list[str] = list(TFTHistory_header.keys())
    TFTHistory_data: dict[str, list[Any]] = {key: [] for key in TFTHistory_header_keys} #云顶之弈对局概要各项目初始化（Initialize every feature / column of TFT match summary）
    current_puuid_list: list[str] = []
    current_summonerName_list: list[str] = []
    for current_puuid in puuidList:
        info: dict[str, Any] = await get_info(connection, current_puuid)
        if info["info_got"]:
            current_puuid_list.append(info["body"]["puuid"])
            current_summonerName_list.append(get_info_name(info["body"]))
        else:
            logPrint(info["body"], verbose = verbose)
            logPrint(info["message"], verbose = verbose)
    if len(current_puuid_list) == 0:
        logPrint("召唤师信息获取失败。函数将返回空白表。\nSummoner information capture failed! An empty dataframe will be returned instead.", verbose = verbose)
    else:
        for i in range(len(TFTMatchIDs)):
            matchId: int = TFTMatchIDs[i]
            match_id: str = f"{platformId}_{matchId}"
            if matchId in TFTGame_summary_cache:
                TFTGame_summary: dict[str, Any] = TFTGame_summary_cache[matchId]
                status: int = 200
            else:
                status, TFTGame_summary = await get_game_summary_sgp(connection, sgpSession, match_id, checkLoL = False, checkTFT = True, log = log, verbose = verbose)
                if status == 200:
                    TFTGame_summary_cache[matchId] = TFTGame_summary
            if status != 200 or not TFTGame_summary.get("json"): #在没有json数据的情况下，当然不可能找得到主召唤师（Without json data, the program certainly can't find the main summoner）
                continue
            TFTGame_summary_json: dict[str, Any] = TFTGame_summary["json"]
            participantIndices: list[int] = []
            if bool(TFTGame_summary_json):
                for participantIndex in range(len(TFTGame_summary_json["participants"])):
                    if TFTGame_summary_json["participants"][participantIndex]["puuid"] in current_puuid_list:
                        participantIndices.append(participantIndex)
                if len(participantIndices) == 0:
                    logPrint("[%d/%d]对局%d不包括主召唤师。已跳过该对局。\nMatch %d doesn't contain the main summoner. Skipped this match." %(i + 1, len(TFTMatchIDs), matchId, matchId), verbose = verbose)
                    continue
            else:
                logPrint("[%d/%d]对局%d数据不存在。已跳过该对局。\nMatch %d doesn't exist. Skipped this match." %(i + 1, len(TFTMatchIDs), matchId, matchId), verbose = verbose)
                continue
            TFTGameVersion: str = version_re.search(TFTGame_summary_json["game_version"]).group()
            TFTGamePatch: str = ".".join(TFTGameVersion.split(".")[:2]) #由于需要通过这部分代码事先获取所有对局的版本，因此无论如何，这部分代码都要放在与从CommunityDragon重新获取云顶之弈数据相关的代码前面（Since game patches are captured here, by all means should this part of code be in front of the code relevant to regetting TFT data from CommunityDragon）
            #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
            if useAllVersions:
                ##游戏模式（Game mode）
                queueIds_match_list: list[int] = [TFTGame_summary_json["queue_id"]]
                for j in queueIds_match_list:
                    if not j in queues and current_versions["queue"] != TFTGamePatch:
                        queuePatch_adopted: str = TFTGamePatch
                        queue_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, queue_recapture, queuePatch_adopted, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], queuePatch_adopted, queue_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                queue: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                queuePatch_deserted: str = queuePatch_adopted
                                queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                queue_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if queue_recapture < 3:
                                    queue_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                current_versions["queue"] = queuePatch_adopted
                                unmapped_keys["queue"].clear()
                                break
                        break
                ##云顶之弈强化符文（TFT augments）
                TFTAugmentIds_match_list: list[str] = sorted(set(augmentId for lst in list(map(lambda x: TFTGame_summary_json["participants"][x]["augments"] if "augments" in TFTGame_summary_json["participants"][x] else [], participantIndices)) for augmentId in lst)) #`if "augments" in x`的作用是防止早期云顶之弈对局无强化符文导致程序报错（`if "augments" in x` is used here because some early TFT matches don't contain augments and result in KeyErrors consequently）
                for j in TFTAugmentIds_match_list:
                    if not j in TFTAugments and current_versions["TFTAugment"] != TFTGamePatch:
                        TFTAugmentPatch_adopted: str = TFTGamePatch
                        TFTAugment_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nAugment information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT augments of Patch %s ... Times tried: %d." %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, TFTAugment_recapture, TFTAugmentPatch_adopted, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTBasic: dict[str, Any] = source.json()
                            except requests.exceptions.JSONDecodeError: #存在版本合并更新的情况（Situation like merged update exists）
                                TFTAugmentPatch_deserted: str = TFTAugmentPatch_adopted
                                TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                                TFTAugment_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                            except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                if TFTAugment_recapture < 3:
                                    TFTAugment_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                                TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                                current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                unmapped_keys["TFTAugment"].clear()
                                break
                        break
                ##云顶之弈小小英雄（TFT companions）
                TFTCompanionIds_match_list: list[str] = sorted(set(map(lambda x: TFTGame_summary_json["participants"][x]["companion"]["content_ID"], participantIndices)))
                for j in TFTCompanionIds_match_list:
                    if not j in TFTCompanions and current_versions["TFTCompanion"] != TFTGamePatch:
                        TFTCompanionPatch_adopted: str = TFTGamePatch
                        TFTCompanion_recapture = 1
                        logPrint("第%d/%d场对局（对局序号：%d）小小英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的小小英雄信息……\nTFT companion information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT companions of Patch %s ... Times tried: %d." %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, TFTCompanion_recapture, TFTCompanionPatch_adopted, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(TFTCompanionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTCompanion: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTCompanionPatch_deserted: str = TFTCompanionPatch_adopted
                                TFTCompanionPatch_adopted = FindPostPatch(Patch(TFTCompanionPatch_adopted), versionList)
                                TFTCompanion_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTCompanionPatch_deserted, TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_deserted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if TFTCompanion_recapture < 3:
                                    TFTCompanion_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的小小英雄信息……\nYour network environment is abnormal! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的小小英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the companion (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的小小英雄信息。\nTFT companion information changed to Patch %s." %(TFTCompanionPatch_adopted, TFTCompanionPatch_adopted), verbose = verbose)
                                TFTCompanions = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanion}
                                current_versions["TFTCompanion"] = TFTCompanionPatch_adopted
                                unmapped_keys["TFTCompanion"].clear()
                                break
                        break
                ##云顶之弈羁绊（TFT Traits）
                TFTTraitIds_match_list: list[str] = sorted(set(traitId for s in [set(map(lambda x: x["name"], TFTGame_summary_json["participants"][j]["traits"])) for j in participantIndices] for traitId in s))
                for j in TFTTraitIds_match_list:
                    if not j in TFTTraits and current_versions["TFTTrait"] != TFTGamePatch:
                        TFTTraitPatch_adopted: str = TFTGamePatch
                        TFTTrait_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）羁绊信息（%s）获取失败！正在第%d次尝试改用%s版本的羁绊信息……\nTFT trait information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT traits of Patch %s ... Times tried: %d." %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, TFTTrait_recapture, TFTTraitPatch_adopted, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(TFTTraitPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTTrait: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTTraitPatch_deserted: str = TFTTraitPatch_adopted
                                TFTTraitPatch_adopted = FindPostPatch(Patch(TFTTraitPatch_adopted), versionList)
                                TFTTrait_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTraitPatch_deserted, TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_deserted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if TFTTrait_recapture < 3:
                                    TFTTrait_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的羁绊信息……\nYour network environment is abnormal! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的羁绊信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the trait (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的羁绊信息。\nTFT trait information changed to Patch %s." %(TFTTraitPatch_adopted, TFTTraitPatch_adopted), verbose = verbose)
                                TFTTraits = {}
                                for trait_iter in TFTTrait:
                                    trait_id: str = trait_iter["trait_id"]
                                    conditional_trait_sets: dict[str, Any] = {}
                                    if "conditional_trait_sets" in trait_iter: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
                                        for conditional_trait_set in trait_iter["conditional_trait_sets"]:
                                            style_idx = conditional_trait_set["style_idx"]
                                            conditional_trait_sets[style_idx] = conditional_trait_set
                                    trait_iter["conditional_trait_sets"] = conditional_trait_sets
                                    TFTTraits[trait_id] = trait_iter
                                current_versions["TFTTrait"] = TFTTraitPatch_adopted
                                unmapped_keys["TFTTrait"].clear()
                                break
                        break
                ##云顶之弈英雄（TFT champions）
                TFTChampionIds_match_list: list[str] = sorted(set(championId for s in [set(map(lambda x: x["character_id"], TFTGame_summary_json["participants"][j]["units"])) for j in participantIndices] for championId in s))
                for j in TFTChampionIds_match_list:
                    if not j in TFTChampions and not j.lower() in set(map(lambda x: x.lower(), TFTChampions.keys())) and current_versions["TFTChampion"] != TFTGamePatch:
                        TFTChampionPatch_adopted: str = TFTGamePatch
                        TFTChampion_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的棋子信息……\nTFT champion (%s) information of Match %d / %d (matchId: %d) capture failed! Changing to TFT champions of Patch %s ... Times tried: %d." %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, TFTChampion_recapture, TFTChampionPatch_adopted, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(TFTChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTChampion: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTChampionPatch_deserted: str = TFTChampionPatch_adopted
                                TFTChampionPatch_adopted = FindPostPatch(Patch(TFTChampionPatch_adopted), versionList)
                                TFTChampion_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampionPatch_deserted, TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_deserted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if TFTChampion_recapture < 3:
                                    TFTChampion_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的棋子信息……\nYour network environment is abnormal! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）将采用原始数据！\nNetwork error! The original data will be used for Match %d / %d (matchId: %d)!" %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的棋子信息。\nTFT champion information changed to Patch %s." %(TFTChampionPatch_adopted, TFTChampionPatch_adopted), verbose = verbose)
                                TFTChampions = {}
                                if Patch(TFTChampionPatch_adopted) < Patch("13.17"): #从13.17版本开始，CommunityDragon数据库中关于云顶之弈棋子的数据格式发生微调（Since Patch 13.17, the format of TFT Champion data in CommunityDragon database has been modified）
                                    for TFTChampion_iter in TFTChampion:
                                        champion_name: str = TFTChampion_iter["character_id"]
                                        TFTChampions[champion_name] = TFTChampion_iter
                                else:
                                    for TFTChampion_iter in TFTChampion:
                                        champion_name = TFTChampion_iter["name"]
                                        TFTChampions[champion_name] = TFTChampion_iter["character_record"] #请注意该语句与4行之前的语句的差异，并看看一开始准备数据文件时使用的是哪一种——其实你应该猜的出来（Have you noticed the difference between this statement and the statement that is 4 lines above from this statement? Also, check which statement I chose for the beginning, when I prepared the data resources. Actually, you should be able to speculate it without referring to the code）
                                current_versions["TFTChampion"] = TFTChampionPatch_adopted
                                unmapped_keys["TFTChampion"].clear()
                                break
                        break
                ##云顶之弈装备（TFT items）
                s: set[str] = set()
                for j in participantIndices:
                    for unit in TFTGame_summary_json["participants"][j]["units"]:
                        if "itemNames" in unit:
                            s |= set(unit["itemNames"])
                        elif "items" in unit:
                            s |= set(unit["items"])
                TFTItemIds_match_list: list[str] = sorted(s)
                for j in TFTItemIds_match_list:
                    if not j in TFTItems and not j in TFTAugments:
                        if current_versions["TFTItem"] != TFTGamePatch:
                            TFTItemPatch_adopted: str = TFTGamePatch
                            TFTItem_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT items of Patch %s ... Times tried: %d." %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, TFTItem_recapture, TFTItemPatch_adopted, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    TFTItem: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    TFTItemPatch_deserted: str = TFTItemPatch_adopted
                                    TFTItemPatch_adopted = FindPostPatch(Patch(TFTItemPatch_adopted), versionList)
                                    TFTItem_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if TFTItem_recapture < 3:
                                        TFTItem_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的装备信息（%d）将采用原始数据！\nNetwork error! The original data will be used for the item (%d) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的云顶之弈装备信息。\nTFT item information changed to Patch %s." %(TFTItemPatch_adopted, TFTItemPatch_adopted), verbose = verbose)
                                    TFTItems = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItem}
                                    current_versions["TFTItem"] = TFTItemPatch_adopted
                                    unmapped_keys["TFTItem"].clear()
                                    break
                        #由于云顶之弈基础数据中也包含装备信息，这里将重新获取对局版本的云顶之弈基础数据（Because TFT basic data contain item data, here the program recaptures TFT basic data of the match version）
                        if current_versions["TFTAugment"] != TFTGamePatch:
                            TFTAugmentPatch_adopted = TFTGamePatch
                            TFTAugment_recapture = 1
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    TFTBasic = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                    TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                                    TFTAugment_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                    if TFTAugment_recapture < 3:
                                        TFTAugment_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                                    TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                                    current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                    unmapped_keys["TFTAugment"].clear()
                                    break
                        break
            for participantIndex in participantIndices:
                await generate_TFTHistory_records(connection, TFTHistory_data, TFTGame_summary, participantIndex, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = i + 1, unmapped_keys = unmapped_keys, useInfoDict = useInfoDict, infos = infos, log = log, verbose = verbose)
            logPrint("对局记录重查进度（Match history recheck process）：%d/%d\t对局序号（MatchID）： %s" %(i + 1, len(TFTMatchIDs), matchId), print_time = True, verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    TFTHistory_statistics_output_order: list[int] = [0, 46, 47, 5, 14, 15, 16, 6, 10, 18, 8, 17, 7, 13, 12, 11, 306, 304, 40, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 149, 147, 148, 202, 205, 208, 154, 152, 153, 211, 214, 217, 159, 157, 158, 220, 223, 226, 164, 162, 163, 229, 232, 235, 169, 167, 168, 238, 241, 244, 174, 172, 173, 247, 250, 253, 179, 177, 178, 256, 259, 262, 184, 182, 183, 265, 268, 271, 189, 187, 188, 274, 277, 280, 194, 192, 193, 283, 286, 289, 199, 197, 198, 292, 295, 298, 60, 56, 57, 58, 59, 67, 63, 64, 65, 66, 74, 70, 71, 72, 73, 81, 77, 78, 79, 80, 88, 84, 85, 86, 87, 95, 91, 92, 93, 94, 102, 98, 99, 100, 101, 109, 105, 106, 107, 108, 116, 112, 113, 114, 115, 123, 119, 120, 121, 122, 130, 126, 127, 128, 129, 137, 133, 134, 135, 136, 144, 140, 141, 142, 143]
    TFTHistory_data_organized: dict[str, list[Any]] = {TFTHistory_header_keys[i]: TFTHistory_data[TFTHistory_header_keys[i]] for i in TFTHistory_statistics_output_order}
    TFTHistory_df: pandas.DataFrame = pandas.DataFrame(data = TFTHistory_data_organized)
    optimize_bool_display(TFTHistory_df)
    TFTHistory_df = pandas.concat([pandas.DataFrame([TFTHistory_header])[TFTHistory_df.columns], TFTHistory_df], ignore_index = True)
    return (TFTHistory_df, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits)

def generate_LoLHistory_records(LoLHistory_data: dict[str, list[Any]], LoLGame_summary: dict[str, Any], participantIndex: int, queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], gameIndex: int = 1, unmapped_keys: Optional[dict[str, set[Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> dict[str, list[Any]]: #由于字典作为参数的引用传递特性，在使用该函数时可以不用将返回结果保存到一个变量中（Due to the pass-by-reference feature of a dictionary parameter, the result returned by this function doesn't have to be stored as a variable）
    '''
    向英雄联盟对局记录数据中追加记录。<br>Append records to LoL match history data.
    
    :param LoLHistory_data: 英雄联盟对局记录数据。记录将追加到其中。<br>LoL match history data. Records are appended into it.
    :type LoLHistory_data: dict[str, list[Any]]
    :param LoLGame_summary: 英雄联盟对局概要。通过以下LCU接口得到：<br>LoL match summary, obtained through the following LCU endpoint:
    
        - `GET /lol-match-history/v1/games/{gameId}`
    :type LoLGame_summary: dict[str, Any]
    :param participantIndex: 主召唤师索引。从0开始。<br>The index of the main summoner, which starts from 0.
    :type participantIndex: int
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 追加数据后的英雄联盟对局记录数据。<br>LoL match history data after appending.
    :rtype: dict[str, list[Any]]
    '''
    #参数预处理（Parameter pre-processing）
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    matchId: int = LoLGame_summary["gameId"]
    version: str = LoLGame_summary["gameVersion"]
    stats: dict[str, int | bool] = LoLGame_summary["participants"][participantIndex]["stats"]
    timeline: dict[str, Any] = LoLGame_summary["participants"][participantIndex]["timeline"]
    LoLHistory_header_keys: list[str] = list(LoLHistory_header.keys())
    for i in range(len(LoLHistory_header_keys)):
        key: str = LoLHistory_header_keys[i]
        if i == 0:
            to_append: Any = gameIndex
        elif i <= 15:
            if i == 1: #对局终止情况（`endOfGameResult`）
                to_append = endOfGameResults[LoLGame_summary["endOfGameResult"]]
            elif i == 7: #游戏模式配置（`gameModeMutators`）
                to_append = json.dumps(LoLGame_summary["gameModeMutators"])
            elif i == 8: #游戏类型（`gameType`）
                to_append = gameTypes_history[LoLGame_summary["gameType"]]
            elif i == 13: #持续时长（`gameDuration_norm`）
                to_append = lcuTime(LoLGame_summary["gameDuration"])
            elif i == 14: #游戏模式名称（`gameModeName`）
                to_append = "自定义" if LoLGame_summary["queueId"] == 0 else queues[LoLGame_summary["queueId"]]["name"] if LoLGame_summary["queueId"] in queues else ""
            elif i == 15: #地图名称（`mapName`）
                mapName: str = gamemaps[LoLGame_summary["mapId"]]["zh_CN"]
                if LoLGame_summary["mapId"] == 12:
                    if "mapskin_map12_bloom" in LoLGame_summary["gameModeMutators"]:
                        mapName = "莲华栈桥"
                    elif "mapskin_ha_bilgewater" in LoLGame_summary["gameModeMutators"]:
                        mapName = "屠夫之桥"
                    elif "mapskin_ha_crepe" in LoLGame_summary["gameModeMutators"]:
                        mapName = "进步之桥"
                    elif "mapskin_map12_jade" in LoLGame_summary["gameModeMutators"]:
                        mapName = "LCU_Map12_Name_Jade"
                    else:
                        mapName = "嚎哭深渊"
                to_append = mapName
            else:
                to_append = LoLGame_summary[key]
        elif i <= 28:
            if i >= 27: #召唤师图标相关键（Summoner icon-related keys）
                profileIconId: int = LoLGame_summary["participantIdentities"][participantIndex]["player"]["profileIcon"]
                if profileIconId == -1:
                    to_append = profileIconId if i == 27 else ""
                elif profileIconId in summonerIcons:
                    to_append = summonerIcons[profileIconId].get(key.split("_")[1], profileIconId if i == 27 else "")
                else:
                    if not profileIconId in unmapped_keys["summonerIcon"]:
                        unmapped_keys["summonerIcon"].add(profileIconId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, profileIconId, i, key, profileIconId, matchId, version), verbose = verbose)
                    to_append = profileIconId if i == 27 else ""
            else:
                to_append = LoLGame_summary["participantIdentities"][participantIndex]["player"][key]
        elif i <= 42:
            if i == 30: #最高段位（`highestAchievedSeasonTier`）
                to_append = tiers[LoLGame_summary["participants"][participantIndex]["highestAchievedSeasonTier"]]
            elif i >= 35 and i <= 37: #英雄相关键（Champion-related keys）
                championId: int = LoLGame_summary["participants"][participantIndex][key.split("_")[0] + "Id"]
                if championId in LoLChampions:
                    to_append = LoLChampions[championId][key.split("_")[1]]
                else: #在国服体验服的对局序号为696083511的对局中，出现了英雄序号为37225015（In a match with matchId 696083511 on Chinese PBE, there's a champion with championId 37225015）
                    if not championId in unmapped_keys["LoLChampion"]:
                        unmapped_keys["LoLChampion"].add(championId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                    to_append = championId if i == 35 else ""
            elif i >= 38 and i <= 41: #召唤师技能相关键（Summoner spell-related keys）
                spellId: int = LoLGame_summary["participants"][participantIndex][key.split("_")[0] + "Id"]
                if spellId == 0:
                    to_append = spellId if i <= 39 else ""
                elif spellId in spells:
                    to_append = spells[spellId][key.split("_")[1]]
                else:
                    if not spellId in unmapped_keys["spell"]:
                        unmapped_keys["spell"].add(spellId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, spellId, i, key, spellId, matchId, version), verbose = verbose)
                    to_append = spellId if i <= 39 else ""
            elif i == 42: #阵营（`team_color`）
                to_append = team_colors_int[LoLGame_summary["participants"][participantIndex]["teamId"]]
            else:
                to_append = LoLGame_summary["participants"][participantIndex][key]
        elif i <= 224:
            if i == 132: #角色绑定装备：临时应付正式服15.24版本、测试服16.1版本的情形（`roleBoundItem`: a temporary solution to handle the period when Live is v25.24 and PBE is 16.1）
                to_append = stats.get("roleBoundItem", "")
            elif i >= 160 and i <= 173: #英雄联盟装备相关键（LoLItems-related keys）
                itemId: int = stats[key.split("_")[0]]
                if itemId == 0:
                    to_append = ""
                elif itemId in LoLItems:
                    to_append = LoLItems[itemId][key.split("_")[1]]
                else:
                    if not itemId in unmapped_keys["LoLItem"]:
                        unmapped_keys["LoLItem"].add(itemId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                    to_append = itemId if i <= 166 else ""
            elif i >= 174 and i <= 191: #符文相关键（Perks-related keys）
                if i <= 179:
                    perkId: int = stats[key[:5]]
                    if perkId == 0:
                        to_append = ""
                    elif perkId in perks:
                        perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                        to_append = perk_EndOfGameStatDescs
                    else:
                        if not perkId in unmapped_keys["perk"]:
                            unmapped_keys["perk"].add(perkId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkId, i, key, perkId, matchId, version), verbose = verbose)
                        to_append = ""
                else:
                    perkId = stats[key.split("_")[0]]
                    if perkId == 0:
                        to_append = ""
                    elif perkId in perks:
                        to_append = perks[perkId][key.split("_")[1]]
                    else:
                        if not perkId in unmapped_keys["perk"]:
                            unmapped_keys["perk"].add(perkId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkId, i, key, perkId, matchId, version), verbose = verbose)
                        to_append = perkId if i <= 185 else ""
            elif i >= 192 and i <= 195: #符文系相关键（Perkstyles-related keys）
                perkstyleId: int = stats[key.split("_")[0]]
                if perkstyleId == 0:
                    to_append = ""
                elif perkstyleId in perkstyles:
                    to_append = perkstyles[perkstyleId][key.split("_")[1]]
                else:
                    if not perkstyleId in unmapped_keys["perkstyle"]:
                        unmapped_keys["perkstyle"].add(perkstyleId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkstyleId, i, key, perkstyleId, matchId, version), verbose = verbose)
                    to_append = perkstyleId if (i - 192) % 2 == 0 else ""
            elif i >= 196 and i <= 213: #强化符文相关键（Augment-related keys）
                CherryAugmentId: int = stats[key.split("_")[0]]
                if CherryAugmentId == 0:
                    to_append = ""
                elif CherryAugmentId in CherryAugments:
                    if i <= 201: #强化符文名称（`nameTRA`）
                        to_append = CherryAugments[CherryAugmentId][key.split("_")[1]]
                    elif i <= 207: #强化符文图标路径（`augmentIconPath`）
                        to_append = CherryAugments[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png")
                    else: #强化符文等级（`rarity`）
                        to_append = augment_rarity[CherryAugments[CherryAugmentId][key.split("_")[1]]]
                else:
                    if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                        unmapped_keys["CherryAugment"].add(CherryAugmentId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, CherryAugmentId, i, key, CherryAugmentId, matchId, version), verbose = verbose)
                    to_append = CherryAugmentId if i <= 201 else ""
            elif i == 214: #子阵营（`playerSubteamColor`）
                to_append = subteam_colors[stats["playerSubteamId"]]
            elif i == 215 or i == 216: #角色绑定装备相关键（Role bound item-related keys）
                if "roleBoundItem" in stats:
                    roleBoundItemId: int = stats["roleBoundItem"]
                    if roleBoundItemId == 0:
                        to_append = ""
                    elif roleBoundItemId in LoLItems:
                        to_append = LoLItems[roleBoundItemId][key.split("_")[1]]
                    else:
                        if not roleBoundItemId in unmapped_keys["LoLItem"]:
                            unmapped_keys["LoLItem"].add(roleBoundItemId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, roleBoundItemId, i, key, roleBoundItemId, matchId, version), verbose = verbose)
                        to_append = roleBoundItemId if i == 215 else ""
                else:
                    to_append = ""
            elif i == 217: #击杀/死亡/助攻（`K/D/A`）
                to_append = "/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])])
            elif i == 218: #战损比（`KDA`）
                to_append = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"])
            elif i == 219: #补刀（`CS`）
                to_append = stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]
            elif i == 220: #分均经济（`GPM`）
                to_append = 0 if LoLGame_summary["gameDuration"] == 0 else stats["goldEarned"] * 60 / LoLGame_summary["gameDuration"]
            elif i == 221: #金币利用率（`GUE` - Gold Utilization Efficiency）
                to_append = 0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"]
            elif i == 222: #分均补刀（`CSPM`）
                to_append = 0 if LoLGame_summary["gameDuration"] == 0 else (stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]) * 60 / LoLGame_summary["gameDuration"]
            elif i == 223: #伤害转化率（`D/G`）
                to_append = 0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"]
            elif i == 224: #胜负（`result`）
                to_append = "被终止" if LoLGame_summary["endOfGameResult"] == "Abort_AntiCheatExit" else "胜利" if stats["win"] else "失败"
            else:
                to_append = stats[key]
        else: #时间轴相关键（Timeline-related keys）
            to_append = lanes[timeline[key]] if i == 225 else roles[timeline[key]]
        LoLHistory_data[key].append(to_append)
    return LoLHistory_data

def generate_LoLHistory_records_sgp(LoLHistory_data: dict[str, list[Any]], LoLGame_summary: dict[str, Any], participantIndex: int, queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], gameIndex: int = 1, unmapped_keys: Optional[dict[str, set[Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> dict[str, list[Any]]:
    '''
    向英雄联盟对局记录数据中追加记录。<br>Append records to LoL match history data.
    
    :param LoLHistory_data: 英雄联盟对局记录数据。记录将追加到其中。<br>LoL match history data. Records are appended into it.
    :type LoLHistory_data: dict[str, list[Any]]
    :param LoLGame_summary: 英雄联盟对局概要。通过以下SGP接口得到：<br>LoL match summary, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/lol/{match_id}/SUMMARY`
    :type LoLGame_summary: dict[str, Any]
    :param participantIndex: 主召唤师索引。从0开始。<br>The index of the main summoner, which starts from 0.
    :type participantIndex: int
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 追加数据后的英雄联盟对局记录数据。<br>LoL match history data after appending.
    :rtype: dict[str, list[Any]]
    '''
    #参数预处理（Parameter pre-processing）
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    LoLHistory_header_keys: list[str] = list(LoLHistory_header.keys())
    if participantIndex == -1: #对局数据记录存在异常时的处理（Exception of match data recording exception）
        for i in range(len(LoLHistory_header_keys)):
            key: str = LoLHistory_header_keys[i]
            if i == 0: #游戏序号（`gameIndex`）
                to_append: Any = gameIndex
            elif i == 2: #对局创建时间戳（`gameCreation`）
                to_append = int(LoLGame_summary["metadata"].get("timestamp", 0))
            elif i == 3: #对局创建日期（`gameCreationDate`）
                to_append = getISOTime(int(LoLGame_summary["metadata"].get("timestamp", 0)) / 1000)
            elif i == 5: #对局序号（`gameId`）
                to_append = int(LoLGame_summary["metadata"]["match_id"].split("_")[1])
            else:
                to_append = ""
            LoLHistory_data[key].append(to_append)
    else:
        LoLGame_summary_json: dict[str, Any] = LoLGame_summary["json"]
        matchId: int = LoLGame_summary_json["gameId"]
        version: str = LoLGame_summary_json["gameVersion"]
        stats: dict[str, Any] = LoLGame_summary_json["participants"][participantIndex]
        for i in range(len(LoLHistory_header_keys)):
            key = LoLHistory_header_keys[i]
            if i == 0:
                to_append: Any = gameIndex
            elif i <= 15:
                if i == 1: #对局终止情况（`endOfGameResult`）
                    to_append = endOfGameResults[LoLGame_summary_json["endOfGameResult"]] if "endOfGameResult" in LoLGame_summary_json else ""
                elif i == 3: #对局创建日期（`gameCreationDate`）
                    to_append = getISOTime(LoLGame_summary_json["gameCreation"] / 1000) if "gameCreation" in LoLGame_summary_json else ""
                elif i == 7: #游戏模式配置（`gameModeMutators`）
                    to_append = json.dumps(LoLGame_summary_json["gameModeMutators"]) if "gameModeMutators" in LoLGame_summary_json else ""
                elif i == 8: #游戏类型（`gameType`）
                    to_append = gameTypes_history[LoLGame_summary_json["gameType"]] if "gameType" in LoLGame_summary_json else ""
                elif i == 13: #持续时长（`gameDuration_norm`）
                    to_append = lcuTime(LoLGame_summary_json["gameDuration"]) if "gameDuration" in LoLGame_summary_json else ""
                elif i == 14: #游戏模式名称（`gameModeName`）
                    to_append = "自定义" if LoLGame_summary_json["queueId"] == 0 else queues[LoLGame_summary_json["queueId"]]["name"] if LoLGame_summary_json["queueId"] in queues else ""
                elif i == 15: #地图名称（`mapName`）
                    mapName: str = gamemaps[LoLGame_summary_json["mapId"]]["zh_CN"]
                    if LoLGame_summary_json["mapId"] == 12:
                        if not "gameModeMutators" in LoLGame_summary_json:
                            mapName = "嚎哭深渊"
                        elif "mapskin_map12_bloom" in LoLGame_summary_json["gameModeMutators"]:
                            mapName = "莲华栈桥"
                        elif "mapskin_ha_bilgewater" in LoLGame_summary_json["gameModeMutators"]:
                            mapName = "屠夫之桥"
                        elif "mapskin_ha_crepe" in LoLGame_summary_json["gameModeMutators"]:
                            mapName = "进步之桥"
                        elif "mapskin_map12_jade" in LoLGame_summary_json["gameModeMutators"]:
                            mapName = "LCU_Map12_Name_Jade"
                        else:
                            mapName = "嚎哭深渊"
                    to_append = mapName
                else:
                    to_append = LoLGame_summary_json.get(key, "")
            else:
                if i == 19: #玩家名称（`gameName`）
                    to_append = stats["riotIdGameName"] if "riotIdGameName" in stats else stats["riotIdName"] if "riotIdName" in stats else ""
                elif i == 26: #名称编号（`tagLine`）
                    to_append = stats["riotIdTagline"] if "riotIdTagline" in stats else ""
                elif i == 27 or i == 28: #召唤师图标相关键（Summoner icon-related keys）
                    if "profileIcon" in stats:
                        profileIconId: int = stats["profileIcon"]
                        if profileIconId == -1:
                            to_append = profileIconId if i == 27 else ""
                        elif profileIconId in summonerIcons:
                            to_append = summonerIcons[profileIconId].get(key.split("_")[1], profileIconId if i == 27 else "")
                        else:
                            if not profileIconId in unmapped_keys["summonerIcon"]:
                                unmapped_keys["summonerIcon"].add(profileIconId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, profileIconId, i, key, profileIconId, matchId, version), verbose = verbose)
                            to_append = profileIconId if i == 27 else ""
                    else:
                        to_append = ""
                elif i >= 35 and i <= 37: #英雄相关键（Champion-related keys）
                    championId: int = stats[key.split("_")[0] + "Id"]
                    if championId in LoLChampions:
                        to_append = LoLChampions[championId][key.split("_")[1]]
                    else: #在国服体验服的对局序号为696083511的对局中，出现了英雄序号为37225015（In a match with matchId 696083511 on Chinese PBE, there's a champion with championId 37225015）
                        if not championId in unmapped_keys["LoLChampion"]:
                            unmapped_keys["LoLChampion"].add(championId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                        to_append = championId if i == 35 else ""
                elif i >= 38 and i <= 41: #召唤师技能相关键（Summoner spell-related keys）
                    spellId: int = stats[key.split("_")[0] + "Id"]
                    if spellId == 0:
                        to_append = spellId if i <= 39 else ""
                    elif spellId in spells:
                        to_append = spells[spellId][key.split("_")[1]]
                    else:
                        if not spellId in unmapped_keys["spell"]:
                            unmapped_keys["spell"].add(spellId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, spellId, i, key, spellId, matchId, version), verbose = verbose)
                        to_append = spellId if i <= 39 else ""
                elif i == 42: #阵营（`team_color`）
                    to_append = team_colors_int[stats["teamId"]]
                elif i == 79: #承受的魔法伤害（`magicalDamageTaken`）
                    to_append = stats["magicalDamageTaken"] if "magicalDamageTaken" in stats else stats["magicDamageTaken"] if "magicDamageTaken" in stats else ""
                elif i == 81: #击杀敌方野区野怪（`neutralMinionsKilledEnemyJungle`）
                    to_append = stats["totalEnemyJungleMinionsKilled"] if "totalEnemyJungleMinionsKilled" in stats else ""
                elif i == 82: #击杀我方野区野怪（`neutralMinionsKilledTeamJungle`）
                    to_append = stats["totalAllyJungleMinionsKilled"] if "totalAllyJungleMinionsKilled" in stats else ""
                elif i >= 85 and i <= 108: #符文相关键（Perk related keys）
                    if i <= 100: #主系符文相关键（Primary style's perk related keys）
                        perkCount: int = 1 + (i - 85) // 4
                        if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 and "selections" in stats["perks"]["styles"][0] and len(stats["perks"]["styles"][0]["selections"]) >= perkCount:
                            remainder: int = (i - 85) % 4
                            perk: dict[str, int] = stats["perks"]["styles"][0]["selections"][perkCount - 1]
                            if remainder == 0: #符文序号相关键（PerkId related keys）
                                to_append = perk["perk"]
                            else:
                                to_append = perk[f"var{remainder}"]
                        else:
                            to_append = ""
                    else: #副系符文（Secondary style's perk related keys）
                        perkCount: int = 1 + (i - 101) // 4
                        if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 and "selections" in stats["perks"]["styles"][1] and len(stats["perks"]["styles"][0]["selections"]) >= perkCount:
                            remainder: int = (i - 101) % 4
                            perk: dict[str, int] = stats["perks"]["styles"][1]["selections"][perkCount - 1]
                            if remainder == 0: #符文序号相关键（PerkId related keys）
                                to_append = perk["perk"]
                            else:
                                to_append = perk[f"var{remainder}"]
                        else:
                            to_append = ""
                elif i == 109: #主系序号（`perkPrimaryStyle`）
                    to_append = stats["perks"]["styles"][0]["style"] if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 else ""
                elif i == 110: #副系序号（`perkSecondaryStyle`)
                    to_append = stats["perks"]["styles"][1]["style"] if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 2 else ""
                elif i == 132: #角色绑定装备：临时应付正式服15.24版本、测试服16.1版本的情形（`roleBoundItem`: a temporary solution to handle the period when Live is v25.24 and PBE is 16.1）
                    to_append = stats.get("roleBoundItem", "")
                elif i >= 160 and i <= 173: #英雄联盟装备相关键（LoLItems-related keys）
                    subkey: str = key.split("_")[0]
                    if subkey in stats:
                        itemId: int = stats[subkey]
                        if itemId == 0:
                            to_append = ""
                        elif itemId in LoLItems:
                            to_append = LoLItems[itemId][key.split("_")[1]]
                        else:
                            if not itemId in unmapped_keys["LoLItem"]:
                                unmapped_keys["LoLItem"].add(itemId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                            to_append = itemId if i <= 166 else ""
                    else:
                        to_append = ""
                elif i >= 174 and i <= 191: #符文相关键（Perks-related keys）
                    perkId_got: bool = False
                    perkId: int = 0
                    perkVar1: int = 0
                    perkVar2: int = 0
                    perkVar3: int = 0
                    perkStyle_index: int = (i - 174) % 6 // 4
                    perkCount: int = 1 + (i - 174) % 6 % 4
                    if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 and "selections" in stats["perks"]["styles"][perkStyle_index] and len(stats["perks"]["styles"][perkStyle_index]["selections"]) >= perkCount:
                        perk: dict[str, int] = stats["perks"]["styles"][perkStyle_index]["selections"][perkCount - 1]
                        perkId, perkVar1, perkVar2, perkVar3 = perk["perk"], perk["var1"], perk["var2"], perk["var3"]
                        perkId_got = True
                    if perkId_got:
                        if perkId == 0:
                            to_append = ""
                        elif perkId in perks:
                            if i <= 179:
                                perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                                perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(perkVar1))
                                perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(perkVar2))
                                perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(perkVar3))
                                to_append = perk_EndOfGameStatDescs
                            else:
                                to_append = perks[perkId][key.split("_")[1]]
                        else:
                            if not perkId in unmapped_keys["perk"]:
                                unmapped_keys["perk"].add(perkId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkId, i, key, perkId, matchId, version), verbose = verbose)
                            to_append = perkId if i >= 180 and i <= 185 else ""
                    else:
                        to_append = ""
                elif i >= 192 and i <= 195: #符文系相关键（Perkstyles-related keys）
                    perkStyle_index: int = (i - 192) // 2
                    perkstyleId: int = stats["perks"]["styles"][perkStyle_index]["style"] if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= perkStyle_index + 1 else 0
                    if perkstyleId == 0:
                        to_append = ""
                    elif perkstyleId in perkstyles:
                        to_append = perkstyles[perkstyleId][key.split("_")[1]]
                    else:
                        if not perkstyleId in unmapped_keys["perkstyle"]:
                            unmapped_keys["perkstyle"].add(perkstyleId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkstyleId, i, key, perkstyleId, matchId, version), verbose = verbose)
                        to_append = perkstyleId if (i - 192) % 2 == 0 else ""
                elif i >= 196 and i <= 213: #强化符文相关键（Augment-related keys）
                    subkey = key.split("_")[0]
                    if subkey in stats:
                        CherryAugmentId: int = stats[subkey]
                        if CherryAugmentId == 0:
                            to_append = ""
                        elif CherryAugmentId in CherryAugments:
                            if i <= 201: #强化符文名称（`nameTRA`）
                                to_append = CherryAugments[CherryAugmentId][key.split("_")[1]]
                            elif i <= 207: #强化符文图标路径（`augmentIconPath`）
                                to_append = CherryAugments[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png")
                            else: #强化符文等级（`rarity`）
                                to_append = augment_rarity[CherryAugments[CherryAugmentId][key.split("_")[1]]]
                        else:
                            if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                                unmapped_keys["CherryAugment"].add(CherryAugmentId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, CherryAugmentId, i, key, CherryAugmentId, matchId, version), verbose = verbose)
                            to_append = CherryAugmentId if i <= 201 else ""
                    else:
                        to_append = ""
                elif i == 214: #子阵营（`playerSubteamColor`）
                    to_append = subteam_colors[stats["playerSubteamId"]] if "playerSubteamId" in stats else ""
                elif i == 215 or i == 216: #角色绑定装备相关键（Role bound item-related keys）
                    if "roleBoundItem" in stats:
                        roleBoundItemId: int = stats["roleBoundItem"]
                        if roleBoundItemId == 0:
                            to_append = ""
                        elif roleBoundItemId in LoLItems:
                            to_append = LoLItems[roleBoundItemId][key.split("_")[1]]
                        else:
                            if not roleBoundItemId in unmapped_keys["LoLItem"]:
                                unmapped_keys["LoLItem"].add(roleBoundItemId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, roleBoundItemId, i, key, roleBoundItemId, matchId, version), verbose = verbose)
                            to_append = roleBoundItemId if i == 215 else ""
                    else:
                        to_append = ""
                elif i == 217: #击杀/死亡/助攻（`K/D/A`）
                    to_append = "/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])]) if all(map(lambda x: x in stats, ["kills", "deaths", "assists"])) else ""
                elif i == 218: #战损比（`KDA`）
                    to_append = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"]) if all(map(lambda x: x in stats, ["kills", "deaths", "assists"])) else ""
                elif i == 219: #补刀（`CS`）
                    to_append = stats["neutralMinionsKilled"] + stats["totalMinionsKilled"] if all(map(lambda x: x in stats, ["neutralMinionsKilled", "totalMinionsKilled"])) else ""
                elif i == 220: #分均经济（`GPM`）
                    to_append = (0 if LoLGame_summary_json["gameDuration"] == 0 else stats["goldEarned"] * 60 / LoLGame_summary_json["gameDuration"]) if "gameDuration" in LoLGame_summary_json and "goldEarned" in stats else ""
                elif i == 221: #金币利用率（`GUE` - Gold Utilization Efficiency）
                    to_append = (0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"]) if all(map(lambda x: x in stats, ["goldSpent", "goldEarned"])) else ""
                elif i == 222: #分均补刀（`CSPM`）
                    to_append = (0 if LoLGame_summary_json["gameDuration"] == 0 else (stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]) * 60 / LoLGame_summary_json["gameDuration"]) if "gameDuration" in LoLGame_summary_json and all(map(lambda x: x in stats, ["neutralMinionsKilled", "totalMinionsKilled"])) else ""
                elif i == 223: #伤害转化率（`D/G`）
                    to_append = (0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"]) if all(map(lambda x: x in stats, ["goldEarned", "totalDamageDealtToChampions"])) else ""
                elif i == 224: #胜负（`result`）
                    to_append = "被终止" if "endOfGameResult" in LoLGame_summary_json and LoLGame_summary_json["endOfGameResult"] == "Abort_AntiCheatExit" else "" if not "win" in stats else "胜利" if stats["win"] else "失败"
                else:
                    to_append = stats.get(key, "")
            LoLHistory_data[key].append(to_append)
    return LoLHistory_data

def sort_LoLHistory(LoLHistory: dict[str, Any], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], useAllVersions: bool = False, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]: #当数据转换出现无法匹配的情况时，重新获取对局版本的数据资源。目前只应用于查战绩脚本和自定义脚本11（When dismatch happens during data conversion, get the data resources of the game version. Only applied to Customized Programs 05 and 11 only）
    '''
    将英雄联盟对局记录整理成一张表格。<br>Organize LoL match history into a dataframe.
    
    :param LoLHistory: 英雄联盟对局记录数据。通过以下接口得到：<br>LoL match history data, obtained through the following endpoint:
    
        - `GET /lol-match-history/v1/products/lol/{puuid}/matches?begIndex={begIndex}&endIndex={endIndex}`
    :type LoLHistory: dict[str, Any]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[int]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 英雄联盟对局记录数据框，以及游戏队列、召唤师图标、英雄、召唤师技能、英雄联盟装备、符文、符文系和斗魂竞技场强化符文等数据资源的缓存。<br>LoL match history dataframe and data resources like queues, summoner icons, champions, summoner spells, LoL items, perks, perkstyles and Arena augments.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queues": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    LoLHistory_header_keys: list[str] = list(LoLHistory_header.keys())
    LoLHistory_data: dict[str, list[Any]] = {key: [] for key in LoLHistory_header_keys}
    games: list[dict[str, Any]] = LoLHistory["games"]["games"]
    for i in range(len(games)):
        game: dict[str, Any] = games[i]
        version: str = game["gameVersion"]
        bigVersion: str = ".".join(version.split(".")[:2])
        #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
        if useAllVersions:
            ##游戏模式（Game mode）
            queueIds_match_list: list[int] = [game["queueId"]]
            for j in queueIds_match_list:
                if not j in queues and current_versions["queue"] != bigVersion:
                    queuePatch_adopted: str = bigVersion
                    queue_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, queue_recapture, queuePatch_adopted, j, i + 1, len(games), game["gameId"], queuePatch_adopted, queue_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                            queue: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            queuePatch_deserted: str = queuePatch_adopted
                            queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                            queue_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if queue_recapture < 3:
                                queue_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                            queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                            current_versions["queue"] = queuePatch_adopted
                            unmapped_keys["queue"].clear()
                            break
                    break
            ##召唤师图标（Summoner icon）
            summonerIconIds_match_list: list[int] = sorted(set(map(lambda x: x["player"]["profileIcon"], game["participantIdentities"])))
            for j in summonerIconIds_match_list:
                if not j in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                    summonerIconPatch_adopted: str = bigVersion
                    summonerIcon_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, summonerIcon_recapture, summonerIconPatch_adopted, j, i + 1, len(games), game["gameId"], summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            summonerIcon: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            summonerIconPatch_deserted: str = summonerIconPatch_adopted
                            summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                            summonerIcon_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if summonerIcon_recapture < 3:
                                summonerIcon_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                            summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                            current_versions["summonerIcon"] = summonerIconPatch_adopted
                            unmapped_keys["summonerIcon"].clear()
                            break
                    break #切换版本只需一次即可。如果对局版本还不对，那就不用再找下去了（The version of data resources only needs changing once. If data resources of the version of this match don't match all the game data, then there's no need of retrying）
            ##英雄：包含选用英雄（LoL champions, which contain picked ones）
            LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: x["championId"], game["participants"])))
            for j in LoLChampionIds_match_list:
                if not j in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                    LoLChampionPatch_adopted: str = bigVersion
                    LoLChampion_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, LoLChampion_recapture, LoLChampionPatch_adopted, j, i + 1, len(games), game["gameId"], LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            LoLChampion: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                            LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                            LoLChampion_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if LoLChampion_recapture < 3:
                                LoLChampion_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                            LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                            current_versions["LoLChampion"] = LoLChampionPatch_adopted
                            unmapped_keys["LoLChampion"].clear() #切换版本时，未对应的键应当清空。下同（When the version is switched, the unmapped keys should be cleared. This applies to other data resources）
                            break
                    break
            ##召唤师技能（Summoner spells）
            spellIds_match_list: list[int] = sorted(set(map(lambda x: x["spell1Id"], game["participants"])) | set(map(lambda x: x["spell2Id"], game["participants"])))
            for j in spellIds_match_list:
                if not j in spells and current_versions["spell"] != bigVersion and j != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                    spellPatch_adopted: str = bigVersion
                    spell_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, spell_recapture, spellPatch_adopted, j, i + 1, len(games), game["gameId"], spellPatch_adopted, spell_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            spell: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            spellPatch_deserted: str = spellPatch_adopted
                            spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                            spell_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if spell_recapture < 3:
                                spell_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                            spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                            current_versions["spell"] = spellPatch_adopted
                            unmapped_keys["spell"].clear()
                            break
                    break
            ##英雄联盟装备（LoL items）
            LoLItemIds_match_list: list[int] = sorted(set(map(lambda x: x["stats"]["item0"], game["participants"])) | set(map(lambda x: x["stats"]["item1"], game["participants"])) | set(map(lambda x: x["stats"]["item2"], game["participants"])) | set(map(lambda x: x["stats"]["item3"], game["participants"])) | set(map(lambda x: x["stats"]["item4"], game["participants"])) | set(map(lambda x: x["stats"]["item5"], game["participants"])) | set(map(lambda x: x["stats"]["item6"], game["participants"])) | set(map(lambda x: x["stats"].get("roleBoundItem", 0), game["participants"])))
            for j in LoLItemIds_match_list:
                if not j in LoLItems and current_versions["LoLItem"] != bigVersion and j != 0: #空装备序号是0（The itemId of an empty item is 0）
                    LoLItemPatch_adopted: str = bigVersion
                    LoLItem_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, LoLItem_recapture, LoLItemPatch_adopted, j, i + 1, len(games), game["gameId"], LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            LoLItem: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            LoLItemPatch_deserted: str = LoLItemPatch_adopted
                            LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                            LoLItem_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if LoLItem_recapture < 3:
                                LoLItem_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                            LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                            current_versions["LoLItem"] = LoLItemPatch_adopted
                            unmapped_keys["LoLItem"].clear()
                            break
                    break
            ##符文（Perks）
            perkIds_match_list: list[int] = sorted(set(perk for s in [set(map(lambda x: x["stats"]["perk" + str(i)], game["participants"])) for i in range(6)] for perk in s))
            for j in perkIds_match_list:
                if not j in perks and current_versions["perk"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                    perkPatch_adopted: str = bigVersion
                    perk_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, perk_recapture, perkPatch_adopted, j, i + 1, len(games), game["gameId"], perkPatch_adopted, perk_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            perk: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            perkPatch_deserted: str = perkPatch_adopted
                            perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                            perk_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if perk_recapture < 3:
                                perk_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                            perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                            current_versions["perk"] = perkPatch_adopted
                            unmapped_keys["perk"].clear()
                            break
                    break
            ##符文系（Perkstyles）
            perkstyleIds_match_list: list[int] = sorted(list(set(map(lambda x: x["stats"]["perkPrimaryStyle"], game["participants"])) | set(map(lambda x: x["stats"]["perkSubStyle"], game["participants"]))))
            for j in perkstyleIds_match_list:
                if not j in perkstyles and current_versions["perkstyle"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                    perkstylePatch_adopted: str = bigVersion
                    perkstyle_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, perkstyle_recapture, perkstylePatch_adopted, j, i + 1, len(games), game["gameId"], perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                            perkstyle: dict[str, Any] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            perkstylePatch_deserted: str = perkstylePatch_adopted
                            perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                            perkstyle_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if perkstyle_recapture < 3:
                                perkstyle_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                            perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                            current_versions["perkstyle"] = perkstylePatch_adopted
                            unmapped_keys["perkstyle"].clear()
                            break
                    break
            ##斗魂竞技场强化符文（Cherry augments）
            CherryAugmentIds_match_list: list[int] = sorted(set(augment for s in [set(map(lambda x: x["stats"]["playerAugment" + str(i)], game["participants"])) for i in range(1, 7)] for augment in s))
            for j in CherryAugmentIds_match_list:
                if not j in CherryAugments and current_versions["CherryAugment"] != bigVersion and j != 0:
                    CherryAugmentPatch_adopted: str = bigVersion
                    CherryAugment_recapture: int = 1
                    logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, CherryAugment_recapture, CherryAugmentPatch_adopted, j, i + 1, len(games), game["gameId"], CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            CherryAugment: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                            CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                            CherryAugment_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if CherryAugment_recapture < 3:
                                CherryAugment_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                            CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                            current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                            unmapped_keys["CherryAugment"].clear()
                            break
                    break
        #下面开始整理数据（Organize data）
        generate_LoLHistory_records(LoLHistory_data, game, 0, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = i + 1, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
        print("对局记录查询进度（Match history query process）：%d/%d\t对局序号（MatchId）：%d" %(i + 1, len(games), game["gameId"]), end = "\r")
    #数据框列序整理（Dataframe column ordering）
    LoLHistory_statistics_output_order: list[int] = [0, 25, 19, 26, 5, 3, 13, 4, 11, 6, 14, 10, 15, 9, 35, 36, 46, 38, 39, 160, 161, 162, 163, 164, 165, 166, 215, 217, 219, 63, 224, 136]
    LoLHistory_data_organized: dict[str, list[Any]] = {LoLHistory_header_keys[i]: LoLHistory_data[LoLHistory_header_keys[i]] for i in LoLHistory_statistics_output_order}
    LoLHistory_df: pandas.DataFrame = pandas.DataFrame(data = LoLHistory_data_organized)
    optimize_bool_display(LoLHistory_df)
    LoLHistory_df = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df.columns], LoLHistory_df], ignore_index = True)
    #LoLHistory_df.apply(lambda x: pandas.Series([-3], index = ["K/D/A"]))
    return (LoLHistory_df, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments)
    LoLHistory_web_display_order: list[int] = [0, 25, 19, 26, 5, 3, 13, 4, 11, 6, 14, 10, 15, 9, 35, 36, 37, 46, 40, 41, 167, 168, 169, 170, 171, 172, 173, 216, 217, 219, 63, 224, 136]
    LoLHistory_data_organized_web: dict[str, list[Any]] = {}
    for i in LoLHistory_web_display_order:
        key: str = LoLHistory_header_keys[i]
        if i in [28, 37, 40, 41, 167, 168, 169, 170, 171, 172, 173, 186, 187, 188, 189, 190, 191, 193, 194, 202, 203, 204, 205, 206, 207, 216]: #转换路径（Transform the paths）
            LoLHistory_data_organized_web[key] = list(map(lambda x: "" if x == "" else urljoin(connection.address, x), LoLHistory_data[key]))
        else:
            LoLHistory_data_organized_web[key] = LoLHistory_data[key]
    LoLHistory_df_web: pandas.DataFrame = pandas.DataFrame(data = LoLHistory_data_organized_web)
    LoLHistory_df_web = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df_web.columns], LoLHistory_df_web], ignore_index = True)
    LoLHistory_htmltable: str = LoLHistory_df_web.to_html(escape = False)

def sort_LoLHistory_sgp(LoLHistory: dict[str, Any], current_puuid: str | list[str], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], useAllVersions: bool = False, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]: #当数据转换出现无法匹配的情况时，重新获取对局版本的数据资源。目前只应用于查战绩脚本和自定义脚本11（When dismatch happens during data conversion, get the data resources of the game version. Only applied to Customized Programs 05 and 11 only）
    '''
    将英雄联盟对局记录整理成一张表格。<br>Organize LoL match history into a dataframe.
    
    :param LoLHistory: 英雄联盟对局记录数据。通过以下接口得到：<br>LoL match history data, obtained through the following endpoint:
    
        - `GET /lol-match-history/v1/products/lol/{puuid}/matches?begIndex={begIndex}&endIndex={endIndex}`
    :type LoLHistory: dict[str, Any]
    :param current_puuid: 主召唤师玩家通用唯一识别码。可以是单一值，也可以是一个列表。用于确定各对局中的主召唤师索引。<br>The main summoner's puuid. Both a single value and a list are supported. Used to determine the main player's indices in all matches.
    :type current_puuid: str | list[str]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[int]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 英雄联盟对局记录数据框，以及游戏队列、召唤师图标、英雄、召唤师技能、英雄联盟装备、符文、符文系和斗魂竞技场强化符文等数据资源的缓存。<br>LoL match history dataframe and data resources like queues, summoner icons, champions, summoner spells, LoL items, perks, perkstyles and Arena augments.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queues": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    LoL_main_player_indices: list[int] = []
    for game in LoLHistory["games"]:
        if game.get("json"):
            for i in range(len(game["json"]["participants"])):
                if game["json"]["participants"][i]["puuid"] in puuidList:
                    LoL_main_player_indices.append(i)
                    break
            else:
                LoL_main_player_indices.append(-1)
        else:
            LoL_main_player_indices.append(-1) #当主玩家索引为-1时，表示本场对局存在异常（Main player index being -1 represents an abnormal match）
    LoLHistory_header_keys: list[str] = list(LoLHistory_header.keys())
    LoLHistory_data: dict[str, list[Any]] = {key: [] for key in LoLHistory_header_keys}
    games: list[dict[str, Any]] = LoLHistory["games"]
    for i in range(len(games)):
        matchId: int = int(games[i]["metadata"]["match_id"].split("_")[1])
        participantIndex: int = LoL_main_player_indices[i]
        if participantIndex != -1:
            LoLGame_summary_json: dict[str, Any] = games[i]["json"]
            version: str = LoLGame_summary_json["gameVersion"]
            bigVersion: str = ".".join(version.split(".")[:2])
            stats: dict[str, Any] = LoLGame_summary_json["participants"][participantIndex]
            #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
            if useAllVersions:
                ##游戏模式（Game mode）
                queueIds_match_list: list[int] = [LoLGame_summary_json["queueId"]]
                for j in queueIds_match_list:
                    if not j in queues and current_versions["queue"] != bigVersion:
                        queuePatch_adopted: str = bigVersion
                        queue_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, queue_recapture, queuePatch_adopted, j, i + 1, len(games), matchId, queuePatch_adopted, queue_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                queue: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                queuePatch_deserted: str = queuePatch_adopted
                                queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                queue_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if queue_recapture < 3:
                                    queue_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                current_versions["queue"] = queuePatch_adopted
                                unmapped_keys["queue"].clear()
                                break
                        break
                ##召唤师图标（Summoner icon）
                summonerIconIds_match_list: list[int] = [stats["profileIcon"]]
                for j in summonerIconIds_match_list:
                    if not j in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                        summonerIconPatch_adopted: str = bigVersion
                        summonerIcon_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, summonerIcon_recapture, summonerIconPatch_adopted, j, i + 1, len(games), matchId, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                summonerIcon: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                summonerIconPatch_deserted: str = summonerIconPatch_adopted
                                summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                                summonerIcon_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if summonerIcon_recapture < 3:
                                    summonerIcon_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                                summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                                current_versions["summonerIcon"] = summonerIconPatch_adopted
                                unmapped_keys["summonerIcon"].clear()
                                break
                        break #切换版本只需一次即可。如果对局版本还不对，那就不用再找下去了（The version of data resources only needs changing once. If data resources of the version of this match don't match all the game data, then there's no need of retrying）
                ##英雄：包含选用英雄（LoL champions, which contain picked ones）
                LoLChampionIds_match_list: list[int] = [stats["championId"]]
                for j in LoLChampionIds_match_list:
                    if not j in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                        LoLChampionPatch_adopted: str = bigVersion
                        LoLChampion_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, LoLChampion_recapture, LoLChampionPatch_adopted, j, i + 1, len(games), matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                LoLChampion: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                                LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                                LoLChampion_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if LoLChampion_recapture < 3:
                                    LoLChampion_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                                LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                                current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                unmapped_keys["LoLChampion"].clear() #切换版本时，未对应的键应当清空。下同（When the version is switched, the unmapped keys should be cleared. This applies to other data resources）
                                break
                        break
                ##召唤师技能（Summoner spells）
                spellIds_match_list: list[int] = sorted({stats["spell1Id"], stats["spell2Id"]})
                for j in spellIds_match_list:
                    if not j in spells and current_versions["spell"] != bigVersion and j != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                        spellPatch_adopted: str = bigVersion
                        spell_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, spell_recapture, spellPatch_adopted, j, i + 1, len(games), matchId, spellPatch_adopted, spell_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                spell: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                spellPatch_deserted: str = spellPatch_adopted
                                spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                                spell_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if spell_recapture < 3:
                                    spell_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                                spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                                current_versions["spell"] = spellPatch_adopted
                                unmapped_keys["spell"].clear()
                                break
                        break
                ##英雄联盟装备（LoL items）
                LoLItemIds_match_list: list[int] = sorted(set(stats.get(key, 0) for key in ["item0", "item1", "item2", "item3", "item4", "item5", "item6", "roleBoundItem"])) #不需要考虑成就中的装备，因为成就中的装备也是来自这里（No need to consider the items in challenges, because they also come from here）
                for j in LoLItemIds_match_list:
                    if not j in LoLItems and current_versions["LoLItem"] != bigVersion and j != 0: #空装备序号是0（The itemId of an empty item is 0）
                        LoLItemPatch_adopted: str = bigVersion
                        LoLItem_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, LoLItem_recapture, LoLItemPatch_adopted, j, i + 1, len(games), matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                LoLItem: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                LoLItemPatch_deserted: str = LoLItemPatch_adopted
                                LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                                LoLItem_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if LoLItem_recapture < 3:
                                    LoLItem_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                                LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                                current_versions["LoLItem"] = LoLItemPatch_adopted
                                unmapped_keys["LoLItem"].clear()
                                break
                        break
                ##符文（Perks）
                perkIds_match_list: list[int] = []
                if "perks" in stats:
                    if "statPerks" in stats["perks"]:
                        perkIds_match_list += list(stats["perks"]["statPerks"].values())
                    if "styles" in stats["perks"]:
                        for style in stats["perks"]["styles"]:
                            if "selections" in style:
                                perkIds_match_list += list(map(lambda x: x["perk"], style["selections"]))
                perkIds_match_list = sorted(set(perkIds_match_list))
                for j in perkIds_match_list:
                    if not j in perks and current_versions["perk"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                        perkPatch_adopted: str = bigVersion
                        perk_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, perk_recapture, perkPatch_adopted, j, i + 1, len(games), matchId, perkPatch_adopted, perk_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                perk: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                perkPatch_deserted: str = perkPatch_adopted
                                perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                                perk_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if perk_recapture < 3:
                                    perk_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                                perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                                current_versions["perk"] = perkPatch_adopted
                                unmapped_keys["perk"].clear()
                                break
                        break
                ##符文系（Perkstyles）
                perkstyleIds_match_list: list[int] = []
                if "perks" in stats and "styles" in stats["perks"]:
                    perkstyleIds_match_list += list(map(lambda x: x["style"], stats["perks"]["styles"]))
                perkstyleIds_match_list = sorted(set(perkstyleIds_match_list))
                for j in perkstyleIds_match_list:
                    if not j in perkstyles and current_versions["perkstyle"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                        perkstylePatch_adopted: str = bigVersion
                        perkstyle_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, perkstyle_recapture, perkstylePatch_adopted, j, i + 1, len(games), matchId, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                perkstyle: dict[str, Any] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                perkstylePatch_deserted: str = perkstylePatch_adopted
                                perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                                perkstyle_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if perkstyle_recapture < 3:
                                    perkstyle_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                                perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                                current_versions["perkstyle"] = perkstylePatch_adopted
                                unmapped_keys["perkstyle"].clear()
                                break
                        break
                ##斗魂竞技场强化符文（Cherry augments）
                CherryAugmentIds_match_list: list[int] = sorted(set(stats.get("playerAugment" + str(i), 0) for i in range(1, 7)))
                for j in CherryAugmentIds_match_list:
                    if not j in CherryAugments and current_versions["CherryAugment"] != bigVersion and j != 0:
                        CherryAugmentPatch_adopted: str = bigVersion
                        CherryAugment_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(i + 1, len(games), matchId, j, CherryAugment_recapture, CherryAugmentPatch_adopted, j, i + 1, len(games), matchId, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                CherryAugment: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                                CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                                CherryAugment_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if CherryAugment_recapture < 3:
                                    CherryAugment_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(games), matchId, j, j, i + 1, len(games), matchId), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                                CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                                current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                unmapped_keys["CherryAugment"].clear()
                                break
                        break
        #下面开始整理数据（Organize data）
        generate_LoLHistory_records_sgp(LoLHistory_data, games[i], participantIndex, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = i + 1, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
        print("对局记录查询进度（Match history query process）：%d/%d\t对局序号（MatchId）：%d" %(i + 1, len(games), matchId), end = "\r")
    #数据框列序整理（Dataframe column ordering）
    LoLHistory_statistics_output_order: list[int] = [0, 25, 19, 26, 5, 3, 13, 4, 11, 6, 14, 10, 15, 9, 35, 36, 46, 38, 39, 160, 161, 162, 163, 164, 165, 166, 215, 217, 219, 63, 224, 136]
    LoLHistory_data_organized: dict[str, list[Any]] = {LoLHistory_header_keys[i]: LoLHistory_data[LoLHistory_header_keys[i]] for i in LoLHistory_statistics_output_order}
    LoLHistory_df: pandas.DataFrame = pandas.DataFrame(data = LoLHistory_data_organized)
    optimize_bool_display(LoLHistory_df)
    LoLHistory_df = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df.columns], LoLHistory_df], ignore_index = True)
    #LoLHistory_df.apply(lambda x: pandas.Series([-3], index = ["K/D/A"]))
    return (LoLHistory_df, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments)

def generate_LoLGameSummary_records(LoLGame_summary_data: dict[str, list[Any]], LoLGame_summary: dict[str, Any], participantIndex: int, queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], gameIndex: int = 1, current_puuid: str | list[str] = "", bans: Optional[list[dict[str, int]]] = None, legacy_banData_appended: Optional[dict[int, bool]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> dict[str, list[Any]]:
    '''
    向英雄联盟对局概要数据中追加记录。<br>Append records to LoL match summary data.
    
    :param LoLGame_summary_data: 英雄联盟对局概要数据。记录将追加到其中。<br>LoL match summary data. Records are appended into it.
    :type LoLGame_summary_data: dict[str, list[Any]]
    :param LoLGame_summary: 英雄联盟对局概要。通过以下LCU接口得到：<br>LoL match summary, obtained through the following LCU endpoint:
    
        - `GET /lol-match-history/v1/games/{gameId}`
    :type LoLGame_summary: dict[str, Any]
    :param participantIndex: 主召唤师索引。从0开始。<br>The index of the main summoner, which starts from 0.
    :type participantIndex: int
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param current_puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type current_puuid: str | list[str]
    :param bans: 事先从对局概要中整理的禁用信息列表，每个元素是一个字典，包含选用顺序和禁用英雄序号。<br>Banned champion list prepared from the match summary in advance, where each element is a dictionary that contains pick order and banned championId.
    :type bans: list[dict[str, int]]
    :param legacy_banData_appended: 传统征召模式禁用信息已追加情况。键是阵营序号，值是表明禁用信息是否已追加过的逻辑值。<br>The status of whether legacy ban data have been appended. Each key is teamId, and each value is a boolean value that indicates whether the ban information has been appended.
    
        在传统征召模式的英雄选择阶段，每支队伍禁用三名英雄，全部由一名玩家禁用。因此，每支队伍只应追加禁用信息一次。<br>In the champ select stage of the legacy draft mode, each team bans three champions by a single player. Therefore, for each team, the ban information should be appended only once.
    :type legacy_banData_appended: dict[int, bool]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 追加数据后的英雄联盟对局概要数据。<br>LoL match summary data after appending.
    :rtype: dict[str, list[Any]]
    '''
    #参数预处理（Parameter pre-processing）
    if bans == None:
        bans = []
    if legacy_banData_appended == None:
        legacy_banData_appended = {100: False, 200: False}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    matchId: int = LoLGame_summary["gameId"]
    version: str = LoLGame_summary["gameVersion"]
    mapName: str = gamemaps[LoLGame_summary["mapId"]]["zh_CN"]
    stats: dict[str, Any] = LoLGame_summary["participants"][participantIndex]["stats"]
    timeline: dict[str, Any] = LoLGame_summary["participants"][participantIndex]["timeline"]
    bans_team100: list[dict[str, int]] = []
    bans_team200: list[dict[str, int]] = []
    for i in range(len(LoLGame_summary["teams"])):
        if LoLGame_summary["teams"][i]["teamId"] == 100:
            bans_team100 = LoLGame_summary["teams"][i]["bans"]
        elif LoLGame_summary["teams"][i]["teamId"] == 200:
            bans_team200 = LoLGame_summary["teams"][i]["bans"]
    current_participant_found: bool = False
    current_participantId: int = 0
    current_participant: dict[str, Any] = {}
    for participant in LoLGame_summary["participantIdentities"]:
        for puuid in puuidList:
            if participant["player"]["puuid"] == puuid:
                current_participantId = participant["participantId"]
                current_participant_found: bool = True
                break #注意，这里是找到一个对应的玩家通用唯一识别码，即找到一名玩家就退出循环。因为传入玩家通用唯一识别码的主要目的是区别敌我，而如果自己的多个账号在一场对局中同时出现，需要选择一个账号所在阵营视为友方。这里选择的是第一个账号所在阵营（Note that once a puuid, or a player is found, the program exits the loop. This is because the main purpose of passing the puuid is to distinguish the ally team and the enemy team. If the user's multiple accounts are present in a match at the same time, the ally team should be the team of one account. Here we take the team of the account first found in the match as the ally team）
        if current_participant_found:
            break
    if current_participant_found:
        for participant in LoLGame_summary["participants"]:
            if participant["participantId"] == current_participantId:
                current_participant = participant
                break
    else:
        current_participantId = 0 #如果出现数据异常，也认为目标玩家不存在于该对局中（If an error occurs to the data, consider this player isn't in this match）
    team_participants: list[dict[str, Any]] = [participant for participant in LoLGame_summary["participants"] if LoLGame_summary["gameMode"] == "CHERRY" and participant["stats"]["playerSubteamId"] == stats["playerSubteamId"] or LoLGame_summary["gameMode"] != "CHERRY" and participant["teamId"] == LoLGame_summary["participants"][participantIndex]["teamId"]] #存储对局概要中同一队伍的玩家。斗魂竞技场对局应该使用子阵营（Store the participants of the same team from the game summary. Subteam should be used to evaluate a player）
    if LoLGame_summary["mapId"] == 12:
        if "mapskin_map12_bloom" in LoLGame_summary["gameModeMutators"]:
            mapName = "莲华栈桥"
        elif "mapskin_ha_bilgewater" in LoLGame_summary["gameModeMutators"]:
            mapName = "屠夫之桥"
        elif "mapskin_ha_crepe" in LoLGame_summary["gameModeMutators"]:
            mapName = "进步之桥"
        elif "mapskin_map12_jade" in LoLGame_summary["gameModeMutators"]:
            mapName = "LCU_Map12_Name_Jade"
        else:
            mapName = "嚎哭深渊"
    #数据整理核心部分（Data organization core part）
    LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
    for i in range(len(LoLGame_summary_header_keys)):
        key: str = LoLGame_summary_header_keys[i]
        if i == 0: #游戏序号（`gameIndex`）
            to_append: Any = gameIndex
        elif i <= 15:
            if i == 1: #对局终止情况（`endOfGameResult`）
                to_append = endOfGameResults[LoLGame_summary["endOfGameResult"]]
            elif i == 7: #游戏模式配置（`gameModeMutators`）
                to_append = json.dumps(LoLGame_summary["gameModeMutators"])
            elif i == 8: #游戏类型（`gameType`）
                to_append = gameTypes_history[LoLGame_summary["gameType"]]
            elif i == 13: #持续时长（`gameDuration_norm`）
                to_append = lcuTime(LoLGame_summary["gameDuration"])
            elif i == 14: #游戏模式名称（`gameModeName`）
                to_append = "自定义" if LoLGame_summary["queueId"] == 0 else queues[LoLGame_summary["queueId"]]["name"] if LoLGame_summary["queueId"] in queues else ""
            elif i == 15: #地图名称（`mapName`）
                to_append = mapName
            else:
                to_append = LoLGame_summary[key]
        elif i == 16: #玩家序号（`participantId`）
            to_append = LoLGame_summary["participantIdentities"][participantIndex]["participantId"]
        elif i <= 29:
            if i >= 28: #召唤师图标相关键（Profile icon-related keys）
                profileIconId: int = LoLGame_summary["participantIdentities"][participantIndex]["player"]["profileIcon"]
                if profileIconId == -1: #早期存在一个空图标（There was once an empty icon, which is transparent）
                    to_append = profileIconId if i == 28 else ""
                elif profileIconId in summonerIcons:
                    to_append = summonerIcons[profileIconId].get(key.split("_")[1], profileIconId if i == 28 else "")
                else:
                    if not profileIconId in unmapped_keys["summonerIcon"]:
                        unmapped_keys["summonerIcon"].add(profileIconId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, profileIconId, i, key, profileIconId, matchId, version), verbose = verbose)
                    to_append = profileIconId if i == 28 else ""
            else:
                to_append = LoLGame_summary["participantIdentities"][participantIndex]["player"][key]
        elif i <= 42:
            if i == 31: #最高段位（`highestAchievedSeasonTier`）
                to_append = tiers[LoLGame_summary["participants"][participantIndex]["highestAchievedSeasonTier"]]
            elif i >= 35 and i <= 37: #选用英雄序号相关键（`championId`-related keys）
                championId: int = LoLGame_summary["participants"][participantIndex][key.split("_")[0] + "Id"]
                if championId in LoLChampions:
                    to_append = LoLChampions[championId][key.split("_")[1]]
                else:
                    if not championId in unmapped_keys["LoLChampion"]:
                        unmapped_keys["LoLChampion"].add(championId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                    to_append = championId if i == 35 else ""
            elif i >= 38 and i <= 41: #召唤师技能序号相关键（SpellIds-related keys）
                spellId: int = LoLGame_summary["participants"][participantIndex][key.split("_")[0] + "Id"]
                if spellId == 0: #2024年更新人机对战之前，在对局记录中记录的电脑玩家的召唤师技能序号都是0。在加载界面，玩家总是会看到电脑玩家携带了净化和惩戒，在进游戏后即表现为正常（Before Co-op vs. AI was updated in 2024, spellIds of all bots recorded in the match history are 0. In the loading screen, player always saw the bot players taking Cleanse and Smite, while the spells became normal after players enter the game）
                    to_append = spellId if i <= 39 else ""
                elif spellId in spells:
                    to_append = spells[spellId][key.split("_")[1]]
                else:
                    if not spellId in unmapped_keys["spell"]:
                        unmapped_keys["spell"].add(spellId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, spellId, i, key, spellId, matchId, version), verbose = verbose)
                    to_append = spellId if i <= 39 else ""
            elif i == 42: #阵营（`team_color`）
                to_append = team_colors_int[LoLGame_summary["participants"][participantIndex]["teamId"]]
            else:
                to_append = LoLGame_summary["participants"][participantIndex][key]
        elif i <= 224:
            if i == 132: #角色绑定装备：临时应付正式服15.24版本、测试服16.1版本的情形（`roleBoundItem`: a temporary solution to handle the period when Live is v25.24 and PBE is 16.1）
                to_append = stats.get("roleBoundItem", "")
            elif i >= 160 and i <= 173: #英雄联盟装备相关键（LoLItems-related keys）
                itemId: int = stats[key.split("_")[0]]
                if itemId == 0:
                    to_append = ""
                elif itemId in LoLItems:
                    to_append = LoLItems[itemId][key.split("_")[1]]
                else:
                    if not itemId in unmapped_keys["LoLItem"]:
                        unmapped_keys["LoLItem"].add(itemId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                    to_append = itemId if i <= 166 else ""
            elif i >= 174 and i <= 191: #符文相关键（Perks-related keys）
                if i <= 179:
                    perkId: int = stats[key[:5]]
                    if perkId == 0:
                        to_append = ""
                    elif perkId in perks:
                        perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                        to_append = perk_EndOfGameStatDescs
                    else:
                        if not perkId in unmapped_keys["perk"]:
                            unmapped_keys["perk"].add(perkId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkId, i, key, perkId, matchId, version), verbose = verbose)
                        to_append = ""
                else:
                    perkId = stats[key.split("_")[0]]
                    if perkId == 0:
                        to_append = ""
                    elif perkId in perks:
                        to_append = perks[perkId][key.split("_")[1]]
                    else:
                        if not perkId in unmapped_keys["perk"]:
                            unmapped_keys["perk"].add(perkId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkId, i, key, perkId, matchId, version), verbose = verbose)
                        to_append = perkId if i <= 185 else ""
            elif i >= 192 and i <= 195: #符文系相关键（Perkstyles-related keys）
                perkstyleId: int = stats[key.split("_")[0]]
                if perkstyleId == 0:
                    to_append = ""
                elif perkstyleId in perkstyles:
                    to_append = perkstyles[perkstyleId][key.split("_")[1]]
                else:
                    if not perkstyleId in unmapped_keys["perkstyle"]:
                        unmapped_keys["perkstyle"].add(perkstyleId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkstyleId, i, key, perkstyleId, matchId, version), verbose = verbose)
                    to_append = perkstyleId if (i - 192) % 2 == 0 else ""
            elif i >= 196 and i <= 213: #强化符文相关键（Augment-related keys）
                CherryAugmentId: int = stats[key.split("_")[0]]
                if CherryAugmentId == 0:
                    to_append = ""
                elif CherryAugmentId in CherryAugments:
                    if i <= 201: #强化符文名称（`nameTRA`）
                        to_append = CherryAugments[CherryAugmentId][key.split("_")[1]]
                    elif i <= 207: #强化符文图标路径（`augmentIconPath`）
                        to_append = CherryAugments[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png")
                    else: #强化符文等级（`rarity`）
                        to_append = augment_rarity[CherryAugments[CherryAugmentId][key.split("_")[1]]]
                else:
                    if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                        unmapped_keys["CherryAugment"].add(CherryAugmentId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, CherryAugmentId, i, key, CherryAugmentId, matchId, version), verbose = verbose)
                    to_append = CherryAugmentId if i <= 201 else ""
            elif i == 214: #子阵营（`playerSubteamColor`）
                to_append = subteam_colors[stats["playerSubteamId"]]
            elif i == 215 or i == 216: #角色绑定装备相关键（Role bound item-related keys）
                if "roleBoundItem" in stats:
                    roleBoundItemId: int = stats["roleBoundItem"]
                    if roleBoundItemId == 0:
                        to_append = ""
                    elif roleBoundItemId in LoLItems:
                        to_append = LoLItems[roleBoundItemId][key.split("_")[1]]
                    else:
                        if not roleBoundItemId in unmapped_keys["LoLItem"]:
                            unmapped_keys["LoLItem"].add(roleBoundItemId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, roleBoundItemId, i, key, roleBoundItemId, matchId, version), verbose = verbose)
                        to_append = roleBoundItemId if i == 215 else ""
                else:
                    to_append = ""
            elif i == 217: #击杀/死亡/助攻（`K/D/A`）
                to_append = "/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])])
            elif i == 218: #战损比（`KDA`）
                to_append = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"])
            elif i == 219: #补刀（`CS`）
                to_append = stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]
            elif i == 220: #分均经济（`GPM`）
                to_append = 0 if LoLGame_summary["gameDuration"] == 0 else stats["goldEarned"] * 60 / LoLGame_summary["gameDuration"]
            elif i == 221: #金币利用率（`GUE` - Gold Utilization Efficiency）
                to_append = 0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"]
            elif i == 222: #分均补刀（`CSPM`）
                to_append = 0 if LoLGame_summary["gameDuration"] == 0 else (stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]) * 60 / LoLGame_summary["gameDuration"]
            elif i == 223: #伤害转化率（`D/G`）
                to_append = 0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"]
            elif i == 224: #胜负（`win/lose`）
                to_append = "被终止" if LoLGame_summary["endOfGameResult"] == "Abort_AntiCheatExit" else "胜利" if stats["win"] else "失败"
            else:
                to_append = stats[key]
        elif i <= 228:
            if bans == []: #修改说明：以前判断禁用数据是否为空是通过禁用模式进行的，如果禁用模式是经典策略就记录禁用信息，否则直接追加空值到列表中。但是在终极魔典中，先前版本记录禁用信息，后来却不记录了。因此，这里判断禁用数据是否为空，直接通过判断bans是否为空【Modification note: To judge whether the ban information of a match is empty, banMode (teams\bans) is used: if banMode is StandardBanStrategy, record the ban information; otherwise, append empty values to the list (by player_count times). But in Ultbook, ban information is recorded in previous versions but not anymore recorded later. Therefore, to judge whether the ban information is empty, whether the variable bans is empty is directly checked】
                to_append = ""
            else:
                if LoLGame_summary["queueId"] == 0 or LoLGame_summary["gameMode"] == "JADE":
                    if LoLGame_summary["participants"][participantIndex]["teamId"] == 100:
                        if not legacy_banData_appended[100]:
                            if i == 225:
                                to_append = list(map(lambda x: x["championId"], bans_team100))
                            else:
                                championIds: list[int] = list(map(lambda x: x["championId"], bans_team100))
                                championNames: list[str | int] = []
                                for championId in championIds:
                                    if championId in LoLChampions:
                                        championNames.append(LoLChampions[championId][key.split("_")[1]])
                                    else:
                                        if not championId in unmapped_keys["LoLChampion"]:
                                            unmapped_keys["LoLChampion"].add(championId)
                                            logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                        championNames.append(championId if i == 226 else "")
                                to_append = championNames
                            if i == 228:
                                legacy_banData_appended[100] = True
                        else:
                            to_append = ""
                    elif LoLGame_summary["participants"][participantIndex]["teamId"] == 200:
                        if not legacy_banData_appended[200]:
                            if i == 225:
                                to_append = list(map(lambda x: x["championId"], bans_team200))
                            else:
                                championIds = list(map(lambda x: x["championId"], bans_team200))
                                championNames = []
                                for championId in championIds:
                                    if championId in LoLChampions:
                                        championNames.append(LoLChampions[championId][key.split("_")[1]])
                                    else:
                                        if not championId in unmapped_keys["LoLChampion"]:
                                            unmapped_keys["LoLChampion"].add(championId)
                                            logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                        championNames.append(championId if i == 226 else "")
                                to_append = championNames
                            if i == 228:
                                legacy_banData_appended[200] = True
                        else:
                            to_append = ""
                    else:
                        to_append = ""
                else:
                    if bans[participantIndex]["championId"] == -1:
                        to_append = ""
                    else:
                        if i == 225:
                            to_append = bans[participantIndex]["championId"]
                        else:
                            championId = bans[participantIndex]["championId"]
                            if championId in LoLChampions:
                                to_append = LoLChampions[championId][key.split("_")[1]]
                            else:
                                if not championId in unmapped_keys["LoLChampion"]:
                                    unmapped_keys["LoLChampion"].add(championId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                to_append = championId if i == 226 else ""
        elif i <= 230: #时间轴相关键（Timeline-related keys）
            to_append = lanes[timeline[key]] if i == 229 else roles[timeline[key]]
        elif i == 231: #是否队友？（`isAlly`）
            to_append = current_participantId != 0 and (LoLGame_summary["gameMode"] == "CHERRY" and stats["playerSubteamId"] == current_participant["stats"]["playerSubteamId"] or LoLGame_summary["gameMode"] != "CHERRY" and LoLGame_summary["participants"][participantIndex]["teamId"] == current_participant["teamId"])
        else: #对局概要转换键（Keys transformed according to game summary）
            subkey = key.split("_")[0]
            if key.endswith("_percent"): #团队占比键（Team percentage keys）
                if i == 290: #击杀参与率（`KP_percent`）
                    self_stat: int | float = stats["kills"] + stats["assists"]
                    total_stat: int | float = sum(map(lambda x: x["stats"]["kills"], team_participants))
                elif i == 291: #补刀数占比（`CS_percent`）
                    self_stat = stats["totalMinionsKilled"] + stats["neutralMinionsKilled"]
                    total_stat = sum(map(lambda x: x["stats"]["totalMinionsKilled"] + x["stats"]["neutralMinionsKilled"], team_participants))
                else:
                    self_stat = stats[subkey]
                    total_stat = sum(map(lambda x: x["stats"][subkey], team_participants))
                value = 0 if total_stat == 0 else self_stat / total_stat
                to_append = value
            else: #位次键（Order keys）
                if i == 351: #战损比位次（`KDA_order`）
                    self_stat = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"])
                    stat_list: list[int | float] = sorted(map(lambda x: (x["stats"]["kills"] + x["stats"]["assists"]) / max(1, x["stats"]["deaths"]), team_participants), reverse = True)
                elif i == 352: #击杀参与率位次（`KP_order`）
                    self_stat = stats["kills"] + stats["assists"]
                    stat_list = sorted(map(lambda x: x["stats"]["kills"] + x["stats"]["assists"], team_participants), reverse = True)
                elif i == 353: #补刀数位次（`CS_order`）
                    self_stat = stats["totalMinionsKilled"] + stats["neutralMinionsKilled"]
                    stat_list = sorted(map(lambda x: x["stats"]["totalMinionsKilled"] + x["stats"]["neutralMinionsKilled"], team_participants), reverse = True)
                elif i == 354: #伤害转化率位次（`D/G_order`）
                    self_stat = 0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"]
                    stat_list = sorted(map(lambda x: 0 if x["stats"]["goldEarned"] == 0 else x["stats"]["totalDamageDealtToChampions"] / x["stats"]["goldEarned"], team_participants), reverse = True)
                elif i == 355: #金币利用率位次（`GUE_order`）
                    self_stat = 0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"]
                    stat_list = sorted(map(lambda x: 0 if x["stats"]["goldEarned"] == 0 else x["stats"]["goldSpent"] / x["stats"]["goldEarned"], team_participants), reverse = True)
                else:
                    self_stat = stats[subkey]
                    stat_list = sorted(map(lambda x: x["stats"][subkey], team_participants), reverse = i != 298) #死亡次数越低，死亡位次越小（For deaths, the lower the number of deaths is, the smaller the death order is）
                to_append = 0 if len(set(stat_list)) == 1 else stat_list.index(self_stat) + 1 #当所有人的数据一样时，则不用比较位次（When some stat of every player is the same, there's no need to compare it）
        LoLGame_summary_data[key].append(to_append)
    return LoLGame_summary_data

def generate_LoLGameSummary_records_sgp(LoLGame_summary_data: dict[str, list[Any]], LoLGame_summary: dict[str, Any], participantIndex: int, queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], gameIndex: int = 1, current_puuid: str | list[str] = "", bans: Optional[list[dict[str, int]]] = None, legacy_banData_appended: Optional[dict[int, bool]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> dict[str, list[Any]]:
    '''
    向英雄联盟对局概要数据中追加记录。<br>Append records to LoL match summary data.
    
    :param LoLGame_summary_data: 英雄联盟对局概要数据。记录将追加到其中。<br>LoL match summary data. Records are appended into it.
    :type LoLGame_summary_data: dict[str, list[Any]]
    :param LoLGame_summary: 英雄联盟对局概要。通过以下SGP接口得到：<br>LoL match summary, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/lol/{match_id}/SUMMARY`
    :type LoLGame_summary: dict[str, Any]
    :param participantIndex: 主召唤师索引。从0开始。<br>The index of the main summoner, which starts from 0.
    :type participantIndex: int
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param current_puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type current_puuid: str | list[str]
    :param bans: 事先从对局概要中整理的禁用信息列表，每个元素是一个字典，包含选用顺序和禁用英雄序号。<br>Banned champion list prepared from the match summary in advance, where each element is a dictionary that contains pick order and banned championId.
    :type bans: list[dict[str, int]]
    :param legacy_banData_appended: 传统征召模式禁用信息已追加情况。键是阵营序号，值是表明禁用信息是否已追加过的逻辑值。<br>The status of whether legacy ban data have been appended. Each key is teamId, and each value is a boolean value that indicates whether the ban information has been appended.
    
        在传统征召模式的英雄选择阶段，每支队伍禁用三名英雄，全部由一名玩家禁用。因此，每支队伍只应追加禁用信息一次。<br>In the champ select stage of the legacy draft mode, each team bans three champions by a single player. Therefore, for each team, the ban information should be appended only once.
    :type legacy_banData_appended: dict[int, bool]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 追加数据后的英雄联盟对局概要数据。<br>LoL match summary data after appending.
    :rtype: dict[str, list[Any]]
    '''
    #参数预处理（Parameter pre-processing）
    if bans == None:
        bans = []
    if legacy_banData_appended == None:
        legacy_banData_appended = {100: False, 200: False}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    LoLGame_summary_json: dict[str, Any] = LoLGame_summary["json"]
    matchId: int = LoLGame_summary_json["gameId"]
    version: str = LoLGame_summary_json["gameVersion"]
    mapName: str = gamemaps[LoLGame_summary_json["mapId"]]["zh_CN"]
    stats: dict[str, Any] = LoLGame_summary_json["participants"][participantIndex]
    playerBehavior: dict[str, Any] = stats.get("PlayerBehavior", {})
    challenges: dict[str, Any] = stats.get("challenges", {})
    missions: dict[str, float] = stats.get("missions", {})
    bans_team100: list[dict[str, int]] = []
    bans_team200: list[dict[str, int]] = []
    for i in range(len(LoLGame_summary_json["teams"])):
        if LoLGame_summary_json["teams"][i]["teamId"] == 100:
            bans_team100 = LoLGame_summary_json["teams"][i]["bans"]
        elif LoLGame_summary_json["teams"][i]["teamId"] == 200:
            bans_team200 = LoLGame_summary_json["teams"][i]["bans"]
    current_participant_found: bool = False
    current_participantId: int = 0
    current_participant: dict[str, Any] = {}
    for participant in LoLGame_summary_json["participants"]:
        for puuid in puuidList:
            if participant["puuid"] == puuid:
                current_participantId = participant["participantId"]
                current_participant_found: bool = True
                break #注意，这里是找到一个对应的玩家通用唯一识别码，即找到一名玩家就退出循环。因为传入玩家通用唯一识别码的主要目的是区别敌我，而如果自己的多个账号在一场对局中同时出现，需要选择一个账号所在阵营视为友方。这里选择的是第一个账号所在阵营（Note that once a puuid, or a player is found, the program exits the loop. This is because the main purpose of passing the puuid is to distinguish the ally team and the enemy team. If the user's multiple accounts are present in a match at the same time, the ally team should be the team of one account. Here we take the team of the account first found in the match as the ally team）
        if current_participant_found:
            break
    if current_participant_found:
        for participant in LoLGame_summary_json["participants"]:
            if participant["participantId"] == current_participantId:
                current_participant = participant
                break
    else:
        current_participantId = 0 #如果出现数据异常，也认为目标玩家不存在于该对局中（If an error occurs to the data, consider this player isn't in this match）
    team_participants: list[dict[str, Any]] = [participant for participant in LoLGame_summary_json["participants"] if LoLGame_summary_json["gameMode"] == "CHERRY" and participant["playerSubteamId"] == stats["playerSubteamId"] or LoLGame_summary_json["gameMode"] != "CHERRY" and participant["teamId"] == stats["teamId"]] #存储对局概要中同一队伍的玩家。斗魂竞技场对局应该使用子阵营（Store the participants of the same team from the game summary. Subteam should be used to evaluate a player）
    if LoLGame_summary_json["mapId"] == 12:
        if not "gameModeMutators" in LoLGame_summary_json:
            mapName = "嚎哭深渊"
        elif "mapskin_map12_bloom" in LoLGame_summary_json["gameModeMutators"]:
            mapName = "莲华栈桥"
        elif "mapskin_ha_bilgewater" in LoLGame_summary_json["gameModeMutators"]:
            mapName = "屠夫之桥"
        elif "mapskin_ha_crepe" in LoLGame_summary_json["gameModeMutators"]:
            mapName = "进步之桥"
        elif "mapskin_map12_jade" in LoLGame_summary_json["gameModeMutators"]:
            mapName = "LCU_Map12_Name_Jade"
        else:
            mapName = "嚎哭深渊"
    #数据整理核心部分（Data organization core part）
    LoLGame_summary_header: dict[str, str] = LoLGame_summary_sgp_header #通过在函数内指定同名变量，使得其不再使用全局变量，并减少以下代码的修改（By specifying the variable with the same name, this variable is no longer the global one, and meanwhile the following code doesn't need changing much）
    LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
    for i in range(len(LoLGame_summary_header_keys)):
        key: str = LoLGame_summary_header_keys[i]
        if i == 0: #游戏序号（`gameIndex`）
            to_append: Any = gameIndex
        elif i <= 8: #元数据子键（`metadata`'s subkeys）
            if i == 3: #所有玩家（`participants`）
                to_append = json.dumps(LoLGame_summary["metadata"]["participants"])
            elif i == 4 or i == 5:
                to_append = int(LoLGame_summary["metadata"][key])
            else:
                to_append = LoLGame_summary["metadata"][key]
        elif i <= 30:
            if i == 9: #对局终止情况（`endOfGameResult`）
                to_append = endOfGameResults[LoLGame_summary_json["endOfGameResult"]] if "endOfGameResult" in LoLGame_summary_json else ""
            elif i == 15: #游戏模式配置（`gameModeMutators`）
                to_append = json.dumps(LoLGame_summary_json["gameModeMutators"]) if "gameModeMutators" in LoLGame_summary_json else ""
            elif i == 18: #游戏类型（`gameType`）
                to_append = gameTypes_history[LoLGame_summary_json["gameType"]] if "gameType" in LoLGame_summary_json else ""
            elif i == 25: #创建日期（`gameCreationDate`）
                to_append = getISOTime(LoLGame_summary_json["gameCreation"] / 1000) if "gameCreation" in LoLGame_summary_json else ""
            elif i == 26: #持续时长（`gameDuration_norm`）
                to_append = lcuTime(LoLGame_summary_json["gameDuration"]) if "gameDuration" in LoLGame_summary_json else ""
            elif i == 27: #结束时间（`gameEndTime`）
                to_append = getISOTime(LoLGame_summary_json["gameEndTimestamp"] / 1000) if "gameEndTimestamp" in LoLGame_summary_json else ""
            elif i == 28: #开始时间（`gameStartTime`）
                to_append = getISOTime(LoLGame_summary_json["gameStartTimestamp"] / 1000) if "gameStartTimestamp" in LoLGame_summary_json else ""
            elif i == 29: #游戏模式名称（`gameModeName`）
                to_append = "自定义" if LoLGame_summary_json["queueId"] == 0 else queues[LoLGame_summary_json["queueId"]]["name"] if LoLGame_summary_json["queueId"] in queues else ""
            elif i == 30: #地图名称（`mapName`）
                to_append = mapName
            else:
                to_append = LoLGame_summary_json.get(key, "")
        elif i <= 236:
            if i <= 42: #玩家得分键（Player score keys）
                to_append = stats[key] if key in stats else stats[decapitalize(key)] if decapitalize(key) in stats else ""
            elif i in {50, 68, 76, 150, 180, 181, 182}: #可变逻辑值键（Mutable boolean keys）
                to_append = stats.get(key, False)
            elif i == 57: #购买消耗品（`consumablePurchased`）
                to_append = stats["consumablesPurchased"] if "consumablesPurchased" in stats else stats["consumablePurchased"] if "consumablePurchased" in stats else ""
            elif i in {82, 125, 152}: #角色定位（`individualPosition`, `positionAssignedByMatchmaking` and `teamPosition`）
                to_append = positions[stats[key]] if key in stats else ""
            elif i == 96: #分路（`lane`）
                to_append = lanes[stats["lane"]] if "lane" in stats else ""
            elif i == 103: #承受的魔法伤害（`magicalDamageTaken`）
                to_append = stats["magicalDamageTaken"] if "magicalDamageTaken" in stats else stats["magicDamageTaken"] if "magicDamageTaken" in stats else ""
            elif i == 131: #玩家名称（`riotIdGameName`）
                to_append = stats["riotIdGameName"] if "riotIdGameName" in stats else stats["riotIdName"] if "riotIdName" in stats else ""
            elif i == 133: #角色定位（`role`）
                to_append = roles[stats["role"]] if "role" in stats else ""
            elif i == 184 or i == 185: #选用英雄序号相关键（`championId`-related keys）
                championId: int = stats["championId"]
                if championId in LoLChampions:
                    to_append = LoLChampions[championId][key.split("_")[1]]
                else:
                    if not championId in unmapped_keys["LoLChampion"]:
                        unmapped_keys["LoLChampion"].add(championId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                    to_append = championId if i == 184 else ""
            elif i >= 186 and i <= 199: #英雄联盟装备相关键（LoLItems-related keys）
                subkey: str = key.split("_")[0]
                if subkey in stats:
                    itemId: int = stats[subkey]
                    if itemId == 0:
                        to_append = ""
                    elif itemId in LoLItems:
                        to_append = LoLItems[itemId][key.split("_")[1]]
                    else:
                        if not itemId in unmapped_keys["LoLItem"]:
                            unmapped_keys["LoLItem"].add(itemId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                        to_append = itemId if i <= 192 else ""
                else:
                    to_append = ""
            elif i >= 200 and i <= 217: #强化符文相关键（Augment-related keys）
                subkey = key.split("_")[0]
                if subkey in stats:
                    CherryAugmentId: int = stats[subkey]
                    if CherryAugmentId == 0:
                        to_append = ""
                    elif CherryAugmentId in CherryAugments:
                        if i <= 205: #强化符文名称（`nameTRA`）
                            to_append = CherryAugments[CherryAugmentId][key.split("_")[1]]
                        elif i <= 211: #强化符文图标路径（`augmentIconPath`）
                            to_append = CherryAugments[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png")
                        else: #强化符文等级（`rarity`）
                            to_append = augment_rarity[CherryAugments[CherryAugmentId][key.split("_")[1]]]
                    else:
                        if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                            unmapped_keys["CherryAugment"].add(CherryAugmentId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, CherryAugmentId, i, key, CherryAugmentId, matchId, version), verbose = verbose)
                        to_append = CherryAugmentId if i <= 205 else ""
                else:
                    to_append = ""
            elif i == 218: #子阵营（`playerSubteamColor`）
                to_append = subteam_colors[stats["playerSubteamId"]] if "playerSubteamId" in stats else ""
            elif i == 219 or i == 220: #召唤师图标相关键（Profile icon-related keys）
                if "profileIcon" in stats:
                    profileIconId: int = stats["profileIcon"]
                    if profileIconId == -1: #早期存在一个空图标（There was once an empty icon, which is transparent）
                        to_append = profileIconId if i == 219 else ""
                    elif profileIconId in summonerIcons:
                        to_append = summonerIcons[profileIconId].get(key.split("_")[1], profileIconId if i == 219 else "")
                    else:
                        if not profileIconId in unmapped_keys["summonerIcon"]:
                            unmapped_keys["summonerIcon"].add(profileIconId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, profileIconId, i, key, profileIconId, matchId, version), verbose = verbose)
                        to_append = profileIconId if i == 219 else ""
                else:
                    to_append = ""
            elif i == 221 or i == 222: #角色绑定装备相关键（Role bound item-related keys）
                if "roleBoundItem" in stats:
                    roleBoundItemId: int = stats["roleBoundItem"]
                    if roleBoundItemId == 0:
                        to_append = ""
                    elif roleBoundItemId in LoLItems:
                        to_append = LoLItems[roleBoundItemId][key.split("_")[1]]
                    else:
                        if not roleBoundItemId in unmapped_keys["LoLItem"]:
                            unmapped_keys["LoLItem"].add(roleBoundItemId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, roleBoundItemId, i, key, roleBoundItemId, matchId, version), verbose = verbose)
                        to_append = roleBoundItemId if i == 221 else ""
                else:
                    to_append = ""
            elif i >= 223 and i <= 226: #召唤师技能序号相关键（SpellIds-related keys）
                subkey = key.split("_")[0] + "Id"
                if subkey in stats:
                    spellId: int = stats[subkey]
                    if spellId == 0: #2024年更新人机对战之前，在对局记录中记录的电脑玩家的召唤师技能序号都是0。在加载界面，玩家总是会看到电脑玩家携带了净化和惩戒，在进游戏后即表现为正常（Before Co-op vs. AI was updated in 2024, spellIds of all bots recorded in the match history are 0. In the loading screen, player always saw the bot players taking Cleanse and Smite, while the spells became normal after players enter the game）
                        to_append = spellId if i <= 224 else ""
                    elif spellId in spells:
                        to_append = spells[spellId][key.split("_")[1]]
                    else:
                        if not spellId in unmapped_keys["spell"]:
                            unmapped_keys["spell"].add(spellId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, spellId, i, key, spellId, matchId, version), verbose = verbose)
                        to_append = spellId if i <= 224 else ""
                else:
                    to_append = ""
            elif i == 227: #阵营（`team_color`）
                to_append = team_colors_int[stats["teamId"]] if "teamId" in stats else ""
            elif i == 228: #英雄技能总施放次数（`totalSpellCasts`）
                subkeyList: list[str] = ["spell1Casts", "spell2Casts", "spell3Casts", "spell4Casts"]
                totalSpellCasts: int = 0
                if any(map(lambda x: x in stats, subkeyList)):
                    for subkey in subkeyList:
                        totalSpellCasts += stats.get(subkey, 0)
                    to_append = totalSpellCasts
                else: #如果完全没有这些键，则也不应为此键设置值（If none of these keys exists, then this key shouldn't be set as any value）
                    to_append = ""
            elif i == 229: #击杀/死亡/助攻（`K/D/A`）
                to_append = "/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])]) if all(map(lambda x: x in stats, ["kills", "deaths", "assists"])) else ""
            elif i == 230: #战损比（`KDA`）
                to_append = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"]) if all(map(lambda x: x in stats, ["kills", "deaths", "assists"])) else ""
            elif i == 231: #补刀（`CS`）
                to_append = stats["neutralMinionsKilled"] + stats["totalMinionsKilled"] if all(map(lambda x: x in stats, ["neutralMinionsKilled", "totalMinionsKilled"])) else ""
            elif i == 232: #分均经济（`GPM`）
                to_append = (0 if LoLGame_summary_json["gameDuration"] == 0 else stats["goldEarned"] * 60 / LoLGame_summary_json["gameDuration"]) if "gameDuration" in LoLGame_summary_json and "goldEarned" in stats else ""
            elif i == 233: #金币利用率（`GUE` - Gold Utilization Efficiency）
                to_append = (0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"]) if all(map(lambda x: x in stats, ["goldSpent", "goldEarned"])) else ""
            elif i == 234: #分均补刀（`CSPM`）
                to_append = (0 if LoLGame_summary_json["gameDuration"] == 0 else (stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]) * 60 / LoLGame_summary_json["gameDuration"]) if "gameDuration" in LoLGame_summary_json and all(map(lambda x: x in stats, ["neutralMinionsKilled", "totalMinionsKilled"])) else ""
            elif i == 235: #伤害转化率（`D/G`）
                to_append = (0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"]) if all(map(lambda x: x in stats, ["goldEarned", "totalDamageDealtToChampions"])) else ""
            elif i == 236: #胜负（`win/lose`）
                to_append = "被终止" if "endOfGameResult" in LoLGame_summary_json and LoLGame_summary_json["endOfGameResult"] == "Abort_AntiCheatExit" else "" if not "win" in stats else "胜利" if stats["win"] else "失败"
            else:
                to_append = stats.get(key, "")
        elif i == 237: #玩家行为子键（`PlayerBehavior`'s subkeys）
            if "PlayerBehavior" in stats:
                to_append = playerBehavior.get(key.split()[1], "")
            else:
                to_append = ""
        elif i <= 385: #成就子键（`challenges`' subkeys）
            if "challenges" in stats:
                if i == 319: #成就：【传说武器：2024 - 第1赛段】（带着<em>不同的传说装备</em>赢得对局）游戏结束时使用的传说装备序号（`challenges legendaryItemUsed`）
                    to_append = json.dumps(list(map(int, challenges["legendaryItemUsed"])), ensure_ascii = False) if "legendaryItemUsed" in challenges else ""
                elif i == 330: #成就：【神话武器大师】（用<em>不同的神话装备</em>赢得对局）使用的神话装备序号（`challenges mythicItemUsed`）
                    to_append = int(challenges["mythicItemUsed"]) if "mythicItemUsed" in challenges else ""
                elif i == 381: #成就：【别把龙晾太久】（在8分钟之前参与击杀第一条龙）最早参与击杀巨龙时间（`challenges earliestDragonTakedown_norm`）
                    to_append = lcuTime(challenges["earliestDragonTakedown"]) if "earliestDragonTakedown" in challenges else ""
                elif i == 382: #成就：最快的传说装备构建时间（`challenges fastestLegendary_norm`）
                    to_append = lcuTime(challenges["fastestLegendary"]) if "fastestLegendary" in challenges else ""
                elif i == 383: #成就：【速拆一塔】（在10分钟之前拿下【第一座塔】）【疾速拆塔】（在5分钟之前拿下【第一座塔】）第一座塔摧毁时间（`challenges firstTurretKilledTime_norm`）
                    to_append = lcuTime(challenges["firstTurretKilledTime"]) if "firstTurretKilledTime" in challenges else ""
                elif i == 384: #成就：【传说武器：2024 - 第1赛段】（带着<em>不同的传说装备</em>赢得对局）游戏结束时使用的传说装备名称（`challenges legendaryItemUsed_names`）
                    if "legendaryItemUsed" in challenges: #此处的装备序号不需要放到其父函数的数据资源异常处理机制中。为什么？（Here this itemId doesn't need to be put in the data resource exceptional handling mechanism part. Why?）
                        legendaryItemsUsed: list[str | int] = []
                        for itemId in challenges["legendaryItemUsed"]:
                            if itemId == 0:
                                legendaryItemsUsed.append("")
                            elif itemId in LoLItems:
                                legendaryItemsUsed.append(LoLItems[itemId]["name"])
                            else:
                                if not itemId in unmapped_keys["LoLItem"]:
                                    unmapped_keys["LoLItem"].add(itemId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                                legendaryItemsUsed.append(itemId)
                        to_append = json.dumps(legendaryItemsUsed, ensure_ascii = False)
                    else:
                        to_append = ""
                elif i == 385: #成就：【神话武器大师】（用<em>不同的神话装备</em>赢得对局）使用的神话装备名称（`challenges mythicItemUsed_name`）
                    if "mythicItemUsed" in challenges:
                        itemId: int = challenges["mythicItemUsed"]
                        if itemId == 0:
                            to_append = ""
                        elif itemId in LoLItems:
                            to_append = LoLItems[itemId]["name"]
                        else:
                            if not itemId in unmapped_keys["LoLItem"]:
                                unmapped_keys["LoLItem"].add(itemId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                            to_append = ""
                    else:
                        to_append = ""
                else:
                    to_append = challenges.get(key.split()[1], "")
            else:
                to_append = ""
        elif i <= 566: #任务子键（`missions`' subkeys）
            subkey: str = key.split()[1]
            if i >= 546 and i <= 557: #任务：玩家得分相关键（Mission: PlayerScore related keys）
                to_append = missions.get(subkey, missions.get(decapitalize(subkey), ""))
            else:
                to_append = missions.get(subkey, "")
        elif i <= 623: #符文子键（`perks`' subkeys）
            if i == 570: #主系序号（`perkPrimaryStyle`）
                to_append = stats["perks"]["styles"][0]["style"] if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 else ""
            elif i >= 571 and i <= 586: #主系符文相关键（Primary style's perk related keys）
                perkCount: int = 1 + (i - 571) // 4
                if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 and "selections" in stats["perks"]["styles"][0] and len(stats["perks"]["styles"][0]["selections"]) >= perkCount:
                    remainder: int = (i - 571) % 4
                    perk: dict[str, int] = stats["perks"]["styles"][0]["selections"][perkCount - 1]
                    if remainder == 0: #符文序号相关键（PerkId related keys）
                        to_append = perk["perk"]
                    else:
                        to_append = perk[f"var{remainder}"]
                else:
                    to_append = ""
            elif i == 587: #副系序号（`perkSubStyle`）
                to_append = stats["perks"]["styles"][1]["style"] if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 2 else ""
            elif i >= 588 and i <= 595: #副系符文相关键（Substyle's perk related keys）
                perkCount: int = 1 + (i - 588) // 4
                if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 and "selections" in stats["perks"]["styles"][1] and len(stats["perks"]["styles"][0]["selections"]) >= perkCount:
                    remainder: int = (i - 588) % 4
                    perk: dict[str, int] = stats["perks"]["styles"][1]["selections"][perkCount - 1]
                    if remainder == 0: #符文序号相关键（PerkId related keys）
                        to_append = perk["perk"]
                    else:
                        to_append = perk[f"var{remainder}"]
                else:
                    to_append = ""
            elif i >= 596 and i <= 601 or i >= 604 and i <= 615 or i >= 618: #属性符文子键（`statPerks`' subkeys）
                perkId_got: bool = False
                perkId: int = 0
                perkVar1: int = 0
                perkVar2: int = 0
                perkVar3: int = 0
                if i >= 596 and i <= 601: #属性符文子键（`statPerks`' subkeys）
                    subkey = key.split("_")[0].split()[1]
                    if "perks" in stats and "statPerks" in stats["perks"] and subkey in stats["perks"]["statPerks"]:
                        perkId = stats["perks"]["statPerks"][subkey]
                        perkId_got = True
                elif i >= 604 and i <= 615: #主系符文子键（Primary style's perk's subkeys）
                    perkCount: int = int(key.split("_")[0].split()[1][-1])
                    if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 and "selections" in stats["perks"]["styles"][0] and len(stats["perks"]["styles"][0]["selections"]) >= perkCount:
                        perk: dict[str, int] = stats["perks"]["styles"][0]["selections"][perkCount - 1]
                        perkId, perkVar1, perkVar2, perkVar3 = perk["perk"], perk["var1"], perk["var2"], perk["var3"]
                        perkId_got = True
                else: #副系符文子键（Secondary style's perk's subkeys）
                    perkCount = int(key.split("_")[0].split()[1][-1])
                    if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 2 and "selections" in stats["perks"]["styles"][1] and len(stats["perks"]["styles"][1]["selections"]) >= perkCount:
                        perk = stats["perks"]["styles"][1]["selections"][perkCount - 1]
                        perkId, perkVar1, perkVar2, perkVar3 = perk["perk"], perk["var1"], perk["var2"], perk["var3"]
                        perkId_got = True
                if perkId_got:
                    if perkId == 0:
                        to_append = ""
                    elif perkId in perks:
                        subkey: str = key.split("_")[1]
                        if subkey == "EndOfGameStatDescs":
                            perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(perkVar1))
                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(perkVar2))
                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(perkVar3))
                            to_append = perk_EndOfGameStatDescs
                        else:
                            to_append = perks[perkId][subkey]
                    else:
                        if not perkId in unmapped_keys["perk"]:
                            unmapped_keys["perk"].add(perkId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkId, i, key, perkId, matchId, version), verbose = verbose)
                        to_append = perkId if i <= 598 or i >= 608 and i <= 611 or i == 620 or i == 621 else ""
                else:
                    to_append = ""
            elif i in {602, 603, 616, 617}: #符文系相关键（Perkstyle related keys）
                perkstyleId_got: bool = False
                perkstyleId: int = 0
                if i == 602 or i == 603: #主系相关键（Primary style related keys）
                    if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 1 and "style" in stats["perks"]["styles"][0]:
                        perkstyleId = stats["perks"]["styles"][0]["style"]
                        perkstyleId_got = True
                else: #副系相关键（Secondary style related keys）
                    if "perks" in stats and "styles" in stats["perks"] and len(stats["perks"]["styles"]) >= 2 and "style" in stats["perks"]["styles"][1]:
                        perkstyleId = stats["perks"]["styles"][1]["style"]
                        perkstyleId_got = True
                if perkstyleId_got:
                    if perkstyleId == 0:
                        to_append = ""
                    elif perkstyleId in perkstyles:
                        to_append = perkstyles[perkstyleId][key.split("_")[1]]
                    else:
                        if not perkstyleId in unmapped_keys["perkstyle"]:
                            unmapped_keys["perkstyle"].add(perkstyleId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, perkstyleId, i, key, perkstyleId, matchId, version), verbose = verbose)
                        to_append = perkstyleId if i == 602 or i == 616 else ""
                else:
                    to_append = ""
            else:
                if "perks" in stats and "statPerks" in stats["perks"]:
                    to_append = stats["perks"]["statPerks"][key.split()[1]]
                else:
                    to_append = ""
        elif i <= 627:
            if bans == []: #修改说明：以前判断禁用数据是否为空是通过禁用模式进行的，如果禁用模式是经典策略就记录禁用信息，否则直接追加空值到列表中。但是在终极魔典中，先前版本记录禁用信息，后来却不记录了。因此，这里判断禁用数据是否为空，直接通过判断bans是否为空【Modification note: To judge whether the ban information of a match is empty, banMode (teams\bans) is used: if banMode is StandardBanStrategy, record the ban information; otherwise, append empty values to the list (by player_count times). But in Ultbook, ban information is recorded in previous versions but not anymore recorded later. Therefore, to judge whether the ban information is empty, whether the variable bans is empty is directly checked】
                to_append = ""
            else:
                if LoLGame_summary_json["queueId"] == 0 or LoLGame_summary_json["gameMode"] == "JADE":
                    if stats["teamId"] == 100:
                        if not legacy_banData_appended[100]:
                            if i == 624:
                                to_append = list(map(lambda x: x["championId"], bans_team100))
                            else:
                                championIds: list[int] = list(map(lambda x: x["championId"], bans_team100))
                                championNames: list[str | int] = []
                                for championId in championIds:
                                    if championId in LoLChampions:
                                        championNames.append(LoLChampions[championId][key.split("_")[1]])
                                    else:
                                        if not championId in unmapped_keys["LoLChampion"]:
                                            unmapped_keys["LoLChampion"].add(championId)
                                            logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                        championNames.append(championId if i == 625 else "")
                                to_append = championNames
                            if i == 627:
                                legacy_banData_appended[100] = True
                        else:
                            to_append = ""
                    elif stats["teamId"] == 200:
                        if not legacy_banData_appended[200]:
                            if i == 624:
                                to_append = list(map(lambda x: x["championId"], bans_team200))
                            else:
                                championIds = list(map(lambda x: x["championId"], bans_team200))
                                championNames = []
                                for championId in championIds:
                                    if championId in LoLChampions:
                                        championNames.append(LoLChampions[championId][key.split("_")[1]])
                                    else:
                                        if not championId in unmapped_keys["LoLChampion"]:
                                            unmapped_keys["LoLChampion"].add(championId)
                                            logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                        championNames.append(championId if i == 625 else "")
                                to_append = championNames
                            if i == 627:
                                legacy_banData_appended[200] = True
                        else:
                            to_append = ""
                    else:
                        to_append = ""
                else:
                    if bans[participantIndex]["championId"] == -1:
                        to_append = ""
                    else:
                        if i == 624:
                            to_append = bans[participantIndex]["championId"]
                        else:
                            championId = bans[participantIndex]["championId"]
                            if championId in LoLChampions:
                                to_append = LoLChampions[championId][key.split("_")[1]]
                            else:
                                if not championId in unmapped_keys["LoLChampion"]:
                                    unmapped_keys["LoLChampion"].add(championId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                to_append = championId if i == 625 else ""
        elif i == 628: #是否队友？（`isAlly`）
            to_append = current_participantId != 0 and (LoLGame_summary_json["gameMode"] == "CHERRY" and stats["playerSubteamId"] == current_participant["playerSubteamId"] or LoLGame_summary_json["gameMode"] != "CHERRY" and stats["teamId"] == current_participant["teamId"])
        else: #对局概要转换键（Keys transformed according to game summary）
            subkey = key.split("_")[0]
            if key.endswith("_percent"): #团队占比键（Team percentage keys）
                if i == 727: #英雄技能总施放次数占比（`totalSpellCasts_percent`）
                    subkeyList: list[str] = ["spell1Casts", "spell2Casts", "spell3Casts", "spell4Casts"]
                    self_stat: int | float = 0
                    for subkey in subkeyList:
                        self_stat += stats.get(subkey, 0)
                    total_stat: int | float = 0
                    for participant in team_participants:
                        for subkey in subkeyList:
                            total_stat += participant.get(subkey, 0)
                elif i == 728: #击杀参与率（`KP_percent`）
                    self_stat = stats.get("kills", 0) + stats.get("assists", 0)
                    total_stat = sum(map(lambda x: x.get("kills", 0), team_participants))
                elif i == 729: #补刀数占比（`CS_percent`）
                    self_stat = stats.get("totalMinionsKilled", 0) + stats.get("neutralMinionsKilled", 0)
                    total_stat = sum(map(lambda x: x.get("totalMinionsKilled", 0) + x.get("neutralMinionsKilled", 0), team_participants))
                else:
                    self_stat = stats.get(subkey, 0)
                    total_stat = sum(map(lambda x: x.get(subkey, 0), team_participants))
                value = 0 if total_stat == 0 else self_stat / total_stat
                to_append = value
            else: #位次键（Order keys）
                if i == 829: #英雄技能总施放次数位次（`totalSpellCasts_order`）
                    subkeyList = ["spell1Casts", "spell2Casts", "spell3Casts", "spell4Casts"]
                    self_stat = 0
                    for subkey in subkeyList:
                        self_stat += stats.get(subkey, 0)
                    stat_list: list[int | float] = []
                    for participant in team_participants:
                        participant_stat: int | float = 0
                        for subkey in subkeyList:
                            participant_stat += participant.get(subkey, 0)
                        stat_list.append(participant_stat)
                elif i == 830: #战损比位次（`KDA_order`）
                    self_stat = (stats.get("kills", 0) + stats.get("assists", 0)) / max(1, stats.get("deaths", 0))
                    stat_list = sorted(map(lambda x: (x.get("kills", 0) + x.get("assists")) / max(1, x.get("deaths", 0)), team_participants), reverse = True)
                elif i == 831: #击杀参与率位次（`KP_order`）
                    self_stat = stats.get("kills", 0) + stats.get("assists", 0)
                    stat_list = sorted(map(lambda x: x.get("kills", 0) + x.get("assists", 0), team_participants), reverse = True)
                elif i == 832: #补刀数位次（`CS_order`）
                    self_stat = stats.get("totalMinionsKilled", 0) + stats.get("neutralMinionsKilled", 0)
                    stat_list = sorted(map(lambda x: x.get("totalMinionsKilled", 0) + x.get("neutralMinionsKilled", 0), team_participants), reverse = True)
                elif i == 833: #伤害转化率位次（`D/G_order`）
                    self_stat = 0 if stats.get("goldEarned", 0) == 0 else stats.get("totalDamageDealtToChampions", 0) / stats["goldEarned"]
                    stat_list = sorted(map(lambda x: 0 if x.get("goldEarned", 0) == 0 else x.get("totalDamageDealtToChampions", 0) / x["goldEarned"], team_participants), reverse = True)
                elif i == 834: #金币利用率位次（`GUE_order`）
                    self_stat = 0 if stats.get("goldEarned", 0) == 0 else stats.get("goldSpent", 0) / stats["goldEarned"]
                    stat_list = sorted(map(lambda x: 0 if x.get("goldEarned", 0) == 0 else x.get("goldSpent", 0) / x["goldEarned"], team_participants), reverse = True)
                else:
                    self_stat = stats.get(subkey, 0)
                    stat_list = sorted(map(lambda x: x.get(subkey, 0), team_participants), reverse = i != 759) #死亡次数越低，死亡位次越小（For deaths, the lower the number of deaths is, the smaller the death order is）
                to_append = 0 if len(set(stat_list)) == 1 else stat_list.index(self_stat) + 1 #当所有人的数据一样时，则不用比较位次（When some stat of every player is the same, there's no need to compare it）
        LoLGame_summary_data[key].append(to_append)
    return LoLGame_summary_data

def sort_LoLGame_summary(LoLGame_summary: dict[str, Any], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], gameIndex: int = 1, current_puuid: str | list[str] = "", useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, session: Optional[requests.Session] = None, sortStats: bool = False, LoLGame_stat_data: Optional[dict[str, list[Any]]] = None, save_self: bool = True, save_other: bool = True, save_bot: bool = False, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    '''
    将英雄联盟对局概要中的玩家信息整理成一张表格。<br>Organize player information in a LoL match summary into a dataframe.
    
    :param LoLGame_summary: 英雄联盟对局概要。通过以下LCU接口得到：<br>LoL match summary, obtained through the following LCU endpoint:
    
        - `GET /lol-match-history/v1/games/{gameId}`
    :type LoLGame_summary: dict[str, Any]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param current_puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type current_puuid: str | list[str]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[int]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param sortStats: 是否在整理对局概要数据的同时整理玩家战绩数据。默认为假。<br>Whether to organize player stats data while organizing the match summary data. False by default.
    :type sortStats: bool
    :param LoLGame_stat_data: 玩家战绩数据。相比对局概要数据，添加了对局元数据信息。<br>Player stat data, which additionally organize the match metadata compared with match summary.
    :type LoLGame_stat_data: dict[str, list[Any]]
    :param save_self: 在汇总玩家战绩时，是否保存主召唤师的数据。默认为真。<br>Whether to save the data of the main summoner when the program is summarizing player stats. True by default.
    :type save_self: bool
    :param save_other: 在汇总玩家战绩时，是否保存主召唤师以外的玩家数据。默认为真。<br>Whether to save the data of players except the main summoner when the program is summarizing player stats. True by default.
    :type save_other: bool
    :param save_bot: 在汇总玩家战绩时，是否保存电脑玩家的数据。默认为假。<br>Whether to save the data of bot players when the program is summarizing player stats. False by default.
    :type save_bot: bool
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 英雄联盟对局概要数据框，以及游戏队列、召唤师图标、英雄、召唤师技能、英雄联盟装备、符文、符文系和斗魂竞技场强化符文等数据资源的缓存。<br>LoL match summary dataframe, and data resources like queues, summoner icons, champions, summoner spells, LoL items, perks, perkstyles and Arena augments.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if session == None:
        session = requests.Session()
    if LoLGame_stat_data == None:
        LoLGame_stat_data = {key: [] for key in LoLGame_summary_header.keys()}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    version: str = LoLGame_summary["gameVersion"]
    bigVersion: str = ".".join(version.split(".")[:2])
    matchId: int = LoLGame_summary["gameId"]
    #整理对局禁用信息（Sort out the team ban information）
    if len(LoLGame_summary["teams"]) == 0: #对局创建后没有任何人进入游戏，如所有人在加载界面结束进程，或者服务器异常，对应的是这种情况（This is the case whether nobody enters the game after the match is created. For example, all players terminate the process during the loading phase, or something is wrong with the server）
        bans: list[dict[str, int]] = []
    elif len(LoLGame_summary["teams"]) == 1: #空对局也会进入历史记录。空对局定义为完成选英雄但是无法正常进入游戏，而后游戏不存在的对局。而训练模式的空对局只有一方，因此LoLGame_summary["teams"]中只有一个元素（Empty matches are included in the match history. An empty match is defined as the matches which can't be launched after the ChmpSlct period. Since an empty match of Practice Tool has only one team, there's only 1 element in LoLGame_summary["teams"]）
        bans = LoLGame_summary["teams"][0]["bans"]
    else:
        bans = LoLGame_summary["teams"][0]["bans"] + LoLGame_summary["teams"][1]["bans"]
        if len(LoLGame_summary["teams"]) > 2:
            logPrint("警告：对局%d中含有%d支阵营。\nWarning: There're %d teams in Match %d." %(matchId, len(LoLGame_summary["teams"]), len(LoLGame_summary["teams"]), matchId), verbose = verbose)
    if LoLGame_summary["gameMode"] == "CHERRY" and Patch("14.8") < Patch(version):
        bans_tmp: list[dict[str, int]] = bans[:]
        bans = []
        emptyBan: dict[str, int] = {"championId": -1, "pickTurn": 0} #定义一个初始化禁用字典，用于后续数据框填充空值（Define an initialized banning dictionary so that empty values are appended to the dataframe at certain times subsequently）
        playerSubteam: dict[int, list[int]] = {} #存储不同子阵营的玩家，键是子阵营序号，值是该子阵营中的玩家的API序号列表（Stores different subteams' players. Keys are playerSubteamIds, and values are index lists from API for players in the subteams）
        for i in range(len(LoLGame_summary["participants"])):
            bans.append(emptyBan.copy())
            playerSubteamId: int = LoLGame_summary["participants"][i]["stats"]["playerSubteamId"]
            if not playerSubteamId in playerSubteam:
                playerSubteam[playerSubteamId] = []
            playerSubteam[playerSubteamId].append(i)
        if Patch("14.12") < Patch(version):
            participantBanIds: list[int] = []
            for i in sorted(playerSubteam.keys()):
                participantBanIds += playerSubteam[i] #这里默认采用某个子阵营在API中记录的第一名玩家作为该子阵营的先选者。这可能与实际选用顺序有出入（Here the first player of a subteam recorded in API is considered as the player that picks a champion first. This player may not be the real first player.）
        else:
            participantBanIds = [playerSubteam[i][0] for i in sorted(playerSubteam.keys())] #这里默认采用某个子阵营在API中记录的第一名玩家作为禁用英雄的玩家。这可能与实际禁用英雄的玩家有出入（Here the first player of a subteam recorded in API is considered as the player that banned some champion. This player may not be the real player that banned it）
        for i in range(len(participantBanIds)):
            bans[participantBanIds[i]] = bans_tmp[i]
    legacy_banData_appended: dict[int, bool] = {100: False, 200: False} #自定义对局中的征召模式是由每个阵营的1号选手禁用3个英雄，所以当禁用信息添加到一个阵营的第一名玩家后，后续玩家不需要再添加禁用信息。这个字典就是用来判断这一点的（Draft mode in custom matches is performed by the first player of each team banning 3 champions, so if the ban information is added into the first player, the subsequent player in the same team doesn't need to add this information. That's what this dictionary is used for）
    #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
    if useAllVersions:
        ##游戏模式（Game mode）
        queueIds_match_list: list[int] = [LoLGame_summary["queueId"]]
        for i in queueIds_match_list:
            if not i in queues and current_versions["queue"] != bigVersion:
                queuePatch_adopted: str = bigVersion
                queue_recapture: int = 1
                logPrint("对局%d游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(matchId, i, queue_recapture, queuePatch_adopted, i, matchId, queuePatch_adopted, queue_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                        queue: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        queuePatch_deserted: str = queuePatch_adopted
                        queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                        queue_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if queue_recapture < 3:
                            queue_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game mode (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                        queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                        current_versions["queue"] = queuePatch_adopted
                        unmapped_keys["queue"].clear()
                        break
                break
        ##召唤师图标（Summoner icon）
        summonerIconIds_match_list: list[int] = sorted(set(map(lambda x: x["player"]["profileIcon"], LoLGame_summary["participantIdentities"])))
        for i in summonerIconIds_match_list:
            if not i in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                summonerIconPatch_adopted: str = bigVersion
                summonerIcon_recapture: int = 1
                logPrint("对局%d召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(matchId, i, summonerIcon_recapture, summonerIconPatch_adopted, i, matchId, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        summonerIcon: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        summonerIconPatch_deserted: str = summonerIconPatch_adopted
                        summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                        summonerIcon_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if summonerIcon_recapture < 3:
                            summonerIcon_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                        summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                        current_versions["summonerIcon"] = summonerIconPatch_adopted
                        unmapped_keys["summonerIcon"].clear()
                        break
                break
        ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
        LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: x["championId"], LoLGame_summary["participants"])) | set(map(lambda x: x["championId"], bans)))
        for i in LoLChampionIds_match_list:
            if not i in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                LoLChampionPatch_adopted: str = bigVersion
                LoLChampion_recapture: int = 1
                logPrint("对局%d英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(matchId, i, LoLChampion_recapture, LoLChampionPatch_adopted, i, matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        LoLChampion: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                        LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                        LoLChampion_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if LoLChampion_recapture < 3:
                            LoLChampion_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                        LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                        current_versions["LoLChampion"] = LoLChampionPatch_adopted
                        unmapped_keys["LoLChampion"].clear()
                        break
                break
        ##召唤师技能（Summoner spells）
        spellIds_match_list: list[int] = sorted(set(map(lambda x: x["spell1Id"], LoLGame_summary["participants"])) | set(map(lambda x: x["spell2Id"], LoLGame_summary["participants"])))
        for i in spellIds_match_list:
            if not i in spells and current_versions["spell"] != bigVersion and i != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                spellPatch_adopted: str = bigVersion
                spell_recapture: int = 1
                logPrint("对局%d召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d capture failed! Changing to spells of Patch %s ... Times tried: %d." %(matchId, i, spell_recapture, spellPatch_adopted, i, matchId, spellPatch_adopted, spell_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        spell: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        spellPatch_deserted: str = spellPatch_adopted
                        spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                        spell_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if spell_recapture < 3:
                            spell_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                        spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                        current_versions["spell"] = spellPatch_adopted
                        unmapped_keys["spell"].clear()
                        break
                break
        ##英雄联盟装备（LoL items）
        #接下来查询具体的对局概要，使用的可能并不是历史记录中记载的对局序号形成的列表。考虑实际使用需求，这里对于装备的合适版本信息采取的思路是默认从最新版本开始获取，如果有装备不存在于最新版本的装备信息，则获取游戏概要中存储的版本对应的装备信息。该思路仍然有问题，详见后续关于美测服的装备获取的注释（The next step is to capture the summary of each specific match, which may not originate from the matchIDs recorded in the match history. Considering the practical use, here the stream of thought for an appropriate version for items is to get items' information from the latest patch, and if some item doesn't exist in the items information of the latest patch, then get the items of the version corresponding to the game according to gameVersion recorded in the match summary. There's a flaw of this idea. Please refer to the annotation regarding PBE data crawling for further solution）
        LoLItemIds_match_list: list[int] = sorted(set(item for s in [set(map(lambda x: x["stats"].get(key, 0), LoLGame_summary["participants"])) for key in ["item0", "item1", "item2", "item3", "item4", "item5", "item6", "roleBoundItem"]] for item in s)) #该表达式等价于以下表达式（This expression is equivalent to the following expression）：`LoLItemIds_match_list = sorted(set(map(lambda x: x["stats"]["item0"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item1"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item2"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item3"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item4"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item5"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item6"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["roleBoundItem"], LoLGame_summary["participants"])))`
        for i in LoLItemIds_match_list:
            if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                LoLItemPatch_adopted: str = bigVersion
                LoLItem_recapture: int = 1
                logPrint("对局%d英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(matchId, i, LoLItem_recapture, LoLItemPatch_adopted, i, matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        LoLItem: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        LoLItemPatch_deserted: str = LoLItemPatch_adopted
                        LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                        LoLItem_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if LoLItem_recapture < 3:
                            LoLItem_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                        LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                        current_versions["LoLItem"] = LoLItemPatch_adopted
                        unmapped_keys["LoLItem"].clear()
                        break
                break
        ##符文（Perks）
        perkIds_match_list: list[int] = sorted(set(perk for s in [set(map(lambda x: x["stats"]["perk" + str(i)], LoLGame_summary["participants"])) for i in range(6)] for perk in s))
        for i in perkIds_match_list:
            if not i in perks and current_versions["perk"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                perkPatch_adopted: str = bigVersion
                perk_recapture: int = 1
                logPrint("对局%d基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d capture failed! Changing to perks of Patch %s ... Times tried: %d." %(matchId, i, perk_recapture, perkPatch_adopted, i, matchId, perkPatch_adopted, perk_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        perk: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        perkPatch_deserted: str = perkPatch_adopted
                        perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                        perk_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if perk_recapture < 3:
                            perk_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                        perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                        current_versions["perk"] = perkPatch_adopted
                        unmapped_keys["perk"].clear()
                        break
                break
        ##符文系（Perkstyles）
        perkstyleIds_match_list: list[int] = sorted(list(set(map(lambda x: x["stats"]["perkPrimaryStyle"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["perkSubStyle"], LoLGame_summary["participants"]))))
        for i in perkstyleIds_match_list:
            if not i in perkstyles and current_versions["perkstyle"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                perkstylePatch_adopted: str = bigVersion
                perkstyle_recapture = 1
                logPrint("对局%d符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(matchId, i, perkstyle_recapture, perkstylePatch_adopted, i, matchId, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                        perkstyle: dict[str, Any] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        perkstylePatch_deserted: str = perkstylePatch_adopted
                        perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                        perkstyle_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if perkstyle_recapture < 3:
                            perkstyle_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                        perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                        current_versions["perkstyle"] = perkstylePatch_adopted
                        unmapped_keys["perkstyle"].clear()
                        break
                break
        ##斗魂竞技场强化符文（Cherry augments）
        CherryAugmentIds_match_list: list[int] = sorted(set(augment for s in [set(map(lambda x: x["stats"]["playerAugment" + str(i)], LoLGame_summary["participants"])) for i in range(1, 7)] for augment in s)) #该表达式等价于以下表达式（This expression is equivalent to the following expression）：CherryAugmentIds_match_list = sorted(list(set(map(lambda x: x["stats"]["playerAugment1"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment2"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment3"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment4"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment5"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment6"], LoLGame_summary["participants"]))))
        for i in CherryAugmentIds_match_list:
            if not i in CherryAugments and current_versions["CherryAugment"] != bigVersion and i != 0:
                CherryAugmentPatch_adopted: str = bigVersion
                CherryAugment_recapture: int = 1
                logPrint("对局%d强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(matchId, i, CherryAugment_recapture, CherryAugmentPatch_adopted, i, matchId, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        CherryAugment: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                        CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                        CherryAugment_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if CherryAugment_recapture < 3:
                            CherryAugment_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                        CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                        current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                        unmapped_keys["CherryAugment"].clear()
                        break
                break
    #下面开始整理数据（Organize data）
    LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
    LoLGame_summary_data: dict[str, list[Any]] = {key: [] for key in LoLGame_summary_header} #这里将对局的数据放在一个字典中，键为统计量，值为由所有玩家的数据组成的列表（Here the whole match data are stored in a dictionary whose keys are statistics and values are lists composed of corresponding data of all players）
    for i in range(len(LoLGame_summary["participantIdentities"])): #对于对局概要而言，每个玩家对应一条记录（For match summary, each record represents a player）
        participant_puuid: str = LoLGame_summary["participantIdentities"][i]["player"]["puuid"]
        generate_LoLGameSummary_records(LoLGame_summary_data, LoLGame_summary, i, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = gameIndex, current_puuid = puuidList, bans = bans, legacy_banData_appended = legacy_banData_appended, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
        if sortStats and not (not save_bot and participant_puuid == BOT_UUID or not save_self and participant_puuid in puuidList or not save_other and not participant_puuid in puuidList): #这个if语句块是适配查战绩脚本而做的修改（This if-block is a modification made to adapt to Customized Program 05）
            for j in range(len(LoLGame_summary_header_keys)):
                key: str = LoLGame_summary_header_keys[j]
                LoLGame_stat_data[key].append(LoLGame_summary_data[key][-1]) #直接添加最近一次追加的数据，以简化代码（Directly append the recently appended data to simplify the code）
    #数据框列序整理（Dataframe column ordering）
    LoLGame_summary_statistics_output_order: list[int] = [42, 214, 16, 231, 26, 20, 27, 25, 24, 22, 19, 31, 35, 36, 226, 227, 229, 230, 46, 38, 39, 160, 161, 162, 163, 164, 165, 166, 215, 196, 208, 197, 209, 198, 210, 199, 211, 200, 212, 201, 213, 74, 51, 43, 218, 219, 222, 223, 47, 144, 145, 76, 73, 77, 55, 54, 59, 58, 57, 56, 52, 148, 133, 86, 153, 138, 146, 140, 114, 80, 150, 139, 113, 79, 149, 75, 49, 48, 142, 147, 141, 115, 81, 151, 50, 154, 157, 156, 135, 155, 63, 220, 64, 221, 143, 82, 84, 83, 152, 65, 78, 192, 194, 180, 174, 181, 175, 182, 176, 183, 177, 184, 178, 185, 179, 44, 53, 137, 45, 60, 61, 62, 158, 224, 136, 243, 237, 232, 290, 233, 277, 245, 242, 246, 238, 280, 269, 255, 285, 271, 278, 273, 257, 249, 282, 272, 256, 248, 281, 244, 235, 234, 275, 279, 274, 258, 250, 283, 236, 286, 289, 288, 270, 287, 239, 240, 276, 251, 253, 252, 291, 284, 241, 247, 293, 304, 298, 292, 351, 352, 354, 294, 338, 306, 303, 307, 299, 341, 330, 316, 346, 332, 339, 334, 318, 310, 343, 333, 317, 309, 342, 305, 296, 295, 336, 340, 335, 319, 311, 344, 297, 347, 350, 349, 331, 348, 300, 301, 355, 337, 312, 313, 314, 353, 345, 302, 308]
    LoLGame_summary_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: LoLGame_summary_data[LoLGame_summary_header_keys[i]] for i in LoLGame_summary_statistics_output_order}
    LoLGame_summary_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_summary_data_organized)
    optimize_bool_display(LoLGame_summary_df)
    LoLGame_summary_df = pandas.concat([pandas.DataFrame([LoLGame_summary_header])[LoLGame_summary_df.columns], LoLGame_summary_df], ignore_index = True)
    return (LoLGame_summary_df, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments)

def sort_LoLGame_summary_sgp(LoLGame_summary: dict[str, Any], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], gameIndex: int = 1, current_puuid: str | list[str] = "", useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, session: Optional[requests.Session] = None, sortStats: bool = False, LoLGame_stat_data: Optional[dict[str, list[Any]]] = None, save_self: bool = True, save_other: bool = True, save_bot: bool = False, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    '''
    将英雄联盟对局概要中的玩家信息整理成一张表格。<br>Organize player information in a match summary into a dataframe.
    
    :param LoLGame_summary: 英雄联盟对局概要。通过以下SGP接口得到：<br>LoL match summary, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/lol/{match_id}/SUMMARY`
    :type LoLGame_summary: dict[str, Any]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param current_puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type current_puuid: str | list[str]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[int]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param sortStats: 是否在整理对局概要数据的同时整理玩家战绩数据。默认为假。<br>Whether to organize player stats data while organizing the match summary data. False by default.
    :type sortStats: bool
    :param LoLGame_stat_data: 玩家战绩数据。相比对局概要数据，添加了对局元数据信息。<br>Player stat data, which additionally organize the match metadata compared with match summary.
    :type LoLGame_stat_data: dict[str, list[Any]]
    :param save_self: 在汇总玩家战绩时，是否保存主召唤师的数据。默认为真。<br>Whether to save the data of the main summoner when the program is summarizing player stats. True by default.
    :type save_self: bool
    :param save_other: 在汇总玩家战绩时，是否保存主召唤师以外的玩家数据。默认为真。<br>Whether to save the data of players except the main summoner when the program is summarizing player stats. True by default.
    :type save_other: bool
    :param save_bot: 在汇总玩家战绩时，是否保存电脑玩家的数据。默认为假。<br>Whether to save the data of bot players when the program is summarizing player stats. False by default.
    :type save_bot: bool
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 英雄联盟对局概要数据框，以及游戏队列、召唤师图标、英雄、召唤师技能、英雄联盟装备、符文、符文系和斗魂竞技场强化符文等数据资源的缓存。<br>LoL match summary dataframe, and data resources like queues, summoner icons, champions, summoner spells, LoL items, perks, perkstyles and Arena augments.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if session == None:
        session = requests.Session()
    if LoLGame_stat_data == None:
        LoLGame_stat_data = {key: [] for key in LoLGame_summary_sgp_header.keys()}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    LoLGame_summary_header: dict[str, str] = LoLGame_summary_sgp_header #通过在函数内指定同名变量，使得其不再使用全局变量，并减少以下代码的修改（By specifying the variable with the same name, this variable is no longer the global one, and meanwhile the following code doesn't need changing much）
    LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
    LoLGame_summary_data: dict[str, list[Any]] = {key: [] for key in LoLGame_summary_header} #这里将对局的数据放在一个字典中，键为统计量，值为由所有玩家的数据组成的列表（Here the whole match data are stored in a dictionary whose keys are statistics and values are lists composed of corresponding data of all players）
    if LoLGame_summary.get("json"):
        LoLGame_summary_json: dict[str, Any] = LoLGame_summary["json"]
        version: str = LoLGame_summary_json["gameVersion"]
        bigVersion: str = ".".join(version.split(".")[:2])
        matchId: int = LoLGame_summary_json["gameId"]
        #整理对局禁用信息（Sort out the team ban information）
        if len(LoLGame_summary_json["teams"]) == 0:
            bans: list[dict[str, int]] = []
        elif len(LoLGame_summary_json["teams"]) == 1:
            bans = LoLGame_summary_json["teams"][0]["bans"]
        else:
            bans = LoLGame_summary_json["teams"][0]["bans"] + LoLGame_summary_json["teams"][1]["bans"]
            if len(LoLGame_summary_json["teams"]) > 2:
                logPrint("警告：对局%d中含有%d支阵营。\nWarning: There're %d teams in Match %d." %(matchId, len(LoLGame_summary_json["teams"]), len(LoLGame_summary_json["teams"]), matchId), verbose = verbose)
        if LoLGame_summary_json["gameMode"] == "CHERRY" and Patch("14.8") < Patch(version):
            bans_tmp: list[dict[str, int]] = bans[:]
            bans = []
            emptyBan: dict[str, int] = {"championId": -1, "pickTurn": 0} #定义一个初始化禁用字典，用于后续数据框填充空值（Define an initialized banning dictionary so that empty values are appended to the dataframe at certain times subsequently）
            playerSubteam: dict[int, list[int]] = {} #存储不同子阵营的玩家，键是子阵营序号，值是该子阵营中的玩家的API序号列表（Stores different subteams' players. Keys are playerSubteamIds, and values are index lists from API for players in the subteams）
            for i in range(len(LoLGame_summary_json["participants"])):
                bans.append(emptyBan.copy())
                playerSubteamId: int = LoLGame_summary_json["participants"][i]["playerSubteamId"]
                if not playerSubteamId in playerSubteam:
                    playerSubteam[playerSubteamId] = []
                playerSubteam[playerSubteamId].append(i)
            if Patch("14.12") < Patch(version):
                participantBanIds: list[int] = []
                for i in sorted(playerSubteam.keys()):
                    participantBanIds += playerSubteam[i] #这里默认采用某个子阵营在API中记录的第一名玩家作为该子阵营的先选者。这可能与实际选用顺序有出入（Here the first player of a subteam recorded in API is considered as the player that picks a champion first. This player may not be the real first player.）
            else:
                participantBanIds = [playerSubteam[i][0] for i in sorted(playerSubteam.keys())] #这里默认采用某个子阵营在API中记录的第一名玩家作为禁用英雄的玩家。这可能与实际禁用英雄的玩家有出入（Here the first player of a subteam recorded in API is considered as the player that banned some champion. This player may not be the real player that banned it）
            for i in range(len(participantBanIds)):
                bans[participantBanIds[i]] = bans_tmp[i]
        legacy_banData_appended: dict[int, bool] = {100: False, 200: False} #自定义对局中的征召模式是由每个阵营的1号选手禁用3个英雄，所以当禁用信息添加到一个阵营的第一名玩家后，后续玩家不需要再添加禁用信息。这个字典就是用来判断这一点的（Draft mode in custom matches is performed by the first player of each team banning 3 champions, so if the ban information is added into the first player, the subsequent player in the same team doesn't need to add this information. That's what this dictionary is used for）
        #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
        if useAllVersions:
            ##游戏模式（Game mode）
            queueIds_match_list: list[int] = [LoLGame_summary_json["queueId"]]
            for i in queueIds_match_list:
                if not i in queues and current_versions["queue"] != bigVersion:
                    queuePatch_adopted: str = bigVersion
                    queue_recapture: int = 1
                    logPrint("对局%d游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(matchId, i, queue_recapture, queuePatch_adopted, i, matchId, queuePatch_adopted, queue_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                            queue: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            queuePatch_deserted: str = queuePatch_adopted
                            queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                            queue_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if queue_recapture < 3:
                                queue_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game mode (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                            queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                            current_versions["queue"] = queuePatch_adopted
                            unmapped_keys["queue"].clear()
                            break
                    break
            ##召唤师图标（Summoner icon）
            summonerIconIds_match_list: list[int] = sorted(set(map(lambda x: x["profileIcon"], LoLGame_summary_json["participants"])))
            for i in summonerIconIds_match_list:
                if not i in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                    summonerIconPatch_adopted: str = bigVersion
                    summonerIcon_recapture: int = 1
                    logPrint("对局%d召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(matchId, i, summonerIcon_recapture, summonerIconPatch_adopted, i, matchId, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            summonerIcon: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            summonerIconPatch_deserted: str = summonerIconPatch_adopted
                            summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                            summonerIcon_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if summonerIcon_recapture < 3:
                                summonerIcon_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                            summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                            current_versions["summonerIcon"] = summonerIconPatch_adopted
                            unmapped_keys["summonerIcon"].clear()
                            break
                    break
            ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
            LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: x["championId"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["championId"], bans)))
            for i in LoLChampionIds_match_list:
                if not i in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                    LoLChampionPatch_adopted: str = bigVersion
                    LoLChampion_recapture: int = 1
                    logPrint("对局%d英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(matchId, i, LoLChampion_recapture, LoLChampionPatch_adopted, i, matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            LoLChampion: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                            LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                            LoLChampion_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if LoLChampion_recapture < 3:
                                LoLChampion_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                            LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                            current_versions["LoLChampion"] = LoLChampionPatch_adopted
                            unmapped_keys["LoLChampion"].clear()
                            break
                    break
            ##召唤师技能（Summoner spells）
            spellIds_match_list: list[int] = sorted(set(map(lambda x: x["spell1Id"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["spell2Id"], LoLGame_summary_json["participants"])))
            for i in spellIds_match_list:
                if not i in spells and current_versions["spell"] != bigVersion and i != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                    spellPatch_adopted: str = bigVersion
                    spell_recapture: int = 1
                    logPrint("对局%d召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d capture failed! Changing to spells of Patch %s ... Times tried: %d." %(matchId, i, spell_recapture, spellPatch_adopted, i, matchId, spellPatch_adopted, spell_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            spell: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            spellPatch_deserted: str = spellPatch_adopted
                            spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                            spell_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if spell_recapture < 3:
                                spell_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                            spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                            current_versions["spell"] = spellPatch_adopted
                            unmapped_keys["spell"].clear()
                            break
                    break
            ##英雄联盟装备（LoL items）
            #接下来查询具体的对局概要，使用的可能并不是历史记录中记载的对局序号形成的列表。考虑实际使用需求，这里对于装备的合适版本信息采取的思路是默认从最新版本开始获取，如果有装备不存在于最新版本的装备信息，则获取游戏概要中存储的版本对应的装备信息。该思路仍然有问题，详见后续关于美测服的装备获取的注释（The next step is to capture the summary of each specific match, which may not originate from the matchIDs recorded in the match history. Considering the practical use, here the stream of thought for an appropriate version for items is to get items' information from the latest patch, and if some item doesn't exist in the items information of the latest patch, then get the items of the version corresponding to the game according to gameVersion recorded in the match summary. There's a flaw of this idea. Please refer to the annotation regarding PBE data crawling for further solution）
            LoLItemIds_match_list: list[int] = sorted(set(item for s in [set(map(lambda x: x.get(key, 0), LoLGame_summary_json["participants"])) for key in ["item0", "item1", "item2", "item3", "item4", "item5", "item6", "roleBoundItem"]] for item in s)) #该表达式等价于以下表达式（This expression is equivalent to the following expression）：`LoLItemIds_match_list = sorted(set(map(lambda x: x["item0"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["item1"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["item2"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["item3"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["item4"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["item5"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["item6"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["roleBoundItem"], LoLGame_summary_json["participants"])))`
            for i in LoLItemIds_match_list:
                if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                    LoLItemPatch_adopted: str = bigVersion
                    LoLItem_recapture: int = 1
                    logPrint("对局%d英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(matchId, i, LoLItem_recapture, LoLItemPatch_adopted, i, matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            LoLItem: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            LoLItemPatch_deserted: str = LoLItemPatch_adopted
                            LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                            LoLItem_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if LoLItem_recapture < 3:
                                LoLItem_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                            LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                            current_versions["LoLItem"] = LoLItemPatch_adopted
                            unmapped_keys["LoLItem"].clear()
                            break
                    break
            ##符文（Perks）
            perkIds_match_list: list[int] = []
            for participant in LoLGame_summary_json["participants"]:
                if "perks" in participant:
                    if "statPerks" in participant["perks"]:
                        perkIds_match_list += list(participant["perks"]["statPerks"].values())
                    if "styles" in participant["perks"]:
                        for style in participant["perks"]["styles"]:
                            if "selections" in style:
                                perkIds_match_list += list(map(lambda x: x["perk"], style["selections"]))
            perkIds_match_list = sorted(set(perkIds_match_list))
            for i in perkIds_match_list:
                if not i in perks and current_versions["perk"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                    perkPatch_adopted: str = bigVersion
                    perk_recapture: int = 1
                    logPrint("对局%d基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d capture failed! Changing to perks of Patch %s ... Times tried: %d." %(matchId, i, perk_recapture, perkPatch_adopted, i, matchId, perkPatch_adopted, perk_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            perk: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            perkPatch_deserted: str = perkPatch_adopted
                            perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                            perk_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if perk_recapture < 3:
                                perk_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                            perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                            current_versions["perk"] = perkPatch_adopted
                            unmapped_keys["perk"].clear()
                            break
                    break
            ##符文系（Perkstyles）
            perkstyleIds_match_list: list[int] = []
            for participant in LoLGame_summary_json["participants"]:
                if "perks" in participant and "styles" in participant["perks"]:
                    perkstyleIds_match_list += list(map(lambda x: x["style"], participant["perks"]["styles"]))
            perkstyleIds_match_list = sorted(set(perkstyleIds_match_list))
            for i in perkstyleIds_match_list:
                if not i in perkstyles and current_versions["perkstyle"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                    perkstylePatch_adopted: str = bigVersion
                    perkstyle_recapture = 1
                    logPrint("对局%d符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(matchId, i, perkstyle_recapture, perkstylePatch_adopted, i, matchId, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                            perkstyle: dict[str, Any] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            perkstylePatch_deserted: str = perkstylePatch_adopted
                            perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                            perkstyle_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if perkstyle_recapture < 3:
                                perkstyle_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                            perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                            current_versions["perkstyle"] = perkstylePatch_adopted
                            unmapped_keys["perkstyle"].clear()
                            break
                    break
            ##斗魂竞技场强化符文（Cherry augments）
            CherryAugmentIds_match_set: set[int] = set()
            for participant in LoLGame_summary_json["participants"]:
                for i in range(1, 7):
                    key: str = f"playerAugment{i}"
                    if key in participant:
                        CherryAugmentIds_match_set.add(participant[key])
            CherryAugmentIds_match_list: list[int] = sorted(CherryAugmentIds_match_set)
            for i in CherryAugmentIds_match_list:
                if not i in CherryAugments and current_versions["CherryAugment"] != bigVersion and i != 0:
                    CherryAugmentPatch_adopted: str = bigVersion
                    CherryAugment_recapture: int = 1
                    logPrint("对局%d强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(matchId, i, CherryAugment_recapture, CherryAugmentPatch_adopted, i, matchId, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            CherryAugment: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                            CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                            CherryAugment_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if CherryAugment_recapture < 3:
                                CherryAugment_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                            CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                            current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                            unmapped_keys["CherryAugment"].clear()
                            break
                    break
        #下面开始整理数据（Organize data）
        for i in range(len(LoLGame_summary_json["participants"])): #对于对局概要而言，每个玩家对应一条记录（For match summary, each record represents a player）
            participant_puuid: str = LoLGame_summary_json["participants"][i]["puuid"]
            generate_LoLGameSummary_records_sgp(LoLGame_summary_data, LoLGame_summary, i, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = gameIndex, current_puuid = puuidList, bans = bans, legacy_banData_appended = legacy_banData_appended, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
            if sortStats and not (not save_bot and participant_puuid == BOT_UUID or not save_self and participant_puuid in puuidList or not save_other and not participant_puuid in puuidList): #这个if语句块是适配查战绩脚本而做的修改（This if-block is a modification made to adapt to Customized Program 05）
                for j in range(len(LoLGame_summary_header_keys)):
                    key: str = LoLGame_summary_header_keys[j]
                    LoLGame_stat_data[key].append(LoLGame_summary_data[key][-1]) #直接添加最近一次追加的数据，以简化代码（Directly append the recently appended data to simplify the code）
    #数据框列序整理（Dataframe column ordering）
    LoLGame_summary_statistics_output_order: list[int] = [227, 218, 112, 628, 148, 131, 132, 146, 128, 147, 68, 21, 184, 54, 625, 626, 96, 133, 125, 82, 152, 135, 52, 51, 55, 223, 224, 186, 187, 188, 189, 190, 191, 192, 221, 200, 212, 201, 213, 202, 214, 203, 215, 204, 216, 205, 217, 95, 64, 45, 230, 231, 234, 235, 98, 94, 99, 49, 72, 71, 74, 73, 66, 167, 129, 113, 174, 153, 164, 157, 115, 102, 169, 156, 114, 101, 168, 97, 61, 60, 58, 59, 161, 162, 166, 158, 159, 116, 103, 170, 62, 176, 179, 178, 136, 177, 65, 79, 232, 80, 233, 93, 57, 163, 105, 155, 160, 171, 172, 83, 84, 106, 108, 173, 85, 107, 67, 47, 109, 110, 100, 48, 56, 78, 130, 127, 111, 43, 44, 104, 69, 70, 175, 63, 46, 81, 154, 165, 137, 139, 141, 142, 228, 144, 145, 602, 616, 608, 604, 609, 605, 610, 606, 611, 607, 620, 618, 621, 619, 598, 596, 597, 50, 149, 150, 75, 76, 77, 182, 181, 180, 236, 117, 143, 672, 658, 643, 728, 674, 671, 675, 647, 660, 715, 692, 687, 721, 701, 712, 705, 689, 678, 717, 704, 688, 677, 716, 673, 655, 654, 652, 653, 709, 710, 714, 706, 707, 690, 679, 718, 656, 723, 726, 725, 694, 724, 659, 665, 666, 670, 651, 711, 681, 703, 708, 729, 719, 720, 668, 669, 682, 683, 661, 645, 684, 685, 676, 646, 650, 664, 693, 691, 686, 641, 642, 680, 662, 663, 722, 657, 644, 667, 702, 713, 695, 696, 697, 698, 727, 699, 700, 802, 750, 749, 773, 759, 744, 830, 831, 833, 775, 772, 776, 748, 761, 817, 793, 788, 823, 803, 814, 807, 790, 779, 819, 806, 789, 778, 818, 774, 756, 755, 753, 754, 811, 812, 816, 808, 809, 791, 780, 820, 757, 825, 828, 827, 795, 826, 760, 766, 767, 834, 771, 752, 813, 782, 810, 805, 832, 821, 822, 769, 770, 762, 746, 785, 786, 783, 784, 777, 747, 751, 765, 794, 792, 787, 742, 743, 781, 763, 764, 824, 758, 745, 768, 804, 815, 796, 797, 798, 799, 829, 800, 801, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 381, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 382, 283, 284, 285, 383, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 384, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 385, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 237]
    LoLGame_summary_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: LoLGame_summary_data[LoLGame_summary_header_keys[i]] for i in LoLGame_summary_statistics_output_order}
    LoLGame_summary_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_summary_data_organized)
    optimize_bool_display(LoLGame_summary_df)
    LoLGame_summary_df = pandas.concat([pandas.DataFrame([LoLGame_summary_header])[LoLGame_summary_df.columns], LoLGame_summary_df], ignore_index = True)
    return (LoLGame_summary_df, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments)

async def sort_LoLGame_stats(connection: Connection, LoLMatchIDs: list[int], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], puuid: str | list[str] = "", excluded_reserve: bool = False, save_self: bool = True, save_other: bool = False, save_bot: bool = False, useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, LoLGame_summary_cache: Optional[dict[int, dict[str, Any]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame:
    '''
    将多场英雄联盟对局中的玩家数据汇总形成一个表格，同时包含对局元数据和玩家战绩。<br>Organize player stats in multiple LoL matches into a dataframe, which contains match metadata and player stats.
    
    和`sort_LoLGame_summary`函数不同的是，该函数从对局序号得到玩家战绩数据框，而`sort_LoLGame_summary`函数是伴随着对局概要数据框的形成而形成的。<br>The difference of this function from `sort_LoLGame_summary` is that this function returns the player stats dataframe based on matchIds, while this dataframe is formed along the formation of match summary dataframe in `sort_LoLGame_summary`.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param LoLMatchIDs: 英雄联盟对局序号列表。<br>LoL matchId list.
    :type LoLMatchIDs: list[int]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type puuid: str | list[str]
    :param excluded_reserve: 在对局不包含主召唤师时，是否仍然保存该对局。默认为假。<br>Whether to persist on saving the match when the match doesn't contain the main summoner. False by default.
    :type excluded_reserve: bool
    :param save_self: 是否保存主召唤师的数据。默认为真。<br>Whether to save the data of the main summoner. True by default.
    :type save_self: bool
    :param save_other: 是否保存主召唤师以外的玩家数据。默认为假。<br>Whether to save the data of players except the main summoner. False by default.
    :type save_other: bool
    :param save_bot: 是否保存电脑玩家的数据。默认为假。<br>Whether to save the data of bot players. False by default.
    :type save_bot: bool
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param LoLGame_summary_cache: 英雄联盟对局概要缓存。键为对局序号，值为对局概要。<br>LoL match summary cache. Each key is a matchId, and each value is a match summary.
    :type LoLGame_summary_cache: dict[int, dict[str, Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 玩家战绩数据框。<br>Player stat dataframe.
    :rtype: pandas.DataFrame
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if LoLGame_summary_cache == None or not (isinstance(LoLGame_summary_cache, dict) and all(map(lambda x: isinstance(x, int), LoLGame_summary_cache.keys())) and all(map(lambda x: isinstance(x, dict) and all(map(lambda y: y in {"endOfGameResult", "gameCreation", "gameCreationDate", "gameDuration", "gameId", "gameMode", "gameModeMutators", "gameType", "gameVersion", "mapId", "participantIdentities", "participants", "platformId", "queueId", "seasonId", "teams"}, x.keys())), LoLGame_summary_cache.values()))):
        LoLGame_summary_cache = {}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    error_LoLMatchIDs: list[int] = [] #记录实际存在但未如期获取的对局序号（Records the LoL matches that really exist but fail to be fetched）
    matches_to_remove: list[int] = [] #记录获取成功但不包含主玩家的对局序号（Records the matches that are fetched successfully but don't contain the main player）
    #开始获取各对局内的玩家信息。数据结构参考/lol-match-history/v1/recently-played-summoners（Begin to capture the players' information in each match. The data structure refers to "/lol-match-history/v1/recently-played-summoners"）
    LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
    LoLGame_stat_data: dict[str, list[Any]] = {key: [] for key in LoLGame_summary_header_keys}
    for matchId in LoLMatchIDs:
        if matchId in LoLGame_summary_cache:
            LoLGame_summary: dict[str, Any] = LoLGame_summary_cache[matchId]
            status: int = 200
        else:
            status, LoLGame_summary = await get_LoLGame_summary(connection, matchId, log = log)
            if status == 200:
                LoLGame_summary_cache[matchId] = LoLGame_summary
        
        if "errorCode" in LoLGame_summary:
            logPrint(LoLGame_summary, verbose = verbose)
            error_LoLMatchIDs.append(matchId)
        else:
            version: str = LoLGame_summary["gameVersion"]
            bigVersion: str = ".".join(version.split(".")[:2])
            #整理对局禁用信息（Sort out the team ban information）
            if len(LoLGame_summary["teams"]) == 0:
                bans: list[dict[str, int]] = []
            elif len(LoLGame_summary["teams"]) == 1:
                bans = LoLGame_summary["teams"][0]["bans"]
            else:
                bans = LoLGame_summary["teams"][0]["bans"] + LoLGame_summary["teams"][1]["bans"]
                if len(LoLGame_summary["teams"]) > 2:
                    logPrint("警告：对局%d中含有%d支阵营。\nWarning: There're %d teams in Match %d." %(matchId, len(LoLGame_summary["teams"]), len(LoLGame_summary["teams"]), matchId), verbose = verbose)
            if LoLGame_summary["gameMode"] == "CHERRY" and Patch("14.8") < Patch(version):
                bans_tmp: list[dict[str, int]] = bans[:]
                bans = []
                emptyBan: dict[str, int] = {"championId": -1, "pickTurn": 0} #定义一个初始化禁用字典，用于后续数据框填充空值（Define an initialized banning dictionary so that empty values are appended to the dataframe at certain times subsequently）
                playerSubteam: dict[int, list[int]] = {} #存储不同子阵营的玩家，键是子阵营序号，值是该子阵营中的玩家的API序号列表（Stores different subteams' players. Keys are playerSubteamIds, and values are index lists from API for players in the subteams）
                for i in range(len(LoLGame_summary["participants"])):
                    bans.append(emptyBan.copy())
                    playerSubteamId: int = LoLGame_summary["participants"][i]["stats"]["playerSubteamId"]
                    if not playerSubteamId in playerSubteam:
                        playerSubteam[playerSubteamId] = []
                    playerSubteam[playerSubteamId].append(i)
                if Patch("14.12") < Patch(version):
                    participantBanIds: list[int] = []
                    for i in sorted(playerSubteam.keys()):
                        participantBanIds += playerSubteam[i] #这里默认采用某个子阵营在API中记录的第一名玩家作为该子阵营的先选者。这可能与实际选用顺序有出入（Here the first player of a subteam recorded in API is considered as the player that picks a champion first. This player may not be the real first player.）
                else:
                    participantBanIds = [playerSubteam[i][0] for i in sorted(playerSubteam.keys())] #这里默认采用某个子阵营在API中记录的第一名玩家作为禁用英雄的玩家。这可能与实际禁用英雄的玩家有出入（Here the first player of a subteam recorded in API is considered as the player that banned some champion. This player may not be the real player that banned it）
                for i in range(len(participantBanIds)):
                    bans[participantBanIds[i]] = bans_tmp[i]
            legacy_banData_appended: dict[int, bool] = {100: False, 200: False} #自定义对局中的征召模式是由每个阵营的1号选手禁用3个英雄，所以当禁用信息添加到一个阵营的第一名玩家后，后续玩家不需要再添加禁用信息。这个字典就是用来判断这一点的（Draft mode in custom matches is performed by the first player of each team banning 3 champions, so if the ban information is added into the first player, the subsequent player in the same team doesn't need to add this information. That's what this dictionary is used for）
            if excluded_reserve or len(set(puuidList) & set(map(lambda x: x["player"]["puuid"], LoLGame_summary["participantIdentities"]))) != 0: #之所以使用玩家通用唯一识别码，而不是用召唤师名称来识别对局是否包含主玩家，是因为该玩家可能使用过改名卡。这里也没有选择帐户序号，这是因为保存在对局中的各玩家的帐户序号竟然是0！（The reason why the puuid instead of the displayName or summonerName is used to identify whether the matches contain the main player is that the player may have used name changing card. AccountId isn't chosen here, because all players' accountIds saved in the match fetched from 127 API is 0, to my surprise!）
                #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                if useAllVersions:
                    ##游戏模式（Game mode）
                    queueIds_match_list: list[int] = [LoLGame_summary["queueId"]]
                    for i in queueIds_match_list:
                        if not i in queues and current_versions["queue"] != bigVersion:
                            queuePatch_adopted = bigVersion
                            queue_recapture = 1
                            logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, queue_recapture, queuePatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, queuePatch_adopted, queue_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    queue: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    queuePatch_deserted: str = queuePatch_adopted
                                    queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                    queue_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if queue_recapture < 3:
                                        queue_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game mode (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                    queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                    current_versions["queue"] = queuePatch_adopted
                                    unmapped_keys["queue"].clear()
                                    break
                            break
                    ##召唤师图标（Summoner icon）
                    summonerIconIds_match_list: list[int] = sorted(set(map(lambda x: x["player"]["profileIcon"], LoLGame_summary["participantIdentities"])))
                    for i in summonerIconIds_match_list:
                        if not i in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                            summonerIconPatch_adopted: str = bigVersion
                            summonerIcon_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, summonerIcon_recapture, summonerIconPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    summonerIcon: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    summonerIconPatch_deserted: str = summonerIconPatch_adopted
                                    summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                                    summonerIcon_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if summonerIcon_recapture < 3:
                                        summonerIcon_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                                    summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                                    current_versions["summonerIcon"] = summonerIconPatch_adopted
                                    unmapped_keys["summonerIcon"].clear()
                                    break
                            break
                    ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
                    LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: x["championId"], LoLGame_summary["participants"])) | set(map(lambda x: x["championId"], bans)))
                    for i in LoLChampionIds_match_list:
                        if not i in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                            LoLChampionPatch_adopted: str = bigVersion
                            LoLChampion_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, LoLChampion_recapture, LoLChampionPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    LoLChampion: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                                    LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                                    LoLChampion_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if LoLChampion_recapture < 3:
                                        LoLChampion_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                                    LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                                    current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                    unmapped_keys["LoLChampion"].clear()
                                    break
                            break
                    ##召唤师技能（Summoner spells）
                    spellIds_match_list: list[int] = sorted(set(map(lambda x: x["spell1Id"], LoLGame_summary["participants"])) | set(map(lambda x: x["spell2Id"], LoLGame_summary["participants"])))
                    for i in spellIds_match_list:
                        if not i in spells and current_versions["spell"] != bigVersion and i != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                            spellPatch_adopted: str = bigVersion
                            spell_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, spell_recapture, spellPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, spellPatch_adopted, spell_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    spell: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    spellPatch_deserted: str = spellPatch_adopted
                                    spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                                    spell_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if spell_recapture < 3:
                                        spell_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                                    spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                                    current_versions["spell"] = spellPatch_adopted
                                    unmapped_keys["spell"].clear()
                                    break
                            break
                    ##英雄联盟装备（LoL items）
                    LoLItemIds_match_list: list[int] = sorted(set(item for s in [set(map(lambda x: x["stats"].get(key, 0), LoLGame_summary["participants"])) for key in ["item0", "item1", "item2", "item3", "item4", "item5", "item6", "roleBoundItem"]] for item in s)) #该表达式等价于以下表达式（This expression is equivalent to the following expression）：`LoLItemIds_match_list = sorted(set(map(lambda x: x["stats"]["item0"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item1"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item2"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item3"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item4"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item5"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["item6"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["roleBoundItem"], LoLGame_summary["participants"])))`
                    for i in LoLItemIds_match_list:
                        if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                            LoLItemPatch_adopted: str = bigVersion
                            LoLItem_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, LoLItem_recapture, LoLItemPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    LoLItem: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    LoLItemPatch_deserted: str = LoLItemPatch_adopted
                                    LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                                    LoLItem_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if LoLItem_recapture < 3:
                                        LoLItem_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                                    LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                                    current_versions["LoLItem"] = LoLItemPatch_adopted
                                    unmapped_keys["LoLItem"].clear()
                                    break
                            break
                    ##符文（Perks）
                    perkIds_match_list: list[int] = sorted(set(perk for s in [set(map(lambda x: x["stats"]["perk" + str(i)], LoLGame_summary["participants"])) for i in range(6)] for perk in s))
                    for i in perkIds_match_list:
                        if not i in perks and current_versions["perk"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                            perkPatch_adopted: str = bigVersion
                            perk_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, perk_recapture, perkPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, perkPatch_adopted, perk_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    perk: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    perkPatch_deserted = perkPatch_adopted
                                    perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                                    perk_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if perk_recapture < 3:
                                        perk_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                                    perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                                    current_versions["perk"] = perkPatch_adopted
                                    unmapped_keys["perk"].clear()
                                    break
                            break
                    ##符文系（Perkstyles）
                    perkstyleIds_match_list: list[int] = sorted(list(set(map(lambda x: x["stats"]["perkPrimaryStyle"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["perkSubStyle"], LoLGame_summary["participants"]))))
                    for i in perkstyleIds_match_list:
                        if not i in perkstyles and current_versions["perkstyle"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                            perkstylePatch_adopted: str = bigVersion
                            perkstyle_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, perkstyle_recapture, perkstylePatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    perkstyle: dict[str, Any] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    perkstylePatch_deserted = perkstylePatch_adopted
                                    perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                                    perkstyle_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if perkstyle_recapture < 3:
                                        perkstyle_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                                    perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                                    current_versions["perkstyle"] = perkstylePatch_adopted
                                    unmapped_keys["perkstyle"].clear()
                                    break
                            break
                    ##斗魂竞技场强化符文（Cherry augments）
                    CherryAugmentIds_match_list: list[int] = sorted(set(augment for s in [set(map(lambda x: x["stats"]["playerAugment" + str(i)], LoLGame_summary["participants"])) for i in range(1, 7)] for augment in s)) #该表达式等价于以下表达式（This expression is equivalent to the following expression）：CherryAugmentIds_match_list = sorted(list(set(map(lambda x: x["stats"]["playerAugment1"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment2"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment3"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment4"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment5"], LoLGame_summary["participants"])) | set(map(lambda x: x["stats"]["playerAugment6"], LoLGame_summary["participants"]))))
                    for i in CherryAugmentIds_match_list:
                        if not i in CherryAugments and current_versions["CherryAugment"] != bigVersion and i != 0:
                            CherryAugmentPatch_adopted: str = bigVersion
                            CherryAugment_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, CherryAugment_recapture, CherryAugmentPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    CherryAugment: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                                    CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                                    CherryAugment_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if CherryAugment_recapture < 3:
                                        CherryAugment_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                                    CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                                    current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                    unmapped_keys["CherryAugment"].clear()
                                    break
                            break
                #下面开始整理数据（Organize data）
                for i in range(len(LoLGame_summary["participants"])):
                    participant_puuid: str = LoLGame_summary["participantIdentities"][i]["player"]["puuid"]
                    if not (not save_bot and participant_puuid == BOT_UUID or not save_self and participant_puuid in puuidList or not save_other and not participant_puuid in puuidList):
                        generate_LoLGameSummary_records(LoLGame_stat_data, LoLGame_summary, i, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = LoLMatchIDs.index(matchId) + 1, current_puuid = puuidList, bans = bans, legacy_banData_appended = legacy_banData_appended, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
                if excluded_reserve:
                    logPrint("[%d/%d]对局%d不包含主玩家。已保留该对局。\nMatch %d doesn't contain the main player but is reserved." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, matchId), print_time = True, verbose = verbose)
                else:
                    logPrint("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %s" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), print_time = True, verbose = verbose)
            else:
                matches_to_remove.append(matchId)
                logPrint("[%d/%d]对局%d不包含主玩家。已移除该对局。\nMatch %d doesn't contain the main player and is deprecated." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, matchId), print_time = True, verbose = verbose)
    if len(error_LoLMatchIDs) > 0:
        logPrint("警告：以下%d场对局获取失败。\nWarning: The following %d match(es) fail to be fetched." %(len(error_LoLMatchIDs), len(error_LoLMatchIDs)), verbose = verbose)
        logPrint(error_LoLMatchIDs, verbose = verbose)
    if len(matches_to_remove) > 0:
        logPrint("注意：以下%d场对局因不包含主玩家而被移除。\nAttention: The following %d match(es) are removed because they don't contain the main player." %(len(matches_to_remove), len(matches_to_remove)), verbose = verbose)
        logPrint(matches_to_remove, verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    LoLGame_stat_statistics_output_order: list[int] = [0, 16, 26, 20, 27, 25, 24, 31, 5, 3, 13, 4, 11, 6, 14, 10, 15, 9, 42, 214, 231, 35, 36, 226, 227, 229, 230, 46, 38, 39, 160, 161, 162, 163, 164, 165, 166, 215, 196, 208, 197, 209, 198, 210, 199, 211, 200, 212, 201, 213, 74, 51, 43, 217, 218, 219, 222, 223, 47, 144, 145, 76, 73, 77, 55, 54, 59, 58, 57, 56, 52, 148, 133, 86, 153, 138, 146, 140, 114, 80, 150, 139, 113, 79, 149, 75, 49, 48, 142, 147, 141, 115, 81, 151, 50, 154, 157, 156, 135, 155, 63, 220, 64, 221, 143, 82, 84, 83, 152, 65, 78, 192, 194, 180, 174, 181, 175, 182, 176, 183, 177, 184, 178, 185, 179, 44, 53, 137, 45, 60, 61, 62, 158, 224, 136, 243, 237, 232, 290, 233, 277, 245, 242, 246, 238, 280, 269, 255, 285, 271, 278, 273, 257, 249, 282, 272, 256, 248, 281, 244, 235, 234, 275, 279, 274, 258, 250, 283, 236, 286, 289, 288, 270, 287, 239, 240, 276, 251, 253, 252, 291, 284, 241, 247, 293, 304, 298, 292, 351, 352, 354, 294, 338, 306, 303, 307, 299, 341, 330, 316, 346, 332, 339, 334, 318, 310, 343, 333, 317, 309, 342, 305, 296, 295, 336, 340, 335, 319, 311, 344, 297, 347, 350, 349, 331, 348, 300, 301, 355, 337, 312, 313, 314, 353, 345, 302, 308]
    LoLGame_stat_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: LoLGame_stat_data[LoLGame_summary_header_keys[i]] for i in LoLGame_stat_statistics_output_order}
    LoLGame_stat_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_stat_data_organized)
    logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...", verbose = verbose)
    optimize_bool_display(LoLGame_stat_df)
    logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!", verbose = verbose)
    LoLGame_stat_df = pandas.concat([pandas.DataFrame([LoLGame_summary_header])[LoLGame_stat_df.columns], LoLGame_stat_df], ignore_index = True)
    return LoLGame_stat_df

async def sort_LoLGame_stats_sgp(connection: Connection, sgpSession: SGPSession, LoLMatchIDs: list[int], queues: dict[int, dict[str, Any]], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], spells: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]], CherryAugments: dict[int, dict[str, Any]], puuid: str | list[str] = "", excluded_reserve: bool = False, save_self: bool = True, save_other: bool = False, save_bot: bool = False, useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, LoLGame_summary_cache: Optional[dict[int, dict[str, Any]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame:
    '''
    将多场英雄联盟对局中的玩家数据汇总形成一个表格，同时包含对局元数据和玩家战绩。<br>Organize player stats in multiple LoL matches into a dataframe, which contains match metadata and player stats.
    
    和`sort_LoLGame_summary_sgp`函数不同的是，该函数从对局序号得到玩家战绩数据框，而`sort_LoLGame_summary_sgp`函数是伴随着对局概要数据框的形成而形成的。<br>The difference of this function from `sort_LoLGame_summary_sgp` is that this function returns the player stats dataframe based on matchIds, while this dataframe is formed along the formation of match summary dataframe in `sort_LoLGame_summary_sgp`.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param LoLMatchIDs: 英雄联盟对局序号列表。<br>LoL matchId list.
    :type LoLMatchIDs: list[int]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param summonerIcons: 整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`
    :type summonerIcons: dict[int, dict[str, Any]]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param spells: 整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`
    :type spells: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    :param CherryAugments: 整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`
    :type CherryAugments: dict[int, dict[str, Any]]
    :param puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type puuid: str | list[str]
    :param excluded_reserve: 在对局不包含主召唤师时，是否仍然保存该对局。默认为假。<br>Whether to persist on saving the match when the match doesn't contain the main summoner. False by default.
    :type excluded_reserve: bool
    :param save_self: 是否保存主召唤师的数据。默认为真。<br>Whether to save the data of the main summoner. True by default.
    :type save_self: bool
    :param save_other: 是否保存主召唤师以外的玩家数据。默认为假。<br>Whether to save the data of players except the main summoner. False by default.
    :type save_other: bool
    :param save_bot: 是否保存电脑玩家的数据。默认为假。<br>Whether to save the data of bot players. False by default.
    :type save_bot: bool
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param LoLGame_summary_cache: 英雄联盟对局概要缓存。键为对局序号，值为对局概要。通过以下接口得到：<br>LoL match summary cache. Each key is a matchId, and each value is a match summary. It's obtained by the following endpoint:
    
        - `GET /match-history-query/v1/products/lol/player/{puuid}/SUMMARY?startIndex={startIndex}&count={count}`
    :type LoLGame_summary_cache: dict[int, dict[str, Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 玩家战绩数据框。<br>Player stat dataframe.
    :rtype: pandas.DataFrame
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"queue": "", "summonerIcon": "", "spell": "", "LoLChampion": "", "LoLItem": "", "summonerIcon": "", "perk": "", "perkstyle": "", "CherryAugment": ""}
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "CherryAugment": set()}
    if LoLGame_summary_cache == None or not (isinstance(LoLGame_summary_cache, dict) and all(map(lambda x: isinstance(x, int), LoLGame_summary_cache.keys())) and all(map(lambda x: isinstance(x, dict) and all(map(lambda y: y in {"metadata", "json"}, x.keys())), LoLGame_summary_cache.values()))):
        LoLGame_summary_cache = {}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId: str = current_party["platformId"]
    error_LoLMatchIDs: list[int] = [] #记录实际存在但未如期获取的对局序号（Records the LoL matches that really exist but fail to be fetched）
    matches_to_remove: list[int] = [] #记录获取成功但不包含主玩家的对局序号（Records the matches that are fetched successfully but don't contain the main player）
    #开始获取各对局内的玩家信息。数据结构参考/lol-match-history/v1/recently-played-summoners（Begin to capture the players' information in each match. The data structure refers to "/lol-match-history/v1/recently-played-summoners"）
    LoLGame_summary_header = LoLGame_summary_sgp_header
    LoLGame_summary_header_keys: list[str] = list(LoLGame_summary_header.keys())
    LoLGame_stat_data: dict[str, list[Any]] = {key: [] for key in LoLGame_summary_header_keys}
    for matchId in LoLMatchIDs:
        match_id: str = f"{platformId}_{matchId}"
        if matchId in LoLGame_summary_cache:
            LoLGame_summary: dict[str, Any] = LoLGame_summary_cache[matchId]
            status: int = 200
        else:
            status, LoLGame_summary = await get_game_summary_sgp(connection, sgpSession, match_id, skipTFT = True, log = log)
            if status == 200:
                LoLGame_summary_cache[matchId] = LoLGame_summary
        
        if status == 200 and LoLGame_summary.get("json"):
            LoLGame_summary_json: dict[str, Any] = LoLGame_summary["json"]
            version: str = LoLGame_summary_json["gameVersion"]
            bigVersion: str = ".".join(version.split(".")[:2])
            #整理对局禁用信息（Sort out the team ban information）
            if len(LoLGame_summary_json["teams"]) == 0:
                bans: list[dict[str, int]] = []
            elif len(LoLGame_summary_json["teams"]) == 1:
                bans = LoLGame_summary_json["teams"][0]["bans"]
            else:
                bans = LoLGame_summary_json["teams"][0]["bans"] + LoLGame_summary_json["teams"][1]["bans"]
                if len(LoLGame_summary_json["teams"]) > 2:
                    logPrint("警告：对局%d中含有%d支阵营。\nWarning: There're %d teams in Match %d." %(matchId, len(LoLGame_summary_json["teams"]), len(LoLGame_summary_json["teams"]), matchId), verbose = verbose)
            if LoLGame_summary_json["gameMode"] == "CHERRY" and Patch("14.8") < Patch(version):
                bans_tmp: list[dict[str, int]] = bans[:]
                bans = []
                emptyBan: dict[str, int] = {"championId": -1, "pickTurn": 0} #定义一个初始化禁用字典，用于后续数据框填充空值（Define an initialized banning dictionary so that empty values are appended to the dataframe at certain times subsequently）
                playerSubteam: dict[int, list[int]] = {} #存储不同子阵营的玩家，键是子阵营序号，值是该子阵营中的玩家的API序号列表（Stores different subteams' players. Keys are playerSubteamIds, and values are index lists from API for players in the subteams）
                for i in range(len(LoLGame_summary_json["participants"])):
                    bans.append(emptyBan.copy())
                    playerSubteamId: int = LoLGame_summary_json["participants"][i]["playerSubteamId"]
                    if not playerSubteamId in playerSubteam:
                        playerSubteam[playerSubteamId] = []
                    playerSubteam[playerSubteamId].append(i)
                if Patch("14.12") < Patch(version):
                    participantBanIds: list[int] = []
                    for i in sorted(playerSubteam.keys()):
                        participantBanIds += playerSubteam[i] #这里默认采用某个子阵营在API中记录的第一名玩家作为该子阵营的先选者。这可能与实际选用顺序有出入（Here the first player of a subteam recorded in API is considered as the player that picks a champion first. This player may not be the real first player.）
                else:
                    participantBanIds = [playerSubteam[i][0] for i in sorted(playerSubteam.keys())] #这里默认采用某个子阵营在API中记录的第一名玩家作为禁用英雄的玩家。这可能与实际禁用英雄的玩家有出入（Here the first player of a subteam recorded in API is considered as the player that banned some champion. This player may not be the real player that banned it）
                for i in range(len(participantBanIds)):
                    bans[participantBanIds[i]] = bans_tmp[i]
            legacy_banData_appended: dict[int, bool] = {100: False, 200: False} #自定义对局中的征召模式是由每个阵营的1号选手禁用3个英雄，所以当禁用信息添加到一个阵营的第一名玩家后，后续玩家不需要再添加禁用信息。这个字典就是用来判断这一点的（Draft mode in custom matches is performed by the first player of each team banning 3 champions, so if the ban information is added into the first player, the subsequent player in the same team doesn't need to add this information. That's what this dictionary is used for）
            if excluded_reserve or len(set(puuidList) & set(map(lambda x: x["puuid"], LoLGame_summary_json["participants"]))) != 0: #之所以使用玩家通用唯一识别码，而不是用召唤师名称来识别对局是否包含主玩家，是因为该玩家可能使用过改名卡。这里也没有选择帐户序号，这是因为保存在对局中的各玩家的帐户序号竟然是0！（The reason why the puuid instead of the displayName or summonerName is used to identify whether the matches contain the main player is that the player may have used name changing card. AccountId isn't chosen here, because all players' accountIds saved in the match fetched from 127 API is 0, to my surprise!）
                #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                if useAllVersions:
                    ##游戏模式（Game mode）
                    queueIds_match_list: list[int] = []
                    if "queueId" in LoLGame_summary_json:
                        queueIds_match_list.append(LoLGame_summary_json["queueId"])
                    for i in queueIds_match_list:
                        if not i in queues and current_versions["queue"] != bigVersion:
                            queuePatch_adopted = bigVersion
                            queue_recapture = 1
                            logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, queue_recapture, queuePatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, queuePatch_adopted, queue_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    queue: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    queuePatch_deserted: str = queuePatch_adopted
                                    queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                    queue_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if queue_recapture < 3:
                                        queue_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game mode (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                    queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                    current_versions["queue"] = queuePatch_adopted
                                    unmapped_keys["queue"].clear()
                                    break
                            break
                    ##召唤师图标（Summoner icon）
                    summonerIconIds_match_set: set[int] = set()
                    for participant in LoLGame_summary_json["participants"]:
                        if "profileIcon" in participant:
                            summonerIconIds_match_set.add(participant["profileIcon"])
                    summonerIconIds_match_list: list[int] = sorted(summonerIconIds_match_set)
                    for i in summonerIconIds_match_list:
                        if not i in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                            summonerIconPatch_adopted: str = bigVersion
                            summonerIcon_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, summonerIcon_recapture, summonerIconPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    summonerIcon: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    summonerIconPatch_deserted: str = summonerIconPatch_adopted
                                    summonerIconPatch_adopted = FindPostPatch(Patch(summonerIconPatch_adopted), versionList)
                                    summonerIcon_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if summonerIcon_recapture < 3:
                                        summonerIcon_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted), verbose = verbose)
                                    summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcon}
                                    current_versions["summonerIcon"] = summonerIconPatch_adopted
                                    unmapped_keys["summonerIcon"].clear()
                                    break
                            break
                    ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
                    LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: x["championId"], LoLGame_summary_json["participants"])) | set(map(lambda x: x["championId"], bans))) #英雄序号是一直存在的（ChampionId always exists）
                    for i in LoLChampionIds_match_list:
                        if not i in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                            LoLChampionPatch_adopted: str = bigVersion
                            LoLChampion_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, LoLChampion_recapture, LoLChampionPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    LoLChampion: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                                    LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                                    LoLChampion_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if LoLChampion_recapture < 3:
                                        LoLChampion_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                                    LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                                    current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                    unmapped_keys["LoLChampion"].clear()
                                    break
                            break
                    ##召唤师技能（Summoner spells）
                    spellIds_match_set: set[int] = set()
                    for participant in LoLGame_summary_json["participants"]:
                        for key in ["spell1Id", "spell2Id"]:
                            if key in participant:
                                spellIds_match_set.add(participant["spell1Id"])
                    spellIds_match_list: list[int] = sorted(spellIds_match_set)
                    for i in spellIds_match_list:
                        if not i in spells and current_versions["spell"] != bigVersion and i != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                            spellPatch_adopted: str = bigVersion
                            spell_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, spell_recapture, spellPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, spellPatch_adopted, spell_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    spell: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    spellPatch_deserted: str = spellPatch_adopted
                                    spellPatch_adopted = FindPostPatch(Patch(spellPatch_adopted), versionList)
                                    spell_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if spell_recapture < 3:
                                        spell_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted), verbose = verbose)
                                    spells = {int(spell_iter["id"]): spell_iter for spell_iter in spell}
                                    current_versions["spell"] = spellPatch_adopted
                                    unmapped_keys["spell"].clear()
                                    break
                            break
                    ##英雄联盟装备（LoL items）
                    LoLItemIds_match_set: set[int] = set()
                    for participant in LoLGame_summary_json["participants"]:
                        for key in ["item0", "item1", "item2", "item3", "item4", "item5", "item6", "roleBoundItem"]:
                            if key in participant:
                                LoLItemIds_match_set.add(participant[key])
                    LoLItemIds_match_list: list[int] = sorted(LoLItemIds_match_set)
                    for i in LoLItemIds_match_list:
                        if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                            LoLItemPatch_adopted: str = bigVersion
                            LoLItem_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, LoLItem_recapture, LoLItemPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    LoLItem: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    LoLItemPatch_deserted: str = LoLItemPatch_adopted
                                    LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                                    LoLItem_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if LoLItem_recapture < 3:
                                        LoLItem_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                                    LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                                    current_versions["LoLItem"] = LoLItemPatch_adopted
                                    unmapped_keys["LoLItem"].clear()
                                    break
                            break
                    ##符文（Perks）
                    perkIds_match_set: set[int] = set()
                    for participant in LoLGame_summary_json["participants"]:
                        if "perks" in participant:
                            if "statPerks" in participant["perks"]:
                                perkIds_match_set |= set(participant["perks"]["statPerks"].values())
                            if "styles" in participant["perks"]:
                                for style in participant["perks"]["styles"]:
                                    if "selections" in style:
                                        for perkSelection in style["selections"]:
                                            if "perk" in perkSelection:
                                                perkIds_match_set.add(perkSelection["perk"])
                    perkIds_match_list: list[int] = sorted(perkIds_match_set)
                    for i in perkIds_match_list:
                        if not i in perks and current_versions["perk"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                            perkPatch_adopted: str = bigVersion
                            perk_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, perk_recapture, perkPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, perkPatch_adopted, perk_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    perk: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    perkPatch_deserted = perkPatch_adopted
                                    perkPatch_adopted = FindPostPatch(Patch(perkPatch_adopted), versionList)
                                    perk_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if perk_recapture < 3:
                                        perk_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted), verbose = verbose)
                                    perks = {int(perk_iter["id"]): perk_iter for perk_iter in perk}
                                    current_versions["perk"] = perkPatch_adopted
                                    unmapped_keys["perk"].clear()
                                    break
                            break
                    ##符文系（Perkstyles）
                    perkstyleIds_match_set: set[int] = set()
                    for participant in LoLGame_summary_json["participants"]:
                        if "perks" in participant and "styles" in participant["perks"]:
                            for style in participant["perks"]["styles"]:
                                if "style" in style:
                                    perkstyleIds_match_set.add(style["style"])
                    perkstyleIds_match_list: list[int] = sorted(perkstyleIds_match_set)
                    for i in perkstyleIds_match_list:
                        if not i in perkstyles and current_versions["perkstyle"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                            perkstylePatch_adopted: str = bigVersion
                            perkstyle_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, perkstyle_recapture, perkstylePatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    perkstyle: dict[str, Any] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    perkstylePatch_deserted = perkstylePatch_adopted
                                    perkstylePatch_adopted = FindPostPatch(Patch(perkstylePatch_adopted), versionList)
                                    perkstyle_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if perkstyle_recapture < 3:
                                        perkstyle_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted), verbose = verbose)
                                    perkstyles = {int(perkstyle_iter["id"]): perkstyle_iter for perkstyle_iter in perkstyle["styles"]}
                                    current_versions["perkstyle"] = perkstylePatch_adopted
                                    unmapped_keys["perkstyle"].clear()
                                    break
                            break
                    ##斗魂竞技场强化符文（Cherry augments）
                    CherryAugmentIds_match_set: set[int] = set()
                    for participant in LoLGame_summary_json["participants"]:
                        for i in range(1, 7):
                            key = f"playerAugment{i}"
                            if key in participant:
                                CherryAugmentIds_match_set.add(participant[key])
                    CherryAugmentIds_match_list: list[int] = sorted(CherryAugmentIds_match_set)
                    for i in CherryAugmentIds_match_list:
                        if not i in CherryAugments and current_versions["CherryAugment"] != bigVersion and i != 0:
                            CherryAugmentPatch_adopted: str = bigVersion
                            CherryAugment_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, CherryAugment_recapture, CherryAugmentPatch_adopted, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    CherryAugment: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    CherryAugmentPatch_deserted: str = CherryAugmentPatch_adopted
                                    CherryAugmentPatch_adopted = FindPostPatch(Patch(CherryAugmentPatch_adopted), versionList)
                                    CherryAugment_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if CherryAugment_recapture < 3:
                                        CherryAugment_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchId: %d)!" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, i, i, LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted), verbose = verbose)
                                    CherryAugments = {int(CherryAugment_iter["id"]): CherryAugment_iter for CherryAugment_iter in CherryAugment}
                                    current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                    unmapped_keys["CherryAugment"].clear()
                                    break
                            break
                #下面开始整理数据（Organize data）
                for i in range(len(LoLGame_summary_json["participants"])):
                    participant_puuid: str = LoLGame_summary_json["participants"][i]["puuid"]
                    if not (not save_bot and participant_puuid == BOT_UUID or not save_self and participant_puuid in puuidList or not save_other and not participant_puuid in puuidList):
                        generate_LoLGameSummary_records_sgp(LoLGame_stat_data, LoLGame_summary, i, queues, summonerIcons, LoLChampions, spells, LoLItems, perks, perkstyles, CherryAugments, gameIndex = LoLMatchIDs.index(matchId) + 1, current_puuid = puuidList, bans = bans, legacy_banData_appended = legacy_banData_appended, unmapped_keys = unmapped_keys, log = log, verbose = verbose)
                if excluded_reserve:
                    logPrint("[%d/%d]对局%d不包含主玩家。已保留该对局。\nMatch %d doesn't contain the main player but is reserved." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, matchId), print_time = True, verbose = verbose)
                else:
                    logPrint("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %s" %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId), print_time = True, verbose = verbose)
            else:
                matches_to_remove.append(matchId)
                logPrint("[%d/%d]对局%d不包含主玩家。已移除该对局。\nMatch %d doesn't contain the main player and is deprecated." %(LoLMatchIDs.index(matchId) + 1, len(LoLMatchIDs), matchId, matchId), print_time = True, verbose = verbose)
        else:
            logPrint(LoLGame_summary, verbose = verbose)
            error_LoLMatchIDs.append(matchId)
    if len(error_LoLMatchIDs) > 0:
        logPrint("警告：以下%d场对局获取失败。\nWarning: The following %d match(es) fail to be fetched." %(len(error_LoLMatchIDs), len(error_LoLMatchIDs)), verbose = verbose)
        logPrint(error_LoLMatchIDs, verbose = verbose)
    if len(matches_to_remove) > 0:
        logPrint("注意：以下%d场对局因不包含主玩家而被移除。\nAttention: The following %d match(es) are removed because they don't contain the main player." %(len(matches_to_remove), len(matches_to_remove)), verbose = verbose)
        logPrint(matches_to_remove, verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    LoLGame_stat_statistics_output_order: list[int] = [0, 112, 148, 131, 132, 146, 128, 147, 68, 21, 16, 13, 25, 26, 11, 18, 22, 14, 29, 15, 20, 30, 19, 24, 227, 218, 628, 184, 54, 625, 626, 96, 133, 125, 82, 152, 135, 52, 51, 55, 223, 224, 186, 187, 188, 189, 190, 191, 192, 221, 200, 212, 201, 213, 202, 214, 203, 215, 204, 216, 205, 217, 95, 64, 45, 229, 230, 231, 234, 235, 98, 94, 99, 49, 72, 71, 74, 73, 66, 167, 129, 113, 174, 153, 164, 157, 115, 102, 169, 156, 114, 101, 168, 97, 61, 60, 58, 59, 161, 162, 166, 158, 159, 116, 103, 170, 62, 176, 179, 178, 136, 177, 65, 79, 232, 80, 233, 93, 57, 163, 105, 155, 160, 171, 172, 83, 84, 106, 108, 173, 85, 107, 67, 47, 109, 110, 100, 48, 56, 78, 130, 127, 111, 43, 44, 104, 69, 70, 175, 63, 46, 81, 154, 165, 137, 139, 141, 142, 228, 144, 145, 602, 616, 608, 604, 609, 605, 610, 606, 611, 607, 620, 618, 621, 619, 598, 596, 597, 50, 149, 150, 75, 76, 77, 182, 181, 180, 236, 117, 143, 672, 658, 643, 728, 674, 671, 675, 647, 660, 715, 692, 687, 721, 701, 712, 705, 689, 678, 717, 704, 688, 677, 716, 673, 655, 654, 652, 653, 709, 710, 714, 706, 707, 690, 679, 718, 656, 723, 726, 725, 694, 724, 659, 665, 666, 670, 651, 711, 681, 703, 708, 729, 719, 720, 668, 669, 682, 683, 661, 645, 684, 685, 676, 646, 650, 664, 693, 691, 686, 641, 642, 680, 662, 663, 722, 657, 644, 667, 702, 713, 695, 696, 697, 698, 727, 699, 700, 802, 750, 749, 773, 759, 744, 830, 831, 833, 775, 772, 776, 748, 761, 817, 793, 788, 823, 803, 814, 807, 790, 779, 819, 806, 789, 778, 818, 774, 756, 755, 753, 754, 811, 812, 816, 808, 809, 791, 780, 820, 757, 825, 828, 827, 795, 826, 760, 766, 767, 834, 771, 752, 813, 782, 810, 805, 832, 821, 822, 769, 770, 762, 746, 785, 786, 783, 784, 777, 747, 751, 765, 794, 792, 787, 742, 743, 781, 763, 764, 824, 758, 745, 768, 804, 815, 796, 797, 798, 799, 829, 800, 801, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 381, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 382, 283, 284, 285, 383, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 384, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 385, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 237]
    LoLGame_stat_data_organized: dict[str, list[Any]] = {LoLGame_summary_header_keys[i]: LoLGame_stat_data[LoLGame_summary_header_keys[i]] for i in LoLGame_stat_statistics_output_order}
    LoLGame_stat_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_stat_data_organized)
    logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...", verbose = verbose)
    optimize_bool_display(LoLGame_stat_df)
    logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!", verbose = verbose)
    LoLGame_stat_df = pandas.concat([pandas.DataFrame([LoLGame_summary_header])[LoLGame_stat_df.columns], LoLGame_stat_df], ignore_index = True)
    return LoLGame_stat_df

def sort_LoLGame_timeline(LoLGame_timeline: dict[str, Any], LoLGame_summary: dict[str, Any], LoLChampions: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], useAllVersions: bool = False, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, pandas.DataFrame, dict[int, dict[str, Any]]]: #对局时间轴的整理依赖于对局概要（Sorting out match timeline relies on the match summary）
    '''
    将英雄联盟对局时间轴信息整理成对局时间轴和对局事件两张表格。<br>Organize LoL match timeline information into two dataframes including match timeline and match events.
    
    :param LoLGame_timeline: 英雄联盟对局时间轴。通过以下LCU接口得到：<br>LoL match timeline, obtained through the following LCU endpoint:
    
        - `GET /lol-match-history/v1/game-timelines/{gameId}`
    :type LoLGame_timeline: dict[str, Any]
    :param LoLGame_summary: 英雄联盟对局概要。通过以下LCU接口得到：<br>LoL match summary, obtained through the following LCU endpoint:
    
        - `GET /lol-match-history/v1/games/{gameId}`
        
        在整理时间轴的信息时，仍然需要使用对局概要的一些信息。<br>To organize the timeline information, match summary is needed.
    :type LoLGame_summary: dict[str, Any]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局时间轴数据框、对局事件数据框和英雄联盟装备数据资源。<br>Match timeline dataframe, match event dataframe and LoL item data resource.
    :rtype: tuple[pandas.DataFrame, pandas.DataFrame, dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"LoLChampion": "", "LoLItem": ""}
    if unmapped_keys == None:
        unmapped_keys = {"LoLChampion": set(), "LoLItem": set()}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    #准备LoLGame_summary的相关变量（Prepare variables related to `LoLGame_summary`）
    matchId: int = LoLGame_summary["gameId"]
    version: str = LoLGame_summary["gameVersion"]
    bigVersion: str = ".".join(version.split(".")[:2])
    LoLGame_summary_participantIdentities: dict[int, dict[str, Any]] = {participant["participantId"]: participant["player"] for participant in LoLGame_summary["participantIdentities"]} #构建从玩家序号到玩家身份的映射（Build the map from participantId to participant identity）
    LoLGame_summary_participants: dict[int, dict[str, Any]] = {participant["participantId"]: participant for participant in LoLGame_summary["participants"]} #构建从玩家序号到玩家的映射（Build the map from participantId to participant）
    #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
    if useAllVersions:
        ##英雄：只包含选用英雄（LoL champions, which only contain picked ones）
        LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: x["championId"], LoLGame_summary["participants"])))
        for i in LoLChampionIds_match_list:
            if not i in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                LoLChampionPatch_adopted: str = bigVersion
                LoLChampion_recapture: int = 1
                logPrint("对局%d英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(matchId, i, LoLChampion_recapture, LoLChampionPatch_adopted, i, matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        LoLChampion: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                        LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                        LoLChampion_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if LoLChampion_recapture < 3:
                            LoLChampion_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                        LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                        current_versions["LoLChampion"] = LoLChampionPatch_adopted
                        unmapped_keys["LoLChampion"].clear()
                        break
                break
    #数据整理核心部分（Data organization core part）
    ##时间轴（Timeline）
    frames: list[dict[str, Any]] = LoLGame_timeline["frames"]
    LoLGame_timeline_header_keys: list[str] = list(LoLGame_timeline_header.keys())
    LoLGame_timeline_data: dict[str, list[Any]] = {key: [] for key in LoLGame_timeline_header_keys}
    for frame in frames:
        if frame["participantFrames"] == None: #在诸如训练模式提前退出游戏的情况下极易在最后一个记录帧出现这种情况（Under situations where a player exits a solo Practice game, the last recorded frame is likely to become this）
            continue
        participantFrames: dict[int, dict[str, Any]] = {int(key): value for (key, value) in frame["participantFrames"].items()}
        for participantId_index in range(len(participantFrames)):
            isHeaderRecord: bool = participantId_index == 0
            participantId: int = sorted(participantFrames.keys())[participantId_index]
            participant: dict[str, Any] = participantFrames[participantId]
            LoLGame_summary_participantIdentity: dict[str, Any] = LoLGame_summary_participantIdentities[participant["participantId"]] #虽然说“participantFrames”的值的键就是玩家序号，但是保险起见，还是提取“participantId”键的值作为玩家序号（Although the keys of the value of "participantFrames" key are participantIds, as a precaution, we take the value of the "participantId" key as the participantId instead）
            LoLGame_summary_participant: dict[str, Any] = LoLGame_summary_participants[participant["participantId"]]
            for i in range(len(LoLGame_timeline_header)): #注意由于对局概要和对局时间轴是绑定在一起的，所以这里会用到构建LoLGame_summary_df时的一些变量，包括player_count（Note that since the match summary and match timeline are tied together, some variables during the creation of "LoLGame_summary_df" will be reused in the following code, including player_count）
                key: str = LoLGame_timeline_header_keys[i]
                if i <= 2:
                    if isHeaderRecord:
                        if i == 0: #事件（`events`）
                            to_append: Any = json.dumps(frame["events"], ensure_ascii = False)
                        elif i == 2: #时间（`time`）
                            to_append = lcuTime(frame["timestamp"] // 1000) #使用lcuTime函数将时间戳转化为时间（Use function lcuTime to convert timestamp into time）
                        else: #时间戳（`timestamp`）
                            to_append = frame[key]
                    else: #对于同一个记录帧的多个玩家而言，时间戳和事件只需要输出一次即可。剩余部分留空，以保证表格对齐（For multiple players in one frame, timestamp and events only need to be appended once. The rest part should be empty stings to align the table）
                        to_append = ""
                elif i <= 9:
                    if i >= 4 and i <= 7: #选用英雄相关键（Champion-related keys）
                        championId: int = LoLGame_summary_participant["championId"]
                        if i == 4: #选用英雄序号（`championId`）
                            to_append = championId
                        else:
                            if championId in LoLChampions:
                                to_append = LoLChampions[championId][key.split("_")[1]]
                            else:
                                if not championId in unmapped_keys["LoLChampion"]:
                                    unmapped_keys["LoLChampion"].add(championId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                to_append = ""
                    elif i == 8: #召唤师名称（`summonerName`）
                        to_append = get_info_name(LoLGame_summary_participantIdentity)
                    elif i == 9: #阵营（`team_color`）
                        to_append = team_colors_int[LoLGame_summary_participant["teamId"]]
                    else: #阵营代号（`teamId`）
                        to_append = LoLGame_summary_participant["teamId"]
                else:
                    if i == 16: #当前位置坐标（`position`）
                        position: dict[str, int] = participant["position"]
                        to_append = "(%d, %d)" %(position["x"], position["y"])
                    else:
                        to_append = participant.get(key, "") #部分自定义对局存在后续事件无内容的情况，即participantFrames为空（Some custom matches don't have anything in later events, namely the "participantFrames" parameter is empty. More details in PBE1-4422435386）
                LoLGame_timeline_data[key].append(to_append)
    LoLGame_timeline_statistics_output_order: list[int] = [1, 2, 3, 9, 15, 8, 5, 6, 13, 19, 16, 14, 12, 10, 18, 11, 17]
    LoLGame_timeline_data_organized: dict[str, list[Any]] = {LoLGame_timeline_header_keys[i]: LoLGame_timeline_data[LoLGame_timeline_header_keys[i]] for i in LoLGame_timeline_statistics_output_order}
    LoLGame_timeline_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_timeline_data_organized)
    LoLGame_timeline_df = pandas.concat([pandas.DataFrame([LoLGame_timeline_header])[LoLGame_timeline_df.columns], LoLGame_timeline_df], ignore_index = True)
    ##事件（Events）
    LoLGame_event_header_keys: list[str] = list(LoLGame_event_header.keys())
    LoLGame_event_data: dict[str, list[Any]] = {key: [] for key in LoLGame_event_header_keys}
    events: dict[int, dict[str, Any]] = {}
    for frame in frames:
        for event in frame["events"]:
            events[event["timestamp"]] = event
    #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
    if useAllVersions:
        ##英雄联盟装备（LoL items）
        LoLItemIds_match_list: list[int] = sorted(set(map(lambda x: x["itemId"], events.values())))
        for i in LoLItemIds_match_list:
            if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                LoLItemPatch_adopted: str = bigVersion
                LoLItem_recapture: int = 1
                logPrint("对局%d英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(matchId, i, LoLItem_recapture, LoLItemPatch_adopted, i, matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                while True:
                    try:
                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                        LoLItem: list[dict[str, Any]] = source.json()
                    except requests.exceptions.JSONDecodeError:
                        LoLItemPatch_deserted: str = LoLItemPatch_adopted
                        LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                        LoLItem_recapture = 1
                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                    except requests.exceptions.RequestException:
                        if LoLItem_recapture < 3:
                            LoLItem_recapture += 1
                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        else:
                            logPrint("网络环境异常！对局%d的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                            break
                    else:
                        logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                        LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                        current_versions["LoLItem"] = LoLItemPatch_adopted
                        unmapped_keys["LoLItem"].clear()
                        break
                break
    champion_subkey_index_map: list[str] = ["name", "alias", "squarePortraitPath"]
    for timestamp in sorted(events.keys()):
        event: dict[str, Any] = events[timestamp]
        for i in range(len(LoLGame_event_header)):
            key: str = LoLGame_event_header_keys[i]
            if i <= 14:
                if i == 1: #被摧毁的建筑物类型（`buildingTypes`）
                    to_append: Any = buildingTypes[event["buildingType"]]
                elif i == 4: #线路位置（`laneType`）
                    to_append = laneTypes[event["laneType"]]
                elif i == 5: #野区生物亚型（`monsterSubType`）
                    to_append = monsterSubTypes[event["monsterSubType"]]
                elif i == 6: #野区生物类型（`monsterType`）
                    to_append = monsterTypes[event["monsterType"]]
                elif i == 8: #位置坐标（`position`）
                    to_append = "(%s, %s)" %(event["position"]["x"], event["position"]["y"])
                elif i == 12: #防御塔类型（`towerType`）
                    to_append = towerTypes[event["towerType"]]
                elif i == 13: #事件类型（`type`）
                    to_append = eventTypes[event["type"]]
                else:
                    to_append = event[key]
            else:
                if i <= 19: #助攻者相关键（Assistant-related keys）
                    if i <= 18: #助攻者英雄相关键（Assistant champion related keys）
                        assistingChampionIds: list[Any] = []
                        assistingChampion_names: list[Any] = []
                        assistingChampion_aliases: list[Any] = []
                        assistingChampion_squarePortraitPaths: list[Any] = []
                        for participantId in event["assistingParticipantIds"]:
                            if participantId in LoLGame_summary_participants:
                                championId: int = LoLGame_summary_participants[participantId]["championId"]
                                if i == 15: #助攻者英雄序号（`assistingChampionIds`）
                                    assistingChampionIds.append(championId)
                                else:
                                    if championId in LoLChampions:
                                        if i == 16: #助攻者英雄名称（`assistingChampionNames`）
                                            assistingChampion_names.append(LoLChampions[championId]["name"])
                                        elif i == 17: #助攻者英雄代号（`assistingChampionAliases`）
                                            assistingChampion_aliases.append(LoLChampions[championId]["alias"])
                                        else: #助攻者英雄方块头像路径（`assistingChampionSquarePortraitPaths`）
                                            assistingChampion_squarePortraitPaths.append(LoLChampions[championId]["squarePortraitPath"])
                                    else:
                                        if i == 16:
                                            assistingChampion_names.append(championId)
                                        elif i == 17:
                                            assistingChampion_aliases.append("")
                                        else:
                                            assistingChampion_squarePortraitPaths.append("")
                            else: #在末日人工智能中，末日BOSS维迦的参与者序号是0（In Doom Bots, Boss Veigar's participantId is 0）
                                if i == 15:
                                    assistingChampionIds.append("")
                                elif i == 16:
                                    assistingChampion_names.append("")
                                elif i == 17:
                                    assistingChampion_aliases.append("")
                                else:
                                    assistingChampion_squarePortraitPaths.append("")
                        to_append = json.dumps(assistingChampionIds if i == 15 else assistingChampion_names if i == 16 else assistingChampion_aliases if i == 17 else assistingChampion_squarePortraitPaths, ensure_ascii = False)
                    else: #助攻者召唤师名（`assistingParticipantSummonerName`）
                        assistingParticipant_summonerNames: list[str] = []
                        for participantId in event["assistingParticipantIds"]:
                            if participantId in LoLGame_summary_participantIdentities:
                                player: dict[str, Any] = LoLGame_summary_participantIdentities[participantId]
                                assistingParticipant_summonerNames.append(get_info_name(player))
                            else:
                                assistingParticipant_summonerNames.append("")
                        to_append = json.dumps(assistingParticipant_summonerNames, ensure_ascii = False)
                    if to_append == "[]":
                        to_append = ""
                elif i == 20 or i == 21: #装备相关键（Item related keys）
                    itemId: int = event["itemId"]
                    if itemId == 0:
                        to_append = ""
                    elif itemId in LoLItems:
                        to_append = LoLItems[itemId]["name" if i == 20 else "iconPath"]
                    else:
                        if not itemId in unmapped_keys["LoLItem"]:
                            unmapped_keys["LoLItem"].add(itemId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                        to_append = itemId if i == 20 else ""
                elif i >= 22 and i <= 26 or i >= 27 and i <= 31 or i >= 34: #单数玩家相关键（Singular player related keys）
                    if i >= 22 and i <= 26: #击杀者相关键（Killer-related keys）
                        subkey: str = "killerId"
                        champion_subkey_index: int = i - 23
                    elif i >= 27 and i <= 31: #参与者相关键（Participant-related keys）
                        subkey = "participantId"
                        champion_subkey_index = i - 28
                    else: #被杀者相关键（Victim-related keys）
                        subkey = "victimId"
                        champion_subkey_index = i - 35
                    if event[subkey] == 0:
                        to_append = ""
                    else:
                        if champion_subkey_index <= 2: #英雄相关键（Champion related keys）
                            if event[subkey] in LoLGame_summary_participants:
                                championId: int = LoLGame_summary_participants[event[subkey]]["championId"]
                                if champion_subkey_index == -1: #英雄序号（ChampionId）
                                    to_append = championId
                                else: #英雄子键（Champion's subkeys）
                                    if championId in LoLChampions:
                                        to_append = LoLChampions[championId][champion_subkey_index_map[champion_subkey_index]]
                                    else:
                                        to_append = championId if champion_subkey_index == 0 else ""
                            else:
                                to_append = ""
                        else: #召唤师名（SummonerName）
                            if event[subkey] in LoLGame_summary_participantIdentities:
                                player: dict[str, Any] = LoLGame_summary_participantIdentities[event[subkey]]
                                to_append = get_info_name(player)
                            else:
                                to_append = ""
                elif i == 32: #阵营（`team_color`）
                    to_append = team_colors_int[event["teamId"]]
                else: #时间（`time`）
                    to_append = lcuTime(event["timestamp"] // 1000)
            LoLGame_event_data[key].append(to_append)
    LoLGame_event_statistics_output_order: list[int] = [11, 33, 8, 13, 3, 23, 24, 26, 14, 35, 36, 38, 0, 16, 17, 19, 6, 5, 10, 32, 4, 1, 12]
    LoLGame_event_data_organized: dict[str, list[Any]] = {LoLGame_event_header_keys[i]: LoLGame_event_data[LoLGame_event_header_keys[i]] for i in LoLGame_event_statistics_output_order}
    LoLGame_event_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_event_data_organized)
    LoLGame_event_df = pandas.concat([pandas.DataFrame([LoLGame_event_header])[LoLGame_event_df.columns], LoLGame_event_df], ignore_index = True)
    return (LoLGame_timeline_df, LoLGame_event_df, LoLItems)

async def sort_LoLGame_timeline_sgp(connection: Connection, LoLGame_timeline: dict[str, Any], LoLGame_summary: dict[str, Any], LoLChampions: dict[int, dict[str, Any]], LoLItems: dict[int, dict[str, Any]], useAllVersions: bool = False, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[int]]] = None, useInfoDict: bool = False, infos: Optional[dict[str, dict[str, Any]]] = None, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, pandas.DataFrame, dict[int, dict[str, Any]]]:
    '''
    将英雄联盟对局时间轴信息整理成对局时间轴和对局事件两张表格。<br>Organize LoL match timeline information into two dataframes including match timeline and match events.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param LoLGame_timeline: 英雄联盟对局时间轴。通过以下SGP接口得到：<br>LoL match timeline, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/lol/{match_id}/DETAILS`
    :type LoLGame_timeline: dict[str, Any]
    :param LoLGame_summary: 英雄联盟对局概要。通过以下SGP接口得到：<br>LoL match summary, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/lol/{match_id}/SUMMARY`
        
        在整理时间轴的信息时，仍然需要使用对局概要的一些信息。<br>To organize the timeline information, match summary is needed.
    :type LoLGame_summary: dict[str, Any]
    :param LoLChampions: 整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`
    :type LoLChampions: dict[int, dict[str, Any]]
    :param LoLItems: 整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`
    :type LoLItems: dict[int, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局时间轴数据框、对局事件数据框和英雄联盟装备数据资源。<br>Match timeline dataframe, match event dataframe and LoL item data resource.
    :rtype: tuple[pandas.DataFrame, pandas.DataFrame, dict[int, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"LoLItem": ""}
    if unmapped_keys == None:
        unmapped_keys = {"LoLItem": set()}
    if infos == None:
        infos = {}
    if session == None:
        session = requests.Session()
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    #从时间轴信息准备常量（Prepare constants from timeline information）
    matchId: int = int(LoLGame_timeline["metadata"]["match_id"].split("_")[1])
    frames: list[dict[str, Any]] = LoLGame_timeline["json"]["frames"]
    events: dict[int, dict[str, Any]] = {}
    for frame in frames:
        for event in frame["events"]:
            events[event["timestamp"]] = event
    #准备LoLGame_summary的相关变量（Prepare variables related to `LoLGame_summary`）
    summary_valid: bool = LoLGame_summary.get("json") #表示对局概要信息是否正常获取（Represents whether match summary is normal）
    if summary_valid:
        LoLGame_summary_json: dict[str, Any] = LoLGame_summary["json"]
        version: str = LoLGame_summary_json["gameVersion"]
        bigVersion: str = ".".join(version.split(".")[:2])
        LoLGame_summary_participants: dict[int, dict[str, Any]] = {participant["participantId"]: participant for participant in LoLGame_summary_json["participants"]} #构建从玩家序号到玩家的映射（Build the map from participantId to participant）
        #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
        if useAllVersions:
            ##英雄：只包含选用英雄（LoL champions, which only contain picked ones）
            LoLChampionIds_match_list: list[int] = sorted(set(map(lambda x: x["championId"], LoLGame_summary_json["participants"])))
            for i in LoLChampionIds_match_list:
                if not i in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                    LoLChampionPatch_adopted: str = bigVersion
                    LoLChampion_recapture: int = 1
                    logPrint("对局%d英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(matchId, i, LoLChampion_recapture, LoLChampionPatch_adopted, i, matchId, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            LoLChampion: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            LoLChampionPatch_deserted: str = LoLChampionPatch_adopted
                            LoLChampionPatch_adopted = FindPostPatch(Patch(LoLChampionPatch_adopted), versionList)
                            LoLChampion_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if LoLChampion_recapture < 3:
                                LoLChampion_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted), verbose = verbose)
                            LoLChampions = {int(LoLChampion_iter["id"]): LoLChampion_iter for LoLChampion_iter in LoLChampion}
                            current_versions["LoLChampion"] = LoLChampionPatch_adopted
                            unmapped_keys["LoLChampion"].clear()
                            break
                    break
            ##英雄联盟装备（LoL items）
            LoLItemIds_match_set: set[int] = set()
            for event in events.values():
                if "itemId" in event:
                    LoLItemIds_match_set.add(event["itemId"])
                if "afterId" in event:
                    LoLItemIds_match_set.add(event["afterId"])
                if "beforeId" in event:
                    LoLItemIds_match_set.add(event["beforeId"])
            LoLItemIds_match_list: list[int] = sorted(LoLItemIds_match_set)
            for i in LoLItemIds_match_list:
                if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                    LoLItemPatch_adopted: str = bigVersion
                    LoLItem_recapture: int = 1
                    logPrint("对局%d英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(matchId, i, LoLItem_recapture, LoLItemPatch_adopted, i, matchId, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            LoLItem: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            LoLItemPatch_deserted: str = LoLItemPatch_adopted
                            LoLItemPatch_adopted = FindPostPatch(Patch(LoLItemPatch_adopted), versionList)
                            LoLItem_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if LoLItem_recapture < 3:
                                LoLItem_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d!" %(matchId, i, i, matchId), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted), verbose = verbose)
                            LoLItems = {int(LoLItem_iter["id"]): LoLItem_iter for LoLItem_iter in LoLItem}
                            current_versions["LoLItem"] = LoLItemPatch_adopted
                            unmapped_keys["LoLItem"].clear()
                            break
                    break
    else: #对局概要信息获取异常时，当然无法进行版本回溯（When the match summary has an error, version backtrack can't be performed of course）
        version = "" #此时只是为了后续数据资源的异常处理提示（In this case this variable is only used by subsequent exception handling prompts）
        LoLGame_summary_participants = {}
        for participant in LoLGame_timeline["json"]["participants"]:
            if useInfoDict and participant["puuid"] in infos:
                participant_info_body = infos[participant["puuid"]]
                LoLGame_summary_participants[participant["participantId"]] = participant_info_body
            else:
                participant_info_recapture: int = 0
                participant_info: dict[str, Any] = await get_info(connection, participant["puuid"])
                while not participant_info["info_got"] and participant_info["body"]["httpStatus"] != 404 and participant_info_recapture < 3:
                    logPrint(participant_info["body"], verbose = verbose)
                    participant_info_recapture += 1
                    logPrint("对局%d玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) in Match %d capture failed! Recapturing this player's information ... Times tried: %d." %(matchId, participant["puuid"], participant_info_recapture, participant["puuid"], matchId, participant_info_recapture), verbose = verbose)
                    participant_info = await get_info(connection, participant["puuid"])
                if participant_info["info_got"]:
                    participant_info_body = participant_info["body"]
                    if useInfoDict:
                        infos[participant["puuid"]] = participant_info_body
                    LoLGame_summary_participants[participant["participantId"]] = participant_info_body
                else:
                    logPrint(participant_info["body"], verbose = verbose)
                    logPrint("对局%d玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) in Match %d capture failed!" %(matchId, participant["puuid"], participant["puuid"], matchId), verbose = verbose)
    #数据整理核心部分（Data organization core part）
    ##时间轴（Timeline）
    LoLGame_timeline_header: dict[str, str] = LoLGame_timeline_sgp_header
    LoLGame_timeline_header_keys: list[str] = list(LoLGame_timeline_header.keys())
    LoLGame_timeline_data: dict[str, list[Any]] = {key: [] for key in LoLGame_timeline_header_keys}
    for frame in frames:
        if frame["participantFrames"] == None:
            continue
        participantFrames: dict[int, dict[str, Any]] = {int(key): value for (key, value) in frame["participantFrames"].items()}
        for participantId_index in range(len(participantFrames)):
            isHeaderRecord: bool = participantId_index == 0
            participantId: int = sorted(participantFrames.keys())[participantId_index]
            participant: dict[str, Any] = participantFrames[participantId]
            LoLGame_summary_participant: dict[str, Any] = LoLGame_summary_participants[participant["participantId"]] #虽然说“participantFrames”的值的键就是玩家序号，但是保险起见，还是提取“participantId”键的值作为玩家序号（Although the keys of the value of "participantFrames" key are participantIds, as a precaution, we take the value of the "participantId" key as the participantId instead）
            for i in range(len(LoLGame_timeline_header)): #注意由于对局概要和对局时间轴是绑定在一起的，所以这里会用到构建LoLGame_summary_df时的一些变量，包括player_count（Note that since the match summary and match timeline are tied together, some variables during the creation of "LoLGame_summary_df" will be reused in the following code, including player_count）
                key: str = LoLGame_timeline_header_keys[i]
                if i <= 2:
                    if isHeaderRecord:
                        if i == 0: #事件（`events`）
                            to_append: Any = json.dumps(frame["events"], ensure_ascii = False)
                        elif i == 2: #时间（`time`）
                            to_append = lcuTime(frame["timestamp"] // 1000) #使用lcuTime函数将时间戳转化为时间（Use function lcuTime to convert timestamp into time）
                        else: #时间戳（`timestamp`）
                            to_append = frame[key]
                    else: #对于同一个记录帧的多个玩家而言，时间戳和事件只需要输出一次即可。剩余部分留空，以保证表格对齐（For multiple players in one frame, timestamp and events only need to be appended once. The rest part should be empty stings to align the table）
                        to_append = ""
                elif i <= 9:
                    if summary_valid:
                        if i >= 4 and i <= 7: #选用英雄相关键（Champion-related keys）
                            championId: int = LoLGame_summary_participant["championId"]
                            if i == 4: #选用英雄序号（`championId`）
                                to_append = championId
                            else:
                                if championId in LoLChampions:
                                    to_append = LoLChampions[championId][key.split("_")[1]]
                                else:
                                    if not championId in unmapped_keys["LoLChampion"]:
                                        unmapped_keys["LoLChampion"].add(championId)
                                        logPrint("【%d. %s】对局%d（对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, championId, i, key, championId, matchId, version), verbose = verbose)
                                    to_append = ""
                        elif i == 8: #召唤师名称（`summonerName`）
                            to_append = get_info_name(LoLGame_summary_participant)
                        elif i == 9: #阵营（`team_color`）
                            to_append = team_colors_int[LoLGame_summary_participant["teamId"]]
                        else: #阵营代号（`teamId`）
                            to_append = LoLGame_summary_participant["teamId"]
                    else:
                        if i == 8:
                            to_append = get_info_name(LoLGame_summary_participant)
                        else:
                            to_append = ""
                elif i <= 20:
                    if i == 16: #当前位置坐标（`position`）
                        position: dict[str, int] = participant["position"]
                        to_append = "(%d, %d)" %(position["x"], position["y"])
                    elif i == 20: #控制时长（`timeEnemySpentControlled`）
                        to_append = lcuTime(participant["timeEnemySpentControlled"] / 1000)
                    else:
                        to_append = participant[key]
                else:
                    to_append = participant[key.split()[0]][key.split()[1]]
                LoLGame_timeline_data[key].append(to_append)
    LoLGame_timeline_statistics_output_order: list[int] = [1, 2, 3, 9, 15, 8, 5, 6, 13, 19, 16, 14, 12, 11, 10, 18, 17, 20, 53, 50, 47, 56, 52, 49, 46, 55, 54, 51, 48, 57, 32, 33, 42, 43, 26, 22, 23, 38, 27, 21, 31, 39, 34, 44, 24, 28, 25, 36, 29, 37, 35, 41, 45, 40, 30]
    LoLGame_timeline_data_organized: dict[str, list[Any]] = {LoLGame_timeline_header_keys[i]: LoLGame_timeline_data[LoLGame_timeline_header_keys[i]] for i in LoLGame_timeline_statistics_output_order}
    LoLGame_timeline_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_timeline_data_organized)
    LoLGame_timeline_df = pandas.concat([pandas.DataFrame([LoLGame_timeline_header])[LoLGame_timeline_df.columns], LoLGame_timeline_df], ignore_index = True)
    ##事件（Events）
    LoLGame_event_header: dict[str, str] = LoLGame_event_sgp_header
    LoLGame_event_header_keys: list[str] = list(LoLGame_event_header.keys())
    LoLGame_event_data: dict[str, list[Any]] = {key: [] for key in LoLGame_event_header_keys}
    champion_subkey_index_map: list[str] = ["name", "alias", "squarePortraitPath"]
    item_subkey_index_map: list[str] = ["name", "iconPath"]
    for timestamp in sorted(events.keys()):
        event: dict[str, Any] = events[timestamp]
        for i in range(len(LoLGame_event_header)):
            key: str = LoLGame_event_header_keys[i]
            if i <= 39:
                if key in event:
                    if i == 5: #被摧毁的建筑物类型（`buildingTypes`）
                        to_append: Any = buildingTypes[event["buildingType"]]
                    elif i == 13: #击杀类型（`killTypes`）
                        to_append = killTypes[event["killType"]]
                    elif i == 16: #线路位置（`laneType`）
                        to_append = laneTypes[event["laneType"]]
                    elif i == 18: #升级类型（`levelUpType`）
                        to_append = levelUpTypes[event["levelUpType"]]
                    elif i == 19: #野区生物亚型（`monsterSubType`）
                        to_append = monsterSubTypes[event["monsterSubType"]]
                    elif i == 20: #野区生物类型（`monsterType`）
                        to_append = monsterTypes[event["monsterType"]]
                    elif i == 22: #龙魂名称（`name`）
                        to_append = dragonSoul_names[event["name"]]
                    elif i == 24: #位置坐标（`position`）
                        to_append = "(%s, %s)" %(event["position"]["x"], event["position"]["y"])
                    elif i == 30: #防御塔类型（`towerType`）
                        to_append = towerTypes[event["towerType"]]
                    elif i == 31: #转换形态（`transformType`）
                        to_append = transformTypes[event["transformType"]]
                    elif i == 32: #事件类型（`type`）
                        to_append = eventTypes[event["type"]]
                    elif i in {33, 34, 36, 37}: #json
                        to_append = json.dumps(event[key], ensure_ascii = False)
                        if to_append == "[]":
                            to_append = ""
                    elif i == 38: #守卫类型（`wardType`）
                        to_append = wardTypes[event["wardType"]]
                    else:
                        to_append = event[key]
                else:
                    to_append = ""
            else:
                if i == 40 or i == 71: #游戏内时间戳标准化键（In-game timestamp normalization keys）
                    subkey: str = "actualStartTime" if i == 40 else "timestamp"
                    if subkey in event:
                        to_append = lcuTime(event[subkey] / 1000)
                    else:
                        to_append = ""
                elif i in {41, 42, 48, 49, 56, 57}: #装备相关键（Item related keys）
                    if i == 41 or i == 42: #售出后被撤回的装备相关键（Undoing-sold related keys）
                        subkey = "afterId"
                        item_subkey_index: int = i - 41
                    elif i == 48 or i == 49:
                        subkey = "beforeId"
                        item_subkey_index = i - 48
                    else:
                        subkey = "itemId"
                        item_subkey_index = i - 56
                    if subkey in event:
                        itemId: int = event[subkey]
                        if itemId == 0:
                            to_append = ""
                        elif itemId in LoLItems:
                            to_append = LoLItems[itemId][item_subkey_index_map[item_subkey_index]]
                        else:
                            if not itemId in unmapped_keys["LoLItem"]:
                                unmapped_keys["LoLItem"].add(itemId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, matchId, version, itemId, i, key, itemId, matchId, version), verbose = verbose)
                            to_append = itemId if item_subkey_index == 0 else ""
                    else:
                        to_append = ""
                elif i <= 47: #助攻者相关键（Assistant-related keys）
                    if "assistingParticipantIds" in event:
                        assistingChampionIds: list[Any] = []
                        assistingChampion_names: list[Any] = []
                        assistingChampion_aliases: list[Any] = []
                        assistingChampion_squarePortraitPaths: list[Any] = []
                        assistingParticipant_summonerNames: list[str] = []
                        for participantId in event["assistingParticipantIds"]:
                            if participantId in LoLGame_summary_participants:
                                if i == 47: #助攻者召唤师名（`assistingParticipantSummonerName`）
                                    player: dict[str, Any] = LoLGame_summary_participants[participantId]
                                    assistingParticipant_summonerNames.append(get_info_name(player))
                                else:
                                    if summary_valid:
                                        championId: int = LoLGame_summary_participants[participantId]["championId"]
                                        if i == 43: #助攻者英雄序号（`assistingChampionIds`）
                                            assistingChampionIds.append(championId)
                                        else: #助攻者英雄相关键（Assistant champion related keys）
                                            if championId in LoLChampions:
                                                if i == 44: #助攻者英雄名称（`assistingChampionNames`）
                                                    assistingChampion_names.append(LoLChampions[championId]["name"])
                                                elif i == 45: #助攻者英雄代号（`assistingChampionAliases`）
                                                    assistingChampion_aliases.append(LoLChampions[championId]["alias"])
                                                else: #助攻者英雄方块头像路径（`assistingChampionSquarePortraitPaths`）
                                                    assistingChampion_squarePortraitPaths.append(LoLChampions[championId]["squarePortraitPath"])
                                            else:
                                                if i == 44:
                                                    assistingChampion_names.append(championId)
                                                elif i == 45:
                                                    assistingChampion_aliases.append("")
                                                else:
                                                    assistingChampion_squarePortraitPaths.append("")
                                    else:
                                        if i == 43:
                                            assistingChampionIds.append("")
                                        elif i == 44:
                                            assistingChampion_names.append("")
                                        elif i == 45:
                                            assistingChampion_aliases.append("")
                                        else:
                                            assistingChampion_squarePortraitPaths.append("")
                            else: #在末日人工智能中，末日BOSS维迦的参与者序号是0（In Doom Bots, Boss Veigar's participantId is 0）
                                if i == 43:
                                    assistingChampionIds.append("")
                                elif i == 44:
                                    assistingChampion_names.append("")
                                elif i == 45:
                                    assistingChampion_aliases.append("")
                                elif i == 46:
                                    assistingChampion_squarePortraitPaths.append("")
                                else:
                                    assistingParticipant_summonerNames.append("")
                        to_append = json.dumps(assistingChampionIds if i == 43 else assistingChampion_names if i == 44 else assistingChampion_aliases if i == 45 else assistingChampion_squarePortraitPaths if i == 46 else assistingParticipant_summonerNames, ensure_ascii = False)
                        if to_append == "[]":
                            to_append = ""
                    else:
                        to_append = ""
                elif i >= 50 and i <= 54 or i >= 58 and i <= 62 or i >= 64 and i <= 68 or i >= 72 and i <= 76: #单数玩家相关键（Singular player related keys）
                    if i >= 50 and i <= 54:
                        subkey = "creatorId"
                        champion_subkey_index: int = i - 51
                    elif i >= 58 and i <= 62:
                        subkey = "killerId"
                        champion_subkey_index = i - 59
                    elif i >= 64 and i <= 68:
                        subkey = "participantId"
                        champion_subkey_index = i - 65
                    else:
                        subkey = "victimId"
                        champion_subkey_index = i - 73
                    if subkey in event:
                        if event[subkey] == 0:
                            to_append = ""
                        else:
                            if event[subkey] in LoLGame_summary_participants:
                                if champion_subkey_index == 3: #召唤师名（SummonerName）
                                    player: dict[str, Any] = LoLGame_summary_participants[event[subkey]]
                                    to_append = get_info_name(player)
                                else:
                                    if summary_valid:
                                        championId: int = LoLGame_summary_participants[event[subkey]]["championId"]
                                        if champion_subkey_index == -1: #英雄序号（ChampionId）
                                            to_append = championId
                                        else: #英雄子键（Champion's subkeys）
                                            if championId in LoLChampions:
                                                to_append = LoLChampions[championId][champion_subkey_index_map[champion_subkey_index]]
                                            else:
                                                to_append = championId if champion_subkey_index == 0 else ""
                                    else:
                                        to_append = ""
                            else:
                                to_append = ""
                    else:
                        to_append = ""
                elif i == 55: #先机类型（`featTypeTra`）
                    to_append = featTypes[event["featType"]] if "featType" in event else ""
                elif i in {63, 70, 77}: #阵营相关键（Team related keys）
                    subkey = "killerTeamId" if i == 63 else "teamId" if i == 70 else "winningTeam"
                    to_append = team_colors_int[event[subkey]] if subkey in event else ""
                else: #全球UTC时间（`realTime`）
                    to_append = getISOTime(event["realTimestamp"] / 1000) if "realTimestamp" in event else ""
            LoLGame_event_data[key].append(to_append)
    LoLGame_event_statistics_output_order: list[int] = [29, 71, 32, 13, 21, 12, 15, 63, 14, 59, 60, 62, 24, 35, 73, 74, 76, 34, 33, 37, 36, 26, 2, 44, 45, 47, 20, 19, 22, 28, 70, 16, 5, 30, 4, 7, 55, 8, 11, 56, 1, 41, 3, 48, 10, 38, 6, 51, 52, 54, 23, 65, 66, 68, 17, 18, 27, 31, 0, 40, 25, 69, 39, 77, 9]
    LoLGame_event_data_organized: dict[str, list[Any]] = {LoLGame_event_header_keys[i]: LoLGame_event_data[LoLGame_event_header_keys[i]] for i in LoLGame_event_statistics_output_order}
    LoLGame_event_df: pandas.DataFrame = pandas.DataFrame(data = LoLGame_event_data_organized)
    LoLGame_event_df = pandas.concat([pandas.DataFrame([LoLGame_event_header])[LoLGame_event_df.columns], LoLGame_event_df], ignore_index = True)
    return (LoLGame_timeline_df, LoLGame_event_df, LoLItems)

async def generate_TFTHistory_records(connection: Connection, TFTHistory_data: dict[str, list[Any]], TFTGame_summary: dict[str, Any], participantIndex: int, queues: dict[int, dict[str, Any]], TFTAugments: dict[str, dict[str, Any]], TFTChampions: dict[str, dict[str, Any]], TFTItems: dict[str, dict[str, Any]], TFTCompanions: dict[str, dict[str, Any]], TFTTraits: dict[str, dict[str, Any]], gameIndex: int = 1, unmapped_keys: Optional[dict[str, set[Any]]] = None, useInfoDict: bool = False, infos: Optional[dict[str, dict[str, Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> dict[str, list[Any]]:
    '''
    向云顶之弈对局记录数据中追加记录。<br>Append records to TFT match history data.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param TFTHistory_data: 云顶之弈对局记录数据。记录将追加到其中。<br>TFT match history data. Records are appended into it.
    :type TFTHistory_data: dict[str, list[Any]]
    :param TFTGame_summary: 云顶之弈对局概要。通过以下SGP接口得到：<br>TFT match summary, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/tft/{match_id}/SUMMARY`
    :type TFTGame_summary: dict[str, Any]
    :param participantIndex: 主召唤师索引。从0开始。<br>The index of the main summoner, which starts from 0.
    :type participantIndex: int
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param TFTAugments: 整理后的云顶之弈强化符文数据资源。键是强化符文代码，值是强化符文信息字典。<br>Organized TFT augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始云顶之弈强化符文数据资源可通过以下链接获取：<br>The raw TFT augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/cdragon/tft/en_us.json
    :type TFTAugments: dict[str, dict[str, Any]]
    :param TFTChampions: 整理后的云顶之弈英雄数据资源。键是英雄代码，值是英雄信息字典。<br>Organized TFT champion data resource. Each key is a championid, and each value is a champion information dictionary.
    
        原始云顶之弈英雄数据资源可通过以下链接获取：<br>The raw TFT champion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftchampions.json`
    :type TFTChampions: dict[str, dict[str, Any]]
    :param TFTItems: 整理后的云顶之弈装备信息。键是装备代码，值是装备信息字典。<br>Organized TFT item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始云顶之弈装备数据资源可通过以下链接获取：<br>The raw TFT item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftitems.json`
    :type TFTItems: dict[int, dict[str, Any]]
    :param TFTCompanions: 整理后的小小英雄信息。键是小小英雄代码，值是小小英雄信息字典。<br>Organized companion data resource. Each key is a companionId, and each value is a companion information dictionary.
    
        原始小小英雄数据资源可通过以下链接获取：<br>The raw companion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/companions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/companions.json`
    :type TFTCompanions: dict[str, dict[str, Any]]
    :param TFTTraits: 整理后的云顶之弈羁绊信息。键是羁绊代码，值是羁绊信息字典。<br>Organized TFT trait data resource. Each key is a traitId, and each value is a trait information dictionary.
    
        原始云顶之弈羁绊数据资源可通过以下链接获取：<br>The raw TFT trait data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tfttraits.json`
    :type TFTTraits: dict[str, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param useInfoDict: 是否使用召唤师信息缓存字典。默认为否。<br>Whether to use a summoner information cache dictionary. False by default.
    :type useInfoDict: bool
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 追加数据后的云顶之弈对局记录数据。<br>TFT match history data after appending.
    :rtype: dict[str, list[Any]]
    '''
    #参数预处理（Parameter pre-processing）
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
    if infos == None:
        infos = {}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    version_re: re.Pattern[str] = re.compile(r"\d+\.\d+\.\d+\.\d+")
    TFTHistory_header_keys: list[str] = list(TFTHistory_header.keys())
    if participantIndex == -1: #对局数据记录存在异常时的处理（Exception of match data recording exception）
        for i in range(len(TFTHistory_header_keys)):
            key: str = TFTHistory_header_keys[i]
            if i == 0: #游戏序号（`gameIndex`）
                to_append: Any = gameIndex
            elif i == 5: #对局序号（`game_id`）
                to_append = int(TFTGame_summary["metadata"]["match_id"].split("_")[1])
            elif i == 14: #对局创建时间（`gameCreationDate`）
                to_append = getISOTime(TFTGame_summary["metadata"].get("timestamp", 0) / 1000)
            elif i in {51, 304}:
                to_append = False
            else:
                to_append = ""
            TFTHistory_data[key].append(to_append)
    else:
        TFTGame_summary_json: dict[str, Any] = TFTGame_summary["json"]
        TFTGameVersion: str = version_re.search(TFTGame_summary_json["game_version"]).group()
        TFTPlayer: dict[str, Any] = TFTGame_summary_json["participants"][participantIndex]
        TFTPlayer_Traits: list[dict[str, Any]] = TFTPlayer["traits"]
        TFTPlayer_Units: list[dict[str, Any]] = TFTPlayer["units"]
        TFTPlayer_info_got: bool = False
        TFTPlayer_info_body: dict[str, Any] = {}
        if TFTPlayer["puuid"] != BOT_UUID: #在云顶之弈（新手教程）中，无法通过电脑玩家的玩家通用唯一识别码（00000000-0000-0000-0000-000000000000）来查询其召唤师名称和序号（Summoner names and IDs of bot players in TFT (Tutorial) can't be searched for according to their puuid: 00000000-0000-0000-0000-000000000000）
            if "riotIdGameName" in TFTPlayer and "riotIdTagline" in TFTPlayer:
                TFTPlayer_summonerName: str = "%s#%s" %(TFTPlayer["riotIdGameName"], TFTPlayer["riotIdTagline"])
            else:
                if useInfoDict and TFTPlayer["puuid"] in infos:
                    TFTPlayer_info_body = infos[TFTPlayer["puuid"]]
                    TFTPlayer_summonerName = get_info_name(TFTPlayer_info_body)
                    TFTPlayer_info_got = True
                else:
                    TFTPlayer_info_recapture = 0
                    TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                    while not TFTPlayer_info["info_got"] and TFTPlayer_info["body"]["httpStatus"] != 404 and TFTPlayer_info_recapture < 3:
                        logPrint(TFTPlayer_info["body"], verbose = verbose)
                        TFTPlayer_info_recapture += 1
                        logPrint("对局%d玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) in Match %d capture failed! Recapturing this player's information ... Times tried: %d." %(TFTGame_summary_json["game_id"], TFTPlayer["puuid"], TFTPlayer_info_recapture, TFTPlayer["puuid"], TFTGame_summary_json["game_id"], TFTPlayer_info_recapture), verbose = verbose)
                        TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                    if TFTPlayer_info["info_got"]:
                        TFTPlayer_info_body = TFTPlayer_info["body"]
                        if useInfoDict:
                            infos[TFTPlayer["puuid"]] = TFTPlayer_info_body
                        TFTPlayer_summonerName = get_info_name(TFTPlayer_info_body)
                    else:
                        logPrint(TFTPlayer_info["body"], verbose = verbose)
                        logPrint("对局%d玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) in Match %d capture failed!" %(TFTGame_summary_json["game_id"], TFTPlayer["puuid"], TFTPlayer["puuid"], TFTGame_summary_json["game_id"]), verbose = verbose)
                    TFTPlayer_info_got = TFTPlayer_info["info_got"]
        #数据整理核心部分（Data organization core part）
        for i in range(len(TFTHistory_header)):
            key = TFTHistory_header_keys[i]
            if i == 0: #游戏序号（`gameIndex`）
                to_append: Any = gameIndex
            elif i <= 18:
                if i == 1: #对局终止情况（`endOfGameResult`）
                    to_append = endOfGameResults[TFTGame_summary_json["endOfGameResult"]] if "endOfGameResult" in TFTGame_summary_json else ""
                elif i in {2, 3, 8, 9}:
                    to_append = TFTGame_summary_json.get(key, "") #14.6版本之前的云顶之弈对局概要中没有这些键（Those keys don't exist in summary of TFT matches before Patch 14.6）
                elif i == 3: #对局序号（`gameId`）
                    to_append = TFTGame_summary_json.get("gameId", "") #云顶之弈第10赛季及之前无gameId这一键（Before and including TFT Set10, there's not a "gameId" key）
                elif i == 7: #对局版本（`game_version`）
                    to_append = TFTGameVersion
                elif i == 12: #数据版本名称（`tft_set_core_name`）
                    to_append = TFTGame_summary_json.get("tft_set_core_name", "") #在云顶之弈第7赛季之前，TFTGame_summary_json中无tft_set_core_name这一键（Before TFTSet7, tft_set_core_name isn't present as a key of `TFTGame_summary_json`）
                elif i == 14: #对局创建时间（`gameCreationDate`）
                    to_append = getISOTime(TFTGame_summary_json["gameCreation"] / 1000) if "gameCreation" in TFTGame_summary_json else ""
                elif i == 15: #对局结算时间（`gameDate`）
                    to_append = getISOTime(int(TFTGame_summary_json["game_datetime"]) / 1000)
                elif i == 16: #持续时长（`gameLength`）
                    to_append = lcuTime(TFTGame_summary_json["game_length"])
                elif i == 17: #地图名称（`mapName`）
                    to_append = gamemaps[TFTGame_summary_json["mapId"]]["zh_CN"] if "mapId" in TFTGame_summary_json else ""
                elif i == 18: #游戏模式名称（`gameModeName`）
                    to_append = queues[TFTGame_summary_json["queue_id"]]["description"] if TFTGame_summary_json["queue_id"] in queues else ""
                else:
                    to_append = TFTGame_summary_json[key]
            elif i <= 54:
                if i == 19: #玩家序号（`participantId`）
                    to_append = participantIndex + 1
                elif i >= 20 and i <= 28: #强化符文相关键（Augment-related keys）
                    if "augments" in TFTPlayer:
                        augment_index: int = (i - 20) % 3
                        subkey_index: int = (i - 20) // 3
                        if augment_index < len(TFTPlayer["augments"]):
                            TFTAugmentId: str = TFTPlayer["augments"][augment_index]
                            if subkey_index == 0:
                                to_append = TFTAugmentId
                            elif TFTAugmentId in TFTAugments:
                                to_append = TFTAugments[TFTAugmentId][key.split()[-1]]
                            else:
                                if not TFTAugmentId in unmapped_keys["TFTAugment"]:
                                    unmapped_keys["TFTAugment"].add(TFTAugmentId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）强化符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT augment information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTAugmentId, i, key, TFTAugmentId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                                to_append = TFTAugmentId if subkey_index == 1 else ""
                        else:
                            to_append = ""
                    else:
                        to_append = "" #云顶之弈刚出的时候，没有强化符文的概念（The concept of "augment" didn't appear at the beginning of TFT）
                elif i >= 29 and i <= 35: #小小英雄相关键（Companion-related keys）
                    TFTCompanionId: str = TFTPlayer["companion"]["content_ID"]
                    if i <= 32:
                        to_append = TFTPlayer["companion"][key.split()[-1]]
                    elif TFTCompanionId in TFTCompanions:
                        to_append = TFTCompanions[TFTCompanionId][key.split()[-1]] if i <= 34 else rarities[TFTCompanions[TFTCompanionId][key.split()[-1]]]
                    else:
                        if not TFTCompanionId in unmapped_keys["TFTCompanion"]:
                            unmapped_keys["TFTCompanion"].add(TFTCompanionId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）小小英雄信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT companion information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTCompanionId, i, key, TFTCompanionId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                        to_append = TFTCompanionId if i == 33 else ""
                elif i == 45: #通关人机对战（`pve_wonrun`）
                    to_append = "" if not "pve_wonrun" in TFTPlayer else "√" if TFTPlayer["pve_wonrun"] else "×"
                elif i == 46 or i == 47: #玩家名称和名称编号（`riotIdGameName` and `riotIdTagline`）
                    if key in TFTPlayer:
                        to_append = TFTPlayer[key]
                    else:
                        if TFTPlayer["puuid"] != BOT_UUID and TFTPlayer_info_got:
                            to_append = TFTPlayer_info_body["gameName"] if i == 46 else TFTPlayer_info_body["tagLine"]
                        else:
                            to_append = ""
                elif i == 51: #胜利（`win`）
                    to_append = TFTPlayer.get("win", False)
                elif i == 52: #存活回合（`last_round_format`）
                    lastRound: int = TFTPlayer["last_round"]
                    if lastRound <= 3:
                        bigRound: int = 1
                        smallRound: int = lastRound
                    else:
                        bigRound = (lastRound + 3) // 7 + 1
                        smallRound = (lastRound + 3) % 7 + 1
                    to_append = "%d-%d" %(bigRound, smallRound)
                elif i == 53: #存活时长（`time_eliminated_norm`）
                    to_append = lcuTime(TFTPlayer["time_eliminated"])
                elif i == 54: #结果（`result`）
                    to_append = "" if not "win" in TFTPlayer else "胜利" if TFTPlayer["win"] else "失败"
                    if "endOfGameResult" in TFTGame_summary_json and TFTGame_summary_json["endOfGameResult"] == "Abort_AntiCheatExit":
                        to_append = "被终止"
                else:
                    to_append = TFTPlayer.get(key, "")
            elif i <= 145: #云顶之弈羁绊相关键（TFT trait-related keys）
                trait_index: int = (i - 55) // 7
                subkey_index = (i - 55) % 7
                if trait_index < len(TFTPlayer_Traits): #在这个小于的问题上纠结了很久[敲打]——下标是从0开始的。假设API上记录了n个羁绊，那么当程序正在获取第n个羁绊时，就会引起下标越界的问题。所以这里不能使用小于等于号（I stuck at this less than sign for too long xD - note that the index begins from 0. Suppose there're totally n traits recorded in LCU API. Then, when the program is trying to capture the n-th trait, it'll throw an IndexError. That's why the "less than or equal to" sign can't be used here）
                    TFTTrait_iter: dict[str, Any] = TFTPlayer_Traits[trait_index]
                    TFTTraitId: str = TFTTrait_iter["name"]
                    if TFTTraitId == "TemplateTrait": #CommunityDragon数据库中没有收录模板羁绊的数据（Data about TemplateTrait aren't archived in CommunityDragon database）
                        if subkey_index == 4 and TFTPlayer["puuid"] != BOT_UUID: #在艾欧尼亚的对局序号为4959597974的对局中，存在一个模板羁绊，没有tier_total这个键（There exists a TemplateTrait without the key `tier_total` in an Ionia match with matchId 4959597974）
                            if "riotIdGameName" in TFTPlayer and "riotIdTagline" in TFTPlayer or TFTPlayer_info_got:
                                logPrint("警告：对局%d中玩家%s（玩家通用唯一识别码：%s）的第%d个羁绊是模板羁绊！\nWarning: Trait No. %d of the player %s (puuid: %s) in the match %d is TemplateTrait." %(TFTGame_summary_json["game_id"], TFTPlayer_summonerName, TFTPlayer["puuid"], trait_index + 1, trait_index + 1, TFTPlayer_summonerName, TFTPlayer["puuid"], TFTGame_summary_json["game_id"]), verbose = verbose)
                            to_append = ""
                        else:
                            to_append = TFTTraitId if subkey_index == 5 else "" if subkey_index == 6 else TFTTrait_iter[key.split()[-1]]
                    else:
                        if subkey_index <= 4:
                            if subkey_index == 2:
                                to_append = traitStyles[TFTTrait_iter[key.split()[-1]]]
                            else:
                                to_append = TFTTrait_iter[key.split()[-1]]
                        elif TFTTraitId in TFTTraits:
                            to_append = TFTTraits[TFTTraitId][key.split()[-1]]
                        else:
                            if not TFTTraitId in unmapped_keys["TFTTrait"]:
                                unmapped_keys["TFTTrait"].add(TFTTraitId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）羁绊信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT trait information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTTraitId, i, key, TFTTraitId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                            to_append = TFTTraitId if subkey_index == 5 else ""
                else:
                    to_append = ""
            elif i <= 299:
                if i <= 200: #云顶之弈英雄相关键（TFT champion-related keys）
                    unit_index: int = (i - 146) // 5
                    subkey_index = (i - 146) % 5
                    if unit_index < len(TFTPlayer_Units):
                        TFTChampion_iter: dict[str, Any] = TFTPlayer_Units[unit_index]
                        TFTChampionId: str = TFTChampion_iter["character_id"]
                        if subkey_index >= 3:
                            #character_id_lower: str = TFTPlayer_Units[unit_index]["character_id"].lower()
                            #TFTChampion_keys_lower: list[str] = list(map(lambda x: x.lower(), list(TFTChampions.keys())))
                            if TFTChampionId in TFTChampions:
                                to_append = TFTChampions[TFTChampionId][key.split()[-1]]
                            elif TFTChampionId.lower() in set(map(lambda x: x.lower(), TFTChampions.keys())): #在获取艾欧尼亚对局序号为8390690410的英雄信息时，由于雷克塞的英雄序号大小写的原因，会引发键异常（KeyError is caused due to the case of "RekSai" string when the program is getting data from an Ionia match with matchId 8390690410）
                                TFTChampion_index: int = list(map(lambda x: x.lower(), TFTChampions.keys())).index(TFTChampionId.lower())
                                to_append = list(TFTChampions.values())[TFTChampion_index][key.split()[-1]]
                            else:
                                if not TFTChampionId in unmapped_keys["TFTCompanion"]:
                                    unmapped_keys["TFTCompanion"].add(TFTChampionId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）棋子信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT champion information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTChampionId, i, key, TFTChampionId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                                to_append = TFTChampionId if subkey_index == 3 else ""
                        else:
                            to_append = TFTPlayer_Units[unit_index][key.split()[-1]]
                    else:
                        to_append = ""
                else:
                    unit_index = (i - 201) // 9
                    item_index: int = (i - 201) // 3 % 3
                    subkey_index = (i - 201) % 3
                    if unit_index < len(TFTPlayer_Units): #很少有英雄单位可以有3个装备（Merely do champion units have full items）
                        if "itemNames" in TFTPlayer_Units[unit_index] and item_index < len(TFTPlayer_Units[unit_index]["itemNames"]):
                            TFTItemId: str = TFTPlayer_Units[unit_index]["itemNames"][item_index]
                            if subkey_index == 0:
                                to_append = TFTItemId
                            elif TFTItemId in TFTItems:
                                to_append = TFTItems[TFTItemId][key.split()[-1]]
                            elif TFTItemId in TFTAugments: #云顶之弈基础数据文件中存在部分云顶之弈装备数据文件中没有的装备（Some items are present in the TFT basic data file but absent from the TFT item data file）
                                item_basic_dict: dict[str, str] = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"} #云顶之弈装备数据文件和云顶之弈基础数据文件的格式不一致（The formats between TFT basic data and TFT item data are different）
                                to_append = TFTAugments[TFTItemId][item_basic_dict[key.split()[-1]]]
                            else:
                                if not TFTItemId in unmapped_keys["TFTItem"]:
                                    unmapped_keys["TFTItem"].add(TFTItemId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTItemId, i, key, TFTItemId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                                to_append = TFTItemId if subkey_index == 1 else ""
                        elif "items" in TFTPlayer_Units[unit_index] and item_index < len(TFTPlayer_Units[unit_index]["items"]): #在12.4版本之前，装备是通过序号而不是接口名称在LCU API中被存储的（Before Patch 12.4, items are stored via itemIDs instead of itemNames）
                            TFTItemId = TFTPlayer_Units[unit_index]["items"][item_index]
                            if subkey_index == 0:
                                to_append = TFTItemId
                            elif TFTItemId in TFTItems:
                                to_append = TFTItems[TFTItemId][key.split()[-1]]
                            elif TFTItemId in TFTAugments:
                                item_basic_dict = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"}
                                to_append = TFTAugments[TFTItemId][item_basic_dict[key.split()[-1]]]
                            else:
                                if not TFTItemId in unmapped_keys["TFTItem"]:
                                    unmapped_keys["TFTItem"].add(TFTItemId)
                                    logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTItemId, i, key, TFTItemId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                                to_append = TFTItemId if subkey_index == 1 else ""
                        else:
                            to_append = ""
                    else:
                        to_append = ""
            else:
                if i == 300 or i == 307:
                    to_append = int(TFTGame_summary["metadata"][key])
                elif i == 303: #所有玩家（`participants`）
                    to_append = json.dumps(TFTGame_summary["metadata"]["participants"])
                else:
                    to_append = TFTGame_summary["metadata"][key]
            TFTHistory_data[key].append(to_append)
    return TFTHistory_data

async def sort_TFTHistory(connection: Connection, TFTHistory: dict[str, Any], current_puuid: str | list[str], queues: dict[int, dict[str, Any]], TFTAugments: dict[str, dict[str, Any]], TFTChampions: dict[str, dict[str, Any]], TFTItems: dict[str, dict[str, Any]], TFTCompanions: dict[str, dict[str, Any]], TFTTraits: dict[str, dict[str, Any]], useAllVersions: bool = False, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[Any]]] = None, session: Optional[requests.Session] = None, useInfoDict: bool = False, infos: Optional[dict[str, dict[str, Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]: #云顶之弈对局记录包含全部信息，所以需要传入玩家通用唯一识别码来定位主召唤师（TFT match history contains all information, so puuid is needed to locate the main summoner）
    '''
    将云顶之弈对局记录整理成一张表格。<br>Organize TFT match history into a dataframe.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param TFTHistory: 云顶之弈对局记录。通过以下接口得到：<br>TFT match history, obtained by any of the following endpoints:
    
        - (LCU API) `GET /lol-match-history/v1/products/tft/{puuid}/matches?begin={begin}&count={count}`
        - (SGP API) `GET /match-history-query/v1/products/tft/player/{puuid}/SUMMARY?startIndex={startIndex}&count={count}`
        
        上述两个接口返回的内容完全相同。<br>The above two endpoints return completely the same result.
    :type TFTHistory: dict[str, Any]
    :param current_puuid: 主召唤师玩家通用唯一识别码。可以是单一值，也可以是一个列表。用于确定各对局中的主召唤师索引。<br>The main summoner's puuid. Both a single value and a list are supported. Used to determine the main player's indices in all matches.
    :type current_puuid: str | list[str]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param TFTAugments: 整理后的云顶之弈强化符文数据资源。键是强化符文代码，值是强化符文信息字典。<br>Organized TFT augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始云顶之弈强化符文数据资源可通过以下链接获取：<br>The raw TFT augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/cdragon/tft/en_us.json
    :type TFTAugments: dict[str, dict[str, Any]]
    :param TFTChampions: 整理后的云顶之弈英雄数据资源。键是英雄代码，值是英雄信息字典。<br>Organized TFT champion data resource. Each key is a championid, and each value is a champion information dictionary.
    
        原始云顶之弈英雄数据资源可通过以下链接获取：<br>The raw TFT champion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftchampions.json`
    :type TFTChampions: dict[str, dict[str, Any]]
    :param TFTItems: 整理后的云顶之弈装备信息。键是装备代码，值是装备信息字典。<br>Organized TFT item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始云顶之弈装备数据资源可通过以下链接获取：<br>The raw TFT item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftitems.json`
    :type TFTItems: dict[int, dict[str, Any]]
    :param TFTCompanions: 整理后的小小英雄信息。键是小小英雄代码，值是小小英雄信息字典。<br>Organized companion data resource. Each key is a companionId, and each value is a companion information dictionary.
    
        原始小小英雄数据资源可通过以下链接获取：<br>The raw companion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/companions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/companions.json`
    :type TFTCompanions: dict[str, dict[str, Any]]
    :param TFTTraits: 整理后的云顶之弈羁绊信息。键是羁绊代码，值是羁绊信息字典。<br>Organized TFT trait data resource. Each key is a traitId, and each value is a trait information dictionary.
    
        原始云顶之弈羁绊数据资源可通过以下链接获取：<br>The raw TFT trait data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tfttraits.json`
    :type TFTTraits: dict[str, dict[str, Any]]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param useInfoDict: 是否使用召唤师信息缓存字典。默认为否。<br>Whether to use a summoner information cache dictionary. False by default.
    :type useInfoDict: bool
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 云顶之弈对局记录数据框，以及游戏队列、云顶之弈基础数据、云顶之弈英雄、云顶之弈装备、小小英雄和云顶之弈羁绊等数据资源的缓存。<br>TFT match history dataframe and data resources like queues, TFT basic data, TFT champions, TFT items, companions and TFT traits.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if session == None:
        session = requests.Session()
    if infos == None:
        infos = {}
    if log == None:
        log = LogManager()
    if current_versions == None:
        current_versions = {"TFTAugment": "", "TFTChampion": "", "TFTItem": "", "TFTCompanion": "", "TFTTrait": ""}
    if unmapped_keys == None:
        unmapped_keys = {"TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    TFTHistoryList: list[dict[str, Any]] = TFTHistory["games"]
    version_re: re.Pattern[str] = re.compile(r"\d+\.\d+\.\d+\.\d+") #云顶之弈的对局版本信息是一串字符串，从中识别四位对局版本（TFT match version is a long string, from which the 4-number version is identified）
    TFT_main_player_indices: list[int] = [] #云顶之弈对局记录中记录了所有玩家的数据，但是在历史记录的工作表中只要显示主召唤师的数据，因此必须知道每场对局中主召唤师的索引（Each match in TFT history records all players' data, but only the main player's data are needed to display in the match history worksheet, so the index of the main player in each match is necessary）
    for game in TFTHistoryList:
        if game.get("json"):
            for i in range(len(game["json"]["participants"])):
                if game["json"]["participants"][i]["puuid"] in puuidList:
                    TFT_main_player_indices.append(i)
                    break
            else: #在美测服的对局序号为4420772721的对局中，不存在Volibear  PBE6玩家。这是极少见的情况，如果没有此处的判断，一旦发生这种情况，就会引起下标越界的错误（Player "Volibear  PBE6" is absent from a PBE match with matchId 4420772721, which is quite rare. Nevertheless, once it happens, an IndexError that list index out of range will be definitely thrown）
                TFT_main_player_indices.append(-1)
        else: #在艾欧尼亚的对局序号为8346130449的对局中，不存在玩家。这可能是因为系统维护的原因，所有人未正常进入对局，但是对局确实创建了（There doesn't exist any player in an HN1 match with matchId 8346130499. This may be due to system mainteinance, which causes all players to fail to start the game, even if the match itself has been created）
            TFT_main_player_indices.append(-1) #当主玩家索引为-1时，表示本场对局存在异常（Main player index being -1 represents an abnormal match）
    TFTHistory_header_keys: list[str] = list(TFTHistory_header.keys())
    TFTHistory_data: dict[str, list[Any]] = {key: [] for key in TFTHistory_header_keys} #云顶之弈对局概要各项目初始化（Initialize every feature / column of TFT match summary）
    for i in range(len(TFTHistoryList)): #由于不同对局意味着不同版本，不同版本的云顶之弈数据相差较大，所以为了使得一次获取的版本能够尽可能用到多个对局中，第一层迭代器应当是对局序号（Because different matches mean different patches, and TFT data differ greatly among different patches, to make a recently captured version of TFT data applicable in as more matches as possible, the first iterator should be the ID of the matches）
        TFTGame_summary: dict[str, Any] = TFTHistoryList[i]
        TFTGame_summary_json: dict[str, Any] = TFTGame_summary.get("json", {})
        participantIndex: int = TFT_main_player_indices[i]
        # if bool(TFTGame_summary_json):
        #     for j in range(len(TFTGame_summary_json["participants"])):
        #         if TFTGame_summary_json["participants"][j]["puuid"] == puuid:
        #             participantIndex = j
        #             break
        #     else:
        #         participantIndex = -1
        # else:
        #     participantIndex = -1
        if participantIndex != -1:
            TFTGameVersion: str = version_re.search(TFTGame_summary_json["game_version"]).group()
            TFTGamePatch: str = ".".join(TFTGameVersion.split(".")[:2]) #由于需要通过这部分代码事先获取所有对局的版本，因此无论如何，这部分代码都要放在与从CommunityDragon重新获取云顶之弈数据相关的代码前面（Since game patches are captured here, by all means should this part of code be in front of the code relevant to regetting TFT data from CommunityDragon）
            TFTPlayer: dict[str, Any] = TFTGame_summary_json["participants"][participantIndex]
            TFTPlayer_Traits: list[dict[str, Any]] = TFTPlayer["traits"]
            TFTPlayer_Units: list[dict[str, Any]] = TFTPlayer["units"]
            #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
            if useAllVersions:
                ##游戏模式（Game mode）
                queueIds_match_list: list[int] = [TFTGame_summary_json["queue_id"]]
                for j in queueIds_match_list:
                    if not j in queues and current_versions["queue"] != TFTGamePatch:
                        queuePatch_adopted: str = TFTGamePatch
                        queue_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, queue_recapture, queuePatch_adopted, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], queuePatch_adopted, queue_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                queue: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                queuePatch_deserted: str = queuePatch_adopted
                                queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                queue_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if queue_recapture < 3:
                                    queue_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                current_versions["queue"] = queuePatch_adopted
                                unmapped_keys["queue"].clear()
                                break
                        break
                ##云顶之弈强化符文（TFT augments）
                TFTAugmentIds_match_list: list[str] = sorted(set(TFTPlayer.get("augments", []))) #部分云顶之弈对局无强化符文（Some TFT matches don't contain augments）
                for j in TFTAugmentIds_match_list:
                    if not j in TFTAugments and current_versions["TFTAugment"] != TFTGamePatch:
                        TFTAugmentPatch_adopted: str = TFTGamePatch
                        TFTAugment_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nAugment information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT augments of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, TFTAugment_recapture, TFTAugmentPatch_adopted, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTBasic: dict[str, Any] = source.json()
                            except requests.exceptions.JSONDecodeError: #存在版本合并更新的情况（Situation like merged update exists）
                                TFTAugmentPatch_deserted: str = TFTAugmentPatch_adopted
                                TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                                TFTAugment_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                            except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                if TFTAugment_recapture < 3:
                                    TFTAugment_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                                TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                                current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                unmapped_keys["TFTAugment"].clear()
                                break
                        break
                ##云顶之弈小小英雄（TFT companions）
                TFTCompanionIds_match_list: list[str] = [TFTPlayer["companion"]["content_ID"]]
                for j in TFTCompanionIds_match_list:
                    if not j in TFTCompanions and current_versions["TFTCompanion"] != TFTGamePatch:
                        TFTCompanionPatch_adopted: str = TFTGamePatch
                        TFTCompanion_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）小小英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的小小英雄信息……\nTFT companion information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT companions of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, TFTCompanion_recapture, TFTCompanionPatch_adopted, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(TFTCompanionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTCompanion: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTCompanionPatch_deserted: str = TFTCompanionPatch_adopted
                                TFTCompanionPatch_adopted = FindPostPatch(Patch(TFTCompanionPatch_adopted), versionList)
                                TFTCompanion_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTCompanionPatch_deserted, TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_deserted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if TFTCompanion_recapture < 3:
                                    TFTCompanion_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的小小英雄信息……\nYour network environment is abnormal! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的小小英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the companion (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的小小英雄信息。\nTFT companion information changed to Patch %s." %(TFTCompanionPatch_adopted, TFTCompanionPatch_adopted), verbose = verbose)
                                TFTCompanions = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanion}
                                current_versions["TFTCompanion"] = TFTCompanionPatch_adopted
                                unmapped_keys["TFTCompanion"].clear()
                                break
                        break
                ##云顶之弈羁绊（TFT Traits）
                TFTTraitIds_match_list: list[str] = sorted(set(map(lambda x: x["name"], TFTPlayer_Traits)))
                for j in TFTTraitIds_match_list:
                    if not j in TFTTraits and current_versions["TFTTrait"] != TFTGamePatch:
                        TFTTraitPatch_adopted: str = TFTGamePatch
                        TFTTrait_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）羁绊信息（%s）获取失败！正在第%d次尝试改用%s版本的羁绊信息……\nTFT trait information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT traits of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, TFTTrait_recapture, TFTTraitPatch_adopted, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(TFTTraitPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTTrait: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTTraitPatch_deserted: str = TFTTraitPatch_adopted
                                TFTTraitPatch_adopted = FindPostPatch(Patch(TFTTraitPatch_adopted), versionList)
                                TFTTrait_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTraitPatch_deserted, TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_deserted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if TFTTrait_recapture < 3:
                                    TFTTrait_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的羁绊信息……\nYour network environment is abnormal! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的羁绊信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the trait (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的羁绊信息。\nTFT trait information changed to Patch %s." %(TFTTraitPatch_adopted, TFTTraitPatch_adopted), verbose = verbose)
                                TFTTraits = {}
                                for trait_iter in TFTTrait:
                                    trait_id: str = trait_iter["trait_id"]
                                    conditional_trait_sets = {}
                                    if "conditional_trait_sets" in trait_iter: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
                                        for conditional_trait_set in trait_iter["conditional_trait_sets"]:
                                            style_idx: str = conditional_trait_set["style_idx"]
                                            conditional_trait_sets[style_idx] = conditional_trait_set
                                    trait_iter["conditional_trait_sets"] = conditional_trait_sets
                                    TFTTraits[trait_id] = trait_iter
                                current_versions["TFTTrait"] = TFTTraitPatch_adopted
                                unmapped_keys["TFTTrait"].clear()
                                break
                        break
                ##云顶之弈英雄（TFT champions）
                TFTChampionIds_match_list: list[str] = sorted(set(map(lambda x: x["character_id"], TFTPlayer_Units)))
                for j in TFTChampionIds_match_list:
                    if not j in TFTChampions and not j.lower() in set(map(lambda x: x.lower(), TFTChampions.keys())) and current_versions["TFTChampion"] != TFTGamePatch:
                        TFTChampionPatch_adopted: str = TFTGamePatch
                        TFTChampion_recapture: int = 1
                        logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的棋子信息……\nTFT champion (%s) information of Match %d / %d (matchId: %d) capture failed! Changing to TFT champions of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, TFTChampion_recapture, TFTChampionPatch_adopted, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(TFTChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTChampion: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTChampionPatch_deserted: str = TFTChampionPatch_adopted
                                TFTChampionPatch_adopted = FindPostPatch(Patch(TFTChampionPatch_adopted), versionList)
                                TFTChampion_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampionPatch_deserted, TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_deserted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if TFTChampion_recapture < 3:
                                    TFTChampion_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的棋子信息……\nYour network environment is abnormal! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）将采用原始数据！\nNetwork error! The original data will be used for Match %d / %d (matchId: %d)!" %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的棋子信息。\nTFT champion information changed to Patch %s." %(TFTChampionPatch_adopted, TFTChampionPatch_adopted), verbose = verbose)
                                TFTChampions = {}
                                if Patch(TFTChampionPatch_adopted) < Patch("13.17"): #从13.17版本开始，CommunityDragon数据库中关于云顶之弈棋子的数据格式发生微调（Since Patch 13.17, the format of TFT Champion data in CommunityDragon database has been modified）
                                    for TFTChampion_iter in TFTChampion:
                                        champion_name: str = TFTChampion_iter["character_id"]
                                        TFTChampions[champion_name] = TFTChampion_iter
                                else:
                                    for TFTChampion_iter in TFTChampion:
                                        champion_name = TFTChampion_iter["name"]
                                        TFTChampions[champion_name] = TFTChampion_iter["character_record"] #请注意该语句与4行之前的语句的差异，并看看一开始准备数据文件时使用的是哪一种——其实你应该猜的出来（Have you noticed the difference between this statement and the statement that is 4 lines above from this statement? Also, check which statement I chose for the beginning, when I prepared the data resources. Actually, you should be able to speculate it without referring to the code）
                                current_versions["TFTChampion"] = TFTChampionPatch_adopted
                                unmapped_keys["TFTChampion"].clear()
                                break
                        break
                ##云顶之弈装备（TFT items）
                s: set[str] = set()
                for unit in TFTPlayer_Units:
                    if "itemNames" in unit:
                        s |= set(unit["itemNames"])
                    elif "items" in unit:
                        s |= set(unit["items"])
                    else:
                        s |= set()
                TFTItemIds_match_list: list[str] = sorted(s)
                for j in TFTItemIds_match_list:
                    if not j in TFTItems and not j in TFTAugments:
                        if current_versions["TFTItem"] != TFTGamePatch:
                            TFTItemPatch_adopted: str = TFTGamePatch
                            TFTItem_recapture: int = 1
                            logPrint("第%d/%d场对局（对局序号：%d）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT items of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, TFTItem_recapture, TFTItemPatch_adopted, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    TFTItem: list[dict[str, Any]] = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    TFTItemPatch_deserted: str = TFTItemPatch_adopted
                                    TFTItemPatch_adopted = FindPostPatch(Patch(TFTItemPatch_adopted), versionList)
                                    TFTItem_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                except requests.exceptions.RequestException:
                                    if TFTItem_recapture < 3:
                                        TFTItem_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的装备信息（%d）将采用原始数据！\nNetwork error! The original data will be used for the item (%d) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"]), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的云顶之弈装备信息。\nTFT item information changed to Patch %s." %(TFTItemPatch_adopted, TFTItemPatch_adopted), verbose = verbose)
                                    TFTItems = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItem}
                                    current_versions["TFTItem"] = TFTItemPatch_adopted
                                    unmapped_keys["TFTItem"].clear()
                                    break
                        #由于云顶之弈基础数据中也包含装备信息，这里将重新获取对局版本的云顶之弈基础数据（Because TFT basic data contain item data, here the program recaptures TFT basic data of the match version）
                        if current_versions["TFTAugment"] != TFTGamePatch:
                            TFTAugmentPatch_adopted = TFTGamePatch
                            TFTAugment_recapture = 1
                            while True:
                                try:
                                    source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                    TFTBasic = source.json()
                                except requests.exceptions.JSONDecodeError:
                                    TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                    TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                                    TFTAugment_recapture = 1
                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                    if TFTAugment_recapture < 3:
                                        TFTAugment_recapture += 1
                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                    else:
                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchId: %d)!" %(i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"], j, j, i + 1, len(TFTHistoryList), TFTGame_summary_json["game_id"]), verbose = verbose)
                                        break
                                else:
                                    logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                                    TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                                    current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                    unmapped_keys["TFTAugment"].clear()
                                    break
                        break
        await generate_TFTHistory_records(connection, TFTHistory_data, TFTGame_summary, participantIndex, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = i + 1, unmapped_keys = unmapped_keys, useInfoDict = useInfoDict, infos = infos, log = log, verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    TFTHistory_statistics_output_order: list[int] = [0, 46, 47, 5, 14, 15, 16, 6, 10, 18, 8, 17, 7, 13, 12, 11, 306, 304, 40, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 149, 147, 148, 202, 205, 208, 154, 152, 153, 211, 214, 217, 159, 157, 158, 220, 223, 226, 164, 162, 163, 229, 232, 235, 169, 167, 168, 238, 241, 244, 174, 172, 173, 247, 250, 253, 179, 177, 178, 256, 259, 262, 184, 182, 183, 265, 268, 271, 189, 187, 188, 274, 277, 280, 194, 192, 193, 283, 286, 289, 199, 197, 198, 292, 295, 298, 60, 56, 57, 58, 59, 67, 63, 64, 65, 66, 74, 70, 71, 72, 73, 81, 77, 78, 79, 80, 88, 84, 85, 86, 87, 95, 91, 92, 93, 94, 102, 98, 99, 100, 101, 109, 105, 106, 107, 108, 116, 112, 113, 114, 115, 123, 119, 120, 121, 122, 130, 126, 127, 128, 129, 137, 133, 134, 135, 136, 144, 140, 141, 142, 143]
    TFTHistory_data_organized: dict[str, list[Any]] = {TFTHistory_header_keys[i]: TFTHistory_data[TFTHistory_header_keys[i]] for i in TFTHistory_statistics_output_order}
    TFTHistory_df: pandas.DataFrame = pandas.DataFrame(data = TFTHistory_data_organized)
    optimize_bool_display(TFTHistory_df)
    TFTHistory_df = pandas.concat([pandas.DataFrame([TFTHistory_header])[TFTHistory_df.columns], TFTHistory_df], ignore_index = True)
    return (TFTHistory_df, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits)

async def generate_TFTGameSummary_records(connection: Connection, TFTGame_summary_data: dict[str, list[Any]], TFTGame_summary: dict[str, Any], participantIndex: int, queues: dict[int, dict[str, Any]], TFTAugments: dict[str, dict[str, Any]], TFTChampions: dict[str, dict[str, Any]], TFTItems: dict[str, dict[str, Any]], TFTCompanions: dict[str, dict[str, Any]], TFTTraits: dict[str, dict[str, Any]], gameIndex: int = 1, current_puuid: str | list[str] = "", unmapped_keys: Optional[dict[str, set[Any]]] = None, useInfoDict: bool = False, infos: Optional[dict[str, dict[str, Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> dict[str, list[Any]]: #这里传入的玩家通用唯一识别码参数仅用于辨别双人作战模式中的队友（Here the puuid parameter is only used to distinguish the ally from others in Double Up mode）
    '''
    向云顶之弈对局概要数据中追加记录。<br>Append records to TFT match summary data.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param TFTGame_summary_data: 云顶之弈对局概要数据。记录将追加到其中。<br>LoL match summary data. Records are appended into it.
    :type TFTGame_summary_data: dict[str, list[Any]]
    :param TFTGame_summary: 云顶之弈对局概要。通过以下SGP接口得到：<br>TFT match summary, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/tft/{match_id}/SUMMARY`
    :type TFTGame_summary: dict[str, Any]
    :param participantIndex: 主召唤师索引。从0开始。<br>The index of the main summoner, which starts from 0.
    :type participantIndex: int
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param TFTAugments: 整理后的云顶之弈强化符文数据资源。键是强化符文代码，值是强化符文信息字典。<br>Organized TFT augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始云顶之弈强化符文数据资源可通过以下链接获取：<br>The raw TFT augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/cdragon/tft/en_us.json
    :type TFTAugments: dict[str, dict[str, Any]]
    :param TFTChampions: 整理后的云顶之弈英雄数据资源。键是英雄代码，值是英雄信息字典。<br>Organized TFT champion data resource. Each key is a championid, and each value is a champion information dictionary.
    
        原始云顶之弈英雄数据资源可通过以下链接获取：<br>The raw TFT champion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftchampions.json`
    :type TFTChampions: dict[str, dict[str, Any]]
    :param TFTItems: 整理后的云顶之弈装备信息。键是装备代码，值是装备信息字典。<br>Organized TFT item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始云顶之弈装备数据资源可通过以下链接获取：<br>The raw TFT item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftitems.json`
    :type TFTItems: dict[int, dict[str, Any]]
    :param TFTCompanions: 整理后的小小英雄信息。键是小小英雄代码，值是小小英雄信息字典。<br>Organized companion data resource. Each key is a companionId, and each value is a companion information dictionary.
    
        原始小小英雄数据资源可通过以下链接获取：<br>The raw companion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/companions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/companions.json`
    :type TFTCompanions: dict[str, dict[str, Any]]
    :param TFTTraits: 整理后的云顶之弈羁绊信息。键是羁绊代码，值是羁绊信息字典。<br>Organized TFT trait data resource. Each key is a traitId, and each value is a trait information dictionary.
    
        原始云顶之弈羁绊数据资源可通过以下链接获取：<br>The raw TFT trait data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tfttraits.json`
    :type TFTTraits: dict[str, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param current_puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type current_puuid: str | list[str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param useInfoDict: 是否使用召唤师信息缓存字典。默认为否。<br>Whether to use a summoner information cache dictionary. False by default.
    :type useInfoDict: bool
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 追加数据后的云顶之弈对局概要数据。<br>TFT match summary data after appending.
    :rtype: dict[str, list[Any]]
    '''
    #参数预处理（Parameter pre-processing）
    if unmapped_keys == None:
        unmapped_keys = {"queue": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
    if infos == None:
        infos = {}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    version_re: re.Pattern[str] = re.compile(r"\d+\.\d+\.\d+\.\d+")
    TFTGame_summary_json: dict[str, Any] = TFTGame_summary["json"] #在调用此函数之前，已经对对局概要进行过筛选了（Before this function called, match summaries are already filtered）
    TFTGameVersion: str = version_re.search(TFTGame_summary_json["game_version"]).group()
    TFTPlayer: dict[str, Any] = TFTGame_summary_json["participants"][participantIndex]
    TFTPlayer_Traits: list[dict[str, Any]] = TFTPlayer["traits"]
    TFTPlayer_Units: list[dict[str, Any]] = TFTPlayer["units"]
    current_participant_found: bool = False
    current_participant: dict[str, Any] = TFTGame_summary_json["participants"][0]
    for participant in TFTGame_summary_json["participants"]:
        for puuid in puuidList:
            if participant["puuid"] == puuid:
                current_participant = participant
                current_participant_found = True
                break
        if current_participant_found:
            break
    TFTPlayer_info_got: bool = False
    TFTPlayer_info_body: dict[str, Any] = {}
    if TFTPlayer["puuid"] != BOT_UUID:
        if "riotIdGameName" in TFTPlayer and "riotIdTagline" in TFTPlayer:
            TFTPlayer_summonerName: str = "%s#%s" %(TFTPlayer["riotIdGameName"], TFTPlayer["riotIdTagline"])
        else:
            if useInfoDict and TFTPlayer["puuid"] in infos:
                TFTPlayer_info_body: dict[str, Any] = infos[TFTPlayer["puuid"]]
                TFTPlayer_summonerName = get_info_name(TFTPlayer_info_body)
                TFTPlayer_info_got = True
            else:
                TFTPlayer_info_recapture: int = 0
                TFTPlayer_info: dict[str, Any] = await get_info(connection, TFTPlayer["puuid"])
                while not TFTPlayer_info["info_got"] and TFTPlayer_info["body"]["httpStatus"] != 404 and TFTPlayer_info_recapture < 3:
                    logPrint(TFTPlayer_info["message"], verbose = verbose)
                    TFTPlayer_info_recapture += 1
                    logPrint("对局%d玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) in Match %d capture failed! Recapturing this player's information ... Times tried: %d." %(TFTGame_summary_json["game_id"], TFTPlayer["puuid"], TFTPlayer_info_recapture, TFTPlayer["puuid"], TFTGame_summary_json["game_id"], TFTPlayer_info_recapture), verbose = verbose)
                    TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                if TFTPlayer_info["info_got"]:
                    TFTPlayer_info_body = TFTPlayer_info["body"]
                    if useInfoDict:
                        infos[TFTPlayer["puuid"]] = TFTPlayer_info_body
                    TFTPlayer_summonerName = get_info_name(TFTPlayer_info_body)
                else:
                    logPrint(TFTPlayer_info["message"], verbose = verbose)
                    logPrint("对局%d玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) in Match %d capture failed!" %(TFTGame_summary_json["game_id"], TFTPlayer["puuid"], TFTPlayer["puuid"], TFTGame_summary_json["game_id"]), verbose = verbose)
                TFTPlayer_info_got = TFTPlayer_info["info_got"]
    #数据整理核心部分（Data organization core part）
    TFTGame_summary_header_keys: list[str] = list(TFTGame_summary_header.keys())
    for i in range(len(TFTGame_summary_header_keys)):
        key: str = TFTGame_summary_header_keys[i]
        if i == 0: #游戏序号（`gameIndex`）
            to_append: Any = gameIndex
        elif i <= 18:
            if i == 1: #对局终止情况（`endOfGameResult`）
                to_append = endOfGameResults[TFTGame_summary_json["endOfGameResult"]] if "endOfGameResult" in TFTGame_summary_json else ""
            elif i in {2, 3, 8, 9}:
                to_append = TFTGame_summary_json.get(key, "") #14.6版本之前的云顶之弈对局信息中没有这些键（Those keys don't exist in information of TFT matches before Patch 14.6）
            elif i == 7: #对局版本（`game_version`）
                to_append = TFTGameVersion
            elif i == 12: #数据版本名称（`tft_set_core_name`）
                to_append = TFTGame_summary_json.get("tft_set_core_name", "") #在云顶之弈第7赛季之前，TFTGame_summary_json中无tft_set_core_name这一键（Before TFTSet7, tft_set_core_name isn't present as a key of `TFTGame_summary_json`）
            elif i == 14: #对局创建时间（`gameCreationDate`）
                to_append = getISOTime(TFTGame_summary_json["gameCreation"] / 1000) if "gameCreation" in TFTGame_summary_json else ""
            elif i == 15: #对局结算时间（`gameDate`）
                to_append = getISOTime(int(TFTGame_summary_json["game_datetime"]) / 1000)
            elif i == 16: #持续时长（`gameLength`）
                to_append = lcuTime(TFTGame_summary_json["game_length"])
            elif i == 17: #地图名称（`mapName`）
                to_append = gamemaps[TFTGame_summary_json["mapId"]]["zh_CN"] if "mapId" in TFTGame_summary_json else ""
            elif i == 18: #游戏模式名称（`gameModeName`）
                to_append = queues[TFTGame_summary_json["queue_id"]]["description"] if TFTGame_summary_json["queue_id"] in queues else ""
            else:
                to_append = TFTGame_summary_json[key]
        elif i <= 55:
            if i == 19: #玩家序号（`participantId`）
                to_append = participantIndex + 1
            elif i >= 20 and i <= 28: #强化符文相关键（Augment-related keys）
                if "augments" in TFTPlayer:
                    augment_index: int = (i - 20) % 3
                    subkey_index: int = (i - 20) // 3
                    if augment_index < len(TFTPlayer["augments"]):
                        TFTAugmentId: str = TFTPlayer["augments"][augment_index]
                        if subkey_index == 0:
                            to_append = TFTAugmentId
                        elif TFTAugmentId in TFTAugments:
                            to_append = TFTAugments[TFTAugmentId][key.split()[-1]]
                        else:
                            if not TFTAugmentId in unmapped_keys["TFTAugment"]:
                                unmapped_keys["TFTAugment"].add(TFTAugmentId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）强化符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT augment information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTAugmentId, i, key, TFTAugmentId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                            to_append = TFTAugmentId if subkey_index == 1 else ""
                    else:
                        to_append = ""
                else:
                    to_append = "" #云顶之弈刚出的时候，没有强化符文的概念（The concept of "augment" didn't appear at the beginning of TFT）
            elif i >= 29 and i <= 35: #小小英雄相关键（Companion-related keys）
                TFTCompanionId: str = TFTPlayer["companion"]["content_ID"]
                if i <= 32:
                    to_append = TFTPlayer["companion"][key.split()[-1]]
                elif TFTCompanionId in TFTCompanions:
                    to_append = TFTCompanions[TFTCompanionId][key.split()[-1]] if i <= 34 else rarities[TFTCompanions[TFTCompanionId][key.split()[-1]]]
                else:
                    if not TFTCompanionId in unmapped_keys["TFTCompanion"]:
                        unmapped_keys["TFTCompanion"].add(TFTCompanionId)
                        logPrint("【%d. %s】对局%d（对局版本：%s）小小英雄信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT companion information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTCompanionId, i, key, TFTCompanionId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                    to_append = TFTCompanionId if i == 33 else ""
            elif i == 45: #通关人机对战（`pve_wonrun`）
                to_append = "" if not "pve_wonrun" in TFTPlayer else "√" if TFTPlayer["pve_wonrun"] else "×"
            elif i == 46 or i == 47: #玩家名称和名称编号（`riotIdGameName` and `riotIdTagline`）
                if key in TFTPlayer:
                    to_append = TFTPlayer[key]
                else:
                    if TFTPlayer["puuid"] in infos:
                        TFTPlayer_info_body = infos[TFTPlayer["puuid"]]
                        to_append = TFTPlayer_info_body["gameName"] if i == 46 else TFTPlayer_info_body["tagLine"]
                    else:
                        if TFTPlayer["puuid"] != BOT_UUID and TFTPlayer_info_got:
                            to_append = TFTPlayer_info_body["gameName"] if i == 46 else TFTPlayer_info_body["tagLine"]
                        else:
                            to_append = ""
            elif i == 51: #胜利（`win`）
                to_append = TFTPlayer.get("win", False)
            elif i == 52: #存活回合（`last_round_format`）
                lastRound: int = TFTPlayer["last_round"]
                if lastRound <= 3:
                    bigRound: int = 1
                    smallRound: int = lastRound
                else:
                    bigRound = (lastRound + 3) // 7 + 1
                    smallRound = (lastRound + 3) % 7 + 1
                to_append = "%d-%d" %(bigRound, smallRound)
            elif i == 53: #存活时长（`time_eliminated_norm`）
                to_append = lcuTime(TFTPlayer["time_eliminated"])
            elif i == 54: #结果（`result`）
                to_append = "" if not "win" in TFTPlayer else "胜利" if TFTPlayer["win"] else "失败"
                if "endOfGameResult" in TFTGame_summary_json and TFTGame_summary_json["endOfGameResult"] == "Abort_AntiCheatExit":
                    to_append = "被终止"
            elif i == 55: #是否队友（`isAlly`）
                to_append = current_participant_found and "partner_group_id" in TFTPlayer and TFTPlayer["partner_group_id"] == current_participant["partner_group_id"]
            else:
                to_append = TFTPlayer.get(key, "")
        elif i <= 146: #云顶之弈羁绊相关键（TFT trait-related keys）
            trait_index: int = (i - 56) // 7
            subkey_index = (i - 56) % 7
            if trait_index < len(TFTPlayer_Traits): #在这个小于的问题上纠结了很久[敲打]——下标是从0开始的。假设API上记录了n个羁绊，那么当程序正在获取第n个羁绊时，就会引起下标越界的问题。所以这里不能使用小于等于号（I stuck at this less than sign for too long xD - note that the index begins from 0. Suppose there're totally n traits recorded in LCU API. Then, when the program is trying to capture the n-th trait, it'll throw an IndexError. That's why the "less than or equal to" sign can't be used here）
                TFTTrait_iter: dict[str, Any] = TFTPlayer_Traits[trait_index]
                TFTTraitId: str = TFTTrait_iter["name"]
                if TFTTraitId == "TemplateTrait": #CommunityDragon数据库中没有收录模板羁绊的数据（Data about TemplateTrait aren't archived in CommunityDragon database）
                    if subkey_index == 4 and TFTPlayer["puuid"] != BOT_UUID: #在艾欧尼亚的对局序号为4959597974的对局中，存在一个模板羁绊，没有tier_total这个键（There exists a TemplateTrait without the key `tier_total` in an Ionia match with matchId 4959597974）
                        if "riotIdGameName" in TFTPlayer and "riotIdTagline" in TFTPlayer or TFTPlayer_info_got:
                            logPrint("警告：对局%d中玩家%s（玩家通用唯一识别码：%s）的第%d个羁绊是模板羁绊！\nWarning: Trait No. %d of the player %s (puuid: %s) in the match %d is TemplateTrait." %(TFTGame_summary_json["game_id"], TFTPlayer_summonerName, TFTPlayer["puuid"], trait_index + 1, trait_index + 1, TFTPlayer_summonerName, TFTPlayer["puuid"], TFTGame_summary_json["game_id"]), verbose = verbose)
                        to_append = ""
                    else:
                        to_append = TFTTraitId if subkey_index == 5 else "" if subkey_index == 6 else TFTTrait_iter[key.split()[-1]]
                else:
                    if subkey_index <= 4:
                        if subkey_index == 2:
                            to_append = traitStyles[TFTTrait_iter[key.split()[-1]]]
                        else:
                            to_append = TFTTrait_iter[key.split()[-1]]
                    elif TFTTraitId in TFTTraits:
                        to_append = TFTTraits[TFTTraitId][key.split()[-1]]
                    else:
                        if not TFTTraitId in unmapped_keys["TFTTrait"]:
                            unmapped_keys["TFTTrait"].add(TFTTraitId)
                            logPrint("【%d. %s】对局%d（对局版本：%s）羁绊信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT trait information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTTraitId, i, key, TFTTraitId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                        to_append = TFTTraitId if subkey_index == 5 else ""
            else:
                to_append = ""
        elif i <= 300:
            if i <= 201: #云顶之弈英雄相关键（TFT champion-related keys）
                unit_index: int = (i - 147) // 5
                subkey_index = (i - 147) % 5
                if unit_index < len(TFTPlayer_Units):
                    TFTChampion_iter: dict[str, Any] = TFTPlayer_Units[unit_index]
                    TFTChampionId = TFTChampion_iter["character_id"]
                    if subkey_index >= 3:
                        #character_id_lower = TFTPlayer_Units[unit_index]["character_id"].lower()
                        #TFTChampion_keys_lower = list(map(lambda x: x.lower(), list(TFTChampions.keys())))
                        if TFTChampionId in TFTChampions:
                            to_append = TFTChampions[TFTChampionId][key.split()[-1]]
                        elif TFTChampionId.lower() in set(map(lambda x: x.lower(), TFTChampions.keys())): #在获取艾欧尼亚对局序号为8390690410的英雄信息时，由于雷克塞的英雄序号大小写的原因，会引发键异常（KeyError is caused due to the case of "RekSai" string when the program is getting data from an Ionia match with matchId 8390690410）
                            TFTChampion_index: int = list(map(lambda x: x.lower(), TFTChampions.keys())).index(TFTChampionId.lower())
                            to_append = list(TFTChampions.values())[TFTChampion_index][key.split()[-1]]
                        else:
                            if not TFTChampionId in unmapped_keys["TFTCompanion"]:
                                unmapped_keys["TFTCompanion"].add(TFTChampionId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）棋子信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT champion information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTChampionId, i, key, TFTChampionId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                            to_append = TFTChampionId if subkey_index == 3 else ""
                    else:
                        to_append = TFTPlayer_Units[unit_index][key.split()[-1]]
                else:
                    to_append = ""
            else:
                unit_index = (i - 202) // 9
                item_index = (i - 202) // 3 % 3
                subkey_index = (i - 202) % 3
                if unit_index < len(TFTPlayer_Units): #很少有英雄单位可以有3个装备（Merely do champion units have full items）
                    if "itemNames" in TFTPlayer_Units[unit_index] and item_index < len(TFTPlayer_Units[unit_index]["itemNames"]):
                        TFTItemId = TFTPlayer_Units[unit_index]["itemNames"][item_index]
                        if subkey_index == 0:
                            to_append = TFTItemId
                        elif TFTItemId in TFTItems:
                            to_append = TFTItems[TFTItemId][key.split()[-1]]
                        elif TFTItemId in TFTAugments: #云顶之弈基础数据文件中存在部分云顶之弈装备数据文件中没有的装备（Some items are present in the TFT basic data file but absent from the TFT item data file）
                            item_basic_dict: dict[str, str] = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"} #云顶之弈装备数据文件和云顶之弈基础数据文件的格式不一致（The formats between TFT basic data and TFT item data are different）
                            to_append = TFTAugments[TFTItemId][item_basic_dict[key.split()[-1]]]
                        else:
                            if not TFTItemId in unmapped_keys["TFTItem"]:
                                unmapped_keys["TFTItem"].add(TFTItemId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTItemId, i, key, TFTItemId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                            to_append = TFTItemId if subkey_index == 1 else ""
                    elif "items" in TFTPlayer_Units[unit_index] and item_index < len(TFTPlayer_Units[unit_index]["items"]): #在12.4版本之前，装备是通过序号而不是接口名称在LCU API中被存储的（Before Patch 12.4, items are stored via itemIDs instead of itemNames）
                        TFTItemId = TFTPlayer_Units[unit_index]["items"][item_index]
                        if subkey_index == 0:
                            to_append = TFTItemId
                        elif TFTItemId in TFTItems:
                            to_append = TFTItems[TFTItemId][key.split()[-1]]
                        elif TFTItemId in TFTAugments:
                            item_basic_dict = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"}
                            to_append = TFTAugments[TFTItemId][item_basic_dict[key.split()[-1]]]
                        else:
                            if not TFTItemId in unmapped_keys["TFTItem"]:
                                unmapped_keys["TFTItem"].add(TFTItemId)
                                logPrint("【%d. %s】对局%d（对局版本：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d (gameVersion: %s) capture failed! The original data will be used for this match!" %(i, key, TFTGame_summary_json["game_id"], TFTGameVersion, TFTItemId, i, key, TFTItemId, TFTGame_summary_json["game_id"], TFTGameVersion), verbose = verbose)
                            to_append = TFTItemId if subkey_index == 1 else ""
                    else:
                        to_append = ""
                else:
                    to_append = ""
        else:
            if i == 301 or i == 308:
                to_append = int(TFTGame_summary["metadata"][key])
            elif i == 304: #所有玩家（`participants`）
                to_append = json.dumps(TFTGame_summary["metadata"]["participants"])
            else:
                to_append = TFTGame_summary["metadata"][key]
        TFTGame_summary_data[key].append(to_append)
    return TFTGame_summary_data

async def sort_TFTGame_summary(connection: Connection, TFTGame_summary: dict[str, Any], queues: dict[int, dict[str, Any]], TFTAugments: dict[str, dict[str, Any]], TFTChampions: dict[str, dict[str, Any]], TFTItems: dict[str, dict[str, Any]], TFTCompanions: dict[str, dict[str, Any]], TFTTraits: dict[str, dict[str, Any]], gameIndex: int = 1, current_puuid: str | list[str] = "", useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[Any]]] = None, session: Optional[requests.Session] = None, useInfoDict: bool = False, infos: Optional[dict[str, dict[str, Any]]] = None, sortStats: bool = False, TFTGame_stat_data: Optional[dict[str, list[Any]]] = None, save_self: bool = True, save_other: bool = True, save_bot: bool = False, log: Optional[LogManager] = None, verbose: bool = True) -> tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]: #本函数体中涉及召唤师信息的获取，因此需要定义为协程（This function body involves getting summoner information, so this function is defined as an async function）
    '''
    将云顶之弈对局概要中的玩家信息整理成一张表格。<br>Organize player information in a TFT match summary into a dataframe.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param TFTGame_summary: 云顶之弈对局概要。通过以下SGP接口得到：<br>TFT match summary, obtained through the following SGP endpoint:
    
        - `GET /match-history-query/v1/products/tft/{match_id}/SUMMARY`
    :type TFTGame_summary: dict[str, Any]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param TFTAugments: 整理后的云顶之弈强化符文数据资源。键是强化符文代码，值是强化符文信息字典。<br>Organized TFT augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始云顶之弈强化符文数据资源可通过以下链接获取：<br>The raw TFT augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/cdragon/tft/en_us.json
    :type TFTAugments: dict[str, dict[str, Any]]
    :param TFTChampions: 整理后的云顶之弈英雄数据资源。键是英雄代码，值是英雄信息字典。<br>Organized TFT champion data resource. Each key is a championid, and each value is a champion information dictionary.
    
        原始云顶之弈英雄数据资源可通过以下链接获取：<br>The raw TFT champion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftchampions.json`
    :type TFTChampions: dict[str, dict[str, Any]]
    :param TFTItems: 整理后的云顶之弈装备信息。键是装备代码，值是装备信息字典。<br>Organized TFT item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始云顶之弈装备数据资源可通过以下链接获取：<br>The raw TFT item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftitems.json`
    :type TFTItems: dict[int, dict[str, Any]]
    :param TFTCompanions: 整理后的小小英雄信息。键是小小英雄代码，值是小小英雄信息字典。<br>Organized companion data resource. Each key is a companionId, and each value is a companion information dictionary.
    
        原始小小英雄数据资源可通过以下链接获取：<br>The raw companion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/companions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/companions.json`
    :type TFTCompanions: dict[str, dict[str, Any]]
    :param TFTTraits: 整理后的云顶之弈羁绊信息。键是羁绊代码，值是羁绊信息字典。<br>Organized TFT trait data resource. Each key is a traitId, and each value is a trait information dictionary.
    
        原始云顶之弈羁绊数据资源可通过以下链接获取：<br>The raw TFT trait data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tfttraits.json`
    :type TFTTraits: dict[str, dict[str, Any]]
    :param gameIndex: 对局的下标。“序号”列追加此参数。默认为1。<br>Subscript of the match. Appended to the "index" column. 1 by default.
    :type gameIndex: int
    :param current_puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type current_puuid: str | list[str]
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param useInfoDict: 是否使用召唤师信息缓存字典。默认为否。<br>Whether to use a summoner information cache dictionary. False by default.
    :type useInfoDict: bool
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :param sortStats: 是否在整理对局概要数据的同时整理玩家战绩数据。默认为假。<br>Whether to organize player stats data while organizing the match summary data. False by default.
    :type sortStats: bool
    :param TFTGame_stat_data: 玩家战绩数据。相比对局概要数据，添加了对局元数据信息。<br>Player stat data, which additionally organize the match metadata compared with match summary.
    :type TFTGame_stat_data: dict[str, list[Any]]
    :param save_self: 在汇总玩家战绩时，是否保存主召唤师的数据。默认为真。<br>Whether to save the data of the main summoner when the program is summarizing player stats. True by default.
    :type save_self: bool
    :param save_other: 在汇总玩家战绩时，是否保存主召唤师以外的玩家数据。默认为真。<br>Whether to save the data of players except the main summoner when the program is summarizing player stats. True by default.
    :type save_other: bool
    :param save_bot: 在汇总玩家战绩时，是否保存电脑玩家的数据。默认为假。<br>Whether to save the data of bot players when the program is summarizing player stats. False by default.
    :type save_bot: bool
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 云顶之弈对局概要数据框，以及游戏队列、云顶之弈基础数据、云顶之弈英雄、云顶之弈装备、小小英雄和云顶之弈羁绊等数据资源的缓存。<br>TFT match summary dataframe, and data resources like queues, TFT basic data, TFT champions, TFT items, companions and TFT traits.
    :rtype: tuple[pandas.DataFrame, dict[int, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"TFTAugment": "", "TFTChampion": "", "TFTItem": "", "TFTCompanion": "", "TFTTrait": ""}
    if unmapped_keys == None:
        unmapped_keys = {"TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
    if session == None:
        session = requests.Session()
    if infos == None:
        infos = {}
    if TFTGame_stat_data == None:
        TFTGame_stat_data = {}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    puuidList: list[str] = [current_puuid] if isinstance(current_puuid, str) else current_puuid
    version_re: re.Pattern[str] = re.compile(r"\d+\.\d+\.\d+\.\d+")
    TFTGame_summary_header_keys: list[str] = list(TFTGame_summary_header.keys())
    TFTGame_summary_data: dict[str, list[Any]] = {key: [] for key in TFTGame_summary_header} #云顶之弈没有独立的LCU API以供查询对局概要。这里将每场对局的与玩家有关的数据视为对局概要（There's not any available LCU API for TFT match summary query. Here any information relevant to participants is regarded as TFT game summary）
    if TFTGame_summary.get("json"): #该条件等价于（This condition is equivalent to）：`TFT_main_player_indices[i] == -1`
        TFTGame_summary_json: dict[str, Any] = TFTGame_summary["json"]
        TFTGameVersion: str = version_re.search(TFTGame_summary_json["game_version"]).group()
        TFTGamePatch: str = ".".join(TFTGameVersion.split(".")[:2]) #由于需要通过这部分代码事先获取所有对局的版本，因此无论如何，这部分代码都要放在与从CommunityDragon重新获取云顶之弈数据相关的代码前面（Since game patches are captured here, by all means should this part of code be in front of the code relevant to regetting TFT data from CommunityDragon）
        #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
        if useAllVersions:
            ##游戏模式（Game mode）
            queueIds_match_list: list[int] = [TFTGame_summary_json["queue_id"]]
            for i in queueIds_match_list:
                if not i in queues and current_versions["queue"] != TFTGamePatch:
                    queuePatch_adopted: str = TFTGamePatch
                    queue_recapture: int = 1
                    logPrint("对局%d游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(TFTGame_summary_json["game_id"], i, queue_recapture, queuePatch_adopted, i, TFTGame_summary_json["game_id"], queuePatch_adopted, queue_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                            queue: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            queuePatch_deserted: str = queuePatch_adopted
                            queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                            queue_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if queue_recapture < 3:
                                queue_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d!" %(TFTGame_summary_json["game_id"], i, i, TFTGame_summary_json["game_id"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                            queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                            current_versions["queue"] = queuePatch_adopted
                            unmapped_keys["queue"].clear()
                            break
                    break
            ##云顶之弈强化符文（TFT augments）
            TFTAugmentIds_match_list: list[str] = sorted(set(augment for lst in list(map(lambda x: x["augments"] if "augments" in x else [], TFTGame_summary_json["participants"])) for augment in lst)) #`if "augments" in x`的作用是防止早期云顶之弈对局无强化符文导致程序报错（`if "augments" in x` is used here because some early TFT matches don't contain augments and result in KeyErrors consequently）
            for i in TFTAugmentIds_match_list:
                if not i in TFTAugments and current_versions["TFTAugment"] != TFTGamePatch:
                    TFTAugmentPatch_adopted: str = TFTGamePatch
                    TFTAugment_recapture: int = 1
                    logPrint("对局%d强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nAugment information (%s) of Match %d capture failed! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTGame_summary_json["game_id"], i, TFTAugment_recapture, TFTAugmentPatch_adopted, i, TFTGame_summary_json["game_id"], TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            TFTBasic: dict[str, Any] = source.json()
                        except requests.exceptions.JSONDecodeError: #存在版本合并更新的情况（Situation like merged update exists）
                            TFTAugmentPatch_deserted: str = TFTAugmentPatch_adopted
                            TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                            TFTAugment_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                        except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                            if TFTAugment_recapture < 3:
                                TFTAugment_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d!" %(TFTGame_summary_json["game_id"], i, i, TFTGame_summary_json["game_id"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                            TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                            current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                            unmapped_keys["TFTAugment"].clear()
                            break
                    break
            ##云顶之弈小小英雄（TFT companions）
            TFTCompanionIds_match_list: list[str] = sorted(set(map(lambda x: x["companion"]["content_ID"], TFTGame_summary_json["participants"])))
            for i in TFTCompanionIds_match_list:
                if not i in TFTCompanions and current_versions["TFTCompanion"] != TFTGamePatch:
                    TFTCompanionPatch_adopted: str = TFTGamePatch
                    TFTCompanion_recapture: int = 1
                    logPrint("对局%d小小英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的小小英雄信息……\nTFT companion information (%s) of Match %d capture failed! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTGame_summary_json["game_id"], i, TFTCompanion_recapture, TFTCompanionPatch_adopted, i, TFTGame_summary_json["game_id"], TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(TFTCompanionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            TFTCompanion: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            TFTCompanionPatch_deserted: str = TFTCompanionPatch_adopted
                            TFTCompanionPatch_adopted = FindPostPatch(Patch(TFTCompanionPatch_adopted), versionList)
                            TFTCompanion_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTCompanionPatch_deserted, TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_deserted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if TFTCompanion_recapture < 3:
                                TFTCompanion_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的小小英雄信息……\nYour network environment is abnormal! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的小小英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the companion (%s) of Match %d!" %(TFTGame_summary_json["game_id"], i, i, TFTGame_summary_json["game_id"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的小小英雄信息。\nTFT companion information changed to Patch %s." %(TFTCompanionPatch_adopted, TFTCompanionPatch_adopted), verbose = verbose)
                            TFTCompanions = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanion}
                            current_versions["TFTCompanion"] = TFTCompanionPatch_adopted
                            unmapped_keys["TFTCompanion"].clear()
                            break
                    break
            ##云顶之弈羁绊（TFT Traits）
            TFTTraitIds_match_list: list[str] = sorted(set(trait for s in [set(map(lambda x: x["name"], participant["traits"])) for participant in TFTGame_summary_json["participants"]] for trait in s))
            for i in TFTTraitIds_match_list:
                if not i in TFTTraits and current_versions["TFTTrait"] != TFTGamePatch:
                    TFTTraitPatch_adopted: str = TFTGamePatch
                    TFTTrait_recapture: int = 1
                    logPrint("对局%d羁绊信息（%s）获取失败！正在第%d次尝试改用%s版本的羁绊信息……\nTFT trait information (%s) of Match %d capture failed! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTGame_summary_json["game_id"], i, TFTTrait_recapture, TFTTraitPatch_adopted, i, TFTGame_summary_json["game_id"], TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(TFTTraitPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            TFTTrait: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            TFTTraitPatch_deserted: str = TFTTraitPatch_adopted
                            TFTTraitPatch_adopted = FindPostPatch(Patch(TFTTraitPatch_adopted), versionList)
                            TFTTrait_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTraitPatch_deserted, TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_deserted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if TFTTrait_recapture < 3:
                                TFTTrait_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的羁绊信息……\nYour network environment is abnormal! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d的羁绊信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the trait (%s) of Match %d!" %(TFTGame_summary_json["game_id"], i, i, TFTGame_summary_json["game_id"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的羁绊信息。\nTFT trait information changed to Patch %s." %(TFTTraitPatch_adopted, TFTTraitPatch_adopted), verbose = verbose)
                            TFTTraits = {}
                            for trait_iter in TFTTrait:
                                trait_id: str = trait_iter["trait_id"]
                                conditional_trait_sets = {}
                                if "conditional_trait_sets" in trait_iter: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
                                    for conditional_trait_set in trait_iter["conditional_trait_sets"]:
                                        style_idx: str = conditional_trait_set["style_idx"]
                                        conditional_trait_sets[style_idx] = conditional_trait_set
                                trait_iter["conditional_trait_sets"] = conditional_trait_sets
                                TFTTraits[trait_id] = trait_iter
                            current_versions["TFTTrait"] = TFTTraitPatch_adopted
                            unmapped_keys["TFTTrait"].clear()
                            break
                    break
            ##云顶之弈英雄（TFT champions）
            TFTChampionIds_match_list: list[str] = sorted(set(champion for s in [set(map(lambda x: x["character_id"], participant["units"])) for participant in TFTGame_summary_json["participants"]] for champion in s))
            for i in TFTChampionIds_match_list:
                if not i in TFTChampions and not i.lower() in set(map(lambda x: x.lower(), TFTChampions.keys())) and current_versions["TFTChampion"] != TFTGamePatch:
                    TFTChampionPatch_adopted: str = TFTGamePatch
                    TFTChampion_recapture: int = 1
                    logPrint("对局%d英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的棋子信息……\nTFT champion (%s) information of Match %d capture failed! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTGame_summary_json["game_id"], i, TFTChampion_recapture, TFTChampionPatch_adopted, i, TFTGame_summary_json["game_id"], TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                    while True:
                        try:
                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(TFTChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                            TFTChampion: list[dict[str, Any]] = source.json()
                        except requests.exceptions.JSONDecodeError:
                            TFTChampionPatch_deserted = TFTChampionPatch_adopted
                            TFTChampionPatch_adopted = FindPostPatch(Patch(TFTChampionPatch_adopted), versionList)
                            TFTChampion_recapture = 1
                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampionPatch_deserted, TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_deserted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                        except requests.exceptions.RequestException:
                            if TFTChampion_recapture < 3:
                                TFTChampion_recapture += 1
                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的棋子信息……\nYour network environment is abnormal! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                            else:
                                logPrint("网络环境异常！对局%d将采用原始数据！\nNetwork error! The original data will be used for Match %d!" %(TFTGame_summary_json["game_id"], TFTGame_summary_json["game_id"]), verbose = verbose)
                                break
                        else:
                            logPrint("已改用%s版本的棋子信息。\nTFT champion information changed to Patch %s." %(TFTChampionPatch_adopted, TFTChampionPatch_adopted), verbose = verbose)
                            TFTChampions = {}
                            if Patch(TFTChampionPatch_adopted) < Patch("13.17"): #从13.17版本开始，CommunityDragon数据库中关于云顶之弈棋子的数据格式发生微调（Since Patch 13.17, the format of TFT Champion data in CommunityDragon database has been modified）
                                for TFTChampion_iter in TFTChampion:
                                    champion_name: str = TFTChampion_iter["character_id"]
                                    TFTChampions[champion_name] = TFTChampion_iter
                            else:
                                for TFTChampion_iter in TFTChampion:
                                    champion_name = TFTChampion_iter["name"]
                                    TFTChampions[champion_name] = TFTChampion_iter["character_record"] #请注意该语句与4行之前的语句的差异，并看看一开始准备数据文件时使用的是哪一种——其实你应该猜的出来（Have you noticed the difference between this statement and the statement that is 4 lines above from this statement? Also, check which statement I chose for the beginning, when I prepared the data resources. Actually, you should be able to speculate it without referring to the code）
                            current_versions["TFTChampion"] = TFTChampionPatch_adopted
                            unmapped_keys["TFTChampion"].clear()
                            break
                    break
            ##云顶之弈装备（TFT items）
            s: set[str] = set()
            for participant in TFTGame_summary_json["participants"]:
                for unit in participant["units"]:
                    if "itemNames" in unit:
                        s |= set(unit["itemNames"])
                    elif "items" in unit:
                        s |= set(unit["items"])
                    else:
                        s |= set()
            TFTItemIds_match_list: list[str] = sorted(s)
            for i in TFTItemIds_match_list:
                if not i in TFTItems and not i in TFTAugments:
                    if current_versions["TFTItem"] != TFTGamePatch:
                        TFTItemPatch_adopted: str = TFTGamePatch
                        TFTItem_recapture: int = 1
                        logPrint("对局%d装备信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%s) of Match %d capture failed! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTGame_summary_json["game_id"], i, TFTItem_recapture, TFTItemPatch_adopted, i, TFTGame_summary_json["game_id"], TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTItem: list[dict[str, Any]] = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTItemPatch_deserted: str = TFTItemPatch_adopted
                                TFTItemPatch_adopted = FindPostPatch(Patch(TFTItemPatch_adopted), versionList)
                                TFTItem_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                            except requests.exceptions.RequestException:
                                if TFTItem_recapture < 3:
                                    TFTItem_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！对局%d的装备信息（%d）将采用原始数据！\nNetwork error! The original data will be used for the item (%d) of Match %d!" %(TFTGame_summary_json["game_id"], i, i, TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的云顶之弈装备信息。\nTFT item information changed to Patch %s." %(TFTItemPatch_adopted, TFTItemPatch_adopted), verbose = verbose)
                                TFTItems = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItem}
                                current_versions["TFTItem"] = TFTItemPatch_adopted
                                unmapped_keys["TFTItem"].clear()
                                break
                    #由于云顶之弈基础数据中也包含装备信息，这里将重新获取对局版本的云顶之弈基础数据（Because TFT basic data contain item data, here the program recaptures TFT basic data of the match version）
                    if current_versions["TFTAugment"] != TFTGamePatch:
                        TFTAugmentPatch_adopted = TFTGamePatch
                        TFTAugment_recapture = 1
                        while True:
                            try:
                                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                TFTBasic = source.json()
                            except requests.exceptions.JSONDecodeError:
                                TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                                TFTAugment_recapture = 1
                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                            except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                if TFTAugment_recapture < 3:
                                    TFTAugment_recapture += 1
                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                else:
                                    logPrint("网络环境异常！对局%d的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d!" %(TFTGame_summary_json["game_id"], i, i, TFTGame_summary_json["game_id"]), verbose = verbose)
                                    break
                            else:
                                logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                                TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                                current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                unmapped_keys["TFTAugment"].clear()
                                break
                    break
        #下面开始整理数据（Organize data）
        for i in range(len(TFTGame_summary_json["participants"])):
            participant_puuid: str = TFTGame_summary_json["participants"][i]["puuid"]
            await generate_TFTGameSummary_records(connection, TFTGame_summary_data, TFTGame_summary, i, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = gameIndex, current_puuid = puuidList, unmapped_keys = unmapped_keys, useInfoDict = useInfoDict, infos = infos, log = log, verbose = verbose)
            if sortStats and not (not save_bot and participant_puuid == BOT_UUID or not save_self and participant_puuid in puuidList or not save_other and not participant_puuid in puuidList): #这个if语句块是适配自定义脚本20而做的修改（This if-block is a modification made to adapt to Customized Program 20）
                for j in range(len(TFTGame_summary_header_keys)):
                    key: str = TFTGame_summary_header_keys[j]
                    TFTGame_stat_data[key].append(TFTGame_summary_data[key][-1]) #直接添加最近一次追加的数据，以简化代码（Directly append the recently appended data to simplify the code）
    #数据框列序整理（Dataframe column ordering）
    TFTGame_summary_statistics_output_order: list[int] = [40, 19, 55, 46, 47, 43, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 150, 148, 149, 203, 206, 209, 155, 153, 154, 212, 215, 218, 160, 158, 159, 221, 224, 227, 165, 163, 164, 230, 233, 236, 170, 168, 169, 239, 242, 245, 175, 173, 174, 248, 251, 254, 180, 178, 179, 257, 260, 263, 185, 183, 184, 266, 269, 272, 190, 188, 189, 275, 278, 281, 195, 193, 194, 284, 287, 290, 200, 198, 199, 293, 296, 299, 61, 57, 58, 59, 60, 68, 64, 65, 66, 67, 75, 71, 72, 73, 74, 82, 78, 79, 80, 81, 89, 85, 86, 87, 88, 96, 92, 93, 94, 95, 103, 99, 100, 101, 102, 110, 106, 107, 108, 109, 117, 113, 114, 115, 116, 124, 120, 121, 122, 123, 131, 127, 128, 129, 130, 138, 134, 135, 136, 137, 145, 141, 142, 143, 144]
    TFTGame_summary_data_organized: dict[str, list[Any]] = {TFTGame_summary_header_keys[i]: TFTGame_summary_data[TFTGame_summary_header_keys[i]] for i in TFTGame_summary_statistics_output_order}
    TFTGame_summary_df: pandas.DataFrame = pandas.DataFrame(data = TFTGame_summary_data_organized)
    optimize_bool_display(TFTGame_summary_df)
    TFTGame_summary_df = pandas.concat([pandas.DataFrame([TFTGame_summary_header])[TFTGame_summary_df.columns], TFTGame_summary_df], ignore_index = True)
    return (TFTGame_summary_df, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits)

async def sort_TFTGame_stats(connection: Connection, sgpSession: SGPSession, TFTMatchIDs: list[int], queues: dict[int, dict[str, Any]], TFTAugments: dict[str, dict[str, Any]], TFTChampions: dict[str, dict[str, Any]], TFTItems: dict[str, dict[str, Any]], TFTCompanions: dict[str, dict[str, Any]], TFTTraits: dict[str, dict[str, Any]], puuid: str | list[str] = "", excluded_reserve: bool = False, save_self: bool = True, save_other: bool = False, save_bot: bool = False, useAllVersions: bool = True, versionList: Optional[list[Patch]] = None, locale: str = "en_US", current_versions: Optional[dict[str, str]] = None, unmapped_keys: Optional[dict[str, set[Any]]] = None, TFTGame_summary_cache: Optional[dict[int, dict[str, Any]]] = None, session: Optional[requests.Session] = None, useInfoDict: bool = False, infos: Optional[dict[str, dict[str, Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame: #和sort_LoLGame_stats函数不同的是，根据对局序号查询云顶之弈对局概要需要借助SGP API，所以这里做了一处优化：如果某场对局在一个给定的对局记录中已经存在，则直接使用该对局记录中的数据。这就是参数表中引入TFTHistory的原因（The difference of this function from `sort_LoLGame_stats` is that SGP API is used to query TFT match summary. Hence, this function performs an optimization: if a match exists in a specified match history, then query the match history instead. This is why `TFTHistory` appears in the parameter list）
    '''
    将多场云顶之弈对局中的玩家数据汇总形成一个表格，同时包含对局元数据和玩家战绩。<br>Organize player stats in multiple TFT matches into a dataframe, which contains match metadata and player stats.
    
    和`sort_TFTGame_summary`函数不同的是，该函数从对局序号得到玩家战绩数据框，而`sort_TFTGame_summary`函数是伴随着对局概要数据框的形成而形成的。<br>The difference of this function from `sort_TFTGame_summary` is that this function returns the player stats dataframe based on matchIds, while this dataframe is formed along the formation of match summary dataframe in `sort_TFTGame_summary`.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: 通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.
    :type sgpSession: Connection
    :param TFTMatchIDs: 云顶之弈对局序号列表。<br>TFT matchId list.
    :type TFTMatchIDs: list[int]
    :param queues: 整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`
    :type queues: dict[int, dict[str, Any]]
    :param TFTAugments: 整理后的云顶之弈强化符文数据资源。键是强化符文代码，值是强化符文信息字典。<br>Organized TFT augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始云顶之弈强化符文数据资源可通过以下链接获取：<br>The raw TFT augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/cdragon/tft/en_us.json
    :type TFTAugments: dict[str, dict[str, Any]]
    :param TFTChampions: 整理后的云顶之弈英雄数据资源。键是英雄代码，值是英雄信息字典。<br>Organized TFT champion data resource. Each key is a championid, and each value is a champion information dictionary.
    
        原始云顶之弈英雄数据资源可通过以下链接获取：<br>The raw TFT champion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftchampions.json`
    :type TFTChampions: dict[str, dict[str, Any]]
    :param TFTItems: 整理后的云顶之弈装备信息。键是装备代码，值是装备信息字典。<br>Organized TFT item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始云顶之弈装备数据资源可通过以下链接获取：<br>The raw TFT item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftitems.json`
    :type TFTItems: dict[int, dict[str, Any]]
    :param TFTCompanions: 整理后的小小英雄信息。键是小小英雄代码，值是小小英雄信息字典。<br>Organized companion data resource. Each key is a companionId, and each value is a companion information dictionary.
    
        原始小小英雄数据资源可通过以下链接获取：<br>The raw companion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/companions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/companions.json`
    :type TFTCompanions: dict[str, dict[str, Any]]
    :param TFTTraits: 整理后的云顶之弈羁绊信息。键是羁绊代码，值是羁绊信息字典。<br>Organized TFT trait data resource. Each key is a traitId, and each value is a trait information dictionary.
    
        原始云顶之弈羁绊数据资源可通过以下链接获取：<br>The raw TFT trait data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tfttraits.json`
    :type TFTTraits: dict[str, dict[str, Any]]
    :param puuid: 主召唤师的玩家通用唯一识别码。可以是单一值，也可以是一个列表。这个参数只用于确定敌友阵营。<br>The main summoner's puuid. Both a single value and a list are supported. This parameter is only used to determine the enemy and ally teams.
    :type puuid: str | list[str]
    :param excluded_reserve: 在对局不包含主召唤师时，是否仍然保存该对局。默认为假。<br>Whether to persist on saving the match when the match doesn't contain the main summoner. False by default.
    :type excluded_reserve: bool
    :param save_self: 是否保存主召唤师的数据。默认为真。<br>Whether to save the data of the main summoner. True by default.
    :type save_self: bool
    :param save_other: 是否保存主召唤师以外的玩家数据。默认为假。<br>Whether to save the data of players except the main summoner. False by default.
    :type save_other: bool
    :param save_bot: 是否保存电脑玩家的数据。默认为假。<br>Whether to save the data of bot players. False by default.
    :type save_bot: bool
    :param useAllVersions: 是否为数据资源异常处理执行版本回溯。默认为假。<br>Whether to perform version backtracking for data resource exception handling. False by default.
    :type useAllVersions: bool
    :param versionList: 适用于CommunityDragon数据库的版本对象列表。<br>A list of Patch objects compatible with CommunityDragon database versioning.
    :type versionList: list[Patch]
    :param locale: 用于重新获取数据资源的语言文化代码。默认使用美式英语。<br>Language code to recapture data resources. English (US) by default.
    :type locale: str
    :param current_versions: 各数据资源目前正在使用的版本信息。<br>Current patches of data resources.
    :type current_versions: dict[str, str]
    :param unmapped_keys: 各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.
    :type unmapped_keys: dict[str, set[Any]]
    :param TFTGame_summary_cache: 云顶之弈对局概要缓存。键为对局序号，值为对局概要。通过以下接口得到：<br>TFT match summary cache. Each key is a matchId, and each value is a match summary. It's obtained by the following endpoint:
    
        - `GET /match-history-query/v1/products/tft/player/{puuid}/SUMMARY?startIndex={startIndex}&count={count}`
    :type TFTGame_summary_cache: dict[int, dict[str, Any]]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param useInfoDict: 是否使用召唤师信息缓存字典。默认为否。<br>Whether to use a summoner information cache dictionary. False by default.
    :type useInfoDict: bool
    :param infos: 召唤师信息缓存字典。键是玩家通用唯一识别码，值是召唤师信息字典。<br>Summoner information cache dictionary. Each key is a puuid, and each value is a summoner information dictionary.
    :type infos: dict[str, dict[str, Any]]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    '''
    #参数预处理（Parameter pre-processing）
    if versionList == None:
        versionList = []
    if current_versions == None:
        current_versions = {"TFTAugment": "", "TFTChampion": "", "TFTItem": "", "TFTCompanion": "", "TFTTrait": ""}
    if unmapped_keys == None:
        unmapped_keys = {"TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set()}
    if TFTGame_summary_cache == None or not (isinstance(TFTGame_summary_cache, dict) and all(map(lambda x: isinstance(x, int), TFTGame_summary_cache.keys())) and all(map(lambda x: isinstance(x, dict) and all(map(lambda y: y in {"metadata", "json"}, x.keys())), TFTGame_summary_cache.values()))):
        TFTGame_summary_cache = {}
    if session == None:
        session = requests.Session()
    if infos == None:
        infos = {}
    if log == None:
        log = LogManager()
    #常量准备（Constant preparation）
    logPrint = log.logPrint
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId: str = current_party["platformId"]
    puuidList: list[str] = [puuid] if isinstance(puuid, str) else puuid
    version_re: re.Pattern[str] = re.compile(r"\d+\.\d+\.\d+\.\d+")
    error_TFTMatchIDs: list[int] = [] #记录实际存在但未如期获取的对局序号（Records the matches that really exist but fail to be fetched）
    matches_not_found: list[int] = [] #记录系统已经删除但是不报异常的对局序号（Records the matches deleted from the database but still existing in the match history）
    matches_to_remove: list[int] = [] #记录获取成功但不包含主玩家的对局序号（Records the matches that are fetched successfully but don't contain the main player）
    #开始获取各对局内的玩家信息（Begin to capture the players' information in each match）
    TFTGame_summary_header_keys: list[str] = list(TFTGame_summary_header.keys())
    TFTGame_stat_data: dict[str, list[Any]] = {key: [] for key in TFTGame_summary_header_keys}
    for matchId in TFTMatchIDs:
        match_id: str = f"{platformId}_{matchId}"
        if matchId in TFTGame_summary_cache:
            TFTGame_summary: dict[str, Any] = TFTGame_summary_cache[matchId]
            status: int = 200
        else:
            status, TFTGame_summary = await get_game_summary_sgp(connection, sgpSession, match_id, checkLoL = False, checkTFT = True, log = log, verbose = verbose)
            if status == 200:
                TFTGame_summary_cache[matchId] = TFTGame_summary
        if "errorCode" in TFTGame_summary:
            logPrint(TFTGame_summary, verbose = verbose)
            error_TFTMatchIDs.append(matchId)
        else:
            if TFTGame_summary.get("json"):
                TFTGame_summary_json: dict[str, Any] = TFTGame_summary.get("json", {})
                TFTGameVersion: str = version_re.search(TFTGame_summary_json["game_version"]).group()
                TFTGamePatch: str = ".".join(TFTGameVersion.split(".")[:2])
                if excluded_reserve or len(set(puuidList) & set(map(lambda x: x["puuid"], TFTGame_summary_json["participants"]))) != 0:
                    #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                    if useAllVersions:
                        ##游戏模式（Game mode）
                        queueIds_match_list: list[int] = [TFTGame_summary_json["queue_id"]]
                        for j in queueIds_match_list:
                            if not j in queues and current_versions["queue"] != TFTGamePatch:
                                queuePatch_adopted: str = TFTGamePatch
                                queue_recapture: int = 1
                                logPrint("第%d/%d场对局（对局序号：%d）游戏模式信息（%d）获取失败！正在第%d次尝试改用%s版本的游戏模式信息……\nGame mode information (%d) of Match %d / %d (matchId: %d) capture failed! Changing to game modes of Patch %s ... Times tried: %d." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, queue_recapture, queuePatch_adopted, j, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], queuePatch_adopted, queue_recapture), verbose = verbose)
                                while True:
                                    try:
                                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/queues.json" %(queuePatch_adopted, language_cdragon[locale]), session = session, log = log)
                                        queue: list[dict[str, Any]] = source.json()
                                    except requests.exceptions.JSONDecodeError:
                                        queuePatch_deserted: str = queuePatch_adopted
                                        queuePatch_adopted = FindPostPatch(Patch(queuePatch_adopted), versionList)
                                        queue_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to game modes of Patch %s ... Times tried: %d." %(queuePatch_deserted, queue_recapture, queuePatch_adopted, queuePatch_deserted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                    except requests.exceptions.RequestException:
                                        if queue_recapture < 3:
                                            queue_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的游戏模式信息……\nYour network environment is abnormal! Changing to game modes of Patch %s ... Times tried: %d." %(queue_recapture, queuePatch_adopted, queuePatch_adopted, queue_recapture), verbose = verbose)
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的游戏模式信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the game modes (%s) of Match %d / %d (matchId: %d)!" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], j, j, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                            break
                                    else:
                                        logPrint("已改用%s版本的游戏模式信息。\nGame mode information changed to Patch %s." %(queuePatch_adopted, queuePatch_adopted), verbose = verbose)
                                        queues = {queue_iter["id"]: queue_iter for queue_iter in queue}
                                        current_versions["queue"] = queuePatch_adopted
                                        unmapped_keys["queue"].clear()
                                        break
                                break
                        ##云顶之弈强化符文（TFT augments）
                        TFTAugmentIds_match_list: list[str] = sorted(set(augment for lst in list(map(lambda x: x["augments"] if "augments" in x else [], TFTGame_summary_json["participants"])) for augment in lst)) #`if "augments" in x`的作用是防止早期云顶之弈对局无强化符文导致程序报错（`if "augments" in x` is used here because some early TFT matches don't contain augments and result in KeyErrors consequently）
                        for i in TFTAugmentIds_match_list:
                            if not i in TFTAugments and current_versions["TFTAugment"] != TFTGamePatch:
                                TFTAugmentPatch_adopted: str = TFTGamePatch
                                TFTAugment_recapture: int = 1
                                logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nAugment information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, TFTAugment_recapture, TFTAugmentPatch_adopted, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                while True:
                                    try:
                                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                        TFTBasic: dict[str, Any] = source.json()
                                    except requests.exceptions.JSONDecodeError: #存在版本合并更新的情况（Situation like merged update exists）
                                        TFTAugmentPatch_deserted: str = TFTAugmentPatch_adopted
                                        TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                                        TFTAugment_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                    except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                        if TFTAugment_recapture < 3:
                                            TFTAugment_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchId: %d)!" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                            break
                                    else:
                                        logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                                        TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                                        current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                        unmapped_keys["TFTAugment"].clear()
                                        break
                                break
                        ##云顶之弈小小英雄（TFT companions）
                        TFTCompanionIds_match_list: list[str] = sorted(set(map(lambda x: x["companion"]["content_ID"], TFTGame_summary_json["participants"])))
                        for i in TFTCompanionIds_match_list:
                            if not i in TFTCompanions and current_versions["TFTCompanion"] != TFTGamePatch:
                                TFTCompanionPatch_adopted: str = TFTGamePatch
                                TFTCompanion_recapture: int = 1
                                logPrint("第%d/%d场对局（对局序号：%d）小小英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的小小英雄信息……\nTFT companion information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, TFTCompanion_recapture, TFTCompanionPatch_adopted, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                                while True:
                                    try:
                                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(TFTCompanionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                        TFTCompanion: list[dict[str, Any]] = source.json()
                                    except requests.exceptions.JSONDecodeError:
                                        TFTCompanionPatch_deserted: str = TFTCompanionPatch_adopted
                                        TFTCompanionPatch_adopted = FindPostPatch(Patch(TFTCompanionPatch_adopted), versionList)
                                        TFTCompanion_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTCompanionPatch_deserted, TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_deserted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                                    except requests.exceptions.RequestException:
                                        if TFTCompanion_recapture < 3:
                                            TFTCompanion_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的小小英雄信息……\nYour network environment is abnormal! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_adopted, TFTCompanion_recapture), verbose = verbose)
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的小小英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the companion (%s) of Match %d / %d (matchId: %d)!" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                            break
                                    else:
                                        logPrint("已改用%s版本的小小英雄信息。\nTFT companion information changed to Patch %s." %(TFTCompanionPatch_adopted, TFTCompanionPatch_adopted), verbose = verbose)
                                        TFTCompanions = {companion_iter["contentId"]: companion_iter for companion_iter in TFTCompanion}
                                        current_versions["TFTCompanion"] = TFTCompanionPatch_adopted
                                        unmapped_keys["TFTCompanion"].clear()
                                        break
                                break
                        ##云顶之弈羁绊（TFT Traits）
                        TFTTraitIds_match_list: list[str] = sorted(set(trait for s in [set(map(lambda x: x["name"], participant["traits"])) for participant in TFTGame_summary_json["participants"]] for trait in s))
                        for i in TFTTraitIds_match_list:
                            if not i in TFTTraits and current_versions["TFTTrait"] != TFTGamePatch:
                                TFTTraitPatch_adopted: str = TFTGamePatch
                                TFTTrait_recapture: int = 1
                                logPrint("第%d/%d场对局（对局序号：%d）羁绊信息（%s）获取失败！正在第%d次尝试改用%s版本的羁绊信息……\nTFT trait information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, TFTTrait_recapture, TFTTraitPatch_adopted, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                                while True:
                                    try:
                                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(TFTTraitPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                        TFTTrait: list[dict[str, Any]] = source.json()
                                    except requests.exceptions.JSONDecodeError:
                                        TFTTraitPatch_deserted: str = TFTTraitPatch_adopted
                                        TFTTraitPatch_adopted = FindPostPatch(Patch(TFTTraitPatch_adopted), versionList)
                                        TFTTrait_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTraitPatch_deserted, TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_deserted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                                    except requests.exceptions.RequestException:
                                        if TFTTrait_recapture < 3:
                                            TFTTrait_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的羁绊信息……\nYour network environment is abnormal! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_adopted, TFTTrait_recapture), verbose = verbose)
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的羁绊信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the trait (%s) of Match %d / %d (matchId: %d)!" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                            break
                                    else:
                                        logPrint("已改用%s版本的羁绊信息。\nTFT trait information changed to Patch %s." %(TFTTraitPatch_adopted, TFTTraitPatch_adopted), verbose = verbose)
                                        TFTTraits = {}
                                        for trait_iter in TFTTrait:
                                            trait_id: str = trait_iter["trait_id"]
                                            conditional_trait_sets = {}
                                            if "conditional_trait_sets" in trait_iter: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
                                                for conditional_trait_set in trait_iter["conditional_trait_sets"]:
                                                    style_idx: str = conditional_trait_set["style_idx"]
                                                    conditional_trait_sets[style_idx] = conditional_trait_set
                                            trait_iter["conditional_trait_sets"] = conditional_trait_sets
                                            TFTTraits[trait_id] = trait_iter
                                        current_versions["TFTTrait"] = TFTTraitPatch_adopted
                                        unmapped_keys["TFTTrait"].clear()
                                        break
                                break
                        ##云顶之弈英雄（TFT champions）
                        TFTChampionIds_match_list: list[str] = sorted(set(champion for s in [set(map(lambda x: x["character_id"], participant["units"])) for participant in TFTGame_summary_json["participants"]] for champion in s))
                        for i in TFTChampionIds_match_list:
                            if not i in TFTChampions and not i.lower() in map(lambda x: x.lower(), TFTChampions.keys()) and current_versions["TFTChampion"] != TFTGamePatch:
                                TFTChampionPatch_adopted: str = TFTGamePatch
                                TFTChampion_recapture: int = 1
                                logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的棋子信息……\nTFT champion (%s) information of Match %d / %d (matchId: %d) capture failed! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, TFTChampion_recapture, TFTChampionPatch_adopted, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                                while True:
                                    try:
                                        source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(TFTChampionPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                        TFTChampion: list[dict[str, Any]] = source.json()
                                    except requests.exceptions.JSONDecodeError:
                                        TFTChampionPatch_deserted: str = TFTChampionPatch_adopted
                                        TFTChampionPatch_adopted = FindPostPatch(Patch(TFTChampionPatch_adopted), versionList)
                                        TFTChampion_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampionPatch_deserted, TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_deserted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                                    except requests.exceptions.RequestException:
                                        if TFTChampion_recapture < 3:
                                            TFTChampion_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的棋子信息……\nYour network environment is abnormal! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_adopted, TFTChampion_recapture), verbose = verbose)
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）将采用原始数据！\nNetwork error! The original data will be used for Match %d / %d (matchId: %d)!" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                            break
                                    else:
                                        logPrint("已改用%s版本的棋子信息。\nTFT champion information changed to Patch %s." %(TFTChampionPatch_adopted, TFTChampionPatch_adopted), verbose = verbose)
                                        TFTChampions = {}
                                        if Patch(TFTChampionPatch_adopted) < Patch("13.17"): #从13.17版本开始，CommunityDragon数据库中关于云顶之弈小小英雄的数据格式发生微调（Since Patch 13.17, the format of TFT Champion data in CommunityDragon database has been modified）
                                            for TFTChampion_iter in TFTChampion:
                                                champion_name: str = TFTChampion_iter["character_id"]
                                                TFTChampions[champion_name] = TFTChampion_iter
                                        else:
                                            for TFTChampion_iter in TFTChampion:
                                                champion_name = TFTChampion_iter["name"]
                                                TFTChampions[champion_name] = TFTChampion_iter["character_record"] #请注意该语句与4行之前的语句的差异，并看看一开始准备数据文件时使用的是哪一种——其实你应该猜的出来（Have you noticed the difference between this statement and the statement that is 4 lines above from this statement? Also, check which statement I chose for the beginning, when I prepared the data resources. Actually, you should be able to speculate it without referring to the code）
                                        current_versions["TFTChampion"] = TFTChampionPatch_adopted
                                        unmapped_keys["TFTChampion"].clear()
                                        break
                                break
                        ##云顶之弈装备（TFT items）
                        s: set[str] = set()
                        for participant in TFTGame_summary_json["participants"]:
                            for unit in participant["units"]:
                                if "itemNames" in unit:
                                    s |= set(unit["itemNames"])
                                elif "items" in unit:
                                    s |= set(unit["items"])
                                else:
                                    s |= set()
                        TFTItemIds_match_list: list[str] = sorted(s)
                        for i in TFTItemIds_match_list:
                            if not i in TFTItems and not i in TFTAugments:
                                if current_versions["TFTItem"] != TFTGamePatch:
                                    TFTItemPatch_adopted: str = TFTGamePatch
                                    TFTItem_recapture: int = 1
                                    logPrint("第%d/%d场对局（对局序号：%d）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%s) of Match %d / %d (matchId: %d) capture failed! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, TFTItem_recapture, TFTItemPatch_adopted, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                    while True:
                                        try:
                                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                            TFTItem: list[dict[str, Any]] = source.json()
                                        except requests.exceptions.JSONDecodeError:
                                            TFTItemPatch_deserted = TFTItemPatch_adopted
                                            TFTItemPatch_adopted = FindPostPatch(Patch(TFTItemPatch_adopted), versionList)
                                            TFTItem_recapture = 1
                                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                        except requests.exceptions.RequestException:
                                            if TFTItem_recapture < 3:
                                                TFTItem_recapture += 1
                                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture), verbose = verbose)
                                            else:
                                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的装备信息（%d）将采用原始数据！\nNetwork error! The original data will be used for the item (%d) of Match %d / %d (matchId: %d)!" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                                break
                                        else:
                                            logPrint("已改用%s版本的云顶之弈装备信息。\nTFT item information changed to Patch %s." %(TFTItemPatch_adopted, TFTItemPatch_adopted), verbose = verbose)
                                            TFTItems = {TFTItem_iter["nameId"]: TFTItem_iter for TFTItem_iter in TFTItem}
                                            current_versions["TFTItem"] = TFTItemPatch_adopted
                                            unmapped_keys["TFTItem"].clear()
                                            break
                                #由于云顶之弈基础数据中也包含装备信息，这里将重新获取对局版本的云顶之弈基础数据（Because TFT basic data contain item data, here the program recaptures TFT basic data of the match version）
                                if current_versions["TFTAugment"] != TFTGamePatch:
                                    TFTAugmentPatch_adopted = TFTGamePatch
                                    TFTAugment_recapture = 1
                                    while True:
                                        try:
                                            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[locale]), session = session, log = log)
                                            TFTBasic = source.json()
                                        except requests.exceptions.JSONDecodeError:
                                            TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                            TFTAugmentPatch_adopted = FindPostPatch(Patch(TFTAugmentPatch_adopted), versionList)
                                            TFTAugment_recapture = 1
                                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                        except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                            if TFTAugment_recapture < 3:
                                                TFTAugment_recapture += 1
                                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture), verbose = verbose)
                                            else:
                                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchId: %d)!" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"], i, i, TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), TFTGame_summary_json["game_id"]), verbose = verbose)
                                                break
                                        else:
                                            logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted), verbose = verbose)
                                            TFTAugments = {item["apiName"]: item for item in TFTBasic["items"]}
                                            current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                            unmapped_keys["TFTAugment"].clear()
                                            break
                                break
                    for i in range(len(TFTGame_summary_json["participants"])):
                        participant_puuid: str = TFTGame_summary_json["participants"][i]["puuid"]
                        if not (not save_bot and participant_puuid == BOT_UUID or not save_self and participant_puuid in puuidList or not save_other and not participant_puuid in puuidList):
                            await generate_TFTGameSummary_records(connection, TFTGame_stat_data, TFTGame_summary, i, queues, TFTAugments, TFTChampions, TFTItems, TFTCompanions, TFTTraits, gameIndex = TFTMatchIDs.index(matchId) + 1, current_puuid = puuidList, unmapped_keys = unmapped_keys, useInfoDict = useInfoDict, infos = infos, log = log, verbose = verbose)
                    if excluded_reserve:
                        logPrint("[%d/%d]对局%d不包含主玩家。已保留该对局。\nMatch %d doesn't contain the main player but is reserved." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), matchId, matchId), print_time = True, verbose = verbose)
                    else:
                        logPrint("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %s" %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), matchId), print_time = True, verbose = verbose)
                else:
                    matches_to_remove.append(matchId)
                    logPrint("[%d/%d]对局%d不包含主玩家。已移除该对局。\nMatch %d doesn't contain the main player and is deprecated." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), matchId, matchId), print_time = True, verbose = verbose)
            else:
                matches_not_found.append(matchId)
                logPrint("[%d/%d]对局%d数据不可用。\nMatch %d data not available." %(TFTMatchIDs.index(matchId) + 1, len(TFTMatchIDs), matchId, matchId), print_time = True, verbose = verbose)
    if len(error_TFTMatchIDs) > 0:
        logPrint("警告：以下%d场对局获取失败。\nWarning: The following %d match(es) fail to be fetched." %(len(error_TFTMatchIDs), len(error_TFTMatchIDs)), verbose = verbose)
        logPrint(error_TFTMatchIDs, verbose = verbose)
    if len(matches_to_remove) > 0:
        logPrint("注意：以下%d场对局因不包含主玩家而被移除。\nAttention: The following %d match(es) are removed because they don't contain the main player." %(len(matches_to_remove), len(matches_to_remove)), verbose = verbose)
        logPrint(matches_to_remove, verbose = verbose)
    if len(matches_not_found) > 0:
        logPrint("注意：以下%d场对局数据不可用。\nAttention: The following %d match(es) are not available." %(len(matches_not_found), len(matches_not_found)), verbose = verbose)
        logPrint(matches_not_found, verbose = verbose)
    #数据框列序整理（Dataframe column ordering）
    TFTGame_stat_statistics_output_order: list[int] = [0, 19, 46, 47, 43, 5, 14, 15, 16, 6, 10, 18, 7, 13, 11, 12, 307, 305, 40, 55, 33, 34, 35, 38, 52, 53, 49, 36, 50, 42, 54, 41, 39, 44, 45, 23, 24, 25, 150, 148, 149, 203, 206, 209, 155, 153, 154, 212, 215, 218, 160, 158, 159, 221, 224, 227, 165, 163, 164, 230, 233, 236, 170, 168, 169, 239, 242, 245, 175, 173, 174, 248, 251, 254, 180, 178, 179, 257, 260, 263, 185, 183, 184, 266, 269, 272, 190, 188, 189, 275, 278, 281, 195, 193, 194, 284, 287, 290, 200, 198, 199, 293, 296, 299, 61, 57, 58, 59, 60, 68, 64, 65, 66, 67, 75, 71, 72, 73, 74, 82, 78, 79, 80, 81, 89, 85, 86, 87, 88, 96, 92, 93, 94, 95, 103, 99, 100, 101, 102, 110, 106, 107, 108, 109, 117, 113, 114, 115, 116, 124, 120, 121, 122, 123, 131, 127, 128, 129, 130, 138, 134, 135, 136, 137, 145, 141, 142, 143, 144]
    TFTGame_stat_data_organized: dict[str, list[Any]] = {TFTGame_summary_header_keys[i]: TFTGame_stat_data[TFTGame_summary_header_keys[i]] for i in TFTGame_stat_statistics_output_order}
    TFTGame_stat_df: pandas.DataFrame = pandas.DataFrame(data = TFTGame_stat_data_organized)
    logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...", verbose = verbose)
    optimize_bool_display(TFTGame_stat_df)
    logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!", verbose = verbose)
    TFTGame_stat_df = pandas.concat([pandas.DataFrame([TFTGame_summary_header])[TFTGame_stat_df.columns], TFTGame_stat_df], ignore_index = True)
    return TFTGame_stat_df
