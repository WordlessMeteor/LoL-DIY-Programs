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
# 自定义函数（DIY Function）
#-----------------------------------------------------------------------------
async def get_connection_data(connection):
    current_summoner = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    print("连接信息如下：\nConnection information is as follows:")
    print("address: ", connection.address)
    print("auth_key: ", connection.auth_key)
    print("displayName: ", current_summoner["displayName"])
    print("installation_path: ", connection.installation_path)
    print("pid: ", connection.pid)
    print("port: ", connection.port)
    print("protocols: ", connection.protocols)
    print("puuid: ", current_summoner["puuid"])
    print("summonerId: ", current_summoner["summonerId"])
    print("ws_address: ", connection.ws_address)
    print()
    print("请按回车键退出……\nPress Enter to exit ...")
    input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_connection_data(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
