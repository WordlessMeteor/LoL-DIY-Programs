from lcu_driver import Connector
import os, requests, time, pyperclip
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
opened = False #用于message_save函数，如果每次查询第一次打开日志文件，那么在输出所有信息前，先在文件前添加一个换行符。这样可以避免程序在运行中断后再次执行时光标紧跟上次文件的末尾（Used in `message_save` function. If a log file has been opened for the first time during a search of a summoner's matches, then add a line feed character before writing anything, in case the cursor closely follows the end of the log file when an error occurs during the last run of the program）
def message_save(message, folder, summonerName, header = ""):
    global opened
    try:
        log = open(os.path.join(folder, "Matches of Summoners - %s.log" %summonerName), "a+", encoding = "utf-8")
    except FileNotFoundError:
        print("请先使用一次查战绩脚本查询该玩家信息，再使用本脚本！程序即将退出。\nPlease use Customized Program 5 to search for this summoner's information and then use this program! The program will exit now.")
        os._exit(0)
    if opened == False:
        log.write("\n")
        opened = True
    log.write("%s[%s]%s\n" %(header, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), message))
    log.close()
    return 0

def platform_format(platform = '{"TENCENT": "国服（TENCENT）", "RIOT": "外服（RIOT）", "GARENA": "竞舞"}'): #用于将自定义脚本5中的平台字典文本转换成本脚本文件中的嵌套平台字典文本。请不要使用str函数将字典强制转为字符串后传入形式参数platform。这是因为英文中的“'s”容易与用于表示代码的“'”产生混淆（Transforms texts of the platform dictionaries into texts of the nested dictionaries in this program. Please don't pass a string transformed into from a dictionary force by `str` function to the formal parameter. This is because "'s" in English is easily obscured with the "'" in code）
    formatted = platform.replace('": "', '": {"zh_CN": "').replace('）", "', '"}, "').replace("（", '", "en_US": "').replace('）"', '"}')
    pyperclip.copy(formatted)
    print("已复制转换后的平台字典信息。\nSuccessfully copied the transformed dictionary information.")
    return formatted

async def search_summoner_online(connection):
    platform_TENCENT = {"BGP1": {"zh_CN": "全网通区 男爵领域", "en_US": "Baron Zone"}, "BGP2": {"zh_CN": "峡谷之巅", "en_US": "Super Zone"}, "EDU1": {"zh_CN": "教育网专区", "en_US": "CRENET Server"}, "HN1": {"zh_CN": "电信一区 艾欧尼亚", "en_US": "Ionia"}, "HN2": {"zh_CN": "电信二区 祖安", "en_US": "Zaun"}, "HN3": {"zh_CN": "电信三区 诺克萨斯", "en_US": "Noxus 1"}, "HN4": {"zh_CN": "电信四区 班德尔城", "en_US": "Bandle City"}, "HN5": {"zh_CN": "电信五区 皮尔特沃夫", "en_US": "Piltover"}, "HN6": {"zh_CN": "电信六区 战争学院", "en_US": "the Institute of War"}, "HN7": {"zh_CN": "电信七区 巨神峰", "en_US": "Mount Targon"}, "HN8": {"zh_CN": "电信八区 雷瑟守备", "en_US": "Noxus 2"}, "HN9": {"zh_CN": "电信九区 裁决之地", "en_US": "the Proving Grounds"}, "HN10": {"zh_CN": "电信十区 黑色玫瑰", "en_US": "the Black Rose"}, "HN11": {"zh_CN": "电信十一区 暗影岛", "en_US": "Shadow Isles"}, "HN12": {"zh_CN": "电信十二区 钢铁烈阳", "en_US": "the Iron Solari"}, "HN13": {"zh_CN": "电信十三区 水晶之痕", "en_US": "Crystal Scar"}, "HN14": {"zh_CN": "电信十四区 均衡教派", "en_US": "the Kinkou Order"}, "HN15": {"zh_CN": "电信十五区 影流", "en_US": "the Shadow Order"}, "HN16": {"zh_CN": "电信十六区 守望之海", "en_US": "Guardian's Sea"}, "HN17": {"zh_CN": "电信十七区 征服之海", "en_US": "Conqueror's Sea"}, "HN18": {"zh_CN": "电信十八区 卡拉曼达", "en_US": "Kalamanda"}, "HN19": {"zh_CN": "电信十九区 皮城警备", "en_US": "Piltover Wardens"}, "PBE": {"zh_CN": "体验服 试炼之地", "en_US": "Chinese PBE"}, "WT1": {"zh_CN": "网通一区 比尔吉沃特", "en_US": "Bilgewater"}, "WT2": {"zh_CN": "网通二区 德玛西亚", "en_US": "Demacia"}, "WT3": {"zh_CN": "网通三区 弗雷尔卓德", "en_US": "Freljord"}, "WT4": {"zh_CN": "网通四区 无畏先锋", "en_US": "House Crownguard"}, "WT5": {"zh_CN": "网通五区 恕瑞玛", "en_US": "Shurima"}, "WT6": {"zh_CN": "网通六区 扭曲丛林", "en_US": "Twisted Treeline"}, "WT7": {"zh_CN": "网通七区 巨龙之巢", "en_US": "the Dragon Camp"}}
    platform_RIOT = {"BR": {"zh_CN": "巴西服", "en_US": "Brazil"}, "EUNE": {"zh_CN": "北欧和东欧服", "en_US": "Europe Nordic & East"}, "EUW": {"zh_CN": "西欧服", "en_US": "Europe West"}, "LAN": {"zh_CN": "北拉美服", "en_US": "Latin America North"}, "LAS": {"zh_CN": "南拉美服", "en_US": "Latin America South"}, "NA": {"zh_CN": "北美服", "en_US": "North America"}, "OCE": {"zh_CN": "大洋洲服", "en_US": "Oceania"}, "RU": {"zh_CN": "俄罗斯服", "en_US": "Russia"}, "TR": {"zh_CN": "土耳其服", "en_US": "Turkey"}, "JP": {"zh_CN": "日服", "en_US": "Japan"}, "KR": {"zh_CN": "韩服", "en_US": "Republic of Korea"}, "PBE": {"zh_CN": "测试服", "en_US": "Public Beta Environment"}}
    platform_GARENA = {"PH": {"zh_CN": "菲律宾服", "en_US": "Philippines"}, "SG": {"zh_CN": "新加坡服", "en_US": "Singapore, Malaysia and Indonesia"}, "TW": {"zh_CN": "台服", "en_US": "Taiwan, Hong Kong and Macau"}, "VN": {"zh_CN": "越南服", "en_US": "Vietnam"}, "TH": {"zh_CN": "泰服", "en_US": "Thailand"}}
    current_info = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    while True:
        print('请输入您想要查询的召唤师名称。输入“0”以退出。\nPlease enter the name of the summoner you want to look up. Submit "0" to exit.')
        name = input()
        if name == "":
            continue
        elif name == "0":
            break
        else:
            global opened
            opened = False
            #由于召唤师可能使用过改名卡，因此需要依据玩家通用唯一识别码来查询某玩家是否进行过某场对局（Since a summoner may have used the Summoner Name Change, puuid is used to judge whether a summoner is in a match）
            if name.replace(" ", "").count("-") == 4 and len(name.replace(" ", "")) > 22: #拳头规定的玩家名称不超过16个字符，尾标不超过5个字符（Riot game name can't exceed 16 characters. The tagline can't exceed 5 characters）
                search_by_puuid = True
                info = await (await connection.request("GET", "/lol-summoner/v2/summoners/puuid/" + quote(name))).json()
            else:
                search_by_puuid = False
                info = await (await connection.request("GET", "/lol-summoner/v1/summoners?name=" + quote(name))).json()
            if "errorCode" in info and info["httpStatus"] == 400:
                if search_by_puuid:
                    print("您输入的玩家通用唯一识别码格式有误！请重新输入！\nPUUID wasn't in UUID format! Please try again!")
                else:
                    print("您输入的召唤师名称格式有误！请重新输入！\nERROR format of summoner name! Please try again!")
            if "errorCode" in info and info["httpStatus"] == 404:
                if search_by_puuid:
                    print("未找到玩家通用唯一识别码为" + name + "的玩家；请核对识别码并稍后再试。\nA player with puuid " + name + " was not found; verify the puuid and try again.")
                else:
                    print("未找到" + name + "；请核对下名字并稍后再试。\n" + name + " was not found; verify the name and try again.")
            elif "errorCode" in info and info["httpStatus"] == 422:
                print('召唤师名称已变更为拳头ID。请以“{召唤师名称}#{尾标}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"]))
            elif "accountId" in info:
                displayName = info["displayName"] if info["displayName"] else info["gameName"] #用于文件名命名（For use of file naming）
                puuid = info["puuid"]
                switch_summoner = False #控制是否返回到输入召唤师名称的步骤（Controls returning to the step that requires inputting summoner name）
                #设置输出信息中关于召唤师大区的描述（Adjust the description of the current server in printed information）
                riot_client_info = await (await connection.request("GET", "/riotclient/command-line-args")).json()
                client_info = {}
                for i in range(len(riot_client_info)):
                    try:
                        client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
                    except IndexError:
                        pass
                region = client_info["--region"]
                if region == "TENCENT":
                    platform = platform_TENCENT[client_info["--rso_platform_id"]]
                    folder = "召唤师信息（Summoner Information）\\" + "国服（TENCENT）" + "\\" + platform_TENCENT[client_info["--rso_platform_id"]]["zh_CN"] + "（" + platform_TENCENT[client_info["--rso_platform_id"]]["en_US"] + "）" + "\\" + displayName
                elif region == "GARENA":
                    platform = platform_GARENA[region]
                    folder = "召唤师信息（Summoner Information）\\" + "竞舞（GARENA）" + "\\" + platform_GARENA[region]["zh_CN"] + "（" + platform_GARENA[region]["en_US"] + "）" + "\\" + displayName
                else:
                    platform = (platform_RIOT | platform_GARENA)[region]
                    folder = "召唤师信息（Summoner Information）\\" + "外服（RIOT）" + "\\" + (platform_RIOT | platform_GARENA)[region]["zh_CN"] + "（" + (platform_RIOT | platform_GARENA)[region]["en_US"] + "）" + "\\" + displayName
                message = "正在【在线】查询%s大区召唤师%s（玩家通用唯一识别码：%s）的对局……\n[Online] searching for matches of the summoner %s (puuid: %s) on %s server..." %(platform["zh_CN"], displayName, puuid, displayName, puuid, platform["en_US"]) #这里考虑到当程序异常中断时，再次运行该程序，文件中新行会紧跟上次运行的最后一行，不容易区分。所以在字符串最前面加了一个换行符。但是这样的话，在创建文件时，第一行也会变成空行。用户如果觉得不顺眼，可以直接双击日志文件去掉第一行，这样看着舒服一些（Considering when the program 
                message_save(message, folder, displayName, "【参数设置】")
                #从输入获取要查询的对局序号范围（Get matchID range from input）
                print("请输入您要查询的对局序号的下限和上限，以空格为分隔符：\nPlease enter the lower and upper bounds of the matchIDs to be searched, split by space:")
                while True:
                    gameIndices = input()
                    if gameIndices == "":
                        continue
                    try:
                        gameIndexBegin, gameIndexEnd = map(int, gameIndices.split())
                    except ValueError:
                        if gameIndices[0] == "0":
                            switch_summoner = True
                            break
                        else:
                            print('请输入以空格分隔的两个正整数！如“70000000 80000000”。\nPlease enter two positive integers split by space! For example, "70000000 80000000".')
                            continue
                    else:
                        if gameIndexBegin <= 0 or gameIndexEnd <= 0:
                            print('请输入以空格分隔的两个正整数！如“70000000 80000000”。\nPlease enter two positive integers split by space! For example, "70000000 80000000".')
                            continue
                        else:
                            message = "本次查询的对局序号范围（MatchID range for this query）：[%d, %d]" %(gameIndexBegin, gameIndexEnd)
                            message_save(message + "\n", folder, displayName, "【参数设置】")
                            break
                if switch_summoner:
                    continue
                #查询前的数据结构准备（Data structure prepared for query）
                matches_found = []
                gameCount = gameIndexEnd - gameIndexBegin + 1
                for matchID in range(gameIndexBegin, gameIndexEnd + 1):
                    currentProcess = matchID - gameIndexBegin + 1
                    matchID = str(matchID)
                    game_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                    error_occurred = False
                    
                    #尝试修复错误（Try to fix the error）
                    if "errorCode" in game_info:
                        count = 0
                        if game_info["httpStatus"] == 404:
                            message = "（%d/%d）" %(currentProcess, gameCount) + "未找到序号为" + matchID + "的回放文件！将忽略该序号。\nMatch file with matchID " + matchID + " not found! The program will ignore this matchID."
                            print(message)
                            message_save(message, folder, displayName, "【异常信息】")
                            continue
                        if "500 Internal Server Error" in game_info["message"]:
                            if error_occurred == False:
                                error_occurred = True
                                message = "（%d/%d）" %(currentProcess, gameCount) + "您所在大区的对局记录服务异常。尝试重新获取数据……\nThe match history service provided on your server isn't in place. Trying to recapture the history data ..."
                                print(message)
                                message_save(message, folder, displayName, "【异常信息】")
                            while "errorCode" in game_info and "500 Internal Server Error" in game_info["message"] and count <= 3:
                                count += 1
                                message = "（%d/%d）" %(currentProcess, gameCount) + "正在第%d次尝试获取对局%s信息……\nTimes trying to capture Match %s: No. %d ..." %(count, matchID, matchID, count)
                                print(message)
                                message_save(message, folder, displayName, "【异常处理】")
                                game_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                        elif "Connection timed out after " in game_info["message"]:
                            fetched_info = False
                            message = "（%d/%d）" %(currentProcess, gameCount) + "对局信息保存超时！请检查网速状况！\nGame information saving operation timed out after 20000 milliseconds with 0 bytes received! Please check the netspeed!"
                            print(message)
                            message_save(message, folder, displayName, "【异常信息】")
                        elif "Service Unavailable - Connection retries limit exceeded. Response timed out" in game_info["message"]:
                            if error_occurred == False:
                                error_occurred = True
                                message = "（%d/%d）" %(currentProcess, gameCount) + "访问频繁。尝试重新获取数据……\nConnection retries limit exceeded! Trying to recapture the match data ..."
                                print(message)
                                message_save(message, folder, displayName, "【异常处理】")
                            while "errorCode" in game_info and "Service Unavailable - Connection retries limit exceeded. Response timed out" in game_info["message"] and count <= 3:
                                count += 1
                                message = "（%d/%d）" %(currentProcess, gameCount) + "正在第%d次尝试获取对局%s信息……\nTimes trying to capture Match %s: No. %d ..." %(count, matchID, matchID, count)
                                print(message)
                                message_save(message, folder, displayName, "【异常处理】")
                                game_info = await (await connection.request("GET", "/lol-match-history/v1/games/" + matchID)).json()
                        if count > 3:
                            fetched_info = False
                            message = "（%d/%d）" %(currentProcess, gameCount) + "对局%s信息获取失败！\nMatch %s information capture failure!" %(matchID, matchID)
                            print(message)
                            message_save(message, folder, displayName, "【异常信息】")
                            continue
                    if "errorCode" in game_info:
                        fetched_info = False
                        message = "（%d/%d）" %(currentProcess, gameCount) + "对局%s信息获取失败！\nMatch %s information capture failure!" %(matchID, matchID)
                        print(message)
                        message_save(message + "\n" + str(game_info), folder, displayName, "【异常信息】")
                        print(game_info)
                        continue
                    else:
                        main_player_found = False
                        players = []
                        for participant in game_info["participantIdentities"]:
                            if participant["player"]["puuid"] == puuid:
                                main_player_found = True
                                break
                        if main_player_found:
                            message = "（%d/%d）" %(currentProcess, gameCount) + "【√】对局%s包含该玩家。已将其加入列表。\nMatch %s contains this summoner and has been added to the matches_found list." %(matchID, matchID)
                            print(message)
                            message_save(message, folder, displayName, "【找到对局】")
                            matches_found.append(matchID)
                        else:
                            message = "（%d/%d）" %(currentProcess, gameCount) + "对局%s不包含该玩家。\nMatch %s doesn't contain this summoner." %(matchID, matchID)
                            print(message)
                            message_save(message, folder, displayName, "【跳过对局】")
                #保存数据到本地文件（Saved data to a local file）
                print(matches_found)
                print('共找到%d场对局！对局序号已保存到“%s”文件夹下的日志文件。\nMatches found: %d. MatchIDs have been saved into the log file in directory "%s": "Matches of Summoners.log".' %(len(matches_found), folder, len(matches_found), folder))
                message_save("共找到%d场对局。" %(len(matches_found)), folder, displayName, "【结果】")
                result = "%s大区的召唤师%s（玩家通用唯一识别码：%s）参与的对局如下：\nMatches that involve summoner %s (puuid: %s) on %s server are as follows:\n%s\n\n" %(platform["zh_CN"], displayName, puuid, displayName, puuid, platform["en_US"], str(matches_found))
                message_save(result, folder, displayName, "【结果】")
        
def search_summoner_offline(connection): #由于无法使用requests.get函数获取离线链接中的json文件，该函数尚不可用（Because the json files in the non-LCU link can'be fetched by `requests.get` function, this function isn't available yet）
    platform_TENCENT = {"BGP1": {"zh_CN": "全网通区 男爵领域", "en_US": "Baron Zone"}, "EDU1": {"zh_CN": "教育网专区", "en_US": "CRENET Server"}, "HN1": {"zh_CN": "电信一区 艾欧尼亚", "en_US": "Ionia"}, "HN2": {"zh_CN": "电信二区 祖安", "en_US": "Zaun"}, "HN3": {"zh_CN": "电信三区 诺克萨斯", "en_US": "Noxus 1"}, "HN4": {"zh_CN": "电信四区 班德尔城", "en_US": "Bandle City"}, "HN5": {"zh_CN": "电信五区 皮尔特沃夫", "en_US": "Piltover"}, "HN6": {"zh_CN": "电信六区 战争学院", "en_US": "the Institute of War"}, "HN7": {"zh_CN": "电信七区 巨神峰", "en_US": "Mount Targon"}, "HN8": {"zh_CN": "电信八区 雷瑟守备", "en_US": "Noxus 2"}, "HN9": {"zh_CN": "电信九区 裁决之地", "en_US": "the Proving Grounds"}, "HN10": {"zh_CN": "电信十区 黑色玫瑰", "en_US": "the Black Rose"}, "HN11": {"zh_CN": "电信十一区 暗影岛", "en_US": "Shadow Isles"}, "HN12": {"zh_CN": "电信十二区 钢铁烈阳", "en_US": "the Iron Solari"}, "HN13": {"zh_CN": "电信十三区 水晶之痕", "en_US": "Crystal Scar"}, "HN14": {"zh_CN": "电信十四区 均衡教派", "en_US": "the Kinkou Order"}, "HN15": {"zh_CN": "电信十五区 影流", "en_US": "the Shadow Order"}, "HN16": {"zh_CN": "电信十六区 守望之海", "en_US": "Guardian's Sea"}, "HN17": {"zh_CN": "电信十七区 征服之海", "en_US": "Conqueror's Sea"}, "HN18": {"zh_CN": "电信十八区 卡拉曼达", "en_US": "Kalamanda"}, "HN19": {"zh_CN": "电信十九区 皮城警备", "en_US": "Piltover Wardens"}, "PBE": {"zh_CN": "体验服 试炼之地", "en_US": "Chinese PBE"}, "WT1": {"zh_CN": "网通一区 比尔吉沃特", "en_US": "Bilgewater"}, "WT2": {"zh_CN": "网通二区 德玛西亚", "en_US": "Demacia"}, "WT3": {"zh_CN": "网通三区 弗雷尔卓德", "en_US": "Freljord"}, "WT4": {"zh_CN": "网通四区 无畏先锋", "en_US": "House Crownguard"}, "WT5": {"zh_CN": "网通五区 恕瑞玛", "en_US": "Shurima"}, "WT6": {"zh_CN": "网通六区 扭曲丛林", "en_US": "Twisted Treeline"}, "WT7": {"zh_CN": "网通七区 巨龙之巢", "en_US": "the Dragon Camp"}}
    print("注意：该功能只适用于国服。\nNote: This function is only available for summoners on Chinese servers.")
    print('请选择您想要查询的大区：（输入“0”以退出程序）\nPlease choose a server to look up: (Submit "0" to exit)')
    print("Code\tServer Name")
    warning1 = False #指示某条警告是否已经输出过。下同（Indicates whether a warning has been printed. So are the following）
    for i in platform_TENCENT.keys():
        print(i + "\t" + platform_TENCENT[i]["zh_CN"] + "\t" + platform_TENCENT[i]["en_US"])
    while True:
        server = input()
        if server == "":
            continue
        elif server == "0":
            break
        elif not server.toupper() in platform_TENCENT.keys():
            print("您的输入有误。请输入您想要查询的大区的代号。\nInput ERROR! Please input the code of the server you want to search.")
        else:
            while True:
                if not warning1:
                    print("请输入您想要查询的召唤师的名称。请注意：该名称仅用于输出文件时的信息完善，【玩家通用唯一识别码】请在接下来手动输入。\nPlease input the name of the summoner you want to look up. Please note that this name is only used as the supplement of information when exporting data in the end. Please manually submit the summoner's puuid as the following request shows.")
                else:
                    print("请输入您想要查询的召唤师的名称。\nPlease input the name of the summoner you want to look up.")
                while True:
                    name = input()
                    if name != "":
                        print("您输入的召唤师名称是%s。请按回车确认，或者输入任意键以重新输入。\nYou've input %s as the name of the summoner to be looked up. Please press Enter to confirm, or input any nonempty string to reinput the summoner name." %(name, name))
                        name_confirm = input()
                        if name_confirm == "":
                            break
                        else:
                            global opened
                            opened = False
                            folder = "召唤师信息（Summoner Information）\\" + "国服（TENCENT）" + "\\" + platform_TENCENT[server]["zh_CN"] + "（" + platform_TENCENT[server]["en_US"] + "）" + "\\" + name
                            print("请输入您想要查询的召唤师的名称。\nPlease input the name of the summoner you want to look up.")
                            continue
                print('请输入您想要查询的召唤师的【玩家通用唯一识别码】。输入“0”以返回大区选择。\nPlease enter the [puuid] of the summoner you want to look up. Submit "0" to return to server selection.') #暂时无法通过离线数据库根据召唤师的名称获取【玩家通用唯一识别码】。所以这里要求用户事先知道一名召唤师的【玩家通用唯一识别码】（There's temporarily no way of getting a summoner's puuid according to its name, using offline database. Hence, the user is required to get a summoner's puuid before running this program）
                server_selection = False #由于while True循环较多，需要一个额外的逻辑变量指定是否退出上一层while True循环。这是因为，在指定【玩家通用唯一识别码】为"0"时，通过break语句退出的循环只能是控制puuid的循环，而包含名称和【玩家通用唯一识别码】的一个更大的循环无法由这个break语句退出了（Becasue here're many "while True" loops, an extra boolean variable is needed to determine whether to exit the outer while loop. That's because when we set puuid as "0", we can only exit the while loop that controls puuid, but the "break" statement following 'if puuid == "0"' can't handle the outer loop including name and puuid）
                while True:
                    puuid = input()
                    if puuid == "":
                        continue
                    elif puuid == "0":
                        server_selection = True
                        break
                    else:
                        message = "正在离线查询%s大区的召唤师“%s”（玩家通用唯一识别码：%s）的对局……\n[Offline] searching for matches of the summoner %s (puuid: %s) on %s server ..." %(platform_TENCENT[server]["zh_CN"], name, puuid, name, puuid, platform_TENCENT[server]["en_US"])
                        message_save(message, folder, name, "【参数设置】")
                        #从输入获取要查询的对局序号范围（Get matchID range from input）
                        print("请输入您要查询的对局序号的下限和上限，以空格为分隔符：\nPlease enter the lower and upper bounds of the matchIDs to be searched, split by space:")
                        while True:
                            try:
                                gameIndexBegin, gameIndexEnd = map(int, input().split())
                            except ValueError:
                                print('请输入以空格分隔的两个正整数！如“70000000 80000000”。\nPlease enter two positive integers split by space! For example, "70000000 80000000".')
                                continue
                            else:
                                if gameIndexBegin <= 0 or gameIndexEnd <= 0:
                                    print('请输入以空格分隔的两个正整数！如“70000000 80000000”。\nPlease enter two positive integers split by space! For example, "70000000 80000000".')
                                    continue
                                else:
                                    message = "本次查询的对局序号范围（MatchID range for this query）：[%d, %d]" %(gameIndexBegin, gameIndexEnd)
                                    message_save(message + "\n", folder, name, "【参数设置】")
                                    break
                        #查询前的数据结构准备（Data structure prepared for query）
                        matches_found = []
                        for matchID in range(gameIndexBegin, gameIndexEnd + 1):
                            matchID = str(matchID)
                            game_info = requests.get("https://%s-cloud-acs.lol.qq.com/v1/stats/game/%s/%s" %(server.tolower(), server.toupper(), matchID)).json() #目前该系列地址已不可用（Now this series of URLs are no longer available）
                            error_occurred = False
                            
                            players = []
                            for participant in game_info["participantIdentities"]:
                                if participant["player"]["puuid"] == puuid:
                                    message = "对局%s包含该玩家。已将其加入列表。\nMatch %s contains this summoner and has been added to the matches_found list."
                                    print("【√】" + message)
                                    message_save(message, folder, name, "【找到对局】")
                                    matches_found.append(matchID)
                                    break
                        #保存数据到本地文件（Saved data to a local file）
                        print(matches_found)
                        print('共找到%d场对局！对局序号已保存到“%s”文件夹下的日志文件。\nMatches found: %d. MatchIDs have been saved into the log file in directory "%s": "Matches of Summoners.log".' %(len(matches_found), folder, len(matches_found), folder))
                        message_save("共找到%d场对局。" %(len(matches_found)), "【结果】")
                        result = "%s大区召唤师%s（玩家通用唯一识别码：%s）参与的对局如下：\nMatches that involve summoner %s (puuid: %s) on %s server are as follows:\n%s\n\n" %(platform_TENCENT[server]["zh_CN"], name, puuid, name, puuid, platform_TENCENT[server]["en_US"], str(matches_found))
                        message_save(result, folder, name, "【结果】")
                        break
                if server_selection == True:
                    break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_lockfile(connection)
    await search_summoner_online(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
