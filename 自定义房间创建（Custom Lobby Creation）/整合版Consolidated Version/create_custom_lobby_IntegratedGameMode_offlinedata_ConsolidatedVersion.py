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
import os, pandas, random, shutil, time, unicodedata
from wcwidth import wcswidth
#localdata = pandas.read_excel("../../available-bots.xlsx")
localdata = pandas.read_excel("../../available-bots.xlsx", sheet_name = "Sheet1")
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
##localdata = pandas.read_excel("../../QueueID.xlsx")
##print("是否查看可用队列房间序号？（输入任意键查看，否则不查看）\nCheck the available QueueID list? (Any keys for Y, or null for N)")
##check_queueid = input()
##if check_queueid != "":
##    print("*****************************************************************************")
##    print("QueueID\tmapID\t" + "{0:^14}".format("map_CN") + "\t" + "{0:^30}".format("Gamemode_CN") + "\t" + "{0:^11}".format("PickType_CN") + "\t" + "{0:^24}".format("map_EN") + "\t" + "{0:^34}".format("Gamemode_EN") + "\t" + "{0:^15}".format("PickType_EN"))
##    for h in range(len(localdata)):
##        print("{0:<7}".format(str(localdata["QueueID"][h])) + "\t" + "{0:<5}".format(str(localdata["mapID"][h])) + "\t" + "{0:<14}".format(localdata["map_CN"][h]) + "\t" + "{0:<30}".format(localdata["Gamemode_CN"][h]) + "\t" + "{0:<11}".format(localdata["PickType_CN"][h]) + "\t" + "{0:<24}".format(localdata["map_EN"][h]) + "\t" + "{0:<34}".format(localdata["Gamemode_EN"][h]) + "\t" + "{0:<15}".format(localdata["PickType_EN"][h]))
##    print("*****************************************************************************")

def count_nonASCII(s: str): #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def format_df(df: pandas.DataFrame): #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
    df = df.reset_index(drop = True) #这一步至关重要，因为下面的操作前提是行号是默认的（This step is crucial, for the following operations are based on the dataframe with the default row index）
    maxLens = {}
    maxWidth = shutil.get_terminal_size()[0]
    fields = df.columns.tolist()
    for field in fields:
        maxLens[field] = max(max(map(lambda x: wcswidth(str(x)), df[field])), wcswidth(str(field))) + 2
    if sum(maxLens.values()) + 2 * (len(fields) - 1) > maxWidth:
        print("单行数据字符串输出宽度超过当前终端窗口宽度！是否继续？（输入任意键继续，否则直接打印该数据框。）\nThe output width of each record string exceeds the current width of the terminal window! Continue? (Input anything to continue, or null to directly print this dataframe.)")
        if input() == "":
            #print(df)
            result = str(df)
            return (result, maxLens)
    result = ""
    for i in range(df.shape[1]):
        field = fields[i]
        tmp = "{0:^{w}}".format(field, w = maxLens[str(field)] - count_nonASCII(str(field)))
        result += tmp
        #print(tmp, end = "")
        if i != df.shape[1] - 1:
            result += "  "
            #print("  ", end = "")
    result += "\n"
    #print()
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            field = fields[j]
            cell = df[field][i]
            tmp = "{0:^{w}}".format(cell, w = maxLens[field] - count_nonASCII(str(cell)))
            result += tmp
            #print(tmp, end = "")
            if j != df.shape[1] - 1:
                result += "  "
                #print("  ", end = "")
        if i != df.shape[0] - 1:
            result += "\n"
        #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the last line）
    return (result, maxLens)

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
# 检查队列可用性（Check queue availability）
#-----------------------------------------------------------------------------
async def check_available_queue(connection):
    queues = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    map_CN = {8: "水晶之痕", 10: "扭曲丛林", 11: "召唤师峡谷", 12: "嚎哭深渊", 14: "屠夫之桥", 16: "宇宙遗迹", 18: "瓦罗兰城市公园", 19: "第43区", 20: "失控地点", 21: "百合与莲花的神庙", 22: "聚点危机", 30: "怒火角斗场"}
    map_EN = {8: "Crystal Scar", 10: "Twisted Treeline", 11: "Summoner's Rift", 12: "Howling Abyss", 14: "Butcher's Bridge", 16: "Cosmic Ruins", 18: "Valoran City Park", 19: "Substructure 43", 20: "Crash Site", 21: "Temple of Lily and Lotus", 22: "Convergence", 30: "Rings of Wrath"}
    pickmode_CN = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式", "": "待定"}
    pickmode_EN = {"AllRandomPickStrategy": "All Random", "SimulPickStrategy": "Blind Pick", "TeamBuilderDraftPickStrategy": "Draft Mode", "OneTeamVotePickStrategy": "Vote", "TournamentPickStrategy": "Tournament Draft", "": "Pending"}
    available_queues = {}
    for queue in queues:
        if queue["queueAvailability"] == "Available":
            available_queues[queue["id"]] = queue
    queue_dict = {"queueID": [], "mapID": [], "map_CN": [], "map_EN": [], "gameMode": [], "pickType_CN": [], "pickType_EN": []}
    for queue in available_queues.values():
        queue_dict["queueID"].append(queue["id"])
        queue_dict["mapID"].append(queue["mapId"])
        queue_dict["map_CN"].append(map_CN[queue["mapId"]])
        queue_dict["map_EN"].append(map_EN[queue["mapId"]])
        queue_dict["gameMode"].append(queue["name"])
        queue_dict["pickType_CN"].append(pickmode_CN[queue["gameTypeConfig"]["pickMode"]])
        queue_dict["pickType_EN"].append(pickmode_EN[queue["gameTypeConfig"]["pickMode"]])
    queue_df = pandas.DataFrame(queue_dict)
    queue_df.sort_values(by = "queueID", inplace = True, ascending = True, ignore_index = True)
    print("*****************************************************************************")
    print(format_df(queue_df)[0])
    print("*****************************************************************************")

#-----------------------------------------------------------------------------
# 创建自定义房间（Create a custom lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    summoner = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    gameMode = ["CLASSIC","ARAM","PRACTICETOOL","NEXUSBLITZ","TUTORIAL"]
    gamemap = {8: "水晶之痕（Crystal Scar）", 10: "扭曲丛林（Twisted Treeline）", 11: "召唤师峡谷（Summoner's Rift）", 12: "嚎哭深渊（Howling Abyss）", 14: "屠夫之桥（Butcher's Bridge）", 16: "宇宙遗迹（Cosmic Ruins）", 18: "瓦罗兰城市公园（Valoran City Park）", 19: "第43区（Substructure 43）", 20: "失控地点（Crash Site）", 21: "百合与莲花的神庙（Temple of Lily and Lotus）", 22: "聚点危机（Convergence）", 30: "怒火角斗场（Rings of Wrath）"}
    spectatorPolicy = ["LobbyAllowed", "FriendsAllowed", "AllAllowed", "NotAllowed"]
    print("请选择自定义房间的游戏模式：\nPlease select a game mode of the lobby:\n1\t召唤师峡谷（Summoner's Rift）\n2\t嚎哭深渊（Howling Abyss）\n3\t训练模式（Practice Tool）\n4\t极限闪击（国服不可用）【Nexus Blitz (Unavailable on Chinese servers)】")
    while True:
        gameModeTypeNumber = input()
        if gameModeTypeNumber == "":
            continue
        elif gameModeTypeNumber in {"1","2","3","4","5"}:
            gameModeTypeNumber = int(gameModeTypeNumber)
            break
        else:
            print("游戏模式输入错误！请重新输入：\nError input of game mode! Please try again:")
    print("请输入地图序号：\nPlease enter a mapID:")
    mapIDs = list(gamemap.keys())
    mapIDs.sort()
    for i in mapIDs:
        print(str(i) + "\t" + gamemap[i])
    while True:
        mapId = input()
        if mapId == "":
            if gameModeTypeNumber == 1:
                mapId = 11
                break
            elif gameModeTypeNumber == 2:
                mapId = 12
                break
            elif gameModeTypeNumber == 3:
                mapId = 11
                break
            elif gameModeTypeNumber == 4:
                mapId = 21
                break
            else:
                continue
        elif mapId in {"8","10","11","12","14","16","18","19","20","21","22"}:
            mapId = int(mapId)
            break
        else:
            print("地图序号输入错误！请重新输入：\nError input of mapID! Please try again:")
    print("请选择自定义房间的游戏类型：\nPlease select a game type of the lobby:\n1\t自选模式（Blind Pick）\n2\t征召模式（Draft Mode）\n4\t全随机模式（All Random）\n6\t竞技征召模式（国服正式服不可用）【Tournament Draft (Unavailable on Chinese Live servers)】")
    while True:
        mutatorid = input()
        if mutatorid == "":
            continue
        elif mutatorid in {"1","2","4","6"}:
            mutatorid = int(mutatorid)
            break
        else:
            print("游戏类型输入错误！请重新输入：\nError input of game type! Please try again:")
    print("请选择自定义房间的允许观战策略：\nPlease select a spectator policy:\n1\t只允许房间内玩家（Lobby Only）\n2\t只允许好友（国服不可用）【Friends List Only (Unavailable on Chinese servers)】\n3\t所有人（国服不可用）【All (Unavailable on Chinese servers)】\n4\t无（None）")
    while True:
        customSpectatorPolicyTypeNumber = input()
        if customSpectatorPolicyTypeNumber == "":
            continue
        elif customSpectatorPolicyTypeNumber in {"1","2","3","4"}:
            customSpectatorPolicyTypeNumber = int(customSpectatorPolicyTypeNumber)
            break
        else:
            print("允许观战策略输入错误！请重新输入：\nError input of spectator policy! Please try again:")
    print("请依次输入对局名、队伍规模、密码（可选）：\nPlease enter the lobby's name, team size and password (optional):")
    print("对局名（Lobby Name）：", end = "")
    lobbyName = input()
    if lobbyName == "":
        region_locale = await (await connection.request("GET", "/riotclient/region-locale")).json()
        if region_locale["locale"] == "zh_CN":
            lobbyName = summoner["displayName"] + "的对局"
        elif region_locale["locale"] == "en_US":
            lobbyName = summoner["displayName"] + "'s Game"
        else: # 自定义房间无论如何都需要有名字（There has to be a name for a custom lobby）
            lobbyName = summoner["displayName"] + "的对局"
    print("队伍规模（Team Size）：", end = "")
    while True:
        teamsize = input()
        if teamsize == "":
            teamsize = 5
            break
        elif teamsize in {"1","2","3","4","5"}:
            teamsize = int(teamsize)
            break
        else:
            print("队伍规模输入错误！请重新输入：\nError input of team size! Please try again:")
    print("密码（Password）：", end = "")
    lobbyPassword = input()
    custom = {
        "customGameLobby": {
            "configuration": {
                "gameMode": gameMode[gameModeTypeNumber - 1],
                "gameMutator": "",
                "gameServerRegion": "",
                "mapId": mapId,
                "mutators": {
                    "id": mutatorid
                },
            "spectatorPolicy": spectatorPolicy[customSpectatorPolicyTypeNumber - 1],
            "teamSize": teamsize
            },
            "lobbyName": lobbyName,
            "lobbyPassword": lobbyPassword
        },
        "isCustom": True
    }
    await connection.request("POST", "/lol-lobby/v2/lobby", data=custom)

#-----------------------------------------------------------------------------
# 创建队列房间（Create a queue lobby）
#-----------------------------------------------------------------------------
async def create_queue_lobby(connection):
    Client_System_States = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/ClientSystemStates")).json()
    #print(Client_System_States)
    enabled_QueueId = Client_System_States["enabledQueueIdsList"]
    game_version = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    for i in enabled_QueueId:
        i = int(i)
    enabled_QueueId.sort()
    print("当前可用队列房间序号：\nCurrently enabled QueueIds:")
    while True:
        await check_available_queue(connection)
        print("(" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\t" + platformId + "\t" + game_version + ")")
        print("是否刷新可用队列信息？（输入任意键不刷新，否则刷新）\nRefresh available queue information? (Submit anything to quit refreshing, or null to continue refreshing)")
        refresh = input()
        if refresh != "":
            break
##    print("*****************************************************************************")
##    print("QueueID\tmapID\t" + "{0:^14}".format("map_CN") + "\t" + "{0:^30}".format("Gamemode_CN") + "\t" + "{0:^11}".format("PickType_CN") + "\t" + "{0:^24}".format("map_EN") + "\t" + "{0:^34}".format("Gamemode_EN") + "\t" + "{0:^15}".format("PickType_EN"))
##    for i in enabled_QueueId:
##        for j in range(len(localdata)):
##            if i == localdata["QueueID"][j]:
##                print("{0:<7}".format(str(localdata["QueueID"][j])) + "\t" + "{0:<5}".format(str(localdata["mapID"][j])) + "\t" + "{0:<14}".format(localdata["map_CN"][j]) + "\t" + "{0:<30}".format(localdata["Gamemode_CN"][j]) + "\t" + "{0:<11}".format(localdata["PickType_CN"][j]) + "\t" + "{0:<24}".format(localdata["map_EN"][j]) + "\t" + "{0:<34}".format(localdata["Gamemode_EN"][j]) + "\t" + "{0:<15}".format(localdata["PickType_EN"][j]))
##                break
##    print("*****************************************************************************")
    print("请输入队列房间序号：（输入负数以退出创建）\nPlease enter the queueID: (Enter any negative number to exit the creation)")
    while True:
        try:
            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            if "gameConfig" in lobby_information:
                prequeueId = lobby_information["gameConfig"]["queueId"]
            else:
                prequeueId = ""
            queueId = input()
            if queueId == "":
                continue
            queueId = int(queueId)
            if queueId < 0:
                break
            queue = {
                        "queueId": queueId
                    }
            await connection.request("DELETE", "/lol-lobby/v2/lobby")
            await connection.request("POST", "/lol-lobby/v2/lobby", data=queue)
            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            if "gameConfig" in lobby_information:
                postqueueId = lobby_information["gameConfig"]["queueId"]
                if prequeueId == postqueueId:
                    continue
                else:
                    print(lobby_information)
            else:
                print("此房间序号尚不可用。请选择其它序号。\nThis queueId isn't available yet. Please select another ID.")
        except ValueError:
            print("队列房间序号输入错误！请重新输入：\nError input of queueID! Please try again:")
        except KeyError:
            pass

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
    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    print(lobby_information)
    print("创建完成！输入任意键开始游戏，否则继续获取房间信息。\nLobby created successfully! Please press any key to start the game, or null to continue getting lobby information:")
    while input() == "":
        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        print(lobby_information)

#-----------------------------------------------------------------------------
# 开始游戏（Start Game）
#-----------------------------------------------------------------------------
async def start_game(connection):
    while True:
        lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        if lobby_information["gameConfig"]["isCustom"]:
            start_game = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/start-champ-select")).json()
            #print("start_game = ", end = "")
            #print(start_game)
            if "success" in start_game and start_game["success"] == True:
                gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json() #gameflow_phase参数（parameters）：None、Lobby、Matchmaking、ReadyCheck、ChampSelect、InProgress、WaitingForStats、EndOfGame
                while gameflow_phase != "ChampSelect":
                    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                    #print("gameflow-phase = ", end = "")
                    #print(gameflow_phase)
                gamemode_info = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                print(gamemode_info)
                while gameflow_phase == "ChampSelect":
                    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                #print("gameflow-phase = ", end = "")
                #print(gameflow_phase)
                if gameflow_phase == "Lobby":
                    print("请确认各召唤师就绪后，按回车开始匹配。\nPlease start queue by pressing Enter after confirming all ready.")
                    input()
                elif gameflow_phase == "None":
                    print("您已退出房间，请重启程序！\nYou have exited the lobby! Please restart the program!")
                    time.sleep(5)
                    break
                elif gameflow_phase == "InProgress":
                    break
            else:
                print(start_game)
                print("请检查房间有效性。输入任意键开始游戏。\nPlease check the lobby validation. Press any key to start the game.")
                input()
        else:
            members_prepared = False
            count = 0 # count用来控制输出，如果是第一次载入队列房间，需要确定各召唤师首选参数为空还是未选择。因为刚加入房间所有召唤师一定是未选择的，所以只需要请求各召唤师选择位置，不需要输出所有召唤师未首选的信息（count is used to control the output. If it first loads the queue lobby, whether firstPositionPreference is null or "UNSELECTED" should be ensured. Since all summoners join the lobby with unselected preferences, it's unnecessary to print the information about all the summoners with firstPositionPreference = "UNSELECTED"）
            while not members_prepared:
                count += 1
                first_unselected = []
                second_unselected = []
                for i in lobby_information["members"]:
                    if i["firstPositionPreference"] == "UNSELECTED":
                        first_unselected.append((i["summonerName"], i["summonerId"]))
                    elif i["firstPositionPreference"]!= "FILL" and i["secondPositionPreference"] == "UNSELECTED":
                        second_unselected.append((i["summonerName"], i["summonerId"]))
                if first_unselected == [] and second_unselected == []:
                    members_prepared = True
                else:
                    if count > 1:
                        print("以下召唤师未准备就绪：\nThe following summoners aren't ready yet:\n召唤师名称（SummonerName）\t召唤师序号（SummonerId）\t未选优先级（Unselected Preference）")
                        for i in first_unselected:
                            print(i[0] + "\t" + str(i[1]) + "\t" + "首选（First）")
                        for i in second_unselected:
                            print(i[0] + "\t" + str(i[1]) + "\t" + "次选（Second）")
                    print("请确认各召唤师就绪后，按回车开始匹配。\nPlease start queue by pressing Enter after confirming all ready.")
                    input()
                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            start_game = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json() # 对于一些点击“寻找对局”没有反应的房间，会给出以下信息：{'errorCode': 'RPC_ERROR', 'httpStatus': 400, 'implementationDetails': {}, 'message': 'NOT_A_MATCHMADE_QUEUE'}
            search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
            print("start_game = ", end = "")
            print(start_game)
            count1 = 0
            while start_game != None:
                #print(type(start_game))
                count1 += 1 # count1为尝试次数，如果search_state没有及时得到更新，意味着房间内的“寻找对局”按钮不可用（count1 means times of trying. If search_state doesn't get updated in time, it means the "Find Queue" button isn't available）
                search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json() #已知问题：队列房间序号为700时，程序在该处陷入死循环，因为“寻找对局”按钮不可用，无法更新search_state（Known problem: When queueId is 700, program is stuck in an infinite loop here, because the "Find Queue" button isn't available, which prevents search_state from updating）
                #print(search_state, end = "\n")
                if count1 > 500 and search_state["errors"] == []:
                    print("该队列房间不可用！程序即将退出！\nThis queue lobby isn't available! The program will exit soon!")
                    time.sleep(5)
                    os._exit(0)
                while search_state["errors"] != [] and search_state["errors"][0]["errorType"] == "QUEUE_DODGER":
                    print("search-state = ", end = "")
                    print(search_state, end = "\n")
                    penalty_time_remaining = int(search_state["errors"][0]["penaltyTimeRemaining"])
                    penalty_time_remaining_text_zh = ""
                    penalty_time_remaining_text_en = ""
                    penalty_hour = penalty_time_remaining // 3600
                    penalty_minute = penalty_time_remaining % 3600 // 60
                    penalty_second = penalty_time_remaining % 60
                    if penalty_hour != 0:
                        penalty_time_remaining_text_zh += str(penalty_hour) + "时"
                        penalty_time_remaining_text_en += str(penalty_hour) + " h "
                    if penalty_minute != 0:
                        penalty_time_remaining_text_zh += str(penalty_minute) + "分"
                        penalty_time_remaining_text_en += str(penalty_minute) + " m "
                    penalty_time_remaining_text_zh += str(penalty_second) + "秒"
                    penalty_time_remaining_text_en += str(penalty_second) + " s"
                    print("队列秒退计时器：由于你在英雄选择过程中退出了游戏，或者拒绝了过多场游戏，导致你无法加入队列。剩余时间：" + penalty_time_remaining_text_zh + "。\nQUEUE DODGE TIMER: Because you abandoned a recent game during champ selection or declined too many games, you're currently unable to join the queue. Penalty Time Remaining: " + penalty_time_remaining_text_en + ".")
                    input()
                    start_game = await (await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")).json()
                    search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
            print("队列中……\nIn Queue ...")
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
            while search_state["lowPriorityData"]["reason"] == "LEAVER_BUSTED":
                print("search-state = ", end = "")
                print(search_state, end = "\n")
                penalty_time_remaining = int(search_state["lowPriorityData"]["penaltyTimeRemaining"])
                penalty_time_remaining_text_zh = ""
                penalty_time_remaining_text_en = ""
                penalty_hour = penalty_time_remaining // 3600
                penalty_minute = penalty_time_remaining % 3600 // 60
                penalty_second = penalty_time_remaining % 60
                if penalty_hour != 0:
                    penalty_time_remaining_text_zh += str(penalty_hour) + "时"
                    penalty_time_remaining_text_en += str(penalty_hour) + " h "
                if penalty_minute != 0:
                    penalty_time_remaining_text_zh += str(penalty_minute) + "分"
                    penalty_time_remaining_text_en += str(penalty_minute) + " m "
                penalty_time_remaining_text_zh += str(penalty_second) + "秒"
                penalty_time_remaining_text_en += str(penalty_second) + " s"
                print("低优先级队列：放弃比赛或是挂机，会导致你的队友进行一场不公平的对局，并且会被系统视为应受惩罚的恶劣行为。你的队伍已被放置在一条低优先级队列中。离开该队列、拒绝或未能接受对局将重置这个倒计时。剩余时间：" + penalty_time_remaining_text_zh + ".\nLow Priority Queue: Abandoning a match or being AFK results in a negarive experience for your teammates, and is a punishable offense in League of Legends. You've been placed in a lower priority queue. Leaving the queue, declining or failing to accept a match will reset the timer. Time Remaining: " + penalty_time_remaining_text_en + ".")
                input()
                search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
            while gameflow_phase == "Lobby":
                gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            print("gameflow-phase = ", end = "")
            print(gameflow_phase)
            while search_state["searchState"] != "Found":
                search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
                gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                #print("gameflow-phase = " & gameflow_phase)
                if gameflow_phase == "Lobby": #这里可以考虑使用gameflow_phase进行替换。下同（It's alternative to substitute gameflow_phase for search_state here. So are the following code）
                    break
            print("search-state = ", end = "")
            print(search_state)
            print("gameflow-phase = ", end = "")
            print(gameflow_phase)   
            if gameflow_phase == "Lobby":
                print("请确认各召唤师就绪后，按回车开始匹配。\nPlease start queue by pressing Enter after confirming all ready.")
                input()
                continue
            print("对局已找到！是否接受对局？（输入任意键拒绝，否则接受）\nMatch found! Accept the match? (Press any key to decline, or null for acceptance)")
            ready_check = input()
            if ready_check == "":
                await connection.request("POST", "/lol-matchmaking/v1/ready-check/accept")
            else:
                await connection.request("POST", "/lol-matchmaking/v1/ready-check/decline")
                while search_state["searchState"] == "Found":
                    search_state = await (await connection.request("GET", "/lol-lobby/v2/lobby/matchmaking/search-state")).json()
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            count = 0 #这里count确保选英雄时游戏模式的信息只输出一次（Here the variable "count" makes sure that the game mode information will be output only once）
            while gameflow_phase == "ReadyCheck" or gameflow_phase == "ChampSelect":
                gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                if gameflow_phase == "ChampSelect" and count == 0:
                    gamemode_info = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                    print(gamemode_info)
                    count += 1
                #print("gameflow-phase = ", end = "")
                #print(gameflow_phase)
            if gameflow_phase == "Lobby":
                print("请确认各召唤师就绪后，按回车开始匹配。\nPlease start queue by pressing Enter after confirming all ready.")
                input()
            elif gameflow_phase == "Matchmaking":
                pass
            elif gameflow_phase == "InProgress":
                break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
##    print("是否查看可用队列房间序号？（输入任意键查看，否则不查看）\nCheck the available QueueID list? (Any keys for Y, or null for N)")
##    check_queueid = input()
##    if check_queueid != "":
##        await check_available_queue(connection)
    print("请选择创建队列房间还是自定义房间：（输入任意键创建队列房间，否则创建自定义房间）\nCreate a queue lobby or a custom lobby? (Any keys for a queue lobby, or null for a custom lobby)")
    lobby_selection = input()
    if lobby_selection == "":
        await create_custom_lobby(connection)
        lobby = await connection.request("GET", "/lol-lobby/v2/lobby")
        lobby_information = await lobby.json()
        if "errorCode" in lobby_information and lobby_information["message"] == "LOBBY_NOT_FOUND":
            print("房间创建失败！请检查房间参数。\nError creating the lobby! Please check the lobby parameters.")
            print(lobby_information)
        else:
            await add_bots_team1(connection)
            await add_bots_team2(connection)
        await get_lobby_information(connection)
    else:
        await create_queue_lobby(connection)
    await start_game(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
