from lcu_driver import Connector
import copy, os, pandas, requests, time, json, re, pickle
from urllib.parse import quote, unquote

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
# 搜索召唤师生涯（Search summoner profile）
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
        print("该版本为美测服最新版本，暂未收录在DataDragon数据库中。\nThis version is the latest version on PBE and isn't temporarily archived in DataDragon database.")
        return 0

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

async def search_profile(connection):
    platform_config = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    platformId = platform_config["LoginDataPacket"]["platformId"]
    #print("请选择召唤师技能和装备的输出语言：\nPlease select a language to output the summoner spells and items:\nNo.\tCODE\tLANGUAGE\t语言\tCommunityDragon数据库适用版本\n1\tcs_CZ\tCzech (Czech Republic)\t捷克语（捷克共和国）\t7.1+\n2\tel_GR\tGreek (Greece)\t希腊语（希腊）\t9.1+\n3\tpl_PL\tPolish (Poland)\t波兰语（波兰）\t9.1+\n4\tro_RO\tRomanian (Romania)\t罗马尼亚语（罗马尼亚）\t9.1+\n5\thu_HU\tHungarian (Hungary)\t匈牙利语（匈牙利）\t9.1+\n6\ten_GB\t9.1+\tEnglish (United Kingdom)\t英语（英国）\n7\tde_DE\tGerman (Germany)\t德语（德国）\t7.1+\n8\tes_ES\tSpanish (Spain)\t西班牙语（西班牙）\t9.1+\n9\tit_IT\tItalian (Italy)\t意大利语（意大利）\t9.1+\n10\tfr_FR\tFrench (France)\t法语（法国）\t9.1+\n11\tja_JP\tJapanese (Japan)\t日语（日本）\t9.1+\n12\tko_KR\tKorean (Korea)\t朝鲜语（韩国）\t9.7+\n13\tes_MX\tSpanish (Mexico)\t西班牙语（墨西哥）\t9.1+\n14\tes_AR\tSpanish (Argentina)\t西班牙语（阿根廷）\t9.7+\n15\tpt_BR\tPortuguese (Brazil)\t葡萄牙语（巴西）\t9.1+\n16\ten_US\tEnglish (United States)\t英语（美国）\t9.1+\n17\ten_AU\tEnglish (Australia)\t英语（澳大利亚）\t9.1+\n18\tru_RU\tRussian (Russia)\t俄语（俄罗斯）\t9.1+\n19\ttr_TR\tTurkish (Turkey)\t土耳其语（土耳其）\t9.1+\n20\tms_MY\tMalay (Malaysia)\t马来语（马来西亚）\n21\ten_PH\tEnglish (Republic of the Philippines)\t英语（菲律宾共和国）\t10.5+\n22\ten_SG\tEnglish (Singapore)\t英语（新加坡）\t10.5+\n23\tth_TH\tThai (Thailand)\t泰语（泰国）\t9.7+\n24\tvn_VN\tVietnamese (Viet Nam)\t越南语（越南）\t9.7～13.9\n25\tvi_VN\tVietnamese (Viet Nam)\t越南语（越南）\t12.17+\n26\tid_ID\tIndonesian (Indonesia)\t印度尼西亚语（印度尼西亚）\n27\tzh_MY\tChinese (Malaysia)\t中文（马来西亚）\t10.5+\n28\tzh_CN\tChinese (China)\t中文（中国）\t9.7+\n29\tzh_TW\tChinese (Taiwan)\t中文（台湾）\t9.7+")
    print("请选择召唤师技能和装备的输出语言【默认为中文（中国）】：\nPlease select a language to output the summoner spells and items (the default option is zh_CN):\nNo.\tCODE\tLANGUAGE\t语言\tApplicable CDragon Data Patches") #本来考虑把可用CDragon数据版本放在第三列，但是后来发现表头名字太长了，索性放在最后了（I had considered putting "Applicable CDragon Data Patches" at the third column, but then found the header was too long. So I put it at the last column）
    language_ddragon = {1: {"CODE": "cs_CZ", "LANGUAGE (EN)": "Czech (Czech Republic)", "LANGUAGE (ZH)": "捷克语（捷克共和国）", "Applicable CDragon Data Patches": "7.1+"}, 2: {"CODE": "el_GR", "LANGUAGE (EN)": "Greek (Greece)", "LANGUAGE (ZH)": "希腊语（希腊）", "Applicable CDragon Data Patches": "9.1+"}, 3: {"CODE": "pl_PL", "LANGUAGE (EN)": "Polish (Poland)", "LANGUAGE (ZH)": "波兰语（波兰）", "Applicable CDragon Data Patches": "9.1+"}, 4: {"CODE": "ro_RO", "LANGUAGE (EN)": "Romanian (Romania)", "LANGUAGE (ZH)": "罗马尼亚语（罗马尼亚）", "Applicable CDragon Data Patches": "9.1+"}, 5: {"CODE": "hu_HU", "LANGUAGE (EN)": "Hungarian (Hungary)", "LANGUAGE (ZH)": "匈牙利语（匈牙利）", "Applicable CDragon Data Patches": "9.1+"}, 6: {"CODE": "en_GB", "LANGUAGE (EN)": "English (United Kingdom)", "LANGUAGE (ZH)": "英语（英国）", "Applicable CDragon Data Patches": "9.1+"}, 7: {"CODE": "de_DE", "LANGUAGE (EN)": "German (Germany)", "LANGUAGE (ZH)": "德语（德国）", "Applicable CDragon Data Patches": "7.1+"}, 8: {"CODE": "es_ES", "LANGUAGE (EN)": "Spanish (Spain)", "LANGUAGE (ZH)": "西班牙语（西班牙）", "Applicable CDragon Data Patches": "9.1+"}, 9: {"CODE": "it_IT", "LANGUAGE (EN)": "Italian (Italy)", "LANGUAGE (ZH)": "意大利语（意大利）", "Applicable CDragon Data Patches": "9.1+"}, 10: {"CODE": "fr_FR", "LANGUAGE (EN)": "French (France)", "LANGUAGE (ZH)": "法语（法国）", "Applicable CDragon Data Patches": "9.1+"}, 11: {"CODE": "ja_JP", "LANGUAGE (EN)": "Japanese (Japan)", "LANGUAGE (ZH)": "日语（日本）", "Applicable CDragon Data Patches": "9.1+"}, 12: {"CODE": "ko_KR", "LANGUAGE (EN)": "Korean (Korea)", "LANGUAGE (ZH)": "朝鲜语（韩国）", "Applicable CDragon Data Patches": "9.7+"}, 13: {"CODE": "es_MX", "LANGUAGE (EN)": "Spanish (Mexico)", "LANGUAGE (ZH)": "西班牙语（墨西哥）", "Applicable CDragon Data Patches": "9.1+"}, 14: {"CODE": "es_AR", "LANGUAGE (EN)": "Spanish (Argentina)", "LANGUAGE (ZH)": "西班牙语（阿根廷）", "Applicable CDragon Data Patches": "9.7+"}, 15: {"CODE": "pt_BR", "LANGUAGE (EN)": "Portuguese (Brazil)", "LANGUAGE (ZH)": "葡萄牙语（巴西）", "Applicable CDragon Data Patches": "9.1+"}, 16: {"CODE": "en_US", "LANGUAGE (EN)": "English (United States)", "LANGUAGE (ZH)": "英语（美国）", "Applicable CDragon Data Patches": "9.1+"}, 17: {"CODE": "en_AU", "LANGUAGE (EN)": "English (Australia)", "LANGUAGE (ZH)": "英语（澳大利亚）", "Applicable CDragon Data Patches": "9.1+"}, 18: {"CODE": "ru_RU", "LANGUAGE (EN)": "Russian (Russia)", "LANGUAGE (ZH)": "俄语（俄罗斯）", "Applicable CDragon Data Patches": "9.1+"}, 19: {"CODE": "tr_TR", "LANGUAGE (EN)": "Turkish (Turkey)", "LANGUAGE (ZH)": "土耳其语（土耳其）", "Applicable CDragon Data Patches": "9.1+"}, 20: {"CODE": "ms_MY", "LANGUAGE (EN)": "Malay (Malaysia)", "LANGUAGE (ZH)": "马来语（马来西亚）", "Applicable CDragon Data Patches": ""}, 21: {"CODE": "en_PH", "LANGUAGE (EN)": "English (Republic of the Philippines)", "LANGUAGE (ZH)": "英语（菲律宾共和国）", "Applicable CDragon Data Patches": "10.5+"}, 22: {"CODE": "en_SG", "LANGUAGE (EN)": "English (Singapore)", "LANGUAGE (ZH)": "英语（新加坡）", "Applicable CDragon Data Patches": "10.5+"}, 23: {"CODE": "th_TH", "LANGUAGE (EN)": "Thai (Thailand)", "LANGUAGE (ZH)": "泰语（泰国）", "Applicable CDragon Data Patches": "9.7+"}, 24: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "9.7～13.9"}, 25: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "12.17+"}, 26: {"CODE": "id_ID", "LANGUAGE (EN)": "Indonesian (Indonesia)", "LANGUAGE (ZH)": "印度尼西亚语（印度尼西亚）", "Applicable CDragon Data Patches": ""}, 27: {"CODE": "zh_MY", "LANGUAGE (EN)": "Chinese (Malaysia)", "LANGUAGE (ZH)": "中文（马来西亚）", "Applicable CDragon Data Patches": "10.5+"}, 28: {"CODE": "zh_CN", "LANGUAGE (EN)": "Chinese (China)", "LANGUAGE (ZH)": "中文（中国）", "Applicable CDragon Data Patches": "9.7+"}, 29: {"CODE": "zh_TW", "LANGUAGE (EN)": "Chinese (Taiwan)", "LANGUAGE (ZH)": "中文（台湾）", "Applicable CDragon Data Patches": "9.7+"}}
    language_cdragon = {}
    for i in language_ddragon:
        if language_ddragon[i]["CODE"] == "en_US":
            language_cdragon[language_ddragon[i]["CODE"]] = "default" #在CommunityDragon数据库上，美服正式服的数据资源代码是default，而不是小写的en_US（The code for English (US) data resources on CommunityDragon database is "default" instead of the lowercase of "en_US"）
        else:
            language_cdragon[language_ddragon[i]["CODE"]] = language_ddragon[i]["CODE"].lower()
    for i in range(1, 30):
        print(str(i) + "\t" + language_ddragon[i]["CODE"] + "\t" + language_ddragon[i]["LANGUAGE (EN)"] + "\t" + language_ddragon[i]["LANGUAGE (ZH)"] + "\t" + language_ddragon[i]["Applicable CDragon Data Patches"])
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
            spell_local_default = "离线数据（Offline Data）\\summoner.json"
            LoLItem_local_default = "离线数据（Offline Data）\\items.json"
            perk_local_default = "离线数据（Offline Data）\\perks.json"
            perkstyle_local_default = "离线数据（Offline Data）\\perkstyles.json"
            TFT_local_default = "离线数据（Offline Data）\\TFT.json"
            TFTChampion_local_default = "离线数据（Offline Data）\\tftchampions.json"
            TFTItem_local_default = "离线数据（Offline Data）\\tftitems.json"
            TFTCompanion_local_default = "离线数据（Offline Data）\\companions.json"
            TFTTrait_local_default = "离线数据（Offline Data）\\tfttraits.json"
            Arena_local_default = "离线数据（Offline Data）\\Arena.json"
            print("请选择数据资源获取模式：\nPlease select the data resource capture mode:\n1\t在线模式（Online）\n2\t离线模式（Offline）")
            prepareMode = input()
            switch_language = False
            while True:
                if prepareMode != "" and prepareMode[0] == "1":
                    switch_prepare_mode = False
                    #下面获取版本信息（The following code get the patch data）
                    try:
                        patches_initial = requests.get(patches_url)
                    except requests.exceptions.RequestException:
                        print('版本信息获取超时！正在尝试离线加载数据……\nPatch information capture timeout! Trying loading offline data ...\n请输入版本Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the patch Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(patches_local_default, patches_local_default))
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
                    else:
                        patches_initial = patches_initial.json()
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
                        print('召唤师技能信息获取超时！正在尝试离线加载数据……\nSummoner spell information capture timeout! Trying loading offline data ...\n请输入召唤师技能Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the summoner spell Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(spell_local_default, spell_local_default))
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
                        print('英雄联盟装备信息获取超时！正在尝试离线加载数据……\nLoL item information capture timeout! Trying loading offline data ...\n请输入英雄联盟装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the LoL item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(LoLItem_local_default, LoLItem_local_default))
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
                        print('基石符文信息获取超时！正在尝试离线加载数据……\nPerk information capture timeout! Trying loading offline data ...\n请输入基石符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perk Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(perk_local_default, perk_local_default))
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
                        print('符文系信息获取超时！正在尝试离线加载数据……\nPerkstyle information capture timeout! Trying loading offline data ...\n请输入符文系Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the perkstyle Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(perkstyle_local_default, perkstyle_local_default))
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
                        print('云顶之弈基础信息获取超时！正在尝试离线加载数据……\nTFT basic information capture timeout! Trying loading offline data ...\n请输入云顶之弈基础数据Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT basics Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(TFT_local_default, TFT_local_default))
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
                        print('云顶之弈英雄信息获取超时！正在尝试离线加载数据……\nTFT champion information capture timeout! Trying loading offline data ...\n请输入云顶之弈英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(TFTChampion_local_default, TFTChampion_local_default))
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
                        print('云顶之弈装备信息获取超时！正在尝试离线加载数据……\nTFT item information capture timeout! Trying loading offline data ...\n请输入云顶之弈装备Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT item Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(TFTItem_local_default, TFTItem_local_default))
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
                        print('云顶之弈小小英雄信息获取超时！正在尝试离线加载数据……\nTFT companion information capture timeout! Trying loading offline data ...\n请输入云顶之弈小小英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT companion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(TFTCompanion_local_default, TFTCompanion_local_default))
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
                        print('云顶之弈羁绊信息获取超时！正在尝试离线加载数据……\nTFT trait information capture timeout! Trying loading offline data ...\n请输入云顶之弈羁绊Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the TFT trait Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(TFTTrait_local_default, TFTTrait_local_default))
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
                        print('斗魂竞技场强化符文信息获取超时！正在尝试离线加载数据……\nArena augment information capture timeout! Trying loading offline data ...\n请输入斗魂竞技场强化符文Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“2”以转为离线模式。输入“0”以退出程序。\nPlease enter the Arena augment Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(Arena_local_default, Arena_local_default))
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
                    print('请在浏览器中打开以下网页，待加载完成后按Ctrl + S保存网页json文件至同目录的“离线数据（Offline Data）”文件夹下，并根据括号内的提示命名文件。\nPlease open the following URLs in a browser, then press Ctrl + S to save the online json files into the folder "离线数据（Offline Data）" under the same directory after the website finishes loading and rename the downloaded files according to the hints in the circle brackets.\n版本信息（versions.json）： %s\n召唤师技能（summoner.json）： %s\n英雄联盟装备（items.json）： %s\n基石符文（perks.json）： %s\n符文系（perkstyles.json）： %s\n云顶之弈基础信息（TFT.json）： %s\n云顶之弈棋子（tftchampions.json）： %s\n云顶之弈装备（tftitems.json）： %s\n云顶之弈小小英雄（companions.json）： %s\n云顶之弈羁绊（tfttraits.json）： %s\n斗魂竞技场强化符文（Arena.json）： %s' %(patches_url, spell_url, LoLItem_url, perk_url, perkstyle_url, TFT_url, TFTChampion_url, TFTItem_url, TFTCompanion_url, TFTTrait_url, Arena_url))
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
    #下面按照程序需求对数据资源进行一定的整理（The following code sort out the data resource according to the program's need）
    spells_initial = {} #spells为嵌套字典，键为召唤师技能序号，值为召唤师技能信息字典。一个键值对的示例如右：（Variable `spells` is a nested dictionary, whose keys are spellIds and values are spell information dictionaries. An example of the key-value pairs is shown as follows: ）{1: {"name": "净化", "description": "移除身上的所有限制效果（压制效果和击飞效果除外）和召唤师技能的减益效果，并且若在接下来的3秒里再次被施加限制效果时，新效果的持续时间会减少65%。", "summonerLevel": 9, "cooldown": 210, "gameModes": ["URF", "CLASSIC", "ARSR", "ARAM", "ULTBOOK", "WIPMODEWIP", "TUTORIAL", "DOOMBOTSTEEMO", "PRACTICETOOL", "FIRSTBLOOD", "NEXUSBLITZ", "PROJECT", "ONEFORALL"], "iconPath": "/lol-game-data/assets/DATA/Spells/Icons2D/Summoner_boost.png"}}
    for spell_iter in spell_initial:
        spell_id = spell_iter.pop("id")
        spells_initial[spell_id] = spell_iter
    LoLItems_initial = {} #LoLItems为嵌套字典，键为装备序号，值为装备信息字典。一个键值对的示例如右：（Variable `LoLItems` is a nested dictionary, whose keys are itemIds and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{1001: {"name": "鞋子", "description": "<mainText><stats><attention>25</attention>移动速度</stats></mainText><br>", "active": False, "inStore": True, "from": [], "to": [3111, 3006, 3005, 3009, 3020, 3047, 3117, 3158], "categories": ["Boots"], "maxStacks": 1, "requiredChampion": "", "requiredAlly": "", "requiredBuffCurrencyName": "", "requiredBuffCurrencyCost": 0, "specialRecipe": 0, "isEnchantment": False, "price": 300, "priceTotal": 300, "iconPath": "/lol-game-data/assets/ASSETS/Items/Icons2D/1001_Class_T1_BootsofSpeed.png"}}
    for LoLItem_iter in LoLItem_initial:
        LoLItem_id = LoLItem_iter.pop("id")
        LoLItems_initial[str(LoLItem_id)] = LoLItem_iter
    perks_initial = {} #perks为嵌套字典，键为符文序号，值为符文信息字典。一个键值对的示例如右：（Variable `perks` is a nested dictionary, whose keys are perkIds and values are perk information dictionaries. An example of the key-value pairs is shown as follows: ）{8369: {"name": "先攻", "majorChangePatchVersion": "11.23", "tooltip": "在进入与英雄战斗的@GraceWindow.2@秒内，对一名敌方英雄进行的攻击或技能将提供@GoldProcBonus@金币和<b>先攻</b>效果，持续@Duration@秒，来使你对英雄们造成<truedamage>@DamageAmp*100@%</truedamage>额外<truedamage>伤害</truedamage>，并提供<gold>{{ Item_Melee_Ranged_Split }}</gold>该额外伤害值的<gold>金币</gold>。<br><br>冷却时间：<scaleLevel>@Cooldown@</scaleLevel>秒<br><hr><br>已造成的伤害：@f1@<br>已提供的金币：@f2@", "shortDesc": "在你率先发起与英雄的战斗时，造成8%额外伤害，持续3秒，并基于该额外伤害提供金币。", "longDesc": "在进入与英雄战斗的0.25秒内，对一名敌方英雄进行的攻击或技能将提供5金币和<b>先攻</b>效果，持续3秒，来使你对英雄们造成<truedamage>8%</truedamage>额外<truedamage>伤害</truedamage>，并提供<gold>100% (远程英雄为70%)</gold>该额外伤害值的<gold>金币</gold>。<br><br>冷却时间：<scaleLevel>25 ~ 15</scaleLevel>秒", "recommendationDescriptor": "真实伤害，金币收入", "iconPath": "/lol-game-data/assets/v1/perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png", "endOfGameStatDescs": ["已造成的伤害：@eogvar1@", "已提供的金币：@eogvar2@"], "recommendationDescriptorAttributes": {}}}
    for perk_iter in perk_initial:
        perk_id = perk_iter.pop("id")
        perks_initial[perk_id] = perk_iter
    perkstyles_initial = {} #perkstyles为嵌套字典，键为符文系序号，值为符文系信息字典。一个键值对的示例如右：（Variable `perkstyles` is a nested dictionary, whose keys are perkstyle ids and values are perkstyle information dictionaries. An example of the key-value pairs is as follows: ）{8400: {"name": "坚决", "tooltip": "耐久和控制", "iconPath": "/lol-game-data/assets/v1/perk-images/Styles/7204_Resolve.png", "assetMap": {"p8400_s0_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k0.jpg", "p8400_s0_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8437.jpg", "p8400_s0_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8439.jpg", "p8400_s0_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s0_k8465.jpg", "p8400_s8000_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k0.jpg", "p8400_s8000_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8437.jpg", "p8400_s8000_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8439.jpg", "p8400_s8000_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8000_k8465.jpg", "p8400_s8100_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k0.jpg", "p8400_s8100_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8437.jpg", "p8400_s8100_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8439.jpg", "p8400_s8100_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8100_k8465.jpg", "p8400_s8200_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k0.jpg", "p8400_s8200_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8437.jpg", "p8400_s8200_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8439.jpg", "p8400_s8200_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8200_k8465.jpg", "p8400_s8300_k0": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k0.jpg", "p8400_s8300_k8437": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8437.jpg", "p8400_s8300_k8439": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8439.jpg", "p8400_s8300_k8465": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/p8400_s8300_k8465.jpg", "svg_icon": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/resolve_icon.svg", "svg_icon_16": "/lol-game-data/assets/v1/perk-images/Styles/Resolve/resolve_icon_16.svg"}, "isAdvanced": False, "allowedSubStyles": [8000, 8100, 8200, 8300], "subStyleBonus": [{"styleId": 8000, "perkId": 8414}, {"styleId": 8100, "perkId": 8454}, {"styleId": 8200, "perkId": 8415}, {"styleId": 8300, "perkId": 8416}], "slots": [{"type": "kKeyStone", "slotLabel": "", "perks": [8437, 8439, 8465]}, {"type": "kMixedRegularSplashable", "slotLabel": "蛮力", "perks": [8446, 8463, 8401]}, {"type": "kMixedRegularSplashable", "slotLabel": "抵抗", "perks": [8429, 8444, 8473]}, {"type": "kMixedRegularSplashable", "slotLabel": "生机", "perks": [8451, 8453, 8242]}, {"type": "kStatMod", "slotLabel": "进攻", "perks": [5008, 5005, 5007]}, {"type": "kStatMod", "slotLabel": "灵活", "perks": [5008, 5002, 5003]}, {"type": "kStatMod", "slotLabel": "防御", "perks": [5001, 5002, 5003]}], "defaultPageName": "坚决：巨像", "defaultSubStyle": 8200, "defaultPerks": [8437, 8446, 8444, 8451, 8224, 8237, 5008, 5002, 5001], "defaultPerksWhenSplashed": [8444, 8446], "defaultStatModsPerSubStyle": [{"id": "8000", "perks": [5005, 5002, 5001]}, {"id": "8100", "perks": [5008, 5002, 5001]}, {"id": "8200", "perks": [5008, 5002, 5001]}, {"id": "8300", "perks": [5007, 5002, 5001]}]}}
    for perkstyle_iter in perkstyle_initial["styles"]:
        perkstyle_id = perkstyle_iter.pop("id")
        perkstyles_initial[perkstyle_id] = perkstyle_iter
    TFTAugments_initial = {} #TFTAugments为嵌套字典，键为物件在LCU API上的表达形式，值为物件信息字典。一个键值对的示例如右：（Variable `TFTAugments` is a nested dictionary, whose keys are LCU API representation of items and values are item information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFT7_Consumable_NeekosHelpDragon": {"associatedTraits": [], "composition": [], "desc": "TFT7_Consumable_Description_Dragonling", "effects": {}, "from": None, "icon": "ASSETS/Maps/Particles/TFT/TFT7_Consumable_Dragonling.tex", "id": None, "incompatibleTraits": [], "name": "TFT7_Consumable_Name_Dragonling", "unique": False}}
    for item in TFT_initial["items"]:
        item_apiName = item.pop("apiName")
        TFTAugments_initial[item_apiName] = item
    TFTChampions_initial = {} #TFTChampions为嵌套字典，键为棋子在LCU API上的表达形式，值为棋子信息字典。一个键值对的示例如右：（Variable `TFTChampions` is a nested dictionary, whose keys are LCU API representation of TFT Champions and values are TFT Champion information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFT9_Aatrox": {"character_record": {"path": "Characters/TFT9_Aatrox/CharacterRecords/Root", "character_id": "TFT9_Aatrox", "rarity": 9, "display_name": "亚托克斯", "traits": [{"name": "暗裔", "id": "Set9_Darkin"}, {"name": "裁决战士", "id": "Set9_Slayer"}, {"name": "主宰", "id": "Set9_Armorclad"}], "squareIconPath": "/lol-game-data/assets/ASSETS/Characters/TFT9_Aatrox/HUD/TFT9_Aatrox_Square.TFT_Set9.png"}}}
    for TFTChampion_iter in TFTChampion_initial:
        champion_name = TFTChampion_iter.pop("name")
        TFTChampions_initial[champion_name] = TFTChampion_iter["character_record"]
    TFTItems_initial = {} #TTItems为嵌套字典，键为云顶之弈装备名称序号，值为云顶之弈装备信息字典。一个键值对的示例如右：（Variable `TFTItems` is a nested dictionary, whose keys are TFT item nameIds and values are TFT item information dictionaries. An example of the key-value pairs is shown as follows: ）{"TFTTutorial_Item_BFSword": {"guid": "9f6e75bb-7ba2-49aa-8724-04c550279034", "name": "暴风大剑", "id": 0, "color": {"R": 73, "B": 54, "G": 68, "A": 255}, "loadoutsIcon": "/lol-game-data/assets/ASSETS/Maps/Particles/TFT/Item_Icons/Standard/BF_Sword.png"}}
    for TFTItem_iter in TFTItem_initial:
        item_nameId = TFTItem_iter.pop("nameId")
        TFTItems_initial[item_nameId] = TFTItem_iter
    TFTCompanions_initial = {} #TFTCompanions为嵌套字典，键为小小英雄序号，值为小小英雄信息字典。一个键值对的示例如右：（Variable `TFTCompanions` is a nested dictionary, whose keys are companion contentIds and values are companion information dictionaries. An example of the key-value pairs is shown as follows: ）{"91f2e228-4e36-4dad-9a97-36036e3eca36": {"itemId": 13010, "name": "节奏大师 奥希雅", "loadoutsIcon": "/lol-game-data/assets/ASSETS/Loadouts/Companions/Tooltip_AkaliDragon_Beatmaker_Tier1.png", "description": "奥希雅是酷炫的具象化。它用毫不费力的语流，指挥着韵脚和节奏，甚至能让最出色的小小英雄们羡慕不休。", "level": 1, "speciesName": "奥希雅", "speciesId": 13, "rarity": "Epic", "rarityValue": 1, "isDefault": false, "upgrades": ["0e251d36-d86e-4c58-9b7f-bcee2376a408", "e3151dc2-c45c-4949-89e9-6afda3b2fd5f"], "TFTOnly": false}}
    for companion_iter in TFTCompanion_initial:
        contentId = companion_iter.pop("contentId")
        TFTCompanions_initial[contentId] = companion_iter
    TFTTraits_initial = {} #TFTTraits为嵌套字典，键为羁绊在LCU API上的表达形式，值为羁绊信息字典。一个键值对的示例如右：（Variable `TFTTraits` is a nested dictionary, whose keys are LCU API representation of traits and values are trait information dictionaries. An example of the key-value pairs is shown as follows: ）{"Assassin": {"display_name": "刺客", "set": "TFTSet1", "icon_path": "/lol-game-data/assets/ASSETS/UX/TraitIcons/Trait_Icon_Assassin.png", "tooltip_text": "固有：在战斗环节开始时，刺客们会跃至距离最远的敌人处。<br><br>刺客们会获得额外的暴击伤害和暴击几率。<br><br><expandRow>(@MinUnits@) +@CritAmpPercent@%暴击伤害和+@CritChanceAmpPercent@%暴击几率</expandRow><br>", "innate_trait_sets": [], "conditional_trait_sets": {2: {"effect_amounts": [{"name": "CritAmpPercent", "value": 75.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 5.0, "format_string": ""}], "min_units": 3, "max_units": 5, "style_name": "kBronze"}, 3: {"effect_amounts": [{"name": "CritAmpPercent", "value": 150.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 20.0, "format_string": ""}], "min_units": 6, "max_units": 8, "style_name": "kSilver"}, 4: {"effect_amounts": [{"name": "CritAmpPercent", "value": 225.0, "format_string": ""}, {"name": "CritChanceAmpPercent", "value": 30.0, "format_string": ""}], "min_units": 9, "max_units": 25000, "style_name": "kGold"}}}}
    for trait_iter in TFTTrait_initial:
        trait_id = trait_iter.pop("trait_id")
        conditional_trait_sets = {}
        for conditional_trait_set in trait_iter["conditional_trait_sets"]:
            style_idx = conditional_trait_set.pop("style_idx")
            conditional_trait_sets[style_idx] = conditional_trait_set
        trait_iter["conditional_trait_sets"] = conditional_trait_sets
        TFTTraits_initial[trait_id] = trait_iter
    ArenaAugments_initial = {} #ArenaAugments为嵌套字典，键为斗魂竞技场强化符文在LCU API上的表达形式，值为斗魂竞技场强化符文信息字典。一个键值对的实例如右：（Variable `ArenaAugments` is a nested dictionary, whose keys are LCU API representation of Arena augments and values are Arena augment information dictionaries. An example of the key-value pairs is shown as follows: ）{89: {"apiName": "WarmupRoutine", "calculations": {}, "dataValues": {"DamagePerStack": 0.009999999776482582, "MaxStacks": 24.0}, "desc": "获得召唤师技能<spellName>热身动作</spellName>。<br><br><rules><spellName>热身动作</spellName>可使你通过进行引导来提升你的伤害，持续至回合结束。</rules>", "iconLarge": "assets/ux/cherry/augments/icons/warmuproutine_large.2v2_mode_fighters.png", "iconSmall": "assets/ux/cherry/augments/icons/warmuproutine_small.2v2_mode_fighters.png", "name": "热身动作", "rarity": 0, "tooltip": "进行引导，每秒使你的伤害提升2%，至多至24%。<br><br>这个回合的额外伤害：@f1@<br>额外伤害的总和：@f2@"}}
    for ArenaAugment in Arena_initial["augments"]:
        ArenaAugment_id = ArenaAugment.pop("id")
        ArenaAugments_initial[ArenaAugment_id] = ArenaAugment
    #下面创建一个嵌套字典，用来判断所有版本的各种数据是否曾经获取过（The following code creates a nested dictionary to judge whether all kinds of data of a patch is once recaptured）
    TemplateBoolList = [False for i in range(len(bigPatches))] #为什么想到起个template作为后面字典的构成，是为了致敬后续出现的模板羁绊（The reason why I choose a name containing "template" to compose the following dictionary is in honor of the following "TemplateTrait"）
    recaptured_header = ["bigPatch", "spell", "LoLItem", "perk", "perkstyle", "TFTAugment", "TFTChampion", "TFTItem", "TFTCompanion", "TFTTrait", "ArenaAugment"]
    recaptured = {}
    for bigPatch in bigPatches:
        recaptured[bigPatch] = {}
        for recaptured_header_iter in recaptured_header:
            recaptured[bigPatch][recaptured_header_iter] = False
    #实际上，目前recaptured并未投入使用。原本打算使用这个字典，是因为有些时候在获取连续的几场版本相同的对局时，如果都没能正确地把数据对应到其名称，那么每一局都会提示将原始数据填充至单元格。但是后来想到，这样虽然会使得输出减少，但是一旦代码完成英雄联盟对局记录的数据整理，要开始整理具体每一场对局了，那么回归到最近的对局的获取时，由于这场场对局的数据可能标记为“曾经获取过”，那么程序可能不再获取这场对局的版本的数据。此时，程序刚完成对局记录的整理，而对局记录最后几场对局可能是老版本，有些新版本的数据是没有的。这样的话，本来可以通过重新获取新版本的数据来将原始数据对应到其名称，现在却因为新版本被标记为已获取过数据的版本，而导致其原始数据被保存下来（Actually, `recaptured` isn't used currently. The original plan on using this dictionary is due to that if the data of several continuous matches of the same gameVersion fail to be mapped to their names, then the prompt like `the original data will be adopted` will pop up for every match to be captured. But then I come to realize that the use of `recaptured` may reduce the output, but under the circumstance of finishing the data sorting of LoL match history, when the program is about to capture the latest specific game information and timeline, then the program may never fetch data of this patch. At that time, the program has just finished sorting out the match history. Maybe the data version then is an old version, and it doesn't include some new data. In that case, the program could have recaptured data of the latest patch to map data to the corresponding names, but because of the use of `recapture`, this latest patch is marked as "a patch that has been recaptured", and hence the original data instead of their corresponding labels are saved）
    #准备大区数据（Prepare server / platform data）
    platform_TENCENT = {"BGP1": "全网通区 男爵领域（Baron Zone）", "BGP2": "峡谷之巅（Super Zone）", "EDU1": "教育网专区（CRENET Server）", "HN1": "电信一区 艾欧尼亚（Ionia）", "HN2": "电信二区 祖安（Zaun）", "HN3": "电信三区 诺克萨斯（Noxus 1）", "HN4": "电信四区 班德尔城（Bandle City）", "HN5": "电信五区 皮尔特沃夫（Piltover）", "HN6": "电信六区 战争学院（the Institute of War）", "HN7": "电信七区 巨神峰（Mount Targon）", "HN8": "电信八区 雷瑟守备（Noxus 2）", "HN9": "电信九区 裁决之地（the Proving Grounds）", "HN10": "电信十区 黑色玫瑰（the Black Rose）", "HN11": "电信十一区 暗影岛（Shadow Isles）", "HN12": "电信十二区 钢铁烈阳（the Iron Solari）", "HN13": "电信十三区 水晶之痕（Crystal Scar）", "HN14": "电信十四区 均衡教派（the Kinkou Order）", "HN15": "电信十五区 影流（the Shadow Order）", "HN16": "电信十六区 守望之海（Guardian's Sea）", "HN17": "电信十七区 征服之海（Conqueror's Sea）", "HN18": "电信十八区 卡拉曼达（Kalamanda）", "HN19": "电信十九区 皮城警备（Piltover Wardens）", "PBE": "体验服 试炼之地（Chinese PBE）", "WT1": "网通一区 比尔吉沃特（Bilgewater）", "WT2": "网通二区 德玛西亚（Demacia）", "WT3": "网通三区 弗雷尔卓德（Freljord）", "WT4": "网通四区 无畏先锋（House Crownguard）", "WT5": "网通五区 恕瑞玛（Shurima）", "WT6": "网通六区 扭曲丛林（Twisted Treeline）", "WT7": "网通七区 巨龙之巢（the Dragon Camp）"}
    platform_RIOT = {"BR": "巴西服（Brazil）", "EUNE": "北欧和东欧服（Europe Nordic & East）", "EUW": "西欧服（Europe West）", "LAN": "北拉美服（Latin America North）", "LAS": "南拉美服（Latin America South）", "NA": "北美服（North America）", "OCE": "大洋洲服（Oceania）", "RU": "俄罗斯服（Russia）", "TR": "土耳其服（Turkey）", "JP": "日服（Japan）", "KR": "韩服（Republic of Korea）", "PBE": "测试服（Public Beta Environment）"}
    platform_GARENA = {"PH": "菲律宾服（Philippines）", "SG": "新加坡服（Singapore, Malaysia and Indonesia）", "TW": "台服（Taiwan, Hong Kong and Macau）", "VN": "越南服（Vietnam）", "TH": "泰服（Thailand）"}
    platform = {"TENCENT": "国服（TENCENT）", "RIOT": "外服（RIOT）", "GARENA": "竞舞（GARENA）"}
    print('''在腾讯代理的服务器上，如果查询某名玩家的对局记录，请尝试以下操作：\nTo search for the match history of a player on Tencent servers, try out the following operations:\n1. 在浏览器中打开本地主机网络协议：%s\n   Open the localhost IP in any browser: %s\n2. 尝试用以下用户名和密码登录：\n   Try logining in with the following username and password:\n   用户名（Username）：riot\n   密码（Password）：%s\n3. （如果可以立即知道一位玩家的玩家通用唯一识别码，则可以跳过第3和4步）在浏览器的地址栏中的地址最后，添加“lol-summoner/v1/summoners?name={name}”，其中{name}指的是召唤师名称编码后的字符串。当召唤师名称只包含英文字母和阿拉伯数字时，直接以召唤师名称去空格后的字符串代入{name}即可；当召唤师名称存在非美国标准信息交换代码时，以召唤师名称编码后的字符串代入{name}。\n(If a summoner's puuid can be immediately known, the user may skip Steps 3 and 4) Add to following the last character of the address in the browser's address bar "lol-summoner/v1/summoners?name={name}", where {name} refers to strings encoded from summonerName. When summonerName contains only English letters and Arabic numbers, simply substitute {name} with the strings with the spaces removed from summonerName. When a non-ASCII character exists in summonerName, substitute {name} by encoded summonerName.\n3.1 对于包含非美国标准信息交换代码的召唤师名称，如果可以得到该召唤师的精确名称（如通过复制到剪贴板），那么在Python中可以得知其编码后的字符串。在Python中使用from urllib.parse import quote命令引入quote函数，再使用quote(x)函数获取字符串x编码后的字符串。\nFor summonerNames that include non-ASCII characters, if the exact summonerName can be obtained (e. g. by copying to clipboard), then its encoded string can be returned in Python. In Python console, use "from urllib.parse import quote" to introduce the "quote" function. Then use quote(x) function to get the string encoded from the string x.\n4. 在lol-summoner/v1/summoners?name={name}返回的结果中找到puuid并复制。\n   Find "puuid" in the result returned by "lol-summoner/v1/summoners?name={name}" and copy it.\n5. 将地址栏中4位IP地址后的斜杠后的内容删除，再添加“lol-match-history/v1/products/lol/{puuid}/matches?begIndex=0&endIndex=20”或“lol-match-history/v1/products/tft/{puuid}/matches?begin=0&count=20”，其中{puuid}是事先获知的玩家通用唯一识别码，或者是第4步复制到剪贴板的puuid。\nDelete the content following the slash after the 4-bit IP address in the address bar and then add to the end "lol-match-history/v1/products/lol/{puuid}/matches?begIndex=0&endIndex=20" or "lol-match-history/v1/products/tft/{puuid}/matches?begin=0&count=20", where {puuid} refers to the puuid previously known, or copied to clipboard in Step 4.\n6. 尝试将上一步输入的地址中的“endIndex=”或“count=”后的数字依次替换成21、199、200和500，观察每次替换后返回的网页结果有没有变多。\nTry changing the number following "endIndex=" or "count=" in the last step into 21, 199, 200 and 500 one by one, and observe whether the returned webpage contains more information after each change.\n7. 教程完成，请继续执行本脚本……\n   Instruction finished. Please continue to run this program ...\n''' %(connection.address, connection.address, connection.auth_key))
    while True:
        #初始化所有数据资源（Initialize all data resources）
        print("正在初始化所有数据资源……\nInitializing all data resources ...\n")
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
        print('请输入要查询的召唤师名称，退出请输入“0”：\nPlease input the summoner name to be searched. Submit "0" to exit.')
        summoner_name = input()
        if summoner_name == "0":
            os._exit(0)
        elif summoner_name == "":
            print("请输入非空字符串！\nPlease input a string instead of null!")
            continue
        else:
            info = await (await connection.request("GET", "/lol-summoner/v1/summoners?name=" + quote(summoner_name))).json()
            if "errorCode" in info and info["httpStatus"] == 404:
                print("未找到" + summoner_name + "；请核对下名字并稍后再试。\n" + summoner_name + " was not found; verify the name and try again.")
            elif "accountId" in info:
                displayName = info["displayName"] #用于文件名命名（For use of file naming）
                current_puuid = info["puuid"] #用于核验对局是否包含该召唤师。此外，还用于扫描模式从对局的所有玩家信息中定位到该玩家（For use of checking whether the searched matches include this summoner. In addition, it's used for localization of this player from all players in a match in "scan" mode）
                #下面准备一些数据资源（The following code prepare data resources）
                gamemode = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
                gamemodes = {0: {"name": "自定义", "gameMode": "CUSTOM", "category": "CUSTOM"}}
                for gamemode_iter in gamemode:
                    gamemode_id = gamemode_iter.pop("id")
                    gamemodes_iter = {}
                    gamemodes_iter["name"] = gamemode_iter["name"]
                    gamemodes_iter["gameMode"] = gamemode_iter["gameMode"]
                    gamemodes_iter["category"] = gamemode_iter["category"]
                    gamemodes[gamemode_id] = gamemodes_iter
                maps = {8: {"zh_CN": "水晶之痕", "en_US": "Crystal Scar"}, 10: {"zh_CN": "扭曲丛林", "en_US": "Twisted Treeline"}, 11: {"zh_CN": "召唤师峡谷", "en_US": "Summoner's Rift"}, 12: {"zh_CN": "嚎哭深渊", "en_US": "Howling Abyss"}, 16: {"zh_CN": "宇宙遗迹", "en_US": "Cosmic Ruins"}, 18: {"zh_CN": "瓦罗兰城市公园", "en_US": "Valoran City Park"}, 20: {"zh_CN": "失控地点", "en_US": "Crash Site"}, 21: {"zh_CN": "百合与莲花的神庙", "en_US": "Temple of Lily and Lotus"}, 22: {"zh_CN": "聚点危机", "en_US": "Convergence"}, 30: {"zh_CN": "斗魂觉醒", "en_US": "RoW"}}
                summonerId = (await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json())["summonerId"]
                LoLChampion = await (await connection.request("GET", "/lol-champions/v1/inventories/" + str(summonerId) + "/champions")).json()
                LoLChampions = {}
                for LoLChampion_iter in LoLChampion:
                    LoLChampion_id = LoLChampion_iter.pop("id")
                    LoLChampions[LoLChampion_id] = LoLChampion_iter
                
                #print("召唤师信息如下：\nSummoner information is as follows:")
                ranked = await (await connection.request("GET", "/lol-ranked/v1/ranked-stats/" + info["puuid"])).json()
                tier = {"": "", "NONE": "没有段位", "IRON": "坚韧黑铁", "BRONZE": "英勇黄铜", "SILVER": "不屈白银", "GOLD": "荣耀黄金", "PLATINUM": "华贵铂金", "EMERALD": "流光翡翠", "DIAMOND": "璀璨钻石", "MASTER": "超凡大师", "GRANDMASTER": "傲世宗师", "CHALLENGER": "最强王者"}
                #print(info)

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
                    folder = "召唤师信息（Summoner Information）\\" + platform[region] + "\\" + platform_TENCENT[client_info["--rso_platform_id"]] + "\\" + displayName
                elif region == "GARENA":
                    folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[region] + "\\" + displayName
                else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
                    folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[region] + "\\" + displayName
                
                txt1name = "Summoner Profile - " + displayName + ".txt"
                while True:
                    try:
                        txtfile1 = open(os.path.join(folder, txt1name), "w", encoding = "utf-8")
                    except FileNotFoundError: #这里需要注意是否具有创建文件夹的权限。下同（Pay attention to the authority to create the folder. So are the following）
                        os.makedirs(folder)
                    else:
                        break
                try:
                    txtfile1.write(json.dumps(info, indent = 8, ensure_ascii = False))
                except UnicodeEncodeError:
                    print("召唤师信息文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nSummoner information text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                else:
                    print('召唤师信息已保存为“%s”。\nSummoner information is saved as "%s".\n' %(os.path.join(folder, txt1name), os.path.join(folder, txt1name)))
                txtfile1.close()
                currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                pkl1name = "Intermediate Object - info (Summoner Profile) - %s (%s).pkl" %(displayName, currentTime)
                #with open(os.path.join(folder, pkl1name), "wb") as IntObj1:
                    #pickle.dump(info, IntObj1)
                if "errorCode" in ranked and ranked["httpStatus"] == 404: #国服测试服的排位数据API未知（API of ranked stats on Chinese PBE is unknown）
                    info_data = {"项目": ["帐户序号", "召唤师名称", "内置名称", "升级进度", "生涯公开性", "生涯背景序号", "玩家通用唯一识别码", "大乱斗重随点", "召唤师序号", "召唤师等级", "目前经验", "升级所需经验"], "Items": ["accountID", "displayName", "internalName", "percentCompleteforNextLevel", "privacy", "profileIconId", "puuid", "rerollPoints", "summonerId", "summonerLevel", "xpSinceLastLevel", "xpUntilNextLevel"], "值": [info["accountId"], info["displayName"], info["internalName"], info["percentCompleteForNextLevel"], info["privacy"], info["profileIconId"], info["puuid"], info["rerollPoints"]["numberOfRolls"], info["summonerId"], info["summonerLevel"], info["xpSinceLastLevel"], info["xpUntilNextLevel"]]}
                else:
                    info_data = {"项目": ["帐户序号", "召唤师名称", "内置名称", "升级进度", "生涯公开性", "生涯背景序号", "玩家通用唯一识别码", "大乱斗重随点", "召唤师序号", "召唤师等级", "目前经验", "升级所需经验", "已获得的排位赛段奖励物品序号", "过往赛季最高赛段", "过往赛季最高赛段分级", "过往赛季结束赛段", "过往赛季结束赛段分级"], "Items": ["accountID", "displayName", "internalName", "percentCompleteforNextLevel", "privacy", "profileIconId", "puuid", "rerollPoints", "summonerId", "summonerLevel", "xpSinceLastLevel", "xpUntilNextLevel", "earnedRegaliaRewardIds", "highestPreviousSeasonAchievedTier", "highestPreviousSeasonAchievedDivision", "highestPreviousSeasonEndTier", "highestPreviousSeasonEndDivision"], "值": [info["accountId"], info["displayName"], info["internalName"], info["percentCompleteForNextLevel"], info["privacy"], info["profileIconId"], info["puuid"], info["rerollPoints"]["numberOfRolls"], info["summonerId"], info["summonerLevel"], info["xpSinceLastLevel"], info["xpUntilNextLevel"], ranked["earnedRegaliaRewardIds"], tier[ranked["highestPreviousSeasonAchievedTier"]], ranked["highestPreviousSeasonAchievedDivision"], tier[ranked["highestPreviousSeasonEndTier"]], ranked["highestPreviousSeasonEndDivision"]]}
                info_df = pandas.DataFrame(data = info_data)
                
                #print("召唤师英雄成就如下：\nSummoner champion mastery is as follows:")
                mastery = await (await connection.request("GET", "/lol-collections/v1/inventories/" + str(info["summonerId"]) + "/champion-mastery")).json()
                if "errorCode" in mastery: #美测服13.20版本需要使用玩家通用唯一识别码代替召唤师序号来查询英雄成就信息（summonerId is replaced by puuid to search for champion mastery information in Patch 13.20 on PBE. Extra information: A capture of the champion mastery at 2023年10月5日16:08:00 (UTC+8) gave the following information: {"errorCode": "RPC_ERROR", "httpStatus": 500, "implementationDetails": {}, "message": "Error requesting summoner champion masteries for 2772370761401792: {\"message\":\"{\\\"httpStatus\\\":500,\\\"errorCode\\\":\\\"UNHANDLED_SERVER_SIDE_ERROR\\\",\\\"message\\\":\\\"Invlaid puuid 2772370761401792\\\",\\\"implementationDetails\\\":\\\"filtered\\\"}\",\"failureCode_int\":500}"}）
                    mastery = await (await connection.request("GET", "/lol-collections/v1/inventories/" + current_puuid + "/champion-mastery")).json()
                #print(mastery)
                txt2name = "Champion Mastery - " + displayName + ".txt"
                while True:
                    try:
                        txtfile2 = open(os.path.join(folder, txt2name), "w", encoding = "utf-8")
                    except FileNotFoundError:
                        os.makedirs(folder)
                    else:
                        break
                try:
                    txtfile2.write(json.dumps(mastery, indent = 8, ensure_ascii = False))
                except UnicodeEncodeError:
                    print("召唤师英雄成就文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nSummoner champion mastery text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                else:
                    print('召唤师英雄成就已保存为“%s”。\nSummoner champion mastery is saved as "%s".\n' %(os.path.join(folder, txt2name), os.path.join(folder, txt2name)))
                txtfile2.close()
                currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                pkl2name = "Intermediate Object - mastery (Champion Mastery) - %s (%s).pkl" %(displayName, currentTime)
                #with open(os.path.join(folder, pkl2name), "wb") as IntObj2:
                    #pickle.dump(mastery, IntObj2)
                mastery_header = {"champion": "英雄", "alias": "名称", "championLevel": "成就等级", "championPoints": "总成就点数", "championPointsSinceLastLevel": "当前等级成就点数", "championPointsUntilNextLevel": "升级所需成就点数", "chestGranted": "已赚取海克斯宝箱", "highestGrade": "当前赛季最高评分", "lastPlayTime": "上次使用时间", "tokensEarned": "成就代币数量"}
                mastery_header_keys = list(mastery_header.keys())
                mastery_data = {}
                for i in range(len(mastery_header)):
                    key = mastery_header_keys[i]
                    mastery_data[key] = []
                    if i == 0:
                        for j in range(len(mastery)):
                            mastery_data[key].append(LoLChampions[mastery[j]["championId"]]["name"])
                    elif i == 1:
                        for j in range(len(mastery)):
                            mastery_data[key].append(LoLChampions[mastery[j]["championId"]]["alias"])
                    elif i == 8:
                        for j in range(len(mastery)): #这里需要将时间戳转换为标准格式的时间（Here the timestamp is going to be converted into time in standard format）
                            lastPlayTime = time.localtime(mastery[j][key] // 1000) #英雄联盟中的时间戳精确到微妙，也就是放大了1000倍（Timestamps in LCU api are accurate to milliseconds, namely multiplied by 1000）
                            lastPlayTime_standard = time.strftime("%Y年%m月%d日%H:%M:%S", lastPlayTime)
                            mastery_data[key].append(lastPlayTime_standard)
                    else:
                        for j in range(len(mastery)):
                            mastery_data[key].append(mastery[j][key])
                mastery_statistics_display_order = range(len(mastery_header))
                mastery_data_organized = {}
                for i in mastery_statistics_display_order:
                    key = mastery_header_keys[i]
                    mastery_data_organized[key] = [mastery_header[key]] + mastery_data[key]
                mastery_df = pandas.DataFrame(data = mastery_data_organized)
                mastery_df.loc[:, "chestGranted"].replace({True: "√", False: ""}, inplace = True)

                if "errorCode" in ranked and ranked["httpStatus"] == 404: #从13.15版本开始，国服体验服的排位信息和对局记录可以正常查询（From Patch 13.15 on, rank data and match history can be searched on Chinese PBE server）
                    print("该服务器暂不支持排位数据和对局记录查询！\nThis server doesn't support ranked data and match history lookup!")
                    print("是否导出以上召唤师数据至Excel中？（输入任意键导出，否则不导出）\nDo you want to export the above data into Excel? (Press any key to export or null to refuse exporting)")
                    export = input()
                    if export != "":
                        excel_name = "Summoner Profile - " + displayName + ".xlsx"
                        while True:
                            try:
                                with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                                    info_df.to_excel(excel_writer = writer, sheet_name = "Profile")
                                    mastery_df.to_excel(excel_writer = writer, sheet_name = "Champion Mastery")
                            except PermissionError:
                                print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                                input()
                            except FileNotFoundError:
                                os.makedirs(folder)
                            else:
                                break
                    continue
                    
                #print("召唤师排位数据如下：\nSummoner ranked data are as follows:") #排位赛部分数据位于召唤师信息中（Part of ranked data are in Profile Sheet）
                #print(ranked)
                txt3name = "Ranked Data - " + displayName + ".txt"
                while True:
                    try:
                        txtfile3 = open(os.path.join(folder, txt3name), "w", encoding = "utf-8")
                    except FileNotFoundError:
                        os.makedirs(folder)
                    else:
                        break
                try:
                    txtfile3.write(json.dumps(ranked, indent = 8, ensure_ascii = False))
                except UnicodeEncodeError:
                    print("召唤师排位数据文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nSummoner ranked data text generation failure! Please check if the summoner name includes any abnormal characters!\n")
                else:
                    print('召唤师排位数据已保存为“%s”。\nSummoner ranked data are saved as "%s".\n' %(os.path.join(folder, txt3name), os.path.join(folder, txt3name)))
                txtfile3.close()
                currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                pkl3name = "Intermediate Object - ranked (Rank) - %s (%s).pkl" %(displayName, currentTime)
                #with open(os.path.join(folder, pkl3name), "wb") as IntObj3:
                    #pickle.dump(ranked, IntObj3)
                ranked_header = {"division": "分级", "isProvisional": "定位中", "leaguePoints": "胜点", "losses": "负场", "miniSeriesProgress": "定位赛/晋级赛进展", "previousSeasonAchievedDivision": "过往赛季取得赛段分级", "previousSeasonAchievedTier": "过往赛季取得赛段", "previousSeasonEndDivision": "过往赛季结束赛段分级", "previousSeasonEndTier": "过往赛季结束赛段", "provisionalGameThreshold": "总定位场次", "provisionalGamesRemaining": "剩余定位场次", "queueType": "对局类型", "ratedRating": "段位点", "ratedTier": "段位", "tier": "段位", "warnings": "警告消息", "wins": "胜场"}
                queueType = {"RANKED_SOLO_5x5": "单人/双人", "RANKED_FLEX_SR": "灵活 5V5", "RANKED_TFT": "云顶之弈", "RANKED_TFT_PAIRS": "2V0", "RANKED_TFT_DOUBLE_UP": "双人作战 (BETA测试)", "RANKED_TFT_TURBO": "狂暴模式", "CHERRY": "斗魂竞技场"} #2V0模式仅美测服可用（RANKED_TFT_PAIRS is only available on PBE）
                ranked_header_keys = list(ranked_header.keys())
                ranked_data = {}
                for i in range(len(ranked["queues"])):
                    if ranked["queues"][i]["queueType"] == "RANKED_TFT_TURBO":
                        turboNo = i + 1 #这里需要记录狂暴模式排位信息在ranked["queues"]的位置，方便后续的合并操作（Here the location of rank information of TFT_TURBO needs to be saved to make it easy to merge later）
                        break
                for i in range(len(ranked_header_keys)):
                    key = ranked_header_keys[i]
                    ranked_data[key] = [ranked_header[key]]
                    if i == 0 or i == 5 or i == 7:
                        for j in range(len(ranked["queues"])):
                            value = ranked["queues"][j][key]
                            if value == "NA":
                                ranked_data[key].append("")
                            else:
                                ranked_data[key].append(value)
                    elif i == 1:
                        for j in range(len(ranked["queues"])):
                            value = ranked["queues"][j][key]
                            if value:
                                ranked_data[key].append("√")
                            else:
                                ranked_data[key].append("")
                    elif i == 6 or i == 8 or i == 14:
                        for j in range(len(ranked["queues"])):
                            ranked_data[key].append(tier[ranked["queues"][j][key]])
                    elif i == 11:
                        for j in range(len(ranked["queues"])):
                            ranked_data[key].append(queueType[ranked["queues"][j][key]])
                    else:
                        for j in range(len(ranked["queues"])):
                            ranked_data[key].append(ranked["queues"][j][key])
                ranked_statistics_display_order = [11, 14, 0, 2, 13, 12, 16, 3, 1, 9, 10, 4, 6, 5, 8, 7, 15]
                ranked_data_organized = {}
                for i in ranked_statistics_display_order:
                    if not i in [13, 14, 2, 12]: #这里要实现将两个段位参数和两个胜点各合并为一个参数，因此不能简单沿用ranked_data中相应的列表（Here I want to merge the two pairs of parameters - ratedTier and tier, leaguePoints and ratedRating - into two single parameters respectively, so I shouldn't simply inherit the two lists in ranked_data）
                        key = ranked_header_keys[i]
                        ranked_data_organized[key] = ranked_data[key]
                    elif i == 14: #段位放在分级的前面，所以在i = 14时进行特殊处理（Since tier is designed to be in front of division, measures are taken specifically when i equals 14）
                        key = "tier / ratedTier"
                        ranked_data_organized[key] = ranked_data["tier"][:turboNo] + [ranked_data["ratedTier"][turboNo]] + ranked_data["tier"][turboNo + 1:]
                    elif i == 2: #胜点放在段位点的前面，所以在i = 2时进行特殊处理（Since leaguePoints is designed to be in front of ratedRating, measures are taken specifically when i equals 2）
                        key = "leaguePoints / ratedRating"
                        ranked_data_organized[key] = ranked_data["leaguePoints"][:turboNo] + [ranked_data["ratedRating"][turboNo]] + ranked_data["leaguePoints"][turboNo + 1:]
                    else: #i = 2或14时合并完成，所以i = 12和13可以舍弃（Merge is finished when i equals 2 or 14, so the case where i equals 12 or 13 can be abandoned）
                        continue
                ranked_df = pandas.DataFrame(data = ranked_data_organized)
                
                game_info_dfs = {}
                game_timeline_dfs = {}
                LoLHistory_searched = True
                TFTHistory_searched = True
                info_exist_error = {} #当获取对局记录反复出现异常时，为了保证第二次没有获取到的报错信息在导出时不会覆盖上一次使用该程序时导出的正确工作表，设置该列表。列表中的某个元素为True，代表对应的对局记录将能正常导出。由于对局信息往往比对局时间轴更易接受关注，这里只以LoLGame_info的完整性作为exist_error的追加依据（When the match history service encounters errors frequently, to make sure the error information won't overlay the normally captured match information in the last time using this program, this list is declared here. When some element in this list is True, the corresponding match information / timeline can be exported as usual. Because the LoLGame_info is basically more focused on than LoLGame_timeline, True/False is appended to exist_error only based on the integrity of LoLGame_info）
                timeline_exist_error = {}
                main_player_included = {} #当通过列表来查询对局记录时，有可能某场对局并不包含该召唤师（When searching the match history using a list, maybe the summoner isn't present in some match）
                match_reserve_strategy = {} #当某场对局不包含该召唤师时，决定最后导出时是否需要保存该对局记录（Decides whether to reserve the matches when they don't include the searched summoner at present）
                
                print("是否查询英雄联盟对局记录？（输入任意键查询，否则不查询）\nSearch LoL matches? (Input anything to search or null to skip searching LoL matches)")
                if input() != "":
                    #print("召唤师英雄联盟对局记录如下：\nMatch history (LoL) is as follows:")
                    LoLHistory_get = True
                    while True:
                        try:
                            LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=500" %(info["puuid"]))).json()
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
                                        LoLHistory = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=500" %(info["puuid"]))).json()
                                elif "body was empty" in LoLHistory["message"]:
                                    LoLHistory_get = False
                                    print("这位召唤师从5月1日起就没有进行过任何英雄联盟对局。\nThis summoner hasn't played any LoL game yet since May 1st.")
                                    break
                            txt4name = "Match History (LoL) - " + displayName + ".txt"
                            while True:
                                try:
                                    txtfile4 = open(os.path.join(folder, txt4name), "w", encoding = "utf-8")
                                except FileNotFoundError:
                                    os.makedirs(folder)
                                else:
                                    break
                            try:
                                txtfile4.write(json.dumps(LoLHistory, indent = 8, ensure_ascii = False))
                            except UnicodeEncodeError:
                                print("召唤师英雄联盟对局记录文本文档生成失败！请检查召唤师名称和所选语言是否包含不常用字符！\nSummoner LoL match history text generation failure! Please check if the summoner name and the chosen language include any abnormal characters!\n")
                            txtfile4.close()
                            currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                            pkl4name = "Intermediate Object - LoLHistory - %s (%s).pkl" %(displayName, currentTime)
                            #with open(os.path.join(folder, pkl4name), "wb") as IntObj4:
                                #pickle.dump(LoLHistory, IntObj4)
                            if count > 3:
                                LoLHistory_get = False
                                print("英雄联盟对局记录获取失败！请等待官方修复对局记录服务！\nLoL match history capture failure! Please wait for Tencent to fix the match history service!")
                                break
                            print('该玩家共进行%d场英雄联盟对局。近期对局（最近20场）已保存为“%s”。\nThis player has played %d LoL matches. Recent matches (last 20 played) are saved as "%s".\n' %(LoLHistory["games"]["gameCount"], os.path.join(folder, txt4name), LoLHistory["games"]["gameCount"], os.path.join(folder, txt4name)))
                        except KeyError:
                            print(LoLHistory)
                            LoLHistory_url = "%s/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=200" %(connection.address, info["puuid"])
                            print("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续，或输入任意字符以切换召唤师（Please open the following website, type in the username and password accordingly and press Enter to continue or input anything to switch to another summoner）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s" %(LoLHistory_url, connection.auth_key))
                            cont = input()
                            if cont == "":
                                continue
                            else:
                                LoLHistory_get = False
                                break
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
                            print("第%d/%d场对局（对局序号：%s）召唤师技能信息（%s）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to spells of Patch %s ... Times tried: %d" %(i + 1, len(games), game["gameId"], spellId, spell_recapture, spellPatch_adopted, spellId, i + 1, len(games), game["gameId"], spellPatch_adopted, spell_recapture))
                            while True:
                                try:
                                    spell = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[language_code])).json()
                                except requests.exceptions.JSONDecodeError:
                                    spellPatch_deserted = spellPatch_adopted
                                    spellPatch_adopted = bigPatches[bigPatches.index(spellPatch_adopted) + 1]
                                    spell_recapture = 1
                                    print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT augments of Patch %s ... Times tried: %d" %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture))
                                except requests.exceptions.RequestException:
                                    if spell_recapture < 3:
                                        spell_recapture += 1
                                        print("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Try changing to spells of Patch %s ... Times tried: %d" %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture))
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
                            print("第%d/%d场对局（对局序号：%s）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to LoL items of Patch %s ... Times tried: %d" %(i + 1, len(games), game["gameId"], LoLItemID, LoLItem_recapture, LoLItemPatch_adopted, LoLItemID, i + 1, len(games), game["gameId"], LoLItemPatch_adopted, LoLItem_recapture))
                            while True:
                                try:
                                    LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                                except requests.exceptions.JSONDecodeError:
                                    LoLItemPatch_deserted = LoLItemPatch_adopted
                                    LoLItemPatch_adopted = bigPatches[bigPatches.index(LoLItemPatch_adopted) + 1]
                                    LoLItem_recapture = 1
                                    print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                                except requests.exceptions.RequestException:
                                    if LoLItem_recapture < 3:
                                        LoLItem_recapture += 1
                                        print("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
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
                    
                    print('请输入要查询的英雄联盟对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出英雄联盟对局查询“0”：\nPlease enter the LoL match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to quit searching for LoL matches.')
                    LoLMatchIDs = []
                    matches_to_remove = [] #在扫描模式下，当从本地文件获取的对局从API重新获取出现异常时，处理策略是输出异常信息并跳过该对局，而不是将其直接从对局序号列表中去除，因为这样会使循环乱套。而后面的info_exist_error、timeline_exist_error、main_player_included和match_reserve_strategy只会在该对局正常获取时才会统计。所以一旦出现数据获取失败的对局，在最后导出数据时，“if match_reserve_strategy[i]:”语句会出现“IndexError: list index out of range”报错（Under scan mode, when an exception occurred during crawling matches with LoLMatchIDs obtained from local files from API, the strategy is to print the exception and skip this match, instead of directly removing them from the matchID list, for the removal will disturb the loop. However, the variables info_exist_error, timeline_exist_error, main_player_included and match_reserve_strategy only work when the matches are crawled from the database as expected. So once a match fails to be captured, during xlsx file export at the end of the program, an "IndexError: list index out of range" exception will emerge from the statement "if match_reserve_strategy[i]:"）
                    scan = False #用于将扫描获取的历史记录保存为后缀为“ - Scan”的工作表，防止后续【一键查询】时会把【本地重查】辛辛苦苦得到的对局记录覆盖掉。这样也有利于手动重整，即每次【一键查询】后，可手动将新增的对局记录加到后缀为“ - Scan”的工作表中（Determines whether to save the match histories to a sheet postfixxed with " - Scan", in case the subsequent [One-Key Query] overwrites the match histories fetched and sorted hard by [Local Recheck]. It also helps to manual arrangement. That is, after each [One-Key Query], the user may manually add the new match histories to the sheet postfixxed with " - Scan"）
                    while True:
                        matchID = input()
                        fetched_info = True #是否正常存储对局信息（Whether the match information is captured as expected）
                        fetched_timeline = True #是否正常存储对局时间轴（Whether the match timeline is captured as expected）
                        if matchID == "":
                            continue
                        elif matchID == "0":
                            break
                        else:
                            if matchID == "3":
                                print("请设置需要查询的对局索引下界和上界，以空格为分隔符（输入空字符以默认近200场对局）：\nPlease set the begIndex and endIndex of the matches to be searched, split by space (Enter an empty string to search for the recent 200 matches):") #在13.13版本以前，腾讯代理的服务器只支持近20场对局查询（Before Patch 13.13, Tencent servers only provide search of the latest 20 matches）
                                while True:
                                    gameIndex = input()
                                    if gameIndex == "":
                                        begIndex, endIndex = 0, 200
                                    else:
                                        try:
                                            begIndex, endIndex = gameIndex.split()
                                            begIndex, endIndex = int(begIndex), int(endIndex)
                                        except ValueError:
                                            print("请以空格为分隔符输入对局索引的自然数类型的下界和上界！\nPlease enter two nonegative integers as the begIndex and endIndex of the matches split by space!")
                                            continue
                                    break
                                LoLMatchIDs = list(map(str, gameID[begIndex:endIndex]))
                            elif matchID == "scan":
                                filenames = os.listdir(folder)
                                for filename in filenames:
                                    if filename.startswith("Match Information (LoL) - "):
                                        LoLMatchIDs.append(filename.split("-")[-1][:-4])
                                if LoLMatchIDs == list():
                                    print("尚未保存过该玩家的数据！\nYou haven't saved this summoner's matches yet!\n")
                                    break
                                else:
                                    LoLMatchIDs = list(map(int, LoLMatchIDs)) #正确的对局顺序应当是根据整型对局序号的大小来排列的（The correct order of matches should be according to the size of LoLMatchIDs of integer type）
                                    LoLMatchIDs.sort(reverse = True)
                                    LoLMatchIDs = list(map(str, LoLMatchIDs))
                                    print("检测到%d场对局。是否继续？（输入任意键以重新输入要查询的对局序号，否则重新获取这些对局的数据）\nDetected %d matches. Continue? (Input any nonempty string to return to the last step of inputting the matchID, or null to recapture those matches' data)" %(len(LoLMatchIDs), len(LoLMatchIDs)))
                                    recapture = input()
                                    if recapture != "":
                                        LoLMatchIDs = [] #如果没有这句语句，那么当重新输入对局序号列表时，从本地文件中检测到的对局数量相比上次检测数的基础上会多出本地文件中包含的对局的数量（Without this assignment, when reinputting the matchID list, the number of matches detected from the local files will become more than that of the last time's check）
                                        print('请输入要查询的英雄联盟对局序号，批量查询对局请输入对局序号列表，批量查询全部对局请输入“3”，退出英雄联盟对局查询“0”：\nPlease enter the LoL match ID to check. Submit a list containing matchIDs to search in batches. Submit "3" to search the currently stored history in batches. Submit "0" to quit searching for LoL matches.')
                                        continue
                                    scan = True #不应直接放到matchID == "scan"语句下，因为有可能历史记录不是扫描获取的，而是一开始就获取的。比如“尚未保存过该玩家的数据”，或者提示“检测到若干场对局。是否继续”选择了否（This statement shouldn't follow closely after the statement `matchID == "scan"`, because the match history might be obtained in the beginning instead of by scanning. Cases are that a summoner's data has never been saved locally, and that the user inputs something in face of the hint "Detected some matches. Continue?"）
                                    spells = copy.deepcopy(spells_initial) #重新查询历史记录，应当从最新版本开始查起（Researching the history should start from the latest patch）
                                    LoLItems = copy.deepcopy(LoLItems_initial)
                                    #官方的历史记录最多保留200场对局的个人信息。这里要实现将待保存对局全部整理成一个类似于历史记录的布局的功能（要查看历史记录的原来的布局，可以先不使用scan选项，生成Excel文件后查看“Match History”工作表的布局），所以不再使用前面的历史记录，而是从每一局中提取信息，整合成一张历史记录表。因此，大部分代码复制自前面一部分的代码（Official match history holds personal history of at most 200 matches. Here I want to implement a function to sort the information of all matches into a table like the original match history table. (To check this format for the first time, please don't choose the "scan" option and view the "Match History" sheet of the generated xlsx file.) Therefore, the previous history_df is abandoned. Instead, information in the match history is extracted from all matches to form the table subsequently）
                                    gameIndex_iter = 0
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
                                    for matchID in LoLMatchIDs:
                                        LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                                        
                                        #尝试修复错误（Try to fix the error）
                                        if "errorCode" in LoLGame_info:
                                            count = 0
                                            if LoLGame_info["httpStatus"] == 404:
                                                print("未找到序号为" + matchID + "的回放文件！将忽略该序号。\nMatch file with matchID " + matchID + " not found! The program will ignore this matchID.")
                                            if "500 Internal Server Error" in LoLGame_info["message"]:
                                                if error_occurred == False:
                                                    print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                                    error_occurred = True
                                                while "errorCode" in LoLGame_info and "500 Internal Server Error" in LoLGame_info["message"] and count <= 3:
                                                    count += 1
                                                    print("正在第%d次尝试获取对局%s信息……\nTimes trying to capture Match %s: No. %d ..." %(count, matchID, matchID, count))
                                                    LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                                            elif "Connection timed out after " in LoLGame_info["message"]:
                                                fetched_info = False
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
                                                fetched_info = False
                                                print("对局%s信息获取失败！\nMatch %s information capture failure!" %(matchID, matchID))
                                        
                                        if "errorCode" in LoLGame_info:
                                            print(LoLGame_info, end = "\n\n")
                                            continue #重新获取历史与后续输出对局信息和时间轴是两码事。后面info_exist_error、timeline_exist_error、main_player_included和match_reserve_strategy位于输出对局信息和时间轴的代码中，因此这里不需要记录待去除的对局。如果这里记录，后面再次记录，由于是列表追加而不是集合添加元素，重复记录的对局在再次从对局序号列表中去除时会触发IndexError（Recapturing the match history and outputting match history and timeline are not the samething. Because the variables exist_error, timeline_exist_error, main_player_included and match_reserve_strategy is located in the code that output match information and timeline, here's no need to record the matches to remove. Otherwise, with the following code recording these matches again, removal of the repeatedly recorded matches from the matchID list will trigger the IndexError, since the matches are recorded by appending elements to a list, instead of adding elements into a set）
                                        gameIndex_iter += 1
                                        gameIndex.append(gameIndex_iter)
                                        #定位该召唤师（Find the index of this player in a match）
                                        for participantId in range(len(LoLGame_info["participantIdentities"])):
                                            if LoLGame_info["participantIdentities"][participantId]["player"]["puuid"] == current_puuid:
                                                break
                                        #获取游戏序号（Capture gameId）
                                        gameID.append(LoLGame_info["gameId"])
                                        #获取当前召唤师名称（Capture current summonerName）
                                        summonerName.append(LoLGame_info["participantIdentities"][participantId]["player"]["summonerName"])
                                        #获取游戏开始时间（Capture gameCreationDate）
                                        gameCreationDate.append(LoLGame_info["gameCreationDate"][:10] + " " + LoLGame_info["gameCreationDate"][11:23])
                                        #获取游戏持续时长（Capture gameDuration）
                                        duration = LoLGame_info["gameDuration"]
                                        gameDuration.append(str(duration // 60) + ":" + "%02d" %(duration % 60))
                                        #获取队列序号和模式名称（Capture queueID and name of the mode）
                                        queueID.append(LoLGame_info["queueId"])
                                        if LoLGame_info["queueId"] == 0:
                                            gameMode.append("CUSTOM")
                                            gameModeName.append("自定义")
                                        else:
                                            gameMode.append(LoLGame_info["gameMode"])
                                            gameModeName.append(gamemodes[LoLGame_info["queueId"]]["name"])
                                        #获取地图序号（Capture mapID）
                                        mapID.append(LoLGame_info["mapId"])
                                        #获取对局版本号（Capture version）
                                        version = LoLGame_info["gameVersion"]
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
                                            champion.append(LoLChampions[LoLGame_info["participants"][participantId]["championId"]]["name"])
                                        except KeyError:
                                            champion.append("")
                                        try:
                                            alias.append(LoLChampions[LoLGame_info["participants"][participantId]["championId"]]["alias"])
                                        except KeyError:
                                            alias.append(LoLGame_info["participants"][participantId]["championId"])
                                        level.append(LoLGame_info["participants"][participantId]["stats"]["champLevel"])
                                        #获取召唤师技能1和2（Capture spell 1 and 2）
                                        spell1Id = LoLGame_info["participants"][participantId]["spell1Id"]
                                        spell2Id = LoLGame_info["participants"][participantId]["spell2Id"]
                                        try:
                                            spellId = spell1Id
                                            test = spells[spellId]["name"]
                                            spellId = spell2Id
                                            test = spells[spellId]["name"]
                                        except KeyError: #在国服体验服的对局序号为696083511的对局中，出现了召唤师技能序号为37225015和4964（In a match with matchId 696083511 on Chinese PBE, there're two spells with spellIds 37225015 and 4964）
                                            spellPatch_adopted = bigVersion
                                            spell_recapture = 1
                                            print("第%d/%d场对局（对局序号：%s）召唤师技能信息（%s）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to spells of Patch %s ... Times tried: %d" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellId, spell_recapture, spellPatch_adopted, spellId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellPatch_adopted, spell_recapture))
                                            while True:
                                                try:
                                                    spell = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    spellPatch_deserted = spellPatch_adopted
                                                    spellPatch_adopted = bigPatches[bigPatches.index(spellPatch_adopted) + 1]
                                                    spell_recapture = 1
                                                    print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT augments of Patch %s ... Times tried: %d" %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture))
                                                except requests.exceptions.RequestException:
                                                    if spell_recapture < 3:
                                                        spell_recapture += 1
                                                        print("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Try changing to spells of Patch %s ... Times tried: %d" %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture))
                                                    else:
                                                        print("网络环境异常！第%d/%d场对局（对局序号：%s）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchID: %s)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellId, spellId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                        #spell1.append(LoLGame_info["participants"][participantId]["spell1Id"])
                                                        break
                                                else:
                                                    print("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted))
                                                    spells = {}
                                                    for spell_iter in spell:
                                                        spell_id = spell_iter.pop("id")
                                                        spells[spell_id] = spell_iter
                                                    break
                                        try:
                                            spell1.append(spells[LoLGame_info["participants"][participantId]["spell1Id"]]["name"])
                                        except KeyError:
                                            spell1.append(LoLGame_info["participants"][participantId]["spell1Id"])
                                        try:
                                            spell2.append(spells[LoLGame_info["participants"][participantId]["spell2Id"]]["name"])
                                        except KeyError:
                                            spell2.append(LoLGame_info["participants"][participantId]["spell2Id"])
                                        #获取召唤师装备信息（Capture summoner items）
                                        stats = LoLGame_info["participants"][participantId]["stats"]
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
                                                test = LoLItems[str(item1Id)]
                                            if item2Id != 0:
                                                LoLItemID = item2Id
                                                test = LoLItems[str(item2Id)]
                                            if item3Id != 0:
                                                LoLItemID = item3Id
                                                test = LoLItems[str(item3Id)]
                                            if item4Id != 0:
                                                LoLItemID = item4Id
                                                test = LoLItems[str(item4Id)]
                                            if item5Id != 0:
                                                LoLItemID = item5Id
                                                test = LoLItems[str(item5Id)]
                                            if item6Id != 0:
                                                LoLItemID = item6Id
                                                test = LoLItems[str(item6Id)]
                                            if ornamentId != 0:
                                                LoLItemID = ornamentId
                                                test = LoLItems[str(ornamentId)]
                                        except KeyError:
                                            LoLItemPatch_adopted = bigVersion
                                            LoLItem_recapture = 1
                                            print("第%d/%d场对局（对局序号：%s）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemID, LoLItem_recapture, LoLItemPatch_adopted, LoLItemID, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemPatch_adopted, LoLItem_recapture))
                                            while True:
                                                try:
                                                    LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                                                except requests.exceptions.JSONDecodeError:
                                                    LoLItemPatch_deserted = LoLItemPatch_adopted
                                                    LoLItemPatch_adopted = bigPatches[bigPatches.index(LoLItemPatch_adopted) + 1]
                                                    LoLItem_recapture = 1
                                                    print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                                                except requests.exceptions.RequestException:
                                                    if LoLItem_recapture < 3:
                                                        LoLItem_recapture += 1
                                                        print("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
                                                    else:
                                                        print("网络环境异常！第%d/%d场对局（对局序号：%s）的装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the item (%s) of Match %d / %d (matchID: %s)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), gameID, LoLItemID, LoLItemID, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
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
                                        print('对局记录重查进度（Match history recheck process）：%d/%d\t对局序号（MatchID）： %s' %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                    LoLHistory_data = {}
                                    for i in list(LoLHistory_header.keys()):
                                        LoLHistory_data[i] = [LoLHistory_header[i]] + eval(i) #因为这里要用到eval，所以前面的变量名必须和LoLHistory_header中的键保持一致（Since eval() is used here, those lists variable name must correspond to variable LoLHistory_header's keys）
                                    LoLHistory_df = pandas.DataFrame(data = LoLHistory_data)
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
                            spells = copy.deepcopy(spells_initial)
                            LoLItems = copy.deepcopy(LoLItems_initial) #接下来查询具体的对局信息和时间轴，使用的可能并不是历史记录中记载的对局序号形成的列表。考虑实际使用需求，这里对于装备的合适版本信息采取的思路是默认从最新版本开始获取，如果有装备不存在于最新版本的装备信息，则获取游戏信息中存储的版本对应的装备信息。该思路仍然有问题，详见后续关于美测服的装备获取的注释（The next step is to capture the information and timeline for each specific match, which may not originate from the matchIDs recorded in the match history. Considering the practical use, here the stream of thought for an appropriate version for items is to get items' information from the latest patch, and if some item doesn't exist in the items information of the latest patch, then get the items of the version corresponding to the game according to gameVersion recorded in the match information. There's a flaw of this idea. Please refer to the annotation regarding PBE data crawling for further solution）
                            for matchID in LoLMatchIDs:
                                LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                                #print(LoLGame_info)
                                LoLGame_timeline = await (await connection.request("GET", "/lol-match-history/v1/game-timelines/" + matchID)).json()
                                #print(LoLGame_timeline)

                                #尝试修复错误（Try to fix the error）
                                if "errorCode" in LoLGame_info:
                                    count = 0
                                    if LoLGame_info["httpStatus"] == 404:
                                        print("未找到序号为" + matchID + "的回放文件！将忽略该序号。\nMatch file with matchID " + matchID + " not found! The program will ignore this matchID.")
                                        matches_to_remove.append(matchID)
                                        continue
                                    if "500 Internal Server Error" in LoLGame_info["message"]:
                                        if error_occurred == False:
                                            print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_info and "500 Internal Server Error" in LoLGame_info["message"] and count <= 3:
                                            count += 1
                                            print("正在第%d次尝试获取对局%s信息……\nTimes trying to capture Match %s: No. %d ..." %(count, matchID, matchID, count))
                                            history = await (await connection.request("GET", "/lol-match-history/v1/products/lol/%s/matches?begIndex=0&endIndex=500" %(info["puuid"]))).json()
                                    elif "Connection timed out after " in LoLGame_info["message"]:
                                        fetched_info = False
                                        print("对局信息保存超时！请检查网速状况！\nGame information saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                                    elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"]:
                                        if error_occurred == False:
                                            print("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_info and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_info["message"] and count <= 3:
                                            count += 1
                                            print("正在第%d次尝试获取对局%s信息……\nTimes trying to capture Match %s: No. %d ..." %(count, matchID, matchID, count))
                                            LoLGame_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                                    elif "could not convert GAMHS data to match-history format" in LoLGame_info["message"]:
                                        TFTGame = True
                                    if count > 3:
                                        fetched_info = False
                                        print("对局%s信息获取失败！\nMatch %s information capture failure!" %(matchID, matchID))
                                
                                if "errorCode" in LoLGame_info:
                                    print(LoLGame_info, end = "\n\n")
                                    info_exist_error[int(matchID)] = True
                                    for i in error_header:
                                        LoLGame_info_error = {"项目": list(error_header.values()), "items": list(error_header.keys()), "值": [LoLGame_info[j] for j in error_header_keys]}
                                        LoLGame_info_df = pandas.DataFrame(data = LoLGame_info_error)
                                else:
                                    reserve = True #决定是否保存对局的文本文档。match_reserve_strategy变量决定的是是否将不包含主召唤师的对局记录导出到Excel中（Decides whether to save the matches into txt files. The variable match_reserve_strategy decides whether to export the matches which don't include the main summoner into Excel）
                                    participant = []
                                    for i in LoLGame_info["participantIdentities"]:
                                        participant.append(i["player"]["puuid"])
                                    if current_puuid in participant: #之所以使用玩家通用唯一识别码，而不是用召唤师名称来识别对局是否包含主玩家，是因为该玩家可能使用过改名卡。这里也没有选择帐户序号，这是因为保存在对局中的各玩家的帐户序号竟然是0！（The reason why the puuid instead of the displayName or summonerName is used to identify whether the matches contain the main player is that the player may have used name changing card. AccountId isn't chosen here, because all players' accountIds saved in the match fetched from 127 API is 0, to my surprise!）
                                        main_player_included[int(matchID)] = True
                                        match_reserve_strategy[int(matchID)] = True
                                    else:
                                        main_player_included[int(matchID)] = False
                                        reserve = False #由于从文本文件中可以提取该召唤师的对局序号，所以需要保证保留下来的文本文件都包含该召唤师。因此，如果一场对局不包含该召唤师，就不应该把这场对局保存下来（Because a summoner's matchIDs can be extracted from the saved txt files, it needs to be guaranteed that all saved txt files belong to this summoner. Therefore, if a match doesn't include this summoner, then it shouldn't be saved into txt files）
                                        print("警告：对局%s所在对局不包含该玩家！是否仍要保持该对局？（输入任意键以保留该对局，否则舍弃该对局）\nWarning: The match %s doesn't include the current player! Continue? (Input any nonempty string to reserve this match, or null to abandon it)" %(matchID, matchID))
                                        cont = input()
                                        if cont == "":
                                            match_reserve_strategy[int(matchID)] = False
                                        else:
                                            match_reserve_strategy[int(matchID)] = True
                                    info_exist_error[int(matchID)] = False
                                    currentPlatformId = LoLGame_info["participantIdentities"][0]["player"]["currentPlatformId"]
                                    save = True #指示保存是否成功，成功则输出保存进度，不成功则提示生成失败（Indicates whether the saving process is successful. If so, output the saving process, otherwise give a hint of generation failure）
                                    if reserve:
                                        txt6name = "Match Information (LoL) - " + currentPlatformId + "-" + matchID + ".txt"
                                        while True:
                                            try:
                                                txtfile6 = open(os.path.join(folder, txt6name), "w", encoding = "utf-8")
                                            except FileNotFoundError:
                                                os.makedirs(folder)
                                            else:
                                                break
                                        try:
                                            txtfile6.write(json.dumps(LoLGame_info, indent = 8, ensure_ascii = False))
                                        except UnicodeEncodeError:
                                            print("对局%s信息文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nMatch %s information text generation failure! Please check if the summoner name includes any abnormal characters!" %(matchID, matchID))
                                            save = False
                                        txtfile6.close()
                                        currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                                        pkl6name = "Intermediate Object - Match Information (LoL) - %s-%s.pkl" %(currentPlatformId, matchID)
                                        #with open(os.path.join(folder, pkl6name), "wb") as IntObj6:
                                            #pickle.dump(LoLGame_info, IntObj6)
                                        txt7name = "Match Timeline (LoL) - " + currentPlatformId + "-" + matchID + ".txt"
                                        while True:
                                            try:
                                                txtfile7 = open(os.path.join(folder, txt7name), "w", encoding = "utf-8")
                                            except FileNotFoundError:
                                                os.makedirs(folder)
                                            else:
                                                break
                                        try:
                                            txtfile7.write(json.dumps(LoLGame_timeline, indent = 8, ensure_ascii = False))
                                        except UnicodeEncodeError:
                                            print("对局%s时间轴文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nMatch %s timeline text generation failure! Please check if the summoner name includes any abnormal characters!" %(matchID, matchID))
                                            save = False
                                        txtfile7.close()
                                        currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                                        pkl7name = "Intermediate Object - Match Timeline (LoL) - %s-%s.pkl" %(currentPlatformId, matchID)
                                        #with open(os.path.join(folder, pkl7name), "wb") as IntObj7:
                                            #pickle.dump(LoLGame_timeline, IntObj7)
                                        if save:
                                            print('保存进度（Saving process）：%d/%d\t对局序号（MatchID）： %s' %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                    LoLGame_info_header = {"participantId": "玩家序号", "currentPlatformId": "当前大区", "platformId": "原大区", "profileIcon": "召唤师图标序号", "puuid": "玩家通用唯一识别码", "summonerId": "召唤师序号", "summonerName": "召唤师名称", "champion": "选用英雄", "alias": "名称", "spell1": "召唤师技能1", "spell2": "召唤师技能2", "teamId": "阵营", "assists": "助攻", "causedEarlySurrender": "发起提前投降", "champLevel": "英雄等级", "combatPlayerScore": "战斗得分", "damageDealtToObjectives": "对战略点的总伤害", "damageDealtToTurrets": "对防御塔的总伤害", "damageSelfMitigated": "自我缓和的伤害", "deaths": "死亡", "doubleKills": "双杀", "earlySurrenderAccomplice": "同意提前投降", "firstBloodAssist": "协助获得第一滴血", "firstBloodKill": "第一滴血", "firstInhibitorAssist": "协助摧毁第一座召唤水晶", "firstInhibitorKill": "摧毁第一座召唤水晶", "firstTowerAssist": "协助摧毁第一座塔", "firstTowerKill": "摧毁第一座塔", "gameEndedInEarlySurrender": "提前投降导致比赛结束", "gameEndedInSurrender": "投降导致比赛结束", "goldEarned": "金币获取", "goldSpent": "金币使用", "inhibitorKills": "摧毁召唤水晶", "item1": "装备1", "item2": "装备2", "item3": "装备3", "item4": "装备4", "item5": "装备5", "item6": "装备6", "ornament": "饰品", "killingSprees": "大杀特杀", "kills": "击杀", "largestCriticalStrike": "最大暴击伤害", "largestKillingSpree": "最高连杀", "largestMultiKill": "最高多杀", "longestTimeSpentLiving": "最长生存时间", "magicDamageDealt": "造成的魔法伤害", "magicDamageDealtToChampions": "对英雄的魔法伤害", "magicalDamageTaken": "承受的魔法伤害", "neutralMinionsKilled": "击杀野怪", "neutralMinionsKilledEnemyJungle": "击杀敌方野区野怪", "neutralMinionsKilledTeamJungle": "击杀我方野区野怪", "objectivePlayerScore": "战略点玩家得分", "pentaKills": "五杀", "perk0": "符文1", "perk0EndOfGameStatDescs": "符文1游戏结算数据", "perk0Var1": "符文1：参数1", "perk0Var2": "符文1：参数2", "perk0Var3": "符文1：参数3", "perk1": "符文2", "perk1EndOfGameStatDescs": "符文2游戏结算数据", "perk1Var1": "符文2：参数1", "perk1Var2": "符文2：参数2", "perk1Var3": "符文2：参数3", "perk2": "符文3", "perk2EndOfGameStatDescs": "符文3游戏结算数据", "perk2Var1": "符文3：参数1", "perk2Var2": "符文3：参数2", "perk2Var3": "符文3：参数3", "perk3": "符文4", "perk3EndOfGameStatDescs": "符文4游戏结算数据", "perk3Var1": "符文4：参数1", "perk3Var2": "符文4：参数2", "perk3Var3": "符文4：参数3", "perk4": "符文5", "perk4EndOfGameStatDescs": "符文5游戏结算数据", "perk4Var1": "符文5：参数1", "perk4Var2": "符文5：参数2", "perk4Var3": "符文5：参数3", "perk5": "符文6", "perk5EndOfGameStatDescs": "符文6游戏结算数据", "perk5Var1": "符文6：参数1", "perk5Var2": "符文6：参数2", "perk5Var3": "符文6：参数3", "perkPrimaryStyle": "主系", "perkSubStyle": "副系", "physicalDamageDealt": "造成的物理伤害", "physicalDamageDealtToChampions": "对英雄的物理伤害", "physicalDamageTaken": "承受的物理伤害", "playerAugment1": "强化符文1", "playerAugment1_rarity": "强化符文1等级", "playerAugment2": "强化符文2", "playerAugment2_rarity": "强化符文2等级", "playerAugment3": "强化符文3", "playerAugment3_rarity": "强化符文3等级", "playerAugment4": "强化符文4", "playerAugment4_rarity": "强化符文4等级", "playerScore0": "玩家得分1", "playerScore1": "玩家得分2", "playerScore2": "玩家得分3", "playerScore3": "玩家得分4", "playerScore4": "玩家得分5", "playerScore5": "玩家得分6", "playerScore6": "玩家得分7", "playerScore7": "玩家得分8", "playerScore8": "玩家得分9", "playerScore9": "玩家得分10", "playerSubteamId": "子阵营序号", "quadraKills": "四杀", "sightWardsBoughtInGame": "购买洞察之石", "subteamPlacement": "队伍排名", "teamEarlySurrendered": "队伍提前投降", "timeCCingOthers": "控制得分", "totalDamageDealt": "造成的伤害总和", "totalDamageDealtToChampions": "对英雄的伤害总和", "totalDamageTaken": "承受伤害", "totalHeal": "治疗伤害", "totalMinionsKilled": "击杀小兵", "totalPlayerScore": "玩家总得分", "totalScoreRank": "总得分排名", "totalTimeCrowdControlDealt": "控制时间", "totalUnitsHealed": "治疗单位数", "tripleKills": "三杀", "trueDamageDealt": "造成真实伤害", "trueDamageDealtToChampions": "对英雄的真实伤害", "trueDamageTaken": "承受的真实伤害", "turretKills": "摧毁防御塔", "unrealKills": "六杀及以上", "visionScore": "视野得分", "visionWardsBoughtInGame": "购买控制守卫", "wardsKilled": "摧毁守卫", "wardsPlaced": "放置守卫", "win/lose": "胜负", "bannedChampion": "禁用英雄", "bannedAlias": "名称"}
                                    LoLGame_info_data = {} ####这里将对局的数据放在一个字典中，键为统计量，值为由所有玩家的数据组成的列表（Here the whole match data are stored in a dictionary whose keys are statistics and values are lists composed of corresponding data of all players）
                                    LoLGame_info_header_keys = list(LoLGame_info_header.keys())
                                    team_color = {100: "蓝方", 200: "红方"}
                                    subteam_color = {0: "", 1: "魄罗", 2: "小兵", 3: "迅捷蟹", 4: "石甲虫"} #仅用于斗魂竞技场（Only for Soul Fighter mode）
                                    augment_rarity = {0: "白银", 4: "黄金", 8: "棱彩"}
                                    win = {True: "胜利", False: "失败"}
                                    player_count = len(LoLGame_info["participantIdentities"])
                                    LoLItem_recapture = 0
                                    for i in range(len(LoLGame_info_header)): #考虑到i按照代码中LoLGame_info_header的键的顺序遍历字典，可以将中间同一级别的属性按照相同方法输出。于是有了接下来的一些判断语句（Considering variable i traverses the dictionary following the order of LoLGame_info_header's keys, attributes under the same level can be output in the same manner. That's why there're several If-statements in the following code）
                                        key = LoLGame_info_header_keys[i]
                                        LoLGame_info_data[key] = [] #各项目初始化（Initialize every feature / column）
                                        for j in range(player_count):
                                            if i == 0:
                                                LoLGame_info_data[key].append(LoLGame_info["participantIdentities"][j][key])
                                            elif i >= 1 and i <= 6:
                                                LoLGame_info_data[key].append(LoLGame_info["participantIdentities"][j]["player"][key])
                                            elif i == 7:
                                                try:
                                                    LoLGame_info_data[key].append(LoLChampions[LoLGame_info["participants"][j]["championId"]]["name"])
                                                except KeyError:
                                                    LoLGame_info_data[key].append("")
                                            elif i == 8:
                                                try:
                                                    LoLGame_info_data[key].append(LoLChampions[LoLGame_info["participants"][j]["championId"]]["alias"])
                                                except KeyError:
                                                    LoLGame_info_data[key].append(LoLGame_info["participants"][j]["championId"])
                                            elif i == 9 or i == 10: #需要注意电脑玩家的召唤师技能序号都是0（Note that Spell Ids of bot players are both 0s）
                                                spellId = LoLGame_info["participants"][j][key + "Id"]
                                                if spellId == 0:
                                                    LoLGame_info_data[key].append("")
                                                else:
                                                    try:
                                                        to_append = spells[spellId]["name"]
                                                    except KeyError:
                                                        spellPatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                        spell_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%s）召唤师技能信息（%s）获取失败！正在第%d次尝试改用%s版本的召唤师技能信息……\nSpell information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to spells of Patch %s ... Times tried: %d" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellId, spell_recapture, spellPatch_adopted, spellId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellPatch_adopted, spell_recapture))
                                                        while True:
                                                            try:
                                                                spell = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/summoner-spells.json" %(spellPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError:
                                                                spellPatch_deserted = spellPatch_adopted
                                                                spellPatch_adopted = bigPatches[bigPatches.index(spellPatch_adopted) + 1]
                                                                spell_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT augments of Patch %s ... Times tried: %d" %(spellPatch_deserted, spell_recapture, spellPatch_adopted, spellPatch_deserted, spellPatch_adopted, spell_recapture))
                                                            except requests.exceptions.RequestException:
                                                                if spell_recapture < 3:
                                                                    spell_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的召唤师技能信息……\nYour network environment is abnormal! Try changing to spells of Patch %s ... Times tried: %d" %(spell_recapture, spellPatch_adopted, spellPatch_adopted, spell_recapture))
                                                                else:
                                                                    print("网络环境异常！第%d/%d场对局（对局序号：%s）的召唤师技能信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the spell (%s) of Match %d / %d (matchID: %s)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellId, spellId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                    to_append = spellId
                                                                    break
                                                            else:
                                                                print("已改用%s版本的召唤师技能信息。\nSpell information changed to Patch %s." %(spellPatch_adopted, spellPatch_adopted))
                                                                spells = {}
                                                                for spell_iter in spell:
                                                                    spell_id = spell_iter.pop("id")
                                                                    spells[spell_id] = spell_iter
                                                                try:
                                                                    to_append = spells[spellId]["name"]
                                                                except KeyError:
                                                                    print("【%d. %s】第%d/%d场对局（对局序号：%s）召唤师技能信息（%s）获取失败！将采用原始数据！\n[%d. %s] Spell information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(i, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, spellId, i, key, spellId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                    to_append = spellId
                                                                    break
                                                                else:
                                                                    break
                                                    LoLGame_info_data[key].append(to_append)
                                            elif i == 11:
                                                LoLGame_info_data[key].append(team_color[LoLGame_info["participants"][j]["teamId"]])
                                            elif i >= 12 and i <= 32 or i >= 40 and i <= 53 or i >= 86 and i <= 88 or i >= 97 and i <= 131 and i != 107:
                                                LoLGame_info_data[key].append(LoLGame_info["participants"][j]["stats"][key])
                                            elif i >= 33 and i <= 39:
                                                if i >= 33 and i <= 38:
                                                    LoLItemID = LoLGame_info["participants"][j]["stats"][key[:-1] + str(i - 33)]
                                                else:
                                                    LoLItemID = LoLGame_info["participants"][j]["stats"]["item6"]
                                                if LoLItemID == 0:
                                                    LoLGame_info_data[key].append("")
                                                else:
                                                    try:
                                                        to_append = LoLItems[str(LoLItemID)]["name"]
                                                    except KeyError:
                                                        LoLItemPatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                        LoLItem_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%s）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nLoL item information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemID, LoLItem_recapture, LoLItemPatch_adopted, LoLItemID, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemPatch_adopted, LoLItem_recapture))
                                                        while True:
                                                            try:
                                                                LoLItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/items.json" %(LoLItemPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError:
                                                                LoLItemPatch_deserted = LoLItemPatch_adopted
                                                                LoLItemPatch_adopted = bigPatches[bigPatches.index(LoLItemPatch_adopted) + 1]
                                                                LoLItem_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLItemPatch_deserted, LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_deserted, LoLItemPatch_adopted, LoLItem_recapture))
                                                            except requests.exceptions.RequestException:
                                                                if LoLItem_recapture < 3:
                                                                    LoLItem_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的英雄联盟装备信息……\nYour network environment is abnormal! Try changing to LoL items of Patch %s ... Times tried: %d" %(LoLItem_recapture, LoLItemPatch_adopted, LoLItemPatch_adopted, LoLItem_recapture))
                                                                else:
                                                                    print("网络环境异常！第%d/%d场对局（对局序号：%s）的装备信息（%s）将采用原始数据！\nNetwork error! The original data will be used for the item (%s) of Match %d / %d (matchID: %s)!" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemID, LoLItemID, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                    to_append = LoLItemID
                                                                    break
                                                            else:
                                                                print("已改用%s版本的英雄联盟装备信息。\nLoL item information changed to Patch %s." %(LoLItemPatch_adopted, LoLItemPatch_adopted))
                                                                LoLItems = {}
                                                                for LoLItem_iter in LoLItem:
                                                                    LoLItem_id = LoLItem_iter.pop("id")
                                                                    LoLItems[str(LoLItem_id)] = LoLItem_iter
                                                                try:
                                                                    to_append = LoLItems[str(LoLItemID)]["name"]
                                                                except KeyError:
                                                                    print("【%d. %s】第%d/%d场对局（对局序号：%s）装备信息（%s）获取失败！将采用原始数据！\n[%d. %s] LoL item information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(i, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, LoLItemID, i, key, LoLItemID, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                    to_append = LoLItemID
                                                                    break
                                                                else:
                                                                    break
                                                    LoLGame_info_data[key].append(to_append)
                                            elif i >= 54 and i <= 85:
                                                if i <= 83:
                                                    if (i - 54) % 5 == 0 or (i - 54) % 5 == 1:
                                                        subkey = LoLGame_info_header_keys[54 + (i - 54) // 5 * 5]
                                                        perkId = LoLGame_info["participants"][j]["stats"][subkey]
                                                        if perkId == 0: #在一些非常规模式（如新手训练）的对局中，玩家可能没有携带任何符文（In matches with unconventional game mode (e.g. TUTORIAL), maybe the player doesn't take any runes）
                                                            LoLGame_info_data[key].append("")
                                                        else:
                                                            perk_captured = True
                                                            try:
                                                                perk_to_append = perks[perkId] #这里并没有直接使用to_append作为要追加的数据。这是考虑到游戏结算数据需要依赖符文的正确获取。如果符文数据没有从CommunityDragon数据库中如期获取，那么也无法整理得到游戏结算数据。所以这里退而求其次，先检查对局信息中的符文序号是否存在于准备好的符文数据中，如果不存在则按照类似的错误修复机制重新获取符文数据。如果最终的符文数据包含对局信息中的符文序号，那么符文的名称和游戏结算数据可以正常追加。否则，符文的名称将被符文序号代替，而游戏结算数据将被空字符串代替（Here the variable `to_append` isn't used as the data to be appended. This is based on the consideration that EndOfGameStatDescs depends on the successful capture of runes. If runes data aren't fetched as expected from CommunityDragon database, then the EndOfGameStatDescs data can't be concluded, either. Therefore, this line of code seeks for the second best: first check if perkId is in the prepared runes data and then handle the exception if not. If the final runes data contain the perkId, then the name and EndOfGameStatDescs of a perk can be appended. Otherwise, the name and EndOfGameStatDescs of a perk is to be replaced by the perkId and an empty string, respectively）
                                                            except KeyError:
                                                                perkPatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                                perk_recapture = 1
                                                                print("第%d/%d场对局（对局序号：%s）基石符文信息（%s）获取失败！正在第%d次尝试改用%s版本的基石符文信息……\nRunes information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to runes of Patch %s ... Times tried: %d" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkId, perk_recapture, perkPatch_adopted, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkPatch_adopted, perk_recapture))
                                                                while True:
                                                                    try:
                                                                        perk = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perks.json" %(perkPatch_adopted, language_cdragon[language_code])).json()
                                                                    except requests.exceptions.JSONDecodeError:
                                                                        perkPatch_deserted = perkPatch_adopted
                                                                        perkPatch_adopted = bigPatches[bigPatches.index(perkPatch_adopted) + 1]
                                                                        perk_recapture = 1
                                                                        print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to runes of Patch %s ... Times tried: %d" %(perkPatch_deserted, perk_recapture, perkPatch_adopted, perkPatch_deserted, perkPatch_adopted, perk_recapture))
                                                                    except requests.exceptions.RequestException:
                                                                        if perk_recapture < 3:
                                                                            perk_recapture += 1
                                                                            print("网络环境异常！正在第%d次尝试改用%s版本的基石符文信息……\nYour network environment is abnormal! Try changing to runes of Patch %s ... Times tried: %d" %(perk_recapture, perkPatch_adopted, perkPatch_adopted, perk_recapture))
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
                                                                            print("【%d. %s】第%d/%d场对局（对局序号：%s）基石符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] Runes information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(i, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkId, i, key, perkId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                            perk_captured = False
                                                                            break
                                                                        else:
                                                                            break
                                                            if perk_captured:
                                                                if (i - 54) % 5 == 0:
                                                                    to_append = perk_to_append["name"]
                                                                else:
                                                                    perk_EndOfGameStatDescs = "".join(list(map(lambda x: x + "。", perk_to_append["endOfGameStatDescs"])))
                                                                    perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar1@", str(LoLGame_info["participants"][j]["stats"][LoLGame_info_header_keys[i + 1]]))
                                                                    perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar2@", str(LoLGame_info["participants"][j]["stats"][LoLGame_info_header_keys[i + 2]]))
                                                                    perk_EndOfGameStatDescs = perk_EndOfGameStatDescs.replace("@eogvar3@", str(LoLGame_info["participants"][j]["stats"][LoLGame_info_header_keys[i + 3]]))
                                                                    to_append = perk_EndOfGameStatDescs
                                                            else:
                                                                to_append = perkId if (i - 54) % 5 == 0 else ""
                                                            LoLGame_info_data[key].append(to_append)
                                                    else:
                                                        LoLGame_info_data[key].append(LoLGame_info["participants"][j]["stats"][key])
                                                else:
                                                    subkey = LoLGame_info["participants"][j]["stats"][key]
                                                    if subkey == 0:
                                                        LoLGame_info_data[key].append("")
                                                    else:
                                                        try:
                                                            to_append = perkstyles[subkey]["name"]
                                                        except KeyError:
                                                            perkstylePatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                            perkstyle_recapture = 1
                                                            print("第%d/%d场对局（对局序号：%s）符文系信息（%s）获取失败！正在第%d次尝试改用%s版本的符文系信息……\nPerkstyle information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to perkstyles of Patch %s ... Times tried: %d" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, subkey, perkstyle_recapture, perkstylePatch_adopted, subkey, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, perkstylePatch_adopted, perkstyle_recapture))
                                                            while True:
                                                                try:
                                                                    perkstyle = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/perkstyles.json" %(perkstylePatch_adopted, language_cdragon[language_code])).json()
                                                                except requests.exceptions.JSONDecodeError:
                                                                    perkstylePatch_deserted = perkstylePatch_adopted
                                                                    perkstylePatch_adopted = bigPatches[bigPatches.index(perkstylePatch_adopted) + 1]
                                                                    perkstyle_recapture = 1
                                                                    print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to perkstyles of Patch %s ... Times tried: %d" %(perkstylePatch_deserted, perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_deserted, perkstylePatch_adopted, perkstyle_recapture))
                                                                except requests.exceptions.RequestException:
                                                                    if perkstyle_recapture < 3:
                                                                        perkstyle_recapture += 1
                                                                        print("网络环境异常！正在第%d次尝试改用%s版本的符文系信息……\nYour network environment is abnormal! Try changing to runes styles of Patch %s ... Times tried: %d" %(perkstyle_recapture, perkstylePatch_adopted, perkstylePatch_adopted, perkstyle_recapture))
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
                                                                        print("【%d. %s】第%d/%d场对局（对局序号：%s）符文系信息（%s）获取失败！将采用原始数据！\n[%d. %s] Perkstyle information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(i, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, subkey, i, key, subkey, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                        to_append = subkey
                                                                        break
                                                                    else:
                                                                        break
                                                        LoLGame_info_data[key].append(to_append)
                                            elif i >= 89 and i <= 96: #此处处理方法同上——退而求其次（Here the principle is similar to the above: seek for the second best）
                                                subkey = LoLGame_info_header_keys[89 + (i - 89) // 2 * 2]
                                                playerAugmentId = LoLGame_info["participants"][j]["stats"][subkey]
                                                if playerAugmentId == 0:
                                                    LoLGame_info_data[key].append("")
                                                else:
                                                    ArenaAugment_captured = True
                                                    try:
                                                        augment_to_append = ArenaAugments[playerAugmentId]
                                                    except KeyError:
                                                        ArenaPatch_adopted = ".".join(LoLGame_info["gameVersion"].split(".")[:2])
                                                        Arena_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%s）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nArena augment information (%s) of Match %d / %d (matchID: %s) capture failed! Try changing to Arena augments of Patch %s ... Times tried: %d" %(LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, playerAugmentId, Arena_recapture, ArenaPatch_adopted, playerAugmentId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, ArenaPatch_adopted, Arena_recapture))
                                                        while True:
                                                            try:
                                                                Arena = requests.get("https://raw.communitydragon.org/%s/cdragon/arena/%s.json" %(ArenaPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError:
                                                                ArenaPatch_deserted = ArenaPatch_adopted
                                                                ArenaPatch_adopted = bigPatches[bigPatches.index(ArenaPatch_adopted) + 1]
                                                                Arena_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to Arena augments of Patch %s ... Times tried: %d" %(ArenaPatch_deserted, Arena_recapture, ArenaPatch_adopted, ArenaPatch_deserted, ArenaPatch_adopted, Arena_recapture))
                                                            except requests.exceptions.RequestException:
                                                                if Arena_recapture < 3:
                                                                    Arena_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的斗魂竞技场强化符文信息……\nYour network environment is abnormal! Try changing to Arena augments of Patch %s ... Times tried: %d" %(Arena_recapture, ArenaPatch_adopted, ArenaPatch_adopted, Arena_recapture))
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
                                                                    print("【%d. %s】第%d/%d场对局（对局序号：%s）强化符文信息（%s）获取失败！将采用原始数据！\n[%d. %s] Arena augment information (%s) of Match %d / %d (matchID: %s) capture failed! The original data will be used for this match!" %(i, key, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID, playerAugmentId, i, key, playerAugmentId, LoLMatchIDs.index(matchID) + 1, len(LoLMatchIDs), matchID))
                                                                    ArenaAugment_captured = False
                                                                    break
                                                                else:
                                                                    break
                                                    if ArenaAugment_captured:
                                                        to_append = augment_to_append["name"] if (i - 89) % 2 == 0 else augment_rarity[augment_to_append["rarity"]]
                                                    else:
                                                        to_append = playerAugmentId if (i - 89) % 2 == 0 else ""
                                                    LoLGame_info_data[key].append(to_append)
                                            elif i == 107:
                                                LoLGame_info_data[key].append(subteam_color[LoLGame_info["participants"][j]["stats"]["playerSubteamId"]])
                                            elif i == 132:
                                                LoLGame_info_data[key].append(win[LoLGame_info["participants"][j]["stats"]["win"]])
                                            else:
                                                bans_team100 = LoLGame_info["teams"][0]["bans"]
                                                try:
                                                    bans_team200 = LoLGame_info["teams"][1]["bans"]
                                                except IndexError:
                                                    bans = bans_team100 #在拳头代理的英雄联盟中，空对局也会进入历史记录。空对局定义为完成选英雄但是无法正常进入游戏，而后游戏不存在的对局。而训练模式的空对局只有一方，因此LoLGame_info["teams"]中只有一个元素（In LoL propxied by Riot, empty matches are included in the match history. An empty match is defined as the matches which can't be launched after the ChmpSlct period. Since an empty match of Practice Tool has only one team, there's only 1 element in LoLGame_info["teams"]）
                                                else:
                                                    bans = bans_team100 + bans_team200
                                                if bans == []: #修改说明：以前判断禁用数据是否为空是通过禁用模式进行的，如果禁用模式是经典策略就记录禁用信息，否则直接追加空值到列表中。但是在终极魔典中，先前版本记录禁用信息，后来却不记录了。因此，这里判断禁用数据是否为空，直接通过判断bans是否为空【Modification note: To judge whether the ban information of a match is empty, banMode (teams\bans) is used: if banMode is StandardBanStrategy, record the ban information; otherwise, append empty values to the list (by player_count times). But in Ultbook, ban information is recorded in previous versions but not anymore recorded later. Therefore, to judge whether the ban information is empty, whether the variable bans is empty is directly checked】
                                                    LoLGame_info_data[key].append("")
                                                else:
                                                    if bans[j]["championId"] == -1:
                                                        LoLGame_info_data[key].append("")
                                                    else:
                                                        if i == 133:
                                                            try:
                                                                LoLGame_info_data[key].append(LoLChampions[bans[j]["championId"]]["name"])
                                                            except KeyError:
                                                                LoLGame_info_data[key].append("")
                                                        else:
                                                            try:
                                                                LoLGame_info_data[key].append(LoLChampions[bans[j]["championId"]]["alias"])
                                                            except KeyError:
                                                                LoLGame_info_data[key].append(bans[j]["championId"])
                                    LoLGame_info_statistics_display_order = [11, 107, 0, 6, 5, 2, 1, 7, 8, 133, 134, 14, 9, 10, 33, 34, 35, 36, 37, 38, 39, 89, 90, 91, 92, 93, 94, 95, 96, 41, 19, 12, 15, 118, 119, 43, 40, 44, 23, 22, 27, 26, 25, 24, 20, 122, 108, 53, 127, 112, 120, 114, 87, 47, 124, 113, 86, 46, 123, 42, 17, 16, 116, 121, 115, 88, 48, 125, 18, 128, 131, 130, 109, 129, 30, 31, 117, 49, 51, 50, 126, 32, 45, 84, 85, 54, 55, 59, 60, 64, 65, 69, 70, 74, 75, 79, 80, 13, 21, 111, 28, 29, 132, 110]
                                    LoLGame_info_data_organized = {}
                                    for i in LoLGame_info_statistics_display_order:
                                        key = LoLGame_info_header_keys[i]
                                        LoLGame_info_data_organized[key] = [LoLGame_info_header[key]] + LoLGame_info_data[key]
                                    LoLGame_info_df = pandas.DataFrame(data = LoLGame_info_data_organized)
                                    for i in range(LoLGame_info_df.shape[0]): #这里直接使用replace函数会把整数类型的0和1当成逻辑值替换（Here function "replace" will unexpectedly take effects on 0s and 1s of integer type）
                                        for j in range(LoLGame_info_df.shape[1]):
                                            if str(LoLGame_info_df.iat[i, j]) == "True":
                                                LoLGame_info_df.iat[i, j] = "√"
                                            elif str(LoLGame_info_df.iat[i, j]) == "False":
                                                LoLGame_info_df.iat[i, j] = ""
                                    LoLGame_info_df = LoLGame_info_df.stack().unstack(0) #实现对局信息的行列转置（Inverse the match information table）
                                    
                                #尝试修复错误（Try to fix the error）
                                if "errorCode" in LoLGame_timeline:
                                    count = 0
                                    if "500 Internal Server Error" in LoLGame_timeline["message"] or "Missing a closing quotation mark in string" in LoLGame_timeline["message"]:
                                        if error_occurred == False:
                                            print("您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_timeline and ("500 Internal Server Error" in LoLGame_timeline["message"] or "Missing a closing quotation mark in string" in LoLGame_timeline["message"]) and count <= 3:
                                            count += 1
                                            print("正在第%d次尝试获取对局%s时间轴……\nTimes trying to capture Match %s timeline: No. %d ..." %(count, matchID, matchID, count))
                                            LoLGame_timeline = await (await connection.request("GET", "/lol-match-history/v1/game-timelines/" + matchID)).json()
                                    elif "Connection timed out after " in LoLGame_timeline["message"]:
                                        fetched_timeline = False
                                        print("对局时间轴保存超时！请检查网速状况！\nGame timeline saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!")
                                    elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_timeline["message"]:
                                        if error_occurred == False:
                                            print("访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ...")
                                            error_occurred = True
                                        while "errorCode" in LoLGame_timeline and "Service Unavailable - Connection retries limit exceeded. Response timed out" in LoLGame_timeline["message"] and count <= 3:
                                            count += 1
                                            print("正在第%d次尝试获取对局%s时间轴……\nTimes trying to capture Match %s timeline: No. %d ..." %(count, matchID, matchID, count))
                                            LoLGame_timeline = await (await connection.request("GET", "/lol-match-history/v1/game-timelines/" + matchID)).json()
                                    elif "could not convert GAMHS data to match-history format" in LoLGame_timeline["message"]:
                                        fetched_timeline = False
                                        print("斗魂竞技场模式不支持查询时间轴！\nTimeline crawling isn't supported in CHERRY matches!")
                                    if count > 3:
                                        fetched_timeline = False
                                        print("对局%s时间轴获取失败！\nMatch %s timeline capture failure!" %(matchID, matchID))
                                
                                if "errorCode" in LoLGame_timeline:
                                    timeline_exist_error[int(matchID)] = True
                                    print(LoLGame_timeline, end = "\n\n")
                                    for i in error_header:
                                        LoLGame_timeline_error = {"项目": list(error_header.values()), "items": list(error_header.keys()), "值": [LoLGame_timeline[j] for j in error_header_keys]}
                                        LoLGame_timeline_df = pandas.DataFrame(data = LoLGame_timeline_error)
                                elif not "errorCode" in LoLGame_info: #在整理时间轴数据时，需要使用LoLGame_info中的一些数据（While sorting the timeline, some data in LoLGame_info are needed）
                                    timeline_exist_error[int(matchID)] = False
                                    LoLGame_timeline_header = {"events": "事件", "timestamp": "时间戳", "time": "时间", "participantID": "玩家序号", "teamID": "阵营", "summonerName": "召唤师名称", "champion": "选用英雄", "alias": "名称", "currentGold": "当前金币余额", "dominionScore": "占领得分", "jungleMinionsKilled": "击杀野怪数", "level": "英雄等级", "minionsKilled": "击杀小兵数", "position": "当前位置坐标", "teamScore": "队伍得分", "totalGold": "金币获取", "xp": "经验值"}
                                    LoLGame_timeline_data = {}
                                    LoLGame_timeline_header_keys = list(LoLGame_timeline_header.keys())
                                    frames = LoLGame_timeline["frames"]
                                    for i in range(len(LoLGame_timeline_header)): #注意由于对局信息和对局时间轴是绑定在一起的，所以这里会用到构建LoLGame_info_df时的一些变量，包括player_count（Note that since the match information and match timeline are tied together, some variables during the creation of "LoLGame_info_df" will be reused in the following code, including player_count）
                                        key = LoLGame_timeline_header_keys[i]
                                        LoLGame_timeline_data[key] = [] #各项目初始化（Initialize every feature / column）
                                        if i == 0 or i == 1:
                                            for j in range(len(frames)):
                                                LoLGame_timeline_data[key].append(frames[j][key])
                                                for k in range(player_count - 1): #考虑到每个时间戳和事件对应多个不同的玩家，只需要输出一次时间戳和事件，剩余部分为空，以保证表格对齐（Considering each timestamp and each event correspond to multiple participants, they only need to be output once, while the rest assigned by empty strings, so as to align the table）
                                                    LoLGame_timeline_data[key].append("")
                                        elif i == 2:
                                            for j in range(len(frames)):
                                                LoLGame_timeline_data[key].append(lcuTimestamp(frames[j]["timestamp"] // 1000)) #使用lcuTimestamp函数将时间戳转化为时间（Use function lcuTimestamp to convert timestamp into time）
                                                for k in range(player_count - 1):
                                                    LoLGame_timeline_data[key].append("")
                                        elif i == 3:
                                            for j in range(len(frames)):
                                                for k in range(player_count):
                                                    LoLGame_timeline_data[key].append(k + 1)
                                        elif i == 4:
                                            for j in range(len(frames)):
                                                for k in range(player_count):
                                                    LoLGame_timeline_data[key].append(team_color[LoLGame_info["participants"][k]["teamId"]])
                                        elif i == 5:
                                            for j in range(len(frames)):
                                                for k in range(player_count):
                                                    LoLGame_timeline_data[key].append(LoLGame_info["participantIdentities"][k]["player"][key])
                                        elif i == 6:
                                            for j in range(len(frames)):
                                                for k in range(player_count):
                                                    try:
                                                        LoLGame_timeline_data[key].append(LoLChampions[LoLGame_info["participants"][k]["championId"]]["name"])
                                                    except KeyError:
                                                        LoLGame_timeline_data[key].append("")
                                        elif i == 7:
                                            for j in range(len(frames)):
                                                for k in range(player_count):
                                                    try:
                                                        LoLGame_timeline_data[key].append(LoLChampions[LoLGame_info["participants"][k]["championId"]]["alias"])
                                                    except KeyError:
                                                        LoLGame_timeline_data[key].append(LoLGame_info["participants"][k]["championId"])
                                        elif i >= 8 and i <= 12 or i >= 14:
                                            for j in range(len(frames)):
                                                for k in range(player_count):
                                                    try:
                                                        LoLGame_timeline_data[key].append(frames[j]["participantFrames"][str(k + 1)][key])
                                                    except KeyError: #部分自定义对局存在后续事件无内容的情况，即participantFrames为空（Some custom matches don't have anything in later events, namely the "participantFrames" parameter is empty. More details in PBE1-4422435386）
                                                        LoLGame_timeline_data[key].append("")
                                        else:
                                            for j in range(len(frames)):
                                                for k in range(player_count):
                                                    try:
                                                        position = frames[j]["participantFrames"][str(k + 1)][key]
                                                        LoLGame_timeline_data[key].append("(%d, %d)" %(position["x"], position["y"]))
                                                    except KeyError:
                                                        LoLGame_timeline_data[key].append("")
                                    LoLGame_timeline_statistics_display_order = [1, 2, 0, 4, 3, 5, 6, 7, 11, 16, 13, 12, 10, 8, 15, 9, 14]
                                    LoLGame_timeline_data_organized = {}
                                    for i in LoLGame_timeline_statistics_display_order:
                                        key = LoLGame_timeline_header_keys[i]
                                        LoLGame_timeline_data_organized[key] = [LoLGame_timeline_header[key]] + LoLGame_timeline_data[key]
                                    LoLGame_timeline_df = pandas.DataFrame(data = LoLGame_timeline_data_organized)
                                else: #当LoLGame_info正常获取而LoLGame_timeline获取异常时，上述程序将导致无法LoLGame_timeline_df未定义。但是最后导出数据时，是根据确定的对局序号列表来生成工作表名称的，因此一定要向game_timeline_dfs中追加某个数据框，即使该数据框没有任何含义。否则不追加的话，时间轴数据框列表的长度与对局记录中的对局数量不相等，会导致时间轴内容和对局序号乱套。考虑到追加的数据框期望呈现出该对局查询时出现问题，这里选择追加LoLGame_info_df（When LoLGame_info is captured as expected but LoLGame_timeline isn't captured, the program above will cause LoLGame_timeline_df not to be defined. But note that during data export, sheet names are specified based on matchIDs. Therefore, some dataframe must be appended to game_timeline_dfs, even if it doesn't have any meaning. Otherwise, the length of game_timeline_dfs will unequal the length of matchIDs, which results in the discordance between the timeline content and the timeline sheet name. Considering the expectation for the appended dataframe to reflect that the program encountered some problem when searching this match, here LoLGame_info_df is choosen to be appended）
                                    LoLGame_timeline_df = LoLGame_info_df.copy(deep = True)
                                    timeline_exist_error[int(matchID)] = True

                                game_info_dfs[int(matchID)] = LoLGame_info_df.copy(deep = True) #这里添加的LoLGame_info_df会在下一次循环中发生改变，这是数据框类型的特性。因此这里采用深复制，将原有内容克隆到另外一个地址，这样能保证每次添加的是不同的对局信息（The added LoLGame_info_df will be modified next time in the loop, which belongs to the characteristics of DataFrame data type. Therefore a deep copy is used here to clone the original contents to another address, so that each time the appended content is different）
                                game_timeline_dfs[int(matchID)] = LoLGame_timeline_df.copy(deep = True)
                            if LoLGamePlayed:
                                print('对局信息和时间轴已保存在“%s”文件夹下。\nMatch information and timelines are saved in the folder "%s".\n' %(folder, folder))
                            while matches_to_remove != []: #在去除获取异常的对局后，需要在对局序号列表中将这些对局也一并移除（After removing matches that fail to be captured, we need to remove them in matchID list, too）
                                match_to_remove = matches_to_remove.pop()
                                LoLMatchIDs.remove(match_to_remove)
                            break ####搜索完成召唤师最近的对局，需要退出大的while循环（Exit the outer while-loop after work of searching the recent matches is done）
                else:
                    LoLHistory_searched = False
                
                print("是否查询云顶之弈对局记录？（输入任意键查询，否则不查询）\nSearch TFT matches? (Input anything to search or null to export data or switch for another summoner)")
                if input() != "":
                    #print("召唤师云顶之弈对局记录如下：\nMatch history (TFT) is as follows:")
                    TFTHistory_get = True
                    while True:
                        try:
                            TFTHistory = await (await connection.request("GET", "/lol-match-history/v1/products/tft/%s/matches?begin=0&count=500" %(info["puuid"]))).json()
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
                                        TFTHistory = await (await connection.request("GET", "/lol-match-history/v1/products/tft/%s/matches" %(info["puuid"]))).json()
                            txt5name = "Match History (TFT) - " + displayName + ".txt"
                            while True:
                                try:
                                    txtfile5 = open(os.path.join(folder, txt5name), "w", encoding = "utf-8")
                                except FileNotFoundError:
                                    os.makedirs(folder)
                                else:
                                    break
                            try:
                                txtfile5.write(json.dumps(TFTHistory, indent = 8, ensure_ascii = False))
                            except UnicodeEncodeError:
                                print("召唤师云顶之弈对局记录文本文档生成失败！请检查召唤师名称和所选语言是否包含不常用字符！\nSummoner TFT match history text generation failure! Please check if the summoner name and the chosen language include any abnormal characters!\n")
                            txtfile5.close()
                            currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                            pkl5name = "Intermediate Object - TFTHistory - %s (%s).pkl" %(displayName, currentTime)
                            #with open(os.path.join(folder, pkl5name), "wb") as IntObj5:
                                #pickle.dump(TFTHistory, IntObj5)
                            if count > 3:
                                TFTHistory_get = False
                                print("云顶之弈对局记录获取失败！请等待官方修复对局记录服务！\TFT match history capture failure! Please wait for Tencent to fix the match history service!")
                                break
                            print('该玩家共进行%d场云顶之弈对局。近期云顶之弈对局（最近20场）已保存为“%s”。\nThis player has played %d TFT matches. Recent TFT matches (last 20 played) are saved as "%s".\n' %(len(TFTHistory["games"]), os.path.join(folder, txt5name), len(TFTHistory["games"]), os.path.join(folder, txt5name)))
                        except KeyError:
                            if "errorCode" in TFTHistory:
                                print(TFTHistory)
                                TFTHistory_url = "%s/lol-match-history/v1/products/tft/%s/matches?begin=0&count=200" %(connection.address, info["puuid"])
                                print("请打开以下网址，输入如下所示的用户名和密码，打开后在命令行中按回车键继续，或输入任意字符以切换召唤师（Please open the following website, type in the username and password accordingly and press Enter to continue or input anything to switch to another summoner）：\n网址（URL）：\t\t%s\n用户名（Username）：\triot\n密码（Password）：\t%s" %(TFTHistory_url, connection.auth_key))
                                cont = input()
                                if cont == "":
                                    continue
                                else:
                                    TFTHistory_get = False
                                    break
                        else:
                            break
                    if not TFTHistory_get:
                        continue
                    TFTHistory = TFTHistory["games"]
                    TFTHistory_header = {"gameIndex": "游戏序号", "game_datetime": "创建日期", "game_id": "对局序号", "game_length": "持续时长", "game_version": "对局版本", "queue_id": "队列序号", "tft_game_type": "游戏类型", "tft_set_core_name": "数据版本名称", "tft_set_number": "赛季", "participantId": "玩家序号", "augment1": "强化符文1", "augment2": "强化符文2", "augment3": "强化符文3", "companion": "小小英雄", "companion_level": "小小英雄星级", "companion_rarity": "小小英雄稀有度", "gold_left": "剩余金币", "last_round": "存活回合", "level": "等级", "placement": "名次", "players_eliminated": "淘汰玩家数", "puuid": "玩家通用唯一识别码", "summonerName": "召唤师名称", "summonerId": "召唤师序号", "time_eliminated": "存活时长", "total_damage_to_players": "造成玩家伤害", "trait0 name": "羁绊1", "trait0 num_units": "羁绊1单位数", "trait0 style": "羁绊1羁绊框颜色", "trait0 tier_current": "羁绊1当前等级", "trait0 tier_total": "羁绊1最高等级", "trait1 name": "羁绊2", "trait1 num_units": "羁绊2单位数", "trait1 style": "羁绊2羁绊框颜色", "trait1 tier_current": "羁绊2当前等级", "trait1 tier_total": "羁绊2最高等级", "trait2 name": "羁绊3", "trait2 num_units": "羁绊3单位数", "trait2 style": "羁绊3羁绊框颜色", "trait2 tier_current": "羁绊3当前等级", "trait2 tier_total": "羁绊3最高等级", "trait3 name": "羁绊4", "trait3 num_units": "羁绊4单位数", "trait3 style": "羁绊4羁绊框颜色", "trait3 tier_current": "羁绊4当前等级", "trait3 tier_total": "羁绊4最高等级", "trait4 name": "羁绊5", "trait4 num_units": "羁绊5单位数", "trait4 style": "羁绊5羁绊框颜色", "trait4 tier_current": "羁绊5当前等级", "trait4 tier_total": "羁绊5最高等级", "trait5 name": "羁绊6", "trait5 num_units": "羁绊6单位数", "trait5 style": "羁绊6羁绊框颜色", "trait5 tier_current": "羁绊6当前等级", "trait5 tier_total": "羁绊6最高等级", "trait6 name": "羁绊7", "trait6 num_units": "羁绊7单位数", "trait6 style": "羁绊7羁绊框颜色", "trait6 tier_current": "羁绊7当前等级", "trait6 tier_total": "羁绊7最高等级", "trait7 name": "羁绊8", "trait7 num_units": "羁绊8单位数", "trait7 style": "羁绊8羁绊框颜色", "trait7 tier_current": "羁绊8当前等级", "trait7 tier_total": "羁绊8最高等级", "trait8 name": "羁绊9", "trait8 num_units": "羁绊9单位数", "trait8 style": "羁绊9羁绊框颜色", "trait8 tier_current": "羁绊9当前等级", "trait8 tier_total": "羁绊9最高等级", "trait9 name": "羁绊10", "trait9 num_units": "羁绊10单位数", "trait9 style": "羁绊10羁绊框颜色", "trait9 tier_current": "羁绊10当前等级", "trait9 tier_total": "羁绊10最高等级", "trait10 name": "羁绊11", "trait10 num_units": "羁绊11单位数", "trait10 style": "羁绊11羁绊框颜色", "trait10 tier_current": "羁绊11当前等级", "trait10 tier_total": "羁绊11最高等级", "trait11 name": "羁绊12", "trait11 num_units": "羁绊12单位数", "trait11 style": "羁绊12羁绊框颜色", "trait11 tier_current": "羁绊12当前等级", "trait11 tier_total": "羁绊12最高等级", "trait12 name": "羁绊13", "trait12 num_units": "羁绊13单位数", "trait12 style": "羁绊13羁绊框颜色", "trait12 tier_current": "羁绊13当前等级", "trait12 tier_total": "羁绊13最高等级", "unit0 character": "英雄1", "unit0 rarity": "英雄1：稀有度", "unit0 tier": "英雄1：星级", "unit1 character": "英雄2", "unit1 rarity": "英雄2：稀有度", "unit1 tier": "英雄2：星级", "unit2 character": "英雄3", "unit2 rarity": "英雄3：稀有度", "unit2 tier": "英雄3：星级", "unit3 character": "英雄4", "unit3 rarity": "英雄4：稀有度", "unit3 tier": "英雄4：星级", "unit4 character": "英雄5", "unit4 rarity": "英雄5：稀有度", "unit4 tier": "英雄5：星级", "unit5 character": "英雄6", "unit5 rarity": "英雄6：稀有度", "unit5 tier": "英雄6：星级", "unit6 character": "英雄7", "unit6 rarity": "英雄7：稀有度", "unit6 tier": "英雄7：星级", "unit7 character": "英雄8", "unit7 rarity": "英雄8：稀有度", "unit7 tier": "英雄8：星级", "unit8 character": "英雄9", "unit8 rarity": "英雄9：稀有度", "unit8 tier": "英雄9：星级", "unit9 character": "英雄10", "unit9 rarity": "英雄10：稀有度", "unit9 tier": "英雄10：星级", "unit10 character": "英雄11", "unit10 rarity": "英雄11：稀有度", "unit11 tier": "英雄11：星级", "unit0 item0": "英雄1：装备1", "unit0 item1": "英雄1：装备2", "unit0 item2": "英雄1：装备3", "unit1 item0": "英雄2：装备1", "unit1 item1": "英雄2：装备2", "unit1 item2": "英雄2：装备3", "unit2 item0": "英雄3：装备1", "unit2 item1": "英雄3：装备2", "unit2 item2": "英雄3：装备3", "unit3 item0": "英雄4：装备1", "unit3 item1": "英雄4：装备2", "unit3 item2": "英雄4：装备3", "unit4 item0": "英雄5：装备1", "unit4 item1": "英雄5：装备2", "unit4 item2": "英雄5：装备3", "unit5 item0": "英雄6：装备1", "unit5 item1": "英雄6：装备2", "unit5 item2": "英雄6：装备3", "unit6 item0": "英雄7：装备1", "unit6 item1": "英雄7：装备2", "unit6 item2": "英雄7：装备3", "unit7 item0": "英雄8：装备1", "unit7 item1": "英雄8：装备2", "unit7 item2": "英雄8：装备3", "unit8 item0": "英雄9：装备1", "unit8 item1": "英雄9：装备2", "unit8 item2": "英雄9：装备3", "unit9 item0": "英雄10：装备1", "unit9 item1": "英雄10：装备2", "unit9 item2": "英雄10：装备3", "unit10 item0": "英雄11：装备1", "unit10 item1": "英雄11：装备2", "unit10 item2": "英雄11：装备3"}
                    TFTHistory_data = {}
                    TFTHistory_header_keys = list(TFTHistory_header.keys())
                    #traitStyles = {"kThreat": "威慑", "kBronze": "青铜", "kSilver": "白银", "kGold": "黄金", "kChromatic": "炫金"}
                    traitStyles = {0: "", 1: "青铜", 2: "白银", 3: "黄金", 4: "炫金"}
                    rarity = {"Default": "经典", "NoRarity": "其它", "Epic": "史诗", "Legendary": "传说", "Mythic": "神话", "Rare": "稀有", "Ultimate": "终极"}
                    TFTGamePlayed = len(TFTHistory) != 0 #标记该玩家是否进行过云顶之弈对局（Mark whether this summoner has played any TFT game）
                    TFT_main_player_indices = [] #云顶之弈对局记录中记录了所有玩家的数据，但是在历史记录的工作表中只要显示主召唤师的数据，因此必须知道每场对局中主召唤师的索引（Each match in TFT history records all players' data, but only the main player's data are needed to display in the match history worksheet, so the index of the main player in each match is necessary）
                    version_re = re.compile("\d*\.\d*\.\d*\.\d*") #云顶之弈的对局版本信息是一串字符串，从中识别四位对局版本（TFT match version is a long string, from which the 4-number version is identified）
                    TFTGamePatches = [] #这里设定小版本号，以便后续切换云顶之弈相关数据的版本（Here a shorter patch is extracted, in case TFT data version needs changing）
                    for game in TFTHistory:
                        try:
                            for i in range(len(game["json"]["participants"])):
                                if game["json"]["participants"][i]["puuid"] == current_puuid:
                                    TFT_main_player_indices.append(i)
                                    break
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
                        txt8name = "Match Information (TFT) - " + currentPlatformId + "-" + str(matchID) + ".txt"
                        while True:
                            try:
                                txtfile8 = open(os.path.join(folder, txt8name), "w", encoding = "utf-8")
                            except FileNotFoundError:
                                os.makedirs(folder)
                            else:
                                break
                        try:
                            txtfile8.write(json.dumps(TFTHistory[i], indent = 8, ensure_ascii = False))
                        except UnicodeDecodeError:
                            print("对局%s信息文本文档生成失败！请检查召唤师名称是否包含不常用字符！\nMatch %s information text generation failure! Please check if the summoner name includes any abnormal characters!" %(matchID, matchID))
                            save = False
                        txtfile8.close()
                        currentTime = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                        pkl8name = "Intermediate Object - Match Information (LoL) - %s-%d.pkl" %(currentPlatformId, matchID)
                        #with open(os.path.join(folder, pkl8name), "wb") as IntObj8:
                            #pickle.dump(TFTGame_info, IntObj8)
                        if save:
                            print('保存进度（Saving process）：%d/%d\t对局序号（MatchID）： %d' %(i + 1, len(TFTHistory), matchID))
                        
                        info_exist_error[matchID] = False #一旦正常获取到云顶之弈的对局记录，对局信息即视为正常获取（Once the TFT match history is captured successfully, the TFT games' information is then regarded to be captured successfully as well）
                        timeline_exist_error[matchID] = True #云顶之弈对局中没有时间轴信息，因此每个云顶之弈对局的时间轴标记为异常获取（There's no timeline information in each TFT match, so each TFT match's timeline is labeled as "error" captured）
                        main_player_included[matchID] = True #从云顶之弈获取的对局记录中抽取对局信息，则这些对局一定包含当前玩家（Since TFT game information is extracted from TFT match history, these matches must include the current player）
                        match_reserve_strategy[matchID] = True
                        TFTGame_info_data = {} #云顶之弈没有独立的API以供查询对局信息。这里将每场对局的与玩家有关的数据视为对局信息（No API is available for TFT match information query. Here any information relevant to participants is regarded as TFT game information）
                        for j in range(9, len(TFTHistory_header)): #各项目初始化（Initialize every feature / column）
                            key = TFTHistory_header_keys[j]
                            TFTGame_info_data[key] = []
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
                                else:
                                    TFTHistory_data[key].append("")
                                    if j >= 9:
                                        TFTGame_info_data[key].append("")
                        else:
                            for j in range(len(TFTHistory_header)):
                                key = TFTHistory_header_keys[j]
                                if j == 0:
                                    TFTHistory_data[key].append(i + 1)
                                elif j >= 1 and j <= 8:
                                    TFTHistoryJson = TFTHistory[i]["json"]
                                    if j == 1:
                                        game_datetime = int(TFTHistoryJson["game_datetime"])
                                        game_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(game_datetime // 1000))
                                        game_date_fraction = game_datetime / 1000 - game_datetime // 1000
                                        to_append = game_date + ("{0:.3}".format(game_date_fraction))[1:5]
                                        TFTHistory_data[key].append(to_append)
                                    elif j in {2, 5, 7}:
                                        try:
                                            TFTHistory_data[key].append(TFTHistoryJson[key])
                                        except KeyError: #在云顶之弈第7赛季之前，TFTHistoryJson中无tft_set_core_name这一键（Before TFTSet7, tft_set_core_name isn't present as a key of `TFTHistoryJson`）
                                            TFTHistory_data[key].append("")
                                    elif j == 3:
                                        TFTHistory_data[key].append("%d:%02d" %(int(TFTHistoryJson["game_length"]) // 60, int(TFTHistoryJson["game_length"]) % 60))
                                    elif j == 4:
                                        TFTGameVersion = version_re.search(TFTHistoryJson["game_version"]).group()
                                        TFTHistory_data[key].append(TFTGameVersion)
                                        TFTGamePatch = ".".join(TFTGameVersion.split(".")[:2]) #由于需要通过这部分代码事先获取所有对局的版本，因此无论如何，这部分代码都要放在与从CommunityDragon重新获取云顶之弈数据相关的代码前面（Since game patches are captured here, by all means should this part of code be in front of the code relevant to regetting TFT data from CommunityDragon）
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
                                    for k in range(len(TFTHistory[i]["json"]["participants"])):
                                        TFTPlayer = TFTHistory[i]["json"]["participants"][k]
                                        if j == 9:
                                            TFTGame_info_data[key].append(k + 1)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(k + 1)
                                        elif j >= 10 and j <= 12: #以下的try-except语句的思想适用于整个数据整理阶段（The principle of the following try-except statements applies to the whole data sorting period）
                                            if not "augments" in TFTPlayer:
                                                TFTGame_info_data[key].append("") #云顶之弈刚出的时候，没有强化符文的概念（The concept of "augment" didn't appear at the beginning of TFT）
                                                if TFTPlayer["puuid"] == current_puuid: #此处条件判断可优化为k == TFT_main_player_indices[i]（Here the judgment can be optimized into `k == TFT_main_player_indices`）
                                                    TFTHistory_data[key].append("")
                                                continue
                                            try: #如果下面的语句没有报错，那么最新版本的数据将保存到工作表中（If the following statement doesn't generate an exception, then the latest data will be saved into the worksheet）
                                                to_append = TFTAugments[TFTPlayer["augments"][j - 10]]["name"]
                                            except KeyError:
                                                TFTAugmentPatch_adopted = TFTGamePatches[i]
                                                TFTAugment_recapture = 1
                                                print("第%d/%d场对局（对局序号：%d）强化符文信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nTFT augment information (%s) of Match %d / %d (matchID: %d) capture failed! Try changing to TFT augments of Patch %s ... Times tried: %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer["augments"][j - 10], TFTAugment_recapture, TFTAugmentPatch_adopted, TFTPlayer["augments"][j - 10], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTAugmentPatch_adopted, TFTAugment_recapture))
                                                while True:
                                                    try:
                                                        TFT = requests.get("https://raw.communitydragon.org/%s/cdragon/tft/%s.json" %(TFTAugmentPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError: #存在版本合并更新的情况（Situation like merged update exists）
                                                        TFTAugmentPatch_deserted = TFTAugmentPatch_adopted
                                                        TFTAugmentPatch_adopted = bigPatches[bigPatches.index(TFTAugmentPatch_adopted) + 1]
                                                        TFTAugment_recapture = 1
                                                        print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT augments of Patch %s ... Times tried: %d" %(TFTAugmentPatch_deserted, TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_deserted, TFTAugmentPatch_adopted, TFTAugment_recapture))
                                                    except requests.exceptions.RequestException: #如果重新获取数据的过程中出现网络异常，那么暂时先将原始数据导入工作表中（If a network error occurs when recapturing the data, then temporarily export the initial data into the worksheet）
                                                        if TFTAugment_recapture < 3:
                                                            TFTAugment_recapture += 1
                                                            print("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈强化符文信息……\nYour network environment is abnormal! Try changing to TFT augments of Patch %s ... Times tried: %d" %(TFTAugment_recapture, TFTAugmentPatch_adopted, TFTAugmentPatch_adopted, TFTAugment_recapture))
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
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                        elif j >= 13 and j <= 15:
                                            contentId = TFTPlayer["companion"]["content_ID"]
                                            try:
                                                TFTCompanion_iter = TFTCompanions[contentId]
                                            except KeyError:
                                                TFTCompanionPatch_adopted = TFTGamePatches[i]
                                                TFTCompanion_recapture = 1
                                                print("第%d/%d场对局（对局序号：%d）小小英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的小小英雄信息……\nTFT companion information (%s) of Match %d / %d (matchID: %d) capture failed! Try changing to TFT companions of Patch %s ... Times tried: %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], contentId, TFTCompanion_recapture, TFTCompanionPatch_adopted, contentId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                                while True:
                                                    try:
                                                        TFTCompanion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/companions.json" %(TFTCompanionPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        TFTCompanionPatch_deserted = TFTCompanionPatch_adopted
                                                        TFTCompanionPatch_adopted = bigPatches[bigPatches.index(TFTCompanionPatch_adopted) + 1]
                                                        TFTCompanion_recapture = 1
                                                        print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT traits of Patch %s ... Times tried: %d" %(TFTCompanionPatch_deserted, TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_deserted, TFTCompanionPatch_adopted, TFTCompanion_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if TFTCompanion_recapture < 3:
                                                            TFTCompanion_recapture += 1
                                                            print("网络环境异常！正在第%d次尝试改用%s版本的小小英雄信息……\nYour network environment is abnormal! Try changing to TFT companions of Patch %s ... Times tried: %d" %(TFTCompanion_recapture, TFTCompanionPatch_adopted, TFTCompanionPatch_adopted, TFTCompanion_recapture))
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
                                            TFTGame_info_data[key].append(to_append[j])
                                            if TFTPlayer["puuid"] == current_puuid:
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
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                        elif j == 22 or j == 23:
                                            TFTPlayer_info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + TFTPlayer["puuid"])).json()
                                            if TFTPlayer["puuid"] == "00000000-0000-0000-0000-000000000000": #在云顶之弈（新手教程）中，无法通过电脑玩家的玩家通用唯一识别码（00000000-0000-0000-0000-000000000000）来查询其召唤师名称和序号（Summoner names and IDs of bot players in TFT (Tutorial) can't be searched for according to their puuid: 00000000-0000-0000-0000-000000000000）
                                                to_append = {22: "", 23: ""}
                                            else:
                                                to_append = {22: TFTPlayer_info["displayName"], 23: TFTPlayer_info["summonerId"]}
                                            TFTGame_info_data[key].append(to_append[j])
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append[j])
                                        elif j == 24:
                                            to_append = "%d:%02d" %(int(TFTPlayer["time_eliminated"]) // 60, int(TFTPlayer["time_eliminated"]) % 60)
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                        else:
                                            to_append = TFTPlayer[key]
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTPlayer["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                elif j >= 26 and j <= 90:
                                    #TFTMainPlayer_Traits = TFTHistory[i]["json"]["participants"][TFT_main_player_indices[i]]["traits"]
                                    TFTTrait_iter, subkey = key.split(" ")
                                    for k in range(len(TFTHistory[i]["json"]["participants"])):
                                        TFTPlayer_Traits = TFTHistory[i]["json"]["participants"][k]["traits"]
                                        if int(TFTTrait_iter[5:]) < len(TFTPlayer_Traits): #在这个小于的问题上纠结了很久[敲打]——下标是从0开始的。假设API上记录了n个羁绊，那么当程序正在获取第n个羁绊时，就会引起下标越界的问题。所以这里不能使用小于等于号（I stuck at this less than sign for long xD - note that the index begins from 0. Suppose there're totally n traits recorded in LCU API. Then, when the program is trying to capture the n-th trait, it'll throw an IndexError. That's why the less than or equal to sign can't be used here）
                                            try:
                                                if (j - 26) % 5 == 0:
                                                    to_append = TFTTraits[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"]]["display_name"]
                                                elif (j - 26) % 5 == 2:
                                                    #to_append = traitStyles[TFTTraits[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"]]["conditional_trait_sets"][TFTPlayer_Traits[int(TFTTrait_iter[5:])]["style"]]["style_name"]] #至于为什么前面traitStyles变量不直接用数字作为键，那是因为一旦用数字作为键，我的习惯是比较想知道是不是还有其它数字对应了某一种类型，就是说看上去不是特别舒服（As for why I don't take numbers as the keys of the dictionary variable `traitStyles`, if I do that, then I tend to wonder if there's some other number correspondent to some other type, that is, the program seems not so perfect and long-living）
                                                    to_append = traitStyles[TFTPlayer_Traits[int(TFTTrait_iter[5:])]["style"]] #LCU API中记录的style和CommunityDragon数据库中记录的style_idx不是一个东西（`style` in LCU API and `style_idx` in CommunityDragon database aren't the same thing）
                                                else:
                                                    to_append = TFTPlayer_Traits[int(TFTTrait_iter[5:])][subkey]
                                            except KeyError:
                                                TFTTraitPatch_adopted = TFTGamePatches[i]
                                                TFTTrait_recapture = 1
                                                print("第%d/%d场对局（对局序号：%d）羁绊信息（%s）获取失败！正在第%d次尝试改用%s版本的羁绊信息……\nTFT trait information (%s) of Match %d / %d (matchID: %d) capture failed! Try changing to TFT traits of Patch %s ... Times tried: %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], TFTTrait_recapture, TFTTraitPatch_adopted, TFTPlayer_Traits[int(TFTTrait_iter[5:])]["name"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTTraitPatch_adopted, TFTTrait_recapture))
                                                while True:
                                                    try:
                                                        TFTTrait = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tfttraits.json" %(TFTTraitPatch_adopted, language_cdragon[language_code])).json()
                                                    except requests.exceptions.JSONDecodeError:
                                                        TFTTraitPatch_deserted = TFTTraitPatch_adopted
                                                        TFTTraitPatch_adopted = bigPatches[bigPatches.index(TFTTraitPatch_adopted) + 1]
                                                        TFTTrait_recapture = 1
                                                        print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT traits of Patch %s ... Times tried: %d" %(TFTTraitPatch_deserted, TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_deserted, TFTTraitPatch_adopted, TFTTrait_recapture))
                                                    except requests.exceptions.RequestException:
                                                        if TFTTrait_recapture < 3:
                                                            TFTTrait_recapture += 1
                                                            print("网络环境异常！正在第%d次尝试改用%s版本的羁绊信息……\nYour network environment is abnormal! Try changing to TFT traits of Patch %s ... Times tried: %d" %(TFTTrait_recapture, TFTTraitPatch_adopted, TFTTraitPatch_adopted, TFTTrait_recapture))
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
                                            TFTGame_info_data[key].append(to_append)
                                            if TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                                TFTHistory_data[key].append(to_append)
                                        else:
                                            TFTGame_info_data[key].append("")
                                            if TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                                TFTHistory_data[key].append("")
                                else:
                                    #TFTMainPlayer_Units = TFTHistory[i]["json"]["participants"][TFT_main_player_indices[i]]["units"]
                                    unit_iter, subkey = key.split(" ")
                                    for k in range(len(TFTHistory[i]["json"]["participants"])):
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
                                                            TFTChampionPatch_adopted = TFTGamePatches[i]
                                                            TFTChampion_recapture = 1
                                                            print("第%d/%d场对局（对局序号：%d）英雄信息（%s）获取失败！正在第%d次尝试改用%s版本的棋子信息……\nTFT champion (%s) information of Match %d / %d (matchID: %d) capture failed! Try changing to TFT champions of Patch %s ... Times tried: %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTPlayer_Units[int(unit_iter[4:])]["character_id"], TFTChampion_recapture, TFTChampionPatch_adopted, TFTPlayer_Units[int(unit_iter[4:])]["character_id"], i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTChampionPatch_adopted, TFTChampion_recapture))
                                                            while True:
                                                                try:
                                                                    TFTChampion = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftchampions.json" %(TFTChampionPatch_adopted, language_cdragon[language_code])).json()
                                                                except requests.exceptions.JSONDecodeError:
                                                                    TFTChampionPatch_deserted = TFTChampionPatch_adopted
                                                                    TFTChampionPatch_adopted = bigPatches[bigPatches.index(TFTChampionPatch_adopted) + 1]
                                                                    TFTChampion_recapture = 1
                                                                    print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT champions of Patch %s ... Times tried: %d" %(TFTChampionPatch_deserted, TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_deserted, TFTChampionPatch_adopted, TFTChampion_recapture))
                                                                except requests.exceptions.RequestException:
                                                                    if TFTChampion_recapture < 3:
                                                                        TFTChampion_recapture += 1
                                                                        print("网络环境异常！正在第%d次尝试改用%s版本的棋子信息……\nYour network environment is abnormal! Try changing to TFT champions of Patch %s ... Times tried: %d" %(TFTChampion_recapture, TFTChampionPatch_adopted, TFTChampionPatch_adopted, TFTChampion_recapture))
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
                                                    TFTGame_info_data[key].append(to_append)
                                                    if TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                                        TFTHistory_data[key].append(to_append)
                                                else:
                                                    to_append = TFTPlayer_Units[int(unit_iter[4:])][subkey]
                                                    TFTGame_info_data[key].append(to_append)
                                                    if TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                                        TFTHistory_data[key].append(to_append)
                                            else:
                                                TFTGame_info_data[key].append("")
                                                if TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                                    TFTHistory_data[key].append("")
                                        else:
                                            if int(unit_iter[4:]) < len(TFTPlayer_Units): #很少有英雄单位可以有3个装备（Merely do champion units have full items）
                                                if "itemNames" in TFTPlayer_Units[(int(unit_iter[4:]))] and (j - 1) % 3 < len(TFTPlayer_Units[(int(unit_iter[4:]))]["itemNames"]):
                                                    TFTItemNameId = TFTPlayer_Units[(int(unit_iter[4:]))]["itemNames"][(j - 1) % 3]
                                                    try:
                                                        to_append = TFTItems[TFTItemNameId]["name"]
                                                    except KeyError:
                                                        TFTItemPatch_adopted = TFTGamePatches[i]
                                                        TFTItem_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%d）装备信息（%s）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%s) of Match %d / %d (matchID: %d) capture failed! Try changing to TFT items of Patch %s ... Times tried: %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemNameId, TFTItem_recapture, TFTItemPatch_adopted, TFTItemNameId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemPatch_adopted, TFTItem_recapture))
                                                        while True:
                                                            try:
                                                                TFTItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError:
                                                                TFTItemPatch_deserted = TFTItemPatch_adopted
                                                                TFTItemPatch_adopted = bigPatches[bigPatches.index(TFTItemPatch_adopted) + 1]
                                                                TFTItemPatch_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT items of Patch %s ... Times tried: %d" %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture))
                                                            except requests.exceptions.RequestException:
                                                                if TFTItem_recapture < 3:
                                                                    TFTItem_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Try changing to TFT items of Patch %s ... Times tried: %d" %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture))
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
                                                        TFTItemPatch_adopted = TFTGamePatches[i]
                                                        TFTItem_recapture = 1
                                                        print("第%d/%d场对局（对局序号：%d）装备信息（%d）获取失败！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nTFT item information (%d) of Match %d / %d (matchID: %d) capture failed! Try changing to TFT items of Patch %s ... Times tried: %d" %(i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemId, TFTItem_recapture, TFTItemPatch_adopted, TFTItemId, i + 1, len(TFTHistory), TFTHistory[i]["json"]["game_id"], TFTItemPatch_adopted, TFTItem_recapture))
                                                        while True:
                                                            try:
                                                                TFTItem = requests.get("https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/tftitems.json" %(TFTItemPatch_adopted, language_cdragon[language_code])).json()
                                                            except requests.exceptions.JSONDecodeError:
                                                                TFTItemPatch_deserted = TFTItemPatch_adopted
                                                                TFTItemPatch_adopted = bigPatches[bigPatches.index(TFTItemPatch_adopted) + 1]
                                                                TFTItemPatch_recapture = 1
                                                                print("%s版本文件不存在！正在第%s次尝试回退至%s版本……\n%s patch file doesn't exist! Try changing to TFT items of Patch %s ... Times tried: %d" %(TFTItemPatch_deserted, TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_deserted, TFTItemPatch_adopted, TFTItem_recapture))
                                                            except requests.exceptions.RequestException:
                                                                if TFTItem_recapture < 3:
                                                                    TFTItem_recapture += 1
                                                                    print("网络环境异常！正在第%d次尝试改用%s版本的云顶之弈装备信息……\nYour network environment is abnormal! Try changing to TFT items of Patch %s ... Times tried: %d" %(TFTItem_recapture, TFTItemPatch_adopted, TFTItemPatch_adopted, TFTItem_recapture))
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
                                                TFTGame_info_data[key].append(to_append)
                                                if TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                                    TFTHistory_data[key].append(to_append)
                                            else:
                                                TFTGame_info_data[key].append("")
                                                if TFTHistory[i]["json"]["participants"][k]["puuid"] == current_puuid:
                                                    TFTHistory_data[key].append("")
                        TFTGame_info_statistics_display_order = [0, 13, 14, 4, 5, 6, 9, 8, 15, 7, 16, 11, 10, 1, 2, 3, 82, 83, 84, 115, 116, 117, 85, 86, 87, 118, 119, 120, 88, 89, 90, 121, 122, 123, 91, 92, 93, 124, 125, 126, 94, 95, 96, 127, 128, 129, 97, 98, 99, 130, 131, 132, 100, 101, 102, 133, 134, 135, 103, 104, 105, 136, 137, 138, 106, 107, 108, 139, 140, 141, 109, 110, 111, 142, 143, 144, 112, 113, 114, 145, 146, 147, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81]
                        TFTGame_info_data_organized = {}
                        for j in TFTGame_info_statistics_display_order:
                            key = TFTHistory_header_keys[j + 9]
                            TFTGame_info_data_organized[key] = [TFTHistory_header[key]] + TFTGame_info_data[key]
                        TFTGame_info_df = pandas.DataFrame(data = TFTGame_info_data_organized)
                        TFTGame_info_df = TFTGame_info_df.stack().unstack(0)
                        game_info_dfs[matchID] = TFTGame_info_df.copy(deep = True)
                        
                    TFTHistory_statistics_display_order = [0, 2, 1, 3, 5, 6, 4, 8, 13, 14, 15, 18, 17, 24, 16, 25, 20, 19, 10, 11, 12, 91, 92, 93, 124, 125, 126, 94, 95, 96, 127, 128, 129, 97, 98, 99, 130, 131, 132, 100, 101, 102, 133, 134, 135, 103, 104, 105, 136, 137, 138, 106, 107, 108, 139, 140, 141, 109, 110, 111, 142, 143, 144, 112, 113, 114, 145, 146, 147, 115, 116, 117, 148, 149, 150, 118, 119, 120, 151, 152, 153, 121, 122, 123, 154, 155, 156, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90]
                    TFTHistory_data_organized = {}
                    for i in TFTHistory_statistics_display_order:
                        key = TFTHistory_header_keys[i]
                        TFTHistory_data_organized[key] = [TFTHistory_header[key]] + TFTHistory_data[key]
                    TFTHistory_df = pandas.DataFrame(data = TFTHistory_data_organized)
                    if TFTGamePlayed:
                        print(TFTHistory_df[:min(21, len(TFTHistory_df) + 1)])
                    else:
                        print("这位召唤师从5月1日起就没有进行过任何云顶之弈对局。\nThis summoner hasn't played any TFT game yet since May 1st.")
                else:
                    TFTHistory_searched = False
                
                matchIDs = list(game_info_dfs.keys())
                matchIDs.sort()
                
                recent_players_df = pandas.DataFrame() #起到占位作用，保证在使用自定义脚本11时生成的近期一起玩过的玩家数据一定是工作簿的第4和5张工作表（Act as a placeholder to ensure the recent played summoner data from Customized Program 11 are in the fourth and fifth sheets in the workbook)
                if not LoLHistory_searched:
                    LoLHistory_df = pandas.DataFrame() #起到占位作用，保证在使用本脚本时生成的英雄联盟对局记录一定是工作簿的第6或7张工作表（Act as a placeholder to ensure the LoL match history data from this program when running [One-Key Query] are in the sixth or seventh sheet in the workbook)
                if not TFTHistory_searched:
                    TFTHistory_df = pandas.DataFrame() #起到占位作用，保证在使用本脚本时生成的英雄联盟对局记录一定是工作簿的第8张工作表（Act as a placeholder to ensure the LoL match history data from this program when running [One-Key Query] are in the eighth sheet in the workbook)

                print("是否导出以上召唤师数据至Excel中？（输入任意键导出，否则不导出）\nDo you want to export the above data into Excel? (Press any key to export or null to refuse exporting)")
                export = input()
                if export != "":
                    excel_name = "Summoner Profile - " + displayName + ".xlsx"
                    while True:
                        try:
                            with pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") as writer:
                                info_df.to_excel(excel_writer = writer, sheet_name = "Profile")
                                print("召唤师生涯导出完成！\nSummoner profile exported!\n")
                                ranked_df.to_excel(excel_writer = writer, sheet_name = "Rank")
                                print("召唤师排位数据导出完成！\nSummoner ranked data exported!\n")
                                mastery_df.to_excel(excel_writer = writer, sheet_name = "Champion Mastery")
                                print("召唤师英雄成就导出完成！\nSummoner champion mastery exported!\n")
                                if LoLHistory_searched:
                                    if scan:
                                        LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                    else:
                                        LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                    print("召唤师英雄联盟对局记录导出完成！\nSummoner LoL match history exported!\n")
                                if TFTHistory_searched:
                                    TFTHistory_df.to_excel(excel_writer = writer, sheet_name = "TFT Match History")
                                    print("召唤师云顶之弈对局记录导出完成！\nSummoner TFT match history exported!\n")
                                #print(len(info_exist_error), len(timeline_exist_error), len(main_player_included), len(match_reserve_strategy))
                                for i in range(len(matchIDs)):
                                    if match_reserve_strategy[matchIDs[i]]:
                                        if not info_exist_error[matchIDs[i]]:
                                            game_info_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Information")
                                        if not timeline_exist_error[matchIDs[i]]:
                                            game_timeline_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Timeline")
                                    if not main_player_included[matchIDs[i]]:
                                        if not match_reserve_strategy[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner and not exported!)" %(i + 1, len(matchIDs)))
                                        else:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner but yet exported!)" %(i + 1, len(matchIDs)))
                                    else:
                                        if info_exist_error[matchIDs[i]] and not timeline_exist_error[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information capture failure!)" %(i + 1, len(matchIDs)))
                                        elif not info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match timeline capture failure!)" %(i + 1, len(matchIDs)))
                                        elif info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information & timeline capture Failure!)" %(i + 1, len(matchIDs)))
                                        else:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d" %(i + 1, len(matchIDs)))
                                print("对局信息和时间轴导出完成!\nMatch information and timeline exported!\n")
                        except PermissionError:
                            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
                            input()
                        except FileNotFoundError:
                            try:
                                os.makedirs(folder)
                            except FileExistsError:
                                pass
                            with pandas.ExcelWriter(path = os.path.join(folder, excel_name)) as writer:
                                info_df.to_excel(excel_writer = writer, sheet_name = "Profile")
                                print("召唤师生涯导出完成！\nSummoner profile exported!\n")
                                ranked_df.to_excel(excel_writer = writer, sheet_name = "Rank")
                                print("召唤师排位数据导出完成！\nSummoner ranked data exported!\n")
                                mastery_df.to_excel(excel_writer = writer, sheet_name = "Champion Mastery")
                                print("召唤师英雄成就导出完成！\nSummoner champion mastery exported!\n")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (LoL)")
                                pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "Recently Played Summoners (TFT)")
                                print("已创建近期一起玩过的玩家的空白数据表！\nCreated an empty sheet for recently played summoners!\n")
                                if LoLHistory_searched:
                                    if scan:
                                        pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                        LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                    else:
                                        LoLHistory_df.to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                        pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                    print("召唤师英雄联盟对局记录导出完成！\nSummoner LoL match history exported!\n")
                                else:
                                    pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History")
                                    pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "LoL Match History - Scan")
                                    print("已创建英雄联盟对局记录的空白数据表！\nCreated an empty sheet for LoL match history!\n")
                                if TFTHistory_searched:
                                    TFTHistory_df.to_excel(excel_writer = writer, sheet_name = "TFT Match History")
                                    print("召唤师云顶之弈对局记录导出完成！\nSummoner TFT match history exported!\n")
                                else:
                                    pandas.DataFrame().to_excel(excel_writer = writer, sheet_name = "TFT Match History")
                                    print("已创建云顶之弈对局记录的空白工作表！\nCreated an empty sheet for TFT match history!\n")
                                for i in range(len(matchIDs)):
                                    if match_reserve_strategy[matchIDs[i]]:
                                        if not info_exist_error[matchIDs[i]]:
                                            game_info_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Information")
                                        if not timeline_exist_error[matchIDs[i]]:
                                            game_timeline_dfs[matchIDs[i]].to_excel(excel_writer = writer, sheet_name = "Match " + str(matchIDs[i]) + " - Timeline")
                                    if not main_player_included[matchIDs[i]]:
                                        if not match_reserve_strategy[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner and not exported!)" %(i + 1, len(matchIDs)))
                                        else:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Excluding this summoner but yet exported!)" %(i + 1, len(matchIDs)))
                                    else:
                                        if info_exist_error[matchIDs[i]] and not timeline_exist_error[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information capture failure!)" %(i + 1, len(matchIDs)))
                                        elif not info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match timeline capture failure!)" %(i + 1, len(matchIDs)))
                                        elif info_exist_error[matchIDs[i]] and timeline_exist_error[matchIDs[i]]:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d (Match information & timeline capture Failure!)" %(i + 1, len(matchIDs)))
                                        else:
                                            print("对局信息和时间轴导出进度（Match information and timeline export process）：%d/%d" %(i + 1, len(matchIDs)))
                            break
                        else:
                            break
                    print("对局信息和时间轴导出完成!\nMatch information and timeline exported!\n")

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await search_profile(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
