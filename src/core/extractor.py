import copy, json, os, pandas, re, requests, sys, time
from urllib.parse import urljoin
from xxhash import xxh3_64_intdigest
from openpyxl import load_workbook, Workbook
from typing import Any, Callable, Literal, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.logger import LogManager
from src.utils.patch import Patch, get_cdragon_patchList
from src.utils.webRequest import requestUrl
from src.utils.format import optimize_bool_display, format_df, addDefaultStyle, pyobj2json, capitalize, decapitalize
from src.utils.runtimeDebug import subscope
from src.utils.excel_workbook import create_workbook_win32, sort_worksheet
from src.core.config.headers import map_header_l10n, cheatset_header, cheat_header, perkstyle_header, perk_header, champion_header, champion_spell_header, item_header, itemGroup_header, itemModifier_header, CherryAugment_header, SwarmAugment_header, KiwiAugment_header, KiwiAugmentSet_header, CherryAnvil_header, GoH_header, TFTSet_header, TFTShop_header, TFTShopContent_header, TFTDropRate_header, TFTStageRound_header, TFTRound_header, TFTPortal_header, TFTEncounterDistribution_header, TFTEncounter_header, TFTUnitProperty_header, TFTCharacterRole_header, TFTItemList_header, TFTItem_header, TFTTraitList_header, TFTTrait_header, TFTPVENPC_header, TFTScript_header, TFTAnnouncement_header
from src.core.config.localization import language_ddragon, language_cdragon

#=============================================================================
# * 声明（Declaration）
#=============================================================================
# 作者（Author）：          WordlessMeteor
# 主页（Home page）：       https://github.com/WordlessMeteor/LoL-DIY-Programs/
# 鸣谢（Acknowledgement）： Morilli, Le poussin, Moga
# 更新（Last update）：     2026/04/16
#=============================================================================

#定义异质性检验函数（Define heterogeneity verification function）
def verifyDictHeterogeneity(dict_list: list[dict[str, Any]]) -> tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]:
    '''
    检查不同的字典中是否存在键相同但值不同的键值对。<br>Check if there're any key-value pairs among dictionaries, where keys are the same but values are not.
    
    在本脚本中，主要用于调试是否不同的二进制描述数据可以合并。<br>In this program, this function is mainly used to debug whether different binary description data can be merged.
    
    :param dict_list: 由字典组成的列表。<br>A list of dictionaries.
    :type dict_list: list[dict[str, Any]]
    :return: 不同字典的键值覆盖情况。由以下四个表格组成：<br>Key-value pair overlay situation between different dictionaries. Composed of the following four dataframes:
    
        1. 重合键矩阵。每个单元格代表两个字典中的共享键的**集合**。<br>Overlapped key matrix. Each cell represents the **set** of shared keys between this pair of dictionaries.
        2. 重合键数量矩阵。每个单元格代表两个字典中的共享键的**数量**。<br>Overlapped key count matrix. Each cell represents the **number** of shared keys between this pair of dictionaries.
        3. 逻辑矩阵。每个单元格代表两个字典**是否满足**但凡相同的键的值都相同这一命题。<br>Logical matrix. Each cell represents whether this pair of dictionaries **follow the proposition that** the values of each shared key is the same.
        4. 差异矩阵。每个单元格代表两个字典中值不同的共享键的集合。<br>Diff matrix. Each cell represents the set of keys whose values are different between this pair of dictionaries.
    :rtype: tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
    '''
    matrix: list[list[set[str]]] = []
    count_matrix: list[list[int]] = []
    bool_matrix: list[list[int]] = []
    diff_matrix: list[list[list[str]]] = []
    for i in range(len(dict_list)):
        matrix.append([])
        count_matrix.append([])
        bool_matrix.append([])
        diff_matrix.append([])
        for j in range(len(dict_list)):
            common_keys: set[str] = set(dict_list[i].keys()) & set(dict_list[j].keys())
            matrix[i].append(common_keys)
            count_matrix[i].append(len(common_keys))
            bool_matrix[i].append(all(map(lambda x: dict_list[i][x] == dict_list[j][x], common_keys)))
            diff_matrix[i].append([key for key in sorted(common_keys) if dict_list[i][key] != dict_list[j][key]])
    overlay_table: pandas.DataFrame = pandas.DataFrame(matrix)
    overlay_count_table: pandas.DataFrame = pandas.DataFrame(count_matrix)
    overlay_identical_table: pandas.DataFrame = pandas.DataFrame(bool_matrix)
    overlay_difference_table: pandas.DataFrame = pandas.DataFrame(diff_matrix)
    return overlay_table, overlay_count_table, overlay_identical_table, overlay_difference_table

#定义键汇总函数族（Define the key summary function family）
def syncListOrder(src: list[Any], ref: list[Any]) -> None:
    '''
    根据参考列表中元素的顺序排列一个列表中元素的顺序。<br>Arrange elements in a list in the order of those in the reference list.
    
    :param src: 要排序的列表。<br>The list to be ordered.
    :type src: list[Any]
    :param ref: 参考列表。<br>Reference list. 
    :type src: list[Any]
    '''
    #求两个列表的交集，并保持其元素在ref中的顺序（Get the intersection of two lists and reserve its element order as in `ref`）
    intersection: list[Any] = []
    for key in ref:
        if key in src:
            intersection.append(key)
    #冒泡排序（Bubble sort）
    for i in range(len(intersection) - 1):
        key1: Any = intersection[i]
        if key1 in src:
            for j in range(i + 1, len(intersection)):
                key2: Any = intersection[j]
                if key2 in src:
                    if src.index(key1) > src.index(key2): #在这个过程中，key1和key2之间的非交集元素只有相对key1的位置信息发生了变化，尽可能减小排序时的扰动（During this process, the element between `key1` and `key2` not in `intersection` is only changed upon comparing the location relationship with `key1`, so that the disturbance could be minimized as much as possible）
                        tmp: Any = src.pop(src.index(key2))
                        src.insert(src.index(key1) + 1, tmp)
    #检验排序情况（Verify whether `src` is sorted）
    # intersection1: list[Any] = []
    # for i in src:
    #     if i in ref:
    #         intersection1.append(i)
    # intersection2: list[Any] = []
    # for i in ref:
    #     if i in src:
    #         intersection2.append(i)
    # return intersection1 == intersection2

def traverse_keyPath(keys: dict[str, list[str]], keys_count: dict[str, dict[str, int]], keys_to_insert: dict[str, list[str]], value: dict[str, Any], keyPath: list[str], targetTypes: Optional[list[str]] = None, allowNoneType: bool = True) -> int: #递归遍历键路径（Recursively traverse the keyPath）
    '''
    遍历键路径，并构建键路径指向的对象中的所有键按概要顺序组成的列表。<br>Traverse `keyPath` and build a list of keys in the object obtained from `keyPath`. The keys should follow the schemas order by design.
    
    :param keys: 目标数据结构，通过引用传递实现赋值。键是键路径指向的对象的类型，值是由键路径指向的对象的所有键组成的列表。<br>The target data structure of this function, and its assignment is achieved by passing the reference. Each key is the type of the object obtained by traversing throughout `keyPath`. Each value is a list of all keys of the object obtained by traversing throughout `keyPath`.
    :type keys: dict[str, list[str]]
    :param keys_count: 目标数据结构，通过引用传递实现赋值。键和keys参数的键相同，值是keys参数的值的频数统计字典，其中键是键路径指向的对象的键，值是该键在键路径指向的所有对象中的出现次数。<br>The target data structure of this function, and its assignment is achieved by passing the reference. Each key is the same as that of `keys` parameter. Each value is a frequency distribution dictionary of that of `keys` parameter, where each subkey is a key of the object obtained by traversing throughout `keyPath` and each subvalue is the occurrence of this subkey in that object.
    :type keys_count: dict[str, dict[str, int]]
    :param keys_to_insert: 中间变量，不作为返回值。通过引用传递。该参数存储不同对象类型要插入候选下标位置的键。键是键路径指向的对象的类型，值是等待插入的键字符串组成的列表。<br>An intermediate variable, thus not returned. Pass by reference. This parameter stores keys of different object types to insert into the candidate index location. Each of its keys is the type of the object obtained by traversing throughout `keyPath`. Each of its values is a list of keys of that object type to be inserted.
    :type keys_to_insert: dict[str, list[str]]
    :param value: 遍历起点字典。<br>The beginning dictionary for traversal.
    :type value: dict[str, Any]
    :param keyPath: 由键组成的列表。<br>A list of keys.
    :type keyPath: list[str]
    :param targetTypes: 见getBinaryKeys函数的文档字符串。<br>Refer to the docstring of `getBinaryKeys` function.
    :type targetTypes: list[str] | None
    :param allowNoneType: 见getBinaryKeys函数的文档字符串。<br>Refer to the docstring of `getBinaryKeys` function.
    :type allowNoneType: bool
    :return: 状态码。0表示成功，1表示失败。<br>Status code: 0 for success and 1 for failure.
    :rtype: int
    '''
    value_ptr: Any = value
    for i in range(len(keyPath)):
        key: str = keyPath[i]
        if isinstance(value_ptr, list) and all(map(lambda x: isinstance(x, dict), value_ptr)): #可能遍历过程会出现一个列表，然后列表的每个元素是字典（There might be a list during the traversal, each element of which is a dictionary）
            for j in range(len(value_ptr)):
                element = value_ptr[j]
                status = traverse_keyPath(keys, keys_count, keys_to_insert, element, keyPath[i:], targetTypes = targetTypes, allowNoneType = allowNoneType)
                if status == -1: #在遍历过程中发生任何异常，则直接退出遍历，从而不会添加任何数据（If any exception occurs, traversal will be stopped, thus no data will be added）
                    return 1
        elif isinstance(value_ptr, dict):
            if key in value_ptr:
                value_ptr = value_ptr[key]
            else: #要求用户必须输入完全正确的键路径（This required the user to pass a completely valid `keyPath`）
                return 1
        else: #键路径中任何一个节点得到的值的类型不正确时，视为键路径不正确（When the type of any value obtained on one node isn't correct, `keyPath` is regarded as invalid）
            return 1
    else:
        if isinstance(value_ptr, dict):
            index: int = 0 #指示要插入的键的下标。每切换一个对象，该下标重置为0（Denotes the index to insert a key. Every time another object is to traverse, this index becomes 0）
            valueType: str = value_ptr.get("__type", "None")
            if targetTypes == None or isinstance(targetTypes, list) and valueType in targetTypes and (allowNoneType or valueType != "None"): #校验值类型（Verify the value type）
                if not valueType in keys:
                    keys[valueType] = []
                if not valueType in keys_count:
                    keys_count[valueType] = {}
                if not valueType in keys_to_insert:
                    keys_to_insert[valueType] = []
                for key1 in value_ptr.keys():
                    if key1 in keys[valueType]:
                        while len(keys_to_insert[valueType]) > 0:
                            keys[valueType].insert(index, keys_to_insert[valueType].pop(0))
                            index += 1 #每插入一个元素，下标加1（Every time an element is inserted, increment the index）
                        index = keys[valueType].index(key1) + 1 #每识别到一个已存在的元素，下标更新为该元素后的位置（Every time an element already exists, update the index as the location following this element）
                        keys_count[valueType][key1] += 1
                    else:
                        if not key1 in keys_to_insert[valueType]: #在处理列表时，往往会遍历到相同格式的字典。要防止将它们重复加入待插入的键列表中（When processing a list, the program often traverses dictionaries of the same format. We should prevent adding them repeatedly into the list of keys to be inserted）
                            keys_to_insert[valueType].append(key1)
                        keys_count[valueType][key1] = 1
                syncListOrder(keys[valueType], list(value_ptr.keys())) #根据每个新遍历到的字典的键列表，校正keys中已有的键列表的顺序（Correct the order of the existing key list in `keys` according to that of the key list of the new dictionary `value_ptr`）
        elif isinstance(value_ptr, list) and all(map(lambda x: isinstance(x, dict), value_ptr)): #需要考虑末端是一个列表的情形（The current value after traversal may be a list. This should be taken into consideration）
            for i in range(len(value_ptr)):
                element: dict[str, Any] = value_ptr[i]
                status = traverse_keyPath(keys, keys_count, keys_to_insert, element, [], targetTypes = targetTypes, allowNoneType = allowNoneType)
        # else: #当用户输入的键路径不完整时，键列表和键频数统计字典中不会添加任何东西（When `keyPath` isn't complete, nothing will be added into `keys` and `keys_count`）
    return 0

def getBinaryKeys(data: dict[str, Any], isBin: bool = True, objectTypes: Any = None, keyPaths: Any = None, targetTypes: Optional[list[str]] = None, allowNoneType: bool = True) -> tuple[dict[str, list[str]], dict[str, dict[str, int]]]: #字典keys方法的进阶版本，列出一个二进制描述中某种数据类型经过某个键路径得到的所有值字典的键（An advanced version of `keys` method of a dictionary. This function list all keys of the value list following the path of keys from an object of a specified type in a binary description）
    '''
    :param data: 数据字典。一般是二进制描述数据。<br>A data dictionary, which is usually a binary description.
    :type data: dict[str, Any]
    :param isBin: 数据对象是否是从英雄联盟的.wad.client文件中提取得到的二进制描述。默认为真。<br>Whether `data` is extracted from ".wad.client" files of League of Legends. True by default.
    
        这类数据的特征如下：<br>Features of this kind of data are as follows:
        1. 包含一个“__linked”键，其值是一个列表，存储与之相关的二进制描述文件路径。<br>Contains a "__linked" key, whose value is a list that stores related binary description file paths.
        2. 其它所有键值对都由主键和数据对象构成，且数据对象必定包含一个“__type”键，该键的值是一个字符串，表示该数据对象的类型。<br>Any other key-value pair is composed of a primary key and a data object. The data object contains a "__type" key at least, whose value is a string that shows the type of this object.
    :type isBin: bool
    :param objectTypes: 一级值类型，可以传入单个字符串，也可以传入由字符串组成的列表。如果不指定，则对所有类型的数据进行汇总。<br>`objectTypes` refers to the first-level value's type. Both a single string and a list composed of strings are allowed to pass. If unspecified, all kinds of data will be traversed.
    :type objectTypes: str | list[str] | None
    :param keyPaths: 由字符串组成的列表或是一个字符串，这些字符串由路径的每个键用竖线连接而成。在遍历到列表时，函数会自动遍历列表的每个元素，而不需要用户在键路径中指定该列表的整数下标。<br>`keyPaths` is a list of strings or a string, each of which is keys in the path concatenated by "|". If a list is obtained during the traversal, before the traversal completes, the function will traverse each element in this list, so the user doesn't need to explicitly specify the integer index of the list as a part of the keyPath.<br>对于二进制描述数据而言，从字典的每个值开始遍历；对于普通字典而言，从整个字典开始遍历，即从键开始遍历。<br>For binary description data, the traversal starts from each value of the dictionary. For a normal dictionary, the traversal starts from the whole dictionary, namely from the keys.
    :type keyPaths: str | list[str] | None
    :param targetTypes: 由字符串组成的列表，这些字符串代表值类型。该参数用来校验值指针在遍历完keyPaths参数中的每个键路径后得到的值类型是否属于targetTypes中的一个，如果不属于，则跳过该值中的所有键。指定为None时，禁用对象类型校验。<br>`targetTypes` is a list of strings, each of which represents the value type. This parameter is designed to verify whether the type of the value obtained after traversing throughout each keyPath in `keyPaths` corresponds to one of `targetTypes`. If not, the function will skip all keys in this value. When this parameter is specified as `None`, object type verification will be disabled.
    :type targetTypes: list[str] | None
    :param allowNoneType: 仅在指定targetTypes参数时发挥作用。有时，在遍历完某个键路径后，得到的值字典中没有类型，具体地说是没有“__type”键。这类值字典的类型视为NoneType。默认情况下，函数会统计这类值字典的键，但用户可以将其置为假以跳过这类值字典的键的统计。<br>`allowNoneTypes` only makes a difference when `targetTypes` is specified. Sometimes, after traversing throughout some keyPath, the obtained dictionary doesn't have a type. That is, it doesn't have "__type" key. This kind of value dictionary is regarded as of NoneType. By default, the function will consider this kind of value's keys, but the user can set it as False to skip counting these keys.
    :type allowNoneType: bool
    :return: 返回一个元组，第一个元素是一个字典，键是键路径指向的对象的类型，值是由键路径指向的对象的所有键组成的列表。第二个元素是一个字典，键和第一个元素的键相同，值是第一个元素的值的频数统计字典，其中键是键路径指向的对象的键，值是该键在键路径指向的所有对象中的出现次数。<br>Returns a tuple, the first element of which is a dictionary. Each key of this dictionary is the type of the object obtained by traversing throughout `keyPath`. Each value of this dictionary is a list of all keys of the object obtained by traversing throughout `keyPath`. The second element of the tuple is also a dictionary, each key of which is the same as that of the first element. Each value of this dictionary is a frequency distribution dictionary of that of the first element, where each subkey is a key of the object obtained by traversing throughout `keyPath` and each subvalue is the occurrence of this subkey in that object.
    :rtype: tuple[dict[str, list[str]], dict[str, dict[str, int]]]
    '''
    if objectTypes == None:
        objectTypeList: list[str] = []
    elif isinstance(objectTypes, str):
        objectTypeList = [objectTypes]
    elif isinstance(objectTypes, list) and all(map(lambda x: isinstance(x, str), objectTypes)):
        objectTypeList = objectTypes[:]
    else:
        print("错误：您传入的对象类型有误。请检查。函数将返回空列表。\nError: The format of the passed object types is invalid. Please check it. The function will return an empty list instead.")
        return ({}, {})
    if keyPaths == None:
        keyPathList: list[list[str]] = [[]]
    elif isinstance(keyPaths, str):
        keyPathList = [keyPaths.split("|")]
    elif isinstance(keyPaths, list) and all(map(lambda x: isinstance(x, str), keyPaths)):
        keyPathList = list(map(lambda x: x.split("|"), keyPaths))
    else:
        print(f"警告：您传入的键路径有误。请检查。函数将返回{objectTypes}类对象直属的键。\nWarning: Invalid `keyPath`! Please check it. The function will return the keys directly under the objects of {objectTypes} type.")
        keyPathList = [[]]
    if isinstance(data, dict):
        keys: dict[str, list[str]] = {}
        keys_count: dict[str, dict[str, int]] = {}
        keys_to_insert: dict[str, list[str]] = {}
        if isBin:
            for (key, value) in data.items():
                index = 0
                if key != "__linked" and (len(objectTypeList) == 0 or any(map(lambda x: re.fullmatch(x, value["__type"]), objectTypeList))): #如果没有指定任何对象类型，则搜索所有对象（If there's not any object type specified, search all objects）
                    for keyPath in keyPathList: #此时，keyPath已被转换为不带竖线的键字符串组成的列表（Now, `keyPath` has been transformed into a list of key strings without "|"）
                        status: int = traverse_keyPath(keys, keys_count, keys_to_insert, value, keyPath, targetTypes = targetTypes, allowNoneType = allowNoneType)
                        for valueType in keys_to_insert:
                            while len(keys_to_insert[valueType]) > 0: #执行完上面的循环后，可能还有键未插入（After the above loop finishes, there may be some keys not inserted yet）
                                keys[valueType].append(keys_to_insert[valueType].pop(0))
        else:
            for keyPath in keyPathList:
                status = traverse_keyPath(keys, keys_count, keys_to_insert, data, keyPath, targetTypes = targetTypes, allowNoneType = allowNoneType)
                for valueType in keys_to_insert:
                    while len(keys_to_insert[valueType]) > 0: #执行完上面的循环后，可能还有键未插入（After the above loop finishes, there may be some keys not inserted yet）
                        keys[valueType].append(keys_to_insert[valueType].pop(0))
        keys_count_sorted: dict[str, dict[str, int]] = {}
        for objectType in keys_count: #将频数统计字典的键的顺序按照概要顺序排列（Order the keys of the frequency distribution dictionary as that of the schemas order）
            keys_count_sorted[objectType] = {_: keys_count[objectType][_] for _ in keys[objectType]}
        return (keys, keys_count_sorted)
    else:
        print("您传入的二进制描述数据格式有误。请检查。函数将返回空列表。\nThe format of the passed binary description data is invalid. Please check it. The function will return an empty list instead.")
        return ({}, {})

#定义数据导出类（Define the data export class）
class LoLDataExtractor:
    #定义类属性，作为类内临时使用的全局变量（Define class attributes as temporarily used global variables within the class）
    calculatedVariables: dict[str, dict[Literal["value", "__type"], str | dict[str, str]]] = {} #缓存同一个说明文本中计算过的变量。切换到下一个说明文本时清空（Cache the variables that have been calculated before while transforming a tooltip. When another tooltip is to transform, this variable is cleaned）
    mSpells: dict[str, Any] = {} #收录某个二进制描述数据中所有的技能指令对象。键是每个技能指令对象的mScriptName键的值，值是每个技能指令对象（Collect all SpellObjects in binary description data. Each key is the value of the `mScriptName` key of a SpellObject, and its value is this SpellObject）
    # mItems: dict[str, Any] = {} #收录装备二进制描述数据中所有的装备对象。键是每个装备数据对象的装备序号，值是每个装备数据对象（Collect all ItemData objects in item binary description data. Each key is the value of `itemID` key of an ItemData object, and each value is this ItemData object）
    TFTUnitPropertyMap: dict[str, Any] = {} #收录聚点危机地图二进制描述数据中的单位属性定义对象。键是每个单位属性定义对象的名称，值是每个单位属性定义对象（Collect TftUnitPropertyDefinition objects in Convergence map's binary description data. Each key is the value of `name` key of a TftUnitPropertyDefinition object, and its value is this TftUnitPropertyDefinition object）
    TFTTraitMap: dict[str, Any] = {} #收录聚点危机地图二进制描述数据中的羁绊对象。键是每个羁绊对象的名称，值是每个羁绊对象（Collect TftTraitData objects in Convergence map's binary description data. Each key is the value of `name` key of a TftTraitData object, and its value is this TftTraitData object）
    TFTScriptDataMap: dict[str, Any] = {} #收录聚点危机地图二进制描述数据中的指令数据对象。键是每个指令数据对象的名称，值是每个指令数据对象（Collect ScriptDataObjects in Convergence map's binary description data. Each key is the value of `name` key of a ScriptDataObject, and its value os this ScriptDataObject）
    Spell_tooltip_map: dict[str, Any] = {} #收录角色二进制描述数据中所有技能说明文本对应的技能指令对象。键是技能说明文本键，值是每个技能指令对象（Collect all SpellObjects that has spell tooltip key in character binary description data. Each key is a value of `keyTooltip`, and each value is the corresponding SpellObject）
    data_cache: dict[str, dict[str, Any]] = {"online": {}, "local": {}} #每个链接或路径指向的Json对象的缓存（Caches of Json objects directed by each URL or path）
    merged_data_cache: dict[str, Any] = {} #每个变量名代表的变量的缓存。在设计初衷上，这个数据结构只缓存那些获取较为麻烦的合并后的数据字典（Caches of the variables that the name keys represent. By design, this data structure only caches those data dictionaries hard to obtain）
    
    #初始化类（Initialize class）
    def __init__(self, version: str, locale: str, session: Optional[requests.Session] = None, log: Optional[LogManager] = None) -> None:
        '''
        初始化数据提取器类对象。<br>Initialize the `LoLDataExtractor` class object.
        
        :param version: CommunityDragon文件夹名称。<br>CommunityDragon folder name.
        :type version: str
        :param locale: 语言文化代码，如“en_US”和“zh_CN”。<br>Language code, such as "en_US" and "zh_CN".
        :type locale: str
        :param session: 可选参数。传入一个requests会话对象以复用该会话对象的连接。如果不指定，则在内部自动新建一个会话，对外不可见。<br>An optional parameter. Pass in a requests session object to reuse the connections of this session object. If unspecified, a new session will be created internally, invisible to outside.
        :type session: requests.Session
        :param log: 可选参数。日志管理对象。传入以同时将输入和输出保存到一个日志文件中。如果不指定，则在内部自动新建一个空白日志管理对象，对外不可见，只输出到终端中。<br>An optional parameter. A `LogManager` object. Pass in an object to save input and output to a local log file. If unspecified, an empty `LogManager` object will be created internally, invisible to outside, so that content will only be output to terminal.
        :type log: LogManager
        '''
        self.version: str = version #CommunityDragon文件夹名称（CommunityDragon folder name）
        self.locale: str = locale
        self.language_folder: str = "default" if locale == "en_US" else locale.lower()
        self.CHS_PUNCMARKS: set[str] = {"ja_JP", "ko_KR", "zh_CN", "zh_MY", "zh_TW"} #使用中文标点符号的语言（Languages that use Chinese punctuation marks）
        self.session: requests.Session = requests.Session() if session == None else session
        self.log: LogManager = LogManager() if log == None else log
        self.patch: str = "" #完整版本号（Complete version）
        self.patch_number: str = "" #完整版本号的数字部分（The digit part of the complete version）
        self.version_df: pandas.DataFrame = pandas.DataFrame() #覆盖每个工作簿A1单元格的版本数据框（Version dataframe that overlays each workbook's A1 cell）
        self.folder: str = "" #工作簿的保存目录（Directory of the workbook to export into）
        self.wbPath: str = "" #工作簿的路径（Path of the workbook to export）
        self.sheet_naming_fold: bool = False #工作表是否使用适用于在同一个工作簿中展现不同版本数据的命名方式（Whether the sheet uses the naming system that favors displaying data of different versions in a single workbook）
        self.fileExportList_ready: bool = False #标记文件导出列表是否准备就绪（Marks whether the file export list is prepared）
        self.files_exported: list[str] = [] #文件导出列表（File export list）
        self.shared_ready: bool = False #标记共享数据是否准备就绪（Marks whether shared data are prepared）
        self.shared_bin: dict[str, list[str] | dict[str, Any]] = {} #共享数据（Shared data）
        self.strtable_organize_manner: Literal[1, 2] = 1 #字符串常量池网址策略。值为1代表分成英雄联盟和云顶之弈，值为2代表集中存放（Stringtable url strategy. When it equals one, stringtables are divided into a LoL file and a TFT file. When it equals two, stringtables are stored in a single file）
        self.strtables_ready: dict[str, bool] = {"lol_target": False, "lol_default": False, "tft_target": False, "tft_default": False, "target": False, "default": False} #标记字符串常量池是否准备就绪（Marks whether stringtables are prepared）
        self.lolstringtable_target: dict[str, int | dict[str, str]] = {"entries": {}, "version": 5}
        self.lolstringtable_default: dict[str, int | dict[str, str]] = {"entries": {}, "version": 5}
        self.tftstringtable_target: dict[str, int | dict[str, str]] = {"entries": {}, "version": 5}
        self.tftstringtable_default: dict[str, int | dict[str, str]] = {"entries": {}, "version": 5}
        self.mainstringtable_target: dict[str, int | dict[str, str]] = {"entries": {}, "version": 5}
        self.mainstringtable_default: dict[str, int | dict[str, str]] = {"entries": {}, "version": 5}
        self.optimize_tooltip_layout: bool = True #是否对说明文本的布局进行优化。决定变量代换时使用tooltipTransform还是tooltipSubstitute方法（Whether to optimize the layout of tooltips. Determines which one of `tooltipTransform` and `tooltipSubstitute` is used during variable substitution）
        self.tooltipConvert: Callable[[str, dict[str, int | dict[str, str]], dict[str, Any], bool, bool, bool, dict[str, dict[str, Any] | Any] | None], str] = self.tooltipTransform #说明文本转换方法（Tooltip transformation method）
        self.reserve_variable: bool = False #是否在变量代换时保留变量名。如果保留，则说明文本会同时带有变量名和值。这个属性应只在本基类中声明（Whether to reserve the variable during its substitution. If reserve, then the tooltip will have both name and value of the variable. This attribute should only be declared in this base class）
    
    def make_dir(self) -> None: #基于对象创建保存目录。对外使用（Create the export directory based on the object. For outside use）
        '''
        基于用户传入的文件夹或者通过set_dir方法指定的文件夹新建保存目录。<br>Create the export directory based on the folder passed in by the user or specified by `set_dir` method.
        
        该方法优先使用folder属性指定的目录，其次使用wbPath属性指定的目录。<br>This method uses the directory specified by `folder` attribute first, and then that specified by `wbPath` attribute.
        '''
        logPrint = self.log.logPrint
        if self.folder != "":
            os.makedirs(self.folder)
        elif self.wbPath != "":
            self.folder = os.path.dirname(self.wbPath)
            os.makedirs(self.folder)
        else:
            logPrint("尚未指定文件保存目录！\nExport directory not specified yet!")
            
    def set_dir(self, folder: str) -> str: #手动指定保存目录。对外使用（Manually specify the export directory. For outside use）
        '''
        手动设置工作簿的保存目录。<br>Manually set the export directory of the workbook.
        
        :param folder: 工作簿导出目录。<br>Workbook export directory.
        :type folder: str
        :return: 目录字符串。反斜杠将被替换为斜杠。<br>Directory string. Backslashes will be replaced by forward slashes.
        :rtype: str
        '''
        self.folder = folder.replace("\\", "/")
        return self.folder
    
    def set_path(self, wbPath: str) -> str: #手动指定工作簿路径。对外使用（Manually specify the workbook path. For outside use）
        '''
        手动设置工作簿的保存路径。<br>Manually set the workbook path.
        
        :param folder: 工作簿的路径。<br>Workbook path.
        :type folder: str
        :return: 工作簿路径字符串。反斜杠将被替换为斜杠。<br>Workbook path string. Backslashes will be replaced by forward slashes.
        :rtype: str
        '''
        self.wbPath = wbPath.replace("\\", "/")
        return self.wbPath
    
    def encapsulate(self) -> bool: #将所有版本的数据保存到一个工作簿中（Save all patches into one workbook）
        '''
        将本类的sheet_naming_fold属性置为真，即所有版本的数据保存为名为版本号加内容的工作表，然后保存在同一个工作簿中。<br>Set the `sheet_naming_fold` attribute of this class to True, that is, data of all patches are saved as sheets named by patch number plus content, and then stored in a single workbook
        '''
        self.sheet_naming_fold = True
        return self.sheet_naming_fold
        
    def decapsulate(self) -> bool: #不同版本的数据保存到不同工作簿中（Export for each workbook per patch）
        '''
        将本类的sheet_naming_fold属性置为假，即不同版本的数据保存为不同工作簿。工作簿默认情况下带有版本号。<br>Set the `sheet_naming_fold` attribute of this class to False, that is, data of different patches are saved as different workbooks. The name of the workbook contains the patch number by default.
        '''
        self.sheet_naming_fold = False
        return self.sheet_naming_fold
    
    @classmethod
    def clear_cache(cls) -> None: #清空缓存（Clear data cache）
        '''
        清空所有在线和离线数据缓存。一般情况下，在切换版本时需要调用此方法。<br>Clear all online and local data caches. Basically, this method only needs to be called when the user switches to another version.
        '''
        cls.calculatedVariables.clear()
        cls.mSpells.clear()
        # cls.mItems.clear()
        cls.TFTUnitPropertyMap.clear()
        cls.TFTTraitMap.clear()
        cls.TFTScriptDataMap.clear()
        cls.Spell_tooltip_map.clear()
        cls.data_cache["online"].clear()
        cls.data_cache["local"].clear()
        cls.merged_data_cache.clear()
    
    #获取版本数据框（Obtain version dataframe）
    def init_patch(self) -> None:
        '''
        将版本和版本号初始化为空字符串。<br>Initialize patch and patch number as empty strings.
        '''
        self.patch = self.patch_number = ""
        self.version_df = pandas.DataFrame()
    
    def init_path_and_dir(self) -> None | tuple[str, str]: #基于对象的版本号初始化保存目录和工作簿路径（Initialize the export directory and the workbook path based on the patch number of the object）
        '''
        在指定版本号的情况下，初始化工作簿输出目录及其路径。<br>When the patch number is specified, initialize the export directory and its path of the workbook.
        '''
        logPrint = self.log.logPrint
        if self.patch == "":
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
        else:
            self.folder = os.path.expanduser("~/Desktop")
            if self.sheet_naming_fold:
                self.wbPath = os.path.join(self.folder, "游戏数据提取_AllPatches.xlsx").replace("\\", "/")
            else:
                self.wbPath = os.path.join(self.folder, f"游戏数据提取_{self.patch}.xlsx").replace("\\", "/")
            return (self.folder, self.wbPath)
    
    def get_version(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线加载游戏版本，并生成游戏版本数据框。<br>Load the game version online and generate the game version dataframe.
        '''
        logPrint = self.log.logPrint
        game_version_url: str = f"https://raw.communitydragon.org/{self.version}/compat-version-metadata.json"
        source, status, self.session = requestUrl("GET", game_version_url, session = self.session, log = self.log)
        if status != 200:
            if status == -1:
                logPrint("游戏版本获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nGame version capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
            elif status == 404:
                logPrint("游戏版本获取失败！请检查以下链接的可用性。程序即将退出此版本。\nGame version capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(game_version_url))
            time.sleep(3)
            self.init_patch()
            return
        game_version: dict[str, str] = source.json()
        #数据框构建（Build the dataframe）
        self.patch = game_version["version"]
        self.patch_number = re.search(r"[\d\.]+", self.patch).group()
        self.version_df = pandas.DataFrame(game_version, index = [0])
        self.init_path_and_dir() #供用户使用（For user use）
    
    def read_version(self, game_version_path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        读取本地游戏版本文件，并生成游戏版本数据框。<br>Read the local game version file and generate the game version dataframe.
        
        :param game_version_path: 版本号文件，通常以“compat-version-metadata.json”结尾。<br>Version file, usually endswith "compat-version-metadata.json".
        :type game_version_path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(game_version_path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{game_version_path}")
            return
        with open(game_version_path, "r", encoding = "utf-8") as fp:
            game_version: dict[str, str] = json.load(fp)
        #数据框构建（Build the dataframe）
        self.patch = game_version["version"]
        self.patch_number = re.search(r"[\d\.]+", self.patch).group()
        self.version_df = pandas.DataFrame(game_version, index = [0])
        self.init_path_and_dir() #供用户使用（For user use）
    
    #获取文件导出列表（Get file export list）
    def init_fileExportList_readiness(self) -> None:
        '''
        将文件导出列表准备就绪状态初始化为未就绪。<br>Initialize the file export list readiness state as not ready.
        '''
        self.fileExportList_ready = False
    
    def get_exported_files(self) -> None: ##在线加载——供用户使用（Online loading - For user use）
        '''
        在线记载文件导出列表。<br>Load the file export list online.
        '''
        logPrint = self.log.logPrint
        file_exported_url: str = f"https://raw.communitydragon.org/{self.version}/cdragon/files.exported.txt"
        source, status, self.session = requestUrl("GET", file_exported_url, session = self.session, log = self.log)
        if status != 200:
            if status == -1:
                logPrint("文件导出列表获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nFile export list capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
            elif status == 404:
                logPrint("文件导出列表获取失败！请检查以下链接的可用性。程序即将退出此版本。\nFile export list capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(file_exported_url))
            time.sleep(3)
            self.init_fileExportList_readiness()
            return
        self.files_exported = source.text.splitlines()
        self.fileExportList_ready = True
    
    def read_exported_files(self, path: str) -> None: ##离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线读取文件导出列表。<br>Read the file export list offline.
        '''
        logPrint = self.log.logPrint
        #检查路径是否存在（Check if the path exist）
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_fileExportList_readiness()
            return
        with open(path, "r", encoding = "utf-8") as fp:
            self.files_exported = fp.read().splitlines()
        self.fileExportList_ready = True

    #获取共有数据（Get common data）
    def get_shared_data(self) -> None: ##在线加载——供用户使用（Online loading - For user use）
        '''
        在线加载共享数据。<br>Load shared data online.
        '''
        logPrint = self.log.logPrint
        shared_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/shared.cdtb.bin.json"
        if shared_bin_url in self.__class__.data_cache["online"]:
            self.shared_bin = self.__class__.data_cache["online"][shared_bin_url]
        else:
            source, status, self.session = requestUrl("GET", shared_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == -1:
                    logPrint("共享数据获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nShared data capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
                elif status == 404:
                    logPrint("共享数据获取失败！请检查以下链接的可用性。程序即将退出此版本。\nShared data capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(shared_bin_url))
                time.sleep(3)
                self.init_strtable_readiness()
                return
            self.shared_bin = source.json()
            self.__class__.data_cache["online"][shared_bin_url] = self.shared_bin
        self.shared_ready = True
    
    def read_shared_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线读取共享数据。<br>Read shared data offline.
        '''
        logPrint = self.log.logPrint
        #检查路径是否存在（Check if the path exist）
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.shared_ready = False
            return
        shared_bin_path: str = path
        if shared_bin_path in self.__class__.data_cache["local"]:
            self.shared_bin = self.__class__.data_cache["local"][shared_bin_path]
        else:
            with open(shared_bin_path, "r", encoding = "utf-8") as fp:
                self.shared_bin = json.load(fp)
            self.__class__.data_cache["local"][shared_bin_path] = self.shared_bin
        self.shared_ready = True
    
    def init_mSpells(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        基于共享数据初始化指令字典和从说明文本（keyTooltip）键到指令对象的映射字典。<br>Initialize the spell dictionary and the mapping dictionary from tooltip key (`keyTooltip`) to spell object based on shared data.
        '''
        logPrint = self.log.logPrint
        if not self.shared_ready:
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return
                else:
                    self.read_shared_data(path = path)
            else:
                self.get_shared_data()
            if not self.shared_ready:
                logPrint("共享数据尚未准备就绪！\nShared data not prepared!")
        for (key, value) in self.shared_bin.items():
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
                tmp_ptr: Any = value
                subkeyList: list[str] = ["mSpell", "mClientData", "mTooltipData", "mLocKeys", "keyTooltip"]
                for tmp_key in subkeyList:
                    if tmp_key in tmp_ptr:
                        tmp_ptr = tmp_ptr[tmp_key]
                    else:
                        break
                else:
                    self.__class__.Spell_tooltip_map[tmp_ptr] = value
    
    def init_strtable_readiness(self) -> None:
        '''
        将字符串常量池准备就绪状态初始化为未就绪。<br>Initialize the stringtable readiness state as not ready.
        '''
        self.strtables_ready = {key: False for key in self.strtables_ready}
    
    def get_strtable(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线加载字符串常量池。<br>Load stringtables online.
        
        注意，不同版本的字符串常量池的相对路径不同。<br>Note that the relative paths of stringtables differ in different patches.
        '''
        logPrint = self.log.logPrint
        if Patch(self.version) < Patch("14.15"): #根据版本确定字符串常量池的网址（Determine stringtable url according to version）
            self.strtable_organize_manner = 2
            if Patch(self.version) < Patch("12.23"):
                mainstringtable_target_url: str = f"https://raw.communitydragon.org/%s/game/data/menu/fontconfig_%s.txt.json" %(self.version, self.locale.lower())
                mainstringtable_default_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/menu/fontconfig_en_us.txt.json"
            elif Patch(self.version) < Patch("14.4"):
                mainstringtable_target_url: str = f"https://raw.communitydragon.org/%s/game/data/menu/main_%s.stringtable.json" %(self.version, self.locale.lower())
                mainstringtable_default_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/menu/main_en_us.stringtable.json"
            else:
                mainstringtable_target_url: str = f"https://raw.communitydragon.org/%s/game/%s/data/menu/en_us/main.stringtable.json" %(self.version, self.locale.lower())
                mainstringtable_default_url: str = f"https://raw.communitydragon.org/{self.version}/game/en_us/data/menu/en_us/main.stringtable.json"
            #目标语言的字符串常量池（Stringtable in target language）
            if mainstringtable_target_url in self.__class__.data_cache["online"]:
                self.mainstringtable_target = self.__class__.data_cache["online"][mainstringtable_target_url]
            else:
                source, status, self.session = requestUrl("GET", mainstringtable_target_url, session = self.session, log = self.log)
                if status != 200:
                    if status == -1:
                        logPrint("目标语言的字符串常量池获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nStringtable in target language capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
                    elif status == 404:
                        logPrint("目标语言的字符串常量池获取失败！请检查以下链接的可用性。程序即将退出此版本。\nStringtable in target language capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(mainstringtable_target_url))
                    time.sleep(3)
                    self.init_strtable_readiness()
                    return
                self.mainstringtable_target = source.json()
                self.__class__.data_cache["online"][mainstringtable_target_url] = self.mainstringtable_target
            self.strtables_ready["target"] = True
            #默认语言的字符串常量池（Stringtable in default language）
            if mainstringtable_default_url in self.__class__.data_cache["online"]:
                self.mainstringtable_default = self.__class__.data_cache["online"][mainstringtable_default_url]
            else:
                source, status, self.session = requestUrl("GET", mainstringtable_default_url, session = self.session, log = self.log)
                if status != 200:
                    if status == -1:
                        logPrint("默认语言的字符串常量池获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nStringtable in default language capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
                    elif status == 404:
                        logPrint("默认语言的字符串常量池获取失败！请检查以下链接的可用性。程序即将退出此版本。\nStringtable in default language capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(mainstringtable_default_url))
                    time.sleep(3)
                    self.init_strtable_readiness()
                    return
                self.mainstringtable_default = source.json()
                self.__class__.data_cache["online"][mainstringtable_default_url] = self.mainstringtable_default
            self.strtables_ready["default"] = True
        else:
            self.strtable_organize_manner = 1
            lolstringtable_target_url: str = f"https://raw.communitydragon.org/%s/game/%s/data/menu/en_us/lol.stringtable.json" %(self.version, self.locale.lower())
            lolstringtable_default_url: str = f"https://raw.communitydragon.org/{self.version}/game/en_us/data/menu/en_us/lol.stringtable.json"
            tftstringtable_target_url: str = "https://raw.communitydragon.org/%s/game/%s/data/menu/en_us/tft.stringtable.json" %(self.version, self.locale.lower())
            tftstringtable_default_url: str = f"https://raw.communitydragon.org/{self.version}/game/en_us/data/menu/en_us/tft.stringtable.json"
            #目标语言的英雄联盟字符串常量池（LoL stringtable in target language）
            if lolstringtable_target_url in self.__class__.data_cache["online"]:
                self.lolstringtable_target = self.__class__.data_cache["online"][lolstringtable_target_url]
            else:
                source, status, self.session = requestUrl("GET", lolstringtable_target_url, session = self.session, log = self.log)
                if status != 200:
                    if status == -1:
                        logPrint("目标语言的英雄联盟字符串常量池获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nLoL stringtable in target language capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
                    elif status == 404:
                        logPrint("目标语言的英雄联盟字符串常量池获取失败！请检查以下链接的可用性。程序即将退出此版本。\nLoL stringtable in target language capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(lolstringtable_target_url))
                    time.sleep(3)
                    self.init_strtable_readiness()
                    return
                self.lolstringtable_target = source.json()
                self.__class__.data_cache["online"][lolstringtable_target_url] = self.lolstringtable_target
            self.strtables_ready["lol_target"] = True
            #默认语言的英雄联盟字符串常量池（LoL stringtable in default language）
            if lolstringtable_default_url in self.__class__.data_cache["online"]:
                self.lolstringtable_default = self.__class__.data_cache["online"][lolstringtable_default_url]
            else:
                source, status, self.session = requestUrl("GET", lolstringtable_default_url, session = self.session, log = self.log)
                if status != 200:
                    if status == -1:
                        logPrint("默认语言的英雄联盟字符串常量池获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nLoL stringtable in default language capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
                    elif status == 404:
                        logPrint("默认语言的英雄联盟字符串常量池获取失败！请检查以下链接的可用性。程序即将退出此版本。\nLoL stringtable in default language capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(lolstringtable_default_url))
                    time.sleep(3)
                    self.init_strtable_readiness()
                    return
                self.lolstringtable_default = source.json()
                self.__class__.data_cache["online"][lolstringtable_default_url] = self.lolstringtable_default
            self.strtables_ready["lol_default"] = True
            #目标语言的云顶之弈字符串常量池（TFT stringtable in target language）
            if tftstringtable_target_url in self.__class__.data_cache["online"]:
                self.tftstringtable_target = self.__class__.data_cache["online"][tftstringtable_target_url]
            else:
                source, status, self.session = requestUrl("GET", tftstringtable_target_url, session = self.session, log = self.log)
                if status != 200:
                    if status == -1:
                        logPrint("目标语言的云顶之弈字符串常量池获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nTFT stringtable in target language capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
                    elif status == 404:
                        logPrint("目标语言的云顶之弈字符串常量池获取失败！请检查以下链接的可用性。程序即将退出此版本。\nTFT stringtable in target language capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(tftstringtable_target_url))
                    time.sleep(3)
                    self.init_strtable_readiness()
                    return
                self.tftstringtable_target = source.json()
                self.__class__.data_cache["online"][tftstringtable_target_url] = self.tftstringtable_target
            self.strtables_ready["tft_target"] = True
            #默认语言的云顶之弈字符串常量池（TFT stringtable in default language）
            if tftstringtable_default_url in self.__class__.data_cache["online"]:
                self.tftstringtable_default = self.__class__.data_cache["online"][tftstringtable_default_url]
            else:
                source, status, self.session = requestUrl("GET", tftstringtable_default_url, session = self.session, log = self.log)
                if status != 200:
                    if status == -1:
                        logPrint("默认语言的云顶之弈字符串常量池获取失败！请检查系统网络状况和代理设置。程序即将退出此版本。\nTFT stringtable in default language capture failure! Please check the system network condition and agent configuration. The program will quit this version soon.")
                    elif status == 404:
                        logPrint("默认语言的云顶之弈字符串常量池获取失败！请检查以下链接的可用性。程序即将退出此版本。\nTFT stringtable in default language capture failure! Please check the URL availability. The program will quit this version soon.\n%s" %(tftstringtable_default_url))
                    time.sleep(3)
                    self.init_strtable_readiness()
                    return
                self.tftstringtable_default = source.json()
                self.__class__.data_cache["online"][tftstringtable_default_url] = self.tftstringtable_default
            self.strtables_ready["tft_default"] = True
    
    def read_strtable(self, strtable_paths: list[str], dType: Literal[1, 2] = 1) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线读取字符串常量池。<br>Read stringtables offline.
        
        :param strtable_paths: 一个字符串常量池路径列表。<br>A stringtable path list.
        
            - 14.15版本之前：目标语言的英雄联盟字符串常量池路径、默认语言的英雄联盟字符串常量池路径、目标语言的云顶之弈字符串常量池路径和默认语言的云顶之弈字符串常量池路径<br>Before v14.15: LoL stringtable in target language, LoL stringtable in default language (English), TFT stringtable in target language and TFT strigntable in target language (English).
            - 14.15版本及以后：目标语言的字符串常量池路径和默认语言的字符串常量池路径。<br>After v14.15 (including): Stringtable in both target language and default language (English).
        :type strtable_paths: list[str]
        :param dType: 字符串常量池路径组成类型。1对应14.15版本之后；2对应之前。<br>Stringtable path composition type, where 1 corresponds to a version later than v14.15, and 2 corresponds to one earlier.
        :type dType: int
        '''
        logPrint = self.log.logPrint
        #检查路径是否都存在（Check if all paths exist）
        paths_not_found: list[str] = [path for path in strtable_paths if not os.path.exists(path)]
        if len(paths_not_found) > 0:
            logPrint("以下路径不存在：\nThe following path(s) do(es)n't exist:")
            for path in paths_not_found:
                logPrint(path)
            self.init_strtable_readiness()
            return
        if dType == 1: #根据字符串列表组成类型确定字符串常量池的路径（Determine stringtable path according to stringtable list composition type）
            self.strtable_organize_manner = 1
            #目标语言的英雄联盟字符串常量池（LoL stringtable in target language）
            lolstringtable_target_path: str = strtable_paths[0]
            if lolstringtable_target_path in self.__class__.data_cache["local"]:
                self.lolstringtable_target = self.__class__.data_cache["local"][lolstringtable_target_path]
            else:
                with open(lolstringtable_target_path, "r", encoding = "utf-8") as fp:
                    self.lolstringtable_target = json.load(fp)
                self.__class__.data_cache["local"][lolstringtable_target_path] = self.lolstringtable_target
            self.strtables_ready["lol_target"] = True
            #默认语言的英雄联盟字符串常量池（LoL stringtable in default language）
            lolstringtable_default_path: str = strtable_paths[1]
            if lolstringtable_default_path in self.__class__.data_cache["local"]:
                self.lolstringtable_default = self.__class__.data_cache["local"][lolstringtable_default_path]
            else:
                with open(lolstringtable_default_path, "r", encoding = "utf-8") as fp:
                    self.lolstringtable_default = json.load(fp)
                self.__class__.data_cache["local"][lolstringtable_default_path] = self.lolstringtable_default
            self.strtables_ready["lol_default"] = True
            #目标语言的云顶之弈字符串常量池（TFT stringtable in target language）
            tftstringtable_target_path: str = strtable_paths[2]
            if tftstringtable_target_path in self.__class__.data_cache["local"]:
                self.tftstringtable_target = self.__class__.data_cache["local"][tftstringtable_target_path]
            else:
                with open(tftstringtable_target_path, "r", encoding = "utf-8") as fp:
                    self.tftstringtable_target = json.load(fp)
                self.__class__.data_cache["local"][tftstringtable_target_path] = self.tftstringtable_target
            self.strtables_ready["tft_target"] = True
            #默认语言的云顶之弈字符串常量池（TFT stringtable in default language）
            tftstringtable_default_path: str = strtable_paths[3]
            if tftstringtable_default_path in self.__class__.data_cache["local"]:
                self.tftstringtable_default = self.__class__.data_cache["local"][tftstringtable_default_path]
            else:
                with open(tftstringtable_default_path, "r", encoding = "utf-8") as fp:
                    self.tftstringtable_default = json.load(fp)
                self.__class__.data_cache["local"][tftstringtable_default_path] = self.tftstringtable_default
            self.strtables_ready["tft_default"] = True
        else:
            self.strtable_organize_manner = 2
            #目标语言的字符串常量池（Stringtable in target language）
            mainstringtable_target_path: str = strtable_paths[0]
            if mainstringtable_target_path in self.__class__.data_cache["local"]:
                self.mainstringtable_target = self.__class__.data_cache["local"][mainstringtable_target_path]
            else:
                with open(mainstringtable_target_path, "r", encoding = "utf-8") as fp:
                    self.mainstringtable_target = json.load(fp)
                self.__class__.data_cache["local"][mainstringtable_target_path] = self.mainstringtable_target
            self.strtables_ready["target"] = True
            #默认语言的字符串常量池（Stringtable in default language）
            mainstringtable_default_path: str = strtable_paths[1]
            if mainstringtable_default_path in self.__class__.data_cache["local"]:
                self.mainstringtable_default = self.__class__.data_cache["local"][mainstringtable_default_path]
            else:
                with open(mainstringtable_default_path, "r", encoding = "utf-8") as fp:
                    self.mainstringtable_default = json.load(fp)
                self.__class__.data_cache["local"][mainstringtable_default_path] = self.mainstringtable_default
            self.strtables_ready["default"] = True

    @classmethod
    def compute_rsthash(cls, s: str, version: int) -> str: #感谢CommunityDragon社群的Le poussin和Haru提供的支持（Thanks to the help from Le poussin and Haru in CommunityDragon discord server）
        '''
        计算某个字符串键的hash值。<br>Compute the hash value of a string key.
        '''
        hash_int: int = xxh3_64_intdigest(s.lower())
        if version == 5:
            mask: int = (1 << 38) - 1
        else: #version == 4
            mask: int = (1 << 39) - 1
        low_bits: int = hash_int & mask
        result: str = format(low_bits, "010x")
        return "{" + result + "}"
    
    @classmethod
    def compute_binhash(cls, s: str) -> str: #改编自cdtb.binfile.compute_binhash函数（Adapted from `cdtb.binfile.compute_binhash`）
        '''
        计算某个出现在二进制描述文件中的字符串的hash值。<br>Compute the hash value of a string appearing in some binary description file.
        '''
        basis: int = 0x811c9dc5 #偏移基准（Offset basis）
        hash_int: int = basis
        for b in s.encode("ascii").lower():
            hash_int = ((hash_int ^ b) * 0x01000193) % 0x100000000
        result: str = format(hash_int, "08x")
        return "{" + result + "}"
    
    @staticmethod
    def aGet(d: Any, keys: list[Any], default: Any = None) -> Any: #字典进阶get方法（An advanced version of `get` method of a dictionary）
        '''
        对字典get方法的优化。该方法从一个列表中取键的值，如果找到一个键，则返回其值。如果一个键都没有找到，则返回默认值。<br>An optimization of dict `get` method. This method successively gets the value of a key in `keys`. If any key is found, return its value. Otherwise, return the default value.
        
        :param d: 一个字典。如果传入的不是字典，则引发类型错误。<br>A dictionary. A TypeError will be thrown if a non-dict-type variable is passed.
        :type d: dict
        :param keys: 一个键列表，从前到后依次寻找索引。<br>A key list to be indexxed one by one.
        :type keys: list[Any]
        :param default: 在未找到指定值时的默认值。如果未指定，则为None。<br>The default value used when the path of keys isn't found. `None` if unspecified.
        :type default: Any
        :return: 遍历键列表后得到的值。如果没有完成遍历，则返回默认值。<br>A value traversed after traversing the whole key list. If the traversal doesn't finish, return the default value instead.
        :rtype: Any
        '''
        if isinstance(d, dict):
            for key in keys:
                if key in d:
                    return d[key]
            return default
        else:
            raise TypeError("Parameter d must be of dict type.")
    
    @staticmethod
    def dGet(d: Any, key: Any, default: Any = None, ifnan: Any = None) -> Any: #字典非None get方法（`get` method of a dictionary but doesn't like a None returned）
        '''
        对字典get方法的特殊优化。仅用于处理字典中显式声明某个键的值为None的情形。<br>A special optimization of dict `get` method. Only used to handle the case where a key's value is explicitly declared as `None` in a dictionary.
        
        :param d: 一个字典。如果传入的不是字典，则引发类型错误。<br>A dictionary. A TypeError will be thrown if a non-dict-type variable is passed.
        :type d: dict
        :param key: 要查询的键。<br>The key to query.
        :type key: Any
        :param default: 在未找到指定值时的默认值。如果未指定，则为None。<br>The default value used when `key` isn't found. `None` if unspecified.
        :type default: Any
        :param ifnan: 在找到指定键但其值为None时的取值。如果未指定，则为None。<br>The value used when `key` is found but its value is `None`. `None` if unspecified.
        :type ifnan: Any
        '''
        if isinstance(d, dict):
            if key in d:
                value: Any = d[key]
                if value == None:
                    return ifnan
                else:
                    return value
            else:
                return default
        else:
            raise TypeError("Parameter d must be of dict type.")
    
    @classmethod
    def get_strtable_value(cls, strtable: dict[str, int | dict[str, str]], key: str, default: str = "") -> str: #获取某个字符串常量池中某个键的值（Get the value of a key in a stringtable）
        '''
        获取某个字符串常量池中某个键的值。如果键不存在，尝试寻找其hash值，否则返回默认值。<br>Get the value of a key in a stringtable. If the key doesn't exist, try searching for its hash. If the hash isn't found, return the default value.
        
        :param strtable: 字符串常量池。通过session.request.json方法直接获得的对象。<br>Stringtable obtained directly from `session.request.json` method.
        :type strtable: dict[str, int | dict[str, str]]
        :param key: 要查询的键。大小写均可。<br>The key to query in the stringtable. Case insensitive.
        :type key: str
        :param default: 在查不到相关键情况下的默认取值。<br>Default value when `key` isn't found.
        :type default: str
        :return: 字符串常量池中的字符串值。<br>A string value in the stringtable.
        :rtype: str
        '''
        pHash: re.Pattern[str] = re.compile(r"\{\w+\}")
        keys: list[str] = [key.lower()]
        if not pHash.fullmatch(key): #如果传入的key已经是hash值，则不用再求其hash（If `key` is already a hash value, then don't obtain its hash）
            keys.append(cls.compute_rsthash(key.lower(), strtable["version"]))
        return cls.aGet(strtable["entries"], keys = keys, default = default)
    
    #定义说明文本转换函数族（Define tooltip transformation function family）
    @classmethod
    def normalizeBinData(cls, binData: dict[str, Any]):
        '''
        将二进制描述数据进行标准化。往往涉及以下处理：<br>Normalize a binary description, involving the following operations:
        
            - 键名小写。<br>Lower-cased keys.
            - 键值对拷贝，但键转化为hash形式。<br>Copied key-value pairs, but keys transformed into hash form.
            - 部分键值对的适当处理，以便引用。<br>Proper handling of some key-value pairs for reference.
        
        :param binData: 待处理的二进制描述数据。<br>The binary description to process.
        :type binData: dict[str, Any]
        '''
        pHash: re.Pattern[str] = re.compile(r"\{\w+\}")
        if isinstance(binData, dict):
            binData = copy.deepcopy(binData)
            if "DataValues" in binData:
                DataValues: dict[str, dict[str, str | float | list[float]]] = {}
                for spellData in binData["DataValues"]:
                    if "name" in spellData:
                        var: str = spellData["name"].lower() #对变量统一取小写形式，因为原格式存在不一致（Get the lower form of all variables, for some variables may not correspond well with their form in the tooltip）
                    else: #这里不写成`elif "mName" in spellData`是为了在以后出现问题时，由程序直接报错，这样更好发现问题。下同（The reason why I don't write `elif "mName" in spellData` here is that if something wrong occurs to this key, error thrown by the program should make it easier to find the problem. So do the following）
                        var = spellData["mName"].lower()
                    DataValues[var] = spellData
                    if not pHash.fullmatch(var): #当然可以舍弃上面的部分，直接全部采用hash形式，但是既然存储字典存的是引用，多一份数据实际上不会占用太大空间，并且如果全都是hash，调试的时候会非常难辨认（Of course we can abandon the above part and normalize all variables into the hash form, but since dictionaries are cited by reference, a shallow copy won't take up too much extra space. Besides, all variables transformed into hashes will make it obscure for debugging）
                        var_hash: str = cls.compute_binhash(var)
                        DataValues[var_hash] = spellData
                binData["DataValues"] = DataValues
            if "mDataValues" in binData:
                DataValues: dict[str, dict[str, str | float | list[float]]] = {}
                for data in binData["mDataValues"]:
                    if "name" in data:
                        var = data["name"].lower()
                    else:
                        var = data["mName"].lower()
                    DataValues[var] = data
                    if not pHash.fullmatch(var):
                        var_hash = cls.compute_binhash(var)
                        DataValues[var_hash] = data
                binData["mDataValues"] = DataValues
            if "mEffectAmount" in binData and isinstance(binData["mEffectAmount"], dict) and all(map(lambda x: isinstance(x, str), binData["mEffectAmount"].keys())) and all(map(lambda x: isinstance(x, (int, float)), binData["mEffectAmount"].values())): #传说：急速的HastePerStack存在大小写不一致的情况（Case mismatch occurs to Legend: Haste's `HastePerStack` variable）
                mEffectAmount: dict[str, int | float] = {}
                for (key, value) in binData["mEffectAmount"].items():
                    var = key.lower()
                    mEffectAmount[var] = value
                    if not pHash.fullmatch(var):
                        var_hash = cls.compute_binhash(var)
                        mEffectAmount[var_hash] = value
                binData["mEffectAmount"] = mEffectAmount
            if "mSpellCalculations" in binData:
                mSpellCalculations: dict[str, dict[str, Any]] = {}
                for (key, value) in binData["mSpellCalculations"].items():
                    var = key.lower()
                    mSpellCalculations[var] = value
                    if not pHash.fullmatch(var):
                        var_hash = cls.compute_binhash(var)
                        mSpellCalculations[var_hash] = value
                binData["mSpellCalculations"] = mSpellCalculations
            if "mItemCalculations" in binData: #星界驱驰的移速计算存在大小写不一致的情况（Case mismatch occurs to Cosmic Drive's move speed calculation）
                mItemCalculations: dict[str, dict[str, Any]] = {}
                for (key, value) in binData["mItemCalculations"].items():
                    var = key.lower()
                    mItemCalculations[var] = value
                    if not pHash.fullmatch(var):
                        var_hash = cls.compute_binhash(var)
                        mItemCalculations[var_hash] = value
                binData["mItemCalculations"] = mItemCalculations
            if "mCalculations" in binData:
                mCalculations: dict[str, dict[str, Any]] = {}
                for (key, value) in binData["mCalculations"].items():
                    var = key.lower()
                    mCalculations[var] = value
                    if not pHash.fullmatch(var):
                        var_hash = cls.compute_binhash(var)
                        mCalculations[var_hash] = value
                binData["mCalculations"] = mCalculations
            if "DataValuesModeOverride" in binData:
                DataValuesModeOverride: dict[str, dict[str, dict[str, dict[str, str| float | list[float]]]]] = {}
                for gameModeName in binData["DataValuesModeOverride"]:
                    for (key, value) in binData["DataValuesModeOverride"][gameModeName].items():
                        if isinstance(value, list) and all(map(lambda x: isinstance(x, dict), value)):
                            for dataValue in value:
                                if "name" in dataValue or "mName" in dataValue:
                                    if "name" in dataValue:
                                        var = dataValue["name"].lower()
                                    else:
                                        var = dataValue["mName"].lower()
                                    if not var in DataValuesModeOverride:
                                        DataValuesModeOverride[var] = {}
                                    DataValuesModeOverride[var][gameModeName] = dataValue #将变量从列表中提取出来，并且放到模式的上一层（Extract the variable from the data value list and put it as a parent layer of game modes）、
                                    if not pHash.fullmatch(var):
                                        var_hash = cls.compute_binhash(var)
                                        if not var_hash in DataValuesModeOverride:
                                            DataValuesModeOverride[var_hash] = {}
                                        DataValuesModeOverride[var_hash][gameModeName] = dataValue
                binData["DataValuesModeOverride"] = DataValuesModeOverride
            if "mEffectAmountGameMode" in binData:
                mEffectAmountGameMode: dict[str, dict[str, int | float]] = {}
                for gameModeName in binData["mEffectAmountGameMode"]:
                    for (key, value) in binData["mEffectAmountGameMode"][gameModeName]["mEffectAmountPerMode"].items():
                        var = key.lower()
                        if not var in mEffectAmountGameMode:
                            mEffectAmountGameMode[var] = {}
                        mEffectAmountGameMode[var][gameModeName] = value
                        if not pHash.fullmatch(var):
                            var_hash = cls.compute_binhash(var)
                            if not var_hash in mEffectAmountGameMode:
                                mEffectAmountGameMode[var_hash] = {}
                            mEffectAmountGameMode[var_hash][gameModeName] = value
                binData["mEffectAmountGameMode"] = mEffectAmountGameMode
            if "mConditionalTraitSets" in binData: #云顶之弈羁绊的数据只需要转换minUnits和maxUnits，将其首字母变为大写即可（For TFT trait binary data, only capitalizing "minUnits" and "maxUnits" is enough）
                mConditionalTraitSets: list[dict[str, Any]] = []
                for traitSet in binData["mConditionalTraitSets"]:
                    normalizedTraitSet: dict[str, Any] = {}
                    for (key, value) in traitSet.items():
                        if key == "minUnits" or key == "maxUnits":
                            normalizedTraitSet[capitalize(key)] = value #这里已知其数值是正整数，因此不需要担心引用传递问题（We already know the values are integers, so there's no need to worry about the pass-by-reference problem）
                        else:
                            normalizedTraitSet[key] = value #既然不做改变，引用传递也无所谓（Since no change is made, pass-by-reference is all right）
                    mConditionalTraitSets.append(normalizedTraitSet)
                binData["mConditionalTraitSets"] = mConditionalTraitSets
            if "effectAmounts" in binData: #专用于云顶之弈传送门（Specially used for TFT portals）
                effectAmounts: dict[str, dict[str, str | float| int]] = {}
                for effectAmount in binData["effectAmounts"]:
                    effectAmounts[effectAmount["name"]] = effectAmount
                binData["effectAmounts"] = effectAmounts
        return binData
    
    @classmethod
    def tooltipStringtableIteration(cls, tooltip: str, strtable_locale: dict[str, int | dict[str, str]], deep: bool = False, reserve_CSS: bool = False, reserve_variable: bool = False, binData: None | dict[str, Any] = None, isCHS: bool = False, enableModeOverride: bool = False, reservedVarsList: Optional[dict[str, list[str]]] = None, flexibleData: Optional[dict[str, dict[str, Any] | Any]] = None) -> str: #将详细信息中花括号包围起来的部分替换成实际的字符串（Replace the part enclosed with two pairs of curly brackets into the actual string it represents）
        '''
        迭代地将说明文本中用双花括号包围起来的字符串键替换为实际的字符串。<br>Iteratively replace the string keys enclosed in double curly brackets in the tooltip with actual strings.
        
        :param tooltip: 待处理的说明文本。<br>The tooltip to process.
        :type tooltip: str
        :param strtable_locale: 字符串常量池。<br>Stringtable.
        :type strtable_locale: dict[str, int | dict[str, str]]
        :param deep: 是否进行深度替换。默认为假。指定为真时，执行变量代换。<br>Whether to perform further replacement. False by default. If set as True, perform the variable substitution.
        :type deep: bool
        :param reserve_CSS: 是否保留说明文本中的CSS样式标签。默认为假。<br>Whether to reserve CSS style tags in the tooltip. False by default.
        :type reserve_CSS: bool
        :param reserve_variable: 是否将变量代换后的结果写成“[{变量名}] = {值}”的形式。默认为假。<br>Whether to write the result after variable substitution in the form of "[{Var_name}] = {Value}". False by default.
        :type reserve_variable: bool
        :param binData: 用于变量代换的标准化二进制描述数据。仅在执行深度替换时需要该参数。<br>Normalized binary description data used for variable substitution. Only used when deep substitution is to perform.
        :type binData: dict[str, Any] | None
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :param enableModeOverride: 是否启用模式覆盖。启用后，将统计某个变量在不同模式中的数值。默认为假。<br>Whether to enable mode overriden values. If enabled, values among different modes will be taken into consideration. False by default.
        :type enableModeOverride: bool
        :param reservedVarsList: 保留变量列表。键为变量名，值为该变量在不同游戏模式下的取值列表，列表的每个元素往往后缀“(mode: ...)”。<br>Reserved variable list., where keys are variable names, and values are the value lists of the variable in different game modes. Each element in the list often ends with "(mode: ...)".
        :type reservedVarsList: dict[str, list[str]]
        :param flexibleData: 附加数据。<br>Supplemental data.
        :type flexibleData: dict[str, dict[str, Any] | Any] | None
        :return: 嵌套说明文本键在替换后的说明文本。<br>The tooltip after replacement of nested tooltip keys.
        :rtype: str
        '''
        pCite: re.Pattern[str] = re.compile(r"{{[/\sA-Za-z0-9=#\'_@]*}}")
        start_index = 0 #如果没有在字符串常量池中找到花括号包起来的部分对应的条目，则跳过这个部分（If the entry corresponding to the citation enclosed in a pair of curly brackets isn't found in the stringtable, skip this citation）
        if binData != None:
            binData = copy.deepcopy(binData)
        index: int = 0
        while (matchObj := pCite.search(tooltip, pos = start_index)):
            if isinstance(reservedVarsList, dict) and all(map(lambda x: isinstance(x, list), reservedVarsList.values())):
                reservedVars = {key: reservedVarsList[key][index if index < len(reservedVarsList[key]) else -1] for key in reservedVarsList} #key通常为GameModeInteger；这里假设pCite每次识别到引用时对应的是不同模式；如果出现下标越界的情况，返回最后一个追加的值（Usually, `key` is `GameModeInteger`. Here we assume every time `pCite` identifies something, it's always a unique game mode. If the index is out of range, return the last appended value of the reserved value list）
            else:
                reservedVars = None
            end_index = matchObj.end()
            citation = matchObj.group()
            entry_key = citation.lstrip("{").rstrip("}").strip(" ")
            if (entry_key.lower() in strtable_locale["entries"] or cls.compute_rsthash(entry_key, strtable_locale["version"]) in strtable_locale["entries"]):
                tooltip = tooltip.replace(citation, cls.get_strtable_value(strtable_locale, entry_key))
                if deep:
                    tooltip = cls.variableSubstitute(tooltip, binData, isCHS = isCHS, enableModeOverride = False, reserve_variable = reserve_variable, reservedVars = reservedVars, flexibleData = flexibleData)
            else:
                start_index = end_index + 1 #这一行语句只放在找不到对应条目的情况下执行，这样，在引用一个条目时，可以递归确认该引用的条目是否还有引用（This line only executes when the corresponding entry isn't found. In this way, when citing an entry, it can recursively confirm whether the cited entry has further citations）
            index += 1
        if deep: #在没有将任何双花括号包围的变量替换为实际说明文本时，仍然需要将说明文本中的双@包围的变量替换为实际说明文本（While there's no variable enclosed in two pairs of curly brackets and to be replaced with the actual tooltip, the variables enclosed in double @s still need to be replaced）
            if not reserve_CSS:
                tooltip = cls.tooltipPreparation(tooltip, isCHS = isCHS)
            tooltip = cls.variableSubstitute(tooltip, binData, isCHS = isCHS, enableModeOverride = enableModeOverride, reserve_variable = reserve_variable, reservedVars = None, flexibleData = flexibleData)
        return tooltip
    @classmethod
    def aRound(cls, num: float, digits: int = 0) -> int | float: #高级保留小数函数（Advanced version of `round` function）
        '''
        在保留小数时，自动忽略百万分位后的部分。<br>Automatically ignore the part after the millionth place when rounding a number.
        
        :param num: 待处理的数字。<br>The number to process.
        :type num: float
        :param digits: 保留的小数位数。默认为0。<br>The number of decimal places to keep. 0 by default.
        :type digits: int
        :return: 处理后的数字。如果保留小数后与整数相差不到一百万分之一，则直接返回整数。<br>The processed number. If the rounded number differs from its integer form by less than one millionth, return the integer instead.
        :rtype: int | float
        '''
        tmp: float | int = round(num, digits)
        result = int(tmp) if abs(tmp - int(tmp)) < 1e-6 else tmp
        return result

    @classmethod
    def isContDivision(cls, expr: str) -> bool: #判断一个表达式是不是连除式（Judge whether an expression is a continuous division）
        '''
        判断一个表达式是不是形如a/b/c/...的表达式。<br>Judge whether an expression is in the form of a/b/c/...
        
        :param expr: 表达式字符串。<br>The expression string.
        :type expr: str
        :return: 表达式是否为连除式。<br>Whether the expression is a continuous division.
        :rtype: bool
        '''
        pFigure: re.Pattern[str] = re.compile(r"-?\d+\.?\d*")
        while (matchObj := pFigure.search(expr)):
            expr = expr[:matchObj.start()] + expr[matchObj.end():]
        return len(set(list(expr))) == 1 and "/" in expr

    @classmethod
    def burnValueList(cls, values: list[float], digits: int = 5) -> str:
        '''
        将一个数值列表转化为连除式。<br>Transform a number list into a continuous division.
        
        :param values: 数值列表。<br>The list of numbers.
        :type values: list[float]
        :param digits: 保留的小数位数。默认为5。<br>The number of decimal places to keep. 5 by default.
        :type digits: int
        :return: 连除式字符串。<br>The continuous division string.
        :rtype: str
        '''
        return str(cls.aRound(values[0], digits = digits)) if len(set(values)) == 1 else "/".join(list(map(lambda x: str(cls.aRound(x, digits = digits)), values)))

    @classmethod
    def leafletCalculation(cls, binData: dict[str, Any], formulaPart: dict[str, Any], var_prefix: str, isCHS: bool = False, enableModeOverride: bool = False, rowIndex: int = -1, reservedVars: Optional[dict[str, str]] = None, flexibleData: Optional[dict[str, dict[str, Any] | Any]] = None) -> str:
        '''
        数值转换的末端计算。<br>Terminal calculation of variable transformation.
        
        :param binData: 用于变量代换的标准化二进制描述数据。只用于递归时传递参数。<br>Normalized binary description data used for variable substitution. Only used to pass the value during recursion.
        :type binData: dict[str, Any] | None
        :param formulaPart: 用于计算变量值的公式数据。<br>Formula data used to calculate the variable value.
        :type formulaPart: dict[str, Any]
        :param var_prefix: 变量名前缀。只用于递归时传递参数。<br>Variable name prefix. Only used to pass the value during recursion.
        :type var_prefix: str
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :param rowIndex: 见variableCalculation函数。<br>See `variableCalculation` function.
        :type rowIndex: int
        :param enableModeOverride: 是否启用模式覆盖。启用后，将统计某个变量在不同模式中的数值。默认为假。<br>Whether to enable mode overriden values. If enabled, values among different modes will be taken into consideration. False by default.
        :type enableModeOverride: bool
        :param reservedVars: 处理暂存的变量值，对于一些在嵌套时仍然保持变量形式的说明文本尤其有用，例如奥恩被动的说明文本。<br>Handles reserved variable values, especially useful for some tooltips that still keep the variable form during nesting, e.g. OrnnP.
        :type reservedVars: dict[str, str] | None
        :param flexibleData: 附加数据。<br>Supplemental data.
        :type flexibleData: dict[str, dict[str, Any] | Any] | None
        :return: 某个变量的值字符串。<br>The value string of a variable.
        :rtype: str
        '''
        mStatFormula_dict_zh: dict[int, str] = {0: "", 1: "基础", 2: "额外"} #0代表总（0 stands for total）
        mStatFormula_dict_en: dict[int, str] = {0: "", 1: "basic ", 2: "bonus "}
        mStat_dict_zh: dict[int, str] = {0: "法术强度", 1: "护甲", 2: "攻击力", 4: "攻击速度", 6: "魔法抗性", 7: "移动速度", 8: "暴击几率", 9: "暴击伤害", 10: "冷却缩减", 11: "技能急速", 12: "生命值", 14: "当前生命值百分比", 18: "生命偷取", 22: "固定法术穿透", 29: "穿甲", 31: "体型", 34: "治疗和护盾强度"}
        mStat_dict_en: dict[int, str] = {0: "Ability Power", 1: "Armor", 2: "Attack Damage", 4: "Attack Speed", 6: "Magic Resistance", 7: "Movement Speed", 8: "Critical Strike Chance", 9: "Crit Damage", 10: "Cooldown Reduction", 11: "Ability Haste", 12: "Health", 14: "Current Health Percent", 18: "Life Steal", 22: "Magic Penetration Flat", 29: "Lethality", 31: "Size", 34: "Heal and Shield Power"}
        if isinstance(flexibleData, dict): #附加数据处理（Supplemental data processing）
            if "mStat_dict_override_version" in flexibleData and isinstance(flexibleData["mStat_dict_override_version"], str):
                if Patch(flexibleData["mStat_dict_override_version"]) <= Patch("14.15"):
                    mStat_dict_zh = {0: "法术强度", 1: "护甲", 2: "攻击力", 3: "攻击速度", 4: "攻击前摇", 5: "魔法抗性", 6: "移动速度", 7: "暴击几率", 8: "暴击伤害", 9: "冷却缩减", 10: "技能急速", 11: "生命值", 12: "当前生命值百分比", 13: "已损失生命值百分比", 15: "生命偷取", 19: "固定法术穿透", 26: "穿甲", 28: "体型", 29: "生命回复", 31: "治疗和护盾强度"}
                    mStat_dict_en = {0: "Ability Power", 1: "Armor", 2: "Attack Damage", 3: "Attack Speed", 4: "Attack Windup", 5: "Magic Resistance", 6: "Movement Speed", 7: "Critical Strike Chance", 8: "Crit Damage", 9: "Cooldown Reduction", 10: "Ability Haste", 11: "Health", 12: "Current Health Percent", 13: "Lost Health Percent", 15: "Life Steal", 19: "Magic Penetration Flat", 26: "Lethality", 28: "Size", 29: "Health Regen", 31: "Heal and Shield Power"}
        formulaPart_type: str = formulaPart["__type"]
        if formulaPart_type in {"ClampSubPartsCalculationPart", "ProductOfSubPartsCalculationPart", "StatBySubPartCalculationPart", "SumOfSubPartsCalculationPart"}:
            formulaStr: str = cls.subpartCalculation(binData, formulaPart, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            if formulaPart_type == "StatBySubPartCalculationPart": #仅用于装备中的卢安娜的飓风和闪电杖和强化符文中的小丑学院的背刺（Only applies to Runaan's Hurricane and Lightning Rod in items and backstab of Clown College in augments）
                stat_header: str = mStatFormula_dict_zh[formulaPart.get("mStatFormula", 0)] if isCHS else mStatFormula_dict_en[formulaPart.get("mStatFormula", 0)]
                stat_desc: str = mStat_dict_zh[formulaPart.get("mStat", 0)] if isCHS else mStat_dict_en[formulaPart.get("mStat", 0)]
                if mStat_dict_zh[formulaPart.get("mStat", 0)] == "生命值" and formulaPart.get("mStatFormula", 0) == 0:
                    stat_header = "最大" if isCHS else "max " #生命值的各类标头出现都较为频繁，需要特别声明（Each header of Health appears frequently, so the default case should be specifically noted）
                formulaStr += " × " + stat_header + stat_desc
            formulaStr = "{" + formulaStr + "}"
        elif formulaPart_type == "AbilityResourceByCoefficientCalculationPart": #法力值收益率（Mana ratio）
            mCoefficient: float = formulaPart["mCoefficient"]
            partCalc: Any = cls.aRound(mCoefficient, 5)
            formulaStr = str(partCalc) + (" × 最大法力值" if isCHS else " × max Mana")
        elif formulaPart_type == "BuffCounterByCoefficientCalculationPart": #在装备中，仅用于飞升护符、榨血睥睨和先机鞋（In items, this only applies to Talisman Ascension, Leeching Leer and the upgraded boots granted by Feats of Strength）
            mCoefficient: float = formulaPart["mCoefficient"]
            partCalc = cls.aRound(mCoefficient, 5)
            formulaStr = str(partCalc) + " × stack of " + formulaPart["mBuffName"]
        elif formulaPart_type == "BuffCounterByNamedDataValueCalculationPart": #仅用于游戏内动态数值的显示，如【终极轮盘】中的【盛宴】提供的攻击距离（Only applies to in-game dynamic stat display, e.g. attack range granted by [Feast] in [Ultimate Roulette]）
            partCalc = cls.variableCalculation(binData, formulaPart["mDataValue"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            formulaStr = partCalc + " × stack of " + formulaPart["mBuffName"]
        elif formulaPart_type == "ByCharLevelBreakpointsCalculationPart": #阶梯式等级提供增益（Bonus value provided by levels in a step function manner）
            mLevel1Value: int | float = formulaPart.get("mLevel1Value", 0)
            mBonusPerLevelAtAndAfter: int | float = formulaPart.get("mInitialBonusPerLevel", 0) #每级增加的数值（The value to increment reaching each level）
            if "mBreakpoints" in formulaPart:
                levelValues: list[int | float] = [] #从封魔剑魂 永恩的【凛神斩】的对小兵最小伤害中推断出，mBonusPerLevelAtAndAfter键适用于1级（From YoneW's MinimumDamageMinions, we can infer that `mBonusPerLevelAtAndAfter` applies at Level 1）
                formulaPart["mBreakpoints"] = sorted(formulaPart["mBreakpoints"], key = lambda x: x.get("mLevel", 1)) #这一步其实无关紧要，因为断点列表总是按照等级正序排列的（This step is actually unnecessary, for the breakpoints are always sorted in the ascending order of mLevel）
                mLevel_i_Value: int | float = mLevel1Value
                i: int = 1 #等级（Level）
                j: int = 0 #断点列表下标（Breakpoint list index）
                while i <= 18:
                    if i == formulaPart["mBreakpoints"][j].get("mLevel"):
                        if "mBonusPerLevelAtAndAfter" in formulaPart["mBreakpoints"][j]:
                            mBonusPerLevelAtAndAfter = formulaPart["mBreakpoints"][j]["mBonusPerLevelAtAndAfter"]
                        elif "mAdditionalBonusAtThisLevel" in formulaPart["mBreakpoints"][j]: #以斯塔缇克电刃的冷却时间计算最为典型（The most typical case is the calculation of cooldown of Statikk Shiv）
                            mLevel_i_Value += formulaPart["mBreakpoints"][j]["mAdditionalBonusAtThisLevel"]
                        else:
                            pass
                        if j < len(formulaPart["mBreakpoints"]) - 1:
                            j += 1
                    mLevel_i_Value += mBonusPerLevelAtAndAfter
                    levelValues.append(mLevel_i_Value)
                    i += 1
                levelValues = list(map(lambda x: cls.aRound(x, 5), levelValues))
                formulaStr = "/".join(list(map(str, levelValues))) + " (based on Level)"
            else:
                mLevel18Value = mLevel1Value + 17 * mBonusPerLevelAtAndAfter
                formulaStr = "%s - %s (based on Level)" %(cls.aRound(mLevel1Value, 5), cls.aRound(mLevel18Value, 5))
        elif formulaPart_type == "ByCharLevelFormulaCalculationPart": #公式等级提供增益（Bonus value provided by levels following a formula）
            formulaStr = cls.burnValueList(formulaPart["values"] if "values" in formulaPart else formulaPart["mValues"]) #在25.06版本以前，值列表的键名是mValues（Before Patch 25.06, the value list's key name is "mValues"）
        elif formulaPart_type == "ByCharLevelInterpolationCalculationPart": #线性等级提供增益（Bonus value provided by levels in a linear manner）
            mStartValue: int | float = cls.aRound(formulaPart.get("mStartValue", 0), 5)
            mEndValue: int | float = cls.aRound(formulaPart["mEndValue"], 5)
            formulaStr = f"{mStartValue} - {mEndValue} (based on Level)"
        elif formulaPart_type == "CooldownMultiplierCalculationPart": #典型示例：无极剑圣 易的【阿尔法突袭】（A typical example: AlphaStrike）
            formulaStr = "100 / (100 + 技能急速)" if isCHS else "100 / (100 + Ability Haste)"
        elif formulaPart_type == "EffectValueCalculationPart": #在装备中仅用于灰烬小刀、冰雹刀刃和黑曜石锋刃的灼烧伤害，在强化符文中仅用于【招架】和【终极轮盘】中的【加农炮幕】的弹体伤害（Only applies to the burn damage from Emberknifre, Hailblade and Obsidian Edge in items and the missiles from [Parry] and [Cannon Barrage] in [Ultimate Roulette] in augments）
            mEffectIndex: int = formulaPart["mEffectIndex"]
            formulaStr = cls.variableCalculation(binData, f"Effect{mEffectIndex}Amount", var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
        elif formulaPart_type == "NamedDataValueCalculationPart":
            formulaStr = cls.variableCalculation(binData, formulaPart["mDataValue"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
        elif formulaPart_type == "NumberCalculationPart":
            partCalc = cls.aRound(formulaPart.get("mNumber", 0), 5)
            formulaStr = str(partCalc)
        elif formulaPart_type == "StatByCoefficientCalculationPart":
            partCalc = cls.aRound(formulaPart["mCoefficient"], 5)
            stat_header: str = mStatFormula_dict_zh[formulaPart.get("mStatFormula", 0)] if isCHS else mStatFormula_dict_en[formulaPart.get("mStatFormula", 0)]
            stat_desc: str = mStat_dict_zh[formulaPart.get("mStat", 0)] if isCHS else mStat_dict_en[formulaPart.get("mStat", 0)]
            if mStat_dict_zh[formulaPart.get("mStat", 0)] == "生命值" and formulaPart.get("mStatFormula", 0) == 0:
                stat_header = "最大" if isCHS else "max "
            formulaStr = str(partCalc) + " × " + stat_header + stat_desc
        elif formulaPart_type == "StatByNamedDataValueCalculationPart":
            formulaStr = cls.variableCalculation(binData, formulaPart["mDataValue"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            stat_header: str = mStatFormula_dict_zh[formulaPart.get("mStatFormula", 0)] if isCHS else mStatFormula_dict_en[formulaPart.get("mStatFormula", 0)]
            stat_desc: str = mStat_dict_zh[formulaPart.get("mStat", 0)] if isCHS else mStat_dict_en[formulaPart.get("mStat", 0)]
            if mStat_dict_zh[formulaPart.get("mStat", 0)] == "生命值" and formulaPart.get("mStatFormula", 0) == 0:
                stat_header = "最大" if isCHS else "max "
            formulaStr += " × " + stat_header + stat_desc
        elif formulaPart_type == "{b22609db}": #仅用于刀锋舞者 艾瑞莉娅的【艾欧尼亚热诚】（Only applies to IreliaPassive）
            mLevel1ValueStr: str = cls.variableCalculation(binData, formulaPart["{91d404a5}"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            mValuePerLevelStr: str = cls.variableCalculation(binData, formulaPart["{b2cd0eb0}"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            formulaStr = f"{mLevel1ValueStr} + {mValuePerLevelStr} × Level"
        elif formulaPart_type == "{ee18a47b}": #仅用于兽灵行者 乌迪尔的【狂暴爪击】（Only applies to UdyrQ）
            mLevel1ValueStr = cls.variableCalculation(binData, formulaPart["{0589a59c}"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            mLevel18ValueStr: str = cls.variableCalculation(binData, formulaPart["{0b65bc23}"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            formulaStr = f"{mLevel1ValueStr} - {mLevel18ValueStr} (based on Level)"
        elif formulaPart_type == "{f3cbe7b2}": #mSpellCalculationKey来自mItemCalculations键的情形。在装备中仅用于夺萃之镰和无终恨意（The case where the value of `mSpellCalculationKey` is a key of the value of `mItemCalculations`. In items, this only applies to Essence Reaver and Unending Despair）
            formulaStr = cls.variableCalculation(binData, formulaPart["mSpellCalculationKey"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
        else: #异常处理（Exception handling）
            formulaStr = "φ"
        return formulaStr

    @classmethod
    def subpartCalculation(cls, binData: dict[str, Any], subpart_formula: dict[str, Any], var_prefix: str, isCHS: bool = False, enableModeOverride: bool = False, rowIndex: int = -1, reservedVars: Optional[dict[str, str]] = None, flexibleData: Optional[dict[str, dict[str, Any] | Any]] = None) -> str:
        '''
        副部计算。通常作为中间处理过程而调用末端计算方法。<br>Subpart calculation. Usually serve as an intermediate process to call `leafletCalculation` method.
        
        :param binData: 用于变量代换的标准化二进制描述数据。只用于递归时传递参数。<br>Normalized binary description data used for variable substitution. Only used to pass the value during recursion.
        :type binData: dict[str, Any] | None
        :param subpart_formula: 用于计算变量值的副部公式数据。<br>Subpart formula data used to calculate the variable value.
        :type subpart_formula: dict[str, Any]
        :param var_prefix: 变量名前缀。只用于递归时传递参数。<br>Variable name prefix. Only used to pass the value during recursion.
        :type var_prefix: str
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :param enableModeOverride: 是否启用模式覆盖。启用后，将统计某个变量在不同模式中的数值。默认为假。<br>Whether to enable mode overriden values. If enabled, values among different modes will be taken into consideration. False by default.
        :type enableModeOverride: bool
        :param rowIndex: 见variableCalculation函数。<br>See `variableCalculation` function.
        :type rowIndex: int
        :param reservedVars: 处理暂存的变量值，对于一些在嵌套时仍然保持变量形式的说明文本尤其有用，例如奥恩被动的说明文本。<br>Handles reserved variable values, especially useful for some tooltips that still keep the variable form during nesting, e.g. OrnnP.
        :type reservedVars: dict[str, str] | None
        :param flexibleData: 附加数据。<br>Supplemental data.
        :type flexibleData: dict[str, dict[str, Any] | Any] | None
        :return: 某个涉及副部计算的变量的中间处理结果。<br>The temporary result of a variable involving subpart calculation.
        :rtype: str
        '''
        #首先得出副部列表（First, get the list of subparts）
        subpart_formula_type: str = subpart_formula["__type"]
        if subpart_formula_type in {"ClampSubPartsCalculationPart", "SumOfSubPartsCalculationPart"}:
            subparts: list[dict[str, Any]] = subpart_formula["mSubparts"]
        elif subpart_formula_type == "StatBySubPartCalculationPart":
            subparts = [subpart_formula["mSubpart"]] #在仅有一个元素时，下面的运算符将不会被添加（When there's only one element in `subpart_formula_strs`, the following operator won't be added）
        elif subpart_formula_type == "ProductOfSubPartsCalculationPart":
            subparts = []
            for (key, value) in subpart_formula.items():
                if key != "__type":
                    subparts.append(value)
        else: #异常情况（Exceptional case）
            subparts = []
        #接着对每个副部计算其结果字符串（Next, calculate the result string from each subpart）
        subpart_formula_strs: list[str] = []
        for subpart in subparts:
            if subpart["__type"] in {"ClampSubPartsCalculationPart", "SumOfSubPartsCalculationPart", "ProductOfSubPartsCalculationPart"}:
                subpart_formula_str: str = cls.subpartCalculation(binData, subpart, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                if subpart_formula["__type"] == "ClampSubPartsCalculationPart": #在装备中仅用于斯特拉克的挑战护手（In items, this only applies to Sterak's Gage）
                    mCeiling = cls.aRound(cls.dGet(subpart_formula, "mCeiling", 0, 0), 2)
                    mFloor = cls.aRound(cls.dGet(subpart_formula, "mFloor", 0, 0), 2) #在14.13版本的奎桑提弈子的技能二进制描述中，某个“mFloor”键的值是None（In TFT10_KSante's spell data, the value of some "mFloor" is None）
                    subpart_formula_str += f" ({mFloor} - {mCeiling})"
            else:
                subpart_formula_str = cls.leafletCalculation(binData, subpart, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            subpart_formula_strs.append(subpart_formula_str)
        #最后连接每个结果字符串（Finally, concatenate all result strings）
        if subpart_formula["__type"] in {"ClampSubPartsCalculationPart", "SumOfSubPartsCalculationPart"}:
            operator: str = "+"
        elif subpart_formula["__type"] == "ProductOfSubPartsCalculationPart":
            operator = "×"
        else:
            operator = "+"
        result: str = "(" + f" {operator} ".join(subpart_formula_strs) + ")"
        return result

    @classmethod
    def variableModeOverrideCalculation(cls, binData: dict[str, Any], var: str) -> dict[str, str]: #处理在DataValuesModeOverride有记录的变量。不支持云顶之弈（Handle variables which exist in `DataValuesModeOverride` key's value. Doesn't support TFT）
        '''
        处理模式覆盖数值计算。<br>Handle mode override value calculation.
        
        :param binData: 转换后的二进制描述数据。<br>Binary description data transformed by `normalizeBinData` function.
        :type binData: dict[str, Any]
        :param var: 双@包围的变量。<br>A variable enclosed within double @.
        :type var: str
        :param isCHS: 是否应用简体中文标点符号。默认为否。<br>Whether to use quotation marks in Chinese Simplified, `False` by default.
        :type isCHS: bool
        :return: 键为游戏模式名称，值为计算结果字符串。<br>Keys are gameModeNames and values are calculation result strings.
        :rtype: dict[str, str]
        '''
        var_hash: str = cls.compute_binhash(var)
        result: dict[str, str] = {}
        if "DataValuesModeOverride" in binData and (var.lower() in binData["DataValuesModeOverride"] or var_hash in binData["DataValuesModeOverride"]):
            if var.lower() in binData["DataValuesModeOverride"]:
                var_modeValues = binData["DataValuesModeOverride"][var.lower()]
            else:
                var_modeValues = binData["DataValuesModeOverride"][var_hash]
            for (gameModeName, dataValue) in var_modeValues.items():
                if dataValue["__type"] == "SpellDataValue":
                    result[gameModeName] = cls.burnValueList(cls.aGet(dataValue, ["values", "mValues"], [0])) #在无限火力中，战争之影 赫卡里姆的【暴走】的冷却缩减被降为0，从而导致其模式覆盖数值中没有mValues键（In URF, Hecarim's Rampage's cooldown reduction is reduced to 0, and consequently its modeOverrideDataValue doesn't have `values` key）
                elif dataValue["__type"] == "ItemDataValue":
                    result[gameModeName] = str(cls.aRound(dataValue["mValue"], 5))
                else:
                    result[gameModeName] = f"@_{var}_@" #为了防止模式重载变量后续被视为默认模式变量重新参与迭代，这里进行异化处理（To avoid the mode override variable from being regarded as the default mode's variable and thus take part in the subsequent iterations, here we make a little difference）
        elif "mEffectAmountGameMode" in binData and (var.lower() in binData["mEffectAmountGameMode"] or var_hash in binData["mEffectAmountGameMode"]):
            if var.lower() in binData["mEffectAmountGameMode"]:
                var_modeValues = binData["mEffectAmountGameMode"][var.lower()]
            else:
                var_modeValues = binData["mEffectAmountGameMode"][var_hash]
            for (gameModeName, value) in var_modeValues.items():
                result[gameModeName] = str(cls.aRound(value, 5))
        return result

    @classmethod
    def variableCalculation(cls, binData: dict[str, Any], var: str, var_prefix: str, isCHS: bool = False, enableModeOverride: bool = False, rowIndex: int = -1, reservedVars: Optional[dict[str, str]] = None, flexibleData: Optional[dict[str, dict[str, Any] | Any]] = None) -> str:
        r'''
        计算一个变量的值字符串。<br>Calculate the value string of a variable.
        
        :param cls: 不作为显式参数，意味着可通过LoLDataExtractor调用。<br>Doesn't act as an explicit parameter. Means this function can be called via `LoLDataExtractor`.
        :param binData: 包含数值计算的二进制描述数据，包括但不限于装备数据对象和指令对象。<br>The binary description data that contain data value calculation, including but not limited to ItemDataObject and SpellObject.
        :type binData: dict[str, Any]
        :param var: 双@包围的变量或进一步解析后得到的变量。<br>A variable enclosed within double @ or obtained by further resolve.
        :type var: str
        :param var_prefix: 变量的前缀，通常处理涉及不在binData内的变量的计算。主要用于从calculatedVariables中引用一个变量。这类变量的格式通常如下：@{category}.{mScriptName}:{var}@，此时var_prefix应为{category}.{mScriptName}。在字符串常量池中，以`@\w+(\.\w*)*:`正则表达式来对这类变量进行搜索。<br>The prefix of the variable, which usually involves calculation of indirect variables not in `binData`. Usually used to cite a variable from `calculatedVariables`. The format of this kind of variables is usually @Spell.{mScriptName}:{var}@, when `var_prefix` should be `Spell.{mScriptName}`. Search for this kind of variables in stringtable using this regular expression: `@\w+(\.\w*)*:`.
        :type var_prefix: str
        :param isCHS: 是否应用简体中文标点符号。默认为否。<br>Whether to use quotation marks in Chinese Simplified, `False` by default.
        :type isCHS: bool
        :param enableModeOverride: 启用模式覆盖数值计算。为真时会从数据中纳入DataValuesModeOverride键的变量。<br>Enable mode override calculation. If it's `True`, variables in `DataValuesModeOverride` will be considered.
        :type enableModeOverride: bool
        :param rowIndex: 标记变量的重复出现次数。专用于云顶之弈羁绊的变量计算，因为其说明文本中会多次引用相同变量字面量，且对应二进制描述数据中的mConditionalTraitSets键的值列表中有多个字典，其中也包含相同的变量。<br>Marks the number of times a variable has appeared. Specially used for variable substitution of TFT trait, because a TFT trait tooltip is likely to cite a same variable literal for multiple times, and in the corresponding binary description data, the value list of `mConditionalTraitSets` key contains multiple dictionaries which contain the same variables.
        :type rowIndex: int
        :param reservedVars: 处理暂存的变量值，对于一些在嵌套时仍然保持变量形式的说明文本尤其有用，例如奥恩被动的说明文本。<br>Handles reserved variable values, especially useful for some tooltips that still keep the variable form during nesting, e.g. OrnnP.
        :type reservedVars: dict[str, str] | None
        :param flexibleData: 附加数据，用于传递可选参数。键是数据的描述，值一般情况下是通过session.request.json方法直接获得的数据对象，也可以自定义。<br>Supplemental data, designed to pass optional parameters. Each key is the data description. Each value is usually an object returned by `session.request.json` method, but users may specify it according to their demands.<br>键值示例（Key-value pair examples）：
            <pre>
            **Level-1 Key**         **Level-1 Value Description**<br>
            lolstringtable      任意语言的英雄联盟字符串常量池（LoL stringtable in any language）<br>
            tftstringtable      任意语言的云顶之弈字符串常量池（TFT stringtable in any language）<br>
            stringtable         任意语言的合并后的字符串常量池（Merged stringtable in any language）<br>
            map22_bin           聚点危机地图的二进制描述（Convergence map's binary description）<br>
            characters_bin      所有角色的二进制描述（All characters' binary description）
            </pre>
            该参数的设计理念类似于**kwargs。<br>This parameter's design concept resembles `**kwargs`.<br><b>警告：</b>由于函数体不会对其中的格式进行严格检查，因此在使用此参数时需要小心。这是编程便捷性与运算严格性之间的取舍问题。<br><b>Warning:</b> Because the body of this function won't perform serious verification on its format, users should be aware of their using this parameter. This is a tradeoff between programming convenience and calculation seriousness.
        :type flexibleData: dict[str, dict[str, Any] | Any] | None
        :return: 变量的计算结果字符串。<br>Calculation result string.
        :rtype: str
        '''
        #在指定变量的保留值时，直接返回该值（Directly return the reserved value when it's specified for the variable）
        if isinstance(reservedVars, dict) and var in reservedVars:
            return reservedVars[var]
        #首先处理默认数值（First, resolve the default value）
        var_hash: str = cls.compute_binhash(var) #准备变量名的8位hash值（Prepare the 8-digit hash value of `var`）
        pOtherBinDataHeader: re.Pattern[str] = re.compile(r"\w*(\.\w*)*:")
        pVarFloat: re.Pattern[str] = re.compile(r"\w*\.-?\d") #变量后带点和数字的表示固定小数位数，这里由于统一通过aRound来进行控制，因此直接忽略（Variables suffixed with a dot and a number means the numebr of digits. Since it's controlled by `aRound` in this program, here we ignore it）
        skip: bool = False #如果出现无法处理的情形，则跳过值处理部分，直接返回空集字符（If the function can't handle some case, it'll skip the value processing part and return an null set character instead）
        normalValue: str = f"@{var}@" #值初始化（Value initialization）
        if var.startswith("Effect") and var.endswith("Amount"):
            mEffectAmount_index = int(var.lstrip("Effect").rstrip("Amount")) - 1
            if "mEffectAmount" in binData:
                mEffectAmount: list[int | float | dict[str, Any]] = binData["mEffectAmount"]
                if mEffectAmount_index < len(mEffectAmount):
                    if all(map(lambda x: isinstance(x, (int, float)), mEffectAmount)):
                        normalValue = str(cls.aRound(mEffectAmount[mEffectAmount_index], 5))
                    elif all(map(lambda x: isinstance(x, dict), mEffectAmount)):
                        normalValue = cls.burnValueList(mEffectAmount[mEffectAmount_index]["value"])
                    else:
                        skip = True
                else:
                    skip = True
            else:
                skip = True
        elif (var in binData or var_hash in binData):
            value: int | float | list[int | float] = binData[var] if var in binData else binData[var_hash]
            if isinstance(value, (int, float)):
                normalValue = str(cls.aRound(value, 5))
            elif isinstance(value, list):
                normalValue = cls.burnValueList(value)
            else:
                skip = True
        elif decapitalize(var) in binData: #var_hash部分在此处无需重复（`var_hash` part doesn't need to repeated once again here）
            value: int | float | list[int | float] = binData[decapitalize(var)]
            if isinstance(value, (int, float)):
                normalValue = str(cls.aRound(value, 5))
            elif isinstance(value, list):
                normalValue = cls.burnValueList(value)
            else:
                skip = True
        elif f"m{var}" in binData:
            value: int | float | list[int | float] = binData[f"m{var}"]
            if isinstance(value, (int, float)):
                normalValue = str(cls.aRound(value, 5))
            elif isinstance(value, list):
                normalValue = cls.burnValueList(value)
            else:
                skip = True
        elif "DataValues" in binData and (var.lower() in binData["DataValues"] or var_hash in binData["DataValues"]):
            if var.lower() in binData["DataValues"]:
                values: list[int | float] = list(map(lambda x: cls.aRound(x, 5), cls.aGet(binData["DataValues"][var.lower()], ["values", "mValues"], [0])))
            else:
                values: list[int | float] = list(map(lambda x: cls.aRound(x, 5), cls.aGet(binData["DataValues"][var_hash], ["values", "mValues"], [0])))
            normalValue = cls.burnValueList(values)
        elif "mDataValues" in binData and (var.lower() in binData["mDataValues"] or var_hash in binData["mDataValues"]):
            if var.lower() in binData["mDataValues"]:
                if "mValue" in binData["mDataValues"][var.lower()]:
                    value: int | float = binData["mDataValues"][var.lower()]["mValue"]
                    normalValue = str(cls.aRound(value, 5))
                elif "mValues" in binData["mDataValues"][var.lower()]: #英雄数据在14.15版本是mDataValues键（In champion data, it's `mDataValues` key in v14.15）
                    values = list(map(lambda x: cls.aRound(x, 5), binData["mDataValues"][var.lower()]["mValues"]))
                    normalValue = cls.burnValueList(values)
                else:
                    skip = True
            else:
                if "mValue" in binData["mDataValues"][var_hash]:
                    value: int | float = binData["mDataValues"][var_hash]["mValue"]
                elif "mValues" in binData["mDataValues"][var_hash]:
                    values = list(map(lambda x: cls.aRound(x, 5), binData["mDataValues"][var_hash]["mValues"]))
                    normalValue = cls.burnValueList(values)
                else:
                    skip = True
        elif "mEffectAmount" in binData and (var.lower() in binData["mEffectAmount"] or var_hash in binData["mEffectAmount"]): #专用于符文（Specially used in perks）
            if var.lower() in binData["mEffectAmount"]:
                value: int | float = binData["mEffectAmount"][var.lower()]
            else:
                value: int | float = binData["mEffectAmount"][var_hash]
            normalValue = str(cls.aRound(value, 5))
        elif "effectAmounts" in binData and (var in binData["effectAmounts"] or var_hash in binData["effectAmounts"]): #专用于云顶之弈（Specially used in TFT）
            if var in binData["effectAmounts"] and "value" in binData["effectAmounts"][var]:
                value: int | float = binData["effectAmounts"][var]["value"]
                normalValue = str(cls.aRound(value, 5))
            elif var_hash in binData["effectAmounts"] and "value" in binData["effectAmounts"][var_hash]:
                value: int | float = binData["effectAmounts"][var_hash]["value"]
                normalValue = str(cls.aRound(value, 5))
            else:
                skip = True
        elif "mSpellCalculations" in binData and (var.lower() in binData["mSpellCalculations"] or var_hash in binData["mSpellCalculations"]) or "mItemCalculations" in binData and (var.lower() in binData["mItemCalculations"] or var_hash in binData["mItemCalculations"]) or "mCalculations" in binData and (var in binData["mCalculations"] or var_hash in binData["mCalculations"]):
            if "mSpellCalculations" in binData and (var.lower() in binData["mSpellCalculations"] or var_hash in binData["mSpellCalculations"]):
                if var.lower() in binData["mSpellCalculations"]:
                    stats: dict[str, Any] = binData["mSpellCalculations"][var.lower()]
                else:
                    stats = binData["mSpellCalculations"][var_hash]
            elif "mItemCalculations" in binData and (var.lower() in binData["mItemCalculations"] or var_hash in binData["mItemCalculations"]): #专用于英雄联盟装备数值计算（Specially used in LoL item data calculation）
                if var.lower() in binData["mItemCalculations"]:
                    stats = binData["mItemCalculations"][var.lower()]
                else:
                    stats = binData["mItemCalculations"][var_hash]
            else: #专用于符文数值计算（Specially used in perk data calculation）
                if var in binData["mCalculations"]:
                    stats = binData["mCalculations"][var]
                else:
                    stats = binData["mCalculations"][var_hash]
            if stats["__type"] == "GameCalculation":
                formulaStrs: list[str] = []
                for formulaPart in stats["mFormulaParts"]:
                    formulaStr = cls.leafletCalculation(binData, formulaPart, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                    formulaStrs.append(formulaStr)
                normalValue = " + ".join(formulaStrs)
                try:
                    normalValue = str(cls.aRound(eval(normalValue), 5))
                except:
                    pass
                if "mMultiplier" in stats:
                    multiple: str = cls.leafletCalculation(binData, stats["mMultiplier"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                    normalValue = f"({normalValue}) × ({multiple})"
            elif stats["__type"] == "GameCalculationConditional": #涉及复杂的远程/近战英雄数值加成计算。仅用于详细信息中双花括号包围的@ChampRange@（Involves complex calculation of bonus stats for melee / ranged champions. Only applies to "@ChampRange@" enclosed within two pairs of curly brackets）
                defaultValue = cls.variableCalculation(binData, stats["mDefaultGameCalculation"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                conditionalValue = cls.variableCalculation(binData, stats["mConditionalGameCalculation"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                requirementType = stats["mConditionalCalculationRequirements"]["__type"]
                if requirementType == "IsRangedCastRequirement":
                    normalValue = "%d (melee) | %d (ranged)" %(float(defaultValue), float(conditionalValue)) #其返回值将在转换详细信息之后，参与到花括号中的变量替换（This value will participant in the replacement of variables enclosed with two pairs of curly brackets）
                elif requirementType == "HasBuffCastRequirement":
                    mBuffName = stats["mConditionalCalculationRequirements"]["mBuffName"]
                    normalValue = f"{defaultValue} (without {mBuffName}) | {conditionalValue} (with {mBuffName})"
                else:
                    normalValue = f"{defaultValue} | {conditionalValue}"
            elif stats["__type"] == "GameCalculationModified":
                baseKey: str = stats["mModifiedGameCalculation"]
                calculatedKey: str = baseKey if var_prefix == "" else f"{var_prefix}:{baseKey}"
                if calculatedKey in cls.calculatedVariables:
                    baseValue_type = cls.calculatedVariables[calculatedKey]["__type"]
                    if baseValue_type == "SingleValue":
                        baseValue: str = cls.calculatedVariables[calculatedKey]["value"]
                    elif baseValue_type == "ModeOverrideValue":
                        modeOverrideValues_tmp: dict[str, str] = cls.calculatedVariables[calculatedKey]["value"]
                        modeOverrideValueDict_raw_tmp: dict[str, str] = {}
                        for (gameModeName, modeOverrideValue) in modeOverrideValues_tmp.items():
                            modeOverrideValueDict_raw_tmp[gameModeName] = modeOverrideValue if gameModeName == "default" else f"{modeOverrideValue} (mode: {gameModeName})"
                        baseValue = " || ".join(list(modeOverrideValueDict_raw_tmp.values()))
                    else:
                        baseValue = cls.calculatedVariables[calculatedKey]["value"]
                else:
                    baseValue = cls.variableCalculation(binData, baseKey, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                multiple = cls.leafletCalculation(binData, stats["mMultiplier"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                normalValue = f"({baseValue}) × ({multiple})"
            elif stats["__type"] == "{e9a3c91d}": #远程/近战英雄不同属性收益（Different bonus on melee / ranged champions）
                formulaStrs: list[str] = []
                for formulaPart in stats["mFormulaParts"]:
                    formulaStr = cls.leafletCalculation(binData, formulaPart, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                    formulaStrs.append(formulaStr)
                meleeValue: str = " + ".join(formulaStrs)
                try:
                    meleeValue: int | float = eval(meleeValue.replace("×", "*"))
                except:
                    pass
                else:
                    meleeValue = cls.aRound(meleeValue, 5)
                rangedMultiple = cls.leafletCalculation(binData, stats["mRangedMultiplier"], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                rangedValue: str = f"({meleeValue}) × ({rangedMultiple})"
                try:
                    rangedValue: int | float = eval(rangedValue.replace("×", "*"))
                except:
                    pass
                else:
                    rangedValue = cls.aRound(rangedValue, 5)
                normalValue = f"{meleeValue} (melee) | {rangedValue} (ranged)"
            else:
                skip = True
        elif "StringCalculations" in binData and (var in binData["StringCalculations"] or var_hash in binData["StringCalculations"]):
            if var in binData["StringCalculations"]:
                stats: dict[str, Any] = binData["StringCalculations"][var]
            else:
                stats = binData["StringCalculations"][var_hash]
            if stats["__type"] == "{4750ceb6}":
                meleeResult = cls.variableCalculation(binData, stats["MeleeResult"].strip("@"), var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                rangedResult = cls.variableCalculation(binData, stats["RangedResult"].strip("@"), var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                normalValue = f"{meleeResult} (melee) | {rangedResult} (ranged)"
            else: #异常处理（Exception handling）
                skip = True
        elif (matchObj := pVarFloat.fullmatch(var)):
            normalValue = cls.variableCalculation(binData, var.split(".")[0], var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
        elif "__type" in binData and binData["__type"] == "TftUnitPropertyDefinition" and (binData["name"] == var or binData["name"] == var_hash): #以下部分为云顶之弈部分的数值转换（The following parts are data value substitution of TFT）
            #实际上，var参数是上一层函数在调用variableCalculation函数时就已经检验过了，因为单位属性对象是和变量一一对应的（Actually, the `var` parameter has been verified in the parent layer of `variableCalculation` function, because each variableCalculation object obeys one-to-one correspondence with `var`）
            DefaultValue = binData["DefaultValue"]
            if DefaultValue["__type"] == "TftUnitPropertyValueBool":
                normalValue = str(DefaultValue.get("value", False))
            elif DefaultValue["__type"] == "TftUnitPropertyValueFloat": #额外含有{82e959c3}键，其作用尚未弄清楚（It additionally has "{82e959c3}" key, whose meaning hasn't been figured out）
                if "value" in DefaultValue:
                    normalValue = str(cls.aRound(DefaultValue["value"], 5))
                else:
                    skip = True
            elif DefaultValue["__type"] == "TftUnitPropertyValueInteger":
                if "value" in DefaultValue:
                    normalValue = str(DefaultValue["value"])
                else:
                    skip = True
            elif DefaultValue["__type"] == "TftUnitPropertyValueIntegerSet":
                skip = True
            elif DefaultValue["__type"] == "TftUnitPropertyValueString":
                if "value" in DefaultValue:
                    normalValue = "{" + DefaultValue["value"] + "}" #在variableSubstitute函数中，该值外会再添加一层括号，从而形成一个对其它字符串常量的引用，从而在tooltipStringtableIteration（while循环之外）函数中被转换成实际文本（In `variableSubstitute` function, this value will be enclosed with another pair of curly brackets, so that a citation of another string constant is formed and thus this citation will be transformed into the actual string by `tooltipStringtableIteration` function outside that while-loop）
                else:
                    skip = True
            else:
                skip = True
        elif "constants" in binData and binData["constants"]["__type"] == "{d65315ee}" and "{df085b93}" in binData["constants"] and (var in binData["constants"]["{df085b93}"] or var_hash in binData["constants"]["{df085b93}"]): #云顶之弈通用常数（TFT general constants）
            if var in binData["constants"]["{df085b93}"]:
                dataValue = binData["constants"]["{df085b93}"][var]
            else:
                dataValue = binData["constants"]["{df085b93}"][var_hash]
            if dataValue["__type"] == "GameModeConstantFloat" or dataValue["__type"] == "GameModeConstantInteger":
                if "mValue" in dataValue:
                    normalValue = str(cls.aRound(dataValue["mValue"], 5))
                else:
                    skip = True
            elif dataValue["__type"] == "{8beb0550}":
                valueDict: dict[str, str] = {}
                if "DefaultValue" in dataValue:
                    valueDict["default"] = str(cls.aRound(dataValue["DefaultValue"], 5))
                if "{b9562e5b}" in dataValue:
                    for (key1, value1) in dataValue["{b9562e5b}"].items():
                        valueDict[key1] = str(cls.aRound(value1, 5))
                valueList: list[str] = []
                for (key1, value1) in valueDict.items():
                    valueList.append("%s ({8beb0550}: %s)" %(value1, key1))
                normalValue = "(" + " || ".join(valueList) + ")" #由于其上可能会嵌套羁绊的条件，因此单独添加一个括号（Because this result may be a sub-result of conditional trait set, the brackets are added aside）
                if normalValue == "()":
                    skip = True
            else: #异常处理（Exception handling）
                skip = True
        elif "__type" in binData and binData["__type"] == "TftTraitData" and "InnateTraitSets" in binData and "constants" in binData["InnateTraitSets"][0] and "{df085b93}" in binData["InnateTraitSets"][0]["constants"] and var in binData["InnateTraitSets"][0]["constants"]["{df085b93}"]: #引用的云顶之弈羁绊数据：固有羁绊效果（Cited TFT trait data: Innate trait data values. Examples: ）@TFTTrait.TFTEvent5YR_Punk:FIRST_ROLL_BONUS@%; TFT14_HotRod
            normalValue = cls.variableCalculation(binData["InnateTraitSets"][0], var, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            #将进入云顶之弈通用常数分支（This call is expected to enter the TFT general constants branch）
        elif "__type" in binData and binData["__type"] == "TftTraitData" and "InnateTraitSets" in binData and "constants" in binData["InnateTraitSets"][0] and "{df085b93}" in binData["InnateTraitSets"][0]["constants"] and var_hash in binData["InnateTraitSets"][0]["constants"]["{df085b93}"]: #上一行判断语句的hash写法（The above condition rewritten by `var_hash`）
            normalValue = cls.variableCalculation(binData["InnateTraitSets"][0], var_hash, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
            #将进入云顶之弈通用常数分支（This call is expected to enter the TFT general constants branch）
        elif "__type" in binData and binData["__type"] == "TftTraitData" and "mConditionalTraitSets" in binData and (any(var in list(traitSet["constants"]["{df085b93}"].keys()) for traitSet in binData["mConditionalTraitSets"] if "constants" in traitSet and "{df085b93}" in traitSet["constants"]) or any(var in list(traitSet.keys()) for traitSet in binData["mConditionalTraitSets"])): #引用云顶之弈羁绊数据：条件羁绊效果。示例：（Cited TFT trait data: Conditional trait data values. Examples: ）@TFTTrait.TFT15_MechanicTrait_DreadNote.1:MinUnits@; TFT14_AnimaSquad ({22205c29})
            if rowIndex >= 0 and rowIndex < len(binData["mConditionalTraitSets"]):
                normalValue = cls.variableCalculation(binData["mConditionalTraitSets"][rowIndex], var, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                #将进入云顶之弈通用常数分支（This call is expected to enter the TFT general constants branch）
            else: #如果一个变量的出现次数超过期望值——mConditionalTraitSets键的值列表的元素数量，则不再对该变量进行转换。示例：云顶之弈第16赛季约德尔人羁绊的说明文本——{040cd634c5}（If the number of times a variable has appearred exceeds the expectation: the number of elements in the value list of `mConditionalTraitSets` key, then the program won't perform any substitution on this variable. Example: TFT16_Yordle's tooltip - {040cd634c5}）
                skip = True
        elif "__type" in binData and binData["__type"] == "TftTraitData" and "mConditionalTraitSets" in binData and (any(var_hash in list(traitSet["constants"]["{df085b93}"].keys()) for traitSet in binData["mConditionalTraitSets"] if "constants" in traitSet and "{df085b93}" in traitSet["constants"]) or any(var_hash in list(traitSet.keys()) for traitSet in binData["mConditionalTraitSets"])): #上一行判断语句的hash写法（The above condition rewritten by `var_hash`）
            if rowIndex >= 0 and rowIndex < len(binData["mConditionalTraitSets"]):
                normalValue = cls.variableCalculation(binData["mConditionalTraitSets"][rowIndex], var_hash, var_prefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                #将进入云顶之弈通用常数分支（This call is expected to enter the TFT general constants branch）
            else: #如果一个变量的出现次数超过期望值——mConditionalTraitSets键的值列表的元素数量，则不再对该变量进行转换。示例：云顶之弈第16赛季约德尔人羁绊的说明文本——{040cd634c5}（If the number of times a variable has appearred exceeds the expectation: the number of elements in the value list of `mConditionalTraitSets` key, then the program won't perform any substitution on this variable. Example: TFT16_Yordle's tooltip - {040cd634c5}）
                skip = True
        elif "__type" in binData and binData["__type"] == "ScriptDataObject" and "mConstants" in binData and (var in binData["mConstants"] or var_hash in binData["mConstants"]): #云顶之弈指令数据（TFT script data）
            if var in binData["mConstants"]:
                dataValue = binData["mConstants"][var]
            else:
                dataValue = binData["mConstants"][var_hash]
            if dataValue["__type"] in {"GameModeConstantBool", "GameModeConstantInteger"}:
                if "mValue" in dataValue:
                    normalValue = str(dataValue["mValue"])
                else:
                    skip = True
            elif dataValue["__type"] == "GameModeConstantFloat":
                if "mValue" in dataValue:
                    normalValue = str(cls.aRound(dataValue["mValue"], 5))
                else:
                    skip = True
            elif dataValue["__type"] == "GameModeConstantString":
                if "mValue" in dataValue:
                    normalValue = dataValue["mValue"]
                else:
                    skip = True
            elif dataValue["__type"] == "GameModeConstantStringVector":
                if "mValue" in dataValue:
                    normalValue = json.dumps(dataValue["mValue"], ensure_ascii = False)
                else:
                    skip = True
            elif dataValue["__type"] == "GameModeConstantTRAKey":
                if "mValue" in dataValue:
                    normalValue = "{" + dataValue["mValue"] + "}"
                else:
                    skip = True
            elif dataValue["__type"] in {"GameModeConstantVector3f", "{6a0aa453}"}:
                if "mValue" in dataValue:
                    normalValue = json.dumps(list(map(lambda x: cls.aRound(x, 5), dataValue["mValue"])))
                else:
                    skip = True
            elif dataValue["__type"] == "{1099c885}":
                if "Character" in dataValue:
                    normalValue = dataValue["Character"]
                else:
                    skip = True
            elif dataValue["__type"] == "{43e9418e}": #云顶之弈单羁绊（Single TFT trait）
                if "Trait" in dataValue:
                    if flexibleData != None and "map22_bin" in flexibleData and dataValue["Trait"] in flexibleData["map22_bin"]:
                        traitData = flexibleData["map22_bin"][dataValue["Trait"]]
                        if "mDisplayNameTra" in traitData and "tftstringtable" in flexibleData:
                            normalValue = cls.get_strtable_value(flexibleData["tftstringtable"], traitData["mDisplayNameTra"], default = traitData["mName"])
                        else:
                            normalValue = traitData["mName"]
                    else:
                        normalValue = dataValue["Trait"]
                else:
                    skip = True
            elif dataValue["__type"] == "{71ae72e5}": #云顶之弈羁绊列表（TFT trait list）
                if "traits" in dataValue:
                    if flexibleData != None and "map22_bin" in flexibleData:
                        traitNameList: list[str] = []
                        for trait_key in dataValue["traits"]:
                            if trait_key in flexibleData["map22_bin"]:
                                traitData = flexibleData["map22_bin"][trait_key]
                                if "mDisplayNameTra" in traitData and "tftstringtable" in flexibleData:
                                    traitNameList.append(cls.get_strtable_value(flexibleData["tftstringtable"], traitData["mDisplayNameTra"], default = traitData["mName"]))
                                else:
                                    traitNameList.append(traitData["mName"])
                            else:
                                traitNameList.append(trait_key)
                        normalValue = json.dumps(traitNameList, ensure_ascii = False)
                    else:
                        normalValue = json.dumps(dataValue["traits"], ensure_ascii = False)
                else:
                    skip = True
            elif dataValue["__type"] == "{80996016}": #排除的云顶之弈装备/强化符文列表（Excluded TFT item / augment list）
                if "items" in dataValue:
                    if flexibleData != None and "map22_bin" in flexibleData:
                        itemNameList: list[str] = []
                        for item_key in dataValue["items"]:
                            if item_key in flexibleData["map22_bin"]:
                                itemData = flexibleData["map22_bin"][item_key]
                                if "mDisplayNameTra" in itemData and "tftstringtable" in flexibleData:
                                    itemNameList.append(cls.get_strtable_value(flexibleData["tftstringtable"], itemData["mDisplayNameTra"], default = itemData["mName"]))
                                else:
                                    itemNameList.append(itemData["mName"])
                            else:
                                itemNameList.append(item_key)
                        normalValue = json.dumps(itemNameList, ensure_ascii = False)
                    else:
                        normalValue = json.dumps(dataValue["traits"], ensure_ascii = False)
                else:
                    skip = True
            elif dataValue["__type"] == "{9f9ec6c2}": #云顶之弈角色（TFT characters）
                if "characters" in dataValue:
                    if flexibleData != None and "characters_bin" in flexibleData:
                        characterNameList: list[str] = []
                        for character_key in dataValue["characters"]:
                            if character_key in flexibleData["map22_bin"]:
                                characterData = flexibleData["map22_bin"][character_key]
                                if "stringtable" in flexibleData:
                                    if "name" in characterData:
                                        characterNameList.append(cls.get_strtable_value(flexibleData["stringtable"], characterData["name"], default = characterData["mName"]))
                                    else:
                                        characterNameList.append(cls.get_strtable_value(flexibleData["stringtable"], "displayname_" + characterData["mCharacterName"], default = characterData["mName"]))
                                else:
                                    characterNameList.append(characterData["mName"])
                            else:
                                characterNameList.append(character_key)
                        normalValue = json.dumps(characterNameList, ensure_ascii = False)
                    else:
                        normalValue = json.dumps(dataValue["characters"], ensure_ascii = False)
                else:
                    skip = True
            elif dataValue["__type"] == "{a82b69c9}": #云顶之弈装备（TFT Item）
                if "Item" in dataValue:
                    if flexibleData != None and "map22_bin" in flexibleData and dataValue["Item"] in flexibleData["map22_bin"]:
                        itemData = flexibleData["map22_bin"][dataValue["Item"]]
                        if "mDisplayNameTra" in itemData and "tftstringtable" in flexibleData:
                            normalValue = cls.get_strtable_value(flexibleData["tftstringtable"], itemData["mDisplayNameTra"], default = itemData["mName"])
                        else:
                            normalValue = itemData["mName"]
                    else:
                        normalValue = dataValue["Item"]
                else:
                    skip = True
            else:
                skip = True
        elif (matchObj := pOtherBinDataHeader.search(var)): #目前暂未发现引用型变量有使用hash值的。这很好理解：解析肯定是整个解析出来的，不可能解析一半就放出来了（Currently no cited variable is found to have a hash value as its part. This is easy to understand: to resolve a hash, that string must be resolved totally. It's impossible that some program resolves part of a hash value and then returns the intermediate calculation as a result）
            otherBinDataPrefix: str = matchObj.group().rstrip(":")
            otherBinDataPrefix_elements: list[str] = otherBinDataPrefix.split(".")
            otherBinData_category: str = otherBinDataPrefix_elements[0]
            otherBinData_mName: str = otherBinDataPrefix_elements[1] if len(otherBinDataPrefix_elements) > 1 else ""
            otherBinData_varIndex: int = int(otherBinDataPrefix_elements[2]) if len(otherBinDataPrefix_elements) > 2 else -1 #因为这个参数，导致本函数族又多了一个参数（Thanks to this variable, this function family added another variable）
            otherBinData_var: str = var.replace(matchObj.group(), "")
            if otherBinData_category.lower() == "spell":
                if otherBinData_mName in cls.mSpells:
                    if "mSpell" in cls.mSpells[otherBinData_mName]:
                        otherBinData: dict[str, Any] = cls.mSpells[otherBinData_mName]["mSpell"]
                        otherBinData = cls.normalizeBinData(otherBinData) #由于以上字符串的替换方法，同一个变量只可能在一次替换过程中经历此分支一次（One variable can only pass this branch once, due to the `replace` method above）
                        normalValue = cls.variableCalculation(otherBinData, otherBinData_var, otherBinDataPrefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                    else: #部分指令对象中没有mSpell键（Some SpellObjects don't have `mSpell` key）
                        skip = True
                else: #在装备说明文本中出现了惩戒的对象名（The object name of Smite exists in an item's tooltip）
                    skip = True
            elif otherBinData_category == "ScriptData":
                if otherBinData_mName in cls.TFTScriptDataMap:
                    otherBinData = cls.TFTScriptDataMap[otherBinData_mName]
                    normalValue = cls.variableCalculation(otherBinData, otherBinData_var, otherBinDataPrefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                else:
                    skip = True
            elif otherBinData_category == "TFTUnitProperty":
                if otherBinData_var in cls.TFTUnitPropertyMap:
                    otherBinData = cls.TFTUnitPropertyMap[otherBinData_var]
                    normalValue = cls.variableCalculation(otherBinData, otherBinData_var, otherBinDataPrefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = rowIndex, reservedVars = reservedVars, flexibleData = flexibleData)
                else:
                    skip = True
            elif otherBinData_category == "TFTTrait":
                if otherBinData_mName in cls.TFTTraitMap:
                    otherBinData = cls.TFTTraitMap[otherBinData_mName]
                    normalValue = cls.variableCalculation(otherBinData, otherBinData_var, otherBinDataPrefix, isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = otherBinData_varIndex - 1, reservedVars = reservedVars, flexibleData = flexibleData)
                else:
                    skip = True
        else:
            skip = True
        calculatedVar: str = var if var_prefix == "" else f"{var_prefix}:{var}" #通过指定变量前缀以避免一种情况：被引用的外部指令中含有和原指令相同的键（Specify the prefix to avoid a case where the external spell has a same key as the original spell）
        if skip:
            normalValue = f"@{calculatedVar}@"
        #下面处理模式覆盖数值（Next, resolve the mode overriden data values）
        modeOverrideValues: dict[str, str] = {"default": normalValue}
        if enableModeOverride:
            modeOverrideValues_tmp: dict[str, str] = cls.variableModeOverrideCalculation(binData, var)
            for (gameModeName, modeOverrideValue) in modeOverrideValues_tmp.items(): #调整顺序，使得遍历时先遍历默认数值（Adjust the order, so that the default value goes through traversal first）
                modeOverrideValues[gameModeName] = modeOverrideValue
            del modeOverrideValues_tmp
        modeOverrideValueDict_raw: dict[str, str] = {} #存储转换中途带模式名的计算结果。所谓转换中途，指的是变量被转换为数值，但是仍保持连除式的格式（Stores halfway calculation result. "halfway" means the variable is transformed into the actual value where continuous division still remains）
        for (gameModeName, modeOverrideValue) in modeOverrideValues.items():
            modeOverrideValueDict_raw[gameModeName] = modeOverrideValue if gameModeName == "default" else f"{modeOverrideValue} (mode: {gameModeName})"
        if len(modeOverrideValues) > 1:
            cls.calculatedVariables[calculatedVar] = {"value": modeOverrideValues, "__type": "ModeOverrideValue"}
        else:
            cls.calculatedVariables[calculatedVar] = {"value": normalValue, "__type": "SingleValue"}
        #得出最终结果（Get the final result）
        result = " || ".join(list(modeOverrideValueDict_raw.values()))
        return result

    @classmethod
    def variableSubstitute(cls, tooltip: str, binData: dict[str, Any], isCHS: bool = False, enableModeOverride: bool = False, reserve_variable: bool = False, reservedVars: Optional[dict[str, str]] = None, flexibleData: Optional[dict[str, dict[str, Any] | Any]] = None): #将双@包围的表达式转换成具体数值（Convert expressions enclosed in double @ into specific stats）
        '''
        将变量替换为具体数值字符串。<br>Replace variables in a tooltip with its result value string.
        
        :param tooltip: 原始说明文本。<br>Raw tooltip.
        :type tooltip: str
        :param binData: 标准化后的二进制描述数据。<br>Normalized binary description data.
        :type binData: dict[str, Any]
        :param isCHS: 是否应用简体中文标点符号。默认为否。<br>Whether to use quotation marks in Chinese Simplified, `False` by default.
        :type isCHS: bool
        :param enableModeOverride: 是否启用模式覆盖。启用后，将统计某个变量在不同模式中的数值。默认为假。<br>Whether to enable mode overriden values. If enabled, values among different modes will be taken into consideration. False by default.
        :type enableModeOverride: bool
        :param reserve_variable: 是否将变量代换后的结果写成“[{变量名}] = {值}”的形式。默认为假。<br>Whether to write the result after variable substitution in the form of "[{Var_name}] = {Value}". False by default.
        :type reserve_variable: bool
        :param reservedVars: 处理暂存的变量值，对于一些在嵌套时仍然保持变量形式的说明文本尤其有用，例如奥恩被动的说明文本。<br>Handles reserved variable values, especially useful for some tooltips that still keep the variable form during nesting, e.g. OrnnP.
        :type reservedVars: dict[str, str] | None
        :param flexibleData: 附加数据。<br>Supplemental data.
        :type flexibleData: dict[str, dict[str, Any] | Any] | None
        :return: 变量代换后的说明文本。<br>Tooltip after variable substitution.
        :rtype: str
        '''
        pStats: re.Pattern[str] = re.compile(r"@.*?@") #贪婪模式（Greedy pattern）
        pVar: re.Pattern[str] = re.compile(r"[\w\.\-\:\{\}]+") #部分变量引用了其它指令数据（Some variables cite other spell data）
        #从此处开始，将逐渐推导出sResult_ValueAmongModes（From this step, we'll derivate and obtain `SResult_ValueAmongModes` as a result）
        sResult_SingleValue: str = r"(\{\w+\}|\d+\.\d+|\d+)" #单值（Single value）
        sResult_ValueOfSingleMode: str = f"{sResult_SingleValue}(/{sResult_SingleValue})*" #单值或连除式（Single value or continuous division）
        sResult_SingleModePart: str = r" \(mode: (\{\w+\}|\w+)\)" #特定模式。注意前面有一个空格（Specific mode. Note that this pattern starts with a space）
        sResult_ValueMode: str = f"{sResult_ValueOfSingleMode}({sResult_SingleModePart})?" #特定模式下的单个数值或连除式（Single value or continuous division of a mode）
        sResult_ValueModeSeparator: str = r" \|\| " #不同模式的单个数值或连除式的分隔符（Separator of single value or continuous division among different modes）
        sResult_ValueAmongModes: str = f"{sResult_ValueMode}({sResult_ValueModeSeparator}{sResult_ValueMode})*" #不同模式下的单个数值或连除式（Single value or continuous division among different modes）
        pResult_ModeBurn: re.Pattern[str] = re.compile(sResult_ValueAmongModes)
        # pResult_ModeBurn: re.Pattern[str] = re.compile(r"(\{\w+\}|\d+\.\d+|\d+)(/(\{\w+\}|\d+\.\d+|\d+))*( \(mode: (\{\w+\}|\w+)\))?( \|\| (\{\w+\}|\d+\.\d+|\d+)(/(\{\w+\}|\d+\.\d+|\d+))*( \(mode: (\{\w+\}|\w+)\))?)*") #不同模式下的单个数值或连除式（Single value or continuous division among different modes）
        pModePart: re.Pattern[str] = re.compile(sResult_SingleModePart) #识别变量计算结果中的游戏模式名称部分。需要注意，游戏模式名称可能为未解析的hash值。这里假设每个模式覆盖变量都是最基本的单项式。作出这个假设是为了保证在识别出“a || b”后，能够正确地进行公式计算，得到“eval(a + formula) || eval(b + formula)”（Identifies the gameModeName in the calculation result of `var`. Note that the gameModeName may be an unhashed value. Here we assume each mode overriden variable is the most basic monomial. This assumption is made to ensure that the subsequent formula calculation can correctly derivate from "a || b" to "eval(a + formula) || eval(b + formula)"）
        #被双花括号包围的变量不应被替换，而应放到嵌套替换函数中被替换（Variables nested within a pair of double curly brackets shouldn't be substituted here, but in `nestedVariableSubstitute` function）
        sTooltipNestedStats: str = r"\{\{\s*\w*@\w+@\w*\s*\}\}"
        pTooltipNestedStats: re.Pattern[str] = re.compile(sTooltipNestedStats)
        coordinates_to_skip: list[tuple[int, int]] = []
        for matchObj in pTooltipNestedStats.finditer(tooltip):
            coordinates_to_skip.append((matchObj.start(), matchObj.end()))
        #下面通过一次性识别某个说明文本中所有的匹配情况，执行按索引替换字符串，而不是通过传统的replace方法替换。这样适用于相同变量替换成不同值的场景（By identifying all matches of a tooltip string for once, we'll replace the string according to the index, instead of the traditional string's replace method. This applies to the case where the same variables need to be replaced with different values）
        matchStructs: list[dict[str, str | int]] = []
        for matchObj in pStats.finditer(tooltip):
            stat: str = matchObj.group()
            skip: bool = False
            for coordinate in coordinates_to_skip:
                if matchObj.start() >= coordinate[0] and matchObj.end() <= coordinate[1]:
                    skip = True
                    break
            if skip:
                continue
            matchStruct: dict[str, str | int] = {}
            matchStruct["var"] = stat #这个var键只是为了方便调试，实际没有参与字符串替换。注意，这个var键的值和下面替换过程中的var变量的值有所不同，它是有双@包围的（This `var` key is only meant for debug. It doesn't participant in string replacement actually. Note that the value of this `var` key is different from the value of the `var` variable in the following replacement stage, because the value of this `var` key is "@" enclosed）
            matchStruct["start"] = matchObj.start()
            matchStruct["end"] = matchObj.end()
            matchStruct["result"] = stat #初始化为原始值（Initialized as the original value）
            matchStruct["rowIndex"] = tooltip[:matchObj.start()].count("<row>") - 1 #统计每个自制匹配结构中的变量是第几次出现在说明文本中的。这对于云顶之弈羁绊的变量替换尤其有用（This counts the number of times the variable in each `matchStruct` appears in the tooltip. Especially useful for variable substitution in TFT trait tooltip）
            matchStructs.append(matchStruct)
        #下面主要对每个自制匹配结构的result键进行修改（In the following, change the `result` key of each `matchStruct`）
        for matchStruct in matchStructs:
            old: str = matchStruct["var"]
            expr: str = old.replace("@", "")
            if (matchObj := pVar.search(expr)):
                var: str = matchObj.group() #这里默认每个数值只涉及一个变量（By default, each stat is only related to one variable）
                formula: str = expr.replace(var, "") #最常见的值是“*100”。在应对不同模式的数值时，公式部分是不变的（The most case is "*100". Although different game modes may have different data values, the formula part stays the same）
                if formula == "{}": #特殊处理在转换过程中产生的变量（Special case: variable produced during processing）
                    var = "{" + var + "}"
                    formula = ""
                result: str = cls.variableCalculation(binData, var, "", isCHS = isCHS, enableModeOverride = enableModeOverride, rowIndex = matchStruct["rowIndex"], reservedVars = reservedVars, flexibleData = flexibleData) #如果存在多个模式的数值，则这些数值由双竖线连接（If there're mode override values for `var`, these values should be concatenated by double "|"）
                if formula == "": #这里认为在双@内涉及二次计算的表达式中的变量视为简单变量，即在binData、binData["DataValues"]或binData["mDataValues"]中能够直接找到的变量。不然的话，拳头的程序员为什么不把这个公式放到binData["mItemCalculations"]或者binData["mSpellCalculations"]的部分呢？（Here we assume if the expression has secondary calculation like "*100", then its variable must be a **simple variable**, that is, a variable that can be directly found in `binData`, `binData["DataValues"]` or `binData["mDataValues"]`. Otherwise, why don't Riot programmers put this formula in `binData["mItemCalculations"]` or `binData["mSpellCalculations"]`?）
                    new: str = result
                else:
                    #这里实际上并没有使用pResult_ModeBurn对result进行识别，因为基于以上假设，在存在二次计算公式的情况下，pResult_ModeBurn应完全匹配result。典型示例：探险家 伊泽瑞尔的【咒能高涨】的AttackSpeedPerStack变量（Here we're not using `pResult_ModeBurn` to identify the result among different modes, because based on the above assumption, `pResult_ModeBurn` should completely match and span `result`. A typical example: EzrealPassive's `AttackSpeedPerStack` variable）
                    modeOverrideValue_burn: str = result
                    modeOverrideValue_list: list[str] = modeOverrideValue_burn.split(" || ")
                    modeOverrideValues: dict[str, str] = {} #从modeOverrideValue_burn中还原不同模式的数值。需要注意，本函数族完全基于字符串的思想来执行变量代换（Recover different modes' data values from `modeOverrideValue_burn`. Recall that this function family performs variable substitution totally based on string operations）
                    for modeOverrideValueStr in modeOverrideValue_list:
                        if (matchObj1 := pModePart.search(modeOverrideValueStr)):
                            modePart: str = matchObj1.group()
                            gameModeName: str = modePart.replace(" (mode: ", "").rstrip(")")
                            modeOverrideValueStr: str = modeOverrideValueStr.replace(modePart, "")
                        else:
                            gameModeName: str = "default"
                        modeOverrideValues[gameModeName] = modeOverrideValueStr
                    modeOverrideValueDict: dict[str, str] = {} #存储转换后的计算结果（Stores pure result after transformation）
                    modeOverrideValueDict_burn: dict[str, str] = {} #存储转换后带模式名的计算结果。join函数对此字典的值列表执行（Stores calculation result plus gameModeName after transformation. `join` function is used on this dictionary's value list）
                    for (gameModeName, value) in modeOverrideValues.items():
                        if value != old:
                            if cls.isContDivision(value): #处理值列表元素不唯一的情形，防止其被视为连除式而参与后续eval的计算（Handles the case where value elements aren't the same, in case it would be considered as a continuous division by the subsequent `eval` function）
                                valueList: list[str] = list(map(lambda x: x + formula, value.split("/")))
                                for i in range(len(valueList)):
                                    try:
                                        valueList[i] = eval(valueList[i].replace("×", "*"))
                                    except:
                                        pass
                                    else:
                                        valueList[i] = str(cls.aRound(valueList[i], 5))
                                value = "/".join(valueList)
                            else:
                                value += formula
                                try:
                                    value = eval(value.replace("×", "*"))
                                except:
                                    pass
                                else:
                                    value = str(cls.aRound(value, 5))
                        modeOverrideValueDict[gameModeName] = value
                        modeOverrideValueDict_burn[gameModeName] = value if gameModeName == "default" else f"{value} (mode: {gameModeName})" #这一处可以在“{gameModeName}”前添加“Mode: ”，以指定该附加说明的用意，同时也便于后续可能的正则表达式识别环节（In this line, we can add "Mode: " to the front of "{gameModeName}" to specify this supplemental note's intention. In the meantime, adding "Mode: " may also make it convenient for subsequent regular expression identification）
                    new: str = " || ".join(list(modeOverrideValueDict_burn.values())) #本脚本规定，双竖线用于分隔不同模式的数值（Define double "|" as the separator of values among different modes）
                if new != old:
                    new = "{[%s] = %s}" %(expr, new) if reserve_variable else "{%s}" %(new) #一旦变量被对应上，变量两边的“@”就会被去掉，在下一次迭代时就不会被pStats识别，即使对应可能还没有完全完成，因此不存在花括号被重复添加的可能（Once the variable is matched with some value, the double "@" enclosing this variable will be removed, and then this variable won't be identified by `pStats`, even if the match isn't thorough, so there's no chance that the curly brackets could be added for multiple times）
                matchStruct["result"] = new
            else: #这是极少见的情况，出现在双@内没有任何字符的情形，例如测试服16.1.730.7246版本的【增益引擎】的说明文本（This is a very rare case, when there's not any character between the pair of "@". An example is the tooltip of Bandlepipes in PBE Patch 16.1.730.7246）
                matchStruct["result"] = old
        #按索引反向替换（Index-wise reverse replacement）
        for matchStruct in matchStructs[::-1]:
            start_index: int = matchStruct["start"]
            end_index: int = matchStruct["end"]
            tooltip = tooltip[:start_index] + matchStruct["result"] + tooltip[end_index:]
        return tooltip

    @classmethod
    def nestedVariableSubstitute(cls, tooltip: str, strtable_locale: dict[str, int | dict[str, str]], binData: dict[str, Any], isCHS: bool = False, enableModeOverride: bool = False) -> tuple[str, dict[str, list[str]]]: #将嵌套变量转换成具体数值（Convert nested variables into specific stats）
        '''
        专用于处理说明文本内嵌套的说明文本变量。<br>Specifically designed to handle the tooltip keys nested in a tooltip string.
        
        :param tooltip: 原始说明文本。<br>Raw tooltip.
        :type tooltip: str
        :param strtable_locale: 字符串常量池。<br>Stringtable.
        :type strtable_locale: dict[str, int | dict[str, str]]
        :param binData: 标准化后的二进制描述数据。<br>Normalized binary description data.
        :type binData: dict[str, Any]
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :param enableModeOverride: 是否启用模式覆盖。启用后，将统计某个变量在不同模式中的数值。默认为假。<br>Whether to enable mode overriden values. If enabled, values among different modes will be taken into consideration. False by default.
        :type enableModeOverride: bool
        :return: 转换**一次**嵌套说明文本变量后的说明文本字符串。<br>The result tooltip string after **one time of** transformation of nested tooltip variables.
        :rtype: str
        '''
        result: str = tooltip
        #下面对变量嵌套单变量的形态进行转换。这一步只有在执行variableSubstitute函数后才可以执行。例如只有在执行variableSubstitute函数后，“{{Spell_HeightenedLearning_Tooltip_@GameModeInteger@}}”才会转变为“{{Spell_HeightenedLearning_Tooltip_{1}}}”（In the following, transform the tooltips where a variable is nested under another variable. Only after `variableSubstitute` function is executed may this step be performed. For example, "{{Spell_HeightenedLearning_Tooltip_@GameModeInteger@}}" won't transform into "{{Spell_HeightenedLearning_Tooltip_{1}}}" until `variableSubstitute` function is executed）
        sTooltipNestedVarValue: str = r"\{[0-9]+\}"
        sTooltipNestedVar: str = r"\{\{\s*\w*" + sTooltipNestedVarValue + r"\w*\s*\}\}"
        pTooltipNestedVar: re.Pattern[str] = re.compile(sTooltipNestedVar)
        pTooltipNestedVarValue: re.Pattern[str] = re.compile(sTooltipNestedVarValue)
        while (matchObj := pTooltipNestedVar.search(result)):
            tooltipNestedVar: str = matchObj.group()
            tooltipNestedVar_result: str = pTooltipNestedVarValue.search(tooltipNestedVar).group() #无需判断是否能匹配到，因为pTooltipNestedVar本来就包含pTooltipNestedVarValue（Don't need to judge whether it can be matched, for `pTooltipNestedVar` already contains `pTooltipNestedVarValue`）
            tooltipValue: str = tooltipNestedVar_result.lstrip("{").rstrip("}")
            tooltipCitation_key: str = tooltipNestedVar.replace(tooltipNestedVar_result, tooltipValue)
            tooltipResult: str = cls.get_strtable_value(strtable_locale, tooltipCitation_key, default = tooltipCitation_key)
            result = result.replace(tooltipNestedVar, tooltipResult)
        #下面对变量嵌套条件变量（往往是同一个技能的不同形态）进行转换。这一步只有在执行variableSubstitute函数后才可以执行。例如只有在执行variableSubstitute函数后，“{{Spell_KarmaE_Tooltip_@spell.KarmaQ:IsEmpowered@}}”才会转变为“{{Spell_KarmaE_Tooltip_{0 (without {752d125a}) | 1 (with {752d125a})}}}”（In the following, transform the tooltips where a conditional variable is nested under another variable (always applies to the case of different forms of one ability). Only after `variableSubstitute` function is executed may this step be performed. For example, "{{Spell_KarmaE_Tooltip_@spell.KarmaQ:IsEmpowered@}}" won't transform into "{{Spell_KarmaE_Tooltip_{0 (without {752d125a}) | 1 (with {752d125a})}}}" until `variableSubstitute` function is executed）
        sTooltipCondition1: str = r" \((melee|without \{?\w*\}?)\)" #专用于mItemCalculations键的值类型为GameCalculationConditional的情形。下同（Specially applies to the case where the type of the value of `mItemCalculations` key is `GameCalculationConditional`. So is the following regular expression）
        sTooltipCondition2: str = r" \((ranged|with \{?\w*\}?)\)"
        sTooltipSplit: str = r"\{[0-9]+" + sTooltipCondition1 + r" \| [0-9]+" + sTooltipCondition2 + r"\}"
        sTooltipSplit_key: str = r"\{\{\s*\w*" + sTooltipSplit + r"\w*\s*\}\}"
        pTooltipSplit: re.Pattern[str] = re.compile(sTooltipSplit)
        pTooltipSplit_key: re.Pattern[str] = re.compile(sTooltipSplit_key)
        pTooltipCondition1: re.Pattern[str] = re.compile(sTooltipCondition1)
        pTooltipCondition2: re.Pattern[str] = re.compile(sTooltipCondition2)
        while (matchObj := pTooltipSplit_key.search(result)):
            tooltipSplit_key: str = matchObj.group()
            tooltipSplit_result: str = pTooltipSplit.search(tooltipSplit_key).group() #无需判断是否能匹配到，因为pTooltipSplit_key本来就包含pTooltipSplit（Don't need to judge whether it can be matched, for `pTooltipSplit_key` already contains `pTooltipSplit`）
            tooltip1Condition: str = pTooltipCondition1.search(tooltipSplit_result.split(" | ")[0]).group()
            tooltip2Condition: str = pTooltipCondition2.search(tooltipSplit_result.split(" | ")[1]).group()
            tooltip1Value: str = tooltipSplit_result.split(" | ")[0].lstrip("{").replace(tooltip1Condition, "")
            tooltip2Value: str = tooltipSplit_result.split(" | ")[1].rstrip("}").replace(tooltip2Condition, "")
            tooltip1Citation_key: str = tooltipSplit_key.replace(tooltipSplit_result, tooltip1Value).lstrip("{{").rstrip("}}").strip()
            tooltip2Citation_key: str = tooltipSplit_key.replace(tooltipSplit_result, tooltip2Value).lstrip("{{").rstrip("}}").strip()
            tooltip1Result: str = cls.get_strtable_value(strtable_locale, tooltip1Citation_key, tooltip1Citation_key)
            tooltip2Result: str = cls.get_strtable_value(strtable_locale, tooltip2Citation_key, tooltip2Citation_key)
            tooltipSplit_result_burn: str = "%s%s | %s%s" %(tooltip1Result, tooltip1Condition, tooltip2Result, tooltip2Condition)
            result = result.replace(tooltipSplit_key, tooltipSplit_result_burn)
        #下面对变量嵌套单值模式变量进行转换。这一步只有在执行variableSubstitute函数后才可以执行。例如只有在执行variableSubstitute函数后，“{{ Spell_SecondSight_Tooltip_@GameModeInteger@ }}”才会转变为“{{ Spell_SecondSight_Tooltip_{1 || 2 (mode: cherry)} }}”（In the following, transform the tooltips where a single-value mode variable is nested under another variable. Only after `variableSubstitute` function is executed may this step be performed. For example, "{{ Spell_SecondSight_Tooltip_@GameModeInteger@ }}" won't transform into "{{ Spell_SecondSight_Tooltip_{1 || 2 (mode: cherry)} }}" until `variableSubstitute` function is executed）
        sTooltipSingleValue: str = r"(\d+\.\d+|\d+)" #单值（Single value）
        sTooltipSingleModePart: str = r" \(mode: (\{\w+\}|\w+)\)" #特定模式（Specific mode）
        sTooltipValueMode: str = f"{sTooltipSingleValue}({sTooltipSingleModePart})?" #特定模式下的单个数值（Single value of a mode）
        sTooltipValueModeSeparator: str = r" \|\| " #不同模式的单个数值的分隔符（Separator of single value among different modes）
        sTooltipValueAmongModes: str = f"{sTooltipValueMode}({sTooltipValueModeSeparator}{sTooltipValueMode})+" #不同模式下的单个数值（Single value among different modes）
        sTooltipModeSplit: str = r"\{" + sTooltipValueAmongModes + r"\}" #被一对花括号包围的不同模式的数值（Single value among different modes enclosed within a pair of curly brackets）
        sTooltipModeSplit_key: str = r"\{\{\s*\w*" + sTooltipModeSplit + r"\w*\s*\}\}"
        pTooltipValueAmongModes: re.Pattern[str] = re.compile(sTooltipValueAmongModes)
        pTooltipModeSplit_key: re.Pattern[str] = re.compile(sTooltipModeSplit_key)
        pTooltipModeSplit: re.Pattern[str] = re.compile(sTooltipModeSplit)
        pTooltipSingleModePart: re.Pattern[str] = re.compile(sTooltipSingleModePart)
        reservedVars_list: dict[str, list[str]] = {} #至于为什么类型声明不是dict[str, dict[str, str]]，是因为整个程序是基于字符串来处理变量代换，而后续想要识别特定模式时是基于每个字符串结尾的“(mode: xxx)”来识别的（As for why the type declaration isn't `dict[str, dict[str, str]]`, it's because the whole program performs variable substitution based on string operations, and subsequent identification of specific modes is based on the "(mode: xxx)" at the end of each string）
        while (matchObj := pTooltipModeSplit_key.search(result)):
            start, end = matchObj.span()
            tooltipModeSplit_key: str = matchObj.group()
            tooltipModeSplit_result: str = pTooltipModeSplit.search(tooltipModeSplit_key).group() #无需判断是否能匹配到，因为pTooltipModeSplit_key本来就包含pTooltipModeSplit（Don't need to judge whether it can be matched, for `pTooltipModeSplit_key` already contains `pTooltipModeSplit`）
            modeOverrideValue_list: list[str] = tooltipModeSplit_result.lstrip("{").rstrip("}").split(" || ")
            modeOverrideValues: dict[str, str] = {} #从tooltipModeSplit_result中还原不同模式的数值（Recover different modes' data values from `tooltipModeSplit_result`）
            for modeOverrideValueStr in modeOverrideValue_list:
                if (matchObj1 := pTooltipSingleModePart.search(modeOverrideValueStr)):
                    modePart: str = matchObj1.group()
                    gameModeName: str = modePart.replace(" (mode: ", "").rstrip(")")
                    modeOverrideValueStr = modeOverrideValueStr.replace(modePart, "")
                else:
                    gameModeName: str = "default"
                modeOverrideValues[gameModeName] = modeOverrideValueStr
            tooltipModeSplit_results_burn: dict[str, str] = {}
            for (gameModeName, value) in modeOverrideValues.items():
                tooltipCitation_key: str = tooltipModeSplit_key.replace(tooltipModeSplit_result, value)
                tooltipResult: str = cls.get_strtable_value(strtable_locale, tooltipCitation_key, tooltipCitation_key)
                tooltipModeSplit_results_burn[gameModeName] = tooltipResult if gameModeName == "default" else f"{tooltipResult} (mode: {gameModeName})"
            if tooltipModeSplit_key == result or (start == 0 or result[start - 1] == "\n") and (end == len(result) - 1 or result[end + 1] == "\n"): #有些技能是整个说明文本作为一个变量的值，这种情况下最好能够多行展示不同情形（Some abilities has the whole tooltip as a value of a variable. In that case, it's better to display the different situations among multiple lines）
                separator: str = "\n||\n"
            else:
                separator: str = " || "
            tooltipModeSplit_result_burn: str = separator.join(list(tooltipModeSplit_results_burn.values()))
            result = result.replace(tooltipModeSplit_key, tooltipModeSplit_result_burn)
        else:
            for (key, value) in cls.calculatedVariables.items():
                if value["__type"] == "ModeOverrideValue":
                    reservedVars_list[key] = list(value["value"].values()) #这里假设每个嵌套的模式相关的变量在每个模式的说明文本中只出现一次（Here we assume each nested mode-related variable only appears once in each mode's tooltip）
        #下面对变量嵌套动态变量进行转换。典型示例：影流之镰 凯隐的技能（In the following, transform the tooltips where a dynamic variable is nested under another variable. A typical example: Kayn's abilities）
        sStats: str = r"@f\d+@"
        sTooltipForm: str = r"\{\{\s*\w*@f\d+@\w*\s*\}\}"
        pStats: re.Pattern[str] = re.compile(sStats)
        pTooltipForm: re.Pattern[str] = re.compile(sTooltipForm)
        while (matchObj := pTooltipForm.search(result)):
            start, end = matchObj.span()
            tooltipForm_key: str = matchObj.group()
            tooltipForm: str = tooltipForm_key.lstrip("{").rstrip("}").strip()
            matchObj1 = pStats.search(tooltipForm)
            strtable_key_static_part1: str = tooltipForm[:matchObj1.start()]
            strtable_key_static_part2: str = tooltipForm[matchObj1.end():]
            strtable_form_key: str = strtable_key_static_part1 + r"\d+" + strtable_key_static_part2
            pStrtable_form_key: re.Pattern[str] = re.compile(strtable_form_key.lower()) #注意字符串常量池中的键都是小写（Note that keys in stringtable are all in lower form）
            tooltip_form_keys: list[str] = []
            for key in strtable_locale["entries"].keys():
                if pStrtable_form_key.fullmatch(key):
                    tooltip_form_key = key.replace(strtable_key_static_part1.lower(), strtable_key_static_part1).replace(strtable_key_static_part2.lower(), strtable_key_static_part2)
                    tooltip_form_keys.append(tooltip_form_key)
            tooltip_form_keys.sort()
            tooltip_form_results: list[str] = list(map(lambda x: "{{%s}} (form: %s)" % (x, x), tooltip_form_keys))
            if tooltipForm_key == result or (start == 0 or result[start - 1] == "\n") and (end == len(result) or result[end + 1] == "\n"):
                separator: str = "\n||\n"
            else:
                separator: str = " || "
            tooltip_form_result_burn: str = separator.join(tooltip_form_results) #因为前面判定整个说明文本被匹配了，所以这里不需要讨论分隔符（Since we determined that the whole tooltip is matched, there's no need to discuss the separator here）
            result = result.replace(tooltipForm_key, tooltip_form_result_burn)
        #下面对其它嵌套变量进行可能的转换。典型示例：海克斯大乱斗强化符文套装【掷骰狂人】（In the following, transform the tooltips with other nested variables. A typical example: ARAM: Mayhem augment set High Roller）
        sTooltipNestedVarOther_var: str = r"@\w+@"
        sTooltipNestedVarOther: str = r"\{\{\s*\w*" + sTooltipNestedVarOther_var + r"\w*\s*\}\}"
        pTooltipNestedVarOther: re.Pattern[str] = re.compile(sTooltipNestedVarOther)
        pTooltipNestedVarOther_var: re.Pattern[str] = re.compile(sTooltipNestedVarOther_var)
        start_pos: int = 0
        while (matchObj := pTooltipNestedVarOther.search(result, pos = start_pos)):
            levelStrs: list[str] = []
            tooltipNestedVarOther: str = matchObj.group()
            tooltipNestedVarOther_var: str = pTooltipNestedVarOther_var.search(tooltipNestedVarOther).group() #无需判断是否能匹配到，因为pTooltipNestedVar2本来就包含pTooltipNestedVarOther（Don't need to judge whether it can be matched, for `pTooltipNestedVar2` already contains `pTooltipNestedVarOther`）
            for i in range(99):
                tmp_var: str = tooltipNestedVarOther.lstrip("{").rstrip("}").strip().replace(tooltipNestedVarOther_var, str(i))
                tmp_value: str = cls.get_strtable_value(strtable_locale, tmp_var, default = "")
                if tmp_value != "":
                    levelStrs.append(tmp_value + " (level: %d)" %i)
                elif i >= 10: #当某个水平不存在时，认为其后的水平也不存在。但是，在第五代斗魂竞技场中，【寄生关系】的说明文本——“Cherry_ParasiticRelationship@TeamSize@_Summary”中的TeamSize变量是从2开始的。毕竟没有单人成队的斗魂竞技场。考虑到一般这类变量取值都是一位数，所以这里强制至少从0遍历到9（When some level doesn't exist, we assume that the subsequent levels don't exist, either. However, in Arena v5, `TeamSize` variable in the tooltip of Parasitic Relationship, namely "Cherry_ParasiticRelationship@TeamSize@_Summary", starts from 2. An Arena game where single player makes up of a team doesn't exist, after all. Considering the value of these kind of parameters usually has only one digit, here it's forced to traverse at least from 0 to 9）
                    break
            if len(levelStrs) > 0:
                levelStr = "\n||\n".join(levelStrs)
                result = result.replace(tooltipNestedVarOther, levelStr)
            else:
                start_pos = matchObj.end()
        return (result, reservedVars_list)

    @classmethod
    def tooltipPreparation(cls, tooltip: str, isCHS: bool = False) -> str: #说明文本预处理（Tooltip preparation）
        '''
        移除说明文本中的CSS标签和修饰符。同时使用统一的标点符号表示强调。<br>Remove all CSS tags and descriptors in a tooltip. In the meantime, add uniform characters for the sake of emphasis.
        
        :param tooltip: 原始说明文本。<br>Raw tooltip.
        :type tooltip: str
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :return: 预处理后的说明文本。<br>Tooltip after preprocessing.
        :rtype: str
        '''
        pFormat: re.Pattern[str] = re.compile(r"</?[\s\w=#\'\"@\-\.]*>")
        pDescriptor: re.Pattern[str] = re.compile(r" ?%[A-Za-z0-9:]+% ?")
        layertags: set[str] = {"titleLeft", "titleRight", "subtitleLeft", "subtitleRight", "mainText", "postScriptTitle"}
        result: str = tooltip.replace("<br>", "\n").replace("<li>", "\n-\n").replace("<rules>", "").replace("</rules>", "").replace("<attention>", "").replace("</attention>", "").replace("&nbsp;", " ")
        for layertag in layertags | {"section"}: #因为会优化分节的字符串，所以这里把分节部分的修饰符也去掉（Because section strings will be optimized subsequently, section tags are removed here）
            result = result.replace(f"<{layertag}>", "").replace(f"</{layertag}>", "")
        while (matchObj := pDescriptor.search(result)): #移除修饰符（Remove descriptors）
            result = result.replace(matchObj.group(), "")
        start_index: int = 0
        while (matchObj := pFormat.search(result, pos = start_index)): #移除CSS标签。但为了表强调，添加统一的标点符号（Remove CSS tags. To declare emphasis, add universal punctuation marks）
            old: str = matchObj.group()
            if old == "<row>" or old == "</row>": #专用于云顶之弈羁绊说明文本确定变量的条件索引。已经事先确定其它说明文本中都不存在<row>标签。而且，既然是表示单独成行，不应该转变成中括号（Specially designed for TFT trait tooltip, to determine a variable's condition index. Already determined <row> tag doesn't contain other tooltips. Besides, since this tag means a single line, it shouldn't be replaced by the square bracket）
                start_index = matchObj.end()
                continue
            if "/" in old:
                new = "】" if isCHS else "]"
            else:
                new = "【" if isCHS else "["
            result = result.replace(old, new)
        result = result.strip()
        while result.startswith("<br>"):
            result = result.lstrip("<br>")
        while result.endswith("<br>"):
            result = result.rstrip("<br>")
        return result

    @classmethod
    def tooltipPostProcessing(cls, tooltip: str, isCHS: bool = False) -> str: #说明文本后处理（Tooltip post-processing）
        '''
        在tooltipPreparation方法后执行，对文本进行排版优化。<br>Executed after `tooltipPreparation` method, to optimize the tooltip layout.
        
        :param tooltip: 预处理后的说明文本。<br>Tooltip after running `tooltipPreparation` method.
        :type tooltip: str
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :return: 排版优化后的说明文本。<br>Tooltip after layout optimization.
        :rtype: str
        '''
        result: str = tooltip.replace("<row>", "").replace("</row>", "") #只有云顶之弈羁绊说明文本中存在<row>标签（<row> tag only exists in a TFT trait tooltip）
        if isCHS:
            while "【\n" in result:
                result = result.replace("【\n", "【")
            while "\n】" in result:
                result = result.replace("\n】", "】")
            while result.startswith("【【") and result.endswith("】】"): #在装备升级类强化符文中出现。下同（Appears in Upgrade-item augments. So does the following）
                result = result.replace("【【", "【").replace("】】", "】")
            while "【】" in result:
                result = result.replace("【】", "")
        else:
            while "[\n" in result:
                result = result.replace("[\n", "[")
            while "\n]" in result:
                result = result.replace("\n]", "]")
            while result.startswith("[[") and result.endswith("]]"): #在装备升级类强化符文中出现。下同（Appears in Upgrade-item augments. So does the following）
                result = result.replace("[[", "[").replace("]]", "]")
            while "[]" in result:
                result = result.replace("[]", "")
        while "()" in result:
            result = result.replace("()", "")
        result = result.strip()
        return result

    @classmethod
    def tooltipTransform(cls, tooltip: str, strtable_locale: dict[str, int | dict[str, str]], binData: dict[str, Any], isCHS: bool = False, enableModeOverride: bool = True, reserve_variable: bool = False, flexibleData: Optional[dict[str, dict[str, Any] | Any]] = None) -> str: #将原始提示转化为带数值的提示（Transform the raw tooltip into the one with detailed stats）
        '''
        将原始说明文本进行排版优化，并转换为带具体数值的说明文本。<br>Optimized the raw tooltip's layout and transform it into the one with detailed stats.
        
        :param tooltip: 原始说明文本。<br>Raw tooltip.
        :type tooltip: str
        :param strtable_locale: 字符串常量池。<br>Stringtable.
        :type strtable_locale: dict[str, int | dict[str, str]]
        :param binData: **原始**二进制描述数据。<br>**Raw** binary description data.
        :type binData: dict[str, Any]
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :param enableModeOverride: 是否启用模式覆盖。启用后，将统计某个变量在不同模式中的数值。默认为假。<br>Whether to enable mode overriden values. If enabled, values among different modes will be taken into consideration. False by default.
        :type enableModeOverride: bool
        :param reserve_variable: 是否将变量代换后的结果写成“[{变量名}] = {值}”的形式。默认为假。<br>Whether to write the result after variable substitution in the form of "[{Var_name}] = {Value}". False by default.
        :type reserve_variable: bool
        :param flexibleData: 附加数据。<br>Supplemental data.
        :type flexibleData: dict[str, dict[str, Any] | Any] | None
        :return: 转换后的说明文本。<br>Transformed tooltip.
        :rtype: str
        '''
        pFormat: re.Pattern[str] = re.compile(r"</?[\s\w=#\'\"@\-\.]*>")
        pSection: re.Pattern[str] = re.compile(r"<section>.*?</section>") #在星号后添加问号以启用贪婪模式（Enable greedy match by adding a question mark after the asterisk）
        layertags: set[str] = {"titleLeft", "titleRight", "subtitleLeft", "subtitleRight", "mainText", "postScriptTitle"}
        #预处理（Preparation）
        binData = cls.normalizeBinData(binData)
        #分节（Divide into sections）
        tooltip_tmp: str = tooltip
        tooltip_layers: list[tuple[str, str]] = [] #将详细信息按照第一层级分为几个部分。一般包括titleLeft、titleRight、subtitleLeft、subtitleRight、mainText和postScriptTitle等几个部分（Divide the details into several parts according to the first layer, basically including titleLeft, titleRight, subtitleLeft, subtitleRight, mainText, postScriptTitle, etc.）
        if any(i in tooltip_tmp for i in layertags):
            while len(tooltip_tmp) > 0:
                if not (matchObj := pFormat.search(tooltip_tmp)):
                    break
                first_layer_tag_start: str = matchObj.group()
                first_layer_tag_end: str = first_layer_tag_start[0] + "/" + first_layer_tag_start[1:]
                first_layer_tag_start_indices: list[int] = []
                first_layer_tag_end_indices: list[int] = []
                for match in re.finditer(first_layer_tag_start, tooltip_tmp):
                    first_layer_tag_start_indices.append(match.start())
                for match in re.finditer(first_layer_tag_end, tooltip_tmp):
                    first_layer_tag_end_indices.append(match.start())
                tag_index_dict: dict[int, int] = {}
                k: int = 0
                for k in first_layer_tag_start_indices:
                    tag_index_dict[k] = 1 #1代表新一层级的开始（1 represents the start of a new layer）
                for k in first_layer_tag_end_indices:
                    tag_index_dict[k] = -1 #-1代表当前层级的结束（-1 represents the end of the current layer）
                layer_tag_stack: int = 1 #通过栈来判断是否达到第一层级的结束开关（Judge by a stack whether the closing tag of the first layer is reached）
                for k in sorted(tag_index_dict.keys())[1:]:
                    layer_tag_stack += tag_index_dict[k]
                    if layer_tag_stack == 0:
                        break
                tooltip_layer: str = tooltip_tmp[:k + len(first_layer_tag_end)]
                tooltip_layers.append((first_layer_tag_start.replace("<", "").replace(">", ""), tooltip_layer))
                tooltip_tmp = tooltip_tmp[k + len(first_layer_tag_end):]
        else:
            tooltip_layers.append(("0", tooltip_tmp))
        tooltip_layers_text: list[tuple[str, str]] = []
        for (tag, tooltip_layer) in tooltip_layers:
            if pSection.search(tooltip_layer) == None:
                sections: list[str] = [tooltip_layer] #神话版本的装备数据中没有<section>和</section>标签。这里的处理方法是将整个层视为一节。由于列表长度是1，所以后续在合并成字符串时也不会出现节与节之间的分隔符（In mythic item versions, <section> and </section> tags weren't present. In that case, that whole layer is regarded as a section. Since the list size is 1, no delimiters will be added when this list is going to concatenate into a string）
            else:
                sections = pSection.findall(tooltip_layer)
            for sectionIndex in range(len(sections)):
                section: str = sections[sectionIndex]
                result = cls.tooltipStringtableIteration(section, strtable_locale, deep = False, binData = binData, isCHS = isCHS, enableModeOverride = False, reserve_variable = reserve_variable, reservedVarsList = None, flexibleData = flexibleData) #将双花括号包围的变量替换为实际说明文本（Replace the variables enclosed in two pairs of curly brackets with the actual tooltips）
                result = cls.tooltipPreparation(result, isCHS = isCHS)
                #下面开始执行复杂的变量代换过程（In the following, a complex variable substitution is performed）
                result = cls.variableSubstitute(result, binData, isCHS = isCHS, enableModeOverride = enableModeOverride, reserve_variable = reserve_variable, reservedVars = None, flexibleData = flexibleData)
                while True:
                    result1, gameModeReservedVars_list = cls.nestedVariableSubstitute(result, strtable_locale, binData, isCHS = isCHS, enableModeOverride = enableModeOverride)
                    if result1 == result: #该条件成立，相当于在上一次执行tooltipStringtableIteration后，不会产生进一步的嵌套变量（If this condition holds, it means that after the last execution of `tooltipStringtableIteration`, no further nested variables will be produced）
                        break
                    result = result1
                    result = cls.tooltipStringtableIteration(result, strtable_locale, deep = True, binData = binData, isCHS = isCHS, enableModeOverride = enableModeOverride, reserve_variable = reserve_variable, reservedVarsList = gameModeReservedVars_list, flexibleData = flexibleData) #因为一个reservedVars产生的闹剧。这是程序员的问题。你可以尝试转换一下spell_ornnp_tooltipextended键的说明文本（A farce due to `reservedVars`. Thanks to the programmer however. Try transforming the tooltip of `spell_ornnp_tooltipextended` key）
                result = cls.tooltipStringtableIteration(result, strtable_locale, deep = True, binData = binData, isCHS = isCHS, enableModeOverride = enableModeOverride, reserve_variable = reserve_variable, reservedVarsList = gameModeReservedVars_list, flexibleData = flexibleData) #在退出以上循环后，需要再次转换说明文本中新产生的变量（After exiting the above loop, it's necessary to transform the newly produced variables in the tooltip）
                #后处理（Post-processing）
                result = cls.tooltipPostProcessing(result, isCHS = isCHS)
                sections[sectionIndex] = result
            while "" in sections:
                sections.remove("")
            if tag in {"titleLeft", "titleRight", "subtitleLeft", "subtitleRight"}:
                tooltip_layer_text: str = " - ".join(sections)
            else:
                tooltip_layer_text = "\n----\n".join(sections)
            tooltip_layers_text.append((tag, tooltip_layer_text))
        if len(tooltip_layers_text) > 1:
            tooltip_text: str = ""
            i: int = 0
            for i in range(len(tooltip_layers_text) - 1):
                tag: str = tooltip_layers_text[i][0]
                tag_next: str = tooltip_layers_text[i + 1][0]
                tooltip_layer_text = tooltip_layers_text[i][1]
                if tag == "titleLeft" and tag_next == "titleRight" or tag == "subtitleLeft" and tag_next == "subtitleRight":
                    tooltip_text += tooltip_layer_text + " | "
                elif tag in {"titleLeft", "titleRight", "subtitleLeft", "subtitleRight"} and tag_next == "mainText" or tag == "mainText" and tag_next in {"postScriptTitle", "postScriptLeft"}:
                    tooltip_text += tooltip_layer_text + "\n--------\n"
                else:
                    tooltip_text += tooltip_layer_text + "\n"
            tooltip_text += tooltip_layers_text[i + 1][1]
        else:
            tooltip_text = tooltip_layers_text[0][1]
        return tooltip_text
    
    @classmethod
    def tooltipSubstitute(cls, tooltip: str, strtable_locale: dict[str, int | dict[str, str]], binData: dict[str, Any], isCHS: bool = False, enableModeOverride: bool = True, reserve_variable: bool = False, flexibleData: Optional[dict[str, dict[str, Any] | Any]] = None) -> str: #在最大程度保留原始说明文本格式的基础上，只进行变量代换（On the basis of maximizing the retention of the original tooltip format, only perform variable substitution）
        '''
        在保留原始说明文本中的CSS标签和修饰符的基础上，只进行变量代换。<br>Perform variable substitution only. The original CSS tags and descriptors in the tooltip are retained.
        
        :param tooltip: 原始说明文本。<br>Raw tooltip.
        :type tooltip: str
        :param strtable_locale: 字符串常量池。<br>Stringtable.
        :type strtable_locale: dict[str, int | dict[str, str]]
        :param binData: **原始**二进制描述数据。<br>**Raw** binary description data.
        :type binData: dict[str, Any]
        :param isCHS: 是否使用简体中文标点符号。默认为假。<br>Whether to use punctuation marks in Chinese Simplified. False by default.
        :type isCHS: bool
        :param enableModeOverride: 是否启用模式覆盖。启用后，将统计某个变量在不同模式中的数值。默认为假。<br>Whether to enable mode overriden values. If enabled, values among different modes will be taken into consideration. False by default.
        :type enableModeOverride: bool
        :param reserve_variable: 是否将变量代换后的结果写成“[{变量名}] = {值}”的形式。默认为假。<br>Whether to write the result after variable substitution in the form of "[{Var_name}] = {Value}". False by default.
        :type reserve_variable: bool
        :param flexibleData: 附加数据。<br>Supplemental data.
        :type flexibleData: dict[str, dict[str, Any] | Any] | None
        :return: 变量代换后的说明文本。<br>Tooltip after variable substitution.
        :rtype: str
        '''
        #预处理（Preparation）
        binData = cls.normalizeBinData(binData)
        result = cls.tooltipStringtableIteration(tooltip, strtable_locale, deep = False, reserve_CSS = True, binData = binData, isCHS = isCHS, enableModeOverride = False, reserve_variable = reserve_variable, reservedVarsList = None, flexibleData = flexibleData)
        #变量代换（Variable substitution）
        result = cls.variableSubstitute(result, binData, isCHS = isCHS, enableModeOverride = enableModeOverride, reserve_variable = reserve_variable, reservedVars = None, flexibleData = flexibleData)
        while True:
            result1, gameModeReservedVars_list = cls.nestedVariableSubstitute(result, strtable_locale, binData, isCHS = isCHS, enableModeOverride = enableModeOverride)
            if result1 == result: #该条件成立，相当于在上一次执行tooltipStringtableIteration后，不会产生进一步的嵌套变量（If this condition holds, it means that after the last execution of `tooltipStringtableIteration`, no further nested variables will be produced）
                break
            result = result1
            result = cls.tooltipStringtableIteration(result, strtable_locale, deep = True, reserve_CSS = True, binData = binData, isCHS = isCHS, enableModeOverride = enableModeOverride, reserve_variable = reserve_variable, reservedVarsList = gameModeReservedVars_list, flexibleData = flexibleData)
        result = cls.tooltipStringtableIteration(result, strtable_locale, deep = True, reserve_CSS = True, binData = binData, isCHS = isCHS, enableModeOverride = enableModeOverride, reserve_variable = reserve_variable, reservedVarsList = gameModeReservedVars_list, flexibleData = flexibleData)
        return result

    def set_tooltipTransform_strategy(self, reserve_CSS: bool = True) -> bool: #确定说明文本转换策略（Determine tooltip transformation strategy）
        '''
        决定转换说明文本时是否保持原样式。<br>Determine whether to retain the original style in the raw tooltips.

        :param reserve_CSS: 是否保留CSS样式。<br>Whether to retain CSS styles.
        :type reserve_CSS: bool
        :return: 是否优化说明文本布局。<br>Whether to optimize the tooltip layout.
        :rtype: bool
        '''
        self.optimize_tooltip_layout = not reserve_CSS
        if reserve_CSS:
            self.tooltipConvert = self.__class__.tooltipSubstitute
        else:
            self.tooltipConvert = self.__class__.tooltipTransform
        return self.optimize_tooltip_layout

class MapExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个地图提取器对象。<br>Initialize a MapExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        #self.extractor: LoLDataExtractor = extractor #主要应用于子类对象调用和修改父类对象的属性（Mainly designed for a child object to call and modify the attribute of a parent object）
        self.maps_ready: dict[int, bool] = {mapId: False for mapId in [11, 12, 21, 22, 30, 33, 35]}
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
        '''
        logPrint = self.log.logPrint
        #召唤师峡谷（Summoner's Rift）
        map11_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map11/map11.bin.json"
        if map11_bin_url in self.__class__.data_cache["online"]:
            self.map11_bin = self.__class__.data_cache["online"][map11_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map11_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("召唤师峡谷地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nSummoner's Rift map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map11_bin_url))
                    self.map11_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("召唤师峡谷地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nSummoner's Rift map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map11_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map11_bin_url] = self.map11_bin #在对一个MapExtractor对象的data_cache进行修改时，由于字典的引用传递，其父LoLDataExtractor对象的data_cache会同步此更改（While modifying `data_cache` of a MapExtractor object, due to the pass-by-reference of a dictionary, the modification will be synchronized in `data_cache` of its parent `LoLDataExtractor` object）
        self.maps_ready[11] = True
        #嚎哭深渊（Howling Abyss）
        map12_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map12/map12.bin.json"
        if map12_bin_url in self.__class__.data_cache["online"]:
            self.map12_bin = self.__class__.data_cache["online"][map12_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map12_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("嚎哭深渊地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nHowling Abyss map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map12_bin_url))
                    self.map12_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("嚎哭深渊地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nHowling Abyss map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map12_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map12_bin_url] = self.map12_bin
        self.maps_ready[12] = True
        #百合与莲花的神庙（Temple of Lily and Lotus）
        map21_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map21/map21.bin.json"
        if map21_bin_url in self.__class__.data_cache["online"]:
            self.map21_bin = self.__class__.data_cache["online"][map21_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map21_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("百合与莲花的神庙地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nTemple of Lily and Lotus map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map21_bin_url))
                    self.map21_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("百合与莲花的神庙地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nTemple of Lily and Lotus map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map21_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map21_bin_url] = self.map21_bin
        self.maps_ready[21] = True
        #聚点危机（Convergence）
        map22_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map22/map22.bin.json"
        if map22_bin_url in self.__class__.data_cache["online"]:
            self.map22_bin = self.__class__.data_cache["online"][map22_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map22_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("聚点危机地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nConvergence map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map22_bin_url))
                    self.map22_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("聚点危机地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nConvergence map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map22_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map22_bin_url] = self.map22_bin
        self.maps_ready[22] = True
        #怒火角斗场（Rings of Wrath）
        map30_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map30/map30.bin.json"
        if map30_bin_url in self.__class__.data_cache["online"]:
            self.map30_bin = self.__class__.data_cache["online"][map30_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map30_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("怒火角斗场地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nRings of Wrath map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map30_bin_url))
                    self.map30_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("怒火角斗场地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map30_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map30_bin_url] = self.map30_bin
        self.maps_ready[30] = True
        #最终都市（Final City）
        map33_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map33/map33.bin.json"
        if map33_bin_url in self.__class__.data_cache["online"]:
            self.map33_bin = self.__class__.data_cache["online"][map33_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map33_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("最终都市地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nFinal City map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map33_bin_url))
                    self.map33_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("最终都市地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nFinal City map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map33_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map33_bin_url] = self.map33_bin
        self.maps_ready[33] = True
        #班德尔之森（The Bandlewood）
        map35_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map35/map35.bin.json"
        if map35_bin_url in self.__class__.data_cache["online"]:
            self.map35_bin = self.__class__.data_cache["online"][map35_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map35_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("班德尔之森地图信息获取失败！请检查以下链接的可用性。程序将跳过该地图。\nThe Bandlewoods map data capture failure! Please check the URL availability. The program will skip this map.\n%s" %(map35_bin_url))
                    self.map35_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("班德尔之森地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nThe Bandlewoods map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map35_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map35_bin_url] = self.map35_bin
        self.maps_ready[35] = True
    
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
            self.map11_bin = self.__class__.data_cache["local"][map11_bin_path]
        else:
            with open(map11_bin_path, "r", encoding = "utf-8") as fp:
                self.map11_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map11_bin_path] = self.map11_bin
        self.maps_ready[11] = True
        #嚎哭深渊（Howling Abyss）
        map12_bin_path: str = paths[1]
        if map12_bin_path in self.__class__.data_cache["local"]:
            self.map12_bin = self.__class__.data_cache["local"][map12_bin_path]
        else:
            with open(map12_bin_path, "r", encoding = "utf-8") as fp:
                self.map12_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map12_bin_path] = self.map12_bin
        self.maps_ready[12] = True
        #百合与莲花的神庙（Temple of Lily and Lotus）
        map21_bin_path: str = paths[2]
        if map21_bin_path in self.__class__.data_cache["local"]:
            self.map21_bin = self.__class__.data_cache["local"][map21_bin_path]
        else:
            with open(map21_bin_path, "r", encoding = "utf-8") as fp:
                self.map21_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map21_bin_path] = self.map21_bin
        self.maps_ready[21] = True
        #聚点危机（Convergence）
        map22_bin_path: str = paths[3]
        if map22_bin_path in self.__class__.data_cache["local"]:
            self.map22_bin = self.__class__.data_cache["local"][map22_bin_path]
        else:
            with open(map22_bin_path, "r", encoding = "utf-8") as fp:
                self.map22_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map22_bin_path] = self.map22_bin
        self.maps_ready[22] = True
        #怒火角斗场（Rings of Wrath）
        map30_bin_path: str = paths[4]
        if map30_bin_path in self.__class__.data_cache["local"]:
            self.map30_bin = self.__class__.data_cache["local"][map30_bin_path]
        else:
            with open(map30_bin_path, "r", encoding = "utf-8") as fp:
                self.map30_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map30_bin_path] = self.map30_bin
        self.maps_ready[30] = True
        #最终都市（Final City）
        map33_bin_path: str = paths[5]
        if map33_bin_path in self.__class__.data_cache["local"]:
            self.map33_bin = self.__class__.data_cache["local"][map33_bin_path]
        else:
            with open(map33_bin_path, "r", encoding = "utf-8") as fp:
                self.map33_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map33_bin_path] = self.map33_bin
        self.maps_ready[33] = True
        #班德尔之森（The Bandlewood）
        map35_bin_path: str = paths[6]
        if map35_bin_path in self.__class__.data_cache["local"]:
            self.map35_bin = self.__class__.data_cache["local"][map35_bin_path]
        else:
            with open(map35_bin_path, "r", encoding = "utf-8") as fp:
                self.map35_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map35_bin_path] = self.map35_bin
        self.maps_ready[35] = True
        
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
        # map_name_list: list[str] = ["召唤师峡谷", "随机地图", "百合与莲花的神庙", "聚点危机", "怒火角斗场", "最终都市", "班德尔之森"]
        # map_bin_list: list[dict[str, list[str] | dict[str, Any]]] = [map11_bin, map12_bin, map21_bin, map22_bin, map30_bin, map33_bin, map35_bin]
        # overlay_table, overlay_count_table, overlay_identical_table, overlay_difference_table = verifyDictHeterogeneity(map_bin_list)
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
        maps_bin: dict[str, list[str] | dict[str, Any]] = self.map11_bin | self.map21_bin | self.map22_bin | self.map30_bin | self.map33_bin | self.map35_bin | self.map12_bin

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
        map_df = map_df.transpose() #行列转置（Row-column transpose）
        self.map_df = map_df
        return 0
    
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
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} Map" if self.sheet_naming_fold else "地图（Map）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.map_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"地图数据已导出到{self.wbPath}。按回车键继续。\nMap data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

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
            self.cheats_bin = self.__class__.data_cache["online"][cheats_bin_url]
        else:
            source, status, self.session = requestUrl("GET", cheats_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == -1:
                    logPrint('作弊指令信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nCheat data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.')
                elif status == 404:
                    logPrint('作弊指令信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nCheat data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s' %(cheats_bin_url))
                time.sleep(3)
                self.init_data_readiness()
                return
            self.cheats_bin: dict[str, list[str] | dict[str, Any]] = source.json()
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
            self.cheats_bin = self.__class__.data_cache["local"][cheats_bin_path]
        else:
            with open(cheats_bin_path, "r", encoding = "utf-8") as fp:
                self.cheats_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
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
                                isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
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
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} CheatSet" if self.sheet_naming_fold else "指令集（CheatSet）"
        sheet2_name: str = f"{self.patch_number} Cheat" if self.sheet_naming_fold else "指令（Cheat）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.cheatset_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(self.cheat_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet2_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"作弊指令数据已导出到{self.wbPath}。按回车键继续。\nCheat data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

class PerkExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个符文提取器对象。<br>Initialize a CheatExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.perk_ready: bool = False
        self.perkstyle_df: pandas.DataFrame = pandas.DataFrame()
        self.perk_df: pandas.DataFrame = pandas.DataFrame()
        
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.perk_ready = False
    
    def get_perk_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取符文二进制描述数据。<br>Get binary description data of perks online.
        '''
        logPrint = self.log.logPrint
        perks_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/perks.cdtb.bin.json"
        if perks_bin_url in self.__class__.data_cache["online"]:
            self.perks_bin = self.__class__.data_cache["online"][perks_bin_url]
        else:
            source, status, self.session = requestUrl("GET", perks_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == -1:
                    logPrint("符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nPerk data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                elif status == 404:
                    logPrint("符文信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nPerk data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(perks_bin_url))
                time.sleep(3)
                self.init_data_readiness()
                return
            self.perks_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][perks_bin_url] = self.perks_bin
        self.perk_ready = True
    
    def read_perk_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取符文二进制描述数据。<br>Get binary description data of perks offline.
        
        :param path: 符文二进制描述文件的本地路径。<br>A local path of perk binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        perks_bin_path: str = path
        if perks_bin_path in self.__class__.data_cache["local"]:
            self.perks_bin = self.__class__.data_cache["local"][perks_bin_path]
        else:
            with open(perks_bin_path, "r", encoding = "utf-8") as fp:
                self.perks_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][perks_bin_path] = self.perks_bin
        self.perk_ready = True
    
    def build_perk_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建符文数据框。<br>Build perk dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 符文二进制描述文件的本地路径。<br>A local path of perk binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.perk_ready:
            #获取符文信息（Get perk information）
            logPrint("正在读取符文数据……\nReading perk data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_perk_data(path = path)
            else:
                self.get_perk_data()
            if not self.perk_ready:
                logPrint("符文数据尚未准备就绪！\nPerk data not prepared!")
                return 2
        
        #提取指令字典（Extract spell dictionary）
        self.init_mSpells()
        for (key, value) in self.perks_bin.items():
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        
        #构建从符文序号到符文数据的映射（Build a map from mPerkId to the corresponding perk data）
        perkstyleKey_perkstyleId_map: dict[int, str] = {}
        perkKey_perkId_map: dict[int, str] = {}
        for (key, value) in self.perks_bin.items():
            if key != "__linked" and value["__type"] == "PerkStyle":
                perkstyleKey_perkstyleId_map[value["mPerkStyleId"]] = key #已事先确定所有符文对象中都有mPerkStyleId键（Confirmed in advance that all Perk objects have `mPerkStyleId` key）
            elif key != "__linked" and value["__type"] == "Perk":
                perkKey_perkId_map[value["mPerkId"]] = key #已事先确定所有符文对象中都有mPerkId键（Confirmed in advance that all Perk objects have `mPerkId` key）
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建符文数据框……\nBuilding the perk dataframes ...", print_time = True)
        ##符文系（Perkstyle）
        perkstyle_header_keys: list[str] = list(perkstyle_header.keys())
        perkstyle_data: dict[str, list[Any]] = {key: [] for key in perkstyle_header_keys}
        perkstyle_data_json: dict[str, list[Any]] = copy.deepcopy(perkstyle_data)
        ##符文（Perk）
        perk_header_keys: list[str] = list(perk_header.keys())
        perk_data: dict[str, list[Any]] = {key: [] for key in perk_header_keys}
        perk_data_json: dict[str, list[Any]] = copy.deepcopy(perk_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.perks_bin.items():
            if key1 != "__linked" and value["__type"] == "PerkStyle":
                for i in range(len(perkstyle_header_keys)):
                    key: str = perkstyle_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 20:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i == 7: #高级符文系（`mIsAdvancedStyle`）
                                    to_append = False
                                else:
                                    to_append = ""
                                break
                        else:
                            to_append = tmp_ptr
                    elif i <= 26:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = value[subkey1] #此处代码写法和其它地方有些不同。它不是引用列表上次追加的数据，而是直接从原始数据中获取。这是因为符文系数据相对比较平衡，很多键基本上都是常驻的（Here the code style somehow differs from other places. It doesn't use the data recently appended to the list; instead, it obtains the raw data. This is because perkstyle data are relatively balanced; many keys aren't flexible）
                        to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                    elif i == 27 or i == 28: #可用副系名称（中文）和可用副系名称（英文）（`mAllowedSubStyles mDisplayNameLocalizationKey_contents_zh` and `mAllowedSubStyles mDisplayNameLocalizationKey_contents_en`）
                        strtable_locale = strtable_lol_target if i == 27 else strtable_lol_default
                        mAllowedSubStyleNames: list[str] = []
                        for substyleId in value["mAllowedSubStyles"]:
                            if substyleId in perkstyleKey_perkstyleId_map and perkstyleKey_perkstyleId_map[substyleId] in self.perks_bin:
                                mDisplayNameLocalizationKey: str = self.perks_bin[perkstyleKey_perkstyleId_map[substyleId]]["mDisplayNameLocalizationKey"]
                                mAllowedSubStyleNames.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                            else:
                                mAllowedSubStyleNames.append(substyleId)
                        to_append = mAllowedSubStyleNames
                    elif i == 29 or i == 30: #渲染插画时默认使用符文名称（中文）和渲染插画时默认使用符文名称（英文）（`mDefaultPerksWhenSplashed mDisplayNameLocalizationKey_contents_zh` and `mDefaultPerksWhenSplashed mDisplayNameLocalizationKey_contents_en`）
                        strtable_locale = strtable_lol_target if i == 29 else strtable_lol_default
                        mDefaultPerksWhenSplashed_names: list[str] = []
                        for perk_key in value["mDefaultPerksWhenSplashed"]:
                            if perk_key in self.perks_bin:
                                mDisplayNameLocalizationKey: str = self.perks_bin[perk_key]["mDisplayNameLocalizationKey"]
                                mDefaultPerksWhenSplashed_names.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                            else:
                                mDefaultPerksWhenSplashed_names.append(perk_key)
                        to_append = mDefaultPerksWhenSplashed_names
                    elif i <= 54: #搭配各副系时的默认属性符文子键（`mDefaultStatModsPerSubStyle`'s subkeys）
                        substyle_index: int = (i - 31) // 6
                        defaultStatMods: dict[str, int | list[str] | str] = value["mDefaultStatModsPerSubStyle"][substyle_index]
                        if (i - 31) % 6 <= 1: #副系序号和属性符文（`mStyleId` and `mPerks`）
                            subkey: str = key.split()[1]
                            to_append = defaultStatMods[subkey]
                        elif (i - 31) % 6 <= 3: #本地化副系名称（Localized substyle name）
                            substyleId = defaultStatMods["mStyleId"]
                            mDisplayNameLocalizationKey: str = self.perks_bin[perkstyleKey_perkstyleId_map[substyleId]]["mDisplayNameLocalizationKey"]
                            strtable_locale = strtable_lol_target if (i - 31) % 6 == 2 else strtable_lol_default
                            to_append = self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey)
                        else: #本地化属性符文名称（Localized stat mod names）
                            strtable_locale = strtable_lol_target if (i - 31) % 6 == 4 else strtable_lol_default
                            mPerks_names: list[str] = []
                            for perk_key in defaultStatMods["mPerks"]:
                                if perk_key in self.perks_bin:
                                    mDisplayNameLocalizationKey: str = self.perks_bin[perk_key]["mDisplayNameLocalizationKey"]
                                    mPerks_names.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                                else:
                                    mPerks_names.append(perk_key)
                            to_append = mPerks_names
                    elif i <= 82: #槽位子键（`mSlots`' subkeys）
                        slot_index: int = (i - 55) // 7
                        slot: dict[str, int | list[str] | str] = value["mSlots"][slot_index]
                        if (i - 55) % 7 <= 2: #标签键、类型和符文（`mSlotLabelKey`, `mType` and `mPerks`）
                            subkey: str = key.split()[1]
                            to_append = slot[subkey]
                        elif (i - 55) % 7 <= 4: #本地化标签（Localized label）
                            tooltip_key: str = slot["mSlotLabelKey"]
                            strtable_locale = strtable_lol_target if (i - 55) % 7 == 3 else strtable_lol_default
                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        else: #本地化符文名称（Localized perk names）
                            strtable_locale = strtable_lol_target if (i - 55) % 7 == 5 else strtable_lol_default
                            mPerks_names: list[str] = []
                            for perk_key in slot["mPerks"]:
                                if perk_key in self.perks_bin:
                                    mDisplayNameLocalizationKey: str = self.perks_bin[perk_key]["mDisplayNameLocalizationKey"]
                                    mPerks_names.append(self.get_strtable_value(strtable_locale, mDisplayNameLocalizationKey, default = mDisplayNameLocalizationKey))
                                else:
                                    mPerks_names.append(perk_key)
                            to_append = mPerks_names
                    else: #本地化槽位标签（Localized slot labels）
                        strtable_locale = strtable_lol_target if i == 83 else strtable_lol_default
                        slotNames: list[str] = []
                        for slot_key in value["mSlotlinks"]:
                            if slot_key in self.perks_bin:
                                tooltip_key: str = self.perks_bin[slot_key]["mSlotLabelKey"]
                                slotNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                            else:
                                slotNames.append(slot_key)
                        to_append = slotNames
                    perkstyle_data[key].append(to_append)
                    perkstyle_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "Perk":
                for i in range(len(perk_header_keys)):
                    key: str = perk_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append = key1
                    elif i <= 20:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i == 11 or i == 18: #可叠加和默认符文（`mStackable` and `mDefault`）
                                    to_append = False
                                elif i == 12: #可用性（`mEnabled`）
                                    to_append = True
                                else:
                                    to_append = ""
                                break
                        else:
                            to_append = tmp_ptr
                    elif i <= 36:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = perk_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            if "mScript" in value and "mSpellScriptData" in value["mScript"]:
                                mSpellScriptData = value["mScript"]["mSpellScriptData"]
                            else:
                                mSpellScriptData = None
                            if mSpellScriptData == None:
                                to_append = ""
                            else:
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpellScriptData, isCHS = isCHS, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    else: #本地化赛后结算描述（Localized `mEndOfGameStatDescriptions`）
                        if "mEndOfGameStatDescriptions" in value:
                            strtable_locale = strtable_lol_target if i == 37 else strtable_lol_default
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_locale, x, default = x), value["mEndOfGameStatDescriptions"]))
                        else:
                            to_append = ""
                    perk_data[key].append(to_append)
                    perk_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        perkstyle_statistics_output_order: list[int] = [0, 1, 2, 3, 21, 22, 7, 4, 23, 24, 8, 27, 28, 9, 16, 83, 84, 15, 55, 58, 59, 56, 57, 60, 61, 62, 65, 66, 63, 64, 67, 68, 69, 72, 73, 70, 71, 74, 75, 76, 79, 80, 77, 78, 81, 82, 14, 31, 33, 34, 32, 35, 36, 37, 39, 40, 38, 41, 42, 43, 45, 46, 44, 47, 48, 49, 51, 52, 50, 53, 54, 5, 25, 26, 13, 29, 30, 17, 18, 19, 6, 10, 11, 12, 20]
        perkstyle_data_organized: dict[str, list[Any]] = {perkstyle_header_keys[i]: perkstyle_data_json[perkstyle_header_keys[i]] for i in perkstyle_statistics_output_order}
        perkstyle_df: pandas.DataFrame = pandas.DataFrame(data = perkstyle_data_organized)
        perkstyle_df = perkstyle_df.sort_values(by = "mPerkStyleId", ascending = True, ignore_index = True)
        logPrint("正在优化符文系数据框的逻辑值显示……\nOptimizing boolean value display of the perkstyle dataframe ...")
        optimize_bool_display(perkstyle_df)
        perkstyle_df = pandas.concat([pandas.DataFrame([perkstyle_header])[perkstyle_df.columns], perkstyle_df], ignore_index = True)
        self.perkstyle_df = perkstyle_df
        perk_statistics_output_order: list[int] = [0, 1, 2, 3, 21, 22, 12, 11, 18, 4, 23, 25, 24, 26, 9, 5, 27, 28, 6, 29, 31, 30, 32, 7, 33, 35, 34, 36, 8, 37, 38, 17, 19, 13, 14, 15, 20, 10, 16]
        perk_data_organized: dict[str, list[Any]] = {perk_header_keys[i]: perk_data_json[perk_header_keys[i]] for i in perk_statistics_output_order}
        perk_df: pandas.DataFrame = pandas.DataFrame(data = perk_data_organized)
        perk_df = perk_df.sort_values(by = "mPerkId", ascending = True, ignore_index = True)
        logPrint("正在优化符文数据框的逻辑值显示……\nOptimizing boolean value display of the perk dataframe ...")
        optimize_bool_display(perk_df)
        perk_df = pandas.concat([pandas.DataFrame([perk_header])[perk_df.columns], perk_df], ignore_index = True)
        self.perk_df = perk_df
        return 0
    
    def export_perk_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出符文数据到工作簿中。产生以下工作表：<br>Export perk data to a workbook. The following worksheets are added:
        - 符文系（PerkStyles）
        - 符文（Perks）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 符文二进制描述文件的本地路径。<br>A local path of perk binary description file.
        
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
        if self.perkstyle_df.empty or self.perk_df.empty:
            status: int = self.build_perk_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} PerkStyles" if self.sheet_naming_fold else "符文系（PerkStyles）"
        sheet2_name: str = f"{self.patch_number} Perks" if self.sheet_naming_fold else "符文（Perks）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.perkstyle_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(self.perk_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet2_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"符文数据已导出到{self.wbPath}。按回车键继续。\nPerk data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

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
    
    def get_champion_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取英雄二进制描述数据。<br>Get binary description data of champions online.
        
        在`useAllCharacter`属性为真时，将获取所有角色的数据，否则只获取英雄的数据。<br>When the attribute `useAllCharacter` is True, all characters' data will be fetched, otherwise only champion data will be fetched.
        '''
        logPrint = self.log.logPrint
        if self.useAllCharacter:
            if "characters_bin_dict" in self.__class__.merged_data_cache:
                self.champions_bin_dict = self.__class__.merged_data_cache["characters_bin_dict"]
            else:
                if self.fileExportList_ready: #当文件导出列表就绪，直接从列表中筛选角色数据网址（When the file export list is ready, directly filter character data URLs from the list）
                    #整理角色列表（Sort out the characters into a list）
                    ##聚点危机地图（Convergence map）
                    map22_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map22/map22.bin.json" #云顶之弈的小小英雄和羁绊信息（TFT champion and trait data）
                    if map22_bin_url in self.__class__.data_cache["online"]:
                        self.map22_bin = self.__class__.data_cache["online"][map22_bin_url]
                    else:
                        source, status, self.session = requestUrl("GET", map22_bin_url, session = self.session, log = self.log)
                        if status != 200:
                            if status == 404:
                                logPrint("聚点危机地图信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nConvergence map data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(map22_bin_url))
                                self.map22_bin: dict[str, list[str] | dict[str, Any]] = {}
                            else:
                                logPrint("聚点危机地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nConvergence map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                                time.sleep(3)
                                self.init_data_readiness()
                                return
                        else:
                            self.map22_bin: dict[str, list[str] | dict[str, Any]] = source.json()
                        self.__class__.data_cache["online"][map22_bin_url] = self.map22_bin
                    self.characters_ready["map22"] = True
                    ##角色列表（Character list）
                    self.characters_ready["characterList1"] = True #在从文件导出列表中获取角色数据时，相当于角色列表已准备就绪（When the file export list is fetched, the character list must be ready）
                    self.characters_ready["characterList2"] = True
                    logPrint("正在整理角色列表……\nSorting out characters into a list ...", print_time = True)
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
                    logPrint("正在读取各角色数据……\nReading all character data ...", print_time = True)
                    characterNames = list(character_binary_urls1.keys())
                    for i in range(len(characterNames)):
                        characterName = characterNames[i]
                        # logPrint("[%d/%d]正在加载角色%s的信息…… | Loading character %s%s information ..." %(i + 1, len(characterNames), characterName, characterName, "s'" if characterName.endswith("s") else "'s"), print_time = True)
                        character_binary_url: str = character_binary_urls1[characterName]
                        if character_binary_url in self.__class__.data_cache["online"]:
                            character_binary = self.__class__.data_cache["online"][character_binary_url]
                        else:
                            source, status, self.session = requestUrl("GET", character_binary_url, session = self.session, log = self.log)
                            if status != 200:
                                if status == 404:
                                    logPrint(f"未找到角色{characterName}的信息。程序将跳过该角色。\nCharacter {characterName} data not found. The program will skip this character.")
                                    continue
                                elif status == -1:
                                    logPrint("角色信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                                    time.sleep(3)
                                self.init_data_readiness()
                                return
                            character_binary: dict[str, list[str] | dict[str, Any]] = source.json()
                            self.__class__.data_cache["online"][character_binary_url] = character_binary
                        self.champions_bin_dict[characterName] = character_binary
                        logPrint("[%d/%d]已加载角色（Character loaded）：%s" %(i + 1, len(characterNames), characterName), print_time = True)
                    else:
                        self.__class__.merged_data_cache["characters_bin_dict"] = self.champions_bin_dict
                else: #当文件导出列表尚未准备就绪时，从两个指定文件夹中获取角色数据（When the file export list isn't ready yet, get character data from two specified folders）
                    #整理角色列表（Sort out the characters into a list）
                    logPrint("正在整理角色列表……\nSorting out characters into a list ...", print_time = True)
                    ##聚点危机地图（Convergence map）
                    map22_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map22/map22.bin.json" #云顶之弈的小小英雄和羁绊信息（TFT champion and trait data）
                    if map22_bin_url in self.__class__.data_cache["online"]:
                        self.map22_bin = self.__class__.data_cache["online"][map22_bin_url]
                    else:
                        source, status, self.session = requestUrl("GET", map22_bin_url, session = self.session, log = self.log)
                        if status != 200:
                            if status == 404:
                                logPrint("聚点危机地图信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nConvergence map data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(map22_bin_url))
                                self.map22_bin: dict[str, list[str] | dict[str, Any]] = {}
                            else:
                                logPrint("聚点危机地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nConvergence map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                                time.sleep(3)
                                self.init_data_readiness()
                                return
                        else:
                            self.map22_bin: dict[str, list[str] | dict[str, Any]] = source.json()
                        self.__class__.data_cache["online"][map22_bin_url] = self.map22_bin
                    self.characters_ready["map22"] = True
                    ##角色文件夹（Character folders）
                    characterList_url1: str = f"https://raw.communitydragon.org/json/{self.version}/game/data/characters/"
                    if characterList_url1 in self.__class__.data_cache["online"]:
                        characterList1 = self.__class__.data_cache["online"][characterList_url1]
                    else:
                        source, status, self.session = requestUrl("GET", characterList_url1, session = self.session, log = self.log)
                        if status != 200:
                            if status == -1:
                                logPrint("第一批角色列表获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nCharacter List 1 capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                            elif status == 404:
                                logPrint("第一批角色列表获取失败！请检查以下链接的可用性。程序即将返回上一层。\nCharacter List 1 capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(characterList_url1))
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
                            if status == -1:
                                logPrint("第二批角色列表获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nCharacter List 2 capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                            elif status == 404:
                                logPrint("第二批角色列表获取失败！请检查以下链接的可用性。程序即将返回上一层。\nCharacter List 2 capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(characterList_url2))
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
                    logPrint("正在读取各角色数据……\nReading all character data ...", print_time = True)
                    characterNames = list(character_binary_urls2.keys())
                    for i in range(len(characterNames)):
                        characterName = characterNames[i]
                        logPrint("[%d/%d]正在加载角色%s的信息…… | Loading character %s%s information ..." %(i + 1, len(characterNames), characterName, characterName, "s'" if characterName.endswith("s") else "'s"), print_time = True)
                        character_bin_urls: list[str] = character_binary_urls2[characterName]
                        for j in range(len(character_bin_urls)):
                            character_binary_url = character_bin_urls[j]
                            if character_binary_url in self.__class__.data_cache["online"]:
                                character_binary = self.__class__.data_cache["online"][character_binary_url]
                            else:
                                logPrint("[%d/%d][%d/%d]正在加载链接（Fetching url）： %s" %(i + 1, len(characterNames), j + 1, len(character_bin_urls), character_binary_url), write_time = False)
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
                                            logPrint("角色信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                                            time.sleep(3)
                                        self.init_data_readiness()
                                        return
                                character_binary: dict[str, list[str] | dict[str, Any]] = source.json()
                                self.__class__.data_cache["online"][character_binary_url] = character_binary
                            self.champions_bin_dict[characterName] = character_binary
                            # logPrint("[%d/%d]已加载角色（Character loaded）：%s" %(i + 1, len(characterNames), characterName), print_time = True)
                            break
                    else:
                        self.__class__.merged_data_cache["characters_bin_dict"] = self.champions_bin_dict
            self.characters_ready["character_binary"] = True #所有角色的二进制描述数据准备就绪后，执行该语句（After all characters' binary description data are prepared, execute this statement）
        else:
            if "champions_bin_dict" in self.__class__.merged_data_cache:
                self.champions_bin_dict = self.__class__.merged_data_cache["champions_bin_dict"]
            else:
                #获取所有英雄的名称信息（Get all champions' name information）
                logPrint("正在读取英雄元数据……\nReading champion metadata ...", print_time = True)
                champion_summary_url: str = "https://raw.communitydragon.org/%s/plugins/rcp-be-lol-game-data/global/%s/v1/champion-summary.json" %(self.version, self.language_folder)
                if champion_summary_url in self.__class__.data_cache["online"]:
                    champion_summary = self.__class__.data_cache["online"][champion_summary_url]
                else:
                    source, status, self.session = requestUrl("GET", champion_summary_url, session = self.session, log = self.log)
                    if status != 200:
                        if status == -1:
                            logPrint("英雄概要信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion summary data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                        elif status == 404:
                            logPrint("英雄概要信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nChampion summary data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(champion_summary_url))
                        time.sleep(3)
                        self.init_data_readiness()
                        return
                    champion_summary: list[dict[str, int | str | list[str]]] = source.json()
                    self.__class__.data_cache["online"][champion_summary_url] = champion_summary
                self.champions_ready["summary"] = True
                #读取所有英雄的二进制描述数据（Load all champions' binary description data）
                logPrint("正在读取各英雄数据……\nReading all champion data ...", print_time = True)
                for i in range(len(champion_summary)):
                    champion = champion_summary[i]
                    alias: str = champion["alias"].lower()
                    if alias == "none":
                        logPrint("[%d/%d]已跳过英雄（Champion skipped）：%s" %(i + 1, len(champion_summary), champion["alias"]), print_time = True)
                    else:
                        champion_binary_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/characters/{alias}/{alias}.bin.json"
                        if champion_binary_url in self.__class__.data_cache["online"]:
                            champion_binary = self.__class__.data_cache["online"][champion_binary_url]
                        else:
                            source, status, self.session = requestUrl("GET", champion_binary_url, session = self.session, log = self.log)
                            if status != 200:
                                if status == -1:
                                    logPrint("英雄信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nChampion data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                                elif status == 404:
                                    logPrint("英雄信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nChampion data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(champion_binary_url))
                                time.sleep(3)
                                self.init_data_readiness()
                                break
                            champion_binary: dict[str, list[str] | dict[str, Any]] = source.json()
                            self.__class__.data_cache["online"][champion_binary_url] = champion_binary
                        self.champions_bin_dict[champion["alias"]] = champion_binary
                        logPrint("[%d/%d]已加载英雄（Champion loaded）：%s" %(i + 1, len(champion_summary), champion["alias"]), print_time = True)
                else:
                    self.__class__.merged_data_cache["champions_bin_dict"] = self.champions_bin_dict
            self.champions_ready["champion_binary"] = True #所有英雄的二进制描述数据准备就绪后，执行该语句（After all champions' binary description data are prepared, execute this statement）
    
    def read_champion_data(self, useAllCharacter: bool = False, paths: Optional[list[str]] = None) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取英雄二进制描述数据。<br>Get binary description data of champions offline.
        
        :param useAllCharacter: 是否导出所有角色数据。默认为假。<br>Whether to export data of all characters. False by default.
        :type useAllCharacter: bool
        :param paths: 当使用所有角色数据时，`paths`由以下部分组成：<br>When all characters' data are used, `paths` is a list composed of the following content:
        
            - 聚点危机地图二进制描述文件路径（Convergence map binary description file path）
            - 角色文件夹1路径（Character folder 1 path）： game/data/characters
            - 角色文件夹2路径（Character folder 2 path）： game/characters
            
            当仅使用英雄数据时，`paths`由以下部分组成：<br>When only champions' data are used, `paths` is a list composed of the following content:
            - 英雄概要文件路径（Champion summary file path）
            - 角色文件夹路径（Character folder path）： game/data/characters
        :type paths: list[str]
        '''
        logPrint = self.log.logPrint
        if paths == None:
            logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
            return
        if useAllCharacter:
            if paths[0] in self.__class__.data_cache["local"] and "characters_bin_dict" in self.__class__.merged_data_cache:
                self.map22_bin = self.__class__.data_cache["local"][paths[0]]
                self.characters_ready["map22"] = True #当目的变量准备就绪时，应标记中间变量准备就绪（When the target variable is prepared, the intermediate variables should also be marked as prepared）
                self.characters_ready["characterList1"] = True
                self.characters_ready["characterList2"] = True
                self.champions_bin_dict = self.__class__.merged_data_cache["characters_bin_dict"]
            else:
                #整理角色列表（Sort out the characters into a list）
                ##聚点危机地图（Convergence map）
                map22_bin_path: str = paths[0]
                if map22_bin_path in self.__class__.data_cache["local"]:
                    self.map22_bin = self.__class__.data_cache["local"][map22_bin_path]
                else:
                    if os.path.exists(map22_bin_path):
                        with open(map22_bin_path, "r", encoding = "utf-8") as fp:
                            self.map22_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
                        self.__class__.data_cache["local"][map22_bin_path] = self.map22_bin
                    else:
                        self.map22_bin: dict[str, list[str] | dict[str, Any]] = {} #早期没有云顶之弈模式（In early days, TFT wasn't invented）
                self.characters_ready["map22"] = True
                ##角色文件夹（Character folders）
                characterList_folder1: str = paths[1]
                characterList_folder2: str = paths[2]
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
                    logPrint("[%d/%d]正在加载角色%s的信息……\nLoading character %s%s information ..." %(i + 1, len(characterNames), characterName, characterName, "s'" if characterName.endswith("s") else "'s"), print_time = True)
                    character_bin_paths: list[str] = character_binary_paths[characterName]
                    for j in range(len(character_bin_paths)):
                        character_binary_path = character_bin_paths[j]
                        if character_binary_path in self.__class__.data_cache["local"]:
                            character_binary = self.__class__.data_cache["local"][character_binary_path]
                            self.champions_bin_dict[characterName] = character_binary
                            break
                        else:
                            try:
                                with open(character_binary_path, "r", encoding = "utf-8") as fp:
                                    character_binary: dict[str, list[str] | dict[str, Any]] = json.load(fp)
                            except json.decoder.JSONDecodeError:
                                if len(character_bin_paths) > 1 and j < len(character_bin_paths) - 1: #正常情况下，每个characterName应只对应一个本地路径。此部分只是为了效仿在线加载部分的代码，并且以防万一（Normally, each `characterName` corresponds to one local path. This part is only designed to fit the code style in online loading part, plus just in case a format mistake would happen）
                                    logPrint("本地文件格式不正确。程序将使用备用地址。\nLocal file format invalid! The program will use another path.")
                                else:
                                    logPrint("本地文件格式不正确。程序将跳过该文件。\nLocal file format invalid! The program will skip this file.")
                                continue
                            else:
                                self.__class__.data_cache["local"][character_binary_path] = character_binary
                                self.champions_bin_dict[characterName] = character_binary
                                break
                else:
                    self.__class__.merged_data_cache["characters_bin_dict"] = self.champions_bin_dict
            self.characters_ready["character_binary"] = True
        else:
            if "champions_bin_dict" in self.__class__.merged_data_cache:
                self.champions_ready["summary"] = True
                self.champions_bin_dict = self.__class__.merged_data_cache["champions_bin_dict"]
            else:
                #获取所有英雄的名称信息（Get all champions' name information）
                champion_summary_path = paths[0]
                if champion_summary_path in self.__class__.data_cache["local"]:
                    champion_summary = self.__class__.data_cache["local"][champion_summary_path]
                else:
                    with open(champion_summary_path, "r", encoding = "utf-8") as fp:
                        champion_summary: list[dict[str, int | str | list[str]]] = json.load(fp)
                    self.__class__.data_cache["local"][champion_summary_path] = champion_summary
                self.champions_ready["summary"] = True
                #读取所有英雄的二进制描述数据（Load all champions' binary description data）
                for i in range(len(champion_summary)):
                    champion = champion_summary[i]
                    alias: str = champion["alias"].lower()
                    if alias == "none":
                        # logPrint("[%d/%d]已跳过英雄（Champion skipped）：%s" %(i + 1, len(champion_summary), champion["alias"]), print_time = True)
                        pass
                    else:
                        champion_binary_path: str = os.path.join(paths[1], f"{alias}/{alias}.bin.json").replace("\\", "/")
                        if champion_binary_path in self.__class__.data_cache["local"]:
                            champion_binary = self.__class__.data_cache["local"][champion_binary_path]
                        else:
                            with open(champion_binary_path, "r", encoding = "utf-8") as fp:
                                champion_binary: dict[str, list[str] | dict[str, Any]] = json.load(fp)
                            self.__class__.data_cache["local"][champion_binary_path] = champion_binary
                        self.champions_bin_dict[champion["alias"]] = champion_binary
                        # logPrint("[%d/%d]已加载英雄（Champion loaded）：%s" %(i + 1, len(champion_summary), champion["alias"]), print_time = True)
                else:
                    self.__class__.merged_data_cache["champions_bin_dict"] = self.champions_bin_dict
            self.champions_ready["champion_binary"] = True
    
    def build_champion_dataframe(self, useAllCharacter: Optional[bool] = None, debug: bool = False, paths: Optional[list[str]] = None) -> int:
        '''
        构建英雄数据框。<br>Build champion dataframe.
        
        :param useAllCharacter: 是否导出所有角色数据。如果未指定，则使用对象的属性值。<br>Whether to export data of all characters. If unspecified, it'll use the attribute value of the object.
        :type useAllCharacter: bool
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
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if useAllCharacter == None:
            useAllCharacter = self.useAllCharacter
        if useAllCharacter and not self.characters_ready["character_binary"] or not useAllCharacter and not self.champions_ready["champion_binary"]:
            if useAllCharacter:
                logPrint("正在读取角色数据……\nReading character data ...", print_time = True)
            else:
                logPrint("正在读取英雄数据……\nReading champion data ...", print_time = True)
            #获取英雄/角色信息（Get champion / character information）
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_champion_data(useAllCharacter = useAllCharacter, paths = paths)
            else:
                self.get_champion_data()
            if useAllCharacter and not self.characters_ready["character_binary"]:
                logPrint("角色数据尚未准备就绪！\nCharacter data not prepared!")
                return 2
            if not useAllCharacter and not self.champions_ready["champion_binary"]:
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
        rootSpell_ability_map: dict[str, dict[str, Any]] = {}
        for (key, value) in champions_bin.items():
            if key != "__linked" and value["__type"] == "AbilityObject":
                rootSpell_ability_map[value["mRootSpell"]] = value
        # logPrint("已构建基本指令到技能的映射关系。\nFinished building the map from root spells to abilities.")
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        strtable_tft_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.tftstringtable_target
        strtable_tft_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
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
                            if i == 118:
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
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            tooltip_key: str = champion_data[subkey1][-1] #通过访问最近一次追加的数据来优化代码。代价是键必须放在值的前面（Optimize the code by accessing the recently appended data. In turn, the key must be put in front of the value）
                            if (i == 133 or i == 134) and tooltip_key == "": #不存在显示名键的情况下，尝试通过一定的模式来确定显示名（When `name` key isn't present, try determining the displayName by certain pattern）
                                if "mCharacterName" in value:
                                    tooltip_key: str = "displayName_" + value["mCharacterName"]
                                else:
                                    tooltip_key = ""
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            if i == 127 or i == 128: #被动技能说明文本（中文/数值转换）和被动技能说明文本（英文/数值转换）（`passiveToolTip_content_zh_burn` and `passiveToolTip_content_en_burn`）
                                if "mCharacterPassiveSpell" in value:
                                    spellKey = value["mCharacterPassiveSpell"]
                                    mSpell = champions_bin[spellKey].get("mSpell")
                                    if mSpell == None:
                                        to_append = ""
                                    else:
                                        self.__class__.calculatedVariables.clear()
                                        tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                        to_append = tooltip_burn
                                else:
                                    to_append = ""
                            else:
                                to_append = tooltip_raw
                        elif i == 137 or i == 138: #技能本地化名称（Spell name localization）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            if "spells" in value:
                                spellNames: list[str] = []
                                for spell_key in value["spells"]:
                                    tmp_ptr = champions_bin
                                    for tmp_key in [spell_key, "mSpell", "mClientData", "mTooltipData", "mLocKeys", "keyName"]:
                                        if tmp_key in tmp_ptr:
                                            tmp_ptr = tmp_ptr[tmp_key]
                                        else:
                                            spellNames.append(spell_key)
                                            break
                                    else:
                                        spellNames.append(self.get_strtable_value(strtable_locale, tmp_ptr, tmp_ptr))
                                to_append = spellNames
                            else:
                                to_append = ""
                        elif i == 139 or i == 140: #角色定位本地化名称（仅云顶之弈）（CharacterRole name localization）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
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
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
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
                            elif i == 111:
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
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            tooltip_key: str | list[str] = champion_data[subkey1][-1]
                            if i in {176, 177, 268, 269}: #说明文本单值（Single tooltip value）
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                to_append = tooltip_raw
                            else: #说明文本列表（Tooltip value list）
                                if tooltip_key == "":
                                    to_append = ""
                                else:
                                    tooltips_raw: list[str] = list(map(lambda x: self.get_strtable_value(strtable_locale, x, default = ""), tooltip_key))
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
                                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
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
                    if i <= 10: #主键衍生键（`key`-derivated keys）
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #英雄文件夹（`championFolder`）
                            try:
                                championFolder = key1.split("/")[1]
                            except IndexError:
                                championFolder = ""
                            to_append = championFolder
                        elif i == 2: #根技能（`isRootSpell`）
                            to_append = key1 in rootSpell_ability_map
                        elif i == 10: #技能热键（`spellHotKey`）
                            if len(key1.split("/")) > 1: #形如（Looks like）：Characters/Aphelios/Spells/ApheliosQ_ClientTooltipWrapper
                                championFolder = key1.split("/")[1]
                                CharacterRecordRoot_key: str = f"Characters/{championFolder}/CharacterRecords/Root"
                                if CharacterRecordRoot_key in champions_bin:
                                    CharacterRecordRoot: dict[str, Any] = champions_bin[CharacterRecordRoot_key]
                                    if "mCharacterPassiveSpell" in CharacterRecordRoot and CharacterRecordRoot["mCharacterPassiveSpell"] == key1:
                                        to_append = "P"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][0] == key1:
                                        to_append = "Q"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][1] == key1:
                                        to_append = "W"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][2] == key1:
                                        to_append = "E"
                                    elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][3] == key1: #经检验，所有有“spells”键的角色记录对象的spells键的值列表长度恒为4（After examination, the length of the value list of existing "spells" key of all CharacterRecord objects is always 4）
                                        to_append = "R"
                                    # elif "spellNames" in CharacterRecordRoot and "Characters/%s/Spells/%s" %(championFolder, CharacterRecordRoot["spellNames"][0]) == key1: #对于不存在“spells”键的版本而言，前面已经根据角色名称代码和技能名称补充了该键，因此下面这部分实际上是不需要的（For the CharacterRecord objects of those versions which don't contain "spells" key, since this key was supplemented previously according to the character name and the spell name, the following part isn't necessary）
                                    #     to_append = "Q"
                                    # elif "spellNames" in CharacterRecordRoot and "Characters/%s/Spells/%s" %(championFolder, CharacterRecordRoot["spellNames"][1]) == key1:
                                    #     to_append = "W"
                                    # elif "spellNames" in CharacterRecordRoot and "Characters/%s/Spells/%s" %(championFolder, CharacterRecordRoot["spellNames"][2]) == key1:
                                    #     to_append = "E"
                                    # elif "spellNames" in CharacterRecordRoot and "Characters/%s/Spells/%s" %(championFolder, CharacterRecordRoot["spellNames"][3]) == key1:
                                    #     to_append = "R"
                                    else:
                                        to_append = ""
                                else:
                                    to_append = ""
                            else:
                                to_append = ""
                        else:
                            subkey = key.split("_")[1]
                            if key1 in rootSpell_ability_map:
                                rootAbility = rootSpell_ability_map[key1]
                                if subkey in rootAbility:
                                    to_append = rootAbility[subkey]
                                else:
                                    if i == 6: #所属技能的持续时间可控制（`rootAbility_mLifetimeManuallyManaged`）
                                        to_append = False
                                    else:
                                        to_append = ""
                            else:
                                if i == 6: #所属技能的持续时间可控制（`rootAbility_mLifetimeManuallyManaged`）
                                    to_append = False
                                else:
                                    to_append = ""
                    else:
                        subkeyList: list[str] = key.split()
                        if "mSpell" in value and pStrConst.search(key):
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            tooltip_key: str = champion_spell_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            if subkey2.endswith("_burn"):
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value["mSpell"], isCHS = isCHS, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                            else:
                                to_append = tooltip_raw
                        else:
                            tmp_ptr = value
                            for j in range(len(subkeyList)):
                                tmp_key = subkeyList[j]
                                if tmp_key in tmp_ptr:
                                    tmp_ptr = tmp_ptr[tmp_key]
                                else:
                                    if i in {6, 20, 39, 48, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 78, 79, 80, 81, 82, 83, 85, 86, 87, 89, 90, 91, 93, 94, 95, 97, 98, 99, 100, 101, 102, 103, 105, 106, 107, 113, 114, 115, 116, 117, 118, 119, 121, 131, 132, 133, 141, 142, 146, 161, 163, 167, 171, 172, 176, 177, 179, 181, 195, 214, 221, 222, 235, 236, 237, 310}:
                                        to_append = False
                                    elif i in {76, 77, 84, 88, 96, 109, 112, 134, 140, 144, 150, 243, 320, 321, 322}:
                                        to_append = tmp_key == subkeyList[-2] #如果遍历到某个逻辑值键的上一级就停止，且该逻辑值键的默认值为真，仍应将其置为假，以表明该逻辑值键所在的命名场景不存在（If `tmp_key` traverses through `subkeyList` and stopped at the parent key of a boolean key whose default value is True, the result to append should be set as False, to indicate that the namespace background of this boolean key doesn't exist）
                                    else:
                                        to_append = ""
                                    break
                            else: #在成功遍历到目标值后才会执行以下部分（Only when the target value is fetched will this part be executed）
                                to_append = tmp_ptr
                    champion_spell_data[key].append(to_append)
                    champion_spell_data_json[key].append(pyobj2json(to_append))
            #     logPrint("[%d/%d]已整理指令对象（Organized spell object）： %s" %(count, len(champions_bin.items()), key1), print_time = True)
            # else:
            #     logPrint("[%d/%d]已跳过键（Skipped key）： %s" %(count, len(champions_bin.items()), key1), print_time = True)

        #数据框构建和排序（Build the dataframe and sort the keys and values）
        ##英雄（Champion）
        if useAllCharacter:
            if Patch(self.patch_number) < Patch("16.5"):
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
        champion_df = champion_df.sort_values(by = "mCharacterName" if useAllCharacter else "characterToolData championId", ascending = True, ignore_index = True) #原来读取文件的顺序是英雄别名顺序，合并后的顺序是打乱后的顺序。因为这两种顺序都不太符合设计初衷（对于前者，试想虚空遁地兽 雷克塞和兽灵行者 乌迪尔中间掺和了一堆末日人机英雄），所以索性就用了英雄序号作为排序标准【Originally, the order to read files follows that of aliases, and the order of champions after being merged is shuffled. Because both orders don't accord to the intuitive intent by design (for the former order, think about those ruby champions between Rek'Sai and Udyr), championId is used here as the sorting criterium】
        logPrint("正在优化英雄数据框的逻辑值显示……\nOptimizing boolean value display of the champion dataframe ...")
        optimize_bool_display(champion_df)
        champion_df = pandas.concat([pandas.DataFrame([champion_header])[champion_df.columns], champion_df], ignore_index = True)
        self.champion_df = champion_df
        ##技能指令（Spell）
        champion_spell_statistics_output_order: list[int] = [0, 11, 12, 1, 10, 247, 264, 265, 3, 2, 7, 8, 9, 6, 4, 5, 24, 13, 14, 15, 25, 101, 116, 218, 65, 219, 44, 30, 39, 66, 47, 61, 62, 63, 29, 64, 67, 26, 27, 28, 31, 217, 32, 33, 220, 196, 122, 123, 56, 57, 58, 93, 124, 125, 42, 43, 197, 126, 127, 128, 95, 96, 45, 46, 49, 50, 51, 52, 48, 22, 23, 97, 102, 16, 17, 54, 19, 18, 20, 21, 38, 53, 55, 59, 60, 86, 78, 79, 89, 90, 70, 69, 75, 107, 72, 73, 74, 91, 94, 68, 71, 233, 81, 76, 77, 92, 84, 85, 80, 82, 83, 87, 105, 115, 88, 235, 236, 237, 103, 118, 117, 119, 121, 232, 221, 222, 223, 224, 225, 226, 227, 34, 35, 36, 98, 231, 100, 114, 104, 205, 206, 106, 109, 108, 110, 113, 111, 112, 120, 129, 208, 99, 209, 210, 211, 212, 213, 216, 228, 229, 230, 234, 238, 240, 239, 300, 301, 241, 242, 243, 244, 258, 259, 248, 253, 280, 282, 281, 283, 256, 292, 294, 293, 295, 251, 274, 275, 252, 276, 278, 277, 279, 254, 284, 286, 285, 287, 255, 288, 290, 289, 291, 257, 296, 298, 297, 299, 245, 260, 261, 246, 262, 263, 249, 266, 268, 267, 269, 250, 270, 272, 271, 273, 302, 303, 304, 305, 306, 307, 308, 309, 310, 207, 40, 37, 41, 311, 312, 314, 315, 324, 316, 329, 330, 313, 325, 327, 326, 328, 317, 331, 333, 332, 334, 318, 335, 337, 336, 338, 319, 320, 321, 322, 323, 198, 199, 200, 201, 202, 203, 204, 130, 174, 134, 132, 135, 136, 131, 133, 214, 215, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 175, 182, 176, 177, 178, 179, 180, 181, 192, 183, 184, 185, 186, 187, 188, 189, 190, 191, 193, 194, 195, 339]
        champion_spell_data_organized: dict[str, list[Any]] = {champion_spell_header_keys[i]: champion_spell_data_json[champion_spell_header_keys[i]] for i in champion_spell_statistics_output_order}
        champion_spell_df: pandas.DataFrame = pandas.DataFrame(data = champion_spell_data_organized)
        logPrint("正在排序英雄技能数据框……\nOrganizing champion spell dataframe ...")
        champion_spell_df_keys_ordered = []
        for i in range(1, len(champion_df)): #根据英雄数据框排序后的英雄顺序读取其技能，使得这些技能总是位于英雄技能数据框的顶部（Read the abilities of champions which follow the order in the champion dataframe to make champion abilities always in the front of the champion spell dataframe）
            mAbilities_str: str = champion_df.loc[i, "mAbilities"]
            if mAbilities_str != "":
                mAbilities: list[str] = eval(mAbilities_str)
                for ability_key in mAbilities:
                    if ability_key in champions_bin:
                        abilityObj = champions_bin[ability_key]
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

    def export_champion_data(self, useAllCharacter: Optional[bool] = None, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出英雄数据到工作簿中。<br>Export champion data to a workbook.
        
        在导出所有角色数据时，产生以下工作表：<br>When all character data are exported, the following worksheets are added:
        - 角色（Characters）
        - 角色技能（Character Spells）
        
        在仅导出英雄数据时，产生以下工作表：<br>When only champion data are exported, the following worksheets are added:
        - 英雄（Champions）
        - 英雄技能（Champion Spells）
        
        :param useAllCharacter: 是否导出所有角色数据。如果未指定，则使用对象的属性值。<br>Whether to export data of all characters. If unspecified, it'll use the attribute value of the object.
        :type useAllCharacter: bool
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
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if self.wbPath == "":
            logPrint("尚未指定文件保存路径。\nPath of exported file not specified.")
            return
        if self.patch == "" and self.sheet_naming_fold:
            logPrint("尚未指定完整版本号！\nPatch number not specified yet!")
            return
        if useAllCharacter == None:
            useAllCharacter = self.useAllCharacter
        if self.champion_df.empty or self.champion_spell_df.empty:
            status: int = self.build_champion_dataframe(useAllCharacter = useAllCharacter, debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name1: str = "角色（Characters）" if useAllCharacter else "英雄（Champions）"
        sheet1_name2: str = f"{self.patch_number} Characters" if useAllCharacter else f"{self.patch_number} Champions"
        sheet2_name1: str = "角色技能（Character Spells）" if useAllCharacter else "英雄技能（Champion Spells）"
        sheet2_name2: str = f"{self.patch_number} CharacterSpells" if useAllCharacter else f"{self.patch_number} ChampionSpells"
        sheet1_name: str = sheet1_name2 if self.sheet_naming_fold else sheet1_name1
        sheet2_name: str = sheet2_name2 if self.sheet_naming_fold else sheet2_name1
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.champion_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(self.champion_spell_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A1 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet2_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"英雄数据已导出到{self.wbPath}。按回车键继续。\nChampion data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

class ItemExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个装备提取器对象。<br>Initialize a ItemExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.item_ready: bool = False
        self.item_df: pandas.DataFrame = pandas.DataFrame()
        self.itemGroup_df: pandas.DataFrame = pandas.DataFrame()
        self.itemModifier_df: pandas.DataFrame = pandas.DataFrame()
        
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.item_ready = False
    
    def get_item_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取装备二进制描述数据。<br>Get binary description data of items online.
        '''
        logPrint = self.log.logPrint
        items_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/items.cdtb.bin.json"
        if items_bin_url in self.__class__.data_cache["online"]:
            self.items_bin = self.__class__.data_cache["online"][items_bin_url]
        else:
            source, status, self.session = requestUrl("GET", items_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == -1:
                    logPrint("装备信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nItem data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                elif status == 404:
                    logPrint("装备信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nItem data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(items_bin_url))
                time.sleep(3)
                self.init_data_readiness()
                return
            self.items_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][items_bin_url] = self.items_bin
        self.item_ready = True
    
    def read_item_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取装备二进制描述数据。<br>Get binary description data of items offline.
        
        :param path: 装备二进制描述文件的本地路径。<br>A local path of item binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        items_bin_path: str = path
        if items_bin_path in self.__class__.data_cache["local"]:
            self.items_bin = self.__class__.data_cache["local"][items_bin_path]
        else:
            with open(items_bin_path, "r", encoding = "utf-8") as fp:
                self.items_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][items_bin_path] = self.items_bin
        self.item_ready = True
    
    def build_item_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建装备数据框。<br>Build item dataframe.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 装备二进制描述文件的本地路径。<br>A local path of item binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.item_ready:
            #获取装备信息（Get item information）
            logPrint("正在读取装备数据……\nReading item data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_item_data(path = path)
            else:
                self.get_item_data()
            if not self.item_ready:
                logPrint("装备数据尚未准备就绪！\nItem data not prepared!")
                return 2
        
        #提取指令字典（Extract spell dictionary）
        self.init_mSpells()
        for (key, value) in self.items_bin.items():
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        
        #构建从装备序号到装备数据的映射（Build a map from the itemId to the corresponding item data）
        itemKey_itemId_map: dict[int, str] = {}
        for (key, value) in self.items_bin.items():
            if key != "__linked" and value["__type"] == "ItemData":
                itemKey_itemId_map[value["itemID"]] = key #已事先确定所有装备数据对象中都有itemID键（Confirmed in advance that all ItemData objects have `itemID` key）
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建装备数据框……\nBuilding the item dataframes ...", print_time = True)
        item_header_keys: list[str] = list(item_header.keys())
        item_data: dict[str, list[Any]] = {key: [] for key in item_header_keys}
        item_data_json: dict[str, list[Any]] = copy.deepcopy(item_data)
        itemGroup_header_keys: list[str] = list(itemGroup_header.keys())
        itemGroup_data: dict[str, list[Any]] = {key: [] for key in itemGroup_header_keys}
        itemGroup_data_json: dict[str, list[Any]] = copy.deepcopy(itemGroup_data)
        itemModifier_header_keys: list[str] = list(itemModifier_header.keys())
        itemModifier_data: dict[str, list[Any]] = {key: [] for key in itemModifier_header_keys}
        itemModifier_data_json: dict[str, list[Any]] = copy.deepcopy(itemModifier_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        item_rarities: dict[str, str] = {0: "无", 1: "初始", 2: "基础", 3: "工资装", 4: "史诗", 5: "传说", 6: "神话", 7: "升级", 8: "锻造器", 9: "棱彩"}
        # item_rarities: dict[str, str] = {0: "NONE", 1: "STARTER", 2: "BASIC", 3: "Gold Income", 4: "EPIC", 5: "LEGENDARY", 6: "Mythic", 7: "Level Up", 8: "ANVIL", 9: "PRISMATIC"}
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.items_bin.items():
            if key1 != "__linked" and value["__type"] == "ItemData":
                for i in range(len(item_header_keys)):
                    key: str = item_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 100:
                        if i == 84: #显示名（中文）（`mDisplayName_content_zh`）
                            to_append = self.get_strtable_value(strtable_lol_target, value.get("mDisplayName", ""), default = "")
                        elif i == 85: #显示名（英文）（`mDisplayName_content_en`）
                            to_append = self.get_strtable_value(strtable_lol_default, value.get("mDisplayName", ""), default = "")
                        elif i == 86: #装备推荐属性内容（`mItemAdviceAttributes_content`）
                            to_append = list(map(lambda x: self.items_bin[x]["mAttribute"], value.get("mItemAdviceAttributes", [])))
                        elif i == 87: #总价格（`totalPrice`）
                            totalPrice = 0
                            #下面通过一个栈实现装备总价格的计算（Calculate the total price using a stack）
                            recipeItem_key_stack: list[str] = [key1]
                            while len(recipeItem_key_stack) > 0:
                                item_key_tmp: str = recipeItem_key_stack.pop()
                                itemJson_tmp = self.items_bin[item_key_tmp]
                                totalPrice += itemJson_tmp.get("price", 0) #部分装备没有价格键，例如防御塔装备（Some items don't have the "price" key, e.g. turret items）
                                if "recipeItemLinks" in itemJson_tmp:
                                    recipeItem_key_stack += itemJson_tmp["recipeItemLinks"][::-1] #保证金币的计算遵循正确的装备构件顺序，虽然这其实无关紧要（Make sure the calculation order of total price follows the correct in-game item component order, although it doesn't matter actually）
                            to_append = totalPrice
                        elif i == 88: #特殊合成材料（中文）（`specialRecipe_displayName_content_zh`）
                            to_append = self.get_strtable_value(strtable_lol_target, self.items_bin[itemKey_itemId_map[value["specialRecipe"]]].get("mDisplayName", ""), default = "") if "specialRecipe" in value else ""
                        elif i == 89: #特殊合成材料（英文）（`specialRecipe_displayName_content_en`）
                            to_append = self.get_strtable_value(strtable_lol_default, self.items_bin[itemKey_itemId_map[value["specialRecipe"]]].get("mDisplayName", ""), default = "") if "specialRecipe" in value else ""
                        elif i == 90: #位阶（`rarity`）
                            to_append = item_rarities[value.get("epicness", 2)]
                        elif i == 91: #次要位阶（`secondaryRarity`）
                            to_append = item_rarities[value["SecondaryEpicness"]] if "SecondaryEpicness" in value else ""
                        elif i == 92: #同级替换装备（中文）（`sidegradeItemNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["sidegradeItemLinks"])) if "sidegradeItemLinks" in value else ""
                        elif i == 93: #同级替换装备（英文）（`sidegradeItemNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["sidegradeItemLinks"])) if "sidegradeItemLinks" in value else ""
                        elif i == 94: #合成材料（中文）（`recipeItemNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["recipeItemLinks"])) if "recipeItemLinks" in value else ""
                        elif i == 95: #合成材料（英文）（`recipeItemNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["recipeItemLinks"])) if "recipeItemLinks" in value else ""
                        elif i == 96: #所需材料（中文）（`requiredItemNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["requiredItemLinks"])) if "requiredItemLinks" in value else ""
                        elif i == 97: #所需材料（英文）（`requiredItemNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["requiredItemLinks"])) if "requiredItemLinks" in value else ""
                        elif i == 98: #同品类合成装备（中文）（`mItemDataBuildNames_content_zh`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_target, self.items_bin[x].get("mDisplayName", ""), default = x), value["mItemDataBuild"]["itemLinks"])) if "mItemDataBuild" in value else ""
                        elif i == 99: #同品类合成装备（英文）（`mItemDataBuildNames_content_en`）
                            to_append = list(map(lambda x: self.get_strtable_value(strtable_lol_default, self.items_bin[x].get("mDisplayName", ""), default = x), value["mItemDataBuild"]["itemLinks"])) if "mItemDataBuild" in value else ""
                        elif i == 100: #装备效果重做版本（`LastMajorChangeVersion`）
                            to_append = "%d.%d" %(value["LastMajorChangeMajorPatchVersion"], value["LastMajorChangeMinorPatchVersion"]) if "LastMajorChangeMajorPatchVersion" in value and "LastMajorChangeMinorPatchVersion" in value else ""
                        else:
                            to_append = value.get(key, False if i in {16, 19, 20, 21, 22, 23, 24, 27} else True if i in {25, 26} else "")
                    elif i <= 103: #数据可用性子键（`mItemDataAvailability`'s subkeys）
                        to_append = value["mItemDataAvailability"].get(key.split()[1], False) if "mItemDataAvailability" in value else False
                    else: #客户端数据子键（`mItemDataClient`'s subkeys）
                        if i <= 137:
                            tmpObj_ptr = value
                            for subkey_iter in key.split():
                                if subkey_iter in tmpObj_ptr:
                                    tmpObj_ptr = tmpObj_ptr[subkey_iter]
                                else:
                                    to_append = True if i == 106 else ""
                                    break
                            else:
                                to_append = tmpObj_ptr
                        elif i == 138: #属性效果（`mItemDataClient mTooltipData mStatList`）
                            if "mItemDataClient" in value and "mTooltipData" in value["mItemDataClient"] and "mLists" in value["mItemDataClient"]["mTooltipData"]:
                                to_append = list(map(lambda x: x["type"], value["mItemDataClient"]["mTooltipData"]["mLists"]["Stats"].get("Elements", [])))
                            else:
                                to_append = ""
                        elif i <= 218: #本地化说明文本（Localized tooltips）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            tooltip_key: str = item_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            if subkey2.endswith("_burn"):
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, isCHS = isCHS, enableModeOverride = True, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                            else:
                                to_append = tooltip_raw
                        else: #客户端内位阶（`mItemDataClient rarity`）
                            to_append = item_rarities[value["mItemDataClient"]["epicness"]] if "mItemDataClient" in value and "epicness" in value["mItemDataClient"] else ""
                    item_data[key].append(to_append)
                    item_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "ItemGroup":
                for i in range(len(itemGroup_header_keys)):
                    key: str = itemGroup_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        to_append = value.get(key, False if i == 6 else "")
                    itemGroup_data[key].append(to_append)
                    itemGroup_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "ItemModifier":
                for i in range(len(itemModifier_header_keys)):
                    key: str = itemModifier_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 27:
                        if i in {9, 12, 25}:
                            to_append = value.get(key, False)
                        else:
                            to_append = value.get(key, "")
                    elif i <= 35:
                        subkey2: str = re.search(r"_mDisplayName_content_\w*", key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[3] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        item_key: str = itemModifier_data[subkey1][-1]
                        if item_key in self.items_bin and "mDisplayName" in self.items_bin[item_key]:
                            tooltip_key: str = self.items_bin[item_key]["mDisplayName"]
                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        else:
                            to_append = ""
                    else:
                        subkey2 = pStrConst.search(key).group()
                        subkey1 = key.replace(subkey2, "")
                        useTargetLocale = subkey2.split("_")[2] == "zh"
                        isCHS = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key = itemModifier_data[subkey1][-1]
                        to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                    itemModifier_data[key].append(to_append)
                    itemModifier_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        item_statistics_output_order: list[int] = [0, 9, 2, 84, 85, 7, 22, 19, 1, 35, 27, 70, 20, 21, 23, 24, 25, 26, 75, 101, 102, 103, 77, 33, 94, 95, 10, 14, 87, 17, 15, 28, 88, 89, 31, 92, 93, 73, 98, 99, 78, 29, 90, 30, 91, 11, 12, 86, 13, 3, 4, 8, 5, 34, 96, 97, 6, 16, 18, 51, 69, 60, 65, 58, 59, 62, 63, 47, 55, 56, 45, 57, 52, 53, 54, 71, 68, 67, 61, 48, 39, 50, 49, 64, 66, 38, 44, 72, 32, 42, 36, 37, 40, 41, 46, 43, 80, 81, 100, 74, 76, 79, 83, 82, 104, 105, 106, 127, 138, 128, 207, 208, 209, 210, 129, 211, 212, 213, 214, 130, 215, 216, 217, 218, 107, 139, 140, 108, 141, 142, 143, 144, 109, 145, 146, 147, 148, 110, 149, 150, 151, 152, 111, 153, 154, 112, 155, 156, 157, 158, 113, 159, 160, 161, 162, 114, 163, 164, 165, 166, 115, 167, 168, 169, 170, 116, 171, 172, 117, 173, 174, 175, 176, 118, 177, 178, 179, 180, 119, 181, 182, 183, 184, 120, 185, 186, 187, 188, 121, 189, 190, 191, 192, 122, 193, 194, 123, 195, 196, 197, 198, 124, 199, 200, 201, 202, 125, 203, 204, 205, 206, 126, 131, 132, 133, 134, 219, 135, 136, 137]
        item_data_organized: dict[str, list[Any]] = {item_header_keys[i]: item_data_json[item_header_keys[i]] for i in item_statistics_output_order}
        item_df: pandas.DataFrame = pandas.DataFrame(data = item_data_organized)
        item_df = item_df.sort_values(by = "itemID", ascending = True, ignore_index = True)
        logPrint("正在优化装备数据框的逻辑值显示……\nOptimizing boolean value display of the item dataframe ...")
        optimize_bool_display(item_df)
        item_df = pandas.concat([pandas.DataFrame([item_header])[item_df.columns], item_df], ignore_index = True)
        self.item_df = item_df
        itemGroup_statistics_output_order: list[int] = [0, 1, 5, 2, 3, 4, 7, 6]
        itemGroup_data_organized: dict[str, list[Any]] = {itemGroup_header_keys[i]: itemGroup_data_json[itemGroup_header_keys[i]] for i in itemGroup_statistics_output_order}
        itemGroup_df: pandas.DataFrame = pandas.DataFrame(data = itemGroup_data_organized)
        logPrint("正在优化装备分组数据框的逻辑值显示……\nOptimizing boolean value display of the item group dataframe ...")
        optimize_bool_display(itemGroup_df)
        itemGroup_df = pandas.concat([pandas.DataFrame([itemGroup_header])[itemGroup_df.columns], itemGroup_df], ignore_index = True)
        self.itemGroup_df = itemGroup_df
        itemModifier_statistics_output_order: list[int] = [0, 1, 3, 30, 31, 5, 26, 18, 12, 9, 10, 25, 4, 6, 14, 15, 13, 11, 2, 28, 29, 7, 32, 33, 8, 34, 35, 22, 44, 45, 23, 46, 47, 24, 48, 49, 16, 36, 37, 17, 38, 39, 20, 40, 41, 21, 42, 43, 19, 27]
        itemModifier_data_organized: dict[str, list[Any]] = {itemModifier_header_keys[i]: itemModifier_data_json[itemModifier_header_keys[i]] for i in itemModifier_statistics_output_order}
        itemModifier_df: pandas.DataFrame = pandas.DataFrame(data = itemModifier_data_organized)
        logPrint("正在优化装备修饰数据框的逻辑值显示……\nOptimizing boolean value display of the item modifier dataframe ...")
        optimize_bool_display(itemModifier_df)
        itemModifier_df = pandas.concat([pandas.DataFrame([itemModifier_header])[itemModifier_df.columns], itemModifier_df], ignore_index = True)
        self.itemModifier_df = itemModifier_df
        return 0
    
    def export_item_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出装备数据到工作簿中。产生以下工作表：<br>Export item data to a workbook. The following worksheet is added:
        - 装备（Items）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 装备二进制描述文件的本地路径。<br>A local path of item binary description file.
        
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
        if self.item_df.empty:
            status: int = self.build_item_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} Items" if self.sheet_naming_fold else "装备（Items）"
        sheet2_name: str = f"{self.patch_number} ItemGroups" if self.sheet_naming_fold else "装备分组（Item Groups）"
        sheet3_name: str = f"{self.patch_number} ItemModifiers" if self.sheet_naming_fold else "装备修饰（Item Modifiers）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.item_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(self.itemGroup_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    addDefaultStyle(self.itemModifier_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet2_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet3_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"装备数据已导出到{self.wbPath}。按回车键继续。\nItem data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

class AugmentExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个强化符文提取器对象。<br>Initialize a AugmentExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.augments_ready: dict[str, bool] = {"map30": False, "cherry": False, "map33": False, "map12": False, "kiwi": False}
        self.CherryAugment_df: pandas.DataFrame = pandas.DataFrame()
        self.SwarmAugment_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiAugment_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiAugmentSet_df: pandas.DataFrame = pandas.DataFrame()
        
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
            self.map30_bin = self.__class__.data_cache["online"][map30_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map30_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == -1:
                    logPrint("怒火角斗场地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                elif status == 404:
                    logPrint("怒火角斗场地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map30_bin_url))
                time.sleep(3)
                self.init_data_readiness()
                return
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map30_bin_url] = self.map30_bin
        self.augments_ready["map30"] = True
        #斗魂竞技场模式（Arena mode）
        cherry_bin_url = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/cherry.bin.json"
        if cherry_bin_url in self.__class__.data_cache["online"]:
            self.cherry_bin = self.__class__.data_cache["online"][cherry_bin_url]
        else:
            source, status, self.session = requestUrl("GET", cherry_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("斗魂竞技场强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nArena augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(cherry_bin_url))
                    self.cherry_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint('斗魂竞技场强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nArena augment data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.')
                    time.sleep()
                    self.init_data_readiness()
                    return
            else:
                self.cherry_bin = source.json()
            self.__class__.data_cache["online"][cherry_bin_url] = self.cherry_bin
        self.augments_ready["cherry"] = True
        #最终都市地图（Final City map）
        map33_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map33/map33.bin.json"
        if map33_bin_url in self.__class__.data_cache["online"]:
            self.map33_bin = self.__class__.data_cache["online"][map33_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map33_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("最终都市地图信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nFinal City map data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(map33_bin_url))
                    self.map33_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("最终都市地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nFinal City map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map33_bin = source.json()
            self.__class__.data_cache["online"][map33_bin_url] = self.map33_bin
        self.augments_ready["map33"] = True
        #嚎哭深渊地图（Howling Abyss map）
        map12_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map12/map12.bin.json"
        if map12_bin_url in self.__class__.data_cache["online"]:
            self.map12_bin = self.__class__.data_cache["online"][map12_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map12_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("嚎哭深渊地图信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nHowling Abyss map data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(map12_bin_url))
                    self.map12_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint("嚎哭深渊地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nHowling Abyss map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                    time.sleep(3)
                    self.init_data_readiness()
                    return
            else:
                self.map12_bin = source.json()
            self.__class__.data_cache["online"][map12_bin_url] = self.map12_bin
        self.augments_ready["map12"] = True
        #海克斯大乱斗模式（ARAM: Mayhem mode）
        if Patch(self.patch_number) >= Patch("16.2.7366411"):
            kiwi_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/kiwi.bin.json"
        else:
            kiwi_bin_url = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/augments.bin.json"
        if kiwi_bin_url in self.__class__.data_cache["online"]:
            self.kiwi_bin = self.__class__.data_cache["online"][kiwi_bin_url]
        else:
            source, status, self.session = requestUrl("GET", kiwi_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("海克斯大乱斗强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nARAM: Mayhem augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(kiwi_bin_url))
                    self.kiwi_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint('海克斯大乱斗强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nARAM: Mayhem augment data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.')
                    time.sleep()
                    self.init_data_readiness()
                    return
            else:
                self.kiwi_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][kiwi_bin_url] = self.kiwi_bin
        self.augments_ready["kiwi"] = True
    
    def read_augment_data(self, paths: list[str]) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取强化符文二进制描述数据。<br>Get binary description data of augments offline.
        
        :param paths: 强化符文二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of augment binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 斗魂竞技场模式专属信息（Arena mode specific data）
            - 最终都市地图（Final City map）
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
            self.map30_bin = self.__class__.data_cache["local"][map30_bin_path]
        else:
            with open(map30_bin_path, "r", encoding = "utf-8") as fp:
                self.map30_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map30_bin_path] = self.map30_bin
        self.augments_ready["map30"] = True
        #斗魂竞技场模式（Arena mode）
        cherry_bin_path: str = paths[1]
        if cherry_bin_path in self.__class__.data_cache["local"]:
            self.cherry_bin = self.__class__.data_cache["local"][cherry_bin_path]
        else:
            with open(cherry_bin_path, "r", encoding = "utf-8") as fp:
                self.cherry_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][cherry_bin_path] = self.cherry_bin
        self.augments_ready["cherry"] = True
        #最终都市地图（Final City map）
        map33_bin_path: str = paths[2]
        if map33_bin_path in self.__class__.data_cache["local"]:
            self.map33_bin = self.__class__.data_cache["local"][map33_bin_path]
        else:
            with open(map33_bin_path, "r", encoding = "utf-8") as fp:
                self.map33_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map33_bin_path] = self.map33_bin
        self.augments_ready["map33"] = True
        #嚎哭深渊地图（Howling Abyss map）
        map12_bin_path: str = paths[3]
        if map12_bin_path in self.__class__.data_cache["local"]:
            self.map12_bin = self.__class__.data_cache["local"][map12_bin_path]
        else:
            with open(map12_bin_path, "r", encoding = "utf-8") as fp:
                self.map12_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map12_bin_path] = self.map12_bin
        self.augments_ready["map12"] = True
        #海克斯大乱斗模式（ARAM: Mayhem mode）
        kiwi_bin_path: str = paths[4]
        if kiwi_bin_path in self.__class__.data_cache["local"]:
            self.kiwi_bin = self.__class__.data_cache["local"][kiwi_bin_path]
        else:
            with open(kiwi_bin_path, "r", encoding = "utf-8") as fp:
                self.kiwi_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][kiwi_bin_path] = self.kiwi_bin
        self.augments_ready["kiwi"] = True
    
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
        
        #数据整理核心部分（Data organization core part）
        AugmentDisplayTags: dict[int, str] = {0: "己方", 1: "伤害", 2: "综合", 3: "复原力", 4: "速度", 5: "功能", 6: "属性锻造器", 7: "经济"} #通过字符串常量池的“cherry_augmentdisplaytag_...”类键得到（Obtained by "cherry_augmentdisplaytag_..." keys）
        #AugmentDisplayTags: dict[int, str] = {0: "Ally", 1: "Damage", 2: "General", 3: "Resilience", 4: "Speed", 5: "Utility", 6: "Stat Anvil", 7: "Economy"}
        augment_rarities: dict[int, str] = {0: "白银", 1: "黄金", 2: "棱彩", 3: "超凡", 4: "晶耀"}
        #augment_rarities: dict[int, str] = {0: "Silver", 1: "Gold", 2: "Prismatic", 3: "Unique", 4: "SheenGlow"}
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
                    if i == 0: #主键（`Key`）
                        to_append: Any = key1
                    elif i <= 18:
                        tmp_ptr: Any = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i == 2: #可用性（`Enabled`）
                                    to_append = True
                                elif i == 17: #{ed593c9c}
                                    to_append = False
                                else:
                                    to_append = ""
                                break
                        else:
                            to_append = tmp_ptr
                    elif i <= 44: #字符串常量（String constants）
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = CherryAugment_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            spellKey: str = value["RootSpell"]
                            if spellKey in map30_bin_whole:
                                mSpell: Optional[dict[str, Any]] = map30_bin_whole[spellKey]["mSpell"]
                            else:
                                mSpell: Optional[dict[str, Any]] = None
                            if mSpell == None:
                                to_append = ""
                            else:
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    elif i == 45: #强化符文显示标签内容（`AugmentDisplayTags_content`）
                        to_append = list(map(lambda x: AugmentDisplayTags[x], value["AugmentDisplayTags"]))
                    elif i == 46: #位阶（`rarityValue`）
                        to_append = augment_rarities[value.get("rarity", 0)]
                    else: #根指令对象（`RootSpellObject`）
                        to_append = map30_bin_whole.get(value["RootSpell"], "")
                    CherryAugment_data[key].append(to_append)
                    CherryAugment_data_json[key].append(pyobj2json(to_append))
        CherryAugment_statistics_output_order: list[int] = [0, 1, 18, 2, 3, 19, 20, 16, 46, 15, 45, 7, 8, 17, 4, 21, 22, 23, 24, 5, 25, 26, 27, 28, 9, 29, 30, 31, 32, 10, 33, 34, 35, 36, 11, 37, 38, 39, 40, 12, 41, 42, 43, 44, 6, 47, 13, 14]
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
                    if i == 0: #主键（`Key`）
                        to_append: Any = key1
                    elif i <= 10:
                        to_append = value.get(key, "")
                    elif i <= 20: #字符串常量（String constants）
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = SwarmAugment_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            spellKey: str = value["RootSpell"]
                            if spellKey in self.map33_bin:
                                mSpell: Optional[dict[str, Any]] = self.map33_bin[spellKey]["mSpell"]
                            else:
                                mSpell: Optional[dict[str, Any]] = None
                            if mSpell == None:
                                to_append = ""
                            else:
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    elif i == 21: #位阶（`rarityValue`）
                        to_append = augment_rarities[value.get("rarity", 0)]
                    else: #根指令对象（`RootSpellObject`）
                        to_append = self.map33_bin.get(value["RootSpell"], "")
                    SwarmAugment_data[key].append(to_append)
                    SwarmAugment_data_json[key].append(pyobj2json(to_append))
        SwarmAugment_statistics_output_order: list[int] = [0, 1, 10, 2, 11, 12, 9, 21, 6, 3, 13, 14, 15, 16, 4, 17, 18, 19, 20, 5, 22, 7, 8]
        SwarmAugment_data_organized: dict[str, list[Any]] = {SwarmAugment_header_keys[i]: SwarmAugment_data_json[SwarmAugment_header_keys[i]] for i in SwarmAugment_statistics_output_order}
        SwarmAugment_df: pandas.DataFrame = pandas.DataFrame(data = SwarmAugment_data_organized)
        logPrint("正在优化无尽狂潮强化数据框的逻辑值显示……\nOptimizing boolean value display of the Swarm augment dataframe ...")
        optimize_bool_display(SwarmAugment_df)
        SwarmAugment_df = pandas.concat([pandas.DataFrame([SwarmAugment_header])[SwarmAugment_df.columns], SwarmAugment_df], ignore_index = True)
        self.SwarmAugment_df = SwarmAugment_df
        ##海克斯大乱斗强化符文（ARAM: Mayhem augments）
        self.init_mSpells()
        augmentSet_map: dict[str, list[str]] = {}
        for (key, value) in map12_bin_whole.items():
            if key != "__linked":
                if value["__type"] == "SpellObject": #提取指令字典（Extract spell dictionary）
                    self.__class__.mSpells[value["mScriptName"]] = value
                elif value["__type"] == "{27bc6378}": #整理从强化符文到强化符文套装的映射（Build a map from augment to its belong sets）
                    for augment_key in value["augments"]:
                        if not augment_key in augmentSet_map:
                            augmentSet_map[augment_key] = []
                        augmentSet_map[augment_key].append(key)
        for (key1, value) in map12_bin_whole.items():
            if key1 != "__linked" and value["__type"] == "AugmentData": #强化符文（Augment）
                for i in range(len(KiwiAugment_header_keys)):
                    key: str = KiwiAugment_header_keys[i]
                    if i == 0: #主键（`Key`）
                        to_append: Any = key1
                    elif i <= 50:
                        if i <= 20:
                            tmp_ptr: Any = value
                            subkeyList: list[str] = key.split()
                            for tmp_key in subkeyList:
                                if tmp_key in tmp_ptr:
                                    tmp_ptr = tmp_ptr[tmp_key]
                                else:
                                    if i == 2: #可用性（`Enabled`）
                                        to_append = value.get(key, True)
                                    elif i == 18: #{ed593c9c}
                                        to_append = value.get(key, False)
                                    else:
                                        to_append = value.get(key, "")
                                    break
                            else:
                                to_append = tmp_ptr
                        elif i <= 46: #字符串常量（String constants）
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                            tooltip_key: str = KiwiAugment_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            if subkey2.endswith("_burn"):
                                spellKey: str = value["RootSpell"]
                                if spellKey in map12_bin_whole:
                                    mSpell: Optional[dict[str, Any]] = map12_bin_whole[spellKey]["mSpell"]
                                else:
                                    mSpell: Optional[dict[str, Any]] = None
                                if mSpell == None:
                                    to_append = ""
                                else:
                                    self.__class__.calculatedVariables.clear()
                                    tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                    to_append = tooltip_burn
                            else:
                                to_append = tooltip_raw
                        elif i == 47: #强化符文显示标签内容（`AugmentDisplayTags_content`）
                            to_append = list(map(lambda x: AugmentDisplayTags[x], value["AugmentDisplayTags"]))
                        elif i == 48: #位阶（`rarityValue`）
                            to_append = augment_rarities[value.get("rarity", 0)]
                        elif i == 49: #根指令对象（`RootSpellObject`）
                            to_append = map12_bin_whole.get(value["RootSpell"], "")
                        else: #其它指令对象（`{40c7b66f}_Object`）
                            to_append = list(map(lambda x: map12_bin_whole.get(x, ""), value.get("{40c7b66f}", [])))
                            if to_append == []:
                                to_append = ""
                    elif i <= 53: #强化符文套装相关键（Augment set related keys）
                        if key1 in augmentSet_map:
                            if i == 51: #强化符文套装列表（`augmentSet`）
                                to_append = augmentSet_map[key1]
                            else: #强化符文套装本地化名称（Augment set localized names）
                                augmentSets: list[str] = augmentSet_map[key1]
                                augmentSetNames: list[str] = []
                                for augmentSet_key in augmentSets:
                                    tooltip_key = map12_bin_whole[augmentSet_key]["{0746ade9}"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 31 else strtable_lol_default
                                    augmentSetNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                to_append = augmentSetNames
                        else:
                            to_append = ""
                    else:
                        if "ResourceResolver" in value and "resourceMap" in map12_bin_whole[value["ResourceResolver"]]:
                            to_append = map12_bin_whole[value["ResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
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
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
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
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    elif i == 16 or i == 17: #强化符文列表本地化信息（Augment list localized text）
                        augmentNames: list[str] = []
                        for augment_key in value["augments"]:
                            tooltip_key = map12_bin_whole[augment_key]["NameTra"]
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if i == 16 else strtable_lol_default
                            augmentNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
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
                                isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                                tooltip_key: str = KiwiAugmentSet_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                if subkey2.endswith("_burn"):
                                    mSpell = rootSpell["mSpell"]
                                    self.__class__.calculatedVariables.clear()
                                    tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
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
        KiwiAugment_statistics_output_order: list[int] = [0, 1, 19, 2, 3, 21, 22, 17, 48, 16, 47, 51, 52, 53, 8, 9, 18, 4, 23, 24, 25, 26, 5, 27, 28, 29, 30, 10, 31, 32, 33, 34, 11, 35, 36, 37, 38, 12, 39, 40, 41, 42, 13, 43, 44, 45, 46, 6, 49, 7, 50, 20, 54, 14, 15]
        KiwiAugment_data_organized: dict[str, list[Any]] = {KiwiAugment_header_keys[i]: KiwiAugment_data_json[KiwiAugment_header_keys[i]] for i in KiwiAugment_statistics_output_order}
        KiwiAugment_df: pandas.DataFrame = pandas.DataFrame(data = KiwiAugment_data_organized)
        KiwiAugment_df = KiwiAugment_df.sort_values(by = "AugmentPlatformId", ascending = True, ignore_index = True)
        logPrint("正在优化海克斯大乱斗强化符文数据框的逻辑值显示……\nOptimizing boolean value display of the Kiwi augment dataframe ...")
        optimize_bool_display(KiwiAugment_df)
        KiwiAugment_df = pandas.concat([pandas.DataFrame([KiwiAugment_header])[KiwiAugment_df.columns], KiwiAugment_df], ignore_index = True)
        self.KiwiAugment_df = KiwiAugment_df
        KiwiAugmentSet_statistics_output_order: list[int] = [0, 1, 3, 10, 11, 4, 12, 13, 14, 15, 19, 20, 21, 22, 23, 5, 16, 17, 6, 18, 9, 24, 7, 25, 8, 2]
        KiwiAugmentSet_data_organized: dict[str, list[Any]] = {KiwiAugmentSet_header_keys[i]: KiwiAugmentSet_data_json[KiwiAugmentSet_header_keys[i]] for i in KiwiAugmentSet_statistics_output_order}
        KiwiAugmentSet_df: pandas.DataFrame = pandas.DataFrame(data = KiwiAugmentSet_data_organized)
        KiwiAugmentSet_df = pandas.concat([pandas.DataFrame([KiwiAugmentSet_header])[KiwiAugmentSet_df.columns], KiwiAugmentSet_df], ignore_index = True)
        self.KiwiAugmentSet_df = KiwiAugmentSet_df
        return 0
    
    def export_augment_data(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出强化符文数据到工作簿中。产生以下工作表：<br>Export augment data to a workbook. The following worksheets are added:
        - 斗魂竞技场强化符文（Cherry Augments）
        - 海克斯大乱斗强化符文（Kiwi Augments）
        - 海克斯大乱斗强化符文套装（Kiwi Augment Set）
        
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
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} CherryAugments" if self.sheet_naming_fold else "斗魂竞技场强化符文（Cherry Augments）"
        sheet2_name: str = f"{self.patch_number} SwarmAugments" if self.sheet_naming_fold else "无尽狂潮强化（Swarm Augments）"
        sheet3_name: str = f"{self.patch_number} KiwiAugments" if self.sheet_naming_fold else "海克斯大乱斗强化符文（Kiwi Augments）"
        sheet4_name: str = f"{self.patch_number} KiwiAugmentSet" if self.sheet_naming_fold else "海克斯大乱斗强化符文套装（Kiwi Augment Set）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.CherryAugment_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    if not self.SwarmAugment_df.empty:
                        addDefaultStyle(self.SwarmAugment_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    if not self.KiwiAugment_df.empty:
                        addDefaultStyle(self.KiwiAugment_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    if not self.KiwiAugmentSet_df.empty:
                        addDefaultStyle(self.KiwiAugmentSet_df).to_excel(excel_writer = writer, sheet_name = sheet4_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
                    if not self.SwarmAugment_df.empty:
                        self.version_df.to_excel(excel_writer = writer, sheet_name = sheet2_name, header = None, index = False, startcol = 0, startrow = 0)
                    if not self.KiwiAugment_df.empty:
                        self.version_df.to_excel(excel_writer = writer, sheet_name = sheet3_name, header = None, index = False, startcol = 0, startrow = 0)
                    if not self.KiwiAugmentSet_df.empty:
                        self.version_df.to_excel(excel_writer = writer, sheet_name = sheet4_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"强化符文数据已导出到{self.wbPath}。按回车键继续。\nAugment data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

class AnvilExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个锻造器提取器对象。<br>Initialize a AnvilExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.anvils_ready: dict[str, bool] = {"map30": False, "kiwi": False}
        self.CherryAnvil_df: pandas.DataFrame = pandas.DataFrame()
        self.KiwiAnvil_df: pandas.DataFrame = pandas.DataFrame()
        
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.anvils_ready = {key: False for key in self.anvils_ready}
    
    def get_anvil_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取锻造器二进制描述数据。包括以下模式：<br>Get binary description data of anvils online. Including the following game modes:
        - 斗魂竞技场（Arena）
        - 海克斯大乱斗（ARAM: Mayhem）
        '''
        logPrint = self.log.logPrint
        #怒火角斗场地图（Rings of Wrath map）
        map30_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map30/map30.bin.json"
        if map30_bin_url in self.__class__.data_cache["online"]:
            self.map30_bin = self.__class__.data_cache["online"][map30_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map30_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == -1:
                    logPrint("怒火角斗场地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                elif status == 404:
                    logPrint("怒火角斗场地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nRings of Wrath map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map30_bin_url))
                time.sleep(3)
                self.init_data_readiness()
                return
            self.map30_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map30_bin_url] = self.map30_bin
        self.anvils_ready["map30"] = True
        if Patch(self.patch_number) >= Patch("16.2"):
            #嚎哭深渊地图（Howling Abyss map）
            map12_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map12/map12.bin.json"
            if map12_bin_url in self.__class__.data_cache["online"]:
                self.KiwiAnvils_bin = self.__class__.data_cache["online"][map12_bin_url]
            else:
                source, status, self.session = requestUrl("GET", map12_bin_url, session = self.session, log = self.log)
                if status != 200:
                    if status == 404:
                        logPrint("嚎哭深渊地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nHowling Abyss map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                        self.KiwiAnvils_bin: dict[str, list[str] | dict[str, Any]] = {}
                    else:
                        logPrint("嚎哭深渊地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nHowling Abyss map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map12_bin_url))
                        time.sleep()
                        self.init_data_readiness()
                        return
                else:
                    self.KiwiAnvils_bin: dict[str, list[str] | dict[str, Any]] = source.json()
                self.__class__.data_cache["online"][map12_bin_url] = self.KiwiAnvils_bin
        else:
            #海克斯大乱斗模式（ARAM: Mayhem mode）
            kiwi_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/augments.bin.json"
            if kiwi_bin_url in self.__class__.data_cache["online"]:
                self.KiwiAnvils_bin = self.__class__.data_cache["online"][kiwi_bin_url]
            else:
                source, status, self.session = requestUrl("GET", kiwi_bin_url, session = self.session, log = self.log)
                if status != 200:
                    if status == -1:
                        logPrint("海克斯大乱斗强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nARAM: Mayhem augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(kiwi_bin_url))
                    elif status == 404:
                        logPrint('海克斯大乱斗强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nARAM: Mayhem augment data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.')
                    time.sleep(3)
                    self.init_data_readiness()
                    return
                self.KiwiAnvils_bin: dict[str, list[str] | dict[str, Any]] = source.json()
                self.__class__.data_cache["online"][kiwi_bin_url] = self.KiwiAnvils_bin
        self.anvils_ready["kiwi"] = True
    
    def read_anvil_data(self, paths: list[str]) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取锻造器二进制描述数据。<br>Get binary description data of anvils offline.
        
        :param paths: 锻造器二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of anvil binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 海克斯大乱斗锻造器（ARAM: Mayhem anvils）
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
            self.map30_bin = self.__class__.data_cache["local"][map30_bin_path]
        else:
            with open(map30_bin_path, "r", encoding = "utf-8") as fp:
                self.map30_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map30_bin_path] = self.map30_bin
        self.anvils_ready["map30"] = True
        #海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        KiwiAnvils_bin_path: str = paths[1]
        if KiwiAnvils_bin_path in self.__class__.data_cache["local"]:
            self.KiwiAnvils_bin = self.__class__.data_cache["local"][KiwiAnvils_bin_path]
        else:
            with open(KiwiAnvils_bin_path, "r", encoding = "utf-8") as fp:
                self.KiwiAnvils_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][KiwiAnvils_bin_path] = self.KiwiAnvils_bin
        self.anvils_ready["kiwi"] = True
    
    def build_anvil_dataframe(self, debug: bool = False, paths: Optional[list[str]] = None) -> int:
        '''
        构建锻造器数据框。<br>Build anvil dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 锻造器二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of anvil binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type paths: list[str]
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not all(self.anvils_ready.values()):
            #获取锻造器信息（Get anvil information）
            logPrint("正在读取锻造器数据……\nReading anvil data ...", print_time = True)
            if debug:
                if paths == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_anvil_data(paths = paths)
            else:
                self.get_anvil_data()
            if not all(self.anvils_ready.values()):
                logPrint("锻造器数据尚未准备就绪！\nAnvil data not prepared!")
                return 2
        #定义数据结构（Define the data structure）
        logPrint("正在构建锻造器数据框……\nBuilding the anvil dataframes ...", print_time = True)
        CherryAnvil_header_keys: list[str] = list(CherryAnvil_header.keys())
        CherryAnvil_data: dict[str, list[Any]] = {key: [] for key in CherryAnvil_header_keys}
        CherryAnvil_data_json: dict[str, list[Any]] = copy.deepcopy(CherryAnvil_data)
        KiwiAnvil_header: dict[str, str] = CherryAnvil_header.copy()
        KiwiAnvil_header_keys: list[str] = list(KiwiAnvil_header.keys())
        KiwiAnvil_data: dict[str, list[Any]] = {key: [] for key in KiwiAnvil_header_keys}
        KiwiAnvil_data_json: dict[str, list[Any]] = copy.deepcopy(KiwiAnvil_data)
        
        #数据整理核心部分（Data organization core part）
        AugmentDisplayTags: dict[int, str] = {0: "己方", 1: "伤害", 2: "综合", 3: "复原力", 4: "速度", 5: "功能", 6: "属性锻造器", 7: "经济"}
        #AugmentDisplayTags: dict[int, str] = {0: "Ally", 1: "Damage", 2: "General", 3: "Resilience", 4: "Speed", 5: "Utility", 6: "Stat Anvil", 7: "Economy"}
        anvil_rarities: dict[int, str] = {0: "白银阶属性", 1: "传说级战士装备", 2: "传说级射手装备", 3: "传说级刺客装备", 4: "传说级法师装备", 5: "传说级坦克装备", 6: "传说级辅助装备", 7: "棱彩装备", 8: "黄金阶属性", 9: "棱彩阶属性"}
        # anvil_rarities: dict[int, str] = {0: "Silver Stat Anvil", 1: "Legendary Fighter Item", 2: "Legendary Marksman Item", 3: "Legendary Assassin Item", 4: "Legendary Mage Item", 5: "Legendary Tank Item", 6: "Legendary Support Item", 7: "Prismatic Item", 8: "Gold Stat Anvil", 9: "Prismatic Stat Anvil"}
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        ##斗魂竞技场锻造器（Arena anvils）
        self.init_mSpells()
        for (key, value) in self.map30_bin.items(): #提取指令字典（Extract spell dictionary）
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        for (key1, value) in self.map30_bin.items():
            if key1 != "__linked" and value["__type"] == "AnvilData":
                for i in range(len(CherryAnvil_header_keys)):
                    key: str = CherryAnvil_header_keys[i]
                    if i == 0: #主键（`Key`）
                        to_append: Any = key1
                    elif i <= 13:
                        if i == 2: #可用性（`Enabled`）
                            to_append = not ("Enabled" in value and not value["Enabled"] or "enabled" in value and not value["enabled"])
                        else:
                            to_append = value.get(key, "")
                    elif i <= 23: #字符串常量（String constants）
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = CherryAnvil_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            if "RootSpell" in value:
                                spellKey: str = value["RootSpell"]
                                if spellKey in self.map30_bin:
                                    mSpell: Optional[dict[str, Any]] = self.map30_bin[spellKey]["mSpell"]
                                else:
                                    mSpell: Optional[dict[str, Any]] = None
                            else:
                                mSpell: Optional[dict[str, Any]] = None
                            if mSpell == None:
                                mSpell = {}
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    elif i == 24: #锻造器显示标签内容（`AugmentDisplayTags_content`）
                        if "AugmentDisplayTags" in value:
                            to_append = list(map(lambda x: AugmentDisplayTags[x], value["AugmentDisplayTags"]))
                        else:
                            to_append = ""
                    elif i == 25: #锻造器位阶（`anvilRarities`）
                        to_append = list(map(lambda x: anvil_rarities[x], value["AnvilTypes"]))
                    else: #根指令对象（`RootSpellObject`）
                        to_append = self.map30_bin.get(value.get("RootSpell", ""), "")
                    CherryAnvil_data[key].append(to_append)
                    CherryAnvil_data_json[key].append(pyobj2json(to_append))
        CherryAnvil_statistics_output_order: list[int] = [0, 1, 13, 2, 3, 14, 15, 12, 25, 11, 24, 7, 8, 4, 16, 17, 18, 19, 5, 20, 21, 22, 23, 6, 26, 9, 10]
        CherryAnvil_data_organized: dict[str, list[Any]] = {CherryAnvil_header_keys[i]: CherryAnvil_data_json[CherryAnvil_header_keys[i]] for i in CherryAnvil_statistics_output_order}
        CherryAnvil_df: pandas.DataFrame = pandas.DataFrame(data = CherryAnvil_data_organized)
        logPrint("正在优化斗魂竞技场锻造器数据框的逻辑值显示……\nOptimizing boolean value display of the Cherry anvil dataframe ...")
        optimize_bool_display(CherryAnvil_df)
        CherryAnvil_df = pandas.concat([pandas.DataFrame([CherryAnvil_header])[CherryAnvil_df.columns], CherryAnvil_df], ignore_index = True)
        self.CherryAnvil_df = CherryAnvil_df
        ##海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        self.init_mSpells()
        for (key, value) in self.KiwiAnvils_bin.items(): #提取指令字典（Extract spell dictionary）
            if key != "__linked" and value["__type"] == "SpellObject":
                self.__class__.mSpells[value["mScriptName"]] = value
        for (key1, value) in self.KiwiAnvils_bin.items():
            if key1 != "__linked" and value["__type"] == "AnvilData":
                for i in range(len(KiwiAnvil_header_keys)):
                    key: str = KiwiAnvil_header_keys[i]
                    if i == 0: #主键（`Key`）
                        to_append: Any = key1
                    elif i <= 13:
                        if i == 2: #可用性（`Enabled`）
                            to_append = value.get(key, True)
                        else:
                            to_append = value.get(key, "")
                    elif i <= 23: #字符串常量（String constants）
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = KiwiAnvil_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            spellKey: str = value["RootSpell"]
                            if spellKey in self.KiwiAnvils_bin:
                                mSpell: Optional[dict[str, Any]] = self.KiwiAnvils_bin[spellKey]["mSpell"]
                            else:
                                mSpell: Optional[dict[str, Any]] = None
                            if mSpell == None:
                                to_append = ""
                            else:
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, reserve_variable = self.reserve_variable, flexibleData = {"mStat_dict_override_version": self.version})
                                to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    elif i == 24: #锻造器显示标签内容（`AugmentDisplayTags_content`）
                        if "AugmentDisplayTags" in value:
                            to_append = list(map(lambda x: AugmentDisplayTags[x], value["AugmentDisplayTags"]))
                        else:
                            to_append = ""
                    elif i == 25: #锻造器位阶（`anvilRarities`）
                        to_append = list(map(lambda x: anvil_rarities[x], value["AnvilTypes"]))
                    else: #根指令对象（`RootSpellObject`）
                        to_append = self.KiwiAnvils_bin.get(value.get("RootSpell", ""), "")
                    KiwiAnvil_data[key].append(to_append)
                    KiwiAnvil_data_json[key].append(pyobj2json(to_append))
        KiwiAnvil_statistics_output_order: list[int] = [0, 1, 13, 2, 3, 14, 15, 12, 25, 11, 24, 7, 8, 4, 16, 17, 18, 19, 5, 20, 21, 22, 23, 6, 26, 9, 10]
        KiwiAnvil_data_organized: dict[str, list[Any]] = {KiwiAnvil_header_keys[i]: KiwiAnvil_data_json[KiwiAnvil_header_keys[i]] for i in KiwiAnvil_statistics_output_order}
        KiwiAnvil_df: pandas.DataFrame = pandas.DataFrame(data = KiwiAnvil_data_organized)
        logPrint("正在优化海克斯大乱斗锻造器数据框的逻辑值显示……\nOptimizing boolean value display of the Kiwi anvil dataframe ...")
        optimize_bool_display(KiwiAnvil_df)
        KiwiAnvil_df = pandas.concat([pandas.DataFrame([KiwiAnvil_header])[KiwiAnvil_df.columns], KiwiAnvil_df], ignore_index = True)
        self.KiwiAnvil_df = KiwiAnvil_df
        return 0
    
    def export_anvil_data(self, debug: bool = False, paths: Optional[list[str]] = None) -> None:
        '''
        导出锻造器数据到工作簿中。产生以下工作表：<br>Export anvil data to a workbook. The following worksheets are added:
        - 斗魂竞技场锻造器（Cherry Anvils）
        - 海克斯大乱斗锻造器（Kiwi Anvils）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param paths: 锻造器二进制描述文件的本地路径列表，按照以下顺序排列：<br>A local path list of anvil binary description files, arranged in the following order:
        
            - 怒火角斗场地图（Rings of Wrath map）
            - 海克斯大乱斗锻造器（ARAM: Mayhem anvils）
        
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
        if self.CherryAnvil_df.empty or self.KiwiAnvil_df.empty:
            status: int = self.build_anvil_dataframe(debug = debug, paths = paths)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} CherryAnvils" if self.sheet_naming_fold else "斗魂竞技场锻造器（Cherry Anvils）"
        sheet2_name: str = f"{self.patch_number} KiwiAnvils" if self.sheet_naming_fold else "海克斯大乱斗锻造器（Kiwi Anvils）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.CherryAnvil_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(self.KiwiAnvil_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet2_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"锻造器数据已导出到{self.wbPath}。按回车键继续。\nAnvil data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

class GoHExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个荣誉嘉宾提取器对象。<br>Initial a GoHExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.GoH_ready: bool = False
        self.GoH_df: pandas.DataFrame = pandas.DataFrame()
        
    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.GoH_ready = False
    
    def get_GoH_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取荣誉嘉宾二进制描述数据。<br>Get binary description data of Guests of Honor online.
        '''
        logPrint = self.log.logPrint
        cherry_bin_url = f"https://raw.communitydragon.org/{self.version}/game/maps/modespecificdata/cherry.bin.json"
        if cherry_bin_url in self.__class__.data_cache["online"]:
            self.cherry_bin = self.__class__.data_cache["online"][cherry_bin_url]
        else:
            source, status, self.session = requestUrl("GET", cherry_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == 404:
                    logPrint("斗魂竞技场强化符文信息获取失败！请检查以下链接的可用性。程序将跳过该信息。\nArena augment data capture failure! Please check the URL availability. The program will skip this information.\n%s" %(cherry_bin_url))
                    self.cherry_bin: dict[str, list[str] | dict[str, Any]] = {}
                else:
                    logPrint('斗魂竞技场强化符文信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nArena augment data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.')
                    time.sleep()
                    self.init_data_readiness()
                    return
            else:
                self.cherry_bin = source.json()
            self.__class__.data_cache["online"][cherry_bin_url] = self.cherry_bin
        self.GoH_ready = True
    
    def read_GoH_data(self, path: str) -> None:
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
        cherry_bin_path: str = path
        if cherry_bin_path in self.__class__.data_cache["local"]:
            self.cherry_bin = self.__class__.data_cache["local"][cherry_bin_path]
        else:
            with open(cherry_bin_path, "r", encoding = "utf-8") as fp:
                self.cherry_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][cherry_bin_path] = self.cherry_bin
        self.GoH_ready = True
    
    def build_GoH_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建荣誉嘉宾数据框。<br>Build GoH dataframe.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 荣誉嘉宾二进制描述文件的本地路径。<br>A local path of GoH binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logPrint = self.log.logPrint
        if not self.GoH_ready:
            #获取荣誉嘉宾信息（Get GoH information）
            logPrint("正在读取荣誉嘉宾数据……\nReading GoH data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_GoH_data(path = path)
            else:
                self.get_GoH_data()
            if not self.GoH_ready:
                logPrint("用于嘉宾数据尚未准备就绪！\nGoH data not prepared!")
                return 2
        
        #定义数据结构（Define the data structure）
        logPrint("正在构建荣誉嘉宾数据框……\nBuilding the GoH dataframes ...", print_time = True)
        GoH_header_keys: list[str] = list(GoH_header.keys())
        GoH_data: dict[str, list[Any]] = {key: [] for key in GoH_header_keys}
        GoH_data_json: dict[str, list[Any]] = copy.deepcopy(GoH_data)
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_lol_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.lolstringtable_target
        strtable_lol_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.lolstringtable_default
        for (key1, value) in self.cherry_bin.items():
            if key1 != "__linked" and value["__type"] == "{05c8aed6}":
                for i in range(len(GoH_header_keys)):
                    key: str = GoH_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i >= 1 and i <= 4: #字符串常量键子键（`{1ff99d7f}`'s subkeys）
                        to_append = value["{1ff99d7f}"][key.split()[1]]
                    elif i == 5 or i == 6:
                        to_append = value[key]
                    else:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_lol_target if useTargetLocale else strtable_lol_default
                        tooltip_key: str = GoH_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            # self.__class__.calculatedVariables.clear()
                            # tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, {}, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable)
                            tooltip_burn = self.tooltipPreparation(tooltip_raw, isCHS = isCHS)
                            tooltip_burn = self.tooltipPostProcessing(tooltip_burn, isCHS = isCHS)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    GoH_data[key].append(to_append)
                    GoH_data_json[key].append(pyobj2json(to_append))
        GoH_statistics_output_order: list[int] = [0, 1, 7, 8, 2, 9, 10, 3, 11, 12, 4, 13, 15, 14, 16, 5, 6]
        GoH_data_organized: dict[str, list[Any]] = {GoH_header_keys[i]: GoH_data_json[GoH_header_keys[i]] for i in GoH_statistics_output_order}
        GoH_df: pandas.DataFrame = pandas.DataFrame(data = GoH_data_organized)
        GoH_df = pandas.concat([pandas.DataFrame([GoH_header])[GoH_df.columns], GoH_df], ignore_index = True)
        self.GoH_df = GoH_df
        return 0
    
    def export_GoH_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出荣誉嘉宾数据到工作簿中。产生以下工作表：<br>Export GoH data to a workbook. The following worksheet is added:
        - 斗魂竞技场荣誉嘉宾（Cherry Guests）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 荣誉嘉宾二进制描述文件的本地路径。<br>A local path of GoH binary description file.
        
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
        if self.GoH_df.empty:
            status: int = self.build_GoH_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} CherryGuests" if self.sheet_naming_fold else "斗魂竞技场荣誉嘉宾（Cherry Guests）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.GoH_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"荣誉嘉宾数据已导出到{self.wbPath}。按回车键继续。\nGoH data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

class TFTExtractor(LoLDataExtractor):
    def __init__(self, extractor: LoLDataExtractor) -> None:
        '''
        初始化一个云顶之弈提取器对象。<br>Initialize a TFTExtractor object.
        
        :param extractor: 父类对象。用于继承其属性。<br>Parent object. Pass it to inherit its attributes.
        :type extractor: LoLDataExtractor
        '''
        self.__dict__.update(extractor.__dict__)
        self.map22_ready: bool = False
        self.TFTSet_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTShop_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTShopContent_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTDropRate_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTStageRound_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTRound_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTPortal_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTEncounterDistribution_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTEncounter_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTUnitProperty_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTCharacterRole_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTItemList_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTItem_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTTraitList_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTTrait_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTPVENPC_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTScript_df: pandas.DataFrame = pandas.DataFrame()
        self.TFTAnnouncement_df: pandas.DataFrame = pandas.DataFrame()

    def init_data_readiness(self) -> None:
        '''
        初始化数据就绪状态。当数据未就绪时，无法构建要导出到工作簿中的数据框。<br>Initialize the data ready status. When data are not ready, dataframes to be exported can't be built.
        '''
        self.map22_ready = False
    
    def get_tft_data(self) -> None: #在线加载——供用户使用（Online loading - For user use）
        '''
        在线获取聚点危机地图二进制描述数据。<br>Get binary description data of Convergence map online.
        '''
        logPrint = self.log.logPrint
        map22_bin_url: str = f"https://raw.communitydragon.org/{self.version}/game/data/maps/shipping/map22/map22.bin.json"
        if map22_bin_url in self.__class__.data_cache["online"]:
            self.map22_bin = self.__class__.data_cache["online"][map22_bin_url]
        else:
            source, status, self.session = requestUrl("GET", map22_bin_url, session = self.session, log = self.log)
            if status != 200:
                if status == -1:
                    logPrint("聚点危机地图信息获取失败！请检查系统网络状况和代理设置。程序即将返回上一层。\nConvergence map data capture failure! Please check the system network condition and agent configuration. The program will return to the last step soon.")
                elif status == 404:
                    logPrint("聚点危机地图信息获取失败！请检查以下链接的可用性。程序即将返回上一层。\nConvergence map data capture failure! Please check the URL availability. The program will return to the last step soon.\n%s" %(map22_bin_url))
                time.sleep(3)
                self.init_data_readiness()
                return
            self.map22_bin: dict[str, list[str] | dict[str, Any]] = source.json()
            self.__class__.data_cache["online"][map22_bin_url] = self.map22_bin
        self.map22_ready = True

    def read_tft_data(self, path: str) -> None: #离线读取——供开发者使用（Offline reading - For developer use）
        '''
        离线获取聚点危机地图二进制描述数据。<br>Get binary description data of Convergence map offline.
        
        :param path: 聚点危机地图二进制描述文件的本地路径。<br>A local path of Convergence map binary description file.
        :type path: str
        '''
        logPrint = self.log.logPrint
        if not os.path.exists(path):
            logPrint(f"以下路径不存在：\nThe following path doesn't exist:\n{path}")
            self.init_data_readiness()
            return
        map22_bin_path: str = path
        if map22_bin_path in self.__class__.data_cache["local"]:
            self.map22_bin = self.__class__.data_cache["local"][map22_bin_path]
        else:
            with open(map22_bin_path, "r", encoding = "utf-8") as fp:
                self.map22_bin: dict[str, list[str] | dict[str, Any]] = json.load(fp)
            self.__class__.data_cache["local"][map22_bin_path] = self.map22_bin
        self.map22_ready = True

    def build_tft_dataframe(self, debug: bool = False, path: Optional[str] = None) -> int:
        '''
        构建云顶之弈数据框。<br>Build TFT dataframes.
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 聚点危机地图二进制描述文件的本地路径。<br>A local path of Convergence map binary description file.
        
            仅在`debug`参数为真时有效。<br>Works only when `debug` is True.
        :type path: str
        :return: 状态码。<br>Status code.
        
            - 0: 成功。<br>Success.
            - 1: 未指定本地文件路径。<br>Local path not specified.
            - 2: 数据未准备就绪。<br>Data not ready.
        :rtype: int
        '''
        logInput = self.log.logInput
        logPrint = self.log.logPrint
        if not "characters_bin_dict" in self.__class__.merged_data_cache:
            logPrint("检测到您尚未获取过云顶之弈角色的二进制描述数据。这将导致相关技能的说明文本无法进行变量代换。（羁绊的说明文本转换依然可用。）是否继续？（输入任意非空字符串以取消导出数据，否则继续。）\nYou haven't got TFT characters' binary description data. This will cause some spells' tooltip not to perform variable substitution. (Trait tooltip transformation will remain available.) Do you want to continue? (Submit any non-empty string to cancel the export, or null to continue.)")
            cancel_str = logInput()
            cancel = bool(cancel_str)
            if cancel:
                logPrint("云顶之弈角色数据尚未准备就绪！\nTFT character data not prepared!")
                return 3
        if not self.map22_ready:
            #获取地图信息（Get map information）
            logPrint("正在读取地图数据……\nReading map data ...", print_time = True)
            if debug:
                if path == None:
                    logPrint("尚未指定本地文件路径！\nLocal path not specified yet!")
                    return 1
                else:
                    self.read_tft_data(path = path)
            else:
                self.get_tft_data()
            if not self.map22_ready:
                logPrint("地图数据尚未准备就绪！\nMap data not prepared!")
                return 2

        #定义数据结构（Define the data structure）
        logPrint("正在构建云顶之弈数据框……\nBuilding the TFT dataframes ...", print_time = True)
        ##云顶之弈赛季（TFT Set）
        TFTSet_header_keys: list[str] = list(TFTSet_header.keys())
        TFTSet_data: dict[str, list[Any]] = {key: [] for key in TFTSet_header_keys}
        TFTSet_data_json: dict[str, list[Any]] = copy.deepcopy(TFTSet_data)
        ##云顶之弈商店（TFT Shop）
        TFTShop_header_keys: list[str] = list(TFTShop_header.keys())
        TFTShop_data: dict[str, list[Any]] = {key: [] for key in TFTShop_header_keys}
        TFTShop_data_json: dict[str, list[Any]] = copy.deepcopy(TFTShop_data)
        ##云顶之弈商店内容（TFT Shop Content）
        TFTShopContent_header_keys: list[str] = list(TFTShopContent_header.keys())
        TFTShopContent_data: dict[str, list[Any]] = {key: [] for key in TFTShopContent_header_keys}
        TFTShopContent_data_json: dict[str, list[Any]] = copy.deepcopy(TFTShopContent_data)
        ##云顶之弈掉率表（TFT Drop Rate）
        TFTDropRate_header_keys: list[str] = list(TFTDropRate_header.keys())
        TFTDropRate_data: dict[str, list[Any]] = {key: [] for key in TFTDropRate_header_keys}
        TFTDropRate_data_json: dict[str, list[Any]] = copy.deepcopy(TFTDropRate_data)
        ##云顶之弈回合阶段（TFT Stage Round）
        TFTStageRound_header_keys: list[str] = list(TFTStageRound_header.keys())
        TFTStageRound_data: dict[str, list[Any]] = {key: [] for key in TFTStageRound_header_keys}
        TFTStageRound_data_json: dict[str, list[Any]] = copy.deepcopy(TFTStageRound_data)
        ##云顶之弈回合（TFT Round）
        TFTRound_header_keys: list[str] = list(TFTRound_header.keys())
        TFTRound_data: dict[str, list[Any]] = {key: [] for key in TFTRound_header_keys}
        TFTRound_data_json: dict[str, list[Any]] = copy.deepcopy(TFTRound_data)
        ##云顶之弈传送门（TFT Portal）
        TFTPortal_header_keys: list[str] = list(TFTPortal_header.keys())
        TFTPortal_data: dict[str, list[Any]] = {key: [] for key in TFTPortal_header_keys}
        TFTPortal_data_json: dict[str, list[Any]] = copy.deepcopy(TFTPortal_data)
        ##云顶之弈开场奇遇（TFT Encounter Distribution）
        TFTEncounterDistribution_header_keys: list[str] = list(TFTEncounterDistribution_header.keys())
        TFTEncounterDistribution_data: dict[str, list[Any]] = {key: [] for key in TFTEncounterDistribution_header_keys}
        TFTEncounterDistribution_data_json: dict[str, list[Any]] = copy.deepcopy(TFTEncounterDistribution_data)
        ##云顶之弈奇遇（TFT Encounter）
        TFTEncounter_header_keys: list[str] = list(TFTEncounter_header.keys())
        TFTEncounter_data: dict[str, list[Any]] = {key: [] for key in TFTEncounter_header_keys}
        TFTEncounter_data_json: dict[str, list[Any]] = copy.deepcopy(TFTEncounter_data)
        ##云顶之弈单位属性（TFT Unit Property）
        TFTUnitProperty_header_keys: list[str] = list(TFTUnitProperty_header.keys())
        TFTUnitProperty_data: dict[str, list[Any]] = {key: [] for key in TFTUnitProperty_header_keys}
        TFTUnitProperty_data_json: dict[str, list[Any]] = copy.deepcopy(TFTUnitProperty_data)
        ##云顶之弈角色定位（TFT Character Role）
        TFTCharacterRole_header_keys: list[str] = list(TFTCharacterRole_header.keys())
        TFTCharacterRole_data: dict[str, list[Any]] = {key: [] for key in TFTCharacterRole_header_keys}
        TFTCharacterRole_data_json: dict[str, list[Any]] = copy.deepcopy(TFTCharacterRole_data)
        ##云顶之弈装备列表（TFT Item List）
        TFTItemList_header_keys: list[str] = list(TFTItemList_header.keys())
        TFTItemList_data: dict[str, list[Any]] = {key: [] for key in TFTItemList_header_keys}
        TFTItemList_data_json: dict[str, list[Any]] = copy.deepcopy(TFTItemList_data)
        ##云顶之弈装备（TFT Item）
        TFTItem_header_keys: list[str] = list(TFTItem_header.keys())
        TFTItem_data: dict[str, list[Any]] = {key: [] for key in TFTItem_header_keys}
        TFTItem_data_json: dict[str, list[Any]] = copy.deepcopy(TFTItem_data)
        ##云顶之弈羁绊列表（TFT Trait List）
        TFTTraitList_header_keys: list[str] = list(TFTTraitList_header.keys())
        TFTTraitList_data: dict[str, list[Any]] = {key: [] for key in TFTTraitList_header_keys}
        TFTTraitList_data_json: dict[str, list[Any]] = copy.deepcopy(TFTTraitList_data)
        ##云顶之弈羁绊（TFT Trait）
        TFTTrait_header_keys: list[str] = list(TFTTrait_header.keys())
        TFTTrait_data: dict[str, list[Any]] = {key: [] for key in TFTTrait_header_keys}
        TFTTrait_data_json: dict[str, list[Any]] = copy.deepcopy(TFTTrait_data)
        ##云顶之弈电脑玩家英雄（TFT PVE NPC）
        TFTPVENPC_header_keys: list[str] = list(TFTPVENPC_header.keys())
        TFTPVENPC_data: dict[str, list[Any]] = {key: [] for key in TFTPVENPC_header_keys}
        TFTPVENPC_data_json: dict[str, list[Any]] = copy.deepcopy(TFTPVENPC_data)
        ##云顶之弈脚本（TFT Script）
        TFTScript_header_keys: list[str] = list(TFTScript_header.keys())
        TFTScript_data: dict[str, list[Any]] = {key: [] for key in TFTScript_header_keys}
        TFTScript_data_json: dict[str, list[Any]] = copy.deepcopy(TFTScript_data)
        ##云顶之弈通告（TFT Announcement）
        TFTAnnouncement_header_keys: list[str] = list(TFTAnnouncement_header.keys())
        TFTAnnouncement_data: dict[str, list[Any]] = {key: [] for key in TFTAnnouncement_header_keys}
        TFTAnnouncement_data_json: dict[str, list[Any]] = copy.deepcopy(TFTAnnouncement_data)
        
        #构建映射关系（Build reflections）
        ##通过角色数据构建从指令名到到指令的映射（Build the map from a SpellObject name to a spell through character data）
        if "characters_bin_dict" in self.__class__.merged_data_cache:
            characters_bin_dict = self.__class__.merged_data_cache["characters_bin_dict"]
            characters_bin: dict[str, list[str] | dict[str, Any]] = {}
            for alias in characters_bin_dict:
                characters_bin |= characters_bin_dict[alias]
            self.init_mSpells()
            for (key, value) in characters_bin.items():
                if key != "__linked" and value["__type"] == "SpellObject":
                    self.__class__.mSpells[value["mScriptName"]] = value
                    tmp_ptr = value
                    subkeyList: list[str] = ["mSpell", "mClientData", "mTooltipData", "mLocKeys", "keyTooltip"]
                    for tmp_key in subkeyList:
                        if tmp_key in tmp_ptr:
                            tmp_ptr = tmp_ptr[tmp_key]
                        else:
                            break
                    else:
                        self.__class__.Spell_tooltip_map[tmp_ptr] = value
        TFTItemMap: dict[str, dict[str, Any]] = {} #构建从装备名称到装备对象的映射（Build the map from item's `mName` key's value to a TftItemData object）
        for (key, value) in self.map22_bin.items():
            if key != "__linked" and value["__type"] == "TftUnitPropertyDefinition":
                self.__class__.TFTUnitPropertyMap[value["name"]] = value
            elif key != "__linked" and value["__type"] == "TftTraitData":
                self.__class__.TFTTraitMap[value["mName"]] = value
            elif key != "__linked" and value["__type"] == "ScriptDataObject":
                self.__class__.TFTScriptDataMap[value["mName"]] = value
            elif key != "__linked" and value["__type"] == "TftItemData":
                TFTItemMap[value["mName"]] = value
        
        #准备附加数据（Prepare supplemental data）
        flexibleData: dict[str, dict[str, Any]] = {}
        flexibleData["map22_bin"] = self.map22_bin
        
        #数据整理核心部分（Data organization core part）
        pStrConst: re.Pattern[str] = re.compile(r"_content_\w*")
        strtable_tft_target: dict[str, int | dict[str, str]] = self.mainstringtable_target if self.strtable_organize_manner == 2 else self.tftstringtable_target
        strtable_tft_default: dict[str, int | dict[str, str]] = self.mainstringtable_default if self.strtable_organize_manner == 2 else self.tftstringtable_default
        for (key1, value) in self.map22_bin.items():
            if key1 != "__linked" and value["__type"] == "TFTSetData": #云顶之弈赛季（TFT Set）
                for i in range(len(TFTSet_header_keys)):
                    key: str = TFTSet_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 130:
                        if i <= 88:
                            tmp_ptr = value
                            subkeyList: list[str] = key.split()
                            for tmp_key in subkeyList:
                                if tmp_key in tmp_ptr:
                                    tmp_ptr = tmp_ptr[tmp_key]
                                else:
                                    if i == 80: #{bdb41827}
                                        to_append = True
                                    else:
                                        to_append = ""
                                    break
                            else:
                                to_append = tmp_ptr
                        elif i >= 89 and i <= 126 and i != 97 and i != 98 or i == 129 or i == 130:
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            flexibleData["mStat_dict_override_version"] = self.version
                            flexibleData["tftstringtable"] = strtable_locale
                            flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            tooltip_key: str = TFTSet_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            if subkey2.endswith("_burn"):
                                self.__class__.calculatedVariables.clear()
                                tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                                to_append = tooltip_burn
                            else:
                                to_append = tooltip_raw
                        elif i == 97 or i == 98: #本地化特定赛季羁绊显示名（Localized `InfoNubData Trait mDisplayNameTra`）
                            if "InfoNubData" in value and "Trait" in value["InfoNubData"] and value["InfoNubData"]["Trait"] in self.map22_bin:
                                trait = self.map22_bin[value["InfoNubData"]["Trait"]]
                                if "mDisplayNameTra" in trait:
                                    tooltip_key = trait["mDisplayNameTra"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 97 else strtable_tft_default
                                    to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                else:
                                    to_append = trait["mName"]
                            else:
                                to_append = ""
                        elif i == 127: #装备边框配置信息（`{47f76f2b} content`）
                            if "{47f76f2b}" in value:
                                to_append = {key: self.map22_bin.get(value, value) for (key, value) in value["{47f76f2b}"].items()}
                            else:
                                to_append = ""
                        else: #电脑玩家难度配置（`BotSkillData SkillAxes`）
                            if "BotSkillData" in value:
                                to_append = {key: self.map22_bin[value]["SkillAxes"] if value in self.map22_bin else value for (key, value) in value["BotSkillData"].items()}
                            else:
                                to_append = ""
                    elif i <= 133: #角色列表（Character list）
                        subkey = key.split()[0]
                        if subkey in value:
                            to_append = [(self.map22_bin[_]["characters"] if _ in self.map22_bin else _) for _ in value[subkey]]
                        else:
                            to_append = ""
                    elif i == 134: #羁绊变异详细信息（`{0a8ae70b} TraitAssignments`）
                        if "{0a8ae70b}" in value:
                            to_append = [(self.map22_bin[_]["TraitAssignments"] if _ in self.map22_bin else _) for _ in value["{0a8ae70b}"]]
                        else:
                            to_append = ""
                    elif i <= 137: #云顶之弈商店相关键（TFT shop data related keys）
                        if "ShopDataLists" in value:
                            ShopDataList_keys = value["ShopDataLists"]
                            ShopDataLists: list[list[str] | str] = []
                            for ShopDataList_key in ShopDataList_keys:
                                if ShopDataList_key in self.map22_bin:
                                    ShopDataLists.append(self.map22_bin[ShopDataList_key]["ShopDatas"])
                                else:
                                    ShopDataLists.append(ShopDataList_key)
                            if i == 135: #云顶之弈商店信息（`ShopDataLists ShopData`）
                                to_append = ShopDataLists
                            else: #本地化云顶之弈商品名称（Localized TFT shopdata names）
                                ShopDataLists_names: list[list[str] | str] = []
                                for ShopDataList in ShopDataLists:
                                    if isinstance(ShopDataList, str): #聚点危机地图二进制描述数据中未找到主键（Key not found in Convergence map's binary description data）
                                        ShopDataLists_names.append(ShopDataList)
                                    else:
                                        ShopDataList_names: list[str] = []
                                        for ShopData_key in ShopDataList:
                                            if ShopData_key in self.map22_bin and "mDisplayNameTra" in self.map22_bin[ShopData_key]:
                                                ShopData_displayName_key: str = self.map22_bin[ShopData_key]["mDisplayNameTra"]
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 136 else strtable_tft_default
                                                ShopDataList_names.append(self.get_strtable_value(strtable_locale, ShopData_displayName_key, default = ShopData_displayName_key))
                                            else:
                                                ShopDataList_names.append(ShopData_key)
                                        ShopDataLists_names.append(ShopDataList_names)
                                to_append = ShopDataLists_names
                        else:
                            to_append = ""
                    elif i == 138: #各星级弈子供应信息（`ShopContentData TierBags`）
                        if "ShopContentData" in value and value["ShopContentData"] in self.map22_bin and "TierBags" in self.map22_bin[value["ShopContentData"]]:
                            to_append = self.map22_bin[value["ShopContentData"]]["TierBags"]
                        else:
                            to_append = ""
                    elif i == 139: #回合阶段代码（`StageRoundData stages`）
                        if "StageRoundData" in value and value["StageRoundData"] in self.map22_bin:
                            to_append = self.map22_bin[value["StageRoundData"]]["stages"]
                        else:
                            to_append = ""
                    elif i <= 142: #传送门列表（Portal lists）
                        if "{46bf1dcb}" in value and value["{46bf1dcb}"] in self.map22_bin:
                            portalLists = self.map22_bin[value["{46bf1dcb}"]]
                            if i == 140 or i == 141: #地区传送门名称列表（Region portals' localized name list）
                                portalList = portalLists["RegionPortals"]
                                regionNames: list[str] = []
                                for portal_key in portalList:
                                    if portal_key in self.map22_bin:
                                        regionName_key = self.map22_bin[portal_key]["RegionTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 140 else strtable_tft_default
                                        regionNames.append(self.get_strtable_value(strtable_locale, regionName_key, default = regionName_key))
                                    else:
                                        regionNames.append(portal_key)
                                to_append = regionNames
                            else:
                                to_append = portalLists["{48a30fbc}"]
                        else:
                            to_append = ""
                    elif i == 143 or i == 144: #奇遇（Encounter）
                        if "EncounterList" in value and value["EncounterList"] in self.map22_bin:
                            EncounterLists = self.map22_bin[value["EncounterList"]]
                            if i == 143: #开场奇遇事件名称列表（`EncounterList {23c80d88} names`）
                                EncounterDistributionList = EncounterLists["{23c80d88}"]
                                EncounterDistributionNames: list[str] = []
                                for EncounterDistribution_key in EncounterDistributionList:
                                    if EncounterDistribution_key in self.map22_bin:
                                        EncounterDistributionNames.append(self.map22_bin[EncounterDistribution_key]["name"])
                                    else:
                                        EncounterDistributionNames.append(EncounterDistribution_key)
                                to_append = EncounterDistributionNames
                            else: #奇遇事件名称列表（`EncounterList Encounters names`）
                                EncounterList = EncounterLists["Encounters"]
                                EncounterNames: list[str] = []
                                for Encounter_key in EncounterList:
                                    if Encounter_key in self.map22_bin:
                                        EncounterNames.append(self.map22_bin[Encounter_key]["name"])
                                    else:
                                        EncounterNames.append(Encounter_key)
                                to_append = EncounterNames
                        else:
                            to_append = ""
                    elif i <= 147: #赛博装备（Cybernatic items）
                        if "{032ade10}" in value:
                            CybernaticItemLists = value["{032ade10}"]
                            CybernaticItem_keys: dict[str, list[str]] = {}
                            CybernaticItem_names: dict[str, list[str]] = {}
                            for (CybernaticItemList_category, CybernaticItemList_key) in CybernaticItemLists.items():
                                if CybernaticItemList_key in self.map22_bin:
                                    CybernaticItem_keys[CybernaticItemList_category] = list(map(lambda x: x["data"], self.map22_bin[CybernaticItemList_key]["{9a7587b2}"]))
                                    if i == 146 or i == 147: #本地化赛博装备名称（Localized Cybernatic item names）
                                        itemNames: list[str] = []
                                        for item_key in CybernaticItem_keys[CybernaticItemList_category]:
                                            if item_key in self.map22_bin:
                                                cItem = self.map22_bin[item_key]
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 146 else strtable_tft_default
                                                if "mDisplayNameTra" in cItem:
                                                    itemNames.append(self.get_strtable_value(strtable_locale, cItem["mDisplayNameTra"], default = cItem["mDisplayNameTra"]))
                                                else:
                                                    itemNames.append(cItem["mName"])
                                            else:
                                                itemNames.append(item_key)
                                        CybernaticItem_names[CybernaticItemList_category] = itemNames
                                else:
                                    CybernaticItem_keys[CybernaticItemList_category] = CybernaticItemList_key
                            if i == 145: #赛博装备键（`{032ade10} {9a7587b2}`）
                                to_append = CybernaticItem_keys
                            else: #本地化赛博装备名称（Localized Cybernatic item names）
                                to_append = CybernaticItem_names
                        else:
                            to_append = ""
                    elif i == 148: #视觉特效资源映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    elif i == 149: #其它资源解析器映射字典（`{f99705af} resourceMap`）
                        if "{f99705af}" in value:
                            resolverList: list[str | dict[str, str]] = []
                            for ResourceResolver_key in value["{f99705af}"]:
                                if ResourceResolver_key in self.map22_bin and "resourceMap" in self.map22_bin[ResourceResolver_key]:
                                    resolverList.append(self.map22_bin[ResourceResolver_key]["resourceMap"])
                                else:
                                    resolverList.append(ResourceResolver_key)
                            to_append = resolverList
                        else:
                            to_append = ""
                    elif i <= 161: #六费卡指令（`{c8369109}`'s subkeys）
                        if "{c8369109}" in value and value["{c8369109}"] in self.map22_bin:
                            tooltipData = self.map22_bin[value["{c8369109}"]]
                            if i <= 153:
                                subkey = key.split()[1]
                                to_append = tooltipData.get(subkey, "")
                            else:
                                subkey2: str = pStrConst.search(key).group()
                                subkey1: str = key.replace(subkey2, "")
                                useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                                isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                                flexibleData["mStat_dict_override_version"] = self.version
                                flexibleData["tftstringtable"] = strtable_locale
                                flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                                tooltip_key: str = TFTSet_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                if subkey2.endswith("_burn"):
                                    self.__class__.calculatedVariables.clear()
                                    tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                                    to_append = tooltip_burn
                                else:
                                    to_append = tooltip_raw
                        else:
                            to_append = ""
                    elif i == 162: #六费单位音频单元（`{235a8995} bankUnits`）
                        if "{235a8995}" in value and value["{235a8995}"] in self.map22_bin:
                            to_append = self.map22_bin[value["{235a8995}"]]["bankUnits"]
                        else:
                            to_append = ""
                    elif i <= 168: #默认棋盘子键（`{52e4eea2}`'s subkeys）
                        if "{52e4eea2}" in value and value["{52e4eea2}"] in self.map22_bin:
                            tmp_ptr = self.map22_bin[value["{52e4eea2}"]]
                            subkeyList: list[str] = key.split()[1:]
                            for tmp_key in subkeyList:
                                if tmp_key in tmp_ptr:
                                    tmp_ptr = tmp_ptr[tmp_key]
                                else:
                                    to_append = ""
                                    break
                            else:
                                to_append = tmp_ptr
                        else:
                            to_append = ""
                    elif i == 169: #签名格信息（`{876a220d} {7c666488}`）
                        if "{876a220d}" in value and value["{876a220d}"] in self.map22_bin:
                            to_append = self.map22_bin[value["{876a220d}"]]["{7c666488}"]
                        else:
                            to_append = ""
                    elif i <= 244: #加农炮击子键（`{c58ff569}`'s subkeys）
                        if "{c58ff569}" in value:
                            if i <= 206:
                                tmp_ptr = value["{c58ff569}"]
                                subkeyList: list[str] = key.split()[1:]
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
                                isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                                tooltip_key: str = TFTSet_data[subkey1][-1]
                                tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                                to_append = tooltip_raw
                        else:
                            to_append = ""
                    else: #人机对战敌方单位子键（`{049d68aa}`'s subkeys）
                        if "{049d68aa}" in value and value["{049d68aa}"] in self.map22_bin:
                            if i == 245 or i == 246:
                                subkey = key.split()[1]
                                to_append = self.map22_bin[value["{049d68aa}"]][subkey]
                            else: #人机对战敌方单位名称列表（`{049d68aa} {d1edd5db} names`）
                                to_append = list(map(lambda x: self.map22_bin[x]["name"] if x in self.map22_bin else x, self.map22_bin[value["{049d68aa}"]]["{d1edd5db}"]))
                        else:
                            to_append = ""
                    TFTSet_data[key].append(to_append)
                    TFTSet_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftShopData": #云顶之弈商店（TFT Shop）
                for i in range(len(TFTShop_header_keys)):
                    key: str = TFTShop_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 15:
                        to_append = value.get(key, "")
                    else:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTShop_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if i == 22 or i == 23: #本地化描述。往往是一个英雄的技能（Localized description, usually of a champion spell）
                            if "characters_bin_dict" in self.__class__.merged_data_cache:
                                if tooltip_key != "" and tooltip_key in self.__class__.Spell_tooltip_map:
                                    mSpell = self.__class__.Spell_tooltip_map[tooltip_key].get("mSpell")
                                else:
                                    mSpell = value
                            else:
                                mSpell = value
                        else:
                            mSpell = value
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, mSpell, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    TFTShop_data[key].append(to_append)
                    TFTShop_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftShopContentData": #云顶之弈商店内容（TFT Shop Content）
                if "TierBags" in value:
                    for TierBagIndex in range(len(value["TierBags"])):
                        for TierBagEntryIndex in range(len(value["TierBags"][TierBagIndex]["TierBagEntries"])):
                            TierBagEntry = value["TierBags"][TierBagIndex]["TierBagEntries"][TierBagEntryIndex]
                            for i in range(len(TFTShopContent_header_keys)):
                                key: str = TFTShopContent_header_keys[i]
                                if i == 0: #主键（`key`）
                                    to_append: Any = key1
                                elif i == 1: #星级背包索引（`TierBagIndex`）
                                    to_append = TierBagIndex
                                elif i == 2: #星级背包记录索引（`TierBagEntryIndex`）
                                    to_append = TierBagEntryIndex
                                elif i <= 4: #商品键（`ShopData`）
                                    to_append = TierBagEntry.get(key, "")
                                else: #本地化商品名称（Localized shop item names）
                                    ShopData_key = TierBagEntry["ShopData"]
                                    if TierBagEntry["ShopData"] in self.map22_bin:
                                        ShopData = self.map22_bin[ShopData_key]
                                        if "mDisplayNameTra" in ShopData:
                                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 5 else strtable_tft_default
                                            tooltip_key: str = ShopData["mDisplayNameTra"]
                                            to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                        else:
                                            to_append = ShopData["mName"]
                                    else:
                                        to_append = ShopData_key
                                TFTShopContent_data[key].append(to_append)
                                TFTShopContent_data_json[key].append(pyobj2json(to_append))
                else:
                    for i in range(len(TFTShopContent_header_keys)):
                        key: str = TFTShopContent_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        else:
                            to_append = ""
                        TFTShopContent_data[key].append(to_append)
                        TFTShopContent_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftDropRateTable": #云顶之弈掉率表（TFT Drop Rate）
                for level_index in range(len(value["mDropRatesByLevel"])):
                    dropRates = value["mDropRatesByLevel"][level_index]
                    for i in range(len(TFTDropRate_header_keys)):
                        key: str = TFTDropRate_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #弈士等级（`mDropRatesByLevel Level`）
                            to_append = level_index + 1
                        elif i == 2: #卡费等第数量（`{4f7d4b97}`）
                            to_append = value.get("{4f7d4b97}", "")
                        elif i == 3: #卡费掉率（`{bcf1e6a6}`）
                            to_append = dropRates["{bcf1e6a6}"]
                        else: #卡费掉率字符串（`{bcf1e6a6}_burn`）
                            to_append = self.burnValueList(dropRates["{bcf1e6a6}"])
                        TFTDropRate_data[key].append(to_append)
                        TFTDropRate_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftStageRoundData": #云顶之弈回合阶段（TFT Stage Round）
                for stage_index in range(len(value["stages"])):
                    for round_index in range(len(value["stages"][stage_index]["mRounds"])):
                        mRound_key = value["stages"][stage_index]["mRounds"][round_index]
                        for i in range(len(TFTStageRound_header_keys)):
                            key: str = TFTStageRound_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i == 1: #阶段序号（`stageIndex`）
                                to_append = stage_index + 1
                            elif i == 2: #回合列表（`roundIndex`）
                                to_append = round_index + 1
                            elif i == 3: #回合字符串（`round_burn`）
                                to_append = f"{stage_index + 1}-{round_index + 1}"
                            elif i == 4: #回合代码（`round`）
                                to_append = mRound_key
                            else: #本地化回合名称（Localized round name）
                                if mRound_key in self.map22_bin and "mDisplayNameTra" in self.map22_bin[mRound_key]:
                                    tooltip_key: str = self.map22_bin[mRound_key]["mDisplayNameTra"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 5 else strtable_tft_default
                                    to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                else:
                                    to_append = ""
                            TFTStageRound_data[key].append(to_append)
                            TFTStageRound_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTRoundData": #云顶之弈回合（TFT Round）
                for i in range(len(TFTRound_header_keys)):
                    key: str = TFTRound_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 46:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i in {12, 16, 19, 21, 22, 27, 31, 36, 40, 42}:
                                    to_append = False
                                else:
                                    to_append = ""
                                break
                        else:
                            to_append = tmp_ptr
                    else:
                        if i == 51 or i == 52: #本地化状态说明文本（Localized state tooltips）
                            if "mStateTooltipsTra" in value:
                                stateTooltips: dict[str, str] = {}
                                for (state, tooltip_key) in value["mStateTooltipsTra"].items():
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 51 else strtable_tft_default
                                    stateTooltips[state] = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                                to_append = stateTooltips
                            else:
                                to_append = ""
                        else:
                            subkey2: str = pStrConst.search(key).group()
                            subkey1: str = key.replace(subkey2, "")
                            useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                            isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                            tooltip_key: str = TFTRound_data[subkey1][-1]
                            tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                            to_append = tooltip_raw
                    TFTRound_data[key].append(to_append)
                    TFTRound_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{b3f382ff}": #云顶之弈传送门（TFT Portal）
                for i in range(len(TFTPortal_header_keys)):
                    key: str = TFTPortal_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 14:
                        if key in value:
                            to_append = value[key]
                        else:
                            if i == 6 or i == 13:
                                to_append = False
                            else:
                                to_append = ""
                    elif i <= 24:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTPortal_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    else: #本地化独特强化符文显示名（Localized uniue augments' displayName）
                        if "{ca451de5}" in value:
                            uniqueAugment_keys: list[str] = value["{ca451de5}"]
                            uniqueAugment_names: list[str] = []
                            for uniqueAugment_key in uniqueAugment_keys:
                                if uniqueAugment_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[uniqueAugment_key]:
                                        tooltip_key: str = self.map22_bin[uniqueAugment_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 25 else strtable_tft_default
                                        uniqueAugment_names.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        uniqueAugment_names.append(self.map22_bin[uniqueAugment_key]["mName"])
                                else:
                                    uniqueAugment_names.append(uniqueAugment_key)
                            to_append = uniqueAugment_names
                        else:
                            to_append = ""
                    TFTPortal_data[key].append(to_append)
                    TFTPortal_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{42c94584}": #云顶之弈开场奇遇（TFT Encounter Distribution）
                for i in range(len(TFTEncounterDistribution_header_keys)):
                    key: str = TFTEncounterDistribution_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        to_append = value.get(key, "")
                    TFTEncounterDistribution_data[key].append(to_append)
                    TFTEncounterDistribution_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftEncounterData": #云顶之弈奇遇（TFT Encounter）
                for i in range(len(TFTEncounter_header_keys)):
                    key: str = TFTEncounter_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 12:
                        to_append = value.get(key, "")
                    elif i <= 14: #排除的强化符文本地化名称（Localized excluded augment names）
                        if "ExcludedAugments" in value:
                            ExcludedAugmentNames: list[str] = []
                            for augment_key in value["ExcludedAugments"]:
                                if augment_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[augment_key]:
                                        tooltip_key: str = self.map22_bin[augment_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 13 else strtable_tft_default
                                        ExcludedAugmentNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        ExcludedAugmentNames.append(self.map22_bin[augment_key]["mName"])
                                else:
                                    ExcludedAugmentNames.append(augment_key)
                            to_append = ExcludedAugmentNames
                        else:
                            to_append = ""
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTEncounter_data[key].append(to_append)
                    TFTEncounter_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftUnitPropertyDefinition": #云顶之弈单位属性（TFT Unit Property）
                for i in range(len(TFTUnitProperty_header_keys)):
                    key: str = TFTUnitProperty_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    else:
                        tmp_ptr = value
                        subkeyList: list[str] = key.split()
                        for tmp_key in subkeyList:
                            if tmp_key in tmp_ptr:
                                tmp_ptr = tmp_ptr[tmp_key]
                            else:
                                if i == 2: #DefaultValue {82e959c3}
                                    to_append = False
                                elif i == 8: #属性继承（`IsCloneable`）
                                    to_append = True
                                else:
                                    to_append = tmp_ptr
                                break
                        else:
                            to_append = tmp_ptr
                    TFTUnitProperty_data[key].append(to_append)
                    TFTUnitProperty_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTCharacterRoleData": #云顶之弈角色定位（TFT Character Role）
                for i in range(len(TFTCharacterRole_header_keys)):
                    key: str = TFTCharacterRole_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 9:
                        to_append = value.get(key, "")
                    elif i <= 25:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTCharacterRole_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    else: #本地化装备显示名（Localized item displayNames）
                        itemNames: list[str] = []
                        for item_key in value["items"]:
                            if item_key in self.map22_bin:
                                if "mDisplayNameTra" in self.map22_bin[item_key]:
                                    tooltip_key: str = self.map22_bin[item_key]["mDisplayNameTra"]
                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 26 else strtable_tft_default
                                    itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                else:
                                    itemNames.append(self.map22_bin[item_key]["mName"])
                            else:
                                itemNames.append(item_key)
                        to_append = itemNames
                    TFTCharacterRole_data[key].append(to_append)
                    TFTCharacterRole_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTItemList": #云顶之弈装备列表（TFT Item List）
                for i in range(len(TFTItemList_header_keys)):
                    key: str = TFTItemList_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 3:
                        to_append = value.get(key, "")
                    elif i <= 5: #本地化装备名称（Localized item names）
                        if "mItems" in value:
                            itemNames: list[str] = []
                            for item_key in value["mItems"]:
                                if item_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[item_key]:
                                        tooltip_key: str = self.map22_bin[item_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 4 else strtable_tft_default
                                        itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        itemNames.append(self.map22_bin[item_key]["mName"])
                                else:
                                    itemNames.append(item_key)
                            to_append = itemNames
                        else:
                            to_append = ""
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTItemList_data[key].append(to_append)
                    TFTItemList_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftItemData": #云顶之弈装备（TFT Item）
                for i in range(len(TFTItem_header_keys)):
                    key: str = TFTItem_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 26:
                        if key in value:
                            to_append = value[key]
                        else:
                            if i == 2 or i == 14:
                                to_append = False
                            else:
                                to_append = ""
                    elif i <= 36:
                        subkey = key.split()[0]
                        if subkey in value:
                            if i == 29 or i == 30: #其它合成方案装备构件本地化名称（Alternative composition localized names）
                                AlternativeCompositions_names: list[list[str]] = []
                                for alternativeComposition in value["mAlternativeCompositions"]:
                                    if "mComponents" in alternativeComposition:
                                        itemNames: list[str] = []
                                        for item_key in alternativeComposition["mComponents"]:
                                            if item_key in self.map22_bin:
                                                if "mDisplayNameTra" in self.map22_bin[item_key]:
                                                    tooltip_key: str = self.map22_bin[item_key]["mDisplayNameTra"]
                                                    strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 29 else strtable_tft_default
                                                    itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                                else:
                                                    itemNames.append(self.map22_bin[item_key]["mName"])
                                            else:
                                                itemNames.append(item_key)
                                        AlternativeCompositions_names.append(itemNames)
                                    else:
                                        AlternativeCompositions_names.append([])
                                to_append = AlternativeCompositions_names
                            else:
                                mSubkey_names: list[str] = []
                                for mValue_key in value[subkey]:
                                    if mValue_key in self.map22_bin:
                                        if "mDisplayNameTra" in self.map22_bin[mValue_key]:
                                            tooltip_key: str = self.map22_bin[mValue_key]["mDisplayNameTra"]
                                            strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if key.endswith("_zh") else strtable_tft_default
                                            mSubkey_names.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                        else:
                                            mSubkey_names.append(self.map22_bin[mValue_key]["mName"])
                                    else:
                                        mSubkey_names.append(mValue_key)
                                to_append = mSubkey_names
                        else:
                            to_append = ""
                    elif i <= 40:
                        subkey = key.split()[0]
                        if subkey in value and value[subkey] in self.map22_bin:
                            if "mDisplayNameTra" in self.map22_bin[value[subkey]]:
                                tooltip_key: str = self.map22_bin[value[subkey]]["mDisplayNameTra"]
                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if key.endswith("_zh") else strtable_tft_default
                                to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key)
                            else:
                                to_append = self.map22_bin[value[subkey]]["mName"]
                        else:
                            to_append = ""
                    elif i <= 48:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTItem_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTItem_data[key].append(to_append)
                    TFTItem_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftTraitList": #云顶之弈羁绊列表（TFT Trait List）
                for i in range(len(TFTTraitList_header_keys)):
                    key: str = TFTTraitList_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 2:
                        to_append = value.get(key, "")
                    elif i <= 4: #本地化羁绊名称（Localized trait names）
                        if "mTraits" in value:
                            traitNames: list[str] = []
                            for trait_key in value["mTraits"]:
                                if trait_key in self.map22_bin:
                                    if "mDisplayNameTra" in self.map22_bin[trait_key]:
                                        tooltip_key: str = self.map22_bin[trait_key]["mDisplayNameTra"]
                                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 3 else strtable_tft_default
                                        traitNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                    else:
                                        traitNames.append(self.map22_bin[trait_key]["mName"])
                                else:
                                    traitNames.append(trait_key)
                            to_append = traitNames
                        else:
                            to_append = ""
                    else: #视觉效果资源解析器映射字典（`VfxResourceResolver resourceMap`）
                        if "VfxResourceResolver" in value and value["VfxResourceResolver"] in self.map22_bin and "resourceMap" in self.map22_bin[value["VfxResourceResolver"]]:
                            to_append = self.map22_bin[value["VfxResourceResolver"]]["resourceMap"]
                        else:
                            to_append = ""
                    TFTTraitList_data[key].append(to_append)
                    TFTTraitList_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TftTraitData": #云顶之弈羁绊（TFT Trait）
                for i in range(len(TFTTrait_header_keys)):
                    key: str = TFTTrait_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 10:
                        if key in value:
                            to_append = value[key]
                        else:
                            if i == 10:
                                to_append = False
                            else:
                                to_append = ""
                    else:
                        subkey2: str = pStrConst.search(key).group()
                        subkey1: str = key.replace(subkey2, "")
                        useTargetLocale: bool = subkey2.split("_")[2] == "zh"
                        isCHS: bool = useTargetLocale and self.locale in self.CHS_PUNCMARKS
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        flexibleData["mStat_dict_override_version"] = self.version
                        flexibleData["tftstringtable"] = strtable_locale
                        flexibleData["stringtable"] = strtable_tft_target if useTargetLocale else strtable_tft_default
                        tooltip_key: str = TFTTrait_data[subkey1][-1]
                        tooltip_raw: str = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                        if subkey2.endswith("_burn"):
                            self.__class__.calculatedVariables.clear()
                            tooltip_burn = self.tooltipConvert(tooltip_raw, strtable_locale, value, isCHS = isCHS, enableModeOverride = False, reserve_variable = self.reserve_variable, flexibleData = flexibleData)
                            to_append = tooltip_burn
                        else:
                            to_append = tooltip_raw
                    TFTTrait_data[key].append(to_append)
                    TFTTrait_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "{d545dcdd}": #云顶之弈电脑玩家英雄（TFT PVE NPC）
                if "champions" in value:
                    for champion_index in range(len(value["champions"])):
                        champion = value["champions"][champion_index]
                        for i in range(len(TFTPVENPC_header_keys)):
                            key: str = TFTPVENPC_header_keys[i]
                            if i == 0: #主键（`key`）
                                to_append: Any = key1
                            elif i == 1: #代码（`name`）
                                to_append = value["name"]
                            elif i == 2: #英雄索引（`championIndex`）
                                to_append = champion_index
                            elif i <= 8:
                                to_append = champion.get(key, "")
                            elif i == 9: #坐标（`Coordinate`）
                                to_append = "(%d, %d)" %(champion["Row"], champion["Col"])
                            else: #本地化装备名称（Localized item names）
                                if "items" in champion:
                                    itemNames: list[str] = []
                                    for item_key in champion["items"]:
                                        if item_key in TFTItemMap: #这里要注意，人机对战敌方阵营的装备都是用装备代码而不是装备主键来显示的（Note here that the items of a bot opponent are denoted by the item's mName instead of the item key）
                                            if "mDisplayNameTra" in TFTItemMap[item_key]:
                                                tooltip_key: str = TFTItemMap[item_key]["mDisplayNameTra"]
                                                strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 10 else strtable_tft_default
                                                itemNames.append(self.get_strtable_value(strtable_locale, tooltip_key, default = tooltip_key))
                                            else:
                                                itemNames.append(TFTItemMap[item_key]["mName"])
                                        else:
                                            itemNames.append(item_key)
                                    to_append = itemNames
                                else:
                                    to_append = ""
                            TFTPVENPC_data[key].append(to_append)
                            TFTPVENPC_data_json[key].append(pyobj2json(to_append))
                else:
                    for i in range(len(TFTPVENPC_header_keys)):
                        key: str = TFTPVENPC_header_keys[i]
                        if i == 0: #主键（`key`）
                            to_append: Any = key1
                        elif i == 1: #代码（`name`）
                            to_append = value["name"]
                        else:
                            to_append = ""
                        TFTPVENPC_data[key].append(to_append)
                        TFTPVENPC_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "ScriptDataObject": #云顶之弈脚本（TFT Script）
                for i in range(len(TFTScript_header_keys)):
                    key: str = TFTScript_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 3:
                        to_append = value.get(key, "")
                    else: #拓展组常数数值（`mRequiredConstantsGroup mConstants`）
                        if value["mRequiredConstantsGroup"] in self.map22_bin and "mConstants" in self.map22_bin[value["mRequiredConstantsGroup"]]:
                            to_append = self.map22_bin[value["mRequiredConstantsGroup"]]["mConstants"]
                        else:
                            to_append = ""
                    TFTScript_data[key].append(to_append)
                    TFTScript_data_json[key].append(pyobj2json(to_append))
            elif key1 != "__linked" and value["__type"] == "TFTAnnouncementData": #云顶之弈通告（TFT Announcement）
                for i in range(len(TFTAnnouncement_header_keys)):
                    key: str = TFTAnnouncement_header_keys[i]
                    if i == 0: #主键（`key`）
                        to_append: Any = key1
                    elif i <= 6:
                        to_append = value.get(key, "")
                    else: #本地化通告标题（Localized announcement title）
                        tooltip_key: str = value["mTitleTra"]
                        strtable_locale: dict[str, int | dict[str, str]] = strtable_tft_target if i == 7 else strtable_tft_default
                        to_append = self.get_strtable_value(strtable_locale, tooltip_key, default = "")
                    TFTAnnouncement_data[key].append(to_append)
                    TFTAnnouncement_data_json[key].append(pyobj2json(to_append))
        
        #数据框构建和排序（Build the dataframe and sort the keys and values）
        ##云顶之弈赛季（TFT Set）
        TFTSet_statistics_output_order: list[int] = [0, 1, 2, 5, 3, 89, 90, 4, 85, 10, 131, 11, 132, 12, 133, 13, 30, 145, 146, 147, 14, 15, 134, 82, 169, 16, 72, 17, 135, 136, 137, 19, 138, 18, 22, 139, 24, 26, 61, 111, 112, 62, 113, 114, 63, 115, 116, 64, 117, 118, 65, 119, 120, 66, 121, 122, 67, 123, 124, 68, 125, 126, 74, 163, 164, 165, 166, 167, 168, 25, 140, 141, 142, 27, 143, 144, 83, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 207, 208, 189, 209, 210, 190, 211, 212, 191, 213, 214, 192, 215, 216, 193, 217, 218, 194, 219, 220, 195, 221, 222, 196, 223, 224, 197, 225, 226, 198, 227, 228, 199, 229, 230, 200, 231, 232, 201, 233, 234, 202, 235, 236, 203, 237, 238, 204, 239, 240, 205, 241, 242, 206, 243, 244, 70, 21, 29, 34, 150, 151, 154, 155, 152, 156, 157, 153, 158, 160, 159, 161, 35, 36, 162, 20, 69, 81, 129, 130, 46, 37, 91, 92, 38, 93, 95, 94, 96, 39, 97, 98, 40, 41, 99, 100, 42, 101, 103, 102, 104, 43, 105, 106, 44, 107, 109, 108, 110, 45, 79, 47, 77, 78, 128, 84, 245, 247, 246, 76, 31, 148, 32, 149, 6, 7, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 71, 127, 88, 33, 8, 9, 23, 28, 58, 59, 60, 73, 75, 80, 86, 87]
        TFTSet_data_organized: dict[str, list[Any]] = {TFTSet_header_keys[i]: TFTSet_data_json[TFTSet_header_keys[i]] for i in TFTSet_statistics_output_order}
        TFTSet_df: pandas.DataFrame = pandas.DataFrame(data = TFTSet_data_organized)
        logPrint("正在优化云顶之弈赛季数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Set dataframe ...")
        optimize_bool_display(TFTSet_df)
        TFTSet_df = pandas.concat([pandas.DataFrame([TFTSet_header])[TFTSet_df.columns], TFTSet_df], ignore_index = True)
        self.TFTSet_df = TFTSet_df
        ##云顶之弈商店（TFT Shop）
        TFTShop_statistics_output_order: list[int] = [0, 3, 1, 11, 16, 17, 2, 4, 5, 12, 18, 19, 13, 20, 22, 21, 23, 14, 24, 25, 15, 6, 7, 8, 9, 10]
        TFTShop_data_organized: dict[str, list[Any]] = {TFTShop_header_keys[i]: TFTShop_data_json[TFTShop_header_keys[i]] for i in TFTShop_statistics_output_order}
        TFTShop_df: pandas.DataFrame = pandas.DataFrame(data = TFTShop_data_organized)
        # logPrint("正在优化云顶之弈商店数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Shop dataframe ...")
        # optimize_bool_display(TFTShop_df)
        TFTShop_df = pandas.concat([pandas.DataFrame([TFTShop_header])[TFTShop_df.columns], TFTShop_df], ignore_index = True)
        self.TFTShop_df = TFTShop_df
        ##云顶之弈商店内容（TFT Shop Content）
        TFTShopContent_statistics_output_order: list[int] = [0, 1, 2, 3, 5, 6, 4]
        TFTShopContent_data_organized: dict[str, list[Any]] = {TFTShopContent_header_keys[i]: TFTShopContent_data_json[TFTShopContent_header_keys[i]] for i in TFTShopContent_statistics_output_order}
        TFTShopContent_df: pandas.DataFrame = pandas.DataFrame(data = TFTShopContent_data_organized)
        # logPrint("正在优化云顶之弈商店内容数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Shop Content dataframe ...")
        # optimize_bool_display(TFTShopContent_df)
        TFTShopContent_df = pandas.concat([pandas.DataFrame([TFTShopContent_header])[TFTShopContent_df.columns], TFTShopContent_df], ignore_index = True)
        self.TFTShopContent_df = TFTShopContent_df
        ##云顶之弈掉率表（TFT Drop Rate）
        TFTDropRate_statistics_output_order: list[int] = [0, 2, 1, 3, 4]
        TFTDropRate_data_organized: dict[str, list[Any]] = {TFTDropRate_header_keys[i]: TFTDropRate_data_json[TFTDropRate_header_keys[i]] for i in TFTDropRate_statistics_output_order}
        TFTDropRate_df: pandas.DataFrame = pandas.DataFrame(data = TFTDropRate_data_organized)
        # logPrint("正在优化云顶之弈掉率数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Drop Rate dataframe ...")
        # optimize_bool_display(TFTDropRate_df)
        TFTDropRate_df = pandas.concat([pandas.DataFrame([TFTDropRate_header])[TFTDropRate_df.columns], TFTDropRate_df], ignore_index = True)
        self.TFTDropRate_df = TFTDropRate_df
        ##云顶之弈回合阶段（TFT Stage Round）
        TFTStageRound_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6]
        TFTStageRound_data_organized: dict[str, list[Any]] = {TFTStageRound_header_keys[i]: TFTStageRound_data_json[TFTStageRound_header_keys[i]] for i in TFTStageRound_statistics_output_order}
        TFTStageRound_df: pandas.DataFrame = pandas.DataFrame(data = TFTStageRound_data_organized)
        # logPrint("正在优化云顶之弈回合阶段数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Stage Round dataframe ...")
        # optimize_bool_display(TFTStageRound_df)
        TFTStageRound_df = pandas.concat([pandas.DataFrame([TFTStageRound_header])[TFTStageRound_df.columns], TFTStageRound_df], ignore_index = True)
        self.TFTStageRound_df = TFTStageRound_df
        ##云顶之弈回合（TFT Round）
        TFTRound_statistics_output_order: list[int] = [0, 1, 3, 47, 48, 4, 49, 50, 5, 51, 52, 12, 15, 53, 54, 13, 14, 16, 17, 18, 19, 20, 21, 22, 25, 55, 56, 23, 24, 26, 27, 30, 57, 58, 28, 29, 31, 34, 59, 60, 32, 33, 35, 36, 39, 61, 62, 37, 38, 40, 41, 63, 64, 42, 45, 65, 66, 43, 44, 46, 2, 6, 7, 8, 9, 10, 11]
        TFTRound_data_organized: dict[str, list[Any]] = {TFTRound_header_keys[i]: TFTRound_data_json[TFTRound_header_keys[i]] for i in TFTRound_statistics_output_order}
        TFTRound_df: pandas.DataFrame = pandas.DataFrame(data = TFTRound_data_organized)
        logPrint("正在优化云顶之弈回合数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Round dataframe ...")
        optimize_bool_display(TFTRound_df)
        TFTRound_df = pandas.concat([pandas.DataFrame([TFTRound_header])[TFTRound_df.columns], TFTRound_df], ignore_index = True)
        self.TFTRound_df = TFTRound_df
        ##云顶之弈传送门（TFT Portal）
        TFTPortal_statistics_output_order: list[int] = [0, 1, 2, 3, 15, 16, 10, 11, 12, 4, 17, 19, 18, 20, 5, 21, 23, 22, 24, 14, 25, 26, 6, 13, 8, 7, 9]
        TFTPortal_data_organized: dict[str, list[Any]] = {TFTPortal_header_keys[i]: TFTPortal_data_json[TFTPortal_header_keys[i]] for i in TFTPortal_statistics_output_order}
        TFTPortal_df: pandas.DataFrame = pandas.DataFrame(data = TFTPortal_data_organized)
        logPrint("正在优化云顶之弈传送门数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Portal dataframe ...")
        optimize_bool_display(TFTPortal_df)
        TFTPortal_df = pandas.concat([pandas.DataFrame([TFTPortal_header])[TFTPortal_df.columns], TFTPortal_df], ignore_index = True)
        self.TFTPortal_df = TFTPortal_df
        ##云顶之弈开场奇遇（TFT Encounter Distribution）
        TFTEncounterDistribution_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        TFTEncounterDistribution_data_organized: dict[str, list[Any]] = {TFTEncounterDistribution_header_keys[i]: TFTEncounterDistribution_data_json[TFTEncounterDistribution_header_keys[i]] for i in TFTEncounterDistribution_statistics_output_order}
        TFTEncounterDistribution_df: pandas.DataFrame = pandas.DataFrame(data = TFTEncounterDistribution_data_organized)
        # logPrint("正在优化云顶之弈开场奇遇数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Encounter Distribution dataframe ...")
        # optimize_bool_display(TFTEncounterDistribution_df)
        TFTEncounterDistribution_df = pandas.concat([pandas.DataFrame([TFTEncounterDistribution_header])[TFTEncounterDistribution_df.columns], TFTEncounterDistribution_df], ignore_index = True)
        self.TFTEncounterDistribution_df = TFTEncounterDistribution_df
        ##云顶之弈奇遇（TFT Encounter）
        TFTEncounter_statistics_output_order: list[int] = [0, 1, 5, 8, 2, 3, 7, 6, 13, 14, 4, 9, 10, 11, 15, 12]
        TFTEncounter_data_organized: dict[str, list[Any]] = {TFTEncounter_header_keys[i]: TFTEncounter_data_json[TFTEncounter_header_keys[i]] for i in TFTEncounter_statistics_output_order}
        TFTEncounter_df: pandas.DataFrame = pandas.DataFrame(data = TFTEncounter_data_organized)
        # logPrint("正在优化云顶之弈奇遇据框的逻辑值显示……\nOptimizing boolean value display of the TFT Encounter dataframe ...")
        # optimize_bool_display(TFTEncounter_df)
        TFTEncounter_df = pandas.concat([pandas.DataFrame([TFTEncounter_header])[TFTEncounter_df.columns], TFTEncounter_df], ignore_index = True)
        self.TFTEncounter_df = TFTEncounter_df
        ##云顶之弈单位属性（TFT Unit Property）
        TFTUnitProperty_statistics_output_order: list[int] = [0, 7, 3, 1, 2, 4, 5, 6, 8]
        TFTUnitProperty_data_organized: dict[str, list[Any]] = {TFTUnitProperty_header_keys[i]: TFTUnitProperty_data_json[TFTUnitProperty_header_keys[i]] for i in TFTUnitProperty_statistics_output_order}
        TFTUnitProperty_df: pandas.DataFrame = pandas.DataFrame(data = TFTUnitProperty_data_organized)
        logPrint("正在优化云顶之弈单位属性数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Unit Property dataframe ...")
        optimize_bool_display(TFTUnitProperty_df)
        TFTUnitProperty_df = pandas.concat([pandas.DataFrame([TFTUnitProperty_header])[TFTUnitProperty_df.columns], TFTUnitProperty_df], ignore_index = True)
        self.TFTUnitProperty_df = TFTUnitProperty_df
        ##云顶之弈角色定位（TFT Character Role）
        TFTCharacterRole_statistics_output_order: list[int] = [0, 1, 3, 10, 11, 4, 12, 13, 5, 14, 16, 15, 17, 6, 18, 19, 7, 20, 21, 8, 22, 24, 23, 25, 9, 26, 27, 2]
        TFTCharacterRole_data_organized: dict[str, list[Any]] = {TFTCharacterRole_header_keys[i]: TFTCharacterRole_data_json[TFTCharacterRole_header_keys[i]] for i in TFTCharacterRole_statistics_output_order}
        TFTCharacterRole_df: pandas.DataFrame = pandas.DataFrame(data = TFTCharacterRole_data_organized)
        # logPrint("正在优化云顶之弈角色定位数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Character Role dataframe ...")
        # optimize_bool_display(TFTCharacterRole_df)
        TFTCharacterRole_df = pandas.concat([pandas.DataFrame([TFTCharacterRole_header])[TFTCharacterRole_df.columns], TFTCharacterRole_df], ignore_index = True)
        self.TFTCharacterRole_df = TFTCharacterRole_df
        ##云顶之弈装备列表（TFT Item List）
        TFTItemList_statistics_output_order: list[int] = [0, 1, 2, 4, 5, 3, 6]
        TFTItemList_data_organized: dict[str, list[Any]] = {TFTItemList_header_keys[i]: TFTItemList_data_json[TFTItemList_header_keys[i]] for i in TFTItemList_statistics_output_order}
        TFTItemList_df: pandas.DataFrame = pandas.DataFrame(data = TFTItemList_data_organized)
        # logPrint("正在优化云顶之弈装备列表数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Item List dataframe ...")
        # optimize_bool_display(TFTItemList_df)
        TFTItemList_df = pandas.concat([pandas.DataFrame([TFTItemList_header])[TFTItemList_df.columns], TFTItemList_df], ignore_index = True)
        self.TFTItemList_df = TFTItemList_df
        ##云顶之弈装备（TFT Item）
        TFTItem_statistics_output_order: list[int] = [0, 1, 15, 41, 43, 42, 44, 14, 2, 11, 4, 27, 28, 5, 29, 30, 6, 31, 32, 13, 25, 7, 33, 34, 8, 35, 36, 9, 37, 38, 10, 3, 16, 45, 47, 46, 48, 12, 39, 40, 17, 18, 19, 20, 21, 22, 23, 24, 26, 49]
        TFTItem_data_organized: dict[str, list[Any]] = {TFTItem_header_keys[i]: TFTItem_data_json[TFTItem_header_keys[i]] for i in TFTItem_statistics_output_order}
        TFTItem_df: pandas.DataFrame = pandas.DataFrame(data = TFTItem_data_organized)
        logPrint("正在优化云顶之弈装备数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Item dataframe ...")
        optimize_bool_display(TFTItem_df)
        TFTItem_df = pandas.concat([pandas.DataFrame([TFTItem_header])[TFTItem_df.columns], TFTItem_df], ignore_index = True)
        self.TFTItem_df = TFTItem_df
        ##云顶之弈羁绊列表（TFT Trait List）
        TFTTraitList_statistics_output_order: list[int] = [0, 1, 3, 4, 2, 5]
        TFTTraitList_data_organized: dict[str, list[Any]] = {TFTTraitList_header_keys[i]: TFTTraitList_data_json[TFTTraitList_header_keys[i]] for i in TFTTraitList_statistics_output_order}
        TFTTraitList_df: pandas.DataFrame = pandas.DataFrame(data = TFTTraitList_data_organized)
        # logPrint("正在优化云顶之弈羁绊列表数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Trait List dataframe ...")
        # optimize_bool_display(TFTTraitList_df)
        TFTTraitList_df = pandas.concat([pandas.DataFrame([TFTTraitList_header])[TFTTraitList_df.columns], TFTTraitList_df], ignore_index = True)
        self.TFTTraitList_df = TFTTraitList_df
        ##云顶之弈羁绊（TFT Trait）
        TFTTrait_statistics_output_order: list[int] = [0, 1, 2, 11, 12, 6, 7, 10, 8, 9, 3, 13, 15, 14, 16, 4, 17, 19, 18, 20, 5]
        TFTTrait_data_organized: dict[str, list[Any]] = {TFTTrait_header_keys[i]: TFTTrait_data_json[TFTTrait_header_keys[i]] for i in TFTTrait_statistics_output_order}
        TFTTrait_df: pandas.DataFrame = pandas.DataFrame(data = TFTTrait_data_organized)
        logPrint("正在优化云顶之弈羁绊数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Trait dataframe ...")
        optimize_bool_display(TFTTrait_df)
        TFTTrait_df = pandas.concat([pandas.DataFrame([TFTTrait_header])[TFTTrait_df.columns], TFTTrait_df], ignore_index = True)
        self.TFTTrait_df = TFTTrait_df
        ##云顶之弈电脑玩家英雄（TFT PVE NPC）
        TFTPVENPC_statistics_output_order: list[int] = [0, 1, 2, 3, 4, 5, 6, 9, 7, 10, 11, 8]
        TFTPVENPC_data_organized: dict[str, list[Any]] = {TFTPVENPC_header_keys[i]: TFTPVENPC_data_json[TFTPVENPC_header_keys[i]] for i in TFTPVENPC_statistics_output_order}
        TFTPVENPC_df: pandas.DataFrame = pandas.DataFrame(data = TFTPVENPC_data_organized)
        # logPrint("正在优化云顶之弈电脑玩家英雄数据框的逻辑值显示……\nOptimizing boolean value display of the TFT PVE NPC dataframe ...")
        # optimize_bool_display(TFTPVENPC_df)
        TFTPVENPC_df = pandas.concat([pandas.DataFrame([TFTPVENPC_header])[TFTPVENPC_df.columns], TFTPVENPC_df], ignore_index = True)
        self.TFTPVENPC_df = TFTPVENPC_df
        ##云顶之弈脚本（TFT Script）
        TFTScript_statistics_output_order: list[int] = [0, 1, 2, 3, 4]
        TFTScript_data_organized: dict[str, list[Any]] = {TFTScript_header_keys[i]: TFTScript_data_json[TFTScript_header_keys[i]] for i in TFTScript_statistics_output_order}
        TFTScript_df: pandas.DataFrame = pandas.DataFrame(data = TFTScript_data_organized)
        # logPrint("正在优化云顶之弈脚本数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Script dataframe ...")
        # optimize_bool_display(TFTScript_df)
        TFTScript_df = pandas.concat([pandas.DataFrame([TFTScript_header])[TFTScript_df.columns], TFTScript_df], ignore_index = True)
        self.TFTScript_df = TFTScript_df
        ##云顶之弈通告（TFT Announcement）
        TFTAnnouncement_statistics_output_order: list[int] = [0, 2, 7, 8, 3, 4, 1, 5, 6]
        TFTAnnouncement_data_organized: dict[str, list[Any]] = {TFTAnnouncement_header_keys[i]: TFTAnnouncement_data_json[TFTAnnouncement_header_keys[i]] for i in TFTAnnouncement_statistics_output_order}
        TFTAnnouncement_df: pandas.DataFrame = pandas.DataFrame(data = TFTAnnouncement_data_organized)
        # logPrint("正在优化云顶之弈通告数据框的逻辑值显示……\nOptimizing boolean value display of the TFT Announcement dataframe ...")
        # optimize_bool_display(TFTAnnouncement_df)
        TFTAnnouncement_df = pandas.concat([pandas.DataFrame([TFTAnnouncement_header])[TFTAnnouncement_df.columns], TFTAnnouncement_df], ignore_index = True)
        self.TFTAnnouncement_df = TFTAnnouncement_df
        return 0
            
    def export_tft_data(self, debug: bool = False, path: Optional[str] = None) -> None:
        '''
        导出云顶之弈数据到工作簿中。产生以下工作表：<br>Export TFT data to a workbook. The following worksheets are added:
        - 云顶之弈赛季（TFT Set）
        - 云顶之弈商店（TFT Shop）
        - 云顶之弈商店内容（TFT Shop Content）
        - 云顶之弈掉率表（TFT Drop Rate）
        - 云顶之弈回合阶段（TFT Stage Round）
        - 云顶之弈回合（TFT Round）
        - 云顶之弈传送门（TFT Portal）
        - 云顶之弈开场奇遇（TFT Encounter Distribution）
        - 云顶之弈奇遇（TFT Encounter）
        - 云顶之弈单位属性（TFT Unit Property）
        - 云顶之弈角色定位（TFT Character Role）
        - 云顶之弈装备列表（TFT Item List）
        - 云顶之弈装备（TFT Item）
        - 云顶之弈羁绊列表（TFT Trait List）
        - 云顶之弈羁绊（TFT Trait）
        - 云顶之弈电脑玩家英雄（TFT PVE NPC）
        - 云顶之弈脚本（TFT Script）
        - 云顶之弈通告（TFT Announcement）
        
        :param debug: 是否离线读取数据资源。默认为假。<br>Whether to read data resource offline. False by default.
        :type debug: bool
        :param path: 聚点危机地图二进制描述文件的本地路径。<br>A local path of Convergence map binary description file.
        
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
        if self.TFTSet_df.empty or self.TFTShop_df.empty or self.TFTShopContent_df.empty or self.TFTDropRate_df.empty or self.TFTStageRound_df.empty or self.TFTRound_df.empty or self.TFTPortal_df.empty or self.TFTEncounterDistribution_df.empty or self.TFTEncounter_df.empty or self.TFTUnitProperty_df.empty or self.TFTCharacterRole_df.empty or self.TFTItemList_df.empty or self.TFTItem_df.empty or self.TFTTraitList_df.empty or self.TFTTrait_df.empty or self.TFTPVENPC_df.empty or self.TFTScript_df.empty or self.TFTAnnouncement_df.empty:
            status: int = self.build_tft_dataframe(debug = debug, path = path)
            if status != 0:
                logPrint("在构建数据框时出现了一个问题，因此数据不会被导出到工作簿中。按回车键继续。\nAn error occurred when the program was build the dataframe. Press Enter to continue.")
                logInput()
                return
        #导出数据（Export data）
        logPrint("正在导出数据……\nExporting data ...", print_time = True)
        if not os.path.exists(self.wbPath):
            wbCreateFlag: bool = create_workbook_win32(os.path.abspath(self.wbPath))
        workbook_exist: bool = os.path.exists(self.wbPath)
        sheet1_name: str = f"{self.patch_number} TFTSet" if self.sheet_naming_fold else "云顶之弈赛季（TFT Set）"
        sheet2_name: str = f"{self.patch_number} TFTShop" if self.sheet_naming_fold else "云顶之弈商店（TFT Shop）"
        sheet3_name: str = f"{self.patch_number} TFTShopContent" if self.sheet_naming_fold else "云顶之弈商店内容（TFT Shop Content）"
        sheet4_name: str = f"{self.patch_number} TFTDropRate" if self.sheet_naming_fold else "云顶之弈掉率表（TFT Drop Rate）"
        sheet5_name: str = f"{self.patch_number} TFTStageRound" if self.sheet_naming_fold else "云顶之弈回合阶段（TFT Stage Round）"
        sheet6_name: str = f"{self.patch_number} TFTRound" if self.sheet_naming_fold else "云顶之弈回合（TFT Round）"
        sheet7_name: str = f"{self.patch_number} TFTPortal" if self.sheet_naming_fold else "云顶之弈传送门（TFT Portal）"
        sheet8_name: str = f"{self.patch_number} TFTEncounterDistribution" if self.sheet_naming_fold else "云顶之弈开场奇遇（TFT Encounter Distribution）"
        sheet9_name: str = f"{self.patch_number} TFTEncounter" if self.sheet_naming_fold else "云顶之弈奇遇（TFT Encounter）"
        sheet10_name: str = f"{self.patch_number} TFTUnitProperty" if self.sheet_naming_fold else "云顶之弈单位属性（TFT Unit Property）"
        sheet11_name: str = f"{self.patch_number} TFTCharacterRole" if self.sheet_naming_fold else "云顶之弈角色定位（TFT Character Role）"
        sheet12_name: str = f"{self.patch_number} TFTItemList" if self.sheet_naming_fold else "云顶之弈装备列表（TFT Item List）"
        sheet13_name: str = f"{self.patch_number} TFTItem" if self.sheet_naming_fold else "云顶之弈装备（TFT Item）"
        sheet14_name: str = f"{self.patch_number} TFTTraitList" if self.sheet_naming_fold else "云顶之弈羁绊列表（TFT Trait List）"
        sheet15_name: str = f"{self.patch_number} TFTTrait" if self.sheet_naming_fold else "云顶之弈羁绊（TFT Trait）"
        sheet16_name: str = f"{self.patch_number} TFTPVENPC" if self.sheet_naming_fold else "云顶之弈电脑玩家英雄（TFT PVE NPC）"
        sheet17_name: str = f"{self.patch_number} TFTScript" if self.sheet_naming_fold else "云顶之弈脚本（TFT Script）"
        sheet18_name: str = f"{self.patch_number} TFTAnnouncement" if self.sheet_naming_fold else "云顶之弈通告（TFT Announcement）"
        while True:
            try:
                with (pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "replace") if workbook_exist else pandas.ExcelWriter(self.wbPath, mode = "w")) as writer:
                    addDefaultStyle(self.TFTSet_df).to_excel(excel_writer = writer, sheet_name = sheet1_name)
                    addDefaultStyle(self.TFTShop_df).to_excel(excel_writer = writer, sheet_name = sheet2_name)
                    addDefaultStyle(self.TFTShopContent_df).to_excel(excel_writer = writer, sheet_name = sheet3_name)
                    addDefaultStyle(self.TFTDropRate_df).to_excel(excel_writer = writer, sheet_name = sheet4_name)
                    addDefaultStyle(self.TFTStageRound_df).to_excel(excel_writer = writer, sheet_name = sheet5_name)
                    addDefaultStyle(self.TFTRound_df).to_excel(excel_writer = writer, sheet_name = sheet6_name)
                    addDefaultStyle(self.TFTPortal_df).to_excel(excel_writer = writer, sheet_name = sheet7_name)
                    addDefaultStyle(self.TFTEncounterDistribution_df).to_excel(excel_writer = writer, sheet_name = sheet8_name)
                    addDefaultStyle(self.TFTEncounter_df).to_excel(excel_writer = writer, sheet_name = sheet9_name)
                    addDefaultStyle(self.TFTUnitProperty_df).to_excel(excel_writer = writer, sheet_name = sheet10_name)
                    addDefaultStyle(self.TFTCharacterRole_df).to_excel(excel_writer = writer, sheet_name = sheet11_name)
                    addDefaultStyle(self.TFTItemList_df).to_excel(excel_writer = writer, sheet_name = sheet12_name)
                    addDefaultStyle(self.TFTItem_df).to_excel(excel_writer = writer, sheet_name = sheet13_name)
                    addDefaultStyle(self.TFTTraitList_df).to_excel(excel_writer = writer, sheet_name = sheet14_name)
                    addDefaultStyle(self.TFTTrait_df).to_excel(excel_writer = writer, sheet_name = sheet15_name)
                    addDefaultStyle(self.TFTPVENPC_df).to_excel(excel_writer = writer, sheet_name = sheet16_name)
                    addDefaultStyle(self.TFTScript_df).to_excel(excel_writer = writer, sheet_name = sheet17_name)
                    addDefaultStyle(self.TFTAnnouncement_df).to_excel(excel_writer = writer, sheet_name = sheet18_name)
                with pandas.ExcelWriter(self.wbPath, mode = "a", if_sheet_exists = "overlay") as writer: #在A1单元格填充数据所在版本（Fill in A0 cell with the data version）
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet1_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet2_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet3_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet4_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet5_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet6_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet7_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet8_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet9_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet10_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet11_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet12_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet13_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet14_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet15_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet16_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet17_name, header = None, index = False, startcol = 0, startrow = 0)
                    self.version_df.to_excel(excel_writer = writer, sheet_name = sheet18_name, header = None, index = False, startcol = 0, startrow = 0)
            except PermissionError:
                logPrint('''无写入权限！请确保文件未被打开且非只读状态！输入任意键以重试，或者输入“0”以放弃导出。\nPermission denied! Please ensure the file isn't opened right now or read-only! Submit any string to try again, or submit "0" to quit exporting.''')
                cont = logInput()
                if cont != "" and cont[0] == "0":
                    break
            else:
                logPrint(f"云顶之弈数据已导出到{self.wbPath}。按回车键继续。\nTFT data have been exported to {self.wbPath}. Press Enter to continue.", print_time = True)
                logInput()
                break

#定义模式覆盖文本描述函数（Define the overriden data tooltip function）
def modeOverrideTooltipTransform(binData: dict[str, Any], objectType: str, keyPaths: str | list[str], gameModeName: Literal["TUTORIAL", "TUTORIAL_MODULE_1", "TUTORIAL_MODULE_2", "TUTORIAL_MODULE_3", "SWIFTPLAY", "PRACTICETOOL", "FIRSTBLOOD", "ARSR", "ARAM", "{bffdf499}", "KINGPORO", "URF", "SNOWURF", "ONEFORALL", "{6462680f}", "NEXUSBLITZ", "TFT", "ASSASSINATE", "ULTBOOK", "cherry", "STRAWBERRY", "{a110bc47}", "Ruby", "DOOMBOTSTEEMO", "{b0cea932}", "{afcea79f}", "{aecea60c}", "{9cf6bf22}"], strtable: dict[str, int | dict[str, str]]) -> str: #这个函数只用于制作英雄平衡表格，不用于本程序（This function is only designed for making the balance table, not for this program）
    '''
    遍历二进制描述数据中的模式覆盖数据并输出。<br>Traverse through the mode overriden values in binary description data and output them.
    
    :param binData: 完整的二进制描述数据，通常通过形如session.get(url).json()的代码直接获得。注意，二进制描述的预处理已在本函数内完成，所以传入该参数的二进制描述数据不能预先被处理过。<br>The complete binary description data, which is often obtained through code like `session.get(url).json()`. Note that the pre-processing of a binary description is finished within this function, so the value to pass to this parameter shouldn't be pre-processed in advance.
    :type binData: dict[str, Any]
    :param objectType: 要遍历的对象类型，通常为某个一级对象的__type键的值。例如，在英雄二进制描述数据中，一般指定该参数为“CharacterRecord”。<br>Object type to traverse through the binData, usually the value of `__type` key of a Level-1 object. For example, when it comes to traversing champion binary description data, this parameter is usually specified as "CharacterRecord".
    :type objectType: str
    :param keyPaths: 键路径，由键通过竖线组成的字符串，详见getBinaryKeys函数的文档字符串。<br>Paths of keys, concatenated by "|" from keys. Detailed are in the DocString of `getBinaryKeys` function.<br>参考数据覆盖键路径：<br>Some known mode override keyPaths corresponding to objectTypes:
        <pre>
        **objectType**      **keyPath**                         **description**<br>
        SpellObject     mSpell|{f9c2333e}               模式覆盖冷却时间（Mode overriden cooldown time）<br>
        SpellObject     mSpell|{b08bc498}               模式覆盖充能时间（Mode overriden charge time）<br>
        SpellObject     mSpell|DataValuesModeOverride   模式覆盖数值（Mode overriden data values）<br>
        ItemData        DataValuesModeOverride          模式覆盖数值（Mode overriden data values）
        </pre>
    :type keyPaths: str
    :param gameModeName: 游戏模式代号，在地图二进制描述中可找到。<br>The game mode name that can be found in the map binary description.<br>目前已知的游戏模式代号及其名称：<br>Currently known gameModeNames and the localized names:
        <pre>
        **gameModeName**      **description**<br>
        TUTORIAL            新手教程（Tutorial）<br>
        TUTORIAL_MODULE_2   新手教程 第二部分（Tutorial Part 2）<br>
        TUTORIAL_MODULE_3   新手教程 第三部分（Tutorial Part 3）<br>
        TUTORIAL_MODULE_1   新手教程 第一部分（Tutorial Part 1）<br>
        SWIFTPLAY           快速模式（Swiftplay）<br>
        PRACTICETOOL        训练模式（Practice Tool）<br>
        FIRSTBLOOD          大对决（Showdown）<br>
        ARSR                峡谷大乱斗（ARSR）<br>
        ARAM                极地大乱斗（ARAM）<br>
        {bffdf499}          海克斯大乱斗（ARAM: Mayhem）<br>
        KINGPORO            魄罗大乱斗（Poro King）<br>
        URF                 无限火力（Ultra Rapid Fire）<br>
        SNOWURF             冰雪无限火力（Snow Ultra Rapid Fire）<br>
        ONEFORALL           克隆大作战（One for All）<br>
        {6462680f}          {c706490e}<br>
        NEXUSBLITZ          极限闪击（Nexus Blitz）<br>
        TFT                 云顶之弈（Teamfight Tactics）<br>
        ASSASSINATE         红月决（Blood Moon Hunt）<br>
        ULTBOOK             终极魔典（Ultimate Spellbook）<br>
        cherry              斗魂竞技场（Arena）<br>
        STRAWBERRY          无尽狂潮（Swarm）<br>
        {a110bc47}          神木之门（Brawl）<br>
        Ruby                末日人工智能（Doom Bots）<br>
        DOOMBOTSTEEMO       末日人工智能（Doom Bots Teemo）<br>
        {b0cea932}          末日人工智能：维迦的诅咒！（Doom Bots - Veigar's Curse!）<br>
        {afcea79f}          末日人工智能：维迦的邪咒！（Doom Bots - Veigar's Evil!）<br>
        {aecea60c}          末日人工智能：维迦的末日厄咒！（Doom Bots - Veigar's Doom!）<br>
        {9cf6bf22}          WASD
        </pre>
    :type gameModeName: str
    :param strtable: 字符串常量池。<br>Stringtable.
    :type strtable: dict[str, int | dict[str, str]]
    :return: 二进制描述binData中的每个objectType项目在gameModeName中的某些符合keyPaths的属性覆盖值的说明文本。<br>Tooltip of some `gameModeName` overriden values that correspond to `keyPaths` in each `objectType` object in the binary description `binData`.
    :rtype: str
    '''
    #预处理参数（Pre-process parameters）
    binData = LoLDataExtractor.normalizeBinData(binData) #因此，传入的binData不能预先被normalizeSpellData函数处理过（Hence, the passed `binData` should be in raw format and not pre-processed by `normalizeBinData` function）
    if isinstance(keyPaths, str):
        keyPathList: list[str] = [keyPaths.split("|")]
    elif isinstance(keyPaths, list) and all(map(lambda x: isinstance(x, str), keyPaths)):
        keyPathList: list[str] = list(map(lambda x: x.split("|"), keyPaths))
    else:
        print(f"警告：您传入的键路径有误。请检查。函数将返回空字符串。\nWarning: Invalid `keyPath`! Please check it. The function will return an empty string instead.")
        return ""
    #构建热键映射（Build the hotkey map）
    #遍历二进制描述数据（Traverse binary description data）
    s: str = "" #初始化结果字符串（Initialize the result string）
    for (key, value) in binData.items():
        if key != "__linked" and value["__type"] == objectType:
            tmp_ptr = value
            for keyPath in keyPathList:
                for tmp_key in keyPath:
                    if tmp_key in tmp_ptr:
                        tmp_ptr = tmp_ptr[tmp_key]
                    else:
                        break
                else:
                    value = copy.deepcopy(value)
                    if value["__type"] == "SpellObject":
                        value["mSpell"] = LoLDataExtractor.normalizeBinData(value["mSpell"])
                    elif value["__type"] == "ItemData":
                        value = LoLDataExtractor.normalizeBinData(value)
                    if tmp_key in {"{f9c2333e}", "{b08bc498}", "DataValuesModeOverride"}:
                        if gameModeName in tmp_ptr:
                            #获取技能名称（Get ability name）
                            if value["__type"] == "SpellObject":
                                keyNamePath: list[str] = ["mSpell", "mClientData", "mTooltipData", "mLocKeys", "keyName"]
                            elif value["__type"] == "ItemData":
                                keyNamePath = ["mItemDataClient", "mTooltipData", "mLocKeys", "keyName"]
                            else:
                                keyNamePath = []
                            if keyNamePath == []:
                                keyName_content = key
                            else:
                                tmp_ptr1 = value
                                for tmp_key1 in keyNamePath:
                                    if tmp_key1 in tmp_ptr1:
                                        tmp_ptr1 = tmp_ptr1[tmp_key1]
                                    else:
                                        keyName_content = key
                                        break
                                else:
                                    keyName = tmp_ptr1
                                    keyName_content = LoLDataExtractor.get_strtable_value(strtable, keyName, default = keyName)
                            #获取技能热键（Get ability hotkey）
                            if value["__type"] == "SpellObject":
                                if len(key.split("/")) > 1: #形如（Looks like）：Characters/Aphelios/Spells/ApheliosQ_ClientTooltipWrapper
                                    championFolder: str = key.split("/")[1]
                                    CharacterRecordRoot_key = f"Characters/{championFolder}/CharacterRecords/Root"
                                    if CharacterRecordRoot_key in binData:
                                        CharacterRecordRoot = binData[CharacterRecordRoot_key]
                                        characterName = CharacterRecordRoot.get("mCharacterName", "")
                                        if "mCharacterPassiveSpell" in CharacterRecordRoot and CharacterRecordRoot["mCharacterPassiveSpell"] == key:
                                            mHotKey = "P"
                                        elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][0] == key:
                                            mHotKey = "Q"
                                        elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][1] == key:
                                            mHotKey = "W"
                                        elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][2] == key:
                                            mHotKey = "E"
                                        elif "spells" in CharacterRecordRoot and CharacterRecordRoot["spells"][3] == key:
                                            mHotKey = "R"
                                        else:
                                            mHotKey = ""
                                else:
                                    characterName = mHotKey = ""
                            else:
                                characterName = mHotKey = ""
                            #获取缺省值和覆盖值（Get the default and overriden value）
                            if tmp_key == "{f9c2333e}" or tmp_key == "{b08bc498}": #基础冷却时间和基础充能时间（Basic cooldown and basic charge time）
                                if tmp_key == "{f9c2333e}": #基础冷却时间（Basic cooldown）
                                    if "cooldownTime" in value["mSpell"]:
                                        if mHotKey == "R":
                                            time_list: list[float] = value["mSpell"]["cooldownTime"][1:4]
                                        else:
                                            time_list = value["mSpell"]["cooldownTime"][1:6]
                                        defaultValue: str = LoLDataExtractor.burnValueList(time_list)
                                    else:
                                        defaultValue = "φ"
                                else: #基础充能时间（Basic charge time）
                                    if "mAmmoRechargeTime" in value["mSpell"]:
                                        if mHotKey == "R":
                                            time_list = value["mSpell"]["mAmmoRechargeTime"][1:4]
                                        else:
                                            time_list = value["mSpell"]["mAmmoRechargeTime"][1:6]
                                        defaultValue = LoLDataExtractor.burnValueList(time_list)
                                    else:
                                        defaultValue = "φ"
                                if mHotKey == "R":
                                    overrideValue: str = LoLDataExtractor.burnValueList(tmp_ptr[gameModeName]["value"][1:4])
                                else:
                                    overrideValue = LoLDataExtractor.burnValueList(tmp_ptr[gameModeName]["value"][1:6])
                                if tmp_key == "{f9c2333e}":
                                    s += "{%s}【%s】（%s）：基础冷却时间：%s秒 → %s秒\n" %(characterName, keyName_content, mHotKey, defaultValue, overrideValue)
                                else:
                                    s += "{%s}【%s】（%s）：基础充能时间：%s秒 → %s秒\n" %(characterName, keyName_content, mHotKey, defaultValue, overrideValue)
                            elif tmp_key == "DataValuesModeOverride":
                                overrideValues: dict[str, list[dict[str, str | float | list[float]]]] = tmp_ptr[gameModeName]
                                if overrideValues["__type"] == "SpellDataValueVector":
                                    s += "{%s}【%s】（%s）：" %(characterName, keyName_content, mHotKey)
                                    for i in range(len(overrideValues["SpellDataValues"])):
                                        spellDataValue = overrideValues["SpellDataValues"][i]
                                        var = spellDataValue["name"] if "name" in spellDataValue else spellDataValue["mName"]
                                        if var.lower() in value["mSpell"]["DataValues"]:
                                            varData: dict[str, Any] = value["mSpell"]["DataValues"][var.lower()]
                                            if mHotKey == "R":
                                                value_list: list[int | float] = varData["values"][1:4] if "values" in varData else varData["mValues"][1:4]
                                            else:
                                                value_list = varData["values"][1:6] if "values" in varData else varData["mValues"][1:6]
                                            defaultValue = LoLDataExtractor.burnValueList(value_list)
                                        else:
                                            defaultValue = "φ"
                                        if mHotKey == "R":
                                            overrideValue = LoLDataExtractor.burnValueList(spellDataValue["values"][1:4]) if "values" in spellDataValue else varData["mValues"][1:4] if "mValues" in varData else "φ"
                                        else:
                                            overrideValue = LoLDataExtractor.burnValueList(spellDataValue["values"][1:6]) if "values" in spellDataValue else varData["mValues"][1:6] if "mValues" in varData else "φ"
                                        s += "{%s}：%s → %s" %(var, defaultValue, overrideValue)
                                        if i < len(overrideValues["SpellDataValues"]) - 1:
                                            s += "；"
                                        else:
                                            s += "\n"
                                elif overrideValues["__type"] == "ItemDataValues":
                                    s += "【%s】：" %(keyName_content)
                                    for i in range(len(overrideValues["DataValues"])):
                                        itemDataValue = overrideValues["DataValues"][i]
                                        var = spellDataValue["name"] if "name" in spellDataValue else spellDataValue["mName"]
                                        if var.lower() in value["mDataValues"]:
                                            defaultValue = LoLDataExtractor.aRound(value["mDataValues"][var.lower()]["mValue"], 5)
                                        else:
                                            defaultValue = "φ"
                                        overrideValue = LoLDataExtractor.aRound(itemDataValue["mValue"][1:4], 5)
                                        s += "{%s}：%s → %s" %(var, defaultValue, overrideValue)
                                        if i < len(overrideValues["SpellDataValues"]) - 1:
                                            s += "；"
                                        else:
                                            s += "\n"
    return s

if __name__ == "__main__":
    log: LogManager = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    #定义语言设置过程（Define the process of setting language）
    def set_locale() -> str:
        '''
        设置全局语言环境。<br>Set the global locale.
        
        :return: 语言文化代码。<br>Language code.
        :rtype: str
        '''
        logPrint("请选择说明文本的输出语言【默认为中文（中国）】：\nPlease select a language for tooltips (the default option is zh_CN):")
        language_dict: dict[str, list[str]] = {"No.": list(language_ddragon.keys()), "CODE": list(map(lambda x: x["CODE"], language_ddragon.values())), "LANGUAGE": list(map(lambda x: x["LANGUAGE (EN)"], language_ddragon.values())), "语言": list(map(lambda x: x["LANGUAGE (ZH)"], language_ddragon.values())), "Applicable CDragon Data Patches": list(map(lambda x: x["Applicable CDragon Data Patches"], language_ddragon.values()))}
        language_df: pandas.DataFrame = pandas.DataFrame(language_dict)
        logPrint(format_df(language_df)[0], write_time = False)
        while True:
            language_option = logInput()
            if language_option == "" or language_option in set(map(str, range(1, 31))):
                if language_option == "":
                    language_option = "29"
                language_code = language_ddragon[int(language_option)]["CODE"]
                break
            elif language_option[0] == "0":
                language_code = ""
                break
            else:
                logPrint("语言选项输入错误！请重新输入：\nERROR input of language option! Please try again:")
        return language_code

    #定义版本设置过程（Define the process of setting version）
    def set_version(session: Optional[requests.Session] = None) -> tuple[list[str], requests.Session]:
        '''
        设置游戏数据版本。<br>Set the game data version.
        
        :param session: 网络请求会话。如果没有指定，则内部新建一个会话，对外不可见。<br>Web request session. If unspecified, a new session will be created, which isn't visible to outside.
        :type session: requests.Session | None
        :return: 大版本号列表和网络请求会话。<br>List of major version numbers and web request session.
        :rtype: tuple[list[str], requests.Session]
        '''
        if session == None:
            session = requests.Session()
        logPrint("请在以下版本号中选择并输入完整的版本号：\nPlease select a version and then enter it entirely:")
        patches_cdragon, patchList_fetched = get_cdragon_patchList(session = session, log = log)
        if not patchList_fetched:
            return ([], session)
        logPrint(json.dumps(patches_cdragon, ensure_ascii = False))
        while True:
            version: str = logInput()
            if version == "":
                versions: list[str] = ["pbe"]
                break
            elif version == "all":
                versions = patches_cdragon
                break
            elif version[0] == "0":
                versions = []
                break
            elif version in patches_cdragon:
                versions = [version]
                break
            else:
                try:
                    versions = eval(version)
                except:
                    logPrint("您的输入有误，请重新输入！\nERROR input! Please try again.")
                else:
                    if isinstance(versions, list) and all(map(lambda x: x in patches_cdragon, versions)):
                        break
                    else:
                        logPrint("您的输入有误，请重新输入！\nERROR input! Please try again.")
        return (versions, session)

    #定义工作表排序函数（Define worksheet sorting function）
    def sort_workbook_sheets(wbPath: str, naming_pattern: int) -> None:
        '''
        对游戏数据提取工作簿的工作表进行排序。<br>Sort the sheets of Game Data Extraction workbook.
        
        :param wbPath: 游戏数据提取工作簿路径。<br>Game Data Extraction workbook path.
        :type wbPath: str
        :param naming_pattern: 命名模式代号。有以下两个取值：<br>Naming pattern code, which has the following two values:
        
            - 1: 中文备注英文。如“斗魂竞技场强化符文（Cherry Augments）”。<br>Chinese with English note. E.g. "斗魂竞技场强化符文（Cherry Augments）".
            - 2: 版本号和英文。如“16.8.7638450 CherryAugments”。<br>Patch number and English. E.g. "16.8.7638450 CherryAugments".
        :type naming_pattern: int
        '''
        if not os.path.exists(wbPath):
            logPrint("文件不存在。不执行任何操作。\nFile not found. No operation will be performed.")
            return
        elif not os.path.isfile(wbPath):
            logPrint("参数不是文件。不执行任何操作。\nThe parameter isn't a file. No operation will be performed.")
            return
        elif not os.path.splitext(wbPath)[1] == ".xlsx":
            logPrint("文件格式错误。不执行任何操作。\nFile format error. No operation will be performed.")
            return
        if naming_pattern != 1 and naming_pattern != 2:
            logPrint("命名模式代号有误。不执行任何操作。\nNaming pattern code error. No operation will be performed.")
            return
        wbPath = wbPath.replace("\\", "/")
        wbPath_sorted: str = " (sorted)".join(os.path.splitext(wbPath))
        #读取工作簿（Read the workbook）
        try:
            wb: Workbook = load_workbook(wbPath)
        except Exception as e:
            logPrint(e)
            logPrint("工作簿读取失败。不执行任何操作。\nWorkbook reading failed. No operation will be performed.")
            return
        #首先整理出所有工作表的排列顺序（First, sort out the order of all sheets）
        sheetnames: list[str] = wb.sheetnames
        logPrint("正在创建顺序工作表列表……\nCreating the ordered sheet list ...", print_time = True)
        if naming_pattern == 1:
            sheetnames_order: list[str] = ["地图（Map）", "指令集（CheatSet）", "指令（Cheat）", "符文系（PerkStyles）", "符文（Perks）", "英雄（Champions）", "英雄技能（Champion Spells）", "角色（Characters）", "角色技能（Character Spells）", "装备（Items）", "装备分组（Item Groups）", "装备修饰（Item Modifiers）", "斗魂竞技场强化符文（Cherry Augments）", "无尽狂潮强化（Swarm Augments）", "海克斯大乱斗强化符文（Kiwi Augments）", "海克斯大乱斗强化符文套装（Kiwi Augment Set）", "斗魂竞技场锻造器（Cherry Anvils）", "海克斯大乱斗锻造器（Kiwi Anvils）", "斗魂竞技场荣誉嘉宾（Cherry Guests）", "云顶之弈赛季（TFT Set）", "云顶之弈商店（TFT Shop）", "云顶之弈商店内容（TFT Shop Content）", "云顶之弈掉率表（TFT Drop Rate）", "云顶之弈回合阶段（TFT Stage Round）", "云顶之弈回合（TFT Round）", "云顶之弈传送门（TFT Portal）", "云顶之弈开场奇遇（TFT Encounter Distribu", "云顶之弈开场奇遇（TFT Encounter Distribution）", "云顶之弈奇遇（TFT Encounter）", "云顶之弈单位属性（TFT Unit Property）", "云顶之弈角色定位（TFT Character Role）", "云顶之弈装备列表（TFT Item List）", "云顶之弈装备（TFT Item）", "云顶之弈羁绊列表（TFT Trait List）", "云顶之弈羁绊（TFT Trait）", "云顶之弈电脑玩家英雄（TFT PVE NPC）", "云顶之弈脚本（TFT Script）", "云顶之弈通告（TFT Announcement）"]
        else:
            pVersion_dataType: re.Pattern[str] = re.compile(r"\d+(\.\d+)*\s\w+") #定义正则表达式来检验工作表名称是否符合整合工作簿中的工作表格式——版本号+数据类型（Define a regular expression to verify whether a sheet name obeys the format of sheets in an integrated workbook: version number + data type）
            version_order: list[Patch] = sorted(set(Patch(name.split()[0]) for name in sheetnames if pVersion_dataType.fullmatch(name))) #提取工作表的版本部分，整理形成正序版本列表（Extract the version part of sheet names and organize them into a ascending list）
            dataType_order: list[str] = ["Map", "CheatSet", "Cheat", "PerkStyles", "Perks", "Champions", "ChampionSpells", "Characters", "CharacterSpells", "Items", "ItemGroups", "ItemModifiers", "CherryAugments", "SwarmAugments", "KiwiAugments", "KiwiAugmentSet", "CherryAnvils", "KiwiAnvils", "CherryGuests", "TFTSet", "TFTShop", "TFTShopContent", "TFTDropRate", "TFTStageRound", "TFTRound", "TFTPortal", "TFTEncounterDistri", "TFTEncounterDistr", "TFTEncounterDistribution", "TFTEncounter", "TFTUnitProperty", "TFTCharacterRole", "TFTItemList", "TFTItem", "TFTTraitList", "TFTTrait", "TFTPVENPC", "TFTScript", "TFTAnnouncement"]
            tmpDf: pandas.DataFrame = pandas.DataFrame(data = [{"name": name, "version_weight": version_order.index(Patch(name.split()[0])), "type_weight": dataType_order.index(name.split()[1])} for name in sheetnames if pVersion_dataType.fullmatch(name)]) #忽略名称不合法的工作表（Bypass sheets with illegal names）
            tmpDf_sorted: pandas.DataFrame = tmpDf.sort_values(by = ["version_weight", "type_weight"]) #工作表名称按照版本的正序和数据类型的正序进行排列（Arrange sheet names in the ascending orders of versions and data types）
            sheetnames_order = tmpDf_sorted["name"].to_list()
        sheetnames_sorted: list[str] = [] #所有工作表的期望顺序存储在sheetnames_sorted变量中（The ordered result of all sheets is stored in the variable `sheetnames_sorted`）
        for sheet_iter in sheetnames_order:
            if sheet_iter in sheetnames:
                sheetnames_sorted.append(sheet_iter)
        #然后排列所有工作表（Then, arrange all sheets）
        logPrint("正在排序……\nOrdering ...", print_time = True)
        sort_worksheet(wb, sheetnames_sorted)
        logPrint("正在保存中……\nSaving the ordered workbook ...", print_time = True)
        wb.save(wbPath_sorted)
        logPrint("排序完成！排好序的工作簿已保存为以下文件。\nOrdering finished! The ordered workbook is saved as the following file.\n%s" %(wbPath_sorted), print_time = True)
        wb.close()

    #定义主函数（Define the main function）
    def main() -> int:
        '''
        主函数，用于发行版。<br>Main function for the release version.
        
        主要读取在线数据资源。<br>Mainly loads online data resources.
        
        :return: 状态码。<br>Status code.
        :rtype: int
        '''
        #初始化网络请求会话（Initialize the web request session）
        session = requests.Session()
        # session.trust_env = False #忽略系统代理设置（Bypass system proxy）

        #设置语言（Set the language）
        language_code = set_locale()
        if language_code == "":
            return 1

        #设置版本（Set the version)
        versions, session = set_version(session = session)
        if len(versions) == 0:
            return 2
        
        #设置工作表集成（Determine whether to integrate sheets in different patches into one workbook）
        logPrint("是否将不同版本的工作表集成到一个工作簿中？（输入任意非空字符串以确认集成，否则分不同版本保存。）\nDo you want to integrate sheets of different versions into a single workbook? (Input any non-empty string to confirm integration, or null save data into multiple workbooks of the different version.)")
        integrate_str: str = logInput()
        integrate: bool = bool(integrate_str)
        
        for i in range(len(versions)):
            version = versions[i]
            logPrint(f"[%d/%d]开始处理%s版本的游戏数据。\nStart to process game data of Version %s." %(i + 1, len(versions), version, version))
            extractor = LoLDataExtractor(version, language_code, session = session)
            if integrate:
                extractor.encapsulate()
            else:
                extractor.decapsulate()
            #加载版本数据（Load version data）
            logPrint(f"正在加载完整的游戏版本号……\nLoading the complete version number ...", print_time = True)
            extractor.get_version()
            if extractor.patch == "" or extractor.patch_number == "":
                continue
            print(f"当前版本号（Current patch）： {extractor.patch}")
            #加载文件导出列表（Load file export list）
            logPrint(f"正在加载文件导出列表……\nLoading the file export list ...", print_time = True)
            extractor.get_exported_files()
            if not extractor.fileExportList_ready:
                continue
            #加载中英文字符串常量池（Load the stringtable in Chinese and English）
            logPrint("正在加载字符串常量池……\nLoading stringtables ...", print_time = True)
            extractor.get_strtable()
            if not (extractor.strtable_organize_manner == 1 and extractor.strtables_ready["lol_target"] and extractor.strtables_ready["lol_default"] and extractor.strtables_ready["tft_target"] and extractor.strtables_ready["tft_default"]) and not (extractor.strtable_organize_manner == 2 and extractor.strtables_ready["target"] and extractor.strtables_ready["default"]):
                continue
            #加载共享数据（Load shared data）
            logPrint("正在加载共享数据……\nLoading shared data ...", print_time = True)
            extractor.init_mSpells()
            if not extractor.shared_ready:
                logPrint("共享数据获取失败。将忽略该数据。\nShared data capture failure! The program will ignore them.")
                # continue
            #设置要提取的数据类型（Set the type of data to extract）
            while True:
                logPrint("请选择您要提取的数据：\nPlease select the type of data you want to extract:\n-1\t设置（Settings）\n0\t退出当前版本（Quit this version）\n1\t地图（Maps）\n2\t作弊指令（Cheat sheet）\n3\t符文（Perks）\n4\t英雄（Champions）\n5\t装备（Items）\n6\t强化符文（Augments）\n7\t锻造器（Anvils）\n8\t荣誉嘉宾（Guests of Honor）\n9\t云顶之弈赛季、装备和羁绊（TFT Sets, Items and Traits）")
                mode = logInput()
                if mode == "":
                    continue
                elif mode == "-1":
                    logPrint("请选择一个配置：\nPlease select an configuration option:\n0\t返回上一层（Return to the last step）\n1\t说明文本样式（Tooltip style）\n2\t变量替换样式（Variable substitution style）")
                    while True:
                        option = logInput()
                        if option == "":
                            continue
                        elif option == "-1":
                            return 0
                        elif option[0] == "0":
                            break
                        elif option[0] == "1":
                            logPrint("是否保留说明文本的原始样式？（输入任意非空字符串以保留原始CSS样式；否则移除所有CSS样式，用统一的标点符号进行强调。）\nDo you want to reserve the original style of tooltips? (Input any non-empty string to reserve the original CSS style; otherwise, remove all CSS styles and use the unified punctuation marks for emphasis.)")
                            reserve_CSS_str: str = logInput()
                            reserve_CSS: bool = bool(reserve_CSS_str)
                            optimize_layout: bool = extractor.set_tooltipTransform_strategy(reserve_CSS = reserve_CSS)
                            if optimize_layout:
                                logPrint("说明文本将移除所有CSS标签。\nCSS tags will be removed from the tooltips.")
                            else:
                                logPrint("说明文本将保留原始CSS标签。\nCSS tags will be reserved in the tooltips.")
                        elif option[0] == "2":
                            logPrint('是否在数值替换的同时保留原变量？（输入任意非空字符串以将转换后的变量写成“[{变量名}] = {值}”的形式，否则只保留值。）\nDo you want to reserve the original variable when variable substitution is being performed? (Input any non-empty string to transform the variable into the form "[{Var_name}] = {Value}", or null to reserve the value only.)')
                            reserve_variable_str: str = logInput()
                            reserve_variable: bool = bool(reserve_variable_str)
                            extractor.reserve_variable = reserve_variable
                            if reserve_variable:
                                logPrint("说明文本在完成变量代换后将同时显示变量名和值。\nBoth the name and the value of variables will appear in the tooltip after variable substitution.")
                            else:
                                logPrint("说明文本在完成变量代换后将只显示值。\nOnly the value of variables will appear in the tooltip after variable substitution.")
                        else:
                            logPrint("您的输入有误！请重新输入。\nERROR input. Please try again.")
                            continue
                        logPrint("请选择一个配置：\nPlease select an configuration option:\n0\t返回上一层（Return to the last step）\n1\t说明文本样式（Tooltip style）\n2\t变量替换样式（Variable substitution style）")
                elif mode[0] == "0":
                    LoLDataExtractor.clear_cache()
                    break
                elif mode[0] == "1":
                    mapExtractor: MapExtractor = MapExtractor(extractor)
                    mapExtractor.export_map_data()
                elif mode[0] == "2":
                    cheatExtractor: CheatExtractor = CheatExtractor(extractor)
                    cheatExtractor.export_cheat_data()
                elif mode[0] == "3":
                    perkExtractor: PerkExtractor = PerkExtractor(extractor)
                    perkExtractor.export_perk_data()
                elif mode[0] == "4":
                    championExtractor: ChampionExtractor = ChampionExtractor(extractor)
                    status: int = championExtractor.set_mode()
                    if status == 0: #当用户输入“0”时，返回上一层（When the user submits "0", the program will return to the last step）
                        championExtractor.export_champion_data()
                elif mode[0] == "5":
                    itemExtractor: ItemExtractor = ItemExtractor(extractor)
                    itemExtractor.export_item_data()
                elif mode[0] == "6":
                    augmentExtractor: AugmentExtractor = AugmentExtractor(extractor)
                    augmentExtractor.export_augment_data()
                elif mode[0] == "7":
                    anvilExtractor: AnvilExtractor = AnvilExtractor(extractor)
                    anvilExtractor.export_anvil_data()
                elif mode[0] == "8":
                    gohExtractor: GoHExtractor = GoHExtractor(extractor)
                    gohExtractor.export_GoH_data()
                elif mode[0] == "9":
                    tftExtractor: TFTExtractor = TFTExtractor(extractor)
                    tftExtractor.export_tft_data()
                else:
                    logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        else:
            print("是否排序工作表？（输入任意非空字符串以排序，否则不排序。）\nDo you want to sort the worksheets? (Submit any non-empty string to sort, or null to refuse sorting.)")
            sort_sheet_str: str = logInput()
            sort_sheet: bool = bool(sort_sheet_str)
            if sort_sheet:
                wbPaths: list[str] = []
                if integrate:
                    logPrint("请输入一个含有多版本数据的工作簿路径。\nPlease the path of a workbook that contains data of multiple patches.")
                else:
                    logPrint('请依次输入每个版本的工作簿路径。输入“-1”以结束。\nPlease input the paths of workbooks of single patches one by one. Enter "-1" to cancel.')
                while True:
                    wbPath: str = logInput()
                    if wbPath == "":
                        continue
                    elif wbPath == "-1" and not integrate:
                        break
                    elif os.path.exists(wbPath) and os.path.isfile(wbPath) and os.path.splitext(wbPath)[1] == ".xlsx":
                        wbPaths.append(wbPath.replace("\\", "/"))
                        if integrate:
                            break
                    elif not os.path.exists(wbPath):
                        logPrint("文件未找到。请重新输入。\nFile not found. Please try again.")
                    elif not os.path.isfile(wbPath):
                        logPrint("请输入一个文件。\nPlease provide a file.")
                    else:
                        logPrint('文件格式错误。请输入以“.xlsx”为后缀的文件。\nFile format error. Please provide a file with ".xlsx" extension.')
                for i in range(len(wbPaths)):
                    wbPath: str = wbPaths[i]
                    logPrint("[%d/%d]正在排序（Ordering）： %s" %(i + 1, len(wbPaths), wbPath), print_time = True)
                    sort_workbook_sheets(wbPath, 2 if integrate else 1)
                else:
                    if len(wbPaths) > 0:
                        logPrint("排序完成。程序即将退出。\nOrder finished. The program will exit soon.")
        return 0

    #定义调试函数。开发者可在其中随时修改代码（Define the debug function. Code in this function may be modified at will）
    def debug(dir_type: Literal["repo", "extract"] = "repo") -> int:
        '''
        调试函数，用于测试。<br>Debug function for the beta version.

        主要读取离线数据资源。<br>Mainly loads offline data resources.

        本人设备上默认使用的数据资源目录：<br>The default data resource directory used on my device:<br>C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe
        
        本人设备上经过LoL-Wad-Extract-Tencent存储库提取的测试服的游戏文本文件的默认目录：<br>The default directory for text files of PBE extracted by LoL-Wad-Extract-Tencent repository:<br>D:/Workspace/LoL-Wad-Extract-Riot/pbe-text
        
        :param dir_type: 目录类型。有以下两个取值：<br>Type of directory, which has two values:
        
            - **repo**: LoL-Dragon-Change-S16存储库中的测试服文件夹。<br>PBE folder under LoL-Dragon-Change-S16 repository.
            - **extract**: 通过LoL-Wad-Extract-Tencent存储库提取测试服时指定的目的文件夹。<br>The destination / target folder specified when extracting PBE data using LoL-Wad-Extract-Tencent repository.
        
        :type dir_type: str
        :return: 状态码。<br>Status code.
        :rtype: int
        '''
        #设置语言（Set the language）
        language_code = "zh_CN"
        if language_code == "":
            return 1
        
        #设置版本（Set the version）
        version = "pbe"
        
        #设置默认导出行为（Set the default export behavior）
        export: bool = False
        
        #设置工作表集成（Determine whether to integrate sheets in different patches into one workbook）
        logPrint("是否将不同版本的工作表集成到一个工作簿中？（输入任意非空字符串以确认集成，否则分不同版本保存。）\nDo you want to integrate sheets of different versions into a single workbook? (Input any non-empty string to confirm integration, or null save data into multiple workbooks of the different version.)")
        integrate_str: str = logInput()
        integrate: bool = bool(integrate_str)
        
        logPrint(f"开始处理%s版本的游戏数据。\nStart to process game data of Version %s." %(version, version))
        extractor = LoLDataExtractor(version, language_code)
        if integrate:
            extractor.encapsulate()
        else:
            extractor.decapsulate()
        #加载版本数据（Load version data）
        logPrint(f"正在加载完整的游戏版本号……\nLoading the complete version number ...")
        if dir_type == "extract":
            game_version_path: str = "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/content-metadata.json"
        else:
            game_version_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/compat-version-metadata.json"
        extractor.read_version(game_version_path)
        if extractor.patch == "" or extractor.patch_number == "":
            return 0
        print(f"当前版本号（Current patch）： {extractor.patch}")
        #加载文件导出列表（Load file export list）
        logPrint(f"正在加载文件导出列表……\nLoading the file export list ...", print_time = True)
        extractor.read_exported_files("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/cdragon/files.exported.txt")
        # if not extractor.fileExportList_ready:
        #     return 0
        #加载中英文字符串常量池（Load the stringtable in Chinese and English）
        logPrint("正在加载字符串常量池……\nLoading stringtables ...", print_time = True)
        if dir_type == "extract":
            strtable_paths: list[str] = [
                "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/zh_cn/data/menu/en_us/lol.stringtable.json",
                "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/en_us/data/menu/en_us/lol.stringtable.json",
                "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/zh_cn/data/menu/en_us/tft.stringtable.json",
                "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/en_us/data/menu/en_us/tft.stringtable.json",
            ]
        else:
            strtable_paths = [
                "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/zh_cn/data/menu/en_us/lol.stringtable.json",
                "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/en_us/data/menu/en_us/lol.stringtable.json",
                "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/zh_cn/data/menu/en_us/tft.stringtable.json",
                "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/en_us/data/menu/en_us/tft.stringtable.json",
            ]
        extractor.read_strtable(strtable_paths = strtable_paths)
        if not (extractor.strtable_organize_manner == 1 and extractor.strtables_ready["lol_target"] and extractor.strtables_ready["lol_default"] and extractor.strtables_ready["tft_target"] and extractor.strtables_ready["tft_default"]) and not (extractor.strtable_organize_manner == 2 and extractor.strtables_ready["target"] and extractor.strtables_ready["default"]):
            return 0
        #加载共享数据（Load shared data）
        logPrint("正在加载共享数据……\nLoading shared data ...", print_time = True)
        if dir_type == "extract":
            shared_bin_path = "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/shared.cdtb.bin.json"
        else:
            shared_bin_path: str = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/shared.cdtb.bin.json"
        extractor.init_mSpells(debug = True, path = shared_bin_path)
        if not extractor.shared_ready:
            # logPrint("共享数据获取失败。将忽略该数据。\nShared data capture failure! The program will ignore them.")
            return 0
        #设置要提取的数据类型（Set the type of data to extract）
        while True:
            logPrint("请选择您要提取的数据：\nPlease select the type of data you want to extract:\n-2\t调试（Debug）\n-1\t设置（Settings）\n0\t退出当前版本（Quit this version）\n1\t地图（Maps）\n2\t作弊指令（Cheat sheet）\n3\t符文（Perks）\n4\t英雄（Champions）\n5\t装备（Items）\n6\t强化符文（Augments）\n7\t锻造器（Anvils）\n8\t荣誉嘉宾（Guests of Honor）\n9\t云顶之弈赛季、装备和羁绊（TFT Sets, Items and Traits）")
            mode = logInput()
            if mode == "":
                continue
            elif mode == "-2":
                logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出调试（Quit debug）\n1\t启动子环境（Start a sub-environment）")
                while True:
                    draft_option = logInput()
                    if draft_option == "":
                        continue
                    elif draft_option[0] == "0":
                        break
                    elif draft_option[0] == "1":
                        scope: dict[str, Any] = {"LogManager": LogManager, "Patch": Patch, "requestUrl": requestUrl, "format_df": format_df, "verifyDictHeterogeneity": verifyDictHeterogeneity, "syncListOrder": syncListOrder, "traverse_keyPath": traverse_keyPath, "getBinaryKeys": getBinaryKeys, "LoLDataExtractor": LoLDataExtractor, "MapExtractor": MapExtractor, "CheatExtractor": CheatExtractor, "PerkExtractor": PerkExtractor, "ChampionExtractor": ChampionExtractor, "ItemExtractor": ItemExtractor, "AugmentExtractor": AugmentExtractor, "AnvilExtractor": AnvilExtractor, "TFTExtractor": TFTExtractor, "modeOverrideTooltipTransform": modeOverrideTooltipTransform, "extractor": extractor}
                        if "mapExtractor" in dir():
                            scope["mapExtractor"] = mapExtractor
                        if "cheatExtractor" in dir():
                            scope["cheatExtractor"] = cheatExtractor
                        if "perkExtractor" in dir():
                            scope["perkExtractor"] = perkExtractor
                        if "championExtractor" in dir():
                            scope["championExtractor"] = championExtractor
                        if "itemExtractor" in dir():
                            scope["itemExtractor"] = itemExtractor
                        if "augmentExtractor" in dir():
                            scope["augmentExtractor"] = augmentExtractor
                        if "anvilExtractor" in dir():
                            scope["anvilExtractor"] = anvilExtractor
                        if "tftExtractor" in dir():
                            scope["tftExtractor"] = tftExtractor
                        logPrint('示例（Examples）：\nprint(dir())\nlog: LogManager = LogManager()\nlogInput = log.logInput\nlogPrint = log.logPrint\nlogPrint(format_df(mapExtractor.map_df)[0], write_time = False)\n输入“-1”以退出调试。\nSubmit "-1" to quit debug.')
                        subscope(scope, log = log)
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
                    logPrint("请选择草稿选项：\nPlease select a draft option:\n0\t退出调试（Quit debug）\n1\t启动子环境（Start a sub-environment）")
            elif mode == "-1":
                logPrint("请选择一个配置：\nPlease select an configuration option:\n0\t返回上一层（Return to the last step）\n1\t说明文本样式（Tooltip style）\n2\t变量替换样式（Variable substitution style）\n3\t数据导出（Data export）")
                while True:
                    option = logInput()
                    if option == "":
                        continue
                    elif option == "-1":
                        return 0
                    elif option[0] == "0":
                        break
                    elif option[0] == "1":
                        logPrint("是否保留说明文本的原始样式？（输入任意非空字符串以保留原始CSS样式；否则移除所有CSS样式，用统一的标点符号进行强调。）\nDo you want to reserve the original style of tooltips? (Input any non-empty string to reserve the original CSS style; otherwise, remove all CSS styles and use the unified punctuation marks for emphasis.)")
                        reserve_CSS_str: str = logInput()
                        reserve_CSS: bool = bool(reserve_CSS_str)
                        optimize_layout: bool = extractor.set_tooltipTransform_strategy(reserve_CSS = reserve_CSS)
                        if optimize_layout:
                            logPrint("说明文本将移除所有CSS标签。\nCSS tags will be removed from the tooltips.")
                        else:
                            logPrint("说明文本将保留原始CSS标签。\nCSS tags will be reserved in the tooltips.")
                    elif option[0] == "2":
                        logPrint('是否在数值替换的同时保留原变量？（输入任意非空字符串以将转换后的变量写成“[{变量名}] = {值}”的形式，否则只保留值。）\nDo you want to reserve the original variable when variable substitution is being performed? (Input any non-empty string to transform the variable into the form "[{Var_name}] = {Value}", or null to reserve the value only.)')
                        reserve_variable_str: str = logInput()
                        reserve_variable: bool = bool(reserve_variable_str)
                        extractor.reserve_variable = reserve_variable
                        if reserve_variable:
                            logPrint("说明文本在完成变量代换后将同时显示变量名和值。\nBoth the name and the value of variables will appear in the tooltip after variable substitution.")
                        else:
                            logPrint("说明文本在完成变量代换后将只显示值。\nOnly the value of variables will appear in the tooltip after variable substitution.")
                    elif option[0] == "3":
                        logPrint("是否导出数据到Excel中？（输入任意非空字符串以导出，否则不导出。）\nDo you want to export data to Excel? (Submit any non-empty string to export, or null to refuse exporting.)")
                        export_str: str = logInput()
                        export = bool(export_str)
                        if export:
                            logPrint("数据将导出到Excel工作簿中。\nData will be exported to an Excel workbook.")
                        else:
                            logPrint("数据将只用来构建数据框，而不会导出。\nData will only be used to build dataframes but not be exported.")
                    else:
                        logPrint("您的输入有误！请重新输入。\nERROR input. Please try again.")
                        continue
                    logPrint("请选择一个配置：\nPlease select an configuration option:\n0\t返回上一层（Return to the last step）\n1\t说明文本样式（Tooltip style）\n2\t变量替换样式（Variable substitution style）\n3\t数据导出（Data export）")
            elif mode[0] == "0":
                LoLDataExtractor.clear_cache()
                break
            elif mode[0] == "1":
                mapExtractor: MapExtractor = MapExtractor(extractor)
                if dir_type == "extract":
                    map_paths: list[str] = [
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map11/map11.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map12/map12.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map21/map21.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map22/map22.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map30/map30.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map33/map33.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map35/map35.bin.json"
                    ]
                else:
                    map_paths = [
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map11/map11.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map12/map12.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map21/map21.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map22/map22.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map30/map30.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map33/map33.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map35/map35.bin.json"
                    ]
                mapExtractor.build_map_dataframe(debug = True, paths = map_paths)
                if export:
                    mapExtractor.export_map_data()
            elif mode[0] == "2":
                cheatExtractor: CheatExtractor = CheatExtractor(extractor)
                if dir_type == "extract":
                    cheat_path = "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/cheats.cdtb.bin.json"
                else:
                    cheat_path: str = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/cheats.cdtb.bin.json"
                cheatExtractor.build_cheat_dataframe(debug = True, path = cheat_path)
                if export:
                    cheatExtractor.export_cheat_data()
            elif mode[0] == "3":
                perkExtractor: PerkExtractor = PerkExtractor(extractor)
                if dir_type == "extract":
                    perk_path: str = "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/perks.cdtb.bin.json"
                else:
                    perk_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/perks.cdtb.bin.json"
                perkExtractor.build_perk_dataframe(debug = True, path = perk_path)
                if export:
                    perkExtractor.export_perk_data()
            elif mode[0] == "4":
                championExtractor: ChampionExtractor = ChampionExtractor(extractor)
                status: int = championExtractor.set_mode()
                if status == -1: #当用户输入“0”时，返回上一层（When the user submits "0", the program will return to the last step）
                    continue
                if dir_type == "extract":
                    champion_paths: list[str] = [
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Plugins/rcp-be-lol-game-data/global/zh_cn/v1/champion-summary.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/characters"
                    ]
                    character_paths: list[str] = [
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map22/map22.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/characters",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/characters"
                    ]
                else:
                    champion_paths = [
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/plugins/rcp-be-lol-game-data/global/zh_cn/v1/champion-summary.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/characters"
                    ]
                    character_paths = [
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map22/map22.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/characters",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/characters"
                    ]
                championExtractor.build_champion_dataframe(debug = True, paths = character_paths if championExtractor.useAllCharacter else champion_paths)
                if export:
                    championExtractor.export_champion_data()
            elif mode[0] == "5":
                itemExtractor: ItemExtractor = ItemExtractor(extractor)
                if dir_type == "extract":
                    item_path: str = "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/items.cdtb.bin.json"
                else:
                    item_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/items.cdtb.bin.json"
                itemExtractor.build_item_dataframe(debug = True, path = item_path)
                if export:
                    itemExtractor.export_item_data()
            elif mode[0] == "6":
                augmentExtractor: AugmentExtractor = AugmentExtractor(extractor)
                if dir_type == "extract":
                    augment_paths: list[str] = [
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map30/map30.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/maps/modespecificdata/cherry.bin.json"
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map33/map33.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map12/map12.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/maps/modespecificdata/kiwi.bin.json"
                    ]
                else:
                    augment_paths = [
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map30/map30.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/maps/modespecificdata/cherry.bin.json"
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map33/map33.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map12/map12.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/maps/modespecificdata/kiwi.bin.json"
                    ]
                augmentExtractor.build_augment_dataframe(debug = True, paths = augment_paths)
                if export:
                    augmentExtractor.export_augment_data()
            elif mode[0] == "7":
                anvilExtractor: AnvilExtractor = AnvilExtractor(extractor)
                if dir_type == "extract":
                    anvil_paths: list[str] = [
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map30/map30.bin.json",
                        "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map12/map12.bin.json"
                    ]
                else:
                    anvil_paths: list[str] = [
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map30/map30.bin.json",
                        "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map12/map12.bin.json"
                    ]
                anvilExtractor.build_anvil_dataframe(debug = True, paths = anvil_paths)
                if export:
                    anvilExtractor.export_anvil_data()
            elif mode[0] == "8":
                gohExtractor: GoHExtractor = GoHExtractor(extractor)
                if dir_type == "extract":
                    cherry_path = "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/maps/modespecificdata/cherry.bin.json"
                else:
                    cherry_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/maps/modespecificdata/cherry.bin.json"
                gohExtractor.build_GoH_dataframe(debug = True, path = cherry_path)
                if export:
                    gohExtractor.export_GoH_data()
            elif mode[0] == "9":
                tftExtractor: TFTExtractor = TFTExtractor(extractor)
                if dir_type == "extract":
                    map22_path = "D:/Workspace/LoL-Wad-Extract-Riot/pbe-text/Game/DATA/FINAL/data/maps/shipping/map22/map22.bin.json"
                else:
                    map22_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map22/map22.bin.json"
                tftExtractor.build_tft_dataframe(debug = True, path = map22_path)
                if export:
                    tftExtractor.export_tft_data()
            else:
                logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
        return 0

    #个性化函数（Personalized function）
    def DIY() -> int: #该函数将会分为数据资源、数据准备和说明文本转换部分，并将随时补充。在VSCode中，按Ctrl-Q以注释或解除注释其中的部分（This function is basically divided into three parts: data resource, data preparation and tooltip transformation, and always receives supplement. In VSCode, press Ctrl—Q to comment or uncomment out regions）
        '''
        个性化函数，用于进一步调试。<br>Personalized function for further debug use.
        
        :return: 状态码。总是0。<br>Status code. Always return 0.
        :rtype: int
        '''
        #数据资源（Data resource）
        ##字符串常量池（Stringtable）
        lolstringtable_zh_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/zh_cn/data/menu/en_us/lol.stringtable.json"
        with open(lolstringtable_zh_path, "r", encoding = "utf-8") as fp:
            lolstringtable_zh = json.load(fp)
        lolstringtable_en_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/en_us/data/menu/en_us/lol.stringtable.json"
        with open(lolstringtable_en_path, "r", encoding = "utf-8") as fp:
            lolstringtable_en = json.load(fp)
        tftstringtable_zh_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/zh_cn/data/menu/en_us/tft.stringtable.json"
        with open(tftstringtable_zh_path, "r", encoding = "utf-8") as fp:
            tftstringtable_zh = json.load(fp)
        tftstringtable_en_path = "C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/en_us/data/menu/en_us/tft.stringtable.json"
        with open(tftstringtable_en_path, "r", encoding = "utf-8") as fp:
            tftstringtable_en = json.load(fp)
        ##地图（Map）
        # with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map22/map22.bin.json", "r", encoding = "utf-8") as fp:
        #     map22_bin = json.load(fp)
        with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map30/map30.bin.json", "r", encoding = "utf-8") as fp:
            map30_bin = json.load(fp)
        # with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/data/maps/shipping/map33/map33.bin.json", "r", encoding = "utf-8") as fp:
        #     map33_bin = json.load(fp)
        ##装备（Item）
        # with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/items.cdtb.bin.json", "r", encoding = "utf-8") as fp:
        #     items_bin = json.load(fp)
        ##共享数据（Shared data）
        # with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/shared.cdtb.bin.json", "r", encoding = "utf-8") as fp:
        #     shared_bin = json.load(fp)
        ##符文（Perk）
        # with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/perks.cdtb.bin.json", "r", encoding = "utf-8") as fp:
        #     perks_bin = json.load(fp)
        ##强化符文和荣誉嘉宾（Augment and Guest of Honor）
        # with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/maps/modespecificdata/cherry.bin.json", "r", encoding = "utf-8") as fp:
        #     cherry_bin = json.load(fp)
        # with open("C:/Users/19250/Documents/GitHub/LoL-Dragon-Change-S16/Data/cdragon/pbe/game/maps/modespecificdata/kiwi.bin.json", "r", encoding = "utf-8") as fp:
        #     kiwi_bin = json.load(fp)
        ##整合后的数据（Merged data）
        # with open("C:/Users/19250/Documents/Workspace/JupyterLab/自定义脚本/英雄联盟自定义房间创建/champions_bin.json", "r", encoding = "utf-8") as fp:
        #     champions_bin = json.load(fp)
        # with open("C:/Users/19250/Documents/Workspace/JupyterLab/自定义脚本/英雄联盟自定义房间创建/characters_bin.json", "r", encoding = "utf-8") as fp:
        #     characters_bin = json.load(fp)
        
        #数据准备（Data preparation）
        # for (key, value) in shared_bin.items():
        #     if key != "__linked" and value["__type"] == "SpellObject":
        #         LoLDataExtractor.mSpells[value["mScriptName"]] = value
        # for (key, value) in characters_bin.items():
        #     if key != "__linked" and value["__type"] == "SpellObject":
        #         LoLDataExtractor.mSpells[value["mScriptName"]] = value
        # for (key, value) in map22_bin.items():
        #     if key != "__linked" and value["__type"] == "TftUnitPropertyDefinition":
        #         LoLDataExtractor.TFTUnitPropertyMap[value["name"]] = value
        #     elif key != "__linked" and value["__type"] == "TftTraitData":
        #         LoLDataExtractor.TFTTraitMap[value["mName"]] = value
        #     elif key != "__linked" and value["__type"] == "ScriptDataObject":
        #         LoLDataExtractor.TFTScriptDataMap[value["mName"]] = value
        
        #总结数据结构（Summarize the data structure）
        # keyDict: dict[str, dict[str, int]] = getBinaryKeys(map33_bin, isBin = True, keyPaths = None, objectTypes = "AugmentData")[1]
        # print(json.dumps(keyDict, indent = 4, ensure_ascii = False))
        # import pyperclip
        # s: str = ""
        # for key in keyDict["{fa33a427}"]:
        #     s += key + "\n"
        # pyperclip.copy(s)
        
        #输出键的hash值（Output hash value of a key）
        # print(LoLDataExtractor.compute_rsthash("Spell_TFT17_PykeSpell_Name", 5))
        
        #键对应（Key map）
        # mDisplayName_key = "Item_2523_Name"
        # print(LoLDataExtractor.get_strtable_value(lolstringtable_zh, mDisplayName_key, default = "获取失败。"))
        
        #说明文本转换（Tooltip transformation）
        tooltip_raw: str = "{{ Cherry_ParasiticRelationship@TeamSize@_Summary }}"
        print("原始说明文本：\n" + tooltip_raw)
        binData: dict[str, Any] = map30_bin["Maps/Shipping/Map30/Spells/Augment_ParasiticRelationship"]["mSpell"]
        print("----")
        print("转换文本：")
        print(LoLDataExtractor.tooltipTransform(tooltip_raw, lolstringtable_zh, binData, isCHS = True, enableModeOverride = True, reserve_variable = False))
        # print(LoLDataExtractor.tooltipTransform(tooltip_raw, lolstringtable_zh, binData, isCHS = True, enableModeOverride = True, reserve_variable = True))
        # print(LoLDataExtractor.tooltipSubstitute(tooltip_raw, lolstringtable_zh, binData, isCHS = True, enableModeOverride = True, reserve_variable = False))
        # print(LoLDataExtractor.tooltipSubstitute(tooltip_raw, lolstringtable_zh, binData, isCHS = True, enableModeOverride = True, reserve_variable = True))
        # print(modeOverrideTooltipTransform(champions_bin, objectType = "SpellObject", keyPaths = "mSpell|DataValuesModeOverride", gameModeName = "URF", strtable = lolstringtable_zh))
        
        return 0

    status = main() #供用户使用（For user use）
    # status = debug(dir_type = "repo") #供开发者使用（For developer use）
    # status = DIY()
    #结束日志输入输出流（Cancel the log I/O stream）
    log.write(f"\n[Program terminated and returned status {status}.]\n")
    log.close()
