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
#  lockfile
#-----------------------------------------------------------------------------
async def get_lockfile(connection):
    import os
    path = os.path.join(connection.installation_path.encode("gb18030").decode("utf-8"), "lockfile")
    if os.path.isfile(path):
        file = open(path, "r")
        text = file.readline().split(":")
        file.close()
        print(connection.address)
        print(f"riot    {connection.auth_key}")
        return connection.auth_key
    return None

#-----------------------------------------------------------------------------
# 重复获取房间信息（Get lobby information repetitively）
#-----------------------------------------------------------------------------
async def get_lobby_information(connection):
    print("\n输入任意字符以退出程序，否则继续获取房间信息：\nPress any key to exit, or null to continue getting lobby information:")
    while input() == "":
        lobby_information = await connection.request("GET", "/lol-lobby/v2/lobby")
        print(await lobby_information.json())

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_lockfile(connection)
    await get_lobby_information(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
