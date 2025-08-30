from lcu_driver import Connector
import copy, json, os, pandas, re, shutil, time, traceback, unicodedata, uuid, _io
from urllib.parse import quote, unquote, urljoin
from wcwidth import wcswidth

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

log_folder = "日志（Logs）/Customized Program 16 - Friend and Blacklist Management"
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
# 通用函数（Generic functions）
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

#-----------------------------------------------------------------------------
# 好友管理（Friend management）
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

def patch_compare(patch1, patch2): #比较两个版本号的先后顺序。当patch1 < patch2时，返回True，否则返回False。用于比较DataDragon数据库中未收录的版本和收录的最新版本的关系。如果未收录的版本小于收录的最新版本，那么该版本是美测服的临时版本，后来被合并更新了，如正式服将13.2和13.3合并更新了，因此DataDragon数据库中未收录13.2版本的数据；如果未收录的版本大于收录的最新版本，那么该版本是美测服的当前版本，但是仍处于开发状态，尚未完全确定，所以DataDragon数据库尚未收录，将以最新版本代替该版本；二者不可能相等，因为如果相等的话，就不会引发报错而调用此函数（Compare the time order of two patches. When patch1 < patch2, return True and vice versa. Designed to compare a patch not archived in DataDragon database with the latest patch archived in DataDragon database. If the unarchived patch is less than the latest archived patch, then this patch must be the intermediate patch and be merged into the update of its successive patch, such as Patch 13.2 merged into the update of Patch 13.3, so that DataDragon database doesn't archive the data of Patch 13.2; If the unarchived patch is greater than the latest archived patch, then this patch must be the current patch on PBE but is under development and improvement, so that DataDragon database doesn't archive this patch, either, in which case the latest patch will be used to substitute this unarchived patch; The two patches can't be the same, for suppose they're same, then the error to cause the call of this function won't be triggered）
    if not isinstance(patch1, str):
        patch1 = str(patch1)
    if not isinstance(patch2, str):
        patch2 = str(patch2)
    lst1, lst2 = patch1.split("."), patch2.split(".")
    try:
        lst1 = list(map(int, lst1))
    except ValueError:
        if lst1[0] != "pbe":
            print("第1个版本字符串不合法！请输入用半角句号连接的正整数，如13.15.1、10.10.3216176。\nThe first patch variable is illegal! Please pass the integers concatenated by dot, such as 13.15.1 and 10.10.3216176.")
        return False
    try:
        lst2 = list(map(int, lst2))
    except ValueError:
        if lst1[0] != "pbe":
            print("第2个版本字符串不合法！请输入用半角句号连接的正整数，如13.15.1、10.10.3216176。\nThe second patch variable is illegal! Please pass the integers concatenated by dot, such as 13.15.1 and 10.10.3216176.")
            return False
        else:
            return True
    for i in range(min(len(lst1), len(lst2))):
        if lst1[i] < lst2[i]:
            return True
        elif lst1[i] > lst2[i]:
            return False
        else:
            continue
    if len(lst1) < len(lst2):
        return True
    else:
        return False #这里将两个版本相同视为假，暗示了在本程序用得到的地方，两个版本不可能相同（Here the case where the two patches are the same is regarded as False, which indicates that the two patches can't be same within its use in this program）

def aInput() -> str: #高级输入模式（Advanced input mode）
    text = ""
    count = 0
    while True:
        try:
            s = input()
        except EOFError: #Jupyter中只输入Ctrl-D会引发报错（A single Ctrl-D character in jupyter will trigger an exception of the input function）
            break
        if count > 0 and not s == chr(4):
            text += "\n"
        count += 1
        if s.endswith(chr(4)): #以Ctrl-D结束
            text += s[:-1]
            break
        else:
            text += s
    return text

def subscope(scope: dict = {}):
    s = copy.deepcopy(scope)
    while True:
        expr = logInput()
        tokens = expr.split() #去除空格的词法分析（Parse by spliting by space）
        if expr == "-1":
            break
        elif expr == "0":
            s = copy.deepcopy(scope)
            logPrint("变量和作用域已复位。\nVariables and the scope have been reset.")
        else:
            try:
                exec(expr, s)
            except:
                traceback_info = traceback.format_exc()
                logPrint(traceback_info)
    return 0

def verify_uuid(s: str) -> bool:
    try:
        return s == str(uuid.UUID(s))
    except ValueError:
        return False

async def sort_friend_hovercard(connection):
    #下面准备一些数据资源（Prepare some data resources）
    ##自己的信息（Self info）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    ##好友悬停卡信息（Friend hovercard）
    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    ##召唤师图标（Summoner icon）
    summonerIcons_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {}
    for icon in summonerIcons_source:
        summonerIcons[icon["id"]] = icon
    ##旗帜（Regalia banner）
    regaliaBanners = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_BANNER")).json()
    ##成就（Challenge）
    challenges = await (await connection.request("GET", "/lol-game-data/assets/v1/challenges.json")).json()
    ##英雄（LoL champion）
    LoLChampions_source = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
    LoLChampions = {}
    for champion in LoLChampions_source:
        LoLChampions[champion["id"]] = champion
    ##小小英雄（Companion）
    TFTCompanions_source = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
    TFTCompanions = {}
    for companion in TFTCompanions_source:
        TFTCompanions[companion["itemId"]] = companion
    ##云顶之弈攻击特效（Damage skin）
    TFTDamageSkins_source = await (await connection.request("GET", "/lol-game-data/assets/v1/tftdamageskins.json")).json()
    TFTDamageSkins = {}
    for damageSkin in TFTDamageSkins_source:
        TFTDamageSkins[damageSkin["itemId"]] = damageSkin
    ##游戏队列（Game queue）
    queues_source = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    queues = {}
    for queue in queues_source:
        queues[queue["id"]] = queue
    ##云顶之弈棋盘皮肤（TFT map skin）
    TFTMapSkins_source = await (await connection.request("GET", "/lol-game-data/assets/v1/tftmapskins.json")).json()
    TFTMapSkins = {}
    for mapSkin in TFTMapSkins_source:
        TFTMapSkins[mapSkin["itemId"]] = mapSkin
    ##头衔（Title）
    titles = await (await connection.request("GET", "/lol-challenges/v2/titles/all")).json()
    ##皮肤（Champion skin）
    championSkins_source = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
    championSkins = {}
    for skin in championSkins_source.values():
        championSkins[skin["id"]] = skin
        if "chromas" in skin:
            for chroma in skin["chromas"]:
                championSkins[chroma["id"]] = chroma
        if "questSkinInfo" in skin:
            for tier in skin["questSkinInfo"]["tiers"]:
                if not tier["id"] in championSkins: #圣堂皮肤和终极皮肤中的系列与主皮肤存在重复的序号（There're redundant ids between the tier and the parent ultimate skin）
                    championSkins[tier["id"]] = tier
    #定义好友数据结构（Define the friend hovercard data structure）
    friend_hovercard_header = {"availability": "可用性", "displayGroupId": "分组显示序号", "displayGroupName": "分组显示名", "gameName": "玩家昵称", "gameTag": "昵称编号", "groupId": "分组序号", "groupName": "分组名称", "icon": "召唤师图标序号", "id": "服务器序号", "isP2PConversationMuted": "私聊已静音", "lastSeenOnlineTimestamp": "上次离线时间戳", "name": "显示名", "note": "备注", "patchline": "版本线", "pid": "社交代码", "platformId": "服务器代码", "product": "产品代码", "productName": "产品名", "puuid": "玩家通用唯一识别码", "statusMessage": "自定义状态信息", "summary": "摘要", "summonerId": "召唤师序号", "time": "登录时间戳", "icon title": "召唤师图标名称", "icon imagePath": "召唤师图标路径", "lastSeenOnlineTime": "上次离线时间", "loginTime": "登录时间", "bannerIdSelected": "所选旗帜序号", "challengeCrystalLevel": "成就等级", "challengePoints": "总成就数", "challengeTokensSelected": "选用勋章序号", "championId": "选用英雄序号", "companionId": "选用小小英雄序号", "damageskinId": "选用云顶之弈攻击特效序号", "gameId": "当前对局序号", "gameMode": "当前游戏模式", "gameQueueType": "当前队列类型", "gameStatus": "游戏状态", "iconOverride": "头像重载情况", "isObservable": "可观战范围", "legendaryMasteryScore": "成就积分", "level": "召唤师等级", "mapId": "当前游戏地图序号", "mapSkinId": "当前棋盘皮肤序号", "playerTitleSelected": "选用头衔序号", "profileIcon": "召唤师图标序号", "queueId": "当前队列序号", "rankedLeagueDivision": "段位分级", "rankedLeagueQueue": "段位队列", "rankedLeagueTier": "段位", "rankedLosses": "排位负场", "rankedPrevSeasonDivision": "过往赛季段位分级", "rankedPrevSeasonTier": "过往赛季段位", "rankedSplitRewardLevel": "赛段奖励等级", "rankedWins": "排位胜场", "skinVariant": "选用（炫彩）皮肤序号", "skinname": "选用皮肤名称", "timestamp": "登录时间戳", "banner assetPath": "所选旗帜图标路径", "banner localizedName": "所选旗帜名称", "challengeTokenNamesSelected": "选用勋章名称", "champion name": "选用英雄名称", "champion alias": "选用英雄代号", "champion squarePortraitPath": "选用英雄方块头像路径", "companion contentId": "选用小小英雄商品编号", "companion name": "选用小小英雄名称", "companion loadoutsIcon": "选用小小英雄预览图", "companion level": "选用小小英雄星级", "companion speciesName": "选用小小英雄物种", "companion speciesId": "选用小小英雄物种序号", "companion rarity": "选用小小英雄品质", "companion rarityValue": "选用小小英雄稀有度", "damageskin contentId": "选用云顶之弈攻击特效商品编号", "damageskin name": "选用云顶之弈攻击特效名称", "damageskin loadoutsIcon": "选用云顶之弈攻击特效预览图路径", "damageskin groupId": "选用云顶之弈攻击特效分组序号", "damageskin groupName": "选用云顶之弈攻击特效组别", "damageskin rarity": "选用云顶之弈攻击特效品质", "damageskin rarityValue": "选用云顶之弈攻击特效品质得分", "damageskin level": "选用云顶之弈攻击特效等级", "gameModeName": "当前游戏模式名称", "mapSkin contentId": "棋盘皮肤商品编号", "mapSkin name": "棋盘皮肤名称", "mapSkin loadoutsIcon": "棋盘皮肤预览图", "mapSkin groupId": "棋盘皮肤分组序号", "mapSkin groupName": "棋盘皮肤组别", "mapSkin rarity": "棋盘皮肤品质", "mapSkin rarityValue": "棋盘皮肤稀有度", "playerTitle name": "头衔名称", "playerTitle titleAcquisitionName": "头衔获取名称", "playerTitle titleAcquisitionType": "头衔获取途径", "playerTitle titleRequirementDescription": "头衔获取要求", "skinVariant contentId": "选用（炫彩）皮肤商品编号", "skinVariant name": "选用（炫彩）皮肤名称", "skinVariant splashPath": "选用（炫彩）皮肤插画路径", "skinVariant uncenteredSplashPath": "选用（炫彩）皮肤原画路径", "skinVariant tilePath": "选用（炫彩）皮肤方块图像路径", "skinVariant loadScreenPath": "选用（炫彩）皮肤经典加载界面", "skinVariant loadScreenVintagePath": "选用（炫彩）皮肤带边框加载界面", "skinVariant rarity": "选用（炫彩）皮肤品质", "skinVariant splashVideoPath": "选用（炫彩）皮肤视频路径", "skinVariant chromaPath": "选用（炫彩）皮肤炫彩路径", "pty maxPlayers": "小队最大玩家数量", "pty partyId": "小队序号", "pty queueId": "小队队列序号", "pty summoners": "小队召唤师序号", "pty summonerNames": "小队召唤师名", "regalia bannerType": "旗帜类型", "regalia crestType": "徽章类型", "regalia selectedPrestigeCrest": "选用至臻徽章序号"}
    friend_hovercard_data = {}
    friend_hovercard_header_keys = list(friend_hovercard_header.keys())
    for i in range(len(friend_hovercard_header_keys)):
        key = friend_hovercard_header_keys[i]
        friend_hovercard_data[key] = []
    #下面定义一些常量字典（Define some constant dictionaries）
    availabilities = {"available": "可用", "away": "离开", "championSelect": "英雄选择", "chat": "在线", "dnd": "游戏中", "hostingCoopVsAIGame": "正创建人机对战", "hostingFeaturedGame": "正创建特殊模式", "hostingNormalGame": "正创建匹配模式", "hostingPracticeGame": "正创建自定义游戏", "hostingRankedGame": "创建排位赛", "hosting_ARAM_UNRANKED_5x5": "正创建匹配模式", "hosting_BOT": "正创建人机对战", "hosting_BOT_3x3": "正创建人机对战", "hosting_CHERRY": "正创建斗魂竞技场", "hosting_RIOTSCRIPT_BOT": "正创建人机对战", "hosting_Custom": "正创建自定义游戏", "hosting_NEXUSBLITZ": "正创建极限闪击", "hosting_NORMAL": "正创建匹配模式", "hosting_NORMAL_3x3": "正创建匹配模式", "hosting_NORMAL_TFT": "正创建云顶之弈对局", "hosting_PRACTICETOOL": "正创建训练模式", "hosting_RANKED_FLEX_SR": "正创建排位对局", "hosting_RANKED_FLEX_TT": "正创建排位对局", "hosting_RANKED_SOLO_5x5": "正创建排位对局", "hosting_RANKED_TEAM_5x5": "正创建排位对局", "hosting_RANKED_TFT": "正创建云顶之弈对局", "hosting_RANKED_TFT_TURBO": "正创建云顶之弈对局", "hosting_RANKED_TFT_PAIRS": "正创建双人作战对局", "hosting_RANKED_TFT_DOUBLE_UP": "正创建双人作战", "hosting_STRAWBERRY": "正创建【无尽狂潮】对局", "hosting_CHONCC_TREASURE_TFT": "正创建云顶之弈对局", "hosting_LNY23_TFT": "正创建云顶之弈对局", "hosting_LNY24_TFT": "正创建云顶之弈对局", "hosting_LNY25_TFT": "正在创建云顶之弈对局", "hosting_SET_REVIVAL_5_5_TFT": "正在创建云顶之弈对局", "hosting_FIVE_YEAR_ANNIVERSARY_TFT": "正在创建云顶之弈对局", "hosting_SF_TFT": "正创建云顶之弈对局", "hosting_PVE_PUZZLE_TFT": "正创建云顶之弈对局", "hosting_featured": "正创建特殊模式", "inGame": "游戏中", "inQueue": "队列中", "inTeamBuilder": "阵容匹配中", "map_hosting_ARAM_UNRANKED_5x5": "正创建匹配模式（进步之桥）", "map_hosting_NORMAL": "正创建匹配模式（召唤师峡谷）", "map_hosting_NORMAL_3x3": "正创建匹配模式（扭曲丛林）", "map_hosting_RANKED_FLEX_SR": "正创建灵活排位（召唤师峡谷）", "map_hosting_RANKED_FLEX_TT": "正创建灵活排位（扭曲丛林）", "mobile": "在线分组", "offline": "离线", "online": "在线", "spectating": "正在观战中", "teamSelect": "正在选择队伍", "tutorial": "正在新手教程中", "undefined": "待定……", "watchingReplay": "正在观看回放", "outOfGame": "在线"} #来源（Source）：plugins/rcp-fe-lol-social/global/zh_cn
    challengeCrystalLevels = {"": "", "IRON": "黑铁阶", "BRONZE": "黄铜阶", "SILVER": "白银阶", "GOLD": "黄金阶", "PLATINUM": "铂金阶", "EMERALD": "翡翠阶", "DIAMOND": "钻石阶", "MASTER": "大师阶", "GRANDMASTER": "宗师阶", "CHALLENGER": "王者阶"}
    tiers = {"": "", "NONE": "没有段位", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    ratedTiers = {"": "", "NONE": "没有段位", "GRAY": "灰白", "GREEN": "翠绿", "BLUE": "天蓝", "PURPLE": "绛紫", "ORANGE": "耀橙"}
    tiers_all = tiers | ratedTiers
    rarities = {"Default": "默认", "Common": "常规", "Epic": "史诗", "Legacy": "限定", "Legendary": "传说", "Mythic": "神话", "Rare": "稀有", "Ultimate": "终极", "Exalted": "圣者至尊", "Transcendant": "超凡"} #来源（Reference）：plugins/rcp-fe-lol-loot/global/zh_cn、plugins/rcp-fe-lol-shared-components/global/zh_cn
    spectatorPolicies = {"ALL": "所有人", "FRIENDONLY": "只允许好友", "LOBBYONLY": "只允许房间内玩家", "NONE": "无"}
    titleAcquisitionTypes = {"DEFAULT": "默认", "CHALLENGE": "成就", "CHAMPION_MASTERY": "英雄成就", "EVENT": "事件"}
    krarities = {"kNoRarity": "其它", "kExalted": "圣堂级", "kEpic": "史诗", "kLegendary": "传说", "kMythic": "神话", "kRare": "稀有", "kUltimate": "终极", "kTranscendent": "卓越"}
    #数据整理核心部分（Data assignment - core part）
    for friend in friends:
        for i in range(len(friend_hovercard_header_keys)):
            key = friend_hovercard_header_keys[i]
            if i <= 26:
                if i == 0: #可用性（`availability`）
                    friend_hovercard_data[key].append(availabilities[friend[key]])
                elif i == 23 or i == 24: #非直接导入的召唤师图标相关键（Not directly imported `icon`-related keys）
                    friend_hovercard_data[key].append(summonerIcons[friend["icon"]].get(key.split(" ")[1], "") if friend["icon"] in summonerIcons else "")
                elif i == 25: #上次离线时间（`lastSeenOnlineTime`）
                    if friend["lastSeenOnlineTimestamp"] == None:
                        friend_hovercard_data[key].append("")
                    else:
                        friend_hovercard_data[key].append(friend["lastSeenOnlineTimestamp"])
                elif i == 26: #登录时间（`loginTime`）
                    if friend["time"] == 0:
                        friend_hovercard_data[key].append("")
                    else:
                        friend_hovercard_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(friend["time"] // 1000)))
                else:
                    friend_hovercard_data[key].append(friend[key])
            elif i <= 101:
                if friend["lol"] == {}:
                    friend_hovercard_data[key].append("")
                else:
                    lol = friend["lol"]
                    if i in {27, 29, 31, 32, 33, 34, 40, 41, 42, 43, 45, 46, 50, 53, 54, 55, 57}: #正整数被转化为字符串的值的键（Keys whose values are originally integers but transformed into strings）
                        friend_hovercard_data[key].append("" if not key in lol or lol[key] == "" else int(lol[key]))
                    elif i == 28: #成就等级（`challengeCrystalLevel`）
                        friend_hovercard_data[key].append("" if not key in lol else challengeCrystalLevels[lol[key]])
                    elif i == 30: #选用勋章序号（`challengeTokensSelected`）
                        friend_hovercard_data[key].append("" if not key in lol else eval("[%s]" %(lol[key])))
                    elif i == 37: #游戏状态（`gameStatus`）
                        friend_hovercard_data[key].append("" if not key in lol else availabilities[lol[key]])
                    elif i == 39: #可观战范围（`isObservable`）
                        friend_hovercard_data[key].append("" if not key in lol else spectatorPolicies[lol[key]])
                    elif i == 47 or i == 51: #段位分级相关键（Division-related keys）
                        friend_hovercard_data[key].append("" if not key in lol or lol[key] == "NA" else lol[key])
                    elif i == 49 or i == 52: #段位相关键（Tier-related keys）
                        friend_hovercard_data[key].append("" if not key in lol else tiers[lol[key]])
                    elif i == 58 or i == 59: #旗帜相关键（Banner-related keys）
                        if "bannerIdSelected" in lol and lol["bannerIdSelected"] != "":
                            regaliaBanner_item = regaliaBanners[lol["bannerIdSelected"]]["items"][0]
                            friend_hovercard_data[key].append(regaliaBanner_item[key.split()[1]])
                        else:
                            friend_hovercard_data[key].append("")
                    elif i == 60: #选用勋章名称（`challengeTokenNamesSelected`）
                        if "challengeTokensSelected" in lol and lol["challengeTokensSelected"] != "":
                            challengeTokensSelected = lol["challengeTokensSelected"].split(",")
                            friend_hovercard_data[key].append(list(map(lambda x: challenges["challenges"][x]["name"], challengeTokensSelected)))
                        else:
                            friend_hovercard_data[key].append("")
                    elif i >= 61 and i <= 63: #英雄相关键（Champion-related keys）
                        if "championId" in lol:
                            if lol["championId"] == "":
                                friend_hovercard_data[key].append("")
                            else:
                                championId = int(lol["championId"])
                                if i == 63:
                                    iconPath = LoLChampions[championId][key.split()[1]]
                                    friend_hovercard_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                                else:
                                    friend_hovercard_data[key].append(LoLChampions[championId][key.split()[1]])
                        else:
                            friend_hovercard_data[key].append("")
                    elif i >= 64 and i <= 71: #小小英雄相关键（Companion-related keys）
                        if "companionId" in lol:
                            if lol["companionId"] == "":
                                friend_hovercard_data[key].append("")
                            else:
                                companionId = int(lol["companionId"])
                                if i == 66:
                                    iconPath = TFTCompanions[companionId][key.split()[1]]
                                    friend_hovercard_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                                elif i == 70:
                                    friend_hovercard_data[key].append(rarities[TFTCompanions[companionId][key.split()[1]]])
                                else:
                                    friend_hovercard_data[key].append(TFTCompanions[companionId][key.split()[1]])
                        else:
                            friend_hovercard_data[key].append("")
                    elif i >= 72 and i <= 79: #云顶之弈攻击特效相关键（TFT damage skin-related keys）
                        if "damageSkinId" in lol:
                            if lol["damageSkinId"] == "":
                                friend_hovercard_data[key].append("")
                            else:
                                damageSkinId = int(lol["damageSkinId"])
                                if i == 74:
                                    iconPath = TFTDamageSkins[damageSkinId][key.split()[1]]
                                    friend_hovercard_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                                if i == 77:
                                    friend_hovercard_data[key].append(rarities[TFTDamageSkins[damageSkinId][key.split()[1]]])
                                else:
                                    friend_hovercard_data[key].append(TFTDamageSkins[damageSkinId][key.split()[1]])
                        else:
                            friend_hovercard_data[key].append("")
                    elif i == 80: #游戏模式名称（`gameModeName`）
                        if "queueId" in lol and lol["queueId"] != "":
                            queueId = int(lol["queueId"])
                            friend_hovercard_data[key].append("自定义" if queueId == -1 or queueId == 0 else queues[queueId]["name"])
                        else:
                            friend_hovercard_data[key].append("")
                    elif i >= 81 and i <= 87: #棋盘皮肤相关键（TFT map skin-related keys）
                        if "mapSkinId" in lol:
                            if lol["mapSkinId"] == "":
                                friend_hovercard_data[key].append("")
                            else:
                                mapSkinId = int(lol["mapSkinId"])
                                if i == 83:
                                    iconPath = TFTMapSkins[mapSkinId][key.split()[1]]
                                    friend_hovercard_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                                if i == 86:
                                    friend_hovercard_data[key].append(rarities[TFTMapSkins[mapSkinId][key.split()[1]]])
                                else:
                                    friend_hovercard_data[key].append(TFTMapSkins[mapSkinId][key.split()[1]])
                        else:
                            friend_hovercard_data[key].append("")
                    elif i >= 88 and i <= 91: #头衔相关键（Title-related keys）
                        if "playerTitleSelected" in lol:
                            title_contentId = lol["playerTitleSelected"]
                            if title_contentId == "":
                                friend_hovercard_data[key].append("")
                            else:
                                if i == 90:
                                    friend_hovercard_data[key].append(titleAcquisitionTypes[titles[title_contentId][key.split()[1]]])
                                else:
                                    friend_hovercard_data[key].append(titles[title_contentId][key.split()[1]])
                        else:
                            friend_hovercard_data[key].append("")
                    elif i >= 92 and i <= 101: #选用皮肤相关键（`skinVariant`-related keys）
                        if "skinVariant" in lol:
                            if lol["skinVariant"] == "":
                                friend_hovercard_data[key].append("")
                            else:
                                skinId = int(lol["skinVariant"])
                                if not key.split()[1] in championSkins[skinId]:
                                    friend_hovercard_data[key].append("")
                                else:
                                    if i >= 94 and i <= 98 or i == 100 or i == 101:
                                        iconPath = championSkins[skinId][key.split()[1]]
                                        friend_hovercard_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                                    elif i == 99:
                                        friend_hovercard_data[key].append(krarities[championSkins[skinId][key.split()[1]]])
                                    else:
                                        friend_hovercard_data[key].append(championSkins[skinId][key.split()[1]])
                        else:
                            friend_hovercard_data[key].append("")
                    else:
                        friend_hovercard_data[key].append(lol.get(key, ""))
            elif i <= 106:
                if friend["lol"] != {} and "pty" in friend and friend["pty"] != "":
                    party = eval(friend["lol"]["pty"])
                    if i == 106: #小队召唤师名（`pty summonerNames`）
                        summonerIds = party["summoners"]
                        summonerNames = []
                        for summonerId in summonerIds:
                            member_info_recapture = 0
                            member_info = await get_info(connection, summonerId)
                            while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                                logPrint(member_info["message"])
                                member_info_recapture += 1
                                logPrint("成员信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an member (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(summonerId, member_info_recapture, summonerId, member_info_recapture))
                                member_info = await get_info(connection, summonerId)
                            if member_info_recapture >= 3:
                                logPrint(member_info["message"])
                                logPrint("成员信息（召唤师序号：%d）获取失败！将忽略该成员。\nInformation of a member (summonerId: %d) capture failed! The program will ignore this member.")
                                summonerNames.append("")
                                continue
                            summonerNames.append(get_info_name(member_info["body"]))
                        friend_hovercard_data[key].append(summonerNames)
                    else:
                        friend_hovercard_data[key].append(party[key.split()[1]])
                else:
                    friend_hovercard_data[key].append("")
            else:
                if friend["lol"] != {} and friend["lol"]["regalia"] != "":
                    regalia = eval(friend["lol"]["regalia"])
                    friend_hovercard_data[key].append(regalia[key.split()[1]])
                else:
                    friend_hovercard_data[key].append("")
    #数据框列序整理（Dataframe column ordering）
    friend_hovercard_statistics_output_order = [11, 3, 4, 21, 18, 14, 5, 6, 23, 0, 9, 19, 12, 25, 26, 41, 48, 49, 47, 54, 50, 52, 51, 53, 59, 28, 29, 40, 88, 89, 90, 91, 60, 37, 104, 106, 103, 35, 36, 46, 42, 34, 61, 62, 93, 99, 65, 67, 68, 70, 73, 79, 76, 77, 82, 85, 86, 39]
    friend_hovercard_data_organized = {}
    for i in friend_hovercard_statistics_output_order:
        key = friend_hovercard_header_keys[i]
        friend_hovercard_data_organized[key] = friend_hovercard_data[key]
    friend_hovercard_df = pandas.DataFrame(data = friend_hovercard_data_organized)
    for column in friend_hovercard_df:
        if friend_hovercard_df[column].dtype == "bool":
            friend_hovercard_df[column] = friend_hovercard_df[column].astype(str)
            for i in range(len(friend_hovercard_df)):
                friend_hovercard_df.loc[i, column] = "√" if friend_hovercard_df[column][i] == "True" else ""
    friend_hovercard_df = pandas.concat([pandas.DataFrame([friend_hovercard_header])[friend_hovercard_df.columns], friend_hovercard_df], ignore_index = True)
    return friend_hovercard_df

async def sort_friend_hovercard_simple(connection):
    #下面准备一些数据资源（Prepare some data resources）
    ##自己的信息（Self info）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    ##好友悬停卡信息（Friend hovercard）
    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    #定义好友数据结构（Define the friend hovercard data structure）
    friend_hovercard_header_simple = {"availability": "可用性", "gameName": "玩家昵称", "gameTag": "昵称编号", "groupId": "分组序号", "groupName": "分组名称", "name": "显示名", "note": "备注", "pid": "社交代码", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号"}
    friend_hovercard_data_simple = {}
    friend_hovercard_header_keys_simple = list(friend_hovercard_header_simple.keys())
    for i in range(len(friend_hovercard_header_keys_simple)):
        key = friend_hovercard_header_keys_simple[i]
        friend_hovercard_data_simple[key] = []
    #下面定义一些常量字典（Define some constant dictionaries）
    availabilities = {"available": "可用", "away": "离开", "championSelect": "英雄选择", "chat": "在线", "dnd": "游戏中", "hostingCoopVsAIGame": "正创建人机对战", "hostingFeaturedGame": "正创建特殊模式", "hostingNormalGame": "正创建匹配模式", "hostingPracticeGame": "正创建自定义游戏", "hostingRankedGame": "创建排位赛", "hosting_ARAM_UNRANKED_5x5": "正创建匹配模式", "hosting_BOT": "正创建人机对战", "hosting_BOT_3x3": "正创建人机对战", "hosting_CHERRY": "正创建斗魂竞技场", "hosting_RIOTSCRIPT_BOT": "正创建人机对战", "hosting_Custom": "正创建自定义游戏", "hosting_NEXUSBLITZ": "正创建极限闪击", "hosting_NORMAL": "正创建匹配模式", "hosting_NORMAL_3x3": "正创建匹配模式", "hosting_NORMAL_TFT": "正创建云顶之弈对局", "hosting_PRACTICETOOL": "正创建训练模式", "hosting_RANKED_FLEX_SR": "正创建排位对局", "hosting_RANKED_FLEX_TT": "正创建排位对局", "hosting_RANKED_SOLO_5x5": "正创建排位对局", "hosting_RANKED_TEAM_5x5": "正创建排位对局", "hosting_RANKED_TFT": "正创建云顶之弈对局", "hosting_RANKED_TFT_TURBO": "正创建云顶之弈对局", "hosting_RANKED_TFT_PAIRS": "正创建双人作战对局", "hosting_RANKED_TFT_DOUBLE_UP": "正创建双人作战", "hosting_STRAWBERRY": "正创建【无尽狂潮】对局", "hosting_CHONCC_TREASURE_TFT": "正创建云顶之弈对局", "hosting_LNY23_TFT": "正创建云顶之弈对局", "hosting_LNY24_TFT": "正创建云顶之弈对局", "hosting_LNY25_TFT": "正在创建云顶之弈对局", "hosting_SET_REVIVAL_5_5_TFT": "正在创建云顶之弈对局", "hosting_FIVE_YEAR_ANNIVERSARY_TFT": "正在创建云顶之弈对局", "hosting_SF_TFT": "正创建云顶之弈对局", "hosting_featured": "正创建特殊模式", "inGame": "游戏中", "inQueue": "队列中", "inTeamBuilder": "阵容匹配中", "map_hosting_ARAM_UNRANKED_5x5": "正创建匹配模式（进步之桥）", "map_hosting_NORMAL": "正创建匹配模式（召唤师峡谷）", "map_hosting_NORMAL_3x3": "正创建匹配模式（扭曲丛林）", "map_hosting_RANKED_FLEX_SR": "正创建灵活排位（召唤师峡谷）", "map_hosting_RANKED_FLEX_TT": "正创建灵活排位（扭曲丛林）", "mobile": "在线分组", "offline": "离线", "online": "在线", "spectating": "正在观战中", "teamSelect": "正在选择队伍", "tutorial": "正在新手教程中", "undefined": "待定……", "watchingReplay": "正在观看回放", "outOfGame": "在线"} #来源（Source）：plugins/rcp-fe-lol-social/global/zh_cn
    #数据整理核心部分（Data assignment - core part）
    for friend in friends:
        for i in range(len(friend_hovercard_header_keys_simple)):
            key = friend_hovercard_header_keys_simple[i]
            if i == 0:
                friend_hovercard_data_simple[key].append(availabilities[friend[key]])
            else:
                friend_hovercard_data_simple[key].append(friend[key])
    #数据框列序整理（Dataframe column ordering）
    friend_hovercard_statistics_output_order_simple = [5, 1, 2, 9, 8, 7, 3, 4, 0, 6]
    friend_hovercard_data_organized_simple = {}
    for i in friend_hovercard_statistics_output_order_simple:
        key = friend_hovercard_header_keys_simple[i]
        friend_hovercard_data_organized_simple[key] = friend_hovercard_data_simple[key]
    friend_hovercard_df_simple = pandas.DataFrame(data = friend_hovercard_data_organized_simple)
    friend_hovercard_df_simple = pandas.concat([pandas.DataFrame([friend_hovercard_header_simple])[friend_hovercard_df_simple.columns], friend_hovercard_df_simple], ignore_index = True)
    return friend_hovercard_df_simple

async def sort_friend_group(connection):
    friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
    friend_groups_header = {"collapsed": "已折叠", "id": "分组序号", "isLocalized": "分组名称已翻译", "isMetaGroup": "大组", "name": "分组名称", "priority": "优先级"}
    friend_groups_header_keys = list(friend_groups_header.keys())
    friend_groups_data = {}
    if isinstance(friend_groups, list) and all(map(lambda x: isinstance(x, dict), friend_groups)) and all(i in group for i in ["collapsed", "id", "isLocalized", "isMetaGroup", "name", "priority"] for group in friend_groups):
        for i in range(len(friend_groups_header_keys)):
            key = friend_groups_header_keys[i]
            friend_groups_data[key] = []
        for group in friend_groups:
            for i in range(len(friend_groups_header_keys)):
                key = friend_groups_header_keys[i]
                friend_groups_data[key].append(group[key])
        friend_groups_statistics_output_order = [1, 4, 5, 0]
        friend_groups_data_organized = {}
        for i in friend_groups_statistics_output_order:
            key = friend_groups_header_keys[i]
            friend_groups_data_organized[key] = friend_groups_data[key]
        friend_groups_df = pandas.DataFrame(data = friend_groups_data_organized)
        for column in friend_groups_df:
            if friend_groups_df[column].dtype == "bool":
                friend_groups_df[column] = friend_groups_df[column].astype(str)
                for i in range(len(friend_groups_df)):
                    friend_groups_df.loc[i, column] = "√" if friend_groups_df[column][i] == "True" else ""
        friend_groups_df = pandas.concat([pandas.DataFrame([friend_groups_header])[friend_groups_df.columns], friend_groups_df], ignore_index = True)
    elif isinstance(friend_groups, dict) and all(i in friend_groups for i in ["errorCode", "httpStatus", "implementationDetails", "message"]):
        friend_groups_df = pandas.DataFrame(data = friend_groups_header, index = [0])
    else:
        logPrint("好友分组数据格式错误！函数只生成空表。\nFriend group data format ERROR! The function will only return an empty table.")
        friend_groups_df = pandas.DataFrame(data = friend_groups_header, index = [0])
    return friend_groups_df

async def sort_conversation_metadata(connection):
    conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
    conversationTypes = {"chat": "私聊", "customGame": "自定义对局", "championSelect": "英雄选择", "postGame": "结算界面"}
    conversation_header = {"gameName": "玩家昵称", "gameTag": "昵称编号", "id": "对话序号", "inviterId": "邀请人序号", "isMuted": "已静音", "name": "召唤师显示名", "password": "密码", "pid": "社交代码", "targetRegion": "目标服务器", "type": "对话类型", "unreadMessageCount": "未读消息数"}
    conversation_header_keys = list(conversation_header.keys())
    conversation_metadata = {}
    for i in range(len(conversation_header_keys)):
        key = conversation_header_keys[i]
        conversation_metadata[key] = []
    for conversation in conversations:
        for i in range(len(conversation_header_keys)):
            key = conversation_header_keys[i]
            if i == 9:
                conversation_metadata[key].append(conversationTypes[conversation[key]])
            else:
                conversation_metadata[key].append(conversation[key])
    conversation_statistics_output_order = [9, 0, 1, 2]
    conversation_metadata_organized = {}
    for i in conversation_statistics_output_order:
        key = conversation_header_keys[i]
        conversation_metadata_organized[key] = conversation_metadata[key]
    conversation_df = pandas.DataFrame(data = conversation_metadata_organized)
    conversation_df = pandas.concat([pandas.DataFrame([conversation_header])[conversation_df.columns], conversation_df], ignore_index = True)
    return conversation_df

async def sort_message_data(connection, messages: list | dict):
    messageTypes = {"chat": "聊天", "groupchat": "队伍聊天", "system": "系统", "information": "通知", "celebration": "庆祝"}
    message_header = {"body": "正文", "fromId": "发送人账号", "fromObfuscatedSummonerId": "发送人隐藏召唤师序号", "fromPid": "发送人社交代码", "fromSummonerId": "发送人召唤师序号", "id": "消息序号", "isHistorical": "记录已保存", "timestamp": "时间戳", "type": "消息类型", "fromSummonerName": "发送人召唤师名", "fromPuuid": "发送人玩家通用唯一识别码"}
    message_header_keys = list(message_header.keys())
    if isinstance(messages, list) and all(map(lambda x: isinstance(x, dict), messages)) and all(i in message for i in ["body", "fromId", "fromObfuscatedSummonerId", "fromPid", "fromSummonerId", "id", "isHistorical", "timestamp", "type"] for message in messages):
        message_data = {}
        for i in range(len(message_header_keys)):
            key = message_header_keys[i]
            message_data[key] = []
        for message in messages:
            for i in range(len(message_header_keys)):
                key = message_header_keys[i]
                if i == 7: #时间戳（`timestamp`）
                    message_data[key].append(message[key][:10] + " " + message[key][11:23])
                elif i == 8: #消息类型（`type`）
                    message_data[key].append(messageTypes.get(message[key], message[key]))
                elif i == 9 or i == 10: #发送人信息相关键（Sender information-related keys）
                    if message["fromSummonerId"] == 0:
                        message_data[key].append("")
                    else:
                        fromInfo = await get_info(connection, message["fromSummonerId"])
                        message_data[key].append(get_info_name(fromInfo["body"]) if i == 9 else fromInfo["body"]["puuid"])
                else:
                    message_data[key].append(message[key])
        message_statistics_output_order = [5, 7, 9, 8, 0, 4, 3, 1, 10, 6, 2]
        message_data_organized = {}
        for i in message_statistics_output_order:
            key = message_header_keys[i]
            message_data_organized[key] = message_data[key]
        message_df = pandas.DataFrame(data = message_data_organized)
        for column in message_df:
            if message_df[column].dtype == "bool":
                message_df[column] = message_df[column].astype(str)
                for i in range(len(message_df)):
                    message_df.loc[i, column] = "√" if message_df[column][i] == "True" else ""
        message_df = pandas.concat([pandas.DataFrame([message_header])[message_df.columns], message_df], ignore_index = True)
    elif isinstance(messages, dict) and all(i in messages for i in ["errorCode", "httpStatus", "implementationDetails", "message"]):
        message_df = pandas.DataFrame(message_header, index = [0])
    else:
        logPrint("消息数据格式错误！函数只生成空表。\nMessage data format ERROR! The function will only return an empty table.")
        message_df = pandas.DataFrame(message_header, index = [0])
    return message_df

async def get_recent_players(connection, search_mode: int = 2):
    if search_mode == 1:
        search_LoL = search_TFT = True, True
    elif search_mode == 2:
        search_LoL = search_TFT = True, False
    elif search_mode == 3:
        search_LoL = search_TFT = False, True
    else:
        search_LoL = search_TFT = False, False
    #下面准备一些数据资源（Prepare some data resources）
    logPrint("正在准备通用数据资源……\nPreparing general data resources ...")
    ##自己的信息（Self info）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_puuid = current_info["puuid"]
    current_summonerId = current_info["summonerId"]
    current_summonerName = get_info_name(current_info)
    ##游戏模式（Game mode）
    gamemode = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gamemodes = {-1: {"name": "自定义", "gameMode": "CUSTOM", "category": "CUSTOM", "description": "", "type": "CUSTOM"}, 0: {"name": "自定义", "gameMode": "CUSTOM", "category": "CUSTOM", "description": "", "type": "CUSTOM"}} #在对局记录中，自定义对局的队列序号是0；在邀请中，自定义房间的队列序号是-1（A custom game's queueId is 0 in the match history. A custom lobby's queueId is -1 in an invitation）
    for gamemode_iter in gamemode:
        gamemode_id = gamemode_iter["id"]
        gamemodes_iter = {}
        gamemodes_iter["name"] = gamemode_iter["name"]
        gamemodes_iter["gameMode"] = gamemode_iter["gameMode"]
        gamemodes_iter["description"] = gamemode_iter["description"]
        gamemodes[gamemode_id] = gamemodes_iter
    #下面定义一些常量字典（Define some constant dictionaries）
    unmapped_keys = {"summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set(), "CherryAugment": set()}
    endOfGameResults = {"": "", "GameComplete": "游戏结束", "Abort_Unexpected": "意外终止", "Abort_TooFewPlayers": "全员提前退出", "Abort_AntiCheatExit": "检测到作弊而终止"}
    gameTypes = {"MATCHED_GAME": "匹配对局", "CUSTOM_GAME": "自定义对局"}
    tiers = {"": "", "NONE": "没有段位", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    ratedTiers = {"": "", "NONE": "没有段位", "GRAY": "灰白", "GREEN": "翠绿", "BLUE": "天蓝", "PURPLE": "绛紫", "ORANGE": "耀橙"}
    tiers_all = tiers | ratedTiers
    team_color = {100: "蓝方", 200: "红方"}
    subteam_color = {0: "", 1: "魄罗", 2: "小兵", 3: "迅捷蟹", 4: "石甲虫", 5: "锋喙鸟", 6: "哨卫", 7: "狼", 8: "魔沼蛙"} #仅用于斗魂竞技场（Only for Arena mode）
    augment_rarity = {0: "白银", 1: "黄金", 2: "棱彩", 4: "黄金", 8: "棱彩", "kBronze": "青铜", "kSilver": "白银", "kGold": "黄金", "kPrismatic": "棱彩"}
    win = {True: "胜利", False: "失败"}
    lanes = {"TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "NONE": ""}
    roles = {"CARRY": "C位", "DUO": "游走", "SOLO": "单人", "SUPPORT": "辅助", "NONE": ""}
    traitStyles = {0: "", 1: "青铜", 2: "白银", 3: "黄金", 4: "炫金", 5: "独行"}
    rarities = {"Default": "经典", "NoRarity": "其它", "Epic": "史诗", "Legendary": "传说", "Mythic": "神话", "Rare": "稀有", "Ultimate": "终极", "Exalted": "圣者至尊", "Transcendant": "超凡"}
    #定义玩家对局表现数据结构（Define the player match behavior data structure）
    ##英雄联盟（LoL）
    LoLGame_info_header = {"gameIndex": "游戏序号", "endOfGameResult": "对局终止情况", "gameCreation": "对局创建时间戳", "gameCreationDate": "创建日期", "gameDuration": "持续时长（秒）", "gameId": "对局序号", "gameMode": "游戏模式", "gameType": "游戏类型", "gameVersion": "对局版本", "mapId": "地图序号", "queueId": "队列序号", "gameDuration_norm": "持续时长", "gameModeName": "游戏模式名称", "participantId": "玩家序号", "accountId": "账户序号", "currentAccountId": "当前账户序号", "currentPlatformId": "当前大区", "gameName": "玩家昵称", "matchHistoryUri": "对局记录网址", "platformId": "原大区", "profileIcon": "召唤师图标序号", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "tagLine": "昵称编号", "profileIcon_title": "召唤师图标名称", "profileIcon_imagePath": "召唤师图标路径", "championId": "选用英雄序号", "highestAchievedSeasonTier": "最高段位", "spell1Id": "召唤师技能1序号", "spell2Id": "召唤师技能2序号", "teamId": "阵营代号", "champion_name": "选用英雄", "champion_alias": "选用英雄代号", "champion_squarePortraitPath": "选用英雄方块头像路径", "spell1_name": "召唤师技能1", "spell2_name": "召唤师技能2", "spell1_iconPath": "召唤师技能1图标", "spell2_iconPath": "召唤师技能2图标", "team_color": "阵营", "assists": "助攻", "causedEarlySurrender": "发起提前投降", "champLevel": "英雄等级", "combatPlayerScore": "战斗得分", "damageDealtToObjectives": "对战略点的总伤害", "damageDealtToTurrets": "对防御塔的总伤害", "damageSelfMitigated": "自我缓和的伤害", "deaths": "死亡", "doubleKills": "双杀", "earlySurrenderAccomplice": "同意提前投降", "firstBloodAssist": "协助获得第一滴血", "firstBloodKill": "第一滴血", "firstInhibitorAssist": "协助摧毁第一座召唤水晶", "firstInhibitorKill": "摧毁第一座召唤水晶", "firstTowerAssist": "协助摧毁第一座塔", "firstTowerKill": "摧毁第一座塔", "gameEndedInEarlySurrender": "提前投降导致比赛结束", "gameEndedInSurrender": "投降导致比赛结束", "goldEarned": "金币获取", "goldSpent": "金币使用", "inhibitorKills": "摧毁召唤水晶", "item0": "装备1序号", "item1": "装备2序号", "item2": "装备3序号", "item3": "装备4序号", "item4": "装备5序号", "item5": "装备6序号", "item6": "饰品序号", "killingSprees": "大杀特杀", "kills": "击杀", "largestCriticalStrike": "最大暴击伤害", "largestKillingSpree": "最高连杀", "largestMultiKill": "最高多杀", "longestTimeSpentLiving": "最长生存时间", "magicDamageDealt": "造成的魔法伤害", "magicDamageDealtToChampions": "对英雄的魔法伤害", "magicalDamageTaken": "承受的魔法伤害", "neutralMinionsKilled": "击杀野怪", "neutralMinionsKilledEnemyJungle": "击杀敌方野区野怪", "neutralMinionsKilledTeamJungle": "击杀我方野区野怪", "objectivePlayerScore": "战略点玩家得分", "pentaKills": "五杀", "perk0": "符文1序号", "perk0Var1": "符文1：参数1", "perk0Var2": "符文1：参数2", "perk0Var3": "符文1：参数3", "perk1": "符文2序号", "perk1Var1": "符文2：参数1", "perk1Var2": "符文2：参数2", "perk1Var3": "符文2：参数3", "perk2": "符文3序号", "perk2Var1": "符文3：参数1", "perk2Var2": "符文3：参数2", "perk2Var3": "符文3：参数3", "perk3": "符文4序号", "perk3Var1": "符文4：参数1", "perk3Var2": "符文4：参数2", "perk3Var3": "符文4：参数3", "perk4": "符文5序号", "perk4Var1": "符文5：参数1", "perk4Var2": "符文5：参数2", "perk4Var3": "符文5：参数3", "perk5": "符文6序号", "perk5Var1": "符文6：参数1", "perk5Var2": "符文6：参数2", "perk5Var3": "符文6：参数3", "perkPrimaryStyle": "主系序号", "perkSubStyle": "副系序号", "physicalDamageDealt": "造成的物理伤害", "physicalDamageDealtToChampions": "对英雄的物理伤害", "physicalDamageTaken": "承受的物理伤害", "playerAugment1": "强化符文1", "playerAugment2": "强化符文2", "playerAugment3": "强化符文3", "playerAugment4": "强化符文4", "playerAugment5": "强化符文5", "playerAugment6": "强化符文6", "playerScore0": "玩家得分1", "playerScore1": "玩家得分2", "playerScore2": "玩家得分3", "playerScore3": "玩家得分4", "playerScore4": "玩家得分5", "playerScore5": "玩家得分6", "playerScore6": "玩家得分7", "playerScore7": "玩家得分8", "playerScore8": "玩家得分9", "playerScore9": "玩家得分10", "playerSubteamId": "子阵营代号", "quadraKills": "四杀", "sightWardsBoughtInGame": "购买洞察之石", "subteamPlacement": "队伍排名", "teamEarlySurrendered": "队伍提前投降", "timeCCingOthers": "控制得分", "totalDamageDealt": "造成的伤害总和", "totalDamageDealtToChampions": "对英雄的伤害总和", "totalDamageTaken": "承受伤害", "totalHeal": "输出治疗效果", "totalMinionsKilled": "击杀小兵", "totalPlayerScore": "玩家总得分", "totalScoreRank": "总得分排名", "totalTimeCrowdControlDealt": "控制时间", "totalUnitsHealed": "治疗单位数", "tripleKills": "三杀", "trueDamageDealt": "造成真实伤害", "trueDamageDealtToChampions": "对英雄的真实伤害", "trueDamageTaken": "承受的真实伤害", "turretKills": "摧毁防御塔", "unrealKills": "六杀及以上", "visionScore": "视野得分", "visionWardsBoughtInGame": "购买控制守卫", "wardsKilled": "摧毁守卫", "wardsPlaced": "放置守卫", "win": "胜利", "item0_name": "装备1", "item1_name": "装备2", "item2_name": "装备3", "item3_name": "装备4", "item4_name": "装备5", "item5_name": "装备6", "item6_name": "饰品", "item0_iconPath": "装备1图标路径", "item1_iconPath": "装备2图标路径", "item2_iconPath": "装备3图标路径", "item3_iconPath": "装备4图标路径", "item4_iconPath": "装备5图标路径", "item5_iconPath": "装备6图标路径", "item6_iconPath": "饰品图标路径", "perk0EndOfGameStatDescs": "符文1游戏结算数据", "perk1EndOfGameStatDescs": "符文2游戏结算数据", "perk2EndOfGameStatDescs": "符文3游戏结算数据", "perk3EndOfGameStatDescs": "符文4游戏结算数据", "perk4EndOfGameStatDescs": "符文5游戏结算数据", "perk5EndOfGameStatDescs": "符文6游戏结算数据", "perk0_name": "符文1名称", "perk1_name": "符文2名称", "perk2_name": "符文3名称", "perk3_name": "符文4名称", "perk4_name": "符文5名称", "perk5_name": "符文6名称", "perk0_iconPath": "符文1图标路径", "perk1_iconPath": "符文2图标路径", "perk2_iconPath": "符文3图标路径", "perk3_iconPath": "符文4图标路径", "perk4_iconPath": "符文5图标路径", "perk5_iconPath": "符文6图标路径", "perkPrimaryStyle_name": "主系名称", "perkPrimaryStyle_iconPath": "主系图标路径", "perkSubStyle_name": "副系名称", "perkSubStyle_iconPath": "副系图标路径", "playerAugment1_nameTRA": "强化符文1名称", "playerAugment2_nameTRA": "强化符文2名称", "playerAugment3_nameTRA": "强化符文3名称", "playerAugment4_nameTRA": "强化符文4名称", "playerAugment5_nameTRA": "强化符文5名称", "playerAugment6_nameTRA": "强化符文6名称", "playerAugment1_augmentIconPath": "强化符文1图标路径", "playerAugment2_augmentIconPath": "强化符文2图标路径", "playerAugment3_augmentIconPath": "强化符文3图标路径", "playerAugment4_augmentIconPath": "强化符文4图标路径", "playerAugment5_augmentIconPath": "强化符文5图标路径", "playerAugment6_augmentIconPath": "强化符文6图标路径", "playerAugment1_rarity": "强化符文1等级", "playerAugment2_rarity": "强化符文2等级", "playerAugment3_rarity": "强化符文3等级", "playerAugment4_rarity": "强化符文4等级", "playerAugment5_rarity": "强化符文5等级", "playerAugment6_rarity": "强化符文6等级", "playerSubteam_color": "子阵营", "K/D/A": "击杀/死亡/助攻", "KDA": "战损比", "CS": "补刀", "GPM": "分均经济", "GUE": "金币利用率", "CSPM": "分均补刀", "D/G": "伤害转化率", "win/lose": "胜负", "bannedChampionId": "禁用英雄序号", "bannedChampion_name": "禁用英雄", "bannedChampion_alias": "禁用英雄代号", "bannedChampion_squarePortraitPath": "禁用英雄方块头像路径", "lane": "分路", "role": "角色定位", "ally?": "是否队友？", "assists_percent": "助攻次数占比", "combatPlayerScore_percent": "战斗得分占比", "damageDealtToObjectives_percent": "对战略点的总伤害占比", "damageDealtToTurrets_percent": "对防御塔的总伤害占比", "damageSelfMitigated_percent": "自我缓和的伤害占比", "deaths_percent": "死亡次数占比", "doubleKills_percent": "双杀次数占比", "goldEarned_percent": "金币获取占比", "goldSpent_percent": "金币使用占比", "inhibitorKills_percent": "摧毁召唤水晶数量占比", "killingSprees_percent": "大杀特杀次数占比", "kills_percent": "击杀数量占比", "largestCriticalStrike_percent": "最大暴击伤害占比", "largestKillingSpree_percent": "最高连杀占比", "largestMultiKill_percent": "最高多杀占比", "longestTimeSpentLiving_percent": "最长生存时间占比", "magicDamageDealt_percent": "造成的魔法伤害占比", "magicDamageDealtToChampions_percent": "对英雄的魔法伤害占比", "magicalDamageTaken_percent": "承受的魔法伤害占比", "neutralMinionsKilled_percent": "击杀野怪数量占比", "neutralMinionsKilledEnemyJungle_percent": "击杀敌方野区野怪数量占比", "neutralMinionsKilledTeamJungle_percent": "击杀我方野区野怪数量占比", "objectivePlayerScore_percent": "战略点玩家得分占比", "pentaKills_percent": "五杀次数占比", "physicalDamageDealt_percent": "造成的物理伤害占比", "physicalDamageDealtToChampions_percent": "对英雄的物理伤害占比", "physicalDamageTaken_percent": "承受的物理伤害占比", "playerScore0_percent": "玩家得分1占比", "playerScore1_percent": "玩家得分2占比", "playerScore2_percent": "玩家得分3占比", "playerScore3_percent": "玩家得分4占比", "playerScore4_percent": "玩家得分5占比", "playerScore5_percent": "玩家得分6占比", "playerScore6_percent": "玩家得分7占比", "playerScore7_percent": "玩家得分8占比", "playerScore8_percent": "玩家得分9占比", "playerScore9_percent": "玩家得分10占比", "quadraKills_percent": "四杀次数占比", "sightWardsBoughtInGame_percent": "购买洞察之石数量占比", "timeCCingOthers_percent": "控制得分占比", "totalDamageDealt_percent": "造成的伤害总和占比", "totalDamageDealtToChampions_percent": "对英雄的伤害总和占比", "totalDamageTaken_percent": "承受伤害占比", "totalHeal_percent": "输出治疗效果占比", "totalMinionsKilled_percent": "击杀小兵数量占比", "totalPlayerScore_percent": "玩家总得分占比", "totalTimeCrowdControlDealt_percent": "控制时间占比", "totalUnitsHealed_percent": "治疗单位数占比", "tripleKills_percent": "三杀次数占比", "trueDamageDealt_percent": "造成真实伤害占比", "trueDamageDealtToChampions_percent": "对英雄的真实伤害占比", "trueDamageTaken_percent": "承受的真实伤害占比", "turretKills_percent": "摧毁防御塔数量占比", "unrealKills_percent": "六杀及以上连杀次数占比", "visionScore_percent": "视野得分占比", "visionWardsBoughtInGame_percent": "购买控制守卫数量占比", "wardsKilled_percent": "摧毁守卫数量占比", "wardsPlaced_percent": "放置守卫数量占比", "KP_percent": "参团率", "CS_percent": "补刀数占比", "assists_order": "助攻次数位次", "champLevel_order": "英雄等级位次", "combatPlayerScore_order": "战斗得分位次", "damageDealtToObjectives_order": "对战略点的总伤害位次", "damageDealtToTurrets_order": "对防御塔的总伤害位次", "damageSelfMitigated_order": "自我缓和的伤害位次", "deaths_order": "死亡次数位次", "doubleKills_order": "双杀次数位次", "goldEarned_order": "金币获取位次", "goldSpent_order": "金币使用位次", "inhibitorKills_order": "摧毁召唤水晶数量位次", "killingSprees_order": "大杀特杀次数位次", "kills_order": "击杀数量位次", "largestCriticalStrike_order": "最大暴击伤害位次", "largestKillingSpree_order": "最高连杀位次", "largestMultiKill_order": "最高多杀位次", "longestTimeSpentLiving_order": "最长生存时间位次", "magicDamageDealt_order": "造成的魔法伤害位次", "magicDamageDealtToChampions_order": "对英雄的魔法伤害位次", "magicalDamageTaken_order": "承受的魔法伤害位次", "neutralMinionsKilled_order": "击杀野怪数量位次", "neutralMinionsKilledEnemyJungle_order": "击杀敌方野区野怪数量位次", "neutralMinionsKilledTeamJungle_order": "击杀我方野区野怪数量位次", "objectivePlayerScore_order": "战略点玩家得分位次", "pentaKills_order": "五杀次数位次", "physicalDamageDealt_order": "造成的物理伤害位次", "physicalDamageDealtToChampions_order": "对英雄的物理伤害位次", "physicalDamageTaken_order": "承受的物理伤害位次", "playerScore0_order": "玩家得分1位次", "playerScore1_order": "玩家得分2位次", "playerScore2_order": "玩家得分3位次", "playerScore3_order": "玩家得分4位次", "playerScore4_order": "玩家得分5位次", "playerScore5_order": "玩家得分6位次", "playerScore6_order": "玩家得分7位次", "playerScore7_order": "玩家得分8位次", "playerScore8_order": "玩家得分9位次", "playerScore9_order": "玩家得分10位次", "quadraKills_order": "四杀次数位次", "sightWardsBoughtInGame_order": "购买洞察之石数量位次", "timeCCingOthers_order": "控制得分位次", "totalDamageDealt_order": "造成的伤害总和位次", "totalDamageDealtToChampions_order": "对英雄的伤害总和位次", "totalDamageTaken_order": "承受伤害位次", "totalHeal_order": "输出治疗效果位次", "totalMinionsKilled_order": "击杀小兵数量位次", "totalPlayerScore_order": "玩家总得分位次", "totalTimeCrowdControlDealt_order": "控制时间位次", "totalUnitsHealed_order": "治疗单位数位次", "tripleKills_order": "三杀次数位次", "trueDamageDealt_order": "造成真实伤害位次", "trueDamageDealtToChampions_order": "对英雄的真实伤害位次", "trueDamageTaken_order": "承受的真实伤害位次", "turretKills_order": "摧毁防御塔数量位次", "unrealKills_order": "六杀及以上连杀次数位次", "visionScore_order": "视野得分位次", "visionWardsBoughtInGame_order": "购买控制守卫数量位次", "wardsKilled_order": "摧毁守卫数量位次", "wardsPlaced_order": "放置守卫数量位次", "KDA_order": "战损比位次", "KP_order": "参团率位次", "CS_order": "补刀数位次", "D/G_order": "伤害转化率位次", "GUE_order": "金币利用率位次"}
    LoLGame_info_data = {}
    LoLGame_info_header_keys = list(LoLGame_info_header.keys())
    for key in LoLGame_info_header_keys:
        LoLGame_info_data[key] = []
    ##云顶之弈（TFT）
    TFTHistory_header = {"gameIndex": "游戏序号", "endOfGameResult": "对局终止情况", "gameCreation": "对局创建时间戳", "game_datetime": "对局结算时间戳", "game_id": "对局序号", "game_length": "持续时长（秒）", "game_version": "对局版本", "queue_id": "队列序号", "tft_game_type": "游戏类型", "tft_set_core_name": "数据版本名称", "tft_set_number": "赛季", "gameCreationDate": "对局创建时间", "gameDate": "对局结算时间", "gameLength": "持续时长", "participantId": "玩家序号", "augment1 apiName": "强化符文1接口名称", "augment2 apiName": "强化符文2接口名称", "augment3 apiName": "强化符文3接口名称", "augment1 name": "强化符文1名称", "augment2 name": "强化符文2名称", "augment3 name": "强化符文3名称", "augment1 icon": "强化符文1图标", "augment2 icon": "强化符文2图标", "augment3 icon": "强化符文3图标", "companion content_ID": "小小英雄商品编号", "companion item_ID": "小小英雄序号", "companion skin_ID": "小小英雄皮肤序号", "companion species": "小小英雄物种", "companion name": "小小英雄名称", "companion level": "小小英雄星级", "companion rarity": "小小英雄稀有度", "gold_left": "剩余金币", "last_round": "存活回合数", "level": "等级", "placement": "名次", "players_eliminated": "淘汰玩家数", "puuid": "玩家通用唯一识别码", "riotIdGameName": "玩家昵称", "riotIdTagLine": "昵称编号", "time_eliminated": "存活时长（秒）", "total_damage_to_players": "造成玩家伤害", "last_round_format": "存活回合", "time_eliminated_norm": "存活时长", "trait0 name": "羁绊1", "trait0 num_units": "羁绊1单位数", "trait0 style": "羁绊1羁绊框颜色", "trait0 tier_current": "羁绊1当前等级", "trait0 tier_total": "羁绊1最高等级", "trait0 display_name": "羁绊1显示名", "trait0 icon_path": "羁绊1图标路径", "trait1 name": "羁绊2", "trait1 num_units": "羁绊2单位数", "trait1 style": "羁绊2羁绊框颜色", "trait1 tier_current": "羁绊2当前等级", "trait1 tier_total": "羁绊2最高等级", "trait1 display_name": "羁绊2显示名", "trait1 icon_path": "羁绊2图标路径", "trait2 name": "羁绊3", "trait2 num_units": "羁绊3单位数", "trait2 style": "羁绊3羁绊框颜色", "trait2 tier_current": "羁绊3当前等级", "trait2 tier_total": "羁绊3最高等级", "trait2 display_name": "羁绊3显示名", "trait2 icon_path": "羁绊3图标路径", "trait3 name": "羁绊4", "trait3 num_units": "羁绊4单位数", "trait3 style": "羁绊4羁绊框颜色", "trait3 tier_current": "羁绊4当前等级", "trait3 tier_total": "羁绊4最高等级", "trait3 display_name": "羁绊4显示名", "trait3 icon_path": "羁绊4图标路径", "trait4 name": "羁绊5", "trait4 num_units": "羁绊5单位数", "trait4 style": "羁绊5羁绊框颜色", "trait4 tier_current": "羁绊5当前等级", "trait4 tier_total": "羁绊5最高等级", "trait4 display_name": "羁绊5显示名", "trait4 icon_path": "羁绊5图标路径", "trait5 name": "羁绊6", "trait5 num_units": "羁绊6单位数", "trait5 style": "羁绊6羁绊框颜色", "trait5 tier_current": "羁绊6当前等级", "trait5 tier_total": "羁绊6最高等级", "trait5 display_name": "羁绊6显示名", "trait5 icon_path": "羁绊6图标路径", "trait6 name": "羁绊7", "trait6 num_units": "羁绊7单位数", "trait6 style": "羁绊7羁绊框颜色", "trait6 tier_current": "羁绊7当前等级", "trait6 tier_total": "羁绊7最高等级", "trait6 display_name": "羁绊7显示名", "trait6 icon_path": "羁绊7图标路径", "trait7 name": "羁绊8", "trait7 num_units": "羁绊8单位数", "trait7 style": "羁绊8羁绊框颜色", "trait7 tier_current": "羁绊8当前等级", "trait7 tier_total": "羁绊8最高等级", "trait7 display_name": "羁绊8显示名", "trait7 icon_path": "羁绊8图标路径", "trait8 name": "羁绊9", "trait8 num_units": "羁绊9单位数", "trait8 style": "羁绊9羁绊框颜色", "trait8 tier_current": "羁绊9当前等级", "trait8 tier_total": "羁绊9最高等级", "trait8 display_name": "羁绊9显示名", "trait8 icon_path": "羁绊9图标路径", "trait9 name": "羁绊10", "trait9 num_units": "羁绊10单位数", "trait9 style": "羁绊10羁绊框颜色", "trait9 tier_current": "羁绊10当前等级", "trait9 tier_total": "羁绊10最高等级", "trait9 display_name": "羁绊10显示名", "trait9 icon_path": "羁绊10图标路径", "trait10 name": "羁绊11", "trait10 num_units": "羁绊11单位数", "trait10 style": "羁绊11羁绊框颜色", "trait10 tier_current": "羁绊11当前等级", "trait10 tier_total": "羁绊11最高等级", "trait10 display_name": "羁绊11显示名", "trait10 icon_path": "羁绊11图标路径", "trait11 name": "羁绊12", "trait11 num_units": "羁绊12单位数", "trait11 style": "羁绊12羁绊框颜色", "trait11 tier_current": "羁绊12当前等级", "trait11 tier_total": "羁绊12最高等级", "trait11 display_name": "羁绊12显示名", "trait11 icon_path": "羁绊12图标路径", "trait12 name": "羁绊13", "trait12 num_units": "羁绊13单位数", "trait12 style": "羁绊13羁绊框颜色", "trait12 tier_current": "羁绊13当前等级", "trait12 tier_total": "羁绊13最高等级", "trait12 display_name": "羁绊13显示名", "trait12 icon_path": "羁绊13图标路径", "unit0 character_id": "英雄1：角色编号", "unit0 rarity": "英雄1：卡费", "unit0 tier": "英雄1：星级", "unit0 display_name": "英雄1：显示名", "unit0 squareIconPath": "英雄1：方块图标路径", "unit1 character_id": "英雄2：角色编号", "unit1 rarity": "英雄2：卡费", "unit1 tier": "英雄2：星级", "unit1 display_name": "英雄2：显示名", "unit1 squareIconPath": "英雄2：方块图标路径", "unit2 character_id": "英雄3：角色编号", "unit2 rarity": "英雄3：卡费", "unit2 tier": "英雄3：星级", "unit2 display_name": "英雄3：显示名", "unit2 squareIconPath": "英雄3：方块图标路径", "unit3 character_id": "英雄4：角色编号", "unit3 rarity": "英雄4：卡费", "unit3 tier": "英雄4：星级", "unit3 display_name": "英雄4：显示名", "unit3 squareIconPath": "英雄4：方块图标路径", "unit4 character_id": "英雄5：角色编号", "unit4 rarity": "英雄5：卡费", "unit4 tier": "英雄5：星级", "unit4 display_name": "英雄5：显示名", "unit4 squareIconPath": "英雄5：方块图标路径", "unit5 character_id": "英雄6：角色编号", "unit5 rarity": "英雄6：卡费", "unit5 tier": "英雄6：星级", "unit5 display_name": "英雄6：显示名", "unit5 squareIconPath": "英雄6：方块图标路径", "unit6 character_id": "英雄7：角色编号", "unit6 rarity": "英雄7：卡费", "unit6 tier": "英雄7：星级", "unit6 display_name": "英雄7：显示名", "unit6 squareIconPath": "英雄7：方块图标路径", "unit7 character_id": "英雄8：角色编号", "unit7 rarity": "英雄8：卡费", "unit7 tier": "英雄8：星级", "unit7 display_name": "英雄8：显示名", "unit7 squareIconPath": "英雄8：方块图标路径", "unit8 character_id": "英雄9：角色编号", "unit8 rarity": "英雄9：卡费", "unit8 tier": "英雄9：星级", "unit8 display_name": "英雄9：显示名", "unit8 squareIconPath": "英雄9：方块图标路径", "unit9 character_id": "英雄10：角色编号", "unit9 rarity": "英雄10：卡费", "unit9 tier": "英雄10：星级", "unit9 display_name": "英雄10：显示名", "unit9 squareIconPath": "英雄10：方块图标路径", "unit10 character_id": "英雄11：角色编号", "unit10 rarity": "英雄11：卡费", "unit10 tier": "英雄11：星级", "unit10 display_name": "英雄11：显示名", "unit10 squareIconPath": "英雄11：方块图标路径", "unit0 item0 nameId": "英雄1：装备1序号", "unit0 item0 name": "英雄1：装备1名称", "unit0 item0 squareIconPath": "英雄1：装备1方块图像路径", "unit0 item1 nameId": "英雄1：装备2序号", "unit0 item1 name": "英雄1：装备2名称", "unit0 item1 squareIconPath": "英雄1：装备2方块图像路径", "unit0 item2 nameId": "英雄1：装备3序号", "unit0 item2 name": "英雄1：装备3名称", "unit0 item2 squareIconPath": "英雄1：装备3方块图像路径", "unit1 item0 nameId": "英雄2：装备1序号", "unit1 item0 name": "英雄2：装备1名称", "unit1 item0 squareIconPath": "英雄2：装备1方块图像路径", "unit1 item1 nameId": "英雄2：装备2序号", "unit1 item1 name": "英雄2：装备2名称", "unit1 item1 squareIconPath": "英雄2：装备2方块图像路径", "unit1 item2 nameId": "英雄2：装备3序号", "unit1 item2 name": "英雄2：装备3名称", "unit1 item2 squareIconPath": "英雄2：装备3方块图像路径", "unit2 item0 nameId": "英雄3：装备1序号", "unit2 item0 name": "英雄3：装备1名称", "unit2 item0 squareIconPath": "英雄3：装备1方块图像路径", "unit2 item1 nameId": "英雄3：装备2序号", "unit2 item1 name": "英雄3：装备2名称", "unit2 item1 squareIconPath": "英雄3：装备2方块图像路径", "unit2 item2 nameId": "英雄3：装备3序号", "unit2 item2 name": "英雄3：装备3名称", "unit2 item2 squareIconPath": "英雄3：装备3方块图像路径", "unit3 item0 nameId": "英雄4：装备1序号", "unit3 item0 name": "英雄4：装备1名称", "unit3 item0 squareIconPath": "英雄4：装备1方块图像路径", "unit3 item1 nameId": "英雄4：装备2序号", "unit3 item1 name": "英雄4：装备2名称", "unit3 item1 squareIconPath": "英雄4：装备2方块图像路径", "unit3 item2 nameId": "英雄4：装备3序号", "unit3 item2 name": "英雄4：装备3名称", "unit3 item2 squareIconPath": "英雄4：装备3方块图像路径", "unit4 item0 nameId": "英雄5：装备1序号", "unit4 item0 name": "英雄5：装备1名称", "unit4 item0 squareIconPath": "英雄5：装备1方块图像路径", "unit4 item1 nameId": "英雄5：装备2序号", "unit4 item1 name": "英雄5：装备2名称", "unit4 item1 squareIconPath": "英雄5：装备2方块图像路径", "unit4 item2 nameId": "英雄5：装备3序号", "unit4 item2 name": "英雄5：装备3名称", "unit4 item2 squareIconPath": "英雄5：装备3方块图像路径", "unit5 item0 nameId": "英雄6：装备1序号", "unit5 item0 name": "英雄6：装备1名称", "unit5 item0 squareIconPath": "英雄6：装备1方块图像路径", "unit5 item1 nameId": "英雄6：装备2序号", "unit5 item1 name": "英雄6：装备2名称", "unit5 item1 squareIconPath": "英雄6：装备2方块图像路径", "unit5 item2 nameId": "英雄6：装备3序号", "unit5 item2 name": "英雄6：装备3名称", "unit5 item2 squareIconPath": "英雄6：装备3方块图像路径", "unit6 item0 nameId": "英雄7：装备1序号", "unit6 item0 name": "英雄7：装备1名称", "unit6 item0 squareIconPath": "英雄7：装备1方块图像路径", "unit6 item1 nameId": "英雄7：装备2序号", "unit6 item1 name": "英雄7：装备2名称", "unit6 item1 squareIconPath": "英雄7：装备2方块图像路径", "unit6 item2 nameId": "英雄7：装备3序号", "unit6 item2 name": "英雄7：装备3名称", "unit6 item2 squareIconPath": "英雄7：装备3方块图像路径", "unit7 item0 nameId": "英雄8：装备1序号", "unit7 item0 name": "英雄8：装备1名称", "unit7 item0 squareIconPath": "英雄8：装备1方块图像路径", "unit7 item1 nameId": "英雄8：装备2序号", "unit7 item1 name": "英雄8：装备2名称", "unit7 item1 squareIconPath": "英雄8：装备2方块图像路径", "unit7 item2 nameId": "英雄8：装备3序号", "unit7 item2 name": "英雄8：装备3名称", "unit7 item2 squareIconPath": "英雄8：装备3方块图像路径", "unit8 item0 nameId": "英雄9：装备1序号", "unit8 item0 name": "英雄9：装备1名称", "unit8 item0 squareIconPath": "英雄9：装备1方块图像路径", "unit8 item1 nameId": "英雄9：装备2序号", "unit8 item1 name": "英雄9：装备2名称", "unit8 item1 squareIconPath": "英雄9：装备2方块图像路径", "unit8 item2 nameId": "英雄9：装备3序号", "unit8 item2 name": "英雄9：装备3名称", "unit8 item2 squareIconPath": "英雄9：装备3方块图像路径", "unit9 item0 nameId": "英雄10：装备1序号", "unit9 item0 name": "英雄10：装备1名称", "unit9 item0 squareIconPath": "英雄10：装备1方块图像路径", "unit9 item1 nameId": "英雄10：装备2序号", "unit9 item1 name": "英雄10：装备2名称", "unit9 item1 squareIconPath": "英雄10：装备2方块图像路径", "unit9 item2 nameId": "英雄10：装备3序号", "unit9 item2 name": "英雄10：装备3名称", "unit9 item2 squareIconPath": "英雄10：装备3方块图像路径", "unit10 item0 nameId": "英雄11：装备1序号", "unit10 item0 name": "英雄11：装备1名称", "unit10 item0 squareIconPath": "英雄11：装备1方块图像路径", "unit10 item1 nameId": "英雄11：装备2序号", "unit10 item1 name": "英雄11：装备2名称", "unit10 item1 squareIconPath": "英雄11：装备2方块图像路径", "unit10 item2 nameId": "英雄11：装备3序号", "unit10 item2 name": "英雄11：装备3名称", "unit10 item2 squareIconPath": "英雄11：装备3方块图像路径"}
    TFTHistory_data = {}
    TFTHistory_header_keys = list(TFTHistory_header.keys())
    for i in range(len(TFTHistory_header)): #各项目初始化（Initialize every feature / column）
        key = TFTHistory_header_keys[i]
        TFTHistory_data[key] = []
    if search_LoL:
        LoLHistory_get = False
        #准备对局记录（Prepare match history）
        logPrint("开始获取英雄联盟对局记录。\nStart getting LoL match history.")
        while True:
            try:
                LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex=500")).json()
                error_occurred = False
                count = 0 #存储内部服务器错误次数（Stores the times of internal server error）
                if "errorCode" in LoLHistory:
                    if "500 Internal Server Error" in LoLHistory["message"]:
                        if not error_occurred:
                            logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                            error_occurred = True
                        while "errorCode" in LoLHistory and "500 Internal Server Error" in LoLHistory["message"] and count <= 3: #在查询艾欧尼亚和黑色玫瑰大区的对局记录时，有时会产生如下报错：An error when looking up match history on HN1 and HN10 servers might occur as follows: {'errorCode': 'RPC_ERROR', 'httpStatus': 500, 'implementationDetails': {}, 'message': 'Failed due to Error deserializing json response for GET https: //hn1-cloud-acs.lol.qq.com/v1/stats/player_history/HN1/2936900903?begIndex=0&endIndex=500: Error: Invalid value. at offset 0. given body <html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body bgcolor="white">\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>nginx/1.10.0</center>\r\n</body>\r\n</html>\r\n'}
                            count += 1
                            logPrint("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                            LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex=500")).json()
                    elif "body was empty" in LoLHistory["message"]:
                        logPrint("这位召唤师从5月1日起就没有进行过英雄联盟任何对局。\nThis summoner hasn't played any LoL game yet since May 1st.")
                        break
                if count > 3:
                    logPrint("对局记录获取失败！请等待官方修复对局记录服务！\nMatch history capture failure! Please wait for Tencent to fix the match history service!")
                    break
                logPrint("玩家%s共进行%d场英雄联盟对局。\nPlayer %s has played %d LoL matches.\n" %(get_info_name(current_info), LoLHistory["games"]["gameCount"], get_info_name(current_info), LoLHistory["games"]["gameCount"]))
            except KeyError:
                logPrint(LoLHistory)
                LoLHistory_url = "%s/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex=200" %(connection.address)
                logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续（Please open the following website, type in the username and password accordingly and press Enter to continue）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s" %(LoLHistory_url, connection.auth_key))
                cont = logInput()
                if cont == "":
                    continue
                else:
                    break
            else:
                LoLHistory_get = True
                break
        if LoLHistory_get:
            LoLMatchIDs = list(map(lambda x: x["gameId"], LoLHistory["games"]["games"]))
            #下面准备一些数据资源（Prepare some data resources）
            logPrint("正在准备英雄联盟数据资源……\nPreparing data resources for LoL ...")
            ##召唤师图标（Summoner icon）
            summonerIcons_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
            summonerIcons = {}
            for icon in summonerIcons_source:
                summonerIcons[icon["id"]] = icon
            ##英雄（LoL champion）
            LoLChampions_source = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
            LoLChampions = {}
            for champion in LoLChampions_source:
                LoLChampions[champion["id"]] = champion
            ##召唤师技能（Summoner spell）
            spells_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
            spells = {}
            for spell in spells_source:
                spells[spell["id"]] = spell
            ##英雄联盟装备（LoL item）
            LoLItems_source = await (await connection.request("GET", "/lol-game-data/assets/v1/items.json")).json()
            LoLItems = {}
            for item in LoLItems_source:
                LoLItems[item["id"]] = item
            ##符文（Perk）
            perks_source = await (await connection.request("GET", "/lol-game-data/assets/v1/perks.json")).json()
            perks = {}
            for perk in perks_source:
                perks[perk["id"]] = perk
            ##符文系（Perkstyle）
            perkstyles_source = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
            perkstyles = {}
            for perkstyle in perkstyles_source["styles"]:
                perkstyles[perkstyle["id"]] = perkstyle
            ##斗魂竞技场强化符文（Arena augment）
            CherryAugments_source = await (await connection.request("GET", "/lol-game-data/assets/v1/cherry-augments.json")).json()
            CherryAugments = {}
            for augment in CherryAugments_source:
                CherryAugments[augment["id"]] = augment
            #下面开始整理数据（Sorts out the data）
            logPrint("开始整理英雄联盟对局数据……\nStart sorting out LoL match data ...")
            for matchID in LoLMatchIDs:
                LoLGame_info = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchID}")).json()
                
                #尝试修复错误（Try to fix the error）
                if "errorCode" in LoLGame_info:
                    count = 0
                    if LoLGame_info["httpStatus"] == 404:
                        logPrint(f"未找到序号为{matchID}的回放文件！将忽略该序号。\nMatch file with matchID {matchID} not found! The program will ignore this matchID.")
                        continue
                    if "500 Internal Server Error" in LoLGame_info["message"]:
                        if not error_occurred:
                            logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                            error_occurred = True
                        while "errorCode" in LoLGame_info and "500 Internal Server Error" in LoLGame_info["message"] and count <= 3:
                            count += 1
                            logPrint("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                            LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                    elif "Connection timed out after " in LoLGame_info["message"]:
                        logPrint("对局信息保存超时！请检查网速状况！\nGame information saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                        pass
                    elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"]:
                        if not error_occurred:
                            logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                            error_occurred = True
                        while "errorCode" in LoLGame_info and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"] and count <= 3:
                            count += 1
                            logPrint("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                            LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                    if count > 3:
                        logPrint("对局%d信息获取失败！\nMatch %d information capture failure!" %(matchID, matchID))
                        pass
                
                if not "errorCode" in LoLGame_info:
                    version = LoLGame_info["gameVersion"]
                    bigVersion = ".".join(version.split(".")[:2])
                    #整理对局禁用信息（Sort out the team ban information）
                    bans_team100 = LoLGame_info["teams"][0]["bans"]
                    try:
                        bans_team200 = LoLGame_info["teams"][1]["bans"]
                    except IndexError:
                        bans = bans_team100 #空对局也会进入历史记录。空对局定义为完成选英雄但是无法正常进入游戏，而后游戏不存在的对局。而训练模式的空对局只有一方，因此LoLGame_info["teams"]中只有一个元素（Empty matches are included in the match history. An empty match is defined as the matches which can't be launched after the ChmpSlct period. Since an empty match of Practice Tool has only one team, there's only 1 element in LoLGame_info["teams"]）
                    else:
                        bans = bans_team100 + bans_team200
                    if LoLGame_info["gameMode"] == "CHERRY" and patch_compare("14.8", version):
                        bans_tmp = bans[:]
                        bans = []
                        emptyBan = {"championId": -1, "pickTurn": 0} #定义一个初始化禁用字典，用于后续数据框填充空值（Define an initialized banning dictionary so that empty values are appended to the dataframe at certain times subsequently）
                        playerSubteam = {} #存储不同子阵营的玩家，键是子阵营序号，值是该子阵营中的玩家的API序号列表（Stores different subteams' players. Keys are playerSubteamIds, and values are index lists from API for players in the subteams）
                        for i in range(len(LoLGame_info["participants"])):
                            bans.append(emptyBan.copy())
                            playerSubteamId = LoLGame_info["participants"][i]["stats"]["playerSubteamId"]
                            if not playerSubteamId in playerSubteam:
                                playerSubteam[playerSubteamId] = []
                            playerSubteam[playerSubteamId].append(i)
                        if patch_compare("14.12", version):
                            participantBanIds = []
                            for i in sorted(playerSubteam.keys()):
                                participantBanIds += [playerSubteam[i][0], playerSubteam[i][1]] #这里默认采用某个子阵营在API中记录的第一名玩家作为该子阵营的先选者。这可能与实际选用顺序有出入（Here the first player of a subteam recorded in API is considered as the player that picks a champion first. This player may not be the real first player.）
                        else:
                            participantBanIds = [playerSubteam[i][0] for i in sorted(playerSubteam.keys())] #这里默认采用某个子阵营在API中记录的第一名玩家作为禁用英雄的玩家。这可能与实际禁用英雄的玩家有出入（Here the first player of a subteam recorded in API is considered as the player that banned some champion. This player may not be the real player that banned it）
                        for i in range(len(participantBanIds)):
                            bans[participantBanIds[i]] = bans_tmp[i]
                    legacy_banData_team100_appended = legacy_banData_team200_appended = False #自定义对局中的征召模式是由每个阵营的1号选手禁用3个英雄，所以当禁用信息添加到一个阵营的第一名玩家后，后续玩家不需要再添加禁用信息。这两个逻辑变量就是用来判断这一点的（Draft mode in custom matches is performed by the first player of each team banning 3 champions, so if the ban information is added into the first player, the subsequent player in the same team doesn't need to add this information. That's what these two boolean variables are used for）
                    legacy_banData_team100_last_i = legacy_banData_team200_last_i = -1 #上面两个逻辑变量需要在切换i时才转变为真。i从0开始遍历，如果这两者在程序进行到判断禁用信息是否已添加的阶段时仍然等于-1，说明还没添加过，将它们赋值为i；一旦i发生变化，则把上面两个逻辑变量转变为真（The above two boolean variables become True only when the loop traverses the next `i`. `i` traverses from 0. When the program is going to judge whether the ban information has been added, if these two variables are still -1, then the ban information hasn't been added, and they're assigned `i`. Once `i` changes, the above two boolean variables are assigned True）
                    #判断对局序号列表中的对局是否包含主玩家（Judges whether the matches in the matchID list contain the main player）
                    participant = []
                    for i in LoLGame_info["participantIdentities"]:
                        participant.append(i["player"]["puuid"])
                    if current_puuid in participant: #之所以使用玩家通用唯一识别码，而不是用召唤师名称来识别对局是否包含主玩家，是因为该玩家可能使用过改名卡。这里也没有选择帐户序号，这是因为保存在对局中的各玩家的帐户序号竟然是0！（The reason why the puuid instead of the displayName or summonerName is used to identify whether the matches contain the main player is that the player may have used name changing card. AccountId isn't chosen here, because all players' accountIds saved in the match fetched from 127 API is 0, to my surprise!）
                        for currentParticipantId in range(len(LoLGame_info["participantIdentities"])): #定位主召唤师（Find the index of the main player in a match）
                            if LoLGame_info["participantIdentities"][currentParticipantId]["player"]["puuid"] == current_puuid or LoLGame_info["participantIdentities"][currentParticipantId]["player"]["summonerName"] == current_info["displayName"] or LoLGame_info["participantIdentities"][currentParticipantId]["player"]["gameName"] + "#" + LoLGame_info["participantIdentities"][currentParticipantId]["player"]["tagLine"] == current_summonerName:
                                break
                    #数据整理核心部分（Data assignment - core part）
                    for i in range(len(LoLGame_info["participants"])):
                        #if LoLGame_info["participantIdentities"][i]["player"]["puuid"] != "00000000-0000-0000-0000-000000000000" and not LoLGame_info["participantIdentities"][i]["player"]["puuid"] == current_puuid: #统计玩家，当然指的是不包括自己的人类玩家（Of course, the players counted are human players but not himself / herself）
                            stats = LoLGame_info["participants"][i]["stats"]
                            timeline = LoLGame_info["participants"][i]["timeline"]
                            team_participants = [participant for participant in LoLGame_info["participants"] if LoLGame_info["gameMode"] == "CHERRY" and participant["stats"]["playerSubteamId"] == stats["playerSubteamId"] or LoLGame_info["gameMode"] != "CHERRY" and participant["teamId"] == LoLGame_info["participants"][i]["teamId"]] #存储对局信息中同一队伍的玩家。斗魂竞技场对局应该使用子阵营（Store the participants of the same team from the game information. Subteam should be used to evaluate a player）
                            for j in range(len(LoLGame_info_header)):
                                key = LoLGame_info_header_keys[j]
                                if j == 0: #游戏序号（`gameIndex`）
                                    LoLGame_info_data[key].append(LoLMatchIDs.index(matchID) + 1)
                                elif j <= 12:
                                    if j == 1: #对局终止情况（`endOfGameResults`）
                                        LoLGame_info_data[key].append(endOfGameResults[LoLGame_info[key]])
                                    if j == 3: #创建日期（`gameCreationDate`）
                                        LoLGame_info_data[key].append(LoLGame_info["gameCreationDate"][:10] + " " + LoLGame_info["gameCreationDate"][11:23])
                                    elif j == 7: #游戏类型（`gameType`）
                                        LoLGame_info_data[key].append(gameTypes[LoLGame_info[key]])
                                    elif j == 11: #持续时长（`gameDuration_norm`）
                                        LoLGame_info_data[key].append(str(LoLGame_info["gameDuration"] // 60) + ":" + "%02d" %(LoLGame_info["gameDuration"] % 60))
                                    elif j == 12: #游戏模式名称（`gameModeName`）
                                        LoLGame_info_data[key].append("自定义" if LoLGame_info["queueId"] == 0 else gamemodes[LoLGame_info["queueId"]]["name"] if LoLGame_info["queueId"] in gamemodes else "")
                                    else:
                                        LoLGame_info_data[key].append(LoLGame_info[key])
                                elif j == 13: #玩家序号（`participantId`）
                                    LoLGame_info_data[key].append(LoLGame_info["participantIdentities"][i][key])
                                elif j <= 26:
                                    if j >= 25: #召唤师图标相关键（Summoner icon-related keys）
                                        profileIconId = LoLGame_info["participantIdentities"][i]["player"]["profileIcon"]
                                        if profileIconId in summonerIcons:
                                            try:
                                                LoLGame_info_data[key].append(summonerIcons[profileIconId][key.split("_")[-1]])
                                            except KeyError:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                LoLGame_info_data[key].append("")
                                        else:
                                            if not profileIconId in unmapped_keys["summonerIcon"]:
                                                unmapped_keys["summonerIcon"].add(profileIconId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, profileIconId, j, key, profileIconId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                            LoLGame_info_data[key].append(profileIconId if j == 25 else "")
                                    else:
                                        LoLGame_info_data[key].append(LoLGame_info["participantIdentities"][i]["player"][key])
                                elif j <= 39:
                                    if j == 28: #最高段位（`highestAchievedSeasonTier`）
                                        LoLGame_info_data[key].append(tiers[LoLGame_info["participants"][i][key]])
                                    elif j == 39: #阵营（`team_color`）
                                        LoLGame_info_data[key].append(team_color[LoLGame_info["participants"][i]["teamId"]])
                                    elif j >= 32 and j <= 34: #选用英雄序号相关键（`championId`-related keys）
                                        championId = LoLGame_info["participants"][i][key.split("_")[0] + "Id"]
                                        if championId in LoLChampions:
                                            LoLGame_info_data[key].append(LoLChampions[championId][key.split("_")[-1]])
                                        else:
                                            if not championId in unmapped_keys["LoLChampion"]:
                                                unmapped_keys["LoLChampion"].add(championId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                            LoLGame_info_data[key].append(championId if j == 32 else "")
                                    elif j >= 35 and j <= 38: #召唤师技能相关键（Summoner spell-related keys）
                                        spellId = LoLGame_info["participants"][i][key.split("_")[0] + "Id"]
                                        if spellId in spells:
                                            LoLGame_info_data[key].append(spells[spellId][key.split("_")[-1]])
                                        else:
                                            if not spellId in unmapped_keys["spell"]:
                                                unmapped_keys["spell"].add(spellId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, spellId, j, key, spellId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                            LoLGame_info_data[key].append(spellId if j <= 36 else "")
                                    else:
                                        LoLGame_info_data[key].append(LoLGame_info["participants"][i][key])
                                elif j <= 215:
                                    if j >= 153 and j <= 166: #英雄联盟装备相关键（LoLItems-related keys）
                                        itemId = stats[key.split("_")[0]]
                                        if itemId == 0:
                                            LoLGame_info_data[key].append("")
                                        elif itemId in LoLItems:
                                            LoLGame_info_data[key].append(LoLItems[itemId][key.split("_")[-1]])
                                        else:
                                            if not itemId in unmapped_keys["LoLItem"]:
                                                unmapped_keys["LoLItem"].add(itemId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, itemId, j, key, itemId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                            LoLGame_info_data[key].append(itemId if j <= 159 else "")
                                    elif j >= 167 and j <= 184: #符文相关键（Perks-related keys）
                                        if j <= 172:
                                            perkId = stats[key[:5]]
                                            if perkId == 0:
                                                LoLGame_info_data[key].append("")
                                            elif perkId in perks:
                                                perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                                                perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                                                perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                                                perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                                                LoLGame_info_data[key].append(perk_EndOfGameStatDescs)
                                            else:
                                                if not perkId in unmapped_keys["perk"]:
                                                    unmapped_keys["perk"].add(perkId)
                                                    logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, perkId, j, key, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                LoLGame_info_data[key].append("")
                                        else:
                                            perkId = stats[key.split("_")[0]]
                                            if perkId == 0:
                                                LoLGame_info_data[key].append("")
                                            elif perkId in perks:
                                                LoLGame_info_data[key].append(perks[perkId][key.split("_")[-1]])
                                            else:
                                                if not perkId in unmapped_keys["perk"]:
                                                    unmapped_keys["perk"].add(perkId)
                                                    logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, perkId, j, key, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                LoLGame_info_data[key].append(perkId if j <= 178 else "")
                                    elif j >= 185 and j <= 188: #符文系相关键（Perkstyles-related keys）
                                        perkstyleId = stats[key.split("_")[0]]
                                        if perkstyleId == 0:
                                            LoLGame_info_data[key].append("")
                                        elif perkstyleId in perkstyles:
                                            LoLGame_info_data[key].append(perkstyles[perkstyleId][key.split("_")[-1]])
                                        else:
                                            if not perkstyleId in unmapped_keys["perkstyle"]:
                                                unmapped_keys["perkstyle"].add(perkstyleId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, perkstyleId, j, key, perkstyleId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                            LoLGame_info_data[key].append(perkstyleId if (j - 185) % 2 == 0 else "")
                                    elif j >= 189 and j <= 206: #强化符文相关键（Augment-related keys）
                                        CherryAugmentId = stats[key.split("_")[0]]
                                        if CherryAugmentId == 0:
                                            LoLGame_info_data[key].append("")
                                        elif CherryAugmentId in CherryAugments:
                                            if j <= 194: #强化符文名称（`nameTRA`）
                                                LoLGame_info_data[key].append(CherryAugments[CherryAugmentId][key.split("_")[-1]])
                                            elif j <= 200: #强化符文图标路径（`augmentIconPath`）
                                                LoLGame_info_data[key].append(CherryAugments[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png"))
                                            else: #强化符文等级（`rarity`）
                                                LoLGame_info_data[key].append(augment_rarity[CherryAugments[CherryAugmentId][key.split("_")[-1]]])
                                        else:
                                            if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                                                unmapped_keys["CherryAugment"].add(CherryAugmentId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, CherryAugmentId, j, key, CherryAugmentId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                            LoLGame_info_data[key].append(CherryAugmentId if j <= 194 else "")
                                    elif j == 207: #子阵营（`playerSubteam_color`）
                                        LoLGame_info_data[key].append(subteam_color[stats["playerSubteamId"]])
                                    elif j == 208: #击杀/死亡/助攻（`K/D/A`）
                                        LoLGame_info_data[key].append("/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])]))
                                    elif j == 209: #战损比（`KDA`）
                                        LoLGame_info_data[key].append((stats["kills"] + stats["assists"]) / max(1, stats["deaths"]))
                                    elif j == 210: #补刀（`CS`）
                                        LoLGame_info_data[key].append(stats["neutralMinionsKilled"] + stats["totalMinionsKilled"])
                                    elif j == 211: #分均经济（`GPM`）
                                        LoLGame_info_data[key].append(0 if LoLGame_info["gameDuration"] == 0 else stats["goldEarned"] * 60 / LoLGame_info["gameDuration"])
                                    elif j == 212: #金币利用率（`GUE` - Gold Utilization Efficiency）
                                        LoLGame_info_data[key].append(0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"])
                                    elif j == 213: #分均补刀（`CSPM`）
                                        LoLGame_info_data[key].append(0 if LoLGame_info["gameDuration"] == 0 else (stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]) * 60 / LoLGame_info["gameDuration"])
                                    elif j == 214: #伤害转化率（`D/G`）
                                        LoLGame_info_data[key].append(0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"])
                                    elif j == 215: #胜负（`win/lose`）
                                        LoLGame_info_data[key].append("胜利" if stats["win"] else "失败")
                                    else:
                                        LoLGame_info_data[key].append(stats[key])
                                elif j <= 219:
                                    if bans == []: #修改说明：以前判断禁用数据是否为空是通过禁用模式进行的，如果禁用模式是经典策略就记录禁用信息，否则直接追加空值到列表中。但是在终极魔典中，先前版本记录禁用信息，后来却不记录了。因此，这里判断禁用数据是否为空，直接通过判断bans是否为空【Modification note: To judge whether the ban information of a match is empty, banMode (teams\bans) is used: if banMode is StandardBanStrategy, record the ban information; otherwise, append empty values to the list (by player_count times). But in Ultbook, ban information is recorded in previous versions but not anymore recorded later. Therefore, to judge whether the ban information is empty, whether the variable bans is empty is directly checked】
                                        LoLGame_info_data[key].append("")
                                    else:
                                        if LoLGame_info["queueId"] == 0:
                                            if LoLGame_info["participants"][i]["teamId"] == 100:
                                                if legacy_banData_team100_last_i == -1:
                                                    legacy_banData_team100_last_i = i
                                                elif legacy_banData_team100_last_i != i:
                                                    legacy_banData_team100_appended = True
                                                if not legacy_banData_team100_appended:
                                                    if j == 216:
                                                        LoLGame_info_data[key].append(list(map(lambda x: x["championId"], bans_team100)))
                                                    else:
                                                        championIds = list(map(lambda x: x["championId"], bans_team100))
                                                        to_append = []
                                                        for championId in championIds:
                                                            if championId in LoLChampions:
                                                                to_append.append(LoLChampions[championId][key.split("_")[-1]])
                                                            else:
                                                                if not championId in unmapped_keys["LoLChampion"]:
                                                                    unmapped_keys["LoLChampion"].add(championId)
                                                                    logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                                to_append.append(championId if j == 217 else "")
                                                        LoLGame_info_data[key].append(to_append)
                                                else:
                                                    LoLGame_info_data[key].append("")
                                            if LoLGame_info["participants"][i]["teamId"] == 200:
                                                if legacy_banData_team200_last_i == -1:
                                                    legacy_banData_team200_last_i = i
                                                elif legacy_banData_team200_last_i != i:
                                                    legacy_banData_team200_appended = True
                                                if not legacy_banData_team200_appended:
                                                    if j == 216:
                                                        LoLGame_info_data[key].append(list(map(lambda x: x["championId"], bans_team200)))
                                                    else:
                                                        championIds = list(map(lambda x: x["championId"], bans_team200))
                                                        to_append = []
                                                        for championId in championIds:
                                                            if championId in LoLChampions:
                                                                to_append.append(LoLChampions[championId][key.split("_")[-1]])
                                                            else:
                                                                if not championId in unmapped_keys["LoLChampion"]:
                                                                    unmapped_keys["LoLChampion"].add(championId)
                                                                    logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                                to_append.append(championId if j == 217 else "")
                                                        LoLGame_info_data[key].append(to_append)
                                                else:
                                                    LoLGame_info_data[key].append("")
                                        else:
                                            if bans[i]["championId"] == -1:
                                                LoLGame_info_data[key].append("")
                                            else:
                                                if j == 216:
                                                    LoLGame_info_data[key].append(bans[i]["championId"])
                                                else:
                                                    championId = bans[i]["championId"]
                                                    if championId in LoLChampions:
                                                        LoLGame_info_data[key].append(LoLChampions[championId][key.split("_")[-1]])
                                                    else:
                                                        if not championId in unmapped_keys["LoLChampion"]:
                                                            unmapped_keys["LoLChampion"].add(championId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%s，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %s, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLGame_info_data[key].append(championId if j == 217 else "")
                                elif j <= 221: #时间轴相关键（Timeline-related keys）
                                    LoLGame_info_data[key].append(lanes[timeline[key]] if j == 220 else roles[timeline[key]])
                                elif j == 222: #是否队友？（`ally?`）
                                    if LoLGame_info["participants"][i]["teamId"] == LoLGame_info["participants"][currentParticipantId]["teamId"] and stats["playerSubteamId"] == LoLGame_info["participants"][currentParticipantId]["stats"]["playerSubteamId"]: #如果小号出现在大号对面的阵营，以大号为主要参考（If a smurf account is against the main account, the main account is referred in priority）
                                        LoLGame_info_data[key].append(True)
                                    else:
                                        LoLGame_info_data[key].append(False)
                                else: #对局信息转换键（Keys transformed according to game information）
                                    subkey = key.split("_")[0]
                                    if key.endswith("_percent"): #团队占比键（Team percentage keys）
                                        if j == 281: #参团率（`KP_percent`）
                                            self_stat = stats["kills"] + stats["assists"]
                                            total_stat = sum(map(lambda x: x["stats"]["kills"], team_participants))
                                        elif j == 282: #补刀数占比（`CS_percent`）
                                            self_stat = stats["totalMinionsKilled"] + stats["neutralMinionsKilled"]
                                            total_stat = sum(map(lambda x: x["stats"]["totalMinionsKilled"] + x["stats"]["neutralMinionsKilled"], team_participants))
                                        else:
                                            self_stat = stats[subkey]
                                            total_stat = sum(map(lambda x: x["stats"][subkey], team_participants))
                                        value = 0 if total_stat == 0 else self_stat / total_stat
                                        LoLGame_info_data[key].append(value)
                                    else: #位次键（Order keys）
                                        if j == 342: #战损比位次（`KDA_order`）
                                            self_stat = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"])
                                            stat_list = sorted(map(lambda x: (x["stats"]["kills"] + x["stats"]["assists"]) / max(1, x["stats"]["deaths"]), team_participants), reverse = True)
                                        elif j == 343: #参团率位次（`KP_order`）
                                            self_stat = stats["kills"] + stats["assists"]
                                            stat_list = sorted(map(lambda x: x["stats"]["kills"] + x["stats"]["assists"], team_participants), reverse = True)
                                        elif j == 344: #补刀数位次（`CS_order`）
                                            self_stat = stats["totalMinionsKilled"] + stats["neutralMinionsKilled"]
                                            stat_list = sorted(map(lambda x: x["stats"]["totalMinionsKilled"] + x["stats"]["neutralMinionsKilled"], team_participants), reverse = True)
                                        elif j == 345: #伤害转化率位次（`D/G_order`）
                                            self_stat = 0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"]
                                            stat_list = sorted(map(lambda x: 0 if x["stats"]["goldEarned"] == 0 else x["stats"]["totalDamageDealtToChampions"] / x["stats"]["goldEarned"], team_participants), reverse = True)
                                        elif j == 346: #金币利用率位次（`GUE_order`）
                                            self_stat = 0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"]
                                            stat_list = sorted(map(lambda x: 0 if x["stats"]["goldEarned"] == 0 else x["stats"]["goldSpent"] / x["stats"]["goldEarned"], team_participants), reverse = True)
                                        else:
                                            self_stat = stats[subkey]
                                            stat_list = sorted(map(lambda x: x["stats"][subkey], team_participants), reverse = j != 289) #死亡次数越低，死亡位次越小（For deaths, the lower the number of deaths is, the smaller the death order is）
                                        LoLGame_info_data[key].append(0 if len(set(stat_list)) == 1 else stat_list.index(self_stat) + 1) #当所有人的数据一样时，则不用比较位次（When some stat of every player is the same, there's no need to compare it）
                    logPrint("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %s" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID), end = "\r", print_time = True)
    #数据框列序整理（Dataframe column ordering）
    recent_LoLPlayers_statistics_output_order = [0, 13, 23, 17, 24, 22, 21, 28, 5, 3, 11, 10, 6, 12, 9, 8, 222, 32, 33, 217, 218, 220, 221, 42, 35, 36, 153, 154, 155, 156, 157, 158, 159, 189, 201, 190, 202, 191, 203, 192, 204, 193, 205, 194, 206, 208, 209, 210, 213, 214, 43, 138, 139, 71, 68, 72, 51, 50, 55, 54, 53, 52, 48, 142, 128, 81, 147, 132, 140, 134, 109, 75, 144, 133, 108, 74, 143, 70, 45, 44, 136, 141, 135, 110, 76, 145, 46, 148, 151, 150, 129, 149, 58, 211, 59, 212, 137, 77, 79, 78, 146, 60, 73, 185, 187, 173, 167, 174, 168, 175, 169, 176, 170, 177, 171, 178, 172, 41, 49, 131, 56, 57, 215, 130, 234, 228, 223, 281, 224, 268, 236, 233, 237, 229, 271, 260, 246, 276, 262, 269, 264, 248, 240, 273, 263, 247, 239, 272, 235, 226, 225, 266, 270, 265, 249, 241, 274, 227, 277, 280, 279, 261, 278, 230, 231, 267, 242, 244, 243, 282, 275, 232, 238, 284, 295, 289, 283, 342, 343, 345, 285, 329, 297, 294, 298, 290, 332, 321, 307, 337, 323, 330, 325, 309, 301, 334, 324, 308, 300, 333, 296, 287, 286, 327, 331, 326, 310, 302, 335, 288, 338, 341, 340, 322, 339, 291, 292, 346, 328, 303, 304, 305, 344, 336, 293, 299]
    recent_LoLPlayers_data_organized = {}
    for i in range(len(recent_LoLPlayers_statistics_output_order)):
        key = LoLGame_info_header_keys[recent_LoLPlayers_statistics_output_order[i]]
        recent_LoLPlayers_data_organized[key] = LoLGame_info_data[key] if search_LoL and LoLHistory_get else []
    recent_LoLPlayers_df = pandas.DataFrame(data = recent_LoLPlayers_data_organized)
    recent_LoLPlayers_df = pandas.concat([pandas.DataFrame([LoLGame_info_header])[recent_LoLPlayers_df.columns], recent_LoLPlayers_df], ignore_index = True)
    if search_TFT:
        TFTHistory_get = False
        #准备对局记录（Prepare match history）
        logPrint("开始获取云顶之弈对局记录。\nStart getting TFT match history.")
        while True:
            try:
                TFTHistory = await (await connection.request("GET", f"/lol-match-history/v1/products/tft/{current_puuid}/matches?begin=0&count=500")).json()
                count = 0 #存储内部服务器错误次数（Stores the times of internal server error）
                if "errorCode" in TFTHistory:
                    if "500 Internal Server Error" in TFTHistory["message"]:
                        if not error_occurred:
                            logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                            occurred = True
                        while "errorCode" in TFTHistory and "500 Internal Server Error" in TFTHistory["message"] and count <= 3:
                            count += 1
                            logPrint("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                            TFTHistory = await (await connection.request("GET", f"/lol-match-history/v1/products/tft/{current_puuid}/matches?begin=0&count=500")).json()
                if count > 3:
                    logPrint("云顶之弈对局记录获取失败！请等待官方修复对局记录服务！\nTFT match history capture failure! Please wait for Tencent to fix the match history service!")
                    break
                logPrint("玩家%s共进行%d场云顶之弈对局。\nPlayer %s has played %d TFT matches.\n" %(get_info_name(current_info), len(TFTHistory["games"]), get_info_name(current_info), len(TFTHistory["games"])))
            except KeyError:
                if "errorCode" in TFTHistory:
                    logPrint(TFTHistory)
                    TFTHistory_url = "%s/lol-match-history/v1/products/tft/%s/matches?begin=0&count=200" %(connection.address, current_puuid)
                    logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续，或输入任意字符以切换召唤师（Please open the following website, type in the username and password accordingly and press Enter to continue or input anything to switch to another summoner）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和对局数。\nOr submit two nonnegative integers split by space to respecify the begin and count." %(TFTHistory_url, connection.auth_key))
                    cont = logInput()
                    if cont == "":
                        continue
                    else:
                        break
            else:
                TFTHistory_get = True
                break
        if TFTHistory_get:
            TFTHistory = TFTHistory["games"]
            #下面准备一些数据资源（Prepare some data resources）
            logPrint("正在准备云顶之弈数据资源……\nPreparing data resources for TFT ...")
            ##云顶之弈小小英雄（TFT companion）
            TFTCompanions_source = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
            TFTCompanions = {}
            for companion in TFTCompanions_source:
                TFTCompanions[companion["contentId"]] = companion
            ##云顶之弈羁绊（TFT Trait）
            TFTTraits_source = await (await connection.request("GET", "/lol-game-data/assets/v1/tfttraits.json")).json()
            TFTTraits = {}
            for trait in TFTTraits_source:
                trait_id = trait["trait_id"]
                conditional_trait_sets = {}
                if "conditional_trait_sets" in trait: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
                    for conditional_trait_set in trait["conditional_trait_sets"]:
                        style_idx = conditional_trait_set["style_idx"]
                        conditional_trait_sets[style_idx] = conditional_trait_set
                trait["conditional_trait_sets"] = conditional_trait_sets
                TFTTraits[trait_id] = trait
            ##云顶之弈英雄（TFT champion）
            TFTChampions_source = await (await connection.request("GET", "/lol-game-data/assets/v1/tftchampions.json")).json()
            TFTChampions = {}
            for champion in TFTChampions_source:
                TFTChampions[champion["name"]] = champion["character_record"]
            ##云顶之弈装备（TFT items）
            TFTItems_source = await (await connection.request("GET", "/lol-game-data/assets/v1/tftitems.json")).json()
            TFTItems = {}
            for item in TFTItems_source:
                TFTItems[item["id"]] = item
            version_re = re.compile(r"\d*\.\d*\.\d*\.\d*") #云顶之弈的对局版本信息是一串字符串，从中识别四位对局版本（TFT match version is a long string, from which the 4-number version is identified）
            #下面开始整理数据（Sorts out the data）
            logPrint("开始整理云顶之弈对局数据……\nStart sorting out TFT match data ...")
            for i in range(len(TFTHistory)):
                if TFTHistory[i]["json"] == {}: #对局数据记录存在异常时的处理（Exception of match data recording exception）
                    logPrint("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %s （Exceptional match neglected）" %(i + 1, len(TFTHistory), TFTHistory[i]["metadata"]["match_id"].split("_")[1]), end = "\r", print_time = True)
                else:
                    TFTHistoryJson = TFTHistory[i]["json"]
                    TFTGameVersion = version_re.search(TFTHistoryJson["game_version"]).group()
                for j in range(len(TFTHistory_header)):
                    key = TFTHistory_header_keys[j]
                    if j == 0:
                        for k in range(len(TFTHistory[i]["metadata"]["participants"])): #这里选择遍历元数据子字典中的玩家，而不是json子字典中的玩家，是因为前者不会包含电脑玩家的玩家通用唯一识别码，而后者会。显然，统计最近一起玩过的玩家数据不应当包含电脑玩家（Here the for-loop traverses the participants saved in the "metadata" sub-dictionary instead of the "json" sub-dictionary. This is becasue puuid of bot players isn't included in the former dictionary, but included in the latter dictionary. Obviously, they shouldn't counted as a recently played summoner）
                            if True or not TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid: #与自定义脚本11的一个区别是，由于可能对玩家数据进行行为评价，所以主召唤师的数据也要考虑在内（A difference between this program and Customized Program 11 is that this program may involve evaluation of player data, so the data of the main summoner should be taken into consideration）
                                TFTHistory_data[key].append(i + 1)
                    elif j <= 10:
                        for k in range(len(TFTHistory[i]["metadata"]["participants"])):
                            if True or not TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                if j == 1: #对局终止情况（`endOfGameResult`）
                                    if "endOfGameResult" in TFTHistoryJson:
                                        TFTHistory_data[key].append(endOfGameResults[TFTHistoryJson[key]])
                                    else:
                                        TFTHistory_data[key].append("")
                                elif j == 2: #对局创建时间戳（`gameCreation`）
                                    TFTHistory_data[key].append(TFTHistoryJson.get("gameCreation", "")) #14.6版本之前的云顶之弈对局信息中没有`gameCreation`这个键（The key `gameCreation` doesn't exist in information of TFT matches before Patch 14.6）
                                elif j == 6: #对局版本（`game_version`）
                                    TFTHistory_data[key].append(TFTGameVersion)
                                elif j == 8: #游戏类型（`tft_game_type`）
                                    TFTHistory_data[key].append(gamemodes[TFTHistoryJson["queue_id"]]["description"] if TFTHistoryJson["queue_id"] in gamemodes else "")
                                elif j == 9: #数据版本名称（`tft_set_core_name`）
                                    TFTHistory_data[key].append(TFTHistoryJson.get("tft_set_core_name", "")) #在云顶之弈第7赛季之前，TFTHistoryJson中无tft_set_core_name这一键（Before TFTSet7, tft_set_core_name isn't present as a key of `TFTHistoryJson`）
                                elif j == 11: #对局创建时间（`gameCreationDate`）
                                    if "gameCreation" in TFTHistoryJson:
                                        gameCreation = int(TFTHistoryJson["gameCreation"])
                                        gameCreationDate = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(gameCreation // 1000))
                                        gameCreationDate_fraction = gameCreation / 1000 - gameCreation // 1000
                                        to_append = gameCreationDate + ("{0:.3}".format(gameCreationDate_fraction))[1:5]
                                    else:
                                        to_append = ""
                                    TFTHistory_data[key].append(to_append)
                                elif j == 12: #对局结算时间（`gameDate`）
                                    game_datetime = int(TFTHistoryJson["game_datetime"])
                                    game_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(game_datetime // 1000))
                                    game_date_fraction = game_datetime / 1000 - game_datetime // 1000
                                    to_append = game_date + ("{0:.3}".format(game_date_fraction))[1:5]
                                    TFTHistory_data[key].append(to_append)
                                elif j == 13: #持续时长（`gameLength`）
                                    TFTHistory_data[key].append("%d:%02d" %(int(TFTHistoryJson["game_length"]) // 60, int(TFTHistoryJson["game_length"]) % 60))
                                else:
                                    TFTHistory_data[key].append(TFTHistoryJson[key])
                    elif j <= 42: #对于一些容易产生争议和报错的情况，引入to_append变量以简化代码。下同（Variable `to_append` is introduced to simplify the code in case of some controversy that produces errors easily. So does the following）
                        #TFTMainPlayer = TFTHistoryJson["participants"][TFT_main_player_indices[i]]
                        for k in range(len(TFTHistory[i]["metadata"]["participants"])): #这里没有遵循迭代器命名原则，因为云顶之弈对局记录的赋值代码中包含了云顶之弈对局信息的赋值代码（Here the iterator naming principle isn't followed, because assignment code of TFT game information are included in those of TFT match information）
                            TFTPlayer = TFTHistoryJson["participants"][k]
                            if j == 14: #玩家序号（`participantId`）
                                if True or not TFTPlayer["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(k + 1)
                            elif j >= 15 and j <= 23: #强化符文相关键（Augment-related keys）
                                if "augments" in TFTPlayer:
                                    augment_index = (j - 15) % 3
                                    subkey_index = (j - 15) // 3
                                    if augment_index < len(TFTPlayer["augments"]):
                                        TFTAugmentId = TFTPlayer["augments"][augment_index]
                                        if subkey_index == 0:
                                            to_append = TFTAugmentId
                                        else:
                                            to_append = ""
                                    else:
                                        to_append = ""
                                else:
                                    to_append = "" #云顶之弈刚出的时候，没有强化符文的概念（The concept of "augment" didn't appear at the beginning of TFT）
                                if True or not TFTPlayer["puuid"] == current_puuid: #此处条件判断可优化为k == TFT_main_player_indices[i]（Here the judgment can be optimized into `k == TFT_main_player_indices[i]`）
                                    TFTHistory_data[key].append(to_append)
                            elif j >= 24 and j <= 30: #小小英雄相关键（Companion-related keys）
                                TFTCompanionId = TFTPlayer["companion"]["content_ID"]
                                if j <= 27:
                                    to_append = TFTPlayer["companion"][key.split()[-1]]
                                elif TFTCompanionId in TFTCompanions:
                                    to_append = TFTCompanions[TFTCompanionId][key.split()[-1]] if j <= 29 else rarities[TFTCompanions[TFTCompanionId][key.split()[-1]]]
                                else:
                                    if not TFTCompanionId in unmapped_keys["TFTCompanion"]:
                                        unmapped_keys["TFTCompanion"].add(TFTCompanionId)
                                        logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）小小英雄信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT companion information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTCompanionId, j, key, TFTCompanionId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                    to_append = TFTCompanionId if j == 28 else ""
                                if True or not TFTPlayer["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(to_append)
                            elif j == 37 or j == 38: #玩家昵称和昵称编号（`riotIdGameName` and `riotIdTagLine`）
                                if key in TFTPlayer:
                                    to_append = TFTPlayer[key]
                                else:
                                    if TFTPlayer["puuid"] == "00000000-0000-0000-0000-000000000000": #在云顶之弈（新手教程）中，无法通过电脑玩家的玩家通用唯一识别码（00000000-0000-0000-0000-000000000000）来查询其召唤师名称和序号（Summoner names and IDs of bot players in TFT (Tutorial) can't be searched for according to their puuid: 00000000-0000-0000-0000-000000000000）
                                        to_append = ""
                                    else:
                                        TFTPlayer_info_recapture = 0
                                        TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                                        while not TFTPlayer_info["info_got"] and TFTPlayer_info["body"]["httpStatus"] != 404 and TFTPlayer_info_recapture < 3:
                                            logPrint(TFTPlayer_info["message"])
                                            TFTPlayer_info_recapture += 1
                                            logPrint("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of Player (puuid: %s) in Match %d / %d (matchID: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer["puuid"], TFTPlayer_info_recapture, TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer_info_recapture))
                                            TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                                        if TFTPlayer_info["info_got"]:
                                            TFTPlayer_info_body = TFTPlayer_info["body"]
                                            to_append = TFTPlayer_info_body["gameName"] if j == 37 else TFTPlayer_info_body["tagLine"]
                                        else:
                                            logPrint(TFTPlayer_info["message"])
                                            logPrint("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of Player (puuid: %s) in Match %d / %d (matchID: %d) capture failed!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer["puuid"], TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                            to_append = ""
                                if True or not TFTPlayer["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(to_append)
                            elif j == 41: #存活回合（`last_round_format`）
                                lastRound = TFTPlayer["last_round"]
                                if lastRound <= 3:
                                    bigRound = 1
                                    smallRound = lastRound
                                else:
                                    bigRound = (lastRound + 3) // 7 + 1
                                    smallRound = (lastRound + 3) % 7 + 1
                                to_append = "%d-%d" %(bigRound, smallRound)
                                if True or not TFTPlayer["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(to_append)
                            elif j == 42: #存活时长（`time_eliminated_norm`）
                                to_append = "%d:%02d" %(int(TFTPlayer["time_eliminated"]) // 60, int(TFTPlayer["time_eliminated"]) % 60)
                                if True or not TFTPlayer["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(to_append)
                            else:
                                to_append = TFTPlayer[key]
                                if True or not TFTPlayer["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(to_append)
                    elif j <= 133: #云顶之弈羁绊相关键（TFT trait-related keys）
                        #TFTMainPlayer_Traits = TFTHistoryJson["participants"][TFT_main_player_indices[i]]["traits"]
                        trait_index = (j - 43) // 7
                        subkey_index = (j - 43) % 7
                        for k in range(len(TFTHistory[i]["metadata"]["participants"])):
                            TFTPlayer = TFTHistoryJson["participants"][k]
                            TFTPlayer_Traits = TFTPlayer["traits"]
                            if TFTPlayer["puuid"] != "00000000-0000-0000-0000-000000000000":
                                TFTPlayer_info_recapture = 0
                                TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"]) #这里的玩家信息仅用于模板羁绊的提示（The summoner information here is only used for the prompt of TemplateTrait）
                                while not TFTPlayer_info["info_got"] and TFTPlayer_info["body"]["httpStatus"] != 404 and TFTPlayer_info_recapture < 3:
                                    logPrint(TFTPlayer_info["message"])
                                    TFTPlayer_info_recapture += 1
                                    logPrint("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of Player (puuid: %s) in Match %d / %d (matchID: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer["puuid"], TFTPlayer_info_recapture, TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer_info_recapture))
                                    TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                                if TFTPlayer_info["info_got"]:
                                    TFTPlayer_info_body = TFTPlayer_info["body"]
                                else:
                                    logPrint(TFTPlayer_info["message"])
                                    logPrint("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of Player (puuid: %s) in Match %d / %d (matchID: %d) capture failed!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer["puuid"], TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                            if trait_index < len(TFTPlayer_Traits): #在这个小于的问题上纠结了很久[敲打]——下标是从0开始的。假设API上记录了n个羁绊，那么当程序正在获取第n个羁绊时，就会引起下标越界的问题。所以这里不能使用小于等于号（I stuck at this less than sign for too long xD - note that the index begins from 0. Suppose there're totally n traits recorded in LCU API. Then, when the program is trying to capture the n-th trait, it'll throw an IndexError. That's why the "less than or equal to" sign can't be used here）
                                TFTTrait_iter = TFTPlayer_Traits[trait_index]
                                TFTTraitId = TFTTrait_iter["name"]
                                if TFTTraitId == "TemplateTrait": #CommunityDragon数据库中没有收录模板羁绊的数据（Data about TemplateTrait aren't archived in CommunityDragon database）
                                    if subkey_index == 4 and TFTPlayer["puuid"] != "00000000-0000-0000-0000-000000000000": #在艾欧尼亚的对局序号为4959597974的对局中，存在一个模板羁绊，没有tier_total这个键（There exists a TemplateTrait without the key `tier_total` in an Ionia match with matchID 4959597974）
                                        to_append = ""
                                        logPrint("警告：对局%d中玩家%s（玩家通用唯一识别码：%s）的第%d个羁绊是模板羁绊！\nWarning: Trait No. %d of the player %s (puuid: %s) in the match %d is TemplateTrait." %(TFTHistoryJson["game_id"], get_info_name(TFTPlayer_info_body), TFTPlayer["puuid"], trait_index + 1, trait_index + 1, get_info_name(TFTPlayer_info_body), TFTPlayer["puuid"], TFTHistoryJson["game_id"]))
                                    else:
                                        to_append = TFTTraitId if subkey_index == 5 else "" if subkey_index == 6 else TFTTrait_iter[key.split()[-1]]
                                else:
                                    if subkey_index <= 4:
                                        if subkey_index == 2:
                                            to_append = traitStyles[TFTTrait_iter[key.split()[-1]]]
                                        else:
                                            to_append = TFTTrait_iter[key.split()[-1]]
                                    elif TFTTraitId in TFTTraits:
                                        to_append = TFTTraits[TFTTraitId][key.split()[-1]]
                                    else:
                                        if not TFTTraitId in unmapped_keys["TFTTrait"]:
                                            unmapped_keys["TFTTrait"].add(TFTTraitId)
                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）羁绊信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT trait information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTTraitId, j, key, TFTTraitId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                        to_append = TFTTraitId if subkey_index == 5 else ""
                            else:
                                to_append = ""
                            if True or not TFTPlayer["puuid"] == current_puuid:
                                TFTHistory_data[key].append(to_append)
                    else:
                        #TFTMainPlayer_Units = TFTHistoryJson["participants"][TFT_main_player_indices[i]]["units"]
                        for k in range(len(TFTHistory[i]["metadata"]["participants"])):
                            TFTPlayer_Units = TFTHistoryJson["participants"][k]["units"]
                            if j <= 188: #云顶之弈英雄相关键（TFT champion-related keys）
                                unit_index = (j - 134) // 5
                                subkey_index = (j - 134) % 5
                                if unit_index < len(TFTPlayer_Units):
                                    TFTChampion_iter = TFTPlayer_Units[unit_index]
                                    TFTChampionId = TFTChampion_iter["character_id"]
                                    if subkey_index >= 3:
                                        #character_id_lower = TFTPlayer_Units[unit_index]["character_id"].lower()
                                        #TFTChampion_keys_lower = list(map(lambda x: x.lower(), list(TFTChampions.keys())))
                                        if TFTChampionId in TFTChampions:
                                            to_append = TFTChampions[TFTChampionId][key.split()[-1]]
                                        elif TFTChampionId.lower() in set(map(lambda x: x.lower(), TFTChampions.keys())): #在获取艾欧尼亚对局序号为8390690410的英雄信息时，由于雷克塞的英雄序号大小写的原因，会引发键异常（KeyError is caused due to the case of "RekSai" string when the program is getting data from an Ionia match with matchID 8390690410）
                                            TFTChampion_index = list(map(lambda x: x.lower(), TFTChampions.keys())).index(TFTChampionId.lower())
                                            to_append = list(TFTChampions.values())[TFTChampion_index][key.split()[-1]]
                                        else:
                                            if not TFTChampionId in unmapped_keys["TFTCompanion"]:
                                                unmapped_keys["TFTCompanion"].add(TFTChampionId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）棋子信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT champion information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTChampionId, j, key, TFTChampionId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                            to_append = TFTChampionId if subkey_index == 3 else ""
                                    else:
                                        to_append = TFTPlayer_Units[unit_index][key.split()[-1]]
                                else:
                                    to_append = ""
                                if True or not TFTHistoryJson["participants"][k]["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(to_append)
                            else:
                                unit_index = (j - 189) // 9
                                item_index = (j - 189) // 3 % 3
                                subkey_index = (j - 189) % 3
                                if unit_index < len(TFTPlayer_Units): #很少有英雄单位可以有3个装备（Merely do champion units have full items）
                                    if "itemNames" in TFTPlayer_Units[unit_index] and item_index < len(TFTPlayer_Units[unit_index]["itemNames"]):
                                        TFTItemId = TFTPlayer_Units[unit_index]["itemNames"][item_index]
                                        if subkey_index == 0:
                                            to_append = TFTItemId
                                        elif TFTItemId in TFTItems:
                                            to_append = TFTItems[TFTItemId][key.split()[-1]]
                                        else:
                                            if not TFTItemId in unmapped_keys["TFTItem"]:
                                                unmapped_keys["TFTItem"].add(TFTItemId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTItemId, j, key, TFTItemId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                            to_append = TFTItemId if subkey_index == 1 else ""
                                    elif "items" in TFTPlayer_Units[unit_index] and item_index < len(TFTPlayer_Units[unit_index]["items"]): #在12.4版本之前，装备是通过序号而不是接口名称在LCU API中被存储的（Before Patch 12.4, items are stored via itemIDs instead of itemNames）
                                        TFTItemId = TFTPlayer_Units[unit_index]["items"][item_index]
                                        if subkey_index == 0:
                                            to_append = TFTItemId
                                        elif TFTItemId in TFTItems:
                                            to_append = TFTItems[TFTItemId][key.split()[-1]]
                                        else:
                                            if not TFTItemId in unmapped_keys["TFTItem"]:
                                                unmapped_keys["TFTItem"].add(TFTItemId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTItemId, j, key, TFTItemId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                            to_append = TFTItemId if subkey_index == 1 else ""
                                    else:
                                        to_append = ""
                                else:
                                    to_append = ""
                                if True or not TFTHistoryJson["participants"][k]["puuid"] == current_puuid:
                                    TFTHistory_data[key].append(to_append)
                logPrint("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]), end = "\r", print_time = True)
    #数据框列序整理（Dataframe column ordering）
    recent_TFTPlayers_statistics_output_order = [37, 38, 36, 4, 11, 12, 6, 13, 7, 8, 28, 29, 30, 33, 41, 42, 31, 40, 35, 34, 18, 19, 20, 137, 135, 136, 190, 193, 196, 142, 140, 141, 199, 202, 205, 147, 145, 146, 208, 211, 214, 152, 150, 151, 217, 220, 223, 157, 155, 156, 226, 229, 232, 162, 160, 161, 235, 238, 241, 167, 165, 166, 244, 247, 250, 172, 170, 171, 253, 256, 259, 177, 175, 176, 262, 265, 268, 182, 180, 181, 271, 274, 277, 187, 185, 186, 280, 283, 286, 48, 44, 45, 46, 47, 55, 51, 52, 53, 54, 62, 58, 59, 60, 61, 69, 65, 66, 67, 68, 76, 72, 73, 74, 75, 83, 79, 80, 81, 82, 90, 86, 87, 88, 89, 97, 93, 94, 95, 96, 104, 100, 101, 102, 103, 111, 107, 108, 109, 110, 118, 114, 115, 116, 117, 125, 121, 122, 123, 124, 132, 128, 129, 130, 131]
    recent_TFTPlayers_data_organized = {}
    for i in range(len(recent_TFTPlayers_statistics_output_order)):
        key = TFTHistory_header_keys[recent_TFTPlayers_statistics_output_order[i]]
        recent_TFTPlayers_data_organized[key] = TFTHistory_data[key] if search_TFT and TFTHistory_get else []
    recent_TFTPlayers_df = pandas.DataFrame(data = recent_TFTPlayers_data_organized)
    recent_TFTPlayers_df = pandas.concat([pandas.DataFrame([TFTHistory_header])[recent_TFTPlayers_df.columns], recent_TFTPlayers_df], ignore_index = True)
    return {"LoL": recent_LoLPlayers_df, "TFT": recent_TFTPlayers_df}

async def sort_friend_request(connection):
    friend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
    friend_request_header = {"direction": "方向", "gameName": "玩家昵称", "icon": "召唤师图标序号", "id": "好友请求序号", "name": "显示名", "note": "备注", "pid": "社交代码", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "tagLine": "尾标", "icon title": "召唤师图标名称"}
    friend_request_header_keys = list(friend_request_header.keys())
    summonerIcons_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {}
    for icon in summonerIcons_source:
        summonerIcons[icon["id"]] = icon
    friend_request_data = {}
    for i in range(len(friend_request_header_keys)):
        key = friend_request_header_keys[i]
        friend_request_data[key] = []
    for friend_request in friend_requests:
        for i in range(len(friend_request_header_keys)):
            key = friend_request_header_keys[i]
            if i == 10:
                iconId = friend_request["icon"]
                friend_request_data[key].append(summonerIcons[iconId]["title"] if iconId in summonerIcons else "")
            else:
                friend_request_data[key].append(friend_request[key])
    friend_request_statistics_output_order = [1, 9, 7, 0, 2, 10, 5]
    friend_request_data_organized = {}
    for i in friend_request_statistics_output_order:
        key = friend_request_header_keys[i]
        friend_request_data_organized[key] = friend_request_data[key]
    friend_request_df = pandas.DataFrame(data = friend_request_data_organized)
    friend_request_df = pandas.concat([pandas.DataFrame([friend_request_header])[friend_request_df.columns], friend_request_df], ignore_index = True)
    return friend_request_df

async def sort_party_data(connection, parties: list):
    party_header = {"maxPlayers": "房间规模", "partyId": "小队序号", "queueId": "队列序号", "summoners": "已加入的召唤师序号", "queue gameMode": "游戏模式", "queue name": "游戏模式名称", "queue type": "游戏类型", "summonerNames": "已加入的召唤师名", "full?": "满员"}
    party_header_keys = list(party_header.keys())
    if isinstance(parties, list) and all(map(lambda x: isinstance(x, dict), parties)) and all(i in party for i in ["maxPlayers", "partyId", "queueId", "summoners"] for party in parties):
        queues_source = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
        queues = {}
        for queue in queues_source:
            queues[queue["id"]] = queue
        party_data = {}
        for i in range(len(party_header_keys)):
            key = party_header_keys[i]
            party_data[key] = []
        for party in parties:
            for i in range(len(party_header_keys)):
                key = party_header_keys[i]
                if i >= 4 and i <= 6:
                    party_data[key].append(queues[party["queueId"]][key.split()[1]])
                elif i == 7:
                    summonerIds = party["summoners"]
                    summonerNames = []
                    for summonerId in summonerIds:
                        member_info_recapture = 0
                        member_info = await get_info(connection, summonerId)
                        while not member_info["info_got"] and member_info["body"]["httpStatus"] != 404 and member_info_recapture < 3:
                            logPrint(member_info["message"])
                            member_info_recapture += 1
                            logPrint("成员信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an member (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(summonerId, member_info_recapture, summonerId, member_info_recapture))
                            member_info = await get_info(connection, summonerId)
                        if not member_info["info_got"]:
                            logPrint(member_info["message"])
                            logPrint("成员信息（召唤师序号：%d）获取失败！将忽略该成员。\nInformation of a member (summonerId: %d) capture failed! The program will ignore this member.")
                            summonerNames.append("")
                            continue
                        summonerNames.append(get_info_name(member_info["body"]))
                    party_data[key].append(summonerNames)
                elif i == 8:
                    party_data[key].append(party["maxPlayers"] == len(party["summoners"]))
                else:
                    party_data[key].append(party[key])
        party_statistics_output_order = [1, 0, 4, 5, 2, 8, 7]  
        party_data_organized = {}
        for i in party_statistics_output_order:
            key = party_header_keys[i]
            party_data_organized[key] = party_data[key]
        party_df = pandas.DataFrame(data = party_data_organized)
        party_df = pandas.concat([pandas.DataFrame([party_header])[party_df.columns], party_df], ignore_index = True)
    else:
        logPrint("小队数据格式错误！函数只生成空表。\nParty data format ERROR! The function will only return an empty table.")
        party_df = pandas.DataFrame(party_header, index = [0])
    return party_df

async def sort_received_invitations(connection):
    queues_source = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    queues = {}
    for queue in queues_source:
        queues[queue["id"]] = queue
    receivedInvitations = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
    invidStates = {"Pending": "等待确定", "OnHold": "搁置"}
    invidTypes = {"party": "小队", "lobby": "自定义房间"}
    invid_header = {"canAcceptInvitation": "允许接受邀请", "fromSummonerId": "邀请人召唤师序号", "fromSummonerName": "邀请人召唤师名", "invitationId": "邀请码", "invitationType": "邀请类型", "restrictions": "限制", "state": "邀请状态", "timestamp": "邀请时间戳", "fromPuuid": "邀请人玩家通用唯一识别码", "time": "邀请时间戳", "gameMode": "游戏模式", "inviteGameType": "游戏类型", "mapId": "地图序号", "queueId": "队列序号", "queue name": "队列名称"}
    invid_header_keys = list(invid_header.keys())
    invid_data = {}
    for i in range(len(invid_header_keys)):
        key = invid_header_keys[i]
        invid_data[key] = []
    for invid in receivedInvitations:
        inviter_info_recapture = 0
        inviter_info = await get_info(connection, invid["fromSummonerId"])
        while not inviter_info["info_got"] and inviter_info["body"]["httpStatus"] != 404 and inviter_info_recapture < 3:
            logPrint(inviter_info["message"])
            inviter_info_recapture += 1
            logPrint("邀请者信息（召唤师序号：%d）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an inviter (summonerId: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(invid["fromSummonerId"], inviter_info_recapture, invid["fromSummonerId"], inviter_info_recapture))
            inviter_info = await get_info(connection, invid["fromSummonerId"])
        if not inviter_info["info_got"]:
            logPrint(inviter_info["message"])
            logPrint("邀请者信息（召唤师序号：%d）获取失败！将忽略该邀请者。\nInformation of an inviter (summonerId: %d) capture failed! The program will ignore this inviter.")
        for i in range(len(invid_header_keys)):
            key = invid_header_keys[i]
            if i <= 9:
                if i == 2:
                    invid_data[key].append(get_info_name(inviter_info["body"]) if inviter_info["info_got"] else "")
                elif i == 8:
                    invid_data[key].append(inviter_info["body"]["puuid"] if inviter_info["info_got"] else "")
                elif i == 9:
                    try:
                        invid_timestamp = int(invid["timestamp"])
                    except ValueError: #自定义对局邀请的时间戳是转换好的（Custom game invitation's timestamp has already been transformed）
                        invid_data[key].append(invid["timestamp"])
                    else:
                        invid_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(invid_timestamp // 1000)))
                else:
                    invid_data[key].append(invid[key])
            elif i <= 13:
                invid_data[key].append(invid["gameConfig"][key])
            else:
                invid_data[key].append("自定义" if invid["gameConfig"]["queueId"] == -1 else queues[invid["gameConfig"]["queueId"]][key.split()[1]])
    invid_statistics_output_order = [2, 1, 8, 9, 4, 10, 11, 12, 14, 13, 3, 6, 0, 5]
    invid_data_organized = {}
    for i in invid_statistics_output_order:
        key = invid_header_keys[i]
        invid_data_organized[key] = invid_data[key]
    invid_df = pandas.DataFrame(data = invid_data_organized)
    invid_df = pandas.concat([pandas.DataFrame([invid_header])[invid_df.columns], invid_df], ignore_index = True)
    return invid_df

async def sort_muted_players(connection):
    muted_players = await (await connection.request("GET", "/lol-chat/v1/player-mutes")).json()
    muted_player_header = {"isPlayerMuted": "玩家已静音", "isSettingsMuted": "设置已静音", "isSystemMuted": "系统已静音", "obfuscatedPuuid": "隐藏识别码", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "gameName": "玩家昵称", "tagLine": "昵称编号"}
    muted_player_header_keys = list(muted_player_header.keys())
    muted_player_data = {}
    for i in range(len(muted_player_header_keys)):
        key = muted_player_header_keys[i]
        muted_player_data[key] = []
    for muted_player_puuid in muted_players:
        muted_player = muted_players[muted_player_puuid]
        muted_player_info = await get_info(connection, muted_player_puuid)
        for i in range(len(muted_player_header_keys)):
            key = muted_player_header_keys[i]
            if i >= 5:
                muted_player_data[key].append(muted_player_info["body"][key] if muted_player_info["info_got"] else "")
            else:
                muted_player_data[key].append(muted_player[key])
    muted_player_statistics_output_order = [3, 6, 7, 5, 4, 0, 1, 2]
    muted_player_data_organized = {}
    for i in muted_player_statistics_output_order:
        key = muted_player_header_keys[i]
        muted_player_data_organized[key] = muted_player_data[key]
    muted_player_df = pandas.DataFrame(data = muted_player_data_organized)
    muted_player_df = pandas.concat([pandas.DataFrame([muted_player_header])[muted_player_df.columns], muted_player_df], ignore_index = True)
    return muted_player_df

async def sort_champSelect_team(connection):
    #下面准备一些数据资源（Prepare some data resources）
    ##自己的信息（Self info）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    ##英雄（LoL champion）
    LoLChampions_source = await (await connection.request("GET", "/lol-champions/v1/inventories/%d/champions" %current_info["summonerId"])).json()
    LoLChampions = {}
    for champion in LoLChampions_source:
        LoLChampions[champion["id"]] = champion
    ##皮肤（Champion skin）
    championSkins_source = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
    championSkins = {}
    for skin in championSkins_source.values():
        championSkins[skin["id"]] = skin
        if "chromas" in skin:
            for chroma in skin["chromas"]:
                championSkins[chroma["id"]] = chroma
        if "questSkinInfo" in skin:
            for tier in skin["questSkinInfo"]["tiers"]:
                if not tier["id"] in championSkins: #圣堂皮肤和终极皮肤中的系列与主皮肤存在重复的序号（There're redundant ids between the tier and the parent ultimate skin）
                    championSkins[tier["id"]] = tier
    ##召唤师技能（Summoner spell）
    spells_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
    spells = {}
    for spell in spells_source:
        spells[spell["id"]] = spell
    ##饰品（Ward skin）
    wardSkins_source = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    wardSkins = {}
    for skin in wardSkins_source:
        wardSkins[skin["id"]] = skin
    #下面定义一些常量字典（Define some constant dictionaries）
    team_colors = {1: "蓝方", 2: "红方"}
    rarities = {"Default": "默认", "Common": "常规", "Epic": "史诗", "Legacy": "限定", "Legendary": "传说", "Mythic": "神话", "Rare": "稀有", "Ultimate": "终极", "Exalted": "圣者至尊", "Transcendant": "超凡"}
    krarities = {"kNoRarity": "其它", "kExalted": "圣堂级", "kEpic": "史诗", "kLegendary": "传说", "kMythic": "神话", "kRare": "稀有", "kUltimate": "终极", "kTranscendent": "卓越"}
    #定义英雄选择玩家数据结构（Define the champ select player data structure）
    champSelect_team_header = {"assignedPosition": "分配路线", "cellId": "槽位序号", "championId": "选用英雄序号", "championPickIntent": "声明英雄序号", "gameName": "玩家昵称", "internalName": "内置名", "isHumanoid": "电脑玩家", "nameVisibilityType": "信息可见性", "obfuscatedPuuid": "隐藏识别码", "obfuscatedSummonerId": "隐藏召唤师序号", "pickMode": "选用模式", "pickTurn": "选用顺序", "playerAlias": "玩家代号", "playerType": "玩家类型", "puuid": "玩家通用唯一识别码", "selectedSkinId": "选用皮肤序号", "spell1Id": "召唤师技能1序号", "spell2Id": "召唤师技能2序号", "summonerId": "召唤师序号", "tagLine": "昵称编号", "team": "阵营", "wardSkinId": "饰品序号", "team_color": "阵营名称", "champion name": "选用英雄名称", "champion alias": "选用英雄代号", "championPickIntent name": "声明英雄名称", "championPickIntent alias": "声明英雄代号", "selectedSkin contentId": "选用（炫彩）皮肤商品编号", "selectedSkin name": "选用（炫彩）皮肤名称", "selectedSkin splashPath": "选用（炫彩）皮肤插画", "selectedSkin uncenteredSplashPath": "选用（炫彩）皮肤原画", "selectedSkin tilePath": "选用（炫彩）皮肤方块图像", "selectedSkin loadScreenPath": "选用（炫彩）皮肤经典加载界面", "selectedSkin loadScreenVintagePath": "选用（炫彩）皮肤带边框加载界面", "selectedSkin rarity": "选用（炫彩）皮肤品质", "selectedSkin splashVideoPath": "选用（炫彩）皮肤视频", "selectedSkin chromaPath": "选用（炫彩）皮肤炫彩", "spell1 name": "召唤师技能1名称", "spell1 iconPath": "召唤师技能1图标", "spell2 name": "召唤师技能2名称", "spell2 iconPath": "召唤师技能2图标", "wardSkin name": "饰品名称", "wardSkin description": "饰品简介", "wardSkin wardImagePath": "饰品图标", "wardSkin wardShadowImagePath": "饰品阴影", "wardSkin isLegacy": "限定饰品", "wardSkin rarity": "饰品品质"}
    champSelect_team_header_keys = list(champSelect_team_header.keys())
    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
    if gameflow_phase == "ChampSelect":
        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
        players = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
        champSelect_team_data = {}
        #数据整理核心部分（Data assignment - core part）
        for i in range(len(champSelect_team_header_keys)):
            key = champSelect_team_header_keys[i]
            champSelect_team_data[key] = []
        for player in players:
            if player["nameVisibilityType"] != "HIDDEN":
                player_info_recapture = 0
                player_info = await get_info(connection, player["puuid"])
                while not player_info["info_got"] and player_info["body"]["httpStatus"] != 404 and player_info_recapture < 3:
                    logPrint(player_info["message"])
                    player_info_recapture += 1
                    logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s, cellId: %d) capture failed! Recapturing this player's information ... Times tried: %d" %(player["cellId"], player["puuid"], player_info_recapture, player["puuid"], player["cellId"], player_info_recapture))
                    player_info = await get_info(connection, player["puuid"])
                if not player_info["info_got"]:
                    logPrint(player_info["message"])
                    logPrint("槽位序号为%d的玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s, cellId: %d) capture failed!" %(player["cellId"], player["puuid"], player["puuid"], player["cellId"]))
            for i in range(len(champSelect_team_header_keys)):
                key = champSelect_team_header_keys[i]
                if i <= 21:
                    if i in {4, 5, 19}: #召唤师信息相关键（Summoner information-related keys）
                        champSelect_team_data[key].append(player[key] if player[key] != "" else player_info["body"][key] if player_info["info_got"] else "")
                    else:
                        champSelect_team_data[key].append(player[key])
                else:
                    if i == 22: #阵营名称（`team_color`）
                        champSelect_team_data[key].append(team_colors[player["team"]])
                    elif i <= 24: #选用英雄相关键（Champion-related keys）
                        champSelect_team_data[key].append(LoLChampions[player["championId"]][key.split()[1]] if player["championId"] in LoLChampions else "")
                    elif i <= 26: #声明英雄相关键（Champion pick intent-related keys）
                        champSelect_team_data[key].append(LoLChampions[player["championPickIntent"]][key.split()[1]] if player["championPickIntent"] in LoLChampions else "")
                    elif i <= 36: #选用皮肤相关键（selected skin-related keys）
                        selectedSkinId = player["selectedSkinId"]
                        if selectedSkinId in championSkins and key.split()[1] in championSkins[selectedSkinId]:
                            if i == 27 or i == 28:
                                champSelect_team_data[key].append(championSkins[selectedSkinId][key.split()[1]])
                            elif i == 34:
                                champSelect_team_data[key].append(krarities[championSkins[selectedSkinId][key.split()[1]]])
                            else:
                                iconPath = championSkins[selectedSkinId][key.split()[1]]
                                champSelect_team_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                        else:
                            champSelect_team_data[key].append("")
                    elif i <= 38: #召唤师技能1相关键（Summoner spell 1-related keys）
                        if player["spell1Id"] in spells:
                            if i == 37:
                                champSelect_team_data[key].append(spells[player["spell1Id"]][key.split()[1]])
                            else:
                                iconPath = spells[player["spell1Id"]][key.split()[1]]
                                champSelect_team_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                        else:
                            champSelect_team_data[key].append("")
                    elif i <= 40: #召唤师技能2相关键（Summoner spell 2-related keys）
                        if player["spell2Id"] in spells:
                            if i == 39:
                                champSelect_team_data[key].append(spells[player["spell2Id"]][key.split()[1]])
                            else:
                                iconPath = spells[player["spell2Id"]][key.split()[1]]
                                champSelect_team_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                        else:
                            champSelect_team_data[key].append("")
                    else: #饰品相关键（Ward-related keys）
                        if player["wardSkinId"] in wardSkins:
                            if i == 43 or i == 44:
                                iconPath = wardSkins[player["wardSkinId"]][key.split()[1]]
                                champSelect_team_data[key].append("" if iconPath == "" else urljoin(connection.address, iconPath))
                            elif i == 46:
                                champSelect_team_data[key].append(wardSkins[player["wardSkinId"]]["rarities"][0]["rarity"])
                            else:
                                champSelect_team_data[key].append(wardSkins[player["wardSkinId"]][key.split()[1]])
                        else:
                            champSelect_team_data[key].append("")
        #数据框列序整理（Dataframe column ordering）
        champSelect_team_statistics_output_order = [1, 4, 17, 5, 16, 12, 9, 8, 7, 18, 20, 0, 2, 21, 22, 3, 23, 24, 14, 35, 36, 15, 37, 38, 13, 25, 26, 32, 27, 28, 29, 30, 31, 33, 34, 19, 39, 40, 44, 43, 41, 42, 6, 10, 11]
        champSelect_team_data_organized = {}
        for i in champSelect_team_statistics_output_order:
            key = champSelect_team_header_keys[i]
            champSelect_team_data_organized[key] = champSelect_team_data[key]
        champSelect_team_df = pandas.DataFrame(data = champSelect_team_data_organized)
        for column in champSelect_team_df:
            if champSelect_team_df[column].dtype == "bool":
                champSelect_team_df[column] = champSelect_team_df[column].astype(str)
                for i in range(len(champSelect_team_df)):
                    champSelect_team_df.loc[i, column] = "√" if champSelect_team_df[column][i] == "True" else ""
        champSelect_team_df = pandas.concat([pandas.DataFrame([champSelect_team_header])[champSelect_team_df.columns], champSelect_team_df], ignore_index = True)
    else:
        champSelect_team_df = pandas.DataFrame(data = champSelect_team_header, index = [0])
    return champSelect_team_df

async def sort_capture_devices(connection):
    captureDevices = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
    captureDevices_header = {"handle": "句柄", "is_current_device": "当前设备", "is_default": "默认设备", "name": "设备名称", "usable": "可用性"}
    captureDevices_header_keys = list(captureDevices_header.keys())
    captureDevices_data = {}
    for i in range(len(captureDevices_header_keys)):
        key = captureDevices_header_keys[i]
        captureDevices_data[key] = []
    for device in captureDevices:
        for i in range(len(captureDevices_header_keys)):
            key = captureDevices_header_keys[i]
            captureDevices_data[key].append(device[key])
    captureDevices_statistics_output_order = [3, 4, 1, 2, 0]
    captureDevices_data_organized = {}
    for i in captureDevices_statistics_output_order:
        key = captureDevices_header_keys[i]
        captureDevices_data_organized[key] = captureDevices_data[key]
    captureDevices_df = pandas.DataFrame(data = captureDevices_data_organized)
    for column in captureDevices_df:
        if captureDevices_df[column].dtype == "bool":
            captureDevices_df[column] = captureDevices_df[column].astype(str)
            for i in range(len(captureDevices_df)):
                captureDevices_df.loc[i, column] = "√" if captureDevices_df[column][i] == "True" else ""
    captureDevices_df = pandas.concat([pandas.DataFrame([captureDevices_header])[captureDevices_df.columns], captureDevices_df], ignore_index = True)
    return captureDevices_df

async def sort_voice_settings(connection):
    voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
    voiceSettings_header = {"autoJoin": "自动加入语音频道", "currentCaptureDeviceHandle": "当前输入设备句柄", "inputMode": "输入模式", "localMicMuted": "已自我静音", "loopbackEnabled": "允许回环", "micLevel": "输入音量", "muteOnConnect": "连接时静音", "pttActive": "按键发言已激活", "pttKey": "按键发言热键", "vadActive": "语音活跃度已激活", "vadHangoverTime": "语音检测延迟", "vadSensitivity": "语音活跃度阈值"}
    voiceSettings_df = pandas.concat([pandas.DataFrame(voiceSettings), pandas.DataFrame(voiceSettings_header)], axis = 1)

async def sort_voice_participants(connection):
    participant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
    participant_record_header = {"displayName": "显示名", "energy": "音量强度", "isMuted": "已静音", "isSpeaking": "正在讲话", "participantId": "成员编号", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "volume": "音量", "gameName": "玩家昵称", "tagLine": "昵称编号"}
    participant_record_header_keys = list(participant_record_header.keys())
    participant_record_data = {}
    for i in range(len(participant_record_header_keys)):
        key = participant_record_header_keys[i]
        participant_record_data[key] = []
    for participant in participant_records:
        participant_info = await get_info(connection, participant["puuid"])
        for i in range(len(participant_record_header_keys)):
            key = participant_record_header_keys[i]
            if i >= 8:
                participant_record_data[key].append(participant_info["body"][key] if participant_info["info_got"] else "")
            else:
                participant_record_data[key].append(participant[key])
    participant_record_statistics_output_order = [8, 9, 6, 5, 4, 2, 7, 3, 1]
    participant_record_data_organized = {}
    for i in participant_record_statistics_output_order:
        key = participant_record_header_keys[i]
        participant_record_data_organized[key] = participant_record_data[key]
    participant_record_df = pandas.DataFrame(data = participant_record_data_organized)
    participant_record_df = pandas.concat([pandas.DataFrame([participant_record_header])[participant_record_df.columns], participant_record_df], ignore_index = True)
    return participant_record_df

async def friend_behavior_simulation(connection): #在本函数中可以看到一些查战绩脚本中涉及的数据资源。但是这里是通过LCU API来获取的，这是因为该脚本获取的数据一定是实时的，而查战绩脚本和自定义脚本11会涉及过时的数据（This function involves some data resources in Customized Program 05, except that they're obtained through LCU API in this program. This is because the data this program obtains must be real-time, while Customized Program 05 and 11 may get old data）
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    #校验客户端是否连接到聊天服务（Verify whether the League Client has connected to Riot Client chat service）
    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
    if "errorCode" in friends:
        if friends["errorCode"] == 503 and friends["message"] == "not connected to RC chat yet":
            logPrint("客户端尚未连接到聊天服务。如果这个问题持续存在，请重新登录客户端后再重新运行此脚本。\nNot connected to RC client yet. If this problem persists, please relog in and then rerun this program.")
            return 1
    #准备大区数据（Prepare server / platform data）
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
    if region == "TENCENT":
        platform_folder = "召唤师信息（Summoner Information）\\" + "国服（TENCENT）" + "\\" + platform_TENCENT[platformId]
        folder = platform_folder + "\\" + get_info_name(current_info, 2)
    elif region == "GARENA":
        platform_folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[platformId]
        folder = platform_folder + "\\" + get_info_name(current_info, 2)
    else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
        platform_folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[platformId]
        folder = platform_folder + "\\" + get_info_name(current_info, 3)
    platform_config_filepath = platform_folder + "\\" + "platform_config_namespaces.json"
    while True:
        try:
            with open(platform_config_filepath, "w", encoding = "utf-8") as fp:
                json.dump(platform_config, fp, indent = 4, ensure_ascii = False)
        except FileNotFoundError: #这里需要注意是否具有创建文件夹的权限。下同（Pay attention to the authority to create the folder. So are the following）
            os.makedirs(os.path.dirname(platform_config_filepath), exist_ok = True)
        else:
            break
    os.makedirs(folder, exist_ok = True)
    while True:
        logPrint("请选择好友操作：\nPlease select an operation on friends:\n0\t返回上一层（Return to the last step）\n1\t查看好友列表（Check the friend list）\n2\t好友分组管理（Manage the friend groups）\n3\t统计好友信息（Count friend statistics）\n4\t导出对话（Export conversations）\n5\t聊天（Chat）\n6\t好友管理（Friend management）\n7\t邀请加入游戏（Invite to game）\n8\t加入游戏（Join a game）\n9\t观战（Spectate）\n10\t玩家静音（Player mute）")
        option = logInput()
        if option == "":
            continue
        elif not option in set(map(str, range(1, 11))):
            break
        elif option == "1":
            friend_hovercard_df = await sort_friend_hovercard(connection)
            #输出到终端（Output to Terminal）
            friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "availability", "level"]
            print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print])[0], end = "\n\n")
            log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n\n")
            #保存文件（Save file）
            logPrint("是否导出以上好友数据至Excel中？（输入任意键导出，否则不导出）\nDo you want to export the above data into Excel? (Press any key to export or null to refuse exporting)")
            export_str = logInput()
            export = bool(export_str)
            if export:
                excel_name = "Friend List - %s.xlsx" %(get_info_name(current_info))
                sheet_name = platformId + "-" + get_info_name(current_info)
                while True:
                    try:
                        with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                            friend_hovercard_df.to_excel(excel_writer = writer, sheet_name = sheet_name)
                        logPrint('好友信息已保存为“%s”！\nFriend information is saved as "%s"!\n' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
                    except PermissionError:
                        logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                        logInput()
                    except FileNotFoundError:
                        with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                            friend_hovercard_df.to_excel(excel_writer = writer, sheet_name = sheet_name)
                        logPrint('好友信息已保存为“%s”！\nFriend information is saved as "%s"!\n' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
                        break
                    else:
                        break
        elif option == "2":
            friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
            friend_groupIds = list(map(lambda x: x["id"], friend_groups))
            logPrint("您一共设置了%d个分组：\nYou have %d group(s):\n" %(len(friend_groups), len(friend_groups)))
            friend_groups_df = await sort_friend_group(connection)
            friend_groups_df_to_print = friend_groups_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
            print(format_df(friend_groups_df_to_print)[0], end = "\n\n")
            log.write(format_df(friend_groups_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n\n")
            logPrint("请选择好友分组操作：\nPlease select an operation on friend groups:\n0\t返回上一层（Return to the last step）\n1\t添加分组（Add folder）\n2\t折叠/展开分组（Collapse/Expand folder）\n3\t重命名分组（Rename folder）\n*4\t排列分组顺序（Arrange folder order）\n5\t删除分组（Delete folder）\n6\t刷新好友分组（Refresh folders）")
            while True:
                action = logInput()
                if action == "":
                    continue
                if action[0] == "0":
                    break
                elif action[0] == "1":
                    logPrint("请输入新分组名称：（输入默认分组名称以退出创建）\nPlease enter the new group name: (Submit the default folder name, namely **Default, to quit creating)")
                    while True:
                        newGroupName = logInput()
                        if newGroupName == "":
                            continue
                        elif newGroupName == "**Default":
                            logPrint("请选择好友分组操作：\nPlease select an operation on friend groups:\n0\t返回上一层（Return to the last step）\n1\t添加分组（Add folder）\n2\t折叠/展开分组（Collapse/Expand folder）\n3\t重命名分组（Rename folder）\n*4\t排列分组顺序（Arrange folder order）\n5\t删除分组（Delete folder）\n6\t刷新好友分组（Refresh folders）")
                            break
                        elif newGroupName in set(friend_groups_df["name"]):
                            logPrint("该分组已存在。请使用其它名称。\nThis folder already exists. Please use another name.")
                        else:
                            body = {"name": newGroupName}
                            response = await (await connection.request("POST", "/lol-chat/v1/friend-groups", data = body)).json()
                            logPrint(response)
                            if response == None:
                                logPrint("已创建新的分组：%s。\nCreated a new folder: %s" %(newGroupName, newGroupName))
                                friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                                friend_groupIds = list(map(lambda x: x["id"], friend_groups))
                                logPrint("您一共设置了%d个分组：\nYou have %d group(s):\n" %(len(friend_groups), len(friend_groups)))
                                friend_groups_df = await sort_friend_group(connection)
                                friend_groups_df_to_print = friend_groups_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
                                print(format_df(friend_groups_df_to_print)[0], end = "\n\n")
                                log.write(format_df(friend_groups_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n\n")
                                logPrint("请输入新分组名称：\nPlease enter the new group name:")
                            else:
                                logPrint("创建分组失败。\nThe program failed to create the new folder.")
                elif action[0] == "2":
                    logPrint("请选择折叠/展开选项：\nPlease select a collapse/expand option:\n0\t返回上一层（Return to the last step）\n1\t全部展开（Expand all）\n2\t全部折叠（Collaspe all）\n3\t展开/折叠指定分组（Expand/Collapse specific groups）")
                    while True:
                        strategy = logInput()
                        if strategy == "":
                            continue
                        elif strategy[0] == "0":
                            break
                        elif strategy[0] == "1" or strategy[0] == "2":
                            for group in friend_groups:
                                body = {"collapsed": strategy[0] == "2", "name": group["name"], "priority": group["priority"]} #展开/折叠分组时，只要在链接中指定分组序号即可，即使这里没有name键（To expand / collapse a folder, specifiying the following folder id should be enough. It doesn't matter whether the key "name" exists here）
                                response = await (await connection.request("PUT", "/lol-chat/v1/friend-groups/%d" %(group["id"]), data = body)).json()
                                logPrint(response)
                                if response == None or "errorCode" in response and response["httpStatus"] == 500:
                                    if strategy[0] == "1":
                                        logPrint("已展开%s分组。\nFolder %s expanded." %(group["name"], group["name"]))
                                    else:
                                        logPrint("已折叠%s分组。\nFolder %s collapsed." %(group["name"], group["name"]))
                                elif "errorCode" in response and response["httpStatus"] == 404:
                                    logPrint("操作失败！请检查分组%s是否存在。\nAction failed! Please check if the folder %s is still there." %(group["name"], group["name"]))
                        elif strategy[0] == "3":
                            logPrint("请输入要更改展开/折叠状态的分组序号。输入-1以返回上一层。\nPlease input the group ids to switch the expansion/collapse state. Submit -1 to return to the last step.")
                            while True:
                                groupId = logInput()
                                if groupId == "":
                                    continue
                                elif groupId.startswith("-1"):
                                    break
                                elif groupId in set(map(str, friend_groupIds)):
                                    group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                                    if "errorCode" in group and group["httpStatus"] == 404:
                                        logPrint("操作失败！请检查分组是否存在。\nAction failed! Please check if the folder is still there.")
                                    else:
                                        body = {"collapsed": not(group["collapsed"]), "name": group["name"], "priority": group["priority"]}
                                        response = await (await connection.request("PUT", "/lol-chat/v1/friend-groups/%d" %(group["id"]), data = body)).json()
                                        logPrint(response)
                                        if response == None or "errorCode" in response and response["httpStatus"] == 500:
                                            if body["collapsed"]:
                                                logPrint("已折叠%s分组。\nFolder %s collapsed." %(group["name"], group["name"]))
                                            else:
                                                logPrint("已展开%s分组。\nFolder %s expanded." %(group["name"], group["name"]))
                                        elif "errorCode" in response and response["httpStatus"] == 404:
                                            logPrint("操作失败！请检查分组%s是否存在。\nAction failed! Please check if the folder %s is still there." %(group["name"], group["name"]))
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            continue
                        friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                        friend_groupIds = list(map(lambda x: x["id"], friend_groups))
                        logPrint("您一共设置了%d个分组：\nYou have %d group(s):\n" %(len(friend_groups), len(friend_groups)))
                        friend_groups_df = await sort_friend_group(connection)
                        friend_groups_df_to_print = friend_groups_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
                        print(format_df(friend_groups_df_to_print)[0], end = "\n\n")
                        log.write(format_df(friend_groups_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n\n")
                        logPrint("请选择折叠/展开选项：\nPlease select a collapse/expand option:\n1\t全部展开（Expand all）\n2\t全部折叠（Collaspe all）\n3\t展开/折叠指定分组（Expand/Collapse specific folders）")
                elif action[0] == "3":
                    logPrint("请输入要重命名的分组序号。输入-1以返回上一层。\nPlease input the group ids to rename. Submit -1 to return to the last step.")
                    while True:
                        groupId = logInput()
                        if groupId == "":
                            continue
                        elif groupId.startswith("-1"):
                            break
                        elif groupId in set(map(str, friend_groupIds)):
                            group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                            if groupId == "0":
                                logPrint("无法重命名默认分组。请换一个分组重试。\nCan't rename the default folder. Please change another folder and try again.") #重命名默认分组返回的状态值是403（The httpStatus returned by renaming the default folder is 403）
                            else:
                                logPrint("该分组的当前名称是%s。您想要将其修改为：\nThe current name for the selected folder is %s. You want to change it into:" %(group["name"], group["name"]))
                                name = logInput()
                                if name == "":
                                    logPrint("请输入要重命名的分组序号：\nPlease input the group ids to rename:")
                                    continue
                                else:
                                    body = {"collapsed": group["collapsed"], "name": name, "priority": group["priority"]}
                                    response = await (await connection.request("PUT", "/lol-chat/v1/friend-groups/%d" %(group["id"]), data = body)).json()
                                    logPrint(response)
                                    if response == None:
                                        logPrint("已重命名分组。\nRenamed the group.\n原名称（Old name）：%s新名称（New name）：%s" %(group["name"], name))
                                    else:
                                        if response["httpStatus"] == 404:
                                            logPrint("新名称已存在。请换个名字再试一次。\nNew name already exists. Please change another name and try again.")
                                        else:
                                            logPrint("重命名%s分组失败。\nRenaming the group %s failed." %(group["name"], group["name"]))
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            continue
                        friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                        friend_groupIds = list(map(lambda x: x["id"], friend_groups))
                        logPrint("您一共设置了%d个分组：\nYou have %d group(s):\n" %(len(friend_groups), len(friend_groups)))
                        friend_groups_df = await sort_friend_group(connection)
                        friend_groups_df_to_print = friend_groups_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
                        print(format_df(friend_groups_df_to_print)[0], end = "\n\n")
                        log.write(format_df(friend_groups_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n\n")
                        logPrint("请输入要重命名的分组序号：\nPlease input the group ids to rename:")
                elif action[0] == "4":
                    current_groupOrder_list = list(friend_groups_df.iloc[1:].sort_values(by = "priority", ascending = False)["id"])
                    logPrint("警告：修改好友分组排列顺序涉及较多的优先级运算，因此请不要频繁修改，否则可能导致预期之外的排列顺序。\nWarning: Rearranging friend group order involve involve a lot of priority calculations, so please don't change frequently, otherwise the folders may display in an unexpected order.\n")
                    logPrint('''请输入一个您期望的分组序号排列顺序列表，排在前面的代表显示在前，排在后面的代表显示在后。例如，如果想恢复您当前的排序，您可以输入“%s”。\nPlease input a groupId order list, where the group whose groupId index is small will be moved in the front of friend list, and vice versa. For example, if you'd like to recover the current friend group order, you may input "%s".''' %(current_groupOrder_list, current_groupOrder_list))
                    while True:
                        group_order = logInput()
                        if group_order == "":
                            continue
                        elif group_order[0] == "0":
                            break
                        else:
                            try:
                                group_order = eval(group_order)
                            except:
                                traceback_info = traceback.format_exc()
                                logPrint(traceback_info)
                                logPrint("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
                            else:
                                if isinstance(group_order, list) and all(map(lambda x: isinstance(x, int) and x in friend_groupIds, group_order)) and len(group_order) == len(set(group_order)): #这里需要严格控制输入格式：①输入的是一个列表；②列表的元素全是整型，且都是分组序号；③列表元素无重复（Here the input format are strictly controlled: ①the input is a list; ②each element in the list is of integer type and represents a group id; ③the elements are unique）
                                    priority = max(100, max(map(lambda x: x["priority"], friend_groups))) + len(group_order) #后者是为了防止优先级递减而小于原分组优先级的最大值（The addend is designed to prevent `priority` from being less than the maximum of the original group priority）
                                    error_occurred_groupArrange = False
                                    for groupId in group_order:
                                        group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                                        body = {"collapsed": group["collapsed"], "name": group["name"], "priority": priority} #请求主体中没有name键时，不仅请求速度降低，而且还会返回一个500异常信息（If the key "name" isn't in the request body, not only does the request speed slows, but the request also returns an error with a 500 httpStatus）
                                        response = await (await connection.request("PUT", f"/lol-chat/v1/friend-groups/{groupId}", data = body)).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("已将%s分组的优先级设置为%d。\nSet the priority of Group %s as %d." %(group["name"], priority, group["name"], priority))
                                        else:
                                            if response["httpStatus"] != 500:
                                                error_occurred_groupArrange = True
                                        priority -= 1
                                    if error_occurred_groupArrange:
                                        logPrint("排序过程发生了异常。请等待客户端刷新分组顺序后，或者对好友列表进行适当操作后手动排序。\nAn error occurred during ordering. Please order manually after League client refreshes the group order or you do some operations on your friend list.")
                                    else:
                                        logPrint("排序完成。请等待客户端刷新分组顺序，或者对好友列表进行适当操作以立刻刷新分组顺序。\nOrder success. Please wait for the League client to refresh the group order, or make some operations on the friend list to refersh group order immediately.")
                                    break
                                else:
                                    logPrint("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
                elif action[0] == "5":
                    logPrint("警告：删除分组将导致该分组好友全部移至默认分组。您确认要删除分组吗？（输入任意键以确认删除，否则取消删除。）\nWarning: Removing folders will cause the friends under these folders to be moved to the default group. Do you want to continue? (Input anything to confirm removal, or null to cancel.)")
                    confirm_str = logInput()
                    confirm = bool(confirm_str)
                    if confirm:
                        logPrint("请输入您要删除的分组序号。输入-1以退出。\nPlease input the id of the group to remove. Submit -1 to exit.")
                        while True:
                            groupId = logInput()
                            if groupId == "":
                                continue
                            elif groupId.startswith("-1"):
                                break
                            elif groupId in set(map(str, friend_groupIds)):
                                group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                                if groupId == "0":
                                    logPrint("无法删除默认分组。\nYou can't remove the default folder.")
                                else:
                                    response = await (await connection.request("DELETE", f"/lol-chat/v1/friend-groups/{groupId}")).json()
                                    logPrint(response)
                                    if response == None:
                                        logPrint("已删除分组%s。\nRemoved folder %s." %(group["name"], group["name"]))
                                    else:
                                        logPrint("删除分组%s失败。也许它已经被删除了。\nRemoving folder %s failed. Maybe it's already been removed." %(group["name"], group["name"]))
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                            friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                            friend_groupIds = list(map(lambda x: x["id"], friend_groups))
                            logPrint("您一共设置了%d个分组：\nYou have %d folder(s):\n" %(len(friend_groups), len(friend_groups)))
                            friend_groups_df = await sort_friend_group(connection)
                            friend_groups_df_to_print = friend_groups_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
                            print(format_df(friend_groups_df_to_print)[0], end = "\n\n")
                            log.write(format_df(friend_groups_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n\n")
                            logPrint("请输入您要删除的分组序号。输入-1以退出。\nPlease input the id of the group to remove. Submit -1 to exit.")
                friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json() #每次操作完成需要更新一下好友分组（Friend group data need an update once an action is done.）
                friend_groupIds = list(map(lambda x: x["id"], friend_groups))
                logPrint("您一共设置了%d个分组：\nYou have %d folder(s):\n" %(len(friend_groups), len(friend_groups)))
                friend_groups_df = await sort_friend_group(connection)
                friend_groups_df_to_print = friend_groups_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
                print(format_df(friend_groups_df_to_print)[0], end = "\n\n")
                log.write(format_df(friend_groups_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n\n")
                logPrint("请选择好友分组操作：\nPlease select an operation on friend groups:\n0\t返回上一层（Return to the last step）\n1\t添加分组（Add folder）\n2\t折叠/展开分组（Collapse/Expand folder）\n3\t重命名分组（Rename folder）\n*4\t排列分组顺序（Arrange folder order）\n5\t删除分组（Delete folder）\n6\t刷新好友分组（Refresh folders）")
        elif option == "3":
            friend_counts = await (await connection.request("GET", "/lol-chat/v1/friend-counts")).json()
            logPrint("好友在线/离线状态数据如下：\nFriend online/offline status is listed below:\n")
            friend_counts_data = {"项目": ["好友总数", "在线", "闲置", "队列中", "英雄选择", "游戏中", "离开", "在线分组"], "Items": ["numFriends", "numFriendsOnline", "numFriendsAvailable", "numFriendsInQueue", "numFriendsInChampSelect", "numFriendsInGame", "numFriendsAway", "numFriendsMobile"], "值": [friend_counts["numFriends"], friend_counts["numFriendsOnline"], friend_counts["numFriendsAvailable"], friend_counts["numFriendsInQueue"], friend_counts["numFriendsInChampSelect"], friend_counts["numFriendsInGame"], friend_counts["numFriendsAway"], friend_counts["numFriendsMobile"]]}
            friend_counts_df = pandas.DataFrame(data = friend_counts_data)
            print(format_df(friend_counts_df, align = "><^")[0], end = "\n\n")
            log.write(format_df(friend_counts_df, align = "><^", width_exceed_ask = False, direct_print = False)[0] + "\n\n")
        elif option == "4":
            logPrint("提示：请在客户端右侧点击你想要导出对话的好友以激活对话。\nHint: Please activate the conversation by clicking the friend whom you want to export the messages from and to at the right side of the client.")
            json1name = "Conversations - %s.json" %(get_info_name(current_info))
            if os.path.exists(os.path.join(folder, json1name)):
                with open(os.path.join(folder, json1name), "r", encoding = "utf-8") as fp:
                    conversation_json = json.load(fp)
            else:
                conversation_json = {}
            conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
            if len(conversations) > 0:
                logPrint("请选择导出对话的模式：\nPlease select a mode to export conversations:\n1\t全部导出（All）\n2\t单个导出（Single）")
                while True:
                    mode = logInput()
                    if mode == "":
                        continue
                    elif mode[0] == "0":
                        break
                    elif mode[0] == "1":
                        conversations_to_export = conversations
                    elif mode[0] == "2":
                        if len(conversations) > 0:
                            logPrint("目前已激活的对话如下：\nCurrently active conversations:")
                            conversation_df = await sort_conversation_metadata(connection)
                            print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                            log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            logPrint("请选择您想要导出的对话序号：\nPlease select a conversation to export messages:")
                            back = False
                            while True:
                                conversationIndex = logInput()
                                if conversationIndex == "":
                                    continue
                                elif conversationIndex == "-1":
                                    logPrint("目前已激活的对话如下：\nCurrently active conversations:")
                                    conversation_df = await sort_conversation_metadata(connection)
                                    print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                                    log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint("请选择您想要导出的对话序号：\nPlease select a conversation to export messages:")
                                    continue
                                elif conversationIndex[0] == "0":
                                    back = True
                                    break
                                elif conversationIndex in set(map(str, list(range(1, len(conversations) + 1)))):
                                    conversations_to_export = [conversations[int(conversationIndex) - 1]]
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if back:
                                logPrint("请选择导出对话的模式：\nPlease select a mode to export conversations:\n1\t全部导出（All）\n2\t单个导出（Single）")
                                continue
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    exported = False
                    for conversation in conversations_to_export:
                        chatId = conversation["id"]
                        messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                        if "errorCode" in messages and messages["httpStatus"] == 404:
                            continue
                        messages_sorted = sorted(messages, key = lambda x: x["timestamp"])
                        if not chatId in conversation_json:
                            conversation_json[chatId] = []
                        else:
                            old_system_messages = []
                            for message in conversation_json[chatId]:
                                if message["type"] == "system":
                                    old_system_messages.append(message)
                            for message in old_system_messages:
                                conversation_json[chatId].remove(message)
                        for message in messages_sorted:
                            if not message in conversation_json[chatId]:
                                conversation_json[chatId].append(message)
                    with open(os.path.join(folder, json1name), "w", encoding = "utf-8") as fp:
                        json.dump(conversation_json, fp, indent = 4, ensure_ascii = False)
                    for conversation in conversations_to_export:
                        chatId = conversation["id"]
                        message_df = await sort_message_data(connection, conversation_json[chatId])
                        message_df = pandas.concat([message_df.iloc[:1], message_df.iloc[1:].sort_values(by = "timestamp", ascending = True)], ignore_index = True)
                        excel_name = "Conversations - %s.xlsx" %(get_info_name(current_info))
                        sheet_name = conversation["gameName"] + "#" + conversation["gameTag"] if conversation["type"] == "chat" else conversation["id"].split("@")[0]
                        while True:
                            try:
                                with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                                    message_df.to_excel(excel_writer = writer, sheet_name = sheet_name)
                                logPrint('对话信息已导出！对话序号：%s\nConversations have been exported! Id: %s' %(conversation["id"], conversation["id"]))
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            except FileNotFoundError:
                                with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                                    message_df.to_excel(excel_writer = writer, sheet_name = sheet_name)
                                logPrint('对话信息已导出！对话序号：%s\nConversations have been exported! Id: %s' %(conversation["id"], conversation["id"]))
                                break
                            else:
                                break
                        exported = True
                    if exported:
                        logPrint('\n对话信息已保存为“%s”！\nConversation messages are saved as "%s"!\n' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
                    else: #有可能获取完对话元数据后，用户把对话关了，然后从对话获取消息就获取不到了（Chances are that the user closes the conversation after the program obtains the conversation metadata, so that the program can't get the messages）
                        logPrint("未检测到激活的对话。\nNo active conversation detected.")
                    conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
                    logPrint("请选择导出对话的模式：\nPlease select a mode to export conversations:\n1\t全部导出（All）\n2\t单个导出（Single）")
            else:
                logPrint("未检测到激活的对话。\nNo active conversation detected.")
        elif option == "5":
            global message_hint_printed
            if not message_hint_printed:
                logPrint("（提示：编辑好内容后，在终端中按Ctrl-D以插入结束字符，再按回车键发送消息。插入两个Ctrl-D以取消对话。插入三个Ctrl-D以刷新消息。如果终端不支持插入Ctrl-D字符，新建一个Python工作台，引入pyperclip库后使用pyperclip.copy(chr(4))以复制Ctrl-D实际代表的字符，再粘贴在聊天终端中，按回车键发送消息。）\n(Hint: If you finished editing the message, you must press Ctrl-D to insert the ending character and then press Enter to send the message. Append double Ctrl-D to cancel chatting. Append triple Ctrl-D to refresh messages. If the current terminal doesn't support inserting Ctrl-D character, please create a Python console, import pyperclip library and then use `pyperclip.copy(chr(4))` to copy the character that Ctrl-D actually represents. Finally, paste it into the current terminal and press Enter to send the message.)")
                message_hint_printed = True
            messageTypes = {"chat": "聊天", "groupchat": "队伍聊天", "system": "系统", "information": "通知", "celebration": "庆祝"}
            escape_sequences = {"\\n": ""} #这个变量本来是用于确定在聊天中怎么输入转义字符的。目前仅通过input()函数来输入换行符没有办法做到。参考链接：（This variable is originally intended to determine how to input an escape character in chat. It seems for now that there's no way of inputting a line feed character only using `input` function. Reference: ）https://www.educba.com/escape-sequence-in-c/
            logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")
            while True:
                situation = logInput()
                if situation == "":
                    continue
                elif situation[0] == "0":
                    break
                elif situation[0] == "1":
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    if len(friends) == 0:
                        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                    else:
                        logPrint("您的好友信息如下：\nYour friends:")
                        friend_hovercard_df = await sort_friend_hovercard(connection)
                        friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "availability", "note"]
                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                    subscope(scope)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                        logPrint("请选择一位好友：\nPlease select a friend:")
                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint("变量提示（Variable hints）：\nfriend_hovercard_df = await sort_friend_hovercard(connection)")
                        while True:
                            friend_index = logInput()
                            if friend_index == "":
                                continue
                            elif friend_index[0] == "0":
                                break
                            else:
                                try:
                                    friend_index = eval(friend_index)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(friend_index, int) and friend_index in range(1, len(friend_hovercard_df)):
                                        chatId = friend_hovercard_df.loc[friend_index, "pid"]
                                        messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                                        if "errorCode" in messages and messages["httpStatus"] == 404:
                                            logPrint("该对话尚未激活。请在客户端右边的好友列表中点击该好友，或者直接发送一条聊天类消息，以激活对话。\nThis conversation hasn't been activated yet. Please click this friend in the friend list at the right side of the client, or send a chat message directly to activate the conversation.")
                                        mTypeDict = {"1": "chat", "2": "system", "3": "information", "4": "celebration"}
                                        logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t系统（System）\n3\t通知（Information）\n4\t庆祝语（Celebration）\n5\t自定义（custom）")
                                        while True:
                                            mType = logInput()
                                            if mType == "":
                                                continue
                                            elif mType[0] == "0":
                                                logPrint("请选择一位好友：\nPlease select a friend:")
                                                print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                                log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                                logPrint("变量提示（Variable hints）：\nfriend_hovercard_df = await sort_friend_hovercard(connection)")
                                                break
                                            elif mType[0] in mTypeDict:
                                                messageType = mTypeDict[mType[0]]
                                            elif mType[0] == "5":
                                                logPrint("请输入您要发送的消息类型：\nPlease input the type of the message you want to send:")
                                                while True:
                                                    messageType = logInput()
                                                    if messageType != "":
                                                        break
                                            else:
                                                messageType = "chat"
                                            while True:
                                                messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                                                #先输出聊天记录（First output the chat history）
                                                if not "errorCode" in messages:
                                                    logPrint("聊天记录（Chat history）：\n")
                                                    for message in messages:
                                                        timestamp = message["timestamp"][:10] + " " + message["timestamp"][11:23]
                                                        fromInfo = await get_info(connection, message["fromSummonerId"])
                                                        from_summonerName = get_info_name(fromInfo["body"]) if fromInfo["info_got"] else ""
                                                        if message["type"] == "chat" or message["type"] == "groupchat":
                                                            logPrint("[%s]%s：\n%s\n" %(timestamp, from_summonerName, message["body"]))
                                                        elif message["type"] == "system":
                                                            system_messages = {"connecting": "正在连接……", "disconnected": "您已从聊天服务器断开，正在尝试重新连接……", "dropped_message": "由于发言内容或账号环境存在异常，消息发送暂时被限制，请注意账号保护并24小时后再试。", "is_blocked": "{actor}正在你的聊天黑名单中。你将不会看到它们的聊天信息。".format(actor = from_summonerName), "joined_room": "{actor}加入了队伍聊天".format(actor = from_summonerName), "left_room": "{actor}离开了队伍聊天".format(actor = from_summonerName), "no_friends": "看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。", "no_online_friends": "一个小伙伴都没在线。你知道吗，你是可以给离线的玩家发送信息的哟~", "rich_content_replaced": "请查看《英雄联盟》移动端APP里的消息", "TEXT_CHAT_MUTED": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_RESTRICTION": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_MUTED_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。", "TEXT_CHAT_RESTRICTION_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。"}
                                                            logPrint("[%s]%s\n" %(timestamp, system_messages.get(message["body"], message["body"])))
                                                        else:
                                                            logPrint("[%s](%s)%s\n" %(timestamp, messageTypes.get(message["type"], message["type"]), message["body"]))
                                                logPrint("▶ ", end = "")
                                                text = aInput()
                                                log.write(text + "\n")
                                                if text.endswith(chr(4) * 2):
                                                    continue
                                                elif text == "" or text.endswith(chr(4)): #后者用于以下场景：①终端中已经敲下回车的语句已经无法编辑，而事后又不想发送出去；②用户想要退出聊天。在这种情况下，用两个Ctrl-D结尾即可（The latter condition is used in the following situations: ②The entered words can't be edited in Terminal, but then the user doesn't want to send it out; ②The user wants to quit chatting. Under these circumstances, end the chat with double Ctrl-D will work）
                                                    logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t系统（System）\n3\t通知（Information）\n4\t庆祝语（Celebration）\n5\t自定义（custom）")
                                                    break
                                                else:
                                                    body = {"type": messageType, "body": text}
                                                    response = await (await connection.request("POST", f"/lol-chat/v1/conversations/{chatId}/messages", data = body)).json()
                                                    logPrint(response)
                                                    if "errorCode" in response:
                                                        if response["httpStatus"] == 404:
                                                            logPrint("聊天服务响应失败！请先激活对话。\nERROR response for chat service! Please activate this conversation first.")
                                                        else:
                                                            logPrint("聊天服务响应失败！\nERROR response for chat service!")
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")
                elif situation[0] == "2":
                    conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
                    conversation_df = await sort_conversation_metadata(connection)
                    if len(conversation_df) == 1: #筛选后的数据框仍包含中文标题（The filtered dataframe still includes the Chinese header）
                        logPrint("未检测到激活的对话。\nNo active conversation detected.")
                        logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")
                    else:
                        logPrint("请选择对话：\nPlease select a conversation:")
                        print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                        log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        while True:
                            conversation_index = logInput()
                            if conversation_index == "":
                                continue
                            elif conversation_index == "0":
                                logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")
                                break
                            elif conversation_index in set(map(str, range(len(conversation_df)))):
                                chatId = conversation_df.loc[int(conversation_index), "id"]
                                messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                                if "errorCode" in messages and messages["httpStatus"] == 404:
                                    logPrint("该对话尚未激活。请在客户端右边的好友列表中点击该好友，或者直接发送一条聊天类消息，以激活对话。\nThis conversation hasn't been activated yet. Please click this friend in the friend list at the right side of the client, or send a chat message directly to activate the conversation.")
                                mTypeDict = {"1": "chat", "2": "groupchat", "3": "system", "4": "information", "5": "celebration"}
                                logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                                while True:
                                    mType = logInput()
                                    if mType == "":
                                        continue
                                    elif mType[0] == "0":
                                        break
                                    elif mType[0] in mTypeDict:
                                        messageType = mTypeDict[mType[0]]
                                    elif mType[0] == "6":
                                        logPrint("请输入您要发送的消息类型：\nPlease input the type of the message you want to send:")
                                        while True:
                                            messageType = logInput()
                                            if messageType != "":
                                                break
                                    else:
                                        messageType = "chat"
                                    while True:
                                        messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{chatId}/messages")).json()
                                        #先输出聊天记录（First output the chat history）
                                        if not "errorCode" in messages:
                                            logPrint("聊天记录（Chat history）：\n")
                                            for message in messages:
                                                timestamp = message["timestamp"][:10] + " " + message["timestamp"][11:23]
                                                fromInfo = await get_info(connection, message["fromSummonerId"])
                                                from_summonerName = get_info_name(fromInfo["body"]) if fromInfo["info_got"] else ""
                                                if message["type"] == "chat" or message["type"] == "groupchat":
                                                    logPrint("[%s]%s：\n%s\n" %(timestamp, from_summonerName, message["body"]))
                                                elif message["type"] == "system":
                                                    system_messages = {"connecting": "正在连接……", "disconnected": "您已从聊天服务器断开，正在尝试重新连接……", "dropped_message": "由于发言内容或账号环境存在异常，消息发送暂时被限制，请注意账号保护并24小时后再试。", "is_blocked": "{actor}正在你的聊天黑名单中。你将不会看到它们的聊天信息。".format(actor = from_summonerName), "joined_room": "{actor}加入了队伍聊天".format(actor = from_summonerName), "left_room": "{actor}离开了队伍聊天".format(actor = from_summonerName), "no_friends": "看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。", "no_online_friends": "一个小伙伴都没在线。你知道吗，你是可以给离线的玩家发送信息的哟~", "rich_content_replaced": "请查看《英雄联盟》移动端APP里的消息", "TEXT_CHAT_MUTED": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_RESTRICTION": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_MUTED_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。", "TEXT_CHAT_RESTRICTION_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。"}
                                                    logPrint("[%s]%s\n" %(timestamp, system_messages.get(message["body"], message["body"])))
                                                else:
                                                    logPrint("[%s](%s)%s\n" %(timestamp, messageTypes.get(message["type"], message["type"]), message["body"]))
                                        logPrint("▶ ", end = "")
                                        text = aInput()
                                        log.write(text + "\n")
                                        if text.endswith(chr(4) * 2):
                                            continue
                                        elif text == "" or text.endswith(chr(4)):
                                            logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                                            break
                                        else:
                                            body = {"type": messageType, "body": text}
                                            response = await (await connection.request("POST", f"/lol-chat/v1/conversations/{chatId}/messages", data = body)).json()
                                            logPrint(response)
                                            if "errorCode" in response:
                                                if response["httpStatus"] == 404:
                                                    logPrint("聊天服务响应失败！请先激活对话。\nERROR response for chat service! Please activate this conversation first.")
                                                else:
                                                    logPrint("聊天服务响应失败！\nERROR response for chat service!")
                                conversations = await (await connection.request("GET", "/lol-chat/v1/conversations")).json()
                                conversation_df = await sort_conversation_metadata(connection)
                                if len(conversation_df) == 1:
                                    logPrint("未检测到激活的对话。\nNo active conversation detected.")
                                    logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")
                                    break
                                else:
                                    logPrint("请选择对话：\nPlease select a conversation:")
                                    print(format_df(conversation_df.iloc[1:], print_index = True, start_index = 1)[0])
                                    log.write(format_df(conversation_df.iloc[1:], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                elif situation[0] == "3":
                    logPrint("请输入社交代码：\nPlease enter the pid:")
                    while True:
                        pid = logInput()
                        if pid == "":
                            continue
                        elif pid == "0":
                            logPrint("请选择聊天场合：\nPlease select a chat situation:\n0\t返回上一层（Return to the last step）\n1\t好友聊天（Friend chat）\n2\t活动对话（Active conversation）\n3\t指定社交代码（Specify pid）")
                            break
                        else:
                            messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{pid}/messages")).json()
                            if "errorCode" in messages and messages["httpStatus"] == 404:
                                logPrint("该对话尚未激活。如果这是一位好友的社交代码，请在客户端右边的好友列表中点击该好友，或者直接发送一条聊天类消息，以激活对话。\nThis conversation hasn't been activated yet. If this is a friend's pid, please click this friend in the friend list at the right side of the client, or send a chat message directly to activate the conversation.")
                            mTypeDict = {"1": "chat", "2": "groupchat", "3": "system", "4": "information", "5": "celebration"}
                            logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                            while True:
                                mType = logInput()
                                if mType == "":
                                    continue
                                elif mType[0] == "0":
                                    logPrint("请输入社交代码：\nPlease enter the pid:")
                                    break
                                elif mType[0] in mTypeDict:
                                    messageType = mTypeDict[mType[0]]
                                elif mType[0] == "6":
                                    logPrint("请输入您要发送的消息类型：\nPlease input the type of the message you want to send:")
                                    while True:
                                        messageType = logInput()
                                        if messageType != "":
                                            break
                                else:
                                    messageType = "chat"
                                while True:
                                    messages = await (await connection.request("GET", f"/lol-chat/v1/conversations/{pid}/messages")).json()
                                    #先输出聊天记录（First output the chat history）
                                    if not "errorCode" in messages:
                                        logPrint("聊天记录（Chat history）：\n")
                                        for message in messages:
                                            timestamp = message["timestamp"][:10] + " " + message["timestamp"][11:23]
                                            fromInfo = await get_info(connection, message["fromSummonerId"])
                                            from_summonerName = get_info_name(fromInfo["body"]) if fromInfo["info_got"] else ""
                                            if message["type"] == "chat" or message["type"] == "groupchat":
                                                logPrint("[%s]%s：\n%s\n" %(timestamp, from_summonerName, message["body"]))
                                            elif message["type"] == "system":
                                                system_messages = {"connecting": "正在连接……", "disconnected": "您已从聊天服务器断开，正在尝试重新连接……", "dropped_message": "由于发言内容或账号环境存在异常，消息发送暂时被限制，请注意账号保护并24小时后再试。", "is_blocked": "{actor}正在你的聊天黑名单中。你将不会看到它们的聊天信息。".format(actor = from_summonerName), "joined_room": "{actor}加入了队伍聊天".format(actor = from_summonerName), "left_room": "{actor}离开了队伍聊天".format(actor = from_summonerName), "no_friends": "看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。", "no_online_friends": "一个小伙伴都没在线。你知道吗，你是可以给离线的玩家发送信息的哟~", "rich_content_replaced": "请查看《英雄联盟》移动端APP里的消息", "TEXT_CHAT_MUTED": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_RESTRICTION": "由于为其他玩家带来了负面游戏体验，你的聊天功能已受到限制。", "TEXT_CHAT_MUTED_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。", "TEXT_CHAT_RESTRICTION_LIFTED": "你的聊天功能限制已解除。记住，清晰且有礼貌的发言是一支队伍一起获胜的关键。"}
                                                logPrint("[%s]%s\n" %(timestamp, system_messages.get(message["body"], message["body"])))
                                            else:
                                                logPrint("[%s](%s)%s\n" %(timestamp, messageTypes.get(message["type"], message["type"]), message["body"]))
                                    logPrint("▶ ", end = "")
                                    text = aInput()
                                    log.write(text + "\n")
                                    if text.endswith(chr(4) * 2):
                                        continue
                                    elif text == "" or text.endswith(chr(4)):
                                        logPrint("请选择您要发送的消息类型：\nPlease select the type of the message you want to send:\n0\t返回上一层（Return to the last step）\n1\t聊天（Chat）\n2\t小队聊天（Groupchat）\n3\t系统（System）\n4\t通知（Information）\n5\t庆祝语（Celebration）\n6\t自定义（custom）")
                                        break
                                    else:
                                        body = {"type": messageType, "body": text}
                                        response = await (await connection.request("POST", f"/lol-chat/v1/conversations/{pid}/messages", data = body)).json()
                                        logPrint(response)
                                        if "errorCode" in response:
                                            if response["httpStatus"] == 404:
                                                logPrint("聊天服务响应失败！请先激活对话。\nERROR response for chat service! Please activate this conversation first.")
                                            else:
                                                logPrint("聊天服务响应失败！\nERROR response for chat service!")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option == "6": #好友管理涉及添加好友、同意/拒绝好友请求、移动好友、修改好友备注、删除好友、拉黑
            logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
            while True:
                action = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    logPrint("已经知道好友的召唤师昵称#尾标？快给TA发送好友请求吧！请输入您想要添加的玩家名称：\nAlready know your friend’s Riot ID? Send them a friend request! Please submit the Riot IDs of the player(s) you want to make friend with:")
                    while True:
                        friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                        friend_puuids = set(map(lambda x: x["puuid"], friends))
                        prefriend_name = logInput()
                        prefriend_exist = False
                        if prefriend_name == "":
                            #logPrint("玩家名字不能为空！\nPlayer name cannot be blank!")
                            continue
                        elif prefriend_name == "0":
                            logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                            break
                        else:
                            prefriend_info = await get_info(connection, prefriend_name)
                            if prefriend_info["info_got"]:
                                if prefriend_info["selfInfo"]:
                                    logPrint("你无法把自己加为好友，亲～\nYou cannot friend yourself, silly xD")
                                    continue
                                elif prefriend_info["body"]["puuid"] in friend_puuids:
                                    logPrint("你和%s已经是好友了。\nYou and %s are already friends." %(get_info_name(prefriend_info["body"]), get_info_name(prefriend_info["body"])))
                                    continue
                                else:
                                    if prefriend_info["searchType"] == "puuid":
                                        body = {"puuid": prefriend_name}
                                    elif prefriend_info["searchType"] == "riotId":
                                        prefriend_gameName, prefriend_tagLine = prefriend_name.split("#")
                                        body = {"gameName": prefriend_gameName, "tagLine": prefriend_tagLine}
                                    response = await (await connection.request("POST", "/lol-chat/v2/friend-requests", data = body)).json() #由于该接口的报错信息过于单一，这里只能自己设置报错机制。来源：rcp-fe-lol-social/global/zh_cn/trans.json（Because the error information from endpoint turns out to be too simple, here the error feedback is set manually. Reference: rcp-fe-lol-social/global/zh_cn/trans.json）
                                    logPrint(response)
                            else:
                                logPrint(prefriend_info["message"])
                            if prefriend_info["info_got"]:
                                if response == None:
                                    logPrint("已给这位用户发送了请求。如果该用户接受了你的请求，那么你就可以看到该用户处于在线状态。\nA request has been sent to this user. You will see them online if they accept your request.")
                                else:
                                    if response["httpStatus"] == 403:
                                        logPrint("你无法把自己加为好友，亲～\nYou cannot friend yourself, silly xD")
                                    elif response["httpStatus"] == 404:
                                        logPrint("该玩家名字不存在。\nThis player name doesn't exist.")
                                    elif response["httpStatus"] == 405:
                                        logPrint("该玩家在聊天黑名单中。请将其移出聊天黑名单并重试。\nThis player is blocked. Please unblock his/her and try again.")
                                    elif response["httpStatus"] == 409:
                                        logPrint("您在该玩家的聊天黑名单中。\nYou're blocked by this player.")
                                    elif response["httpStatus"] == 500:
                                        logPrint("内部服务器错误。可能原因如下：\n1. 该玩家名字包含了无效字符。\n2. 您发送和接收的好友请求数量总和已满50个。\n3. 您的好友数量和发送和接受的好友请求数量总和的和已满375个。\n4. 你的账号受限，无法发送好友请求。请稍后再试或联系客服寻求帮助。\nInternal server error. A possible reason may be:\n1. This player name contains invalid characters.\n2. You can't sent and receive more than 50 friend requests at the same time.\n3. The sum of your friend count and the total number of friend requests sent and received has reached 375.\n4. Your account is restricted from sending friend requests. Please try again later or contact customer service for help.")
                                    elif response["httpStatus"] == 503:
                                        logPrint("发送好友请求的过程响应失败。\nError response for POST /chat/v6/friendrequests: ")
                                    else:
                                        logPrint(response)
                elif action[0] == "2":
                    friend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
                    if "errorCode" in friend_requests:
                        if friend_requests["httpStatus"] == 503 and friend_requests["message"] == "Error response for GET /chat/v6/friendrequests: ": #获取新玩家的好友请求会返回此信息（Getting a new player's friend request will return this information）
                            logPrint("好友请求获取失败！\nError response for GET /chat/v6/friendrequests!")
                        else:
                            logPrint("好友请求获取失败！\nFriend request data capture failure!")
                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                    else:
                        if len(friend_requests) == 0:
                            logPrint("您尚未发送或收到任何好友请求。\nYou haven't sent or received any friend request.")
                        else:
                            logPrint("您的好友请求如下：\nYour friend requests:")
                            friend_request_df = await sort_friend_request(connection)
                            friend_request_fields_to_print = ["gameName", "tagLine", "direction", "icon title"]
                            print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
                            log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            logPrint("请选择好友请求处理模式：\nPlease select a mode to handle friend requests:\n0\t返回上一层（Return to the last step）\n1\t单个处理（Single）\n2\t批量处理（In batches）\n3\t全部处理（All）")
                            while True:
                                index_got = False
                                mode = logInput()
                                if mode == "":
                                    continue
                                elif mode == "0":
                                    logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                                    break
                                elif mode == "1":
                                    logPrint("请选择要处理的好友请求：\nPlease enter the index of the friend request to handle:")
                                    while True:
                                        handle_input = logInput()
                                        if handle_input == "":
                                            continue
                                        elif handle_input == "0":
                                            break
                                        elif handle_input in set(map(str, range(1, len(friend_request_df)))):
                                            handle_indices = [int(handle_input)]
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                elif mode == "2":
                                    logPrint("是否需要对好友请求取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend request data? (Submit any non-empty string to make a draft, or null to input the friend request index directly.)")
                                    draft_str = logInput()
                                    draft = bool(draft_str)
                                    if draft:
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        while True:
                                            draft_option = logInput()
                                            if draft_option == "":
                                                continue
                                            elif draft_option[0] == "0":
                                                break
                                            elif draft_option[0] == "1":
                                                scope = {"format_df": format_df, "df": friend_request_df.copy(deep = True), "fields": friend_request_fields_to_print}
                                                logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["direction"] == "out")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                subscope(scope)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    logPrint('请输入要处理的好友请求的索引（见下面好友请求表的索引列）。一些允许的输入格式：\nPlease submit the indices of friend requests to handle (you may refer to the index column of the friend request table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friend_requests)) if friend_requests[i]["gameName"] == "WordlessMeteor"]')
                                    print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint('变量提示（Variable hints）：\nfriend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()\nfriend_request_df = await sort_friend_request(connection)')
                                    while True:
                                        handle_str = logInput()
                                        if handle_str == "":
                                            continue
                                        elif handle_str[0] == "0":
                                            break
                                        elif handle_str == "all":
                                            handle_indices = list(range(1, len(friend_request_df)))
                                            index_got = True
                                            break
                                        else:
                                            try:
                                                handle_indices = eval(handle_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            else:
                                                if isinstance(handle_indices, int):
                                                    handle_indices = [handle_indices]
                                                elif not isinstance(handle_indices, list):
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                        if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_request_df), handle_indices)) and len(handle_indices) == len(set(handle_indices)):
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                elif mode == "3":
                                    handle_indices = list(range(1, len(friend_request_df)))
                                    index_got = True
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if index_got:
                                    logPrint("您选择了以下%d个好友请求：\nYou selected the following %d friend request(s): " %(len(handle_indices), len(handle_indices)))
                                    print(format_df(friend_request_df.loc[handle_indices, friend_request_fields_to_print], print_header = True, print_index = True, reserve_index = True)[0])
                                    log.write(format_df(friend_request_df.loc[handle_indices, friend_request_fields_to_print], print_header = True, width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                    logPrint("请选择对好友请求的处理：\nPlease decide how to deal with this friend request:\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝/取消（Reject/Cancel）\n3\t拉入聊天黑名单（Block）")
                                    while True:
                                        method = logInput()
                                        if method == "":
                                            continue
                                        elif method[0] == "0":
                                            break
                                        elif method[0] in {"1", "2", "3"}:
                                            for requestId in handle_indices:
                                                prefriend_summonerName = friend_request_df.loc[requestId, "gameName"] + "#" + friend_request_df.loc[requestId, "tagLine"]
                                                prefriend_puuid = friend_request_df.loc[requestId, "puuid"]
                                                friend_request_direction = friend_request_df.loc[requestId, "direction"]
                                                if method[0] == "1":
                                                    if friend_request_direction == "in":
                                                        body = {"puuid": prefriend_puuid} #选用玩家通用唯一识别码作为请求主体，是考虑到它的不变性（Puuid is chosen as the request body, considering its invariability）
                                                        response = await (await connection.request("POST", "/lol-chat/v2/friend-requests", data = body)).json() #两个人成为好友，等价于两个人互相承认对方为自己的好友。这话说着有点文绉绉的……说白了就是双方都向对方发起好友申请（If two guys become friends, that means they admit the other to be their friends. This may sound obscure ... In brief, that means the two guys both send friend requests to each other）
                                                        logPrint(response)
                                                        if response == None:
                                                            logPrint("您同意了%s的好友请求。\nYou accepted the friend request from %s." %(prefriend_summonerName, prefriend_summonerName))
                                                        else:
                                                            logPrint("您未能成功同意%s的好友请求。\nYou failed to accept the friend request from %s." %(prefriend_summonerName, prefriend_summonerName))
                                                    else:
                                                        logPrint("该操作不适用于当前好友请求。\nThis operation doesn't apply to the current friend request.")
                                                elif method[0] == "2":
                                                    response = await (await connection.request("DELETE", "/lol-chat/v2/friend-requests/%s" %(prefriend_puuid))).json()
                                                    logPrint(response)
                                                    if response == None:
                                                        if friend_request_direction == "in":
                                                            logPrint("您拒绝了%s的好友请求。\nYou rejected the friend request from %s." %(prefriend_summonerName, prefriend_summonerName))
                                                        elif friend_request_direction == "out":
                                                            logPrint("您取消了对%s发起的好友请求。\nYou canceled the friend request to %s." %(prefriend_summonerName, prefriend_summonerName))
                                                    else:
                                                        if friend_request_direction == "in":
                                                            logPrint("您未能成功拒绝%s的好友请求。也许您已经处理了该玩家的好友请求，或者该玩家取消了对您发起的好友请求。\nYou failed to reject the friend request from %s. Maybe you've already handled this friend request, or he/she canceled it." %(prefriend_summonerName, prefriend_summonerName))
                                                        elif friend_request_direction == "out":
                                                            logPrint("您未能成功取消对%s发起的好友请求。也许该玩家已经处理了您的好友请求，或者您取消了对该玩家发起的好友请求。\nYou failed to cancel the friend request to %s. Maybe he/she's already handled your friend request, or you canceled it." %(prefriend_summonerName, prefriend_summonerName))
                                                else:
                                                    logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.)' %(prefriend_summonerName, prefriend_summonerName))
                                                    block_confirm_str = logInput()
                                                    block_confirm = bool(block_confirm_str == "block")
                                                    if block_confirm:
                                                        body = {"puuid": prefriend_puuid}
                                                        response = await (await connection.request("POST", "/lol-chat/v1/blocked-players", data = body)).json()
                                                        logPrint(response)
                                                        if response == None:
                                                            logPrint("您已将%s拉入聊天黑名单。\nYou've blocked %s." %(prefriend_summonerName, prefriend_summonerName))
                                                        else:
                                                            logPrint("您未能成功将%s拉入聊天黑名单。可能TA已经在您的聊天黑名单里了。\nYou failed to block %s. Maybe he/she's been blocked some time before." %(prefriend_summonerName, prefriend_summonerName))
                                            logPrint("请选择对好友请求的处理：\nPlease decide how to deal with this friend request:\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝/取消（Reject/Cancel）\n3\t拉入聊天黑名单（Block）")
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                friend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
                                if len(friend_requests) == 0:
                                    logPrint("您尚未发送或收到任何好友请求。\nYou haven't sent or received any friend request.")
                                    logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                                    break
                                else:
                                    logPrint("您的好友请求如下：\nYour friend requests:")
                                    friend_request_df = await sort_friend_request(connection)
                                    friend_request_fields_to_print = ["gameName", "tagLine", "direction", "icon title"]
                                    print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], width_exceed_ask = False, direct_print = False, print_header = True, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint("请选择好友请求处理模式：\nPlease select a mode to handle friend requests:\n0\t返回上一层（Return to the last step）\n1\t单个处理（Single）\n2\t批量处理（In batches）\n3\t全部处理（All）")
                elif action[0] == "3":
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    if len(friends) == 0:
                        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                    else:
                        logPrint("您的好友分组信息如下：\nFriend group distribution:")
                        friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends)) #这三个列表一定是一一对应的，且列表元素无重复（These three lists must follow one-to-one correspondence, and there must be no repetitive elements in them all）
                        friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                        friend_puuids = list(map(lambda x: x["puuid"], friends))
                        friend_pids = list(map(lambda x: x["pid"], friends))
                        friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                        friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupId", "groupName"]
                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint("请选择移动模式：\nPlease select a moving mode:\n0\t返回上一层（Return to the last step）\n1\t单个移动（Single）\n2\t批量移动（In batches）\n3\t全部移动（All）")
                        while True:
                            index_got = False
                            mode = logInput()
                            if mode == "":
                                continue
                            elif mode == "0":
                                logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                                break
                            elif mode == "1":
                                logPrint("请输入要移动的好友索引或者名称：\nPlease enter the index or name of the friend to move:")
                                while True:
                                    move_input = logInput()
                                    if move_input == "":
                                        continue
                                    else:
                                        try:
                                            friend_index = int(move_input) - 1
                                        except ValueError:
                                            friend_summonerName = move_input
                                            if friend_summonerName in friend_summonerNames:
                                                friend_index = friend_summonerNames.index(friend_summonerName)
                                            elif friend_summonerName in set(map(str, friend_summonerIds)):
                                                friend_index = friend_summonerIds.index(int(friend_summonerName))
                                            elif friend_summonerName in friend_puuids:
                                                friend_index = friend_puuids.index(friend_summonerName)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                        else:
                                            if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                                break
                                            elif not friend_index in range(len(friends)):
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                    move_indices = [friend_index]
                                    index_got = True
                                    break
                            elif mode == "2":
                                logPrint("请选择您输入要移动的好友信息的方式：\nPlease select a method of inputting the information of your friends to be moved to other groups:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                                while True:
                                    method = logInput()
                                    if method == "":
                                        continue
                                    elif method[0] == "0":
                                        break
                                    elif method[0] == "1":
                                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                                        draft_str = logInput()
                                        draft = bool(draft_str)
                                        if draft:
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                            while True:
                                                draft_option = logInput()
                                                if draft_option == "":
                                                    continue
                                                elif draft_option[0] == "0":
                                                    break
                                                elif draft_option[0] == "1":
                                                    scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                    subscope(scope)
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        logPrint('请输入要移动的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to move (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                        logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                                        while True:
                                            move_str = logInput()
                                            if move_str == "":
                                                continue
                                            elif move_str[0] == "0":
                                                break
                                            elif move_str == "all":
                                                move_indices = list(range(len(friends)))
                                                index_got = True
                                                break
                                            else:
                                                try:
                                                    move_indices = eval(move_str)
                                                except:
                                                    traceback_info = traceback.format_exc()
                                                    logPrint(traceback_info)
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                                else:
                                                    if isinstance(move_indices, int):
                                                        move_indices = [move_indices]
                                                    elif not isinstance(move_indices, list):
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                            if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), move_indices)) and len(move_indices) == len(set(move_indices)):
                                                move_indices = list(map(lambda x: x - 1, move_indices))
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    elif method[0] == "2":
                                        logPrint('''请输入要移动的好友的召唤师名。每个好友的召唤师名格式为{玩家昵称}#{昵称编号}。输入“-1”以结束输入。\nPlease submit the names of the friends to be moved. Each friend's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)''')
                                        move_indices = []
                                        while True:
                                            friend_summonerName = logInput()
                                            if friend_summonerName == "":
                                                continue
                                            elif friend_summonerName == "0":
                                                index_got = False
                                                break
                                            elif friend_summonerName == "-1":
                                                break
                                            else:
                                                try:
                                                    friend_summonerName_list = eval(friend_summonerName)
                                                except:
                                                    friend_summonerName_list = [friend_summonerName]
                                                else:
                                                    if isinstance(friend_summonerName_list, list) and all(map(lambda x: isinstance(x, (str, int)), friend_summonerName_list)):
                                                        pass
                                                    else:    
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                                for friend_summonerName in friend_summonerName_list:
                                                    if friend_summonerName in friend_summonerNames:
                                                        friend_index = friend_summonerNames.index(friend_summonerName)
                                                    elif friend_summonerName in friend_summonerIds:
                                                        friend_index = friend_summonerIds.index(friend_summonerName)
                                                    elif friend_summonerName in set(map(str, friend_summonerIds)):
                                                        friend_index = friend_summonerIds.index(int(friend_summonerName))
                                                    elif friend_summonerName in friend_puuids:
                                                        friend_index = friend_puuids.index(friend_summonerName)
                                                    else:
                                                        logPrint("%s不是一个合法的召唤师名、召唤师序号或者玩家通用唯一识别码。\n%s isn't a legal summoner name, summonerId or puuid." %(friend_summonerName, friend_summonerName))
                                                        continue
                                                    if not friend_index in move_indices:
                                                        move_indices.append(friend_index)
                                                        index_got = True
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    if index_got:
                                        break
                                    logPrint("请选择您输入要移动的好友信息的方式：\nPlease select a method of inputting the information of your friends to be moved to other groups:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                            elif mode == "3":
                                move_indices = list(range(len(friends)))
                                index_got = True
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                logPrint("您选择了以下%d名好友：\nYou selected the following %d friend(s):" %(len(move_indices), len(move_indices)))
                                print(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, move_indices)), friend_hovercard_fields_to_print], print_index = True, reserve_index = True)[0])
                                log.write(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, move_indices)), friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                logPrint("请选择目标分组：\nPlease select a target group:")
                                friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                                friend_groups_df = await sort_friend_group(connection)
                                friend_groups_df_to_print = friend_groups_df.iloc[1:].sort_values(by = "id", ascending = True, ignore_index = True)
                                print(format_df(friend_groups_df_to_print)[0])
                                log.write(format_df(friend_groups_df_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n")
                                while True:
                                    target_groupId = logInput()
                                    if target_groupId == "":
                                        continue
                                    elif target_groupId == "-1":
                                        logPrint("已取消本次移动。\nThis move has been cancelled.")
                                        break
                                    elif target_groupId in set(map(str, friend_groups_df.loc[1:, "id"])):
                                        for friend_index in sorted(set(move_indices)):
                                            group = await (await connection.request("GET", f"/lol-chat/v1/friend-groups/{target_groupId}")).json()
                                            move_summonerName = friend_summonerNames[friend_index]
                                            pid = friend_pids[friend_index]
                                            note = friends[friend_index]["note"]
                                            body = {"groupId": group["id"], "note": note}
                                            response = await (await connection.request("PUT", f"/lol-chat/v1/friends/{pid}", data = body)).json()
                                            logPrint(response)
                                            target_groupName = group["name"]
                                            if response == None:
                                                logPrint("您的好友%s已移动到%s分组中。\nYour friend %s has been moved to the group %s." %(move_summonerName, target_groupName, move_summonerName, target_groupName))
                                            else:
                                                if response["httpStatus"] == 404:
                                                    logPrint("您的好友%s未能移动到%s分组中。请检查TA是否是您的好友。\nYour friend %s failed to be moved to the group %s. Please check if he/she's still your friend." %(move_summonerName, target_groupName, move_summonerName, target_groupName))
                                                else:
                                                    logPrint("您的好友%s未能移动到%s分组中。\nYour friend %s failed to be moved to the group %s." %(move_summonerName, target_groupName, move_summonerName, target_groupName))
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                                if len(friends) == 0:
                                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                                    logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                                    break
                                else:
                                    logPrint("您的好友分组信息如下：\nFriend group distribution:")
                                    friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                                    friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                                    friend_puuids = list(map(lambda x: x["puuid"], friends))
                                    friend_pids = list(map(lambda x: x["pid"], friends))
                                    friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                                    friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupId", "groupName"]
                                    print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0])
                            logPrint("请选择移动模式：\nPlease select a moving mode:\n0\t返回上一层（Return to the last step）\n1\t单个移动（Single）\n2\t批量移动（In batches）\n3\t全部移动（All）")
                elif action[0] == "4":
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    if len(friends) == 0:
                        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                    else:
                        logPrint("请选择要修改备注的好友：\nPlease select a friend to modify note:")
                        friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                        friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                        friend_puuids = list(map(lambda x: x["puuid"], friends))
                        friend_pids = list(map(lambda x: x["pid"], friends))
                        friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                        friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupName", "note"]
                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        while True:
                            noteChange_input = logInput()
                            if noteChange_input == "":
                                continue
                            else:
                                try:
                                    friend_index = int(noteChange_input) - 1
                                except ValueError:
                                    friend_summonerName = noteChange_input
                                    if friend_summonerName in friend_summonerNames:
                                        friend_index = friend_summonerNames.index(friend_summonerName)
                                    elif friend_summonerName in set(map(str, friend_summonerIds)):
                                        friend_index = friend_summonerIds.index(int(friend_summonerName))
                                    elif friend_summonerName in friend_puuids:
                                        friend_index = friend_puuids.index(friend_summonerName)
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                else:
                                    if friend_index == -1:
                                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                                        break
                                    elif not friend_index in range(len(friend_hovercard_df)):
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                pid = friend_pids[friend_index]
                                groupId = friends[friend_index]["groupId"]
                                logPrint("请输入新备注：\nPlease enter the new note:")
                                note = logInput()
                                body = {"groupId": groupId, "note": note}
                                response = await (await connection.request("PUT", f"/lol-chat/v1/friends/{pid}", data = body)).json()
                                logPrint(response)
                                if response == None:
                                    logPrint("为%s添加/修改备注成功。\nAdd/Edit note for %s successfully.\n旧备注（Old note）：%s\n新备注（New note）：%s\n" %(friend_summonerNames[friend_index], friend_summonerNames[friend_index], friends[friend_index]["note"], note))
                                else:
                                    logPrint("为%s添加/修改备注失败。\nFailed to add / modify note for %s." %(friend_summonerNames[friend_index], friend_summonerNames[friend_index]))
                            friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                            if len(friends) == 0:
                                logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                                logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                            else:
                                logPrint("请选择要修改备注的好友：\nPlease select a friend to modify note:")
                                friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                                friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                                friend_puuids = list(map(lambda x: x["puuid"], friends))
                                friend_pids = list(map(lambda x: x["pid"], friends))
                                friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                                friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupName", "note"]
                                print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                elif action[0] == "5":
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    if len(friends) == 0:
                        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                    else:
                        logPrint("您的好友信息如下：\nYour friends:")
                        friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                        friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                        friend_puuids = list(map(lambda x: x["puuid"], friends))
                        friend_pids = list(map(lambda x: x["pid"], friends))
                        friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                        friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupName", "availability", "note"]
                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint("请选择删除模式：\nPlease select an unfriending mode:\n0\t返回上一层（Return to the last step）\n1\t单个删除（Single）\n2\t批量删除（In batches）\n3\t全部删除（All）")
                        while True:
                            index_got = False
                            mode = logInput()
                            if mode == "":
                                continue
                            elif mode == "0":
                                break
                            elif mode == "1":
                                logPrint("请输入要删除的好友索引或者名称：\nPlease enter the index or name of the friend to unfriend:")
                                while True:
                                    unfriend_input = logInput()
                                    if unfriend_input == "":
                                        continue
                                    else:
                                        try:
                                            friend_index = int(unfriend_input) - 1
                                        except ValueError:
                                            friend_summonerName = unfriend_input
                                            if friend_summonerName in friend_summonerNames:
                                                friend_index = friend_summonerNames.index(friend_summonerName)
                                            elif friend_summonerName in set(map(str, friend_summonerIds)):
                                                friend_index = friend_summonerIds.index(int(friend_summonerName))
                                            elif friend_summonerName in friend_puuids:
                                                friend_index = friend_puuids.index(friend_summonerName)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                        else:
                                            if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                                break
                                            elif not friend_index in range(len(friends)):
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                    unfriend_indices = [friend_index]
                                    index_got = True
                                    break
                            elif mode == "2":
                                logPrint("请选择您输入要删除的好友信息的方式：\nPlease select a method of inputting the information of your friends to be removed:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                                while True:
                                    method = logInput()
                                    if method == "":
                                        continue
                                    elif method[0] == "0":
                                        break
                                    elif method[0] == "1":
                                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                                        draft_str = logInput()
                                        draft = bool(draft_str)
                                        if draft:
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                            while True:
                                                draft_option = logInput()
                                                if draft_option == "":
                                                    continue
                                                elif draft_option[0] == "0":
                                                    break
                                                elif draft_option[0] == "1":
                                                    scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                    subscope(scope)
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        logPrint('请输入要删除的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to remove (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                        logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                                        while True:
                                            remove_str = logInput()
                                            if remove_str == "":
                                                continue
                                            elif remove_str[0] == "0":
                                                break
                                            elif remove_str == "all":
                                                unfriend_indices = list(range(len(friends)))
                                                index_got = True
                                                break
                                            else:
                                                try:
                                                    unfriend_indices = eval(remove_str)
                                                except:
                                                    traceback_info = traceback.format_exc()
                                                    logPrint(traceback_info)
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                                else:
                                                    if isinstance(unfriend_indices, int):
                                                        unfriend_indices = [unfriend_indices]
                                                    elif not isinstance(unfriend_indices, list):
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                            if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), unfriend_indices)) and len(unfriend_indices) == len(set(unfriend_indices)):
                                                unfriend_indices = list(map(lambda x: x - 1, unfriend_indices))
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    elif method[0] == "2":
                                        logPrint('''请输入要删除的好友的召唤师名。每个好友的召唤师名格式为{玩家昵称}#{昵称编号}。输入“-1”以结束输入。\nPlease submit the names of the friends to be unfriended. Each friend's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)''')
                                        unfriend_indices = []
                                        while True:
                                            friend_summonerName = logInput()
                                            if friend_summonerName == "":
                                                continue
                                            elif friend_summonerName == "0":
                                                index_got = False
                                                break
                                            elif friend_summonerName == "-1":
                                                break
                                            else:
                                                try:
                                                    friend_summonerName_list = eval(friend_summonerName)
                                                except:
                                                    friend_summonerName_list = [friend_summonerName]
                                                else:
                                                    if isinstance(friend_summonerName_list, list) and all(map(lambda x: isinstance(x, (str, int)), friend_summonerName_list)):
                                                        pass
                                                    else:    
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                                for friend_summonerName in friend_summonerName_list:
                                                    if friend_summonerName in friend_summonerNames:
                                                        friend_index = friend_summonerNames.index(friend_summonerName)
                                                    elif friend_summonerName in friend_summonerIds:
                                                        friend_index = friend_summonerIds.index(friend_summonerName)
                                                    elif friend_summonerName in set(map(str, friend_summonerIds)):
                                                        friend_index = friend_summonerIds.index(int(friend_summonerName))
                                                    elif friend_summonerName in friend_puuids:
                                                        friend_index = friend_puuids.index(friend_summonerName)
                                                    else:
                                                        logPrint("%s不是一个合法的召唤师名、召唤师序号或者玩家通用唯一识别码。\n%s isn't a legal summoner name, summonerId or puuid." %(friend_summonerName, friend_summonerName))
                                                        continue
                                                    if not friend_index in unfriend_indices:
                                                        unfriend_indices.append(friend_index)
                                                        index_got = True
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    if index_got:
                                        break
                                    logPrint("请选择您输入要删除的好友信息的方式：\nPlease select a method of inputting the information of your friends to be removed:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                            elif mode == "3":
                                unfriend_indices = list(range(len(friends)))
                                index_got = True
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                unfriend_summonerNames = list(map(lambda x: friend_summonerNames[x], unfriend_indices))
                                logPrint('与%s解除好友关系：\n- 将该玩家从你的好友列表移除\n- 清除和该玩家的任何现存的会话\nUnfriending %s: \n- Removes them from your friends list\n- Clears any existing conversations with them\n\n您确定要与该玩家解除好友关系吗？（输入“remove”以确认，否则取消。）\nDo you really want to unfriend this player? (Submit "remove" to confirm, otherwise cancel unfriending.)' %("、".join(unfriend_summonerNames), ", ".join(unfriend_summonerNames)))
                                unfriend_confirm_str = logInput()
                                unfriend_confirm = unfriend_confirm_str == "remove"
                                for friend_index in unfriend_indices:
                                    pid = friend_pids[friend_index]
                                    unfriend_summonerName = friend_summonerNames[friend_index]
                                    if unfriend_confirm:
                                        response = await (await connection.request("DELETE", f"/lol-chat/v1/friends/{pid}")).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("您已与%s解除好友关系。\nYou've unfriended %s successfully." %(unfriend_summonerName, unfriend_summonerName))
                                        else:
                                            if response["httpStatus"] == 404:
                                                logPrint("您未能成功与%s解除好友关系。可能你们已经不是好友了。\nYou failed to unfriend %s. Maybe you're not friends already." %(unfriend_summonerName, unfriend_summonerName))
                                            else:
                                                logPrint("您未能成功与%s解除好友关系。\nYou failed to unfriend %s." %(unfriend_summonerName, unfriend_summonerName))
                                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                                if len(friends) == 0:
                                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                                    logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                                    break
                                else:
                                    logPrint("您的好友信息如下：\nYour friends:")
                                    friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                                    friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                                    friend_puuids = list(map(lambda x: x["puuid"], friends))
                                    friend_pids = list(map(lambda x: x["pid"], friends))
                                    friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                                    friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupName", "availability", "note"]
                                    print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            logPrint("请选择删除模式：\nPlease select an unfriending mode:\n0\t返回上一层（Return to the last step）\n1\t单个删除（Single）\n2\t批量删除（In batches）\n3\t全部删除（All）")
                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                elif action[0] == "6":
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    if len(friends) == 0:
                        logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                    else:
                        logPrint("您的好友信息如下：\nYour friends:")
                        friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                        friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                        friend_puuids = list(map(lambda x: x["puuid"], friends))
                        friend_pids = list(map(lambda x: x["pid"], friends))
                        friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                        friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupName", "availability", "note"]
                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t全部拉黑（All）")
                        while True:
                            index_got = False
                            mode = logInput()
                            if mode == "":
                                continue
                            elif mode == "0":
                                break
                            elif mode == "1":
                                logPrint("请输入要拉黑的好友索引或者名称：\nPlease enter the index or name of the friend to block:")
                                while True:
                                    block_input = logInput()
                                    if block_input == "":
                                        continue
                                    else:
                                        try:
                                            friend_index = int(block_input) - 1
                                        except ValueError:
                                            friend_summonerName = block_input
                                            if friend_summonerName in friend_summonerNames:
                                                friend_index = friend_summonerNames.index(friend_summonerName)
                                            elif friend_summonerName in set(map(str, friend_summonerIds)):
                                                friend_index = friend_summonerIds.index(int(friend_summonerName))
                                            elif friend_summonerName in friend_puuids:
                                                friend_index = friend_puuids.index(friend_summonerName)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                        else:
                                            if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                                break
                                            elif not friend_index in range(len(friends)):
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                    block_indices = [friend_index]
                                    index_got = True
                                    break
                            elif mode == "2":
                                logPrint("请选择您输入要拉黑的好友信息的方式：\nPlease select a method of inputting the information of your friends to be blocked:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                                while True:
                                    method = logInput()
                                    if method == "":
                                        continue
                                    elif method[0] == "0":
                                        break
                                    elif method[0] == "1":
                                        logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                                        draft_str = logInput()
                                        draft = bool(draft_str)
                                        if draft:
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                            while True:
                                                draft_option = logInput()
                                                if draft_option == "":
                                                    continue
                                                elif draft_option[0] == "0":
                                                    break
                                                elif draft_option[0] == "1":
                                                    scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                    subscope(scope)
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        logPrint('请输入要拉黑的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to block (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                                        print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                        log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                        logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                                        while True:
                                            block_str = logInput()
                                            if block_str == "":
                                                continue
                                            elif block_str[0] == "0":
                                                break
                                            elif block_str == "all":
                                                block_indices = list(range(len(friends)))
                                                index_got = True
                                                break
                                            else:
                                                try:
                                                    block_indices = eval(block_str)
                                                except:
                                                    traceback_info = traceback.format_exc()
                                                    logPrint(traceback_info)
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                                else:
                                                    if isinstance(block_indices, int):
                                                        block_indices = [block_indices]
                                                    elif not isinstance(block_indices, list):
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                            if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), block_indices)) and len(block_indices) == len(set(block_indices)):
                                                block_indices = list(map(lambda x: x - 1, block_indices))
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    elif method[0] == "2":
                                        logPrint('''请输入要拉黑的好友的召唤师名。每个好友的召唤师名格式为{玩家昵称}#{昵称编号}。输入“-1”以结束输入。\nPlease submit the names of the friends to be blocked. Each friend's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)''')
                                        block_indices = []
                                        while True:
                                            friend_summonerName = logInput()
                                            if friend_summonerName == "":
                                                continue
                                            elif friend_summonerName == "0":
                                                index_got = False
                                                break
                                            elif friend_summonerName == "-1":
                                                break
                                            else:
                                                try:
                                                    friend_summonerName_list = eval(friend_summonerName)
                                                except:
                                                    friend_summonerName_list = [friend_summonerName]
                                                else:
                                                    if isinstance(friend_summonerName_list, list) and all(map(lambda x: isinstance(x, (str, int)), friend_summonerName_list)):
                                                        pass
                                                    else:    
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                                for friend_summonerName in friend_summonerName_list:
                                                    if friend_summonerName in friend_summonerNames:
                                                        friend_index = friend_summonerNames.index(friend_summonerName)
                                                    elif friend_summonerName in friend_summonerIds:
                                                        friend_index = friend_summonerIds.index(friend_summonerName)
                                                    elif friend_summonerName in set(map(str, friend_summonerIds)):
                                                        friend_index = friend_summonerIds.index(int(friend_summonerName))
                                                    elif friend_summonerName in friend_puuids:
                                                        friend_index = friend_puuids.index(friend_summonerName)
                                                    else:
                                                        logPrint("%s不是一个合法的召唤师名、召唤师序号或者玩家通用唯一识别码。\n%s isn't a legal summoner name, summonerId or puuid." %(friend_summonerName, friend_summonerName))
                                                        continue
                                                    if not friend_index in block_indices:
                                                        block_indices.append(friend_index)
                                                        index_got = True
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    if index_got:
                                        break
                                    logPrint("请选择您输入要拉黑的好友信息的方式：\nPlease select a method of inputting the information of your friends to be blocked to other groups:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                            elif mode == "3":
                                block_indices = list(range(len(friends)))
                                index_got = True
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if index_got:
                                logPrint("您选择了以下%d名好友：\nYou selected the following %d friends:" %(len(block_indices), len(block_indices)))
                                print(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, block_indices)), friend_hovercard_fields_to_print], print_index = True, reserve_index = True)[0])
                                log.write(format_df(friend_hovercard_df.loc[list(map(lambda x: x + 1, block_indices)), friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                block_summonerNames = list(map(lambda x: friend_summonerNames[x], block_indices))
                                logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.' %("、".join(block_summonerNames), ", ".join(block_summonerNames)))
                                block_confirm_str = logInput()
                                block_confirm = block_confirm_str == "block"
                                for friend_index in block_indices:
                                    pid = friend_pids[friend_index]
                                    block_summonerName = friend_summonerNames[friend_index]
                                    if block_confirm:
                                        body = {"puuid": friend_puuids[friend_index]}
                                        response = await (await connection.request("POST", f"/lol-chat/v1/blocked-players", data = body)).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("%s已被拉入聊天黑名单。你再也不会看到TA的在线状态或是收到来自TA的信息了。\n%s has been blocked. You will no longer see them online or receive their messages." %(block_summonerName, block_summonerName))
                                        else:
                                            if response["httpStatus"] == 400:
                                                logPrint("您未能成功将%s拉入聊天黑名单。也许TA已经在其中了。\nYou failed to block %s. Maybe he/she's already in it." %(block_summonerName, block_summonerName))
                                            else:
                                                logPrint("您未能成功将%s拉入聊天黑名单。\nYou failed to block %s." %(block_summonerName, block_summonerName))
                                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                                if len(friends) == 0:
                                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                                    break
                                else:
                                    logPrint("您的好友信息如下：\nYour friends:")
                                    friend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))
                                    friend_summonerIds = list(map(lambda x: x["summonerId"], friends))
                                    friend_puuids = list(map(lambda x: x["puuid"], friends))
                                    friend_pids = list(map(lambda x: x["pid"], friends))
                                    friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                                    friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupName", "availability", "note"]
                                    print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t全部拉黑（All）")
                        logPrint("请选择好友管理行为：\nPlease select a friend management action:\n1\t添加好友（Add friends）\n2\t好友请求操作（Friend request operations）\n3\t移动好友至分组（Move to group）\n4\t修改好友备注（Add/Edit note）\n5\t解除好友关系（Unfriend）\n6\t拉入聊天黑名单（Block）")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option == "7":
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            if gameflow_phase == "Lobby":
                friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                if len(friends) == 0:
                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                else:
                    logPrint("您的好友信息如下：\nYour friends:")
                    friend_hovercard_df = await sort_friend_hovercard_simple(connection)
                    friend_hovercard_fields_to_print = ["name", "gameName", "gameTag", "groupName", "note"]
                    print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                    log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                logPrint("请选择邀请模式：\nPlease select an inviting mode:\n0\t返回上一层（Return to the last step）\n1\t单个邀请（Single）\n2\t批量邀请（In batches）\n3\t全部在线好友邀请（All available friends）\n4\t按组邀请（By group）")
                while True:
                    invitee_obtained = False
                    mode = logInput()
                    if mode == "":
                        continue
                    elif mode == "0":
                        break
                    elif mode == "1":
                        logPrint("请输入要邀请的好友索引或者玩家名称：\nPlease enter the invitee's friend index or summoner name:")
                        while True:
                            invite_input = logInput()
                            if invite_input == "":
                                continue
                            else:
                                try:
                                    friend_index = int(invite_input) - 1
                                except ValueError:
                                    invitee_summonerName = invite_input
                                    invitee_info = await get_info(connection, invitee_summonerName)
                                    if invitee_info["info_got"]:
                                        if invitee_info["selfInfo"]:
                                            logPrint("您已经在房间内了。\nYou're already in the lobby.")
                                        else:
                                            invitee_obtained = True
                                            invitee_summonerIds = [invitee_info["body"]["summonerId"]]
                                            logPrint(invitee_info["body"])
                                            break
                                    else:
                                        logPrint(invitee_info["message"])
                                else:
                                    if friend_index == -1: #输入“0”以返回上一层（Submit "0" to return to the last step）
                                        break
                                    elif not friend_index in range(len(friends)):
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        invitee_obtained = True
                                        invitee_summonerIds = [friends[friend_index]["summonerId"]]
                                        break
                    elif mode == "2":
                        invitee_summonerIds = []
                        logPrint("请选择您输入要邀请的玩家信息的方式：\nPlease select a method of inputting the information of invitees:\n0\t返回上一层（Return to the last step）\n1\t好友索引（By friend index）\n2\t近期一起玩过的玩家索引（By recently played summoner index）\n3\t好友请求索引（By friend request index）\n4\t玩家召唤师名（By player summonerName）")
                        while True:
                            method = logInput()
                            if method == "":
                                continue
                            elif method[0] == "0":
                                break
                            elif method[0] == "1":
                                if len(friends) == 0:
                                    logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                                    break
                                else:
                                    logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                                    draft_str = logInput()
                                    draft = bool(draft_str)
                                    if draft:
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        while True:
                                            draft_option = logInput()
                                            if draft_option == "":
                                                continue
                                            elif draft_option[0] == "0":
                                                break
                                            elif draft_option[0] == "1":
                                                scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                                logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                subscope(scope)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    logPrint('请输入要邀请的好友的索引（见下面好友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your friends to invite (you may refer to the index column of the friend table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friends)) if friends[i]["gameName"] == "WordlessMeteor"]')
                                    print(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_hovercard_df.loc[1:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint('变量提示（Variable hints）：\nfriends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()\nfriend_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], friends))\nfriend_summonerIds = list(map(lambda x: x["summonerId"], friends))\nfriend_puuids = list(map(lambda x: x["puuid"], friends))\nfriend_pids = list(map(lambda x: x["pid"], friends))\nfriend_hovercard_df = await sort_friend_hovercard_simple(connection)')
                                    while True:
                                        invite_str = logInput()
                                        if invite_str == "":
                                            continue
                                        elif invite_str[0] == "0":
                                            break
                                        elif invite_str == "all":
                                            invitee_obtained = True
                                            invitee_summonerIds = list(map(lambda x: x["summonerId"], friends))
                                            break
                                        else:
                                            try:
                                                friend_indices = eval(invite_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            else:
                                                if isinstance(friend_indices, int):
                                                    friend_indices = [friend_indices]
                                                elif not isinstance(friend_indices, list):
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                        if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_hovercard_df), friend_indices)) and len(friend_indices) == len(set(friend_indices)):
                                            friend_indices = list(map(lambda x: x - 1, friend_indices))
                                            invitee_obtained = True
                                            invitee_summonerIds = list(map(lambda x: friends[x]["summonerId"], friend_indices))
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            elif method[0] == "2":
                                recent_players_dfs = await get_recent_players(connection, search_mode = 1)
                                recent_LoLPlayers_df = recent_players_dfs["LoL"]
                                recent_TFTPlayers_df = recent_players_dfs["TFT"]
                                recent_LoLPlayers_df = recent_LoLPlayers_df[(recent_LoLPlayers_df["puuid"] != current_info["puuid"]) & (recent_LoLPlayers_df["puuid"] != "00000000-0000-0000-0000-000000000000")] #邀请玩家，当然指的是不包括自己的人类玩家（Of course, the players invited are human players but not himself / herself）
                                recent_TFTPlayers_df = recent_TFTPlayers_df[(recent_TFTPlayers_df["puuid"] != current_info["puuid"]) & (recent_TFTPlayers_df["puuid"] != "00000000-0000-0000-0000-000000000000")]
                                recent_LoLPlayers_df.reset_index(drop = True, inplace = True)
                                recent_TFTPlayers_df.reset_index(drop = True, inplace = True)
                                recent_LoLPlayers_fields_to_print = ["gameName", "tagLine", "gameModeName", "queueId", "champion_name", "champion_alias", "KDA", "ally?"]
                                recent_TFTPlayers_fields_to_print = ["riotIdGameName", "riotIdTagLine", "tft_game_type", "queue_id", "last_round", "time_eliminated", "placement"]
                                logPrint("是否需要对近期一起玩过的玩家取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current recently played summoner data? (Submit any non-empty string to make a draft, or null to input the recently played summoner index directly.)")
                                draft_str = logInput()
                                draft = bool(draft_str)
                                if draft:
                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    while True:
                                        draft_option = logInput()
                                        if draft_option == "":
                                            continue
                                        elif draft_option[0] == "0":
                                            break
                                        elif draft_option[0] == "1":
                                            scope = {"format_df": format_df, "df": recent_players_dfs.copy(), "fields": {"LoL": recent_LoLPlayers_fields_to_print, "TFT": recent_TFTPlayers_fields_to_print}}
                                            logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df["LoL"][(df["LoL"]["gameName"] == "WordlessMeteor") & (df["LoL"]["gameTag"] == "5071")].loc[1:, fields["LoL"]])[0])\nprint(format_df(df["LoL"].loc[[i for i in range(len(df["LoL"])) if df["LoL"]["totalDamageDealtToChampions"] / sum(df["LoL"][(df["LoL"]["gameId"] == df["LoL"].loc[i, "gameId"]) & (df["LoL"]["ally?"] == df["LoL"].loc[i, "ally?"])]["totalDamageDealtToChampions"] > 1 / 3)], fields["LoL"]])[0])\nprint(format_df(df["LoL"].loc[[i for i in range(len(df)) if df["visionScore"] / (int(df["gameDuration"].split(":")[0]) + int(df["gameDuration"].split(":")[1]) / 6) > 2.5], fields["LoL"]])[0])\nprint(format_df(df["TFT"][(df["TFT"]["gameName"] == "WordlessMeteor") & (df["TFT"]["gameTag"] == "5071")].loc[1:, fields["TFT"]])[0])\nprint(format_df(df["TFT"][df["TFT"]["placement"] == 1].loc[1:, fields["TFT"]])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                            subscope(scope)
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                logPrint("请选择您要邀请的近期一起玩过的玩家类型：\nPlease select a type of players:\n0\t返回上一层（Return to the last step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）\n3\t英雄联盟和云顶之弈（LoL and TFT）")
                                while True:
                                    product_option = logInput()
                                    if product_option == "":
                                        continue
                                    elif product_option[0] == "0":
                                        break
                                    elif product_option[0] in {"1", "2", "3"}:
                                        invitee_summonerIds = []
                                        if product_option[0] == "1" or product_option[0] == "3":
                                            logPrint('请输入要邀请的英雄联盟玩家的索引（见下面近期一起玩过的玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of recently played LoL summoners to invite (you may refer to the index column of the recently played summoner table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(recent_LoLPlayers_df)) if recent_LoLPlayers_df.loc[i, "gameName"] == "WordlessMeteor"]')
                                            print(format_df(recent_LoLPlayers_df.loc[1:20, recent_LoLPlayers_fields_to_print], print_index = True, start_index = 1)[0])
                                            log.write(format_df(recent_LoLPlayers_df.loc[1:20, recent_LoLPlayers_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                            logPrint('变量提示（Variable hints）：\nrecent_players_dfs = await get_recent_players(connection, search_mode = 1)\nrecent_LoLPlayers_df = recent_players_dfs["LoL"]')
                                            while True:
                                                invite_str = logInput()
                                                if invite_str == "":
                                                    continue
                                                elif invite_str[0] == "0":
                                                    invitee_obtained = False
                                                    if product_option[0] != "3":
                                                        logPrint("请选择您要邀请的近期一起玩过的玩家类型：\nPlease select a type of players:\n0\t返回上一层（Return to the last step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）\n3\t英雄联盟和云顶之弈（LoL and TFT）")
                                                    break
                                                elif invite_str == "all":
                                                    invitee_obtained = True
                                                    invitee_summonerIds += list(recent_LoLPlayers_df.loc[1:, "summonerId"])
                                                    break
                                                else:
                                                    try:
                                                        player_indices = eval(invite_str)
                                                    except:
                                                        traceback_info = traceback.format_exc()
                                                        logPrint(traceback_info)
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                                    else:
                                                        if isinstance(player_indices, int):
                                                            player_indices = [player_indices]
                                                        elif not isinstance(player_indices, list):
                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                            continue
                                                if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(recent_LoLPlayers_df), player_indices)) and len(player_indices) == len(set(player_indices)):
                                                    invitee_obtained = True
                                                    invitee_summonerIds += list(recent_LoLPlayers_df.loc[player_indices, "summonerId"])
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        if product_option[0] == "2" or product_option[0] == "3":
                                            logPrint('请输入要邀请的云顶之弈玩家的索引（见下面近期一起玩过的玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of recently played TFT summoners to invite (you may refer to the index column of the recently played summoner table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(recent_LoLPlayers_df)) if recent_LoLPlayers_df.loc[i, "gameName"] == "WordlessMeteor"]')
                                            print(format_df(recent_TFTPlayers_df.loc[1:20, recent_TFTPlayers_fields_to_print], print_index = True, start_index = 1)[0])
                                            log.write(format_df(recent_TFTPlayers_df.loc[1:20, recent_TFTPlayers_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                            logPrint('变量提示（Variable hints）：\nrecent_players_dfs = await get_recent_players(connection, search_mode = 1)\nrecent_TFTPlayers_df = recent_players_dfs["TFT"]')
                                            invitee_puuids = []
                                            while True:
                                                invite_str = logInput()
                                                if invite_str == "":
                                                    continue
                                                elif invite_str[0] == "0":
                                                    invitee_obtained = False
                                                    logPrint("请选择您要邀请的近期一起玩过的玩家类型：\nPlease select a type of players:\n0\t返回上一层（Return to the last step）\n1\t英雄联盟（LoL）\n2\t云顶之弈（TFT）\n3\t英雄联盟和云顶之弈（LoL and TFT）")
                                                    break
                                                elif invite_str == "all":
                                                    invitee_obtained = True
                                                    invitee_puuids += list(recent_TFTPlayers_df.loc[1:, "puuid"])
                                                    break
                                                else:
                                                    try:
                                                        player_indices = eval(invite_str)
                                                    except:
                                                        traceback_info = traceback.format_exc()
                                                        logPrint(traceback_info)
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                                    else:
                                                        if isinstance(player_indices, int):
                                                            player_indices = [player_indices]
                                                        elif not isinstance(player_indices, list):
                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                            continue
                                                if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(recent_TFTPlayers_df), player_indices)) and len(player_indices) == len(set(player_indices)):
                                                    invitee_obtained = True
                                                    invitee_puuids += list(recent_TFTPlayers_df.loc[player_indices, "puuid"])
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            for invitee_puuid in invitee_puuids:
                                                invitee_info = await get_info(connection, invitee_puuid)
                                                if invitee_info["info_got"]:
                                                    invitee_summonerIds.append(invitee_info["body"]["summonerId"])
                                                else:
                                                    logPrint(invitee_info["message"])
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    if invitee_obtained: #对输入的召唤师去重（Remove the redundancy in the input summoners）
                                        tmp_set = set()
                                        tmp_list = []
                                        for invitee_summonerId in invitee_summonerIds:
                                            if not invitee_summonerId in tmp_set:
                                                tmp_set.add(invitee_summonerId)
                                                tmp_list.append(invitee_summonerId)
                                        invitee_summonerIds = tmp_list[:]
                                        break
                            elif method[0] == "3": #部分主播短时间内（48小时）添加好友过于频繁导致操作受限，即可使用该方法，但是需要告知观众取消勾选“只接受好友游戏邀请”（Some hosts may be restricted to add any summoner as friend because they add too many friends with a short time period (48 hours, exactly). In that case they can use this method to invite them to lobby, but they need to inform the audience that they should tick off "Allow game invites only from friends"）
                                friend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()
                                if len(friend_requests) == 0:
                                    logPrint("您尚未发送或收到任何好友请求。\nYou haven't sent or received any friend request.")
                                else:
                                    logPrint("您的好友请求如下：\nYour friend requests:")
                                    friend_request_df = await sort_friend_request(connection)
                                    friend_request_fields_to_print = ["gameName", "tagLine", "direction", "icon title"]
                                    print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_header = True, print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], width_exceed_ask = False, direct_print = False, print_header = True, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint("是否需要对好友请求取子集？（输入任意键以开始打草稿，否则直接开始输入玩家索引。）\nDo you want to get a subset of the current friend request data? (Submit any non-empty string to make a draft, or null to input the player index directly.)")
                                    draft_str = logInput()
                                    draft = bool(draft_str)
                                    if draft:
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        while True:
                                            draft_option = logInput()
                                            if draft_option == "":
                                                continue
                                            elif draft_option[0] == "0":
                                                break
                                            elif draft_option[0] == "1":
                                                scope = {"format_df": format_df, "df": friend_request_df.copy(deep = True), "fields": friend_request_fields_to_print}
                                                logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["tagLine"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                subscope(scope)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    logPrint('请输入要邀请的玩家的索引（见下面好友请求信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of players to invite (you may refer to the index column of the friend request table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(friend_requests)) if friend_requests[i]["gameName"] == "WordlessMeteor"]')
                                    print(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(friend_request_df.loc[1:, friend_request_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint('变量提示（Variable hints）：\nfriend_requests = await (await connection.request("GET", "/lol-chat/v2/friend-requests")).json()\nfriend_request_df = await sort_friend_request(connection)')
                                    while True:
                                        invite_str = logInput()
                                        if invite_str == "":
                                            continue
                                        elif invite_str[0] == "0":
                                            break
                                        elif invite_str == "all":
                                            invitee_obtained = True
                                            invitee_puuids = list(map(lambda x: x["puuid"], friend_requests)) #好友请求中的召唤师序号都是0（All summonerIds in the friend request list are 0s）
                                            break
                                        else:
                                            try:
                                                player_indices = eval(invite_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            else:
                                                if isinstance(player_indices, int):
                                                    player_indices = [player_indices]
                                                elif not isinstance(player_indices, list):
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                        if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_request_df), player_indices)) and len(player_indices) == len(set(player_indices)):
                                            player_indices = list(map(lambda x: x - 1, player_indices))
                                            invitee_obtained = True
                                            invitee_puuids = list(map(lambda x: friend_requests[x]["summonerId"], player_indices))
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    if invitee_obtained:
                                        invitee_summonerIds = []
                                        for invitee_puuid in invitee_puuids:
                                            invitee_info = await get_info(connection, invitee_puuid)
                                            if invitee_info["info_got"]:
                                                invitee_summonerIds.append(invitee_info["body"]["summonerId"])
                                            else:
                                                logPrint(invitee_info["message"])
                            elif method[0] == "4":
                                logPrint('''请输入要邀请的玩家的召唤师名。每个玩家的召唤师名格式为{玩家昵称}#{昵称编号}。输入“-1”以结束输入。\nPlease submit the invitees' names. Each invitee's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.''')
                                invitee_summonerIds = []
                                while True:
                                    invitee_summonerName = logInput()
                                    if invitee_summonerName == "":
                                        continue
                                    elif invitee_summonerName == "0":
                                        invitee_obtained = False
                                        break
                                    elif invitee_summonerName == "-1":
                                        break
                                    else:
                                        try:
                                            invitee_summonerName_list = eval(invitee_summonerName)
                                        except:
                                            invitee_summonerName_list = [invitee_summonerName]
                                        else:
                                            if isinstance(invitee_summonerName_list, list) and all(map(lambda x: isinstance(x, (int, str)), invitee_summonerName_list)):
                                                pass
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                        for invitee_summonerName in invitee_summonerName_list:
                                            invitee_info = await get_info(connection, invitee_summonerName)
                                            if invitee_info["info_got"]:
                                                if invitee_info["body"]["puuid"] == current_info["puuid"]:
                                                    logPrint("您已经在房间内了。\nYou're already in the lobby.")
                                                else:
                                                    if invitee_info["body"]["summonerId"] in invitee_summonerIds: #如果已经邀请过该玩家且该玩家拒绝邀请，或同意后退出房间，那么用户需要先返回上一层，再进入才能再次邀请该玩家（If the user has invited a summoner but he/she rejects it, or he/she accepts it but exit the lobby afterwards, then the user need to first return to the last step and then select this method to invite this summoner again）
                                                        logPrint("您已经邀请过该玩家了。\nYou've already invited this player.")
                                                    else:
                                                        invitee_obtained = True
                                                        invitee_summonerIds.append(invitee_info["body"]["summonerId"])
                                                        logPrint(invitee_info["body"])
                                            else:
                                                logPrint("[%s]" %(invitee_summonerName), invitee_info["message"])
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if invitee_obtained:
                                break
                            logPrint("请选择您输入要邀请的玩家信息的方式：\nPlease select a method of inputting the information of invitees:\n0\t返回上一层（Return to the last step）\n1\t好友索引（By friend index）\n2\t近期一起玩过的玩家索引（By recently played summoner index）\n3\t好友请求索引（By friend request index）\n4\t玩家召唤师名（By player summonerName）")
                    elif mode == "3":
                        if len(friends) == 0:
                            logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                        else:
                            invitee_obtained = True
                            invitee_summonerIds = [friend["summonerId"] for friend in friends if not friend["availability"] in {"offline", "mobile", "dnd"}]
                    elif mode == "4":
                        if len(friends) == 0:
                            logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                        else:
                            friend_groups = await (await connection.request("GET", "/lol-chat/v1/friend-groups")).json()
                            friend_groups_df = await sort_friend_group(connection)
                            friend_group_fields_to_print = ["name", "id"]
                            friend_groups_df_to_print = friend_groups_df.loc[1:, friend_group_fields_to_print]
                            logPrint("请选择您要邀请的好友分组（见下面的好友分组信息列）。一些允许的输入格式：\nPlease select a group or groups of friends to invite (You may refer to the index column of the friend group table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall")
                            print(format_df(friend_groups_df_to_print, print_index = True, start_index = 1)[0])
                            log.write(format_df(friend_groups_df_to_printwidth_exceed_ask = False, direct_print = True, print_index = True, start_index = 1)[0] + "\n")
                            while True:
                                invite_str = logInput()
                                if invite_str == "":
                                    continue
                                elif invite_str[0] == "0":
                                    break
                                elif invite_str == "all":
                                    invitee_obtained = True
                                    invitee_summonerIds = list(map(lambda x: x["summonerId"], friends))
                                    break
                                else:
                                    try:
                                        group_indices = eval(invite_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                    else:
                                        if isinstance(group_indices, int):
                                            group_indices = [group_indices]
                                        elif not isinstance(group_indices, list):
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            continue
                                if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(friend_groups_df), group_indices)) and len(group_indices) == len(set(group_indices)):
                                    invitee_obtained = True
                                    invitee_summonerIds = [friend["summonerId"] for friend in friends if friend["groupId"] in set(friend_groups_df.loc[group_indices, "id"]) and not friend["availability"] in {"offline", "mobile", "dnd"}]
                                    break
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        continue
                    if invitee_obtained:
                        logPrint("您邀请了以下%d名玩家：\nYou invited the following %d player(s):" %(len(invitee_summonerIds), len(invitee_summonerIds)))
                        for invitee_summonerId in invitee_summonerIds:
                            invitee_info = await get_info(connection, invitee_summonerId)
                            if invitee_info["info_got"]:
                                logPrint(get_info_name(invitee_info["body"]))
                            else:
                                logPrint(invitee_info["message"])
                        body = list(map(lambda x: {"toSummonerId": x}, invitee_summonerIds))
                        response = await (await connection.request("POST", "/lol-lobby/v2/lobby/invitations", data = body)).json()
                        logPrint(response)
                        lobby_invitations = await (await connection.request("GET", "/lol-lobby/v2/lobby/invitations")).json()
                        if "errorCode" in lobby_invitations:
                            if lobby_invitations["httpStatus"] == 404 and lobby_invitations["message"] == "LOBBY_NOT_FOUND":
                                logPrint("您已离开房间。\nYou've left the original lobby.")
                            break
                        else:
                            accepted_invitations = filter(lambda x: x["state"] == "Accepted", lobby_invitations)
                            pending_invitations = filter(lambda x: x["state"] == "Pending", lobby_invitations)
                            accepted_summonerIds = list(map(lambda x: x["toSummonerId"], accepted_invitations))
                            pending_summonerIds = list(map(lambda x: x["toSummonerId"], pending_invitations))
                            accepted_summonerNames = []
                            pending_summonerNames = []
                            uninvited_summonerNames = []
                            for invitee_summonerId in invitee_summonerIds:
                                invitee_info = await get_info(connection, invitee_summonerId)
                                if invitee_info["info_got"]:
                                    if invitee_summonerId in accepted_summonerIds:
                                        accepted_summonerNames.append(get_info_name(invitee_info["body"]))
                                    elif invitee_summonerId in pending_summonerIds:
                                        pending_summonerNames.append(get_info_name(invitee_info["body"]))
                                    else:
                                        uninvited_summonerNames.append(get_info_name(invitee_info["body"]))
                            if len(accepted_summonerNames) != 0:
                                if len(accepted_summonerNames) == 1:
                                    logPrint("%s已在房间内。\n%s is already in lobby." %("、".join(accepted_summonerNames), ", ".join(accepted_summonerNames)))
                                else:
                                    logPrint("%s已在房间内。\n%s are already in lobby." %("、".join(accepted_summonerNames), ", ".join(accepted_summonerNames)))
                            if len(pending_summonerNames) != 0:
                                logPrint("%s已收到邀请。\n%s received your invitation." %("、".join(pending_summonerNames), ", ".join(pending_summonerNames)))
                            if len(uninvited_summonerNames) != 0:
                                logPrint("%s未能收到邀请。这可能是因为您还没有邀请权限，您的房间已经满员，对方不在线，对方只接受好友游戏邀请，或者对方将您拉入了聊天黑名单。\n%s didn't receive your invitation. Maybe you don't have invite priviledges, your lobby is already full, they're offline, they allow game invites only from friends, or they blocked you." %("、".join(uninvited_summonerNames), ", ".join(uninvited_summonerNames)))
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    logPrint("请选择邀请模式：\nPlease select an inviting mode:\n0\t返回上一层（Return to the last step）\n1\t单个邀请（Single）\n2\t批量邀请（In batches）\n3\t全部在线好友邀请（All available friends）\n4\t按组邀请（By group）")
            elif gameflow_phase == "None":
                logPrint("您尚未创建房间。请创建房间后再尝试邀请。\nYou've not created any lobby. Please try again after a lobby is created.")
            else:
                logPrint("您目前无法邀请玩家。\nYou can't invite any player currently.")
        elif option == "8":
            lol_notifications = await (await connection.request("GET", "/lol-settings/v2/account/LCUPreferences/lol-notifications")).json()
            settings_changed = False
            if lol_notifications["data"] == None or not "blockNonFriendGameInvites" in lol_notifications["data"] or lol_notifications["data"]["blockNonFriendGameInvites"]:
                body = {"data": {"blockNonFriendGameInvites": False}, "schemaVersion": lol_notifications["schemaVersion"]} #注意：schemaVersion一旦增加就不可减少（Warning: Once schemaVersion increases, it can't be decreased）
                response = await (await connection.request("PATCH", "/lol-settings/v2/account/LCUPreferences/lol-notifications", data = body)).json()
                logPrint(response)
                if response == None:
                    logPrint('已经关闭“只接受好友游戏邀请”选项。\nDisabled "Allow game invites only from friends" option.')
                    settings_changed = True
            while True:
                logPrint("您是要加入好友的公开小队，还是接受邀请？\nDo you want to join a friend's open party or accept an invitation?\n1\t加入公开小队（Join party）\n2\t接受邀请（Accept an invitation）")
                action = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    parties = []
                    party_owners = {}
                    for friend in friends:
                        if friend["lol"] != {} and "pty" in friend["lol"] and friend["lol"]["pty"] != "":
                            party = eval(friend["lol"]["pty"])
                            if not party["partyId"] in list(map(lambda x: x["partyId"], parties)): #当多个好友在同一个小队中时，需要去重（When multiple friends are in a same party, the repeated records need removing）
                                parties.append(party)
                                party_owners[party["partyId"]] = friend["gameName"] + "#" + friend["gameTag"]
                    if len(parties) == 0:
                        logPrint("没有公开的小队。\nThere's not any open party.")
                        continue
                    else:
                        party_df = await sort_party_data(connection, parties)
                        party_fields_to_print = ["partyId", "maxPlayers", "queue gameMode", "queue name", "summonerNames"]
                        logPrint("请选择您要加入的小队：\nPlease select a party to join:")
                        print(format_df(party_df.loc[1:, party_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(party_df.loc[1:, party_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        while True:
                            return_home = False
                            partyIndex = logInput()
                            if partyIndex == "":
                                continue
                            elif partyIndex == "0":
                                break
                            elif partyIndex in set(map(str, range(1, len(parties) + 1))):
                                partyId = parties[int(partyIndex) - 1]["partyId"]
                                response = await (await connection.request("POST", f"/lol-lobby/v2/party/{partyId}/join")).json()
                                logPrint(response)
                                if response == None:
                                    logPrint("您加入了%s的小队。\nYou joined the party of %s." %(party_owners[partyId], party_owners[partyId]))
                                    return_home = True
                                    break
                                else:
                                    if response["httpStatus"] == 400:
                                        if response["message"] == "PARTY_SIZE_LIMIT":
                                            logPrint("你试图加入的小队已经满员。\nThe open party you attempted to join is full.")
                                        elif response["message"] == "INVALID_ROLE_TRANSITION":
                                            logPrint("你已被移出小队。你必须收到邀请才能重新加入。\nYou have been removed from the party. You must receive an invite to rejoin.")
                                        elif response["message"] == "INVALID_WHILE_PARTY_IN_ACTION":
                                            logPrint("你无法加入该小队，因为该小队正在队列中。\nYou were not able to join the party because the party is now in queue.")
                                        else:
                                            logPrint("你无法加入该小队。\nYou were not able to join the party.")
                                    else:
                                        logPrint("你无法加入该小队。\nYou were not able to join the party.")
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                continue
                            friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                            parties = []
                            party_owners = {}
                            for friend in friends:
                                if friend["lol"] != {} and "pty" in friend["lol"] and friend["lol"]["pty"] != "":
                                    party = eval(friend["lol"]["pty"])
                                    if not party["partyId"] in list(map(lambda x: x["partyId"], parties)):
                                        parties.append(party)
                                        party_owners[party["partyId"]] = friend["gameName"] + "#" + friend["gameTag"]
                            if len(parties) == 0:
                                logPrint("没有公开的小队。\nThere's not any open party.")
                                break
                            else:
                                party_df = await sort_party_data(connection, parties)
                                party_fields_to_print = ["partyId", "maxPlayers", "queue gameMode", "queue name", "summonerNames"]
                                logPrint("请选择您要加入的小队：\nPlease select a party to join:")
                                print(format_df(party_df.loc[1:, party_fields_to_print], print_index = True, start_index = 1)[0])
                                log.write(format_df(party_df.loc[1:, party_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                elif action[0] == "2":
                    receivedInvitations = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()
                    if len(receivedInvitations) == 0:
                        logPrint("您还没有收到邀请。\nYou've not received any invitation.")
                        continue
                    else:
                        logPrint("您收到的邀请信息如下：\nYour received invitations:")
                        invid_df = await sort_received_invitations(connection)
                        invid_fields_to_print = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
                        print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                        log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                        logPrint("请选择邀请处理方式：\nPlease select a method of handling the invitation(s):\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）")
                        while True:
                            return_home = False
                            method = logInput()
                            if method == "":
                                continue
                            elif method[0] == "0":
                                break
                            elif method[0] == "1":
                                logPrint("请选择要接受的邀请序号：\nPlease select the index of the invitation to accept:")
                                while True:
                                    invitationIndex = logInput()
                                    if invitationIndex == "":
                                        continue
                                    elif invitationIndex == "0":
                                        logPrint("请选择邀请处理方式：\nPlease select a method of handling the invitation(s):\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）")
                                        break
                                    elif invitationIndex in set(map(str, range(1, len(invid_df)))):
                                        invitationId = invid_df.loc[int(invitationIndex), "invitationId"] #注意到邀请序号和小队序号的获取方式有所不同。小队序号是从原始的小队数据中获取的，因为小队数据作为静态数据传入小队信息整理函数中，而邀请信息没有传入邀请信息整理函数中，在程序运行前后邀请信息会频繁更新，可能导致原始邀请信息和邀请信息数据框中的内容不符（邀请信息数据框整理过程中的邀请信息和这里的邀请信息不在同一个作用域中）【Note that it differs between getting invitationId and getting partyId. PartyId is obtained from the original party data, in that party data are passed into `sort_party_data` function as static data, while invitation data aren't passed into `sort_received_invitations` function. As a result, invitation information may be frequently updated, which causes the original invitation data not in accordance with data in the invitation dataframe (invitation data here don't belong to the same scope of those during sorting out the invitation dataframe)】
                                        invid_owner = invid_df.loc[int(invitationIndex), "fromSummonerName"]
                                        response = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/accept")).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("您接受了%s的邀请。\nYou accepted the invitation of %s." %(invid_owner, invid_owner))
                                            return_home = True
                                            break
                                        else:
                                            if response["httpStatus"] == 400:
                                                if response["message"] == "PARTY_SIZE_LIMIT":
                                                    logPrint("你试图加入的小队已经满员。\nThe open party you attempted to join is full.")
                                                elif response["message"] == "INVALID_ROLE_TRANSITION":
                                                    logPrint("你已被移出小队。你必须收到邀请才能重新加入。\nYou have been removed from the party. You must receive an invite to rejoin.")
                                                elif response["message"] == "INVALID_WHILE_PARTY_IN_ACTION":
                                                    logPrint("你无法加入该小队，因为该小队正在队列中。\nYou were not able to join the party because the party is now in queue.")
                                                else:
                                                    logPrint("你无法加入该小队。\nYou were not able to join the party.")
                                            elif response["httpStatus"] == 404 and response["message"] == "INVITATION_NOT_FOUND":
                                                logPrint("邀请已过期。\nInvite expired.")
                                            else:
                                                logPrint("你无法加入该小队。\nYou were not able to join the party.")
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    invid_df = await sort_received_invitations(connection)
                                    invid_fields_to_print = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
                                    logPrint("请选择要接受的邀请序号：\nPlease select the index of the invitation to accept:")
                                    print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                            elif method[0] == "2":
                                logPrint("请选择拒绝模式：\nPlease select a decline mode:\n0\t返回上一层（Return to the last step）\n1\t单个拒绝（Single）\n2\t批量拒绝（In batches）\n3\t全部拒绝（All）")
                                while True:
                                    index_got = False
                                    mode = logInput()
                                    if mode == "":
                                        continue
                                    elif mode == "0":
                                        logPrint("请选择邀请处理方式：\nPlease select a method of handling the invitation(s):\n0\t返回上一层（Return to the last step）\n1\t接受（Accept）\n2\t拒绝（Decline）")
                                        break
                                    elif mode == "1":
                                        logPrint("请选择要拒绝的邀请序号：\nPlease enter the index of the invitation to decline:")
                                        while True:
                                            decline_input = logInput()
                                            if decline_input == "":
                                                continue
                                            elif decline_input == "0":
                                                break
                                            elif decline_input in set(map(str, range(1, len(invid_df)))):
                                                decline_indices = [int(decline_input)]
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    elif mode == "2":
                                        logPrint("是否需要对邀请取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current invitation data? (Submit any non-empty string to make a draft, or null to input the invitation index directly.)")
                                        draft_str = logInput()
                                        draft = bool(draft_str)
                                        if draft:
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                            while True:
                                                draft_option = logInput()
                                                if draft_option == "":
                                                    continue
                                                elif draft_option[0] == "0":
                                                    break
                                                elif draft_option[0] == "1":
                                                    scope = {"format_df": format_df, "df": friend_hovercard_df.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                    subscope(scope)
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        logPrint('请输入要拒绝的邀请的索引（见下面邀请信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of invitations to decline (you may refer to the index column of the above invitation table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(receivedInvitations)) if receivedInvitations[i]["gameConfig"]["queueId"] == -1 or receivedInvitations[i]["gameConfig"]["inviteGameType"] == "RIOTSCRIPT_BOT"]\n[i for i in range(len(invid_df)) if "WordlessMeteor" in invid_df.loc[i, "fromSummonerName"]]')
                                        print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                                        log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                        logPrint('变量提示（Variable hints）：\nreceivedInvitations = await (await connection.request("GET", "/lol-lobby/v2/received-invitations")).json()\ninvid_df = await sort_received_invitations(connection)')
                                        while True:
                                            decline_str = logInput()
                                            if decline_str == "":
                                                continue
                                            elif decline_str[0] == "0":
                                                break
                                            elif decline_str == "all":
                                                decline_indices = list(range(1, len(invid_df)))
                                                index_got = True
                                                break
                                            else:
                                                try:
                                                    decline_indices = eval(decline_str)
                                                except:
                                                    traceback_info = traceback.format_exc()
                                                    logPrint(traceback_info)
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                                else:
                                                    if isinstance(decline_indices, int):
                                                        decline_indices = [decline_indices]
                                                    elif not isinstance(decline_indices, list):
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                            if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(invid_df), decline_indices)) and len(decline_indices) == len(set(decline_indices)):
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    elif mode == "3":
                                        decline_indices = list(range(1, len(invid_df)))
                                        index_got = True
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    logPrint("您选择了以下%d个组队邀请：\nYou selected the following %d invitation(s):" %(len(decline_indices), len(decline_indices)))
                                    print(format_df(invid_df.loc[decline_indices, invid_fields_to_print], print_index = True, reserve_index = True)[0])
                                    log.write(format_df(invid_df.loc[decline_indices, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                    if index_got:
                                        for invitationIndex in decline_indices:
                                            invitationId = invid_df.loc[int(invitationIndex), "invitationId"]
                                            invid_owner = invid_df.loc[int(invitationIndex), "fromSummonerName"]
                                            response = await (await connection.request("POST", f"/lol-lobby/v2/received-invitations/{invitationId}/decline")).json()
                                            logPrint(response)
                                            if response == None:
                                                logPrint("您拒绝了%s的邀请。\nYou accepted the invitation of %s." %(invid_owner, invid_owner))
                                            else:
                                                if response["httpStatus"] == 404 and response["message"] == "INVITATION_NOT_FOUND":
                                                    logPrint("邀请已过期。\nInvite expired.")
                                                else:
                                                    logPrint("拒绝邀请失败。\nInvitation decline failure.")
                                        logPrint("您收到的邀请信息如下：\nYour received invitations:")
                                        invid_df = await sort_received_invitations(connection)
                                        if len(invid_df) == 1:
                                            logPrint("您还没有收到邀请。\nYou've not received any invitation.")
                                            return_home = True
                                            break
                                        else:
                                            invid_fields_to_print = ["fromSummonerName", "time", "gameMode", "mapId", "queue name", "queueId", "state"]
                                            print(format_df(invid_df.loc[1:, invid_fields_to_print], print_index = True, start_index = 1)[0])
                                            log.write(format_df(invid_df.loc[1:, invid_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint("请选择拒绝模式：\nPlease select a decline mode:\n0\t返回上一层（Return to the last step）\n1\t单个拒绝（Single）\n2\t批量拒绝（In batches）\n3\t全部拒绝（All）")
                            else:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            if return_home:
                                break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                if return_home:
                    break
            if settings_changed:
                body = {"data": {"blockNonFriendGameInvites": True}, "schemaVersion": lol_notifications["schemaVersion"]}
                response = await (await connection.request("PATCH", "/lol-settings/v2/account/LCUPreferences/lol-notifications", data = body)).json()
                logPrint(response)
                if response == None:
                    logPrint('恢复了“只接受好友游戏邀请”选项。\nRecovered "Allow game invites only from friends" option.')
        elif option == "9":
            global spectatorPluginNA_hint_printed
            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
            if gameflow_phase == "None":
                exit_loop = False #决定是否退出下面的循环（Determines whether to exit the following loop）
                while not exit_loop:
                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                    friend_puuids = list(map(lambda x: x["puuid"], friends))
                    response = await (await connection.request("POST", "/lol-spectator/v3/buddy/spectate", data = [current_info["puuid"]] if len(friends) == 0 else friend_puuids)).json() #在国服，如果这个接口的请求主体不是空列表，那么返回的异常信息是“SpectatorPlugin_NOT_AVAILABLE”。问题在于，如果请求主体是空列表，那么这个接口仍能正常响应。这样看来，似乎下面程序逻辑本应先处理len(friends)是否为0的情形。但是有一个比较巧妙的解法，就是将这个接口的请求主体设置为自己。这样一来，在观战插件可用的时候，如果程序识别到自己不在游戏中，那么自己肯定是不可观战的；如果程序识别到自己在游戏中，那么程序压根就无法运行这里的代码【On Chinese servers, if the request body of this endpoint isn't an empty list, then the error message is "SpectatorPlugin_NOT_AVAILABLE". But the problem is, if the request body is an empty list, then it still responds as normal (Riot servers). In that case, it seems the following program logic should first deal with the case where `len(friends) == 0` or `len(friends) != 0`. But here I provide a relatively clever solution: assign a list containing only the user's puuid as the request body. In this way, when the spectator plugin is available, if the program identifies that the user isn't in game right now, then the user itself can't be observable; if the program identifies the user itself is in game, then the program won't run the code here and hereinafter at all】
                    logPrint(response)
                    pluginNA = False
                    use_pluginNA = False #决定是否在观战可用性插件可用的情况下仍然运行观战可用性插件不可用的情况下的代码（Decides whether to run the code of the case where spectating availability endpoint isn't available when this endpoint is actually available）
                    spectate_ready = False
                    if "errorCode" in response: #传入空列表也会导致异常（Passing an empty list also causes an error）
                        if response["httpStatus"] == 400 and response["message"] == "SpectatorPlugin_NOT_AVAILABLE":
                            pluginNA = True
                            if not spectatorPluginNA_hint_printed:
                                logPrint("您所在的服务器不支持玩家可观战性检测。请自行判断玩家是否可观战。\nThe server or platform you're currently on doesn't support this endpoint. Please judge by yourself whether a player is observable.")
                                spectatorPluginNA_hint_printed = True
                        elif response["httpStatus"] == 400 and response["message"] == "Couldn't assign value to 'puuids' of type vector because the input not a collection.":
                            logPrint("看起来你现在还没有添加任何好友。邀请好友来聊天并一起玩游戏。\nLooks like you haven't added any friends yet. Invite friends to chat and play together.")
                        elif response["httpStatus"] == 500 and "Couldn't find service in service discovery using ServerLocationEndpointFilter" in response["message"]:
                            logPrint("观战服务不可用。\nSpectator service unavailable.")
                        else:
                            logPrint("无法获取好友可观战性信息。请通过客户端内右键点击一名好友以观战。\nCan't get friend observability information. Please right click on a friend to spectate.")
                    else:
                        if len(friends) == 0 or len(response["availableForWatching"]) == 0: #如果len(friends)不是0，那么上面的response就不会是异常，从而导致后面一个条件不会引发键错误（If `len(friends)` isn't 0, then the above `response` isn't an error and thus the latter condition here won't cause a KeyError）
                            logPrint("您尚无可观战的好友。是否观战其它玩家？（输入任意键以搜索其它玩家的观战可用性，否则返回上一层。）\nThere's not any friend available for watching. Do you want to spectate other players? (Submit any non-empty string to search for other players' observability, or null to return to the last step.)")
                            nonfriend_spectate_str = logInput()
                            nonfriend_spectate = bool(nonfriend_spectate_str)
                            if not nonfriend_spectate: #既不观战好友，也不观战其它玩家，那就是不观战（If neither friends nor players are to spectate, then don't spectate）
                                break
                        else:
                            logPrint("您有%d个好友允许观战。请选择观战好友还是其它玩家。（输入任意键以观战其它玩家，否则观战好友。）\nThere're %d friend(s) that allow watching. Please select whether you want to spectate a friend or another non-friend player. (Submit any non-empty string to try spectating another non-friend player, or null to spectate friend.)" %(len(response["availableForWatching"]), len(response["availableForWatching"])))
                            nonfriend_spectate_str = logInput()
                            nonfriend_spectate = bool(nonfriend_spectate_str)
                        back = False
                        if nonfriend_spectate:
                            logPrint('请输入您要检测观战可用性的玩家的召唤师名。输入“-1”以结束输入。\nPlease input the summonerName of the player to detect observability. Submit "-1" to end the input.')
                            spectate_summonerNames = []
                            spectate_puuids = []
                            spectate_infos = []
                            spectate_availability = []
                            while True:
                                spectate_summonerName = logInput()
                                if spectate_summonerName == "":
                                    continue
                                elif spectate_summonerName == "0":
                                    back = True
                                    break
                                elif spectate_summonerName == "-1":
                                    break
                                else:
                                    if spectate_summonerName in spectate_summonerNames:
                                        logPrint("您已经输入过该玩家了。\nYou've alerady added this summoner.")
                                    else:
                                        spectate_info = await get_info(connection, spectate_summonerName)
                                        if spectate_info["info_got"]:
                                            if spectate_info["body"]["puuid"] == current_info["puuid"]:
                                                logPrint("你不能观战你自己。\nYou can't spectate yourself.")
                                            elif spectate_info["body"]["puuid"] in spectate_puuids:
                                                logPrint("您已经输入过该玩家了。\nYou've alerady added this summoner.")
                                            else:
                                                response = await (await connection.request("POST", "/lol-spectator/v3/buddy/spectate", data = [spectate_info["body"]["puuid"]])).json()
                                                logPrint(response)
                                                if len(response["availableForWatching"]) == 0:
                                                    spectate_availability.append(False)
                                                    logPrint("该玩家目前不可观战。\nThis player isn't observable currently.")
                                                else:
                                                    spectate_availability.append(True)
                                                    logPrint(spectate_info["body"])
                                                spectate_summonerNames.append(spectate_summonerName)
                                                spectate_puuids.append(spectate_info["body"]["puuid"])
                                                spectate_infos.append(spectate_info["body"]) #即使接口返回结果是该玩家目前不可观战，但是由于观战可用性检测接口存在问题，这里还是要保留一下意见（Even if the spectating availability endpoint returns the fact that this player isn't observable currently, because this endpoint may sometimes not work correctly, this player is still a candidate）
                                        else:
                                            logPrint(spectate_info["message"])
                            if not back:
                                if len(spectate_puuids) == 0:
                                    logPrint("您尚未输入任何玩家。\nYou've not input any player.")
                                else:
                                    spectate_nonfriend_header = {"gameName": "玩家昵称", "tagLine": "昵称编号", "puuid": "玩家通用唯一识别码", "availability": "观战可用性"}
                                    spectate_nonfriend_header_keys = list(spectate_nonfriend_header.keys())
                                    spectate_nonfriend_data = {}
                                    for i in range(len(spectate_nonfriend_header_keys)):
                                        key = spectate_nonfriend_header_keys[i]
                                        spectate_nonfriend_data[key] = []
                                    for spectate_info in spectate_infos:
                                        for i in range(len(spectate_nonfriend_header_keys)):
                                            if i <= 2:
                                                key = spectate_nonfriend_header_keys[i]
                                                spectate_nonfriend_data[key].append(spectate_info[key])
                                    spectate_nonfriend_data["availability"] = spectate_availability
                                    spectate_nonfriend_statistics_output_order = list(range(len(spectate_nonfriend_header_keys)))
                                    spectate_nonfriend_data_organized = {}
                                    for i in spectate_nonfriend_statistics_output_order:
                                        key = spectate_nonfriend_header_keys[i]
                                        spectate_nonfriend_data_organized[key] = spectate_nonfriend_data[key]
                                    spectate_nonfriend_df = pandas.DataFrame(data = spectate_nonfriend_data_organized)
                                    spectate_nonfriend_df["availability"] = spectate_nonfriend_df["availability"].astype(str)
                                    for i in range(len(spectate_nonfriend_df)):
                                        spectate_nonfriend_df.loc[i, "availability"] = "√" if spectate_nonfriend_df["availability"][i] == "True" else ""
                                    spectate_nonfriend_df = pandas.concat([pandas.DataFrame([spectate_nonfriend_header])[spectate_nonfriend_df.columns], spectate_nonfriend_df], ignore_index = True)
                                    logPrint("请选择一名玩家进行观战：\nPlease select a player to spectate:")
                                    print(format_df(spectate_nonfriend_df, print_index = True)[0])
                                    log.write(format_df(spectate_nonfriend_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                    while True:
                                        index_got = False
                                        spectate_str = logInput()
                                        if spectate_str == "":
                                            continue
                                        elif spectate_str == "0":
                                            break
                                        else:
                                            try:
                                                player_index = eval(spectate_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            else:
                                                if isinstance(player_index, int) and player_index > 0 and player_index < len(spectate_nonfriend_df):
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                    if index_got:
                                        dropInSpectateGameId = gameQueueType = allowObserveMode = ""
                                        spectate_puuid = spectate_nonfriend_df.loc[player_index, "puuid"]
                                        spectating_summonerName = get_info_name(spectate_infos[player_index - 1])
                                        spectate_ready = True
                        else:
                            if len(friends) > 0 and len(response["availableForWatching"]) > 0:
                                logPrint("可观战的好友信息如下：\nFriends that allow spectating:")
                                friend_hovercard_df = await sort_friend_hovercard(connection)
                                friend_hovercard_fields_to_print = ["gameName", "tagLine", "gameModeName", "gameId", "champion name", "champion alias"]
                                friend_hovercard_df_to_print = pandas.concat([friend_hovercard_df.iloc[:1], friend_hovercard_df[friend_hovercard_df["puuid"].isin(response["availableForWatching"])]], ignore_index = True)
                                print(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], print_index = True)[0])
                                log.write(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                logPrint("是否需要对好友取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current friend data? (Submit any non-empty string to make a draft, or null to input the friend index directly.)")
                                draft_str = logInput()
                                draft = bool(draft_str)
                                if draft:
                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    while True:
                                        draft_option = logInput()
                                        if draft_option == "":
                                            continue
                                        elif draft_option[0] == "0":
                                            break
                                        elif draft_option[0] == "1":
                                            scope = {"format_df": format_df, "df": friend_hovercard_df_to_print.copy(deep = True), "fields": friend_hovercard_fields_to_print}
                                            logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\nprint(format_df(df[df["championId"] == 11]].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                            subscope(scope)
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                logPrint('''请选择一名好友，或者输入召唤师名进行观战。输入“0”以返回上一层。\nPlease select a friend or enter a summoner's name to spectate. Submit "0" to return to the last step.''')
                                print(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], print_index = True)[0])
                                log.write(format_df(friend_hovercard_df_to_print.loc[:, friend_hovercard_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                while True:
                                    index_got = False
                                    spectate_str = logInput()
                                    if spectate_str == "":
                                        continue
                                    elif spectate_str == "0":
                                        exit_loop = True
                                        break
                                    else:
                                        try:
                                            friend_index = eval(spectate_str)
                                        except:
                                            use_pluginNA = True
                                            break
                                        else:
                                            if isinstance(friend_index, int) and friend_index > 0 and friend_index < len(friend_hovercard_df_to_print):
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                if index_got:
                                    dropInSpectateGameId, gameQueueType, allowObserveMode, spectate_puuid = friend_hovercard_df_to_print.loc[friend_index, ["gameId", "gameQueueType", "isObservable", "puuid"]]
                                    spectating_summonerName = friend_hovercard_df_to_print.loc[friend_index, "gameName"] + "#" + friend_hovercard_df_to_print.loc[friend_index, "gameTag"]
                                    spectate_ready = True
                            #这里对应的情况是nonfriend_spectate为假、好友数量是0且可观看玩家的数量也是0。既没有可观看的玩家，也不观战非好友，那就直接重新开始一个while循环，所以这里不写else语句（In this case, nonfriend_spectate = False, len(friends) = 0 and len(response["availableForWatching"]) = 0. That is, the user doesn't want to spectate the game of either a friend or a non-friend, so the next step should be returning to the start of the while-loop. Therefore, there's no need to write this else-statement）
                    if pluginNA or use_pluginNA:
                        if pluginNA:
                            logPrint('请输入您想要观看的玩家召唤师名。输入“0”以返回上一层。\nPlease input the summonerName of the player to spectate. Submit "0" to return to the last step.')
                        while True:
                            spectating_summonerName = spectate_str if use_pluginNA else logInput()
                            use_pluginNA = False #如果在转到这里之前输入的召唤师名有问题，在本While循环内需要允许用户重新输入召唤师名（If the summoner name input before running here has a problem, the user should be allowed to input the summoner name again in this while-loop）
                            if spectating_summonerName == "":
                                continue
                            elif spectating_summonerName == "0":
                                exit_loop = True
                                break
                            else:
                                spectating_summoner_info = await get_info(connection, spectating_summonerName)
                                if spectating_summoner_info["info_got"]:
                                    if spectating_summoner_info["body"]["puuid"] == current_info["puuid"]:
                                        logPrint("你不能观战自己。战斗！爽！————\nYou can't spectate yourself. Battle... YES!!!!")
                                        continue
                                    dropInSpectateGameId = gameQueueType = allowObserveMode = ""
                                    spectate_puuid = spectating_summoner_info["body"]["puuid"]
                                    spectating_summonerName = get_info_name(spectating_summoner_info["body"])
                                    spectate_ready = True
                                    break
                                else:
                                    logPrint(spectating_summoner_info["message"])
                    if spectate_ready:
                        body = {"dropInSpectateGameId": str(dropInSpectateGameId), "gameQueueType": gameQueueType, "allowObserveMode": allowObserveMode, "puuid": spectate_puuid}
                        response = await (await connection.request("POST", "/lol-spectator/v1/spectate/launch", data = body)).json()
                        logPrint(response)
                        if response == None:
                            time.sleep(1) #发送指令后客户端不一定马上进入英雄选择或游戏中（The client won't immediately enter the champ select or in game stage after the program posts the spectating requests）
                            gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                            if gameflow_phase == "ChampSelect" or gameflow_phase == "InProgress":
                                logPrint("启动观战成功！您正在观看%s的对局。\nLaunched spectating successfully. You'll be spectating the game of %s soon." %(spectating_summonerName, spectating_summonerName))
                            else:
                                logPrint("这场对局现在不可观战。它也许已经结束了。\nThe game isn't available for spectate now. It might have ended.")
                        else:
                            if response["httpStatus"] == 400 and response["message"] == "SpectatorPlugin_NOT_AVAILABLE":
                                pluginNA = True
                                logPrint("您所在的服务器不支持玩家可观战性检测。请自行判断玩家是否可观战。\nThe server or platform you're currently on doesn't support this endpoint. Please judge by yourself whether a player is observable.")
                                spectatorPluginNA_hint_printed = True
                            elif response["httpStatus"] == 500 and "Couldn't find service in service discovery using ServerLocationEndpointFilter" in response["message"]:
                                logPrint("观战服务不可用。\nSpectator service unavailable.")
                            else:
                                if "Game is not able to be spectated" in response["message"]:
                                    logPrint("现在还不能观战这个游戏类型，或者这个自定义对局未对观战者开放。\nThis game type cannot be spectated right now, or this custom game is not open to spectators.")
                                elif "Player was not found" in response["message"]:
                                    logPrint("该玩家未在游戏中。\nThis player isn't in a game currently.")
                                elif "Game not found" in response["message"]:
                                    logPrint("游戏已结束。\nThe game has ended.")
                                elif "Already in gameflow" in response["message"]:
                                    logPrint("您目前的状态不可观战。请等待游戏结束或者退出房间来进行观战。\nYou're not allowed to spectate for now. Please wait for the current game to end or exit the party or lobby to spectate any game.")
                                else:
                                    logPrint("观战失败。请通过客户端内右键点击一名好友，或者通过第三方工具来进行观战。\nSpectating failed. Please right click on a friend or use another third-party tool to spectate.")
            elif gameflow_phase == "Reconnect":
                gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                inGame_puuids = list(map(lambda x: x["puuid"], gameflow_session["gameData"]["playerChampionSelections"]))
                isSpectating = not current_info["puuid"] in inGame_puuids
                logPrint("检测到您正在游戏中。是否重新连接？（输入任意键重新连接，否则不连接。）\nDetected you're currently in a game. Do you want to reconnect? (Submit any non-empty string to reconnect, or null to refuse reconnecting.)")
                reconnect_str = logInput()
                reconnect = bool(reconnect_str)
                if reconnect:
                    response = await (await connection.request("POST", "/lol-gameflow/v1/reconnect")).json()
                    logPrint(response)
                    if response == None:
                        logPrint("重新连接成功。\nReconnect succeeded.")
                    else:
                        if "errorCode" in response and response["message"] == "Reconnect is not available.":
                            logPrint("重新连接不可用。请重启客户端并重试。\nReconnect isn't available. Please restart the client and try again.")
                        else:
                            logPrint("重新连接失败。\nReconnect failed.")
            else:
                logPrint("您目前的状态不可观战。请等待游戏结束或者退出房间来进行观战。\nYou're not allowed to spectate for now. Please wait for the current game to end or exit the party or lobby to spectate any game.")
        elif option == "10":
            logPrint("请选择静音场景：\nPlease select a mute situation:\n0\t返回上一层（Return to the last step）\n1\t预组队语音（Premade voice）\n2\t英雄选择小队聊天（Group chat during champ select）")
            while True:
                situation = logInput()
                if situation == "":
                    continue
                elif situation[0] == "0":
                    break
                elif situation[0] == "1":
                    voiceAvailability = await (await connection.request("GET", "/lol-premade-voice/v1/availability")).json()
                    if voiceAvailability["connectedToVoiceServer"]:
                        if voiceAvailability["enabled"]:
                            if voiceAvailability["voiceChannelAvailable"]:
                                logPrint("请选择要更改的设置类别：\nPlease choose an action:\n0\t返回上一层（Return to the last step）\n1\t更改输入设置（Change input settings）\n2\t更改输出设置（Change output settings）\n3\t重置使用提示（Reset first-experience hints）")
                                while True:
                                    setting = logInput()
                                    if setting == "":
                                        continue
                                    elif setting[0] == "0":
                                        logPrint("请选择静音场景：\n0\t返回上一层（Return to the last step）\n1\t预组队语音（Premade voice）\n2\t英雄选择小队聊天（Group chat during champ select）")
                                        break
                                    elif setting[0] == "1":
                                        capture_permission = await (await connection.request("GET", "/lol-premade-voice/v1/devices/capture/permission")).json()
                                        if capture_permission:
                                            logPrint("请选择具体设置：\nPlease select a detailed setting:\n0\t返回上一层（Return to the last step）\n1\t更改输入设备（Switch the capture device）\n2\t测试当前输入设备（Test the current capture device）\n3\t切换输入模式（Switch the input mode）\n4\t设置语音激活阈值（Change voice activation threshold）\n5\t设置【按键发言】热键（不可用）【Change Push to Talk hotkey (not available)】\n6\t设置输入音量（Set input volume）\n7\t自我静音/解除自我静音（Self mute/unmute）\n8\t输出设置信息（Output settings）")
                                            while True:
                                                action = logInput()
                                                if action == "":
                                                    continue
                                                elif action[0] == "0":
                                                    break
                                                elif action[0] == "1":
                                                    captureDevices_df = await sort_capture_devices(connection)
                                                    if len(captureDevices_df) == 1:
                                                        logPrint("未检测到输入设备。\nNo capture devices detected.")
                                                    else:
                                                        logPrint("您的输入设备信息如下：\nYour capture devices:")
                                                        print(format_df(captureDevices_df, print_index = True)[0])
                                                        log.write(format_df(captureDevices_df, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                        logPrint("请选择您要使用的输入设备：\nPlease select an capture device to use:")
                                                        while True:
                                                            deviceIndex = logInput()
                                                            if deviceIndex == "":
                                                                continue
                                                            elif deviceIndex == "0":
                                                                break
                                                            else:
                                                                try:
                                                                    deviceIndex = eval(deviceIndex)
                                                                except ValueError:
                                                                    traceback_info = traceback.format_exc()
                                                                    logPrint(traceback_info)
                                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                else:
                                                                    if isinstance(deviceIndex, int):
                                                                        if deviceIndex in range(1, len(captureDevices_df)):
                                                                            if True or captureDevices_df.loc[deviceIndex, "usable"]: #有时用户的确有切换到不可用输入设备的需要（Sometimes the user does get the demand of switching to a capture device that isn't usable）
                                                                                deviceName = captureDevices_df.loc[deviceIndex, "name"]
                                                                                response = await (await connection.request("PUT", "/lol-premade-voice/v1/capturedevices", data = deviceName)).json() #这里的设备名称改成句柄也是可以的（Here the device handle works, too）
                                                                                logPrint(response)
                                                                                if response == None:
                                                                                    captureDevices = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
                                                                                    captureDevices_transformed = {}
                                                                                    for device in captureDevices:
                                                                                        captureDevices_transformed[device["name"]] = device
                                                                                    if captureDevices_transformed[deviceName]["is_current_device"]:
                                                                                        logPrint("输入设备已切换为%s。\nThe capture device has switched to %s." %(deviceName, deviceName))
                                                                                    else:
                                                                                        logPrint("输入设备切换失败。\nCapture device switch failed.")
                                                                                    break
                                                                                else:
                                                                                    logPrint("输入设备切换失败。\nCapture device switch failed.")
                                                                            else:
                                                                                logPrint("您选择的输入设备不可用。请切换一个设备并重试。\nThe capture device you selected isn't usable. Please switch another device and try again.")
                                                                        else:
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                elif action[0] == "2":
                                                    captureDevices = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
                                                    captureDevices_transformed = {}
                                                    for device in captureDevices:
                                                        captureDevices_transformed[device["handle"]] = device
                                                    voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                                                    current_captureDevice_name = captureDevices_transformed[voiceSettings["currentCaptureDeviceHandle"]]["name"]
                                                    logPrint("您当前的输入设备是%s。\nThe current capture device is %s." %(current_captureDevice_name, current_captureDevice_name))
                                                    while True:
                                                        logPrint("输入任意非空字符串以开始测试，或者直接按回车键以返回上一层。\nSubmit any non-empty string to start mic-test, or press Enter directly to return to the last step.")
                                                        micTest_str = logInput()
                                                        micTest = bool(micTest_str)
                                                        if micTest:
                                                            response = await (await connection.request("POST", "/lol-premade-voice/v1/mic-test")).json()
                                                            logPrint(response)
                                                            logPrint("按回车键以结束测试。\nPress Enter to end the test.")
                                                            logInput()
                                                            response = await (await connection.request("DELETE", "/lol-premade-voice/v1/mic-test")).json()
                                                            logPrint(response)
                                                            continue
                                                        else:
                                                            break
                                                elif action[0] == "3":
                                                    logPrint("请选择输入模式：\nPlease select an input mode:\n0\t返回上一层（Return to the last step）\n1\t语音活跃度（Voice activity）\n2\t按住以发言（Push to talk）")
                                                    while True:
                                                        mode = logInput()
                                                        if mode == "":
                                                            continue
                                                        elif mode[0] == "0":
                                                            break
                                                        elif mode[0] == "1":
                                                            response = await (await connection.request("PUT", "/lol-premade-voice/v1/self/inputMode", data = "voiceActivity")).json()
                                                            logPrint(response)
                                                            if response == None:
                                                                logPrint("输入模式已改为语音活跃度。\nInput mode has switched to Voice Activity.")
                                                            else:
                                                                logPrint("输入模式切换失败。\nInput mode switch failed.")
                                                            break
                                                        elif mode[0] == "2":
                                                            pttAvailable = await (await connection.request("POST", "/lol-premade-voice/v1/push-to-talk/check-available", data = "0")).json() #这里比较神奇的地方是把POST改成其它方法会导致下面的response也会受到影响（Here a magical thing is if "POST" is changed into another HTTP method, then the following `response` will be influenced）
                                                            if pttAvailable:
                                                                response = await (await connection.request("PUT", "/lol-premade-voice/v1/self/inputMode", data = "pushToTalk")).json()
                                                                logPrint(response)
                                                                if response == None:
                                                                    logPrint("输入模式已改为按住以发言。\nInput mode has switched to Push to Talk.")
                                                                else:
                                                                    logPrint("输入模式切换失败。\nInput mode switch failed.")
                                                            else:
                                                                logPrint("无法启用按住以发言。如果要启用【按键发言】，你必须提供额外的访问许可。你可以点击MacOS命令符或在系统偏好设置中，在安全及隐私(Security & Privacy) > 隐私(Privacy) > 可访问性(Accessibility)下启用LeagueClient.app的检查框。\nCan't enable Push to Talk. To enable push to talk, you must grant additional accessibility permissions. Either click on the MacOS prompt or in System Preferences, enable the checkbox for LeagueClient.app under Security & Privacy > Privacy > Accessibility.")
                                                            break
                                                        else:
                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                elif action[0] == "4":
                                                    logPrint("请输入一个不超过100的自然数。\nPlease enter a nonnegative integer not greater than 100.")
                                                    while True:
                                                        sensitivity = logInput()
                                                        if sensitivity == "":
                                                            continue
                                                        elif sensitivity[0] == "q":
                                                            break
                                                        else:
                                                            try:
                                                                sensitivity = int(sensitivity)
                                                            except ValueError:
                                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                            else:
                                                                response = await (await connection.request("PUT", "/lol-premade-voice/v1/self/activationSensitivity", data = sensitivity)).json()
                                                                logPrint(response)
                                                                if response == None:
                                                                    voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                                                                    logPrint("语音激活阈值已设置为%d%%。\nVoice activation threshold is set as %d%%." %(voiceSettings["vadSensitivity"], voiceSettings["vadSensitivity"]))
                                                                    break
                                                                else:
                                                                    if response["httpStatus"] == 400 and response["httpStatus"] == f"Value {sensitivity} for 'sensitivity' of type int32 is out of range":
                                                                        logPrint("您输入的整数过大。请重新输入。\nThe integer you input is too large. Please try again.")
                                                                    else:
                                                                        logPrint("语音激活阈值修改失败。\nVoice activation threshold change failed.")
                                                elif action[0] == "5":
                                                    pttAvailable = await (await connection.request("POST", "/lol-premade-voice/v1/push-to-talk/check-available", data = "0")).json() #这里和上面一样神奇（This is just as magical as above）
                                                    if pttAvailable:
                                                        logPrint('请输入按键字符串。按键字符串应为单键或组合键，如“[c]”“[Ctrl][c]”“[Shift][Ctrl][c]”“[<Unbound>]”。\nPlease input the key string. A key string represents either a single key or a combined key, like "[c]", "[Ctrl][c]", "[Shift][Ctrl][c]" or "[<Unbound>]".')
                                                        while True:
                                                            keyStr = logInput()
                                                            if keyStr == "0":
                                                                break
                                                            response = await (await connection.request("POST", "/lol-premade-voice/v1/gameClientUpdatedPTTKey", data = keyStr)).json()
                                                            logPrint(response)
                                                            if response == None:
                                                                voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                                                                logPrint("【按键发言】热键已设置为%s。\nPush to Talk hotkey is set as %s." %(voiceSettings["pttKey"], voiceSettings["pttKey"]))
                                                                break
                                                            else:
                                                                logPrint("【按键发言】热键设置失败。请检查按键字符串是否规范。\nPush to Talk hotkey change failed. Please check if the key string is standard.")
                                                    else:
                                                        logPrint("按住以发言不可用。如果要启用【按键发言】，你必须提供额外的访问许可。你可以点击MacOS命令符或在系统偏好设置中，在安全及隐私(Security & Privacy) > 隐私(Privacy) > 可访问性(Accessibility)下启用LeagueClient.app的检查框。\nPush to Talk not available. To enable push to talk, you must grant additional accessibility permissions. Either click on the MacOS prompt or in System Preferences, enable the checkbox for LeagueClient.app under Security & Privacy > Privacy > Accessibility.")
                                                elif action[0] == "6":
                                                    logPrint("请输入一个不超过100的自然数。\nPlease enter a nonnegative integer not greater than 100.")
                                                    while True:
                                                        micLevel = logInput()
                                                        if micLevel == "":
                                                            continue
                                                        elif micLevel[0] == "q":
                                                            break
                                                        else:
                                                            try:
                                                                micLevel = int(micLevel)
                                                            except ValueError:
                                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                            else:
                                                                response = await (await connection.request("PUT", "/lol-premade-voice/v1/self/micLevel", data = micLevel)).json()
                                                                logPrint(response)
                                                                if response == None:
                                                                    voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                                                                    logPrint(f"输入音量（增强）已设置为%d%%。\nInput Volume (Gain) is set as %d%%." %(voiceSettings["micLevel"], voiceSettings["micLevel"]))
                                                                    break
                                                                else:
                                                                    if response["httpStatus"] == 400 and response["httpStatus"] == f"Value {micLevel} for 'micLevel' of type int32 is out of range":
                                                                        logPrint("您输入的整数过大。请重新输入。\nThe integer you input is too large. Please try again.")
                                                                    else:
                                                                        logPrint("输入音量（增强）修改失败。\nInput Volume (Gain) change failed.")
                                                elif action[0] == "7":
                                                    voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                                                    if voiceSettings["localMicMuted"]:
                                                        response = await (await connection.request("PUT", "/lol-premade-voice/v1/self/mute", data = "0")).json()
                                                        logPrint(response)
                                                        if response == None:
                                                            logPrint("自我静音已解除。\nSelf unmuted.")
                                                        else:
                                                            logPrint("自我静音解除失败。\nSelf unmute failed.")
                                                    else:
                                                        response = await (await connection.request("PUT", "/lol-premade-voice/v1/self/mute", data = "1")).json()
                                                        logPrint(response)
                                                        if response == None:
                                                            logPrint("已自我静音。\nSelf muted.")
                                                        else:
                                                            logPrint("自我静音失败。\nSelf mute failed.")
                                                elif action[0] == "8":
                                                    captureDevices = await (await connection.request("GET", "/lol-premade-voice/v1/capturedevices")).json()
                                                    captureDevices_transformed = {}
                                                    for device in captureDevices:
                                                        captureDevices_transformed[device["handle"]] = device
                                                    voiceSettings = await (await connection.request("GET", "/lol-premade-voice/v1/settings")).json()
                                                    logPrint("语音设置如下：\nVoice settings:")
                                                    voiceSettings_data = {"项目": ["自动加入语音频道", "连接时静音", "当前输入设备句柄", "当前输入设备名称", "输入音量", "已自我静音", "输入模式", "语音活跃度已激活", "语音活跃度阈值", "语音检测延迟", "按键发言已激活", "按键发言热键", "允许回环"], "Items": ["autoJoin", "muteOnConnect", "currentCaptureDeviceHandle", "currentCaptureDeviceName", "micLevel", "localMicMuted", "inputMode", "vadActive", "vadSensitivity", "vadHangoverTime", "pttActive", "pttKey", "loopbackEnabled"], "值": [voiceSettings["autoJoin"], voiceSettings["muteOnConnect"], voiceSettings["currentCaptureDeviceHandle"], captureDevices_transformed[voiceSettings["currentCaptureDeviceHandle"]]["name"], voiceSettings["micLevel"], voiceSettings["localMicMuted"], voiceSettings["inputMode"], voiceSettings["vadActive"], voiceSettings["vadSensitivity"], voiceSettings["vadHangoverTime"], voiceSettings["pttActive"], voiceSettings["pttKey"], voiceSettings["loopbackEnabled"]]}
                                                    voiceSettings_df = pandas.DataFrame(data = voiceSettings_data)
                                                    print(format_df(voiceSettings_df, align = "><^")[0], end = "\n\n")
                                                    log.write(format_df(voiceSettings_df, width_exceed_ask = False, direct_print = False, align = "><^")[0] + "\n\n")
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择具体设置：\nPlease select a detailed setting:\n0\t返回上一层（Return to the last step）\n1\t更改输入设备（Switch the capture device）\n2\t测试当前输入设备（Test the current capture device）\n3\t切换输入模式（Switch the input mode）\n4\t设置语音激活阈值（Change voice activation threshold）\n5\t设置【按键发言】热键（不可用）【Change Push to Talk hotkey (not available)】\n6\t设置输入音量（Set input volume）\n7\t自我静音/解除自我静音（Self mute/unmute）\n8\t输出设置信息（Output settings）")
                                        else:
                                            logPrint("您的输入设备没有获得访问许可。\nYour capture devices aren't granted accessibility permissions.")
                                    elif setting[0] == "2":
                                        participant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
                                        if len(participant_records) == 0:
                                            logPrint("您尚未加入语音频道。请连接至语音。\nYou haven't joined the voice channel. Please connect to League Voice.")
                                        else:
                                            for i in range(len(participant_records)):  #确定自己的编号，因为自己不应该被静音，虽然其实静音自己并不会造成什么影响（Determine the index of the user itself, for he/she shouldn't mute him/herself, although muting itself doesn't make any difference）
                                                if participant_records[i]["puuid"] == current_info["puuid"]:
                                                    selfIndex = i + 1 #数据框的中文表头占用了1个索引位置（The Chinese header of the dataframe takes up an index）
                                                    break
                                            logPrint("语音频道内的玩家音量设置如下：\nVoice settings of participants in the current voice channel:")
                                            participant_record_df = await sort_voice_participants(connection)
                                            participant_record_fields_to_print = ["gameName", "tagLine", "isMuted", "volume", "isSpeaking", "energy"]
                                            print(format_df(participant_record_df.loc[:, participant_record_fields_to_print])[0])
                                            log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                            logPrint("请选择设置方法：\nPlease select a voice setting:\n0\t返回上一层（Return to the last step）\n1\t静音/解除静音（Mute/Unmute）\n2\t修改音量（Change volume）")
                                            while True:
                                                action = logInput()
                                                if action == "":
                                                    continue
                                                elif action[0] == "0":
                                                    break
                                                elif action[0] == "1":
                                                    logPrint("请选择静音/解除静音模式：\nPlease select a mute mode:\n0\t返回上一层（Return to the last step）\n1\t单个静音/解除静音（Single）\n2\t批量静音/解除静音（In batches）\n3\t全部静音/解除静音（All）")
                                                    while True:
                                                        index_got = False
                                                        mode = logInput()
                                                        if mode == "":
                                                            continue
                                                        elif mode[0] == "0":
                                                            break
                                                        elif mode[0] == "1":
                                                            logPrint("请选择要静音的小队玩家的索引：\nPlease select a participant to mute:")
                                                            print(format_df(participant_record_df.loc[:, participant_record_fields_to_print], print_index = True)[0])
                                                            log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                            while True:
                                                                mute_input = logInput()
                                                                if mute_input == "":
                                                                    continue
                                                                elif mute_input == "0":
                                                                    break
                                                                else:
                                                                    try:
                                                                        player_index = int(mute_input)
                                                                    except ValueError:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                    else:
                                                                        if player_index == selfIndex:
                                                                            logPrint("你不能静音你自己。\nYou can't mute yourself.")
                                                                        if player_index in range(1, len(participant_record_df)):
                                                                            index_got = True
                                                                            mute_indices = [player_index]
                                                                            break
                                                        elif mode[0] == "2":
                                                            logPrint("是否需要对小队玩家取子集？（输入任意键以开始打草稿，否则直接开始输入小队玩家索引。）\nDo you want to get a subset of the current participant data? (Submit any non-empty string to make a draft, or null to input the participant index directly.)")
                                                            draft_str = logInput()
                                                            draft = bool(draft_str)
                                                            if draft:
                                                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                                                while True:
                                                                    draft_option = logInput()
                                                                    if draft_option == "":
                                                                        continue
                                                                    elif draft_option[0] == "0":
                                                                        break
                                                                    elif draft_option[0] == "1":
                                                                        scope = {"format_df": format_df, "df": participant_record_df.copy(deep = True), "fields": participant_record_fields_to_print}
                                                                        logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["tagLine"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                                        subscope(scope)
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                                            logPrint('请输入要静音/解除静音的小队玩家的索引（见下面小队玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the participants to mute/mute (you may refer to the index column of the participant table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(participant_record_df)) if participant_record_df.loc[i, "gameName"] == "WordlessMeteor"]')
                                                            print(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], print_index = True, start_index = 1)[0])
                                                            log.write(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0]) + "\n"
                                                            logPrint('变量提示（Variable hints）：\nparticipant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()\nparticipant_record_df = await sort_voice_participants(connection)\nfor i in range(len(participant_records)):\n    if participant_records[i]["puuid"] == current_info["puuid"]:\n        selfIndex = i\n        break')
                                                            while True:
                                                                mute_str = logInput()
                                                                if mute_str == "":
                                                                    continue
                                                                elif mute_str[0] == "0":
                                                                    break
                                                                elif mute_str == "all":
                                                                    mute_indices = list(range(1, len(participant_record_df)))
                                                                    mute_indices.remove(selfIndex)
                                                                    index_got = True
                                                                    break
                                                                else:
                                                                    try:
                                                                        mute_indices = eval(mute_str)
                                                                    except:
                                                                        traceback_info = traceback.format_exc()
                                                                        logPrint(traceback_info)
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                        continue
                                                                    else:
                                                                        if isinstance(mute_indices, int):
                                                                            mute_indices = [mute_indices]
                                                                        elif not isinstance(mute_indices, list):
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                            continue
                                                                if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(participant_record_df) and x != selfIndex, mute_indices)) and len(mute_indices) == len(set(mute_indices)):
                                                                    index_got = True
                                                                    break
                                                                else:
                                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        elif mode[0] == "3":
                                                            index_got = True
                                                            mute_indices = list(range(1, len(participant_record_df)))
                                                            mute_indices.remove(selfIndex)
                                                        else:
                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        if index_got:
                                                            logPrint("您选择了以下%d名玩家：\nYou selected the following %d player(s):" %(len(mute_indices), len(mute_indices)))
                                                            print(format_df(participant_record_df.loc[mute_indices, participant_record_fields_to_print], print_index = True, reserve_index = True)[0])
                                                            log.write(format_df(participant_record_df.loc[mute_indices, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                                            logPrint("您想要将这些玩家静音，还是解除静音？（输入任意键以静音，否则解除静音。）\nDo you want to mute or unmute these participants? (Submit any non-empty string to mute, or null to unmute.)")
                                                            isMuted_str = logInput()
                                                            isMuted = bool(isMuted_str)
                                                            for player_index in mute_indices:
                                                                player_puuid = participant_record_df.loc[player_index, "puuid"]
                                                                player_summonerName = participant_record_df.loc[player_index, "gameName"] + "#" + participant_record_df.loc[player_index, "tagLine"]
                                                                response = await (await connection.request("PUT", f"/lol-premade-voice/v1/participants/{player_puuid}/mute", data = str(int(isMuted)))).json()
                                                                logPrint(response)
                                                                if response == None:
                                                                    if isMuted:
                                                                        logPrint(f"您已将玩家{player_summonerName}静音。\nYou muted the participant {player_summonerName}.")
                                                                    else:
                                                                        logPrint(f"您已将玩家{player_summonerName}解除静音。\nYou unmuted the participant {player_summonerName}.")
                                                                else:
                                                                    if isMuted:
                                                                        logPrint("静音失败。\nMute failed.")
                                                                    else:
                                                                        logPrint("解除静音失败。\nUnmute failed.")
                                                            logPrint("语音频道内的玩家音量设置如下：\nVoice settings of participants in the current voice channel:")
                                                            participant_record_df = await sort_voice_participants(connection)
                                                            participant_record_fields_to_print = ["gameName", "tagLine", "isMuted", "volume", "isSpeaking", "energy"]
                                                            print(format_df(participant_record_df.loc[:, participant_record_fields_to_print])[0])
                                                            log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                        logPrint("请选择静音/解除静音模式：\nPlease select a mute mode:\n0\t返回上一层（Return to the last step）\n1\t单个静音/解除静音（Single）\n2\t批量静音/解除静音（In batches）\n3\t全部静音/解除静音（All）")
                                                elif action[0] == "2":
                                                    logPrint("请选择音量修改模式：\nPlease select a mode to change volume:\n0\t返回上一层（Return to the last step）\n1\t单个修改音量（Single）\n2\t批量修改音量（In batches）\n3\t全部修改音量（All）\n4\t逐个修改音量（One by one）")
                                                    while True:
                                                        index_got = False
                                                        mode = logInput()
                                                        if mode == "":
                                                            continue
                                                        elif mode[0] == "0":
                                                            break
                                                        elif mode[0] == "1":
                                                            volume_share = True #表示是否所有小队玩家都改成相同的音量（Represents whether all participants except the user itself are set the same volume）
                                                            logPrint("请选择要修改音量的小队玩家的索引：\nPlease select a participant to change volume:")
                                                            print(format_df(participant_record_df.loc[:, participant_record_fields_to_print], print_index = True)[0])
                                                            log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                                            while True:
                                                                volumeChange_input = logInput()
                                                                if volumeChange_input == "":
                                                                    continue
                                                                elif volumeChange_input == "0":
                                                                    break
                                                                else:
                                                                    try:
                                                                        player_index = int(volumeChange_input)
                                                                    except ValueError:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                    else:
                                                                        if player_index == selfIndex: #自己看自己的音量始终是50（When the user looks at his/her own volume, it's always 50）
                                                                            logPrint("你无法修改自己的音量。\nYou can't change the volume of yourself.")
                                                                        if player_index in range(1, len(participant_record_df)):
                                                                            index_got = True
                                                                            volumeChange_indices = [player_index]
                                                                            break
                                                        elif mode[0] == "2":
                                                            volume_share = True
                                                            logPrint("是否需要对小队玩家取子集？（输入任意键以开始打草稿，否则直接开始输入小队玩家索引。）\nDo you want to get a subset of the current participant data? (Submit any non-empty string to make a draft, or null to input the participant index directly.)")
                                                            draft_str = logInput()
                                                            draft = bool(draft_str)
                                                            if draft:
                                                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                                                while True:
                                                                    draft_option = logInput()
                                                                    if draft_option == "":
                                                                        continue
                                                                    elif draft_option[0] == "0":
                                                                        break
                                                                    elif draft_option[0] == "1":
                                                                        scope = {"format_df": format_df, "df": participant_record_df.copy(deep = True), "fields": participant_record_fields_to_print}
                                                                        logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["tagLine"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                                        subscope(scope)
                                                                    else:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                                            logPrint('请输入要修改音量的小队玩家的索引（见下面小队玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the participants to change volume (you may refer to the index column of the participant table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(participant_record_df)) if participant_record_df.loc[i, "gameName"] == "WordlessMeteor"]')
                                                            print(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], print_index = True, start_index = 1)[0])
                                                            log.write(format_df(participant_record_df.loc[1:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                                            logPrint('变量提示（Variable hints）：\nparticipant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()\nparticipant_record_df = await sort_voice_participants(connection)\nfor i in range(len(participant_records)):\n    if participant_records[i]["puuid"] == current_info["puuid"]:\n        selfIndex = i\n        break')
                                                            while True:
                                                                volumeChange_str = logInput()
                                                                if volumeChange_str == "":
                                                                    continue
                                                                elif volumeChange_str[0] == "0":
                                                                    break
                                                                elif volumeChange_str == "all":
                                                                    volumeChange_indices = list(range(1, len(participant_record_df)))
                                                                    volumeChange_indices.remove(selfIndex)
                                                                    index_got = True
                                                                    break
                                                                else:
                                                                    try:
                                                                        volumeChange_indices = eval(volumeChange_str)
                                                                    except:
                                                                        traceback_info = traceback.format_exc()
                                                                        logPrint(traceback_info)
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                        continue
                                                                    else:
                                                                        if isinstance(volumeChange_indices, int):
                                                                            volumeChange_indices = [volumeChange_indices]
                                                                        elif not isinstance(volumeChange_indices, list):
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                            continue
                                                                if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(participant_record_df) and x != selfIndex, volumeChange_indices)) and len(volumeChange_indices) == len(set(volumeChange_indices)):
                                                                    index_got = True
                                                                    break
                                                                else:
                                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        elif mode[0] == "3":
                                                            volume_share = True
                                                            index_got = True
                                                            volumeChange_indices = list(range(1, len(participant_record_df)))
                                                            volumeChange_indices.remove(selfIndex)
                                                        elif mode[0] == "4":
                                                            volume_share = False
                                                            playerVolumes = {}
                                                            logPrint('请依次输入小队玩家的索引和要设置的音量值，以空格为分隔符。输入“-1”以结束输入。\nPlease input the index of the participant and the volume value to set one by one, split by space. Submit "-1" to end the input.')
                                                            while True:
                                                                volume_str = logInput()
                                                                if volume_str == "":
                                                                    continue
                                                                elif volume_str[0] == "0":
                                                                    index_got = False
                                                                    break
                                                                elif volume_str == "-1":
                                                                    break
                                                                else:
                                                                    try:
                                                                        player_index, volume = map(int, volume_str.split())
                                                                    except ValueError:
                                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                    else:
                                                                        if player_index == selfIndex:
                                                                            logPrint("你无法修改自己的音量。\nYou can't change the volume of yourself.")
                                                                        if player_index in range(1, len(participant_record_df)):
                                                                            index_got = True
                                                                            playerVolumes[player_index] = volume
                                                                            print(format_df(pandas.concat([participant_record_df.loc[playerVolumes.keys(), participant_record_fields_to_print], pandas.DataFrame(data = {"energy_to_change": playerVolumes.values()}, index = playerVolumes.keys())], axis = 1), print_index = True, reserve_index = True)[0])
                                                                            log.write(format_df(pandas.concat([participant_record_df.loc[playerVolumes.keys(), participant_record_fields_to_print], pandas.DataFrame(data = {"energy_to_change": playerVolumes.values()}, index = playerVolumes.keys())], axis = 1), width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                                                        else:
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        else:
                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        if index_got:
                                                            if mode[0] in {"1", "2", "3"}:
                                                                logPrint("您选择了以下%d名玩家：\nYou selected the following %d player(s):" %(len(volumeChange_indices), len(volumeChange_indices)))
                                                                print(format_df(participant_record_df.loc[volumeChange_indices, participant_record_fields_to_print], print_index = True, reserve_index = True)[0])
                                                                log.write(format_df(participant_record_df.loc[volumeChange_indices, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                                            if volume_share:
                                                                logPrint("请输入一个不超过100的自然数以设置音量：\nPlease enter a nonnegative integer not greater than 100 to set the volume:")
                                                                while True:
                                                                    volume = logInput()
                                                                    if volume == "":
                                                                        continue
                                                                    elif volume[0] == "q":
                                                                        break
                                                                    else:
                                                                        try:
                                                                            volume = int(volume)
                                                                        except ValueError:
                                                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                                        else:
                                                                            for player_index in volumeChange_indices:
                                                                                player_puuid = participant_record_df.loc[player_index, "puuid"]
                                                                                player_summonerName = participant_record_df.loc[player_index, "gameName"] + "#" + participant_record_df.loc[player_index, "tagLine"]
                                                                                response = await (await connection.request("PUT", f"/lol-premade-voice/v1/participants/{player_puuid}/volume", data = str(volume))).json()
                                                                                logPrint(response)
                                                                                if response == None:
                                                                                    participant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
                                                                                    participant_records_transformed = {}
                                                                                    for participant in participant_records:
                                                                                        participant_records_transformed[participant["puuid"]] = participant
                                                                                    volume = participant_records_transformed[player_puuid]["volume"]
                                                                                    logPrint(f"您已将{player_summonerName}的音量设置为{volume}.\nYou set the volume of {player_summonerName} as {volume}.")
                                                                                else:
                                                                                    logPrint(f"{player_summonerName}的音量设置失败。\nVolume of {player_summonerName} change failed.")
                                                                            break
                                                            else:
                                                                for player_index in playerVolumes:
                                                                    player_puuid = participant_record_df.loc[player_index, "puuid"]
                                                                    player_summonerName = participant_record_df.loc[player_index, "gameName"] + "#" + participant_record_df.loc[player_index, "tagLine"]
                                                                    volume = playerVolumes[player_index]
                                                                    response = await (await connection.request("PUT", f"/lol-premade-voice/v1/participants/{player_puuid}/volume", data = str(volume))).json()
                                                                    logPrint(response)
                                                                    if response == None:
                                                                        participant_records = await (await connection.request("GET", "/lol-premade-voice/v1/participant-records")).json()
                                                                        participant_records_transformed = {}
                                                                        for participant in participant_records:
                                                                            participant_records_transformed[participant["puuid"]] = participant
                                                                        volume = participant_records_transformed[player_puuid]["volume"]
                                                                        logPrint(f"您已将{player_summonerName}的音量设置为{volume}.\nYou set the volume of {player_summonerName} as {volume}.")
                                                                    else:
                                                                        logPrint(f"{player_summonerName}的音量设置失败。\nVolume of {player_summonerName} change failed.")
                                                            logPrint("语音频道内的玩家音量设置如下：\nVoice settings of participants in the current voice channel:")
                                                            participant_record_df = await sort_voice_participants(connection)
                                                            participant_record_fields_to_print = ["gameName", "tagLine", "isMuted", "volume", "isSpeaking", "energy"]
                                                            print(format_df(participant_record_df.loc[:, participant_record_fields_to_print])[0])
                                                            log.write(format_df(participant_record_df.loc[:, participant_record_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                                        logPrint("请选择音量修改模式：\nPlease select a mode to change volume:\n0\t返回上一层（Return to the last step）\n1\t单个修改音量（Single）\n2\t批量修改音量（In batches）\n3\t全部修改音量（All）\n4\t逐个修改音量（One by one）")
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择设置方法：\nPlease select a voice setting:\n0\t返回上一层（Return to the last step）\n1\t静音/解除静音（Mute/Unmute）\n2\t修改音量（Change volume）")
                                    elif setting[0] == "3":
                                        response = await (await connection.request("POST", "/lol-premade-voice/v1/first-experience/reset")).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("小队语音提示已启用。您将在客户端和游戏内看到相关提示。注意，重置提示在一个客户端进程进行时只能生效一次。\nLeague Voice hint enabled. You'll see tooltips both in League Client and in game. Note that tooltip reset can only come into effect once during each process living.")
                                        else:
                                            logPrint("小队语音提示重置失败。\nLeague Voice first-experience tooltips reset failed.")
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    logPrint("请选择要更改的设置类别：\nPlease choose an action:\n0\t返回上一层（Return to the last step）\n1\t更改输入设置（Change input settings）\n2\t更改输出设置（Change output settings）\n3\t重置使用提示（Reset first-experience hints）")
                                
                            else:
                                logPrint("语音频道不可用。加入一个小队来使用语音。\nVoice channel not available. Join a party to use League Voice.")
                        else:
                            logPrint("语音不可用。请检查麦克风和扬声器是否正确连接。\nVoice not available. Please check if your microphone and speaker has connected properly.")
                    else:
                        logPrint("您未连接到语音服务。请检查网络情况。如果这个问题持续存在，请重新启动英雄联盟客户端。\nYou're not connected to League Voice service. Please check your network condition. If this problem persists, please restart the League Client.")
                    logPrint("请选择静音场景：\nPlease select a mute situation:\n0\t返回上一层（Return to the last step）\n1\t预组队语音（Premade voice）\n2\t英雄选择小队聊天（Group chat during champ select）")
                elif situation[0] == "2":
                    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        if champ_select_session["isSpectating"]:
                            logPrint("您正在观战中。静音操作不适用。\nYou're spectating a game now. Player mute actions aren't applicable.")
                        else:
                            if len(champ_select_session["myTeam"]) == 1:
                                logPrint("没有玩家可以静音。\nNo players to mute.")
                            else:
                                muted_players = await (await connection.request("GET", "/lol-chat/v1/player-mutes")).json()
                                if len(muted_players) != 0:
                                    logPrint("您当前静音的玩家如下：\nCurrently muted players:")
                                    muted_player_df = await sort_muted_players(connection)
                                    muted_player_fields_to_print = ["obfuscatedPuuid", "gameName", "tagLine", "puuid", "isPlayerMuted", "isSettingsMuted", "isSystemMuted"]
                                    print(format_df(muted_player_df.loc[1:, muted_player_fields_to_print])[0])
                                    log.write(format_df(muted_player_df.loc[1:, muted_player_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                myTeamId = champ_select_session["myTeam"][0]["team"]
                                champSelect_team_df = await sort_champSelect_team(connection)
                                champSelect_myTeam_df = pandas.concat([champSelect_team_df.iloc[:1], champSelect_team_df[champSelect_team_df["team"] == myTeamId]], ignore_index = True)
                                for i in range(len(champSelect_myTeam_df)): #确定自己的编号，因为自己不应该被静音，虽然其实静音自己相当于不做任何操作（Determine the index of the user itself, for he/she shouldn't mute him/herself, although muting itself means nothing done）
                                    if champSelect_myTeam_df.loc[i, "puuid"] == current_info["puuid"]:
                                        myIndex = i
                                        break
                                else:
                                    logPrint("英雄选择数据异常。请确保您正在这场比赛中，且信息可见。\nUnexpected champ select data encountered. Please ensure you're current in this game and your information is visible.")
                                    logPrint("请选择静音场景：\n0\t返回上一层（Return to the last step）\n1\t预组队语音（Premade voice）\n2\t英雄选择小队聊天（Group chat during champ select）")
                                    continue
                                logPrint("当前英雄选择阵营数据如下：\nCurrent champ select team data:")
                                champSelect_team_fields_to_print = ["team_color", "cellId", "obfuscatedPuuid", "assignedPosition", "champion name", "champion alias"]
                                champSelect_myTeam_df_to_print = champSelect_myTeam_df.loc[:, champSelect_team_fields_to_print].reset_index(drop = True)
                                print(format_df(champSelect_myTeam_df.loc[1:, champSelect_team_fields_to_print], print_index = True, start_index = 1)[0])
                                log.write(format_df(champSelect_myTeam_df.loc[1:, champSelect_team_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                logPrint("请选择静音操作：\nPlease select a mute action:\n0\t返回上一层（Return to the last step）\n1\t单个静音（Single）\n2\t批量静音（In batches）\n3\t全部静音（All）\n4\t解除所有静音（Remove all）")
                                while True:
                                    index_got = False
                                    action = logInput()
                                    if action == "":
                                        continue
                                    elif action[0] == "0":
                                        break
                                    elif action[0] == "1":
                                        logPrint("请选择要静音的队友索引：\nPlease select an ally to mute:")
                                        print(format_df(champSelect_myTeam_df_to_print, print_index = True)[0])
                                        log.write(format_df(champSelect_myTeam_df_to_print, width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                                        while True:
                                            mute_input = logInput()
                                            if mute_input == "":
                                                continue
                                            elif mute_input == "0":
                                                break
                                            else:
                                                try:
                                                    ally_index = int(mute_input)
                                                except ValueError:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                else:
                                                    if ally_index == myIndex:
                                                        logPrint("你不能静音你自己。\nYou can't mute yourself.")
                                                    if ally_index in range(1, len(champSelect_myTeam_df)):
                                                        index_got = True
                                                        mute_indices = [ally_index]
                                                        break
                                    elif action[0] == "2":
                                        logPrint("是否需要对队友取子集？（输入任意键以开始打草稿，否则直接开始输入队友索引。）\nDo you want to get a subset of the current ally data? (Submit any non-empty string to make a draft, or null to input the ally index directly.)")
                                        draft_str = logInput()
                                        draft = bool(draft_str)
                                        if draft:
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                            while True:
                                                draft_option = logInput()
                                                if draft_option == "":
                                                    continue
                                                elif draft_option[0] == "0":
                                                    break
                                                elif draft_option[0] == "1":
                                                    scope = {"format_df": format_df, "df": champSelect_myTeam_df.copy(deep = True), "fields": champSelect_team_fields_to_print}
                                                    logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[df["cellId"] == 1].loc[1:, fields])[0])\nprint(format_df(df[df["championId"] == 350].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                    subscope(scope)
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        logPrint('请输入要静音的队友的索引（见下面队友信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of your allies to mute (you may refer to the index column of the ally table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(champSelect_myTeam_df)) if champSelect_myTeam_df.loc[i, "gameName"] == "WordlessMeteor"]')
                                        print(format_df(champSelect_myTeam_df.loc[1:, champSelect_team_fields_to_print], print_index = True, start_index = 1)[0])
                                        log.write(format_df(champSelect_myTeam_df.loc[1:, champSelect_team_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                        logPrint('变量提示（Variable hints）：\nchamp_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()\nmyTeamId = champ_select_session["myTeam"][0]["team"]\nchampSelect_team_df = await sort_champSelect_team(connection)\nchampSelect_myTeam_df = pandas.concat([champSelect_team_df.loc[:1], champSelect_team_df[champSelect_team_df["team"] == myTeamId]], ignore_index = True)\nfor i in range(len(champSelect_myTeam_df)):\n    if champSelect_myTeam_df.loc[i, "puuid"] == current_info["puuid"]:\n        myIndex = i\n        break')
                                        while True:
                                            mute_str = logInput()
                                            if mute_str == "":
                                                continue
                                            elif mute_str[0] == "0":
                                                break
                                            elif mute_str == "all":
                                                mute_indices = list(range(1, len(champSelect_myTeam_df)))
                                                mute_indices.remove(myIndex)
                                                index_got = True
                                                break
                                            else:
                                                try:
                                                    mute_indices = eval(mute_str)
                                                except:
                                                    traceback_info = traceback.format_exc()
                                                    logPrint(traceback_info)
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                                else:
                                                    if isinstance(mute_indices, int):
                                                        mute_indices = [mute_indices]
                                                    elif not isinstance(mute_indices, list):
                                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                        continue
                                            if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(champSelect_myTeam_df) and x != myIndex, mute_indices)) and len(mute_indices) == len(set(mute_indices)):
                                                index_got = True
                                                break
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    elif action[0] == "3":
                                        index_got = True
                                        mute_indices = list(range(1, len(champSelect_myTeam_df)))
                                        mute_indices.remove(myIndex)
                                    elif action[0] == "4":
                                        index_got = False
                                        response = await (await connection.request("DELETE", "/lol-chat/v1/player-mutes")).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("所有队友被已解除静音。\nYour allies are unmuted.")
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    if index_got:
                                        if action[0] in {"1", "2", "3"}:
                                            logPrint("您选择了以下%d名队友：\nYou selected the following %d ally/allies:" %(len(mute_indices), len(mute_indices)))
                                            print(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_team_fields_to_print], print_index = True, reserve_index = True)[0])
                                            log.write(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_team_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                        mute_puuids = []
                                        for ally_index in mute_indices:
                                            ally_nameVisibilityType = champSelect_myTeam_df.loc[ally_index, "nameVisibilityType"]
                                            ally_obfuscatedPuuid = champSelect_myTeam_df.loc[ally_index, "obfuscatedPuuid"]
                                            ally_puuid = champSelect_myTeam_df.loc[ally_index, "puuid"]
                                            mute_puuids.append(ally_obfuscatedPuuid if ally_nameVisibilityType == "HIDDEN" else ally_puuid)
                                        logPrint("您想要将这些队友静音，还是解除静音？（输入任意键以静音，否则解除静音。）\nDo you want to mute or unmute these allies? (Submit any non-empty string to mute, or null to unmute.)")
                                        isMuted_str = logInput()
                                        isMuted = bool(isMuted_str)
                                        body = {"puuids": mute_puuids, "isMuted": isMuted}
                                        logPrint("请选择（解除）静音模式：\nPlease select a(n) (un)mute mode:\n0\t返回上一层（Return to the last step）\n1\t玩家静音（Player mute）\n2\t系统静音（System mute）")
                                        while True:
                                            mode = logInput()
                                            if mode == "":
                                                continue
                                            elif mode[0] == "0":
                                                break
                                            elif mode[0] == "1":
                                                response = await (await connection.request("POST", "/lol-chat/v1/player-mutes", data = body)).json()
                                                logPrint(response)
                                                if response == None:
                                                    if isMuted:
                                                        logPrint("您已将以下队友静音。\nYou muted the following allies.")
                                                    else:
                                                        logPrint("您已将以下队友解除静音。\nYou unmuted the following allies.")
                                                    print(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_team_fields_to_print], print_index = True, reserve_index = True)[0])
                                                    log.write(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_team_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                                    break
                                                else:
                                                    if isMuted:
                                                        logPrint("静音失败。\nMute failed.")
                                                    else:
                                                        logPrint("解除静音失败。\nUnmute failed.")
                                            elif mode[0] == "2":
                                                response = await (await connection.request("POST", "/lol-chat/v1/system-mutes", data = body)).json()
                                                logPrint(response)
                                                if response == None:
                                                    if isMuted:
                                                        logPrint("您已将以下队友静音。\nYou muted the following allies.")
                                                    else:
                                                        logPrint("您已将以下队友解除静音。\nYou unmuted the following allies.")
                                                    log.write(format_df(champSelect_myTeam_df.loc[mute_indices, champSelect_team_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
                                                    break
                                                else:
                                                    if isMuted:
                                                        logPrint("静音失败。\nMute failed.")
                                                    else:
                                                        logPrint("解除静音失败。\nUnmute failed.")
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        muted_players = await (await connection.request("GET", "/lol-chat/v1/player-mutes")).json()
                                        if len(muted_players) != 0:
                                            logPrint("您当前静音的玩家如下：\nCurrently muted players:")
                                            muted_player_df = await sort_muted_players(connection)
                                            muted_player_fields_to_print = ["obfuscatedPuuid", "gameName", "tagLine", "puuid", "isPlayerMuted", "isSettingsMuted", "isSystemMuted"]
                                            print(format_df(muted_player_df.loc[1:, muted_player_fields_to_print])[0])
                                            log.write(format_df(muted_player_df.loc[1:, muted_player_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                                    logPrint("请选择静音操作：\nPlease select a mute action:\n0\t返回上一层（Return to the last step）\n1\t单个静音（Single）\n2\t批量静音（In batches）\n3\t全部静音（All）\n4\t解除所有静音（Remove all）")
                    else:
                        logPrint("提示：以下静音操作仅在英雄选择阶段生效。请确保您目前正在英雄选择阶段。\nHint: The following mute actions only apply in a champ select group chat. Please confirm that you're during champ select.")
                    logPrint("请选择静音场景：\n0\t返回上一层（Return to the last step）\n1\t预组队语音（Premade voice）\n2\t英雄选择小队聊天（Group chat during champ select）")
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        #time.sleep(2) #原意是通过2秒的延迟使得好友数据及时更新，但是好友数据用不着在这里更新，反倒是在各个选项下更深的地方需要更新。然而如果你要取消注释也有说法，因为第一层好友操作的输出很长，可能会瞬间覆盖上一次结果（Originally intended to let the friend data update in time, but it's not necessary for friend data to be updated here. Instead, it needs updating in some deeper hierachies of those if-statements above. It's rather reasonable if you want to uncomment this piece of code, however, because output of the first layer turns out to be too long, so that it may cover the last result）

#-----------------------------------------------------------------------------
# 黑名单管理（Black list management）
#-----------------------------------------------------------------------------
async def sort_blockList_data(connection, CustomURF_blockList_enabled: bool = False, blockList: list = []):
    blockList_header = {"gameName": "玩家昵称", "gameTag": "昵称编号", "icon": "召唤师图标序号", "id": "社交代码", "name": "显示名", "pid": "社交代码", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "icon title": "召唤师图标名称"}
    blockList_header_keys = list(blockList_header.keys())
    if CustomURF_blockList_enabled:
        if isinstance(blockList, list) and all(map(lambda x: isinstance(x, dict), blockList)) and all(i in player for player in blockList for i in ["gameName", "gameTag", "icon", "id", "name", "pid", "puuid", "summonerId"]):
            blockList = blockList[:]
        else:
            logPrint("黑名单数据格式错误！函数只生成空表。\nBlock list data format ERROR! The function will only return an empty table.")
            blockList_df = pandas.DataFrame(data = blockList_header, index = [0])
            return blockList_df
    else:
        blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
    summonerIcons_source = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    summonerIcons = {}
    for icon in summonerIcons_source:
        summonerIcons[icon["id"]] = icon
    blockList_data = {}
    for i in range(len(blockList_header_keys)):
        key = blockList_header_keys[i]
        blockList_data[key] = []
    for player in blockList:
        for i in range(len(blockList_header_keys)):
            key = blockList_header_keys[i]
            if i == 8:
                blockList_data[key].append(summonerIcons[player["icon"]][key.split()[1]])
            else:
                blockList_data[key].append(player[key])
    blockList_statistics_output_order = [0, 1, 4, 7, 5, 6, 2, 8]
    blockList_data_organized = {}
    for i in blockList_statistics_output_order:
        key = blockList_header_keys[i]
        blockList_data_organized[key] = blockList_data[key]
    blockList_df = pandas.DataFrame(data = blockList_data_organized)
    blockList_df = pandas.concat([pandas.DataFrame([blockList_header])[blockList_df.columns], blockList_df], ignore_index = True)
    return blockList_df

async def blacklist_behavior_simulation(connection):
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_hovercard = await (await connection.request("GET", "/lol-hovercard/v1/friend-info/%s" %(current_info["puuid"]))).json()
    CustomURF_BlockList_enabled = False
    while True:
        logPrint("请选择黑名单操作：\nPlease select an operation on the block list:\n0\t返回上一层（Return to the last step）\n1\t查看黑名单（Check the block list）\n2\t拉入聊天黑名单（Block）\n3\t检测活跃状态（Detect active state）\n4\t移出聊天黑名单（Unblock）")
        option = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] == "1":
            if CustomURF_BlockList_enabled:
                blockList = blockList_CustomURF[:]
            else:
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
            if len(blockList) == 0:
                logPrint("这里什么都没有。你的聊天黑名单是空的。\nNothing to see here. Your block list is empty.")
            else:
                blockList_df = await sort_blockList_data(connection, CustomURF_BlockList_enabled, blockList)
                blockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]
                print(format_df(blockList_df.loc[:, blockList_fields_to_print])[0])
                log.write(format_df(blockList_df.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
        elif option[0] == "2": #这部分代码框架来自好友行为模拟函数中，但是判断行为大大简化（The following code frame come from `friend_behavior_simulation` function, but the judgments are greatly simplified）
            if CustomURF_BlockList_enabled:
                logPrint("该操作目前不可用。\nThis option isn't available for now.")
            else:
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                blocked_puuids = set(map(lambda x: x["puuid"], blockList))
                logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t从文件中拉黑（From file）")
                while True:
                    info_got = False
                    mode = logInput()
                    if mode == "":
                        continue
                    elif mode == "0":
                        break
                    elif mode == "1":
                        logPrint("请输入要拉黑的玩家名称：\nPlease enter the summonerName of the player to block:")
                        while True:
                            blockName = logInput()
                            if blockName == "":
                                continue
                            elif blockName == "0":
                                info_got = False
                                break
                            else:
                                block_info = await get_info(connection, blockName)
                                if block_info["info_got"]:
                                    block_puuid = block_info["body"]["puuid"]
                                    if block_puuid == current_info["puuid"]:
                                        logPrint("你无法把自己拉入聊天黑名单。\nYou cannot block yourself, silly.")
                                    elif block_puuid in blocked_puuids:
                                        logPrint("你已经将%s拉入聊天黑名单。\nYou have already blocked %s." %(get_info_name(block_info["body"]), get_info_name(block_info["body"])))
                                    else:
                                        block_puuids = [block_puuid]
                                        block_summonerNames = [get_info_name(block_info["body"])]
                                        info_got = True
                                        break
                                else:
                                    logPrint(block_info["message"])
                    elif mode == "2":
                        block_puuids = []
                        block_summonerNames = []
                        logPrint('请依次输入要拉黑的玩家名称。输入“-1”以结束输入。\nPlease enter the summonerName of the player to block one by one. Submit "-1" to end the input.')
                        while True:
                            blockName = logInput()
                            if blockName == "":
                                continue
                            elif blockName == "0":
                                info_got = False
                                break
                            elif blockName == "-1":
                                break
                            else:
                                try:
                                    blockName_list = eval(blockName)
                                except:
                                    blockName_list = [blockName]
                                else:
                                    if isinstance(blockName_list, list) and all(map(lambda x: isinstance(x, (str, int)), blockName_list)):
                                        pass
                                    else:    
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                        continue
                                for blockName in blockName_list:
                                    block_info = await get_info(connection, blockName)
                                    if block_info["info_got"]:
                                        block_puuid = block_info["body"]["puuid"]
                                        block_summonerName = get_info_name(block_info["body"])
                                        if block_puuid == current_info["puuid"]:
                                            logPrint("你无法把自己拉入聊天黑名单。\nYou cannot block yourself, silly.")
                                        elif block_puuid in blocked_puuids:
                                            logPrint("你已经将%s拉入聊天黑名单。\nYou have already blocked %s." %(get_info_name(block_info["body"]), get_info_name(block_info["body"])))
                                        elif not block_puuid in block_puuids:
                                            block_puuids.append(block_puuid)
                                            block_summonerNames.append(block_summonerName)
                                            info_got = True
                                    else:
                                        logPrint(block_info["message"])
                    elif mode == "3":
                        logPrint("是否需要测试玩家信息的获取？（输入任意键以开始打草稿，否则直接开始输入要拉入聊天黑名单的玩家信息。）\nDo you want to test obtaining player information? (Submit any non-empty string to make a draft, or null to input the index of the players to block directly.)")
                        draft_str = logInput()
                        draft = bool(draft_str)
                        if draft:
                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                            while True:
                                draft_option = logInput()
                                if draft_option == "":
                                    continue
                                elif draft_option[0] == "0":
                                    break
                                elif draft_option[0] == "1":
                                    scope = {"get_info_name": get_info_name, "current_info": current_info, "blockList": blockList}
                                    logPrint('示例（Examples）：\nprint(dir()) #输出exec函数使用的作用域中的变量名称（Output names of variables to the scope of `exec` function）\nimport os, pandas, pyperclip #引入需要的库（Introduce required libraries）\nos.system("CLS") #清屏（Clear screen）\ndf = pandas.read_excel("black list.xlsx", sheet_name = "Sheet1") #示例：从工作簿中读取黑名单数据（Example: Read black list data from a workbook）\nblock_puuids = set(df.iloc[:, 2])\npyperclip.copy(str(block_puuids)) #将结果复制到全局剪贴板中，用于后续输入黑名单列表（Copy the result to the global clipboard for subsequently inputting the blocked player list）\n输入“-1”以退出测试。\nSubmit "-1" to quit the test.')
                                    subscope(scope)
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                        block_puuids = []
                        block_summonerNames = []
                        logPrint('请输入要拉黑的玩家名称列表。输入“0”以返回上一层。\nPlease submit a list containing summonerNames of players to block. Submit "0" to return to the last step.')
                        while True:
                            block_str = logInput()
                            if block_str == "":
                                continue
                            elif block_str[0] == "0":
                                info_got = False
                                break
                            else:
                                try:
                                    blockNames = eval(block_str)
                                except:
                                    traceback_info = traceback.format_exc()
                                    logPrint(traceback_info)
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                else:
                                    if isinstance(blockNames, list) and all(map(lambda x: isinstance(x, (int, str)), blockNames)):
                                        for blockName in blockNames:
                                            block_info = await get_info(connection, blockName)
                                            if block_info["info_got"]:
                                                block_puuid = block_info["body"]["puuid"]
                                                block_summonerName = get_info_name(block_info["body"])
                                                if block_puuid == current_info["puuid"]:
                                                    logPrint(f"[{blockName}]你无法把自己拉入聊天黑名单。\nYou cannot block yourself, silly.")
                                                elif block_puuid in blocked_puuids:
                                                    logPrint(f"[{blockName}]" + "你已经将%s拉入聊天黑名单。\nYou have already blocked %s." %(get_info_name(block_info["body"]), get_info_name(block_info["body"])))
                                                elif not block_puuid in block_puuids:
                                                    block_puuids.append(block_puuid)
                                                    block_summonerNames.append(block_summonerName)
                                                    info_got = True
                                            else:
                                                logPrint(f"[{blockName}]" + block_info["message"])
                                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    if info_got:
                        logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.' %("、".join(block_summonerNames), ", ".join(block_summonerNames)))
                        block_confirm_str = logInput()
                        block_confirm = block_confirm_str == "block"
                        if block_confirm:
                            for i in range(len(block_puuids)):
                                body = {"puuid": block_puuids[i]}
                                block_summonerName = block_summonerNames[i]
                                response = await (await connection.request("POST", f"/lol-chat/v1/blocked-players", data = body)).json()
                                logPrint(response)
                                if response == None:
                                    logPrint("%s已被拉入聊天黑名单。你再也不会看到TA的在线状态或是收到来自TA的信息了。\n%s has been blocked. You will no longer see them online or receive their messages." %(block_summonerName, block_summonerName))
                                else:
                                    if response["httpStatus"] == 400:
                                        logPrint("您未能成功将%s拉入聊天黑名单。也许TA已经在其中了。\nYou failed to block %s. Maybe he/she's already in it." %(block_summonerName, block_summonerName))
                                    else:
                                        logPrint("您未能成功将%s拉入聊天黑名单。\nYou failed to block %s." %(block_summonerName, block_summonerName))
                    blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                    blocked_puuids = set(map(lambda x: x["puuid"], blockList))
                    logPrint("请选择拉黑模式：\nPlease select a blocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个拉黑（Single）\n2\t批量拉黑（In batches）\n3\t从文件中拉黑（From file）")
        elif option[0] == "3":
            if CustomURF_BlockList_enabled:
                blockList = blockList_CustomURF[:]
                blockList_df = await sort_blockList_data(connection, True, blockList)
            else:
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                blockList_df = await sort_blockList_data(connection)
            blockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]
            blockList_transformed = {}
            for player in blockList:
                blockList_transformed[player["puuid"]] = player
            blocked_puuids = set(map(lambda x: x["puuid"], blockList))
            while True:
                gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                if gameflow_phase == "None":
                    logPrint("您尚未创建任何房间！请创建房间后再按回车键开始检测。\nYou haven't created any lobby yet! Please create a lobby and then start detection.")
                elif gameflow_phase in {"Lobby", "Matchmaking", "ReadyCheck", "ChampSelect"}:
                    #检测房间/小队内成员有无黑名单成员（Detect whether a blocked player is in the lobby / party）
                    lobby = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                    blocked_member_puuids = []
                    for member in lobby["members"]:
                        if member["puuid"] in blocked_puuids:
                            blocked_member_puuids.append(member["puuid"])
                        if member["puuid"] == current_info["puuid"]:
                            isLeader = member["isLeader"]
                    if len(blocked_member_puuids) == 0:
                        logPrint("小队/房间中无黑名单成员。\nNo blocked member detected in the current party / lobby.")
                    else:
                        logPrint("小队/房间中发现以下%d名成员在黑名单中：\nFound the following %d blocked member(s) in the lobby:" %(len(blocked_member_puuids), len(blocked_member_puuids)))
                        blockList_df_filtered_lobby = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_member_puuids)]], ignore_index = True)
                        print(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print])[0])
                        log.write(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                    #检测房间邀请中有无向黑名单成员发起的邀请（Detect whether there's any lobby invitation sent to a blocked player）
                    lobby_invitations = await (await connection.request("GET", "/lol-lobby/v1/lobby/invitations")).json()
                    toSummonerIds = list(map(lambda x: x["toSummonerId"], lobby_invitations))
                    blocked_invitee_puuids = []
                    for summonerId in toSummonerIds:
                        invitee_info = await get_info(connection, summonerId)
                        if invitee_info["info_got"]:
                            invitee_puuid = invitee_info["body"]["puuid"]
                            if invitee_puuid in blocked_puuids:
                                blocked_invitee_puuids.append(invitee_puuid)
                    if len(blocked_invitee_puuids) == 0:
                        logPrint("房间邀请中无黑名单玩家。\nNo blocked invitee detected in the lobby invitations.")
                    else:
                        logPrint("房间邀请中发现以下%d名玩家在黑名单中：\nFound the following %d blocked invitee(s) in the lobby invitations:" %(len(blocked_invitee_puuids), len(blocked_invitee_puuids)))
                        blockList_df_filtered_invid = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_invitee_puuids)]], ignore_index = True)
                        print(format_df(blockList_df_filtered_invid.loc[:, blockList_fields_to_print])[0])
                        log.write(format_df(blockList_df_filtered_invid.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                    if len(blocked_member_puuids) > 0 and isLeader and gameflow_phase != "ReadyCheck" and gameflow_phase != "ChampSelect": #房主有权遣离黑名单成员（The lobby owner or party leader has priviledge to kick the blocked members）
                        logPrint("检测到您是小队拥有者/房主。是否将黑名单成员移出小队/房间？\nDetected you're the party / lobby owner. Do you want to kick the blocked member(s)?")
                        kick_str = logInput()
                        kick = bool(kick_str)
                        if kick:
                            print(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print], print_index = True)[0])
                            log.write(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                            logPrint("请选择遣离方式：\nPlease select a kicking mode:\n0\t退出遣离（Quit kicking）\n1\t单个遣离（Single）\n2\t批量遣离（In batches）\n3\t全部遣离（All）")
                            while isLeader:
                                index_got = False
                                mode = logInput()
                                if mode == "":
                                    continue
                                elif mode[0] == "0":
                                    break
                                elif mode[0] == "1":
                                    logPrint("请输入要遣离的成员索引：\nPlease enter the index of the members to kick:")
                                    while True:
                                        kick_str = logInput()
                                        if kick_str == "":
                                            continue
                                        elif kick_str[0] == "0":
                                            index_got = False
                                            break
                                        else:
                                            try:
                                                blocked_index = int(kick_str)
                                            except ValueError:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            else:
                                                if blocked_index in range(1, len(blockList_df_filtered_lobby)):
                                                    kick_indices = [blocked_index]
                                                    index_got = True
                                                    break
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                elif mode[0] == "2":
                                    logPrint("是否需要对房间中的黑名单成员取子集？（输入任意键以开始打草稿，否则直接开始输入黑名单玩家索引。）\nDo you want to get a subset of the blocked member data? (Submit any non-empty string to make a draft, or null to input the blocked player index directly.)")
                                    draft_str = logInput()
                                    draft = bool(draft_str)
                                    if draft:
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        while True:
                                            draft_option = logInput()
                                            if draft_option == "":
                                                continue
                                            elif draft_option[0] == "0":
                                                break
                                            elif draft_option[0] == "1":
                                                scope = {"format_df": format_df, "df": blockList_df_filtered_lobby.copy(deep = True), "fields": blockList_fields_to_print}
                                                logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[df["gameName"] == "WordlessMeteor"].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                subscope(scope)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    logPrint('请输入要移出的队友的索引（见下面黑名单玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the blocked members to kick (you may refer to the index column of the blocked players below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i for i in range(len(blockList_df_filtered_lobby)) if blockList_df_filtered_lobby.loc[i, "gameName"] == "WordlessMeteor"]')
                                    print(format_df(blockList_df_filtered_lobby.loc[1:, blockList_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(blockList_df_filtered_lobby.loc[1:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint("是否查看变量提示？（输入任意键已查看，否则不查看。）\nDo you want to refer to the variable hint? (Submit any non-empty string to refer, or null to skip.)")
                                    check_hint_str = logInput()
                                    check_hint = bool(check_hint_str)
                                    if check_hint:
                                        logPrint('变量提示（Variable hints）：\nblockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()\nblockList_df = await sort_blockList_data(connection)\nblockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]\nblocked_puuids = set(map(lambda x: x["puuid"], blockList))\nblocked_member_puuids = []\nfor member in lobby["members"]:\n    if member["puuid"] in blocked_puuids:\n        blocked_member_puuids.append(member["puuid"])')
                                    else:
                                        logPrint("索引列表（Index list）：", end = "")
                                    while True:
                                        kick_str = logInput()
                                        if kick_str == "":
                                            continue
                                        elif kick_str == "0":
                                            index_got = False
                                            break
                                        elif kick_str == "all":
                                            kick_indices = list(range(1, len(blockList_df_filtered_lobby)))
                                            index_got = True
                                            break
                                        else:
                                            try:
                                                kick_indices = eval(kick_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            else:
                                                if isinstance(kick_indices, int):
                                                    kick_indices = [kick_indices]
                                                elif not isinstance(kick_indices, list):
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                        if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(blockList_df_filtered_lobby), kick_indices)) and len(kick_indices) == len(set(kick_indices)):
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                elif mode[0] == "3":
                                    index_got = True
                                    kick_indices = list(range(1, len(blockList_df_filtered_lobby)))
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if index_got:
                                    for blocked_index in kick_indices:
                                        blocked_summonerId = blockList_df_filtered_lobby.loc[blocked_index, "summonerId"]
                                        blocked_summonerName = blockList_df_filtered_lobby.loc[blocked_index, "gameName"] + "#" + blockList_df_filtered_lobby.loc[blocked_index, "gameTag"]
                                        response = await (await connection.request("POST", f"/lol-lobby/v2/lobby/members/{blocked_summonerId}/kick")).json()
                                        logPrint(response)
                                        if response == blocked_summonerId:
                                            logPrint(f"已将{blocked_summonerName}移出小队/房间。\nKicked {blocked_summonerName} from the party / lobby.")
                                        else:
                                            if response["httpStatus"] == 400 and response["message"] == "INVALID_ROLE_TRANSITION":
                                                logPrint("遣离失败！对方可能已经离开小队/房间，或者您不再是小队拥有者/房主了。\nKick failed! The member may have left the party / lobby, or you're not the party or lobby owner anymore.")
                                            elif response["httpStatus"] == 400 and response["message"] == "INVALID_PARTY_STATE":
                                                logPrint("小队/房间即将进入或已经进入英雄选择阶段，无法将其移出。\nFailed to kick the member because the party / lobby are going to enter or has entered the champ select stage.")
                                            elif response["httpStatus"] == 404 and response["message"] == "Couldn't kick player: Not found":
                                                logPrint("遣离失败！对方已经离开小队/房间了。\nKick failed! The member has already left the party / lobby.")
                                            elif response["httpStatus"] == 404 and response["message"] == "SUMMONER_NOT_FOUND":
                                                logPrint("您已经不在小队/房间内了。\nYou're no longer in the party / lobby.")
                                            else:
                                                logPrint("遣离失败！\nKick failed!")
                                    lobby = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                                    if "errorCode" in lobby and lobby["message"] == "LOBBY_NOT_FOUND":
                                        logPrint("您已经不在小队/房间内了。\nYou're no longer in the party / lobby.")
                                        break
                                    else:
                                        blocked_member_puuids = []
                                        for member in lobby["members"]:
                                            if member["puuid"] in blocked_puuids:
                                                blocked_member_puuids.append(member["puuid"])
                                            if member["puuid"] == current_info["puuid"]:
                                                isLeader = member["isLeader"]
                                        if len(blocked_member_puuids) == 0:
                                            logPrint("小队/房间中无黑名单成员。\nNo blocked member detected in the current party / lobby.")
                                            break
                                        else:
                                            logPrint("小队/房间中发现以下%d名成员在黑名单中：\nFound the following %d blocked member(s) in the lobby:" %(len(blocked_member_puuids), len(blocked_member_puuids)))
                                            blockList_df_filtered_lobby = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_member_puuids)]], ignore_index = True)
                                            logPrint(format_df(blockList_df_filtered_lobby.loc[:, blockList_fields_to_print])[0], write_time = False)
                                logPrint("请选择遣离方式：\nPlease select a kicking mode:\n0\t退出遣离（Quit kicking）\n1\t单个遣离（Single）\n2\t批量遣离（In batches）\n3\t全部遣离（All）")
                    gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                    if gameflow_phase == "ChampSelect":
                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                        if not champ_select_session["isSpectating"]:
                            team = champ_select_session["myTeam"] + champ_select_session["theirTeam"]
                            blocked_player_puuids = []
                            for player in team:
                                if player["puuid"] in blocked_puuids:
                                    blocked_player_puuids.append(player["puuid"])
                            if len(blocked_player_puuids) == 0:
                                logPrint("英雄选择阶段无黑名单成员。\nNo blocked member detected during the champ select stage.")
                            else:
                                logPrint("英雄选择阶段发现以下%d名成员在黑名单中：\nFound the following %d blocked player(s) during the champ select stage:" %(len(blocked_player_puuids), len(blocked_player_puuids)))
                                blockList_df_filtered_champSelect = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_player_puuids)]], ignore_index = True)
                                print(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print])[0])
                                log.write(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0])
                elif gameflow_phase in {"InProgress", "Reconnect"}:
                    gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                    gameData = gameflow_session["gameData"]
                    team = gameData["teamOne"] + gameData["teamTwo"]
                    blocked_player_puuids = []
                    for player in team:
                        if player["puuid"] in blocked_puuids:
                            blocked_player_puuids.append(player["puuid"])
                    if len(blocked_player_puuids) == 0:
                        logPrint("游戏中无黑名单成员。\nNo blocked member detected in game.")
                    else:
                        logPrint("游戏中发现以下%d名成员在黑名单中：\nFound the following %d blocked player(s) in game:" %(len(blocked_player_puuids), len(blocked_player_puuids)))
                        blockList_df_filtered_champSelect = pandas.concat([blockList_df.iloc[:1], blockList_df[blockList_df["puuid"].isin(blocked_player_puuids)]], ignore_index = True)
                        print(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print])[0])
                        log.write(format_df(blockList_df_filtered_champSelect.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                logPrint("检测完成！是否重新检测？（输入任意键以退出检测，否则重新检测。）\nDetection finished! Try again? (Submit any non-empty string to quit detection, or null to detect again.)")
                redetect_str = logInput()
                redetect = bool(redetect_str)
                if redetect:
                    break
        elif option[0] == "4":
            if CustomURF_BlockList_enabled:
                logPrint("该操作目前不可用。\nThis option isn't available for now.")
            else:
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                if len(blockList) == 0:
                    logPrint("这里什么都没有。你的聊天黑名单是空的。\nNothing to see here. Your block list is empty.")
                else:
                    logPrint("聊天黑名单如下：\nBlock list:")
                    player_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], blockList))
                    player_summonerIds = list(map(lambda x: x["summonerId"], blockList))
                    player_puuids = list(map(lambda x: x["puuid"], blockList))
                    blockList_df = await sort_blockList_data(connection)
                    blockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]
                    print(format_df(blockList_df.loc[:, blockList_fields_to_print], print_index = True)[0])
                    log.write(format_df(blockList_df.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                    logPrint("请选择取消拉黑模式：\nPlease select an unblocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个移出（Single）\n2\t批量移出（In batches）\n3\t全部移出（All）\n4\t从文件中移出（From file）")
                    while True:
                        index_got = False
                        mode = logInput()
                        if mode == "":
                            continue
                        elif mode == "0":
                            break
                        elif mode == "1":
                            logPrint("请输入要移出聊天黑名单的玩家索引或者名称：\nPlease enter the index or name of the blocked player to unblock:")
                            while True:
                                unblock_input = logInput()
                                if unblock_input == "":
                                    continue
                                elif unblock_input == "0":
                                    break
                                else:
                                    try:
                                        player_index = int(unblock_input) - 1
                                    except ValueError:
                                        player_summonerName = unblock_input
                                        if player_summonerName in player_summonerNames:
                                            player_index = player_summonerNames.index(player_summonerName)
                                        elif player_summonerName in set(map(str, player_summonerIds)):
                                            player_index = player_summonerIds.index(int(player_summonerName))
                                        elif player_summonerName in player_puuids:
                                            player_index = player_puuids.index(player_summonerName)
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        if player_index in range(len(blockList)):
                                            unblock_indices = [player_index]
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            continue
                        elif mode == "2":
                            logPrint("请选择您输入要移出聊天黑名单的玩家信息的方式：\nPlease select a method of inputting the information of the blocked players to be unblocked:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                            while True:
                                method = logInput()
                                if method == "":
                                    continue
                                elif method[0] == "0":
                                    break
                                elif method[0] == "1":
                                    logPrint("是否需要对黑名单玩家取子集？（输入任意键以开始打草稿，否则直接开始输入好友索引。）\nDo you want to get a subset of the current blocked player data? (Submit any non-empty string to make a draft, or null to input the blocked player index directly.)")
                                    draft_str = logInput()
                                    draft = bool(draft_str)
                                    if draft:
                                        logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                        while True:
                                            draft_option = logInput()
                                            if draft_option == "":
                                                continue
                                            elif draft_option[0] == "0":
                                                break
                                            elif draft_option[0] == "1":
                                                scope = {"format_df": format_df, "df": blockList_df.copy(deep = True), "fields": blockList_fields_to_print}
                                                logPrint('示例（Examples）：\nprint(dir())\nprint(format_df(df[(df["gameName"] == "WordlessMeteor") & (df["gameTag"] == "5071")].loc[1:, fields])[0])\n输入“-1”以退出取子集。\nSubmit "-1" to quit taking subsets.')
                                                subscope(scope)
                                            else:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t迭代式取子集（Take subsets iteratively）")
                                    logPrint('请输入要移出聊天黑名单的好友的索引（见下面聊天黑名单玩家信息表的索引列）。一些允许的输入格式：\nPlease submit the indices of the blocked players to unblock (you may refer to the index column of the blocked player table below). Allowed input formats look like these:\n1\n[1, 2, 3]\nall\n[i + 1 for i in range(len(blockList)) if blockList[i]["gameName"] == "WordlessMeteor"]')
                                    print(format_df(blockList_df.loc[1:, blockList_fields_to_print], print_index = True, start_index = 1)[0])
                                    log.write(format_df(blockList_df.loc[1:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, start_index = 1)[0] + "\n")
                                    logPrint('变量提示（Variable hints）：\nblockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()\nplayer_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], blockList))\nplayer_summonerIds = list(map(lambda x: x["summonerId"], blockList))\nplayer_puuids = list(map(lambda x: x["puuid"], blockList))\nblockList_df = await sort_blockList_data(connection)')
                                    while True:
                                        unblock_str = logInput()
                                        if unblock_str == "":
                                            continue
                                        elif unblock_str[0] == "0":
                                            break
                                        elif unblock_str == "all":
                                            unblock_indices = list(range(len(blockList)))
                                            index_got = True
                                            break
                                        else:
                                            try:
                                                unblock_indices = eval(unblock_str)
                                            except:
                                                traceback_info = traceback.format_exc()
                                                logPrint(traceback_info)
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                continue
                                            else:
                                                if isinstance(unblock_indices, int):
                                                    unblock_indices = [unblock_indices]
                                                elif not isinstance(unblock_indices, list):
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                        if all(map(lambda x: isinstance(x, int) and x > 0 and x < len(blockList_df), unblock_indices)) and len(unblock_indices) == len(set(unblock_indices)):
                                            unblock_indices = list(map(lambda x: x - 1, unblock_indices))
                                            index_got = True
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                elif method[0] == "2":
                                    logPrint('''请输入要移出聊天黑名单的玩家的召唤师名。每个玩家的召唤师名格式为{玩家昵称}#{昵称编号}。输入“-1”以结束输入。\nPlease submit the names of the blocked players to be unblocked. Each player's name should accord to the format {gameName}#{gameTag}. Submit "-1" to end the input.\n变量提示（Variable hints）：\nblockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()\nblockList_df = await sort_blockList_data(connection)''')
                                    unblock_indices = []
                                    while True:
                                        player_summonerName = logInput()
                                        if player_summonerName == "":
                                            continue
                                        elif player_summonerName == "0":
                                            index_got = False
                                            break
                                        elif player_summonerName == "-1":
                                            break
                                        else:
                                            try:
                                                player_summonerName_list = eval(player_summonerName)
                                            except:
                                                player_summonerName_list = [player_summonerName]
                                            else:
                                                if isinstance(player_summonerName_list, list) and all(map(lambda x: isinstance(x, (str, int)), player_summonerName_list)):
                                                    pass
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                            for player_summonerName in player_summonerName_list:
                                                if player_summonerName in player_summonerNames:
                                                    player_index = player_summonerNames.index(player_summonerName)
                                                elif player_summonerName in set(map(str, player_summonerIds)):
                                                    player_index = player_summonerIds.index(int(player_summonerName))
                                                elif player_summonerName in player_puuids:
                                                    player_index = player_puuids.index(player_summonerName)
                                                else:
                                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                                    continue
                                                if not player_index in unblock_indices:
                                                    unblock_indices.append(player_index)
                                                    index_got = True
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    continue
                                if index_got:
                                    break
                                logPrint("请选择您输入要移出聊天黑名单的玩家信息的方式：\nPlease select a method of inputting the information of the blocked players to be unblocked:\n0\t返回上一层（Return to the last step）\n1\t索引（By index）\n2\t召唤师名（By summoner name）")
                        elif mode == "3":
                            unblock_indices = list(range(len(blockList)))
                            index_got = True
                        elif mode == "4":
                            logPrint("是否需要测试玩家信息的获取？（输入任意键以开始打草稿，否则直接开始输入要移出聊天黑名单的玩家信息。）\nDo you want to test obtaining player information? (Submit any non-empty string to make a draft, or null to input the index of the players to unblock directly.)")
                            draft_str = logInput()
                            draft = bool(draft_str)
                            if draft:
                                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                                while True:
                                    draft_option = logInput()
                                    if draft_option == "":
                                        continue
                                    elif draft_option[0] == "0":
                                        break
                                    elif draft_option[0] == "1":
                                        scope = {"get_info_name": get_info_name, "current_info": current_info, "blockList": blockList}
                                        logPrint('示例（Examples）：\nprint(dir()) #输出exec函数使用的作用域中的变量名称（Output names of variables to the scope of `exec` function）\nimport os, pandas, pyperclip #引入需要的库（Introduce required libraries）\nos.system("CLS") #清屏（Clear screen）\ndf = pandas.read_excel("black list.xlsx", sheet_name = "Sheet1") #示例：从工作簿中读取黑名单数据（Example: Read black list data from a workbook）\nblock_puuids = set(df.iloc[:, 2])\nunblock_puuids = []\nfor player_puuid in player_puuids: #确定公示名单中已经解除拉黑的玩家（Determines the unblocked player in the announcement）\n    if not player_puuid in block_puuids:\n        unblock_puuids.append(player_puuid)\npyperclip.copy(str(unblock_puuids)) #将结果复制到全局剪贴板中，用于后续输入黑名单列表（Copy the result to the global clipboard for subsequently inputting the blocked player list）\n输入“-1”以退出测试。\nSubmit "-1" to quit the test.')
                                        subscope(scope)
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出草稿（Quit drafting）\n1\t测试（Test）")
                            unblock_puuids = []
                            unblock_summonerNames = []
                            unblock_indices = []
                            logPrint('请输入要拉黑的玩家名称列表。输入“0”以返回上一层。\nPlease submit a list containing summonerNames of players to unblock. Submit "0" to return to the last step.')
                            while True:
                                unblock_str = logInput()
                                if unblock_str == "":
                                    continue
                                elif unblock_str[0] == "0":
                                    index_got = False
                                    break
                                else:
                                    try:
                                        unblockNames = eval(unblock_str)
                                    except:
                                        traceback_info = traceback.format_exc()
                                        logPrint(traceback_info)
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                    else:
                                        if isinstance(unblockNames, list) and all(map(lambda x: isinstance(x, (int, str)), unblockNames)):
                                            for unblockName in unblockNames:
                                                unblock_info = await get_info(connection, unblockName)
                                                if unblock_info["info_got"]:
                                                    unblock_puuid = unblock_info["body"]["puuid"]
                                                    unblock_summonerName = get_info_name(unblock_info["body"])
                                                    if unblock_puuid == current_info["puuid"]:
                                                        logPrint(f"[{unblockName}]你不在自己的聊天黑名单中。以前不在，以后也不会在。\nYou haven't been and will never be blocked by yourself.")
                                                    elif not unblock_puuid in player_puuids:
                                                        logPrint(f"[{unblockName}]" + "%s不在你的聊天黑名单中。\n%s isn't blocked." %(get_info_name(unblock_info["body"], unblock_info["body"])))
                                                    elif not unblock_puuid in unblock_puuids:
                                                        unblock_puuids.append(unblock_puuid)
                                                        unblock_summonerNames.append(unblock_summonerName)
                                                        unblock_indices.append(player_puuids.index(unblock_puuid))
                                                        index_got = True
                                                else:
                                                    logPrint(f"[{unblockName}]" + unblock_info["message"])
                                            break
                                        else:
                                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        if index_got:
                            unblock_summonerNames = list(map(lambda x: player_summonerNames[x], unblock_indices))
                            logPrint('您确定要将%s移出聊天黑名单吗？（输入“unblock”确认移出，否则不移出。）\nAre you sure you want to unblock %s? (Submit "unblock" to unblock those players, or null to cancel.)' %("、".join(unblock_summonerNames), ", ".join(unblock_summonerNames)))
                            unblock_confirm_str = logInput()
                            unblock_confirm = unblock_confirm_str == "unblock"
                            if unblock_confirm:
                                for player_index in unblock_indices:
                                    unblock_summonerName = player_summonerNames[player_index]
                                    unblock_puuid = player_puuids[player_index]
                                    response = await (await connection.request("DELETE", f"/lol-chat/v1/blocked-players/{unblock_puuid}")).json()
                                    logPrint(response)
                                    if response == None:
                                        logPrint("%s已被移出聊天黑名单。\n%s has been unblocked." %(unblock_summonerName, unblock_summonerName))
                                    else:
                                        if response["httpStatus"] == 400:
                                            logPrint("您未能成功将%s移出聊天黑名单。也许TA已经不在其中了。\nYou failed to unblock %s. Maybe he/she's already out of it." %(unblock_summonerName, unblock_summonerName))
                                        else:
                                            logPrint("您未能成功将%s移出聊天黑名单。\nYou failed to unblock %s." %(unblock_summonerName, unblock_summonerName))
                                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                                if len(blockList) == 0:
                                    logPrint("这里什么都没有。你的聊天黑名单是空的。\nNothing to see here. Your block list is empty.")
                                    break
                                else:
                                    logPrint("聊天黑名单如下：\nBlock list:")
                                    player_summonerNames = list(map(lambda x: x["gameName"] + "#" + x["gameTag"], blockList))
                                    player_summonerIds = list(map(lambda x: x["summonerId"], blockList))
                                    player_puuids = list(map(lambda x: x["puuid"], blockList))
                                    blockList_df = await sort_blockList_data(connection)
                                    blockList_fields_to_print = ["gameName", "gameTag", "puuid", "icon title"]
                                    print(format_df(blockList.loc[:, blockList_fields_to_print])[0])
                                    log.write(format_df(blockList.loc[:, blockList_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                        logPrint("请选择取消拉黑模式：\nPlease select an unblocking mode:\n0\t返回上一层（Return to the last step）\n1\t单个移出（Single）\n2\t批量移出（In batches）\n3\t全部移出（All）\n4\t从文件中移出（From file）")
        elif option[0] == "5":
            #logPrint("警告：该模式会将与自定义无限火力行为无关的黑名单玩家移除。输入任意键以继续，否则退出。\nWarning: This option will unblock the players that are blocked not because of bad Custom URF behaviors. Submit any non-empty string to continue, or null to exit.")
            logPrint("输入任意键以启用自定义无限火力专用黑名单，否则回归到英雄联盟客户端的聊天黑名单。\nSubmit any non-empty string to enable the black list specially designed for Custom URF, or null to return to the normal League of Legends black list.")
            CustomURF_BlockList_enabled_str = logInput()
            if bool(CustomURF_BlockList_enabled_str):
                blockList = await (await connection.request("GET", "/lol-chat/v1/blocked-players")).json()
                blocked_puuids = list(map(lambda x: x["puuid"], blockList))
                if os.path.exists("自定义无限火力玩家行为记录表.xlsx"):
                    fp = "自定义无限火力玩家行为记录表.xlsx"
                else:
                    logPrint("请输入自定义无限火力玩家行为记录表的路径：\nPlease input the path of Custom URF player behavior table:")
                    while True:
                        fp = logInput()
                        if os.path.exists(fp) and fp.endswith(".xlsx"):
                            break
                        elif fp == "0":
                            break
                        else:
                            logPrint(f"没有找到{fp}。请重新输入。\n{fp} not found. Please try again.")
                    if fp == "0":
                        continue
                try:
                    df = pandas.read_excel("自定义无限火力玩家行为记录表.xlsx", sheet_name = "Sheet2")
                    puuids_to_block = []
                    for i in range(len(df)):
                        if not pandas.isnull(df.loc[i, "封禁时间"]) and not pandas.isnull(df.loc[i, "封禁天数"]):
                            if not pandas.isnull(df.loc[i, "封禁时间"]) and not pandas.isnull(df.loc[i, "封禁天数"]) and df.loc[i, "封禁时间"].timestamp() + 86400 * int(df.loc[i, "封禁天数"]) > time.time():
                                if not pandas.isnull(df.loc[i, "玩家通用唯一识别码"]) and not df.loc[i, "玩家通用唯一识别码"] in puuids_to_block:
                                    puuids_to_block.append(df.loc[i, "玩家通用唯一识别码"])
                except:
                    traceback_info = traceback.format_exc()
                    logPrint(traceback_info)
                    logPrint("文件格式错误！请从群文件重新导出到与该脚本同目录的位置，且表格内容不要变动。\nFile format ERROR! Please export the Tencent table to the same directory as this program again. Make sure the table content stays unchanged.")
                else:
                    if len(puuids_to_block) == 0:
                        logPrint("暂无封禁的玩家。\nThere's not any suspended player.")
                    else:
                        blockList_CustomURF = []
                        puuids_found = []
                        summonerNames_to_block = []
                        pid_postfix = current_hovercard["id"].split("@")[1]
                        for puuid in puuids_to_block:
                            player_info = await get_info(connection, puuid)
                            if player_info["info_got"]:
                                player_info_body = player_info["body"]
                                player = {"gameName": player_info_body["gameName"], "gameTag": player_info_body["tagLine"], "icon": player_info_body["profileIconId"], "id": player_info_body["puuid"] + "@" + pid_postfix, "name": "", "pid": player_info_body["puuid"] + "@" + pid_postfix, "puuid": player_info_body["puuid"], "summonerId": player_info_body["summonerId"]}
                                blockList_CustomURF.append(player.copy())
                                puuids_found.append(puuid)
                                summonerNames_to_block.append(get_info_name(player_info_body))
                        if len(blockList_CustomURF) == 0:
                            logPrint("腾讯文档记录了封禁玩家，但是在该服务器上没有查询到这些玩家。请检查您运行的服务器是否正确。\nTencent table does record the suspended players, but the program failed to find these players on this server. Please check if you're running the client on a correct platform.")
                        else:
                            logPrint("目前处于封禁期的玩家：\nCurrently suspended players:")
                            for i in range(len(puuids_found)):
                                logPrint(puuids_found[i] + "\t" + summonerNames_to_block[i])
                            CustomURF_BlockList_enabled = True
                    #以下代码将聊天黑名单与自定义无限火力黑名单同步。现已弃用（The following code synchronize the League of Legends block list with Custom URF block list. They're deserted now）
                    # puuids_to_unblock = []
                    # for player in blockList:
                    #     if not player["puuid"] in blocked_puuids:
                    #         puuids_to_unblock.append(player["puuid"])
                    # summonerNames_to_block = []
                    # if len(puuids_to_block) != 0:
                    #     for puuid in puuids_to_block:
                    #         player_info = await get_info(connection, puuid)
                    #         if player_info["info_got"]:
                    #             summonerNames_to_block.append(get_info_name(player_info["body"]))
                    #     if len(summonerNames_to_block) != 0:
                    #         logPrint('将%s拉入聊天黑名单：\n- 将该玩家从你的好友列表中移除\n- 屏蔽来自该玩家的好友请求\n- 屏蔽任何未来的会话\n- 屏蔽该玩家的游戏邀请\nBlocking %s:\n- Removes them from your friends list\n- Blocks friend requests from them\n- Blocks any future conversations\n- Blocks game invites from them\n\n您确定要将该玩家拉入聊天黑名单吗？（输入“block”以确认，否则取消。）\nDo you really want to block this player? (Submit "block" to confirm, otherwise cancel blocking.' %("、".join(summonerNames_to_block), ", ".join(summonerNames_to_block)))
                    #         block_confirm_str = logInput()
                    #         block_confirm = block_confirm_str == "block"
                    #         if block_confirm:
                    #             for i in range(len(puuids_to_block)):
                    #                 puuid_to_block = puuids_to_block[i]
                    #                 summonerName_to_block = summonerNames_to_block[i]
                    #                 if not puuid_to_block in blocked_puuids:
                    #                     body = {"puuid": puuids_to_block[i]}
                    #                     response = await (await connection.request("POST", "/lol-chat/v1/blocked-players", data = body)).json()
                    #                     logPrint(response)
                    #                     if response == None:
                    #                         logPrint("%s已被拉入聊天黑名单。你再也不会看到TA的在线状态或是收到来自TA的信息了。\n%s has been blocked. You will no longer see them online or receive their messages." %(summonerName_to_block, summonerName_to_block))
                    #                     else:
                    #                         logPrint("您未能成功将%s拉入聊天黑名单。\nYou failed to block %s." %(summonerName_to_block, summonerName_to_block))
                    #                 else:
                    #                     logPrint("%s已经在您的聊天黑名单中。\n%s is already blocked." %(summonerName_to_block, summonerName_to_block))
                    # summonerNames_to_unblock = []
                    # if len(puuids_to_unblock) != 0:
                    #     for puuid in puuids_to_unblock:
                    #         player_info = await get_info(connection, puuid)
                    #         if player_info["info_got"]:
                    #             summonerNames_to_unblock.append(get_info_name(player_info["body"]))
                    #     if len(summonerNames_to_unblock) != 0:
                    #         logPrint('您确定要将%s移出聊天黑名单吗？（输入“unblock”确认移出，否则不移出。）\nAre you sure you want to unblock %s? (Submit "unblock" to unblock those players, or null to cancel.)' %("、".join(summonerNames_to_unblock), ", ".join(summonerNames_to_unblock)))
                    #         unblock_confirm_str = logInput()
                    #         unblock_confirm = unblock_confirm_str == "unblock"
                    #         if unblock_confirm:
                    #             for i in range(len(puuids_to_unblock)):
                    #                 puuid_to_unblock = puuids_to_unblock[i]
                    #                 summonerName_to_unblock = summonerNames_to_unblock[i]
                    #                 body = {"puuid": puuids_to_unblock[i]}
                    #                 response = await (await connection.request("DELETE", f"/lol-chat/v1/blocked-players/{puuid_to_unblock}")).json()
                    #                 logPrint(response)
                    #                 if response == None:
                    #                     logPrint("%s已被移出聊天黑名单。\n%s has been unblocked." %(summonerName_to_unblock, summonerName_to_unblock))
                    #                 else:
                    #                     logPrint("您未能成功将%s移出聊天黑名单。\nYou failed to unblock %s." %(summonerName_to_unblock, summonerName_to_unblock))
            else:
                CustomURF_BlockList_enabled = False

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    while True:
        logPrint("请选择要模拟的行为类型：\nPlease select the type of behaviors to simulate:\n1\t好友（Friends）\n2\t黑名单（Block list）")
        bType = logInput()
        if bType == "" or bType[0] == "1":
            await friend_behavior_simulation(connection)
        elif bType[0] == "2":
            await blacklist_behavior_simulation(connection)
        else:
            break
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
message_hint_printed = False
spectatorPluginNA_hint_printed = False
connector.start()
