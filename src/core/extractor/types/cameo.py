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
from src.core.config.headers import cameo_header
from src.core.extractor.base import LoLDataExtractor

class CameoExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个场景英雄提取器对象。<br>Initial a CameoExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.cameo_ready: bool = False
        self.cameo_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.cameo_ready = False
    
    def get_cameo_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取场景英雄二进制描述数据。<br>Get binary description data of cameos online.
        '''
        logPrint = self.log.logPrint
        map30_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map30/map30.bin.json"
        if map30_bin_url in self.__class__.data_cache["online"]:
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map30_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map30_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("斗魂竞技场场景英雄信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nArena cameo data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map30_bin_url))
                else:
                    logPrint('斗魂竞技场场景英雄信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nArena cameo data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                time.sleep(3)
                self.init_data_readiness()
                return
            self.map30_bin = source.json()
            self.map30_bin = self.resolve_bin_hash(self.map30_bin)
            self.__class__.data_cache["online"][map30_bin_url] = self.map30_bin
        self.cameo_ready = True
    
    def read_cameo_data(self, path: str) -> None:
        '''
        离线获取场景英雄二进制描述数据。<br>Get binary description data of Guests of Honor offline.
        
        :param path: 场景英雄二进制描述文件的本地路径。<br>A local path of cameo binary description file.
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
        self.cameo_ready = True
    
    def build_cameo_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建场景英雄数据框。<br>Build cameo dataframe.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 场景英雄二进制描述文件的本地路径。<br>A local path of cameo binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.cameo_ready:
            #获取场景英雄信息（Get cameo information）
            logPrint("正在读取场景英雄数据……\nReading cameo data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_cameo_data(path = path)
            else:
                self.get_cameo_data()
            if not self.cameo_ready:
                logPrint("场景英雄数据尚未准备就绪！\ncameo data not prepared!")
                return 2
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建场景英雄数据框……\nBuilding the cameo dataframes ...", print_time = True)
        cameo_header_keys: list[str] = list(cameo_header.keys())
        cameo_data: dict[str, list[Any]] = {key: [] for key in cameo_header_keys}
        cameo_data_json: dict[str, list[Any]] = copy.deepcopy(cameo_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.map30_bin.items():
            if key1 != "__linked" and value["__type"] == "CherryCameo":
                for i in range(len(cameo_header_keys)):
                    key: str = cameo_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i >= 1 and i <= 6:
                        to_append = value.get(key, True if i == 3 else "")
                    else:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = cameo_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            tooltip_burn = self.tooltipPreparation(tooltip_raw, self.locale if useTargetLocale else self.DEFAULT_LOCALE)
                            tooltip_burn = self.tooltipPostProcessing(tooltip_burn, self.locale if useTargetLocale else self.DEFAULT_LOCALE)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    cameo_data[key].append(to_append)
                    cameo_data_json[key].append(pyobj2json(to_append))
        cameo_statistics_output_order: list[int] = [0, 1, 3, 4, 7, 8, 5, 9, 10, 6, 11, 13, 12, 14]
        cameo_data_organized: dict[str, list[Any]] = {cameo_header_keys[i]: cameo_data_json[cameo_header_keys[i]] for i in cameo_statistics_output_order}
        cameo_df: pandas.DataFrame = pandas.DataFrame(data = cameo_data_organized)
        optimize_bool_display(cameo_df)
        cameo_df = pandas.concat([pandas.DataFrame([cameo_header])[cameo_df.columns], cameo_df], ignore_index = True)
        self.cameo_df = cameo_df
        return 0
    
    def enqueue_cameo_dataframe(self) -> None:
        '''
        将斗魂竞技场场景英雄数据框追加到数据提取器基类的数据框队列尾部。<br>Append the Arena cameo dataframe into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.cameo_df.empty:
            cameo_ws: dict[str, Any] = self.worksheet_metadata["CherryCameo"]
            sheet1_name: str = cameo_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else cameo_ws["sheet_name_without_version"]
            cameo_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(cameo_ws["dType"]), "dType": cameo_ws["dType"], "sheet_name": sheet1_name, "sheet": self.cameo_df}
            self.enqueue_df(cameo_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_cameo_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出场景英雄数据到工作簿中。产生以下工作表：<br>Export cameo data to a workbook. The following worksheet is added:
        - 斗魂竞技场场景英雄（Cherry Cameos）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 荣誉嘉宾二进制描述文件的本地路径。<br>A local path of cameo binary description file.
        
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
        if self.cameo_df.empty:
            status: int = self.build_cameo_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            cameo_df: pandas.DataFrame = eliminate_empty_fields(self.cameo_df)
        else:
            cameo_df = self.cameo_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["CherryCameo"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryCameo"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(cameo_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    for sheet_name in [sheet1_name]:
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
                logPrint(f"场景英雄数据已导出到{self.wbPath}。\nCameo data have been exported to {self.wbPath}.", print_time = True)
                break
