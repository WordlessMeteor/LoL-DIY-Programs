from lcu_driver.connection import Connection
import json, os, pandas, sys, time
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.utils.logger import LogManager
from src.utils.summoner import get_info
from src.utils.format import optimize_bool_display
from src.core.config.headers import game_leaderboard_header
from src.core.config.localization import queueTypes_ranked, tiers, ratedTiers_turbo, ratedTiers_cherry

def get_tier_name(tier: str, isCherry: bool = False) -> str:
    '''
    获取一个段位的本地化名称。<br>Get a tier's localized name.

    :param tier: 段位。可以是胜点段位，也可以是排名分段位。<br>Tier. Can be either a LP tier or a rated tier.
    
        必须是本地化模块的`tiers`、`ratedTiers_turbo`或`ratedTiers_cherry`中的一个键，否则则会引发键错误。<br>This must be one of the keys of `tiers`, `ratedTiers_turbo` or `ratedTiers_cherry`, or a KeyError will be thrown.
    :type tier: str
    :param isCherry: 排名分段位是否属于斗魂竞技场。默认为假。<br>Whether the rated tier belongs to Arena. False by default.
    
        斗魂竞技场和云顶之弈狂暴模式对于相同的排名分段位代码的翻译有所不同。<br>Arena and TFT Turbo have different translations of the same rated tier code.
    :return: 段位本地化名称。<br>Tier localized name.
    :rtype: str
    '''
    return tiers[tier] if tier in tiers else ratedTiers_cherry[tier] if isCherry else ratedTiers_turbo[tier]

async def sort_game_leaderboard(connection: Connection, queueTypes_list: Optional[list[str]] = None, puuids: Optional[list[str]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> pandas.DataFrame:
    '''
    整理多名玩家的排位信息，形成对局排行表。<br>Organize multiple players' ranked information into a game leaderboard dataframe.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param queueTypes_list: 排位队列列表。如果未指定，则默认使用所有队列。<br>Ranked queue type list. If unspecified, all ranked queues will be used.
    
        所有排位队列列举如下：<br>All ranked queues are listed as follows:
        - RANKED_SOLO_5x5: 排位赛 单排/双排 -- Ranked Solo/Duo
        - RANKED_FLEX_SR: 排位赛 灵活排位 -- Ranked Flex
        - RANKED_TFT: 云顶之弈（排位赛） -- Teamfight Tactics (Ranked)
        - RANKED_TFT_PAIRS: 云顶之弈（双人作战） -- Teamfight Tactics (Double Up)
        - RANKED_TFT_DOUBLE_UP: 云顶之弈（双人作战） -- Teamfight Tactics (Double Up)
        - RANKED_TFT_TURBO: 云顶之弈（狂暴模式） -- Teamfight Tactics (Hyper Roll)
        - CHERRY: 斗魂竞技场 -- Arena
    :type queueTypes_list: list[str]
    :param puuids: 要查询的玩家的玩家通用唯一识别码列表。<br>A list of puuids of players to query.
    :type puuids: list[str]
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 对局排行榜数据框。<br>A game leaderboard dataframe.
    :rtype: Match leaderboard dataframe.
    '''
    if queueTypes_list == None:
        queueTypes_list = []
    if puuids == None:
        puuids = []
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    challenger_ladder_queueTypes: list[str] = await (await connection.request("GET", "/lol-ranked/v1/challenger-ladders-enabled")).json()
    topRated_ladder_queueTypes: list[str] = await (await connection.request("GET", "/lol-ranked/v1/top-rated-ladders-enabled")).json()
    if queueTypes_list == []:
        queueTypes_list = challenger_ladder_queueTypes + topRated_ladder_queueTypes
    game_leaderboard_header_keys: list[str] = list(game_leaderboard_header.keys())
    game_leaderboard_data: dict[str, list[Any]] = {key: [] for key in game_leaderboard_header_keys}
    for queueType in queueTypes_list:
        params: dict[str, str] = {"queueType": queueType, "puuids": json.dumps(puuids, ensure_ascii = False)}
        game_leaderboard: dict[str, dict[str, Any]] = await (await connection.request("GET", "/lol-ranked/v1/social-leaderboard-ranked-queue-stats-for-puuids", params = params)).json()
        for participant_puuid_iter in game_leaderboard:
            participant_leaderboard: dict[str, Any] = game_leaderboard[participant_puuid_iter]
            participantInfo: dict[str, Any] = await get_info(connection, participant_puuid_iter)
            if participantInfo["info_got"]:
                participantInfo_body: dict[str, Any] = participantInfo["body"]
                for i in range(len(game_leaderboard_header_keys)):
                    key: str = game_leaderboard_header_keys[i]
                    if i <= 3:
                        to_append: Any = participantInfo_body[key]
                    elif i <= 15:
                        if i == 4: #分级（`division`）
                            to_append = "" if participant_leaderboard["division"] == "NA" else participant_leaderboard["division"]
                        elif i == 11: #战区（`queueType`）
                            to_append = queueTypes_ranked[participant_leaderboard["queueType"]]
                        elif i == 13: #段位（`ratedTier`）
                            to_append = ratedTiers[participant_leaderboard["ratedTier"]]
                        elif i == 14: #段位（`tier`）
                            to_append = tiers[participant_leaderboard["tier"]]
                        else:
                            to_append = participant_leaderboard[key]
                    elif i == 16: #段位（`tier / ratedTier`）
                        to_append = ratedTiers[participant_leaderboard["ratedTier"]] if queueType in topRated_ladder_queueTypes else tiers[participant_leaderboard["tier"]]
                    elif i == 17: #胜点（`leaguePoints / ratedRating`）
                        to_append = participant_leaderboard["ratedRating"] if queueType in topRated_ladder_queueTypes else participant_leaderboard["leaguePoints"]
                    elif i == 18: #获取时间戳（`timestamp`）
                        to_append = time.time()
                    else: #获取时间（`time`）
                        to_append = time.strftime("%Y年%m月%d日%H时%M分%S秒", time.localtime())
                    game_leaderboard_data[key].append(to_append)
            else:
                logPrint(participantInfo["message"], verbose = verbose)
    game_leaderboard_statistics_output_order: list[int] = [11, 1, 2, 3, 0, 16, 4, 17, 15, 7, 5, 9, 10, 8, 19]
    game_leaderboard_data_organized: dict[str, Any] = {game_leaderboard_header_keys[i]: game_leaderboard_data[game_leaderboard_header_keys[i]] for i in game_leaderboard_statistics_output_order}
    game_leaderboard_df: pandas.DataFrame = pandas.DataFrame(data = game_leaderboard_data_organized)
    optimize_bool_display(game_leaderboard_df)
    game_leaderboard_df = pandas.concat([pandas.DataFrame([game_leaderboard_header])[game_leaderboard_df.columns], game_leaderboard_df], ignore_index = True)
    return game_leaderboard_df
