from lcu_driver.connection import Connection
import os, re, requests, sys
from typing import Any, Optional
from urllib.parse import urljoin
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.logger import LogManager

def requestUrl(method: str, url: str, retry: int = 5, session: Optional[requests.Session] = None, log: Optional[LogManager] = None, verbose: bool = True, **kwargs: Any) -> tuple[requests.models.Response, int, requests.Session]:
    '''
    一个综合的网络请求函数，包含以下特性：<br>A universal web request function integrated with the following features:
    - 异常处理。<br>Error handling.
    - 重复请求。<br>Repeat on error.
    
    :param method: 请求方法。全大写。<br>Request method. Whole word in upper case.
    :type method: str
    :param url: 请求链接。<br>Request url.
    :type url: str
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :param kwargs: 任何可传入`session.request`函数中的参数。<br>Any parameters that can be passed into `session.request` function.
    :type kwargs: Any
    :return: 响应主体、状态码和网络请求会话组成的三元组。<br>A three-tuple composed of the response body, http status code and web request session.
    :rtype: tuple[requests.models.Response, int, requests.Session]
    '''
    if session == None:
        session = requests.Session()
        # session.trust_env = False
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    verify: bool = True #是否验证证书（Whether to verify the certificate）
    count: int = 0
    while True:
        count += 1
        try:
            source: requests.Response = session.request(method, url, verify = verify, **kwargs)
        except Exception as e:
            session = requests.Session()
            if count > retry:
                source = requests.Response() #这只是为了保持代码类型检查的一致性（This is meant to keep consistency for code type checking）
                source.status_code = -1
                # session.trust_env = False
                break
            if isinstance(e, requests.exceptions.SSLError):
                if "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol" in str(e):
                    logPrint(f"违反协议导致读取中断！正在尝试第{count}次重新获取数据！\nEOF occurred in violation of protocol! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
                elif "certificate verify failed" in str(e):
                    verify = False
                    logPrint(f"SSL证书验证失败！正在尝试第{count}次重新获取数据！\nSSL certificate verify failed! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
                elif "Max retries exceeded with url" in str(e):
                    logPrint(f"请求数量超过限制！正在尝试第{count}次重新获取数据！\nMax retries exceed with url! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
            elif isinstance(e, requests.exceptions.ProxyError):
                logPrint(f"无法连接到代理！正在尝试第{count}次重新获取数据！\nCannot connect to proxy! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
            elif isinstance(e, requests.exceptions.ChunkedEncodingError):
                logPrint(f"接收数据块长度不正确导致连接中断！正在尝试第{count}次重新获取数据！\nConnection broken: InvalidChunkLength. Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
            elif isinstance(e, requests.exceptions.ConnectionError):
                if "Failed to establish a new connection: [Errno 11001] getaddrinfo failed" in str(e):
                    logPrint(f"无法获取网址信息，因此无法建立连接！正在尝试第{count}次重新获取数据！\nCannot get address information, so connection can't be established! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
                else:
                    logPrint(f"由于远程服务器端无响应，连接已关闭！正在尝试第{count}次重新获取数据！\nRemote end closed connection without response. Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
            elif isinstance(e, requests.exceptions.ReadTimeout):
                logPrint(f"读取超时！正在尝试第{count}次重新获取数据！\nRead time out! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
            else:
                logPrint(e, verbose = verbose)
                logPrint(f"请求失败！正在尝试第{count}次重新获取数据！\nRequest failed! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
        else:
            try:
                response: Any = source.json() #检验响应内容是否可转换为json（Verify whether the response content can be transformed into json）
            except:
                try:
                    source.raise_for_status()
                except Exception as e:
                    session = requests.Session()
                    # session.trust_env = False
                    if count > retry:
                        break
                    logPrint(e, verbose = verbose)
                    if isinstance(e, requests.exceptions.HTTPError):
                        if e.response.status_code in {403, 404}: #DataDragon数据库的数据不存在的状态码是403（The Http status for files not found in DataDragon database is 403）
                            return (source, e.response.status_code, session)
                    else:
                        logPrint(f"请求失败！正在尝试第{count}次重新获取数据！\nRequest failed! Trying to recapture the data with url: {url}. Time(s) tried: {count}", write_time = False, verbose = verbose)
                else:
                    return (source, source.status_code, session)
            else:
                return (source, 200, session)
    return (source, source.status_code, session)

class SGPSession:
    def __init__(self, token: Optional[str] = None, client_settings: Optional[dict[str, Any]] = None, log: Optional[LogManager] = None, verbose: bool = True) -> None:
        '''
        SGP会话类的构造函数。<br>The constructor of `SGPSession` class.
        
        :param token: 英雄联盟会话令牌。可先不指定，后续通过`init`方法来指定。<br>League session token. It may be left unspecified when creating an object of this class, waiting to be specified using the `init` method.
        
            英雄联盟会话令牌可以通过以下LCU接口获取：<br>Leauge session token can be obtained through the following LCU endpoint:
            - `GET /lol-league-session/v1/league-session-token`
        :type token: str
        :param client_settings: 客户端设置数据。可先不指定，后续通过`init`方法来指定。<br>Client settings data. It may be left unspecified when creating an object of this class, waiting to be specified using the `init` method.
        
            客户端设置可以通过以下LCU接口获取：<br>Client settings can be obtained through the following LCU endpoint:
            - `GET /client-config/v2/namespace/lol.client_settings`
        :type client_settings: dict[str, Any]
        :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
        :type log: LogManager
        :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
        :type verbose: bool
        '''
        self.userInfoToken: str = "" if token == None else token
        self._headers: dict[str, str] = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}
        self.session: requests.Session = requests.Session()
        # self.session.trust_env = False #忽略系统代理设置（Bypass system proxy）
        self.log: LogManager = log or LogManager()
        self.verbose: bool = verbose
        if isinstance(client_settings, dict) and "lol.client_settings.league_edge.url" in client_settings:
            self.client_settings: dict[str, Any] = client_settings
    
    def __repr__(self) -> str:
        return (f'SGPSession("{self.userInfoToken}")')
    
    def setLog(self, log: LogManager) -> None:
        '''
        设置日志文件流。<br>Set the log file iostream.
        
        :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
        :type log: LogManager
        '''
        self.log = log
    
    async def update_userInfo_token(self, connection: Connection) -> None:
        '''
        更新联盟会话令牌。<br>Update the league session token.
        
        :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
        :type connection: Connection
        '''
        token: str = await (await connection.request("GET", "/lol-league-session/v1/league-session-token")).json()
        if isinstance(token, str):
            self.userInfoToken = token
            self._headers["Authorization"] = f"Bearer {token}"
        else:
            self.log.logPrint(token, verbose = self.verbose)
            if token["httpStatus"] == 404 and token["message"] == "NOT_FOUND":
                self.log.logPrint("未找到用户信息令牌。请检查您的登录状态。\nUser info token not found. Please check your login status.")
            else:
                self.log.logPrint("令牌更新失败！\nToken update failed!", verbose = self.verbose)
    
    async def init(self, connection: Connection) -> None:
        '''
        初始化SGP会话对象的联盟会话令牌和客户端设置。<br>Initialize an `SGPSession` object's league session token and client settings.
        
        :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
        :type connection: Connection
        '''
        await self.update_userInfo_token(connection)
        self.client_settings = await (await connection.request("GET", "/client-config/v2/namespace/lol.client_settings")).json()
        self.session = requests.Session()
        # self.session.headers.update({"X-Riot-Spectator-Key": "YOUR_SPECTATOR_KEY_HERE"})
        # self.session.trust_env = False #忽略系统代理设置（Bypass system proxy）
    
    async def request(self, connection: Connection, method: str, endpoint: str, headers: Optional[dict[str, str]] = None, retry: int = 5, verbose: bool = True, **kwargs: Any) -> requests.models.Response: #参考了lcu_driver的代码（Referred to code in `lcu_driver`）
        '''
        通过SGP API发送一个网络请求。<br>Send a web request through SGP API.
        
        :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
        :type connection: Connection
        :param method: 请求方法。全大写。<br>Request method. Whole word in upper case.
        :type method: str
        :param endpoint: 终端节点路径。<br>An endpoint path.
        
            在SGP API的请求网址中，每个网址的开头是一段因服务器而异的域名，后面的路径则在各服务器上都相同。当用户只传入路径时，函数将自适应地从客户端设置中找到域名。<br>In the url of an SGP request, the header is a domain name that depends on the server, while the subsequent path remains the same across all servers. When the user only provides the path, this function will adaptively determine the domain name from the client settings.
        :type endpoint: str
        :param headers: 额外的请求头。<br>Extra request headers.
        
            函数默认使用以下请求头：<br>This function uses the following header by default:
            - `{"Authorization": "Bearer {token}", "Content-type": "application/json"}`
            
            用户可以另外指定其它的字段。函数会将其与默认请求头进行合并。<br>The user may specify other fields in the header. This function will join them with the default header.
        :type headers: dict[str, str]
        :param retry: 最大尝试次数。默认为5次。<br>Maximum number of attempts. 5 by default.
        :type retry: int
        :param verbose: 控制网络请求的异常提示是否在终端输出。默认为真。<br>Controls whether the error information of the web request is printed to terminal. True by default.
        :type verbose: bool
        :param kwargs: 任何可传入`session.request`函数中的参数。<br>Any parameters that can be passed into `session.request` function.
        :type kwargs: Any
        :return: 原始响应信息。<br>Raw response.
        :rtype: requests.model.Response
        '''
        #参数预处理（Parameter preparation）
        if not hasattr(self, "client_settings"):
            self.client_settings = await (await connection.request("GET", "/client-config/v2/namespace/lol.client_settings")).json()
        if "errorCode" in self.client_settings and self.client_settings["httpStatus"] == 400 and re.search(r"Proxy: GetConfigAsync '/client-config/v2/namespace/lol.client_settings': Error response for GET /client-config/v2/namespace/lol.client_settings: Operation timed out after \d+ milliseconds with 0 out of 0 bytes received", self.client_settings["message"]):
            self.log.logPrint(self.client_settings, verbose = self.verbose)
            raise TimeoutError("Client configuration fetch timeout! Please restart the League Client.")
        if endpoint.startswith("https://"):
            url: str = endpoint
        elif endpoint.startswith(("/login-queue", "/session-external", "/services", "/match-history-query")):
            url = urljoin(self.client_settings.get("lol.client_settings.account_verification_edge.url", self.client_settings["lol.client_settings.league_edge.url"]), endpoint)
        else:
            url = urljoin(self.client_settings["lol.client_settings.league_edge.url"], endpoint)
        if headers == None:
            headers = {}
        source, status, self.session = requestUrl(method, url, retry = retry, session = self.session, headers = self._headers | headers, log = self.log, verbose = verbose, **kwargs)
        try:
            response: dict[str, Any] = source.json()
        except requests.exceptions.JSONDecodeError:
            self.log.logPrint("在转换为json对象时发生了错误。\nAn error occurred when converting the response body into a json object.", verbose = self.verbose)
        except AttributeError: #AttributeError: 'NoneType' object has no attribute 'json'
            pass
        else:
            if response == {"httpStatus": 400, "message": "A newer more recent session has been processed for this player", "errorCode": "INVALID_PLAYER_SESSION"} or response == {"status": {"message": "Unauthorized", "status_code": 401}}:
                self.log.logPrint("令牌已过期。正在更新令牌……\nToken has expired. Updating the token ...", verbose = self.verbose)
                await self.update_userInfo_token(connection)
                source = self.session.request(method = method, url = url, headers = self._headers | headers, **kwargs)
        return source

def sgpConnect(method: str, url: str, token: str, extra_headers: Optional[dict[str, str]] = None, session: Optional[requests.Session] = None, **kwargs: Any) -> tuple[dict[str, Any], requests.Session]: #一个单独用来调试SGP API的函数（A function specially designed to debug SGP API）
    '''
    一个用来调用SGP API的相对较为独立的函数。<br>A relatively standalone function to call SGP API.
    
    :param method: 请求方法。全大写。<br>Request method. Whole word in upper case.
    :type method: str
    :param url: 请求链接。<br>Request url.
    :type url: str
    :param token: 英雄联盟会话令牌。可先不指定，后续通过`init`方法来指定。<br>League session token. It may be left unspecified when creating an object of this class, waiting to be specified using the `init` method.
        
        英雄联盟会话令牌可以通过以下LCU接口获取：<br>Leauge session token can be obtained through the following LCU endpoint:
        - `GET /lol-league-session/v1/league-session-token`
    :type token: str
    :param extra_headers: 额外的请求头。<br>Extra request headers.
        
        函数默认使用以下请求头：<br>This function uses the following header by default:
        - `{"Authorization": "Bearer {token}", "Content-type": "application/json"}`
        
        用户可以另外指定其它的字段。函数会将其与默认请求头进行合并。<br>The user may specify other fields in the header. This function will join them with the default header.
    :type extra_headers: dict[str, str]
    :param session: 网络请求会话。<br>Web request session.
    :type session: requests.Session
    :param kwargs: 任何可传入`session.request`函数中的参数。<br>Any parameters that can be passed into `session.request` function.
    :type kwargs: Any
    :return: 响应结构体和网络请求会话。<br>Response struct and web request session.
    
        响应结构体由以下三部分组成：<br>The response struct is composed of the following three elements:
        - status_code: 状态码。<br>Status code.
        - json: 响应主体。<br>Response body.
        - error: 异常对象的字符串表达。<br>The string representation of any error arising.
    :rtype: tuple[dict[str, Any], requests.Session]
    '''
    if session == None:
        session = requests.Session()
        # session.trust_env = False #忽略系统代理设置（Bypass system proxy）
    if extra_headers == None:
        extra_headers = {}
    result: dict[str, Any] = {"status_code": 0, "json": None, "error": None}
    headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}
    try:
        source = session.request(method, url, headers = headers | extra_headers, **kwargs)
    except requests.exceptions.SSLError as ssl_error:
        result["status_code"] = -1
        result["error"] = str(ssl_error)
    else:
        result["status_code"] = source.status_code
        result["json"] = source.json()
    return (result, session)
