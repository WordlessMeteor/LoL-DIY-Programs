from lcu_driver.connection import Connection
import json, os, sys
from typing import Any
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.core.config.localization import language_ddragon
from src.utils.summoner import get_info_name

#大区数据（Servers/Platforms）
platform_TENCENT: dict[str, str] = {
    "BGP1": "全网通区 男爵领域（Baron Zone）",
    "BGP2": "峡谷之巅（Super Zone）",
    "EDU1": "教育网专区（CRENET Server）",
    "HN1": "电信一区 艾欧尼亚（Ionia）",
    "HN2": "电信二区 祖安（Zaun）",
    "HN3": "电信三区 诺克萨斯（Noxus 1）",
    "HN4": "电信四区 班德尔城（Bandle City）",
    "HN4_NEW": "电信四区 班德尔城（Bandle City）",
    "HN5": "电信五区 皮尔特沃夫（Piltover）",
    "HN6": "电信六区 战争学院（the Institute of War）",
    "HN7": "电信七区 巨神峰（Mount Targon）",
    "HN8": "电信八区 雷瑟守备（Noxus 2）",
    "HN9": "电信九区 裁决之地（the Proving Grounds）",
    "HN10": "电信十区 黑色玫瑰（the Black Rose）",
    "HN11": "电信十一区 暗影岛（Shadow Isles）",
    "HN12": "电信十二区 钢铁烈阳（the Iron Solari）",
    "HN13": "电信十三区 水晶之痕（Crystal Scar）",
    "HN14": "电信十四区 均衡教派（the Kinkou Order）",
    "HN15": "电信十五区 影流（the Shadow Order）",
    "HN16": "电信十六区 守望之海（Guardian's Sea）",
    "HN17": "电信十七区 征服之海（Conqueror's Sea）",
    "HN18": "电信十八区 卡拉曼达（Kalamanda）",
    "HN19": "电信十九区 皮城警备（Piltover Wardens）",
    "WT1": "网通一区 比尔吉沃特（Bilgewater）",
    "WT1_NEW": "网通一区 比尔吉沃特（Bilgewater）",
    "WT2": "网通二区 德玛西亚（Demacia）",
    "WT2_NEW": "网通二区 德玛西亚（Demacia）",
    "WT3": "网通三区 弗雷尔卓德（Freljord）",
    "WT3_NEW": "网通三区 弗雷尔卓德（Freljord）",
    "WT4": "网通四区 无畏先锋（House Crownguard）",
    "WT4_NEW": "网通四区 无畏先锋（House Crownguard）",
    "WT5": "网通五区 恕瑞玛（Shurima）",
    "WT6": "网通六区 扭曲丛林（Twisted Treeline）",
    "WT7": "网通七区 巨龙之巢（the Dragon Camp）",
    "NJ100": "联盟一区",
    "GZ100": "联盟二区",
    "CQ100": "联盟三区",
    "TJ100": "联盟四区",
    "TJ101": "联盟五区",
    "PBE": "体验服 试炼之地（Chinese PBE）", #也译为云顶之巅（Also known as "TOC"）
    "FORCES": "比赛服 艾欧尼亚（Tournament - Ionia）",
    "PREPBE": "试炼之地 临时过渡服务器（Chinese PBE Temporary）",
}
platform_RIOT: dict[str, str] = {
    "ME1": "中东服（Middle East）",
    "BR1": "巴西服（Brazil）",
    "EUN1": "北欧和东欧服（Europe Nordic & East）",
    "EUW1": "西欧服（Europe West）",
    "JP1": "日服（Japan）",
    "KR": "韩服（Republic of Korea）",
    "LA1": "北拉美服（Latin America North）",
    "LA2": "南拉美服（Latin America South）",
    "NA1": "北美服（North America）",
    "OC1": "大洋洲服（Oceania）",
    "TR1": "土耳其服（Turkey）",
    "RU": "俄罗斯服（Russia）",
    "PH2": "菲律宾服（Philippines）",
    "SG2": "新加坡服（Singapore）",
    "TH2": "泰服（Thailand）",
    "TW2": "台服（Taiwan, Hong Kong and Macau）",
    "VN2": "越南服（Vietnam）",
    "PBE1": "测试服（Public Beta Environment）"
} #顺序采用参考开发者传送门网站的服务器路由（The order refers to Platform Routing Values on Riot Developer Portal website）
platform_GARENA: dict[str, str] = {
    "PH1": "菲律宾服（Philippines）",
    "SG1": "新加坡服（Singapore, Malaysia and Indonesia）",
    "TW1": "台服（Taiwan, Hong Kong and Macau）",
    "VN1": "越南服（Vietnam）",
    "TH1": "泰服（Thailand）"
} #顺序采用英雄联盟维基百科的“Server”词条的竞舞代理的服务器（The order refers to Garena servers in "Server" entry of League Wiki）
valid_platformIds: set[str] = set(platform_TENCENT.keys()) | set(platform_RIOT.keys()) | set(platform_GARENA.keys())
regions: dict[str, str] = {
    "TENCENT": "国服（TENCENT）",
    "RIOT": "外服（RIOT）",
    "GARENA": "竞舞（GARENA）"
}
hosts: dict[str, str] = {
    "HN1": "https://hn1-k8s-sgp.lol.qq.com:21019",
    "HN10": "https://hn10-k8s-sgp.lol.qq.com:21019",
    "BGP2": "https://bgp2-k8s-sgp.lol.qq.com:21019",
    "NJ100": "https://nj100-sgp.lol.qq.com:21019",
    "GZ100": "https://gz100-sgp.lol.qq.com:21019",
    "CQ100": "https://cq100-sgp.lol.qq.com:21019",
    "TJ100": "https://tj100-sgp.lol.qq.com:21019",
    "TJ101": "https://tj101-sgp.lol.qq.com:21019",
    "PBE": "https://pbe-sgp.lol.qq.com:21019",
    "PREPBE": "https://prepbe-sgp.lol.qq.com:21019",
    "LDL": "https://ldl-sgp.lol.qq.com:21019",
    "FORCES_NEW": "https://forces-new-sgp.lol.qq.com:21019",
    "NA1": "https://usw2-red.pp.sgp.pvp.net",
    "LA1": "https://usw2-red.pp.sgp.pvp.net",
    "LA2": "https://usw2-red.pp.sgp.pvp.net",
    "JP1": "https://apne1-red.pp.sgp.pvp.net",
    "KR": "https://apne1-red.pp.sgp.pvp.net",
    "TW2": "https://apse1-red.pp.sgp.pvp.net",
    "SG2": "https://apse1-red.pp.sgp.pvp.net",
    "OC1": "https://apse1-red.pp.sgp.pvp.net",
    "EUN1": "https://euc1-red.pp.sgp.pvp.net",
    "EUW1": "https://euc1-red.pp.sgp.pvp.net",
    "TR1": "https://euc1-red.pp.sgp.pvp.net",
    "RU": "https://euc1-red.pp.sgp.pvp.net",
    "ME1": "https://euc1-red.pp.sgp.pvp.net",
    "PBE1": "https://usw2-red.pp.sgp.pvp.net"
} #这个变量目前并未投入使用（This variable isn't put to use for now）

def set_platform_folder(region: str, platformId: str) -> str:
    '''
    通过大区和服务器代号设置大区文件夹。<br>Set the platform folder through region and platformId.
    
    :param region: 大区。有以下选项：<br>Region. Options are as follows:
    
        - TENCENT: 腾讯游戏
        - GARENA: 竞舞娱乐
        - RIOT: 拳头游戏
        
        可通过以下LCU接口得到：<br>Obtained by the folowing LCU endpoint:
        
        - `GET /riotclient/region-locale`
        - `GET /riotclient/command-line-args`
    :type region: str
    :param platformId: 服务器代号。可通过以下LCU接口得到：<br>PlatfromId, which can be obtained by any of the following LCU endpoints:
    
        - `GET /lol-lobby/v1/parties/player`
        - `GET /riotclient/command-line-args` (Only for Tencent servers)
    :type platformId: str
    :return: 大区文件夹路径。对主目录的相对路径。<br>Platform folder path. Relative to the home directory.
    :rtype: str
    '''
    if region == "TENCENT":
        platform_folder: str = "召唤师信息（Summoner Information）/国服（TENCENT）/%s" %(platform_TENCENT[platformId])
    elif region == "GARENA":
        platform_folder = "召唤师信息（Summoner Information）/竞舞（GARENA）/%s" %(platform_GARENA[platformId])
    else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
        platform_folder = "召唤师信息（Summoner Information）/外服（RIOT）/%s" %((platform_RIOT | platform_GARENA)[platformId])
    return platform_folder

def set_summonerInfo_folder(region: str, platformId: str, info: dict[str, Any]) -> str:
    '''
    通过大区、服务器代号和召唤师信息设置召唤师文件夹。<br>Set the summoner folder through region, platformId and summoner information.
    
    :param region: 大区。有以下选项：<br>Region. Options are as follows:
    
        - TENCENT: 腾讯游戏
        - GARENA: 竞舞娱乐
        - RIOT: 拳头游戏
        
        可通过以下LCU接口得到：<br>Obtained by the folowing LCU endpoint:
        
        - `GET /riotclient/region-locale`
        - `GET /riotclient/command-line-args`
    :type region: str
    :param platformId: 服务器代号。可通过以下LCU接口得到：<br>PlatfromId, which can be obtained by any of the following LCU endpoints:
    
        - `GET /lol-lobby/v1/parties/player`
        - `GET /riotclient/command-line-args` (Only for Tencent servers)
    :type platformId: str
    :param info: 召唤师信息。可通过以下LCU接口得到：<br>Summoner information, which can be obtained by any of the following LCU endpoints:
    
        - `GET /lol-summoner/v1/current-summoner`
        - `GET /lol-summoner/v1/summoners?name={name}`
        - `GET /lol-summoner/v2/summoners/puuid/{puuid}`
    :type info: dict[str, Any]
    :return: 召唤师文件夹路径。对主目录的相对路径。<br>Summoner folder path. Relative to the home directory.
    :rtype: str
    '''
    platform_folder = set_platform_folder(region, platformId)
    if region == "TENCENT":
        summonerInfo_folder: str = platform_folder + "/" + get_info_name(info, 2)
    elif region == "GARENA":
        summonerInfo_folder = platform_folder + "/" + get_info_name(info, 2)
    else:
        summonerInfo_folder = platform_folder + "/" + get_info_name(info, 3)
    return summonerInfo_folder

def set_rankedApex_folder(region: str, platformId: str, currentLoLSeasonId: int, currentLoLSeasonSplitId: int) -> str:
    '''
    通过大区、服务器代号和当前赛季序号设置赛季天梯文件夹。<br>Set the seasonal apex folder through region, platformId and current season number.
    
    :param region: 大区。有以下选项：<br>Region. Options are as follows:
    
        - TENCENT: 腾讯游戏
        - GARENA: 竞舞娱乐
        - RIOT: 拳头游戏
        
        可通过以下LCU接口得到：<br>Obtained by the folowing LCU endpoint:
        
        - `GET /riotclient/region-locale`
        - `GET /riotclient/command-line-args`
    :type region: str
    :param platformId: 服务器代号。可通过以下LCU接口得到：<br>PlatfromId, which can be obtained by any of the following LCU endpoints:
    
        - `GET /lol-lobby/v1/parties/player`
        - `GET /riotclient/command-line-args` (Only for Tencent servers)
    :type platformId: str
    :param currentLoLSeasonId: 当前赛季序号。可通过以下LCU接口得到：<br>Current season number, which can be obtained by the following LCU endpoint:
    
        - `GET /lol-seasons/v1/season/product/LOL`
    :type currentLoLSeasonId: int
    :param currentLoLSeasonSplitId: 当前赛段序号。现已弃用。<br>Current split number. Deprecated now.
    :type currntSplit: int
    :return: 赛季天梯文件夹路径。对主目录的相对路径。<br>Seasonal apex folder path. Relative to the home directory.
    :rtype: str
    '''
    if region == "TENCENT":
        apex_folder: str = "顶尖排位玩家（Ranked Apex）/国服（TENCENT）/%s/第%d赛季 - 第%d赛段（SEASON %d - Split %d）" %(platform_TENCENT[platformId], currentLoLSeasonId, currentLoLSeasonSplitId, currentLoLSeasonId, currentLoLSeasonSplitId)
    elif region == "GARENA":
        apex_folder = "顶尖排位玩家（Ranked Apex）/竞舞（GARENA）/%s/第%d赛季 - 第%d赛段（SEASON %d - Split %d）" %(platform_GARENA[platformId], currentLoLSeasonId, currentLoLSeasonSplitId, currentLoLSeasonId, currentLoLSeasonSplitId)
    else: #拳头公司与竞舞娱乐公司的合同于2023年1月终止（In January 2023, Riot Games ended its contract with Garena）
        apex_folder = "顶尖排位玩家（Ranked Apex）/外服（RIOT）/%s/第%d赛季 - 第%d赛段（SEASON %d - Split %d）" %((platform_RIOT | platform_GARENA)[platformId], currentLoLSeasonId, currentLoLSeasonSplitId, currentLoLSeasonId, currentLoLSeasonSplitId)
    return apex_folder

async def save_platform_info(connection: Connection, print_summary: bool = True) -> None:
    '''
    在与联盟客户端创建连接时，保存大区的配置信息到大区文件夹内。<br>Upon building a connection with League Client, save the platform configuration into the local platform folder.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param print_summary: 是否输出当前大区和客户端的标识性信息。默认为真。<br>Whether to print some representative information of the current server and client. True by default.
    :type print_summary: bool
    '''
    #准备数据资源（Prepare data resources）
    platform_config: dict[str, Any] = await (await connection.request("GET", "/lol-platform-config/v1/namespaces")).json()
    current_party: dict[str, Any] = await (await connection.request("GET", "/lol-lobby/v1/parties/player")).json()
    riot_client_info: dict[str, str] = await (await connection.request("GET", "/riotclient/command-line-args")).json()
    client_settings: dict[str, Any] = await (await connection.request("GET", "/client-config/v2/namespace/lol.client_settings")).json()
    if isinstance(platform_config, dict) and "errorCode" in platform_config:
        print(platform_config)
        if platform_config["httpStatus"] == 400 and platform_config["message"] == "PLATFORM_CONFIG_NOT_READY":
            print("大区信息未准备就绪。\nPlatform config not ready.")
    elif current_party["platformId"] == "":
        print("小队信息未准备就绪。\nParty information not ready.")
    else:
        #确定大区信息文件夹参数（Determine parameters of the platform folder）
        platformId: str = current_party["platformId"]
        client_info: dict[str, str] = {}
        for i in range(len(riot_client_info)):
            try:
                client_info[riot_client_info[i].split("=")[0]] = riot_client_info[i].split("=")[1]
            except IndexError:
                pass
        region: str = client_info["--region"]
        if print_summary: #打印大区信息（Print server information）
            print("region:         %s" %region)
            print("platformId:     %s" %platformId)
            print("Server name:    %s" %((platform_TENCENT | platform_RIOT)[platformId]))
            region_locale: dict[str, str] = await (await connection.request("GET", "/riotclient/region-locale")).json()
            print("locale:         %s" %(region_locale["locale"]))
            print("Language:       %s" %(language_ddragon[region_locale["locale"]]["desc_local"]))
            print("-")
        #保存Json文件（Save the json file）
        platform_folder: str = set_platform_folder(region, platformId)
        os.makedirs(platform_folder, exist_ok = True)
        platform_config_filepath: str = platform_folder + "/platform_config_namespaces.json"
        with open(platform_config_filepath, "w", encoding = "utf-8") as fp:
            json.dump(platform_config, fp, indent = 4, ensure_ascii = False)
        cmdline_arg_filepath: str = platform_folder + "/command_line_args.json"
        with open(cmdline_arg_filepath, "w", encoding = "utf-8") as fp:
            json.dump(riot_client_info, fp, indent = 4, ensure_ascii = False)
        client_settings_filepath: str = platform_folder + "/client_settings.json"
        with open(client_settings_filepath, "w", encoding = "utf-8") as fp:
            json.dump(client_settings, fp, indent = 4, ensure_ascii = False)
