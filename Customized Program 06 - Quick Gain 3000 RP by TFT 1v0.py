from lcu_driver import Connector
import os, time

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

async def get_summoner_data(connection):
    data = await connection.request('GET', '/lol-summoner/v1/current-summoner')
    summoner = await data.json()
    print(f"displayName:    {summoner['displayName']}")
    print(f"summonerId:     {summoner['summonerId']}")
    print(f"puuid:          {summoner['puuid']}")
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
# 快速启动云顶之弈1V0对局（Quick launch a TFT 1V0 match）
#-----------------------------------------------------------------------------
async def RP_generator(connection):
    queue = {
                "queueId": 2200
            }
    create_lobby = await connection.request("POST", "/lol-lobby/v2/lobby", data = queue)
    create_lobby = await create_lobby.json()
    print("create-lobby = ", end = "")
    print(create_lobby)
    if "errorCode" in create_lobby:
        if create_lobby["message"] == "INVALID_LOBBY":
            print("请确认当前服务器云顶之弈1V0模式可用！\nPlease ensure TFT 1V0 mode is available on current server!")
            time.sleep(5)
            return create_lobby["httpStatus"]
        elif create_lobby["message"] == "Gameflow prevented a lobby.":
            print("您正在选择英雄或者游戏内！程序即将退出！\nYou're right now in champ select or game progress! The program will exit soon!")
            time.sleep(5)
            return create_lobby["httpStatus"]
    start = await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")
    start_game = await start.json()
    print("start-game = ", end = "")
    print(start_game)
    count = 0
    while start_game != None:
        start = await connection.request("POST", "/lol-lobby/v2/lobby/matchmaking/search")
        start_game = await start.json()
        print("start-game = ", end = "")
        print(start_game, end = "")
        print(". Times tried: " + str(count))
        if count >= 5000:
            print("请求超时！请检查网络连接和秒退计时器。\nRequest timeout! Please check the network and queue dodge timer.")
            time.sleep(5)
            os._exit(0)
        count += 1
    gameflow = await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")
    gameflow_phase = await gameflow.json()
    print("gameflow-phase = ", end = "")
    print(gameflow_phase)
    count = 0
    while gameflow_phase != "ReadyCheck":
        gameflow = await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")
        gameflow_phase = await gameflow.json()
        print("gameflow-phase = ", end = "")
        print(gameflow_phase, end = "")
        print(". Times tried: " + str(count))
        if count >= 5000:
            print("接受对局超时！请检查计算机运行状况。\nAccept match timeout! Please check your computer's running situation.")
            time.sleep(5)
            os._exit(0)
        count += 1
    accept = await connection.request("POST", "/lol-matchmaking/v1/ready-check/accept")
    accept = await accept.json()
    print("match-accept = ", end = "")
    print(accept)
    count = 0
    while gameflow_phase != "InProgress":
        count += 1
        gameflow = await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")
        gameflow_phase = await gameflow.json()
        print("gameflow-phase = ", end = "")
        print(gameflow_phase, end = "")
        print(". Times tried: " + str(count))

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await RP_generator(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
