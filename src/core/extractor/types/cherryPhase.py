import copy, json, os, pandas, re, sys, time
from openpyxl.worksheet.worksheet import Worksheet
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.webRequest import requestUrl
from src.utils.format import addDefaultStyle, eliminate_empty_fields, pyobj2json
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.headers import CherryRoundList_header, CherryRound_header, CherryPhase_header, CherryRoundPhase_header
from src.core.extractor.base import LoLDataExtractor

class CherryRoundExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个斗魂竞技场回合阶段提取器对象。<br>Initial a CherryRoundExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.map30_ready: bool = False
        self.CherryRoundList_df: pandas.DataFrame = pandas.DataFrame()
        self.CherryRound_df: pandas.DataFrame = pandas.DataFrame()
        self.CherryPhase_df: pandas.DataFrame = pandas.DataFrame()
        self.CherryRoundPhase_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.map30_ready = False
    
    def get_CherryRound_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取斗魂竞技场回合二进制描述数据。<br>Get binary description data of Arena rounds online.
        '''
        logPrint = self.log.logPrint
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
        self.map30_ready = True
    
    def read_CherryRound_data(self, path: str) -> None:
        '''
        离线获取荣誉嘉宾二进制描述数据。<br>Get binary description data of Guests of Honor offline.
        
        :param path: 荣誉嘉宾二进制描述文件的本地路径。<br>A local path of GoH binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        map30_bin_path: str = path
        if map30_bin_path in self.__class__.data_cache["local"]:
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map30_bin_path]
        else:
            with open(map30_bin_path, "r", encoding = "utf-8") as fp:
                self.map30_bin = json.load(fp)
            self.map30_bin = self.resolve_bin_hash(self.map30_bin)
            self.__class__.data_cache["local"][map30_bin_path] = self.map30_bin
        self.map30_ready = True
    
    def build_CherryRound_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建斗魂竞技场回合数据框。<br>Build Arena round dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 斗魂竞技场回合二进制描述文件的本地路径。<br>A local path of Arena round binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.map30_ready:
            #获取斗魂竞技场回合信息（Get Arena round information）
            logPrint("正在读取斗魂竞技场回合数据……\nReading Arena round data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_CherryRound_data(path = path)
            else:
                self.get_CherryRound_data()
            if not self.map30_ready:
                logPrint("斗魂竞技场回合数据尚未准备就绪！\nArena round data not prepared!")
                return 2
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建斗魂竞技场回合数据框……\nBuilding the Arena round dataframes ...", print_time = True)
        CherryRoundList_header_keys: list[str] = list(CherryRoundList_header.keys())
        CherryRoundList_data: dict[str, list[Any]] = {key: [] for key in CherryRoundList_header_keys}
        CherryRoundList_data_json: dict[str, list[Any]] = copy.deepcopy(CherryRoundList_data)
        CherryRound_header_keys: list[str] = list(CherryRound_header.keys())
        CherryRound_data: dict[str, list[Any]] = {key: [] for key in CherryRound_header_keys}
        CherryRound_data_json: dict[str, list[Any]] = copy.deepcopy(CherryRound_data)
        CherryPhase_header_keys: list[str] = list(CherryPhase_header.keys())
        CherryPhase_data: dict[str, list[Any]] = {key: [] for key in CherryPhase_header_keys}
        CherryPhase_data_json: dict[str, list[Any]] = copy.deepcopy(CherryPhase_data)
        CherryRoundPhase_header_keys: list[str] = list(CherryRoundPhase_header.keys())
        CherryRoundPhase_data: dict[str, list[Any]] = {key: [] for key in CherryRoundPhase_header_keys}
        CherryRoundPhase_data_json: dict[str, list[Any]] = copy.deepcopy(CherryRoundPhase_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.map30_bin.items():
            if key1 != "__linked" and value["__type"] == "LoLModesRoundsListData":
                rounds: list[str] = value["rounds"] if "rounds" in value else value["Rounds"] #“{b7b53758}”在“hashes.binfields.txt”中对应到“Rounds”，在“hashes.binhashes.txt”中对应到“rounds”（"rounds" corresponds to "Rounds" in "hashes.binfields.txt", while corresponds to "rounds" in "hashes.binhashes.txt"）
                for round_index in range(len(rounds)):
                    roundKey: str = rounds[round_index]
                    for i in range(len(CherryRoundList_header_keys)):
                        key: str = CherryRoundList_header_keys[i]
                        if i == 0: #方案主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #旗标（`{37e6e53a}`）
                            to_append = value["{37e6e53a}"]
                        elif i == 2: #回合数（`roundNumber`）
                            to_append = round_index + 1
                        elif i == 3: #回合主键（`roundKey`）
                            to_append = roundKey
                        else: #回合阶段本地化名称（Localized round phase names）
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 4 else strtable_lol_default
                            if roundKey in self.map30_bin:
                                phaseKeys: list[str] = self.map30_bin[roundKey]["Phases"]
                                phaseNames: list[str] = []
                                for phaseKey in phaseKeys:
                                    if phaseKey in self.map30_bin:
                                        phaseName_key: str = self.map30_bin[phaseKey]["DisplayNameTra"]
                                        phaseName: str = self.get_strtable_value(strtable_locale, phaseName_key, default = phaseName_key)
                                        phaseNames.append(phaseName)
                                    else:
                                        phaseNames.append("")
                                to_append = phaseNames
                            else:
                                to_append = ""
                        CherryRoundList_data[key].append(to_append)
                        CherryRoundList_data_json[key].append(pyobj2json(to_append))
                    round: dict[str, Any] = self.map30_bin[roundKey]
                    phases: list[str] = round["Phases"]
                    for phase_index in range(len(phases)):
                        phaseKey: str = phases[phase_index]
                        phase: dict[str, Any] = self.map30_bin[phaseKey]
                        subPhases: list[dict[str, Any]] = phase["SubPhases"]
                        for subPhase_index in range(len(subPhases)):
                            subPhase: dict[str, Any] = subPhases[subPhase_index]
                            for i in range(len(CherryRoundPhase_header_keys)):
                                key: str = CherryRoundPhase_header_keys[i]
                                if i <= 1:
                                    if i == 0: #方案主键（`key`）
                                        to_append: Any = key1
                                    else: ##旗标（`{37e6e53a}`）
                                        to_append = value["{37e6e53a}"]
                                elif i <= 3:
                                    if i == 2: #回合数（`roundNumber`）
                                        to_append = round_index + 1
                                    else: #回合主键（`roundKey`）
                                        to_append = roundKey
                                elif i <= 12:
                                    if i == 4: #阶段数（`PhaseNumber`）
                                        to_append = phase_index + 1
                                    elif i == 5: #阶段主键（`PhaseKey`）
                                        to_append = phaseKey
                                    elif i <= 10:
                                        to_append = phase.get(key, "")
                                    else: #显示名（Display name）
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 11 else strtable_lol_default
                                        to_append = self.get_strtable_value(strtable_locale, phase["DisplayNameTra"], default = "")
                                else:
                                    if i == 13: #子阶段序号（`subPhase number`）
                                        to_append = subPhase_index + 1
                                    else:
                                        to_append = subPhase.get(key.split()[1], "")
                                CherryRoundPhase_data[key].append(to_append)
                                CherryRoundPhase_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "LoLModesRoundData":
                phaseKeys: list[str] = value["Phases"]
                for i in range(len(CherryRound_header_keys)):
                    key: str = CherryRound_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i == 1: #阶段主键列表（`Phases`）
                        to_append = phaseKeys
                    else: #回合阶段本地化名称（Localized round phase names）
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 2 else strtable_lol_default
                        phaseNames: list[str] = []
                        for phaseKey in phaseKeys:
                            if phaseKey in self.map30_bin:
                                phaseName_key: str = self.map30_bin[phaseKey]["DisplayNameTra"]
                                phaseName: str = self.get_strtable_value(strtable_locale, phaseName_key, default = phaseName_key)
                                phaseNames.append(phaseName)
                            else:
                                phaseNames.append("")
                        to_append = phaseNames
                    CherryRound_data[key].append(to_append)
                    CherryRound_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "LoLModesPhaseData":
                for subPhase_index in range(len(value["SubPhases"])):
                    subPhase: dict[str, Any] = value["SubPhases"][subPhase_index]
                    for i in range(len(CherryPhase_header_keys)):
                        key: str = CherryPhase_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i <= 7:
                            if i <= 5:
                                to_append = value.get(key, "")
                            else: #回合阶段本地化名称（Localized round phase names）
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 6 else strtable_lol_default
                                to_append = self.get_strtable_value(strtable_locale, value["DisplayNameTra"], default = "")
                        else:
                            if i == 8: #阶段序号（`phase number`）
                                to_append = subPhase_index + 1
                            else:
                                to_append = subPhase.get(key.split()[1], "")
                        CherryPhase_data[key].append(to_append)
                        CherryPhase_data_json[key].append(pyobj2json(to_append))
        CherryRoundList_statistics_output_order: list[int] = [0, 2, 3, 4, 5]
        CherryRoundList_data_organized: dict[str, list[Any]] = {CherryRoundList_header_keys[i]: CherryRoundList_data_json[CherryRoundList_header_keys[i]] for i in CherryRoundList_statistics_output_order}
        CherryRoundList_df: pandas.DataFrame = pandas.DataFrame(data = CherryRoundList_data_organized)
        CherryRoundList_df = pandas.concat([pandas.DataFrame([CherryRoundList_header])[CherryRoundList_df.columns], CherryRoundList_df], ignore_index = True)
        self.CherryRoundList_df = CherryRoundList_df
        CherryRound_statistics_output_order: list[int] = [0, 1, 2, 3]
        CherryRound_data_organized: dict[str, list[Any]] = {CherryRound_header_keys[i]: CherryRound_data_json[CherryRound_header_keys[i]] for i in CherryRound_statistics_output_order}
        CherryRound_df: pandas.DataFrame = pandas.DataFrame(data = CherryRound_data_organized)
        CherryRound_df = pandas.concat([pandas.DataFrame([CherryRound_header])[CherryRound_df.columns], CherryRound_df], ignore_index = True)
        self.CherryRound_df = CherryRound_df
        CherryPhase_statistics_output_order: list[int] = [0, 2, 6, 7, 1, 8, 9, 10, 11, 12, 13, 3, 4, 5]
        CherryPhase_data_organized: dict[str, list[Any]] = {CherryPhase_header_keys[i]: CherryPhase_data_json[CherryPhase_header_keys[i]] for i in CherryPhase_statistics_output_order}
        CherryPhase_df: pandas.DataFrame = pandas.DataFrame(data = CherryPhase_data_organized)
        CherryPhase_df = pandas.concat([pandas.DataFrame([CherryPhase_header])[CherryPhase_df.columns], CherryPhase_df], ignore_index = True)
        self.CherryPhase_df = CherryPhase_df
        CherryRoundPhase_statistics_output_order: list[int] = [0, 2, 3, 4, 5, 7, 11, 12, 6, 13, 14, 15, 16, 17, 18, 8, 9, 10]
        CherryRoundPhase_data_organized: dict[str, list[Any]] = {CherryRoundPhase_header_keys[i]: CherryRoundPhase_data_json[CherryRoundPhase_header_keys[i]] for i in CherryRoundPhase_statistics_output_order}
        CherryRoundPhase_df: pandas.DataFrame = pandas.DataFrame(data = CherryRoundPhase_data_organized)
        CherryRoundPhase_df = pandas.concat([pandas.DataFrame([CherryRoundPhase_header])[CherryRoundPhase_df.columns], CherryRoundPhase_df], ignore_index = True)
        self.CherryRoundPhase_df = CherryRoundPhase_df
        return 0
    
    def enqueue_CherryRound_dataframe(self) -> None:
        '''
        将斗魂竞技场回合阶段数据框追加到数据提取器基类的数据框队列尾部。<br>Append Arena round phase dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.CherryRoundList_df.empty:
            CherryRoundList_ws: dict[str, Any] = self.worksheet_metadata["CherryRoundList"]
            sheet1_name: str = CherryRoundList_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else CherryRoundList_ws["sheet_name_without_version"]
            CherryRoundList_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(CherryRoundList_ws["dType"]), "dType": CherryRoundList_ws["dType"], "sheet_name": sheet1_name, "sheet": self.CherryRoundList_df}
            self.enqueue_df(CherryRoundList_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.CherryRound_df.empty:
            CherryRound_ws: dict[str, Any] = self.worksheet_metadata["CherryRound"]
            sheet2_name: str = CherryRound_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else CherryRound_ws["sheet_name_without_version"]
            CherryRound_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(CherryRound_ws["dType"]), "dType": CherryRound_ws["dType"], "sheet_name": sheet2_name, "sheet": self.CherryRound_df}
            self.enqueue_df(CherryRound_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.CherryPhase_df.empty:
            CherryPhase_ws: dict[str, Any] = self.worksheet_metadata["CherryPhase"]
            sheet3_name: str = CherryPhase_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else CherryPhase_ws["sheet_name_without_version"]
            CherryPhase_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(CherryPhase_ws["dType"]), "dType": CherryPhase_ws["dType"], "sheet_name": sheet3_name, "sheet": self.CherryPhase_df}
            self.enqueue_df(CherryPhase_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.CherryRoundPhase_df.empty:
            CherryRoundPhase_ws: dict[str, Any] = self.worksheet_metadata["CherryRoundPhase"]
            sheet4_name: str = CherryRoundPhase_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else CherryRoundPhase_ws["sheet_name_without_version"]
            CherryRoundPhase_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(CherryRoundPhase_ws["dType"]), "dType": CherryRoundPhase_ws["dType"], "sheet_name": sheet4_name, "sheet": self.CherryRoundPhase_df}
            self.enqueue_df(CherryRoundPhase_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_CherryRound_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出斗魂竞技场回合数据到工作簿中。产生以下工作表：<br>Export Arena round data to a workbook. The following worksheet is added:
        - 斗魂竞技场回合列表（Cherry Round List）
        - 斗魂竞技场回合（Cherry Round）
        - 斗魂竞技场阶段（Cherry Phase）
        - 斗魂竞技场回合阶段（Cherry Round Phase）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 斗魂竞技场回合二进制描述文件的本地路径。<br>A local path of Arena round binary description file.
        
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
        if self.CherryRoundList_df.empty or self.CherryRound_df.empty or self.CherryPhase_df.empty or self.CherryRoundPhase_df.empty:
            status: int = self.build_CherryRound_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            CherryRoundList_df: pandas.DataFrame = eliminate_empty_fields(self.CherryRoundList_df)
            CherryRound_df: pandas.DataFrame = eliminate_empty_fields(self.CherryRound_df)
            CherryPhase_df: pandas.DataFrame = eliminate_empty_fields(self.CherryPhase_df)
            CherryRoundPhase_df: pandas.DataFrame = eliminate_empty_fields(self.CherryRoundPhase_df)
        else:
            CherryRoundList_df = self.CherryRoundList_df
            CherryRound_df = self.CherryRound_df
            CherryPhase_df = self.CherryPhase_df
            CherryRoundPhase_df = self.CherryRoundPhase_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["CherryRoundList"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryRoundList"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["CherryRound"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryRound"]["sheet_name_without_version"]
        sheet3_name: str = self.worksheet_metadata["CherryPhase"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryPhase"]["sheet_name_without_version"]
        sheet4_name: str = self.worksheet_metadata["CherryRoundPhase"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryRoundPhase"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(CherryRoundList_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(CherryRound_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    addDefaultStyle(CherryPhase_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    addDefaultStyle(CherryRoundPhase_df).to_excel(excel_writer = writer, sheet_name = sheet4_name)
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
                logPrint(f"斗魂竞技场回合数据已导出到{self.wbPath}。\nArena round data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出斗魂竞技场回合阶段数据到网页中。产生以下文件：<br>Export Arena round phase data into an html file. The following file is produced:
        - 斗魂竞技场回合阶段（Arena Round Phase）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 怒火角斗场地图二进制描述文件的本地路径。<br>A local path of Rings of Wrath map binary description file.
        
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
        if self.CherryRoundPhase_df.empty:
            status: int = self.build_CherryRound_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #斗魂竞技场回合阶段（Arena Round Phase）
        if len(self.CherryRoundPhase_df) > 1:
            CherryRoundPhase_df_web: pandas.DataFrame = self.CherryRoundPhase_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            UpcomingIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.CherryRoundPhase_df.loc[1:, "{7011dd78}"].to_list()))
            ProgressIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.CherryRoundPhase_df.loc[1:, "{44bdfcf8}"].to_list()))
            FinishedIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.CherryRoundPhase_df.loc[1:, "{bafc35cb}"].to_list()))
            CherryRoundPhase_df_web.insert(len(CherryRoundPhase_df_web.columns), "UpcomingIconUrl", ["即将到来的事件缩略图网址"] + UpcomingIconUrls)
            CherryRoundPhase_df_web.insert(len(CherryRoundPhase_df_web.columns), "ProgressIconUrl", ["正在发生的事件缩略图网址"] + ProgressIconUrls)
            CherryRoundPhase_df_web.insert(len(CherryRoundPhase_df_web.columns), "FinishedIconUrl", ["已经完成的事件缩略图网址"] + FinishedIconUrls)
            ##保留小数（Round）
            CherryRoundPhase_df_web.loc[1:, "subPhase duration"] = CherryRoundPhase_df_web.loc[1:, "subPhase duration"].apply(lambda x: self.aRound(x, 5))
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "key",
                "roundNumber",
                "PhaseNumber",
                "DisplayNameTra_content_zh",
                "DisplayNameTra_content_en",
                "subPhase number",
                "subPhase duration",
                "UpcomingIconUrl",
                "ProgressIconUrl",
                "FinishedIconUrl"
            ]
            CherryRoundPhase_df_web = CherryRoundPhase_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            CherryRoundPhase_df_styled: pandas.io.formats.style.Styler = CherryRoundPhase_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:]
            CherryRoundPhase_df_styled = CherryRoundPhase_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            CherryRoundPhase_htmltable: str = CherryRoundPhase_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            CherryRoundPhase_htmltable = '<meta charset="UTF-8">\n' + CherryRoundPhase_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"CherryRoundPhase_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(CherryRoundPhase_htmltable)
