from lcu_driver.connection import Connection
import json, os, requests, sys
from typing import Any
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.utils.webRequest import SGPSession

async def download_replay(connection: Connection, sgpSession: SGPSession, match_id: str, rofl_path: str, product: str = "LoL") -> tuple[bool, str]:
    '''
    下载当前大区的英雄联盟回放。<br>Download League of Legends replays in current server.

    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param sgpSession: SGP会话。<br>SGP Session.
    :type sgpSession: SGPSession
    :param match_id: 大区对局序号。由服务器代号和对局序号通过下划线连接而成。<br>Platform matchId, concatenated from a platformId and a matchId.
    :type match_id: str
    :param rofl_path: 回放路径。<br>Replay path.
    :type rofl_path: str
    :param product: 游戏产品名。有以下取值：<br>Game product name, which has the following values:
    
        - LoL: 英雄联盟（League of Legends）（☆）
        - TFT: 云顶之弈（Teamfight Tactics）

        云顶之弈对局无法下载回放，所以一般选择英雄联盟。<br>A TFT match doesn't support downloading the match, so this parameter is always "LoL".
    :type product: Literal["LoL, "TFT"]
    :return: 一个二元组。<br>A 2-tuple.

        第一个元素是回放是否成功下载。当下载回放的请求返回二进制数据时，视为回放成功下载。<br>The first element is whether the replay is successfully downloaded. When the request to download the replay returns binary data, the function considers the replay has been successfully downloaded.

        第二个元素是消息字符串。<br>The second element is a message string.
    :rtype: tuple[bool, str]
    '''
    #参数预处理（Parameter preprocessing）
    if product != "TFT":
        product = "LoL"
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
    return (replay_downloaded, message)
