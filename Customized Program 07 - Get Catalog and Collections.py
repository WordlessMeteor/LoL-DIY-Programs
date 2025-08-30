from lcu_driver import Connector
import os, json, time, pandas, re, requests
from openpyxl import load_workbook

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/07/30
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
    print("displayName:    %s" %(summoner["gameName"] + "#" + summoner["tagLine"]))
    print("summonerId:     %s" %(summoner["summonerId"]))
    print("puuid:          %s" %(summoner["puuid"]))
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

def get_info_name(info: dict, mode = 1) -> str:
    if not isinstance(info, dict) or not all(i in info for i in ["displayName", "gameName", "tagLine"]):
        print("您的召唤师信息格式有误！\nERROR format of summoner information!")
        name = ""
    else:
        if info["displayName"] or info["gameName"]:
            if info["gameName"] and info["tagLine"]:
                name = info["gameName"] + "#" + info["tagLine"]
            elif not info["tagLine"] and info["gameName"]:
                name = info["gameName"]
            else:
                name = info["displayName"]
        else: #新玩家属于这种类型（This case matches new players）
            if mode == 1:
                name = str(info["puuid"])
            elif mode == 2: #仅用于设置召唤师数据保存路径（Designed to set the summoner name directory）
                name = "0. 新玩家\\" + str(info["puuid"])
            elif mode == 3: #仅用于设置召唤师数据保存路径（Designed to set the summoner name directory）
                name = "0. New Player\\" + str(info["puuid"])
    return name

async def fetch_store(connection):
    #获取大区信息，用于设置工作簿保存位置和工作表名称和获取相应的CommunityDragon数据资源（Get server information to set up workbook saving directory and sheet name and fetch the adaptive CommunityDragon data resources）
    info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    displayName = get_info_name(info)
    current_puuid = info["puuid"]
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    platform_TENCENT = {"BGP1": "全网通区 男爵领域（Baron Zone）", "BGP2": "峡谷之巅（Super Zone）", "EDU1": "教育网专区（CRENET Server）", "HN1": "电信一区 艾欧尼亚（Ionia）", "HN2": "电信二区 祖安（Zaun）", "HN3": "电信三区 诺克萨斯（Noxus 1）", "HN4": "电信四区 班德尔城（Bandle City）", "HN4_NEW": "电信四区 班德尔城（Bandle City）", "HN5": "电信五区 皮尔特沃夫（Piltover）", "HN6": "电信六区 战争学院（the Institute of War）", "HN7": "电信七区 巨神峰（Mount Targon）", "HN8": "电信八区 雷瑟守备（Noxus 2）", "HN9": "电信九区 裁决之地（the Proving Grounds）", "HN10": "电信十区 黑色玫瑰（the Black Rose）", "HN11": "电信十一区 暗影岛（Shadow Isles）", "HN12": "电信十二区 钢铁烈阳（the Iron Solari）", "HN13": "电信十三区 水晶之痕（Crystal Scar）", "HN14": "电信十四区 均衡教派（the Kinkou Order）", "HN15": "电信十五区 影流（the Shadow Order）", "HN16": "电信十六区 守望之海（Guardian's Sea）", "HN17": "电信十七区 征服之海（Conqueror's Sea）", "HN18": "电信十八区 卡拉曼达（Kalamanda）", "HN19": "电信十九区 皮城警备（Piltover Wardens）", "PBE": "体验服 试炼之地（Chinese PBE）", "WT1": "网通一区 比尔吉沃特（Bilgewater）", "WT1_NEW": "网通一区 比尔吉沃特（Bilgewater）", "WT2": "网通二区 德玛西亚（Demacia）", "WT2_NEW": "网通二区 德玛西亚（Demacia）", "WT3": "网通三区 弗雷尔卓德（Freljord）", "WT3_NEW": "网通三区 弗雷尔卓德（Freljord）", "WT4": "网通四区 无畏先锋（House Crownguard）", "WT4_NEW": "网通四区 无畏先锋（House Crownguard）", "WT5": "网通五区 恕瑞玛（Shurima）", "WT6": "网通六区 扭曲丛林（Twisted Treeline）", "WT7": "网通七区 巨龙之巢（the Dragon Camp）", "FORCES": "比赛服 艾欧尼亚（Tournament - Ionia）", "NJ100": "联盟一区", "GZ100": "联盟二区", "CQ100": "联盟三区", "TJ100": "联盟四区", "TJ101": "联盟五区", "PREPBE": "试炼之地 临时过渡服务器（Chinese PBE Temporary）"}
    platform_RIOT = {"ME1": "中东服（Middle East）", "BR1": "巴西服（Brazil）", "EUN1": "北欧和东欧服（Europe Nordic & East）", "EUW1": "西欧服（Europe West）", "JP1": "日服（Japan）", "KR": "韩服（Republic of Korea）", "LA1": "北拉美服（Latin America North）", "LA2": "南拉美服（Latin America South）", "NA1": "北美服（North America）", "OC1": "大洋洲服（Oceania）", "TR1": "土耳其服（Turkey）", "RU": "俄罗斯服（Russia）", "PH2": "菲律宾服（Philippines）", "SG2": "新加坡服（Singapore）", "TH2": "泰服（Thailand）", "TW2": "台服（Taiwan, Hong Kong and Macau）", "VN2": "越南服（Vietnam）", "PBE1": "测试服（Public Beta Environment）"}
    platform_GARENA = {"PH1": "菲律宾服（Philippines）", "SG1": "新加坡服（Singapore, Malaysia and Indonesia）", "TW1": "台服（Taiwan, Hong Kong and Macau）", "VN1": "越南服（Vietnam）", "TH1": "泰服（Thailand）"}
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
        platform_folder = "召唤师信息（Summoner Information）\\" + "国服（TENCENT）" + "\\" + platform_TENCENT[platformId]
        folder = platform_folder + "\\" + get_info_name(info, 2)
    elif region == "GARENA":
        platform_folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[platformId]
        folder = platform_folder + "\\" + get_info_name(info, 2)
    else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
        platform_folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[platformId]
        folder = platform_folder + "\\" + get_info_name(info, 3)
    platform_config_filepath = platform_folder + "\\" + "platform_config_namespaces.json"
    while True:
        try:
            with open(platform_config_filepath, "w", encoding = "utf-8") as fp:
                json.dump(platform_config, fp, indent = 4, ensure_ascii = False)
        except FileNotFoundError: #这里需要注意是否具有创建文件夹的权限。下同（Pay attention to the authority to create the folder. So are the following）
            os.makedirs(os.path.dirname(platform_config_filepath), exist_ok = True)
        else:
            break
    #下面声明一些数据资源地址（The following code declare some data resources' URLs）
    URLPatch = "pbe" if platformId == "PBE1" or platformId == "PBE" else "latest"
    language_cdragon = "default" if URLPatch == "en_US" else locale.lower()
    championSkins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/skins.json" %(URLPatch, language_cdragon)
    companions_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(URLPatch, language_cdragon)
    nexusfinishers_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/nexusfinishers.json" %(URLPatch, language_cdragon)
    statstones_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/statstones.json" %(URLPatch, language_cdragon)
    strawberryHub_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/strawberry-hub.json" %(URLPatch, language_cdragon)
    summonerEmotes_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-emotes.json" %(URLPatch, language_cdragon)
    summonerIcons_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(URLPatch, language_cdragon)
    tftdamageskins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftdamageskins.json" %(URLPatch, language_cdragon)
    tftmapskins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftmapskins.json" %(URLPatch, language_cdragon)
    tftplaybooks_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftplaybooks.json" %(URLPatch, language_cdragon)
    tftzoomskins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftzoomskins.json" %(URLPatch, language_cdragon)
    wardSkins_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/ward-skins.json" %(URLPatch, language_cdragon)
    lolinventorytype_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/default/v1/lolinventorytype.json" %(URLPatch)
    #下面声明离线数据资源的默认地址（The following code declare the default paths of offline data resources）
    championSkins_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\skins.json" %(URLPatch, language_cdragon)
    companions_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\companions.json" %(URLPatch, language_cdragon)
    nexusfinishers_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\nexusfinishers.json" %(URLPatch, language_cdragon)
    statstones_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\statstones.json" %(URLPatch, language_cdragon)
    strawberryHub_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\strawberry-hub.json" %(URLPatch, language_cdragon)
    summonerEmotes_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\summoner-emotes.json" %(URLPatch, language_cdragon)
    summonerIcons_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\summoner-icons.json" %(URLPatch, language_cdragon)
    tftdamageskins_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftdamageskins.json" %(URLPatch, language_cdragon)
    tftmapskins_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftmapskins.json" %(URLPatch, language_cdragon)
    tftplaybooks_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftplaybooks.json" %(URLPatch, language_cdragon)
    tftzoomskins_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftzoomskins.json" %(URLPatch, language_cdragon)
    wardSkins_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\ward-skins.json" %(URLPatch, language_cdragon)
    lolinventorytype_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\default\\v1\\lolinventorytype.json" %(URLPatch)
    #下面声明离线数据资源的格式（The following code declare the formats of offline data resources）
    championSkins_format = 'isinstance(data, dict) and all(map(lambda x: isinstance(x, dict), data.values())) and all(i in data[j] for i in ["id", "isBase", "name", "splashPath", "uncenteredSplashPath", "tilePath", "loadScreenPath", "skinType", "rarity", "isLegacy", "splashVideoPath", "collectionSplashVideoPath", "featuresText", "emblems", "regionRarityId", "rarityGemPath", "skinLines", "description"] for j in data)'
    companions_format = 'isinstance(data, list) and all(isinstance(data[i], dict) for i in range(len(data))) and all(j in data[i] for i in range(len(data)) for j in ["contentId", "itemId", "name", "loadoutsIcon", "description", "level", "speciesName", "speciesId", "rarity", "rarityValue", "isDefault", "upgrades", "TFTOnly"])'
    nexusfinishers_format = 'isinstance(data, list) and all(isinstance(data[i], dict) for i in range(len(data))) and all(j in data[i] for i in range(len(data)) for j in ["name", "itemId", "contentId", "translatedName", "translatedDescription", "iconPath", "splashPath", "videoPath"]) and all(isinstance(data[i][j], str) for i in range(len(data)) for j in ["name", "contentId", "translatedName", "translatedDescription", "iconPath", "splashPath", "videoPath"]) and all(isinstance(data[i][j], int) for i in range(len(data)) for j in ["itemId"])'
    statstones_format = 'isinstance(data, dict) and all(i in data for i in ["statstoneData", "packData", "packIdToStatStonesIds", "seriesIdToStatStoneIds", "packIdToSubPackIds", "collectionIdToStatStoneIds", "packIdToChampIds", "champIdToPackIds", "packItemIdToContainingPackItemId"]) and all(isinstance(data[i], dict) if i != "statstoneData" and i != "packData" else isinstance(data[i], list) for i in data) and all(i in j for i in ["name", "itemId", "inventoryType", "contentId", "statstones"] for j in data["statstoneData"]) and all(i in j for statstone in data["statstoneData"] for i in ["name", "contentId", "itemId", "isRetired", "trackingType", "isEpic", "description", "milestones", "boundChampion", "category", "iconUnowned", "iconUnlit", "iconLit", "iconFull"] for j in statstone["statstones"]) and all(map(lambda x: all(i in x for i in ["name", "description", "itemId", "contentId", "storeIconImage"]), data["packData"]))'
    strawberryHub_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["AllowedChampions", "MapDisplayInfoList", "ProgressGroups", "PowerUpGroups", "EoGNarrativeBarks"]), data)) and all(map(lambda x: all(isinstance(x[i], dict) for i in ["AllowedChampions"]), data)) and all(map(lambda x: all(j in x[i] for i in ["AllowedChampions"] for j in ["champions"]), data)) and all(map(lambda x: all(map(lambda y: isinstance(y, list), [x["AllowedChampions"]["champions"], x["MapDisplayInfoList"], x["ProgressGroups"], x["PowerUpGroups"], x["EoGNarrativeBarks"]])), data)) and all(map(lambda x: all(map(lambda y: all(map(lambda z: isinstance(z, dict) and all(i in z for i in ["id", "o", "value"]) and all(isinstance(z[i], str) for i in ["id"]) and all(isinstance(z[i], float) for i in ["o"]) and all(isinstance(z[i], dict) for i in ["value"]), y)), [x["AllowedChampions"]["champions"], x["MapDisplayInfoList"], x["ProgressGroups"], x["PowerUpGroups"], x["EoGNarrativeBarks"]])), data))'
    summonerEmotes_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(i in j for i in ["id", "name", "inventoryIcon", "description"] for j in data) and all(map(lambda x: isinstance(x["id"], int) and isinstance(x["name"], str) and isinstance(x["inventoryIcon"], str) and isinstance(x["description"], str), data))'
    summonerIcons_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["id", "title", "yearReleased", "isLegacy", "descriptions", "rarities", "disabledRegions"]), data)) and all(map(lambda x: isinstance(x["id"], int) and isinstance(x["title"], str) and isinstance(x["yearReleased"], int) and isinstance(x["isLegacy"], bool) and isinstance(x["descriptions"], list) and isinstance(x["rarities"], list) and isinstance(x["disabledRegions"], list), data))'
    tftdamageskins_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["contentId", "itemId", "name", "description", "loadoutsIcon", "groupId", "groupName", "rarity", "rarityValue", "level"]), data)) and all(map(lambda x: isinstance(x["contentId"], str) and isinstance(x["itemId"], int) and isinstance(x["name"], str) and isinstance(x["description"], str) and isinstance(x["loadoutsIcon"], str) and isinstance(x["groupId"], int) and isinstance(x["groupName"], str) and isinstance(x["rarity"], str) and isinstance(x["rarityValue"], int) and isinstance(x["level"], int), data))'
    tftmapskins_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["contentId", "itemId", "name", "description", "loadoutsIcon", "groupId", "groupName", "rarity", "rarityValue"]), data)) and all(map(lambda x: isinstance(x["contentId"], str) and isinstance(x["itemId"], int) and isinstance(x["name"], str) and isinstance(x["description"], str) and isinstance(x["loadoutsIcon"], str) and isinstance(x["groupId"], int) and isinstance(x["groupName"], str) and isinstance(x["rarity"], str) and isinstance(x["rarityValue"], int), data))'
    tftplaybooks_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["name", "itemId", "contentId", "capTypeId", "offerId", "alternateOfferId", "translatedName", "translatedDescription", "earlyAugments", "midAugments", "lateAugments", "loadoutsIcon", "enabled", "iconPath", "iconPathSmall", "splashPath", "isDisabledInDoubleUp"]), data)) and all(map(lambda x: all(isinstance(x[i], str) for i in ["name", "contentId", "capTypeId", "offerId", "alternateOfferId", "translatedName", "translatedDescription", "loadoutsIcon", "iconPath", "iconPathSmall", "splashPath"]), data)) and all(map(lambda x: all(isinstance(x[i], int) for i in ["itemId"]), data)) and all(map(lambda x: all(isinstance(x[i], list) for i in ["earlyAugments", "midAugments", "lateAugments"]), data)) and all(map(lambda x: all(isinstance(x[i][j], dict) for i in ["earlyAugments", "midAugments", "lateAugments"] for j in range(len(x[i]))), data)) and all(map(lambda x: all(k in x[i][j] and isinstance(x[i][j][k], str) for i in ["earlyAugments", "midAugments", "lateAugments"] for j in range(len(x[i])) for k in ["name", "description", "iconPath"]), data)) and all(map(lambda x: all(isinstance(x[i], bool) for i in ["enabled", "isDisabledInDoubleUp"]), data))'
    tftzoomskins_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["contentId", "itemId", "rarity", "rarityValue", "name", "description", "loadoutsIcon", "largeLoadoutsIcon", "group", "TFTRarity"]), data)) and all(map(lambda x: all(isinstance(x[i], str) for i in ["contentId", "rarity", "name", "description", "loadoutsIcon", "largeLoadoutsIcon", "group", "TFTRarity"]), data)) and all(map(lambda x: all(isinstance(x[i], int) for i in ["itemId", "rarityValue"]), data))'
    wardSkins_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["id", "name", "description", "wardImagePath", "wardShadowImagePath", "isLegacy", "regionalDescriptions", "rarities"]), data)) and all(map(lambda x: isinstance(x["id"], int) and isinstance(x["name"], str) and isinstance(x["description"], str) and isinstance(x["wardImagePath"], str) and isinstance(x["wardShadowImagePath"], str) and isinstance(x["isLegacy"], bool) and isinstance(x["regionalDescriptions"], list) and isinstance(x["rarities"], list), data))'
    lolinventorytype_format = 'isinstance(data, list) and all(map(lambda x: isinstance(x, dict), data)) and all(map(lambda x: all(i in x for i in ["inventoryTypeId", "capInventoryTypeId", "gipAware", "gipJsonPath", "gipIsMap", "gipItemId", "gipName", "gipDescription", "gipImage"]), data)) and all(isinstance(x[i], str) for x in data for i in ["inventoryTypeId", "capInventoryTypeId", "gipJsonPath", "gipItemId", "gipName", "gipDescription", "gipImage"]) and all(isinstance(x[i], bool) for x in data for i in ["gipAware", "gipIsMap"])'
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
            #下面获取终结特效数据（The following code get nexus finisher data）
            nexusfinishers_initial_dict = load_data_online("终结特效", "nexus finisher", nexusfinishers_url, nexusfinishers_local_default, nexusfinishers_format)
            if nexusfinishers_initial_dict["captured"]:
                nexusfinishers_initial = nexusfinishers_initial_dict["data"]
            elif nexusfinishers_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif nexusfinishers_initial_dict["exit"]:
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
            #下面获取PVE模式基础数据（The following code get PVE mode basic data）
            strawberryHub_initial_dict = load_data_online("PVE模式基础", "PVE mode basic", strawberryHub_url, strawberryHub_local_default, strawberryHub_format)
            if strawberryHub_initial_dict["captured"]:
                strawberryHub_initial = strawberryHub_initial_dict["data"]
            elif strawberryHub_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif strawberryHub_initial_dict["exit"]:
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
            #下面获取云顶之弈进攻特效数据（The following code get TFT damage skin data）
            tftdamageskins_initial_dict = load_data_online("云顶之弈进攻特效", "TFT damage skin", tftdamageskins_url, tftdamageskins_local_default, tftdamageskins_format)
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
            #下面获取云顶之弈指导手册数据（The following code get TFT playbook data）
            tftplaybooks_initial_dict = load_data_online("云顶之弈指导手册", "TFT playbook", tftplaybooks_url, tftplaybooks_local_default, tftplaybooks_format)
            if tftplaybooks_initial_dict["captured"]:
                tftplaybooks_initial = tftplaybooks_initial_dict["data"]
            elif tftplaybooks_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif tftplaybooks_initial_dict["exit"]:
                return 0
            #下面获取云顶之弈传送门数据（The following code get TFT zoom skin data）
            tftzoomskins_initial_dict = load_data_online("云顶之弈传送门", "TFT zoom skin", tftzoomskins_url, tftzoomskins_local_default, tftzoomskins_format)
            if tftzoomskins_initial_dict["captured"]:
                tftzoomskins_initial = tftzoomskins_initial_dict["data"]
            elif tftzoomskins_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif tftzoomskins_initial_dict["exit"]:
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
            #下面获取道具类型数据（The following code get inventory type data）
            lolinventorytype_initial_dict = load_data_online("道具类型", "inventory type", lolinventorytype_url, lolinventorytype_local_default, lolinventorytype_format)
            if lolinventorytype_initial_dict["captured"]:
                lolinventorytype_initial = lolinventorytype_initial_dict["data"]
            elif lolinventorytype_initial_dict["switch_to_offline"]:
                prepareMode == ""
                continue
            elif lolinventorytype_initial_dict["exit"]:
                return 0
        else:
            switch_prepare_mode = False
            print('请在浏览器中打开以下网页，待加载完成后按Ctrl + S保存网页json文件至同目录的“离线数据（Offline Data）”文件夹下，并根据括号内的提示放置和命名文件。\nPlease open the following URLs in a browser, then press Ctrl + S to save the online json files into the folder "离线数据（Offline Data）" under the same directory after the website finishes loading and organize and rename the downloaded files according to the hints in the circle brackets.\n皮肤（%s）： %s\n云顶之弈小小英雄（%s）： %s\n终结特效（%s）： %s\n永恒星碑（%s）： %s\nPVE模式基础信息（%s）： %s\n表情（%s）： %s\n召唤师图标（%s）： %s\n云顶之弈进攻特效（%s）： %s\n云顶之弈棋盘皮肤（%s）： %s\n云顶之弈指导手册（%s）： %s\n云顶之弈传送门（%s）： %s\n守卫（眼）皮肤（%s）： %s\n道具类型（%s）： %s' %(championSkins_local_default[19:], championSkins_url, companions_local_default[19:], companions_url, nexusfinishers_local_default[19:], nexusfinishers_url, statstones_local_default[19:], statstones_url, strawberryHub_local_default[19:], strawberryHub_url, summonerEmotes_local_default[19:], summonerEmotes_url, summonerIcons_local_default[19:], summonerIcons_url, tftdamageskins_local_default[19:], tftdamageskins_url, tftmapskins_local_default[19:], tftmapskins_url, tftplaybooks_local_default[19:], tftplaybooks_url, tftzoomskins_local_default[19:], tftzoomskins_url, wardSkins_local_default[19:], wardSkins_url, lolinventorytype_local_default[19:], lolinventorytype_url))
            offline_files_loaded = {"skin": False, "companion": False, "nexusfinisher": False, "statstone": False, "strawberryHub": False, "summonerEmote": False, "summonerIcon": False, "tftdamageskin": False, "tftmapskin": False, "tftplaybook": False, "tftzoomskin": False, "wardSkin": False, "lolinventorytype": False}
            offline_files = {"skin": {"file": championSkins_local_default, "URL": championSkins_url, "content": "皮肤"}, "companion": {"file": companions_local_default, "URL": companions_url, "content": "云顶之弈小小英雄"}, "nexusfinisher": {"file": nexusfinishers_local_default, "URL": nexusfinishers_url, "content": "终结特效"}, "statstone": {"file": statstones_local_default, "URL": statstones_url, "content": "永恒星碑"}, "strawberryHub": {"file": strawberryHub_local_default, "URL": strawberryHub_url, "content": "PVE模式基础信息"}, "summonerEmote": {"file": summonerEmotes_local_default, "URL": summonerEmotes_url, "content": "表情"}, "summonerIcon": {"file": summonerIcons_local_default, "URL": summonerIcons_url, "content": "召唤师图标"}, "tftdamageskin": {"file": tftdamageskins_local_default, "URL": tftdamageskins_url, "content": "云顶之弈进攻特效"}, "tftmapskin": {"file": tftmapskins_local_default, "URL": tftmapskins_url, "content": "云顶之弈棋盘皮肤"}, "tftplaybook": {"file": tftplaybooks_local_default, "URL": tftplaybooks_url, "content": "云顶之弈指导手册"}, "tftzoomskin": {"file": tftzoomskins_local_default, "URL": tftzoomskins_url, "content": "云顶之弈传送门"}, "wardSkin": {"file": wardSkins_local_default, "URL": wardSkins_url, "content": "守卫（眼）皮肤"}, "lolinventorytype": {"file": lolinventorytype_local_default, "URL": lolinventorytype_url, "content": "道具类型"}}
            print('请按任意键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPlease input anything to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
            while any(not i for i in offline_files_loaded.values()):
                offline_files_notfound = {"skin": False, "companion": False, "nexusfinisher": False, "statstone": False, "strawberryHub": False, "summonerEmote": False, "summonerIcon": False, "tftdamageskin": False, "tftmapskin": False, "tftplaybook": False, "tftzoomskin": False, "wardSkin": False, "lolinventorytype": False}
                offline_files_formaterror = {"skin": False, "companion": False, "nexusfinisher": False, "statstone": False, "strawberryHub": False, "summonerEmote": False, "summonerIcon": False, "tftdamageskin": False, "tftmapskin": False, "tftplaybook": False, "tftzoomskin": False, "wardSkin": False, "lolinventorytype": False}
                prepareMode = input()
                if prepareMode != "" and prepareMode[0] == "1":
                    switch_prepare_mode = True
                    break
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
                #下面获取终结特效数据（The following code get nexus finisher data）
                if not offline_files_loaded["nexusfinisher"]:
                    nexusfinishers_initial_dict = load_data_offline(nexusfinishers_local_default, nexusfinishers_format)
                    offline_files_loaded["nexusfinisher"], offline_files_notfound["nexusfinisher"], offline_files_formaterror["nexusfinisher"] = nexusfinishers_initial_dict["loaded"], nexusfinishers_initial_dict["notfound"], nexusfinishers_initial_dict["formaterror"]
                    if nexusfinishers_initial_dict["loaded"]:
                        nexusfinishers_initial = nexusfinishers_initial_dict["data"]
                #下面获取PVE模式基础数据（The following code get PVE mode basic data）
                if not offline_files_loaded["strawberryHub"]:
                    strawberryHub_initial_dict = load_data_offline(strawberryHub_local_default, strawberryHub_format)
                    offline_files_loaded["strawberryHub"], offline_files_notfound["strawberryHub"], offline_files_formaterror["strawberryHub"] = strawberryHub_initial_dict["loaded"], strawberryHub_initial_dict["notfound"], strawberryHub_initial_dict["formaterror"]
                    if strawberryHub_initial_dict["loaded"]:
                        strawberryHub_initial = strawberryHub_initial_dict["data"]
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
                #下面获取云顶之弈进攻特效数据（The following code get TFT damage skin data）
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
                #下面获取云顶之弈指导手册数据（The following code get TFT playbook data）
                if not offline_files_loaded["tftplaybook"]:
                    tftplaybooks_initial_dict = load_data_offline(tftplaybooks_local_default, tftplaybooks_format)
                    offline_files_loaded["tftplaybook"], offline_files_notfound["tftplaybook"], offline_files_formaterror["tftplaybook"] = tftplaybooks_initial_dict["loaded"], tftplaybooks_initial_dict["notfound"], tftplaybooks_initial_dict["formaterror"]
                    if tftplaybooks_initial_dict["loaded"]:
                        tftplaybooks_initial = tftplaybooks_initial_dict["data"]
                #下面获取云顶之弈传送门数据（The following code get TFT zoom skin data）
                if not offline_files_loaded["tftzoomskin"]:
                    tftzoomskins_initial_dict = load_data_offline(tftzoomskins_local_default, tftzoomskins_format)
                    offline_files_loaded["tftzoomskin"], offline_files_notfound["tftzoomskin"], offline_files_formaterror["tftzoomskin"] = tftzoomskins_initial_dict["loaded"], tftzoomskins_initial_dict["notfound"], tftzoomskins_initial_dict["formaterror"]
                    if tftzoomskins_initial_dict["loaded"]:
                        tftzoomskins_initial = tftzoomskins_initial_dict["data"]
                #下面获取守卫（眼）皮肤数据（The following code get ward skin data）
                if not offline_files_loaded["wardSkin"]:
                    wardSkins_initial_dict = load_data_offline(wardSkins_local_default, wardSkins_format)
                    offline_files_loaded["wardSkin"], offline_files_notfound["wardSkin"], offline_files_formaterror["wardSkin"] = wardSkins_initial_dict["loaded"], wardSkins_initial_dict["notfound"], wardSkins_initial_dict["formaterror"]
                    if wardSkins_initial_dict["loaded"]:
                        wardSkins_initial = wardSkins_initial_dict["data"]
                #下面获取道具类型数据（The following code get inventory type data）
                if not offline_files_loaded["lolinventorytype"]:
                    lolinventorytype_initial_dict = load_data_offline(lolinventorytype_local_default, lolinventorytype_format)
                    offline_files_loaded["lolinventorytype"], offline_files_notfound["lolinventorytype"], offline_files_formaterror["lolinventorytype"] = lolinventorytype_initial_dict["loaded"], lolinventorytype_initial_dict["notfound"], lolinventorytype_initial_dict["formaterror"]
                    if lolinventorytype_initial_dict["loaded"]:
                        lolinventorytype_initial = lolinventorytype_initial_dict["data"]
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
    lolinventorytypes = {x["inventoryTypeId"]: x for x in lolinventorytype_initial}
    inventoryTypes = sorted(list(map(lambda x: x["inventoryTypeId"], lolinventorytype_initial)))
    #inventoryTypes = ["ACHIEVEMENT_BANNER_ACCENT", "ACHIEVEMENT_TITLE", "ANNOUNCER_PACK", "AUGMENT", "AUGMENT_SLOT", "BOOST", "BUNDLES", "CHAMPION", "CHAMPION_SKIN", "CHERRY_BOON", "COMPANION", "CURRENCY", "EMOTE", "EVENT_PASS", "FANPASS", "GIFT", "HEXTECH_CRAFTING", "MODE_PROGRESSION_REWARD", "MYSTERY", "NEXUS_FINISHER", "PREMIUM_CLUB_MEMBERSHIP", "PROVIEW_PASS", "PVE_RELIC", "PVE_SUMMONER_PACKAGE", "PVE_UPGRADE", "QUEUE_ENTRY", "REGALIA_BANNER", "REGALIA_BORDER", "REGALIA_CREST", "RP", "RUNE", "SKIN_AUGMENT", "SKIN_BORDER", "SKIN_UPGRADE_GEAR", "SKIN_UPGRADE_HOME_GUARD", "SKIN_UPGRADE_RECALL", "SKIN_UPGRADE_SPAWN", "SPELL_BOOK_PAGE", "STATSTONE", "STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP", "SUMMONER_CUSTOMIZATION", "SUMMONER_ICON", "TEAMPASS", "TEAM_SKIN_PURCHASE", "TFT_DAMAGE_SKIN", "TFT_EVENT_SKILLS", "TFT_MAP_SKIN", "TFT_PLAYBOOK", "TFT_ZOOM_SKIN", "TOURNAMENT_FLAG", "TOURNAMENT_FRAME", "TOURNAMENT_LOGO", "TOURNAMENT_TROPHY", "TRANSFER", "WARD_SKIN"]
    catalogDicts = {} #该变量并未投入使用，只是用于观察时分类（This variable isn't put to use. It's only intended for classifcation during inspection）
    catalogList = []
    for inventoryType in inventoryTypes:
        catalogDicts[inventoryType] = await (await connection.request("GET", "/lol-catalog/v1/items/" + inventoryType)).json()
        catalogDicts[inventoryType] = sorted(catalogDicts[inventoryType], key = lambda x: x["itemId"])
        catalogList += catalogDicts[inventoryType]
    json1name = "Catalog - %s.json" %(get_info_name(info))
    while True:
        try:
            with open(os.path.join(folder, json1name), "w", encoding = "utf-8") as fp: #从`lol-catalog`接口获取的商品信息含有个人拥有信息，因此放到召唤师信息文件夹里（Item information obtained from `lol-catalog` API contains personal information like ownership, so it's saved into the summoner information folder）
                json.dump(catalogDicts, fp, indent = 4, ensure_ascii = False)
        except FileNotFoundError:
            os.makedirs(folder, exist_ok = True)
        else:
            break
    #with open(os.path.join(folder, json1name), "w", encoding = "utf-8") as fp:
        #json.dump(catalogList, fp, indent = 4, ensure_ascii = False)
    print('商品信息已保存为“%s”。\nCatalog information is saved as "%s".\n' %(os.path.join(folder, json1name), os.path.join(folder, json1name)))
    store = await (await connection.request("GET", "/lol-store/v1/catalog")).json()
    store_catalogDict = {} #该变量并未投入使用，只是用于观察时分类（This variable isn't put to use. It's only intended for classifcation during inspection）
    for inventoryType in sorted(set(map(lambda x: x["inventoryType"], store))):
        store_catalogDict[inventoryType] = []
    for item in store:
        store_catalogDict[item["inventoryType"]].append(item)
    for inventoryType in store_catalogDict:
        store_catalogDict[inventoryType] = sorted(store_catalogDict[inventoryType], key = lambda x: x["itemId"]) #将商店中道具按照道具类型和道具序号升序排列（Sort the items by inventoryType and itemId）
    json2name = "Store.json"
    while True:
        try:
            with open(os.path.join(platform_folder, json2name), "w", encoding = "utf-8") as fp: #从`lol-store`接口获取的商品信息是服务器特定的，因此放到服务器文件夹里（Item information obtained from `lol-store` API is server-specific, so it's saved into the platform folder）
                json.dump(store_catalogDict, fp, indent = 4, ensure_ascii = False)
        except FileNotFoundError:
            os.makedirs(platform_folder, exist_ok = True)
        else:
            break
    print('商店信息已保存为“%s”。\nStore data are saved as "%s".\n' %(os.path.join(folder, json2name), os.path.join(folder, json2name)))
    #collection = await (await connection.request("GET", "/lol-inventory/v1/inventory", data = inventoryTypes)).json()
    collection = await (await connection.request("GET", "/lol-inventory/v1/inventory?inventoryTypes=%s" %(str(inventoryTypes).replace(" ", "").replace("'", '"')))).json()
    #collection = await (await connection.request("GET", '/lol-inventory/v1/inventory?inventoryTypes=["ACHIEVEMENT_BANNER_ACCENT","ACHIEVEMENT_TITLE","ANNOUNCER_PACK","AUGMENT","AUGMENT_SLOT","BOOST","BUNDLES","CHAMPION","CHAMPION_SKIN","CHERRY_BOON","COMPANION","CURRENCY","EMOTE","EVENT_PASS","FANPASS","GIFT","HEXTECH_CRAFTING","MODE_PROGRESSION_REWARD","MYSTERY","NEXUS_FINISHER","PREMIUM_CLUB_MEMBERSHIP","PROVIEW_PASS","PVE_RELIC","PVE_SUMMONER_PACKAGE","PVE_UPGRADE","QUEUE_ENTRY","REGALIA_BANNER","REGALIA_BORDER","REGALIA_CREST","RP","RUNE","SKIN_AUGMENT","SKIN_BORDER","SKIN_UPGRADE_GEAR","SKIN_UPGRADE_HOME_GUARD","SKIN_UPGRADE_RECALL","SKIN_UPGRADE_SPAWN","SPELL_BOOK_PAGE","STATSTONE","STRAWBERRY_BOON","STRAWBERRY_LOADOUT_ITEM","STRAWBERRY_MAP","SUMMONER_CUSTOMIZATION","SUMMONER_ICON","TEAMPASS","TEAM_SKIN_PURCHASE","TFT_DAMAGE_SKIN","TFT_EVENT_SKILLS","TFT_MAP_SKIN","TFT_PLAYBOOK","TFT_ZOOM_SKIN","TOURNAMENT_FLAG","TOURNAMENT_FRAME","TOURNAMENT_LOGO","TOURNAMENT_TROPHY","TRANSFER","WARD_SKIN"]')).json()
    json3name = "Collection - %s.json" %(get_info_name(info))
    while True:
        try:
            with open(os.path.join(folder, json3name), "w", encoding = "utf-8") as fp:
                json.dump(collection, fp, indent = 4, ensure_ascii = False)
        except FileNotFoundError:
            os.makedirs(folder, exist_ok = True)
        else:
            break
    print('藏品信息已保存为“%s”。\nCollection information is saved as "%s".\n' %(os.path.join(folder, json3name), os.path.join(folder, json3name)))
    print("正在创建索引……\nCreating index ...\n")
    collection_hashtable = {(item["inventoryType"], item["itemId"]): item["name"] for item in catalogList} | {(item["inventoryType"], item["itemId"]): item["localizations"][locale]["name"] for item in store if item["localizations"] != None} #原本的藏品信息中没有记录名称，所以需要借用商品信息中的名称。之所以不考虑使用识别码作为键，是因为在从`lol-store`接口获取的商品信息中，存在识别码重复的两件商品，而道具类型和道具序号的组合应当能够唯一确定一件商品。另外，从`lol-catalog`和`lol-store`接口获取的商品信息可以互相补充（The original collection information doesn't contain the names, so they're cited from the catalog information. The reason why `itemInstanceId` isn't taken as the key is that there're two items with the same `itemInstanceId` in the items obtaned from `lol-store` API. However, the combination of `inventoryType` and `itemId` should uniquely correspond to an item. Besides, item information obtained from `lol-catalog` API and that from `lol-store` API can supplement each other）
    championSkins_hashtable = {} #对于特定道具类型的商品，道具序号可唯一确定一件商品。下同（As for an item of specific inventory type, the itemId can uniquely correspond to that item. So can the following）
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
        companions_hashtable[companion["itemId"]]["name"] = companion["name"]
        companions_hashtable[companion["itemId"]]["description"] = companion["description"]
    nexusfinishers_hashtable = {}
    for nexusfinisher in nexusfinishers_initial:
        nexusfinishers_hashtable[nexusfinisher["itemId"]] = {}
        nexusfinishers_hashtable[nexusfinisher["itemId"]]["name"] = nexusfinisher["translatedName"]
        nexusfinishers_hashtable[nexusfinisher["itemId"]]["description"] = nexusfinisher["translatedDescription"]
    statstones_hashtable = {}
    for statstone in statstones_initial["packData"]:
        statstones_hashtable[statstone["itemId"]] = {}
        statstones_hashtable[statstone["itemId"]]["name"] = statstone["name"]
        statstones_hashtable[statstone["itemId"]]["description"] = statstone["description"]
    strawberryBoons_hashtable = {} #注意，PVE模式的相关索引都是识别码（Note that index of PBE mode data is itemInstanceId）
    strawberryLoadoutItems_hashtable = {}
    strawberryMaps_hashtable = {}
    for strawberryMap in strawberryHub_initial[0]["MapDisplayInfoList"]:
        strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]] = {}
        strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]]["name"] = strawberryMap["value"]["Name"]
        strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]]["description"] = strawberryMap["value"]["Bark"]
    for ProgressGroup in strawberryHub_initial[0]["ProgressGroups"]:
        for Milestone in ProgressGroup["value"]["Milestones"]:
            for Property in Milestone["value"]["Properties"]:
                for Reward in Property["Rewards"]:
                    if all(key in Reward for key in ["Title", "Details", "ItemId", "ItemType"]) and "CapInventoryTypeId" in Reward["ItemType"]:
                        if Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_BOON"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryBoons_hashtable:
                                if not "name" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["name"] == "":
                                    strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryBoons_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                            else:
                                strawberryBoons_hashtable[Reward["ItemId"]] = {}
                                strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                strawberryBoons_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                        elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                                if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                                    strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                            else:
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {}
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                        elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                            if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                                if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here suppose an empty dictionary has been created for this map before）
                                    strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                                    strawberryMaps_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                                else:
                                    strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + Property["Name"]
                            else:
                                strawberryMaps_hashtable[Reward["ItemId"]] = {}
                                strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                strawberryMaps_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
    for PowerUpGroup in strawberryHub_initial[0]["PowerUpGroups"]:
        for Boon in PowerUpGroup["value"]["Boons"]:
            if Boon["value"]["ContentId"] in strawberryBoons_hashtable:
                if not "name" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] == "":
                    strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] = PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"]
                if not "description" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] == "":
                    strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] = PowerUpGroup["value"]["Description"]
            else:
                strawberryBoons_hashtable[Boon["value"]["ContentId"]] = {}
                strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] = PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"]
                strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] = PowerUpGroup["value"]["Description"]
    for EoGNarrativeBark in strawberryHub_initial[0]["EoGNarrativeBarks"]:
        for Reward in EoGNarrativeBark["value"]["RewardGroup"]["Rewards"]:
            if all(key in Reward for key in ["Title", "Details", "ItemId", "ItemType"]) and "CapInventoryTypeId" in Reward["ItemType"]:
                if Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_BOON"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryBoons_hashtable:
                        if not "name" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["name"] == "":
                            strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryBoons_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryBoons_hashtable[Reward["ItemId"]] = {}
                        strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        strawberryBoons_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                        if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                            strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {}
                        strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                    if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                        if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here suppose an empty dictionary has been created for this map before）
                            strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                            strawberryMaps_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                        # else: #实际上在遍历模式进程分组时已经添加过地图激活要求信息了（Actually, when traversing the ProgressGroups, the program has added information of the requirement to activate maps）
                        #     strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + EoGNarrativeBark["value"]["RewardGroup"]["name"]
                    else:
                        strawberryMaps_hashtable[Reward["ItemId"]] = {}
                        strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                        strawberryMaps_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
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
    tftplaybooks_hashtable = {}
    for tftplaybook in tftplaybooks_initial:
        tftplaybooks_hashtable[tftplaybook["itemId"]] = {}
        tftplaybooks_hashtable[tftplaybook["itemId"]]["name"] = tftplaybook["translatedName"]
        tftplaybooks_hashtable[tftplaybook["itemId"]]["description"] = tftplaybook["translatedDescription"]
    tftzoomskins_hashtable = {}
    for skin in tftzoomskins_initial:
        tftzoomskins_hashtable[skin["itemId"]] = {}
        tftzoomskins_hashtable[skin["itemId"]]["name"] = skin["name"]
        tftzoomskins_hashtable[skin["itemId"]]["description"] = skin["description"]
    wardSkins_hashtable = {}
    for skin in wardSkins_initial:
        wardSkins_hashtable[skin["id"]] = {}
        wardSkins_hashtable[skin["id"]]["name"] = skin["name"]
        wardSkins_hashtable[skin["id"]]["description"] = skin["description"]
    #以下类型的藏品在商品中也没有记录名称，需要借助其它接口来获取其名称（Collection items of the following types aren't recorded the names in catalog, so other APIs are required to get their names）
    titles_all = await (await connection.request("GET", "/lol-challenges/v2/titles/all")).json()
    titles_hashtable = {}
    for title in titles_all.values():
        titles_hashtable[title["itemId"]] = {}
        titles_hashtable[title["itemId"]]["name"] = title["name"]
        titles_hashtable[title["itemId"]]["description"] = title["challengeTitleData"]["challengeDescription"] if title["challengeTitleData"] != None and "challengeDescription" in title["challengeTitleData"] else ""
    regaliaBanners = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_BANNER")).json()
    regaliaBanners_hashtable = {}
    for bannerId in regaliaBanners:
        regaliaBanners_hashtable[int(regaliaBanners[bannerId]["items"][0]["id"])] = {}
        regaliaBanners_hashtable[int(regaliaBanners[bannerId]["items"][0]["id"])]["name"] = regaliaBanners[bannerId]["items"][0]["localizedName"]
        regaliaBanners_hashtable[int(regaliaBanners[bannerId]["items"][0]["id"])]["description"] = regaliaBanners[bannerId]["items"][0]["localizedDescription"]
    regaliaCrests = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_CREST")).json()
    hashtable_dicts = {"CHAMPION_SKIN": championSkins_hashtable, "COMPANION": companions_hashtable, "NEXUS_FINISHER": nexusfinishers_hashtable, "STATSTONE": statstones_hashtable, "STRAWBERRY_BOON": strawberryBoons_hashtable, "STRAWBERRY_LOADOUT_ITEM": strawberryLoadoutItems_hashtable, "STRAWBERRY_MAP": strawberryMaps_hashtable, "EMOTE": summonerEmotes_hashtable, "SUMMONER_ICON": summonerIcons_hashtable, "TFT_DAMAGE_SKIN": tftdamageskins_hashtable, "TFT_MAP_SKIN": tftmapskins_hashtable, "TFT_PLAYBOOK": tftplaybooks_hashtable, "TFT_ZOOM_SKIN": tftzoomskins_hashtable, "WARD_SKIN": wardSkins_hashtable, "ACHIEVEMENT_TITLE": titles_hashtable, "REGALIA_BANNER": regaliaBanners_hashtable}
    print("开始整理数据。\nBegin to sort out the data ...")
    #定义商品数据结构（Define the store item data structure）
    catalog_header = {"active": "可用性", "description": "简介", "imagePath": "缩略图路径", "inactiveDate": "停止销售时间戳", "inventoryType": "道具类型", "itemId": "序号", "itemInstanceId": "识别码", "metadata": "元数据", "name": "名称", "offerId": "交易代码", "owned": "已拥有", "ownershipType": "拥有状态", "purchaseDate": "购买时间戳", "questSkinInfo": "任务皮肤信息", "releaseDate": "发布时间戳", "sale": "销售信息", "subInventoryType": "次级道具类型", "subTitle": "副标题", "tags": "搜索关键词", "inactiveTime": "停止销售时间", "purchaseTime": "购买时间", "releaseTime": "发布时间", "IP_cost": "原价（蓝色精萃）", "IP_costType": "支付类型（蓝色精萃）", "RP_cost": "原价（点券）", "RP_costType": "支付类型（点券）", "sale IP_cost": "售价（蓝色精萃）", "sale IP_discount": "销售折扣（蓝色精萃）", "sale IP_endDate": "停止售卖时间（蓝色精萃）", "sale IP_startDate": "开放售卖时间（蓝色精萃）", "sale RP_cost": "售价（点券）", "sale RP_discount": "销售折扣（点券）", "sale RP_endDate": "停止售卖时间（点券）", "sale RP_startDate": "开放售卖时间（点券）"}
    catalog_header_keys = list(catalog_header.keys())
    catalog_data = {}
    inventoryType_dict = {"ACHIEVEMENT_BANNER_ACCENT": "旗帜装饰", "ACHIEVEMENT_TITLE": "头衔", "ANNOUNCER_PACK": "播报员语音包", "AUGMENT": "AUGMENT", "AUGMENT_SLOT": "AUGMENT_SLOT", "BOOST": "加成道具", "BUNDLES": "道具包", "CHAMPION": "英雄", "CHAMPION_SKIN": "皮肤", "CHERRY_BOON": "斗魂竞技场赛季旅程奖励", "COMPANION": "小小英雄", "CURRENCY": "货币", "EMOTE": "表情", "EVENT_PASS": "事件通行证", "FANPASS": "粉丝通行证", "GIFT": "礼物", "HEXTECH_CRAFTING": "海克斯科技宝箱", "MODE_PROGRESSION_REWARD": "游戏模式进度奖励", "MYSTERY": "神秘道具", "NEXUS_FINISHER": "终结特效", "PREMIUM_CLUB_MEMBERSHIP": "高级俱乐部会员身份", "PROGRESSION": "通行证升级", "PROVIEW_PASS": "Pro View许可", "PVE_RELIC": "PVE_RELIC", "PVE_SUMMONER_PACKAGE": "PVE_SUMMONER_PACKAGE", "PVE_UPGRADE": "PVE模式战略目标属性增益", "QUEUE_ENTRY": "队列通行证", "REGALIA_BANNER": "旗帜", "REGALIA_BORDER": "排位边框", "REGALIA_CREST": "徽章", "RP": "点券", "RUNE": "符文", "SKIN_AUGMENT": "签名升级", "SKIN_BORDER": "皮肤边框", "SKIN_UPGRADE_GEAR": "皮肤自带服装升级", "SKIN_UPGRADE_HOME_GUARD": "皮肤自带家园卫士特效", "SKIN_UPGRADE_RECALL": "皮肤自带回城特效", "SKIN_UPGRADE_SPAWN": "皮肤自带重生特效", "SPELL_BOOK_PAGE": "符文页", "STATSTONE": "永恒星碑", "STRAWBERRY_BOON": "无尽狂潮增益效果", "STRAWBERRY_LOADOUT_ITEM": "无尽狂潮配置", "STRAWBERRY_MAP": "无尽狂潮地图", "SUMMONER_CUSTOMIZATION": "SUMMONER_CUSTOMIZATION", "SUMMONER_ICON": "召唤师图标", "TEAMPASS": "战队通行证", "TEAM_SKIN_PURCHASE": "TEAM_SKIN_PURCHASE", "TFT_DAMAGE_SKIN": "云顶之弈进攻特效", "TFT_EVENT_SKILLS": "云顶之弈技巧加成", "TFT_MAP_SKIN": "云顶之弈棋盘皮肤", "TFT_PLAYBOOK": "云顶之弈指导手册", "TFT_ZOOM_SKIN": "云顶之弈传送门", "TOURNAMENT_FLAG": "冠军杯赛旗帜", "TOURNAMENT_FRAME": "冠军杯赛旗帜框架", "TOURNAMENT_LOGO": "冠军杯赛标志", "TOURNAMENT_TROPHY": "冠军杯赛奖杯", "TRANSFER": "转区项目", "WARD_SKIN": "守卫（眼）皮肤"}
    ownershipType_dict = {None: "未拥有", "F2P": "免费使用", "RENTED": "租借中", "OWNED": "已拥有"}
    subInventoryType_dict = {None: "", "": "", "CHEST": "海克斯科技宝箱", "CHAMPION_BUNDLE": "英雄道具包", "CHROMA_BUNDLE": "炫彩道具包", "EMOTE_BUNDLE": "表情道具包", "HEXTECH_BUNDLE": "海克斯科技宝箱道具包", "LOL_EVENT_PASS": "英雄联盟事件通行证", "MATERIAL": "材料", "RECOLOR": "炫彩", "RUNE_PAGE_BUNDLE": "符文页道具包", "SKIN_BUNDLE": "皮肤道具包", "SKIN_VARIANT_BUNDLE": "皮肤套装", "TFT_PASS": "云顶之弈事件通行证", "TFT_TREASURE_TROVE_TOKEN": "云顶之弈召唤商店代币", "lol_clash_premium_tickets": "冠军杯赛豪华版挑战券", "lol_clash_tickets": "冠军杯赛挑战券", "lol_blessing_token": "圣堂花火", "lol_blue_essence": "蓝色精萃", "lol_mythic_essence": "神话精萃", "lol_orange_essence": "橙色精萃", "tft_star_fragments": "星之碎片"}
    for i in range(len(catalog_header)):
        key = catalog_header_keys[i]
        catalog_data[key] = []
    #定义商店道具数据结构（Define the store item data structure）
    store_header = {"active": "可用性", "bundled": "附赠信息", "iconUrl": "图标链接", "inactiveDate": "禁用日期", "inventoryType": "道具类型", "itemId": "序号", "itemInstanceId": "识别码", "itemRequirements": "购买要求", "maxQuantity": "最大购买数量", "metadata": "元数据", "offerId": "交易代码", "releaseDate": "发布日期", "subInventoryType": "次级道具类型", "tags": "关键词", "name": "名称", "description": "简介", "IP_cost": "原价（蓝色精粹）", "IP_discount": "折扣（蓝色精粹）", "RP_cost": "原价（点券）", "RP_dscount": "折扣（点券）", "sale endDate": "停止售卖时间", "sale startDate": "开放售卖时间", "sale IP_cost": "售价（蓝色精粹）", "sale IP_discount": "销售折扣（蓝色精粹）", "sale RP_cost": "售价（点券）", "sale RP_discount": "销售折扣（点券）"}
    store_header_keys = list(store_header.keys())
    store_data = {}
    for i in range(len(store_header)):
        key = store_header_keys[i]
        store_data[key] = []
    #定义藏品数据结构（Define the collection item data structure）
    collection_header = {"expirationDate": "租赁到期时间", "f2p": "免费使用", "inventoryType": "道具类型", "itemId": "序号", "loyalty": "", "loyaltySources": "", "owned": "已拥有", "ownershipType": "拥有权", "purchaseDate": "购买时间", "quantity": "数量", "rental": "租借中", "usedInGameDate": "上次使用时间", "uuid": "唯一识别码", "wins": "使用该道具可获得增益的胜场数", "isVintage": "典藏皮肤", "name": "名称"}
    collection_header_keys = list(collection_header.keys())
    collection_data = {}
    for i in range(len(collection_header)):
        key = collection_header_keys[i]
        collection_data[key] = []
    #数据整理核心部分（Data assignment - core part）
    for item_index in range(len(catalogList)):
        item = catalogList[item_index]
        priceDict = {}
        for price in item["prices"]:
            priceDict[price["currency"]] = price
        sale_priceDict = {}
        for price in item["prices"]:
            if price["sale"] != None:
                sale_priceDict[price["currency"]] = price["sale"]
        for i in range(len(catalog_header)):
            key = catalog_header_keys[i]
            if i <= 21:
                if i == 1: #简介（`description`）
                    if item[key] != "" and (len(set(list(item[key]))) != 1 or item[key][0] != " "):
                        catalog_data[key].append(item[key])
                    elif item["inventoryType"] in hashtable_dicts:
                        if item["inventoryType"] in {"STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP"} and item["itemInstanceId"] in hashtable_dicts[item["inventoryType"]]: #PVE模式相关的索引是识别码（PVE mode hashtable index is itemInstanceId）
                            catalog_data[key].append(hashtable_dicts[item["inventoryType"]][item["itemInstanceId"]]["description"]) #为了简化这里的代码，上面所有索引字典的描述键必须是“description”（To simplify the code here, name keys of all above hashtable dictionaries must be "description"）
                        elif item["itemId"] in hashtable_dicts[item["inventoryType"]]: #道具序号为111007的炫彩皮肤没有收录在CommunityDragon数据库中（The skin chroma with the itemId 111007 isn't archived in CommunityDragon database）
                            catalog_data[key].append(hashtable_dicts[item["inventoryType"]][item["itemId"]]["description"])
                        else:
                            catalog_data[key].append("")
                    else:
                        catalog_data[key].append("")
                elif i == 2: #缩略图路径（`imagePath`）
                    if item[key].startswith("//"):
                        imagePath = "https:" + item[key]
                    elif item[key].startswith("/"):
                        imagePath = connection.address + item[key]
                    elif not "/" in item[key]:
                        imagePath = item[key]
                    else:
                        imagePath = connection.address + "/" + item[key]
                    catalog_data[key].append(imagePath)
                elif i == 4: #道具类型（`inventoryType`）
                    catalog_data[key].append(inventoryType_dict[item[key]])
                elif i == 8: #名称（`name`）
                    if item[key] != "":
                        catalog_data[key].append(item[key])
                    elif item["inventoryType"] in hashtable_dicts:
                        if item["inventoryType"] in {"STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP"} and item["itemInstanceId"] in hashtable_dicts[item["inventoryType"]]:
                            catalog_data[key].append(hashtable_dicts[item["inventoryType"]][item["itemInstanceId"]]["name"]) #为了简化这里的代码，上面所有索引字典的名称键必须是“name”（To simplify the code here, name keys of all above hashtable dictionaries must be "name"）
                        elif item["itemId"] in hashtable_dicts[item["inventoryType"]]:
                            catalog_data[key].append(hashtable_dicts[item["inventoryType"]][item["itemId"]]["name"])
                        else:
                            catalog_data[key].append("")
                    else:
                        catalog_data[key].append("")
                elif i == 11: #拥有状态（`ownershipType`）
                    catalog_data[key].append(ownershipType_dict[item[key]])
                elif i == 16: #次级道具类型（`subInventoryType`）
                    catalog_data[key].append(subInventoryType_dict[item[key]])
                elif i >= 19: #时间戳相关键（Timestamp-related keys）
                    subkey = "inactiveDate" if i == 19 else "purchaseDate" if i == 20 else "releaseDate"
                    catalog_data[key].append("" if item[subkey] == 0 else "∞" if item[subkey] == 18446744073709551615 else time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(item[subkey])))
                else:
                    catalog_data[key].append(item[key])
            elif i <= 25:
                currency, subkey = key.split("_")
                if currency in priceDict and subkey in priceDict[currency]:
                    catalog_data[key].append(priceDict[currency][subkey])
                else:
                    catalog_data[key].append("")
            else:
                currency, subkey = key.split(" ")[1].split("_")
                if currency in sale_priceDict and subkey in sale_priceDict[currency]:
                    catalog_data[key].append(sale_priceDict[currency][subkey])
                else:
                    catalog_data[key].append("")
        if item_index < len(catalogList) - 1:
            print("商品信息整理进度（Catalog data sorting process）：%d/%d" %(item_index + 1, len(catalogList)), end = "\r", flush = True)
        else:
            print("商品信息整理进度（Catalog data sorting process）：%d/%d" %(item_index + 1, len(catalogList)))
    for item_index in range(len(store)):
        item = store[item_index]
        priceDict = {} #应用于“i <= 19”的场景（Applies when "i <= 19"）
        for price in item["prices"]:
            priceDict[price["currency"]] = price
        sale_priceDict = {} #应用与“i >= 22”的场景（Applies when "i >= 22"）
        if item["sale"] != None:
            for price in item["sale"]["prices"]:
                sale_priceDict[price["currency"]] = price
        for i in range(len(store_header)):
            key = store_header_keys[i]
            if i <= 13:
                if i == 4: #道具类型（`inventoryType`）
                    store_data[key].append(inventoryType_dict[item[key]])
                elif i == 7: #购买要求（`itemRequirements`）
                    itemRequirements = []
                    if item[key] != None:
                        for requirement in item[key]:
                            requirement["name"] = collection_hashtable.get((requirement["inventoryType"], requirement["itemId"]), "")
                            itemRequirements.append(requirement)
                    store_data[key].append(itemRequirements)
                elif i == 12: #次级道具类型（`subInventoryType`）
                    store_data[key].append(subInventoryType_dict[item[key]])
                else:
                    store_data[key].append(item[key])
            elif i <= 15:
                value = ""
                if item["localizations"] != None and locale in item["localizations"] and key in item["localizations"][locale]:
                    value = item["localizations"][locale][key]
                if value == "": #当商店中没有给出一件道具的名称和描述时，从索引字典中获取（When the store doesn't provide an item's name and description, get them from the hashtable dictionaries）
                    if item["inventoryType"] in hashtable_dicts:
                        if item["inventoryType"] in {"STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP"} and item["itemInstanceId"] in hashtable_dicts[item["inventoryType"]]:
                            value = hashtable_dicts[item["inventoryType"]][item["itemInstanceId"]][key]
                        elif item["itemId"] in hashtable_dicts[item["inventoryType"]]:
                            value = hashtable_dicts[item["inventoryType"]][item["itemId"]][key]
                store_data[key].append(value)
            elif i <= 19:
                currency, subkey = key.split("_")
                if currency in priceDict and subkey in priceDict[currency]:
                    store_data[key].append(priceDict[currency][subkey])
                else:
                    store_data[key].append("")
            elif i <= 21:
                store_data[key].append(item["sale"][key.split()[1]] if item["sale"] != None else "")
            else:
                currency, subkey = key.split(" ")[1].split("_")
                if currency in sale_priceDict and subkey in sale_priceDict[currency]:
                    store_data[key].append(sale_priceDict[currency][subkey])
                else:
                    store_data[key].append("")
        if item_index < len(store) - 1:
            print("商店信息整理进度（Store data sorting process）：%d/%d" %(item_index + 1, len(store)), end = "\r", flush = True)
        else:
            print("商店信息整理进度（Store data sorting process）：%d/%d" %(item_index + 1, len(store)))
    for item_index in range(len(collection)):
        item = collection[item_index]
        for i in range(len(collection_header)):
            key = collection_header_keys[i]
            if i in {0, 8, 11}: #时间字符串相关键（Time string-related keys）
                collection_data[key].append("") if item[key] == "" else collection_data[key].append("%s-%s-%s %s-%s-%s" %(item[key][:4], item[key][5:7], item[key][8:10], item[key][11:13], item[key][14:16], item[key][17:19])) if "-" in item[key] and ":" in item[key] else collection_data[key].append("%s-%s-%s %s-%s-%s" %(item[key][:4], item[key][4:6], item[key][6:8], item[key][9:11], item[key][11:13], item[key][13:15]))
            elif i == 2: #道具类型（`inventoryType`）
                collection_data[key].append(inventoryType_dict[item[key]])
            elif i == 7: #拥有权（`ownershipType`）
                collection_data[key].append(ownershipType_dict[item[key]])
            elif i == 14: #典藏皮肤（带边框）（`isVintage`）
                collection_data[key].append(item["payload"]["isVintage"]) if item["payload"] and "isVintage" in item["payload"] else collection_data[key].append(False) #没有“是否典藏”选项的默认不是典藏（An item without the "isVintage" key can't be vintage）
            elif i == 15: #名称（`name`）
                if (item["inventoryType"], item["itemId"]) in collection_hashtable:
                    name = collection_hashtable[(item["inventoryType"], item["itemId"])]
                elif item["inventoryType"] in hashtable_dicts: #商品中可能不包含藏品（A collection item may not be contained in the collection）
                    if item["inventoryType"] in {"STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP"} and item["uuid"] in hashtable_dicts[item["inventoryType"]]:
                        name = hashtable_dicts[item["inventoryType"]][item["uuid"]]["name"]
                    elif item["itemId"] in hashtable_dicts[item["inventoryType"]]:
                        name = hashtable_dicts[item["inventoryType"]][item["itemId"]]["name"]
                    else:
                        name = ""
                else:
                    name = ""
                collection_data[key].append(name)
            else:
                collection_data[key].append(item[key])
        if item_index < len(collection) - 1:
            print("藏品信息整理进度（Collection data sorting process）：%d/%d" %(item_index + 1, len(collection)), end = "\r", flush = True)
        else:
            print("藏品信息整理进度（Collection data sorting process）：%d/%d\n" %(item_index + 1, len(collection)))
    #数据框列序整理（Dataframe column ordering）
    catalog_statistics_output_order = [8, 17, 1, 5, 0, 4, 16, 7, 6, 21, 19, 22, 23, 24, 25, 15, 26, 27, 29, 28, 30, 31, 33, 32, 10, 11, 20, 13, 9, 18, 2]
    catalog_data_organized = {}
    for i in catalog_statistics_output_order:
        key = catalog_header_keys[i]
        catalog_data_organized[key] = catalog_data[key]
    catalog_df = pandas.DataFrame(data = catalog_data_organized)
    for column in catalog_df:
        if catalog_df[column].dtype == "bool":
            catalog_df[column] = catalog_df[column].astype(str)
            for i in range(len(catalog_df)):
                catalog_df.loc[i, column] = "√" if catalog_df[column][i] == "True" else ""
    catalog_df = pandas.concat([pandas.DataFrame([catalog_header])[catalog_df.columns], catalog_df], ignore_index = True)
    store_statistics_output_order = [14, 15, 5, 0, 4, 12, 9, 1, 6, 11, 3, 16, 17, 18, 19, 8, 7, 10, 21, 20, 22, 23, 24, 25, 13, 2]
    store_data_organized = {}
    for i in store_statistics_output_order:
        key = store_header_keys[i]
        store_data_organized[key] = store_data[key]
    store_df = pandas.DataFrame(data = store_data_organized)
    for column in store_df:
        if store_df[column].dtype == "bool":
            store_df[column] = store_df[column].astype(str)
            for i in range(len(store_df)):
                store_df.loc[i, column] = "√" if store_df[column][i] == "True" else ""
    store_df = pandas.concat([pandas.DataFrame([store_header])[store_df.columns], store_df], ignore_index = True)
    collection_statistics_output_order = [15, 9, 3, 2, 12, 6, 10, 1, 7, 8, 0, 14, 13, 11]
    collection_data_organized = {}
    for i in collection_statistics_output_order:
        key = collection_header_keys[i]
        collection_data_organized[key] = collection_data[key]
    collection_df = pandas.DataFrame(data = collection_data_organized)
    for column in collection_df:
        if collection_df[column].dtype == "bool":
            collection_df[column] = collection_df[column].astype(str)
            for i in range(len(collection_df)):
                collection_df.loc[i, column] = "√" if collection_df[column][i] == "True" else ""
    collection_df = pandas.concat([pandas.DataFrame([collection_header])[collection_df.columns], collection_df], ignore_index = True)
    version = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    version_df = pandas.DataFrame({"Patch": [version]})
    #保存文件（Save file）
    print("开始导出到工作簿。\nBegin to export to the workbook.\n")
    excel_name = f"Store - {platformId}.xlsx"
    while True:
        try:
            with pandas.ExcelWriter(path = os.path.join(platform_folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                currentTime = time.strftime("%Y-%m-%d", time.localtime(time.time()))
                store_df.to_excel(excel_writer = writer, sheet_name = "Store - " + currentTime + "_" + platformId + "_" + locale)
            with pandas.ExcelWriter(path = os.path.join(platform_folder, excel_name), mode = "a", if_sheet_exists = "overlay") as writer:
                version_df.to_excel(excel_writer = writer, sheet_name = "Store - " + currentTime + "_" + platformId + "_" + locale, header = None, index = False, startcol = 0, startrow = 0)
            print('商店数据已保存为“%s”！\nStore data are saved as "%s"!' %(os.path.join(platform_folder, excel_name), os.path.join(platform_folder, excel_name)))
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
            input()
        except FileNotFoundError:
            workbook_exist = False
            os.makedirs(platform_folder, exist_ok = True)
            with pandas.ExcelWriter(path = os.path.join(platform_folder, excel_name)) as writer:
                currentTime = time.strftime("%Y-%m-%d", time.localtime(time.time()))
                store_df.to_excel(excel_writer = writer, sheet_name = "Store - " + currentTime + "_" + platformId + "_" + locale)
                version_df.to_excel(excel_writer = writer, sheet_name = "Store - " + currentTime + "_" + platformId + "_" + locale, header = None, index = False, startcol = 0, startrow = 0)
            print('商店数据已保存为“%s”！\nStore data are saved as "%s"!' %(os.path.join(platform_folder, excel_name), os.path.join(platform_folder, excel_name)))
            break
        else:
            break
    excel_name = "Store and Collections - %s.xlsx" %displayName
    excel_name_sorted = "Store and Collections - %s (sorted).xlsx" %displayName
    workbook_exist = True
    while True:
        try:
            with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                currentTime = time.strftime("%Y-%m-%d", time.localtime(time.time()))
                catalog_df.to_excel(excel_writer = writer, sheet_name = "Catalog - " + currentTime + "_" + platformId + "_" + locale)
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
                catalog_df.to_excel(excel_writer = writer, sheet_name = "Catalog - " + currentTime + "_" + platformId + "_" + locale)
                collection_df.to_excel(excel_writer = writer, sheet_name = "Collections - " + currentTime + "_" + platformId)
            print('商品和藏品信息已保存为“%s”！\nStore and collections information is saved as "%s"!' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
            break
        else:
            break
    #工作表排序（Worksheet ordering）
    if workbook_exist:
        print("警告：由于该文件已存在，本次导出已追加新工作表到工作簿的末尾。这可能导致工作表顺序的错乱。是否需要对工作表进行排序？（输入任意键排序，否则不排序）\nWarning: Because the excel workbook has existed, new sheets are appended to the last of the original sheet list. This may result in the disarrangement of worksheet order. Do you want to sort the sheets? (Input anything to sort the sheets, or null to skip sorting)")
        sort = bool(input())
        if sort:
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
                    sheetname_platform_list = list(map(lambda x: x.split("_")[1], sheetnames)) #从工作表名称提取大区信息形成列表（Extract the platformId from the sheetnames to form a list）
                    sheetname_tmpDf = pandas.DataFrame(data = [sheetnames, sheetname_date_list, sheetname_type_list, sheetname_platform_list]).stack().unstack(0) #创建一个四列数据框，各列分别是完整工作表名、日期信息、数据类型信息和大区信息（Create a 4-column dataframe whose columns are the complete sheetname, date, data type and platformId）
                    sheetnames_sorted = sheetname_tmpDf.sort_values(by = [1, 2, 3], ascending = [True, False, True]).iloc[:, 0].tolist() #将工作表名按照第一关键字——日期信息正序排列，第二关键字——数据类型信息倒序排列（先商品后藏品），第三关键字——大区信息正序排列（Order the sheetnames according to the ascending order of the first keyword - date, the descending order of the second keyword - data type and the ascending order of the third keyword - platformId）
                else:
                    sheets_Store = [sheet_iter for sheet_iter in sheetnames if sheet_iter.startswith("Store") or sheet_iter.startswith("Catalog")] #提取商品类型的工作表名称（Extract the names of the sheets containing Store data）
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
                wb.save(os.path.join(folder, excel_name_sorted))
                print('排序完成！排好序的工作簿已保存为“%s”。请按任意键退出。\nOrdering finished! The ordered workbook is saved as "%s". Press any key to exit ...\n' %(excel_name_sorted, excel_name_sorted))
                input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await fetch_store(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
