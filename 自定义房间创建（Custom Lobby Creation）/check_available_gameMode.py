from lcu_driver import Connector
import os, time

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/05/07
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

gamemodes = ["ARAM", "ARSR", "ASCENSION", "ASSASSINATE", "BRAWL", "CHERRY", "CLASSIC", "CS", "DARKSTAR", "DOOMBOTSTEEMO", "FIRSTBLOOD", "GAMEMODEX", "HAWTHORN", "HEXAKILL", "KINGPORO", "MAKO_CLASSIC", "NEXUSBLITZ", "ODIN", "ODYSSEY", "ONEFORALL", "PRACTICETOOL", "PROJECT", "SIEGE", "SNOWURF", "STARGUARDIAN", "STRAWBERRY", "SWIFTPLAY", "TFT", "TUTORIAL", "TUTORIAL_MODULE_1", "TUTORIAL_MODULE_2", "ULTBOOK", "URF", "WIPMODEWIP", "WIPMODEWIP3", "WIPMODEWIP4"]

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
async def get_lockfile(connection):
    path = os.path.join(connection.installation_path.encode("gb18030").decode("utf-8"), "lockfile")
    if os.path.isfile(path):
        file = open(path, "r")
        text = file.readline().split(":")
        file.close()
        print(connection.address)
        print(f"riot    {connection.auth_key}")
        return connection.auth_key
    return None

#-----------------------------------------------------------------------------
# 检测自定义房间有效性（Check the availability of different custom lobbies）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    print("正在检查自定义房间有效性……\nChecking the abailability of different custom lobbies ...")
    global available_custom_game
    available_custom_game = []
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    for i in range(len(gamemodes)):
        for j in range(0, 100):
            custom = {
                "customGameLobby": {
                    "configuration": {
                        "gameMode": gamemodes[i],
                        "gameMutator": "",
                        "gameServerRegion": "",
                        "mapId": j,
                        "mutators": {
                            "id": 1
                        },
                    "spectatorPolicy": "AllAllowed",
                    "teamSize": 1
                    },
                    "lobbyName": summoner["gameName"] + "'s Game",
                    "lobbyPassword": ""
                },
                "isCustom": True
            }
            await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)
            bot = {"championId": 11, "botDifficulty": "RSINTERMEDIATE", "teamId": "200", "position": "TOP"}
            await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)
            time.sleep(0.1)
            data = await connection.request("GET", "/lol-lobby/v2/lobby")
            bot = await data.json()
            try:
                if bool(bot["gameConfig"]["customTeam200"]):
                    available_custom_game.append((gamemodes[i],j))
                    print(custom)
            except KeyError:
                print("游戏模式为%s、地图序号为%d的自定义房间不可用。\nThe lobby of gameMode %s and mapId %d isn't available."%(gamemodes[i], j, gamemodes[i], j))
    time.sleep(2)

#-----------------------------------------------------------------------------
# 检测队列房间有效性（Check the availability of different queue lobbies）
#-----------------------------------------------------------------------------
async def create_queue_lobby(connection):
    print("正在检查队列房间有效性……\nChecking the availability of different queue lobbies ...")
    global available_queueId
    available_queueId = []
    for queueId in range(10000):
        lobby = await connection.request("GET", "/lol-lobby/v2/lobby")
        lobby_information = await lobby.json()
        if "gameConfig" in lobby_information:
            prequeueId = lobby_information["gameConfig"]["queueId"]
        else:
            prequeueId = ""
        queue = {"queueId": queueId}
        await connection.request("POST", "/lol-lobby/v2/lobby", data=queue)
        lobby = await connection.request("GET", "/lol-lobby/v2/lobby")
        lobby_information = await lobby.json()
        if "gameConfig" in lobby_information:
            postqueueId = lobby_information["gameConfig"]["queueId"]
            if prequeueId != postqueueId:
                available_queueId.append(queueId)
                print('{\n\t"queueId": ' + str(queueId) + "\n}")
                print(lobby_information)
            else:
                print("序号为%d的队列房间不可用。\nThe lobby of queueId %d isn't available."%(queueId, queueId))
        else:
            print("序号为%d的队列房间不可用。\nThe lobby of queueId %d isn't available."%(queueId, queueId))
        time.sleep(0.1)
    time.sleep(2)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await create_custom_lobby(connection)
    await create_queue_lobby(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
print("可用自定义房间游戏模式和地图序号如下：\nAvailable custom lobby game modes and mapIds are as follows:")
print(available_custom_game)
print("可用队列房间序号如下：\nAvailable lobby queueIds are as follows:")
print(available_queueId)
print("检查完成，请按任意键退出……\nCheck finished. Please press any key to quit ...")
input()
