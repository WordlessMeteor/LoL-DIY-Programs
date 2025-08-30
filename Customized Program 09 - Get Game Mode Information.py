from lcu_driver import Connector
from wcwidth import wcswidth
import os, pandas, time, unicodedata, shutil

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/08/28
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
# 数据框格式化输出（Format print dataframes）
#-----------------------------------------------------------------------------
def count_nonASCII(s: str): #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str): #移除一个字符串中的所有C0和C1字符（Remove all C0 and C1 characters from a string）
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc")

def format_df(df: pandas.DataFrame, width_exceed_ask: bool = True, direct_print: bool = False, print_header: bool = True, print_index: bool = False, reserve_index = False, start_index = 0, header_align: str = "^", align: str = "^", align_replicate_rule: str = "all"): #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
    df = df.copy(deep = True)
    old_index = df.index
    df.index = range(start_index, len(df) + start_index)
    maxLens = {}
    maxWidth = shutil.get_terminal_size()[0]
    fields = df.columns.tolist()
    for field in fields:
        maxLens[field] = max(0 if len(df) == 0 else max(map(lambda x: wcswidth(rm_ctrl_char(str(x))), df[field])), wcswidth(rm_ctrl_char(field))) + 2
    index_len = 0 if len(df) == 0 else max(map(lambda x: len(str(x)), old_index)) if reserve_index else max(len(str(start_index)), len(str(start_index + len(df) - 1)))
    if sum(maxLens.values()) + 2 * (len(fields) - 1) > maxWidth or print_index and index_len + sum(maxLens.values()) + 2 * len(fields) > maxWidth:
        if width_exceed_ask:
            print("单行数据字符串输出宽度超过当前终端窗口宽度！是否继续？（输入任意键继续，否则直接打印该数据框。）\nThe output width of each record string exceeds the current width of the terminal window! Continue? (Input anything to continue, or null to directly print this dataframe.)")
            if not bool(input()):
                #print(df)
                result = str(df)
                return (result, maxLens)
        elif direct_print:
            print("单行数据字符串输出宽度超过当前终端窗口宽度！将直接打印该数据框！\nThe output width of each record string exceeds the current width of the terminal window! The program is going to directly print this dataframe!")
            result = str(df)
            return (result, maxLens)
        else:
            print("单行数据字符串输出宽度超过当前终端窗口宽度！将继续格式化输出！\nThe output width of each record string exceeds the current width of the terminal window! The program is going on formatted printing!")
    result = ""
    #确定各列的排列方向（Determine the alignments of all columns）
    if isinstance(header_align, str) and isinstance(align, str):
        if not all(map(lambda x: x in {"<", "^", ">"}, header_align)) or not all(map(lambda x: x in {"<", "^", ">"}, align)):
            print('排列方式字符串参数错误！排列方式必须是“<”“^”或者“>”中的一个。请修改排列方式字符串参数。\nParameter ERROR of the alignment string! The alignment value must be one of {"<", "^", ">"}. Please change the alignment string parameter.')
        if len(header_align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            header_alignments = ["^"] * df.shape[1]
        elif len(header_align) == 1:
            header_alignments = [header_align] * df.shape[1]
        else:
            header_alignments_tmp = list(header_align)
            if len(header_align) < df.shape[1]:
                if align_replicate_rule == "last":
                    header_alignments = header_alignments_tmp + [header_alignments_tmp[-1]] * len(df.shape[1] - len(header_align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    header_alignments = header_alignments_tmp * (df.shape[1] // len(header_align)) + header_alignments_tmp[:df.shape[1] % len(header_align)]
            else:
                header_alignments = header_alignments_tmp[:df.shape[1]]
        if len(align) == 0:
            alignments = ["^"] * df.shape[1]
        elif len(align) == 1:
            alignments = [align] * df.shape[1]
        else:
            alignments_tmp = list(align)
            if len(align) < df.shape[1]:
                if align_replicate_rule == "last":
                    alignments = alignments_tmp + [alignments_tmp[-1]] * len(df.shape[1] - len(align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    alignments = alignments_tmp * (df.shape[1] // len(align)) + alignments_tmp[:df.shape[1] % len(align)]
            else:
                alignments = alignments_tmp[:df.shape[1]]
        if print_header:
            if print_index:
                result += " " * (index_len + 2)
            for i in range(df.shape[1]):
                field = fields[i]
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(field), align = header_alignments[i], w = maxLens[field] - count_nonASCII(field))
                result += tmp
                #print(tmp, end = "")
                if i != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            result += "\n"
            #print()
        index = start_index
        for i in range(df.shape[0]):
            if print_index:
                result += "{0:>{w}}".format(old_index[index - start_index] if reserve_index else index, w = index_len) + "  "
            for j in range(df.shape[1]):
                field = fields[j]
                cell = str(list(df[field])[i])
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(cell), align = alignments[j], w = maxLens[field] - count_nonASCII(cell))
                result += tmp
                #print(tmp, end = "")
                if j != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            if i != df.shape[0] - 1:
                result += "\n"
            #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the last line）
            index += 1
    else:
        print("排列方式参数错误！请传入字符串。\nAlignment parameter ERROR! Please pass a string instead.")
    return (result, maxLens)

#-----------------------------------------------------------------------------
# 梳理可用队列（Sorts out available queues）
#-----------------------------------------------------------------------------
async def check_available_queue(connection):
    queues = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    map_CN = {8: "水晶之痕", 10: "扭曲丛林", 11: "召唤师峡谷", 12: "嚎哭深渊", 14: "屠夫之桥", 16: "星界废墟", 18: "瓦洛兰城市公园", 19: "第43区", 20: "飞船坠落点", 21: "百合与莲花的神庙", 22: "聚点危机", 30: "怒火角斗场", 33: "最终都市", 35: "班德尔之森"}
    map_EN = {8: "Crystal Scar", 10: "Twisted Treeline", 11: "Summoner's Rift", 12: "Howling Abyss", 14: "Butcher's Bridge", 16: "Cosmic Ruins", 18: "Valoran City Park", 19: "Substructure 43", 20: "Crash Site", 21: "Temple of Lily and Lotus", 22: "Convergence", 30: "Rings of Wrath", 33: "Final City", 35: "The Bandlewood"}
    pickmode_CN = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式", "QuickplayPickStrategy": "快速匹配", "": "待定"}
    pickmode_EN = {"AllRandomPickStrategy": "All Random", "SimulPickStrategy": "Blind Pick", "TeamBuilderDraftPickStrategy": "Draft Mode", "OneTeamVotePickStrategy": "Vote", "TournamentPickStrategy": "Tournament Draft", "QuickplayPickStrategy": "Quickplay", "": "Pending"}
    available_queues = {}
    for queue in queues:
        if queue["queueAvailability"] == "Available" or queue["id"] in platform_config["ClientSystemStates"]["enabledQueueIdsList"]:
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
    queues_header = {"allowablePremadeSizes": "可用预组队规模", "areFreeChampionsAllowed": "允许使用周免英雄", "assetMutator": "游戏模式配置", "category": "对局类型", "championsRequiredToPlay": "需要英雄数量", "description": "游戏模式描述", "detailedDescription": "补充描述", "gameMode": "游戏模式", "gameSelectCategory": "游戏选择类别", "gameSelectModeGroup": "游戏模式分组", "gameSelectPriority": "游戏选择优先级", "hidePlayerPosition": "隐藏玩家位置", "id": "队列序号", "isBotHonoringAllowed": "允许赞誉电脑玩家", "isCustom": "自定义对局", "isRanked": "排位赛", "isSkillTreeQueue": "技巧加成队列", "isTeamBuilderManaged": "服从阵容匹配机制", "isVisible": "客户端可见性", "lastToggledOffTime": "上次关闭时间戳", "lastToggledOnTime": "上次开放时间戳", "mapId": "地图序号", "maxDivisionForPremadeSize2": "双排最高分级限制", "maxLobbySpectatorCount": "房间最大观战者数量", "maxTierForPremadeSize2": "双排最高段位限制", "maximumParticipantListSize": "最大玩家数量", "minLevel": "最低召唤师等级", "minimumParticipantListSize": "最小玩家数量", "name": "游戏模式名称", "numPlayersPerTeam": "队伍规模", "numberOfTeamsInLobby": "房间内队伍数量", "queueAvailability": "队列可用性", "removalFromGameAllowed": "允许退出游戏", "removalFromGameDelayMinutes": "允许退出游戏时间（分钟）", "shortName": "游戏模式简称", "showPositionSelector": "呈现位置指示器", "showQuickPlaySlotSelection": "呈现快速模式偏好英雄选择界面", "spectatorEnabled": "允许观战", "type": "游戏类型", "lastToggledOffDate": "上次关闭时间", "lastToggledOnDate": "上次开放时间", "advancedLearningQuests": "进阶教程", "allowTrades": "允许交换", "banMode": "禁用模式", "banTimerDuration": "禁用时间限制（秒）", "battleBoost": "战斗加成", "crossTeamChampionPool": "跨队伍英雄共享", "deathMatch": "团体竞赛", "doNotRemove": "禁止退出游戏", "duplicatePick": "克隆选择", "exclusivePick": "唯一选择", "gameModeOverride": "游戏类型重写来源", "typeId": "游戏类型序号", "learningQuests": "新手教程", "mainPickTimerDuration": "盲选时间限制（秒）", "maxAllowableBans": "最大禁用数量", "typeName": "英雄选择策略", "numPlayersPerTeamOverride": "队伍规模重写历史", "onboardCoopBeginner": "人机对战引导模式", "pickMode": "英雄选择模式", "postPickTimerDuration": "符文和皮肤选择时间限制（秒）", "reroll": "允许重随", "teamChampionPool": "队伍英雄共享", "isChampionPointsEnabled": "队列奖励：英雄成就点数", "isIpEnabled": "队列奖励：成就", "isXpEnabled": "队列奖励：经验点数", "partySizeIpRewards": "组队额外成就奖励"}
    queues_data = {}
    queues_header_keys = list(queues_header.keys())
    # 下面定义的字典对导出的Excel结果进行优化（The following defined dictionaries optimizes the results in Excel）
    categories = {"Custom": "自定义对局", "PvP": "玩家对战", "VersusAi": "人机对战"}
    gameSelectCategories = {"": "待定", "CreateCustom": "创建自定义对局", "JoinCustom": "加入自定义对局", "kPvP": "玩家对战", "kTraining": "训练", "kVersusAI": "人机对战"}
    gameSelectModeGroups = {"": "待定", "kARAM": "极地大乱斗", "kAlternativeLeagueGameModes": "轮换模式", "kSummonersRift": "召唤师峡谷", "kTeamfightTactics": "云顶之弈"}
    queueAvailability_dict = {"Available": "√", "PlatformDisabled": ""}
    banModes = {"": "待定", "SkipBanStrategy": "无", "StandardBanStrategy": "经典策略", "TournamentBanStrategy": "竞技策略"}
    pickModes = {"": "待定", "AllRandomPickStrategy": "全随机模式", "AllTeamVotePickStrategy": "全队投票", "CounterDraftPickStrategy": "互选模式", "DraftModeSinglePickStrategy": "传统征召模式", "OneTeamVotePickStrategy": "单队投票", "QuickplayPickStrategy": "快速匹配", "SimulPickStrategy": "自选模式", "SkipPickStrategy": "跳过英雄选择", "TeamBuilderDraftPickStrategy": "征召模式", "TournamentPickStrategy": "竞技征召模式"}
    tiers = {"": "", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    for i in range(len(queues_header)):
        key = queues_header_keys[i]
        queues_data[key] = []
    for queue in queues:
        for i in range(len(queues_header_keys)):
            key = queues_header_keys[i]
            if i <= 40:
                if i == 3: #对局类型（`category`）
                    queues_data[key].append(categories[queue[key]])
                elif i == 8: #游戏选择类别（`gameSelectCategory`）
                    queues_data[key].append(gameSelectCategories[queue[key]])
                elif i == 9: #游戏模式分组（`gameSelectModeGroup`）
                    queues_data[key].append(gameSelectModeGroups[queue[key]])
                elif i == 24: #双排最高段位限制（`maxTierForPremadeSize2`）
                    queues_data[key].append(tiers[queue[key]])
                elif i == 31: #队列可用性（`queueAvailability`）
                    queues_data[key].append(queueAvailability_dict[queue[key]])
                elif i == 39 or i == 40: #上次关闭时间和上次开放时间（`lastToggledOffDate` and `lastToggledOnDate`）
                    subkey = "lastToggledOffTime" if i == 39 else "lastToggledOnTime"
                    standard_time = time.strftime("%Y年%m月%d日%H:%M:%S", time.localtime(queue[subkey] / 1000))
                    queues_data[key].append(standard_time)
                else:
                    queues_data[key].append(queue[key])
            elif i <= 62:
                if i == 43: #禁用模式（`banMode`）
                    queues_data[key].append(banModes[queue["gameTypeConfig"][key]])
                elif i == 52: #游戏类型序号（`typeId`）
                    queues_data[key].append(queue["gameTypeConfig"]["id"])
                elif i == 56: #英雄选择策略（`typeName`）
                    queues_data[key].append(queue["gameTypeConfig"]["name"])
                elif i == 59: #英雄选择模式（`pickMode`）
                    queues_data[key].append(pickModes[queue["gameTypeConfig"][key]])
                else:
                    queues_data[key].append(queue["gameTypeConfig"][key])
            else:
                queues_data[key].append(queue["queueRewards"][key])
    queues_output_order = [12, 31, 18, 7, 28, 5, 6, 21, 52, 3, 38, 2, 8, 9, 10, 0, 56, 14, 15, 16, 43, 59, 39, 40, 29, 24, 22, 26, 4, 30, 27, 25, 55, 37, 23, 35, 36, 17, 50, 61, 45, 49, 1, 62, 46, 11, 44, 54, 60, 32, 33, 48, 53, 41, 42, 58, 47, 63, 64, 65, 13]
    queues_data_organized = {}
    sort_index = [i for i, v in sorted(enumerate(queues_data["id"]), key = lambda x: x[1])] # 此处指定按照队列序号排序（Here the DataFrame is sorted by queueId）
    for i in queues_output_order:
        key = queues_header_keys[i]
        queues_data_organized[key] = []
        for j in sort_index:
            queues_data_organized[key].append(queues_data[key][j])
    queues_df = pandas.DataFrame(data = queues_data_organized)
    for column in queues_df:
        if queues_df[column].dtype == "bool":
            queues_df[column] = queues_df[column].astype(str)
            for i in range(len(queues_df)):
                queues_df.loc[i, column] = "√" if queues_df[column][i] == "True" else ""
    queues_df = pandas.concat([pandas.DataFrame([queues_header])[queues_df.columns], queues_df], ignore_index = True)

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
    #locale = await (await connection.request("GET", "/riotclient/region-locale")).json()
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
    check = bool(input())
    if check:
        while True:
            await check_available_queue(connection)
            print("(" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\t" + platformId + "\t" + game_version + ")")
            print("是否刷新可用队列信息？（输入任意键不刷新，否则刷新）\nRefresh available queue information? (Submit anything to quit refreshing, or null to continue refreshing)")
            refresh = bool(input())
            if refresh:
                break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    print("是否导出游戏队列数据？（输入任意键不导出，否则导出）\nExport queue data? (Enter anything to refuse exporting, or null to export)")
    export = input()
    if export == "":
        await gamemode(connection)
    await print_available_queue(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
