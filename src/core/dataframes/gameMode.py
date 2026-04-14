from lcu_driver.connection import Connection
import os, pandas, sys, time
from typing import Any
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.utils.format import optimize_bool_display
from src.core.config.headers import queue_header
from src.core.config.localization import categories, gameSelectCategories, gameSelectModeGroups, tiers, queueAvailability_dict, banModes, pickModes

def sort_queue_data(queues: list[dict[str, Any]]) -> pandas.DataFrame:
    '''
    将游戏队列信息整理成一个表格。<br>Sort the game queue information into a dataframe.
    
    :param queues: 队列信息。通过`GET /lol-game-queues/v1/queues`接口获取。<br>Game queue information obtained through `GET /lol-game-queues/v1/queues` endpoint.
    :type queues: list[dict[str, Any]]
    :return: 游戏模式表。<br>Game mode dataframe.
    :rtype: pandas.DataFrame
    '''
    queue_header_keys: list[str] = list(queue_header.keys()) #以前含有“最大召唤师等级”参数（There was previously a "maxLevel" parameter）
    queue_data: dict[str, Any] = {key: [] for key in queue_header_keys}
    for queue in queues:
        for i in range(len(queue_header_keys)):
            key = queue_header_keys[i]
            if i <= 41:
                if i == 3: #对局类型（`category`）
                    to_append: Any = categories[queue[key]]
                elif i == 8: #游戏选择类别（`gameSelectCategory`）
                    to_append = gameSelectCategories[queue[key]]
                elif i == 9: #游戏模式分组（`gameSelectModeGroup`）
                    to_append = gameSelectModeGroups[queue[key]]
                elif i == 25: #双排最高段位限制（`maxTierForPremadeSize2`）
                    to_append = tiers[queue[key]]
                elif i == 32: #队列可用性（`queueAvailability`）
                    to_append = queueAvailability_dict[queue[key]]
                elif i == 40 or i == 41: #上次关闭时间和上次开放时间（`lastToggledOffDate` and `lastToggledOnDate`）
                    subkey = "lastToggledOffTime" if i == 40 else "lastToggledOnTime"
                    standard_time = time.strftime("%Y年%m月%d日%H:%M:%S", time.localtime(queue[subkey] / 1000))
                    to_append = standard_time
                else:
                    to_append = queue[key]
            elif i <= 63:
                if i == 44: #禁用模式（`banMode`）
                    to_append = banModes[queue["gameTypeConfig"][key]]
                elif i == 53: #游戏类型序号（`typeId`）
                    to_append = queue["gameTypeConfig"]["id"]
                elif i == 57: #英雄选择策略（`typeName`）
                    to_append = queue["gameTypeConfig"]["name"]
                elif i == 60: #英雄选择模式（`pickMode`）
                    to_append = pickModes[queue["gameTypeConfig"][key]]
                else:
                    to_append = queue["gameTypeConfig"][key]
            else:
                to_append = queue["queueRewards"][key]
            queue_data[key].append(to_append)
    queue_output_order: list[int] = [12, 32, 19, 15, 7, 29, 5, 6, 22, 53, 3, 39, 2, 8, 9, 10, 0, 57, 14, 16, 17, 44, 60, 40, 41, 30, 25, 23, 27, 4, 31, 28, 26, 56, 38, 24, 36, 37, 18, 51, 62, 46, 50, 1, 63, 47, 11, 45, 55, 61, 33, 34, 49, 54, 42, 43, 59, 48, 64, 65, 66, 13]
    queue_data_organized: dict[str, list[Any]] = {queue_header_keys[i]: queue_data[queue_header_keys[i]] for i in queue_output_order}
    queue_df: pandas.DataFrame = pandas.DataFrame(data = queue_data_organized)
    queue_df = queue_df.sort_values(by = "id", ascending = True, ignore_index = True)
    optimize_bool_display(queue_df)
    queue_df = pandas.concat([pandas.DataFrame([queue_header])[queue_df.columns], queue_df], ignore_index = True)
    return queue_df

async def check_available_queue(connection: Connection) -> pandas.DataFrame: #梳理可用队列（Sort out available queues）
    '''
    梳理服务器开放的游戏模式，并整理成表格的形式。<br>Filter platform available game modes and organize them into a dataframe.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :return: 可用游戏模式表。<br>Available game mode dataframe.
    :rtype: pandas.DataFrame
    '''
    gameQueues_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json()
    map_CN: dict[int, str] = {8: "水晶之痕", 10: "扭曲丛林", 11: "召唤师峡谷", 12: "随机地图", 14: "屠夫之桥", 16: "星界废墟", 18: "瓦洛兰城市公园", 19: "第43区", 20: "飞船坠落点", 21: "百合与莲花的神庙", 22: "聚点危机", 30: "怒火角斗场", 33: "最终都市", 35: "班德尔之森"}
    map_EN: dict[int, str] = {8: "Crystal Scar", 10: "Twisted Treeline", 11: "Summoner's Rift", 12: "Random Map", 14: "Butcher's Bridge", 16: "Cosmic Ruins", 18: "Valoran City Park", 19: "Substructure 43", 20: "Crash Site", 21: "Temple of Lily and Lotus", 22: "Convergence", 30: "Rings of Wrath", 33: "Final City", 35: "The Bandlewood"}
    pickmode_CN: dict[str, str] = {"AllRandomPickStrategy": "全随机模式", "SimulPickStrategy": "自选模式", "TeamBuilderDraftPickStrategy": "征召模式", "OneTeamVotePickStrategy": "投票", "TournamentPickStrategy": "竞技征召模式", "QuickplayPickStrategy": "快速匹配", "": "待定"}
    pickmode_EN: dict[str, str] = {"AllRandomPickStrategy": "All Random", "SimulPickStrategy": "Blind Pick", "TeamBuilderDraftPickStrategy": "Draft Mode", "OneTeamVotePickStrategy": "Vote", "TournamentPickStrategy": "Tournament Draft", "QuickplayPickStrategy": "Quickplay", "": "Pending"}
    available_queues: dict[int, dict[str, Any]] = {}
    for queue in gameQueues_source:
        if queue["queueAvailability"] == "Available":
            available_queues[queue["id"]] = queue
    queue_dict: dict[str, list[Any]] = {"queueID": [], "mapID": [], "map_CN": [], "map_EN": [], "gameMode": [], "pickType_CN": [], "pickType_EN": []}
    for queue in available_queues.values():
        queue_dict["queueID"].append(queue["id"])
        queue_dict["mapID"].append(queue["mapId"])
        queue_dict["map_CN"].append(map_CN[queue["mapId"]])
        queue_dict["map_EN"].append(map_EN[queue["mapId"]])
        queue_dict["gameMode"].append(queue["name"])
        queue_dict["pickType_CN"].append(pickmode_CN[queue["gameTypeConfig"]["pickMode"]])
        queue_dict["pickType_EN"].append(pickmode_EN[queue["gameTypeConfig"]["pickMode"]])
    available_queue_df: pandas.DataFrame = pandas.DataFrame(queue_dict)
    available_queue_df.sort_values(by = "queueID", inplace = True, ascending = True, ignore_index = True)
    return available_queue_df
