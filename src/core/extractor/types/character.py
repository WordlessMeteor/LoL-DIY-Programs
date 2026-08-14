import copy, json, os, pandas, re, sys, time
from urllib.parse import urljoin
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
from src.core.config.headers import champion_header, champion_spell_header
from src.core.extractor.base import LoLDataExtractor

class ChampionExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个英雄提取器对象。<br>Initialize a ChampionExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.useAllCharacter: bool = False #决定数据资源是否使用所有角色信息（Determines whether the data resources are from all characters）
        self.characters_ready: dict[str, bool] = {"map22": False, "characterList1": False, "characterList2": False, "character_binary": False} #后面在判断角色数据是否准备就绪时只用到了“character_binary”键（Only "character_binary" key is used later to judge whether character data are prepared）
        self.champions_ready: dict[str, bool] = {"summary": False, "champion_binary": False}
        self.champions_bin_dict: dict[str, list[str] | dict[str, Any]] = {} #所有角色的原始数据字典（Raw data dictionary of all characters）
        self.champion_df: pandas.DataFrame = pandas.DataFrame()
        self.champion_spell_df: pandas.DataFrame = pandas.DataFrame()

    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.characters_ready = {key: False for key in self.characters_ready}
        self.champions_ready = {key: False for key in self.champions_ready}
    
    def set_mode(self, useAllCharacter: Optional[bool] = None) -> int:
        '''
        设置要导出的角色信息范围。<br>Set the range of character data to export.
        
        :param useAllCharacter: 是否导出所有角色数据。如果未指定，则会输出提示来询问。<br>Whether to export data of all characters. If it's unspecified, hints will be given to ask the user.
        :type useAllCharacter: bool
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if useAllCharacter == None:
            logPrint("请选择您想要获取的英雄信息：\nPlease select a range of champions you want to get:\n1\t可用英雄（Available champions）\n2\t所有角色（All characters）\n警告：选择提取所有角色信息耗费时间可达1小时。任何网络异常会中止数据获取过程。\nNote: It may takes up to an hour to extract all characters' data. Any network error will cancel the data fetching process.")
            self.useAllCharacter = False #初始化英雄范围控制变量（Initialize character range control variable）
            while True:
                option = logInput()
                if option == "":
                    continue
                elif option[0] == "0":
                    return 1
                elif option[0] == "1" or option[0] == "2":
                    self.useAllCharacter = option[0] == "2"
                    break
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        else:
            self.useAllCharacter = useAllCharacter
        return 0
    
    def get_champion_data(self, verbose: bool = True) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取英雄二进制描述数据。<br>Get binary description data of champions online.
        
        在`useAllCharacter`属性为真时，将获取所有角色的数据，否则只获取英雄的数据。<br>When the attribute `useAllCharacter` is True, all characters' data will be fetched, otherwise only champion data will be fetched.
        
        :param verbose: 是否打印过程性信息。默认为是。<br>Whether to print the progress. True by default.
        :type verbose: bool
        '''
        logPrint = self.log.logPrint
        #获取所有英雄的名称信息（Get all champions' name information）
        logPrint("正在读取英雄元数据……\nReading champion metadata ...", print_time = True, verbose = verbose)
        champion_summary_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(self.version, self.language_folder)
        if champion_summary_url in self.__class__.data_cache["online"]:
            self.champion_summary = self.__class__.data_cache["online"][champion_summary_url]
        else:
            source, status, self.session = requestUrl("GET", champion_summary_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("英雄概要信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nChampion summary data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(champion_summary_url))
                else:
                    logPrint("英雄概要信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion summary data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            self.champion_summary: list[dict[str, int | str | list[str]]] = source.json()
            self.__class__.data_cache["online"][champion_summary_url] = self.champion_summary
        self.champions_ready["summary"] = True
        if self.useAllCharacter:
            ##聚点危机地图（Convergence map）
            map22_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map22/map22.bin.json" #云顶之弈的小小英雄和羁绊信息（TFT champion and trait data）
            if map22_bin_url in self.__class__.data_cache["online"]:
                self.map22_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map22_bin_url]
            else:
                source, status, self.session = requestUrl("GET", map22_bin_url, session = self.session, log = self.log)
                if status != 200:
                    if status == 404:
                        logPrint("聚点危机地图信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nConvergence map data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(map22_bin_url))
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
            self.characters_ready["map22"] = True
            if "characters_bin_dict" in self.__class__.merged_data_cache:
                self.champions_bin_dict = self.__class__.merged_data_cache["characters_bin_dict"]
            else:
                if self.fileExportList_ready: #当文件导出列表就绪，直接从列表中筛选角色数据网址（When the file export list is ready, directly filter character data URLs from the list）
                    #整理角色列表（Sort out the characters into a list）
                    self.characters_ready["characterList1"] = True #在从文件导出列表中获取角色数据时，相当于角色列表已准备就绪（When the file export list is fetched, the character list must be ready）
                    self.characters_ready["characterList2"] = True
                    logPrint("正在整理角色列表……\nSorting out characters into a list ...", print_time = True, verbose = verbose)
                    character_binary_urls1: dict[str, str] = {}
                    for item in self.files_exported:
                        if item.startswith("game/data/characters/") and item.endswith(".bin.json"):
                            characterName: str = item.split("/")[3]
                            if len(item.split("/")) == 5 and item.split("/")[4] == f"{characterName}.bin.json":
                                character_binary_urls1[characterName] = urljoin(f"https://raw.communitydragon.org/json/{self.version}/", item)
                        elif item.startswith("game/characters/") and item.endswith(".cdtb.bin.json"):
                            characterName: str = item.split("/")[2].replace(".cdtb.bin.json", "")
                            if len(item.split("/")) == 3:
                                character_binary_urls1[characterName] = urljoin(f"https://raw.communitydragon.org/json/{self.version}/", item)
                    #读取所有角色的二进制描述数据（Load all characters' binary description data）
                    logPrint("正在读取各角色数据……\nReading all character data ...", print_time = True, verbose = verbose)
                    characterNames = list(character_binary_urls1.keys())
                    for i in range(len(characterNames)):
                        characterName = characterNames[i]
                        # logPrint("[%d/%d]正在加载角色%s的信息…… | Loading character %s%s information ..." %(i + 1, len(characterNames), characterName, characterName, "s'" if characterName.endswith("s") else "'s"), print_time = True, verbose = verbose)
                        character_binary_url: str = character_binary_urls1[characterName]
                        if character_binary_url in self.__class__.data_cache["online"]:
                            character_binary: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][character_binary_url]
                        else:
                            source, status, self.session = requestUrl("GET", character_binary_url, session = self.session, log = self.log)
                            if status != 200:
                                if status == 404:
                                    logPrint(f"未找到角色{characterName}的信息。程序将跳过该角色。\nCharacter {characterName} data not found. The program will skip this character.")
                                    continue
                                else:
                                    logPrint("角色信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                                    time.sleep(3)
                                self.init_data_readiness()
                                return
                            character_binary = source.json()
                            character_binary = self.resolve_bin_hash(character_binary)
                            self.__class__.data_cache["online"][character_binary_url] = character_binary
                        self.champions_bin_dict[characterName] = character_binary
                        logPrint("[%d/%d]已加载角色（Character loaded）：%s" %(i + 1, len(characterNames), characterName), print_time = True, verbose = verbose)
                    else:
                        self.__class__.merged_data_cache["characters_bin_dict"] = self.champions_bin_dict
                else: #当文件导出列表尚未准备就绪时，从两个指定文件夹中获取角色数据（When the file export list isn't ready yet, get character data from two specified folders）
                    #整理角色列表（Sort out the characters into a list）
                    logPrint("正在整理角色列表……\nSorting out characters into a list ...", print_time = True, verbose = verbose)
                    characterList_url1: str = f"https://raw.communitydragon.org/json/{self.version}/game/data/characters/"
                    if characterList_url1 in self.__class__.data_cache["online"]:
                        characterList1 = self.__class__.data_cache["online"][characterList_url1]
                    else:
                        source, status, self.session = requestUrl("GET", characterList_url1, session = self.session, log = self.log)
                        if status != 200:
                            if status == 404:
                                logPrint("第一批角色列表获取失败！请检查以下链接的可用性。程序即将返回上一层。\nCharacter List 1 capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(characterList_url1))
                            else:
                                logPrint("第一批角色列表获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nCharacter List 1 capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                            time.sleep(3)
                            self.init_data_readiness()
                            return
                        characterList1: list[dict[str, str]] = source.json()
                        self.__class__.data_cache["online"][characterList_url1] = characterList1
                    self.characters_ready["characterList1"] = True
                    characterList_url2: str = f"https://raw.communitydragon.org/json/{self.version}/game/characters/"
                    if characterList_url2 in self.__class__.data_cache["online"]:
                        characterList2 = self.__class__.data_cache["online"][characterList_url2]
                    else:
                        source, status, self.session = requestUrl("GET", characterList_url2, session = self.session, log = self.log)
                        if status != 200:
                            if status == 404:
                                logPrint("第二批角色列表获取失败！请检查以下链接的可用性。程序即将返回上一层。\nCharacter List 2 capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(characterList_url2))
                            else:
                                logPrint("第二批角色列表获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nCharacter List 2 capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                            time.sleep(3)
                            self.init_data_readiness()
                            return
                        characterList2: list[dict[str, str | int]] = source.json()
                        self.__class__.data_cache["online"][characterList_url2] = characterList2
                    self.characters_ready["characterList2"] = True
                    character_binary_urls2: dict[str, list[str]] = {}
                    for item in characterList1:
                        if item["type"] == "directory":
                            characterName: str = item["name"]
                            character_binary_urls2[characterName] = [f"https://raw.communitydragon.org/{self.version}/game/data/characters/{characterName}/{characterName}.bin.json"]
                    for item in characterList2:
                        if item["type"] == "file" and item["name"].endswith(".cdtb.bin.json"):
                            characterName: str = item["name"].replace(".cdtb.bin.json", "")
                            if characterName in character_binary_urls2: #当首选地址不存在时，采取备用地址（When the first url doesn't exist, use the second url）
                                character_binary_urls2[characterName].append(f"https://raw.communitydragon.org/{self.version}/game/characters/{characterName}.cdtb.bin.json")
                            else:
                                character_binary_urls2[characterName] = [f"https://raw.communitydragon.org/{self.version}/game/characters/{characterName}.cdtb.bin.json"]
                    #读取所有角色的二进制描述数据（Load all characters' binary description data）
                    logPrint("正在读取各角色数据……\nReading all character data ...", print_time = True, verbose = verbose)
                    characterNames = list(character_binary_urls2.keys())
                    for i in range(len(characterNames)):
                        characterName = characterNames[i]
                        logPrint("[%d/%d]正在加载角色%s的信息…… | Loading character %s%s information ..." %(i + 1, len(characterNames), characterName, characterName, "s'" if characterName.endswith("s") else "'s"), print_time = True, verbose = verbose)
                        character_bin_urls: list[str] = character_binary_urls2[characterName]
                        for j in range(len(character_bin_urls)):
                            character_binary_url = character_bin_urls[j]
                            if character_binary_url in self.__class__.data_cache["online"]:
                                character_binary: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][character_binary_url]
                            else:
                                logPrint("[%d/%d][%d/%d]正在加载链接（Fetching url）： %s" %(i + 1, len(characterNames), j + 1, len(character_bin_urls), character_binary_url), write_time = False, verbose = verbose)
                                source, status, self.session = requestUrl("GET", character_binary_url, session = self.session, log = self.log)
                                if status != 200:
                                    if status == 404:
                                        if len(character_bin_urls) > 1 and j < len(character_bin_urls) - 1:
                                            logPrint(f"未找到角色{characterName}的信息。程序将使用备用网址。\nCharacter {characterName} data not found. The program will use another url.")
                                        else:
                                            logPrint(f"未找到角色{characterName}的信息。程序将跳过该角色。\nCharacter {characterName} data not found. The program will skip this character.")
                                        continue
                                    else:
                                        if status == -1:
                                            logPrint("角色信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                                            time.sleep(3)
                                        self.init_data_readiness()
                                        return
                                character_binary = source.json()
                                character_binary = self.resolve_bin_hash(character_binary)
                                self.__class__.data_cache["online"][character_binary_url] = character_binary
                            self.champions_bin_dict[characterName] = character_binary
                            # logPrint("[%d/%d]已加载角色（Character loaded）：%s" %(i + 1, len(characterNames), characterName), print_time = True, verbose = verbose)
                            break
                    else:
                        self.__class__.merged_data_cache["characters_bin_dict"] = self.champions_bin_dict
            self.characters_ready["character_binary"] = True #所有角色的二进制描述数据准备就绪后，执行该语句（After all characters' binary description data are prepared, execute this statement）
        else:
            if "champions_bin_dict" in self.__class__.merged_data_cache:
                self.champions_bin_dict = self.__class__.merged_data_cache["champions_bin_dict"]
            else:
                #读取所有英雄的二进制描述数据（Load all champions' binary description data）
                logPrint("正在读取各英雄数据……\nReading all champion data ...", print_time = True, verbose = verbose)
                for i in range(len(self.champion_summary)):
                    champion = self.champion_summary[i]
                    alias: str = champion["alias"].lower()
                    if alias == "none":
                        logPrint("[%d/%d]已跳过英雄（Champion skipped）：%s" %(i + 1, len(self.champion_summary), champion["alias"]), print_time = True, verbose = verbose)
                    else:
                        champion_binary_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/characters/{alias}/{alias}.bin.json"
                        if champion_binary_url in self.__class__.data_cache["online"]:
                            champion_binary: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][champion_binary_url]
                        else:
                            source, status, self.session = requestUrl("GET", champion_binary_url, session = self.session, log = self.log)
                            if status != 200:
                                if status == 404:
                                    logPrint("英雄信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nChampion data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(champion_binary_url))
                                else:
                                    logPrint("英雄信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                                time.sleep(3)
                                self.init_data_readiness()
                                break
                            champion_binary = source.json()
                            champion_binary = self.resolve_bin_hash(champion_binary)
                            self.__class__.data_cache["online"][champion_binary_url] = champion_binary
                        self.champions_bin_dict[champion["alias"]] = champion_binary
                        logPrint("[%d/%d]已加载英雄（Champion loaded）：%s" %(i + 1, len(self.champion_summary), champion["alias"]), print_time = True, verbose = verbose)
                else:
                    self.__class__.merged_data_cache["champions_bin_dict"] = self.champions_bin_dict
            self.champions_ready["champion_binary"] = True #所有英雄的二进制描述数据准备就绪后，执行该语句（After all champions' binary description data are prepared, execute this statement）
    
    def read_champion_data(self, paths: Optional[list[str]] = None, verbose: bool = True) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取英雄二进制描述数据。<br>Get binary description data of champions offline.
        
        :param paths: 当使用所有角色数据时，`paths`由以下部分组成：<br>When all characters' data are used, `paths` is a list composed of the following content:
        
            - 英雄概要文件路径（Champion summary file path）
            - 聚点危机地图二进制描述文件路径（Convergence map binary description file path）
            - 角色文件夹1路径（Character folder 1 path）： game/data/characters
            - 角色文件夹2路径（Character folder 2 path）： game/characters
            
            当仅使用英雄数据时，`paths`由以下部分组成：<br>When only champions' data are used, `paths` is a list composed of the following content:
            - 英雄概要文件路径（Champion summary file path）
            - 角色文件夹路径（Character folder path）： game/data/characters
        :type paths: list[str]
        :param verbose: 是否打印过程性信息。默认为是。<br>Whether to print the progress. True by default.
        :type verbose: bool
        '''
        logPrint = self.log.logPrint
        if paths == None:
            logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
            return
        #获取所有英雄的名称信息（Get all champions' name information）
        champion_summary_path = paths[0]
        if champion_summary_path in self.__class__.data_cache["local"]:
            self.champion_summary: list[dict[str, int | str | list[str]]] = self.__class__.data_cache["local"][champion_summary_path]
        else:
            with open(champion_summary_path, "r", encoding = "utf-8") as fp:
                self.champion_summary = json.load(fp)
            self.__class__.data_cache["local"][champion_summary_path] = self.champion_summary
        self.champions_ready["summary"] = True
        if self.useAllCharacter:
            if paths[1] in self.__class__.data_cache["local"]:
                self.map22_bin = self.__class__.data_cache["local"][paths[1]]
                self.characters_ready["map22"] = True #当目的变量准备就绪时，应标记中间变量准备就绪（When the target variable is prepared, the intermediate variables should also be marked as prepared）
            else:
                ##聚点危机地图（Convergence map）
                map22_bin_path: str = paths[1]
                if map22_bin_path in self.__class__.data_cache["local"]:
                    self.map22_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map22_bin_path]
                else:
                    if os.path.exists(map22_bin_path):
                        with open(map22_bin_path, "r", encoding = "utf-8") as fp:
                            self.map22_bin = json.load(fp)
                        self.map22_bin = self.resolve_bin_hash(self.map22_bin)
                        self.__class__.data_cache["local"][map22_bin_path] = self.map22_bin
                    else:
                        self.map22_bin = {} #早期没有云顶之弈模式（In early days, TFT wasn't invented）
                self.characters_ready["map22"] = True
            if "characters_bin_dict" in self.__class__.merged_data_cache:
                self.characters_ready["characterList1"] = True
                self.characters_ready["characterList2"] = True
                self.champions_bin_dict = self.__class__.merged_data_cache["characters_bin_dict"]
            else:
                #整理角色列表（Sort out the characters into a list）
                characterList_folder1: str = paths[2]
                characterList_folder2: str = paths[3]
                character_binary_paths: dict[str, list[str]] = {}
                items1: list[str] = os.listdir(characterList_folder1)
                for characterName in items1:
                    character_folder: str = os.path.join(characterList_folder1, characterName).replace("\\", "/")
                    if os.path.isdir(character_folder):
                        character_binary_path: str = os.path.join(character_folder, f"{characterName}.bin.json").replace("\\", "/")
                        if os.path.exists(character_binary_path) and os.path.isfile(character_binary_path):
                            character_binary_paths[characterName] = [character_binary_path]
                self.characters_ready["characterList1"] = True
                items2: list[str] = os.listdir(characterList_folder2)
                for file in items2:
                    if file.endswith(".cdtb.bin.json"):
                        characterName = file.rstrip(".cdtb.bin.json")
                        character_binary_path: str = os.path.join(characterList_folder2, file).replace("\\", "/")
                        if characterName in character_binary_paths:
                            character_binary_paths[characterName].append(character_binary_path)
                        else:
                            character_binary_paths[characterName] = [character_binary_path]
                self.characters_ready["characterList2"] = True
                #读取所有角色的二进制描述数据（Load all characters' binary description data）
                characterNames = list(character_binary_paths.keys())
                for i in range(len(characterNames)):
                    characterName = characterNames[i]
                    logPrint("[%d/%d]正在加载角色%s的信息……\nLoading character %s%s information ..." %(i + 1, len(characterNames), characterName, characterName, "s'" if characterName.endswith("s") else "'s"), print_time = True, verbose = verbose)
                    character_bin_paths: list[str] = character_binary_paths[characterName]
                    for j in range(len(character_bin_paths)):
                        character_binary_path = character_bin_paths[j]
                        if character_binary_path in self.__class__.data_cache["local"]:
                            character_binary: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][character_binary_path]
                            self.champions_bin_dict[characterName] = character_binary
                            break
                        else:
                            try:
                                with open(character_binary_path, "r", encoding = "utf-8") as fp:
                                    character_binary = json.load(fp)
                            except json.decoder.JSONDecodeError:
                                if len(character_bin_paths) > 1 and j < len(character_bin_paths) - 1: #正常情况下，每个characterName应只对应一个本地路径。此部分只是为了效仿在线加载部分的代码，并且以防万一（Normally, each `characterName` corresponds to one local path. This part is only designed to fit the code style in online loading part, plus just in case a format mistake would happen）
                                    logPrint("本地文件格式不正确。程序将使用备用地址。\nLocal file format invalid! The program will use another path.")
                                else:
                                    logPrint("本地文件格式不正确。程序将跳过该文件。\nLocal file format invalid! The program will skip this file.")
                                continue
                            else:
                                character_binary = self.resolve_bin_hash(character_binary)
                                self.__class__.data_cache["local"][character_binary_path] = character_binary
                                self.champions_bin_dict[characterName] = character_binary
                                break
                else:
                    self.__class__.merged_data_cache["characters_bin_dict"] = self.champions_bin_dict
            self.characters_ready["character_binary"] = True
        else:
            if "champions_bin_dict" in self.__class__.merged_data_cache:
                self.champions_bin_dict = self.__class__.merged_data_cache["champions_bin_dict"]
            else:
                #读取所有英雄的二进制描述数据（Load all champions' binary description data）
                for i in range(len(self.champion_summary)):
                    champion = self.champion_summary[i]
                    alias: str = champion["alias"].lower()
                    if alias == "none":
                        # logPrint("[%d/%d]已跳过英雄（Champion skipped）：%s" %(i + 1, len(self.champion_summary), champion["alias"]), print_time = True, verbose = verbose)
                        pass
                    else:
                        champion_binary_path: str = os.path.join(paths[1], f"{alias}/{alias}.bin.json").replace("\\", "/")
                        if champion_binary_path in self.__class__.data_cache["local"]:
                            champion_binary: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][champion_binary_path]
                        else:
                            with open(champion_binary_path, "r", encoding = "utf-8") as fp:
                                champion_binary = json.load(fp)
                            champion_binary = self.resolve_bin_hash(champion_binary)
                            self.__class__.data_cache["local"][champion_binary_path] = champion_binary
                        self.champions_bin_dict[champion["alias"]] = champion_binary
                        # logPrint("[%d/%d]已加载英雄（Champion loaded）：%s" %(i + 1, len(self.champion_summary), champion["alias"]), print_time = True, verbose = verbose)
                else:
                    self.__class__.merged_data_cache["champions_bin_dict"] = self.champions_bin_dict
            self.champions_ready["champion_binary"] = True
    
    def build_champion_dataframe(self, debug: bool = False, paths: Optional[list[str]] = None, verbose: bool = True) -> int:
        '''
        构建英雄数据框。<br>Build champion dataframe.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 当使用所有角色数据时，`paths`由以下部分组成：<br>When all characters' data are used, `paths` is a list composed of the following content:
        
            - 聚点危机地图二进制描述文件路径（Convergence map binary description file path）
            - 角色文件夹1路径（Character folder 1 path）： game/data/characters
            - 角色文件夹2路径（Character folder 2 path）： game/characters
            
            当仅使用英雄数据时，`paths`由以下部分组成：<br>When only champions' data are used, `paths` is a list composed of the following content:
            - 英雄概要文件路径（Champion summary file path）
            - 角色文件夹路径（Character folder path）： game/data/characters
            
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        :param verbose: 是否打印过程性信息。默认为是。<br>Whether to print the progress. True by default.
        :type verbose: bool
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if self.useAllCharacter and not self.characters_ready["character_binary"] or not self.useAllCharacter and not self.champions_ready["champion_binary"] or not self.champions_ready["summary"]:
            if self.useAllCharacter:
                logPrint("正在读取角色数据……\nReading character data ...", print_time = True)
            else:
                logPrint("正在读取英雄数据……\nReading champion data ...", print_time = True)
            #获取英雄/角色信息（Get champion / character information）
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_champion_data(paths = paths, verbose = verbose)
            else:
                self.get_champion_data(verbose = verbose)
            if self.useAllCharacter and not self.characters_ready["character_binary"]:
                logPrint("角色数据尚未准备就绪！\nCharacter data not prepared!")
                return 2
            if not self.useAllCharacter and not self.champions_ready["champion_binary"]:
                logPrint("英雄数据尚未准备就绪！\nChampion data not prepared!")
                return 2
        
        #检验不同英雄数据的异质性（Verify the heterogeneity among different champions' data）
        # overlay_table, overlay_count_table, overlay_identical_table, overlay_difference_table = verifyDictHeterogeneity(list(champions_bin_dict.values()))
        # print(all(overlay_identical_table.iloc[i, j] for i in range(overlay_identical_table.shape[0]) for j in range(overlay_identical_table.shape[1]))) #返回真则表明所有重合键的值都相同，意味着可以放心合并数据（True returned means all common keys' values are the same, so feel free to merge any champion's data）
        
        #合并所有英雄数据，形成单个字典（Merge all champion data into a dictionary into a single dictionary）
        champions_bin: dict[str, list[str] | dict[str, Any]] = {}
        for alias in self.champions_bin_dict:
            champion_bin = copy.deepcopy(self.champions_bin_dict[alias])
            for (key, value) in champion_bin.items():
                if key != "__linked" and value["__type"] == "CharacterRecord":
                    if not "spells" in value and "spellNames" in value: #14.15版本的角色记录对象的没有“spells”键（In v14.15, the CharacterRecord objects don't contain "spells" key）
                        value["spells"] = list(map(lambda x: "Characters/%s/Spells/%s" %(value["mCharacterName"], x), value["spellNames"]))
            champions_bin |= champion_bin
        
        #将整合后的英雄数据保存到本地（Save merged champion data to local）
        # folder: str = os.path.expanduser("~/Desktop")
        # file_path: str = "C:/Users/19250/Documents/Workspace/JupyterLab/自定义脚本/英雄联盟自定义房间创建/champions_bin_v1415.json" #供开发者调试（For developer debug use）
        # file_path: str = os.path.join(folder, "champions_bin.json").replace("\\", "/") #供用户调试（For user debug use）
        # with open(file_path, "w", encoding = "utf-8") as fp:
        #     json.dump(champions_bin, fp, indent = 4, ensure_ascii = False)
        
        #离线加载各英雄数据（Load all champions' binary data offline）
        # logPrint("正在读取各英雄数据……\nReading all champion data ...", print_time = True)
        # with open("C:/Users/19250/Documents/Workspace/JupyterLab/自定义脚本/英雄联盟自定义房间创建/champions_bin.json", "r", encoding = "utf-8") as fp:
        #     champions_bin = json.load(fp)
        # champions_bin = self.resolve_bin_hash(champions_bin)

        #提取指令字典。主要用于来自其它指令数据的变量的转换（Extract spell dictionary. Mainly used for transformation of variables from other spells）
        self.init_mSpells()
        for (key, value) in champions_bin.items():
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value

        #定义数据结构（Define the data structure）
        logPrint("正在构建英雄及其技能数据框……\nBuilding the champion and spell dataframes ...", print_time = True)
        champion_header_keys: list[str] = list(champion_header.keys())
        champion_data: dict[str, list[Any]] = {key: [] for key in champion_header_keys}
        champion_data_json: dict[str, list[Any]] = copy.deepcopy(champion_data)
        champion_spell_header_keys: list[str] = list(champion_spell_header.keys())
        champion_spell_data: dict[str, list[Any]] = {key: [] for key in champion_spell_header_keys}
        champion_spell_data_json: dict[str, list[Any]] = copy.deepcopy(champion_spell_data)
        
        #构建从基本指令到技能的映射（Build map from root spells to abilities）
        abilityKey_rootSpellKey_map: dict[str, str] = {}
        abilityKey_childSpellKey_map: dict[str, str] = {}
        characterRecordKey_abilityKey_map: dict[str, str] = {} #主要用于确认技能热键（Mainly designed to determine a spell's hotkey）
        for (key, value) in champions_bin.items():
            if key != "__linked" and value["__type"] in {"CharacterRecord", "TFTCharacterRecord"}:
                if "mAbilities" in value:
                    for ability_key in value["mAbilities"]:
                        characterRecordKey_abilityKey_map[ability_key] = key
            elif key != "__linked" and value["__type"] == "AbilityObject":
                abilityKey_rootSpellKey_map[value["mRootSpell"]] = key
                abilityKey_childSpellKey_map[value["mRootSpell"]] = key #部分技能对象的根技能不包含在其子技能列表中，如“Characters/Ambessa/Spells/AmbessaWAbility”（Some ability objects' root spell isn't contained in their child spell list, such as "Characters/Ambessa/Spells/AmbessaWAbility"）
                if "mChildSpells" in value:
                    for childSpell_key in value["mChildSpells"]:
                        abilityKey_childSpellKey_map[childSpell_key] = key
        # logPrint("已构建基本指令到技能的映射关系。\nFinished building the map from root spells to abilities.")
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        strtable_tft_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.tftstringtable_target
        strtable_tft_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.tftstringtable_default
        for (key1, value) in champions_bin.items():
            if key1 != "__linked" and value["__type"] in {"CharacterRecord", "TFTCharacterRecord"}: #之所以不把二者分开来放，是因为三个原因：①CharacterRecord对象和TFTCharacterRecord对象有部分重合键；②早期云顶之弈的角色对象类型仍为CharacterRecord，如“Characters/TFT3_FizzShark/CharacterRecords/Root”；③英雄联盟和云顶之弈的角色数据存放位置也是掺杂的（There're three reasons why these two value types are put together to be sorted out: ①A CharacterRecord object's keys partly overlap with a TFTCharacterRecord object's; ②The early TFT character's object type is "CharacterRecord", e.g. "Characters/TFT3_FizzShark/CharacterRecords/Root"; ③Locations of LoL and TFT character data files are usually mixed with each other）
                for i in range(len(champion_header_keys)):
                    key: str = champion_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i == 1: #模式文件夹（`modeFolder`）
                        try:
                            modeFolder = key1.split("/")[3]
                        except IndexError:
                            modeFolder = ""
                        to_append = modeFolder
                    elif i <= 143:
                        if i >= 118 and i <= 122: #技能指令对象（Spell objects）
                            if i == 118: #被动技能指令对象（`passiveObject`）
                                if "mCharacterPassiveSpell" in value:
                                    to_append = champions_bin.get(value["mCharacterPassiveSpell"], "")
                                else:
                                    to_append = ""
                            else:
                                if "spells" in value:
                                    to_append = champions_bin.get(value["spells"][i - 119], "")
                                else:
                                    to_append = ""
                        elif i >= 123 and i <= 136: #字符串常量（String constants）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                            strtable_locale_lol: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            strtable_locale_tft: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            tooltip_key: str = champion_data[subkey1][-1] #通过访问最近一次追加的数据来优化代码。代价是键必须放在值的前面（Optimize the code by accessing the recently appended data. In turn, the key must be put in front of the value）
                            use_lol_strtable: bool = True
                            if (i == 133 or i == 134) and tooltip_key == "": #不存在显示名键的情况下，尝试通过一定的模式来确定显示名（When `name` key isn't present, try determining the displayName by certain pattern）
                                if "mCharacterName" in value:
                                    tooltip_key: str = "displayName_" + value["mCharacterName"]
                                else:
                                    tooltip_key = ""
                            tooltip_raw: str = self.get_strtable_value(strtable_locale_lol, tooltip_key, default = "")
                            if tooltip_raw == "": #如果没有找到，则尝试在云顶之弈字符串常量池中寻找（If the result isn't found, then search for it in TFT stringtable）
                                tooltip_raw: str = self.get_strtable_value(strtable_locale_tft, tooltip_key, default = "")
                                if tooltip_raw != "":
                                    use_lol_strtable = False
                            if i == 127 or i == 128: #被动技能说明文本（中文/数值转换）和被动技能说明文本（英文/数值转换）（`passiveToolTip_content_zh_burn` and `passiveToolTip_content_en_burn`）
                                if "mCharacterPassiveSpell" in value:
                                    spellKey = value["mCharacterPassiveSpell"]
                                    mSpell = champions_bin[spellKey].get("mSpell")
                                    if mSpell == None:
                                        to_append = ""
                                    else:
                                        self.__class__.calculatedVariables.clear()
                                        tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale_lol if use_lol_strtable else strtable_locale_tft, mSpell, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                        to_append = tooltip_burn
                                else:
                                    to_append = ""
                            else:
                                to_append = tooltip_raw
                        elif i == 137 or i == 138: #技能本地化名称（Spell name localization）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            strtable_locale_lol: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            strtable_locale_tft: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            if "spells" in value:
                                spellNames: list[str] = []
                                for spell_key in value["spells"]:
                                    tmp_ptr: Any = champions_bin
                                    for tmp_key in [spell_key, "mSpell", "mClientData", "mTooltipData", "mLocKeys", "keyName"]:
                                        if tmp_key in tmp_ptr:
                                            tmp_ptr = tmp_ptr[tmp_key]
                                        else:
                                            spellNames.append(spell_key)
                                            break
                                    else:
                                        spellName: str = self.get_strtable_value(strtable_locale_lol, tmp_ptr, tmp_ptr)
                                        if spellName == tmp_ptr: #判断是否使用云顶之弈字符串常量池的标准应该是结果是不是等于默认值（The condition to judge whether to use TFT stringtable should be whether the result equals the default value）
                                            spellName = self.get_strtable_value(strtable_locale_tft, tmp_ptr, tmp_ptr)
                                        spellNames.append(spellName)
                                to_append = spellNames
                            else:
                                to_append = ""
                        elif i == 139 or i == 140: #角色定位本地化名称（仅云顶之弈）（CharacterRole name localization）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            if "CharacterRole" in value and value["CharacterRole"] in self.map22_bin:
                                CharacterRoleNameTra_key: str = self.map22_bin[value["CharacterRole"]]["CharacterRoleNameTra"]
                                CharacterRoleNameTra: str = self.get_strtable_value(strtable_locale, CharacterRoleNameTra_key, default = "")
                                to_append = CharacterRoleNameTra
                            else:
                                to_append = ""
                        elif i == 141: #购物数据对象（仅云顶之弈）（`ShopDataObject`）
                            if "mShopData" in value and value["mShopData"] in self.map22_bin:
                                to_append = self.map22_bin[value["mShopData"]]
                            else:
                                to_append = ""
                        elif i == 142 or i == 143: #相关羁绊本地化名称（Linked trait localized names）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            if "mLinkedTraits" in value:
                                trait_keys: list[str] = list(map(lambda x: x["TraitData"], value["mLinkedTraits"]))
                                traitDisplayNameTra_list: list[str] = []
                                for trait_key in trait_keys:
                                    if trait_key in self.map22_bin and "mDisplayNameTra" in self.map22_bin[trait_key]:
                                        traitDisplayNameTra_key: str = self.map22_bin[trait_key]["mDisplayNameTra"]
                                        traitDisplayNameTra: str = self.get_strtable_value(strtable_locale, traitDisplayNameTra_key, default = "")
                                        traitDisplayNameTra_list.append(traitDisplayNameTra)
                                    else:
                                        traitDisplayNameTra_list.append(trait_key)
                                to_append = traitDisplayNameTra_list
                            else:
                                to_append = ""
                        else:
                            if i in {12, 18, 68, 80, 83, 105, 112, 113, 115, 117}:
                                defaultValue: str | bool = False
                            elif i == 111: #使用法术强度（仅云顶之弈）（`mUsesAbilityPower`）
                                defaultValue = value["__type"] == "TFTCharacterRecord"
                            else:
                                defaultValue = ""
                            to_append = value.get(key, defaultValue)
                    else:
                        subkeyList: list[str] = key.split()
                        if i >= 176 and i <= 181 or i == 268 or i == 269: #字符串常量（String constants）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            locale: str = self.locale if useTargetLocale else self.DEFAULT_LOCALE
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            complex_tooltip_key: str | list[str] = champion_data[subkey1][-1]
                            if i in {176, 177, 268, 269}: #说明文本单值（Single tooltip value）
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, complex_tooltip_key, default = "")
                                to_append = tooltip_raw
                            else: #说明文本列表（Tooltip value list）
                                if complex_tooltip_key == "":
                                    to_append = ""
                                else:
                                    tooltips_raw: list[str] = list(map(lambda x: self.get_strtable_value(strtable_locale, x, default = ""), complex_tooltip_key))
                                    if i == 178 or i == 179: #技能进化说明文本（中文）和技能进化说明文本（英文）（`evolutionData mTooltips_content_zh` and `evolutionData mTooltips_content_en`）
                                        to_append = tooltips_raw
                                    else: #技能进化说明文本（中文/数值转换）和技能进化说明文本（英文/数值转换）（`evolutionData mTooltips_content_zh_burn` and `evolutionData mTooltips_content_en_burn`）
                                        tooltips_burn: list[str] = []
                                        for j in range(len(tooltips_raw)):
                                            tooltip_raw = tooltips_raw[j]
                                            mSpell = champions_bin[value["spells"][j]].get("mSpell") if value["spells"][j] in champions_bin else None
                                            if mSpell == None:
                                                tooltips_burn.append("")
                                            else:
                                                self.__class__.calculatedVariables.clear()
                                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, locale, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                                tooltips_burn.append(tooltip_burn)
                                        to_append = tooltips_burn
                        else:
                            tmp_ptr = value
                            for j in range(len(subkeyList)):
                                tmp_key = subkeyList[j]
                                if tmp_key in tmp_ptr:
                                    tmp_ptr = tmp_ptr[tmp_key]
                                else:
                                    if i in {166, 193, 196, 208, 218, 258}:
                                        defaultValue: str | bool = value["__type"] == "CharacterRecord"
                                    elif i in {194, 195, 209, 215, 216, 217, 256, 257}:
                                        defaultValue = False
                                    else:
                                        defaultValue = ""
                                    to_append = defaultValue
                                    break
                            else:
                                to_append = tmp_ptr
                    champion_data[key].append(to_append)
                    champion_data_json[key].append(pyobj2json(to_append))
                # logPrint("[%d/%d]已整理角色对象（Organized character record）： %s" %(count, len(champions_bin.items()), key1), print_time = True)
            elif key1 != "__linked" and value["__type"] == "SpellObject":
                for i in range(len(champion_spell_header_keys)):
                    key: str = champion_spell_header_keys[i]
                    if i <= 7: #主键衍生键（`key`-derivated keys）
                        if i == 0: #角色名称（`mCharacterName`）
                            if key1 in abilityKey_childSpellKey_map and abilityKey_childSpellKey_map[key1] in characterRecordKey_abilityKey_map:
                                characterRecord_key: str = characterRecordKey_abilityKey_map[abilityKey_childSpellKey_map[key1]]
                                to_append = champions_bin[characterRecord_key]["mCharacterName"]
                            else:
                                to_append = ""
                        elif i == 1: #根技能（`isRootSpell`）
                            to_append = key1 in abilityKey_rootSpellKey_map
                        elif i <= 6:
                            subkey = key.split("_")[1]
                            if key1 in abilityKey_childSpellKey_map:
                                parentAbility: dict[str, Any] = champions_bin[abilityKey_childSpellKey_map[key1]]
                                if subkey in parentAbility:
                                    to_append = parentAbility[subkey]
                                else:
                                    if i == 3: #所属技能的持续时间可控制（`rootAbility_mLifetimeManuallyManaged`）
                                        to_append = False
                                    else:
                                        to_append = ""
                            else:
                                if i == 3: #所属技能的持续时间可控制（`rootAbility_mLifetimeManuallyManaged`）
                                    to_append = False
                                else:
                                    to_append = ""
                        else: #技能热键（`spellHotKey`）
                            if key1 in abilityKey_childSpellKey_map:
                                parentAbility_key: str = abilityKey_childSpellKey_map[key1]
                                rootSpell_key: str = champions_bin[parentAbility_key]["mRootSpell"]
                                if parentAbility_key in characterRecordKey_abilityKey_map:
                                    CharacterRecordRoot_key: str = characterRecordKey_abilityKey_map[parentAbility_key]
                                    CharacterRecordRoot: dict[str, Any] = champions_bin[CharacterRecordRoot_key]
                                    if "mCharacterPassiveSpell" in CharacterRecordRoot and CharacterRecordRoot["mCharacterPassiveSpell"] == rootSpell_key:
                                        to_append = "P"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][0] == rootSpell_key:
                                        to_append = "Q"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][1] == rootSpell_key:
                                        to_append = "W"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][2] == rootSpell_key:
                                        to_append = "E"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][3] == rootSpell_key: #经检验，所有有“spells”键的角色记录对象的spells键的值列表长度恒为4（After examination, the length of the value list of existing "spells" key of all CharacterRecord objects is always 4）
                                        to_append = "R"
                                    else:
                                        to_append = ""
                                else:
                                    to_append = ""
                            else:
                                to_append = ""
                    else:
                        to_append = self.generate_spell_record(champion_spell_data, key, key1, value)
                    champion_spell_data[key].append(to_append)
                    champion_spell_data_json[key].append(pyobj2json(to_append))
            #     logPrint("[%d/%d]已整理指令对象（Organized spell object）： %s" %(count, len(champions_bin.items()), key1), print_time = True)
            # else:
            #     logPrint("[%d/%d]已跳过键（Skipped key）： %s" %(count, len(champions_bin.items()), key1), print_time = True)

        #数据框构建和排序（Build the dataframe and sort the keys and values）
        ##英雄（Champion）
        if self.useAllCharacter:
            if Patch(self.patch_number) < Patch("16.5"): #26.05版本调整了所有基础属性键（All base stat keys are adjusted in Patch 26.05）
                champion_statistics_output_order: list[int] = [0, 1, 2, 62, 133, 134, 3, 61, 222, 80, 230, 246, 247, 73, 84, 19, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 20, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 64, 135, 136, 8, 9, 21, 22, 23, 24, 26, 28, 33, 35, 34, 30, 10, 11, 32, 27, 25, 29, 37, 91, 79, 232, 223, 220, 221, 240, 226, 231, 229, 225, 228, 233, 237, 216, 234, 235, 238, 239, 211, 212, 217, 218, 214, 215, 219, 224, 213, 241, 242, 243, 244, 245, 227, 236, 86, 88, 42, 43, 85, 12, 14, 15, 16, 17, 13, 18, 69, 70, 71, 72, 38, 44, 66, 57, 58, 39, 202, 203, 204, 205, 206, 207, 208, 40, 41, 50, 36, 65, 63, 68, 31, 83, 4, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 7, 167, 168, 169, 170, 51, 123, 124, 52, 54, 89, 55, 118, 53, 125, 127, 126, 128, 90, 56, 49, 78, 81, 82, 45, 46, 137, 138, 119, 120, 121, 122, 47, 48, 67, 5, 6, 157, 158, 161, 162, 159, 163, 165, 164, 166, 160, 77, 209, 210, 59, 129, 130, 60, 131, 132, 74, 75, 76, 87, 92, 104, 106, 117, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 105, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 139, 140, 141, 142, 143]
            else:
                champion_statistics_output_order = [0, 1, 2, 62, 133, 134, 3, 61, 244, 80, 252, 268, 269, 73, 84, 19, 186, 198, 199, 200, 201, 191, 192, 193, 194, 195, 196, 197, 20, 202, 221, 222, 223, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 64, 135, 136, 144, 145, 148, 149, 150, 151, 152, 153, 156, 158, 157, 154, 146, 147, 155, 27, 25, 29, 37, 91, 79, 254, 245, 242, 243, 262, 248, 253, 251, 247, 250, 255, 259, 238, 256, 257, 260, 261, 233, 234, 239, 240, 236, 237, 241, 246, 235, 263, 264, 265, 266, 267, 249, 258, 86, 88, 42, 43, 85, 12, 14, 15, 16, 17, 13, 18, 69, 70, 71, 72, 38, 44, 66, 57, 58, 39, 224, 225, 226, 227, 228, 229, 230, 40, 41, 50, 36, 65, 63, 68, 31, 83, 4, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 7, 182, 183, 184, 185, 51, 123, 124, 52, 54, 89, 55, 118, 53, 125, 127, 126, 128, 90, 56, 49, 78, 81, 82, 45, 46, 137, 138, 119, 120, 121, 122, 47, 48, 67, 5, 6, 172, 173, 176, 177, 174, 178, 180, 179, 181, 175, 77, 231, 232, 59, 129, 130, 60, 131, 132, 74, 75, 76, 87, 92, 104, 106, 117]
        else:
            if Patch(self.patch_number) < Patch("16.5"):
                champion_statistics_output_order = [0, 1, 2, 62, 133, 134, 3, 61, 222, 80, 230, 246, 247, 73, 84, 19, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 20, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 64, 135, 136, 8, 9, 21, 22, 23, 24, 26, 28, 33, 35, 34, 30, 10, 11, 32, 27, 25, 29, 37, 91, 79, 232, 223, 220, 221, 240, 226, 231, 229, 225, 228, 233, 237, 216, 234, 235, 238, 239, 211, 212, 217, 218, 214, 215, 219, 224, 213, 241, 242, 243, 244, 245, 227, 236, 86, 88, 42, 43, 85, 12, 14, 15, 16, 17, 13, 18, 69, 70, 71, 72, 38, 44, 66, 57, 58, 39, 202, 203, 204, 205, 206, 207, 208, 40, 41, 50, 36, 65, 63, 68, 31, 83, 4, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 7, 167, 168, 169, 170, 51, 123, 124, 52, 54, 89, 55, 118, 53, 125, 127, 126, 128, 90, 56, 49, 78, 81, 82, 45, 46, 137, 138, 119, 120, 121, 122, 47, 48, 67, 5, 6, 157, 158, 161, 162, 159, 163, 165, 164, 166, 160, 77, 209, 210, 59, 129, 130, 60, 131, 132, 74, 75, 76, 87, 92, 104, 106, 117]
            else:
                champion_statistics_output_order = [0, 1, 2, 62, 133, 134, 3, 61, 244, 80, 252, 268, 269, 73, 84, 19, 186, 198, 199, 200, 201, 191, 192, 193, 194, 195, 196, 197, 20, 202, 221, 222, 223, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 64, 135, 136, 144, 145, 148, 149, 150, 151, 152, 153, 156, 158, 157, 154, 146, 147, 155, 27, 25, 29, 37, 91, 79, 254, 245, 242, 243, 262, 248, 253, 251, 247, 250, 255, 259, 238, 256, 257, 260, 261, 233, 234, 239, 240, 236, 237, 241, 246, 235, 263, 264, 265, 266, 267, 249, 258, 86, 88, 42, 43, 85, 12, 14, 15, 16, 17, 13, 18, 69, 70, 71, 72, 38, 44, 66, 57, 58, 39, 224, 225, 226, 227, 228, 229, 230, 40, 41, 50, 36, 65, 63, 68, 31, 83, 4, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 7, 182, 183, 184, 185, 51, 123, 124, 52, 54, 89, 55, 118, 53, 125, 127, 126, 128, 90, 56, 49, 78, 81, 82, 45, 46, 137, 138, 119, 120, 121, 122, 47, 48, 67, 5, 6, 172, 173, 176, 177, 174, 178, 180, 179, 181, 175, 77, 231, 232, 59, 129, 130, 60, 131, 132, 74, 75, 76, 87, 92, 104, 106, 117, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 105, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 139, 140, 141, 142, 143]
        champion_data_organized: dict[str, list[Any]] = {champion_header_keys[i]: champion_data_json[champion_header_keys[i]] for i in champion_statistics_output_order}
        champion_df: pandas.DataFrame = pandas.DataFrame(data = champion_data_organized)
        champion_df = champion_df.sort_values(by = "mCharacterName" if self.useAllCharacter else "characterToolData championId", ascending = True, ignore_index = True) #原来读取文件的顺序是英雄别名顺序，合并后的顺序是打乱后的顺序。因为这两种顺序都不太符合设计初衷（对于前者，试想虚空遁地兽 雷克塞和兽灵行者 乌迪尔中间掺和了一堆末日人机英雄），所以索性就用了英雄序号作为排序标准【Originally, the order to read files follows that of aliases, and the order of champions after being merged is shuffled. Because both orders don't accord to the intuitive intent by design (for the former order, think about those ruby champions between Rek'Sai and Udyr), championId is used here as the sorting criterium】
        logPrint("正在优化英雄数据框的逻辑值显示……\nOptimizing boolean value display of the champion dataframe ...")
        optimize_bool_display(champion_df)
        champion_df = pandas.concat([pandas.DataFrame([champion_header])[champion_df.columns], champion_df], ignore_index = True)
        self.champion_df = champion_df
        ##法术（Spell）
        champion_spell_statistics_output_order: list[int] = [8, 9, 0, 7, 269, 291, 292, 2, 1, 4, 5, 6, 3, 11, 12, 10, 24, 13, 14, 15, 25, 106, 121, 235, 237, 238, 70, 236, 47, 48, 49, 30, 40, 71, 52, 66, 67, 68, 29, 69, 72, 26, 27, 28, 31, 234, 32, 33, 239, 207, 127, 134, 135, 128, 61, 62, 63, 98, 129, 130, 43, 46, 208, 131, 132, 133, 100, 101, 50, 51, 54, 55, 56, 57, 53, 22, 23, 102, 107, 16, 17, 59, 19, 18, 20, 21, 39, 58, 60, 64, 65, 44, 45, 91, 83, 84, 94, 95, 75, 74, 80, 112, 77, 78, 79, 96, 99, 73, 76, 255, 86, 81, 82, 97, 89, 90, 85, 87, 88, 92, 110, 120, 93, 257, 258, 259, 108, 123, 122, 124, 126, 254, 240, 241, 242, 243, 244, 245, 246, 34, 35, 36, 37, 103, 253, 105, 119, 109, 218, 219, 111, 114, 113, 115, 118, 116, 117, 125, 136, 223, 104, 224, 226, 225, 229, 230, 233, 247, 251, 252, 256, 260, 262, 261, 329, 330, 263, 264, 265, 266, 281, 282, 270, 275, 307, 309, 308, 310, 278, 319, 321, 320, 322, 273, 301, 302, 274, 303, 305, 304, 306, 276, 311, 313, 312, 314, 277, 315, 317, 316, 318, 279, 323, 325, 324, 326, 280, 327, 328, 267, 283, 285, 284, 286, 268, 287, 289, 288, 290, 271, 293, 295, 294, 296, 272, 297, 299, 298, 300, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 221, 41, 38, 42, 341, 342, 344, 345, 356, 346, 347, 361, 362, 343, 357, 359, 358, 360, 349, 367, 369, 368, 370, 350, 371, 373, 372, 374, 348, 363, 364, 365, 366, 351, 352, 353, 354, 355, 209, 210, 211, 212, 213, 214, 215, 216, 217, 137, 185, 141, 139, 142, 143, 138, 140, 231, 232, 144, 145, 147, 148, 149, 150, 151, 152, 146, 153, 154, 155, 156, 157, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 183, 158, 184, 174, 175, 176, 177, 178, 179, 180, 181, 182, 186, 193, 187, 188, 189, 190, 191, 192, 203, 194, 195, 196, 197, 198, 199, 200, 201, 202, 204, 205, 206, 227, 228, 220, 222, 248, 249, 250, 375, 376, 377, 378, 379]
        champion_spell_data_organized: dict[str, list[Any]] = {champion_spell_header_keys[i]: champion_spell_data_json[champion_spell_header_keys[i]] for i in champion_spell_statistics_output_order}
        champion_spell_df: pandas.DataFrame = pandas.DataFrame(data = champion_spell_data_organized)
        logPrint("正在排序英雄技能数据框……\nOrganizing champion spell dataframe ...")
        champion_spell_df_keys_ordered = []
        for i in range(1, len(champion_df)): #根据英雄数据框排序后的英雄顺序读取其技能，使得这些技能总是位于英雄技能数据框的顶部（Read the abilities of champions which follow the order in the champion dataframe to make champion abilities always in the front of the champion spell dataframe）
            mAbilities_str: str = champion_df["mAbilities"][i]
            if mAbilities_str != "":
                mAbilities: list[str] = eval(mAbilities_str)
                for ability_key in mAbilities:
                    if ability_key in champions_bin:
                        abilityObj: dict[str, Any] = champions_bin[ability_key]
                        if "mChildSpells" in abilityObj:
                            if not abilityObj["mRootSpell"] in abilityObj["mChildSpells"]:
                                champion_spell_df_keys_ordered.append(abilityObj["mRootSpell"])
                            champion_spell_df_keys_ordered += abilityObj["mChildSpells"]
                        else:
                            champion_spell_df_keys_ordered.append(abilityObj["mRootSpell"])
        for key in champion_spell_data["key"]:
            if not key in champion_spell_df_keys_ordered: #非英雄技能指令按照其键在champions_bin的出现顺序依次追加到顺序列表最后（Non-champion spells are appended to the end of the ordered list one by one, in the order of their occurrences in `champions_bin`'s keys）
                champion_spell_df_keys_ordered.append(key)
        spell_status_order = {champion_spell_df_keys_ordered[i]: i for i in range(len(champion_spell_df_keys_ordered))} #定义权重列表（Define the status dict）
        champion_spell_df = champion_spell_df.sort_values(by = "key", key = lambda x: x.map(spell_status_order), ascending = True, ignore_index = True)
        logPrint("正在优化英雄技能数据框的逻辑值显示……\nOptimizing boolean value display of the champion spell dataframe ...")
        optimize_bool_display(champion_spell_df)
        champion_spell_df = pandas.concat([pandas.DataFrame([champion_spell_header])[champion_spell_df.columns], champion_spell_df], ignore_index = True)
        self.champion_spell_df = champion_spell_df
        return 0
    
    def enqueue_champion_dataframe(self) -> None:
        '''
        将角色数据框追加到数据提取器基类的数据框队列尾部。<br>Append character dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.champion_df.empty:
            champion_ws: dict[str, Any] = self.worksheet_metadata["Character"] if self.useAllCharacter else self.worksheet_metadata["Champion"]
            sheet1_name: str = champion_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else champion_ws["sheet_name_without_version"]
            champion_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(champion_ws["dType"]), "dType": champion_ws["dType"], "sheet_name": sheet1_name, "sheet": self.champion_df}
            self.enqueue_df(champion_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.champion_spell_df.empty:
            champion_spell_ws: dict[str, Any] = self.worksheet_metadata["CharacterSpell"] if self.useAllCharacter else self.worksheet_metadata["ChampionSpell"]
            sheet2_name: str = champion_spell_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else champion_spell_ws["sheet_name_without_version"]
            champion_spell_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(champion_spell_ws["dType"]), "dType": champion_spell_ws["dType"], "sheet_name": sheet2_name, "sheet": self.champion_spell_df}
            self.enqueue_df(champion_spell_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_champion_data(self, debug: bool = False, paths: Optional[list[str]] = None, verbose: bool = True) -> None:
        '''
        导出英雄数据到工作簿中。<br>Export champion data to a workbook.
        
        在导出所有角色数据时，产生以下工作表：<br>When all character data are exported, the following worksheets are added:
        - 角色（Characters）
        - 角色技能（Character Spells）
        
        在仅导出英雄数据时，产生以下工作表：<br>When only champion data are exported, the following worksheets are added:
        - 英雄（Champions）
        - 英雄技能（Champion Spells）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 当使用所有角色数据时，`paths`由以下部分组成：<br>When all characters' data are used, `paths` is a list composed of the following content:
        
            - 聚点危机地图二进制描述文件路径（Convergence map binary description file path）
            - 角色文件夹1路径（Character folder 1 path）： game/data/characters
            - 角色文件夹2路径（Character folder 2 path）： game/characters
            
            当仅使用英雄数据时，`paths`由以下部分组成：<br>When only champions' data are used, `paths` is a list composed of the following content:
            - 英雄概要文件路径（Champion summary file path）
            - 角色文件夹路径（Character folder path）： game/data/characters

            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        :param verbose: 是否打印过程性信息。默认为是。<br>Whether to print the progress. True by default.
        :type verbose: bool
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径。\nPath of exported file not specified.")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if self.champion_df.empty or self.champion_spell_df.empty:
            status: int = self.build_champion_dataframe(debug = debug, paths = paths, verbose = verbose)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            champion_df: pandas.DataFrame = eliminate_empty_fields(self.champion_df)
            champion_spell_df: pandas.DataFrame = eliminate_empty_fields(self.champion_spell_df)
        else:
            champion_df = self.champion_df
            champion_spell_df = self.champion_spell_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name1: str = self.worksheet_metadata["Character"]["sheet_name_without_version"] if self.useAllCharacter else self.worksheet_metadata["Champion"]["sheet_name_without_version"]
        sheet1_name2: str = self.worksheet_metadata["Character"]["sheet_name_with_version"] if self.useAllCharacter else self.worksheet_metadata["Champion"]["sheet_name_with_version"]
        sheet2_name1: str = self.worksheet_metadata["CharacterSpell"]["sheet_name_without_version"] if self.useAllCharacter else self.worksheet_metadata["ChampionSpell"]["sheet_name_without_version"]
        sheet2_name2: str = self.worksheet_metadata["CharacterSpell"]["sheet_name_with_version"] if self.useAllCharacter else self.worksheet_metadata["ChampionSpell"]["sheet_name_with_version"]
        sheet1_name: str = sheet1_name2 if self.sheet_naming_fold else sheet1_name1
        sheet2_name: str = sheet2_name2 if self.sheet_naming_fold else sheet2_name1
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(champion_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(champion_spell_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
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
                logPrint(f"英雄数据已导出到{self.wbPath}。\nChampion data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, paths: Optional[list[str]] = None, verbose: bool = True) -> None:
        '''
        导出英雄数据到网页中。产生以下文件：<br>Export champion data into an html file. The following file is produced:
        
        在导出所有角色数据时，产生以下文件：<br>When all character data are exported, the following files are produced:
        - 角色（Characters）
        - 角色技能（Character Spells）
        
        在仅导出英雄数据时，产生以下工作表：<br>When only champion data are exported, the following files are produced:
        - 英雄（Champions）
        - 英雄技能（Champion Spells）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 当使用所有角色数据时，`paths`由以下部分组成：<br>When all characters' data are used, `paths` is a list composed of the following content:
        
            - 聚点危机地图二进制描述文件路径（Convergence map binary description file path）
            - 角色文件夹1路径（Character folder 1 path）： game/data/characters
            - 角色文件夹2路径（Character folder 2 path）： game/characters
            
            当仅使用英雄数据时，`paths`由以下部分组成：<br>When only champions' data are used, `paths` is a list composed of the following content:
            - 英雄概要文件路径（Champion summary file path）
            - 角色文件夹路径（Character folder path）： game/data/characters

            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        :param verbose: 是否打印过程性信息。默认为是。<br>Whether to print the progress. True by default.
        :type verbose: bool
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径。\nPath of exported file not specified.")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if self.champion_df.empty or self.champion_spell_df.empty or not self.champions_ready["summary"]: #下面在整理角色信息时需要把英雄放到最前面，所以需要用到概要信息（In the following code, champions are put in the front of the dataframe, so champion summary information is required）
            status: int = self.build_champion_dataframe(debug = debug, paths = paths, verbose = verbose)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #角色技能（Character spell）
        if len(self.champion_spell_df) > 1:
            champion_spell_df_web: pandas.DataFrame = self.champion_spell_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            imgIconUrls: list[str] = list(map(lambda x: "" if x == "" else "<br>".join(list(map(lambda y: self.url2image(self.assetPath2url(self.version, f"DATA/Spells/Icons2D/{y}" if not "/" in y else y)), eval(x)))), self.champion_spell_df.loc[1:, "mSpell mImgIconName"].to_list()))
            champion_spell_df_web.insert(len(champion_spell_df_web.columns), "mSpell ImgIconUrl", ["缩略图网址列表"] + imgIconUrls)
            ##保留小数（Round）
            champion_spell_df_web.loc[1:, "mSpell Cooldown {0a3e0478}"] = champion_spell_df_web.loc[1:, "mSpell Cooldown {0a3e0478}"].apply(lambda x: "" if x == "" else self.aRound(x, 5))
            ##排序（Order）
            ###第一关键字——英雄文件夹（Primary keyword - championFolder）
            championFolder_ordered: list[str] = sorted(set(champion_spell_df_web["mCharacterName"][1:].to_list())) #期望的排序后的英雄文件夹（Expected ordered championFolders）
            championFolder_champion: list[str] = [] #排序后的英雄文件夹的英雄部分（The champion part of the ordered championFolders）
            championFolder_TFT: list[str] = [] #排序后的英雄文件夹的弈子部分（The TFT champion part of the ordered championFolders）
            championFolder_ruby: list[str] = [] #排序后的英雄文件夹的末日人工智能英雄部分（The Doom Bots champion part of the ordered championFolders）
            championFolder_jade: list[str] = [] #排序后的英雄文件夹的经典英雄部分（The classic champion part of the ordered championFolders）
            championFolder_empty: list[str] = [] #排序后的英雄文件夹的空字符串部分（The empty string part of the ordered championFolders）
            championFolder_other: list[str] = [] #排序后的英雄文件夹的其它部分（Other part of the ordered championFolders）
            for alias in championFolder_ordered:
                if alias.startswith("TFT"):
                    championFolder_TFT.append(alias)
                elif alias.startswith("Ruby_"):
                    championFolder_ruby.append(alias)
                elif alias.startswith("Jade_"):
                    championFolder_jade.append(alias)
                elif alias in set(map(lambda x: x["alias"], self.champion_summary)):
                    championFolder_champion.append(alias)
                elif alias == "":
                    championFolder_empty.append(alias)
                else:
                    championFolder_other.append(alias)
            championFolder_ordered = championFolder_champion + championFolder_ruby + championFolder_jade + championFolder_TFT + championFolder_other + championFolder_empty
            championFolder_weight_map: dict[str, int] = {_: championFolder_ordered.index(_) for _ in championFolder_ordered}
            ###第二关键字——技能热键（Secondary keyword - spellHotKey）
            spellHotKey_weight_map: dict[str, int] = {"P": 0, "Q": 1, "W": 2, "E": 3, "R": 4, "": 5}
            ###插入关键字权重列（Insert keyword weight columns）
            championFolder_weights: list[int] = list(map(lambda x: championFolder_weight_map[x], champion_spell_df_web["mCharacterName"][1:].to_list()))
            champion_spell_df_web.insert(len(champion_spell_df_web.columns), "championFolder_weight", ["英雄文件夹权重"] + championFolder_weights)
            spellHotKey_weights: list[int] = list(map(lambda x: spellHotKey_weight_map[x], champion_spell_df_web["spellHotKey"][1:].to_list()))
            champion_spell_df_web.insert(len(champion_spell_df_web.columns), "spellHotKey_weight", ["技能热键权重"] + spellHotKey_weights)
            ###排序重组（Sort and recombination）
            champion_spell_df_web = pandas.concat([champion_spell_df_web.iloc[:1, :], champion_spell_df_web.iloc[1:, :].sort_values(by = ["championFolder_weight", "spellHotKey_weight", "key"], ascending = True)])
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "mCharacterName",
                "ObjectName",
                "spellHotKey",
                "mSpell ImgIconUrl",
                "mSpell mClientData mTooltipData mLocKeys keyName_content_zh_burn",
                "mSpell mClientData mTooltipData mLocKeys keyName_content_en_burn",
                "mSpell {210f9ec0} values",
                "mSpell Cooldown values",
                "mSpell mClientData mTooltipData mLocKeys keySummary_content_zh",
                "mSpell mClientData mTooltipData mLocKeys keySummary_content_en",
                "mSpell mClientData mTooltipData mLocKeys keyTooltip_content_zh_burn",
                "mSpell mClientData mTooltipData mLocKeys keyTooltip_content_en_burn",
                "mSpell mClientData mTooltipData mLocKeys keyTooltipExtendedBelowLine_content_zh_burn",
                "mSpell mClientData mTooltipData mLocKeys keyTooltipExtendedBelowLine_content_en_burn"
            ]
            champion_spell_df_web = champion_spell_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            champion_spell_df_styled: pandas.io.formats.style.Styler = champion_spell_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:8]
            champion_spell_df_styled = champion_spell_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            champion_spell_htmltable: str = champion_spell_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            champion_spell_htmltable = '<meta charset="UTF-8">\n' + champion_spell_htmltable
            webContent: str = "CharacterSpell" if self.useAllCharacter else "ChampionSpell"
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"{webContent}_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(champion_spell_htmltable)
