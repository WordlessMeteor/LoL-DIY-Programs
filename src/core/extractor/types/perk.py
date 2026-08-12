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
from src.core.config.headers import perkstyle_header, perk_header
from src.core.extractor.base import LoLDataExtractor

class PerkExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个符文提取器对象。<br>Initialize a CheatExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.perk_ready: bool = False
        self.perkstyle_df: pandas.DataFrame = pandas.DataFrame()
        self.perk_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.perk_ready = False
    
    def get_perk_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取符文二进制描述数据。<br>Get binary description data of perks online.
        '''
        logPrint = self.log.logPrint
        perks_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/perks.cdtb.bin.json"
        if perks_bin_url in self.__class__.data_cache["online"]:
            self.perks_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][perks_bin_url]
        else:
            source, status, self.session = requestUrl("GET", perks_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("符文信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nPerk data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(perks_bin_url))
                else:
                    logPrint("符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nPerk data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            self.perks_bin = source.json()
            self.perks_bin = self.resolve_bin_hash(self.perks_bin)
            self.__class__.data_cache["online"][perks_bin_url] = self.perks_bin
        self.perk_ready = True
    
    def read_perk_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取符文二进制描述数据。<br>Get binary description data of perks offline.
        
        :param path: 符文二进制描述文件的本地路径。<br>A local path of perk binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        perks_bin_path: str = path
        if perks_bin_path in self.__class__.data_cache["local"]:
            self.perks_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][perks_bin_path]
        else:
            with open(perks_bin_path, "r", encoding = "utf-8") as fp:
                self.perks_bin = json.load(fp)
            self.perks_bin = self.resolve_bin_hash(self.perks_bin)
            self.__class__.data_cache["local"][perks_bin_path] = self.perks_bin
        self.perk_ready = True
    
    def build_perk_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建符文数据框。<br>Build perk dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 符文二进制描述文件的本地路径。<br>A local path of perk binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.perk_ready:
            #获取符文信息（Get perk information）
            logPrint("正在读取符文数据……\nReading perk data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_perk_data(path = path)
            else:
                self.get_perk_data()
            if not self.perk_ready:
                logPrint("符文数据尚未准备就绪！\nPerk data not prepared!")
                return 2
        
        #提取指令字典（Extract spell dictionary）
        self.init_mSpells()
        for (key, value) in self.perks_bin.items():
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        
        #构建从符文序号到符文数据的映射（Build a map from mPerkId to the corresponding perk data）
        perkstyleKey_perkstyleId_map: dict[int, str] = {}
        perkKey_perkId_map: dict[int, str] = {}
        perkstyle_perkKey_map: dict[str, tuple[str, int]] = {} #键是符文主键，值是由符文系主键和符文系槽位序号组成的二元组（Each key is a perk key, and each value is a two-tuple composed of perkstyle key and slot index）
        for (key, value) in self.perks_bin.items():
            if key != "__linked" and value["__type"] == "PerkStyle":
                perkstyleKey_perkstyleId_map[value["mPerkStyleId"]] = key #已事先确定所有符文系对象中都有mPerkStyleId键（Confirmed in advance that all PerkStyle objects have `mPerkStyleId` key）
                for i in range(len(value["mSlots"])):
                    slot: dict[str, Any] = value["mSlots"][i]
                    for perkKey in slot["mPerks"]:
                        perkstyle_perkKey_map[perkKey] = (key, i)
            elif key != "__linked" and value["__type"] == "Perk":
                perkKey_perkId_map[value["mPerkId"]] = key #已事先确定所有符文对象中都有mPerkId键（Confirmed in advance that all Perk objects have `mPerkId` key）
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建符文数据框……\nBuilding the perk dataframes ...", print_time = True)
        ##符文系（Perkstyle）
        perkstyle_header_keys: list[str] = list(perkstyle_header.keys())
        perkstyle_data: dict[str, list[Any]] = {key: [] for key in perkstyle_header_keys}
        perkstyle_data_json: dict[str, list[Any]] = copy.deepcopy(perkstyle_data)
        ##符文（Perk）
        perk_header_keys: list[str] = list(perk_header.keys())
        perk_data: dict[str, list[Any]] = {key: [] for key in perk_header_keys}
        perk_data_json: dict[str, list[Any]] = copy.deepcopy(perk_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.perks_bin.items():
            if key1 != "__linked" and value["__type"] == "PerkStyle":
                for i in range(len(perkstyle_header_keys)):
                    key: str = perkstyle_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 20:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i == 7: #高级符文系（`mIsAdvancedStyle`）
                                    to_append = False
                                else:
                                    to_append = ""
                                break
                        else:
                            to_append = tmp_ptr
                    elif i <= 26:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = value[subkey1] #此处代码写法和其它地方有些不同。它不是引用列表上次追加的数据，而是直接从原始数据中获取。这是因为符文系数据相对比较平衡，很多键基本上都是常驻的（Here the code style somehow differs from other places. It doesn't use the data recently appended to the list; instead, it obtains the raw data. This is because perkstyle data are relatively balanced; many keys aren't flexible）
                        to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                    elif i == 27 or i == 28: #可用副系名称（中文）和可用副系名称（英文）（`mAllowedSubStyles mDisplayNameLocalizationKey_contents_zh` and `mAllowedSubStyles mDisplayNameLocalizationKey_contents_en`）
                        strtable_locale = strtable_lol_target if i == 27 else strtable_lol_default
                        mAllowedSubStyleNames: list[str] = []
                        for substyleId in value["mAllowedSubStyles"]:
                            if substyleId in perkstyleKey_perkstyleId_map and perkstyleKey_perkstyleId_map[substyleId] in self.perks_bin:
                                mDisplayNameLocalizationKey: str = self.perks_bin[perkstyleKey_perkstyleId_map[substyleId]]["mDisplayNameLocalizationKey"]
                                mAllowedSubStyleNames.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                            else:
                                mAllowedSubStyleNames.append(substyleId)
                        to_append = mAllowedSubStyleNames
                    elif i == 29 or i == 30: #渲染插画时默认使用符文名称（中文）和渲染插画时默认使用符文名称（英文）（`mDefaultPerksWhenSplashed mDisplayNameLocalizationKey_contents_zh` and `mDefaultPerksWhenSplashed mDisplayNameLocalizationKey_contents_en`）
                        strtable_locale = strtable_lol_target if i == 29 else strtable_lol_default
                        mDefaultPerksWhenSplashed_names: list[str] = []
                        for perk_key in value["mDefaultPerksWhenSplashed"]:
                            if perk_key in self.perks_bin:
                                mDisplayNameLocalizationKey: str = self.perks_bin[perk_key]["mDisplayNameLocalizationKey"]
                                mDefaultPerksWhenSplashed_names.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                            else:
                                mDefaultPerksWhenSplashed_names.append(perk_key)
                        to_append = mDefaultPerksWhenSplashed_names
                    elif i <= 54: #搭配各副系时的默认属性符文子键（`mDefaultStatModsPerSubStyle`'s subkeys）
                        substyle_index: int = (i - 31) // 6
                        defaultStatMods: dict[str, int | list[str] | str] = value["mDefaultStatModsPerSubStyle"][substyle_index]
                        if (i - 31) % 6 <= 1: #副系序号和属性符文（`mStyleId` and `mPerks`）
                            subkey: str = key.split()[1]
                            to_append = defaultStatMods[subkey]
                        elif (i - 31) % 6 <= 3: #本地化副系名称（Localized substyle name）
                            substyleId = defaultStatMods["mStyleId"]
                            mDisplayNameLocalizationKey: str = self.perks_bin[perkstyleKey_perkstyleId_map[substyleId]]["mDisplayNameLocalizationKey"]
                            strtable_locale = strtable_lol_target if (i - 31) % 6 == 2 else strtable_lol_default
                            to_append = self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey)
                        else: #本地化属性符文名称（Localized stat mod names）
                            strtable_locale = strtable_lol_target if (i - 31) % 6 == 4 else strtable_lol_default
                            mPerks_names: list[str] = []
                            for perk_key in defaultStatMods["mPerks"]:
                                if perk_key in self.perks_bin:
                                    mDisplayNameLocalizationKey: str = self.perks_bin[perk_key]["mDisplayNameLocalizationKey"]
                                    mPerks_names.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                                else:
                                    mPerks_names.append(perk_key)
                            to_append = mPerks_names
                    elif i <= 82: #槽位子键（`mSlots`' subkeys）
                        slot_index: int = (i - 55) // 7
                        slot: dict[str, int | list[str] | str] = value["mSlots"][slot_index]
                        if (i - 55) % 7 <= 2: #标签键、类型和符文（`mSlotLabelKey`, `mType` and `mPerks`）
                            subkey: str = key.split()[1]
                            to_append = slot[subkey]
                        elif (i - 55) % 7 <= 4: #本地化标签（Localized label）
                            tooltip_key: str = slot["mSlotLabelKey"]
                            strtable_locale = strtable_lol_target if (i - 55) % 7 == 3 else strtable_lol_default
                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        else: #本地化符文名称（Localized perk names）
                            strtable_locale = strtable_lol_target if (i - 55) % 7 == 5 else strtable_lol_default
                            mPerks_names: list[str] = []
                            for perk_key in slot["mPerks"]:
                                if perk_key in self.perks_bin:
                                    mDisplayNameLocalizationKey: str = self.perks_bin[perk_key]["mDisplayNameLocalizationKey"]
                                    mPerks_names.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                                else:
                                    mPerks_names.append(perk_key)
                            to_append = mPerks_names
                    else: #本地化槽位标签（Localized slot labels）
                        strtable_locale = strtable_lol_target if i == 83 else strtable_lol_default
                        slotNames: list[str] = []
                        for slot_key in value["mSlotlinks"]:
                            if slot_key in self.perks_bin:
                                tooltip_key: str = self.perks_bin[slot_key]["mSlotLabelKey"]
                                slotNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                            else:
                                slotNames.append(slot_key)
                        to_append = slotNames
                    perkstyle_data[key].append(to_append)
                    perkstyle_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "Perk":
                for i in range(len(perk_header_keys)):
                    key: str = perk_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append = key1
                    elif i <= 20:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i == 11 or i == 18: #可叠加和默认符文（`mStackable` and `mDefault`）
                                    to_append = False
                                elif i == 12: #可用性（`mEnabled`）
                                    to_append = True
                                else:
                                    to_append = ""
                                break
                        else:
                            to_append = tmp_ptr
                    elif i <= 36:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = perk_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            if "mScript" in value and "mSpellScriptData" in value["mScript"]:
                                mSpellScriptData = value["mScript"]["mSpellScriptData"]
                            else:
                                mSpellScriptData = None
                            if mSpellScriptData == None:
                                to_append = ""
                            else:
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpellScriptData, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    elif i <= 38: #本地化赛后结算描述（Localized `mEndOfGameStatDescriptions`）
                        if "mEndOfGameStatDescriptions" in value:
                            strtable_locale = strtable_lol_target if i == 37 else strtable_lol_default
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_locale, x, default = x), value["mEndOfGameStatDescriptions"]))
                        else:
                            to_append = ""
                    else:
                        if key1 in perkstyle_perkKey_map:
                            perkstyleKey, slotIndex = perkstyle_perkKey_map[key1]
                            if i == 39: #所属符文系主键（`belonging_perkstyle_key`）
                                to_append = perkstyleKey
                            elif i == 40 or i == 41: #所属符文系显示名（Belonging perkstyle's display name）
                                subkey2: str = pStrConst.search(key).group()
                                subkey1: str = key.replace(subkey2, "")
                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                tooltip_key: str = self.perks_bin[perkstyleKey]["mDisplayNameLocalizationKey"]
                                to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            else: #所属符文系槽位序号（`belonging_perkstyle_slotIndex`）
                                to_append = slotIndex
                        else:
                            to_append = ""
                    perk_data[key].append(to_append)
                    perk_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        perkstyle_statistics_output_order: list[int] = [0, 1, 2, 3, 21, 22, 7, 4, 23, 24, 8, 27, 28, 9, 16, 83, 84, 15, 55, 58, 59, 56, 57, 60, 61, 62, 65, 66, 63, 64, 67, 68, 69, 72, 73, 70, 71, 74, 75, 76, 79, 80, 77, 78, 81, 82, 14, 31, 33, 34, 32, 35, 36, 37, 39, 40, 38, 41, 42, 43, 45, 46, 44, 47, 48, 49, 51, 52, 50, 53, 54, 5, 25, 26, 13, 29, 30, 17, 18, 19, 6, 10, 11, 12, 20]
        perkstyle_data_organized: dict[str, list[Any]] = {perkstyle_header_keys[i]: perkstyle_data_json[perkstyle_header_keys[i]] for i in perkstyle_statistics_output_order}
        perkstyle_df: pandas.DataFrame = pandas.DataFrame(data = perkstyle_data_organized)
        perkstyle_df = perkstyle_df.sort_values(by = "mPerkStyleId", ascending = True, ignore_index = True)
        logPrint("正在优化符文系数据框的逻辑值显示……\nOptimizing boolean value display of the perkstyle dataframe ...")
        optimize_bool_display(perkstyle_df)
        perkstyle_df = pandas.concat([pandas.DataFrame([perkstyle_header])[perkstyle_df.columns], perkstyle_df], ignore_index = True)
        self.perkstyle_df = perkstyle_df
        perk_statistics_output_order: list[int] = [0, 1, 2, 3, 21, 22, 40, 41, 42, 12, 11, 18, 4, 23, 25, 24, 26, 9, 5, 27, 28, 6, 29, 31, 30, 32, 7, 33, 35, 34, 36, 8, 37, 38, 17, 19, 13, 14, 15, 20, 10, 16]
        perk_data_organized: dict[str, list[Any]] = {perk_header_keys[i]: perk_data_json[perk_header_keys[i]] for i in perk_statistics_output_order}
        perk_df: pandas.DataFrame = pandas.DataFrame(data = perk_data_organized)
        perk_df = perk_df.sort_values(by = "mPerkId", ascending = True, ignore_index = True)
        logPrint("正在优化符文数据框的逻辑值显示……\nOptimizing boolean value display of the perk dataframe ...")
        optimize_bool_display(perk_df)
        perk_df = pandas.concat([pandas.DataFrame([perk_header])[perk_df.columns], perk_df], ignore_index = True)
        self.perk_df = perk_df
        return 0
    
    def enqueue_perk_dataframe(self) -> None:
        '''
        将符文数据框追加到数据提取器基类的数据框队列尾部。<br>Append perk dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.perkstyle_df.empty:
            perkstyle_ws: dict[str, Any] = self.worksheet_metadata["PerkStyle"]
            sheet1_name: str = perkstyle_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else perkstyle_ws["sheet_name_without_version"]
            perkstyle_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(perkstyle_ws["dType"]), "dType": perkstyle_ws["dType"], "sheet_name": sheet1_name, "sheet": self.perkstyle_df}
            self.enqueue_df(perkstyle_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.perk_df.empty:
            perk_ws: dict[str, Any] = self.worksheet_metadata["Perk"]
            sheet2_name: str = perk_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else perk_ws["sheet_name_without_version"]
            perk_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(perk_ws["dType"]), "dType": perk_ws["dType"], "sheet_name": sheet2_name, "sheet": self.perk_df}
            self.enqueue_df(perk_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_perk_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出符文数据到工作簿中。产生以下工作表：<br>Export perk data to a workbook. The following worksheets are added:
        - 符文系（PerkStyles）
        - 符文（Perks）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 符文二进制描述文件的本地路径。<br>A local path of perk binary description file.
        
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
        if self.perkstyle_df.empty or self.perk_df.empty:
            status: int = self.build_perk_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            perkstyle_df: pandas.DataFrame = eliminate_empty_fields(self.perkstyle_df)
            perk_df: pandas.DataFrame = eliminate_empty_fields(self.perk_df)
        else:
            perkstyle_df = self.perkstyle_df
            perk_df = self.perk_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["PerkStyle"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["PerkStyle"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["Perk"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["Perk"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(perkstyle_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(perk_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    for sheet_name in [sheet1_name, sheet2_name]:
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
                logPrint(f"符文数据已导出到{self.wbPath}。\nPerk data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出符文数据到网页中。产生以下文件：<br>Export perk data into html files. The following files are produced:
        - 符文系（PerkStyles）
        - 符文（Perks）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 符文二进制描述文件的本地路径。<br>A local path of perk binary description file.
        
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
        if self.perkstyle_df.empty or self.perk_df.empty:
            status: int = self.build_perk_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到网页中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #符文系（Perkstyle）
        if len(self.perkstyle_df) > 1: #只导出含有记录的数据框（Only dataframes with records are exported）
            perkstyle_df_web: pandas.DataFrame = self.perkstyle_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            mIconTextureUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.perkstyle_df.loc[1:, "mIconTextureName"].to_list()))
            perkstyle_df_web.insert(len(perkstyle_df_web.columns), "mIconTextureUrl", ["图标纹理网址"] + mIconTextureUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mPerkStyleName",
                "mPerkStyleId",
                "mIconTextureUrl",
                "mDisplayNameLocalizationKey_content_zh",
                "mDisplayNameLocalizationKey_content_en",
                "mIsAdvancedStyle",
                "mTooltipNameLocalizationKey_content_zh",
                "mTooltipNameLocalizationKey_content_en",
                "mSlot1 mPerks mDisplayNameLocalizationKey_contents_zh",
                "mSlot1 mPerks mDisplayNameLocalizationKey_contents_en",
                "mSlot2 mPerks mDisplayNameLocalizationKey_contents_zh",
                "mSlot2 mPerks mDisplayNameLocalizationKey_contents_en",
                "mSlot3 mPerks mDisplayNameLocalizationKey_contents_zh",
                "mSlot3 mPerks mDisplayNameLocalizationKey_contents_en",
                "mSlot4 mPerks mDisplayNameLocalizationKey_contents_zh",
                "mSlot4 mPerks mDisplayNameLocalizationKey_contents_en",
            ]
            perkstyle_df_web = perkstyle_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            perkstyle_df_styled: pandas.io.formats.style.Styler = perkstyle_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:6]
            perkstyle_df_styled = perkstyle_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            perkstyle_htmltable: str = perkstyle_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            perkstyle_htmltable = '<meta charset="UTF-8">\n' + perkstyle_htmltable #以兼容中文的编码来保存（Save with a meta encoding compatible with Chinese）
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"Perkstyle_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(perkstyle_htmltable)
        #符文（Perk）
        if len(self.perk_df) > 1:
            perk_df_web: pandas.DataFrame = self.perk_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            mIconTextureUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.perk_df.loc[1:, "mIconTextureName"].to_list()))
            perk_df_web.insert(len(perk_df_web.columns), "mIconTextureUrl", ["图标纹理网址"] + mIconTextureUrls)
            ##排序（Order）
            ###第一关键字——所属符文系（Primary keyword - belonging perkstyle）
            belonging_perkstyle_weight_map: dict[str, int] = {self.perkstyle_df["mDisplayNameLocalizationKey_content_zh"][1:][i]: i for i in range(1, len(self.perkstyle_df))}
            belonging_perkstyle_weight_map[""] = len(self.perkstyle_df)
            ###第二关键字——槽位序号（Secondary keyword - slot index）
            slotIndex_weight_map: dict[int | str, int] = {_: _ for _ in set(perk_df_web["belonging_perkstyle_slotIndex"][1:]) if isinstance(_, int)}
            slotIndex_weight_map[""] = max(slotIndex_weight_map.values()) + 1
            ###插入关键字权重列（Insert keyword weight columns）
            belonging_perkstyle_weights: list[int] = list(map(lambda x: belonging_perkstyle_weight_map[x], perk_df_web["belonging_perkstyle mDisplayNameLocalizationKey_content_zh"][1:].to_list()))
            perk_df_web.insert(len(perk_df_web.columns), "perkstyle_weight", ["符文系权重"] + belonging_perkstyle_weights)
            slotIndex_weights: list[int] = list(map(lambda x: slotIndex_weight_map[x], perk_df_web["belonging_perkstyle_slotIndex"][1:].to_list()))
            perk_df_web.insert(len(perk_df_web.columns), "slotIndex_weight", ["槽位序号权重"] + slotIndex_weights)
            ###排序重组（Sort and recombination）
            perk_df_web = pandas.concat([perk_df_web.iloc[:1, :], perk_df_web.iloc[1:, :].sort_values(by = ["perkstyle_weight", "slotIndex_weight", "mPerkId"], ascending = True)])
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mPerkName",
                "mPerkId",
                "mIconTextureUrl",
                "mDisplayNameLocalizationKey_content_zh",
                "mDisplayNameLocalizationKey_content_en",
                "belonging_perkstyle mDisplayNameLocalizationKey_content_zh",
                "belonging_perkstyle mDisplayNameLocalizationKey_content_en",
                "belonging_perkstyle_slotIndex",
                "mEnabled",
                "mStackable",
                "mDefault",
                "mTooltipNameLocalizationKey_content_zh_burn",
                "mTooltipNameLocalizationKey_content_en_burn",
                "mLongDescLocalizationKey_content_zh_burn",
                "mLongDescLocalizationKey_content_en_burn",
                "mEndOfGameStatDescriptions_contents_zh",
                "mEndOfGameStatDescriptions_contents_en",
            ]
            perk_df_web = perk_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            perk_df_styled: pandas.io.formats.style.Styler = perk_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:8]
            perk_df_styled = perk_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            perk_htmltable: str = perk_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            perk_htmltable = '<meta charset="UTF-8">\n' + perk_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"Perk_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(perk_htmltable)
