from lcu_driver import Connector
import argparse, os, copy, unicodedata, shutil, pandas, requests, time, json, re, traceback, pickle, _io
from urllib.parse import quote, unquote, urljoin
from wcwidth import wcswidth
from collections import OrderedDict
from openpyxl import load_workbook
from openpyxl.styles import Color, numbers, PatternFill
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule, FormulaRule
from openpyxl.utils import get_column_letter
#from flask import Flask, render_template

parser = argparse.ArgumentParser()
parser.add_argument("-r", "--reserve", help = "在对局不包含主玩家的情况下仍然加载该对局（Load a match even if it doesn't contain the main player）", action = "store_true")
parser.add_argument("-rt", "--reserve_text", help = "在对局不包含主玩家的情况下仍然保存该对局（Save a match even if it doesn't contain the main player）", action = "store_true")
args = parser.parse_args()

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

log_folder = "日志（Logs）/Customized Program 05 - Search Summoner Profile"
os.makedirs(log_folder, exist_ok = True)
currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
log = open(os.path.join(log_folder, currentTime + ".log"), "a+", encoding = "utf-8")

error_header = {"errorCode": "异常代码", "httpStatus": "HTTP状态码", "implementationDetails": "细节", "message": "消息"}
error_header_keys = list(error_header.keys())
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
# 搜索召唤师生涯（Search summoner profile）
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

def count_nonASCII(s: str): #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str): #移除一个字符串中的所有C0和C1字符（Remove all C0 and C1 characters from a string）
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc") #该表达式等价于（This expression is equivalent to）`re.sub(r"[\x00-\x1F\x7F-\x9F]", "", s)`

def format_df(df: pandas.DataFrame, width_exceed_ask: bool = True, direct_print: bool = False, print_header: bool = True, print_index: bool = False, reserve_index = False, start_index = 0, header_align: str = "^", align: str = "^", align_replicate_rule: str = "all"): #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
    df = df.copy(deep = True) #深复制，防止原数据框被修改（Deep copy prevents the original dataframe from being changed）
    old_index = df.index #用于存储旧索引。当`reserve_index`为真时，将输出旧索引（Stores the old indices. When `reserve_index` is True, the program outputs the old indices）
    df.index = range(start_index, len(df) + start_index) #新索引允许从`start_index`开始，默认从0开始（New indices allow starting from `start_index`, which is 0 by default）
    maxLens = {} #存储不同列的最大字符串宽度（Stores the max string lengths of different columns）
    maxWidth = shutil.get_terminal_size()[0] #获取当前终端的单行宽度（Get the line width of the current terminal）
    fields = df.columns.tolist()
    for field in fields: #计算每一列的最大字符串宽度（Calculate the max string length of each column）
        maxLens[field] = max(0 if len(df) == 0 else max(map(lambda x: wcswidth(rm_ctrl_char(str(x))), df[field])), wcswidth(rm_ctrl_char(field))) + 2
    index_len = 0 if len(df) == 0 else max(map(lambda x: len(str(x)), old_index)) if reserve_index else max(len(str(start_index)), len(str(start_index + len(df) - 1))) #计算索引列的最大字符串宽度（Calculate the max string length of the index column）
    if sum(maxLens.values()) + 2 * (len(fields) - 1) > maxWidth or print_index and index_len + sum(maxLens.values()) + 2 * len(fields) > maxWidth: #字符串宽度和超出终端窗口宽度的情形（The case where the sum of the string lengths exceeds the terminal size）
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
    result = "" #结果字符串初始化（Initialize the result string）
    #确定各列的排列方向（Determine the alignments of all columns）
    if isinstance(header_align, str) and isinstance(align, str): #确保排列方向参数无误（Ensure the alignment parameters are valid）
        if not all(map(lambda x: x in {"<", "^", ">"}, header_align)) or not all(map(lambda x: x in {"<", "^", ">"}, align)):
            print('排列方式字符串参数错误！排列方式必须是“<”“^”或者“>”中的一个。请修改排列方式字符串参数。\nParameter ERROR of the alignment string! The alignment value must be one of {"<", "^", ">"}. Please change the alignment string parameter.')
        if len(header_align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            header_alignments = ["^"] * df.shape[1]
        elif len(header_align) == 1:
            header_alignments = [header_align] * df.shape[1]
        else:
            header_alignments_tmp = list(header_align)
            if len(header_align) < df.shape[1]: #表头排列规则字符串长度小于数据框列数时，通过排列方式列表补充规则进行补充（When the length of `header_align` is less than the number of the dataframe's columns, supplement the rest of the rules according to `align_replicate_rule`）
                if align_replicate_rule == "last": #仅重复最后一列的排列方式（Only replicate the alignment of the last column）
                    header_alignments = header_alignments_tmp + [header_alignments_tmp[-1]] * len(df.shape[1] - len(header_align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    header_alignments = header_alignments_tmp * (df.shape[1] // len(header_align)) + header_alignments_tmp[:df.shape[1] % len(header_align)] #所有排列方式循环补充（Supplement the alignments in a cycle of the whole `header_alignment` string）
            else: #表头排列规则字符串大于等于数据框列数时，取长度等于数据框列数的字符串开头切片（When the length of `header_align` is greater than or equal to the number of the dataframe's columns, get the slice at the beginning of `header_align` whose length equal to the number of the dataframe's columns）
                header_alignments = header_alignments_tmp[:df.shape[1]]
        if len(align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            alignments = ["^"] * df.shape[1]
        elif len(align) == 1:
            alignments = [align] * df.shape[1]
        else:
            alignments_tmp = list(align)
            if len(align) < df.shape[1]: #数据排列规则字符串长度小于数据框列数时，通过排列方式列表补充规则进行补充（When the length of `align` is less than the number of the dataframe's columns, supplement the rest of the rules according to `align_replicate_rule`）
                if align_replicate_rule == "last": #仅重复最后一列的排列方式（Only replicate the alignment of the last column）
                    alignments = alignments_tmp + [alignments_tmp[-1]] * len(df.shape[1] - len(align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    alignments = alignments_tmp * (df.shape[1] // len(align)) + alignments_tmp[:df.shape[1] % len(align)]
            else: #数据排列规则字符串大于等于数据框列数时，取长度等于数据框列数的字符串开头切片（When the length of `align` is greater than or equal to the number of the dataframe's columns, get the slice at the beginning of `header_align` whose length equal to the number of the dataframe's columns）
                alignments = alignments_tmp[:df.shape[1]]
        if print_header: #打印表头（Prints the header）
            if print_index: #打印表头时，如果输出索引，由于表头没有索引，所以用空格代替（Spaces will be printed as the index part of the header）
                result += " " * (index_len + 2)
            for i in range(df.shape[1]):
                field = fields[i]
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(field), align = header_alignments[i], w = maxLens[field] - count_nonASCII(field))
                result += tmp
                #print(tmp, end = "")
                if i != df.shape[1] - 1: #未到行尾时，用两个空格来分割该列和下一列（When the program doesn't reach the end of the line, separate this column and the next column by two spaces）
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
                if j != df.shape[1] - 1: #未到行尾时，用两个空格来分割该列和下一列（When the program doesn't reach the end of the line, separate this column and the next column by two spaces）
                    result += "  "
                    #print("  ", end = "")
            if i != df.shape[0] - 1:
                result += "\n"
            #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the above line）
            index += 1
    else:
        print("排列方式参数错误！请传入字符串。\nAlignment parameter ERROR! Please pass a string instead.")
    return (result, maxLens)

def lcuTimestamp(timestamp): #根据对局时间轴的时间戳返回对局时间（Return the time according to the timestamp in match timeline）
    min = timestamp // 60
    sec = timestamp % 60
    return str(min) + ":" + "{0:0>2}".format(str(sec))

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

def FindPostPatch(patch, patchList): #二分查找某个版本号在DataDragon数据库的后一个版本（Binary search for the precedent patch of a given patch in the patch list archived in DataDragon database）
    leftIndex, rightIndex = 0, len(patchList) - 1
    mid = (leftIndex + rightIndex) // 2
    count = 0 #函数调试阶段的保护机制（A protecion mechanism during rebugging this function）
    #print("[" + str(count) + "]", leftIndex, mid, rightIndex)
    while leftIndex < rightIndex:
        count += 1
        if patch_compare(patch, patchList[mid]):
            leftIndex = mid + 1
            mid = (leftIndex + rightIndex) // 2
        elif patch_compare(patchList[mid], patch):
            rightIndex = mid
            mid = (leftIndex + rightIndex) // 2
        else:
            return patchList[mid - 1]
        #print("[" + str(count) + "]", leftIndex, mid, rightIndex)
        if count >= 15:
            print("程序即将进入死循环！请检查算法！\nThe program is stepping into a dead loop! Please check the algorithm!")
            return 1
    if mid >= 1:
        return patchList[mid - 1]
    else:
        print("该版本为美测服最新版本，暂未收录在DataDragon数据库中。\nThis version is the latest version on PBE and isn't archived in DataDragon database for now.")
        return "pbe"

def patch_sort(patchList: list): #利用插入排序算法，根据patch_compare函数对版本列表进行升序排列（Sorts a patch list according to the principle of `patch_compare` function through the insertion sort algorithm）
    bigPatch_re = re.compile("[0-9]*.[0-9]*")
    if all(map(lambda x: isinstance(x, str), patchList)) and all(map(lambda x: bigPatch_re.search(x), patchList)): #此处放款了参数的格式限制：只要列表的每个元素都是包含版本字符串的字符串即可（Here the function relaxes the limit for the format of the parameter: any list whose elements are all strings that contain a patch string is OK）
        patchList = list(map(lambda x: bigPatch_re.search(x).group(), patchList))
        for i in range(1, len(patchList)):
            tmp = patchList[i] #将第i个元素临时存储（Temporarily stores the i-th element of `patchList`）
            j = i - 1
            while j >= 0 and patch_compare(tmp, patchList[j]): #如果检测到第i个元素比第(j = i - 1)个元素小，就要逐渐减小j，直到找到一个j，使得第j个元素小于第i个元素，此时第j + 1个元素仍然大于第i个铁元素。把j + 1及以后的元素右移，空出的位置再插入第i个元素（1f an i-th element is detected to be less than the j-th element, namely the (i - 1)th element, then the program decrements j until it finds a j such that the j-th element is less than the i-th element, while the (j + 1)-th element is still greater than the i-the element. Then, shift all elements between the current j-th and i-th elements and insert the i-th elements into the empty space）
                patchList[j + 1] = patchList[j]
                j -= 1
            patchList[j + 1] = tmp
    else:
        print("您的版本列表格式有误！\nYour patch list is not correctly formatted!")
    return patchList

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

def format_runtime(seconds: int):
    units = [(" d", 86400), (" h", 3600), (" m", 60), (" s", 1)]
    result = []
    for unit_name, unit_seconds in units:
        if seconds >= unit_seconds:
            unit_value = round(seconds // unit_seconds)
            seconds %= unit_seconds
            result.append(f"{unit_value}{unit_name}")
    
    return " ".join(result) if result else "0"

def write_roman(num): #此部分代码来自Stack Overflow（The following code come from https://stackoverflow.com/questions/28777219/basic-program-to-convert-integer-to-roman-numerals）
    roman = OrderedDict()
    roman[1000] = "M"
    roman[900] = "CM"
    roman[500] = "D"
    roman[400] = "CD"
    roman[100] = "C"
    roman[90] = "XC"
    roman[50] = "L"
    roman[40] = "XL"
    roman[10] = "X"
    roman[9] = "IX"
    roman[5] = "V"
    roman[4] = "IV"
    roman[1] = "I"

    def roman_num(num):
        for r in roman.keys():
            x, y = divmod(num, r)
            yield roman[r] * x
            num -= (r * x)
            if num <= 0:
                break

    return "".join([a for a in roman_num(num)])

async def search_profile(connection):
    # logPrint("是否将部分数据框用于网页展示？（输入任意键展示，否则不生成网页）\nDo you want to display some dataframes in a webpage? (Input anything to display them in a web, or null to skip generating the web.)")
    # web_display = logInput()
    # if bool(web_display):
    #     app = Flask()
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    logPrint("请选择召唤师技能和装备的输出语言【默认为中文（中国）】：\nPlease select a language to output the summoner spells and items (the default option is zh_CN):") #本来考虑把可用CDragon数据版本放在第三列，但是后来发现表头名字太长了，索性放在最后了（I had considered putting "Applicable CDragon Data Patches" at the third column, but then found the header was too long. So I put it at the last column）
    language_ddragon = {1: {"CODE": "ar_AE", "LANGUAGE (EN)": "Arabic (United Arab Emirates)", "LANGUAGE (ZH)": "阿拉伯语（阿拉伯联合酋长国）", "Applicable CDragon Data Patches": "9.20～10.1, 13.20+"}, 2: {"CODE": "cs_CZ", "LANGUAGE (EN)": "Czech (Czech Republic)", "LANGUAGE (ZH)": "捷克语（捷克共和国）", "Applicable CDragon Data Patches": "7.1+"}, 3: {"CODE": "el_GR", "LANGUAGE (EN)": "Greek (Greece)", "LANGUAGE (ZH)": "希腊语（希腊）", "Applicable CDragon Data Patches": "9.1+"}, 4: {"CODE": "pl_PL", "LANGUAGE (EN)": "Polish (Poland)", "LANGUAGE (ZH)": "波兰语（波兰）", "Applicable CDragon Data Patches": "9.1+"}, 5: {"CODE": "ro_RO", "LANGUAGE (EN)": "Romanian (Romania)", "LANGUAGE (ZH)": "罗马尼亚语（罗马尼亚）", "Applicable CDragon Data Patches": "9.1+"}, 6: {"CODE": "hu_HU", "LANGUAGE (EN)": "Hungarian (Hungary)", "LANGUAGE (ZH)": "匈牙利语（匈牙利）", "Applicable CDragon Data Patches": "9.1+"}, 7: {"CODE": "en_GB", "LANGUAGE (EN)": "English (United Kingdom)", "LANGUAGE (ZH)": "英语（英国）", "Applicable CDragon Data Patches": "9.1+"}, 8: {"CODE": "de_DE", "LANGUAGE (EN)": "German (Germany)", "LANGUAGE (ZH)": "德语（德国）", "Applicable CDragon Data Patches": "7.1+"}, 9: {"CODE": "es_ES", "LANGUAGE (EN)": "Spanish (Spain)", "LANGUAGE (ZH)": "西班牙语（西班牙）", "Applicable CDragon Data Patches": "9.1+"}, 10: {"CODE": "it_IT", "LANGUAGE (EN)": "Italian (Italy)", "LANGUAGE (ZH)": "意大利语（意大利）", "Applicable CDragon Data Patches": "9.1+"}, 11: {"CODE": "fr_FR", "LANGUAGE (EN)": "French (France)", "LANGUAGE (ZH)": "法语（法国）", "Applicable CDragon Data Patches": "9.1+"}, 12: {"CODE": "ja_JP", "LANGUAGE (EN)": "Japanese (Japan)", "LANGUAGE (ZH)": "日语（日本）", "Applicable CDragon Data Patches": "9.1+"}, 13: {"CODE": "ko_KR", "LANGUAGE (EN)": "Korean (Korea)", "LANGUAGE (ZH)": "朝鲜语（韩国）", "Applicable CDragon Data Patches": "9.7+"}, 14: {"CODE": "es_MX", "LANGUAGE (EN)": "Spanish (Mexico)", "LANGUAGE (ZH)": "西班牙语（墨西哥）", "Applicable CDragon Data Patches": "9.1+"}, 15: {"CODE": "es_AR", "LANGUAGE (EN)": "Spanish (Argentina)", "LANGUAGE (ZH)": "西班牙语（阿根廷）", "Applicable CDragon Data Patches": "9.7+"}, 16: {"CODE": "pt_BR", "LANGUAGE (EN)": "Portuguese (Brazil)", "LANGUAGE (ZH)": "葡萄牙语（巴西）", "Applicable CDragon Data Patches": "9.1+"}, 17: {"CODE": "en_US", "LANGUAGE (EN)": "English (United States)", "LANGUAGE (ZH)": "英语（美国）", "Applicable CDragon Data Patches": "9.1+"}, 18: {"CODE": "en_AU", "LANGUAGE (EN)": "English (Australia)", "LANGUAGE (ZH)": "英语（澳大利亚）", "Applicable CDragon Data Patches": "9.1+"}, 19: {"CODE": "ru_RU", "LANGUAGE (EN)": "Russian (Russia)", "LANGUAGE (ZH)": "俄语（俄罗斯）", "Applicable CDragon Data Patches": "9.1+"}, 20: {"CODE": "tr_TR", "LANGUAGE (EN)": "Turkish (Turkey)", "LANGUAGE (ZH)": "土耳其语（土耳其）", "Applicable CDragon Data Patches": "9.1+"}, 21: {"CODE": "ms_MY", "LANGUAGE (EN)": "Malay (Malaysia)", "LANGUAGE (ZH)": "马来语（马来西亚）", "Applicable CDragon Data Patches": ""}, 22: {"CODE": "en_PH", "LANGUAGE (EN)": "English (Republic of the Philippines)", "LANGUAGE (ZH)": "英语（菲律宾共和国）", "Applicable CDragon Data Patches": "10.5+"}, 23: {"CODE": "en_SG", "LANGUAGE (EN)": "English (Singapore)", "LANGUAGE (ZH)": "英语（新加坡）", "Applicable CDragon Data Patches": "10.5+"}, 24: {"CODE": "th_TH", "LANGUAGE (EN)": "Thai (Thailand)", "LANGUAGE (ZH)": "泰语（泰国）", "Applicable CDragon Data Patches": "9.7+"}, 25: {"CODE": "vn_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "9.7～13.9"}, 26: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "12.17+"}, 27: {"CODE": "id_ID", "LANGUAGE (EN)": "Indonesian (Indonesia)", "LANGUAGE (ZH)": "印度尼西亚语（印度尼西亚）", "Applicable CDragon Data Patches": ""}, 28: {"CODE": "zh_MY", "LANGUAGE (EN)": "Chinese (Malaysia)", "LANGUAGE (ZH)": "中文（马来西亚）", "Applicable CDragon Data Patches": "10.5+"}, 29: {"CODE": "zh_CN", "LANGUAGE (EN)": "Chinese (China)", "LANGUAGE (ZH)": "中文（中国）", "Applicable CDragon Data Patches": "9.7+"}, 30: {"CODE": "zh_TW", "LANGUAGE (EN)": "Chinese (Taiwan)", "LANGUAGE (ZH)": "中文（台湾）", "Applicable CDragon Data Patches": "9.7+"}}
    language_cdragon = {}
    for i in language_ddragon:
        if language_ddragon[i]["CODE"] == "en_US":
            language_cdragon[language_ddragon[i]["CODE"]] = "default" #在CommunityDragon数据库上，美服正式服的数据资源代码是default，而不是小写的en_US（The code for English (US) data resources on CommunityDragon database is "default" instead of the lowercase of "en_US"）
        else:
            language_cdragon[language_ddragon[i]["CODE"]] = language_ddragon[i]["CODE"].lower()
    language_dict = {"No.": list(language_ddragon.keys()), "CODE": list(map(lambda x: x["CODE"], language_ddragon.values())), "LANGUAGE": list(map(lambda x: x["LANGUAGE (EN)"], language_ddragon.values())), "语言": list(map(lambda x: x["LANGUAGE (ZH)"], language_ddragon.values())), "Applicable CDragon Data Patches": list(map(lambda x: x["Applicable CDragon Data Patches"], language_ddragon.values()))}
    language_df = pandas.DataFrame(language_dict)
    print(format_df(language_df)[0])
    log.write(format_df(language_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
    while True:
        language_option = logInput()
        if language_option == "" or language_option in [str(i) for i in range(1, 31)]:
            if language_option == "":
                language_option = "29"
            language_code = language_ddragon[int(language_option)]["CODE"]
            #下面声明一些数据资源的地址（The following code declare some data resources' URLs）
            URLPatch = "pbe" if platformId == "PBE1" or platformId == "PBE" else "latest"
            patches_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            spell_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(URLPatch, language_cdragon[language_code]) #CommunityDragon数据库只存储第7赛季及以后的数据（CommunityDragon database only stores data including and after Season 7）
            LoLChampion_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(URLPatch, language_cdragon[language_code])
            LoLItem_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(URLPatch, language_cdragon[language_code])
            summonerIcon_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(URLPatch, language_cdragon[language_code])
            perk_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(URLPatch, language_cdragon[language_code])
            perkstyle_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(URLPatch, language_cdragon[language_code])
            TFT_url = "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(URLPatch, language_code.lower())
            TFTChampion_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(URLPatch, language_cdragon[language_code])
            TFTItem_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(URLPatch, language_cdragon[language_code])
            TFTCompanion_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(URLPatch, language_cdragon[language_code])
            TFTTrait_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(URLPatch, language_cdragon[language_code])
            CherryAugment_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(URLPatch, language_cdragon[language_code])
            #下面声明离线数据资源的默认地址（The following code declare the default paths of offline data resources）
            patches_local_default = "离线数据（Offline Data）\\versions.json"
            spell_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\summoner-spells.json" %(URLPatch, language_cdragon[language_code])
            LoLChampion_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\champion-summary.json" %(URLPatch, language_cdragon[language_code])
            LoLItem_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\items.json" %(URLPatch, language_cdragon[language_code])
            summonerIcon_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\summoner-icons.json" %(URLPatch, language_cdragon[language_code])
            perk_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\perks.json" %(URLPatch, language_cdragon[language_code])
            perkstyle_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\perkstyles.json" %(URLPatch, language_cdragon[language_code])
            TFT_local_default = "离线数据（Offline Data）\\cdragon\\%s\\cdragon\\tft\\%s.json" %(URLPatch, language_code.lower())
            TFTChampion_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftchampions.json" %(URLPatch, language_cdragon[language_code])
            TFTItem_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tftitems.json" %(URLPatch, language_cdragon[language_code])
            TFTCompanion_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\companions.json" %(URLPatch, language_cdragon[language_code])
            TFTTrait_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\tfttraits.json" %(URLPatch, language_cdragon[language_code])
            CherryAugment_local_default = "离线数据（Offline Data）\\cdragon\\%s\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\cherry-augments.json" %(URLPatch, language_code.lower())
            logPrint("请选择数据资源获取模式：\nPlease select the data resource capture mode:\n1\t在线模式（Online）\n2\t离线模式（Offline）")
            prepareMode = logInput()
            switch_language = False
            while True:
                if prepareMode != "" and prepareMode[0] == "1":
                    switch_prepare_mode = False
                    #下面获取版本信息（The following code get the patch data）
                    try:
                        patches_initial = requests.get(patches_url).json()
                    except requests.exceptions.RequestException:
                        logPrint('版本信息获取超时！正在尝试离线加载数据……\nPatch information capture timeout! Trying loading offline data ...\n请输入版本Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the patch Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(patches_local_default, patches_local_default))
                        while True:
                            patches_local = logInput()
                            if patches_local == "":
                                patches_local = patches_local_default
                            elif patches_local[0] == "0":
                                logPrint("版本信息获取失败！请检查系统网络状况和代理设置。\nPatch information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(patches_local, "r", encoding = "utf-8") as fp:
                                    patches_initial = json.load(fp)
                                if isinstance(patches_initial, list) and patches_initial[-1] == "lolpatch_3.7":
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合DataDragon数据库中记录的版本数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the patch data archived in DataDragon database (%s)!" %(patches_url, patches_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的版本Json数据文件路径！\nFile "%s" NOT found! Please input a correct patch Json data file path!' %(patches_local, patches_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有版本信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with patch information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合DataDragon数据库中记录的版本数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the patch data archived in DataDragon database (%s)!" %(patches_url, patches_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    latest_patch = patches_initial[0]
                    patches_dict = {}
                    smallPatches = []
                    bigPatches = []
                    for patch in patches_initial:
                        if not patch.startswith("lolpatch"):
                            patch_split = patch.split(".")
                            smallPatch = ".".join(patch_split[:3])
                            smallPatches.append(smallPatch)
                            bigPatch = ".".join(patch_split[:2])
                            bigPatches.append(bigPatch)
                            patches_dict[bigPatch] = []
                    for i in range(len(bigPatches)):
                        patches_dict[bigPatches[i]].append(smallPatches[i])
                    #下面获取召唤师技能数据（The following code get summoner spell data）
                    try:
                        logPrint("正在加载召唤师技能信息……\nLoading summoner spell information from CommunityDragon...")
                        spell_initial = requests.get(spell_url) #spell存储召唤师技能信息（Variable `spell_initial` stores summoner spell information）
                        if spell_initial.ok:
                            spell_initial = spell_initial.json()
                        else:
                            logPrint(spell_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('召唤师技能信息获取超时！正在尝试离线加载数据……\nSummoner spell information capture timeout! Trying loading offline data ...\n请输入召唤师技能Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the summoner spell Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(spell_local_default, spell_local_default))
                        while True:
                            spell_local = logInput()
                            if spell_local == "":
                                spell_local = spell_local_default
                            elif spell_local[0] == "0":
                                logPrint("召唤师技能信息获取失败！请检查系统网络状况和代理设置。\nSummoner spell information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(spell_local, "r", encoding = "utf-8") as fp:
                                    spell_initial = json.load(fp)
                                if isinstance(spell_initial, list) and all(i in spell_initial[j] for i in ["id", "name", "description", "summonerLevel", "cooldown", "gameModes", "iconPath"] for j in range(len(spell_initial))):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师技能数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner spell data archived in CommunityDragon database (%s)!" %(spell_url, spell_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的召唤师技能Json数据文件路径！\nFile "%s" NOT found! Please input a correct summoner spell Json data file path!' %(spell_local, spell_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有召唤师技能信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with summoner spell information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师技能数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner spell data archived in CommunityDragon database (%s)!" %(spell_url, spell_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取英雄信息（The following code get LoL champion data）
                    try:
                        logPrint("正在加载英雄信息……\nLoading LoL champion information from CommunityDragon...")
                        LoLChampion_initial = requests.get(LoLChampion_url) #LoLItem存储英雄信息。（Variable `LoLChampion_initial` stores information of LoL champions）
                        if LoLChampion_initial.ok:
                            LoLChampion_initial = LoLChampion_initial.json()
                        else:
                            logPrint(LoLChampion_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('英雄信息获取超时！正在尝试离线加载数据……\nLoL champion information capture timeout! Trying loading offline data ...\n请输入英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the LoL champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(LoLChampion_local_default, LoLChampion_local_default))
                        while True:
                            LoLChampion_local = logInput()
                            if LoLChampion_local == "":
                                LoLChampion_local = LoLChampion_local_default
                            elif LoLChampion_local[0] == "0":
                                logPrint("英雄信息获取失败！请检查系统网络状况和代理设置。\nLoL champion information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(LoLChampion_local, "r", encoding = "utf-8") as fp:
                                    LoLChampion_initial = json.load(fp)
                                if isinstance(LoLChampion_initial, list) and all(isinstance(LoLChampion_initial[i], dict) for i in range(len(LoLChampion_initial))) and all(j in LoLChampion_initial[i] for i in range(len(LoLChampion_initial)) for j in ["id", "name", "alias", "squarePortraitPath", "roles"]) and all(isinstance(LoLChampion_initial[i]["id"], int) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["name"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["alias"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["squarePortraitPath"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["roles"], list) for i in range(len(LoLChampion_initial))):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL champion data archived in CommunityDragon database (%s)!" %(LoLChampion_url, LoLChampion_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的英雄Json数据文件路径！\nFile "%s" NOT found! Please input a correct LoL champion Json data file path!' %(LoLChampion_local, LoLChampion_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with LoL champion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL champion data archived in CommunityDragon database (%s)!" %(LoLChampion_url, LoLChampion_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取英雄联盟装备信息（The following code get LoL item data）
                    try:
                        logPrint("正在加载英雄联盟装备信息……\nLoading LoL item information from CommunityDragon...")
                        LoLItem_initial = requests.get(LoLItem_url) #LoLItem存储经典模式的装备信息。（Variable `LoLItem_initial` stores information of LoL items）
                        if LoLItem_initial.ok:
                            LoLItem_initial = LoLItem_initial.json()
                        else:
                            logPrint(LoLItem_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('英雄联盟装备信息获取超时！正在尝试离线加载数据……\nLoL item information capture timeout! Trying loading offline data ...\n请输入英雄联盟装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the LoL item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(LoLItem_local_default, LoLItem_local_default))
                        while True:
                            LoLItem_local = logInput()
                            if LoLItem_local == "":
                                LoLItem_local = LoLItem_local_default
                            elif LoLItem_local[0] == "0":
                                logPrint("英雄联盟装备信息获取失败！请检查系统网络状况和代理设置。\nLoL item information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(LoLItem_local, "r", encoding = "utf-8") as fp:
                                    LoLItem_initial = json.load(fp)
                                if isinstance(LoLItem_initial, list) and all(i in LoLItem_initial[j] for i in ["id", "name", "description", "active", "inStore", "from", "to", "categories", "maxStacks", "requiredChampion", "requiredAlly", "requiredBuffCurrencyName", "requiredBuffCurrencyCost", "specialRecipe", "isEnchantment", "price", "priceTotal", "iconPath"] for j in range(len(LoLItem_initial))):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄联盟装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL item data archived in CommunityDragon database (%s)!" %(LoLItem_url, LoLItem_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的英雄联盟装备Json数据文件路径！\nFile "%s" NOT found! Please input a correct LoL item Json data file path!' %(LoLItem_local, LoLItem_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有英雄联盟装备信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with LoL item information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄联盟装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL item data archived in CommunityDragon database (%s)!" %(LoLItem_url, LoLItem_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取召唤师图标信息（The following code get summoner icon data）
                    try:
                        logPrint("正在加载召唤师图标信息……\nLoading summoner icon information from CommunityDragon...")
                        summonerIcon_initial = requests.get(summonerIcon_url) #LoLItem存储召唤师图标信息。（Variable `summonerIcon_initial` stores information of summoner icons）
                        if summonerIcon_initial.ok:
                            summonerIcon_initial = summonerIcon_initial.json()
                        else:
                            logPrint(summonerIcon_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('召唤师图标信息获取超时！正在尝试离线加载数据……\nSummoner icon information capture timeout! Trying loading offline data ...\n请输入召唤师图标Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the summoner icon Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(summonerIcon_local_default, summonerIcon_local_default))
                        while True:
                            summonerIcon_local = logInput()
                            if summonerIcon_local == "":
                                summonerIcon_local = summonerIcon_local_default
                            elif summonerIcon_local[0] == "0":
                                logPrint("召唤师图标信息获取失败！请检查系统网络状况和代理设置。\nSummoner icon information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(summonerIcon_local, "r", encoding = "utf-8") as fp:
                                    summonerIcon_initial = json.load(fp)
                                if isinstance(summonerIcon_initial, list) and all(map(lambda x: isinstance(x, dict), summonerIcon_initial)) and all(i in j for i in ["id", "title", "yearReleased", "isLegacy", "descriptions", "rarities", "disabledRegions"] for j in summonerIcon_initial):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师图标数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner icon data archived in CommunityDragon database (%s)!" %(summonerIcon_url, summonerIcon_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的召唤师图标Json数据文件路径！\nFile "%s" NOT found! Please input a correct summoner icon Json data file path!' %(summonerIcon_local, summonerIcon_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有召唤师图标信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with summoner icon information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师图标数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner icon data archived in CommunityDragon database (%s)!" %(summonerIcon_url, summonerIcon_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取基石符文信息（The following code get perk data）
                    try:
                        logPrint("正在加载基石符文信息……\nLoading perk information from CommunityDragon...")
                        perk_initial = requests.get(perk_url) #perk存储基石符文信息。（Variable `perk_initial` stores information of perks）
                        if perk_initial.ok:
                            perk_initial = perk_initial.json()
                        else:
                            logPrint(perk_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('基石符文信息获取超时！正在尝试离线加载数据……\nPerk information capture timeout! Trying loading offline data ...\n请输入基石符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perk Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(perk_local_default, perk_local_default))
                        while True:
                            perk_local = logInput()
                            if perk_local == "":
                                perk_local = perk_local_default
                            elif perk_local[0] == "0":
                                logPrint("基石符文信息获取失败！请检查系统网络状况和代理设置。\nPerk information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(perk_local, "r", encoding = "utf-8") as fp:
                                    perk_initial = json.load(fp)
                                if isinstance(perk_initial, list) and all(i in perk_initial[j] for i in ["id", "name", "majorChangePatchVersion", "tooltip", "shortDesc", "longDesc", "recommendationDescriptor", "iconPath", "endOfGameStatDescs", "recommendationDescriptorAttributes"] for j in range(len(perk_initial))):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的基石符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perk data archived in CommunityDragon database (%s)!" %(perk_url, perk_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的基石符文Json数据文件路径！\nFile "%s" NOT found! Please input a correct perk Json data file path!' %(perk_local, perk_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有基石符文信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with perk information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的基石符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perk data archived in CommunityDragon database (%s)!" %(perk_url, perk_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取符文系信息（The following code get perkstyle data）
                    try:
                        logPrint("正在加载符文系信息……\nLoading perkstyle information from CommunityDragon...")
                        perkstyle_initial = requests.get(perkstyle_url) #perkstyle存储符文系信息。（Variable `perkstyle_initial` stores information of perkstyles）
                        if perkstyle_initial.ok:
                            perkstyle_initial = perkstyle_initial.json()
                        else:
                            logPrint(perkstyle_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('符文系信息获取超时！正在尝试离线加载数据……\nPerkstyle information capture timeout! Trying loading offline data ...\n请输入符文系Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perkstyle Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(perkstyle_local_default, perkstyle_local_default))
                        while True:
                            perkstyle_local = logInput()
                            if perkstyle_local == "":
                                perkstyle_local = perkstyle_local_default
                            elif perkstyle_local[0] == "0":
                                logPrint("符文系信息获取失败！请检查系统网络状况和代理设置。\nperkstyle information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(perkstyle_local, "r", encoding = "utf-8") as fp:
                                    perkstyle_initial = json.load(fp)
                                if isinstance(perkstyle_initial, dict) and all(perkstyle_initial.get(i, 0) for i in ["schemaVersion", "styles"]) and isinstance(perkstyle_initial["styles"], list) and all(j in perkstyle_initial["styles"][i] for i in range(len(perkstyle_initial["styles"])) for j in ["id", "name", "tooltip", "iconPath", "assetMap", "isAdvanced", "allowedSubStyles", "subStyleBonus", "slots", "defaultPageName", "defaultSubStyle", "defaultPerks", "defaultPerksWhenSplashed", "defaultStatModsPerSubStyle"]):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的符文系数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perkstyle data archived in CommunityDragon database (%s)!" %(perkstyle_url, perkstyle_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的符文系Json数据文件路径！\nFile "%s" NOT found! Please input a correct perkstyle Json data file path!' %(perkstyle_local, perkstyle_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有符文系信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with perkstyle information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的符文系数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perkstyle data archived in CommunityDragon database (%s)!" %(perkstyle_url, perkstyle_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取云顶之弈强化符文数据（The following code get TFT augment data）
                    try:
                        logPrint("正在加载云顶之弈基础数据……\nLoading TFT basic data from CommunityDragon ...")
                        TFT_initial = requests.get(TFT_url) #TFT存储云顶之弈中至今为止所有的强化符文、英雄和羁绊信息和各赛季的英雄和羁绊信息（Variable `TFT_initial` stores information of all augments, champions and traits so far and information of champions and traits with respect to season）
                        if TFT_initial.ok:
                            TFT_initial = TFT_initial.json()
                        else:
                            logPrint(TFT_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('云顶之弈基础信息获取超时！正在尝试离线加载数据……\nTFT basic information capture timeout! Trying loading offline data ...\n请输入云顶之弈基础数据Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT basics Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFT_local_default, TFT_local_default))
                        while True:
                            TFT_local = logInput()
                            if TFT_local == "":
                                TFT_local = TFT_local_default
                            elif TFT_local[0] == "0":
                                logPrint("云顶之弈基础信息获取失败！请检查系统网络状况和代理设置。\nTFT basic information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(TFT_local, "r", encoding = "utf-8") as fp:
                                    TFT_initial = json.load(fp)
                                if isinstance(TFT_initial, dict) and all(i in TFT_initial for i in ["items", "setData", "sets"]) and all(isinstance(TFT_initial[i], list) for i in ["items", "setData"]) and all(isinstance(TFT_initial[i], dict) for i in ["sets"]) and all(j in TFT_initial["items"][i] for i in range(len(TFT_initial["items"])) for j in ["apiName", "associatedTraits", "composition", "desc", "effects", "from", "icon", "id", "incompatibleTraits", "name", "tags", "unique"]) and all(isinstance(TFT_initial["items"][i][j], str) or TFT_initial["items"][i][j] == None for i in range(len(TFT_initial["items"])) for j in ["apiName", "desc", "icon", "name"]) and all(isinstance(TFT_initial["items"][i][j], list) for i in range(len(TFT_initial["items"])) for j in ["associatedTraits", "composition", "tags"]) and all(isinstance(TFT_initial["items"][i][j], dict) for i in range(len(TFT_initial["items"])) for j in ["effects"]) and all(isinstance(TFT_initial["items"][i][j], bool) for i in range(len(TFT_initial["items"])) for j in ["unique"]) and all(j in TFT_initial["setData"][i] for i in range(len(TFT_initial["setData"])) for j in ["augments", "champions", "items", "mutator", "name", "number", "traits"]) and all(isinstance(TFT_initial["setData"][i][j], list) for i in range(len(TFT_initial["setData"])) for j in ["augments", "champions", "items", "traits"]) and all(isinstance(TFT_initial["setData"][i][j], str) for i in range(len(TFT_initial["setData"])) for j in ["mutator", "name"]) and all(isinstance(TFT_initial["setData"][i][j], int) for i in range(len(TFT_initial["setData"])) for j in ["number"]) and all(map(lambda x: isinstance(x, str), TFT_initial["setData"][i][j]) for i in range(len(TFT_initial["setData"])) for j in ["augments", "items"]) and all(map(lambda x: isinstance(x, dict), TFT_initial["setData"][i]["champions"]) for i in range(len(TFT_initial["setData"]))) and all(k in TFT_initial["setData"][i]["champions"][j] for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in ["ability", "apiName", "characterName", "cost", "icon", "name", "role", "squareIcon", "stats", "tileIcon", "traits"]) and all(isinstance(TFT_initial["setData"][i]["champions"][j][k], dict) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in ["ability", "stats"]) and all(isinstance(TFT_initial["setData"][i]["champions"][j][k], str) or TFT_initial["setData"][i]["champions"][j][k] == None for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in ["apiName", "characterName", "icon", "name", "squareIcon", "tileIcon"]) and all(isinstance(TFT_initial["setData"][i]["champions"][j][k], int) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in ["cost"]) and all(k in TFT_initial["setData"][i]["champions"][j]["ability"] for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in ["desc", "icon", "name", "variables"]) and all(isinstance(TFT_initial["setData"][i]["champions"][j]["ability"][k], str) or TFT_initial["setData"][i]["champions"][j]["ability"][k] == None for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in ["desc", "icon", "name"]) and all(isinstance(TFT_initial["setData"][i]["champions"][j]["ability"][k], list) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in ["variables"]) and all(map(lambda x: isinstance(x, dict), TFT_initial["setData"][i]["champions"][j]["ability"]["variables"]) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"]))) and all(l in TFT_initial["setData"][i]["champions"][j]["ability"]["variables"][k] for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in range(len(TFT_initial["setData"][i]["champions"][j]["ability"]["variables"])) for l in ["name", "value"]) and all(isinstance(TFT_initial["setData"][i]["champions"][j]["ability"]["variables"][k][l], str) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in range(len(TFT_initial["setData"][i]["champions"][j]["ability"]["variables"])) for l in ["name"]) and all(isinstance(TFT_initial["setData"][i]["champions"][j]["ability"]["variables"][k][l], list) or TFT_initial["setData"][i]["champions"][j]["ability"]["variables"][k][l] == None for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["champions"])) for k in range(len(TFT_initial["setData"][i]["champions"][j]["ability"]["variables"])) for l in ["value"]) and all(k in TFT_initial["setData"][i]["traits"][j] for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["traits"])) for k in ["apiName", "desc", "effects", "icon", "name"]) and all(isinstance(TFT_initial["setData"][i]["traits"][j][k], str) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["traits"])) for k in ["apiName", "desc", "icon", "name"]) and all(isinstance(TFT_initial["setData"][i]["traits"][j][k], list) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["traits"])) for k in ["effects"]) and all(map(lambda x: isinstance(x, dict), TFT_initial["setData"][i]["traits"][j]["effects"]) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["traits"]))) and all(l in TFT_initial["setData"][i]["traits"][j]["effects"][k] for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["traits"])) for k in range(len(TFT_initial["setData"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style", "variables"]) and all(isinstance(TFT_initial["setData"][i]["traits"][j]["effects"][k][l], int) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["traits"])) for k in range(len(TFT_initial["setData"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style"]) and all(isinstance(TFT_initial["setData"][i]["traits"][j]["effects"][k][l], dict) for i in range(len(TFT_initial["setData"])) for j in range(len(TFT_initial["setData"][i]["traits"])) for k in range(len(TFT_initial["setData"][i]["traits"][j]["effects"])) for l in ["variables"]) and all(j in TFT_initial["sets"][i] for i in TFT_initial["sets"] for j in ["champions", "name", "traits"]) and all(isinstance(TFT_initial["sets"][i][j], list) for i in TFT_initial["sets"] for j in ["champions", "traits"]) and all(isinstance(TFT_initial["sets"][i][j], str) for i in TFT_initial["sets"] for j in ["name"]) and all(k in TFT_initial["sets"][i]["champions"][j] for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in ["ability", "apiName", "characterName", "cost", "icon", "name", "role", "squareIcon", "stats", "tileIcon", "traits"]) and all(isinstance(TFT_initial["sets"][i]["champions"][j][k], dict) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in ["ability", "stats"]) and all(isinstance(TFT_initial["sets"][i]["champions"][j][k], str) or TFT_initial["sets"][i]["champions"][j][k] == None for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in ["apiName", "characterName", "icon", "name", "squareIcon", "tileIcon"]) and all(isinstance(TFT_initial["sets"][i]["champions"][j][k], int) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in ["cost"]) and all(k in TFT_initial["sets"][i]["champions"][j]["ability"] for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in ["desc", "icon", "name", "variables"]) and all(isinstance(TFT_initial["sets"][i]["champions"][j]["ability"][k], str) or TFT_initial["sets"][i]["champions"][j]["ability"][k] == None for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in ["desc", "icon", "name"]) and all(isinstance(TFT_initial["sets"][i]["champions"][j]["ability"][k], list) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in ["variables"]) and all(map(lambda x: isinstance(x, dict), TFT_initial["sets"][i]["champions"][j]["ability"]["variables"]) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"]))) and all(l in TFT_initial["sets"][i]["champions"][j]["ability"]["variables"][k] for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in range(len(TFT_initial["sets"][i]["champions"][j]["ability"]["variables"])) for l in ["name", "value"]) and all(isinstance(TFT_initial["sets"][i]["champions"][j]["ability"]["variables"][k][l], str) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in range(len(TFT_initial["sets"][i]["champions"][j]["ability"]["variables"])) for l in ["name"]) and all(isinstance(TFT_initial["sets"][i]["champions"][j]["ability"]["variables"][k][l], list) or TFT_initial["sets"][i]["champions"][j]["ability"]["variables"][k][l] == None for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["champions"])) for k in range(len(TFT_initial["sets"][i]["champions"][j]["ability"]["variables"])) for l in ["value"]) and all(k in TFT_initial["sets"][i]["traits"][j] for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["traits"])) for k in ["apiName", "desc", "effects", "icon", "name"]) and all(isinstance(TFT_initial["sets"][i]["traits"][j][k], str) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["traits"])) for k in ["apiName", "desc", "icon", "name"]) and all(isinstance(TFT_initial["sets"][i]["traits"][j][k], list) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["traits"])) for k in ["effects"]) and all(map(lambda x: isinstance(x, dict), TFT_initial["sets"][i]["traits"][j]["effects"]) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["traits"]))) and all(l in TFT_initial["sets"][i]["traits"][j]["effects"][k] for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["traits"])) for k in range(len(TFT_initial["sets"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style", "variables"]) and all(isinstance(TFT_initial["sets"][i]["traits"][j]["effects"][k][l], int) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["traits"])) for k in range(len(TFT_initial["sets"][i]["traits"][j]["effects"])) for l in ["maxUnits", "minUnits", "style"]) and all(isinstance(TFT_initial["sets"][i]["traits"][j]["effects"][k][l], dict) for i in TFT_initial["sets"] for j in range(len(TFT_initial["sets"][i]["traits"])) for k in range(len(TFT_initial["sets"][i]["traits"][j]["effects"])) for l in ["variables"]):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈基础数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT basic data archived in CommunityDragon database (%s)!" %(TFT_url, TFT_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的云顶之弈基础信息Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT basics Json data file path!' %(TFT_local, TFT_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有云顶之弈基础信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT basic information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈基础数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT basic data archived in CommunityDragon database (%s)!" %(TFT_url, TFT_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取云顶之弈英雄数据（The following code get TFT champion data）
                    try:
                        logPrint("正在加载云顶之弈棋子信息……\nLoading TFT champion information from CommunityDragon ...")
                        TFTChampion_initial = requests.get(TFTChampion_url) #TFTChampion存储云顶之弈的棋子信息（Variable `TFTChampion_initial` stores information of TFT champions）
                        if TFTChampion_initial.ok:
                            TFTChampion_initial = TFTChampion_initial.json()
                        else:
                            logPrint(TFTChampion_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('云顶之弈英雄信息获取超时！正在尝试离线加载数据……\nTFT champion information capture timeout! Trying loading offline data ...\n请输入云顶之弈英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTChampion_local_default, TFTChampion_local_default))
                        while True:
                            TFTChampion_local = logInput()
                            if TFTChampion_local == "":
                                TFTChampion_local = TFTChampion_local_default
                            elif TFTChampion_local[0] == "0":
                                logPrint("云顶之弈英雄信息获取失败！请检查系统网络状况和代理设置。\nTFT champion information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(TFTChampion_local, "r", encoding = "utf-8") as fp:
                                    TFTChampion_initial = json.load(fp)
                                if isinstance(TFTChampion_initial, list) and all(isinstance(TFTChampion_initial[i], dict) for i in range(len(TFTChampion_initial))) and all(TFTChampion_initial[i].get(j, 0) for i in range(len(TFTChampion_initial)) for j in ["name", "character_record"]):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈棋子数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT champion data archived in CommunityDragon database (%s)!" %(TFTChampion_url, TFTChampion_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的云顶之弈棋子Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT champion Json data file path!' %(TFTChampion_local, TFTChampion_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有云顶之弈英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT champion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈棋子数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT champion data archived in CommunityDragon database (%s)!" %(TFTChampion_url, TFTChampion_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取云顶之弈装备数据（The following code get TFT item information）
                    try:
                        logPrint("正在加载云顶之弈装备信息……\nLoading TFT item information from CommunityDragon ...")
                        TFTItem_initial = requests.get(TFTItem_url) #TFTItem存储云顶之弈的装备信息（Variable `TFTItem_initial` stores information of TFT items）
                        if TFTItem_initial.ok:
                            TFTItem_initial = TFTItem_initial.json()
                        else:
                            logPrint(TFTItem_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('云顶之弈装备信息获取超时！正在尝试离线加载数据……\nTFT item information capture timeout! Trying loading offline data ...\n请输入云顶之弈装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTItem_local_default, TFTItem_local_default))
                        while True:
                            TFTItem_local = logInput()
                            if TFTItem_local == "":
                                TFTItem_local = TFTItem_local_default
                            elif TFTItem_local[0] == "0":
                                logPrint("云顶之弈装备信息获取失败！请检查系统网络状况和代理设置。\nTFT item information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(TFTItem_local, "r", encoding = "utf-8") as fp:
                                    TFTItem_initial = json.load(fp)
                                if isinstance(TFTItem_initial, list) and all(isinstance(TFTItem_initial[i], dict) for i in range(len(TFTItem_initial))) and (all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "loadoutsIcon"]) or all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "squareIconPath"])):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT item data archived in CommunityDragon database (%s)!" %(TFTItem_url, TFTItem_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的云顶之弈装备Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT item Json data file path!' %(TFTItem_local, TFTItem_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有云顶之弈装备信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT item data archived in CommunityDragon database (%s)!" %(TFTItem_url, TFTItem_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取云顶之弈小小英雄数据（The following code get TFT companion data）
                    try:
                        logPrint("正在加载云顶之弈小小英雄信息……\nLoading companion information from CommunityDragon ...")
                        TFTCompanion_initial = requests.get(TFTCompanion_url) #TFTChampion存储云顶之弈的小小英雄信息（Variable `TFTChampion_initial` stores information of companions）
                        if TFTCompanion_initial.ok:
                            TFTCompanion_initial = TFTCompanion_initial.json()
                        else:
                            logPrint(TFTCompanion_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('云顶之弈小小英雄信息获取超时！正在尝试离线加载数据……\nTFT companion information capture timeout! Trying loading offline data ...\n请输入云顶之弈小小英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT companion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTCompanion_local_default, TFTCompanion_local_default))
                        while True:
                            TFTCompanion_local = logInput()
                            if TFTCompanion_local == "":
                                TFTCompanion_local = TFTCompanion_local_default
                            elif TFTCompanion_local[0] == "0":
                                logPrint("云顶之弈小小英雄信息获取失败！请检查系统网络状况和代理设置。\nTFT companion information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(TFTCompanion_local, "r", encoding = "utf-8") as fp:
                                    TFTCompanion_initial = json.load(fp)
                                if isinstance(TFTCompanion_initial, list) and all(isinstance(TFTCompanion_initial[i], dict) for i in range(len(TFTCompanion_initial))) and all(j in TFTCompanion_initial[i] for i in range(len(TFTCompanion_initial)) for j in ["contentId", "itemId", "name", "loadoutsIcon", "description", "level", "speciesName", "speciesId", "rarity", "rarityValue", "isDefault", "upgrades", "TFTOnly"]):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈小小英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT companion data archived in CommunityDragon database (%s)!" %(TFTCompanion_url, TFTCompanion_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的云顶之弈小小英雄Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT companion Json data file path!' %(TFTCompanion_local, TFTCompanion_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有云顶之弈小小英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈小小英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT companion data archived in CommunityDragon database (%s)!" %(TFTCompanion_url, TFTCompanion_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取云顶之弈羁绊数据（The following code get TFT trait data）
                    try:
                        logPrint("正在加载云顶之弈羁绊信息……\nLoading TFT trait information from CommunityDragon ...")
                        TFTTrait_initial = requests.get(TFTTrait_url) #TFTTrait存储云顶之弈的羁绊信息（Variable `TFTTrait_initial` stores information of TFT traits）
                        if TFTTrait_initial.ok:
                            TFTTrait_initial = TFTTrait_initial.json()
                        else:
                            logPrint(TFTTrait_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('云顶之弈羁绊信息获取超时！正在尝试离线加载数据……\nTFT trait information capture timeout! Trying loading offline data ...\n请输入云顶之弈羁绊Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT trait Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTTrait_local_default, TFTTrait_local_default))
                        while True:
                            TFTTrait_local = logInput()
                            if TFTTrait_local == "":
                                TFTTrait_local = TFTTrait_local_default
                            elif TFTTrait_local[0] == "0":
                                logPrint("云顶之弈羁绊信息获取失败！请检查系统网络状况和代理设置。\nTFT trait information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(TFTTrait_local, "r", encoding = "utf-8") as fp:
                                    TFTTrait_initial = json.load(fp)
                                if isinstance(TFTTrait_initial, list) and all(isinstance(TFTTrait_initial[i], dict) for i in range(len(TFTTrait_initial))) and all(j in TFTTrait_initial[i] for i in range(len(TFTTrait_initial)) for j in ["display_name", "trait_id", "set", "icon_path", "tooltip_text", "innate_trait_sets", "conditional_trait_sets"]):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈羁绊数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT trait data archived in CommunityDragon database (%s)!" %(TFTTrait_url, TFTTrait_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的云顶之弈羁绊Json数据文件路径！\nFile "%s" NOT found! Please input a correct TFT trait Json data file path!' %(TFTTrait_local, TFTTrait_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有云顶之弈小小英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈羁绊数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT trait data archived in CommunityDragon database (%s)!" %(TFTTrait_url, TFTTrait_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    #下面获取斗魂竞技场强化符文数据（The following code get Arena augment data）
                    try:
                        logPrint("正在加载斗魂竞技场强化符文信息……\nLoading Arena augment information from CommunityDragon ...")
                        CherryAugment_initial = requests.get(CherryAugment_url) #Arena存储斗魂竞技场的强化符文信息（Variable `CherryAugment_initial` stores information of Arena augments）
                        if CherryAugment_initial.ok:
                            CherryAugment_initial = CherryAugment_initial.json()
                            break
                        else:
                            logPrint(CherryAugment_initial)
                            logPrint("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        logPrint('斗魂竞技场强化符文信息获取超时！正在尝试离线加载数据……\nArena augment information capture timeout! Trying loading offline data ...\n请输入斗魂竞技场强化符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the Arena augment Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(CherryAugment_local_default, CherryAugment_local_default))
                        while True:
                            CherryAugment_local = logInput()
                            if CherryAugment_local == "":
                                CherryAugment_local = CherryAugment_local_default
                            elif CherryAugment_local[0] == "0":
                                logPrint("斗魂竞技场强化符文信息获取失败！请检查系统网络状况和代理设置。\nArena augment information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(CherryAugment_local, "r", encoding = "utf-8") as fp:
                                    CherryAugment_initial = json.load(fp)
                                if isinstance(CherryAugment_initial, list) and all(isinstance(CherryAugment_initial[i], dict) for i in range(len(CherryAugment_initial))) and all(j in CherryAugment_initial[i] for i in range(len(CherryAugment_initial)) for j in ["id", "nameTRA", "augmentSmallIconPath", "rarity"]) and all(isinstance(CherryAugment_initial[i]["id"], int) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["nameTRA"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["augmentSmallIconPath"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["rarity"], str) for i in range(len(CherryAugment_initial))):
                                    break
                                else:
                                    logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的斗魂竞技场强化符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the Arena augment data archived in CommunityDragon database (%s)!" %(CherryAugment_url, CherryAugment_url))
                                    continue
                            except FileNotFoundError:
                                logPrint('未找到文件“%s”！请输入正确的斗魂竞技场强化符文Json数据文件路径！\nFile "%s" NOT found! Please input a correct Arena augment Json data file path!' %(CherryAugment_local, CherryAugment_local))
                                continue
                            except OSError:
                                logPrint("数据文件名不合法！请输入含有斗魂竞技场强化符文信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with Arena augment information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                logPrint("数据格式错误！请选择一个符合CommunityDragon数据库中记录的斗魂竞技场强化符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the Arena augment data archived in CommunityDragon database (%s)!" %(CherryAugment_url, CherryAugment_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    break
                else:
                    switch_prepare_mode = False
                    logPrint('请在浏览器中打开以下网页，待加载完成后按Ctrl + S保存网页json文件至同目录的“离线数据（Offline Data）”文件夹下，并根据括号内的提示放置和命名文件。\nPlease open the following URLs in a browser, then press Ctrl + S to save the online json files into the folder "离线数据（Offline Data）" under the same directory after the website finishes loading and organize and rename the downloaded files according to the hints in the circle brackets.\n版本信息（%s）： %s\n召唤师技能（%s）： %s\n英雄（%s）： %s\n英雄联盟装备（%s）： %s\n召唤师图标（%s）： %s\n基石符文（%s）： %s\n符文系（%s）： %s\n云顶之弈基础信息（%s）： %s\n云顶之弈棋子（%s）： %s\n云顶之弈装备（%s）： %s\n云顶之弈小小英雄（%s）： %s\n云顶之弈羁绊（%s）： %s\n斗魂竞技场强化符文（%s）： %s' %(patches_local_default[19:], patches_url, spell_local_default[19:], spell_url, LoLChampion_local_default[19:], LoLChampion_url, LoLItem_local_default[19:], LoLItem_url, summonerIcon_local_default[19:], summonerIcon_url, perk_local_default[19:], perk_url, perkstyle_local_default[19:], perkstyle_url, TFT_local_default[19:], TFT_url, TFTChampion_local_default[19:], TFTChampion_url, TFTItem_local_default[19:], TFTItem_url, TFTCompanion_local_default[19:], TFTCompanion_url, TFTTrait_local_default[19:], TFTTrait_url, CherryAugment_local_default[19:], CherryAugment_url))
                    offline_files_loaded = {"patch": False, "spell": False, "LoLChampion": False, "LoLItem": False, "summonerIcon": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "CherryAugment": False}
                    offline_files = {"patch": {"file": patches_local_default, "URL": patches_url, "content": "版本信息"}, "spell": {"file": spell_local_default, "URL": spell_url, "content": "召唤师技能"}, "LoLChampion": {"file": LoLChampion_local_default, "URL": LoLChampion_url, "content": "英雄"}, "LoLItem": {"file": LoLItem_local_default, "URL": LoLItem_url, "content": "英雄联盟装备"}, "summonerIcon": {"file": summonerIcon_local_default, "URL": summonerIcon_url, "content": "召唤师图标"}, "perk": {"file": perk_local_default, "URL": perk_url, "content": "基石符文"}, "perkstyle": {"file": perkstyle_local_default, "URL": perkstyle_url, "content": "符文系"}, "TFT": {"file": TFT_local_default, "URL": TFT_url, "content": "云顶之弈基础信息"}, "TFTChampion": {"file": TFTChampion_local_default, "URL": TFTChampion_url, "content": "云顶之弈英雄"}, "TFTItem": {"file": TFTItem_local_default, "URL": TFTItem_url, "content": "云顶之弈装备"}, "TFTCompanion": {"file": TFTCompanion_local_default, "URL": TFTCompanion_url, "content": "云顶之弈小小英雄"}, "TFTTrait": {"file": TFTTrait_local_default, "URL": TFTTrait_url, "content": "云顶之弈羁绊"}, "CherryAugment": {"file": CherryAugment_local_default, "URL": CherryAugment_url, "content": "斗魂竞技场强化符文"}}
                    logPrint('请按任意键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPlease input anything to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
                    while any(not i for i in offline_files_loaded.values()):
                        offline_files_notfound = {"patch": False, "spell": False, "LoLChampion": False, "LoLItem": False, "summonerIcon": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "CherryAugment": False}
                        offline_files_formaterror = {"patch": False, "spell": False, "LoLChampion": False, "LoLItem": False, "summonerIcon": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "CherryAugment": False}
                        prepareMode = logInput()
                        if prepareMode != "" and prepareMode[0] == "1":
                            switch_prepare_mode = True
                            break
                        if prepareMode != "" and prepareMode[0] == "0":
                            return 0
                        #下面获取版本信息（The following code get the patch data）
                        if not offline_files_loaded["patch"]:
                            try:
                                with open(patches_local_default, "r", encoding = "utf-8") as fp:
                                    patches_initial = json.load(fp)
                                if not (isinstance(patches_initial, list) and patches_initial[-1] == "lolpatch_3.7"): #之所以将patches的最后一个元素作为判断版本文件数据格式合法的依据，是因为按照这样的逻辑，代码在一般情况下就不需要频繁变动（The reason why I use the last element of the variable `patches_initial` as the judgment whether the patch file data format is legal is, that under this logic, the code won't need further adjustment as the update goes on）
                                    offline_files_formaterror["patch"] = True
                            except FileNotFoundError:
                                offline_files_notfound["patch"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["patch"] = True
                            else:
                                if not offline_files_formaterror["patch"]:
                                    offline_files_loaded["patch"] = True
                                    latest_patch = patches_initial[0]
                                    patches_dict = {}
                                    smallPatches = []
                                    bigPatches = []
                                    for patch in patches_initial:
                                        if not patch.startswith("lolpatch"):
                                            patch_split = patch.split(".")
                                            smallPatch = ".".join(patch_split[:3])
                                            smallPatches.append(smallPatch)
                                            bigPatch = ".".join(patch_split[:2])
                                            bigPatches.append(bigPatch)
                                            patches_dict[bigPatch] = []
                                    for i in range(len(bigPatches)):
                                        patches_dict[bigPatches[i]].append(smallPatches[i])
                        #下面获取召唤师技能数据（The following code get summoner spell data）
                        if not offline_files_loaded["spell"]:
                            try:
                                with open(spell_local_default, "r", encoding = "utf-8") as fp:
                                    spell_initial = json.load(fp)
                                if not(isinstance(spell_initial, list) and all(i in spell_initial[j] for i in ["id", "name", "description", "summonerLevel", "cooldown", "gameModes", "iconPath"] for j in range(len(spell_initial)))):
                                    offline_files_formaterror["spell"] = True
                            except FileNotFoundError:
                                offline_files_notfound["spell"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["spell"] = True
                            else:
                                if not offline_files_formaterror["spell"]:
                                    offline_files_loaded["spell"] = True
                        #下面获取英雄信息（The following code get LoL champion data）
                        if not offline_files_loaded["LoLChampion"]:
                            try:
                                with open(LoLChampion_local_default, "r", encoding = "utf-8") as fp:
                                    LoLChampion_initial = json.load(fp)
                                if not(isinstance(LoLChampion_initial, list) and all(isinstance(LoLChampion_initial[i], dict) for i in range(len(LoLChampion_initial))) and all(j in LoLChampion_initial[i] for i in range(len(LoLChampion_initial)) for j in ["id", "name", "alias", "squarePortraitPath", "roles"]) and all(isinstance(LoLChampion_initial[i]["id"], int) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["name"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["alias"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["squarePortraitPath"], str) for i in range(len(LoLChampion_initial))) and all(isinstance(LoLChampion_initial[i]["roles"], list) for i in range(len(LoLChampion_initial)))):
                                    offline_files_formaterror["LoLChampion"] = True
                            except FileNotFoundError:
                                offline_files_notfound["LoLChampion"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["LoLChampion"] = True
                            else:
                                if not offline_files_formaterror["LoLChampion"]:
                                    offline_files_loaded["LoLChampion"] = True
                        #下面获取英雄联盟装备信息（The following code get LoL item data）
                        if not offline_files_loaded["LoLItem"]:
                            try:
                                with open(LoLItem_local_default, "r", encoding = "utf-8") as fp:
                                    LoLItem_initial = json.load(fp)
                                if not(isinstance(LoLItem_initial, list) and all(i in LoLItem_initial[j] for i in ["id", "name", "description", "active", "inStore", "from", "to", "categories", "maxStacks", "requiredChampion", "requiredAlly", "requiredBuffCurrencyName", "requiredBuffCurrencyCost", "specialRecipe", "isEnchantment", "price", "priceTotal", "iconPath"] for j in range(len(LoLItem_initial)))):
                                    offline_files_formaterror["LoLItem"] = True
                            except FileNotFoundError:
                                offline_files_notfound["LoLItem"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["LoLItem"] = True
                            else:
                                if not offline_files_formaterror["LoLItem"]:
                                    offline_files_loaded["LoLItem"] = True
                        #下面获取召唤师图标信息（The following code get summoner icon data）
                        if not offline_files_loaded["summonerIcon"]:
                            try:
                                with open(summonerIcon_local_default, "r", encoding = "utf-8") as fp:
                                    summonerIcon_initial = json.load(fp)
                                if not(isinstance(summonerIcon_initial, list) and all(map(lambda x: isinstance(x, dict), summonerIcon_initial)) and all(i in j for i in ["id", "title", "yearReleased", "isLegacy", "descriptions", "rarities", "disabledRegions"] for j in summonerIcon_initial)):
                                    offline_files_formaterror["summonerIcon"] = True
                            except FileNotFoundError:
                                offline_files_notfound["summonerIcon"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["summonerIcon"] = True
                            else:
                                if not offline_files_formaterror["summonerIcon"]:
                                    offline_files_loaded["summonerIcon"] = True
                        #下面获取基石符文信息（The following code get perk data）
                        if not offline_files_loaded["perk"]:
                            try:
                                with open(perk_local_default, "r", encoding = "utf-8") as fp:
                                    perk_initial = json.load(fp)
                                if not(isinstance(perk_initial, list) and all(i in perk_initial[j] for i in ["id", "name", "majorChangePatchVersion", "tooltip", "shortDesc", "longDesc", "recommendationDescriptor", "iconPath", "endOfGameStatDescs", "recommendationDescriptorAttributes"] for j in range(len(perk_initial)))):
                                    offline_files_formaterror["perk"] = True
                            except FileNotFoundError:
                                offline_files_notfound["perk"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["perk"] = True
                            else:
                                if not offline_files_formaterror["perk"]:
                                    offline_files_loaded["perk"] = True
                        #下面获取符文系信息（The following code get perkstyle data）
                        if not offline_files_loaded["perkstyle"]:
                            try:
                                with open(perkstyle_local_default, "r", encoding = "utf-8") as fp:
                                    perkstyle_initial = json.load(fp)
                                if not(isinstance(perkstyle_initial, dict) and all(perkstyle_initial.get(i, 0) for i in ["schemaVersion", "styles"]) and isinstance(perkstyle_initial["styles"], list) and all(j in perkstyle_initial["styles"][i] for i in range(len(perkstyle_initial["styles"])) for j in ["id", "name", "tooltip", "iconPath", "assetMap", "isAdvanced", "allowedSubStyles", "subStyleBonus", "slots", "defaultPageName", "defaultSubStyle", "defaultPerks", "defaultPerksWhenSplashed", "defaultStatModsPerSubStyle"])):
                                    offline_files_formaterror["perkstyle"] = True
                            except FileNotFoundError:
                                offline_files_notfound["perkstyle"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["perkstyle"] = True
                            else:
                                if not offline_files_formaterror["perkstyle"]:
                                    offline_files_loaded["perkstyle"] = True
                        #下面获取云顶之弈强化符文数据（The following code get TFT augment data）
                        if not offline_files_loaded["TFT"]:
                            try:
                                with open(TFT_local_default, "r", encoding = "utf-8") as fp:
                                    TFT_initial = json.load(fp)
                                if not(isinstance(TFT_initial, dict) and all(i in TFT_initial for i in ["items", "setData", "sets"])):
                                    offline_files_formaterror["TFT"] = True
                            except FileNotFoundError:
                                offline_files_notfound["TFT"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["TFT"] = True
                            else:
                                if not offline_files_formaterror["TFT"]:
                                    offline_files_loaded["TFT"] = True
                        #下面获取云顶之弈英雄数据（The following code get TFT champion data）
                        if not offline_files_loaded["TFTChampion"]:
                            try:
                                with open(TFTChampion_local_default, "r", encoding = "utf-8") as fp:
                                    TFTChampion_initial = json.load(fp)
                                if not(isinstance(TFTChampion_initial, list) and all(isinstance(TFTChampion_initial[i], dict) for i in range(len(TFTChampion_initial))) and all(TFTChampion_initial[i].get(j, 0) for i in range(len(TFTChampion_initial)) for j in ["name", "character_record"])):
                                    offline_files_formaterror["TFTChampion"] = True
                            except FileNotFoundError:
                                offline_files_notfound["TFTChampion"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["TFTChampion"] = True
                            else:
                                if not offline_files_formaterror["TFTChampion"]:
                                    offline_files_loaded["TFTChampion"] = True
                        #下面获取云顶之弈装备数据（The following code get TFT item information）
                        if not offline_files_loaded["TFTItem"]:
                            try:
                                with open(TFTItem_local_default, "r", encoding = "utf-8") as fp:
                                    TFTItem_initial = json.load(fp)
                                if not(isinstance(TFTItem_initial, list) and all(isinstance(TFTItem_initial[i], dict) for i in range(len(TFTItem_initial))) and (all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "loadoutsIcon"]) or all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "squareIconPath"]))):
                                    offline_files_formaterror["TFTItem"] = True
                            except FileNotFoundError:
                                offline_files_notfound["TFTItem"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["TFTItem"] = True
                            else:
                                if not offline_files_formaterror["TFTItem"]:
                                    offline_files_loaded["TFTItem"] = True
                        #下面获取云顶之弈小小英雄数据（The following code get TFT companion data）
                        if not offline_files_loaded["TFTCompanion"]:
                            try:
                                with open(TFTCompanion_local_default, "r", encoding = "utf-8") as fp:
                                    TFTCompanion_initial = json.load(fp)
                                if not(isinstance(TFTCompanion_initial, list) and all(isinstance(TFTCompanion_initial[i], dict) for i in range(len(TFTCompanion_initial))) and all(j in TFTCompanion_initial[i] for i in range(len(TFTCompanion_initial)) for j in ["contentId", "itemId", "name", "loadoutsIcon", "description", "level", "speciesName", "speciesId", "rarity", "rarityValue", "isDefault", "upgrades", "TFTOnly"])):
                                    offline_files_formaterror["TFTCompanion"] = True
                            except FileNotFoundError:
                                offline_files_notfound["TFTCompanion"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["TFTCompanion"] = True
                            else:
                                if not offline_files_formaterror["TFTCompanion"]:
                                    offline_files_loaded["TFTCompanion"] = True
                        #下面获取云顶之弈羁绊数据（The following code get TFT trait data）
                        if not offline_files_loaded["TFTTrait"]:
                            try:
                                with open(TFTTrait_local_default, "r", encoding = "utf-8") as fp:
                                    TFTTrait_initial = json.load(fp)
                                if not(isinstance(TFTTrait_initial, list) and all(isinstance(TFTTrait_initial[i], dict) for i in range(len(TFTTrait_initial))) and all(j in TFTTrait_initial[i] for i in range(len(TFTTrait_initial)) for j in ["display_name", "trait_id", "set", "icon_path", "tooltip_text", "innate_trait_sets", "conditional_trait_sets"])):
                                    offline_files_formaterror["TFTTrait"] = True
                            except FileNotFoundError:
                                offline_files_notfound["TFTTrait"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["TFTTrait"] = True
                            else:
                                if not offline_files_formaterror["TFTTrait"]:
                                    offline_files_loaded["TFTTrait"] = True
                        #下面获取斗魂竞技场强化符文数据（The following code get Arena augment data）
                        if not offline_files_loaded["CherryAugment"]:
                            try:
                                with open(CherryAugment_local_default, "r", encoding = "utf-8") as fp:
                                    CherryAugment_initial = json.load(fp)
                                if not(isinstance(CherryAugment_initial, list) and all(isinstance(CherryAugment_initial[i], dict) for i in range(len(CherryAugment_initial))) and all(j in CherryAugment_initial[i] for i in range(len(CherryAugment_initial)) for j in ["id", "nameTRA", "augmentSmallIconPath", "rarity"]) and all(isinstance(CherryAugment_initial[i]["id"], int) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["nameTRA"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["augmentSmallIconPath"], str) for i in range(len(CherryAugment_initial))) and all(isinstance(CherryAugment_initial[i]["rarity"], str) for i in range(len(CherryAugment_initial)))):
                                    offline_files_formaterror["CherryAugment"] = True
                            except FileNotFoundError:
                                offline_files_notfound["CherryAugment"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["CherryAugment"] = True
                            else:
                                if not offline_files_formaterror["CherryAugment"]:
                                    offline_files_loaded["CherryAugment"] = True
                        #下面总结离线数据加载情况（The following code conclude the result of loading offline data）
                        unloaded_offline_files = []
                        notfound_offline_files = []
                        formaterror_offline_files = []
                        if any(offline_files_notfound.values()):
                            for i in offline_files_notfound:
                                if offline_files_notfound[i]:
                                    notfound_offline_files.append(i)
                                    unloaded_offline_files.append(i)
                            logPrint("以下信息文件不存在：\nNot existing file(s):")
                            for i in notfound_offline_files:
                                logPrint(offline_files[i]["file"] + "\t" + offline_files[i]["content"] + "\t" + offline_files[i]["URL"])
                        if any(offline_files_formaterror.values()):
                            for i in offline_files_formaterror:
                                if offline_files_formaterror[i]:
                                    formaterror_offline_files.append(i)
                                    unloaded_offline_files.append(i)
                            logPrint("以下信息文件格式错误：\nFormatError file(s):")
                            for i in formaterror_offline_files:
                                logPrint(offline_files[i]["file"] + "\t" + offline_files[i]["content"] + "\t" + offline_files[i]["URL"])
                        if any(not i for i in offline_files_loaded.values()):
                            logPrint('请按任意键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPlease input anything to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
                    if switch_prepare_mode:
                        continue
                    else:
                        break
            if switch_language:
                continue
            break
        elif language_option[0] == "0":
            return 2
        else:
            logPrint("语言选项输入错误！请重新输入：\nERROR input of language option! Please try again:")
    #下面按照程序需求对数据资源进行一定的整理（The following code sort out the data resource according to the program's need）
    spells_initial = {} #spells为嵌套字典，键为召唤师技能序号，值为召唤师技能信息字典。一个键值对的示例如右：（Variable `spells` is a nested dictionary, whose keys are spellIds and values are spell information dictionaries. An example of the key-value pairs is shown as follows: ）{1: {"name": "净化", "description": "移除身上的所有限制效果（压制效果和击飞效果除外）和召唤师技能的减益效果，并且若在接下来的3秒里再次被施加限制效果时，新效果的持续时间会减少65%。", "summonerLevel": 9, "cooldown": 210, "gameModes": ["URF", "CLASSIC", "ARSR", "ARAM", "ULTBOOK", "WIPMODEWIP", "TUTORIAL", "DOOMBOTSTEEMO", "PRACTICETOOL", "FIRSTBLOOD", "NEXUSBLITZ", "PROJECT", "ONEFORALL"], "iconPath": "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_boost.png"}}
    for spell_iter in spell_initial:
        spell_id = int(spell_iter["id"])
        spells_initial[spell_id] = spell_iter
    LoLChampions_initial = {} #LoLChampions为嵌套字典，键为英雄序号，值为英雄信息字典。一个键值对的示例如右：（Variable `LoLItems` is a nested dictionary, whose keys are itemIds and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{1: {"name": "黑暗之女", "alias": "Annie", "squarePortraitPath": "/lol-game-data/assets/v1/champion-icons/1.png", "roles": ["mage", "support"]}}
    for LoLChampion_iter in LoLChampion_initial:
        LoLChampion_id = int(LoLChampion_iter["id"])
        LoLChampions_initial[LoLChampion_id] = LoLChampion_iter
    LoLItems_initial = {} #LoLItems为嵌套字典，键为装备序号，值为装备信息字典。一个键值对的示例如右：（Variable `LoLItems` is a nested dictionary, whose keys are itemIds and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{1001: {"name": "鞋子", "description": "<mainText><stats><attention>25</attention>移动速度</stats></mainText><br>", "active": False, "inStore": True, "from": [], "to": [3111, 3006, 3005, 3009, 3020, 3047, 3117, 3158], "categories": ["Boots"], "maxStacks": 1, "requiredChampion": "", "requiredAlly": "", "requiredBuffCurrencyName": "", "requiredBuffCurrencyCost": 0, "specialRecipe": 0, "isEnchantment": False, "price": 300, "priceTotal": 300, "iconPath": "/lol-game-data/assets/ASSETS/Items/Icons2D/1001_Class_T1_BootsofSpeed.png"}}
    for LoLItem_iter in LoLItem_initial:
        LoLItem_id = int(LoLItem_iter["id"])
        LoLItems_initial[LoLItem_id] = LoLItem_iter #从Json中读取到的整数键会被转换为字符串（Integer keys read from local json files will transform into strings）
    summonerIcons_initial = {} #summonerIcons为嵌套字典，键为装备序号，值为装备信息字典。一个键值对的示例如右：（Variable `summonerIcons` is a nested dictionary, whose keys are itemIds and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{0: {"id":0,"title":"可爱凯尔 图标","yearReleased":2009,"isLegacy":false,"imagePath":"/lol-game-data/assets/v1/profile-icons/0.jpg","descriptions":[{"region":"riot","description":" "}],"rarities":[{"region":"riot","rarity":0}],"disabledRegions":[]},{"id":1000,"title":"2016 LCL Hard Random","yearReleased":2016,"isLegacy":false,"imagePath":"/lol-game-data/assets/v1/profile-icons/1000.jpg","esportsTeam":"Hard Random","esportsRegion":"RU","esportsEvent":"英雄联盟欧陆联赛 LCL","descriptions":[{"region":"riot","description":" "}],"rarities":[{"region":"riot","rarity":0}],"disabledRegions":[]}}
    for summonerIcon_iter in summonerIcon_initial:
        summonerIcon_id = int(summonerIcon_iter["id"])
        summonerIcons_initial[summonerIcon_id] = summonerIcon_iter #从Json中读取到的整数键会被转换为字符串（Integer keys read from local json files will transform into strings）
    perks_initial = {} #perks为嵌套字典，键为符文序号，值为符文信息字典。一个键值对的示例如右：（Variable `perks` is a nested dictionary, whose keys are perkIds and values are perk information dictionaries. An example of the key-value pairs is shown as follows: ）{8369: {"name": "先攻", "majorChangePatchVersion": "11.23", "tooltip": "在进入与英雄战斗的@GraceWindow.2@秒内，对一名敌方英雄进行的攻击或技能将提供@GoldProcBonus@金币和<b>先攻</b>效果，持续@Duration@秒，来使你对英雄们造成<truedamage>@DamageAmp*100@%</truedamage>额外<truedamage>伤害</truedamage>，并提供<gold>{{ Item_Melee_Ranged_Split }}</gold>该额外伤害值的<gold>金币</gold>。<br><br>冷却时间：<scaleLevel>@Cooldown@</scaleLevel>秒<br><hr><br>已造成的伤害：@f1@<br>已提供的金币：@f2@", "shortDesc": "在你率先发起与英雄的战斗时，造成8%额外伤害，持续3秒，并基于该额外伤害提供金币。", "longDesc": "在进入与英雄战斗的0.25秒内，对一名敌方英雄进行的攻击或技能将提供5金币和<b>先攻</b>效果，持续3秒，来使你对英雄们造成<truedamage>8%</truedamage>额外<truedamage>伤害</truedamage>，并提供<gold>100% (远程英雄为70%)</gold>该额外伤害值的<gold>金币</gold>。<br><br>冷却时间：<scaleLevel>25 ~ 15</scaleLevel>秒", "recommendationDescriptor": "真实伤害，金币收入", "iconPath": "/lol-game-data/assets/v1/perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png", "endOfGameStatDescs": ["已造成的伤害：@eogvar1@", "已提供的金币：@eogvar2@"], "recommendationDescriptorAttributes": {}}}
    for perk_iter in perk_initial:
        perk_id = int(perk_iter["id"])
        perks_initial[perk_id] = perk_iter
    perkstyles_initial = {} #perkstyles为嵌套字典，键为符文系序号，值为符文系信息字典。一个键值对的示例如右：（Variable `perkstyles` is a nested dictionary, whose keys are perkstyle ids and values are perkstyle information dictionaries. An example of the key-value pairs is as follows: ）{8400: {"name": "坚决", "tooltip": "耐久和控制", "iconPath": "/lol-game-data/assets/v1/perk-images/Styles/7204_Resolve.png", "assetMap": {"p8400_s0_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k0.jpg", "p8400_s0_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8437.jpg", "p8400_s0_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8439.jpg", "p8400_s0_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8465.jpg", "p8400_s8000_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k0.jpg", "p8400_s8000_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8437.jpg", "p8400_s8000_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8439.jpg", "p8400_s8000_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8465.jpg", "p8400_s8100_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k0.jpg", "p8400_s8100_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8437.jpg", "p8400_s8100_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8439.jpg", "p8400_s8100_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8465.jpg", "p8400_s8200_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k0.jpg", "p8400_s8200_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8437.jpg", "p8400_s8200_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8439.jpg", "p8400_s8200_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8465.jpg", "p8400_s8300_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k0.jpg", "p8400_s8300_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8437.jpg", "p8400_s8300_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8439.jpg", "p8400_s8300_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8465.jpg", "svg_icon": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/resolve_icon.svg", "svg_icon_16": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/resolve_icon_16.svg"}, "isAdvanced": False, "allowedSubStyles": [8000, 8100, 8200, 8300], "subStyleBonus": [{"styleId": 8000, "perkId": 8414}, {"styleId": 8100, "perkId": 8454}, {"styleId": 8200, "perkId": 8415}, {"styleId": 8300, "perkId": 8416}], "slots": [{"type": "kKeyStone", "slotLabel": "", "perks": [8437, 8439, 8465]}, {"type": "kMixedRegularSplashable", "slotLabel": "蛮力", "perks": [8446, 8463, 8401]}, {"type": "kMixedRegularSplashable", "slotLabel": "抵抗", "perks": [8429, 8444, 8473]}, {"type": "kMixedRegularSplashable", "slotLabel": "生机", "perks": [8451, 8453, 8242]}, {"type": "kStatMod", "slotLabel": "进攻", "perks": [5008, 5005, 5007]}, {"type": "kStatMod", "slotLabel": "灵活", "perks": [5008, 5002, 5003]}, {"type": "kStatMod", "slotLabel": "防御", "perks": [5001, 5002, 5003]}], "defaultPageName": "坚决：巨像", "defaultSubStyle": 8200, "defaultPerks": [8437, 8446, 8444, 8451, 8224, 8237, 5008, 5002, 5001], "defaultPerksWhenSplashed": [8444, 8446], "defaultStatModsPerSubStyle": [{"id": "8000", "perks": [5005, 5002, 5001]}, {"id": "8100", "perks": [5008, 5002, 5001]}, {"id": "8200", "perks": [5008, 5002, 5001]}, {"id": "8300", "perks": [5007, 5002, 5001]}]}}
    for perkstyle_iter in perkstyle_initial["styles"]:
        perkstyle_id = int(perkstyle_iter["id"])
        perkstyles_initial[perkstyle_id] = perkstyle_iter
    TFTAugments_initial = {} #TFTAugments为嵌套字典，键为物件在LCU API上的表达形式，值为物件信息字典。一个键值对的示例如右：（Variable `TFTAugments` is a nested dictionary, whose keys are LCU API representation of items and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFT7_Consumable_NeekosHelpDragon": {"associatedTraits": [], "composition": [], "desc": "TFT7_Consumable_Description_Dragonling", "effects": {}, "from": None, "icon": "ASSETS/Maps/Particles/TFT/TFT7_Consumable_Dragonling.tex", "id": None, "incompatibleTraits": [], "name": "TFT7_Consumable_Name_Dragonling", "unique": False}}
    for item in TFT_initial["items"]:
        item_apiName = item["apiName"]
        TFTAugments_initial[item_apiName] = item
    TFTChampions_initial = {} #TFTChampions为嵌套字典，键为棋子在LCU API上的表达形式，值为棋子信息字典。一个键值对的示例如右：（Variable `TFTChampions` is a nested dictionary, whose keys are LCU API representation of TFT Champions and values are TFT Champion information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFT9_Aatrox": {"character_record": {"path": "Characters/TFT9_Aatrox/CharacterRecords/Root", "character_id": "TFT9_Aatrox", "rarity": 9, "display_name": "亚托克斯", "traits": [{"name": "暗裔", "id": "Set9_Darkin"}, {"name": "裁决战士", "id": "Set9_Slayer"}, {"name": "主宰", "id": "Set9_Armorclad"}], "squareIconPath": "/lol-game-data/assets/ASSETS/Characters/TFT9_Aatrox/HUD/TFT9_Aatrox_Square.TFT_Set9.png"}}}
    for TFTChampion_iter in TFTChampion_initial:
        champion_name = TFTChampion_iter["name"]
        TFTChampions_initial[champion_name] = TFTChampion_iter["character_record"]
    TFTItems_initial = {} #TTItems为嵌套字典，键为云顶之弈装备名称序号，值为云顶之弈装备信息字典。一个键值对的示例如右：（Variable `TFTItems` is a nested dictionary, whose keys are TFT item nameIds and values are TFT item information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFTTutorial_Item_BFSword": {"guid": "9f6e75bb-7ba2-49aa-8724-04c550279034", "name": "暴风大剑", "id": 0, "color": {"R": 73, "B": 54, "G": 68, "A": 255}, "loadoutsIcon": "/lol-game-data/assets/ASSETS/Maps/Particles/TFT/Item_Icons/Standard/BF_Sword.png"}}
    for TFTItem_iter in TFTItem_initial:
        item_nameId = TFTItem_iter["nameId"]
        TFTItems_initial[item_nameId] = TFTItem_iter
    TFTCompanions_initial = {} #TFTCompanions为嵌套字典，键为小小英雄序号，值为小小英雄信息字典。一个键值对的示例如右：（Variable `TFTCompanions` is a nested dictionary, whose keys are companion contentIds and values are companion information dictionaries. An example of the key-value pairs is shown as follows: ）{"91f2e228-4e36-4dad-9a97-36036e3eca36": {"itemId": 13010, "name": "节奏大师 奥希雅", "loadoutsIcon": "/lol-game-data/assets/ASSETS/Loadouts/Companions/Tooltip_AkaliDragon_Beatmaker_Tier1.png", "description": "奥希雅是酷炫的具象化。它用毫不费力的语流，指挥着韵脚和节奏，甚至能让最出色的小小英雄们羡慕不休。", "level": 1, "speciesName": "奥希雅", "speciesId": 13, "rarity": "Epic", "rarityValue": 1, "isDefault": false, "upgrades": ["0e251d36-d86e-4c58-9b7f-bcee2376a408", "e3151dc2-c45c-4949-89e9-6afda3b2fd5f"], "TFTOnly": false}}
    for companion_iter in TFTCompanion_initial:
        contentId = companion_iter["contentId"]
        TFTCompanions_initial[contentId] = companion_iter
    TFTTraits_initial = {} #TFTTraits为嵌套字典，键为羁绊在LCU API上的表达形式，值为羁绊信息字典。一个键值对的示例如右：（Variable `TFTTraits` is a nested dictionary, whose keys are LCU API representation of traits and values are trait information dictionaries. An example of the key-value pairs is shown as follows: ）{"Assassin": {"display_name": "刺客", "set": "TFTSet1", "icon_path": "/lol-game-data/assets/ASSETS/UX/TraitIcons/Trait_Icon_Assassin.png", "tooltip_text": "固有：在战斗环节开始时，刺客们会跃至距离最远的敌人处。<br><br>刺客们会获得额外的暴击伤害和暴击几率。<br><br><expandRow>(@MinUnits@) +@CritAmpPercent@%暴击伤害和+@CritChanceAmpPercent@%暴击几率</expandRow><br>", "innate_trait_sets": [], "conditional_trait_sets": {2: {"effect_amounts": [{"name": "CritAmpPercent", "value": 75.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 5.0, "format_string": ""}], "min_units": 3, "max_units": 5, "style_name": "kBronze"}, 3: {"effect_amounts": [{"name": "CritAmpPercent", "value": 150.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 20.0, "format_string": ""}], "min_units": 6, "max_units": 8, "style_name": "kSilver"}, 4: {"effect_amounts": [{"name": "CritAmpPercent", "value": 225.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 30.0, "format_string": ""}], "min_units": 9, "max_units": 25000, "style_name": "kGold"}}}}
    for trait_iter in TFTTrait_initial:
        trait_id = trait_iter["trait_id"]
        conditional_trait_sets = {}
        for conditional_trait_set in trait_iter["conditional_trait_sets"]:
            style_idx = conditional_trait_set["style_idx"]
            conditional_trait_sets[style_idx] = conditional_trait_set
        trait_iter["conditional_trait_sets"] = conditional_trait_sets
        TFTTraits_initial[trait_id] = trait_iter
    CherryAugments_initial = {} #CherryAugments为嵌套字典，键为斗魂竞技场强化符文在LCU API上的表达形式，值为斗魂竞技场强化符文信息字典。一个键值对的实例如右：（Variable `CherryAugments` is a nested dictionary, whose keys are LCU API representation of Arena augments and values are Arena augment information dictionaries. An example of the key-value pairs is shown as follows: ）{205: {"nameTRA": "物理转魔法", "augmentSmallIconPath": "/lol-game-data/assets/ASSETS/UX/Cherry/Augments/Icons/ADAPt_small.png", "rarity": "kSilver"}}
    for CherryAugment in CherryAugment_initial:
        CherryAugment_id = int(CherryAugment["id"])
        CherryAugments_initial[CherryAugment_id] = CherryAugment
    #下面创建一个嵌套字典，用来判断所有版本的各种数据是否曾经获取过（The following code create a nested dictionary to judge whether all kinds of data of a patch is once recaptured）
    TemplateBoolList = [False for i in range(len(bigPatches))] #为什么想到起个template作为后面字典的构成，是为了致敬后续出现的模板羁绊（The reason why I choose a name containing "template" to compose the following dictionary is in honor of the following "TemplateTrait"）
    recaptured_header = ["bigPatch", "spell", "LoLChampion", "LoLItem", "summonerIcon", "perk", "perkstyle", "TFTAugment", "TFTChampion", "TFTItem", "TFTCompanion", "TFTTrait", "CherryAugment"]
    recaptured = {}
    for bigPatch in bigPatches:
        recaptured[bigPatch] = {}
        for recaptured_header_iter in recaptured_header:
            recaptured[bigPatch][recaptured_header_iter] = False
    #实际上，目前recaptured并未投入使用。原本打算使用这个字典，是因为有些时候在获取连续的几场版本相同的对局时，如果都没能正确地把数据对应到其名称，那么每一局都会提示将原始数据填充至单元格。但是后来想到，这样虽然会使得输出减少，但是一旦代码完成英雄联盟对局记录的数据整理，要开始整理具体每一场对局了，那么回归到最近的对局的获取时，由于这场场对局的数据可能标记为“曾经获取过”，那么程序可能不再获取这场对局的版本的数据。此时，程序刚完成对局记录的整理，而对局记录最后几场对局可能是老版本，有些新版本的数据是没有的。这样的话，本来可以通过重新获取新版本的数据来将原始数据对应到其名称，现在却因为新版本被标记为已获取过数据的版本，而导致其原始数据被保存下来（Actually, `recaptured` isn't used currently. The original plan on using this dictionary is due to that if the data of several continuous matches of the same gameVersion fail to be mapped to their names, then the prompt like `the original data will be adopted` will pop up for every match to be captured. But then I come to realize that the use of `recaptured` may reduce the output, but under the circumstance of finishing the data sorting of LoL match history, when the program is about to capture the latest specific game information and timeline, then the program may never fetch data of this patch. At that time, the program has just finished sorting out the match history. Maybe the data version then is an old version, and it doesn't include some new data. In that case, the program could have recaptured data of the latest patch to map data to the corresponding names, but because of the use of `recapture`, this latest patch is marked as "a patch that has been recaptured", and hence the original data instead of their corresponding labels are saved）
    #下面创建一个字典，用来存储程序正在使用的各数据资源的版本（The following code create a dictionary to store the versions of data resources that the program currently uses）
    current_versions = {"summonerIcon": URLPatch, "spell": URLPatch, "LoLChampion": URLPatch, "LoLItem": URLPatch, "summonerIcon": URLPatch, "perk": URLPatch, "perkstyle": URLPatch, "TFTAugment": URLPatch, "TFTChampion": URLPatch, "TFTItem": URLPatch, "TFTCompanion": URLPatch, "TFTTrait": URLPatch, "CherryAugment": URLPatch}
    #下面创建一个字典，用来存储程序正在使用的各数据资源的版本下发生错误的键。当某个数据资源更换版本时，其出错的键会被清空（The following code create a dictionary to store the keys that fail to map to the constant dictionaries under certain versions of each kind of data resource. Once the version of a data resource changes, its unmapped keys will be cleared）
    unmapped_keys = {"summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set(), "CherryAugment": set()}
    #准备自己的召唤师数据（Prepare the information of the user himself/herself）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    #准备大区数据（Prepare server / platform data）
    platform_TENCENT = {"BGP1": "全网通区 男爵领域（Baron Zone）", "BGP2": "峡谷之巅（Super Zone）", "EDU1": "教育网专区（CRENET Server）", "HN1": "电信一区 艾欧尼亚（Ionia）", "HN2": "电信二区 祖安（Zaun）", "HN3": "电信三区 诺克萨斯（Noxus 1）", "HN4": "电信四区 班德尔城（Bandle City）", "HN4_NEW": "电信四区 班德尔城（Bandle City）", "HN5": "电信五区 皮尔特沃夫（Piltover）", "HN6": "电信六区 战争学院（the Institute of War）", "HN7": "电信七区 巨神峰（Mount Targon）", "HN8": "电信八区 雷瑟守备（Noxus 2）", "HN9": "电信九区 裁决之地（the Proving Grounds）", "HN10": "电信十区 黑色玫瑰（the Black Rose）", "HN11": "电信十一区 暗影岛（Shadow Isles）", "HN12": "电信十二区 钢铁烈阳（the Iron Solari）", "HN13": "电信十三区 水晶之痕（Crystal Scar）", "HN14": "电信十四区 均衡教派（the Kinkou Order）", "HN15": "电信十五区 影流（the Shadow Order）", "HN16": "电信十六区 守望之海（Guardian's Sea）", "HN17": "电信十七区 征服之海（Conqueror's Sea）", "HN18": "电信十八区 卡拉曼达（Kalamanda）", "HN19": "电信十九区 皮城警备（Piltover Wardens）", "PBE": "体验服 试炼之地（Chinese PBE）", "WT1": "网通一区 比尔吉沃特（Bilgewater）", "WT1_NEW": "网通一区 比尔吉沃特（Bilgewater）", "WT2": "网通二区 德玛西亚（Demacia）", "WT2_NEW": "网通二区 德玛西亚（Demacia）", "WT3": "网通三区 弗雷尔卓德（Freljord）", "WT3_NEW": "网通三区 弗雷尔卓德（Freljord）", "WT4": "网通四区 无畏先锋（House Crownguard）", "WT4_NEW": "网通四区 无畏先锋（House Crownguard）", "WT5": "网通五区 恕瑞玛（Shurima）", "WT6": "网通六区 扭曲丛林（Twisted Treeline）", "WT7": "网通七区 巨龙之巢（the Dragon Camp）", "FORCES": "比赛服 艾欧尼亚（Tournament - Ionia）", "NJ100": "联盟一区", "GZ100": "联盟二区", "CQ100": "联盟三区", "TJ100": "联盟四区", "TJ101": "联盟五区", "PREPBE": "试炼之地 临时过渡服务器（Chinese PBE Temporary）"}
    platform_RIOT = {"ME1": "中东服（Middle East）", "BR1": "巴西服（Brazil）", "EUN1": "北欧和东欧服（Europe Nordic & East）", "EUW1": "西欧服（Europe West）", "JP1": "日服（Japan）", "KR": "韩服（Republic of Korea）", "LA1": "北拉美服（Latin America North）", "LA2": "南拉美服（Latin America South）", "NA1": "北美服（North America）", "OC1": "大洋洲服（Oceania）", "TR1": "土耳其服（Turkey）", "RU": "俄罗斯服（Russia）", "PH2": "菲律宾服（Philippines）", "SG2": "新加坡服（Singapore）", "TH2": "泰服（Thailand）", "TW2": "台服（Taiwan, Hong Kong and Macau）", "VN2": "越南服（Vietnam）", "PBE1": "测试服（Public Beta Environment）"} #顺序采用参考开发者传送门网站的服务器路由（The order refers to Platform Routing Values on Riot Developer Portal website）
    platform_GARENA = {"PH1": "菲律宾服（Philippines）", "SG1": "新加坡服（Singapore, Malaysia and Indonesia）", "TW1": "台服（Taiwan, Hong Kong and Macau）", "VN1": "越南服（Vietnam）", "TH1": "泰服（Thailand）"} #顺序采用英雄联盟维基百科的“Server”词条的竞舞代理的服务器（The order refers to Garena servers in "Server" entry of League Wiki）
    platform = {"TENCENT": "国服（TENCENT）", "RIOT": "外服（RIOT）", "GARENA": "竞舞（GARENA）"}
    #定义常量字典（Define constant dictionaries）
    ##基础信息（Basic information）
    tiers = {"": "", "NONE": "没有段位", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
    #tiers = {"": "", "NONE": "NONE", "IRON": "IRON", "BRONZE": "BRONZE", "SILVER": "SILVER", "GOLD": "GOLD", "PLATINUM": "PLATINUM", "EMERALD": "EMERALD", "DIAMOND": "DIAMOND", "MASTER": "MASTER", "GRANDMASTER": "GRANDMASTER", "CHALLENGER": "CHALLENGER"}
    ratedTiers = {"": "", "NONE": "没有段位", "GRAY": "灰白", "GREEN": "翠绿", "BLUE": "天蓝", "PURPLE": "绛紫", "ORANGE": "耀橙"}
    #ratedTiers = {"": "", "NONE": "NONE", "GRAY": "GRAY", "GREEN": "GREEN", "BLUE": "BLUE", "PURPLE": "PURPLE", "ORANGE": "ORANGE"}
    tiers_all = tiers | ratedTiers
    ##排位信息（Ranked）
    #queueTypes = {"ARAM_BOT": "极地大乱斗 人机对战", "ARAM_CLASH": "极地大乱斗 冠军杯赛", "ARAM_UNRANKED_1x1": "极地大乱斗1v1", "ARAM_UNRANKED_5x5": "极地大乱斗5v5", "BOT": "人机对战", "CHERRY": "斗魂竞技场", "CHERRY_UNRANKED": "斗魂竞技场 匹配模式", "CHONCC_TREASURE_TFT": "云顶之弈（恭喜发财）", "CLASH": "冠军杯赛", "FIVE_YEAR_ANNIVERSARY_TFT": "云顶之弈 5周年时光机", "LNY23_TFT": "云顶之弈（恭喜发财）", "LNY24_TFT": "云顶之弈 （第3.5赛季回归：再战星海）", "NEXUSBLITZ": "极限闪击", "NORMAL": "匹配模式", "NORMAL_TFT": "云顶之弈 匹配模式", "ONEFORALL": "克隆大作战", "RANKED_FLEX_SR": "灵活 5V5", "RANKED_SOLO_5x5": "单人/双人", "RANKED_TFT": "云顶之弈 排位赛", "RANKED_TFT_DOUBLE_UP": "双人作战", "RANKED_TFT_PAIRS": "2V0", "RANKED_TFT_TURBO": "狂暴模式", "RIOTSCRIPT_BOT": "人机对战", "SF_TFT": "云顶之弈（斗魂锦标赛）", "STRAWBERRY": "无尽狂潮", "TURBO_TFT": "云顶之弈 狂暴模式 自定义", "TUTORIAL_MODULE_1": "新手教程 第一部分", "TUTORIAL_MODULE_2": "新手教程 第二部分", "TUTORIAL_MODULE_3": "新手教程 第三部分", "TUTORIAL_TFT": "云顶之弈 新手教程", "ULTBOOK": "终极魔典", "URF": "无限火力"}
    queueTypes = {"RANKED_SOLO_5x5": "单人/双人", "RANKED_FLEX_SR": "灵活 5V5", "RANKED_TFT": "云顶之弈", "RANKED_TFT_PAIRS": "2V0", "RANKED_TFT_DOUBLE_UP": "双人作战", "RANKED_TFT_TURBO": "狂暴模式", "CHERRY": "斗魂竞技场"} #2V0模式仅美测服可用（RANKED_TFT_PAIRS is only available on PBE）
    #queueTypes = {"RANKED_SOLO_5x5": "Ranked Solo/Duo", "RANKED_FLEX_SR": "Ranked Flex", "RANKED_TFT": "Ranked TFT", "RANKED_TFT_PAIRS": "2V0", "RANKED_TFT_DOUBLE_UP": "Double Up", "RANKED_TFT_TURBO": "Hyper Roll", "CHERRY": "Arena"}
    ##英雄联盟对局记录（LoL match history）
    gameTypes = {"MATCHED_GAME": "匹配对局", "CUSTOM_GAME": "自定义对局", "TUTORIAL_GAME": "新手教程"}
    #gameTypes = {"MATCHED_GAME": "MATCHED_GAME", "CUSTOM_GAME": "CUSTOM_GAME", "TUTORIAL_GAME": "TUTORIAL_GAME"}
    team_color = {0: "", 100: "蓝方", 200: "红方"}
    #team_color = {0: "", 100: "Blue", 200: "Red"}
    endOfGameResults = {"": "", "GameComplete": "游戏结束", "Abort_Unexpected": "意外终止", "Abort_TooFewPlayers": "全员提前退出", "Abort_AntiCheatExit": "检测到作弊而终止"}
    #endOfGameResults = {"": "", "GameComplete": "GameComplete", "Abort_Unexpected": "Abort_Unexpected", "Abort_TooFewPlayers": "Abort_TooFewPlayers", "Abort_AntiCheatExit": "Abort_AntiCheatExit"}
    lanes = {"TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "NONE": ""}
    #lanes = {"TOP": "TOP", "JUNGLE": "JUNGLE", "MIDDLE": "MIDDLE", "BOTTOM": "BOTTOM", "NONE": ""}
    roles = {"CARRY": "C位", "DUO": "游走", "SOLO": "单人", "SUPPORT": "辅助", "NONE": ""}
    #roles = {"CARRY": "CARRY", "DUO": "DUO", "SOLO": "SOLO", "SUPPORT": "SUPPORT", "NONE": ""}
    ##英雄联盟对局信息（LoL match information）
    subteam_color = {0: "", 1: "魄罗", 2: "小兵", 3: "迅捷蟹", 4: "石甲虫", 5: "锋喙鸟", 6: "哨卫", 7: "狼", 8: "魔沼蛙"} #仅用于斗魂竞技场（Only for Arena mode）
    #subteam_color = {0: "", 1: "Poro", 2: "Minion", 3: "Scuttle", 4: "Krug", 5: "Raptor", 6: "Sentinel", 7: "Wolf", 8: "Gromp"}
    augment_rarity = {0: "白银", 1: "黄金", 2: "棱彩", 4: "黄金", 8: "棱彩", "kBronze": "青铜", "kSilver": "白银", "kGold": "黄金", "kPrismatic": "棱彩"}
    #augment_rarity = {0: "Silver", 1: "Gold", 2: "Prismatic", 4: "Gold", 8: "Prismatic", "KBronze": "Bronze", "KSilver": "Silver", "kGold": "Gold", "kPrismatic": "Prismatic"}
    win = {True: "胜利", False: "失败"}
    #win = {True: "V", False: "D"}
    ##英雄联盟事件（LoL events）
    eventTypes = {"CHAMPION_KILL": "英雄击杀", "ELITE_MONSTER_KILL": "史诗级野怪击杀", "BUILDING_KILL": "建筑物击杀"}
    #eventTypes = {"CHAMPION_KILL": "Champion Kills", "ELITE_MONSTER_KILL": "Elite Monster Kills", "BUILDING_KILL": "Building Kills"}
    buildingTypes = {"": "", "TOWER_BUILDING": "防御塔", "INHIBITOR_BUILDING": "召唤水晶"}
    #buildingTypes = {"": "", "TOWER_BUILDING": "Turret", "INHIBITOR_BUILDING": "Inhibitor"}
    laneTypes = {"": "", "TOP_LANE": "上路", "MID_LANE": "中路", "BOT_LANE": "下路"}
    #laneTypes = {"": "", "TOP_LANE": "Top", "MID_LANE": "Middle", "BOT_LANE": "Bottom"}
    monsterSubTypes = {"": "", "EARTH_DRAGON": "山脉亚龙", "CHEMTECH_DRAGON": "炼金科技亚龙", "WATER_DRAGON": "海洋亚龙", "HEXTECH_DRAGON": "海克斯科技亚龙", "AIR_DRAGON": "云霄亚龙", "FIRE_DRAGON": "炼狱亚龙", "ELDER_DRAGON": "远古巨龙", "RUINED_DRAGON": "破败巨龙", "UNKNOWN": "未知"}
    #monsterSubTypes = {"": "", "EARTH_DRAGON": "Mountain Drake", "CHEMTECH_DRAGON": "Chemtech Drake", "WATER_DRAGON": "Ocean Drake", "HEXTECH_DRAGON": "Hextech Drake", "AIR_DRAGON": "Cloud Drake", "FIRE_DRAGON": "Infernal Drake", "ELDER_DRAGON": "Elder Dragon", "RUINED_DRAGON": "Ruined Dragon", "UNKNOWN": "Unknown"}
    monsterTypes = {"": "", "RIFTHERALD": "峡谷先锋", "HORDE": "虚空巢虫", "BARON_NASHOR": "纳什男爵", "DRAGON": "巨龙", "ATAKHAN": "厄塔汗"}
    #monsterTypes = {"": "", "RIFTHERALD": "Rift Herald", "HORDE": "Voidgrub", "BARON_NASHOR": "Baron Nashor", "DRAGON": "Drake", "ATAKHAN": "Atakhan"}
    towerTypes = {"": "", "OUTER_TURRET": "外防御塔", "INNER_TURRET": "内防御塔", "BASE_TURRET": "水晶防御塔", "NEXUS_TURRET": "枢纽防御塔"}
    #towerTypes = {"": "", "OUTER_TURRET": "Outer Turret", "INNER_TURRET": "Inner Turret", "BASE_TURRET": "Inhibitor Turret", "NEXUS_TURRET": "Nexus Turret"}
    ##云顶之弈对局记录（TFT match history）
    #traitStyles = {"kThreat": "威慑", "kBronze": "青铜", "kSilver": "白银", "kGold": "黄金", "kChromatic": "炫金"}
    traitStyles = {0: "", 1: "青铜", 2: "白银", 3: "黄金", 4: "炫金", 5: "独特"}
    rarities = {"Default": "经典", "NoRarity": "其它", "Epic": "史诗", "Legendary": "传说", "Mythic": "神话", "Rare": "稀有", "Ultimate": "终极", "Exalted": "圣者至尊", "Transcendant": "超凡"}
    #控制只输出一遍的提示（Control the hint to be displayed only once）
    puuid_change_warning_printed = False
    #logPrint('''在腾讯代理的服务器上，如果查询某名玩家的对局记录，请尝试以下操作：\nTo search for the match history of a player on Tencent servers, try out the following operations:\n1. 在浏览器中打开本地主机网络协议：%s\n   Open the localhost IP in any browser: %s\n2. 尝试用以下用户名和密码登录：\n   Try logining in with the following username and password:\n   用户名（Username）：riot\n   密码（Password）：%s\n3. （如果可以立即知道一位玩家的玩家通用唯一识别码，则可以跳过第3和4步）在浏览器的地址栏中的地址最后，添加“lol-summoner/v1/summoners?name={name}”，其中{name}指的是召唤师名称编码后的字符串。当召唤师名称只包含英文字母和阿拉伯数字时，直接以召唤师名称去空格后的字符串代入{name}即可；当召唤师名称存在非美国标准信息交换代码时，以召唤师名称编码后的字符串代入{name}。\n(If a summoner's puuid can be immediately known, the user may skip Steps 3 and 4) Add to following the last character of the address in the browser's address bar "lol-summoner/v1/summoners?name={name}", where {name} refers to strings encoded from summonerName. When summonerName contains only English letters and Arabic numbers, simply substitute {name} with the strings with the spaces removed from summonerName. When a non-ASCII character exists in summonerName, substitute {name} by encoded summonerName.\n3.1 对于包含非美国标准信息交换代码的召唤师名称，如果可以得到该召唤师的精确名称（如通过复制到剪贴板），那么在Python中可以得知其编码后的字符串。在Python中使用from urllib.parse import quote命令引入quote函数，再使用quote(x)函数获取字符串x编码后的字符串。\nFor summonerNames that include non-ASCII characters, if the exact summonerName can be obtained (e. g. by copying to clipboard), then its encoded string can be returned in Python. In Python console, use "from urllib.parse import quote" to introduce the "quote" function. Then use quote(x) function to get the string encoded from the string x.\n4. 在lol-summoner/v1/summoners?name={name}返回的结果中找到puuid并复制。\n   Find "puuid" in the result returned by "lol-summoner/v1/summoners?name={name}" and copy it.\n5. 将地址栏中4位IP地址后的斜杠后的内容删除，再添加“lol-match-history/v1/products/lol/{puuid}/matches?begIndex=0&endIndex=20”或“lol-match-history/v1/products/tft/{puuid}/matches?begin=0&count=20”，其中{puuid}是事先获知的玩家通用唯一识别码，或者是第4步复制到剪贴板的puuid。\nDelete the content following the slash after the 4-bit IP address in the address bar and then add to the end "lol-match-history/v1/products/lol/{puuid}/matches?begIndex=0&endIndex=20" or "lol-match-history/v1/products/tft/{puuid}/matches?begin=0&count=20", where {puuid} refers to the puuid previously known, or copied to clipboard in Step 4.\n6. 尝试将上一步输入的地址中的“endIndex=”或“count=”后的数字依次替换成21、199、200和500，观察每次替换后返回的网页结果有没有变多。\nTry changing the number following "endIndex=" or "count=" in the last step into 21, 199, 200 and 500 one by one, and observe whether the returned webpage contains more information after each change.\n7. 教程完成，请继续执行本脚本……\n   Instruction finished. Please continue to run this program ...''' %(connection.address, connection.address, connection.auth_key))
    while True:
        #初始化所有数据资源（Initialize all data resources）
        logPrint("\n正在初始化所有数据资源……\nInitializing all data resources ...\n")
        patches = copy.deepcopy(patches_initial)
        spells = copy.deepcopy(spells_initial)
        LoLChampions = copy.deepcopy(LoLChampions_initial)
        LoLItems = copy.deepcopy(LoLItems_initial)
        summonerIcons = copy.deepcopy(summonerIcons_initial)
        perks = copy.deepcopy(perks_initial)
        perkstyles = copy.deepcopy(perkstyles_initial)
        TFTAugments = copy.deepcopy(TFTAugments_initial)
        TFTChampions = copy.deepcopy(TFTChampions_initial)
        TFTItems = copy.deepcopy(TFTItems_initial)
        TFTCompanions = copy.deepcopy(TFTCompanions_initial)
        TFTTraits = copy.deepcopy(TFTTraits_initial)
        CherryAugments = copy.deepcopy(CherryAugments_initial)
        current_versions = {"summonerIcon": URLPatch, "spell": URLPatch, "LoLChampion": URLPatch, "LoLItem": URLPatch, "summonerIcon": URLPatch, "perk": URLPatch, "perkstyle": URLPatch, "TFTAugment": URLPatch, "TFTChampion": URLPatch, "TFTItem": URLPatch, "TFTCompanion": URLPatch, "TFTTrait": URLPatch, "CherryAugment": URLPatch}
        unmapped_keys = {"summonerIcon": set(), "spell": set(), "LoLChampion": set(), "LoLItem": set(), "summonerIcon": set(), "perk": set(), "perkstyle": set(), "TFTAugment": set(), "TFTChampion": set(), "TFTItem": set(), "TFTCompanion": set(), "TFTTrait": set(), "CherryAugment": set()}
        infos = {} #存储程序运行过程中遇到的玩家信息，防止后续程序反复获取已经获取过的玩家信息（Store the summoner information fetched during the program execution, in case the program would keep capturing the summoner information already fetched before）
        match_notbelonging_warning_printed = False
        logPrint('请输入要查询的召唤师名称，退出请输入“0”：\nPlease input the summoner name to be searched. Submit "0" to exit.')
        summoner_name = logInput()
        if summoner_name == "0":
            break
        elif summoner_name == "":
            logPrint("请输入非空字符串！\nPlease input a string instead of null!")
            continue
        else:
            if summoner_name == "current-summoner":
                info = {"searchType": "current-summoner", "endpoint": "/lol-summoner/v1/current-summoner", "info_got": True, "network_error": False, "body": current_info.copy(), "message": "", "selfInfo": True}
            else:
                info = await get_info(connection, summoner_name)
            if not info["info_got"]:
                logPrint(info["message"])
            else:
                info_body = info["body"]
                displayName = get_info_name(info_body) #用于文件名命名（For use of file naming）
                current_puuid = info_body["puuid"] #用于核验对局是否包含该召唤师。此外，还用于扫描模式从对局的所有玩家信息中定位到该玩家（For use of checking whether the searched matches include this summoner. In addition, it's used for localization of this player from all players in a match in "scan" mode）
                current_summonerName = "" if info_body["gameName"] == "" and info_body["tagLine"] == "" else info_body["gameName"] + "#" + info_body["tagLine"] #作用同上，用于模糊定位，主要应用于玩家通用唯一识别码发生变动的大区且在昵称编号引入后注册的主召唤师的对局记录扫描模式（Acts as the same role as the above variable for a rough localization. It's mainly designed for Scan Mode on players that signed up after tagLine was introduced on servers that changed the players' puuids）
                infos[current_puuid] = info_body
                #下面准备一些数据资源（The following code prepare data resources）
                gamemode = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
                gamemodes = {-1: {"name": "自定义", "gameMode": "CUSTOM", "category": "CUSTOM", "description": "", "type": "CUSTOM"}, 0: {"name": "自定义", "gameMode": "CUSTOM", "category": "CUSTOM", "description": "", "type": "CUSTOM"}}
                for gamemode_iter in gamemode:
                    gamemode_id = gamemode_iter["id"]
                    gamemodes_iter = {}
                    gamemodes_iter["name"] = gamemode_iter["name"]
                    gamemodes_iter["gameMode"] = gamemode_iter["gameMode"]
                    gamemodes_iter["category"] = gamemode_iter["category"]
                    gamemodes_iter["description"] = gamemode_iter["description"]
                    gamemodes_iter["type"] = gamemode_iter["type"]
                    gamemodes[gamemode_id] = gamemodes_iter
                queues = {queue["id"]: queue for queue in gamemode}
                maps = {8: {"zh_CN": "水晶之痕", "en_US": "Crystal Scar"}, 10: {"zh_CN": "扭曲丛林", "en_US": "Twisted Treeline"}, 11: {"zh_CN": "召唤师峡谷", "en_US": "Summoner's Rift"}, 12: {"zh_CN": "嚎哭深渊", "en_US": "Howling Abyss"}, 16: {"zh_CN": "星界废墟", "en_US": "Cosmic Ruins"}, 18: {"zh_CN": "瓦洛兰城市公园", "en_US": "Valoran City Park"}, 20: {"zh_CN": "飞船坠落点", "en_US": "Crash Site"}, 21: {"zh_CN": "百合与莲花的神庙", "en_US": "Temple of Lily and Lotus"}, 22: {"zh_CN": "聚点危机", "en_US": "Convergence"}, 30: {"zh_CN": "怒火角斗场", "en_US": "Rings of Wrath"}, 33: {"zh_CN": "最终都市", "en_US": "Final City"}, 35: {"zh_CN": "班德尔之森", "en_US": "The Bandlewood"}}
                
                #logPrint("召唤师信息如下：\nSummoner information is as follows:")
                ranked = await (await connection.request("GET", "/lol-ranked/v1/ranked-stats/" + info_body["puuid"])).json()
                #logPrint(info_body)

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
                    folder = platform_folder + "\\" + get_info_name(info_body, 2)
                elif region == "GARENA":
                    platform_folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[platformId]
                    folder = platform_folder + "\\" + get_info_name(info_body, 2)
                else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
                    platform_folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[platformId]
                    folder = platform_folder + "\\" + get_info_name(info_body, 3)
                platform_config_filepath = platform_folder + "\\" + "platform_config_namespaces.json"
                while True:
                    try:
                        with open(platform_config_filepath, "w", encoding = "utf-8") as fp:
                            json.dump(platform_config, fp, indent = 4, ensure_ascii = False)
                    except FileNotFoundError: #这里需要注意是否具有创建文件夹的权限。下同（Pay attention to the authority to create the folder. So are the following）
                        os.makedirs(os.path.dirname(platform_config_filepath), exist_ok = True)
                    else:
                        break
                
                json1name = "Summoner Profile - " + displayName + ".json"
                while True:
                    try:
                        jsonfile1 = open(os.path.join(folder, json1name), "w", encoding = "utf-8")
                    except FileNotFoundError:
                        os.makedirs(folder, exist_ok = True)
                    else:
                        break
                try:
                    jsonfile1.write(json.dumps(info_body, indent = 4, ensure_ascii = False))
                except UnicodeEncodeError:
                    logPrint("召唤师信息文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nSummoner information text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                else:
                    logPrint('召唤师信息已保存为“%s”。\nSummoner information is saved as "%s".\n' %(os.path.join(folder, json1name), os.path.join(folder, json1name)))
                jsonfile1.close()
                currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                pkl1name = "Intermediate Object - info (Summoner Profile) - %s (%s).pkl" %(displayName, currentTime)
                #with open(os.path.join(folder, pkl1name), "wb") as IntObj1:
                    #pickle.dump(info_body, IntObj1)
                if "errorCode" in ranked and ranked["httpStatus"] == 404: #很久以前，国服体验服的排位数据API未知。现在已经与正式服统一（Long ago, API of ranked stats on Chinese PBE was unknown. Now it accords with Live servers）
                    info_data = {"项目": ["帐户序号", "显示名", "玩家昵称", "内置名称", "改名警告", "升级进度", "生涯公开性", "生涯背景序号", "玩家通用唯一识别码", "召唤师序号", "召唤师等级", "昵称编号", "尚未命名", "目前经验", "升级所需经验", "当前大乱斗重随次数", "最大重随次数", "当前大乱斗重随点", "单次重随消耗大乱斗重随点", "增加一次重随次数所需大乱斗重随点"], "Items": ["accountID", "displayName", "gameName", "internalName", "nameChangeFlag", "percentCompleteforNextLevel", "privacy", "profileIconId", "puuid", "summonerId", "summonerLevel", "tagLine", "unnamed", "xpSinceLastLevel", "xpUntilNextLevel", "numberOfRolls", "maxRerollPoints", "currentRerollPoints", "pointsCostToRoll", "pointsToRoll"], "值": [info_body["accountId"], info_body["displayName"], info_body["gameName"], info_body["internalName"], info_body["nameChangeFlag"], info_body["percentCompleteForNextLevel"], info_body["privacy"], info_body["profileIconId"], info_body["puuid"], info_body["summonerId"], info_body["summonerLevel"], info_body["tagLine"], info_body["unnamed"], info_body["xpSinceLastLevel"], info_body["xpUntilNextLevel"], info_body["rerollPoints"]["numberOfRolls"], info_body["rerollPoints"]["maxRolls"], info_body["rerollPoints"]["currentPoints"], info_body["rerollPoints"]["pointsCostToRoll"], info_body["rerollPoints"]["pointsToReroll"]]}
                elif not "highestPreviousSeasonAchievedDivision" in ranked and not "highestPreviousSeasonAchievedTier" in ranked: #在美测服14.2版本发现这两个键被删除了（These two keys are found to be deleted in PBE Patch 14.2）
                    info_data = {"项目": ["帐户序号", "显示名", "玩家昵称", "内置名称", "改名警告", "升级进度", "生涯公开性", "生涯背景序号", "玩家通用唯一识别码", "召唤师序号", "召唤师等级", "昵称编号", "尚未命名", "目前经验", "升级所需经验", "当前大乱斗重随次数", "最大重随次数", "当前大乱斗重随点", "单次重随消耗大乱斗重随点", "增加一次重随次数所需大乱斗重随点", "当前赛季赛段点", "已获得的段位奖励物品序号", "当前赛季最高段位（召唤师峡谷）", "过往赛季结束段位", "过往赛季结束段位分级"], "Items": ["accountID", "displayName", "gameName", "internalName", "nameChangeFlag", "percentCompleteforNextLevel", "privacy", "profileIconId", "puuid", "summonerId", "summonerLevel", "tagLine", "unnamed", "xpSinceLastLevel", "xpUntilNextLevel", "numberOfRolls", "maxRerollPoints", "currentRerollPoints", "pointsCostToRoll", "pointsToRoll", "currentSeasonSplitPoints", "earnedRegaliaRewardIds", "highestCurrentSeasonReachedTierSR", "highestPreviousSeasonEndTier", "highestPreviousSeasonEndDivision"], "值": [info_body["accountId"], info_body["displayName"], info_body["gameName"], info_body["internalName"], info_body["nameChangeFlag"], info_body["percentCompleteForNextLevel"], info_body["privacy"], info_body["profileIconId"], info_body["puuid"], info_body["summonerId"], info_body["summonerLevel"], info_body["tagLine"], info_body["unnamed"], info_body["xpSinceLastLevel"], info_body["xpUntilNextLevel"], info_body["rerollPoints"]["numberOfRolls"], info_body["rerollPoints"]["maxRolls"], info_body["rerollPoints"]["currentPoints"], info_body["rerollPoints"]["pointsCostToRoll"], info_body["rerollPoints"]["pointsToReroll"], ranked["currentSeasonSplitPoints"], ranked["earnedRegaliaRewardIds"], tiers[ranked["highestCurrentSeasonReachedTierSR"]], tiers[ranked["highestPreviousSeasonEndTier"]], ranked["highestPreviousSeasonEndDivision"]]}
                else:
                    info_data = {"项目": ["帐户序号", "显示名", "玩家昵称", "内置名称", "改名警告", "升级进度", "生涯公开性", "生涯背景序号", "玩家通用唯一识别码", "召唤师序号", "召唤师等级", "昵称编号", "尚未命名", "目前经验", "升级所需经验", "当前大乱斗重随次数", "最大重随次数", "当前大乱斗重随点", "单次重随消耗大乱斗重随点", "增加一次重随次数所需大乱斗重随点", "当前赛季赛段点", "已获得的段位奖励物品序号", "当前赛季最高段位（召唤师峡谷）", "过往赛季最高段位", "过往赛季最高段位分级", "过往赛季结束段位", "过往赛季结束段位分级"], "Items": ["accountID", "displayName", "gameName", "internalName", "nameChangeFlag", "percentCompleteforNextLevel", "privacy", "profileIconId", "puuid", "summonerId", "summonerLevel", "tagLine", "unnamed", "xpSinceLastLevel", "xpUntilNextLevel", "numberOfRolls", "maxRerollPoints", "currentRerollPoints", "pointsCostToRoll", "pointsToRoll", "currentSeasonSplitPoints", "earnedRegaliaRewardIds", "highestCurrentSeasonReachedTierSR", "highestPreviousSeasonAchievedTier", "highestPreviousSeasonAchievedDivision", "highestPreviousSeasonEndTier", "highestPreviousSeasonEndDivision"], "值": [info_body["accountId"], info_body["displayName"], info_body["gameName"], info_body["internalName"], info_body["nameChangeFlag"], info_body["percentCompleteForNextLevel"], info_body["privacy"], info_body["profileIconId"], info_body["puuid"], info_body["summonerId"], info_body["summonerLevel"], info_body["tagLine"], info_body["unnamed"], info_body["xpSinceLastLevel"], info_body["xpUntilNextLevel"], info_body["rerollPoints"]["numberOfRolls"], info_body["rerollPoints"]["maxRolls"], info_body["rerollPoints"]["currentPoints"], info_body["rerollPoints"]["pointsCostToRoll"], info_body["rerollPoints"]["pointsToReroll"], ranked["currentSeasonSplitPoints"], ranked["earnedRegaliaRewardIds"], tiers[ranked["highestCurrentSeasonReachedTierSR"]], tiers[ranked["highestPreviousSeasonAchievedTier"]], ranked["highestPreviousSeasonAchievedDivision"], tiers[ranked["highestPreviousSeasonEndTier"]], ranked["highestPreviousSeasonEndDivision"]]}
                info_df = pandas.DataFrame(data = info_data)
                info_htmlTable = info_df.to_html(escape = False)
                
                #logPrint("召唤师英雄成就如下：\nSummoner champion mastery is as follows:")
                mastery = await (await connection.request("GET", "/lol-champion-mastery/v1/" + current_puuid + "/champion-mastery")).json()
                #logPrint(mastery)
                json2name = "Champion Mastery - " + displayName + ".json"
                while True:
                    try:
                        jsonfile2 = open(os.path.join(folder, json2name), "w", encoding = "utf-8")
                    except FileNotFoundError:
                        os.makedirs(folder, exist_ok = True)
                    else:
                        break
                try:
                    jsonfile2.write(json.dumps(mastery, indent = 4, ensure_ascii = False))
                except UnicodeEncodeError:
                    logPrint("召唤师英雄成就文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nSummoner champion mastery text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                else:
                    logPrint('召唤师英雄成就已保存为“%s”。\nSummoner champion mastery is saved as "%s".\n' %(os.path.join(folder, json2name), os.path.join(folder, json2name)))
                jsonfile2.close()
                currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                pkl2name = "Intermediate Object - mastery (Champion Mastery) - %s (%s).pkl" %(displayName, currentTime)
                #with open(os.path.join(folder, pkl2name), "wb") as IntObj2:
                    #pickle.dump(mastery, IntObj2)
                mastery_header = {"championId": "英雄序号", "championLevel": "成就等级", "championPoints": "总成就点数", "championPointsSinceLastLevel": "当前等级成就点数", "championPointsUntilNextLevel": "升级所需成就点数", "championSeasonMilestone": "当前赛季英雄成就里程点", "chestGranted": "已赚取海克斯宝箱", "highestGrade": "当前赛季最高评分", "lastPlayTime": "上次使用时间戳", "markRequiredForNextLevel": "下一级成就所需英雄成就标记个数", "milestoneGrades": "已取得的对局评价", "puuid": "玩家通用唯一识别码", "tokensEarned": "成就代币数量", "champion": "英雄", "alias": "代号", "lastPlayDate": "上次使用时间", "championSquarePortrait": "英雄方块图像", "nextSeasonMilestoneBonus": "已达到IV级里程碑", "nextSeasonMilestoneRequireGrade": "下个里程点所需对局评价", "nextSeasonMilestoneRewardMarks": "下个里程点奖励英雄成就标记个数", "nextSeasonMilestoneMaximumReward": "下个里程点最大奖励次数", "nextSeasonMilestoneRewardValue": "下个里程点奖励物品序号"}
                mastery_header_keys = list(mastery_header.keys())
                mastery_data = {}
                for i in range(len(mastery_header)):
                    key = mastery_header_keys[i]
                    mastery_data[key] = []
                for mastery_iter in mastery:
                    for i in range(len(mastery_header)):
                        key = mastery_header_keys[i]
                        if i <= 15:
                            if i == 6: #已赚取海克斯宝箱（`chestGranted`）
                                mastery_data[key].append(mastery_iter.get("chestGranted", False)) #外服的英雄成就接口中没有“chestGranted”这个键（Champion mastery API in Riot servers don't include the key "chestGranted"）
                            elif i == 13: #英雄（`champion`）
                                mastery_data[key].append(LoLChampions[mastery_iter["championId"]]["name"])
                            elif i == 14: #代号（`alias`）
                                mastery_data[key].append(LoLChampions[mastery_iter["championId"]]["alias"])
                            elif i == 15: #上次使用时间（`lastPlayDate`）
                                lastPlayTime = time.localtime(mastery_iter["lastPlayTime"] // 1000) #英雄联盟中的时间戳精确到微妙，也就是放大了1000倍（Timestamps in LCU API are accurate to milliseconds, namely multiplied by 1000）
                                lastPlayDate = time.strftime("%Y年%m月%d日%H:%M:%S", lastPlayTime) #这里需要将时间戳转换为标准格式的时间（Here the timestamp is going to be converted into time in standard format）
                                mastery_data[key].append(lastPlayDate)
                            else:
                                mastery_data[key].append(mastery_iter[key])
                        elif i == 16: #英雄方块图像（`championSquarePortrait`）
                            mastery_data[key].append(urljoin(connection.address, LoLChampions[mastery_iter["championId"]]["squarePortraitPath"]))
                        elif i >= 17 and i <= 19:
                            if i == 17: #已达到Ⅳ级里程碑（`nextSeasonMilestoneBonus`）
                                mastery_data[key].append(mastery_iter["nextSeasonMilestone"]["bonus"])
                            elif i == 18: #下个里程点所需对局评价（`nextSeasonMilestoneRequireGrade`）
                                mastery_data[key].append(mastery_iter["nextSeasonMilestone"]["requireGradeCounts"])
                            else: #下个里程点奖励英雄成就标记个数（`nextSeasonMilestoneRewardMarks`）
                                mastery_data[key].append(mastery_iter["nextSeasonMilestone"]["rewardMarks"])
                        else:
                            if i == 20: #下个里程点最大奖励次数（`nextSeasonMilestoneMaximumReward`）
                                mastery_data[key].append(mastery_iter["nextSeasonMilestone"]["rewardConfig"]["maximumReward"])
                            else: #下个里程点奖励物品序号（`nextSeasonMilestoneRewardValue`）
                                mastery_data[key].append(mastery_iter["nextSeasonMilestone"]["rewardConfig"]["rewardValue"])
                mastery_statistics_output_order = [13, 14, 1, 2, 3, 4, 9, 12, 6, 7, 5, 17, 10, 18, 19, 20, 21, 15]
                mastery_data_organized = {}
                for i in mastery_statistics_output_order:
                    key = mastery_header_keys[i]
                    mastery_data_organized[key] = mastery_data[key]
                mastery_df = pandas.DataFrame(data = mastery_data_organized)
                for column in mastery_df:
                    if mastery_df[column].dtype == "bool":
                        mastery_df[column] = mastery_df[column].astype(str)
                        for i in range(len(mastery_df)):
                            mastery_df.loc[i, column] = "√" if mastery_df[column][i] == "True" else ""
                mastery_df = pandas.concat([pandas.DataFrame([mastery_header])[mastery_df.columns], mastery_df], ignore_index = True)
                mastery_web_display_order = [16, 1, 2, 3, 4, 9, 12, 6, 7, 5, 17, 10, 18, 19, 20, 21, 15]
                mastery_data_organized_web = {}
                for i in mastery_web_display_order:
                    key = mastery_header_keys[i]
                    mastery_data_organized_web[key] = mastery_data[key]
                mastery_df_web = pandas.DataFrame(data = mastery_data_organized_web)
                for column in mastery_df_web:
                    if mastery_df_web[column].dtype == "bool":
                        mastery_df_web[column] = mastery_df_web[column].astype(str)
                        for i in range(len(mastery_df_web)):
                            mastery_df_web.loc[i, column] = "√" if mastery_df_web[column][i] == "True" else ""
                mastery_df_web = pandas.concat([pandas.DataFrame([mastery_header])[mastery_df_web.columns], mastery_df_web], ignore_index = True)
                mastery_htmltable = mastery_df_web.to_html(escape = False)

                if "errorCode" in ranked and ranked["httpStatus"] == 404: #从13.15版本开始，国服体验服的排位信息和对局记录可以正常查询（From Patch 13.15 on, rank data and match history can be searched on Chinese PBE server）
                    logPrint("该服务器暂不支持排位数据和对局记录查询！\nThis server doesn't support ranked data and match history lookup!")
                    logPrint("是否导出以上召唤师数据至Excel中？（输入任意键导出，否则不导出）\nDo you want to export the above data into Excel? (Press any key to export or null to refuse exporting)")
                    export_str = logInput()
                    export = bool(export_str)
                    if export:
                        excel_name = "Summoner Profile - " + displayName + ".xlsx"
                        wbPath = os.path.join(folder, excel_name)
                        while True:
                            try:
                                with pandas.ExcelWriter(path = wbPath) as writer:
                                    info_df.to_excel(excel_writer = writer, sheet_name = "Profile")
                                    mastery_df.to_excel(excel_writer = writer, sheet_name = "Champion Mastery")
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            except FileNotFoundError:
                                os.makedirs(folder, exist_ok = True)
                            else:
                                break
                    continue
                    
                #logPrint("召唤师排位数据如下：\nSummoner ranked data are as follows:") #排位赛部分数据位于召唤师信息中（Part of ranked data are in Profile Sheet）
                #logPrint(ranked)
                json3name = "Ranked Data - " + displayName + ".json"
                while True:
                    try:
                        jsonfile3 = open(os.path.join(folder, json3name), "w", encoding = "utf-8")
                    except FileNotFoundError:
                        os.makedirs(folder, exist_ok = True)
                    else:
                        break
                try:
                    jsonfile3.write(json.dumps(ranked, indent = 4, ensure_ascii = False))
                except UnicodeEncodeError:
                    logPrint("召唤师排位数据文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nSummoner ranked data text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                else:
                    logPrint('召唤师排位数据已保存为“%s”。\nSummoner ranked data are saved as "%s".\n' %(os.path.join(folder, json3name), os.path.join(folder, json3name)))
                jsonfile3.close()
                currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                pkl3name = "Intermediate Object - ranked (Rank) - %s (%s).pkl" %(displayName, currentTime)
                #with open(os.path.join(folder, pkl3name), "wb") as IntObj3:
                    #pickle.dump(ranked, IntObj3)
                ranked_header = {"division": "分级", "highestDivision": "当前赛季最高段位分级", "highestTier": "当前赛季最高段位", "isProvisional": "定位中", "leaguePoints": "胜点", "losses": "负场", "miniSeriesProgress": "定位赛/晋级赛进展", "previousSeasonEndDivision": "过往赛季结束段位分级", "previousSeasonEndTier": "过往赛季结束段位", "previousSeasonHighestDivision": "过往赛季最高段位分级", "previousSeasonHighestTier": "过往赛季最高段位", "provisionalGameThreshold": "总定位场次", "provisionalGamesRemaining": "剩余定位场次", "queueType": "对局类型", "ratedRating": "排名分", "ratedTier": "段位", "tier": "段位", "warnings": "警告消息", "wins": "胜场", "tier / ratedTier": "段位", "leaguePoints / ratedRating": "胜点"} #ratedRating也可译为战力积分（ratedRating can be expressed as GR）
                ranked_header_keys = list(ranked_header.keys())
                ranked_data = {}
                for i in range(len(ranked_header_keys)):
                    key = ranked_header_keys[i]
                    ranked_data[key] = []
                for i in range(len(ranked["queues"])):
                    queue = ranked["queues"][i]
                    for j in range(len(ranked_header_keys)):
                        key = ranked_header_keys[j]
                        if j in {0, 1, 7, 9}: #段位分级相关键（Division-related keys）
                            ranked_data[key].append("" if queue[key] == "NA" else queue[key])
                        elif j in {2, 8, 10, 16}: #段位相关键（Tier-related keys）
                            ranked_data[key].append(tiers[queue[key]])
                        elif j == 13: #对局类型（`queueType`）
                            ranked_data[key].append(queueTypes[queue[key]])
                        elif j == 15: #云顶之弈狂暴模式段位（`ratedTier`）
                            ranked_data[key].append(ratedTiers[queue[key]])
                        elif j == 19 or j == 20:
                            if j == 19: #综合段位（`tier / ratedTier`）
                                ranked_data[key].append(ratedTiers[queue["ratedTier"]] if queue["queueType"] == "RANKED_TFT_TURBO" else tiers[queue["tier"]])
                            else: #综合胜点（`leaguePoints / ratedRating`）
                                ranked_data[key].append(queue["ratedRating"] if queue["queueType"] == "RANKED_TFT_TURBO" else queue["leaguePoints"])
                        else:
                            ranked_data[key].append(queue[key])
                ranked_statistics_output_order = [13, 19, 0, 20, 18, 5, 3, 11, 12, 6, 2, 1, 8, 7, 10, 9, 17]
                ranked_data_organized = {}
                for i in ranked_statistics_output_order:
                    key = ranked_header_keys[i]
                    ranked_data_organized[key] = ranked_data[key]
                ranked_df = pandas.DataFrame(data = ranked_data_organized)
                for column in ranked_df:
                    if ranked_df[column].dtype == "bool":
                        ranked_df[column] = ranked_df[column].astype(str)
                        for i in range(len(ranked_df)):
                            ranked_df.loc[i, column] = "√" if ranked_df[column][i] == "True" else ""
                ranked_df = pandas.concat([pandas.DataFrame([ranked_header])[ranked_df.columns], ranked_df], ignore_index = True)
                ranked_htmltable = ranked_df.to_html(escape = False)
                
                #logPrint("召唤师所在赛段天梯数据如下：\nSummoner league ladders data are as follows:")
                ladders = await (await connection.request("GET", f"/lol-ranked/v1/league-ladders/{current_puuid}")).json()
                json4name = "Ranked Ladders - " + displayName + ".json"
                while True:
                    try:
                        jsonfile4 = open(os.path.join(folder, json4name), "w", encoding = "utf-8")
                    except FileNotFoundError:
                        os.makedirs(folder, exist_ok = True)
                    else:
                        break
                try:
                    jsonfile4.write(json.dumps(ladders, indent = 4, ensure_ascii = False))
                except UnicodeEncodeError:
                    logPrint("召唤师排位天梯数据文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nSummoner league ladder data text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                else:
                    logPrint('召唤师排位天梯数据已保存为“%s”。\nSummoner league ladder data are saved as "%s".\n' %(os.path.join(folder, json4name), os.path.join(folder, json4name)))
                jsonfile4.close()
                currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                pkl4name = "Intermediate Object - ranked (Rank) - %s (%s).pkl" %(displayName, currentTime)
                #with open(os.path.join(folder, pkl4name), "wb") as IntObj3:
                    #pickle.dump(ladders, IntObj3)
                ladders_header = {"queueType": "战区", "division": "当前分级", "earnedRegaliaRewardIds": "已获得的段位奖励物品序号", "isProvisional": "定位中", "leaguePoints": "胜点", "losses": "负场", "miniseriesResults": "晋升赛结果", "pendingDemotion": "即将降级", "pendingPromotion": "即将晋级", "position": "当前位次", "positionDelta": "位次变化", "previousPosition": "过往位次", "previousSeasonEndDivision": "过往赛季结束段位分级", "previousSeasonEndTier": "过往赛季结束段位", "provisionalGamesRemaining": "剩余定位场次", "puuid": "玩家通用唯一识别码", "rankedRegaliaLevel": "华甲等级", "summonerId": "召唤师序号", "summonerName": "召唤师名", "tier": "当前段位", "wins": "胜场", "gameName": "玩家昵称", "tagLine": "昵称编号", "mark": "本人标记"}
                ladders_header_keys = list(ladders_header.keys())
                ladders_data = {}
                for i in range(len(ladders_header_keys)):
                    key = ladders_header_keys[i]
                    ladders_data[key] = []
                standings_count = 0
                for ladder in ladders:
                    for division in ladder["divisions"]:
                        standings_count += len(division["standings"])
                if standings_count > 1000:
                    logPrint(f"即将整理{standings_count}名玩家的信息。是否继续？（输入任意键继续，否则不整理）\nInformation of {standings_count} player(s) is going to be sorted out. Do you want to continue? (Submit any non-empty string to continue or null to refuse)")
                    ladder_sort_str = logInput()
                    ladder_sort = bool(ladder_sort_str)
                else:
                    ladder_sort = True
                if ladder_sort:
                    for i in range(len(ladders)):
                        ladder = ladders[i]
                        for j in range(len(ladder["divisions"])):
                            division = ladder["divisions"][j]
                            for k in range(len(division["standings"])):
                                standing = division["standings"][k]
                                standing_summoner_recapture = 0
                                standing_summoner = await get_info(connection, standing["puuid"])
                                while not standing_summoner["info_got"] and standing_summoner["body"]["httpStatus"] != 404 and standing_summoner_recapture < 3:
                                    logPrint(standing_summoner["message"])
                                    standing_summoner_recapture += 1
                                    logPrint("顶级%s%s玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of top %s %s player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d" %(queueTypes[ladder["queueType"]], tiers_all[ladder["tier"]], standing["puuid"], standing_summoner_recapture, queueTypes[ladder["queueType"]], tiers_all[ladder["tier"]], standing["puuid"], standing_summoner_recapture))
                                    standing_summoner = await get_info(connection, standing["puuid"])
                                if not standing_summoner["info_got"]:
                                    logPrint(standing_summoner["message"])
                                    logPrint("顶级%s%s玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of top %s %s player (puuid: %s) capture failed!" %(queueTypes[ladder["queueType"]], tiers_all[ladder["tier"]], standing["puuid"], queueTypes[ladder["queueType"]], tiers_all[ladder["tier"]], standing["puuid"]))
                                for l in range(len(ladders_header_keys)):
                                    key = ladders_header_keys[l]
                                    if l == 0:
                                        ladders_data[key].append(queueTypes[ladder["queueType"]])
                                    elif l <= 20:
                                        if l == 1 or l == 12:
                                            ladders_data[key].append("") if standing[key] == "NA" else ladders_data[key].append(standing[key])
                                        elif l == 13 or l == 19:
                                            ladders_data[key].append(tiers[standing[key]])
                                        else:
                                            ladders_data[key].append(standing[key])
                                    elif l <= 22:
                                        ladders_data[key].append(standing_summoner["body"][key] if standing_summoner["info_got"] else "")
                                    else:
                                        ladders_data[key].append("☆" if standing_summoner["info_got"] and standing_summoner["body"]["puuid"] == current_puuid else "")
                                logPrint("顶级%s%s玩家信息整理进度（Top %s %s player information sorting process）：[%d/%d][%d/%d][%d/%d]" %(queueTypes[ladder["queueType"]], tiers_all[ladder["tier"]], ladder["queueType"], ladder["tier"], i + 1, len(ladders), j + 1, len(ladder["divisions"]), k + 1, len(division["standings"])), end = "\r")
                    else: #为了使得整理完成时能够输出完整的信息，因此需要重新在终端中输出一次进度信息（To make sure the progress information is printed out completely when the sorting is done, this line is needed to print the progress information again in terminal）
                        if standings_count > 0:
                            print("顶级%s%s玩家信息整理进度（Top %s %s player information sorting process）：[%d/%d][%d/%d][%d/%d]" %(queueTypes[ladder["queueType"]], tiers_all[ladder["tier"]], ladder["queueType"], ladder["tier"], i + 1, len(ladders), j + 1, len(ladder["divisions"]), k + 1, len(division["standings"])))
                ladders_statistics_output_order = [0, 9, 11, 10, 17, 15, 18, 21, 22, 19, 1, 4, 3, 14, 8, 7, 6, 20, 5, 13, 12, 2, 16, 23]
                ladders_web_display_order = [0, 9, 11, 10, 17, 15, 18, 21, 22, 19, 1, 4, 3, 14, 8, 7, 6, 20, 5, 13, 12, 2, 16, 23]
                ladders_data_organized = {}
                for i in ladders_statistics_output_order:
                    key = ladders_header_keys[i]
                    ladders_data_organized[key] = ladders_data[key]
                ladders_df = pandas.DataFrame(data = ladders_data_organized)
                for column in ladders_df:
                    if ladders_df[column].dtype == "bool":
                        ladders_df[column] = ladders_df[column].astype(str)
                        for i in range(len(ladders_df)):
                            ladders_df.loc[i, column] = "√" if ladders_df[column][i] == "True" else ""
                ladders_df = pandas.concat([pandas.DataFrame([ladders_header])[ladders_df.columns], ladders_df], ignore_index = True)
                ladders_htmltable = ladders_df.to_html(escape = False)
                
                # game_leaderboard_dfs = {}
                game_info_dfs = {}
                game_timeline_dfs = {}
                game_event_dfs = {}
                LoLHistory_searched = True
                TFTHistory_searched = True
                info_exist_error = {} #当获取对局记录反复出现异常时，为了保证第二次没有获取到的报错信息在导出时不会覆盖上一次使用该程序时导出的正确工作表，设置该列表。列表中的某个元素为True，代表对应的对局记录将能正常导出。由于对局信息往往比对局时间轴更易接受关注，这里只以LoLGame_info的完整性作为exist_error的追加依据（When the match history service encounters errors frequently, to make sure the error information won't overlay the normally captured match information in the last time using this program, this list is declared here. When some element in this list is True, the corresponding match information / timeline can be exported as usual. Because the LoLGame_info is basically more focused on than LoLGame_timeline, True/False is appended to exist_error only based on the integrity of LoLGame_info）
                timeline_exist_error = {}
                main_player_included = {} #当通过列表来查询对局记录时，有可能某场对局并不包含该召唤师（When searching the match history using a list, maybe the summoner isn't present in some match）
                match_reserve_strategy = {} #当某场对局不包含该召唤师，或者对局数据异常时，决定最后导出时是否需要保存该对局记录（Decides whether to reserve the matches when they don't include the searched summoner at present or data in them are lost）
                
                logPrint("是否查询英雄联盟对局记录？（输入任意键查询，否则不查询）\nSearch LoL matches? (Input anything to search or null to skip searching LoL matches)")
                search_LoL_str = logInput()
                search_LoL = bool(search_LoL_str)
                if search_LoL:
                    #logPrint("召唤师英雄联盟对局记录如下：\nMatch history (LoL) is as follows:")
                    LoLHistory_get = True
                    begIndex_get, endIndex_get = 0, 500
                    while True:
                        try:
                            LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches?begIndex=%d&endIndex=%d" %(info_body["puuid"], begIndex_get, endIndex_get))).json()
                            #logPrint(LoLHistory)
                            error_occurred = False
                            count = 0 #存储内部服务器错误次数（Stores the times of internal server error）
                            if "errorCode" in LoLHistory:
                                if "500 Internal Server Error" in LoLHistory["message"]:
                                    if not error_occurred:
                                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                        occurred = True
                                    while "errorCode" in LoLHistory and "500 Internal Server Error" in LoLHistory["message"] and count <= 3: #在查询艾欧尼亚和黑色玫瑰大区的对局记录时，有时会产生如下报错：An error when looking up match history on HN1 and HN10 servers might occur as follows: {'errorCode': 'RPC_ERROR', 'httpStatus': 500, 'implementationDetails': {}, 'message': 'Failed due to Error deserializing json response for GET https: //hn1-cloud-acs.lol.qq.com/v1/stats/player_history/HN1/2936900903?begIndex=0&endIndex=500: Error: Invalid value. at offset 0. given body <html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body bgcolor="white">\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>nginx/1.10.0</center>\r\n</body>\r\n</html>\r\n'}
                                        count += 1
                                        logPrint("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                                        LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches?begIndex=%d&endIndex=%d" %(info_body["puuid"], begIndex_get, endIndex_get))).json()
                                elif "body was empty" in LoLHistory["message"]:
                                    logPrint("这位召唤师从5月1日起就没有进行过任何英雄联盟对局。\nThis summoner hasn't played any LoL game yet since May 1st.")
                                    break
                            json5name = "Match History (LoL) - " + displayName + ".json"
                            while True:
                                try:
                                    jsonfile5 = open(os.path.join(folder, json5name), "w", encoding = "utf-8")
                                except FileNotFoundError:
                                    os.makedirs(folder, exist_ok = True)
                                else:
                                    break
                            try:
                                jsonfile5.write(json.dumps(LoLHistory, indent = 4, ensure_ascii = False))
                            except UnicodeEncodeError:
                                logPrint("召唤师英雄联盟对局记录文本文档生成失败！请检查召唤师名称和所选语言是否包含不常用字符！\nSummoner LoL match history text generation failure! Please check if the summoner name and the chosen language include any abnormal characters!\n")
                            jsonfile5.close()
                            currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                            pkl5name = "Intermediate Object - LoLHistory - %s (%s).pkl" %(displayName, currentTime)
                            #with open(os.path.join(folder, pkl5name), "wb") as IntObj4:
                                #pickle.dump(LoLHistory, IntObj4)
                            if count > 3:
                                logPrint("英雄联盟对局记录获取失败！请等待官方修复对局记录服务！\nLoL match history capture failure! Please wait for Tencent to fix the match history service!")
                                break
                            logPrint('该玩家共进行%d场英雄联盟对局。近期对局（最近20场）已保存为“%s”。\nThis player has played %d LoL matches. Recent matches (last 20 played) are saved as "%s".\n' %(LoLHistory["games"]["gameCount"], os.path.join(folder, json5name), LoLHistory["games"]["gameCount"], os.path.join(folder, json5name))) #在这里引发键异常（Here may trigger a KeyError）
                        except KeyError:
                            logPrint(LoLHistory)
                            LoLHistory_url = "%s/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=200" %(connection.address, info_body["puuid"])
                            logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续（Please open the following website, type in the username and password accordingly and press Enter to continue）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和上限。\nOr submit two nonnegative integers split by space to respecify the begIndex and endIndex." %(LoLHistory_url, connection.auth_key))
                            cont = logInput()
                            if cont == "":
                                continue
                            else:
                                try:
                                    begIndex_get, endIndex_get = map(int, cont.split())
                                except:
                                    break
                                else:
                                    continue
                        else:
                            LoLHistory_get = True
                            break
                    if not LoLHistory_get:
                        continue
                    LoLGamePlayed = True #标记该玩家是否进行过英雄联盟对局（Mark whether this summoner has played any LoL game）
                    LoLHistory_header = {"gameIndex": "游戏序号", "endOfGameResult": "对局终止情况", "gameCreation": "对局创建时间戳", "gameCreationDate": "对局创建日期", "gameDuration": "持续时长（秒）", "gameId": "对局序号", "gameMode": "游戏模式", "gameModeMutators": "游戏模式配置", "gameType": "游戏类型", "gameVersion": "对局版本", "mapId": "地图序号", "queueId": "队列序号", "seasonId": "赛季序号", "gameDuration_norm": "持续时长", "gameModeName": "游戏模式名称", "accountId": "帐户序号", "currentAccountId": "当前帐户序号", "currentPlatformId": "当前服务器代码", "gameName": "玩家昵称", "matchHistoryUri": "对局记录网址", "platformId": "服务器代码", "profileIcon": "召唤师图标序号", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "tagLine": "昵称编号", "profileIcon_title": "召唤师图标名称", "profileIcon_imagePath": "召唤师图标路径", "championId": "英雄序号", "highestAchievedSeasonTier": "最高段位", "participantId": "玩家序号", "spell1Id": "召唤师技能1序号", "spell2Id": "召唤师技能2序号", "teamId": "阵营代号", "champion_name": "英雄", "champion_alias": "代号", "champion_squarePortraitPath": "方块头像路径", "spell1_name": "召唤师技能1", "spell2_name": "召唤师技能2", "spell1_iconPath": "召唤师技能1图标", "spell2_iconPath": "召唤师技能2图标", "team_color": "阵营", "assists": "助攻", "causedEarlySurrender": "发起提前投降", "champLevel": "英雄等级", "combatPlayerScore": "战斗得分", "damageDealtToObjectives": "对战略点的总伤害", "damageDealtToTurrets": "对防御塔的总伤害", "damageSelfMitigated": "自我缓和的伤害", "deaths": "死亡", "doubleKills": "双杀", "earlySurrenderAccomplice": "同意提前投降", "firstBloodAssist": "协助获得第一滴血", "firstBloodKill": "第一滴血", "firstInhibitorAssist": "协助摧毁第一座召唤水晶", "firstInhibitorKill": "摧毁第一座召唤水晶", "firstTowerAssist": "协助摧毁第一座塔", "firstTowerKill": "摧毁第一座塔", "gameEndedInEarlySurrender": "提前投降导致比赛结束", "gameEndedInSurrender": "投降导致比赛结束", "goldEarned": "金币", "goldSpent": "金币使用", "inhibitorKills": "摧毁召唤水晶", "item0": "装备1序号", "item1": "装备2序号", "item2": "装备3序号", "item3": "装备4序号", "item4": "装备5序号", "item5": "装备6序号", "item6": "饰品序号", "killingSprees": "大杀特杀", "kills": "击杀", "largestCriticalStrike": "最大暴击伤害", "largestKillingSpree": "最高连杀", "largestMultiKill": "最高多杀", "longestTimeSpentLiving": "最长生存时间", "magicDamageDealt": "造成的魔法伤害", "magicDamageDealtToChampions": "对英雄的魔法伤害", "magicalDamageTaken": "承受的魔法伤害", "neutralMinionsKilled": "击杀野怪", "neutralMinionsKilledEnemyJungle": "击杀敌方野区野怪", "neutralMinionsKilledTeamJungle": "击杀我方野区野怪", "objectivePlayerScore": "战略点玩家得分", "pentaKills": "五杀", "perk0": "符文1序号", "perk0Var1": "符文1：参数1", "perk0Var2": "符文1：参数2", "perk0Var3": "符文1：参数3", "perk1": "符文2序号", "perk1Var1": "符文2：参数1", "perk1Var2": "符文2：参数2", "perk1Var3": "符文2：参数3", "perk2": "符文3序号", "perk2Var1": "符文3：参数1", "perk2Var2": "符文3：参数2", "perk2Var3": "符文3：参数3", "perk3": "符文4序号", "perk3Var1": "符文4：参数1", "perk3Var2": "符文4：参数2", "perk3Var3": "符文4：参数3", "perk4": "符文5序号", "perk4Var1": "符文5：参数1", "perk4Var2": "符文5：参数2", "perk4Var3": "符文5：参数3", "perk5": "符文6序号", "perk5Var1": "符文6：参数1", "perk5Var2": "符文6：参数2", "perk5Var3": "符文6：参数3", "perkPrimaryStyle": "主系序号", "perkSubStyle": "副系序号", "physicalDamageDealt": "造成的物理伤害", "physicalDamageDealtToChampions": "对英雄的物理伤害", "physicalDamageTaken": "承受的物理伤害", "playerAugment1": "强化符文1", "playerAugment2": "强化符文2", "playerAugment3": "强化符文3", "playerAugment4": "强化符文4", "playerAugment5": "强化符文5", "playerAugment6": "强化符文6", "playerScore0": "玩家得分1", "playerScore1": "玩家得分2", "playerScore2": "玩家得分3", "playerScore3": "玩家得分4", "playerScore4": "玩家得分5", "playerScore5": "玩家得分6", "playerScore6": "玩家得分7", "playerScore7": "玩家得分8", "playerScore8": "玩家得分9", "playerScore9": "玩家得分10", "playerSubteamId": "子阵营代号", "quadraKills": "四杀", "sightWardsBoughtInGame": "购买洞察之石", "subteamPlacement": "队伍排名", "teamEarlySurrendered": "队伍提前投降", "timeCCingOthers": "控制得分", "totalDamageDealt": "造成的伤害总和", "totalDamageDealtToChampions": "对英雄的伤害总和", "totalDamageTaken": "承受伤害", "totalHeal": "输出治疗效果", "totalMinionsKilled": "击杀小兵", "totalPlayerScore": "玩家总得分", "totalScoreRank": "总得分排名", "totalTimeCrowdControlDealt": "控制时间", "totalUnitsHealed": "治疗单位数", "tripleKills": "三杀", "trueDamageDealt": "造成真实伤害", "trueDamageDealtToChampions": "对英雄的真实伤害", "trueDamageTaken": "承受的真实伤害", "turretKills": "摧毁防御塔", "unrealKills": "六杀及以上", "visionScore": "视野得分", "visionWardsBoughtInGame": "购买控制守卫", "wardsKilled": "摧毁守卫", "wardsPlaced": "放置守卫", "win": "胜利", "item0_name": "装备1", "item1_name": "装备2", "item2_name": "装备3", "item3_name": "装备4", "item4_name": "装备5", "item5_name": "装备6", "item6_name": "饰品", "item0_iconPath": "装备1图标路径", "item1_iconPath": "装备2图标路径", "item2_iconPath": "装备3图标路径", "item3_iconPath": "装备4图标路径", "item4_iconPath": "装备5图标路径", "item5_iconPath": "装备6图标路径", "item6_iconPath": "饰品图标路径", "perk0EndOfGameStatDescs": "符文1游戏结算数据", "perk1EndOfGameStatDescs": "符文2游戏结算数据", "perk2EndOfGameStatDescs": "符文3游戏结算数据", "perk3EndOfGameStatDescs": "符文4游戏结算数据", "perk4EndOfGameStatDescs": "符文5游戏结算数据", "perk5EndOfGameStatDescs": "符文6游戏结算数据", "perk0_name": "符文1名称", "perk1_name": "符文2名称", "perk2_name": "符文3名称", "perk3_name": "符文4名称", "perk4_name": "符文5名称", "perk5_name": "符文6名称", "perk0_iconPath": "符文1图标路径", "perk1_iconPath": "符文2图标路径", "perk2_iconPath": "符文3图标路径", "perk3_iconPath": "符文4图标路径", "perk4_iconPath": "符文5图标路径", "perk5_iconPath": "符文6图标路径", "perkPrimaryStyle_name": "主系名称", "perkPrimaryStyle_iconPath": "主系图标路径", "perkSubStyle_name": "副系名称", "perkSubStyle_iconPath": "副系图标路径", "playerAugment1_nameTRA": "强化符文1名称", "playerAugment2_nameTRA": "强化符文2名称", "playerAugment3_nameTRA": "强化符文3名称", "playerAugment4_nameTRA": "强化符文4名称", "playerAugment5_nameTRA": "强化符文5名称", "playerAugment6_nameTRA": "强化符文6名称", "playerAugment1_augmentIconPath": "强化符文1图标路径", "playerAugment2_augmentIconPath": "强化符文2图标路径", "playerAugment3_augmentIconPath": "强化符文3图标路径", "playerAugment4_augmentIconPath": "强化符文4图标路径", "playerAugment5_augmentIconPath": "强化符文5图标路径", "playerAugment6_augmentIconPath": "强化符文6图标路径", "playerAugment1_rarity": "强化符文1等级", "playerAugment2_rarity": "强化符文2等级", "playerAugment3_rarity": "强化符文3等级", "playerAugment4_rarity": "强化符文4等级", "playerAugment5_rarity": "强化符文5等级", "playerAugment6_rarity": "强化符文6等级", "playerSubteamColor": "子阵营", "K/D/A": "击杀/死亡/助攻", "KDA": "战损比", "CS": "补刀", "GPM": "分均经济", "GUE": "金币利用率", "CSPM": "分均补刀", "D/G": "伤害转化率", "result": "结果", "lane": "分路", "role": "角色定位"}
                    LoLHistory_header_keys = list(LoLHistory_header.keys())
                    LoLHistory_data = {}
                    games = LoLHistory["games"]["games"]
                    versions = [] #该变量并不是用来呈现在Excel中的，而是用来存储不同装备的合适版本的信息（This variable isn't intended to be displyed in the Excel Sheets. Instead, it stores information of appropriate patches of different patches）
                    if len(games) == 0:
                        LoLGamePlayed = False
                    for i in range(len(LoLHistory_header_keys)):
                        key = LoLHistory_header_keys[i]
                        LoLHistory_data[key] = []
                    for i in range(len(games)):
                        game = games[i]
                        version = game["gameVersion"]
                        bigVersion = ".".join(version.split(".")[:2])
                        stats = game["participants"][0]["stats"]
                        timeline = game["participants"][0]["timeline"]
                        try: #这一部分语句无关紧要（This piece of statements doesn't matter）
                            versions.append(patches_dict[bigVersion][0])
                        except KeyError: #有可能存在美测服的临时版本未收录到DataDragon数据库中。详见patch_compare函数的注释（Possibly an intermediate patch on PBE isn't archived in DataDragon database. More details in the annotation of `patch_compare` function）
                            if patch_compare(bigVersion, latest_patch):
                                patches_dict[bigVersion] = [FindPostPatch(version, patches)]
                            else:
                                patches_dict[bigVersion] = [latest_patch]
                            versions.append(patches_dict[bigVersion][0])
                        #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                        ##召唤师图标（Summoner icon）
                        summonerIconIds_match_list = sorted(set(map(lambda x: x["player"]["profileIcon"], game["participantIdentities"])))
                        for j in summonerIconIds_match_list:
                            if not j in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                                summonerIconPatch_adopted = bigVersion
                                summonerIcon_recapture = 1
                                logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, summonerIcon_recapture, summonerIconPatch_adopted, j, i + 1, len(games), game["gameId"], summonerIconPatch_adopted, summonerIcon_recapture))
                                while True:
                                    try:
                                        summonerIcon = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[language_code])).json()
                                    except requests.exceptions.JSONDecodeError:
                                        summonerIconPatch_deserted = summonerIconPatch_adopted
                                        summonerIconPatch_adopted = FindPostPatch(summonerIconPatch_adopted, bigPatches)
                                        summonerIcon_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture))
                                    except requests.exceptions.RequestException:
                                        if summonerIcon_recapture < 3:
                                            summonerIcon_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture))
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]))
                                            break
                                    else:
                                        logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted))
                                        summonerIcons = {}
                                        for summonerIcon_iter in summonerIcon:
                                            summonerIcon_id = summonerIcon_iter["id"]
                                            summonerIcons[summonerIcon_id] = summonerIcon_iter
                                        current_versions["summonerIcon"] = summonerIconPatch_adopted
                                        unmapped_keys["summonerIcon"].clear()
                                        break
                                break #切换版本只需一次即可。如果对局版本还不对，那就不用再找下去了（The version of data resources only needs changing once. If data resources of the version of this match don't match all the game data, then there's no need of retrying）
                        ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
                        LoLChampionIds_match_list = sorted(set(map(lambda x: x["championId"], game["participants"])))
                        for j in LoLChampionIds_match_list:
                            if not j in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                                LoLChampionPatch_adopted = bigVersion
                                LoLChampion_recapture = 1
                                logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, LoLChampion_recapture, LoLChampionPatch_adopted, j, i + 1, len(games), game["gameId"], LoLChampionPatch_adopted, LoLChampion_recapture))
                                while True:
                                    try:
                                        LoLChampion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[language_code])).json()
                                    except requests.exceptions.JSONDecodeError:
                                        LoLChampionPatch_deserted = LoLChampionPatch_adopted
                                        LoLChampionPatch_adopted = FindPostPatch(LoLChampionPatch_adopted, bigPatches)
                                        LoLChampion_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture))
                                    except requests.exceptions.RequestException:
                                        if LoLChampion_recapture < 3:
                                            LoLChampion_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture))
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]))
                                            break
                                    else:
                                        logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted))
                                        LoLChampions = {}
                                        for LoLChampion_iter in LoLChampion:
                                            LoLChampion_id = LoLChampion_iter["id"]
                                            LoLChampions[LoLChampion_id] = LoLChampion_iter
                                        current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                        unmapped_keys["LoLChampion"].clear() #切换版本时，未对应的键应当清空。下同（When the version is switched, the unmapped keys should be cleared. This applies to other data resources）
                                        break
                                break
                        ##召唤师技能（Summoner spells）
                        spellIds_match_list = sorted(set(map(lambda x: x["spell1Id"], game["participants"])) | set(map(lambda x: x["spell2Id"], game["participants"])))
                        for j in spellIds_match_list:
                            if not j in spells and current_versions["spell"] != bigVersion and j != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                                spellPatch_adopted = bigVersion
                                spell_recapture = 1
                                logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, spell_recapture, spellPatch_adopted, j, i + 1, len(games), game["gameId"], spellPatch_adopted, spell_recapture))
                                while True:
                                    try:
                                        spell = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[language_code])).json()
                                    except requests.exceptions.JSONDecodeError:
                                        spellPatch_deserted = spellPatch_adopted
                                        spellPatch_adopted = FindPostPatch(spellPatch_adopted, bigPatches)
                                        spell_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture))
                                    except requests.exceptions.RequestException:
                                        if spell_recapture < 3:
                                            spell_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture))
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]))
                                            break
                                    else:
                                        logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted))
                                        spells = {}
                                        for spell_iter in spell:
                                            spell_id = spell_iter["id"]
                                            spells[spell_id] = spell_iter
                                        current_versions["spell"] = spellPatch_adopted
                                        unmapped_keys["spell"].clear()
                                        break
                                break
                        ##英雄联盟装备（LoL items）
                        LoLItemIds_match_list = sorted(set(map(lambda x: x["stats"]["item0"], game["participants"])) | set(map(lambda x: x["stats"]["item1"], game["participants"])) | set(map(lambda x: x["stats"]["item2"], game["participants"])) | set(map(lambda x: x["stats"]["item3"], game["participants"])) | set(map(lambda x: x["stats"]["item4"], game["participants"])) | set(map(lambda x: x["stats"]["item5"], game["participants"])) | set(map(lambda x: x["stats"]["item6"], game["participants"])))
                        for j in LoLItemIds_match_list:
                            if not j in LoLItems and current_versions["LoLItem"] != bigVersion and j != 0: #空装备序号是0（The itemId of an empty item is 0）
                                LoLItemPatch_adopted = bigVersion
                                LoLItem_recapture = 1
                                logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, LoLItem_recapture, LoLItemPatch_adopted, j, i + 1, len(games), game["gameId"], LoLItemPatch_adopted, LoLItem_recapture))
                                while True:
                                    try:
                                        LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                                    except requests.exceptions.JSONDecodeError:
                                        LoLItemPatch_deserted = LoLItemPatch_adopted
                                        LoLItemPatch_adopted = FindPostPatch(LoLItemPatch_adopted, bigPatches)
                                        LoLItem_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                                    except requests.exceptions.RequestException:
                                        if LoLItem_recapture < 3:
                                            LoLItem_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]))
                                            break
                                    else:
                                        logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted))
                                        LoLItems = {}
                                        for LoLItem_iter in LoLItem:
                                            LoLItem_id = LoLItem_iter["id"]
                                            LoLItems[LoLItem_id] = LoLItem_iter
                                        current_versions["LoLItem"] = LoLItemPatch_adopted
                                        unmapped_keys["LoLItem"].clear()
                                        break
                                break
                        ##符文（Perks）
                        perkIds_match_list = sorted(set(perk for s in [set(map(lambda x: x["stats"]["perk" + str(i)], game["participants"])) for i in range(6)] for perk in s))
                        for j in perkIds_match_list:
                            if not j in perks and current_versions["perk"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                perkPatch_adopted = bigVersion
                                perk_recapture = 1
                                logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, perk_recapture, perkPatch_adopted, j, i + 1, len(games), game["gameId"], perkPatch_adopted, perk_recapture))
                                while True:
                                    try:
                                        perk = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[language_code])).json()
                                    except requests.exceptions.JSONDecodeError:
                                        perkPatch_deserted = perkPatch_adopted
                                        perkPatch_adopted = FindPostPatch(perkPatch_adopted, bigPatches)
                                        perk_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture))
                                    except requests.exceptions.RequestException:
                                        if perk_recapture < 3:
                                            perk_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture))
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]))
                                            break
                                    else:
                                        logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted))
                                        perks = {}
                                        for perk_iter in perk:
                                            perk_id = perk_iter["id"]
                                            perks[perk_id] = perk_iter
                                        current_versions["perk"] = perkPatch_adopted
                                        unmapped_keys["perk"].clear()
                                        break
                                break
                        ##符文系（Perkstyles）
                        perkstyleIds_match_list = sorted(list(set(map(lambda x: x["stats"]["perkPrimaryStyle"], game["participants"])) | set(map(lambda x: x["stats"]["perkSubStyle"], game["participants"]))))
                        for j in perkstyleIds_match_list:
                            if not j in perkstyles and current_versions["perkstyle"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                perkstylePatch_adopted = bigVersion
                                perkstyle_recapture = 1
                                logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, perkstyle_recapture, perkstylePatch_adopted, j, i + 1, len(games), game["gameId"], perkstylePatch_adopted, perkstyle_recapture))
                                while True:
                                    try:
                                        perkstyle = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[language_code])).json()
                                    except requests.exceptions.JSONDecodeError:
                                        perkstylePatch_deserted = perkstylePatch_adopted
                                        perkstylePatch_adopted = FindPostPatch(perkstylePatch_adopted, bigPatches)
                                        perkstyle_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture))
                                    except requests.exceptions.RequestException:
                                        if perkstyle_recapture < 3:
                                            perkstyle_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture))
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]))
                                            break
                                    else:
                                        logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted))
                                        perkstyles = {}
                                        for perkstyle_iter in perkstyle["styles"]:
                                            perkstyle_id = perkstyle_iter["id"]
                                            perkstyles[perkstyle_id] = perkstyle_iter
                                        current_versions["perkstyle"] = perkstylePatch_adopted
                                        unmapped_keys["perkstyle"].clear()
                                        break
                                break
                        ##斗魂竞技场强化符文（Cherry augments）
                        CherryAugmentIds_match_list = sorted(set(augment for s in [set(map(lambda x: x["stats"]["playerAugment" + str(i)], game["participants"])) for i in range(1, 7)] for augment in s))
                        for j in CherryAugmentIds_match_list:
                            if not j in CherryAugments and current_versions["CherryAugment"] != bigVersion and j != 0:
                                CherryAugmentPatch_adopted = bigVersion
                                CherryAugment_recapture = 1
                                logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], j, CherryAugment_recapture, CherryAugmentPatch_adopted, j, i + 1, len(games), game["gameId"], CherryAugmentPatch_adopted, CherryAugment_recapture))
                                while True:
                                    try:
                                        CherryAugment = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[language_code])).json()
                                    except requests.exceptions.JSONDecodeError:
                                        CherryAugmentPatch_deserted = CherryAugmentPatch_adopted
                                        CherryAugmentPatch_adopted = FindPostPatch(CherryAugmentPatch_adopted, bigPatches)
                                        CherryAugment_recapture = 1
                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                    except requests.exceptions.RequestException:
                                        if CherryAugment_recapture < 3:
                                            CherryAugment_recapture += 1
                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                        else:
                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(games), game["gameId"], j, j, i + 1, len(games), game["gameId"]))
                                            break
                                    else:
                                        logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted))
                                        CherryAugments = {}
                                        for CherryAugment_iter in CherryAugment:
                                            CherryAugment_id = CherryAugment_iter["id"]
                                            CherryAugments[CherryAugment_id] = CherryAugment_iter
                                        current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                        unmapped_keys["CherryAugment"].clear()
                                        break
                                break
                        #下面开始整理数据（Sorts out the data）
                        for j in range(len(LoLHistory_header_keys)):
                            key = LoLHistory_header_keys[j]
                            if j == 0:
                                LoLHistory_data[key].append(i + 1)
                            elif j <= 14:
                                if j == 1: #对局终止情况（`endOfGameResult`）
                                    LoLHistory_data[key].append(endOfGameResults[game["endOfGameResult"]])
                                if j == 3: #对局创建日期（`gameCreationDate`）
                                    LoLHistory_data[key].append(game["gameCreationDate"][:10] + " " + game["gameCreationDate"][11:23])
                                elif j == 8: #游戏类型（`gameType`）
                                    LoLHistory_data[key].append(gameTypes[game[key]])
                                elif j == 13: #持续时长（`gameDuration_norm`）
                                    LoLHistory_data[key].append(str(game["gameDuration"] // 60) + ":" + "%02d" %(game["gameDuration"] % 60))
                                elif j == 14: #游戏模式名称（`gameModeName`）
                                    LoLHistory_data[key].append("自定义" if game["queueId"] == 0 else gamemodes[game["queueId"]]["name"] if game["queueId"] in gamemodes else "")
                                else:
                                    LoLHistory_data[key].append(game[key])
                            elif j <= 27:
                                if j >= 26: #召唤师图标相关键（Summoner icon-related keys）
                                    profileIconId = game["participantIdentities"][0]["player"]["profileIcon"]
                                    if profileIconId in summonerIcons:
                                        try:
                                            LoLHistory_data[key].append(summonerIcons[profileIconId][key.split("_")[-1]])
                                        except KeyError:
                                            traceback_info = traceback.format_exc()
                                            logPrint(traceback_info)
                                            LoLHistory_data[key].append("")
                                    elif profileIconId in summonerIcons_initial:
                                        try:
                                            LoLHistory_data[key].append(summonerIcons_initial[profileIconId][key.split("_")[-1]])
                                        except KeyError:
                                            traceback_info = traceback.format_exc()
                                            logPrint(traceback_info)
                                            LoLHistory_data[key].append("")
                                    else:
                                        if not profileIconId in unmapped_keys["summonerIcon"]:
                                            unmapped_keys["summonerIcon"].add(profileIconId)
                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, profileIconId, j, key, profileIconId, i + 1, len(games), game["gameId"], version))
                                        LoLHistory_data[key].append(profileIconId if j == 26 else "")
                                else:
                                    LoLHistory_data[key].append(game["participantIdentities"][0]["player"][key])
                            elif j <= 41:
                                if j == 29: #最高段位（`highestAchievedSeasonTier`）
                                    LoLHistory_data[key].append(tiers[game["participants"][0]["highestAchievedSeasonTier"]])
                                elif j >= 34 and j <= 36: #英雄相关键（Champion-related keys）
                                    championId = game["participants"][0][key.split("_")[0] + "Id"]
                                    if championId in LoLChampions:
                                        LoLHistory_data[key].append(LoLChampions[championId][key.split("_")[1]])
                                    elif championId in LoLChampions_initial: #一些旧版的键可能出现在最新的数据资源中，而随着程序的进行，程序所使用的数据资源可能并不是最新的，因此再和最新的数据资源做一次比较。这种现象在云顶之弈对局中尤其普遍（Some old-version keys might appear in the latest data resource, while as the program executes, the data resource it uses may not be the latest. Therefore, a lookup in the latest data resource is performed. This phenomenon is especially normal in TFT matches）
                                        LoLHistory_data[key].append(LoLChampions_initial[championId][key.split("_")[1]])
                                    else: #在国服体验服的对局序号为696083511的对局中，出现了英雄序号为37225015（In a match with matchId 696083511 on Chinese PBE, there's a champion with championId 37225015）
                                        if not championId in unmapped_keys["LoLChampion"]:
                                            unmapped_keys["LoLChampion"].add(championId)
                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, championId, j, key, championId, i + 1, len(games), game["gameId"], version))
                                        LoLHistory_data[key].append(championId if j == 34 else "")
                                elif j >= 37 and j <= 40: #召唤师技能相关键（Summoner spell-related keys）
                                    spellId = game["participants"][0][key.split("_")[0] + "Id"]
                                    if spellId in spells:
                                        LoLHistory_data[key].append(spells[spellId][key.split("_")[1]])
                                    elif spellId in spells_initial:
                                        LoLHistory_data[key].append(spells_initial[spellId][key.split("_")[1]])
                                    else:
                                        if not spellId in unmapped_keys["spell"]:
                                            unmapped_keys["spell"].add(spellId)
                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, spellId, j, key, spellId, i + 1, len(games), game["gameId"], version))
                                        LoLHistory_data[key].append(spellId if j <= 38 else "")
                                elif j == 41: #阵营（`team_color`）
                                    LoLHistory_data[key].append(team_color[game["participants"][0]["teamId"]])
                                else:
                                    LoLHistory_data[key].append(game["participants"][0][key])
                            elif j <= 217:
                                if j >= 155 and j <= 168: #英雄联盟装备相关键（LoLItems-related keys）
                                    itemId = stats[key.split("_")[0]]
                                    if itemId == 0:
                                        LoLHistory_data[key].append("")
                                    elif itemId in LoLItems:
                                        LoLHistory_data[key].append(LoLItems[itemId][key.split("_")[-1]])
                                    elif itemId in LoLItems_initial:
                                        LoLHistory_data[key].append(LoLItems_initial[itemId][key.split("_")[-1]])
                                    else:
                                        if not itemId in unmapped_keys["LoLItem"]:
                                            unmapped_keys["LoLItem"].add(itemId)
                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, itemId, j, key, itemId, i + 1, len(games), game["gameId"], version))
                                        LoLHistory_data[key].append(itemId if j <= 161 else "")
                                elif j >= 169 and j <= 186: #符文相关键（Perks-related keys）
                                    if j <= 174:
                                        perkId = stats[key[:5]]
                                        if perkId == 0:
                                            LoLHistory_data[key].append("")
                                        elif perkId in perks:
                                            perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                                            LoLHistory_data[key].append(perk_EndOfGameStatDescs)
                                        elif perkId in perks_initial:
                                            perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks_initial[perkId]["endOfGameStatDescs"])))
                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                                            LoLHistory_data[key].append(perk_EndOfGameStatDescs)
                                        else:
                                            if not perkId in unmapped_keys["perk"]:
                                                unmapped_keys["perk"].add(perkId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, perkId, j, key, perkId, i + 1, len(games), game["gameId"], version))
                                            LoLHistory_data[key].append("")
                                    else:
                                        perkId = stats[key.split("_")[0]]
                                        if perkId == 0:
                                            LoLHistory_data[key].append("")
                                        elif perkId in perks:
                                            LoLHistory_data[key].append(perks[perkId][key.split("_")[-1]])
                                        elif perkId in perks_initial:
                                            LoLHistory_data[key].append(perks_initial[perkId][key.split("_")[-1]])
                                        else:
                                            if not perkId in unmapped_keys["perk"]:
                                                unmapped_keys["perk"].add(perkId)
                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, perkId, j, key, perkId, i + 1, len(games), game["gameId"], version))
                                            LoLHistory_data[key].append(perkId if j <= 180 else "")
                                elif j >= 187 and j <= 190: #符文系相关键（Perkstyles-related keys）
                                    perkstyleId = stats[key.split("_")[0]]
                                    if perkstyleId == 0:
                                        LoLHistory_data[key].append("")
                                    elif perkstyleId in perkstyles:
                                        LoLHistory_data[key].append(perkstyles[perkstyleId][key.split("_")[-1]])
                                    elif perkstyleId in perkstyles_initial:
                                        LoLHistory_data[key].append(perkstyles_initial[perkstyleId][key.split("_")[-1]])
                                    else:
                                        if not perkstyleId in unmapped_keys["perkstyle"]:
                                            unmapped_keys["perkstyle"].add(perkstyleId)
                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, perkstyleId, j, key, perkstyleId, i + 1, len(games), game["gameId"], version))
                                        LoLHistory_data[key].append(perkstyleId if (j - 187) % 2 == 0 else "")
                                elif j >= 191 and j <= 208: #强化符文相关键（Augment-related keys）
                                    CherryAugmentId = stats[key.split("_")[0]]
                                    if CherryAugmentId == 0:
                                        LoLHistory_data[key].append("")
                                    elif CherryAugmentId in CherryAugments:
                                        if j <= 196: #强化符文名称（`nameTRA`）
                                            LoLHistory_data[key].append(CherryAugments[CherryAugmentId][key.split("_")[-1]])
                                        elif j <= 202: #强化符文图标路径（`augmentIconPath`）
                                            LoLHistory_data[key].append(CherryAugments[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png"))
                                        else: #强化符文等级（`rarity`）
                                            LoLHistory_data[key].append(augment_rarity[CherryAugments[CherryAugmentId][key.split("_")[-1]]])
                                    elif CherryAugmentId in CherryAugments_initial:
                                        if j <= 196: #强化符文名称（`nameTRA`）
                                            LoLHistory_data[key].append(CherryAugments_initial[CherryAugmentId][key.split("_")[-1]])
                                        elif j <= 202: #强化符文图标路径（`augmentIconPath`）
                                            LoLHistory_data[key].append(CherryAugments_initial[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png"))
                                        else: #强化符文等级（`rarity`）
                                            LoLHistory_data[key].append(augment_rarity[CherryAugments_initial[CherryAugmentId][key.split("_")[-1]]])
                                    else:
                                        if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                                            unmapped_keys["CherryAugment"].add(CherryAugmentId)
                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(games), game["gameId"], version, CherryAugmentId, j, key, CherryAugmentId, i + 1, len(games), game["gameId"], version))
                                        LoLHistory_data[key].append(CherryAugmentId if j <= 196 else "")
                                elif j == 209: #子阵营（`playerSubteam_color`）
                                    LoLHistory_data[key].append(subteam_color[stats["playerSubteamId"]])
                                elif j == 210: #击杀/死亡/助攻（`K/D/A`）
                                    LoLHistory_data[key].append("/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])]))
                                elif j == 211: #战损比（`KDA`）
                                    LoLHistory_data[key].append((stats["kills"] + stats["assists"]) / max(1, stats["deaths"]))
                                elif j == 212: #补刀（`CS`）
                                    LoLHistory_data[key].append(stats["neutralMinionsKilled"] + stats["totalMinionsKilled"])
                                elif j == 213: #分均经济（`GPM`）
                                    LoLHistory_data[key].append(0 if game["gameDuration"] == 0 else stats["goldEarned"] * 60 / game["gameDuration"])
                                elif j == 214: #金币利用率（`GUE` - Gold Utilization Efficiency）
                                    LoLHistory_data[key].append(0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"])
                                elif j == 215: #分均补刀（`CSPM`）
                                    LoLHistory_data[key].append(0 if game["gameDuration"] == 0 else (stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]) * 60 / game["gameDuration"])
                                elif j == 216: #伤害转化率（`D/G`）
                                    LoLHistory_data[key].append(0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"])
                                elif j == 217: #胜负（`result`）
                                    LoLHistory_data[key].append("胜利" if stats["win"] else "失败")
                                else:
                                    LoLHistory_data[key].append(stats[key])
                            else: #时间轴相关键（Timeline-related keys）
                                LoLHistory_data[key].append(lanes[timeline[key]] if j == 218 else roles[timeline[key]])
                        print("对局记录查询进度（Match history query process）：%d/%d\t对局序号（MatchId）：%d" %(i + 1, len(games), game["gameId"]), end = "\r")
                    LoLHistory_statistics_output_order = [0, 24, 5, 3, 13, 11, 6, 14, 10, 9, 34, 35, 44, 37, 38, 155, 156, 157, 158, 159, 160, 161, 210, 212, 60, 217, 132]
                    LoLHistory_data_organized = {}
                    for i in LoLHistory_statistics_output_order:
                        key = LoLHistory_header_keys[i]
                        LoLHistory_data_organized[key] = LoLHistory_data[key]
                    LoLHistory_df = pandas.DataFrame(data = LoLHistory_data_organized)
                    LoLHistory_df = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df.columns], LoLHistory_df], ignore_index = True)
                    #LoLHistory_df.apply(lambda x: pandas.Series([-3], index = ["K/D/A"]))
                    LoLHistory_web_display_order = [0, 24, 5, 3, 13, 11, 6, 14, 10, 9, 34, 35, 36, 44, 39, 40, 162, 163, 164, 165, 166, 167, 168, 210, 212, 60, 217, 132]
                    LoLHistory_data_organized_web = {}
                    for i in LoLHistory_web_display_order:
                        key = LoLHistory_header_keys[i]
                        if i in [27, 36, 39, 40, 162, 163, 164, 165, 166, 167, 168, 181, 182, 183, 184, 185, 186, 188, 190, 197, 198, 199, 200, 201, 202]: #转换路径（Transform the paths）
                            LoLHistory_data_organized_web[key] = list(map(lambda x: "" if x == "" else urljoin(connection.address, x), LoLHistory_data[key]))
                        else:
                            LoLHistory_data_organized_web[key] = LoLHistory_data[key]
                    LoLHistory_df_web = pandas.DataFrame(data = LoLHistory_data_organized_web)
                    LoLHistory_df_web = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df_web.columns], LoLHistory_df_web], ignore_index = True)
                    LoLHistory_htmltable = LoLHistory_df_web.to_html(escape = False)
                    if LoLGamePlayed:
                        logPrint(LoLHistory_df[:min(21, len(LoLHistory_df) + 1)], write_time = False)
                    
                    logPrint('请输入要查询的英雄联盟对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出英雄联盟对局查询“0”：\nPlease enter the LoL match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to quit searching for LoL matches.')
                    gameIds = LoLHistory_data["gameId"]
                    LoLMatchIDs = []
                    matches_not_found = [] #在扫描模式下，当从本地文件获取的对局从API重新获取出现异常时，处理策略是输出异常信息并跳过该对局，而不是将其直接从对局序号列表中去除，因为这样会使循环乱套。而后面的info_exist_error、timeline_exist_error、main_player_included和match_reserve_strategy只会在该对局正常获取时才会统计。所以一旦出现数据获取失败的对局，在最后导出数据时，“if match_reserve_strategy[i]:”语句会出现“IndexError: list index out of range”报错（Under scan mode, when an exception occurred during crawling matches with LoLMatchIDs obtained from local files from API, the strategy is to print the exception and skip this match, instead of directly removing them from the matchID list, for the removal will disturb the loop. However, the variables info_exist_error, timeline_exist_error, main_player_included and match_reserve_strategy only work when the matches are crawled from the database as expected. So once a match fails to be captured, during xlsx file export at the end of the program, an "IndexError: list index out of range" exception will emerge from the statement "if match_reserve_strategy[i]:"）
                    error_LoLMatchIDs = [] #记录实际存在但未如期获取的对局序号（Records the LoL matchIDs that really exist but fail to be fetched）
                    scan = False #用于将扫描获取的历史记录保存为后缀为“ - Scan”的工作表，防止后续【一键查询】时会把【本地重查】辛辛苦苦得到的对局记录覆盖掉。这样也有利于手动重整，即每次【一键查询】后，可手动将新增的对局记录加到后缀为“ - Scan”的工作表中（Determines whether to save the match histories to a sheet postfixxed with " - Scan", in case the subsequent [One-Key Query] overwrites the match histories fetched and sorted hard by [Local Recheck]. It also helps manual arrangement. That is, after each [One-Key Query], the user may manually add the new match histories to the sheet postfixxed with " - Scan"）
                    while True:
                        matchID = logInput()
                        fetched_info = True #是否正常存储对局信息（Whether the match information is captured as expected）
                        fetched_timeline = True #是否正常存储对局时间轴（Whether the match timeline is captured as expected）
                        old_match_detected = False #是否检测到旧对局（Whether any old match is detected）
                        if matchID == "":
                            continue
                        elif matchID == "0":
                            LoLGame_stat_df = pandas.DataFrame()
                            LoLGame_stat_df_export = False #是否导出英雄联盟战绩（Whether to export LoL game stats）
                            break
                        else:
                            if matchID == "3":
                                saved_LoLMatchIDs = [int(name.split(".")[0].split("-")[-1]) for name in os.listdir(folder) if name.startswith("Match Information (LoL) - ")]
                                old_match_detected = len(saved_LoLMatchIDs) > 0
                                if old_match_detected:
                                    latest_LoLMatchID = max(saved_LoLMatchIDs) #需要注意，对局序号最大的对局未必是最近进行的对局。而这种情况并不会引起数据的丢失。相反，最近进行的对局会被重新保存一次，从数据完整性的角度上讲无关紧要（Note that the match with the greatest matchID doesn't mean it's the latest match. Nevertheless, when this situation happens, there won't be any data loss. Conversely, the latest match will be saved again, which doesn't matter in terms of data integrity）
                                    latest_LoLMatchID_index = gameIds.index(latest_LoLMatchID) if latest_LoLMatchID in gameIds else 500
                                    logPrint("检测到您以前曾经查询过该召唤师的英雄联盟对局记录。是否只保存该召唤师信息文件夹中不包含的英雄联盟对局？（输入空字符串以只保存未保存过文本文档的对局，否则自行指定对局索引上下限）\nThe program detected that you've searched for this summoner's LoL match history before. Do you want to only save the LoL matches not present in the current summoner folder? (Enter an empty string to saved only the matches whose json files haven't been saved, or any non-empty string to specify the begIndex and endIndex of the matches by yourself)\n即将使用的对局索引下界和上界（The match begIndex and endIndex to be used）：0 %d" %latest_LoLMatchID_index)
                                    update_unsaved_only_str = logInput()
                                    update_unsaved_only = not bool(update_unsaved_only_str)
                                if old_match_detected and update_unsaved_only:
                                    LoLMatchIDs = gameIds[:]
                                else:
                                    logPrint("请设置需要查询的对局索引下界和上界，以空格为分隔符（输入空字符以默认查询近200场对局）：\nPlease set the begIndex and endIndex of the matches to be searched, split by space (Enter an empty string to search for the recent 200 matches):") #在13.13版本以前，腾讯代理的服务器只支持近20场对局查询（Before Patch 13.13, Tencent servers only provide search of the latest 20 matches）
                                    while True:
                                        gameIndex = logInput()
                                        if gameIndex == "":
                                            begIndex, endIndex = 0, 200
                                        else:
                                            try:
                                                begIndex, endIndex = map(int, gameIndex.split())
                                            except ValueError:
                                                logPrint("请以空格为分隔符输入对局索引的自然数类型的下界和上界！\nPlease enter two nonegative integers as the begIndex and endIndex of the matches split by space!")
                                                continue
                                        break
                                    LoLMatchIDs = gameIds[begIndex:endIndex]
                            elif matchID == "scan":
                                filenames = os.listdir(folder)
                                LoLMatchIDs += gameIds
                                for filename in filenames:
                                    if filename.startswith("Match Information (LoL) - "):
                                        LoLMatchIDs.append(int(filename.split("-")[-1].split(".")[0]))
                                if LoLMatchIDs == list():
                                    logPrint("尚未保存过该玩家的数据！\nYou haven't saved this summoner's matches yet!\n")
                                    break
                                else:
                                    LoLMatchIDs = sorted(set(LoLMatchIDs), reverse = True)
                                    logPrint("检测到%d场对局。是否继续？（输入任意键以重新输入要查询的对局序号，否则重新获取这些对局的数据）\nDetected %d matches. Continue? (Input any nonempty string to return to the last step of inputting the matchID, or null to recapture those matches' data)" %(len(LoLMatchIDs), len(LoLMatchIDs)))
                                    recapture_str = logInput()
                                    recapture = bool(recapture_str)
                                    if recapture:
                                        LoLMatchIDs = [] #如果没有这句语句，那么当重新输入对局序号列表时，从本地文件中检测到的对局数量相比上次检测数的基础上会多出本地文件中包含的对局的数量（Without this assignment, when reinputting the matchID list, the number of matches detected from the local files will become more than that of the last time's check）
                                        logPrint('请输入要查询的英雄联盟对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出英雄联盟对局查询“0”：\nPlease enter the LoL match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to quit searching for LoL matches.')
                                        continue
                                    scan = True #不应直接放到matchID == "scan"语句下，因为有可能历史记录不是扫描获取的，而是一开始就获取的。比如“尚未保存过该玩家的数据”，或者提示“检测到若干场对局。是否继续”选择了否（This statement shouldn't follow closely after the statement `matchID == "scan"`, because the match history might be obtained in the beginning instead of by scanning. Cases are that a summoner's data has never been saved locally, and that the user inputs something in face of the hint "Detected some matches. Continue?"）
                                    LoLChampions = copy.deepcopy(LoLChampions_initial) #重新查询历史记录，应当从最新版本开始查起（Re-searching the history should start from the latest patch）
                                    spells = copy.deepcopy(spells_initial)
                                    LoLItems = copy.deepcopy(LoLItems_initial)
                                    current_versions["summonerIcon"] = current_versions["LoLChampion"] = current_versions["spell"] = current_versions["LoLItem"] = current_versions["perk"] = current_versions["perkstyle"] = current_versions["CherryAugment"] = URLPatch
                                    unmapped_keys["summonerIcon"], unmapped_keys["LoLChampion"], unmapped_keys["spell"], unmapped_keys["LoLItem"], unmapped_keys["perk"], unmapped_keys["perkstyle"], unmapped_keys["CherryAugment"] = set(), set(), set(), set(), set(), set(), set()
                                    #官方的历史记录最多保留200场对局的个人信息。这里要实现将待保存对局全部整理成一个类似于历史记录的布局的功能（要查看历史记录的原来的布局，可以先不使用scan选项，生成Excel文件后查看“Match History”工作表的布局），所以不再使用前面的历史记录，而是从每一局中提取信息，整合成一张历史记录表。因此，大部分代码复制自前面一部分的代码（Official match history holds personal history of at most 200 matches. Here I want to implement a function to sort the information of all matches into a table like the original match history table. (To check this format for the first time, please don't choose the "scan" option and view the "Match History" sheet of the generated xlsx file.) Therefore, the previous history_df is abandoned. Instead, information in the match history is extracted from all matches to form the table subsequently）
                                    LoLHistory_header = {"gameIndex": "游戏序号", "endOfGameResult": "对局终止情况", "gameCreation": "对局创建时间戳", "gameCreationDate": "对局创建日期", "gameDuration": "持续时长（秒）", "gameId": "对局序号", "gameMode": "游戏模式", "gameModeMutators": "游戏模式配置", "gameType": "游戏类型", "gameVersion": "对局版本", "mapId": "地图序号", "queueId": "队列序号", "seasonId": "赛季序号", "gameDuration_norm": "持续时长", "gameModeName": "游戏模式名称", "accountId": "帐户序号", "currentAccountId": "当前帐户序号", "currentPlatformId": "当前服务器代码", "gameName": "玩家昵称", "matchHistoryUri": "对局记录网址", "platformId": "服务器代码", "profileIcon": "召唤师图标序号", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "tagLine": "昵称编号", "profileIcon_title": "召唤师图标名称", "profileIcon_imagePath": "召唤师图标路径", "championId": "英雄序号", "highestAchievedSeasonTier": "最高段位", "participantId": "玩家序号", "spell1Id": "召唤师技能1序号", "spell2Id": "召唤师技能2序号", "teamId": "阵营代号", "champion_name": "英雄", "champion_alias": "代号", "champion_squarePortraitPath": "方块头像路径", "spell1_name": "召唤师技能1", "spell2_name": "召唤师技能2", "spell1_iconPath": "召唤师技能1图标", "spell2_iconPath": "召唤师技能2图标", "team_color": "阵营", "assists": "助攻", "causedEarlySurrender": "发起提前投降", "champLevel": "英雄等级", "combatPlayerScore": "战斗得分", "damageDealtToObjectives": "对战略点的总伤害", "damageDealtToTurrets": "对防御塔的总伤害", "damageSelfMitigated": "自我缓和的伤害", "deaths": "死亡", "doubleKills": "双杀", "earlySurrenderAccomplice": "同意提前投降", "firstBloodAssist": "协助获得第一滴血", "firstBloodKill": "第一滴血", "firstInhibitorAssist": "协助摧毁第一座召唤水晶", "firstInhibitorKill": "摧毁第一座召唤水晶", "firstTowerAssist": "协助摧毁第一座塔", "firstTowerKill": "摧毁第一座塔", "gameEndedInEarlySurrender": "提前投降导致比赛结束", "gameEndedInSurrender": "投降导致比赛结束", "goldEarned": "金币", "goldSpent": "金币使用", "inhibitorKills": "摧毁召唤水晶", "item0": "装备1序号", "item1": "装备2序号", "item2": "装备3序号", "item3": "装备4序号", "item4": "装备5序号", "item5": "装备6序号", "item6": "饰品序号", "killingSprees": "大杀特杀", "kills": "击杀", "largestCriticalStrike": "最大暴击伤害", "largestKillingSpree": "最高连杀", "largestMultiKill": "最高多杀", "longestTimeSpentLiving": "最长生存时间", "magicDamageDealt": "造成的魔法伤害", "magicDamageDealtToChampions": "对英雄的魔法伤害", "magicalDamageTaken": "承受的魔法伤害", "neutralMinionsKilled": "击杀野怪", "neutralMinionsKilledEnemyJungle": "击杀敌方野区野怪", "neutralMinionsKilledTeamJungle": "击杀我方野区野怪", "objectivePlayerScore": "战略点玩家得分", "pentaKills": "五杀", "perk0": "符文1序号", "perk0Var1": "符文1：参数1", "perk0Var2": "符文1：参数2", "perk0Var3": "符文1：参数3", "perk1": "符文2序号", "perk1Var1": "符文2：参数1", "perk1Var2": "符文2：参数2", "perk1Var3": "符文2：参数3", "perk2": "符文3序号", "perk2Var1": "符文3：参数1", "perk2Var2": "符文3：参数2", "perk2Var3": "符文3：参数3", "perk3": "符文4序号", "perk3Var1": "符文4：参数1", "perk3Var2": "符文4：参数2", "perk3Var3": "符文4：参数3", "perk4": "符文5序号", "perk4Var1": "符文5：参数1", "perk4Var2": "符文5：参数2", "perk4Var3": "符文5：参数3", "perk5": "符文6序号", "perk5Var1": "符文6：参数1", "perk5Var2": "符文6：参数2", "perk5Var3": "符文6：参数3", "perkPrimaryStyle": "主系序号", "perkSubStyle": "副系序号", "physicalDamageDealt": "造成的物理伤害", "physicalDamageDealtToChampions": "对英雄的物理伤害", "physicalDamageTaken": "承受的物理伤害", "playerAugment1": "强化符文1", "playerAugment2": "强化符文2", "playerAugment3": "强化符文3", "playerAugment4": "强化符文4", "playerAugment5": "强化符文5", "playerAugment6": "强化符文6", "playerScore0": "玩家得分1", "playerScore1": "玩家得分2", "playerScore2": "玩家得分3", "playerScore3": "玩家得分4", "playerScore4": "玩家得分5", "playerScore5": "玩家得分6", "playerScore6": "玩家得分7", "playerScore7": "玩家得分8", "playerScore8": "玩家得分9", "playerScore9": "玩家得分10", "playerSubteamId": "子阵营代号", "quadraKills": "四杀", "sightWardsBoughtInGame": "购买洞察之石", "subteamPlacement": "队伍排名", "teamEarlySurrendered": "队伍提前投降", "timeCCingOthers": "控制得分", "totalDamageDealt": "造成的伤害总和", "totalDamageDealtToChampions": "对英雄的伤害总和", "totalDamageTaken": "承受伤害", "totalHeal": "输出治疗效果", "totalMinionsKilled": "击杀小兵", "totalPlayerScore": "玩家总得分", "totalScoreRank": "总得分排名", "totalTimeCrowdControlDealt": "控制时间", "totalUnitsHealed": "治疗单位数", "tripleKills": "三杀", "trueDamageDealt": "造成真实伤害", "trueDamageDealtToChampions": "对英雄的真实伤害", "trueDamageTaken": "承受的真实伤害", "turretKills": "摧毁防御塔", "unrealKills": "六杀及以上", "visionScore": "视野得分", "visionWardsBoughtInGame": "购买控制守卫", "wardsKilled": "摧毁守卫", "wardsPlaced": "放置守卫", "win": "胜利", "item0_name": "装备1", "item1_name": "装备2", "item2_name": "装备3", "item3_name": "装备4", "item4_name": "装备5", "item5_name": "装备6", "item6_name": "饰品", "item0_iconPath": "装备1图标路径", "item1_iconPath": "装备2图标路径", "item2_iconPath": "装备3图标路径", "item3_iconPath": "装备4图标路径", "item4_iconPath": "装备5图标路径", "item5_iconPath": "装备6图标路径", "item6_iconPath": "饰品图标路径", "perk0EndOfGameStatDescs": "符文1游戏结算数据", "perk1EndOfGameStatDescs": "符文2游戏结算数据", "perk2EndOfGameStatDescs": "符文3游戏结算数据", "perk3EndOfGameStatDescs": "符文4游戏结算数据", "perk4EndOfGameStatDescs": "符文5游戏结算数据", "perk5EndOfGameStatDescs": "符文6游戏结算数据", "perk0_name": "符文1名称", "perk1_name": "符文2名称", "perk2_name": "符文3名称", "perk3_name": "符文4名称", "perk4_name": "符文5名称", "perk5_name": "符文6名称", "perk0_iconPath": "符文1图标路径", "perk1_iconPath": "符文2图标路径", "perk2_iconPath": "符文3图标路径", "perk3_iconPath": "符文4图标路径", "perk4_iconPath": "符文5图标路径", "perk5_iconPath": "符文6图标路径", "perkPrimaryStyle_name": "主系名称", "perkPrimaryStyle_iconPath": "主系图标路径", "perkSubStyle_name": "副系名称", "perkSubStyle_iconPath": "副系图标路径", "playerAugment1_nameTRA": "强化符文1名称", "playerAugment2_nameTRA": "强化符文2名称", "playerAugment3_nameTRA": "强化符文3名称", "playerAugment4_nameTRA": "强化符文4名称", "playerAugment5_nameTRA": "强化符文5名称", "playerAugment6_nameTRA": "强化符文6名称", "playerAugment1_augmentIconPath": "强化符文1图标路径", "playerAugment2_augmentIconPath": "强化符文2图标路径", "playerAugment3_augmentIconPath": "强化符文3图标路径", "playerAugment4_augmentIconPath": "强化符文4图标路径", "playerAugment5_augmentIconPath": "强化符文5图标路径", "playerAugment6_augmentIconPath": "强化符文6图标路径", "playerAugment1_rarity": "强化符文1等级", "playerAugment2_rarity": "强化符文2等级", "playerAugment3_rarity": "强化符文3等级", "playerAugment4_rarity": "强化符文4等级", "playerAugment5_rarity": "强化符文5等级", "playerAugment6_rarity": "强化符文6等级", "playerSubteamColor": "子阵营", "K/D/A": "击杀/死亡/助攻", "KDA": "战损比", "CS": "补刀", "GPM": "分均经济", "GUE": "金币利用率", "CSPM": "分均补刀", "D/G": "伤害转化率", "result": "结果", "lane": "分路", "role": "角色定位"}
                                    LoLHistory_header_keys = list(LoLHistory_header.keys())
                                    LoLHistory_data = {}
                                    versions = []
                                    for i in range(len(LoLHistory_header_keys)):
                                        key = LoLHistory_header_keys[i]
                                        LoLHistory_data[key] = []
                                    #开始赋值（Begin assignment）
                                    for i in range(len(LoLMatchIDs)):
                                        matchID = LoLMatchIDs[i]
                                        LoLGame_info = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchID}")).json()
                                        
                                        #尝试修复错误（Try to fix the error）
                                        if "errorCode" in LoLGame_info:
                                            count = 0
                                            if LoLGame_info["httpStatus"] == 404:
                                                logPrint(f"未找到序号为{matchID}的回放文件！将忽略该序号。\nMatch file with matchID {matchID} not found! The program will ignore this matchID.")
                                            if "500 Internal Server Error" in LoLGame_info["message"]:
                                                if not error_occurred:
                                                    logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                                    error_occurred = True
                                                while "errorCode" in LoLGame_info and "500 Internal Server Error" in LoLGame_info["message"] and count <= 3:
                                                    count += 1
                                                    logPrint("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                                                    LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                                            elif "Connection timed out after " in LoLGame_info["message"]:
                                                fetched_info = False
                                                logPrint("对局信息保存超时！请检查网速状况！\nGame information saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                                            elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"]:
                                                if not error_occurred:
                                                    logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                                                    error_occurred = True
                                                while "errorCode" in LoLGame_info and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"] and count <= 3:
                                                    count += 1
                                                    logPrint("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                                                    LoLGame_info = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchID}")).json()
                                            if count > 3:
                                                fetched_info = False
                                                logPrint("对局%d信息获取失败！\nMatch %d information capture failure!" %(matchID, matchID))
                                        
                                        if "errorCode" in LoLGame_info:
                                            logPrint(LoLGame_info, end = "\n\n")
                                            continue #重新获取历史与后续输出对局信息和时间轴是两码事。后面info_exist_error、timeline_exist_error、main_player_included和match_reserve_strategy位于输出对局信息和时间轴的代码中，因此这里不需要记录待去除的对局。如果这里记录，后面再次记录，由于是列表追加而不是集合添加元素，重复记录的对局在再次从对局序号列表中去除时会触发IndexError（Recapturing the match history and outputting match history and timeline are not the samething. Because the variables exist_error, timeline_exist_error, main_player_included and match_reserve_strategy is located in the code that output match information and timeline, here's no need to record the matches to remove. Otherwise, with the following code recording these matches again, removal of the repeatedly recorded matches from the matchID list will trigger the IndexError, since the matches are recorded by appending elements to a list, instead of adding elements into a set）
                                        version = LoLGame_info["gameVersion"]
                                        bigVersion = ".".join(version.split(".")[:2])
                                        try: #这一部分语句无关紧要（This piece of statements doesn't matter）
                                            versions.append(patches_dict[bigVersion][0])
                                        except KeyError: #有可能存在美测服的临时版本未收录到DataDragon数据库中。详见patch_compare函数的注释（Possibly an intermediate patch on PBE isn't archived in DataDragon database. More details in the annotation of `patch_compare` function）
                                            if patch_compare(bigVersion, latest_patch):
                                                patches_dict[bigVersion] = [FindPostPatch(version, patches)]
                                            else:
                                                patches_dict[bigVersion] = [latest_patch]
                                            versions.append(patches_dict[bigVersion][0])
                                        #定位该召唤师（Find the index of this player in a match）
                                        for participantId in range(len(LoLGame_info["participantIdentities"])):
                                            if LoLGame_info["participantIdentities"][participantId]["player"]["puuid"] == current_puuid or LoLGame_info["participantIdentities"][participantId]["player"]["gameName"] + "#" + LoLGame_info["participantIdentities"][participantId]["player"]["tagLine"] == current_summonerName:
                                                break
                                        stats = LoLGame_info["participants"][participantId]["stats"]
                                        timeline = LoLGame_info["participants"][participantId]["timeline"]
                                        #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                                        ##召唤师图标（Summoner icon）
                                        summonerIconIds_match_list = [LoLGame_info["participantIdentities"][participantId]["player"]["profileIcon"]]
                                        for j in summonerIconIds_match_list:
                                            if not j in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                                                summonerIconPatch_adopted = bigVersion
                                                summonerIcon_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchID, j, summonerIcon_recapture, summonerIconPatch_adopted, j, i + 1, len(LoLMatchIDs), matchID, summonerIconPatch_adopted, summonerIcon_recapture))
                                                while True:
                                                    try:
                                                        summonerIcon = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        summonerIconPatch_deserted = summonerIconPatch_adopted
                                                        summonerIconPatch_adopted = FindPostPatch(summonerIconPatch_adopted, bigPatches)
                                                        summonerIcon_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if summonerIcon_recapture < 3:
                                                            summonerIcon_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(LoLMatchIDs), matchID, j, j, i + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted))
                                                        summonerIcons = {}
                                                        for summonerIcon_iter in summonerIcon:
                                                            summonerIcon_id = summonerIcon_iter["id"]
                                                            summonerIcons[summonerIcon_id] = summonerIcon_iter
                                                        current_versions["summonerIcon"] = summonerIconPatch_adopted
                                                        unmapped_keys["summonerIcon"].clear()
                                                        break
                                                break
                                        ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
                                        LoLChampionIds_match_list = [LoLGame_info["participants"][participantId]["championId"]]
                                        for j in LoLChampionIds_match_list:
                                            if not j in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                                                LoLChampionPatch_adopted = bigVersion
                                                LoLChampion_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchID, j, LoLChampion_recapture, LoLChampionPatch_adopted, j, i + 1, len(LoLMatchIDs), matchID, LoLChampionPatch_adopted, LoLChampion_recapture))
                                                while True:
                                                    try:
                                                        LoLChampion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        LoLChampionPatch_deserted = LoLChampionPatch_adopted
                                                        LoLChampionPatch_adopted = FindPostPatch(LoLChampionPatch_adopted, bigPatches)
                                                        LoLChampion_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if LoLChampion_recapture < 3:
                                                            LoLChampion_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(LoLMatchIDs), matchID, j, j, i + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted))
                                                        LoLChampions = {}
                                                        for LoLChampion_iter in LoLChampion:
                                                            LoLChampion_id = LoLChampion_iter["id"]
                                                            LoLChampions[LoLChampion_id] = LoLChampion_iter
                                                        current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                                        unmapped_keys["LoLChampion"].clear()
                                                        break
                                                break
                                        ##召唤师技能（Summoner spells）
                                        spellIds_match_list = [LoLGame_info["participants"][participantId]["spell1Id"], LoLGame_info["participants"][participantId]["spell2Id"]] #一般情况下，一名玩家不可能带两个相同的召唤师技能（Normally, a player can't take two same spells）
                                        for j in spellIds_match_list:
                                            if not j in spells and current_versions["spell"] != bigVersion and j != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                                                spellPatch_adopted = bigVersion
                                                spell_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchID, j, spell_recapture, spellPatch_adopted, j, i + 1, len(LoLMatchIDs), matchID, spellPatch_adopted, spell_recapture))
                                                while True:
                                                    try:
                                                        spell = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        spellPatch_deserted = spellPatch_adopted
                                                        spellPatch_adopted = FindPostPatch(spellPatch_adopted, bigPatches)
                                                        spell_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if spell_recapture < 3:
                                                            spell_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(LoLMatchIDs), matchID, j, j, i + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted))
                                                        spells = {}
                                                        for spell_iter in spell:
                                                            spell_id = spell_iter["id"]
                                                            spells[spell_id] = spell_iter
                                                        current_versions["spell"] = spellPatch_adopted
                                                        unmapped_keys["spell"].clear()
                                                        break
                                                break
                                        ##英雄联盟装备（LoL items）
                                        LoLItemIds_match_list = sorted(set(LoLGame_info["participants"][participantId]["stats"]["item" + str(i)] for i in range(7)))
                                        for j in LoLItemIds_match_list:
                                            if not j in LoLItems and current_versions["LoLItem"] != bigVersion and j != 0: #空装备序号是0（The itemId of an empty item is 0）
                                                LoLItemPatch_adopted = bigVersion
                                                LoLItem_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchID, j, LoLItem_recapture, LoLItemPatch_adopted, j, i + 1, len(LoLMatchIDs), matchID, LoLItemPatch_adopted, LoLItem_recapture))
                                                while True:
                                                    try:
                                                        LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        LoLItemPatch_deserted = LoLItemPatch_adopted
                                                        LoLItemPatch_adopted = FindPostPatch(LoLItemPatch_adopted, bigPatches)
                                                        LoLItem_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if LoLItem_recapture < 3:
                                                            LoLItem_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(LoLMatchIDs), matchID, j, j, i + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted))
                                                        LoLItems = {}
                                                        for LoLItem_iter in LoLItem:
                                                            LoLItem_id = LoLItem_iter["id"]
                                                            LoLItems[LoLItem_id] = LoLItem_iter
                                                        current_versions["LoLItem"] = LoLItemPatch_adopted
                                                        unmapped_keys["LoLItem"].clear()
                                                        break
                                                break
                                        ##符文（Perks）
                                        perkIds_match_list = sorted(set(perk for s in [set(map(lambda x: x["stats"]["perk" + str(j)], LoLGame_info["participants"])) for j in range(6)] for perk in s))
                                        for j in perkIds_match_list:
                                            if not j in perks and current_versions["perk"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                                perkPatch_adopted = bigVersion
                                                perk_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchID, j, perk_recapture, perkPatch_adopted, j, i + 1, len(LoLMatchIDs), matchID, perkPatch_adopted, perk_recapture))
                                                while True:
                                                    try:
                                                        perk = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        perkPatch_deserted = perkPatch_adopted
                                                        perkPatch_adopted = FindPostPatch(perkPatch_adopted, bigPatches)
                                                        perk_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if perk_recapture < 3:
                                                            perk_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(LoLMatchIDs), matchID, j, j, i + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted))
                                                        perks = {}
                                                        for perk_iter in perk:
                                                            perk_id = perk_iter["id"]
                                                            perks[perk_id] = perk_iter
                                                        current_versions["perk"] = perkPatch_adopted
                                                        unmapped_keys["perk"].clear()
                                                        break
                                                break
                                        ##符文系（Perkstyles）
                                        perkstyleIds_match_list = sorted(list(set(map(lambda x: x["stats"]["perkPrimaryStyle"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["perkSubStyle"], LoLGame_info["participants"]))))
                                        for j in perkstyleIds_match_list:
                                            if not j in perkstyles and current_versions["perkstyle"] != bigVersion and j != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                                perkstylePatch_adopted = bigVersion
                                                perkstyle_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchID, j, perkstyle_recapture, perkstylePatch_adopted, j, i + 1, len(LoLMatchIDs), matchID, perkstylePatch_adopted, perkstyle_recapture))
                                                while True:
                                                    try:
                                                        perkstyle = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        perkstylePatch_deserted = perkstylePatch_adopted
                                                        perkstylePatch_adopted = FindPostPatch(perkstylePatch_adopted, bigPatches)
                                                        perkstyle_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if perkstyle_recapture < 3:
                                                            perkstyle_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(LoLMatchIDs), matchID, j, j, i + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted))
                                                        perkstyles = {}
                                                        for perkstyle_iter in perkstyle["styles"]:
                                                            perkstyle_id = perkstyle_iter["id"]
                                                            perkstyles[perkstyle_id] = perkstyle_iter
                                                        current_versions["perkstyle"] = perkstylePatch_adopted
                                                        unmapped_keys["perkstyle"].clear()
                                                        break
                                                break
                                        ##斗魂竞技场强化符文（Cherry augments）
                                        CherryAugmentIds_match_list = sorted(set(augment for s in [set(map(lambda x: x["stats"]["playerAugment" + str(j)], LoLGame_info["participants"])) for j in range(1, 7)] for augment in s))
                                        for j in CherryAugmentIds_match_list:
                                            if not j in CherryAugments and current_versions["CherryAugment"] != bigVersion and j != 0:
                                                CherryAugmentPatch_adopted = bigVersion
                                                CherryAugment_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(i + 1, len(LoLMatchIDs), matchID, j, CherryAugment_recapture, CherryAugmentPatch_adopted, j, i + 1, len(LoLMatchIDs), matchID, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                                while True:
                                                    try:
                                                        CherryAugment = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        CherryAugmentPatch_deserted = CherryAugmentPatch_adopted
                                                        CherryAugmentPatch_adopted = FindPostPatch(CherryAugmentPatch_adopted, bigPatches)
                                                        CherryAugment_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if CherryAugment_recapture < 3:
                                                            CherryAugment_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(LoLMatchIDs), matchID, j, j, i + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted))
                                                        CherryAugments = {}
                                                        for CherryAugment_iter in CherryAugment:
                                                            CherryAugment_id = CherryAugment_iter["id"]
                                                            CherryAugments[CherryAugment_id] = CherryAugment_iter
                                                        current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                                        unmapped_keys["CherryAugment"].clear()
                                                        break
                                                break
                                        #下面开始整理数据（Sorts out the data）
                                        for j in range(len(LoLHistory_header_keys)):
                                            key = LoLHistory_header_keys[j]
                                            if j == 0:
                                                LoLHistory_data[key].append(i + 1)
                                            elif j <= 14:
                                                if j == 1: #对局终止情况（`endOfGameResult`）
                                                    LoLHistory_data[key].append(endOfGameResults[LoLGame_info["endOfGameResult"]])
                                                elif j == 3: #对局创建日期（`gameCreationDate`）
                                                    LoLHistory_data[key].append(LoLGame_info["gameCreationDate"][:10] + " " + LoLGame_info["gameCreationDate"][11:23])
                                                elif j == 8: #游戏类型（`gameType`）
                                                    LoLHistory_data[key].append(gameTypes[LoLGame_info[key]])
                                                elif j == 13: #持续时长（`gameDuration_norm`）
                                                    LoLHistory_data[key].append(str(LoLGame_info["gameDuration"] // 60) + ":" + "%02d" %(LoLGame_info["gameDuration"] % 60))
                                                elif j == 14: #游戏模式名称（`gameModeName`）
                                                    LoLHistory_data[key].append("自定义" if LoLGame_info["queueId"] == 0 else gamemodes[LoLGame_info["queueId"]]["name"] if LoLGame_info["queueId"] in gamemodes else "")
                                                else:
                                                    LoLHistory_data[key].append(LoLGame_info[key])
                                            elif j <= 27:
                                                if j >= 26: #召唤师图标相关键（Summoner icon-related keys）
                                                    profileIconId = LoLGame_info["participantIdentities"][participantId]["player"]["profileIcon"]
                                                    if profileIconId in summonerIcons:
                                                        try:
                                                            LoLHistory_data[key].append(summonerIcons[profileIconId][key.split("_")[-1]])
                                                        except KeyError:
                                                            traceback_info = traceback.format_exc()
                                                            logPrint(traceback_info)
                                                            LoLHistory_data[key].append("")
                                                    elif profileIconId in summonerIcons_initial:
                                                        try:
                                                            LoLHistory_data[key].append(summonerIcons_initial[profileIconId][key.split("_")[-1]])
                                                        except KeyError:
                                                            traceback_info = traceback.format_exc()
                                                            logPrint(traceback_info)
                                                            LoLHistory_data[key].append("")
                                                    else:
                                                        if not profileIconId in unmapped_keys["summonerIcon"]:
                                                            unmapped_keys["summonerIcon"].add(profileIconId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, profileIconId, j, key, profileIconId, i + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLHistory_data[key].append(profileIconId if j == 26 else "")
                                                else:
                                                    LoLHistory_data[key].append(LoLGame_info["participantIdentities"][participantId]["player"][key])
                                            elif j <= 41:
                                                if j == 29: #最高段位（`highestAchievedSeasonTier`）
                                                    LoLHistory_data[key].append(tiers[LoLGame_info["participants"][participantId]["highestAchievedSeasonTier"]])
                                                elif j >= 34 and j <= 36: #英雄相关键（Champion-related keys）
                                                    championId = LoLGame_info["participants"][participantId][key.split("_")[0] + "Id"]
                                                    if championId in LoLChampions:
                                                        LoLHistory_data[key].append(LoLChampions[championId][key.split("_")[1]])
                                                    elif championId in LoLChampions_initial:
                                                        LoLHistory_data[key].append(LoLChampions_initial[championId][key.split("_")[1]])
                                                    else: #在国服体验服的对局序号为696083511的对局中，出现了英雄序号为37225015（In a match with matchId 696083511 on Chinese PBE, there's a champion with championId 37225015）
                                                        if not championId in unmapped_keys["LoLChampion"]:
                                                            unmapped_keys["LoLChampion"].add(championId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, i + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLHistory_data[key].append(championId if j == 34 else "")
                                                elif j >= 37 and j <= 40: #召唤师技能相关键（Summoner spell-related keys）
                                                    spellId = LoLGame_info["participants"][participantId][key.split("_")[0] + "Id"]
                                                    if spellId in spells:
                                                        LoLHistory_data[key].append(spells[spellId][key.split("_")[1]])
                                                    elif spellId in spells_initial:
                                                        LoLHistory_data[key].append(spells_initial[spellId][key.split("_")[1]])
                                                    else:
                                                        if not spellId in unmapped_keys["spell"]:
                                                            unmapped_keys["spell"].add(spellId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, spellId, j, key, spellId, i + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLHistory_data[key].append(spellId if j <= 38 else "")
                                                elif j == 41: #阵营（`team_color`）
                                                    LoLHistory_data[key].append(team_color[LoLGame_info["participants"][participantId]["teamId"]])
                                                else:
                                                    LoLHistory_data[key].append(LoLGame_info["participants"][participantId][key])
                                            elif j <= 217:
                                                if j >= 155 and j <= 168: #英雄联盟装备相关键（LoLItems-related keys）
                                                    itemId = stats[key.split("_")[0]]
                                                    if itemId == 0:
                                                        LoLHistory_data[key].append("")
                                                    elif itemId in LoLItems:
                                                        LoLHistory_data[key].append(LoLItems[itemId][key.split("_")[-1]])
                                                    elif itemId in LoLItems_initial:
                                                        LoLHistory_data[key].append(LoLItems_initial[itemId][key.split("_")[-1]])
                                                    else:
                                                        if not itemId in unmapped_keys["LoLItem"]:
                                                            unmapped_keys["LoLItem"].add(itemId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, itemId, j, key, itemId, i + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLHistory_data[key].append(itemId if j <= 161 else "")
                                                elif j >= 169 and j <= 186: #符文相关键（Perks-related keys）
                                                    if j <= 174:
                                                        perkId = stats[key[:5]]
                                                        if perkId == 0:
                                                            LoLHistory_data[key].append("")
                                                        elif perkId in perks:
                                                            perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks[perkId]["endOfGameStatDescs"])))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                                                            LoLHistory_data[key].append(perk_EndOfGameStatDescs)
                                                        elif perkId in perks_initial:
                                                            perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks_initial[perkId]["endOfGameStatDescs"])))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                                                            LoLHistory_data[key].append(perk_EndOfGameStatDescs)
                                                        else:
                                                            if not perkId in unmapped_keys["perk"]:
                                                                unmapped_keys["perk"].add(perkId)
                                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, perkId, j, key, perkId, i + 1, len(LoLMatchIDs), matchID, version))
                                                            LoLHistory_data[key].append("")
                                                    else:
                                                        perkId = stats[key.split("_")[0]]
                                                        if perkId == 0:
                                                            LoLHistory_data[key].append("")
                                                        elif perkId in perks:
                                                            LoLHistory_data[key].append(perks[perkId][key.split("_")[-1]])
                                                        elif perkId in perks_initial:
                                                            LoLHistory_data[key].append(perks_initial[perkId][key.split("_")[-1]])
                                                        else:
                                                            if not perkId in unmapped_keys["perk"]:
                                                                unmapped_keys["perk"].add(perkId)
                                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, perkId, j, key, perkId, i + 1, len(LoLMatchIDs), matchID, version))
                                                            LoLHistory_data[key].append(perkId if j <= 180 else "")
                                                elif j >= 187 and j <= 190: #符文系相关键（Perkstyles-related keys）
                                                    perkstyleId = stats[key.split("_")[0]]
                                                    if perkstyleId == 0:
                                                        LoLHistory_data[key].append("")
                                                    elif perkstyleId in perkstyles:
                                                        LoLHistory_data[key].append(perkstyles[perkstyleId][key.split("_")[-1]])
                                                    elif perkstyleId in perkstyles_initial:
                                                        LoLHistory_data[key].append(perkstyles_initial[perkstyleId][key.split("_")[-1]])
                                                    else:
                                                        if not perkstyleId in unmapped_keys["perkstyle"]:
                                                            unmapped_keys["perkstyle"].add(perkstyleId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, perkstyleId, j, key, perkstyleId, i + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLHistory_data[key].append(perkstyleId if (j - 187) % 2 == 0 else "")
                                                elif j >= 191 and j <= 208: #强化符文相关键（Augment-related keys）
                                                    CherryAugmentId = stats[key.split("_")[0]]
                                                    if CherryAugmentId == 0:
                                                        LoLHistory_data[key].append("")
                                                    elif CherryAugmentId in CherryAugments:
                                                        if j <= 196: #强化符文名称（`nameTRA`）
                                                            LoLHistory_data[key].append(CherryAugments[CherryAugmentId][key.split("_")[-1]])
                                                        elif j <= 202: #强化符文图标路径（`augmentIconPath`）
                                                            LoLHistory_data[key].append(CherryAugments[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png"))
                                                        else: #强化符文等级（`rarity`）
                                                            LoLHistory_data[key].append(augment_rarity[CherryAugments[CherryAugmentId][key.split("_")[-1]]])
                                                    elif CherryAugmentId in CherryAugments_initial:
                                                        if j <= 196: #强化符文名称（`nameTRA`）
                                                            LoLHistory_data[key].append(CherryAugments_initial[CherryAugmentId][key.split("_")[-1]])
                                                        elif j <= 202: #强化符文图标路径（`augmentIconPath`）
                                                            LoLHistory_data[key].append(CherryAugments_initial[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png"))
                                                        else: #强化符文等级（`rarity`）
                                                            LoLHistory_data[key].append(augment_rarity[CherryAugments_initial[CherryAugmentId][key.split("_")[-1]]])
                                                    else:
                                                        if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                                                            unmapped_keys["CherryAugment"].add(CherryAugmentId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(LoLMatchIDs), matchID, version, CherryAugmentId, j, key, CherryAugmentId, i + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLHistory_data[key].append(CherryAugmentId if j <= 196 else "")
                                                elif j == 209: #子阵营（`playerSubteam_color`）
                                                    LoLHistory_data[key].append(subteam_color[stats["playerSubteamId"]])
                                                elif j == 210: #击杀/死亡/助攻（`K/D/A`）
                                                    LoLHistory_data[key].append("/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])]))
                                                elif j == 211: #战损比（`KDA`）
                                                    LoLHistory_data[key].append((stats["kills"] + stats["assists"]) / max(1, stats["deaths"]))
                                                elif j == 212: #补刀（`CS`）
                                                    LoLHistory_data[key].append(stats["neutralMinionsKilled"] + stats["totalMinionsKilled"])
                                                elif j == 213: #分均经济（`GPM`）
                                                    LoLHistory_data[key].append(0 if game["gameDuration"] == 0 else stats["goldEarned"] * 60 / game["gameDuration"])
                                                elif j == 214: #金币利用率（`GUE` - Gold Utilization Efficiency）
                                                    LoLHistory_data[key].append(0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"])
                                                elif j == 215: #分均补刀（`CSPM`）
                                                    LoLHistory_data[key].append(0 if game["gameDuration"] == 0 else (stats["neutralMinionsKilled"] + stats["totalMinionsKilled"]) * 60 / game["gameDuration"])
                                                elif j == 216: #伤害转化率（`D/G`）
                                                    LoLHistory_data[key].append(0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"])
                                                elif j == 217: #胜负（`result`）
                                                    LoLHistory_data[key].append("胜利" if stats["win"] else "失败")
                                                else:
                                                    LoLHistory_data[key].append(stats[key])
                                            else: #时间轴相关键（Timeline-related keys）
                                                LoLHistory_data[key].append(lanes[timeline[key]] if j == 218 else roles[timeline[key]])
                                        logPrint('对局记录重查进度（Match history recheck process）：%d/%d\t对局序号（MatchID）： %s' %(i + 1, len(LoLMatchIDs), matchID), print_time = True)
                                    LoLHistory_statistics_output_order = [0, 24, 5, 3, 13, 11, 6, 14, 10, 9, 34, 35, 44, 37, 38, 155, 156, 157, 158, 159, 160, 161, 210, 212, 60, 217, 132]
                                    LoLHistory_data_organized = {}
                                    for i in LoLHistory_statistics_output_order:
                                        key = LoLHistory_header_keys[i]
                                        LoLHistory_data_organized[key] = LoLHistory_data[key]
                                    LoLHistory_df = pandas.DataFrame(data = LoLHistory_data_organized)
                                    LoLHistory_df = pandas.concat([pandas.DataFrame([LoLHistory_header])[LoLHistory_df.columns], LoLHistory_df], ignore_index = True)
                                    #LoLHistory_df.apply(lambda x: pandas.Series([-3], index = ["K/D/A"]))
                                    logPrint("是否一同保存每场对局的信息？（输入任意键保存，否则将只导出对局记录）\nSave each match? (Input anything to save each match, or null to only save the scanned match history)")
                                    sort_gameInfo_sync_str = logInput()
                                    sort_gameInfo_sync = bool(sort_gameInfo_sync_str)
                                    if not sort_gameInfo_sync:
                                        LoLGame_stat_df = pandas.DataFrame()
                                        LoLGame_stat_df_export = False
                                        break
                            else:
                                try:
                                    matchID = eval(matchID)
                                    LoLMatchIDs = []
                                    if isinstance(matchID, int):
                                        LoLMatchIDs.append(matchID)
                                    elif isinstance(matchID, list):
                                        for match in matchID:
                                            if isinstance(match, int):
                                                LoLMatchIDs.append(match)
                                    if len(LoLMatchIDs) == 0:
                                        logPrint("您输入的对局序号集不合法！请重新输入。\nThe matchID set you've input is illegal! Please try again.")
                                        continue
                                except (SyntaxError, NameError):
                                    logPrint("您的输入存在语法错误。请重新输入！\nSyntax ERROR detected in this input! Please try again!")
                                    continue
                            LoLChampions = copy.deepcopy(LoLChampions_initial) #接下来查询具体的对局信息和时间轴，使用的可能并不是历史记录中记载的对局序号形成的列表。考虑实际使用需求，这里对于装备的合适版本信息采取的思路是默认从最新版本开始获取，如果有装备不存在于最新版本的装备信息，则获取游戏信息中存储的版本对应的装备信息。该思路仍然有问题，详见后续关于美测服的装备获取的注释（The next step is to capture the information and timeline for each specific match, which may not originate from the matchIDs recorded in the match history. Considering the practical use, here the stream of thought for an appropriate version for items is to get items' information from the latest patch, and if some item doesn't exist in the items information of the latest patch, then get the items of the version corresponding to the game according to gameVersion recorded in the match information. There's a flaw of this idea. Please refer to the annotation regarding PBE data crawling for further solution）
                            spells = copy.deepcopy(spells_initial)
                            LoLItems = copy.deepcopy(LoLItems_initial)
                            current_versions["summonerIcon"] = current_versions["LoLChampion"] = current_versions["spell"] = current_versions["LoLItem"] = current_versions["perk"] = current_versions["perkstyle"] = current_versions["CherryAugment"] = URLPatch
                            unmapped_keys["summonerIcon"], unmapped_keys["LoLChampion"], unmapped_keys["spell"], unmapped_keys["LoLItem"], unmapped_keys["perk"], unmapped_keys["perkstyle"], unmapped_keys["CherryAugment"] = set(), set(), set(), set(), set(), set(), set()
                            logPrint("是否输出每场对局的文本文档？（输入任意键不输出，否则默认输出）\nExport text files of each match? (Input anything to refuse exporting, or null to export by default)")
                            export_json_str = logInput()
                            export_json = not bool(export_json_str)
                            LoLGame_info_header = {"gameIndex": "游戏序号", "endOfGameResult": "对局终止情况", "gameCreation": "对局创建时间戳", "gameCreationDate": "创建日期", "gameDuration": "持续时长（秒）", "gameId": "对局序号", "gameMode": "游戏模式", "gameType": "游戏类型", "gameVersion": "对局版本", "mapId": "地图序号", "queueId": "队列序号", "gameDuration_norm": "持续时长", "gameModeName": "游戏模式名称", "participantId": "玩家序号", "accountId": "账户序号", "currentAccountId": "当前账户序号", "currentPlatformId": "当前大区", "gameName": "玩家昵称", "matchHistoryUri": "对局记录网址", "platformId": "原大区", "profileIcon": "召唤师图标序号", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "tagLine": "昵称编号", "profileIcon_title": "召唤师图标名称", "profileIcon_imagePath": "召唤师图标路径", "championId": "选用英雄序号", "highestAchievedSeasonTier": "最高段位", "spell1Id": "召唤师技能1序号", "spell2Id": "召唤师技能2序号", "teamId": "阵营代号", "champion_name": "选用英雄", "champion_alias": "选用英雄代号", "champion_squarePortraitPath": "选用英雄方块头像路径", "spell1_name": "召唤师技能1", "spell2_name": "召唤师技能2", "spell1_iconPath": "召唤师技能1图标", "spell2_iconPath": "召唤师技能2图标", "team_color": "阵营", "assists": "助攻", "causedEarlySurrender": "发起提前投降", "champLevel": "英雄等级", "combatPlayerScore": "战斗得分", "damageDealtToObjectives": "对战略点的总伤害", "damageDealtToTurrets": "对防御塔的总伤害", "damageSelfMitigated": "自我缓和的伤害", "deaths": "死亡", "doubleKills": "双杀", "earlySurrenderAccomplice": "同意提前投降", "firstBloodAssist": "协助获得第一滴血", "firstBloodKill": "第一滴血", "firstInhibitorAssist": "协助摧毁第一座召唤水晶", "firstInhibitorKill": "摧毁第一座召唤水晶", "firstTowerAssist": "协助摧毁第一座塔", "firstTowerKill": "摧毁第一座塔", "gameEndedInEarlySurrender": "提前投降导致比赛结束", "gameEndedInSurrender": "投降导致比赛结束", "goldEarned": "金币获取", "goldSpent": "金币使用", "inhibitorKills": "摧毁召唤水晶", "item0": "装备1序号", "item1": "装备2序号", "item2": "装备3序号", "item3": "装备4序号", "item4": "装备5序号", "item5": "装备6序号", "item6": "饰品序号", "killingSprees": "大杀特杀", "kills": "击杀", "largestCriticalStrike": "最大暴击伤害", "largestKillingSpree": "最高连杀", "largestMultiKill": "最高多杀", "longestTimeSpentLiving": "最长生存时间", "magicDamageDealt": "造成的魔法伤害", "magicDamageDealtToChampions": "对英雄的魔法伤害", "magicalDamageTaken": "承受的魔法伤害", "neutralMinionsKilled": "击杀野怪", "neutralMinionsKilledEnemyJungle": "击杀敌方野区野怪", "neutralMinionsKilledTeamJungle": "击杀我方野区野怪", "objectivePlayerScore": "战略点玩家得分", "pentaKills": "五杀", "perk0": "符文1序号", "perk0Var1": "符文1：参数1", "perk0Var2": "符文1：参数2", "perk0Var3": "符文1：参数3", "perk1": "符文2序号", "perk1Var1": "符文2：参数1", "perk1Var2": "符文2：参数2", "perk1Var3": "符文2：参数3", "perk2": "符文3序号", "perk2Var1": "符文3：参数1", "perk2Var2": "符文3：参数2", "perk2Var3": "符文3：参数3", "perk3": "符文4序号", "perk3Var1": "符文4：参数1", "perk3Var2": "符文4：参数2", "perk3Var3": "符文4：参数3", "perk4": "符文5序号", "perk4Var1": "符文5：参数1", "perk4Var2": "符文5：参数2", "perk4Var3": "符文5：参数3", "perk5": "符文6序号", "perk5Var1": "符文6：参数1", "perk5Var2": "符文6：参数2", "perk5Var3": "符文6：参数3", "perkPrimaryStyle": "主系序号", "perkSubStyle": "副系序号", "physicalDamageDealt": "造成的物理伤害", "physicalDamageDealtToChampions": "对英雄的物理伤害", "physicalDamageTaken": "承受的物理伤害", "playerAugment1": "强化符文1", "playerAugment2": "强化符文2", "playerAugment3": "强化符文3", "playerAugment4": "强化符文4", "playerAugment5": "强化符文5", "playerAugment6": "强化符文6", "playerScore0": "玩家得分1", "playerScore1": "玩家得分2", "playerScore2": "玩家得分3", "playerScore3": "玩家得分4", "playerScore4": "玩家得分5", "playerScore5": "玩家得分6", "playerScore6": "玩家得分7", "playerScore7": "玩家得分8", "playerScore8": "玩家得分9", "playerScore9": "玩家得分10", "playerSubteamId": "子阵营代号", "quadraKills": "四杀", "sightWardsBoughtInGame": "购买洞察之石", "subteamPlacement": "队伍排名", "teamEarlySurrendered": "队伍提前投降", "timeCCingOthers": "控制得分", "totalDamageDealt": "造成的伤害总和", "totalDamageDealtToChampions": "对英雄的伤害总和", "totalDamageTaken": "承受伤害", "totalHeal": "输出治疗效果", "totalMinionsKilled": "击杀小兵", "totalPlayerScore": "玩家总得分", "totalScoreRank": "总得分排名", "totalTimeCrowdControlDealt": "控制时间", "totalUnitsHealed": "治疗单位数", "tripleKills": "三杀", "trueDamageDealt": "造成真实伤害", "trueDamageDealtToChampions": "对英雄的真实伤害", "trueDamageTaken": "承受的真实伤害", "turretKills": "摧毁防御塔", "unrealKills": "六杀及以上", "visionScore": "视野得分", "visionWardsBoughtInGame": "购买控制守卫", "wardsKilled": "摧毁守卫", "wardsPlaced": "放置守卫", "win": "胜利", "item0_name": "装备1", "item1_name": "装备2", "item2_name": "装备3", "item3_name": "装备4", "item4_name": "装备5", "item5_name": "装备6", "item6_name": "饰品", "item0_iconPath": "装备1图标路径", "item1_iconPath": "装备2图标路径", "item2_iconPath": "装备3图标路径", "item3_iconPath": "装备4图标路径", "item4_iconPath": "装备5图标路径", "item5_iconPath": "装备6图标路径", "item6_iconPath": "饰品图标路径", "perk0EndOfGameStatDescs": "符文1游戏结算数据", "perk1EndOfGameStatDescs": "符文2游戏结算数据", "perk2EndOfGameStatDescs": "符文3游戏结算数据", "perk3EndOfGameStatDescs": "符文4游戏结算数据", "perk4EndOfGameStatDescs": "符文5游戏结算数据", "perk5EndOfGameStatDescs": "符文6游戏结算数据", "perk0_name": "符文1名称", "perk1_name": "符文2名称", "perk2_name": "符文3名称", "perk3_name": "符文4名称", "perk4_name": "符文5名称", "perk5_name": "符文6名称", "perk0_iconPath": "符文1图标路径", "perk1_iconPath": "符文2图标路径", "perk2_iconPath": "符文3图标路径", "perk3_iconPath": "符文4图标路径", "perk4_iconPath": "符文5图标路径", "perk5_iconPath": "符文6图标路径", "perkPrimaryStyle_name": "主系名称", "perkPrimaryStyle_iconPath": "主系图标路径", "perkSubStyle_name": "副系名称", "perkSubStyle_iconPath": "副系图标路径", "playerAugment1_nameTRA": "强化符文1名称", "playerAugment2_nameTRA": "强化符文2名称", "playerAugment3_nameTRA": "强化符文3名称", "playerAugment4_nameTRA": "强化符文4名称", "playerAugment5_nameTRA": "强化符文5名称", "playerAugment6_nameTRA": "强化符文6名称", "playerAugment1_augmentIconPath": "强化符文1图标路径", "playerAugment2_augmentIconPath": "强化符文2图标路径", "playerAugment3_augmentIconPath": "强化符文3图标路径", "playerAugment4_augmentIconPath": "强化符文4图标路径", "playerAugment5_augmentIconPath": "强化符文5图标路径", "playerAugment6_augmentIconPath": "强化符文6图标路径", "playerAugment1_rarity": "强化符文1等级", "playerAugment2_rarity": "强化符文2等级", "playerAugment3_rarity": "强化符文3等级", "playerAugment4_rarity": "强化符文4等级", "playerAugment5_rarity": "强化符文5等级", "playerAugment6_rarity": "强化符文6等级", "playerSubteamColor": "子阵营", "K/D/A": "击杀/死亡/助攻", "KDA": "战损比", "CS": "补刀", "GPM": "分均经济", "GUE": "金币利用率", "CSPM": "分均补刀", "D/G": "伤害转化率", "win/lose": "胜负", "bannedChampionId": "禁用英雄序号", "bannedChampion_name": "禁用英雄", "bannedChampion_alias": "禁用英雄代号", "bannedChampion_squarePortraitPath": "禁用英雄方块头像路径", "lane": "分路", "role": "角色定位", "assists_percent": "助攻次数占比", "combatPlayerScore_percent": "战斗得分占比", "damageDealtToObjectives_percent": "对战略点的总伤害占比", "damageDealtToTurrets_percent": "对防御塔的总伤害占比", "damageSelfMitigated_percent": "自我缓和的伤害占比", "deaths_percent": "死亡次数占比", "doubleKills_percent": "双杀次数占比", "goldEarned_percent": "金币获取占比", "goldSpent_percent": "金币使用占比", "inhibitorKills_percent": "摧毁召唤水晶数量占比", "killingSprees_percent": "大杀特杀次数占比", "kills_percent": "击杀数量占比", "largestCriticalStrike_percent": "最大暴击伤害占比", "largestKillingSpree_percent": "最高连杀占比", "largestMultiKill_percent": "最高多杀占比", "longestTimeSpentLiving_percent": "最长生存时间占比", "magicDamageDealt_percent": "造成的魔法伤害占比", "magicDamageDealtToChampions_percent": "对英雄的魔法伤害占比", "magicalDamageTaken_percent": "承受的魔法伤害占比", "neutralMinionsKilled_percent": "击杀野怪数量占比", "neutralMinionsKilledEnemyJungle_percent": "击杀敌方野区野怪数量占比", "neutralMinionsKilledTeamJungle_percent": "击杀我方野区野怪数量占比", "objectivePlayerScore_percent": "战略点玩家得分占比", "pentaKills_percent": "五杀次数占比", "physicalDamageDealt_percent": "造成的物理伤害占比", "physicalDamageDealtToChampions_percent": "对英雄的物理伤害占比", "physicalDamageTaken_percent": "承受的物理伤害占比", "playerScore0_percent": "玩家得分1占比", "playerScore1_percent": "玩家得分2占比", "playerScore2_percent": "玩家得分3占比", "playerScore3_percent": "玩家得分4占比", "playerScore4_percent": "玩家得分5占比", "playerScore5_percent": "玩家得分6占比", "playerScore6_percent": "玩家得分7占比", "playerScore7_percent": "玩家得分8占比", "playerScore8_percent": "玩家得分9占比", "playerScore9_percent": "玩家得分10占比", "quadraKills_percent": "四杀次数占比", "sightWardsBoughtInGame_percent": "购买洞察之石数量占比", "timeCCingOthers_percent": "控制得分占比", "totalDamageDealt_percent": "造成的伤害总和占比", "totalDamageDealtToChampions_percent": "对英雄的伤害总和占比", "totalDamageTaken_percent": "承受伤害占比", "totalHeal_percent": "输出治疗效果占比", "totalMinionsKilled_percent": "击杀小兵数量占比", "totalPlayerScore_percent": "玩家总得分占比", "totalTimeCrowdControlDealt_percent": "控制时间占比", "totalUnitsHealed_percent": "治疗单位数占比", "tripleKills_percent": "三杀次数占比", "trueDamageDealt_percent": "造成真实伤害占比", "trueDamageDealtToChampions_percent": "对英雄的真实伤害占比", "trueDamageTaken_percent": "承受的真实伤害占比", "turretKills_percent": "摧毁防御塔数量占比", "unrealKills_percent": "六杀及以上连杀次数占比", "visionScore_percent": "视野得分占比", "visionWardsBoughtInGame_percent": "购买控制守卫数量占比", "wardsKilled_percent": "摧毁守卫数量占比", "wardsPlaced_percent": "放置守卫数量占比", "KP_percent": "参团率", "CS_percent": "补刀数占比", "assists_order": "助攻次数位次", "champLevel_order": "英雄等级位次", "combatPlayerScore_order": "战斗得分位次", "damageDealtToObjectives_order": "对战略点的总伤害位次", "damageDealtToTurrets_order": "对防御塔的总伤害位次", "damageSelfMitigated_order": "自我缓和的伤害位次", "deaths_order": "死亡次数位次", "doubleKills_order": "双杀次数位次", "goldEarned_order": "金币获取位次", "goldSpent_order": "金币使用位次", "inhibitorKills_order": "摧毁召唤水晶数量位次", "killingSprees_order": "大杀特杀次数位次", "kills_order": "击杀数量位次", "largestCriticalStrike_order": "最大暴击伤害位次", "largestKillingSpree_order": "最高连杀位次", "largestMultiKill_order": "最高多杀位次", "longestTimeSpentLiving_order": "最长生存时间位次", "magicDamageDealt_order": "造成的魔法伤害位次", "magicDamageDealtToChampions_order": "对英雄的魔法伤害位次", "magicalDamageTaken_order": "承受的魔法伤害位次", "neutralMinionsKilled_order": "击杀野怪数量位次", "neutralMinionsKilledEnemyJungle_order": "击杀敌方野区野怪数量位次", "neutralMinionsKilledTeamJungle_order": "击杀我方野区野怪数量位次", "objectivePlayerScore_order": "战略点玩家得分位次", "pentaKills_order": "五杀次数位次", "physicalDamageDealt_order": "造成的物理伤害位次", "physicalDamageDealtToChampions_order": "对英雄的物理伤害位次", "physicalDamageTaken_order": "承受的物理伤害位次", "playerScore0_order": "玩家得分1位次", "playerScore1_order": "玩家得分2位次", "playerScore2_order": "玩家得分3位次", "playerScore3_order": "玩家得分4位次", "playerScore4_order": "玩家得分5位次", "playerScore5_order": "玩家得分6位次", "playerScore6_order": "玩家得分7位次", "playerScore7_order": "玩家得分8位次", "playerScore8_order": "玩家得分9位次", "playerScore9_order": "玩家得分10位次", "quadraKills_order": "四杀次数位次", "sightWardsBoughtInGame_order": "购买洞察之石数量位次", "timeCCingOthers_order": "控制得分位次", "totalDamageDealt_order": "造成的伤害总和位次", "totalDamageDealtToChampions_order": "对英雄的伤害总和位次", "totalDamageTaken_order": "承受伤害位次", "totalHeal_order": "输出治疗效果位次", "totalMinionsKilled_order": "击杀小兵数量位次", "totalPlayerScore_order": "玩家总得分位次", "totalTimeCrowdControlDealt_order": "控制时间位次", "totalUnitsHealed_order": "治疗单位数位次", "tripleKills_order": "三杀次数位次", "trueDamageDealt_order": "造成真实伤害位次", "trueDamageDealtToChampions_order": "对英雄的真实伤害位次", "trueDamageTaken_order": "承受的真实伤害位次", "turretKills_order": "摧毁防御塔数量位次", "unrealKills_order": "六杀及以上连杀次数位次", "visionScore_order": "视野得分位次", "visionWardsBoughtInGame_order": "购买控制守卫数量位次", "wardsKilled_order": "摧毁守卫数量位次", "wardsPlaced_order": "放置守卫数量位次", "KDA_order": "战损比位次", "KP_order": "参团率位次", "CS_order": "补刀数位次", "D/G_order": "伤害转化率位次", "GUE_order": "金币利用率位次"}
                            LoLGame_info_header_keys = list(LoLGame_info_header.keys())
                            LoLGame_stat_data = {} #将主召唤师的信息单独导出到一个工作表中。键使用下面的`LoLGame_info_header`（Export the game stats of the main summoner into a single sheet. Keys are from `LoLGame_info_header`）
                            for i in range(len(LoLGame_info_header)):
                                key = LoLGame_info_header_keys[i]
                                LoLGame_stat_data[key] = []
                            for matchID in LoLMatchIDs:
                                LoLGame_info_export = not (old_match_detected and update_unsaved_only and matchID in saved_LoLMatchIDs) #标记是否导出对局详细信息。如果是在批量查询全部对局的情况下仅保存本地没有的对局，且该对局已在本地，则不保存本场对局（Marks whether to export the match information. If the user submits "3" to search matches in batch and selected to update the matches that don't exist locally, while the current match already exists, then the program won't export this match）
                                #LoLGame_leaderboard_export = False #标记是否导出对局排行榜。这一块目前待定，未来考虑设计识别成只有那些要保存的匹配对局才导出（Marks whether to export the match leaderboard. This is currently undicided, and in the future it should export matched games to be saved as planned）
                                LoLGame_timeline_export = LoLGame_info_export #标记是否导出对局时间轴。时间轴的整理依赖于详细信息，因此目前认为这两者的值相同（Marks whether to export the match timeline. Timeline data sorting is based on the match information, so its value is set the same as the above）
                                #LoLGame_event_export = LoLGame_timeline_export #标记是否导出对局事件信息。由于事件信息源于时间轴，因此这两者的值在任何情形下是相同的（Marks whether to export the match events. Because events are extracted from the timeline, these two values should be the same under any circumstance）
                                LoLGame_info = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchID}")).json()
                                #logPrint(LoLGame_info)
                                LoLGame_timeline = await (await connection.request("GET", f"/lol-match-history/v1/game-timelines/{matchID}")).json()
                                #logPrint(LoLGame_timeline)

                                #尝试修复错误（Try to fix the error）
                                if "errorCode" in LoLGame_info:
                                    count = 0
                                    if LoLGame_info["httpStatus"] == 404:
                                        logPrint(f"未找到序号为{matchID}的回放文件！将忽略该序号。\nMatch file with matchID {matchID} not found! The program will ignore this matchID.")
                                        matches_not_found.append(matchID)
                                        continue
                                    if "500 Internal Server Error" in LoLGame_info["message"]:
                                        if not error_occurred:
                                            logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_info and "500 Internal Server Error" in LoLGame_info["message"] and count <= 3:
                                            count += 1
                                            logPrint("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                                            LoLGame_info = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchID}")).json()
                                    elif "Connection timed out after " in LoLGame_info["message"]:
                                        fetched_info = False
                                        logPrint("对局信息保存超时！请检查网速状况！\nGame information saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                                    elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"]:
                                        if not error_occurred:
                                            logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_info and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"] and count <= 3:
                                            count += 1
                                            logPrint("正在第%d次尝试获取对局%d信息……\nTimes trying to capture Match %d: No. %d ..." %(count, matchID, matchID, count))
                                            LoLGame_info = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchID}")).json()
                                    elif "could not convert GAMHS data to match-history format" in LoLGame_info["message"]:
                                        TFTGame = True
                                    if count > 3:
                                        fetched_info = False
                                        logPrint("对局%d信息获取失败！\nMatch %d information capture failure!" %(matchID, matchID))
                                if "errorCode" in LoLGame_timeline:
                                    count = 0
                                    if "500 Internal Server Error" in LoLGame_timeline["message"] or "Missing a closing quotation mark in string" in LoLGame_timeline["message"]:
                                        if not error_occurred:
                                            logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_timeline and ("500 Internal Server Error" in LoLGame_timeline["message"] or "Missing a closing quotation mark in string" in LoLGame_timeline["message"]) and count <= 3:
                                            count += 1
                                            logPrint("正在第%d次尝试获取对局%d时间轴……\nTimes trying to capture Match %d timeline: No. %d ..." %(count, matchID, matchID, count))
                                            LoLGame_timeline = await (await connection.request("GET", f"/lol-match-history/v1/game-timelines/{matchID}")).json()
                                    elif "Connection timed out after " in LoLGame_timeline["message"]:
                                        fetched_timeline = False
                                        logPrint("对局时间轴保存超时！请检查网速状况！\nGame timeline saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                                    elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_timeline["message"]:
                                        if not error_occurred:
                                            logPrint("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_timeline and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_timeline["message"] and count <= 3:
                                            count += 1
                                            logPrint("正在第%d次尝试获取对局%d时间轴……\nTimes trying to capture Match %d timeline: No. %d ..." %(count, matchID, matchID, count))
                                            LoLGame_timeline = await (await connection.request("GET", f"/lol-match-history/v1/game-timelines/{matchID}")).json()
                                    elif "could not convert GAMHS data to match-history format" in LoLGame_timeline["message"]:
                                        fetched_timeline = False
                                        if LoLGame_info["gameMode"] == "CHERRY":
                                            logPrint("斗魂竞技场模式不支持查询时间轴！\nTimeline crawling isn't supported in CHERRY matches!")
                                        else:
                                            logPrint("时间轴加载失败。\nFailed to load timeline.")
                                    if count > 3:
                                        fetched_timeline = False
                                        logPrint("对局%d时间轴获取失败！\nMatch %d timeline capture failure!" %(matchID, matchID))
                                
                                #信息（Information）
                                if "errorCode" in LoLGame_info:
                                    logPrint(LoLGame_info, end = "\n\n")
                                    info_exist_error[matchID] = True
                                    error_LoLMatchIDs.append(matchID)
                                    for i in error_header:
                                        LoLGame_info_error = {"项目": list(error_header.values()), "items": list(error_header.keys()), "值": [LoLGame_info[j] for j in error_header_keys]}
                                        LoLGame_info_df = pandas.DataFrame(data = LoLGame_info_error)
                                else:
                                    reserve = LoLGame_info_export #决定是否保存对局的文本文档。match_reserve_strategy变量决定的是是否将不包含主召唤师的对局记录导出到Excel中（Decides whether to save the matches into json files. The variable match_reserve_strategy decides whether to export the matches which don't include the main summoner into Excel）
                                    participant_puuid = []
                                    participant_summonerName = []
                                    participant_gameName = []
                                    for i in LoLGame_info["participantIdentities"]:
                                        participant_puuid.append(i["player"]["puuid"])
                                        participant_summonerName.append(i["player"]["summonerName"])
                                        participant_gameName.append(i["player"]["gameName"] + "#" + i["player"]["tagLine"])
                                    if current_puuid in participant_puuid: #之所以使用玩家通用唯一识别码，而不是用召唤师名称来识别对局是否包含主玩家，是因为该玩家可能使用过改名卡。这里也没有选择帐户序号，这是因为保存在对局中的各玩家的帐户序号竟然是0！（The reason why the puuid instead of the displayName or summonerName is used to identify whether the matches contain the main player is that the player may have used name changing card. AccountId isn't chosen here, because all players' accountIds saved in the match fetched from 127 API is 0, to my surprise!）
                                        main_player_included[matchID] = True
                                        match_reserve_strategy[matchID] = True
                                    elif current_summonerName in participant_gameName: #在玩家通用唯一识别码发生变动的大区，要识别变动之前的对局是否包含主玩家，最好的办法是依据显示名。因为在引入昵称编号后，显示名就固定下来，没有办法变动了，玩家只能通过改名卡修改玩家昵称和昵称编号。也就是说，显示名可视为玩家的另一种“身份识别码”。对于在引入昵称编号后注册的玩家，其显示名是空字符串，所以在模糊定位时用玩家昵称代替（On servers that changed the players' puuids once, to identify whether the matches before this change include this player, the best strategy is to refer to the displayName. This is because after tagLine is introduced, displayName is locked and there's no way of changing it. What the player can change through the Summmoner Name Change is gameName and tagLine. That is to say, displayName may be regarded as another ID of a player. For those who signed up after tagLine was introduced, their displayNames are empty strings. So gameName is taken for the rough localization）
                                        main_player_included[matchID] = True
                                        match_reserve_strategy[matchID] = True
                                        if not puuid_change_warning_printed:
                                            logPrint("警告：该大区的玩家通用唯一识别码曾发生变动！请检查保存的各对局是否属于该玩家。\nWarning: The puuids of players on this server have been changed! Please check if the saved matches really belong to this player.")
                                            puuid_change_warning_printed = True
                                    else:
                                        main_player_included[matchID] = False
                                        reserve = args.reserve_text #由于从文本文件中可以提取该召唤师的对局序号，所以需要保证保留下来的文本文件都包含该召唤师。因此，如果一场对局不包含该召唤师，就不应该把这场对局保存下来（Because a summoner's matchIDs can be extracted from the saved json files, it needs to be guaranteed that all saved json files belong to this summoner. Therefore, if a match doesn't include this summoner, then it shouldn't be saved into json files）
                                        if args.reserve:
                                            match_reserve = True
                                            logPrint("[%d/%d]对局%d不包含该玩家！已保持该对局。\nMatch %d doesn't include the current player but is reserved." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, matchID))
                                        else:
                                            if not match_notbelonging_warning_printed:
                                                logPrint("警告：对局%d不包含该玩家！是否仍要保持该对局？（输入任意键以保留该对局，否则舍弃该对局）\nWarning: The Match %d doesn't include the current player! Continue? (Input any nonempty string to reserve this match, or null to abandon it.)\n注意：此改动对于后续情形也生效。\nNote: This decision takes effect in similar situations later." %(matchID, matchID))
                                                match_reserve_str = logInput()
                                                match_reserve = bool(match_reserve_str)
                                                match_notbelonging_warning_printed = True
                                            elif match_reserve:
                                                logPrint("[%d/%d]对局%d不包含该玩家！已保持该对局。\nMatch %d doesn't include the current player but is reserved." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, matchID))
                                            else:
                                                logPrint("[%d/%d]对局%d不包含该玩家！已舍弃该对局。\nMatch %d doesn't include the current player and is decrepated." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, matchID))
                                        match_reserve_strategy[matchID] = match_reserve
                                    info_exist_error[matchID] = False
                                    currentPlatformId = LoLGame_info["participantIdentities"][0]["player"]["currentPlatformId"]
                                    save = True #指示保存是否成功，成功则输出保存进度，不成功则提示生成失败（Indicates whether the saving process is successful. If so, output the saving process, otherwise give a hint of generation failure）
                                    if export_json and reserve:
                                        json7name = f"Match Information (LoL) - {currentPlatformId}-{matchID}.json"
                                        while True:
                                            try:
                                                jsonfile7 = open(os.path.join(folder, json7name), "w", encoding = "utf-8")
                                            except FileNotFoundError:
                                                os.makedirs(folder, exist_ok = True)
                                            else:
                                                break
                                        try:
                                            jsonfile7.write(json.dumps(LoLGame_info, indent = 4, ensure_ascii = False))
                                        except UnicodeEncodeError:
                                            logPrint("对局%d信息文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nMatch %d information text generation failure! Please check if the summoner name includes any abnormal characters!" %(matchID, matchID))
                                            save = False
                                        jsonfile7.close()
                                        currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                                        pkl7name = f"Intermediate Object - Match Information (LoL) - {currentPlatformId}-{matchID}.pkl"
                                        #with open(os.path.join(folder, pkl7name), "wb") as IntObj6:
                                            #pickle.dump(LoLGame_info, IntObj6)
                                        json8name = f"Match Timeline (LoL) - {currentPlatformId}-{matchID}.json"
                                        while True:
                                            try:
                                                jsonfile8 = open(os.path.join(folder, json8name), "w", encoding = "utf-8")
                                            except FileNotFoundError:
                                                os.makedirs(folder, exist_ok = True)
                                            else:
                                                break
                                        try:
                                            jsonfile8.write(json.dumps(LoLGame_timeline, indent = 4, ensure_ascii = False))
                                        except UnicodeEncodeError:
                                            logPrint("对局%d时间轴文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nMatch %d timeline text generation failure! Please check if the summoner name includes any abnormal characters!" %(matchID, matchID))
                                            save = False
                                        jsonfile8.close()
                                        currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                                        pkl8name = f"Intermediate Object - Match Timeline (LoL) - {currentPlatformId}-{matchID}.pkl"
                                        #with open(os.path.join(folder, pkl8name), "wb") as IntObj7:
                                            #pickle.dump(LoLGame_timeline, IntObj7)
                                    if save:
                                        if export_json and reserve:
                                            logPrint('保存进度（Saving process）：%d/%d\t对局序号（MatchID）： %s' %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID), print_time = True)
                                        else:
                                            logPrint('加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %s' %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID), print_time = True)

                                    # challenger_ladder_queueTypes = await (await connection.request("GET", "/lol-ranked/v1/challenger-ladders-enabled")).json()
                                    # topRated_ladder_queueTypes = await (await connection.request("GET", "/lol-ranked/v1/top-rated-ladders-enabled")).json()
                                    # ranked_queueTypes = challenger_ladder_queueTypes + topRated_ladder_queueTypes
                                    # LoLGame_leaderboard_header = {"puuid": "玩家通用唯一识别码", "displayName": "显示名", "gameName": "玩家昵称", "tagLine": "昵称编号", "division": "分级", "isProvisional": "定位中", "leaguePoints": "胜点", "losses": "负场", "miniSeriesProgress": "定位赛/晋级赛进展", "provisionalGameThreshold": "总定位场次", "provisionalGamesRemaining": "剩余定位场次", "queueType": "战区", "ratedRating": "排名分", "ratedTier": "段位", "tier": "段位", "wins": "胜场", "tier / ratedTier": "段位", "leaguePoints / ratedRating": "胜点", "timestamp": "获取时间戳", "time": "获取时间"}
                                    # LoLGame_leaderboard_header_keys = list(LoLGame_leaderboard_header.keys())
                                    # LoLGame_leaderboard_data = {}
                                    # for i in range(len(LoLGame_leaderboard_header_keys)):
                                    #     key = LoLGame_leaderboard_header_keys[i]
                                    #     LoLGame_leaderboard_data[key] = []
                                    # for queueType in ranked_queueTypes:
                                    #     LoLGame_leaderboard = await (await connection.request("GET", "/lol-ranked/v1/social-leaderboard-ranked-queue-stats-for-puuids?queueType=%s&puuids=%s" %(queueType, str(participant_puuid).replace(" ", "").replace("'", '"')))).json()
                                    #     for participant_puuid_iter in LoLGame_leaderboard:
                                    #         participant_leaderboard = LoLGame_leaderboard[participant_puuid_iter]
                                    #         participantInfo = await get_info(connection, participant_puuid_iter)
                                    #         if participantInfo["info_got"]:
                                    #             participantInfo_body = participantInfo["body"]
                                    #             for i in range(len(LoLGame_leaderboard_header_keys)):
                                    #                 key = LoLGame_leaderboard_header_keys[i]
                                    #                 if i <= 3:
                                    #                     LoLGame_leaderboard_data[key].append(participantInfo_body[key])
                                    #                 elif i <= 15:
                                    #                     if i == 4: #分级（`division`）
                                    #                         LoLGame_leaderboard_data[key].append("" if participant_leaderboard["division"] == "NA" else participant_leaderboard["division"])
                                    #                     elif i == 11: #战区（`queueType`）
                                    #                         LoLGame_leaderboard_data[key].append(queueTypes[participant_leaderboard["queueType"]])
                                    #                     elif i == 13: #段位（`ratedTier`）
                                    #                         LoLGame_leaderboard_data[key].append(ratedTiers[participant_leaderboard["ratedTier"]])
                                    #                     elif i == 14: #段位（`tier`）
                                    #                         LoLGame_leaderboard_data[key].append(tiers[participant_leaderboard["tier"]])
                                    #                     else:
                                    #                         LoLGame_leaderboard_data[key].append(participant_leaderboard[key])
                                    #                 elif i == 16: #段位（`tier / ratedTier`）
                                    #                     LoLGame_leaderboard_data[key].append(ratedTiers[participant_leaderboard["ratedTier"]] if queueType in topRated_ladder_queueTypes else tiers[participant_leaderboard["tier"]])
                                    #                 elif i == 17: #胜点（`leaguePoints / ratedRating`）
                                    #                     LoLGame_leaderboard_data[key].append(participant_leaderboard["ratedRating"] if queueType in topRated_ladder_queueTypes else participant_leaderboard["leaguePoints"])
                                    #                 elif i == 18: #获取时间戳（`timestamp`）
                                    #                     LoLGame_leaderboard_data[key].append(time.time())
                                    #                 else: #获取时间（`time`）
                                    #                     LoLGame_leaderboard_data[key].append(time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime()))
                                    #         else:
                                    #             logPrint(participantInfo["message"])
                                    # LoLGame_leaderboard_statistics_output_order = [11, 1, 2, 3, 0, 16, 4, 17, 15, 7, 5, 9, 10, 8, 19]
                                    # LoLGame_leaderboard_data_organized = {}
                                    # for i in LoLGame_leaderboard_statistics_output_order:
                                    #     key = LoLGame_leaderboard_header_keys[i]
                                    #     LoLGame_leaderboard_data_organized[key] = LoLGame_leaderboard_data[key]
                                    # LoLGame_leaderboard_df = pandas.DataFrame(data = LoLGame_leaderboard_data_organized)
                                    # for column in LoLGame_leaderboard_df:
                                    #     if LoLGame_leaderboard_df[column].dtype == "bool":
                                    #         LoLGame_leaderboard_df[column] = LoLGame_leaderboard_df[column].astype(str)
                                    #         for i in range(len(LoLGame_leaderboard_df)):
                                    #             LoLGame_leaderboard_df.loc[i, column] = "√" if LoLGame_leaderboard_df[column][i] == "True" else ""
                                    # LoLGame_leaderboard_df = pandas.concat([pandas.DataFrame([LoLGame_leaderboard_header])[LoLGame_leaderboard_df.columns], LoLGame_leaderboard_df], ignore_index = True)
                                    
                                    version = LoLGame_info["gameVersion"]
                                    bigVersion = ".".join(version.split(".")[:2])
                                    LoLGame_info_data = {} #这里将对局的数据放在一个字典中，键为统计量，值为由所有玩家的数据组成的列表（Here the whole match data are stored in a dictionary whose keys are statistics and values are lists composed of corresponding data of all players）
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
                                    #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                                    ##召唤师图标（Summoner icon）
                                    summonerIconIds_match_list = sorted(set(map(lambda x: x["player"]["profileIcon"], LoLGame_info["participantIdentities"])))
                                    for i in summonerIconIds_match_list:
                                        if not i in summonerIcons and current_versions["summonerIcon"] != bigVersion:
                                            summonerIconPatch_adopted = bigVersion
                                            summonerIcon_recapture = 1
                                            logPrint("第%d/%d场对局（对局序号：%d）召唤师图标信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师图标信息……\nSummoner icon information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to summoner icons of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, summonerIcon_recapture, summonerIconPatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, summonerIconPatch_adopted, summonerIcon_recapture))
                                            while True:
                                                try:
                                                    summonerIcon = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-icons.json" %(summonerIconPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    summonerIconPatch_deserted = summonerIconPatch_adopted
                                                    summonerIconPatch_adopted = FindPostPatch(summonerIconPatch_adopted, bigPatches)
                                                    summonerIcon_recapture = 1
                                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(summonerIconPatch_deserted, summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_deserted, summonerIconPatch_adopted, summonerIcon_recapture))
                                                except requests.exceptions.RequestException:
                                                    if summonerIcon_recapture < 3:
                                                        summonerIcon_recapture += 1
                                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师图标信息……\nYour network environment is abnormal! Changing to summoner icons of Patch %s ... Times tried: %d." %(summonerIcon_recapture, summonerIconPatch_adopted, summonerIconPatch_adopted, summonerIcon_recapture))
                                                    else:
                                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师图标信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the summoner icon (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        break
                                                else:
                                                    logPrint("已改用%s版本的召唤师图标信息。\nSummoner icon information changed to Patch %s." %(summonerIconPatch_adopted, summonerIconPatch_adopted))
                                                    summonerIcons = {}
                                                    for summonerIcon_iter in summonerIcon:
                                                        summonerIcon_id = summonerIcon_iter["id"]
                                                        summonerIcons[summonerIcon_id] = summonerIcon_iter
                                                    current_versions["summonerIcon"] = summonerIconPatch_adopted
                                                    unmapped_keys["summonerIcon"].clear()
                                                    break
                                            break
                                    ##英雄：包含选用英雄和禁用英雄（LoL champions, which contain picked and banned ones）
                                    LoLChampionIds_match_list = sorted(set(map(lambda x: x["championId"], LoLGame_info["participants"])) | set(map(lambda x: x["championId"], bans)))
                                    for i in LoLChampionIds_match_list:
                                        if not i in LoLChampions and current_versions["LoLChampion"] != bigVersion:
                                            LoLChampionPatch_adopted = bigVersion
                                            LoLChampion_recapture = 1
                                            logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄信息……\nLoL champion information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, LoLChampion_recapture, LoLChampionPatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLChampionPatch_adopted, LoLChampion_recapture))
                                            while True:
                                                try:
                                                    LoLChampion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(LoLChampionPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    LoLChampionPatch_deserted = LoLChampionPatch_adopted
                                                    LoLChampionPatch_adopted = FindPostPatch(LoLChampionPatch_adopted, bigPatches)
                                                    LoLChampion_recapture = 1
                                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampionPatch_deserted, LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_deserted, LoLChampionPatch_adopted, LoLChampion_recapture))
                                                except requests.exceptions.RequestException:
                                                    if LoLChampion_recapture < 3:
                                                        LoLChampion_recapture += 1
                                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄信息……\nYour network environment is abnormal! Changing to LoL champions of Patch %s ... Times tried: %d." %(LoLChampion_recapture, LoLChampionPatch_adopted, LoLChampionPatch_adopted, LoLChampion_recapture))
                                                    else:
                                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL champion (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        break
                                                else:
                                                    logPrint("已改用%s版本的英雄信息。\nLoL champion information changed to Patch %s." %(LoLChampionPatch_adopted, LoLChampionPatch_adopted))
                                                    LoLChampions = {}
                                                    for LoLChampion_iter in LoLChampion:
                                                        LoLChampion_id = LoLChampion_iter["id"]
                                                        LoLChampions[LoLChampion_id] = LoLChampion_iter
                                                    current_versions["LoLChampion"] = LoLChampionPatch_adopted
                                                    unmapped_keys["LoLChampion"].clear()
                                                    break
                                            break
                                    ##召唤师技能（Summoner spells）
                                    spellIds_match_list = sorted(set(map(lambda x: x["spell1Id"], LoLGame_info["participants"])) | set(map(lambda x: x["spell2Id"], LoLGame_info["participants"])))
                                    for i in spellIds_match_list:
                                        if not i in spells and current_versions["spell"] != bigVersion and i != 0: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                                            spellPatch_adopted = bigVersion
                                            spell_recapture = 1
                                            logPrint("第%d/%d场对局（对局序号：%d）召唤师技能信息（%d）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, spell_recapture, spellPatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellPatch_adopted, spell_recapture))
                                            while True:
                                                try:
                                                    spell = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    spellPatch_deserted = spellPatch_adopted
                                                    spellPatch_adopted = FindPostPatch(spellPatch_adopted, bigPatches)
                                                    spell_recapture = 1
                                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to spells of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture))
                                                except requests.exceptions.RequestException:
                                                    if spell_recapture < 3:
                                                        spell_recapture += 1
                                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture))
                                                    else:
                                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        break
                                                else:
                                                    logPrint("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted))
                                                    spells = {}
                                                    for spell_iter in spell:
                                                        spell_id = spell_iter["id"]
                                                        spells[spell_id] = spell_iter
                                                    current_versions["spell"] = spellPatch_adopted
                                                    unmapped_keys["spell"].clear()
                                                    break
                                            break
                                    ##英雄联盟装备（LoL items）
                                    LoLItemIds_match_list = sorted(set(item for s in [set(map(lambda x: x["stats"]["item" + str(i)], LoLGame_info["participants"])) for i in range(7)] for item in s)) #该表达式等价于以下表达式（This expression is equivalent to the following expression）：`LoLItemIds_match_list = sorted(set(map(lambda x: x["stats"]["item0"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["item1"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["item2"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["item3"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["item4"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["item5"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["item6"], LoLGame_info["participants"])))`
                                    for i in LoLItemIds_match_list:
                                        if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                                            LoLItemPatch_adopted = bigVersion
                                            LoLItem_recapture = 1
                                            logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, LoLItem_recapture, LoLItemPatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemPatch_adopted, LoLItem_recapture))
                                            while True:
                                                try:
                                                    LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    LoLItemPatch_deserted = LoLItemPatch_adopted
                                                    LoLItemPatch_adopted = FindPostPatch(LoLItemPatch_adopted, bigPatches)
                                                    LoLItem_recapture = 1
                                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                                                except requests.exceptions.RequestException:
                                                    if LoLItem_recapture < 3:
                                                        LoLItem_recapture += 1
                                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
                                                    else:
                                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        break
                                                else:
                                                    logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted))
                                                    LoLItems = {}
                                                    for LoLItem_iter in LoLItem:
                                                        LoLItem_id = LoLItem_iter["id"]
                                                        LoLItems[LoLItem_id] = LoLItem_iter
                                                    current_versions["LoLItem"] = LoLItemPatch_adopted
                                                    unmapped_keys["LoLItem"].clear()
                                                    break
                                            break
                                    ##符文（Perks）
                                    perkIds_match_list = sorted(set(perk for s in [set(map(lambda x: x["stats"]["perk" + str(i)], LoLGame_info["participants"])) for i in range(6)] for perk in s))
                                    for i in perkIds_match_list:
                                        if not i in perks and current_versions["perk"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                            perkPatch_adopted = bigVersion
                                            perk_recapture = 1
                                            logPrint("第%d/%d场对局（对局序号：%d）基石符文信息（%d）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nPerk information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to perks of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, perk_recapture, perkPatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkPatch_adopted, perk_recapture))
                                            while True:
                                                try:
                                                    perk = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    perkPatch_deserted = perkPatch_adopted
                                                    perkPatch_adopted = FindPostPatch(perkPatch_adopted, bigPatches)
                                                    perk_recapture = 1
                                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture))
                                                except requests.exceptions.RequestException:
                                                    if perk_recapture < 3:
                                                        perk_recapture += 1
                                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to perks of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture))
                                                    else:
                                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perk (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        break
                                                else:
                                                    logPrint("已改用%s版本的基石符文信息。\nPerk information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted))
                                                    perks = {}
                                                    for perk_iter in perk:
                                                        perk_id = perk_iter["id"]
                                                        perks[perk_id] = perk_iter
                                                    current_versions["perk"] = perkPatch_adopted
                                                    unmapped_keys["perk"].clear()
                                                    break
                                            break
                                    ##符文系（Perkstyles）
                                    perkstyleIds_match_list = sorted(list(set(map(lambda x: x["stats"]["perkPrimaryStyle"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["perkSubStyle"], LoLGame_info["participants"]))))
                                    for i in perkstyleIds_match_list:
                                        if not i in perkstyles and current_versions["perkstyle"] != bigVersion and i != 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                            perkstylePatch_adopted = bigVersion
                                            perkstyle_recapture = 1
                                            logPrint("第%d/%d场对局（对局序号：%d）符文系信息（%d）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, perkstyle_recapture, perkstylePatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkstylePatch_adopted, perkstyle_recapture))
                                            while True:
                                                try:
                                                    perkstyle = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    perkstylePatch_deserted = perkstylePatch_adopted
                                                    perkstylePatch_adopted = FindPostPatch(perkstylePatch_adopted, bigPatches)
                                                    perkstyle_recapture = 1
                                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perks of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture))
                                                except requests.exceptions.RequestException:
                                                    if perkstyle_recapture < 3:
                                                        perkstyle_recapture += 1
                                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture))
                                                    else:
                                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyle (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        break
                                                else:
                                                    logPrint("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted))
                                                    perkstyles = {}
                                                    for perkstyle_iter in perkstyle["styles"]:
                                                        perkstyle_id = perkstyle_iter["id"]
                                                        perkstyles[perkstyle_id] = perkstyle_iter
                                                    current_versions["perkstyle"] = perkstylePatch_adopted
                                                    unmapped_keys["perkstyle"].clear()
                                                    break
                                            break
                                    ##斗魂竞技场强化符文（Cherry augments）
                                    CherryAugmentIds_match_list = sorted(set(augment for s in [set(map(lambda x: x["stats"]["playerAugment" + str(i)], LoLGame_info["participants"])) for i in range(1, 7)] for augment in s)) #该表达式等价于以下表达式（This expression is equivalent to the following expression）：CherryAugmentIds_match_list = sorted(list(set(map(lambda x: x["stats"]["playerAugment1"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["playerAugment2"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["playerAugment3"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["playerAugment4"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["playerAugment5"], LoLGame_info["participants"])) | set(map(lambda x: x["stats"]["playerAugment6"], LoLGame_info["participants"]))))
                                    for i in CherryAugmentIds_match_list:
                                        if not i in CherryAugments and current_versions["CherryAugment"] != bigVersion and i != 0:
                                            CherryAugmentPatch_adopted = bigVersion
                                            CherryAugment_recapture = 1
                                            logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%d）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nAugment information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to Cherry augments of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, CherryAugment_recapture, CherryAugmentPatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                            while True:
                                                try:
                                                    CherryAugment = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/cherry-augments.json" %(CherryAugmentPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    CherryAugmentPatch_deserted = CherryAugmentPatch_adopted
                                                    CherryAugmentPatch_adopted = FindPostPatch(CherryAugmentPatch_adopted, bigPatches)
                                                    CherryAugment_recapture = 1
                                                    logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugmentPatch_deserted, CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_deserted, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                                except requests.exceptions.RequestException:
                                                    if CherryAugment_recapture < 3:
                                                        CherryAugment_recapture += 1
                                                        logPrint("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Cherry augments of Patch %s ... Times tried: %d." %(CherryAugment_recapture, CherryAugmentPatch_adopted, CherryAugmentPatch_adopted, CherryAugment_recapture))
                                                    else:
                                                        logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Cherry augment (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        break
                                                else:
                                                    logPrint("已改用%s版本的斗魂竞技场强化符文信息。\nCherry augment information changed to Patch %s." %(CherryAugmentPatch_adopted, CherryAugmentPatch_adopted))
                                                    CherryAugments = {}
                                                    for CherryAugment_iter in CherryAugment:
                                                        CherryAugment_id = CherryAugment_iter["id"]
                                                        CherryAugments[CherryAugment_id] = CherryAugment_iter
                                                    current_versions["CherryAugment"] = CherryAugmentPatch_adopted
                                                    unmapped_keys["CherryAugment"].clear()
                                                    break
                                            break
                                    #下面开始整理数据（Sorts out the data）
                                    player_count = len(LoLGame_info["participantIdentities"])
                                    for i in range(len(LoLGame_info_header)): #考虑到i按照代码中LoLGame_info_header的键的顺序遍历字典，可以将中间同一级别的属性按照相同方法输出。于是有了接下来的一些判断语句（Considering variable i traverses the dictionary following the order of LoLGame_info_header's keys, attributes under the same level can be output in the same manner. That's why there're several If-statements in the following code）
                                        key = LoLGame_info_header_keys[i]
                                        LoLGame_info_data[key] = [] #各项目初始化（Initialize every feature / column）
                                    for i in range(player_count):
                                        stats = LoLGame_info["participants"][i]["stats"]
                                        timeline = LoLGame_info["participants"][i]["timeline"]
                                        team_participants = [participant for participant in LoLGame_info["participants"] if LoLGame_info["gameMode"] == "CHERRY" and participant["stats"]["playerSubteamId"] == stats["playerSubteamId"] or LoLGame_info["gameMode"] != "CHERRY" and participant["teamId"] == LoLGame_info["participants"][i]["teamId"]] #存储对局信息中同一队伍的玩家。斗魂竞技场对局应该使用子阵营（Store the participants of the same team from the game information. Subteam should be used to evaluate a player）
                                        for j in range(len(LoLGame_info_header)):
                                            key = LoLGame_info_header_keys[j]
                                            if j == 0: #游戏序号（`gameIndex`）
                                                LoLGame_info_data[key].append(LoLMatchIDs.index(matchID) + 1)
                                            elif j <= 12:
                                                if j == 1: #对局终止情况（`endOfGameResult`）
                                                    LoLGame_info_data[key].append(endOfGameResults[LoLGame_info["endOfGameResult"]])
                                                elif j == 3: #创建日期（`gameCreationDate`）
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
                                                if j >= 25: #召唤师图标相关键（Profile icon-related keys）
                                                    profileIconId = LoLGame_info["participantIdentities"][i]["player"]["profileIcon"]
                                                    if profileIconId in summonerIcons:
                                                        try:
                                                            LoLGame_info_data[key].append(summonerIcons[profileIconId][key.split("_")[-1]])
                                                        except KeyError:
                                                            traceback_info = traceback.format_exc()
                                                            logPrint(traceback_info)
                                                            LoLGame_info_data[key].append("")
                                                    elif profileIconId in summonerIcons_initial:
                                                        try:
                                                            LoLGame_info_data[key].append(summonerIcons_initial[profileIconId][key.split("_")[-1]])
                                                        except KeyError:
                                                            traceback_info = traceback.format_exc()
                                                            logPrint(traceback_info)
                                                            LoLGame_info_data[key].append("")
                                                    else:
                                                        if not profileIconId in unmapped_keys["summonerIcon"]:
                                                            unmapped_keys["summonerIcon"].add(profileIconId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）召唤师图标信息（%d）获取失败！将采用原始数据！\n[%d. %s] Summoner icon information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, profileIconId, j, key, profileIconId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLGame_info_data[key].append(profileIconId if j == 25 else "")
                                                else:
                                                    LoLGame_info_data[key].append(LoLGame_info["participantIdentities"][i]["player"][key])
                                            elif j <= 39:
                                                if j == 28: #最高段位（`highestAchievedSeasonTier`）
                                                    LoLGame_info_data[key].append(tiers[LoLGame_info["participants"][i]["highestAchievedSeasonTier"]])
                                                elif j >= 32 and j <= 34: #选用英雄序号相关键（`championId`-related keys）
                                                    championId = LoLGame_info["participants"][i][key.split("_")[0] + "Id"]
                                                    if championId in LoLChampions:
                                                        LoLGame_info_data[key].append(LoLChampions[championId][key.split("_")[-1]])
                                                    elif championId in LoLChampions_initial:
                                                        LoLGame_info_data[key].append(LoLChampions_initial[championId][key.split("_")[-1]])
                                                    else:
                                                        if not championId in unmapped_keys["LoLChampion"]:
                                                            unmapped_keys["LoLChampion"].add(championId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLGame_info_data[key].append(championId if j == 32 else "")
                                                elif j >= 35 and j <= 38: #召唤师技能序号相关键（SpellIds-related keys）
                                                    spellId = LoLGame_info["participants"][i][key.split("_")[0] + "Id"]
                                                    if spellId in spells:
                                                        LoLGame_info_data[key].append(spells[spellId][key.split("_")[-1]])
                                                    elif spellId in spells_initial:
                                                        LoLGame_info_data[key].append(spells_initial[spellId][key.split("_")[-1]])
                                                    else:
                                                        if not spellId in unmapped_keys["spell"]:
                                                            unmapped_keys["spell"].add(spellId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）召唤师技能信息（%d）获取失败！将采用原始数据！\n[%d. %s] Spell information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, spellId, j, key, spellId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                        LoLGame_info_data[key].append(spellId if j <= 36 else "")
                                                elif j == 39: #阵营（`team_color`）
                                                    LoLGame_info_data[key].append(team_color[LoLGame_info["participants"][i]["teamId"]])
                                                else:
                                                    LoLGame_info_data[key].append(LoLGame_info["participants"][i][key])
                                            elif j <= 215:
                                                if j >= 153 and j <= 166: #英雄联盟装备相关键（LoLItems-related keys）
                                                    itemId = stats[key.split("_")[0]]
                                                    if itemId == 0:
                                                        LoLGame_info_data[key].append("")
                                                    elif itemId in LoLItems:
                                                        LoLGame_info_data[key].append(LoLItems[itemId][key.split("_")[-1]])
                                                    elif itemId in LoLItems_initial:
                                                        LoLGame_info_data[key].append(LoLItems_initial[itemId][key.split("_")[-1]])
                                                    else:
                                                        if not itemId in unmapped_keys["LoLItem"]:
                                                            unmapped_keys["LoLItem"].add(itemId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, itemId, j, key, itemId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
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
                                                        elif perkId in perks_initial:
                                                            perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perks_initial[perkId]["endOfGameStatDescs"])))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(stats[key[:5] + "Var1"]))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(stats[key[:5] + "Var2"]))
                                                            perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(stats[key[:5] + "Var3"]))
                                                            LoLGame_info_data[key].append(perk_EndOfGameStatDescs)
                                                        else:
                                                            if not perkId in unmapped_keys["perk"]:
                                                                unmapped_keys["perk"].add(perkId)
                                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, perkId, j, key, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                            LoLGame_info_data[key].append("")
                                                    else:
                                                        perkId = stats[key.split("_")[0]]
                                                        if perkId == 0:
                                                            LoLGame_info_data[key].append("")
                                                        elif perkId in perks:
                                                            LoLGame_info_data[key].append(perks[perkId][key.split("_")[-1]])
                                                        elif perkId in perks_initial:
                                                            LoLGame_info_data[key].append(perks_initial[perkId][key.split("_")[-1]])
                                                        else:
                                                            if not perkId in unmapped_keys["perk"]:
                                                                unmapped_keys["perk"].add(perkId)
                                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Runes information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, perkId, j, key, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                            LoLGame_info_data[key].append(perkId if j <= 178 else "")
                                                elif j >= 185 and j <= 188: #符文系相关键（Perkstyles-related keys）
                                                    perkstyleId = stats[key.split("_")[0]]
                                                    if perkstyleId == 0:
                                                        LoLGame_info_data[key].append("")
                                                    elif perkstyleId in perkstyles:
                                                        LoLGame_info_data[key].append(perkstyles[perkstyleId][key.split("_")[-1]])
                                                    elif perkstyleId in perkstyles_initial:
                                                        LoLGame_info_data[key].append(perkstyles_initial[perkstyleId][key.split("_")[-1]])
                                                    else:
                                                        if not perkstyleId in unmapped_keys["perkstyle"]:
                                                            unmapped_keys["perkstyle"].add(perkstyleId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）符文系信息（%d）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, perkstyleId, j, key, perkstyleId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
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
                                                    elif CherryAugmentId in CherryAugments_initial:
                                                        if j <= 194: #强化符文名称（`nameTRA`）
                                                            LoLGame_info_data[key].append(CherryAugments_initial[CherryAugmentId][key.split("_")[-1]])
                                                        elif j <= 200: #强化符文图标路径（`augmentIconPath`）
                                                            LoLGame_info_data[key].append(CherryAugments_initial[CherryAugmentId]["augmentSmallIconPath"].replace("_small.png", "_large.png"))
                                                        else: #强化符文等级（`rarity`）
                                                            LoLGame_info_data[key].append(augment_rarity[CherryAugments_initial[CherryAugmentId][key.split("_")[-1]]])
                                                    else:
                                                        if not CherryAugmentId in unmapped_keys["CherryAugment"]:
                                                            unmapped_keys["CherryAugment"].add(CherryAugmentId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）强化符文信息（%d）获取失败！将采用原始数据！\n[%d. %s] Cherry augment information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, CherryAugmentId, j, key, CherryAugmentId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
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
                                                                        elif championId in LoLChampions_initial:
                                                                            to_append.append(LoLChampions_initial[championId][key.split("_")[-1]])
                                                                        else:
                                                                            if not championId in unmapped_keys["LoLChampion"]:
                                                                                unmapped_keys["LoLChampion"].add(championId)
                                                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
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
                                                                        elif championId in LoLChampions_initial:
                                                                            to_append.append(LoLChampions_initial[championId][key.split("_")[-1]])
                                                                        else:
                                                                            if not championId in unmapped_keys["LoLChampion"]:
                                                                                unmapped_keys["LoLChampion"].add(championId)
                                                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
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
                                                                elif championId in LoLChampions_initial:
                                                                    LoLGame_info_data[key].append(LoLChampions_initial[championId][key.split("_")[-1]])
                                                                else:
                                                                    if not championId in unmapped_keys["LoLChampion"]:
                                                                        unmapped_keys["LoLChampion"].add(championId)
                                                                        logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）英雄信息（%d）获取失败！将采用原始数据！\n[%d. %s] Champion information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, championId, j, key, championId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                                    LoLGame_info_data[key].append(championId if j == 217 else "")
                                            elif j <= 221: #时间轴相关键（Timeline-related keys）
                                                LoLGame_info_data[key].append(lanes[timeline[key]] if j == 220 else roles[timeline[key]])
                                            else: #对局信息转换键（Keys transformed according to game information）
                                                subkey = key.split("_")[0]
                                                if key.endswith("_percent"): #团队占比键（Team percentage keys）
                                                    if j == 280: #参团率（`KP_percent`）
                                                        self_stat = stats["kills"] + stats["assists"]
                                                        total_stat = sum(map(lambda x: x["stats"]["kills"], team_participants))
                                                    elif j == 281: #补刀数占比（`CS_percent`）
                                                        self_stat = stats["totalMinionsKilled"] + stats["neutralMinionsKilled"]
                                                        total_stat = sum(map(lambda x: x["stats"]["totalMinionsKilled"] + x["stats"]["neutralMinionsKilled"], team_participants))
                                                    else:
                                                        self_stat = stats[subkey]
                                                        total_stat = sum(map(lambda x: x["stats"][subkey], team_participants))
                                                    value = 0 if total_stat == 0 else self_stat / total_stat
                                                    LoLGame_info_data[key].append(value)
                                                else: #位次键（Order keys）
                                                    if j == 341: #战损比位次（`KDA_order`）
                                                        self_stat = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"])
                                                        stat_list = sorted(map(lambda x: (x["stats"]["kills"] + x["stats"]["assists"]) / max(1, x["stats"]["deaths"]), team_participants), reverse = True)
                                                    elif j == 342: #参团率位次（`KP_order`）
                                                        self_stat = stats["kills"] + stats["assists"]
                                                        stat_list = sorted(map(lambda x: x["stats"]["kills"] + x["stats"]["assists"], team_participants), reverse = True)
                                                    elif j == 343: #补刀数位次（`CS_order`）
                                                        self_stat = stats["totalMinionsKilled"] + stats["neutralMinionsKilled"]
                                                        stat_list = sorted(map(lambda x: x["stats"]["totalMinionsKilled"] + x["stats"]["neutralMinionsKilled"], team_participants), reverse = True)
                                                    elif j == 344: #伤害转化率位次（`D/G_order`）
                                                        self_stat = 0 if stats["goldEarned"] == 0 else stats["totalDamageDealtToChampions"] / stats["goldEarned"]
                                                        stat_list = sorted(map(lambda x: 0 if x["stats"]["goldEarned"] == 0 else x["stats"]["totalDamageDealtToChampions"] / x["stats"]["goldEarned"], team_participants), reverse = True)
                                                    elif j == 345: #金币利用率位次（`GUE_order`）
                                                        self_stat = 0 if stats["goldEarned"] == 0 else stats["goldSpent"] / stats["goldEarned"]
                                                        stat_list = sorted(map(lambda x: 0 if x["stats"]["goldEarned"] == 0 else x["stats"]["goldSpent"] / x["stats"]["goldEarned"], team_participants), reverse = True)
                                                    else:
                                                        self_stat = stats[subkey]
                                                        stat_list = sorted(map(lambda x: x["stats"][subkey], team_participants), reverse = j != 288) #死亡次数越低，死亡位次越小（For deaths, the lower the number of deaths is, the smaller the death order is）
                                                    LoLGame_info_data[key].append(0 if len(set(stat_list)) == 1 else stat_list.index(self_stat) + 1) #当所有人的数据一样时，则不用比较位次（When some stat of every player is the same, there's no need to compare it）
                                            if LoLGame_info["participantIdentities"][i]["player"]["puuid"] == current_puuid:
                                                LoLGame_stat_data[key].append(LoLGame_info_data[key][-1]) #直接添加最近一次追加的数据，以简化代码（Directly append the recently appended data to simplify the code） 
                                    #数据框列排序（Dataframe column sorting）
                                    LoLGame_info_statistics_output_order = [39, 207, 13, 23, 17, 24, 22, 21, 19, 16, 28, 32, 33, 217, 218, 220, 221, 42, 35, 36, 153, 154, 155, 156, 157, 158, 159, 189, 201, 190, 202, 191, 203, 192, 204, 193, 205, 194, 206, 69, 47, 40, 209, 210, 213, 214, 43, 138, 139, 71, 68, 72, 51, 50, 55, 54, 53, 52, 48, 142, 128, 81, 147, 132, 140, 134, 109, 75, 144, 133, 108, 74, 143, 70, 45, 44, 136, 141, 135, 110, 76, 145, 46, 148, 151, 150, 129, 149, 58, 211, 59, 212, 137, 77, 79, 78, 146, 60, 73, 185, 187, 173, 167, 174, 168, 175, 169, 176, 170, 177, 171, 178, 172, 41, 49, 131, 56, 57, 215, 130, 233, 227, 222, 280, 223, 267, 235, 232, 236, 228, 270, 259, 245, 275, 261, 268, 263, 247, 239, 272, 262, 246, 238, 271, 234, 225, 224, 265, 269, 264, 248, 240, 273, 226, 276, 279, 278, 260, 277, 229, 230, 266, 241, 243, 242, 281, 274, 231, 237, 283, 294, 288, 282, 341, 342, 344, 284, 328, 296, 293, 297, 289, 331, 320, 306, 336, 322, 329, 324, 308, 300, 333, 323, 307, 299, 332, 295, 286, 285, 326, 330, 325, 309, 301, 334, 287, 337, 340, 339, 321, 338, 290, 291, 345, 327, 302, 303, 304, 343, 335, 292, 298]
                                    LoLGame_info_data_organized = {}
                                    for i in LoLGame_info_statistics_output_order:
                                        key = LoLGame_info_header_keys[i]
                                        LoLGame_info_data_organized[key] = LoLGame_info_data[key]
                                    LoLGame_info_df = pandas.DataFrame(data = LoLGame_info_data_organized)
                                    for column in LoLGame_info_df:
                                        if LoLGame_info_df[column].dtype == "bool":
                                            LoLGame_info_df[column] = LoLGame_info_df[column].astype(str)
                                            for i in range(len(LoLGame_info_df)):
                                                LoLGame_info_df.loc[i, column] = "√" if LoLGame_info_df[column][i] == "True" else ""
                                    LoLGame_info_df = pandas.concat([pandas.DataFrame([LoLGame_info_header])[LoLGame_info_df.columns], LoLGame_info_df], ignore_index = True)
                                    LoLGame_info_df = LoLGame_info_df.stack().unstack(0) #实现对局信息的行列转置（Inverse the match information table）
                                
                                #时间轴（Timeline）
                                if LoLGame_timeline_export:
                                    if "errorCode" in LoLGame_timeline:
                                        timeline_exist_error[matchID] = True
                                        logPrint(LoLGame_timeline, end = "\n\n")
                                        for i in error_header:
                                            LoLGame_timeline_error = {"项目": list(error_header.values()), "items": list(error_header.keys()), "值": [LoLGame_timeline[j] for j in error_header_keys]}
                                            LoLGame_timeline_df = pandas.DataFrame(data = LoLGame_timeline_error)
                                            LoLGame_event_df = pandas.DataFrame(data = LoLGame_timeline_error)
                                    elif not "errorCode" in LoLGame_info: #在整理时间轴数据时，需要使用`LoLGame_info`中的一些数据（While sorting the timeline, some data in `LoLGame_info` are needed）
                                        timeline_exist_error[matchID] = False
                                        LoLGame_timeline_header = {"events": "事件", "timestamp": "时间戳", "time": "时间", "participantID": "玩家序号", "teamId": "阵营代号", "team_color": "阵营", "summonerName": "召唤师名称", "champion_name": "选用英雄", "champion_alias": "选用英雄代号", "currentGold": "当前金币余额", "dominionScore": "占领得分", "jungleMinionsKilled": "击杀野怪数", "level": "英雄等级", "minionsKilled": "击杀小兵数", "position": "当前位置坐标", "teamScore": "队伍得分", "totalGold": "金币获取", "xp": "经验值"}
                                        LoLGame_timeline_header_keys = list(LoLGame_timeline_header.keys())
                                        LoLGame_timeline_data = {}
                                        frames = LoLGame_timeline["frames"]
                                        for i in range(len(LoLGame_timeline_header)): #注意由于对局信息和对局时间轴是绑定在一起的，所以这里会用到构建LoLGame_info_df时的一些变量，包括player_count（Note that since the match information and match timeline are tied together, some variables during the creation of "LoLGame_info_df" will be reused in the following code, including player_count）
                                            key = LoLGame_timeline_header_keys[i]
                                            LoLGame_timeline_data[key] = [] #各项目初始化（Initialize every feature / column）
                                            if i <= 2:
                                                if i == 2: #时间（`time`）
                                                    for j in range(len(frames)):
                                                        LoLGame_timeline_data[key].append(lcuTimestamp(frames[j]["timestamp"] // 1000)) #使用lcuTimestamp函数将时间戳转化为时间（Use function lcuTimestamp to convert timestamp into time）
                                                        for k in range(player_count - 1):
                                                            LoLGame_timeline_data[key].append("") #考虑到每个时间戳和事件对应多个不同的玩家，只需要输出一次时间戳和事件，剩余部分为空，以保证表格对齐（Considering each timestamp and each event correspond to multiple participants, they only need to be output once, while the rest assigned by empty strings, so as to align the table）
                                                else:
                                                    for j in range(len(frames)):
                                                        LoLGame_timeline_data[key].append(frames[j][key])
                                                        for k in range(player_count - 1):
                                                            LoLGame_timeline_data[key].append("")
                                            elif i == 3: #玩家序号（`participantID`）
                                                for j in range(len(frames)):
                                                    for k in range(player_count):
                                                        LoLGame_timeline_data[key].append(k + 1)
                                            elif i <= 8:
                                                if i == 4: #阵营代号（`teamId`）
                                                    for j in range(len(frames)):
                                                        for k in range(player_count):
                                                            LoLGame_timeline_data[key].append(LoLGame_info["participants"][k]["teamId"])
                                                elif i == 5: #阵营代号（`team_color`）
                                                    for j in range(len(frames)):
                                                        for k in range(player_count):
                                                            LoLGame_timeline_data[key].append(team_color[LoLGame_info["participants"][k]["teamId"]])
                                                elif i == 6: #召唤师名称（`summonerName`）
                                                    for j in range(len(frames)):
                                                        for k in range(player_count):
                                                            LoLGame_timeline_data[key].append(LoLGame_info["participantIdentities"][k]["player"]["gameName"] + "#" + LoLGame_info["participantIdentities"][k]["player"]["tagLine"])
                                                else: #选用英雄相关键（Champion-related keys）
                                                    for j in range(len(frames)):
                                                        for k in range(player_count):
                                                            try:
                                                                LoLGame_timeline_data[key].append(LoLChampions[LoLGame_info["participants"][k]["championId"]][key.split("_")[1]])
                                                            except KeyError:
                                                                LoLGame_timeline_data[key].append("")
                                            else:
                                                if i == 14: #当前位置坐标（`position`）
                                                    for j in range(len(frames)):
                                                        for k in range(player_count):
                                                            try:
                                                                position = frames[j]["participantFrames"][str(k + 1)][key]
                                                                LoLGame_timeline_data[key].append("(%d, %d)" %(position["x"], position["y"]))
                                                            except KeyError:
                                                                LoLGame_timeline_data[key].append("")
                                                else:
                                                    for j in range(len(frames)):
                                                        for k in range(player_count):
                                                            try:
                                                                LoLGame_timeline_data[key].append(frames[j]["participantFrames"][str(k + 1)][key])
                                                            except KeyError: #部分自定义对局存在后续事件无内容的情况，即participantFrames为空（Some custom matches don't have anything in later events, namely the "participantFrames" parameter is empty. More details in PBE1-4422435386）
                                                                LoLGame_timeline_data[key].append("")
                                        LoLGame_timeline_statistics_output_order = [1, 2, 0, 5, 3, 6, 7, 8, 12, 17, 14, 13, 11, 9, 16, 10, 15]
                                        LoLGame_timeline_data_organized = {}
                                        for i in LoLGame_timeline_statistics_output_order:
                                            key = LoLGame_timeline_header_keys[i]
                                            LoLGame_timeline_data_organized[key] = LoLGame_timeline_data[key]
                                        LoLGame_timeline_df = pandas.DataFrame(data = LoLGame_timeline_data_organized)
                                        LoLGame_timeline_df = pandas.concat([pandas.DataFrame([LoLGame_timeline_header])[LoLGame_timeline_df.columns], LoLGame_timeline_df], ignore_index = True)
                                        
                                        LoLGame_event_header = {"assistingParticipantIds": "助攻者序号", "buildingType": "被摧毁的建筑物类型", "itemId": "获得的装备序号", "killerId": "击杀者序号", "laneType": "线路位置", "monsterSubType": "野区生物亚型", "monsterType": "野区生物类型", "participantId": "事件参与者序号", "position": "位置坐标", "skillSlot": "学习技能槽位", "teamId": "阵营代号", "timestamp": "时间戳", "towerType": "防御塔类型", "type": "事件类型", "victimId": "被杀者序号", "assistingChampion": "助攻者英雄", "assistingChampionAlias": "助攻者英雄代号", "assistingParticipantSummonerName": "助攻者召唤师名", "item": "获得的装备", "killerChampion": "击杀者英雄", "killerChampionAlias": "击杀者英雄代号", "killerParticipantSummonerName": "击杀者召唤师名", "participantChampion": "参与者英雄", "participantChampionAlias": "参与者英雄代号", "participantSummonerName": "参与者召唤师名", "team_color": "阵营", "time": "时间", "victimChampion": "被杀者英雄", "victimChampionAlias": "被杀者英雄代号", "victimParticipantSummonerName": "被杀者召唤师名"}
                                        LoLGame_event_header_keys = list(LoLGame_event_header.keys())
                                        LoLGame_event_data = {}
                                        events = {}
                                        for frame in frames:
                                            for event in frame["events"]:
                                                events[event["timestamp"]] = event
                                        #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                                        ##英雄联盟装备（LoL items）
                                        LoLItemIds_match_list = sorted(set(map(lambda x: x["itemId"], events.values())))
                                        for i in LoLItemIds_match_list:
                                            if not i in LoLItems and current_versions["LoLItem"] != bigVersion and i != 0: #空装备序号是0（The itemId of an empty item is 0）
                                                LoLItemPatch_adopted = bigVersion
                                                LoLItem_recapture = 1
                                                logPrint("第%d/%d场对局（对局序号：%d）英雄联盟装备信息（%d）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, LoLItem_recapture, LoLItemPatch_adopted, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemPatch_adopted, LoLItem_recapture))
                                                while True:
                                                    try:
                                                        LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        LoLItemPatch_deserted = LoLItemPatch_adopted
                                                        LoLItemPatch_adopted = FindPostPatch(LoLItemPatch_adopted, bigPatches)
                                                        LoLItem_recapture = 1
                                                        logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if LoLItem_recapture < 3:
                                                            LoLItem_recapture += 1
                                                            logPrint("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
                                                        else:
                                                            logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的英雄联盟装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the LoL item (%s) of Match %d / %d (matchID: %d)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, i, i, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                            break
                                                    else:
                                                        logPrint("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted))
                                                        LoLItems = {}
                                                        for LoLItem_iter in LoLItem:
                                                            LoLItem_id = LoLItem_iter["id"]
                                                            LoLItems[LoLItem_id] = LoLItem_iter
                                                        current_versions["LoLItem"] = LoLItemPatch_adopted
                                                        unmapped_keys["LoLItem"].clear()
                                                        break
                                                break
                                        for i in range(len(LoLGame_event_header)):
                                            key = LoLGame_event_header_keys[i]
                                            LoLGame_event_data[key] = [] #各项目初始化（Initialize every feature / column）
                                        for timestamp in sorted(events.keys()):
                                            event = events[timestamp]
                                            for i in range(len(LoLGame_event_header)):
                                                key = LoLGame_event_header_keys[i]
                                                if i <= 14:
                                                    if i == 1: #被摧毁的建筑物类型（`buildingTypes`）
                                                        LoLGame_event_data[key].append(buildingTypes[event[key]])
                                                    elif i == 4: #线路位置（`laneType`）
                                                        LoLGame_event_data[key].append(laneTypes[event[key]])
                                                    elif i == 5: #野区生物亚型（`monsterSubType`）
                                                        LoLGame_event_data[key].append(monsterSubTypes[event[key]])
                                                    elif i == 6: #野区生物类型（`monsterType`）
                                                        LoLGame_event_data[key].append(monsterTypes[event[key]])
                                                    elif i == 8: #位置坐标（`position`）
                                                        LoLGame_event_data[key].append("(%s, %s)" %(event[key]["x"], event[key]["y"]))
                                                    elif i == 12: #防御塔类型（`towerType`）
                                                        LoLGame_event_data[key].append(towerTypes[event[key]])
                                                    elif i == 13:
                                                        LoLGame_event_data[key].append(eventTypes[event[key]])
                                                    else:
                                                        LoLGame_event_data[key].append(event[key])
                                                else:
                                                    if i <= 17: #助攻者相关键（Assistant-related keys）
                                                        if i == 15: #助攻者英雄（`assistingChampion`）
                                                            LoLGame_event_data[key].append(list(map(lambda x: x if x == 0 else LoLChampions[LoLGame_info["participants"][x - 1]["championId"]]["name"], event["assistingParticipantIds"])))
                                                        elif i == 16: #助攻者英雄代号（`assistingChampionAlias`）
                                                            LoLGame_event_data[key].append(list(map(lambda x: "" if x == 0 else LoLChampions[LoLGame_info["participants"][x - 1]["championId"]]["alias"], event["assistingParticipantIds"])))
                                                        else: #助攻者召唤师名（`assistingParticipantSummonerName`）
                                                            LoLGame_event_data[key].append(list(map(lambda x: "" if x == 0 else LoLGame_info["participantIdentities"][x - 1]["player"]["gameName"] + "#" + LoLGame_info["participantIdentities"][x - 1]["player"]["tagLine"], event["assistingParticipantIds"])))
                                                    elif i == 18: #获得的装备（`item`）
                                                        itemId = event["itemId"]
                                                        if itemId == 0:
                                                            LoLGame_event_data[key].append("")
                                                        elif itemId in LoLItems:
                                                            LoLGame_event_data[key].append(LoLItems[itemId]["name"])
                                                        elif itemId in LoLItems_initial:
                                                            LoLGame_event_data[key].append(LoLItems_initial[itemId]["name"])
                                                        else:
                                                            if not itemId in unmapped_keys["LoLItem"]:
                                                                unmapped_keys["LoLItem"].add(itemId)
                                                                logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%d) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version, itemId, j, key, itemId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, version))
                                                            LoLGame_event_data[key].append(itemId)
                                                    elif i >= 19 and i <= 21: #击杀者相关键（Killer-related keys）
                                                        if event["killerId"] == 0:
                                                            LoLGame_event_data[key].append("")
                                                        else:
                                                            if i == 19: #击杀者英雄（`killerChampion`）
                                                                LoLGame_event_data[key].append(LoLChampions[LoLGame_info["participants"][event["killerId"] - 1]["championId"]]["name"])
                                                            elif i == 20: #击杀者英雄代号（`killerChampionAlias`）
                                                                LoLGame_event_data[key].append(LoLChampions[LoLGame_info["participants"][event["killerId"] - 1]["championId"]]["alias"])
                                                            else: #击杀者召唤师名（`killerParticipantSummonerName`）
                                                                LoLGame_event_data[key].append(LoLGame_info["participantIdentities"][event["killerId"] - 1]["player"]["gameName"] + "#" + LoLGame_info["participantIdentities"][event["killerId"] - 1]["player"]["tagLine"])
                                                    elif i >= 22 and i <= 24: #参与者相关键（Participant-related keys）
                                                        if event["participantId"] == 0:
                                                            LoLGame_event_data[key].append("")
                                                        else:
                                                            if i == 22: #参与者英雄（`participantChampion`）
                                                                LoLGame_event_data[key].append(LoLChampions[LoLGame_info["participants"][event["participantId"] - 1]["championId"]]["name"])
                                                            elif i == 23: #参与者英雄代号（`participantChampionAlias`）
                                                                LoLGame_event_data[key].append(LoLChampions[LoLGame_info["participants"][event["participantId"] - 1]["championId"]]["alias"])
                                                            else: #参与者召唤师名（`participantSummonerName`）
                                                                LoLGame_event_data[key].append(LoLGame_info["participantIdentities"][event["participantId"] - 1]["player"]["gameName"] + "#" + LoLGame_info["participantIdentities"][event["participantId"] - 1]["player"]["tagLine"])
                                                    elif i == 25: #阵营（`team_color`）
                                                        LoLGame_event_data[key].append(team_color[event["teamId"]])
                                                    elif i == 26: #时间（`time`）
                                                        LoLGame_event_data[key].append(lcuTimestamp(event["timestamp"] // 1000))
                                                    else: #被杀者相关键（Victim-related keys）
                                                        if event["victimId"] == 0:
                                                            LoLGame_event_data[key].append("")
                                                        else:
                                                            if i == 27: #被杀者英雄（`victimChampion`）
                                                                LoLGame_event_data[key].append(LoLChampions[LoLGame_info["participants"][event["victimId"] - 1]["championId"]]["name"])
                                                            elif i == 28: #被杀者英雄代号（`victimChampionAlias`）
                                                                LoLGame_event_data[key].append(LoLChampions[LoLGame_info["participants"][event["victimId"] - 1]["championId"]]["alias"])
                                                            else: #被杀者召唤师名（`victimParticipantSummonerName`）
                                                                LoLGame_event_data[key].append(LoLGame_info["participantIdentities"][event["victimId"] - 1]["player"]["gameName"] + "#" + LoLGame_info["participantIdentities"][event["victimId"] - 1]["player"]["tagLine"])
                                                
                                        LoLGame_event_statistics_output_order = [11, 26, 8, 13, 3, 19, 20, 21, 14, 27, 28, 29, 0, 15, 16, 17, 6, 5, 25, 4, 1, 12]
                                        LoLGame_event_data_organized = {}
                                        for i in LoLGame_event_statistics_output_order:
                                            key = LoLGame_event_header_keys[i]
                                            LoLGame_event_data_organized[key] = LoLGame_event_data[key]
                                        LoLGame_event_df = pandas.DataFrame(data = LoLGame_event_data_organized)
                                        LoLGame_event_df = pandas.concat([pandas.DataFrame([LoLGame_event_header])[LoLGame_event_df.columns], LoLGame_event_df], ignore_index = True)
                                    else: #当LoLGame_info未正常获取时，上述程序将导致无法LoLGame_timeline_df未定义。但是最后导出数据时，是根据确定的对局序号列表来生成工作表名称的，因此一定要向game_timeline_dfs中追加某个数据框，即使该数据框没有任何含义。否则不追加的话，时间轴数据框列表的长度与对局记录中的对局数量不相等，会导致时间轴内容和对局序号乱套（When LoLGame_info isn't captured as expected, the program above will cause LoLGame_timeline_df not to be defined. But note that during data export, sheet names are specified based on matchIDs. Therefore, some dataframe must be appended to game_timeline_dfs, even if it doesn't have any meaning. Otherwise, the length of game_timeline_dfs will unequal the length of matchIDs, which results in the discordance between the timeline content and the timeline sheet name）
                                        LoLGame_timeline_df = pandas.DataFrame()
                                        LoLGame_event_df = pandas.DataFrame()
                                        timeline_exist_error[matchID] = True

                                # if LoLGame_leaderboard_export:
                                #     game_leaderboard_dfs[matchID] = LoLGame_leaderboard_df.copy(deep = True)
                                if LoLGame_info_export:
                                    game_info_dfs[matchID] = LoLGame_info_df.copy(deep = True) #这里添加的LoLGame_info_df会在下一次循环中发生改变，这是数据框类型的特性。因此这里采用深复制，将原有内容克隆到另外一个地址，这样能保证每次添加的是不同的对局信息（The added LoLGame_info_df will be modified next time in the loop, which belongs to the characteristics of DataFrame data type. Therefore a deep copy is used here to clone the original contents to another address, so that each time the appended content is different）
                                if LoLGame_timeline_export:
                                    game_timeline_dfs[matchID] = LoLGame_timeline_df.copy(deep = True)
                                    game_event_dfs[matchID] = LoLGame_event_df.copy(deep = True)
                                
                            if len(matches_not_found) > 0:
                                logPrint("警告：以下%d场对局不存在。\nWarning: The following %d match(es) aren't found." %(len(matches_not_found), len(matches_not_found)))
                                logPrint(matches_not_found)
                            if len(error_LoLMatchIDs) > 0:
                                logPrint("警告：以下%d场对局获取失败。\nWarning: The following %d match(es) fail to be fetched." %(len(error_LoLMatchIDs), len(error_LoLMatchIDs)))
                                logPrint(error_LoLMatchIDs)
                            LoLGame_stat_statistics_output_order = [0, 13, 23, 5, 3, 11, 10, 6, 12, 9, 8, 39, 207, 32, 33, 217, 218, 220, 221, 42, 35, 36, 153, 154, 155, 156, 157, 158, 159, 189, 201, 190, 202, 191, 203, 192, 204, 193, 205, 194, 206, 69, 47, 40, 209, 210, 213, 214, 43, 138, 139, 71, 68, 72, 51, 50, 55, 54, 53, 52, 48, 142, 128, 81, 147, 132, 140, 134, 109, 75, 144, 133, 108, 74, 143, 70, 45, 44, 136, 141, 135, 110, 76, 145, 46, 148, 151, 150, 129, 149, 58, 211, 59, 212, 137, 77, 79, 78, 146, 60, 73, 185, 187, 173, 167, 174, 168, 175, 169, 176, 170, 177, 171, 178, 172, 41, 49, 131, 56, 57, 215, 130, 233, 227, 222, 280, 223, 267, 235, 232, 236, 228, 270, 259, 245, 275, 261, 268, 263, 247, 239, 272, 262, 246, 238, 271, 234, 225, 224, 265, 269, 264, 248, 240, 273, 226, 276, 279, 278, 260, 277, 229, 230, 266, 241, 243, 242, 281, 274, 231, 237, 283, 294, 288, 282, 341, 342, 344, 284, 328, 296, 293, 297, 289, 331, 320, 306, 336, 322, 329, 324, 308, 300, 333, 323, 307, 299, 332, 295, 286, 285, 326, 330, 325, 309, 301, 334, 287, 337, 340, 339, 321, 338, 290, 291, 345, 327, 302, 303, 304, 343, 335, 292, 298]
                            LoLGame_stat_data_organized = {}
                            for i in LoLGame_stat_statistics_output_order:
                                key = LoLGame_info_header_keys[i]
                                LoLGame_stat_data_organized[key] = LoLGame_stat_data[key]
                            LoLGame_stat_df = pandas.DataFrame(data = LoLGame_stat_data_organized)
                            for column in LoLGame_stat_df:
                                if LoLGame_stat_df[column].dtype == "bool":
                                    LoLGame_stat_df[column] = LoLGame_stat_df[column].astype(str)
                                    for i in range(len(LoLGame_stat_df)):
                                        LoLGame_stat_df.loc[i, column] = "√" if LoLGame_stat_df[column][i] == "True" else ""
                            LoLGame_stat_df = pandas.concat([pandas.DataFrame([LoLGame_info_header])[LoLGame_stat_df.columns], LoLGame_stat_df], ignore_index = True)
                            LoLGame_stat_df_export = True
                            
                            if LoLGamePlayed and export_json:
                                logPrint('对局信息和时间轴已保存在“%s”文件夹下。\nMatch information and timelines are saved in the folder "%s".\n' %(folder, folder))
                            matches_to_remove = matches_not_found + error_LoLMatchIDs
                            for match_to_remove in matches_to_remove: #在去除获取异常的对局后，需要在对局序号列表中将这些对局也一并移除（After removing matches that fail to be captured, we need to remove them in matchID list, too）
                                LoLMatchIDs.remove(match_to_remove)
                            break ####搜索完成召唤师最近的对局，需要退出大的while循环（Exit the outer while-loop after work of searching the recent matches is done）
                else:
                    LoLHistory_searched = False
                
                logPrint("是否查询云顶之弈对局记录？（输入任意键查询，否则不查询）\nSearch TFT matches? (Input anything to search or null to export data or switch for another summoner)")
                search_TFT_str = logInput()
                search_TFT = bool(search_TFT_str)
                if search_TFT:
                    #logPrint("召唤师云顶之弈对局记录如下：\nMatch history (TFT) is as follows:")
                    TFTHistory_get = True
                    begin_get, count_get = 0, 500
                    while True:
                        try:
                            TFTHistory = await (await connection.request("GET", "/lol-match-history/v1/products/tft/%s/matches?begin=%d&count=%d" %(info_body["puuid"], begin_get, count_get))).json()
                            #logPrint(TFTHistory)
                            count = 0 #存储内部服务器错误次数（Stores the times of internal server error）
                            if "errorCode" in TFTHistory:
                                if "500 Internal Server Error" in TFTHistory["message"]:
                                    if not error_occurred:
                                        logPrint("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                        occurred = True
                                    while "errorCode" in TFTHistory and "500 Internal Server Error" in TFTHistory["message"] and count <= 3:
                                        count += 1
                                        logPrint("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                                        TFTHistory = await (await connection.request("GET", "/lol-match-history/v1/products/tft/%s/matches?begin=%d&count=%d" %(info_body["puuid"], begin_get, count_get))).json()
                            json6name = "Match History (TFT) - " + displayName + ".json"
                            while True:
                                try:
                                    jsonfile6 = open(os.path.join(folder, json6name), "w", encoding = "utf-8")
                                except FileNotFoundError:
                                    os.makedirs(folder, exist_ok = True)
                                else:
                                    break
                            try:
                                jsonfile6.write(json.dumps(TFTHistory, indent = 4, ensure_ascii = False))
                            except UnicodeEncodeError:
                                logPrint("召唤师云顶之弈对局记录文本文档生成失败！请检查召唤师名称和所选语言是否包含不常用字符！\nSummoner TFT match history text generation failure! Please check if the summoner name and the chosen language include any abnormal characters!\n")
                            jsonfile6.close()
                            currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                            pkl6name = "Intermediate Object - TFTHistory - %s (%s).pkl" %(displayName, currentTime)
                            #with open(os.path.join(folder, pkl6name), "wb") as IntObj5:
                                #pickle.dump(TFTHistory, IntObj5)
                            if count > 3:
                                logPrint("云顶之弈对局记录获取失败！请等待官方修复对局记录服务！\nTFT match history capture failure! Please wait for Tencent to fix the match history service!")
                                break
                            logPrint('该玩家共进行%d场云顶之弈对局。近期云顶之弈对局（最近20场）已保存为“%s”。\nThis player has played %d TFT matches. Recent TFT matches (last 20 played) are saved as "%s".\n' %(len(TFTHistory["games"]), os.path.join(folder, json6name), len(TFTHistory["games"]), os.path.join(folder, json6name))) #在这里引发键异常（Here may trigger a KeyError）
                        except KeyError: #以下接口固定返回异常信息（The following endpoint always returns an error）：/lol-match-history/v1/products/tft/current-summoner/matches?begin=0&count=500
                            if "errorCode" in TFTHistory:
                                logPrint(TFTHistory)
                                TFTHistory_url = "%s/lol-match-history/v1/products/tft/%s/matches?begin=0&count=200" %(connection.address, info_body["puuid"])
                                logPrint("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续，或输入任意字符以切换召唤师（Please open the following website, type in the username and password accordingly and press Enter to continue or input anything to switch to another summoner）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和对局数。\nOr submit two nonnegative integers split by space to respecify the begin and count." %(TFTHistory_url, connection.auth_key))
                                cont = logInput()
                                if cont == "":
                                    continue
                                else:
                                    try:
                                        begin_get, count_get = map(int, cont.split())
                                    except ValueError:
                                        break
                                    else:
                                        continue
                        else:
                            TFTHistory_get = True
                            break
                    if not TFTHistory_get:
                        continue
                    logPrint("是否输出每场对局的文本文档？（输入任意键不输出，否则默认输出）\nExport text files of each match? (Input anything to cancel, or null to export by default)")
                    export_json_str = logInput()
                    export_json = not bool(export_json_str)
                    TFTHistory = TFTHistory["games"]
                    TFTHistory_gameIDs = list(map(lambda x: int(x["metadata"]["match_id"].split("_")[1]), TFTHistory))
                    saved_TFTMatchIDs = [int(name.split(".")[0].split("-")[-1]) for name in os.listdir(folder) if name.startswith("Match Information (TFT) - ")]
                    update_unsaved_only = False
                    if export_json and saved_TFTMatchIDs:
                        latest_TFTMatchID = max(saved_TFTMatchIDs)
                        latest_TFTMatchID_index = TFTHistory_gameIDs.index(latest_TFTMatchID) if latest_TFTMatchID in TFTHistory_gameIDs else 500
                        logPrint("检测到您以前曾经查询过该召唤师的云顶之弈对局记录。是否只保存该召唤师信息文件夹中不包含的云顶之弈对局？（输入空字符串以只保存尚未保存过文本文档的对局，否则将全部重新保存一遍）\nThe program detected that you've searched for this summoner's TFT match history before. Do you want to only fetch the TFT matches not present in the current summoner folder? (Enter an empty string to only save the matches whose json files haven't been saved, or any non-empty string to save all the TFT matches' information)\n已保存的最大对局序号的对局在最新对局列表中的下标（The index of the saved match with the greatest matchID in the latest match list recorded in API）：0 %d" %latest_TFTMatchID_index)
                        update_unsaved_only_str = logInput()
                        update_unsaved_only = not bool(update_unsaved_only_str)
                    TFTHistory_header = {"gameIndex": "游戏序号", "endOfGameResult": "对局终止情况", "gameCreation": "对局创建时间戳", "game_datetime": "对局结算时间戳", "game_id": "对局序号", "game_length": "持续时长（秒）", "game_version": "对局版本", "queue_id": "队列序号", "tft_game_type": "游戏类型", "tft_set_core_name": "数据版本名称", "tft_set_number": "赛季", "gameCreationDate": "对局创建时间", "gameDate": "对局结算时间", "gameLength": "持续时长", "participantId": "玩家序号", "augment1 apiName": "强化符文1接口名称", "augment2 apiName": "强化符文2接口名称", "augment3 apiName": "强化符文3接口名称", "augment1 name": "强化符文1名称", "augment2 name": "强化符文2名称", "augment3 name": "强化符文3名称", "augment1 icon": "强化符文1图标", "augment2 icon": "强化符文2图标", "augment3 icon": "强化符文3图标", "companion content_ID": "小小英雄商品编号", "companion item_ID": "小小英雄序号", "companion skin_ID": "小小英雄皮肤序号", "companion species": "小小英雄物种", "companion name": "小小英雄名称", "companion level": "小小英雄星级", "companion rarity": "小小英雄稀有度", "gold_left": "剩余金币", "last_round": "存活回合数", "level": "等级", "placement": "名次", "players_eliminated": "淘汰玩家数", "puuid": "玩家通用唯一识别码", "riotIdGameName": "玩家昵称", "riotIdTagLine": "昵称编号", "time_eliminated": "存活时长（秒）", "total_damage_to_players": "造成玩家伤害", "last_round_format": "存活回合", "time_eliminated_norm": "存活时长", "trait0 name": "羁绊1", "trait0 num_units": "羁绊1单位数", "trait0 style": "羁绊1羁绊框颜色", "trait0 tier_current": "羁绊1当前等级", "trait0 tier_total": "羁绊1最高等级", "trait0 display_name": "羁绊1显示名", "trait0 icon_path": "羁绊1图标路径", "trait1 name": "羁绊2", "trait1 num_units": "羁绊2单位数", "trait1 style": "羁绊2羁绊框颜色", "trait1 tier_current": "羁绊2当前等级", "trait1 tier_total": "羁绊2最高等级", "trait1 display_name": "羁绊2显示名", "trait1 icon_path": "羁绊2图标路径", "trait2 name": "羁绊3", "trait2 num_units": "羁绊3单位数", "trait2 style": "羁绊3羁绊框颜色", "trait2 tier_current": "羁绊3当前等级", "trait2 tier_total": "羁绊3最高等级", "trait2 display_name": "羁绊3显示名", "trait2 icon_path": "羁绊3图标路径", "trait3 name": "羁绊4", "trait3 num_units": "羁绊4单位数", "trait3 style": "羁绊4羁绊框颜色", "trait3 tier_current": "羁绊4当前等级", "trait3 tier_total": "羁绊4最高等级", "trait3 display_name": "羁绊4显示名", "trait3 icon_path": "羁绊4图标路径", "trait4 name": "羁绊5", "trait4 num_units": "羁绊5单位数", "trait4 style": "羁绊5羁绊框颜色", "trait4 tier_current": "羁绊5当前等级", "trait4 tier_total": "羁绊5最高等级", "trait4 display_name": "羁绊5显示名", "trait4 icon_path": "羁绊5图标路径", "trait5 name": "羁绊6", "trait5 num_units": "羁绊6单位数", "trait5 style": "羁绊6羁绊框颜色", "trait5 tier_current": "羁绊6当前等级", "trait5 tier_total": "羁绊6最高等级", "trait5 display_name": "羁绊6显示名", "trait5 icon_path": "羁绊6图标路径", "trait6 name": "羁绊7", "trait6 num_units": "羁绊7单位数", "trait6 style": "羁绊7羁绊框颜色", "trait6 tier_current": "羁绊7当前等级", "trait6 tier_total": "羁绊7最高等级", "trait6 display_name": "羁绊7显示名", "trait6 icon_path": "羁绊7图标路径", "trait7 name": "羁绊8", "trait7 num_units": "羁绊8单位数", "trait7 style": "羁绊8羁绊框颜色", "trait7 tier_current": "羁绊8当前等级", "trait7 tier_total": "羁绊8最高等级", "trait7 display_name": "羁绊8显示名", "trait7 icon_path": "羁绊8图标路径", "trait8 name": "羁绊9", "trait8 num_units": "羁绊9单位数", "trait8 style": "羁绊9羁绊框颜色", "trait8 tier_current": "羁绊9当前等级", "trait8 tier_total": "羁绊9最高等级", "trait8 display_name": "羁绊9显示名", "trait8 icon_path": "羁绊9图标路径", "trait9 name": "羁绊10", "trait9 num_units": "羁绊10单位数", "trait9 style": "羁绊10羁绊框颜色", "trait9 tier_current": "羁绊10当前等级", "trait9 tier_total": "羁绊10最高等级", "trait9 display_name": "羁绊10显示名", "trait9 icon_path": "羁绊10图标路径", "trait10 name": "羁绊11", "trait10 num_units": "羁绊11单位数", "trait10 style": "羁绊11羁绊框颜色", "trait10 tier_current": "羁绊11当前等级", "trait10 tier_total": "羁绊11最高等级", "trait10 display_name": "羁绊11显示名", "trait10 icon_path": "羁绊11图标路径", "trait11 name": "羁绊12", "trait11 num_units": "羁绊12单位数", "trait11 style": "羁绊12羁绊框颜色", "trait11 tier_current": "羁绊12当前等级", "trait11 tier_total": "羁绊12最高等级", "trait11 display_name": "羁绊12显示名", "trait11 icon_path": "羁绊12图标路径", "trait12 name": "羁绊13", "trait12 num_units": "羁绊13单位数", "trait12 style": "羁绊13羁绊框颜色", "trait12 tier_current": "羁绊13当前等级", "trait12 tier_total": "羁绊13最高等级", "trait12 display_name": "羁绊13显示名", "trait12 icon_path": "羁绊13图标路径", "unit0 character_id": "英雄1：角色编号", "unit0 rarity": "英雄1：卡费", "unit0 tier": "英雄1：星级", "unit0 display_name": "英雄1：显示名", "unit0 squareIconPath": "英雄1：方块图标路径", "unit1 character_id": "英雄2：角色编号", "unit1 rarity": "英雄2：卡费", "unit1 tier": "英雄2：星级", "unit1 display_name": "英雄2：显示名", "unit1 squareIconPath": "英雄2：方块图标路径", "unit2 character_id": "英雄3：角色编号", "unit2 rarity": "英雄3：卡费", "unit2 tier": "英雄3：星级", "unit2 display_name": "英雄3：显示名", "unit2 squareIconPath": "英雄3：方块图标路径", "unit3 character_id": "英雄4：角色编号", "unit3 rarity": "英雄4：卡费", "unit3 tier": "英雄4：星级", "unit3 display_name": "英雄4：显示名", "unit3 squareIconPath": "英雄4：方块图标路径", "unit4 character_id": "英雄5：角色编号", "unit4 rarity": "英雄5：卡费", "unit4 tier": "英雄5：星级", "unit4 display_name": "英雄5：显示名", "unit4 squareIconPath": "英雄5：方块图标路径", "unit5 character_id": "英雄6：角色编号", "unit5 rarity": "英雄6：卡费", "unit5 tier": "英雄6：星级", "unit5 display_name": "英雄6：显示名", "unit5 squareIconPath": "英雄6：方块图标路径", "unit6 character_id": "英雄7：角色编号", "unit6 rarity": "英雄7：卡费", "unit6 tier": "英雄7：星级", "unit6 display_name": "英雄7：显示名", "unit6 squareIconPath": "英雄7：方块图标路径", "unit7 character_id": "英雄8：角色编号", "unit7 rarity": "英雄8：卡费", "unit7 tier": "英雄8：星级", "unit7 display_name": "英雄8：显示名", "unit7 squareIconPath": "英雄8：方块图标路径", "unit8 character_id": "英雄9：角色编号", "unit8 rarity": "英雄9：卡费", "unit8 tier": "英雄9：星级", "unit8 display_name": "英雄9：显示名", "unit8 squareIconPath": "英雄9：方块图标路径", "unit9 character_id": "英雄10：角色编号", "unit9 rarity": "英雄10：卡费", "unit9 tier": "英雄10：星级", "unit9 display_name": "英雄10：显示名", "unit9 squareIconPath": "英雄10：方块图标路径", "unit10 character_id": "英雄11：角色编号", "unit10 rarity": "英雄11：卡费", "unit10 tier": "英雄11：星级", "unit10 display_name": "英雄11：显示名", "unit10 squareIconPath": "英雄11：方块图标路径", "unit0 item0 nameId": "英雄1：装备1序号", "unit0 item0 name": "英雄1：装备1名称", "unit0 item0 squareIconPath": "英雄1：装备1方块图像路径", "unit0 item1 nameId": "英雄1：装备2序号", "unit0 item1 name": "英雄1：装备2名称", "unit0 item1 squareIconPath": "英雄1：装备2方块图像路径", "unit0 item2 nameId": "英雄1：装备3序号", "unit0 item2 name": "英雄1：装备3名称", "unit0 item2 squareIconPath": "英雄1：装备3方块图像路径", "unit1 item0 nameId": "英雄2：装备1序号", "unit1 item0 name": "英雄2：装备1名称", "unit1 item0 squareIconPath": "英雄2：装备1方块图像路径", "unit1 item1 nameId": "英雄2：装备2序号", "unit1 item1 name": "英雄2：装备2名称", "unit1 item1 squareIconPath": "英雄2：装备2方块图像路径", "unit1 item2 nameId": "英雄2：装备3序号", "unit1 item2 name": "英雄2：装备3名称", "unit1 item2 squareIconPath": "英雄2：装备3方块图像路径", "unit2 item0 nameId": "英雄3：装备1序号", "unit2 item0 name": "英雄3：装备1名称", "unit2 item0 squareIconPath": "英雄3：装备1方块图像路径", "unit2 item1 nameId": "英雄3：装备2序号", "unit2 item1 name": "英雄3：装备2名称", "unit2 item1 squareIconPath": "英雄3：装备2方块图像路径", "unit2 item2 nameId": "英雄3：装备3序号", "unit2 item2 name": "英雄3：装备3名称", "unit2 item2 squareIconPath": "英雄3：装备3方块图像路径", "unit3 item0 nameId": "英雄4：装备1序号", "unit3 item0 name": "英雄4：装备1名称", "unit3 item0 squareIconPath": "英雄4：装备1方块图像路径", "unit3 item1 nameId": "英雄4：装备2序号", "unit3 item1 name": "英雄4：装备2名称", "unit3 item1 squareIconPath": "英雄4：装备2方块图像路径", "unit3 item2 nameId": "英雄4：装备3序号", "unit3 item2 name": "英雄4：装备3名称", "unit3 item2 squareIconPath": "英雄4：装备3方块图像路径", "unit4 item0 nameId": "英雄5：装备1序号", "unit4 item0 name": "英雄5：装备1名称", "unit4 item0 squareIconPath": "英雄5：装备1方块图像路径", "unit4 item1 nameId": "英雄5：装备2序号", "unit4 item1 name": "英雄5：装备2名称", "unit4 item1 squareIconPath": "英雄5：装备2方块图像路径", "unit4 item2 nameId": "英雄5：装备3序号", "unit4 item2 name": "英雄5：装备3名称", "unit4 item2 squareIconPath": "英雄5：装备3方块图像路径", "unit5 item0 nameId": "英雄6：装备1序号", "unit5 item0 name": "英雄6：装备1名称", "unit5 item0 squareIconPath": "英雄6：装备1方块图像路径", "unit5 item1 nameId": "英雄6：装备2序号", "unit5 item1 name": "英雄6：装备2名称", "unit5 item1 squareIconPath": "英雄6：装备2方块图像路径", "unit5 item2 nameId": "英雄6：装备3序号", "unit5 item2 name": "英雄6：装备3名称", "unit5 item2 squareIconPath": "英雄6：装备3方块图像路径", "unit6 item0 nameId": "英雄7：装备1序号", "unit6 item0 name": "英雄7：装备1名称", "unit6 item0 squareIconPath": "英雄7：装备1方块图像路径", "unit6 item1 nameId": "英雄7：装备2序号", "unit6 item1 name": "英雄7：装备2名称", "unit6 item1 squareIconPath": "英雄7：装备2方块图像路径", "unit6 item2 nameId": "英雄7：装备3序号", "unit6 item2 name": "英雄7：装备3名称", "unit6 item2 squareIconPath": "英雄7：装备3方块图像路径", "unit7 item0 nameId": "英雄8：装备1序号", "unit7 item0 name": "英雄8：装备1名称", "unit7 item0 squareIconPath": "英雄8：装备1方块图像路径", "unit7 item1 nameId": "英雄8：装备2序号", "unit7 item1 name": "英雄8：装备2名称", "unit7 item1 squareIconPath": "英雄8：装备2方块图像路径", "unit7 item2 nameId": "英雄8：装备3序号", "unit7 item2 name": "英雄8：装备3名称", "unit7 item2 squareIconPath": "英雄8：装备3方块图像路径", "unit8 item0 nameId": "英雄9：装备1序号", "unit8 item0 name": "英雄9：装备1名称", "unit8 item0 squareIconPath": "英雄9：装备1方块图像路径", "unit8 item1 nameId": "英雄9：装备2序号", "unit8 item1 name": "英雄9：装备2名称", "unit8 item1 squareIconPath": "英雄9：装备2方块图像路径", "unit8 item2 nameId": "英雄9：装备3序号", "unit8 item2 name": "英雄9：装备3名称", "unit8 item2 squareIconPath": "英雄9：装备3方块图像路径", "unit9 item0 nameId": "英雄10：装备1序号", "unit9 item0 name": "英雄10：装备1名称", "unit9 item0 squareIconPath": "英雄10：装备1方块图像路径", "unit9 item1 nameId": "英雄10：装备2序号", "unit9 item1 name": "英雄10：装备2名称", "unit9 item1 squareIconPath": "英雄10：装备2方块图像路径", "unit9 item2 nameId": "英雄10：装备3序号", "unit9 item2 name": "英雄10：装备3名称", "unit9 item2 squareIconPath": "英雄10：装备3方块图像路径", "unit10 item0 nameId": "英雄11：装备1序号", "unit10 item0 name": "英雄11：装备1名称", "unit10 item0 squareIconPath": "英雄11：装备1方块图像路径", "unit10 item1 nameId": "英雄11：装备2序号", "unit10 item1 name": "英雄11：装备2名称", "unit10 item1 squareIconPath": "英雄11：装备2方块图像路径", "unit10 item2 nameId": "英雄11：装备3序号", "unit10 item2 name": "英雄11：装备3名称", "unit10 item2 squareIconPath": "英雄11：装备3方块图像路径"}
                    TFTHistory_header_keys = list(TFTHistory_header.keys())
                    TFTHistory_data = {}
                    TFTGamePlayed = len(TFTHistory) != 0 #标记该玩家是否进行过云顶之弈对局（Mark whether this summoner has played any TFT game）
                    TFT_main_player_indices = [] #云顶之弈对局记录中记录了所有玩家的数据，但是在历史记录的工作表中只要显示主召唤师的数据，因此必须知道每场对局中主召唤师的索引（Each match in TFT history records all players' data, but only the main player's data are needed to display in the match history worksheet, so the index of the main player in each match is necessary）
                    version_re = re.compile(r"\d*\.\d*\.\d*\.\d*") #云顶之弈的对局版本信息是一串字符串，从中识别四位对局版本（TFT match version is a long string, from which the 4-number version is identified）
                    for game in TFTHistory:
                        TFT_main_player_found = False
                        try:
                            for i in range(len(game["json"]["participants"])):
                                if game["json"]["participants"][i]["puuid"] == current_puuid:
                                    TFT_main_player_found = True
                                    TFT_main_player_indices.append(i)
                                    break
                            if not TFT_main_player_found: #在美测服的对局序号为4420772721的对局中，不存在Volibear  PBE6玩家。这是极少见的情况，如果没有此处的判断，一旦发生这种情况，就会引起下标越界的错误（Player "Volibear  PBE6" is absent from a PBE match with matchId 4420772721, which is quite rare. Nevertheless, once it happens, an IndexError that list index out of range will be definitely thrown）
                                TFT_main_player_indices.append(-1)
                        except TypeError: #在艾欧尼亚的对局序号为8346130449的对局中，不存在玩家。这可能是因为系统维护的原因，所有人未正常进入对局，但是对局确实创建了（There doesn't exist any player in an HN1 match with matchID 8346130499. This may be due to system mainteinance, which causes all players to fail to start the game, even if the match itself has been created）
                            TFT_main_player_indices.append(-1) #当主玩家索引为-1时，表示本场对局存在异常（Main player index being -1 represents an abnormal match）
                    for i in range(len(TFTHistory_header)): #云顶之弈对局信息各项目初始化（Initialize every feature / column of TFT match information）
                        key = TFTHistory_header_keys[i]
                        TFTHistory_data[key] = []
                    for i in range(len(TFTHistory)): #由于不同对局意味着不同版本，不同版本的云顶之弈数据相差较大，所以为了使得一次获取的版本能够尽可能用到多个对局中，第一层迭代器应当是对局序号（Because different matches mean different patches, and TFT data differ greatly among different patches, to make a recently captured version of TFT data applicable in as more matches as possible, the first iterator should be the ID of the matches）
                        #云顶之弈的每场对局没有独立的API以存储对局战绩，只能通过某玩家的对局记录来存储。这里先生成对局文档，再同时生成和对局记录有关的变量（No available LCU API for each TFT match. It can only be fetched from some player's match history. Here the program generates match text files first and then dataframes regarding match history and game information）
                        save = True
                        TFTGame_info = TFTHistory[i]
                        matchID = int(TFTGame_info["metadata"]["match_id"].split("_")[1]) #由于后面将对局序号作为键实现混合排序，所以这里需要将字符串分割后提取到的对局序号转化为整数类型（Because the matchIDs are used as keys to perform a mixed sort, the matchID extracted here needs transforming into integer type）
                        currentPlatformId = TFTGame_info["metadata"]["match_id"].split("_")[0]
                        if export_json and TFTGame_info["json"] and not (update_unsaved_only and matchID in saved_TFTMatchIDs): #一些旧版本的云顶之弈对局数据在API中被删除了。这样的对局信息不应覆盖写到本地保存完好的json文件（Some old TFT matches are deleted from API. These matches shouldn't overwrite the complete local json files）
                            save = True
                            json9name = f"Match Information (TFT) - {currentPlatformId}-{matchID}.json"
                            while True:
                                try:
                                    jsonfile9 = open(os.path.join(folder, json9name), "w", encoding = "utf-8")
                                except FileNotFoundError:
                                    os.makedirs(folder, exist_ok = True)
                                else:
                                    break
                            try:
                                jsonfile9.write(json.dumps(TFTHistory[i], indent = 4, ensure_ascii = False))
                            except UnicodeDecodeError:
                                logPrint("对局%d信息文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nMatch %d information text generation failure! Please check if the summoner name includes any abnormal characters!" %(matchID, matchID))
                                save = False
                            jsonfile9.close()
                            pkl9name = f"Intermediate Object - Match Information (TFT) - {currentPlatformId}-{matchID}.pkl"
                            #with open(os.path.join(folder, pkl9name), "wb") as IntObj8:
                                #pickle.dump(TFTGame_info, IntObj8)
                        if save:
                            if export_json:
                                logPrint('保存进度（Saving process）：%d/%d\t对局序号（MatchID）： %d' %(i + 1, len(TFTHistory), matchID), end = "", print_time = True)
                                if update_unsaved_only and matchID in saved_TFTMatchIDs:
                                    logPrint(" (Json file already exists!)")
                                else:
                                    logPrint("")
                            else:
                                logPrint('加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %d' %(i + 1, len(TFTHistory), matchID), print_time = True)
                        
                        TFTHistoryJson = TFTHistory[i]["json"]
                        info_exist_error[matchID] = False #一旦正常获取到云顶之弈的对局记录，对局信息即视为正常获取（Once the TFT match history is captured successfully, the TFT games' information is then regarded to be captured successfully as well）
                        timeline_exist_error[matchID] = True #云顶之弈对局中没有时间轴信息，因此每个云顶之弈对局的时间轴标记为异常获取（There's no timeline information in each TFT match, so each TFT match's timeline is labeled as "error" captured）
                        main_player_included[matchID] = True #从云顶之弈对局记录中抽取对局信息，则这些对局一定包含当前玩家（Since TFT game information is extracted from TFT match history, these matches must include the current player）
                        match_reserve_strategy[matchID] = True if TFTGame_info["json"] else False
                        TFTGame_info_data = {} #云顶之弈没有独立的API以供查询对局信息。这里将每场对局的与玩家有关的数据视为对局信息（No API is available for TFT match information query. Here any information relevant to participants is regarded as TFT game information）
                        for j in range(9, len(TFTHistory_header)): #各项目初始化（Initialize every feature / column）
                            key = TFTHistory_header_keys[j]
                            TFTGame_info_data[key] = []
                        if TFTHistoryJson != None: #该条件等价于（This condition is equivalent to）：`TFT_main_player_indices[i] == -1`
                            TFTGameVersion = version_re.search(TFTHistoryJson["game_version"]).group()
                            TFTGamePatch = ".".join(TFTGameVersion.split(".")[:2]) #由于需要通过这部分代码事先获取所有对局的版本，因此无论如何，这部分代码都要放在与从CommunityDragon重新获取云顶之弈数据相关的代码前面（Since game patches are captured here, by all means should this part of code be in front of the code relevant to regetting TFT data from CommunityDragon）
                            #下面针对每场对局建立总的数据资源异常处理机制（Builds the summarized data resource exceptional handling mechanism for each match）
                            ##云顶之弈强化符文（TFT augments）
                            TFTAugmentIds_match_list = sorted(set(augment for lst in list(map(lambda x: x["augments"] if "augments" in x else [], TFTHistoryJson["participants"])) for augment in lst)) #`if "augments" in x`的作用是防止早期云顶之弈对局无强化符文导致程序报错（`if "augments" in x` is used here because some early TFT matches don't contain augments and result in KeyErrors consequently）
                            for j in TFTAugmentIds_match_list:
                                if not j in TFTAugments and current_versions["TFTAugment"] != TFTGamePatch:
                                    TFTAugmentPatch_adopted = TFTGamePatch
                                    TFTAugment_recapture = 1
                                    logPrint("第%d/%d场对局（对局序号：%d）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nAugment information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT augments of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, TFTAugment_recapture, TFTAugmentPatch_adopted, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTAugmentPatch_adopted, TFTAugment_recapture))
                                    while True:
                                        try:
                                            TFT = requests.get("https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[language_code])).json()
                                        except requests.exceptions.JSONDecodeError: #存在版本合并更新的情况（Situation like merged update exists）
                                            TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                            TFTAugmentPatch_adopted = FindPostPatch(TFTAugmentPatch_adopted, bigPatches)
                                            TFTAugment_recapture = 1
                                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture))
                                        except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                            if TFTAugment_recapture < 3:
                                                TFTAugment_recapture += 1
                                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture))
                                            else:
                                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                                break
                                        else:
                                            logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted))
                                            TFTAugments = {}
                                            for item in TFT["items"]:
                                                item_apiName = item["apiName"]
                                                TFTAugments[item_apiName] = item
                                            current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                            unmapped_keys["TFTAugment"].clear()
                                            break
                                    break
                            ##云顶之弈小小英雄（TFT companions）
                            TFTCompanionIds_match_list = sorted(set(map(lambda x: x["companion"]["content_ID"], TFTHistoryJson["participants"])))
                            for j in TFTCompanionIds_match_list:
                                if not j in TFTCompanions and current_versions["TFTCompanion"] != TFTGamePatch:
                                    TFTCompanionPatch_adopted = TFTGamePatch
                                    TFTCompanion_recapture = 1
                                    logPrint("第%d/%d场对局（对局序号：%d）小小英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的小小英雄信息……\nTFT companion information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT companions of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, TFTCompanion_recapture, TFTCompanionPatch_adopted, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                    while True:
                                        try:
                                            TFTCompanion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(TFTCompanionPatch_adopted, language_cdragon[language_code])).json()
                                        except requests.exceptions.JSONDecodeError:
                                            TFTCompanionPatch_deserted = TFTCompanionPatch_adopted
                                            TFTCompanionPatch_adopted = FindPostPatch(TFTCompanionPatch_adopted, bigPatches)
                                            TFTCompanion_recapture = 1
                                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTCompanionPatch_deserted, TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_deserted, TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                        except requests.exceptions.RequestException:
                                            if TFTCompanion_recapture < 3:
                                                TFTCompanion_recapture += 1
                                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的小小英雄信息……\nYour network environment is abnormal! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                            else:
                                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的小小英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the companion (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                                break
                                        else:
                                            logPrint("已改用%s版本的小小英雄信息。\nTFT companion information changed to Patch %s." %(TFTCompanionPatch_adopted, TFTCompanionPatch_adopted))
                                            TFTCompanions = {}
                                            for companion_iter in TFTCompanion:
                                                contentId = companion_iter["contentId"]
                                                TFTCompanions[contentId] = companion_iter
                                            current_versions["TFTCompanion"] = TFTCompanionPatch_adopted
                                            unmapped_keys["TFTCompanion"].clear()
                                            break
                                    break
                            ##云顶之弈羁绊（TFT Traits）
                            TFTTraitIds_match_list = sorted(set(trait for s in [set(map(lambda x: x["name"], participant["traits"])) for participant in TFTHistoryJson["participants"]] for trait in s))
                            for j in TFTTraitIds_match_list:
                                if not j in TFTTraits and current_versions["TFTTrait"] != TFTGamePatch:
                                    TFTTraitPatch_adopted = TFTGamePatch
                                    TFTTrait_recapture = 1
                                    logPrint("第%d/%d场对局（对局序号：%d）羁绊信息（%s）获取失败！正在第%d次尝试改用%s版本的羁绊信息……\nTFT trait information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT traits of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, TFTTrait_recapture, TFTTraitPatch_adopted, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTTraitPatch_adopted, TFTTrait_recapture))
                                    while True:
                                        try:
                                            TFTTrait = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(TFTTraitPatch_adopted, language_cdragon[language_code])).json()
                                        except requests.exceptions.JSONDecodeError:
                                            TFTTraitPatch_deserted = TFTTraitPatch_adopted
                                            TFTTraitPatch_adopted = FindPostPatch(TFTTraitPatch_adopted, bigPatches)
                                            TFTTrait_recapture = 1
                                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTraitPatch_deserted, TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_deserted, TFTTraitPatch_adopted, TFTTrait_recapture))
                                        except requests.exceptions.RequestException:
                                            if TFTTrait_recapture < 3:
                                                TFTTrait_recapture += 1
                                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的羁绊信息……\nYour network environment is abnormal! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_adopted, TFTTrait_recapture))
                                            else:
                                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的羁绊信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the trait (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                                break
                                        else:
                                            logPrint("已改用%s版本的羁绊信息。\nTFT trait information changed to Patch %s." %(TFTTraitPatch_adopted, TFTTraitPatch_adopted))
                                            TFTTraits = {}
                                            for trait_iter in TFTTrait:
                                                trait_id = trait_iter["trait_id"]
                                                conditional_trait_sets = {}
                                                if "conditional_trait_sets" in trait_iter: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
                                                    for conditional_trait_set in trait_iter["conditional_trait_sets"]:
                                                        style_idx = conditional_trait_set["style_idx"]
                                                        conditional_trait_sets[style_idx] = conditional_trait_set
                                                trait_iter["conditional_trait_sets"] = conditional_trait_sets
                                                TFTTraits[trait_id] = trait_iter
                                            current_versions["TFTTrait"] = TFTTraitPatch_adopted
                                            unmapped_keys["TFTTrait"].clear()
                                            break
                                    break
                            ##云顶之弈英雄（TFT champions）
                            TFTChampionIds_match_list = sorted(set(champion for s in [set(map(lambda x: x["character_id"], participant["units"])) for participant in TFTHistoryJson["participants"]] for champion in s))
                            for j in TFTChampionIds_match_list:
                                if not j in TFTChampions and not j.lower() in map(lambda x: x.lower(), TFTChampions.keys()) and current_versions["TFTChampion"] != TFTGamePatch:
                                    TFTChampionPatch_adopted = TFTGamePatch
                                    TFTChampion_recapture = 1
                                    logPrint("第%d/%d场对局（对局序号：%d）英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的棋子信息……\nTFT champion (%s) information of Match %d / %d (matchID: %d) capture failed! Changing to TFT champions of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, TFTChampion_recapture, TFTChampionPatch_adopted, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTChampionPatch_adopted, TFTChampion_recapture))
                                    while True:
                                        try:
                                            TFTChampion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(TFTChampionPatch_adopted, language_cdragon[language_code])).json()
                                        except requests.exceptions.JSONDecodeError:
                                            TFTChampionPatch_deserted = TFTChampionPatch_adopted
                                            TFTChampionPatch_adopted = FindPostPatch(TFTChampionPatch_adopted, bigPatches)
                                            TFTChampion_recapture = 1
                                            logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampionPatch_deserted, TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_deserted, TFTChampionPatch_adopted, TFTChampion_recapture))
                                        except requests.exceptions.RequestException:
                                            if TFTChampion_recapture < 3:
                                                TFTChampion_recapture += 1
                                                logPrint("网络环境异常！正在第%d次尝试改用%s版本的棋子信息……\nYour network environment is abnormal! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_adopted, TFTChampion_recapture))
                                            else:
                                                logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）将采用原始数据！\nNetwork error! The original data will be used for Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                                break
                                        else:
                                            logPrint("已改用%s版本的棋子信息。\nTFT champion information changed to Patch %s." %(TFTChampionPatch_adopted, TFTChampionPatch_adopted))
                                            TFTChampions = {}
                                            if patch_compare(TFTChampionPatch_adopted, "13.17"): #从13.17版本开始，CommunityDragon数据库中关于云顶之弈棋子的数据格式发生微调（Since Patch 13.17, the format of TFT Champion data in CommunityDragon database has been modified）
                                                for TFTChampion_iter in TFTChampion:
                                                    champion_name = TFTChampion_iter["character_id"]
                                                    TFTChampions[champion_name] = TFTChampion_iter
                                            else:
                                                for TFTChampion_iter in TFTChampion:
                                                    champion_name = TFTChampion_iter["name"]
                                                    TFTChampions[champion_name] = TFTChampion_iter["character_record"] #请注意该语句与4行之前的语句的差异，并看看一开始准备数据文件时使用的是哪一种——其实你应该猜的出来（Have you noticed the difference between this statement and the statement that is 4 lines above from this statement? Also, check which statement I chose for the beginning, when I prepared the data resources. Actually, you should be able to speculate it without referring to the code）
                                            current_versions["TFTChampion"] = TFTChampionPatch_adopted
                                            unmapped_keys["TFTChampion"].clear()
                                            break
                                    break
                            ##云顶之弈装备（TFT items）
                            s = set()
                            for participant in TFTHistoryJson["participants"]:
                                for unit in participant["units"]:
                                    if "itemNames" in unit:
                                        s |= set(unit["itemNames"])
                                    elif "items" in unit:
                                        s |= set(unit["items"])
                                    else:
                                        s |= set()
                            TFTItemIds_match_list = sorted(s)
                            for j in TFTItemIds_match_list:
                                if not j in TFTItems and not j in TFTAugments:
                                    if current_versions["TFTItem"] != TFTGamePatch:
                                        TFTItemPatch_adopted = TFTGamePatch
                                        TFTItem_recapture = 1
                                        logPrint("第%d/%d场对局（对局序号：%d）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT items of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, TFTItem_recapture, TFTItemPatch_adopted, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTItemPatch_adopted, TFTItem_recapture))
                                        while True:
                                            try:
                                                TFTItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[language_code])).json()
                                            except requests.exceptions.JSONDecodeError:
                                                TFTItemPatch_deserted = TFTItemPatch_adopted
                                                TFTItemPatch_adopted = FindPostPatch(TFTItemPatch_adopted, bigPatches)
                                                TFTItemPatch_recapture = 1
                                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture))
                                            except requests.exceptions.RequestException:
                                                if TFTItem_recapture < 3:
                                                    TFTItem_recapture += 1
                                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture))
                                                else:
                                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的装备信息（%d）将采用原始数据！\nNetwork error! The original data will be used for the item (%d) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                                    break
                                            else:
                                                logPrint("已改用%s版本的云顶之弈装备信息。\nTFT item information changed to Patch %s." %(TFTItemPatch_adopted, TFTItemPatch_adopted))
                                                TFTItems = {}
                                                for TFTItem_iter in TFTItem:
                                                    item_id = TFTItem_iter["id"]
                                                    TFTItems[item_id] = TFTItem_iter
                                                current_versions["TFTItem"] = TFTItemPatch_adopted
                                                unmapped_keys["TFTItem"].clear()
                                                break
                                    #由于云顶之弈基础数据中也包含装备信息，这里将重新获取对局版本的云顶之弈基础数据（Because TFT basic data contain item data, here the program recaptures TFT basic data of the match version）
                                    if current_versions["TFTAugment"] != TFTGamePatch:
                                        TFTAugmentPatch_adopted = TFTGamePatch
                                        TFTAugment_recapture = 1
                                        while True:
                                            try:
                                                TFT = requests.get("https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[language_code])).json()
                                            except requests.exceptions.JSONDecodeError:
                                                TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                                TFTAugmentPatch_adopted = FindPostPatch(TFTAugmentPatch_adopted, bigPatches)
                                                TFTAugment_recapture = 1
                                                logPrint("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture))
                                            except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                                if TFTAugment_recapture < 3:
                                                    TFTAugment_recapture += 1
                                                    logPrint("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture))
                                                else:
                                                    logPrint("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], j, j, i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                                    break
                                            else:
                                                logPrint("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted))
                                                TFTAugments = {}
                                                for item in TFT["items"]:
                                                    item_apiName = item["apiName"]
                                                    TFTAugments[item_apiName] = item
                                                current_versions["TFTAugment"] = TFTAugmentPatch_adopted
                                                unmapped_keys["TFTAugment"].clear()
                                                break
                                    break
                        #下面开始整理数据（Sorts out the data）
                        if TFT_main_player_indices[i] == -1: #对局数据记录存在异常时的处理（Exception of match data recording exception）
                            for j in range(len(TFTHistory_header)):
                                key = TFTHistory_header_keys[j]
                                if j == 0: #游戏序号（`gameIndex`）
                                    TFTHistory_data[key].append(i + 1)
                                elif j == 4: #对局序号（`game_id`）
                                    TFTHistory_data[key].append(TFTHistory[i]["metadata"]["match_id"].split("_")[1])
                                elif j == 11: #对局创建时间（`gameCreationDate`）
                                    game_datetime = TFTHistory[i]["metadata"]["timestamp"]
                                    game_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(game_datetime // 1000))
                                    game_date_fraction = game_datetime / 1000 - game_datetime // 1000
                                    to_append = game_date + ("{0:.3}".format(game_date_fraction))[1:5]
                                    TFTHistory_data[key].append(to_append)
                                else:
                                    TFTHistory_data[key].append("")
                                    if j >= 14:
                                        TFTGame_info_data[key].append("")
                        else:
                            # challenger_ladder_queueTypes = await (await connection.request("GET", "/lol-ranked/v1/challenger-ladders-enabled")).json()
                            # topRated_ladder_queueTypes = await (await connection.request("GET", "/lol-ranked/v1/top-rated-ladders-enabled")).json()
                            # ranked_queueTypes = challenger_ladder_queueTypes + topRated_ladder_queueTypes
                            # TFTGame_leaderboard_header = {"puuid": "玩家通用唯一识别码", "displayName": "显示名", "gameName": "玩家昵称", "tagLine": "昵称编号", "division": "分级", "isProvisional": "定位中", "leaguePoints": "胜点", "losses": "负场", "miniSeriesProgress": "定位赛/晋级赛进展", "provisionalGameThreshold": "总定位场次", "provisionalGamesRemaining": "剩余定位场次", "queueType": "战区", "ratedRating": "排名分", "ratedTier": "段位", "tier": "段位", "wins": "胜场", "tier / ratedTier": "段位", "leaguePoints / ratedRating": "胜点", "timestamp": "获取时间戳", "time": "获取时间"}
                            # TFTGame_leaderboard_header_keys = list(TFTGame_leaderboard_header.keys())
                            # TFTGame_leaderboard_data = {}
                            # for j in range(len(TFTGame_leaderboard_header_keys)):
                            #     key = TFTGame_leaderboard_header_keys[j]
                            #     TFTGame_leaderboard_data[key] = []
                            # for queueType in ranked_queueTypes:
                            #     TFTGame_leaderboard = await (await connection.request("GET", "/lol-ranked/v1/social-leaderboard-ranked-queue-stats-for-puuids?queueType=%s&puuids=%s" %(queueType, str(TFTHistory[i]["metadata"]["participants"]).replace(" ", "").replace("'", '"')))).json()
                            #     for participant_puuid_iter in TFTGame_leaderboard:
                            #         participant_leaderboard = TFTGame_leaderboard[participant_puuid_iter]
                            #         participantInfo = await get_info(connection, participant_puuid_iter)
                            #         if participantInfo["info_got"]:
                            #             participantInfo_body = participantInfo["body"]
                            #             for j in range(len(TFTGame_leaderboard_header_keys)):
                            #                 key = TFTGame_leaderboard_header_keys[j]
                            #                 if j <= 3:
                            #                     TFTGame_leaderboard_data[key].append(participantInfo_body[key])
                            #                 elif j <= 15:
                            #                     if j == 4: #分级（`division`）
                            #                         TFTGame_leaderboard_data[key].append("" if participant_leaderboard["division"] == "NA" else participant_leaderboard["division"])
                            #                     elif j == 11: #战区（`queueType`）
                            #                         TFTGame_leaderboard_data[key].append(queueTypes[participant_leaderboard["queueType"]])
                            #                     elif j == 13: #段位（`ratedTier`）
                            #                         TFTGame_leaderboard_data[key].append(ratedTiers[participant_leaderboard["ratedTier"]])
                            #                     elif j == 14: #段位（`tier`）
                            #                         TFTGame_leaderboard_data[key].append(tiers[participant_leaderboard["tier"]])
                            #                     else:
                            #                         TFTGame_leaderboard_data[key].append(participant_leaderboard[key])
                            #                 elif j == 16: #段位（`tier / ratedTier`）
                            #                     TFTGame_leaderboard_data[key].append(ratedTiers[participant_leaderboard["ratedTier"]] if queueType in topRated_ladder_queueTypes else tiers[participant_leaderboard["tier"]])
                            #                 elif j == 17: #胜点（`leaguePoints / ratedRating`）
                            #                     TFTGame_leaderboard_data[key].append(participant_leaderboard["ratedRating"] if queueType in topRated_ladder_queueTypes else participant_leaderboard["leaguePoints"])
                            #                 elif j == 18: #获取时间戳（`timestamp`）
                            #                     TFTGame_leaderboard_data[key].append(time.time())
                            #                 else: #获取时间（`time`）
                            #                     TFTGame_leaderboard_data[key].append(time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime()))
                            #         else:
                            #             logPrint(participantInfo["message"])
                            # TFTGame_leaderboard_statistics_output_order = [11, 1, 2, 3, 0, 16, 4, 17, 15, 7, 5, 9, 10, 8, 19]
                            # TFTGame_leaderboard_data_organized = {}
                            # for i in TFTGame_leaderboard_statistics_output_order:
                            #     key = TFTGame_leaderboard_header_keys[i]
                            #     TFTGame_leaderboard_data_organized[key] = TFTGame_leaderboard_data[key]
                            # TFTGame_leaderboard_df = pandas.DataFrame(data = TFTGame_leaderboard_data_organized)
                            # for column in TFTGame_leaderboard_df:
                            #     if TFTGame_leaderboard_df[column].dtype == "bool":
                            #         TFTGame_leaderboard_df[column] = TFTGame_leaderboard_df[column].astype(str)
                            #         for i in range(len(TFTGame_leaderboard_df)):
                            #             TFTGame_leaderboard_df.loc[i, column] = "√" if TFTGame_leaderboard_df[column][i] == "True" else ""
                            # TFTGame_leaderboard_df = pandas.concat([pandas.DataFrame([TFTGame_leaderboard_header])[TFTGame_leaderboard_df.columns], TFTGame_leaderboard_df], ignore_index = True)
                            
                            for j in range(len(TFTHistory_header)):
                                key = TFTHistory_header_keys[j]
                                if j == 0: #游戏序号（`gameIndex`）
                                    TFTHistory_data[key].append(i + 1)
                                elif j <= 13:
                                    if j == 1: #对局终止情况（`endOfGameResult`）
                                        if "endOfGameResult" in TFTHistoryJson:
                                            TFTHistory_data[key].append(endOfGameResults[TFTHistoryJson["endOfGameResult"]])
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
                                    for k in range(len(TFTHistoryJson["participants"])): #这里没有遵循迭代器命名原则，因为云顶之弈对局记录的赋值代码中包含了云顶之弈对局信息的赋值代码（Here the iterator naming principle isn't followed, because assignment code of TFT game information are included in those of TFT match information）
                                        TFTPlayer = TFTHistoryJson["participants"][k]
                                        if j == 14: #玩家序号（`participantId`）
                                            TFTGame_info_data[key].append(k + 1)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(k + 1)
                                        elif j >= 15 and j <= 23: #强化符文相关键（Augment-related keys）
                                            if "augments" in TFTPlayer:
                                                augment_index = (j - 15) % 3
                                                subkey_index = (j - 15) // 3
                                                if augment_index < len(TFTPlayer["augments"]):
                                                    TFTAugmentId = TFTPlayer["augments"][augment_index]
                                                    if subkey_index == 0:
                                                        to_append = TFTAugmentId
                                                    elif TFTAugmentId in TFTAugments:
                                                        to_append = TFTAugments[TFTAugmentId][key.split()[-1]]
                                                    elif TFTAugmentId in TFTAugments_initial:
                                                        to_append = TFTAugments_initial[TFTAugmentId][key.split()[-1]]
                                                    else:
                                                        if not TFTAugmentId in unmapped_keys["TFTAugment"]:
                                                            unmapped_keys["TFTAugment"].add(TFTAugmentId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）强化符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT augment information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTAugmentId, j, key, TFTAugmentId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                                        to_append = TFTAugmentId if subkey_index == 1 else ""
                                                else:
                                                    to_append = ""
                                            else:
                                                to_append = "" #云顶之弈刚出的时候，没有强化符文的概念（The concept of "augment" didn't appear at the beginning of TFT）
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid: #此处条件判断可优化为k == TFT_main_player_indices[i]（Here the judgment can be optimized into `k == TFT_main_player_indices[i]`）
                                                TFTHistory_data[key].append(to_append)
                                        elif j >= 24 and j <= 30: #小小英雄相关键（Companion-related keys）
                                            TFTCompanionId = TFTPlayer["companion"]["content_ID"]
                                            if j <= 27:
                                                to_append = TFTPlayer["companion"][key.split()[-1]]
                                            elif TFTCompanionId in TFTCompanions:
                                                to_append = TFTCompanions[TFTCompanionId][key.split()[-1]] if j <= 29 else rarities[TFTCompanions[TFTCompanionId][key.split()[-1]]]
                                            elif TFTCompanionId in TFTCompanions_initial:
                                                to_append = TFTCompanions_initial[TFTCompanionId][key.split()[-1]] if j <= 29 else rarities[TFTCompanions_initial[TFTCompanionId][key.split()[-1]]]
                                            else:
                                                if not TFTCompanionId in unmapped_keys["TFTCompanion"]:
                                                    unmapped_keys["TFTCompanion"].add(TFTCompanionId)
                                                    logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）小小英雄信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT companion information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTCompanionId, j, key, TFTCompanionId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                                to_append = TFTCompanionId if j == 28 else ""
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                        elif j == 37 or j == 38: #玩家昵称和昵称编号（`riotIdGameName` and `riotIdTagLine`）
                                            if key in TFTPlayer:
                                                to_append = TFTPlayer[key]
                                            else:
                                                if TFTPlayer["puuid"] in infos:
                                                    TFTPlayer_info_body = infos[TFTPlayer["puuid"]]
                                                    to_append = TFTPlayer_info_body["gameName"] if j == 37 else TFTPlayer_info_body["tagLine"]
                                                else:
                                                    if TFTPlayer["puuid"] == "00000000-0000-0000-0000-000000000000": #在云顶之弈（新手教程）中，无法通过电脑玩家的玩家通用唯一识别码（00000000-0000-0000-0000-000000000000）来查询其召唤师名称和序号（Summoner names and IDs of bot players in TFT (Tutorial) can't be searched for according to their puuid: 00000000-0000-0000-0000-000000000000）
                                                        to_append = ""
                                                    else:
                                                        TFTPlayer_info_recapture = 0
                                                        TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                                                        while not TFTPlayer_info["info_got"] and TFTPlayer_info["body"]["httpStatus"] != 404 and TFTPlayer_info_recapture < 3:
                                                            logPrint(TFTPlayer_info["message"])
                                                            TFTPlayer_info_recapture += 1
                                                            logPrint("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) in Match %d / %d (matchID: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer["puuid"], TFTPlayer_info_recapture, TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer_info_recapture))
                                                            TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                                                        if TFTPlayer_info["info_got"]:
                                                            TFTPlayer_info_body = TFTPlayer_info["body"]
                                                            infos[TFTPlayer["puuid"]] = TFTPlayer_info_body #虽然即使infos中已经存在该召唤师信息时也会执行这一步，但不会影响数据的准确性（Despite the this summoner's existence in `infos`, running this statement won't influence data accuracy）
                                                            to_append = TFTPlayer_info_body["gameName"] if j == 37 else TFTPlayer_info_body["tagLine"]
                                                        else:
                                                            logPrint(TFTPlayer_info["message"])
                                                            logPrint("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) in Match %d / %d (matchID: %d) capture failed!" %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer["puuid"], TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"]))
                                                            to_append = ""
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
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
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                        elif j == 42: #存活时长（`time_eliminated_norm`）
                                            to_append = "%d:%02d" %(int(TFTPlayer["time_eliminated"]) // 60, int(TFTPlayer["time_eliminated"]) % 60)
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                        else:
                                            to_append = TFTPlayer[key]
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                elif j <= 133: #云顶之弈羁绊相关键（TFT trait-related keys）
                                    #TFTMainPlayer_Traits = TFTHistoryJson["participants"][TFT_main_player_indices[i]]["traits"]
                                    trait_index = (j - 43) // 7
                                    subkey_index = (j - 43) % 7
                                    for k in range(len(TFTHistoryJson["participants"])):
                                        TFTPlayer = TFTHistoryJson["participants"][k]
                                        TFTPlayer_Traits = TFTPlayer["traits"]
                                        if TFTPlayer["puuid"] in infos:
                                            TFTPlayer_info_body = infos[TFTPlayer["puuid"]]
                                        elif TFTPlayer["puuid"] != "00000000-0000-0000-0000-000000000000":
                                            TFTPlayer_info_recapture = 0
                                            TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"]) #这里的玩家信息仅用于模板羁绊的提示（The summoner information here is only used for the prompt of TemplateTrait）
                                            while not TFTPlayer_info["info_got"] and TFTPlayer_info["body"]["httpStatus"] != 404 and TFTPlayer_info_recapture < 3:
                                                logPrint(TFTPlayer_info["message"])
                                                TFTPlayer_info_recapture += 1
                                                logPrint("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of Player (puuid: %s) in Match %d / %d (matchID: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer["puuid"], TFTPlayer_info_recapture, TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistoryJson["game_id"], TFTPlayer_info_recapture))
                                                TFTPlayer_info = await get_info(connection, TFTPlayer["puuid"])
                                            TFTPlayer_info_body = TFTPlayer_info["body"]
                                            if TFTPlayer_info["info_got"]:
                                                infos[TFTPlayer["puuid"]] = TFTPlayer_info_body
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
                                                elif TFTTraitId in TFTTraits_initial:
                                                    to_append = TFTTraits_initial[TFTTraitId][key.split()[-1]]
                                                else:
                                                    if not TFTTraitId in unmapped_keys["TFTTrait"]:
                                                        unmapped_keys["TFTTrait"].add(TFTTraitId)
                                                        logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）羁绊信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT trait information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTTraitId, j, key, TFTTraitId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                                    to_append = TFTTraitId if subkey_index == 5 else ""
                                        else:
                                            to_append = ""
                                        TFTGame_info_data[key].append(to_append)
                                        if TFTPlayer["puuid"] == current_puuid:
                                            TFTHistory_data[key].append(to_append)
                                else:
                                    #TFTMainPlayer_Units = TFTHistoryJson["participants"][TFT_main_player_indices[i]]["units"]
                                    for k in range(len(TFTHistoryJson["participants"])):
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
                                                    elif TFTChampionId in TFTChampions_initial:
                                                        to_append = TFTChampions_initial[TFTChampionId][key.split()[-1]]
                                                    elif TFTChampionId.lower() in map(lambda x: x.lower(), TFTChampions.keys()): #在获取艾欧尼亚对局序号为8390690410的英雄信息时，由于雷克塞的英雄序号大小写的原因，会引发键异常（KeyError is caused due to the case of "RekSai" string when the program is getting data from an Ionia match with matchID 8390690410）
                                                        TFTChampion_index = list(map(lambda x: x.lower(), TFTChampions.keys())).index(TFTChampionId.lower())
                                                        to_append = list(TFTChampions.values())[TFTChampion_index][key.split()[-1]]
                                                    elif TFTChampionId.lower() in map(lambda x: x.lower(), TFTChampions_initial.keys()):
                                                        TFTChampion_index = list(map(lambda x: x.lower(), TFTChampions_initial.keys())).index(TFTChampionId.lower())
                                                        to_append = list(TFTChampions_initial.values())[TFTChampion_index][key.split()[-1]]
                                                    else:
                                                        if not TFTChampionId in unmapped_keys["TFTCompanion"]:
                                                            unmapped_keys["TFTCompanion"].add(TFTChampionId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）棋子信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT champion information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTChampionId, j, key, TFTChampionId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                                        to_append = TFTChampionId if subkey_index == 3 else ""
                                                else:
                                                    to_append = TFTPlayer_Units[unit_index][key.split()[-1]]
                                            else:
                                                to_append = ""
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTHistoryJson["participants"][k]["puuid"] == current_puuid:
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
                                                    elif TFTItemId in TFTItems_initial:
                                                        to_append = TFTItems_initial[TFTItemId][key.split()[-1]]
                                                    elif TFTItemId in TFTAugments: #云顶之弈基础数据文件中存在部分云顶之弈装备数据文件中没有的装备（Some items are present in the TFT basic data file but absent from the TFT item data file）
                                                        item_basic_dict = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"} #云顶之弈装备数据文件和云顶之弈基础数据文件的格式不一致（The formats between TFT basic data and TFT item data are different）
                                                        to_append = TFTAugments[TFTItemId][item_basic_dict[key.split()[-1]]]
                                                    elif TFTItemId in TFTAugments_initial:
                                                        item_basic_dict = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"} #云顶之弈装备数据文件和云顶之弈基础数据文件的格式不一致（The formats between TFT basic data and TFT item data are different）
                                                        to_append = TFTAugments_initial[TFTItemId][item_basic_dict[key.split()[-1]]]
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
                                                    elif TFTItemId in TFTItems_initial:
                                                        to_append = TFTItems_initial[TFTItemId][key.split()[-1]]
                                                    elif TFTItemId in TFTAugments:
                                                        item_basic_dict = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"}
                                                        to_append = TFTAugments[TFTItemId][item_basic_dict[key.split()[-1]]]
                                                    elif TFTItemId in TFTAugments_initial:
                                                        item_basic_dict = {"nameId": "apiName", "name": "name", "squareIconPath": "icon"}
                                                        to_append = TFTAugments_initial[TFTItemId][item_basic_dict[key.split()[-1]]]
                                                    else:
                                                        if not TFTItemId in unmapped_keys["TFTItem"]:
                                                            unmapped_keys["TFTItem"].add(TFTItemId)
                                                            logPrint("【%d. %s】第%d/%d场对局（对局序号：%d，对局版本：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d / %d (matchID: %d, gameVersion: %s) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion, TFTItemId, j, key, TFTItemId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTGameVersion))
                                                        to_append = TFTItemId if subkey_index == 1 else ""
                                                else:
                                                    to_append = ""
                                            else:
                                                to_append = ""
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTHistoryJson["participants"][k]["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                        TFTGame_info_statistics_output_order = [0, 23, 24, 22, 14, 15, 16, 19, 27, 28, 17, 26, 21, 20, 4, 5, 6, 123, 121, 122, 176, 179, 182, 128, 126, 127, 185, 188, 191, 133, 131, 132, 194, 197, 200, 138, 136, 137, 203, 206, 209, 143, 141, 142, 212, 215, 218, 148, 146, 147, 221, 224, 227, 153, 151, 152, 230, 233, 236, 158, 156, 157, 239, 242, 245, 163, 161, 162, 248, 251, 254, 168, 166, 167, 257, 260, 263, 173, 171, 172, 266, 269, 272, 34, 30, 31, 32, 33, 41, 37, 38, 39, 40, 48, 44, 45, 46, 47, 55, 51, 52, 53, 54, 62, 58, 59, 60, 61, 69, 65, 66, 67, 68, 76, 72, 73, 74, 75, 83, 79, 80, 81, 82, 90, 86, 87, 88, 89, 97, 93, 94, 95, 96, 104, 100, 101, 102, 103, 111, 107, 108, 109, 110, 118, 114, 115, 116, 117]
                        TFTGame_info_data_organized = {}
                        for j in TFTGame_info_statistics_output_order:
                            key = TFTHistory_header_keys[j + 14]
                            TFTGame_info_data_organized[key] = TFTGame_info_data[key]
                        TFTGame_info_df = pandas.DataFrame(data = TFTGame_info_data_organized)
                        TFTGame_info_df = pandas.concat([pandas.DataFrame([TFTHistory_header])[TFTGame_info_df.columns], TFTGame_info_df], ignore_index = True)
                        TFTGame_info_df = TFTGame_info_df.stack().unstack(0)
                        if not (update_unsaved_only and matchID in saved_TFTMatchIDs):
                            game_info_dfs[matchID] = TFTGame_info_df.copy(deep = True)
                            # game_leaderboard_dfs[matchID] = TFTGame_leaderboard_df.copy(deep = True)
                        
                    TFTHistory_statistics_output_order = [0, 4, 11, 12, 13, 7, 8, 6, 10, 28, 29, 30, 33, 41, 42, 31, 40, 35, 34, 18, 19, 20, 137, 135, 136, 190, 193, 196, 142, 140, 141, 199, 202, 205, 147, 145, 146, 208, 211, 214, 152, 150, 151, 217, 220, 223, 157, 155, 156, 226, 229, 232, 162, 160, 161, 235, 238, 241, 167, 165, 166, 244, 247, 250, 172, 170, 171, 253, 256, 259, 177, 175, 176, 262, 265, 268, 182, 180, 181, 271, 274, 277, 187, 185, 186, 280, 283, 286, 48, 44, 45, 46, 47, 55, 51, 52, 53, 54, 62, 58, 59, 60, 61, 69, 65, 66, 67, 68, 76, 72, 73, 74, 75, 83, 79, 80, 81, 82, 90, 86, 87, 88, 89, 97, 93, 94, 95, 96, 104, 100, 101, 102, 103, 111, 107, 108, 109, 110, 118, 114, 115, 116, 117, 125, 121, 122, 123, 124, 132, 128, 129, 130, 131]
                    TFTHistory_data_organized = {}
                    for i in TFTHistory_statistics_output_order:
                        key = TFTHistory_header_keys[i]
                        TFTHistory_data_organized[key] = TFTHistory_data[key]
                    TFTHistory_df = pandas.DataFrame(data = TFTHistory_data_organized)
                    TFTHistory_df = pandas.concat([pandas.DataFrame([TFTHistory_header])[TFTHistory_df.columns], TFTHistory_df], ignore_index = True)
                    if TFTGamePlayed:
                        logPrint(TFTHistory_df[:min(21, len(TFTHistory_df) + 1)], write_time = False)
                    else:
                        logPrint("这位召唤师从5月1日起就没有进行过任何云顶之弈对局。\nThis summoner hasn't played any TFT game yet since May 1st.")
                else:
                    TFTHistory_searched = False
                
                matchIDs = list(game_info_dfs.keys())
                matchIDs.sort()
                logPrint("正在计算每场对局要保存的工作表数量……\nCalculating the number of sheets to be saved for each match ...\n")
                sheetNumber = {}
                for i in range(len(matchIDs)):
                    if not match_reserve_strategy[matchIDs[i]]:
                        sheetNumber[matchIDs[i]] = 0
                    else:
                        sheetNumber[matchIDs[i]] = (1 - info_exist_error[matchIDs[i]]) + 2 * (1 - timeline_exist_error[matchIDs[i]])
                
                recent_players_df = pandas.DataFrame() #起到占位作用，保证在使用自定义脚本11时生成的近期一起玩过的玩家数据一定是工作簿的第5和6张工作表（Act as a placeholder to ensure the recent played summoner data from Customized Program 11 are in the fifth and sixth sheets in the workbook)
                if not LoLHistory_searched:
                    LoLHistory_df = pandas.DataFrame() #起到占位作用，保证在使用本脚本时生成的英雄联盟对局记录一定是工作簿的第7张工作表（Act as a placeholder to ensure the LoL match history data from this program when running [One-Key Query] are in the seventh sheet in the workbook)
                    LoLGame_stat_df = pandas.DataFrame() #起到占位作用，保证在使用本脚本时生成的英雄联盟对局数据一定是工作簿的第8或9张工作表（Act as a placeholder to ensure the LoL game stats data from this program when running [One-Key Query] are in the eighth or ninth sheet in the workbook)
                    LoLGame_stat_df_export = False
                if not TFTHistory_searched:
                    TFTHistory_df = pandas.DataFrame() #起到占位作用，保证在使用本脚本时生成的云顶之弈对局记录一定是工作簿的第8、9或10张工作表（Act as a placeholder to ensure the TFT match history data from this program when running [One-Key Query] are in the eighth, ninth or tenth sheet in the workbook)

                #with open("infos.json", "w", encoding = "utf-8") as fp:
                    #json.dump(infos, fp, indent = 4, ensure_ascii = False)
                #定义条件格式（Define the conditional formats）
                twoDigitPercentage_columns_lol = [column for column in LoLGame_stat_df.columns if column.endswith("_percent") or column == "GUE"] #百分比（Percentage）
                oneDigitFloat_columns_lol = ["KDA"] #一位小数（One-digit float）
                threeDigitFloat_columns_lol = ["CSPM", "D/G", "GPM"] #三位小数（Three-digit float）
                colorScale_columns_lol = [column for column in LoLGame_stat_df.columns if column.endswith("_order")] #条件格式——渐变颜色（Conditional formatting - color scaling）
                dataBar_columns_lol = [column for column in LoLGame_stat_df.columns if column.endswith("_percent")] #条件格式——数据条（Conditional formatting - data bar）
                max_numPlayersPerTeam_lol = 5 if len(LoLGame_stat_df) <= 1 else max(map(lambda x: 5 if x == 0 else 2 if queues[x]["gameMode"] == "CHERRY" else queues[x]["numPlayersPerTeam"], LoLGame_stat_df.loc[1:, "queueId"])) #自定义对局的队伍规模视为5；斗魂竞技场的队伍规模虽然在API中记录为16，但这里应该考虑的是子阵营（The team size of any custom game is regarded as 5; although the team size of an Arena game is recorded as in LCU API, the subteam has more reference value）
                order_colorScaleRule_lol = ColorScaleRule(start_type = "num", start_value = 1, start_color = "63BE7B", mid_type = "percentile", mid_value = 50, mid_color = "FFEB84", end_type = "num", end_value = max_numPlayersPerTeam_lol, end_color = "FF6B6B") #跳过名次为0的单元格（Skip the order cells whose values are 0）
                percent_dataBarRule_lol = DataBarRule(start_type = "percentile", start_value = 0, end_type = "percentile", end_value = 100, color = Color("008AEF"), minLength = None, maxLength = None)
                
                logPrint("是否导出以上召唤师数据至Excel中？（输入任意键导出，否则不导出）\nDo you want to export the above data into Excel? (Press any key to export or null to refuse exporting)")
                export_str = logInput()
                export = bool(export_str)
                if export:
                    excel_name = "Summoner Profile - " + displayName + ".xlsx"
                    wbPath = os.path.join(folder, excel_name)
                    excel_name_sorted = "Summoner Profile - " + displayName + " (sorted).xlsx"
                    workbook_exist = os.path.exists(wbPath)
                    if workbook_exist:
                        if len(matchIDs) > 0 and sum(sheetNumber.values()) > 0:
                            logPrint("是否导出所有对局的详细信息？注意，这可能需要一定时间。（输入任意键导出，否则不导出。）\nDo you want to export detailed information of each match? Note that this may take some time. (Submit any non-empty string to export, or null to refuse exporting.)")
                            detail_export_str = logInput()
                            detail_export = bool(detail_export_str)
                        else:
                            detail_export = False
                        while True:
                            try:
                                with pandas.ExcelWriter(path = wbPath, engine = "openpyxl", mode = "a", if_sheet_exists = "replace") as writer:
                                    info_df.to_excel(excel_writer = writer, sheet_name = "Profile")
                                    logPrint("召唤师生涯导出完成！\nSummoner profile exported!\n")
                                    ranked_df.to_excel(excel_writer = writer, sheet_name = "Rank")
                                    logPrint("召唤师排位数据导出完成！\nSummoner ranked data exported!\n")
                                    if ladder_sort:
                                        ladders_df.to_excel(excel_writer = writer, sheet_name = "Ladders")
                                        logPrint("召唤师排位天梯数据导出完成！\nSummoner league ladder data exported!\n")
                                    mastery_df.to_excel(excel_writer = writer, sheet_name = "Champion Mastery")
                                    logPrint("召唤师英雄成就导出完成！\nSummoner champion mastery exported!\n")
                                    if LoLHistory_searched:
                                        if scan:
                                            LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                            worksheet = writer.sheets["LoL Match History - Scan"]
                                        else:
                                            LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                            worksheet = writer.sheets["LoL Match History"]
                                        worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                                        if len(LoLHistory_df) > 1:
                                            #胜负颜色（Win/Lose color）
                                            col_idx = LoLHistory_df.columns.get_loc("result") + 2
                                            col_letter = get_column_letter(col_idx)
                                            rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLHistory_df) + 1)
                                            win_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "胜利")], stopIfTrue = True, fill = PatternFill(start_color = "63BE7B", end_color = "63BE7B", fill_type = "solid"))
                                            lose_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "失败")], stopIfTrue = True, fill = PatternFill(start_color = "FF6B6B", end_color = "FF6B6B", fill_type = "solid"))
                                            worksheet.conditional_formatting.add(rangeStr, win_formulaRule_lol)
                                            worksheet.conditional_formatting.add(rangeStr, lose_formulaRule_lol)
                                            #斗魂竞技场队伍排名颜色设置（Arena subteamPlacement color）
                                            col_idx = LoLHistory_df.columns.get_loc("subteamPlacement") + 2
                                            col_letter = get_column_letter(col_idx)
                                            rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLHistory_df) + 1)
                                            firstPlace_formulaRule_lol = FormulaRule(formula = ['$%s3=1' %(col_letter)], stopIfTrue = False, fill = PatternFill(start_color = "FFC000", end_color = "FFC000", fill_type = "solid"))
                                            worksheet.conditional_formatting.add(rangeStr, firstPlace_formulaRule_lol)
                                        logPrint("召唤师英雄联盟对局记录导出完成！\nSummoner LoL match history exported!\n")
                                        if LoLGame_stat_df_export:
                                            LoLGame_stat_df.to_excel(excel_writer = writer, sheet_name = "LoL Match Stats")
                                            worksheet = writer.sheets["LoL Match Stats"]
                                            worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                                            if len(LoLGame_stat_df) > 1:
                                                #套用保留两位小数的百分比格式（Two-digit percentage）
                                                for column in twoDigitPercentage_columns_lol:
                                                    col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                                    for row in range(3, len(LoLGame_stat_df) + 2):
                                                        worksheet.cell(row = row, column = col_idx).number_format = numbers.FORMAT_PERCENTAGE_00
                                                #套用一位小数（One-digit float）
                                                for column in oneDigitFloat_columns_lol:
                                                    col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                                    for row in range(3, len(LoLGame_stat_df) + 2):
                                                        worksheet.cell(row = row, column = col_idx).number_format = "0.0"
                                                #套用三位小数（Three-digit float）
                                                for column in threeDigitFloat_columns_lol:
                                                    col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                                    for row in range(3, len(LoLGame_stat_df) + 2):
                                                        worksheet.cell(row = row, column = col_idx).number_format = "0.000"
                                                #胜负颜色（Win/Lose color）
                                                col_idx = LoLGame_stat_df.columns.get_loc("win/lose") + 2
                                                col_letter = get_column_letter(col_idx)
                                                rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLGame_stat_df) + 1)
                                                win_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "胜利")], stopIfTrue = True, fill = PatternFill(start_color = "63BE7B", end_color = "63BE7B", fill_type = "solid"))
                                                lose_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "失败")], stopIfTrue = True, fill = PatternFill(start_color = "FF6B6B", end_color = "FF6B6B", fill_type = "solid"))
                                                worksheet.conditional_formatting.add(rangeStr, win_formulaRule_lol)
                                                worksheet.conditional_formatting.add(rangeStr, lose_formulaRule_lol)
                                                #百分比颜色（Percent color）
                                                rangeStrs = [] #存储尽可能连贯的条件格式区域（Stores continuous conditional formatting areas）
                                                for i in range(len(dataBar_columns_lol)): #这里需要注意尽量保持条件格式的区域连贯，以免在打开工作簿时条件格式过多导致卡顿（Note that each conditional formatting area should be as large as possible, otherwise the workbook will perform slow when opening it due to too many rules）
                                                    column = dataBar_columns_lol[i]
                                                    if i == 0:
                                                        startCol_idx = endCol_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                                    else:
                                                        col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                                        if col_idx == endCol_idx + 1: #如果下一个要添加条件格式的列号与上一个要添加条件格式的列号差1，那么这两列是相邻的，即连贯的（If the number of the current column to add conditional format is greater than the number of the predecessive column to add conditional format by 1, then these two columns are continuous）
                                                            endCol_idx = col_idx
                                                        else: #如果两列不相邻，则提取得到上一个连贯的区域（If these two columns aren't continuous, then get the previous continuous area）
                                                            startCol_letter = get_column_letter(startCol_idx)
                                                            endCol_letter = get_column_letter(endCol_idx)
                                                            rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                                            rangeStrs.append(rangeStr)
                                                            startCol_idx = endCol_idx = col_idx #将区域的起始列和终止列设置为当前列（Set the starting and ending columns as the current column）
                                                else: #执行完成后，把最后一个连贯区域也加上（After the for-loop finishes, add the last continuous area）
                                                    startCol_letter = get_column_letter(startCol_idx)
                                                    endCol_letter = get_column_letter(endCol_idx)
                                                    rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                                    rangeStrs.append(rangeStr)
                                                for rangeStr in rangeStrs:
                                                    worksheet.conditional_formatting.add(rangeStr, percent_dataBarRule_lol)
                                                #斗魂竞技场队伍排名颜色设置（Arena subteamPlacement color）
                                                col_idx = LoLGame_stat_df.columns.get_loc("subteamPlacement") + 2
                                                col_letter = get_column_letter(col_idx)
                                                rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLGame_stat_df) + 1)
                                                firstPlace_formulaRule_lol = FormulaRule(formula = ['$%s3=1' %(col_letter)], stopIfTrue = False, fill = PatternFill(start_color = "FFC000", end_color = "FFC000", fill_type = "solid"))
                                                worksheet.conditional_formatting.add(rangeStr, firstPlace_formulaRule_lol)
                                                #位次颜色（Order color）
                                                rangeStrs = [] #存储尽可能连贯的条件格式区域（Stores continuous conditional formatting areas）
                                                rangeTuples = []
                                                for i in range(len(colorScale_columns_lol)): #这里需要注意尽量保持条件格式的区域连贯，以免在打开工作簿时条件格式过多导致卡顿（Note that each conditional formatting area should be as large as possible, otherwise the workbook will perform slow when opening it due to too many rules）
                                                    column = colorScale_columns_lol[i]
                                                    if i == 0:
                                                        startCol_idx = endCol_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                                    else:
                                                        col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                                        if col_idx == endCol_idx + 1: #如果下一个要添加条件格式的列号与上一个要添加条件格式的列号差1，那么这两列是相邻的，即连贯的（If the number of the current column to add conditional format is greater than the number of the predecessive column to add conditional format by 1, then these two columns are continuous）
                                                            endCol_idx = col_idx
                                                        else: #如果两列不相邻，则提取得到上一个连贯的区域（If these two columns aren't continuous, then get the previous continuous area）
                                                            startCol_letter = get_column_letter(startCol_idx)
                                                            endCol_letter = get_column_letter(endCol_idx)
                                                            rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                                            rangeStrs.append(rangeStr)
                                                            rangeTuples.append((startCol_letter, endCol_letter))
                                                            startCol_idx = endCol_idx = col_idx #将区域的起始列和终止列设置为当前列（Set the starting and ending columns as the current column）
                                                else: #执行完成后，把最后一个连贯区域也加上（After the for-loop finishes, add the last continuous area）
                                                    startCol_letter = get_column_letter(startCol_idx)
                                                    endCol_letter = get_column_letter(endCol_idx)
                                                    rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                                    rangeStrs.append(rangeStr)
                                                    rangeTuples.append((startCol_letter, endCol_letter))
                                                for i in range(len(rangeStrs)):
                                                    rangeStr = rangeStrs[i]
                                                    rangeTuple = rangeTuples[i]
                                                    order_noFillRule = FormulaRule(formula = ["%s3=0" %(rangeTuple[0])], stopIfTrue = True, fill = PatternFill(fill_type = None))
                                                    worksheet.conditional_formatting.add(rangeStr, order_noFillRule)
                                                    worksheet.conditional_formatting.add(rangeStr, order_colorScaleRule_lol)
                                            logPrint("召唤师英雄联盟战绩导出完成！\nSummoner LoL game stats exported!\n")
                                    if TFTHistory_searched:
                                        TFTHistory_df.to_excel(excel_writer = writer, sheet_name = "TFT Match History")
                                        logPrint("召唤师云顶之弈对局记录导出完成！\nSummoner TFT match history exported!\n")
                                    if detail_export:
                                        #logPrint(len(info_exist_error), len(timeline_exist_error), len(main_player_included), len(match_reserve_strategy))
                                        runTimes = [] #记录保存一场对局的所有数据所花费的时间（Records the time spent in saving all data of a match）
                                        total_used = 0
                                        match_reserved = 0
                                        for i in range(len(matchIDs)):
                                            start = time.time()
                                            if not main_player_included[matchIDs[i]]:
                                                if not match_reserve_strategy[matchIDs[i]]:
                                                    logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner and not exported!)" %(i + 1, len(matchIDs)))
                                                else:
                                                    logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner but yet exported!)" %(i + 1, len(matchIDs)))
                                            else:
                                                if not match_reserve_strategy[matchIDs[i]]: #这种情况只会发生在云顶之弈中（This case only happens on a TFT match）
                                                    logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match data deleted from API!)" %(i + 1, len(matchIDs)))
                                                elif info_exist_error[matchIDs[i]] and not timeline_exist_error[matchIDs[i]]:
                                                    logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information capture failure!)" %(i + 1, len(matchIDs)))
                                                elif not info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                                    logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match timeline capture failure!)" %(i + 1, len(matchIDs)))
                                                elif info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                                    logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information & timeline capture Failure!)" %(i + 1, len(matchIDs)))
                                                else:
                                                    logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d" %(i + 1, len(matchIDs)))
                                            logPrint("对局序号（MatchID）： %d" %matchIDs[i])
                                            if match_reserve_strategy[matchIDs[i]]:
                                                match_reserved += 1
                                                if not info_exist_error[matchIDs[i]]:
                                                    # game_leaderboard_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Leaderboard")
                                                    # logPrint("对局段位排行榜导出完成。\nMatch leaderboard exported.")
                                                    game_info_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Information")
                                                    logPrint("对局信息导出完成。\nMatch information exported.")
                                                if not timeline_exist_error[matchIDs[i]]:
                                                    game_timeline_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Timeline")
                                                    logPrint("对局时间轴导出完成。\nMatch timeline exported.")
                                                    game_event_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Events")
                                                    logPrint("对局事件导出完成。\nMatch events exported.")
                                            end = time.time()
                                            unit = end - start
                                            total_used += unit
                                            if match_reserve_strategy[matchIDs[i]]:
                                                runTimes.append((sheetNumber[matchIDs[i]], unit))
                                                total_remaining = 0 if sum([j[0] for j in runTimes[:match_reserved + 1]]) == 0 else sum([j[1] for j in runTimes[:match_reserved + 1]]) / sum([j[0] for j in runTimes[:match_reserved + 1]]) * sum([sheetNumber[matchIDs[j]] for j in range(i + 1, len(matchIDs))]) #需要考虑除数为0的情况（The case where the divisor is 0 needs considering）
                                                logPrint("保存本场对局所花费的时间（Time spent in saving this match）： %s" %(format_runtime(unit)))
                                                logPrint("已花费的总时间（Total time used）                          ： %s" %(format_runtime(total_used)))
                                                logPrint("剩余时间（Time remaining）                                 ： %s" %(format_runtime(total_remaining)))
                                                logPrint("预计总时间（Expected total time）                          ： %s" %(format_runtime(total_used + total_remaining)), end = "\n\n")
                            except PermissionError:
                                logPrint("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                logInput()
                            else:
                                if len(matchIDs) != 0:
                                    logPrint("对局信息和时间轴导出完成！\nMatch information and timeline exported!")
                                break
                    else:
                        os.makedirs(folder, exist_ok = True)
                        with pandas.ExcelWriter(path = wbPath, engine = "openpyxl") as writer:
                            info_df.to_excel(excel_writer = writer, sheet_name = "Profile")
                            logPrint("召唤师生涯导出完成！\nSummoner profile exported!\n")
                            ranked_df.to_excel(excel_writer = writer, sheet_name = "Rank")
                            logPrint("召唤师排位数据导出完成！\nSummoner ranked data exported!\n")
                            ladders_df.to_excel(excel_writer = writer, sheet_name = "Ladders")
                            logPrint("召唤师排位天梯数据导出完成！\nSummoner league ladder data exported!\n")
                            mastery_df.to_excel(excel_writer = writer, sheet_name = "Champion Mastery")
                            logPrint("召唤师英雄成就导出完成！\nSummoner champion mastery exported!\n")
                            pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (LoL)")
                            pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (TFT)")
                            logPrint("已创建近期一起玩过的玩家的空白数据表！\nCreated an empty sheet for recently played summoners!\n")
                            if LoLHistory_searched:
                                if scan:
                                    pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                    LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                    pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History - Manual")
                                    worksheet = writer.sheets["LoL Match History - Scan"]
                                else:
                                    LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                    pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                    pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History - Manual")
                                    worksheet = writer.sheets["LoL Match History"]
                                worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                                if len(LoLHistory_df) > 1:
                                    #胜负颜色（Win/Lose color）
                                    col_idx = LoLHistory_df.columns.get_loc("result") + 2
                                    col_letter = get_column_letter(col_idx)
                                    rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLHistory_df) + 1)
                                    win_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "胜利")], stopIfTrue = True, fill = PatternFill(start_color = "63BE7B", end_color = "63BE7B", fill_type = "solid"))
                                    lose_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "失败")], stopIfTrue = True, fill = PatternFill(start_color = "FF6B6B", end_color = "FF6B6B", fill_type = "solid"))
                                    worksheet.conditional_formatting.add(rangeStr, win_formulaRule_lol)
                                    worksheet.conditional_formatting.add(rangeStr, lose_formulaRule_lol)
                                    #斗魂竞技场队伍排名颜色设置（Arena subteamPlacement color）
                                    col_idx = LoLHistory_df.columns.get_loc("subteamPlacement") + 2
                                    col_letter = get_column_letter(col_idx)
                                    rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLHistory_df) + 1)
                                    firstPlace_formulaRule_lol = FormulaRule(formula = ['$%s3=1' %(col_letter)], stopIfTrue = False, fill = PatternFill(start_color = "FFC000", end_color = "FFC000", fill_type = "solid"))
                                    worksheet.conditional_formatting.add(rangeStr, firstPlace_formulaRule_lol)
                                logPrint("召唤师英雄联盟对局记录导出完成！\nSummoner LoL match history exported!\n")
                                LoLGame_stat_df.to_excel(excel_writer = writer, sheet_name = "LoL Match Stats")
                                worksheet = writer.sheets["LoL Match Stats"]
                                worksheet.conditional_formatting.rules = [] #读取时清空原规则（Clear original rules when reading）
                                if len(LoLGame_stat_df) > 1:
                                    #套用保留两位小数的百分比格式（Two-digit percentage）
                                    for column in twoDigitPercentage_columns_lol:
                                        col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                        for row in range(3, len(LoLGame_stat_df) + 2):
                                            worksheet.cell(row = row, column = col_idx).number_format = numbers.FORMAT_PERCENTAGE_00
                                    #套用一位小数（One-digit float）
                                    for column in oneDigitFloat_columns_lol:
                                        col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                        for row in range(3, len(LoLGame_stat_df) + 2):
                                            worksheet.cell(row = row, column = col_idx).number_format = "0.0"
                                    #套用三位小数（Three-digit float）
                                    for column in threeDigitFloat_columns_lol:
                                        col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                        for row in range(3, len(LoLGame_stat_df) + 2):
                                            worksheet.cell(row = row, column = col_idx).number_format = "0.000"
                                    #胜负颜色（Win/Lose color）
                                    col_idx = LoLGame_stat_df.columns.get_loc("win/lose") + 2
                                    col_letter = get_column_letter(col_idx)
                                    rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLGame_stat_df) + 1)
                                    win_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "胜利")], stopIfTrue = True, fill = PatternFill(start_color = "63BE7B", end_color = "63BE7B", fill_type = "solid"))
                                    lose_formulaRule_lol = FormulaRule(formula = ['$%s3="%s"' %(col_letter, "失败")], stopIfTrue = True, fill = PatternFill(start_color = "FF6B6B", end_color = "FF6B6B", fill_type = "solid"))
                                    worksheet.conditional_formatting.add(rangeStr, win_formulaRule_lol)
                                    worksheet.conditional_formatting.add(rangeStr, lose_formulaRule_lol)
                                    #百分比颜色（Percent color）
                                    rangeStrs = [] #存储尽可能连贯的条件格式区域（Stores continuous conditional formatting areas）
                                    for i in range(len(dataBar_columns_lol)): #这里需要注意尽量保持条件格式的区域连贯，以免在打开工作簿时条件格式过多导致卡顿（Note that each conditional formatting area should be as large as possible, otherwise the workbook will perform slow when opening it due to too many rules）
                                        column = dataBar_columns_lol[i]
                                        if i == 0:
                                            startCol_idx = endCol_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                        else:
                                            col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                            if col_idx == endCol_idx + 1: #如果下一个要添加条件格式的列号与上一个要添加条件格式的列号差1，那么这两列是相邻的，即连贯的（If the number of the current column to add conditional format is greater than the number of the predecessive column to add conditional format by 1, then these two columns are continuous）
                                                endCol_idx = col_idx
                                            else: #如果两列不相邻，则提取得到上一个连贯的区域（If these two columns aren't continuous, then get the previous continuous area）
                                                startCol_letter = get_column_letter(startCol_idx)
                                                endCol_letter = get_column_letter(endCol_idx)
                                                rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                                rangeStrs.append(rangeStr)
                                                startCol_idx = endCol_idx = col_idx #将区域的起始列和终止列设置为当前列（Set the starting and ending columns as the current column）
                                    else: #执行完成后，把最后一个连贯区域也加上（After the for-loop finishes, add the last continuous area）
                                        startCol_letter = get_column_letter(startCol_idx)
                                        endCol_letter = get_column_letter(endCol_idx)
                                        rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                        rangeStrs.append(rangeStr)
                                    for rangeStr in rangeStrs:
                                        worksheet.conditional_formatting.add(rangeStr, percent_dataBarRule_lol)
                                    #斗魂竞技场队伍排名颜色设置（Arena subteamPlacement color）
                                    col_idx = LoLGame_stat_df.columns.get_loc("subteamPlacement") + 2
                                    col_letter = get_column_letter(col_idx)
                                    rangeStr = "%s3:%s%d" %(col_letter, col_letter, len(LoLGame_stat_df) + 1)
                                    firstPlace_formulaRule_lol = FormulaRule(formula = ['$%s3=1' %(col_letter)], stopIfTrue = False, fill = PatternFill(start_color = "FFC000", end_color = "FFC000", fill_type = "solid"))
                                    worksheet.conditional_formatting.add(rangeStr, firstPlace_formulaRule_lol)
                                    #位次颜色（Order color）
                                    rangeStrs = [] #存储尽可能连贯的条件格式区域（Stores continuous conditional formatting areas）
                                    rangeTuples = []
                                    for i in range(len(colorScale_columns_lol)): #这里需要注意尽量保持条件格式的区域连贯，以免在打开工作簿时条件格式过多导致卡顿（Note that each conditional formatting area should be as large as possible, otherwise the workbook will perform slow when opening it due to too many rules）
                                        column = colorScale_columns_lol[i]
                                        if i == 0:
                                            startCol_idx = endCol_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                        else:
                                            col_idx = LoLGame_stat_df.columns.get_loc(column) + 2
                                            if col_idx == endCol_idx + 1: #如果下一个要添加条件格式的列号与上一个要添加条件格式的列号差1，那么这两列是相邻的，即连贯的（If the number of the current column to add conditional format is greater than the number of the predecessive column to add conditional format by 1, then these two columns are continuous）
                                                endCol_idx = col_idx
                                            else: #如果两列不相邻，则提取得到上一个连贯的区域（If these two columns aren't continuous, then get the previous continuous area）
                                                startCol_letter = get_column_letter(startCol_idx)
                                                endCol_letter = get_column_letter(endCol_idx)
                                                rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                                rangeStrs.append(rangeStr)
                                                rangeTuples.append((startCol_letter, endCol_letter))
                                                startCol_idx = endCol_idx = col_idx #将区域的起始列和终止列设置为当前列（Set the starting and ending columns as the current column）
                                    else: #执行完成后，把最后一个连贯区域也加上（After the for-loop finishes, add the last continuous area）
                                        startCol_letter = get_column_letter(startCol_idx)
                                        endCol_letter = get_column_letter(endCol_idx)
                                        rangeStr = "%s3:%s%d" %(startCol_letter, endCol_letter, len(LoLGame_stat_df) + 1)
                                        rangeStrs.append(rangeStr)
                                        rangeTuples.append((startCol_letter, endCol_letter))
                                    for i in range(len(rangeStrs)):
                                        rangeStr = rangeStrs[i]
                                        rangeTuple = rangeTuples[i]
                                        order_noFillRule = FormulaRule(formula = ["%s3=0" %(rangeTuple[0])], stopIfTrue = True, fill = PatternFill(fill_type = None))
                                        worksheet.conditional_formatting.add(rangeStr, order_noFillRule)
                                        worksheet.conditional_formatting.add(rangeStr, order_colorScaleRule_lol)
                                logPrint("召唤师英雄联盟战绩导出完成！\nSummoner LoL game stats exported!\n")
                            else:
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History - Manual")
                                logPrint("已创建英雄联盟对局记录的空白数据表！\nCreated an empty sheet for LoL match history!\n")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match Stats")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match Stats - Manual")
                                logPrint("已创建英雄联盟战绩的空白数据表。\nCreated an empty sheet for LoL game stats!\n")
                            if TFTHistory_searched:
                                TFTHistory_df.to_excel(excel_writer = writer, sheet_name = "TFT Match History")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "TFT Match History - Manual")
                                logPrint("召唤师云顶之弈对局记录导出完成！\nSummoner TFT match history exported!\n")
                            else:
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "TFT Match History")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "TFT Match History - Manual")
                                logPrint("已创建云顶之弈对局记录的空白工作表！\nCreated an empty sheet for TFT match history!\n")
                            runTimes = []
                            total_used = 0
                            match_reserved = 0
                            for i in range(len(matchIDs)):
                                start = time.time()
                                if not main_player_included[matchIDs[i]]:
                                    if not match_reserve_strategy[matchIDs[i]]:
                                        logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner and not exported!)" %(i + 1, len(matchIDs)))
                                    else:
                                        logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner but yet exported!)" %(i + 1, len(matchIDs)))
                                else:
                                    if not match_reserve_strategy[matchIDs[i]]: #这种情况只会发生在云顶之弈中（This case only happens on a TFT match）
                                        logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match data deleted from API!)" %(i + 1, len(matchIDs)))
                                    elif info_exist_error[matchIDs[i]] and not timeline_exist_error[matchIDs[i]]:
                                        logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information capture failure!)" %(i + 1, len(matchIDs)))
                                    elif not info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                        logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match timeline capture failure!)" %(i + 1, len(matchIDs)))
                                    elif info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                        logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information & timeline capture Failure!)" %(i + 1, len(matchIDs)))
                                    else:
                                        logPrint("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d" %(i + 1, len(matchIDs)))
                                logPrint("对局序号（MatchID）： %d" %matchIDs[i])
                                if match_reserve_strategy[matchIDs[i]]:
                                    match_reserved += 1
                                    if not info_exist_error[matchIDs[i]]:
                                        # game_leaderboard_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Leaderboard")
                                        # logPrint("对局段位排行榜导出完成。\nMatch leaderboard exported.")
                                        game_info_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Information")
                                        logPrint("对局信息导出完成。\nMatch information exported.")
                                    if not timeline_exist_error[matchIDs[i]]:
                                        game_timeline_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Timeline")
                                        logPrint("对局时间轴导出完成。\nMatch timeline exported.")
                                        game_event_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Events")
                                        logPrint("对局事件导出完成。\nMatch events exported.")
                                end = time.time()
                                unit = end - start
                                total_used += unit
                                if match_reserve_strategy[matchIDs[i]]:
                                    runTimes.append((sheetNumber[matchIDs[i]], unit))
                                    total_remaining = 0 if sum([j[0] for j in runTimes[:match_reserved + 1]]) == 0 else sum([j[1] for j in runTimes[:match_reserved + 1]]) / sum([j[0] for j in runTimes[:match_reserved + 1]]) * sum([sheetNumber[matchIDs[j]] for j in range(i + 1, len(matchIDs))]) #需要考虑除数为0的情况（The case where the divisor is 0 needs considering）
                                    logPrint("保存本场对局所花费的时间（Time spent in saving this match）： %s" %(format_runtime(unit)))
                                    logPrint("已花费的总时间（Total time used）                          ： %s" %(format_runtime(total_used)))
                                    logPrint("剩余时间（Time remaining）                                 ： %s" %(format_runtime(total_remaining)))
                                    logPrint("预计总时间（Expected total time）                          ： %s" %(format_runtime(total_used + total_remaining)), end = "\n\n")
                            if len(matchIDs) != 0:
                                logPrint("对局信息和时间轴导出完成！\nMatch information and timeline exported!")
                    if workbook_exist:
                        logPrint("警告：由于该文件已存在，本次导出已追加新工作表到工作簿的末尾。这可能导致对局序号顺序的错乱。是否需要对工作表进行排序？（输入任意键排序，否则不排序）\nWarning: Because the excel workbook has existed, new sheets are appended to the last of the original sheet list. This may result in the disarrangement of matchID order. Do you want to sort the sheets? (Input anything to sort the sheets, or null to skip sorting)")
                        sort_str = logInput()
                        sort = bool(sort_str)
                        if sort: #所有工作表分为基础信息类和对局信息类，排列顺序为前者在前、后者在后。基础信息工作表类按顺序依次为人物简介、排位信息、英雄成就和对局记录。对局信息类工作表包括对局信息和对局时间轴，按照对局序号排序（All sheets are divided into the basic data class and match information class, the former arranged in front of the latter. The basic data class includes profile, rank, champion mastery and match history in turn. The match information class includes match information and match timeline ordered by matchIDs）
                            profile_loaded = True
                            logPrint("正在读取刚刚创建的工作表……\nLoading the workbook just created ...")
                            while True:
                                try:
                                    wb = load_workbook(wbPath)
                                except FileNotFoundError:
                                    logPrint('召唤师生涯工作簿读取失败！请确保“%s”文件夹内含有名为“%s”的工作簿。如果需要重新生成该召唤师的工作簿，请输入“0”。\nERROR reading the summoner profile workbook! Please make sure the workbook "%s" is in the folder "%s". If you want to regenerate this summoner\'s workbook, please submit "0".' %(folder, excel_name, excel_name, folder))
                                    profile_reload = logInput()
                                    if profile_reload == "0":
                                        profile_loaded = False
                                        break
                                else:
                                    break
                            if profile_loaded:
                                sheetnames = wb.sheetnames #第一次获取原工作簿的工作表名称列表（The first time to get the sheet name list of the original workbook）
                                #下面锁定基础信息类的工作表顺序（The following code lock the order of sheets in basic data class）
                                logPrint("正在创建顺序工作表列表……\nCreating the ordered sheet list ...")
                                basic_info_list = ["Profile", "Rank", "Ladders", "Champion Mastery", "Recently Played Summoners (LoL)", "Recently Played Summoners (TFT)", "LoL Match History", "LoL Match History - Scan", "LoL Match History - Manual", "LoL Match Stats", "LoL Match Stats - Manual", "TFT Match History", "TFT Match History - Manual"]
                                match_dict = {}
                                for sheet_iter in sheetnames:
                                    if sheet_iter.startswith("Match "):
                                        matchID = int(sheet_iter.split()[1]) #目前暂不需要考虑对局序号因工作表名长度限制而被截断的问题（Currently the issue that matchID may be cut off due to the sheet name length limit doesn't need to be considered）
                                        key = sheet_iter.split()[3][0] #以工作表名的内容部分的首字母为排序依据（Sort the sheetnames by the initial letter of the content part of the sheet name）
                                        if not matchID in match_dict:
                                            match_dict[matchID] = {}
                                        match_dict[matchID][key] = sheet_iter
                                sheetnames_sorted = [] #所有工作表的期望顺序存储在sheetnames_sorted变量中（The ordered result of all sheets is stored in the variable `sheetnames_sorted`）
                                for sheet_iter in basic_info_list:
                                    if sheet_iter in sheetnames:
                                        sheetnames_sorted.append(sheet_iter)
                                for matchID in sorted(match_dict.keys()):
                                    if "L" in match_dict[matchID]:
                                        sheetnames_sorted.append(match_dict[matchID]["L"])
                                    if "I" in match_dict[matchID]:
                                        sheetnames_sorted.append(match_dict[matchID]["I"])
                                    if "T" in match_dict[matchID]:
                                        sheetnames_sorted.append(match_dict[matchID]["T"])
                                    if "E" in match_dict[matchID]:
                                        sheetnames_sorted.append(match_dict[matchID]["E"])
                                #下面排列所有工作表（The following code arrange all sheets）
                                logPrint("正在排序……\nOrdering ...")
                                for i in range(len(sheetnames_sorted)): #排序的思路是每次将一个工作表根据其在原工作表列表中的索引和在顺序工作表列表中的索引的差值进行移动（The main idea of sheets' sorting is to move each sheet according to the difference of the indices between in the original sheet list and in the ordered sheet list）
                                    sheetnames = wb.sheetnames #因为一次移动可能导致很多其它工作表的位置发生变化，所以必须每次都重新获取工作表列表（Because a moving event may result in location change of many other sheets, the sheet list must be obtained each time）
                                    sheetname_iter = sheetnames_sorted[i] #这里以顺序工作表为迭代器进行遍历，因为顺序工作表是固定不变的（Here the ordered sheet list acts as the iterator to be traversed, for the ordered sheet list is fixed）
                                    if sheetnames[i] != sheetname_iter:
                                        preIndex = sheetnames.index(sheetname_iter)
                                        wb.move_sheet(sheetname_iter, i - preIndex) #注意移动距离数应当是排序后的索引减去排序前的索引（Note that the moving offset should be the index in the ordered list subtracted by that in the original list）
                                    #logPrint("排序进度（Ordering process）：%d/%d\t工作表名称（Sheet name）： %s" %(i + 1, len(sheetnames_sorted), sheetname_iter))
                                logPrint('正在保存中……\nSaving the ordered workbook ...')
                                wb.save(os.path.join(folder, excel_name_sorted))
                                logPrint('排序完成！排好序的工作簿已保存为“%s”。\nOrdering finished! The ordered workbook is saved as "%s".\n' %(excel_name_sorted, excel_name_sorted))

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await search_profile(connection)
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
