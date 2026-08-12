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
from src.core.config.headers import item_header, itemGroup_header, itemModifier_header
from src.core.extractor.base import LoLDataExtractor

class ItemExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个装备提取器对象。<br>Initialize a ItemExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.item_ready: bool = False
        self.item_df: pandas.DataFrame = pandas.DataFrame()
        self.itemGroup_df: pandas.DataFrame = pandas.DataFrame()
        self.itemModifier_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.item_ready = False
    
    def get_item_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取装备二进制描述数据。<br>Get binary description data of items online.
        '''
        logPrint = self.log.logPrint
        items_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/items.cdtb.bin.json"
        if items_bin_url in self.__class__.data_cache["online"]:
            self.items_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][items_bin_url]
        else:
            source, status, self.session = requestUrl("GET", items_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("装备信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nItem data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(items_bin_url))
                else:
                    logPrint("装备信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nItem data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            self.items_bin = source.json()
            self.items_bin = self.resolve_bin_hash(self.items_bin)
            self.__class__.data_cache["online"][items_bin_url] = self.items_bin
        self.item_ready = True
    
    def read_item_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取装备二进制描述数据。<br>Get binary description data of items offline.
        
        :param path: 装备二进制描述文件的本地路径。<br>A local path of item binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        items_bin_path: str = path
        if items_bin_path in self.__class__.data_cache["local"]:
            self.items_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][items_bin_path]
        else:
            with open(items_bin_path, "r", encoding = "utf-8") as fp:
                self.items_bin = json.load(fp)
            self.items_bin = self.resolve_bin_hash(self.items_bin)
            self.__class__.data_cache["local"][items_bin_path] = self.items_bin
        self.item_ready = True
    
    def build_item_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建装备数据框。<br>Build item dataframe.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 装备二进制描述文件的本地路径。<br>A local path of item binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.item_ready:
            #获取装备信息（Get item information）
            logPrint("正在读取装备数据……\nReading item data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_item_data(path = path)
            else:
                self.get_item_data()
            if not self.item_ready:
                logPrint("装备数据尚未准备就绪！\nItem data not prepared!")
                return 2
        
        #提取指令字典（Extract spell dictionary）
        self.init_mSpells()
        for (key, value) in self.items_bin.items():
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        
        #构建从装备序号到装备数据的映射（Build a map from the itemId to the corresponding item data）
        itemKey_itemId_map: dict[int, str] = {}
        for (key, value) in self.items_bin.items():
            if key != "__linked" and value["__type"] == "ItemData":
                itemKey_itemId_map[value["itemID"]] = key #已事先确定所有装备数据对象中都有itemID键（Confirmed in advance that all ItemData objects have `itemID` key）
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建装备数据框……\nBuilding the item dataframes ...", print_time = True)
        item_header_keys: list[str] = list(item_header.keys())
        item_data: dict[str, list[Any]] = {key: [] for key in item_header_keys}
        item_data_json: dict[str, list[Any]] = copy.deepcopy(item_data)
        itemGroup_header_keys: list[str] = list(itemGroup_header.keys())
        itemGroup_data: dict[str, list[Any]] = {key: [] for key in itemGroup_header_keys}
        itemGroup_data_json: dict[str, list[Any]] = copy.deepcopy(itemGroup_data)
        itemModifier_header_keys: list[str] = list(itemModifier_header.keys())
        itemModifier_data: dict[str, list[Any]] = {key: [] for key in itemModifier_header_keys}
        itemModifier_data_json: dict[str, list[Any]] = copy.deepcopy(itemModifier_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        item_rarities_zh: dict[int, str] = {0: "无", 1: "初始", 2: "基础", 3: "工资装", 4: "史诗", 5: "传说", 6: "神话", 7: "升级", 8: "锻造器", 9: "棱彩"}
        item_rarities_en: dict[int, str] = {0: "NONE", 1: "STARTER", 2: "BASIC", 3: "Gold Income", 4: "EPIC", 5: "LEGENDARY", 6: "Mythic", 7: "Level Up", 8: "ANVIL", 9: "PRISMATIC"}
        item_rarities: dict[int, str] = item_rarities_zh if self.locale in self.ZH_LOCALE else item_rarities_en
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.items_bin.items():
            if key1 != "__linked" and value["__type"] == "ItemData":
                for i in range(len(item_header_keys)):
                    key: str = item_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 100:
                        if i == 84: #显示名（中文）（`mDisplayName_content_zh`）
                            to_append = self.get_strtable_value(strtable_lol_target, value.get("mDisplayName", ""), default = "")
                        elif i == 85: #显示名（英文）（`mDisplayName_content_en`）
                            to_append = self.get_strtable_value(strtable_lol_default, value.get("mDisplayName", ""), default = "")
                        elif i == 86: #装备推荐属性内容（`mItemAdviceAttributes_content`）
                            to_append = list(map(lambda x: self.items_bin[x]["mAttribute"], value.get("mItemAdviceAttributes", [])))
                        elif i == 87: #总价格（`totalPrice`）
                            totalPrice = 0
                            #下面通过一个栈实现装备总价格的计算（Calculate the total price using a stack）
                            recipeItem_key_stack: list[str] = [key1]
                            while len(recipeItem_key_stack) > 0:
                                item_key_tmp: str = recipeItem_key_stack.pop()
                                itemJson_tmp = self.items_bin[item_key_tmp]
                                totalPrice += itemJson_tmp.get("price", 0) #部分装备没有价格键，例如防御塔装备（Some items don't have the "price" key, e.g. turret items）
                                if "recipeItemLinks" in itemJson_tmp:
                                    recipeItem_key_stack += itemJson_tmp["recipeItemLinks"][::-1] #保证金币的计算遵循正确的装备构件顺序，虽然这其实无关紧要（Make sure the calculation order of total price follows the correct in-game item component order, although it doesn't matter actually）
                            to_append = totalPrice
                        elif i == 88: #特殊合成材料（中文）（`specialRecipe_displayName_content_zh`）
                            to_append = self.get_strtable_value(strtable_lol_target, self.items_bin[itemKey_itemId_map[value["specialRecipe"]]].get("mDisplayName", ""), default = "") if "specialRecipe" in value else ""
                        elif i == 89: #特殊合成材料（英文）（`specialRecipe_displayName_content_en`）
                            to_append = self.get_strtable_value(strtable_lol_default, self.items_bin[itemKey_itemId_map[value["specialRecipe"]]].get("mDisplayName", ""), default = "") if "specialRecipe" in value else ""
                        elif i == 90: #位阶（`rarity`）
                            to_append = item_rarities[value.get("epicness", 2)]
                        elif i == 91: #次要位阶（`secondaryRarity`）
                            to_append = item_rarities[value["SecondaryEpicness"]] if "SecondaryEpicness" in value else ""
                        elif i == 92: #同级替换装备（中文）（`sidegradeItemNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["sidegradeItemLinks"])) if "sidegradeItemLinks" in value else ""
                        elif i == 93: #同级替换装备（英文）（`sidegradeItemNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["sidegradeItemLinks"])) if "sidegradeItemLinks" in value else ""
                        elif i == 94: #合成材料（中文）（`recipeItemNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["recipeItemLinks"])) if "recipeItemLinks" in value else ""
                        elif i == 95: #合成材料（英文）（`recipeItemNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["recipeItemLinks"])) if "recipeItemLinks" in value else ""
                        elif i == 96: #所需材料（中文）（`requiredItemNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["requiredItemLinks"])) if "requiredItemLinks" in value else ""
                        elif i == 97: #所需材料（英文）（`requiredItemNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["requiredItemLinks"])) if "requiredItemLinks" in value else ""
                        elif i == 98: #同品类合成装备（中文）（`mItemDataBuildNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["mItemDataBuild"]["itemLinks"])) if "mItemDataBuild" in value else ""
                        elif i == 99: #同品类合成装备（英文）（`mItemDataBuildNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["mItemDataBuild"]["itemLinks"])) if "mItemDataBuild" in value else ""
                        elif i == 100: #装备效果重做版本（`LastMajorChangeVersion`）
                            to_append = "%d.%d" %(value["LastMajorChangeMajorPatchVersion"], value["LastMajorChangeMinorPatchVersion"]) if "LastMajorChangeMajorPatchVersion" in value and "LastMajorChangeMinorPatchVersion" in value else ""
                        else:
                            to_append = value.get(key, False if i in {16, 19, 20, 21, 22, 23, 24, 27} else True if i in {25, 26} else "")
                    elif i <= 103: #数据可用性子键（`mItemDataAvailability`'s subkeys）
                        to_append = value["mItemDataAvailability"].get(key.split()[1], False) if "mItemDataAvailability" in value else False
                    else: #客户端数据子键（`mItemDataClient`'s subkeys）
                        if i <= 137:
                            tmpObj_ptr = value
                            for subkey_iter in key.split():
                                if subkey_iter in tmpObj_ptr:
                                    tmpObj_ptr = tmpObj_ptr[subkey_iter]
                                else:
                                    to_append = True if i == 106 else ""
                                    break
                            else:
                                to_append = tmpObj_ptr
                        elif i == 138: #属性效果（`mItemDataClient mTooltipData mStatList`）
                            if "mItemDataClient" in value and "mTooltipData" in value["mItemDataClient"] and "mLists" in value["mItemDataClient"]["mTooltipData"]:
                                to_append = list(map(lambda x: x["type"], value["mItemDataClient"]["mTooltipData"]["mLists"]["Stats"].get("Elements", [])))
                            else:
                                to_append = ""
                        elif i <= 218: #本地化说明文本（Localized tooltips）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            tooltip_key: str = item_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            if subkey2.endswith("_burn"):
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                            else:
                                to_append = tooltip_raw
                        else: #客户端内位阶（`mItemDataClient rarity`）
                            to_append = item_rarities[value["mItemDataClient"]["epicness"]] if "mItemDataClient" in value and "epicness" in value["mItemDataClient"] else ""
                    item_data[key].append(to_append)
                    item_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "ItemGroup":
                for i in range(len(itemGroup_header_keys)):
                    key: str = itemGroup_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        to_append = value.get(key, False if i == 6 else "")
                    itemGroup_data[key].append(to_append)
                    itemGroup_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "ItemModifier":
                for i in range(len(itemModifier_header_keys)):
                    key: str = itemModifier_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 27:
                        if i in {9, 12, 25}:
                            to_append = value.get(key, False)
                        else:
                            to_append = value.get(key, "")
                    elif i <= 35:
                        subkey2: str = re.search(r"_mDisplayName_content_\w*", key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[3] == "zh"
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        item_key: str = itemModifier_data[subkey1][-1]
                        if item_key in self.items_bin and "mDisplayName" in self.items_bin[item_key]:
                            tooltip_key: str = self.items_bin[item_key]["mDisplayName"]
                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        else:
                            to_append = ""
                    else:
                        subkey2 = pStrConst.search(key).group()
                        subkey1 = key.replace(subkey2, "")
                        useTargetLocale = subkey2.split("_")[2] == "zh"
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key = itemModifier_data[subkey1][-1]
                        to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                    itemModifier_data[key].append(to_append)
                    itemModifier_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        item_statistics_output_order: list[int] = [0, 9, 2, 84, 85, 7, 22, 19, 1, 35, 27, 70, 20, 21, 23, 24, 25, 26, 75, 101, 102, 103, 77, 33, 94, 95, 10, 14, 87, 17, 15, 28, 88, 89, 31, 92, 93, 73, 98, 99, 78, 29, 90, 30, 91, 11, 12, 86, 13, 3, 4, 8, 5, 34, 96, 97, 6, 16, 18, 51, 69, 60, 65, 58, 59, 62, 63, 47, 55, 56, 45, 57, 52, 53, 54, 71, 68, 67, 61, 48, 39, 50, 49, 64, 66, 38, 44, 72, 32, 42, 36, 37, 40, 41, 46, 43, 80, 81, 100, 74, 76, 79, 83, 82, 104, 105, 106, 127, 138, 128, 207, 208, 209, 210, 129, 211, 212, 213, 214, 130, 215, 216, 217, 218, 107, 139, 140, 108, 141, 142, 143, 144, 109, 145, 146, 147, 148, 110, 149, 150, 151, 152, 111, 153, 154, 112, 155, 156, 157, 158, 113, 159, 160, 161, 162, 114, 163, 164, 165, 166, 115, 167, 168, 169, 170, 116, 171, 172, 117, 173, 174, 175, 176, 118, 177, 178, 179, 180, 119, 181, 182, 183, 184, 120, 185, 186, 187, 188, 121, 189, 190, 191, 192, 122, 193, 194, 123, 195, 196, 197, 198, 124, 199, 200, 201, 202, 125, 203, 204, 205, 206, 126, 131, 132, 133, 134, 219, 135, 136, 137]
        item_data_organized: dict[str, list[Any]] = {item_header_keys[i]: item_data_json[item_header_keys[i]] for i in item_statistics_output_order}
        item_df: pandas.DataFrame = pandas.DataFrame(data = item_data_organized)
        item_df = item_df.sort_values(by = "itemID", ascending = True, ignore_index = True)
        logPrint("正在优化装备数据框的逻辑值显示……\nOptimizing boolean value display of the item dataframe ...")
        optimize_bool_display(item_df)
        item_df = pandas.concat([pandas.DataFrame([item_header])[item_df.columns], item_df], ignore_index = True)
        self.item_df = item_df
        itemGroup_statistics_output_order: list[int] = [0, 1, 5, 2, 3, 4, 7, 6]
        itemGroup_data_organized: dict[str, list[Any]] = {itemGroup_header_keys[i]: itemGroup_data_json[itemGroup_header_keys[i]] for i in itemGroup_statistics_output_order}
        itemGroup_df: pandas.DataFrame = pandas.DataFrame(data = itemGroup_data_organized)
        logPrint("正在优化装备分组数据框的逻辑值显示……\nOptimizing boolean value display of the item group dataframe ...")
        optimize_bool_display(itemGroup_df)
        itemGroup_df = pandas.concat([pandas.DataFrame([itemGroup_header])[itemGroup_df.columns], itemGroup_df], ignore_index = True)
        self.itemGroup_df = itemGroup_df
        itemModifier_statistics_output_order: list[int] = [0, 1, 3, 30, 31, 5, 26, 18, 12, 9, 10, 25, 4, 6, 14, 15, 13, 11, 2, 28, 29, 7, 32, 33, 8, 34, 35, 22, 44, 45, 23, 46, 47, 24, 48, 49, 16, 36, 37, 17, 38, 39, 20, 40, 41, 21, 42, 43, 19, 27]
        itemModifier_data_organized: dict[str, list[Any]] = {itemModifier_header_keys[i]: itemModifier_data_json[itemModifier_header_keys[i]] for i in itemModifier_statistics_output_order}
        itemModifier_df: pandas.DataFrame = pandas.DataFrame(data = itemModifier_data_organized)
        logPrint("正在优化装备修饰数据框的逻辑值显示……\nOptimizing boolean value display of the item modifier dataframe ...")
        optimize_bool_display(itemModifier_df)
        itemModifier_df = pandas.concat([pandas.DataFrame([itemModifier_header])[itemModifier_df.columns], itemModifier_df], ignore_index = True)
        self.itemModifier_df = itemModifier_df
        return 0
    
    def enqueue_item_dataframe(self) -> None:
        '''
        将装备数据框追加到数据提取器基类的数据框队列尾部。<br>Append item dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.item_df.empty:
            item_ws: dict[str, Any] = self.worksheet_metadata["Item"]
            sheet1_name: str = item_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else item_ws["sheet_name_without_version"]
            item_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(item_ws["dType"]), "dType": item_ws["dType"], "sheet_name": sheet1_name, "sheet": self.item_df}
            self.enqueue_df(item_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.itemGroup_df.empty:
            itemGroup_ws: dict[str, Any] = self.worksheet_metadata["ItemGroup"]
            sheet2_name: str = itemGroup_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else itemGroup_ws["sheet_name_without_version"]
            itemGroup_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(itemGroup_ws["dType"]), "dType": itemGroup_ws["dType"], "sheet_name": sheet2_name, "sheet": self.itemGroup_df}
            self.enqueue_df(itemGroup_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.itemModifier_df.empty:
            itemModifier_ws: dict[str, Any] = self.worksheet_metadata["ItemModifier"]
            sheet3_name: str = itemModifier_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else itemModifier_ws["sheet_name_without_version"]
            itemModifier_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(itemModifier_ws["dType"]), "dType": itemModifier_ws["dType"], "sheet_name": sheet3_name, "sheet": self.itemModifier_df}
            self.enqueue_df(itemModifier_df_struct, overwrite_on_exist = True, log = self.log)

    def export_item_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出装备数据到工作簿中。产生以下工作表：<br>Export item data to a workbook. The following worksheets are added:
        - 装备（Items）
        - 装备分组（Item Groups）
        - 装备修饰（Item Modifiers）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 装备二进制描述文件的本地路径。<br>A local path of item binary description file.
        
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
        if self.item_df.empty:
            status: int = self.build_item_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            item_df: pandas.DataFrame = eliminate_empty_fields(self.item_df)
            itemGroup_df: pandas.DataFrame = eliminate_empty_fields(self.itemGroup_df)
            itemModifier_df: pandas.DataFrame = eliminate_empty_fields(self.itemModifier_df)
        else:
            item_df = self.item_df
            itemGroup_df = self.itemGroup_df
            itemModifier_df = self.itemModifier_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["Item"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["Item"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["ItemGroup"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["ItemGroup"]["sheet_name_without_version"]
        sheet3_name: str = self.worksheet_metadata["ItemModifier"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["ItemModifier"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(item_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(itemGroup_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    addDefaultStyle(itemModifier_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    for sheet_name in [sheet1_name, sheet2_name, sheet3_name]:
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
                logPrint(f"装备数据已导出到{self.wbPath}。\nItem data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出装备数据到网页中。产生以下文件：<br>Export item data into an html file. The following file is produced:
        - 装备（Item）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 装备二进制描述文件的本地路径。<br>A local path of item binary description file.
        
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
        if self.item_df.empty:
            status: int = self.build_item_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #装备（Item）
        if len(self.item_df) > 1:
            item_df_web: pandas.DataFrame = self.item_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            inventoryIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.item_df.loc[1:, "mItemDataClient inventoryIcon"].to_list()))
            item_df_web.insert(len(item_df_web.columns), "mItemDataClient inventoryIconUrl", ["装备栏网址"] + inventoryIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "itemID",
                "mItemDataClient inventoryIconUrl",
                "mDisplayName_content_zh",
                "mDisplayName_content_en",
                "recipeItemNames_content_zh",
                "recipeItemNames_content_en",
                "totalPrice",
                "rarity",
                "mItemDataClient mShopTooltip_content_zh_burn",
                "mItemDataClient mShopTooltip_content_en_burn",
                "mItemDataClient mTooltipData mLocKeys keyTooltipExtendedRules_content_zh_burn",
                "mItemDataClient mTooltipData mLocKeys keyTooltipExtendedRules_content_en_burn"
            ]
            item_df_web = item_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            item_df_styled: pandas.io.formats.style.Styler = item_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:8]
            item_df_styled = item_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            item_htmltable: str = item_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            item_htmltable = '<meta charset="UTF-8">\n' + item_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"Item_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(item_htmltable)
