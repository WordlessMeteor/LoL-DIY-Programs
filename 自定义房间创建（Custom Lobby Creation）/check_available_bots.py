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
#print("是否查看可用电脑玩家列表？（输入任意键查看，否则不查看）\nCheck the availbale-bots list? (Any keys for Y, or null for N)")
#check_botlist = input()
#if check_botlist != "":
    #print("*****************************************************************************")
    #print("championId\t" + "{0:^14}".format("CN") + "\t" + "{0:^14}".format("EN"))
    #for h in range(len(localdata)):
        #print("{0:<10}".format(str(localdata["championId"][h])) + "\t" + "{0:<14}".format(localdata["CN"][h]) + "\t" + "{0:<14}".format(localdata["EN"][h]))
    #print("*****************************************************************************\n")

connector = Connector()

#-----------------------------------------------------------------------------
# 获得召唤师数据（Get access to summoner data）
#-----------------------------------------------------------------------------
async def get_summoner_data(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    #print(f"displayName:    {summoner['displayName']}")
    #print(f"summonerId:     {summoner['summonerId']}")
    #print(f"puuid:          {summoner['puuid']}")
    #print("-")


#-----------------------------------------------------------------------------
#  lockfile
#-----------------------------------------------------------------------------
async def get_lockfile(connection):
    path = os.path.join(connection.installation_path.encode("gb18030").decode("utf-8"), "lockfile")
    if os.path.isfile(path):
        file = open(path, "r")
        text = file.readline().split(":")
        file.close()
        #print(connection.address)
        #print(f"riot    {connection.auth_key}")
        return connection.auth_key
    return None

#-----------------------------------------------------------------------------
# 创建自定义房间（Create a custom lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    data = await connection.request("GET", "/lol-summoner/v1/current-summoner")
    summoner = await data.json()
    gameMode = ["CLASSIC","ARAM","PRACTICETOOL"]
    mapId = [11,12,11]
    #print("请选择自定义房间的游戏类型：\nPlease select a game mode of the lobby:\n1\t召唤师峡谷（Summoner's Rift）\n2\t嚎哭深渊（Howling Abyss）\n3\t训练模式（Practice Tool）\n3")
    while True:
        TypeNumber = "3"
        if TypeNumber == "":
            continue
        elif TypeNumber in {"1","2","3"}:
            TypeNumber = int(TypeNumber)
            custom = {
                "customGameLobby": {
                    "configuration": {
                        "gameMode": gameMode[TypeNumber - 1],
                        "gameMutator": "",
                        "gameServerRegion": "",
                        "mapId": mapId[TypeNumber - 1],
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
            break
        else:
            print("游戏类型输入错误！请重新输入：\nError input of game mode! Please try again:")

#-----------------------------------------------------------------------------
# 添加单个机器人（Add a bot）
#-----------------------------------------------------------------------------
async def add_bots_team(connection):
    global official_available_bots
    activedata = await connection.request('GET', '/lol-lobby/v2/lobby/custom/available-bots')
    official_available_bots = [ bot['id'] for bot in await activedata.json() ]
    champion = {
                    "championId": i,
                    "botDifficulty": "MEDIUM",
                    "teamId": "200"
                }
    await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = champion)
    time.sleep(0.1)
    data = await connection.request("GET", "/lol-lobby/v2/lobby")
    bot = await data.json()
    if bool(bot["gameConfig"]["customTeam200"]):
        bot_name = bot["gameConfig"]["customTeam200"][0]["botId"][4:-4]
        available_bots[i] = bot_name
        print(str(i) + "\t" + bot_name)
        

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    #await get_summoner_data(connection)
    #await get_lockfile(connection)
    await create_custom_lobby(connection)
    await add_bots_team(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

print("请输入待检测的电脑玩家ID范围上下限，以空格为分隔符：\nPlease input the superior and inferior limit of the range of botChampionIds to be checked:")
while True:
    try:
        inf,sup = map(int,input().split())
        if sup < inf:
            sup,inf = inf,sup
        break
    except ValueError:
        print("您的输入有误，请重新输入！\nInput ERROR! Please try again!")
available_bots = {}
unofficial_available_bots = {}
print("ID\tName")
for i in range(inf,sup):
    connector.start()
print("\n从ID = " + str(inf) + "到ID = " + str(sup - 1) + "共有" + str(len(available_bots)) + "名可用电脑玩家。")
print("From ID = " + str(inf) + " to ID = " + str(sup - 1) + ", " + str(len(available_bots)) + " IDs in total are available.")
for i in available_bots:
    if i not in official_available_bots:
        unofficial_available_bots[i] = available_bots[i]
print("以下" + str(len(unofficial_available_bots)) + "名电脑玩家非官方可用但可添加：")
print("The following " + str(len(unofficial_available_bots)) + " bots can be added unofficially:")
for i in unofficial_available_bots:
    print(str(i) + "\t" + unofficial_available_bots[i])
print("检查完成，可添加以上电脑玩家。请复制到剪贴板后按任意键退出……\nCheck finished. The bots above can be added. Please copy the bots' information and press any key to quit ...")
input()
