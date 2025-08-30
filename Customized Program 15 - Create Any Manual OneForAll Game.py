from lcu_driver import Connector
import os, time

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/08/23
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector = Connector()

async def get_summoner_data(connection):
    data = await connection.request('GET', '/lol-summoner/v1/current-summoner')
    summoner = await data.json()
    print("displayName:    %s" %(summoner["gameName"] + "#" + summoner["tagLine"]))
    print("summonerId:     %s" %(summoner["summonerId"]))
    print("puuid:          %s" %(summoner["puuid"]))
    print("-")


#-----------------------------------------------------------------------------
#  lockfile
#-----------------------------------------------------------------------------
async def update_lockfile(connection):
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'w+')
        text = "LeagueClient:%d:%d:%s:%s" %(connection.pid, connection.port, connection.auth_key, connection.protocols[0])
        file.write(text)
        file.close()
    return None

async def get_lockfile(connection):
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'r')
        text = file.readline().split(':')
        file.close()
        print(connection.address)
        print(f'riot    {connection.auth_key}')
        return connection.auth_key
    return None

#-----------------------------------------------------------------------------
#  自动选英雄（Automatically select a champion）
#-----------------------------------------------------------------------------
async def autoPick(connection):
    current_summoner = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_puuid = current_summoner["puuid"]
    LoLChampion = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %current_summoner["summonerId"])).json()
    LoLChampions = {}
    for champion in LoLChampion:
        LoLChampions[champion["id"]] = champion
    print("本脚本用于帮助队友同时选择相同的英雄。请确保同队伍的成员输入的英雄序号相同。\nThis program is aimed at helping players of the same team to pick the same champion. Please ensure all teammates have submitted the same championId.\nchampionId\tname\ttitle\talias")
    time.sleep(3)
    for i in sorted(LoLChampions.keys()):
        if i == -1:
            continue
        champion = LoLChampions[i]
        print("%d\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]))
    repick = True #决定是否执行大循环（Determines whether the big while-loop is to execute）
    while repick:
        repick = False
        print('请输入英雄序号。输入“0”以查看英雄信息。\nPlease input the championId. Enter "0" to check all champion information.')
        while True:
            s = input()
            try:
                championId = int(s)
                if championId == 0:
                    print("championId\tname\ttitle\talias")
                    for i in sorted(LoLChampions.keys()):
                        if i == -1:
                            continue
                        champion = LoLChampions[i]
                        print("%d\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]))
                elif not championId in sorted(LoLChampions.keys()) and not championId == -3:
                    print("请输入合法的英雄序号！\nPlease enter a legal champion's id.")
                else:
                    break
            except ValueError:
                print("请输入正整数！\nPlease enter a positive integer!")
        if championId == -1:
            break
        print("请选择行为类型。\nPlease select an action type.\n1\t禁（Ban）\n2\t选（Pick）\n3\t投票（Vote）") #自动禁用的一个有用的地方是斗魂竞技场：通过抢先选中要禁的英雄，用户可以查看是否这名英雄会被其它人禁用。如果被别人抢先禁用了，在用户视角下可能就看不出来有没有被禁用了（A useful case of autoban is Arena: by selecting a champion to ban, the user can know whether this champion is banned by another player. If someone bans this champion before this champion is selected to be banned by the user, then in the user's vision, it can't be inferred accurately whether this champion has been banned）
        while True:
            ban = pick = vote = False
            s = input()
            if s == "":
                continue
            elif s[0] == "1":
                ban = True
                break
            elif s[0] == "2":
                pick = True
                break
            elif s[0] == "3":
                vote = True
                break
            else:
                print("您的输入有误！请重新输入。\nERROR input! Please try again.")
        print("是否直接锁定选择？（输入任意键直接锁定，否则不锁定。）\nDo you want to lock in? (Submit any non-empty string to lock in, or null to refuse locking in.)")
        complete = bool(input())
        #先确保用户进入英雄选择阶段（First, make sure the user is during champ select stage）
        if ban:
            print("等待进入英雄选择阶段的禁英雄阶段……\nWaiting for the banning stage of the champ select stage ...")
        if pick:
            print("等待进入英雄选择阶段的选英雄阶段……\nWaiting for the picking stage of the champ select stage ...")
        if vote:
            print("等待进入英雄选择阶段的投票阶段……\nWaiting for the voting stage of the champ select stage ...")
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        spectateWarningPrinted = False
        while True:
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            if gameflow_phase == "ChampSelect":
                champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                if champ_select_session["isSpectating"]:
                    if not spectateWarningPrinted:
                        print("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                        spectateWarningPrinted = True
                else:
                    break
        #下面获取用户的槽位序号（Then, get the user's cellId）
        start1 = time.time()
        localPlayerCellId = champ_select_session["localPlayerCellId"]
        end1 = time.time()
        diff1 = end1 - start1
        #下面获取用户选英雄时的行为序号（Get the user's actionId when he/she's picking a champion）
        start2 = time.time()
        action_found = False
        selfKey_pick = str(localPlayerCellId) + " pick" #只选择类型为“选英雄”的行为（Only do operations on a pick action）
        selfKey_ban = str(localPlayerCellId) + " ban" #只选择类型为“禁英雄”的行为（Only do operations on a ban action）
        selfKey_vote = str(localPlayerCellId) + " vote" #只选择类型为“投票”的行为（Only do operations on a vote action）
        selfKey = selfKey_ban if ban else selfKey_pick if pick else selfKey_vote
        while not action_found:
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            if gameflow_phase == "ChampSelect":
                champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                if "actions" in champ_select_session: #gameflow_phase == "ChampSelect"并不意味着champ_select_session准备就绪（gameflow_phase == "ChampSelect" doesn't necessarily mean champ_select_session is ready）
                    actions = {}
                    for stage in champ_select_session["actions"]:
                        for action in stage:
                            key = str(action["actorCellId"]) + " " + action["type"]
                            if key in actions and action["type"] != "ban": #在旧版征召模式中，由同一个人来禁英雄，因此在禁用期间，这个人的行为的槽位序号和行为类型是一样的。这样的键重复无关紧要，因为后面的禁用行为序号一定比前面的禁用行为序号大，所以程序总是能追踪到最新的禁用行为（In old draft mode, one player bans multiple champions, so during the ban phase, the actorCellIds and types are both the same among this player's actions. In this case, the key duplicate doesn't matter, for the id of the later ban action is always greater than that of the earlier ban action, which means the program will always track the latest ban action）
                                print("检测到重复键（%s）。请修改代码。\nDetected the same key (%s). Please fix the code." %(key, key))
                            actions[key] = action
                    if selfKey in actions:
                        action_found = True
                        pick_actionId = actions[selfKey]["id"]
                        end2 = time.time()
                        diff2 = end2 - start2
                    # actions = []
                    # for stage in champ_select_session["actions"]:
                    #     actions += stage
                    # for action in actions:
                    #     if action["actorCellId"] == localPlayerCellId and action["type"] == "pick":
                    #         print(action)
                    #         action_found = True
                    #         pick_actionId = action["id"]
                    #         break
            else:
                print("您已退出英雄选择阶段！请重新选择英雄。\nYou've exited the champ select stage! Please pick the champion again.")
                repick = True
                break
        #下面通过LCU API选择英雄（Pick a champion through LCU API)
        if action_found:
            start3 = time.time()
            body = {"id": pick_actionId, "actorCellId": localPlayerCellId, "championId": championId, "type": "pick", "completed": complete, "isAllyAction": True, "isInProgress": True, "pickTurn": 0}
            response = await (await connection.request("PATCH", "/lol-champ-select/v1/session/actions/%d" %pick_actionId, data = body)).json()
            end3 = time.time()
            diff3 = end3 - start3
            print(body)
            print(response)
            #校验用户是否成功选择想要选择的英雄（Verify whether the user has successfully picked the expected champion）
            #time.sleep(1) #从选英雄到英雄会话数据更新有一定延迟，特别是在外国服务器（There's some lag between picking a champion and updating the session data, especially in a foreign server）
            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            actions = []
            for stage in champ_select_session["actions"]:
                actions += stage
            for action in actions:
                if action["id"] == pick_actionId:
                    if action["championId"] == championId:
                        print("自动选择成功！\nAutopick succeeded!")
                    else:
                        print("自动选择失败！\nAutopick failed!")
                    break
            # print("获取槽位序号所花费的时间（Time spent in getting cellId）：%d\n获取行为序号所花费的时间（Time spent in getting actionId）：%d\n选择英雄所花费的时间（Time spent in picking the champion）：%d\n从进入英雄选择阶段到选择英雄所花费的总时间（Total time spent from entering the champ select stage to picking the champion）：%d" %(diff1, diff2, diff3, end3 - start1))
            # print(start1)
            # print(end1)
            # print(start2)
            # print(end2)
            # print(start3)
            # print(end3)
            repick = True


#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await autoPick(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
