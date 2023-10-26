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
# 创建嚎哭深渊自定义房间（Create a custom Howling Abyss lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    custom = {
        "customGameLobby": {
            "configuration": {
                "gameMode": "ARAM",
                "gameMutator": "",
                "gameServerRegion": "",
                "mapId": 12,
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
    # 获取自定义模式电脑玩家列表（Get access to the bot list in Custom）
    print("是否查看可用电脑玩家列表？（输入任意键查看，否则不查看）\nCheck the availbale-bots list? (Any keys for Y, or null for N)")
    check_botlist = input()
    if check_botlist != "":
        print("*****************************************************************************")
        print("championId\t" + "{0:^14}".format("name"))
        for h in champions:
            print("{0:<10}".format(str(h)) + "\t" + "{0:<14}".format(champions[h]))
        print("*****************************************************************************\n")

    print("队伍1：请选择自选电脑玩家或者随机生成电脑玩家：\nTeam 1: Please select the option to generate bot players:\n0\t跳过该队伍（Skip this team）\n1\t随机生成（Randomly）\n2\t自选（By picking）")
    while True:
        o = input()
        if o == "":
            continue
        elif o == "0":
            return 0
        elif o[0] == "1":
            print("请输入电脑玩家数量：\nPlease enter the number of bot players:")
            while True:
                i = input()
                if i == "":
                    continue
                elif i in {"1","2","3","4","5"}:
                    i = int(i)
                    team1 = random.sample(all_champions,i)
                    print("系统为您分配到以下英雄：\nYou have been distributed the bot champions as follows:\n*****************************************************************************")
                    for j in team1:
                        print(champions[j])
                    print("*****************************************************************************")
                    break
                else:
                    print("电脑玩家数量不合法！请重新输入：\nIllegal bot players number! Please try again:")
            break

        else:
            print("请输入电脑玩家的id，以空格为分隔符：\nPlease input the ids of bot players, split by space:")
            while True:
                try:
                    team1 = list(set(list(map(int, input().split()))))
                except ValueError:
                    print("您的输入有误，请重新输入！\nInput ERROR! Please try again!")
                else:
                    break
            team1.sort()
            print("您已选择以下英雄：\nYou have selected the bot champions as follows:\n*****************************************************************************")
            for j in team1:
                print(champions[j])
            print("*****************************************************************************")
            break

    print("请依次输入电脑玩家的难度：\nPlease enter the botDifficulty one by one: (among NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD and UBER)")
    botDifficulty_team1 = []
    for Id in team1:
        while True:
            temp1 = input()
            if temp1 == "":
                continue
            elif temp1.upper() in {"NONE", "TUTORIAL", "INTRO", "EASY", "MEDIUM", "HARD", "UBER"}:
                botDifficulty_team1.append(temp1)
                bot = { "championId": Id, "botDifficulty": temp1, "teamId": "100"}
                await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)
                break
            else:
                print("电脑玩家难度输入错误！请选择{NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}中的一个：\nError input of botDifficulty! Please choose among {NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}:")

    print("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
    bot_order1 = 0
    for k in team1:
        print("{0:<14}".format(champions[k]) + "\t" + botDifficulty_team1[bot_order1].upper())
        bot_order1 += 1
    print("*****************************************************************************\n")
    time.sleep(2)

#-----------------------------------------------------------------------------
# 批量添加机器人（Add a batch of bots）
#-----------------------------------------------------------------------------
async def add_bots_team2(connection):
    activedata = await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")
    champions = { bot["id"]: bot["name"] for bot in await activedata.json() }

    all_champions = list(champions.keys())
    print("队伍2：请选择自选电脑玩家或者随机生成电脑玩家：\nTeam 2: Please select the option to generate bot players:\n0\t跳过该队伍（Skip this team）\n1\t随机生成（Randomly）\n2\t自选（By picking）")
    while True:
        o = input()
        if o == "":
            continue
        elif o == "0":
            return 0
        elif o[0] == "1":
            print("请输入电脑玩家数量：\nPlease enter the number of bot players:")
            while True:
                i = input()
                if i == "":
                    continue
                elif i in {"1","2","3","4","5"}:
                    i = int(i)
                    team2 = random.sample(all_champions,i)
                    print("系统为您分配到以下英雄：\nYou have been distributed the bot champions as follows:\n*****************************************************************************")
                    for j in team2:
                        print(champions[j])
                    print("*****************************************************************************")
                    break
                else:
                    print("电脑玩家数量不合法！请重新输入：\nIllegal bot players number! Please try again:")
            break

        else:
            print("请输入电脑玩家的id，以空格为分隔符：\nPlease input the ids of bot players, split by space:")
            while True:
                try:
                    team2 = list(set(list(map(int, input().split()))))
                except ValueError:
                    print("您的输入有误，请重新输入！\nInput ERROR! Please try again!")
                else:
                    break
            team2.sort()
            print("您已选择以下英雄：\nYou have selected the bot champions as follows:\n*****************************************************************************")
            for j in team2:
                print(champions[j])
            print("*****************************************************************************")
            break

    print("请依次输入电脑玩家的难度：\nPlease enter the botDifficulty one by one: (among NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD and UBER)")
    botDifficulty_team2 = []
    for Id in team2:
        while True:
            temp2 = input()
            if temp2 == "":
                continue
            elif temp2.upper() in {"NONE", "TUTORIAL", "INTRO", "EASY", "MEDIUM", "HARD", "UBER"}:
                botDifficulty_team2.append(temp2)
                bot = { "championId": Id, "botDifficulty": temp2, "teamId": "200"}
                await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)
                break
            else:
                print("电脑玩家难度输入错误！请选择{NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}中的一个：\nError input of botDifficulty! Please choose among {NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}:")

    print("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
    bot_order2 = 0
    for k in team2:
        print("{0:<14}".format(champions[k]) + "\t" + botDifficulty_team2[bot_order2].upper())
        bot_order2 += 1
    print("*****************************************************************************\n")

#-----------------------------------------------------------------------------
# 获取房间信息（Get lobby information）
#-----------------------------------------------------------------------------
async def get_lobby_information(connection):
    lobby_information = await connection.request("GET", "/lol-lobby/v2/lobby")
    print(await lobby_information.json())

#-----------------------------------------------------------------------------
# 开始游戏（Start game）
#-----------------------------------------------------------------------------
async def start_game(connection):
    start = await connection.request("POST", "/lol-lobby/v1/lobby/custom/start-champ-select")

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    try:
        await get_summoner_data(connection)
        await get_lockfile(connection)
        await create_custom_lobby(connection)
        await add_bots_team1(connection)
        await add_bots_team2(connection)
        await get_lobby_information(connection)
        await start_game(connection)
    except ValueError:
        print("云数据中无可用电脑玩家。请尝试添加本地数据。\nNo available-bots online. Please try using offline data.\n")
    except KeyError:
        print("云数据中无可用电脑玩家。请尝试添加本地数据。\nNo available-bots online. Please try using offline data.\n")
    time.sleep(5)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
