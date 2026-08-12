import copy, json, os, pandas, re, sys, time
from openpyxl.worksheet.worksheet import Worksheet
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.webRequest import requestUrl
from src.utils.format import optimize_bool_display, addDefaultStyle, eliminate_empty_fields, pyobj2json
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.headers import TFTSet_header, TFTShop_header, TFTShopContent_header, TFTDropRate_header, TFTStageRound_header, TFTRound_header, TFTPortal_header, TFTEncounterDistribution_header, TFTEncounter_header, TFTUnitProperty_header, TFTCharacterRole_header, TFTItemList_header, TFTItem_header, TFTTraitList_header, TFTTrait_header, TFTPVENPC_header, TFTScript_header, TFTAnnouncement_header
from src.core.extractor.base import LoLDataExtractor

class TFTExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个云顶之弈提取器对象。<br>Initialize a TFTExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.map22_ready: bool = False
        self.TFTSet_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTShop_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTShopContent_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTDropRate_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTStageRound_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTRound_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTPortal_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTEncounterDistribution_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTEncounter_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTUnitProperty_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTCharacterRole_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTItemList_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTItem_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTTraitList_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTTrait_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTPVENPC_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTScript_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTAnnouncement_df: pandas.DataFrame = pandas.DataFrame()

    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.map22_ready = False
    
    def get_tft_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取聚点危机地图二进制描述数据。<br>Get binary description data of Convergence map online.
        '''
        logPrint = self.log.logPrint
        map22_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map22/map22.bin.json"
        if map22_bin_url in self.__class__.data_cache["online"]:
            self.map22_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map22_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map22_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("聚点危机地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nConvergence map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map22_bin_url))
                else:
                    logPrint("聚点危机地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nConvergence map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            self.map22_bin = source.json()
            self.map22_bin = self.resolve_bin_hash(self.map22_bin)
            self.__class__.data_cache["online"][map22_bin_url] = self.map22_bin
        self.map22_ready = True

    def read_tft_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取聚点危机地图二进制描述数据。<br>Get binary description data of Convergence map offline.
        
        :param path: 聚点危机地图二进制描述文件的本地路径。<br>A local path of Convergence map binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        map22_bin_path: str = path
        if map22_bin_path in self.__class__.data_cache["local"]:
            self.map22_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map22_bin_path]
        else:
            with open(map22_bin_path, "r", encoding = "utf-8") as fp:
                self.map22_bin = json.load(fp)
            self.map22_bin = self.resolve_bin_hash(self.map22_bin)
            self.__class__.data_cache["local"][map22_bin_path] = self.map22_bin
        self.map22_ready = True

    def build_tft_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建云顶之弈数据框。<br>Build TFT dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 聚点危机地图二进制描述文件的本地路径。<br>A local path of Convergence map binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if not "characters_bin_dict" in self.__class__.merged_data_cache:
            logPrint("检测到您尚未获取过云顶之弈角色的二进制描述数据。这将导致相关技能的说明文本无法进行变量代换。（羁绊的说明文本转换依然可用。）是否继续？（输入任意非空字符串以取消导出数据，否则继续。）\nYou haven't got TFT characters' binary description data. This will cause some spells' tooltip not to perform variable substitution. (Trait tooltip transformation will remain available.) Do you want to continue? (Submit any non-empty string to cancel the export, or null to continue.)")
            cancel_str = logInput()
            cancel = bool(cancel_str)
            if cancel:
                logPrint("云顶之弈角色数据尚未准备就绪！\nTFT character data not prepared!")
                return 3
        if not self.map22_ready:
            #获取地图信息（Get map information）
            logPrint("正在读取地图数据……\nReading map data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_tft_data(path = path)
            else:
                self.get_tft_data()
            if not self.map22_ready:
                logPrint("地图数据尚未准备就绪！\nMap data not prepared!")
                return 2

        #定义数据结构（Define the data structure）
        logPrint("正在构建云顶之弈数据框……\nBuilding the TFT dataframes ...", print_time = True)
        ##云顶之弈赛季（TFT Set）
        TFTSet_header_keys: list[str] = list(TFTSet_header.keys())
        TFTSet_data: dict[str, list[Any]] = {key: [] for key in TFTSet_header_keys}
        TFTSet_data_json: dict[str, list[Any]] = copy.deepcopy(TFTSet_data)
        ##云顶之弈商店（TFT Shop）
        TFTShop_header_keys: list[str] = list(TFTShop_header.keys())
        TFTShop_data: dict[str, list[Any]] = {key: [] for key in TFTShop_header_keys}
        TFTShop_data_json: dict[str, list[Any]] = copy.deepcopy(TFTShop_data)
        ##云顶之弈商店内容（TFT Shop Content）
        TFTShopContent_header_keys: list[str] = list(TFTShopContent_header.keys())
        TFTShopContent_data: dict[str, list[Any]] = {key: [] for key in TFTShopContent_header_keys}
        TFTShopContent_data_json: dict[str, list[Any]] = copy.deepcopy(TFTShopContent_data)
        ##云顶之弈掉率表（TFT Drop Rate）
        TFTDropRate_header_keys: list[str] = list(TFTDropRate_header.keys())
        TFTDropRate_data: dict[str, list[Any]] = {key: [] for key in TFTDropRate_header_keys}
        TFTDropRate_data_json: dict[str, list[Any]] = copy.deepcopy(TFTDropRate_data)
        ##云顶之弈回合阶段（TFT Stage Round）
        TFTStageRound_header_keys: list[str] = list(TFTStageRound_header.keys())
        TFTStageRound_data: dict[str, list[Any]] = {key: [] for key in TFTStageRound_header_keys}
        TFTStageRound_data_json: dict[str, list[Any]] = copy.deepcopy(TFTStageRound_data)
        ##云顶之弈回合（TFT Round）
        TFTRound_header_keys: list[str] = list(TFTRound_header.keys())
        TFTRound_data: dict[str, list[Any]] = {key: [] for key in TFTRound_header_keys}
        TFTRound_data_json: dict[str, list[Any]] = copy.deepcopy(TFTRound_data)
        ##云顶之弈传送门（TFT Portal）
        TFTPortal_header_keys: list[str] = list(TFTPortal_header.keys())
        TFTPortal_data: dict[str, list[Any]] = {key: [] for key in TFTPortal_header_keys}
        TFTPortal_data_json: dict[str, list[Any]] = copy.deepcopy(TFTPortal_data)
        ##云顶之弈开场奇遇（TFT Encounter Distribution）
        TFTEncounterDistribution_header_keys: list[str] = list(TFTEncounterDistribution_header.keys())
        TFTEncounterDistribution_data: dict[str, list[Any]] = {key: [] for key in TFTEncounterDistribution_header_keys}
        TFTEncounterDistribution_data_json: dict[str, list[Any]] = copy.deepcopy(TFTEncounterDistribution_data)
        ##云顶之弈奇遇（TFT Encounter）
        TFTEncounter_header_keys: list[str] = list(TFTEncounter_header.keys())
        TFTEncounter_data: dict[str, list[Any]] = {key: [] for key in TFTEncounter_header_keys}
        TFTEncounter_data_json: dict[str, list[Any]] = copy.deepcopy(TFTEncounter_data)
        ##云顶之弈单位属性（TFT Unit Property）
        TFTUnitProperty_header_keys: list[str] = list(TFTUnitProperty_header.keys())
        TFTUnitProperty_data: dict[str, list[Any]] = {key: [] for key in TFTUnitProperty_header_keys}
        TFTUnitProperty_data_json: dict[str, list[Any]] = copy.deepcopy(TFTUnitProperty_data)
        ##云顶之弈角色定位（TFT Character Role）
        TFTCharacterRole_header_keys: list[str] = list(TFTCharacterRole_header.keys())
        TFTCharacterRole_data: dict[str, list[Any]] = {key: [] for key in TFTCharacterRole_header_keys}
        TFTCharacterRole_data_json: dict[str, list[Any]] = copy.deepcopy(TFTCharacterRole_data)
        ##云顶之弈装备列表（TFT Item List）
        TFTItemList_header_keys: list[str] = list(TFTItemList_header.keys())
        TFTItemList_data: dict[str, list[Any]] = {key: [] for key in TFTItemList_header_keys}
        TFTItemList_data_json: dict[str, list[Any]] = copy.deepcopy(TFTItemList_data)
        ##云顶之弈装备（TFT Item）
        TFTItem_header_keys: list[str] = list(TFTItem_header.keys())
        TFTItem_data: dict[str, list[Any]] = {key: [] for key in TFTItem_header_keys}
        TFTItem_data_json: dict[str, list[Any]] = copy.deepcopy(TFTItem_data)
        ##云顶之弈羁绊列表（TFT Trait List）
        TFTTraitList_header_keys: list[str] = list(TFTTraitList_header.keys())
        TFTTraitList_data: dict[str, list[Any]] = {key: [] for key in TFTTraitList_header_keys}
        TFTTraitList_data_json: dict[str, list[Any]] = copy.deepcopy(TFTTraitList_data)
        ##云顶之弈羁绊（TFT Trait）
        TFTTrait_header_keys: list[str] = list(TFTTrait_header.keys())
        TFTTrait_data: dict[str, list[Any]] = {key: [] for key in TFTTrait_header_keys}
        TFTTrait_data_json: dict[str, list[Any]] = copy.deepcopy(TFTTrait_data)
        ##云顶之弈电脑玩家英雄（TFT PVE NPC）
        TFTPVENPC_header_keys: list[str] = list(TFTPVENPC_header.keys())
        TFTPVENPC_data: dict[str, list[Any]] = {key: [] for key in TFTPVENPC_header_keys}
        TFTPVENPC_data_json: dict[str, list[Any]] = copy.deepcopy(TFTPVENPC_data)
        ##云顶之弈脚本（TFT Script）
        TFTScript_header_keys: list[str] = list(TFTScript_header.keys())
        TFTScript_data: dict[str, list[Any]] = {key: [] for key in TFTScript_header_keys}
        TFTScript_data_json: dict[str, list[Any]] = copy.deepcopy(TFTScript_data)
        ##云顶之弈通告（TFT Announcement）
        TFTAnnouncement_header_keys: list[str] = list(TFTAnnouncement_header.keys())
        TFTAnnouncement_data: dict[str, list[Any]] = {key: [] for key in TFTAnnouncement_header_keys}
        TFTAnnouncement_data_json: dict[str, list[Any]] = copy.deepcopy(TFTAnnouncement_data)
        
        #构建映射关系（Build reflections）
        ##通过角色数据构建从指令名到到指令的映射（Build the map from a SpellObject name to a spell through character data）
        if "characters_bin_dict" in self.__class__.merged_data_cache:
            characters_bin_dict = self.__class__.merged_data_cache["characters_bin_dict"]
            characters_bin: dict[str, list[str] | dict[str, Any]] = {}
            for alias in characters_bin_dict:
                characters_bin |= characters_bin_dict[alias]
            self.init_mSpells()
            for (key, value) in characters_bin.items():
                if key != "__linked" and value["__type"] == "SpellObject":
                    self.__class__.mSpells[value["mScriptName"]] = value
                    tmp_ptr = value
                    subkeyList: list[str] = ["mSpell", "mClientData", "mTooltipData", "mLocKeys", "keyTooltip"]
                    for tmp_key in subkeyList:
                        if tmp_key in tmp_ptr:
                            tmp_ptr = tmp_ptr[tmp_key]
                        else:
                            break
                    else:
                        self.__class__.Spell_tooltip_map[tmp_ptr] = value
        TFTItemMap: dict[str, dict[str, Any]] = {} #构建从装备名称到装备对象的映射（Build the map from item's `mName` key's value to a TftItemData object）
        for (key, value) in self.map22_bin.items():
            if key != "__linked" and value["__type"] == "TftUnitPropertyDefinition":
                self.__class__.TFTUnitPropertyMap[value["name"]] = value
            elif key != "__linked" and value["__type"] == "TftTraitData":
                self.__class__.TFTTraitMap[value["mName"]] = value
            elif key != "__linked" and value["__type"] == "ScriptDataObject":
                self.__class__.TFTScriptDataMap[value["mName"]] = value
            elif key != "__linked" and value["__type"] == "TftItemData":
                TFTItemMap[value["mName"]] = value
        
        #准备附加数据（Prepare supplemental data）
        flexibleData: dict[str, dict[str, Any]] = {}
        flexibleData["map22_bin"] = self.map22_bin
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_tft_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.tftstringtable_target
        strtable_tft_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.tftstringtable_default
        for (key1, value) in self.map22_bin.items():
            if key1 != "__linked" and value["__type"] == "TFTSetData": #云顶之弈赛季（TFT Set）
                for i in range(len(TFTSet_header_keys)):
                    key: str = TFTSet_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 130:
                        if i <= 88:
                            tmp_ptr = value
                            subkeyList: list[str] = key.split()
                            for tmp_key in subkeyList:
                                if tmp_key in tmp_ptr:
                                    tmp_ptr = tmp_ptr[tmp_key]
                                else:
                                    if i == 59: #{dacd2fc1} {a211c44d}
                                        to_append = "{dacd2fc1}" in value #默认值其实是真，但如果连上一级键都没有，当然应该设置为假（The default value is True, but if its parent key doesn't exist, then it should be set as False）
                                    elif i == 80: #{bdb41827}
                                        to_append = True
                                    else:
                                        to_append = ""
                                    break
                            else:
                                to_append = tmp_ptr
                        elif i >= 89 and i <= 126 and i != 97 and i != 98 or i == 129 or i == 130:
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            flexibleData["mStat_dict_override_version"] = self.version
                            flexibleData["tftstringtable"] = strtable_locale
                            flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            tooltip_key: str = TFTSet_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            if subkey2.endswith("_burn"):
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, locale, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                                to_append = tooltip_burn
                            else:
                                to_append = tooltip_raw
                        elif i == 97 or i == 98: #本地化特定赛季羁绊显示名（Localized `InfoNubData Trait mDisplayNameTra`）
                            if "InfoNubData" in value and "Trait" in value["InfoNubData"] and value["InfoNubData"]["Trait"] in self.map22_bin:
                                trait = self.map22_bin[value["InfoNubData"]["Trait"]]
                                if "mDisplayNameTra" in trait:
                                    tooltip_key = trait["mDisplayNameTra"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 97 else strtable_tft_default
                                    to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                else:
                                    to_append = trait["mName"]
                            else:
                                to_append = ""
                        elif i == 127: #装备边框配置信息（`{47f76f2b} content`）
                            if "{47f76f2b}" in value:
                                to_append = {key: self.map22_bin.get(value, value) for (key, value) in value["{47f76f2b}"].items()}
                            else:
                                to_append = ""
                        else: #电脑玩家难度配置（`BotSkillData SkillAxes`）
                            if "BotSkillData" in value:
                                to_append = {key: self.map22_bin[value]["SkillAxes"] if value in self.map22_bin else value for (key, value) in value["BotSkillData"].items()}
                            else:
                                to_append = ""
                    elif i <= 133: #角色列表（Character list）
                        subkey = key.split()[0]
                        if subkey in value:
                            to_append = [(self.map22_bin[_]["characters"] if _ in self.map22_bin else _) for _ in value[subkey]]
                        else:
                            to_append = ""
                    elif i == 134: #羁绊变异详细信息（`{0a8ae70b} TraitAssignments`）
                        if "{0a8ae70b}" in value:
                            to_append = [(self.map22_bin[_]["TraitAssignments"] if _ in self.map22_bin else _) for _ in value["{0a8ae70b}"]]
                        else:
                            to_append = ""
                    elif i <= 137: #云顶之弈商店相关键（TFT shop data related keys）
                        if "ShopDataLists" in value:
                            ShopDataList_keys = value["ShopDataLists"]
                            ShopDataLists: list[list[str] | str] = []
                            for ShopDataList_key in ShopDataList_keys:
                                if ShopDataList_key in self.map22_bin:
                                    ShopDataLists.append(self.map22_bin[ShopDataList_key]["ShopDatas"])
                                else:
                                    ShopDataLists.append(ShopDataList_key)
                            if i == 135: #云顶之弈商店信息（`ShopDataLists ShopData`）
                                to_append = ShopDataLists
                            else: #本地化云顶之弈商品名称（Localized TFT shopdata names）
                                ShopDataLists_names: list[list[str] | str] = []
                                for ShopDataList in ShopDataLists:
                                    if isinstance(ShopDataList, str): #聚点危机地图二进制描述数据中未找到主键（Key not found in Convergence map's binary description data）
                                        ShopDataLists_names.append(ShopDataList)
                                    else:
                                        ShopDataList_names: list[str] = []
                                        for ShopData_key in ShopDataList:
                                            if ShopData_key in self.map22_bin and "mDisplayNameTra" in self.map22_bin[ShopData_key]:
                                                ShopData_displayName_key: str = self.map22_bin[ShopData_key]["mDisplayNameTra"]
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 136 else strtable_tft_default
                                                ShopDataList_names.append(self.get_strtable_value(strtable_locale, ShopData_displayName_key, default = ShopData_displayName_key))
                                            else:
                                                ShopDataList_names.append(ShopData_key)
                                        ShopDataLists_names.append(ShopDataList_names)
                                to_append = ShopDataLists_names
                        else:
                            to_append = ""
                    elif i == 138: #各星级弈子供应信息（`ShopContentData TierBags`）
                        if "ShopContentData" in value and value["ShopContentData"] in self.map22_bin and "TierBags" in self.map22_bin[value["ShopContentData"]]:
                            to_append = self.map22_bin[value["ShopContentData"]]["TierBags"]
                        else:
                            to_append = ""
                    elif i == 139: #回合阶段代码（`StageRoundData stages`）
                        if "StageRoundData" in value and value["StageRoundData"] in self.map22_bin:
                            to_append = self.map22_bin[value["StageRoundData"]]["stages"]
                        else:
                            to_append = ""
                    elif i <= 142: #传送门列表（Portal lists）
                        if "{46bf1dcb}" in value and value["{46bf1dcb}"] in self.map22_bin:
                            portalLists = self.map22_bin[value["{46bf1dcb}"]]
                            if i == 140 or i == 141: #地区传送门名称列表（Region portals' localized name list）
                                portalList = portalLists["RegionPortals"]
                                regionNames: list[str] = []
                                for portal_key in portalList:
                                    if portal_key in self.map22_bin:
                                        regionName_key = self.map22_bin[portal_key]["RegionTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 140 else strtable_tft_default
                                        regionNames.append(self.get_strtable_value(strtable_locale, regionName_key, default = regionName_key))
                                    else:
                                        regionNames.append(portal_key)
                                to_append = regionNames
                            else:
                                to_append = portalLists["{48a30fbc}"]
                        else:
                            to_append = ""
                    elif i == 143 or i == 144: #奇遇（Encounter）
                        if "EncounterList" in value and value["EncounterList"] in self.map22_bin:
                            EncounterLists = self.map22_bin[value["EncounterList"]]
                            if i == 143: #开场奇遇事件名称列表（`EncounterList {23c80d88} names`）
                                EncounterDistributionList = EncounterLists["{23c80d88}"]
                                EncounterDistributionNames: list[str] = []
                                for EncounterDistribution_key in EncounterDistributionList:
                                    if EncounterDistribution_key in self.map22_bin:
                                        EncounterDistributionNames.append(self.map22_bin[EncounterDistribution_key]["name"])
                                    else:
                                        EncounterDistributionNames.append(EncounterDistribution_key)
                                to_append = EncounterDistributionNames
                            else: #奇遇事件名称列表（`EncounterList Encounters names`）
                                EncounterList = EncounterLists["Encounters"]
                                EncounterNames: list[str] = []
                                for Encounter_key in EncounterList:
                                    if Encounter_key in self.map22_bin:
                                        EncounterNames.append(self.map22_bin[Encounter_key]["name"])
                                    else:
                                        EncounterNames.append(Encounter_key)
                                to_append = EncounterNames
                        else:
                            to_append = ""
                    elif i <= 147: #赛博装备（Cybernatic items）
                        if "{032ade10}" in value:
                            CybernaticItemLists = value["{032ade10}"]
                            CybernaticItem_keys: dict[str, list[str]] = {}
                            CybernaticItem_names: dict[str, list[str]] = {}
                            for (CybernaticItemList_category, CybernaticItemList_key) in CybernaticItemLists.items():
                                if CybernaticItemList_key in self.map22_bin:
                                    CybernaticItem_keys[CybernaticItemList_category] = list(map(lambda x: x["data"], self.map22_bin[CybernaticItemList_key]["{9a7587b2}"]))
                                    if i == 146 or i == 147: #本地化赛博装备名称（Localized Cybernatic item names）
                                        itemNames: list[str] = []
                                        for item_key in CybernaticItem_keys[CybernaticItemList_category]:
                                            if item_key in self.map22_bin:
                                                cItem = self.map22_bin[item_key]
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 146 else strtable_tft_default
                                                if "mDisplayNameTra" in cItem:
                                                    itemNames.append(self.get_strtable_value(strtable_locale, cItem["mDisplayNameTra"], default = cItem["mDisplayNameTra"]))
                                                else:
                                                    itemNames.append(cItem["mName"])
                                            else:
                                                itemNames.append(item_key)
                                        CybernaticItem_names[CybernaticItemList_category] = itemNames
                                else:
                                    CybernaticItem_keys[CybernaticItemList_category] = CybernaticItemList_key
                            if i == 145: #赛博装备键（`{032ade10} {9a7587b2}`）
                                to_append = CybernaticItem_keys
                            else: #本地化赛博装备名称（Localized Cybernatic item names）
                                to_append = CybernaticItem_names
                        else:
                            to_append = ""
                    elif i == 148: #视觉特效资源映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    elif i == 149: #其它资源解析器映射字典（`{f99705af} resourceMap`）
                        if "{f99705af}" in value:
                            resolverList: list[str | dict[str, str]] = []
                            for ResourceResolver_key in value["{f99705af}"]:
                                if ResourceResolver_key in self.map22_bin and "resourceMap" in self.map22_bin[ResourceResolver_key]:
                                    resolverList.append(self.map22_bin[ResourceResolver_key]["resourceMap"])
                                else:
                                    resolverList.append(ResourceResolver_key)
                            to_append = resolverList
                        else:
                            to_append = ""
                    elif i <= 161: #六费卡指令（`{c8369109}`'s subkeys）
                        if "{c8369109}" in value and value["{c8369109}"] in self.map22_bin:
                            tooltipData = self.map22_bin[value["{c8369109}"]]
                            if i <= 153:
                                subkey = key.split()[1]
                                to_append = tooltipData.get(subkey, "")
                            else:
                                subkey2: str = pStrConst.search(key).group()
                                subkey1: str = key.replace(subkey2, "")
                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                                flexibleData["mStat_dict_override_version"] = self.version
                                flexibleData["tftstringtable"] = strtable_locale
                                flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                                tooltip_key: str = TFTSet_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                if subkey2.endswith("_burn"):
                                    self.__class__.calculatedVariables.clear()
                                    tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, locale, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                                    to_append = tooltip_burn
                                else:
                                    to_append = tooltip_raw
                        else:
                            to_append = ""
                    elif i == 162: #六费单位音频单元（`{235a8995} bankUnits`）
                        if "{235a8995}" in value and value["{235a8995}"] in self.map22_bin:
                            to_append = self.map22_bin[value["{235a8995}"]]["bankUnits"]
                        else:
                            to_append = ""
                    elif i <= 168: #默认棋盘子键（`{52e4eea2}`'s subkeys）
                        if "{52e4eea2}" in value and value["{52e4eea2}"] in self.map22_bin:
                            tmp_ptr = self.map22_bin[value["{52e4eea2}"]]
                            subkeyList: list[str] = key.split()[1:]
                            for tmp_key in subkeyList:
                                if tmp_key in tmp_ptr:
                                    tmp_ptr = tmp_ptr[tmp_key]
                                else:
                                    to_append = ""
                                    break
                            else:
                                to_append = tmp_ptr
                        else:
                            to_append = ""
                    elif i == 169: #签名格信息（`{876a220d} {7c666488}`）
                        if "{876a220d}" in value and value["{876a220d}"] in self.map22_bin:
                            to_append = self.map22_bin[value["{876a220d}"]]["{7c666488}"]
                        else:
                            to_append = ""
                    elif i <= 244: #加农炮击子键（`{c58ff569}`'s subkeys）
                        if "{c58ff569}" in value:
                            if i <= 206:
                                tmp_ptr = value["{c58ff569}"]
                                subkeyList: list[str] = key.split()[1:]
                                for tmp_key in subkeyList:
                                    if tmp_key in tmp_ptr:
                                        tmp_ptr = tmp_ptr[tmp_key]
                                    else:
                                        to_append = ""
                                        break
                                else:
                                    to_append = tmp_ptr
                            else:
                                subkey2: str = pStrConst.search(key).group()
                                subkey1: str = key.replace(subkey2, "")
                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                                tooltip_key: str = TFTSet_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                to_append = tooltip_raw
                        else:
                            to_append = ""
                    else: #人机对战敌方单位子键（`{049d68aa}`'s subkeys）
                        if "{049d68aa}" in value and value["{049d68aa}"] in self.map22_bin:
                            if i == 245 or i == 246:
                                subkey = key.split()[1]
                                to_append = self.map22_bin[value["{049d68aa}"]][subkey]
                            else: #人机对战敌方单位名称列表（`{049d68aa} {d1edd5db} names`）
                                to_append = list(map(lambda x: self.map22_bin[x]["name"] if x in self.map22_bin else x, self.map22_bin[value["{049d68aa}"]]["{d1edd5db}"]))
                        else:
                            to_append = ""
                    TFTSet_data[key].append(to_append)
                    TFTSet_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftShopData": #云顶之弈商店（TFT Shop）
                for i in range(len(TFTShop_header_keys)):
                    key: str = TFTShop_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 15:
                        to_append = value.get(key, "")
                    else:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTShop_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if i == 22 or i == 23: #本地化描述。往往是一个英雄的技能（Localized description, usually of a champion spell）
                            if "characters_bin_dict" in self.__class__.merged_data_cache:
                                if tooltip_key != "" and tooltip_key in self.__class__.Spell_tooltip_map:
                                    mSpell = self.__class__.Spell_tooltip_map[tooltip_key].get("mSpell")
                                else:
                                    mSpell = value
                            else:
                                mSpell = value
                        else:
                            mSpell = value
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, locale, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    TFTShop_data[key].append(to_append)
                    TFTShop_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftShopContentData": #云顶之弈商店内容（TFT Shop Content）
                if "TierBags" in value:
                    for TierBagIndex in range(len(value["TierBags"])):
                        for TierBagEntryIndex in range(len(value["TierBags"][TierBagIndex]["TierBagEntries"])):
                            TierBagEntry = value["TierBags"][TierBagIndex]["TierBagEntries"][TierBagEntryIndex]
                            for i in range(len(TFTShopContent_header_keys)):
                                key: str = TFTShopContent_header_keys[i]
                                if i == 0: #主键（`key`）
                                    to_append: Any = key1
                                elif i == 1: #星级背包索引（`TierBagIndex`）
                                    to_append = TierBagIndex
                                elif i == 2: #星级背包记录索引（`TierBagEntryIndex`）
                                    to_append = TierBagEntryIndex
                                elif i <= 4: #商品键（`ShopData`）
                                    to_append = TierBagEntry.get(key, "")
                                else: #本地化商品名称（Localized shop item names）
                                    ShopData_key = TierBagEntry["ShopData"]
                                    if TierBagEntry["ShopData"] in self.map22_bin:
                                        ShopData = self.map22_bin[ShopData_key]
                                        if "mDisplayNameTra" in ShopData:
                                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 5 else strtable_tft_default
                                            tooltip_key: str = ShopData["mDisplayNameTra"]
                                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                        else:
                                            to_append = ShopData["mName"]
                                    else:
                                        to_append = ShopData_key
                                TFTShopContent_data[key].append(to_append)
                                TFTShopContent_data_json[key].append(pyobj2json(to_append))
                else:
                    for i in range(len(TFTShopContent_header_keys)):
                        key: str = TFTShopContent_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        else:
                            to_append = ""
                        TFTShopContent_data[key].append(to_append)
                        TFTShopContent_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftDropRateTable": #云顶之弈掉率表（TFT Drop Rate）
                for level_index in range(len(value["mDropRatesByLevel"])):
                    dropRates = value["mDropRatesByLevel"][level_index]
                    for i in range(len(TFTDropRate_header_keys)):
                        key: str = TFTDropRate_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #弈士等级（`mDropRatesByLevel Level`）
                            to_append = level_index + 1
                        elif i == 2: #卡费等第数量（`{4f7d4b97}`）
                            to_append = value.get("{4f7d4b97}", "")
                        elif i == 3: #卡费掉率（`{bcf1e6a6}`）
                            to_append = dropRates["{bcf1e6a6}"]
                        else: #卡费掉率字符串（`{bcf1e6a6}_burn`）
                            to_append = self.burnValueList(dropRates["{bcf1e6a6}"])
                        TFTDropRate_data[key].append(to_append)
                        TFTDropRate_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftStageRoundData": #云顶之弈回合阶段（TFT Stage Round）
                for stage_index in range(len(value["stages"])):
                    for round_index in range(len(value["stages"][stage_index]["mRounds"])):
                        mRound_key = value["stages"][stage_index]["mRounds"][round_index]
                        for i in range(len(TFTStageRound_header_keys)):
                            key: str = TFTStageRound_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i == 1: #阶段序号（`stageIndex`）
                                to_append = stage_index + 1
                            elif i == 2: #回合列表（`roundIndex`）
                                to_append = round_index + 1
                            elif i == 3: #回合字符串（`round_burn`）
                                to_append = f"{stage_index + 1}-{round_index + 1}"
                            elif i == 4: #回合代码（`round`）
                                to_append = mRound_key
                            else: #本地化回合名称（Localized round name）
                                if mRound_key in self.map22_bin and "mDisplayNameTra" in self.map22_bin[mRound_key]:
                                    tooltip_key: str = self.map22_bin[mRound_key]["mDisplayNameTra"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 5 else strtable_tft_default
                                    to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                else:
                                    to_append = ""
                            TFTStageRound_data[key].append(to_append)
                            TFTStageRound_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTRoundData": #云顶之弈回合（TFT Round）
                for i in range(len(TFTRound_header_keys)):
                    key: str = TFTRound_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 46:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i in {12, 16, 19, 21, 22, 27, 31, 36, 40, 42}:
                                    to_append = False
                                else:
                                    to_append = ""
                                break
                        else:
                            to_append = tmp_ptr
                    else:
                        if i == 51 or i == 52: #本地化状态说明文本（Localized state tooltips）
                            if "mStateTooltipsTra" in value:
                                stateTooltips: dict[str, str] = {}
                                for (state, tooltip_key) in value["mStateTooltipsTra"].items():
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 51 else strtable_tft_default
                                    stateTooltips[state] = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                to_append = stateTooltips
                            else:
                                to_append = ""
                        else:
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            tooltip_key: str = TFTRound_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            to_append = tooltip_raw
                    TFTRound_data[key].append(to_append)
                    TFTRound_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{b3f382ff}": #云顶之弈传送门（TFT Portal）
                for i in range(len(TFTPortal_header_keys)):
                    key: str = TFTPortal_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 14:
                        if key in value:
                            to_append = value[key]
                        else:
                            if i == 6 or i == 13:
                                to_append = False
                            else:
                                to_append = ""
                    elif i <= 24:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTPortal_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, locale, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    else: #本地化独特强化符文显示名（Localized uniue augments' displayName）
                        if "{ca451de5}" in value:
                            uniqueAugment_keys: list[str] = value["{ca451de5}"]
                            uniqueAugment_names: list[str] = []
                            for uniqueAugment_key in uniqueAugment_keys:
                                if uniqueAugment_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[uniqueAugment_key]:
                                        tooltip_key: str = self.map22_bin[uniqueAugment_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 25 else strtable_tft_default
                                        uniqueAugment_names.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        uniqueAugment_names.append(self.map22_bin[uniqueAugment_key]["mName"])
                                else:
                                    uniqueAugment_names.append(uniqueAugment_key)
                            to_append = uniqueAugment_names
                        else:
                            to_append = ""
                    TFTPortal_data[key].append(to_append)
                    TFTPortal_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{42c94584}": #云顶之弈开场奇遇（TFT Encounter Distribution）
                for i in range(len(TFTEncounterDistribution_header_keys)):
                    key: str = TFTEncounterDistribution_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        to_append = value.get(key, "")
                    TFTEncounterDistribution_data[key].append(to_append)
                    TFTEncounterDistribution_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftEncounterData": #云顶之弈奇遇（TFT Encounter）
                for i in range(len(TFTEncounter_header_keys)):
                    key: str = TFTEncounter_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 12:
                        to_append = value.get(key, "")
                    elif i <= 14: #排除的强化符文本地化名称（Localized excluded augment names）
                        if "ExcludedAugments" in value:
                            ExcludedAugmentNames: list[str] = []
                            for augment_key in value["ExcludedAugments"]:
                                if augment_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[augment_key]:
                                        tooltip_key: str = self.map22_bin[augment_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 13 else strtable_tft_default
                                        ExcludedAugmentNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        ExcludedAugmentNames.append(self.map22_bin[augment_key]["mName"])
                                else:
                                    ExcludedAugmentNames.append(augment_key)
                            to_append = ExcludedAugmentNames
                        else:
                            to_append = ""
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTEncounter_data[key].append(to_append)
                    TFTEncounter_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftUnitPropertyDefinition": #云顶之弈单位属性（TFT Unit Property）
                for i in range(len(TFTUnitProperty_header_keys)):
                    key: str = TFTUnitProperty_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i == 2: #DefaultValue {82e959c3}
                                    to_append = False
                                elif i == 8: #属性继承（`IsCloneable`）
                                    to_append = True
                                else:
                                    to_append = tmp_ptr
                                break
                        else:
                            to_append = tmp_ptr
                    TFTUnitProperty_data[key].append(to_append)
                    TFTUnitProperty_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTCharacterRoleData": #云顶之弈角色定位（TFT Character Role）
                for i in range(len(TFTCharacterRole_header_keys)):
                    key: str = TFTCharacterRole_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 9:
                        to_append = value.get(key, "")
                    elif i <= 25:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTCharacterRole_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, locale, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    else: #本地化装备显示名（Localized item displayNames）
                        itemNames: list[str] = []
                        for item_key in value["items"]:
                            if item_key in self.map22_bin:
                                if "mDisplayNameTra" in self.map22_bin[item_key]:
                                    tooltip_key: str = self.map22_bin[item_key]["mDisplayNameTra"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 26 else strtable_tft_default
                                    itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                else:
                                    itemNames.append(self.map22_bin[item_key]["mName"])
                            else:
                                itemNames.append(item_key)
                        to_append = itemNames
                    TFTCharacterRole_data[key].append(to_append)
                    TFTCharacterRole_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTItemList": #云顶之弈装备列表（TFT Item List）
                for i in range(len(TFTItemList_header_keys)):
                    key: str = TFTItemList_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 3:
                        to_append = value.get(key, "")
                    elif i <= 5: #本地化装备名称（Localized item names）
                        if "mItems" in value:
                            itemNames: list[str] = []
                            for item_key in value["mItems"]:
                                if item_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[item_key]:
                                        tooltip_key: str = self.map22_bin[item_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 4 else strtable_tft_default
                                        itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        itemNames.append(self.map22_bin[item_key]["mName"])
                                else:
                                    itemNames.append(item_key)
                            to_append = itemNames
                        else:
                            to_append = ""
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTItemList_data[key].append(to_append)
                    TFTItemList_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftItemData": #云顶之弈装备（TFT Item）
                for i in range(len(TFTItem_header_keys)):
                    key: str = TFTItem_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 26:
                        if key in value:
                            to_append = value[key]
                        else:
                            if i == 2 or i == 14:
                                to_append = False
                            else:
                                to_append = ""
                    elif i <= 36:
                        subkey = key.split()[0]
                        if subkey in value:
                            if i == 29 or i == 30: #其它合成方案装备构件本地化名称（Alternative composition localized names）
                                AlternativeCompositions_names: list[list[str]] = []
                                for alternativeComposition in value["mAlternativeCompositions"]:
                                    if "mComponents" in alternativeComposition:
                                        itemNames: list[str] = []
                                        for item_key in alternativeComposition["mComponents"]:
                                            if item_key in self.map22_bin:
                                                if "mDisplayNameTra" in self.map22_bin[item_key]:
                                                    tooltip_key: str = self.map22_bin[item_key]["mDisplayNameTra"]
                                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 29 else strtable_tft_default
                                                    itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                                else:
                                                    itemNames.append(self.map22_bin[item_key]["mName"])
                                            else:
                                                itemNames.append(item_key)
                                        AlternativeCompositions_names.append(itemNames)
                                    else:
                                        AlternativeCompositions_names.append([])
                                to_append = AlternativeCompositions_names
                            else:
                                mSubkey_names: list[str] = []
                                for mValue_key in value[subkey]:
                                    if mValue_key in self.map22_bin:
                                        if "mDisplayNameTra" in self.map22_bin[mValue_key]:
                                            tooltip_key: str = self.map22_bin[mValue_key]["mDisplayNameTra"]
                                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if key.endswith("_zh") else strtable_tft_default
                                            mSubkey_names.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                        else:
                                            mSubkey_names.append(self.map22_bin[mValue_key]["mName"])
                                    else:
                                        mSubkey_names.append(mValue_key)
                                to_append = mSubkey_names
                        else:
                            to_append = ""
                    elif i <= 40:
                        subkey = key.split()[0]
                        if subkey in value and value[subkey] in self.map22_bin:
                            if "mDisplayNameTra" in self.map22_bin[value[subkey]]:
                                tooltip_key: str = self.map22_bin[value[subkey]]["mDisplayNameTra"]
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if key.endswith("_zh") else strtable_tft_default
                                to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                            else:
                                to_append = self.map22_bin[value[subkey]]["mName"]
                        else:
                            to_append = ""
                    elif i <= 48:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTItem_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, locale, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTItem_data[key].append(to_append)
                    TFTItem_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftTraitList": #云顶之弈羁绊列表（TFT Trait List）
                for i in range(len(TFTTraitList_header_keys)):
                    key: str = TFTTraitList_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 2:
                        to_append = value.get(key, "")
                    elif i <= 4: #本地化羁绊名称（Localized trait names）
                        if "mTraits" in value:
                            traitNames: list[str] = []
                            for trait_key in value["mTraits"]:
                                if trait_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[trait_key]:
                                        tooltip_key: str = self.map22_bin[trait_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 3 else strtable_tft_default
                                        traitNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        traitNames.append(self.map22_bin[trait_key]["mName"])
                                else:
                                    traitNames.append(trait_key)
                            to_append = traitNames
                        else:
                            to_append = ""
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTTraitList_data[key].append(to_append)
                    TFTTraitList_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftTraitData": #云顶之弈羁绊（TFT Trait）
                for i in range(len(TFTTrait_header_keys)):
                    key: str = TFTTrait_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 10:
                        if key in value:
                            to_append = value[key]
                        else:
                            if i == 10:
                                to_append = False
                            else:
                                to_append = ""
                    else:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTTrait_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, locale, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    TFTTrait_data[key].append(to_append)
                    TFTTrait_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{d545dcdd}": #云顶之弈电脑玩家英雄（TFT PVE NPC）
                if "champions" in value:
                    for champion_index in range(len(value["champions"])):
                        champion = value["champions"][champion_index]
                        for i in range(len(TFTPVENPC_header_keys)):
                            key: str = TFTPVENPC_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i == 1: #代码（`name`）
                                to_append = value["name"]
                            elif i == 2: #英雄索引（`championIndex`）
                                to_append = champion_index
                            elif i <= 8:
                                to_append = champion.get(key, "")
                            elif i == 9: #坐标（`Coordinate`）
                                to_append = "(%d, %d)" %(champion["Row"], champion["Col"])
                            else: #本地化装备名称（Localized item names）
                                if "items" in champion:
                                    itemNames: list[str] = []
                                    for item_key in champion["items"]:
                                        if item_key in TFTItemMap: #这里要注意，人机对战敌方阵营的装备都是用装备代码而不是装备主键来显示的（Note here that the items of a bot opponent are denoted by the item's mName instead of the item key）
                                            if "mDisplayNameTra" in TFTItemMap[item_key]:
                                                tooltip_key: str = TFTItemMap[item_key]["mDisplayNameTra"]
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 10 else strtable_tft_default
                                                itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                            else:
                                                itemNames.append(TFTItemMap[item_key]["mName"])
                                        else:
                                            itemNames.append(item_key)
                                    to_append = itemNames
                                else:
                                    to_append = ""
                            TFTPVENPC_data[key].append(to_append)
                            TFTPVENPC_data_json[key].append(pyobj2json(to_append))
                else:
                    for i in range(len(TFTPVENPC_header_keys)):
                        key: str = TFTPVENPC_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #代码（`name`）
                            to_append = value["name"]
                        else:
                            to_append = ""
                        TFTPVENPC_data[key].append(to_append)
                        TFTPVENPC_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "ScriptDataObject": #云顶之弈脚本（TFT Script）
                for i in range(len(TFTScript_header_keys)):
                    key: str = TFTScript_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 3:
                        to_append = value.get(key, "")
                    else: #拓展组常数数值（`mRequiredConstantsGroup mConstants`）
                        if value["mRequiredConstantsGroup"] in self.map22_bin and "mConstants" in self.map22_bin[value["mRequiredConstantsGroup"]]:
                            to_append = self.map22_bin[value["mRequiredConstantsGroup"]]["mConstants"]
                        else:
                            to_append = ""
                    TFTScript_data[key].append(to_append)
                    TFTScript_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTAnnouncementData": #云顶之弈通告（TFT Announcement）
                for i in range(len(TFTAnnouncement_header_keys)):
                    key: str = TFTAnnouncement_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 6:
                        to_append = value.get(key, "")
                    else: #本地化通告标题（Localized announcement title）
                        tooltip_key: str = value["mTitleTra"]
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 7 else strtable_tft_default
                        to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                    TFTAnnouncement_data[key].append(to_append)
                    TFTAnnouncement_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        ##云顶之弈赛季（TFT Set）
        TFTSet_statistics_output_order: list[int] = [0, 1, 2, 5, 3, 89, 90, 4, 85, 10, 131, 11, 132, 12, 133, 13, 30, 145, 146, 147, 14, 15, 134, 82, 169, 16, 72, 17, 135, 136, 137, 19, 138, 18, 22, 139, 24, 26, 61, 111, 112, 62, 113, 114, 63, 115, 116, 64, 117, 118, 65, 119, 120, 66, 121, 122, 67, 123, 124, 68, 125, 126, 74, 163, 164, 165, 166, 167, 168, 25, 140, 141, 142, 27, 143, 144, 83, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 207, 208, 189, 209, 210, 190, 211, 212, 191, 213, 214, 192, 215, 216, 193, 217, 218, 194, 219, 220, 195, 221, 222, 196, 223, 224, 197, 225, 226, 198, 227, 228, 199, 229, 230, 200, 231, 232, 201, 233, 234, 202, 235, 236, 203, 237, 238, 204, 239, 240, 205, 241, 242, 206, 243, 244, 70, 21, 29, 34, 150, 151, 154, 155, 152, 156, 157, 153, 158, 160, 159, 161, 35, 36, 162, 20, 69, 81, 129, 130, 46, 37, 91, 92, 38, 93, 95, 94, 96, 39, 97, 98, 40, 41, 99, 100, 42, 101, 103, 102, 104, 43, 105, 106, 44, 107, 109, 108, 110, 45, 79, 47, 77, 78, 128, 84, 245, 247, 246, 76, 31, 148, 32, 149, 6, 7, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 71, 127, 88, 33, 8, 9, 23, 28, 58, 59, 60, 73, 75, 80, 86, 87]
        TFTSet_data_organized: dict[str, list[Any]] = {TFTSet_header_keys[i]: TFTSet_data_json[TFTSet_header_keys[i]] for i in TFTSet_statistics_output_order}
        TFTSet_df: pandas.DataFrame = pandas.DataFrame(data = TFTSet_data_organized)
        logPrint("正在优化云顶之弈赛季数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Set dataframe ...")
        optimize_bool_display(TFTSet_df)
        TFTSet_df = pandas.concat([pandas.DataFrame([TFTSet_header])[TFTSet_df.columns], TFTSet_df], ignore_index = True)
        self.TFTSet_df = TFTSet_df
        ##云顶之弈商店（TFT Shop）
        TFTShop_statistics_output_order: list[int] = [0, 3, 1, 11, 16, 17, 2, 4, 5, 12, 18, 19, 13, 20, 22, 21, 23, 14, 24, 25, 15, 6, 7, 8, 9, 10]
        TFTShop_data_organized: dict[str, list[Any]] = {TFTShop_header_keys[i]: TFTShop_data_json[TFTShop_header_keys[i]] for i in TFTShop_statistics_output_order}
        TFTShop_df: pandas.DataFrame = pandas.DataFrame(data = TFTShop_data_organized)
        # logPrint("正在优化云顶之弈商店数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Shop dataframe ...")
        # optimize_bool_display(TFTShop_df)
        TFTShop_df = pandas.concat([pandas.DataFrame([TFTShop_header])[TFTShop_df.columns], TFTShop_df], ignore_index = True)
        self.TFTShop_df = TFTShop_df
        ##云顶之弈商店内容（TFT Shop Content）
        TFTShopContent_statistics_output_order: list[int] = [0, 1, 2, 3, 5, 6, 4]
        TFTShopContent_data_organized: dict[str, list[Any]] = {TFTShopContent_header_keys[i]: TFTShopContent_data_json[TFTShopContent_header_keys[i]] for i in TFTShopContent_statistics_output_order}
        TFTShopContent_df: pandas.DataFrame = pandas.DataFrame(data = TFTShopContent_data_organized)
        # logPrint("正在优化云顶之弈商店内容数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Shop Content dataframe ...")
        # optimize_bool_display(TFTShopContent_df)
        TFTShopContent_df = pandas.concat([pandas.DataFrame([TFTShopContent_header])[TFTShopContent_df.columns], TFTShopContent_df], ignore_index = True)
        self.TFTShopContent_df = TFTShopContent_df
        ##云顶之弈掉率表（TFT Drop Rate）
        TFTDropRate_statistics_output_order: list[int] = [0, 2, 1, 3, 4]
        TFTDropRate_data_organized: dict[str, list[Any]] = {TFTDropRate_header_keys[i]: TFTDropRate_data_json[TFTDropRate_header_keys[i]] for i in TFTDropRate_statistics_output_order}
        TFTDropRate_df: pandas.DataFrame = pandas.DataFrame(data = TFTDropRate_data_organized)
        # logPrint("正在优化云顶之弈掉率数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Drop Rate dataframe ...")
        # optimize_bool_display(TFTDropRate_df)
        TFTDropRate_df = pandas.concat([pandas.DataFrame([TFTDropRate_header])[TFTDropRate_df.columns], TFTDropRate_df], ignore_index = True)
        self.TFTDropRate_df = TFTDropRate_df
        ##云顶之弈回合阶段（TFT Stage Round）
        TFTStageRound_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6]
        TFTStageRound_data_organized: dict[str, list[Any]] = {TFTStageRound_header_keys[i]: TFTStageRound_data_json[TFTStageRound_header_keys[i]] for i in TFTStageRound_statistics_output_order}
        TFTStageRound_df: pandas.DataFrame = pandas.DataFrame(data = TFTStageRound_data_organized)
        # logPrint("正在优化云顶之弈回合阶段数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Stage Round dataframe ...")
        # optimize_bool_display(TFTStageRound_df)
        TFTStageRound_df = pandas.concat([pandas.DataFrame([TFTStageRound_header])[TFTStageRound_df.columns], TFTStageRound_df], ignore_index = True)
        self.TFTStageRound_df = TFTStageRound_df
        ##云顶之弈回合（TFT Round）
        TFTRound_statistics_output_order: list[int] = [0, 1, 3, 47, 48, 4, 49, 50, 5, 51, 52, 12, 15, 53, 54, 13, 14, 16, 17, 18, 19, 20, 21, 22, 25, 55, 56, 23, 24, 26, 27, 30, 57, 58, 28, 29, 31, 34, 59, 60, 32, 33, 35, 36, 39, 61, 62, 37, 38, 40, 41, 63, 64, 42, 45, 65, 66, 43, 44, 46, 2, 6, 7, 8, 9, 10, 11]
        TFTRound_data_organized: dict[str, list[Any]] = {TFTRound_header_keys[i]: TFTRound_data_json[TFTRound_header_keys[i]] for i in TFTRound_statistics_output_order}
        TFTRound_df: pandas.DataFrame = pandas.DataFrame(data = TFTRound_data_organized)
        logPrint("正在优化云顶之弈回合数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Round dataframe ...")
        optimize_bool_display(TFTRound_df)
        TFTRound_df = pandas.concat([pandas.DataFrame([TFTRound_header])[TFTRound_df.columns], TFTRound_df], ignore_index = True)
        self.TFTRound_df = TFTRound_df
        ##云顶之弈传送门（TFT Portal）
        TFTPortal_statistics_output_order: list[int] = [0, 1, 2, 3, 15, 16, 10, 11, 12, 4, 17, 19, 18, 20, 5, 21, 23, 22, 24, 14, 25, 26, 6, 13, 8, 7, 9]
        TFTPortal_data_organized: dict[str, list[Any]] = {TFTPortal_header_keys[i]: TFTPortal_data_json[TFTPortal_header_keys[i]] for i in TFTPortal_statistics_output_order}
        TFTPortal_df: pandas.DataFrame = pandas.DataFrame(data = TFTPortal_data_organized)
        logPrint("正在优化云顶之弈传送门数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Portal dataframe ...")
        optimize_bool_display(TFTPortal_df)
        TFTPortal_df = pandas.concat([pandas.DataFrame([TFTPortal_header])[TFTPortal_df.columns], TFTPortal_df], ignore_index = True)
        self.TFTPortal_df = TFTPortal_df
        ##云顶之弈开场奇遇（TFT Encounter Distribution）
        TFTEncounterDistribution_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        TFTEncounterDistribution_data_organized: dict[str, list[Any]] = {TFTEncounterDistribution_header_keys[i]: TFTEncounterDistribution_data_json[TFTEncounterDistribution_header_keys[i]] for i in TFTEncounterDistribution_statistics_output_order}
        TFTEncounterDistribution_df: pandas.DataFrame = pandas.DataFrame(data = TFTEncounterDistribution_data_organized)
        # logPrint("正在优化云顶之弈开场奇遇数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Encounter Distribution dataframe ...")
        # optimize_bool_display(TFTEncounterDistribution_df)
        TFTEncounterDistribution_df = pandas.concat([pandas.DataFrame([TFTEncounterDistribution_header])[TFTEncounterDistribution_df.columns], TFTEncounterDistribution_df], ignore_index = True)
        self.TFTEncounterDistribution_df = TFTEncounterDistribution_df
        ##云顶之弈奇遇（TFT Encounter）
        TFTEncounter_statistics_output_order: list[int] = [0, 1, 5, 8, 2, 3, 7, 6, 13, 14, 4, 9, 10, 11, 15, 12]
        TFTEncounter_data_organized: dict[str, list[Any]] = {TFTEncounter_header_keys[i]: TFTEncounter_data_json[TFTEncounter_header_keys[i]] for i in TFTEncounter_statistics_output_order}
        TFTEncounter_df: pandas.DataFrame = pandas.DataFrame(data = TFTEncounter_data_organized)
        # logPrint("正在优化云顶之弈奇遇据框的逻辑值显示……\nOptimizing boolean value display of the TFT Encounter dataframe ...")
        # optimize_bool_display(TFTEncounter_df)
        TFTEncounter_df = pandas.concat([pandas.DataFrame([TFTEncounter_header])[TFTEncounter_df.columns], TFTEncounter_df], ignore_index = True)
        self.TFTEncounter_df = TFTEncounter_df
        ##云顶之弈单位属性（TFT Unit Property）
        TFTUnitProperty_statistics_output_order: list[int] = [0, 7, 3, 1, 2, 4, 5, 6, 8]
        TFTUnitProperty_data_organized: dict[str, list[Any]] = {TFTUnitProperty_header_keys[i]: TFTUnitProperty_data_json[TFTUnitProperty_header_keys[i]] for i in TFTUnitProperty_statistics_output_order}
        TFTUnitProperty_df: pandas.DataFrame = pandas.DataFrame(data = TFTUnitProperty_data_organized)
        logPrint("正在优化云顶之弈单位属性数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Unit Property dataframe ...")
        optimize_bool_display(TFTUnitProperty_df)
        TFTUnitProperty_df = pandas.concat([pandas.DataFrame([TFTUnitProperty_header])[TFTUnitProperty_df.columns], TFTUnitProperty_df], ignore_index = True)
        self.TFTUnitProperty_df = TFTUnitProperty_df
        ##云顶之弈角色定位（TFT Character Role）
        TFTCharacterRole_statistics_output_order: list[int] = [0, 1, 3, 10, 11, 4, 12, 13, 5, 14, 16, 15, 17, 6, 18, 19, 7, 20, 21, 8, 22, 24, 23, 25, 9, 26, 27, 2]
        TFTCharacterRole_data_organized: dict[str, list[Any]] = {TFTCharacterRole_header_keys[i]: TFTCharacterRole_data_json[TFTCharacterRole_header_keys[i]] for i in TFTCharacterRole_statistics_output_order}
        TFTCharacterRole_df: pandas.DataFrame = pandas.DataFrame(data = TFTCharacterRole_data_organized)
        # logPrint("正在优化云顶之弈角色定位数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Character Role dataframe ...")
        # optimize_bool_display(TFTCharacterRole_df)
        TFTCharacterRole_df = pandas.concat([pandas.DataFrame([TFTCharacterRole_header])[TFTCharacterRole_df.columns], TFTCharacterRole_df], ignore_index = True)
        self.TFTCharacterRole_df = TFTCharacterRole_df
        ##云顶之弈装备列表（TFT Item List）
        TFTItemList_statistics_output_order: list[int] = [0, 1, 2, 4, 5, 3, 6]
        TFTItemList_data_organized: dict[str, list[Any]] = {TFTItemList_header_keys[i]: TFTItemList_data_json[TFTItemList_header_keys[i]] for i in TFTItemList_statistics_output_order}
        TFTItemList_df: pandas.DataFrame = pandas.DataFrame(data = TFTItemList_data_organized)
        # logPrint("正在优化云顶之弈装备列表数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Item List dataframe ...")
        # optimize_bool_display(TFTItemList_df)
        TFTItemList_df = pandas.concat([pandas.DataFrame([TFTItemList_header])[TFTItemList_df.columns], TFTItemList_df], ignore_index = True)
        self.TFTItemList_df = TFTItemList_df
        ##云顶之弈装备（TFT Item）
        TFTItem_statistics_output_order: list[int] = [0, 1, 15, 41, 43, 42, 44, 14, 2, 11, 4, 27, 28, 5, 29, 30, 6, 31, 32, 13, 25, 7, 33, 34, 8, 35, 36, 9, 37, 38, 10, 3, 16, 45, 47, 46, 48, 12, 39, 40, 17, 18, 19, 20, 21, 22, 23, 24, 26, 49]
        TFTItem_data_organized: dict[str, list[Any]] = {TFTItem_header_keys[i]: TFTItem_data_json[TFTItem_header_keys[i]] for i in TFTItem_statistics_output_order}
        TFTItem_df: pandas.DataFrame = pandas.DataFrame(data = TFTItem_data_organized)
        logPrint("正在优化云顶之弈装备数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Item dataframe ...")
        optimize_bool_display(TFTItem_df)
        TFTItem_df = pandas.concat([pandas.DataFrame([TFTItem_header])[TFTItem_df.columns], TFTItem_df], ignore_index = True)
        self.TFTItem_df = TFTItem_df
        ##云顶之弈羁绊列表（TFT Trait List）
        TFTTraitList_statistics_output_order: list[int] = [0, 1, 3, 4, 2, 5]
        TFTTraitList_data_organized: dict[str, list[Any]] = {TFTTraitList_header_keys[i]: TFTTraitList_data_json[TFTTraitList_header_keys[i]] for i in TFTTraitList_statistics_output_order}
        TFTTraitList_df: pandas.DataFrame = pandas.DataFrame(data = TFTTraitList_data_organized)
        # logPrint("正在优化云顶之弈羁绊列表数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Trait List dataframe ...")
        # optimize_bool_display(TFTTraitList_df)
        TFTTraitList_df = pandas.concat([pandas.DataFrame([TFTTraitList_header])[TFTTraitList_df.columns], TFTTraitList_df], ignore_index = True)
        self.TFTTraitList_df = TFTTraitList_df
        ##云顶之弈羁绊（TFT Trait）
        TFTTrait_statistics_output_order: list[int] = [0, 1, 2, 11, 12, 6, 7, 10, 8, 9, 3, 13, 15, 14, 16, 4, 17, 19, 18, 20, 5]
        TFTTrait_data_organized: dict[str, list[Any]] = {TFTTrait_header_keys[i]: TFTTrait_data_json[TFTTrait_header_keys[i]] for i in TFTTrait_statistics_output_order}
        TFTTrait_df: pandas.DataFrame = pandas.DataFrame(data = TFTTrait_data_organized)
        logPrint("正在优化云顶之弈羁绊数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Trait dataframe ...")
        optimize_bool_display(TFTTrait_df)
        TFTTrait_df = pandas.concat([pandas.DataFrame([TFTTrait_header])[TFTTrait_df.columns], TFTTrait_df], ignore_index = True)
        self.TFTTrait_df = TFTTrait_df
        ##云顶之弈电脑玩家英雄（TFT PVE NPC）
        TFTPVENPC_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6, 9, 7, 10, 11, 8]
        TFTPVENPC_data_organized: dict[str, list[Any]] = {TFTPVENPC_header_keys[i]: TFTPVENPC_data_json[TFTPVENPC_header_keys[i]] for i in TFTPVENPC_statistics_output_order}
        TFTPVENPC_df: pandas.DataFrame = pandas.DataFrame(data = TFTPVENPC_data_organized)
        # logPrint("正在优化云顶之弈电脑玩家英雄数据框的逻辑值显示……\nOptimizing boolean value display of the TFT PVE NPC dataframe ...")
        # optimize_bool_display(TFTPVENPC_df)
        TFTPVENPC_df = pandas.concat([pandas.DataFrame([TFTPVENPC_header])[TFTPVENPC_df.columns], TFTPVENPC_df], ignore_index = True)
        self.TFTPVENPC_df = TFTPVENPC_df
        ##云顶之弈脚本（TFT Script）
        TFTScript_statistics_output_order: list[int] = [0, 1, 2, 3, 4]
        TFTScript_data_organized: dict[str, list[Any]] = {TFTScript_header_keys[i]: TFTScript_data_json[TFTScript_header_keys[i]] for i in TFTScript_statistics_output_order}
        TFTScript_df: pandas.DataFrame = pandas.DataFrame(data = TFTScript_data_organized)
        # logPrint("正在优化云顶之弈脚本数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Script dataframe ...")
        # optimize_bool_display(TFTScript_df)
        TFTScript_df = pandas.concat([pandas.DataFrame([TFTScript_header])[TFTScript_df.columns], TFTScript_df], ignore_index = True)
        self.TFTScript_df = TFTScript_df
        ##云顶之弈通告（TFT Announcement）
        TFTAnnouncement_statistics_output_order: list[int] = [0, 2, 7, 8, 3, 4, 1, 5, 6]
        TFTAnnouncement_data_organized: dict[str, list[Any]] = {TFTAnnouncement_header_keys[i]: TFTAnnouncement_data_json[TFTAnnouncement_header_keys[i]] for i in TFTAnnouncement_statistics_output_order}
        TFTAnnouncement_df: pandas.DataFrame = pandas.DataFrame(data = TFTAnnouncement_data_organized)
        # logPrint("正在优化云顶之弈通告数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Announcement dataframe ...")
        # optimize_bool_display(TFTAnnouncement_df)
        TFTAnnouncement_df = pandas.concat([pandas.DataFrame([TFTAnnouncement_header])[TFTAnnouncement_df.columns], TFTAnnouncement_df], ignore_index = True)
        self.TFTAnnouncement_df = TFTAnnouncement_df
        return 0
    
    def enqueue_tft_dataframe(self) -> None:
        '''
        将云顶之弈数据框追加到数据提取器基类的数据框队列尾部。<br>Append TFT dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.TFTSet_df.empty:
            TFTSet_ws: dict[str, Any] = self.worksheet_metadata["TFTSet"]
            sheet1_name: str = TFTSet_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTSet_ws["sheet_name_without_version"]
            TFTSet_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTSet_ws["dType"]), "dType": TFTSet_ws["dType"], "sheet_name": sheet1_name, "sheet": self.TFTSet_df}
            self.enqueue_df(TFTSet_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTShop_df.empty:
            TFTShop_ws: dict[str, Any] = self.worksheet_metadata["TFTShop"]
            sheet2_name: str = TFTShop_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTShop_ws["sheet_name_without_version"]
            TFTShop_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTShop_ws["dType"]), "dType": TFTShop_ws["dType"], "sheet_name": sheet2_name, "sheet": self.TFTShop_df}
            self.enqueue_df(TFTShop_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTShopContent_df.empty:
            TFTShopContent_ws: dict[str, Any] = self.worksheet_metadata["TFTShopContent"]
            sheet3_name: str = TFTShopContent_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTShopContent_ws["sheet_name_without_version"]
            TFTShopContent_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTShopContent_ws["dType"]), "dType": TFTShopContent_ws["dType"], "sheet_name": sheet3_name, "sheet": self.TFTShopContent_df}
            self.enqueue_df(TFTShopContent_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTDropRate_df.empty:
            TFTDropRate_ws: dict[str, Any] = self.worksheet_metadata["TFTDropRate"]
            sheet4_name: str = TFTDropRate_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTDropRate_ws["sheet_name_without_version"]
            TFTDropRate_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTDropRate_ws["dType"]), "dType": TFTDropRate_ws["dType"], "sheet_name": sheet4_name, "sheet": self.TFTDropRate_df}
            self.enqueue_df(TFTDropRate_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTStageRound_df.empty:
            TFTStageRound_ws: dict[str, Any] = self.worksheet_metadata["TFTStageRound"]
            sheet5_name: str = TFTStageRound_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTStageRound_ws["sheet_name_without_version"]
            TFTStageRound_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTStageRound_ws["dType"]), "dType": TFTStageRound_ws["dType"], "sheet_name": sheet5_name, "sheet": self.TFTStageRound_df}
            self.enqueue_df(TFTStageRound_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTRound_df.empty:
            TFTRound_ws: dict[str, Any] = self.worksheet_metadata["TFTRound"]
            sheet6_name: str = TFTRound_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTRound_ws["sheet_name_without_version"]
            TFTRound_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTRound_ws["dType"]), "dType": TFTRound_ws["dType"], "sheet_name": sheet6_name, "sheet": self.TFTRound_df}
            self.enqueue_df(TFTRound_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTPortal_df.empty:
            TFTPortal_ws: dict[str, Any] = self.worksheet_metadata["TFTPortal"]
            sheet7_name: str = TFTPortal_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTPortal_ws["sheet_name_without_version"]
            TFTPortal_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTPortal_ws["dType"]), "dType": TFTPortal_ws["dType"], "sheet_name": sheet7_name, "sheet": self.TFTPortal_df}
            self.enqueue_df(TFTPortal_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTEncounterDistribution_df.empty:
            TFTEncounterDistribution_ws: dict[str, Any] = self.worksheet_metadata["TFTEncounterDistribution"]
            sheet8_name: str = TFTEncounterDistribution_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTEncounterDistribution_ws["sheet_name_without_version"]
            TFTEncounterDistribution_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTEncounterDistribution_ws["dType"]), "dType": TFTEncounterDistribution_ws["dType"], "sheet_name": sheet8_name, "sheet": self.TFTEncounterDistribution_df}
            self.enqueue_df(TFTEncounterDistribution_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTEncounter_df.empty:
            TFTEncounter_ws: dict[str, Any] = self.worksheet_metadata["TFTEncounter"]
            sheet9_name: str = TFTEncounter_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTEncounter_ws["sheet_name_without_version"]
            TFTEncounter_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTEncounter_ws["dType"]), "dType": TFTEncounter_ws["dType"], "sheet_name": sheet9_name, "sheet": self.TFTEncounter_df}
            self.enqueue_df(TFTEncounter_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTUnitProperty_df.empty:
            TFTUnitProperty_ws: dict[str, Any] = self.worksheet_metadata["TFTUnitProperty"]
            sheet10_name: str = TFTUnitProperty_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTUnitProperty_ws["sheet_name_without_version"]
            TFTUnitProperty_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTUnitProperty_ws["dType"]), "dType": TFTUnitProperty_ws["dType"], "sheet_name": sheet10_name, "sheet": self.TFTUnitProperty_df}
            self.enqueue_df(TFTUnitProperty_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTCharacterRole_df.empty:
            TFTCharacterRole_ws: dict[str, Any] = self.worksheet_metadata["TFTCharacterRole"]
            sheet11_name: str = TFTCharacterRole_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTCharacterRole_ws["sheet_name_without_version"]
            TFTCharacterRole_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTCharacterRole_ws["dType"]), "dType": TFTCharacterRole_ws["dType"], "sheet_name": sheet11_name, "sheet": self.TFTCharacterRole_df}
            self.enqueue_df(TFTCharacterRole_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTItemList_df.empty:
            TFTItemList_ws: dict[str, Any] = self.worksheet_metadata["TFTItemList"]
            sheet12_name: str = TFTItemList_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTItemList_ws["sheet_name_without_version"]
            TFTItemList_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTItemList_ws["dType"]), "dType": TFTItemList_ws["dType"], "sheet_name": sheet12_name, "sheet": self.TFTItemList_df}
            self.enqueue_df(TFTItemList_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTItem_df.empty:
            TFTItem_ws: dict[str, Any] = self.worksheet_metadata["TFTItem"]
            sheet13_name: str = TFTItem_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTItem_ws["sheet_name_without_version"]
            TFTItem_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTItem_ws["dType"]), "dType": TFTItem_ws["dType"], "sheet_name": sheet13_name, "sheet": self.TFTItem_df}
            self.enqueue_df(TFTItem_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTTraitList_df.empty:
            TFTTraitList_ws: dict[str, Any] = self.worksheet_metadata["TFTTraitList"]
            sheet14_name: str = TFTTraitList_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTTraitList_ws["sheet_name_without_version"]
            TFTTraitList_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTTraitList_ws["dType"]), "dType": TFTTraitList_ws["dType"], "sheet_name": sheet14_name, "sheet": self.TFTTraitList_df}
            self.enqueue_df(TFTTraitList_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTTrait_df.empty:
            TFTTrait_ws: dict[str, Any] = self.worksheet_metadata["TFTTrait"]
            sheet15_name: str = TFTTrait_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTTrait_ws["sheet_name_without_version"]
            TFTTrait_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTTrait_ws["dType"]), "dType": TFTTrait_ws["dType"], "sheet_name": sheet15_name, "sheet": self.TFTTrait_df}
            self.enqueue_df(TFTTrait_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTPVENPC_df.empty:
            TFTPVENPC_ws: dict[str, Any] = self.worksheet_metadata["TFTPVENPC"]
            sheet16_name: str = TFTPVENPC_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTPVENPC_ws["sheet_name_without_version"]
            TFTPVENPC_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTPVENPC_ws["dType"]), "dType": TFTPVENPC_ws["dType"], "sheet_name": sheet16_name, "sheet": self.TFTPVENPC_df}
            self.enqueue_df(TFTPVENPC_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTScript_df.empty:
            TFTScript_ws: dict[str, Any] = self.worksheet_metadata["TFTScript"]
            sheet17_name: str = TFTScript_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTScript_ws["sheet_name_without_version"]
            TFTScript_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTScript_ws["dType"]), "dType": TFTScript_ws["dType"], "sheet_name": sheet17_name, "sheet": self.TFTScript_df}
            self.enqueue_df(TFTScript_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.TFTAnnouncement_df.empty:
            TFTAnnouncement_ws: dict[str, Any] = self.worksheet_metadata["TFTAnnouncement"]
            sheet18_name: str = TFTAnnouncement_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else TFTAnnouncement_ws["sheet_name_without_version"]
            TFTAnnouncement_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(TFTAnnouncement_ws["dType"]), "dType": TFTAnnouncement_ws["dType"], "sheet_name": sheet18_name, "sheet": self.TFTAnnouncement_df}
            self.enqueue_df(TFTAnnouncement_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_tft_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出云顶之弈数据到工作簿中。产生以下工作表：<br>Export TFT data to a workbook. The following worksheets are added:
        - 云顶之弈赛季（TFT Set）
        - 云顶之弈商店（TFT Shop）
        - 云顶之弈商店内容（TFT Shop Content）
        - 云顶之弈掉率表（TFT Drop Rate）
        - 云顶之弈回合阶段（TFT Stage Round）
        - 云顶之弈回合（TFT Round）
        - 云顶之弈传送门（TFT Portal）
        - 云顶之弈开场奇遇（TFT Encounter Distribution）
        - 云顶之弈奇遇（TFT Encounter）
        - 云顶之弈单位属性（TFT Unit Property）
        - 云顶之弈角色定位（TFT Character Role）
        - 云顶之弈装备列表（TFT Item List）
        - 云顶之弈装备（TFT Item）
        - 云顶之弈羁绊列表（TFT Trait List）
        - 云顶之弈羁绊（TFT Trait）
        - 云顶之弈电脑玩家英雄（TFT PVE NPC）
        - 云顶之弈脚本（TFT Script）
        - 云顶之弈通告（TFT Announcement）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 聚点危机地图二进制描述文件的本地路径。<br>A local path of Convergence map binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径。\nPath of exported file not specified.")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if self.TFTSet_df.empty or self.TFTShop_df.empty or self.TFTShopContent_df.empty or self.TFTDropRate_df.empty or self.TFTStageRound_df.empty or self.TFTRound_df.empty or self.TFTPortal_df.empty or self.TFTEncounterDistribution_df.empty or self.TFTEncounter_df.empty or self.TFTUnitProperty_df.empty or self.TFTCharacterRole_df.empty or self.TFTItemList_df.empty or self.TFTItem_df.empty or self.TFTTraitList_df.empty or self.TFTTrait_df.empty or self.TFTPVENPC_df.empty or self.TFTScript_df.empty or self.TFTAnnouncement_df.empty:
            status: int = self.build_tft_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if dense_export:
            TFTSet_df: pandas.DataFrame = eliminate_empty_fields(self.TFTSet_df)
            TFTShop_df: pandas.DataFrame = eliminate_empty_fields(self.TFTShop_df)
            TFTShopContent_df: pandas.DataFrame = eliminate_empty_fields(self.TFTShopContent_df)
            TFTDropRate_df: pandas.DataFrame = eliminate_empty_fields(self.TFTDropRate_df)
            TFTStageRound_df: pandas.DataFrame = eliminate_empty_fields(self.TFTStageRound_df)
            TFTRound_df: pandas.DataFrame = eliminate_empty_fields(self.TFTRound_df)
            TFTPortal_df: pandas.DataFrame = eliminate_empty_fields(self.TFTPortal_df)
            TFTEncounterDistribution_df: pandas.DataFrame = eliminate_empty_fields(self.TFTEncounterDistribution_df)
            TFTEncounter_df: pandas.DataFrame = eliminate_empty_fields(self.TFTEncounter_df)
            TFTUnitProperty_df: pandas.DataFrame = eliminate_empty_fields(self.TFTUnitProperty_df)
            TFTCharacterRole_df: pandas.DataFrame = eliminate_empty_fields(self.TFTCharacterRole_df)
            TFTItemList_df: pandas.DataFrame = eliminate_empty_fields(self.TFTItemList_df)
            TFTItem_df: pandas.DataFrame = eliminate_empty_fields(self.TFTItem_df)
            TFTTraitList_df: pandas.DataFrame = eliminate_empty_fields(self.TFTTraitList_df)
            TFTTrait_df: pandas.DataFrame = eliminate_empty_fields(self.TFTTrait_df)
            TFTPVENPC_df: pandas.DataFrame = eliminate_empty_fields(self.TFTPVENPC_df)
            TFTScript_df: pandas.DataFrame = eliminate_empty_fields(self.TFTScript_df)
        else:
            TFTAnnouncement_df = self.TFTAnnouncement_df
            TFTSet_df = self.TFTSet_df
            TFTShop_df = self.TFTShop_df
            TFTShopContent_df = self.TFTShopContent_df
            TFTDropRate_df = self.TFTDropRate_df
            TFTStageRound_df = self.TFTStageRound_df
            TFTRound_df = self.TFTRound_df
            TFTPortal_df = self.TFTPortal_df
            TFTEncounterDistribution_df = self.TFTEncounterDistribution_df
            TFTEncounter_df = self.TFTEncounter_df
            TFTUnitProperty_df = self.TFTUnitProperty_df
            TFTCharacterRole_df = self.TFTCharacterRole_df
            TFTItemList_df = self.TFTItemList_df
            TFTItem_df = self.TFTItem_df
            TFTTraitList_df = self.TFTTraitList_df
            TFTTrait_df = self.TFTTrait_df
            TFTPVENPC_df = self.TFTPVENPC_df
            TFTScript_df = self.TFTScript_df
            TFTAnnouncement_df = self.TFTAnnouncement_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["TFTSet"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTSet"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["TFTShop"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTShop"]["sheet_name_without_version"]
        sheet3_name: str = self.worksheet_metadata["TFTShopContent"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTShopContent"]["sheet_name_without_version"]
        sheet4_name: str = self.worksheet_metadata["TFTDropRate"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTDropRate"]["sheet_name_without_version"]
        sheet5_name: str = self.worksheet_metadata["TFTStageRound"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTStageRound"]["sheet_name_without_version"]
        sheet6_name: str = self.worksheet_metadata["TFTRound"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTRound"]["sheet_name_without_version"]
        sheet7_name: str = self.worksheet_metadata["TFTPortal"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTPortal"]["sheet_name_without_version"]
        sheet8_name: str = self.worksheet_metadata["TFTEncounterDistribution"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTEncounterDistribution"]["sheet_name_without_version"]
        sheet9_name: str = self.worksheet_metadata["TFTEncounter"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTEncounter"]["sheet_name_without_version"]
        sheet10_name: str = self.worksheet_metadata["TFTUnitProperty"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTUnitProperty"]["sheet_name_without_version"]
        sheet11_name: str = self.worksheet_metadata["TFTCharacterRole"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTCharacterRole"]["sheet_name_without_version"]
        sheet12_name: str = self.worksheet_metadata["TFTItemList"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTItemList"]["sheet_name_without_version"]
        sheet13_name: str = self.worksheet_metadata["TFTItem"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTItem"]["sheet_name_without_version"]
        sheet14_name: str = self.worksheet_metadata["TFTTraitList"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTTraitList"]["sheet_name_without_version"]
        sheet15_name: str = self.worksheet_metadata["TFTTrait"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTTrait"]["sheet_name_without_version"]
        sheet16_name: str = self.worksheet_metadata["TFTPVENPC"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTPVENPC"]["sheet_name_without_version"]
        sheet17_name: str = self.worksheet_metadata["TFTScript"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTScript"]["sheet_name_without_version"]
        sheet18_name: str = self.worksheet_metadata["TFTAnnouncement"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["TFTAnnouncement"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(TFTSet_df.drop(labels = ["BotSkillData SkillAxes", "VfxResourceResolver resourceMap"], axis = 1)).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(TFTShop_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    addDefaultStyle(TFTShopContent_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    addDefaultStyle(TFTDropRate_df).to_excel(excel_writer = writer, sheet_name = sheet4_name)
                    addDefaultStyle(TFTStageRound_df).to_excel(excel_writer = writer, sheet_name = sheet5_name)
                    addDefaultStyle(TFTRound_df).to_excel(excel_writer = writer, sheet_name = sheet6_name)
                    addDefaultStyle(TFTPortal_df).to_excel(excel_writer = writer, sheet_name = sheet7_name)
                    addDefaultStyle(TFTEncounterDistribution_df).to_excel(excel_writer = writer, sheet_name = sheet8_name[:31])
                    addDefaultStyle(TFTEncounter_df).to_excel(excel_writer = writer, sheet_name = sheet9_name)
                    addDefaultStyle(TFTUnitProperty_df).to_excel(excel_writer = writer, sheet_name = sheet10_name)
                    addDefaultStyle(TFTCharacterRole_df).to_excel(excel_writer = writer, sheet_name = sheet11_name)
                    addDefaultStyle(TFTItemList_df).to_excel(excel_writer = writer, sheet_name = sheet12_name)
                    addDefaultStyle(TFTItem_df).to_excel(excel_writer = writer, sheet_name = sheet13_name)
                    addDefaultStyle(TFTTraitList_df).to_excel(excel_writer = writer, sheet_name = sheet14_name)
                    addDefaultStyle(TFTTrait_df).to_excel(excel_writer = writer, sheet_name = sheet15_name)
                    addDefaultStyle(TFTPVENPC_df).to_excel(excel_writer = writer, sheet_name = sheet16_name)
                    addDefaultStyle(TFTScript_df).to_excel(excel_writer = writer, sheet_name = sheet17_name)
                    addDefaultStyle(TFTAnnouncement_df).to_excel(excel_writer = writer, sheet_name = sheet18_name)
                    for sheet_name in [sheet1_name, sheet2_name, sheet3_name, sheet4_name, sheet5_name, sheet6_name, sheet7_name, sheet8_name[:31], sheet9_name, sheet10_name, sheet11_name, sheet12_name, sheet13_name, sheet14_name, sheet15_name, sheet16_name, sheet17_name, sheet18_name]:
                        if sheet_name in writer.sheets:
                            worksheet: Worksheet = writer.sheets[sheet_name]
                            if worksheet.calculate_dimension() != "A1:A1":
                                worksheet.cell(row = 1, column = 1, value = self.patch) #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont: str = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"云顶之弈数据已导出到{self.wbPath}。\nTFT data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出云顶之弈数据到网页中。产生以下文件：<br>Export TFT data into html files. The following files are produced:
        - 云顶之弈商店（TFT Shop）
        - 云顶之弈回合阶段（TFT Stage Round）
        - 云顶之弈传送门（TFT Portal）
        - 云顶之弈角色定位（TFT Character Role）
        - 云顶之弈装备（TFT Items）
        - 云顶之弈强化符文（TFT Augments）
        - 云顶之弈羁绊（TFT Traits）
        - 云顶之弈通告（TFT Announcement）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 聚点危机地图二进制描述文件的本地路径。<br>A local path of Convergence map binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径。\nPath of exported file not specified.")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if self.TFTSet_df.empty or self.TFTShop_df.empty or self.TFTShopContent_df.empty or self.TFTDropRate_df.empty or self.TFTStageRound_df.empty or self.TFTRound_df.empty or self.TFTPortal_df.empty or self.TFTEncounterDistribution_df.empty or self.TFTEncounter_df.empty or self.TFTUnitProperty_df.empty or self.TFTCharacterRole_df.empty or self.TFTItemList_df.empty or self.TFTItem_df.empty or self.TFTTraitList_df.empty or self.TFTTrait_df.empty or self.TFTPVENPC_df.empty or self.TFTScript_df.empty or self.TFTAnnouncement_df.empty:
            status: int = self.build_tft_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #云顶之弈商店（TFT Shop）
        if len(self.TFTShop_df) > 1:
            TFTShop_df_web: pandas.DataFrame = self.TFTShop_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AbilityIconUrls: list[str] = list(map(lambda x: "" if x == "" else self.url2image(self.assetPath2url(self.version, x)), self.TFTShop_df.loc[1:, "AbilityIconPath"].to_list()))
            TeamPlannerPortraitUrls: list[str] = list(map(lambda x: "" if x == "" else self.url2image(self.assetPath2url(self.version, x)), self.TFTShop_df.loc[1:, "TeamPlannerPortraitPath"].to_list()))
            TFTShop_df_web.insert(len(TFTShop_df_web.columns), "AbilityIconUrl", ["技能图标网址"] + AbilityIconUrls)
            TFTShop_df_web.insert(len(TFTShop_df_web.columns), "TeamPlannerPortraitUrl", ["用于小队规划器的肖像网址"] + TeamPlannerPortraitUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mName",
                "{4d4e5cf5}",
                "TeamPlannerPortraitUrl",
                "AbilityIconUrl",
                "mDisplayNameTra_content_zh",
                "mDisplayNameTra_content_en",
                "mRarity",
                "BaseCost",
                "mAbilityNameTra_content_zh",
                "mAbilityNameTra_content_en",
                "mDescriptionTra_content_zh_burn",
                "mDescriptionTra_content_en_burn"
            ]
            TFTShop_df_web = TFTShop_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            TFTShop_df_styled: pandas.io.formats.style.Styler = TFTShop_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:7]
            TFTShop_df_styled = TFTShop_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            TFTShop_htmltable: str = TFTShop_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            TFTShop_htmltable = '<meta charset="UTF-8">\n' + TFTShop_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"TFTShop_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(TFTShop_htmltable)
        #云顶之弈回合阶段（TFT Stage Round）
        if len(self.TFTStageRound_df) > 1 and len(self.TFTRound_df) > 1: #正常情况下，如果两个数据框都有记录，一定是能对应上的（In normal cases, if both dataframes have records, they must be matched）
            TFTStageRound_df_web: pandas.DataFrame = pandas.merge(self.TFTStageRound_df, self.TFTRound_df.rename(columns = {"key": "roundKey"}), left_on = "round", right_on = "roundKey", how = "inner")
            TFTStageRound_df_web.drop("roundKey", axis = 1)
            ##将图标路径转换为网址（Transform icon paths into urls）
            mIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTStageRound_df_web.loc[1:, "mIconPath"].to_list()))
            mRoundUpcomingIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTStageRound_df_web.loc[1:, "mRoundUpcomingIconPath"].to_list()))
            mRoundActiveIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTStageRound_df_web.loc[1:, "mRoundActiveIconPath"].to_list()))
            mRoundResultNoneIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTStageRound_df_web.loc[1:, "mRoundResultNoneIconPath"].to_list()))
            mRoundResultWinIconUrls: list[str] = list(map(lambda x: "" if x == "" else self.url2image(self.assetPath2url(self.version, x)), TFTStageRound_df_web.loc[1:, "mRoundResultWinIconPath"].to_list()))
            mRoundResultLossIconUrls: list[str] = list(map(lambda x: "" if x == "" else self.url2image(self.assetPath2url(self.version, x)), TFTStageRound_df_web.loc[1:, "mRoundResultLossIconPath"].to_list()))
            mRoundResultDrawIconUrls: list[str] = list(map(lambda x: "" if x == "" else self.url2image(self.assetPath2url(self.version, x)), TFTStageRound_df_web.loc[1:, "mRoundResultDrawIconPath"].to_list()))
            TFTStageRound_df_web.insert(len(TFTStageRound_df_web.columns), "mIconUrl", ["缩略图网址"] + mIconUrls)
            TFTStageRound_df_web.insert(len(TFTStageRound_df_web.columns), "mRoundUpcomingIconUrl", ["即将到来的回合缩略图网址"] + mRoundUpcomingIconUrls)
            TFTStageRound_df_web.insert(len(TFTStageRound_df_web.columns), "mRoundActiveIconUrl", ["当前回合缩略图网址"] + mRoundActiveIconUrls)
            TFTStageRound_df_web.insert(len(TFTStageRound_df_web.columns), "mRoundResultNoneIconUrl", ["无回合结果缩略图网址"] + mRoundResultNoneIconUrls)
            TFTStageRound_df_web.insert(len(TFTStageRound_df_web.columns), "mRoundResultWinIconUrl", ["回合胜利缩略图网址"] + mRoundResultWinIconUrls)
            TFTStageRound_df_web.insert(len(TFTStageRound_df_web.columns), "mRoundResultLossIconUrl", ["回合失败缩略图网址"] + mRoundResultLossIconUrls)
            TFTStageRound_df_web.insert(len(TFTStageRound_df_web.columns), "mRoundResultDrawIconUrl", ["平局缩略图网址"] + mRoundResultDrawIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "key",
                "round_burn",
                "mDisplayNameTra_content_zh",
                "mDisplayNameTra_content_en",
                "mDefaultTooltipTra_content_zh",
                "mDefaultTooltipTra_content_en",
                "mIconUrl",
                "mRoundUpcomingIconUrl",
                "mRoundActiveIconUrl",
                "mRoundResultNoneIconUrl",
                "mRoundResultWinIconUrl",
                "mRoundResultLossIconUrl",
                "mRoundResultDrawIconUrl",
            ]
            TFTStageRound_df_web = TFTStageRound_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            TFTStageRound_df_styled: pandas.io.formats.style.Styler = TFTStageRound_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:4] + columns_to_export[-7:]
            TFTStageRound_df_styled = TFTStageRound_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            TFTStageRound_htmltable: str = TFTStageRound_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            TFTStageRound_htmltable = '<meta charset="UTF-8">\n' + TFTStageRound_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"TFTStageRound_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(TFTStageRound_htmltable)
        #云顶之弈传送门（TFT Portal）
        if len(self.TFTPortal_df) > 1:
            TFTPortal_df_web: pandas.DataFrame = self.TFTPortal_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            iconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.TFTPortal_df.loc[1:, "IconPath"].to_list()))
            TFTPortal_df_web.insert(len(TFTPortal_df_web.columns), "IconUrl", ["缩略图网址"] + iconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "name",
                "RegionName",
                "IconUrl",
                "RegionTra_content_zh",
                "RegionTra_content_en",
                "type",
                "ShortDescriptionTra_content_zh_burn",
                "ShortDescriptionTra_content_en_burn",
                "LongDescriptionTra_content_zh_burn",
                "LongDescriptionTra_content_en_burn"
            ]
            TFTPortal_df_web = TFTPortal_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            TFTPortal_df_styled: pandas.io.formats.style.Styler = TFTPortal_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:6]
            TFTPortal_df_styled = TFTPortal_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            TFTPortal_htmltable: str = TFTPortal_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            TFTPortal_htmltable = '<meta charset="UTF-8">\n' + TFTPortal_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"TFTPortal_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(TFTPortal_htmltable)
        #云顶之弈装备（TFT Items）
        TFTItem_df_web: pandas.DataFrame = pandas.concat([self.TFTItem_df.iloc[:1, :], self.TFTItem_df[self.TFTItem_df["IsAugment"] == ""]], ignore_index = True)
        if len(TFTItem_df_web) > 1:
            ##将图标路径转换为网址（Transform icon paths into urls）
            mIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTItem_df_web.loc[1:, "mIconPath"].to_list()))
            TFTItem_df_web.insert(len(TFTItem_df_web.columns), "mIconUrl", ["缩略图网址"] + mIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mName",
                "mIconUrl",
                "mDisplayNameTra_content_zh_burn",
                "mDisplayNameTra_content_en_burn",
                "mComposition mDisplayNameTra_contents_zh",
                "mComposition mDisplayNameTra_contents_en",
                "mAlternativeCompositions mDisplayNameTra_contents_zh",
                "mAlternativeCompositions mDisplayNameTra_contents_en",
                "MutuallyExclusiveItems mDisplayNameTra_contents_zh",
                "MutuallyExclusiveItems mDisplayNameTra_contents_en",
                "IncompatibleTraits mDisplayNameTra_contents_zh",
                "IncompatibleTraits mDisplayNameTra_contents_en",
                "AssociatedTraits mDisplayNameTra_contents_zh",
                "AssociatedTraits mDisplayNameTra_contents_en",
                "BonusTrait mDisplayNameTra_content_zh",
                "BonusTrait mDisplayNameTra_content_en",
                "mDescriptionNameTra_content_zh_burn",
                "mDescriptionNameTra_content_en_burn"
            ]
            TFTItem_df_web = TFTItem_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            TFTItem_df_styled: pandas.io.formats.style.Styler = TFTItem_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:16]
            TFTItem_df_styled = TFTItem_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            TFTItem_htmltable: str = TFTItem_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            TFTItem_htmltable = '<meta charset="UTF-8">\n' + TFTItem_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"TFTItem_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(TFTItem_htmltable)
        #云顶之弈强化符文（TFT Augments）
        TFTAugment_df_web: pandas.DataFrame = pandas.concat([self.TFTItem_df.iloc[:1, :], self.TFTItem_df[self.TFTItem_df["IsAugment"] == "√"]], ignore_index = True)
        if len(TFTAugment_df_web) > 1:
            ##将图标路径转换为网址（Transform icon paths into urls）
            mIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTAugment_df_web.loc[1:, "mIconPath"].to_list()))
            TFTAugment_df_web.insert(len(TFTAugment_df_web.columns), "mIconUrl", ["缩略图网址"] + mIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mName",
                "mIconUrl",
                "mDisplayNameTra_content_zh_burn",
                "mDisplayNameTra_content_en_burn",
                "mComposition mDisplayNameTra_contents_zh",
                "mComposition mDisplayNameTra_contents_en",
                "mAlternativeCompositions mDisplayNameTra_contents_zh",
                "mAlternativeCompositions mDisplayNameTra_contents_en",
                "MutuallyExclusiveItems mDisplayNameTra_contents_zh",
                "MutuallyExclusiveItems mDisplayNameTra_contents_en",
                "IncompatibleTraits mDisplayNameTra_contents_zh",
                "IncompatibleTraits mDisplayNameTra_contents_en",
                "AssociatedTraits mDisplayNameTra_contents_zh",
                "AssociatedTraits mDisplayNameTra_contents_en",
                "BonusTrait mDisplayNameTra_content_zh",
                "BonusTrait mDisplayNameTra_content_en",
                "mDescriptionNameTra_content_zh_burn",
                "mDescriptionNameTra_content_en_burn"
            ]
            TFTAugment_df_web = TFTAugment_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            TFTAugment_df_styled: pandas.io.formats.style.Styler = TFTAugment_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:16]
            TFTAugment_df_styled = TFTAugment_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            TFTAugment_htmltable: str = TFTAugment_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            TFTAugment_htmltable = '<meta charset="UTF-8">\n' + TFTAugment_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"TFTAugment_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(TFTAugment_htmltable)
        #云顶之弈羁绊（TFT Traits）
        if len(self.TFTTrait_df) > 1:
            TFTTrait_df_web: pandas.DataFrame = self.TFTTrait_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            mIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTTrait_df_web.loc[1:, "mIconPath"].to_list()))
            TFTTrait_df_web.insert(len(TFTTrait_df_web.columns), "mIconUrl", ["缩略图网址"] + mIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mName",
                "mIconUrl",
                "mDisplayNameTra_content_zh",
                "mDisplayNameTra_content_en",
                "TraitType",
                "{0247448b}_content_zh_burn",
                "{0247448b}_content_en_burn",
                "mDescriptionNameTra_content_zh_burn",
                "mDescriptionNameTra_content_en_burn"
            ]
            TFTTrait_df_web = TFTTrait_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            TFTTrait_df_styled: pandas.io.formats.style.Styler = TFTTrait_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:5]
            TFTTrait_df_styled = TFTTrait_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            TFTTrait_htmltable: str = TFTTrait_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            TFTTrait_htmltable = '<meta charset="UTF-8">\n' + TFTTrait_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"TFTTrait_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(TFTTrait_htmltable)
        #云顶之弈通告（TFT Annoucements）
        if len(self.TFTAnnouncement_df) > 1:
            TFTAnnouncement_df_web: pandas.DataFrame = self.TFTAnnouncement_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            mIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), TFTAnnouncement_df_web.loc[1:, "mIconPath"].to_list()))
            TFTAnnouncement_df_web.insert(len(TFTAnnouncement_df_web.columns), "mIconUrl", ["缩略图网址"] + mIconUrls)
            ##保留小数（Round）
            TFTAnnouncement_df_web.loc[1:, "mDuration"] = TFTAnnouncement_df_web.loc[1:, "mDuration"].apply(lambda x: self.aRound(x, 5))
            TFTAnnouncement_df_web.loc[1:, "mDelay"] = TFTAnnouncement_df_web.loc[1:, "mDelay"].apply(lambda x: "" if x == "" else self.aRound(x, 5))
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mIconUrl",
                "mTitleTra_content_zh",
                "mTitleTra_content_en",
                "mDuration",
                "mDelay"
            ]
            TFTAnnouncement_df_web = TFTAnnouncement_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            TFTAnnouncement_df_styled: pandas.io.formats.style.Styler = TFTAnnouncement_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:]
            TFTAnnouncement_df_styled = TFTAnnouncement_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            TFTAnnouncement_htmltable: str = TFTAnnouncement_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            TFTAnnouncement_htmltable = '<meta charset="UTF-8">\n' + TFTAnnouncement_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"TFTAnnouncement_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(TFTAnnouncement_htmltable)
