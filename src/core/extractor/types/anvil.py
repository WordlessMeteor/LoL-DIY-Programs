import copy, json, os, pandas, sys, time
from openpyxl.worksheet.worksheet import Worksheet
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.patch import Patch
from src.utils.webRequest import requestUrl
from src.utils.format import optimize_bool_display, addDefaultStyle, eliminate_empty_fields, pyobj2json
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.headers import anvil_header
from src.core.extractor.base import LoLDataExtractor

class AnvilExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个锻造器提取器对象。<br>Initialize a AnvilExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.anvils_ready: dict[str, bool] = {"map30": False, "kiwi": False}
        self.CherryAnvil_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiAnvil_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.anvils_ready = {key: False for key in self.anvils_ready}
    
    def get_anvil_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取锻造器二进制描述数据。包括以下模式：<br>Get binary description data of anvils online. Including the following game modes:
        - 斗魂竞技场（Arena）
        - 海克斯大乱斗（ARAM: Mayhem）
        '''
        logPrint = self.log.logPrint
        #怒火角斗场地图（Rings of Wrath map）
        map30_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map30/map30.bin.json"
        if map30_bin_url in self.__class__.data_cache["online"]:
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map30_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map30_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("怒火角斗场地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map30_bin_url))
                else:
                    logPrint("怒火角斗场地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            self.map30_bin = source.json()
            self.map30_bin = self.resolve_bin_hash(self.map30_bin)
            self.__class__.data_cache["online"][map30_bin_url] = self.map30_bin
        self.anvils_ready["map30"] = True
        if Patch(self.patch_number) >= Patch("16.2"):
            #嚎哭深渊地图（Howling Abyss map）
            map12_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map12/map12.bin.json"
            if map12_bin_url in self.__class__.data_cache["online"]:
                self.KiwiAnvils_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map12_bin_url]
            else:
                source, status, self.session = requestUrl("GET", map12_bin_url, session = self.session, log = self.log)
                if status != 200:
                    if status == 404:
                        logPrint("嚎哭深渊地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nHowling Abyss map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                        self.KiwiAnvils_bin = {}
                    else:
                        logPrint("嚎哭深渊地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nHowling Abyss map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map12_bin_url))
                        time.sleep(3)
                        self.init_data_readiness()
                        return
                else:
                    self.KiwiAnvils_bin = source.json()
                    self.KiwiAnvils_bin = self.resolve_bin_hash(self.KiwiAnvils_bin)
                self.__class__.data_cache["online"][map12_bin_url] = self.KiwiAnvils_bin
        else:
            #海克斯大乱斗模式（ARAM: Mayhem mode）
            kiwi_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/augments.bin.json"
            if kiwi_bin_url in self.__class__.data_cache["online"]:
                self.KiwiAnvils_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][kiwi_bin_url]
            else:
                source, status, self.session = requestUrl("GET", kiwi_bin_url, session = self.session, log = self.log)
                if status != 200:
                    if status == 404:
                        logPrint("海克斯大乱斗强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nARAM: Mayhem augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(kiwi_bin_url))
                        self.KiwiAnvils_bin = {}
                    else:
                        logPrint('海克斯大乱斗强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nARAM: Mayhem augment data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                        time.sleep(3)
                        self.init_data_readiness()
                        return
                else:
                    self.KiwiAnvils_bin = source.json()
                    self.KiwiAnvils_bin = self.resolve_bin_hash(self.KiwiAnvils_bin)
                self.__class__.data_cache["online"][kiwi_bin_url] = self.KiwiAnvils_bin
        self.anvils_ready["kiwi"] = True
    
    def read_anvil_data(self, paths: list[str]) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取锻造器二进制描述数据。<br>Get binary description data of anvils offline.
        
        :param paths: 锻造器二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of anvil binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        :type paths: list[str]
        '''
        logPrint = self.log.logPrint
        #检查路径是否都存在（Check if all paths exist）
        paths_not_found: list[str] = [path for path in paths if not os.path.exists(path)]
        if len(paths_not_found) > 0:
            logPrint("以下路径不存在：\nThe following path(s) do(es)n't exist:")
            for path in paths_not_found:
                logPrint(path)
            self.init_data_readiness()
            return
        #怒火角斗场地图（Rings of Wrath map）
        map30_bin_path: str = paths[0]
        if map30_bin_path in self.__class__.data_cache["local"]:
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map30_bin_path]
        else:
            with open(map30_bin_path, "r", encoding = "utf-8") as fp:
                self.map30_bin = json.load(fp)
            self.map30_bin = self.resolve_bin_hash(self.map30_bin)
            self.__class__.data_cache["local"][map30_bin_path] = self.map30_bin
        self.anvils_ready["map30"] = True
        #海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        KiwiAnvils_bin_path: str = paths[1]
        if KiwiAnvils_bin_path in self.__class__.data_cache["local"]:
            self.KiwiAnvils_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][KiwiAnvils_bin_path]
        else:
            with open(KiwiAnvils_bin_path, "r", encoding = "utf-8") as fp:
                self.KiwiAnvils_bin = json.load(fp)
            self.KiwiAnvils_bin = self.resolve_bin_hash(self.KiwiAnvils_bin)
            self.__class__.data_cache["local"][KiwiAnvils_bin_path] = self.KiwiAnvils_bin
        self.anvils_ready["kiwi"] = True
    
    def build_anvil_dataframe(self, debug: bool = False, paths: Optional[list[str]] = None) -> int:
        '''
        构建锻造器数据框。<br>Build anvil dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 锻造器二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of anvil binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not all(self.anvils_ready.values()):
            #获取锻造器信息（Get anvil information）
            logPrint("正在读取锻造器数据……\nReading anvil data ...", print_time = True)
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_anvil_data(paths = paths)
            else:
                self.get_anvil_data()
            if not all(self.anvils_ready.values()):
                logPrint("锻造器数据尚未准备就绪！\nAnvil data not prepared!")
                return 2
        #定义数据结构（Define the data structure）
        logPrint("正在构建锻造器数据框……\nBuilding the anvil dataframes ...", print_time = True)
        CherryAnvil_header: dict[str, str] = anvil_header.copy()
        CherryAnvil_header_keys: list[str] = list(CherryAnvil_header.keys())
        CherryAnvil_data: dict[str, list[Any]] = {key: [] for key in CherryAnvil_header_keys}
        CherryAnvil_data_json: dict[str, list[Any]] = copy.deepcopy(CherryAnvil_data)
        KiwiAnvil_header: dict[str, str] = anvil_header.copy()
        KiwiAnvil_header_keys: list[str] = list(KiwiAnvil_header.keys())
        KiwiAnvil_data: dict[str, list[Any]] = {key: [] for key in KiwiAnvil_header_keys}
        KiwiAnvil_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiAnvil_data)
        
        #数据整理核心部分（Data organization core part）
        ##斗魂竞技场锻造器（Arena anvils）
        self.init_mSpells()
        for (key, value) in self.map30_bin.items(): #提取指令字典（Extract spell dictionary）
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        for (key1, value) in self.map30_bin.items():
            if key1 != "__linked" and value["__type"] == "AnvilData":
                for i in range(len(CherryAnvil_header_keys)):
                    key: str = CherryAnvil_header_keys[i]
                    to_append: Any = self.generate_anvil_record(self.map30_bin, CherryAnvil_data, key, key1, value)
                    CherryAnvil_data[key].append(to_append)
                    CherryAnvil_data_json[key].append(pyobj2json(to_append))
        CherryAnvil_statistics_output_order: list[int] = [0, 1, 13, 2, 3, 14, 15, 12, 25, 11, 24, 7, 8, 4, 16, 17, 18, 19, 5, 20, 21, 22, 23, 6, 26, 9, 10]
        CherryAnvil_data_organized: dict[str, list[Any]] = {CherryAnvil_header_keys[i]: CherryAnvil_data_json[CherryAnvil_header_keys[i]] for i in CherryAnvil_statistics_output_order}
        CherryAnvil_df: pandas.DataFrame = pandas.DataFrame(data = CherryAnvil_data_organized)
        logPrint("正在优化斗魂竞技场锻造器数据框的逻辑值显示……\nOptimizing boolean value display of the Cherry anvil dataframe ...")
        optimize_bool_display(CherryAnvil_df)
        CherryAnvil_df = pandas.concat([pandas.DataFrame([CherryAnvil_header])[CherryAnvil_df.columns], CherryAnvil_df], ignore_index = True)
        self.CherryAnvil_df = CherryAnvil_df
        ##海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        self.init_mSpells()
        for (key, value) in self.KiwiAnvils_bin.items(): #提取指令字典（Extract spell dictionary）
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        for (key1, value) in self.KiwiAnvils_bin.items():
            if key1 != "__linked" and value["__type"] == "AnvilData":
                for i in range(len(KiwiAnvil_header_keys)):
                    key: str = KiwiAnvil_header_keys[i]
                    to_append: Any = self.generate_anvil_record(self.KiwiAnvils_bin, KiwiAnvil_data, key, key1, value)
                    KiwiAnvil_data[key].append(to_append)
                    KiwiAnvil_data_json[key].append(pyobj2json(to_append))
        KiwiAnvil_statistics_output_order: list[int] = [0, 1, 13, 2, 3, 14, 15, 12, 25, 11, 24, 7, 8, 4, 16, 17, 18, 19, 5, 20, 21, 22, 23, 6, 26, 9, 10]
        KiwiAnvil_data_organized: dict[str, list[Any]] = {KiwiAnvil_header_keys[i]: KiwiAnvil_data_json[KiwiAnvil_header_keys[i]] for i in KiwiAnvil_statistics_output_order}
        KiwiAnvil_df: pandas.DataFrame = pandas.DataFrame(data = KiwiAnvil_data_organized)
        logPrint("正在优化海克斯大乱斗锻造器数据框的逻辑值显示……\nOptimizing boolean value display of the Kiwi anvil dataframe ...")
        optimize_bool_display(KiwiAnvil_df)
        KiwiAnvil_df = pandas.concat([pandas.DataFrame([KiwiAnvil_header])[KiwiAnvil_df.columns], KiwiAnvil_df], ignore_index = True)
        self.KiwiAnvil_df = KiwiAnvil_df
        return 0
    
    def enqueue_anvil_dataframe(self) -> None:
        '''
        将锻造器数据框追加到数据提取器基类的数据框队列尾部。<br>Append anvil dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.CherryAnvil_df.empty:
            CherryAnvil_ws: dict[str, Any] = self.worksheet_metadata["CherryAnvil"]
            sheet1_name: str = CherryAnvil_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else CherryAnvil_ws["sheet_name_without_version"]
            CherryAnvil_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(CherryAnvil_ws["dType"]), "dType": CherryAnvil_ws["dType"], "sheet_name": sheet1_name, "sheet": self.CherryAnvil_df}
            self.enqueue_df(CherryAnvil_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiAnvil_df.empty:
            KiwiAnvil_ws: dict[str, Any] = self.worksheet_metadata["KiwiAnvil"]
            sheet2_name: str = KiwiAnvil_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiAnvil_ws["sheet_name_without_version"]
            KiwiAnvil_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiAnvil_ws["dType"]), "dType": KiwiAnvil_ws["dType"], "sheet_name": sheet2_name, "sheet": self.KiwiAnvil_df}
            self.enqueue_df(KiwiAnvil_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_anvil_data(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出锻造器数据到工作簿中。产生以下工作表：<br>Export anvil data to a workbook. The following worksheets are added:
        - 斗魂竞技场锻造器（Cherry Anvils）
        - 海克斯大乱斗锻造器（Kiwi Anvils）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 锻造器二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of anvil binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径。\nPath of exported file not specified.")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if self.CherryAnvil_df.empty or self.KiwiAnvil_df.empty:
            status: int = self.build_anvil_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            CherryAnvil_df: pandas.DataFrame = eliminate_empty_fields(self.CherryAnvil_df)
            KiwiAnvil_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiAnvil_df)
        else:
            CherryAnvil_df = self.CherryAnvil_df
            KiwiAnvil_df = self.KiwiAnvil_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["CherryAnvil"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryAnvil"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["KiwiAnvil"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiAnvil"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(CherryAnvil_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(KiwiAnvil_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
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
                logPrint(f"锻造器数据已导出到{self.wbPath}。\nAnvil data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出锻造器数据到网页中。产生以下文件：<br>Export anvil data into html files. The following files are produced:
        - 斗魂竞技场锻造器（Cherry Anvils）
        - 海克斯大乱斗锻造器（Kiwi Anvils）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 锻造器二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of anvil binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径。\nPath of exported file not specified.")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if self.CherryAnvil_df.empty or self.KiwiAnvil_df.empty:
            status: int = self.build_anvil_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #斗魂竞技场锻造器（Arena anvil）
        if len(self.CherryAnvil_df) > 1:
            CherryAnvil_df_web: pandas.DataFrame = self.CherryAnvil_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AugmentLargeIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.CherryAnvil_df.loc[1:, "AugmentLargeIconPath"].to_list()))
            CherryAnvil_df_web.insert(len(CherryAnvil_df_web.columns), "AugmentLargeIconUrl", ["锻造器大图标网址"] + AugmentLargeIconUrls)
            ##排序（Order）
            CherryAnvil_df_web = pandas.concat([CherryAnvil_df_web.iloc[:1, :], CherryAnvil_df_web.iloc[1:, :].sort_values(by = "AugmentNameId", ascending = True)])
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "AugmentNameId",
                "AugmentLargeIconUrl",
                "Enabled",
                "NameTra_content_zh",
                "NameTra_content_en",
                "anvilRarities",
                "AugmentDisplayTags_content",
                "DescriptionTra_content_zh_burn",
                "DescriptionTra_content_en_burn"
            ]
            CherryAnvil_df_web = CherryAnvil_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            CherryAnvil_df_styled: pandas.io.formats.style.Styler = CherryAnvil_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:7]
            CherryAnvil_df_styled = CherryAnvil_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            CherryAnvil_htmltable: str = CherryAnvil_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            CherryAnvil_htmltable = '<meta charset="UTF-8">\n' + CherryAnvil_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"CherryAnvil_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(CherryAnvil_htmltable)
        #海克斯大乱斗锻造器（ARAM: Mayhem anvil）
        if len(self.KiwiAnvil_df) > 1:
            KiwiAnvil_df_web: pandas.DataFrame = self.KiwiAnvil_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AugmentLargeIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.KiwiAnvil_df.loc[1:, "AugmentLargeIconPath"].to_list()))
            KiwiAnvil_df_web.insert(len(KiwiAnvil_df_web.columns), "AugmentLargeIconUrl", ["锻造器大图标网址"] + AugmentLargeIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "AugmentNameId",
                "AugmentLargeIconUrl",
                "Enabled",
                "NameTra_content_zh",
                "NameTra_content_en",
                "anvilRarities",
                "DescriptionTra_content_zh_burn",
                "DescriptionTra_content_en_burn"
            ]
            KiwiAnvil_df_web = KiwiAnvil_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            KiwiAnvil_df_styled: pandas.io.formats.style.Styler = KiwiAnvil_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:6]
            KiwiAnvil_df_styled = KiwiAnvil_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            KiwiAnvil_htmltable: str = KiwiAnvil_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            KiwiAnvil_htmltable = '<meta charset="UTF-8">\n' + KiwiAnvil_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"KiwiAnvil_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(KiwiAnvil_htmltable)
