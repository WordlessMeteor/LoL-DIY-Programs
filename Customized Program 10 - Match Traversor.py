from lcu_driver import Connector
from lcu_driver.connection import Connection
import argparse, json, keyboard, os, random, time
from typing import Any, Callable, Iterable, Optional
from typing_extensions import Literal
from src.utils.logger import LogManager
from src.utils.webRequest import SGPSession
from src.utils.patch import Patch
from src.utils.summoner import print_summoner_info, get_info, get_info_name
from src.core.config.const import TEST_GAME_INFO
from src.core.config.servers import set_platform_folder
from src.core.dataframes.matchHistory import get_matchSummary_sgp, get_matchDetails_sgp, get_game_info_sgp, get_game_timeline_sgp

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--begin", help = "指定对局序号范围的下标（Specify the lower limit of matchId range）", action = "store", type = int, default = 0)
parser.add_argument("-e", "--end", help = "指定对局序号范围的上标（Specify the upper limit of matchId range）", action = "store", type = int, default = 0)
args = parser.parse_args()

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/03/07
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 遍历对局以查找符合要求的对局（Traverse the matches to find one that fits the demands）
#-----------------------------------------------------------------------------
def specify_matchId_limit(start_matchId: Optional[int] = None, end_matchId: Optional[int] = None) -> tuple[int, int]: #处理命令行和函数传入的变量（Handle the arguments passed from cmdline and a function）
    if args.begin == 0 or not isinstance(args.begin, int):
        if start_matchId == None:
            print("请输入起始对局序号：\nPlease input the starting matchId:")
            while True:
                start_matchId_str: str = input()
                if start_matchId_str == "":
                    continue
                elif start_matchId_str == "-1":
                    return (-1, -1)
                else:
                    try:
                        start_matchId = int(start_matchId_str)
                    except ValueError:
                        print("请输入一个整数。\nPlease submit an integer.")
                    else:
                        if start_matchId <= 0:
                            print("请输入一个正整数。\nPlease submit a positive integer.")
                        else:
                            break
    elif args.begin < 0:
        print("起始对局序号必须是一个正整数。\nThe starting matchId must be a positive integer.")
        return (-1, -1)
    else:
        start_matchId = args.begin #在指定了命令行变量的情况下，优先采用命令行的值（While the cmdline argument is specified, its value is taken in priority）
    if args.end == 0 or not isinstance(args.end, int):
        if end_matchId == None:
            print("请输入终止对局序号：\nPlease input the ending matchId:")
            while True:
                end_matchId_str: str = input()
                if end_matchId_str == "":
                    continue
                elif end_matchId_str == "-1":
                    return (-1, -1)
                else:
                    try:
                        end_matchId = int(end_matchId_str)
                    except ValueError:
                        print("请输入一个整数。\nPlease submit an integer.")
                    else:
                        if end_matchId <= 0:
                            print("请输入一个正整数。\nPlease submit a non-negative integer.")
                        else:
                            break
    elif args.end < 0:
        print("终止对局序号必须是一个正整数。\nThe ending matchId must be a positive integer.")
        return (-1, -1)
    else:
        end_matchId = args.end
    if start_matchId >= end_matchId:
        print("起始对局序号必须小于终止对局序号。\nThe starting matchId must be smaller than the ending matchId.")
        return (-1, -1)
    else:
        return (start_matchId, end_matchId)

async def index_traverse_match(connection: Connection, start_matchId: Optional[int] = None, end_matchId: Optional[int] = None, func_str: str = "", product: Literal["LoL", "TFT", ""] = "") -> int:
    '''
    在给定对局上下限的情况下，遍历范围内的对局，并保存所有符合条件的对局信息和时间轴。<br>Given the starting and ending matchIds, traverse save information and timeline of matches that meet the condition.
    
    :param connection: 连接对象。一般在程序中已指定好。<br>A Connection object. Usually specified in the program.
    :type connection: lcu_driver.connection.Connection
    :param start_matchId: 起始对局序号。<br>Starting matchId.
    :type start_matchId: int
    :param end_matchId: 终止对局序号。<br>Ending matchId.
    :type end_matchId: int
    :param func_str: 判断条件函数的字符串形式，给定对局序号的情况下返回其是否符合条件。<br>A string form of a condition judgment function that returns whether a matchId meets the condition.
    :type func_str: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）
    :type product: str
    :return: 状态码。<br>Status code.
    :rtype: int
    '''
    #参数预处理（Parameter preprocess）
    start_matchId, end_matchId = specify_matchId_limit(start_matchId, end_matchId)
    if start_matchId == -1 and end_matchId == -1:
        return -1
    if func_str == "":
        print("未指定条件函数。将保存所有有效的对局信息和时间轴。\nNo condition function specified. All valid match information and timeline will be saved.")
        func: Callable[[dict[str, Any]], bool] = lambda x: "metadata" in x and "json" in x
    else:
        try:
            func = eval(f"lambda game_info: {func_str}")
        except:
            print("判断条件函数语法错误！\nCondition judgment function syntax error!")
            return -1
        else:
            try:
                tmp = func(TEST_GAME_INFO) #校验函数是否能如期运行（Check whether the function can run as expected）
            except:
                print("判断条件函数运行出错！\nAn error occurred when testing the condition judgment function!")
                return -1
            else:
                if not isinstance(tmp, bool):
                    print("判断条件函数返回类型错误！\nCondition judgment function return type mismatch!")
                    return -1
    #变量和会话初始化（Variable and session initialization）
    if product == "":
        checkLoL: bool = True
        checkTFT: bool = False
        skipTFT: bool = False
    elif product == "TFT":
        checkLoL = skipTFT = False
        checkTFT = True
    else:
        checkLoL = skipTFT = True
        checkTFT = False #此时这个变量无关紧要（In this case this variable doesn't matter）
    session: SGPSession = SGPSession()
    await session.init(connection)
    session.session.trust_env = False #英雄联盟请求无需走代理（League of Legends requests don't need a proxy）
    region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    region: str = region_locale["region"]
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    log_filename: str = f"Matches on {platformId} {start_matchId}-{end_matchId}.log"
    log_folder: str = "日志（Logs）/对局遍历器"
    log_path: str = os.path.join(log_folder, log_filename).replace("\\", "/")
    os.makedirs(log_folder, exist_ok = True)
    if not os.path.exists(log_path):
        with open(log_path, "w", encoding = "utf-8") as fp: #因为要追加写，所以要先创建这个文件（To append content, this file must be created previously）
            pass
    log: LogManager = LogManager(path = log_path, mode = "a+", encoding = "utf-8")
    logPrint = log.logPrint
    session.setLog(log)
    logPrint(f"正在查询{platformId}服务器的对局……\nSearching matches on server {platformId} ...")
    logPrint(f"【参数设置】对局序号范围（matchId range）：[{start_matchId}, {end_matchId}]")
    logPrint(f"【参数设置】判断条件（Condition）： {func_str}")
    logPrint(f"【参数设置】产品（Product）：{product}")
    #查询前的数据结构准备（Data structure prepared for query）
    matches_found: list[int] = []
    json_folder: str = os.path.join(set_platform_folder(region, platformId), "1. MatchIDs").replace("\\", "/")
    os.makedirs(json_folder, exist_ok = True)
    saved_matchIds: set[int] = set(map(lambda x: int(x.split("-")[-1].split()[0]), [_ for _ in os.listdir(json_folder) if _.startswith(f"Match Information ({product}) - ") and "(SGP)" in _]))
    #遍历对局序号（Traverse matchIds）
    gameCount: int = end_matchId - start_matchId + 1
    for matchId in range(start_matchId, end_matchId + 1):
        if keyboard.is_pressed("esc"):
            logPrint("【手动中止】您已退出查询。\nYou've exited the query.")
            break
        currentProcess: int = matchId - start_matchId + 1
        match_id: str = f"{platformId}_{matchId}"
        status, game_info = await get_game_info_sgp(connection, session, match_id, checkLoL = checkLoL, checkTFT = checkTFT, skipTFT = skipTFT)
        if status != 200:
            logPrint(f"【获取失败】[{currentProcess}/{gameCount}]对局{matchId}信息获取失败！\nMatch {matchId} information capture failure!", print_time = True)
        else:
            if func(game_info):
                matches_found.append(matchId)
                logPrint(f"【找到对局】[{currentProcess}/{gameCount}]对局{matchId}信息符合条件。已将其加入列表。\nMatch {matchId} fits the requirements and has been added to the found match list!", print_time = True)
                #下面将json文件保存到对局文件夹中（The following code save the json files into the match folder）
                if not matchId in saved_matchIds:
                    match_product: str = game_info["metadata"]["product"]
                    json1name: str = f"Match Information ({match_product}) - {platformId}-{matchId} (SGP).json"
                    with open(os.path.join(json_folder, json1name), "w", encoding = "utf-8") as fp:
                        json.dump(game_info, fp, indent = 4, ensure_ascii = False)
                    if match_product == "LoL":
                        json2name: str = f"Match Timeline ({match_product}) - {platformId}-{matchId} (SGP).json"
                        status, game_timeline = await get_game_timeline_sgp(connection, session, match_id, checkLoL = checkLoL, checkTFT = checkTFT)
                        if status == 200:
                            with open(os.path.join(json_folder, json2name), "w", encoding = "utf-8") as fp:
                                json.dump(game_timeline, fp, indent = 4, ensure_ascii = False)
                    saved_matchIds.add(matchId)
            else:
                logPrint(f"【跳过对局】[{currentProcess}/{gameCount}]对局{matchId}不符合条件。\nMatch {matchId} doesn't meet the requirements.", print_time = True)
    #保存数据到本地文件（Saved data to a local file）
    print(matches_found)
    print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
    print('共找到%d场对局！对局序号已保存到%s。\nNumber of matches found: %d. MatchIDs have been saved into %s.' %(len(matches_found), log_path, len(matches_found), log_path))
    log.write("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())))
    log.write("【结果】共找到%d场对局。\nFound %d match(es).\n" %(len(matches_found), len(matches_found)))
    # logPrint("符合条件的对局如下：\nMatches that fit the requirements are as follows:")
    # for matchId in matches_found:
    #     logPrint(matchId)
    log.write("列表形式（List）：\n" + str(matches_found))
    log.close()
    return 0

async def history_traverse_match(connection: Connection, start_puuid: str, product: Literal["LoL", "TFT"], func_str: str = "") -> int:
    '''
    指定一个起始玩家通用唯一识别码，查询其对局记录，并查询其对战历史中遇到过的所有人类玩家的对局记录，往复。<br>Specify a starting puuid, search for its match history, and search for match history of each human player involved, and so on.
    
    :param start_puuid: 起始的玩家通用唯一识别码。该参数的不同取值决定了被保存的对局序号的不同。<br>The starting puuid. Value of this parameter may influence the order of matches to be saved.
    :type start_puuid: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）
    :param func_str: 判断条件函数的字符串形式，给定对局序号的情况下返回其是否符合条件。<br>A string form of a condition judgment function that returns whether a matchId meets the condition.
    
        提示：与另外两个函数不同的是，由于本函数中的游戏产品是预先确定的，所以在制作判断条件函数时可以跳过对产品名的假设。<br>Hint: What's different from the other two functions is that because `product` is preemptively determined in this function, users may skip the verification of the game product when making the custom condition judgment function.
    :type func_str: str
    :return: 状态码。<br>Status code.
    :rtype: int
    '''
    #参数预处理（Parameter preprocess）
    if func_str == "":
        print("未指定条件函数。将保存所有有效的对局信息和时间轴。\nNo condition function specified. All valid match information and timeline will be saved.")
        func: Callable[[dict[str, Any]], bool] = lambda x: "metadata" in x and "json" in x
    else:
        try:
            func = eval(f"lambda game_info: {func_str}")
        except:
            print("判断条件函数语法错误！\nCondition judgment function syntax error!")
            return -1
        else:
            try:
                tmp = func(TEST_GAME_INFO) #校验函数是否能如期运行（Check whether the function can run as expected）
            except:
                print("判断条件函数运行出错！\nAn error occurred when testing the condition judgment function!")
                return -1
            else:
                if not isinstance(tmp, bool):
                    print("判断条件函数返回类型错误！\nCondition judgment function return type mismatch!")
                    return -1
    start_summoner_info: dict[str, Any] = await get_info(connection, start_puuid)
    if not start_summoner_info["info_got"]:
        print(start_summoner_info["message"])
        return -1
    #变量和会话初始化（Variable and session initialization）
    start_summoner_name: str = get_info_name(start_summoner_info["body"])
    session: SGPSession = SGPSession()
    await session.init(connection)
    session.session.trust_env = False #英雄联盟请求无需走代理（League of Legends requests don't need a proxy）
    region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    region: str = region_locale["region"]
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    log_filename: str = f"Matches on {platformId} starting from {start_summoner_name}.log"
    log_folder: str = "日志（Logs）/对局遍历器"
    log_path: str = os.path.join(log_folder, log_filename).replace("\\", "/")
    os.makedirs(log_folder, exist_ok = True)
    if not os.path.exists(log_path):
        with open(log_path, "w", encoding = "utf-8") as fp: #因为要追加写，所以要先创建这个文件（To append content, this file must be created previously）
            pass
    log: LogManager = LogManager(path = log_path, mode = "a+", encoding = "utf-8")
    logPrint = log.logPrint
    session.setLog(log)
    logPrint(f"正在查询{platformId}服务器的对局……\nSearching matches on server {platformId} ...")
    logPrint("【参数设置】起始玩家（Starting summoner）： %s (%s)" %(start_summoner_name, start_summoner_info["body"]["puuid"]))
    logPrint(f"【参数设置】判断条件（Condition）： {func_str}")
    logPrint(f"【参数设置】产品（Product）：{product}")
    #查询前的数据结构准备（Data structure prepared for query）
    matches_found: set[int] = set()
    json_folder: str = os.path.join(set_platform_folder(region, platformId), "1. MatchIDs").replace("\\", "/")
    os.makedirs(json_folder, exist_ok = True)
    puuids_to_search: list[str] = [start_puuid]
    puuids_searched: set[str] = set()
    traversed_player_count: int = 0
    found_match_count: int = 0
    saved_matchIds: set[int] = set(map(lambda x: int(x.split("-")[-1].split()[0]), [_ for _ in os.listdir(json_folder) if _.startswith(f"Match Information ({product}) - ") and "(SGP)" in _]))
    #遍历对局序号（Traverse matchIds）
    while len(puuids_to_search) > 0:
        if keyboard.is_pressed("esc"):
            logPrint("【手动中止】您已退出查询。\nYou've exited the query.")
            break
        puuid: str = puuids_to_search.pop(0)
        if puuid in puuids_searched:
            continue
        traversed_player_count += 1
        info: dict[str, Any] = await get_info(connection, puuid)
        if info["info_got"]:
            summoner_name: str = get_info_name(info["body"])
        else:
            summoner_name = str(traversed_player_count)
        if product == "LoL":
            logPrint(f"【对局记录】[{traversed_player_count}]正在获取玩家{summoner_name}（{puuid}）的对局概要和时间轴……\nFetching the match summary and details of player {summoner_name} ({puuid}) ...")
        else:
            logPrint(f"【对局记录】[{traversed_player_count}]正在获取玩家{summoner_name}（{puuid}）的对局信息……\nFetching the match information of player {summoner_name} ({puuid}) ...")
        matchHistory_get, matchHistory = await get_matchSummary_sgp(connection, session, puuid, product, begin = 0, count = 1000, log = log)
        if matchHistory_get:
            if product == "LoL":
                matchDetails_get, matchDetails = await get_matchDetails_sgp(connection, session, puuid, product, begin = 0, count = 1000, log = log)
                matchTimelines: dict[int, dict[str, Any]] = {int(game_timeline["metadata"]["match_id"].split("_")[1]): game_timeline for game_timeline in matchDetails["games"]}
            else:
                matchTimelines = {}
            for game_info in matchHistory["games"]:
                match_id: str = game_info["metadata"]["match_id"]
                matchId: int = int(match_id.split("_")[1])
                if "participants" in game_info["metadata"]:
                    puuids_to_search.extend(game_info["metadata"]["participants"])
                if func(game_info):
                    matches_found.add(matchId)
                    found_match_count += 1
                    logPrint(f"【找到对局】[{traversed_player_count}][{found_match_count}]对局{matchId}信息符合条件。已将其加入集合。\nMatch {matchId} fits the requirements and has been added to the found match set!")
                    #下面将json文件保存到日志文件夹中（The following code save the json files into the log folder）
                    if not matchId in saved_matchIds:
                        match_product: str = game_info["metadata"]["product"]
                        json1name: str = f"Match Information ({match_product}) - {platformId}-{matchId} (SGP).json"
                        with open(os.path.join(json_folder, json1name), "w", encoding = "utf-8") as fp:
                            json.dump(game_info, fp, indent = 4, ensure_ascii = False)
                        if matchId in matchTimelines:
                            json2name: str = f"Match Timeline ({match_product}) - {platformId}-{matchId} (SGP).json"
                            game_timeline: dict[str, Any] = matchTimelines[matchId]
                            with open(os.path.join(json_folder, json2name), "w", encoding = "utf-8") as fp:
                                json.dump(game_timeline, fp, indent = 4, ensure_ascii = False)
                        saved_matchIds.add(matchId)
                else:
                    logPrint(f"【跳过对局】[{traversed_player_count}][{found_match_count}]对局{matchId}不符合条件。\nMatch {matchId} doesn't meet the requirements.")
        else:
            logPrint(f"【获取失败】[{traversed_player_count}]玩家{summoner_name}（{puuid}）的对局概要获取失败。\nFailed to fetch the match summary of player {summoner_name} ({puuid}).")
        puuids_searched.add(puuid)
    #保存数据到本地文件（Saved data to a local file）
    print(sorted(matches_found))
    print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
    print('共找到%d场对局！对局序号已保存到“%s”。\nNumber of matches found: %d. MatchIDs have been saved into "%s".' %(len(matches_found), log_path, len(matches_found), log_path))
    log.write("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())))
    log.write("【结果】共找到%d场对局。\nFound %d match(es).\n" %(len(matches_found), len(matches_found)))
    # logPrint("符合条件的对局如下：\nMatches that fit the requirements are as follows:")
    # for matchId in matches_found:
    #     logPrint(matchId)
    log.write("列表形式（List）：\n" + str(sorted(matches_found)))
    log.close()
    return 0

async def binary_search_match(connection: Connection, start_matchId: Optional[int] = None, end_matchId: Optional[int] = None, func_str: str = "", product: Literal["LoL", "TFT", ""] = "LoL", matchIds_not_found: Optional[set[int]] = None) -> int:
    '''
    在给定对局上下限的情况下，通过指定判断条件函数参数，查询符合条件的**一场**对局。<br>Given the starting and ending matchIds, by specifying the condition judgment function in the parameter, this function searches for **a** match that fits the conditions.
    
    条件必须具有单调不减性：<br>The condition must be monotonously non-decreasing:
        - `func(begin_gameInfo)`应返回False。<br>`func(start_matchId)` should return False.
        - `func(end_gameInfo)`应返回True。<br>`func(end_matchId)` should return True.
        - 在`start_matchId`和`end_matchId`有且仅有一个`middle_matchId`，使得对于任意的`matchId ∈ [start_matchId, middle_matchId)`，`func(begin_gameInfo)`都返回False，且对于任意的`matchId ∈ [middle_matchId, end_matchId]`，`func(end_gameInfo)`都返回True。<br>There's only one `middle_matchId` between `start_matchId` and `end_matchId`, where for an arbitrary `matchId ∈ [start_matchId, middle_matchId)`, `func(begin_gameInfo)` returns False, and for an arbitraty `matchId ∈ [middle_matchId, end_matchId]`, `func(end_gameInfo)` returns True.
    
    在传入起始对局序号和终止对局序号时，应尽量保证其周围存在对局，以缩短二分查找的启动时间。<br>While passing the `start_matchId` and `end_matchId`, users should make sure that available matches exist around them, so that the time to launch the binary search can be shortened.
    
    :param connection: 连接对象。一般在程序中已指定好。<br>A Connection object. Usually specified in the program.
    :type connection: lcu_driver.connection.Connection
    :param start_matchId: 起始对局序号。<br>Starting matchId.
    :type start_matchId: int
    :param end_matchId: 终止对局序号。<br>Ending matchId.
    :type end_matchId: int
    :param func_str: 阈值函数的字符串形式，给定对局序号的情况下返回其是否符合条件。<br>A string form of a threshold function that returns whether a matchId meets the condition.
    :type func_str: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）
    :type product: str
    :param matchIds_not_found: 通过事先指定不存在的对局序号，减少请求次数。在某个阶段提示后半部分无可用对局时，用户中断程序后重新运行的情形下非常好用。<br>Decrease the number of requests by specifying the matchIds of matches that don't exist in advance. Especially useful when the program gives a hint that "No match found in latter half", then the user interrupts the program and runs it again.
    :type matchIds_not_found: set[int]
    :return: 符合条件的最小对局序号。<br>The smallest matchId that fits the condition.
    :rtype: int
    '''
    #参数预处理（Parameter preprocess）
    start_matchId, end_matchId = specify_matchId_limit(start_matchId, end_matchId)
    if start_matchId == -1 and end_matchId == -1:
        return -1
    if func_str == "":
        print("请指定一个条件函数。\nPlease specify a condition function.")
        return -1
    else:
        try:
            func: Callable[[dict[str, Any]], bool] = eval(f"lambda game_info: {func_str}")
        except:
            print("阈值函数语法错误！\nThreshold function syntax error!")
            return -1
        else:
            try:
                tmp = func(TEST_GAME_INFO) #校验函数是否能如期运行（Check whether the function can run as expected）
            except:
                print("阈值函数运行出错！\nAn error occurred when testing the threshold function!")
                return -1
            else:
                if not isinstance(tmp, bool):
                    print("阈值函数必须返回一个逻辑值。\nThe threshold function must return a boolean value.")
                    return -1
    if matchIds_not_found == None:
        matchIds_not_found = set()
    #变量和会话初始化（Variable and session initialization）
    session: SGPSession = SGPSession()
    await session.init(connection)
    session.session.trust_env = False #英雄联盟请求无需走代理（League of Legends requests don't need a proxy）
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    skipTFT: bool = not (product == "TFT")
    traversed_matchIds: dict[int, bool] = {} #记录已经遍历过的对局是否符合条件（Records whether the traversed matches meet the condition）
    #准备日志输入输出流（Prepare log iostream）
    log_folder = "日志（Logs）/Customized Program 10 - Match Traversor"
    os.makedirs(log_folder, exist_ok = True)
    currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log: LogManager = LogManager(os.path.join(log_folder, currentTime + ".log"), mode = "a+", encoding = "utf-8")
    logPrint = log.logPrint
    logPrint(f"正在查询{platformId}服务器的对局……\nSearching matches on server {platformId} ...")
    logPrint(f"【参数设置】对局序号范围（matchId range）：[{start_matchId}, {end_matchId}]")
    logPrint(f"【参数设置】判断条件（Condition）： {func_str}")
    logPrint(f"【参数设置】产品（Product）：{product}")
    #首先检查目标对局序号是否会落在所指定的对局序号范围中（First, check whether the target matchId will fall within the specified matchId range）
    logPrint("【参数处理】正在递减查找起始对局……\nSearching for an available starting match by decrement ...")
    while True:
        print(start_matchId, end = "\r")
        match_id: str = f"{platformId}_{start_matchId}"
        status, game_info = await get_game_info_sgp(connection, session, match_id, skipTFT = skipTFT, verbose = False)
        if status == 404:
            start_matchId -= 1
        else:
            traversed_matchIds[start_matchId] = func(game_info)
            if func(game_info):
                logPrint(f"【中止程序】起始对局序号{start_matchId}已符合条件。请尝试更改条件或者换用一个更小的起始对局序号。\nThe starting matchId {start_matchId} already meets the demands. Please try again with another condition or a smaller `start_matchId`.")
                return -1
            else:
                break
    logPrint("【参数处理】正在递增查找终止对局……\nSearching for an available ending match by increment ...")
    while True:
        print(end_matchId, end = "\r")
        match_id: str = f"{platformId}_{end_matchId}"
        status, game_info = await get_game_info_sgp(connection, session, match_id, skipTFT = skipTFT, verbose = False)
        if status == 404:
            end_matchId += 1
        else:
            traversed_matchIds[end_matchId] = func(game_info)
            if func(game_info):
                break
            else:
                logPrint(f"【中止程序】终止对局序号{end_matchId}不符合条件。请尝试更改条件或者换用一个更大的终止对局序号。\nThe ending matchId {end_matchId} doesn't meet the demands. Please try again with another condition or a bigger `end_matchId`.")
                return -1
    #执行二分查找。需要着重解决对局序号的稀疏性（Perform the binary search. Need to settle the sparsity of matchIds）
    logPrint("开始执行二分查找。\nBegin to perform binary search.")
    begin: int = start_matchId
    end: int = end_matchId
    offset: int = 0 #标记存在的对局相对于中位数的偏移量。已弃用，因为在停机维护期间存在大量不可访问的对局序号（Marks the offset of an existing match to the middle matchId. Depracated because there're too many inaccessible matchIds during mainteinance）
    matchIds_not_found = set() #优化请求次数（Optimize the number of times of requests）
    times: int = 0 #标记尝试次数（Marks number of attempts）
    ##方案1：优先高位偏移（Scheme 1: Significant-bit offset in priority）
    # power: int = int(math.log10((end - begin) // 2)) #从高位增加偏移量，是基于高位遍历到不存在的对局的概率要低于低位遍历的统计命题。底数10可基于服务器中不存在的对局的频率进行适当调整（Adding offset to the most significant bit is based on the statistical proposition that the probability of a traversal based on a more significant bit to encounter a match that doesn't exist is less than the probability of a traversal based on a less significant bit. The base number 10 can be modified based on the frequency of matches that don't exist）
    # while True:
    #     times += 1
    #     middle: int = (begin + end) // 2 + offset
    #     logPrint("#{0:<4}".format(times), "{0:>15}".format(begin), "{0:>15}".format(end), "{0:>10}".format(f"({end - begin})"), "{0:>15}".format(middle), sep = " | ", end = " | ", print_time = True)
    #     if begin >= end: #当begin和end之间全部是不存在的对局时，end最终会因为`end = (begin + end) // 2`这一步逐渐回归到begin，此时应当返回迭代之前的那个end（When none of the matchIds between and excluding `begin` and `end` exist, `end` will gradually approach `begin` by `end = (begin + end) // 2`. When `end` equals `begin`, this function should return the `end` before any iteration）
    #         logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False)
    #         result: int = end_matchId
    #         break
    #     if middle >= end: #终止对局序号在上面已经验证过，此处不需要验证（`end` has been verified above, so here we don't need to verify it again）
    #         if power == 0: #表明前闭后开区间[(begin + end) // 2, end)无可用对局（Represents the half-closed interval [(begin + end) // 2, end) doesn't contain any available match）
    #             end = (begin + end) // 2 #注意到此时end临时变为“可能不存在”的状态。这有三种情形：①如果begin和end之间的对局序号全部不存在，最终会导致begin == end而退出函数；②如果有一个对局序号存在，但该对局序号不符合条件，则begin变为middle，继续执行此循环；③如果有一个对局序号存在，且该对局序号符合条件，end变为middle，从而恢复存在的状态（Note that now `end` enters a status that "might not exist". Then there're three cases: ① If none of the matchIds between `begin` and `end` exists, eventually `begin == end` and the program will quit this function; ②If there's one matchId that exists, but this matchId doesn't meet the condition, `begin` will become `middle` and this loop will go on; ③ If there's one matchId that exists, and this matchId meets the condition, `end` will become middle and therefore recover its existence property）
    #             offset = 0
    #             logPrint("{0:<30}".format("No match found in latter half."), "↙", sep = " | ", write_time = False)
    #         else:
    #             power -= 1
    #             offset = 10 ** power
    #             logPrint("{0:<30}".format("Power of offset decrements."), "↙", sep = " | ", write_time = False)
    #         continue
    #     if middle == begin: #end = begin + 1
    #         logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False) #因为事先已知起始对局序号不符合条件，终止对局序号符合条件（Because we already know that the starting matchId doesn't meet the condition, but the ending matchId does）
    #         result = sorted(traversed_matchIds.keys())[sorted(traversed_matchIds.keys()).index(middle) + 1] #期望返回的是条件第一次为真时的对局序号。不需要担心下标越界的问题，因为下一个最多到达end。此处不可写为`result = end`，因为此时end可能不存在（The expected returned result is the smallest matchId that meets the condition. No worries about IndexError, for the next element is `end` in the most extreme case. This line shouldn't be replaced by `result = end`, because the matchId `end` may not exist）
    #         break
    #     if middle in matchIds_not_found:
    #         offset += 10 ** power
    #         logPrint("{0:<30}".format("Match not found."), "×", sep = " | ", write_time = False)
    #     else:
    #         match_id = f"{platformId}_{middle}"
    #         status, game_info = await get_game_info_sgp(connection, session, match_id, skipTFT = skipTFT, verbose = False)
    #         if status == 404:
    #             matchIds_not_found.add(middle)
    #             offset += 10 ** power
    #             logPrint("{0:<30}".format("Match not found."), "×", sep = " | ", write_time = False)
    #         else:
    #             traversed_matchIds[middle] = func(game_info)
    #             ordered_matchIds: list[int] = sorted(traversed_matchIds.keys()) #每次遍历一场存在的对局后更新此列表（Each traversal of an existing match updates this list）
    #             current_index: int = ordered_matchIds.index(middle) #获取有序列表中刚刚添加的对局的下标（Get the index of the match just added in the ordered list）
    #             if func(game_info):
    #                 prev_matchId: int = ordered_matchIds[current_index - 1] #这里不可能出现下标越界，因为有序列表中至少已经有用户一开始输入的起始对局序号了（Here IndexError can't be thrown, for the ordered list at least contains the starting matchId that the user inputs at the beginning of the program execution）
    #                 if not traversed_matchIds[prev_matchId] and set(range(prev_matchId + 1, middle)) < matchIds_not_found: #prev_matchId不符合条件，middle符合条件，且prev_matchId和middle之间的对局序号都不存在（`prev_matchId` doesn't meet the condition, `middle` does and none of the matchIds between `prev_matchId` and `middle` exists）
    #                     logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False)
    #                     result = middle
    #                     break
    #                 else:
    #                     end = middle
    #                     logPrint("{0:<30}".format("End matchId decrements."), "↓", sep = " | ", write_time = False)
    #             else:
    #                 next_matchId: int = ordered_matchIds[current_index + 1] #这里不可能出现下标越界，因为有序列表中至少已经有用户一开始输入的终止对局序号了（Here IndexError can't be thrown, for the ordered list at least contains the ending matchId that the user inputs at the beginning of the program execution）
    #                 if traversed_matchIds[next_matchId] and set(range(middle + 1, next_matchId)) < matchIds_not_found: #middle不符合条件，next_matchId符合条件，且next_matchId和middle之间的对局序号都不存在（`middle` doesn't meet the condition, `next_matchId` does and none of the matchIds between `middle` and `next_matchId` exists）
    #                     logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False)
    #                     result = next_matchId
    #                     break
    #                 else:
    #                     begin = middle
    #                     logPrint("{0:<30}".format("Begin matchId Increments."), "↑", sep = " | ", write_time = False)
    #             offset = 0
    #             power = int(math.log10((end - begin) // 2)) if end - begin > 1 else 0
    ##方案2：随机选取偏移（Scheme 2: Random offset）
    offset_range: set[int] = set()
    reset_offset_range: bool = True #重置偏移范围（Resets the range of offset）
    while True:
        times += 1
        middle: int = (begin + end) // 2 + offset
        if reset_offset_range:
            offset_range = set(range(0, end - middle))
            reset_offset_range = False
        logPrint("#{0:<4}".format(times), "{0:>15}".format(begin), "{0:>15}".format(end), "{0:>10}".format(f"({end - begin})"), "{0:>15}".format(middle), "{0:>10}".format(f"({offset})"), sep = " | ", end = " | ", print_time = True)
        if begin >= end: #当begin和end之间全部是不存在的对局时，end最终会因为`end = (begin + end) // 2`这一步逐渐回归到begin，此时应当返回迭代之前的那个end（When none of the matchIds between and excluding `begin` and `end` exist, `end` will gradually approach `begin` by `end = (begin + end) // 2`. When `end` equals `begin`, this function should return the `end` before any iteration）
            logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False)
            result: int = end_matchId
            break
        if middle == begin: #end = begin + 1
            logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False) #因为事先已知起始对局序号不符合条件，终止对局序号符合条件（Because we already know that the starting matchId doesn't meet the condition, but the ending matchId does）
            result = sorted(traversed_matchIds.keys())[sorted(traversed_matchIds.keys()).index(middle) + 1] #期望返回的是条件第一次为真时的对局序号。不需要担心下标越界的问题，因为下一个最多到达end。此处不可写为`result = end`，因为此时end可能不存在（The expected returned result is the smallest matchId that meets the condition. No worries about IndexError, for the next element is `end` in the most extreme case. This line shouldn't be replaced by `result = end`, because the matchId `end` may not exist）
            break
        if middle in matchIds_not_found:
            offset_range.remove(offset)
            if len(offset_range) > 0:
                offset_range_list: list[int] = sorted(offset_range)
                offset = random.sample(offset_range_list, 1)[0]
                logPrint("{0:<30}".format("Match not found."), "×", sep = " | ", write_time = False)
            else: #表明前闭后开区间[(begin + end) // 2, end)无可用对局（Represents the half-closed interval [(begin + end) // 2, end) doesn't contain any available match）
                end = (begin + end) // 2
                logPrint("{0:<30}".format("No match found in latter half."), "↙", sep = " | ", write_time = False)
                offset = 0
                reset_offset_range = True
                continue
        else:
            match_id = f"{platformId}_{middle}"
            status, game_info = await get_game_info_sgp(connection, session, match_id, skipTFT = skipTFT, verbose = False)
            if status == 404:
                matchIds_not_found.add(middle)
                offset_range.remove(offset)
                if len(offset_range) > 0:
                    offset_range_list: list[int] = sorted(offset_range)
                    offset = random.sample(offset_range_list, 1)[0]
                    logPrint("{0:<30}".format("Match not found."), "×", sep = " | ", write_time = False)
                else:
                    end = (begin + end) // 2
                    logPrint("{0:<30}".format("No match found in latter half."), "↙", sep = " | ", write_time = False)
                    offset = 0
                    reset_offset_range = True
                    continue
            else:
                traversed_matchIds[middle] = func(game_info)
                ordered_matchIds: list[int] = sorted(traversed_matchIds.keys()) #每次遍历一场存在的对局后更新此列表（Each traversal of an existing match updates this list）
                current_index: int = ordered_matchIds.index(middle) #获取有序列表中刚刚添加的对局的下标（Get the index of the match just added in the ordered list）
                if func(game_info):
                    prev_matchId: int = ordered_matchIds[current_index - 1] #这里不可能出现下标越界，因为有序列表中至少已经有用户一开始输入的起始对局序号了（Here IndexError can't be thrown, for the ordered list at least contains the starting matchId that the user inputs at the beginning of the program execution）
                    if not traversed_matchIds[prev_matchId] and set(range(prev_matchId + 1, middle)) < matchIds_not_found: #prev_matchId不符合条件，middle符合条件，且prev_matchId和middle之间的对局序号都不存在（`prev_matchId` doesn't meet the condition, `middle` does and none of the matchIds between `prev_matchId` and `middle` exists）
                        logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False)
                        result = middle
                        break
                    else:
                        end = end_matchId = middle
                        logPrint("{0:<30}".format("End matchId decrements."), "↓", sep = " | ", write_time = False)
                else:
                    next_matchId: int = ordered_matchIds[current_index + 1] #这里不可能出现下标越界，因为有序列表中至少已经有用户一开始输入的终止对局序号了（Here IndexError can't be thrown, for the ordered list at least contains the ending matchId that the user inputs at the beginning of the program execution）
                    if traversed_matchIds[next_matchId] and set(range(middle + 1, next_matchId)) < matchIds_not_found: #middle不符合条件，next_matchId符合条件，且next_matchId和middle之间的对局序号都不存在（`middle` doesn't meet the condition, `next_matchId` does and none of the matchIds between `middle` and `next_matchId` exists）
                        logPrint("{0:<30}".format("Target match is found."), "√", sep = " | ", write_time = False)
                        result = next_matchId
                        break
                    else:
                        begin = start_matchId = middle
                        logPrint("{0:<30}".format("Begin matchId Increments."), "↑", sep = " | ", write_time = False)
                reset_offset_range = True
                offset = 0
    logPrint(f"结果（Result）： {result}")
    return result

#在这里自定义用于对局遍历函数的判断条件函数模板（Define the custom condition judgment function templates for `index_traverse_match` function hereafter）
##示例（Examples）
def isKiwiMatch(game_info: dict[str, Any]) -> bool:
    return game_info["metadata"]["product"] == "LoL" and game_info["json"]["gameMode"] == "KIWI"

def isKiwiPentaMatch(game_info: dict[str, Any]) -> bool:
    return game_info["metadata"]["product"] == "LoL" and bool(game_info["json"]) and game_info["json"]["queueId"] == 2400 and any(map(lambda participant: bool(participant["pentaKills"]), game_info["json"]["participants"]))

#在这里自定义用于二分查找对局函数的阈值函数模板（Define the custom threshold function templates for `binary_search_match` function hereafter）
##调试（Debug）
def gameId_compare(game_info: dict[str, Any], gameId: int) -> bool:
    return game_info["json"]["gameId"] >= gameId

##示例（Examples）
def first_match_after_mainteinance(game_info: dict[str, Any], patch: str) -> bool:
    return game_info["json"].get("endOfGameResult", "") != "Abort_Unexpected" and Patch(game_info["json"]["gameVersion"]) >= Patch(patch)

def define_function() -> tuple[str, Optional[Callable[[dict[str, Any]], bool]]]:
    while True:
        func_str: str = input("f(game_info): ")
        if func_str == "":
            func = None
            break
        else:
            try:
                func = eval(f"lambda game_info: {func_str}")
            except:
                print("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                try:
                    tmp = func(TEST_GAME_INFO) #校验函数是否能如期运行（Check whether the function can run as expected）
                except:
                    print("函数运行出错！请重新输入。\nAn error occurred when testing the function! Please try again.")
                else:
                    if isinstance(tmp, bool):
                        break
                    else:
                        print("您输入的函数返回的不是逻辑值！请重新输入。\nYour function doesn't return a boolean value! Please try again.")
    return (func_str, func)

async def index_traversal_main(connection: Connection) -> None:
    prepared: bool = False #标记函数参数是否准备就绪（Marks whether the parameters are ready）
    step: int = 1 #步骤计数（Step counter）
    start_matchId: int = -1 #起始对局序号（Starting matchId）
    end_matchId: int = -1 #终止对局序号（Ending matchId）
    func_str: str = "" #函数字符串（Function string）
    func: Optional[Callable[[dict[str, Any]], bool]] = None #函数对象（Function object）
    product: str = "" #产品（Product）
    while True:
        if step == 0:
            break
        elif step == 1:
            start_matchId, end_matchId = specify_matchId_limit()
            if start_matchId == -1 and end_matchId == -1:
                step -= 2
        elif step == 2:
            print('请输入一个筛选对局的函数。该函数应当返回逻辑值。\nPlease input a function to filter matches. This function should return a boolean value.\n示例（Example）：\ngame_info["metadata"]["product"] == "LoL" and game_info["json"]["gameMode"] == "KIWI" #判断对局是否是海克斯大乱斗（Judge whethe a match is ARAM: Mayhem）\n输入空字符串以放弃筛选，转而保留所有对局的信息。\nSumbit an empty string to give up filtering and save all matches instead.')
            func_str, func = define_function()
        elif step == 3:
            print('请选择一个产品。\nPlease select a product.\n0\t返回第一步（Return to the first step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）\n%s3\t全部（Both）' %("☆" if func == None else "!"))
            while True:
                product_option: str = input()
                if product_option == "":
                    continue
                elif product_option[0] == "0":
                    step = 0
                    break
                elif product_option[0] == "1":
                    product = "LoL"
                    break
                elif product_option[0] == "2":
                    product = "TFT"
                    break
                elif product_option[0] == "3":
                    product = ""
                    break
                else:
                    print("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 4:
            prepared = True
            break
        else:
            print("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
        step += 1
    if prepared:
        await index_traverse_match(connection, start_matchId = start_matchId, end_matchId = end_matchId, func_str = func_str, product = product)

async def history_traversal_main(connection: Connection) -> None:
    prepared: bool = False #标记函数参数是否准备就绪（Marks whether the parameters are ready）
    step: int = 1 #步骤计数（Step counter）
    start_puuid: str = "" #起始玩家通用唯一识别码（Starting puuid）
    product: str = "LoL" #产品（Product）
    func_str: str = "" #函数字符串（Function string）
    func: Optional[Callable[[dict[str, Any]], bool]] = None #函数对象（Function object）
    while True:
        if step == 0:
            break
        elif step == 1:
            print('请输入您想要当作遍历起点的召唤师名称。输入空字符串从自己开始。输入“0”以退出程序。\nPlease input the name of the summoner you want to start with. Submit an empty string to start from yourself. Submit "0" to exit the program.')
            while True:
                start_summoner_name: str = input()
                if start_summoner_name == "":
                    start_summoner_name = "current-summoner"
                if start_summoner_name == "0":
                    step -= 2
                    break
                else:
                    start_info: dict[str, Any] = await get_info(connection, start_summoner_name)
                    if start_info["info_got"]:
                        start_puuid: str = start_info["body"]["puuid"]
                        start_summonerName: str = get_info_name(start_info["body"])
                        print(f"当前遍历起点（Current traversal origin）： {start_summonerName} ({start_puuid})")
                        break
                    else:
                        print(start_info["message"])
        elif step == 2:
            print('请输入一个筛选对局的函数。该函数应当返回逻辑值。\nPlease input a function to filter matches. This function should return a boolean value.\n示例（Example）：\ngame_info["metadata"]["product"] == "LoL" and game_info["json"]["gameMode"] == "KIWI" #判断对局是否是海克斯大乱斗（Judge whethe a match is ARAM: Mayhem）\n输入空字符串以放弃筛选，转而保留所有对局的信息。\nSumbit an empty string to give up filtering and save all matches instead.')
            func_str, func = define_function()
        elif step == 3:
            print('请选择一个产品。\nPlease select a product.\n0\t返回第一步（Return to the first step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）')
            while True:
                product_option: str = input()
                if product_option == "":
                    continue
                elif product_option[0] == "0":
                    step = 0
                    break
                elif product_option[0] == "1":
                    product = "LoL"
                    break
                elif product_option[0] == "2":
                    product = "TFT"
                    break
                else:
                    print("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 4:
            prepared = True
            break
        else:
            print("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
        step += 1
    if prepared:
        await history_traverse_match(connection, start_puuid, product, func_str = func_str)

async def binary_search_main(connection: Connection) -> None:
    threshold_function_definition_hint_printed: bool = False #标记是否已经打印过阈值函数定义的提示（Marks whether the program has printed the hint of a threshold function's definition）
    prepared: bool = False
    step: int = 1
    start_matchId: int = -1
    end_matchId: int = -1
    func_str: str = ""
    func: Optional[Callable[[dict[str, Any]], bool]] = None
    product: str = ""
    matchIds_not_found: set[int] = set()
    while True:
        if step == 0:
            break
        elif step == 1:
            start_matchId, end_matchId = specify_matchId_limit()
            if start_matchId == -1 and end_matchId == -1:
                step -= 2
        elif step == 2:
            if not threshold_function_definition_hint_printed:
                print("阈值函数f：存在唯一的对局序号x₀ ∈ [a, b]，使得对于任意的x < x₀，f(x)为假，且对于任意的x ≥ x₀，f(x)为真。\nThreshold function f: There exists a unique matchId x₀ ∈ [a, b] such that for any x < x₀, f(x) is false, and for any x ≥ x₀, f(x) is true.")
                threshold_function_definition_hint_printed = True
            print('请输入一个阈值函数。该函数应当返回逻辑值。\nPlease input a threshold function. This function should return a boolean value.\n示例（Example）：\ngame_info["json"]["gameId"] >= 8502294282 #获取对局序号在8502294282之后的下一场可用对局（Get the next available match after Match 8502294282）\ngame_info["json"].get("endOfGameResult", "") != "Abort_Unexpected" and Patch(game_info["json"]["gameVersion"]) >= Patch("16.5") #查找当前大区在26.05版本的第一场对局（Check the first match in Patch 26.05 on the current server）\n输入空字符串以返回上一步。\nSumbit an empty string to return to the last step.')
            func_str, func = define_function()
            if func == None:
                step -= 2
        elif step == 3:
            print('请选择一个产品。\nPlease select a product.\n0\t返回上一步（Return to the last step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）')
            while True:
                product_option: str = input()
                if product_option == "":
                    continue
                elif product_option[0] == "0":
                    step -= 2
                    break
                elif product_option[0] == "1":
                    product = "LoL"
                    break
                elif product_option[0] == "2":
                    product = "TFT"
                    break
                else:
                    print("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 4:
            print('''如果您已知某些对局不存在，请在下方输入它们的对局序号组成的列表。输入空字符串以跳过此步骤。输入“0”以返回上一步。\nIf you already know that some matches don't exist, please provide them here. Submit an empty string to skip this step. Submit "0" to return to the last step.''')
            while True:
                matchIds_not_found_str: str = input()
                if matchIds_not_found_str == "":
                    matchIds_not_found = set()
                    break
                elif matchIds_not_found_str[0] == "0":
                    step -= 2
                    break
                else:
                    try:
                        tmp = eval(matchIds_not_found_str)
                    except:
                        print("语法错误！请重新输入。\nSyntax ERROR! Please try again.")
                    else:
                        if isinstance(tmp, Iterable) and all(map(lambda x: isinstance(x, int), tmp)):
                            matchIds_not_found = set(tmp)
                            break
                        else:
                            print("格式错误！请重新输入。\nFormat ERROR! Please try again.")
        elif step == 5:
            prepared = True
            break
        else:
            print("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
        step += 1
    if prepared:
        await binary_search_match(connection, start_matchId = start_matchId, end_matchId = end_matchId, func_str = func_str, product = product, matchIds_not_found = matchIds_not_found)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await print_summoner_info(connection)
    print("请选择一个选项：\nPlease select an option:\n0\t退出程序（Exit the program）\n1\t遍历对局序号（Traverse matchIds）\n2\t二分查找对局（Binary search for a match）")
    while True:
        option: str = input()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] == "1":
            print("请选择一个遍历模式：\nPlease select a traversal mode:\n1\t按对局序号遍历（By gameId）\n2\t按对局记录遍历（By match history）")
            while True:
                mode: str = input()
                if mode == "":
                    continue
                elif mode[0] == "1":
                    await index_traversal_main(connection)
                elif mode[0] == "2":
                    await history_traversal_main(connection)
                break
            break
        elif option[0] == "2":
            await binary_search_main(connection)
            break
        else:
            print("请选择一个选项：\nPlease select an option:\n0\t退出程序（Exit the program）\n1\t遍历对局序号（Traverse matchIds）\n2\t二分查找对局（Binary search for a match）")

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
