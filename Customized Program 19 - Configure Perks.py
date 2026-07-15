from lcu_driver import Connector
from lcu_driver.connection import Connection
import copy, json, os, pandas, platform, pyperclip, re, subprocess, time, traceback
from typing import Any, Optional
from src.utils.format import getISOTime, optimize_bool_display, format_df, addDefaultStyle, pyobj2json
from src.utils.logger import LogManager
from src.utils.summoner import print_summoner_info, get_info_name
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.localization import gamemaps, slotTypes, positions, recommendedAttributes
from src.core.config.headers import perk_header, recommendedPage_header, perkPage_header
from src.core.config.servers import set_summonerInfo_folder, save_platform_info
from src.core.dataframes.champions import sort_inventory_champions, filter_champion

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/07/15
#=============================================================================

#-----------------------------------------------------------------------------
# 工具库（Tool library）
#-----------------------------------------------------------------------------
#  - lcu-driver 
#    https://github.com/sousa-andre/lcu-driver
#-----------------------------------------------------------------------------

spells: dict[int, dict[str, Any]] = {}
perks_source: list[dict[str, Any]] = []
perks: dict[int, dict[str, Any]] = {}
perkstyles_source: dict[str, Any] = {}
perkstyles: dict[int, dict[str, Any]] = {}
LoLChampions: dict[int, dict[str, Any]] = {}
recommended_position_for_champions: dict[str, dict[str, Any]] = {}
champion_colloq_dict: dict[int, list[str]] = {}
log: LogManager = LogManager()

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 配置符文（Configure perks）
#-----------------------------------------------------------------------------
def clear_screen() -> None:
    '''
    清理终端屏幕。跨平台支持。<br>Clear the terminal screen. Cross-platform support.
    '''
    if platform.system() == "Windows":
        subprocess.call("CLS", shell = True)
    else:
        subprocess.call("clear", shell = True)

async def prepare_data_resources(connection: Connection) -> None:
    '''
    准备全局数据资源。<br>Prepare global data resources.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    global spells, perks_source, perks, perkstyles_source, perkstyles, LoLChampions, recommended_position_for_champion, champion_colloq_dict
    #召唤师技能（Summoner spell）
    spells_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-spells.json")).json()
    spells = {spell["id"]: spell for spell in spells_source}
    #符文（Perks）
    perks_source = await (await connection.request("GET", "/lol-perks/v1/perks")).json()
    perks = {perk["id"]: perk for perk in perks_source}
    #符文系（Perkstyles）
    perkstyles_source = await (await connection.request("GET", "/lol-game-data/assets/v1/perkstyles.json")).json()
    perkstyles = {style["id"]: style for style in perkstyles_source["styles"]}
    #英雄（LoL Champion）
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    LoLChampions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-champions/v1/inventories/%s/champions" %(current_info["summonerId"]))).json()
    LoLChampions = {champion["id"]: champion for champion in LoLChampions_source}
    #推荐分路（Recommended positions）
    recommended_position_for_champion = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
    ##英雄惯用语（Champion colloquialism）
    champion_catalog: list[dict[str, Any]] = await (await connection.request("GET", "/lol-catalog/v1/items/CHAMPION")).json()
    champion_colloq_dict = {item["itemId"]: item.get("tags", []) for item in champion_catalog}

#数据整理部分（Data organization）
def sort_perk_data(perks_source: list[dict[str, Any]], perkstyles_source: dict[str, Any]) -> pandas.DataFrame:
    '''
    将符文和符文系数据整理成表格。<br>Sort perk and perkstyle data into a dataframe.
    
    :param perks_source: 原始符文数据资源。<br>Raw perk data resource.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks_source: list[dict[str, Any]]
    :param perkstyles_source: 原始符文系数据资源。<br>Raw perkstyle data resource.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles_source: dict[str, Any]
    :return: 符文数据框。<br>Perk dataframe.
    :rtype: pandas.DataFrame
    '''
    perkstyles: dict[int, dict[str, Any]] = {style["id"]: style for style in perkstyles_source["styles"]}
    #下面指定符文的排列顺序（The following code specify the perk ordering）
    defaultPerkOrder: list[int] = [] #后续形成数据框时，对符文按照其在客户端中的出现顺序进行排序（When the dataframe is formed, sort it by the order that the perks appear in the League Client）
    perkSlotLabels: dict[int, str] = {}
    ##基石和符文（Keystones and perks）
    for style in perkstyles_source["styles"]:
        for slot in style["slots"]:
            if slot["type"] in {"kKeyStone", "kMixedRegularSplashable"}:
                defaultPerkOrder += slot["perks"]
            for perkId in slot["perks"]:
                perkSlotLabels[perkId] = slot["slotLabel"]
    ##属性（Stat mods）
    kStatMod_perkIds: list[int] = []
    for perk in perks_source:
        if perk["slotType"] == "kStatMod":
            kStatMod_perkIds.append(perk["id"])
    defaultPerkOrder += sorted(kStatMod_perkIds)
    ##其它符文按照符文序号正序排列（Other perks are sorted by the ascending order of perkId）
    perkIds_sorted: list[int] = sorted(map(lambda x: x["id"], perks_source))
    for perkId in perkIds_sorted:
        if not perkId in defaultPerkOrder:
            defaultPerkOrder.append(perkId)
    ##构建符文序号权重字典（Create the status dictionary of perkIds）
    defaultPerkOrder_dict: dict[int, int] = {defaultPerkOrder[i]: i for i in range(len(defaultPerkOrder))}
    perk_header_keys: list[str] = list(perk_header.keys())
    perk_data: dict[str, list[Any]] = {key: [] for key in perk_header_keys}
    for perk in perks_source:
        for i in range(len(perk_header_keys)):
            key: str = perk_header_keys[i]
            if i <= 9:
                if i == 6: #槽位类型（`slotType`）
                    to_append: Any = slotTypes[perk[key]]
                else:
                    to_append = perk[key]
            elif i == 10: #符文系名称（`styleName`）
                to_append = perkstyles[perk["styleId"]]["name"] if perk["styleId"] in perkstyles else ""
            else: #槽位标签（`slotLabel`）
                to_append = perkSlotLabels.get(perk["id"], "")
            perk_data[key].append(to_append)
    perk_statistics_output_order: list[int] = [1, 3, 7, 8, 10, 6, 11, 4, 5, 2, 9, 0]
    perk_data_organized: dict[str, list[Any]] = {perk_header_keys[i]: perk_data[perk_header_keys[i]] for i in perk_statistics_output_order}
    perk_df: pandas.DataFrame = pandas.DataFrame(data = perk_data_organized)
    perk_df = perk_df.sort_values(by = "id", key = lambda x: x.map(defaultPerkOrder_dict), ascending = True)
    perk_df = pandas.concat([pandas.DataFrame([perk_header])[perk_df.columns], perk_df], ignore_index = True)
    return perk_df

def sort_recommended_perk(recommendedPages: list[dict[str, Any]]) -> pandas.DataFrame:
    '''
    将推荐符文页整理成一张表格。<br>Organize recommended pages into a dataframe.
    
    :param recommendedPages: 推荐符文页列表。<br>A list of recommended pages.
    :type recommendedPages: list[dict[str, Any]]
    :return: 推荐符文页数据框。<br>Recommended page dataframe.
    :rtype: pandas.DataFrame
    '''
    if recommendedPages == []:
        recommendedPage_df: pandas.DataFrame = pandas.DataFrame(data = recommendedPage_header, index = [0])
    else:
        recommendedPage_header_keys: list[str] = list(recommendedPage_header.keys())
        recommendedPage_data: dict[str, list[Any]] = {key: [] for key in recommendedPage_header_keys}
        recommendedPage_data_json: dict[str, list[Any]] = copy.deepcopy(recommendedPage_data)
        for page in recommendedPages:
            for i in range(len(recommendedPage_header_keys)):
                key: str = recommendedPage_header_keys[i]
                if i <= 12:
                    if i == 2: #分路（`position`）
                        to_append: Any = positions[page[key]]
                    elif i == 4 or i == 8: #推荐属性类键（Recommendation attribute-type keys）
                        to_append = recommendedAttributes[page[key]]
                    elif i == 10: #主系名称（`primaryPerkStyleName`）
                        to_append = perkstyles[page["primaryPerkStyleId"]]["name"]
                    elif i == 11: #副系名称（`secondaryPerkStyleName`）
                        to_append = perkstyles[page["secondaryPerkStyleId"]]["name"]
                    elif i == 12:
                        to_append = list(map(lambda x: spells[x]["name"], page["summonerSpellIds"]))
                    else:
                        to_append = page[key]
                elif i <= 14: #基石符文相关键（Keystone-related keys）
                    to_append = page[key.split()[0]][key.split()[1]]
                elif i == 15: #推荐符文序号列表（`perkIds`）
                    to_append = list(map(lambda x: x["id"], page["perks"]))
                else: #推荐符文名称列表（`perkNames`）
                    to_append = list(map(lambda x: x["name"], page["perks"]))
                recommendedPage_data[key].append(to_append)
                recommendedPage_data_json[key].append(pyobj2json(to_append))
        recommendedPage_statistics_output_order: list[int] = [2, 0, 3, 10, 4, 7, 11, 8, 13, 14, 15, 16, 1, 9, 12, 6]
        recommendedPage_data_organized: dict[str, list[Any]] = {recommendedPage_header_keys[i]: recommendedPage_data_json[recommendedPage_header_keys[i]] for i in recommendedPage_statistics_output_order}
        recommendedPage_df = pandas.DataFrame(data = recommendedPage_data_organized)
        optimize_bool_display(recommendedPage_df)
        recommendedPage_df = pandas.concat([pandas.DataFrame([recommendedPage_header])[recommendedPage_df.columns], recommendedPage_df], ignore_index = True)
    return recommendedPage_df

async def get_perk_page(connection: Connection) -> pandas.DataFrame:
    '''
    获取用户的符文配置，并整理成一张表格。<br>Get perk configuration of the user and organize it into a dataframe.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :return: 用户符文页数据框。<br>User perk page dataframe.
    :rtype: pandas.DataFrame
    '''
    perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
    perkPage_header_keys: list[str] = list(perkPage_header.keys())
    perkPage_data: dict[str, list[Any]] = {key: [] for key in perkPage_header_keys}
    perkPage_data_json: dict[str, list[Any]] = copy.deepcopy(perkPage_data)
    for page in perkPages:
        for i in range(len(perkPage_header_keys)):
            key: str = perkPage_header_keys[i]
            if i <= 26:
                if i == 24: #上次修改时间（`lastModifiedTime`）
                    to_append: Any = getISOTime(page["lastModified"] / 1000)
                elif i == 25: #快速模式英雄名称列表（`quickPlayChampionNames`）
                    to_append = list(map(lambda x: LoLChampions[x]["name"], page["quickPlayChampionIds"]))
                elif i == 26: #推荐英雄名称（`recommendationChampionName`）
                    to_append = "" if page["recommendationChampionId"] == 0 else LoLChampions[page["recommendationChampionId"]]["name"]
                else:
                    to_append = page[key]
            elif i <= 31:
                if i == 30: #基石槽位类型（`pageKeystone slotType`）
                    to_append = slotTypes[page[key.split()[0]][key.split()[1]]]
                else:
                    to_append = page[key.split()[0]][key.split()[1]]
            else: #已选择的符文（`uiPerksNames`）
                to_append = list(map(lambda x: x["name"], page["uiPerks"]))
            perkPage_data[key].append(to_append)
            perkPage_data_json[key].append(to_append)
    perkPage_statistics_output_order: list[int] = [2, 10, 11, 1, 3, 7, 5, 4, 8, 6, 13, 14, 12, 22, 20, 19, 28, 29, 30, 31, 27, 32, 21, 23, 24, 15, 25, 16, 26, 18]
    perkPage_data_organized: dict[str, list[Any]] = {perkPage_header_keys[i]: perkPage_data_json[perkPage_header_keys[i]] for i in perkPage_statistics_output_order}
    perkPage_df: pandas.DataFrame = pandas.DataFrame(data = perkPage_data_organized)
    optimize_bool_display(perkPage_df)
    perkPage_df = pandas.concat([pandas.DataFrame([perkPage_header])[perkPage_df.columns], perkPage_df], ignore_index = True)
    return perkPage_df

#过程（Process）
def check_all_perks_classified(perks: dict[int, dict[str, Any]], perkstyles: dict[int, dict[str, Any]]) -> None:
    '''
    按类别打印所有符文。<br>Print all perks by classes.
    
    :param perks: 整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`
    :type perks: dict[int, dict[str, Any]]
    :param perkstyles: 整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`
    :type perkstyles: dict[int, dict[str, Any]]
    '''
    HTML_tag_re: re.Pattern[str] = re.compile(r"<[^>]*>")
    perkIds_unprinted: list[int] = list(map(lambda x: x["id"], perks.values()))
    #先打印符文系下的符文（First, print perks under perkstyles）
    for i in range(len(perkstyles)):
        style: dict[str, Any] = perkstyles[sorted(perkstyles.keys())[i]]
        slots: list[dict[str, Any]] = [] #要打印的符文槽位。属性单独显示，不会在某个符文系中被打印出来（Slots to print. Stat mods are displayed individually but not printed under any perkstyle）
        for slot in style["slots"]:
            if slot["type"] in {"kKeyStone", "kMixedRegularSplashable"}:
                slots.append(slot)
        splashableSeries: int = 0
        for j in range(len(slots)):
            slot: dict[str, Any] = slots[j]
            logPrint("%d - %s: %s\n" %(style["id"], style["name"], style["tooltip"]))
            if slot["type"] == "kKeyStone":
                logPrint("%s（%s）：" %(slotTypes[slot["type"]], slot["type"]))
            else:
                splashableSeries += 1
                logPrint("%s第%d系列 - %s（%s Series %d - %s）：" %(slotTypes[slot["type"]], splashableSeries, slot["slotLabel"], slot["type"], splashableSeries, slot["slotLabel"]))
            for perkId in slot["perks"]:
                perkIds_unprinted.remove(perkId)
                perk: dict[str, Any] = perks[perkId]
                shortDesc: str = perk["shortDesc"].replace("<br>", "\n")
                longDesc: str = perk["longDesc"].replace("<br>", "\n")
                while (matchObj := HTML_tag_re.search(shortDesc)):
                    shortDesc = shortDesc.replace(matchObj.group(), "")
                while (matchObj := HTML_tag_re.search(longDesc)):
                    longDesc = longDesc.replace(matchObj.group(), "")
                shortDesc = shortDesc.replace("\n", "<br>")
                longDesc = longDesc.replace("\n", "<br>")
                logPrint("%d - %s: %s\n简略描述（ShortDesc）：%s\n详细描述（LongDesc）：%s\n" %(perk["id"], perk["name"], perk["recommendationDescriptor"], shortDesc, longDesc))
            if j < len(slots) - 1:
                logPrint("按回车键以显示下一行符文。\nPress Enter to display the next line of perks.")
                logInput()
                logPrint()
                #clear_screen()
        if i < len(perkstyles) - 1:
            logPrint("按回车键以显示下一个符文系。\nPress Enter to display the next perkstyle.")
            logInput()
            logPrint("\n")
            #clear_screen()
        else:
            logPrint("按回车键以显示属性。\nPress Enter to display the stat modes.")
            logInput()
            logPrint("\n")
            #clear_screen()
    #然后打印属性符文（Second, print stat mods）
    logPrint("属性（kStatMod）：")
    for perk in perks_source:
        if perk["slotType"] == "kStatMod":
            perkIds_unprinted.remove(perk["id"])
            shortDesc = perk["shortDesc"].replace("<br>", "\n")
            while (matchObj := HTML_tag_re.search(shortDesc)):
                shortDesc = shortDesc.replace(matchObj.group(), "")
            shortDesc = shortDesc.replace("\n", "<br>")
            logPrint("%d - %s: %s" %(perk["id"], perk["name"], shortDesc)) #属性符文的简略描述和详细描述是相同的，所以只需要输出一个即可（LongDesc and shortDesc of all stat mods are the same, respectively, so only one of each is enough to output）
    logPrint("\n按回车键以显示其它符文。\nPress Enter to display other perks.")
    logInput()
    logPrint("\n")
    #clear_screen()
    #最后打印其它符文（At last, print other perks）
    logPrint("其它（Others）：")
    for perkId in sorted(perkIds_unprinted):
        perk = perks[perkId]
        shortDesc = perk["shortDesc"].replace("<br>", "\n")
        longDesc = perk["longDesc"].replace("<br>", "\n")
        while (matchObj := HTML_tag_re.search(shortDesc)):
            shortDesc = shortDesc.replace(matchObj.group(), "")
        while (matchObj := HTML_tag_re.search(longDesc)):
            longDesc = longDesc.replace(matchObj.group(), "")
        shortDesc = shortDesc.replace("\n", "<br>")
        longDesc = longDesc.replace("\n", "<br>")
        logPrint("%d - %s: %s\n简略描述（ShortDesc）：%s\n详细描述（LongDesc）：%s\n" %(perk["id"], perk["name"], perk["recommendationDescriptor"], shortDesc, longDesc))
    logPrint("按回车键以返回上一层。\nPress Enter to return to the last step.")
    logInput()
    logPrint("\n")
    #clear_screen()

def check_all_perks_tabified(perk_df: pandas.DataFrame) -> None:
    '''
    将符文数据框打印到终端。<br>Print the perk dataframe to terminal.
    
    :param perk_df: 符文数据框。<br>Perk dataframe.
    :type perk_df: pandas.DataFrame
    '''
    HTML_tag_re: re.Pattern[str] = re.compile(r"<[^>]*>")
    for i in range(1, len(perk_df)):
        shortDesc = perk_df["shortDesc"][i]
        while (matchObj := HTML_tag_re.search(shortDesc)):
            shortDesc = shortDesc.replace(matchObj.group(), "") #数据框在输出到终端时移除HTML标签（When the dataframe is output to terminal, the HTML tags are removed）
        perk_df.loc[i, "shortDesc"] = shortDesc
    perk_df_fields_to_print: list[str] = ["styleName", "id", "name", "slotType", "slotLabel"]
    print(format_df(perk_df.loc[:, perk_df_fields_to_print])[0])
    log.write(format_df(perk_df.loc[:, perk_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")

def export_all_perks(perk_df: pandas.DataFrame) -> None:
    '''
    将符文数据框导出到工作簿。<br>Export the perk dataframe into a workbook.
    
    :param perk_df: 符文数据框。<br>Perk dataframe.
    :type perk_df: pandas.DataFrame
    '''
    excel_name: str = "Perks.xlsx"
    if not os.path.exists(excel_name):
        wbCreateFlag: bool = create_workbook_win32(os.path.abspath(excel_name), sheet1_name = "Perks")
    while True:
        try:
            with (pandas.ExcelWriter(path = excel_name, mode = "a", if_sheet_exists = "replace") if os.path.exists(excel_name) else pandas.ExcelWriter(path = excel_name)) as writer:
                addDefaultStyle(perk_df).to_excel(excel_writer = writer, sheet_name = "Perks") #数据框在导出到Excel中时保留最原始的数据（When the dataframe is exported to Excel, the most original information is reserved）
        except PermissionError:
            logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
            logInput()
        else:
            break
    logPrint(f'符文信息已导出到同目录下的“{excel_name}”中。\nPerk information has been exported into {excel_name} under the same folder.')

def check_all_perks() -> None:
    '''
    查看所有符文信息。由此进入各种输出形式。<br>Check all perks. Entry to output forms.
    '''
    logPrint("请选择输出形式：\nPlease select a form to output:\n0\t返回上一层（Return to the last step）\n1\t分类（Classified）\n2\t表格（Tabified）\n3\t文件（File）")
    while True:
        form: str = logInput()
        if form == "":
            continue
        elif form[0] == "0":
            break
        elif form[0] == "1":
            check_all_perks_classified(perks, perkstyles)
            break
        elif form[0] == "2":
            perk_df: pandas.DataFrame = sort_perk_data(perks_source, perkstyles_source)
            check_all_perks_tabified(perk_df)
            break
        elif form[0] == "3":
            perk_df = sort_perk_data(perks_source, perkstyles_source)
            export_all_perks(perk_df)
            break
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")

def specify_recommend_perkPage_parameters() -> tuple[int, int, str, int]:
    '''
    指定推荐符文接口的参数。<br>Specify parameters required by the recommend perk endpoint.
    
    :return: 步骤数、英雄序号、分路和地图序号。<br>Step number, championId, position and mapId.
    
        步骤数的作用类似于状态码。当步骤数为0时，表示用户取消操作；否则表示操作完成。<br>The role of step number resembles a status code. When step is 0, it means the user has cancelled this operation. Otherwise, the operation is finished.
    :rtype: tuple[int, int, str, int]
    '''
    championId: int = 0
    championName: str = ""
    championAlias: str = ""
    championPosition: str = "TOP"
    mapId: int = 11
    step: int = 1
    while True:
        if step == 0:
            break
        elif step == 1:
            logPrint("第一步：请选择一个英雄：\nStep 1: Please select a champion:")
            LoLChampion_df: pandas.DataFrame = sort_inventory_champions(LoLChampions, recommended_position_for_champion)[0]
            LoLChampion_df["colloq"] = ["检索关键字"] + list(map(lambda x: champion_colloq_dict[x] if x in champion_colloq_dict and champion_colloq_dict[x] != None else [], LoLChampion_df["id"][1:]))
            LoLChampion_fields_to_print: list[str] = ["id", "name", "title", "alias"]
            LoLChampion_df_query_initial: pandas.DataFrame = LoLChampion_df.loc[:, LoLChampion_fields_to_print + ["colloq"]] #代表初始值（Represent the initial value）
            LoLChampion_df_query: pandas.DataFrame = LoLChampion_df_query_initial #代表查询过程中的值（Represent the value during a query）
            print(format_df(LoLChampion_df.loc[:, LoLChampion_fields_to_print])[0])
            log.write(format_df(LoLChampion_df.loc[:, LoLChampion_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
            while True:
                champion_queryStr: str = logInput()
                if champion_queryStr == "":
                    continue
                elif champion_queryStr == "0":
                    step -= 2
                    break
                else:
                    break_flag, championId, LoLChampion_df_query = filter_champion(champion_queryStr, LoLChampion_df_query, LoLChampion_df_query_initial)
                    if break_flag:
                        championName = LoLChampions[championId]["name"]
                        championAlias = LoLChampions[championId]["alias"]
                        break
        elif step == 2:
            recommendedPositions: list[str] = recommended_position_for_champion[str(championId)]["recommendedPositions"] if str(championId) in recommended_position_for_champion else ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
            logPrint("第二步：请选择一条推荐路线：\nStep 2: Please select a recommended position:")
            position_count: int = 0
            for position in recommendedPositions:
                position_count += 1
                logPrint("%d\t%s\t%s" %(position_count, position, positions[position]))
            while True:
                position_str: str = logInput()
                if position_str == "0":
                    step -= 2
                    break
                elif position_str.upper() in recommendedPositions:
                    championPosition: str = position_str.upper()
                    break
                elif position_str in list(map(str, range(1, len(recommendedPositions) + 1))):
                    championPosition = recommendedPositions[int(position_str) - 1]
                    break
                elif position_str.upper() in positions:
                    logPrint("%s的推荐路线中没有%s。请重新输入。\n%s isn't a recommended position of %s. Please try again." %(championName, position_str.upper(), position_str.upper(), championAlias))
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif step == 3:
            logPrint("第三步：请输入地图序号：\nStep 3: Please enter the mapId:")
            gamemap_df: pandas.DataFrame = pandas.DataFrame(data = {"mapId": list(gamemaps.keys()), "zh_CN": list(map(lambda x: x["zh_CN"], gamemaps.values())), "en_US": list(map(lambda x: x["en_US"], gamemaps.values()))})
            print(format_df(gamemap_df)[0])
            log.write(format_df(gamemap_df, width_exceed_ask = False, direct_print = False)[0])
            while True:
                mapStr: str = logInput()
                if mapStr == "0":
                    step -= 2
                    break
                elif mapStr == "":
                    mapId: int = 11
                    break
                elif mapStr in list(map(str, gamemaps.keys())):
                    mapId = int(mapStr)
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input. Please try again.")
        elif step == 4:
            break
        else:
            logPrint("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
        step += 1
    return (step, championId, championPosition, mapId)

def check_recommend_perkPage(recommendedPages: list[dict[str, Any]], championId: int, position: str, mapId: int) -> None:
    '''
    输出并导出推荐符文。<br>Output and export recommend perk information.
    
    :param recommendedPages: 推荐符文列表。<br>Recommend perks list.
    
        推荐符文信息可以通过以下LCU接口获取：<br>Recommend perk information can be obtained from the following LCU endpoint:
        - `GET /lol-perks/v1/recommended-pages/champion/{championId}/position/{position}/map/{mapId}`
    :type recommendedPages: list[dict[str, Any]]
    :param championId: 英雄序号。仅用于输出。<br>ChampionId. Only used for output.
    :type championId: int
    :param position: 分路。仅用于输出。<br>Position. Only used for output.
    :type position: str
    :param mapId: 地图序号。仅用于输出。<br>MapId. Only used for output.
    :type mapId: int
    '''
    recommendedPage_df: pandas.DataFrame = sort_recommended_perk(recommendedPages)
    championName: str = LoLChampions[championId]["name"]
    championAlias: str = LoLChampions[championId]["alias"]
    if len(recommendedPage_df) == 1: #一般情况下接口数据是正常获取的（The endpoint should work in normal cases）
        logPrint("%s中的%s%s推荐符文信息不可用。\nRecommended perk information of %s %s on %s isn't available." %(gamemaps[mapId]["zh_CN"], positions[position], championName, position, championAlias, gamemaps[mapId]["en_US"]))
    else:
        logPrint('选择下方的一个方案以查看详细信息。输入“0”以返回上一层。\nSelect a page to check the details. Submit "0" to return to the last step.')
        recommendedPage_df_fields_to_print: list[str] = ["primaryPerkStyleName", "secondaryPerkStyleName", "keystone name", "summonerSpellNames"]
        print(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], print_index = True)[0])
        log.write(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
        while True:
            pageIndex_str: str = logInput()
            if pageIndex_str == "":
                continue
            elif pageIndex_str == "0":
                break
            elif pageIndex_str in list(map(str, range(1, len(recommendedPage_df) + 1))):
                pageIndex: int = int(pageIndex_str)
                primaryPerkStyleName: str = recommendedPage_df["primaryPerkStyleName"][pageIndex]
                primaryPerkStyleId: int = recommendedPage_df["primaryPerkStyleId"][pageIndex]
                primaryRecommendationAttribute: str = recommendedPage_df["primaryRecommendationAttribute"][pageIndex]
                secondaryPerkStyleName: str = recommendedPage_df["secondaryPerkStyleName"][pageIndex]
                secondaryPerkStyleId: int = recommendedPage_df["secondaryPerkStyleId"][pageIndex]
                secondaryRecommendationAttribute: str = recommendedPage_df["secondaryRecommendationAttribute"][pageIndex]
                keystoneId: int = recommendedPage_df["keystone id"][pageIndex]
                keystoneName: str = recommendedPage_df["keystone name"][pageIndex]
                perkIds: list[str] = recommendedPage_df["perkIds"][pageIndex]
                perkNames: list[str] = recommendedPage_df["perkNames"][pageIndex]
                logPrint("主系（Style）：%s (%d)\t%s\n副系（Substyle）：%s (%d)\t%s\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, primaryRecommendationAttribute, secondaryPerkStyleName, secondaryPerkStyleId, secondaryRecommendationAttribute, keystoneName, keystoneId, perkIds, perkNames))
                logPrint("是否导出推荐符文信息？（输入任意键导出，否则不导出。）\nExport recommended page information? (Submit any non-empty string to export, or null to refuse exporting.)")
                page_export_str: str = logInput()
                page_export: bool = bool(page_export_str)
                if page_export:
                    recommendedPage_json: dict[str, Any] = {"name": "%s - %s" %(championName, keystoneName), "isTemporary": True, "primaryStyleId": primaryPerkStyleId, "secondaryStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                    logPrint("请选择导出方式：\nPlease select a way to export:\n1\t写入文件（Write into a file）\n2\t复制到剪贴板（Copy to clipboard）")
                    while True:
                        export_method: str = logInput()
                        if export_method == "":
                            continue
                        elif export_method[0] == "0":
                            break
                        elif export_method[0] == "1":
                            json1name: str = "Recommended Page.json"
                            with open(json1name, "w", encoding = "utf-8") as fp:
                                json.dump(recommendedPage_json, fp, ensure_ascii = False)
                            logPrint('%s的推荐符文信息已导出到同目录下的“%s”中。\nRecommended perk page of %s has been exported into "%s" under the same folder.' %(championName, json1name, championAlias, json1name))
                            break
                        elif export_method[0] == "2":
                            try:
                                pyperclip.copy(json.dumps(recommendedPage_json, ensure_ascii = False))
                            except: #在执行极致压缩任务时，可能导致剪贴板操作失败（When the user is performing an extreme compression task, clipboard operations might fail）
                                traceback_info = traceback.format_exc()
                                logPrint(traceback_info)
                                logPrint("推荐符文信息复制失败。\nRecommended perk page copy failed.")
                            else:
                                logPrint('%s的推荐符文信息已复制到剪贴板中。\nRecommended perk page of %s has been copied to clipboard.' %(championName, championAlias))
                            break
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                logPrint('选择下方的一个方案以查看详细信息。输入“0”以返回上一层。\nSelect a page to check the details. Submit "0" to return to the last step.')
                print(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], print_index = True)[0])
                log.write(format_df(recommendedPage_df.loc[:, recommendedPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input. Please try again.")

def export_all_perkPages(perkPage_df: pandas.DataFrame, displayName: str, folder: str) -> None:
    '''
    将用户的所有符文配置导出到工作簿中。<br>Export the user's all perk configuration into a workbook.
    
    :param perkPage_df: 符文页数据框。<br>Perk page dataframe.
    :type perkPage_df: pandas.DataFrame
    :param displayName: 工作簿命名中的召唤师名称部分。<br>The summoner name part in the name of the workbook.
    :type displayName: str
    :param folder: 工作簿的导出目录。<br>Export directory of the workbook.
    :type folder: str
    '''
    excel_name: str = f"Player Perk Pages - {displayName}.xlsx"
    wbPath: str = os.path.join(folder, excel_name).replace("\\", "/")
    os.makedirs(folder, exist_ok = True)
    if not os.path.exists(wbPath):
        wbCreateFlag: bool = create_workbook_win32(os.path.abspath(wbPath))
    workbook_exist: bool = os.path.exists(wbPath)
    while True:
        try:
            with (pandas.ExcelWriter(path = wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(path = wbPath)) as writer:
                currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(time.time()))
                addDefaultStyle(perkPage_df).to_excel(excel_writer = writer, sheet_name = f"Perk Page - {currentTime}")
        except PermissionError:
            logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
            logInput()
        else:
            logPrint('玩家符文页信息已保存为“%s”。\nPlayer perk page information is saved as "%s".' %(wbPath, wbPath))
            break

def set_perks_successively(page_body: dict[str, Any]) -> int:
    '''
    按照步骤设置一个符文页。<br>Set a perk page following steps.
    
    :param page_body: 符文页主体。修改将在此参数上进行。<br>Perk page body. Modification will be made on this parameter.
    :type page_body: dict[str, Any]
    :return: 步骤数。<br>Step number.
    
        步骤数的作用类似于状态码。当步骤数为0时，表示用户取消操作；否则表示操作完成。<br>The role of step number resembles a status code. When step is 0, it means the user has cancelled this operation. Otherwise, the operation is finished.
    :rtype: int
    '''
    logPrint('在下面的步骤中，请确保输入的是正整数类型的符文系序号和符文序号。输入“0”以撤回最近一次输入。\nDuring the following steps, please make sure you submit the perkStyleId and perkId of integer type. Submit "0" to revert the latest input.')
    allowedSubStyles: list[int] = []
    step: int = 1
    while True: #客户端内配置符文页需要11个步骤（Setting a perk page in the League Client needs 11 steps）
        parameter_dict: dict[int, int] = {} #将用户输入的序号映射到符文系序号和符文序号。用户也可以直接输入原始序号（Map user input to the perkstyleIds and perkIds. The user may input the raw ids）
        #设置输出提示（Set up the output hint）
        if step == 0:
            break
        elif step == 1:
            tooltip: str = f"第{step}步：请选择主系。\nStep {step}: Please select a primary perkstyle."
            primaryStyleIds: list[int] = sorted(perkstyles.keys())
            perkTableStr: str = ""
            for i in range(len(primaryStyleIds)):
                styleId: int = primaryStyleIds[i]
                parameter_dict[i + 1] = styleId
                perkTableStr += "\n#%d\t%d\t%s" %(i + 1, styleId, perkstyles[styleId]["name"])
        elif step == 2:
            tooltip = f"第{step}步：请选择基石。\nStep {step}: Please select a keystone."
            perkTableStr = ""
            if page_body["primaryStyleId"] in perkstyles:
                slotPerks: list[int] = perkstyles[page_body["primaryStyleId"]]["slots"][step - 2]["perks"]
                for i in range(len(slotPerks)):
                    perkId: int = slotPerks[i]
                    parameter_dict[i + 1] = perkId
                    perkTableStr += "\n#%d\t%d\t%s" %(i + 1, perkId, perks[perkId]["name"])
        elif step <= 5:
            perkTableStr = ""
            if page_body["primaryStyleId"] in perkstyles:
                slotLabel: str = perkstyles[page_body["primaryStyleId"]]["slots"][step - 2]["slotLabel"]
                slotPerks: list[int] = perkstyles[page_body["primaryStyleId"]]["slots"][step - 2]["perks"]
                for i in range(len(slotPerks)):
                    perkId = slotPerks[i]
                    parameter_dict[i + 1] = perkId
                    perkTableStr += "\n#%d\t%d\t%s" %(i + 1, perkId, perks[perkId]["name"])
            else:
                slotLabel = "主系第%d行符文" %(step - 2)
            tooltip = f"第{step}步：请选择{slotLabel}符文。\nStep {step}: Please select a {slotLabel} perk."
        elif step == 6:
            tooltip = f"第{step}步：请选择副系。\nStep {step}: Please select a secondary perkstyle."
            perkTableStr = ""
            if page_body["primaryStyleId"] in perkstyles:
                allowedSubStyles = perkstyles[page_body["primaryStyleId"]]["allowedSubStyles"]
                for i in range(len(allowedSubStyles)):
                    styleId: int = allowedSubStyles[i]
                    parameter_dict[i + 1] = styleId
                    perkTableStr += "\n#%d\t%d\t%s" %(i + 1, styleId, perkstyles[styleId]["name"])
        elif step <= 8:
            substyle: str = perkstyles[page_body["subStyleId"]]["name"] if page_body["subStyleId"] in perkstyles else "副系"
            tooltip = f"第{step}步：请选择一个{substyle}符文。\nStep {step}: Please select a {substyle} perk."
            perkTableStr = ""
            if page_body["primaryStyleId"] in perkstyles and page_body["subStyleId"] in allowedSubStyles:
                j = 0
                for i in range(1, 4):
                    slotLabel = perkstyles[page_body["subStyleId"]]["slots"][i]["slotLabel"]
                    perkTableStr += "\n%s:" %(slotLabel)
                    slotPerks = perkstyles[page_body["subStyleId"]]["slots"][i]["perks"]
                    for perkId in slotPerks:
                        j += 1
                        parameter_dict[j] = perkId
                        perkTableStr += "\n#%d\t%d\t%s" %(j, perkId, perks[perkId]["name"])
        elif step <= 11:
            slotLabel = perkstyles_source["styles"][0]["slots"][step - 5]["slotLabel"] #这里的“0”可以换成1～4之间的任意正整数，因为所有符文系的后三个小符文信息都是一样的（Here the "0" can be replaced by any integer between 1 and 4, for the last three stat mods in all perkstyles are the same）
            slotPerks = perkstyles_source["styles"][0]["slots"][step - 5]["perks"]
            tooltip = f"第{step}步：请选择{slotLabel}属性。\nStep {step}: Please select a {slotLabel} stat mod."
            perkTableStr = ""
            for i in range(len(slotPerks)):
                perkId = slotPerks[i]
                parameter_dict[i + 1] = perkId
                perkTableStr += "\n#%d\t%d\t%s" %(i + 1, perkId, perks[perkId]["name"])
        elif step == 12:
            break
        else:
            logPrint("步骤异常。请联系开发人员修复程序。\nStep error. Please contact the developer to fix the program.")
            return 0
        logPrint(tooltip + perkTableStr)
        #输入参数（Input the parameter）
        while True:
            parameter: int = 0
            parameter_got: bool = False
            parameter_str: str = logInput()
            if parameter_str == "":
                continue
            elif parameter_str == "0":
                step -= 2
                break
            else:
                try:
                    parameter: int = int(parameter_str) #这里除了要求输入是整数外，没有其它要求。这也就意味着，逐个修改允许配置不可用的符文页（There's not any other restraints besides the input is an integer, which means successive input allows invalid perk pages）
                except ValueError:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                else:
                    if parameter in parameter_dict:
                        parameter = parameter_dict[parameter]
                    parameter_got = True
                    break
        if parameter_got:
            if step == 1:
                page_body["primaryStyleId"] = parameter
            elif step <= 5:
                page_body["selectedPerkIds"][step - 2] = parameter
            elif step == 6:
                page_body["subStyleId"] = parameter
            else:
                page_body["selectedPerkIds"][step - 3] = parameter
        step += 1
    return step

def verify_perkIds(perkIds: Any) -> bool:
    '''
    检验符文序号列表合法性的一个标准函数。<br>A standard function that verifies the validity of the perkId list.
    
    :param perkIds: 符文序号列表。
    :type perkIds: list[int]
    :return: 符文序号列表是否合法。<br>Whether the passed perkId list is legal.
    :rtype: bool
    '''
    keystoneIds: list[int] = [perk["id"] for perk in perks_source if perk["slotType"] == "kKeyStone"] #提取基石序号列表，用于判断基石的正确性（Extract the list of keystone ids to judge the keystone's correctness）
    statmodIds: list[int] = [perk["id"] for perk in perks_source if perk["slotType"] == "kStatMod"] #提取属性符文序号列表，用于判断基石的正确性（Extract the list of stat mod ids to judge the keystone's correctness）
    perkMap: dict[int, dict[str, Any]] = {} #建立一个由符文对应到所属符文页的对应关系，并从符文页信息中提取每个符文的槽位类型和槽位名称（Build a map from perks to the belonging perkstyles and extract each perk's slot type and slot label from perkstyle information）
    for style in perkstyles_source["styles"]:
        for slot in style["slots"]:
            for perkId in slot["perks"]:
                perkMap[perkId] = {"styleId": perks[perkId]["styleId"], "slotType": slot["type"], "slotLabel": slot["slotLabel"]}
    perkIds_valid: bool = True
    if isinstance(perkIds, list) and all(map(lambda x: isinstance(x, int) and x in perks.keys(), perkIds)):
        uiPerksIds: list[int] = perkIds
        if len(uiPerksIds) >= 9:
            uiPerksIds = uiPerksIds[:9] #正确的请求主体中，符文序号列表长度为9。因此如果用户输入长度超过9的列表，将被自动截断（In a correct request body, the length of the perkId list is 9. Therefore, if the user submits a list with length over 9, this list will be taken a slice automatically）
            if uiPerksIds[0] in keystoneIds: #首先判断基石的正确性（First, check the keystone correctness）
                primaryStyle: dict[str, Any] = perkstyles[perks[uiPerksIds[0]]["styleId"]] #在基石正确的情况下，推断出主系（If the keystone is correct, infer the primary style）
                for i in range(1, 4): #判断基石后三个符文是否都能对应到主系的三个槽位（Judge whether the three perks after keystone can correspond to the three slots of the primary style, respectively）
                    slot: dict[str, Any] = perkstyles[primaryStyle["id"]]["slots"][i]
                    if not uiPerksIds[i] in slot["perks"]:
                        perkIds_valid = False
                        logPrint("%s系的%s符文中不包含%s（%d）。\n%s (%d) doesn't exist in the %s slot of %s style." %(primaryStyle["name"], slot["slotLabel"], perks[uiPerksIds[i]]["name"], uiPerksIds[i], perks[uiPerksIds[i]]["name"], uiPerksIds[i], slot["slotLabel"], primaryStyle["name"]))
                #下面检验副系的两个符文。副系的检验依赖于主系的确定，因为涉及到主系的合法副系的判断，因此这一段代码置于基石正确性判断的if条件语句块内（Second, check the correctness of two perks in the substyle. Check on the substyle depends on the confirmation of the primary style, for it involves the allowed substyle of a primary style. Therefore, the following code are under the if-statement that check the keystone correctness）
                ##首先针对其所属符文系展开检验（First, perform tests on their belonging perkstyles）
                if not perkMap[uiPerksIds[4]]["styleId"] in perkstyles[primaryStyle["id"]]["allowedSubStyles"]: #检验副系第一个符文所属符文系是否是主系的合法副系（Check whether the first perk of substyle is a legal substyle of the primary style）
                    perkIds_valid = False
                    logPrint("%s（%d）所属符文系（%d）不是主系%s（%d）的合法副系。\nThe belonging style (%d) of %s (%d) isn't an allowed substyle for primary style %s (%d)." %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perkMap[uiPerksIds[4]]["styleId"], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"], perkMap[uiPerksIds[4]]["styleId"], perks[uiPerksIds[4]]["name"], uiPerksIds[4], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"]))
                if not perkMap[uiPerksIds[5]]["styleId"] in perkstyles[primaryStyle["id"]]["allowedSubStyles"]: #检验副系第二个符文所属符文系是否是主系的合法副系（Check whether the second perk of substyle is a legal substyle of the primary style）
                    perkIds_valid = False
                    logPrint("%s（%d）所属符文系（%d）不是主系%s（%d）的合法副系。\nThe belonging style (%d) of %s (%d) isn't an allowed substyle for primary style %s (%d)." %(perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[5]]["styleId"], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"], perkMap[uiPerksIds[5]]["styleId"], perks[uiPerksIds[5]]["name"], uiPerksIds[5], primaryStyle["name"], perks[uiPerksIds[0]]["styleId"]))
                if perkMap[uiPerksIds[4]]["styleId"] != perkMap[uiPerksIds[5]]["styleId"]:
                    perkIds_valid = False
                    logPrint("%s（%d）所属符文系（%d）和%s（%d）所属符文系（%d）不相同。\n%s (%d) and %s (%d) have different belonging perkstyles (%d and %d)." %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perkMap[uiPerksIds[4]]["styleId"], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[5]]["styleId"], perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[4]]["styleId"], perkMap[uiPerksIds[5]]["styleId"]))
                ##在迄今为止副系的两个符文所属符文系合法——两个符文所属符文系相同，且是主系的合法副系——的情况下，接下来对其槽位展开检验（When the belonging perkstyles of the two substyle perks are legal, that is, these two perks belong to one style and this style is an allowed substyle of the primary style, perform tests on these two perks' slots）
                if perkIds_valid: #该条件等价于（This condition is equivalent to）`perkMap[uiPerksIds[4]]["styleId"] == perkMap[uiPerksIds[5]]["styleId"] and perkMap[uiPerksIds[4]]["styleId"] in perkstyles[primaryStyle["id"]]["allowedSubStyles"]`
                    ##注意：在上面的符文对应关系字典中，属性符文也被包含在内。虽然会有多个符文系包含同一套属性符文的问题，但是这里只对副系的两个符文进行检验，所以该字典中关于属性符文的问题在这里是无关紧要的（Note: In the `perkMap` dictionary, stat mods are included. Despite the fact that multiple perkstyles contain a same set of stat mods, here the test is performed only on the two perks of the substyle, so the stat mod issue here is insignificant）
                    if perkMap[uiPerksIds[4]]["slotType"] != "kMixedRegularSplashable": #检验副系第一个符文是不是基石和属性之外的符文（Check whether the first perk of the substyle is of "kMixedRegularSplashable" type）
                        perkIds_valid = False
                        logPrint('''%s（%d）所属槽位类型不是符文。\nThe slot type of %s (%d) isn't "kMixedRegularSplashable".''' %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[4]]["name"], uiPerksIds[4]))
                    if perkMap[uiPerksIds[5]]["slotType"] != "kMixedRegularSplashable": #检验副系第二个符文是不是基石和属性之外的符文（Check whether the second perk of the substyle is of "kMixedRegularSplashable" type）
                        perkIds_valid = False
                        logPrint('''%s（%d）所属槽位类型不是符文。\nThe slot type of %s (%d) isn't "kMixedRegularSplashable".''' %(perks[uiPerksIds[5]]["name"], uiPerksIds[5], perks[uiPerksIds[5]]["name"], uiPerksIds[5]))
                    if perkMap[uiPerksIds[4]]["slotLabel"] == perkMap[uiPerksIds[5]]["slotLabel"]: #检验副系的两个符文的槽位是否相同（Check whether two slot labels of the two perks of the substyle are the same）
                        perkIds_valid = False
                        logPrint("%s（%d）和%s（%d）具有相同的槽位（%s）。\n%s (%d) and %s (%d) has the same slot label (%s)." %(perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[4]]["slotLabel"], perks[uiPerksIds[4]]["name"], uiPerksIds[4], perks[uiPerksIds[5]]["name"], uiPerksIds[5], perkMap[uiPerksIds[4]]["slotLabel"]))
            else:
                perkIds_valid = False
                logPrint("%s（%d）不是基石符文。\n%s (%d) isn't a keystone." %(perks[uiPerksIds[0]]["name"], uiPerksIds[0], perks[uiPerksIds[0]]["name"], uiPerksIds[0]))
            #最后检验属性符文。属性符文和主系和副系都是独立的，因此其缩进回调一个单位（Finally, check the stat mods. Stat mods are indenpendent from both primary style and substyle, so the indentation is decreased by one unit）
            ##回到上面的符文对应关系字典。它具体存在的问题是，由于多个符文系都存在这些属性符文，而每个属性符文的符文系序号、槽位名称和槽位类型是由遍历符文系产生的，因此每个属性符文的这些信息都会是最后一个被遍历的符文系的这些信息。实际上，这对于后续判断也没有影响。首先，属性符文和主系和副系都是独立的，压根儿就不会用上其符文系序号这个信息。其次，虽然多个符文系包含这些属性符文，但是这些属性符文的槽位名称和槽位类型在这些符文系中是相同的，所以无论采用哪个符文系的信息都无所谓（Back to previous `perkMap` dictionary. The detailed issue is, multiple perkstyles contain these stat mods, so given that the perkstyleId, slot label and slot type of each stat mod is obtained by traversing the perkstyles, these information is actually from the perkstyle traversed. But in fact, this issue shouldn't affact the subsequent judgments. On the one hand, stat mods are indenpendent from both primary style and substyle, and their styleIds will never be regarded as useful. On the other hand, although these statmods are contained in multiple perkstyles, their slot labels and slot types recorded in the perkstyles are same, so it doesn't matter which perkstyle is used）
            for i in range(6, 9):
                if not uiPerksIds[i] in statmodIds: #首先判断第7～9个符文是不是属性符文（First, judge whether the 7th to 9th perks are stat mods）
                    perkIds_valid = False
                    logPrint("%s（%d）不是属性符文。\n%s (%d) isn't a stat mod." %(perks[uiPerksIds[i]]["name"], uiPerksIds[i], perks[uiPerksIds[i]]["name"], uiPerksIds[i]))
                elif perkMap[uiPerksIds[i]]["slotLabel"] != perkstyles_source["styles"][0]["slots"][i - 2]["slotLabel"]: #然后判断这些属性符文是不是对应行的。这里有两点：第一，之所以用elif不是if，是因为上面的perkMap的数据来源是符文系，而符文系相比符文少了一些符文信息，上面的判断过程也没有排除这些少的符文信息，所以如果直接用if的话，当用户输入的是这部分少的符文的序号时，会引发perkMap的键错误；第二，既然前面提到属性符文的槽位名称和槽位类型在符文系中都是相同的，所以这里直接默认使用了第一个符文系（Next, judge whether the stat mods have the corresponding slot labels. Here're two points worth mentioning. First, the reason why "elif" instead of "if" is used here is that data in the previous `perkMap` dictionary are (traversed) from perkstyles, which don't collect all perks. These extra perks aren't excluded during the previous steps, so if an "if" is used here, when the user inputs these extra perks' ids, a KeyError will occurred to `perkMap`. Second, now that slot names and slot types of stat mods in different perkstyles are the same, here the first perkstyle is used by default）
                    perkIds_valid = False
                    logPrint("%s（%d）不是%s类属性符文。\n%s (%d) isn't a stat mod of %s type." %(perks[uiPerksIds[i]]["name"], uiPerksIds[i], perkMap[uiPerksIds[i]]["slotLabel"], perks[uiPerksIds[i]]["name"], uiPerksIds[i], perkMap[uiPerksIds[i]]["slotLabel"]))
            else:
                perkIds_valid = True
        else:
            perkIds_valid = False
            logPrint("您输入的符文数量过少！请输入由9个符文序号组成的列表。\nPerk number not enough! Please submit a list composed of 9 perkIds.")
    else:
        perkIds_valid = False
        logPrint("您的输入格式有误！请输入一个由符文序号正整数组成的列表。\nERROR format! Please submit a list composed of perkIds of integer type.")
    return perkIds_valid

async def change_perkPage_name(connection: Connection, page_body: dict[str, Any], page_exist: bool, old_pageName: str = "", skip_ask: bool = False, verify: bool = False) -> bool:
    '''
    修改符文页名称。<br>Change the name of a perk page.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param page_body: 修改符文页请求主体。修改将在此参数上进行。<br>The request body to edit a perk page. Modification will be made on this parameter.
    :type page_body: dict[str, Any]
    :param page_exist: 符文页是否存在。决定了是创建符文页还是修改符文页。<br>Whether this perk page already exists, which determines the program will create or edit a perk page downstream.
    :type page_exist: bool
    :param old_pageName: 旧符文页名称。如果未指定，则视为用户正在创建符文页。<br>Old page name. If it's unspecified, the function wil regard the user is creating a page.
    
        该参数本可以替换为符文页序号，这样旧符文页名称可直接通过接口获取，这样设计似乎更加符合直觉。但是这样的话，需要在函数体内另外声明符文页不存在时的异常处理，而这在外部已经声明了。而且，引入接口还会导致更多的类型检查错误。所以为了简约起见，这里要求用户手动传入旧符文页名称。<br>This parameter could have been replaced with some other parameter like "pageId", so that the old name could have been obtained by simply accessing the API, which feels more intuitive than what it is now. But in that case, I would have to implement the exception handling about page not found inside the function, which now has been implemented outside. Besides, introducing API will result in more type checking errors. Anyway, to make this function as simple as possible, "old_pageName" is used here.
    :type old_pageName: str
    :param skip_ask: 跳过修改符文页的询问，直接开始输入新符文页的名称。默认为假。<br>Skip asking whether to change the perk page and start inputting the new page name directly. False by default.
    :type skip_ask: bool
    :param verify: 是否验证符文页名称合法性。默认为否。<br>Whether to verify the name validity of the perk page. False by default.
    :type verify: bool
    '''
    if page_exist:
        if skip_ask:
            pageNameChange: bool = True
        else:
            logPrint("是否需要修改符文页名称？（输入任意键修改，否则不修改。）\nDo you want to change the page name? (Submit any non-empty string to change, or null to stop changing.)")
            pageNameChange_str: str = logInput()
            pageNameChange = bool(pageNameChange_str)
        if pageNameChange:
            logPrint("请输入符文页的新名称：\nPlease enter the new name of this perk page:")
    else:
        pageNameChange = True
        logPrint("请输入新符文页的名称：\nPlease enter the name of the new perk page:")
    if pageNameChange:
        if verify:
            while True:
                new_pageName: str = logInput()
                if new_pageName == chr(4):
                    new_pageName = old_pageName
                    break
                #检验符文页名称有效性的接口依赖于一个具体的符文页。这需要针对用户是否有符文页进行讨论（The endpoint to validate the page name depends on a specific perk page. This introduces the discussion about whether the user has one perk page）
                perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                dummy_page_created: bool = False
                if len(perkPages) == 0: #如果用户没有符文页，则创建一个占位符文页。目的只是为了拿到一个具体的符文页序号（If the user doesn't have any perk page, create one. The aim is only to get a perk page id）
                    dummy_page_body: dict[str, Any] = {"name": "占位符文页", "isTemporary": True, "primaryStyleId": -1, "subStyleId": -1, "selectedPerkIds": [-1, -1, -1, -1, -1, -1, -1, -1, -1]}
                    response: dict[str, Any] = await (await connection.request("POST", "/lol-perks/v1/pages", data = dummy_page_body)).json()
                    logPrint(response)
                    if "errorCode" in response:
                        logPrint(response)
                        logPrint("符文页名称有效性验证失败。将不再验证符文页名称有效性。\nPerk page name validation failed. This name won't be validated this time.")
                        break
                    else:
                        dummy_page_created = True
                        dummy_pageId: int = response["id"]
                        validate_body: dict[str, int | str] = {"id": response["id"], "name": new_pageName}
                else: #如果用户有符文页，则使用第一个符文页的序号。这不会对第一个符文页产生影响（If the user has a perk page, use the id of the first page. This won't cause any change to it）
                    validate_body = {"id": perkPages[0]["id"], "name": new_pageName}
                response: dict[str, Any] = await (await connection.request("PUT", "/lol-perks/v1/pages/validate", data = validate_body)).json()
                logPrint(response)
                if "errorCode" in response:
                    logPrint(response)
                    logPrint("符文页名称有效性验证失败。将不再验证符文页名称有效性。\nPerk page name validation failed. This name won't be validated this time.")
                    break
                else:
                    if response["success"]:
                        logPrint("符文页名称通过验证。\nNew page name passed validation.")
                        if dummy_page_created:
                            response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/lol-perks/v1/pages/{dummy_pageId}")).json()
                            logPrint(response)
                            if response != None:
                                logPrint(response)
                                logPrint("占位符文页删除失败。请自行在客户端内删除。\nDummy perk page failed to be deleted. Please delete it by yourself.")
                        break
                    else:
                        if "DISABLED" in response["nameCheckResponse"]["errors"]:
                            logPrint("不能更改。\nPage can't be renamed.")
                        if "INAPPROPRIATE" in response["nameCheckResponse"]["errors"]:
                            logPrint("名字不适当。\nName is inappropriate.")
                        if "INVALID_CHAR" in response["nameCheckResponse"]["errors"]:
                            logPrint("名字有无效字符。\nName has invalid characters.")
        else:
            new_pageName: str = logInput()
    else:
        new_pageName = old_pageName
    if page_exist:
        if old_pageName != new_pageName:
            logPrint("输入任意非空字符串以确认修改，否则取消修改。\nSubmit any non-empty string to confirm changing, or null to cancel.\n旧名称（Old）：%s\n新名称（New）：%s" %(old_pageName, new_pageName))
            pageName_change_confirm_str: str = logInput()
            pageName_change_confirm: bool = bool(pageName_change_confirm_str)
        else:
            pageName_change_confirm = False
        page_body["name"] = new_pageName if pageName_change_confirm else old_pageName
    else:
        page_body["name"] = new_pageName
    return page_body["name"] != old_pageName

def input_perkPage_body() -> dict[str, Any]:
    '''
    通过用户输入读取编辑/创建符文页的请求主体。<br>Read the request body to edit / create a perk page from user input.
    
    支持Python字典的格式和json格式。<br>Both Python dictionary format and json format are supported.
    
    :return: 读取到的符文页请求主体。在取消操作时，返回一个空结构。<br>Loaded perk page request body. When this operation is cancelled, the function will return an empty struct.
    :rtype: dict[str, Any]
    '''
    logPrint('请在单行内输入包含新符文页信息的字典或Json代码：\nPlease input a Python dictionary or a piece of Json code that represents the new perk page information in a single line:\n示例（Examples）：\nPython字典（Python dictionary）：\n{"name": "无极剑圣 - 致命节奏", "isActive": False, "isTemporary": True, "primaryStyleId": 8000, "secondaryStyleId": 8300, "selectedPerkIds": [8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]}\nJson：\n{"name": "无极剑圣 - 致命节奏", "isActive": false, "isTemporary": true, "primaryStyleId": 8000, "secondaryStyleId": 8300, "selectedPerkIds": [8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]}')
    while True:
        page_body_str: str = logInput()
        if page_body_str == "":
            continue
        elif page_body_str[0] == "0":
            page_body: dict[str, Any] = {}
            break
        else:
            try:
                page_body: dict[str, Any] = json.loads(page_body_str)
            except json.decoder.JSONDecodeError:
                traceback_info = traceback.format_exc()
                logPrint(traceback_info)
                try:
                    page_body = eval(page_body_str)
                except:
                    traceback_info = traceback.format_exc()
                    logPrint(traceback_info)
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                else:
                    break
            else:
                break
    return page_body

def import_perkPage_body() -> dict[str, Any]:
    '''
    通过用户输入读取编辑/创建符文页的请求主体。<br>Read the request body to edit / create a perk page from user input.
    
    文件内容必须符合json格式。<br>File content must follow the standard json format.
    
    :return: 读取到的符文页请求主体。在取消操作时，返回一个空结构。<br>Loaded perk page request body. When this operation is cancelled, the function will return an empty struct.
    :rtype: dict[str, Any]
    '''
    logPrint('请输入以Json格式存储新符文页信息的文件路径。输入“0”以返回上一层。\nPlease submit the path of the file that stores the new perk page information in Json format. Submit "0" to return to the last step.')
    while True:
        page_body_path: str = logInput()
        if page_body_path == "":
            continue
        elif page_body_path == "0":
            page_body: dict[str, Any] = {}
            break
        else:
            if os.path.exists(page_body_path):
                logPrint("您输入的路径不存在！请重新输入。\nFile not found! Please try again.")
            else:
                try:
                    with open(page_body_path, "r", encoding = "utf-8") as fp:
                        page_body = json.load(fp)
                except json.decoder.JSONDecodeError:
                    traceback_info = traceback.format_exc()
                    logPrint(traceback_info)
                    logPrint("文件格式错误！请检查文件格式或使用其它文件。\nERROR format! Please check the file format or use another file.")
                else:
                    break
    return page_body

async def edit_perkPage(connection: Connection) -> None:
    '''
    编辑一个符文页。由此进入各个编辑选项。<br>Edit a perk page. Entry to each edit option.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    logPrint('请选择一个符文页：（输入索引范围之外的整数则创建一个新的符文页。）\nPlease select a page: (Enter an integer beyong the index range to create a new page.)')
    perkPage_df: pandas.DataFrame = await get_perk_page(connection)
    perkPage_df_fields_to_print: list[str] = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
    print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
    log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
    while True:
        pageIndex: int = 0
        page_exist: bool = False
        pageIndex_str: str = logInput()
        if pageIndex_str == "":
            continue
        elif pageIndex_str == "0":
            break
        else:
            try:
                pageIndex: int = int(pageIndex_str)
            except ValueError:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            else:
                page_exist = pageIndex >= 1 and pageIndex < len(perkPage_df)
        if page_exist:
            pageId: int = perkPage_df["id"][pageIndex]
            pageName: str = perkPage_df["name"][pageIndex]
            isTemporary: bool = perkPage_df["isTemporary"][pageIndex] == "√"
            primaryPerkStyleName: str = perkPage_df["primaryStyleName"][pageIndex]
            primaryPerkStyleId: int = perkPage_df["primaryStyleId"][pageIndex]
            secondaryPerkStyleName: str = perkPage_df["secondaryStyleName"][pageIndex]
            secondaryPerkStyleId: int = perkPage_df["subStyleId"][pageIndex]
            keystoneId: int = perkPage_df["pageKeystone id"][pageIndex]
            keystoneName: str = perkPage_df["pageKeystone name"][pageIndex]
            perkIds: list[int] = perkPage_df["selectedPerkIds"][pageIndex]
            perkNames: list[str] = perkPage_df["uiPerksNames"][pageIndex]
            logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
            logPrint("是否编辑该符文页？（输入任意键以确认，否则放弃编辑。）\nDo you want to edit this perk page? (Submit any non-empty string to confirm, or null to decline editing.)")
            page_edit_str: str = logInput()
            page_edit: bool = bool(page_edit_str)
        else:
            pageId = -1
            pageName = ""
            primaryPerkStyleId = 0
            secondaryPerkStyleId = 0
            perkIds = []
            page_edit = True
            perkInventory: dict[str, Any] = await (await connection.request("GET", "/lol-perks/v1/inventory")).json() #这个接口返回的信息中，自定义符文页可解锁似乎是一直是可用的（In the result returned by this endpoint, the "isCustomPageCreationUnlocked" seems always to be True）
            if not perkInventory["canAddCustomPage"]:
                logPrint("符文页栏位已满。删除或拥有更多符文页以创建新的符文页。程序将创建临时符文页。\nInventory full. Delete or obtain more pages to create more. The program is going to create a temporary perk page.")
                isTemporary = True
            else:
                isTemporary = False
        response: dict[str, Any] = {}
        if page_edit:
            logPrint("请选择编辑方式：\nPlease select a method of:\n0\t放弃修改（Quit editing）\n1\t逐个修改（Successively）\n2\t批量修改（In batch）\n3\t仅重命名（Rename only）\n4\t读取Json数据（From json data）\n5\t读取文件（From a file）")
            while True:
                page_body: dict[str, Any] = {"name": "", "isTemporary": isTemporary, "primaryStyleId": -1, "subStyleId": -1, "selectedPerkIds": [-1, -1, -1, -1, -1, -1, -1, -1, -1]} #请求主体初始化（Initialize the request body）
                method = logInput()
                if method == "":
                    continue
                elif method[0] == "0":
                    page_edit = False
                    break
                elif method[0] == "1": #保持与客户端符文配置步骤相同（Keep synchronized with the latest perk configuration steps in the League Client）
                    step: int = set_perks_successively(page_body)
                    page_edit = step != 0
                    if page_edit:
                        await change_perkPage_name(connection, page_body, page_exist, old_pageName = pageName)
                elif method[0] == "2":
                    logPrint("请输入一个由符文序号组成的列表。\nPlease input a list composed of perkIds.\n例如（Example）：[8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]")
                    while True:
                        uiPerksStr: str = logInput()
                        if uiPerksStr == "":
                            continue
                        elif uiPerksStr[0] == "0":
                            page_edit = False
                            break
                        else:
                            try:
                                tmp = eval(uiPerksStr)
                            except:
                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                            else:
                                #下面对uiPerksIds展开重重检验，确保生成的是有效的符文页（The following code perform continuous tests on `uiPerksIds` to ensure that a valid perk page will be generated）
                                perkIds_valid = verify_perkIds(tmp)
                                if perkIds_valid: #前面的检验都通过，则用户输入的符文序号列表是合法的（If all the previous tests are passed, then the perkId list is valid）
                                    uiPerksIds: list[int] = tmp
                                    page_body["primaryStyleId"] = perks[uiPerksIds[0]]["styleId"]
                                    page_body["substyleId"] = perks[uiPerksIds[4]]["styleId"] #第4个和第5个符文的所属符文系是相同的，这里默认使用了第4个（The 4th and 5th perks have the same belonging perkstyles. Here the 4th's is used）
                                    page_body["selectedPerkIds"] = uiPerksIds
                                    #设置符文页的名称（Set the perk page name）
                                    await change_perkPage_name(connection, page_body, page_exist, old_pageName = pageName, verify = True)
                                    break
                elif method[0] == "3":
                    page_body = {"name": pageName, "isTemporary": isTemporary, "primaryStyleId": primaryPerkStyleId, "subStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                    if page_exist:
                        page_edit = await change_perkPage_name(connection, page_body, True, old_pageName = pageName, skip_ask = True)
                    else:
                        logPrint("未创建的符文页不支持该操作。\nA perk page that hasn't been created doesn't support this method.")
                        page_edit = False
                elif method[0] == "4":
                    page_body = input_perkPage_body()
                    page_edit = bool(page_body)
                elif method[0] == "5":
                    page_body = import_perkPage_body()
                    page_edit = bool(page_body)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                if page_edit:
                    if page_exist:
                        response: dict[str, Any] = await (await connection.request("PUT", f"/lol-perks/v1/pages/{pageId}", data = page_body)).json()
                        logPrint(response)
                        if "errorCode" in response:
                            logPrint("符文页编辑失败。\nFailed to edit this perk page.")
                        else:
                            logPrint("符文页编辑成功。\nPerk page is edited successfully.")
                    else:
                        response: dict[str, Any] = await (await connection.request("POST", "/lol-perks/v1/pages", data = page_body)).json()
                        logPrint(response)
                        if "errorCode" in response:
                            logPrint("符文页创建失败。\nFailed to add this perk page.")
                        else:
                            logPrint("符文页创建成功。\nPerk page is added successfully.")
                    if not "errorCode" in response:
                        pageId = response["id"]
                        pageName = response["name"]
                        primaryPerkStyleName = response["primaryStyleName"]
                        primaryPerkStyleId = response["primaryStyleId"]
                        secondaryPerkStyleName = response["secondaryStyleName"]
                        secondaryPerkStyleId = response["subStyleId"]
                        keystoneId = response["pageKeystone"]["id"]
                        keystoneName = response["pageKeystone"]["name"]
                        perkIds = response["selectedPerkIds"]
                        perkNames = list(map(lambda x: x["name"], response["uiPerks"]))
                        logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
                    break
                logPrint("请选择编辑方式：\nPlease select a method of:\n0\t放弃修改（Quit editing）\n1\t逐个修改（Successively）\n2\t批量修改（In batch）\n3\t仅重命名（Rename only）\n4\t读取Json数据（From json data）\n5\t读取文件（From a file）")
        if page_exist or page_edit and not "errorCode" in response:
            logPrint("是否导出该符文页？（输入任意键以确认，否则放弃导出。）\nDo you want to export this perk page? (Submit any non-empty string to confirm, or null to decline exporting.)")
            page_export_str: str = logInput()
            page_export: bool = bool(page_export_str)
            if page_export:
                perkPage_json: dict[str, Any] = {"name": pageName, "isTemporary": isTemporary, "primaryStyleId": primaryPerkStyleId, "secondaryStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                logPrint("请选择导出方式：\nPlease select a way to export:\n1\t写入文件（Write into a file）\n2\t复制到剪贴板（Copy to clipboard）")
                while True:
                    export_method: str = logInput()
                    if export_method == "":
                        continue
                    elif export_method[0] == "0":
                        break
                    elif export_method[0] == "1":
                        json2name: str = "MyPage.json"
                        with open(json2name, "w", encoding = "utf-8") as fp:
                            json.dump(perkPage_json, fp, ensure_ascii = False)
                        logPrint('符文页“%s”（%d）已导出到同目录下的“%s”中。\nPage "%s" (%d) has been exported into "%s" under the same folder.\n' %(pageName, pageId, json2name, pageName, pageId, json2name))
                        break
                    elif export_method[0] == "2":
                        try:
                            pyperclip.copy(json.dumps(perkPage_json, ensure_ascii = False))
                        except:
                            traceback_info = traceback.format_exc()
                            logPrint(traceback_info)
                            logPrint("符文页复制失败。\nPerk page copy failed.")
                        else:
                            logPrint('符文页“%s”（%d）已复制到剪贴板中。\nPage "%s" (%d) has been copied to clipboard.\n' %(pageName, pageId, pageName, pageId))
                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        logPrint('请选择一个符文页：（输入索引范围之外的整数则创建一个新的符文页。）\nPlease select a page: (Enter an integer beyong the index range to create a new page.)')
        perkPage_df: pandas.DataFrame = await get_perk_page(connection)
        perkPage_df_fields_to_print: list[str] = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
        print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
        log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")

async def switch_active_perkPage(connection: Connection) -> None:
    '''
    选择一个符文页，用于游戏内使用。<br>Select a perk page to be used in game.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
    if len(perkPages) == 0:
        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
    else:
        if not any(map(lambda x: x["isActive"], perkPages)):
            logPrint("符文页活动性无法正常显示。请确保您目前处于涉及符文配置的游戏模式的英雄选择阶段。\nPerk page activity doesn't display right now. Please make sure you're during the champ select stage of a game mode that involves perk configuration.")
        logPrint("您的符文页活动性信息如下：\nPerk page activity is as follows:")
        perkPage_df: pandas.DataFrame = await get_perk_page(connection)
        perkPage_df_fields_to_print: list[str] = ["name", "isActive", "isValid", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
        print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
        log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
        logPrint("请选择您想要使用的符文页：\nPlease select a perk page to use:")
        while True:
            pageIndex_str: str = logInput()
            if pageIndex_str == "":
                continue
            elif pageIndex_str == "0":
                break
            else:
                try:
                    pageIndex: int = int(pageIndex_str)
                except ValueError:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                else:
                    if pageIndex >= 1 and pageIndex < len(perkPage_df):
                        pageId: int = perkPage_df["id"][pageIndex]
                        pageName: str = perkPage_df["name"][pageIndex]
                        isTemporary: bool = perkPage_df["isTemporary"][pageIndex] == "√"
                        primaryPerkStyleName: str = perkPage_df["primaryStyleName"][pageIndex]
                        primaryPerkStyleId: int = perkPage_df["primaryStyleId"][pageIndex]
                        secondaryPerkStyleName: str = perkPage_df["secondaryStyleName"][pageIndex]
                        secondaryPerkStyleId: int = perkPage_df["subStyleId"][pageIndex]
                        keystoneId: int = perkPage_df["pageKeystone id"][pageIndex]
                        keystoneName: str = perkPage_df["pageKeystone name"][pageIndex]
                        perkIds: list[int] = perkPage_df["selectedPerkIds"][pageIndex]
                        perkNames: list[str] = perkPage_df["uiPerksNames"][pageIndex]
                        page_body: dict[str, Any] = {"name": pageName, "isTemporary": isTemporary, "primaryStyleId": primaryPerkStyleId, "subStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                        response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-perks/v1/pages/{pageId}", data = page_body)).json()
                        logPrint(response)
                        if response == None:
                            logPrint("符文页活动性设置失败。\nFailed to set the selected page active.")
                        else:
                            logPrint("已选择的符文页：%s（%d）\nSelected perk page: %s (%d)" %(pageName, pageId, pageName, pageId))
                            logPrint("主系（Style）：%s (%d)\n副系（Substyle）：%s (%d)\n基石符文（Keystone）：%s (%d)\n符文序号列表（Perk id list）： %s\n符文名称列表（Perk name list）： %s\n" %(primaryPerkStyleName, primaryPerkStyleId, secondaryPerkStyleName, secondaryPerkStyleId, keystoneName, keystoneId, perkIds, perkNames))
                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")

async def arrange_perk_pages(connection: Connection) -> None:
    '''
    排序符文页。<br>Order the perk pages.
    
    本功能允许用户绕过访问藏品，直接在英雄选择阶段修改符文页的显示顺序。<br>This function allows user to skip opening Collection and directly change the display order of perk pages during a champ select stage.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    '''
    perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json() #排序过程容易牵一发而动全身地出现问题，因此尽可能还是保证符文页信息是最新的（One problem may bring about cascade effects during ordering, so the program had better keep the perk page information latest）
    if len(perkPages) == 0:
        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
    else:
        pageIds: list[int] = list(map(lambda x: x["id"], perkPages))
        logPrint('''请输入一个您期望的符文页序号排列顺序列表，排在前面的代表显示在前，排在后面的代表显示在后。例如，如果想恢复您当前的排序，您可以输入“%s”。\nPlease input a perk page id order list, where the page whose pageId is in the front of pageId list will be moved in the front of the page list, and vice versa. For example, if you'd like to recover the current page order, you may input "%s".''' %(current_pageOrder_list, current_pageOrder_list))
        perkPage_df: pandas.DataFrame = await get_perk_page(connection)
        perkPage_df_fields_to_print: list[str] = ["id", "name", "order", "primaryStyleName", "secondaryStyleName"]
        print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print])[0])
        log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
        current_pageOrder_list: list[int] = list(perkPage_df.loc[1:].sort_values(by = "order", ascending = True)["id"])
        page_order: list[int] = []
        while True:
            page_order_got: bool = False
            page_order_str: str = logInput()
            if page_order_str == "":
                continue
            elif page_order_str[0] == "0":
                page_order_got = False
                break
            else:
                try:
                    tmp = eval(page_order_str)
                except:
                    traceback_info = traceback.format_exc()
                    logPrint(traceback_info)
                    logPrint("您的输入格式有误！请重新输入。\nERROR format of input! Please try again.")
                else:
                    if isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x in pageIds, tmp)) and len(tmp) == len(set(tmp)): #这里需要严格控制输入格式：①输入的是一个列表；②列表的元素全是整型，且都是分组序号；③列表元素无重复（Here the input format are strictly controlled: ①the input is a list; ②each element in the list is of integer type and represents a group id; ③the elements are unique）
                        page_order: list[int] = tmp
                        for pageId in page_order:
                            pageIds.remove(pageId)
                        page_order += pageIds #虽然用户可能只是想把个别符文页移到前面，但是后面的操作涉及到调整位次，所以还是需要对所有符文页都进行操作。这样，如果用户输入的是一个空列表，那么表面上看起来程序没有作任何操作，而实际上程序调整了所有位次的数值（Although the user may only want to move several pages to the front, the subsequent operations involve all page orders' value adjustment. In that means, if the user submits an empty list, then it seems that the program doesn't do anything, but actually adjusts all orders' values）
                        page_order_got = True
                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        if page_order_got:
            #除了排序以外，本程序尽量控制位次的大小，规定排在第一的符文页的位次是1，排在第二的符文页的位次是2，依此类推（Aside from ordering, this program also aims at controlling the value of orders: the first page's order is 1, the second page's order is 2, and so on）
            #排序算法：先将所有符文页的位次设置为大于总符文页数量的整数，然后对排在第一的符文页关于其自身做当前位次减1的前移，后面的符文页分别关于排在第一的符文页做从1开始递增数值的后移（Ordering algorithm: Set orders of all pages to integers greater than the total number of pages, then perform a negative offset whose absolute value equals the current order minus 1 towards the page to be ordered in the first place, and perform a positive offset whose absolute value increments starting from 1 towards each of its successor pages）
            perkPages = sorted(perkPages, key = lambda x: x["order"], reverse = True) #对符文页作关于位次的降序排列（Arrange the pages in the descending order of "order"）
            for page in perkPages:
                body: dict[str, int] = {"targetPageId": page["id"], "destinationPageId": page["id"], "offset": len(perkPages) + abs(perkPages[-1]["order"])} #为了避免可能的位次冲突，在准备阶段，尽可能保证所有符文页的偏移量是定值。考虑到有些符文页的位次可能是负数，这里的偏移量带上了符文页最小位次的绝对值，这样能保证所有符文页经过这个for循环之后位次的值大于总符文页数量的整数，且保持原有顺序（To avoid possible order conflicts, the offset of each move should be constant during preparation. Considering some orders may be negative, here the offset is added the absolute value of the smallest order. In this way, orders of all pages will be greater than the total number of perk pages after this for-loop and obey the original order）
                response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-perks/v1/update-page-order", data = body)).json()
                logPrint(response)
                if response != None:
                    logPrint('准备阶段移动“%s”（%d）的过程出现了问题。\nAn error occurred when the program was moving "%s" (%d) during preparation.' %(page["name"], page["id"], page["name"], page["id"]))
            #即使准备阶段出现了问题，实际排序时也不会发生错误。下面的注释会证明这一点（Although errors may occur during preparation, this doesn't make any difference to the actual ordering process. The following comments prove it）
            perkPages = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
            perkPages_dict: dict[int, dict[str, Any]] = {page["id"]: page for page in perkPages} #虽然其实可以从上面的公式中推导出下面的偏移量，但如果上面移动的过程出现了问题，这个办法就行不通了（Although the following offset can be inferred from the above calculation, if an error occurs, this solution won't work）
            error_occurred_perkPageArrange = False
            #首先把排在第一的符文页的位次置为1（First, set the order of the first perk page as 1）
            body: dict[str, int] = {"targetPageId": page_order[0], "destinationPageId": page_order[0], "offset": 1 - perkPages_dict[page["id"]]["order"]} #在准备阶段，如果是排在第一的符文页移动出现问题，那么在这里移动后位次一定是1；如果是排在第二的符文页移动出现了问题，导致经过准备阶段排在第二的符文页的位次是1，那么经过这次操作，排在第二的符文页的位次变成`2 - perkPages_dict[page["id"]]["order"]`（During preparation, if an error occurred when the program was moving the first page, then after this move, its order must be 1; otherwise, if an error occurred when the program was moving the second page, and therefore after the preparation, the second page's order became 1, then after this move, the second page's order becomes `2 - perkPages_dict[page["id"]]["order"]`）
            response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-perks/v1/update-page-order", data = body)).json()
            logPrint(response)
            if response == None:
                logPrint('符文页“%s”（%d）的位次已置为1。\nPage "%s" (%d) order set to 1.' %(perkPages_dict[page_order[0]]["name"], page_order[0], perkPages_dict[page_order[0]]["name"], page_order[0]))
            else:
                error_occurred_perkPageArrange = True
            #排在后面的符文页关于排在第一的符文页作递增偏移量的移动（The successor pages move by an incrementing offset to the first page）
            for i in range(1, len(page_order)):
                body: dict[str, int] = {"targetPageId": page_order[i], "destinationPageId": page_order[0], "offset": i} #在准备阶段，如果是排在第i + 1的符文页移动出现问题，那么在这里移动后位次一定是i + 1；如果是排在第i + 2的符文页移动出现了问题，导致经过准备阶段排在第i + 2的符文页的位次位于1和i + 1之间，那么经过这次操作，排在第i + 2的符文页的位次应当位于i + 1和2i + 1之间，这样就不会对前面i - 1个符文页的顺序产生影响（During preparation, if an error occurred when the program was moving the (i + 1)th page, then after this move, its order must be (i + 1); otherwise, if an error occurred when the program was moving the (i + 2)th page, and therefore the after the preparation, the (i + 2)th page's order is between 1 and i + 1, then after this move, the (i + 2)th page's order should be within (i + 1) and (2i + 1), which makes no difference to the order of the first (i - 1) pages）
                response: dict[str, Any] = await (await connection.request("POST", "/lol-perks/v1/update-page-order", data = body)).json()
                logPrint(response)
                if response == None:
                    logPrint('符文页“%s”（%d）的位次已置为%d。\nPage "%s" (%d) order set to %d.' %(perkPages_dict[page_order[i]]["name"], page_order[i], i + 1, perkPages_dict[page_order[i]]["name"], page_order[i], i + 1))
                else:
                    error_occurred_perkPageArrange = True
            #这样一看，你是不是发现前面的准备阶段完全没有必要（Above all, do you realize that the preparation is totally unnecessary）
            if error_occurred_perkPageArrange:
                logPrint("排序过程发生了异常。请等待客户端符文页顺序稳定后手动排序。\nAn error occurred during ordering. Please order manually after the order of the perk pages becomes stable.")
            else:
                logPrint("排序完成。\nOrder success.")

async def remove_perkPage(connection: Connection) -> None:
    '''
    移除符文页。<br>Remove perk pages.
    '''
    perkPages: dict[str, Any] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
    if len(perkPages) == 0:
        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
    else:
        delete_indices: list[int] = []
        logPrint('请输入要删除的符文页的索引：\nPlease submit the index of the page(s) to delete:\n变量提示（Variable hint）：\nperkPage_df = await get_perk_page(connection)\n示例（Examples）：\n1 #删除数据框索引为1的符文页（Delete the page whose index in the dataframe is 1）\n[1, 2, 3] #删除数据框索引为1、2和3的符文页（Delete the pages whose indices in the dataframe are 1, 2 and 3, respectively）\nall #删除所有符文页（Delete all pages）\n[i for i in range(1, len(perkPage_df)) if perkPage_df.loc[i, "isTemporary"]] #删除所有临时符文页（Delete all temporary pages）\nlist(perkPage_df[perkPage_df["pageKeystone id"] == 8010].index) #删除所有基石序号是8010的符文页（Delete all pages whose keystone id is 8010）\nlist(perkPage_df.iloc[1:, :][(~(perkPage_df.iloc[1:, :]["pageKeystone name"].isin(["征服者", "致命节奏"])) | (perkPage_df.iloc[1:, :]["recommendationChampionId"] == 11)) & (perkPage_df.iloc[1:, :]["secondaryStyleName"] == "启迪")].index) #删除所有基石不是征服者也不是致命节奏，或者推荐英雄序号是11，且副系是启迪系的符文页（Delete all pages whose keystone is neither Conqueror nor Lethal Tempo, or recommended champion id is 11, and the secondary perkstyle is Inspiration）')
        perkPage_df: pandas.DataFrame = await get_perk_page(connection)
        perkPage_df_fields_to_print: list[str] = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
        print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print])[0])
        log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
        while True:
            index_got: bool = False
            delete_str: str = logInput()
            if delete_str == "":
                continue
            elif delete_str == "0":
                break
            elif delete_str == "all":
                delete_indices = list(range(1, len(perkPage_df)))
                break
            else:
                try:
                    tmp = eval(delete_str)
                except:
                    traceback_info = traceback.format_exc()
                    logPrint(traceback_info)
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                else:
                    if isinstance(tmp, int):
                        delete_indices = [tmp]
                        index_got = True
                        break
                    elif isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x > 0 and x < len(perkPage_df), tmp)) and len(tmp) == len(set(tmp)):
                        delete_indices = tmp
                        index_got = True
                        break
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        if index_got and len(delete_indices) > 0:
            logPrint("您选择删除以下%d个符文页。\nYou selected the following %d perk page(s)." %(len(delete_indices), len(delete_indices)))
            print(format_df(perkPage_df.loc[delete_indices, perkPage_df_fields_to_print], print_index = True, reserve_index = True)[0])
            log.write(format_df(perkPage_df.loc[delete_indices, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True, reserve_index = True)[0] + "\n")
            logPrint("请输入任意非空字符串以继续删除，否则取消删除。\nPlease submit any non-empty string to continue deleting, or null to cancel.")
            delete_confirm_str: str = logInput()
            delete_confirm: bool = bool(delete_confirm_str)
            if delete_confirm:
                for delete_index in delete_indices:
                    pageId: int = perkPage_df["id"][delete_index]
                    pageName: str = perkPage_df["name"][delete_index]
                    response: Optional[dict[str, Any]] = await (await connection.request("DELETE", f"/lol-perks/v1/pages/{pageId}")).json()
                    logPrint(response)
                    if response == None:
                        logPrint(f"已删除的符文页（Deleted page）：{pageName}（{pageId}）")
                    else:
                        logPrint(f'符文页“{pageName}”（{pageId}）删除失败。\nPage "{pageName}" ({pageId}) failed to be deleted.')

async def configure_perks(connection: Connection) -> None:
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    platformId: str = current_party["platformId"]
    riot_client_info: list[str] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_info: dict[str, str] = {}
    for i in range(len(riot_client_info)):
        try:
            client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
        except IndexError:
            pass
    region: str = client_info["--region"]
    #设置输出路径（Set the output directory）
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    displayName: str = get_info_name(current_info)
    folder: str = set_summonerInfo_folder(region, platformId, current_info)
    while True:
        logPrint("请选择您想要执行的操作：\nPlease select an operation to perform:\n0\t退出程序（Exit the program）\n1\t查看所有符文（Check all perks）\n2\t查看推荐符文（Check recommended pages）\n3\t管理符文页（Manage perk pages）")
        option: str = logInput()
        if option == "":
            continue
        elif option[0] == "0":
            break
        elif option[0] == "1":
            check_all_perks()
        elif option[0] == "2":
            step, championId, championPosition, mapId = specify_recommend_perkPage_parameters()
            if step == 0:
                continue
            recommendedPages: list[dict[str, Any]] = await (await connection.request("GET", f"/lol-perks/v1/recommended-pages/champion/{championId}/position/{championPosition}/map/{mapId}")).json()
            check_recommend_perkPage(recommendedPages, championId, championPosition, mapId)
        elif option[0] == "3":
            logPrint("您的符文页信息如下：\nYour perk pages are listed below:")
            perkPage_df: pandas.DataFrame = await get_perk_page(connection)
            perkPage_df_fields_to_print: list[str] = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
            print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
            log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
            logPrint("请选择一个操作：\nPlease select an action:\n0\t返回上一层（Return to the last step）\n1\t导出所有符文页（Export all pages）\n2\t查看、编辑和导出一个符文页（Check, edit and export a page）\n3\t切换活动符文页（Toggle active perk page）\n4\t排序符文页（Order perk pages）\n5\t删除符文页（Delete perk pages）")
            while True:
                action: str = logInput()
                if action == "":
                    continue
                elif action[0] == "0":
                    break
                elif action[0] == "1":
                    export_all_perkPages(perkPage_df, displayName, folder)
                elif action[0] == "2":
                    await edit_perkPage(connection)
                elif action[0] == "3":
                    await switch_active_perkPage(connection)
                elif action[0] == "4":
                    await arrange_perk_pages(connection)
                elif action[0] == "5":
                    await remove_perkPage(connection)
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    continue
                logPrint("您的符文页信息如下：\nYour perk pages are listed below:")
                perkPage_df: pandas.DataFrame = await get_perk_page(connection)
                perkPage_df_fields_to_print: list[str] = ["id", "name", "isTemporary", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]
                print(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], print_index = True)[0])
                log.write(format_df(perkPage_df.loc[:, perkPage_df_fields_to_print], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
                logPrint("请选择一个操作：\nPlease select an action:\n0\t返回上一层（Return to the last step）\n1\t导出所有符文页（Export all pages）\n2\t查看、编辑和导出一个符文页（Check, edit and export a page）\n3\t切换活动符文页（Toggle active perk page）\n4\t排序符文页（Order perk pages）\n5\t删除符文页（Delete perk pages）")

#-----------------------------------------------------------------------------
# websocket
#-----------------------------------------------------------------------------
@connector.ready
async def connect(connection: Connection) -> None:
    global log, logInput, logPrint
    log_folder: str = "日志（Logs）/Customized Program 19 - Configure Perks"
    os.makedirs(log_folder, exist_ok = True)
    currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    log = LogManager(path = os.path.join(log_folder, currentTime + ".log"), mode = "a+", encoding = "utf-8")
    logInput = log.logInput
    logPrint = log.logPrint
    await print_summoner_info(connection)
    await prepare_data_resources(connection)
    await save_platform_info(connection)
    await configure_perks(connection)
    log.write("\n[Program terminated and returned status 0.]\n")
    log.close()

@connector.close
async def disconnect(connection: Connection) -> None:
    print("已从英雄联盟客户端断开连接。\nDisconnected from the League Client.")

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------

connector.start()
