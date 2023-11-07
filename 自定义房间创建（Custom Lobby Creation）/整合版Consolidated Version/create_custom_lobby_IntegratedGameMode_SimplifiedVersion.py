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
localdata = pandas.read_excel("../../available-bots.xlsx")
champions_CN = { int(localdata["championId"][bot]): localdata["CN"][bot] for bot in range(len(localdata)) }
champions_EN = { int(localdata["championId"][bot]): localdata["EN"][bot] for bot in range(len(localdata)) }
all_champions = list(champions_CN.keys())

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
# 创建自定义房间（Create a custom lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    gameMode = ["CLASSIC","ARAM","PRACTICETOOL","NEXUSBLITZ"]
    mapId = [11,12,11,21]
    print("请选择自定义房间的游戏模式：\nPlease select a game mode of the lobby:\n1\t召唤师峡谷（Summoner's Rift）\n2\t嚎哭深渊（Howling Abyss）\n3\t训练模式（Practice Tool）\n4\t极限闪击（国服不可用）【Nexus Blitz (Unavailable on Chinese servers)】")
    while True:
        TypeNumber = input()
        if TypeNumber == "":
            continue
        elif TypeNumber in {"1","2","3","4"}:
            TypeNumber = int(TypeNumber)
            print("请选择自定义房间的游戏类型：\nPlease select a game type of the lobby:\n1\t自选模式（Blind Pick）\n2\t征召模式（Draft Mode）\n4\t全随机模式（All Random）\n6\t竞技征召模式（国服正式服不可用）【Tournament Draft (Unavailable on Chinese Live servers)】")
            while True:
                mutatorid = input()
                if mutatorid == "":
                    continue
                elif mutatorid in {"1","2","4","6"}:
                    mutatorid = int(mutatorid)
                    custom = {
                        "customGameLobby": {
                            "configuration": {
                                "gameMode": gameMode[TypeNumber - 1],
                                "gameMutator": "",
                                "gameServerRegion": "",
                                "mapId": mapId[TypeNumber - 1],
                                "mutators": {
                                    "id": mutatorid
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
                    break
                else:
                    print("游戏类型输入错误！请重新输入：\nError input of game type! Please try again:")
            break
        else:
            print("游戏模式输入错误！请重新输入：\nError input of game mode! Please try again:")

#-----------------------------------------------------------------------------
# 批量添加机器人（Add a batch of bots）
#-----------------------------------------------------------------------------
async def add_bots_team1(connection):
    team1 = random.sample(all_champions,5)

    for Id in team1:
        bot = { "championId": Id, "botDifficulty": "MEDIUM", "teamId": "100"}
        await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)

#-----------------------------------------------------------------------------
# 批量添加机器人（Add a batch of bots）
#-----------------------------------------------------------------------------
async def add_bots_team2(connection):
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
