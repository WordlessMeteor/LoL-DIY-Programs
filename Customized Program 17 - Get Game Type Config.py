from lcu_driver import Connector
import pandas, os, json

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2025/06/29
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

connector = Connector()

async def get_summoner_data(connection):
    data = await connection.request('GET', '/lol-summoner/v1/current-summoner')
    summoner = await data.json()
    print("displayName:    %s" %(summoner["gameName"] + "#" + summoner["tagLine"]))
    print("summonerId:     %s" %(summoner["summonerId"]))
    print("puuid:          %s" %(summoner["puuid"]))
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
# 获取英雄联盟中的所有游戏类型信息（Get all game types' information in League of Legends）
#-----------------------------------------------------------------------------
async def get_gametype_config(connection):
    gametype_config = []
    for i in range(100):
        response = await (await connection.request("GET", f"/lol-game-queues/v1/game-type-config/{i}")).json()
        print(response)
        if "errorCode" in response:
            if response["message"] == f'No game type config found with id {i}':
                #print(f"没有找到序号为{i}的游戏类型信息。\nNo game type config found with id {i}.")
                pass
            else:
                #print(f"序号为{i}的游戏类型信息获取失败。\nFailed to get the game type config with id {i}.")
                pass
        else:
            print(f"序号为{i}的游戏类型信息如下：\nGame type config with id {i} is as follows:")
            print(response)
            gametype_config.append(response)
    jsonname = "GameTypeConfig.json"
    with open(jsonname, "w", encoding = "utf-8") as fp:
        json.dump(gametype_config, fp, indent = 4, ensure_ascii = False)
    gameTypes_zh = {"GAME_CFG_PICK_BLIND": "自选模式（自定义）", "GAME_CFG_DRAFT_STD": "征召模式（自定义）", "GAME_CFG_DRAFT_NOBAN": "轮选模式", "GAME_CFG_PICK_RANDOM": "全随机模式（自定义）", "GAME_CFG_PICK_SIMUL": "同选模式", "GAME_CFG_DRAFT_TOURNAMENT": "竞技征召模式（自定义）", "GAME_CFG_PICK_SIMUL_TD": "计时征召", "GAME_CFG_BASIC_TUTORIAL": "基础教程", "GAME_CFG_ADV_TUTORIAL": "进阶教程", "GAME_CFG_CAP": "最终教程", "GAME_CFG_BLIND_RANDOM": "盲选随机", "GAME_CFG_BLIND_DUPE": "克隆选择（自定义）", "GAME_CFG_CROSS_DUPE": "全队克隆", "GAME_CFG_BLIND_DRAFT_ST": "自选征召模式（自定义）", "GAME_CFG_COUNTER_PICK": "互选模式（自定义）", "GAME_CFG_TEAM_BUILDER_DRAFT": "征召模式", "GAME_CFG_TEAM_BUILDER_BLIND": "自选模式", "GAME_CFG_TEAM_BUILDER_BLIND_DRAFT": "自选征召", "GAME_CFG_TEAM_BUILDER_RANDOM": "全随机模式", "GAME_CFG_TEAM_BUILDER_BLIND_DUPE": "克隆选择", "GAME_CFG_TEAM_BUILDER_QUICKPLAY": "快速匹配"}
    gameTypes_en = {"GAME_CFG_PICK_BLIND": "Blind Pick (custom)", "GAME_CFG_DRAFT_STD": "Draft Mode (custom)", "GAME_CFG_DRAFT_NOBAN": "Draft Noban (custom)", "GAME_CFG_PICK_RANDOM": "All Random (custom)", "GAME_CFG_PICK_SIMUL": "Simultaneous Pick (custom)", "GAME_CFG_DRAFT_TOURNAMENT": "Tournament Draft (custom)", "GAME_CFG_PICK_SIMUL_TD": "Timed Draft (custom)", "GAME_CFG_BASIC_TUTORIAL": "Basic Tutorial", "GAME_CFG_ADV_TUTORIAL": "Advanced Tutorial", "GAME_CFG_CAP": "Capstone Tutorial", "GAME_CFG_BLIND_RANDOM": "Blind Random (custom)", "GAME_CFG_BLIND_DUPE": "All for one (custom)", "GAME_CFG_CROSS_DUPE": "All for one (cross-team)", "GAME_CFG_BLIND_DRAFT_ST": "Blind Draft Pick (custom)", "GAME_CFG_COUNTER_PICK": "Nemesis Draft (custom)", "GAME_CFG_TEAM_BUILDER_DRAFT": "Draft Pick", "GAME_CFG_TEAM_BUILDER_BLIND": "Blind Pick", "GAME_CFG_TEAM_BUILDER_BLIND_DRAFT": "Blind Draft Pick", "GAME_CFG_TEAM_BUILDER_RANDOM": "All Random", "GAME_CFG_TEAM_BUILDER_BLIND_DUPE": "All for one", "GAME_CFG_TEAM_BUILDER_QUICKPLAY": "Quickplay"}
    gametype_config_header = {"advancedLearningQuests": "进阶教程", "allowTrades": "允许交换", "banMode": "禁用模式", "banTimerDuration": "禁用时间限制（秒）", "battleBoost": "战斗加成", "crossTeamChampionPool": "跨队伍英雄共享", "deathMatch": "团体竞赛", "doNotRemove": "禁止退出游戏", "duplicatePick": "克隆选择", "exclusivePick": "唯一选择", "gameModeOverride": "游戏模式重载设置", "id": "序号", "learningQuests": "新手教程", "mainPickTimerDuration": "盲选时间限制（秒）", "maxAllowableBans": "最大禁用数量", "name": "代码", "numPlayersPerTeamOverride": "队伍规模重载设置", "onboardCoopBeginner": "人机对战引导模式", "pickMode": "英雄选择模式", "postPickTimerDuration": "符文和皮肤选择时间限制（秒）", "reroll": "允许重随", "teamChampionPool": "队伍英雄共享", "localizedName_zh": "中文名称", "localizedName_en": "英文名称"}
    gametype_config_header_keys = list(gametype_config_header.keys())
    gametype_config_data = {}
    for i in range(len(gametype_config_header_keys)):
        key = gametype_config_header_keys[i]
        gametype_config_data[key] = []
    for config in gametype_config:
        for i in range(len(gametype_config_header_keys)):
            key = gametype_config_header_keys[i]
            if i <= 21:
                gametype_config_data[key].append(config[key])
            else:
                if i == 22: #中文名称（`localizedName_zh`）
                    gametype_config_data[key].append(gameTypes_zh.get(config["name"]))
                else: #英文名称（`localizedName_en`）
                    gametype_config_data[key].append(gameTypes_en.get(config["name"]))
    gametype_config_statistics_output_order = [11, 15, 22, 23, 18, 2, 1, 14, 3, 13, 19, 20, 21, 5, 9, 8, 4, 12, 0, 17, 6, 7, 10, 16]
    gametype_config_data_organized = {}
    for i in gametype_config_statistics_output_order:
        key = gametype_config_header_keys[i]
        gametype_config_data_organized[key] = gametype_config_data[key]
    gametype_config_df = pandas.DataFrame(data = gametype_config_data_organized)
    for column in gametype_config_df:
        if gametype_config_df[column].dtype == "bool":
            gametype_config_df[column] = gametype_config_df[column].astype(str)
            for i in range(len(gametype_config_df)):
                gametype_config_df.loc[i, column] = "√" if gametype_config_df[column][i] == "True" else ""
    gametype_config_df = pandas.concat([pandas.DataFrame([gametype_config_header])[gametype_config_df.columns], gametype_config_df], ignore_index = True)
    #导出到Excel工作簿（Export to an Excel workbook）
    excel_name = "游戏类型信息.xlsx"
    while True:
        try:
            with pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") as writer:
                gametype_config_df.to_excel(excel_writer = writer, sheet_name = "All Game Types")
        except PermissionError:
            print("无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press any key to try again.")
            input()
        except FileNotFoundError:
            with pandas.ExcelWriter(path = excel_name) as writer:
                gametype_config_df.to_excel(excel_writer = writer, sheet_name = "All Game Types")
            break
        else:
            break
    print(f"游戏类型信息已导出到同目录下的{jsonname}和{excel_name}中。请按回车键退出。\nGame type config has been exported to {jsonname} and {excel_name} under the same dierctory. Press Enter to exit.")
    input()

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection):
    await get_summoner_data(connection)
    await get_gametype_config(connection)

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
