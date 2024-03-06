from lcu_driver import Connector
import copy, os, unicodedata, shutil, pandas, requests, time, json, re, pyperclip
from urllib.parse import quote, unquote
from wcwidth import wcswidth
import matplotlib.pyplot as plt

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

error_header = {"errorCode": "异常代码", "httpStatus": "HTTP状态码", "implementationDetails": "细节", "message": "消息"}
error_header_keys = list(error_header.keys())
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
# 查找最近一起并肩作战的召唤师并给出统计信息（Find recently played summoners and give statistics of it）
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
        print("第1个版本字符串不合法！请输入用半角句号连接的正整数，如13.15.1、10.10.3216176。\nThe first patch variable is illegal! Please pass the integers concatenated by dot, such as 13.15.1 and 10.10.3216176.")
        return 1
    try:
        lst2 = list(map(int, lst2))
    except ValueError:
        print("第2个版本字符串不合法！请输入用半角句号连接的正整数，如13.15.1、10.10.3216176。\nThe second patch variable is illegal! Please pass the integers concatenated by dot, such as 13.15.1 and 10.10.3216176.")
        return 1
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
        print("该版本为美测服最新版本，暂未收录在DataDragon数据库中。该函数将返回正式服的最新版本。\nThis version is the latest version on PBE and isn't temporarily archived in DataDragon database. This function will return the latest Live version.")
        return patchList[0]

async def search_recent_players(connection):
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    print("请选择召唤师技能和装备的输出语言【默认为中文（中国）】：\nPlease select a language to output the summoner spells and items (the default option is zh_CN):") #本来考虑把可用CDragon数据版本放在第三列，但是后来发现表头名字太长了，索性放在最后了（I had considered putting "Applicable CDragon Data Patches" at the third column, but then found the header was too long. So I put it at the last column）
    language_ddragon = {1: {"CODE": "cs_CZ", "LANGUAGE (EN)": "Czech (Czech Republic)", "LANGUAGE (ZH)": "捷克语（捷克共和国）", "Applicable CDragon Data Patches": "7.1+"}, 2: {"CODE": "el_GR", "LANGUAGE (EN)": "Greek (Greece)", "LANGUAGE (ZH)": "希腊语（希腊）", "Applicable CDragon Data Patches": "9.1+"}, 3: {"CODE": "pl_PL", "LANGUAGE (EN)": "Polish (Poland)", "LANGUAGE (ZH)": "波兰语（波兰）", "Applicable CDragon Data Patches": "9.1+"}, 4: {"CODE": "ro_RO", "LANGUAGE (EN)": "Romanian (Romania)", "LANGUAGE (ZH)": "罗马尼亚语（罗马尼亚）", "Applicable CDragon Data Patches": "9.1+"}, 5: {"CODE": "hu_HU", "LANGUAGE (EN)": "Hungarian (Hungary)", "LANGUAGE (ZH)": "匈牙利语（匈牙利）", "Applicable CDragon Data Patches": "9.1+"}, 6: {"CODE": "en_GB", "LANGUAGE (EN)": "English (United Kingdom)", "LANGUAGE (ZH)": "英语（英国）", "Applicable CDragon Data Patches": "9.1+"}, 7: {"CODE": "de_DE", "LANGUAGE (EN)": "German (Germany)", "LANGUAGE (ZH)": "德语（德国）", "Applicable CDragon Data Patches": "7.1+"}, 8: {"CODE": "es_ES", "LANGUAGE (EN)": "Spanish (Spain)", "LANGUAGE (ZH)": "西班牙语（西班牙）", "Applicable CDragon Data Patches": "9.1+"}, 9: {"CODE": "it_IT", "LANGUAGE (EN)": "Italian (Italy)", "LANGUAGE (ZH)": "意大利语（意大利）", "Applicable CDragon Data Patches": "9.1+"}, 10: {"CODE": "fr_FR", "LANGUAGE (EN)": "French (France)", "LANGUAGE (ZH)": "法语（法国）", "Applicable CDragon Data Patches": "9.1+"}, 11: {"CODE": "ja_JP", "LANGUAGE (EN)": "Japanese (Japan)", "LANGUAGE (ZH)": "日语（日本）", "Applicable CDragon Data Patches": "9.1+"}, 12: {"CODE": "ko_KR", "LANGUAGE (EN)": "Korean (Korea)", "LANGUAGE (ZH)": "朝鲜语（韩国）", "Applicable CDragon Data Patches": "9.7+"}, 13: {"CODE": "es_MX", "LANGUAGE (EN)": "Spanish (Mexico)", "LANGUAGE (ZH)": "西班牙语（墨西哥）", "Applicable CDragon Data Patches": "9.1+"}, 14: {"CODE": "es_AR", "LANGUAGE (EN)": "Spanish (Argentina)", "LANGUAGE (ZH)": "西班牙语（阿根廷）", "Applicable CDragon Data Patches": "9.7+"}, 15: {"CODE": "pt_BR", "LANGUAGE (EN)": "Portuguese (Brazil)", "LANGUAGE (ZH)": "葡萄牙语（巴西）", "Applicable CDragon Data Patches": "9.1+"}, 16: {"CODE": "en_US", "LANGUAGE (EN)": "English (United States)", "LANGUAGE (ZH)": "英语（美国）", "Applicable CDragon Data Patches": "9.1+"}, 17: {"CODE": "en_AU", "LANGUAGE (EN)": "English (Australia)", "LANGUAGE (ZH)": "英语（澳大利亚）", "Applicable CDragon Data Patches": "9.1+"}, 18: {"CODE": "ru_RU", "LANGUAGE (EN)": "Russian (Russia)", "LANGUAGE (ZH)": "俄语（俄罗斯）", "Applicable CDragon Data Patches": "9.1+"}, 19: {"CODE": "tr_TR", "LANGUAGE (EN)": "Turkish (Turkey)", "LANGUAGE (ZH)": "土耳其语（土耳其）", "Applicable CDragon Data Patches": "9.1+"}, 20: {"CODE": "ms_MY", "LANGUAGE (EN)": "Malay (Malaysia)", "LANGUAGE (ZH)": "马来语（马来西亚）", "Applicable CDragon Data Patches": ""}, 21: {"CODE": "en_PH", "LANGUAGE (EN)": "English (Republic of the Philippines)", "LANGUAGE (ZH)": "英语（菲律宾共和国）", "Applicable CDragon Data Patches": "10.5+"}, 22: {"CODE": "en_SG", "LANGUAGE (EN)": "English (Singapore)", "LANGUAGE (ZH)": "英语（新加坡）", "Applicable CDragon Data Patches": "10.5+"}, 23: {"CODE": "th_TH", "LANGUAGE (EN)": "Thai (Thailand)", "LANGUAGE (ZH)": "泰语（泰国）", "Applicable CDragon Data Patches": "9.7+"}, 24: {"CODE": "vn_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "9.7～13.9"}, 25: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "12.17+"}, 26: {"CODE": "id_ID", "LANGUAGE (EN)": "Indonesian (Indonesia)", "LANGUAGE (ZH)": "印度尼西亚语（印度尼西亚）", "Applicable CDragon Data Patches": ""}, 27: {"CODE": "zh_MY", "LANGUAGE (EN)": "Chinese (Malaysia)", "LANGUAGE (ZH)": "中文（马来西亚）", "Applicable CDragon Data Patches": "10.5+"}, 28: {"CODE": "zh_CN", "LANGUAGE (EN)": "Chinese (China)", "LANGUAGE (ZH)": "中文（中国）", "Applicable CDragon Data Patches": "9.7+"}, 29: {"CODE": "zh_TW", "LANGUAGE (EN)": "Chinese (Taiwan)", "LANGUAGE (ZH)": "中文（台湾）", "Applicable CDragon Data Patches": "9.7+"}}
    language_cdragon = {}
    for i in language_ddragon:
        if language_ddragon[i]["CODE"] == "en_US":
            language_cdragon[language_ddragon[i]["CODE"]] = "default" #在CommunityDragon数据库上，美服正式服的数据资源代码是default，而不是小写的en_US（The code for English (US) data resources on CommunityDragon database is "default" instead of the lowercase of "en_US"）
        else:
            language_cdragon[language_ddragon[i]["CODE"]] = language_ddragon[i]["CODE"].lower()
    language_dict = {"No.": [], "CODE": [], "LANGUAGE": [], "语言": [], "Applicable CDragon Data Patches": []}
    for i in language_ddragon:
        language_dict["No."].append(i)
        language_dict["CODE"].append(language_ddragon[i]["CODE"])
        language_dict["LANGUAGE"].append(language_ddragon[i]["LANGUAGE (EN)"])
        language_dict["语言"].append(language_ddragon[i]["LANGUAGE (ZH)"])
        language_dict["Applicable CDragon Data Patches"].append(language_ddragon[i]["Applicable CDragon Data Patches"])
    language_df = pandas.DataFrame(language_dict)
    print(format_df(language_df)[0])
    while True:
        language_option = input()
        if language_option == "" or language_option in [str(i) for i in range(1, 30)]:
            if language_option == "":
                language_option = "28"
            language_code = language_ddragon[int(language_option)]["CODE"]
            #下面声明一些数据资源的地址（The following code declare some data resources' URLs）
            URLPatch = "pbe" if platformId == "PBE1" else "latest"
            patches_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            spell_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(URLPatch, language_cdragon[language_code]) #CommunityDragon数据库只存储第7赛季及以后的数据（CommunityDragon database only stores data including and after Season 7）
            LoLItem_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(URLPatch, language_cdragon[language_code])
            perk_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(URLPatch, language_cdragon[language_code])
            perkstyle_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(URLPatch, language_cdragon[language_code])
            TFT_url = "https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(URLPatch, language_code.lower())
            TFTChampion_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(URLPatch, language_cdragon[language_code])
            TFTItem_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(URLPatch, language_cdragon[language_code])
            TFTCompanion_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(URLPatch, language_cdragon[language_code])
            TFTTrait_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(URLPatch, language_cdragon[language_code])
            Arena_url = "https://raw.communitydragon.org/%s/cdragon/arena/%s.json" %(URLPatch, language_code.lower())
            #下面声明离线数据资源的默认地址（The following code declare the default paths of offline data resources）
            patches_local_default = "离线数据（Offline Data）\\versions.json"
            spell_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\summoner-spells.json"
            LoLItem_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\items.json"
            perk_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\perks.json"
            perkstyle_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\perkstyles.json"
            TFT_local_default = "离线数据（Offline Data）\\cdragon\\tft\\zh_cn.json"
            TFTChampion_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tftchampions.json"
            TFTItem_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tftitems.json"
            TFTCompanion_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\companions.json"
            TFTTrait_local_default = "离线数据（Offline Data）\\plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tfttraits.json"
            Arena_local_default = "离线数据（Offline Data）\\cdragon\\arena\\zh_cn.json"
            print("请选择数据资源获取模式：\nPlease select the data resource capture mode:\n1\t在线模式（Online）\n2\t离线模式（Offline）")
            prepareMode = input()
            switch_language = False
            while True:
                if prepareMode != "" and prepareMode[0] == "1":
                    switch_prepare_mode = False
                    #下面获取版本信息（The following code get the patch data）
                    try:
                        patches_initial = requests.get(patches_url).json()
                    except requests.exceptions.RequestException:
                        print('版本信息获取超时！正在尝试离线加载数据……\nPatch information capture timeout! Trying loading offline data ...\n请输入版本Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the patch Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(patches_local_default, patches_local_default))
                        while True:
                            patches_local = input()
                            if patches_local == "":
                                patches_local = patches_local_default
                            elif patches_local[0] == "0":
                                print("版本信息获取失败！请检查系统网络状况和代理设置。\nPatch information capture failure! Please check the system network condition and agent configuration.")
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
                    #下面获取召唤师技能数据（The following code get summoenr spell data）
                    try:
                        print("正在加载召唤师技能信息……\nLoading summoner spell information from CommunityDragon...")
                        spell_initial = requests.get(spell_url) #spell存储召唤师技能信息（Variable `spell_initial` stores summoner spell information）
                        if spell_initial.ok:
                            spell_initial = spell_initial.json()
                        else:
                            print(spell_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('召唤师技能信息获取超时！正在尝试离线加载数据……\nSummoner spell information capture timeout! Trying loading offline data ...\n请输入召唤师技能Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the summoner spell Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(spell_local_default, spell_local_default))
                        while True:
                            spell_local = input()
                            if spell_local == "":
                                spell_local = spell_local_default
                            elif spell_local[0] == "0":
                                print("召唤师技能信息获取失败！请检查系统网络状况和代理设置。\nSummoner spell information capture failure! Please check the system network condition and agent configuration.")
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
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师技能数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner spell data archived in CommunityDragon database (%s)!" %(spell_url, spell_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的召唤师技能Json数据文件路径！\nFile %s NOT found! Please input a correct summoner spell Json data file path!" %(spell_local, spell_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有召唤师技能信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with summoner spell information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的召唤师技能数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the summoner spell data archived in CommunityDragon database (%s)!" %(spell_url, spell_url))
                                continue
                    #下面获取英雄联盟装备信息（The following code get LoL item data）
                    try:
                        print("正在加载英雄联盟装备信息……\nLoading LoL item information from CommunityDragon...")
                        LoLItem_initial = requests.get(LoLItem_url) #LoLItem存储经典模式的装备信息。（Variable `LoLItem_initial` stores information of LoL items）
                        if LoLItem_initial.ok:
                            LoLItem_initial = LoLItem_initial.json()
                        else:
                            print(LoLItem_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('英雄联盟装备信息获取超时！正在尝试离线加载数据……\nLoL item information capture timeout! Trying loading offline data ...\n请输入英雄联盟装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the LoL item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(LoLItem_local_default, LoLItem_local_default))
                        while True:
                            LoLItem_local = input()
                            if LoLItem_local == "":
                                LoLItem_local = LoLItem_local_default
                            elif LoLItem_local[0] == "0":
                                print("英雄联盟装备信息获取失败！请检查系统网络状况和代理设置。\nLoL item information capture failure! Please check the system network condition and agent configuration.")
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
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄联盟装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL item data archived in CommunityDragon database (%s)!" %(LoLItem_url, LoLItem_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的英雄联盟装备Json数据文件路径！\nFile %s NOT found! Please input a correct LoL item Json data file path!" %(LoLItem_local, LoLItem_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有英雄联盟装备信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with LoL item information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的英雄联盟装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the LoL item data archived in CommunityDragon database (%s)!" %(LoLItem_url, LoLItem_url))
                                continue
                    #下面获取基石符文信息（The following code get perk data）
                    try:
                        print("正在加载基石符文信息……\nLoading perk information from CommunityDragon...")
                        perk_initial = requests.get(perk_url) #perk存储基石符文信息。（Variable `perk_initial` stores information of perks）
                        if perk_initial.ok:
                            perk_initial = perk_initial.json()
                        else:
                            print(perk_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('基石符文信息获取超时！正在尝试离线加载数据……\nPerk information capture timeout! Trying loading offline data ...\n请输入基石符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perk Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(perk_local_default, perk_local_default))
                        while True:
                            perk_local = input()
                            if perk_local == "":
                                perk_local = perk_local_default
                            elif perk_local[0] == "0":
                                print("基石符文信息获取失败！请检查系统网络状况和代理设置。\nPerk information capture failure! Please check the system network condition and agent configuration.")
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
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的基石符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perk data archived in CommunityDragon database (%s)!" %(perk_url, perk_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的基石符文Json数据文件路径！\nFile %s NOT found! Please input a correct perk Json data file path!" %(perk_local, perk_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有基石符文信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with perk information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的基石符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perk data archived in CommunityDragon database (%s)!" %(perk_url, perk_url))
                                continue
                    #下面获取符文系信息（The following code get perkstyle data）
                    try:
                        print("正在加载符文系信息……\nLoading perkstyle information from CommunityDragon...")
                        perkstyle_initial = requests.get(perkstyle_url) #perkstyle存储符文系信息。（Variable `perkstyle_initial` stores information of perkstyles）
                        if perkstyle_initial.ok:
                            perkstyle_initial = perkstyle_initial.json()
                        else:
                            print(perkstyle_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('符文系信息获取超时！正在尝试离线加载数据……\nPerkstyle information capture timeout! Trying loading offline data ...\n请输入符文系Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perkstyle Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(perkstyle_local_default, perkstyle_local_default))
                        while True:
                            perkstyle_local = input()
                            if perkstyle_local == "":
                                perkstyle_local = perkstyle_local_default
                            elif perkstyle_local[0] == "0":
                                print("符文系信息获取失败！请检查系统网络状况和代理设置。\nperkstyle information capture failure! Please check the system network condition and agent configuration.")
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
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的符文系数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perkstyle data archived in CommunityDragon database (%s)!" %(perkstyle_url, perkstyle_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的符文系Json数据文件路径！\nFile %s NOT found! Please input a correct perkstyle Json data file path!" %(perkstyle_local, perkstyle_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有符文系信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with perkstyle information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的符文系数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the perkstyle data archived in CommunityDragon database (%s)!" %(perkstyle_url, perkstyle_url))
                                continue
                    #下面获取云顶之弈强化符文数据（The following code get TFT augment data）
                    try:
                        print("正在加载云顶之弈基础数据……\nLoading TFT basic data from CommunityDragon ...")
                        TFT_initial = requests.get(TFT_url) #TFT存储云顶之弈中至今为止所有的强化符文、英雄和羁绊信息和各赛季的英雄和羁绊信息（Variable `TFT_initial` stores information of all augments, champions and traits so far and information of champions and traits with respect to season）
                        if TFT_initial.ok:
                            TFT_initial = TFT_initial.json()
                        else:
                            print(TFT_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('云顶之弈基础信息获取超时！正在尝试离线加载数据……\nTFT basic information capture timeout! Trying loading offline data ...\n请输入云顶之弈基础数据Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT basics Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFT_local_default, TFT_local_default))
                        while True:
                            TFT_local = input()
                            if TFT_local == "":
                                TFT_local = TFT_local_default
                            elif TFT_local[0] == "0":
                                print("云顶之弈基础信息获取失败！请检查系统网络状况和代理设置。\nTFT basic information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(TFT_local, "r", encoding = "utf-8") as fp:
                                    TFT_initial = json.load(fp)
                                if isinstance(TFT_initial, dict) and all(i in TFT_initial for i in ["items", "setData", "sets"]):
                                    break
                                else:
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈基础数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT basic data archived in CommunityDragon database (%s)!" %(TFT_url, TFT_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的云顶之弈基础信息Json数据文件路径！\nFile %s NOT found! Please input a correct TFT basics Json data file path!" %(TFT_local, TFT_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有云顶之弈基础信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT basic information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈基础数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT basic data archived in CommunityDragon database (%s)!" %(TFT_url, TFT_url))
                                continue
                    #下面获取云顶之弈英雄数据（The following code get TFT champion data）
                    try:
                        print("正在加载云顶之弈棋子信息……\nLoading TFT champion information from CommunityDragon ...")
                        TFTChampion_initial = requests.get(TFTChampion_url) #TFTChampion存储云顶之弈的棋子信息（Variable `TFTChampion_initial` stores information of TFT champions）
                        if TFTChampion_initial.ok:
                            TFTChampion_initial = TFTChampion_initial.json()
                        else:
                            print(TFTChampion_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('云顶之弈英雄信息获取超时！正在尝试离线加载数据……\nTFT champion information capture timeout! Trying loading offline data ...\n请输入云顶之弈英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTChampion_local_default, TFTChampion_local_default))
                        while True:
                            TFTChampion_local = input()
                            if TFTChampion_local == "":
                                TFTChampion_local = TFTChampion_local_default
                            elif TFTChampion_local[0] == "0":
                                print("云顶之弈英雄信息获取失败！请检查系统网络状况和代理设置。\nTFT champion information capture failure! Please check the system network condition and agent configuration.")
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
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈棋子数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT champion data archived in CommunityDragon database (%s)!" %(TFTChampion_url, TFTChampion_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的云顶之弈棋子Json数据文件路径！\nFile %s NOT found! Please input a correct TFT champion Json data file path!" %(TFTChampion_local, TFTChampion_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有云顶之弈英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT champion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈棋子数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT champion data archived in CommunityDragon database (%s)!" %(TFTChampion_url, TFTChampion_url))
                                continue
                    #下面获取云顶之弈装备数据（The following code get TFT item information）
                    try:
                        print("正在加载云顶之弈装备信息……\nLoading TFT item information from CommunityDragon ...")
                        TFTItem_initial = requests.get(TFTItem_url) #TFTItem存储云顶之弈的装备信息（Variable `TFTItem_initial` stores information of TFT items）
                        if TFTItem_initial.ok:
                            TFTItem_initial = TFTItem_initial.json()
                        else:
                            print(TFTItem_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('云顶之弈装备信息获取超时！正在尝试离线加载数据……\nTFT item information capture timeout! Trying loading offline data ...\n请输入云顶之弈装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTItem_local_default, TFTItem_local_default))
                        while True:
                            TFTItem_local = input()
                            if TFTItem_local == "":
                                TFTItem_local = TFTItem_local_default
                            elif TFTItem_local[0] == "0":
                                print("云顶之弈装备信息获取失败！请检查系统网络状况和代理设置。\nTFT item information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(TFTItem_local, "r", encoding = "utf-8") as fp:
                                    TFTItem_initial = json.load(fp)
                                if isinstance(TFTItem_initial, list) and all(isinstance(TFTItem_initial[i], dict) for i in range(len(TFTItem_initial))) and all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "loadoutsIcon"]):
                                    break
                                else:
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT item data archived in CommunityDragon database (%s)!" %(TFTItem_url, TFTItem_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的云顶之弈装备Json数据文件路径！\nFile %s NOT found! Please input a correct TFT item Json data file path!" %(TFTItem_local, TFTItem_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有云顶之弈装备信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈装备数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT item data archived in CommunityDragon database (%s)!" %(TFTItem_url, TFTItem_url))
                                continue
                    #下面获取云顶之弈小小英雄数据（The following code get TFT companion data）
                    try:
                        print("正在加载云顶之弈小小英雄信息……\nLoading companion information from CommunityDragon ...")
                        TFTCompanion_initial = requests.get(TFTCompanion_url) #TFTChampion存储云顶之弈的小小英雄信息（Variable `TFTChampion_initial` stores information of companions）
                        if TFTCompanion_initial.ok:
                            TFTCompanion_initial = TFTCompanion_initial.json()
                        else:
                            print(TFTCompanion_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('云顶之弈小小英雄信息获取超时！正在尝试离线加载数据……\nTFT companion information capture timeout! Trying loading offline data ...\n请输入云顶之弈小小英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT companion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTCompanion_local_default, TFTCompanion_local_default))
                        while True:
                            TFTCompanion_local = input()
                            if TFTCompanion_local == "":
                                TFTCompanion_local = TFTCompanion_local_default
                            elif TFTCompanion_local[0] == "0":
                                print("云顶之弈小小英雄信息获取失败！请检查系统网络状况和代理设置。\nTFT companion information capture failure! Please check the system network condition and agent configuration.")
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
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈小小英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT companion data archived in CommunityDragon database (%s)!" %(TFTCompanion_url, TFTCompanion_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的云顶之弈小小英雄Json数据文件路径！\nFile %s NOT found! Please input a correct TFT companion Json data file path!" %(TFTCompanion_local, TFTCompanion_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有云顶之弈小小英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈小小英雄数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT companion data archived in CommunityDragon database (%s)!" %(TFTCompanion_url, TFTCompanion_url))
                                continue
                    #下面获取云顶之弈羁绊数据（The following code get TFT trait data）
                    try:
                        print("正在加载云顶之弈羁绊信息……\nLoading TFT trait information from CommunityDragon ...")
                        TFTTrait_initial = requests.get(TFTTrait_url) #TFTTrait存储云顶之弈的羁绊信息（Variable `TFTTrait_initial` stores information of TFT traits）
                        if TFTTrait_initial.ok:
                            TFTTrait_initial = TFTTrait_initial.json()
                        else:
                            print(TFTTrait_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('云顶之弈羁绊信息获取超时！正在尝试离线加载数据……\nTFT trait information capture timeout! Trying loading offline data ...\n请输入云顶之弈羁绊Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT trait Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(TFTTrait_local_default, TFTTrait_local_default))
                        while True:
                            TFTTrait_local = input()
                            if TFTTrait_local == "":
                                TFTTrait_local = TFTTrait_local_default
                            elif TFTTrait_local[0] == "0":
                                print("云顶之弈羁绊信息获取失败！请检查系统网络状况和代理设置。\nTFT trait information capture failure! Please check the system network condition and agent configuration.")
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
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈羁绊数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT trait data archived in CommunityDragon database (%s)!" %(TFTTrait_url, TFTTrait_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的云顶之弈羁绊Json数据文件路径！\nFile %s NOT found! Please input a correct TFT trait Json data file path!" %(TFTTrait_local, TFTTrait_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有云顶之弈小小英雄信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with TFT companion information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的云顶之弈羁绊数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the TFT trait data archived in CommunityDragon database (%s)!" %(TFTTrait_url, TFTTrait_url))
                                continue
                    #下面获取斗魂竞技场强化符文数据（The following code get Arena augment data）
                    try:
                        print("正在加载斗魂竞技场强化符文信息……\nLoading Arena augment information from CommunityDragon ...")
                        Arena_initial = requests.get(Arena_url) #Arena存储斗魂竞技场的强化符文信息（Variable `Arena_initial` stores information of Arena augments）
                        if Arena_initial.ok:
                            Arena_initial = Arena_initial.json()
                            break
                        else:
                            print(Arena_initial)
                            print("当前语言不可用！请切换语言或检查源代码中的链接。\nCurrent language isn't available! Please change another language or check the requests link in the source code.")
                            switch_language = True
                            break
                    except requests.exceptions.RequestException:
                        print('斗魂竞技场强化符文信息获取超时！正在尝试离线加载数据……\nArena augment information capture timeout! Trying loading offline data ...\n请输入斗魂竞技场强化符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the Arena augment Json data file path. Enter an empty string to use the default relative path: "%s". Submit "2" to switch to offline mode. Submit "0" to exit.' %(Arena_local_default, Arena_local_default))
                        while True:
                            Arena_local = input()
                            if Arena_local == "":
                                Arena_local = Arena_local_default
                            elif Arena_local[0] == "0":
                                print("斗魂竞技场强化符文信息获取失败！请检查系统网络状况和代理设置。\nArena augment information capture failure! Please check the system network condition and agent configuration.")
                                time.sleep(5)
                                return 1
                            else:
                                switch_prepare_mode = True
                                break
                            try:
                                with open(Arena_local, "r", encoding = "utf-8") as fp:
                                    Arena_initial = json.load(fp)
                                if isinstance(Arena_initial, dict) and all(i in Arena_initial for i in ["augments"]) and isinstance(Arena_initial["augments"], list) and all(isinstance(Arena_initial["augments"][i], dict) for i in range(len(Arena_initial))) and all(j in Arena_initial["augments"][i] for i in range(len(Arena_initial["augments"])) for j in ["apiName", "calculations", "dataValues", "desc", "iconLarge", "iconSmall", "id", "name", "rarity", "tooltip"]):
                                    break
                                else:
                                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的斗魂竞技场强化符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the Arena augment data archived in CommunityDragon database (%s)!" %(Arena_url, Arena_url))
                                    continue
                            except FileNotFoundError:
                                print("未找到文件%s！请输入正确的斗魂竞技场强化符文Json数据文件路径！\nFile %s NOT found! Please input a correct Arena augment Json data file path!" %(Arena_local, Arena_local))
                                continue
                            except OSError:
                                print("数据文件名不合法！请输入含有斗魂竞技场强化符文信息的本地文件的路径！\nIllegal data filename! Please input the path of a local file with Arena augment information.")
                                continue
                            except json.decoder.JSONDecodeError:
                                print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的斗魂竞技场强化符文数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the Arena augment data archived in CommunityDragon database (%s)!" %(Arena_url, Arena_url))
                                continue
                    if switch_prepare_mode:
                        prepareMode = ""
                        continue
                    break
                else:
                    switch_prepare_mode = False
                    print('请在浏览器中打开以下网页，待加载完成后按Ctrl + S保存网页json文件至同目录的“离线数据（Offline Data）”文件夹下，并根据括号内的提示放置和命名文件。\nPlease open the following URLs in a browser, then press Ctrl + S to save the online json files into the folder "离线数据（Offline Data）" under the same directory after the website finishes loading and organize and rename the downloaded files according to the hints in the circle brackets.\n版本信息（versions.json）： %s\n召唤师技能（summoner.json）： %s\n英雄联盟装备（items.json）： %s\n基石符文（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\perks.json）： %s\n符文系（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\perkstyles.json）： %s\n云顶之弈基础信息（cdragon\\tft\\zh_cn.json）： %s\n云顶之弈棋子（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tftchampions.json）： %s\n云顶之弈装备（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tftitems.json）： %s\n云顶之弈小小英雄（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\companions.json）： %s\n云顶之弈羁绊（plugins\\rcp-be-lol-game-data\\global\\zh_cn\\v1\\tfttraits.json）： %s\n斗魂竞技场强化符文（cdragon\\arena\\zh_cn.json）： %s' %(patches_url, spell_url, LoLItem_url, perk_url, perkstyle_url, TFT_url, TFTChampion_url, TFTItem_url, TFTCompanion_url, TFTTrait_url, Arena_url))
                    offline_files_loaded = {"patch": False, "spell": False, "LoLItem": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "Arena": False}
                    offline_files = {"patch": {"file": patches_local_default, "URL": patches_url, "content": "版本信息"}, "spell": {"file": spell_local_default, "URL": spell_url, "content": "召唤师技能"}, "LoLItem": {"file": LoLItem_local_default, "URL": LoLItem_url, "content": "英雄联盟装备"}, "perk": {"file": perk_local_default, "URL": perk_url, "content": "基石符文"}, "perkstyle": {"file": perkstyle_local_default, "URL": perkstyle_url, "content": "符文系"}, "TFT": {"file": TFT_local_default, "URL": TFT_url, "content": "云顶之弈基础信息"}, "TFTChampion": {"file": TFTChampion_local_default, "URL": TFTChampion_url, "content": "云顶之弈英雄"}, "TFTItem": {"file": TFTItem_local_default, "URL": TFTItem_url, "content": "云顶之弈装备"}, "TFTCompanion": {"file": TFTCompanion_local_default, "URL": TFTCompanion_url, "content": "云顶之弈小小英雄"}, "TFTTrait": {"file": TFTTrait_local_default, "URL": TFTTrait_url, "content": "云顶之弈羁绊"}, "Arena": {"file": Arena_local_default, "URL": Arena_url, "content": "斗魂竞技场强化符文"}}
                    print('请按任意键以加载离线数据。输入“1”以转为在线模式。输入“0”以退出程序。\nPlease input anything to load offline data. Input "1" to switch to online mode. Submit "0" to exit.')
                    while any(not i for i in offline_files_loaded.values()):
                        offline_files_notfound = {"patch": False, "spell": False, "LoLItem": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "Arena": False}
                        offline_files_formaterror = {"patch": False, "spell": False, "LoLItem": False, "perk": False, "perkstyle": False, "TFT": False, "TFTChampion": False, "TFTItem": False, "TFTCompanion": False, "TFTTrait": False, "Arena": False}
                        prepareMode = input()
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
                        #下面获取召唤师技能数据（The following code get summoenr spell data）
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
                                if not(isinstance(TFTItem_initial, list) and all(isinstance(TFTItem_initial[i], dict) for i in range(len(TFTItem_initial))) and all(j in TFTItem_initial[i] for i in range(len(TFTItem_initial)) for j in ["guid", "name", "nameId", "id", "color", "loadoutsIcon"])):
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
                        if not offline_files_loaded["Arena"]:
                            try:
                                with open(Arena_local_default, "r", encoding = "utf-8") as fp:
                                    Arena_initial = json.load(fp)
                                if not(isinstance(Arena_initial, dict) and all(i in Arena_initial for i in ["augments"]) and isinstance(Arena_initial["augments"], list) and all(isinstance(Arena_initial["augments"][i], dict) for i in range(len(Arena_initial))) and all(j in Arena_initial["augments"][i] for i in range(len(Arena_initial["augments"])) for j in ["apiName", "calculations", "dataValues", "desc", "iconLarge", "iconSmall", "id", "name", "rarity", "tooltip"])):
                                    offline_files_formaterror["Arena"] = True
                            except FileNotFoundError:
                                offline_files_notfound["Arena"] = True
                            except json.decoder.JSONDecodeError:
                                offline_files_formaterror["Arena"] = True
                            else:
                                if not offline_files_formaterror["Arena"]:
                                    offline_files_loaded["Arena"] = True
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
                    else:
                        break
            if switch_language:
                continue
            break
        elif language_option[0] == "0":
            return 2
        else:
            print("语言选项输入错误！请重新输入：\nERROR input of language option! Please try again:")
    #首先准备一些数据（First, prepare some data）
    #准备自己的召唤师数据（Prepare the information of the user himself/herself）
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    ##准备游戏模式数据（Prepare game mode data）
    gamemode = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    gamemodes = {0: {"name": "自定义", "gameMode": "CUSTOM", "category": "CUSTOM"}}
    for gamemode_iter in gamemode:
        gamemode_id = gamemode_iter.pop("id")
        gamemodes_iter = {}
        gamemodes_iter["name"] = gamemode_iter["name"]
        gamemodes_iter["gameMode"] = gamemode_iter["gameMode"]
        gamemodes_iter["category"] = gamemode_iter["category"]
        gamemodes[gamemode_id] = gamemodes_iter
    ##准备英雄数据，用于将英雄序号映射到英雄名称（Prepare champion data to map championIds to champions' names）
    summonerId = current_info["summonerId"]
    LoLChampion = await (await connection.request("GET", "/lol-champions/v1/inventories/" + str(summonerId) + "/champions")).json()
    LoLChampions = {}
    for LoLChampion_iter in LoLChampion:
        LoLChampion_id = LoLChampion_iter.pop("id")
        LoLChampions[LoLChampion_id] = LoLChampion_iter
    ##准备召唤师技能数据（Prepare summoner spell data）
    spells_initial = {} #spells为嵌套字典，键为召唤师技能序号，值为召唤师技能信息字典。一个键值对的示例如右：（Variable `spells` is a nested dictionary, whose keys are spellIds and values are spell information dictionaries. An example of the key-value pairs is shown as follows: ）{1: {"name": "净化", "description": "移除身上的所有限制效果（压制效果和击飞效果除外）和召唤师技能的减益效果，并且若在接下来的3秒里再次被施加限制效果时，新效果的持续时间会减少65%。", "summonerLevel": 9, "cooldown": 210, "gameModes": ["URF", "CLASSIC", "ARSR", "ARAM", "ULTBOOK", "WIPMODEWIP", "TUTORIAL", "DOOMBOTSTEEMO", "PRACTICETOOL", "FIRSTBLOOD", "NEXUSBLITZ", "PROJECT", "ONEFORALL"], "iconPath": "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_boost.png"}}
    for spell_iter in spell_initial:
        spell_id = spell_iter.pop("id")
        spells_initial[spell_id] = spell_iter
    ##准备英雄联盟装备数据（Prapare LoL item data）
    LoLItems_initial = {} #LoLItems为嵌套字典，键为装备序号，值为装备信息字典。一个键值对的示例如右：（Variable `LoLItems` is a nested dictionary, whose keys are itemIds and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{1001: {"name": "鞋子", "description": "<mainText><stats><attention>25</attention>移动速度</stats></mainText><br>", "active": False, "inStore": True, "from": [], "to": [3111, 3006, 3005, 3009, 3020, 3047, 3117, 3158], "categories": ["Boots"], "maxStacks": 1, "requiredChampion": "", "requiredAlly": "", "requiredBuffCurrencyName": "", "requiredBuffCurrencyCost": 0, "specialRecipe": 0, "isEnchantment": False, "price": 300, "priceTotal": 300, "iconPath": "/lol-game-data/assets/ASSETS/Items/Icons2D/1001_Class_T1_BootsofSpeed.png"}}
    for LoLItem_iter in LoLItem_initial:
        LoLItem_id = LoLItem_iter.pop("id")
        LoLItems_initial[str(LoLItem_id)] = LoLItem_iter
    ##准备符文数据（Prepare runes data）
    perks_initial = {} #perks为嵌套字典，键为符文序号，值为符文信息字典。一个键值对的示例如右：（Variable `perks` is a nested dictionary, whose keys are perkIds and values are perk information dictionaries. An example of the key-value pairs is shown as follows: ）{8369: {"name": "先攻", "majorChangePatchVersion": "11.23", "tooltip": "在进入与英雄战斗的@GraceWindow.2@秒内，对一名敌方英雄进行的攻击或技能将提供@GoldProcBonus@金币和<b>先攻</b>效果，持续@Duration@秒，来使你对英雄们造成<truedamage>@DamageAmp*100@%</truedamage>额外<truedamage>伤害</truedamage>，并提供<gold>{{ Item_Melee_Ranged_Split }}</gold>该额外伤害值的<gold>金币</gold>。<br><br>冷却时间：<scaleLevel>@Cooldown@</scaleLevel>秒<br><hr><br>已造成的伤害：@f1@<br>已提供的金币：@f2@", "shortDesc": "在你率先发起与英雄的战斗时，造成8%额外伤害，持续3秒，并基于该额外伤害提供金币。", "longDesc": "在进入与英雄战斗的0.25秒内，对一名敌方英雄进行的攻击或技能将提供5金币和<b>先攻</b>效果，持续3秒，来使你对英雄们造成<truedamage>8%</truedamage>额外<truedamage>伤害</truedamage>，并提供<gold>100% (远程英雄为70%)</gold>该额外伤害值的<gold>金币</gold>。<br><br>冷却时间：<scaleLevel>25 ~ 15</scaleLevel>秒", "recommendationDescriptor": "真实伤害，金币收入", "iconPath": "/lol-game-data/assets/v1/perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png", "endOfGameStatDescs": ["已造成的伤害：@eogvar1@", "已提供的金币：@eogvar2@"], "recommendationDescriptorAttributes": {}}}
    for perk_iter in perk_initial:
        perk_id = perk_iter.pop("id")
        perks_initial[perk_id] = perk_iter
    ##准备符文系数据（Prepare perkstyle data）
    perkstyles_initial = {} #perkstyles为嵌套字典，键为符文系序号，值为符文系信息字典。一个键值对的示例如右：（Variable `perkstyles` is a nested dictionary, whose keys are perkstyle ids and values are perkstyle information dictionaries. An example of the key-value pairs is as follows: ）{8400: {"name": "坚决", "tooltip": "耐久和控制", "iconPath": "/lol-game-data/assets/v1/perk-images/Styles/7204_Resolve.png", "assetMap": {"p8400_s0_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k0.jpg", "p8400_s0_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8437.jpg", "p8400_s0_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8439.jpg", "p8400_s0_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8465.jpg", "p8400_s8000_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k0.jpg", "p8400_s8000_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8437.jpg", "p8400_s8000_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8439.jpg", "p8400_s8000_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8465.jpg", "p8400_s8100_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k0.jpg", "p8400_s8100_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8437.jpg", "p8400_s8100_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8439.jpg", "p8400_s8100_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8465.jpg", "p8400_s8200_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k0.jpg", "p8400_s8200_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8437.jpg", "p8400_s8200_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8439.jpg", "p8400_s8200_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8465.jpg", "p8400_s8300_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k0.jpg", "p8400_s8300_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8437.jpg", "p8400_s8300_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8439.jpg", "p8400_s8300_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8465.jpg", "svg_icon": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/resolve_icon.svg", "svg_icon_16": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/resolve_icon_16.svg"}, "isAdvanced": False, "allowedSubStyles": [8000, 8100, 8200, 8300], "subStyleBonus": [{"styleId": 8000, "perkId": 8414}, {"styleId": 8100, "perkId": 8454}, {"styleId": 8200, "perkId": 8415}, {"styleId": 8300, "perkId": 8416}], "slots": [{"type": "kKeyStone", "slotLabel": "", "perks": [8437, 8439, 8465]}, {"type": "kMixedRegularSplashable", "slotLabel": "蛮力", "perks": [8446, 8463, 8401]}, {"type": "kMixedRegularSplashable", "slotLabel": "抵抗", "perks": [8429, 8444, 8473]}, {"type": "kMixedRegularSplashable", "slotLabel": "生机", "perks": [8451, 8453, 8242]}, {"type": "kStatMod", "slotLabel": "进攻", "perks": [5008, 5005, 5007]}, {"type": "kStatMod", "slotLabel": "灵活", "perks": [5008, 5002, 5003]}, {"type": "kStatMod", "slotLabel": "防御", "perks": [5001, 5002, 5003]}], "defaultPageName": "坚决：巨像", "defaultSubStyle": 8200, "defaultPerks": [8437, 8446, 8444, 8451, 8224, 8237, 5008, 5002, 5001], "defaultPerksWhenSplashed": [8444, 8446], "defaultStatModsPerSubStyle": [{"id": "8000", "perks": [5005, 5002, 5001]}, {"id": "8100", "perks": [5008, 5002, 5001]}, {"id": "8200", "perks": [5008, 5002, 5001]}, {"id": "8300", "perks": [5007, 5002, 5001]}]}}
    for perkstyle_iter in perkstyle_initial["styles"]:
        perkstyle_id = perkstyle_iter.pop("id")
        perkstyles_initial[perkstyle_id] = perkstyle_iter
    ##准备云顶之弈强化符文数据（Prepare TFT augment data）
    TFTAugments_initial = {} #TFTAugments为嵌套字典，键为物件在LCU API上的表达形式，值为物件信息字典。一个键值对的示例如右：（Variable `TFTAugments` is a nested dictionary, whose keys are LCU API representation of items and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFT7_Consumable_NeekosHelpDragon": {"associatedTraits": [], "composition": [], "desc": "TFT7_Consumable_Description_Dragonling", "effects": {}, "from": None, "icon": "ASSETS/Maps/Particles/TFT/TFT7_Consumable_Dragonling.tex", "id": None, "incompatibleTraits": [], "name": "TFT7_Consumable_Name_Dragonling", "unique": False}}
    for item in TFT_initial["items"]:
        item_apiName = item.pop("apiName")
        TFTAugments_initial[item_apiName] = item
    ##准备云顶之弈英雄数据（Prepare TFT champion data）
    TFTChampions_initial = {} #TFTChampions为嵌套字典，键为棋子在LCU API上的表达形式，值为棋子信息字典。一个键值对的示例如右：（Variable `TFTChampions` is a nested dictionary, whose keys are LCU API representation of TFT Champions and values are TFT Champion information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFT9_Aatrox": {"character_record": {"path": "Characters/TFT9_Aatrox/CharacterRecords/Root", "character_id": "TFT9_Aatrox", "rarity": 9, "display_name": "亚托克斯", "traits": [{"name": "暗裔", "id": "Set9_Darkin"}, {"name": "裁决战士", "id": "Set9_Slayer"}, {"name": "主宰", "id": "Set9_Armorclad"}], "squareIconPath": "/lol-game-data/assets/ASSETS/Characters/TFT9_Aatrox/HUD/TFT9_Aatrox_Square.TFT_Set9.png"}}}
    for TFTChampion_iter in TFTChampion_initial:
        champion_name = TFTChampion_iter.pop("name")
        TFTChampions_initial[champion_name] = TFTChampion_iter["character_record"]
    ##准备云顶之弈装备数据（Prepare TFT item data）
    TFTItems_initial = {} #TTItems为嵌套字典，键为云顶之弈装备名称序号，值为云顶之弈装备信息字典。一个键值对的示例如右：（Variable `TFTItems` is a nested dictionary, whose keys are TFT item nameIds and values are TFT item information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFTTutorial_Item_BFSword": {"guid": "9f6e75bb-7ba2-49aa-8724-04c550279034", "name": "暴风大剑", "id": 0, "color": {"R": 73, "B": 54, "G": 68, "A": 255}, "loadoutsIcon": "/lol-game-data/assets/ASSETS/Maps/Particles/TFT/Item_Icons/Standard/BF_Sword.png"}}
    for TFTItem_iter in TFTItem_initial:
        item_nameId = TFTItem_iter.pop("nameId")
        TFTItems_initial[item_nameId] = TFTItem_iter
    ##准备云顶之弈小小英雄数据（Prepare TFT companion data）
    TFTCompanions_initial = {} #TFTCompanions为嵌套字典，键为小小英雄序号，值为小小英雄信息字典。一个键值对的示例如右：（Variable `TFTCompanions` is a nested dictionary, whose keys are companion contentIds and values are companion information dictionaries. An example of the key-value pairs is shown as follows: ）{"91f2e228-4e36-4dad-9a97-36036e3eca36": {"itemId": 13010, "name": "节奏大师 奥希雅", "loadoutsIcon": "/lol-game-data/assets/ASSETS/Loadouts/Companions/Tooltip_AkaliDragon_Beatmaker_Tier1.png", "description": "奥希雅是酷炫的具象化。它用毫不费力的语流，指挥着韵脚和节奏，甚至能让最出色的小小英雄们羡慕不休。", "level": 1, "speciesName": "奥希雅", "speciesId": 13, "rarity": "Epic", "rarityValue": 1, "isDefault": false, "upgrades": ["0e251d36-d86e-4c58-9b7f-bcee2376a408", "e3151dc2-c45c-4949-89e9-6afda3b2fd5f"], "TFTOnly": false}}
    for companion_iter in TFTCompanion_initial:
        contentId = companion_iter.pop("contentId")
        TFTCompanions_initial[contentId] = companion_iter
    ##准备云顶之弈羁绊数据（Prepare TFT trait data）
    TFTTraits_initial = {} #TFTTraits为嵌套字典，键为羁绊在LCU API上的表达形式，值为羁绊信息字典。一个键值对的示例如右：（Variable `TFTTraits` is a nested dictionary, whose keys are LCU API representation of traits and values are trait information dictionaries. An example of the key-value pairs is shown as follows: ）{"Assassin": {"display_name": "刺客", "set": "TFTSet1", "icon_path": "/lol-game-data/assets/ASSETS/UX/TraitIcons/Trait_Icon_Assassin.png", "tooltip_text": "固有：在战斗环节开始时，刺客们会跃至距离最远的敌人处。<br><br>刺客们会获得额外的暴击伤害和暴击几率。<br><br><expandRow>(@MinUnits@) +@CritAmpPercent@%暴击伤害和+@CritChanceAmpPercent@%暴击几率</expandRow><br>", "innate_trait_sets": [], "conditional_trait_sets": {2: {"effect_amounts": [{"name": "CritAmpPercent", "value": 75.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 5.0, "format_string": ""}], "min_units": 3, "max_units": 5, "style_name": "kBronze"}, 3: {"effect_amounts": [{"name": "CritAmpPercent", "value": 150.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 20.0, "format_string": ""}], "min_units": 6, "max_units": 8, "style_name": "kSilver"}, 4: {"effect_amounts": [{"name": "CritAmpPercent", "value": 225.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 30.0, "format_string": ""}], "min_units": 9, "max_units": 25000, "style_name": "kGold"}}}}
    for trait_iter in TFTTrait_initial:
        trait_id = trait_iter.pop("trait_id")
        conditional_trait_sets = {}
        for conditional_trait_set in trait_iter["conditional_trait_sets"]:
            style_idx = conditional_trait_set.pop("style_idx")
            conditional_trait_sets[style_idx] = conditional_trait_set
        trait_iter["conditional_trait_sets"] = conditional_trait_sets
        TFTTraits_initial[trait_id] = trait_iter
    ##准备斗魂竞技场强化符文数据（Prepare Arena augment data）
    ArenaAugments_initial = {} #ArenaAugments为嵌套字典，键为斗魂竞技场强化符文在LCU API上的表达形式，值为斗魂竞技场强化符文信息字典。一个键值对的实例如右：（Variable `ArenaAugments` is a nested dictionary, whose keys are LCU API representation of Arena augments and values are Arena augment information dictionaries. An example of the key-value pairs is shown as follows: ）{89: {"apiName": "WarmupRoutine", "calculations": {}, "dataValues": {"DamagePerStack": 0.009999999776482582, "MaxStacks": 24.0}, "desc": "获得召唤师技能<spellName>热身动作</spellName>。<br><br><rules><spellName>热身动作</spellName>可使你通过进行引导来提升你的伤害，持续至回合结束。</rules>", "iconLarge": "assets/ux/cherry/augments/icons/warmuproutine_large.2v2_mode_fighters.png", "iconSmall": "assets/ux/cherry/augments/icons/warmuproutine_small.2v2_mode_fighters.png", "name": "热身动作", "rarity": 0, "tooltip": "进行引导，每秒使你的伤害提升2%，至多至24%。<br><br>这个回合的额外伤害：@f1@<br>额外伤害的总和：@f2@"}}
    for ArenaAugment in Arena_initial["augments"]:
        ArenaAugment_id = ArenaAugment.pop("id")
        ArenaAugments_initial[ArenaAugment_id] = ArenaAugment
    ##准备大区数据（Prepare server / platform data）
    platform_TENCENT = {"BGP1": "全网通区 男爵领域（Baron Zone）", "BGP2": "峡谷之巅（Super Zone）", "EDU1": "教育网专区（CRENET Server）", "HN1": "电信一区 艾欧尼亚（Ionia）", "HN2": "电信二区 祖安（Zaun）", "HN3": "电信三区 诺克萨斯（Noxus 1）", "HN4": "电信四区 班德尔城（Bandle City）", "HN5": "电信五区 皮尔特沃夫（Piltover）", "HN6": "电信六区 战争学院（the Institute of War）", "HN7": "电信七区 巨神峰（Mount Targon）", "HN8": "电信八区 雷瑟守备（Noxus 2）", "HN9": "电信九区 裁决之地（the Proving Grounds）", "HN10": "电信十区 黑色玫瑰（the Black Rose）", "HN11": "电信十一区 暗影岛（Shadow Isles）", "HN12": "电信十二区 钢铁烈阳（the Iron Solari）", "HN13": "电信十三区 水晶之痕（Crystal Scar）", "HN14": "电信十四区 均衡教派（the Kinkou Order）", "HN15": "电信十五区 影流（the Shadow Order）", "HN16": "电信十六区 守望之海（Guardian's Sea）", "HN17": "电信十七区 征服之海（Conqueror's Sea）", "HN18": "电信十八区 卡拉曼达（Kalamanda）", "HN19": "电信十九区 皮城警备（Piltover Wardens）", "PBE": "体验服 试炼之地（Chinese PBE）", "WT1": "网通一区 比尔吉沃特（Bilgewater）", "WT2": "网通二区 德玛西亚（Demacia）", "WT3": "网通三区 弗雷尔卓德（Freljord）", "WT4": "网通四区 无畏先锋（House Crownguard）", "WT5": "网通五区 恕瑞玛（Shurima）", "WT6": "网通六区 扭曲丛林（Twisted Treeline）", "WT7": "网通七区 巨龙之巢（the Dragon Camp）"}
    platform_RIOT = {"BR": "巴西服（Brazil）", "EUNE": "北欧和东欧服（Europe Nordic & East）", "EUW": "西欧服（Europe West）", "LAN": "北拉美服（Latin America North）", "LAS": "南拉美服（Latin America South）", "NA": "北美服（North America）", "OCE": "大洋洲服（Oceania）", "RU": "俄罗斯服（Russia）", "TR": "土耳其服（Turkey）", "JP": "日服（Japan）", "KR": "韩服（Republic of Korea）", "PBE": "测试服（Public Beta Environment）"}
    platform_GARENA = {"PH": "菲律宾服（Philippines）", "SG": "新加坡服（Singapore, Malaysia and Indonesia）", "TW": "台服（Taiwan, Hong Kong and Macau）", "VN": "越南服（Vietnam）", "TH": "泰服（Thailand）"}
    platform = {"TENCENT": "国服（TENCENT）", "RIOT": "外服（RIOT）", "GARENA": "竞舞（GARENA）"}
    print("请选择本脚本的使用模式：\nPlease select a mode for use:\n1\t生成模式（Generate Mode）\n2\t检测模式（Detect Mode）")
    detectMode = False
    mode = input()
    if mode == "" or mode[0] != "1":
        detectMode = True
    #然后获取历史记录（Next, fetch the history）
    print('''在腾讯代理的服务器上，如果查询某名玩家的对局记录，请尝试以下操作：\nTo search for the match history of a player on Tencent servers, try out the following operations:\n1. 在浏览器中打开本地主机网络协议：%s\n   Open the localhost IP in any browser: %s\n2. 尝试用以下用户名和密码登录：\n   Try logining in with the following username and password:\n   用户名（Username）：riot\n   密码（Password）：%s\n3. （如果可以立即知道一位玩家的玩家通用唯一识别码，则可以跳过第3和4步）在浏览器的地址栏中的地址最后，添加“lol-summoner/v1/summoners?name={name}”，其中{name}指的是召唤师名称编码后的字符串。当召唤师名称只包含英文字母和阿拉伯数字时，直接以召唤师名称去空格后的字符串代入{name}即可；当召唤师名称存在非美国标准信息交换代码时，以召唤师名称编码后的字符串代入{name}。\n(If a summoner's puuid can be immediately known, the user may skip Steps 3 and 4) Add to following the last character of the address in the browser's address bar "lol-summoner/v1/summoners?name={name}", where {name} refers to strings encoded from summonerName. When summonerName contains only English letters and Arabic numbers, simply substitute {name} with the strings with the spaces removed from summonerName. When a non-ASCII character exists in summonerName, substitute {name} by encoded summonerName.\n3.1 对于包含非美国标准信息交换代码的召唤师名称，如果可以得到该召唤师的精确名称（如通过复制到剪贴板），那么在Python中可以得知其编码后的字符串。在Python中使用from urllib.parse import quote命令引入quote函数，再使用quote(x)函数获取字符串x编码后的字符串。\nFor summonerNames that include non-ASCII characters, if the exact summonerName can be obtained (e. g. by copying to clipboard), then its encoded string can be returned in Python. In Python console, use "from urllib.parse import quote" to introduce the "quote" function. Then use quote(x) function to get the string encoded from the string x.\n4. 在lol-summoner/v1/summoners?name={name}返回的结果中找到puuid并复制。\n   Find "puuid" in the result returned by "lol-summoner/v1/summoners?name={name}" and copy it.\n5. 将地址栏中4位IP地址后的斜杠后的内容删除，再添加“lol-match-history/v1/products/lol/{puuid}/matches?begIndex=0&endIndex=20”，其中{puuid}是事先获知的玩家通用唯一识别码，或者是第4步复制到剪贴板的puuid。\nDelete the content following the slash after the 4-bit IP address in the address bar and then add to the end "lol-match-history/v1/products/lol/{puuid}/matches?begIndex=0&endIndex=20", where {puuid} refers to the puuid previously known, or copied to clipboard in Step 4.\n6. 尝试将上一步输入的地址中的“endIndex=”后的数字依次替换成21、199、200和500，观察每次替换后返回的网页结果有没有变多。\nTry changing the number followin "endIndex=" in the last step into 21, 199, 200 and 500 one by one, and observe whether the returned webpage contains more information after each change.\n7. 教程完成，请继续执行本脚本……\n   Instruction finished. Please continue to run this program ...''' %(connection.address, connection.address, connection.auth_key))
    while True:
        #初始化所有数据资源（Initialize all data resources）
        print("\n正在初始化所有数据资源……\nInitializing all data resources ...\n")
        patches = copy.deepcopy(patches_initial)
        spells = copy.deepcopy(spells_initial)
        LoLItems = copy.deepcopy(LoLItems_initial)
        perks = copy.deepcopy(perks_initial)
        perkstyles = copy.deepcopy(perkstyles_initial)
        TFTAugments = copy.deepcopy(TFTAugments_initial)
        TFTChampions = copy.deepcopy(TFTChampions_initial)
        TFTItems = copy.deepcopy(TFTItems_initial)
        TFTCompanions = copy.deepcopy(TFTCompanions_initial)
        TFTTraits = copy.deepcopy(TFTTraits_initial)
        ArenaAugments = copy.deepcopy(ArenaAugments_initial)
        if detectMode == False:
            print('请输入要查询的召唤师名称，退出请输入“0”：\nPlease input the summoner name to be searched. Submit "0" to exit.')
            summoner_name = input()
        else:
            info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
            summoner_name = info["displayName"]
        if summoner_name == "0":
            os._exit(0)
        elif summoner_name == "":
            print("请输入非空字符串！\nPlease input a string instead of null!")
            continue
        else:
            if detectMode == False:
                if summoner_name.count("-") == 4 and len(summoner_name.replace(" ", "")) > 22: #拳头规定的玩家名称不超过16个字符，尾标不超过5个字符（Riot game name can't exceed 16 characters. The tagline can't exceed 5 characters）
                    search_by_puuid = True
                    info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + quote(summoner_name))).json()
                else:
                    search_by_puuid = False
                    info = await (await connection.request("GET", "/lol-summoner/v1/summoners?name=" + quote(summoner_name))).json()
            if "errorCode" in info and info["httpStatus"] == 400:
                if search_by_puuid:
                    print("您输入的玩家通用唯一识别码格式有误！请重新输入！\nPUUID wasn't in UUID format! Please try again!")
                else:
                    print("您输入的召唤师名称格式有误！请重新输入！\nERROR format of summoner name! Please try again!")
            if "errorCode" in info and info["httpStatus"] == 404:
                if search_by_puuid:
                    print("未找到玩家通用唯一识别码为" + summoner_name + "的玩家；请核对识别码并稍后再试。\nA player with puuid " + summoner_name + " was not found; verify the puuid and try again.")
                else:
                    print("未找到" + summoner_name + "；请核对下名字并稍后再试。\n" + summoner_name + " was not found; verify the name and try again.")
            elif "errorCode" in info and info["httpStatus"] == 422:
                print('召唤师名称已变更为拳头ID。请以“{召唤师名称}#{尾标}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"]))
                continue
            elif "accountId" in info:
                displayName = info["displayName"] #用于扫描模式定位到某召唤师（Determines the directory which contains the summoner's data）
                current_puuid = info["puuid"] #用于核验对局是否包含该召唤师。此外，还用于扫描模式从对局的所有玩家信息中定位到该玩家（For use of checking whether the searched matches include this summoner. In addition, it's used for localization of this player from all players in a match in "scan" mode）
                #下面设置扫描模式的扫描目录（The following code determines the scanning directory for scan mode）
                riot_client_info = await (await connection.request("GET", "/riotclient/command-line-args")).json()
                client_info = {}
                for i in range(len(riot_client_info)):
                    try:
                        client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
                    except IndexError:
                        pass
                region = client_info["--region"]
                if region == "TENCENT":
                    folder = "召唤师信息（Summoner Information）\\" + platform[region] + "\\" + platform_TENCENT[client_info["--rso_platform_id"]] + "\\" + displayName
                elif region == "GARENA":
                    folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[region] + "\\" + displayName
                else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
                    folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[region] + "\\" + displayName
                #print("召唤师英雄联盟对局记录如下：\nLoL match history is as follows:")
                LoLHistory_get = True
                begIndex_get, endIndex_get = 0, 500
                while True:
                    try:
                        LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches?begIndex=%d&endIndex=%d" %(info["puuid"], begIndex_get, endIndex_get))).json()
                        #print(LoLHistory)
                        error_occurred = False
                        count = 0 #存储内部服务器错误次数（Stores the times of internal server error）
                        if "errorCode" in LoLHistory:
                            if "500 Internal Server Error" in LoLHistory["message"]:
                                if error_occurred == False:
                                    print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                    occurred = True
                                while "errorCode" in LoLHistory and "500 Internal Server Error" in LoLHistory["message"] and count <= 3: #在查询艾欧尼亚和黑色玫瑰大区的对局记录时，有时会产生如下报错：An error when looking up match history on HN1 and HN10 servers might occur as follows: {'errorCode': 'RPC_ERROR', 'httpStatus': 500, 'implementationDetails': {}, 'message': 'Failed due to Error deserializing json response for GET https: //hn1-cloud-acs.lol.qq.com/v1/stats/player_history/HN1/2936900903?begIndex=0&endIndex=500: Error: Invalid value. at offset 0. given body <html>\r\n<head><title>500 Internal Server Error</title></head>\r\n<body bgcolor="white">\r\n<center><h1>500 Internal Server Error</h1></center>\r\n<hr><center>nginx/1.10.0</center>\r\n</body>\r\n</html>\r\n'}
                                    count += 1
                                    print("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                                    LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches?begIndex=%d&endIndex=%d" %(info["puuid"], begIndex_get, endIndex_get))).json()
                            elif "body was empty" in LoLHistory["message"]:
                                LoLHistory_get = False
                                print("这位召唤师从5月1日起就没有进行过英雄联盟任何对局。\nThis summoner hasn't played any LoL game yet since May 1st.")
                                break
                        if count > 3:
                            LoLHistory_get = False
                            print("对局记录获取失败！请等待官方修复对局记录服务！\nMatch history capture failure! Please wait for Tencent to fix the match history service!")
                            break
                        print('该玩家共进行%d场对局。\nThis player has played %d matches.\n' %(LoLHistory["games"]["gameCount"], LoLHistory["games"]["gameCount"]))
                    except KeyError:
                        print(LoLHistory)
                        LoLHistory_url = "%s/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=200" %(connection.address, info["puuid"])
                        print("请打开以下网址，输入如下所示的用户名和密码如下，打开后在命令行中按回车键继续（Please open the following website, type in the username and password accordingly and press Enter to continue）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和上限。\nOr submit two nonnegative integers split by space to respecify the begIndex and endIndex." %(LoLHistory_url, connection.auth_key))
                        cont = input()
                        if cont == "":
                            continue
                        else:
                            try:
                                begIndex_get, endIndex_get = map(int, cont.split())
                            except ValueError:
                                LoLHistory_get = False
                                break
                            else:
                                continue
                    else:
                        break
                if not LoLHistory_get:
                    continue
                LoLHistory_header = {"gameIndex": "游戏序号", "summonerName": "召唤师名称", "gameID": "对局序号", "gameCreationDate": "创建日期", "gameDuration": "持续时长", "queueID": "队列序号", "gameMode": "游戏模式", "gameModeName": "模式名称", "mapID": "地图序号", "gameVersion": "对局版本", "champion": "英雄", "alias": "名字", "level": "等级", "spell1": "召唤师技能1", "spell2": "召唤师技能2", "item1": "装备1", "item2": "装备2", "item3": "装备3", "item4": "装备4", "item5": "装备5", "item6": "装备6", "ornament": "饰品", "KDA": "战损比", "CS": "补刀", "goldEarned": "金币", "result": "结果"}
                LoLGamePlayed = True #标记该玩家是否进行过英雄联盟对局（Mark whether this summoner has played any LoL game）
                #初始化数据框（Initialize dataframe）
                gameIndex = []
                summonerName = []
                gameID = []
                gameCreationDate = []
                gameDuration = []
                queueID = []
                gameMode = []
                gameModeName = []
                mapID = []
                gameVersion = []
                versions = [] #该变量并不是用来呈现在Excel中的，而是用来存储不同装备的合适版本的信息（This variable isn't intended to be displyed in the Excel Sheets. Instead, it stores information of appropriate patches of different patches）
                champion = []
                alias = []
                level = []
                spell1 = []
                spell2 = []
                item1 = []
                item2 = []
                item3 = []
                item4 = []
                item5 = []
                item6 = []
                ornament = []
                KDA = []
                CS = []
                goldEarned = []
                result = []
                
                #开始赋值（Begin assignment）
                games = LoLHistory["games"]["games"]
                for i in list(range(len(games))):
                    try:
                        game = games[i]
                    except IndexError: #用户近期对局数量可能小于20（The summoner's recent matches may be less than 20）
                        break
                    except KeyError:
                        LoLGamePlayed = False
                        print("这位召唤师从5月1日起就没有进行过任何英雄联盟对局。\nThis summoner hasn't played any LoL game yet since May 1st.")
                        break
                    gameIndex.append(i + 1)
                    #获取游戏序号（Capture gameId）
                    gameID.append(game["gameId"])
                    #获取当前召唤师名称（Capture current summonerName）
                    summonerName.append(game["participantIdentities"][0]["player"]["summonerName"])
                    #获取游戏开始时间（Capture gameCreationDate）
                    gameCreationDate.append(game["gameCreationDate"][:10] + " " + game["gameCreationDate"][11:23])
                    #获取游戏持续时长（Capture gameDuration）
                    duration = game["gameDuration"]
                    gameDuration.append(str(duration // 60) + ":" + "%02d" %(duration % 60))
                    #获取队列序号和模式名称（Capture queueID and name of the mode）
                    queueID.append(game["queueId"])
                    if game["queueId"] == 0:
                        gameMode.append("CUSTOM")
                        gameModeName.append("自定义")
                    else:
                        gameMode.append(game["gameMode"])
                        gameModeName.append(gamemodes[game["queueId"]]["name"])
                    #获取地图序号（Capture mapID）
                    mapID.append(game["mapId"])
                    #获取对局版本号（Capture version）
                    version = game["gameVersion"]
                    gameVersion.append(version)
                    version_digits = version.split(".")
                    bigVersion = ".".join(version_digits[:2])
                    try:
                        versions.append(patches_dict[bigVersion][0])
                    except KeyError: #有可能存在美测服的临时版本未收录到DataDragon数据库中。详见patch_compare函数的注释（Possibly an intermediate patch on PBE isn't archived in DataDragon database. More details in the annotation of `patch_compare` function）
                        if patch_compare(bigVersion, latest_patch):
                            patches_dict[bigVersion] = [FindPostPatch(version, patches)]
                        else:
                            patches_dict[bigVersion] = [latest_patch]
                        versions.append(patches_dict[bigVersion][0])
                    #获取英雄信息（Capture champion）
                    try:
                        champion.append(LoLChampions[game["participants"][0]["championId"]]["name"])
                    except KeyError: #在国服体验服的对局序号为696083511的对局中，出现了英雄序号为37225015（In a match with matchId 696083511 on Chinese PBE, there's a champion with championId 37225015）
                        champion.append("")
                    try:
                        alias.append(LoLChampions[game["participants"][0]["championId"]]["alias"])
                    except KeyError:
                        alias.append(game["participants"][0]["championId"])
                    level.append(game["participants"][0]["stats"]["champLevel"])
                    #获取召唤师技能1和2（Capture spell 1 and 2）
                    spell1Id = game["participants"][0]["spell1Id"]
                    spell2Id = game["participants"][0]["spell2Id"]
                    try:
                        spellId = spell1Id
                        test = spells[spellId]["name"]
                        spellId = spell2Id
                        test = spells[spellId]["name"]
                    except KeyError: #在国服体验服的对局序号为696083511的对局中，出现了召唤师技能序号为37225015和4964（In a match with matchId 696083511 on Chinese PBE, there're two spells with spellIds 37225015 and 4964）
                        spellPatch_adopted = bigVersion
                        spell_recapture = 1
                        print("第%d/%d场对局（对局序号：%s）召唤师技能信息（%s）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%s) of Match %d / %d (matchID: %s) capture failed! Changing to spells of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], spellId, spell_recapture, spellPatch_adopted, spellId, i + 1, len(games), game["gameId"], spellPatch_adopted, spell_recapture))
                        while True:
                            try:
                                spell = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[language_code])).json()
                            except requests.exceptions.JSONDecodeError:
                                spellPatch_deserted = spellPatch_adopted
                                spellPatch_adopted = FindPostPatch(spellPatch_adopted, bigPatches)
                                spell_recapture = 1
                                print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture))
                            except requests.exceptions.RequestException:
                                if spell_recapture < 3:
                                    spell_recapture += 1
                                    print("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Changing to spells of Patch %s ... Times tried: %d." %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture))
                                else:
                                    print("网络环境异常！第%d/%d场对局（对局序号：%s）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchID: %s)!" %(i + 1, len(games), game["gameId"], spellId, spellId, i + 1, len(games), game["gameId"]))
                                    spell1.append(game["participants"][0]["spell1Id"])
                                    break
                            else:
                                print("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted))
                                spells = {}
                                for spell_iter in spell:
                                    spell_id = spell_iter.pop("id")
                                    spells[spell_id] = spell_iter
                                try:
                                    spell1.append(spells[game["participants"][0]["spell1Id"]]["name"])
                                except KeyError:
                                    print("【%d. %s】第%d/%d场对局（对局序号：%s）召唤师技能信息（%s）获取失败！将采用原始数据！\n[%d. %s] Spell information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(i, key, i + 1, len(games), game["gameId"], spellId, i, key, spellId, i + 1, len(games), game["gameId"]))
                                    spell1.append(game["participants"][0]["spell1Id"])
                                    break
                                else:
                                    break
                    try:
                        spell1.append(spells[game["participants"][0]["spell1Id"]]["name"])
                    except KeyError:
                        spell1.append(game["participants"][0]["spell1Id"])
                    try:
                        spell2.append(spells[game["participants"][0]["spell2Id"]]["name"])
                    except KeyError:
                        spell2.append(game["participants"][0]["spell2Id"])
                    #获取召唤师装备信息（Capture summoner items）
                    stats = game["participants"][0]["stats"]
                    item1Id = stats["item0"]
                    item2Id = stats["item1"]
                    item3Id = stats["item2"]
                    item4Id = stats["item3"]
                    item5Id = stats["item4"]
                    item6Id = stats["item5"]
                    ornamentId = stats["item6"]
                    try: #部分装备可能为老版本装备，在新版本中没有数据。如12.21版本的炉火冠饰在12.23版本中被删除（Some items may be of old versions so that they're deleted in newer versions, e.g. Forgefire Crest in 12.21 deleted in 12.22 and later versions）
                        if item1Id != 0:
                            LoLItemID = item1Id
                            test = LoLItems[str(item1Id)]["name"]
                        if item2Id != 0:
                            LoLItemID = item2Id
                            test = LoLItems[str(item2Id)]["name"]
                        if item3Id != 0:
                            LoLItemID = item3Id
                            test = LoLItems[str(item3Id)]["name"]
                        if item4Id != 0:
                            LoLItemID = item4Id
                            test = LoLItems[str(item4Id)]["name"]
                        if item5Id != 0:
                            LoLItemID = item5Id
                            test = LoLItems[str(item5Id)]["name"]
                        if item6Id != 0:
                            LoLItemID = item6Id
                            test = LoLItems[str(item6Id)]["name"]
                        if ornamentId != 0:
                            LoLItemID = ornamentId
                            test = LoLItems[str(ornamentId)]["name"]
                    except KeyError:
                        LoLItemPatch_adopted = bigVersion
                        LoLItem_recapture = 1
                        print("第%d/%d场对局（对局序号：%s）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%s) of Match %d / %d (matchID: %s) capture failed! Changing to LoL items of Patch %s ... Times tried: %d." %(i + 1, len(games), game["gameId"], LoLItemID, LoLItem_recapture, LoLItemPatch_adopted, LoLItemID, i + 1, len(games), game["gameId"], LoLItemPatch_adopted, LoLItem_recapture))
                        while True:
                            try:
                                LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                            except requests.exceptions.JSONDecodeError:
                                LoLItemPatch_deserted = LoLItemPatch_adopted
                                LoLItemPatch_adopted = FindPostPatch(LoLItemPatch_adopted, bigPatches)
                                LoLItem_recapture = 1
                                print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                            except requests.exceptions.RequestException:
                                if LoLItem_recapture < 3:
                                    LoLItem_recapture += 1
                                    print("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Changing to LoL items of Patch %s ... Times tried: %d." %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
                                else:
                                    print("网络环境异常！第%d/%d场对局（对局序号：%s）的装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the item (%s) of Match %d / %d (matchID: %s)!" %(i + 1, len(games), game["gameId"], LoLItemID, LoLItemID, i + 1, len(games), game["gameId"]))
                                    break
                            else:
                                print("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted))
                                LoLItems = {}
                                for LoLItem_iter in LoLItem:
                                    LoLItem_id = LoLItem_iter.pop("id")
                                    LoLItems[str(LoLItem_id)] = LoLItem_iter
                                break
                    if item1Id == 0:
                        item1.append("")
                    else:
                        try:
                            item1.append(LoLItems[str(item1Id)]["name"])
                        except KeyError:
                            item1.append(str(item1Id))
                    if item2Id == 0:
                        item2.append("")
                    else:
                        try:
                            item2.append(LoLItems[str(item2Id)]["name"])
                        except KeyError:
                            item2.append(str(item2Id))
                    if item3Id == 0:
                        item3.append("")
                    else:
                        try:
                            item3.append(LoLItems[str(item3Id)]["name"])
                        except KeyError:
                            item3.append(str(item3Id))
                    if item4Id == 0:
                        item4.append("")
                    else:
                        try:
                            item4.append(LoLItems[str(item4Id)]["name"])
                        except KeyError:
                            item4.append(str(item4Id))
                    if item5Id == 0:
                        item5.append("")
                    else:
                        try:
                            item5.append(LoLItems[str(item5Id)]["name"])
                        except KeyError:
                            item5.append(str(item5Id))
                    if item6Id == 0:
                        item6.append("")
                    else:
                        try:
                            item6.append(LoLItems[str(item6Id)]["name"])
                        except KeyError:
                            item6.append(str(item6Id))
                    if ornamentId == 0:
                        ornament.append("")
                    else:
                        try:
                            ornament.append(LoLItems[str(ornamentId)]["name"])
                        except KeyError:
                            ornament.append(str(ornamentId))
                    #获取战损比（Capture K/D/A）
                    KDA.append("/".join([str(stats["kills"]), str(stats["deaths"]), str(stats["assists"])]))
                    #获取补刀数（Capture the creep score）
                    CS.append(stats["neutralMinionsKilled"] + stats["totalMinionsKilled"])
                    goldEarned.append(stats["goldEarned"])
                    #获取对局结果（Capture the match result）
                    if stats["win"]:
                        result.append("胜利")
                    else:
                        result.append("失败")
                LoLHistory_data = {}
                for i in list(LoLHistory_header.keys()):
                    LoLHistory_data[i] = [LoLHistory_header[i]] + eval(i) #因为这里要用到eval，所以前面的变量名必须和LoLHistory_header中的键保持一致（Since eval() is used here, those lists variable name must correspond to variable LoLHistory_header's keys）
                LoLHistory_df = pandas.DataFrame(data = LoLHistory_data)
                #LoLHistory_df.apply(lambda x: pandas.Series([-3], index = ["K/D/A"]))
                if LoLGamePlayed:
                    print(LoLHistory_df[:min(21, len(gameIndex) + 1)])
                
                #下面获取最近一起玩过的英雄联盟玩家的信息（The following code captures the recently played LoL players' information）
                if detectMode:
                    print('请输入要查询的对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出程序请输入“0”：\nPlease enter the match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to exit the program.')
                else:
                    print('请输入要查询的对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，切换召唤师请输入“0”：\nPlease enter the match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to switch for next summoner.')
                while True:
                    matchID = input()
                    if matchID == "":
                        continue
                    elif matchID == "0":
                        break
                    else:
                        if matchID == "3":
                            print("请设置需要查询的对局索引下界和上界，以空格为分隔符（输入空字符以默认查询近20场对局）：\nPlease set the begIndex and endIndex of the matches to be searched, split by space (Enter an empty string to search for the recent 20 matches):") #在13.13版本以前，腾讯代理的服务器只支持近20场对局查询（Before Patch 13.13, Tencent servers only provide search of the latest 20 matches）
                            while True:
                                gameIndex = input()
                                if gameIndex == "":
                                    begIndex, endIndex = 0, 20
                                elif gameIndex == "0":
                                    break
                                else:
                                    try:
                                        begIndex, endIndex = map(int, gameIndex.split())
                                    except ValueError:
                                        print("请以空格为分隔符输入对局索引的自然数类型的下界和上界！\nPlease enter the two nonnegative integers as the begIndex and endIndex of the matches split by space!")
                                        continue
                                break
                            if gameIndex == "0":
                                break
                            LoLMatchIDs = list(map(str, gameID[begIndex:endIndex]))
                        elif matchID == "scan":
                            LoLMatchIDs = []
                            filenames = os.listdir(folder)
                            for filename in filenames:
                                if filename.startswith("Match Information (LoL) - "):
                                    LoLMatchIDs.append(filename.split("-")[-1].split(".")[0])
                            if LoLMatchIDs == list():
                                print("尚未保存过该玩家的数据！\nYou haven't saved this summoner's matches yet!\n")
                                break
                            else:
                                LoLMatchIDs = list(map(int, set(LoLMatchIDs))) #正确的对局顺序应当是根据整型对局序号的大小来排列的（The correct order of matches should be according to based on the order of LoLMatchIDs of integer type）
                                LoLMatchIDs.sort(reverse = True)
                                LoLMatchIDs = list(map(str, LoLMatchIDs))
                                print("检测到%d场对局。是否继续？（输入任意键以重新输入要查询的对局序号，否则重新获取这些对局的数据）\nDetected %d matches. Continue? (Input any nonempty string to return to the last step of inputting the matchID, or null to recapture those matches' data)" %(len(LoLMatchIDs), len(LoLMatchIDs)))
                                recapture = input()
                                if recapture != "":
                                    LoLMatchIDs = [] #如果没有这句语句，那么当重新输入对局序号列表时，从本地文件中检测到的对局数量相比上次检测数的基础上会多出本地文件中包含的对局的数量（Without this assignment, when reinputting the matchID list, the number of matches detected from the local files will become more than that of the last time's check）
                                    print('请输入要查询的对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，切换召唤师请输入“0”：\nPlease enter the match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to switch for next summoner.')
                                    continue
                                #在沿用查生涯脚本时，后续对局记录重新生成的代码不再需要了。因为这只是查召唤师信息的脚本，不是查对局记录的脚本（When inheritting code from Customized Program 5, the following code to regenerate match history is no longer needed. That's because this program is just designed to search for recently played summoners, rather than sort out match history）
                        else:
                            try:
                                matchID = eval(matchID)
                                LoLMatchIDs = []
                                if isinstance(matchID, int):
                                    LoLMatchIDs.append(str(matchID))
                                elif isinstance(matchID, list):
                                    for match in matchID:
                                        if isinstance(match, int):
                                            LoLMatchIDs.append(str(match))
                                if len(LoLMatchIDs) == 0:
                                    print("您输入的对局序号集不合法！请重新输入。\nThe matchID set you've input is illegal! Please try again.")
                                    continue
                            except SyntaxError:
                                print("您的输入存在语法错误。请重新输入！\nSyntax ERROR detected in this input! Please try again!")
                                continue
                        #开始获取各对局内的玩家信息。数据结构参考/lol-match-history/v1/recently-played-summoners（Begin to capture the players' information in each match. The data structure can be referred to "/lol-match-history/v1/recently-played-summoners"）
                        ##首先定义存储玩家信息的数据框的数据结构（First, define the data structure of the dataframe that stores player information）
                        LoLGame_info_header = {"gameCreationDate": "创建日期", "gameDuration": "持续时长", "gameId": "对局序号", "gameMode": "游戏模式", "gameModeName": "模式名称", "gameVersion": "对局版本", "mapId": "地图序号", "queueId": "队列序号", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "champion": "英雄", "alias": "名字", "spell1": "召唤师技能1", "spell2": "召唤师技能2", "KDA": "战损比", "assists": "助攻", "causedEarlySurrender": "发起提前投降", "champLevel": "英雄等级", "combatPlayerScore": "战斗得分", "damageDealtToObjectives": "对战略点的总伤害", "damageDealtToTurrets": "对防御塔的总伤害", "damageSelfMitigated": "自我缓和的伤害", "deaths": "死亡", "doubleKills": "双杀", "earlySurrenderAccomplice": "同意提前投降", "firstBloodAssist": "协助获得第一滴血", "firstBloodKill": "第一滴血", "firstInhibitorAssist": "协助摧毁第一座召唤水晶", "firstInhibitorKill": "摧毁第一座召唤水晶", "firstTowerAssist": "协助摧毁第一座塔", "firstTowerKill": "摧毁第一座塔", "gameEndedInEarlySurrender": "提前投降导致比赛结束", "gameEndedInSurrender": "投降导致比赛结束", "goldEarned": "金币获取", "goldSpent": "金币使用", "inhibitorKills": "摧毁召唤水晶", "item1": "装备1", "item2": "装备2", "item3": "装备3", "item4": "装备4", "item5": "装备5", "item6": "装备6", "ornament": "饰品", "killingSprees": "大杀特杀", "kills": "击杀", "largestCriticalStrike": "最大暴击伤害", "largestKillingSpree": "最高连杀", "largestMultiKill": "最高多杀", "longestTimeSpentLiving": "最长生存时间", "magicDamageDealt": "造成的魔法伤害", "magicDamageDealtToChampions": "对英雄的魔法伤害", "magicalDamageTaken": "承受的魔法伤害", "neutralMinionsKilled": "击杀野怪", "neutralMinionsKilledEnemyJungle": "击杀敌方野区野怪", "neutralMinionsKilledTeamJungle": "击杀我方野区野怪", "objectivePlayerScore": "战略点玩家得分", "pentaKills": "五杀", "perk0": "符文1", "perk0EndOfGameStatDescs": "符文1游戏结算数据", "perk0Var1": "符文1：参数1", "perk0Var2": "符文1：参数2", "perk0Var3": "符文1：参数3", "perk1": "符文2", "perk1EndOfGameStatDescs": "符文2游戏结算数据", "perk1Var1": "符文2：参数1", "perk1Var2": "符文2：参数2", "perk1Var3": "符文2：参数3", "perk2": "符文3", "perk2EndOfGameStatDescs": "符文3游戏结算数据", "perk2Var1": "符文3：参数1", "perk2Var2": "符文3：参数2", "perk2Var3": "符文3：参数3", "perk3": "符文4", "perk3EndOfGameStatDescs": "符文4游戏结算数据", "perk3Var1": "符文4：参数1", "perk3Var2": "符文4：参数2", "perk3Var3": "符文4：参数3", "perk4": "符文5", "perk4EndOfGameStatDescs": "符文5游戏结算数据", "perk4Var1": "符文5：参数1", "perk4Var2": "符文5：参数2", "perk4Var3": "符文5：参数3", "perk5": "符文6", "perk5EndOfGameStatDescs": "符文6游戏结算数据", "perk5Var1": "符文6：参数1", "perk5Var2": "符文6：参数2", "perk5Var3": "符文6：参数3", "perkPrimaryStyle": "主系", "perkSubStyle": "副系", "physicalDamageDealt": "造成的物理伤害", "physicalDamageDealtToChampions": "对英雄的物理伤害", "physicalDamageTaken": "承受的物理伤害", "playerAugment1": "强化符文1", "playerAugment1_rarity": "强化符文1等级", "playerAugment2": "强化符文2", "playerAugment2_rarity": "强化符文2等级", "playerAugment3": "强化符文3", "playerAugment3_rarity": "强化符文3等级", "playerAugment4": "强化符文4", "playerAugment4_rarity": "强化符文4等级", "playerScore0": "玩家得分1", "playerScore1": "玩家得分2", "playerScore2": "玩家得分3", "playerScore3": "玩家得分4", "playerScore4": "玩家得分5", "playerScore5": "玩家得分6", "playerScore6": "玩家得分7", "playerScore7": "玩家得分8", "playerScore8": "玩家得分9", "playerScore9": "玩家得分10", "playerSubteamId": "子阵营序号", "quadraKills": "四杀", "sightWardsBoughtInGame": "购买洞察之石", "subteamPlacement": "队伍排名", "teamEarlySurrendered": "队伍提前投降", "timeCCingOthers": "控制得分", "totalDamageDealt": "造成的伤害总和", "totalDamageDealtToChampions": "对英雄的伤害总和", "totalDamageTaken": "承受伤害", "totalHeal": "治疗伤害", "totalMinionsKilled": "击杀小兵", "totalPlayerScore": "玩家总得分", "totalScoreRank": "总得分排名", "totalTimeCrowdControlDealt": "控制时间", "totalUnitsHealed": "治疗单位数", "tripleKills": "三杀", "trueDamageDealt": "造成真实伤害", "trueDamageDealtToChampions": "对英雄的真实伤害", "trueDamageTaken": "承受的真实伤害", "turretKills": "摧毁防御塔", "unrealKills": "六杀及以上", "visionScore": "视野得分", "visionWardsBoughtInGame": "购买控制守卫", "wardsKilled": "摧毁守卫", "wardsPlaced": "放置守卫", "win/lose": "胜负", "ally?": "是否队友？"}
                        LoLGame_info_data = {}
                        LoLGame_info_header_keys = list(LoLGame_info_header.keys())
                        fetched_info = False #用于控制程序走向，防止在没有获取到任何对局信息的情况下程序进入可视化部分（Used to control the running of the program, in case the program enters visualization part without fetching any match information）
                        error_LoLMatchIDs = [] #记录实际存在但未如期获取的对局序号（Records the LoL matchIDs that really exist but fail to be fetched）
                        matches_to_remove = [] #记录获取成功但不包含主玩家的对局序号（Records the matches that are fetched successfully but don't contain the main player）
                        LoLGameDuration_raw = [] #用于存储未转化成几分几秒格式的游戏持续时间。主要是为了方便可视化时呈现不同玩家的累计游戏时间的图表（Used to store the gameDuration that is not transformed into "(X)X:XX" form. Mainly for convenience of displaying the chart regarding the total time for which a player has accompanied the main player）
                        subteam_color = {0: "", 1: "魄罗", 2: "小兵", 3: "迅捷蟹", 4: "石甲虫"} #仅用于斗魂竞技场（Only for Soul Fighter mode）
                        augment_rarity = {0: "白银", 4: "黄金", 8: "棱彩"}
                        win = {True: "胜利", False: "失败"}
                        spells = copy.deepcopy(spells_initial)
                        LoLItems = copy.deepcopy(LoLItems_initial) #接下来查询具体的对局信息和时间轴，使用的可能并不是历史记录中记载的对局序号形成的列表。考虑实际使用需求，这里对于装备的合适版本信息采取的思路是默认从最新版本开始获取，如果有装备不存在于最新版本的装备信息，则获取游戏信息中存储的版本对应的装备信息。该思路仍然有问题，详见后续关于美测服的装备获取的注释（The next step is to capture the information and timeline for each specific match, which may not originate from the matchIDs recorded in the match history. Considering the practical use, here the stream of thought for an appropriate version for items is to get items' information from the latest patch, and if some item doesn't exist in the items information of the latest patch, then get the items of the version corresponding to the game according to gameVersion recorded in the match information. There's a flaw of this idea. Please refer to the annotation regarding PBE data crawling for further solution）
                        for key in LoLGame_info_header_keys:
                            LoLGame_info_data[key] = []
                        for matchID in LoLMatchIDs:
                            LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                            #print(LoLGame_info)
                            
                            #尝试修复错误（Try to fix the error）
                            if "errorCode" in LoLGame_info:
                                count = 0
                                if LoLGame_info["httpStatus"] == 404:
                                    print("未找到序号为" + matchID + "的回放文件！将忽略该序号。\nMatch file with matchID " + matchID + " not found! The program will ignore this matchID.")
                                    continue
                                if "500 Internal Server Error" in LoLGame_info["message"]:
                                    if error_occurred == False:
                                        print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                        error_occurred = True
                                    while "errorCode" in LoLGame_info and "500 Internal Server Error" in LoLGame_info["message"] and count <= 3:
                                        count += 1
                                        print("正在第%d次尝试获取对局%s信息……\nTimes trying to capture Match %s: No. %d ..." %(count, matchID, matchID, count))
                                        LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                                elif "Connection timed out after " in LoLGame_info["message"]:
                                    print("对局信息保存超时！请检查网速状况！\nGame information saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                                elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"]:
                                    if error_occurred == False:
                                        print("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                                        error_occurred = True
                                    while "errorCode" in LoLGame_info and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"] and count <= 3:
                                        count += 1
                                        print("正在第%d次尝试获取对局%s信息……\nTimes trying to capture Match %s: No. %d ..." %(count, matchID, matchID, count))
                                        LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                                if count > 3:
                                    print("对局%s信息获取失败！\nMatch %s information capture failure!" %(matchID, matchID))
                            
                            if "errorCode" in LoLGame_info:
                                print(LoLGame_info, end = "\n\n")
                                error_LoLMatchIDs.append(matchID)
                            else:
                                #判断对局序号列表中的对局是否包含主玩家（Judges whether the matches in the matchID list contain the main player）
                                participant = []
                                for i in LoLGame_info["participantIdentities"]:
                                    participant.append(i["player"]["puuid"])
                                if current_puuid in participant: #之所以使用玩家通用唯一识别码，而不是用召唤师名称来识别对局是否包含主玩家，是因为该玩家可能使用过改名卡。这里也没有选择帐户序号，这是因为保存在对局中的各玩家的帐户序号竟然是0！（The reason why the puuid instead of the displayName or summonerName is used to identify whether the matches contain the main player is that the player may have used name changing card. AccountId isn't chosen here, because all players' accountIds saved in the match fetched from 127 API is 0, to my surprise!）
                                    for currentParticipantId in range(len(LoLGame_info["participantIdentities"])): #定位主召唤师（Find the index of the main player in a match）
                                        if LoLGame_info["participantIdentities"][currentParticipantId]["player"]["puuid"] == current_puuid:
                                            break
                                    for i in range(len(LoLGame_info["participants"])): #开始整理数据（Begin to sort out the data）
                                        if LoLGame_info["participantIdentities"][i]["player"]["puuid"] != "00000000-0000-0000-0000-000000000000" and LoLGame_info["participantIdentities"][i]["player"]["puuid"] != current_puuid: #统计玩家，当然指的是不包括自己的人类玩家（Of course, the players counted are human players but not himself / herself）
                                            stats = LoLGame_info["participants"][i]["stats"]
                                            for j in range(len(LoLGame_info_header_keys)):
                                                key = LoLGame_info_header_keys[j]
                                                if j == 0:
                                                    LoLGame_info_data[key].append(LoLGame_info["gameCreationDate"][:10] + " " + LoLGame_info["gameCreationDate"][11:23])
                                                elif j == 1:
                                                    duration = LoLGame_info["gameDuration"]
                                                    LoLGameDuration_raw.append(duration)
                                                    LoLGame_info_data[key].append("%s:%02d" %(str(duration // 60), duration % 60))
                                                elif j in {2, 5, 6, 7}:
                                                    LoLGame_info_data[key].append(LoLGame_info[key])
                                                elif j == 3:
                                                    if LoLGame_info["queueId"] == 0:
                                                        LoLGame_info_data[key].append("CUSTOM")
                                                    else:
                                                        LoLGame_info_data[key].append(LoLGame_info["gameMode"])
                                                elif j == 4:
                                                    if LoLGame_info["queueId"] == 0:
                                                        LoLGame_info_data[key].append("自定义")
                                                    else:
                                                        LoLGame_info_data[key].append(gamemodes[LoLGame_info["queueId"]]["name"])
                                                elif j in {8, 9, 10}:
                                                    LoLGame_info_data[key].append(LoLGame_info["participantIdentities"][i]["player"][key])
                                                elif j in {11, 12}:
                                                    championID = LoLGame_info["participants"][i]["championId"]
                                                    if j == 11:
                                                        LoLGame_info_data[key].append(LoLChampions[championID]["name"])
                                                    else:
                                                        LoLGame_info_data[key].append(LoLChampions[championID]["alias"])
                                                elif j in {13, 14}:
                                                    spellId = LoLGame_info["participants"][i][key + "Id"]
                                                    try:
                                                        LoLGame_info_data[key].append(spells[spellId]["name"])
                                                    except KeyError:
                                                        LoLGame_info_data[key].append(spellId)
                                                elif j == 15:
                                                    kill, death, assist = stats["kills"], stats["deaths"], stats["assists"]
                                                    LoLGame_info_data[key].append("%d/%d/%d" %(kill, death, assist))
                                                elif j >= 37 and j <= 43:
                                                    if j >= 37 and j <= 43:
                                                        LoLItemID = stats["item%d" %(j - 37)]
                                                    else:
                                                        LoLItemID = stats["item6"]
                                                    if LoLItemID == 0:
                                                        LoLGame_info_data[key].append("")
                                                    else:
                                                        try: #当爬取美测服新版本的数据时，新装备往往没有收录在Datadragon中，从而引起KeyError报错。解决措施是以装备序号代替装备名称（When crawling data of new version on PBE, new items are never collected in the latest Datadragon archive, which results in KeyError. Here the solution is to substitute the items' names by the LoLItemIDs）
                                                            LoLGame_info_data[key].append(LoLItems[str(LoLItemID)]["name"])
                                                        except KeyError:
                                                            LoLGame_info_data[key].append(str(LoLItemID))
                                                elif j >= 58 and j <= 89:
                                                    if j <= 87:
                                                        if (j - 58) % 5 == 0 or (j - 58) % 5 == 1:
                                                            subkey = LoLGame_info_header_keys[58 + (j - 58) // 5 * 5]
                                                            perkId = LoLGame_info["participants"][i]["stats"][subkey]
                                                            if perkId == 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                                                LoLGame_info_data[key].append("")
                                                            else:
                                                                perk_captured = True
                                                                try:
                                                                    perk_to_append = perks[perkId] #这里并没有直接使用to_append作为要追加的数据。这是考虑到游戏结算数据需要依赖符文的正确获取。如果符文数据没有从CommunityDragon数据库中如期获取，那么也无法整理得到游戏结算数据。所以这里退而求其次，先检查对局信息中的符文序号是否存在于准备好的符文数据中，如果不存在则按照类似的错误修复机制重新获取符文数据。如果最终的符文数据包含对局信息中的符文序号，那么符文的名称和游戏结算数据可以正常追加。否则，符文的名称将被符文序号代替，而游戏结算数据将被空字符串代替（Here the variable `to_append` isn't used as the data to be appended. This is based on the consideration that EndOfGameStatDescs depends on the successful capture of runes. If runes data aren't fetched as expected from CommunityDragon database, then the EndOfGameStatDescs data can't be concluded, either. Therefore, this line of code seeks for the second best: first check if perkId is in the prepared runes data and then handle the exception if not. If the final runes data contain the perkId, then the name and EndOfGameStatDescs of a perk can be appended. Otherwise, the name and EndOfGameStatDescs of a perk is to be replaced by the perkId and an empty string, respectively）
                                                                except KeyError:
                                                                    perkPatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                                    perk_recapture = 1
                                                                    print("第%d/%d场对局（对局序号：%s）基石符文信息（%s）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nRunes information (%s) of Match %d / %d (matchID: %s) capture failed! Changing to runes of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkId, perk_recapture, perkPatch_adopted, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkPatch_adopted, perk_recapture))
                                                                    while True:
                                                                        try:
                                                                            perk = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[language_code])).json()
                                                                        except requests.exceptions.JSONDecodeError:
                                                                            perkPatch_deserted = perkPatch_adopted
                                                                            perkPatch_adopted = FindPostPatch(perkPatch_adopted, bigPatches)
                                                                            perk_recapture = 1
                                                                            print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to runes of Patch %s ... Times tried: %d." %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture))
                                                                        except requests.exceptions.RequestException:
                                                                            if perk_recapture < 3:
                                                                                perk_recapture += 1
                                                                                print("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Changing to runes of Patch %s ... Times tried: %d." %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture))
                                                                            else:
                                                                                print("网络环境异常！第%d/%d场对局（对局序号：%s）的基石符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the runes (%s) of Match %d / %d (matchID: %s)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkId, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                                perk_captured = False
                                                                                break
                                                                        else:
                                                                            print("已改用%s版本的基石符文信息。\nRunes information changed to Patch %s." %(perkPatch_adopted, perkPatch_adopted))
                                                                            perks = {}
                                                                            for perk_iter in perk:
                                                                                perk_id = perk_iter.pop("id")
                                                                                perks[perk_id] = perk_iter
                                                                            try:
                                                                                perk_to_append = perks[perkId]
                                                                            except KeyError:
                                                                                print("【%d. %s】第%d/%d场对局（对局序号：%s）基石符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] Runes information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkId, j, key, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                                perk_captured = False
                                                                                break
                                                                            else:
                                                                                break
                                                                if perk_captured:
                                                                    if (j - 58) % 5 == 0:
                                                                        to_append = perk_to_append["name"]
                                                                    else:
                                                                        perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perk_to_append["endOfGameStatDescs"])))
                                                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(LoLGame_info["participants"][i]["stats"][LoLGame_info_header_keys[j + 1]]))
                                                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(LoLGame_info["participants"][i]["stats"][LoLGame_info_header_keys[j + 2]]))
                                                                        perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(LoLGame_info["participants"][i]["stats"][LoLGame_info_header_keys[j + 3]]))
                                                                        to_append = perk_EndOfGameStatDescs
                                                                else:
                                                                    to_append = perkId if (j - 58) % 5 == 0 else ""
                                                                LoLGame_info_data[key].append(to_append)
                                                        else:
                                                            LoLGame_info_data[key].append(LoLGame_info["participants"][i]["stats"][key])
                                                    else:
                                                        subkey = LoLGame_info["participants"][i]["stats"][key]
                                                        if subkey == 0:
                                                            LoLGame_info_data[key].append("")
                                                        else:
                                                            try:
                                                                to_append = perkstyles[subkey]["name"]
                                                            except KeyError:
                                                                perkstylePatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                                perkstyle_recapture = 1
                                                                print("第%d/%d场对局（对局序号：%s）符文系信息（%s）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%s) of Match %d / %d (matchID: %s) capture failed! Changing to perkstyles of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, subkey, perkstyle_recapture, perkstylePatch_adopted, subkey, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkstylePatch_adopted, perkstyle_recapture))
                                                                while True:
                                                                    try:
                                                                        perkstyle = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[language_code])).json()
                                                                    except requests.exceptions.JSONDecodeError:
                                                                        perkstylePatch_deserted = perkstylePatch_adopted
                                                                        perkstylePatch_adopted = FindPostPatch(perkstylePatch_adopted, bigPatches)
                                                                        perkstyle_recapture = 1
                                                                        print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to perkstyles of Patch %s ... Times tried: %d." %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture))
                                                                    except requests.exceptions.RequestException:
                                                                        if perkstyle_recapture < 3:
                                                                            perkstyle_recapture += 1
                                                                            print("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Changing to runes styles of Patch %s ... Times tried: %d." %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture))
                                                                        else:
                                                                            print("网络环境异常！第%d/%d场对局（对局序号：%s）的符文系信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the perkstyles (%s) of Match %d / %d (matchID: %s)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, subkey, subkey, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                            to_append = subkey
                                                                            break
                                                                    else:
                                                                        print("已改用%s版本的符文系信息。\nPerkstyle information changed to Patch %s." %(perkstylePatch_adopted, perkstylePatch_adopted))
                                                                        perkstyles = {}
                                                                        for perkstyle_iter in perkstyle["styles"]:
                                                                            perkstyle_id = perkstyle_iter.pop("id")
                                                                            perkstyles[perkstyle_id] = perkstyle_iter
                                                                        try:
                                                                            to_append = perkstyles[subkey]["name"]
                                                                        except KeyError:
                                                                            print("【%d. %s】第%d/%d场对局（对局序号：%s）符文系信息（%s）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, subkey, j, key, subkey, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                            to_append = subkey
                                                                            break
                                                                        else:
                                                                            break
                                                            LoLGame_info_data[key].append(to_append)
                                                elif j >= 93 and j <= 100: #此处处理方法同上——退而求其次（Here the principle is similar to the above: seek for the second best）
                                                    subkey = LoLGame_info_header_keys[93 + (j - 93) // 2 * 2]
                                                    playerAugmentId = LoLGame_info["participants"][i]["stats"][subkey]
                                                    if playerAugmentId == 0:
                                                        LoLGame_info_data[key].append("")
                                                    else:
                                                        ArenaAugment_captured = True
                                                        try:
                                                            augment_to_append = ArenaAugments[playerAugmentId]
                                                        except KeyError:
                                                            ArenaPatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                            Arena_recapture = 1
                                                            print("第%d/%d场对局（对局序号：%s）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nArena augment information (%s) of Match %d / %d (matchID: %s) capture failed! Changing to Arena augments of Patch %s ... Times tried: %d." %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, playerAugmentId, Arena_recapture, ArenaPatch_adopted, playerAugmentId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, ArenaPatch_adopted, Arena_recapture))
                                                            while True:
                                                                try:
                                                                    Arena = requests.get("https://raw.communitydragon.org/%s/cdragon/arena/%s.json" %(ArenaPatch_adopted, language_cdragon[language_code])).json()
                                                                except requests.exceptions.JSONDecodeError:
                                                                    ArenaPatch_deserted = ArenaPatch_adopted
                                                                    ArenaPatch_adopted = FindPostPatch(ArenaPatch_adopted, bigPatches)
                                                                    Arena_recapture = 1
                                                                    print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to Arena augments of Patch %s ... Times tried: %d." %(ArenaPatch_deserted, Arena_recapture, ArenaPatch_adopted, ArenaPatch_deserted, ArenaPatch_adopted, Arena_recapture))
                                                                except requests.exceptions.RequestException:
                                                                    if Arena_recapture < 3:
                                                                        Arena_recapture += 1
                                                                        print("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Changing to Arena augments of Patch %s ... Times tried: %d." %(Arena_recapture, ArenaPatch_adopted, ArenaPatch_adopted, Arena_recapture))
                                                                    else:
                                                                        print("网络环境异常！第%d/%d场对局（对局序号：%s）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the Arena augments (%s) of Match %d / %d (matchID: %s)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, playerAugmentId, playerAugmentId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                        ArenaAugment_captured = False
                                                                        break
                                                                else:
                                                                    print("已改用%s版本的斗魂竞技场强化符文信息。\nArena augment information changed to Patch %s." %(ArenaPatch_adopted, ArenaPatch_adopted))
                                                                    ArenaAugments = {}
                                                                    for ArenaAugment in Arena["augments"]:
                                                                        ArenaAugment_id = ArenaAugment.pop("id")
                                                                        ArenaAugments[ArenaAugment_id] = ArenaAugment
                                                                    try:
                                                                        augment_to_append = ArenaAugments[playerAugmentId]
                                                                    except KeyError:
                                                                        print("【%d. %s】第%d/%d场对局（对局序号：%s）强化符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] Arena augment information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(j, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, playerAugmentId, j, key, playerAugmentId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                        ArenaAugment_captured = False
                                                                        break
                                                                    else:
                                                                        break
                                                        if ArenaAugment_captured:
                                                            to_append = augment_to_append["name"] if (j - 93) % 2 == 0 else augment_rarity[augment_to_append["rarity"]]
                                                        else:
                                                            to_append = playerAugmentId if (j - 93) % 2 == 0 else ""
                                                        LoLGame_info_data[key].append(to_append)
                                                elif j == 111:
                                                    LoLGame_info_data[key].append(subteam_color[LoLGame_info["participants"][i]["stats"]["playerSubteamId"]])
                                                elif j == 136:
                                                    LoLGame_info_data[key].append(win[LoLGame_info["participants"][i]["stats"]["win"]])
                                                elif j == 137:
                                                    if LoLGame_info["participants"][i]["teamId"] == LoLGame_info["participants"][currentParticipantId]["teamId"] and stats["playerSubteamId"] == LoLGame_info["participants"][currentParticipantId]["stats"]["playerSubteamId"]:
                                                        LoLGame_info_data[key].append(True)
                                                    else:
                                                        LoLGame_info_data[key].append(False)
                                                else:
                                                    LoLGame_info_data[key].append(stats[key])
                                    fetched_info = True
                                    print("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %s" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                else:
                                    matches_to_remove.append(matchID)
                                    print("对局%s不包含主玩家。已舍弃该对局。\nMatch %s doesn't contain the main player. Abandoned this match." %(matchID, matchID))

                        if not fetched_info:
                            print("未获取到有效对局。请重新输入要查询的对局序号。\nThe program didn't fetch any valid match. Please reinput the match ID to check.")
                            continue
                        recent_LoLPlayers_statistics_display_order = [10, 9, 8, 2, 0, 1, 7, 3, 4, 6, 5, 137, 11, 12, 18, 13, 14, 37, 38, 39, 40, 41, 42, 43, 93, 94, 95, 96, 97, 98, 99, 100, 15, 19, 122, 123, 47, 44, 48, 27, 26, 31, 30, 29, 28, 24, 126, 112, 57, 131, 116, 124, 118, 91, 51, 128, 117, 90, 50, 127, 46, 21, 20, 120, 125, 119, 92, 52, 129, 22, 132, 135, 134, 113, 133, 34, 35, 121, 53, 55, 54, 130, 36, 49, 88, 89, 58, 59, 63, 64, 68, 69, 73, 74, 78, 79, 83, 84, 17, 25, 115, 32, 33, 136]
                        recent_LoLPlayers_data_organized = {}
                        for i in range(len(recent_LoLPlayers_statistics_display_order)):
                            key = LoLGame_info_header_keys[recent_LoLPlayers_statistics_display_order[i]]
                            recent_LoLPlayers_data_organized[key] = [LoLGame_info_header[key]] + LoLGame_info_data[key]
                            #print("近期一起玩过的英雄联盟玩家数据重排进度（Rearranging process of recently played summoner (LoL) data）：%d/%d" %(i + 1, len(recent_LoLPlayers_statistics_display_order)))
                        #print("正在创建数据框……\nCreating the dataframe ...")
                        recent_LoLPlayers_df = pandas.DataFrame(data = recent_LoLPlayers_data_organized)
                        #print("数据框创建完成！\nDataframe creation finished!")
                        print("正在优化逻辑值显示……\nOptimizing the display of boolean values ...")
                        for i in range(recent_LoLPlayers_df.shape[0]): #这里直接使用replace函数会把整数类型的0和1当成逻辑值替换（Here function "replace" will unexpectedly take effects on 0s and 1s of integer type）
                            for j in range(recent_LoLPlayers_df.shape[1]):
                                if str(recent_LoLPlayers_df.iat[i, j]) == "True":
                                    recent_LoLPlayers_df.iat[i, j] = "√"
                                elif str(recent_LoLPlayers_df.iat[i, j]) == "False":
                                    recent_LoLPlayers_df.iat[i, j] = ""
                        print("逻辑值显示优化完成！\nBoolean value display optimization finished!")
                        
                        #下面获取最近一起玩过的云顶之弈玩家的信息（The following code captures the recently played TFT players' information）
                        print("是否查询云顶之弈对局记录？（输入任意键查询，否则不查询）\nSearch TFT matches? (Input anything to search or null to export data or switch for another summoner)")
                        search_TFT = input()
                        if search_TFT != "":
                            print("请设置需要查询的对局索引下界和对局数，以空格为分隔符（输入空字符以默认查询近20场对局）：\nPlease set the begin and count of the matches to be searched, split by space (Enter an empty string to search for the recent 20 matches):")
                            while True:
                                gameIndex = input()
                                if gameIndex == "":
                                    begin_get, count_get = 0, 20
                                elif gameIndex == "0":
                                    break
                                else:
                                    try:
                                        begin_get, count_get = map(int, gameIndex.split())
                                    except ValueError:
                                        print("请以空格为分隔符输入自然数类型的对局索引下界和对局数！\nPlease enter the two nonnegative integers as the begin and count of the matches split by space!")
                                        continue
                                break
                            if gameIndex == "0":
                                break
                            print("正在加载云顶之弈对局信息……\nLoading TFT match information ...")
                            TFTHistory_get = True
                            while True:
                                try:
                                    TFTHistory = await (await connection.request("GET", "/lol-match-history/v1/products/tft/%s/matches?begin=%d&count=%d" %(info["puuid"], begin_get, count_get))).json()
                                    #print(TFTHistory)
                                    count = 0 #存储内部服务器错误次数（Stores the times of internal server error）
                                    if "errorCode" in TFTHistory:
                                        if "500 Internal Server Error" in TFTHistory["message"]:
                                            if error_occurred == False:
                                                print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                                occurred = True
                                            while "errorCode" in TFTHistory and "500 Internal Server Error" in TFTHistory["message"] and count <= 3:
                                                count += 1
                                                print("正在进行第%d次尝试……\nTimes trying: No. %d ..." %(count, count))
                                                TFTHistory = await (await connection.request("GET", "/lol-match-history/v1/products/tft/%s/matches?begin=%d&count=%d" %(info["puuid"], begin_get, count_get))).json()
                                    currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                                    pkl5name = "Intermediate Object - TFTHistory - %s (%s).pkl" %(displayName, currentTime)
                                    #with open(os.path.join(folder, pkl5name), "wb") as IntObj5:
                                        #pickle.dump(TFTHistory, IntObj5)
                                    if count > 3:
                                        TFTHistory_get = False
                                        print("云顶之弈对局记录获取失败！请等待官方修复对局记录服务！\TFT match history capture failure! Please wait for Tencent to fix the match history service!")
                                        break
                                except KeyError:
                                    if "errorCode" in TFTHistory:
                                        print(TFTHistory)
                                        TFTHistory_url = "%s/lol-match-history/v1/products/tft/%s/matches?begin=0&count=200" %(connection.address, info["puuid"])
                                        print("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续，或输入任意字符以切换召唤师（Please open the following website, type in the username and password accordingly and press Enter to continue or input anything to switch to another summoner）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s\n或者输入空格分隔的两个自然数以重新指定对局索引下限和对局数。\nOr submit two nonnegative integers split by space to respecify the begin and count." %(TFTHistory_url, connection.auth_key))
                                        cont = input()
                                        if cont == "":
                                            continue
                                        else:
                                            try:
                                                begin_get, count_get = map(int, cont.split())
                                            except ValueError:
                                                TFTHistory_get = False
                                                break
                                            else:
                                                continue
                                else:
                                    break
                            if not TFTHistory_get:
                                continue
                            TFTHistory = TFTHistory["games"]
                            TFTHistory_header = {"gameIndex": "游戏序号", "game_datetime": "创建日期", "game_id": "对局序号", "game_length": "持续时长", "game_version": "对局版本", "queue_id": "队列序号", "tft_game_type": "游戏类型", "tft_set_core_name": "数据版本名称", "tft_set_number": "赛季", "participantId": "玩家序号", "augment1": "强化符文1", "augment2": "强化符文2", "augment3": "强化符文3", "companion": "小小英雄", "companion_level": "小小英雄星级", "companion_rarity": "小小英雄稀有度", "gold_left": "剩余金币", "last_round": "存活回合", "level": "等级", "placement": "名次", "players_eliminated": "淘汰玩家数", "puuid": "玩家通用唯一识别码", "summonerName": "召唤师名称", "summonerId": "召唤师序号", "time_eliminated": "存活时长", "total_damage_to_players": "造成玩家伤害", "trait0 name": "羁绊1", "trait0 num_units": "羁绊1单位数", "trait0 style": "羁绊1羁绊框颜色", "trait0 tier_current": "羁绊1当前等级", "trait0 tier_total": "羁绊1最高等级", "trait1 name": "羁绊2", "trait1 num_units": "羁绊2单位数", "trait1 style": "羁绊2羁绊框颜色", "trait1 tier_current": "羁绊2当前等级", "trait1 tier_total": "羁绊2最高等级", "trait2 name": "羁绊3", "trait2 num_units": "羁绊3单位数", "trait2 style": "羁绊3羁绊框颜色", "trait2 tier_current": "羁绊3当前等级", "trait2 tier_total": "羁绊3最高等级", "trait3 name": "羁绊4", "trait3 num_units": "羁绊4单位数", "trait3 style": "羁绊4羁绊框颜色", "trait3 tier_current": "羁绊4当前等级", "trait3 tier_total": "羁绊4最高等级", "trait4 name": "羁绊5", "trait4 num_units": "羁绊5单位数", "trait4 style": "羁绊5羁绊框颜色", "trait4 tier_current": "羁绊5当前等级", "trait4 tier_total": "羁绊5最高等级", "trait5 name": "羁绊6", "trait5 num_units": "羁绊6单位数", "trait5 style": "羁绊6羁绊框颜色", "trait5 tier_current": "羁绊6当前等级", "trait5 tier_total": "羁绊6最高等级", "trait6 name": "羁绊7", "trait6 num_units": "羁绊7单位数", "trait6 style": "羁绊7羁绊框颜色", "trait6 tier_current": "羁绊7当前等级", "trait6 tier_total": "羁绊7最高等级", "trait7 name": "羁绊8", "trait7 num_units": "羁绊8单位数", "trait7 style": "羁绊8羁绊框颜色", "trait7 tier_current": "羁绊8当前等级", "trait7 tier_total": "羁绊8最高等级", "trait8 name": "羁绊9", "trait8 num_units": "羁绊9单位数", "trait8 style": "羁绊9羁绊框颜色", "trait8 tier_current": "羁绊9当前等级", "trait8 tier_total": "羁绊9最高等级", "trait9 name": "羁绊10", "trait9 num_units": "羁绊10单位数", "trait9 style": "羁绊10羁绊框颜色", "trait9 tier_current": "羁绊10当前等级", "trait9 tier_total": "羁绊10最高等级", "trait10 name": "羁绊11", "trait10 num_units": "羁绊11单位数", "trait10 style": "羁绊11羁绊框颜色", "trait10 tier_current": "羁绊11当前等级", "trait10 tier_total": "羁绊11最高等级", "trait11 name": "羁绊12", "trait11 num_units": "羁绊12单位数", "trait11 style": "羁绊12羁绊框颜色", "trait11 tier_current": "羁绊12当前等级", "trait11 tier_total": "羁绊12最高等级", "trait12 name": "羁绊13", "trait12 num_units": "羁绊13单位数", "trait12 style": "羁绊13羁绊框颜色", "trait12 tier_current": "羁绊13当前等级", "trait12 tier_total": "羁绊13最高等级", "unit0 character": "英雄1", "unit0 rarity": "英雄1：稀有度", "unit0 tier": "英雄1：星级", "unit1 character": "英雄2", "unit1 rarity": "英雄2：稀有度", "unit1 tier": "英雄2：星级", "unit2 character": "英雄3", "unit2 rarity": "英雄3：稀有度", "unit2 tier": "英雄3：星级", "unit3 character": "英雄4", "unit3 rarity": "英雄4：稀有度", "unit3 tier": "英雄4：星级", "unit4 character": "英雄5", "unit4 rarity": "英雄5：稀有度", "unit4 tier": "英雄5：星级", "unit5 character": "英雄6", "unit5 rarity": "英雄6：稀有度", "unit5 tier": "英雄6：星级", "unit6 character": "英雄7", "unit6 rarity": "英雄7：稀有度", "unit6 tier": "英雄7：星级", "unit7 character": "英雄8", "unit7 rarity": "英雄8：稀有度", "unit7 tier": "英雄8：星级", "unit8 character": "英雄9", "unit8 rarity": "英雄9：稀有度", "unit8 tier": "英雄9：星级", "unit9 character": "英雄10", "unit9 rarity": "英雄10：稀有度", "unit9 tier": "英雄10：星级", "unit10 character": "英雄11", "unit10 rarity": "英雄11：稀有度", "unit11 tier": "英雄11：星级", "unit0 item0": "英雄1：装备1", "unit0 item1": "英雄1：装备2", "unit0 item2": "英雄1：装备3", "unit1 item0": "英雄2：装备1", "unit1 item1": "英雄2：装备2", "unit1 item2": "英雄2：装备3", "unit2 item0": "英雄3：装备1", "unit2 item1": "英雄3：装备2", "unit2 item2": "英雄3：装备3", "unit3 item0": "英雄4：装备1", "unit3 item1": "英雄4：装备2", "unit3 item2": "英雄4：装备3", "unit4 item0": "英雄5：装备1", "unit4 item1": "英雄5：装备2", "unit4 item2": "英雄5：装备3", "unit5 item0": "英雄6：装备1", "unit5 item1": "英雄6：装备2", "unit5 item2": "英雄6：装备3", "unit6 item0": "英雄7：装备1", "unit6 item1": "英雄7：装备2", "unit6 item2": "英雄7：装备3", "unit7 item0": "英雄8：装备1", "unit7 item1": "英雄8：装备2", "unit7 item2": "英雄8：装备3", "unit8 item0": "英雄9：装备1", "unit8 item1": "英雄9：装备2", "unit8 item2": "英雄9：装备3", "unit9 item0": "英雄10：装备1", "unit9 item1": "英雄10：装备2", "unit9 item2": "英雄10：装备3", "unit10 item0": "英雄11：装备1", "unit10 item1": "英雄11：装备2", "unit10 item2": "英雄11：装备3"}
                            TFTHistory_data = {}
                            TFTHistory_header_keys = list(TFTHistory_header.keys())
                            traitStyles = {0: "", 1: "青铜", 2: "白银", 3: "黄金", 4: "炫金", 5: "独行"}
                            rarity = {"Default": "经典", "NoRarity": "其它", "Epic": "史诗", "Legendary": "传说", "Mythic": "神话", "Rare": "稀有", "Ultimate": "终极"}
                            TFTGamePlayed = len(TFTHistory) != 0 #标记该玩家是否进行过云顶之弈对局（Mark whether this summoner has played any TFT game）
                            TFT_main_player_indices = [] #云顶之弈对局记录中记录了所有玩家的数据，但是在历史记录的工作表中只要显示主召唤师的数据，因此必须知道每场对局中主召唤师的索引（Each match in TFT history records all players' data, but only the main player's data are needed to display in the match history worksheet, so the index of the main player in each match is necessary）
                            version_re = re.compile("\d*\.\d*\.\d*\.\d*") #云顶之弈的对局版本信息是一串字符串，从中识别四位对局版本（TFT match version is a long string, from which the 4-number version is identified）
                            TFTGamePatches = [] #这里设定小版本号，以便后续切换云顶之弈相关数据的版本（Here a shorter patch is extracted, in case TFT data version needs changing）
                            TFTGameDuration_raw = []
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
                            for i in range(len(TFTHistory_header)): #各项目初始化（Initialize every feature / column）
                                key = TFTHistory_header_keys[i]
                                TFTHistory_data[key] = []
                            for i in range(len(TFTHistory)): #由于不同对局意味着不同版本，不同版本的云顶之弈数据相差较大，所以为了使得一次获取的版本能够尽可能用到多个对局中，第一层迭代器应当是对局序号（Because different matches mean different patches, and TFT data differ greatly among different patches, to make a recently captured version of TFT data applicable in as more matches as possible, the first iterator should be the ID of the matches）
                                if TFT_main_player_indices[i] == -1: #对局数据记录存在异常时的处理（Exception of match data recording exception）
                                    TFTGamePatches.append("") #后面的代码中存在对TFTGamePatches的索引，因此为了保证索引的准确性，当对局记录出现异常时，应当追加一个空版本号到版本列表中（There're indices of `TFTGamePatches`. Therefore, to ensure the correctness of the indices, an empty patch should be appended to this patch list）
                                    for j in range(len(TFTHistory_header)):
                                        key = TFTHistory_header_keys[j]
                                        if j == 0:
                                            TFTHistory_data[key].append(i + 1)
                                        elif j == 1:
                                            game_datetime = TFTHistory[i]["metadata"]["timestamp"]
                                            game_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(game_datetime // 1000))
                                            game_date_fraction = game_datetime / 1000 - game_datetime // 1000
                                            to_append = game_date + ("{0:.3}".format(game_date_fraction))[1:5]
                                            TFTHistory_data[key].append(to_append)
                                        elif j == 2:
                                            TFTHistory_data[key].append(TFTHistory[i]["metadata"]["match_id"].split("_")[1])
                                        elif j == 3:
                                            TFTGameDuration_raw.append(0)
                                        else:
                                            TFTHistory_data[key].append("")
                                    print("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： Unknown" %(i + 1, len(TFTHistory)))
                                else:
                                    TFTHistoryJson = TFTHistory[i]["json"] #该数据结构应用于1 ≤ j ≤ 8（This variable applies when 1 ≤ j ≤ 8）
                                    #j == 1
                                    game_datetime = int(TFTHistoryJson["game_datetime"])
                                    game_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(game_datetime // 1000))
                                    game_date_fraction = game_datetime / 1000 - game_datetime // 1000
                                    #j == 4
                                    TFTGameVersion = version_re.search(TFTHistoryJson["game_version"]).group()
                                    TFTGamePatch = ".".join(TFTGameVersion.split(".")[:2])
                                    for j in range(len(TFTHistory_header)):
                                        key = TFTHistory_header_keys[j]
                                        if j == 0:
                                            for k in range(len(TFTHistory[i]["metadata"]["participants"])): #这里选择遍历元数据子字典中的玩家，而不是json子字典中的玩家，是因为前者不会包含电脑玩家的玩家通用唯一识别码，而后者会。显然，统计最近一起玩过的玩家数据不应当包含电脑玩家（Here the for-loop traverses the participants saved in the "metadata" sub-dictionary instead of the "json" sub-dictionary. This is becasue puuid of bot players isn't included in the former dictionary, but included in the latter dictionary. Obviously, they shouldn't counted as a recently played summoner）
                                                if TFTHistory[i]["json"]["participants"][k]["puuid"] != current_puuid:
                                                    TFTHistory_data[key].append(i + 1)
                                        elif j >= 1 and j <= 8:
                                            for k in range(len(TFTHistory[i]["metadata"]["participants"])):
                                                if TFTHistory[i]["json"]["participants"][k]["puuid"] != current_puuid:
                                                    if j == 1:
                                                        to_append = game_date + ("{0:.3}".format(game_date_fraction))[1:5]
                                                        TFTHistory_data[key].append(to_append)
                                                    elif j in {2, 5, 7}:
                                                        try:
                                                            TFTHistory_data[key].append(TFTHistoryJson[key])
                                                        except KeyError: #在云顶之弈第7赛季之前，TFTHistoryJson中无tft_set_core_name这一键（Before TFTSet7, tft_set_core_name isn't present as a key of `TFTHistoryJson`）
                                                            TFTHistory_data[key].append("")
                                                    elif j == 3:
                                                        TFTGameDuration_raw.append(TFTHistoryJson["game_length"])
                                                        TFTHistory_data[key].append("%d:%02d" %(int(TFTHistoryJson["game_length"]) // 60, int(TFTHistoryJson["game_length"]) % 60))
                                                    elif j == 4:
                                                        TFTHistory_data[key].append(TFTGameVersion)
                                                        TFTGamePatches.append(TFTGamePatch)
                                                    else:
                                                        if not key in TFTHistoryJson.keys() or TFTHistoryJson[key] == "standard": #在云顶之弈第4赛季及以前，TFTHistoryJson中无tft_game_type键（Before (and including) TFT set 4, the key `tft_game_type` is absent from `TFTHistoryJson`）
                                                            if "normal" in TFTHistory[i]["metadata"]["tags"]:
                                                                TFTHistory_data[key].append("匹配模式")
                                                            elif "ranked" in TFTHistory[i]["metadata"]["tags"]:
                                                                TFTHistory_data[key].append("排位")
                                                        elif TFTHistoryJson[key] == "turbo":
                                                            TFTHistory_data[key].append("狂暴模式")
                                                        elif TFTHistoryJson[key] == "pairs":
                                                            TFTHistory_data[key].append("双人作战")
                                                        elif TFTHistoryJson[key] == "tutorial":
                                                            TFTHistory_data[key].append("新手教程")
                                                        else:
                                                            TFTHistory_data[key].append(TFTHistoryJson[key])
                                        elif j >= 9 and j <= 25: #对于一些容易产生争议和报错的情况，引入to_append变量以简化代码。下同（Variable `to_append` is introduced to simplify the code in case of some controversy that produces errors easily. So does the following）
                                            #TFTMainPlayer = TFTHistory[i]["json"]["participants"][TFT_main_player_indices[i]]
                                            for k in range(len(TFTHistory[i]["metadata"]["participants"])): #注意这里遍历对象和查战绩脚本的区别。实际上相当于判断玩家是不是人类玩家（Pay attention to the difference between this piece of code and the corresponding code in Customized Program 5. Actually this line of code judges whether a player is human player）
                                                TFTPlayer = TFTHistory[i]["json"]["participants"][k]
                                                if j == 9:
                                                    if TFTPlayer["puuid"] != current_puuid: #注意这里获取的是其它玩家的信息（Note that this program captures other players' information）
                                                        TFTHistory_data[key].append(k + 1)
                                                elif j >= 10 and j <= 12: #以下的try-except语句的思想适用于整个数据整理阶段（The principle of the following try-except statements applies to the whole data sorting period）
                                                    if not "augments" in TFTPlayer:
                                                        if TFTPlayer["puuid"] != current_puuid: #此处条件判断可优化为k == TFT_main_player_indices[i]（Here the judgment can be optimized into `k == TFT_main_player_indices`）
                                                            TFTHistory_data[key].append("")
                                                        continue
                                                    try: #如果下面的语句没有报错，那么最新版本的数据将保存到工作表中（If the following statement doesn't generate an exception, then the latest data will be saved into the worksheet）
                                                        to_append = TFTAugments[TFTPlayer["augments"][j - 10]]["name"]
                                                    except KeyError:
                                                        TFTAugmentPatch_adopted = TFTGamePatch
                                                        TFTAugment_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%d）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nTFT augment information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT augments of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer["augments"][j - 10], TFTAugment_recapture, TFTAugmentPatch_adopted, TFTPlayer["augments"][j - 10], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTAugmentPatch_adopted, TFTAugment_recapture))
                                                        while True:
                                                            try:
                                                                TFT = requests.get("https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError: #存在版本合并更新的情况（Situation like merged update exists）
                                                                TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                                                TFTAugmentPatch_adopted = FindPostPatch(TFTAugmentPatch_adopted, bigPatches)
                                                                TFTAugment_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture))
                                                            except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                                                if TFTAugment_recapture < 3:
                                                                    TFTAugment_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Changing to TFT augments of Patch %s ... Times tried: %d." %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture))
                                                                else:
                                                                    print("网络环境异常！第%d/%d场对局（对局序号：%d）的强化符文信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the augment (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer["augments"][j - 10], TFTPlayer["augments"][j - 10], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                    to_append = TFTPlayer["augments"][j - 10]
                                                                    break
                                                            else:
                                                                print("已改用%s版本的云顶之弈强化符文信息。\nTFT augment information changed to Patch %s." %(TFTAugmentPatch_adopted, TFTAugmentPatch_adopted))
                                                                TFTAugments = {}
                                                                for item in TFT["items"]:
                                                                    item_apiName = item.pop("apiName")
                                                                    TFTAugments[item_apiName] = item
                                                                try: #如果下面的语句没有报错，那么对局版本的数据将保存到工作表中（If the following statement doesn't generate an exception, then data of corresponding version will be saved into the worksheet）
                                                                    to_append = TFTAugments[TFTPlayer["augments"][j - 10]]["name"]
                                                                except KeyError: #如果找不到键，那么暂时先将原始数据导入工作表中（If the key still can't be found, then temporarily export the initial data into the worksheet）
                                                                    print("【%d. %s】第%d/%d场对局（对局序号：%d）强化符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT augment information (%s) of Match %d / %d (matchID: %d) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer["augments"][j - 10], j, key, TFTPlayer["augments"][j - 10], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                    to_append = TFTPlayer["augments"][j - 10]
                                                                    break
                                                                else:
                                                                    break
                                                    except IndexError: #有的时候玩家不一定选了3个强化符文（Sometimes a player might choose less than 3 augments）
                                                        to_append = ""
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append(to_append)
                                                elif j >= 13 and j <= 15:
                                                    contentId = TFTPlayer["companion"]["content_ID"]
                                                    try:
                                                        TFTCompanion_iter = TFTCompanions[contentId]
                                                    except KeyError:
                                                        TFTCompanionPatch_adopted = TFTGamePatch
                                                        TFTCompanion_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%d）小小英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的小小英雄信息……\nTFT companion information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT companions of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], contentId, TFTCompanion_recapture, TFTCompanionPatch_adopted, contentId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                                        while True:
                                                            try:
                                                                TFTCompanion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(TFTCompanionPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError:
                                                                TFTCompanionPatch_deserted = TFTCompanionPatch_adopted
                                                                TFTCompanionPatch_adopted = FindPostPatch(TFTCompanionPatch_adopted, bigPatches)
                                                                TFTCompanion_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTCompanionPatch_deserted, TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_deserted, TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                                            except requests.exceptions.RequestException:
                                                                if TFTCompanion_recapture < 3:
                                                                    TFTCompanion_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的小小英雄信息……\nYour network environment is abnormal! Changing to TFT companions of Patch %s ... Times tried: %d." %(TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                                                else:
                                                                    print("网络环境异常！第%d/%d场对局（对局序号：%d）的小小英雄信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the companion (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], contentId, contentId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                    to_append = {13: contentId, 14: "", 15: ""}
                                                                    break
                                                            else:
                                                                print("已改用%s版本的小小英雄信息。\nTFT companion information changed to Patch %s." %(TFTCompanionPatch_adopted, TFTCompanionPatch_adopted))
                                                                TFTCompanions = {}
                                                                for companion_iter in TFTCompanion:
                                                                    contentId = companion_iter.pop("contentId")
                                                                    TFTCompanions[contentId] = companion_iter
                                                                try:
                                                                    TFTCompanion_iter = TFTCompanions[contentId]
                                                                except KeyError:
                                                                    print("【%d. %s】第%d/%d场对局（对局序号：%d）小小英雄信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT companion information (%s) of Match %d / %d (matchID: %d) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], contentId, j, key, contentId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                    to_append = {13: contentId, 14: "NA", 15: "NA"}
                                                                    break
                                                                else:
                                                                    to_append = {13: TFTCompanion_iter["name"], 14: TFTCompanion_iter["level"], 15: rarity[TFTCompanion_iter["rarity"]]}
                                                                    break
                                                    else:
                                                        to_append = {13: TFTCompanion_iter["name"], 14: TFTCompanion_iter["level"], 15: rarity[TFTCompanion_iter["rarity"]]}
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append(to_append[j])
                                                elif j == 17:
                                                    lastRound = TFTPlayer["last_round"]
                                                    if lastRound <= 3:
                                                        bigRound = 1
                                                        smallRound = lastRound
                                                    else:
                                                        bigRound = (lastRound + 3) // 7 + 1
                                                        smallRound = (lastRound + 3) % 7 + 1
                                                    to_append = "%d-%d" %(bigRound, smallRound)
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append(to_append)
                                                elif j == 22 or j == 23:
                                                    if TFTPlayer["puuid"] == "00000000-0000-0000-0000-000000000000": #在云顶之弈（新手教程）中，无法通过电脑玩家的玩家通用唯一识别码（00000000-0000-0000-0000-000000000000）来查询其召唤师名称和序号（Summoner names and IDs of bot players in TFT (Tutorial) can't be searched for according to their puuid: 00000000-0000-0000-0000-000000000000）
                                                        to_append = {22: "", 23: ""}
                                                    else:
                                                        TFTPlayer_info_recapture = 0
                                                        TFTPlayer_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + TFTPlayer["puuid"])).json()
                                                        while "errorCode" in TFTPlayer_info and TFTPlayer_info_recapture < 3:
                                                            TFTPlayer_info_recapture += 1
                                                            print("第%d/%d场对局（对局序号：%d）玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of Player (puuid: %s) in Match %d / %d (matchID: %d) capture failed! Recapturing this player's information ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer["puuid"], TFTPlayer_info_recapture, TFTPlayer["puuid"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_info_recapture))
                                                            TFTPlayer_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + TFTPlayer["puuid"])).json()
                                                        if "errorCode" in TFTPlayer:
                                                            to_append = {22: "", 23: ""}
                                                        else:
                                                            to_append = {22: TFTPlayer_info["displayName"], 23: TFTPlayer_info["summonerId"]}
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append(to_append[j])
                                                elif j == 24:
                                                    to_append = "%d:%02d" %(int(TFTPlayer["time_eliminated"]) // 60, int(TFTPlayer["time_eliminated"]) % 60)
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append(to_append)
                                                else:
                                                    to_append = TFTPlayer[key]
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append(to_append)
                                        elif j >= 26 and j <= 90:
                                            #TFTMainPlayer_Traits = TFTHistory[i]["json"]["participants"][TFT_main_player_indices[i]]["traits"]
                                            TFTTrait_iter, subkey = key.split(" ")
                                            for k in range(len(TFTHistory[i]["metadata"]["participants"])):
                                                TFTPlayer = TFTHistory[i]["json"]["participants"][k]
                                                TFTPlayer_Traits = TFTPlayer["traits"]
                                                TFTPlayer_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + TFTPlayer["puuid"])).json()
                                                if int(TFTTrait_iter[5:]) < len(TFTPlayer_Traits): #在这个小于的问题上纠结了很久[敲打]——下标是从0开始的。假设API上记录了n个羁绊，那么当程序正在获取第n个羁绊时，就会引起下标越界的问题。所以这里不能使用小于等于号（I stuck at this less than sign for long xD - note that the index begins from 0. Suppose there're totally n traits recorded in LCU API. Then, when the program is trying to capture the n-th trait, it'll throw an IndexError. That's why the less than or equal to sign can't be used here）
                                                    try:
                                                        if TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"] == "TemplateTrait": #CommunityDragon数据库中没有收录模板羁绊的数据（Data about TemplateTrait aren't archived in CommunityDragon database）
                                                            if (j - 26) % 5 == 4: #模板羁绊没有tier_total键（The key `tier_total` doesn't exist in "TemplateTrait" dictionary）
                                                                to_append == ""
                                                                print("警告：对局%d中玩家%s（玩家通用唯一识别码：%s）的第%d个羁绊是模板羁绊！\nWarning: Trait No. %d of the player %s (puuid: %s) in the match %d is TemplateTrait." %(TFTHistory[i]["json"]["game_id"], TFTPlayer_info["displayName"], TFTPlayer["puuid"], int(TFTTrait_iter[5:]) + 1, int(TFTTrait_iter[5:]) + 1, TFTPlayer_info["displayName"], TFTPlayer["puuid"], TFTHistory[i]["json"]["game_id"]))
                                                            else:
                                                                to_append == TFTPlayer_Traits[int(TFTTrait_iter[5:])][subkey]
                                                        else:
                                                            if (j - 26) % 5 == 0:
                                                                to_append = TFTTraits[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"]]["display_name"]
                                                            elif (j - 26) % 5 == 2:
                                                                #to_append = traitStyles[TFTTraits[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"]]["conditional_trait_sets"][TFTPlayer_Traits[int(TFTTrait_iter[5:])]["style"]]["style_name"]] #至于为什么前面traitStyles变量不直接用数字作为键，那是因为一旦用数字作为键，我的习惯是比较想知道是不是还有其它数字对应了某一种类型，就是说看上去不是特别舒服（As for why I don't take numbers as the keys of the dictionary variable `traitStyles`, if I do that, then I tend to wonder if there's some other number correspondent to some other type, that is, the program seems not so perfect and long-living）
                                                                to_append = traitStyles[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["style"]] #LCU API中记录的style和CommunityDragon数据库中记录的style_idx不是一个东西（`style` in LCU API and `style_idx` in CommunityDragon database aren't the same thing）
                                                            else:
                                                                to_append = TFTPlayer_Traits[int(TFTTrait_iter[5:])][subkey]
                                                    except KeyError:
                                                        TFTTraitPatch_adopted = TFTGamePatch
                                                        TFTTrait_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%d）羁绊信息（%s）获取失败！正在第%d次尝试改用%s版本的羁绊信息……\nTFT trait information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT traits of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], TFTTrait_recapture, TFTTraitPatch_adopted, TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTTraitPatch_adopted, TFTTrait_recapture))
                                                        while True:
                                                            try:
                                                                TFTTrait = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(TFTTraitPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError:
                                                                TFTTraitPatch_deserted = TFTTraitPatch_adopted
                                                                TFTTraitPatch_adopted = FindPostPatch(TFTTraitPatch_adopted, bigPatches)
                                                                TFTTrait_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTraitPatch_deserted, TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_deserted, TFTTraitPatch_adopted, TFTTrait_recapture))
                                                            except requests.exceptions.RequestException:
                                                                if TFTTrait_recapture < 3:
                                                                    TFTTrait_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的羁绊信息……\nYour network environment is abnormal! Changing to TFT traits of Patch %s ... Times tried: %d." %(TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_adopted, TFTTrait_recapture))
                                                                else:
                                                                    print("网络环境异常！第%d/%d场对局（对局序号：%d）的羁绊信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the trait (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                    to_append = TFTPlayer_Traits[int(TFTTrait_iter[5:])][subkey]
                                                                    break
                                                            else:
                                                                print("已改用%s版本的羁绊信息。\nTFT trait information changed to Patch %s." %(TFTTraitPatch_adopted, TFTTraitPatch_adopted))
                                                                TFTTraits = {}
                                                                for trait_iter in TFTTrait:
                                                                    trait_id = trait_iter.pop("trait_id")
                                                                    conditional_trait_sets = {}
                                                                    if "conditional_trait_sets" in trait_iter: #在英雄联盟第13赛季之前，CommunityDragon数据库中记录的羁绊信息无conditional_trait_sets项（Before Season 13, `conditional_trait_sets` item is absent from tfttraits from CommunityDragon database）
                                                                        for conditional_trait_set in trait_iter["conditional_trait_sets"]:
                                                                            style_idx = conditional_trait_set.pop("style_idx")
                                                                            conditional_trait_sets[style_idx] = conditional_trait_set
                                                                    trait_iter["conditional_trait_sets"] = conditional_trait_sets
                                                                    TFTTraits[trait_id] = trait_iter
                                                                try:
                                                                    if (j - 26) % 5 == 0:
                                                                        to_append = TFTTraits[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"]]["display_name"]
                                                                    elif (j - 26) % 5 == 2:
                                                                        to_append = traitStyles[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["style"]]
                                                                    else:
                                                                        to_append = TFTPlayer_Traits[int(TFTTrait_iter[5:])][subkey]
                                                                except KeyError:
                                                                    print("【%d. %s】第%d/%d场对局（对局序号：%d）羁绊信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT trait information (%s) of Match %d / %d (matchID: %d) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], j, key, TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                    try:
                                                                        to_append = TFTPlayer_Traits[int(TFTTrait_iter[5:])][subkey]
                                                                    except KeyError: #在艾欧尼亚的对局序号为4959597974的对局中，存在一个模板羁绊，没有tier_total这个键（There exists a TemplateTrait without the key `tier_total` in an Ionia match with matchID 4959597974）
                                                                        to_append = ""
                                                                    break
                                                                else:
                                                                    break
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append(to_append)
                                                else:
                                                    if TFTPlayer["puuid"] != current_puuid:
                                                        TFTHistory_data[key].append("")
                                        else:
                                            #TFTMainPlayer_Units = TFTHistory[i]["json"]["participants"][TFT_main_player_indices[i]]["units"]
                                            unit_iter, subkey = key.split(" ")
                                            for k in range(len(TFTHistory[i]["metadata"]["participants"])):
                                                TFTPlayer_Units = TFTHistory[i]["json"]["participants"][k]["units"]
                                                if j >= 91 and j <= 123:
                                                    if int(unit_iter[4:]) < len(TFTPlayer_Units):
                                                        if j % 3 == 1:
                                                            try:
                                                                to_append = TFTChampions[TFTPlayer_Units[int(unit_iter[4:])]["character_id"]]["display_name"]
                                                            except KeyError: #在获取艾欧尼亚对局序号为8390690410的英雄信息时，由于雷克塞的英雄序号大小写的原因，会引发键异常（KeyError is caused due to the case of "RekSai" string when the program is getting data from an Ionia match with matchID 8390690410）
                                                                try:
                                                                    subkey = list(TFTChampions.keys())[list(map(lambda x: x.lower(), list(TFTChampions.keys()))).index(TFTPlayer_Units[int(unit_iter[4:])]["character_id"].lower())] #该语句的原理是先将TFTChampions的所有键转换为小写，然后将LCU API中记录的character_id转换为小写，查询小写后的character_id在小写后的键列表中的索引。确定索引后，根据键列表和索引接下来字典要查询的键更换为原character_id对应大小写形式的键，供字典直接索引（The principle of this key is as follows. First, convert all keys of TFTChampions into lowercase. Second, convert `character_id` recorded in LCU API into lowercase. Third, search for `character_id` in lowercase in the key list whose keys are also converted into lowercase and determine the index. Fourth, once the index is determined, substitute the original key as the index of the dictionary variable `TFTChampions`, that is, `TFTPlayer_Units[int(unit_iter[4:])]["character_id"]`, with a new key that corresponds to the case of the original corresponding key, according to the key list and the index）
                                                                    to_append = TFTChampions[subkey]["display_name"]
                                                                except ValueError: #当在列表list(map(lambda x: x.lower(), list(TFTChampions.keys())))中查不到TFTPlayer_Units[int(unit_iter[4:])]["character_id"].lower()时，需要更换版本（When the champion with `character_id` `TFTPlayer_Units[int(unit_iter[4:])]["character_id"].lower()` isn't in the list `list(map(lambda x: x.lower(), list(TFTChampions.keys())))`, the data version needs to be changed）
                                                                    TFTChampionPatch_adopted = TFTGamePatch
                                                                    TFTChampion_recapture = 1
                                                                    print("第%d/%d场对局（对局序号：%d）英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的棋子信息……\nTFT champion (%s) information of Match %d / %d (matchID: %d) capture failed! Changing to TFT champions of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_Units[int(unit_iter[4:])]["character_id"], TFTChampion_recapture, TFTChampionPatch_adopted, TFTPlayer_Units[int(unit_iter[4:])]["character_id"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTChampionPatch_adopted, TFTChampion_recapture))
                                                                    while True:
                                                                        try:
                                                                            TFTChampion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(TFTChampionPatch_adopted, language_cdragon[language_code])).json()
                                                                        except requests.exceptions.JSONDecodeError:
                                                                            TFTChampionPatch_deserted = TFTChampionPatch_adopted
                                                                            TFTChampionPatch_adopted = FindPostPatch(TFTChampionPatch_adopted, bigPatches)
                                                                            TFTChampion_recapture = 1
                                                                            print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampionPatch_deserted, TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_deserted, TFTChampionPatch_adopted, TFTChampion_recapture))
                                                                        except requests.exceptions.RequestException:
                                                                            if TFTChampion_recapture < 3:
                                                                                TFTChampion_recapture += 1
                                                                                print("网络环境异常！正在第%d次尝试改用%s版本的棋子信息……\nYour network environment is abnormal! Changing to TFT champions of Patch %s ... Times tried: %d." %(TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_adopted, TFTChampion_recapture))
                                                                            else:
                                                                                print("网络环境异常！第%d/%d场对局（对局序号：%d）将采用原始数据！\nNetwork error! The original data will be used for Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                                to_append = TFTPlayer_Units[int(unit_iter[4:])]["character_id"]
                                                                                break
                                                                        else:
                                                                            print("已改用%s版本的棋子信息。\nTFT champion information changed to Patch %s." %(TFTChampionPatch_adopted, TFTChampionPatch_adopted))
                                                                            TFTChampions = {}
                                                                            if patch_compare(TFTChampionPatch_adopted, "13.17"): #从13.17版本开始，CommunityDragon数据库中关于云顶之弈小小英雄的数据格式发生微调（Since Patch 13.17, the format of TFT Champion data in CommunityDragon database has been modified）
                                                                                for TFTChampion_iter in TFTChampion:
                                                                                    champion_name = TFTChampion_iter.pop("character_id")
                                                                                    TFTChampions[champion_name] = TFTChampion_iter
                                                                            else:
                                                                                for TFTChampion_iter in TFTChampion:
                                                                                    champion_name = TFTChampion_iter.pop("name")
                                                                                    TFTChampions[champion_name] = TFTChampion_iter["character_record"] #请注意该语句与4行之前的语句的差异，并看看一开始准备数据文件时使用的是哪一种——其实你应该猜的出来（Have you noticed the difference between this statement and the statement that is 4 lines above from this statement? Also, check which statement I chose for the beginning, when I prepared the data resources. Actually, you should be able to speculate it without referring to the code）
                                                                            try:
                                                                                to_append = TFTChampions[TFTPlayer_Units[int(unit_iter[4:])]["character_id"]]["display_name"]
                                                                            except KeyError:
                                                                                try:
                                                                                    subkey = list(TFTChampions.keys())[list(map(lambda x: x.lower(), list(TFTChampions.keys()))).index(TFTPlayer_Units[int(unit_iter[4:])]["character_id"].lower())]
                                                                                    to_append = TFTChampions[subkey]["display_name"]
                                                                                except ValueError:
                                                                                    print("【%d. %s】第%d/%d场对局（对局序号：%d）棋子信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT champion information (%s) of Match %d / %d (matchID: %d) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_Units[int(unit_iter[4:])]["character_id"], j, key, TFTPlayer_Units[int(unit_iter[4:])]["character_id"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                                    to_append = TFTPlayer_Units[int(unit_iter[4:])]["character_id"]
                                                                                    break
                                                                                else:
                                                                                    break
                                                                            else:
                                                                                break
                                                            if TFTHistory[i]["json"]["participants"][k]["puuid"] != current_puuid:
                                                                TFTHistory_data[key].append(to_append)
                                                        else:
                                                            to_append = TFTPlayer_Units[int(unit_iter[4:])][subkey]
                                                            if TFTHistory[i]["json"]["participants"][k]["puuid"] != current_puuid:
                                                                TFTHistory_data[key].append(to_append)
                                                    else:
                                                        if TFTHistory[i]["json"]["participants"][k]["puuid"] != current_puuid:
                                                            TFTHistory_data[key].append("")
                                                else:
                                                    if int(unit_iter[4:]) < len(TFTPlayer_Units): #很少有英雄单位可以有3个装备（Merely do champion units have full items）
                                                        if "itemNames" in TFTPlayer_Units[(int(unit_iter[4:]))] and (j - 1) % 3 < len(TFTPlayer_Units[(int(unit_iter[4:]))]["itemNames"]):
                                                            TFTItemNameId = TFTPlayer_Units[(int(unit_iter[4:]))]["itemNames"][(j - 1) % 3]
                                                            try:
                                                                to_append = TFTItems[TFTItemNameId]["name"]
                                                            except KeyError:
                                                                TFTItemPatch_adopted = TFTGamePatch
                                                                TFTItem_recapture = 1
                                                                print("第%d/%d场对局（对局序号：%d）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%s) of Match %d / %d (matchID: %d) capture failed! Changing to TFT items of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemNameId, TFTItem_recapture, TFTItemPatch_adopted, TFTItemNameId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemPatch_adopted, TFTItem_recapture))
                                                                while True:
                                                                    try:
                                                                        TFTItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[language_code])).json()
                                                                    except requests.exceptions.JSONDecodeError:
                                                                        TFTItemPatch_deserted = TFTItemPatch_adopted
                                                                        TFTItemPatch_adopted = FindPostPatch(TFTItemPatch_adopted, bigPatches)
                                                                        TFTItemPatch_recapture = 1
                                                                        print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture))
                                                                    except requests.exceptions.RequestException:
                                                                        if TFTItem_recapture < 3:
                                                                            TFTItem_recapture += 1
                                                                            print("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture))
                                                                        else:
                                                                            print("网络环境异常！第%d/%d场对局（对局序号：%d）的装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the item (%s) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemNameId, TFTItemNameId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                            to_append = TFTItemNameId
                                                                            break
                                                                    else:
                                                                        print("已改用%s版本的云顶之弈装备信息。\nTFT item information changed to Patch %s." %(TFTItemPatch_adopted, TFTItemPatch_adopted))
                                                                        TFTItems = {}
                                                                        for TFTItem_iter in TFTItem:
                                                                            item_nameId = TFTItem_iter.pop("nameId")
                                                                            TFTItems[item_nameId] = TFTItem_iter
                                                                        try:
                                                                            to_append = TFTItems[TFTItemNameId]["name"]
                                                                        except KeyError:
                                                                            print("【%d. %s】第%d/%d场对局（对局序号：%d）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%s) of Match %d / %d (matchID: %d) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemNameId, j, key, TFTItemNameId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                            to_append = TFTItemNameId
                                                                            break
                                                                        else:
                                                                            break
                                                        elif "items" in TFTPlayer_Units[(int(unit_iter[4:]))] and (j - 1) % 3 < len(TFTPlayer_Units[(int(unit_iter[4:]))]["items"]): #在12.4版本之前，装备是通过序号而不是接口名称在LCU API中被存储的（Before Patch 12.4, items are stored via itemIDs instead of itemNames）
                                                            TFTItemId = TFTPlayer_Units[(int(unit_iter[4:]))]["items"][(j - 1) % 3]
                                                            try:
                                                                to_append = TFTItems[TFTItemId]["name"] #第一次运行此处时，必定发生报错，因为在重新获取装备信息之前，最新版本的TFTItems是以TFTItemName而不是TFTItemId作为键的（First run here will definitely cause an error. That's because before recapturing the item information, the latest `TFTItems` takes `TFTItemName` instead of `TFTItemId` as the key）
                                                            except KeyError:
                                                                TFTItemPatch_adopted = TFTGamePatch
                                                                TFTItem_recapture = 1
                                                                print("第%d/%d场对局（对局序号：%d）装备信息（%d）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%d) of Match %d / %d (matchID: %d) capture failed! Changing to TFT items of Patch %s ... Times tried: %d." %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemId, TFTItem_recapture, TFTItemPatch_adopted, TFTItemId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemPatch_adopted, TFTItem_recapture))
                                                                while True:
                                                                    try:
                                                                        TFTItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[language_code])).json()
                                                                    except requests.exceptions.JSONDecodeError:
                                                                        TFTItemPatch_deserted = TFTItemPatch_adopted
                                                                        TFTItemPatch_adopted = FindPostPatch(TFTItemPatch_adopted, bigPatches)
                                                                        TFTItemPatch_recapture = 1
                                                                        print("%s版本文件不存在！正在第%s次尝试转至%s版本……\n%s patch file doesn't exist! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture))
                                                                    except requests.exceptions.RequestException:
                                                                        if TFTItem_recapture < 3:
                                                                            TFTItem_recapture += 1
                                                                            print("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Changing to TFT items of Patch %s ... Times tried: %d." %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture))
                                                                        else:
                                                                            print("网络环境异常！第%d/%d场对局（对局序号：%d）的装备信息（%d）将采用原始数据！\nNetwork error! The original data will be used for the item (%d) of Match %d / %d (matchID: %d)!" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemId, TFTItemId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                            to_append = TFTItemId
                                                                            break
                                                                    else:
                                                                        print("已改用%s版本的云顶之弈装备信息。\nTFT item information changed to Patch %s." %(TFTItemPatch_adopted, TFTItemPatch_adopted))
                                                                        TFTItems = {}
                                                                        for TFTItem_iter in TFTItem:
                                                                            item_id = TFTItem_iter.pop("id")
                                                                            TFTItems[item_id] = TFTItem_iter
                                                                        try:
                                                                            to_append = TFTItems[TFTItemId]["name"]
                                                                        except KeyError:
                                                                            print("【%d. %s】第%d/%d场对局（对局序号：%d）装备信息（%d）获取失败！将采用原始数据！\n[%d. %s] TFT item information (%d) of Match %d / %d (matchID: %d) capture failed! The original data will be used for this match!" %(j, key, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemId, j, key, TFTItemId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                                                                            to_append = TFTItemId
                                                                            break
                                                                        else:
                                                                            break
                                                        else:
                                                            to_append = ""
                                                        if TFTHistory[i]["json"]["participants"][k]["puuid"] != current_puuid:
                                                            TFTHistory_data[key].append(to_append)
                                                    else:
                                                        if TFTHistory[i]["json"]["participants"][k]["puuid"] != current_puuid:
                                                            TFTHistory_data[key].append("")
                                    print("加载进度（Loading process）：%d/%d\t对局序号（MatchID）： %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"]))
                            recent_TFTPlayers_statistics_display_order = [22, 23, 21, 2, 1, 3, 5, 6, 4, 13, 14, 15, 18, 17, 24, 16, 25, 20, 19, 10, 11, 12, 91, 92, 93, 124, 125, 126, 94, 95, 96, 127, 128, 129, 97, 98, 99, 130, 131, 132, 100, 101, 102, 133, 134, 135, 103, 104, 105, 136, 137, 138, 106, 107, 108, 139, 140, 141, 109, 110, 111, 142, 143, 144, 112, 113, 114, 145, 146, 147, 115, 116, 117, 148, 149, 150, 118, 119, 120, 151, 152, 153, 121, 122, 123, 154, 155, 156, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90]
                            recent_TFTPlayers_data_organized = {}
                            for i in range(len(recent_TFTPlayers_statistics_display_order)):
                                key = TFTHistory_header_keys[recent_TFTPlayers_statistics_display_order[i]]
                                recent_TFTPlayers_data_organized[key] = [TFTHistory_header[key]] + TFTHistory_data[key]
                                #print("近期一起玩过的云顶之弈玩家数据重排进度（Rearranging process of recently played summoner (TFT) data）：%d/%d" %(i + 1, len(recent_TFTPlayers_statistics_display_order)))
                            #print("正在创建数据框……\nCreating the dataframe ...")
                            recent_TFTPlayers_df = pandas.DataFrame(data = recent_TFTPlayers_data_organized)
                            #print("数据框创建完成！\nDataframe creation finished!")
                            if not TFTGamePlayed:
                                print("这位召唤师从5月1日起就没有进行过任何云顶之弈对局。\nThis summoner hasn't played any TFT game yet since May 1st.")
                        else:
                            TFTHistory_header = {"gameIndex": "游戏序号", "game_datetime": "创建日期", "game_id": "对局序号", "game_length": "持续时长", "game_version": "对局版本", "queue_id": "队列序号", "tft_game_type": "游戏类型", "tft_set_core_name": "数据版本名称", "tft_set_number": "赛季", "participantId": "玩家序号", "augment1": "强化符文1", "augment2": "强化符文2", "augment3": "强化符文3", "companion": "小小英雄", "companion_level": "小小英雄星级", "companion_rarity": "小小英雄稀有度", "gold_left": "剩余金币", "last_round": "存活回合", "level": "等级", "placement": "名次", "players_eliminated": "淘汰玩家数", "puuid": "玩家通用唯一识别码", "summonerName": "召唤师名称", "summonerId": "召唤师序号", "time_eliminated": "存活时长", "total_damage_to_players": "造成玩家伤害", "trait0 name": "羁绊1", "trait0 num_units": "羁绊1单位数", "trait0 style": "羁绊1羁绊框颜色", "trait0 tier_current": "羁绊1当前等级", "trait0 tier_total": "羁绊1最高等级", "trait1 name": "羁绊2", "trait1 num_units": "羁绊2单位数", "trait1 style": "羁绊2羁绊框颜色", "trait1 tier_current": "羁绊2当前等级", "trait1 tier_total": "羁绊2最高等级", "trait2 name": "羁绊3", "trait2 num_units": "羁绊3单位数", "trait2 style": "羁绊3羁绊框颜色", "trait2 tier_current": "羁绊3当前等级", "trait2 tier_total": "羁绊3最高等级", "trait3 name": "羁绊4", "trait3 num_units": "羁绊4单位数", "trait3 style": "羁绊4羁绊框颜色", "trait3 tier_current": "羁绊4当前等级", "trait3 tier_total": "羁绊4最高等级", "trait4 name": "羁绊5", "trait4 num_units": "羁绊5单位数", "trait4 style": "羁绊5羁绊框颜色", "trait4 tier_current": "羁绊5当前等级", "trait4 tier_total": "羁绊5最高等级", "trait5 name": "羁绊6", "trait5 num_units": "羁绊6单位数", "trait5 style": "羁绊6羁绊框颜色", "trait5 tier_current": "羁绊6当前等级", "trait5 tier_total": "羁绊6最高等级", "trait6 name": "羁绊7", "trait6 num_units": "羁绊7单位数", "trait6 style": "羁绊7羁绊框颜色", "trait6 tier_current": "羁绊7当前等级", "trait6 tier_total": "羁绊7最高等级", "trait7 name": "羁绊8", "trait7 num_units": "羁绊8单位数", "trait7 style": "羁绊8羁绊框颜色", "trait7 tier_current": "羁绊8当前等级", "trait7 tier_total": "羁绊8最高等级", "trait8 name": "羁绊9", "trait8 num_units": "羁绊9单位数", "trait8 style": "羁绊9羁绊框颜色", "trait8 tier_current": "羁绊9当前等级", "trait8 tier_total": "羁绊9最高等级", "trait9 name": "羁绊10", "trait9 num_units": "羁绊10单位数", "trait9 style": "羁绊10羁绊框颜色", "trait9 tier_current": "羁绊10当前等级", "trait9 tier_total": "羁绊10最高等级", "trait10 name": "羁绊11", "trait10 num_units": "羁绊11单位数", "trait10 style": "羁绊11羁绊框颜色", "trait10 tier_current": "羁绊11当前等级", "trait10 tier_total": "羁绊11最高等级", "trait11 name": "羁绊12", "trait11 num_units": "羁绊12单位数", "trait11 style": "羁绊12羁绊框颜色", "trait11 tier_current": "羁绊12当前等级", "trait11 tier_total": "羁绊12最高等级", "trait12 name": "羁绊13", "trait12 num_units": "羁绊13单位数", "trait12 style": "羁绊13羁绊框颜色", "trait12 tier_current": "羁绊13当前等级", "trait12 tier_total": "羁绊13最高等级", "unit0 character": "英雄1", "unit0 rarity": "英雄1：稀有度", "unit0 tier": "英雄1：星级", "unit1 character": "英雄2", "unit1 rarity": "英雄2：稀有度", "unit1 tier": "英雄2：星级", "unit2 character": "英雄3", "unit2 rarity": "英雄3：稀有度", "unit2 tier": "英雄3：星级", "unit3 character": "英雄4", "unit3 rarity": "英雄4：稀有度", "unit3 tier": "英雄4：星级", "unit4 character": "英雄5", "unit4 rarity": "英雄5：稀有度", "unit4 tier": "英雄5：星级", "unit5 character": "英雄6", "unit5 rarity": "英雄6：稀有度", "unit5 tier": "英雄6：星级", "unit6 character": "英雄7", "unit6 rarity": "英雄7：稀有度", "unit6 tier": "英雄7：星级", "unit7 character": "英雄8", "unit7 rarity": "英雄8：稀有度", "unit7 tier": "英雄8：星级", "unit8 character": "英雄9", "unit8 rarity": "英雄9：稀有度", "unit8 tier": "英雄9：星级", "unit9 character": "英雄10", "unit9 rarity": "英雄10：稀有度", "unit9 tier": "英雄10：星级", "unit10 character": "英雄11", "unit10 rarity": "英雄11：稀有度", "unit11 tier": "英雄11：星级", "unit0 item0": "英雄1：装备1", "unit0 item1": "英雄1：装备2", "unit0 item2": "英雄1：装备3", "unit1 item0": "英雄2：装备1", "unit1 item1": "英雄2：装备2", "unit1 item2": "英雄2：装备3", "unit2 item0": "英雄3：装备1", "unit2 item1": "英雄3：装备2", "unit2 item2": "英雄3：装备3", "unit3 item0": "英雄4：装备1", "unit3 item1": "英雄4：装备2", "unit3 item2": "英雄4：装备3", "unit4 item0": "英雄5：装备1", "unit4 item1": "英雄5：装备2", "unit4 item2": "英雄5：装备3", "unit5 item0": "英雄6：装备1", "unit5 item1": "英雄6：装备2", "unit5 item2": "英雄6：装备3", "unit6 item0": "英雄7：装备1", "unit6 item1": "英雄7：装备2", "unit6 item2": "英雄7：装备3", "unit7 item0": "英雄8：装备1", "unit7 item1": "英雄8：装备2", "unit7 item2": "英雄8：装备3", "unit8 item0": "英雄9：装备1", "unit8 item1": "英雄9：装备2", "unit8 item2": "英雄9：装备3", "unit9 item0": "英雄10：装备1", "unit9 item1": "英雄10：装备2", "unit9 item2": "英雄10：装备3", "unit10 item0": "英雄11：装备1", "unit10 item1": "英雄11：装备2", "unit10 item2": "英雄11：装备3"}
                            TFTHistory_data = {}
                            TFTHistory_header_keys = list(TFTHistory_header.keys())
                            recent_TFTPlayers_statistics_display_order = [22, 23, 21, 2, 1, 3, 5, 6, 4, 13, 14, 15, 18, 17, 24, 16, 25, 20, 19, 10, 11, 12, 91, 92, 93, 124, 125, 126, 94, 95, 96, 127, 128, 129, 97, 98, 99, 130, 131, 132, 100, 101, 102, 133, 134, 135, 103, 104, 105, 136, 137, 138, 106, 107, 108, 139, 140, 141, 109, 110, 111, 142, 143, 144, 112, 113, 114, 145, 146, 147, 115, 116, 117, 148, 149, 150, 118, 119, 120, 151, 152, 153, 121, 122, 123, 154, 155, 156, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90]
                            recent_TFTPlayers_data_organized = {}
                            for i in range(len(recent_TFTPlayers_statistics_display_order)):
                                key = TFTHistory_header_keys[recent_TFTPlayers_statistics_display_order[i]]
                                recent_TFTPlayers_data_organized[key] = [TFTHistory_header[key]]
                            recent_TFTPlayers_df = pandas.DataFrame(data = recent_TFTPlayers_data_organized)
                        
                        if not detectMode:
                            recent_players_metadata = {} #这里另外设置元数据是为了整理出用于可视化的数据（Here the metadata is designed to sort out data for visualization）
                            for i in range(1, len(recent_LoLPlayers_df)): #第0行是中文表头，所以要从第1行开始（The 0th line contains the Chinese headers, so the iteration should start from the first line）
                                puuid_iter = recent_LoLPlayers_df["puuid"][i]
                                summonerName_iter = recent_LoLPlayers_df["summonerName"][i]
                                matchID_iter = recent_LoLPlayers_df["gameId"][i]
                                LoLGameDuration_iter = LoLGameDuration_raw[i - 1] #由于列表变量LoLGameDuration_raw独立于recent_players_data之外单独存储信息，其中不包含中文表头，全是数据，因此在设置索引时应当减1，以对应其它与recent_LoLPlayers_df有关的列表变量（Since the list variable `LoLGameDuration_raw` stores data independently from the variable `recent_players_data`, it only contains data without a header. Therefore, its index is subtracted by 1 to correspond to other list variables with regard to `recent_LoLPlayers_df`）
                                isPvP_iter = True if gamemodes[recent_LoLPlayers_df["queueId"][i]]["category"] == "PvP" else False #添加是否玩家对战的信息，以便单独统计一同进行玩家对战的总时间。下同（Added the information whether a match is PvP, so that the total time of only PvP matches can be calculated. So do the following two variables）
                                isPvE_iter = True if gamemodes[recent_LoLPlayers_df["queueId"][i]]["category"] == "VersusAi" else False
                                isCustom_iter = True if gamemodes[recent_LoLPlayers_df["queueId"][i]]["category"] == "CUSTOM" else False
                                if not puuid_iter in recent_players_metadata:
                                    recent_players_metadata[puuid_iter] = {}
                                    recent_players_metadata[puuid_iter]["name"] = summonerName_iter #该语句不会在else部分出现。这是考虑到如果召唤师改过名字，那么呈现在频数直方图上的横轴的召唤师名应当是最新的（This statement won't appear in the else-part, considering if a summoner has changed its name, then the summonerName near the horizontal axis of the frequency histogram should be latest）
                                    recent_players_metadata[puuid_iter]["gameCount"] = 1
                                    recent_players_metadata[puuid_iter]["matches"] = [matchID_iter]
                                    recent_players_metadata[puuid_iter]["durations"] = [LoLGameDuration_iter]
                                    recent_players_metadata[puuid_iter]["isPvP"] = [isPvP_iter]
                                    recent_players_metadata[puuid_iter]["isPvE"] = [isPvE_iter]
                                    recent_players_metadata[puuid_iter]["isCustom"] = [isCustom_iter]
                                    recent_players_metadata[puuid_iter]["PvPCount"] = int(isPvP_iter)
                                    recent_players_metadata[puuid_iter]["PvECount"] = int(isPvE_iter)
                                    recent_players_metadata[puuid_iter]["CustomCount"] = int(isCustom_iter)
                                    recent_players_metadata[puuid_iter]["totalTime"] = LoLGameDuration_iter
                                    recent_players_metadata[puuid_iter]["totalPvPTime"] = LoLGameDuration_iter * isPvP_iter
                                    recent_players_metadata[puuid_iter]["totalPvETime"] = LoLGameDuration_iter * isPvE_iter
                                    recent_players_metadata[puuid_iter]["totalCustomTime"] = LoLGameDuration_iter * isCustom_iter
                                else:
                                    recent_players_metadata[puuid_iter]["gameCount"] += 1
                                    recent_players_metadata[puuid_iter]["matches"].append(matchID_iter)
                                    recent_players_metadata[puuid_iter]["durations"].append(LoLGameDuration_iter)
                                    recent_players_metadata[puuid_iter]["isPvP"].append(isPvP_iter)
                                    recent_players_metadata[puuid_iter]["isPvE"].append(isPvE_iter)
                                    recent_players_metadata[puuid_iter]["isCustom"].append(isCustom_iter)
                                    recent_players_metadata[puuid_iter]["PvPCount"] += isPvP_iter
                                    recent_players_metadata[puuid_iter]["PvECount"] += isPvE_iter
                                    recent_players_metadata[puuid_iter]["CustomCount"] += isCustom_iter
                                    recent_players_metadata[puuid_iter]["totalTime"] += LoLGameDuration_iter
                                    recent_players_metadata[puuid_iter]["totalPvPTime"] += LoLGameDuration_iter * isPvP_iter
                                    recent_players_metadata[puuid_iter]["totalPvETime"] += LoLGameDuration_iter * isPvE_iter
                                    recent_players_metadata[puuid_iter]["totalCustomTime"] += LoLGameDuration_iter * isCustom_iter
                                #print("用于可视化的元数据创建进度（Creating process of metadata for visualization）：%d/%d" %(i, len(recent_LoLPlayers_df) - 1))
                            if search_TFT != "":
                                for i in range(1, len(recent_TFTPlayers_df)):
                                    puuid_iter = recent_TFTPlayers_df["puuid"][i]
                                    summonerName_iter = recent_TFTPlayers_df["summonerName"][i]
                                    matchID_iter = recent_TFTPlayers_df["game_id"][i]
                                    TFTGameDuration_iter = TFTGameDuration_raw[i - 1]
                                    isPvP_iter = True if gamemodes[recent_TFTPlayers_df["queue_id"][i]]["category"] == "PvP" else False
                                    isPvE_iter = True if gamemodes[recent_TFTPlayers_df["queue_id"][i]]["category"] == "VersusAi" else False
                                    isCustom_iter = True if gamemodes[recent_TFTPlayers_df["queue_id"][i]]["category"] == "CUSTOM" else False
                                    if not puuid_iter in recent_players_metadata:
                                        recent_players_metadata[puuid_iter] = {}
                                        recent_players_metadata[puuid_iter]["name"] = summonerName_iter
                                        recent_players_metadata[puuid_iter]["gameCount"] = 1
                                        recent_players_metadata[puuid_iter]["matches"] = [matchID_iter]
                                        recent_players_metadata[puuid_iter]["durations"] = [TFTGameDuration_iter]
                                        recent_players_metadata[puuid_iter]["isPvP"] = [isPvP_iter]
                                        recent_players_metadata[puuid_iter]["isPvE"] = [isPvE_iter]
                                        recent_players_metadata[puuid_iter]["isCustom"] = [isCustom_iter]
                                        recent_players_metadata[puuid_iter]["PvPCount"] = int(isPvP_iter)
                                        recent_players_metadata[puuid_iter]["PvECount"] = int(isPvE_iter)
                                        recent_players_metadata[puuid_iter]["CustomCount"] = int(isCustom_iter)
                                        recent_players_metadata[puuid_iter]["totalTime"] = TFTGameDuration_iter
                                        recent_players_metadata[puuid_iter]["totalPvPTime"] = TFTGameDuration_iter * isPvP_iter
                                        recent_players_metadata[puuid_iter]["totalPvETime"] = TFTGameDuration_iter * isPvE_iter
                                        recent_players_metadata[puuid_iter]["totalCustomTime"] = TFTGameDuration_iter * isCustom_iter
                                    else:
                                        recent_players_metadata[puuid_iter]["gameCount"] += 1
                                        recent_players_metadata[puuid_iter]["matches"].append(matchID_iter)
                                        recent_players_metadata[puuid_iter]["durations"].append(TFTGameDuration_iter)
                                        recent_players_metadata[puuid_iter]["isPvP"].append(isPvP_iter)
                                        recent_players_metadata[puuid_iter]["isPvE"].append(isPvE_iter)
                                        recent_players_metadata[puuid_iter]["isCustom"].append(isCustom_iter)
                                        recent_players_metadata[puuid_iter]["PvPCount"] += isPvP_iter
                                        recent_players_metadata[puuid_iter]["PvECount"] += isPvE_iter
                                        recent_players_metadata[puuid_iter]["CustomCount"] += isCustom_iter
                                        recent_players_metadata[puuid_iter]["totalTime"] += TFTGameDuration_iter
                                        recent_players_metadata[puuid_iter]["totalPvPTime"] += TFTGameDuration_iter * isPvP_iter
                                        recent_players_metadata[puuid_iter]["totalPvETime"] += TFTGameDuration_iter * isPvE_iter
                                        recent_players_metadata[puuid_iter]["totalCustomTime"] += TFTGameDuration_iter * isCustom_iter
                                    #print("用于可视化的元数据创建进度（Creating process of metadata for visualization）：%d/%d" %(i, len(recent_TFTPlayers_df) - 1))
                            #pyperclip.copy(str(recent_players_metadata))
                            jsonname = "Recently Played Summoners - %s.json" %displayName
                            while True:
                                try:
                                    jsonfile = open(os.path.join(folder, jsonname), "w", encoding = "utf-8")
                                except FileNotFoundError:
                                    os.makedirs(folder, exist_ok = True)
                                else:
                                    break
                            try:
                                jsonfile.write(str(json.dumps(recent_players_metadata, indent = 4, ensure_ascii = False)))
                            except UnicodeEncodeError:
                                print("近期一起玩过的玩家元数据文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nRecently played summoner metadata text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                            
                            #针对元数据中记录的每个玩家的累计游戏时长和游戏对局数输出条形图（Output the bar chart of each summoner's total time and game counts in the metadata）
                            totalTime = {}
                            PvPTime = {}
                            PvETime = {}
                            CustomTime = {}
                            totalCount = {}
                            PvPCount = {}
                            PvECount = {}
                            CustomCount = {}
                            for player in recent_players_metadata.values():
                                totalTime[player["name"]] = player["totalTime"]
                                PvPTime[player["name"]] = player["totalPvPTime"]
                                PvETime[player["name"]] = player["totalPvETime"]
                                CustomTime[player["name"]] = player["totalCustomTime"]
                                totalCount[player["name"]] = player["gameCount"]
                                PvPCount[player["name"]] = player["PvPCount"]
                                PvECount[player["name"]] = player["PvECount"]
                                CustomCount[player["name"]] = player["CustomCount"]
                            totalTime_sorted = sorted(totalTime.items(), key = lambda x: x[1], reverse = True)
                            PvPTime_sorted = sorted(PvPTime.items(), key = lambda x: x[1], reverse = True)
                            PvETime_sorted = sorted(PvETime.items(), key = lambda x: x[1], reverse = True)
                            CustomTime_sorted = sorted(CustomTime.items(), key = lambda x: x[1], reverse = True)
                            totalCount_sorted = sorted(totalCount.items(), key = lambda x: x[1], reverse = True)
                            PvPCount_sorted = sorted(PvPCount.items(), key = lambda x: x[1], reverse = True)
                            PvECount_sorted = sorted(PvECount.items(), key = lambda x: x[1], reverse = True)
                            CustomCount_sorted = sorted(CustomCount.items(), key = lambda x: x[1], reverse = True)
                            print("您希望条形图中显示游戏时长最长的前几名玩家？（默认为前20名）\nHow many players of the longest game time do you want to display in the bar chart? (20 by default)")
                            while True:
                                try:
                                    topN = input()
                                    if topN == "":
                                        topN = 20
                                        break
                                    else:
                                        topN = int(topN)
                                except ValueError:
                                    print("请输入整数！\nPlease input an integer!")
                                else:
                                    if topN <= 0:
                                        print("请输入正整数！\nPlease input a positive integer!")
                                    else:
                                        break
                            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei'] #设置默认字体为微软雅黑（Set the default font Microsoft YaHei）
                            plt.figure(figsize = (topN / 2, 10)) #设置导出图象的大小（Set the size of the exported figure ）
                            valuefont = {"family": "Times New Roman", "weight": "normal", "size": 9} #指定柱上显示的数据的字体格式（Determines the font of the values above the bars）
                            #绘制各玩家的总游戏时间柱状图（Plot the bar chart of the total time of certain number of players）
                            totalTimePic = plt.bar([totalTime_sorted[i][0] for i in range(topN)], [totalTime_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("游戏时长（秒）\ntotalGameTime (s)")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in totalTime_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("总游戏时间\ntotal game time")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Time_total.png" %displayName))
                            plt.clf()
                            #绘制各玩家的玩家对战时间柱状图（Plot the bar chart of the PvP time of certain number of players）
                            PvPTimePic = plt.bar([PvPTime_sorted[i][0] for i in range(topN)], [PvPTime_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("游戏时长（秒）\ntotalGameTime (s)")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in PvPTime_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("玩家对战时间\nPvP game time")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Time_PvP.png" %displayName))
                            plt.clf()
                            #绘制各玩家的人机对战时间柱状图（Plot the bar chart of the PvE time of certain number of players）
                            PvETimePic = plt.bar([PvETime_sorted[i][0] for i in range(topN)], [PvETime_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("游戏时长（秒）\ntotalGameTime (s)")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in PvETime_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("人机对战时间\nPvE game time")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Time_PvE.png" %displayName))
                            plt.clf()
                            #绘制各玩家的自定义对战时间柱状图（Plot the bar chart of the Custom time of certain number of players）
                            CustomTimePic = plt.bar([CustomTime_sorted[i][0] for i in range(topN)], [CustomTime_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("游戏时长（秒）\ntotalGameTime (s)")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in CustomTime_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("自定义对战时间\nCustom game time")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Time_Custom.png" %displayName))
                            plt.clf()
                            #绘制各玩家的总游戏对局数柱状图（Plot the bar chart of the total game count of certain number of players）
                            totalCountPic = plt.bar([totalCount_sorted[i][0] for i in range(topN)], [totalCount_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("对局数\ntotalGameCount")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in totalCount_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("总游戏对局数\ntotal game count")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Count_total.png" %displayName))
                            plt.clf()
                            #绘制各玩家的玩家对战局数柱状图（Plot the bar chart of the PvP game count of certain number of players）
                            PvPCountPic = plt.bar([PvPCount_sorted[i][0] for i in range(topN)], [PvPCount_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("对局数\ntotalGameCount")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in PvPCount_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("玩家对战局数\nPvP game count")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Count_PvP.png" %displayName))
                            plt.clf()
                            #绘制各玩家的人机对战局数柱状图（Plot the bar chart of the PvE game count of certain number of players）
                            PvECountPic = plt.bar([PvECount_sorted[i][0] for i in range(topN)], [PvECount_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("对局数\ntotalGameCount")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in PvECount_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("人机对战局数\nPvE game count")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Count_PvE.png" %displayName))
                            plt.clf()
                            #绘制各玩家的自定义对战局数柱状图（Plot the bar chart of the Custom game count of certain number of players）
                            CustomCountPic = plt.bar([CustomCount_sorted[i][0] for i in range(topN)], [CustomCount_sorted[i][1] for i in range(topN)])
                            plt.xticks(rotation = 45, ha = "right")
                            plt.ylabel("对局数\ntotalGameCount")
                            plt.yticks(fontproperties = "Calibri", size = 12)
                            for player, playtime in CustomCount_sorted[:topN]:
                                plt.text(player, playtime, playtime, ha = "center", va = "bottom", fontdict = valuefont)
                            plt.title("自定义对战局数\nCustom game count")
                            plt.savefig(os.path.join(folder, "Recently Played Summoners - %s - Count_Custom.png" %displayName))
                            plt.clf()
                            
                            print("是否导出以上近期一起玩过的玩家数据？（输入任意键导出，否则不导出）\nDo you want to export the above recently played summoner data? (Input anything to export or null to refuse exporting)")
                            export = input()
                            if export != "":
                                excel_name = "Summoner Profile - " + displayName + ".xlsx"
                                while True:
                                    try:
                                        with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                                            recent_LoLPlayers_df.to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (LoL)")
                                            print("近期一起玩过的英雄联盟玩家数据导出完成！\nRecently played summoner data (LoL) exported!\n")
                                            if search_TFT != "":
                                                recent_TFTPlayers_df.to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (TFT)")
                                                print("近期一起玩过的云顶之弈玩家数据导出完成！\nRecently played summoner data (TFT) exported!\n")
                                    except PermissionError:
                                        print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                        input()
                                    except FileNotFoundError:
                                        try:
                                            os.makedirs(folder)
                                        except FileExistsError:
                                            pass
                                        with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                                            recent_LoLPlayers_df.to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (LoL)")
                                            print("近期一起玩过的英雄联盟玩家数据导出完成！\nRecently played summoner data (LoL) exported!\n")
                                            if search_TFT != "":
                                                recent_TFTPlayers_df.to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (TFT)")
                                                print("近期一起玩过的云顶之弈玩家数据导出完成！\nRecently played summoner data (TFT) exported!\n")
                                        break
                                    else:
                                        break
                            break #搜索近期一起玩过的玩家完成，需要退出大的while循环（Exit the outer while-loop after work of searching for recently played summoners）
                        else:
                            print("近期一起玩过的玩家数据已加载完成！\nRecently played summoner data loaded successfully!")
                            update = False
                            while True:
                                recent_LoLPlayer_fields = ["summonerName", "gameCreationDate", "gameMode", "gameModeName", "mapId", "ally?", "champion", "alias", "champLevel", "spell1", "spell2", "KDA", "item1", "item2", "item3", "item4", "item5", "item6", "ornament", "win/lose"]
                                recent_TFTPlayer_fields = ["summonerName", "game_datetime", "tft_game_type", "companion", "companion_level", "companion_rarity", "level", "last_round", "time_eliminated", "gold_left", "total_damage_to_players", "players_eliminated", "placement", "augment1", "augment2", "augment3", "unit0 character", "unit0 rarity", "unit0 tier", "unit0 item0", "unit0 item1", "unit0 item2", "unit1 character", "unit1 rarity", "unit1 tier", "unit1 item0", "unit1 item1", "unit1 item2", "unit2 character", "unit2 rarity", "unit2 tier", "unit2 item0", "unit2 item1", "unit2 item2", "unit3 character", "unit3 rarity", "unit3 tier", "unit3 item0", "unit3 item1", "unit3 item2", "unit4 character", "unit4 rarity", "unit4 tier", "unit4 item0", "unit4 item1", "unit4 item2", "unit5 character", "unit5 rarity", "unit5 tier", "unit5 item0", "unit5 item1", "unit5 item2", "unit6 character", "unit6 rarity", "unit6 tier", "unit6 item0", "unit6 item1", "unit6 item2", "unit7 character", "unit7 rarity", "unit7 tier", "unit7 item0", "unit7 item1", "unit7 item2", "unit8 character", "unit8 rarity", "unit8 tier", "unit8 item0", "unit8 item1", "unit8 item2", "unit9 character", "unit9 rarity", "unit9 tier", "unit9 item0", "unit9 item1", "unit9 item2", "unit10 character", "unit10 rarity", "unit11 tier", "unit10 item0", "unit10 item1", "unit10 item2", "trait0 name", "trait0 num_units", "trait0 style", "trait0 tier_current", "trait0 tier_total", "trait1 name", "trait1 num_units", "trait1 style", "trait1 tier_current", "trait1 tier_total", "trait2 name", "trait2 num_units", "trait2 style", "trait2 tier_current", "trait2 tier_total", "trait3 name", "trait3 num_units", "trait3 style", "trait3 tier_current", "trait3 tier_total", "trait4 name", "trait4 num_units", "trait4 style", "trait4 tier_current", "trait4 tier_total", "trait5 name", "trait5 num_units", "trait5 style", "trait5 tier_current", "trait5 tier_total", "trait6 name", "trait6 num_units", "trait6 style", "trait6 tier_current", "trait6 tier_total", "trait7 name", "trait7 num_units", "trait7 style", "trait7 tier_current", "trait7 tier_total", "trait8 name", "trait8 num_units", "trait8 style", "trait8 tier_current", "trait8 tier_total", "trait9 name", "trait9 num_units", "trait9 style", "trait9 tier_current", "trait9 tier_total", "trait10 name", "trait10 num_units", "trait10 style", "trait10 tier_current", "trait10 tier_total", "trait11 name", "trait11 num_units", "trait11 style", "trait11 tier_current", "trait11 tier_total", "trait12 name", "trait12 num_units", "trait12 style", "trait12 tier_current", "trait12 tier_total"]
                                recent_LoLPlayer_dict_to_print = {}
                                recent_TFTPlayer_dict_to_print = {}
                                for key in recent_LoLPlayer_fields:
                                    recent_LoLPlayer_dict_to_print[key] = []
                                for key in recent_TFTPlayer_fields:
                                    recent_TFTPlayer_dict_to_print[key] = []
                                print("请选择检测场景：\nPlease select the situation to detect:\n1\t英雄选择阶段/游戏中（默认）【During champ select/In-game (Default)】\n2\t好友列表（Friend list）\n3\t好友请求（Friend requests）\n4\t自定义召唤师名称列表（List of any summoners' names）")
                                detect_scene = input()
                                if detect_scene == "":
                                    detect_scene = "1"
                                elif detect_scene[0] == "0":
                                    print('请输入要查询的对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出程序请输入“0”：\nPlease enter the match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to exit the program.')
                                    break
                                elif detect_scene[0] in set(map(str, range(1, 5))):
                                    detect_scene = detect_scene[0]
                                else:
                                    detect_scene = "4"
                                if detect_scene == "1":
                                    ally_count = 0
                                    enemy_count = 0
                                    player_count = 0
                                    recent_player_count = 0
                                    recent_friends = []
                                    LoLAlly_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
                                    LoLEnemy_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print) #在玩家对战的英雄选择阶段，所有敌方玩家的信息都是不可见的；在人机对战的英雄选择阶段，无敌方玩家。统计敌方信息只适用于自定义对局（During champ select of PVP games, all enemies' information is hidden; during champ select of PVE games, there're no enemy players. Counting enemy stats only applys for custom games）
                                    LoLPlayer_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
                                    TFTAlly_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
                                    TFTEnemy_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
                                    TFTPlayer_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
                                    recent_LoLPlayer_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
                                    recent_TFTPlayer_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
                                    print('''请确保您在英雄选择阶段或在游戏中，以便本脚本检测是否存在曾经遇到过的队友。在英雄选择阶段，按回车键开始检测；或者按“0”以返回上一步。\nPlease confirm you're during champ select or already in game, so that this script can detect whether there's an ally encountered before. During champ select or in game, press Enter to start detection; or press "0" to return to the last step.''')
                                    while True:
                                        detect = input()
                                        if detect != "" and detect[0] == "0":
                                            break
                                        gameflow_phase = await (await connection.request("GET", "/lol-gameflow/v1/gameflow-phase")).json()
                                        if gameflow_phase == "None":
                                            print("您尚未创建任何房间！请创建房间、开始对局并进入英雄选择阶段，再按回车键开始检测。\nYou haven't created any lobby yet! Please create a lobby, starts a game and then press Enter to start detection during the champ select stage.")
                                            continue
                                        elif gameflow_phase == "Lobby":
                                            print('''您尚未开始游戏！请单击开始游戏按钮，在进入英雄选择阶段后再按回车键开始检测。\nYou haven't started the game yet! Please click the "START GAME" button and press Enter to start detection after entering champ select stage.''')
                                            continue
                                        elif gameflow_phase == "Matchmaking":
                                            print("您尚未找到对局！请在接受对局进入英雄选择阶段后再按回车键开始检测。\nNo match has been found yet! Please press Enter to start detection after accepting a match and entering champ select stage.")
                                            continue
                                        elif gameflow_phase == "ReadyCheck":
                                            print("您已找到对局！请接受对局，并在进入英雄选择阶段后按回车键开始检测。\nA match has been found! Please accept this match and press Enter to start detection after entering champ select stage.")
                                            continue
                                        elif gameflow_phase == "ChampSelect" or gameflow_phase == "InProgress" or gameflow_phase == "Reconnect":
                                            break
                                        elif gameflow_phase == "WaitingForStats" or gameflow_phase == "EndOfGame" or gameflow_phase == "PreEndOfGame":
                                            print("您已完成对局！请使用生成模式以查看最近一局比赛中遇到的玩家信息，或者开启下一局以查看下一局遇到的队友是否曾经遇到过。\nYou've finished the match! Please use [Generate Mode] to check the information of players encountered in the latest match, or start another game and use [Detect Mode] to check whether an ally has been met before.")
                                            continue
                                    if detect != "" and detect[0] == "0":
                                        continue
                                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                                    friends = list(map(lambda x: x["puuid"], friends))
                                    update = False
                                    if gameflow_phase == "ChampSelect":
                                        champ_select_session = await (await connection.request("GET", "/lol-champ-select/v1/session")).json()
                                        print(champ_select_session)
                                        excel_name = "Recently Played Summoners in Match %s.xlsx" %champ_select_session["gameId"]
                                        if champ_select_session["isSpectating"]:
                                            print("您正在观战，无法显示玩家信息。请等待进入游戏后查看。\nYou're during the champ select of a spectated game, and the player information won't display. Please wait until you enter the game.")
                                        else:
                                            for ally in champ_select_session["myTeam"]:
                                                if ally["puuid"] != current_puuid:
                                                    if ally["nameVisibilityType"] == "VISIBLE":
                                                        ally_info_recapture = 0
                                                        ally_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %ally["puuid"])).json()
                                                        while "errorCode" in ally_info and ally_info_recapture < 3:
                                                            ally_info_recapture += 1
                                                            print("队友信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an ally (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                                                            ally_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %ally["puuid"])).json()
                                                        if ally_info_recapture >= 3:
                                                            print("队友信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an ally (puuid: %s) capture failed! The program will ignore this ally.")
                                                            continue
                                                        LoLAlly_index = [0] #第0行是中文表头，所以一开始要包含在内（The 0th line is Chinese header, so it should be contained in the beginning）
                                                        TFTAlly_index = [0]
                                                        for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                                            if recent_LoLPlayers_df.at[i, "puuid"] == ally["puuid"]:
                                                                LoLAlly_index.append(i)
                                                        if search_TFT != "":
                                                            for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                                if recent_TFTPlayers_df.at[i, "puuid"] == ally["puuid"]:
                                                                    TFTAlly_index.append(i)
                                                        if len(LoLAlly_index) + len(TFTAlly_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTAlly_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTAlly_index is defined and its length is at least 1）
                                                            ally_count += 1
                                                            LoLAlly_df = recent_LoLPlayers_df.loc[LoLAlly_index, :]
                                                            LoLAlly_df_to_print = pandas.concat([LoLAlly_df_to_print, LoLAlly_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                                            TFTAlly_df = recent_TFTPlayers_df.loc[TFTAlly_index, :]
                                                            TFTAlly_df_to_print = pandas.concat([TFTAlly_df_to_print, TFTAlly_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                                            if ally["puuid"] in friends:
                                                                recent_friends.append(ally_info["displayName"])
                                                            while True:
                                                                try:
                                                                    with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                                        if len(LoLAlly_index) > 1:
                                                                            LoLAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (LoL)")
                                                                        if search_TFT != "" and len(TFTAlly_index) > 1:
                                                                            TFTAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (TFT)")
                                                                        print("队友%s曾经与您一同战斗过%d次。\nAlly %s has fought with you for %d times." %(ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2, ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2))
                                                                except PermissionError:
                                                                    print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                                    input()
                                                                except FileNotFoundError:
                                                                    with pandas.ExcelWriter(path = excel_name) as writer:
                                                                        if len(LoLAlly_index) > 1:
                                                                            LoLAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (LoL)")
                                                                        if search_TFT != "" and len(TFTAlly_index) > 1:
                                                                            TFTAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (TFT)")
                                                                        print("队友%s曾经与您一同战斗过%d次。\nAlly %s has fought with you for %d times." %(ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2, ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2))
                                                                    break
                                                                else:
                                                                    break
                                            if champ_select_session["theirTeam"]: #在人机对战、云顶之弈和斗魂竞技场中，无敌方玩家（There're no enemy players in bot games, TFT and Arena）
                                                for enemy in champ_select_session["theirTeam"]:
                                                    if enemy["nameVisibilityType"] == "VISIBLE":
                                                        enemy_info_recapture = 0
                                                        enemy_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %enemy["puuid"])).json()
                                                        while "errorCode" in enemy_info and enemy_info_recapture < 3:
                                                            enemy_info_recapture += 1
                                                            print("对手信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an enemy (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(enemy["puuid"], enemy_info_recapture, enemy["puuid"], enemy_info_recapture))
                                                            enemy_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %enemy["puuid"])).json()
                                                        if enemy_info_recapture >= 3:
                                                            print("对手信息（玩家通用唯一识别码：%s）获取失败！将忽略该名对手。\nInformation of an enemy (puuid: %s) capture failed! The program will ignore this enemy.")
                                                            continue
                                                        LoLEnemy_index = [0]
                                                        TFTEnemy_index = [0]
                                                        for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                                            if recent_LoLPlayers_df.at[i, "puuid"] == enemy["puuid"]:
                                                                LoLEnemy_index.append(i)
                                                        if search_TFT != "":
                                                            for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                                if recent_TFTPlayers_df.at[i, "puuid"] == enemy["puuid"]:
                                                                    TFTEnemy_index.append(i)
                                                        if len(LoLEnemy_index) + len(TFTEnemy_index) > 2:
                                                            enemy_count += 1
                                                            LoLEnemy_df = recent_LoLPlayers_df.loc[LoLEnemy_index, :]
                                                            LoLEnemy_df_to_print = pandas.concat([LoLEnemy_df_to_print, LoLEnemy_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                                            TFTEnemy_df = recent_TFTPlayers_df.loc[TFTEnemy_index, :]
                                                            TFTEnemy_df_to_print = pandas.concat([TFTEnemy_df_to_print, TFTEnemy_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                                            if enemy["puuid"] in friends:
                                                                recent_friends.append((enemy_info["displayName"]))
                                                            while True:
                                                                try:
                                                                    with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                                        if len(LoLEnemy_index) > 1:
                                                                            LoLEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (LoL)")
                                                                        if search_TFT != "" and len(TFTEnemy_index) > 1:
                                                                            TFTEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (TFT)")
                                                                        print("对手%s曾经与您一同战斗过%d次。\nEnemy %s has fought with you for %d times." %(enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2, enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2))
                                                                except PermissionError:
                                                                    print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                                    input()
                                                                except FileNotFoundError:
                                                                    with pandas.ExcelWriter(path = excel_name) as writer:
                                                                        if len(LoLEnemy_index) > 1:
                                                                            LoLEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (LoL)")
                                                                        if search_TFT != "" and len(TFTEnemy_index) > 1:
                                                                            TFTEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (TFT)")
                                                                        print("对手%s曾经与您一同战斗过%d次。\nEnemy %s has fought with you for %d times." %(enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2, enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2))
                                                                    break
                                                                else:
                                                                    break
                                            if ally_count == 0:
                                                print("您目前遇到的都是新的队友。尝试拓展人缘吧！\nThe allies you've met now are all new. Try extending your friendship!")
                                            else:
                                                print()
                                                print(LoLAlly_df_to_print)
                                                if search_TFT != "":
                                                    print(TFTAlly_df_to_print)
                                                if recent_friends == []:
                                                    if ally_count == 1:
                                                        print('''一名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an ally present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                                    else:
                                                        print('''%d名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d allies present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, excel_name, ally_count, excel_name))
                                            if any(map(lambda x: x["nameVisibilityType"] == "VISIBLE", champ_select_session["theirTeam"])):
                                                if enemy_count > 0:
                                                    print()
                                                    print(LoLEnemy_df_to_print)
                                                    if search_TFT != "":
                                                        print(TFTEnemy_df_to_print)
                                                    if recent_friends == []:
                                                        if enemy_count == 1:
                                                            print('''一名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an enemy present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                                        else:
                                                            print('''%d名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d enemies present in your past matches. Please check the workbook "%s" in the main directory.''' %(enemy_count, excel_name, enemy_count, excel_name))
                                            if len(recent_friends) == 1:
                                                print("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friends[0], recent_friends[0]))
                                            elif len(recent_friends) > 1:
                                                print("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friends), ", ".join(recent_friends)))
                                            if not (all(map(lambda x: x["nameVisibilityType"] == "VISIBLE", champ_select_session["theirTeam"])) or all(map(lambda x: x["nameVisibilityType"] == "HIDDEN", champ_select_session["theirTeam"]))):
                                                print("检测到敌方信息可见性异常！请检查之前输出的英雄选择阶段信息。\nDetected enemies' visibility abnormal! Please check the champ select session information printed before.")
                                    elif gameflow_phase == "InProgress" or gameflow_phase == "Reconnect":
                                        gameflow_session = await (await connection.request("GET", "/lol-gameflow/v1/session")).json()
                                        print(gameflow_session)
                                        gameData = gameflow_session["gameData"]
                                        excel_name = "Recently Played Summoners in Match %s.xlsx" %gameData["gameId"]
                                        if gameData["queue"]["mapId"] == "22" or gameData["queue"]["mapId"] == "30": #玩家在API上的阵营划分随对局模式而不同。云顶之弈和斗魂竞技场虽然有多个阵营，但是都是记录在gameData["teamOne"]中，这需要和其它模式区分开来。该条件语句与“if gameData["queue"]["gameMode"] == "TFT" or gameData["queue"]["gameMode"] == "CHERRY"”等价，但是因为召唤师峡谷还能分成CLASSIC、URF等模式，所以这里直接用地图序号作为判断依据（The team where a player belongs varies by the game mode. Although there're actually more than 2 teams in TFT and Arena, all players are recorded in `gameData["teamOne"]`, which needs ditinguishing from other game modes. This conditional statement is equivalent to `if gameData["queue"]["gameMode"] == "TFT" or gameData["queue"]["gameMode"] == "CHERRY"`, but since there're multiple modes based on one map, like CLASSIC and URF based on Summoner's Rift, the mapId is thus taken as the judgment criterium）
                                            for player in gameData["teamOne"]:
                                                if "puuid" in player and player["puuid"] != current_puuid: #电脑玩家没有玩家通用唯一识别码（Bot players don't have puuids）
                                                    player_info_recapture = 0
                                                    player_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %player["puuid"])).json()
                                                    while "errorCode" in player_info and player_info_recapture < 3:
                                                        player_info_recapture += 1
                                                        print("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(player["puuid"], player_info_recapture, player["puuid"], player_info_recapture))
                                                        player_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %player["puuid"])).json()
                                                    if player_info_recapture >= 3:
                                                        print("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an player (puuid: %s) capture failed! The program will ignore this player.")
                                                        continue
                                                    LoLPlayer_index = [0] #第0行是中文表头，所以一开始要包含在内（The 0th line is Chinese header, so it should be contained in the beginning）
                                                    TFTPlayer_index = [0]
                                                    for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                                        if recent_LoLPlayers_df.at[i, "puuid"] == player["puuid"]:
                                                            LoLPlayer_index.append(i)
                                                    if search_TFT != "":
                                                        for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                            if recent_TFTPlayers_df.at[i, "puuid"] == player["puuid"]:
                                                                TFTPlayer_index.append(i)
                                                    if len(LoLPlayer_index) + len(TFTPlayer_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTPlayer_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTPlayer_index is defined and its length is at least 1）
                                                        player_count += 1
                                                        LoLPlayer_df = recent_LoLPlayers_df.loc[LoLPlayer_index, :]
                                                        LoLPlayer_df_to_print = pandas.concat([LoLPlayer_df_to_print, LoLPlayer_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                                        TFTPlayer_df = recent_TFTPlayers_df.loc[TFTPlayer_index, :]
                                                        TFTPlayer_df_to_print = pandas.concat([TFTPlayer_df_to_print, TFTPlayer_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                                        if player["puuid"] in friends:
                                                            recent_friends.append(player_info["displayName"])
                                                        while True:
                                                            try:
                                                                with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                                    if len(LoLPlayer_index) > 1:
                                                                        LoLPlayer_df.to_excel(excel_writer = writer, sheet_name = player_info["displayName"] + " (LoL)")
                                                                    if search_TFT != "" and len(TFTPlayer_index) > 1:
                                                                        TFTPlayer_df.to_excel(excel_writer = writer, sheet_name = player_info["displayName"] + " (TFT)")
                                                                    print("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d times." %(player_info["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2, player_info["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2))
                                                            except PermissionError:
                                                                print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                                input()
                                                            except FileNotFoundError:
                                                                with pandas.ExcelWriter(path = excel_name) as writer:
                                                                    if len(LoLPlayer_index) > 1:
                                                                        LoLPlayer_df.to_excel(excel_writer = writer, sheet_name = player_info["displayName"] + " (LoL)")
                                                                    if search_TFT != "" and len(TFTPlayer_index) > 1:
                                                                        TFTPlayer_df.to_excel(excel_writer = writer, sheet_name = player_info["displayName"] + " (TFT)")
                                                                    print("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d times." %(player_info["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2, player_info["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2))
                                                                break
                                                            else:
                                                                break
                                            if player_count == 0:
                                                print("您目前遇到的都是新的玩家。尝试拓展人缘吧！\nThe players you've met now are all new. Try extending your friendship!")
                                            else:
                                                print()
                                                print(LoLPlayer_df_to_print)
                                                if search_TFT != "":
                                                    print(TFTPlayer_df_to_print)
                                                if recent_friends == []:
                                                    if player_count == 1:
                                                        print('''一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a player present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                                    else:
                                                        print('''%d名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d players present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, excel_name, ally_count, excel_name))
                                            if len(recent_friends) == 1:
                                                print("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friends[0], recent_friends[0]))
                                            elif len(recent_friends) > 1:
                                                print("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friends), ", ".join(recent_friends)))
                                        else:
                                            isSpectating = False #目前支持观战的地图只有召唤师峡谷和极地大乱斗，所以只在这一部分设置观战逻辑变量，来表示游戏会话是不是观战的（Currently only the games based on Summoner's Rift and Howling Abyss support spectation, so this boolean variable is declared only this part, to tell whether the game session is a spectation）
                                            if current_puuid in map(lambda x: x["puuid"], gameData["teamOne"]): #API记录游戏中的玩家时，只会区分红蓝方，不会区分敌我。所以这里需要先判断那个阵营是我方（Players recorded in API only differentiate by blue or red team, instead of my or enemy team. So judging the own team or the enemy team is the first thing to do）
                                                myTeam = gameData["teamOne"]
                                                theirTeam = gameData["teamTwo"]
                                            elif current_puuid in map(lambda x: x["puuid"], gameData["teamTwo"]):
                                                myTeam = gameData["teamTwo"]
                                                theirTeam = gameData["teamOne"]
                                            else:
                                                myTeam = gameData["teamOne"] + gameData["teamTwo"]
                                                theirTeam = []
                                                isSpectating = True
                                            for ally in myTeam:
                                                if "puuid" in ally and ally["puuid"] != current_puuid:
                                                    ally_info_recapture = 0
                                                    ally_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %ally["puuid"])).json()
                                                    while "errorCode" in ally_info and ally_info_recapture < 3:
                                                        ally_info_recapture += 1
                                                        if isSpectating:
                                                            print("队友信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an ally (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                                                        else:
                                                            print("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of a player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(ally["puuid"], ally_info_recapture, ally["puuid"], ally_info_recapture))
                                                        ally_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %ally["puuid"])).json()
                                                    if ally_info_recapture >= 3:
                                                        if isSpectating:
                                                            print("队友信息（玩家通用唯一识别码：%s）获取失败！将忽略该名队友。\nInformation of an ally (puuid: %s) capture failed! The program will ignore this ally.")
                                                        else:
                                                            print("玩家信息（玩家通用唯一识别码：%s）获取失败！将忽略该名玩家。\nInformation of a player (puuid: %s) capture failed! The program will ignore this player.")
                                                        continue
                                                    LoLAlly_index = [0] #第0行是中文表头，所以一开始要包含在内（The 0th line is Chinese header, so it should be contained in the beginning）
                                                    TFTAlly_index = [0]
                                                    for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                                        if recent_LoLPlayers_df.at[i, "puuid"] == ally["puuid"]:
                                                            LoLAlly_index.append(i)
                                                    if search_TFT != "":
                                                        for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                            if recent_TFTPlayers_df.at[i, "puuid"] == ally["puuid"]:
                                                                TFTAlly_index.append(i)
                                                    if len(LoLAlly_index) + len(TFTAlly_index) > 2: #这里不需要关于是否查询了云顶之弈对局记录分类讨论，因为不管有没有查询云顶之弈对局记录，TFTAlly_index都存在，且长度至少为1（Here it's not necessary to discuss whether TFT match history has been searched before, because no matter whether it's searched, TFTAlly_index is defined and its length is at least 1）
                                                        ally_count += 1
                                                        LoLAlly_df = recent_LoLPlayers_df.loc[LoLAlly_index, :]
                                                        LoLAlly_df_to_print = pandas.concat([LoLAlly_df_to_print, LoLAlly_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                                        TFTAlly_df = recent_TFTPlayers_df.loc[TFTAlly_index, :]
                                                        TFTAlly_df_to_print = pandas.concat([TFTAlly_df_to_print, TFTAlly_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                                        if ally["puuid"] in friends:
                                                            recent_friends.append(ally_info["displayName"])
                                                        while True:
                                                            try:
                                                                with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                                    if len(LoLAlly_index) > 1:
                                                                        LoLAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (LoL)")
                                                                    if search_TFT != "" and len(TFTAlly_index) > 1:
                                                                        TFTAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (TFT)")
                                                                    if isSpectating:
                                                                        print("队友%s曾经与您一同战斗过%d次。\nAlly %s has fought with you for %d times." %(ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2, ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2))
                                                                    else:
                                                                        print("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d times." %(ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2, ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2))
                                                            except PermissionError:
                                                                print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                                input()
                                                            except FileNotFoundError:
                                                                with pandas.ExcelWriter(path = excel_name) as writer:
                                                                    if len(LoLAlly_index) > 1:
                                                                        LoLAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (LoL)")
                                                                    if search_TFT != "" and len(TFTAlly_index) > 1:
                                                                        TFTAlly_df.to_excel(excel_writer = writer, sheet_name = ally_info["displayName"] + " (TFT)")
                                                                    if isSpectating:
                                                                        print("队友%s曾经与您一同战斗过%d次。\nAlly %s has fought with you for %d times." %(ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2, ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2))
                                                                    else:
                                                                        print("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d times." %(ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2, ally_info["displayName"], len(LoLAlly_index) + len(TFTAlly_index) - 2))
                                                                break
                                                            else:
                                                                break
                                            for enemy in theirTeam:
                                                if "puuid" in enemy:
                                                    enemy_info_recapture = 0
                                                    enemy_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %enemy["puuid"])).json()
                                                    while "errorCode" in enemy_info and enemy_info_recapture < 3:
                                                        enemy_info_recapture += 1
                                                        print("对手信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of an enemy (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(enemy["puuid"], enemy_info_recapture, enemy["puuid"], enemy_info_recapture))
                                                        enemy_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/%s" %enemy["puuid"])).json()
                                                    if enemy_info_recapture >= 3:
                                                        print("对手信息（玩家通用唯一识别码：%s）获取失败！将忽略该名对手。\nInformation of an enemy (puuid: %s) capture failed! The program will ignore this enemy.")
                                                        continue
                                                    LoLEnemy_index = [0]
                                                    TFTEnemy_index = [0]
                                                    for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                                        if recent_LoLPlayers_df.at[i, "puuid"] == enemy["puuid"]:
                                                            LoLEnemy_index.append(i)
                                                    if search_TFT != "":
                                                        for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                            if recent_TFTPlayers_df.at[i, "puuid"] == enemy["puuid"]:
                                                                TFTEnemy_index.append(i)
                                                    if len(LoLEnemy_index) + len(TFTEnemy_index) > 2:
                                                        enemy_count += 1
                                                        LoLEnemy_df = recent_LoLPlayers_df.loc[LoLEnemy_index, :]
                                                        LoLEnemy_df_to_print = pandas.concat([LoLEnemy_df_to_print, LoLEnemy_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                                        TFTEnemy_df = recent_TFTPlayers_df.loc[TFTEnemy_index, :]
                                                        TFTEnemy_df_to_print = pandas.concat([TFTEnemy_df_to_print, TFTEnemy_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                                        if enemy["puuid"] in friends:
                                                            recent_friends.append((enemy_info["displayName"]))
                                                        while True:
                                                            try:
                                                                with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                                    if len(LoLEnemy_index) > 1:
                                                                        LoLEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (LoL)")
                                                                    if search_TFT != "" and len(TFTEnemy_index) > 1:
                                                                        TFTEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (TFT)")
                                                                    print("对手%s曾经与您一同战斗过%d次。\nEnemy %s has fought with you for %d times." %(enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2, enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2))
                                                            except PermissionError:
                                                                print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                                input()
                                                            except FileNotFoundError:
                                                                with pandas.ExcelWriter(path = excel_name) as writer:
                                                                    if len(LoLEnemy_index) > 1:
                                                                        LoLEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (LoL)")
                                                                    if search_TFT != "" and len(TFTEnemy_index) > 1:
                                                                        TFTEnemy_df.to_excel(excel_writer = writer, sheet_name = enemy_info["displayName"] + " (TFT)")
                                                                    print("对手%s曾经与您一同战斗过%d次。\nEnemy %s has fought with you for %d times." %(enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2, enemy_info["displayName"], len(LoLEnemy_index) + len(TFTEnemy_index) - 2))
                                                                break
                                                            else:
                                                                break
                                            if isSpectating:
                                                if ally_count == 0:
                                                    print("您目前遇到的都是新的玩家。尝试拓展人缘吧！\nThe players you've met now are all new. Try extending your friendship!")
                                                else:
                                                    print()
                                                    print(LoLAlly_df_to_print)
                                                    if search_TFT != "":
                                                        print(TFTAlly_df_to_print)
                                                    if recent_friends == []:
                                                        if ally_count == 1:
                                                            print('''一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a player present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                                        else:
                                                            print('''%d名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d players present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, excel_name, ally_count, excel_name))
                                            else:
                                                if ally_count == 0:
                                                    print("您目前遇到的都是新的玩家。尝试拓展人缘吧！\nThe players you've met now are all new. Try extending your friendship!")
                                                else:
                                                    print()
                                                    print(LoLAlly_df_to_print)
                                                    if search_TFT != "":
                                                        print(TFTAlly_df_to_print)
                                                    if recent_friends == []:
                                                        if ally_count == 1:
                                                            print('''一名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an ally present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                                        else:
                                                            print('''%d名队友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d allies present in your past matches. Please check the workbook "%s" in the main directory.''' %(ally_count, excel_name, ally_count, excel_name))
                                                if enemy_count > 0:
                                                    print()
                                                    print(LoLEnemy_df_to_print)
                                                    if search_TFT != "":
                                                        print(TFTEnemy_df_to_print)
                                                    if recent_friends == []:
                                                        if enemy_count == 1:
                                                            print('''一名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's an enemy present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                                        else:
                                                            print('''%d名对手曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d enemies present in your past matches. Please check the workbook "%s" in the main directory.''' %(enemy_count, excel_name, enemy_count, excel_name))
                                            if len(recent_friends) == 1:
                                                print("以上玩家中，%s是您的好友。\nAmong the above players, %s is your friend." %(recent_friends[0], recent_friends[0]))
                                            elif len(recent_friends) > 1:
                                                print("以上玩家中，%s是您的好友。\nAmong the above players, %s are your friends." %("、".join(recent_friends), ", ".join(recent_friends)))
                                elif detect_scene == "2":
                                    recent_friend_count = 0
                                    recent_LoLFriend_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
                                    recent_TFTFriend_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
                                    friends = await (await connection.request("GET", "/lol-chat/v1/friends")).json()
                                    excel_name = "Recently Played Summoners in Friend List.xlsx"
                                    try:
                                        os.remove(excel_name) #所有用户生成的文件名都相同，且该部分一次性生成所有好友信息。因此，如果主目录下原先有这个工作簿，需要先删除工作簿，防止不同召唤师的好友信息出现错乱（The names of the files generated by all users are the same. Besides, this part one-time generates all recently played friends. Therefore, if the workbook already exists in the main directory, it needs removing in case friends of different summoners exist in the workbook in the meantime）
                                    except FileNotFoundError:
                                        pass
                                    for friend in friends:
                                        LoLFriend_index = [0]
                                        TFTFriend_index = [0]
                                        for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                            if recent_LoLPlayers_df.at[i, "puuid"] == friend["puuid"]:
                                                LoLFriend_index.append(i)
                                        if search_TFT != "":
                                            for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                if recent_TFTPlayers_df.at[i, "puuid"] == friend["puuid"]:
                                                    TFTFriend_index.append(i)
                                        if len(LoLFriend_index) + len(TFTFriend_index) > 2:
                                            recent_friend_count += 1
                                            recent_LoLFriend_df = recent_LoLPlayers_df.loc[LoLFriend_index, :]
                                            recent_LoLFriend_df.insert(1, "note", ["备注"] + [friend["note"]] * (len(LoLFriend_index) - 1))
                                            recent_LoLFriend_df_to_print = pandas.concat([recent_LoLFriend_df_to_print, recent_LoLFriend_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                            recent_TFTFriend_df = recent_TFTPlayers_df.loc[TFTFriend_index, :]
                                            recent_TFTFriend_df.insert(1, "note", ["备注"] + [friend["note"]] * (len(TFTFriend_index) - 1))
                                            recent_TFTFriend_df_to_print = pandas.concat([recent_TFTFriend_df_to_print, recent_TFTFriend_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                            while True:
                                                try:
                                                    with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                        if len(LoLFriend_index) > 1:
                                                            recent_LoLFriend_df.to_excel(excel_writer = writer, sheet_name = friend["name"] + " (LoL)")
                                                        if search_TFT != "" and len(TFTFriend_index) > 1:
                                                            recent_TFTFriend_df.to_excel(excel_writer = writer, sheet_name = friend["name"] + " (TFT)")
                                                        print("好友%s曾经与您一同战斗过%d次。\nFriend %s has fought with you for %d times." %(friend["name"], len(LoLFriend_index) + len(TFTFriend_index) - 2, friend["name"], len(LoLFriend_index) + len(TFTFriend_index) - 2))
                                                except PermissionError:
                                                    print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                    input()
                                                except FileNotFoundError:
                                                    with pandas.ExcelWriter(path = excel_name) as writer:
                                                        if len(LoLFriend_index) > 1:
                                                            recent_LoLFriend_df.to_excel(excel_writer = writer, sheet_name = friend["name"] + " (LoL)")
                                                        if search_TFT != "" and len(TFTFriend_index) > 1:
                                                            recent_TFTFriend_df.to_excel(excel_writer = writer, sheet_name = friend["name"] + " (TFT)")
                                                        print("好友%s曾经与您一同战斗过%d次。\nFriend %s has fought with you for %d times." %(friend["name"], len(LoLFriend_index) + len(TFTFriend_index) - 2, friend["name"], len(LoLFriend_index) + len(TFTFriend_index) - 2))
                                                    break
                                                else:
                                                    break
                                    if len(friends) == 0:
                                        print("您尚未添加任何好友。尝试拓展人缘吧！\nYou haven't added any friend. Try extending your friendship!")
                                    elif recent_friend_count == 0:
                                        print("您近期还没有和任何好友一起玩过。这不赶紧开个黑ヽ(*^ｰ^)人(^ｰ^*)ノ\nYou haven't played with any friend recently. Go for a game with one of your friends ...")
                                    else:
                                        print()
                                        print(recent_LoLFriend_df_to_print)
                                        if search_TFT != "":
                                            print(recent_TFTFriend_df_to_print)
                                        if recent_friend_count == 1:
                                            print('''一名好友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a friend present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                        else:
                                            print('''%d名好友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d friends present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_friend_count, excel_name, recent_friend_count, excel_name))
                                elif detect_scene == "3":
                                    recent_prefriend_count = 0
                                    recent_LoLPrefriend_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
                                    recent_TFTPrefriend_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
                                    friend_requests = await (await (connection.request("GET", "/lol-chat/v2/friend-requests"))).json()
                                    excel_name = "Recently Played Summoners in Friend Requests.xlsx"
                                    try:
                                        os.remove(excel_name)
                                    except FileNotFoundError:
                                        pass
                                    for prefriend in friend_requests:
                                        LoLPrefriend_index = [0]
                                        TFTPrefriend_index = [0]
                                        for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                            if recent_LoLPlayers_df.at[i, "puuid"] == prefriend["puuid"]:
                                                LoLPrefriend_index.append(i)
                                        if search_TFT != "":
                                            for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                if recent_TFTPlayers_df.at[i, "puuid"] == prefriend["puuid"]:
                                                    TFTPrefriend_index.append(i)
                                        if len(LoLPrefriend_index) + len(TFTPrefriend_index) > 2:
                                            recent_prefriend_count += 1
                                            recent_LoLPrefriend_df = recent_LoLPlayers_df.loc[LoLPrefriend_index, :]
                                            recent_LoLPrefriend_df_to_print = pandas.concat([recent_LoLPrefriend_df_to_print, recent_LoLPrefriend_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                            recent_TFTPrefriend_df = recent_TFTPlayers_df.loc[TFTPrefriend_index, :]
                                            recent_TFTPrefriend_df_to_print = pandas.concat([recent_TFTPrefriend_df_to_print, recent_TFTPrefriend_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                            while True:
                                                try:
                                                    with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                        if len(LoLPrefriend_index) > 1:
                                                            recent_LoLPrefriend_df.to_excel(excel_writer = writer, sheet_name = prefriend["name"] + " (" + prefriend["direction"] + ") (LoL)")
                                                        if search_TFT != "" and len(TFTPrefriend_index) > 1:
                                                            recent_TFTPrefriend_df.to_excel(excel_writer = writer, sheet_name = prefriend["name"] + " (" + prefriend["direction"] + ") (TFT)")
                                                        print("好友请求列表中的%s曾经与您一同战斗过%d次。\nPlayer %s in friend request list has fought with you for %d times." %(prefriend["name"], len(LoLPrefriend_index) + len(TFTPrefriend_index) - 2, prefriend["name"], len(LoLPrefriend_index) + len(TFTPrefriend_index) - 2))
                                                except PermissionError:
                                                    print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                    input()
                                                except FileNotFoundError:
                                                    with pandas.ExcelWriter(path = excel_name) as writer:
                                                        if len(LoLPrefriend_index) > 1:
                                                            recent_LoLPrefriend_df.to_excel(excel_writer = writer, sheet_name = prefriend["name"] + " (" + prefriend["direction"] + ") (LoL)")
                                                        if search_TFT != "" and len(TFTPrefriend_index) > 1:
                                                            recent_TFTPrefriend_df.to_excel(excel_writer = writer, sheet_name = prefriend["name"] + " (" + prefriend["direction"] + ") (TFT)")
                                                        print("好友请求列表中的%s曾经与您一同战斗过%d次。\nPlayer %s in friend request list has fought with you for %d times." %(prefriend["name"], len(LoLPrefriend_index) + len(TFTPrefriend_index) - 2, prefriend["name"], len(LoLPrefriend_index) + len(TFTPrefriend_index) - 2))
                                                    break
                                                else:
                                                    break
                                    if len(friend_requests) == 0:
                                        print("您尚未发送或收到任何好友请求。尝试拓展人缘吧！\nYou haven't sent or received any friend request. Try extending your friendship!")
                                    elif recent_prefriend_count == 0:
                                        print("您近期未曾和好友请求列表中的玩家一起战斗过。这可能是因为好友请求太久未审核，或者该请求源于朋友或视频推荐，或者该请求不正当。\nYou haven't fought with any player in the friend request list. This may be because this request is put aside for too long, this request results from the recommendation from a friend or a video, or this request isn't sent in a proper manner.")
                                    else:
                                        print()
                                        print(recent_LoLPrefriend_df_to_print)
                                        if search_TFT != "":
                                            print(recent_TFTPrefriend_df_to_print)
                                        if recent_prefriend_count == 1:
                                            print('''好友请求列表中的一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a friend in the request list that is present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                        else:
                                            print('''好友请求列表中的%d名好友曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d friends in the request that is present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_prefriend_count, excel_name, recent_prefriend_count, excel_name))
                                elif detect_scene == "4":
                                    print('请输入一个由召唤师名称或玩家通用唯一识别码组成的列表。注意列表的每个元素都必须用半角引号括起来。示例：\nPlease input a list of summoner names or puuids. Note that each element of the list must be quoted with English quotation marks. Examples:\n["丿丶莫言丶丶丶", "WordlessMeteor", "沈黙の流れ星"]\n["d7669616-971c-53b1-a19e-570340d825dd", "671e9989-4165-59b6-8d3b-46c9090791a7", "60a6db11-8ff4-5eb4-b6fa-360e6e0eb8fc"]')
                                    while True:
                                        try:
                                            summoners = input()
                                            if summoners == "":
                                                continue
                                            elif summoners[0] == "0":
                                                break
                                            else:
                                                summoners = eval(summoners)
                                        except SyntaxError as e:
                                            print("语法错误！请重新输入！")
                                            print(e)
                                        else:
                                            if not isinstance(summoners, list):
                                                print("请输入一个列表！\nPlease input a list!")
                                            elif not all(map(lambda x: isinstance(x, str), summoners)):
                                                print("请输入一个元素全为字符串的列表！\nPlease input a list consisting of only string elements.")
                                            else:
                                                break
                                    if isinstance(summoners, str) and summoners[0] == "0":
                                        continue
                                    recent_players_count = 0
                                    recent_LoLPlayer_df_to_print = pandas.DataFrame(data = recent_LoLPlayer_dict_to_print)
                                    recent_TFTPlayer_df_to_print = pandas.DataFrame(data = recent_TFTPlayer_dict_to_print)
                                    excel_name = "Recently Played Summoners in Specified Player List.xlsx"
                                    try:
                                        os.remove(excel_name)
                                    except FileNotFoundError:
                                        pass
                                    print("是否呈现非法召唤师名称警告？（输入任意键呈现，否则不呈现。）\nDo you want to display illegal summoner name warning? (Input anything to display the warnings, or null to stop displaying.)")
                                    illegal_name_warning = bool(input())
                                    legal_summoners = {}
                                    for summoner in summoners:
                                        if summoner.count("-") == 4 and len(summoner.replace(" ", "")) > 22: #拳头规定的玩家名称不超过16个字符，尾标不超过5个字符（Riot game name can't exceed 16 characters. The tagline can't exceed 5 characters）
                                            check_by_puuid = True
                                            info_check = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + quote(summoner))).json()
                                        else:
                                            check_by_puuid = False
                                            info_check = await (await connection.request("GET", "/lol-summoner/v1/summoners?name=" + quote(summoner))).json()
                                        if "accountId" in info_check:
                                            legal_summoners[info_check["puuid"]] = info_check["displayName"] if info_check["tagLine"] == "" else info_check["gameName"] + "#" + info_check["tagLine"] #在腾讯代理的未开放跨区匹配的服务器上，尾标为空（On Tencent servers that don't support cross-server matching for now, the tagLine is empty）
                                            LoLPlayer_index = [0]
                                            TFTPlayer_index = [0]
                                            for i in range(len(recent_LoLPlayers_df.loc[:, "puuid"])):
                                                if recent_LoLPlayers_df.at[i, "puuid"] == info_check["puuid"]:
                                                    LoLPlayer_index.append(i)
                                            if search_TFT != "":
                                                for i in range(len(recent_TFTPlayers_df.loc[:, "puuid"])):
                                                    if recent_TFTPlayers_df.at[i, "puuid"] == info_check["puuid"]:
                                                        TFTPlayer_index.append(i)
                                            if len(LoLPlayer_index) + len(TFTPlayer_index) > 2:
                                                recent_players_count += 1
                                                recent_LoLPlayer_df = recent_LoLPlayers_df.loc[LoLPlayer_index, :]
                                                recent_LoLPlayer_df_to_print = pandas.concat([recent_LoLPlayer_df_to_print, recent_LoLPlayer_df.loc[1:, recent_LoLPlayer_fields]], axis = 0)
                                                recent_TFTPlayer_df = recent_TFTPlayers_df.loc[TFTPlayer_index, :]
                                                recent_TFTPlayer_df_to_print = pandas.concat([recent_TFTPlayer_df_to_print, recent_TFTPlayer_df.loc[1:, recent_TFTPlayer_fields]], axis = 0)
                                                while True:
                                                    try:
                                                        with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                                                            if len(LoLPlayer_index) > 1:
                                                                recent_LoLPlayer_df.to_excel(excel_writer = writer, sheet_name = info_check["displayName"] + " (LoL)")
                                                            if search_TFT != "" and len(TFTPlayer_index) > 1:
                                                                recent_TFTPlayer_df.to_excel(excel_writer = writer, sheet_name = info_check["displayName"] + " (TFT)")
                                                            print("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d times." %(info_check["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2, info_check["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2))
                                                    except PermissionError:
                                                        print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                                        input()
                                                    except FileNotFoundError:
                                                        with pandas.ExcelWriter(path = excel_name) as writer:
                                                            if len(LoLPlayer_index) > 1:
                                                                recent_LoLPlayer_df.to_excel(excel_writer = writer, sheet_name = info_check["displayName"] + " (LoL)")
                                                            if search_TFT != "" and len(TFTPlayer_index) > 1:
                                                                recent_TFTPlayer_df.to_excel(excel_writer = writer, sheet_name = info_check["displayName"] + " (TFT)")
                                                            print("玩家%s曾经与您一同战斗过%d次。\nPlayer %s has fought with you for %d times." %(info_check["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2, info_check["displayName"], len(LoLPlayer_index) + len(TFTPlayer_index) - 2))
                                                        break
                                                    else:
                                                        break
                                        elif illegal_name_warning:
                                            if "errorCode" in info_check and info_check["httpStatus"] == 400:
                                                if check_by_puuid:
                                                    print("您输入的玩家通用唯一识别码（%s）格式有误！请重新输入！\nPUUID (%s) wasn't in UUID format! Please try again!" %(summoner, summoner))
                                                else:
                                                    print("您输入的召唤师名称（%s）格式有误！请重新输入！\nERROR format of summoner name (%s)! Please try again!" %(summoner, summoner))
                                            elif "errorCode" in info_check and info_check["httpStatus"] == 404:
                                                if check_by_puuid:
                                                    print("未找到玩家通用唯一识别码为" + summoner + "的玩家；请核对识别码并稍后再试。\nA player with puuid " + summoner + " was not found; verify the puuid and try again.")
                                                else:
                                                    print("未找到" + summoner + "；请核对下名字并稍后再试。\n" + summoner + " was not found; verify the name and try again.")
                                            elif "errorCode" in info_check and info_check["httpStatus"] == 422:
                                                print('您输入的召唤师名称（%s）格式有误！召唤师名称已变更为拳头ID。请以“{召唤师名称}#{尾标}”的格式输入。\nERROR format of summoner name (%s)! Summoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}".' %(summoner, summoner))
                                    print("检测到%d名玩家：\nDetected %d players:" %(len(legal_summoners), len(legal_summoners)))
                                    print(pandas.DataFrame({"puuid": legal_summoners.keys(), "summonerName": legal_summoners.values()}))
                                    if recent_players_count == 0:
                                        print("未从以上玩家中检测到近期一起玩过的玩家。\nNo players detected in the above summoner list.")
                                    else:
                                        print()
                                        print(recent_LoLPlayer_df_to_print)
                                        if search_TFT != "":
                                            print(recent_TFTPlayer_df_to_print)
                                        if recent_players_count == 1:
                                            print('''一名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere's a player present in your past matches. Please check the workbook "%s" in the main directory.''' %(excel_name, excel_name))
                                        else:
                                            print('''%d名玩家曾经出现在您的历史对局中。请查看主目录下的“%s”文件。\nThere're %d players present in your past matches. Please check the workbook "%s" in the main directory.''' %(recent_players_count, excel_name, recent_players_count, excel_name))
                                print('是否更新数据？（输入“0”以返回上一层更新对局记录信息，否则在不更新对局信息的情况下再次查询近期一起玩过的玩家）\nUpdate data? (Submit "0" to update match history information, otherwise check the recently played summoners again without updating match history)')
                                update_str = input()
                                if update_str != "" and update_str[0] == "0":
                                    update = True
                                    break
                            if update:
                                break
            if detectMode and matchID == "0":
                break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await search_recent_players(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
