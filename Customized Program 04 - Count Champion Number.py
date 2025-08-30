from lcu_driver import Connector
import json, pandas, re, requests, shutil, time, unicodedata, uuid
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

def patch_sort(patchList: list): #利用插入排序算法，根据patch_compare函数对版本列表进行升序排列（Sorts a patch list according to the principle of `patch_compare` function through the insertion sort algorithm）
    bigPatch_re = re.compile("[0-9]*.[0-9]*")
    if all(map(lambda x: isinstance(x, str), patchList)) and all(map(lambda x: bigPatch_re.search(x), patchList)): #此处放宽了参数的格式限制：只要列表的每个元素都是包含版本字符串的字符串即可（Here the function relaxes the limit for the format of the parameter: any list whose elements are all strings that contain a patch string is OK）
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

def getUrl(url: str):
    retry = 0
    while True:
        try:
            retry += 1
            source = requests.get(url)
            source.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            if retry > 5:
                break
            if http_err.response.status_code in {403, 404}:
                return (source, http_err.response.status_code)
        except requests.exceptions.SSLError as ssl_error:
            if retry > 5:
                break
            if "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol" in str(ssl_error):
                print("违反协议导致读取中断！正在尝试第%d次重新获取数据！\nEOF occurred in violation of protocol! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry))
            elif 'certificate verify failed' in str(ssl_error):
                print("SSL证书验证失败！正在尝试第%d次重新获取数据！\nSSL certificate verify failed! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry))
            elif 'Max retries exceeded with url' in str(ssl_error):
                print("请求数量超过限制！正在尝试第%d次重新获取数据！\nMax retries exceed with url! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry))
        except requests.exceptions.ProxyError:
            if retry > 5:
                break
            print("无法连接到代理！正在尝试第%d次重新获取数据！\nCannot connect to proxy! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry))
        except requests.exceptions.ChunkedEncodingError:
            if retry > 5:
                break
            print("接收数据块长度不正确导致连接中断！正在尝试第%d次重新获取数据！\nConnection broken: InvalidChunkLength. Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry))
        except requests.exceptions.ConnectionError:
            if retry > 5:
                break
            print("由于远程服务器端无响应，连接已关闭！正在尝试第%d次重新获取数据！\nRemote end closed connection without response. Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry))
        except requests.exceptions.ReadTimeout:
            if retry > 5:
                break
            print("读取超时！正在尝试第%d次重新获取数据！\nRead time out! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry))
        else:
            return (source, 0)
    if retry > 5:
        return (None, 1)

def count_nonASCII(s: str): #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str): #移除一个字符串中的所有C0和C1字符（Remove all C0 and C1 characters from a string）
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc") #该表达式等价于（This expression is equivalent to）`re.sub(r"[\x00-\x1F\x7F-\x9F]", "", s)`

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

def get_ddragon_champions() -> dict:
    src, status = getUrl(patches_url)
    if status != 0:
        if status == 1:
            print('版本信息获取超时！正在尝试离线加载数据……\nPatch information capture timeout! Trying loading offline data ...\n请输入版本Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“0”以退出程序。\nPlease enter the patch Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(patches_local_default, patches_local_default))
            while True:
                patches_local = input()
                if patches_local == "":
                    patches_local = patches_local_default
                elif patches_local[0] == "0":
                    print("版本信息获取失败！请检查系统网络状况和代理设置。\nPatch information capture failure! Please check the system network condition and agent configuration.")
                    time.sleep(3)
                    exit()
                try:
                    with open(patches_local, "r", encoding = "utf-8") as fp:
                        patches = json.load(fp)
                    if isinstance(patches, list) and patches[-1] == "lolpatch_3.7":
                        break
                    else:
                        print("数据格式错误！请选择一个符合DataDragon数据库中记录的版本数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the patch data archived in DataDragon database (%s)!" %(patches_url, patches_url))
                        continue
                except FileNotFoundError:
                    print("未找到文件%s！请输入正确的版本Json数据文件路径！\nFile %s NOT found! Please input a correct patch Json data file path!" %(patches_local, patches_local))
                    continue
                except OSError:
                    print("数据文件名不合法！请输入含有版本信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with patch information.")
                    continue
                except json.decoder.JSONDecodeError:
                    print("数据格式错误！请选择一个符合DataDragon数据库中记录的版本数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the patch data archived in DataDragon database (%s)!" %(patches_url, patches_url))
                    continue
        elif status == 404:
            print("版本信息文件不存在！请联系作者修复程序。\nPatch information resource file not found! Please contact the author and ask for a repair.")
    else:
        patches = src.json()
        latest_patch = patches[0]
    champion_local_default = ddragon_champion_local_default
    print("请输入您想要获取的版本。输入空字符串以获取最新版本英雄信息。\nPlease input the patch you want to search from. Submit an empty string to get the latest champion data. Examples: \n" + ", ".join(patches[:-98]))
    while True:
        patch_in_url = input()
        if patch_in_url == "":
            patch_in_url = patches[0]
        if patch_in_url in patches[:-98]:
            champion_url = "http://ddragon.leagueoflegends.com/cdn/%s/data/%s/championFull.json" %(patch_in_url, language_code)
            break
        else:
            print("版本输入有误！请重新输入。\nERROR input of patch! Please try again!")
    src, status = getUrl(champion_url)
    if status != 0:
        if status == 1:
            print('英雄数据获取超时！正在尝试离线加载数据……\nChampion data capture timeout! Trying loading offline data ...\n请输入英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“0”以退出程序。\nPlease enter the champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(champion_local_default, champion_local_default))
            while True:
                champion_local = input()
                if champion_local == "":
                    champion_local = champion_local_default
                elif champion_local[0] == "0":
                    print("英雄数据获取失败！请检查系统网络状况和代理设置。\nChampion data capture failure! Please check the system network condition and agent configuration.")
                    time.sleep(3)
                    exit()
                try:
                    with open(champion_local, "r", encoding = "utf-8") as fp:
                        LoLChampion = json.load(fp)
                    if isinstance(LoLChampion, dict) and all(i in LoLChampion for i in ["type", "format", "version", "data"]) and LoLChampion["type"] == "champion" and all(j in LoLChampion["data"][i] for i in LoLChampion["data"] for j in ["id", "key", "name", "title", "image", "skins", "lore", "blurb", "allytips", "enemytips", "tags", "partype", "info", "stats", "speklls", "passive", "recommended"]):
                        break
                    else:
                        print("数据格式错误！请选择一个符合DataDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the champion data archived in DataDragon database (%s)!" %(champion_url, champion_url))
                        continue
                except FileNotFoundError:
                    print("未找到文件%s！请输入正确的英雄Json数据文件路径！\nFile %s NOT found! Please input a correct champion Json data file path!" %(champion_local, champion_local))
                    continue
                except OSError:
                    print("数据文件名不合法！请输入含有英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with champion information.")
                    continue
                except json.decoder.JSONDecodeError:
                    print("数据格式错误！请选择一个符合DataDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the champion data archived in DataDragon database (%s)!" %(champion_url, champion_url))
                    continue
    else:
        LoLChampion = src.json()
    return LoLChampion
        
def sort_ddragon_champions(LoLChampion: dict) -> pandas.DataFrame:
    #下面按照程序需求对数据资源进行一定的整理（The following code sort out the data resource according to the program's need）
    LoLChampions = {}
    for champion in LoLChampion["data"].values():
        LoLChampions[int(champion["key"])] = champion
    LoLChampions_header = {"id": "英雄代码", "key": "英雄序号", "name": "称号", "title": "名称", "skins": "皮肤", "lore": "故事", "blurb": "背景介绍", "allytips": "游玩提示", "enemytips": "对抗提示", "partype": "施法资源属性", "recommended": "推荐配置", "image: full": "完整图像名", "image: sprite": "精灵图像名", "image: group": "图像组别", "image: x": "图像锚点横坐标", "image: y": "图像锚点纵坐标", "image: w": "图像宽度", "image: h": "图像高度", "tag: Assassin": "角色定位：刺客", "tag: Fighter": "角色定位：战士", "tag: Mage": "角色定位：法师", "tag: Marksman": "角色定位：射手", "tag: Support": "角色定位：辅助", "tag: Tank": "角色定位：坦克", "info: attack": "伤害属性得分", "info: defense": "强韧属性得分", "info: magic": "法术属性得分", "info: difficulty": "使用难度系数", "hp": "基础生命值", "hpperlevel": "生命值成长", "mp": "基础法力/能量值", "mpperlevel": "法力/能量值成长", "movespeed": "移动速度", "armor": "护甲", "armorperlevel": "护甲成长", "spellblock": "魔法抗性", "spellblockperlevel": "魔法抗性成长", "attackrange": "攻击距离", "hpregen": "生命回复", "hpregenperlevel": "生命回复成长", "mpregen": "施法资源回复", "mpregenperlevel": "法力/能量回复成长", "crit": "暴击率", "critperlevel": "暴击率成长", "attackdamage": "攻击力", "attackdamageperlevel": "攻击力成长", "attackspeedperlevel": "攻击速度成长", "attackspeed": "攻击速度", "lvl18hp": "18级生命值", "lvl30hp": "30级生命值", "lvl18mp": "18级法力/能量值", "lvl30mp": "30级法力/能量值", "lvl18attackdamage": "18级攻击力", "lvl30attackdamage": "30级攻击力", "lvl18armor": "18级护甲", "lvl30armor": "30级护甲", "lvl18spellblock": "18级魔法抗性", "lvl30spellblock": "30级魔法抗性", "lvl18attackspeed": "18级攻击速度", "lvl30attackspeed": "30级攻击速度", "lvl18hpregen": "18级生命回复", "lvl30hpregen": "30级生命回复", "lvl18mpregen": "18级施法资源回复", "lvl30mpregen": "30级施法资源回复", "spell1: id": "技能1编号", "spell1: name": "技能1名称", "spell1: description": "技能1简介", "spell1: tooltip": "技能1详细信息", "spell1: maxrank": "技能1最大等级", "spell1: cooldown": "技能1冷却时间", "spell1: cooldownBurn": "技能1冷却时间简化表示", "spell1: cost": "技能1消耗", "spell1: costBurn": "技能1消耗简化表示", "spell1: datavalues": "技能1具体数值", "spell1: effect": "技能1效果参数", "spell1: effectBurn": "技能1效果参数简化表示", "spell1: vars": "技能1变量", "spell1: costType": "技能1施法资源", "spell1: maxammo": "技能1最大充能数", "spell1: range": "技能1施法距离", "spell1: rangeBurn": "技能1施法距离简化表示", "spell1: resource": "技能1施法资源描述", "spell1: leveltip: label": "技能1升级对象", "spell1: leveltip: effect": "技能1升级效果", "spell1: image: full": "技能1完整图像名", "spell1: image: sprite": "技能1精灵图", "spell1: image: group": "技能1图像组别", "spell1: image: x": "技能1图像锚点横坐标", "spell1: image: y": "技能1图像锚点纵坐标", "spell1: image: w": "技能1图像宽度", "spell1: image: h": "技能1图像高度", "spell2: id": "技能2编号", "spell2: name": "技能2名称", "spell2: description": "技能2简介", "spell2: tooltip": "技能2详细信息", "spell2: maxrank": "技能2最大等级", "spell2: cooldown": "技能2冷却时间", "spell2: cooldownBurn": "技能2冷却时间简化表示", "spell2: cost": "技能2消耗", "spell2: costBurn": "技能2消耗简化表示", "spell2: datavalues": "技能2具体数值", "spell2: effect": "技能2效果参数", "spell2: effectBurn": "技能2效果参数简化表示", "spell2: vars": "技能2变量", "spell2: costType": "技能2施法资源", "spell2: maxammo": "技能2最大充能数", "spell2: range": "技能2施法距离", "spell2: rangeBurn": "技能2施法距离简化表示", "spell2: resource": "技能2施法资源描述", "spell2: leveltip: label": "技能2升级对象", "spell2: leveltip: effect": "技能2升级效果", "spell2: image: full": "技能2完整图像名", "spell2: image: sprite": "技能2精灵图", "spell2: image: group": "技能2图像组别", "spell2: image: x": "技能2图像锚点横坐标", "spell2: image: y": "技能2图像锚点纵坐标", "spell2: image: w": "技能2图像宽度", "spell2: image: h": "技能2图像高度", "spell3: id": "技能3编号", "spell3: name": "技能3名称", "spell3: description": "技能3简介", "spell3: tooltip": "技能3详细信息", "spell3: maxrank": "技能3最大等级", "spell3: cooldown": "技能3冷却时间", "spell3: cooldownBurn": "技能3冷却时间简化表示", "spell3: cost": "技能3消耗", "spell3: costBurn": "技能3消耗简化表示", "spell3: datavalues": "技能3具体数值", "spell3: effect": "技能3效果参数", "spell3: effectBurn": "技能3效果参数简化表示", "spell3: vars": "技能3变量", "spell3: costType": "技能3施法资源", "spell3: maxammo": "技能3最大充能数", "spell3: range": "技能3施法距离", "spell3: rangeBurn": "技能3施法距离简化表示", "spell3: resource": "技能3施法资源描述", "spell3: leveltip: label": "技能3升级对象", "spell3: leveltip: effect": "技能3升级效果", "spell3: image: full": "技能3完整图像名", "spell3: image: sprite": "技能3精灵图", "spell3: image: group": "技能3图像组别", "spell3: image: x": "技能3图像锚点横坐标", "spell3: image: y": "技能3图像锚点纵坐标", "spell3: image: w": "技能3图像宽度", "spell3: image: h": "技能3图像高度", "spell4: id": "技能4编号", "spell4: name": "技能4名称", "spell4: description": "技能4简介", "spell4: tooltip": "技能4详细信息", "spell4: maxrank": "技能4最大等级", "spell4: cooldown": "技能4冷却时间", "spell4: cooldownBurn": "技能4冷却时间简化表示", "spell4: cost": "技能4消耗", "spell4: costBurn": "技能4消耗简化表示", "spell4: datavalues": "技能4具体数值", "spell4: effect": "技能4效果参数", "spell4: effectBurn": "技能4效果参数简化表示", "spell4: vars": "技能4变量", "spell4: costType": "技能4施法资源", "spell4: maxammo": "技能4最大充能数", "spell4: range": "技能4施法距离", "spell4: rangeBurn": "技能4施法距离简化表示", "spell4: resource": "技能4施法资源描述", "spell4: leveltip: label": "技能4升级对象", "spell4: leveltip: effect": "技能4升级效果", "spell4: image: full": "技能4完整图像名", "spell4: image: sprite": "技能4精灵图", "spell4: image: group": "技能4图像组别", "spell4: image: x": "技能4图像锚点横坐标", "spell4: image: y": "技能4图像锚点纵坐标", "spell4: image: w": "技能4图像宽度", "spell4: image: h": "技能4图像高度", "passive: name": "被动技能名称", "passive: description": "被动技能简介", "passive: image: full": "被动技能完整图像名", "passive: image: sprite": "被动技能精灵图", "passive: image: group": "被动技能图像组别", "passive: image: x": "被动技能图像锚点横坐标", "passive: image: y": "被动技能图像锚点纵坐标", "passive: image: w": "被动技能图像宽度", "passive: image: h": "被动技能图像高度"}
    LoLChampions_header_keys = list(LoLChampions_header.keys())
    LoLChampions_data = {}
    for i in range(len(LoLChampions_header_keys)):
        key = LoLChampions_header_keys[i]
        LoLChampions_data[key] = []
    print("championId\tname\ttitle\talias")
    count = 0
    for i in sorted(LoLChampions.keys()):
        champion = LoLChampions[i]
        print("%s\t%s\t%s\t%s" %(champion["key"], champion["name"], champion["title"], champion["id"]))
        if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
            count += 1
        for j in range(len(LoLChampions_header_keys)):
            key = LoLChampions_header_keys[j]
            if j <= 10:
                if j == 1: #DataDragon数据库中存储的英雄序号为字符串（ChampionIds stored in DataDragon database are of string type）
                    LoLChampions_data[key].append(int(champion[key]))
                else:
                    LoLChampions_data[key].append(champion[key])
            elif j <= 17: #英雄图像相关键（Champion image related keys）
                LoLChampions_data[key].append(champion["image"][key.split(": ")[1]])
            elif j <= 23: #标签（Tags）
                if key.split(": ")[1] in champion["tags"]:
                    LoLChampions_data[key].append("√")
                else:
                    LoLChampions_data[key].append("")
            elif j <= 27: #英雄信息相关键（Champion info related keys）
                LoLChampions_data[key].append(champion["info"][key.split(": ")[1]])
            elif j <= 47: #英雄属性相关键（Stats related keys）
                LoLChampions_data[key].append(champion["stats"][key])
            elif j <= 63: #英雄属性成长相关键（Stats growth related keys）
                level, subkey = int(key[3:5]), key[5:]
                result = champion["stats"][subkey] + (level - 1) * champion["stats"][subkey + "perlevel"] * (0.01 if subkey == "attackspeed" else 1) #攻击速度成长是百分比（`attackspeedperlevel` is a percentage）
            else: #技能相关键（Spell related keys）
                spell = champion["spells"][int(key[5:6]) - 1] if j <= 171 else champion["passive"]
                subkey_list = key.split(": ")[1:]
                value = spell
                for subkey in subkey_list:
                    if j <= 171 and spell["id"] == "JayceStanceHtG" and subkey == "leveltip": #杰斯的R技能没有升级提示（Jayce's R doesn't have leveltips）
                        value = ""
                        break
                    value = value[subkey]
                LoLChampions_data[key].append(value)
    LoLChampions_statistics_output_order = [1, 2, 3, 0, 6, 9, 24, 25, 26, 27, 18, 19, 20, 21, 22, 23, 28, 29, 30, 31, 44, 45, 33, 34, 35, 36, 47, 46, 42, 43, 32, 38, 39, 40, 41, 37, 172, 65, 92, 119, 146]
    #LoLChampions_statistics_output_order = [1, 2, 3, 0, 6, 9, 24, 25, 26, 27, 18, 19, 20, 21, 22, 23, 28, 29, 48, 49, 30, 31, 50, 51, 44, 45, 52, 53, 33, 34, 54, 55, 35, 36, 56, 57, 47, 46, 58, 59, 42, 43, 32, 38, 39, 60, 61, 40, 41, 62, 63, 37] #带成长数值（With leveling up stats）
    LoLChampions_data_organized = {}
    for i in LoLChampions_statistics_output_order:
        key = LoLChampions_header_keys[i]
        LoLChampions_data_organized[key] = LoLChampions_data[key]
    LoLChampions_df = pandas.DataFrame(data = LoLChampions_data_organized)
    LoLChampions_df = pandas.concat([pandas.DataFrame([LoLChampions_header])[LoLChampions_df.columns], LoLChampions_df], ignore_index = True)
    return LoLChampions_df

def get_cdragon_champions() -> dict:
    print("请输入您想要获取的版本。输入空字符串以获取最新版本英雄信息。\nPlease input the patch you want to search from. Submit an empty string to get the latest champion data. Examples: ")
    src, status = getUrl("https://raw.communitydragon.org/") #对应于DataDragon数据库的版本，下面从CommunityDragons数据库主页的源代码获取可用版本（Corresponding to getting patches DataDragon database, the following code crawl the available patches in CommunityDragon database through its homepage）
    if status != 0:
        if status == 1:
            print("CommunityDragon数据库主页访问失败！\nCommunityDragon database homepage access failed!")
            time.sleep(3)
            exit()
        elif status == 404:
            print("CommunityDragon数据库主页不存在！可能它已经变更了。请联系作者修复程序。\nCommunityDragon database homepage not found! Maybe it's changed. Please contact the author and ask for a repair.")
            time.sleep(3)
            exit()
    else:
        cdragon_homepage = src
        sourceCode = cdragon_homepage.content.decode()
        source_list = list(map(lambda x: x.strip(), sourceCode.split("\n")))
        line_re = re.compile(r'<tr><td class="link"><a href="[0-9]*\.[0-9]*/" title="[0-9]*\.[0-9]*">[0-9]*\.[0-9]*/</a></td><td class="size">-</td><td class="date">[0-9]*-[a-zA-Z]*-[0-9]* [0-9]*:[0-9]*</td></tr>')
        patch_re = re.compile(r'[0-9]*\.[0-9]*')
        patches_cdragon = []
        for line in source_list:
            matchedLine = line_re.search(line) #先通过一个比较长的正则表达式筛选包含版本信息的CSS代码行（First filter the CSS code lines that contain patch information through a long regular expression）
            if matchedLine:
                matchedPatch = patch_re.search(line).group() #在包含版本信息的CSS代码中再获取版本字符串（Then obtains patch string from the CSS code that contain it）
                patches_cdragon.append(matchedPatch)
        patches_cdragon = patch_sort(patches_cdragon)
        patches_cdragon.insert(0, "pbe")
        patches_cdragon.insert(0, "latest")
        print(", ".join(patches_cdragon))
        while True:
            patch_in_url = input()
            if patch_in_url == "":
                patch_in_url = patches_cdragon[1]
            if patch_in_url in patches_cdragon:
                champion_folder_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champions/" %(patch_in_url, language_code.lower())
                break
            else:
                print("版本输入有误！请重新输入。\nERROR input of patch! Please try again!")
    #下面获取每个英雄的数据资源链接（The following code obtain the data resource url of each champion）
    src, status = getUrl(champion_folder_url)
    if status != 0:
        if status == 1:
            print("英雄文件夹访问失败！\nChampion folder access failed!")
            time.sleep(3)
            exit()
        elif status == 404:
            print("英雄文件夹不存在！请联系作者修复程序。\nChampion folder not found! Please contact the author and ask for a repair.")
            time.sleep(3)
            exit()
    else:
        champion_folder = src
        sourceCode = champion_folder.content.decode()
        source_list = list(map(lambda x: x.strip(), sourceCode.split("\n")))
        line_re = re.compile(r'<tr><td class="link"><a href="-?[0-9]*\.json" title="-?[0-9]*\.json">-?[0-9]*\.json</a></td><td class="size">.*</td><td class="date">[0-9]*-[a-zA-Z]*-[0-9]* [0-9]*:[0-9]*</td></tr>')
        json_re = re.compile(r'-?[0-9]*\.json')
        champion_urls = []
        champion_files = {}
        for line in source_list:
            matchedLine = line_re.search(line)
            if matchedLine:
                matchedJson = json_re.search(line).group()
                champion_files[int(matchedJson[:-5])] = matchedJson
        for championId in sorted(champion_files.keys()):
            champion_urls.append(champion_folder_url + champion_files[championId])
    champion_local_default = cdragon_champion_local_default
    champion_files_ready = False
    LoLChampion = []
    #注释以下代码以直接离线加载数据资源（Comment out the following code to load offline data resources directly）
    for i in range(len(champion_urls)):
        champion_url = champion_urls[i]
        src, status = getUrl(champion_url)
        if status != 0:
            break
        champion = src.json()
        LoLChampion.append(champion)
        print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
        print("获取进度（Capturing process）：%d/%d" %(i + 1, len(champion_urls)))
    else:
        champion_files_ready = True #任何一个文件获取失败都会导致程序进入离线加载模式（Any file that failed to be loaded will cause to program to load all data again offline）
    #注释以上代码以直接离线加载数据资源（Comment out the above code to load offline data resources directly）
    if not champion_files_ready:
        print('英雄信息获取超时！正在尝试离线加载数据……\nChampion information capture timeout! Trying loading offline data ...\n请输入英雄Json数据文件夹路径。输入空字符以使用默认相对引用路径“%s”。输入“0”以退出程序。\nPlease enter the champion Json data folder path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(champion_local_default, champion_local_default))
        while True:
            LoLChampion = []
            champion_local = input()
            if champion_local == "":
                champion_local = champion_local_default
            elif champion_local[0] == "0":
                print("英雄数据获取失败！请检查系统网络状况和代理设置。\nChampion data capture failure! Please check the system network condition and agent configuration.")
                time.sleep(3)
                exit()
            try:
                for championId in sorted(champion_files.keys()):
                    with open(champion_local + champion_files[championId], "r", encoding = "utf-8") as fp:
                        champion = json.load(fp)
                    if isinstance(champion, dict) and all([i in champion for i in ["id", "name", "alias", "title", "shortBio", "tacticalInfo", "playstyleInfo", "squarePortraitPath", "stingerSfxPath", "chooseVoPath", "banVoPath", "roles", "recommendedItemDefaults", "skins", "passive", "spells"]]) and all(isinstance(i, dict) for i in [champion["tacticalInfo"], champion["playstyleInfo"], champion["passive"]]) and all(i in champion["tacticalInfo"] for i in ["style", "difficulty", "damageType"]) and all(i in champion["playstyleInfo"] for i in ["damage", "durability", "crowdControl", "mobility", "utility"]) and all(i in champion["passive"] for i in ["name", "abilityIconPath", "abilityVideoPath", "abilityVideoImagePath", "description"]) and all(isinstance(i, int) for i in [champion["id"], champion["tacticalInfo"]["style"], champion["tacticalInfo"]["difficulty"], champion["playstyleInfo"]["damage"], champion["playstyleInfo"]["durability"], champion["playstyleInfo"]["crowdControl"], champion["playstyleInfo"]["mobility"], champion["playstyleInfo"]["utility"]]) and all(isinstance(i, str) for i in [champion["name"], champion["alias"], champion["title"], champion["shortBio"], champion["squarePortraitPath"], champion["stingerSfxPath"], champion["chooseVoPath"], champion["banVoPath"], champion["tacticalInfo"]["damageType"], champion["passive"]["name"], champion["passive"]["abilityIconPath"], champion["passive"]["abilityVideoPath"], champion["passive"]["abilityVideoImagePath"], champion["passive"]["description"]]) and all(isinstance(i, list) for i in [champion["roles"], champion["recommendedItemDefaults"], champion["skins"], champion["spells"]]):
                        LoLChampion.append(champion)
                    else:
                        print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the champion data archived in CommunityDragon database (%s)!" %(champion_url, champion_url))
                        break
            except FileNotFoundError:
                print("未找到文件%s！请输入正确的英雄Json数据文件夹路径！\nFile %s NOT found! Please input a correct champion Json data folder path!" %(champion_local, champion_local))
                continue
            except OSError:
                print("数据文件名不合法！请输入含有英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with champion information.")
                continue
            except json.decoder.JSONDecodeError:
                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the champion data archived in CommunityDragon database (%s)!" %(champion_url, champion_url))
                continue
            else:
                break
    return LoLChampion

def sort_cdragon_champions(LoLChampion: dict) -> pandas.DataFrame:
    LoLChampions = {}
    for champion in LoLChampion:
        LoLChampions[champion["id"]] = champion
    LoLChampions_header = {"id": "英雄序号", "name": "称号", "alias": "英雄代号", "title": "名称", "shortBio": "背景简介", "squarePortraitPath": "方格头像路径", "stingerSfxPath": "锁定音效路径", "chooseVoPath": "锁定台词路径", "banVoPath": "禁用台词路径", "recommendedItemDefaults": "默认推荐装备序号列表", "tacticalInfo: style": "战略信息：风格【表明英雄的伤害输出方式的倾向（普攻vs技能）】", "tacticalInfo: difficulty": "战略信息：难度（英雄的使用难度）", "tacticalInfo: damageType": "战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】", "tacticalInfo: attackType": "战略信息：攻击方式", "playStyleInfo: damage": "玩法雷达图：伤害（用来对敌方英雄造成伤害的英雄技能）得分", "playStyleInfo: durability": "玩法雷达图：强韧（用来吸收来自敌方英雄伤害的英雄技能）得分", "playStyleInfo: crowdControl": "玩法雷达图：控制（用来对敌方英雄施加诸如减速和晕眩的有害效果的英雄技能）得分", "playStyleInfo: mobility": "玩法雷达图：机动（通过使用闪现或位移来快速在地图四处移动的英雄技能）得分", "playStyleInfo: utility": "玩法雷达图：功能（用来对友军提供护盾、治疗或移动速度等有益效果的英雄技能）得分", "championTagInfo: championTagPrimary": "英雄标签信息：第一标签", "championTagInfo: championTagSecondary": "英雄标签信息：第二标签", "role: assassin": "角色定位：刺客", "role: fighter": "角色定位：战士", "role: mage": "角色定位：法师", "role: marksman": "角色定位：射手", "role: support": "角色定位：辅助", "role: tank": "角色定位：坦克", "passive: name": "被动技能名称", "passive: abilityIconPath": "被动技能图标路径", "passive: abilityVideoPath": "被动技能动画视频路径", "passive: abilityVideoImagePath": "被动技能动画预览图路径", "passive: description": "被动技能简述", "spell1: spellKey": "技能1热键", "spell1: name": "技能1名称", "spell1: abilityIconPath": "技能1图标路径", "spell1: abilityVideoPath": "技能1动画视频路径", "spell1: abilityVideoImagePath": "技能1动画预览图路径", "spell1: cost": "技能1消耗计算方式", "spell1: cooldown": "技能1冷却时间计算方式", "spell1: description": "技能1简述", "spell1: dynamicDescription": "技能1详细信息", "spell1: range": "技能1施法距离", "spell1: costCoefficients": "技能1施法资源系数", "spell1: cooldownCoefficients": "技能1冷却时间系数", "spell1: maxLevel": "技能1最大等级", "spell1: coefficients: coefficient1": "技能1系数1", "spell1: coefficients: coefficient2": "技能1系数2", "spell1: effectAmounts: Effect1Amount": "技能1效应因子1", "spell1: effectAmounts: Effect2Amount": "技能1效应因子2", "spell1: effectAmounts: Effect3Amount": "技能1效应因子3", "spell1: effectAmounts: Effect4Amount": "技能1效应因子4", "spell1: effectAmounts: Effect5Amount": "技能1效应因子5", "spell1: effectAmounts: Effect6Amount": "技能1效应因子6", "spell1: effectAmounts: Effect7Amount": "技能1效应因子7", "spell1: effectAmounts: Effect8Amount": "技能1效应因子8", "spell1: effectAmounts: Effect9Amount": "技能1效应因子9", "spell1: effectAmounts: Effect10Amount": "技能1效应因子10", "spell1: ammo: ammoRechargeTime": "技能1充能时间", "spell1: ammo: maxAmmo": "技能1最大充能数", "spell2: spellKey": "技能2热键", "spell2: name": "技能2名称", "spell2: abilityIconPath": "技能2图标路径", "spell2: abilityVideoPath": "技能2动画视频路径", "spell2: abilityVideoImagePath": "技能2动画预览图路径", "spell2: cost": "技能2消耗计算方式", "spell2: cooldown": "技能2冷却时间计算方式", "spell2: description": "技能2简述", "spell2: dynamicDescription": "技能2详细信息", "spell2: range": "技能2施法距离", "spell2: costCoefficients": "技能2施法资源系数", "spell2: cooldownCoefficients": "技能2冷却时间系数", "spell2: maxLevel": "技能2最大等级", "spell2: coefficients: coefficient1": "技能2系数1", "spell2: coefficients: coefficient2": "技能2系数2", "spell2: effectAmounts: Effect1Amount": "技能2效应因子1", "spell2: effectAmounts: Effect2Amount": "技能2效应因子2", "spell2: effectAmounts: Effect3Amount": "技能2效应因子3", "spell2: effectAmounts: Effect4Amount": "技能2效应因子4", "spell2: effectAmounts: Effect5Amount": "技能2效应因子5", "spell2: effectAmounts: Effect6Amount": "技能2效应因子6", "spell2: effectAmounts: Effect7Amount": "技能2效应因子7", "spell2: effectAmounts: Effect8Amount": "技能2效应因子8", "spell2: effectAmounts: Effect9Amount": "技能2效应因子9", "spell2: effectAmounts: Effect10Amount": "技能2效应因子10", "spell2: ammo: ammoRechargeTime": "技能2充能时间", "spell2: ammo: maxAmmo": "技能2最大充能数", "spell3: spellKey": "技能3热键", "spell3: name": "技能3名称", "spell3: abilityIconPath": "技能3图标路径", "spell3: abilityVideoPath": "技能3动画视频路径", "spell3: abilityVideoImagePath": "技能3动画预览图路径", "spell3: cost": "技能3消耗计算方式", "spell3: cooldown": "技能3冷却时间计算方式", "spell3: description": "技能3简述", "spell3: dynamicDescription": "技能3详细信息", "spell3: range": "技能3施法距离", "spell3: costCoefficients": "技能3施法资源系数", "spell3: cooldownCoefficients": "技能3冷却时间系数", "spell3: maxLevel": "技能3最大等级", "spell3: coefficients: coefficient1": "技能3系数1", "spell3: coefficients: coefficient2": "技能3系数2", "spell3: effectAmounts: Effect1Amount": "技能3效应因子1", "spell3: effectAmounts: Effect2Amount": "技能3效应因子2", "spell3: effectAmounts: Effect3Amount": "技能3效应因子3", "spell3: effectAmounts: Effect4Amount": "技能3效应因子4", "spell3: effectAmounts: Effect5Amount": "技能3效应因子5", "spell3: effectAmounts: Effect6Amount": "技能3效应因子6", "spell3: effectAmounts: Effect7Amount": "技能3效应因子7", "spell3: effectAmounts: Effect8Amount": "技能3效应因子8", "spell3: effectAmounts: Effect9Amount": "技能3效应因子9", "spell3: effectAmounts: Effect10Amount": "技能3效应因子10", "spell3: ammo: ammoRechargeTime": "技能3充能时间", "spell3: ammo: maxAmmo": "技能3最大充能数", "spell4: spellKey": "技能4热键", "spell4: name": "技能4名称", "spell4: abilityIconPath": "技能4图标路径", "spell4: abilityVideoPath": "技能4动画视频路径", "spell4: abilityVideoImagePath": "技能4动画预览图路径", "spell4: cost": "技能4消耗计算方式", "spell4: cooldown": "技能4冷却时间计算方式", "spell4: description": "技能4简述", "spell4: dynamicDescription": "技能4详细信息", "spell4: range": "技能4施法距离", "spell4: costCoefficients": "技能4施法资源系数", "spell4: cooldownCoefficients": "技能4冷却时间系数", "spell4: maxLevel": "技能4最大等级", "spell4: coefficients: coefficient1": "技能4系数1", "spell4: coefficients: coefficient2": "技能4系数2", "spell4: effectAmounts: Effect1Amount": "技能4效应因子1", "spell4: effectAmounts: Effect2Amount": "技能4效应因子2", "spell4: effectAmounts: Effect3Amount": "技能4效应因子3", "spell4: effectAmounts: Effect4Amount": "技能4效应因子4", "spell4: effectAmounts: Effect5Amount": "技能4效应因子5", "spell4: effectAmounts: Effect6Amount": "技能4效应因子6", "spell4: effectAmounts: Effect7Amount": "技能4效应因子7", "spell4: effectAmounts: Effect8Amount": "技能4效应因子8", "spell4: effectAmounts: Effect9Amount": "技能4效应因子9", "spell4: effectAmounts: Effect10Amount": "技能4效应因子10", "spell4: ammo: ammoRechargeTime": "技能4充能时间", "spell4: ammo: maxAmmo": "技能4最大充能数"}
    LoLChampions_header_keys = list(LoLChampions_header.keys())
    LoLChampions_data = {}
    damageTypes = {"kPhysical": "物理伤害", "kMagic": "魔法伤害", "kMixed": "混合伤害"}
    #damageTypes = {"kPhysical": "Physical", "kMagic": "Magic", "kMixed": "Mixed"}
    attackTypes = {"melee": "近战", "ranged": "远程"}
    for i in range(len(LoLChampions_header_keys)):
        key = LoLChampions_header_keys[i]
        LoLChampions_data[key] = []
    print("championId\tname\ttitle\talias")
    count = 0
    for i in sorted(LoLChampions.keys()):
        champion = LoLChampions[i]
        print("%s\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]))
        if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
            count += 1
        for j in range(len(LoLChampions_header_keys)):
            key = LoLChampions_header_keys[j]
            if j <= 9:
                LoLChampions_data[key].append(champion[key])
            elif j <= 13: #战略信息子键（`tacticalInfo`'s subkeys）
                if j == 12: #战略信息：伤害（`tacticalInfo: damageType`）
                    LoLChampions_data[key].append(damageTypes[champion["tacticalInfo"][key.split(": ")[1]]])
                elif j == 13: #战略信息：攻击方式（`tacticalInfo: attackType`）
                    LoLChampions_data[key].append(attackTypes[champion["tacticalInfo"][key.split(": ")[1]]])
                else:
                    LoLChampions_data[key].append(champion["tacticalInfo"][key.split(": ")[1]])
            elif j <= 18: #玩法雷达图子键（`playStyleInfo`'s subkeys）
                LoLChampions_data[key].append(champion["playstyleInfo"][key.split(": ")[1]])
            elif j <= 20: #英雄标签信息子键（`championTagInfo`'s subkeys）
                LoLChampions_data[key].append(champion["championTagInfo"][key.split(": ")[1]])
            elif j <= 26: #角色定位子键（`role`'s subkeys）
                if key.split(": ")[1] in champion["roles"]:
                    LoLChampions_data[key].append("√")
                else:
                    LoLChampions_data[key].append("")
            elif j <= 31: #被动技能子键（`passive`'s subkeys）
                LoLChampions_data[key].append(champion["passive"][key.split(": ")[1]])
            else: #技能相关键（Spell related keys）
                spell_index = int(key[5:6]) - 1
                if spell_index < len(champion["spells"]):
                    spell = champion["spells"][spell_index]
                    subkey_list = key.split(": ")[1:]
                    value = spell
                    for subkey in subkey_list:
                        value = value[subkey]
                    LoLChampions_data[key].append(value)
                else:
                    LoLChampions_data[key].append("")
    LoLChampions_statistics_output_order = [0, 1, 3, 2, 21, 22, 23, 24, 25, 26, 12, 10, 11, 13, 19, 20, 14, 15, 16, 17, 18, 4, 5, 6, 7, 8, 27, 33, 60, 87, 114]
    LoLChampions_data_organized = {}
    for i in LoLChampions_statistics_output_order:
        key = LoLChampions_header_keys[i]
        LoLChampions_data_organized[key] = LoLChampions_data[key]
    LoLChampions_df = pandas.DataFrame(data = LoLChampions_data_organized)
    LoLChampions_df = pandas.concat([pandas.DataFrame([LoLChampions_header])[LoLChampions_df.columns], LoLChampions_df], ignore_index = True)
    return LoLChampions_df

async def get_plugin_champions(connection):
    champion_summary = await (await connection.request("GET", "/lol-game-data/assets/v1/champion-summary.json")).json()
    championIds = [champion["id"] for champion in champion_summary]
    LoLChampion = []
    for i in range(len(championIds)):
        championId = championIds[i]
        champion_uri = f"/lol-game-data/assets/v1/champions/{championId}.json"
        champion = await (await connection.request("GET", champion_uri)).json() #插件从本地读取，因此一般不需要设置异常处理（Plugins are read locally, so exception handling isn't needed here）
        LoLChampion.append(champion)
        print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
        print("获取进度（Capturing process）：%d/%d" %(i + 1, len(championIds)))
    return LoLChampion

language_ddragon = {1: {"CODE": "ar_AE", "LANGUAGE (EN)": "Arabic (United Arab Emirates)", "LANGUAGE (ZH)": "阿拉伯语（阿拉伯联合酋长国）", "Applicable CDragon Data Patches": "9.20～10.1, 13.20+"}, 2: {"CODE": "cs_CZ", "LANGUAGE (EN)": "Czech (Czech Republic)", "LANGUAGE (ZH)": "捷克语（捷克共和国）", "Applicable CDragon Data Patches": "7.1+"}, 3: {"CODE": "el_GR", "LANGUAGE (EN)": "Greek (Greece)", "LANGUAGE (ZH)": "希腊语（希腊）", "Applicable CDragon Data Patches": "9.1+"}, 4: {"CODE": "pl_PL", "LANGUAGE (EN)": "Polish (Poland)", "LANGUAGE (ZH)": "波兰语（波兰）", "Applicable CDragon Data Patches": "9.1+"}, 5: {"CODE": "ro_RO", "LANGUAGE (EN)": "Romanian (Romania)", "LANGUAGE (ZH)": "罗马尼亚语（罗马尼亚）", "Applicable CDragon Data Patches": "9.1+"}, 6: {"CODE": "hu_HU", "LANGUAGE (EN)": "Hungarian (Hungary)", "LANGUAGE (ZH)": "匈牙利语（匈牙利）", "Applicable CDragon Data Patches": "9.1+"}, 7: {"CODE": "en_GB", "LANGUAGE (EN)": "English (United Kingdom)", "LANGUAGE (ZH)": "英语（英国）", "Applicable CDragon Data Patches": "9.1+"}, 8: {"CODE": "de_DE", "LANGUAGE (EN)": "German (Germany)", "LANGUAGE (ZH)": "德语（德国）", "Applicable CDragon Data Patches": "7.1+"}, 9: {"CODE": "es_ES", "LANGUAGE (EN)": "Spanish (Spain)", "LANGUAGE (ZH)": "西班牙语（西班牙）", "Applicable CDragon Data Patches": "9.1+"}, 10: {"CODE": "it_IT", "LANGUAGE (EN)": "Italian (Italy)", "LANGUAGE (ZH)": "意大利语（意大利）", "Applicable CDragon Data Patches": "9.1+"}, 11: {"CODE": "fr_FR", "LANGUAGE (EN)": "French (France)", "LANGUAGE (ZH)": "法语（法国）", "Applicable CDragon Data Patches": "9.1+"}, 12: {"CODE": "ja_JP", "LANGUAGE (EN)": "Japanese (Japan)", "LANGUAGE (ZH)": "日语（日本）", "Applicable CDragon Data Patches": "9.1+"}, 13: {"CODE": "ko_KR", "LANGUAGE (EN)": "Korean (Korea)", "LANGUAGE (ZH)": "朝鲜语（韩国）", "Applicable CDragon Data Patches": "9.7+"}, 14: {"CODE": "es_MX", "LANGUAGE (EN)": "Spanish (Mexico)", "LANGUAGE (ZH)": "西班牙语（墨西哥）", "Applicable CDragon Data Patches": "9.1+"}, 15: {"CODE": "es_AR", "LANGUAGE (EN)": "Spanish (Argentina)", "LANGUAGE (ZH)": "西班牙语（阿根廷）", "Applicable CDragon Data Patches": "9.7+"}, 16: {"CODE": "pt_BR", "LANGUAGE (EN)": "Portuguese (Brazil)", "LANGUAGE (ZH)": "葡萄牙语（巴西）", "Applicable CDragon Data Patches": "9.1+"}, 17: {"CODE": "en_US", "LANGUAGE (EN)": "English (United States)", "LANGUAGE (ZH)": "英语（美国）", "Applicable CDragon Data Patches": "9.1+"}, 18: {"CODE": "en_AU", "LANGUAGE (EN)": "English (Australia)", "LANGUAGE (ZH)": "英语（澳大利亚）", "Applicable CDragon Data Patches": "9.1+"}, 19: {"CODE": "ru_RU", "LANGUAGE (EN)": "Russian (Russia)", "LANGUAGE (ZH)": "俄语（俄罗斯）", "Applicable CDragon Data Patches": "9.1+"}, 20: {"CODE": "tr_TR", "LANGUAGE (EN)": "Turkish (Turkey)", "LANGUAGE (ZH)": "土耳其语（土耳其）", "Applicable CDragon Data Patches": "9.1+"}, 21: {"CODE": "ms_MY", "LANGUAGE (EN)": "Malay (Malaysia)", "LANGUAGE (ZH)": "马来语（马来西亚）", "Applicable CDragon Data Patches": ""}, 22: {"CODE": "en_PH", "LANGUAGE (EN)": "English (Republic of the Philippines)", "LANGUAGE (ZH)": "英语（菲律宾共和国）", "Applicable CDragon Data Patches": "10.5+"}, 23: {"CODE": "en_SG", "LANGUAGE (EN)": "English (Singapore)", "LANGUAGE (ZH)": "英语（新加坡）", "Applicable CDragon Data Patches": "10.5+"}, 24: {"CODE": "th_TH", "LANGUAGE (EN)": "Thai (Thailand)", "LANGUAGE (ZH)": "泰语（泰国）", "Applicable CDragon Data Patches": "9.7+"}, 25: {"CODE": "vn_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "9.7～13.9"}, 26: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "12.17+"}, 27: {"CODE": "id_ID", "LANGUAGE (EN)": "Indonesian (Indonesia)", "LANGUAGE (ZH)": "印度尼西亚语（印度尼西亚）", "Applicable CDragon Data Patches": ""}, 28: {"CODE": "zh_MY", "LANGUAGE (EN)": "Chinese (Malaysia)", "LANGUAGE (ZH)": "中文（马来西亚）", "Applicable CDragon Data Patches": "10.5+"}, 29: {"CODE": "zh_CN", "LANGUAGE (EN)": "Chinese (China)", "LANGUAGE (ZH)": "中文（中国）", "Applicable CDragon Data Patches": "9.7+"}, 30: {"CODE": "zh_TW", "LANGUAGE (EN)": "Chinese (Taiwan)", "LANGUAGE (ZH)": "中文（台湾）", "Applicable CDragon Data Patches": "9.7+"}}
language_cdragon = {}
for i in language_ddragon:
    if language_ddragon[i]["CODE"] == "en_US":
        language_cdragon[language_ddragon[i]["CODE"]] = "default" #在CommunityDragon数据库上，美服正式服的数据资源代码是default，而不是小写的en_US（The code for English (US) data resources on CommunityDragon database is "default" instead of the lowercase of "en_US"）
    else:
        language_cdragon[language_ddragon[i]["CODE"]] = language_ddragon[i]["CODE"].lower()
print('请选择英雄数据来源（输入“0”以退出程序）：\nPlease select the champion data source (submit "0" to exit):\n1\tLCU API\n2\tDataDragon\n3\tCommunityDragon')
source = input()
if source != "" and (source[0] == "0" or source[0] == "2" or source[0] == "3"):
    if source[0] == "0":
        exit()
    print("请选择输出语言【默认为中文（中国）】：\nPlease select a language for output (the default option is zh_CN):")
    language_dict = {"No.": list(language_ddragon.keys()), "CODE": list(map(lambda x: x["CODE"], language_ddragon.values())), "LANGUAGE": list(map(lambda x: x["LANGUAGE (EN)"], language_ddragon.values())), "语言": list(map(lambda x: x["LANGUAGE (ZH)"], language_ddragon.values())), "Applicable CDragon Data Patches": list(map(lambda x: x["Applicable CDragon Data Patches"], language_ddragon.values()))}
    language_df = pandas.DataFrame(language_dict)
    print(format_df(language_df)[0])
    while True:
        language_option = input()
        if language_option == "" or language_option in [str(i) for i in range(1, 31)]:
            if language_option == "":
                language_option = "29"
            language_code = language_ddragon[int(language_option)]["CODE"]
            #下面声明一些数据资源的地址（The following code declare some data resources' URLs）
            patches_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            #下面声明离线数据资源的默认地址（The following code declare the default paths of offline data resources）
            patches_local_default = "离线数据（Offline Data）\\versions.json"
            cdragon_champion_local_default = "离线数据（Offline Data）\\cdragon\\pbe\\plugins\\rcp-be-lol-game-data\\global\\%s\\v1\\champions\\" %language_cdragon[language_code]
            ddragon_champion_local_default = "离线数据（Offline Data）\\ddragon\\%s\\champion.json" %language_code
            break
        else:
            print("语言选项输入错误！请重新输入：\nERROR input of language option! Please try again:")
    if source[0] == "2":
        LoLChampions_df = sort_ddragon_champions()
        count = len(LoLChampions_df) - 2
        while True:
            try:
                with pandas.ExcelWriter(path = "available-bots.xlsx", mode = "a", if_sheet_exists = "replace") as writer:
                    LoLChampions_df.to_excel(excel_writer = writer, sheet_name = "Sheet3")
            except PermissionError:
                print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                input()
            except FileNotFoundError:
                with open(path = "available-bots.xlsx") as writer:
                    LoLChampions_df.to_excel(excel_writer = writer, sheet_name = "Sheet3")
                break
            else:
                print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
                break
        input()
        exit() #执行到此，程序结束（Here the program terminates）
    else:
        LoLChampion = get_cdragon_champions()
        LoLChampions_df = sort_cdragon_champions(LoLChampion)
        count = len(LoLChampions_df) - 2
        while True:
            try:
                with pandas.ExcelWriter(path = "available-bots.xlsx", mode = "a", if_sheet_exists = "replace") as writer:
                    LoLChampions_df.to_excel(excel_writer = writer, sheet_name = "Sheet3")
            except PermissionError:
                print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                input()
            except FileNotFoundError:
                with open(path = "available-bots.xlsx") as writer:
                    LoLChampions_df.to_excel(excel_writer = writer, sheet_name = "Sheet3")
                break
            else:
                print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
                break
        input()
        exit() #执行到此，程序结束（Here the program terminates）

connector = Connector()

async def get_summoner_data(connection):
    data = await connection.request('GET', '/lol-summoner/v1/current-summoner')
    global summoner
    summoner = await data.json()
    print("displayName:    %s" %(summoner["gameName"] + "#" + summoner["tagLine"]))
    print("summonerId:     %s" %(summoner["summonerId"]))
    print("puuid:          %s" %(summoner["puuid"]))
    print("-")


#-----------------------------------------------------------------------------
#  lockfile
#-----------------------------------------------------------------------------
async def update_lockfile(connection):
    import os
    path = os.path.join(connection.installation_path.encode('gb18030').decode('utf-8'), 'lockfile')
    if os.path.isfile(path):
        file = open(path, 'w+')
        text = "LeagueClient:%d:%d:%s:%s" %(connection.pid, connection.port, connection.auth_key, connection.protocols[0])
        file.write(text)
        file.close()
    return None

async def get_lockfile(connection):
    import os
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
# 创建训练模式 5V5 自定义房间（Create a Practice Tool lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    custom = {
        "queueId": 3140,
        "isCustom": True,
        "customGameLobby": {
            "lobbyName": "可用电脑英雄测试（程序结束前请勿退出）",
            "lobbyPassword": "",
            "configuration": {
                "mapId": 11,
                "gameMode": "PRACTICETOOL",
                "gameMutator": "",
                "mutators": {
                    "id": 1
                },
                "spectatorPolicy": "AllAllowed",
                "teamSize": 5,
                "maxPlayerCount": 0,
                "gameServerRegion": "",
                "spectatorDelayEnabled": False,
                "hidePublicly": False
            }
        }
    }
    response = await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)

#-----------------------------------------------------------------------------
# 统计英雄数量（Count champions）
#-----------------------------------------------------------------------------
async def count_champions(connection):
    print("请选择英雄数据类型：\nPlease a champion data type:\n1\t个人所有（Personal inventory）\n2\t插件（Plugins）")
    while True:
        data_type = input()
        if data_type == "":
            continue
        elif data_type[0] == "0":
            return 1
        elif data_type[0] == "1":
            LoLChampion = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %summoner["summonerId"])).json()
            break
        elif data_type[0] == "2":
            LoLChampion = await get_plugin_champions(connection)
            break
        else:
            print("您的输入有误，请重新输入！\nERROR input! Please try again!")
    LoLChampions = {}
    print("请选择统计类型：\nPlease select which type of champions to count:\n1\t所有英雄（All champions）\n2\t所有电脑英雄（All bot champions）\n3\t当前房间可用电脑英雄（Available bot champions in this lobby）")
    while True: #分类讨论确定`LoLChampions`（Discuss and determine `LoLChampions`）
        mode = input()
        if mode == "":
            continue
        elif mode[0] == "0":
            return 2
        elif mode[0] == "1":
            for champion in LoLChampion:
                LoLChampions[champion["id"]] = champion
            sheet_name = "Sheet3"
            break
        elif mode[0] == "2":
            print("正在统计具有电脑模型的英雄……请勿退出房间！\nCounting botEnabled champions ... Please don't exit the lobby!\n")
            await create_custom_lobby(connection)
            print("championId\tname\ttitle\talias")
            count = 0
            for champion in LoLChampion:
                botUuid = str(uuid.uuid4())
                bot = {"championId": champion["id"], "botDifficulty": "RSINTERMEDIATE", "teamId": "200", "position": "TOP", "botUuid": botUuid}
                response = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
                if response == None: #这里认为当返回内容为空时，电脑玩家被添加（Here the principle is, once the response body is empty, the bot player is definitely added）
                    # start = time.time()
                    LoLChampions[champion["id"]] = champion
                    print("%d\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]))
                    if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                        count += 1
                    #接下来反复获取房间信息，直到从房间信息中获取到添加的电脑玩家信息（Next, repeatedly get the lobby information, until the added bot information can be found）
                    lobby = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                    while not champion["id"] in list(map(lambda x: x["botChampionId"], lobby["gameConfig"]["customTeam200"])):
                        lobby = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                    # end = time.time()
                    # cost = end - start
                    # print("从添加电脑玩家到房间信息刷新所花费的时间【Time interval (seconds) between a bot is added and lobby information is refreshed】：%f" %(cost))
                    botId_uuid_dict = {bot["botUuid"]: bot["botId"] for bot in lobby["gameConfig"]["customTeam200"]}
                    for bot in lobby["gameConfig"]["customTeam200"]: #从25.16版本开始，电脑玩家通用唯一识别码不再能由用户决定。因此，过往通过电脑玩家通用唯一识别码来判断电脑是否被添加的办法失效了（Since Patch 25.16, botUuid can never be decided by the user. Therefore, the original way to judge by botUuid whether a bot player is added no longer works）
                        if bot["botChampionId"] == champion["id"]:
                            botUuid = bot["botUuid"]
                            break
                    else:
                        botUuid = lobby["gameConfig"]["customTeam200"][0]["botUuid"] #保护机制，防止下面在引用botUuid时出现问题（A protection from an error occurring when the program refers to `botUuid` below）
                    response = await (await connection.request("DELETE", "/lol-lobby/v1/lobby/custom/bots/%s/%s/200" %(botId_uuid_dict[botUuid], botUuid))).json()
            print("\n统计完毕，共%d名英雄。\nCount finished! There're %d champions in total." %(count, count))
            sheet_name = "Sheet2"
            break
        elif mode[0] == "3":
            lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
            if "errorCode" in lobby_information and lobby_information["message"] == "LOBBY_NOT_FOUND":
                print("请确保您正在房间内！程序即将退出！\nPlease make sure you're in a lobby! The program will exit soon!")
                time.sleep(3)
                exit()
            bots_enabled = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/bots-enabled")).json()
            if not bots_enabled:
                print("该房间无可用电脑玩家。请输入任意键退出。\nThere're no available bot champions in this lobby. Please press any key to exit.")
                input()
                return 0
            available_bots = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")).json()
            available_botIds = list(map(lambda x: x["id"], available_bots))
            for champion in LoLChampion:
                if champion["id"] in available_botIds:
                    LoLChampions[champion["id"]] = champion
            sheet_name = "Sheet1"
            break
        else:
            print("您的输入有误，请重新输入！\nERROR input! Please try again!")
    #下面按照程序需求对数据资源进行一定的整理（The following code sort out the data resource according to the program's need）
    if mode[0] == "1" or mode[0] == "3":
        print("championId\tname\ttitle\talias")
        count = 0
    else:
        print("正在整理数据……\nSorting out the data ...")
    if data_type[0] == "1":
        LoLChampions_header = {"active": "可用性", "alias": "英雄代号", "banVoPath": "禁用台词路径", "baseLoadScreenPath": "加载界面图像路径", "baseSplashPath": "英雄封面路径", "botEnabled": "电脑模型激活情况", "chooseVoPath": "锁定台词路径", "disabledQueues": "禁用队列", "freeToPlay": "允许免费使用", "id": "英雄序号", "isVisibleInClient": "藏品可见性", "name": "称号", "purchased": "购买时间戳", "rankedPlayEnabled": "取得排位许可", "squarePortraitPath": "方格头像路径", "stingerSfxPath": "锁定音效路径", "title": "名称", "purchaseDate": "购买日期", "ownership: loyaltyReward": "获取方式：排位赛段奖励", "ownership: owned": "已拥有", "ownership: xboxGPReward": "获取方式：Xbox Game Pass奖励", "ownership: rental: endDate": "租借截止时间戳", "ownership: rental: purchaseDate": "租借时间戳", "ownership: rental: rented": "已租借", "ownership: rented: winCountRemaining": "租借可用胜场数", "ownership: rental: endTime": "租借截止日期", "ownership: rental: purchaseTime": "租借日期", "role: assassin": "角色定位：刺客", "role: fighter": "角色定位：战士", "role: mage": "角色定位：法师", "role: marksman": "角色定位：射手", "role: support": "角色定位：辅助", "role: tank": "角色定位：坦克", "tacticalInfo: damageType": "战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】", "tacticalInfo: difficulty": "战略信息：难度（英雄的使用难度）", "tacticalInfo: style": "战略信息：风格【表明英雄的伤害输出方式的倾向（普攻vs技能）】", "passive: description": "被动技能简介", "passive: name": "被动技能名称", "spell1: description": "技能1简介", "spell1: name": "技能1名称", "spell2: description": "技能2简介", "spell2: name": "技能2名称", "spell3: description": "技能3简介", "spell3: name": "技能3名称", "spell4: description": "技能4简介", "spell4: name": "技能4名称", "recommendedPosition: TOP": "推荐路线：上路", "recommendedPosition: JUNGLE": "推荐路线：打野", "recommendedPosition: MIDDLE": "推荐路线：中路", "recommendedPosition: BOTTOM": "推荐路线：下路", "recommendedPosition: UTILITY": "推荐路线：辅助"}
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
            if mode[0] == "1" or mode[0] == "3":
                print("%d\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]))
                if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                    count += 1
            for j in range(len(LoLChampions_header_keys)):
                key = LoLChampions_header_keys[j]
                if j <= 17:
                    if j == 17: #购买日期（`purchased`）
                        if champion["purchased"] == 0:
                            LoLChampions_data[key].append("")
                        else:
                            try:
                                LoLChampions_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion["purchased"] // 1000)))
                            except OSError: #出现了购买时间戳为18446744073709550616的英雄（There's a champion with the purchased timestamp 18446744073709550616）
                                LoLChampions_data[key].append("")
                    else:
                        LoLChampions_data[key].append(champion[key])
                elif j <= 26: #拥有权子键（`ownership`'s subkeys）
                    if j <= 20:
                        LoLChampions_data[key].append(champion["ownership"][key.split(": ")[1]])
                    else:
                        if j == 25 or j == 26:
                            if champion["ownership"]["rental"][key.split(": ")[2].replace("Time", "Date")] == 0:
                                LoLChampions_data[key].append("")
                            else:
                                try:
                                    LoLChampions_data[key].append(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion["ownership"]["rental"][key.split(": ")[2].replace("Time", "Date")] // 1000)))
                                except OSError: #出现了租借时间戳为18446744073709550616的英雄（There's a champion with the rented timestamp 18446744073709550616）
                                    LoLChampions_data[key].append("")
                        else:
                            LoLChampions_data[key].append(champion["ownership"]["rental"][key.split(": ")[2]])
                elif j <= 32: #角色定位相关键（Role related keys）
                    LoLChampions_data[key].append(key.split(": ")[1] in champion["roles"])
                elif j <= 35: #战略信息子键（`tacticalInfo`'s subkeys）
                    if j == 33: #战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】（`tacticalInfo: damageType`）
                        LoLChampions_data[key].append(damageTypes[champion["tacticalInfo"][key.split(": ")[1]]])
                    else:
                        LoLChampions_data[key].append(champion["tacticalInfo"][key.split(": ")[1]])
                elif j <= 37: #被动技能子键（`passive`'s subkeys）
                    LoLChampions_data[key].append(champion["passive"][key.split(": ")[1]])
                elif j <= 45: #技能相关键（Spell related keys）
                    spell_index = int(key[5:6]) - 1
                    if spell_index < len(champion["spells"]):
                        LoLChampions_data[key].append(champion["spells"][spell_index][key.split(": ")[1]])
                    else:
                        LoLChampions_data[key].append("")
                else:
                    if champion["id"] == -1:
                        LoLChampions_data[key].append(False)
                    elif key.split(": ")[1] in recommended_position_for_champion[str(champion["id"])]["recommendedPositions"]:
                        LoLChampions_data[key].append(True)
                    else:
                        LoLChampions_data[key].append(False)
        LoLChampions_statistics_output_order = [9, 11, 16, 1, 10, 5, 27, 28, 29, 30, 31, 32, 46, 47, 48, 49, 50, 33, 35, 34, 19, 17, 18, 20, 8, 23, 26, 25, 24, 13, 7, 14, 3, 4, 15, 6, 2, 37, 39, 41, 43, 45]
        LoLChampions_data_organized = {}
        for i in LoLChampions_statistics_output_order:
            key = LoLChampions_header_keys[i]
            LoLChampions_data_organized[key] = LoLChampions_data[key]
        LoLChampions_df = pandas.DataFrame(data = LoLChampions_data_organized)
        print("正在优化逻辑值显示……\nOptimizing the display of boolean values ...")
        for column in LoLChampions_df:
            if LoLChampions_df[column].dtype == "bool":
                LoLChampions_df[column] = LoLChampions_df[column].astype(str)
                for i in range(len(LoLChampions_df)):
                    LoLChampions_df.loc[i, column] = "√" if LoLChampions_df[column][i] == "True" else ""
        print("逻辑值显示优化完成！\nBoolean value display optimization finished!")
        LoLChampions_df = pandas.concat([pandas.DataFrame([LoLChampions_header])[LoLChampions_df.columns], LoLChampions_df], ignore_index = True)
    elif data_type[0] == "2":
        #下面按照程序需求对数据资源进行一定的整理（The following code sort out the data resource according to the program's need）
        LoLChampions_header = {"id": "英雄序号", "name": "称号", "alias": "英雄代号", "title": "名称", "shortBio": "背景简介", "isVisibleInClient": "客户端可见性", "squarePortraitPath": "方格头像路径", "stingerSfxPath": "锁定音效路径", "chooseVoPath": "锁定台词路径", "banVoPath": "禁用台词路径", "recommendedItemDefaults": "默认推荐装备序号列表", "tacticalInfo: style": "战略信息：风格【表明英雄的伤害输出方式的倾向（普攻vs技能）】", "tacticalInfo: difficulty": "战略信息：难度（英雄的使用难度）", "tacticalInfo: damageType": "战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】", "tacticalInfo: attackType": "战略信息：攻击方式", "playStyleInfo: damage": "玩法雷达图：伤害（用来对敌方英雄造成伤害的英雄技能）得分", "playStyleInfo: durability": "玩法雷达图：强韧（用来吸收来自敌方英雄伤害的英雄技能）得分", "playStyleInfo: crowdControl": "玩法雷达图：控制（用来对敌方英雄施加诸如减速和晕眩的有害效果的英雄技能）得分", "playStyleInfo: mobility": "玩法雷达图：机动（通过使用闪现或位移来快速在地图四处移动的英雄技能）得分", "playStyleInfo: utility": "玩法雷达图：功能（用来对友军提供护盾、治疗或移动速度等有益效果的英雄技能）得分", "championTagInfo: championTagPrimary": "英雄标签信息：第一标签", "championTagInfo: championTagSecondary": "英雄标签信息：第二标签", "role: assassin": "角色定位：刺客", "role: fighter": "角色定位：战士", "role: mage": "角色定位：法师", "role: marksman": "角色定位：射手", "role: support": "角色定位：辅助", "role: tank": "角色定位：坦克", "passive: name": "被动技能名称", "passive: abilityIconPath": "被动技能图标路径", "passive: abilityVideoPath": "被动技能动画视频路径", "passive: abilityVideoImagePath": "被动技能动画预览图路径", "passive: description": "被动技能简述", "spell1: spellKey": "技能1热键", "spell1: name": "技能1名称", "spell1: abilityIconPath": "技能1图标路径", "spell1: abilityVideoPath": "技能1动画视频路径", "spell1: abilityVideoImagePath": "技能1动画预览图路径", "spell1: cost": "技能1消耗计算方式", "spell1: cooldown": "技能1冷却时间计算方式", "spell1: description": "技能1简述", "spell1: dynamicDescription": "技能1详细信息", "spell1: range": "技能1施法距离", "spell1: costCoefficients": "技能1施法资源系数", "spell1: cooldownCoefficients": "技能1冷却时间系数", "spell1: maxLevel": "技能1最大等级", "spell1: coefficients: coefficient1": "技能1系数1", "spell1: coefficients: coefficient2": "技能1系数2", "spell1: effectAmounts: Effect1Amount": "技能1效应因子1", "spell1: effectAmounts: Effect2Amount": "技能1效应因子2", "spell1: effectAmounts: Effect3Amount": "技能1效应因子3", "spell1: effectAmounts: Effect4Amount": "技能1效应因子4", "spell1: effectAmounts: Effect5Amount": "技能1效应因子5", "spell1: effectAmounts: Effect6Amount": "技能1效应因子6", "spell1: effectAmounts: Effect7Amount": "技能1效应因子7", "spell1: effectAmounts: Effect8Amount": "技能1效应因子8", "spell1: effectAmounts: Effect9Amount": "技能1效应因子9", "spell1: effectAmounts: Effect10Amount": "技能1效应因子10", "spell1: ammo: ammoRechargeTime": "技能1充能时间", "spell1: ammo: maxAmmo": "技能1最大充能数", "spell2: spellKey": "技能2热键", "spell2: name": "技能2名称", "spell2: abilityIconPath": "技能2图标路径", "spell2: abilityVideoPath": "技能2动画视频路径", "spell2: abilityVideoImagePath": "技能2动画预览图路径", "spell2: cost": "技能2消耗计算方式", "spell2: cooldown": "技能2冷却时间计算方式", "spell2: description": "技能2简述", "spell2: dynamicDescription": "技能2详细信息", "spell2: range": "技能2施法距离", "spell2: costCoefficients": "技能2施法资源系数", "spell2: cooldownCoefficients": "技能2冷却时间系数", "spell2: maxLevel": "技能2最大等级", "spell2: coefficients: coefficient1": "技能2系数1", "spell2: coefficients: coefficient2": "技能2系数2", "spell2: effectAmounts: Effect1Amount": "技能2效应因子1", "spell2: effectAmounts: Effect2Amount": "技能2效应因子2", "spell2: effectAmounts: Effect3Amount": "技能2效应因子3", "spell2: effectAmounts: Effect4Amount": "技能2效应因子4", "spell2: effectAmounts: Effect5Amount": "技能2效应因子5", "spell2: effectAmounts: Effect6Amount": "技能2效应因子6", "spell2: effectAmounts: Effect7Amount": "技能2效应因子7", "spell2: effectAmounts: Effect8Amount": "技能2效应因子8", "spell2: effectAmounts: Effect9Amount": "技能2效应因子9", "spell2: effectAmounts: Effect10Amount": "技能2效应因子10", "spell2: ammo: ammoRechargeTime": "技能2充能时间", "spell2: ammo: maxAmmo": "技能2最大充能数", "spell3: spellKey": "技能3热键", "spell3: name": "技能3名称", "spell3: abilityIconPath": "技能3图标路径", "spell3: abilityVideoPath": "技能3动画视频路径", "spell3: abilityVideoImagePath": "技能3动画预览图路径", "spell3: cost": "技能3消耗计算方式", "spell3: cooldown": "技能3冷却时间计算方式", "spell3: description": "技能3简述", "spell3: dynamicDescription": "技能3详细信息", "spell3: range": "技能3施法距离", "spell3: costCoefficients": "技能3施法资源系数", "spell3: cooldownCoefficients": "技能3冷却时间系数", "spell3: maxLevel": "技能3最大等级", "spell3: coefficients: coefficient1": "技能3系数1", "spell3: coefficients: coefficient2": "技能3系数2", "spell3: effectAmounts: Effect1Amount": "技能3效应因子1", "spell3: effectAmounts: Effect2Amount": "技能3效应因子2", "spell3: effectAmounts: Effect3Amount": "技能3效应因子3", "spell3: effectAmounts: Effect4Amount": "技能3效应因子4", "spell3: effectAmounts: Effect5Amount": "技能3效应因子5", "spell3: effectAmounts: Effect6Amount": "技能3效应因子6", "spell3: effectAmounts: Effect7Amount": "技能3效应因子7", "spell3: effectAmounts: Effect8Amount": "技能3效应因子8", "spell3: effectAmounts: Effect9Amount": "技能3效应因子9", "spell3: effectAmounts: Effect10Amount": "技能3效应因子10", "spell3: ammo: ammoRechargeTime": "技能3充能时间", "spell3: ammo: maxAmmo": "技能3最大充能数", "spell4: spellKey": "技能4热键", "spell4: name": "技能4名称", "spell4: abilityIconPath": "技能4图标路径", "spell4: abilityVideoPath": "技能4动画视频路径", "spell4: abilityVideoImagePath": "技能4动画预览图路径", "spell4: cost": "技能4消耗计算方式", "spell4: cooldown": "技能4冷却时间计算方式", "spell4: description": "技能4简述", "spell4: dynamicDescription": "技能4详细信息", "spell4: range": "技能4施法距离", "spell4: costCoefficients": "技能4施法资源系数", "spell4: cooldownCoefficients": "技能4冷却时间系数", "spell4: maxLevel": "技能4最大等级", "spell4: coefficients: coefficient1": "技能4系数1", "spell4: coefficients: coefficient2": "技能4系数2", "spell4: effectAmounts: Effect1Amount": "技能4效应因子1", "spell4: effectAmounts: Effect2Amount": "技能4效应因子2", "spell4: effectAmounts: Effect3Amount": "技能4效应因子3", "spell4: effectAmounts: Effect4Amount": "技能4效应因子4", "spell4: effectAmounts: Effect5Amount": "技能4效应因子5", "spell4: effectAmounts: Effect6Amount": "技能4效应因子6", "spell4: effectAmounts: Effect7Amount": "技能4效应因子7", "spell4: effectAmounts: Effect8Amount": "技能4效应因子8", "spell4: effectAmounts: Effect9Amount": "技能4效应因子9", "spell4: effectAmounts: Effect10Amount": "技能4效应因子10", "spell4: ammo: ammoRechargeTime": "技能4充能时间", "spell4: ammo: maxAmmo": "技能4最大充能数"}
        LoLChampions_header_keys = list(LoLChampions_header.keys())
        LoLChampions_data = {}
        damageTypes = {"kPhysical": "物理伤害", "kMagic": "魔法伤害", "kMixed": "混合伤害"}
        #damageTypes = {"kPhysical": "Physical", "kMagic": "Magic", "kMixed": "Mixed"}
        attackTypes = {"melee": "近战", "ranged": "远程"}
        for i in range(len(LoLChampions_header_keys)):
            key = LoLChampions_header_keys[i]
            LoLChampions_data[key] = []
        count = 0
        for i in sorted(LoLChampions.keys()):
            champion = LoLChampions[i]
            if mode[0] == "1" or mode[0] == "3":
                print("%s\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]))
                if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                    count += 1
            for j in range(len(LoLChampions_header_keys)):
                key = LoLChampions_header_keys[j]
                if j <= 10:
                    LoLChampions_data[key].append(champion[key])
                elif j <= 14: #战略信息子键（`tacticalInfo`'s subkeys）
                    if j == 13: #战略信息：伤害（`tacticalInfo: damageType`）
                        LoLChampions_data[key].append(damageTypes[champion["tacticalInfo"][key.split(": ")[1]]])
                    elif j == 14: #战略信息：攻击方式（`tacticalInfo: attackType`）
                        LoLChampions_data[key].append(attackTypes[champion["tacticalInfo"][key.split(": ")[1]]])
                    else:
                        LoLChampions_data[key].append(champion["tacticalInfo"][key.split(": ")[1]])
                elif j <= 19: #玩法雷达图子键（`playStyleInfo`'s subkeys）
                    LoLChampions_data[key].append(champion["playstyleInfo"][key.split(": ")[1]])
                elif j <= 21: #英雄标签信息子键（`championTagInfo`'s subkeys）
                    LoLChampions_data[key].append(champion["championTagInfo"][key.split(": ")[1]])
                elif j <= 27: #角色定位子键（`role`'s subkeys）
                    if key.split(": ")[1] in champion["roles"]:
                        LoLChampions_data[key].append("√")
                    else:
                        LoLChampions_data[key].append("")
                elif j <= 32: #被动技能子键（`passive`'s subkeys）
                    LoLChampions_data[key].append(champion["passive"][key.split(": ")[1]])
                else: #技能相关键（Spell related keys）
                    spell_index = int(key[5:6]) - 1
                    if spell_index < len(champion["spells"]):
                        spell = champion["spells"][spell_index]
                        subkey_list = key.split(": ")[1:]
                        value = spell
                        for subkey in subkey_list:
                            value = value[subkey]
                        LoLChampions_data[key].append(value)
                    else:
                        LoLChampions_data[key].append("")
        LoLChampions_statistics_output_order = [0, 1, 3, 2, 5, 22, 23, 24, 25, 26, 27, 13, 11, 12, 14, 20, 21, 15, 16, 17, 18, 19, 4, 6, 7, 8, 9, 28, 34, 61, 88, 115]
        LoLChampions_data_organized = {}
        for i in LoLChampions_statistics_output_order:
            key = LoLChampions_header_keys[i]
            LoLChampions_data_organized[key] = LoLChampions_data[key]
        LoLChampions_df = pandas.DataFrame(data = LoLChampions_data_organized)
        print("正在优化逻辑值显示……\nOptimizing the display of boolean values ...")
        for column in LoLChampions_df:
            if LoLChampions_df[column].dtype == "bool":
                LoLChampions_df[column] = LoLChampions_df[column].astype(str)
                for i in range(len(LoLChampions_df)):
                    LoLChampions_df.loc[i, column] = "√" if LoLChampions_df[column][i] == "True" else ""
        print("逻辑值显示优化完成！\nBoolean value display optimization finished!")
        LoLChampions_df = pandas.concat([pandas.DataFrame([LoLChampions_header])[LoLChampions_df.columns], LoLChampions_df], ignore_index = True)
    while True:
        try:
            with pandas.ExcelWriter(path = "available-bots.xlsx", mode = "a", if_sheet_exists = "replace") as writer:
                LoLChampions_df.to_excel(excel_writer = writer, sheet_name = sheet_name)
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
            input()
        except FileNotFoundError:
            with open(path = "available-bots.xlsx") as writer:
                LoLChampions_df.to_excel(excel_writer = writer, sheet_name = sheet_name)
            break
        else:
            if mode[0] == "1" or mode[0] == "3":
                print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
            else:
                print("英雄数据导出完成！请输入任意键退出。\nChampion data exported! Please press any key to exit.")
            break
    input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await count_champions(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
