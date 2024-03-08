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

async def fetch_store(connection):
    #获取大区信息，用于设置工作簿保存位置和工作表名称和获取相应的CommunityDragon数据资源（Get server information to set up workbook saving directory and sheet name and fetch the adaptive CommunityDragon data resources）
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
            if i == 2:
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
                collection_data[key].append(collection_hashtable.get(item["uuid"], ""))
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
