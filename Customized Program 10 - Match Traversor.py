from lcu_driver import Connector
from lcu_driver.connection import Connection
import argparse, json, keyboard, os, random, time
from typing import Any, Callable, Optional
from typing_extensions import Literal
from src.utils.logger import LogManager
from src.utils.webRequest import SGPSession
from src.utils.patch import Patch
from src.utils.summoner import get_summoner_data
from src.core.dataframes.matchHistory import get_game_info_sgp, get_game_timeline_sgp

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
# 更新（Last update）：     2026/02/03
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
def acquire_matchId_limit(start_matchId: Optional[int] = None, end_matchId: Optional[int] = None, func: Optional[Callable[[dict[str, Any]], bool]] = None) -> tuple[int, int]: #处理命令行和函数传入的变量（Handle the arguments passed from cmdline and a function）
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

async def search_match(connection: Connection, start_matchId: Optional[int] = None, end_matchId: Optional[int] = None, func: Optional[Callable[[dict[str, Any]], bool]] = None, product: Optional[Literal["LoL", "TFT"]] = None) -> int:
    '''
    在给定对局上下限的情况下，遍历范围内的对局，并保存所有符合条件的对局信息和时间轴。<br>Given the starting and ending matchIds, traverse save information and timeline of matches that meet the condition.
    
    :param connection: 连接对象。一般在程序中已指定好。<br>A Connection object. Usually specified in the program.
    :type connection: lcu_driver.connection.Connection
    :param start_matchId: 起始对局序号。<br>Starting matchId.
    :type start_matchId: int
    :param end_matchId: 终止对局序号。<br>Ending matchId.
    :type end_matchId: int
    :param func: 判断条件函数，给定对局序号的情况下返回其是否符合条件。<br>A condition judgment function that returns whether a matchId meets the condition.
    :type func: Callable[[dict[str, Any]], bool]
    :return: 状态码。<br>Status code.
    :rtype: int
    '''
    #参数预处理（Parameter preprocess）
    start_matchId, end_matchId = acquire_matchId_limit(start_matchId, end_matchId)
    if start_matchId == -1 and end_matchId == -1:
        return -1
    if func == None:
        print("未指定条件函数。将保存所有有效的对局信息和时间轴。\nNo condition function specified. All valid match information and timeline will be saved.")
        func = lambda x: "metadata" in x and "json" in x
    #变量和会话初始化（Variable and session initialization）
    if product == None:
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
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    log_filename: str = f"Matches on {platformId} {start_matchId}-{end_matchId}.log"
    json_folder: str = "日志（Logs）/对局遍历器"
    os.makedirs(json_folder, exist_ok = True)
    if not os.path.exists(log_filename):
        with open(log_filename, "w", encoding = "utf-8") as fp: #因为要追加写，所以要先创建这个文件（To append content, this file must be created previously）
            pass
    log: LogManager = LogManager(path = log_filename, mode = "a+", encoding = "utf-8")
    logPrint = log.logPrint
    session.setLog(log)
    logPrint(f"正在查询{platformId}服务器的对局……\nSearching matches on server {platformId} ...")
    logPrint(f"【参数设置】本次查询的对局序号范围（matchId range for this query）：[{start_matchId}, {end_matchId}]")
    #查询前的数据结构准备（Data structure prepared for query）
    matches_found: list[int] = []
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
                #下面将json文件保存到日志文件夹中（The following code save the json files into the log folder）
                match_product: str = game_info["metadata"]["product"]
                json1name: str = f"Match Information ({match_product}) - {platformId}-{matchId}.json"
                json2name: str = f"Match Timeline ({match_product}) - {platformId}-{matchId}.json"
                with open(os.path.join(json_folder, json1name), "w", encoding = "utf-8") as fp:
                    json.dump(game_info, fp, indent = 4, ensure_ascii = False)
                status, game_timeline = await get_game_timeline_sgp(connection, session, match_id, checkLoL = checkLoL, checkTFT = checkTFT)
                if status == 200:
                    with open(os.path.join(json_folder, json2name), "w", encoding = "utf-8") as fp:
                        json.dump(game_timeline, fp, indent = 4, ensure_ascii = False)
            else:
                logPrint(f"【跳过对局】[{currentProcess}/{gameCount}]对局{matchId}不符合条件。\nMatch {matchId} doesn't meet the requirements.", print_time = True)
    #保存数据到本地文件（Saved data to a local file）
    print(matches_found)
    print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
    print('共找到%d场对局！对局序号已保存到%s。\nMatches found: %d. MatchIDs have been saved into %s.' %(len(matches_found), log_filename, len(matches_found), log_filename))
    log.write("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())))
    log.write("【结果】共找到%d场对局。\nFound %d match(es).\n" %(len(matches_found), len(matches_found)))
    logPrint("符合条件的对局如下：\nMatches that fit the requirements are as follows:")
    for matchId in matches_found:
        logPrint(matchId)
    log.write("列表形式（List）：\n" + str(matches_found))
    log.close()
    return 0

async def binary_search_match(connection: Connection, start_matchId: Optional[int] = None, end_matchId: Optional[int] = None, func: Optional[Callable[[dict[str, Any]], bool]] = None, matchIds_not_found: Optional[set[int]] = None, product: Literal["LoL", "TFT"] = "LoL") -> int:
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
    :param func: 判断条件函数，给定对局序号的情况下返回其是否符合条件。<br>A condition judgment function that returns whether a matchId meets the condition.
    :type func: Callable[[dict[str, Any]], bool]
    :param matchIds_not_found: 通过事先指定不存在的对局序号，减少请求次数。在某个阶段提示后半部分无可用对局时，用户中断程序后重新运行的情形下非常好用。<br>Decrease the number of requests by specifying the matchIds of matches that don't exist in advance. Especially useful when the program gives a hint that "No match found in latter half", then the user interrupts the program and runs it again.
    :type matchIds_not_found: set[int]
    :return: 符合条件的最小对局序号。<br>The smallest matchId that fits the condition.
    :rtype: int
    '''
    #参数预处理（Parameter preprocess）
    start_matchId, end_matchId = acquire_matchId_limit(start_matchId, end_matchId)
    if start_matchId == -1 and end_matchId == -1:
        return -1
    if func == None:
        print("请指定一个条件函数。\nPlease specify a condition function.")
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
    #首先检查目标对局序号是否会落在所指定的对局序号范围中（First, check whether the target matchId will fall within the specified matchId range）
    logPrint("正在递减查找起始对局……\nSearching for an available starting match by decrement ...")
    while True:
        print(start_matchId, end = "\r")
        match_id: str = f"{platformId}_{start_matchId}"
        status, game_info = await get_game_info_sgp(connection, session, match_id, skipTFT = skipTFT, verbose = False)
        if status == 404:
            start_matchId -= 1
        else:
            traversed_matchIds[start_matchId] = func(game_info)
            if func(game_info):
                logPrint(f"起始对局序号{start_matchId}已符合条件。请尝试更改条件或者换用一个更小的起始对局序号。\nThe starting matchId {start_matchId} already meets the demands. Please try again with another condition or a smaller `start_matchId`.")
                return -1
            else:
                break
    logPrint("正在递增查找终止对局……\nSearching for an available ending match by increment ...")
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
                logPrint(f"终止对局序号{end_matchId}不符合条件。请尝试更改条件或者换用一个更大的终止对局序号。\nThe ending matchId {end_matchId} doesn't meet the demands. Please try again with another condition or a bigger `end_matchId`.")
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

#在这里自定义用于对局遍历函数的判断条件函数（Define the custom condition judgment conditions for `search_match` function hereafter）
##示例（Examples）
def isKiwiMatch(game_info: dict[str, Any]) -> bool:
    return game_info["metadata"]["product"] == "LoL" and game_info["json"]["gameMode"] == "KIWI"

#在这里自定义用于二分查找对局函数的判断条件函数（Define the custom condition judgment conditions for `binary_search_match` function hereafter）
##调试（Debug）
def condition_debug(game_info: dict[str, Any]) -> bool:
    return game_info["json"]["gameId"] >= 8502294282

##示例（Examples）
def first_match_after_mainteinance(game_info: dict[str, Any]) -> bool:
    return game_info["json"].get("endOfGameResult", "") != "Abort_Unexpected" and Patch(game_info["json"]["gameVersion"]) >= Patch("16.5")

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await get_summoner_data(connection)
    # await search_match(connection, start_matchId = 4524116001, end_matchId = 4524406763, func = None, product = None)
    await binary_search_match(connection, 4524891249, 4524988488, first_match_after_mainteinance, product = "LoL")

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
