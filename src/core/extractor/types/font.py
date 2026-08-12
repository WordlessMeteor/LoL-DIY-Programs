import copy, json, os, pandas, re, sys, time
from openpyxl.worksheet.worksheet import Worksheet
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.webRequest import requestUrl
from src.utils.format import optimize_bool_display, addDefaultStyle, eliminate_empty_fields, pyobj2json
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.headers import fontDesc_header, fontType_header, fontResolution_header, fontStyle_header, font_CSSStyle_header, font_CSSIcon_header
from src.core.extractor.base import LoLDataExtractor

class FontExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个字体提取器对象。<br>Initialize a FontExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.font_ready: bool = False
        self.fontDesc_df: pandas.DataFrame = pandas.DataFrame()
        self.fontType_df: pandas.DataFrame = pandas.DataFrame()
        self.fontResolution_df: pandas.DataFrame = pandas.DataFrame()
        self.fontStyle_df: pandas.DataFrame = pandas.DataFrame()
        self.font_CSSStyle_df: pandas.DataFrame = pandas.DataFrame()
        self.font_CSSIcon_df: pandas.DataFrame = pandas.DataFrame()

    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.font_ready = False
    
    def get_font_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取字体二进制描述数据。<br>Get binary description data of fonts online.
        '''
        logPrint = self.log.logPrint
        fonts_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/ux/fonts.cdtb.bin.json"
        if fonts_bin_url in self.__class__.data_cache["online"]:
            self.fonts_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][fonts_bin_url]
        else:
            source, status, self.session = requestUrl("GET", fonts_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("字体信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nFont data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(fonts_bin_url))
                else:
                    logPrint("字体信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nFont data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            self.fonts_bin = source.json()
            self.fonts_bin = self.resolve_bin_hash(self.fonts_bin)
            self.__class__.data_cache["online"][fonts_bin_url] = self.fonts_bin
        self.font_ready = True

    def read_font_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取字体二进制描述数据。<br>Get binary description data of fonts offline.
        
        :param path: 字体二进制描述文件的本地路径。<br>A local path of font binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        fonts_bin_path: str = path
        if fonts_bin_path in self.__class__.data_cache["local"]:
            self.fonts_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][fonts_bin_path]
        else:
            with open(fonts_bin_path, "r", encoding = "utf-8") as fp:
                self.fonts_bin = json.load(fp)
            self.fonts_bin = self.resolve_bin_hash(self.fonts_bin)
            self.__class__.data_cache["local"][fonts_bin_path] = self.fonts_bin
        self.font_ready = True

    def build_font_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建字体数据框。<br>Build font dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 字体二进制描述文件的本地路径。<br>A local path of font binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.font_ready:
            #获取字体息（Get font information）
            logPrint("正在读取字体数据……\nReading font data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_font_data(path = path)
            else:
                self.get_font_data()
            if not self.font_ready:
                logPrint("字体数据尚未准备就绪！\nFont data not prepared!")
                return 2

        #定义数据结构（Define the data structure）
        logPrint("正在构建字体数据框……\nBuilding the font dataframes ...", print_time = True)
        ##字体描述（Font description）
        fontDesc_header_keys: list[str] = list(fontDesc_header.keys())
        fontDesc_data: dict[str, list[Any]] = {key: [] for key in fontDesc_header_keys}
        fontDesc_data_json: dict[str, list[Any]] = copy.deepcopy(fontDesc_data)
        ##字体类型（Font type）
        fontType_header_keys: list[str] = list(fontType_header.keys())
        fontType_data: dict[str, list[Any]] = {key: [] for key in fontType_header_keys}
        fontType_data_json: dict[str, list[Any]] = copy.deepcopy(fontType_data)
        ##字体分辨率（Font resolution）
        fontResolution_header_keys: list[str] = list(fontResolution_header.keys())
        fontResolution_data: dict[str, list[Any]] = {key: [] for key in fontResolution_header_keys}
        fontResolution_data_json: dict[str, list[Any]] = copy.deepcopy(fontResolution_data)
        ##字体样式（Font style）
        fontStyle_header_keys: list[str] = list(fontStyle_header.keys())
        fontStyle_data: dict[str, list[Any]] = {key: [] for key in fontStyle_header_keys}
        fontStyle_data_json: dict[str, list[Any]] = copy.deepcopy(fontStyle_data)
        ##CSS样式（CSS style）
        font_CSSStyle_header_keys: list[str] = list(font_CSSStyle_header.keys())
        font_CSSStyle_data: dict[str, list[Any]] = {key: [] for key in font_CSSStyle_header_keys}
        font_CSSStyle_data_json: dict[str, list[Any]] = copy.deepcopy(font_CSSStyle_data)
        ##说明文本内嵌图标（Tooltip inline icon）
        font_CSSIcon_header_keys: list[str] = list(font_CSSIcon_header.keys())
        font_CSSIcon_data: dict[str, list[Any]] = {key: [] for key in font_CSSIcon_header_keys}
        font_CSSIcon_data_json: dict[str, list[Any]] = copy.deepcopy(font_CSSIcon_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        for (key1, value) in self.fonts_bin.items():
            if key1 != "__linked" and value["__type"] == "GameFontDescription": #字体描述（Font description）
                for i in range(len(fontDesc_header_keys)):
                    key: str = fontDesc_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        to_append = value.get(key, "")
                    fontDesc_data[key].append(to_append)
                    fontDesc_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "FontType": #字体类型（Font type）
                for localeType_index in range(len(value["localeTypes"])):
                    localeType: dict[str, str] = value["localeTypes"][localeType_index]
                    for i in range(len(fontType_header_keys)):
                        key: str = fontType_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #语言配置类型序号（`localeType_index`）
                            to_append = localeType_index
                        else:
                            to_append = localeType.get(key, "")
                        fontType_data[key].append(to_append)
                        fontType_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "FontResolutionData": #字体分辨率（Font resolution）
                for localeResolution_index in range(len(value["localeResolutions"])):
                    localeResolution: list[dict[str, Any]] = value["localeResolutions"][localeResolution_index]
                    for resolution_index in range(len(localeResolution["resolutions"])):
                        resolution: dict[str, Any] = localeResolution["resolutions"][resolution_index]
                        for i in range(len(fontResolution_header_keys)):
                            key: str = fontResolution_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i == 1: #自动缩放（`autoScale`）
                                to_append = value.get("autoScale", True)
                            elif i <= 3:
                                if i == 2: #分辨率语言方案序号（`localeResolution_index`）
                                    to_append = localeResolution_index
                                else: #语言（`localeName`）
                                    to_append = localeResolution.get("localeName", "")
                            else:
                                if i == 4: #分辨率方案序号（`resolution_index`）
                                    to_append = resolution_index
                                else:
                                    to_append = value.get(key, "")
                            fontResolution_data[key].append(to_append)
                            fontResolution_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{215f4776}": #字体样式（Font style）
                for variant_index in range(len(value["{1b2d687d}"])):
                    variant: dict[str, Any] = value["{1b2d687d}"][variant_index]
                    for i in range(len(fontStyle_header_keys)):
                        key: str = fontStyle_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #字体显示名（`displayName`）
                            to_append = value["displayName"]
                        else:
                            if i == 2: #变体序号（`variant_index`）
                                to_append = variant_index
                            else:
                                to_append = variant.get(key, "")
                        fontStyle_data[key].append(to_append)
                        fontStyle_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "CSSSheet":
                if "styles" in value: #CSS样式（CSS style）
                    for (tag, style) in value["styles"].items():
                        for i in range(len(font_CSSStyle_header_keys)):
                            key: str = font_CSSStyle_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i == 1: #路径检索字符串（`PathHashToSelf`）
                                to_append = value["PathHashToSelf"]
                            elif i == 2: #CSS样式（`tag`）
                                to_append = tag
                            else:
                                if i == 3: #颜色（`Color`）
                                    to_append = style.get(key, "")
                                elif i == 4: #加粗（`bold`）
                                    to_append = style.get(key, True)
                                else:
                                    to_append = style.get(key, False)
                            font_CSSStyle_data[key].append(to_append)
                            font_CSSStyle_data_json[key].append(pyobj2json(to_append))
                if "icons" in value: #说明文本内嵌图标（Tooltip inline icon）
                    for (tag, icon) in value["icons"].items():
                        for i in range(len(font_CSSIcon_header_keys)):
                            key: str = font_CSSIcon_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i == 1: #路径检索字符串（`PathHashToSelf`）
                                to_append = value["PathHashToSelf"]
                            elif i == 2: #修饰符标签（`tag`）
                                to_append = tag
                            else:
                                to_append = icon.get(key, "")
                            font_CSSIcon_data[key].append(to_append)
                            font_CSSIcon_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        ##字体描述（Font description）
        fontDesc_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 9]
        fontDesc_data_organized: dict[str, list[Any]] = {fontDesc_header_keys[i]: fontDesc_data_json[fontDesc_header_keys[i]] for i in fontDesc_statistics_output_order}
        fontDesc_df: pandas.DataFrame = pandas.DataFrame(data = fontDesc_data_organized)
        logPrint("正在优化字体描述数据框的逻辑值显示……\nOptimizing boolean value display of the font description dataframe ...")
        optimize_bool_display(fontDesc_df)
        fontDesc_df = pandas.concat([pandas.DataFrame([fontDesc_header])[fontDesc_df.columns], fontDesc_df], ignore_index = True)
        self.fontDesc_df = fontDesc_df
        ##字体类型（Font type）
        fontType_statistics_output_order: list[int] = [0, 1, 2, 3, 4]
        fontType_data_organized: dict[str, list[Any]] = {fontType_header_keys[i]: fontType_data_json[fontType_header_keys[i]] for i in fontType_statistics_output_order}
        fontType_df: pandas.DataFrame = pandas.DataFrame(data = fontType_data_organized)
        logPrint("正在优化字体类型数据框的逻辑值显示……\nOptimizing boolean value display of the font type dataframe ...")
        optimize_bool_display(fontType_df)
        fontType_df = pandas.concat([pandas.DataFrame([fontType_header])[fontType_df.columns], fontType_df], ignore_index = True)
        self.fontType_df = fontType_df
        ##字体分辨率（Font resolution）
        fontResolution_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        fontResolution_data_organized: dict[str, list[Any]] = {fontResolution_header_keys[i]: fontResolution_data_json[fontResolution_header_keys[i]] for i in fontResolution_statistics_output_order}
        fontResolution_df: pandas.DataFrame = pandas.DataFrame(data = fontResolution_data_organized)
        logPrint("正在优化字体分辨率数据框的逻辑值显示……\nOptimizing boolean value display of the font resolution dataframe ...")
        optimize_bool_display(fontResolution_df)
        fontResolution_df = pandas.concat([pandas.DataFrame([fontResolution_header])[fontResolution_df.columns], fontResolution_df], ignore_index = True)
        self.fontResolution_df = fontResolution_df
        ##字体样式（Font style）
        fontStyle_statistics_output_order: list[int] = [0, 1, 2, 3, 5, 6, 4]
        fontStyle_data_organized: dict[str, list[Any]] = {fontStyle_header_keys[i]: fontStyle_data_json[fontStyle_header_keys[i]] for i in fontStyle_statistics_output_order}
        fontStyle_df: pandas.DataFrame = pandas.DataFrame(data = fontStyle_data_organized)
        logPrint("正在优化字体样式数据框的逻辑值显示……\nOptimizing boolean value display of the font style dataframe ...")
        optimize_bool_display(fontStyle_df)
        fontStyle_df = pandas.concat([pandas.DataFrame([fontStyle_header])[fontStyle_df.columns], fontStyle_df], ignore_index = True)
        self.fontStyle_df = fontStyle_df
        ##CSS样式（CSS style）
        font_CSSStyle_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6]
        font_CSSStyle_data_organized: dict[str, list[Any]] = {font_CSSStyle_header_keys[i]: font_CSSStyle_data_json[font_CSSStyle_header_keys[i]] for i in font_CSSStyle_statistics_output_order}
        font_CSSStyle_df: pandas.DataFrame = pandas.DataFrame(data = font_CSSStyle_data_organized)
        logPrint("正在优化CSS样式数据框的逻辑值显示……\nOptimizing boolean value display of the CSS style dataframe ...")
        optimize_bool_display(font_CSSStyle_df)
        font_CSSStyle_df = pandas.concat([pandas.DataFrame([font_CSSStyle_header])[font_CSSStyle_df.columns], font_CSSStyle_df], ignore_index = True)
        self.font_CSSStyle_df = font_CSSStyle_df
        ##说明文本内嵌图标（Tooltip inline icon）
        font_CSSIcon_statistics_output_order: list[int] = [0, 1, 2, 3, 4]
        font_CSSIcon_data_organized: dict[str, list[Any]] = {font_CSSIcon_header_keys[i]: font_CSSIcon_data_json[font_CSSIcon_header_keys[i]] for i in font_CSSIcon_statistics_output_order}
        font_CSSIcon_df: pandas.DataFrame = pandas.DataFrame(data = font_CSSIcon_data_organized)
        logPrint("正在优化说明文本内嵌图标数据框的逻辑值显示……\nOptimizing boolean value display of the tooltip inline icon dataframe ...")
        optimize_bool_display(font_CSSIcon_df)
        font_CSSIcon_df = pandas.concat([pandas.DataFrame([font_CSSIcon_header])[font_CSSIcon_df.columns], font_CSSIcon_df], ignore_index = True)
        self.font_CSSIcon_df = font_CSSIcon_df
        return 0
    
    def enqueue_font_dataframe(self) -> None:
        '''
        将字体数据框追加到数据提取器基类的数据框队列尾部。<br>Append font dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.fontDesc_df.empty:
            fontDesc_ws: dict[str, Any] = self.worksheet_metadata["FontDescription"]
            sheet1_name: str = fontDesc_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else fontDesc_ws["sheet_name_without_version"]
            fontDesc_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(fontDesc_ws["dType"]), "dType": fontDesc_ws["dType"], "sheet_name": sheet1_name, "sheet": self.fontDesc_df}
            self.enqueue_df(fontDesc_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.fontType_df.empty:
            fontType_ws: dict[str, Any] = self.worksheet_metadata["FontType"]
            sheet1_name: str = fontType_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else fontType_ws["sheet_name_without_version"]
            fontType_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(fontType_ws["dType"]), "dType": fontType_ws["dType"], "sheet_name": sheet1_name, "sheet": self.fontType_df}
            self.enqueue_df(fontType_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.fontResolution_df.empty:
            fontResolution_ws: dict[str, Any] = self.worksheet_metadata["FontResolution"]
            sheet1_name: str = fontResolution_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else fontResolution_ws["sheet_name_without_version"]
            fontResolution_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(fontResolution_ws["dType"]), "dType": fontResolution_ws["dType"], "sheet_name": sheet1_name, "sheet": self.fontResolution_df}
            self.enqueue_df(fontResolution_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.fontStyle_df.empty:
            fontStyle_ws: dict[str, Any] = self.worksheet_metadata["FontStyle"]
            sheet1_name: str = fontStyle_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else fontStyle_ws["sheet_name_without_version"]
            fontStyle_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(fontStyle_ws["dType"]), "dType": fontStyle_ws["dType"], "sheet_name": sheet1_name, "sheet": self.fontStyle_df}
            self.enqueue_df(fontStyle_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.font_CSSStyle_df.empty:
            font_CSSStyle_ws: dict[str, Any] = self.worksheet_metadata["FontCSSStyle"]
            sheet1_name: str = font_CSSStyle_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else font_CSSStyle_ws["sheet_name_without_version"]
            font_CSSStyle_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(font_CSSStyle_ws["dType"]), "dType": font_CSSStyle_ws["dType"], "sheet_name": sheet1_name, "sheet": self.font_CSSStyle_df}
            self.enqueue_df(font_CSSStyle_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.font_CSSIcon_df.empty:
            font_CSSIcon_ws: dict[str, Any] = self.worksheet_metadata["InlineIcon"]
            sheet1_name: str = font_CSSIcon_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else font_CSSIcon_ws["sheet_name_without_version"]
            font_CSSIcon_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(font_CSSIcon_ws["dType"]), "dType": font_CSSIcon_ws["dType"], "sheet_name": sheet1_name, "sheet": self.font_CSSIcon_df}
            self.enqueue_df(font_CSSIcon_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_font_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出字体数据到工作簿中。产生以下工作表：<br>Export font data to a workbook. The following worksheets are added:
        - 字体描述（Font Description）
        - 字体类型（Font Type）
        - 字体分辨率（Font Resolution）
        - 字体样式（Font Style）
        - CSS样式（CSS Style）
        - 内嵌图标（Inline Icon）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 字体二进制描述文件的本地路径。<br>A local path of font binary description file.
        
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
        if self.fontDesc_df.empty or self.fontType_df.empty or self.fontResolution_df.empty or self.fontStyle_df.empty or self.font_CSSStyle_df.empty or self.font_CSSIcon_df.empty:
            status: int = self.build_font_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            fontDesc_df: pandas.DataFrame = eliminate_empty_fields(self.fontDesc_df)
            fontType_df: pandas.DataFrame = eliminate_empty_fields(self.fontType_df)
            fontResolution_df: pandas.DataFrame = eliminate_empty_fields(self.fontResolution_df)
            fontStyle_df: pandas.DataFrame = eliminate_empty_fields(self.fontStyle_df)
            font_CSSStyle_df: pandas.DataFrame = eliminate_empty_fields(self.font_CSSStyle_df)
        else:
            font_CSSIcon_df = self.font_CSSIcon_df
            fontDesc_df = self.fontDesc_df
            fontType_df = self.fontType_df
            fontResolution_df = self.fontResolution_df
            fontStyle_df = self.fontStyle_df
            font_CSSStyle_df = self.font_CSSStyle_df
            font_CSSIcon_df = self.font_CSSIcon_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["FontDescription"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["FontDescription"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["FontType"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["FontType"]["sheet_name_without_version"]
        sheet3_name: str = self.worksheet_metadata["FontResolution"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["FontResolution"]["sheet_name_without_version"]
        sheet4_name: str = self.worksheet_metadata["FontStyle"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["FontStyle"]["sheet_name_without_version"]
        sheet5_name: str = self.worksheet_metadata["FontCSSStyle"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["FontCSSStyle"]["sheet_name_without_version"]
        sheet6_name: str = self.worksheet_metadata["InlineIcon"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["InlineIcon"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(fontDesc_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(fontType_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    addDefaultStyle(fontResolution_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    addDefaultStyle(fontStyle_df).to_excel(excel_writer = writer, sheet_name = sheet4_name)
                    addDefaultStyle(font_CSSStyle_df).to_excel(excel_writer = writer, sheet_name = sheet5_name)
                    addDefaultStyle(font_CSSIcon_df).to_excel(excel_writer = writer, sheet_name = sheet6_name)
                    for sheet_name in [sheet1_name, sheet2_name, sheet3_name, sheet4_name, sheet5_name, sheet6_name]:
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
                logPrint(f"字体数据已导出到{self.wbPath}。\nFont data have been exported to {self.wbPath}.", print_time = True)
                break
