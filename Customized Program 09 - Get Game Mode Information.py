from lcu_driver import Connector
from wcwidth import wcswidth
import os, pandas, time, unicodedata, shutil

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
# 数据框格式化输出（Format print dataframes）
#-----------------------------------------------------------------------------
def count_nonASCII(s: str): #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def format_df(df: pandas.DataFrame): #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
    df = df.reset_index(drop = True) #这一步至关重要，因为下面的操作前提是行号是默认的（This step is crucial, for the following operations are based on the dataframe with the default row index）
    maxLens = {}
    maxWidth = shutil.get_terminal_size()[0]
    fields = df.columns.tolist()
    for field in fields:
        maxLens[field] = max(max(map(lambda x: wcswidth(str(x)), df[field])), wcswidth(str(field))) + 2
    if sum(maxLens.values()) + 2 * (len(fields) - 1) > maxWidth:
        print("单行数据字符串输出宽度超过当前终端窗口宽度！是否继续？（输入任意键继续，否则直接打印该数据框。）\nThe output width of each record string exceeds the current width of the terminal window! Continue? (Input anything to continue, or null to directly print this dataframe.)")
        if input() == "":
            #print(df)
            result = str(df)
            return (result, maxLens)
    result = ""
    for i in range(df.shape[1]):
        field = fields[i]
        tmp = "{0:^{w}}".format(field, w = maxLens[str(field)] - count_nonASCII(str(field)))
        result += tmp
        #print(tmp, end = "")
        if i != df.shape[1] - 1:
            result += "  "
            #print("  ", end = "")
    result += "\n"
    #print()
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            field = fields[j]
            cell = df[field][i]
            tmp = "{0:^{w}}".format(cell, w = maxLens[field] - count_nonASCII(str(cell)))
            result += tmp
            #print(tmp, end = "")
            if j != df.shape[1] - 1:
                result += "  "
                #print("  ", end = "")
        if i != df.shape[0] - 1:
            result += "\n"
        #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the last line）
    return (result, maxLens)

#-----------------------------------------------------------------------------
# 梳理可用队列（Sorts out available queues）
#-----------------------------------------------------------------------------
async def check_available_queue(connection):
    queues = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    map_CN = {8: "水晶之痕", 10: "扭曲丛林", 11: "召唤师峡谷", 12: "嚎哭深渊", 14: "屠夫之桥", 16: "宇宙遗迹", 18: "瓦罗兰城市公园", 19: "第43区", 20: "失控地点", 21: "百合与莲花的神庙", 22: "聚点危机", 30: "怒火角斗场"}
    map_EN = {8: "Crystal Scar", 10: "Twisted Treeline", 11: "Summoner's Rift", 12: "Howling Abyss", 14: "Butcher's Bridge", 16: "Cosmic Ruins", 18: "Valoran City Park", 19: "Substructure 43", 20: "Crash Site", 21: "Temple of Lily and Lotus", 22: "Convergence", 30: "Rings of Wrath"}
    pickmode_CN = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式", "": "待定"}
    pickmode_EN = {"AllRandomPickStrategy": "All Random", "SimulPickStrategy": "Blind Pick", "TeamBuilderDraftPickStrategy": "Draft Mode", "OneTeamVotePickStrategy": "Vote", "TournamentPickStrategy": "Tournament Draft", "": "Pending"}
    available_queues = {}
    for queue in queues:
        if queue["queueAvailability"] == "Available":
            available_queues[queue["id"]] = queue
    queue_dict = {"queueID": [], "mapID": [], "map_CN": [], "map_EN": [], "gameMode": [], "pickType_CN": [], "pickType_EN": []}
    for queue in available_queues.values():
        queue_dict["queueID"].append(queue["id"])
        queue_dict["mapID"].append(queue["mapId"])
        queue_dict["map_CN"].append(map_CN[queue["mapId"]])
        queue_dict["map_EN"].append(map_EN[queue["mapId"]])
        queue_dict["gameMode"].append(queue["name"])
        queue_dict["pickType_CN"].append(pickmode_CN[queue["gameTypeConfig"]["pickMode"]])
        queue_dict["pickType_EN"].append(pickmode_EN[queue["gameTypeConfig"]["pickMode"]])
    queue_df = pandas.DataFrame(queue_dict)
    queue_df.sort_values(by = "queueID", inplace = True, ascending = True, ignore_index = True)
    print("*****************************************************************************")
    print(format_df(queue_df)[0])
    print("*****************************************************************************")

#-----------------------------------------------------------------------------
# 获取游戏模式信息（Get game mode information）
#-----------------------------------------------------------------------------
def lcuTimestamp(timestamp): #根据队列开放和关闭时间戳返回对局时间（Return the time according to the timestamp of queue opening and closure）
    min = timestamp // 60
    sec = timestamp % 60
    return str(min) + ":" + "{0:0>2}".format(str(sec))

async def gamemode(connection):
    queues = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    # 以前含有"最大召唤师等级"参数（There was previously a parameter: maxLevel）
    queues_header = {"allowablePremadeSizes": "可用预组队规模", "areFreeChampionsAllowed": "允许使用周免英雄", "category": "对局类型", "championsRequiredToPlay": "需要英雄数量", "description": "游戏模式描述", "detailedDescription": "补充描述", "gameMode": "游戏模式", "id": "队列序号", "isRanked": "排位赛", "isTeamBuilderManaged": "服从阵营式管理", "lastToggledOffTime": "上次关闭时间", "lastToggledOnTime": "上次开放时间", "mapId": "地图序号", "maxDivisionForPremadeSize2": "双排最高分级限制", "maxTierForPremadeSize2": "双排最高段位限制", "maximumParticipantListSize": "最大玩家数量", "minLevel": "最低召唤师等级", "minimumParticipantListSize": "最小玩家数量", "name": "游戏模式名称", "numPlayersPerTeam": "队伍规模", "queueAvailability": "队列可用性", "removalFromGameAllowed": "允许退出游戏", "removalFromGameDelayMinutes": "允许退出游戏时间（分钟）", "shortName": "游戏模式简称", "showPositionSelector": "呈现位置指示器", "showQuickPlaySlotSelection": "呈现快速匹配偏好英雄选择界面", "showPreferredChampions": "呈现推荐英雄", "spectatorEnabled": "允许观战", "type": "游戏类型", "advancedLearningQuests": "进阶教程", "allowTrades": "允许购物", "banMode": "禁用模式", "banTimerDuration": "禁用时间限制（秒）", "battleBoost": "战斗加成", "crossTeamChampionPool": "跨队伍英雄共享", "deathMatch": "团体竞赛", "doNotRemove": "禁止退出游戏", "duplicatePick": "克隆选择", "exclusivePick": "允许声明想玩的英雄", "gameModeOverride": "游戏类型重写来源", "typeId": "游戏类型序号", "learningQuests": "进阶教程", "mainPickTimerDuration": "盲选时间限制（秒）", "maxAllowableBans": "最大禁用数量", "typeName": "英雄选择策略", "numPlayersPerTeamOverride": "队伍规模重写历史", "onboardCoopBeginner": "初期电脑玩家延迟上线", "pickMode": "英雄选择模式", "postPickTimerDuration": "符文和皮肤选择时间限制（秒）", "reroll": "允许重随", "teamChampionPool": "队伍英雄共享", "isChampionPointsEnabled": "队列奖励：英雄成就点数", "isIpEnabled": "队列奖励：成就", "isXpEnabled": "队列奖励：经验点数", "partySizeIpRewards": "组队额外成就奖励"}
    queues_data = {}
    queues_header_keys = list(queues_header.keys())
    # 下面定义的字典对导出的Excel结果进行优化（The following defined dictionaries optimizes the results in Excel）
    category = {"PvP": "玩家对战", "VersusAi": "人机对战"}
    queueAvailability = {"PlatformDisabled": "", "Available": "√"}
    banMode = {"SkipBanStrategy": "无", "StandardBanStrategy": "经典策略", "": "待定"}
    pickMode = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式", "": "待定"}
    maxTierForPremadeSize2 = {"": "", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    for i in range(len(queues_header)):
        key = queues_header_keys[i]
        queues_data[key] = []
        if i <= 28:
            if i in {2, 14, 20}: #主要优化这三项的结果显示（These 3 results are mainly optimized）
                for j in range(len(queues)):
                    queues_data[key].append(eval(queues_header_keys[i])[queues[j][key]])
            elif i == 10 or i == 11: #queues_header_keys[7] = "lastToggledOffTime"；header_keys[8] = "lastToggledOnTime"
                for j in range(len(queues)):
                    t = time.localtime(queues[j][key] / 1000)
                    standard_time = time.strftime("%Y年%m月%d日%H:%M:%S", t)
                    queues_data[key].append(standard_time)
            elif i != 26: #在一次更新中删除了showPreferredChampions接口（An update deletes the api for showPreferredChampions）
                for j in range(len(queues)):
                    queues_data[key].append(queues[j][key])
        elif i <= 50:
            if i in {31, 47}:
                for j in range(len(queues)):
                    queues_data[key].append(eval(queues_header_keys[i])[queues[j]["gameTypeConfig"][key]])
            elif i == 40:
                for j in range(len(queues)):
                    queues_data[key].append(queues[j]["gameTypeConfig"]["id"])
            elif i == 44:
                for j in range(len(queues)):
                    queues_data[key].append(queues[j]["gameTypeConfig"]["name"])
            else:
                for j in range(len(queues)):
                    queues_data[key].append(queues[j]["gameTypeConfig"][key])
        else:
            for j in range(len(queues)):
                queues_data[key].append(queues[j]["queueRewards"][key])
    #queues_display_order = range(len(queues_header))
    queues_display_order = [7, 20, 6, 18, 40, 12, 2, 28, 0, 8, 31, 44, 47, 11, 10, 19, 14, 13, 3, 17, 15, 16, 43, 24, 25, 38, 49, 33, 37, 1, 34, 50, 32, 42, 48, 21, 22, 27, 29, 41, 30, 36, 46, 51, 52, 53]
    queues_data_organized = {}
    sort_index = [i for i, v in sorted(enumerate(queues_data["id"]), key = lambda x: x[1])] # 此处指定按照队列序号排序（Here the DataFrame is sorted by queueId）
    for i in queues_display_order:
        key = queues_header_keys[i]
        queues_data_organized[key] = [queues_header[key]]
        for j in sort_index:
            queues_data_organized[key].append(queues_data[key][j])
    queues_df = pandas.DataFrame(data = queues_data_organized)
    for i in range(queues_df.shape[0]): #这里直接使用replace函数会把整数类型的0和1当成逻辑值替换（Here function "replace" will unexpectedly take effects on 0s and 1s of integer type）
        for j in range(queues_df.shape[1]):
            if str(queues_df.iat[i, j]) == "True":
                queues_df.iat[i, j] = "√"
            elif str(queues_df.iat[i, j]) == "False":
                queues_df.iat[i, j] = ""

    #下面设置覆盖写时添加的Sheet名称（The code here sets the Sheet name to be appended into the xlsx file with the same name）
    riot_client_info = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region = client_info["--region"]
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    #locale = await (await connection.request("GET", "/riotclient/get_region_locale")).json()
    locale = client_info["--locale"]
    version = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    version_df = pandas.DataFrame({"Patch": [version]})

    try:
        with pandas.ExcelWriter(path = "游戏队列信息.xlsx", mode = "a", if_sheet_exists = "overlay") as writer:
            currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
            queues_df.to_excel(excel_writer = writer, sheet_name = currentTime + " " + platformId + " " + locale)
            version_df.to_excel(excel_writer = writer, sheet_name = currentTime + " " + platformId + " " + locale, header = None, index = False, startcol = 0, startrow = 0)
    except FileNotFoundError: #第一次使用本程序追加写文件时，目录内不包含该文件，程序会报错（The program encounters an error when first writing to a folder without the wanted xlsx file under the appending mode）
        with pandas.ExcelWriter(path = "游戏队列信息.xlsx") as writer:
            currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
            queues_df.to_excel(excel_writer = writer, sheet_name = currentTime + " " + platformId + " " + locale)
            version_df.to_excel(excel_writer = writer, sheet_name = currentTime + " " + platformId + " " + locale, header = None, index = False, startcol = 0, startrow = 0)
    #要完整读取游戏队列信息，请使用命令（To read in the queue information entirely, it's highly recommended that user use the following command）：df = pandas.read_excel("游戏队列信息.xlsx", header = 0, index_col = 0)

async def print_available_queue(connection):
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    game_version = await (await connection.request("GET", "/lol-patch/v1/game-version")).json()
    print("是否检查可用队列？（输入任意键检查，否则退出程序）\nDo you want to check available queues? (Submit anything to check, or null to exit the program)")
    check = input()
    if check != "":
        while True:
            await check_available_queue(connection)
            print("(" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\t" + platformId + "\t" + game_version + ")")
            print("是否刷新可用队列信息？（输入任意键不刷新，否则刷新）\nRefresh available queue information? (Submit anything to quit refreshing, or null to continue refreshing)")
            refresh = input()
            if refresh != "":
                break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    print("是否导出游戏队列数据？（输入任意键不导出，否则导出）\nExport queue data? (Enter anything to refuse exporting, or null to export)")
    export = input()
    if export == "":
        await gamemode(connection)
    await print_available_queue(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
