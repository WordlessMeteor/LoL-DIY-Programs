from lcu_driver import Connector
from lcu_driver.connection import Connection
import copy, json, numpy, os, pandas, platform, pyperclip, re, time, traceback
from typing import Any, Optional
from src.utils.format import getISOTime, optimize_bool_display, format_df, addDefaultStyle, pyobj2json
from src.utils.logger import LogManager
from src.utils.summoner import get_summoner_data, get_info_name
from src.core.config.localization import slotTypes, positions, recommendedAttributes
from src.core.config.headers import perk_header, recommendedPage_header, perkPage_header
from src.core.config.servers import set_summonerInfo_folder, save_platform_info
from src.core.dataframes.champions import sort_inventory_champions

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： XHXIAIEIN
# 更新（Last update）：     2026/03/06
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
log: LogManager = LogManager()

connector: Connector = Connector()

#-----------------------------------------------------------------------------
# 配置符文（Configure perks）
#-----------------------------------------------------------------------------
def clear_screen() -> None:
    if platform.system() == "Windows":
        os.system("CLS")
    else:
        os.system("clear")

async def prepare_data_resources(connection: Connection) -> None:
    global spells, perks_source, perks, perkstyles_source, perkstyles, LoLChampions, recommended_position_for_champion
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

async def sort_perk_data(connection: Connection) -> pandas.DataFrame:
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
    perkIds_sorted: list[str] = sorted(map(lambda x: x["id"], perks_source))
    for perkId in perkIds_sorted:
        if not perkId in defaultPerkOrder:
            defaultPerkOrder.append(perkId)
    ##构建符文序号权重字典（Create the status dictionary of perkIds）
    defaultPerkOrder_dict: dict[str, int] = {defaultPerkOrder[i]: i for i in range(len(defaultPerkOrder))}
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

async def get_recommended_perk(connection: Connection, championId: int, position: str, mapId: int) -> pandas.DataFrame:
    recommendedPages: list[dict[str, Any]] = await (await connection.request("GET", f"/lol-perks/v1/recommended-pages/champion/{championId}/position/{position}/map/{mapId}")).json()
    if recommendedPages == []:
        recommendedPage_df: pandas.DataFrame = pandas.DataFrame(data = recommendedPage_header, index = 0)
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
    current_info: dict[str, Any] = await (await connection.request("GET", "/lol-summoner/v1/current-summoner")).json()
    current_summonerId: int = current_info["summonerId"]
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

async def configure_perks(connection: Connection) -> None:
    platformId: str = await (await connection.request("GET", "/lol-platform-config/v1/namespaces/LoginDataPacket/platformId")).json()
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
        if option == "0":
            break
        elif option == "1":
            logPrint("请选择输出形式：\nPlease select a form to output:\n0\t返回上一层（Return to the last step）\n1\t分类（Classified）\n2\t表格（Tabified）\n3\t文件（File）")
            while True:
                form: str = logInput()
                if form == "":
                    continue
                elif form[0] == "0":
                    break
                elif form[0] == "1":
                    HTML_tag_re = re.compile(r"<[^>]*>")
                    perkIds_unprinted: list[int] = list(map(lambda x: x["id"], perks_source))
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
                    break
                elif form[0] == "2":
                    HTML_tag_re = re.compile(r"<[^>]*>")
                    perk_df: pandas.DataFrame = await sort_perk_data(connection)
                    for i in range(1, len(perk_df)):
                        shortDesc = perk_df["shortDesc"][i]
                        while HTML_tag_re.search(shortDesc):
                            shortDesc = shortDesc.replace(HTML_tag_re.search(shortDesc).group(), "") #数据框在输出到终端时移除HTML标签（When the dataframe is output to terminal, the HTML tags are removed）
                        perk_df["shortDesc"][i] = shortDesc
                    perk_df_fields_to_print: list[str] = ["styleName", "id", "name", "slotType", "slotLabel"]
                    print(format_df(perk_df.loc[:, perk_df_fields_to_print])[0])
                    log.write(format_df(perk_df.loc[:, perk_df_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
                    break
                elif form[0] == "3":
                    perk_df = await sort_perk_data(connection)
                    excel_name: str = "Perks.xlsx"
                    while True:
                        try:
                            with pandas.ExcelWriter(path = excel_name) as writer:
                                addDefaultStyle(perk_df).to_excel(excel_writer = writer, sheet_name = "Perks") #数据框在导出到Excel中时保留最原始的数据（When the dataframe is exported to Excel, the most original information is reserved）
                        except PermissionError:
                            logPrint("无写入权限！请确保文件未被打开且非只读状态！按回车键以重试。\nPermission denied! Please ensure the file isn't opened right now or read-only! Press Enter to try again.")
                            logInput()
                        else:
                            break
                    logPrint(f'符文信息已导出到同目录下的“{excel_name}”中。\nPerk information has been exported into {excel_name} under the same folder.')
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        elif option == "2":
            logPrint("请输入英雄序号：\nPlease enter a champion id:")
            LoLChampion_df, count = sort_inventory_champions(LoLChampions, recommended_position_for_champion)
            LoLChampion_fields_to_print: list[str] = ["id", "name", "title", "alias"]
            LoLChampion_df_query: pandas.DataFrame = LoLChampion_df.loc[:, LoLChampion_fields_to_print]
            LoLChampion_df_query["id"] = LoLChampion_df["id"].astype(str) #方便检索（For convenience of retrieval）
            LoLChampion_df_query = LoLChampion_df_query.map(lambda x: x.lower() if isinstance(x, str) else x)
            print(format_df(LoLChampion_df.loc[:, LoLChampion_fields_to_print])[0])
            log.write(format_df(LoLChampion_df.loc[:, LoLChampion_fields_to_print], width_exceed_ask = False, direct_print = False)[0] + "\n")
            back: bool = False
            championId: int = 0
            championName: str = ""
            championAlias: str = ""
            while True:
                champion_queryStr: str = logInput()
                if champion_queryStr == "":
                    continue
                elif champion_queryStr == "0":
                    back = True
                    break
                else:
                    query_positions = numpy.where(LoLChampion_df_query == champion_queryStr.lower()) #使用numpy.where检索的前提是数据框中每个单元格的值都不一样（The premise of query by `numpy.where` is that no two cells are the same）
                    if len(query_positions[0]) == 0:
                        logPrint("没有找到该英雄。请重新输入。\nChampion not found. Please try again.")
                    else:
                        resultRow: int = query_positions[0]
                        result_champion_df: pandas.DataFrame = LoLChampion_df.loc[resultRow, LoLChampion_fields_to_print].reset_index(drop = True)
                        championId = LoLChampion_df["id"][resultRow[0]]
                        championName = LoLChampion_df["name"][resultRow[0]]
                        championAlias = LoLChampion_df["alias"][resultRow[0]]
                        logPrint("您选择了以下英雄：\nYou selected the following champion:")
                        print(format_df(result_champion_df)[0])
                        log.write(format_df(result_champion_df, width_exceed_ask = False, direct_print = False)[0] + "\n")
                        break
            if back:
                continue
            positionDict: dict[str, str] = {"TOP": "上路", "JUNGLE": "打野", "MIDDLE": "中路", "BOTTOM": "下路", "UTILITY": "辅助"}
            recommended_champion_positions: dict[str, dict[str, list[str]]] = await (await connection.request("GET", "/lol-perks/v1/recommended-champion-positions")).json()
            recommendedPositions: list[str] = recommended_champion_positions[str(championId)]["recommendedPositions"] if str(championId) in recommended_champion_positions else ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
            logPrint("请选择一条推荐路线：\nPlease select a recommended position:")
            position_count: int = 0
            for position in recommendedPositions:
                position_count += 1
                logPrint("%d\t%s\t%s" %(position_count, position, positionDict[position]))
            while True:
                position_str: str = logInput()
                if position_str == "0":
                    back = True
                    break
                elif position_str.upper() in recommendedPositions:
                    championPosition: str = position_str.upper()
                    break
                elif position_str in list(map(str, range(1, len(recommendedPositions) + 1))):
                    championPosition = recommendedPositions[int(position_str) - 1]
                    break
                elif position_str.upper() in positionDict:
                    logPrint("%s的推荐路线中没有%s。请重新输入。\n%s isn't a recommended position of %s. Please try again." %(result_champion_df["name"][0], position_str.upper(), position_str.upper(), result_champion_df["alias"][0]))
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            if back:
                continue
            logPrint("请输入地图序号：\nPlease enter the mapId:")
            gamemaps: dict[int, dict[str, str]] = {8: {"zh_CN": "水晶之痕", "en_US": "Crystal Scar"}, 10: {"zh_CN": "扭曲丛林", "en_US": "Twisted Treeline"}, 11: {"zh_CN": "召唤师峡谷", "en_US": "Summoner's Rift"}, 12: {"zh_CN": "随机地图", "en_US": "Random Map"}, 14: {"zh_CN": "屠夫之桥", "en_US": "Butcher's Bridge"}, 16: {"zh_CN": "星界废墟", "en_US": "Cosmic Ruins"}, 18: {"zh_CN": "瓦洛兰城市公园", "en_US": "Valoran City Park"}, 19: {"zh_CN": "第43区", "en_US": "Substructure 43"}, 20: {"zh_CN": "飞船坠落点", "en_US": "Crash Site"}, 21: {"zh_CN": "百合与莲花的神庙", "en_US": "Temple of Lily and Lotus"}, 22: {"zh_CN": "聚点危机", "en_US": "Convergence"}, 30: {"zh_CN": "怒火角斗场", "en_US": "Rings of Wrath"}, 33: {"zh_CN": "最终都市", "en_US": "Final City"}, 35: {"zh_CN": "班德尔之森", "en_US": "The Bandlewood"}}
            gamemap_df: pandas.DataFrame = pandas.DataFrame(data = {"mapId": list(gamemaps.keys()), "zh_CN": list(map(lambda x: x["zh_CN"], gamemaps.values())), "en_US": list(map(lambda x: x["en_US"], gamemaps.values()))})
            print(format_df(gamemap_df)[0])
            log.write(format_df(gamemap_df, width_exceed_ask = False, direct_print = False)[0])
            while True:
                mapStr: str = logInput()
                if mapStr == "0":
                    back = True
                    break
                elif mapStr == "":
                    mapId: int = 11
                    break
                elif mapStr in list(map(str, gamemaps.keys())):
                    mapId = int(mapStr)
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input. Please try again.")
            if back:
                continue
            recommendedPage_df: pandas.DataFrame = await get_recommended_perk(connection, championId, championPosition, mapId)
            if len(recommendedPage_df) == 1: #一般情况下接口数据是正常获取的（The endpoint should work in normal cases）
                logPrint("%s中的%s%s推荐符文信息不可用。\nRecommended perk information of %s %s on %s isn't available." %(gamemaps[mapId]["zh_CN"], positionDict[championPosition], result_champion_df["name"][0], championPosition, result_champion_df["alias"][0], gamemaps[mapId]["en_US"]))
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
                                        pyperclip.copy(recommendedPage_json)
                                    except: #在执行极致压缩任务时，可能导致剪贴板操作失败（When the user is performing an extreme compression task, clipboard operations might fail）
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
        elif option == "3":
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
                    excel_name: str = f"Player Perk Pages - {displayName}.xlsx"
                    wbPath: str = os.path.join(folder, excel_name)
                    os.makedirs(folder, exist_ok = True)
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
                elif action[0] == "2":
                    logPrint('请选择一个符文页：（输入索引范围之外的整数则创建一个新的符文页。）\nPlease select a page: (Enter an integer beyong the index range to create a new page.)')
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
                            pageName = ""
                            page_edit = True
                            perkInventory: dict[str, Any] = await (await connection.request("GET", "/lol-perks/v1/inventory")).json() #这个接口返回的信息中，自定义符文页可解锁似乎是一直是可用的（In the result returned by this endpoint, the "isCustomPageCreationUnlocked" seems always to be True）
                            if not perkInventory["canAddCustomPage"]:
                                logPrint("符文页栏位已满。删除或拥有更多符文页以创建新的符文页。程序将创建临时符文页。\nInventory full. Delete or obtain more pages to create more. The program is going to create a temporary perk page.")
                                isTemporary = True
                            else:
                                isTemporary = False
                        response: Optional[dict[str, Any]] = {}
                        if page_edit:
                            logPrint("请选择编辑方式：\nPlease select a method of:\n0\t放弃修改（Quit editing）\n1\t逐个修改（Successively）\n2\t批量修改（In batch）\n3\t仅重命名（Rename only）\n4\t读取Json数据（From json data）\n5\t读取文件（From a file）")
                            while True:
                                back: bool = False #决定是否切换编辑方式（Determines whether to switch to another method of editing）
                                method = logInput()
                                if method == "":
                                    continue
                                elif method[0] == "0":
                                    page_edit = False
                                    break
                                elif method[0] == "1": #保持与客户端符文配置步骤相同（Keep synchronized with the latest perk configuration steps in the League Client）
                                    page_body: dict[str, Any] = {"name": "", "isTemporary": isTemporary, "primaryStyleId": -1, "subStyleId": -1, "selectedPerkIds": [-1, -1, -1, -1, -1, -1, -1, -1, -1]} #请求主体初始化（Initialize the request body）
                                    logPrint('在下面的步骤中，请确保输入的是正整数类型的符文系序号和符文序号。输入“0”以撤回最近一次输入。\nDuring the following steps, please make sure you submit the perkStyleId and perkId of integer type. Submit "0" to revert the latest input.')
                                    allowedSubStyles: list[int] = []
                                    step: int = 1
                                    while step <= 11: #客户端内配置符文页需要11个步骤（Setting a perk page in the League Client needs 11 steps）
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
                                            substyle: dict[str, Any] = perkstyles[page_body["subStyleId"]]["name"] if page_body["subStyleId"] in perkstyles else "副系"
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
                                        else:
                                            slotLabel = perkstyles_source["styles"][0]["slots"][step - 5]["slotLabel"] #这里的“0”可以换成1～4之间的任意正整数，因为所有符文系的后三个小符文信息都是一样的（Here the "0" can be replaced by any integer between 1 and 4, for the last three stat mods in all perkstyles are the same）
                                            slotPerks = perkstyles_source["styles"][0]["slots"][step - 5]["perks"]
                                            tooltip = f"第{step}步：请选择{slotLabel}属性。\nStep {step}: Please select a {slotLabel} stat mod."
                                            perkTableStr = ""
                                            for i in range(len(slotPerks)):
                                                perkId = slotPerks[i]
                                                parameter_dict[i + 1] = perkId
                                                perkTableStr += "\n#%d\t%d\t%s" %(i + 1, perkId, perks[perkId]["name"])
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
                                    if back:
                                        page_edit = False
                                    else:
                                        page_edit = True
                                        if page_exist:
                                            old_pageName: str = pageName
                                            logPrint("是否需要修改符文页名称？（输入任意键修改，否则不修改。）\nDo you want to change the page name? (Submit any non-empty string to change, or null to stop changing.)")
                                            pageNameChange_str: str = logInput()
                                            pageName_change: bool = bool(pageNameChange_str)
                                            if pageName_change:
                                                logPrint("请输入符文页的新名称：\nPlease enter the new name of this perk page:")
                                                new_pageName: str = logInput()
                                            else:
                                                new_pageName = old_pageName
                                            if old_pageName != new_pageName:
                                                logPrint("输入任意非空字符串以确认修改，否则取消修改。\nSubmit any non-empty string to confirm changing, or null to cancel.\n旧名称（Old）：%s\n新名称（New）：%s" %(old_pageName, new_pageName))
                                                pageName_change_confirm_str: str = logInput()
                                                pageName_change_confirm: bool = bool(pageName_change_confirm_str)
                                            else:
                                                pageName_change_confirm = False
                                            page_body["name"] = new_pageName if pageName_change_confirm else old_pageName
                                        else:
                                            logPrint("请输入新符文页的名称：\nPlease enter the name of the new perk page:")
                                            new_pageName: str = logInput()
                                            page_body["name"] = new_pageName
                                elif method[0] == "2":
                                    keystoneIds: list[int] = [perk["id"] for perk in perks_source if perk["slotType"] == "kKeyStone"] #提取基石序号列表，用于判断基石的正确性（Extract the list of keystone ids to judge the keystone's correctness）
                                    statmodIds: list[int] = [perk["id"] for perk in perks_source if perk["slotType"] == "kStatMod"] #提取属性符文序号列表，用于判断基石的正确性（Extract the list of stat mod ids to judge the keystone's correctness）
                                    perkMap: dict[int, dict[str, Any]] = {} #建立一个由符文对应到所属符文页的对应关系，并从符文页信息中提取每个符文的槽位类型和槽位名称（Build a map from perks to the belonging perkstyles and extract each perk's slot type and slot label from perkstyle information）
                                    for style in perkstyles_source["styles"]:
                                        for slot in style["slots"]:
                                            for perkId in slot["perks"]:
                                                perkMap[perkId] = {"styleId": perks[perkId]["styleId"], "slotType": slot["type"], "slotLabel": slot["slotLabel"]}
                                    logPrint("请输入一个由符文序号组成的列表。\nPlease input a list composed of perkIds.\n例如（Example）：[8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]")
                                    while True:
                                        uiPerksStr: str = logInput()
                                        if uiPerksStr == "":
                                            continue
                                        elif uiPerksStr[0] == "0":
                                            back = True
                                            break
                                        else:
                                            try:
                                                tmp = eval(uiPerksStr)
                                            except:
                                                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                            else:
                                                #下面对uiPerksIds展开重重检验，确保生成的是有效的符文页（The following code perform continuous tests on `uiPerksIds` to ensure that a valid perk page will be generated）
                                                if isinstance(tmp, list) and all(map(lambda x: isinstance(x, int) and x in perks.keys(), tmp)):
                                                    uiPerksIds: list[int] = tmp
                                                    if len(uiPerksIds) >= 9:
                                                        uiPerksIds = uiPerksIds[:9] #正确的请求主体中，符文序号列表长度为9。因此如果用户输入长度超过9的列表，将被自动截断（In a correct request body, the length of the perkId list is 9. Therefore, if the user submits a list with length over 9, this list will be taken a slice automatically）
                                                        perkIds_valid: bool = True #在保证用户的输入的列表元素都是整数的情况下，对于符文序号列表的逻辑展开检验（Perform tests on the perkId list's logic, if each element of this list is of integer type）
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
                                                        if perkIds_valid: #前面的检验都通过，则用户输入的符文序号列表是合法的（If all the previous tests are passed, then the perkId list is valid）
                                                            page_body = {"name": "", "isTemporary": isTemporary, "primaryStyleId": primaryStyle["id"], "subStyleId": perkMap[uiPerksIds[4]]["styleId"], "selectedPerkIds": uiPerksIds} #第4个和第5个符文的所属符文系是相同的，这里默认使用了第4个（The 4th and 5th perks have the same belonging perkstyles. Here the 4th's is used）
                                                            #设置符文页的名称（Set the perk page name）
                                                            pageNameChange: bool = False
                                                            if page_exist:
                                                                old_pageName: str = pageName
                                                                logPrint("是否需要修改符文页名称？（输入任意键修改，否则不修改。）\nDo you want to change the page name? (Submit any non-empty string to change, or null to stop changing.)")
                                                                pageNameChange_str = logInput()
                                                                pageNameChange = bool(pageNameChange_str)
                                                                if pageNameChange:
                                                                    logPrint("请输入符文页的新名称：\nPlease enter the new name of this perk page:")
                                                            else:
                                                                old_pageName = ""
                                                                pageNameChange = True
                                                                logPrint("请输入新符文页的名称：\nPlease enter the name of the new perk page:")
                                                            if pageNameChange:
                                                                while True:
                                                                    new_pageName: str = logInput()
                                                                    #检验符文页名称有效性的接口依赖于一个具体的符文页。这需要针对用户是否有符文页进行讨论（The endpoint to validate the page name depends on a specific perk page. This introduces the discussion about whether the user has one perk page）
                                                                    perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                                                                    dummy_page_created: bool = False
                                                                    if len(perkPages) == 0: #如果用户没有符文页，则创建一个占位符文页。目的只是为了拿到一个具体的符文页序号（If the user doesn't have any perk page, create one. The aim is only to get a perk page id）
                                                                        dummy_page_body: dict[str, Any] = {"name": "占位符文页", "isTemporary": isTemporary, "primaryStyleId": -1, "subStyleId": -1, "selectedPerkIds": [-1, -1, -1, -1, -1, -1, -1, -1, -1]}
                                                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-perks/v1/pages", data = dummy_page_body)).json()
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
                                                            break
                                                        else:
                                                            logPrint("您输入的符文序号列表有误！请检查您输入的符文序号列表并再试一次。\nERROR occurred in the perkId list! Please check your perkId list and try again.")
                                                    else:
                                                        logPrint("您输入的符文数量过少！请输入由9个符文序号组成的列表。\nPerk number not enough! Please submit a list composed of 9 perkIds.")
                                                else:
                                                    logPrint("您的输入格式有误！请输入一个由符文序号正整数组成的列表。\nERROR format! Please submit a list composed of perkIds of integer type.")
                                    page_edit = not back
                                elif method[0] == "3":
                                    if page_exist:
                                        old_pageName: str = pageName
                                        logPrint("请输入符文页的新名称：\nPlease enter the new name of this perk page:")
                                        new_pageName: str = logInput()
                                        if old_pageName != new_pageName:
                                            logPrint("输入任意非空字符串以确认修改，否则取消修改。\nSubmit any non-empty string to confirm changing, or null to cancel.\n旧名称（Old）：%s\n新名称（New）：%s" %(old_pageName, new_pageName))
                                            pageName_change_confirm_str: str = logInput()
                                            pageName_change_confirm: bool = bool(pageName_change_confirm_str)
                                        else:
                                            pageName_change_confirm = False
                                        page_edit = pageName_change_confirm
                                        page_body = {"name": new_pageName if pageName_change_confirm else old_pageName, "isTemporary": isTemporary, "primaryStyleId": primaryPerkStyleId, "subStyleId": secondaryPerkStyleId, "selectedPerkIds": perkIds}
                                    else:
                                        logPrint("未创建的符文页不支持该操作。\nA perk page that hasn't been created doesn't support this method.")
                                        continue
                                elif method[0] == "4":
                                    logPrint('请在单行内输入包含新符文页信息的字典或Json代码：\nPlease input a Python dictionary or a piece of Json code that represents the new perk page information in a single line:\n示例（Examples）：\nPython字典（Python dictionary）：\n{"name": "无极剑圣 - 致命节奏", "isActive": False, "isTemporary": True, "primaryStyleId": 8000, "secondaryStyleId": 8300, "selectedPerkIds": [8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]}\nJson：\n{"name": "无极剑圣 - 致命节奏", "isActive": false, "isTemporary": true, "primaryStyleId": 8000, "secondaryStyleId": 8300, "selectedPerkIds": [8008, 9111, 9104, 8014, 8347, 8304, 5005, 5008, 5001]}')
                                    while True:
                                        page_body_str: str = logInput()
                                        if page_body_str == "":
                                            continue
                                        elif page_body_str[0] == "0":
                                            back = True
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
                                    page_edit = not back
                                elif method[0] == "5":
                                    logPrint('请输入以Json格式存储新符文页信息的文件路径。输入“0”以返回上一层。\nPlease submit the path of the file that stores the new perk page information in Json format. Submit "0" to return to the last step.')
                                    while True:
                                        page_body_path: str = logInput()
                                        if page_body_path == "":
                                            continue
                                        elif page_body_path == "0":
                                            back = True
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
                                    page_edit = not back
                                else:
                                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                                if page_edit:
                                    if page_exist:
                                        response: Optional[dict[str, Any]] = await (await connection.request("PUT", f"/lol-perks/v1/pages/{pageId}", data = page_body)).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("符文页编辑成功。\nPerk page is edited successfully.")
                                        else:
                                            logPrint("符文页编辑失败。\nFailed to edit this perk page.")
                                    else:
                                        response: Optional[dict[str, Any]] = await (await connection.request("POST", "/lol-perks/v1/pages", data = page_body)).json()
                                        logPrint(response)
                                        if response == None:
                                            logPrint("符文页创建成功。\nPerk page is added successfully.")
                                        else:
                                            logPrint("符文页创建失败。\nFailed to add this perk page.")
                                    if response == None:
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
                        if page_exist or page_edit and response == None:
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
                                            pyperclip.copy(json.dumps(perkPage_json, encoding = "utf-8"))
                                        except:
                                            logPrint("符文页复制失败。\nPerk page copy failed.")
                                        else:
                                            logPrint('符文页“%s”（%d）已复制到剪贴板中。\nPage "%s" (%d) has been copied to clipboard.\n' %(pageName, pageId, pageName, pageId))
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                        break
                elif action[0] == "3":
                    perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                    if len(perkPages) == 0:
                        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
                    else:
                        if not any(map(lambda x: x["isActive"], perkPages)):
                            logPrint("符文页活动性无法正常显示。请确保您目前处于涉及符文配置的游戏模式的英雄选择阶段。\nPerk page activity doesn't display right now. Please make sure you're during the champ select stage of a game mode that involves perk configuration.")
                        logPrint("您的符文页活动性信息如下：\nPerk page activity is as follows:")
                        perkPage_df: pandas.DataFrame = await get_perk_page(connection)
                        print(format_df(perkPage_df.loc[:, ["name", "isActive", "isValid", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]], print_index = True)[0])
                        log.write(format_df(perkPage_df.loc[:, ["name", "isActive", "isValid", "primaryStyleName", "secondaryStyleName", "pageKeystone name"]], width_exceed_ask = False, direct_print = False, print_index = True)[0] + "\n")
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
                elif action[0] == "4":
                    perkPages: list[dict[str, Any]] = await (await connection.request("GET", "/lol-perks/v1/pages")).json() #排序过程容易牵一发而动全身地出现问题，因此尽可能还是保证符文页信息是最新的（One problem may bring about cascade effects during ordering, so the program had better keep the perk page information latest）
                    if len(perkPages) == 0:
                        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
                    else:
                        perkPage_df: pandas.DataFrame = await get_perk_page(connection)
                        pageIds: list[int] = list(map(lambda x: x["id"], perkPages))
                        current_pageOrder_list: list[int] = list(perkPage_df.loc[1:].sort_values(by = "order", ascending = True)["id"])
                        logPrint('''请输入一个您期望的符文页序号排列顺序列表，排在前面的代表显示在前，排在后面的代表显示在后。例如，如果想恢复您当前的排序，您可以输入“%s”。\nPlease input a perk page id order list, where the page whose pageId is in the front of pageId list will be moved in the front of the page list, and vice versa. For example, if you'd like to recover the current page order, you may input "%s".''' %(current_pageOrder_list, current_pageOrder_list))
                        print(format_df(perkPage_df.loc[:, ["id", "name", "order", "primaryStyleName", "secondaryStyleName"]])[0])
                        log.write(format_df(perkPage_df.loc[:, ["id", "name", "order", "primaryStyleName", "secondaryStyleName"]], width_exceed_ask = False, direct_print = False)[0] + "\n")
                        while True:
                            page_order_str: str = logInput()
                            if page_order_str == "":
                                continue
                            elif page_order_str[0] == "0":
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
                                        break
                                    else:
                                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                elif action[0] == "5":
                    perkPages: dict[str, Any] = await (await connection.request("GET", "/lol-perks/v1/pages")).json()
                    if len(perkPages) == 0:
                        logPrint("您还未创建任何符文页！请先创建一个符文页再选择此操作。\nYou don't have any page currently. Please select this action after creating a page.")
                    else:
                        logPrint('请输入要删除的符文页的索引：\nPlease submit the index of the page(s) to delete:\n变量提示（Variable hint）：\nperkPage_df = await get_perk_page(connection)\n示例（Examples）：\n1 #删除数据框索引为1的符文页（Delete the page whose index in the dataframe is 1）\n[1, 2, 3] #删除数据框索引为1、2和3的符文页（Delete the pages whose indices in the dataframe are 1, 2 and 3, respectively）\nall #删除所有符文页（Delete all pages）\n[i for i in range(1, len(perkPage_df)) if perkPage_df.loc[i, "isTemporary"]] #删除所有临时符文页（Delete all temporary pages）\nlist(perkPage_df[perkPage_df["pageKeystone id"] == 8010].index) #删除所有基石序号是8010的符文页（Delete all pages whose keystone id is 8010）\nlist(perkPage_df.iloc[1:, :][(~(perkPage_df.iloc[1:, :]["pageKeystone name"].isin["征服者", "致命节奏"]) | (perkPage_df.iloc[1:, :]["recommendationChampionId"] == 11)) & (perkPage_df.iloc[1:, :]["secondaryStyleName"] == "启迪")].index) #删除所有基石不是征服者也不是致命节奏，或者推荐英雄序号是11，且副系是启迪系的符文页（Delete all pages whose keystone is neither Conqueror nor Lethal Tempo, or recommended champion id is 11, and the secondary perkstyle is Inspiration）')
                        while True:
                            index_got: bool = False
                            delete_indices: list[int] = []
                            delete_str: str = logInput()
                            if delete_str == "":
                                continue
                            elif delete_str == "0":
                                break
                            elif delete_str == "all":
                                delete_indices = list(range(1, len(perkPage_df)))
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
                        if index_got:
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
    await get_summoner_data(connection)
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
