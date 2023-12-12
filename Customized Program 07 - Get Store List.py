from lcu_driver import Connector
import os
import json

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
# 获取商品（Capture items in the store）
#-----------------------------------------------------------------------------
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

async def items(connection):
    inventoryType_zh = ["", "", "加成道具", "道具包", "英雄", "炫彩皮肤", "", "货币", "表情", "事件通行证", "礼物", "海克斯科技宝箱", "", "", "", "点券", "符文页", "永恒星碑", "", "召唤师图标", "", "", "棋盘皮肤", "", "", "守卫（眼）皮肤"]
    inventoryType_en = ["AUGMENT", "AUGMENT_SLOT", "BOOST", "BUNDLES", "CHAMPION", "CHAMPION_SKIN", "COMPANION", "CURRENCY", "EMOTE", "EVENT_PASS", "GIFT", "HEXTECH_CRAFTING", "MODE_PROGRESSION_REWARD", "MYSTERY", "QUEUE_ENTRY", "RP", "SPELL_BOOK_PAGE", "STATSTONE", "SUMMONER_CUSTOMIZATION", "SUMMONER_ICON", "TEAM_SKIN_PURCHASE", "TFT_DAMAGE_SKIN", "TFT_MAP_SKIN", "TOURNAMENT_TROPHY", "TRANSFER", "WARD_SKIN"]
    print('请选择商品类型，输入“0”以退出程序：\nPlease choose inventory type. Submit "0" to exit.')
    if len(inventoryType_zh) == len(inventoryType_en):
        for i in range(len(inventoryType_en)):
           print(str(i + 1) + "\t" + inventoryType_en[i])
    while True:
        check_type = input()
        if check_type[0] == "0":
            return 0
        elif check_type in [str(i) for i in range(1, len(inventoryType_en) + 1)]:
            item = await connection.request("GET", "/lol-catalog/v1/items/" + inventoryType_en[int(check_type) - 1])
            item = await item.json()
            print(str(item))
            file = open("Store items.json", "w", encoding = "utf-8")
            file.write(json.dumps(item, indent = 4, ensure_ascii = False))
            file.close()
            print('请选择商品类型，输入“0”以退出程序：\nPlease choose inventory type. Submit "0" to exit.')
            if len(inventoryType_zh) == len(inventoryType_en):
                for i in range(len(inventoryType_en)):
                   print(str(i + 1) + "\t" + inventoryType_en[i])
        else:
            print("您的输入有误，请重新输入！\nERROR input! Please try again!")

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await items(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
