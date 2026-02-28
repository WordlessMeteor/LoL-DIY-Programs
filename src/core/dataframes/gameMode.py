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

async def sort_queue_data(connection: Connection) -> pandas.DataFrame:
    queues: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-queues/v1/queues")).json() #以前含有“最大召唤师等级”参数（There was previously a "maxLevel" parameter）
    queue_header_keys: list[str] = list(queue_header.keys())
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
