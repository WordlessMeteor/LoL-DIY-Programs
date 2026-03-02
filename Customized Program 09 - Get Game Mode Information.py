from lcu_driver import Connector
from lcu_driver.connection import Connection
import os, pandas, time
from typing import Any
from src.utils.format import format_df, addDefaultStyle
from src.utils.summoner import get_summoner_data
from src.core.config.localization import gamemaps
from src.core.dataframes.gameMode import sort_queue_data

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/03/02
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector = Connector()

#-----------------------------------------------------------------------------
# 梳理可用队列（Sorts out available queues）
#-----------------------------------------------------------------------------
async def check_available_queue(connection: Connection) -> None:
    gameQueues: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    platform_config: dict[str, Any] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    map_CN: dict[int, str] = {mapId: gamemaps[mapId]["zh_CN"] for mapId in gamemaps}
    map_EN: dict[int, str] = {mapId: gamemaps[mapId]["en_US"] for mapId in gamemaps}
    pickmode_CN: dict[str, str] = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式", "QuickplayPickStrategy": "快速匹配", "": "待定"}
    pickmode_EN: dict[str, str] = {"AllRandomPickStrategy": "All Random", "SimulPickStrategy": "Blind Pick", "TeamBuilderDraftPickStrategy": "Draft Mode", "OneTeamVotePickStrategy": "Vote", "TournamentPickStrategy": "Tournament Draft", "QuickplayPickStrategy": "Quickplay", "": "Pending"}
    available_queues: dict[int, dict[str, Any]] = {}
    for queue in gameQueues:
        if queue["queueAvailability"] == "Available" or queue["id"] in platform_config["ClientSystemStates"]["enabledQueueIdsList"]:
            available_queues[queue["id"]] = queue
    queue_dict: dict[str, list[Any]] = {"queueID": [], "mapID": [], "map_CN": [], "map_EN": [], "gameMode": [], "pickType_CN": [], "pickType_EN": []}
    for queue in available_queues.values():
        queue_dict["queueID"].append(queue["id"])
        queue_dict["mapID"].append(queue["mapId"])
        queue_dict["map_CN"].append(map_CN[queue["mapId"]])
        queue_dict["map_EN"].append(map_EN[queue["mapId"]])
        queue_dict["gameMode"].append(queue["name"])
        queue_dict["pickType_CN"].append(pickmode_CN[queue["gameTypeConfig"]["pickMode"]])
        queue_dict["pickType_EN"].append(pickmode_EN[queue["gameTypeConfig"]["pickMode"]])
    queue_df: pandas.DataFrame = pandas.DataFrame(queue_dict)
    queue_df.sort_values(by = "queueID", inplace = True, ascending = True, ignore_index = True)
    print("*****************************************************************************")
    print(format_df(queue_df)[0])
    print("*****************************************************************************")

#-----------------------------------------------------------------------------
# 获取游戏模式信息（Get game mode information）
#-----------------------------------------------------------------------------
def lcuTimestamp(timestamp: int) -> str: #根据队列开放和关闭时间戳返回对局时间（Return the time according to the timestamp of queue opening and closure）
    min = timestamp // 60
    sec = timestamp % 60
    return str(min) + ":" + "{0:0>2}".format(str(sec))

async def gamemode(connection: Connection) -> None:
    queue_df: pandas.DataFrame = await sort_queue_data(connection)
    #下面设置覆盖写时添加的Sheet名称（The code here sets the Sheet name to be appended into the xlsx file with the same name）
    riot_client_info: list[str] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info: dict[str, str] = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region: str = client_info["--region"]
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    #locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
    locale: str = client_info["--locale"]
    version: str = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    version_df: pandas.DataFrame = pandas.DataFrame({"Patch": [version]})
    while True:
        try:
            with (pandas.ExcelWriter(path = "游戏队列信息.xlsx", mode = "a", if_sheet_exists = "overlay") if os.path.exists("游戏队列信息.xlsx") else pandas.ExcelWriter(path = "游戏队列信息.xlsx")) as writer:
                currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
                addDefaultStyle(queue_df).to_excel(excel_writer = writer, sheet_name = f"{currentTime} {platformId} {locale}")
                version_df.to_excel(excel_writer = writer, sheet_name = f"{currentTime} {platformId} {locale}", header = None, index = False, startcol = 0, startrow = 0)
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
            if input().startswith("0"):
                break
        else:
            break
    #要完整读取游戏队列信息，请使用命令（To read in the queue information entirely, it's highly recommended that user use the following command）：df = pandas.read_excel("游戏队列信息.xlsx", header = 0, index_col = 0)

async def print_available_queue(connection: Connection) -> None:
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    game_version: str = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    print("是否检查可用队列？（输入任意键检查，否则退出程序）\nDo you want to check available queues? (Submit anything to check, or null to exit the program)")
    check: bool = bool(input())
    if check:
        while True:
            await check_available_queue(connection)
            print("(" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\t" + platformId + "\t" + game_version + ")")
            print("是否刷新可用队列信息？（输入任意键不刷新，否则刷新）\nRefresh available queue information? (Submit anything to quit refreshing, or null to continue refreshing)")
            refresh: bool = bool(input())
            if refresh:
                break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await get_summoner_data(connection)
    print("是否导出游戏队列数据？（输入任意键不导出，否则导出）\nExport queue data? (Enter anything to refuse exporting, or null to export)")
    export: str = input()
    if export == "":
        await gamemode(connection)
    await print_available_queue(connection)

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
