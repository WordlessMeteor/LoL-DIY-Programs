from lcu_driver import Connector

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：       XHXIAIEIN
# 更新（Last update）：  2021/01/08
# 主页（Home page）：    https://github.com/XHXIAIEIN/LeagueCustomLobby/
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# 获取自定义模式电脑玩家列表（Get access to the bot list in Custom）
#-----------------------------------------------------------------------------
import os, pandas, random, time
localdata = pandas.read_excel("../available-bots.xlsx")
champions_CN = { int(localdata["championId"][bot]): localdata["CN"][bot] for bot in range(len(localdata)) }
champions_EN = { int(localdata["championId"][bot]): localdata["EN"][bot] for bot in range(len(localdata)) }
all_champions = list(champions_CN.keys())
gameMode = {1: "CLASSIC", 2: "ODIN", 3: "ARAM", 4: "TUTORIAL", 5: "URF", 6: "DOOMBOTSTEEMO", 7: "ONEFORALL", 8: "ASCENSION", 9: "FIRSTBLOOD", 10: "KINGPORO", 11: "SIEGE", 12: "ASSASSINATE", 13: "ARSR", 14: "DARKSTAR", 15: "STARGUARDIAN", 16: "PROJECT", 17: "GAMEMODEX", 18: "ODYSSEY", 19: "NEXUSBLITZ", 20: "ULTBOOK"}

connector = Connector()

#-----------------------------------------------------------------------------
# 获得召唤师数据（Get access to summoner data）
#-----------------------------------------------------------------------------
async def get_summoner_data(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    print(f"displayName:    {summoner['displayName']}")
    print(f"summonerId:     {summoner['summonerId']}")
    print(f"puuid:          {summoner['puuid']}")
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
    for i in gameMode:
        for j in range(0,100):
            custom = {
                "customGameLobby": {
                    "configuration": {
                        "gameMode": gameMode[i],
                        "gameMutator": "",
                        "gameServerRegion": "",
                        "mapId": j,
                        "mutators": {
                            "id": 1
                        },
                    "spectatorPolicy": "AllAllowed",
                    "teamSize": 1
                    },
                    "lobbyName": summoner["displayName"] + "'s Game",
                    "lobbyPassword": ""
                },
                "isCustom": True
            }
            await connection.request("POST", "/lol-lobby/v2/lobby", data=custom)
            bot = { "championId": 11, "botDifficulty": "MEDIUM", "teamId": "200"}
            await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)
            time.sleep(0.1)
            data = await connection.request("GET", "/lol-lobby/v2/lobby")
            bot = await data.json()
            try:
                if bool(bot["gameConfig"]["customTeam200"]):
                    available_custom_game.append((gameMode[i],j))
                    print(custom)
            except KeyError:
                print("游戏模式为%s、地图序号为%d的自定义房间不可用。\nThe lobby of gameMode %s and mapId %d isn't available."%(gameMode[i], j, gameMode[i], j))
    time.sleep(2)

#-----------------------------------------------------------------------------
# 检测队列房间有效性（Check the availability of different queue lobbies）
#-----------------------------------------------------------------------------
async def create_queue_lobby(connection):
    print("正在检查队列房间有效性……\nChecking the availability of different queue lobbies ...")
    global available_queueId
    available_queueId = []
    for queueId in range(3000):
        lobby = await connection.request("GET", "/lol-lobby/v2/lobby")
        lobby_information = await lobby.json()
        if "gameConfig" in lobby_information:
            prequeueId = lobby_information["gameConfig"]["queueId"]
        else:
            prequeueId = ""
        queue = {
                    "queueId": queueId
                }
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
                print("序号为%d的房间不可用。\nThe lobby of queueId %d isn't available."%(queueId, queueId))
        else:
            print("序号为%d的房间不可用。\nThe lobby of queueId %d isn't available."%(queueId, queueId))
        time.sleep(0.1)
    time.sleep(2)

#-----------------------------------------------------------------------------
# 批量添加机器人（Add a batch of bots）
#-----------------------------------------------------------------------------
async def add_bots_team1(connection):
    activedata = await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")
    champions = { bot["id"]: bot["name"] for bot in await activedata.json() }
    all_champions = list(champions.keys())
    
    team1 = random.sample(all_champions,5)

    for Id in team1:
        bot = { "championId": Id, "botDifficulty": "MEDIUM", "teamId": "100"}
        await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)

#-----------------------------------------------------------------------------
# 批量添加机器人（Add a batch of bots）
#-----------------------------------------------------------------------------
async def add_bots_team2(connection):
    activedata = await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")
    champions = { bot["id"]: bot["name"] for bot in await activedata.json() }
    all_champions = list(champions.keys())
    
    team2 = random.sample(all_champions,5)

    for Id in team2:
        bot = { "championId": Id, "botDifficulty": "MEDIUM", "teamId": "200"}
        await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    #await get_summoner_data(connection)
    #await get_lockfile(connection)
    await create_custom_lobby(connection)
    await create_queue_lobby(connection)
    #await add_bots_team1(connection)
    #await add_bots_team2(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
print("可用自定义房间游戏模式和地图序号如下：\nAvailable custom lobby gameModes and mapIds are as follows:")
print(available_custom_game)
print("可用队列房间序号如下：\nAvailable lobby queueIds are as follows:")
print(available_queueId)
print("检查完成，请按任意键退出……\nCheck finished. Please press any key to quit ...")
input()
