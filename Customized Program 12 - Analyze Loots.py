from lcu_driver import Connector
from lcu_driver.connection import Connection
import os, pandas, json, time
from typing import Any, IO
from src.utils.format import addDefaultStyle
from src.utils.summoner import print_summoner_info, get_info_name
from src.core.config.servers import set_summonerInfo_folder, save_platform_info
from src.core.config.headers import player_loot_header
from src.core.config.localization import essenceTypes, lootCategories, itemStatus_dict, lootRarities, redeemableStatus_dict, lootTypes

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/03/07
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector = Connector()

#-----------------------------------------------------------------------------
#  分析战利品（Analyze loots）
#-----------------------------------------------------------------------------
async def analyze_player_loots(connection: Connection) -> None: #导出玩家目前含有的战利品的信息（Exports the user's current loots' information）
    #下面设置输出文件的位置（The following code determines the output files' location）
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    displayName: str = get_info_name(current_info)
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
    riot_client_info: list[str] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info: dict[str, str] = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region: str = client_info["--region"]
    locale: str = client_info["--locale"]
    folder: str = set_summonerInfo_folder(region, platformId, current_info)
    #loots: list[dict[str, Any]] = await (await connection.request("GET", "/lol-loot/v1/loot-items")).json()
    player_loot: list[dict[str, Any]] = await (await connection.request("GET", "/lol-loot/v1/player-loot")).json()
    jsonname: str = "Loot - %s.json" %displayName
    while True:
        try:
            jsonfile: IO[Any] = open(os.path.join(folder, jsonname), "w", encoding = "utf-8")
        except FileNotFoundError:
            os.makedirs(folder, exist_ok = True)
        else:
            break
    try:
        jsonfile.write(str(json.dumps(player_loot, indent = 4, ensure_ascii = False)))
    except UnicodeEncodeError:
        print("玩家战利品信息文本文档生成失败！请检查战利品信息是否包含不常用字符！\nPlayer loot text generation failure! Please check if the loot information includes any abnormal characters!\n")
    else:
        print('玩家战利品信息已保存为“%s”。\nPlayer loot information is saved as "%s".\n' %(os.path.join(folder, jsonname), os.path.join(folder, jsonname)))
    player_loot_header_keys: list[str] = list(player_loot_header.keys())
    player_loot_data: dict[str, list[Any]] = {key: [] for key in player_loot_header_keys}
    for i in range(len(player_loot)):
        for j in range(len(player_loot_header_keys)):
            key = player_loot_header_keys[j]
            if j == 2 or j == 30:
                to_append: Any = essenceTypes[player_loot[i][key]]
            elif j == 5:
                to_append = lootCategories[player_loot[i][key]]
            elif j == 10 or j == 17:
                to_append = itemStatus_dict[player_loot[i][key]]
            elif j == 19:
                to_append = lootRarities[player_loot[i][key]]
            elif j == 20:
                to_append = redeemableStatus_dict[player_loot[i][key]]
            elif j == 29:
                to_append = lootTypes[player_loot[i][key]]
            else:
                to_append = player_loot[i][key]
            player_loot_data[key].append(to_append)
    player_loot_statistics_output_order: list[int] = [15, 9, 12, 11, 1, 0, 19, 30, 31, 32, 2, 4, 33, 5, 29, 20, 17, 10, 27]
    player_loot_data_organized: dict[str, list[Any]] = {player_loot_header_keys[i]: player_loot_data[player_loot_header_keys[i]] for i in player_loot_statistics_output_order}
    player_loot_df: pandas.DataFrame = pandas.DataFrame(data = player_loot_data_organized)
    player_loot_df = pandas.concat([pandas.DataFrame([player_loot_header])[player_loot_df.columns], player_loot_df], ignore_index = True)
    excel_name: str = "Player Loot - %s.xlsx" %displayName
    os.makedirs(folder, exist_ok = True)
    while True:
        try:
            with (pandas.ExcelWriter(path = os.path.join(folder, excel_name), mode = "a", if_sheet_exists = "replace") if os.path.exists(os.path.join(folder, excel_name)) else pandas.ExcelWriter(path = os.path.join(folder, excel_name))) as writer:
                currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
                addDefaultStyle(player_loot_df).to_excel(excel_writer = writer, sheet_name = f"{currentTime} {platformId} {locale}")
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
            input()
        else:
            print('玩家战利品信息已保存为“%s”！请按回车键退出。\nPlayer loot information is saved as "%s"! Press Enter to exit ...' %(os.path.join(folder, excel_name), os.path.join(folder, excel_name)))
            break

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await print_summoner_info(connection)
    await save_platform_info(connection)
    await analyze_player_loots(connection)
    input()

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
connector.start()
