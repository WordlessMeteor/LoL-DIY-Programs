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
async def get_lockfile(connection):
    import os
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
# 统计当前服务器的玩家数量（Count the number of players on the current server）
#-----------------------------------------------------------------------------
async def count_summoner(connection):
    number = 0
    for i in range(9999999999999999):
        summoner_info = await connection.request("GET", "/lol-summoner/v1/summoners/" + str(i))
        info = await summoner_info.json()
        if not "errorCode" in info:
            print(str(i) + "\t" + info["displayName"])
            number += 1
    print("\n该服务器共有%d名召唤师。\nThere're totally %d summoners on this server.")
    print("请按回车键退出！Please Exit by enter!")
    input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await count_summoner(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
