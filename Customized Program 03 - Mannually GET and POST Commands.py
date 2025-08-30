from lcu_driver import Connector
import json, os, pickle, time, _io

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/07/01
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

log_folder = "日志（Logs）/Customized Program 03 - Manually GET and POST Commands"
os.makedirs(log_folder, exist_ok = True)
currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
log = open(os.path.join(log_folder, currentTime + ".log"), "a+", encoding = "utf-8")

connector = Connector()

async def get_summoner_data(connection):
    data = await connection.request('GET', '/lol-summoner/v1/current-summoner')
    summoner = await data.json()
    if not "errorCode" in summoner:
        print("displayName:    %s" %(summoner["gameName"] + "#" + summoner["tagLine"]))
        print("summonerId:     %s" %(summoner["summonerId"]))
        print("puuid:          %s" %(summoner["puuid"]))
        print("-")
    else:
        print(summoner, end = "\n\n")


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
# 向服务器发送指令（Send commands to the server）
#-----------------------------------------------------------------------------
def logInput(prompt: str = "", log: _io.TextIOWrapper = log, write_time: bool = True):
    s = input(prompt)
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
            log.write("[%s]%s\n" %(currentTime, prompt + s))
        else:
            log.write(prompt + s + "\n")
    return s

def logPrint(s: str = "", log: _io.TextIOWrapper = log, end: str = "\n", print_time: bool = False, write_time: bool = True):
    currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    if print_time:
        print("[%s]%s" %(currentTime, s), end = end, flush = end == "\r")
    else:
        print(s, end = end, flush = end == "\r")
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            log.write("[%s]%s%s" %(currentTime, str(s), "\n" if end == "\r" else end))
        else:
            log.write("%s%s" %(str(s), "\n" if end == "\r" else end))

def format_json(origin = '''{"customGameLobby": {"configuration": {"gameMode": "PRACTICETOOL","gameMutator": "","gameServerRegion": "","mapId": 11,"mutators": {"id": 4},"spectatorPolicy": "AllAllowed","teamSize": 5},"lobbyName": "WordlessMeteor's Game","lobbyPassword": null},"isCustom": true}'''): #对字符串origin进行格式化
    temp = list(str(origin))
    brace = 0 # brace用来根据花括号的级别输出对应数量的水平制表符(brace is used to input the corresponding number of horizontal tabs based on the hierachy of the curly brackets）
    for i in range(len(temp)): #j遍历temp列表
        if temp[i] == "{":
            square_bracket = 0
            brace += 1
            temp[i] = "{\n" + brace * "\t"
        elif temp[i] == ":" and temp[i + 1] != " ":
            temp[i] = ": "
        elif temp[i] == "}":
            brace -= 1
            temp[i] = "\n" + brace * "\t" + "}"
        elif temp[i] == "[":
            square_bracket = 1
            temp[i] = "["
        elif temp[i] == "]":
            square_bracket = 0
            temp[i] = "]"
        elif temp[i] == "," and not square_bracket:
            temp[i] = ",\n" + brace * "\t"
    result = "".join(temp)
    return result

async def send_commands(connection):
    method = endpoint = ""
    logPrint('请依次输入方法、统一资源标识符和请求主体（如有），以空格为分隔符：\nPlease enter the method, URI and request body (if needed), split by space:\n示例：\nExamples:\nGET类endpoint：\nGET /lol-chat/v1/friends\nGET /lol-chat/v1/friend-groups\nGET /lol-collections/v1/inventories/2936900903/backdrop\nGET /lol-collections/v1/inventories/2936900903/champion-mastery/top?limit=5\nGET /lol-game-queues/v1/custom\nGET /lol-game-queues/v1/queues\nGET /lol-hovercard/v1/friend-info-by-summoner/{summonerid}\nGET /lol-kr-playtime-reminder/v1/message\nGET /lol-platform-config/v1/namespaces\nGET /lol-lobby/v2/lobby\nGET /lol-lobby/v2/lobby/members\nGET /lol-map/v1/maps\nGET /lol-maps/v2/maps\nGET /lol-match-history/v1/web-url\nGET /lol-match-history/v1/products/lol/09f67406-d51b-5868-a0be-7ac12c2f3307/matches\nGET /lol-match-history/v1/products/tft/09f67406-d51b-5868-a0be-7ac12c2f3307/matches\nGET /lol-match-history/v1/recently-played-summoners\nGET /lol-matchmaking/v1/ready-check\nGET /lol-npe-tutorial-path/v1/tutorials\nGET /lol-patch/v1/checking-enabled\nGET /lol-patch/v1/environment\nGET /lol-patch/v1/game-version\nGET /lol-patch/v1/products/league_of_legends/install-location\nGET /lol-patch/v1/products/league_of_legends/state\nGET /lol-perks/v1/currentpage\nGET /lol-perks/v1/inventory\nGET /lol-perks/v1/styles\nGET /lol-player-behavior/v1/ban\nGET /lol-player-behavior/v1/chat-restriction\nGET /lol-player-behavior/v1/config\nGET /lol-ranked/v1/rated-ladder/RANKED_SOLO_5x5\nGET /lol-ranked/v1/ranked-stats/09f67406-d51b-5868-a0be-7ac12c2f3307\nGET /lol-ranked/v1/splits-config\nGET /lol-ranked/v1/top-rated-ladders-enabled\nGET /lol-regalia/v2/config\nGET /lol-regalia/v2/2936900903/regalia\nGET /lol-replays/v1/configuration\nGET /lol-replays/v1/metadata/4452343205\nGET /lol-rewards/v1/grants\nGET /lol-rewards/v1/groups\nGET /lol-rso-auth/configuration/v3/ready-state\nGET /lol-rso-auth/v1/authorization\nGET /lol-rso-auth/v1/authorization/access-token\nGET /lol-rso-auth/v1/authorization/id-token\nGET /lol-rso-auth/v1/authorization/userinfo\nGET /lol-service-status/v1/lcu-status\nGET /lol-shutdown/v1/notification\nGET /lol-social-leaderboard/v1/leaderboard-next-update-time?queueType=RANKED_SOLO_5x5\nGET /lol-social-leaderboard/v1/social-leaderboard-data?queueType=RANKED_SOLO_5x5\nGET /lol-social-leaderboard/v1/social-leaderboard-data?queueType=RANKED_SOLO_5x5\nGET /lol-spectator/v1/spectate\nGET /lol-store/v1/catalog\nGET /lol-store/v1/offers\nGET /lol-suggested-players/v1/suggested-players\nGET /lol-summoner/v1/check-name-availability-new-summoners/WordlessMeteor\nGET /lol-summoner/v1/check-name-availability/WordlessMeteor\nGET /lol-summoner/v1/summoner-profile?puuid=09f67406-d51b-5868-a0be-7ac12c2f3307\nGET /lol-summoner/v1/summoner-requests-ready\nGET /lol-summoner/v1/summoners?name=%E6%B1%9F%E6%88%B7%E7%81%B0%E5%8E%9F%E5%93%80\nGET /lol-summoner/v1/summoners/2936900903\nGET /lol-summoner/v1/summoners-by-puuid-cached/09f67406-d51b-5868-a0be-7ac12c2f3307\nGET /lol-summoner/v2/summoner-icons?ids=["2316157572415584","2936900903"]\nGET /lol-summoner/v2/summoner-names?ids=["2316157572415584","2936900903"]\nGET /lol-summoner/v2/summoners?ids=["2316157572415584","2936900903"]\nGET /lol-summoner/v2/summoners/puuid/09f67406-d51b-5868-a0be-7ac12c2f3307\nGET /lol-tastes/v1/ready\nGET /lol-trophies/v1/current-summoner/trophies/profile\nGET /lol-trophies/v1/players/09f67406-d51b-5868-a0be-7ac12c2f3307/tropies/profile\nGET /patcher/v1/p2p/status\nGET /patcher/v1/products\nGET /performance/v1/report\nGET /player-notifications/v1/config\nGET /plugin-manager/v1/external-plugins/availability\nGET /plugin-manager/v1/status\nGET /plugin-manager/v2/descriptions\nGET /plugin-manager/v2/plugins\nGET /plugin-manager/v2/plugins/rcp-be-lol-rso-auth\nGET /riot-messaging-service/v1/session\nGET /riot-messaging-service/v1/state\nGET /sanitizer/v1/status\n\nPOST类endpoint：\nPOST /lol-lobby/v2/lobby/matchmaking/search\nPOST /lol-matchmaking/v1/ready-check/accept\nPOST /lol-matchmaking/v1/ready-check/decline\nPOST /lol-end-of-game/v1/state/dismiss-stats\nPOST /process-control/v1/process/quit\nPOST /riotclient/unload\nPOST /riotclient/launch-ux\nPOST /riotclient/ux-flash\nPOST /riotclient/ux-allow-foreground\n\nPUT类endpoint：\nPUT /lol-lobby/v1/autofill-displayed\n\nDELETE类endpoint：\nDELETE /lol-lobby-team-builder/v1/lobby\nDELETE /lol-rso-auth/v1/session\nDELETE /riot-messaging-service/v1/connect\nDELETE /riot-messaging-service/v1/entitlements\nDELETE /lol-chat/v1/conversations/active\nDELETE /lol-chat/v1/friend-groups/2\nDELETE /lol-clash/v1/voice\nDELETE /lol-cosmetics/v1/selection/companion\nDELETE /lol-cosmetics/v1/selection/tft-damage-skin\nDELETE /lol-cosmetics/v1/selection/tft-map-skin\nDELETE /lol-lobby/v1/clash\nDELETE /lol-lobby/v1/lobby/custom/bots/bot_Nami_200\nDELETE /lol-lobby/v2/lobby\nDELETE /lol-lobby/v2/lobby/matchmaking/search\nDELETE /lol-perks/v1/pages/179282318\nDELETE /lol-premade-voice/v1/mic-test\nDELETE /lol-premade-voice/v1/session\n\nPATCH类endpoint：\nPATCH /lol-game-settings/v1/game-settings\nPATCH /lol-game-settings/v1/input-settings\n\nHEAD类endpoint：\nHEAD /{plugin}/assets/{path}')
    while True:
        request = logInput()
        tmp = request.split()
        if len(tmp) == 2:
            method, endpoint = tmp
            body = None
        elif len(tmp) == 3:
            method, endpoint = tmp[:2]
            logPrint("请求主体（Request body）：")
            while True:
                body_str = logInput()
                if body_str == "":
                    body_str = "None"
                try:
                    body = eval(body_str)
                except:
                    logPrint("请求主体格式错误！\nRequest body format error!")
                else:
                    break
        else:
            break
        if endpoint[0] != "/":
            logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
            continue
        try:
            response = await (await connection.request(method, endpoint, data = body)).json()
        except TypeError:
            logPrint("请求主体格式错误！\nRequest body format error!")
        else:
            logPrint(response)
            with open("temporary data.json", "w", encoding = "utf-8") as fp:
                fp.write(json.dumps(response, indent = 4, ensure_ascii = False))
            with open("temporary data.pkl", "wb") as fp:
                pickle.dump(response, fp)

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await send_commands(connection)
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
