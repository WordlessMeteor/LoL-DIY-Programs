import os, sys
from typing import Any, Annotated
from docstrands import Description
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from lcu_driver.connection import Connection
from openpyxl.worksheet.worksheet import Worksheet
from src.utils.logger import LogManager
from src.utils.webRequest import SGPSession
#ds，既指数据资源（Data reSource），也指文档字符串（DocString）
dsConnection = Annotated[Connection, Description("通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.")]
dsSGPSession = Annotated[SGPSession, Description("通过网络请求模块创建的用于访问SGP API的会话对象。<br>A session created through Web Request Module, meant to access SGP API.")]
dsWorksheet = Annotated[Worksheet, Description('工作表对象，通过对一个`pandas.ExcelWriter`对象对工作表取下标得到，如`writer["Sheet1"]`。<br>A Worksheet object obtained by subscripting a `pandas.ExcelWriter` object, e.g. `writer["Sheet1"]`.')]
dsRegion = Annotated[str, Description('''大区。有以下选项：<br>Region. Options are as follows:
    
        - TENCENT: 腾讯游戏
        - GARENA: 竞舞娱乐
        - RIOT: 拳头游戏
        
        可通过以下LCU接口得到：<br>Obtained by the folowing LCU endpoint:
        
        - `GET /riotclient/region-locale`
        - `GET /riotclient/command-line-args`''')]
dsPlatformId = Annotated[str, Description('''服务器代号。可通过以下LCU接口得到：<br>PlatfromId, which can be obtained by any of the following LCU endpoints:
    
        - `GET /lol-platform-config/v1/namespaces/LoginDataPacket/platfromId`
        - `GET /riotclient/command-line-args` (Only for Tencent servers)''')]
dsProduct = Annotated[str, Description('''游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）
        - TFT: 云顶之弈（Teamfight Tactics）''')]
dsMatchId = Annotated[int, Description("对局序号。<br>GameId.")]
dsMatch_id = Annotated[str, Description("大区对局序号。由服务器代号和对局序号通过下划线连接而成。<br>Platform matchId, concatenated from a platformId and a matchId.")]
dsQueues = Annotated[dict[int, dict[str, Any]], Description('''整理后的队列数据资源。键是队列序号，值是游戏模式信息字典。<br>Organized queue data resource. Each key is a queueId, and each value is a game mode information dictionary.
    
        原始队列数据资源可通过以下链接获取：<br>The raw queue data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/queues.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/queues.json`''')]
dsSummonerIcons = Annotated[dict[int, dict[str, Any]], Description('''整理后的召唤师图标数据资源。键是召唤师图标序号，值是召唤师图标信息字典。<br>Organized champion skin data resource. Each key is a profileIconId, and each value is a summoner icon information dictionary.
    
        原始召唤师图标数据资源可通过以下链接获取：<br>The raw summoner icon data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-icons.json`''')]
dsLoLChampions = Annotated[dict[int, dict[str, Any]], Description('''整理后的英雄数据资源。键是英雄序号，值是英雄信息字典。<br>Organized champion data resource. Each key is a championId, and each value is a champion information dictionary.
    
        原始英雄数据资源可通过以下链接获取：<br>The raw champion data resource can be obtained through the following links:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champions/{championId}.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/champion-summary.json`
        - `GET /lol-game-data/assets/v1/champions/{championId}.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`''')]
dsChampionSkins = Annotated[dict[int, dict[str, Any]], Description('''整理后的英雄皮肤数据资源。键是皮肤序号，值是皮肤信息字典。<br>Organized champion skin data resource. Each key is a skinId, and each value is a skin information dictionary.
    
        原始英雄皮肤数据资源可通过以下链接获取：<br>The raw champion skin data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/skins.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoints:
        - `GET /lol-game-data/assets/v1/skins.json`
        - `GET /lol-champions/v1/inventories/{summonerId}/champions`''')]
dsSpells = Annotated[dict[int, dict[str, Any]], Description('''整理后的召唤师技能数据资源。键是召唤师技能序号，值是召唤师技能信息字典。<br>Organized summoner spell data resource. Each key is a spellId, and each value is a summoner spell information dictionary.
    
        原始召唤师技能数据资源可通过以下链接获取：<br>The raw summoner spell data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/summoner-spells.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/summoner-spells.json`''')]
dsWardSkins = Annotated[dict[int, dict[str, Any]], Description("整理后的饰品皮肤数据资源。键是皮肤序号，值是皮肤信息字典。<br>Organized ward skin data resource. Each key is a skinId, and each value is a skin information dictionary.")]
dsLoLItems = Annotated[dict[int, dict[str, Any]], Description('''整理后的英雄联盟装备信息。键是装备序号，值是装备信息字典。<br>Organized LoL item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始英雄联盟装备数据资源可通过以下链接获取：<br>The raw LoL item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/items.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/items.json`''')]
dsPerks = Annotated[dict[int, dict[str, Any]], Description('''整理后的符文信息。键是符文序号，值是符文信息字典。<br>Organized perk data resource. Each key is a perkId, and each value is a perk information dictionary.
    
        原始符文数据资源可通过以下链接获取：<br>The raw perk data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perks.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perks.json`''')]
dsPerkstyles = Annotated[dict[int, dict[str, Any]], Description('''整理后的符文系信息。键是符文系序号，值是符文系信息字典。<br>Organized perkstyle data resource. Each key is a perkstyleId, and each value is a perkstyle information dictionary.
    
        原始符文系数据资源可通过以下链接获取：<br>The raw perkstyle data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/perkstyles.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/perkstyles.json`''')]
dsCherryAugments = Annotated[dict[int, dict[str, Any]], Description('''整理后的斗魂竞技场强化符文信息。键是强化符文序号，值是强化符文信息字典。<br>Organized Arena augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始斗魂竞技场强化符文数据资源可通过以下链接获取：<br>The raw Arena augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/cherry-augments.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/cherry-augments.json`''')]
dsTFTAugments = Annotated[dict[str, dict[str, Any]], Description('''整理后的云顶之弈强化符文数据资源。键是强化符文代码，值是强化符文信息字典。<br>Organized TFT augment data resource. Each key is an augmentId, and each value is an augment information dictionary.
    
        原始云顶之弈强化符文数据资源可通过以下链接获取：<br>The raw TFT augment data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/cdragon/tft/en_us.json''')]
dsTFTChampions = Annotated[dict[str, dict[str, Any]], Description('''整理后的云顶之弈英雄数据资源。键是英雄代码，值是英雄信息字典。<br>Organized TFT champion data resource. Each key is a championid, and each value is a champion information dictionary.
    
        原始云顶之弈英雄数据资源可通过以下链接获取：<br>The raw TFT champion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftchampions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftchampions.json`''')]
dsTFTItems = Annotated[dict[int, dict[str, Any]], Description('''整理后的云顶之弈装备信息。键是装备代码，值是装备信息字典。<br>Organized TFT item data resource. Each key is an itemId, and each value is an item information dictionary.
    
        原始云顶之弈装备数据资源可通过以下链接获取：<br>The raw TFT item data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tftitems.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tftitems.json`''')]
dsTFTCompanions = Annotated[dict[str, dict[str, Any]], Description('''整理后的小小英雄信息。键是小小英雄代码，值是小小英雄信息字典。<br>Organized companion data resource. Each key is a companionId, and each value is a companion information dictionary.
    
        原始小小英雄数据资源可通过以下链接获取：<br>The raw companion data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/companions.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/companions.json`''')]
dsTFTTraits = Annotated[dict[str, dict[str, Any]], Description('''整理后的云顶之弈羁绊信息。键是羁绊代码，值是羁绊信息字典。<br>Organized TFT trait data resource. Each key is a traitId, and each value is a trait information dictionary.
    
        原始云顶之弈羁绊数据资源可通过以下链接获取：<br>The raw TFT trait data resource can be obtained through the following link:
        - https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/tfttraits.json
        
        也可以通过以下LCU接口获取：<br>It can also be obtained from the following LCU endpoint:
        - `GET /lol-game-data/assets/v1/tfttraits.json`''')]
dsCurrent_versions = Annotated[dict[int, dict[str, Any]], Description("各数据资源目前正在使用的版本信息。<br>Current patches of data resources.")]
dsUnmapped_keys = Annotated[dict[str, set[int]], Description("各数据资源未找到的键。用于控制数据未找到匹配记录的提示最多输出一次。<br>Unmapped keys in all data resources, used to control the hint about data not found to be printed at most once.")]
dsLogManager = Annotated[LogManager, Description("日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.")]
dsVerbose = Annotated[bool, Description("日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.")]
