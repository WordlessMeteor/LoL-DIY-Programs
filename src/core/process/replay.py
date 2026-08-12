from lcu_driver.connection import Connection
import json, os, requests, sys
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.utils.webRequest import SGPSession

async def download_replay_lcu(connection: Connection, matchId: int) -> Optional[dict[str, Any]]:
    '''
    使用LCU API下载当前大区的英雄联盟回放。<br>Download League of Legends replays in current server using LCU API.

    提示：在国外的服务器上下载回放时，建议使用适当的VPN加速。<br>Hint: It's highly recommended that users use appropriate VPN to accelerate download When downloading replays from a foreign server.

    该函数不产生有效的返回值。<br>This function doesn't have any valid value to return.

    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param matchId: 对局序号。<br>GameId.
    :type matchId: int
    :return: 调用下载回放接口后的响应主体。<br>The response body after calling the replay downloading endpoint.
    :rtype: Optional[dict[str, Any]]
    '''
    #首先检查元数据是否已经准备就绪。在用户访问一名玩家的对局记录页时，客户端会更新当前页面内所有对局的状态（First, check if the metadata is ready. When the user accesses a player's MATCH HISTORY page / tab, League Client updates the status of all matches in this page）
    metadata: dict[str, Any] = await (await connection.request("GET", f"/lol-replays/v1/metadata/{matchId}")).json()
    if metadata == {"errorCode": "RPC_ERROR", "httpStatus": 404, "implementationDetails": {}, "message": "Plugin found no local metadata. Try using the POST metadata create endpoint first."}: #必须在有元数据的前提下才能下载回放（Metadata is required to download the replay）
        #获取对局概要（Get match summary）
        LoLGame_summary: dict[str, Any] = await (await connection.request("GET", f"/lol-match-history/v1/games/{matchId}")).json()
        #构建创建元数据接口的请求主体（Construct the request body of the endpoint that creates the metadata）
        if "errorCode" in LoLGame_summary: #这里不进行详细的异常处理。一旦出现错误，直接使用空请求数据，其实也是能够下载的（Detailed exception handling isn't performed here. Once an error occurs, an empty piece of request data will be used, which is enough for downloading a replay）
            requestData: dict[str, Any] = {"gameVersion": "", "gameType": "", "queueId": 0, "gameEnd": 0}
        else:
            requestData = {"gameVersion": LoLGame_summary["gameVersion"], "gameType": LoLGame_summary["gameType"], "queueId": LoLGame_summary["queueId"], "gameEnd": LoLGame_summary["gameCreation"] + LoLGame_summary["gameDuration"] + 1000} #这里的对局结束时间戳的结算方式可能不符合实际情况。但只要意思一下就够了（Here the algorithm of `gameEnd` might not fit the actual calculation. However, a rough approximation is sufficient）
        #创建元数据（Create metadata）
        response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-replays/v2/metadata/{matchId}/create", data = requestData)).json()
    #在元数据准备就绪后，下载回放（When metadata is ready, download the replay）
    contextData: dict[str, str] = {"componentType": "replay-button_match-history"}
    response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-replays/v1/rofls/{matchId}/download", data = contextData)).json()
    return response

async def download_replay_sgp(connection: Connection, sgpSession: SGPSession, match_id: str, rofl_path: str, product: str = "LoL") -> tuple[str, bool, str]:
    '''
    使用SGP API下载当前大区的英雄联盟回放。<br>Download League of Legends replays in current server using SGP API.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: SGP会话。<br>SGP Session.
    :type sgpSession: SGPSession
    :param match_id: 大区对局序号。由服务器代号和对局序号通过下划线连接而成。<br>Platform matchId, which is a platformId and a matchId concatenated by an underscore.
    :type match_id: str
    :param rofl_path: 回放路径。<br>Replay path.
    
        如果用户指定的路径已存在，程序会重命名待生成的文件。<br>If the rofl path already exists, the program will rename the generated file.
    :type rofl_path: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）（☆）
        - TFT: 云顶之弈（Teamfight Tactics）

        云顶之弈对局无法下载回放，所以一般选择英雄联盟。<br>A TFT match doesn't support downloading the match, so this parameter is always "LoL".
    :type product: Literal["LoL, "TFT"]
    :return: 一个三元组。<br>A 3-tuple.
    
        第一个元素是实际使用的下载路径。<br>The first element is the actually used download path.
        
        第二个元素是回放是否成功下载。当下载回放的请求返回二进制数据时，视为回放成功下载。<br>The second element is whether the replay is successfully downloaded. When the request to download the replay returns binary data, the function considers the replay has been successfully downloaded.
        
        第三个元素是消息字符串。<br>The third element is a message string.
    :rtype: tuple[str, bool, str]
    '''
    #参数预处理（Parameter preprocessing）
    if product != "TFT":
        product = "LoL"
    while os.path.exists(rofl_path): #避免覆盖已存在的回放文件而影响其创建时间。因为ReplayBook就依赖于文件创建时间来排序（Avoid overwriting an existing replay file and thus affecting its creation time. Because ReplayBook relies on the file creation time to sort the replays）
        rofl_path = "(1)".join(os.path.splitext(rofl_path))
    #初始化返回结果（Initialize returned result）
    replay_downloaded: bool = False
    message: str = ""
    #发送请求（Send request）
    source: requests.Response = await sgpSession.request(connection, "GET", f"/match-history-query/v3/product/LoL/matchId/{match_id}/infoType/replay", verbose = True)
    #异常处理（Exception handling）
    try:
        response: Any = source.json()
    except requests.exceptions.JSONDecodeError:
        content: bytes = source.content
        try:
            text: str = content.decode()
        except UnicodeDecodeError:
            with open(rofl_path, "wb") as fp:
                fp.write(content)
            replay_downloaded = True
        else:
            message = text
    except Exception as e: #AttributeError: 'NoneType' object has no attribute 'json'
        message = str(e)
    else:
        message = json.dumps(response)
    return (rofl_path, replay_downloaded, message)

async def watch_replay(connection: Connection, matchId: int) -> str:
    '''
    播放当前大区的英雄联盟回放。<br>Play a League of Legends replay in current server.

    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param matchId: 对局序号。<br>GameId.
    :type matchId: int
    :return: 消息字符串。<br>Message string.
    :rtype: str
    '''
    #初始化返回结果（Initialize returned result）
    message: str = ""
    #首先检查元数据是否已经准备就绪。在用户访问一名玩家的对局记录页时，客户端会更新当前页面内所有对局的状态（First, check if the metadata is ready. When the user accesses a player's MATCH HISTORY page / tab, League Client updates the status of all matches in this page）
    metadata: dict[str, Any] = await (await connection.request("GET", f"/lol-replays/v1/metadata/{matchId}")).json()
    if metadata == {"errorCode": "RPC_ERROR", "httpStatus": 404, "implementationDetails": {}, "message": "Plugin found no local metadata. Try using the POST metadata create endpoint first."}: #必须在有元数据的前提下才能下载回放（Metadata is required to download the replay）
        message: str = "尚未创建回放元数据。请在客户端内点击一次该玩家的对局记录页签，或者自行使用接口来创建元数据。\nReplay metadata not created yet. Please click this player's MATCH HISTORY tab once inside the League Client or use the endpoint to create metadata."
        state: str = ""
    else:
        state = metadata["state"]
        if state == "error":
            message = "你的下载出错了。\nThere was an error with your download."
        elif state == "unsupported":
            message = "回放不支持这个游戏模式。\nReplays are unsupported for this game mode."
        elif state == "lost":
            message = "这场对局的回放已丢失或不可用。\nThe replay for this game is missing and isn't available."
        elif state == "retryDownload":
            message = "你的下载出错了。点击此处重试。\nThere was an error with your download. Click here to try again."
        elif state == "missingOrExpired":
            message = "你的下载出问题了。\nThere was an error with your download."
        elif state == "incompatible":
            message = "回放已失效。\nThis Replay has expired."
        elif state == "downloading":
            message = "你的回放正在下载中。\nYour Replay is downloading."
        elif state == "download":
            message = "点击此处下载这场对局的回放。请注意，回放也可在比赛记录中下载，直到下个版本发布为止。\nClick here to download the Replay for this match. Replays will also be available for download on Match History until the next patch."
        elif state == "watch":
            message = "点击此处来观看你的回放。\nClick here to watch your Replay."
        elif state == "found":
            message = "回放已找到，正在排队下载。\nReplay found, queuing up for download."
        elif state == "checking":
            message = "检查回放的可用性。\nChecking for replay availability."
        else:
            message = f"未识别到的状态。\nUnidentified state: {state}."
    #在元数据准备就绪后，下载回放（When metadata is ready, download the replay）
    if state == "watch":
        replay_config: dict[str, Any] = await (await connection.request("GET", "/lol-replays/v1/configuration")).json()
        if replay_config["isPatching"]:
            message = "你目前正在变更版本。请等待版本变更完成后再观看你的回放。\nYou are currently patching. Please wait until patching is finished to watch your replay."
        elif replay_config["isInTournament"]:
            message = "在等待冠军杯赛的对局时，录像功能会处于禁用状态。\nReplays are disabled while waiting for a match in Clash."
        elif replay_config["isPlayingGame"]:
            message = "游戏仍在进行中。在进行游戏时，回放功能会处在禁用状态。\nA game is still in progress. Replays are disabled while playing a game."
        elif replay_config["isPlayingReplay"]:
            message = "你目前正在观看回放。同一时间只能观看一场录像。\nYou are currently watching a replay. Only one replay can be watched at a time."
        else:
            contextData: dict[str, str] = {"componentType": "replay-button_match-history"}
            response: Optional[dict[str, Any]] = await (await connection.request("POST", f"/lol-replays/v1/rofls/{matchId}/watch", data = contextData)).json()
            message = "已发送观看回放的请求。\nRequest to watch the replay has been sent."
            replay_config: dict[str, Any] = await (await connection.request("GET", "/lol-replays/v1/configuration")).json()
            if replay_config["isPlayingReplay"]:
                message = "回放正在播放中。\nThe replay is now playing."
            else:
                message = "回放启动失败。\nThe replay failed to start."
    return message
