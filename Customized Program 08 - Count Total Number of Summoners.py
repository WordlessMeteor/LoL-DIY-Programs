from lcu_driver import Connector
from lcu_driver.connection import Connection
import json, keyboard, os, pandas, time
from typing import Any
from src.utils.format import addDefaultStyle, optimize_bool_display, create_workbook_win32
from src.utils.summoner import print_summoner_info, get_info
from src.utils.logger import LogManager
from src.utils.webRequest import SGPSession
from src.core.config.headers import info_header
from src.core.dataframes.matchHistory import get_matchSummary_sgp

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/04/11
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

summonerIcons: dict[int, dict[str, Any]] = {}
sgpSession: SGPSession = SGPSession()
log: LogManager = LogManager()

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 统计当前服务器的玩家数量（Count the number of players in the current server）
#-----------------------------------------------------------------------------
async def prepare_data_resources(connection: Connection) -> None:
    '''
    准备全局数据资源。<br>Prepare global data resources.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    global summonerIcons
    logPrint("正在加载召唤师图标信息……\nLoading summoner icon information ...")
    summonerIcons_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {int(summonerIcon_iter["id"]): summonerIcon_iter for summonerIcon_iter in summonerIcons_source}

async def generate_info_records(connection: Connection, info_data: dict[str, list[Any]], puuid: str) -> bool:
    '''
    向召唤师生涯数据中追加记录。<br>Append records into the summoner information data.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param info_data: 召唤师生涯数据。记录将追加到其中。<br>Summoner information data. Records are appended into it.
    :type info_data: dict[str, list[Any]]
    :param puuid: 要查询的召唤师的玩家通用唯一识别码。<br>Puuid of the summoner to query.
    :type puuid: str
    :return: 是否成功获取该召唤师的信息。<br>Whether the summoner information is successfully fetched.
    :rtype: bool
    '''
    #设置召唤师信息获取的异常处理机制（Set the exception handling mechanism for getting summoner information）
    info_recapture: int = 0
    info: dict[str, Any] = await get_info(connection, puuid)
    while not info["info_got"] and info["body"]["httpStatus"] != 404 and info_recapture < 3:
        # logPrint(info["message"])
        info_recapture += 1
        # logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) apture failed! Recapturing this player's information ... Times tried: %d." %(puuid, info_recapture, puuid, info_recapture))
        info = await get_info(connection, puuid)
    if info["info_got"]:
        info_body: dict[str, Any] = info["body"]
        info_header_keys: list[str] = list(info_header.keys())
        for i in range(len(info_header_keys)):
            key: str = info_header_keys[i]
            if i <= 16:
                if i >= 15: #召唤师图标相关键（Profile icon related keys）
                    profileIconId: int = info_body["profileIconId"]
                    if profileIconId in summonerIcons:
                        to_append: Any = summonerIcons[profileIconId].get(key.split("_")[1])
                    else:
                        to_append = ""
                else:
                    to_append = info_body[key]
            else:
                to_append = info_body["rerollPoints"][key]
            info_data[key].append(to_append)
        return True
    else:
        # logPrint(info["message"])
        # logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) capture failed!" %(puuid, puuid))
        return False

async def interaction_traverse_summoner(connection: Connection, export: bool = True) -> tuple[pandas.DataFrame, dict[tuple[str, str], dict[str, int]]]:
    '''
    通过人物关系来遍历一个服务器上的所有召唤师。<br>Traverse as many summoners as possible in a server through human interactions.
    
    人物关系主要是对局记录。对于用户自身来说，还包括好友关系。<br>Basically, an interaction refers to two players being in the same match. It may also include the friendship when it comes to the user itself.
    
    :param export: 是否导出召唤师身份信息和互作关系数据。默认为真。<br>Whether to export summoner information and interaction data. True by default.
    :type export: bool
    :return: 本次遍历到的所有召唤师的身份信息数据框，以及不同召唤师之间两两的关系。<br>A dataframe of information of all summoners obtained after this traversal, together with a relationship dictionary between each pair of summoners.
    
        每两个召唤师之间可存在对战关系和好友关系。<br>Each pair of summoners can have a relationship of "game" or "friend" type.
        
            - 对战关系的数值代表两个召唤师同时在多少场对局中出现。<br>The value of a gameship represents how many games these two summoners simultaneously appear in.
            - 好友关系的数值恒为1。<br>The value of a friendship is always 1.
    :rtype: tuple[pandas.DataFrame, dict[tuple[str, str], dict[str, Any]]]
    '''
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_puuid: str = current_info["puuid"]
    #获取起始召唤师（Get an initial summoner）
    logPrint('''请输入起始召唤师名称。输入“0”以退出程序。\nPlease submit the starting summoner's name. Submit "0" to exit the program.''')
    main_info_body: dict[str, Any] = {}
    while True:
        main_info_got: bool = False
        summoner_name: str = logInput()
        if summoner_name == "0":
            return (pandas.DataFrame(), {})
        elif summoner_name == "":
            continue
        else:
            info: dict[str, Any] = await get_info(connection, summoner_name)
            if not info["info_got"]:
                logPrint(info["message"])
            else:
                main_info_body: dict[str, Any] = info["body"]
                main_info_got = True
                break
    #初始化返回结果（Initialize the result to return）
    interactions: dict[tuple[str, str], dict[str, Any]] = {}
    #初始化队列（Initialize a queue）
    queue: list[str] = [current_puuid] #存储等待查询的玩家的玩家通用唯一识别码Store the puuid of the players to search for）
    logPrint("×\t%s\tself\t%d" %(current_puuid, len(queue)))
    searched_puuids: set[str] = set() #存储已经查询过对局记录的玩家的玩家通用唯一识别码，防止二次查询（Store the puuids of the players that have been searched match history before, in case a summoner would be looked up twice）
    searched_matchIds: set[int] = set() #存储已经查询过的对局序号。通过不同的召唤师可能查询到相同对局，需要避免互作关系的二次添加（Store the id of the matches that have been searched before. The same match might exist among different summoners, so here we need to avoid same interactions being added twice）
    #初始化数据结构（Initialize the data structure）
    info_header_keys: list[str] = list(info_header.keys())
    info_data: dict[str, list[Any]] = {key: [] for key in info_header_keys}
    #先添加好友信息（First, add friend information and interactions）
    if main_info_got:
        puuid_initial: str = main_info_body["puuid"]
        if puuid_initial == current_puuid:
            logPrint("正在加载好友信息……\nLoading friends ...")
            friends: list[dict[str, Any]] | dict[str, Any] = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
            if isinstance(friends, dict) and "errorCode" in friends:
                logPrint(friends)
                if friends["errorCode"] == 503 and friends["message"] == "not connected to RC chat yet":
                    logPrint("客户端尚未连接到聊天服务。如果这个问题持续存在，请重新登录客户端后再重新运行此脚本。\nNot connected to RC client yet. If this problem persists, please relog in and then rerun this program.")
                    return (pandas.DataFrame(), interactions)
                else:
                    logPrint("好友列表获取失败。程序将跳过好友。\nFailed to get the friend list. Friends will be skipped.")
                    friends = []
            for friend in friends:
                friend_puuid: str = friend["puuid"]
                queue.append(friend_puuid) #入队（Enqueue）
                logPrint("×\t%s\tfriend\t%d" %(friend_puuid, len(queue))) #遵循磁场的叉进点出标识法（Follow the convention of magnetics, where a cross means something enters something, while a dot means something escapes from something）
                interaction_key: tuple[str, str] = (min(current_puuid, friend_puuid), max(current_puuid, friend_puuid))
                interactions[interaction_key] = {"puuid1": interaction_key[0], "puuid2": interaction_key[1], "weight": {"friend": 1}} #导出到json时元组不能作为键，因此将元组中的信息等价保存到值中（When the data is exported to a json file, the key can't be a tuple, so here we save the information into the value in a lossless manner）
    #然后，逐个取队列中的玩家通用唯一识别码，获取其信息，并分析对局记录中的互作关系（Then, pop the puuid from queue, get the corresponding summoner information and analyze the interaction in the match history）
    while len(queue) > 0:
        if keyboard.is_pressed("esc"):
            logPrint("您已中断遍历过程。\nYou've cancelled the traversal.")
            break
        player_puuid: str = queue.pop(0) #出队（Dequeue）
        logPrint("·\t%s\tpop\t%d" %(player_puuid, len(queue)))
        info_got: bool = await generate_info_records(connection, info_data, player_puuid)
        # if not info_got:
        #     logPrint(f"获取玩家{player_puuid}信息的过程出现了一个异常。\nAn error occurred when the program was trying to get the information of the summoner with puuid {player_puuid}.")
        searched_puuids.add(player_puuid) #即使没有正确获取到其召唤师信息，在程序的下游也不再获取了（Even if the summoner information isn't fetched as expected, it won't be fetched subsequently）
        LoLHistory_get, LoLHistory = await get_matchSummary_sgp(connection, sgpSession, player_puuid, product = "LoL", log = log)
        if LoLHistory_get:
            for game in LoLHistory["games"]:
                match_id: str = game["metadata"]["match_id"]
                matchId: int = int(match_id.replace(f"{platformId}_", ""))
                if not matchId in searched_matchIds:
                    participant_puuids: list[str] = game["metadata"].get("participants", [])
                    for i in range(len(participant_puuids)):
                        puuid1: str = participant_puuids[i]
                        for j in range(i + 1, len(participant_puuids)):
                            puuid2: str = participant_puuids[j]
                            interaction_key = (min(puuid1, puuid2), max(puuid1, puuid2))
                            if interaction_key in interactions:
                                if "lol" in interactions[interaction_key]["weight"]:
                                    interactions[interaction_key]["weight"]["lol"] += 1
                                else:
                                    interactions[interaction_key]["weight"]["lol"] = 1
                            else:
                                interactions[interaction_key] = {"puuid1": interaction_key[0], "puuid2": interaction_key[1], "weight": {"lol": 1}}
                    diff_puuids: list[str] = list(set(participant_puuids) - set(searched_puuids) - set(queue))
                    if len(diff_puuids) > 0:
                        queue += diff_puuids #批量入队（Batch enqueue）
                        logPrint("×\t%s\tlol\t%d" %(queue[-1], len(queue))) #批量入队时，打印最后一个入队的玩家通用唯一识别码（When batch enqueue is performed, print the puuid that enters the queue in the end）
        else:
            logPrint(LoLHistory)
        TFTHistory_get, TFTHistory = await get_matchSummary_sgp(connection, sgpSession, player_puuid, product = "TFT", log = log)
        if TFTHistory_get:
            for game in TFTHistory["games"]:
                match_id: str = game["metadata"]["match_id"]
                matchId: int = int(match_id.replace(f"{platformId}_", ""))
                if not matchId in searched_matchIds:
                    participant_puuids: list[str] = game["metadata"].get("participants", []) #部分早期的云顶之弈对局的元数据无“participants”键（The early TFT match metadata doesn't have "participants" key）
                    for i in range(len(participant_puuids)):
                        puuid1: str = participant_puuids[i]
                        for j in range(i + 1, len(participant_puuids)):
                            puuid2: str = participant_puuids[j]
                            interaction_key = (min(puuid1, puuid2), max(puuid1, puuid2))
                            if interaction_key in interactions:
                                if "tft" in interactions[interaction_key]["weight"]:
                                    interactions[interaction_key]["weight"]["tft"] += 1
                                else:
                                    interactions[interaction_key]["weight"]["tft"] = 1
                            else:
                                interactions[interaction_key] = {"puuid1": interaction_key[0], "puuid2": interaction_key[1], "weight": {"tft": 1}}
                    diff_puuids: list[str] = list(set(participant_puuids) - set(searched_puuids) - set(queue))
                    if len(diff_puuids) > 0:
                        queue += diff_puuids #批量入队（Batch enqueue）
                        logPrint("×\t%s\ttft\t%d" %(queue[-1], len(queue)))
        else:
            logPrint(TFTHistory)
    info_statistics_output_order: list[int] = [0, 1, 3, 2, 11, 12, 4, 9, 8, 6, 7, 15, 16, 10, 13, 14, 5, 19, 18, 17, 20, 21]
    info_data_organized: dict[str, list[Any]] = {info_header_keys[i]: info_data[info_header_keys[i]] for i in info_statistics_output_order}
    info_df: pandas.DataFrame = pandas.DataFrame(info_data_organized)
    optimize_bool_display(info_df)
    info_df = pandas.concat([pandas.DataFrame([info_header])[info_df.columns], info_df], ignore_index = True)
    if export:
        excel_name: str = f"Summoner Traversal on {platformId}.xlsx"
        if not os.path.exists(excel_name):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(excel_name))
        workbook_exist: bool = os.path.exists(excel_name)
        while True:
            try:
                with (pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(path = excel_name, mode = "w")) as writer:
                    addDefaultStyle(info_df).to_excel(excel_writer = writer)
            except PermissionError:
                logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                logInput()
            else:
                logPrint(f'本次遍历查询到的召唤师信息已保存到同目录下的“{excel_name}”。\nInformation of traversed summoners has been saved into "{excel_name}" under the same directory.')
                break
        with open("Interactions.json", "w", encoding = "utf-8") as fp:
            json.dump(list(interactions.values()), fp, indent = 4, ensure_ascii = False)
        logPrint('本次遍历汇总的召唤师互作关系数据已保存到同目录下的“Interactions.json”。\nSummoner interaction data summary by this traversal has been saved into "Interactions.json" under the same directory.')
    return (info_df, interactions)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection):
    global sgpSession, log, logInput, logPrint
    await sgpSession.init(connection)
    log_folder: str = "日志（Logs）/Customized Program 08 - Count Total Number of Summoners"
    os.makedirs(log_folder, exist_ok = True)
    currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log = LogManager(os.path.join(log_folder, currentTime + ".log"), mode = "a+", encoding = "utf-8")
    logInput = log.logInput
    logPrint = log.logPrint
    await print_summoner_info(connection)
    await prepare_data_resources(connection)
    info_df, interactions = await interaction_traverse_summoner(connection)

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
