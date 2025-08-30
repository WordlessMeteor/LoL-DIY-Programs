from lcu_driver import Connector
import pandas, random, time, uuid

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/06/09
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
localdata = pandas.read_excel("../../available-bots.xlsx", sheet_name = "Sheet2", index_col = 0, usecols = list(range(1, 5)), skiprows = [1])
names = {championId: localdata.at[championId, "name"] for championId in localdata.index}
aliases = {championId: localdata.at[championId, "alias"] for championId in localdata.index}
botPositions_CN = {"TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "UTILITY": "辅助"}
roles_CN = {"assassin": "刺客", "fighter": "战士", "mage": "法师", "marksman": "射手", "support": "辅助", "tank": "坦克", "arbitrary": "任意"}
all_bots = list(names.keys())
print("是否查看可用电脑玩家列表？（输入任意键查看，否则不查看）\nCheck the availbale-bots list? (Any keys for Y, or null for N)")
check_botlist = input()
if check_botlist != "":
    print("*****************************************************************************")
    print("championId\t" + "{0:^14}".format("name") + "\t" + "{0:^14}".format("alias"))
    for championId in localdata.index:
        print("{0:<10}".format(str(championId)) + "\t" + "{0:<14}".format(names[championId]) + "\t" + "{0:<14}".format(aliases[championId]))
    print("*****************************************************************************\n")

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
    #英雄的推荐路线（Recommended positions for champions）
    recommended_position_for_champion = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    recommended_position_for_champion_keys = list(recommended_position_for_champion.keys())
    for championId in recommended_position_for_champion_keys:
        if not int(championId) in all_bots:
            del recommended_position_for_champion[championId]
    #可用的路线（Available lanes）
    botPositions = set()
    for champion in recommended_position_for_champion.values():
        botPositions |= set(champion["recommendedPositions"])
    #将botPositions排序整理为["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    botPositions = list(botPositions)
    botPositions_tmp = []
    for position in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
        if position in botPositions:
            botPositions.remove(position)
            botPositions_tmp.append(position)
    botPositions = botPositions_tmp + botPositions
    #botPositions = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    #各路线上的英雄（Champions on each lane）
    recommended_champion_for_position = {} #用于生成某条分路的随机英雄（Used to generate random champions of specific positions respectively）
    for position in botPositions:
        recommended_champion_for_position[position] = []
    for championId in recommended_position_for_champion:
        for position in recommended_position_for_champion[championId]["recommendedPositions"]:
            recommended_champion_for_position[position].append(int(championId))
    for position in recommended_champion_for_position:
        recommended_champion_for_position[position].sort()
    #角色定位（Champion roles）
    roles = set()
    for champion in LoLChampions.values():
        roles |= set(champion["roles"])
    #将roles排序整理为["assassin", "fighter", "mage", "marksman", "support", "tank"]
    roles = list(roles)
    roles_tmp = []
    for role in ["assassin", "fighter", "mage", "marksman", "support", "tank"]:
        if role in roles:
            roles.remove(role)
            roles_tmp.append(role)
    roles = roles_tmp + roles
    #roles = ["assassin", "fighter", "mage", "marksman", "support", "tank"]
    #各角色定位的英雄（Champions of each role）
    recommended_champion_for_role = {} #用于生成某个角色定位的随机英雄（Used to generate random champions of specific roles respectively）
    for role in roles:
        recommended_champion_for_role[role] = []
    for championId in LoLChampions:
        for role in LoLChampions[championId]["roles"]:
            recommended_champion_for_role[role].append(championId)
    #可用的电脑玩家难度（Available bot difficulty）
    botDifficulty = ["EASY", "HARD", "MEDIUM", "RSINTRO", "RSBEGINNER", "RSINTERMEDIATE", "RSWARMINTRO"]
    print("队伍%s：请选择自选电脑玩家或者随机生成电脑玩家：\nTeam %s: Please select the option to generate bot players:\n0\t跳过该队伍（Skip this team）\n1\t完全随机生成（Completely Randomly）\n2\t按照分路随机生成（Randomly according to Positions）\n3\t自选（By Picking）" %(teamId[0], teamId[0]))
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
                elif i in map(str, range(1, maxTeamSize + 1)):
                    i = int(i)
                    while True:
                        team = random.sample(all_bots, i)
                        print("程序为您分配到以下英雄：\nYou have been distributed the following bot champions:\n*****************************************************************************")
                        for j in team:
                            print("{0:<14}".format(names[j]) + "\t" + "{0:<14}".format(aliases[j]) + "\t" + str(recommended_position_for_champion[str(j)]["recommendedPositions"]))
                        print("*****************************************************************************\n是否重新随机英雄？（输入任意键以重新随机，否则进行下一步）\nDo you want to regenerate the champions? (Input anything to reroll, or null to enter the next step)")
                        if not bool(input()):
                            break
                    break
                else:
                    print("电脑玩家数量不合法！请重新输入：\nIllegal bot players number! Please try again:")
            break
        elif o[0] == "2":
            print(f'请输入分路，以空格为分隔符。（默认使用全分路。）\nPlease enter the bot positions split by space (among {botPositions}, which is taken by default.)')
            while True:
                botPositions_add = input().split()
                if botPositions_add == []:
                    botPositions_add = botPositions[:]
                if all(map(lambda x: x in botPositions, botPositions_add)):
                    botPositions_add = botPositions_add[:maxTeamSize]
                    break
                else:
                    print(f"电脑玩家路线错误！请选择{botPositions}中的一个：\nError input of botDifficulty! Please choose among {botPositions}:")
            while True:
                back = False
                print("您想要对战什么样的阵容？\nWhat comp do you want to fight against?\n1\t清一色阵容（Full comp）\n2\t自定义阵容（Customized comp）\n3\t任意阵容（Arbitrary comp）")
                comp_specified = False
                comp_option = input()
                if comp_option != "" and comp_option[0] == "1":
                    print("请选择角色定位类型：\nPlease select a role type:\n1\t纯刺客（All assassin）\n2\t纯战士（All fighters）\n3\t纯法师（All mages）\n4\t纯射手（All marksmen）\n5\t纯辅助（All supports）\n6\t纯坦克（All tanks）")
                    while True:
                        fullcomp_role_option = input()
                        if fullcomp_role_option in list(map(str, range(1, len(roles) + 1))):
                            comp_specified = True
                            comp_role = roles[int(fullcomp_role_option) - 1]
                            print("您选择了纯%s阵容。\nYou chose all-%s comp." %(roles_CN[comp_role], comp_role))
                            break
                        elif fullcomp_role_option == "0":
                            back = True
                            break
                        else:
                            print("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if back:
                        continue
                    comp_roles = [comp_role] * len(botPositions_add)
                    role_specific_championIds = [recommended_champion_for_role[comp_role]] * len(botPositions_add)
                elif comp_option != "" and comp_option[0] == "2":
                    print("请依次为上路、打野、中路、下路和辅助位置指定英雄角色定位，以空格为分隔符。\nPlease specify the roles for TOP, JUNGLE, MIDDLE, BOTTOM and UTILITY champions, respectively, split by space.\n1\t刺客（Assassin）\n2\t战士（Fighter）\n3\t法师（Mage）\n4\t射手（Marksman）\n5\t辅助（Support）\n6\t坦克（Tank）\n示例输入（Example）：\n2 2 3 4 6\n4 6 1 3 5")
                    while True:
                        try:
                            comp_role_numbers = list(map(int, input().split()))
                        except ValueError:
                            print("您的输入有误！请输入整数。\nERROR input! Please enter integers.")
                        else:
                            if comp_role_numbers == [0]:
                                back = True
                                break
                            elif len(comp_role_numbers) != len(botPositions_add):
                                print("数量不符！请输入%d个位置的英雄角色定位。\nLength mismatch! Please enter %d champion roles." %(len(botPositions_add), len(botPositions_add)))
                            elif any(map(lambda x: x < 1 or x > 6, comp_role_numbers)):
                                print("您的输入有误！请输入1～6之间的正整数。\nERROR input! Please enter positive integers between 1 and 6.")
                            else:
                                comp_specified = True
                                comp_roles = list(map(lambda x: roles[x - 1], comp_role_numbers))
                                comp_role_str_zh = "、".join(list(map(lambda x: roles_CN[roles[x - 1]], comp_role_numbers)))
                                comp_role_str_en = ", ".join(list(map(lambda x: roles[x - 1], comp_role_numbers)))
                                print(f"您为上路、打野、中路、下路和辅助位置分别指定了{comp_role_str_zh}英雄。\nYou specified {comp_role_str_en} champions for TOP, JUNGLE, MIDDLE, BOTTOM and UTILITY champions, respectively.")
                                break
                    if back:
                        continue
                    role_specific_championIds = [recommended_champion_for_role[roles[i - 1]] for i in comp_role_numbers]
                else:
                    comp_roles = ["arbitrary"] * len(botPositions_add)
                    role_specific_championIds = [all_bots] * len(botPositions_add)
                break
            sample_notfound_hints_printed = [False] * len(botPositions_add) #有些分路可能没有特定的角色。这样的提示只需要输出一遍（Some lanes might be lack of certain roles. Such hints only need to be printed once）
            while True:
                team = []
                for i in range(len(botPositions_add)):
                    position = botPositions_add[i]
                    role = comp_roles[i]
                    candidate_champions = sorted(set(recommended_champion_for_position[position]) & set(role_specific_championIds[i]))
                    if len(candidate_champions) == 0:
                        if not sample_notfound_hints_printed[i]:
                            print("%s位置无%s英雄。将不再限定角色定位。\nNo %s champions found for %s. The program will use another arbitrary role." %(botPositions_CN[position], roles_CN[role], role, position))
                            sample_notfound_hints_printed[i] = True
                        candidate_champions = recommended_champion_for_position[position]
                        comp_roles[i] = "arbitrary"
                    team += random.sample(candidate_champions, 1)
                print("程序为您分配到以下英雄：\nYou have been distributed the following bot champions:\n*****************************************************************************")
                for i in range(len(team)):
                    print("{0:<14}".format(names[team[i]]) + "\t" + "{0:<14}".format(aliases[team[i]]) + "\t" + botPositions_add[i] + "\t" + comp_roles[i])
                print("*****************************************************************************\n是否重新随机英雄？（输入任意键以重新随机，否则进行下一步）\nDo you want to regenerate the champions? (Input anything to reroll, or null to enter the next step)")
                tmp = input()
                if tmp == "" or tmp[0] == "s":
                    break
            if tmp != "" and tmp[0] == "s": #隐藏功能：自行指定（Hidden function: manually specify the champions）
                print('''请按照“上路—打野—中路—下路—辅助”的顺序逐行输入电脑玩家的英雄序号：\nPlease input the bot championIds in the "TOP-JUNGLE-MIDDLE-BOTTOM-UTILITY" order, one bot per line:''')
                team = []
                for position in botPositions:
                    while True:
                        try:
                            championId = input()
                            if championId == "":
                                continue
                            else:
                                championId = int(championId)
                                if championId in recommended_champion_for_position[position]:
                                    team.append(championId)
                                    print("您已选择以下英雄：\nYou have selected the bot champions as follows:\n*****************************************************************************")
                                    for i in range(len(team)):
                                        print("{0:<14}".format(names[team[i]]) + "\t" + "{0:<14}".format(aliases[team[i]]) + "\t" + botPositions[i])
                                    print("*****************************************************************************")
                                    break
                                elif championId in all_bots:
                                    recommended_position_str_zh = "、".join(list(map(lambda x: botPositions_CN[x], recommended_position_for_champion[str(championId)]["recommendedPositions"])))
                                    recommended_position_str_en = ", ".join(recommended_position_for_champion[str(championId)]["recommendedPositions"])
                                    print("%s的推荐路线是%s。请选择一位适合%s的英雄，或者在选择%s位英雄时输入该英雄的序号。\nThe recommended positions for %s include %s. Please select a champion whose recommended positions include %s, or input this championId when selecting champions of the following lane(s): %s." %(names[championId], recommended_position_str_zh, botPositions_CN[position], recommended_position_str_zh, aliases[championId], recommended_position_str_en, position, recommended_position_str_en))
                                elif championId in LoLChampions:
                                    print("没有名为%s的电脑玩家。请对照可用电脑玩家工作簿的第一张工作表选择一个%s英雄。\nThere's not a bot named %s. Please refer to Sheet1 of the available-bots workbook and select a %s champion." %(LoLChampions[championId]["name"], botPositions_CN[position], LoLChampions[championId]["alias"], position))
                                else:
                                    print(f"没有序号为{championId}的英雄。请重新输入！\nNo champion with championId {championId}. Please try again!")
                        except ValueError:
                            print("您的输入有误！请输入一个正整数。\nERROR input of championId! Please submit a positive integer.")
            break
        else:
            print("请输入电脑玩家的id，以空格为分隔符：\nPlease input the ids of bot players, split by space:")
            while True:
                try:
                    team = list(map(int, input().split()))
                except ValueError:
                    print("您的输入有误，请重新输入！\nInput ERROR! Please try again!")
                else:
                    break
            print("您已选择以下英雄：\nYou have selected the bot champions as follows:\n*****************************************************************************")
            for j in team:
                print("{0:<14}".format(names[j]) + "\t" + "{0:<14}".format(aliases[j]) + "\t" + str(recommended_position_for_champion[str(j)]["recommendedPositions"]))
            print("*****************************************************************************")
            break

    botUuid_team = []
    print("是否设定电脑玩家难度一致？（输入任意键设定为不一致，否则一致）\nSet all botDifficulties identical? (Any keys for N, or null for Y)")
    botDifficulty_consistency = not bool(input())
    if botDifficulty_consistency:
        print(f"请输入电脑玩家的难度：\nPlease enter the botDifficulty: (among {botDifficulty})")
        while True:
            botDifficulty_team = input()
            if botDifficulty_team == "":
                continue
            elif botDifficulty_team in botDifficulty:
                break
            else:
                print(f"电脑玩家难度输入错误！请选择{botDifficulty}中的一个：\nError input of botDifficulty! Please choose among {botDifficulty}:")
        if o[0] == "2":
            botPosition_team = botPositions_add[:]
            for i in range(len(team)):
                Id = team[i]
                botUuid = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                bot = {"championId": Id, "botDifficulty": botDifficulty_team, "teamId": teamId, "position": botPositions_add[i], "botUuid": botUuid}
                response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
        else:
            print(f"请依次输入电脑玩家路线：\nPlease enter the botPositions: (among {botPositions})")
            botPosition_team = []
            for i in range(len(team)):
                Id = team[i]
                botUuid = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                while True:
                    botPosition_tmp = input()
                    if botPosition_tmp == "":
                        continue
                    elif botPosition_tmp in botPositions:
                        botPosition_team.append(botPosition_tmp)
                        bot = {"championId": Id, "botDifficulty": botDifficulty_team, "teamId": teamId, "position": botPosition_tmp, "botUuid": botUuid}
                        response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
                        break
                    else:
                        print(f"电脑玩家路线错误！请选择{botPositions}中的一个：\nError input of botDifficulty! Please choose among {botPositions}:")
        print("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
        for i in range(len(team)):
            print("{0:<14}".format(names[team[i]]) + "\t" + "{0:<14}".format(aliases[team[i]]) + "\t" + botDifficulty_team + "\t" + botPosition_team[i] + "\t" + botUuid_team[i])
        print("*****************************************************************************\n")
    else:
        if o[0] == "2":
            print(f"请依次输入电脑玩家的难度：\nPlease enter the botDifficulty: (among {botDifficulty})")
            botDifficulty_team = []
            botPosition_team = botPositions_add[:]
            for i in range(len(team)):
                Id = team[i]
                botUuid = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                botPosition_tmp = botPositions_add[i]
                while True:
                    botDifficulty_tmp = input()
                    if botDifficulty_tmp == "":
                        continue
                    elif botDifficulty_tmp in botDifficulty:
                        botDifficulty_team.append(botDifficulty_tmp)
                        bot = {"championId": Id, "botDifficulty": botDifficulty_tmp, "teamId": teamId, "position": botPosition_tmp, "botUuid": botUuid}
                        response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
                        break
                    else:
                        print(f"电脑玩家难度输入错误！请选择{botDifficulty}中的一个：\nError input of botDifficulty! Please choose among {botDifficulty}:")
        else:
            print(f"请依次输入电脑玩家的难度和路线，以空格为分隔符：\nPlease enter the botDifficulty (among {botDifficulty}) and role (among {botPositions}), split by space:")
            botDifficulty_team = []
            botPosition_team = []
            for i in range(len(team)):
                Id = team[i]
                botUuid = str(uuid.uuid4())
                botUuid_team.append(botUuid)
                while True:
                    tmp = input()
                    if tmp == "":
                        continue
                    else:
                        try:
                            botDifficulty_tmp, botPosition_tmp = tmp.split()
                        except ValueError:
                            print("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
                        else:
                            if botDifficulty_tmp in botDifficulty and botPosition_tmp in botPositions:
                                botDifficulty_team.append(botDifficulty_tmp)
                                botPosition_team.append(botPosition_tmp)
                                bot = {"championId": Id, "botDifficulty": botDifficulty_tmp, "teamId": teamId, "position": botPosition_tmp, "botUuid": botUuid}
                                response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
                                break
                            elif not botDifficulty_tmp in botDifficulty and botPosition_tmp in botPositions:
                                print(f"电脑玩家难度输入错误！请选择{botDifficulty}中的一个：\nError input of botDifficulty! Please choose among {botDifficulty}:")
                            elif botDifficulty_tmp in botDifficulty and not botPosition_tmp in botPositions:
                                print(f"电脑玩家路线输入错误！请选择{botPositions}中的一个：\nError input of botPositions! Please choose among {botPositions}:")
                            else:
                                print(f"电脑玩家难度和路线输入错误！\nError input of botDifficulty!\n请选择{botDifficulty}中的一个作为电脑玩家难度。\nPlease choose among {botDifficulty} as botDifficulty.\n请选择{botPositions}中的一个作为电脑玩家路线。\nPlease choose among {botDifficulty} as botPositions.")
        print("您的最终选择如下：\nYour final choices are as follows:\n*****************************************************************************")
        for i in range(len(team)):
            print("{0:<14}".format(names[team[i]]) + "\t" + "{0:<14}".format(aliases[team[i]]) + "\t" + botDifficulty_team[i] + "\t" + botPosition_team[i] + "\t" + botUuid_team[i])
        print("*****************************************************************************\n")

#-----------------------------------------------------------------------------
# 获取房间信息（Get lobby information）
#-----------------------------------------------------------------------------
async def get_lobby_information(connection):
    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    print(lobby_information)
    time.sleep(5)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    #await create_custom_lobby(connection)
    await add_bots_team(connection, teamId = "100")
    await add_bots_team(connection, teamId = "200")
    time.sleep(0.1)
    await get_lobby_information(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
