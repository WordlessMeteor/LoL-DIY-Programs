from lcu_driver import Connector
import os, pandas, random, time, uuid

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/05/01
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
localdata = pandas.read_excel("../../available-bots.xlsx", index_col = 0, usecols = list(range(1, 5)), skiprows = [1])
names = {championId: localdata.at[championId, "name"] for championId in localdata.index}
aliases = {championId: localdata.at[championId, "alias"] for championId in localdata.index}
all_bots = list(names.keys())

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
# 创建自定义房间（Create a custom lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    gamemodes = ["CLASSIC", "ARAM", "PRACTICETOOL", "NEXUSBLITZ", "GAMEMODEX"]
    mapId = [11, 12, 11, 21, 21]
    print("请选择自定义房间的游戏模式：\nPlease select a game mode of the lobby:\n1\t召唤师峡谷（Summoner's Rift）\n2\t嚎哭深渊（Howling Abyss）\n3\t训练模式（Practice Tool）\n4\t极限闪击（不可用）【Nexus Blitz (Unavailable)】\n5\t极限闪击（Nexus Blitz）")
    while True:
        typeNumber = input()
        if typeNumber == "":
            continue
        elif typeNumber in map(str, range(1, 6)):
            typeNumber = int(typeNumber)
            print("请选择自定义房间的游戏类型：\nPlease select a game type of the lobby:\n1\t自选模式（Blind Pick）\n2\t征召模式（Draft Mode）\n4\t全随机模式（All Random）\n6\t竞技征召模式（Tournament Draft）")
            while True:
                mutatorId = input()
                if mutatorId == "":
                    continue
                elif mutatorId in {"1", "2", "4", "6"}:
                    mutatorId = int(mutatorId)
                    custom = {
                        "customGameLobby": {
                            "configuration": {
                                "gameMode": gamemodes[typeNumber - 1],
                                "gameMutator": "",
                                "gameServerRegion": "",
                                "mapId": mapId[typeNumber - 1],
                                "mutators": {
                                    "id": mutatorId
                                },
                            "spectatorPolicy": "AllAllowed",
                            "teamSize": 5
                            },
                            "lobbyName": summoner["gameName"] + "'s Game",
                            "lobbyPassword": ""
                        },
                        "isCustom": True
                    }
                    await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)
                    break
                else:
                    print("游戏类型输入错误！请重新输入：\nError input of game type! Please try again:")
            break
        else:
            print("游戏模式输入错误！请重新输入：\nError input of game mode! Please try again:")

#-----------------------------------------------------------------------------
# 批量添加机器人（Add a batch of bots）
#-----------------------------------------------------------------------------
async def add_bots_team(connection, teamId: str):
    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    maxTeamSize = lobby_information["gameConfig"]["maxTeamSize"]
    current_summonerId = (await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json())["summonerId"]
    LoLChampions = await (await connection.request("GET", f"/lol-champions/v1/inventories/{current_summonerId}/champions")).json()
    LoLChampions = {champion["id"]: champion for champion in LoLChampions}
    recommended_position_for_champion = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    recommended_position_for_champion_keys = list(recommended_position_for_champion.keys())
    for championId in recommended_position_for_champion_keys:
        if not int(championId) in all_bots:
            del recommended_position_for_champion[championId]
    botPositions = set()
    for champion in recommended_position_for_champion.values():
        botPositions |= set(champion["recommendedPositions"])
    #将botPositions排序整理为["TOP", "MIDDLE", "BOTTOM", "UTILITY", "JUNGLE"]
    botPositions = list(botPositions)
    botPositions_tmp = []
    for position in ["TOP", "MIDDLE", "BOTTOM", "UTILITY", "JUNGLE"]: #与电脑玩家添加脚本和整合版文件不同，在添加己方电脑玩家时，默认自己是打野位置（What's different from Bot Adding Program and the Consolidated File is that the user is regarded as a jungler in its team）
        if position in botPositions:
            botPositions.remove(position)
            botPositions_tmp.append(position)
    botPositions = botPositions_tmp + botPositions
    recommended_champion_for_position = {} #用于生成某条分路的随机英雄（Used to generate random champions of specific positions respectively）
    for position in botPositions:
        recommended_champion_for_position[position] = []
    for championId in recommended_position_for_champion:
        for position in recommended_position_for_champion[championId]["recommendedPositions"]:
            recommended_champion_for_position[position].append(int(championId))
    for position in recommended_champion_for_position:
        recommended_champion_for_position[position].sort()
    
    team = []
    for position in botPositions:
        team += random.sample(recommended_champion_for_position[position], 1)
    
    botUuid_team = []
    botPosition_team = botPositions[:]
    for i in range(len(team)):
        Id = team[i]
        botUuid = str(uuid.uuid4())
        botUuid_team.append(botUuid)
        bot = {"championId": Id, "botDifficulty": "RSINTERMEDIATE", "teamId": teamId, "position": botPositions[i], "botUuid": botUuid}
        response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
    
    print("队伍%s的电脑玩家：\nTeam %s bots:\n*****************************************************************************" %(teamId[0], teamId[0]))
    for i in range(len(team)):
        print("{0:<14}".format(names[team[i]]) + "\t" + "{0:<14}".format(aliases[team[i]]) + "\tRSINTERMEDIATE\t" + botPosition_team[i] + "\t" + botUuid_team[i])
    print("*****************************************************************************\n")

#-----------------------------------------------------------------------------
# 开始游戏（Start Game）
#-----------------------------------------------------------------------------
async def start_game(connection):
    response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/start-champ-select")).json()
    #print(response)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await create_custom_lobby(connection)
    await add_bots_team(connection, teamId = "100")
    await add_bots_team(connection, teamId = "200")
    time.sleep(0.1)
    await start_game(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
