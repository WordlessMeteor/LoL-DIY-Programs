from lcu_driver import Connector
from lcu_driver.connection import Connection
import os, time
from typing import Any, Optional
from src.utils.summoner import get_summoner_data

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/02/09
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 快速启动云顶之弈对局（Quickly launch a TFT match）
#-----------------------------------------------------------------------------
async def RP_generator(connection: Connection) -> None:
    queue: dict[str, Any] = {"queueId": 1220}
    count: int = 1
    while True:
        create_lobby: dict[str, Any] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = queue)).json()
        print("create-lobby = %s. Times tried: %d" %(create_lobby, count))
        if "errorCode" in create_lobby:
            if create_lobby["message"] == "INVALID_LOBBY":
                print("请确认当前服务器云顶之弈发条鸟的试炼（队列序号：1220）可用！\nPlease ensure TFT Tocker's Trial (queueId: 1220) is available on current server!")
                time.sleep(5)
                return create_lobby["httpStatus"]
            elif create_lobby["message"] == "Gameflow prevented a lobby.":
                gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                if gameflow_phase != "None":
                    print(f"gameflow-phase = {gameflow_phase}")
                    print("您正在选择英雄或者游戏内！程序即将退出！\nYou're right now in champ select or game progress! The program will exit soon!")
                    time.sleep(5)
                    return create_lobby["httpStatus"]
        else:
            break
        count += 1
    #寻找对局（Find match）
    count = 1
    while True:
        start_game: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
        print("start-game = %s. Times tried: %d" %(start_game, count))
        if start_game == None:
            break
        elif count > 5000:
            print("请求超时！请检查网络连接和秒退计时器。\nRequest timeout! Please check the network and queue dodge timer.")
            time.sleep(5)
            os._exit(0)
        if start_game["message"] == "QUEUE_NOT_ENABLED":
            create_lobby = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = queue)).json()
            print("create-lobby = %s" %(create_lobby))
        count += 1
    #对局已找到（Match found）
    count = 1
    while True:
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        print("gameflow-phase = %s. Times tried: %d" %(gameflow_phase, count))
        if gameflow_phase == "ReadyCheck":
            break
        elif count > 5000:
            print("接受对局超时！请检查计算机运行状况。\nAccept match timeout! Please check your computer's running status.")
            time.sleep(5)
            os._exit(0)
        count += 1
    #接受对局（Accept）
    accept: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-matchmaking/v1/ready-check/accept")).json()
    print("match-accept = " + str(accept))
    #游戏中（In progress）
    while True:
        count += 1
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        print("gameflow-phase = %s. Times tried: %d" %(gameflow_phase, count))
        if gameflow_phase == "InProgress":
            break
        elif count >= 5000:
            print("启动游戏超时！请检查脚本和客户端运行状况。\nGame start timeout! Please check your program's and client's running status.")
            time.sleep(5)
            break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await get_summoner_data(connection)
    await RP_generator(connection)

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
