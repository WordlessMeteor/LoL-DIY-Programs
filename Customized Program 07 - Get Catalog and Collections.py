from lcu_driver import Connector
import os, json, time, pandas, re, requests
from openpyxl import load_workbook

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

def load_data_online(type_zh: str, type_en: str, url: str, path: str, format: str) -> dict:
    try:
        print("正在加载%s信息……\nLoading %s information from CommunityDragon..." %(type_zh, type_en))
        captured = True
        data = requests.get(url)
        if data.ok:
            data = data.json()
            return {"captured": True, "data": data, "switch_to_offline": False, "exit": False}
        else:
            captured = False
            print(data)
            print('当前语言不可用！正在尝试离线加载数据……\nCurrent language isn\'t available! Trying loading offline data ...\n请输入%sJson数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the %s Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(type_zh, path, type_en, path))
    except requests.exceptions.RequestException:
        captured = False
        print('%s信息获取超时！正在尝试离线加载数据……\n%s information capture timeout! Trying loading offline data ...\n请输入%sJson数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the %s Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(type_zh, type_en.title(), type_zh, path, type_en, path))
    if not captured:
        while True:
            data_local = input()
            if data_local == "":
                data_local = path
            elif data_local[0] == "0":
                print("%s信息获取失败！请检查系统网络状况和代理设置。\n%s information capture failure! Please check the system network condition and agent configuration." %(type_zh, type_en.title()))
                time.sleep(3)
                return {"captured": False, "data": None, "switch_to_offline": False, "exit": True}
            elif data_local[0] == "2":
                return {"captured": False, "data": None, "switch_to_offline": True, "exit": False}
            try:
                with open(data_local, "r", encoding = "utf-8") as fp:
                    data = json.load(fp)
                if eval(format, {"data": data}):
                    return {"captured": True, "data": data, "switch_to_offline": False, "exit": True}
                else:
                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的%s数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the %s data archived in CommunityDragon database (%s)!" %(type_zh, url, type_en, url))
                    continue
            except FileNotFoundError:
                print('未找到文件“%s”！请输入正确的%sJson数据文件路径！\nFile "%s" NOT FOUND! Please input a correct %s Json data file path!' %(data_local, type_zh, data_local, type_en))
                continue
            except OSError:
                print("数据文件名不合法！请输入含有%s信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with %s information." %(type_zh, type_en))
                continue
            except json.decoder.JSONDecodeError:
                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的%s数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the %s data archived in CommunityDragon database (%s)!" %(type_zh, url, type_en, url))
                continue

def load_data_offline(path: str, format: str) -> dict:
    loaded = notfound = formaterror = False
    try:
        with open(path, "r", encoding = "utf-8") as fp:
            data = json.load(fp)
        if not eval(format, {"data": data}): #这个地方非常玄学，一定要指定“data”这个临时变量，否则会引发命名错误（Here is an unreasonable point: "data" must be determined, otherwise a NameError will be thrown）
            formaterror = True
    except FileNotFoundError:
        notfound = True
    except json.decoder.JSONDecodeError:
        formaterror = True
    else:
        if not formaterror:
            loaded = True
    return {"data": data if loaded else None, "loaded": loaded, "notfound": notfound, "formaterror": formaterror}

async def fetch_store(connection):
    #获取大区信息，用于设置工作簿保存位置和工作表名称和获取相应的CommunityDragon数据资源（Get server information to set up workbook saving directory and sheet name and fetch the adaptive CommunityDragon data resources）
    info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    displayName = info["displayName"] if info["displayName"] else (info["gameName"] if info["gameName"] else str(info["summonerId"]))
    current_puuid = info["puuid"]
    platform_TENCENT = {"BGP1": "全网通区 男爵领域（Baron Zone）", "BGP2": "峡谷之巅（Super Zone）", "EDU1": "教育网专区（CRENET Server）", "HN1": "电信一区 艾欧尼亚（Ionia）", "HN2": "电信二区 祖安（Zaun）", "HN3": "电信三区 诺克萨斯（Noxus 1）", "HN4": "电信四区 班德尔城（Bandle City）", "HN4_NEW": "电信四区 班德尔城（Bandle City）", "HN5": "电信五区 皮尔特沃夫（Piltover）", "HN6": "电信六区 战争学院（the Institute of War）", "HN7": "电信七区 巨神峰（Mount Targon）", "HN8": "电信八区 雷瑟守备（Noxus 2）", "HN9": "电信九区 裁决之地（the Proving Grounds）", "HN10": "电信十区 黑色玫瑰（the Black Rose）", "HN11": "电信十一区 暗影岛（Shadow Isles）", "HN12": "电信十二区 钢铁烈阳（the Iron Solari）", "HN13": "电信十三区 水晶之痕（Crystal Scar）", "HN14": "电信十四区 均衡教派（the Kinkou Order）", "HN15": "电信十五区 影流（the Shadow Order）", "HN16": "电信十六区 守望之海（Guardian's Sea）", "HN17": "电信十七区 征服之海（Conqueror's Sea）", "HN18": "电信十八区 卡拉曼达（Kalamanda）", "HN19": "电信十九区 皮城警备（Piltover Wardens）", "PBE": "体验服 试炼之地（Chinese PBE）", "WT1": "网通一区 比尔吉沃特（Bilgewater）", "WT1_NEW": "网通一区 比尔吉沃特（Bilgewater）", "WT2": "网通二区 德玛西亚（Demacia）", "WT2_NEW": "网通二区 德玛西亚（Demacia）", "WT3": "网通三区 弗雷尔卓德（Freljord）", "WT3_NEW": "网通三区 弗雷尔卓德（Freljord）", "WT4": "网通四区 无畏先锋（House Crownguard）", "WT4_NEW": "网通四区 无畏先锋（House Crownguard）", "WT5": "网通五区 恕瑞玛（Shurima）", "WT6": "网通六区 扭曲丛林（Twisted Treeline）", "WT7": "网通七区 巨龙之巢（the Dragon Camp）", "NJ100": "联盟一区", "GZ100": "联盟二区"}
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
        folder = "召唤师信息（Summoner Information）\\" + "国服（TENCENT）" + "\\" + platform_TENCENT[client_info["--rso_platform_id"]] + "\\" + (displayName if info["displayName"] or info["gameName"] else "0. 新玩家\\" + displayName)
    elif region == "GARENA":
        folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[region] + "\\" + (displayName if info["displayName"] or info["gameName"] else "0. 新玩家\\" + displayName)
    else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
        folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[region] + "\\" + (displayName if info["displayName"] or info["gameName"] else "0. New Player\\" + displayName)
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    #下面声明一些数据资源地址（The following code declare some data resources' URLs）
    URLPatch = "pbe" if platformId == "PBE1" else "latest"
    language_cdragon = "default" if URLPatch == "en_US" else locale.lower()
    championSkins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/skins.json" %(URLPatch, language_cdragon)
    companions_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(URLPatch, language_cdragon)
    statstones_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/statstones.json" %(URLPatch, language_cdragon)
    summonerEmotes_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-emotes.json" %(URLPatch, language_cdragon)
    summonerIcons_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(URLPatch, language_cdragon)
    tftdamageskins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftdamageskins.json" %(URLPatch, language_cdragon)
    tftmapskins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftmapskins.json" %(URLPatch, language_cdragon)
    wardSkins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/ward-skins.json" %(URLPatch, language_cdragon)
    #下面声明离线数据资源的默认地址（The following code declare the default paths of offline data resources）
    championSkins_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\skins.json"
    companions_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\companions.json"
    statstones_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\statstones.json"
    summonerEmotes_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\summoner-emotes.json"
    summonerIcons_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\summoner-icons.json"
    tftdamageskins_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tftdamageskins.json"
    tftmapskins_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tftmapskins.json"
    wardSkins_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\ward-skins.json"
    #下面声明离线数据资源的格式（The following code declare the formats of offline data resources）
    championSkins_format = 'isinstance(data, dict) and all(map(lambda x: isinstance(x, dict), data.values())) and all(i in data[j] for i in ["id", "isBase", "name", "splashPath", "uncenteredSplashPath", "tilePath", "loadScreenPath", "skinType", "rarity", "isLegacy", "splashVideoPath", "collectionSplashVideoPath", "featuresText", "emblems", "regionRarityId", "rarityGemPath", "skinLines", "skinAugments", "description"] for j in data) and all("chromaPath" in data[i] for i in data if not i in ["147000", "147001", "147015"])'
    companions_format = 'isinstance(data, list) and all(isinstance(data[i], dict) for i in range(len(data))) and all(j in data[i] for i in range(len(data)) for j in ["contentId", "itemId", "name", "loadoutsIcon", "description", "level", "speciesName", "speciesId", "rarity", "rarityValue", "isDefault", "upgrades", "TFTOnly"])'
    statstones_format = 'isinstance(data, dict) and all(i in data for i in ["statstoneData", "packData", "packIdToStatStonesIds", "seriesIdToStatStoneIds", "packIdToSubPackIds", "collectionIdToStatStoneIds", "packIdToChampIds", "champIdToPackIds", "packItemIdToContainingPackItemId"]) and all(isinstance(data[i], dict) if i != "statstoneData" and i != "packData" else isinstance(data[i], list) for i in data) and all(i in j for i in ["name", "itemId", "inventoryType", "contentId", "statstones"] for j in data["statstoneData"]) and all(i in j for statstone in data["statstoneData"] for i in ["name", "contentId", "itemId", "isRetired", "trackingType", "isEpic", "description", "milestones", "boundChampion", "category", "iconUnowned", "iconUnlit", "iconLit", "iconFull"] for j in statstone["statstones"]) and all(map(lambda x: all(i in x for i in ["name", "description", "itemId", "contentId", "storeIconImage"]), data["packData"]))'
    summonerEmotes_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(i in j for i in ["id", "name", "inventoryIcon", "description"] for j in data) and all(map(lambda x: isinstance(x["id"], int) and isinstance(x["name"], str) and isinstance(x["inventoryIcon"], str) and isinstance(x["description"], str), data))'
    summonerIcons_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["id", "title", "yearReleased", "isLegacy", "descriptions", "rarities", "disabledRegions"]), data)) and all(map(lambda x: isinstance(x["id"], int) and isinstance(x["title"], str) and isinstance(x["yearReleased"], int) and isinstance(x["isLegacy"], bool) and isinstance(x["descriptions"], list) and isinstance(x["rarities"], list) and isinstance(x["disabledRegions"], list), data))'
    tftdamageskins_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["contentId", "itemId", "name", "description", "loadoutsIcon", "groupId", "groupName", "rarity", "rarityValue", "level"]), data)) and all(map(lambda x: isinstance(x["contentId"], str) and isinstance(x["itemId"], int) and isinstance(x["name"], str) and isinstance(x["description"], str) and isinstance(x["loadoutsIcon"], str) and isinstance(x["groupId"], int) and isinstance(x["groupName"], str) and isinstance(x["rarity"], str) and isinstance(x["rarityValue"], int) and isinstance(x["level"], int), data))'
    tftmapskins_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["contentId", "itemId", "name", "description", "loadoutsIcon", "groupId", "groupName", "rarity", "rarityValue"]), data)) and all(map(lambda x: isinstance(x["contentId"], str) and isinstance(x["itemId"], int) and isinstance(x["name"], str) and isinstance(x["description"], str) and isinstance(x["loadoutsIcon"], str) and isinstance(x["groupId"], int) and isinstance(x["groupName"], str) and isinstance(x["rarity"], str) and isinstance(x["rarityValue"], int), data))'
    wardSkins_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["id", "name", "description", "wardImagePath", "wardShadowImagePath", "isLegacy", "regionalDescriptions", "rarities"]), data)) and all(map(lambda x: isinstance(x["id"], int) and isinstance(x["name"], str) and isinstance(x["description"], str) and isinstance(x["wardImagePath"], str) and isinstance(x["wardShadowImagePath"], str) and isinstance(x["isLegacy"], bool) and isinstance(x["regionalDescriptions"], list) and isinstance(x["rarities"], list), data))'
    print("请选择数据资源获取模式：\nPlease select the data resource capture mode:\n1\t在线模式（Online）\n2\t离线模式（Offline）")
    prepareMode = input()
    while True:
        if prepareMode != "" and prepareMode[0] == "1":
            #下面获取皮肤数据（The following code get champion skin data）
            championSkins_initial_dict = load_data_online("皮肤", "champion skin", championSkins_url, championSkins_local_default, championSkins_format)
            if championSkins_initial_dict["captured"]:
                championSkins_initial = championSkins_initial_dict["data"]
            elif championSkins_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif championSkins_initial_dict["exit"]:
                return 0
            #下面获取云顶之弈小小英雄数据（The following code get companion data）
            companions_initial_dict = load_data_online("云顶之弈小小英雄", "companion", companions_url, companions_local_default, companions_format)
            if companions_initial_dict["captured"]:
                companions_initial = companions_initial_dict["data"]
            elif companions_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif companions_initial_dict["exit"]:
                return 0
            #下面获取永恒星碑数据（The following code get statstone data）
            statstones_initial_dict = load_data_online("永恒星碑", "statstone", statstones_url, statstones_local_default, statstones_format)
            if statstones_initial_dict["captured"]:
                statstones_initial = statstones_initial_dict["data"]
            elif statstones_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif statstones_initial_dict["exit"]:
                return 0
            #下面获取表情数据（The following code get summoner emote data）
            summonerEmotes_initial_dict = load_data_online("表情", "summoner emote", summonerEmotes_url, summonerEmotes_local_default, summonerEmotes_format)
            if summonerEmotes_initial_dict["captured"]:
                summonerEmotes_initial = summonerEmotes_initial_dict["data"]
            elif summonerEmotes_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif summonerEmotes_initial_dict["exit"]:
                return 0
            #下面获取召唤师图标数据（The following code get summoner icon data）
            summonerIcons_initial_dict = load_data_online("召唤师图标", "summoner icon", summonerIcons_url, summonerIcons_local_default, summonerIcons_format)
            if summonerIcons_initial_dict["captured"]:
                summonerIcons_initial = summonerIcons_initial_dict["data"]
            elif summonerIcons_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif summonerIcons_initial_dict["exit"]:
                return 0
            #下面获取云顶之弈攻击特效数据（The following code get TFT damage skin data）
            tftdamageskins_initial_dict = load_data_online("云顶之弈攻击特效", "TFT damage skin", tftdamageskins_url, tftdamageskins_local_default, tftdamageskins_format)
            if tftdamageskins_initial_dict["captured"]:
                tftdamageskins_initial = tftdamageskins_initial_dict["data"]
            elif tftdamageskins_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif tftdamageskins_initial_dict["exit"]:
                return 0
            #下面获取云顶之弈棋盘皮肤数据（The following code get TFT map skin data）
            tftmapskins_initial_dict = load_data_online("云顶之弈棋盘皮肤", "TFT map skin", tftmapskins_url, tftmapskins_local_default, tftmapskins_format)
            if tftmapskins_initial_dict["captured"]:
                tftmapskins_initial = tftmapskins_initial_dict["data"]
            elif tftmapskins_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif tftmapskins_initial_dict["exit"]:
                return 0
            #下面获取守卫（眼）皮肤数据（The following code get ward skin data）
            wardSkins_initial_dict = load_data_online("守卫（眼）皮肤", "ward skin", wardSkins_url, wardSkins_local_default, wardSkins_format)
            if wardSkins_initial_dict["captured"]:
                wardSkins_initial = wardSkins_initial_dict["data"]
            elif wardSkins_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif wardSkins_initial_dict["exit"]:
                return 0
        else:
            switch_prepare_mode = False
            print('请在浏览器中打开以下网页，待加载完成后按Ctrl + S保存网页json文件至同目录的“离线数据（Offline Data）”文件夹下，并根据括号内的提示放置和命名文件。\nPlease open the following URLs in a browser, then press Ctrl + S to save the online json files into the folder "离线数据（Offline Data）" under the same directory after the website finishes loading and organize and rename the downloaded files according to the hints in the circle brackets.\n皮肤（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\skins.json）： %s\n云顶之弈小小英雄（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\companions.json）： %s\n表情（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\summoner-emotes.json）： %s\n召唤师图标（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\summoner-icons.json）： %s\n云顶之弈攻击特效（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tftdamageskins.json）： %s\n守卫（眼）皮肤（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\ward-skins.json）： %s' %(championSkins_url, companions_url, summonerIcons_url, tftdamageskins_url, wardSkins_url))
            offline_files_loaded = {"skin": False, "companion": False, "statstone": False, "summonerEmote": False, "summonerIcon": False, "tftdamageskin": False, "tftmapskin": False, "wardSkin": False}
            offline_files = {"skin": {"file": championSkins_local_default, "URL": championSkins_url, "content": "皮肤"}, "companion": {"file": companions_local_default, "URL": companions_url, "content": "云顶之弈小小英雄"}, "statstone": {"file": statstones_local_default, "URL": statstones_url, "content": "永恒星碑"}, "summonerEmote": {"file": summonerEmotes_local_default, "URL": summonerEmotes_url, "content": "表情"}, "summonerIcon": {"file": summonerIcons_local_default, "URL": summonerIcons_url, "content": "召唤师图标"}, "tftdamageskin": {"file": tftdamageskins_local_default, "URL": tftdamageskins_url, "content": "云顶之弈攻击特效"}, "tftmapskin": {"file": tftmapskins_local_default, "URL": tftmapskins_url, "content": "云顶之弈棋盘皮肤"}, "wardSkin": {"file": wardSkins_local_default, "URL": wardSkins_url, "content": "守卫（眼）皮肤"}}
            print('请按任意键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPlease input anything to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
            while any(not i for i in offline_files_loaded.values()):
                offline_files_notfound = {"skin": False, "companion": False, "statstone": False, "summonerEmote": False, "summonerIcon": False, "tftdamageskin": False, "tftmapskin": False, "wardSkin": False}
                offline_files_formaterror = {"skin": False, "companion": False, "statstone": False, "summonerEmote": False, "summonerIcon": False, "tftdamageskin": False, "tftmapskin": False, "wardSkin": False}
                prepareMode = input()
                if prepareMode != "" and prepareMode[0] == "1":
                    switch_prepare_mode = True
                    continue
                if prepareMode != "" and prepareMode[0] == "0":
                    return 0
                #下面获取皮肤数据（The following code get champion skin data）
                if not offline_files_loaded["skin"]:
                    championSkins_initial_dict = load_data_offline(championSkins_local_default, championSkins_format)
                    offline_files_loaded["skin"], offline_files_notfound["skin"], offline_files_formaterror["skin"] = championSkins_initial_dict["loaded"], championSkins_initial_dict["notfound"], championSkins_initial_dict["formaterror"]
                    if championSkins_initial_dict["loaded"]:
                        championSkins_initial = championSkins_initial_dict["data"]
                #下面获取云顶之弈小小英雄数据（The following code get companion data）
                if not offline_files_loaded["companion"]:
                    companions_initial_dict = load_data_offline(companions_local_default, companions_format)
                    offline_files_loaded["companion"], offline_files_notfound["companion"], offline_files_formaterror["companion"] = companions_initial_dict["loaded"], companions_initial_dict["notfound"], companions_initial_dict["formaterror"]
                    if companions_initial_dict["loaded"]:
                        companions_initial = companions_initial_dict["data"]
                #下面获取永恒星碑数据（The following code get statstone data）
                if not offline_files_loaded["statstone"]:
                    statstones_initial_dict = load_data_offline(statstones_local_default, statstones_format)
                    offline_files_loaded["statstone"], offline_files_notfound["statstone"], offline_files_formaterror["statstone"] = statstones_initial_dict["loaded"], statstones_initial_dict["notfound"], statstones_initial_dict["formaterror"]
                    if statstones_initial_dict["loaded"]:
                        statstones_initial = statstones_initial_dict["data"]
                #下面获取表情数据（The following code get summoner emote data）
                if not offline_files_loaded["summonerEmote"]:
                    summonerEmotes_initial_dict = load_data_offline(summonerEmotes_local_default, summonerEmotes_format)
                    offline_files_loaded["summonerEmote"], offline_files_notfound["summonerEmote"], offline_files_formaterror["summonerEmote"] = summonerEmotes_initial_dict["loaded"], summonerEmotes_initial_dict["notfound"], summonerEmotes_initial_dict["formaterror"]
                    if summonerEmotes_initial_dict["loaded"]:
                        summonerEmotes_initial = summonerEmotes_initial_dict["data"]
                #下面获取召唤师图标数据（The following code get summoner icon data）
                if not offline_files_loaded["summonerIcon"]:
                    summonerIcons_initial_dict = load_data_offline(summonerIcons_local_default, summonerIcons_format)
                    offline_files_loaded["summonerIcon"], offline_files_notfound["summonerIcon"], offline_files_formaterror["summonerIcon"] = summonerIcons_initial_dict["loaded"], summonerIcons_initial_dict["notfound"], summonerIcons_initial_dict["formaterror"]
                    if summonerIcons_initial_dict["loaded"]:
                        summonerIcons_initial = summonerIcons_initial_dict["data"]
                #下面获取云顶之弈攻击特效数据（The following code get TFT damage skin data）
                if not offline_files_loaded["tftdamageskin"]:
                    tftdamageskins_initial_dict = load_data_offline(tftdamageskins_local_default, tftdamageskins_format)
                    offline_files_loaded["tftdamageskin"], offline_files_notfound["tftdamageskin"], offline_files_formaterror["tftdamageskin"] = tftdamageskins_initial_dict["loaded"], tftdamageskins_initial_dict["notfound"], tftdamageskins_initial_dict["formaterror"]
                    if tftdamageskins_initial_dict["loaded"]:
                        tftdamageskins_initial = tftdamageskins_initial_dict["data"]
                #下面获取云顶之弈棋盘皮肤数据（The following code get TFT map skin data）
                if not offline_files_loaded["tftmapskin"]:
                    tftmapskins_initial_dict = load_data_offline(tftmapskins_local_default, tftmapskins_format)
                    offline_files_loaded["tftmapskin"], offline_files_notfound["tftmapskin"], offline_files_formaterror["tftmapskin"] = tftmapskins_initial_dict["loaded"], tftmapskins_initial_dict["notfound"], tftmapskins_initial_dict["formaterror"]
                    if tftmapskins_initial_dict["loaded"]:
                        tftmapskins_initial = tftmapskins_initial_dict["data"]
                #下面获取守卫（眼）皮肤数据（The following code get ward skin data）
                if not offline_files_loaded["wardSkin"]:
                    wardSkins_initial_dict = load_data_offline(wardSkins_local_default, wardSkins_format)
                    offline_files_loaded["wardSkin"], offline_files_notfound["wardSkin"], offline_files_formaterror["wardSkin"] = wardSkins_initial_dict["loaded"], wardSkins_initial_dict["notfound"], wardSkins_initial_dict["formaterror"]
                    if wardSkins_initial_dict["loaded"]:
                        wardSkins_initial = wardSkins_initial_dict["data"]
                #下面总结离线数据加载情况（The following code conclude the result of loading offline data）
                unloaded_offline_files = []
                notfound_offline_files = []
                formaterror_offline_files = []
                if any(offline_files_notfound.values()):
                    for i in offline_files_notfound:
                        if offline_files_notfound[i]:
                            notfound_offline_files.append(i)
                            unloaded_offline_files.append(i)
                    print("以下信息文件不存在：\nNot existing file(s):")
                    for i in notfound_offline_files:
                        print(offline_files[i]["file"] + "\t" + offline_files[i]["content"] + "\t" + offline_files[i]["URL"])
                if any(offline_files_formaterror.values()):
                    for i in offline_files_formaterror:
                        if offline_files_formaterror[i]:
                            formaterror_offline_files.append(i)
                            unloaded_offline_files.append(i)
                    print("以下信息文件格式错误：\nFormatError file(s):")
                    for i in formaterror_offline_files:
                        print(offline_files[i]["file"] + "\t" + offline_files[i]["content"] + "\t" + offline_files[i]["URL"])
                if any(not i for i in offline_files_loaded.values()):
                    print('请按任意键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPlease input anything to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
            if switch_prepare_mode:
                continue
        print("数据资源加载完成。\nData resources loaded successfully.")
        break
    #下面准备数据资源（The following code prepare the data resource）
    inventoryTypes = ["AUGMENT", "AUGMENT_SLOT", "BOOST", "BUNDLES", "CHAMPION", "CHAMPION_SKIN", "COMPANION", "CURRENCY", "EMOTE", "EVENT_PASS", "GIFT", "HEXTECH_CRAFTING", "MODE_PROGRESSION_REWARD", "MYSTERY", "QUEUE_ENTRY", "RP", "SPELL_BOOK_PAGE", "STATSTONE", "SUMMONER_CUSTOMIZATION", "SUMMONER_ICON", "TEAM_SKIN_PURCHASE", "TFT_DAMAGE_SKIN", "TFT_MAP_SKIN", "TOURNAMENT_TROPHY", "TRANSFER", "WARD_SKIN"]
    catalogDicts = {} #该变量并未投入使用，只是用于观察时分类（This variable isn't put to use. It's only intended for classifcation during inspection）
    catalogList = []
    for inventoryType in inventoryTypes:
        catalogDicts[inventoryType] = await (await connection.request("GET", "/lol-catalog/v1/items/" + inventoryType)).json()
        catalogDicts[inventoryType] = sorted(catalogDicts[inventoryType], key = lambda x: x["itemId"])
        catalogList += catalogDicts[inventoryType]
    #with open("catalogDicts.json", "w", encoding = "utf-8") as fp:
        #json.dump(catalogDicts, fp, indent = 4, ensure_ascii = False)
    #with open("catalogList.json", "w", encoding = "utf-8") as fp:
        #json.dump(catalogList, fp, indent = 4, ensure_ascii = False)
    collection = await (await connection.request("GET", '/lol-inventory/v1/inventory?inventoryTypes=["AUGMENT","AUGMENT_SLOT","BOOST","BUNDLES","CHAMPION","CHAMPION_SKIN","COMPANION","CURRENCY","EMOTE","EVENT_PASS","GIFT","HEXTECH_CRAFTING","MODE_PROGRESSION_REWARD","MYSTERY","QUEUE_ENTRY","RP","SPELL_BOOK_PAGE","STATSTONE","SUMMONER_CUSTOMIZATION","SUMMONER_ICON","TEAM_SKIN_PURCHASE","TFT_DAMAGE_SKIN","TFT_MAP_SKIN","TOURNAMENT_TROPHY","TRANSFER","WARD_SKIN"]')).json()
    #with open("collection.json", "w", encoding = "utf-8") as fp:
        #json.dump(collection, fp, indent = 4, ensure_ascii = False)
    collection_hashtable = {} #原本的藏品信息中没有记录名称，所以需要借用商品信息中的名称（The original collection information doesn't contain the names, so they're cited from the catalog information）
    for item in catalogList:
        if item["itemInstanceId"] != "":
            collection_hashtable[item["itemInstanceId"]] = item["name"]
    championSkins_hashtable = {}
    for skin in championSkins_initial.values():
        championSkins_hashtable[skin["id"]] = {}
        championSkins_hashtable[skin["id"]]["name"] = skin["name"]
        championSkins_hashtable[skin["id"]]["description"] = skin["description"]
        if "chromas" in skin:
            for chroma in skin["chromas"]:
                championSkins_hashtable[chroma["id"]] = {}
                championSkins_hashtable[chroma["id"]]["name"] = chroma["name"]
                for desc in chroma["descriptions"]:
                    if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1:
                        championSkins_hashtable[chroma["id"]]["description"] = desc["description"]
                        break
                else:
                    championSkins_hashtable[chroma["id"]]["description"] = ""
        if "questSkinInfo" in skin:
            for tier in skin["questSkinInfo"]["tiers"]:
                championSkins_hashtable[tier["id"]] = {}
                championSkins_hashtable[tier["id"]]["name"] = tier["name"]
                championSkins_hashtable[tier["id"]]["description"] = tier["description"]
    companions_hashtable = {}
    for companion in companions_initial:
        companions_hashtable[companion["itemId"]] = {}
        companions_hashtable[companion["itemId"]]["name"] = item["name"]
        companions_hashtable[companion["itemId"]]["description"] = item["description"]
    statstones_hashtable = {}
    for statstone in statstones_initial["packData"]:
        statstones_hashtable[statstone["itemId"]] = {}
        statstones_hashtable[statstone["itemId"]]["name"] = statstone["name"]
        statstones_hashtable[statstone["itemId"]]["description"] = statstone["description"]
    summonerEmotes_hashtable = {}
    for emote in summonerEmotes_initial:
        summonerEmotes_hashtable[emote["id"]] = {}
        summonerEmotes_hashtable[emote["id"]]["name"] = emote["name"]
        summonerEmotes_hashtable[emote["id"]]["description"] = emote["description"]
    summonerIcons_hashtable = {}
    for icon in summonerIcons_initial:
        summonerIcons_hashtable[icon["id"]] = {}
        summonerIcons_hashtable[icon["id"]]["name"] = icon["title"]
        for desc in icon["descriptions"]:
            if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1: #为简化代码，目前仅统计守卫（眼）在拳头大区的简介。有些简介是非空字符串，但是实际上是一堆空格（To simplify the code, only riot descriptions of wards are counted. Some descriptions are indeed non-empty strings but actually a bunch of spaces）
                summonerIcons_hashtable[icon["id"]]["description"] = desc["description"]
                break
        else:
            summonerIcons_hashtable[icon["id"]]["description"] = ""
    tftdamageskins_hashtable = {}
    for skin in tftdamageskins_initial:
        tftdamageskins_hashtable[skin["itemId"]] = {}
        tftdamageskins_hashtable[skin["itemId"]]["name"] = skin["name"]
        tftdamageskins_hashtable[skin["itemId"]]["description"] = skin["description"]
    tftmapskins_hashtable = {}
    for skin in tftmapskins_initial:
        tftmapskins_hashtable[skin["itemId"]] = {}
        tftmapskins_hashtable[skin["itemId"]]["name"] = skin["name"]
        tftmapskins_hashtable[skin["itemId"]]["description"] = skin["description"]
    wardSkins_hashtable = {}
    for wardSkin in wardSkins_initial:
        wardSkins_hashtable[wardSkin["id"]] = {}
        wardSkins_hashtable[wardSkin["id"]]["name"] = wardSkin["name"]
        wardSkins_hashtable[wardSkin["id"]]["description"] = wardSkin["description"]
    hashtable_dicts = {"CHAMPION_SKIN": championSkins_hashtable, "COMPANION": companions_hashtable, "STATSTONE": statstones_hashtable, "EMOTE": summonerEmotes_hashtable, "SUMMONER_ICON": summonerIcons_hashtable, "TFT_DAMAGE_SKIN": tftdamageskins_hashtable, "TFT_MAP_SKIN": tftmapskins_hashtable, "WARD_SKIN": wardSkins_hashtable}
    #定义商品数据结构（Define the store item data structure）
    catalog_header = {"active": "可用性", "description": "简介", "imagePath": "缩略图路径", "inactiveDate": "停止销售日期", "inventoryType": "道具类型", "itemId": "序号", "itemInstanceId": "识别码", "metadata": "元数据", "name": "名称", "offerId": "赠送代码", "owned": "已拥有", "ownershipType": "拥有权", "prices": "价格", "purchaseDate": "购买日期", "questSkinInfo": "赠送皮肤信息", "releaseDate": "发布日期", "sale": "销售信息", "subInventoryType": "次级道具类型", "subTitle": "副标题", "tags": "搜索关键词"}
    catalog_data = {}
    catalog_header_keys = list(catalog_header.keys())
    inventoryType_dict = {"AUGMENT": "AUGMENT", "AUGMENT_SLOT": "AUGMENT_SLOT", "BOOST": "加成道具", "BUNDLES": "道具包", "CHAMPION": "英雄", "CHAMPION_SKIN": "皮肤", "COMPANION": "小小英雄", "CURRENCY": "货币", "EMOTE": "表情", "EVENT_PASS": "事件通行证", "GIFT": "礼物", "HEXTECH_CRAFTING": "海克斯科技宝箱", "MODE_PROGRESSION_REWARD": "MODE_PROGRESSION_REWARD", "MYSTERY": "MYSTERY", "QUEUE_ENTRY": "队列通行证", "RP": "点券", "SPELL_BOOK_PAGE": "符文页", "STATSTONE": "永恒星碑", "SUMMONER_CUSTOMIZATION": "SUMMONER_CUSTOMIZATION", "SUMMONER_ICON": "召唤师图标", "TEAM_SKIN_PURCHASE": "TEAM_SKIN_PURCHASE", "TFT_DAMAGE_SKIN": "云顶之弈进攻特效", "TFT_MAP_SKIN": "云顶之弈棋盘皮肤", "TOURNAMENT_TROPHY": "赛事奖励", "TRANSFER": "转区项目", "WARD_SKIN": "守卫（眼）皮肤"}
    ownershipType_dict = {None: "未拥有", "F2P": "免费使用", "RENTED": "租借中", "OWNED": "已拥有"}
    subInventoryType_dict = {"": "", "lol_clash_tickets": "冠军杯赛挑战券", "tft_star_fragments": "星之碎片", "TFT_PASS": "云顶之弈事件通行证", "RECOLOR": "炫彩", "lol_clash_premium_tickets": "冠军杯赛豪华版挑战券", "LOL_EVENT_PASS": "英雄联盟事件通行证"}
    for i in range(len(catalog_header)):
        key = catalog_header_keys[i]
        catalog_data[key] = []
    #定义藏品数据结构（Define the collection item data structure）
    collection_header = {"expirationDate": "租赁到期时间", "f2p": "免费使用", "inventoryType": "道具类型", "itemId": "序号", "loyalty": "", "loyaltySources": "", "owned": "已拥有", "ownershipType": "拥有权", "purchaseDate": "购买时间", "quantity": "数量", "rental": "租借中", "uuid": "唯一识别码", "wins": "使用该道具获得的胜场数", "isVintage": "典藏皮肤", "name": "名称"}
    collection_data = {}
    collection_header_keys = list(collection_header.keys())
    for i in range(len(collection_header)):
        key = collection_header_keys[i]
        collection_data[key] = []
    #数据整理核心部分（Data assignment - core part）
    for item in catalogList:
        for i in range(len(catalog_header)):
            key = catalog_header_keys[i]
            if i == 1:
                if item[key] != "" and (len(set(list(item[key]))) != 1 or item[key][0] != " "):
                    catalog_data[key].append(item[key])
                elif item["inventoryType"] in hashtable_dicts and item["itemId"] in hashtable_dicts[item["inventoryType"]]: #道具序号为111007的炫彩皮肤没有收录在CommunityDragon数据库中（The skin chroma with the itemId 111007 isn't archived in CommunityDragon database）
                    catalog_data[key].append(hashtable_dicts[item["inventoryType"]][item["itemId"]]["description"])
                else:
                    catalog_data[key].append("")
            elif i == 2:
                if item[key].startswith("//"):
                    imagePath = "https:" + item[key]
                elif item[key].startswith("/"):
                    imagePath = connection.address + item[key]
                elif not "/" in item[key]:
                    imagePath = item[key]
                else:
                    imagePath = connection.address + "/" + item[key]
                catalog_data[key].append(imagePath)
            elif i in {3, 13, 15}:
                if item[key] == 0:
                    catalog_data[key].append("")
                elif item[key] == 18446744073709551615:
                    catalog_data[key].append("∞")
                else:
                    catalog_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(item[key])))
            elif i == 8:
                if item[key] != "":
                    catalog_data[key].append(item[key])
                elif item["inventoryType"] in hashtable_dicts:
                    catalog_data[key].append(hashtable_dicts[item["inventoryType"]][item["itemId"]]["name"])
                else:
                    catalog_data[key].append("")
            elif i == 4:
                catalog_data[key].append(inventoryType_dict[item[key]])
            elif i == 11:
                catalog_data[key].append(ownershipType_dict[item[key]])
            elif i == 12:
                priceList = []
                for price in item[key]:
                    priceList.append(str(price["cost"]) + " " + price["currency"])
                priceStr = " & ".join(priceList)
                priceStr = priceStr.replace(" IP", "蓝色精萃").replace(" RP", "点券").replace(" & ", "&")
                catalog_data[key].append(priceStr)
            elif i == 17:
                catalog_data[key].append(subInventoryType_dict[item[key]])
            else:
                catalog_data[key].append(item[key])
    for item in collection:
        for i in range(len(collection_header)):
            key = collection_header_keys[i]
            if i == 0 or i == 8:
                collection_data[key].append("") if item[key] == "" else collection_data[key].append("%s-%s-%s %s-%s-%s" %(item[key][:4], item[key][4:6], item[key][6:8], item[key][9:11], item[key][11:13], item[key][13:15]))
            elif i == 2:
                collection_data[key].append(inventoryType_dict[item[key]])
            elif i == 7:
                collection_data[key].append(ownershipType_dict[item[key]])
            elif i == 13:
                collection_data[key].append(item["payload"]["isVintage"]) if item["payload"] and "isVintage" in item["payload"] else collection_data[key].append("")
            elif i == 14:
                if item["uuid"] in collection_hashtable:
                    name = collection_hashtable[item["uuid"]]
                    if name == "" and item["inventoryType"] in hashtable_dicts:
                        name = hashtable_dicts[item["inventoryType"]][item["itemId"]]["name"]
                elif item["inventoryType"] in hashtable_dicts:
                    name = hashtable_dicts[item["inventoryType"]][item["itemId"]]["name"]
                else:
                    name = ""
                collection_data[key].append(name)
            else:
                collection_data[key].append(item[key])
    #数据框列序整理（Dataframe column ordering）
    catalog_statistics_display_order = [8, 18, 1, 5, 0, 4, 17, 7, 6, 15, 3, 12, 10, 11, 13, 14, 9, 16, 19, 2]
    catalog_data_organized = {}
    for i in catalog_statistics_display_order:
        key = catalog_header_keys[i]
        catalog_data_organized[key] = [catalog_header[key]] + catalog_data[key]
    catalog_df = pandas.DataFrame(data = catalog_data_organized)
    for i in range(catalog_df.shape[0]): #这里直接使用replace函数会把整数类型的0和1当成逻辑值替换（Here function "replace" will unexpectedly take effects on 0s and 1s of integer type）
        for j in range(catalog_df.shape[1]):
            if str(catalog_df.iat[i, j]) == "True":
                catalog_df.iat[i, j] = "√"
            elif str(catalog_df.iat[i, j]) == "False":
                catalog_df.iat[i, j] = ""
    collection_statistics_display_order = [14, 9, 3, 2, 11, 6, 10, 1, 7, 8, 0, 13, 12]
    collection_data_organized = {}
    for i in collection_statistics_display_order:
        key = collection_header_keys[i]
        collection_data_organized[key] = [collection_header[key]] + collection_data[key]
    collection_df = pandas.DataFrame(data = collection_data_organized)
    for i in range(collection_df.shape[0]): #这里直接使用replace函数会把整数类型的0和1当成逻辑值替换（Here function "replace" will unexpectedly take effects on 0s and 1s of integer type）
        for j in range(collection_df.shape[1]):
            if str(collection_df.iat[i, j]) == "True":
                collection_df.iat[i, j] = "√"
            elif str(collection_df.iat[i, j]) == "False":
                collection_df.iat[i, j] = ""
    #保存文件（Save file）
    excel_name = "Store and Collections - %s.xlsx" %displayName
    workbook_exist = True
    while True:
        try:
            with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                currentTime = time.strftime("%Y-%m-%d", time.localtime(time.time()))
                catalog_df.to_excel(excel_writer = writer, sheet_name = "Store - " + currentTime + "_" + platformId + "_" + locale)
                collection_df.to_excel(excel_writer = writer, sheet_name = "Collections - " + currentTime + "_" + platformId)
            print('商品和藏品信息已保存为“%s”！\nStore and collections information is saved as "%s"!' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
            input()
        except FileNotFoundError:
            workbook_exist = False
            os.makedirs(folder, exist_ok = True)
            with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                currentTime = time.strftime("%Y-%m-%d", time.localtime(time.time()))
                catalog_df.to_excel(excel_writer = writer, sheet_name = "Store - " + currentTime + "_" + platformId + "_" + locale)
                collection_df.to_excel(excel_writer = writer, sheet_name = "Collections - " + currentTime + "_" + platformId)
            print('商品和藏品信息已保存为“%s”！请按任意键退出。\nStore and collections information is saved as "%s"! Press any key to exit ...' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
            break
        else:
            break
    #工作表排序（Worksheet ordering）
    if workbook_exist:
        print("警告：由于该文件已存在，本次导出已追加新工作表到工作簿的末尾。这可能导致工作表顺序的错乱。是否需要对工作表进行排序？（输入任意键排序，否则不排序）\nWarning: Because the excel workbook has existed, new sheets are appended to the last of the original sheet list. This may result in the disarrangement of worksheet order. Do you want to sort the sheets? (Input anything to sort the sheets, or null to skip sorting)")
        sort = input()
        if sort != "":
            store_loaded = True
            print("正在读取刚刚创建的工作表……\nLoading the workbook just created ...")
            while True:
                try:
                    wb = load_workbook(os.path.join(folder, excel_name))
                except FileNotFoundError:
                    print('商品藏品信息工作簿读取失败！请确保“%s”文件夹内含有名为“%s”的工作簿。如果需要退出程序，请输入“0”。\nERROR reading the Store and Collections workbook! Please make sure the workbook "%s" is in the folder "%s". If you want to exit the program, please submit "0".' %(folder, excel_name, excel_name, folder))
                    store_reload = input()
                    if store_reload == "0":
                        store_loaded = False
                        break
                else:
                    break
            if store_loaded:
                sheetnames = wb.sheetnames #第一次获取原工作簿的工作表名称列表（The first time to get the sheet name list of the original workbook）
                print("请选择排序方式：\nPlease select an ordering pattern:\n1\t时间优先（默认）【Time in priority (by default)】\n2\t类别优先（Type in priority）")
                op = input()
                print("正在创建顺序工作表列表……\nCreating the ordered sheet list ...")
                date_re = re.compile(r"\d{4}-\d{2}-\d{2}") #设置正则表达式识别
                if op == "" or op[0] != "2": #按照时间优先的原则对工作表进行排序，时间相同则商品工作表在前，藏品工作表在后（Sort the sheets by time in priority. If the times are the same, then the store sheet is arranged in front of the collection sheet）
                    sheetname_date_list = list(map(lambda x: date_re.search(x).group(), sheetnames)) #从工作表名称提取日期信息形成列表（Extract the dates from the sheetnames to form a list）
                    sheetname_type_list = list(map(lambda x: x.split()[0], sheetnames)) #从工作表名称提取数据类型信息形成列表（Extract the data types from the sheetnames to form a list）
                    sheetname_platform_list = list(map(lambda x: x.split("-")[1], sheetnames)) #从工作表名称提取大区信息形成列表（Extract the platformId from the sheetnames to form a list）
                    sheetname_tmpDf = pandas.DataFrame(data = [sheetnames, sheetname_date_list, sheetname_type_list, sheetname_platform_list]).stack().unstack(0) #创建一个四列数据框，各列分别是完整工作表名、日期信息、数据类型信息和大区信息（Create a 4-column dataframe whose columns are the complete sheetname, date, data type and platformId）
                    sheetnames_sorted = sheetname_tmpDf.sort_values(by = [1, 2, 3], ascending = [True, False, True]).iloc[:, 0].tolist() #将工作表名按照第一关键字——日期信息正序排列，第二关键字——数据类型信息倒序排列（先商品后藏品），第三关键字——大区信息正序排列（Order the sheetnames according to the ascending order of the first keyword - date, the descending order of the second keyword - data type and the ascending order of the third keyword - platformId）
                else:
                    sheets_Store = [sheet_iter for sheet_iter in sheetnames if sheet_iter.startswith("Store")] #提取商品类型的工作表名称（Extract the names of the sheets containing Store data）
                    sheets_Collections = [sheet_iter for sheet_iter in sheetnames if sheet_iter.startswith("Collections")] #提取藏品类型的工作表名称（Extract the names of the sheets containing Collection data）
                    sheets_Store = sorted(sheets_Store, key = lambda x: date_re.search(x).group()) #按照日期正序排列商品类型的工作表名称（Order the Store sheetnames according to the ascending order of dates）
                    sheets_Collections = sorted(sheets_Collections, key = lambda x: date_re.search(x).group()) #按照日期正序排列藏品类型的工作表名称（Order the Collection sheetnames according to the ascending order of dates）
                    sheetnames_sorted = sheets_Store + sheets_Collections #合并列表得到先按类别排列、再按日期排列的工作表名称（Combine the lists to get the sheetname list ordered firstly by data type and secondly by date）
                #下面排列所有工作表（The following code arrange all sheets）
                print("正在排序……\nOrdering ...")
                for i in range(len(sheetnames_sorted)): #排序的思路是每次将一个工作表根据其在原工作表列表中的索引和在顺序工作表列表中的索引的差值进行移动（The main idea of sheets' sorting is to move each sheet according to the difference of the indices between in the original sheet list and in the ordered sheet list）
                    sheetnames = wb.sheetnames #因为一次移动可能导致很多其它工作表的位置发生变化，所以必须每次都重新获取工作表列表（Because a moving event may result in location change of many other sheets, the sheet list must be obtained each time）
                    sheetname_iter = sheetnames_sorted[i] #这里以顺序工作表为迭代器进行遍历，因为顺序工作表是固定不变的（Here the ordered sheet list acts as the iterator to be traversed, for the ordered sheet list is fixed）
                    if sheetnames[i] != sheetname_iter:
                        preIndex = sheetnames.index(sheetname_iter)
                        wb.move_sheet(sheetname_iter, i - preIndex) #注意移动距离数应当是排序后的索引减去排序前的索引（Note that the moving offset should be the index in the ordered list subtracted by that in the original list）
                    #print("排序进度（Ordering process）：%d/%d\t工作表名称（Sheet name）： %s" %(i + 1, len(sheetnames_sorted), sheetname_iter))
                print('正在保存中……\nSaving the ordered workbook ...')
                wb.save(os.path.join(folder, excel_name))
                print('排序完成！排好序的工作簿已保存为“%s”。请按任意键退出。\nOrdering finished! The ordered workbook is saved as "%s". Press any key to exit ...\n' %(excel_name, excel_name))
                input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await fetch_store(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
