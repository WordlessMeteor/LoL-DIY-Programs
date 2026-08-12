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
from src.core.config.headers import cheatset_header, cheat_header
from src.core.extractor.base import LoLDataExtractor

class CheatExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个作弊指令提取器对象。<br>Initialize a CheatExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.cheats_ready: bool = False
        self.cheatset_df: pandas.DataFrame = pandas.DataFrame()
        self.cheat_df: pandas.DataFrame = pandas.DataFrame()

    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.cheats_ready = False
    
    def get_cheat_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取作弊指令二进制描述数据。<br>Get binary description data of cheats online.
        '''
        logPrint = self.log.logPrint
        cheats_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/cheats.cdtb.bin.json"
        if cheats_bin_url in self.__class__.data_cache["online"]:
            self.cheats_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][cheats_bin_url]
        else:
            source, status, self.session = requestUrl("GET", cheats_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint('作弊指令信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nCheat data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s' %(cheats_bin_url))
                else:
                    logPrint('作弊指令信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nCheat data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                time.sleep(3)
                self.init_data_readiness()
                return
            self.cheats_bin = source.json()
            self.cheats_bin = self.resolve_bin_hash(self.cheats_bin)
            self.__class__.data_cache["online"][cheats_bin_url] = self.cheats_bin
        self.cheats_ready = True
    
    def read_cheat_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取作弊指令二进制描述数据。<br>Get binary description data of cheats offline.
        
        :param path: 作弊指令二进制描述文件的本地路径。<br>A local path of cheat binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        cheats_bin_path: str = path
        if cheats_bin_path in self.__class__.data_cache["local"]:
            self.cheats_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][cheats_bin_path]
        else:
            with open(cheats_bin_path, "r", encoding = "utf-8") as fp:
                self.cheats_bin = json.load(fp)
            self.cheats_bin = self.resolve_bin_hash(self.cheats_bin)
            self.__class__.data_cache["local"][cheats_bin_path] = self.cheats_bin
        self.cheats_ready = True
    
    def build_cheat_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建作弊指令数据框。<br>Build cheat dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 作弊指令二进制描述文件的本地路径。<br>A local path of cheat binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.cheats_ready:
            #获取作弊指令信息（Get cheat information）
            logPrint("正在读取作弊指令数据……\nReading cheat data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_cheat_data(path = path)
            else:
                self.get_cheat_data()
            if not self.cheats_ready:
                logPrint("作弊指令数据尚未准备就绪！\nCheat data not prepared!")
                return 2
        logPrint("正在构建作弊指令集数据框……\nBuilding the cheat set dataframes ...", print_time = True)
        
        #定义数据结构（Define the data structure）
        cheatset_header_keys: list[str] = list(cheatset_header.keys())
        cheatset_data: dict[str, list[Any]] = {key: [] for key in cheatset_header_keys}
        cheatset_data_json: dict[str, list[Any]] = copy.deepcopy(cheatset_data)
        cheat_header_keys: list[str] = list(cheat_header.keys())
        cheat_data: dict[str, list[Any]] = {key: [] for key in cheat_header_keys}
        cheat_data_json: dict[str, list[Any]] = copy.deepcopy(cheat_data)
        
        #构建指令到指令集的映射（Build the map from cheats to cheatsets）
        cheatset_map: dict[str, str] = {}
        for (key, value) in self.cheats_bin.items():
            if key != "__linked" and value["__type"] == "CheatSet":
                if "{bd50bdef}" in value:
                    for cheatPage in value["{bd50bdef}"]:
                        for cheat in cheatPage["{928eb9b4}"]:
                            cheatset_map[cheat] = value["mName"]
                elif "mCheatPages" in value: #适用于14.15版本（Compatible with v14.15）
                    for cheatPage in value["mCheatPages"]:
                        for cheat in cheatPage["mCheats"]:
                            cheatset_map[cheat] = value["mName"]

        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.cheats_bin.items():
            if key1 != "__linked" and value["__type"] == "CheatSet":
                for i in range(len(cheatset_header_keys)):
                    key: str = cheatset_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        if i == 2 or i == 7: #逻辑值键（Boolean keys）
                            to_append = value.get(key, False)
                        else:
                            to_append = value.get(key, "")
                    cheatset_data[key].append(to_append)
                    cheatset_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"].endswith("Cheat"):
                for i in range(len(cheat_header_keys)):
                    key: str = cheat_header_keys[i]
                    if i == 0:
                        to_append = key1
                    elif i <= 29:
                        if i in {2, 5, 6, 11, 12, 21, 22, 23, 25, 26, 28}: #可见性（`mIsPlayerFacing`）
                            to_append = value.get(key, False)
                        else:
                            to_append = value.get(key, "")
                    elif i <= 43:
                        if "mCheatMenuUIData" in value:
                            if i <= 37:
                                to_append = value["mCheatMenuUIData"].get(key, False if i == 36 else "")
                            else:
                                subkey2: str = pStrConst.search(key).group()
                                subkey1: str = key.replace(subkey2, "")
                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                tooltip_key: str = cheat_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                to_append = tooltip_raw
                        else:
                            to_append = False if i == 36 else ""
                    else: #所属指令集代码（`belonging_cheatset_mName`）
                        to_append = cheatset_map.get(key1, "")
                    cheat_data[key].append(to_append)
                    cheat_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        ##作弊指令集（Cheatset）
        cheatset_statistics_output_order: list[int] = [0, 1, 2, 7, 3, 4, 5, 6]
        cheatset_data_organized: dict[str, list[Any]] = {cheatset_header_keys[i]: cheatset_data_json[cheatset_header_keys[i]] for i in cheatset_statistics_output_order}
        cheatset_df: pandas.DataFrame = pandas.DataFrame(data = cheatset_data_organized)
        logPrint("正在优化指令集数据框的逻辑值显示……\nOptimizing boolean value display of the cheatset dataframe ...")
        optimize_bool_display(cheatset_df)
        cheatset_df = pandas.concat([pandas.DataFrame([cheatset_header])[cheatset_df.columns], cheatset_df], ignore_index = True)
        self.cheatset_df = cheatset_df
        ##作弊指令（ScriptCheat）
        cheat_statistics_output_order: list[int] = [0, 29, 44, 1, 30, 2, 36, 9, 31, 38, 39, 32, 40, 41, 33, 42, 43, 34, 35, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
        cheat_data_organized: dict[str, list[Any]] = {cheat_header_keys[i]: cheat_data_json[cheat_header_keys[i]] for i in cheat_statistics_output_order}
        cheat_df: pandas.DataFrame = pandas.DataFrame(data = cheat_data_organized)
        logPrint("正在优化指令数据框的逻辑值显示……\nOptimizing boolean value display of the cheat dataframe ...")
        optimize_bool_display(cheat_df)
        cheat_df = pandas.concat([pandas.DataFrame([cheat_header])[cheat_df.columns], cheat_df], ignore_index = True)
        self.cheat_df = cheat_df
        return 0
    
    def enqueue_cheat_dataframe(self) -> None:
        '''
        将作弊指令数据框追加到数据提取器基类的数据框队列尾部。<br>Append cheat dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.cheatset_df.empty:
            cheatset_ws: dict[str, Any] = self.worksheet_metadata["CheatSet"]
            sheet1_name: str = cheatset_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else cheatset_ws["sheet_name_without_version"]
            cheatset_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(cheatset_ws["dType"]), "dType": cheatset_ws["dType"], "sheet_name": sheet1_name, "sheet": self.cheatset_df}
            self.enqueue_df(cheatset_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.cheat_df.empty:
            cheat_ws: dict[str, Any] = self.worksheet_metadata["Cheat"]
            sheet2_name: str = cheat_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else cheat_ws["sheet_name_without_version"]
            cheat_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(cheat_ws["dType"]), "dType": cheat_ws["dType"], "sheet_name": sheet2_name, "sheet": self.cheat_df}
            self.enqueue_df(cheat_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_cheat_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出作弊指令数据到工作簿中。产生以下工作表：<br>Export cheat data to a workbook. The following worksheets are added:
        - 指令集（CheatSet）
        - 指令（Cheat）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 作弊指令二进制描述文件的本地路径。<br>A local path of cheat binary description file.
        
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
        if self.cheatset_df.empty or self.cheat_df.empty:
            status: int = self.build_cheat_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            cheatset_df: pandas.DataFrame = eliminate_empty_fields(self.cheatset_df)
            cheat_df: pandas.DataFrame = eliminate_empty_fields(self.cheat_df)
        else:
            cheatset_df = self.cheatset_df
            cheat_df = self.cheat_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["CheatSet"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CheatSet"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["Cheat"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["Cheat"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(cheatset_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(cheat_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
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
                logPrint(f"作弊指令数据已导出到{self.wbPath}。\nCheat data have been exported to {self.wbPath}.", print_time = True)
                break
