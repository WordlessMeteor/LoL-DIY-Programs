from lcu_driver import Connector
from lcu_driver.connection import Connection
from urllib.parse import quote
import ctypes, keyboard, pickle, time
from typing import Any, Optional
from src.utils.summoner import get_summoner_data
from src.core.dataframes.matchHistory import get_LoLHistory, get_LoLGame_info

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/02/09
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

#终端权限检测（Terminal permission detection)
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    print("请以管理员权限运行此程序。\nPlease run this program as administrator.")
    time.sleep(3)
    exit()

connector: Connector = Connector()

#-----------------------------------------------------------------------------
#  抢主播车位（Steal a streamer's lobby seat）
#-----------------------------------------------------------------------------
async def detect_played(connection: Connection, puuid: str) -> int: #检测某个玩家是否近期一起玩过（Detect whether a player has been played with recently）
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    LoLHistory_get, LoLHistory = await get_LoLHistory(connection, current_info["puuid"])
    if not LoLHistory_get:
        print("请在对局记录能够正常获取的情况下运行本脚本。程序即将退出。\nPlease ensure the match history can be fetched successfully. The program will exit now!")
        time.sleep(3)
        return 2
    LoLMatchIDs: list[int] = list(map(lambda x: x["gameId"], LoLHistory["games"]["games"])) #按照LCU API的记录规则，对局序号一定是根据日期降序排列的（According to the recording principle of LCU API, the matchIDs must be in the descending order of gameCreation）
    for matchId in LoLMatchIDs:
        status, LoLGame_info = await get_LoLGame_info(connection, matchId)
        if status != 200:
            print("对局%d信息获取失败！程序即将退出。\nMatch %d information capture failure! The program will exit now." %(matchId, matchId))
            time.sleep(3)
            return 2
        participant_puuids: list[str] = list(map(lambda x: x["player"]["puuid"], LoLGame_info["participantIdentities"]))
        if puuid in participant_puuids:
            if time.time() - LoLGame_info["gameCreation"] / 1000 < 7200:
                print("您近期已经和该玩家一起玩过。请稍后重试！\nYou've played with this player recently. Please try later!")
                return 1 #返回值1表示近期一起玩过（1 returned means this player has been played with recently）
            break
    return 0 #返回值0表示没有玩过（0 returned means this player hasn't been played with recently）

async def join_party(connection: Connection, partyId: str, data: Optional[dict[str, Any]] = None) -> tuple[Optional[dict[str, Any]], str]: #复制于游戏状态管理脚本（Copied from Customized Program 21）
    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join", data = data)).json()
    if isinstance(response, dict) and "errorCode" in response:
        if response["httpStatus"] == 400:
            if response["message"] == "PARTY_SIZE_LIMIT":
                message: str = "你试图加入的小队已经满员。\nThe open party you attempted to join is full."
            elif response["message"] == "PARTY_NOT_FOUND":
                message = "没有激活的游戏。\nActive game was not found."
            elif response["message"] == "INVALID_ROLE_TRANSITION":
                message = "你已被移出小队。你必须收到邀请才能重新加入。\nYou have been removed from the party. You must receive an invite to rejoin."
            elif response["message"] == "INVALID_WHILE_PARTY_IN_ACTION":
                message = "你无法加入该小队，因为该小队正在队列中。\nYou were not able to join the party because the party is now in queue."
            elif response["message"] == "INVALID_PERMISSIONS":
                message = "加入游戏时发生错误。请检查密码。\nThere was an error in joining this game. Please check the lobby password."
            else:
                message = "你无法加入该小队。\nYou were not able to join the party."
        else:
            message = "你无法加入该小队。\nYou were not able to join the party."
    else:
        message = ""
    return (response, message)

async def seatVie(connection: Connection) -> None: #从好友列表中选择一个小队加入（Find a party from the friend list）
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    print("请确保以下条件：\nPlease check the following requirements:\n1. 您想要一起玩的主播是您的好友。\n   The streamer / uploader you want to player with is your friend.\n2. 该主播正在创建队列房间，而不是自定义房间。\n   This streamer / uploader is creating a queue lobby, instead of a custom lobby.\n3. 该主播创建的小队是公开给好友的，而不是仅通过邀请才能进入。\n   The party is open to friends, instead of invite-only.\n\n声明：请自觉使用，切勿恶意干扰主播。为保证程序正常运行，如无特殊需求，请勿随意退出程序。\nDeclaration: Please mind yourself and avoid from disturbing the streamer miliciously. To guarantee the expected program execution, please don't exit the program at will without specific demands.\n")
    partyId_previous: str = "" #鼠标悬停弹窗存在延迟，所以当一位好友退出房间并马上创建房间时，鼠标悬停弹窗中的信息可能是老房间的信息。需要注意，切换模式不会改变小队编号。这应该很好理解，因为你的好友切换游戏模式时，你不会被自动踢出房间（There's a delay in the display of hovercard, so when a friend exits an old lobby and immediately creates a new lobby, the hovercard information may belong to the old lobby. Note that changing mode doesn't change the partyId. This should be easy to understand: if your friend changes the mode, you won't be automatically kicked from the lobby）
    response_previous: Optional[dict[str, Any]] = {}
    print('请输入您想要加入的小队的拥有者的玩家名称，返回上一层请输入“0”。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to return to the last step. If you want to cancel the program later, please press Ctrl-C.')
    while True:
        summoner_name: str = input()
        if summoner_name == "0":
            break
        elif summoner_name == "":
            print("请输入非空字符串！\nPlease input a string instead of null!")
            continue
        else:
            if summoner_name == "current-summoner":
                search_by_puuid: bool = False
                info: dict[str, Any] = current_info
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
                    print(f"未找到玩家通用唯一识别码为{summoner_name}的玩家；请核对识别码并稍后再试。\nA player with puuid {summoner_name} was not found; verify the puuid and try again.")
                else:
                    print(f"未找到{summoner_name}；请核对下名字并稍后再试。\n{summoner_name} was not found; verify the name and try again.")
            elif "errorCode" in info and info["httpStatus"] == 422:
                print('召唤师名称已变更为拳头ID。请以“{玩家昵称}#{昵称编号}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"]))
            elif "accountId" in info:
                current_puuid: str = info["puuid"]
                current_summonerId: int = info["summonerId"]
                current_gameName: str = info["gameName"]
                current_tagLine: str = info["tagLine"]
                
                #联网校验（Online verification）
                status: int = await detect_played(connection, current_puuid)
                if status == 0:
                    switch_summoner: bool = False
                elif status == 1:
                    switch_summoner = True
                else:
                    print("联网校验的过程出现了一个异常。\nAn error occurred during online verification.")
                    break
                if switch_summoner:
                    continue
                
                hovercard: dict[str, Any] = await (await connection.request("GET", f"/lol-hovercard/v1/friend-info/{current_puuid}")).json()
                #控制只输出一遍的提示（Control the hint to be displayed only once）
                empty_party_hint_printed: bool = False
                lobby_remake_hint_printed: bool = False
                received_invitation_hint_printed: bool = False
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
                    join_open_party: bool = False
                    accept_invid: bool = False
                    while True:
                        join_strategy: str = input()
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
                    
                    print('''正在尝试加入该玩家的小队……按住“Esc”键以退出循环返回上一层。\nTrying to join this player's party ... Press and keep holding "Esc" to exit the loop and return to the last step.''')
                    while True:
                        if keyboard.is_pressed("esc"):
                            print("您已中断程序运行。程序将返回上一层。\nYou've interrupted the program loop. The program will return to the last step.")
                            print('请输入您想要加入的小队的拥有者的玩家名称，返回上一层请输入“0”。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to return to the last step. If you want to cancel the program later, please press Ctrl-C.')
                            break
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
                                partyId: str = eval(hovercard["lol"]["pty"])["partyId"]
                                if partyId == partyId_previous:
                                    if not lobby_remake_hint_printed:
                                        print(f"您已经加入好友{current_gameName}#{current_tagLine}的小队！如果该好友重新创建了队列房间，请等待程序回应。\nYou've joined the party of the friend {current_gameName}#{current_tagLine}! If this friend has created another queue lobby, please wait for the program to respond.\n小队编号（PartyId）： {partyId}\n")
                                        lobby_remake_hint_printed, empty_party_hint_printed = True, False
                                else:
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                                    if response == None:
                                        lobbyInfo: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                        member_puuids: list[str] = list(map(lambda x: x["puuid"], lobbyInfo["members"]))
                                        if current_puuid in member_puuids: #有可能先前在某个主播的小队里，但是后来这个主播退出小队并迅速重新创了个房间，而这个主播的鼠标悬停卡片尚未更新（Chances are that the user might be in the party of a streamer previously, but then the streamer exited the lobby and immediately created a new lobby, while the hovercard hadn't updated）
                                            print(f"您成功加入好友{current_gameName}#{current_tagLine}的队列房间！程序即将返回上层。\nYou've successfully joined the queue lobby of the friend {current_gameName}#{current_tagLine}! The program will return to the last step.\n小队编号（PartyId）： {partyId}\n")
                                            partyId_previous = lobbyInfo["partyId"]
                                            #time.sleep(3)
                                            print('请输入您想要加入的小队的拥有者的玩家名称，返回上一层请输入“0”。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to return to the last step. If you want to cancel the program later, please press Ctrl-C.')
                                            break
                                    else:
                                        #小队私密或被踢出小队的提示（The prompt of a closed or kicked party）：{'errorCode': 'RPC_ERROR', 'httpStatus': 400, 'implementationDetails': {}, 'message': 'INVALID_ROLE_TRANSITION'}
                                        #小队已满的提示（The prompt of a full party）：{'errorCode': 'RPC_ERROR', 'httpStatus': 400, 'implementationDetails': {}, 'message': 'PARTY_SIZE_LIMIT'}
                                        #小队排队中的提示（The prompt of a queuing party）：{'errorCode': 'RPC_ERROR', 'httpStatus': 400, 'implementationDetails': {}, 'message': 'INVALID_WHILE_PARTY_IN_ACTION'}
                                        if response != response_previous:
                                            print(response)
                                            response_previous = response
                        if accept_invid:
                            #尝试接受组队邀请（Try accepting a lobby invitation）
                            receivedInvitations: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
                            received_invitation: bool = False
                            for invid in receivedInvitations:
                                if invid["fromSummonerId"] == current_summonerId:
                                    received_invitation = True
                                    if not received_invitation_hint_printed:
                                        print(f"检测到来自玩家{current_gameName}#{current_tagLine}的组队邀请。尝试接受该邀请……\nThe program detected an invitation from player {current_gameName}#{current_tagLine}. Trying to accept this invitation ...")
                                        received_invitation_hint_printed = True
                                    invitationId = invid["invitationId"]
                                    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/accept")).json()
                                    if response == None:
                                        lobbyInfo = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                        member_puuids = list(map(lambda x: x["puuid"], lobbyInfo["members"]))
                                        if current_puuid in member_puuids:
                                            print(f"您成功加入好友{current_gameName}#{current_tagLine}的队列房间！程序即将返回上层。\nYou've successfully joined the queue lobby of the friend {current_gameName}#{current_tagLine}! The program will return to the last step.\n小队编号（PartyId）： %s\n" %(lobbyInfo["partyId"]))
                                            partyId_previous = lobbyInfo["partyId"]
                                            #time.sleep(3)
                                            print('请输入您想要加入的小队的拥有者的玩家名称，返回上一层请输入“0”。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease enter the player name of the party leader that you want to play with. Submit "0" to return to the last step. If you want to cancel the program later, please press Ctrl-C.')
                                            break
                                    else:
                                        if response != response_previous:
                                            print(response)
                                            response_previous = response
                            if not received_invitation:
                                received_invitation_hint_printed = False

async def lobbyVie(connection: Connection) -> None:
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    response_previous: Optional[dict[str, Any]] = {}
    print('请选择您要加入的房间的房主召唤师名，返回上一层请输入“0”。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease input the summoner name of the owner of the lobby you want to join. Submit "0" to return to the last step. If you want to cancel the program later, please press Ctrl-C.')
    while True:
        summoner_name: str = input()
        if summoner_name == "0":
            break
        elif summoner_name == "":
            print("请输入非空字符串！\nPlease input a string instead of null!")
            continue
        else:
            if summoner_name == "current-summoner":
                search_by_puuid = False
                info: dict[str, Any] = current_info
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
                    print(f"未找到玩家通用唯一识别码为{summoner_name}的玩家；请核对识别码并稍后再试。\nA player with puuid {summoner_name} was not found; verify the puuid and try again.")
                else:
                    print(f"未找到{summoner_name}；请核对下名字并稍后再试。\n{summoner_name} was not found; verify the name and try again.")
            elif "errorCode" in info and info["httpStatus"] == 422:
                print('召唤师名称已变更为拳头ID。请以“{玩家昵称}#{昵称编号}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"]))
            elif "accountId" in info:
                current_puuid: str = info["puuid"]
                current_summonerId: int = info["summonerId"]
                current_gameName: str = info["gameName"]
                current_tagLine: str = info["tagLine"]
                
                #联网校验（Online verification）
                status: int = await detect_played(connection, current_puuid)
                if status == 0:
                    switch_summoner: bool = False
                elif status == 1:
                    switch_summoner = True
                else:
                    print("联网校验的过程出现了一个异常。\nAn error occurred during online verification.")
                    break
                if switch_summoner:
                    continue
                
                #输入密码（Input the password）
                while True:
                    print("请输入密码。如果没有密码，请直接按回车键。\nPlease input the password. If the lobby doesn't have a password, please press Enter directly.")
                    password: str = input()
                    if password == "":
                        print("您未输入任何密码。按回车键以确认密码，或者输入任意非空字符串以更改密码。\nYou haven't input any password. Press Enter to confirm the password, or input any non-empty string to change the password.")
                    else:
                        print(f"您输入的密码是：\nThe password you just submitted is:\n{password}\n按回车键以确认密码，或者输入任意非空字符串以更改密码。\nPress Enter to confirm the password, or input any non-empty string to change the password.")
                    confirm: bool = not bool(input())
                    if confirm:
                        break
                
                #发送请求（Send the request）
                print('''正在尝试加入该玩家的房间……按住“Esc”键以退出循环返回上一层。\nTrying to join this player's lobby ... Press and keep holding "Esc" to exit the loop and return to the last step.''')
                ownerDisplayName: str = f"{current_gameName} #{current_tagLine}"
                lobby_not_created_hint_printed: bool = False
                while True:
                    if keyboard.is_pressed("esc"):
                        print("您已中断程序运行。程序将返回上一层。\nYou've interrupted the program loop. The program will return to the last step.")
                        print('请选择您要加入的房间的房主召唤师名，返回上一层请输入“0”。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease input the summoner name of the owner of the lobby you want to join. Submit "0" to return to the last step. If you want to cancel the program later, please press Ctrl-C.')
                        break
                    response = await (await connection.request("POST", "/lol-lobby/v1/custom-games/refresh")).json() #每次循环时刷新自定义房间列表一次（Refresh the custom lobby list once per loop）
                    custom_games: list[dict[str, Any]] = await (await connection.request("GET", "/lol-lobby/v1/custom-games")).json()
                    custom_lobbies: dict[str, dict[str, Any]] = {lobby["ownerDisplayName"]: lobby for lobby in custom_games}
                    if ownerDisplayName in custom_lobbies:
                        lobby_not_created_hint_printed = False
                        partyId: str = custom_lobbies[ownerDisplayName]["partyId"]
                        body: dict[str, Any] = {"lobbyPassword": password, "team": None}
                        response = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join", data = body)).json()
                        if response_previous != response:
                            response_previous = response
                        if isinstance(response, dict) and "errorCode" in response:
                            print(response)
                        else:
                            lobbyInfo = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                            member_puuids = list(map(lambda x: x["puuid"], lobbyInfo["members"]))
                            if current_puuid in member_puuids:
                                print(f"您成功加入好友{current_gameName}#{current_tagLine}的自定义房间！程序即将返回上层。\nYou've successfully joined the custom lobby of the player {current_gameName}#{current_tagLine}! The program will return to the last step.\n小队编号（PartyId）： {partyId}\n")
                                #time.sleep(3)
                                print('请选择您要加入的房间的房主召唤师名，返回上一层请输入“0”。如果要中断程序运行，请按Ctrl-C结束程序。\nPlease input the summoner name of the owner of the lobby you want to join. Submit "0" to return to the last step. If you want to cancel the program later, please press Ctrl-C.')
                                break
                    else:
                        if not lobby_not_created_hint_printed:
                            print("等待该玩家创建自定义房间……\nWaiting for this player to create a custom lobby ...")
                            lobby_not_created_hint_printed = True

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await get_summoner_data(connection)
    print("请选择运行模式：\nPlease select a mode:\n0\t退出程序（Exit the program）\n1\t从好友列表加入（Join from friend list）\n2\t从自定义房间列表加入（Join from custom lobby list）")
    while True:
        mode: str = input()
        if mode == "":
            continue
        elif mode == "-1":
            print('请输入小队编号，返回上一层请输入0。\nPlease input the partyId. Submit "0" to return to the last step.')
            while True:
                partyId: str = input()
                if partyId == "0":
                    break
                else:
                    response = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                    if response == None:
                        print("您已成功加入小队！\nYou've successfully joined the party!")
                    else:
                        print(response)
        elif mode[0] == "0":
            break
        elif mode[0] == "1":
            await seatVie(connection)
        elif mode[0] == "2":
            await lobbyVie(connection)
        print("请选择运行模式：\nPlease select a mode:\n0\t退出程序（Exit the program）\n1\t从好友列表加入（Join from friend list）\n2\t从自定义房间列表加入（Join from custom lobby list）")

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
def check_last_run_time(fp: str) -> bool: #本地校验（Local / Offline verification）
    if os.path.exists(fp):
        with open(fp, "rb") as file:
            last_run_time: float = pickle.load(file)
        current_time: float = time.time()
        time_diff: float = current_time - last_run_time
        if time_diff < 7200:
            print("您的运行次数过于频繁！请稍后重试。程序即将退出。\nYour requests are too frequent! Please try later. The program will exit now.")
            return False
    return True

def update_last_run_time(fp: str) -> None:
    current_time: float = time.time()
    with open(fp, "wb") as file:
        pickle.dump(current_time, file)

verifyFile: str = "C:/Windows/Temp/seatVie_lastrun.pkl"
if check_last_run_time(verifyFile):
    connector.start()
    update_last_run_time(verifyFile)
else:
    time.sleep(3)
