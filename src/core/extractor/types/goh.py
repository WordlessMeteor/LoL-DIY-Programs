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
from src.core.config.headers import CherryGoH_header, KiwiGoH_header
from src.core.extractor.base import LoLDataExtractor

class GoHExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个荣誉嘉宾提取器对象。<br>Initial a GoHExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.GoH_ready: dict[str, bool] = {"map30": False, "cherry": False, "map12": False, "kiwi": False}
        self.CherryGoH_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiGoH_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.GoH_ready = {key: False for key in self.GoH_ready}
    
    def get_GoH_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取荣誉嘉宾二进制描述数据。<br>Get binary description data of Guests of Honor online.
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
        self.GoH_ready["map30"] = True
        #斗魂竞技场模式（Arena mode）
        cherry_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/cherry.bin.json"
        if cherry_bin_url in self.__class__.data_cache["online"]:
            self.cherry_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][cherry_bin_url]
        else:
            source, status, self.session = requestUrl("GET", cherry_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("斗魂竞技场模式专属信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nArena mode specific data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(cherry_bin_url))
                else:
                    logPrint('斗魂竞技场模式专属信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nArena mode specific data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                time.sleep(3)
                self.init_data_readiness()
                return
            self.cherry_bin = source.json()
            self.cherry_bin = self.resolve_bin_hash(self.cherry_bin)
            self.__class__.data_cache["online"][cherry_bin_url] = self.cherry_bin
        self.GoH_ready["cherry"] = True
        #嚎哭深渊地图（Howling Abyss map）
        map12_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map12/map12.bin.json"
        if map12_bin_url in self.__class__.data_cache["online"]:
            self.map12_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map12_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map12_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("嚎哭深渊地图信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nHowling Abyss map data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(map12_bin_url))
                    self.map12_bin = {}
                else:
                    logPrint("嚎哭深渊地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nHowling Abyss map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            self.map12_bin = source.json()
            self.map12_bin = self.resolve_bin_hash(self.map12_bin)
            self.__class__.data_cache["online"][map12_bin_url] = self.map12_bin
        self.GoH_ready["map12"] = True
        #海克斯大乱斗模式（ARAM: Mayhem mode）
        kiwi_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/kiwi.bin.json"
        if kiwi_bin_url in self.__class__.data_cache["online"]:
            self.kiwi_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][kiwi_bin_url]
        else:
            source, status, self.session = requestUrl("GET", kiwi_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("海克斯大乱斗模式专属信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nArena mode specific data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(kiwi_bin_url))
                    self.kiwi_bin = {}
                else:
                    logPrint('海克斯大乱斗模式专属信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nArena mode specific data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            self.kiwi_bin = source.json()
            self.kiwi_bin = self.resolve_bin_hash(self.kiwi_bin)
            self.__class__.data_cache["online"][kiwi_bin_url] = self.kiwi_bin
        self.GoH_ready["kiwi"] = True
    
    def read_GoH_data(self, paths: list[str]) -> None:
        '''
        离线获取荣誉嘉宾二进制描述数据。<br>Get binary description data of Guests of Honor offline.
        
        :param paths: 荣誉嘉宾二进制描述文件的本地路径列表，按照以下顺序排列。<br>A local path list of GoH binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 嚎哭深渊地图（Howling Abyss map）
            - 海克斯大乱斗模式专属信息（ARAM: Mayhem mode specific data）
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
        self.GoH_ready["map30"] = True
        #斗魂竞技场模式（Arena mode）
        cherry_bin_path: str = paths[1]
        if cherry_bin_path in self.__class__.data_cache["local"]:
            self.cherry_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][cherry_bin_path]
        else:
            with open(cherry_bin_path, "r", encoding = "utf-8") as fp:
                self.cherry_bin = json.load(fp)
            self.cherry_bin = self.resolve_bin_hash(self.cherry_bin)
            self.__class__.data_cache["local"][cherry_bin_path] = self.cherry_bin
        self.GoH_ready["cherry"] = True
        #嚎哭深渊地图（Howling Abyss map）
        map12_bin_path: str = paths[2]
        if map12_bin_path in self.__class__.data_cache["local"]:
            self.map12_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map12_bin_path]
        else:
            with open(map12_bin_path, "r", encoding = "utf-8") as fp:
                self.map12_bin = json.load(fp)
            self.map12_bin = self.resolve_bin_hash(self.map12_bin)
            self.__class__.data_cache["local"][map12_bin_path] = self.map12_bin
        self.GoH_ready["map12"] = True
        #海克斯大乱斗模式（ARAM: Mayhem mode）
        kiwi_bin_path: str = paths[3]
        if kiwi_bin_path in self.__class__.data_cache["local"]:
            self.kiwi_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][kiwi_bin_path]
        else:
            with open(kiwi_bin_path, "r", encoding = "utf-8") as fp:
                self.kiwi_bin = json.load(fp)
            self.kiwi_bin = self.resolve_bin_hash(self.kiwi_bin)
            self.__class__.data_cache["local"][kiwi_bin_path] = self.kiwi_bin
        self.GoH_ready["kiwi"] = True
    
    def build_GoH_dataframe(self, debug: bool = False, paths: Optional[list[str]] = None) -> int:
        '''
        构建荣誉嘉宾数据框。<br>Build GoH dataframe.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 荣誉嘉宾二进制描述文件的本地路径列表，按照以下顺序排列。<br>A local path list of GoH binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 嚎哭深渊地图（Howling Abyss map）
            - 海克斯大乱斗模式专属信息（ARAM: Mayhem mode specific data）
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not all(self.GoH_ready.values()):
            #获取荣誉嘉宾信息（Get GoH information）
            logPrint("正在读取荣誉嘉宾数据……\nReading GoH data ...", print_time = True)
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_GoH_data(paths = paths)
            else:
                self.get_GoH_data()
            if not all(self.GoH_ready.values()):
                logPrint("荣誉嘉宾数据尚未准备就绪！\nGoH data not prepared!")
                return 2
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建荣誉嘉宾数据框……\nBuilding the GoH dataframes ...", print_time = True)
        CherryGoH_header_keys: list[str] = list(CherryGoH_header.keys())
        CherryGoH_data: dict[str, list[Any]] = {key: [] for key in CherryGoH_header_keys}
        CherryGoH_data_json: dict[str, list[Any]] = copy.deepcopy(CherryGoH_data)
        KiwiGoH_header_keys: list[str] = list(KiwiGoH_header.keys())
        KiwiGoH_data: dict[str, list[Any]] = {key: [] for key in KiwiGoH_header_keys}
        KiwiGoH_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiGoH_data)
        
        #整理所有事件列表键（Sort out all event list keys）
        CherryEventList_keys: list[str] = [key for key in self.map30_bin if key != "__linked" and self.map30_bin[key]["__type"] == "GameModeEventList"]
        KiwiEventList_keys: list[str] = [key for key in self.map12_bin if key != "__linked" and self.map12_bin[key]["__type"] == "GameModeEventList"]
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        ##斗魂竞技场荣誉嘉宾（Arena Guest of Honor）
        for (key1, value) in self.map30_bin.items():
            if key1 != "__linked" and value["__type"] == "GuestOfHonorListData":
                for guest in value["{bae7ae53}"]:
                    GoHKey: str = guest["GuestOfHonor"]
                    if GoHKey in self.map30_bin:
                        guestData: dict[str, Any] = self.map30_bin[GoHKey]
                        guestName: str = guestData["name"]
                        for i in range(len(CherryGoH_header_keys)):
                            key: str = CherryGoH_header_keys[i]
                            if i <= 6: #怒火角斗场地图——荣誉嘉宾（Rings of Wrath: GuestOfHonor）
                                if i == 0: #嘉宾主键（`GoHKey`）
                                    to_append: Any = GoHKey
                                else:
                                    to_append = guestData.get(key, True if i == 3 else "")
                            elif i <= 23: #斗魂竞技场模式专属数据——{05c8aed6}（Arena mode specific data: {05c8aed6}）
                                if len(CherryEventList_keys) == 0:
                                    to_append = ""
                                else:
                                    for key2 in CherryEventList_keys:
                                        if key2 in self.map30_bin and "events" in self.map30_bin[key2] and f"Cherry_Event_{guestName}" in self.map30_bin[key2]["events"]:
                                            eventKey: str = self.map30_bin[key2]["events"][f"Cherry_Event_{guestName}"]["{40a56dcf}"]
                                            if eventKey in self.cherry_bin:
                                                eventData: dict[str, Any] = self.cherry_bin[eventKey]
                                                if i == 7: #事件主键（`eventKey`）
                                                    to_append: Any = eventKey
                                                elif i >= 8 and i <= 11: #字符串常量键子键（`{1ff99d7f}`'s subkeys）
                                                    to_append = eventData["{1ff99d7f}"][key.split()[1]]
                                                elif i == 12 or i == 13:
                                                    to_append = eventData[key]
                                                else:
                                                    subkey2: str = pStrConst.search(key).group()
                                                    subkey1: str = key.replace(subkey2, "")
                                                    useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                                    locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                                    tooltip_key: str = CherryGoH_data[subkey1][-1]
                                                    tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                                    if subkey2.endswith("_burn"):
                                                        # self.__class__.calculatedVariables.clear()
                                                        # tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, {}, locale, enableModeOverride = False, reserve_variable = self.reserve_variable)
                                                        tooltip_burn = self.tooltipPreparation(tooltip_raw, locale)
                                                        tooltip_burn = self.tooltipPostProcessing(tooltip_burn, locale)
                                                        to_append = tooltip_burn
                                                    else:
                                                        to_append = tooltip_raw
                                                break #找到匹配的事件键后就不再执行循环（Once the matching event key is found, break the loop）
                                    else:
                                        to_append = ""
                            else: #互斥荣誉嘉宾本地化名称（Localized subtitles of mutex guests）
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 24 else strtable_lol_default
                                if "{e7879fb5}" in guestData:
                                    mutexGoHNames: list[str] = []
                                    for GoH_key in self.map30_bin[GoHKey]["{e7879fb5}"]:
                                        if GoH_key in self.map30_bin:
                                            guest_name: str = self.map30_bin[GoH_key]["name"]
                                            for key2 in CherryEventList_keys:
                                                if key2 in self.map30_bin and "events" in self.map30_bin[key2] and f"Cherry_Event_{guestName}" in self.map30_bin[key2]["events"]:
                                                    event_key: str = self.map30_bin[key2]["events"][f"Cherry_Event_{guestName}"]["{40a56dcf}"]
                                                    if event_key in self.cherry_bin:
                                                        GoH_subtitle_key: str = self.cherry_bin[event_key]["{1ff99d7f}"]["Subtitle"]
                                                        GoH_subtitle: str = self.get_strtable_value(strtable_locale, GoH_subtitle_key, default = GoH_subtitle_key)
                                                        mutexGoHNames.append(GoH_subtitle)
                                                        break
                                            else:
                                                mutexGoHNames.append(guest_name)
                                        else:
                                            mutexGoHNames.append(GoH_key)
                                    to_append = mutexGoHNames
                                else:
                                    to_append = ""
                            CherryGoH_data[key].append(to_append)
                            CherryGoH_data_json[key].append(pyobj2json(to_append))
                    else:
                        for i in range(len(CherryGoH_header_keys)):
                            key: str = CherryGoH_header_keys[i]
                            to_append: Any = GoHKey if i == 0 else ""
                            CherryGoH_data[key].append(to_append)
                            CherryGoH_data_json[key].append(pyobj2json(to_append))
        CherryGoH_statistics_output_order: list[int] = [0, 7, 1, 2, 3, 5, 8, 14, 15, 9, 16, 17, 4, 10, 18, 19, 11, 20, 22, 21, 23, 6, 24, 25, 12, 13]
        CherryGoH_data_organized: dict[str, list[Any]] = {CherryGoH_header_keys[i]: CherryGoH_data_json[CherryGoH_header_keys[i]] for i in CherryGoH_statistics_output_order}
        CherryGoH_df: pandas.DataFrame = pandas.DataFrame(data = CherryGoH_data_organized)
        optimize_bool_display(CherryGoH_df)
        CherryGoH_df = pandas.concat([pandas.DataFrame([CherryGoH_header])[CherryGoH_df.columns], CherryGoH_df], ignore_index = True)
        self.CherryGoH_df = CherryGoH_df
        ##海克斯大乱斗乐队（Kiwi Band）
        for (key1, value) in self.map12_bin.items():
            if key1 != "__linked" and value["__type"] == "GuestOfHonorListData":
                for guest in value["{bae7ae53}"]:
                    GoHKey: str = guest["GuestOfHonor"]
                    if GoHKey in self.map12_bin:
                        bandData: dict[str, Any] = self.map12_bin[GoHKey]
                        bandName: str = bandData["name"]
                        for i in range(len(KiwiGoH_header_keys)):
                            key: str = KiwiGoH_header_keys[i]
                            if i <= 4: #嚎哭深渊地图——荣誉嘉宾（Howling Abyss: GuestOfHonor）
                                if i == 0: #嘉宾主键（`GoHKey`）
                                    to_append: Any = GoHKey
                                elif i <= 3:
                                    to_append = bandData[key]
                                else: #视觉特效资源映射字典（`ResourceResolver resourceMap`）
                                    if "VfxResourceResolver" in bandData and bandData["VfxResourceResolver"] in self.map12_bin and "resourceMap" in self.map12_bin[bandData["VfxResourceResolver"]]:
                                        to_append = self.map12_bin[bandData["VfxResourceResolver"]]["resourceMap"]
                                    else:
                                        to_append = ""
                            else: #海克斯大乱斗模式专属数据——{05c8aed6}（ARAM: Mayhem mode specific data: {05c8aed6}）
                                for key2 in KiwiEventList_keys:
                                    if key2 in self.map12_bin and "events" in self.map12_bin[key2] and bandName in self.map12_bin[key2]["events"]:
                                        eventKey: str = self.map12_bin[key2]["events"][bandName]["{40a56dcf}"]
                                        if eventKey in self.kiwi_bin:
                                            eventData: dict[str, Any] = self.kiwi_bin[eventKey]
                                            if i == 5: #事件主键（`eventKey`）
                                                to_append: Any = eventKey
                                            elif i >= 6 and i <= 9: #字符串常量键子键（`{1ff99d7f}`'s subkeys）
                                                to_append = eventData["{1ff99d7f}"][key.split()[1]]
                                            elif i == 10 or i == 11:
                                                to_append = eventData[key]
                                            else:
                                                subkey2: str = pStrConst.search(key).group()
                                                subkey1: str = key.replace(subkey2, "")
                                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                                locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                                tooltip_key: str = KiwiGoH_data[subkey1][-1]
                                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                                if subkey2.endswith("_burn"):
                                                    # self.__class__.calculatedVariables.clear()
                                                    # tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, {}, locale, enableModeOverride = False, reserve_variable = self.reserve_variable)
                                                    tooltip_burn = self.tooltipPreparation(tooltip_raw, locale)
                                                    tooltip_burn = self.tooltipPostProcessing(tooltip_burn, locale)
                                                    to_append = tooltip_burn
                                                else:
                                                    to_append = tooltip_raw
                                            break #找到匹配的事件键后就不再执行循环（Once the matching event key is found, break the loop）
                                else:
                                    to_append = ""
                            KiwiGoH_data[key].append(to_append)
                            KiwiGoH_data_json[key].append(pyobj2json(to_append))
                    else:
                        for i in range(len(KiwiGoH_header_keys)):
                            key: str = KiwiGoH_header_keys[i]
                            to_append: Any = GoHKey if i == 0 else ""
                            KiwiGoH_data[key].append(to_append)
                            KiwiGoH_data_json[key].append(pyobj2json(to_append))
        KiwiGoH_statistics_output_order: list[int] = [0, 5, 1, 2, 3, 6, 12, 13, 7, 14, 15, 8, 16, 17, 9, 18, 20, 19, 21, 10, 11, 4]
        KiwiGoH_data_organized: dict[str, list[Any]] = {KiwiGoH_header_keys[i]: KiwiGoH_data_json[KiwiGoH_header_keys[i]] for i in KiwiGoH_statistics_output_order}
        KiwiGoH_df: pandas.DataFrame = pandas.DataFrame(data = KiwiGoH_data_organized)
        optimize_bool_display(KiwiGoH_df)
        KiwiGoH_df = pandas.concat([pandas.DataFrame([KiwiGoH_header])[KiwiGoH_df.columns], KiwiGoH_df], ignore_index = True)
        self.KiwiGoH_df = KiwiGoH_df
        return 0
    
    def enqueue_GoH_dataframe(self) -> None:
        '''
        将荣誉嘉宾数据框追加到数据提取器基类的数据框队列尾部。<br>Append GoH dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.CherryGoH_df.empty:
            CherryGoH_ws: dict[str, Any] = self.worksheet_metadata["CherryGoH"]
            sheet1_name: str = CherryGoH_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else CherryGoH_ws["sheet_name_without_version"]
            CherryGoH_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(CherryGoH_ws["dType"]), "dType": CherryGoH_ws["dType"], "sheet_name": sheet1_name, "sheet": self.CherryGoH_df}
            self.enqueue_df(CherryGoH_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiGoH_df.empty:
            KiwiGoH_ws: dict[str, Any] = self.worksheet_metadata["KiwiGoH"]
            sheet2_name: str = KiwiGoH_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiGoH_ws["sheet_name_without_version"]
            KiwiGoH_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiGoH_ws["dType"]), "dType": KiwiGoH_ws["dType"], "sheet_name": sheet2_name, "sheet": self.KiwiGoH_df}
            self.enqueue_df(KiwiGoH_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_GoH_data(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出荣誉嘉宾数据到工作簿中。产生以下工作表：<br>Export GoH data to a workbook. The following worksheet is added:
        - 斗魂竞技场荣誉嘉宾（Cherry Guests）
        - 海克斯大乱斗乐队（Kiwi Band）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 荣誉嘉宾二进制描述文件的本地路径列表，按照以下顺序排列。<br>A local path list of GoH binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 嚎哭深渊地图（Howling Abyss map）
            - 海克斯大乱斗模式专属信息（ARAM: Mayhem mode specific data）
        
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
        if self.CherryGoH_df.empty: #海克斯大乱斗乐队未发布时，应当也能够正确导出荣誉嘉宾数据（GoH data should be exported properly when ARAM: Mayhem bands weren't released）
            status: int = self.build_GoH_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            CherryGoH_df: pandas.DataFrame = eliminate_empty_fields(self.CherryGoH_df)
            KiwiGoH_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiGoH_df)
        else:
            CherryGoH_df = self.CherryGoH_df
            KiwiGoH_df = self.KiwiGoH_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["CherryGoH"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryGoH"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["KiwiGoH"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiGoH"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(CherryGoH_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(KiwiGoH_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
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
                logPrint(f"荣誉嘉宾数据已导出到{self.wbPath}。\nGoH data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出荣誉嘉宾数据到网页中。产生以下文件：<br>Export GoH data into an html file. The following file is produced:
        - 斗魂竞技场荣誉嘉宾（Cherry Guests）
        - 海克斯大乱斗乐队（Kiwi Band）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 荣誉嘉宾二进制描述文件的本地路径列表，按照以下顺序排列。<br>A local path list of GoH binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 嚎哭深渊地图（Howling Abyss map）
            - 海克斯大乱斗模式专属信息（ARAM: Mayhem mode specific data）
        
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
        if self.CherryGoH_df.empty:
            status: int = self.build_GoH_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #斗魂竞技场荣誉嘉宾（Arena GoH）
        if len(self.CherryGoH_df) > 1:
            CherryGoH_df_web: pandas.DataFrame = self.CherryGoH_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            iconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.CherryGoH_df.loc[1:, "{982aa425}"].to_list()))
            CherryGoH_df_web.insert(len(CherryGoH_df_web.columns), "iconUrl", ["缩略图网址"] + iconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "name",
                "iconUrl",
                "Enabled",
                "{b0f32561}",
                "{1ff99d7f} title_content_zh",
                "{1ff99d7f} title_content_en",
                "{1ff99d7f} {bff2f361}_content_zh",
                "{1ff99d7f} {bff2f361}_content_en",
                "{1ff99d7f} {3b7aa707}_content_zh",
                "{1ff99d7f} {3b7aa707}_content_en",
            ]
            CherryGoH_df_web = CherryGoH_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            CherryGoH_df_styled: pandas.io.formats.style.Styler = CherryGoH_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:5]
            CherryGoH_df_styled = CherryGoH_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            CherryGoH_htmltable: str = CherryGoH_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            CherryGoH_htmltable = '<meta charset="UTF-8">\n' + CherryGoH_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"CherryGoH_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(CherryGoH_htmltable)
        #海克斯大乱斗乐队（Kiwi Band）
        if len(self.KiwiGoH_df) > 1:
            KiwiGoH_df_web: pandas.DataFrame = self.KiwiGoH_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            iconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.KiwiGoH_df.loc[1:, "{982aa425}"].to_list()))
            KiwiGoH_df_web.insert(len(KiwiGoH_df_web.columns), "iconUrl", ["缩略图网址"] + iconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "name",
                "iconUrl",
                "{b0f32561}",
                "{1ff99d7f} title_content_zh",
                "{1ff99d7f} title_content_en",
                "{1ff99d7f} {bff2f361}_content_zh",
                "{1ff99d7f} {bff2f361}_content_en",
                "{1ff99d7f} {3b7aa707}_content_zh",
                "{1ff99d7f} {3b7aa707}_content_en",
            ]
            KiwiGoH_df_web = KiwiGoH_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            KiwiGoH_df_styled: pandas.io.formats.style.Styler = KiwiGoH_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:5]
            KiwiGoH_df_styled = KiwiGoH_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            KiwiGoH_htmltable: str = KiwiGoH_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            KiwiGoH_htmltable = '<meta charset="UTF-8">\n' + KiwiGoH_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"KiwiBand_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(KiwiGoH_htmltable)
