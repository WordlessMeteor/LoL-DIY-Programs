from lcu_driver import Connector
from urllib.parse import quote, unquote
import ctypes, copy, os, pickle, time

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/07/26
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

#终端权限检测（Terminal permission detection)
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    print("请以管理员权限运行此程序。\nPlease run this program as administrator.")
    os.system("pause")
    exit()

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
#  抢主播车位（Steal a streamer's lobby seat）
#-----------------------------------------------------------------------------
async def seatVie(connection):
    print("请确保以下条件：\nPlease check the following requirements:\n1. 您想要一起玩的主播是您的好友。\n   The streamer / uploader you want to player with is your friend.\n2. 该主播正在创建队列房间，而不是自定义房间。\n   This streamer / uploader is creating a queue lobby, instead of a custom lobby.\n3. 该主播创建的小队是公开给好友的，而不是仅通过邀请才能进入。\n   The party is open to friends, instead of invite-only.\n\n声明：请自觉使用，切勿恶意干扰主播。为保证程序正常运行，如无特殊需求，请勿随意退出程序。\nDeclaration: Please mind yourself and avoid from disturbing the streamer miliciously. To guarantee the expected program execution, please don't exit the program at will without specific demands.\n")
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    partyId_previous = "" #鼠标悬停弹窗存在延迟，所以当一位好友退出房间并马上创建房间时，鼠标悬停弹窗中的信息可能是老房间的信息。需要注意，切换模式不会改变小队编号。这应该很好理解，因为你的好友切换游戏模式时，你不会被自动踢出房间（There's a delay in the display of hovercard, so when a friend exits an old lobby and immediately creates a new lobby, the hovercard information may belong to the old lobby. Note that changing mode doesn't change the partyId. This should be easy to understand: if your friend changes the mode, you won't be automatically kicked from the lobby）
    response_previous = {}
    print('请输入您想要加入的小队的拥有者的玩家名称，退出请输入0。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to exit. If you want to cancel the program later, please press Ctrl-C.')
    while True:
        summoner_name = input()
        if summoner_name == "0":
            break
        elif summoner_name == "":
            print("请输入非空字符串！\nPlease input a string instead of null!")
            continue
        elif summoner_name == "partyId":
            print('请输入小队编号，返回上一层请输入0。\nPlease input the partyId. Submit "0" to return to the last step.')
            while True:
                partyId = input()
                if partyId == "0":
                    print('请输入您想要加入的小队的拥有者的玩家名称，退出请输入0。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to exit. If you want to cancel the program later, please press Ctrl-C.')
                    break
                response = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                if response == None:
                    print("您已成功加入小队！\nYou've successfully joined the party!")
                else:
                    print(response)
        else:
            if summoner_name == "current-summoner":
                search_by_puuid = False
                info = current_info.copy()
            elif summoner_name.count("-") == 4 and len(summoner_name.replace(" ", "")) > 22: #拳头规定的玩家昵称不超过16个字符，昵称编号不超过5个字符（Riot game name can't exceed 16 characters. The tagline can't exceed 5 characters）
                search_by_puuid = True
                info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + quote(summoner_name))).json()
            else:
                search_by_puuid = False
                info = await (await connection.request("GET", "/lol-summoner/v1/summoners?name=" + quote(summoner_name))).json()
            if "errorCode" in info and info["httpStatus"] == 400:
                if search_by_puuid:
                    print("您输入的玩家通用唯一识别码格式有误！请重新输入！\nPUUID wasn't in UUID format! Please try again!")
                else:
                    print("您输入的召唤师名称格式有误！请重新输入！\nERROR format of summoner name! Please try again!")
            elif "errorCode" in info and info["httpStatus"] == 404:
                if search_by_puuid:
                    print("未找到玩家通用唯一识别码为" + summoner_name + "的玩家；请核对识别码并稍后再试。\nA player with puuid " + summoner_name + " was not found; verify the puuid and try again.")
                else:
                    print("未找到" + summoner_name + "；请核对下名字并稍后再试。\n" + summoner_name + " was not found; verify the name and try again.")
            elif "errorCode" in info and info["httpStatus"] == 422:
                print('召唤师名称已变更为拳头ID。请以“{玩家昵称}#{昵称编号}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"]))
            elif "accountId" in info:
                current_puuid = info["puuid"]
                current_summonerId = info["summonerId"]
                current_gameName = info["gameName"]
                current_tagLine = info["tagLine"]
                
                #联网校验（Online verification）
                switch_summoner = False
                LoLHistory_get = True
                LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches" %(current_info["puuid"]))).json() #这里之所以不把对局索引上界设置为500，是为了让用户有机可乘：用户可以通过不断开训练模式并且秒退，使最近20局全是训练模式，从而丢失和主播的对局信息（Here the upper limit of matchIDs could haven been set as 500, but a loophole is given: the user can keep starting a practice tool game and quitting once he/she enters the game, so that the recent 20 matches will all be custom games, and hence the match with the streamer will be lost）
                error_occurred = False
                count = 0
                if "errorCode" in LoLHistory:
                    if "500 Internal Server Error" in LoLHistory["message"]:
                        if not error_occurred:
                            print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                            occurred = True
                        while "errorCode" in LoLHistory and "500 Internal Server Error" in LoLHistory["message"] and count <= 3:
                            count += 1
                            print("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                            LoLHistory = await (connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches" %(current_info["puuid"]))).json()
                    elif "body was empty" in LoLHistory["message"]:
                        LoLHistory_get = False
                        print("您从5月1日起就没有进行过任何英雄联盟对局。请先进行一场对局再运行本脚本。\nThis summoner hasn't played any LoL game yet since May 1st. Please run this program after you've played a game.")
                if not LoLHistory_get:
                    print("请在对局记录能够正常获取的情况下运行本脚本。程序即将退出。\nPlease ensure the match history can be fetched successfully. The program will exit now!")
                    time.sleep(3)
                    return 1
                LoLMatchIDs = list(map(lambda x: x["gameId"], LoLHistory["games"]["games"])) #按照LCU API的记录规则，对局序号一定是根据日期降序排列的（According to the recording principle of LCU API, the matchIDs must be in the descending order of gameCreation）
                for matchID in LoLMatchIDs:
                    LoLGame_info = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchID}")).json()
                    if "errorCode" in LoLGame_info:
                        count = 0
                        if LoLGame_info["httpStatus"] == 404:
                            print("未找到序号为" + matchID + "的回放文件！将忽略该序号。\nMatch file with matchID " + matchID + " not found! The program will ignore this matchID.")
                        if "500 Internal Server Error" in LoLGame_info["message"]:
                            if not error_occurred:
                                print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                error_occurred = True
                            while "errorCode" in LoLGame_info and "500 Internal Server Error" in LoLGame_info["message"] and count <= 3:
                                count += 1
                                print("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                                LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                        elif "Connection timed out after " in LoLGame_info["message"]:
                            fetched_info = False
                            print("对局信息获取超时！请检查网速状况！\nGame information fetching operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                        elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"]:
                            if not error_occurred:
                                print("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                                error_occurred = True
                            while "errorCode" in LoLGame_info and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"] and count <= 3:
                                count += 1
                                print("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                                LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                        if count > 3:
                            fetched_info = False
                            print("对局%d信息获取失败！程序即将退出。\nMatch %d information capture failure! The program will exit now." %(matchID, matchID))
                            time.sleep(3)
                            return 1
                    participant_puuids = list(map(lambda x: x["player"]["puuid"], LoLGame_info["participantIdentities"]))
                    if current_puuid in participant_puuids:
                        if time.time() - LoLGame_info["gameCreation"] / 1000 < 7200:
                            print("您近期已经和该玩家一起玩过。请稍后重试！\nYou've played with this player recently. Please try later!")
                            switch_summoner = True
                        break
                if switch_summoner:
                    continue
                
                hovercard = await (await connection.request("GET", f"/lol-hovercard/v1/friend-info/{current_puuid}")).json()
                #控制只输出一遍的提示（Control the hint to be displayed only once）
                empty_party_hint_printed = False
                lobby_remake_hint_printed = False
                received_invitation_hint_printed = False
                if hovercard["availability"] == "":
                    print(f"玩家{current_gameName}#{current_tagLine}不是您的好友。请添加该玩家为好友后重试。\nPlayer {current_gameName}#{current_tagLine} isn't your friend right now. Please add him/her as a friend and retry.")
                elif hovercard["lol"] == {}: #对应的是离线和Riot手机端游戏状态（Corresponding to the offline and Riot Mobile status）
                    print(f"玩家{current_gameName}#{current_tagLine}目前处于离线状态。请重新输入。\nPlayer {current_gameName}#{current_tagLine} is offline right now. Please try again.")
                # elif hovercard["lol"]["gameStatus"] == "inQueue":
                #     print(f"玩家{current_gameName}#{current_tagLine}目前在队列中。请等待其返回房间后重试。\nPlayer {current_gameName}#{current_tagLine} is currently in queue. Please try again after the leader returns to the lobby.")
                # elif hovercard["lol"]["gameStatus"] == "championSelect":
                #     print(f"玩家{current_gameName}#{current_tagLine}目前处于英雄选择阶段。请等待其结束游戏或返回房间后重试。\nPlayer {current_gameName}#{current_tagLine} is during champion selection. Please try again after the game ends or the leader returns to the lobby.")
                elif hovercard["lol"]["gameStatus"] == "inGame":
                    print(f"玩家{current_gameName}#{current_tagLine}已在游戏中。请等待其结束游戏后重试。\nPlayer {current_gameName}#{current_tagLine} is already in a game. Please try again after the game ends.")
                else:
                    print("您可以通过加入公开小队或者接受小队拥有者邀请来加入一个小队。请选择加入小队的方式：\nYou may join a party by joining an open party or accepting a lobby invitation. Please choose a strategy of joining this party:\n1\t同时检查小队公开情况和邀请（Check both lobby publicity and lobby invitations）\n2\t只检查小队公开情况（Check only lobby publicity）\n3\t只检查小队邀请（Check only lobby invitations）\n4\t既不检查小队公开情况，也不检查小队邀请（Check neither lobby publicity nor lobby invitations）")
                    join_open_party = accept_invid = False
                    while True:
                        join_strategy = input()
                        if join_strategy == "":
                            continue
                        elif join_strategy[0] == "1":
                            join_open_party = accept_invid = True
                            break
                        elif join_strategy[0] == "2":
                            join_open_party, accept_invid = True, False
                            break
                        elif join_strategy[0] == "3":
                            join_open_party, accept_invid = False, True
                            break
                        elif join_strategy[0] == "0" or join_strategy[0] == "4":
                            join_open_party = accept_invid = False
                            break
                        else:
                            print("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    
                    print("正在尝试加入该玩家的小队……\nTrying to join this player's party ...")
                    while True:
                        if join_open_party:
                            #尝试加入公开小队（Try to join an open party）
                            hovercard = await (await connection.request("GET", f"/lol-hovercard/v1/friend-info/{current_puuid}")).json()
                            if not "pty" in hovercard["lol"] or hovercard["lol"]["pty"] == "":
                                if hovercard["lol"]["gameStatus"] == "inGame":
                                    print(f"玩家{current_gameName}#{current_tagLine}已在游戏中。请等待其结束游戏后重试。\nPlayer {current_gameName}#{current_tagLine} is already in a game. Please try again after the game ends.")
                                    break
                                elif not empty_party_hint_printed:
                                    print(f"玩家{current_gameName}#{current_tagLine}尚未处于小队中。或者该玩家处于私密小队中。\nPlayer {current_gameName}#{current_tagLine} isn't in a party. Or this player is in a closed party.")
                                    empty_party_hint_printed, lobby_remake_hint_printed = True, False
                            else:
                                partyId = eval(hovercard["lol"]["pty"])["partyId"]
                                if partyId == partyId_previous:
                                    if not lobby_remake_hint_printed:
                                        print(f"您已经加入好友{current_gameName}#{current_tagLine}的小队！如果该好友重新创建了队列房间，请等待程序回应。\nYou've joined the party of the friend {current_gameName}#{current_tagLine}! If this friend has created another queue lobby, please wait for the program to respond.\n小队编号（PartyId）： {partyId}\n")
                                        lobby_remake_hint_printed, empty_party_hint_printed = True, False
                                else:
                                    response = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                                    if response == None:
                                        lobbyInfo = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                        member_puuids = list(map(lambda x: x["puuid"], lobbyInfo["members"]))
                                        if current_puuid in member_puuids: #有可能先前在某个主播的小队里，但是后来这个主播退出小队并迅速重新创了个房间，而这个主播的鼠标悬停卡片尚未更新（Chances are that the user might be in the party of a streamer previously, but then the streamer exited the lobby and immediately created a new lobby, while the hovercard hadn't updated）
                                            print(f"您成功加入好友{current_gameName}#{current_tagLine}的队列房间！程序即将返回上层。\nYou've successfully joined the queue lobby of the friend {current_gameName}#{current_tagLine}! The program will return to the last step.\n小队编号（PartyId）： {partyId}\n")
                                            partyId_previous = lobbyInfo["partyId"]
                                            #time.sleep(3)
                                            print('请输入您想要加入的小队的拥有者的玩家名称，退出请输入0。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to exit. If you want to cancel the program later, please press Ctrl-C.')
                                            break
                                    else:
                                        #小队私密或被踢出小队的提示（The prompt of a closed or kicked party）：{'errorCode': 'RPC_ERROR', 'httpStatus': 400, 'implementationDetails': {}, 'message': 'INVALID_ROLE_TRANSITION'}
                                        #小队已满的提示（The prompt of a full party）：{'errorCode': 'RPC_ERROR', 'httpStatus': 400, 'implementationDetails': {}, 'message': 'PARTY_SIZE_LIMIT'}
                                        #小队排队中的提示（The prompt of a queuing party）：{'errorCode': 'RPC_ERROR', 'httpStatus': 400, 'implementationDetails': {}, 'message': 'INVALID_WHILE_PARTY_IN_ACTION'}
                                        if response != response_previous:
                                            print(response)
                                            response_previous = copy.deepcopy(response)
                        if accept_invid:
                            #尝试接受组队邀请（Try accepting a lobby invitation）
                            receivedInvitations = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
                            received_invitation = False
                            for invid in receivedInvitations:
                                if invid["fromSummonerId"] == current_summonerId:
                                    received_invitation = True
                                    if not received_invitation_hint_printed:
                                        print(f"检测到来自玩家{current_gameName}#{current_tagLine}的组队邀请。尝试接受该邀请……\nThe program detected an invitation from player {current_gameName}#{current_tagLine}. Trying to accept this invitation ...")
                                        received_invitation_hint_printed = True
                                    invitationId = invid["invitationId"]
                                    response = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/accept")).json()
                                    if response == None:
                                        lobbyInfo = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                        member_puuids = list(map(lambda x: x["puuid"], lobbyInfo["members"]))
                                        if current_puuid in member_puuids:
                                            print(f"您成功加入好友{current_gameName}#{current_tagLine}的队列房间！程序即将返回上层。\nYou've successfully joined the queue lobby of the friend {current_gameName}#{current_tagLine}! The program will return to the last step.\n小队编号（PartyId）： %s\n" %(lobbyInfo["partyId"]))
                                            partyId_previous = lobbyInfo["partyId"]
                                            #time.sleep(3)
                                            print('请输入您想要加入的小队的拥有者的玩家名称，退出请输入0。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to exit. If you want to cancel the program later, please press Ctrl-C.')
                                            break
                                    else:
                                        if response != response_previous:
                                            print(response)
                                            response_previous = copy.deepcopy(response)
                            if not received_invitation:
                                received_invitation_hint_printed = False
    
#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await seatVie(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
def check_last_run_time(fp): #本地校验（Local / Offline verification）
    if os.path.exists(fp):
        with open(fp, "rb") as file:
            last_run_time = pickle.load(file)
        current_time = time.time()
        time_diff = current_time - last_run_time
        if time_diff < 7200:
            print("您的运行次数过于频繁！请稍后重试。程序即将退出。\nYour requests are too frequent! Please try later. The program will exit now.")
            return False
    return True

def update_last_run_time(fp):
    current_time = time.time()
    with open(fp, "wb") as file:
        pickle.dump(current_time, file)

verifyFile = "C:/Windows/Temp/seatVie_lastrun.pkl"
if check_last_run_time(verifyFile):
    connector.start()
    update_last_run_time(verifyFile)
else:
    time.sleep(3)
