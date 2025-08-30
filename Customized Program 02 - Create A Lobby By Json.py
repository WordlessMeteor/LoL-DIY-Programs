from lcu_driver import Connector
import os

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/08/27
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector = Connector()

#-----------------------------------------------------------------------------
# 获得召唤师数据（Get access to summoner data）
#-----------------------------------------------------------------------------
async def get_summoner_data(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    print("displayName:    %s" %(summoner["gameName"] + "#" + summoner["tagLine"]))
    print("summonerId:     %s" %(summoner["summonerId"]))
    print("puuid:          %s" %(summoner["puuid"]))
    print("-")


#-----------------------------------------------------------------------------
#  lockfile
#-----------------------------------------------------------------------------
async def update_lockfile(connection):
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'w+')
        text = "LeagueClient:%d:%d:%s:%s" %(connection.pid, connection.port, connection.auth_key, connection.protocols[0])
        file.write(text)
        file.close()
    return None

async def get_lockfile(connection):
    import os
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'r')
        text = file.readline().split(':')
        file.close()
        print(connection.address)
        print(f'riot    {text[3]}')
        return text[3]
    return None

#-----------------------------------------------------------------------------
# 创建训练模式 5V5 自定义房间（Create a Practice Tool lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    custom = {
        "queueId": 3140,
        "isCustom": True,
        "customGameLobby": {
            "lobbyName": "WordlessMeteor's Lobby",
            "lobbyPassword": "",
            "configuration": {
                "mapId": 11,
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
    response = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)).json()
    print(response)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await create_custom_lobby(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
