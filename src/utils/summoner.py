from lcu_driver.connection import Connection
import os, pandas, sys
from urllib.parse import quote
from typing import Any, IO, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.logger import LogManager
from src.utils.format import getISOTime, optimize_bool_display
from src.core.config.headers import profile_header
from src.core.config.localization import tiers, challengeCategories, challengeCrystalLevels, titleAcquisitionTypes

#-----------------------------------------------------------------------------
# 输出召唤师信息（Output summoner information）
#-----------------------------------------------------------------------------
async def print_summoner_info(connection: Connection, name: str = "current-summoner") -> None:
    info: dict[str, Any] = await get_info(connection, name)
    if info["info_got"]:
        info_body: dict[str, Any] = info["body"]
        print("displayName:    %s" %(info_body["gameName"] + "#" + info_body["tagLine"]))
        print("summonerId:     %s" %(info_body["summonerId"]))
        print("puuid:          %s" %(info_body["puuid"]))
        print("-")

#-----------------------------------------------------------------------------
#  lockfile
#-----------------------------------------------------------------------------
async def update_lockfile(connection: Connection) -> None:
    path: str = os.path.join(connection.installation_path.encode("gb18030").decode("utf-8"), "lockfile")
    if os.path.isfile(path):
        file: IO[Any] = open(path, "w+")
        text: str = "LeagueClient:%d:%d:%s:%s" %(connection.pid, connection.port, connection.auth_key, connection.protocols[0])
        file.write(text)
        file.close()
    return None

async def get_lockfile(connection: Connection) -> Optional[str]:
    path: str = os.path.join(connection.installation_path.encode("gb18030").decode("utf-8"), "lockfile")
    if os.path.isfile(path):
        file: IO[Any] = open(path, "r")
        text: str = file.readline().split(":")
        file.close()
        print(connection.address)
        print(f"riot    {text[3]}")
        return text[3]
    return None

#-----------------------------------------------------------------------------
#  查询召唤师信息（Search for summoner information）
#-----------------------------------------------------------------------------
async def get_info(connection: Connection, name: str, searchType: str | int = "riotId") -> dict[str, Any]:
    #searchTypes = {0: "selfCheck", 1: "riotId", 2: "puuid", 3: "summonerId"}
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    result: dict[str, Any] = {"searchType": "riotId", "endpoint": "/lol-summoner/v2/summoners/puuid/{puuid}", "info_got": False, "network_error": False, "body": {}, "message": "", "selfInfo": False}
    if "errorCode" in current_info:
        result["searchType"] = "puuid"
        result["endpoint"] = "/lol-summoner/v1/current-summoner"
        result["network_error"] = True
        result["body"] = current_info
        if current_info["httpStatus"] == 404 and current_info["message"] == "You are not logged in.":
            result["message"] = "您还未登录。\nYou're not logged in."
        else:
            result["message"] = "网络异常。\nNetwork Error."
        result["selfInfo"] = True
    else:
        try:
            summonerId: int = int(name)
        except ValueError:
            if name == "current-summoner":
                result = {"searchType": "selfCheck", "endpoint": "/lol-summoner/v1/current-summoner", "info_got": True, "network_error": False, "body": current_info, "message": "", "selfInfo": True}
            elif name.count("-") == 4 and len(name.replace(" ", "")) > 22: #拳头规定的玩家名称不超过16个字符，名称编号不超过5个字符（Riot game name can't exceed 16 characters. The tagline can't exceed 5 characters）
                result["searchType"] = "puuid"
                result["endpoint"] = "/lol-summoner/v2/summoners/puuid/{puuid}"
                info: dict[str, Any] = await (await connection.request("GET", f"/lol-summoner/v2/summoners/puuid/{name}")).json()
                result["body"] = info
                if "errorCode" in info:
                    if info["httpStatus"] == 400:
                        if "in UUID format" in info["message"]:
                            result["message"] = "您输入的玩家通用唯一识别码格式有误！请重新输入！\nPUUID wasn't in UUID format! Please try again!"
                        elif "Error response for POST /player-account/lookup/v1/namesets-for-puuids: Failed to connect to 127.0.0.1 port" in info["message"]:
                            result["message"] = "连接超时！请检查您的登录状态。\nConnection timed out! Please check your login status."
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
                    result["message"] = '召唤师名称已变更为拳头ID。请以“{玩家名称}#{名称编号}”的格式输入。\nSummoner name has been replaced with Riot ID. Please input the name in this format: "{gameName}#{tagLine}", e.g. "%s#%s".' %(current_info["gameName"], current_info["tagLine"])
                elif name.count("#") > 1:
                    result["message"] = "该玩家名字包含了无效字符。\nThis player name contains invalid characters."
                else:
                    gameName, tagLine = name.split("#")
                    if len(gameName) == 0:
                        result["message"] = "缺少玩家名称。\nGame name is missing."
                    elif len(tagLine) == 0:
                        result["message"] = "缺少名称编号。\nTagline is missing."
                    elif len(gameName) < 3:
                        result["message"] = "召唤师名称过短。\nRiot ID is too short."
                    elif len(gameName.replace(" ", "")) > 16:
                        result["message"] = "召唤师名称过长。\nRiot ID is too long."
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
            info: dict[str, Any] = await (await connection.request("GET", f"/lol-summoner/v1/summoners/{summonerId}")).json()
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

async def get_infos(connection: Connection, puuids: Optional[list[str]] = None, batch_size: int = 1500, retry: int = 5) -> dict[str, dict[str, Any]]: #下面的接口非常容易报错。非—常—难—受！（The following endpoint is likely to return an error. Very frustrating）
    '''
    通过POST /lol-summoner/v2/summoners/puuid接口批量获取多名召唤师的信息。对于天梯等内部数据的信息呈现非常有帮助。<br>Get multiple summoners' information through `POST /lol-summoner/v2/summoners/puuid` endpoint in batches. Especially helpful for internal data transformation like ranked ladders.
    
    :type connection: lcu_driver.connection.Connection
    :param puuids: 由玩家通用唯一识别码组成的列表。<br>A list of player universally unique identifiers (PUUIDs).
    :type puuids: list[str]
    :param batch_size: 每批召唤师的数量。默认为1500个。这个数量不能过多，否则上述接口会返回错误信息。<br>The number of each batch of summoners to query. 1500 by default. This number shouldn't be set too high, or the above endpoint will return an error message.
    :type batch_size: int
    :param retry: 每批召唤师在获取失败后的重新尝试次数。默认为5次。<br>The times of retries after an error occurs in the first fetch of each batch of summoners' information. 5 by default.
    :type retry: int
    :return: 召唤师信息索引字典。键是玩家通用唯一识别码，值是对应的召唤师信息。<br>A summoner information index dictionary, whose keys are puuids and values are corresponding summoner information.
    :rtype: dict[str, dict[str, Any]]
    '''
    if puuids == None:
        puuids = []
    puuid_search_batches: list[list[str]] = []
    for i in range(len(puuids) // 1500):
        puuid_search_batches.append(puuids[batch_size * i:batch_size * (i + 1)])
    puuid_search_batches.append(puuids[len(puuids) // 1500 * 1500:])
    summoners: dict[str, dict[str, Any]] = {}
    for i in range(len(puuid_search_batches)):
        batch: list[str] = puuid_search_batches[i]
        print("正在查询第%d/%d批共%d名召唤师的信息……\nSearching for information of %d summoners in Batch %d / %d ..." %(i + 1, len(puuid_search_batches), len(batch), len(batch), i + 1, len(puuid_search_batches)))
        summoner_infos_recapture: int = 0
        while True:
            summoner_info_bodies: list[dict[str, Any]] | dict[str, Any] = await (await connection.request("POST", "/lol-summoner/v2/summoners/puuid", data = batch)).json()
            if summoner_infos_recapture > retry:
                break
            if isinstance(summoner_info_bodies, dict) and "errorCode" in summoner_info_bodies and summoner_info_bodies["httpStatus"] == 400 and summoner_info_bodies["message"] == "Error response for POST /player-account/lookup/v1/namesets-for-puuids: ":
                print("召唤师信息获取失败。正在第%d次尝试重新获取这些玩家的信息。\nSummoner info capture failure! Recapturing these players' information ... Times tried: %d" %(summoner_infos_recapture, summoner_infos_recapture))
            else:
                break
            summoner_infos_recapture += 1
        if isinstance(summoner_info_bodies, dict) and "errorCode" in summoner_info_bodies:
            print(summoner_info_bodies)
            if summoner_info_bodies["errorCode"] == "BAD_REQUEST_HEADERS" and summoner_info_bodies["httpStatus"] == 413 and summoner_info_bodies["message"] == "Content length is too large":
                print("请求内容过长。请尝试每批查询召唤师的数量。\nRequest content too long. Please try reducing the number of summoners of each batch.")
            elif summoner_info_bodies["httpStatus"] == 400 and summoner_info_bodies["message"] == '{"httpStatus":400,"errorCode":"BAD_REQUEST","message":"PUUID was not in UUID format","implementationDetails":"filtered"}':
                print("您输入的玩家通用唯一识别码格式有误！请重新输入！\nPUUID wasn't in UUID format! Please try again!")
            elif summoner_info_bodies["httpStatus"] == 400 and summoner_info_bodies["message"] == "Error response for POST /player-account/lookup/v1/namesets-for-puuids: ":
                print("查询对应的账号信息时出现了一个问题。\nAn error occurred while looking up a player's account.")
        else:
            for info_body in summoner_info_bodies:
                summoners[info_body["puuid"]] = info_body
    return summoners

def get_info_name(info: Any, mode: int = 1, verbose: bool = True) -> str:
    if isinstance(info, dict):
        #初始化变量（Initialize variables）
        displayName_exist: bool = False
        gameName_exist: bool = False
        tagLine_exist: bool = False
        puuid_exist: bool = False
        displayName: str = ""
        gameName: str = ""
        tagLine: str = ""
        puuid: str = ""
        #显示名（Display name）
        if "displayName" in info:
            displayName = info["displayName"]
            displayName_exist = True
        elif "summonerName" in info:
            if "#" in info["summonerName"]:
                return info["summonerName"]
            else:
                displayName = info["summonerName"]
                displayName_exist = True
        #玩家名称（Game name）
        for key in ["gameName", "riotIdGameName", "riotIdName"]:
            if key in info:
                gameName = info[key]
                gameName_exist = True
                break
        #名称编号（Tagline）
        for key in ["tagLine", "gameTag", "riotIdTagline", "riotIdTagLine"]:
            if key in info:
                tagLine = info[key]
                tagLine_exist = True
                break
        #玩家通用唯一识别码（Puuid）
        if "puuid" in info:
            puuid = info["puuid"]
            puuid_exist = True
        #分类讨论（Discuss）
        if displayName_exist and gameName_exist and tagLine_exist and puuid_exist:
            if displayName_exist or gameName_exist:
                if gameName and tagLine:
                    name = gameName + "#" + tagLine
                elif not tagLine and gameName:
                    name = gameName
                else:
                    name = displayName
            else: #新玩家属于这种类型（This case matches new players）
                if mode == 2: #仅用于设置召唤师数据保存路径（Designed to set the summoner name directory）
                    name = "0. 新玩家/" + puuid
                elif mode == 3: #仅用于设置召唤师数据保存路径（Designed to set the summoner name directory）
                    name = "0. New Player/" + puuid
                else:
                    name = puuid
        elif gameName_exist and tagLine_exist and puuid_exist: #/lol-end-of-game/v1/eog-stats-block
            if gameName and tagLine:
                name = gameName + "#" + tagLine
            else:
                if mode == 2:
                    name = "0. 新玩家/" + puuid
                elif mode == 3:
                    name = "0. New Player/" + puuid
                else:
                    name = puuid
        elif gameName_exist and tagLine_exist and bool(gameName) and bool(tagLine):
            name = gameName + "#" + tagLine
        else:
            if verbose:
                print("您的召唤师信息格式有误！\nERROR format of summoner information!")
            name = ""
    else:
        if verbose:
            print("您的召唤师信息格式有误！\nERROR format of summoner information!")
        name = ""
    return name

async def sort_summoner_info(connection: Connection, puuids: list[str], summonerIcons: dict[int, dict[str, Any]], LoLChampions: dict[int, dict[str, Any]], regaliaBanners: dict[str, dict[str, Any]], unmapped_keys: Optional[dict[str, set[Any]]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame:
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    if unmapped_keys == None:
        unmapped_keys: dict[str, set[Any]] = {"summonerIcon": set(), "regaliaBanner": set(), "LoLChampion": set()}
    info_header_keys: list[str] = list(profile_header.keys())
    info_data: dict[str, Any] = {key: [] for key in info_header_keys}
    logPrint("召唤师信息整理进度（Summoner information organization process）：")
    for i in range(len(puuids)):
        puuid: str = puuids[i]
        logPrint("[%d/%d]%s" %(i + 1, len(puuids), puuid))
        info_recapture: int = 0
        info: dict[str, Any] = await get_info(connection, puuid)
        while not info["info_got"] and info["body"]["httpStatus"] != 404 and info_recapture < 3:
            logPrint(info["body"], verbose = verbose)
            info_recapture += 1
            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！正在第%d次尝试重新获取该玩家信息……\nInformation of player (puuid: %s) capture failed! Recapturing this player's information ... Times tried: %d." %(puuid, info_recapture, puuid, info_recapture), verbose = verbose)
            info = await get_info(connection, puuid)
        if info["info_got"]:
            info_body: dict[str, Any] = info["body"]
            displayName: str = get_info_name(info_body)
            #准备局部数据资源（Prepare local data resources）
            ##排位（Ranked）
            ranked: dict[str, Any] = await (await connection.request("GET", f"/lol-ranked/v1/ranked-stats/{puuid}")).json()
            if "errorCode" in ranked: #很久以前，国服体验服的排位数据API未知。现在已经与正式服统一（Long ago, API of ranked stats on Chinese PBE was unknown. Now it accords with Live servers）
                logPrint(ranked, verbose = verbose)
                logPrint("玩家%s的排位信息获取失败。\nRanked information of Player %s capture failed." %(displayName, displayName), verbose = verbose)
            ##冠军杯赛旗帜（Tournament flag）
            banner: dict[str, int | str] = await (await connection.request("GET", f"/lol-banners/v1/players/{puuid}/flags/equipped")).json()
            if isinstance(banner, dict) and "errorCode" in banner:
                logPrint(banner, verbose = verbose)
                if banner == {"errorCode": "RPC_ERROR", "httpStatus": 404, "implementationDetails": {}, "message": f"{puuid} has no valid banner flags."}:
                    logPrint("玩家%s未装备冠军杯赛旗帜。\nPlayer %s doesn't equip any tournament flag." %(displayName, displayName), verbose = verbose)
                else:
                    logPrint("玩家%s的冠军杯赛旗帜获取失败。\nTournament flag information of Player %s capture failed." %(displayName, displayName), verbose = verbose)
            ##成就（Challenge）
            challenge: dict[str, Any] = await (await connection.request("GET", f"/lol-challenges/v1/summary-player-data/player/{puuid}")).json()
            if "errorCode" in challenge:
                logPrint(challenge, verbose = verbose)
                logPrint("玩家%s的成就信息获取失败。\nChallenge information of Player %s capture failed." %(displayName, displayName), verbose = verbose)
            ##永恒星碑（Statstone）
            topStatstones: list[dict[str, Any]] = await (await connection.request("GET", f"/lol-statstones/v1/profile-summary/{puuid}")).json()
            if isinstance(topStatstones, dict) and "errorCode" in topStatstones:
                logPrint(topStatstones, verbose = verbose)
                logPrint("玩家%s的最高永恒星碑信息获取失败。\nTop statstone information of Player %s capture failed." %(displayName, displayName), verbose = verbose)
            #整理数据（Organize data）
            for i in range(len(info_header_keys)):
                key: str = info_header_keys[i]
                if i <= 21: #召唤师信息（Summoner information）
                    if i <= 16:
                        if i >= 15: #召唤师图标相关键（Profile icon related keys）
                            profileIconId: int = info_body["profileIconId"]
                            if profileIconId in summonerIcons:
                                to_append: Any = summonerIcons[profileIconId].get(key.split("_")[1], "") #部分召唤师图标没有名称键（Some summoner icons don't have a "name" key）
                            else:
                                if not profileIconId in unmapped_keys["summonerIcon"]:
                                    unmapped_keys["summonerIcon"].add(profileIconId)
                                    logPrint("玩家%s的召唤师图标（%d）信息获取失败。\nSummoner icon information (%d) of Player %s capture failed." %(displayName, profileIconId, profileIconId, displayName), verbose = verbose)
                                to_append = ""
                        else:
                            to_append = info_body[key]
                    else: #重随点子键（`rerollPoints`' subkeys）
                        to_append = info_body["rerollPoints"][key]
                elif i <= 28: #段位（Rank）
                    if "errorCode" in ranked: #很久以前，国服体验服的排位数据API未知。现在已经与正式服统一（Long ago, API of ranked stats on Chinese PBE was unknown. Now it accords with Live servers）
                        to_append = ""
                    else:
                        if key in ranked:
                            if i in {24, 25, 27}:
                                to_append = tiers[ranked[key]]
                            else:
                                to_append = ranked[key]
                        else:
                            to_append = ""
                elif i <= 33: #冠军杯赛旗帜（Tournament flag）
                    if isinstance(banner, dict) and "errorCode" in banner:
                        to_append = ""
                    else:
                        to_append = banner[key.split()[1]]
                elif i <= 90: #成就和头衔（Challenge and title）
                    if "errorCode" in challenge:
                        to_append = ""
                    else:
                        if i == 36 or i == 37: #整数字符串（Integer string）
                            to_append = "" if challenge[key.split()[1]] == "" else int(challenge[key.split()[1]])
                        elif i == 39: #总成就等级（`challenge overallChallengeLevel`）
                            to_append = challengeCrystalLevels[challenge["overallChallengeLevel"]]
                        elif i == 44: #天梯更新时间（`challenge apexLadderUpdateDate`）
                            to_append = getISOTime(challenge["apexLadderUpdateTime"] / 1000)
                        elif i == 45 or i == 46: #身份旗帜子键（Info banner's subkeys）
                            bannerId: str = challenge["bannerId"]
                            if bannerId in regaliaBanners:
                                to_append = regaliaBanners[bannerId]["items"][0][key.split("_")[1]]
                            else:
                                if not bannerId in unmapped_keys["regaliaBanner"]:
                                    unmapped_keys["regaliaBanner"].add(bannerId)
                                    logPrint("玩家%s的身份旗帜（%s）信息获取失败。\nInfo banner information (%s) of Player %s capture failed." %(displayName, bannerId, bannerId, displayName), verbose = verbose)
                                to_append = ""
                        elif i == 47: #排位徽章名称（`challenge crestName`）
                            to_append = "" #目前尚不明确排位徽章的本地化内容（Localized content of crests haven't figured out yet）
                        elif i >= 48 and i <= 72: #分类进度子键（`categoryProgress`' subkeys）
                            challengeCategoryIndex: int = (i - 48) // 5
                            subIndex: int = (i - 48) % 5
                            subkey: str = key.split()[2]
                            if challengeCategoryIndex < len(challenge["categoryProgress"]):
                                if subIndex == 0: #名称（`category`）
                                    to_append = challengeCategories[challenge["categoryProgress"][challengeCategoryIndex]["category"]]
                                elif subIndex == 2: #等级（`level`）
                                    to_append = challengeCrystalLevels[challenge["categoryProgress"][challengeCategoryIndex]["level"]]
                                else:
                                    to_append = challenge["categoryProgress"][challengeCategoryIndex][subkey]
                            else:
                                to_append = ""
                        elif i >= 73 and i <= 84: #最佳成就子键（`topChallenges`' subkeys）
                            topChallengeIndex: int = (i - 73) // 4
                            subIndex: int = (i - 73) % 4
                            subkey = key.split()[1]
                            if topChallengeIndex < len(challenge["topChallenges"]):
                                if subIndex == 2: #当前等级（`currentLevel`）
                                    to_append = challengeCrystalLevels[challenge["topChallenges"][topChallengeIndex]["currentLevel"]]
                                else:
                                    to_append = challenge["topChallenges"][topChallengeIndex][subkey]
                            else:
                                to_append = ""
                        elif i >= 85 and i <= 87: #头衔子键（`title`'s subkeys）
                            if i == 87: #头衔等级（`challenge title titleAcquisitionType`）
                                to_append = titleAcquisitionTypes[challenge["title"]["titleAcquisitionType"]]
                            else:
                                to_append = challenge["title"][key.split()[2]]
                        elif i >= 88: #头衔成就数据子键（`challengeTitleData`'s subkeys）
                            if challenge["title"]["challengeTitleData"] == None:
                                to_append = ""
                            else:
                                if i == 90: #头衔成就等级（`challenge title challengeTitleData level`）
                                    to_append = challengeCrystalLevels[challenge["title"]["challengeTitleData"]["level"]]
                                else:
                                    to_append = challenge["title"]["challengeTitleData"][key.split()[3]]
                                if to_append == None:
                                    to_append = ""
                        else:
                            to_append = challenge[key.split()[1]]
                else: #最高永恒星碑相关键（Top statstone related keys）
                    if isinstance(topStatstones, dict) and "errorCode" in topStatstones:
                        to_append = ""
                    else:
                        topStatstoneIndex: int = (i - 91) // 8
                        subIndex: int = (i - 91) % 8
                        subkey: str = key.split()[1]
                        if topStatstoneIndex < len(topStatstones):
                            if subIndex >= 5: #英雄子键（Champion's subkeys）
                                championId: int = topStatstones[topStatstoneIndex]["championId"]
                                if championId in LoLChampions:
                                    to_append = LoLChampions[championId][key.split("_")[1]]
                                else:
                                    if not championId in unmapped_keys["LoLChampion"]:
                                        unmapped_keys["LoLChampion"].add(championId)
                                        logPrint("玩家%s的第%d永恒星碑的英雄信息（%d）获取失败。\nStatstone No. %d champion information (%d) of Player %s capture failed." %(displayName, topStatstoneIndex + 1, championId, topStatstoneIndex + 1, championId, displayName), verbose = verbose)
                                    to_append = ""
                            else:
                                to_append = topStatstones[topStatstoneIndex][subkey]
                        else:
                            to_append = ""
                info_data[key].append(to_append)
        else:
            logPrint(info["body"], verbose = verbose)
            logPrint("玩家信息（玩家通用唯一识别码：%s）获取失败！\nInformation of player (puuid: %s) capture failed!" %(puuid, puuid), verbose = verbose)
    info_statistics_output_order: list[int] = [0, 1, 3, 2, 11, 12, 4, 9, 8, 6, 7, 15, 16, 10, 13, 14, 5, 19, 18, 17, 20, 21, 24, 22, 25, 26, 27, 28, 23, 30, 33, 32, 31, 29, 38, 34, 44, 35, 36, 45, 46, 37, 47, 42, 43, 39, 40, 41, 85, 86, 87, 88, 89, 90, 48, 50, 49, 51, 52, 53, 55, 54, 56, 57, 58, 60, 59, 61, 62, 63, 65, 64, 66, 67, 68, 70, 69, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 94, 91, 95, 93, 92, 96, 97, 98, 102, 99, 103, 101, 100, 104, 105, 106, 110, 107, 111, 109, 108, 112, 113, 114]
    info_data_organized: dict[str, list[Any]] = {info_header_keys[i]: info_data[info_header_keys[i]] for i in info_statistics_output_order}
    info_df: pandas.DataFrame = pandas.DataFrame(info_data_organized)
    optimize_bool_display(info_df)
    info_df = pandas.concat([pandas.DataFrame([profile_header])[info_df.columns], info_df], ignore_index = True)
    return info_df
