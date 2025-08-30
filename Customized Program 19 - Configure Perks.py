from lcu_driver import Connector
import json, numpy, os, pandas, platform, pyperclip, re, shutil, time, traceback, unicodedata, _io
from wcwidth import wcswidth
from openpyxl import load_workbook

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/08/20
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

log_folder = "日志（Logs）/Customized Program 19 - Configure Perks"
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
# 配置符文（Configure perks）
#-----------------------------------------------------------------------------
#声明适用于所有符文数据的常量字典（Declare constant dictionaries which apply to all perk data）
slotTypes = {"": "待定", "kKeyStone": "基石", "kMixedRegularSplashable": "符文", "kStatMod": "属性"}

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
            # print("单行数据字符串输出宽度超过当前终端窗口宽度！将直接打印该数据框！\nThe output width of each record string exceeds the current width of the terminal window! The program is going to directly print this dataframe!")
            result = str(df)
            return (result, maxLens)
        # else:
        #     print("单行数据字符串输出宽度超过当前终端窗口宽度！将继续格式化输出！\nThe output width of each record string exceeds the current width of the terminal window! The program is going on formatted printing!")
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

def clear_screen():
    if platform.system() == "Windows":
        os.system("CLS")
    else:
        os.system("clear")

async def sort_perk_data(connection):
    perks = await (await connection.request("GET", "/lol-perks/v1/perks")).json()
    perkstyles_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
    #下面指定符文的排列顺序（The following code specify the perk ordering）
    defaultPerkOrder = [] #后续形成数据框时，对符文按照其在客户端中的出现顺序进行排序（When the dataframe is formed, sort it by the order that the perks appear in the League Client）
    perkSlotLabels = {}
    ##基石和符文（Key stones and perks）
    for style in perkstyles_initial["styles"]:
        for slot in style["slots"]:
            if slot["type"] in {"kKeyStone", "kMixedRegularSplashable"}:
                defaultPerkOrder += slot["perks"]
            for perkId in slot["perks"]:
                perkSlotLabels[perkId] = slot["slotLabel"]
    ##属性（Stat mods）
    kStatMod_perkIds = []
    for perk in perks:
        if perk["slotType"] == "kStatMod":
            kStatMod_perkIds.append(perk["id"])
    defaultPerkOrder += sorted(kStatMod_perkIds)
    ##其它符文按照符文序号正序排列（Other perks are sorted by the ascending order of perkId）
    perkIds_sorted = sorted(map(lambda x: x["id"], perks))
    for perkId in perkIds_sorted:
        if not perkId in defaultPerkOrder:
            defaultPerkOrder.append(perkId)
    ##构建符文序号权重字典
    defaultPerkOrder_dict = {defaultPerkOrder[i]: i for i in range(len(defaultPerkOrder))}
    perkstyles = {style["id"]: style for style in perkstyles_initial["styles"]}
    perk_header = {"iconPath": "图标路径", "id": "符文序号", "longDesc": "详细描述", "name": "符文名称", "recommendationDescriptor": "符文推荐工具描述", "shortDesc": "简略描述", "slotType": "槽位类型", "styleId": "符文系序号", "styleIdName": "符文系内置名", "tooltip": "游戏内提示", "styleName": "符文系名称", "slotLabel": "槽位标签"}
    perk_header_keys = list(perk_header.keys())
    perk_data = {}
    for i in range(len(perk_header_keys)):
        key = perk_header_keys[i]
        perk_data[key] = []
    slotTypes = {"": "待定", "kKeyStone": "基石", "kMixedRegularSplashable": "符文", "kStatMod": "属性"}
    for perk in perks:
        for i in range(len(perk_header_keys)):
            key = perk_header_keys[i]
            if i <= 9:
                if i == 6: #槽位类型（`slotType`）
                    perk_data[key].append(slotTypes[perk[key]])
                else:
                    perk_data[key].append(perk[key])
            elif i == 10: #符文系名称（`styleName`）
                perk_data[key].append(perkstyles[perk["styleId"]]["name"] if perk["styleId"] in perkstyles else "")
            else: #槽位标签（`slotLabel`）
                perk_data[key].append(perkSlotLabels.get(perk["id"], ""))
    perk_statistics_output_order = [1, 3, 7, 8, 10, 6, 11, 4, 5, 2, 9, 0]
    perk_data_organized = {}
    for i in perk_statistics_output_order:
        key = perk_header_keys[i]
        perk_data_organized[key] = perk_data[key]
    perk_df = pandas.DataFrame(data = perk_data_organized, index = range(1, len(perks) + 1))
    perk_df = perk_df.sort_values(by = "id", key = lambda x: x.map(defaultPerkOrder_dict), ascending = True)
    perk_df = pandas.concat([pandas.DataFrame([perk_header])[perk_df.columns], perk_df])
    return perk_df

async def get_LoLChampions(connection): #以下代码来自查英雄脚本（The following code are from Customized Program 04）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_summonerId = current_info["summonerId"]
    LoLChampions_initial = await (await connection.request("GET", f"/lol-champions/v1/inventories/{current_summonerId}/champions")).json()
    LoLChampions = {}
    for champion in LoLChampions_initial:
        LoLChampions[champion["id"]] = champion
    LoLChampions_header = {"active": "可用性", "alias": "英雄代号", "banVoPath": "禁用台词路径", "baseLoadScreenPath": "加载界面图像路径", "baseSplashPath": "英雄封面路径", "botEnabled": "电脑模型激活情况", "chooseVoPath": "锁定台词路径", "disabledQueues": "禁用队列", "freeToPlay": "允许免费使用", "id": "英雄序号", "name": "称号", "purchased": "购买日期", "rankedPlayEnabled": "排位许可", "squarePortraitPath": "方格头像路径", "stingerSfxPath": "锁定音效路径", "title": "名称", "ownership: loyaltyReward": "获取方式：排位赛段奖励", "ownership: owned": "已拥有", "ownership: xboxGPReward": "获取方式：Xbox Game Pass奖励", "ownership: rental: endDate": "租借截止日期", "ownership: rental: purchaseDate": "租借日期", "ownership: rental: rented": "已租借", "ownership: rental: winCountRemaining": "租借可用胜场数", "role: assassin": "角色定位：刺客", "role: fighter": "角色定位：战士", "role: mage": "角色定位：法师", "role: marksman": "角色定位：射手", "role: support": "角色定位：辅助", "role: tank": "角色定位：坦克", "tacticalInfo: damageType": "战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】", "tacticalInfo: difficulty": "战略信息：难度（英雄的使用难度）", "tacticalInfo: style": "战略信息：风格【表明英雄的伤害输出方式的倾向（普攻vs技能）】", "recommendedPosition: TOP": "推荐路线：上路", "recommendedPosition: JUNGLE": "推荐路线：打野", "recommendedPosition: MIDDLE": "推荐路线：中路", "recommendedPosition: BOTTOM": "推荐路线：下路", "recommendedPosition: UTILITY": "推荐路线：辅助"}
    LoLChampions_header_keys = list(LoLChampions_header.keys())
    LoLChampions_data = {}
    recommended_position_for_champion = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    damageTypes = {"kPhysical": "物理伤害", "kMagic": "魔法伤害", "kMixed": "混合伤害"}
    #damageTypes = {"kPhysical": "Physical", "kMagic": "Magic", "kMixed": "Mixed"}
    for i in range(len(LoLChampions_header_keys)):
        key = LoLChampions_header_keys[i]
        LoLChampions_data[key] = []
    for i in sorted(LoLChampions.keys()):
        champion = LoLChampions[i]
        for j in range(len(LoLChampions_header_keys)):
            key = LoLChampions_header_keys[j]
            if j <= 15:
                if j == 11:
                    if champion[key] == 0:
                        LoLChampions_data[key].append("")
                    else:
                        try:
                            LoLChampions_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion[key] // 1000)))
                        except OSError: #出现了购买时间戳为18446744073709550616的英雄（There's a champion with the purchased timestamp 18446744073709550616）
                            LoLChampions_data[key].append("")
                else:
                    LoLChampions_data[key].append(champion[key])
            elif j <= 22:
                if j <= 18:
                    LoLChampions_data[key].append(champion["ownership"][key[11:]])
                else:
                    if j == 19 or j == 20:
                        if champion["ownership"]["rental"][key[19:]] == 0:
                            LoLChampions_data[key].append("")
                        else:
                            try:
                                LoLChampions_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion["ownership"]["rental"][key[19:]] // 1000)))
                            except OSError: #出现了租借时间戳为18446744073709550616的英雄（There's a champion with the rented timestamp 18446744073709550616）
                                LoLChampions_data[key].append("")
                    else:
                        LoLChampions_data[key].append(champion["ownership"]["rental"][key[19:]])
            elif j <= 28:
                if key[6:] in champion["roles"]:
                    LoLChampions_data[key].append(True)
                else:
                    LoLChampions_data[key].append(False)
            elif j <= 31:
                if j == 29:
                    LoLChampions_data[key].append(damageTypes[champion["tacticalInfo"][key[14:]]])
                else:
                    LoLChampions_data[key].append(champion["tacticalInfo"][key[14:]])
            else:
                if i == -1:
                    LoLChampions_data[key].append(False)
                elif key[21:] in recommended_position_for_champion[str(i)]["recommendedPositions"]:
                    LoLChampions_data[key].append(True)
                else:
                    LoLChampions_data[key].append(False)
    LoLChampions_statistics_output_order = [9, 10, 15, 1, 5, 23, 24, 25, 26, 27, 28, 32, 33, 34, 35, 36, 29, 31, 30, 17, 11, 16, 18, 8, 20, 21, 19, 22, 12, 7, 13, 3, 4, 14, 6, 2]
    LoLChampions_data_organized = {}
    for i in LoLChampions_statistics_output_order:
        key = LoLChampions_header_keys[i]
        LoLChampions_data_organized[key] = LoLChampions_data[key]
    LoLChampions_df = pandas.DataFrame(data = LoLChampions_data_organized)
    for column in LoLChampions_df:
        if LoLChampions_df[column].dtype == "bool":
            LoLChampions_df[column] = LoLChampions_df[column].astype(str)
            for i in range(len(LoLChampions_df)):
                LoLChampions_df.loc[i, column] = "√" if LoLChampions_df[column][i] == "True" else ""
    LoLChampions_df = pandas.concat([pandas.DataFrame([LoLChampions_header])[LoLChampions_df.columns], LoLChampions_df], ignore_index = True)
    return LoLChampions_df

async def get_recommended_perk(connection, championId: int, position: str, mapId: int):
    recommendedPage_header = {"isDefaultPosition": "默认分路", "isRecommendationOverride": "覆盖系统推荐符文", "position": "分路", "primaryPerkStyleId": "主系序号", "primaryRecommendationAttribute": "主系推荐属性", "recommendationChampionId": "推荐英雄序号", "recommendationId": "推荐号", "secondaryPerkStyleId": "副系序号", "secondaryRecommendationAttribute": "副系推荐属性", "summonerSpellIds": "推荐召唤师技能序号", "primaryPerkStyleName": "主系名称", "secondaryPerkStyleName": "副系名称", "summonerSpellNames": "推荐召唤师技能名称", "keystone id": "基石符文序号", "keystone name": "基石符文名称", "perkIds": "推荐符文序号列表", "perkNames": "推荐符文名称列表"}
    recommendedPage_header_keys = list(recommendedPage_header.keys())
    recommendedPage_data = {}
    recommendedPages = await (await connection.request("GET", f"/lol-perks/v1/recommended-pages/champion/{championId}/position/{position}/map/{mapId}")).json()
    if recommendedPages == []:
        recommendedPage_df = pandas.DataFrame(data = recommendedPage_header, index = 0)
    else:
        for i in range(len(recommendedPage_header_keys)):
            key = recommendedPage_header_keys[i]
            recommendedPage_data[key] = []
        positions = {"TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "UTILITY": "辅助"}
        recommendedAttributes = {"kBurstDamage": "爆发伤害", "kCooldown": "冷却时间", "kDamagePerSecond": "输出", "kDurability": "耐久", "kGold": "金币", "kHealing": "治疗效果", "kMana": "法力", "kMoveSpeed": "移动速度", "kUtility": "功能"}
        spells_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
        spells = {spell["id"]: spell for spell in spells_initial}
        perkstyles_initial = await (await connection.request("GET", "/lol-perks/v1/styles")).json()
        perkstyles = {style["id"]: style for style in perkstyles_initial}
        for page in recommendedPages:
            for i in range(len(recommendedPage_header_keys)):
                key = recommendedPage_header_keys[i]
                if i <= 12:
                    if i == 2: #分路（`position`）
                        recommendedPage_data[key].append(positions[page[key]])
                    elif i == 4 or i == 8: #推荐属性类键（Recommendation attribute-type keys）
                        recommendedPage_data[key].append(recommendedAttributes[page[key]])
                    elif i == 10: #主系名称（`primaryPerkStyleName`）
                        recommendedPage_data[key].append(perkstyles[page["primaryPerkStyleId"]]["name"])
                    elif i == 11: #副系名称（`secondaryPerkStyleName`）
                        recommendedPage_data[key].append(perkstyles[page["secondaryPerkStyleId"]]["name"])
                    elif i == 12:
                        recommendedPage_data[key].append(list(map(lambda x: spells[x]["name"], page["summonerSpellIds"])))
                    else:
                        recommendedPage_data[key].append(page[key])
                elif i <= 14: #基石符文相关键（Keystone-related keys）
                    recommendedPage_data[key].append(page[key.split()[0]][key.split()[1]])
                elif i == 15: #推荐符文序号列表（`perkIds`）
                    recommendedPage_data[key].append(list(map(lambda x: x["id"], page["perks"])))
                else: #推荐符文名称列表（`perkNames`）
                    recommendedPage_data[key].append(list(map(lambda x: x["name"], page["perks"])))
        recommendedPage_statistics_output_order = [2, 0, 3, 10, 4, 7, 11, 8, 13, 14, 15, 16, 1, 9, 12, 6]
        recommendedPage_data_organized = {}
        for i in recommendedPage_statistics_output_order:
            key = recommendedPage_header_keys[i]
            recommendedPage_data_organized[key] = recommendedPage_data[key]
        recommendedPage_df = pandas.DataFrame(data = recommendedPage_data_organized)
        for column in recommendedPage_df:
            if recommendedPage_df[column].dtype == "bool":
                recommendedPage_df[column] = recommendedPage_df[column].astype(str)
                for i in range(len(recommendedPage_df)):
                    recommendedPage_df.loc[i, column] = "√" if recommendedPage_df[column][i] == "True" else ""
        recommendedPage_df = pandas.concat([pandas.DataFrame([recommendedPage_header])[recommendedPage_df.columns], recommendedPage_df], ignore_index = True)
    return recommendedPage_df

async def get_perk_page(connection):
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_summonerId = current_info["summonerId"]
    LoLChampions_initial = await (await connection.request("GET", f"/lol-champions/v1/inventories/{current_summonerId}/champions")).json()
    LoLChampions = {}
    for champion in LoLChampions_initial:
        LoLChampions[champion["id"]] = champion
    perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
    perkPage_header = {"autoModifiedSelections": "自动调整选择", "current": "正在使用", "id": "符文页序号", "isActive": "活动中", "isDeletable": "可删除", "isEditable": "可编辑", "isRecommendationOverride": "覆盖系统推荐符文", "isTemporary": "临时创建", "isValid": "可用性", "lastModified": "上次修改时间戳", "name": "符文页名称", "order": "符文页位次", "primaryStyleIconPath": "主系图标路径", "primaryStyleId": "主系序号", "primaryStyleName": "主系名称", "quickPlayChampionIds": "快速模式英雄序号列表", "recommendationChampionId": "推荐英雄序号", "recommendationIndex": "推荐序号", "runeRecommendationId": "推荐号", "secondaryStyleIconPath": "副系图标路径", "secondaryStyleName": "副系名称", "selectedPerkIds": "已选择的符文序号列表", "subStyleId": "副系序号", "tooltipBgPath": "已配置的符文背景图片路径", "lastModifiedTime": "上次修改时间", "quickPlayChampionNames": "快速模式英雄名称列表", "recommendationChampionName": "推荐英雄名称", "pageKeystone iconPath": "基石图标路径", "pageKeystone id": "基石序号", "pageKeystone name": "基石名称", "pageKeystone slotType": "基石槽位类型", "pageKeystone styleId": "基石所属符文系序号", "uiPerksNames": "已选择的符文"}
    perkPage_header_keys = list(perkPage_header.keys())
    perkPage_data = {}
    for i in range(len(perkPage_header_keys)):
        key = perkPage_header_keys[i]
        perkPage_data[key] = []
    for page in perkPages:
        for i in range(len(perkPage_header_keys)):
            key = perkPage_header_keys[i]
            if i <= 26:
                if i == 24: #上次修改时间（`lastModifiedTime`）
                    perkPage_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(page["lastModified"] // 1000)))
                elif i == 25: #快速模式英雄名称列表（`quickPlayChampionNames`）
                    perkPage_data[key].append(list(map(lambda x: LoLChampions[x]["name"], page["quickPlayChampionIds"])))
                elif i == 26: #推荐英雄名称（`recommendationChampionName`）
                    perkPage_data[key].append("" if page["recommendationChampionId"] == 0 else LoLChampions[page["recommendationChampionId"]]["name"])
                else:
                    perkPage_data[key].append(page[key])
            elif i <= 31:
                if i == 30: #基石槽位类型（`pageKeystone slotType`）
                    perkPage_data[key].append(slotTypes[page[key.split()[0]][key.split()[1]]])
                else:
                    perkPage_data[key].append(page[key.split()[0]][key.split()[1]])
            else: #已选择的符文（`uiPerksNames`）
                perkPage_data[key].append(list(map(lambda x: x["name"], page["uiPerks"])))
    perkPage_statistics_output_order = [2, 10, 11, 1, 3, 7, 5, 4, 8, 6, 13, 14, 12, 22, 20, 19, 28, 29, 30, 31, 27, 32, 21, 23, 24, 15, 25, 16, 26, 18]
    perkPage_data_organized = {}
    for i in perkPage_statistics_output_order:
        key = perkPage_header_keys[i]
        perkPage_data_organized[key] = perkPage_data[key]
    perkPage_df = pandas.DataFrame(data = perkPage_data_organized)
    for column in perkPage_df:
        if perkPage_df[column].dtype == "bool":
            perkPage_df[column] = perkPage_df[column].astype(str)
            for i in range(len(perkPage_df)):
                perkPage_df.loc[i, column] = "√" if perkPage_df[column][i] == "True" else ""
    perkPage_df = pandas.concat([pandas.DataFrame([perkPage_header])[perkPage_df.columns], perkPage_df], ignore_index = True)
    return perkPage_df

async def configure_perks(connection):
    #设置输出路径（Set the output directory）
    info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    displayName = get_info_name(info)
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
    while True:
        logPrint("请选择您想要执行的操作：\nPlease select an operation to perform:\n0\t退出程序（Exit the program）\n1\t查看所有符文（Check all perks）\n2\t查看推荐符文（Check recommended pages）\n3\t管理符文页（Manage perk pages）")
        option = logInput()
        if option == "0":
            break
        elif option == "1":
            logPrint("请选择输出形式：\nPlease select a form to output:\n0\t返回上一层（Return to the last step）\n1\t分类（Classified）\n2\t表格（Tabified）\n3\t文件（File）")
            while True:
                form = logInput()
                if form == "":
                    continue
                elif form[0] == "0":
                    break
                elif form[0] == "1":
                    HTML_tag_re = re.compile(r"<[^>]*>")
                    perks_initial = await (await connection.request("GET", "/lol-perks/v1/perks")).json()
                    perkIds_unprinted = list(map(lambda x: x["id"], perks_initial))
                    perks = {perk["id"]: perk for perk in perks_initial}
                    perkstyles_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
                    perkstyles = {style["id"]: style for style in perkstyles_initial["styles"]}
                    #先打印符文系下的符文（First, print perks under perkstyles）
                    for i in range(len(perkstyles)):
                        style = perkstyles[sorted(perkstyles.keys())[i]]
                        slots = [] #要打印的符文槽位。属性单独显示，不会在某个符文系中被打印出来（Slots to print. Stat mods are displayed individually but not printed under any perkstyle）
                        for slot in style["slots"]:
                            if slot["type"] in {"kKeyStone", "kMixedRegularSplashable"}:
                                slots.append(slot)
                        splashableSeries = 0
                        for j in range(len(slots)):
                            slot = slots[j]
                            logPrint("%d - %s: %s\n" %(style["id"], style["name"], style["tooltip"]))
                            if slot["type"] == "kKeyStone":
                                logPrint("%s（%s）：" %(slotTypes[slot["type"]], slot["type"]))
                            else:
                                splashableSeries += 1
                                logPrint("%s第%d系列 - %s（%s Series %d - %s）：" %(slotTypes[slot["type"]], splashableSeries, slot["slotLabel"], slot["type"], splashableSeries, slot["slotLabel"]))
                            for perkId in slot["perks"]:
                                perkIds_unprinted.remove(perkId)
                                perk = perks[perkId]
                                shortDesc = perk["shortDesc"].replace("<br>", "\n")
                                longDesc = perk["longDesc"].replace("<br>", "\n")
                                while HTML_tag_re.search(shortDesc):
                                    shortDesc = shortDesc.replace(HTML_tag_re.search(shortDesc).group(), "")
                                while HTML_tag_re.search(longDesc):
                                    longDesc = longDesc.replace(HTML_tag_re.search(longDesc).group(), "")
                                shortDesc = shortDesc.replace("\n", "<br>")
                                longDesc = longDesc.replace("\n", "<br>")
                                logPrint("%d - %s: %s\n简略描述（ShortDesc）：%s\n详细描述（LongDesc）：%s\n" %(perk["id"], perk["name"], perk["recommendationDescriptor"], shortDesc, longDesc))
                            if j < len(slots) - 1:
                                logPrint("按回车键以显示下一行符文。\nPress Enter to display the next line of perks.")
                                logInput()
                                logPrint()
                                clear_screen()
                        if i < len(perkstyles) - 1:
                            logPrint("按回车键以显示下一个符文系。\nPress Enter to display the next perkstyle.")
                            logInput()
                            logPrint("\n")
                            clear_screen()
                        else:
                            logPrint("按回车键以显示属性。\nPress Enter to display the stat modes.")
                            logInput()
                            logPrint("\n")
                            clear_screen()
                    #然后打印属性符文（Second, print stat mods）
                    logPrint("属性（kStatMod）：")
                    for perk in perks_initial:
                        if perk["slotType"] == "kStatMod":
                            perkIds_unprinted.remove(perk["id"])
                            shortDesc = perk["shortDesc"].replace("<br>", "\n")
                            while HTML_tag_re.search(shortDesc):
                                shortDesc = shortDesc.replace(HTML_tag_re.search(shortDesc).group(), "")
                            shortDesc = shortDesc.replace("\n", "<br>")
                            logPrint("%d - %s: %s" %(perk["id"], perk["name"], shortDesc)) #属性符文的简略描述和详细描述是相同的，所以只需要输出一个即可（LongDesc and shortDesc of all stat mods are the same, respectively, so only one of each is enough to output）
                    logPrint("\n按回车键以显示其它符文。\nPress Enter to display other perks.")
                    logInput()
                    logPrint("\n")
                    clear_screen()
                    #最后打印其它符文（At last, print other perks）
                    logPrint("其它（Others）：")
                    for perkId in sorted(perkIds_unprinted):
                        perk = perks[perkId]
                        shortDesc = perk["shortDesc"].replace("<br>", "\n")
                        longDesc = perk["longDesc"].replace("<br>", "\n")
                        while HTML_tag_re.search(shortDesc):
                            shortDesc = shortDesc.replace(HTML_tag_re.search(shortDesc).group(), "")
                        while HTML_tag_re.search(longDesc):
                            longDesc = longDesc.replace(HTML_tag_re.search(longDesc).group(), "")
                        shortDesc = shortDesc.replace("\n", "<br>")
                        longDesc = longDesc.replace("\n", "<br>")
                        logPrint("%d - %s: %s\n简略描述（ShortDesc）：%s\n详细描述（LongDesc）：%s\n" %(perk["id"], perk["name"], perk["recommendationDescriptor"], shortDesc, longDesc))
                    logPrint("按回车键以返回上一层。\nPress Enter to return to the last step.")
                    logInput()
                    logPrint("\n")
                    clear_screen()
                    break
                elif form[0] == "2":
                    HTML_tag_re = re.compile(r"<[^>]*>")
                    perk_df = await sort_perk_data(connection)
                    for i in range(1, len(perk_df)):
                        shortDesc = perk_df.loc[i, "shortDesc"]
                        while HTML_tag_re.search(shortDesc):
                            shortDesc = shortDesc.replace(HTML_tag_re.search(shortDesc).group(), "") #数据框在输出到终端时移除HTML标签（When the dataframe is output to terminal, the HTML tags are removed）
                        perk_df.loc[i, "shortDesc"] = shortDesc
                    perk_df_fields_to_print = ["styleName", "id", "name", "slotType", "slotLabel"]
                    print(format_df(perk_df.loc[:, perk_df_fields_to_print])[0])
                    log.write(format_df(perk_df.loc[:, perk_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                    break
                elif form[0] == "3":
                    perk_df = await sort_perk_data(connection)
                    excel_name = "Perks.xlsx"
                    while True:
                        try:
                            with pandas.ExcelWriter(path = excel_name) as writer:
                                perk_df.to_excel(excel_writer = writer, sheet_name = "Perks") #数据框在导出到Excel中时保留最原始的数据（When the dataframe is exported to Excel, the most original information is reserved）
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                            logInput()
                        else:
                            break
                    logPrint(f'符文信息已导出到同目录下的“{excel_name}”中。\nPerk information has been exported into {excel_name} under the same folder.')
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option == "2":
            logPrint("请输入英雄序号：\nPlease enter a champion id:")
            LoLChampions_df = await get_LoLChampions(connection)
            LoLChampions_fields_to_print = ["id", "name", "title", "alias"]
            LoLChampions_df_query = LoLChampions_df.loc[:, LoLChampions_fields_to_print]
            LoLChampions_df_query["id"] = LoLChampions_df["id"].astype(str) #方便检索（For convenience of retrieval）
            LoLChampions_df_query = LoLChampions_df_query.map(lambda x: x.lower() if isinstance(x, str) else x)
            print(format_df(LoLChampions_df.loc[:, LoLChampions_fields_to_print])[0])
            log.write(format_df(LoLChampions_df.loc[:, LoLChampions_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
            back = False
            while True:
                champion_queryStr = logInput()
                if champion_queryStr == "":
                    continue
                elif champion_queryStr == "0":
                    back = True
                    break
                else:
                    query_positions = numpy.where(LoLChampions_df_query == champion_queryStr.lower()) #使用numpy.where检索的前提是数据框中每个单元格的值都不一样（The premise of query by `numpy.where` is that no two cells are the same）
                    if len(query_positions[0]) == 0:
                        logPrint("没有找到该英雄。请重新输入。\nChampion not found. Please try again.")
                    else:
                        resultRow = query_positions[0]
                        result_champion_df = LoLChampions_df.loc[resultRow, LoLChampions_fields_to_print].reset_index(drop = True)
                        championId = LoLChampions_df.loc[resultRow[0], "id"]
                        championName = LoLChampions_df.loc[resultRow[0], "name"]
                        championAlias = LoLChampions_df.loc[resultRow[0], "alias"]
                        logPrint("您选择了以下英雄：\nYou selected the following champion:")
                        print(format_df(result_champion_df)[0])
                        log.write(format_df(result_champion_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                        break
            if back:
                continue
            positionDict = {"TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "UTILITY": "辅助（补位）"}
            recommended_champion_positions = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
            recommendedPositions = recommended_champion_positions[str(championId)]["recommendedPositions"] if str(championId) in recommended_champion_positions else ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
            logPrint("请选择一条推荐路线：\nPlease select a recommended position:")
            position_count = 0
            for position in recommendedPositions:
                position_count += 1
                logPrint("%d\t%s\t%s" %(position_count, position, positionDict[position]))
            while True:
                position_str = logInput()
                if position_str == "0":
                    back = True
                    break
                elif position_str.upper() in recommendedPositions:
                    championPosition = position_str.upper()
                    break
                elif position_str in list(map(str, range(1, len(recommendedPositions) + 1))):
                    championPosition = recommendedPositions[int(position_str) - 1]
                    break
                elif position_str.upper() in positionDict:
                    logPrint("%s的推荐路线中没有%s。请重新输入。\n%s isn't a recommended position of %s. Please try again." %(result_champion_df.loc[0, "name"], position_str.upper(), position_str.upper(), result_champion_df.loc[0, "alias"]))
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if back:
                continue
            logPrint("请输入地图序号：\nPlease enter the mapId:")
            gamemaps = {8: {"zh_CN": "水晶之痕", "en_US": "Crystal Scar"}, 10: {"zh_CN": "扭曲丛林", "en_US": "Twisted Treeline"}, 11: {"zh_CN": "召唤师峡谷", "en_US": "Summoner's Rift"}, 12: {"zh_CN": "嚎哭深渊", "en_US": "Howling Abyss"}, 14: {"zh_CN": "屠夫之桥", "en_US": "Butcher's Bridge"}, 16: {"zh_CN": "星界废墟", "en_US": "Cosmic Ruins"}, 18: {"zh_CN": "瓦洛兰城市公园", "en_US": "Valoran City Park"}, 19: {"zh_CN": "第43区", "en_US": "Substructure 43"}, 20: {"zh_CN": "飞船坠落点", "en_US": "Crash Site"}, 21: {"zh_CN": "百合与莲花的神庙", "en_US": "Temple of Lily and Lotus"}, 22: {"zh_CN": "聚点危机", "en_US": "Convergence"}, 30: {"zh_CN": "怒火角斗场", "en_US": "Rings of Wrath"}, 33: {"zh_CN": "最终都市", "en_US": "Final City"}, 35: {"zh_CN": "班德尔之森", "en_US": "The Bandlewood"}}
            gamemap_df = pandas.DataFrame(data = {"mapId": list(gamemaps.keys()), "zh_CN": list(map(lambda x: x["zh_CN"], gamemaps.values())), "en_US": list(map(lambda x: x["en_US"], gamemaps.values()))})
            print(format_df(gamemap_df)[0])
            log.write(format_df(gamemap_df, width_exceed_ask = False, direct_print = False)[0])
            while True:
                mapStr = logInput()
                if mapStr == "0":
                    back = True
                    break
                elif mapStr in list(map(str, gamemaps.keys())):
                    mapId = int(mapStr)
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input. Please try again.")
            if back:
                continue
            recommendedPage_df = await get_recommended_perk(connection, championId, championPosition, mapId)
            if len(recommendedPage_df) == 1: #一般情况下接口数据是正常获取的（The endpoint should work in normal cases）
                logPrint("%s中的%s%s推荐符文信息不可用。\nRecommended perk information of %s %s on %s isn't available." %(gamemaps[mapId]["zh_CN"], positionDict[championPosition], result_champion_df.loc[0, "name"], championPosition, result_champion_df.loc[0, "alias"], gamemaps[mapId]["en_US"]))
            else:
                logPrint('选择下方的一个方案以查看详细信息。输入“0”以返回上一层。\nSelect a page to check the details. Submit "0" to return to the last step.')
                recommendedPage_df_fields_to_print = ["primaryPerkStyleName", "secondaryPerkStyleName", "keystone name", "summonerSpellNames"]
                print(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], print_index = True)[0])
                log.write(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                while True:
                    pageIndex = logInput()
                    if pageIndex == "":
                        continue
                    elif pageIndex == "0":
                        break
                    elif pageIndex in list(map(str, range(1, len(recommendedPage_df) + 1))):
                        pageIndex = int(pageIndex)
                        primaryPerkStyleName = recommendedPage_df.loc[pageIndex, "primaryPerkStyleName"]
                        primaryPerkStyleId = recommendedPage_df.loc[pageIndex, "primaryPerkStyleId"]
                        primaryRecommendationAttribute = recommendedPage_df.loc[pageIndex, "primaryRecommendationAttribute"]
                        secondaryPerkStyleName = recommendedPage_df.loc[pageIndex, "secondaryPerkStyleName"]
                        secondaryPerkStyleId = recommendedPage_df.loc[pageIndex, "secondaryPerkStyleId"]
                        secondaryRecommendationAttribute = recommendedPage_df.loc[pageIndex, "secondaryRecommendationAttribute"]
                        keystoneId = recommendedPage_df.loc[pageIndex, "keystone id"]
                        keystoneName = recommendedPage_df.loc[pageIndex, "keystone name"]
                        perkIds = recommendedPage_df.loc[pageIndex, "perkIds"]
                        perkNames = recommendedPage_df.loc[pageIndex, "perkNames"]
                        logPrint("主系（Style）：%s (%d)\t%s\n副系（Substyle）：%s (%d)\t%s\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, primaryRecommendationAttribute, secondaryPerkStyleName, secondaryPerkStyleId, secondaryRecommendationAttribute, keystoneName, keystoneId, perkIds, perkNames))
                        logPrint("是否导出推荐符文信息？（输入任意键导出，否则不导出。）\nExport recommended page information? (Submit any non-empty string to export, or null to refuse exporting.)")
                        page_export_str = logInput()
                        page_export = bool(page_export_str)
                        if page_export:
                            recommendedPage_json = {"name": "%s - %s" %(championName, keystoneName), "isTemporary": True, "primaryStyleId": primaryPerkStyleId, "secondaryStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                            logPrint("请选择导出方式：\nPlease select a way to export:\n1\t写入文件（Write into a file）\n2\t复制到剪贴板（Copy to clipboard）")
                            while True:
                                export_method = logInput()
                                if export_method == "":
                                    continue
                                elif export_method[0] == "0":
                                    break
                                elif export_method[0] == "1":
                                    json1name = "Recommended Page.json"
                                    with open(json1name, "w", encoding = "utf-8") as fp:
                                        json.dump(recommendedPage_json, fp, ensure_ascii = False)
                                    logPrint('%s的推荐符文信息已导出到同目录下的“%s”中。\nRecommended perk page of %s has been exported into "%s" under the same folder.' %(championName, json1name, championAlias, json1name))
                                    break
                                elif export_method[0] == "2":
                                    pyperclip.copy(recommendedPage_json)
                                    logPrint('%s的推荐符文信息已复制到剪贴板中。\nRecommended perk page of %s has been copied to clipboard.' %(championName, championAlias))
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        logPrint('选择下方的一个方案以查看详细信息。输入“0”以返回上一层。\nSelect a page to check the details. Submit "0" to return to the last step.')
                        print(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], print_index = True)[0])
                        log.write(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input. Please try again.")
        elif option == "3":
            logPrint("您的符文页信息如下：\nYour perk pages are listed below:")
            perkPage_df = await get_perk_page(connection)
            perkPage_df_fields_to_print = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
            print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
            log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
            logPrint("请选择一个操作：\nPlease select an action:\n0\t返回上一层（Return to the last step）\n1\t导出所有符文页（Export all pages）\n2\t查看、编辑和导出一个符文页（Check, edit and export a page）\n3\t切换活动符文页（Toggle active perk page）\n4\t排序符文页（Order perk pages）\n5\t删除符文页（Delete perk pages）")
            while True:
                action = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    excel_name = f"Player Perk Pages - {displayName}.xlsx"
                    while True:
                        try:
                            with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                                currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
                                perkPage_df.to_excel(excel_writer = writer, sheet_name = f"Perk Page - {currentTime}")
                            logPrint('玩家符文页信息已保存为“%s”。\nPlayer perk page information is saved as "%s".' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                            logInput()
                        except FileNotFoundError:
                            os.makedirs(folder, exist_ok = True)
                            with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "w") as writer:
                                currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
                                perkPage_df.to_excel(excel_writer = writer, sheet_name = f"Perk Page - {currentTime}")
                            logPrint('玩家符文页信息已保存为“%s”。\nPlayer perk page information is saved as "%s".' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
                            break
                        else:
                            break
                elif action[0] == "2":
                    perks_initial = await (await connection.request("GET", "/lol-perks/v1/perks")).json()
                    perks = {perk["id"]: perk for perk in perks_initial}
                    perkstyles_initial = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
                    perkstyles = {style["id"]: style for style in perkstyles_initial["styles"]}
                    logPrint('请选择一个符文页：（输入索引范围之外的整数则创建一个新的符文页。）\nPlease select a page: (Enter an integer beyong the index range to create a new page.)')
                    print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                    log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                    while True:
                        pageIndex = logInput()
                        if pageIndex == "":
                            continue
                        elif pageIndex == "0":
                            break
                        else:
                            try:
                                pageIndex = int(pageIndex)
                            except ValueError:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            else:
                                page_exist = pageIndex >= 1 and pageIndex < len(perkPage_df)
                        if page_exist:
                            pageId = perkPage_df.loc[pageIndex, "id"]
                            pageName = perkPage_df.loc[pageIndex, "name"]
                            isTemporary = perkPage_df.loc[pageIndex, "isTemporary"] == "√"
                            primaryPerkStyleName = perkPage_df.loc[pageIndex, "primaryStyleName"]
                            primaryPerkStyleId = perkPage_df.loc[pageIndex, "primaryStyleId"]
                            secondaryPerkStyleName = perkPage_df.loc[pageIndex, "secondaryStyleName"]
                            secondaryPerkStyleId = perkPage_df.loc[pageIndex, "subStyleId"]
                            keystoneId = perkPage_df.loc[pageIndex, "pageKeystone id"]
                            keystoneName = perkPage_df.loc[pageIndex, "pageKeystone name"]
                            perkIds = perkPage_df.loc[pageIndex, "selectedPerkIds"]
                            perkNames = perkPage_df.loc[pageIndex, "uiPerksNames"]
                            logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
                            logPrint("是否编辑该符文页？（输入任意键以确认，否则放弃编辑。）\nDo you want to edit this perk page? (Submit any non-empty string to confirm, or null to decline editing.)")
                            page_edit_str = logInput()
                            page_edit = bool(page_edit_str)
                        else:
                            page_edit = True
                            perkInventory = await (await connection.request("GET", "/lol-perks/v1/inventory")).json() #这个接口返回的信息中，自定义符文页可解锁似乎是一直是可用的（In the result returned by this endpoint, the "isCustomPageCreationUnlocked" seems always to be True）
                            if not perkInventory["canAddCustomPage"]:
                                logPrint("符文页栏位已满。删除或拥有更多符文页以创建新的符文页。程序将创建临时符文页。\nInventory full. Delete or obtain more pages to create more. The program is going to create a temporary perk page.")
                                isTemporary = True
                            else:
                                isTemporary = False
                        if page_edit:
                            logPrint("请选择编辑方式：\nPlease select a method of:\n0\t放弃修改（Quit editing）\n1\t逐个修改（Successively）\n2\t批量修改（In batch）\n3\t仅重命名（Rename only）\n4\t读取Json数据（From json data）\n5\t读取文件（From a file）")
                            while True:
                                back = False #决定是否切换编辑方式（Determines whether to switch to another method of editing）
                                method = logInput()
                                if method == "":
                                    continue
                                elif method[0] == "0":
                                    page_edit = False
                                    break
                                elif method[0] == "1": #保持与客户端符文配置步骤相同（Keep synchronized with the latest perk configuration steps in the League Client）
                                    page_body = {"name": "", "isTemporary": isTemporary, "primaryStyleId": -1, "subStyleId": -1, "selectedPerkIds": [-1, -1, -1, -1, -1, -1, -1, -1, -1]} #请求主体初始化（Initialize the request body）
                                    logPrint('在下面的步骤中，请确保输入的是正整数类型的符文系序号和符文序号。输入“0”以撤回最近一次输入。\nDuring the following steps, please make sure you submit the perkStyleId and perkId of integer type. Submit "0" to revert the latest input.')
                                    step = 1
                                    while step <= 11: #客户端内配置符文页需要11个步骤（Setting a perk page in the League Client needs 11 steps）
                                        recall = False #决定是否撤回最近一次操作（Determines whether to recall the latest operation）
                                        parameter_dict = {} #将用户输入的序号映射到符文系序号和符文序号。用户也可以直接输入原始序号（Map user input to the perkstyleIds and perkIds. The user may input the raw ids）
                                        #设置输出提示（Set up the output hint）
                                        if step == 1:
                                            tooltip = f"第{step}步：请选择主系。\nStep {step}: Please select a primary perkstyle."
                                            primaryStyleIds = sorted(perkstyles.keys())
                                            perkTableStr = ""
                                            for i in range(len(primaryStyleIds)):
                                                styleId = primaryStyleIds[i]
                                                parameter_dict[i + 1] = styleId
                                                perkTableStr += "\n#%d\t%d\t%s" %(i + 1, styleId, perkstyles[styleId]["name"])
                                        elif step == 2:
                                            tooltip = f"第{step}步：请选择基石。\nStep {step}: Please select a keystone."
                                            perkTableStr = ""
                                            if page_body["primaryStyleId"] in perkstyles:
                                                slotPerks = perkstyles[page_body["primaryStyleId"]]["slots"][step - 2]["perks"]
                                                for i in range(len(slotPerks)):
                                                    perkId = slotPerks[i]
                                                    parameter_dict[i + 1] = perkId
                                                    perkTableStr += "\n#%d\t%d\t%s" %(i + 1, perkId, perks[perkId]["name"])
                                        elif step <= 5:
                                            perkTableStr = ""
                                            if page_body["primaryStyleId"] in perkstyles:
                                                slotLabel = perkstyles[page_body["primaryStyleId"]]["slots"][step - 2]["slotLabel"]
                                                slotPerks = perkstyles[page_body["primaryStyleId"]]["slots"][step - 2]["perks"]
                                                for i in range(len(slotPerks)):
                                                    perkId = slotPerks[i]
                                                    parameter_dict[i + 1] = perkId
                                                    perkTableStr += "\n#%d\t%d\t%s" %(i + 1, perkId, perks[perkId]["name"])
                                            else:
                                                slotLabel = "主系第%d行符文" %(step - 2)
                                            tooltip = f"第{step}步：请选择{slotLabel}符文。\nStep {step}: Please select a {slotLabel} perk."
                                        elif step == 6:
                                            tooltip = f"第{step}步：请选择副系。\nStep {step}: Please select a secondary perkstyle."
                                            perkTableStr = ""
                                            if page_body["primaryStyleId"] in perkstyles:
                                                allowedSubStyles = perkstyles[page_body["primaryStyleId"]]["allowedSubStyles"]
                                                for i in range(len(allowedSubStyles)):
                                                    styleId = allowedSubStyles[i]
                                                    parameter_dict[i + 1] = styleId
                                                    perkTableStr += "\n#%d\t%d\t%s" %(i + 1, styleId, perkstyles[styleId]["name"])
                                        elif step <= 8:
                                            substyle = perkstyles[page_body["subStyleId"]]["name"] if page_body["subStyleId"] in perkstyles else "副系"
                                            tooltip = f"第{step}步：请选择一个{substyle}符文。\nStep {step}: Please select a {substyle} perk."
                                            perkTableStr = ""
                                            if page_body["primaryStyleId"] in perkstyles and page_body["subStyleId"] in allowedSubStyles:
                                                j = 0
                                                for i in range(1, 4):
                                                    slotLabel = perkstyles[page_body["subStyleId"]]["slots"][i]["slotLabel"]
                                                    perkTableStr += "\n%s:" %(slotLabel)
                                                    slotPerks = perkstyles[page_body["subStyleId"]]["slots"][i]["perks"]
                                                    for perkId in slotPerks:
                                                        j += 1
                                                        parameter_dict[j] = perkId
                                                        perkTableStr += "\n#%d\t%d\t%s" %(j, perkId, perks[perkId]["name"])
                                        else:
                                            slotLabel = perkstyles_initial["styles"][0]["slots"][step - 5]["slotLabel"] #这里的“0”可以换成1～4之间的任意正整数，因为所有符文系的后三个小符文信息都是一样的（Here the "0" can be replaced by any integer between 1 and 4, for the last three stat mods in all perkstyles are the same）
                                            slotPerks = perkstyles_initial["styles"][0]["slots"][step - 5]["perks"]
                                            tooltip = f"第{step}步：请选择{slotLabel}属性。\nStep {step}: Please select a {slotLabel} stat mod."
                                            perkTableStr = ""
                                            for i in range(len(slotPerks)):
                                                perkId = slotPerks[i]
                                                parameter_dict[i + 1] = perkId
                                                perkTableStr += "\n#%d\t%d\t%s" %(i + 1, perkId, perks[perkId]["name"])
                                        logPrint(tooltip + perkTableStr)
                                        #输入参数（Input the parameter）
                                        while True:
                                            parameter = logInput()
                                            if parameter == "":
                                                continue
                                            elif parameter == "0":
                                                recall = True
                                                break
                                            else:
                                                try:
                                                    parameter = int(parameter) #这里除了要求输入是整数外，没有其它要求。这也就意味着，逐个修改允许配置不可用的符文页（There's not any other restraints besides the input is an integer, which means successive input allows invalid perk pages）
                                                except ValueError:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                else:
                                                    if parameter in parameter_dict:
                                                        parameter = parameter_dict[parameter]
                                                    break
                                        #处理输入（Handle the input）
                                        if recall:
                                            step -= 1
                                            if step == 0:
                                                back = True
                                                break
                                        else:
                                            if step == 1:
                                                page_body["primaryStyleId"] = parameter
                                            elif step <= 5:
                                                page_body["selectedPerkIds"][step - 2] = parameter
                                            elif step == 6:
                                                page_body["subStyleId"] = parameter
                                            else:
                                                page_body["selectedPerkIds"][step - 3] = parameter
                                            step += 1
                                    if back:
                                        page_edit = False
                                    else:
                                        page_edit = True
                                        if page_exist:
                                            old_pageName = pageName
                                            logPrint("是否需要修改符文页名称？（输入任意键修改，否则不修改。）\nDo you want to change the page name? (Submit any non-empty string to change, or null to stop changing.)")
                                            pageNameChange_str = logInput()
                                            pageName_change = bool(pageNameChange_str)
                                            if pageName_change:
                                                logPrint("请输入符文页的新名称：\nPlease enter the new name of this perk page:")
                                                new_pageName = logInput()
                                            else:
                                                new_pageName = old_pageName
                                            if old_pageName != new_pageName:
                                                logPrint("输入任意非空字符串以确认修改，否则取消修改。\nSubmit any non-empty string to confirm changing, or null to cancel.\n旧名称（Old）：%s\n新名称（New）：%s" %(old_pageName, new_pageName))
                                                pageName_change_confirm_str = logInput()
                                                pageName_change_confirm = bool(pageName_change_confirm_str)
                                            else:
                                                pageName_change_confirm = False
                                            page_body["name"] = new_pageName if pageName_change_confirm else old_pageName
                                        else:
                                            logPrint("请输入新符文页的名称：\nPlease enter the name of the new perk page:")
                                            new_pageName = logInput()
                                            page_body["name"] = new_pageName
                                elif method[0] == "2":
                                    keystoneIds = [perk["id"] for perk in perks_initial if perk["slotType"] == "kKeyStone"] #提取基石序号列表，用于判断基石的正确性（Extract the list of keystone ids to judge the keystone's correctness）
                                    statmodIds = [perk["id"] for perk in perks_initial if perk["slotType"] == "kStatMod"] #提取属性符文序号列表，用于判断基石的正确性（Extract the list of stat mod ids to judge the keystone's correctness）
                                    perkMap = {} #建立一个由符文对应到所属符文页的对应关系，并从符文页信息中提取每个符文的槽位类型和槽位名称（Build a map from perks to the belonging perkstyles and extract each perk's slot type and slot label from perkstyle information）
                                    for style in perkstyles_initial["styles"]:
                                        for slot in style["slots"]:
                                            for perkId in slot["perks"]:
                                                perkMap[perkId] = {"styleId": perks[perkId]["styleId"], "slotType": slot["type"], "slotLabel": slot["slotLabel"]}
                                    logPrint("请输入一个由符文序号组成的列表。\nPlease input a list composed of perkIds.\n例如（Example）：[8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]")
                                    while True:
                                        uiPerksStr = logInput()
                                        if uiPerksStr == "":
                                            continue
                                        elif uiPerksStr[0] == "0":
                                            back = True
                                            break
                                        else:
                                            try:
                                                uiPerksIds = eval(uiPerksStr)
                                            except:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            else:
                                                #下面对uiPerksIds展开重重检验，确保生成的是有效的符文页（The following code perform continuous tests on `uiPerksIds` to ensure that a valid perk page will be generated）
                                                if isinstance(uiPerksIds, list) and all(map(lambda x: isinstance(x, int) and x in perks.keys(), uiPerksIds)):
                                                    if len(uiPerksIds) >= 9:
                                                        uiPerksIds = uiPerksIds[:9] #正确的请求主体中，符文序号列表长度为9。因此如果用户输入长度超过9的列表，将被自动截断（In a correct request body, the length of the perkId list is 9. Therefore, if the user submits a list with length over 9, this list will be taken a slice automatically）
                                                        perkIds_valid = True #在保证用户的输入的列表元素都是整数的情况下，对于符文序号列表的逻辑展开检验（Perform tests on the perkId list's logic, if each element of this list is of integer type）
                                                        if uiPerksIds[0] in keystoneIds: #首先判断基石的正确性（First, check the keystone correctness）
                                                            primaryStyle = perkstyles[perks[uiPerksIds[0]]["styleId"]] #在基石正确的情况下，推断出主系（If the keystone is correct, infer the primary style）
                                                            for i in range(1, 4): #判断基石后三个符文是否都能对应到主系的三个槽位（Judge whether the three perks after keystone can correspond to the three slots of the primary style, respectively）
                                                                slot = perkstyles[primaryStyle["id"]]["slots"][i]
                                                                if not uiPerksIds[i] in slot["perks"]:
                                                                    perkIds_valid = False
                                                                    logPrint("%s系的%s符文中不包含%s（%d）。\n%s (%d) doesn't exist in the %s slot of %s style." %(primaryStyle["name"], slot["slotLabel"], perks[uiPerksIds[i]]["name"], uiPerksIds[i], perks[uiPerksIds[i]]["name"], uiPerksIds[i], slot["slotLabel"], primaryStyle["name"]))
                                                            #下面检验副系的两个符文。副系的检验依赖于主系的确定，因为涉及到主系的合法副系的判断，因此这一段代码置于基石正确性判断的if条件语句块内（Second, check the correctness of two perks in the substyle. Check on the substyle depends on the confirmation of the primary style, for it involves the allowed substyle of a primary style. Therefore, the following code are under the if-statement that check the keystone correctness）
                                                            ##首先针对其所属符文系展开检验（First, perform tests on their belonging perkstyles）
                                                            if not perkMap[uiPerksIds[4]]["styleId"] in perkstyles[primaryStyle["id"]]["allowedSubStyles"]: #检验副系第一个符文所属符文系是否是主系的合法副系（Check whether the first perk of substyle is a legal substyle of the primary style）
                                                                perkIds_valid = False
                                                                logPrint("%s（%d）所属符文系（%d）不是主系%s（%d）的合法副系。\nThe belonging style (%d) of %s (%d) isn't an allowed substyle for primary style %s (%d)." %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perkMap[uiPerksIds[4]]["styleId"], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"], perkMap[uiPerksIds[4]]["styleId"], perks[uiPerksIds[4]]["name"], uiPerksIds[4], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"]))
                                                            if not perkMap[uiPerksIds[5]]["styleId"] in perkstyles[primaryStyle["id"]]["allowedSubStyles"]: #检验副系第二个符文所属符文系是否是主系的合法副系（Check whether the second perk of substyle is a legal substyle of the primary style）
                                                                perkIds_valid = False
                                                                logPrint("%s（%d）所属符文系（%d）不是主系%s（%d）的合法副系。\nThe belonging style (%d) of %s (%d) isn't an allowed substyle for primary style %s (%d)." %(perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[5]]["styleId"], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"], perkMap[uiPerksIds[5]]["styleId"], perks[uiPerksIds[5]]["name"], uiPerksIds[5], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"]))
                                                            if perkMap[uiPerksIds[4]]["styleId"] != perkMap[uiPerksIds[5]]["styleId"]:
                                                                perkIds_valid = False
                                                                logPrint("%s（%d）所属符文系（%d）和%s（%d）所属符文系（%d）不相同。\n%s (%d) and %s (%d) have different belonging perkstyles (%d and %d)." %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perkMap[uiPerksIds[4]]["styleId"], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[5]]["styleId"], perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[4]]["styleId"], perkMap[uiPerksIds[5]]["styleId"]))
                                                            ##在迄今为止副系的两个符文所属符文系合法——两个符文所属符文系相同，且是主系的合法副系——的情况下，接下来对其槽位展开检验（When the belonging perkstyles of the two substyle perks are legal, that is, these two perks belong to one style and this style is an allowed substyle of the primary style, perform tests on these two perks' slots）
                                                            if perkIds_valid: #该条件等价于（This condition is equivalent to）`perkMap[uiPerksIds[4]]["styleId"] == perkMap[uiPerksIds[5]]["styleId"] and perkMap[uiPerksIds[4]]["styleId"] in perkstyles[primaryStyle["id"]]["allowedSubStyles"]`
                                                                ##注意：在上面的符文对应关系字典中，属性符文也被包含在内。虽然会有多个符文系包含同一套属性符文的问题，但是这里只对副系的两个符文进行检验，所以该字典中关于属性符文的问题在这里是无关紧要的（Note: In the `perkMap` dictionary, stat mods are included. Despite the fact that multiple perkstyles contain a same set of stat mods, here the test is performed only on the two perks of the substyle, so the stat mod issue here is insignificant）
                                                                if perkMap[uiPerksIds[4]]["slotType"] != "kMixedRegularSplashable": #检验副系第一个符文是不是基石和属性之外的符文（Check whether the first perk of the substyle is of "kMixedRegularSplashable" type）
                                                                    perkIds_valid = False
                                                                    logPrint('''%s（%d）所属槽位类型不是符文。\nThe slot type of %s (%d) isn't "kMixedRegularSplashable".''' %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[4]]["name"], uiPerksIds[4]))
                                                                if perkMap[uiPerksIds[5]]["slotType"] != "kMixedRegularSplashable": #检验副系第二个符文是不是基石和属性之外的符文（Check whether the second perk of the substyle is of "kMixedRegularSplashable" type）
                                                                    perkIds_valid = False
                                                                    logPrint('''%s（%d）所属槽位类型不是符文。\nThe slot type of %s (%d) isn't "kMixedRegularSplashable".''' %(perks[uiPerksIds[5]]["name"], uiPerksIds[5], perks[uiPerksIds[5]]["name"], uiPerksIds[5]))
                                                                if perkMap[uiPerksIds[4]]["slotLabel"] == perkMap[uiPerksIds[5]]["slotLabel"]: #检验副系的两个符文的槽位是否相同（Check whether two slot labels of the two perks of the substyle are the same）
                                                                    perkIds_valid = False
                                                                    logPrint("%s（%d）和%s（%d）具有相同的槽位（%s）。\n%s (%d) and %s (%d) has the same slot label (%s)." %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[4]]["slotLabel"], perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[4]]["slotLabel"]))
                                                        else:
                                                            perkIds_valid = False
                                                            logPrint("%s（%d）不是基石符文。\n%s (%d) isn't a keystone." %(perks[uiPerksIds[0]]["name"], uiPerksIds[0], perks[uiPerksIds[0]]["name"], uiPerksIds[0]))
                                                        #最后检验属性符文。属性符文和主系和副系都是独立的，因此其缩进回调一个单位（Finally, check the stat mods. Stat mods are indenpendent from both primary style and substyle, so the indentation is decreased by one unit）
                                                        ##回到上面的符文对应关系字典。它具体存在的问题是，由于多个符文系都存在这些属性符文，而每个属性符文的符文系序号、槽位名称和槽位类型是由遍历符文系产生的，因此每个属性符文的这些信息都会是最后一个被遍历的符文系的这些信息。实际上，这对于后续判断也没有影响。首先，属性符文和主系和副系都是独立的，压根儿就不会用上其符文系序号这个信息。其次，虽然多个符文系包含这些属性符文，但是这些属性符文的槽位名称和槽位类型在这些符文系中是相同的，所以无论采用哪个符文系的信息都无所谓（Back to previous `perkMap` dictionary. The detailed issue is, multiple perkstyles contain these stat mods, so given that the perkstyleId, slot label and slot type of each stat mod is obtained by traversing the perkstyles, these information is actually from the perkstyle traversed. But in fact, this issue shouldn't affact the subsequent judgments. On the one hand, stat mods are indenpendent from both primary style and substyle, and their styleIds will never be regarded as useful. On the other hand, although these statmods are contained in multiple perkstyles, their slot labels and slot types recorded in the perkstyles are same, so it doesn't matter which perkstyle is used）
                                                        for i in range(6, 9):
                                                            if not uiPerksIds[i] in statmodIds: #首先判断第7～9个符文是不是属性符文（First, judge whether the 7th to 9th perks are stat mods）
                                                                perkIds_valid = False
                                                                logPrint("%s（%d）不是属性符文。\n%s (%d) isn't a stat mod." %(perks[uiPerksIds[i]]["name"], uiPerksIds[i], perks[uiPerksIds[i]]["name"], uiPerksIds[i]))
                                                            elif perkMap[uiPerksIds[i]]["slotLabel"] != perkstyles_initial["styles"][0]["slots"][i - 2]["slotLabel"]: #然后判断这些属性符文是不是对应行的。这里有两点：第一，之所以用elif不是if，是因为上面的perkMap的数据来源是符文系，而符文系相比符文少了一些符文信息，上面的判断过程也没有排除这些少的符文信息，所以如果直接用if的话，当用户输入的是这部分少的符文的序号时，会引发perkMap的键错误；第二，既然前面提到属性符文的槽位名称和槽位类型在符文系中都是相同的，所以这里直接默认使用了第一个符文系（Next, judge whether the stat mods have the corresponding slot labels. Here're two points worth mentioning. First, the reason why "elif" instead of "if" is used here is that data in the previous `perkMap` dictionary are (traversed) from perkstyles, which don't collect all perks. These extra perks aren't excluded during the previous steps, so if an "if" is used here, when the user inputs these extra perks' ids, a KeyError will occurred to `perkMap`. Second, now that slot names and slot types of stat mods in different perkstyles are the same, here the first perkstyle is used by default）
                                                                perkIds_valid = False
                                                                logPrint("%s（%d）不是%s类属性符文。\n%s (%d) isn't a stat mod of %s type." %(perks[uiPerksIds[i]]["name"], uiPerksIds[i], perkMap[uiPerksIds[i]]["slotLabel"], perks[uiPerksIds[i]]["name"], uiPerksIds[i], perkMap[uiPerksIds[i]]["slotLabel"]))
                                                        if perkIds_valid: #前面的检验都通过，则用户输入的符文序号列表是合法的（If all the previous tests are passed, then the perkId list is valid）
                                                            page_body = {"name": "", "isTemporary": isTemporary, "primaryStyleId": primaryStyle["id"], "subStyleId": perkMap[uiPerksIds[4]]["styleId"], "selectedPerkIds": uiPerksIds} #第4个和第5个符文的所属符文系是相同的，这里默认使用了第4个（The 4th and 5th perks have the same belonging perkstyles. Here the 4th's is used）
                                                            #设置符文页的名称（Set the perk page name）
                                                            pageNameChange = False
                                                            if page_exist:
                                                                old_pageName = pageName
                                                                logPrint("是否需要修改符文页名称？（输入任意键修改，否则不修改。）\nDo you want to change the page name? (Submit any non-empty string to change, or null to stop changing.)")
                                                                pageNameChange_str = logInput()
                                                                pageNameChange = bool(pageNameChange_str)
                                                                if pageNameChange:
                                                                    logPrint("请输入符文页的新名称：\nPlease enter the new name of this perk page:")
                                                            else:
                                                                pageNameChange = True
                                                                logPrint("请输入新符文页的名称：\nPlease enter the name of the new perk page:")
                                                            if pageNameChange:
                                                                while True:
                                                                    new_pageName = logInput()
                                                                    #检验符文页名称有效性的接口依赖于一个具体的符文页。这需要针对用户是否有符文页进行讨论（The endpoint to validate the page name depends on a specific perk page. This introduces the discussion about whether the user has one perk page）
                                                                    perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                                                                    dummy_page_created = False
                                                                    if len(perkPages) == 0: #如果用户没有符文页，则创建一个占位符文页。目的只是为了拿到一个具体的符文页序号（If the user doesn't have any perk page, create one. The aim is only to get a perk page id）
                                                                        dummy_page_body = {"name": "占位符文页", "isTemporary": isTemporary, "primaryStyleId": -1, "subStyleId": -1, "selectedPerkIds": [-1, -1, -1, -1, -1, -1, -1, -1, -1]}
                                                                        response = await (await connection.request("POST", "/lol-perks/v1/pages", data = dummy_page_body)).json()
                                                                        logPrint(response)
                                                                        if "errorCode" in response:
                                                                            logPrint(response)
                                                                            logPrint("符文页名称有效性验证失败。将不再验证符文页名称有效性。\nPerk page name validation failed. This name won't be validated this time.")
                                                                            break
                                                                        else:
                                                                            dummy_page_created = True
                                                                            dummy_pageId = response["id"]
                                                                            validate_body = {"id": response["id"], "name": new_pageName}
                                                                    else: #如果用户有符文页，则使用第一个符文页的序号。这不会对第一个符文页产生影响（If the user has a perk page, use the id of the first page. This won't cause any change to it）
                                                                        validate_body = {"id": perkPages[0]["id"], "name": new_pageName}
                                                                    response = await (await connection.request("PUT", "/lol-perks/v1/pages/validate", data = validate_body)).json()
                                                                    logPrint(response)
                                                                    if "errorCode" in response:
                                                                        logPrint(response)
                                                                        logPrint("符文页名称有效性验证失败。将不再验证符文页名称有效性。\nPerk page name validation failed. This name won't be validated this time.")
                                                                        break
                                                                    else:
                                                                        if response["success"]:
                                                                            logPrint("符文页名称通过验证。\nNew page name passed validation.")
                                                                            if dummy_page_created:
                                                                                response = await (await connection.request("DELETE", f"/lol-perks/v1/pages/{dummy_pageId}")).json()
                                                                                logPrint(response)
                                                                                if response != None:
                                                                                    logPrint(response)
                                                                                    logPrint("占位符文页删除失败。请自行在客户端内删除。\nDummy perk page failed to be deleted. Please delete it by yourself.")
                                                                            break
                                                                        else:
                                                                            if "DISABLED" in response["nameCheckResponse"]["errors"]:
                                                                                logPrint("不能更改。\nPage can't be renamed.")
                                                                            if "INAPPROPRIATE" in response["nameCheckResponse"]["errors"]:
                                                                                logPrint("名字不适当。\nName is inappropriate.")
                                                                            if "INVALID_CHAR" in response["nameCheckResponse"]["errors"]:
                                                                                logPrint("名字有无效字符。\nName has invalid characters.")
                                                            if page_exist:
                                                                if old_pageName != new_pageName:
                                                                    logPrint("输入任意非空字符串以确认修改，否则取消修改。\nSubmit any non-empty string to confirm changing, or null to cancel.\n旧名称（Old）：%s\n新名称（New）：%s" %(old_pageName, new_pageName))
                                                                    pageName_change_confirm_str = logInput()
                                                                    pageName_change_confirm = bool(pageName_change_confirm_str)
                                                                else:
                                                                    pageName_change_confirm = False
                                                                page_body["name"] = new_pageName if pageName_change_confirm else old_pageName
                                                            else:
                                                                page_body["name"] = new_pageName
                                                            break
                                                        else:
                                                            logPrint("您输入的符文序号列表有误！请检查您输入的符文序号列表并再试一次。\nERROR occurred in the perkId list! Please check your perkId list and try again.")
                                                    else:
                                                        logPrint("您输入的符文数量过少！请输入由9个符文序号组成的列表。\nPerk number not enough! Please submit a list composed of 9 perkIds.")
                                                else:
                                                    logPrint("您的输入格式有误！请输入一个由符文序号正整数组成的列表。\nERROR format! Please submit a list composed of perkIds of integer type.")
                                    page_edit = not back
                                elif method[0] == "3":
                                    if page_exist:
                                        old_pageName = pageName
                                        logPrint("请输入符文页的新名称：\nPlease enter the new name of this perk page:")
                                        new_pageName = logInput()
                                        if old_pageName != new_pageName:
                                            logPrint("输入任意非空字符串以确认修改，否则取消修改。\nSubmit any non-empty string to confirm changing, or null to cancel.\n旧名称（Old）：%s\n新名称（New）：%s" %(old_pageName, new_pageName))
                                            pageName_change_confirm_str = logInput()
                                            pageName_change_confirm = bool(pageName_change_confirm_str)
                                        else:
                                            pageName_change_confirm = False
                                        page_edit = pageName_change_confirm
                                        page_body = {"name": new_pageName if pageName_change_confirm else old_pageName, "isTemporary": isTemporary, "primaryStyleId": primaryPerkStyleId, "subStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                                    else:
                                        logPrint("未创建的符文页不支持该操作。\nA perk page that hasn't been created doesn't support this method.")
                                        continue
                                elif method[0] == "4":
                                    logPrint('请在单行内输入包含新符文页信息的字典或Json代码：\nPlease input a Python dictionary or a piece of Json code that represents the new perk page information in a single line:\n示例（Examples）：\nPython字典（Python dictionary）：\n{"name": "无极剑圣 - 致命节奏", "isActive": False, "isTemporary": True, "primaryStyleId": 8000, "secondaryStyleId": 8300, "selectedPerkIds": [8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]}\nJson：\n{"name": "无极剑圣 - 致命节奏", "isActive": false, "isTemporary": true, "primaryStyleId": 8000, "secondaryStyleId": 8300, "selectedPerkIds": [8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]}')
                                    while True:
                                        json_decoded = False
                                        page_body_str = logInput()
                                        if page_body_str == "":
                                            continue
                                        elif page_body_str[0] == "0":
                                            back = True
                                            break
                                        else:
                                            try:
                                                page_body = json.loads(page_body_str)
                                            except json.decoder.JSONDecodeError:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                try:
                                                    page_body = eval(page_body_str)
                                                except:
                                                    traceback_info = traceback.format_exc()
                                                    logPrint(traceback_info)
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                else:
                                                    break
                                            else:
                                                break
                                    page_edit = not back
                                elif method[0] == "5":
                                    logPrint('请输入以Json格式存储新符文页信息的文件路径。输入“0”以返回上一层。\nPlease submit the path of the file that stores the new perk page information in Json format. Submit "0" to return to the last step.')
                                    while True:
                                        page_body_path = logInput()
                                        if page_body_path == "":
                                            continue
                                        elif page_body_path == "0":
                                            back = True
                                            break
                                        else:
                                            if os.path.exists(page_body_path):
                                                logPrint("您输入的路径不存在！请重新输入。\nFile not found! Please try again.")
                                            else:
                                                try:
                                                    with open(page_body_path, "r", encoding = "utf-8") as fp:
                                                        page_body = json.load(fp)
                                                except json.decoder.JSONDecodeError:
                                                    traceback_info = traceback.format_exc()
                                                    logPrint(traceback_info)
                                                    logPrint("文件格式错误！请检查文件格式或使用其它文件。\nERROR format! Please check the file format or use another file.")
                                                else:
                                                    break
                                    page_edit = not back
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if page_edit:
                                    if page_exist:
                                        response = await (await connection.request("PUT", f"/lol-perks/v1/pages/{pageId}", data = page_body)).json()
                                        logPrint(response)
                                        if "errorCode" in response:
                                            logPrint("符文页编辑失败。\nFailed to edit this perk page.")
                                        else:
                                            logPrint("符文页编辑成功。\nPerk page is edited successfully.")
                                    else:
                                        response = await (await connection.request("POST", "/lol-perks/v1/pages", data = page_body)).json()
                                        logPrint(response)
                                        if "errorCode" in response:
                                            logPrint("符文页创建失败。\nFailed to add this perk page.")
                                        else:
                                            logPrint("符文页创建成功。\nPerk page is added successfully.")
                                    if not "errorCode" in response:
                                        pageId = response["id"]
                                        pageName = response["name"]
                                        primaryPerkStyleName = response["primaryStyleName"]
                                        primaryPerkStyleId = response["primaryStyleId"]
                                        secondaryPerkStyleName = response["secondaryStyleName"]
                                        secondaryPerkStyleId = response["subStyleId"]
                                        keystoneId = response["pageKeystone"]["id"]
                                        keystoneName = response["pageKeystone"]["name"]
                                        perkIds = response["selectedPerkIds"]
                                        perkNames = list(map(lambda x: x["name"], response["uiPerks"]))
                                        logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
                                    break
                                logPrint("请选择编辑方式：\nPlease select a method of:\n0\t放弃修改（Quit editing）\n1\t逐个修改（Successively）\n2\t批量修改（In batch）\n3\t仅重命名（Rename only）\n4\t读取Json数据（From json data）\n5\t读取文件（From a file）")
                        if page_exist or page_edit and not "errorCode" in response:
                            logPrint("是否导出该符文页？（输入任意键以确认，否则放弃导出。）\nDo you want to export this perk page? (Submit any non-empty string to confirm, or null to decline exporting.)")
                            page_export_str = logInput()
                            page_export = bool(page_export_str)
                            if page_export:
                                perkPage_json = {"name": pageName, "isTemporary": isTemporary, "primaryStyleId": primaryPerkStyleId, "secondaryStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                                logPrint("请选择导出方式：\nPlease select a way to export:\n1\t写入文件（Write into a file）\n2\t复制到剪贴板（Copy to clipboard）")
                                while True:
                                    export_method = logInput()
                                    if export_method == "":
                                        continue
                                    elif export_method[0] == "0":
                                        break
                                    elif export_method[0] == "1":
                                        json2name = "MyPage.json"
                                        with open(json2name, "w", encoding = "utf-8") as fp:
                                            json.dump(perkPage_json, fp, ensure_ascii = False)
                                        logPrint('符文页“%s”（%d）已导出到同目录下的“%s”中。\nPage "%s" (%d) has been exported into "%s" under the same folder.\n' %(pageName, pageId, json2name, pageName, pageId, json2name))
                                        break
                                    elif export_method[0] == "2":
                                        pyperclip.copy(perkPage_json)
                                        logPrint('符文页“%s”（%d）已复制到剪贴板中。\nPage "%s" (%d) has been copied to clipboard.\n' %(pageName, pageId, pageName, pageId))
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        break
                elif action[0] == "3":
                    perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                    if len(perkPages) == 0:
                        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
                    else:
                        if not any(map(lambda x: x["isActive"], perkPages)):
                            logPrint("符文页活动性无法正常显示。请确保您目前处于涉及符文配置的游戏模式的英雄选择阶段。\nPerk page activity doesn't display right now. Please make sure you're during the champ select stage of a game mode that involves perk configuration.")
                        logPrint("您的符文页活动性信息如下：\nPerk page activity is as follows:")
                        perkPage_df = await get_perk_page(connection)
                        print(format_df(perkPage_df.loc[:, ["name", "isActive", "isValid", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]], print_index = True)[0])
                        log.write(format_df(perkPage_df.loc[:, ["name", "isActive", "isValid", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                        logPrint("请选择您想要使用的符文页：\nPlease select a perk page to use:")
                        while True:
                            pageIndex = logInput()
                            if pageIndex == "":
                                continue
                            elif pageIndex == "0":
                                break
                            else:
                                try:
                                    pageIndex = int(pageIndex)
                                except ValueError:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if pageIndex >= 1 and pageIndex < len(perkPage_df):
                                        pageId = perkPage_df.loc[pageIndex, "id"]
                                        pageName = perkPage_df.loc[pageIndex, "name"]
                                        isTemporary = perkPage_df.loc[pageIndex, "isTemporary"] == "√"
                                        primaryPerkStyleName = perkPage_df.loc[pageIndex, "primaryStyleName"]
                                        primaryPerkStyleId = perkPage_df.loc[pageIndex, "primaryStyleId"]
                                        secondaryPerkStyleName = perkPage_df.loc[pageIndex, "secondaryStyleName"]
                                        secondaryPerkStyleId = perkPage_df.loc[pageIndex, "subStyleId"]
                                        keystoneId = perkPage_df.loc[pageIndex, "pageKeystone id"]
                                        keystoneName = perkPage_df.loc[pageIndex, "pageKeystone name"]
                                        perkIds = perkPage_df.loc[pageIndex, "selectedPerkIds"]
                                        perkNames = perkPage_df.loc[pageIndex, "uiPerksNames"]
                                        page_body = {"name": pageName, "isTemporary": isTemporary, "primaryStyleId": primaryPerkStyleId, "subStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                                        response = await (await connection.request("PUT", f"/lol-perks/v1/pages/{pageId}", data = page_body)).json()
                                        logPrint(response)
                                        if "errorCode" in response:
                                            logPrint("符文页活动性设置失败。\nFailed to set the selected page active.")
                                        else:
                                            logPrint("已选择的符文页：%s（%d）\nSelected perk page: %s (%d)" %(pageName, pageId, pageName, pageId))
                                            logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                elif action[0] == "4":
                    perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json() #排序过程容易牵一发而动全身地出现问题，因此尽可能还是保证符文页信息是最新的（One problem may bring about cascade effects during ordering, so the program had better keep the perk page information latest）
                    if len(perkPages) == 0:
                        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
                    else:
                        perkPage_df = await get_perk_page(connection)
                        pageIds = list(map(lambda x: x["id"], perkPages))
                        current_pageOrder_list = list(perkPage_df.loc[1:].sort_values(by = "order", ascending = True)["id"])
                        logPrint('''请输入一个您期望的符文页序号排列顺序列表，排在前面的代表显示在前，排在后面的代表显示在后。例如，如果想恢复您当前的排序，您可以输入“%s”。\nPlease input a perk page id order list, where the page whose pageId is in the front of pageId list will be moved in the front of the page list, and vice versa. For example, if you'd like to recover the current page order, you may input "%s".''' %(current_pageOrder_list, current_pageOrder_list))
                        print(format_df(perkPage_df.loc[:, ["id", "name", "order", "primaryStyleName", "secondaryStyleName"]])[0])
                        log.write(format_df(perkPage_df.loc[:, ["id", "name", "order", "primaryStyleName", "secondaryStyleName"]], width_exceed_ask = False, direct_print = False)[0] + "\n")
                        while True:
                            page_order = logInput()
                            if page_order == "":
                                continue
                            elif page_order[0] == "0":
                                break
                            else:
                                try:
                                    page_order = eval(page_order)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
                                else:
                                    if isinstance(page_order, list) and all(map(lambda x: isinstance(x, int) and x in pageIds, page_order)) and len(page_order) == len(set(page_order)): #这里需要严格控制输入格式：①输入的是一个列表；②列表的元素全是整型，且都是分组序号；③列表元素无重复（Here the input format are strictly controlled: ①the input is a list; ②each element in the list is of integer type and represents a group id; ③the elements are unique）
                                        for pageId in page_order:
                                            pageIds.remove(pageId)
                                        page_order += pageIds #虽然用户可能只是想把个别符文页移到前面，但是后面的操作涉及到调整位次，所以还是需要对所有符文页都进行操作。这样，如果用户输入的是一个空列表，那么表面上看起来程序没有作任何操作，而实际上程序调整了所有位次的数值（Although the user may only want to move several pages to the front, the subsequent operations involve all page orders' value adjustment. In that means, if the user submits an empty list, then it seems that the program doesn't do anything, but actually adjusts all orders' values）
                                        #除了排序以外，本程序尽量控制位次的大小，规定排在第一的符文页的位次是1，排在第二的符文页的位次是2，依此类推（Aside from ordering, this program also aims at controlling the value of orders: the first page's order is 1, the second page's order is 2, and so on）
                                        #排序算法：先将所有符文页的位次设置为大于总符文页数量的整数，然后对排在第一的符文页关于其自身做当前位次减1的前移，后面的符文页分别关于排在第一的符文页做从1开始递增数值的后移（Ordering algorithm: Set orders of all pages to integers greater than the total number of pages, then perform a negative offset whose absolute value equals the current order minus 1 towards the page to be ordered in the first place, and perform a positive offset whose absolute value increments starting from 1 towards each of its successor pages）
                                        perkPages = sorted(perkPages, key = lambda x: x["order"], reverse = True) #对符文页作关于位次的降序排列（Arrange the pages in the descending order of "order"）
                                        for page in perkPages:
                                            body = {"targetPageId": page["id"], "destinationPageId": page["id"], "offset": len(perkPages) + abs(perkPages[-1]["order"])} #为了避免可能的位次冲突，在准备阶段，尽可能保证所有符文页的偏移量是定值。考虑到有些符文页的位次可能是负数，这里的偏移量带上了符文页最小位次的绝对值，这样能保证所有符文页经过这个for循环之后位次的值大于总符文页数量的整数，且保持原有顺序（To avoid possible order conflicts, the offset of each move should be constant during preparation. Considering some orders may be negative, here the offset is added the absolute value of the smallest order. In this way, orders of all pages will be greater than the total number of perk pages after this for-loop and obey the original order）
                                            response = await (await connection.request("POST", "/lol-perks/v1/update-page-order", data = body)).json()
                                            logPrint(response)
                                            if response != None:
                                                logPrint('准备阶段移动“%s”（%d）的过程出现了问题。\nAn error occurred when the program was moving "%s" (%d) during preparation.' %(page["name"], page["id"], page["name"], page["id"]))
                                        #即使准备阶段出现了问题，实际排序时也不会发生错误。下面的注释会证明这一点（Although errors may occur during preparation, this doesn't make any difference to the actual ordering process. The following comments prove it）
                                        perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                                        perkPages_dict = {page["id"]: page for page in perkPages} #虽然其实可以从上面的公式中推导出下面的偏移量，但如果上面移动的过程出现了问题，这个办法就行不通了（Although the following offset can be inferred from the above calculation, if an error occurs, this solution won't work）
                                        error_occurred_perkPageArrange = False
                                        #首先把排在第一的符文页的位次置为1（First, set the order of the first perk page as 1）
                                        body = {"targetPageId": page_order[0], "destinationPageId": page_order[0], "offset": 1 - perkPages_dict[page["id"]]["order"]} #在准备阶段，如果是排在第一的符文页移动出现问题，那么在这里移动后位次一定是1；如果是排在第二的符文页移动出现了问题，导致经过准备阶段排在第二的符文页的位次是1，那么经过这次操作，排在第二的符文页的位次变成`2 - perkPages_dict[page["id"]]["order"]`（During preparation, if an error occurred when the program was moving the first page, then after this move, its order must be 1; otherwise, if an error occurred when the program was moving the second page, and therefore after the preparation, the second page's order became 1, then after this move, the second page's order becomes `2 - perkPages_dict[page["id"]]["order"]`）
                                        response = await (await connection.request("POST", "/lol-perks/v1/update-page-order", data = body)).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint('符文页“%s”（%d）的位次已置为1。\nPage "%s" (%d) order set to 1.' %(perkPages_dict[page_order[0]]["name"], page_order[0], perkPages_dict[page_order[0]]["name"], page_order[0]))
                                        else:
                                            error_occurred_perkPageArrange = True
                                        #排在后面的符文页关于排在第一的符文页作递增偏移量的移动（The successor pages move by an incrementing offset to the first page）
                                        for i in range(1, len(page_order)):
                                            body = {"targetPageId": page_order[i], "destinationPageId": page_order[0], "offset": i} #在准备阶段，如果是排在第i + 1的符文页移动出现问题，那么在这里移动后位次一定是i + 1；如果是排在第i + 2的符文页移动出现了问题，导致经过准备阶段排在第i + 2的符文页的位次位于1和i + 1之间，那么经过这次操作，排在第i + 2的符文页的位次应当位于i + 1和2i + 1之间，这样就不会对前面i - 1个符文页的顺序产生影响（During preparation, if an error occurred when the program was moving the (i + 1)th page, then after this move, its order must be (i + 1); otherwise, if an error occurred when the program was moving the (i + 2)th page, and therefore the after the preparation, the (i + 2)th page's order is between 1 and i + 1, then after this move, the (i + 2)th page's order should be within (i + 1) and (2i + 1), which makes no difference to the order of the first (i - 1) pages）
                                            response = await (await connection.request("POST", "/lol-perks/v1/update-page-order", data = body)).json()
                                            logPrint(response)
                                            if response == None:
                                                logPrint('符文页“%s”（%d）的位次已置为%d。\nPage "%s" (%d) order set to %d.' %(perkPages_dict[page_order[i]]["name"], page_order[i], i + 1, perkPages_dict[page_order[i]]["name"], page_order[i], i + 1))
                                            else:
                                                error_occurred_perkPageArrange = True
                                        #这样一看，你是不是发现前面的准备阶段完全没有必要（Above all, do you realize that the preparation is totally unnecessary）
                                        if error_occurred_perkPageArrange:
                                            logPrint("排序过程发生了异常。请等待客户端符文页顺序稳定后手动排序。\nAn error occurred during ordering. Please order manually after the order of the perk pages becomes stable.")
                                        else:
                                            logPrint("排序完成。\nOrder success.")
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                elif action[0] == "5":
                    perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                    if len(perkPages) == 0:
                        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
                    else:
                        logPrint('请输入要删除的符文页的索引：\nPlease submit the index of the page(s) to delete:\n变量提示（Variable hint）：\nperkPage_df = await get_perk_page(connection)\n示例（Examples）：\n1 #删除数据框索引为1的符文页（Delete the page whose index in the dataframe is 1）\n[1, 2, 3] #删除数据框索引为1、2和3的符文页（Delete the pages whose indices in the dataframe are 1, 2 and 3, respectively）\nall #删除所有符文页（Delete all pages）\n[i for i in range(1, len(perkPage_df)) if perkPage_df.loc[i, "isTemporary"]] #删除所有临时符文页（Delete all temporary pages）\nlist(perkPage_df[perkPage_df["pageKeystone id"] == 8010].index) #删除所有基石序号是8010的符文页（Delete all pages whose keystone id is 8010）\nlist(perkPage_df.iloc[1:, :][(~(perkPage_df.iloc[1:, :]["pageKeystone name"].isin["征服者", "致命节奏"]) | (perkPage_df.iloc[1:, :]["recommendationChampionId"] == 11)) & (perkPage_df.iloc[1:, :]["secondaryStyleName"] == "启迪")].index) #删除所有基石不是征服者也不是致命节奏，或者推荐英雄序号是11，且副系是启迪系的符文页（Delete all pages whose keystone is neither Conqueror nor Lethal Tempo, or recommended champion id is 11, and the secondary perkstyle is Inspiration）')
                        while True:
                            index_got = False
                            delete_str = logInput()
                            if delete_str == "":
                                continue
                            elif delete_str == "0":
                                break
                            elif delete_str == "all":
                                delete_indices = list(range(1, len(perkPage_df)))
                            else:
                                try:
                                    delete_indices = eval(delete_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(delete_indices, int):
                                        delete_indices = [delete_indices]
                                    elif not isinstance(delete_indices, list):
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                            if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(perkPage_df), delete_indices)) and len(delete_indices) == len(set(delete_indices)):
                                index_got = True
                                break
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if index_got:
                            logPrint("您选择删除以下%d个符文页。\nYou selected the following %d perk page(s)." %(len(delete_indices), len(delete_indices)))
                            print(format_df(perkPage_df.loc[delete_indices, perkPage_df_fields_to_print], print_index = True, reserve_index = True)[0])
                            log.write(format_df(perkPage_df.loc[delete_indices, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                            logPrint("请输入任意非空字符串以继续删除，否则取消删除。\nPlease submit any non-empty string to continue deleting, or null to cancel.")
                            delete_confirm_str = logInput()
                            delete_confirm = bool(delete_confirm_str)
                            if delete_confirm:
                                for delete_index in delete_indices:
                                    pageId = perkPage_df.loc[delete_index, "id"]
                                    pageName = perkPage_df.loc[delete_index, "name"]
                                    response = await (await connection.request("DELETE", f"/lol-perks/v1/pages/{pageId}")).json()
                                    logPrint(response)
                                    if response == None:
                                        logPrint(f"已删除的符文页（Deleted page）：{pageName}（{pageId}）")
                                    else:
                                        logPrint(f'符文页“{pageName}”（{pageId}）删除失败。\nPage "{pageName}" ({pageId}) failed to be deleted.')
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("您的符文页信息如下：\nYour perk pages are listed below:")
                perkPage_df = await get_perk_page(connection)
                perkPage_df_fields_to_print = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
                print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                logPrint("请选择一个操作：\nPlease select an action:\n0\t返回上一层（Return to the last step）\n1\t导出所有符文页（Export all pages）\n2\t查看、编辑和导出一个符文页（Check, edit and export a page）\n3\t切换活动符文页（Toggle active perk page）\n4\t排序符文页（Order perk pages）\n5\t删除符文页（Delete perk pages）")

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await configure_perks(connection)
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
