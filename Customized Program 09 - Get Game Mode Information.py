from lcu_driver import Connector
from lcu_driver.connection import Connection
import os, pandas, time
from typing import Any
from src.utils.format import format_df, addDefaultStyle
from src.utils.summoner import print_summoner_info
from src.core.dataframes.gameMode import sort_queue_data, check_available_queue

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/03/12
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 获取游戏模式信息（Get game mode information）
#-----------------------------------------------------------------------------
async def gamemode(connection: Connection) -> None: #导出游戏模式信息到工作簿中（Export game mode information into a workbook）
    queues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    queue_df: pandas.DataFrame = sort_queue_data(queues_source)
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

async def print_available_queue(connection: Connection) -> None: #打印可用队列信息（Print available queues）
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    game_version: str = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    print("是否检查可用队列？（输入任意键检查，否则退出程序）\nDo you want to check available queues? (Submit anything to check, or null to exit the program)")
    check: bool = bool(input())
    if check:
        while True:
            availableQueue_df: pandas.DataFrame = await check_available_queue(connection)
            print("*****************************************************************************")
            print(format_df(availableQueue_df)[0])
            print("*****************************************************************************")
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
    await print_summoner_info(connection)
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
