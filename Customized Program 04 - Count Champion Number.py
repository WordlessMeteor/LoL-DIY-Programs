from lcu_driver import Connector
import time, requests, json, re

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

print('请选择英雄数据来源（输入“0”以退出程序）：\nPlease select the champion data source (submit "0" to exit):\n1\tLCU API\n2\tDataDragon\n3\tCommunityDragon')
source = input()
if source != "" and (source[0] == "0" or source[0] == "2" or source[0] == "3"):
    if source[0] == "0":
        exit()
    print("请选择输出语言【默认为中文（中国）】：\nPlease select a language for output (the default option is zh_CN):\nNo.\tCODE\tLANGUAGE\t语言\tApplicable CDragon Data Patches")
    language = {1: {"CODE": "cs_CZ", "LANGUAGE (EN)": "Czech (Czech Republic)", "LANGUAGE (ZH)": "捷克语（捷克共和国）", "Applicable CDragon Data Patches": "7.1+"}, 2: {"CODE": "el_GR", "LANGUAGE (EN)": "Greek (Greece)", "LANGUAGE (ZH)": "希腊语（希腊）", "Applicable CDragon Data Patches": "9.1+"}, 3: {"CODE": "pl_PL", "LANGUAGE (EN)": "Polish (Poland)", "LANGUAGE (ZH)": "波兰语（波兰）", "Applicable CDragon Data Patches": "9.1+"}, 4: {"CODE": "ro_RO", "LANGUAGE (EN)": "Romanian (Romania)", "LANGUAGE (ZH)": "罗马尼亚语（罗马尼亚）", "Applicable CDragon Data Patches": "9.1+"}, 5: {"CODE": "hu_HU", "LANGUAGE (EN)": "Hungarian (Hungary)", "LANGUAGE (ZH)": "匈牙利语（匈牙利）", "Applicable CDragon Data Patches": "9.1+"}, 6: {"CODE": "en_GB", "LANGUAGE (EN)": "English (United Kingdom)", "LANGUAGE (ZH)": "英语（英国）", "Applicable CDragon Data Patches": "9.1+"}, 7: {"CODE": "de_DE", "LANGUAGE (EN)": "German (Germany)", "LANGUAGE (ZH)": "德语（德国）", "Applicable CDragon Data Patches": "7.1+"}, 8: {"CODE": "es_ES", "LANGUAGE (EN)": "Spanish (Spain)", "LANGUAGE (ZH)": "西班牙语（西班牙）", "Applicable CDragon Data Patches": "9.1+"}, 9: {"CODE": "it_IT", "LANGUAGE (EN)": "Italian (Italy)", "LANGUAGE (ZH)": "意大利语（意大利）", "Applicable CDragon Data Patches": "9.1+"}, 10: {"CODE": "fr_FR", "LANGUAGE (EN)": "French (France)", "LANGUAGE (ZH)": "法语（法国）", "Applicable CDragon Data Patches": "9.1+"}, 11: {"CODE": "ja_JP", "LANGUAGE (EN)": "Japanese (Japan)", "LANGUAGE (ZH)": "日语（日本）", "Applicable CDragon Data Patches": "9.1+"}, 12: {"CODE": "ko_KR", "LANGUAGE (EN)": "Korean (Korea)", "LANGUAGE (ZH)": "朝鲜语（韩国）", "Applicable CDragon Data Patches": "9.7+"}, 13: {"CODE": "es_MX", "LANGUAGE (EN)": "Spanish (Mexico)", "LANGUAGE (ZH)": "西班牙语（墨西哥）", "Applicable CDragon Data Patches": "9.1+"}, 14: {"CODE": "es_AR", "LANGUAGE (EN)": "Spanish (Argentina)", "LANGUAGE (ZH)": "西班牙语（阿根廷）", "Applicable CDragon Data Patches": "9.7+"}, 15: {"CODE": "pt_BR", "LANGUAGE (EN)": "Portuguese (Brazil)", "LANGUAGE (ZH)": "葡萄牙语（巴西）", "Applicable CDragon Data Patches": "9.1+"}, 16: {"CODE": "en_US", "LANGUAGE (EN)": "English (United States)", "LANGUAGE (ZH)": "英语（美国）", "Applicable CDragon Data Patches": "9.1+"}, 17: {"CODE": "en_AU", "LANGUAGE (EN)": "English (Australia)", "LANGUAGE (ZH)": "英语（澳大利亚）", "Applicable CDragon Data Patches": "9.1+"}, 18: {"CODE": "ru_RU", "LANGUAGE (EN)": "Russian (Russia)", "LANGUAGE (ZH)": "俄语（俄罗斯）", "Applicable CDragon Data Patches": "9.1+"}, 19: {"CODE": "tr_TR", "LANGUAGE (EN)": "Turkish (Turkey)", "LANGUAGE (ZH)": "土耳其语（土耳其）", "Applicable CDragon Data Patches": "9.1+"}, 20: {"CODE": "ms_MY", "LANGUAGE (EN)": "Malay (Malaysia)", "LANGUAGE (ZH)": "马来语（马来西亚）", "Applicable CDragon Data Patches": ""}, 21: {"CODE": "en_PH", "LANGUAGE (EN)": "English (Republic of the Philippines)", "LANGUAGE (ZH)": "英语（菲律宾共和国）", "Applicable CDragon Data Patches": "10.5+"}, 22: {"CODE": "en_SG", "LANGUAGE (EN)": "English (Singapore)", "LANGUAGE (ZH)": "英语（新加坡）", "Applicable CDragon Data Patches": "10.5+"}, 23: {"CODE": "th_TH", "LANGUAGE (EN)": "Thai (Thailand)", "LANGUAGE (ZH)": "泰语（泰国）", "Applicable CDragon Data Patches": "9.7+"}, 24: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "9.7～13.9"}, 25: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "12.17+"}, 26: {"CODE": "id_ID", "LANGUAGE (EN)": "Indonesian (Indonesia)", "LANGUAGE (ZH)": "印度尼西亚语（印度尼西亚）", "Applicable CDragon Data Patches": ""}, 27: {"CODE": "zh_MY", "LANGUAGE (EN)": "Chinese (Malaysia)", "LANGUAGE (ZH)": "中文（马来西亚）", "Applicable CDragon Data Patches": "10.5+"}, 28: {"CODE": "zh_CN", "LANGUAGE (EN)": "Chinese (China)", "LANGUAGE (ZH)": "中文（中国）", "Applicable CDragon Data Patches": "9.7+"}, 29: {"CODE": "zh_TW", "LANGUAGE (EN)": "Chinese (Taiwan)", "LANGUAGE (ZH)": "中文（台湾）", "Applicable CDragon Data Patches": "9.7+"}}
    for i in range(1, 30):
        print(str(i) + "\t" + language[i]["CODE"] + "\t" + language[i]["LANGUAGE (EN)"] + "\t" + language[i]["LANGUAGE (ZH)"] + "\t" + language[i]["Applicable CDragon Data Patches"])
    while True:
        language_option = input()
        if language_option == "" or language_option in [str(i) for i in range(1, 30)]:
            if language_option == "":
                language_option = "28"
            language_code = language[int(language_option)]["CODE"]
            #下面声明一些数据资源的地址（The following code declare some data resources' URLs）
            patches_url = "https://ddragon.leagueoflegends.com/api/versions.json"
            #下面声明离线数据资源的默认地址（The following code declare the default paths of offline data resources）
            patches_local_default = "离线数据（Offline Data）\\versions.json"
            champion_local_default = "离线数据（Offline Data）\\champion.json"
            break
        else:
            print("语言选项输入错误！请重新输入：\nERROR input of language option! Please try again:")
    try:
        patches = requests.get(patches_url)
    except requests.exceptions.RequestException:
        print('版本信息获取超时！正在尝试离线加载数据……\nPatch information capture timeout! Trying loading offline data ...\n请输入版本Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“0”以退出程序。\nPlease enter the patch Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(patches_local_default, patches_local_default))
        while True:
            patches_local = input()
            if patches_local == "":
                patches_local = patches_local_default
            elif patches_local[0] == "0":
                print("版本信息获取失败！请检查系统网络状况和代理设置。\nPatch information capture failure! Please check the system network condition and agent configuration.")
                time.sleep(5)
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
    else:
        patches = patches.json()
        latest_patch = patches[0]
    if source[0] == "2":
        print("请输入您想要获取的版本。输入空字符串以获取最新版本英雄信息。\nPlease input the patch you want to search from. Submit an empty string to get the latest champion data. Examples: \n" + ", ".join(patches[:-98]))
        while True:
            patch_in_url = input()
            if patch_in_url == "":
                patch_in_url = patches[0]
            if patch_in_url in patches[:-98]:
                champion_url = "http://ddragon.leagueoflegends.com/cdn/%s/data/%s/champion.json" %(patch_in_url, language_code)
                break
            else:
                print("版本输入有误！请重新输入。\nERROR input of patch! Please try again!")
    else:
        print("请输入您想要获取的版本。输入空字符串以获取最新版本英雄信息。\nPlease input the patch you want to search from. Submit an empty string to get the latest champion data. Examples: ")
        cdragon_homepage = requests.get("https://raw.communitydragon.org/") #对应于DataDragon数据库的版本，下面从CommunityDragons数据库主页的源代码获取可用版本（Corresponding to getting patches DataDragon database, the following code crawl the available patches in CommunityDragon database through its homepage）
        if cdragon_homepage.ok:
            source = cdragon_homepage.content.decode()
            source_list = list(map(lambda x: x.strip(), source.split("\n")))
            line_re = re.compile('<tr><td class="link"><a href="[0-9]*\.[0-9]*/" title="[0-9]*\.[0-9]*">[0-9]*\.[0-9]*/</a></td><td class="size">-</td><td class="date">[0-9]*-[a-zA-Z]*-[0-9]* [0-9]*:[0-9]*</td></tr>')
            patch_re = re.compile('[0-9]*\.[0-9]*')
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
                    patch_in_url = patches_cdragon[0]
                if patch_in_url in patches_cdragon:
                    champion_url = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(patch_in_url, language_code.lower())
                    break
                else:
                    print("版本输入有误！请重新输入。\nERROR input of patch! Please try again!")
        else:
            print("CommunityDragon数据库主页源代码获取失败！请检查系统网络状况和代理设置。CommunityDragon database homepage source code capture failure! Please check the system network condition and agent configuration.")
            time.sleep(5)
            exit()
    try:
        champion = requests.get(champion_url).json()
    except requests.exceptions.RequestException:
        print('英雄数据获取超时！正在尝试离线加载数据……\nChampion data capture timeout! Trying loading offline data ...\n请输入英雄Json数据文件路径。输入空字符以使用默认相对引用路径“%s”。输入“0”以退出程序。\nPlease enter the champion Json data file path. Enter an empty string to use the default relative path: "%s". Submit "0" to exit.' %(patches_local_default, patches_local_default))
        while True:
            champion_local = input()
            if champion_local == "":
                champion_local = champion_local_default
            elif champion_local[0] == "0":
                print("英雄数据获取失败！请检查系统网络状况和代理设置。\nChampion data capture failure! Please check the system network condition and agent configuration.")
                time.sleep(5)
                exit()
            try:
                with open(champion_local, "r", encoding = "utf-8") as fp:
                    champion = json.load(fp)
                if source[0] == "2" and isinstance(champion, dict) and all(i in champion for i in ["type", "format", "version", "data"]) and champion["type"] == "champion" and all(j in champion["data"][i] for i in range(len(champion["data"])) for j in ["version", "id", "key", "name", "title", "blurb", "info", "image", "tags", "partype", "stats"]) or source[0] == "3" and isinstance(champion, list) and all(j in champion[i] for i in range(len(champion)) for j in ["id", "name", "alias", "squarePortraitPath", "roles"]):
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
    #下面按照程序需求对数据资源进行一定的整理（The following code sort out the data resource according to the program's need）
    if source[0] == "2":
        champions = {} #champions为嵌套字典，键为英雄序号，值为英雄信息字典。一个键值对的示例如右：（Variable `champions` is a nested dictionary, whose keys are championIds and values are champions' information dictionaries. An example of the key-value pairs is shown as follows: ）{266: {"version": "13.20.1", "id": "Aatrox", "name": "暗裔剑魔", "title": "亚托克斯", "blurb": "亚托克斯和他的同胞曾是为恕瑞玛对抗虚空的守护者一族。曾经满载荣誉的他们，却成了符文之地上更大的威胁，最后被人类设下的圈套所击败。在被囚禁数个世纪后，亚托克斯率先找到了重获自由的方法：他的精魂被封印在了那把神奇武器之中，而那些妄图挥舞它的愚昧之徒都会被他腐蚀、侵占。如今，他凭借偷来的身躯，以一种近似他曾经形态的凶残外表行走于符文之地，寻求着一次毁天灭地、迟来许久的复仇。", "info": {"attack": 8, "defense": 4, "magic": 3, "difficulty": 4}, "image": {"full": "Aatrox.png", "sprite": "champion0.png", "group": "champion", "x": 0, "y": 0, "w": 48, "h": 48}, "tags": ["Fighter", "Tank"], "partype": "鲜血魔井", "stats": {"hp": 650, "hpperlevel": 114, "mp": 0, "mpperlevel": 0, "movespeed": 345, "armor": 38, "armorperlevel": 4.45, "spellblock": 32, "spellblockperlevel": 2.05, "attackrange": 175, "hpregen": 3, "hpregenperlevel": 1, "mpregen": 0, "mpregenperlevel": 0, "crit": 0, "critperlevel": 0, "attackdamage": 60, "attackdamageperlevel": 5, "attackspeedperlevel": 2.5, "attackspeed": 0.651}}}
        for champion_iter in champion["data"].values():
            champion_key = int(champion_iter.pop("key"))
            champions[champion_key] = champion_iter
        count = 0
        f = open("Champion List.txt", "w")
        header = "championId\tname\ttitle\n"
        print(header, end = "")
        f.write(header)
        for i in sorted(champions.keys()):
            entry = "%s\t%s\t%s\n" %(i, champions[i]["name"], champions[i]["title"])
            print(entry, end = "")
            f.write(entry)
            if int(i) > 0: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                count += 1
        print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
        f.close()
        input()
        exit() #执行到此，程序结束（Here the program terminates）
    else:
        champions = {} #champions为嵌套字典，键为英雄序号，值为英雄信息字典。一个键值对的示例如右：（Variable `champions` is a nested dictionary, whose keys are championIds and values are champions' information dictionaries. An example of the key-value pairs is shown as follows: ）{266: {"version": "13.20.1", "id": "Aatrox", "name": "暗裔剑魔", "title": "亚托克斯", "blurb": "亚托克斯和他的同胞曾是为恕瑞玛对抗虚空的守护者一族。曾经满载荣誉的他们，却成了符文之地上更大的威胁，最后被人类设下的圈套所击败。在被囚禁数个世纪后，亚托克斯率先找到了重获自由的方法：他的精魂被封印在了那把神奇武器之中，而那些妄图挥舞它的愚昧之徒都会被他腐蚀、侵占。如今，他凭借偷来的身躯，以一种近似他曾经形态的凶残外表行走于符文之地，寻求着一次毁天灭地、迟来许久的复仇。", "info": {"attack": 8, "defense": 4, "magic": 3, "difficulty": 4}, "image": {"full": "Aatrox.png", "sprite": "champion0.png", "group": "champion", "x": 0, "y": 0, "w": 48, "h": 48}, "tags": ["Fighter", "Tank"], "partype": "鲜血魔井", "stats": {"hp": 650, "hpperlevel": 114, "mp": 0, "mpperlevel": 0, "movespeed": 345, "armor": 38, "armorperlevel": 4.45, "spellblock": 32, "spellblockperlevel": 2.05, "attackrange": 175, "hpregen": 3, "hpregenperlevel": 1, "mpregen": 0, "mpregenperlevel": 0, "crit": 0, "critperlevel": 0, "attackdamage": 60, "attackdamageperlevel": 5, "attackspeedperlevel": 2.5, "attackspeed": 0.651}}}
        for champion_iter in champion:
            champion_id = int(champion_iter.pop("id"))
            champions[champion_id] = champion_iter
        count = 0
        f = open("Champion List.txt", "w")
        header = "championId\tname\talias\n"
        print(header, end = "")
        f.write(header)
        for i in sorted(champions.keys()):
            entry = "%s\t%s\t%s\n" %(i, champions[i]["name"], champions[i]["alias"])
            print(entry, end = "")
            f.write(entry)
            if i > 0: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                count += 1
        print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
        f.close()
        input()
        exit() #执行到此，程序结束（Here the program terminates）

connector = Connector()

async def get_summoner_data(connection):
    data = await connection.request('GET', '/lol-summoner/v1/current-summoner')
    global summoner
    summoner = await data.json()
    print(f"displayName:    {summoner['displayName']}")
    print(f"summonerId:     {summoner['summonerId']}")
    print(f"puuid:          {summoner['puuid']}")
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
# 向服务器发送指令（Send commands to the server）
#-----------------------------------------------------------------------------
async def send_commands(connection):
    method = ""
    command = "0"
    print("请依次输入方法和统一资源标识符，以空格为分隔符：\nPlease enter the method and URI, split by space:\n示例：\nExamples:\nGET /lol-lobby/v2/lobby\nPOST /lol-lobby/v2/lobby/matchmaking/search\nPUT /lol-lobby/v2/lobby/partyType\nDELETE /lol-lobby-team-builder/v1/lobby\nPATCH /lol-lobby-team-builder/champ-select/v1/session/my-selection\n")
    while command[0] != "3":
        method, command = input().split()
        if command == "":
            command = "0"
        else:
            data = await connection.request(method, command)
            print(await data.json())

#-----------------------------------------------------------------------------
# 创建训练模式 5V5 自定义房间（Create a Practice Tool lobby）
#-----------------------------------------------------------------------------
async def create_custom_lobby(connection):
    custom = {
        "customGameLobby": {
            "configuration": {
                "gameMode": "PRACTICETOOL",
                "gameMutator": "",
                "gameServerRegion": "",
                "mapId": 11,
                "mutators": {
                    "id": 1
                },
            "spectatorPolicy": "AllAllowed",
            "teamSize": 5
            },
            "lobbyName": "可用电脑英雄测试（程序结束前请勿退出）",
            "lobbyPassword": ""
        },
        "isCustom": True
    }
    await connection.request("POST", "/lol-lobby/v2/lobby", data=custom)

#-----------------------------------------------------------------------------
# 统计英雄数量（Count all champions）
#-----------------------------------------------------------------------------
async def count_all_champions(connection):
    count = 0
    f = open("Champion List.txt", "w")
    header = "championId\tname\talias\n"
    print(header, end = "")
    f.write(header)
    champions = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %summoner["summonerId"])).json()
    alias_dict = {4: "Twisted Fate", 5: "Xin Zhao", 11: "Master Yi", 20: "Nunu & Willump", 21: "Miss Fortune", 31: "Cho'Gath", 36: "Dr. Mundo", 59: "Jarvan IV", 62: "Monkey King", 64: "Lee Sin", 96: "Kog'Maw", 136: "Aurelion Sol", 145: "Kai'Sa", 161: "Vel'Koz", 200: "Bel'Veth", 223: "Tahm Kench", 421: "Rek'Sai", 888: "Renata Glasc", 897: "K'Sante"}
    for champion in champions:
        if champion["id"] in alias_dict.keys():
            alias = alias_dict[champion["id"]]
        else:
            alias = champion["alias"]
        entry = "%s\t%s\t%s\n" %(champion["id"], champion["name"], alias)
        print(entry, end = "")
        f.write(entry)
        if champion["id"] > 0: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
            count += 1
    print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
    f.close()
    input()

#-----------------------------------------------------------------------------
# 统计电脑英雄数量（Count all bot champions）
#-----------------------------------------------------------------------------
async def count_all_bots(connection):
    count = 0
    f = open("Champion List.txt", "w")
    header = "championId\tname\talias\n"
    print(header, end = "")
    f.write(header)
    champions = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %summoner["summonerId"])).json()
    await create_custom_lobby(connection)
    alias_dict = {4: "Twisted Fate", 5: "Xin Zhao", 11: "Master Yi", 20: "Nunu & Willump", 21: "Miss Fortune", 31: "Cho'Gath", 36: "Dr. Mundo", 59: "Jarvan IV", 62: "Monkey King", 64: "Lee Sin", 96: "Kog'Maw", 136: "Aurelion Sol", 145: "Kai'Sa", 161: "Vel'Koz", 200: "Bel'Veth", 223: "Tahm Kench", 421: "Rek'Sai", 888: "Renata Glasc", 897: "K'Sante"}
    for champion in champions:
        bot = { "championId": champion["id"], "botDifficulty": "HARD", "teamId": "200"}
        await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)
        time.sleep(0.1) #由于服务器响应速度原因，从添加电脑到房间信息更新，需要0.1秒的缓冲时间（0.1s buffer time is needed between adding a bot and updating the lobby information due to the server response speed）
        lobby = await(await connection.request("GET", "/lol-lobby/v2/lobby")).json()
        if len(lobby["gameConfig"]["customTeam200"]) == 1 and lobby["gameConfig"]["customTeam200"][0]["botChampionId"] == champion["id"]:
            if champion["id"] in alias_dict.keys():
                alias = alias_dict[champion["id"]]
            else:
                alias = champion["alias"]
            entry = "%s\t%s\t%s\n" %(champion["id"], champion["name"], alias)
            print(entry, end = "")
            f.write(entry)
            if champion["id"] > 0: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                count += 1
        for player in lobby["gameConfig"]["customTeam200"]:
            await connection.request("DELETE", "/lol-lobby/v1/lobby/custom/bots/%s" %player["botId"])
    print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
    f.close()
    input()

#-----------------------------------------------------------------------------
# 统计当前房间可用电脑英雄数量（Count available bots in the current lobby）
#-----------------------------------------------------------------------------
async def count_available_bots(connection):
    count = 0
    lobby = await(await connection.request("GET", "/lol-lobby/v2/lobby")).json()
    if "errorCode" in lobby and lobby["message"] == "LOBBY_NOT_FOUND":
        print("请确保您正在房间内！程序即将退出！\nPlease make sure you're in a lobby! The program will exit soon!")
        time.sleep(3)
        exit()
    bots_enabled = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/bots-enabled")).json()
    if bots_enabled == False:
        print("该房间无可用电脑玩家。请输入任意键退出。\nThere're no available bot champions in this lobby. Please press any key to exit.")
        input()
        return 0
    f = open("Champion List.txt", "w")
    header = "championId\tname\talias\n"
    print(header, end = "")
    f.write(header)
    champions = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %summoner["summonerId"])).json()
    alias_dict = {4: "Twisted Fate", 5: "Xin Zhao", 11: "Master Yi", 20: "Nunu & Willump", 21: "Miss Fortune", 31: "Cho'Gath", 36: "Dr. Mundo", 59: "Jarvan IV", 62: "Monkey King", 64: "Lee Sin", 96: "Kog'Maw", 136: "Aurelion Sol", 145: "Kai'Sa", 161: "Vel'Koz", 200: "Bel'Veth", 223: "Tahm Kench", 421: "Rek'Sai", 888: "Renata Glasc", 897: "K'Sante"}
    available_bots = await (await connection.request("GET", "/lol-lobby/v2/lobby/custom/available-bots")).json()
    available_botIds = [bot["id"] for bot in available_bots]
    for champion in champions:
        if champion["id"] in available_botIds:
            if champion["id"] in alias_dict.keys():
                alias = alias_dict[champion["id"]]
            else:
                alias = champion["alias"]
            entry = "%s\t%s\t%s\n" %(champion["id"], champion["name"], alias)
            print(entry, end = "")
            f.write(entry)
            if champion["id"] > 0: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                count += 1
    print("\n统计完毕，共%d名英雄。请输入任意键退出。\nCount finished! There're %d champions in total. Please press any key to exit." %(count, count))
    f.close()
    input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await update_lockfile(connection)
    await get_lockfile(connection)
    #await send_commands(connection)
    print("请选择统计类型：\nPlease select which type of champions to count:\n1\t所有英雄（All champions）\n2\t所有电脑英雄（All bot champions）\n3\t当前房间可用电脑英雄（Available bot champions in this lobby）")
    while True:
        count = input()
        if count == "":
            continue
        elif count[0] == "1":
            await count_all_champions(connection)
            break
        elif count[0] == "2":
            print("正在统计中，请勿退出房间。\nCounting the bot champions. Please don't exit the lobby.")
            await count_all_bots(connection)
            break
        elif count[0] == "3":
            await count_available_bots(connection)
            break
        else:
            print("您的输入有误，请重新输入！\nERROR input! Please try again!")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
