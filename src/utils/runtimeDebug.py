from lcu_driver.connection import Connection
import copy, json, os, pickle, requests, sys, traceback
from typing import Any, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd)
from src.utils.logger import LogManager
from src.utils.webRequest import SGPSession

def subscope(scope: Optional[dict[Any, Any]] = None, clone: bool = True, log: Optional[LogManager] = None, verbose: bool = True) -> int:
    '''
    在程序运行期间开启一个私密的作用域，允许用户自行调试和计算结果。运行效果类似于带有部分运行时变量的一个新的Python终端。<br>Open a private scope to allow users debug and make calculations during the program execution. The experience is like a new Python terminal with some runtime variables inherited.
    
    为了观察表达式的计算结果，建议用户用“print”函数将表达式包裹起来。<br>To inspect the calculation result, it's highly suggested that users enclose the expression with a "print" function.
    
    :param scope: 作用域，存储需要从运行环境中继承的变量。<br>A scope that stores variables to be inherited from the runtime environment.
    
        在用于执行计算时，作用域会经历一次深度拷贝，以避免影响到原运行环境中的变量。<br>To perform calculations, the scope is deep copied, in case the original variables in runtime would be influenced.
    :type scope: dict[Any, Any]
    :param clone: 是否创建作用域的深度拷贝。默认为真。<br>Whether to create a deep copy of the scope. True by default.
    
        深度拷贝通过`copy.deepcopy`函数实现。在有变量无法通过此函数实现深度拷贝时，则应将此参数置为假。<br>Deep copy is implemented by `copy.deepcopy` function. When there are variables that cannot be deep copied by this function, this parameter should be set as False.
    :type clone: bool
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    :param verbose: 日志管理对象的`logPrint`方法的参数之一，表示是否开启终端输出。如果值为真，则在终端输出提示，否则只输出到日志中。默认为真。<br>One of parameters of `logPrint` method of a LogManager object, which means whether to enable terminal output. If the value is True, hints will be printed into terminal, otherwise they'll only be output to log. True by default.
    :type verbose: bool
    :return: 状态码。在正常退出函数的情况下，总是返回0。<br>Status code. When this function is exited as normal, 0 is always returned.
    :rtype: int
    '''
    if scope == None:
        scope = {}
    if log == None:
        log = LogManager()
    logInput = log.logInput
    logPrint = log.logPrint
    s: dict[Any, Any] = copy.deepcopy(scope) if clone else scope
    while True:
        expr: str = logInput()
        # tokens: list[str] = expr.split() #去除空格的词法分析（Parse by spliting by space）
        if expr == "-1":
            break
        elif expr == "0":
            if clone:
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
    '''
    使用LCU API发送指令，并将响应主体保存到临时文件中。<br>Send commands through LCU API, and save the response body into a temporary file.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    '''
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
    '''
    使用SGP API发送指令，并将响应主体保存到临时文件中。<br>Send commands through SGP API, and save the response body into a temporary file.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    '''
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
            source: requests.Response = await session.request(connection, method, endpoint, headers = headers, params = params, data = json.dumps(body, ensure_ascii = False).encode("utf-8"))
        except TypeError:
            logPrint("请求主体格式错误！\nRequest body format error!")
        else:
            try:
                response: Any = source.json()
            except requests.exceptions.JSONDecodeError: #webrequest模块中已经输出过相应的信息了，这里不需要再输出一次（Corresponding information has been output in webrequest module, so here it doesn't need to be output once more）
                content: bytes = source.content
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
                logPrint(response)
                with open("temporary data.json", "w", encoding = "utf-8") as fp:
                    fp.write(json.dumps(response, indent = 4, ensure_ascii = False))
                with open("temporary data.pkl", "wb") as fp:
                    pickle.dump(response, fp)
        logPrint("请依次输入方法、统一资源标识符、参数、请求主体和请求头（如有），以空格为分隔符：\nPlease enter the method, URI, parameters, request body and request header (if needed), split by space:")

async def send_commands(connection: Connection, log: Optional[LogManager] = None) -> None:
    '''
    一个综合的调试LCU API和SGP API的函数。直接应用于调试脚本。<br>A universal function to debug LCU API and SGP API. Directly used in Customized Program 03.
    
    :param connection: 通过lcu-driver库创建的用于访问LCU API的连接对象。<br>A Connection object created through lcu-driver library, meant to access LCU API.
    :type connection: Connection
    :param log: 日志管理对象。如果未指定，则使用传统的输入和打印函数。<br>A LogManager object. If unspecified, traditional `input` and `print` functions will be used instead.
    :type log: LogManager
    '''
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
