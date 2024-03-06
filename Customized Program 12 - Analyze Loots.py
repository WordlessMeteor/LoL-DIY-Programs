from lcu_driver import Connector
import os, pandas, json, time

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
#  分析战利品（Analyze loots）
#-----------------------------------------------------------------------------
async def analyze_player_loots(connection): #导出玩家目前含有的战利品的信息（Exports the user's current loots' information）
    #下面设置输出文件的位置（The following code determines the output files' location）
    info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    displayName = info["displayName"]
    current_puuid = info["puuid"]
    platform_TENCENT = {"BGP1": "全网通区 男爵领域（Baron Zone）", "BGP2": "峡谷之巅（Super Zone）", "EDU1": "教育网专区（CRENET Server）", "HN1": "电信一区 艾欧尼亚（Ionia）", "HN2": "电信二区 祖安（Zaun）", "HN3": "电信三区 诺克萨斯（Noxus 1）", "HN4": "电信四区 班德尔城（Bandle City）", "HN5": "电信五区 皮尔特沃夫（Piltover）", "HN6": "电信六区 战争学院（the Institute of War）", "HN7": "电信七区 巨神峰（Mount Targon）", "HN8": "电信八区 雷瑟守备（Noxus 2）", "HN9": "电信九区 裁决之地（the Proving Grounds）", "HN10": "电信十区 黑色玫瑰（the Black Rose）", "HN11": "电信十一区 暗影岛（Shadow Isles）", "HN12": "电信十二区 钢铁烈阳（the Iron Solari）", "HN13": "电信十三区 水晶之痕（Crystal Scar）", "HN14": "电信十四区 均衡教派（the Kinkou Order）", "HN15": "电信十五区 影流（the Shadow Order）", "HN16": "电信十六区 守望之海（Guardian's Sea）", "HN17": "电信十七区 征服之海（Conqueror's Sea）", "HN18": "电信十八区 卡拉曼达（Kalamanda）", "HN19": "电信十九区 皮城警备（Piltover Wardens）", "PBE": "体验服 试炼之地（Chinese PBE）", "WT1": "网通一区 比尔吉沃特（Bilgewater）", "WT2": "网通二区 德玛西亚（Demacia）", "WT3": "网通三区 弗雷尔卓德（Freljord）", "WT4": "网通四区 无畏先锋（House Crownguard）", "WT5": "网通五区 恕瑞玛（Shurima）", "WT6": "网通六区 扭曲丛林（Twisted Treeline）", "WT7": "网通七区 巨龙之巢（the Dragon Camp）"}
    platform_RIOT = {"BR": "巴西服（Brazil）", "EUNE": "北欧和东欧服（Europe Nordic & East）", "EUW": "西欧服（Europe West）", "LAN": "北拉美服（Latin America North）", "LAS": "南拉美服（Latin America South）", "NA": "北美服（North America）", "OCE": "大洋洲服（Oceania）", "RU": "俄罗斯服（Russia）", "TR": "土耳其服（Turkey）", "JP": "日服（Japan）", "KR": "韩服（Republic of Korea）", "PBE": "测试服（Public Beta Environment）"}
    platform_GARENA = {"PH": "菲律宾服（Philippines）", "SG": "新加坡服（Singapore, Malaysia and Indonesia）", "TW": "台服（Taiwan, Hong Kong and Macau）", "VN": "越南服（Vietnam）", "TH": "泰服（Thailand）"}
    platform = {"TENCENT": "国服（TENCENT）", "RIOT": "外服（RIOT）", "GARENA": "竞舞（GARENA）"}
    riot_client_info = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region = client_info["--region"]
    locale = client_info["--locale"]
    if region == "TENCENT":
        folder = "召唤师信息（Summoner Information）\\" + platform[region] + "\\" + platform_TENCENT[client_info["--rso_platform_id"]] + "\\" + displayName
    elif region == "GARENA":
        folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[region] + "\\" + displayName
    else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
        folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[region] + "\\" + displayName
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    loots = await (await connection.request("GET", "/lol-loot/v1/loot-items")).json()
    player_loot = await (await connection.request("GET", "/lol-loot/v1/player-loot")).json()
    jsonname = "Loot - %s.json" %displayName
    while True:
        try:
            jsonfile = open(os.path.join(folder, jsonname), "w", encoding = "utf-8")
        except FileNotFoundError:
            os.makedirs(folder, exist_ok = True)
        else:
            break
    try:
        jsonfile.write(str(json.dumps(player_loot, indent = 4, ensure_ascii = False)))
    except UnicodeEncodeError:
        print("玩家战利品信息文本文档生成失败！请检查战利品信息是否包含不常用字符！\nPlayer loot text generation failure! Please check if the loot information includes any abnormal characters!\n")
    else:
        print('玩家战利品信息已保存为“%s”。\nPlayer loot information is saved as "%s".\n' %(os.path.join(folder, jsonname), os.path.join(folder, jsonname)))
    player_loot_header = {"asset": "资产类型", "count": "数量", "disenchantLootName": "分解获得精萃类型", "disenchantRecipeName": "战利品分解种类", "disenchantValue": "分解返还", "displayCategories": "战利品类别", "expiryTime": "到期时间戳", "isNew": "是否未查看", "isRental": "是否租赁", "itemDesc": "物品描述", "itemStatus": "战利品拥有状态", "localizedDescription": "战利品附加说明", "localizedName": "战利品简称", "localizedRecipeSubtitle": "战利品兑换界面说明", "localizedRecipeTitle": "战利品兑换界面标题", "lootId": "战利品序号", "lootName": "战利品名称", "parentItemStatus": "升级所需物品状态", "parentStoreItemId": "升级所需商品序号", "rarity": "内容阶位", "redeemableStatus": "可解锁状况", "refId": "解锁商品序号", "rentalGames": "可租借局数", "rentalSeconds": "可租借时间（秒）", "shadowPath": "阴影图示路径", "splashPath": "背景图路径", "storeItemId": "商品序号", "tags": "关键词", "tilePath": "方块图路径", "type": "战利品类型", "upgradeEssenceName": "升级所需精萃类型", "upgradeEssenceValue": "升级所需精萃数量", "upgradeLootName": "升级后的战利品名称", "value": "对应商品原价"}
    player_loot_data = {}
    player_loot_header_keys = list(player_loot_header.keys())
    essenceType = {"CURRENCY_champion": "蓝色精萃", "CURRENCY_cosmetic": "橙色精萃", "": ""}
    lootCategories = {"": "其它", "CHAMPION": "英雄", "CHEST": "宝箱", "COMPANION": "小小英雄", "EMOTE": "表情", "ETERNALS": "永恒星碑", "SKIN": "皮肤", "SUMMONERICON": "图标", "WARDSKIN": "守卫皮肤"}
    itemStatus = {"NONE": "未拥有", "OWNED": "已拥有"}
    rarity = {"": "无", "DEFAULT": "经典", "EPIC": "史诗", "LEGENDARY": "传说", "MYTHIC": "神话", "RARE": "稀有", "ULTIMATE": "终极"}
    redeemableStatus = {"ALREADY_OWNED": "已拥有", "CHAMPION_NOT_OWNED": "英雄未拥有", "NOT_REDEEMABLE": "不可解锁", "REDEEMABLE": "可解锁", "REDEEMABLE_RENTAL": "可激活租借"}
    lootType = {"": "其它", "BOOST": "加成道具", "CHAMPION": "永久英雄", "CHAMPION_RENTAL": "英雄碎片", "CHAMPION_TOKEN": "成就代币", "CHEST": "宝箱", "COMPANION": "小小英雄", "CURRENCY": "货币", "EMOTE": "永久表情", "EMOTE_RENTAL": "表情碎片", "MATERIAL": "材料", "SKIN": "永久皮肤", "SKIN_RENTAL": "皮肤碎片", "STATSTONE": "永久永恒星碑", "STATSTONE_SHARD": "永恒星碑碎片", "SUMMONERICON": "召唤师图标", "TFT_MAP_SKIN": "云顶之弈棋盘皮肤", "TOURNAMENTLOGO": "冠军杯赛图标", "WARDSKIN": "永久守卫皮肤", "WARDSKIN_RENTAL": "守卫皮肤碎片"}
    for i in range(len(player_loot_header_keys)):
        key = player_loot_header_keys[i]
        player_loot_data[key] = []
    for i in range(len(player_loot)):
        for j in range(len(player_loot_header_keys)):
            key = player_loot_header_keys[j]
            if j == 2 or j == 30:
                player_loot_data[key].append(essenceType[player_loot[i][key]])
            elif j == 5:
                player_loot_data[key].append(lootCategories[player_loot[i][key]])
            elif j == 10 or j == 17:
                player_loot_data[key].append(itemStatus[player_loot[i][key]])
            elif j == 19:
                player_loot_data[key].append(rarity[player_loot[i][key]])
            elif j == 20:
                player_loot_data[key].append(redeemableStatus[player_loot[i][key]])
            elif j == 29:
                player_loot_data[key].append(lootType[player_loot[i][key]])
            else:
                player_loot_data[key].append(player_loot[i][key])
    player_loot_statistics_display_order = [15, 9, 12, 1, 0, 19, 30, 31, 32, 2, 4, 33, 5, 29, 20, 17, 10, 27]
    player_loot_data_organized = {}
    for i in player_loot_statistics_display_order:
        key = player_loot_header_keys[i]
        player_loot_data_organized[key] = [player_loot_header[key]] + player_loot_data[key]
    player_loot_df = pandas.DataFrame(data = player_loot_data_organized)
    excel_name = "Player Loot - %s.xlsx" %displayName
    while True:
        try:
            with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
                player_loot_df.to_excel(excel_writer = writer, sheet_name = currentTime + " " + platformId + " " + locale)
            print('玩家战利品信息已保存为“%s”！请按任意键退出。\nPlayer loot information is saved as "%s"! Press any key to exit ...' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
            input()
        except FileNotFoundError:
            os.makedirs(folder, exist_ok = True)
            with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
                player_loot_df.to_excel(excel_writer = writer, sheet_name = currentTime + " " + platformId + " " + locale)
            print('玩家战利品信息已保存为“%s”！请按任意键退出。\nPlayer loot information is saved as "%s"! Press any key to exit ...' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
            break
        else:
            break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await analyze_player_loots(connection)
    input()

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
