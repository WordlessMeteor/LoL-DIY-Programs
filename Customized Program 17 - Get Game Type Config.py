from lcu_driver import Connector
from lcu_driver.connection import Connection
import os, pandas, json
from typing import Any
from src.utils.summoner import print_summoner_info
from src.utils.format import optimize_bool_display, addDefaultStyle
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.headers import gametype_config_header
from src.core.config.servers import save_platform_info
from src.localization.multilingual import gameTypes_config

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/08/17
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 获取英雄联盟中的所有游戏类型信息（Get all game types' information in League of Legends）
#-----------------------------------------------------------------------------
async def sort_gametype_config(connection: Connection) -> None:
    gametype_config: list[dict[str, Any]] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/gameTypeConfigs")).json()
    gameTypes_zh: dict[str, str] = {gameType: gameTypes_config[gameType]["zh_CN"] for gameType in gameTypes_config}
    gameTypes_en: dict[str, str] = {gameType: gameTypes_config[gameType]["en_US"] for gameType in gameTypes_config}
    gametype_config_header_keys: list[str] = list(gametype_config_header.keys())
    gametype_config_data: dict[str, list[Any]] = {key: [] for key in gametype_config_header_keys}
    for config in gametype_config:
        for i in range(len(gametype_config_header_keys)):
            key: str = gametype_config_header_keys[i]
            if i <= 21:
                if key in config:
                    to_append = config[key]
                else:
                    to_append = False if i in {0, 1, 4, 5, 6, 7, 8, 9, 12, 17, 20, 21} else ""
            else:
                if i == 22: #中文名称（`localizedName_zh`）
                    to_append = gameTypes_zh.get(config["name"], "")
                else: #英文名称（`localizedName_en`）
                    to_append = gameTypes_en.get(config["name"], "")
            gametype_config_data[key].append(to_append)
    gametype_config_statistics_output_order: list[int] = [11, 15, 22, 23, 18, 2, 1, 14, 3, 13, 19, 20, 21, 5, 9, 8, 4, 12, 0, 17, 6, 7, 10, 16]
    gametype_config_data_organized: dict[str, list[Any]] = {gametype_config_header_keys[i]: gametype_config_data[gametype_config_header_keys[i]] for i in gametype_config_statistics_output_order}
    gametype_config_df: pandas.DataFrame = pandas.DataFrame(data = gametype_config_data_organized)
    optimize_bool_display(gametype_config_df)
    gametype_config_df = pandas.concat([pandas.DataFrame([gametype_config_header])[gametype_config_df.columns], gametype_config_df], ignore_index = True)
    #导出到Excel工作簿（Export to an Excel workbook）
    excel_name: str = "游戏类型信息.xlsx"
    if not os.path.exists(excel_name):
        wbCreateFlag: bool = create_workbook_win32(os.path.abspath(excel_name), sheet1_name = "所有游戏类型（All Game Types）")
    while True:
        try:
            with (pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") if os.path.exists(excel_name) else pandas.ExcelWriter(path = excel_name)) as writer:
                addDefaultStyle(gametype_config_df).to_excel(excel_writer = writer, sheet_name = "所有游戏类型（All Game Types）")
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
            input()
        else:
            break
    print(f"游戏类型信息已导出到同目录下的{excel_name}中。请按回车键退出。\nGame type config has been exported to {excel_name} under the same dierctory. Press Enter to exit.")
    input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    await print_summoner_info(connection)
    await save_platform_info(connection)
    await sort_gametype_config(connection)

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
