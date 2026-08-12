import copy, json, os, pandas, re, sys, time
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
from src.core.config.headers import CherryAugment_header, SwarmAugment_header, KiwiAugment_header, KiwiAugmentSet_header, KiwiQuestline_header, KiwiJadeAugment_header, augmentModifier_header
from src.core.extractor.base import LoLDataExtractor

class AugmentExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个强化符文提取器对象。<br>Initialize a AugmentExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.augments_ready: dict[str, bool] = {"map30": False, "cherry": False, "map33": False, "map12": False, "kiwi": False, "kiwi_jade": False}
        self.CherryAugment_df: pandas.DataFrame = pandas.DataFrame()
        self.SwarmAugment_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiAugment_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiAugmentSet_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiQuestline_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiJadeAugment_df: pandas.DataFrame = pandas.DataFrame()
        self.augmentModifier_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.augments_ready = {key: False for key in self.augments_ready}
    
    def get_augment_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取强化符文二进制描述数据。包括以下游戏模式：<br>Get binary description data of augments online. Including the following game modes:
        - 斗魂竞技场（Arena）
        - 无尽狂潮（Swarm）
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
        self.augments_ready["map30"] = True
        #斗魂竞技场模式（Arena mode）
        cherry_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/cherry.bin.json"
        if cherry_bin_url in self.__class__.data_cache["online"]:
            self.cherry_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][cherry_bin_url]
        else:
            source, status, self.session = requestUrl("GET", cherry_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("斗魂竞技场强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nArena augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(cherry_bin_url))
                    self.cherry_bin = {}
                else:
                    logPrint('斗魂竞技场强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nArena augment data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.cherry_bin = source.json()
                self.cherry_bin = self.resolve_bin_hash(self.cherry_bin)
            self.__class__.data_cache["online"][cherry_bin_url] = self.cherry_bin
        self.augments_ready["cherry"] = True
        #最终都市地图（Final City map）
        map33_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map33/map33.bin.json"
        if map33_bin_url in self.__class__.data_cache["online"]:
            self.map33_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map33_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map33_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("最终都市地图信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nFinal City map data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(map33_bin_url))
                    self.map33_bin = {}
                else:
                    logPrint("最终都市地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nFinal City map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map33_bin = source.json()
                self.map33_bin = self.resolve_bin_hash(self.map33_bin)
            self.__class__.data_cache["online"][map33_bin_url] = self.map33_bin
        self.augments_ready["map33"] = True
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
            else:
                self.map12_bin = source.json()
                self.map12_bin = self.resolve_bin_hash(self.map12_bin)
            self.__class__.data_cache["online"][map12_bin_url] = self.map12_bin
        self.augments_ready["map12"] = True
        #海克斯大乱斗模式（ARAM: Mayhem mode）
        if Patch(self.patch_number) >= Patch("16.2.7366411"):
            kiwi_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/kiwi.bin.json"
        else:
            kiwi_bin_url = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/augments.bin.json"
        if kiwi_bin_url in self.__class__.data_cache["online"]:
            self.kiwi_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][kiwi_bin_url]
        else:
            source, status, self.session = requestUrl("GET", kiwi_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("海克斯大乱斗强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nARAM: Mayhem augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(kiwi_bin_url))
                    self.kiwi_bin = {}
                else:
                    logPrint('海克斯大乱斗强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nARAM: Mayhem augment data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.kiwi_bin = source.json()
                self.kiwi_bin = self.resolve_bin_hash(self.kiwi_bin)
            self.__class__.data_cache["online"][kiwi_bin_url] = self.kiwi_bin
        self.augments_ready["kiwi"] = True
        #海克斯大乱斗经典模式（ARAM: Mayhem Classic-ish mode）
        kiwi_jade_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/kiwi_jade.bin.json"
        if kiwi_jade_bin_url in self.__class__.data_cache["online"]:
            self.kiwi_jade_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][kiwi_jade_bin_url]
        else:
            source, status, self.session = requestUrl("GET", kiwi_jade_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("海克斯大乱斗经典模式强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nARAM: Mayhem Classic-ish mode augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(kiwi_jade_bin_url))
                    self.kiwi_jade_bin = {}
                else:
                    logPrint('海克斯大乱斗经典模式强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nARAM: Mayhem Classic-ish mode augment data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.')
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.kiwi_jade_bin = source.json()
                self.kiwi_jade_bin = self.resolve_bin_hash(self.kiwi_jade_bin)
            self.__class__.data_cache["online"][kiwi_jade_bin_url] = self.kiwi_jade_bin
        self.augments_ready["kiwi_jade"] = True
    
    def read_augment_data(self, paths: list[str]) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取强化符文二进制描述数据。<br>Get binary description data of augments offline.
        
        :param paths: 强化符文二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of augment binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 最终都市地图（Final City map）
            - 嚎哭深渊地图（Howling Abyss map）
            - 海克斯大乱斗模式专属信息（ARAM: Mayhem mode specific data）
            - 海克斯大乱斗经典模式专属信息（ARAM: Mayhem Classic-ish mode specific data）
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
        self.augments_ready["map30"] = True
        #斗魂竞技场模式（Arena mode）
        cherry_bin_path: str = paths[1]
        if cherry_bin_path in self.__class__.data_cache["local"]:
            self.cherry_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][cherry_bin_path]
        else:
            with open(cherry_bin_path, "r", encoding = "utf-8") as fp:
                self.cherry_bin = json.load(fp)
            self.cherry_bin = self.resolve_bin_hash(self.cherry_bin)
            self.__class__.data_cache["local"][cherry_bin_path] = self.cherry_bin
        self.augments_ready["cherry"] = True
        #最终都市地图（Final City map）
        map33_bin_path: str = paths[2]
        if map33_bin_path in self.__class__.data_cache["local"]:
            self.map33_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map33_bin_path]
        else:
            with open(map33_bin_path, "r", encoding = "utf-8") as fp:
                self.map33_bin = json.load(fp)
            self.map33_bin = self.resolve_bin_hash(self.map33_bin)
            self.__class__.data_cache["local"][map33_bin_path] = self.map33_bin
        self.augments_ready["map33"] = True
        #嚎哭深渊地图（Howling Abyss map）
        map12_bin_path: str = paths[3]
        if map12_bin_path in self.__class__.data_cache["local"]:
            self.map12_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map12_bin_path]
        else:
            with open(map12_bin_path, "r", encoding = "utf-8") as fp:
                self.map12_bin = json.load(fp)
            self.map12_bin = self.resolve_bin_hash(self.map12_bin)
            self.__class__.data_cache["local"][map12_bin_path] = self.map12_bin
        self.augments_ready["map12"] = True
        #海克斯大乱斗模式（ARAM: Mayhem mode）
        kiwi_bin_path: str = paths[4]
        if kiwi_bin_path in self.__class__.data_cache["local"]:
            self.kiwi_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][kiwi_bin_path]
        else:
            with open(kiwi_bin_path, "r", encoding = "utf-8") as fp:
                self.kiwi_bin = json.load(fp)
            self.kiwi_bin = self.resolve_bin_hash(self.kiwi_bin)
            self.__class__.data_cache["local"][kiwi_bin_path] = self.kiwi_bin
        self.augments_ready["kiwi"] = True
        #海克斯大乱斗经典模式（ARAM: Mayhem Classic-ish mode）
        kiwi_jade_bin_path: str = paths[5]
        if kiwi_jade_bin_path in self.__class__.data_cache["local"]:
            self.kiwi_jade_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][kiwi_jade_bin_path]
        else:
            with open(kiwi_jade_bin_path, "r", encoding = "utf-8") as fp:
                self.kiwi_jade_bin = json.load(fp)
            self.kiwi_jade_bin = self.resolve_bin_hash(self.kiwi_jade_bin)
            self.__class__.data_cache["local"][kiwi_jade_bin_path] = self.kiwi_jade_bin
        self.augments_ready["kiwi_jade"] = True
    
    def build_augment_dataframe(self, debug: bool = False, paths: Optional[list[str]] = None) -> int:
        '''
        构建强化符文数据框。<br>Build augment dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 强化符文二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of augment binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 最终都市地图（Final City map）
            - 嚎哭深渊地图（Howling Abyss map）
            - 海克斯大乱斗模式专属信息（ARAM: Mayhem mode specific data）
            - 海克斯大乱斗经典模式专属信息（ARAM: Mayhem Classic-ish mode specific data）
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.augments_ready["map30"]:
            #获取强化符文信息（Get augment information）
            logPrint("正在读取强化符文数据……\nReading augment data ...", print_time = True)
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_augment_data(paths = paths)
            else:
                self.get_augment_data()
            if not self.augments_ready["map30"]:
                logPrint("强化符文数据尚未准备就绪！\nAugment data not prepared!")
                return 2
        #检验海克斯大乱斗不同数据的异质性（Verify the heterogeneity of different data in ARAM: Mayhem mode）
        # bin_list: list[dict[str, list[str] | dict[str, Any]]] = [self.map12_bin, self.kiwi_bin]
        # overlay_table, overlay_count_table, overlay_identical_table, overlay_difference_table, overlay_diffCount_table = verifyDictHeterogeneity(bin_list)
        #经过检验，`overlay_count_table`中所有单元格的值都是True，所以可以放心合并这些二进制描述数据（After verification, all cells in `overlay_count_table` are True, so these binary description data can be merged safely）
        #合并数据（Merge data）
        map12_bin_whole: dict[str, list[str] | dict[str, Any]] = self.map12_bin | self.kiwi_bin #合并海克斯大乱斗模式的强化符文数据（Merge the augment data in ARAM: Mayhem mode）
        map30_bin_whole: dict[str, list[str] | dict[str, Any]] = self.map30_bin | self.cherry_bin #合并斗魂竞技场模式的强化符文数据（Merge the augment data in Arena mode）
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建强化符文数据框……\nBuilding the augment dataframes ...", print_time = True)
        CherryAugment_header_keys: list[str] = list(CherryAugment_header.keys())
        CherryAugment_data: dict[str, list[Any]] = {key: [] for key in CherryAugment_header_keys}
        CherryAugment_data_json: dict[str, list[Any]] = copy.deepcopy(CherryAugment_data)
        SwarmAugment_header_keys: list[str] = list(SwarmAugment_header.keys())
        SwarmAugment_data: dict[str, list[Any]] = {key: [] for key in SwarmAugment_header_keys}
        SwarmAugment_data_json: dict[str, list[Any]] = copy.deepcopy(SwarmAugment_data)
        KiwiAugment_header_keys: list[str] = list(KiwiAugment_header.keys())
        KiwiAugment_data: dict[str, list[Any]] = {key: [] for key in KiwiAugment_header_keys}
        KiwiAugment_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiAugment_data)
        KiwiAugmentSet_header_keys: list[str] = list(KiwiAugmentSet_header.keys())
        KiwiAugmentSet_data: dict[str, list[Any]] = {key: [] for key in KiwiAugmentSet_header_keys}
        KiwiAugmentSet_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiAugmentSet_data)
        KiwiQuestline_header_keys: list[str] = list(KiwiQuestline_header.keys())
        KiwiQuestline_data: dict[str, list[Any]] = {key: [] for key in KiwiQuestline_header_keys}
        KiwiQuestline_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiQuestline_data)
        KiwiJadeAugment_header_keys: list[str] = list(KiwiJadeAugment_header.keys())
        KiwiJadeAugment_data: dict[str, list[Any]] = {key: [] for key in KiwiJadeAugment_header_keys}
        KiwiJadeAugment_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiJadeAugment_data)
        augmentModifier_header_keys: list[str] = list(augmentModifier_header.keys())
        augmentModifier_data: dict[str, list[Any]] = {key: [] for key in augmentModifier_header_keys}
        augmentModifier_data_json: dict[str, list[Any]] = copy.deepcopy(augmentModifier_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        ##斗魂竞技场强化符文（Arena augments）
        self.init_mSpells()
        for (key, value) in map30_bin_whole.items(): #提取指令字典（Extract spell dictionary）
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        for (key1, value) in map30_bin_whole.items():
            if key1 != "__linked" and value["__type"] == "AugmentData":
                for i in range(len(CherryAugment_header_keys)):
                    key: str = CherryAugment_header_keys[i]
                    to_append: Any = self.generate_augment_record(map30_bin_whole, CherryAugment_data, key, key1, value)
                    CherryAugment_data[key].append(to_append)
                    CherryAugment_data_json[key].append(pyobj2json(to_append))
        CherryAugment_statistics_output_order: list[int] = [0, 1, 20, 2, 3, 24, 25, 18, 51, 16, 54, 17, 50, 8, 9, 19, 4, 26, 27, 28, 29, 5, 30, 31, 32, 33, 10, 34, 35, 36, 37, 11, 38, 39, 40, 41, 12, 42, 43, 44, 45, 13, 46, 47, 48, 49, 6, 52, 14, 15]
        CherryAugment_data_organized: dict[str, list[Any]] = {CherryAugment_header_keys[i]: CherryAugment_data_json[CherryAugment_header_keys[i]] for i in CherryAugment_statistics_output_order}
        CherryAugment_df: pandas.DataFrame = pandas.DataFrame(data = CherryAugment_data_organized)
        CherryAugment_df = CherryAugment_df.sort_values(by = "AugmentPlatformId", ascending = True, ignore_index = True)
        logPrint("正在优化斗魂竞技场强化符文数据框的逻辑值显示……\nOptimizing boolean value display of the Cherry augment dataframe ...")
        optimize_bool_display(CherryAugment_df)
        CherryAugment_df = pandas.concat([pandas.DataFrame([CherryAugment_header])[CherryAugment_df.columns], CherryAugment_df], ignore_index = True)
        self.CherryAugment_df = CherryAugment_df
        ##无尽狂潮强化（Swarm augments）
        self.init_mSpells()
        for (key, value) in self.map33_bin.items(): #提取指令字典（Extract spell dictionary）
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        for (key1, value) in self.map33_bin.items():
            if key1 != "__linked" and value["__type"] == "AugmentData":
                for i in range(len(SwarmAugment_header_keys)):
                    key: str = SwarmAugment_header_keys[i]
                    to_append: Any = self.generate_augment_record(self.map33_bin, SwarmAugment_data, key, key1, value)
                    SwarmAugment_data[key].append(to_append)
                    SwarmAugment_data_json[key].append(pyobj2json(to_append))
        SwarmAugment_statistics_output_order: list[int] = [0, 1, 20, 3, 24, 25, 18, 51, 9, 4, 26, 27, 28, 29, 5, 30, 31, 32, 33, 6, 52, 14, 15]
        SwarmAugment_data_organized: dict[str, list[Any]] = {SwarmAugment_header_keys[i]: SwarmAugment_data_json[SwarmAugment_header_keys[i]] for i in SwarmAugment_statistics_output_order}
        SwarmAugment_df: pandas.DataFrame = pandas.DataFrame(data = SwarmAugment_data_organized)
        SwarmAugment_df = SwarmAugment_df.sort_values(by = "AugmentPlatformId", ascending = True, ignore_index = True)
        logPrint("正在优化无尽狂潮强化数据框的逻辑值显示……\nOptimizing boolean value display of the Swarm augment dataframe ...")
        optimize_bool_display(SwarmAugment_df)
        SwarmAugment_df = pandas.concat([pandas.DataFrame([SwarmAugment_header])[SwarmAugment_df.columns], SwarmAugment_df], ignore_index = True)
        self.SwarmAugment_df = SwarmAugment_df
        ##海克斯大乱斗强化符文（ARAM: Mayhem augments）
        self.init_mSpells()
        augmentSet_map: dict[str, list[str]] = {}
        augmentKey_questline_map: dict[str, str] = {}
        for (key, value) in map12_bin_whole.items():
            if key != "__linked":
                if value["__type"] == "SpellObject": #提取指令字典（Extract spell dictionary）
                    self.__class__.mSpells[value["mScriptName"]] = value
                elif value["__type"] == "AugmentData": #整理从任务线到强化符文的映射（Build a map from questline to the corresponding augment）
                    if "{3ed971bd}" in value and "{09d0cf3d}" in value["{3ed971bd}"]:
                        augmentKey_questline_map[value["{3ed971bd}"]["{09d0cf3d}"]] = key
                elif value["__type"] == "{27bc6378}": #整理从强化符文到强化符文套装的映射（Build a map from augment to its belonging sets）
                    for augment_key in value["augments"]:
                        if not augment_key in augmentSet_map:
                            augmentSet_map[augment_key] = []
                        augmentSet_map[augment_key].append(key)
        for (key1, value) in map12_bin_whole.items():
            if key1 != "__linked" and value["__type"] == "AugmentData": #强化符文（Augment）
                for i in range(len(KiwiAugment_header_keys)):
                    key: str = KiwiAugment_header_keys[i]
                    if i == 0: #存在于经典模式版（`isClassic`）
                        to_append = key1 in self.kiwi_jade_bin
                    elif i <= 3: #强化符文套装相关键（Augment set related keys）
                        if key1 in augmentSet_map:
                            if i == 0: #强化符文套装列表（`augmentSet`）
                                to_append = augmentSet_map[key1]
                            else: #强化符文套装本地化名称（Augment set localized names）
                                augmentSets: list[str] = augmentSet_map[key1]
                                augmentSetNames: list[str] = []
                                for augmentSet_key in augmentSets:
                                    tooltip_key = map12_bin_whole[augmentSet_key]["{0746ade9}"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 2 else strtable_lol_default
                                    augmentSetNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                to_append = augmentSetNames
                        else:
                            to_append = ""
                    else:
                        to_append = self.generate_augment_record(map12_bin_whole, KiwiAugment_data, key, key1, value)
                    KiwiAugment_data[key].append(to_append)
                    KiwiAugment_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{27bc6378}": #强化符文套装（Augment set）
                for i in range(len(KiwiAugmentSet_header_keys)):
                    key: str = KiwiAugmentSet_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 9:
                        to_append = value.get(key, "")
                    elif i <= 15: #强化符文套装名称和套装描述本地化文本（Augment set name and description localized text）
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = KiwiAugmentSet_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            spellKey: str = value["{96b4b430}"]
                            if spellKey in map12_bin_whole:
                                mSpell: Optional[dict[str, Any]] = map12_bin_whole[spellKey]["mSpell"]
                            else:
                                mSpell: Optional[dict[str, Any]] = None
                            if mSpell == None:
                                to_append = ""
                            else:
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    elif i == 16 or i == 17: #强化符文列表本地化信息（Augment list localized text）
                        augmentNames: list[str] = []
                        for augment_key in value["augments"]:
                            if augment_key in map12_bin_whole:
                                tooltip_key = map12_bin_whole[augment_key]["NameTra"]
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 16 else strtable_lol_default
                                augmentNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                            else:
                                augmentNames.append("")
                        to_append = augmentNames
                    elif i <= 23: #根指令对象（`{96b4b430}_object`）
                        rootSpell_key: str = value["{96b4b430}"]
                        if rootSpell_key in map12_bin_whole:
                            rootSpell = map12_bin_whole[rootSpell_key]
                            if i == 18: #根指令对象（`{96b4b430}_object`）
                                to_append = rootSpell
                            elif i == 19: #套装说明文本键（`{96b4b430}_object keyTooltip`）
                                tmp_ptr = rootSpell
                                subkeyList: list[str] = ["mSpell", "mClientData", "mTooltipData", "mLocKeys", "keyTooltip"]
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
                                locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                tooltip_key: str = KiwiAugmentSet_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                if subkey2.endswith("_burn"):
                                    mSpell = rootSpell["mSpell"]
                                    self.__class__.calculatedVariables.clear()
                                    tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                    to_append = tooltip_burn
                                else:
                                    to_append = tooltip_raw
                        else:
                            to_append = ""
                    elif i == 24: #其它指令对象（`{40c7b66f}_Object`）
                        to_append = list(map(lambda x: map12_bin_whole.get(x, ""), value.get("{40c7b66f}", [])))
                        if to_append == []:
                            to_append = ""
                    else: #资源解析器映射字典（`{01d14504} resourceMap`）
                        if "{01d14504}" in value and "resourceMap" in map12_bin_whole[value["{01d14504}"]]:
                            to_append = map12_bin_whole[value["{01d14504}"]]["resourceMap"]
                        else:
                            to_append = ""
                    KiwiAugmentSet_data[key].append(to_append)
                    KiwiAugmentSet_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{8d31b69b}": #任务线（Questline）
                milestones: list[dict[str, Any]] = value["Milestones"]
                for milestone_index in range(len(milestones)):
                    milestone: dict[str, Any] = milestones[milestone_index]
                    #下面设置一些用于说明文本转换的变量（Prepare some preset variables used for tooltip transformation）
                    current_questPoint: int = milestone["{7fec0982}"]
                    previous_questPoint: int = 0 if milestone_index == 0 else milestones[milestone_index - 1]["{7fec0982}"]
                    questPoint_diff: int = current_questPoint - previous_questPoint
                    reservedVars: Optional[dict[str, str]] = {"QuestRequirement": str(questPoint_diff), "QuestTier": str(milestone_index)}
                    for i in range(len(KiwiQuestline_header_keys)):
                        key: str = KiwiQuestline_header_keys[i]
                        if i <= 14:
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i <= 8:
                                tmp_ptr: Any = value
                                subkeyList: list[str] = key.split()
                                for tmp_key in subkeyList:
                                    if tmp_key in tmp_ptr:
                                        tmp_ptr = tmp_ptr[tmp_key]
                                    else:
                                        if i == 6 or i == 8:
                                            to_append = value.get(key, False)
                                        else:
                                            to_append = value.get(key, "")
                                        break
                                else:
                                    to_append = tmp_ptr
                            else:
                                subkey2: str = pStrConst.search(key).group()
                                subkey1: str = key.replace(subkey2, "")
                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                tooltip_key: str = KiwiQuestline_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                if subkey2.endswith("_burn"):
                                    if key1 in augmentKey_questline_map:
                                        spellKey: str = map12_bin_whole[augmentKey_questline_map[key1]]["RootSpell"]
                                        mSpell: dict[str, Any] = map12_bin_whole[spellKey]["mSpell"]
                                    else:
                                        mSpell = {}
                                    self.__class__.calculatedVariables.clear()
                                    tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, reservedVars = reservedVars, flexibleData = {"mStat_dict_override_version": self.version})
                                    to_append = tooltip_burn
                                else:
                                    to_append = tooltip_raw
                        elif i <= 21:
                            if i == 15: #里程序号（`Milestone_index`）
                                to_append = milestone_index
                            elif i <= 17:
                                to_append = milestone[key.split()[1]]
                            else:
                                subkey2: str = pStrConst.search(key).group()
                                subkey1: str = key.replace(subkey2, "")
                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                tooltip_key: str = KiwiQuestline_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                if subkey2.endswith("_burn"):
                                    if key1 in augmentKey_questline_map:
                                        spellKey: str = map12_bin_whole[augmentKey_questline_map[key1]]["RootSpell"]
                                        mSpell: dict[str, Any] = map12_bin_whole[spellKey]["mSpell"]
                                    else:
                                        mSpell = {}
                                    self.__class__.calculatedVariables.clear()
                                    tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, reservedVars = reservedVars, flexibleData = {"mStat_dict_override_version": self.version})
                                    to_append = tooltip_burn
                                else:
                                    to_append = tooltip_raw
                        else:
                            if key1 in augmentKey_questline_map:
                                to_append = map12_bin_whole[augmentKey_questline_map[key1]]["AugmentPlatformId"]
                            else:
                                to_append = 0
                        KiwiQuestline_data[key].append(to_append)
                        KiwiQuestline_data_json[key].append(pyobj2json(to_append))
        KiwiAugment_statistics_output_order: list[int] = [4, 5, 24, 6, 7, 28, 29, 0, 22, 55, 21, 54, 1, 2, 3, 60, 61, 12, 13, 23, 26, 65, 68, 8, 30, 31, 32, 33, 9, 34, 35, 36, 37, 14, 38, 39, 40, 41, 15, 42, 43, 44, 45, 63, 71, 72, 73, 74, 10, 56, 11, 57, 25, 67, 27, 59, 18, 19, 64]
        KiwiAugment_data_organized: dict[str, list[Any]] = {KiwiAugment_header_keys[i]: KiwiAugment_data_json[KiwiAugment_header_keys[i]] for i in KiwiAugment_statistics_output_order}
        KiwiAugment_df: pandas.DataFrame = pandas.DataFrame(data = KiwiAugment_data_organized)
        KiwiAugment_df = KiwiAugment_df.sort_values(by = "AugmentPlatformId", ascending = True, ignore_index = True)
        logPrint("正在优化海克斯大乱斗强化符文数据框的逻辑值显示……\nOptimizing boolean value display of the ARAM: Mayhem augment dataframe ...")
        optimize_bool_display(KiwiAugment_df)
        KiwiAugment_df = pandas.concat([pandas.DataFrame([KiwiAugment_header])[KiwiAugment_df.columns], KiwiAugment_df], ignore_index = True)
        self.KiwiAugment_df = KiwiAugment_df
        KiwiAugmentSet_statistics_output_order: list[int] = [0, 1, 3, 10, 11, 4, 12, 13, 14, 15, 19, 20, 21, 22, 23, 5, 16, 17, 6, 18, 9, 24, 7, 25, 8, 2]
        KiwiAugmentSet_data_organized: dict[str, list[Any]] = {KiwiAugmentSet_header_keys[i]: KiwiAugmentSet_data_json[KiwiAugmentSet_header_keys[i]] for i in KiwiAugmentSet_statistics_output_order}
        KiwiAugmentSet_df: pandas.DataFrame = pandas.DataFrame(data = KiwiAugmentSet_data_organized)
        KiwiAugmentSet_df = pandas.concat([pandas.DataFrame([KiwiAugmentSet_header])[KiwiAugmentSet_df.columns], KiwiAugmentSet_df], ignore_index = True)
        self.KiwiAugmentSet_df = KiwiAugmentSet_df
        KiwiQuestline_statistics_output_order: list[int] = [0, 22, 2, 3, 9, 10, 15, 16, 17, 18, 19, 20, 21]
        KiwiQuestline_data_organized: dict[str, list[Any]] = {KiwiQuestline_header_keys[i]: KiwiQuestline_data_json[KiwiQuestline_header_keys[i]] for i in KiwiQuestline_statistics_output_order}
        KiwiQuestline_df: pandas.DataFrame = pandas.DataFrame(data = KiwiQuestline_data_organized)
        KiwiQuestline_df = KiwiQuestline_df.sort_values(by = ["augment AugmentPlatformId", "Milestone_index"], ascending = True, ignore_index = True)
        KiwiQuestline_df = pandas.concat([pandas.DataFrame([KiwiQuestline_header])[KiwiQuestline_df.columns], KiwiQuestline_df], ignore_index = True)
        self.KiwiQuestline_df = KiwiQuestline_df
        ##海克斯大乱斗经典模式版强化符文（ARAM: Mayhem Classic-ish augments）
        self.init_mSpells()
        for (key, value) in self.kiwi_jade_bin.items():
            if key != "__linked":
                if value["__type"] == "SpellObject": #提取指令字典（Extract spell dictionary）
                    self.__class__.mSpells[value["mScriptName"]] = value
        for (key1, value) in self.kiwi_jade_bin.items():
            if key1 != "__linked" and value["__type"] == "AugmentData":
                for i in range(len(KiwiJadeAugment_header_keys)):
                    key: str = KiwiJadeAugment_header_keys[i]
                    if i == 0: #存在于现代版（`isCurrent`）
                        to_append = key1 in map12_bin_whole
                    else:
                        to_append = self.generate_augment_record(self.kiwi_jade_bin, KiwiJadeAugment_data, key, key1, value)
                    KiwiJadeAugment_data[key].append(to_append)
                    KiwiJadeAugment_data_json[key].append(pyobj2json(to_append))
        KiwiJadeAugment_statistics_output_order: list[int] = [1, 2, 21, 3, 4, 25, 26, 0, 19, 52, 18, 51, 57, 58, 9, 10, 20, 23, 62, 65, 5, 27, 28, 29, 30, 6, 31, 32, 33, 34, 11, 35, 36, 37, 38, 12, 39, 40, 41, 42, 60, 68, 69, 70, 71, 7, 53, 8, 54, 22, 64, 24, 56, 15, 16, 61]
        KiwiJadeAugment_data_organized: dict[str, list[Any]] = {KiwiJadeAugment_header_keys[i]: KiwiJadeAugment_data_json[KiwiJadeAugment_header_keys[i]] for i in KiwiJadeAugment_statistics_output_order}
        KiwiJadeAugment_df: pandas.DataFrame = pandas.DataFrame(data = KiwiJadeAugment_data_organized)
        KiwiJadeAugment_df = KiwiJadeAugment_df.sort_values(by = "AugmentPlatformId", ascending = True, ignore_index = True)
        logPrint("正在优化海克斯大乱斗经典模式版强化符文数据框的逻辑值显示……\nOptimizing boolean value display of the ARAM: Mayhem Classic-ish augment dataframe ...")
        optimize_bool_display(KiwiJadeAugment_df)
        KiwiJadeAugment_df = pandas.concat([pandas.DataFrame([KiwiJadeAugment_header])[KiwiJadeAugment_df.columns], KiwiJadeAugment_df], ignore_index = True)
        self.KiwiJadeAugment_df = KiwiJadeAugment_df
        ##强化符文修饰（Augment modifiers）
        for (key1, value) in (self.map12_bin | self.map30_bin).items():
            if key1 != "__linked" and value["__type"] == "{23433cc1}":
                for i in range(len(augmentModifier_header_keys)):
                    key: str = augmentModifier_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append = key1
                    elif i == 1: #所属地图序号（`belonging_mapIds`）
                        belonging_mapIds: list[int] = []
                        if key1 in self.map12_bin:
                            belonging_mapIds.append(12)
                        if key1 in self.map30_bin:
                            belonging_mapIds.append(30)
                        to_append = belonging_mapIds
                    elif i <= 7:
                        to_append = value.get(key, "")
                    else:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = augmentModifier_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            tooltip_burn = self.tooltipPreparation(tooltip_raw, locale)
                            tooltip_burn = self.tooltipPostProcessing(tooltip_burn, locale)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    augmentModifier_data[key].append(to_append)
                    augmentModifier_data_json[key].append(pyobj2json(to_append))
        augmentModifier_statistics_output_order: list[int] = [0, 2, 1, 3, 5, 4, 8, 9, 10, 11, 6, 12, 13, 14, 15, 7]
        augmentModifier_data_organized: dict[str, list[Any]] = {augmentModifier_header_keys[i]: augmentModifier_data_json[augmentModifier_header_keys[i]] for i in augmentModifier_statistics_output_order}
        augmentModifier_df: pandas.DataFrame = pandas.DataFrame(data = augmentModifier_data_organized)
        augmentModifier_df = pandas.concat([pandas.DataFrame([augmentModifier_header])[augmentModifier_df.columns], augmentModifier_df], ignore_index = True)
        self.augmentModifier_df = augmentModifier_df
        return 0
    
    def enqueue_augment_dataframe(self) -> None:
        '''
        将强化符文数据框追加到数据提取器基类的数据框队列尾部。<br>Append augment dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.CherryAugment_df.empty:
            CherryAugment_ws: dict[str, Any] = self.worksheet_metadata["CherryAugment"]
            sheet1_name: str = CherryAugment_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else CherryAugment_ws["sheet_name_without_version"]
            CherryAugment_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(CherryAugment_ws["dType"]), "dType": CherryAugment_ws["dType"], "sheet_name": sheet1_name, "sheet": self.CherryAugment_df}
            self.enqueue_df(CherryAugment_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.SwarmAugment_df.empty:
            SwarmAugment_ws: dict[str, Any] = self.worksheet_metadata["SwarmAugment"]
            sheet2_name: str = SwarmAugment_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else SwarmAugment_ws["sheet_name_without_version"]
            SwarmAugment_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(SwarmAugment_ws["dType"]), "dType": SwarmAugment_ws["dType"], "sheet_name": sheet2_name, "sheet": self.SwarmAugment_df}
            self.enqueue_df(SwarmAugment_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiAugment_df.empty:
            KiwiAugment_ws: dict[str, Any] = self.worksheet_metadata["KiwiAugment"]
            sheet3_name: str = KiwiAugment_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiAugment_ws["sheet_name_without_version"]
            KiwiAugment_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiAugment_ws["dType"]), "dType": KiwiAugment_ws["dType"], "sheet_name": sheet3_name, "sheet": self.KiwiAugment_df}
            self.enqueue_df(KiwiAugment_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiAugmentSet_df.empty:
            KiwiAugmentSet_ws: dict[str, Any] = self.worksheet_metadata["KiwiAugmentSet"]
            sheet4_name: str = KiwiAugmentSet_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiAugmentSet_ws["sheet_name_without_version"]
            KiwiAugmentSet_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiAugmentSet_ws["dType"]), "dType": KiwiAugmentSet_ws["dType"], "sheet_name": sheet4_name, "sheet": self.KiwiAugmentSet_df}
            self.enqueue_df(KiwiAugmentSet_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiQuestline_df.empty:
            KiwiQuestline_ws: dict[str, Any] = self.worksheet_metadata["KiwiQuestline"]
            sheet5_name: str = KiwiQuestline_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiQuestline_ws["sheet_name_without_version"]
            KiwiQuestline_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiQuestline_ws["dType"]), "dType": KiwiQuestline_ws["dType"], "sheet_name": sheet5_name, "sheet": self.KiwiQuestline_df}
            self.enqueue_df(KiwiQuestline_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiJadeAugment_df.empty:
            KiwiJadeAugment_ws: dict[str, Any] = self.worksheet_metadata["KiwiJadeAugment"]
            sheet6_name: str = KiwiJadeAugment_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiJadeAugment_ws["sheet_name_without_version"]
            KiwiJadeAugment_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiJadeAugment_ws["dType"]), "dType": KiwiJadeAugment_ws["dType"], "sheet_name": sheet6_name, "sheet": self.KiwiJadeAugment_df}
            self.enqueue_df(KiwiJadeAugment_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.augmentModifier_df.empty:
            augmentModifier_ws: dict[str, Any] = self.worksheet_metadata["AugmentModifier"]
            sheet7_name: str = augmentModifier_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else augmentModifier_ws["sheet_name_without_version"]
            augmentModifier_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(augmentModifier_ws["dType"]), "dType": augmentModifier_ws["dType"], "sheet_name": sheet7_name, "sheet": self.augmentModifier_df}
            self.enqueue_df(augmentModifier_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_augment_data(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出强化符文数据到工作簿中。产生以下工作表：<br>Export augment data to a workbook. The following worksheets are added:
        - 斗魂竞技场强化符文（Cherry Augments）
        - 无尽狂潮强化符文（Swarm Augments）
        - 海克斯大乱斗强化符文（Kiwi Augments）
        - 海克斯大乱斗强化符文套装（Kiwi Augment Set）
        - 海克斯大乱斗任务线（Kiwi Questlines）
        - 海克斯大乱斗经典模式版强化符文（KiwiJade Augments）
        - 强化符文修饰（Augment Modifiers）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 强化符文二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of augment binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 最终都市地图（Final City map）
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
        if self.CherryAugment_df.empty: #无尽狂潮和海克斯大乱斗未发布时，应当也能够正确导出强化符文数据（Augment data should be exported properly when Swarm and ARAM: Mayhem weren't released）
            status: int = self.build_augment_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            CherryAugment_df: pandas.DataFrame = eliminate_empty_fields(self.CherryAugment_df)
            SwarmAugment_df: pandas.DataFrame = eliminate_empty_fields(self.SwarmAugment_df)
            KiwiAugment_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiAugment_df)
            KiwiAugmentSet_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiAugmentSet_df)
            KiwiQuestline_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiQuestline_df)
            KiwiJadeAugment_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiJadeAugment_df)
            augmentModifier_df: pandas.DataFrame = eliminate_empty_fields(self.augmentModifier_df)
        else:
            CherryAugment_df = self.CherryAugment_df
            SwarmAugment_df = self.SwarmAugment_df
            KiwiAugment_df = self.KiwiAugment_df
            KiwiAugmentSet_df = self.KiwiAugmentSet_df
            KiwiQuestline_df = self.KiwiQuestline_df
            KiwiJadeAugment_df = self.KiwiJadeAugment_df
            augmentModifier_df = self.augmentModifier_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["CherryAugment"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["CherryAugment"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["SwarmAugment"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["SwarmAugment"]["sheet_name_without_version"]
        sheet3_name: str = self.worksheet_metadata["KiwiAugment"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiAugment"]["sheet_name_without_version"]
        sheet4_name: str = self.worksheet_metadata["KiwiAugmentSet"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiAugmentSet"]["sheet_name_without_version"]
        sheet5_name: str = self.worksheet_metadata["KiwiQuestline"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiQuestline"]["sheet_name_without_version"]
        sheet6_name: str = self.worksheet_metadata["KiwiJadeAugment"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiJadeAugment"]["sheet_name_without_version"]
        sheet7_name: str = self.worksheet_metadata["AugmentModifier"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["AugmentModifier"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(CherryAugment_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    if not SwarmAugment_df.empty:
                        addDefaultStyle(SwarmAugment_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    if not KiwiAugment_df.empty:
                        addDefaultStyle(KiwiAugment_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    if not KiwiAugmentSet_df.empty:
                        addDefaultStyle(KiwiAugmentSet_df).to_excel(excel_writer = writer, sheet_name = sheet4_name)
                    if not KiwiQuestline_df.empty:
                        addDefaultStyle(KiwiQuestline_df).to_excel(excel_writer = writer, sheet_name = sheet5_name)
                    if not KiwiJadeAugment_df.empty:
                        addDefaultStyle(KiwiJadeAugment_df).to_excel(excel_writer = writer, sheet_name = sheet6_name)
                    addDefaultStyle(augmentModifier_df).to_excel(excel_writer = writer, sheet_name = sheet7_name)
                    for sheet_name in [sheet1_name, sheet2_name, sheet3_name, sheet4_name, sheet5_name, sheet6_name, sheet7_name]:
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
                logPrint(f"强化符文数据已导出到{self.wbPath}。\nAugment data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出强化符文数据到网页中。产生以下文件：<br>Export augment data into html files. The following files are produced:
        - 斗魂竞技场强化符文（Cherry Augments）
        - 无尽狂潮强化符文（Swarm Augments）
        - 海克斯大乱斗强化符文（Kiwi Augments）
        - 海克斯大乱斗强化符文套装（Kiwi Augment Set）
        - 强化符文修饰（Augment Modifiers）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 强化符文二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of augment binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 最终都市地图（Final City map）
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
        if self.CherryAugment_df.empty:
            status: int = self.build_augment_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #斗魂竞技场强化符文（Arena augment）
        if len(self.CherryAugment_df) > 1:
            CherryAugment_df_web: pandas.DataFrame = self.CherryAugment_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AugmentLargeIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.CherryAugment_df.loc[1:, "AugmentLargeIconPath"].to_list()))
            CherryAugment_df_web.insert(len(CherryAugment_df_web.columns), "AugmentLargeIconUrl", ["强化符文大图标网址"] + AugmentLargeIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "AugmentNameId",
                "AugmentPlatformId",
                "AugmentLargeIconUrl",
                "Enabled",
                "NameTra_content_zh",
                "NameTra_content_en",
                "rarityValue",
                "RootSpell mSpell DataValues MaxLevel",
                "AugmentDisplayTags_content",
                "DescriptionTra_content_zh_burn",
                "DescriptionTra_content_en_burn",
                "AugmentTooltipTra_content_zh_burn",
                "AugmentTooltipTra_content_en_burn",
                "{791eb92e} {5753a320} {05835d27}_content_zh_burn",
                "{791eb92e} {5753a320} {05835d27}_content_en_burn"
            ]
            CherryAugment_df_web = CherryAugment_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            CherryAugment_df_styled: pandas.io.formats.style.Styler = CherryAugment_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:9]
            CherryAugment_df_styled = CherryAugment_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            CherryAugment_htmltable: str = CherryAugment_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            CherryAugment_htmltable = '<meta charset="UTF-8">\n' + CherryAugment_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"CherryAugment_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(CherryAugment_htmltable)
        #无尽狂潮强化符文（Swarm augment）
        if len(self.SwarmAugment_df) > 1:
            SwarmAugment_df_web: pandas.DataFrame = self.SwarmAugment_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AugmentLargeIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.SwarmAugment_df.loc[1:, "AugmentLargeIconPath"].to_list()))
            SwarmAugment_df_web.insert(len(SwarmAugment_df_web.columns), "AugmentLargeIconUrl", ["强化符文大图标网址"] + AugmentLargeIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "AugmentNameId",
                "AugmentPlatformId",
                "AugmentLargeIconUrl",
                "NameTra_content_zh",
                "NameTra_content_en",
                "rarityValue",
                "DescriptionTra_content_zh_burn",
                "DescriptionTra_content_en_burn"
            ]
            SwarmAugment_df_web = SwarmAugment_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            SwarmAugment_df_styled: pandas.io.formats.style.Styler = SwarmAugment_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:6]
            SwarmAugment_df_styled = SwarmAugment_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            SwarmAugment_htmltable: str = SwarmAugment_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            SwarmAugment_htmltable = '<meta charset="UTF-8">\n' + SwarmAugment_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"SwarmAugment_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(SwarmAugment_htmltable)
        #海克斯大乱斗强化符文（ARAM: Mayhem augment）
        if len(self.KiwiAugment_df) > 1:
            KiwiAugment_df_web: pandas.DataFrame = self.KiwiAugment_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AugmentLargeIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.KiwiAugment_df.loc[1:, "AugmentLargeIconPath"].to_list()))
            KiwiAugment_df_web.insert(len(KiwiAugment_df_web.columns), "AugmentLargeIconUrl", ["强化符文大图标网址"] + AugmentLargeIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "AugmentNameId",
                "AugmentPlatformId",
                "AugmentLargeIconUrl",
                "Enabled",
                "NameTra_content_zh",
                "NameTra_content_en",
                "isClassic",
                "rarityValue",
                "AugmentDisplayTags_content",
                "DescriptionTra_content_zh_burn",
                "DescriptionTra_content_en_burn",
                "AugmentTooltipTra_content_zh_burn",
                "AugmentTooltipTra_content_en_burn",
                "questline {c88f1a9b}_content_zh_burn",
                "questline {c88f1a9b}_content_en_burn"
            ]
            KiwiAugment_df_web = KiwiAugment_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            KiwiAugment_df_styled: pandas.io.formats.style.Styler = KiwiAugment_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:9]
            KiwiAugment_df_styled = KiwiAugment_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            KiwiAugment_htmltable: str = KiwiAugment_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            KiwiAugment_htmltable = '<meta charset="UTF-8">\n' + KiwiAugment_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"KiwiAugment_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(KiwiAugment_htmltable)
        #海克斯大乱斗强化符文套装（ARAM: Mayhem augment set）
        if len(self.KiwiAugmentSet_df) > 1:
            KiwiAugmentSet_df_web: pandas.DataFrame = self.KiwiAugmentSet_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AugmentSetIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.KiwiAugmentSet_df.loc[1:, "{4217d741}"].to_list()))
            KiwiAugmentSet_df_web.insert(len(KiwiAugmentSet_df_web.columns), "AugmentSetIconUrl", ["套装缩略图网址"] + AugmentSetIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "{3a942548}",
                "AugmentSetIconUrl",
                "{0746ade9}_content_zh",
                "{0746ade9}_content_en",
                "{97e82990}_content_zh_burn",
                "{97e82990}_content_en_burn",
                "{96b4b430}_object keyTooltip_content_zh_burn",
                "{96b4b430}_object keyTooltip_content_en_burn",
                "augments nameTra_contents_zh",
                "augments nameTra_contents_en"
            ]
            KiwiAugmentSet_df_web = KiwiAugmentSet_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            KiwiAugmentSet_df_styled: pandas.io.formats.style.Styler = KiwiAugmentSet_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:4]
            KiwiAugmentSet_df_styled = KiwiAugmentSet_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            KiwiAugmentSet_htmltable: str = KiwiAugmentSet_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            KiwiAugmentSet_htmltable = '<meta charset="UTF-8">\n' + KiwiAugmentSet_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"KiwiAugmentSet_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(KiwiAugmentSet_htmltable)
        #海克斯大乱斗经典模式版强化符文（ARAM: Mayhem Classic-ish augments）
        if len(self.KiwiJadeAugment_df) > 1:
            KiwiJadeAugment_df_web: pandas.DataFrame = self.KiwiJadeAugment_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            AugmentLargeIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.KiwiJadeAugment_df.loc[1:, "AugmentLargeIconPath"].to_list()))
            KiwiJadeAugment_df_web.insert(len(KiwiJadeAugment_df_web.columns), "AugmentLargeIconUrl", ["强化符文大图标网址"] + AugmentLargeIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "AugmentNameId",
                "AugmentPlatformId",
                "AugmentLargeIconUrl",
                "Enabled",
                "NameTra_content_zh",
                "NameTra_content_en",
                "isCurrent",
                "rarityValue",
                "AugmentDisplayTags_content",
                "DescriptionTra_content_zh_burn",
                "DescriptionTra_content_en_burn",
                "AugmentTooltipTra_content_zh_burn",
                "AugmentTooltipTra_content_en_burn"
            ]
            KiwiJadeAugment_df_web = KiwiJadeAugment_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            KiwiJadeAugment_df_styled: pandas.io.formats.style.Styler = KiwiJadeAugment_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:9]
            KiwiJadeAugment_df_styled = KiwiJadeAugment_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            KiwiJadeAugment_htmltable: str = KiwiJadeAugment_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            KiwiJadeAugment_htmltable = '<meta charset="UTF-8">\n' + KiwiJadeAugment_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"KiwiJadeAugment_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(KiwiJadeAugment_htmltable)
