from lcu_driver import Connector
import os

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

#-----------------------------------------------------------------------------
# 获得召唤师数据（Get access to summoner data）
#-----------------------------------------------------------------------------
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
    import os
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'r')
        text = file.readline().split(':')
        file.close()
        print(connection.address)
        print(f'riot    {text[3]}')
        return text[3]
    return None

#-----------------------------------------------------------------------------
# 创建训练模式 5V5 自定义房间（Create a Practice Tool lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    custom = {
        'customGameLobby': {
            'configuration': {
                'gameMode': 'CLASSIC',
                'gameMutator': '',
                'gameServerRegion': '',
                'mapId': 21,
                'mutators': {'id': 1},
                'spectatorPolicy': 'AllAllowed',
                'teamSize': 5
              },
          'lobbyName': "WordlessMeteor's Lobby",
          'lobbyPassword': ''
        },
        'isCustom': True
    }
    print(await connection.request('POST', '/lol-lobby/v2/lobby', data = custom))

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await update_lockfile(connection)
    await get_lockfile(connection)
    await create_custom_lobby(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
