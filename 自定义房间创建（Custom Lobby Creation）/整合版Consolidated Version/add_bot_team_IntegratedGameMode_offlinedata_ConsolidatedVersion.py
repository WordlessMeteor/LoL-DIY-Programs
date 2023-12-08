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
import pandas,random,time
localdata = pandas.read_excel("../../available-bots.xlsx", sheet_name = "Sheet2")
champions_CN = { int(localdata["championId"][bot]): localdata["name"][bot] for bot in range(len(localdata)) }
champions_EN = { int(localdata["championId"][bot]): localdata["alias"][bot] for bot in range(len(localdata)) }
all_champions = list(champions_CN.keys())
print("是否查看可用电脑玩家列表？（输入任意键查看，否则不查看）\nCheck the availbale-bots list? (Any keys for Y, or null for N)")
check_botlist = input()
if check_botlist != "":
    print("*****************************************************************************")
    print("championId\t" + "{0:^14}".format("name") + "\t" + "{0:^14}".format("alias"))
    for h in range(len(localdata)):
        print("{0:<10}".format(str(localdata["championId"][h])) + "\t" + "{0:<14}".format(localdata["name"][h]) + "\t" + "{0:<14}".format(localdata["alias"][h]))
    print("*****************************************************************************\n")

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
    import os
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
                        print("{0:<14}".format(champions_CN[j]) + "\t" + "{0:<14}".format(champions_EN[j]))
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
                print("{0:<14}".format(champions_CN[j]) + "\t" + "{0:<14}".format(champions_EN[j]))
            print("*****************************************************************************")
            break

    print("是否设定电脑玩家难度一致？（输入任意键设定为不一致，否则一致）\nSet all botDifficulties identical? (Any keys for N, or null for Y)")
    botDifficulty_consistency = input()
    if not botDifficulty_consistency:
        print("请输入电脑玩家的难度：\nPlease enter the botDifficulty: (among NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD and UBER)")
        while True:
            botDifficulty_team1 = input()
            if botDifficulty_team1 == "":
                continue
            elif botDifficulty_team1.upper() in {"NONE", "TUTORIAL", "INTRO", "EASY", "MEDIUM", "HARD", "UBER"}:
                for Id in team1:
                    bot = { "championId": Id, "botDifficulty": botDifficulty_team1, "teamId": "100"}
                    await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)
                break
            else:
                print("电脑玩家难度输入错误！请选择{NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}中的一个：\nError input of botDifficulty! Please choose among {NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}:")
        print("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
        bot_order1 = 0
        for k in team1:
            print("{0:<14}".format(champions_CN[k]) + "\t" + "{0:<14}".format(champions_EN[k]) + "\t" + botDifficulty_team1.upper())
            bot_order1 += 1
        print("*****************************************************************************\n")

    else:
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
            print("{0:<14}".format(champions_CN[k]) + "\t" + "{0:<14}".format(champions_EN[k]) + "\t" + botDifficulty_team1[bot_order1].upper())
            bot_order1 += 1
        print("*****************************************************************************\n")

    time.sleep(2)

#-----------------------------------------------------------------------------
# 批量添加机器人（Add a batch of bots）
#-----------------------------------------------------------------------------
async def add_bots_team2(connection):
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
                        print("{0:<14}".format(champions_CN[j]) + "\t" + "{0:<14}".format(champions_EN[j]))
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
                print("{0:<14}".format(champions_CN[j]) + "\t" + "{0:<14}".format(champions_EN[j]))
            print("*****************************************************************************")
            break

    print("是否设定电脑玩家难度一致？（输入任意键设定为不一致，否则一致）\nSet all botDifficulties identical? (Any keys for N, or null for Y)")
    botDifficulty_consistency = input()
    if not botDifficulty_consistency:
        print("请输入电脑玩家的难度：\nPlease enter the botDifficulty: (among NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD and UBER)")
        while True:
            botDifficulty_team2 = input()
            if botDifficulty_team2 == "":
                continue
            elif botDifficulty_team2.upper() in {"NONE", "TUTORIAL", "INTRO", "EASY", "MEDIUM", "HARD", "UBER"}:
                for Id in team2:
                    bot = { "championId": Id, "botDifficulty": botDifficulty_team2, "teamId": "200"}
                    await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data=bot)
                break
            else:
                print("电脑玩家难度输入错误！请选择{NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}中的一个：\nError input of botDifficulty! Please choose among {NONE, TUTORIAL, INTRO, EASY, MEDIUM, HARD, UBER}:")

        print("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
        bot_order2 = 0
        for k in team2:
            print("{0:<14}".format(champions_CN[k]) + "\t" + "{0:<14}".format(champions_EN[k]) + "\t" + botDifficulty_team2.upper())
            bot_order2 += 1
        print("*****************************************************************************\n")
    else:
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
            print("{0:<14}".format(champions_CN[k]) + "\t" + "{0:<14}".format(champions_EN[k]) + "\t" + botDifficulty_team2[bot_order2].upper())
            bot_order2 += 1
        print("*****************************************************************************\n")

#-----------------------------------------------------------------------------
# 获取房间信息（Get lobby information）
#-----------------------------------------------------------------------------
async def get_lobby_information(connection):
    lobby_information = await connection.request("GET", "/lol-lobby/v2/lobby")
    print(await lobby_information.json())
    time.sleep(5)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    #await create_custom_lobby(connection)
    await add_bots_team1(connection)
    await add_bots_team2(connection)
    await get_lobby_information(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
