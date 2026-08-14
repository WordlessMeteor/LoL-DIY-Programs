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
from src.core.config.headers import summonerSpell_header
from src.core.extractor.base import LoLDataExtractor

class SummonerSpellExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个召唤师技能提取器对象。<br>Initialize a SummonerSpellExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.summonerSpell_ready: bool = True #共享数据已经在基类中获取过了，所以在通过基类初始化子类时，默认将这个属性设置为真（Shared data has already been obtained in the `LoLDataExtractor` base class, so when an object of this class is initialized, this attribute is set as True by default）
        self.summonerSpell_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.summonerSpell_ready = False
    
    def get_summonerSpell_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取召唤师技能二进制描述数据。<br>Get binary description data of summoner spells online.
        '''
        logPrint = self.log.logPrint
        shared_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/shared.cdtb.bin.json"
        if shared_bin_url in self.__class__.data_cache["online"]:
            self.shared_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][shared_bin_url]
        else:
            source, status, self.session = requestUrl("GET", shared_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("共享数据获取失败！请检查以下链接的可用性。程序即将返回上一层。\nShared data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(shared_bin_url))
                else:
                    logPrint("共享数据获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nShared data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            self.shared_bin = source.json()
            self.shared_bin = self.resolve_bin_hash(self.shared_bin)
            self.__class__.data_cache["online"][shared_bin_url] = self.shared_bin
        self.summonerSpell_ready = True
    
    def read_summonerSpell_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取召唤师技能二进制描述数据。<br>Get binary description data of summoner spells offline.

        :param path: 召唤师技能二进制描述文件的本地路径。<br>A local path of summoner spell binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        spells_bin_path: str = path
        if spells_bin_path in self.__class__.data_cache["local"]:
            self.shared_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][spells_bin_path]
        else:
            with open(spells_bin_path, "r", encoding = "utf-8") as fp:
                self.shared_bin = json.load(fp)
            self.shared_bin = self.resolve_bin_hash(self.shared_bin)
            self.__class__.data_cache["local"][spells_bin_path] = self.shared_bin
        self.summonerSpell_ready = True

    def build_summonerSpell_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建召唤师技能数据框。<br>Build summoner spell dataframe.

        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 召唤师技能二进制描述文件的本地路径。<br>A local path of summoner spell binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.summonerSpell_ready:
            #获取召唤师技能信息（Get summoner spell information）
            logPrint("正在读取召唤师技能数据……\nReading summoner spell data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_summonerSpell_data(path = path)
            else:
                self.get_summonerSpell_data()
            if not self.summonerSpell_ready:
                logPrint("召唤师技能数据尚未准备就绪！\nSummoner spell data not prepared!")
                return 2
        
        #提取召唤师技能数据（Extract summoner spell data）
        summonerSpell_bin: dict[str, dict[str, Any]] = {key: value for (key, value) in self.shared_bin.items() if key != "__linked" and value["__type"] == "SpellObject" and "mSpell" in value and "mPlatformSpellInfo" in value["mSpell"]}

        #定义数据结构（Define the data structure）
        logPrint("正在构建召唤师技能数据框……\nBuilding the summoner spell dataframes ...", print_time = True)
        summonerSpell_header_keys: list[str] = list(summonerSpell_header.keys())
        summonerSpell_data: dict[str, list[Any]] = {key: [] for key in summonerSpell_header_keys}
        summonerSpell_data_json: dict[str, list[Any]] = copy.deepcopy(summonerSpell_data)
        
        #数据整理核心部分（Data organization core part）
        for (key1, value) in summonerSpell_bin.items():
            for i in range(len(summonerSpell_header_keys)):
                key: str = summonerSpell_header_keys[i]
                to_append: Any = self.generate_spell_record(summonerSpell_data, key, key1, value)
                summonerSpell_data[key].append(to_append)
                summonerSpell_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        summonerSpell_statistics_output_order: list[int] = [0, 1, 11, 12, 261, 283, 284, 10, 13, 3, 4, 2, 16, 5, 6, 7, 17, 98, 113, 227, 229, 230, 62, 228, 39, 40, 41, 22, 32, 63, 44, 58, 59, 60, 21, 61, 64, 18, 19, 20, 23, 226, 24, 25, 231, 199, 119, 126, 127, 120, 53, 54, 55, 90, 121, 122, 35, 38, 200, 123, 124, 125, 92, 93, 42, 43, 46, 47, 48, 49, 45, 14, 15, 94, 99, 8, 9, 51, 31, 50, 52, 56, 57, 36, 37, 83, 75, 76, 86, 87, 67, 66, 72, 104, 69, 70, 71, 88, 91, 65, 68, 247, 78, 73, 74, 89, 81, 82, 77, 79, 80, 84, 102, 112, 85, 249, 250, 251, 100, 115, 114, 116, 118, 246, 232, 233, 234, 235, 236, 237, 238, 26, 27, 28, 29, 95, 245, 97, 111, 101, 210, 211, 103, 106, 105, 107, 110, 108, 109, 117, 128, 215, 96, 216, 218, 217, 221, 222, 225, 239, 243, 244, 248, 252, 254, 253, 321, 322, 255, 256, 257, 258, 273, 274, 262, 267, 299, 301, 300, 302, 270, 311, 313, 312, 314, 265, 293, 294, 266, 295, 297, 296, 298, 268, 303, 305, 304, 306, 269, 307, 309, 308, 310, 271, 315, 317, 316, 318, 272, 319, 320, 259, 275, 277, 276, 278, 260, 279, 281, 280, 282, 263, 285, 287, 286, 288, 264, 289, 291, 290, 292, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 213, 33, 30, 34, 333, 334, 336, 337, 348, 338, 339, 353, 354, 335, 349, 351, 350, 352, 341, 359, 361, 360, 362, 342, 363, 365, 364, 366, 340, 355, 356, 357, 358, 343, 344, 345, 346, 347, 201, 202, 203, 204, 205, 206, 207, 208, 209, 129, 177, 133, 131, 134, 135, 130, 132, 223, 224, 136, 137, 139, 140, 141, 142, 143, 144, 138, 145, 146, 147, 148, 149, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 175, 150, 176, 166, 167, 168, 169, 170, 171, 172, 173, 174, 178, 185, 179, 180, 181, 182, 183, 184, 195, 186, 187, 188, 189, 190, 191, 192, 193, 194, 196, 197, 198, 219, 220, 212, 214, 240, 241, 242, 367, 368, 369, 370, 371]
        summonerSpell_data_organized: dict[str, list[Any]] = {summonerSpell_header_keys[i]: summonerSpell_data_json[summonerSpell_header_keys[i]] for i in summonerSpell_statistics_output_order}
        summonerSpell_df: pandas.DataFrame = pandas.DataFrame(data = summonerSpell_data_organized)
        logPrint("正在优化召唤师技能数据框的逻辑值显示……\nOptimizing boolean value display of the summoner spell dataframe ...")
        optimize_bool_display(summonerSpell_df)
        summonerSpell_df = pandas.concat([pandas.DataFrame([summonerSpell_header])[summonerSpell_df.columns], summonerSpell_df], ignore_index = True)
        self.summonerSpell_df = summonerSpell_df
        return 0
    
    def enqueue_summonerSpell_dataframe(self) -> None:
        '''
        将召唤师技能数据框追加到数据提取器基类的数据框队列尾部。<br>Append summoner spell dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.summonerSpell_df.empty:
            summonerSpell_ws: dict[str, Any] = self.worksheet_metadata["SummonerSpell"]
            sheet1_name: str = summonerSpell_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else summonerSpell_ws["sheet_name_without_version"]
            summonerSpell_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(summonerSpell_ws["dType"]), "dType": summonerSpell_ws["dType"], "sheet_name": sheet1_name, "sheet": self.summonerSpell_df}
            self.enqueue_df(summonerSpell_df_struct, overwrite_on_exist = True, log = self.log)

    def export_summonerSpell_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出召唤师技能数据到工作簿中。产生以下工作表：<br>Export summoner spell data to a workbook. The following worksheets are added:
        - 召唤师技能（Summoner Spells）

        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 共享二进制描述文件的本地路径。<br>A local path of shared binary description file.
        
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
        if self.summonerSpell_df.empty:
            status: int = self.build_summonerSpell_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            summonerSpell_df: pandas.DataFrame = eliminate_empty_fields(self.summonerSpell_df)
        else:
            summonerSpell_df = self.summonerSpell_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["SummonerSpell"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["SummonerSpell"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(summonerSpell_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
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
                logPrint(f"召唤师技能数据已导出到{self.wbPath}。\nSummoner spell data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出召唤师技能数据到网页中。产生以下文件：<br>Export summoner spell data into an html file. The following file is produced:
        - 召唤师技能（Summoner spell）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 共享二进制描述文件的本地路径。<br>A local path of shared binary description file.
        
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
        if self.summonerSpell_df.empty:
            status: int = self.build_summonerSpell_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #召唤师技能（Summoner spell）
        if len(self.summonerSpell_df) > 1:
            summonerSpell_df_web: pandas.DataFrame = self.summonerSpell_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            imgIconUrls: list[str] = list(map(lambda x: "" if x == "" else "<br>".join(list(map(lambda y: self.url2image(self.assetPath2url(self.version, f"DATA/Spells/Icons2D/{y}" if not "/" in y else y)), eval(x)))), self.summonerSpell_df.loc[1:, "mSpell mImgIconName"].to_list()))
            summonerSpell_df_web.insert(len(summonerSpell_df_web.columns), "mSpell ImgIconUrl", ["缩略图网址列表"] + imgIconUrls)
            ##保留小数（Round）
            summonerSpell_df_web.loc[1:, "mSpell Cooldown {0a3e0478}"] = summonerSpell_df_web.loc[1:, "mSpell Cooldown {0a3e0478}"].apply(lambda x: "" if x == "" else self.aRound(x, 5))
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "ObjectName",
                "mSpell mPlatformSpellInfo mSpellID",
                "mSpell ImgIconUrl",
                "mSpell mPlatformSpellInfo mPlatformEnabled",
                "mSpell mClientData mTooltipData mLocKeys keyName_content_zh_burn",
                "mSpell mClientData mTooltipData mLocKeys keyName_content_en_burn",
                "mSpell Cooldown {0a3e0478}",
                "mSpell mClientData mTooltipData mLocKeys keySummary_content_zh",
                "mSpell mClientData mTooltipData mLocKeys keySummary_content_en",
                "mSpell mClientData mTooltipData mLocKeys keyTooltip_content_zh_burn",
                "mSpell mClientData mTooltipData mLocKeys keyTooltip_content_en_burn"
            ]
            summonerSpell_df_web = summonerSpell_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            summonerSpell_df_styled: pandas.io.formats.style.Styler = summonerSpell_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:7]
            summonerSpell_df_styled = summonerSpell_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            summonerSpell_htmltable: str = summonerSpell_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            summonerSpell_htmltable = '<meta charset="UTF-8">\n' + summonerSpell_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"SummonerSpell_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(summonerSpell_htmltable)
