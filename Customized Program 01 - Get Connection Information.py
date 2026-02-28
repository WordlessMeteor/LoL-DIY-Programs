from lcu_driver import Connector
from lcu_driver.connection import Connection
from typing import Any

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/01/31
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 自定义函数（DIY Function）
#-----------------------------------------------------------------------------
async def get_connection_data(connection: Connection) -> None:
    current_summoner: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    print("连接信息如下：\nConnection information is as follows:")
    print("address: ", connection.address)
    print("auth_key: ", connection.auth_key)
    print("displayName: ", current_summoner["displayName"])
    print("gameName: ", current_summoner["gameName"])
    print("tagLine: ", current_summoner["tagLine"])
    print("installation_path: ", connection.installation_path)
    print("pid: ", connection.pid)
    print("port: ", connection.port)
    print("protocols: ", connection.protocols)
    print("puuid: ", current_summoner["puuid"])
    print("summonerId: ", current_summoner["summonerId"])
    print("ws_address: ", connection.ws_address)
    print()
    print("请按回车键退出……\nPress Enter to exit ...")
    input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await get_connection_data(connection)

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
