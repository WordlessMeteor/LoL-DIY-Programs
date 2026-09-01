from lcu_driver.connection import Connection
from typing import Any

async def build_inventory_map(connection: Connection) -> dict[str, dict[Any, dict[str, str]]]:
    '''
    创建各种道具类型从道具序号到名称和描述的映射。<br>Build the map from itemIds to names and descriptions for all kinds of inventory types.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :return: 综合索引字典。一级键是道具类型，二级键是道具序号或标识符，值是名称和描述组成的对象。<br>Universal index dictionary, whose level-1 keys are inventory types, level-2 keys are itemIds and values are objects composed of a name and a description.
    :rtype: dict[str, dict[Any, dict[str, str]]]
    '''
    #准备数据资源（Prepare data resources）
    ##皮肤（Champion skin）
    championSkins_source: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/skins.json")).json()
    ##云顶之弈小小英雄（TFT companion）
    companions_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/companions.json")).json()
    ##水晶枢纽终结特效（Nexus finisher）
    nexusfinishers_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/nexusfinishers.json")).json()
    ##永恒星碑（Statstone）
    statstones_source: dict[str, Any] = await (await connection.request("GET", "/lol-game-data/assets/v1/statstones.json")).json()
    ##无尽狂潮基础信息（Swarm basic）
    strawberryHub_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/strawberry-hub.json")).json()
    ##表情（Emote）
    summonerEmotes_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-emotes.json")).json()
    ##召唤师图标（Summoner icon）
    summonerIcons_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/summoner-icons.json")).json()
    ##云顶之弈攻击特效（TFT damage skin）
    tftdamageskins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftdamageskins.json")).json()
    ##云顶之弈棋盘皮肤（TFT map skin）
    tftmapskins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftmapskins.json")).json()
    ##云顶之弈指导手册（TFT playbook）
    tftplaybooks_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftplaybooks.json")).json()
    ##云顶之弈传送门皮肤（TFT zoom skin）
    tftzoomskins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/tftzoomskins.json")).json()
    ##饰品（Ward skin）
    wardSkins_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/ward-skins.json")).json()
    ##道具类型（Inventory type）
    lolinventorytype_source: list[dict[str, Any]] = await (await connection.request("GET", "/lol-game-data/assets/v1/lolinventorytype.json")).json()
    lolinventorytypes: dict[str, dict[str, Any]] = {x["inventoryTypeId"]: x for x in lolinventorytype_source}
    #下面定义对应关系表（The following code define the table for mapping）
    ##皮肤（Champion skin)
    championSkins_hashtable: dict[int, dict[str, str]] = {} #对于特定道具类型的商品，道具序号可唯一确定一件商品。下同（As for an item of specific inventory type, the itemId can uniquely correspond to that item. So can the following）
    for skin in championSkins_source.values():
        championSkins_hashtable[skin["id"]] = {"name": skin["name"], "description": skin["description"]}
        if "chromas" in skin:
            for chroma in skin["chromas"]:
                championSkins_hashtable[chroma["id"]] = {"name": chroma["name"], "description": ""}
                for desc in chroma["descriptions"]:
                    if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1:
                        championSkins_hashtable[chroma["id"]]["description"] = desc["description"]
                        break
        if "questSkinInfo" in skin:
            for tier in skin["questSkinInfo"]["tiers"]:
                championSkins_hashtable[tier["id"]] = {"name": tier["name"], "description": tier["description"]}
    ##云顶之弈小小英雄（TFT companion）
    companions_hashtable: dict[str, dict[str, str]] = {companion["itemId"]: {"name": companion["name"], "description": companion["description"]} for companion in companions_source}
    ##水晶枢纽终结特效（Nexus finisher）
    nexusfinishers_hashtable: dict[int, dict[str, str]] = {nexusfinisher["itemId"]: {"name": nexusfinisher["name"], "description": nexusfinisher["translatedDescription"]} for nexusfinisher in nexusfinishers_source}
    ##永恒星碑（Statstone）
    statstones_hashtable: dict[int, dict[str, str]] = {statstone["itemId"]: {"name": statstone["name"], "description": statstone["description"]} for statstone in statstones_source["packData"]}
    ##无尽狂潮基础信息（Swarm basic）
    strawberryBoons_hashtable: dict[str, dict[str, str]] = {} #注意，PVE模式的相关索引都是识别码（Note that index of PBE mode data is itemInstanceId）
    strawberryLoadoutItems_hashtable: dict[str, dict[str, str]] = {}
    strawberryMaps_hashtable: dict[str, dict[str, str]] = {}
    if len(strawberryHub_source) > 0:
        for strawberryMap in strawberryHub_source[0]["MapDisplayInfoList"]:
            strawberryMaps_hashtable[strawberryMap["value"]["Map"]["ContentId"]] = {"name": strawberryMap["value"]["Name"], "description": strawberryMap["value"]["Bark"]}
        for ProgressGroup in strawberryHub_source[0]["ProgressGroups"]:
            for Milestone in ProgressGroup["value"]["Milestones"]:
                for Property in Milestone["value"]["Properties"]:
                    for Reward in Property["Rewards"]:
                        if all(key in Reward for key in ["Title", "Details", "ItemId", "ItemType"]) and "CapInventoryTypeId" in Reward["ItemType"]:
                            if Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_BOON"]["capInventoryTypeId"]:
                                if Reward["ItemId"] in strawberryBoons_hashtable:
                                    if not "name" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["name"] == "":
                                        strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                    if not "description" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["description"] == "":
                                        strawberryBoons_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                                else:
                                    strawberryBoons_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": Property["Name"]}
                            elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                                if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                                    if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                                        strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                    if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                                        strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                                else:
                                    strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": Property["Name"]}
                            elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                                if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                                    if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here assume an empty dictionary has been created for this map before）
                                        strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                                    if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                                        strawberryMaps_hashtable[Reward["ItemId"]]["description"] = Property["Name"]
                                    else:
                                        strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + Property["Name"]
                                else:
                                    strawberryMaps_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": Property["Name"]}
        for PowerUpGroup in strawberryHub_source[0]["PowerUpGroups"]:
            for Boon in PowerUpGroup["value"]["Boons"]:
                if Boon["value"]["ContentId"] in strawberryBoons_hashtable:
                    if not "name" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] == "":
                        strawberryBoons_hashtable[Boon["value"]["ContentId"]]["name"] = PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"]
                    if not "description" in strawberryBoons_hashtable[Boon["value"]["ContentId"]] or strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] == "":
                        strawberryBoons_hashtable[Boon["value"]["ContentId"]]["description"] = PowerUpGroup["value"]["Description"]
                else:
                    strawberryBoons_hashtable[Boon["value"]["ContentId"]] = {"name": PowerUpGroup["value"]["Name"] + " " + Boon["value"]["ShortValueSummary"], "description": PowerUpGroup["value"]["Description"]}
        for EoGNarrativeBark in strawberryHub_source[0]["EoGNarrativeBarks"]:
            for Reward in EoGNarrativeBark["value"]["RewardGroup"]["Rewards"]:
                if all(key in Reward for key in ["Title", "Details", "ItemId", "ItemType"]) and "CapInventoryTypeId" in Reward["ItemType"]:
                    if Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_BOON"]["capInventoryTypeId"]:
                        if Reward["ItemId"] in strawberryBoons_hashtable:
                            if not "name" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["name"] == "":
                                strawberryBoons_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                            if not "description" in strawberryBoons_hashtable[Reward["ItemId"]] or strawberryBoons_hashtable[Reward["ItemId"]]["description"] == "":
                                strawberryBoons_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                        else:
                            strawberryBoons_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": EoGNarrativeBark["value"]["RewardGroup"]["name"]}
                    elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_LOADOUT_ITEM"]["capInventoryTypeId"]:
                        if Reward["ItemId"] in strawberryLoadoutItems_hashtable:
                            if not "name" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] == "":
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                            if not "description" in strawberryLoadoutItems_hashtable[Reward["ItemId"]] or strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] == "":
                                strawberryLoadoutItems_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                        else:
                            strawberryLoadoutItems_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": EoGNarrativeBark["value"]["RewardGroup"]["name"]}
                    elif Reward["ItemType"]["CapInventoryTypeId"] == lolinventorytypes["STRAWBERRY_MAP"]["capInventoryTypeId"]:
                        if Reward["ItemId"] in strawberryMaps_hashtable and isinstance(strawberryMaps_hashtable[Reward["ItemId"]], dict):
                            if not "name" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["name"] == "": #这里假设前面已经对地图创建了空字典（Here suppose an empty dictionary has been created for this map before）
                                strawberryMaps_hashtable[Reward["ItemId"]]["name"] = Reward["Title"]
                            if not "description" in strawberryMaps_hashtable[Reward["ItemId"]] or strawberryMaps_hashtable[Reward["ItemId"]]["description"] == "":
                                strawberryMaps_hashtable[Reward["ItemId"]]["description"] = EoGNarrativeBark["value"]["RewardGroup"]["name"]
                            # else: #实际上在遍历模式进程分组时已经添加过地图激活要求信息了（Actually, when traversing the ProgressGroups, the program has added information of the requirement to activate maps）
                            #     strawberryMaps_hashtable[Reward["ItemId"]]["description"] += "<br>" + EoGNarrativeBark["value"]["RewardGroup"]["name"]
                        else:
                            strawberryMaps_hashtable[Reward["ItemId"]] = {"name": Reward["Title"], "description": EoGNarrativeBark["value"]["RewardGroup"]["name"]}
    ##表情（Emote）
    summonerEmotes_hashtable: dict[int, dict[str, str]] = {emote["id"]: {"name": emote["name"], "description": emote["description"]} for emote in summonerEmotes_source}
    ##召唤师图标（Summoner icon）
    summonerIcons_hashtable: dict[int, dict[str, str]] = {}
    for icon in summonerIcons_source:
        summonerIcons_hashtable[icon["id"]] = {}
        summonerIcons_hashtable[icon["id"]]["name"] = icon["title"]
        for desc in icon["descriptions"]:
            if desc["region"] == "riot" and len(set(list(desc["description"]))) != 1: #为简化代码，目前仅统计守卫（眼）在拳头大区的简介。有些简介是非空字符串，但是实际上是一堆空格（To simplify the code, only riot descriptions of wards are counted. Some descriptions are indeed non-empty strings but actually a bunch of spaces）
                summonerIcons_hashtable[icon["id"]]["description"] = desc["description"]
                break
        else:
            summonerIcons_hashtable[icon["id"]]["description"] = ""
    ##云顶之弈攻击特效（TFT damage skin）
    tftdamageskins_hashtable: dict[str, dict[str, str]] = {skin["itemId"]: {"name": skin["name"], "description": skin["description"]} for skin in tftdamageskins_source}
    ##云顶之弈棋盘皮肤（TFT map skin）
    tftmapskins_hashtable: dict[str, dict[str, str]] = {skin["itemId"]: {"name": skin["name"], "description": skin["description"]} for skin in tftmapskins_source}
    ##云顶之弈指导手册（TFT playbook）
    tftplaybooks_hashtable: dict[str, dict[str, str]] = {tftplaybook["itemId"]: {"name": tftplaybook["translatedName"], "description": tftplaybook["translatedDescription"]} for tftplaybook in tftplaybooks_source}
    ##云顶之弈传送门皮肤（TFT zoom skin）
    tftzoomskins_hashtable: dict[str, dict[str, str]] = {tftzoomskin["itemId"]: {"name": tftzoomskin["name"], "description": tftzoomskin["description"]} for tftzoomskin in tftzoomskins_source}
    ##饰品（Ward skin）
    wardSkins_hashtable: dict[int, dict[str, str]] = {skin["id"]: {"name": skin["name"], "description": skin["description"]} for skin in wardSkins_source}
    #以下类型的藏品在商品中也没有记录名称，需要借助其它接口来获取其名称（Collection items of the following types aren't recorded the names in catalog, so other APIs are required to get their names）
    ##头衔（Title）
    titles_all: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-challenges/v2/titles/all")).json()
    titles_hashtable: dict[int, dict[str, Any]] = {title["itemId"]: {"name": title["name"], "description": title["challengeTitleData"]["challengeDescription"] if title["challengeTitleData"] != None and "challengeDescription" in title["challengeTitleData"] else ""} for title in titles_all.values()}
    ##排位旗帜（Regalia banner）
    regaliaBanners: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_BANNER")).json()
    regaliaBanners_hashtable: dict[int, dict[str, str]] = {int(regaliaBanners[bannerId]["items"][0]["id"]): {"name": regaliaBanners[bannerId]["items"][0]["localizedName"], "description": regaliaBanners[bannerId]["items"][0]["localizedDescription"]} for bannerId in regaliaBanners}
    ##华冠（Regalia crest）
    # regaliaCrests: dict[str, Any] = await (await connection.request("GET", "/lol-regalia/v3/inventory/REGALIA_CREST")).json()
    #汇总（Summary）
    hashtable_dicts: dict[str, dict[Any, dict[str, str]]] = {"CHAMPION_SKIN": championSkins_hashtable, "COMPANION": companions_hashtable, "NEXUS_FINISHER": nexusfinishers_hashtable, "STATSTONE": statstones_hashtable, "STRAWBERRY_BOON": strawberryBoons_hashtable, "STRAWBERRY_LOADOUT_ITEM": strawberryLoadoutItems_hashtable, "STRAWBERRY_MAP": strawberryMaps_hashtable, "EMOTE": summonerEmotes_hashtable, "SUMMONER_ICON": summonerIcons_hashtable, "TFT_DAMAGE_SKIN": tftdamageskins_hashtable, "TFT_MAP_SKIN": tftmapskins_hashtable, "TFT_PLAYBOOK": tftplaybooks_hashtable, "TFT_ZOOM_SKIN": tftzoomskins_hashtable, "WARD_SKIN": wardSkins_hashtable, "ACHIEVEMENT_TITLE": titles_hashtable, "REGALIA_BANNER": regaliaBanners_hashtable}
    return hashtable_dicts