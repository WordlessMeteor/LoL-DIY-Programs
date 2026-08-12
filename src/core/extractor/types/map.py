import copy, json, os, pandas, sys, time
from openpyxl.worksheet.worksheet import Worksheet
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.webRequest import requestUrl
from src.utils.format import optimize_bool_display, addDefaultStyle, eliminate_empty_fields, pyobj2json
from src.utils.excel_workbook import create_workbook_win32
from src.core.config.headers import map_header_l10n
from src.core.extractor.base import LoLDataExtractor, getBinaryKeys

class MapExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个地图提取器对象。<br>Initialize a MapExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        #self.extractor: LoLDataExtractor = extractor #主要应用于子类对象调用和修改父类对象的属性（Mainly designed for a child object to call and modify the attribute of a parent object）
        self.maps_ready: dict[int, bool] = {mapId: False for mapId in [11, 12, 21, 22, 30, 33, 35, 453]}
        self.map_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.maps_ready = {mapId: False for mapId in self.maps_ready}
    
    def get_map_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取地图二进制描述数据。包括以下内容：<br>Get binary description data of maps online. Including the following content:
        - 召唤师峡谷（Summoner's Rift）
        - 嚎哭深渊（Howling Abyss）
        - 百合与莲花的神庙（Temple of Lily and Lotus）
        - 聚点危机（Convergence）
        - 怒火角斗场（Rings of Wrath）
        - 最终都市（Final City）
        - 班德尔之森（The Bandlewoods）
        - 经典召唤师峡谷（Classic Rift）
        '''
        logPrint = self.log.logPrint
        #召唤师峡谷（Summoner's Rift）
        map11_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map11/map11.bin.json"
        if map11_bin_url in self.__class__.data_cache["online"]:
            self.map11_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map11_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map11_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("召唤师峡谷地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nSummoner's Rift map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map11_bin_url))
                    self.map11_bin = {}
                else:
                    logPrint("召唤师峡谷地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nSummoner's Rift map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map11_bin = source.json()
                self.map11_bin = self.resolve_bin_hash(self.map11_bin)
            self.__class__.data_cache["online"][map11_bin_url] = self.map11_bin #在对一个MapExtractor对象的data_cache进行修改时，由于字典的引用传递，其父LoLDataExtractor对象的data_cache会同步此更改（While modifying `data_cache` of a MapExtractor object, due to the pass-by-reference of a dictionary, the modification will be synchronized in `data_cache` of its parent `LoLDataExtractor` object）
        self.maps_ready[11] = True
        #嚎哭深渊（Howling Abyss）
        map12_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map12/map12.bin.json"
        if map12_bin_url in self.__class__.data_cache["online"]:
            self.map12_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map12_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map12_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("嚎哭深渊地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nHowling Abyss map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map12_bin_url))
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
        self.maps_ready[12] = True
        #百合与莲花的神庙（Temple of Lily and Lotus）
        map21_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map21/map21.bin.json"
        if map21_bin_url in self.__class__.data_cache["online"]:
            self.map21_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map21_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map21_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("百合与莲花的神庙地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nTemple of Lily and Lotus map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map21_bin_url))
                    self.map21_bin = {}
                else:
                    logPrint("百合与莲花的神庙地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nTemple of Lily and Lotus map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map21_bin = source.json()
                self.map21_bin = self.resolve_bin_hash(self.map21_bin)
            self.__class__.data_cache["online"][map21_bin_url] = self.map21_bin
        self.maps_ready[21] = True
        #聚点危机（Convergence）
        map22_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map22/map22.bin.json"
        if map22_bin_url in self.__class__.data_cache["online"]:
            self.map22_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map22_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map22_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("聚点危机地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nConvergence map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map22_bin_url))
                    self.map22_bin = {}
                else:
                    logPrint("聚点危机地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nConvergence map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map22_bin = source.json()
                self.map22_bin = self.resolve_bin_hash(self.map22_bin)
            self.__class__.data_cache["online"][map22_bin_url] = self.map22_bin
        self.maps_ready[22] = True
        #怒火角斗场（Rings of Wrath）
        map30_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map30/map30.bin.json"
        if map30_bin_url in self.__class__.data_cache["online"]:
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map30_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map30_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("怒火角斗场地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nRings of Wrath map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map30_bin_url))
                    self.map30_bin = {}
                else:
                    logPrint("怒火角斗场地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map30_bin = source.json()
                self.map30_bin = self.resolve_bin_hash(self.map30_bin)
            self.__class__.data_cache["online"][map30_bin_url] = self.map30_bin
        self.maps_ready[30] = True
        #最终都市（Final City）
        map33_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map33/map33.bin.json"
        if map33_bin_url in self.__class__.data_cache["online"]:
            self.map33_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map33_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map33_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("最终都市地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nFinal City map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map33_bin_url))
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
        self.maps_ready[33] = True
        #班德尔之森（The Bandlewood）
        map35_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map35/map35.bin.json"
        if map35_bin_url in self.__class__.data_cache["online"]:
            self.map35_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map35_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map35_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("班德尔之森地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nThe Bandlewoods map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map35_bin_url))
                    self.map35_bin = {}
                else:
                    logPrint("班德尔之森地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nThe Bandlewoods map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map35_bin = source.json()
                self.map35_bin = self.resolve_bin_hash(self.map35_bin)
            self.__class__.data_cache["online"][map35_bin_url] = self.map35_bin
        self.maps_ready[35] = True
        #经典召唤师峡谷（Classic Rift）
        map453_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map453/map453.bin.json"
        if map453_bin_url in self.__class__.data_cache["online"]:
            self.map453_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map453_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map453_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("经典召唤师峡谷地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nClassic Rift map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map453_bin_url))
                    self.map453_bin = {}
                else:
                    logPrint("经典召唤师峡谷地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nClassic Rift map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map453_bin = source.json()
                self.map453_bin = self.resolve_bin_hash(self.map453_bin)
            self.__class__.data_cache["online"][map453_bin_url] = self.map453_bin
        self.maps_ready[453] = True
    
    def read_map_data(self, paths: list[str]) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取地图二进制描述数据。<br>Get binary description data of maps offline.
        
        :param paths: 地图二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of map binary description files, arranged in the following order:
        
            - 11: 召唤师峡谷（Summoner's Rift）
            - 12: 嚎哭深渊（Howling Abyss）
            - 21: 百合与莲花的神庙（Temple of Lily and Lotus）
            - 22: 聚点危机（Convergence）
            - 30: 怒火角斗场（Rings of Wrath）
            - 33: 最终都市（Final City）
            - 35: 班德尔之森（The Bandlewoods）
            - 453: 经典召唤师峡谷（Classic Rift）
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
        #召唤师峡谷（Summoner's Rift）
        map11_bin_path: str = paths[0]
        if map11_bin_path in self.__class__.data_cache["local"]:
            self.map11_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map11_bin_path]
        else:
            with open(map11_bin_path, "r", encoding = "utf-8") as fp:
                self.map11_bin = json.load(fp)
            self.map11_bin = self.resolve_bin_hash(self.map11_bin)
            self.__class__.data_cache["local"][map11_bin_path] = self.map11_bin
        self.maps_ready[11] = True
        #嚎哭深渊（Howling Abyss）
        map12_bin_path: str = paths[1]
        if map12_bin_path in self.__class__.data_cache["local"]:
            self.map12_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map12_bin_path]
        else:
            with open(map12_bin_path, "r", encoding = "utf-8") as fp:
                self.map12_bin = json.load(fp)
            self.map12_bin = self.resolve_bin_hash(self.map12_bin)
            self.__class__.data_cache["local"][map12_bin_path] = self.map12_bin
        self.maps_ready[12] = True
        #百合与莲花的神庙（Temple of Lily and Lotus）
        map21_bin_path: str = paths[2]
        if map21_bin_path in self.__class__.data_cache["local"]:
            self.map21_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map21_bin_path]
        else:
            with open(map21_bin_path, "r", encoding = "utf-8") as fp:
                self.map21_bin = json.load(fp)
            self.map21_bin = self.resolve_bin_hash(self.map21_bin)
            self.__class__.data_cache["local"][map21_bin_path] = self.map21_bin
        self.maps_ready[21] = True
        #聚点危机（Convergence）
        map22_bin_path: str = paths[3]
        if map22_bin_path in self.__class__.data_cache["local"]:
            self.map22_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map22_bin_path]
        else:
            with open(map22_bin_path, "r", encoding = "utf-8") as fp:
                self.map22_bin = json.load(fp)
            self.map22_bin = self.resolve_bin_hash(self.map22_bin)
            self.__class__.data_cache["local"][map22_bin_path] = self.map22_bin
        self.maps_ready[22] = True
        #怒火角斗场（Rings of Wrath）
        map30_bin_path: str = paths[4]
        if map30_bin_path in self.__class__.data_cache["local"]:
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map30_bin_path]
        else:
            with open(map30_bin_path, "r", encoding = "utf-8") as fp:
                self.map30_bin = json.load(fp)
            self.map30_bin = self.resolve_bin_hash(self.map30_bin)
            self.__class__.data_cache["local"][map30_bin_path] = self.map30_bin
        self.maps_ready[30] = True
        #最终都市（Final City）
        map33_bin_path: str = paths[5]
        if map33_bin_path in self.__class__.data_cache["local"]:
            self.map33_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map33_bin_path]
        else:
            with open(map33_bin_path, "r", encoding = "utf-8") as fp:
                self.map33_bin = json.load(fp)
            self.map33_bin = self.resolve_bin_hash(self.map33_bin)
            self.__class__.data_cache["local"][map33_bin_path] = self.map33_bin
        self.maps_ready[33] = True
        #班德尔之森（The Bandlewood）
        map35_bin_path: str = paths[6]
        if map35_bin_path in self.__class__.data_cache["local"]:
            self.map35_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map35_bin_path]
        else:
            with open(map35_bin_path, "r", encoding = "utf-8") as fp:
                self.map35_bin = json.load(fp)
            self.map35_bin = self.resolve_bin_hash(self.map35_bin)
            self.__class__.data_cache["local"][map35_bin_path] = self.map35_bin
        self.maps_ready[35] = True
        #经典召唤师峡谷（Classic Rift）
        map453_bin_path: str = paths[7]
        if map453_bin_path in self.__class__.data_cache["local"]:
            self.map453_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map453_bin_path]
        else:
            with open(map453_bin_path, "r", encoding = "utf-8") as fp:
                self.map453_bin = json.load(fp)
            self.map453_bin = self.resolve_bin_hash(self.map453_bin)
            self.__class__.data_cache["local"][map453_bin_path] = self.map453_bin
        self.maps_ready[453] = True
    
    def build_map_dataframe(self, debug: bool = False, paths: Optional[list[str]] = None) -> int:
        '''
        构建地图数据框。<br>Build map dataframe.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 地图二进制描述文件的本地路径列表，按照召唤师峡谷（11）、嚎哭深渊（12）、百合与莲花的神庙（21）、聚点危机（22）、怒火角斗场/最高清算（30）、最终都市（33）和班德尔之森（35）的顺序排列。<br>A local path list of map binary description files, following the order of Summoner's Rift (11), Howling Abyss (12), Temple of Lily and Lotus (21), Convergence (22), Rings of Wrath / The Grand Reckoning (30), Final City (33) and The Bandlewood (35) in turn.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not all(self.maps_ready.values()):
            #获取地图信息（Get map information）
            logPrint("正在读取各地图数据……\nReading each map's data ...", print_time = True)
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_map_data(paths = paths)
            else:
                self.get_map_data()
            if not all(self.maps_ready.values()):
                logPrint("地图数据尚未准备就绪！\nMap data not prepared!")
                return 2
        #检验不同地图数据的异质性（Verify the heterogeneity among different maps' data）
        # map_name_list: list[str] = ["召唤师峡谷", "随机地图", "百合与莲花的神庙", "聚点危机", "怒火角斗场", "最终都市", "班德尔之森", "经典召唤师峡谷"]
        # map_bin_list: list[dict[str, list[str] | dict[str, Any]]] = [map11_bin, map12_bin, map21_bin, map22_bin, map30_bin, map33_bin, map35_bin, map453_bin]
        # overlay_table, overlay_count_table, overlay_identical_table, overlay_difference_table, overlay_diffCount_table = verifyDictHeterogeneity(map_bin_list)
        # for i in range(len(map_bin_list) - 1):
        #     for j in range(i + 1, len(map_bin_list)):
        #         if not overlay_identical_table.loc[i, j]:
        #             print(f"{i}号元素和{j}号元素的值不相同的重合键：")
        #             for key in overlay_difference_table.iloc[i, j]:
        #                 print(key)
        #             print()
        # for (i, j) in [(1, 5), (3, 5)]:
        #     map1Name = map_name_list[i]
        #     map2Name = map_name_list[j]
        #     print(f"【{map1Name}】和【{map2Name}】的小小英雄列表比较：")
        #     characters1 = map_bin_list[i]["{2c7e1b6f}"]["characters"]
        #     characters2 = map_bin_list[j]["{2c7e1b6f}"]["characters"]
        #     print(f"【{map1Name}】中有但【{map2Name}】中没有的小小英雄：")
        #     for character in set(characters1) - set(characters2):
        #         print(character)
        #     print(f"\n【{map2Name}】中有但【{map1Name}】中没有的小小英雄：")
        #     for character in set(characters2) - set(characters1):
        #         print(character)
        #     print("\n")
        #一方面，小小英雄与游戏模式地图数据对象无关；另一方面，将这些差异hash值作为主键在地图二进制描述数据中查询时，发现其描述与嚎哭深渊符合一一对应关系。因此下面在导出各地图的游戏模式地图数据对象时，认为所有地图的二进制描述数据之间两两没有不一致的键值对（键相同但值不同的键值对）【On the one hand, companions seem to have nothing to do the GameModeMapData object. On the other hand, searching for the difference hash keys in the map binary description data shows that the description of each hash value follows a one-to-one correspondence with the resolved value in Howling Abyss' companion list. Therefore, when exporting the GameModeMapData object of all maps, this program assumes there's not any inconsistent key-value pairs (with the same key but different values) between each pair of maps】

        #合并所有地图数据，形成单个字典（Merge all map data into a dictionary into a single dictionary）
        maps_bin: dict[str, list[str] | dict[str, Any]] = self.map11_bin | self.map21_bin | self.map22_bin | self.map30_bin | self.map33_bin | self.map35_bin | self.map12_bin | self.map453_bin

        #将整合后的英雄数据保存到本地（Save merged map data to local）
        # folder: str = os.path.expanduser("~/Desktop")
        # file_path: str = "C:/Users/19250/Documents/Workspace/JupyterLab/自定义脚本/英雄联盟自定义房间创建/maps_bin.json" #供开发者调试（For developer debug use）
        # file_path: str = os.path.join(folder, "maps_bin.json").replace("\\", "/") #供用户调试（For user debug use）
        # with open(file_path, "w", encoding = "utf-8") as fp:
        #     json.dump(maps_bin, fp, indent = 4, ensure_ascii = False)

        #离线加载各英雄数据（Load all maps' binary data offline）
        # logPrint("正在读取各英雄数据……\nReading all map data ...", print_time = True)
        # with open("C:/Users/19250/Documents/Workspace/JupyterLab/自定义脚本/英雄联盟自定义房间创建/maps_bin.json", "r", encoding = "utf-8") as fp:
        #     maps_bin = json.load(fp)
        # maps_bin = self.resolve_bin_hash(maps_bin)
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建地图数据框……\nBuilding the map dataframe ...", print_time = True)
        ##表头部分分为基础表头、二次转化表头和附加说明表头（Headers can be divided into three parts: Basic part, transformed part and supplemental part）
        map_header_basic: list[str] = [] #基础表头指游戏模式地图数据对象的一级键（Basic headers are composed of Level-1 keys in the GameModeMapData object）
        map_header_transformed: list[str] = [] #二次转化表头指游戏模式地图数据对象的值在地图中存在的部分。每个二次转化表头由一级键、子数据类型和二级键组成（Transformed headers are values of a GameModeMapData object which are indices of the map object. Each transformed header is composed of three parts: Level-1 key, subtype and Level-2 key）
        map_header_supplemental: list[str] = [] #每个附加说明表头由某个二次转化表头和字符串“string”组成，用于将一些在字符串常量池中出现的键映射为值（Each supplemental header is composed of a transformed header and the string "string", in order to map the keys that appear in the lolstringtable into values）
        bool_keys: set[str] = set() #这里假设相同的键在不同类型的数据对象中出现时，数据类型是相同的。这里只考虑单值为逻辑值的情形，不适用于逻辑值列表（Here suppose if a key exists in data objects of different type, then the type of this key's value must be identical. Only stores keys whose values are a single boolean value instead of a list of boolean values）
        ##生成动态表头（Generate dynamic headers）
        map_header_basic = getBinaryKeys(maps_bin, objectTypes = "GameModeMapData")[0]["GameModeMapData"]
        map_header_basic.remove("__type")
        dynamicKeys: dict[str, list[str]] = {}
        keys_to_insert: dict[str, list[str]] = {}
        for (key, value) in maps_bin.items():
            if key != "__linked" and value["__type"] == "GameModeMapData":
                for (key1, value1) in value.items():
                    if isinstance(value1, list) and all(map(lambda x: isinstance(x, str), value1)): #一级值为字符串列表时，确认每个元素是否是地图数据的主键。如果是，则提取该主键的值（When the value of a Level-1 key is a list of strings, judge whether each element is a key of the map data. If it is, extract the value of this key from the map data）
                        for value2 in value1:
                            if value2 in maps_bin:
                                subkey = " ".join([key1, maps_bin[value2]["__type"]])
                                if not subkey in keys_to_insert:
                                    keys_to_insert[subkey] = []
                                if subkey in dynamicKeys:
                                    index = 0
                                    for key2 in maps_bin[value2].keys():
                                        if key2 in dynamicKeys[subkey]:
                                            while len(keys_to_insert[subkey]) > 0:
                                                dynamicKeys[subkey].insert(index, keys_to_insert[subkey].pop(0))
                                                index += 1
                                            index = dynamicKeys[subkey].index(key2) + 1
                                        else:
                                            keys_to_insert[subkey].append(key2)
                                    while len(keys_to_insert[subkey]) > 0:
                                        dynamicKeys[subkey].append(keys_to_insert[subkey].pop(0))
                                else:
                                    dynamicKeys[subkey] = []
                    elif isinstance(value1, str): #一级值为字符串时，确认其是否是地图数据的主键。如果是，则提取该主键的值（When the value of a Level-1 key is a string, judge whether it's a key of the map data. If it is, extract the value of this key from the map data）
                        if value1 in maps_bin:
                            subkey = " ".join([key1, maps_bin[value1]["__type"]])
                            if not subkey in keys_to_insert:
                                keys_to_insert[subkey] = []
                            if subkey in dynamicKeys:
                                index = 0
                                for key2 in maps_bin[value1].keys():
                                    if key2 in dynamicKeys[subkey]:
                                        while len(keys_to_insert[subkey]) > 0:
                                            dynamicKeys[subkey].insert(index, keys_to_insert[subkey].pop(0))
                                            index += 1
                                        index = dynamicKeys[subkey].index(key2) + 1
                                    else:
                                        keys_to_insert[subkey].append(key2)
                                    if isinstance(maps_bin[value1][key2], bool):
                                        bool_keys.add(key2)
                                while len(keys_to_insert[subkey]) > 0:
                                    dynamicKeys[subkey].append(keys_to_insert[subkey].pop(0))
                            else:
                                dynamicKeys[subkey] = []
        for key in dynamicKeys:
            for value in dynamicKeys[key]:
                if value != "__type":
                    map_header_transformed.append(f"{key} {value}")
        ##组合形成最终表头（Combine and get the final header list）
        map_header: dict[str, str] = {"key": "主键"}
        for key in map_header_basic + map_header_transformed + map_header_supplemental:
            map_header[key] = map_header_l10n.get(key, "")
        map_header_keys: list[str] = list(map_header.keys())
        map_data: dict[str, list[Any]] = {key: [] for key in map_header_keys} #这个数据并不会被导出（This dictionary won't be exported）
        map_data_json: dict[str, list[Any]] = copy.deepcopy(map_data) #将数据框中的Python列表和字典转化成Json对象（Transform Python lists and dictionaries in the dataframe into Json objects）
        
        #数据整理核心部分（Data organization core part）
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        for (key1, value) in maps_bin.items():
            if key1 != "__linked" and value["__type"] == "GameModeMapData":
                for i in range(1 + len(map_header_basic)):
                    key: str = map_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else: #基础表头部分（Basic header part）
                        if key in {"mRelativeColorization", "mChampionIndicatorEnabled", "mMinionsUseAttackAffectFlagsForTargeting"}: 
                            to_append = value.get(key, False)
                        elif key in {"ItemShopEnabled"}:
                            to_append = value.get(key, True)
                        else:
                            to_append = value.get(key, "")
                    map_data[key].append(to_append)
                    map_data_json[key].append(pyobj2json(to_append))
                #二次转化表头部分（Transformed header part）
                value_dict = {}
                for key in value: #构造嵌套字典。一级键是游戏模式地图数据对象的键。二级键是游戏模式地图数据对象的值的类型。三级键是以游戏模式地图数据对象的值为主键的地图数据对象的值（Build a nested dictionary. Level-1 key is the key of a GameModeMapData object. Level-2 key is the type of the value of a GameModeMapData object. Level-3 key is the value of an object whose key is the value of a GameModeMapData object）
                    if isinstance(value[key], list) and all(map(lambda x: isinstance(x, str), value[key])):
                        value_dict[key] = {} #考虑到字符串列表中可能包含相同类型的地图数据对象主键，因此构造一个嵌套字典来存储同类型数据对象的主键。次级字典的每个键的值取同键元素形成列表（Considering there may be more than one keys that has the same type of value, a nested dictionary is defined here to store the keys classified into data types. Each key's value is a list that contain values of the same key）
                        for value1 in value[key]:
                            if value1 in maps_bin:
                                value1Type = maps_bin[value1]["__type"]
                                if not value1Type in value_dict[key]:
                                    value_dict[key][value1Type] = {}
                                for key2 in maps_bin[value1]:
                                    if key2 != "__type":
                                        if not key2 in value_dict[key][value1Type]:
                                            value_dict[key][value1Type][key2] = []
                                        value_dict[key][value1Type][key2].append(maps_bin[value1][key2])
                    elif isinstance(value[key], str):
                        value_dict[key] = {}
                        value1 = value[key]
                        if value1 in maps_bin:
                            value1Type = maps_bin[value1]["__type"]
                            if not value1Type in value_dict[key]:
                                value_dict[key][value1Type] = {}
                            for key2 in maps_bin[value1]:
                                if key2 != "__type":
                                    value_dict[key][value1Type][key2] = maps_bin[value1][key2]
                for i in range(1 + len(map_header_basic), 1 + len(map_header_basic) + len(map_header_transformed)):
                    key: str = map_header_keys[i]
                    Level1Key, objectType, Level2Key = key.split()
                    if Level1Key in value_dict and objectType in value_dict[Level1Key] and Level2Key in value_dict[Level1Key][objectType]:
                        to_append = value_dict[Level1Key][objectType][Level2Key]
                    else:
                        to_append = False if Level2Key in bool_keys else ""
                    map_data[key].append(to_append)
                    map_data_json[key].append(pyobj2json(to_append))
                for i in range(1 + len(map_header_basic) + len(map_header_transformed), len(map_header_keys)): #附件说明表头部分（Supplemental header part）
                    key: str = map_header_keys[i]
                    Level1Key, objectType, Level2Key = key.split()[:3]
                    if Level1Key in value and value[Level1Key] in maps_bin and Level2Key in maps_bin[value[Level1Key]]:
                        to_append = self.get_strtable_value(strtable_lol_target, maps_bin[value[Level1Key]][Level2Key], default = "")
                    else:
                        to_append = ""
                    map_data[key].append(to_append)
                    map_data_json[key].append(pyobj2json(to_append))
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        ##确定表头顺序（Determine the order of the header）
        ###主键置于第一位（`key` is at the first place）
        map_statistics_output_order: list[int] = [0]
        ###基础表头排序（Sort the basic header）
        expected_order_basic: list[str] = ["key", "mModeName", "mGameModeConstants", "mGameplayConfig", "Configs", "ConfigsClient", "mExperienceCurveData", "mExperienceModData", "mDeathTimes", "StartupCheats", "mStatsUiData", "mChampionLists", "mItemShopData", "itemLists", "{dc2bc473}", "mAutoItemPurchasingConfig", "mMapLocators", "DefaultRespawnPoints", "JungleRecommendationMapInformation", "DefaultJunglePathRecommendation", "mPerkReplacements", "mSurrenderSettings", "AnnouncementsMapping", "mRelativeColorization", "mChampionIndicatorEnabled", "mCursorConfig", "mCursorConfigUpdate", "LevelControllers", "AdditionalPropertyDataPaths"]
        map_header_basic_tmp: list[str] = map_header_basic[:]
        for key in expected_order_basic:
            if key in map_header_basic:
                map_statistics_output_order.append(map_header_keys.index(key))
                map_header_basic_tmp.remove(key)
            #如果期望顺序列表中的键不存在于地图数据中，则忽略该键。下同（If any key in the expected order list doesn't exist in the map data, neglect this key. So as the following case）
        map_statistics_output_order += list(map(lambda x: map_header_keys.index(x), map_header_basic_tmp))
        del map_header_basic_tmp
        ###二次转化表头排序（Sort the transformed header）
        map_header_basic_ordered: list[str] = list(map(lambda x: map_header_keys[x], map_statistics_output_order)) #获取排序后的基础表头（Get the ordered basic header）
        expected_order_transformed: list[str] = []
        for key1 in map_header_basic_ordered:
            for key2 in map_header_transformed:
                if key2.split()[0] == key1: #将二次转化表头根据基础表头进行排序（Order the transformed headers according to the order of basic headers）
                    expected_order_transformed.append(key2)
        map_header_transformed_tmp: list[str] = map_header_transformed[:]
        for key in expected_order_transformed:
            if key in map_header_transformed:
                map_statistics_output_order.append(map_header_keys.index(key))
                map_header_transformed_tmp.remove(key)
        map_statistics_output_order += list(map(lambda x: map_header_keys.index(x), map_header_transformed_tmp))
        del map_header_transformed_tmp
        ###附加说明表头排序（Sort the supplemental header）
        
        ##创建数据框（Create the dataframe）
        map_data_organized: dict[str, list[Any]] = {map_header_keys[i]: map_data_json[map_header_keys[i]] for i in map_statistics_output_order}
        map_df: pandas.DataFrame = pandas.DataFrame(data = map_data_organized)
        logPrint("正在优化地图数据框的逻辑值显示……\nOptimizing boolean value display of the map dataframe ...")
        optimize_bool_display(map_df)
        map_df = pandas.concat([pandas.DataFrame([map_header])[map_df.columns], map_df], ignore_index = True)
        self.map_df = map_df
        return 0
    
    def enqueue_map_dataframe(self) -> None:
        '''
        将地图数据框追加到数据提取器基类的数据框队列尾部。<br>Append the map dataframe into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.map_df.empty:
            map_ws: dict[str, Any] = self.worksheet_metadata["Map"]
            sheet1_name: str = map_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else map_ws["sheet_name_without_version"]
            map_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(map_ws["dType"]), "dType": map_ws["dType"], "sheet_name": sheet1_name, "sheet": self.map_df, "T": True}
            self.enqueue_df(map_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_map_data(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出地图数据到工作簿中。产生以下工作表：<br>Export map data to a workbook. The following worksheet is added:
        - 地图（Map）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 地图二进制描述文件的本地路径列表，按照召唤师峡谷（11）、嚎哭深渊（12）、百合与莲花的神庙（21）、聚点危机（22）、怒火角斗场/最高清算（30）、最终都市（33）和班德尔之森（35）的顺序排列。<br>A local path list of map binary description files, following the order of Summoner's Rift (11), Howling Abyss (12), Temple of Lily and Lotus (21), Convergence (22), Rings of Wrath / The Grand Reckoning (30), Final City (33) and The Bandlewood (35) in turn.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径！\nPath of exported file not specified!")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if self.map_df.empty:
            status: int = self.build_map_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            map_df: pandas.DataFrame = eliminate_empty_fields(self.map_df)
        else:
            map_df = self.map_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["Map"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["Map"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(map_df.transpose()).to_excel(excel_writer = writer, sheet_name = sheet1_name)
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
                logPrint(f"地图数据已导出到{self.wbPath}。\nMap data have been exported to {self.wbPath}.", print_time = True)
                break
