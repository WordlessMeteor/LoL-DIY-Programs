from lcu_driver import Connector
from lcu_driver.connection import Connection
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
# 创建训练模式 5V5 自定义房间（Create a Practice Tool lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection: Connection) -> None:
    custom: dict[str, Any] = {
        "queueId": 3140,
        "isCustom": True,
        "customGameLobby": {
            "lobbyName": "Custom Lobby",
            "lobbyPassword": "",
            "configuration": {
                "mapId": 11,
                "aramMapMutator": "MapSkin_HA_Bilgewater",
                "gameMode": "PRACTICETOOL",
                "gameTypeConfig": {
                    "id": 1
                },
                "spectatorPolicy": "AllAllowed",
                "teamSize": 5,
                "maxPlayerCount": 0,
                "gameServerRegion": "",
                "spectatorDelayEnabled": False,
                "hidePublicly": False
            }
        }
    }
    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)).json()
    print(response)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await get_summoner_data(connection)
    await create_custom_lobby(connection)

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
