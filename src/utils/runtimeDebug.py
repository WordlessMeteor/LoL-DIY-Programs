from lcu_driver.connection import Connection
import copy, json, os, pickle, requests, sys, traceback
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.logger import LogManager
from src.utils.webRequest import SGPSession

def subscope(scope: Optional[dict[Any, Any]] = None, log: Optional[LogManager] = None, verbose: bool = True):
    if scope == None:
        scope = {}
    if log == None:
        log = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    s: dict[Any, Any] = copy.deepcopy(scope)
    while True:
        expr: str = logInput()
        # tokens: list[str] = expr.split() #去除空格的词法分析（Parse by spliting by space）
        if expr == "-1":
            break
        elif expr == "0":
            s = copy.deepcopy(scope)
            logPrint("变量和作用域已复位。\nVariables and the scope have been reset.", verbose = verbose)
        else:
            try:
                exec(expr, s)
            except:
                traceback_info = traceback.format_exc()
                logPrint(traceback_info, verbose = verbose)
    return 0

#-----------------------------------------------------------------------------
# 向服务器发送指令（Send commands to the server）
#-----------------------------------------------------------------------------
async def send_LCU_commands(connection: Connection, log: Optional[LogManager] = None) -> None:
    if log == None:
        log = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    logPrint("请依次输入方法、统一资源标识符、参数和请求主体（如有），以空格为分隔符：\nPlease enter the method, URI, parameters and request body (if needed), split by space:") #输入“GET /help”或者访问https://swagger.dysolix.dev/lcu以查看所有接口（Submit "GET /help" or visit "https://swagger.dysolix.dev/lcu" to view all endpoints）
    while True:
        request: str = logInput()
        tmp: list[str] = request.split()
        if len(tmp) == 2:
            method, endpoint = tmp
            if endpoint[0] != "/":
                logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
                continue
            params = body = None
        elif len(tmp) == 3:
            method, endpoint = tmp[:2]
            if endpoint[0] != "/":
                logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
                continue
            params: Optional[dict[str, Any]] = None
            logPrint("请求主体（Request body）：")
            while True:
                body_str: str = logInput()
                if body_str == "":
                    body_str = "None"
                try:
                    body = eval(body_str)
                except:
                    logPrint("请求主体格式错误！请重新输入请求主体。\nRequest body format error! Please input the request body again.")
                else:
                    break
        elif len(tmp) == 4:
            method, endpoint = tmp[:2]
            if endpoint[0] != "/":
                logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
                continue
            logPrint("参数（Params）：")
            while True:
                params_str: str = logInput()
                if params_str == "":
                    params_str = "None"
                try:
                    params = eval(params_str)
                except:
                    logPrint("参数格式错误！请重新输入参数。\nRequest body format error! Please input the parameters again.")
                else:
                    break
            logPrint("请求主体（Request body）：")
            while True:
                body_str = logInput()
                if body_str == "":
                    body_str = "None"
                try:
                    body = eval(body_str)
                except:
                    logPrint("请求主体格式错误！请重新输入请求主体。\nRequest body format error! Please input the request body again.")
                else:
                    break
        else:
            break
        try:
            response: Any = await (await connection.request(method, endpoint, params = params, data = body)).json()
        except TypeError:
            logPrint("请求主体格式错误！\nRequest body format error!")
        else:
            logPrint(response)
            with open("temporary data.json", "w", encoding = "utf-8") as fp:
                fp.write(json.dumps(response, indent = 4, ensure_ascii = False))
            with open("temporary data.pkl", "wb") as fp:
                pickle.dump(response, fp)
        logPrint("请依次输入方法、统一资源标识符、参数和请求主体（如有），以空格为分隔符：\nPlease enter the method, URI, parameters and request body (if needed), split by space:")

async def send_SGP_commands(connection: Connection, log: Optional[LogManager] = None) -> None:
    if log == None:
        log = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    session: SGPSession = SGPSession()
    await session.init(connection)
    logPrint("请依次输入方法、统一资源标识符、参数、请求主体和请求头（如有），以空格为分隔符：\nPlease enter the method, URI, parameters, request body and request header (if needed), split by space:")
    while True:
        request: str = logInput()
        tmp: list[str] = request.split()
        if len(tmp) == 2:
            method, endpoint = tmp
            if endpoint[0] != "/":
                logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
                continue
            params = body = headers = None
        elif len(tmp) == 3:
            method, endpoint = tmp[:2]
            if endpoint[0] != "/":
                logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
                continue
            params = headers = None
            logPrint("请求主体（Request body）：")
            while True:
                body_str: str = logInput()
                if body_str == "":
                    body_str = "None"
                try:
                    body = eval(body_str)
                except:
                    logPrint("请求主体格式错误！请重新输入请求主体。\nRequest body format error! Please input the request body again.")
                else:
                    break
        elif len(tmp) == 4:
            method, endpoint = tmp[:2]
            if endpoint[0] != "/":
                logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
                continue
            headers: Optional[dict[str, str]] = None
            logPrint("参数（Params）：")
            while True:
                params_str: str = logInput()
                if params_str == "":
                    params_str = "None"
                try:
                    params = eval(params_str)
                except:
                    logPrint("参数格式错误！请重新输入参数。\nRequest body format error! Please input the parameters again.")
                else:
                    break
            logPrint("请求主体（Request body）：")
            while True:
                body_str = logInput()
                if body_str == "":
                    body_str = "None"
                try:
                    body = eval(body_str)
                except:
                    logPrint("请求主体格式错误！请重新输入请求主体。\nRequest body format error! Please input the request body again.")
                else:
                    break
        elif len(tmp) == 5:
            method, endpoint = tmp[:2]
            if endpoint[0] != "/":
                logPrint("统一资源标识符必须以斜杠开头！\nThe URL must start with a slash!")
                continue
            logPrint("参数（Params）：")
            while True:
                params_str = logInput()
                if params_str == "":
                    params_str = "None"
                try:
                    params = eval(params_str)
                except:
                    logPrint("参数格式错误！请重新输入参数。\nRequest body format error! Please input the parameters again.")
                else:
                    break
            logPrint("请求主体（Request body）：")
            while True:
                body_str = logInput()
                if body_str == "":
                    body_str = "None"
                try:
                    body = eval(body_str)
                except:
                    logPrint("请求主体格式错误！请重新输入请求主体。\nRequest body format error! Please input the request body again.")
                else:
                    break
            logPrint("额外请求头（Extra request header）：")
            while True:
                header_str: str = logInput()
                if header_str == "":
                    header_str = "None"
                try:
                    headers = eval(header_str)
                except:
                    logPrint("请求头格式错误！请重新输入请求头。\nRequest header format error! Please input the request header again.")
                else:
                    if isinstance(headers, dict) and all(map(lambda x: isinstance(x, str), list(headers.keys()))) and all(map(lambda x: isinstance(x, str), list(headers.values()))):
                        break
                    else:
                        logPrint("请求头格式错误！请重新输入请求头。\nRequest header format error! Please input the request header again.")
        else:
            break
        try:
            response: requests.Response = await session.request(connection, method, endpoint, headers = headers, params = params, data = json.dumps(body, ensure_ascii = False).encode("utf-8"))
        except TypeError:
            logPrint("请求主体格式错误！\nRequest body format error!")
        else:
            try:
                response_body: Any = response.json()
            except requests.exceptions.JSONDecodeError: #webrequest模块中已经输出过相应的信息了，这里不需要再输出一次（Corresponding information has been output in webrequest module, so here it doesn't need to be output once more）
                content: bytes = response.content
                try:
                    text = content.decode()
                except UnicodeDecodeError: #/match-history-query/v3/product/lol/matchId/{match_id}/infoType/replay
                    with open("temporary data.bin", "wb") as fp:
                        fp.write(content)
                    logPrint('解析文本内容时出现了一个编码错误。内容已经以二进制方式进行存储。\nA UnicodeDecodeError occurred when the program was trying to resolve the text. The content has been saved into "temporary data.bin" in binary mode.')
                else:
                    logPrint(f"响应内容（Response content）：\n{text}")
                    with open("temporary data.json", "w") as fp:
                        fp.write(text)
            except AttributeError: #AttributeError: 'NoneType' object has no attribute 'json'
                logPrint("请求失败。\nRequest failed.")
            else:
                logPrint(response_body)
                with open("temporary data.json", "w", encoding = "utf-8") as fp:
                    fp.write(json.dumps(response_body, indent = 4, ensure_ascii = False))
                with open("temporary data.pkl", "wb") as fp:
                    pickle.dump(response_body, fp)
        logPrint("请依次输入方法、统一资源标识符、参数、请求主体和请求头（如有），以空格为分隔符：\nPlease enter the method, URI, parameters, request body and request header (if needed), split by space:")

async def send_commands(connection: Connection, log: Optional[LogManager] = None) -> None:
    if log == None:
        log = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    logPrint('请选择要调试的接口类型：（输入“0”以退出。）\nPlease select a type of API to debug: (Submit "0" to exit.)\n1\tLCU API\n2\tSGP API')
    while True:
        apiType: str = logInput()
        if apiType == "":
            continue
        elif apiType[0] == "0":
            break
        elif apiType[0] == "1":
            await send_LCU_commands(connection, log = log)
        elif apiType[0] == "2":
            await send_SGP_commands(connection, log = log)
        else:
            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.")
            continue
        logPrint('请选择要调试的接口类型：（输入“0”以退出程序）\nPlease select a type of API to debug: (Submit "0" to exit the program)\n1\tLCU API\n2\tSGP API')
