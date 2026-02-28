from lcu_driver import Connector
from lcu_driver.connection import Connection
import numpy, pandas, time
from typing import Any, Optional
from src.utils.summoner import get_summoner_data
from src.utils.format import format_df
from src.core.dataframes.champions import sort_inventory_champions
from src.core.dataframes.gameflow import update_champ_select_session

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/02/10
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector: Connector = Connector()

#-----------------------------------------------------------------------------
#  自动选英雄（Automatically select a champion）
#-----------------------------------------------------------------------------
ChampSelectSession_update_hint_printed: bool = False

async def autoPick(connection: Connection, championId: int = -1, actionType: str = "pick", complete: bool = False) -> None:
    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    #下面获取用户的槽位序号（Then, get the user's cellId）
    start1: float = time.time()
    localPlayerCellId: int = champ_select_session["localPlayerCellId"]
    end1: float = time.time()
    diff1: float = end1 - start1
    #下面获取用户选英雄时的行为序号（Get the user's actionId when he/she's picking a champion）
    start2:float = time.time()
    action_found: bool = False
    selfKey: str = f"{localPlayerCellId} {actionType}"
    while not action_found:
        gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase == "ChampSelect":
            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            if "actions" in champ_select_session: #gameflow_phase == "ChampSelect"并不意味着champ_select_session准备就绪（gameflow_phase == "ChampSelect" doesn't necessarily mean champ_select_session is ready）
                actions: dict[str, dict[str, Any]] = {}
                for stage in champ_select_session["actions"]:
                    for action in stage:
                        key: str = str(action["actorCellId"]) + " " + action["type"]
                        if key in actions and action["type"] != "ban": #在旧版征召模式中，由同一个人来禁英雄，因此在禁用期间，这个人的行为的槽位序号和行为类型是一样的。这样的键重复无关紧要，因为后面的禁用行为序号一定比前面的禁用行为序号大，所以程序总是能追踪到最新的禁用行为（In old draft mode, one player bans multiple champions, so during the ban phase, the actorCellIds and types are both the same among this player's actions. In this case, the key duplicate doesn't matter, for the id of the later ban action is always greater than that of the earlier ban action, which means the program will always track the latest ban action）
                            print("检测到重复键（%s）。请修改代码。\nDetected the same key (%s). Please fix the code." %(key, key))
                        actions[key] = action
                if selfKey in actions:
                    action_found = True
                    previous_action: dict[str, Any] = actions[selfKey]
                    print("已找到行为： | Action found:")
                    print(previous_action)
                    pick_actionId: int = previous_action["id"]
                    end2: float = time.time()
                    diff2: float = end2 - start2
                # actions: list[dict[str, Any]] = []
                # for stage in champ_select_session["actions"]:
                #     actions += stage
                # for action in actions:
                #     if action["actorCellId"] == localPlayerCellId and action["type"] == actionType:
                #         print(action)
                #         action_found = True
                #         pick_actionId = action["id"]
                #         break
        else:
            print("您已退出英雄选择阶段！请重新选择英雄。\nYou've exited the champ select stage! Please pick the champion again.")
            break
    #下面通过LCU API选择英雄（Pick a champion through LCU API)
    if action_found: #找到动作的情况下，用户一定没有退出英雄选择阶段，因此下面的英雄选择会话获取无需做异常处理（If the action is found, the user can't quit the champ select stage, so no exception handling is set for the following champ select session）
        print("请求主体如下： | Request body is as follows:")
        start3: float = time.time()
        ready: bool = False
        body: dict[str, Any] = {"id": pick_actionId, "actorCellId": localPlayerCellId, "championId": championId, "type": actionType, "completed": complete, "isAllyAction": True, "isInProgress": True, "pickTurn": 0}
        print(body)
        previous_response: Optional[dict[str, Any]] = None
        while not ready:
            current_response: Optional[dict[str, Any]] = await (await connection.request("PATCH", "/lol-champ-select/v1/session/actions/%d" %pick_actionId, data = body)).json()
            if current_response != previous_response:
                print(current_response)
                previous_response = current_response
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            if gameflow_phase == "ChampSelect":
                champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                if not "errorCode" in champ_select_session:
                    action_found = False #这里的action_found和上面的action_found作用不同，只用于退出嵌套for循环（This `action_found` doesn't play the same role as the previous one. It's only designed to exit the nested for-loop）
                    for stage in champ_select_session["actions"]:
                        for action in stage:
                            if selfKey == str(action["actorCellId"]) + " " + action["type"]:
                                action_found = True
                                if action != previous_action:
                                    print("已更新行为： | Updated action:")
                                    print(action)
                                    previous_action = action
                                if not (actionType == "ban" and champ_select_session["timer"]["phase"] == "PLANNING") and (action["championId"] == championId and action["completed"] == complete or action["isInProgress"]): #需要注意，一个动作不一定只有在正在进行中时才能进行操作。比如在公布禁用英雄时就已经可以锁定英雄了，以及在规划阶段和禁用阶段就可以声明想玩的英雄了。克隆大作战的投票动作同理。相对应的，一个动作即使正在进行中，也不一定能进行操作，比如在声明想玩的英雄时，英雄选择会话数据显示禁用行为正在进行，但那时实际上不能禁用英雄（Note that an action can be completed not only when it's in progress. For example, when the banned champions are being revealed, the user can complete locking a champion. Another example is one can always declare the champion he/she wants to play during the planning and banning phases. So as the vote action in One for All. On the other hand, even if an action is in progress, it's not necessarily operable. For example, while declaring the champion intent, the champ select session data show that the ban action is in progress, but actually the user can't ban a champion then）
                                    ready = True #ready为真对应两种场景：一种场景是自选模式（如匹配模式和人机对战），在进入英雄选择阶段的瞬间所有动作（人机对战则为所有人类动作）都是正在进行中的，这时在第一次执行该while循环时，在`current_response`中即完成了该动作。而且在这种情况下，由于进入英雄选择阶段的瞬间就完成了动作，所以响应主体为空，与先前定义的`previous_response`相同，程序就不会将该信息输出到终端。另一种场景是征召模式（如排位赛 单排/双排），在公布已禁用英雄时（如`ten_bans_reveal`），英雄选择会话数据显示选英雄动作正在等待进度，而实际上在这个阶段是可以直接锁定英雄的，同样由随后的某个while循环中的`current_response`定义部分完成了该动作。两种情况下，动作都已经完成了，因此在退出该循环后，不需要再发送一次请求。如果因为某些原因，导致动作没有如期完成（没有选到指定英雄，或者选到了指定英雄但无法锁定），则程序会等待该动作在英雄选择会话数据中呈现为正在进行时执行该步，这样在输出`current_response`时也能提示用户为什么没能选到想选的英雄【There're two circumstances where `ready` is True: one is SimulPick (e.g. Normal and Co-op vs. AI), where all actions (or human actions in Co-op vs. AI) are in progress the instance players enter the champ select stage. In this case, the first time this while-loop is executed, the definition of `current_response` finishes this action (maybe completed or maybe not). What's more, since this action is finished the moment the user enters the champ select stage, the response body should be empty, which equals `previous_response`, so this empty response body won't be output to terminal. The other is Draft Mode (e.g. Ranked Solo/Duo), where while banned champions are being revealed (e.g. during `ten_bans_reveal` stage), the champ select session shows the pick action is waiting to become InProgress, but actually the user can directly lock the champion he/she wants to play, with the definition of `current_response` at some later while-loop. In both circumstances, the action is finished, so after exiting the loop, the program doesn't need to send another request. If for some reason, the action isn't finished as expected (either the user fails to select the specific champion or the champion is selected but can't be locked), then the program will wait for this action to become InProgress in the champ select session data and then execute this step. In this way, the program should output the response body when printing `current_response`, showing why the user failed to pick the wanted champion】
                                break
                        if action_found:
                            break
            else:
                print("您已退出英雄选择阶段！请重新选择英雄。\nYou've exited the champ select stage! Please pick the champion again.")
                break
        end3: float = time.time()
        diff3: float = end3 - start3
        #校验用户是否成功选择想要选择的英雄（Verify whether the user has successfully picked the expected champion）
        #time.sleep(1) #从选英雄到英雄会话数据更新有一定延迟，特别是在外国服务器（There's some lag between picking a champion and updating the session data, especially in a foreign server）
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase == "ChampSelect":
            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            actions = [action for stage in champ_select_session["actions"] for action in stage]
            for action in actions:
                if action["id"] == pick_actionId:
                    if action["championId"] == championId and action["completed"] == complete:
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

async def autoBench(connection: Connection, championId: int = -1, lagged_pick: bool = False, timer: float = 0) -> None:
    global ChampSelectSession_update_hint_printed
    #如果将候选视为一种行为，由于模式本身决定是否能候选，因此一旦模式支持候选，即视为动作已找到（If bench is considered as an action, since the mode itself determines whether one can "bench", once it does, the action is considered as found）
    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
    localPlayerCellId: int = champ_select_session["localPlayerCellId"]
    selfKey: str = f"{localPlayerCellId} pick"
    actions: list[dict[str, Any]] = [action for stage in champ_select_session["actions"] for action in stage]
    for action in actions:
        if selfKey == str(action["actorCellId"]) + " " + action["type"]:
            previous_action: dict[str, Any] = action
            break
    print("已找到行为： | Action found:")
    print(previous_action)
    if lagged_pick:
        if not ChampSelectSession_update_hint_printed:
            print("正在更新英雄选择会话。你可能会注意到你的召唤师技能顺序发生了对调。不用担心，程序会将其调换回来。\nUpdating the champ select session. You might notice the order of your summoner spells are reversed. Don't worry. The program will restore it.")
            ChampSelectSession_update_hint_printed = True
        else:
            print("正在更新英雄选择会话。\nUpdating the champ select session.")
        champ_select_session = update_champ_select_session(connection, champ_select_session, force_update = True)
        currentTimeLeft: float = champ_select_session["timer"]["adjustedTimeLeftInPhase"] / 1000 #英雄联盟中的时间主要以毫秒计（Times in League of Legends are most counted by millisecond）
        if currentTimeLeft < timer:
            print("当前剩余时间（{0:g}秒）已不足{1:g}秒。将立刻选择。\nCurrent time left in phase ({0:g} seconds) is less than {1:g} seconds. The program is going to swap for this champion right away.".format(currentTimeLeft, timer))
        else:
            print("正在等待计时器到达{0:g}秒。当前剩余时间：{1:g}秒。\nWaiting for the timer to reach {0:g} seconds. Current time left: {1:g} seconds.".format(timer, currentTimeLeft))
            time.sleep(currentTimeLeft - timer)
        gameflow_phase: str = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase == "ChampSelect":
            response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-champ-select/v1/session/bench/swap/{championId}")).json()
            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            if "errorCode" in champ_select_session:
                print("您已退出英雄选择阶段！请重新选择英雄。\nYou've exited the champ select stage! Please pick the champion again.")
            else:
                actions = [action for stage in champ_select_session["actions"] for action in stage]
                for action in actions:
                    if selfKey == str(action["actorCellId"]) + " " + action["type"]:
                        if action != previous_action:
                            print("已更新行为： | Updated action:")
                            print(action)
                        if action["championId"] == championId:
                            print("自动选择成功！\nAutopick succeeded!")
                        else:
                            print("自动选择失败！\nAutopick failed!")
                        break
        else:
            print("您已退出英雄选择阶段！请重新选择英雄。\nYou've exited the champ select stage! Please pick the champion again.")
    else:
        ready: bool = False
        previous_response: Optional[dict[str, Any]] = None
        while not ready: #这里认为大乱斗随时都有可能出现自己想玩的英雄，因此直接写while True循环，当且仅当用户选到想玩的英雄或者不在英雄选择阶段时才退出循环。这样可能会导致一个后果：最后一秒，有人把自己想玩的英雄放到了替补英雄池中，然后来不及换符文了（Considering the wanted champion may appear in the bench at any time, `while True` is used here. The loop is broken only when the user gets that champion or quits the champ select stage. One possible result is, at the last second, someone swaps the target champion with a champion in the bench, then the user gets it, but doesn't have time to configure perks）
            #这里没有设置对可用英雄池中是否有目标英雄的判断，因为可用英雄池有一个BUG：一旦一个英雄出现在可用英雄池，即可通过接口立即选取该英雄，而不必等到客户端内的倒计时结束（Here we don't add a judgment on whether the target champion is in the available champion pool, for there's a BUG: Once a champion appears in the bench, it can be immediately picked, instead of letting players wait until the timer passes）
            current_response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-champ-select/v1/session/bench/swap/{championId}")).json()
            if current_response != previous_response:
                print(current_response)
                previous_response = current_response
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            if gameflow_phase == "ChampSelect":
                champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                action_found = False #前面说候选动作视为一定会被找到，但这里保险起见还是标记一下，万一英雄选择会话初始化的时候没有发现相关动作，同时也方便退出下面的嵌套for循环（Though we said before that the "bench" action must be found, for the sake of caution, a variable is defined here to mark it, in case the local action isn't found in the champ select session that has just been initialized, meantime making it convenient to exit the following nested for-loop）
                for stage in champ_select_session["actions"]:
                    for action in stage:
                        if selfKey == str(action["actorCellId"]) + " " + action["type"]:
                            action_found = True
                            if action["championId"] == championId:
                                ready = True
                            break
                    if action_found:
                        break
            else:
                print("您已退出英雄选择阶段！请重新选择英雄。\nYou've exited the champ select stage! Please pick the champion again.")
                break
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        if gameflow_phase == "ChampSelect":
            champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
            actions = [action for stage in champ_select_session["actions"] for action in stage]
            for action in actions:
                if selfKey == str(action["actorCellId"]) + " " + action["type"]:
                    if action["championId"] == championId:
                        print("自动选择成功！\nAutopick succeeded!")
                    else:
                        print("自动选择失败！\nAutopick failed!")
                    break

async def autoSelect(connection: Connection) -> None:
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json() #主要用于确定client-config接口的URI和周免英雄键（Mainly used to determine the URI of the client-config endpoint and the free-to-play champion key）
    operational: dict[str, Any] = await (await connection.request("GET", "/client-config/v2/namespace/lol.%s.operational/public" %(platformId.lower()))).json() #大区特定客户端配置（Platform-specific client configuration）
    current_summoner: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    f2p_gameModeName_hint_printed: bool = False
    #准备用于输出和检索的英雄数据（Prepare champion data for output and retrieval）
    LoLChampion: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %current_summoner["summonerId"])).json()
    LoLChampions: dict[int, dict[str, Any]] = {}
    for champion in LoLChampion:
        LoLChampions[champion["id"]] = champion
    LoLChampion_df, count = await sort_inventory_champions(connection, LoLChampions)
    LoLChampion_fields_to_print: list[str] = ["id", "name", "title", "alias"]
    LoLChampion_df_to_print: pandas.DataFrame = LoLChampion_df.loc[:, LoLChampion_fields_to_print]
    LoLChampion_df_query: pandas.DataFrame = LoLChampion_df_to_print.copy(deep = True)
    LoLChampion_df_query["id"] = LoLChampion_df["id"].astype(str) #方便检索（For convenience of retrieval）
    LoLChampion_df_query = LoLChampion_df_query.map(lambda x: x.lower() if isinstance(x, str) else x)
    print("本脚本用于帮助队友同时选择相同的英雄。请确保同队伍的成员输入的英雄序号相同。\nThis program is aimed at helping players of the same team to pick the same champion. Please ensure all teammates have submitted the same championId.")
    while True:
        print('请输入英雄序号：\nPlease input the championId:\n0\t全英雄信息（All champions）\n01\t可选英雄（Pickable champions）\n02\t可禁用英雄（Bannable champions）\n03\t英雄卡牌（Champion cards）\n04\t可选英雄池（替补席）【Available champion pool (bench)】\n05\t万众倾心（Crowd favorite champions）\n06\t免费使用（F2P champions）\n07\t不可用英雄（Disabled champions）')
        while True:
            champion_queryStr: str = input()
            if champion_queryStr == "":
                continue
            elif champion_queryStr in {"0", "01", "02", "03", "04", "05", "06", "07"}:
                if champion_queryStr == "0":
                    print(format_df(LoLChampion_df_to_print)[0])
                elif champion_queryStr == "04":
                    champ_select_session: dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                    if isinstance(champ_select_session, dict) and "errorCode" in champ_select_session or not champ_select_session["benchEnabled"]:
                        print("信息不可用。\nInformation not available.")
                    else:
                        bench_champion_ids: list[int] = list(map(lambda x: x["championId"], champ_select_session["benchChampions"]))
                        print(format_df(pandas.concat([LoLChampion_df_to_print.iloc[:1, :], LoLChampion_df_to_print[LoLChampion_df_to_print["id"].isin(bench_champion_ids)]]))[0])
                else:
                    if champion_queryStr == "01":
                        selectable_champion_ids: list[int] | dict[str, Any] = await (await connection.request("GET", "/lol-champ-select/v1/pickable-champion-ids")).json()
                    elif champion_queryStr == "02":
                        selectable_champion_ids = await (await connection.request("GET", "/lol-champ-select/v1/bannable-champion-ids")).json()
                    elif champion_queryStr == "03":
                        selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/subset-champion-list")).json()
                    elif champion_queryStr == "05":
                        selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/crowd-favorte-champion-list")).json()
                    elif champion_queryStr == "06":
                        # selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/f2p-rotation-for-current-queue")).json() #这个接口曾经可用，现在失效了（This endpoint was available in the past but no longer is now）
                        key_prefix: str = "lol.%s.operational." %(platformId.lower())
                        f2pRotations: dict[str, list[int]] = operational[key_prefix + "champions.freeToPlayChampionRotations"]
                        print("请选择一个模式：（直接按回车键以查看当前模式。）\nPlease select a game mode: (Press Enter directly to check F2P champions for this queue.)\n1\t召唤师峡谷（Summoner's Rift）\n2\t极地大乱斗（ARAM）\n3\t斗魂竞技场（Arena）\n4\t新玩家（New player）\n5\t经典模式（Classic）\n6\t自定义键（Custom key）")
                        while True:
                            f2p_mode: str = input()
                            if f2p_mode == "" or f2p_mode[0] in set(map(str, range(1, 6))):
                                break
                            elif f2p_mode[0] == "6":
                                print("请输入模式名称代号。\nPlease input a game mode name.")
                                if not f2p_gameModeName_hint_printed:
                                    print("示例（Examples）：\n1\t{0:<12}召唤师峡谷（Summoner's Rift）\n2\t{1:<12}极地大乱斗（ARAM）\n3\t{2:<12}斗魂竞技场（Arena）\n4\t{3:<12}新玩家（New player）\n5\t{4:<12}经典模式（Classic）".format("sr", "aram", "arena", "newplayer", "classic"))
                                    f2p_gameModeName_hint_printed = True
                                f2p_mode = input()
                                break
                            else:
                                print("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if f2p_mode == "":
                            lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json() #在英雄选择阶段，仍存在房间/小队（During the champ select stage, the lobby / party still exists）
                            if "errorCode" in lobby_information:
                                selectable_champion_ids = lobby_information
                            else:
                                queueId: int = lobby_information["gameConfig"]["queueId"]
                                queueConfigs: dict[int, dict[str, Any]] = {queue["queueId"]: queue for queue in operational[key_prefix + "queues.queueConfigs"]}
                                if queueId in queueConfigs:
                                    selectable_champion_ids = []
                                    f2pRotations_queue_strategy: str = queueConfigs[queueId]["f2pRotations"]
                                    f2pRotations_queue_strategy_list: list[str] = f2pRotations_queue_strategy.split(",")
                                    for gameModeName in f2pRotations_queue_strategy_list:
                                        if gameModeName in f2pRotations:
                                            selectable_champion_ids += f2pRotations[gameModeName]
                                    selectable_champion_ids = sorted(set(selectable_champion_ids))
                                else:
                                    selectable_champion_ids = {"errorCode": "NOT_FOUND", "httpStatus": 404, "message": "F2P champions not found."}
                        else:
                            if f2p_mode[0] == "1":
                                selectable_champion_ids = f2pRotations.get("sr", [])
                            elif f2p_mode[0] == "2":
                                selectable_champion_ids = f2pRotations.get("aram", [])
                            elif f2p_mode[0] == "3":
                                selectable_champion_ids = f2pRotations.get("arena", [])
                            elif f2p_mode[0] == "4":
                                selectable_champion_ids = f2pRotations.get("newplayer", [])
                            elif f2p_mode[0] == "5":
                                selectable_champion_ids = f2pRotations.get("classic", [])
                            else: #自定义游戏模式代号（Custom game mode name）
                                if f2p_mode in f2pRotations:
                                    selectable_champion_ids = f2pRotations[f2p_mode]
                                else:
                                    selectable_champion_ids = {"errorCode": "NOT_FOUND", "httpStatus": 404, "message": "Game mode not found."}
                    else:
                        selectable_champion_ids = await (await connection.request("GET", "/lol-lobby-team-builder/champ-select/v1/disabled-champion-ids")).json()
                    if isinstance(selectable_champion_ids, dict):
                        print("信息不可用。\nInformation not available.")
                    else:
                        print(format_df(pandas.concat([LoLChampion_df_to_print.iloc[:1, :], LoLChampion_df_to_print[LoLChampion_df_to_print["id"].isin(selectable_champion_ids)]]))[0], end = "\n\n")
                print('请输入英雄序号：\nPlease input the championId:\n0\t全英雄信息（All champions）\n01\t可选英雄（Pickable champions）\n02\t可禁用英雄（Bannable champions）\n03\t英雄卡牌（Champion cards）\n04\t可选英雄池（替补席）【Available champion pool (bench)】\n05\t万众倾心（Crowd favorite champions）\n06\t免费使用（F2P champions）\n07\t不可用英雄（Disabled champions）')
            elif champion_queryStr == "-1":
                championId: int = -1
                break
            elif champion_queryStr == "-3":
                championId = -3
                break
            else:
                query_positions = numpy.where(LoLChampion_df_query == champion_queryStr.lower()) #使用numpy.where检索的前提是数据框中每个单元格的值都不一样（The premise of query by `numpy.where` is that no two cells are the same）
                if len(query_positions[0]) == 0:
                    print("没有找到该英雄。请重新输入。\nChampion not found. Please try again.")
                else:
                    resultRow = query_positions[0]
                    result_champion_df: pandas.DataFrame = LoLChampion_df.loc[resultRow, LoLChampion_fields_to_print].reset_index(drop = True)
                    championId = LoLChampion_df["id"][resultRow[0]]
                    print("您选择了以下英雄：\nYou selected the following champion:")
                    print(format_df(result_champion_df)[0])
                    break
        if championId == -1:
            break
        repick: bool = False
        print("请选择行为类型。\nPlease select an action type.\n0\t撤销（Recall）\n1\t禁（Ban）\n2\t选（Pick）\n3\t投票（Vote）\n4\t候选（Bench）") #自动禁用的一个有用的地方是斗魂竞技场：通过抢先选中要禁的英雄，用户可以查看是否这名英雄会被其它人禁用。如果被别人抢先禁用了，在用户视角下可能就看不出来有没有被禁用了（A useful case of autoban is Arena: by selecting a champion to ban, the user can know whether this champion is banned by another player. If someone bans this champion before this champion is selected to be banned by the user, then in the user's vision, it can't be inferred accurately whether this champion has been banned）
        while True:
            ban: bool = False
            pick: bool = False
            vote: bool = False
            bench: bool = False
            s: str = input()
            if s == "":
                continue
            elif s[0] == "0":
                repick = True
                break
            elif s[0] == "1":
                ban = True
                break
            elif s[0] == "2":
                pick = True
                break
            elif s[0] == "3":
                vote = True
                break
            elif s[0] == "4":
                bench = True
                break
            else:
                print("您的输入有误！请重新输入。\nERROR input! Please try again.")
        if repick:
            continue
        if bench:
            lagged_pick: bool = False
            timer: float = 0
            print("请选择一个模式：\nPlease select a mode:\n0\t重新选择（Change the champion）\n1\t立即选择（Instant pick）\n2\t定时选择（Lagged pick）")
            while True:
                mode: str = input()
                if mode == "":
                    continue
                elif mode[0] == "0":
                    repick = True
                    break
                elif mode[0] == "1":
                    break
                elif mode[0] == "2":
                    lagged_pick = True
                    break
                else:
                    print("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if repick:
                continue
            if lagged_pick:
                print("请设置一个时间。程序将在英雄选择计时器来到该时刻时尝试选用该英雄。\nPlease set a time clock. The program will try swapping for this champion on the bench when the champ select timer reaches that moment.")
                while True:
                    try:
                        timer = float(input())
                    except ValueError:
                        print("请输入一个数字！\nPlease input a number!")
                    else:
                        if timer <= 0:
                            print("请输入一个正数！\nPlease input a positive number")
                        else:
                            break
        else:
            print("是否直接锁定选择？（输入任意键直接锁定，否则不锁定。输入“0”以重新选择英雄。）\nDo you want to lock in? (Submit any non-empty string to lock in, or null to refuse locking in.)")
            complete_str: str = input()
            if complete_str != "" and complete_str[0] == "0":
                continue
            else:
                complete = bool(complete_str)
        #先确保用户进入英雄选择阶段（First, make sure the user is during champ select stage）
        if ban:
            print("等待进入英雄选择阶段的禁英雄阶段……\nWaiting for the banning stage of the champ select stage ...")
        elif pick:
            print("等待进入英雄选择阶段的选英雄阶段……\nWaiting for the picking stage of the champ select stage ...")
        elif vote:
            print("等待进入英雄选择阶段的投票阶段……\nWaiting for the voting stage of the champ select stage ...")
        elif bench:
            print("等待进入英雄选择阶段的赛前配置阶段……\nWaiting for the finalization stage of the champ select stage ...")
        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
        spectateWarningPrinted: bool = False
        benchDisabledWarningPrinted: bool = False
        while True:
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            if gameflow_phase == "ChampSelect":
                champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                if not "errorCode" in champ_select_session: #由于服务器延迟，当用户退出英雄选择阶段时，游戏状态可能在短时间内仍然标记为英雄选择（Due to server lag, when the user quits the champ select stage, the gameflow phase might be "ChampSelect" in a short time period）
                    if champ_select_session["isSpectating"]:
                        if not spectateWarningPrinted:
                            print("您正在观战。请自行开启一把对局。\nYou're spectating. Please start a game by yourself.")
                            spectateWarningPrinted = True
                    elif bench and not champ_select_session["benchEnabled"]:
                        if not benchDisabledWarningPrinted:
                            print("当前模式不支持可用英雄池。\nBench isn't enabled in this mode.")
                            benchDisabledWarningPrinted = True
                    else:
                        break
        if bench:
            await autoBench(connection, championId, lagged_pick, timer)
        else:
            actionType = "ban" if ban else "pick" if pick else "vote"
            await autoPick(connection, championId = championId, actionType = actionType, complete = complete)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await get_summoner_data(connection)
    await autoSelect(connection)

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
