from lcu_driver.connection import Connection
import copy, os, pandas, time, sys, uuid
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.utils.logger import LogManager
from src.utils.format import optimize_bool_display, pyobj2json
from src.core.config.localization import damageTypes, attackTypes
from src.core.config.headers import LoLChampion_ddragon_header, LoLChampion_inventory_header, LoLChampion_plugin_header, champion_summary_header

async def test_bot(connection: Connection, LoLChampions: dict[int, dict[str, Any]], log: Optional[LogManager] = None, verbose: bool = True) -> tuple[dict[int, dict[str, Any]], int]:
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    LoLChampions_subset: dict[int, dict[str, Any]] = {}
    logPrint("正在统计具有电脑模型的英雄……请勿退出房间！\nCounting botEnabled champions ... Please don't exit the lobby!")
    custom: dict[str, Any] = {
        "queueId": 3140,
        "isCustom": True,
        "customGameLobby": {
            "lobbyName": "可用电脑英雄测试（程序结束前请勿退出）",
            "lobbyPassword": "",
            "configuration": {
                "mapId": 11,
                "gameMode": "PRACTICETOOL",
                "gameTypeConfig": {
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
    response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v2/lobby", data = custom)).json()
    if isinstance(response, dict) and "errorCode" in response:
        logPrint(response, verbose = verbose)
        logPrint("测试房间创建失败。请检查您的游戏状态。\nTest lobby creation failed. Please check your gameflow phase.")
    else:
        logPrint("championId\tname\ttitle\talias", verbose = verbose)
        count: int = 0
        for championId in LoLChampions:
            botUuid: str = str(uuid.uuid4())
            bot: dict[str, str] = {"championId": championId, "botDifficulty": "RSINTERMEDIATE", "teamId": "200", "position": "TOP", "botUuid": botUuid}
            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/bots", data = bot)).json()
            if response == None: #这里认为当返回内容为空时，电脑玩家被添加（Here the principle is, once the response body is empty, the bot player is definitely added）
                # start: float = time.time()
                LoLChampions_subset[championId] = LoLChampions[championId]
                logPrint("%d\t%s\t%s\t%s" %(championId, LoLChampions[championId]["name"], LoLChampions[championId]["title"], LoLChampions[championId]["alias"]), verbose = verbose)
                if championId != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
                    count += 1
                #接下来反复获取房间信息，直到从房间信息中获取到添加的电脑玩家信息（Next, repeatedly get the lobby information, until the added bot information can be found）
                lobby_information: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                while not championId in list(map(lambda x: x["botChampionId"], lobby_information["gameConfig"]["customTeam200"])):
                    if lobby_information["multiUserChatId"].endswith("-team-select"):
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-lobby/v1/lobby/custom/switch-teams")).json() #通过切换队伍来刷新房间信息（Refresh the lobby information by switching team）
                    else:
                        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-lobby/v2/lobby/team/TEAM1")).json()
                    lobby_information = await (await connection.request("GET", "/lol-lobby/v2/lobby")).json()
                # end: float = time.time()
                # cost: float = end - start
                # print("从添加电脑玩家到房间信息刷新所花费的时间【Time interval (seconds) between a bot is added and lobby information is refreshed】：%f" %(cost))
                botId_uuid_dict: dict[str, str] = {bot["botUuid"]: bot["botId"] for bot in lobby_information["gameConfig"]["customTeam200"]}
                for bot in lobby_information["gameConfig"]["customTeam200"]: #从25.16版本开始，电脑玩家通用唯一识别码不再能由用户决定。因此，过往通过电脑玩家通用唯一识别码来判断电脑是否被添加的办法失效了（Since Patch 25.16, botUuid can never be decided by the user. Therefore, the original way to judge by botUuid whether a bot player is added no longer works）
                    if bot["botChampionId"] == championId:
                        botUuid: str = bot["botUuid"]
                        break
                else:
                    botUuid = lobby_information["gameConfig"]["customTeam200"][0]["botUuid"] #保护机制，防止下面在引用botUuid时出现问题（A protection from an error occurring when the program refers to `botUuid` below）
                response: Optional[dict[str, Any]] = await (await connection.request("DELETE", "/lol-lobby/v1/lobby/custom/bots/%s/%s/200" %(botId_uuid_dict[botUuid], botUuid))).json()
        logPrint("\n统计完毕，共%d名英雄。\nCount finished! There're %d champions in total." %(count, count), verbose = verbose)
    return (LoLChampions_subset, count)

def sort_ddragon_champions(LoLChampions: dict[int, dict[str, Any]], log: Optional[LogManager] = None, verbose: bool = False) -> tuple[pandas.DataFrame, int]: #这里的LoLChampions参数的键是英雄序号，值是英雄数据（Keys of `LoLChampions` parameter are championIds, and values are champion data）
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    LoLChampion_header: dict[str, str] = LoLChampion_ddragon_header
    LoLChampion_header_keys: list[str] = list(LoLChampion_header.keys())
    LoLChampion_data: dict[str, list[Any]] = {key: [] for key in LoLChampion_header_keys}
    logPrint("championId\tname\ttitle\talias", verbose = verbose)
    count: int = 0
    for i in sorted(LoLChampions.keys()):
        champion: dict[str, Any] = LoLChampions[i]
        logPrint("%s\t%s\t%s\t%s" %(champion["key"], champion["name"], champion["title"], champion["id"]), verbose = verbose)
        if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
            count += 1
        for j in range(len(LoLChampion_header_keys)):
            key: str = LoLChampion_header_keys[j]
            if j <= 10:
                if j == 1: #DataDragon数据库中存储的英雄序号为字符串（ChampionIds stored in DataDragon database are of string type）
                    to_append: Any = int(champion[key])
                else:
                    to_append = champion[key]
            elif j <= 17: #英雄图像相关键（Champion image related keys）
                to_append = champion["image"][key.split(": ")[1]]
            elif j <= 23: #标签（Tags）
                if key.split(": ")[1] in champion["tags"]:
                    to_append = "√"
                else:
                    to_append = ""
            elif j <= 27: #英雄信息相关键（Champion info related keys）
                to_append = champion["info"][key.split(": ")[1]]
            elif j <= 47: #英雄属性相关键（Stats related keys）
                to_append = champion["stats"][key]
            elif j <= 63: #英雄属性成长相关键（Stats growth related keys）
                level, subkey = int(key[3:5]), key[5:]
                result: str = champion["stats"][subkey] + (level - 1) * champion["stats"][subkey + "perlevel"] * (0.01 if subkey == "attackspeed" else 1) #攻击速度成长是百分比（`attackspeedperlevel` is a percentage）
                to_append = result
            else: #技能相关键（Spell related keys）
                spell: dict[str, Any] = champion["spells"][int(key[5:6]) - 1] if j <= 171 else champion["passive"]
                subkey_list: list[str] = key.split(": ")[1:]
                value: Any = spell
                for subkey in subkey_list:
                    if j <= 171 and spell["id"] == "JayceStanceHtG" and subkey == "leveltip": #杰斯的R技能没有升级提示（Jayce's R doesn't have leveltips）
                        value = ""
                        break
                    value = value[subkey]
                to_append = value
            LoLChampion_data[key].append(to_append)
    LoLChampion_statistics_output_order: list[int] = [1, 2, 3, 0, 6, 9, 24, 25, 26, 27, 18, 19, 20, 21, 22, 23, 28, 29, 30, 31, 44, 45, 33, 34, 35, 36, 47, 46, 42, 43, 32, 38, 39, 40, 41, 37, 172, 65, 92, 119, 146]
    #LoLChampion_statistics_output_order: list[int] = [1, 2, 3, 0, 6, 9, 24, 25, 26, 27, 18, 19, 20, 21, 22, 23, 28, 29, 48, 49, 30, 31, 50, 51, 44, 45, 52, 53, 33, 34, 54, 55, 35, 36, 56, 57, 47, 46, 58, 59, 42, 43, 32, 38, 39, 60, 61, 40, 41, 62, 63, 37] #带成长数值（With leveling up stats）
    LoLChampion_data_organized: dict[str, list[Any]] = {LoLChampion_header_keys[i]: LoLChampion_data[LoLChampion_header_keys[i]] for i in LoLChampion_statistics_output_order}
    LoLChampion_df: pandas.DataFrame = pandas.DataFrame(data = LoLChampion_data_organized)
    LoLChampion_df = pandas.concat([pandas.DataFrame([LoLChampion_header])[LoLChampion_df.columns], LoLChampion_df], ignore_index = True)
    return (LoLChampion_df, count)

async def sort_inventory_champions(connection: Connection, LoLChampions: dict[int, dict[str, Any]], log: Optional[LogManager] = None, verbose: bool = False) -> tuple[pandas.DataFrame, int]:
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    LoLChampion_header: dict[str, str] = LoLChampion_inventory_header
    LoLChampion_header_keys: list[str] = list(LoLChampion_header.keys())
    LoLChampion_data: dict[str, list[Any]] = {key: [] for key in LoLChampion_header_keys}
    LoLChampion_data_json: dict[str, list[Any]] = copy.deepcopy(LoLChampion_data)
    recommended_position_for_champion: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    logPrint("championId\tname\ttitle\talias", verbose = verbose)
    count: int = 0
    for i in sorted(LoLChampions.keys()):
        champion: dict[str, Any] = LoLChampions[i]
        logPrint("%d\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]), verbose = verbose)
        if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
            count += 1
        for j in range(len(LoLChampion_header_keys)):
            key = LoLChampion_header_keys[j]
            if j <= 17:
                if j == 7: #禁用队列（`disabledQueues`）
                    to_append = champion["disabledQueues"]
                    if to_append == []:
                        to_append = ""
                elif j == 17: #购买日期（`purchased`）
                    if champion["purchased"] == 0:
                        to_append: Any = ""
                    else:
                        try:
                            to_append = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion["purchased"] // 1000))
                        except OSError: #出现了购买时间戳为18446744073709550616的英雄（There's a champion with the purchased timestamp 18446744073709550616）
                            to_append = ""
                else:
                    to_append = champion[key]
            elif j <= 26: #拥有权子键（`ownership`'s subkeys）
                if j <= 20:
                    to_append = champion["ownership"][key.split(": ")[1]]
                else:
                    if j == 25 or j == 26:
                        if champion["ownership"]["rental"][key.split(": ")[2].replace("Time", "Date")] == 0:
                            to_append = ""
                        else:
                            try:
                                to_append = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(champion["ownership"]["rental"][key.split(": ")[2].replace("Time", "Date")] // 1000))
                            except OSError: #出现了租借时间戳为18446744073709550616的英雄（There's a champion with the rented timestamp 18446744073709550616）
                                to_append = ""
                    else:
                        to_append = champion["ownership"]["rental"][key.split(": ")[2]]
            elif j <= 32: #角色定位相关键（Role related keys）
                to_append = key.split(": ")[1] in champion["roles"]
            elif j <= 35: #战略信息子键（`tacticalInfo`'s subkeys）
                if j == 33: #战略信息：伤害【表明英雄的伤害类型的倾向（物理伤害、魔法伤害或者混合伤害）】（`tacticalInfo: damageType`）
                    to_append = damageTypes[champion["tacticalInfo"][key.split(": ")[1]]]
                else:
                    to_append = champion["tacticalInfo"][key.split(": ")[1]]
            elif j <= 37: #被动技能子键（`passive`'s subkeys）
                to_append = champion["passive"][key.split(": ")[1]]
            elif j <= 45: #技能相关键（Spell related keys）
                spell_index: int = int(key[5:6]) - 1
                if spell_index < len(champion["spells"]):
                    to_append = champion["spells"][spell_index][key.split(": ")[1]]
                else:
                    to_append = ""
            else:
                if champion["id"] == -1:
                    to_append = False
                elif key.split(": ")[1] in recommended_position_for_champion[str(champion["id"])]["recommendedPositions"]:
                    to_append = True
                else:
                    to_append = False
            LoLChampion_data[key].append(to_append)
            LoLChampion_data_json[key].append(pyobj2json(to_append))
    LoLChampion_statistics_output_order: list[int] = [9, 11, 16, 1, 10, 5, 27, 28, 29, 30, 31, 32, 46, 47, 48, 49, 50, 33, 35, 34, 19, 17, 18, 20, 8, 23, 26, 25, 24, 13, 7, 14, 3, 4, 15, 6, 2, 37, 39, 41, 43, 45]
    LoLChampion_data_organized: dict[str, list[Any]] = {LoLChampion_header_keys[i]: LoLChampion_data[LoLChampion_header_keys[i]] for i in LoLChampion_statistics_output_order}
    LoLChampion_df: pandas.DataFrame = pandas.DataFrame(data = LoLChampion_data_organized)
    # logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...", verbose = verbose)
    optimize_bool_display(LoLChampion_df)
    # logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!", verbose = verbose)
    LoLChampion_df = pandas.concat([pandas.DataFrame([LoLChampion_header])[LoLChampion_df.columns], LoLChampion_df], ignore_index = True)
    return (LoLChampion_df, count)

def sort_plugin_champions(LoLChampions: dict[int, dict[str, Any]], log: Optional[LogManager] = None, verbose: bool = False) -> tuple[pandas.DataFrame, int]:
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    LoLChampion_header: dict[str, str] = LoLChampion_plugin_header
    LoLChampion_header_keys: list[str] = list(LoLChampion_header.keys())
    LoLChampion_data: dict[str, list[Any]] = {key: [] for key in LoLChampion_header_keys}
    logPrint("championId\tname\ttitle\talias", verbose = verbose)
    count: int = 0
    for i in sorted(LoLChampions.keys()):
        champion: dict[str, Any] = LoLChampions[i]
        logPrint("%s\t%s\t%s\t%s" %(champion["id"], champion["name"], champion["title"], champion["alias"]), verbose = verbose)
        if champion["id"] != -1: #API中存在一个id为-1的英雄。该英雄不计入英雄个数（There's a champion with the id -1 in API. It won't be counted)
            count += 1
        for j in range(len(LoLChampion_header_keys)):
            key: str = LoLChampion_header_keys[j]
            if j <= 10:
                to_append: Any = champion[key]
            elif j <= 14: #战略信息子键（`tacticalInfo`'s subkeys）
                if j == 13: #战略信息：伤害（`tacticalInfo: damageType`）
                    to_append = damageTypes[champion["tacticalInfo"][key.split(": ")[1]]]
                elif j == 14: #战略信息：攻击方式（`tacticalInfo: attackType`）
                    to_append = attackTypes[champion["tacticalInfo"][key.split(": ")[1]]]
                else:
                    to_append = champion["tacticalInfo"][key.split(": ")[1]]
            elif j <= 19: #玩法雷达图子键（`playStyleInfo`'s subkeys）
                to_append = champion["playstyleInfo"][key.split(": ")[1]]
            elif j <= 21: #英雄标签信息子键（`championTagInfo`'s subkeys）
                to_append = champion["championTagInfo"][key.split(": ")[1]]
            elif j <= 27: #角色定位子键（`role`'s subkeys）
                if key.split(": ")[1] in champion["roles"]:
                    to_append = "√"
                else:
                    to_append = ""
            elif j <= 32: #被动技能子键（`passive`'s subkeys）
                to_append = champion["passive"][key.split(": ")[1]]
            else: #技能相关键（Spell related keys）
                spell_index: int = int(key[5:6]) - 1
                if spell_index < len(champion["spells"]):
                    spell: dict[str, Any] = champion["spells"][spell_index]
                    subkey_list: list[str] = key.split(": ")[1:]
                    value: Any = spell
                    for subkey in subkey_list:
                        value = value[subkey]
                    to_append = value
                else:
                    to_append = ""
            LoLChampion_data[key].append(to_append)
    LoLChampion_statistics_output_order: list[int] = [0, 1, 3, 2, 5, 22, 23, 24, 25, 26, 27, 13, 11, 12, 14, 20, 21, 15, 16, 17, 18, 19, 4, 6, 7, 8, 9, 28, 34, 61, 88, 115]
    LoLChampion_data_organized: dict[str, list[Any]] = {LoLChampion_header_keys[i]: LoLChampion_data[LoLChampion_header_keys[i]] for i in LoLChampion_statistics_output_order}
    LoLChampion_df: pandas.DataFrame = pandas.DataFrame(data = LoLChampion_data_organized)
    # logPrint("正在优化逻辑值显示……\nOptimizing the display of boolean values ...", verbose = verbose)
    optimize_bool_display(LoLChampion_df)
    # logPrint("逻辑值显示优化完成！\nBoolean value display optimization finished!", verbose = verbose)
    LoLChampion_df = pandas.concat([pandas.DataFrame([LoLChampion_header])[LoLChampion_df.columns], LoLChampion_df], ignore_index = True)
    return (LoLChampion_df, count)

def sort_champion_summary(LoLChampions: dict[int, dict[str, Any]]) -> pandas.DataFrame:
    LoLChampion_header: dict[str, str] = champion_summary_header
    LoLChampion_header_keys: list[str] = list(LoLChampion_header.keys())
    LoLChampion_data: dict[str, list[Any]] = {}
    for i in range(len(LoLChampion_header_keys)):
        key: str = LoLChampion_header_keys[i]
        LoLChampion_data[key] = []
    for i in sorted(LoLChampions.keys()):
        champion: dict[str, Any] = LoLChampions[i]
        for j in range(len(LoLChampion_header_keys)):
            key: str = LoLChampion_header_keys[j]
            if j <= 6:
                to_append: Any = champion[key]
            else: #角色定位子键（`role`'s subkeys）
                if key.split(": ")[1] in champion["roles"]:
                    to_append = "√"
                else:
                    to_append = ""
            LoLChampion_data[key].append(to_append)
    LoLChampion_statistics_output_order: list[int] = [0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 4, 5]
    LoLChampion_data_organized: dict[str, list[Any]] = {LoLChampion_header_keys[i]: LoLChampion_data[LoLChampion_header_keys[i]] for i in LoLChampion_statistics_output_order}
    LoLChampion_df: pandas.DataFrame = pandas.DataFrame(data = LoLChampion_data_organized)
    LoLChampion_df = pandas.concat([pandas.DataFrame([LoLChampion_header])[LoLChampion_df.columns], LoLChampion_df], ignore_index = True)
    return LoLChampion_df
