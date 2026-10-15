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
from src.core.config.headers import progressTrack_header, KiwiProgressTrack_header, rewardGroup_header, KiwiReward_header, KiwiQuest_header, KiwiMission_header, KiwiQuestMilestone_header
from src.core.extractor.base import LoLDataExtractor

class MissionExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个任务提取器对象。<br>Initialize a MissionExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.missions_ready: dict[str, bool] = {"map453": False, "map12": False}
        self.KiwiProgressTrack_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiRewardGroup_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiReward_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiQuest_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiMission_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiQuestMilestone_df: pandas.DataFrame = pandas.DataFrame()
        self.JadeProgressTrack_df: pandas.DataFrame = pandas.DataFrame()
        self.JadeRewardGroup_df: pandas.DataFrame = pandas.DataFrame()
    
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.missions_ready = {key: False for key in self.missions_ready}
    
    def get_mission_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取任务二进制描述数据。包括以下游戏模式：<br>Get binary description data of missions online. Including the following game modes:
        - 英雄联盟经典模式（League Classic）
        - 海克斯大乱斗（ARAM: Mayhem）
        '''
        logPrint = self.log.logPrint
        #经典召唤师峡谷（Classic Rift）
        map453_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map453/map453.bin.json"
        if map453_bin_url in self.__class__.data_cache["online"]:
            self.map453_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["online"][map453_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map453_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("经典召唤师峡谷地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nClassic Rift map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map453_bin_url))
                else:
                    logPrint("经典召唤师峡谷地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nClassic Rift map data capture failure! Please check the system network condition and proxy configuration. The program will return to the last step soon.")
                time.sleep(3)
                self.init_data_readiness()
                return
            else:
                self.map453_bin = source.json()
                self.map453_bin = self.resolve_bin_hash(self.map453_bin)
            self.__class__.data_cache["online"][map453_bin_url] = self.map453_bin
        self.missions_ready["map453"] = True
        #嚎哭深渊地图（Howling Abyss map）
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
        self.missions_ready["map12"] = True
    
    def read_mission_data(self, paths: list[str]) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取任务二进制描述数据。<br>Get binary description data of missions offline.
        
        :param path: 任务二进制描述文件的本地路径，按照以下顺序排列：<br>The local path of mission binary description files, arranged in the following order:
        
            - 经典召唤师峡谷地图（Classic Rift map）
            - 嚎哭深渊地图（Howling Abyss map）
        :type path: str
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
        #经典召唤师峡谷地图（Classic Rift map）
        map453_bin_path: str = paths[0]
        if map453_bin_path in self.__class__.data_cache["local"]:
            self.map453_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map453_bin_path]
        else:
            with open(map453_bin_path, "r", encoding = "utf-8") as fp:
                self.map453_bin = json.load(fp)
            self.map453_bin = self.resolve_bin_hash(self.map453_bin)
            self.__class__.data_cache["local"][map453_bin_path] = self.map453_bin
        self.missions_ready["map453"] = True
        #嚎哭深渊地图（Howling Abyss map）
        map12_bin_path: str = paths[1]
        if map12_bin_path in self.__class__.data_cache["local"]:
            self.map12_bin: dict[str, list[str] | dict[str, Any]] = self.__class__.data_cache["local"][map12_bin_path]
        else:
            with open(map12_bin_path, "r", encoding = "utf-8") as fp:
                self.map12_bin = json.load(fp)
            self.map12_bin = self.resolve_bin_hash(self.map12_bin)
            self.__class__.data_cache["local"][map12_bin_path] = self.map12_bin
        self.missions_ready["map12"] = True

    def generate_progressTrack_record(self, source: dict[str, list[str] | dict[str, Any]], field: str, key: str, value: dict[str, Any], milestoneDefinition_index: int = 0) -> Any:
        '''
        生成一个进度追踪字段的值。<br>Generate the value of a progress track field.
        
        :param source: 原始二进制描述数据。<br>Original binary description data.
        :type source: dict[str, list[str] | dict[str, Any]]
        :param field: 字段。<br>Field.
        :type field: str
        :param key: 一个进度追踪数据对象的键。<br>A `ProgressTrack` object's key.
        :type key: str
        :param value: 一个进度追踪数据对象的值。<br>A `ProgressTrack` object's value.
        :type value: dict[str, Any]
        :param milestoneDefinition_index: 里程碑下标。默认是0。<br>Milestone index. 0 by default.
        
            默认值用于在进度追踪数据中没有“MilestoneDefinitions”键时节省参数。<br>The default value is used to omit parameters when progress track data don't have "MilestoneDefinitions" key.
        :type milestoneDefinition_index: int
        :return: 待追加的值。<br>Value to be appended.
        
            之所以要显式返回这个值，是为了方便在形如`_data_json`的字典中追加文本化的值。文本化指的是通过调用`pyobj2json`方法，将列表和字典转化为JSON字符串的形式。<br>The reason why this value is explicitly returned is to facilitate the appending of textualized values in dictionaries like `_data_json`. Textualization refers to the conversion of lists and dictionaries into JSON strings by calling the `pyobj2json` method.
        :rtype: Any
        '''
        progressTrack_header_keys: list[str] = list(progressTrack_header.keys())
        i: int = progressTrack_header_keys.index(field)
        #数据整理核心部分（Data organization core part）
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        if i == 0: #主键（`key`）
            to_append: Any = key
        elif i <= 4:
            if i == 4: #计数器定义列表（`CounterDefinitions_content`）
                to_append = list(map(lambda x: source.get(x, x), value["CounterDefinitions"]))
            else:
                to_append = value[field]
        else:
            if "MilestoneDefinitions" in value:
                milestoneDefinition_key: str = value["MilestoneDefinitions"][milestoneDefinition_index]
                if i == 5: #里程碑定义序号（`MilestoneDefinition_index`）
                    to_append = milestoneDefinition_index + 1
                elif i == 6: #里程碑定义主键（`MilestoneDefinition_key`）
                    to_append = milestoneDefinition_key
                else:
                    if milestoneDefinition_key in source:
                        milestone: dict[str, Any] = source[milestoneDefinition_key]
                        if i <= 11:
                            to_append = milestone[field.split()[1]]
                        elif i <= 13: #奖励分组名称字符串常量（Reward group name string constant）
                            useTargetLocale: bool = field.split("_")[2] == "zh"
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            rewardGroup_names: list[str] = []
                            for rewardGroup_key in milestone["properties"]:
                                if rewardGroup_key in source:
                                    tooltip_key: str = self.aGet(source[rewardGroup_key], ["LocalizedName", "internalName", "ID"], "")
                                    rewardGroup_name: str = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                    rewardGroup_names.append(rewardGroup_name)
                                else:
                                    rewardGroup_names.append("")
                            to_append = rewardGroup_names
                        elif i <= 15: #里程碑奖励字符串常量（Milestone reward string constant）
                            useTargetLocale: bool = field.split("_")[2] == "zh"
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            rewards: list[list[str]] = []
                            for rewardGroup_key in milestone["properties"]:
                                reward_names: list[str] = []
                                if rewardGroup_key in source:
                                    for reward in source[rewardGroup_key]["rewards"]:
                                        tooltip_key: str = self.aGet(reward, ["{31c5f01c}", "itemID"], "")
                                        reward_name: str = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                        reward_names.append(reward_name)
                                rewards.append(reward_names)
                            to_append = rewards
                        else:
                            counter_key: str = milestone["Counter"]
                            to_append = source[counter_key][field.split()[2]] if counter_key in source else ""
                    else: #里程碑计数器子键（`MilestoneDefinition Counter`'s subkeys）
                        to_append = ""
            else:
                to_append = ""
        return to_append
    
    def generate_rewardGroup_record(self, source: dict[str, list[str] | dict[str, Any]], data_ref: dict[str, list[Any]], field: str, key: str, value: dict[str, Any], reward_index: int) -> Any:
        '''
        生成一个奖励分组字段的值。<br>Generate the value of a reward group field.
        
        :param source: 原始二进制描述数据。<br>Original binary description data.
        :type source: dict[str, list[str] | dict[str, Any]]
        :param data_ref: 待追加值的字典的引用。<br>Reference to the dictionary to be appended with values.
        :type data_ref: dict[str, list[Any]]
        :param field: 字段。<br>Field.
        :type field: str
        :param key: 一个奖励分组数据对象的键。<br>A `RewardGroup` object's key.
        :type key: str
        :param value: 一个奖励分组数据对象的值。<br>A `RewardGroup` object's value.
        :type value: dict[str, Any]
        :param reward_index: 奖励下标。<br>Reward index.
        :type reward_index: int
        :return: 待追加的值。<br>Value to be appended.
        
            之所以要显式返回这个值，是为了方便在形如`_data_json`的字典中追加文本化的值。文本化指的是通过调用`pyobj2json`方法，将列表和字典转化为JSON字符串的形式。<br>The reason why this value is explicitly returned is to facilitate the appending of textualized values in dictionaries like `_data_json`. Textualization refers to the conversion of lists and dictionaries into JSON strings by calling the `pyobj2json` method.
        :rtype: Any
        '''
        rewardGroup_header_keys: list[str] = list(rewardGroup_header.keys())
        i: int = rewardGroup_header_keys.index(field)
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        reward: dict[str, Any] = value["rewards"][reward_index]
        if i == 0: #主键（`key`）
            to_append: Any = key
        elif i <= 5:
            to_append = value.get(field, "")
        elif i == 6 or i == 7: #选择策略配置子键（`SelectionStrategyConfig`'s subkeys）
            to_append = value["selectionStrategyConfig"][field.split()[1]] if "selectionStrategyConfig" in value else ""
        elif i == 10: #奖励序号（`reward_index`）
            to_append = reward_index + 1
        elif i >= 11 and i <= 17:
            subkey: str = field.split()[1]
            to_append = reward.get(subkey, "")
        elif i == 18 or i == 19: #奖励媒体子键（`reward media`'s subkeys）
            subkey: str = field.split()[2]
            to_append = reward["media"].get(field, "") if "media" in reward else ""
        elif i == 20: #奖励货币内置名（`reward {00fa4f01} mInternalName`）
            to_append = source[reward["{00fa4f01}"]]["mInternalName"] if "{00fa4f01}" in reward and reward["{00fa4f01}"] in source else ""
        else: #字符串常量（String constants）
            subkey2: str = pStrConst.search(field).group()
            subkey1: str = field.replace(subkey2, "")
            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
            tooltip_key: str = data_ref[subkey1][-1]
            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
        return to_append
    
    def build_mission_dataframe(self, debug: bool = False, paths: Optional[list[str]] = None) -> int:
        '''
        构建任务数据框。<br>Build mission dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 任务二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of mission binary description files, arranged in the following order:
        
            - 嚎哭深渊地图（Howling Abyss map）
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.missions_ready["map453"]:
            #获取任务信息（Get mission information）
            logPrint("正在读取任务数据……\nReading mission data ...", print_time = True)
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_mission_data(paths = paths)
            else:
                self.get_mission_data()
            if not self.missions_ready["map453"]:
                logPrint("任务数据尚未准备就绪！\nMission data not prepared!")
                return 2
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建任务数据框……\nBuilding the mission dataframes ...", print_time = True)
        KiwiProgressTrack_header_keys: list[str] = list(KiwiProgressTrack_header.keys())
        KiwiProgressTrack_data: dict[str, list[Any]] = {key: [] for key in KiwiProgressTrack_header_keys}
        KiwiProgressTrack_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiProgressTrack_data)
        KiwiRewardGroup_header: dict[str, str] = rewardGroup_header.copy()
        KiwiRewardGroup_header_keys: list[str] = list(KiwiRewardGroup_header.keys())
        KiwiRewardGroup_data: dict[str, list[Any]] = {key: [] for key in KiwiRewardGroup_header_keys}
        KiwiRewardGroup_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiRewardGroup_data)
        KiwiReward_header_keys: list[str] = list(KiwiReward_header.keys())
        KiwiReward_data: dict[str, list[Any]] = {key: [] for key in KiwiReward_header_keys}
        KiwiReward_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiReward_data)
        KiwiQuest_header_keys: list[str] = list(KiwiQuest_header.keys())
        KiwiQuest_data: dict[str, list[Any]] = {key: [] for key in KiwiQuest_header_keys}
        KiwiQuest_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiQuest_data)
        KiwiMission_header_keys: list[str] = list(KiwiMission_header.keys())
        KiwiMission_data: dict[str, list[Any]] = {key: [] for key in KiwiMission_header_keys}
        KiwiMission_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiMission_data)
        KiwiQuestMilestone_header_keys: list[str] = list(KiwiQuestMilestone_header.keys())
        KiwiQuestMilestone_data: dict[str, list[Any]] = {key: [] for key in KiwiQuestMilestone_header_keys}
        KiwiQuestMilestone_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiQuestMilestone_data)
        JadeProgressTrack_header: dict[str, str] = progressTrack_header.copy()
        JadeProgressTrack_header_keys: list[str] = list(progressTrack_header.keys())
        JadeProgressTrack_data: dict[str, list[Any]] = {key: [] for key in JadeProgressTrack_header_keys}
        JadeProgressTrack_data_json: dict[str, list[Any]] = copy.deepcopy(JadeProgressTrack_data)
        JadeRewardGroup_header: dict[str, str] = rewardGroup_header.copy()
        JadeRewardGroup_header_keys: list[str] = list(rewardGroup_header.keys())
        JadeRewardGroup_data: dict[str, list[Any]] = {key: [] for key in JadeRewardGroup_header_keys}
        JadeRewardGroup_data_json: dict[str, list[Any]] = copy.deepcopy(JadeRewardGroup_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        ##海克斯大乱斗任务（ARAM: Mayhem quest）
        progressKey_progressTrackKey_map: dict[str, str] = {}
        progressKey_questKey_map: dict[str, str] = {} #因为有太多未被解析的hash值，所以目前只是模糊地命名这个变量（Because there're so many unresolved hashes, currently I just name this variable vaguely）
        progressKey_questGroupKey_map: dict[str, str] = {}
        for (key, value) in self.map12_bin.items():
            if key != "__linked" and value["__type"] == "{a8dcba52}":
                progressKey_progressTrackKey_map[value["{055dd7d5}"]] = key
                progressKey_questKey_map[value["{c760b795}"]] = key
                progressKey_questGroupKey_map[value["{8137940d}"]] = key
        for (key1, value) in self.map12_bin.items():
            if key1 != "__linked" and value["__type"] == "ProgressTrack":
                if "MilestoneDefinitions" in value:
                    for milestoneDefinition_index in range(len(value["MilestoneDefinitions"])):
                        for i in range(len(KiwiProgressTrack_header_keys)):
                            key: str = KiwiProgressTrack_header_keys[i]
                            if i == 0: #进度主键（`progression_key1`）
                                to_append: Any = progressKey_progressTrackKey_map.get(key1, "")
                            else:
                                to_append = self.generate_progressTrack_record(self.map12_bin, key, key1, value, milestoneDefinition_index)
                            KiwiProgressTrack_data[key].append(to_append)
                            KiwiProgressTrack_data_json[key].append(pyobj2json(to_append))
                else:
                    for i in range(len(KiwiProgressTrack_header_keys)):
                        key: str = KiwiProgressTrack_header_keys[i]
                        if i == 0: #进度主键（`progression_key1`）
                            to_append: Any = progressKey_progressTrackKey_map.get(key1, "")
                        else:
                            to_append = self.generate_progressTrack_record(self.map12_bin, key, key1, value)
                        KiwiProgressTrack_data[key].append(to_append)
                        KiwiProgressTrack_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "RewardGroup":
                for reward_index in range(len(value["rewards"])):
                    for i in range(len(KiwiRewardGroup_header_keys)):
                        key: str = KiwiRewardGroup_header_keys[i]
                        to_append: Any = self.generate_rewardGroup_record(self.map12_bin, KiwiRewardGroup_data, key, key1, value, reward_index)
                        KiwiRewardGroup_data[key].append(to_append)
                        KiwiRewardGroup_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{c760b795}":
                for quest_index in range(len(value["{dde3e51f}"])):
                    quest_key: str = value["{dde3e51f}"][quest_index]
                    if quest_key in self.map12_bin:
                        quest: dict[str, Any] = self.map12_bin[quest_key]
                        for i in range(len(KiwiReward_header_keys)):
                            key: str = KiwiReward_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append = key1
                            elif i <= 2:
                                to_append = value[key]
                            elif i == 3: #进度主键（`progression_key`）
                                to_append = progressKey_questKey_map.get(key1, "")
                            else:
                                if i == 4: #大型任务序号（`quest_index`）
                                    to_append = quest_index + 1
                                elif i == 5: #大型任务主键（`quest_key`）
                                    to_append = quest_key
                                elif i <= 8:
                                    to_append = quest.get(key.split()[1], "")
                                elif i == 9: #quest {7fad8491} {8d7928e4}
                                    to_append = self.map12_bin[quest["{7fad8491}"]]["{8d7928e4}"] if quest["{7fad8491}"] in self.map12_bin else ""
                                elif i == 10: #前驱小型任务列表（`quest {90e39fce} {8ff60339}`）
                                    to_append = list(map(lambda x: x["{8ff60339}"], quest["{90e39fce}"])) if "{90e39fce}" in quest else ""
                                else: #奖励道具（`quest rewards Items`）
                                    to_append = self.map12_bin[quest["rewards"]]["items"] if quest["rewards"] in self.map12_bin else ""
                            KiwiReward_data[key].append(to_append)
                            KiwiReward_data_json[key].append(pyobj2json(to_append))
                    else:
                        for i in range(len(KiwiReward_header_keys)):
                            key: str = KiwiReward_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append = key1
                            elif i <= 2:
                                to_append = value[key]
                            elif i == 3: #进度主键（`progression_key`）
                                to_append = progressKey_questKey_map.get(key1, "")
                            else:
                                to_append = ""
                            KiwiReward_data[key].append(to_append)
                            KiwiReward_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{8137940d}":
                for questGroup_index in range(len(value["{3f2e4716}"])):
                    questGroup_key: str = value["{3f2e4716}"][questGroup_index]
                    if questGroup_key in self.map12_bin:
                        questGroup: dict[str, Any] = self.map12_bin[questGroup_key]
                        for quest_index in range(len(questGroup["{5a6276fa}"])):
                            quest_key: str = questGroup["{5a6276fa}"][quest_index]
                            if quest_key in self.map12_bin:
                                quest: dict[str, Any] = self.map12_bin[quest_key]
                                for i in range(len(KiwiQuest_header_keys)):
                                    key: str = KiwiQuest_header_keys[i]
                                    if i == 0: #大型任务事件主键（`key`）
                                        to_append = key1
                                    elif i == 1: #进度主键（`progression_key`）
                                        to_append = progressKey_questGroupKey_map.get(key1, "")
                                    elif i <= 5:
                                        if i == 2: #大型任务分组序号（`questGroup_index`）
                                            to_append = questGroup_index + 1
                                        elif i == 3: #大型任务分组主键（`questGroup_key`）
                                            to_append = questGroup_key
                                        elif i == 4: #大型任务分组已锁定（`questGroup Locked`）
                                            to_append = questGroup.get("Locked", False)
                                        else: #`questGroup {5e7167cd}`
                                            to_append = questGroup.get("{5e7167cd}", "")
                                    else:
                                        if i == 6: #大型任务序号（`quest_index`）
                                            to_append = quest_index + 1
                                        elif i == 7: #大型任务主键（`quest_key`）
                                            to_append = quest_key
                                        elif i <= 12:
                                            to_append = quest.get(key.split()[1], "")
                                        elif i <= 17:
                                            to_append = quest["QuestData"].get(key.split()[2], False if i == 15 or 16 else "")
                                        else:
                                            subkey2: str = pStrConst.search(key).group()
                                            subkey1: str = key.replace(subkey2, "")
                                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                            tooltip_key: str = KiwiQuest_data[subkey1][-1]
                                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                    KiwiQuest_data[key].append(to_append)
                                    KiwiQuest_data_json[key].append(pyobj2json(to_append))
                                for milestone_index in range(len(quest["QuestData"]["Milestones"])):
                                    milestone: dict[str, Any] = quest["QuestData"]["Milestones"][milestone_index]
                                    for i in range(len(KiwiQuestMilestone_header_keys)):
                                        key: str = KiwiQuestMilestone_header_keys[i]
                                        if i == 0: #大型任务事件主键（`key`）
                                            to_append = key1
                                        elif i == 1: #进度主键（`progression_key`）
                                            to_append = progressKey_questGroupKey_map.get(key1, "")
                                        elif i <= 5:
                                            if i == 2: #大型任务分组序号（`questGroup_index`）
                                                to_append = questGroup_index + 1
                                            elif i == 3: #大型任务分组主键（`questGroup_key`）
                                                to_append = questGroup_key
                                            elif i == 4: #大型任务分组已锁定（`questGroup Locked`）
                                                to_append = questGroup.get("Locked", False)
                                            else: #`questGroup {5e7167cd}`
                                                to_append = questGroup.get("{5e7167cd}", "")
                                        elif i <= 9:
                                            if i == 6: #大型任务序号（`quest_index`）
                                                to_append = quest_index + 1
                                            elif i == 7: #大型任务主键（`quest_key`）
                                                to_append = quest_key
                                            else:
                                                subkey2: str = pStrConst.search(key).group()
                                                subkey1: str = key.replace(subkey2, "")
                                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                                tooltip_key: str = quest["TitleTra"]
                                                to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                        else:
                                            if i == 10: #里程碑序号（`milestone_index`）
                                                to_append = milestone_index + 1
                                            elif i == 11 or i == 12:
                                                to_append = milestone[key.split()[1]]
                                            else: #字符串常量（String constants）
                                                subkey2: str = pStrConst.search(key).group()
                                                subkey1: str = key.replace(subkey2, "")
                                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                                tooltip_key: str = milestone["MilestoneDescriptionTra"]
                                                to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                        KiwiQuestMilestone_data[key].append(to_append)
                                        KiwiQuestMilestone_data_json[key].append(pyobj2json(to_append))
                            else:
                                for i in range(len(KiwiQuest_header_keys)):
                                    key: str = KiwiQuest_header_keys[i]
                                    if i == 0: #大型任务事件主键（`key`）
                                        to_append = key1
                                    elif i == 1: #进度主键（`progression_key`）
                                        to_append = progressKey_questGroupKey_map.get(key1, "")
                                    elif i <= 5:
                                        if i == 2: #大型任务分组序号（`questGroup_index`）
                                            to_append = questGroup_index + 1
                                        elif i == 3: #大型任务分组主键（`questGroup_key`）
                                            to_append = questGroup_key
                                        elif i == 4: #大型任务分组已锁定（`questGroup Locked`）
                                            to_append = questGroup.get("Locked", False)
                                        else: #`questGroup {5e7167cd}`
                                            to_append = questGroup.get("{5e7167cd}", "")
                                    else:
                                        to_append = False if i == 15 or i == 16 else ""
                                    KiwiQuest_data[key].append(to_append)
                                    KiwiQuest_data_json[key].append(pyobj2json(to_append))
                    else:
                        for i in range(len(KiwiQuest_header_keys)):
                            key: str = KiwiQuest_header_keys[i]
                            if i == 0: #大型任务事件主键（`key`）
                                to_append = key1
                            elif i == 1: #进度主键（`progression_key`）
                                to_append = progressKey_questGroupKey_map.get(key1, "")
                            else:
                                to_append = False if i in {4, 15, 16} else ""
                            KiwiQuest_data[key].append(to_append)
                            KiwiQuest_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{e3ce28e9}":
                for objective_index in range(len(value["objectives"])):
                    objective: dict[str, Any] = value["objectives"][objective_index]
                    for i in range(len(KiwiMission_header_keys)):
                        key: str = KiwiMission_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1 or i == 2:
                            to_append = value[key]
                        elif i == 3: #小型任务奖励类型识别码（`{7fad8491} {8d7928e4}`）
                            to_append = self.map12_bin[value["{7fad8491}"]]["{8d7928e4}"] if value["{7fad8491}"] in self.map12_bin else ""
                        elif i == 4: #目标序号（`objective_index`）
                            to_append = objective_index + 1
                        elif i <= 7:
                            to_append = objective.get(key.split()[1], "")
                        else: #目标描述字符串常量（Objective description string constant）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            tooltip_key: str = objective["DescriptionTraKey"]
                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        KiwiMission_data[key].append(to_append)
                        KiwiMission_data_json[key].append(pyobj2json(to_append))
        KiwiProgressTrack_statistics_output_order: list[int] = [0, 1, 3, 2, 4, 5, 6, 7, 9, 8, 10, 11, 18, 17, 12, 13, 14, 15, 16]
        KiwiProgressTrack_data_organized: dict[str, list[Any]] = {KiwiProgressTrack_header_keys[i]: KiwiProgressTrack_data_json[KiwiProgressTrack_header_keys[i]] for i in KiwiProgressTrack_statistics_output_order}
        KiwiProgressTrack_df: pandas.DataFrame = pandas.DataFrame(data = KiwiProgressTrack_data_organized)
        KiwiProgressTrack_df = pandas.concat([pandas.DataFrame([KiwiProgressTrack_header])[KiwiProgressTrack_df.columns], KiwiProgressTrack_df], ignore_index = True)
        self.KiwiProgressTrack_df = KiwiProgressTrack_df
        KiwiRewardGroup_statistics_output_order: list[int] = [0, 3, 8, 9, 2, 1, 4, 5, 6, 7, 10, 17, 11, 21, 22, 14, 13, 15, 12, 23, 24, 16, 20, 19]
        KiwiRewardGroup_data_organized: dict[str, list[Any]] = {KiwiRewardGroup_header_keys[i]: KiwiRewardGroup_data_json[KiwiRewardGroup_header_keys[i]] for i in KiwiRewardGroup_statistics_output_order}
        KiwiRewardGroup_df: pandas.DataFrame = pandas.DataFrame(data = KiwiRewardGroup_data_organized)
        KiwiRewardGroup_df = pandas.concat([pandas.DataFrame([KiwiRewardGroup_header])[KiwiRewardGroup_df.columns], KiwiRewardGroup_df], ignore_index = True)
        self.KiwiRewardGroup_df = KiwiRewardGroup_df
        KiwiReward_statistics_output_order: list[int] = [3, 0, 1, 2, 4, 5, 6, 9, 8, 11, 7, 10]
        KiwiReward_data_organized: dict[str, list[Any]] = {KiwiReward_header_keys[i]: KiwiReward_data_json[KiwiReward_header_keys[i]] for i in KiwiReward_statistics_output_order}
        KiwiReward_df: pandas.DataFrame = pandas.DataFrame(data = KiwiReward_data_organized)
        KiwiReward_df = pandas.concat([pandas.DataFrame([KiwiReward_header])[KiwiReward_df.columns], KiwiReward_df], ignore_index = True)
        self.KiwiReward_df = KiwiReward_df
        KiwiQuest_statistics_output_order: list[int] = [1, 0, 2, 3, 4, 5, 6, 7, 8, 15, 16, 17, 9, 18, 19, 13, 22, 23, 10, 20, 21, 14, 24, 25, 12, 11]
        KiwiQuest_data_organized: dict[str, list[Any]] = {KiwiQuest_header_keys[i]: KiwiQuest_data_json[KiwiQuest_header_keys[i]] for i in KiwiQuest_statistics_output_order}
        KiwiQuest_df: pandas.DataFrame = pandas.DataFrame(data = KiwiQuest_data_organized)
        logPrint("正在优化海克斯大乱斗大型任务数据框的逻辑值显示……\nOptimizing boolean value display of the ARAM: Mayhem quest dataframe ...")
        optimize_bool_display(KiwiQuest_df)
        KiwiQuest_df = pandas.concat([pandas.DataFrame([KiwiQuest_header])[KiwiQuest_df.columns], KiwiQuest_df], ignore_index = True)
        self.KiwiQuest_df = KiwiQuest_df
        KiwiMission_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 7, 8, 9, 5, 6]
        KiwiMission_data_organized: dict[str, list[Any]] = {KiwiMission_header_keys[i]: KiwiMission_data_json[KiwiMission_header_keys[i]] for i in KiwiMission_statistics_output_order}
        KiwiMission_df: pandas.DataFrame = pandas.DataFrame(data = KiwiMission_data_organized)
        KiwiMission_df = pandas.concat([pandas.DataFrame([KiwiMission_header])[KiwiMission_df.columns], KiwiMission_df], ignore_index = True)
        self.KiwiMission_df = KiwiMission_df
        KiwiQuestMilestone_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        KiwiQuestMilestone_data_organized: dict[str, list[Any]] = {KiwiQuestMilestone_header_keys[i]: KiwiQuestMilestone_data_json[KiwiQuestMilestone_header_keys[i]] for i in KiwiQuestMilestone_statistics_output_order}
        KiwiQuestMilestone_df: pandas.DataFrame = pandas.DataFrame(data = KiwiQuestMilestone_data_organized)
        logPrint("正在优化海克斯大乱斗大型任务里程碑数据框的逻辑值显示……\nOptimizing boolean value display of the ARAM: Mayhem quest milestone dataframe ...")
        optimize_bool_display(KiwiQuestMilestone_df)
        KiwiQuestMilestone_df = pandas.concat([pandas.DataFrame([KiwiQuestMilestone_header])[KiwiQuestMilestone_df.columns], KiwiQuestMilestone_df], ignore_index = True)
        self.KiwiQuestMilestone_df = KiwiQuestMilestone_df
        ##英雄联盟经典模式进度追踪（League Classic progress track）
        for (key1, value) in self.map453_bin.items():
            if key1 != "__linked" and value["__type"] == "ProgressTrack":
                if "MilestoneDefinitions" in value:
                    for milestoneDefinition_index in range(len(value["MilestoneDefinitions"])):
                        for i in range(len(JadeProgressTrack_header_keys)):
                            key: str = JadeProgressTrack_header_keys[i]
                            to_append = self.generate_progressTrack_record(self.map453_bin, key, key1, value, milestoneDefinition_index)
                            JadeProgressTrack_data[key].append(to_append)
                            JadeProgressTrack_data_json[key].append(pyobj2json(to_append))
                else:
                    for i in range(len(JadeProgressTrack_header_keys)):
                        key: str = JadeProgressTrack_header_keys[i]
                        to_append = self.generate_progressTrack_record(self.map453_bin, key, key1, value)
                        JadeProgressTrack_data[key].append(to_append)
                        JadeProgressTrack_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "RewardGroup":
                for reward_index in range(len(value["rewards"])):
                    for i in range(len(JadeRewardGroup_header_keys)):
                        key: str = JadeRewardGroup_header_keys[i]
                        to_append: Any = self.generate_rewardGroup_record(self.map453_bin, JadeRewardGroup_data, key, key1, value, reward_index)
                        JadeRewardGroup_data[key].append(to_append)
                        JadeRewardGroup_data_json[key].append(pyobj2json(to_append))
        JadeProgressTrack_statistics_output_order: list[int] = [0, 2, 1, 3, 4, 5, 6, 8, 7, 9, 10, 17, 16, 11, 12, 13, 14, 15]
        JadeProgressTrack_data_organized: dict[str, list[Any]] = {JadeProgressTrack_header_keys[i]: JadeProgressTrack_data_json[JadeProgressTrack_header_keys[i]] for i in JadeProgressTrack_statistics_output_order}
        JadeProgressTrack_df: pandas.DataFrame = pandas.DataFrame(data = JadeProgressTrack_data_organized)
        JadeProgressTrack_df = pandas.concat([pandas.DataFrame([JadeProgressTrack_header])[JadeProgressTrack_df.columns], JadeProgressTrack_df], ignore_index = True)
        self.JadeProgressTrack_df = JadeProgressTrack_df
        JadeRewardGroup_statistics_output_order: list[int] = [0, 3, 8, 9, 2, 1, 4, 5, 6, 7, 10, 17, 11, 21, 22, 14, 13, 15, 12, 23, 24, 16, 20, 19]
        JadeRewardGroup_data_organized: dict[str, list[Any]] = {JadeRewardGroup_header_keys[i]: JadeRewardGroup_data_json[JadeRewardGroup_header_keys[i]] for i in JadeRewardGroup_statistics_output_order}
        JadeRewardGroup_df: pandas.DataFrame = pandas.DataFrame(data = JadeRewardGroup_data_organized)
        JadeRewardGroup_df = pandas.concat([pandas.DataFrame([JadeRewardGroup_header])[JadeRewardGroup_df.columns], JadeRewardGroup_df], ignore_index = True)
        self.JadeRewardGroup_df = JadeRewardGroup_df
        return 0
    
    def enqueue_mission_dataframe(self) -> None:
        '''
        将任务数据框追加到数据提取器基类的数据框队列尾部。<br>Append mission dataframes into the end of `LoLDataExtractor.df_queue`.
        '''
        if not self.KiwiProgressTrack_df.empty:
            KiwiProgressTrack_ws: dict[str, Any] = self.worksheet_metadata["KiwiProgressTrack"]
            sheet1_name: str = KiwiProgressTrack_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiProgressTrack_ws["sheet_name_without_version"]
            KiwiProgressTrack_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiProgressTrack_ws["dType"]), "dType": KiwiProgressTrack_ws["dType"], "sheet_name": sheet1_name, "sheet": self.KiwiProgressTrack_df}
            self.enqueue_df(KiwiProgressTrack_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiRewardGroup_df.empty:
            KiwiRewardGroup_ws: dict[str, Any] = self.worksheet_metadata["KiwiRewardGroup"]
            sheet2_name: str = KiwiRewardGroup_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiRewardGroup_ws["sheet_name_without_version"]
            KiwiRewardGroup_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiRewardGroup_ws["dType"]), "dType": KiwiRewardGroup_ws["dType"], "sheet_name": sheet2_name, "sheet": self.KiwiRewardGroup_df}
            self.enqueue_df(KiwiRewardGroup_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiReward_df.empty:
            KiwiReward_ws: dict[str, Any] = self.worksheet_metadata["KiwiReward"]
            sheet3_name: str = KiwiReward_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiReward_ws["sheet_name_without_version"]
            KiwiReward_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiReward_ws["dType"]), "dType": KiwiReward_ws["dType"], "sheet_name": sheet3_name, "sheet": self.KiwiReward_df}
            self.enqueue_df(KiwiReward_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiQuest_df.empty:
            KiwiQuest_ws: dict[str, Any] = self.worksheet_metadata["KiwiQuest"]
            sheet4_name: str = KiwiQuest_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiQuest_ws["sheet_name_without_version"]
            KiwiQuest_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiQuest_ws["dType"]), "dType": KiwiQuest_ws["dType"], "sheet_name": sheet4_name, "sheet": self.KiwiQuest_df}
            self.enqueue_df(KiwiQuest_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiMission_df.empty:
            KiwiMission_ws: dict[str, Any] = self.worksheet_metadata["KiwiMission"]
            sheet5_name: str = KiwiMission_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiMission_ws["sheet_name_without_version"]
            KiwiMission_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiMission_ws["dType"]), "dType": KiwiMission_ws["dType"], "sheet_name": sheet5_name, "sheet": self.KiwiMission_df}
            self.enqueue_df(KiwiMission_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.KiwiQuestMilestone_df.empty:
            KiwiQuestMilestone_ws: dict[str, Any] = self.worksheet_metadata["KiwiQuestMilestone"]
            sheet6_name: str = KiwiQuestMilestone_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else KiwiQuestMilestone_ws["sheet_name_without_version"]
            KiwiQuestMilestone_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(KiwiQuestMilestone_ws["dType"]), "dType": KiwiQuestMilestone_ws["dType"], "sheet_name": sheet6_name, "sheet": self.KiwiQuestMilestone_df}
            self.enqueue_df(KiwiQuestMilestone_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.JadeProgressTrack_df.empty:
            JadeProgressTrack_ws: dict[str, Any] = self.worksheet_metadata["JadeProgressTrack"]
            sheet7_name: str = JadeProgressTrack_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else JadeProgressTrack_ws["sheet_name_without_version"]
            JadeProgressTrack_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(JadeProgressTrack_ws["dType"]), "dType": JadeProgressTrack_ws["dType"], "sheet_name": sheet7_name, "sheet": self.JadeProgressTrack_df}
            self.enqueue_df(JadeProgressTrack_df_struct, overwrite_on_exist = True, log = self.log)
        if not self.JadeRewardGroup_df.empty:
            JadeRewardGroup_ws: dict[str, Any] = self.worksheet_metadata["JadeRewardGroup"]
            sheet8_name: str = JadeRewardGroup_ws["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else JadeRewardGroup_ws["sheet_name_without_version"]
            JadeRewardGroup_df_struct: dict[str, Any] = {"order": self.worksheet_dType_orderedList.index(JadeRewardGroup_ws["dType"]), "dType": JadeRewardGroup_ws["dType"], "sheet_name": sheet8_name, "sheet": self.JadeRewardGroup_df}
            self.enqueue_df(JadeRewardGroup_df_struct, overwrite_on_exist = True, log = self.log)
    
    def export_mission_data(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出任务数据到工作簿中。产生以下工作表：<br>Export mission data to a workbook. The following worksheets are added:
        - 海克斯大乱斗进度追踪（Kiwi Progress Track）
        - 海克斯大乱斗奖励分组（Kiwi Reward Group）
        - 海克斯大乱斗奖励（Kiwi Reward）
        - 海克斯大乱斗大型任务（Kiwi Quest）
        - 海克斯大乱斗小型任务（Kiwi Mission）
        - 海克斯大乱斗任务里程碑（Kiwi Quest Milestone）
        - 经典模式进度追踪（Kiwi Progress Track）
        - 经典模式奖励分组（Jade Reward Group）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 任务二进制描述文件的本地路径，按照以下顺序排列：<br>The local path of mission binary description files, arranged in the following order:
        
            - 经典召唤师峡谷地图（Classic Rift map）
            - 嚎哭深渊地图（Howling Abyss map）
        
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
        if self.JadeProgressTrack_df.empty or self.JadeRewardGroup_df.empty: #海克斯大乱斗未引入乐队时，应当也能够正确导出任务数据（Mission data should be exported properly when bands hadn't been introduced into ARAM: Mayhem）
            status: int = self.build_mission_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        if self.dense_export:
            KiwiProgressTrack_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiProgressTrack_df)
            KiwiRewardGroup_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiRewardGroup_df)
            KiwiReward_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiReward_df)
            KiwiQuest_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiQuest_df)
            KiwiMission_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiMission_df)
            KiwiQuestMilestone_df: pandas.DataFrame = eliminate_empty_fields(self.KiwiQuestMilestone_df)
            JadeProgressTrack_df: pandas.DataFrame = eliminate_empty_fields(self.JadeProgressTrack_df)
            JadeRewardGroup_df: pandas.DataFrame = eliminate_empty_fields(self.JadeRewardGroup_df)
        else:
            KiwiProgressTrack_df = self.KiwiProgressTrack_df
            KiwiRewardGroup_df = self.KiwiRewardGroup_df
            KiwiReward_df = self.KiwiReward_df
            KiwiQuest_df = self.KiwiQuest_df
            KiwiMission_df = self.KiwiMission_df
            KiwiQuestMilestone_df = self.KiwiQuestMilestone_df
            JadeProgressTrack_df = self.JadeProgressTrack_df
            JadeRewardGroup_df = self.JadeRewardGroup_df
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = self.worksheet_metadata["KiwiProgressTrack"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiProgressTrack"]["sheet_name_without_version"]
        sheet2_name: str = self.worksheet_metadata["KiwiRewardGroup"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiRewardGroup"]["sheet_name_without_version"]
        sheet3_name: str = self.worksheet_metadata["KiwiReward"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiReward"]["sheet_name_without_version"]
        sheet4_name: str = self.worksheet_metadata["KiwiQuest"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiQuest"]["sheet_name_without_version"]
        sheet5_name: str = self.worksheet_metadata["KiwiMission"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiMission"]["sheet_name_without_version"]
        sheet6_name: str = self.worksheet_metadata["KiwiQuestMilestone"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["KiwiQuestMilestone"]["sheet_name_without_version"]
        sheet7_name: str = self.worksheet_metadata["JadeProgressTrack"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["JadeProgressTrack"]["sheet_name_without_version"]
        sheet8_name: str = self.worksheet_metadata["JadeRewardGroup"]["sheet_name_with_version"].format(version = self.patch_number) if self.sheet_naming_fold else self.worksheet_metadata["JadeRewardGroup"]["sheet_name_without_version"]
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    if not KiwiProgressTrack_df.empty:
                        addDefaultStyle(KiwiProgressTrack_df).to_excel(excel_writer = writer, sheet_name = sheet1_name[:31])
                    if not KiwiRewardGroup_df.empty:
                        addDefaultStyle(KiwiRewardGroup_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    if not KiwiReward_df.empty:
                        addDefaultStyle(KiwiReward_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    if not KiwiQuest_df.empty:
                        addDefaultStyle(KiwiQuest_df).to_excel(excel_writer = writer, sheet_name = sheet4_name)
                    if not KiwiMission_df.empty:
                        addDefaultStyle(KiwiMission_df).to_excel(excel_writer = writer, sheet_name = sheet5_name)
                    if not KiwiQuestMilestone_df.empty:
                        addDefaultStyle(KiwiQuestMilestone_df).to_excel(excel_writer = writer, sheet_name = sheet6_name[:31])
                    addDefaultStyle(JadeProgressTrack_df).to_excel(excel_writer = writer, sheet_name = sheet7_name[:31])
                    addDefaultStyle(JadeRewardGroup_df).to_excel(excel_writer = writer, sheet_name = sheet8_name)
                    for sheet_name in [sheet1_name, sheet2_name, sheet3_name, sheet4_name, sheet5_name, sheet6_name, sheet7_name, sheet8_name]:
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
                logPrint(f"任务数据已导出到{self.wbPath}。\nMission data have been exported to {self.wbPath}.", print_time = True)
                break
    
    def to_html(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出任务数据到网页中。产生以下文件：<br>Export mission data into html files. The following files are produced:
        - 海克斯大乱斗奖励分组（Kiwi Reward Group）
        - 经典模式奖励分组（Jade Reward Group）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 任务二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of mission binary description files, arranged in the following order:
        
            - 经典召唤师峡谷地图（Classic Rift map）
            - 嚎哭深渊地图（Howling Abyss map）
        
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
        if self.JadeProgressTrack_df.empty or self.JadeRewardGroup_df.empty:
            status: int = self.build_mission_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was building the dataframe. Press Enter to continue.")
                logInput()
                return
        #海克斯大乱斗奖励分组（Kiwi Reward Group）
        if len(self.KiwiRewardGroup_df) > 1:
            KiwiRewardGroup_df_web: pandas.DataFrame = self.KiwiRewardGroup_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            rewardMediaIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.KiwiRewardGroup_df.loc[1:, "reward media {15c4c3cb}"].to_list()))
            KiwiRewardGroup_df_web.insert(len(KiwiRewardGroup_df_web.columns), "rewardMediaIconUrl", ["奖励缩略图网址"] + rewardMediaIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "key",
                "LocalizedName_content_zh",
                "LocalizedName_content_en",
                "rewardStrategy",
                "celebrationType",
                "reward_index",
                "reward __type",
                "reward media {15c4c3cb}",
                "reward quantity",
                "reward {31c5f01c}_content_zh",
                "reward {31c5f01c}_content_en",
                "reward {d35466b8}_content_zh",
                "reward {d35466b8}_content_en"
            ]
            KiwiRewardGroup_df_web = KiwiRewardGroup_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            KiwiRewardGroup_df_styled: pandas.io.formats.style.Styler = KiwiRewardGroup_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:11]
            KiwiRewardGroup_df_styled = KiwiRewardGroup_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            KiwiRewardGroup_htmltable: str = KiwiRewardGroup_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            KiwiRewardGroup_htmltable = '<meta charset="UTF-8">\n' + KiwiRewardGroup_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"KiwiRewardGroup_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(KiwiRewardGroup_htmltable)
        #经典模式奖励分组（Jade Reward Group）
        if len(self.JadeRewardGroup_df) > 1:
            JadeRewardGroup_df_web: pandas.DataFrame = self.JadeRewardGroup_df.copy(deep = True)
            ##将图标路径转换为网址（Transform icon paths into urls）
            rewardMediaIconUrls: list[str] = list(map(lambda x: self.url2image(self.assetPath2url(self.version, x)), self.JadeRewardGroup_df.loc[1:, "reward media {15c4c3cb}"].to_list()))
            JadeRewardGroup_df_web.insert(len(JadeRewardGroup_df_web.columns), "rewardMediaIconUrl", ["奖励缩略图网址"] + rewardMediaIconUrls)
            ##设置要导出的行和列（Set the rows and columns to export）
            columns_to_export: list[str] = [
                "key",
                "LocalizedName_content_zh",
                "LocalizedName_content_en",
                "rewardStrategy",
                "celebrationType",
                "reward_index",
                "reward __type",
                "reward media {15c4c3cb}",
                "reward quantity",
                "reward {31c5f01c}_content_zh",
                "reward {31c5f01c}_content_en",
                "reward {d35466b8}_content_zh",
                "reward {d35466b8}_content_en"
            ]
            JadeRewardGroup_df_web = JadeRewardGroup_df_web.loc[:, columns_to_export]
            ##样式设置（Style configuration）
            ###设置单元格边框（Set cell border）
            JadeRewardGroup_df_styled: pandas.io.formats.style.Styler = JadeRewardGroup_df_web.style.set_table_styles(self.CELL_BORDER_STYLE)
            ###设置居中的列（Set centered columns）
            center_columns: list[str] = columns_to_export[:11]
            JadeRewardGroup_df_styled = JadeRewardGroup_df_styled.set_properties(subset = center_columns, **{"text-align": "center", "encoding": "utf-8"})
            ##获取网页源代码（Get the web source code）
            JadeRewardGroup_htmltable: str = JadeRewardGroup_df_styled.to_html(escape = False)
            ##导出为网页（Export to web）
            self.make_dir()
            JadeRewardGroup_htmltable = '<meta charset="UTF-8">\n' + JadeRewardGroup_htmltable
            locale: str = self.locale.replace("_", "-")
            version: str = self.patch
            with open(os.path.join(self.webFolder, f"JadeRewardGroup_{locale}_{version}.html"), "w", encoding = "utf-8") as fp:
                fp.write(JadeRewardGroup_htmltable)
