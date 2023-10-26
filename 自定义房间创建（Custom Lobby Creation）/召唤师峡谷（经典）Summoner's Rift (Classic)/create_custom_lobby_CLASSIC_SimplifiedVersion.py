from lcu_driver import Connector
import os, random, time

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
# 创建召唤师峡谷自定义房间（Create a custom Summoner's Rift lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    custom = {
        "customGameLobby": {
            "configuration": {
                "gameMode": "CLASSIC",
                "gameMutator": "",
                "gameServerRegion": "",
                "mapId": 11,
                "mutators": {
                    "id": 1
                },
            "spectatorPolicy": "AllAllowed",
            "teamSize": 5
            },
            "lobbyName": summoner["displayName"] + "'s Game",
            "lobbyPassword": ""
        },
        "isCustom": True
    }
    await connection.request("POST", "/lol-lobby/v2/lobby", data=custom)

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
# 开始游戏（Start Game）
#-----------------------------------------------------------------------------
async def start_game(connection):
    start = await connection.request("POST", "/lol-lobby/v1/lobby/custom/start-champ-select")

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await create_custom_lobby(connection)
    await add_bots_team1(connection)
    await add_bots_team2(connection)
    await start_game(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
