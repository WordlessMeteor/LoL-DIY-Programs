from lcu_driver import Connector
import os, pandas, time

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
# 获取游戏模式信息（Get game mode information）
#-----------------------------------------------------------------------------
def lcuTimestamp(timestamp): #根据队列开放和关闭时间戳返回对局时间（Return the time according to the timestamp of queue opening and closure）
    min = timestamp // 60
    sec = timestamp % 60
    return str(min) + ":" + "{0:0>2}".format(str(sec))

async def gamemode(connection):
    queues = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    # 以前含有"最大召唤师等级"参数（There was previously a parameter: maxLevel）
    queues_header = {"allowablePremadeSizes": "可用预组队规模", "areFreeChampionsAllowed": "允许使用周免英雄", "category": "对局类型", "championsRequiredToPlay": "需要英雄数量", "gameMode": "游戏模式", "id": "队列序号", "isRanked": "排位赛", "lastToggledOffTime": "上次关闭时间", "lastToggledOnTime": "上次开放时间", "mapId": "地图序号", "maxDivisionForPremadeSize2": "双排最高分级限制", "maxTierForPremadeSize2": "双排最高段位限制", "maximumParticipantListSize": "最大玩家数量", "minLevel": "最低召唤师等级", "minimumParticipantListSize": "最小玩家数量", "name": "游戏模式名称", "numPlayersPerTeam": "队伍规模", "queueAvailability": "队列可用性", "removalFromGameAllowed": "允许退出游戏", "removalFromGameDelayMinutes": "允许退出游戏时间（分钟）", "showPositionSelector": "呈现位置指示器", "showQuickPlaySlotSelection": "呈现快速匹配偏好英雄界面", "showPreferredChampions": "呈现推荐英雄", "spectatorEnabled": "允许观战", "type": "游戏类型", "advancedLearningQuests": "进阶教程", "allowTrades": "允许购物", "banMode": "禁用模式", "banTimerDuration": "禁用时间限制（秒）", "battleBoost": "战斗加成", "crossTeamChampionPool": "跨队伍英雄共享", "doNotRemove": "禁止退出游戏", "duplicatePick": "克隆选择", "exclusivePick": "允许声明想玩的英雄", "typeId": "游戏类型序号", "learningQuests": "进阶教程", "mainPickTimerDuration": "盲选时间限制（秒）", "maxAllowableBans": "最大禁用数量", "typeName": "英雄选择策略", "onboardCoopBeginner": "初期电脑玩家延迟上线", "pickMode": "英雄选择模式", "postPickTimerDuration": "符文和皮肤选择时间限制（秒）", "reroll": "允许重随", "teamChampionPool": "队伍英雄共享", "isChampionPointsEnabled": "队列奖励：英雄成就点数", "isIpEnabled": "队列奖励：成就", "isXpEnabled": "队列奖励：经验点数"}
    queues_data = {}
    queues_header_keys = list(queues_header.keys())
    # 下面定义的字典对导出的Excel结果进行优化（The following defined dictionaries optimizes the results in Excel）
    category = {"PvP": "玩家对战", "VersusAi": "人机对战"}
    queueAvailability = {"PlatformDisabled": "", "Available": "√"}
    banMode = {"SkipBanStrategy": "无", "StandardBanStrategy": "经典策略"}
    pickMode = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式"}
    maxTierForPremadeSize2 = {"": "", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    for i in range(len(queues_header)):
        key = queues_header_keys[i]
        queues_data[key] = []
        if i <= 24:
            if i in {2, 11, 17}: #主要优化这三项的结果显示（These 3 results are mainly optimized）
                for j in range(len(queues)):
                    queues_data[key].append(eval(queues_header_keys[i])[queues[j][key]])
            elif i == 7 or i == 8: #queues_header_keys[7] = "lastToggledOffTime"；header_keys[8] = "lastToggledOnTime"
                for j in range(len(queues)):
                    t = time.localtime(queues[j][key] / 1000)
                    standard_time = time.strftime("%Y年%m月%d日%H:%M:%S", t)
                    queues_data[key].append(standard_time)
            elif i != 22: #在一次更新中删除了showPreferredChampions接口（An update deletes the api for showPreferredChampions）
                for j in range(len(queues)):
                    queues_data[key].append(queues[j][key])
        elif i <= 43:
            if i in {27, 40}:
                for j in range(len(queues)):
                    queues_data[key].append(eval(queues_header_keys[i])[queues[j]["gameTypeConfig"][key]])
            elif i == 34:
                for j in range(len(queues)):
                    queues_data[key].append(queues[j]["gameTypeConfig"]["id"])
            elif i == 38:
                for j in range(len(queues)):
                    queues_data[key].append(queues[j]["gameTypeConfig"]["name"])
            else:
                for j in range(len(queues)):
                    queues_data[key].append(queues[j]["gameTypeConfig"][key])
        else:
            for j in range(len(queues)):
                queues_data[key].append(queues[j]["queueRewards"][key])
    #queues_display_order = range(len(queues_header))
    queues_display_order = [5, 17, 4, 15, 34, 9, 2, 24, 0, 6, 27, 38, 40, 8, 7, 16, 11, 10, 3, 14, 12, 13, 37, 20, 21, 33, 42, 29, 32, 1, 30, 43, 28, 36, 41, 18, 19, 23, 25, 35, 26, 31, 39, 44, 45, 46]
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

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await gamemode(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
