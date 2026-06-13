from lcu_driver import Connector
from lcu_driver.connection import Connection
import json, os, pandas, requests, time
from typing import Any, Literal, Optional
from src.utils.webRequest import SGPSession
from src.utils.format import format_df
from src.core.config.localization import gamemaps, gamemodes, gameTypes_history
from src.core.dataframes.matchHistory import get_game_summary_sgp, get_game_timeline_sgp
from src.core.process.replay import download_replay

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 更新（Last update）：     2026/06/13
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

sgpSession: SGPSession = SGPSession()
gameQueues: dict[int, dict[str, Any]] = {}
connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 通过SGP API下载回放（Download replays through SGP API）
#-----------------------------------------------------------------------------
async def prepare_data_resources(connection: Connection) -> None:
    '''
    准备全局数据资源。<br>Prepare global data resources.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    global gameQueues
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gameQueues = {queue["id"]: queue for queue in gameQueues_source}

def sort_match_metadata(data: dict[str, Any], product: str, info_type: Literal["summary", "details"]) -> dict[str, Any]:
    '''
    梳理一场对局的游戏模式、对局持续时长等元数据。<br>Sort out a match's metadata like game mode and duration.
    
    :param data: 对局信息。可以是对局概要或者时间轴。<br>Match information, which may be match summary or timeline.
    
        对局概要可以通过以下SGP接口获取：<br>Match summary can be obtained through the following SGP endpoint:
        - `GET /match-history-query/v3/product/{product}/matchId/{match_id}/summary`
        
        对局时间轴可以通过以下SGP接口获取：<br>Match timeline can be obtained through the following SGP endpoint:
        - `GET /match-history-query/v3/product/{product}/matchId/{match_id}/details`
    :type data: dict[str, Any]
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）
    :type product: Literal["LoL", "TFT"]
    :param info_type: 信息类型。表明`data`属于什么信息。<br>Information type. Indicates what kind of information `data` is.
    
        - summary: 对局概要（Match summary）
        - details: 对局时间轴（Match timeline）
    :type info_type: Literal["summary", "details"]
    :return: 元数据。<br>Metadata.
    :rtype: dict[str, Any]
    '''
    result: dict[str, Any] = {"gameId": data["gameId"]}
    if product == "LoL":
        if info_type == "summary":
            #对局版本（Game version）
            gameVersion: str = data["gameVersion"]
            result["gameVersion"] = gameVersion
            #游戏模式（Game mode）
            queueId: int = data["queueId"]
            if queueId in gameQueues:
                gameModeName: str = gameQueues[queueId]["name"]
            else:
                gameModeName = gamemodes[data["gameMode"]]["zh_CN"]
            result["gameModeName"] = gameModeName
            #地图序号（MapId）
            mapId: int = data["mapId"]
            mapName: str = "%s（%s）" %(gamemaps[mapId]["zh_CN"], gamemaps[mapId]["en_US"])
            if mapId == 12:
                if "mapskin_ha_crepe" in data["gameModeMutators"]:
                    mapName = "进步之桥（Bridge of Progress）"
                elif "mapskin_map12_bloom" in data["gameModeMutators"]:
                    mapName = "莲华栈桥（Koeshin's Crossing）"
                elif "mapskin_ha_bilgewater" in data["gameModeMutators"]:
                    mapName = "屠夫之桥（Butcher's Bridge）"
                else:
                    mapName = "嚎哭深渊（Howling Abyss）"
            result["map"] = mapName
            #游戏类型（Game type）
            gameType: str = gameTypes_history[data["gameType"]]
            result["gameType"] = gameType
            #对局创建时间戳（Game creation）
            gameCreation: int = data["gameCreation"]
            gameCreationTime: str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(gameCreation / 1000))
            result["gameCreationDate"] = gameCreationTime
            #持续时间（Game duration）
            gameDuration: int | float = data["gameDuration"]
            gameDuration_norm: str = "%d:%02d" %(gameDuration // 60, gameDuration % 60)
            result["gameDuration"] = gameDuration_norm
        elif info_type == "details":
            #对局结束时间戳（Game end timestamp）
            gameEnd = data["frames"][-1]["events"][-1]["realTimestamp"] #正常对局的最后一个记录帧的最后一个事件必定是“GAME_END”（The last event of the last participant frame of a normal game must be "GAME_END"）
            gameEndTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(gameEnd / 1000))
            result["gameEndTime"] = gameEndTime
            #持续时间（Game duration）
            gameDuration = data["frames"][-1]["events"][-1]["timestamp"] / 1000
            gameDuration_norm = "%d:%02d" %(gameDuration // 60, gameDuration % 60)
            result["gameDuration"] = gameDuration_norm
    else:
        if info_type == "summary":
            #对局版本（Game version）
            gameVersion: str = data["game_version"]
            result["gameVersion"] = gameVersion
            #游戏模式（Game mode）
            queueId: int = data["queue_id"]
            if queueId in gameQueues:
                gameModeName: str = gameQueues[queueId]["name"]
            else:
                gameModeName = "云顶之弈"
            result["gameModeName"] = gameModeName
            #地图序号（MapId）
            result["map"] = "聚点危机（Convergence）"
            #游戏类型（Game type）
            gameType: str = data["tft_game_type"]
            result["gameType"] = gameType
            if "gameCreation" in data:
                #对局创建时间戳（Game creation）
                gameCreation: int = data["gameCreation"]
                gameCreationTime: str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(gameCreation / 1000))
                result["gameCreationDate"] = gameCreationTime
            #持续时间（Game duration）
            gameDuration: int | float = data["game_length"]
            gameDuration_norm: str = "%d:%02d" %(gameDuration // 60, gameDuration % 60)
            result["gameDuration"] = gameDuration_norm
    return result

async def replayDownloader(connection: Connection, matchId: int) -> None:
    '''
    下载一场回放。<br>Download a replay.
    
    该功能支持下载他人的私密回放，以及客户端内已失效但数据库中尚存的回放。<br>This function supports downloading other summoner's private replay and those which have expired in League Client but still exists in the database.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param matchId: 对局序号。<br>MatchId.
    
        仅可下载英雄联盟对局的回放。<br>Only the replay of a LoL match can be downloaded.
    :type matchId: int
    '''
    #准备常量（Prepare constants）
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId: str = current_party["platformId"]
    match_id: str = f"{platformId}_{matchId}"
    rofl_name: str = f"{platformId}-{matchId}.rofl"
    # json_name: str = f"{platformId}-{matchId}.json"
    # text_name: str = f"{platformId}-{matchId}.txt"
    replay_folder: str = await (await connection.request("GET", "/lol-replays/v1/rofls/path")).json()
    rofl_path: str = os.path.join(replay_folder, rofl_name).replace("\\", "/")
    replay_metadata_header: dict[str, Any] = {"gameId": "对局序号", "gameVersion": "对局版本", "gameModeName": "游戏模式", "map": "地图", "gameType": "游戏类型", "gameCreationDate": "对局创建时间", "gameDuration": "持续时间", "gameEndTime": "对局结束时间", "tags": "标签"}
    #首先确定对局序号属于英雄联盟还是云顶之弈（First, determine whether the match is LoL or TFT）
    summary_got: bool = False #指示是否获取到对局概要（Indicates whether match summary is fetched）
    timeline_got: bool = False #指示是否获取到对局时间轴。仅当对局概要获取失败时，这个变量才有可能为真（Indicates whether match timeline is fetched. Only when match summary failed to be fetched may this variable become True）
    game_summary: dict[str, Any] = {}
    game_timeline: dict[str, Any] = {}
    status, game_summary = await get_game_summary_sgp(connection, sgpSession, match_id, skipTFT = True, endpoint_version = 3)
    if status == 200:
        summary_got = True
        product: str = "TFT" if game_summary["mapId"] == 22 else "LoL"
    else: #黑色玫瑰大区对局序号为8595461971的对局的概要损坏，但是时间轴正常。这是一把瑞天帝（The summary of match HN10-8595461971 is corrupted, but the timeline is fine. This is a match of Ryze, the god）
        product = "LoL" #如果正常获取时间轴信息，则该对局一定是一场英雄联盟对局，因为云顶之弈对局没有时间轴；如果时间轴信息获取失败，那么在无法获取对局产品名的情况下，默认设置为英雄联盟（If the timeline information is successfully fetched, then this match must be a LoL match, because TFT games don't have timeline data. If the timeline information fails to be fetched, then the product can't be determined and thus set as the default value - LoL）
        status, game_timeline = await get_game_timeline_sgp(connection, sgpSession, match_id, checkTFT = False, endpoint_version = 3)
        if status == 200:
            timeline_got = True
    # if product == "":
    #     print("无法确定对局产品名。请手动指定。\nCan't determine the product of the match. Please specify it manually.\n0\t返回上一层（Return to the last step）\n☆1\t英雄联盟（LoL）\n!2\t云顶之弈（TFT）")
    #     while True:
    #         choice: str = input()
    #         if choice == "":
    #             choice = "1"
    #         if choice[0] == "0":
    #             return
    #         elif choice[0] == "1":
    #             product = "LoL"
    #             break
    #         elif choice[0] == "2":
    #             product = "TFT"
    #             break
    #         else:
    #             print("您的输入有误！请重新输入。\nERROR input! Please try again.")
    #发送请求并处理响应（Send the request and handle the response）
    if product.lower() == "lol":
        product = "LoL"
    elif product.lower() == "tft":
        product = "TFT"
    replay_downloaded, replay_download_message = await download_replay(connection, sgpSession, match_id, rofl_path, product = product)
    if replay_downloaded:
        print(f"已下载回放（Downloaded replay）： {rofl_path}")
        if summary_got:
            metadata: dict[str, Any] = sort_match_metadata(game_summary, product, "summary")
        elif timeline_got:
            metadata = sort_match_metadata(game_timeline, product, "details")
        else:
            metadata = {}
        if len(metadata) > 0:
            metadata_organized: dict[str, list[Any]] = {key: [replay_metadata_header[key], value] for (key, value) in metadata.items()}
            metaDf: pandas.DataFrame = pandas.DataFrame(metadata_organized, index = ["中文", "Value"])
            metaDf = metaDf.transpose()
            print(f"回放元数据（Replay metadata）：")
            print(format_df(metaDf, print_index = True, reserve_index = True)[0], end = "\n\n")
    else:
        print(replay_download_message)
        print("下载失败。\nDownload failed.")

async def set_replay_folder(connection: Connection) -> str:
    '''
    设置回放的下载目录。<br>Set the download directory of replays.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :return: 新下载目录。<br>New download directory.
    :rtype: str
    '''
    #参数设置（Parameter configuration）
    old_replay_folder: str = await (await connection.request("GET", "/lol-replays/v1/rofls/path")).json()
    old_replay_settings: Optional[dict[str, Any]] = await (await connection.request("GET", "/lol-settings/v2/local/lol-replays")).json()
    schemaVersion: int = 0
    if bool(old_replay_settings) and "schemaVersion" in old_replay_settings:
        schemaVersion = old_replay_settings["schemaVersion"]
    print(f"旧回放位置（Old replays location）：\n{old_replay_folder}")
    print("请输入新的回放位置：（输入空字符串以放弃修改。）\nPlease input the new replays location: (Submit an empty string to cancel.)")
    while True:
        new_replay_folder: str = input()
        if new_replay_folder == "":
            return old_replay_folder
        elif os.path.exists(new_replay_folder):
            if os.path.isdir(new_replay_folder):
                break
            else:
                print("您输入的路径不是一个文件夹！请重新输入。\nThe path you input isn't a folder! Please try again.")
        else:
            os.makedirs(new_replay_folder)
            print("已创建文件夹。\nCreated the folder.")
            break
    new_replay_folder = os.path.abspath(new_replay_folder).replace("\\", "/") #标准化路径（Standardize the path）
    #发送请求和处理响应（Send the request and handle the response）
    settingsResource: dict[str, Any] = {"data": {"replays-folder-path": new_replay_folder}, "schemaVersion": schemaVersion}
    response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-settings/v2/local/lol-replays", data = settingsResource)).json()
    print(response)
    if response == None:
        print("回放位置更新成功。正在扫描当前文件夹下的所有回放文件。\nReplays location is updated successfully. Scanning all replays in this folder ...")
    else:
        print("回放位置更新失败。\nFailed to update replays location.")
    current_replay_folder: str = await (await connection.request("GET", "/lol-replays/v1/rofls/path")).json()
    print(f"当前回放位置（Current replays location）：\n{current_replay_folder}")
    return current_replay_folder

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    global sgpSession
    await prepare_data_resources(connection)
    await sgpSession.init(connection)
    sgpSession.verbose = False
    print("请选择一个操作：\nPlease select an operation:\n0\t退出程序（Exit the program）\n1\t设置回放位置（Set replays location）\n2\t下载回放（Download replay）")
    while True:
        option: str = input()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] == "1":
            await set_replay_folder(connection)
        elif option[0] == "2":
            print('请输入要下载的对局的序号：（输入“0”以返回上一层。）\nPlease input the gameId of the match you want to download: (Submit "0" to return to the last step.)')
            while True:
                matchId_str: str = input()
                if matchId_str == "":
                    continue
                elif matchId_str[0] == "0":
                    break
                elif matchId_str.isdecimal():
                    matchId: int = int(matchId_str)
                    await replayDownloader(connection, matchId)
                else:
                    print("请输入一个正整数。\nPlease input a positive integer.")
                print('请输入要下载的对局的序号：（输入“0”以返回上一层。）\nPlease input the gameId of the match you want to download: (Submit "0" to return to the last step.)')
        else:
            print("您的输入有误！请重新输入。\nERROR input! Please try again.")
        print("请选择一个操作：\nPlease select an operation:\n0\t退出程序（Exit the program）\n1\t设置回放位置（Set replays location）\n2\t下载回放（Download replay）")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
