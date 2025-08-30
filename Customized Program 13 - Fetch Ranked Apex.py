from lcu_driver import Connector
from openpyxl import load_workbook
import json, os, pandas, time, _io
from urllib.parse import quote, unquote

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/07/31
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

log_folder = "日志（Logs）/Customized Program 13 - Fetch Ranked Apex"
os.makedirs(log_folder, exist_ok = True)
currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
log = open(os.path.join(log_folder, currentTime + ".log"), "a+", encoding = "utf-8")

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
#  获取最强王者段位信息（Get challenger tier league information）
#-----------------------------------------------------------------------------
def logInput(prompt: str = "", log: _io.TextIOWrapper = log, write_time: bool = True):
    s = input(prompt)
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
            log.write("[%s]%s\n" %(currentTime, prompt + s))
        else:
            log.write(prompt + s + "\n")
    return s

def logPrint(s: str = "", log: _io.TextIOWrapper = log, end: str = "\n", print_time: bool = False, write_time: bool = True):
    currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    if print_time:
        print("[%s]%s" %(currentTime, s), end = end, flush = end == "\r")
    else:
        print(s, end = end, flush = end == "\r")
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            log.write("[%s]%s%s" %(currentTime, str(s), "\n" if end == "\r" else end))
        else:
            log.write("%s%s" %(str(s), "\n" if end == "\r" else end))

def format_runtime(seconds: int):
    units = [(" d", 86400), (" h", 3600), (" m", 60), (" s", 1)]
    result = []
    for unit_name, unit_seconds in units:
        if seconds >= unit_seconds:
            unit_value = round(seconds // unit_seconds)
            seconds %= unit_seconds
            result.append(f"{unit_value}{unit_name}")
    
    return " ".join(result) if result else "0"

async def get_info(connection, name: str, searchType: str | int = "riotId"):
    #searchTypes = {0: "selfCheck", 1: "riotId", 2: "puuid", 3: "summonerId"}
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    result = {"searchType": "riotId", "endpoint": "/lol-summoner/v2/summoners/puuid/{puuid}", "info_got": False, "network_error": False, "body": {}, "message": "", "selfInfo": False}
    try:
        name = int(name)
    except ValueError:
        if name == "current-summoner":
            result = {"searchType": "selfCheck", "endpoint": "/lol-summoner/v1/current-summoner", "info_got": True, "network_error": False, "body": current_info, "message": "", "selfInfo": True}
        elif name.count("-") == 4 and len(name.replace(" ", "")) > 22: #拳头规定的玩家昵称不超过16个字符，昵称编号不超过5个字符（Riot game name can't exceed 16 characters. The tagline can't exceed 5 characters）
            result["searchType"] = "puuid"
            result["endpoint"] = "/lol-summoner/v2/summoners/puuid/{puuid}"
            info = await (await connection.request("GET", f"/lol-summoner/v2/summoners/puuid/{name}")).json()
            result["body"] = info
            if "errorCode" in info:
                if info["httpStatus"] == 400:
                    result["message"] = "您输入的玩家通用唯一识别码格式有误！请重新输入！\nPUUID wasn't in UUID format! Please try again!"
                elif info["httpStatus"] == 404:
                    result["message"] = "未找到玩家通用唯一识别码为%s的玩家；请核对识别码并稍后再试。\nA player with puuid %s was not found; verify the puuid and try again." %(name, name)
                else:
                    result["network_error"] = True
                    result["message"] = "网络异常。\nNetwork Error."
            else:
                result["info_got"] = True
                result["selfInfo"] = info["puuid"] == current_info["puuid"]
        else:
            result["searchType"] = "riotId"
            result["endpoint"] = "/lol-summoner/v1/summoners?name={name}"
            if name.count("#") == 0:
                result["message"] = '召唤师名称已变更为拳头ID。请以“{玩家昵称}#{昵称编号}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"])
            elif name.count("#") > 1:
                result["message"] = "该玩家名字包含了无效字符。\nThis player name contains invalid characters."
            else:
                gameName, tagLine = name.split("#")
                if len(gameName) == 0:
                    result["message"] = "缺少玩家昵称。\nGame name is missing."
                elif len(tagLine) == 0:
                    result["message"] = "缺少昵称编号。\nTagline is missing."
                elif len(gameName) < 3:
                    result["message"] = "召唤师昵称过短。\nRiot ID is too short."
                elif len(gameName.replace(" ", "")) > 16:
                    result["message"] = "召唤师昵称过长。\nRiot ID is too long."
                else:
                    info = await (await connection.request("GET", "/lol-summoner/v1/summoners?name=" + quote(name))).json()
                    result["body"] = info
                    if "errorCode" in info:
                        if info["httpStatus"] == 404:
                            result["message"] = "未找到%s；请核对下名字并稍后再试。\n%s was not found; verify the name and try again." %(name, name)
                        else:
                            result["network_error"] = True
                            result["message"] = "网络异常。\nNetwork Error."
                    else:
                        result["info_got"] = True
                        result["selfInfo"] = info["puuid"] == current_info["puuid"]
    else:
        result["searchType"] = "summonerId"
        result["endpoint"] = "/lol-summoner/v1/summoners/{id}"
        info = await (await connection.request("GET", f"/lol-summoner/v1/summoners/{name}")).json()
        result["body"] = info
        if "errorCode" in info:
            if info["httpStatus"] == 400:
                if info["message"] == "Value %d for 'id' of type uint64 is out of range":
                    result["message"] = "您输入的召唤师序号格式有误！请重新输入！\nValue for 'id' of type uint64 is out of range! Please try again!"
                else:
                    result["message"] = "未找到召唤师序号为%s的玩家；请核对召唤师序号并稍后再试。\nA player with summonerId %s was not found; verify the summonerId and try again." %(name, name)
            elif info["httpStatus"] == 404:
                result["message"] = "未找到召唤师序号为%s的玩家；请核对召唤师序号并稍后再试。\nA player with summonerId %s was not found; verify the summonerId and try again." %(name, name)
            else:
                result["network_error"] = True
                result["message"] = "网络异常。\nNetwork Error."
        else:
            result["info_got"] = True
            result["selfInfo"] = info["puuid"] == current_info["puuid"]
    return result

async def get_challenger_tier(connection):
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    platform_TENCENT = {"BGP1": "全网通区 男爵领域（Baron Zone）", "BGP2": "峡谷之巅（Super Zone）", "EDU1": "教育网专区（CRENET Server）", "HN1": "电信一区 艾欧尼亚（Ionia）", "HN2": "电信二区 祖安（Zaun）", "HN3": "电信三区 诺克萨斯（Noxus 1）", "HN4": "电信四区 班德尔城（Bandle City）", "HN4_NEW": "电信四区 班德尔城（Bandle City）", "HN5": "电信五区 皮尔特沃夫（Piltover）", "HN6": "电信六区 战争学院（the Institute of War）", "HN7": "电信七区 巨神峰（Mount Targon）", "HN8": "电信八区 雷瑟守备（Noxus 2）", "HN9": "电信九区 裁决之地（the Proving Grounds）", "HN10": "电信十区 黑色玫瑰（the Black Rose）", "HN11": "电信十一区 暗影岛（Shadow Isles）", "HN12": "电信十二区 钢铁烈阳（the Iron Solari）", "HN13": "电信十三区 水晶之痕（Crystal Scar）", "HN14": "电信十四区 均衡教派（the Kinkou Order）", "HN15": "电信十五区 影流（the Shadow Order）", "HN16": "电信十六区 守望之海（Guardian's Sea）", "HN17": "电信十七区 征服之海（Conqueror's Sea）", "HN18": "电信十八区 卡拉曼达（Kalamanda）", "HN19": "电信十九区 皮城警备（Piltover Wardens）", "PBE": "体验服 试炼之地（Chinese PBE）", "WT1": "网通一区 比尔吉沃特（Bilgewater）", "WT1_NEW": "网通一区 比尔吉沃特（Bilgewater）", "WT2": "网通二区 德玛西亚（Demacia）", "WT2_NEW": "网通二区 德玛西亚（Demacia）", "WT3": "网通三区 弗雷尔卓德（Freljord）", "WT3_NEW": "网通三区 弗雷尔卓德（Freljord）", "WT4": "网通四区 无畏先锋（House Crownguard）", "WT4_NEW": "网通四区 无畏先锋（House Crownguard）", "WT5": "网通五区 恕瑞玛（Shurima）", "WT6": "网通六区 扭曲丛林（Twisted Treeline）", "WT7": "网通七区 巨龙之巢（the Dragon Camp）", "FORCES": "比赛服 艾欧尼亚（Tournament - Ionia）", "NJ100": "联盟一区", "GZ100": "联盟二区", "CQ100": "联盟三区", "TJ100": "联盟四区", "TJ101": "联盟五区", "PREPBE": "试炼之地 临时过渡服务器（Chinese PBE Temporary）"}
    platform_RIOT = {"ME1": "中东服（Middle East）", "BR1": "巴西服（Brazil）", "EUN1": "北欧和东欧服（Europe Nordic & East）", "EUW1": "西欧服（Europe West）", "JP1": "日服（Japan）", "KR": "韩服（Republic of Korea）", "LA1": "北拉美服（Latin America North）", "LA2": "南拉美服（Latin America South）", "NA1": "北美服（North America）", "OC1": "大洋洲服（Oceania）", "TR1": "土耳其服（Turkey）", "RU": "俄罗斯服（Russia）", "PH2": "菲律宾服（Philippines）", "SG2": "新加坡服（Singapore）", "TH2": "泰服（Thailand）", "TW2": "台服（Taiwan, Hong Kong and Macau）", "VN2": "越南服（Vietnam）", "PBE1": "测试服（Public Beta Environment）"}
    platform_GARENA = {"PH1": "菲律宾服（Philippines）", "SG1": "新加坡服（Singapore, Malaysia and Indonesia）", "TW1": "台服（Taiwan, Hong Kong and Macau）", "VN1": "越南服（Vietnam）", "TH1": "泰服（Thailand）"}
    platform = {"TENCENT": "国服（TENCENT）", "RIOT": "外服（RIOT）", "GARENA": "竞舞（GARENA）"}
    #下面设置输出文件的位置（The following code determines the output files' location）
    riot_client_info = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region = client_info["--region"]
    currentSeason = platform_config["ClientSystemStates"]["currentSeason"] #API中记录的赛季与平常所说的赛季有所不同（The season recorded in API is different from the often mentioned season）
    currentSplit = int(platform_config["LeagueConfig"]["CurrentSplit"]) + 1 #API中记录的赛段序号从0开始，平常所说的赛季序号从1开始，因此要加1（The split recorded in API counts from 0, while the split that people usually talk about counts from 1, so 1 should be added here）
    if region == "TENCENT":
        folder = "顶尖排位玩家（Ranked Apex）\\" + "国服（TENCENT）" + "\\" + platform_TENCENT[platformId] + "\\" + "第%d赛季 - 第%d赛段（SEASON %d - Split %d）" %(currentSeason, currentSplit, currentSeason, currentSplit)
    elif region == "GARENA":
        folder = "顶尖排位玩家（Ranked Apex）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[platformId] + "\\" + "第%d赛季 - 第%d赛段（SEASON %d - Split %d）" %(currentSeason, currentSplit, currentSeason, currentSplit)
    else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
        folder = "顶尖排位玩家（Ranked Apex）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[platformId] + "\\" + "第%d赛季 - 第%d赛段（SEASON %d - Split %d）" %(currentSeason, currentSplit, currentSeason, currentSplit)
    
    # splitsConfig = await (await connection.request("GET", "/lol-ranked/v1/splits-config")).json()
    # json1name = "SplitsConfig (Season %d).json" %currentSeason
    # while True:
    #     try:
    #         with open(os.path.join(folder, json1name), "w", encoding = "utf-8") as jsonfile1:
    #             json.dump(splitsConfig, jsonfile1, indent = 4, ensure_ascii = False)
    #     except FileNotFoundError:
    #         os.makedirs(folder, exist_ok = True)
    #     except UnicodeEncodeError:
    #         logPrint("\n赛季信息文本文档生成失败！请检查内容是否包含不常用字符！\nSplit config text generation failure! Please check if the content includes any abnormal characters!\n")
    #         break
    #     else:
    #         logPrint('\n赛季信息已保存为“%s”。\nSplit config is saved as "%s".\n' %(os.path.join(folder, json1name), os.path.join(folder, json1name)))
    #         break
    # splits_info_header = {"endTimeMillis": "赛段结束时间戳（毫秒）", "seasonId": "赛季序号", "splitId": "赛段序号", "startTimeMillis": "赛段开始时间戳（毫秒）", "endTime": "赛段结束时间", "startTime": "赛段开始时间", "victoriousSkinReward: itemInstanceId": "胜利系列皮肤奖励：物品识别码", "victoriousSkinRewardLevel: BRONZE": "英勇黄铜胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: CHALLENGER": "最强王者胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: DIAMOND": "璀璨钻石胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: EMERALD": "流光翡翠胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: GOLD": "荣耀黄金胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: GRANDMASTER": "傲世宗师胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: IRON": "坚韧黑铁胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: MASTER": "超凡大师胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: PLATINUM": "华贵铂金胜利系列皮肤所需赛段点数", "victoriousSkinRewardLevel: SILVER": "不屈白银胜利系列皮肤所需赛段点数"}
    # splits_info_header_keys = list(splits_info_header.keys())
    # splits_info_data = {}
    # for i in range(len(splits_info_header_keys)):
    #     key = splits_info_header_keys[i]
    #     splits_info_data[key] = []
    # for i in range(len(splitsConfig["splits"])):
    #     split = splitsConfig["splits"][i]
    #     for j in range(len(splits_info_header_keys)):
    #         key = splits_info_header_keys[j]
    #         if j <= 5:
    #             if j >= 4: #时间相关键（Time-related keys）
    #                 splits_info_data[key].append(time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime(split[key + "Millis"] // 1000)))
    #             else:
    #                 splits_info_data[key].append(split[key])
    #         elif j == 6: #胜利系列皮肤奖励：物品识别码（`victoriousSkinReward: itemInstanceId`）
    #             splits_info_data[key].append(split["victoriousSkinRewardGroup"]["itemInstanceId"])
    #         else:
    #             splits_info_data[key].append(split["victoriousSkinRewardGroup"]["splitPointsByHighestSeasonEndTier"][key[27:]] if key[27:] in split["victoriousSkinRewardGroup"]["splitPointsByHighestSeasonEndTier"] else 0)
    #     logPrint("赛季信息整理进度（Split config sorting process）：%d/%d" %(i + 1, len(splitsConfig["splits"])), end = "\r", print_time = True)
    # splits_info_statistics_output_order = [1, 2, 3, 5, 0, 4, 6, 13, 7, 16, 11, 15, 10, 9, 14, 12, 8]
    # splits_info_data_organized = {}
    # for i in splits_info_statistics_output_order:
    #     key = splits_info_header_keys[i]
    #     splits_info_data_organized[key] = splits_info_data[key]
    # splits_info_df = pandas.DataFrame(data = splits_info_data_organized)
    # splits_info_df = pandas.concat([pandas.DataFrame([splits_info_header])[splits_info_df.columns], splits_info_df], ignore_index = True)
    
    # rewardTrack_header = {"seasonId": "赛季序号", "rewardTrackId": "奖励顺序", "championId": "英雄序号", "description": "描述", "id": "奖励代码", "pointsRequired": "所需赛段点", "quantity": "数量", "regaliaLevel": "排位徽章等级", "rewardType": "奖品类型", "splitId": "发放赛段序号", "name": "奖品名称"}
    # rewardTrack_header_keys = list(rewardTrack_header.keys())
    # rewardTrack_data = {}
    # rewardTypes = {"CHAMPION_TOKEN": "成就代币", "EMOTE": "永久表情", "ETERNALS_CAPSULE": "永恒星碑魔法引擎", "HEXTECH_CHEST": "海克斯科技宝箱", "HEXTECH_KEY": "海克斯科技钥匙", "HEXTECH_KEY_FRAGMENT": "海克斯科技钥匙碎片", "MASTERWORK_CHEST": "杰作宝箱", "MYSTERY_EMOTE": "神秘表情", "ORANGE_ESSENCE": "橙色精萃", "SUMMONER_ICON": "召唤师图标", "WARD_SHARD": "守卫碎片"}
    # #下面整理奖品识别码和奖品名称的对应关系（The following code sorts out the relationship between the itemInstanceIds and the rewardNames）
    # rewardNames = {}
    # inventoryTypes = ["ACHIEVEMENT_BANNER_ACCENT", "ACHIEVEMENT_TITLE", "ANNOUNCER_PACK", "AUGMENT", "AUGMENT_SLOT", "BOOST", "BUNDLES", "CHAMPION", "CHAMPION_SKIN", "CHERRY_BOON", "COMPANION", "CURRENCY", "EMOTE", "EVENT_PASS", "FANPASS", "GIFT", "HEXTECH_CRAFTING", "MODE_PROGRESSION_REWARD", "MYSTERY", "NEXUS_FINISHER", "PREMIUM_CLUB_MEMBERSHIP", "PROVIEW_PASS", "PVE_RELIC", "PVE_SUMMONER_PACKAGE", "PVE_UPGRADE", "QUEUE_ENTRY", "REGALIA_BANNER", "REGALIA_BORDER", "REGALIA_CREST", "RP", "RUNE", "SKIN_AUGMENT", "SKIN_BORDER", "SKIN_UPGRADE_GEAR", "SKIN_UPGRADE_HOME_GUARD", "SKIN_UPGRADE_RECALL", "SKIN_UPGRADE_SPAWN", "SPELL_BOOK_PAGE", "STATSTONE", "STRAWBERRY_BOON", "STRAWBERRY_LOADOUT_ITEM", "STRAWBERRY_MAP", "SUMMONER_CUSTOMIZATION", "SUMMONER_ICON", "TEAMPASS", "TEAM_SKIN_PURCHASE", "TFT_DAMAGE_SKIN", "TFT_EVENT_SKILLS", "TFT_MAP_SKIN", "TFT_PLAYBOOK", "TFT_ZOOM_SKIN", "TOURNAMENT_FLAG", "TOURNAMENT_FRAME", "TOURNAMENT_LOGO", "TOURNAMENT_TROPHY", "TRANSFER", "WARD_SKIN"]
    # for inventoryType in inventoryTypes:
    #     items = await (await connection.request("GET", "/lol-catalog/v1/items/" + inventoryType)).json()
    #     rewardNames |= {item["itemInstanceId"]: item["name"] for item in items}
    # for i in range(len(rewardTrack_header_keys)):
    #     key = rewardTrack_header_keys[i]
    #     rewardTrack_data[key] = []
    # for i in range(len(splitsConfig["splits"])):
    #     split = splitsConfig["splits"][i]
    #     for j in range(len(split["rewardTrack"])):
    #         rewards = split["rewardTrack"][j]["rewards"]
    #         for k in range(len(rewards)):
    #             reward = rewards[k]
    #             for l in range(len(rewardTrack_header_keys)):
    #                 key = rewardTrack_header_keys[l]
    #                 if l == 0: #赛季序号（`seasonId`）
    #                     rewardTrack_data[key].append(split["seasonId"])
    #                 elif l == 1: #奖励顺序（`rewardTrackId`）
    #                     rewardTrack_data[key].append(j)
    #                 else:
    #                     if l == 8: 奖品类型（`rewardType`）
    #                         rewardTrack_data[key].append(rewardTypes[reward["rewardType"]])
    #                     elif l == 10: #奖品名称（`name`）
    #                         rewardTrack_data[key].append(rewardNames.get(reward["id"], ""))
    #                     else:
    #                         rewardTrack_data[key].append(reward[key])
    #             logPrint("奖励里程整理进度（Reward track sorting process）：[%d/%d][%d/%d][%d/%d]" %(i + 1, len(splitsConfig["splits"]), j + 1, len(split["rewardTrack"]), k + 1, len(rewards)), end = "\r", print_time = True)
    # rewardTrack_statistics_output_order = [0, 9, 1, 10, 4, 8, 2, 6, 3, 5, 7]
    # rewardTrack_data_organized = {}
    # for i in rewardTrack_statistics_output_order:
    #     key = rewardTrack_header_keys[i]
    #     rewardTrack_data_organized[key] = rewardTrack_data[key]
    # rewardTrack_df = pandas.DataFrame(data = rewardTrack_data_organized)
    # rewardTrack_df = pandas.concat([pandas.DataFrame([rewardTrack_header])[rewardTrack_df.columns], rewardTrack_df], ignore_index = True)
    
    tiers_zh = {"": "", "NONE": "没有段位", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    tiers_en = {"": "", "NONE": "NONE", "IRON": "IRON", "BRONZE": "BRONZE", "SILVER": "SILVER", "GOLD": "GOLD", "PLATINUM": "PLATINUM", "EMERALD": "EMERALD", "DIAMOND": "DIAMOND", "MASTER": "MASTER", "GRANDMASTER": "GRANDMASTER", "CHALLENGER": "CHALLENGER"}
    ratedTiers_turbo = {"": "", "NONE": "没有段位", "GRAY": "灰白", "GREEN": "翠绿", "BLUE": "天蓝", "PURPLE": "绛紫", "ORANGE": "耀橙"}
    ratedTiers_cherry = {"": "", "NONE": "没有段位", "GRAY": "木木角斗士", "GREEN": "青铜角斗士", "BLUE": "白银角斗士", "PURPLE": "黄金角斗士", "ORANGE": "王者角斗士"}
    #ratedTiers = {"": "", "NONE": "NONE", "GRAY": "GRAY", "GREEN": "GREEN", "BLUE": "BLUE", "PURPLE": "PURPLE", "ORANGE": "ORANGE"}
    queueTypes_zh = {"RANKED_SOLO_5x5": "单人/双人", "RANKED_FLEX_SR": "灵活 5V5", "RANKED_TFT": "云顶之弈", "RANKED_TFT_PAIRS": "2V0", "RANKED_TFT_DOUBLE_UP": "双人作战", "RANKED_TFT_TURBO": "狂暴模式", "CHERRY": "斗魂竞技场"} #2V0模式仅美测服可用（RANKED_TFT_PAIRS is only available on PBE）
    queueTypes_en = {"RANKED_SOLO_5x5": "Ranked Solo/Duo", "RANKED_FLEX_SR": "Ranked Flex", "RANKED_TFT": "Ranked TFT", "RANKED_TFT_PAIRS": "2V0", "RANKED_TFT_DOUBLE_UP": "Double Up", "RANKED_TFT_TURBO": "Hyper Roll", "CHERRY": "Arena"}
    challenger_ladder_queueTypes = await (await connection.request("GET", "/lol-ranked/v1/challenger-ladders-enabled")).json()
    challenger_ladders_metadata_header = {"nextApexUpdateMillis": "下次天梯更新时间戳（毫秒）", "provisionalGameThreshold": "定位赛场次", "queueType": "队列类型", "requestedRankedEntry": "排位解锁条件", "nextApexUpdateTime": "下次天梯更新时间", "apexUnlockTimeMillis": "天梯解锁时间戳（毫秒）", "division": "段位分级", "maxLeagueSize": "段位容量", "minLpForApexTier": "上榜所需胜点", "tier": "段位", "topNumberOfPlayers": "上榜所需名次", "apexUnlockTime": "天梯解锁时间"}
    challenger_ladders_metadata_header_keys = list(challenger_ladders_metadata_header.keys())
    challenger_ladders_metadata = {}
    for i in range(len(challenger_ladders_metadata_header_keys)):
        key = challenger_ladders_metadata_header_keys[i]
        challenger_ladders_metadata[key] = []
    challenger_ladders_header = {"division": "当前分级", "earnedRegaliaRewardIds": "已获得的段位奖励物品序号", "isProvisional": "定位中", "leaguePoints": "胜点", "losses": "负场", "miniseriesResults": "晋升赛结果", "pendingDemotion": "即将降级", "pendingPromotion": "即将晋级", "position": "当前位次", "positionDelta": "位次变化", "previousPosition": "过往位次", "previousSeasonEndDivision": "过往赛季结束段位分级", "previousSeasonEndTier": "过往赛季结束段位", "provisionalGamesRemaining": "剩余定位场次", "puuid": "玩家通用唯一识别码", "rankedRegaliaLevel": "华甲等级", "summonerId": "召唤师序号", "summonerName": "召唤师名", "tier": "当前段位", "wins": "胜场", "gameName": "玩家昵称", "tagLine": "昵称编号"}
    challenger_ladders_header_keys = list(challenger_ladders_header.keys())
    ladders_data = {"challenger_ladder": {}, "topRated_ladder": {}}
    ladders_dfs = {"challenger_ladder": {}, "topRated_ladder": {}}
    for queueType in challenger_ladder_queueTypes:
        ladders_data["challenger_ladder"][queueType] = {}
        queue_ladder_data = ladders_data["challenger_ladder"][queueType] #注意字典赋值的原理（Pay attention to the principle of assigning a dictionary）
        for i in range(len(challenger_ladders_header_keys)):
            key = challenger_ladders_header_keys[i]
            queue_ladder_data[key] = []
        for tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
            ladders = await (await connection.request("GET", f"/lol-ranked/v1/apex-leagues/{queueType}/{tier}")).json()
            json2name = "Apex-%s-%s(%s).json" %(tier.capitalize(), queueType, runTime_day)
            while True:
                try:
                    with open(os.path.join(folder, json2name), "w", encoding = "utf-8") as jsonfile2:
                        json.dump(ladders, jsonfile2, indent = 4, ensure_ascii = False)
                except FileNotFoundError:
                    os.makedirs(folder, exist_ok = True)
                except UnicodeEncodeError:
                    logPrint("\n顶级%s%s玩家信息文本文档生成失败！请检查内容是否包含不常用字符！\nTop %s %s player information generation failure! Please check if the content includes any abnormal characters!\n" %(queueTypes_zh[queueType], tiers_zh[tier], queueTypes_en[queueType], tiers_en[tier]))
                    break
                else:
                    logPrint('\n顶级%s%s玩家信息已保存为“%s”。\nTop %s %s player information is saved as "%s".\n' %(queueTypes_zh[queueType], tiers_zh[tier], os.path.join(folder, json2name), queueTypes_en[queueType], tiers_en[tier], os.path.join(folder, json2name)))
                    break
            for i in range(len(ladders["divisions"])):
                division = ladders["divisions"][i]
                for j in range(len(challenger_ladders_metadata_header_keys)):
                    key = challenger_ladders_metadata_header_keys[j]
                    if j <= 4:
                        if j == 2: #队列类型（`queueType`）
                            challenger_ladders_metadata[key].append(queueTypes_zh[ladders[key]])
                        elif j == 4: #下次天梯更新时间（`nextApexUpdateTime`）
                            challenger_ladders_metadata[key].append(time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime(ladders["nextApexUpdateMillis"] // 1000)))
                        else:
                            challenger_ladders_metadata[key].append(ladders[key])
                    else:
                        if j == 6: #段位分级（`division`）
                            challenger_ladders_metadata[key].append("") if division[key] == "" else challenger_ladders_metadata[key].append(division[key])
                        elif j == 9: #段位（`tier`）
                            challenger_ladders_metadata[key].append(tiers_zh[division[key]])
                        elif j == 11: #天梯解锁时间（`apexUnlockTime`）
                            challenger_ladders_metadata[key].append(time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime(division["apexUnlockTimeMillis"] // 1000)))
                        else:
                            challenger_ladders_metadata[key].append(division[key])
                for j in range(len(division["standings"])):
                    standing = division["standings"][j]
                    standing_summoner_recapture = 0
                    standing_summoner = await get_info(connection, standing["puuid"])
                    while not standing_summoner["info_got"] and standing_summoner["body"]["httpStatus"] != 404 and standing_summoner_recapture < 3:
                        logPrint(standing_summoner["message"])
                        standing_summoner_recapture += 1
                        logPrint("第%d/%d名顶级%s%s%s玩家（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\n[%d/%d] Information of Player (Puuid: %s) in the %s %s %s apex capture failed! Recapturing this player's information ... Times tried: %d" %(j + 1, len(division["standings"]), queueTypes_zh[queueType], tiers_zh[tier], division["division"], standing["puuid"], standing_summoner_recapture, j + 1, len(division["standings"]), standing["puuid"], queueTypes_zh[queueType], tiers_zh[tier], division["division"], standing_summoner_recapture))
                        standing_summoner = await get_info(connection, standing["puuid"])
                    if not standing_summoner["info_got"]:
                        logPrint(standing_summoner["message"])
                        logPrint("第%d/%d名顶级%s%s%s玩家（玩家通用唯一识别码：%s）获取失败！\n[%d/%d] Information of Player (Puuid: %s) in the %s %s %s apex capture failed!" %(j + 1, len(division["standings"]), queueTypes_zh[queueType], tiers_zh[tier], division["division"], standing["puuid"], j + 1, len(division["standings"]), standing["puuid"], queueTypes_zh[queueType], tiers_zh[tier], division["division"]))
                    for k in range(len(challenger_ladders_header_keys)):
                        key = challenger_ladders_header_keys[k]
                        if k == 0 or k == 11:
                            queue_ladder_data[key].append("") if standing[key] == "NA" else queue_ladder_data[key].append(standing[key])
                        elif k == 12 or k == 18:
                            queue_ladder_data[key].append(tiers_zh[standing[key]])
                        elif k <= 19:
                            queue_ladder_data[key].append(standing[key])
                        else:
                            queue_ladder_data[key].append(standing_summoner["body"][key] if standing_summoner["info_got"] else "")
                    logPrint("顶级%s%s玩家信息整理进度（Top %s %s player information sorting process）：[%d/%d][%d/%d]" %(queueTypes_zh[queueType], tiers_zh[tier], queueTypes_en[queueType], tiers_en[tier], i + 1, len(ladders["divisions"]), j + 1, len(division["standings"])), end = "\r", print_time = True)
        challenger_ladders_statistics_output_order = [8, 10, 9, 16, 14, 17, 20, 21, 18, 0, 3, 2, 13, 7, 6, 5, 19, 4, 12, 11, 1, 15]
        queue_ladder_data_organized = {}
        for i in challenger_ladders_statistics_output_order:
            key = challenger_ladders_header_keys[i]
            queue_ladder_data_organized[key] = queue_ladder_data[key]
        ladders_data["challenger_ladder"][queueType] = queue_ladder_data_organized #注意字典赋值的原理。该语句其实无关紧要（Pay attention to the principle of assigning a dictionary. This statement is actually unnecessary）
        ladders_dfs["challenger_ladder"][queueType] = pandas.DataFrame(data = queue_ladder_data_organized)
        logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...")
        for column in ladders_dfs["challenger_ladder"][queueType]:
            if ladders_dfs["challenger_ladder"][queueType][column].dtype == "bool":
                ladders_dfs["challenger_ladder"][queueType][column] = ladders_dfs["challenger_ladder"][queueType][column].astype(str)
                for i in range(len(ladders_dfs["challenger_ladder"][queueType])):
                    ladders_dfs["challenger_ladder"][queueType].loc[i, column] = "√" if ladders_dfs["challenger_ladder"][queueType][column][i] == "True" else ""
        logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!")
        ladders_dfs["challenger_ladder"][queueType] = pandas.concat([pandas.DataFrame([challenger_ladders_header])[ladders_dfs["challenger_ladder"][queueType].columns], ladders_dfs["challenger_ladder"][queueType]], ignore_index = True)
    challenger_ladders_metadata_statistics_output_order = [2, 9, 6, 1, 7, 10, 8, 3, 0, 4, 5, 11]
    challenger_ladders_metadata_organized = {}
    for i in challenger_ladders_metadata_statistics_output_order:
        key = challenger_ladders_metadata_header_keys[i]
        challenger_ladders_metadata_organized[key] = challenger_ladders_metadata[key]
    challenger_ladders_metadata_df = pandas.DataFrame(data = challenger_ladders_metadata_organized)
    challenger_ladders_metadata_df = pandas.concat([pandas.DataFrame([challenger_ladders_metadata_header])[challenger_ladders_metadata_df.columns], challenger_ladders_metadata_df], ignore_index = True)
    
    topRated_ladder_queueTypes = await (await connection.request("GET", "/lol-ranked/v1/top-rated-ladders-enabled")).json()
    topRated_ladders_header = {"leaguePoints": "排名分", "position": "当前位次", "positionDelta": "位次变化", "previousPosition": "过往位次", "puuid": "玩家通用唯一识别码", "ratedTier": "段位", "summonerId": "召唤师序号", "summonerName": "召唤师名", "wins": "胜场", "gameName": "玩家昵称", "tagLine": "昵称编号"}
    topRated_ladders_header_keys = list(topRated_ladders_header.keys())
    for queueType in topRated_ladder_queueTypes:
        ladders = await (await connection.request("GET", f"/lol-ranked/v1/rated-ladder/{queueType}")).json()
        json3name = "RatedApex-%s(%s).json" %(queueType, runTime_hour)
        while True:
            try:
                with open(os.path.join(folder, json3name), "w", encoding = "utf-8") as jsonfile3:
                    json.dump(ladders, jsonfile3, indent = 4, ensure_ascii = False)
            except FileNotFoundError:
                os.makedirs(folder, exist_ok = True)
            except UnicodeEncodeError:
                logPrint("\n顶级%s玩家信息文本文档生成失败！请检查内容是否包含不常用字符！\nTop %s player information generation failure! Please check if the content includes any abnormal characters!\n" %(queueTypes_zh[queueType], queueTypes_en[queueType]))
                break
            else:
                logPrint('\n顶级%s玩家信息已保存为“%s”。\nTop %s player information is saved as "%s".\n' %(queueTypes_zh[queueType], os.path.join(folder, json3name), queueTypes_en[queueType], os.path.join(folder, json3name)))
                break
        ladders_data["topRated_ladder"][queueType] = {}
        queue_ladder_data = ladders_data["topRated_ladder"][queueType]
        for i in range(len(topRated_ladders_header_keys)):
            key = topRated_ladders_header_keys[i]
            queue_ladder_data[key] = []
        for i in range(len(ladders["standings"])):
            standing = ladders["standings"][i]
            standing_summoner_recapture = 0
            standing_summoner = await get_info(connection, standing["puuid"])
            while not standing_summoner["info_got"] and standing_summoner["body"]["httpStatus"] != 404 and standing_summoner_recapture < 3:
                logPrint(standing_summoner["message"])
                standing_summoner_recapture += 1
                logPrint("第%d/%d名顶级%s玩家（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\n[%d/%d] Information of Player (Puuid: %s) in the %s apex capture failed! Recapturing this player's information ... Times tried: %d" %(j + 1, len(division["standings"]), queueTypes_zh[queueType], standing["puuid"], standing_summoner_recapture, j + 1, len(division["standings"]), standing["puuid"], queueTypes_zh[queueType], standing_summoner_recapture))
                standing_summoner = await get_info(connection, standing["puuid"])
            if not standing_summoner["info_got"]:
                logPrint(standing_summoner["message"])
                logPrint("第%d/%d名顶级%s玩家（玩家通用唯一识别码：%s）获取失败！\n[%d/%d] Information of Player (Puuid: %s) in the %s apex capture failed!" %(j + 1, len(division["standings"]), queueTypes_zh[queueType], standing["puuid"], j + 1, len(division["standings"]), standing["puuid"], queueTypes_zh[queueType]))
            for j in range(len(topRated_ladders_header_keys)):
                key = topRated_ladders_header_keys[j]
                if j <= 8:
                    if j == 5:
                        queue_ladder_data[key].append(ratedTiers_cherry[standing[key]] if queueType == "CHERRY" else ratedTiers_turbo[standing[key]])
                    else:
                        queue_ladder_data[key].append(standing[key])
                else:
                    queue_ladder_data[key].append(standing_summoner["body"][key] if standing_summoner["info_got"] else "")
            logPrint("顶级%s玩家信息整理进度（Top %s player information sorting process）：%d/%d" %(queueTypes_zh[queueType], queueTypes_en[queueType], i + 1, len(ladders["standings"])), end = "\r", print_time = True)
        topRated_ladders_statistics_output_order = [1, 3, 2, 6, 4, 7, 9, 10, 5, 0, 8]
        queue_ladder_data_organized = {}
        for i in topRated_ladders_statistics_output_order:
            key = topRated_ladders_header_keys[i]
            queue_ladder_data_organized[key] = queue_ladder_data[key]
        ladders_data["topRated_ladder"][queueType] = queue_ladder_data_organized
        ladders_dfs["topRated_ladder"][queueType] = pandas.DataFrame(data = queue_ladder_data_organized)
        logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...")
        for column in ladders_dfs["topRated_ladder"][queueType]:
            if ladders_dfs["topRated_ladder"][queueType][column].dtype == "bool":
                ladders_dfs["topRated_ladder"][queueType][column] = ladders_dfs["topRated_ladder"][queueType][column].astype(str)
                for i in range(len(ladders_dfs["topRated_ladder"][queueType])):
                    ladders_dfs["topRated_ladder"][queueType].loc[i, column] = "√" if ladders_dfs["topRated_ladder"][queueType][column][i] == "True" else ""
        logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!")
        ladders_dfs["topRated_ladder"][queueType] = pandas.concat([pandas.DataFrame([topRated_ladders_header])[ladders_dfs["topRated_ladder"][queueType].columns], ladders_dfs["topRated_ladder"][queueType]], ignore_index = True)
    
    logPrint("是否导出以上天梯数据至Excel中？（输入任意键导出，否则不导出）\nDo you want to export the above data into Excel? (Press any key to export or null to refuse exporting)")
    export_str = logInput()
    export = bool(export_str)
    if export:
        workbook_regenerate = True
        while workbook_regenerate:
            excel_name = "Ranked Apex - %s (%d-%d).xlsx" %(platformId, currentSeason, currentSplit)
            excel_name_sorted = "Ranked Apex - %s (%d-%d) (sorted).xlsx" %(platformId, currentSeason, currentSplit)
            workbook_exist = True
            while True:
                try:
                    with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                        # splits_info_df.to_excel(excel_writer = writer, sheet_name = "Split Config - Season %d" %currentSeason)
                        # logPrint("赛季信息导出完成！\nSplit config exported!\n")
                        # rewardTrack_df.to_excel(excel_writer = writer, sheet_name = "Reward Track - Season %d" %currentSeason)
                        # logPrint("奖励里程导出完成！\nReward milestones exported!\n")
                        challenger_ladders_metadata_df.to_excel(excel_writer = writer, sheet_name = "Tier Apex Metadata - Season %d" %currentSeason)
                        logPrint("胜点系列段位天梯元数据导出完成！\nLP apex metadata exported!\n")
                        #topRated_ladders_metadata_df.to_excel(excel_writer = writer, sheet_name = "Rating Apex Metadata - Season %d" %currentSeason)
                        #logPrint("排名分系列段位天梯元数据导出完成！\nRating apex metadata exported!\n")
                        runTimes = [] #记录保存每个队列的顶级玩家信息所花费的时间（Records the time spent in saving the top player information of each queue）
                        total_used = 0
                        ladders_reserved = 0
                        for ladderType in ladders_dfs:
                            for queueType in ladders_dfs[ladderType]:
                                start = time.time()
                                logPrint("正在导出顶级%s玩家信息……\nExporting top %s player information ..." %(queueTypes_zh[queueType], queueTypes_en[queueType]))
                                ladders_dfs[ladderType][queueType].to_excel(excel_writer = writer, sheet_name = queueType + " " + (runTime_day if ladderType == "challenger_ladder" else runTime_hour))
                                ladders_reserved += 1
                                end = time.time()
                                unit = end - start
                                total_used += unit
                                runTimes.append(unit)
                                total_remaining = 0 if sum([i for i in runTimes[:ladders_reserved + 1]]) == 0 else sum([i for i in runTimes[:ladders_reserved + 1]]) / ladders_reserved * (len(ladders_dfs["challenger_ladder"]) + len(ladders_dfs["topRated_ladder"]) - ladders_reserved)
                                logPrint("保存该段位排位天梯所花费的时间（Time spent in saving this match）： %s" %(format_runtime(unit)))
                                logPrint("已花费的总时间（Total time used）                                ： %s" %(format_runtime(total_used)))
                                logPrint("剩余时间（Time remaining）                                       ： %s" %(format_runtime(total_remaining)))
                                logPrint("预计总时间（Expected total time）                                ： %s" %(format_runtime(total_used + total_remaining)), end = "\n\n")
                except PermissionError:
                    logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                    logInput()
                except FileNotFoundError:
                    workbook_exist = False
                    os.makedirs(folder, exist_ok = True)
                    with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                        # splits_info_df.to_excel(excel_writer = writer, sheet_name = "Split Config - Season %d" %currentSeason)
                        # logPrint("赛季信息导出完成！\nSplit config exported!\n")
                        # rewardTrack_df.to_excel(excel_writer = writer, sheet_name = "Reward Track - Season %d" %currentSeason)
                        # logPrint("奖励里程导出完成！\nReward milestones exported!\n")
                        challenger_ladders_metadata_df.to_excel(excel_writer = writer, sheet_name = "Tier Apex Metadata - Season %d" %currentSeason)
                        logPrint("胜点系列段位天梯元数据导出完成！\nLP apex metadata exported!\n")
                        runTimes = [] #记录保存每个队列的顶级玩家信息所花费的时间（Records the time spent in saving the top player information of each queue）
                        total_used = 0
                        ladders_reserved = 0
                        for ladderType in ladders_dfs:
                            for queueType in ladders_dfs[ladderType]:
                                start = time.time()
                                logPrint("正在导出顶级%s玩家信息……\nExporting top %s player information ..." %(queueTypes_zh[queueType], queueTypes_en[queueType]))
                                ladders_dfs[ladderType][queueType].to_excel(excel_writer = writer, sheet_name = queueType + " " + (runTime_day if ladderType == "challenger_ladder" else runTime_hour))
                                ladders_reserved += 1
                                end = time.time()
                                unit = end - start
                                total_used += unit
                                runTimes.append(unit)
                                total_remaining = 0 if sum([i for i in runTimes[:ladders_reserved + 1]]) == 0 else sum([i for i in runTimes[:ladders_reserved + 1]]) / ladders_reserved * (len(ladders_dfs["challenger_ladder"]) + len(ladders_dfs["topRated_ladder"]) - ladders_reserved)
                                logPrint("保存该段位排位天梯所花费的时间（Time spent in saving this match）： %s" %(format_runtime(unit)))
                                logPrint("已花费的总时间（Total time used）                                ： %s" %(format_runtime(total_used)))
                                logPrint("剩余时间（Time remaining）                                       ： %s" %(format_runtime(total_remaining)))
                                logPrint("预计总时间（Expected total time）                                ： %s" %(format_runtime(total_used + total_remaining)), end = "\n\n")
                    logPrint("各队列顶级玩家信息导出完成！\nTop player information of all queues exported!\n")
                    workbook_regenerate = False
                    break
                else:
                    logPrint("各队列顶级玩家信息导出完成！\nTop player information of all queues exported!\n")
                    workbook_regenerate = False
                    break
            if workbook_exist:
                logPrint("警告：由于该文件已存在，本次导出已追加新工作表到工作簿的末尾。这可能导致队列和时间顺序的错乱。是否需要对工作表进行排序？（输入任意键排序，否则不排序）\nWarning: Because the excel workbook has existed, new sheets are appended to the last of the original sheet list. This may result in the disarrangement of queue and time orders. Do you want to sort the sheets? (Input anything to sort the sheets, or null to skip sorting)")
                sort_str = logInput()
                sort = bool(sort_str)
                if sort:
                    apex_loaded = True
                    logPrint("正在读取刚刚创建的工作表……\nLoading the workbook just created ...")
                    while True:
                        try:
                            wb = load_workbook(os.path.join(folder, excel_name))
                        except FileNotFoundError:
                            logPrint('排位天梯工作簿读取失败！请确保“%s”文件夹内含有名为“%s”的工作簿。如果需要重新生成该工作簿，请输入“0”。\nERROR reading the ranked apex workbook! Please make sure the workbook "%s" is in the folder "%s". If you want to regenerate this workbook, please submit "0".' %(folder, excel_name, excel_name, folder))
                            apex_reload = logInput()
                            if apex_reload == "0":
                                apex_loaded = False
                                workbook_regenerate = True
                                break
                        else:
                            break
                    if apex_loaded:
                        sheetnames = wb.sheetnames #第一次获取原工作簿的工作表名称列表（The first time to get the sheet name list of the original workbook）
                        #下面锁定工作表顺序（The following code determine the sheet order）
                        logPrint("正在创建顺序工作表列表……\nCreating the ordered sheet list ...")
                        ##第一部分：赛季信息类工作表（Part 1: Split config sheets）
                        split_config_dict = {int(sheet_iter.split()[-1]): sheet_iter for sheet_iter in sheetnames if sheet_iter.startswith("Split Config")}
                        reward_track_dict = {int(sheet_iter.split()[-1]): sheet_iter for sheet_iter in sheetnames if sheet_iter.startswith("Reward Track")}
                        ##第二部分：天梯元数据工作表（Part 2: Apex metadata sheets）
                        tier_apex_metadata_dict = {int(sheet_iter.split()[-1]): sheet_iter for sheet_iter in sheetnames if sheet_iter.startswith("Tier Apex Metadata")}
                        ##第三部分：天梯工作表（Part 3: Apex sheets）
                        challenger_ladders_dict = {}
                        topRated_ladders_dict = {}
                        for sheet_iter in sheetnames:
                            if any(sheet_iter.split(maxsplit = 1)[0] == queueType for queueType in challenger_ladder_queueTypes):
                                queueType_tmp = sheet_iter.split(maxsplit = 1)[0] #以工作表名的队列部分为排序依据（Sort the sheetnames by the queueType part of the sheet name）
                                time_str = sheet_iter.split(maxsplit = 1)[1] #目前暂不需要考虑时间因工作表名长度限制而被截断的问题（Currently the issue that the time may be cut off due to the sheet name length limit doesn't need to be considered）
                                if not queueType_tmp in challenger_ladders_dict:
                                    challenger_ladders_dict[queueType_tmp] = {}
                                challenger_ladders_dict[queueType_tmp][time_str] = sheet_iter
                            elif any(sheet_iter.split(maxsplit = 1)[0] == queueType for queueType in topRated_ladder_queueTypes):
                                queueType_tmp = sheet_iter.split(maxsplit = 1)[0] #以工作表名的队列部分为排序依据（Sort the sheetnames by the queueType part of the sheet name）
                                time_str = sheet_iter.split(maxsplit = 1)[1] #目前暂不需要考虑时间因工作表名长度限制而被截断的问题（Currently the issue that the time may be cut off due to the sheet name length limit doesn't need to be considered）
                                if not queueType_tmp in topRated_ladders_dict:
                                    topRated_ladders_dict[queueType_tmp] = {}
                                topRated_ladders_dict[queueType_tmp][time_str] = sheet_iter
                        sheetnames_sorted = [] #所有工作表的期望顺序存储在sheetnames_sorted变量中（The ordered result of all sheets is stored in the variable `sheetnames_sorted`）
                        for season in sorted(set(split_config_dict.keys()) | set(reward_track_dict.keys())): #第一部分：赛季信息类工作表（Part 1: Split config sheets）
                            if split_config_dict[season] in sheetnames:
                                sheetnames_sorted.append(split_config_dict[season])
                            if reward_track_dict[season] in sheetnames:
                                sheetnames_sorted.append(reward_track_dict[season])
                        for season in sorted(tier_apex_metadata_dict.keys()): #第二部分：天梯元数据工作表（Part 2: Apex metadata sheets）
                            if tier_apex_metadata_dict[season] in sheetnames:
                                sheetnames_sorted.append(tier_apex_metadata_dict[season])
                        for queueType_iter in challenger_ladder_queueTypes + topRated_ladder_queueTypes: #第三部分：天梯工作表（Part 3: Apex sheets）
                            if queueType_iter in challenger_ladders_dict:
                                for time_iter in sorted(challenger_ladders_dict[queueType_iter].keys()): #队列顺序以API中记录的队列顺序为准。下同（The queueType order of sheets adopts that recorded in API. So does the following）
                                    sheetnames_sorted.append(challenger_ladders_dict[queueType_iter][time_iter])
                            if queueType_iter in topRated_ladders_dict:
                                for time_iter in sorted(topRated_ladders_dict[queueType_iter].keys()):
                                    sheetnames_sorted.append(topRated_ladders_dict[queueType_iter][time_iter])
                        #下面排列所有工作表（The following code arrange all sheets）
                        logPrint("正在排序……\nOrdering ...")
                        for i in range(len(sheetnames_sorted)): #排序的思路是每次将一个工作表根据其在原工作表列表中的索引和在顺序工作表列表中的索引的差值进行移动（The main idea of sheets' sorting is to move each sheet according to the difference of the indices between in the original sheet list and in the ordered sheet list）
                            sheetnames = wb.sheetnames #因为一次移动可能导致很多其它工作表的位置发生变化，所以必须每次都重新获取工作表列表（Because a moving event may result in location change of many other sheets, the sheet list must be obtained each time）
                            sheetname_iter = sheetnames_sorted[i] #这里以顺序工作表为迭代器进行遍历，因为顺序工作表是固定不变的（Here the ordered sheet list acts as the iterator to be traversed, for the ordered sheet list is fixed）
                            if sheetnames[i] != sheetname_iter:
                                preIndex = sheetnames.index(sheetname_iter)
                                wb.move_sheet(sheetname_iter, i - preIndex) #注意移动距离数应当是排序后的索引减去排序前的索引（Note that the moving offset should be the index in the ordered list subtracted by that in the original list）
                            #logPrint("排序进度（Ordering process）：%d/%d\t工作表名称（Sheet name）： %s" %(i + 1, len(sheetnames_sorted), sheetname_iter), end = "\r")
                        logPrint('正在保存中……\nSaving the ordered workbook ...')
                        wb.save(os.path.join(folder, excel_name_sorted))
                        logPrint('排序完成！排好序的工作簿已保存为“%s”。\nOrdering finished! The ordered workbook is saved as "%s".\n' %(excel_name_sorted, excel_name_sorted))
                        workbook_regenerate = False

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_challenger_tier(connection)
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

runTime_day = time.strftime("%Y-%m-%d", time.localtime())
runTime_hour = time.strftime("%Y-%m-%d %Hh", time.localtime())
connector.start()
