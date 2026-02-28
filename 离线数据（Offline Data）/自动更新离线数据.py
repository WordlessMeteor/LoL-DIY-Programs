import cssbeautifier, datetime, dateutil, jsbeautifier, json, os, pandas, re, requests, shutil, time, unicodedata, _io
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from wcwidth import wcswidth
from humanize import naturalsize
from cdtb.binfile import BinFile
from cdtb.rstfile import RstFile, get_hashfile, key_to_hash
from cdtb.export import AtlasInfoConverter
from typing import Any, IO

cwd: str = os.getcwd()
if cwd.endswith("离线数据（Offline Data）"): #允许用户直接双击脚本（Users are allowed to double click this program）
    os.chdir("..")
os.makedirs("离线数据（Offline Data）/Update Logs", exist_ok = True)
currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
log: IO[Any] = open(f"离线数据（Offline Data）/Update Logs/{currentTime}.log", "w", encoding = "utf-8")

def logInput(prompt: str = "", log: _io.TextIOWrapper = log, write_time: bool = True) -> str:
    s: str = input(prompt)
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
            log.write("[%s]%s\n" %(currentTime, prompt + s))
        else:
            log.write(prompt + s + "\n")
    return s

def logPrint(s: object = "", log: _io.TextIOWrapper = log, end: str = "\n", print_time: bool = False, write_time: bool = True) -> None:
    currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    if print_time:
        print("[%s]%s" %(currentTime, s), end = end, flush = end == "\r")
    else:
        print(s, end = end, flush = end == "\r")
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            log.write("[%s]%s%s" %(currentTime, str(s), "\n" if end == "\r" else end))
        else:
            log.write("%s%s" %(str(s), "\n" if end == "\r" else end))

def count_nonASCII(s: str) -> int: #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str) -> str: #移除一个字符串中的所有C0和C1字符（Remove all C0 and C1 characters from a string）
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc") #该表达式等价于（This expression is equivalent to）`re.sub(r"[\x00-\x1F\x7F-\x9F]", "", s)`

def format_df(df: pandas.DataFrame, width_exceed_ask: bool = True, direct_print: bool = False, print_header: bool = True, print_index: bool = False, reserve_index: bool = False, start_index: int = 0, header_align: str = "^", align: str = "^", align_replicate_rule: Literal["all", "last"] = "all") -> tuple[str, dict[str, int]]:
    df = df.copy(deep = True)
    old_index: pandas.Index = df.index
    df.index = pandas.Index(range(start_index, len(df) + start_index))
    maxLens: dict[str, int] = {}
    maxWidth: int = shutil.get_terminal_size()[0]
    fields: list[str] = df.columns.tolist()
    for field in fields:
        maxLens[field] = max(0 if len(df) == 0 else max(map(lambda x: wcswidth(rm_ctrl_char(str(x))), df[field])), wcswidth(rm_ctrl_char(field))) + 2
    index_len: int = 0 if len(df) == 0 else max(map(lambda x: len(str(x)), old_index)) if reserve_index else max(len(str(start_index)), len(str(start_index + len(df) - 1)))
    if sum(maxLens.values()) + 2 * (len(fields) - 1) > maxWidth or print_index and index_len + sum(maxLens.values()) + 2 * len(fields) > maxWidth:
        if width_exceed_ask:
            print("单行数据字符串输出宽度超过当前终端窗口宽度！是否继续？（输入任意键继续，否则直接打印该数据框。）\nThe output width of each record string exceeds the current width of the terminal window! Continue? (Input anything to continue, or null to directly print this dataframe.)")
            if not bool(input()):
                #print(df)
                result = str(df)
                return (result, maxLens)
        elif direct_print:
            print("单行数据字符串输出宽度超过当前终端窗口宽度！将直接打印该数据框！\nThe output width of each record string exceeds the current width of the terminal window! The program is going to directly print this dataframe!")
            result = str(df)
            return (result, maxLens)
        else:
            print("单行数据字符串输出宽度超过当前终端窗口宽度！将继续格式化输出！\nThe output width of each record string exceeds the current width of the terminal window! The program is going on formatted printing!")
    result: str = ""
    #确定各列的排列方向（Determine the alignments of all columns）
    if isinstance(header_align, str) and isinstance(align, str):
        if not all(map(lambda x: x in {"<", "^", ">"}, header_align)) or not all(map(lambda x: x in {"<", "^", ">"}, align)):
            print('排列方式字符串参数错误！排列方式必须是“<”“^”或者“>”中的一个。请修改排列方式字符串参数。\nParameter ERROR of the alignment string! The alignment value must be one of {"<", "^", ">"}. Please change the alignment string parameter.')
        if len(header_align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            header_alignments: list[str] = ["^"] * df.shape[1]
        elif len(header_align) == 1:
            header_alignments = [header_align] * df.shape[1]
        else:
            header_alignments_tmp = list(header_align)
            if len(header_align) < df.shape[1]:
                if align_replicate_rule == "last":
                    header_alignments = header_alignments_tmp + [header_alignments_tmp[-1]] * (df.shape[1] - len(header_align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    header_alignments = header_alignments_tmp * (df.shape[1] // len(header_align)) + header_alignments_tmp[:df.shape[1] % len(header_align)]
            else:
                header_alignments = header_alignments_tmp[:df.shape[1]]
        if len(align) == 0:
            alignments = ["^"] * df.shape[1]
        elif len(align) == 1:
            alignments = [align] * df.shape[1]
        else:
            alignments_tmp = list(align)
            if len(align) < df.shape[1]:
                if align_replicate_rule == "last":
                    alignments = alignments_tmp + [alignments_tmp[-1]] * (df.shape[1] - len(align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    alignments = alignments_tmp * (df.shape[1] // len(align)) + alignments_tmp[:df.shape[1] % len(align)]
            else:
                alignments = alignments_tmp[:df.shape[1]]
        if print_header:
            if print_index:
                result += " " * (index_len + 2)
            for i in range(df.shape[1]):
                field = fields[i]
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(field), align = header_alignments[i], w = maxLens[field] - count_nonASCII(field))
                result += tmp
                #print(tmp, end = "")
                if i != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            result += "\n"
            #print()
        index = start_index
        for i in range(df.shape[0]):
            if print_index:
                result += "{0:>{w}}".format(old_index[index - start_index] if reserve_index else index, w = index_len) + "  "
            for j in range(df.shape[1]):
                field = fields[j]
                cell = str(list(df[field])[i])
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(cell), align = alignments[j], w = maxLens[field] - count_nonASCII(cell))
                result += tmp
                #print(tmp, end = "")
                if j != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            if i != df.shape[0] - 1:
                result += "\n"
            #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the last line）
            index += 1
    else:
        print("排列方式参数错误！请传入字符串。\nAlignment parameter ERROR! Please pass a string instead.")
    return (result, maxLens)

def format_json(origin: str, indent_char: str = " ", number: int = 4) -> str: #对字符串origin进行格式化（Formalize the string `origin`）
    indent: str = indent_char * number
    bracket_level: int = 0 #bracket_level用来根据花括号的级别输出对应数量的水平制表符（`bracket_level` is used to input the corresponding number of horizontal tabs based on the hierachy of the curly brackets）
    result: str = ""
    escape: bool = False #标注是否对下一个字符应用转义（Marks whether the next character is escaped）
    for char in origin:
        if escape: #如果一个字符是被转义的，直接添加该字符，不作任何处理（If a character is escaped, add this character directly without any other operations）
            result += char
            escape = False #转义字符被添加后，关闭转义开关（After that escaped character is added, switch off `escape`）
        else:
            if char in "{[":
                bracket_level += 1
                result += char + "\n" + indent * bracket_level
            elif char in "]}":
                bracket_level -= 1
                result += "\n" + indent * bracket_level + char
            elif char == ":":
                result += ": "
            elif char == ",":
                result += ",\n" + indent * bracket_level
            elif char == "\\":
                result += "\\"
                escape = True
            else:
                result += char
    return result

def requestUrl(method: str, url: str, session: requests.sessions.Session | None = None, **kwargs: Any) -> tuple[requests.models.Response, int, requests.sessions.Session]:
    if session == None:
        session = requests.Session()
        # session.trust_env = False
    retry = 0
    while True:
        retry += 1
        try:
            source = session.request(method, url, **kwargs)
        except Exception as e:
            session = requests.Session()
            if retry > 5:
                source = requests.Response() #这只是为了保持代码类型检查的一致性（This is meant to keep consistency for code type checking）
                # session.trust_env = False
                source.status_code = -1
                break
            if isinstance(e, requests.exceptions.SSLError):
                if "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol" in str(e):
                    logPrint(f"违反协议导致读取中断！正在尝试第{retry}次重新获取数据！\nEOF occurred in violation of protocol! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
                elif "certificate verify failed" in str(e):
                    logPrint(f"SSL证书验证失败！正在尝试第{retry}次重新获取数据！\nSSL certificate verify failed! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
                elif "Max retries exceeded with url" in str(e):
                    logPrint(f"请求数量超过限制！正在尝试第{retry}次重新获取数据！\nMax retries exceed with url! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
            elif isinstance(e, requests.exceptions.ProxyError):
                logPrint(f"无法连接到代理！正在尝试第{retry}次重新获取数据！\nCannot connect to proxy! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
            elif isinstance(e, requests.exceptions.ChunkedEncodingError):
                logPrint(f"接收数据块长度不正确导致连接中断！正在尝试第{retry}次重新获取数据！\nConnection broken: InvalidChunkLength. Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
            elif isinstance(e, requests.exceptions.ConnectionError):
                if "Failed to establish a new connection: [Errno 11001] getaddrinfo failed" in str(e):
                    logPrint(f"无法获取网址信息，因此无法建立连接！正在尝试第{retry}次重新获取数据！\nCannot get address information, so connection can't be established! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
                else:
                    logPrint(f"由于远程服务器端无响应，连接已关闭！正在尝试第{retry}次重新获取数据！\nRemote end closed connection without response. Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
            elif isinstance(e, requests.exceptions.ReadTimeout):
                logPrint(f"读取超时！正在尝试第{retry}次重新获取数据！\nRead time out! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
            else:
                logPrint(e)
                logPrint(f"请求失败！正在尝试第{retry}次重新获取数据！\nRequest failed! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
        else:
            try:
                source.raise_for_status()
            except Exception as e:
                session = requests.Session()
                if retry > 5:
                    # session.trust_env = False
                    break
                logPrint(e)
                if isinstance(e, requests.exceptions.HTTPError):
                    if e.response.status_code in {403, 404}:
                        return (source, e.response.status_code, session)
                else:
                    logPrint(f"请求失败！正在尝试第{retry}次重新获取数据！\nRequest failed! Trying to recapture the data with url: {url}. Time(s) tried: {retry}", write_time = False)
            else:
                return (source, 200, session)
    return (source, source.status_code, session)

def CopyConvert(src: str, dst: str) -> None: #纯文本文件复制函数（Plain text file copy function）
    os.makedirs(os.path.dirname(dst), exist_ok = True)
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        shutil.copyfileobj(fsrc, fdst)

def BinConvert(src: str, dst: str) -> None: #二进制文件复制函数。dst参数应以“.json”结尾（Binary file copy function. `dst` should end with ".json"）
    os.makedirs(os.path.dirname(dst), exist_ok = True)
    with open(dst, "w", encoding = "utf-8") as fdst:
        binfile: BinFile = BinFile(src)
        binData: dict[str, Any] = binfile.to_serializable()
        if "__linked" in binData: #确保最后两个键一定是__linked和__patches（如有）【Make sure the last two keys must be __linked and __patches (if there they are)】
            tmp: Any = binData.pop("__linked")
            binData["__linked"] = tmp
        if "__patches" in binData:
            tmp: Any = binData.pop("__patches")
            binData["__patches"] = tmp
        json.dump(binfile.to_serializable(), fdst, indent = 4, ensure_ascii = False)

def RstConvert(src: str, dst: str, game_version: int = 1502) -> None: #字符串常量池复制函数。dst参数应以“.json”结尾（Stringtable copy function. `dst` should end with ".json"）
    rstfile: RstFile = RstFile(src)
    hashes = get_hashfile(game_version).load()
    hashes = {key_to_hash(hash, bits = rstfile.hash_bits): value for (hash, value) in hashes.items()}
    rst_json: dict[str, int | dict[str, str]] = {"entries": {}, "version": rstfile.version}
    for (key, value) in rstfile.entries.items():
        if key in hashes:
            key = hashes[key]
        else:
            key = f"{{{key:010x}}}"
        rst_json["entries"][key] = value
    os.makedirs(os.path.dirname(dst), exist_ok = True)
    with open(dst, "w", encoding = "utf-8") as fdst:
        json.dump(rst_json, fdst, indent = 4, ensure_ascii = False)

def AtlasInfoConvert(src: str, dst: str) -> None: #图册信息转换函数（Atlas info conversion function）
    with open(src, "rb") as fsrc, open(dst, "w", encoding = "utf-8") as fdst:
        json.dump(AtlasInfoConverter.parse_atlasinfo(fsrc), fdst, indent = 4, ensure_ascii = False)

TEXT_EXTENSIONS: tuple[str, ...] = (".json", ".txt", ".js", ".yaml", ".css", ".html")
#控制只输出一遍的提示（Control the hint to be displayed only once）
task_continue_hint: bool = True
ddragon_hint: bool = True
while True:
    logPrint("请选择一个数据库，输入空字符串以退出程序：\nPlease select a database, or submit an empty string to exit the program:\n1\tCommunityDragon\n2\tDataDragon", write_time = False)
    resource: str = logInput()
    if resource == "":
        log.write("[The program has exited!]\n")
        log.close()
        break
    elif resource[0] == "1":
        session: requests.Session = requests.Session() #初始化请求会话以便使用相同的认证信息（Initialize the request session so that the following requests can use the same authentification as much as possible）
        # session.trust_env = False #忽略系统代理设置（Bypass system proxy）
        step: int = 1
        option: str = ""
        mode: str = ""
        time_get_method: str = ""
        latest_mod_timestamp = 0
        latest_mod_date: str = ""
        while True:
            if step == 1:
                logPrint("请选择要更新的数据资源：\nPlease select the data resources to update:\n1\t所有文件（不可用）【All files (not available)】\n2\t所有正式服文件（不可用）【All latest files (not available)】\n3\t所有测试服文件（不可用）【All PBE files (not available)】\n☆4\t程序所需文件（默认）【Program requirement (by default)】\n5\t自行指定（Specify manually）", write_time = False)
                # logPrint("请选择要更新的数据资源：\nPlease select the data resources to update:\n☆1\t所有文件（默认）【All files (by default)】\n2\t所有正式服文件（All latest files）\n3\t所有测试服文件（All PBE files）\n4\t程序所需文件（不可用）【Program requirement (not available)】\n5\t自行指定（Specify manually）", write_time = False)
                option = logInput()
                if option != "" and option[0] == "0":
                    step -= 1
                    continue
                elif option != "" and option[0] == "5":
                    option = "5"
                else:
                    option = "4"
            elif step == 2:
                logPrint("请选择更新模式：\nPlease select the update mode:\n1\t全局扫描（Global Scan）\n☆2\t按修改时间更新（默认）【Updating According to Modification Time (by default)】", write_time = False)
                mode = logInput()
                if mode != "" and mode[0] == "0":
                    step -= 1
                    continue
                elif mode == "" or mode[0] != "1":
                    mode = "2"
                    logPrint("请选择一种方式指定修改时间：\nPlease select a method of specifying the modification time:\n☆1\t自动获取（默认）【Automatically get (by default)】\n2\t手动输入（Manually input）", write_time = False)
                    time_get_method: str = logInput()
                    if time_get_method != "" and time_get_method[0] == "0":
                        continue
                    elif time_get_method == "" or time_get_method[0] != "2":
                        time_get_method = "1"
                    else:
                        time_get_method = "2"
                        logPrint('请以“年-月-日 时-分-秒”的格式输入修改时间。示例：2024-05-04 10-26-21。\nPlease input a modification time in the format "%Y-%m-%d %H-%M-%S". Example: 2024-05-04 10-26-21.', write_time = False)
                        while True:
                            back: bool = False
                            latest_mod_timestamp_str: str = logInput()
                            if latest_mod_timestamp_str == "":
                                continue
                            elif latest_mod_timestamp_str[0] == "0":
                                back = True
                                break
                            else:
                                try: #允许输入整型或浮点型时间戳（A timestamp of integer or float type is allowed）
                                    latest_mod_timestamp = eval(latest_mod_timestamp_str)
                                    if isinstance(latest_mod_timestamp, (int, float)):
                                        break
                                except:
                                    try:
                                        date_obj = datetime.datetime.strptime(latest_mod_timestamp_str, "%Y-%m-%d %H-%M-%S")
                                    except ValueError:
                                        logPrint("您的输入格式有误！请重新输入。\nFormat not matched! Please try again.", write_time = False)
                                    else:
                                        latest_mod_timestamp = date_obj.timestamp()
                                        break
                        if back:
                            continue
                        latest_mod_date = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(latest_mod_timestamp))
                        logPrint("指定修改时间（Specified modification time）：%s" %(latest_mod_date), print_time = True)
                else:
                    mode = "1"
                    time_get_method, latest_mod_date = "0", "" #用于后面的文件列表提示动态字符串的初始化。删除后会引发变量未定义的错误（This variable is used for initialization of a subsequent dynamic file list hint string. Deleting it will cause an UnboundLocalError）
            elif step == 0 or step == 3:
                break
            else:
                logPrint("步骤异常！\nStep ERROR!", write_time = False)
            step += 1
        if step == 0:
            continue
        complete_scan: bool = False
        if option == "4":
            logPrint("正在获取目前CommunityDragon数据库支持的语言……\nTrying to get the currently supported locales in CommunityDragon database ...", print_time = True)
            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/json/latest/plugins/rcp-be-lol-game-data/global/", session)
            if status != 200:
                if status == -1:
                    logPrint('正式服语言信息获取失败！请检查系统网络状况和代理设置。程序即将退出。\nLocales in the "latest" folder capture failure! Please check the system network condition and agent configuration. The program will exit now.', write_time = False)
                elif status == 404:
                    logPrint('正式服语言信息获取失败！请检查以下链接的可用性。程序即将退出。\nLocales in the "latest" folder capture failure! Please check the URL availability. The program will exit now.\nhttps://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/', write_time = False)
                log.close()
                time.sleep(3)
                exit()
            web_folder: list[dict[str, Any]] = source.json()
            locales_latest: list[str] = []
            for record in web_folder:
                if record["type"] == "directory":
                    locales_latest.append(record["name"])
            source, status, session = requestUrl("GET", "https://raw.communitydragon.org/json/pbe/plugins/rcp-be-lol-game-data/global/", session)
            if status != 200:
                if status == -1:
                    logPrint('测试服语言信息获取失败！请检查系统网络状况和代理设置。程序即将退出。\nLocales in the "pbe" folder capture failure! Please check the system network condition and agent configuration. The program will exit now.', write_time = False)
                elif status == 404:
                    logPrint('测试服语言信息获取失败！请检查以下链接的可用性。程序即将退出。\nLocales in the "pbe" folder capture failure! Please check the URL availability. The program will exit now.\nhttps://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/', write_time = False)
                log.close()
                time.sleep(3)
                exit()
            web_folder = source.json()
            locales_pbe: list[str] = []
            for record in web_folder:
                if record["type"] == "directory":
                    locales_pbe.append(record["name"])
            cdragon_folders: list[str] = ["latest/cdragon/tft/"] + ["latest/plugins/rcp-be-lol-game-data/global/%s/v1/" %locale for locale in locales_latest] + ["latest/plugins/rcp-be-lol-game-data/global/%s/v1/champions/" %locale for locale in locales_latest] + ["pbe/cdragon/tft/"] + ["pbe/plugins/rcp-be-lol-game-data/global/%s/v1/" %locale for locale in locales_pbe] + ["pbe/plugins/rcp-be-lol-game-data/global/%s/v1/champions/" %locale for locale in locales_pbe] #由于urljoin函数的特性，所有文件夹类地址必须以斜杠结尾。下同（Due to the feature of `urljoin` function, all folder URLs must end with a slash. So do the following）
            cdragon_folders.sort()
        elif option == "5":
            logPrint("请选择指定文件夹的输入方式：\nPlease choose an input method to specify the folders:\n☆1\t逐行输入（推荐）【Line by line (recommended)】\n2\t来自文件（From file）\n3\t（试验）来自提取文件夹（Experimental: From extracted folder）", write_time = False) #推荐逐行输入，这样指定的文件夹能够记录到日志中（Line-by-line input is recommended, for the specified folders can be recorded into the log in this way）
            input_method: str = logInput()
            if input_method != "" and input_method[0] == "2":
                logPrint('请输入一个存放CommunityDragon数据库文件夹地址的文本文档的位置：\nPlease input the path of a text file that contains URLs of folders in CommunityDragon database:', write_time = False)
                while True:
                    txtfile: str = logInput()
                    if txtfile == "":
                        continue
                    elif os.path.exists(txtfile) and os.path.isfile(txtfile):
                        break
                    else:
                        logPrint("您输入的地址有误！请重新输入。\nERROR input of the text file path! Please try again.", write_time = False)
                with open(txtfile, "r", encoding = "utf-8") as fp:
                    cdragon_folders = list(set(map(lambda x: (x if x.endswith("/") else x[:-len(os.path.basename(x))]).strip("\n").replace("https://raw.communitydragon.org/", "").replace("离线数据（Offline Data）/cdragon/", ""), fp.readlines())))
                if "" in cdragon_folders:
                    cdragon_folders.remove("")
                cdragon_folders.sort()
            elif input_method != "" and input_method[0] == "3":
                bin_pattern = re.compile(r"game/.*\.bin$")
                rst_pattern = re.compile(r"game/(?:.*/)?data/menu/.*\.(txt|stringtable)$")
                atlasInfo_pattern = re.compile(r"game/clientstates/.*\.cdtb$|game/assets/items/icons2d/autoatlas/.*/atlas_info\.bin$")
                logPrint("请输入一个通过CDTB或者Obsidian等工具提取的客户端文件存放的文件夹路径：\nPlease input the path of a folder that contains the extracted client files using tools like CDTB or Obsidian:", write_time = False)
                while True:
                    folder_path: str = logInput()
                    if folder_path == "":
                        continue
                    elif os.path.exists(folder_path) and os.path.isdir(folder_path):
                        break
                    else:
                        logPrint("您输入的地址有误！请重新输入。\nERROR input of the folder path! Please try again.", write_time = False)
                logPrint("请输入目标文件夹的路径：\nPlease input the path of the target folder:")
                while True:
                    target_folder: str = logInput()
                    if target_folder == "":
                        continue
                    else:
                        os.makedirs(target_folder, exist_ok = True)
                        break
                logPrint('请输入版本号：\nPlease input the game version number:\n示例：要查询26.01版本的hash，请输入“1601”。\nExample: To use hashes in v26.01, input "1601".')
                while True:
                    game_version_str: str = logInput()
                    if game_version_str == "":
                        continue
                    else:
                        try:
                            game_version: int = int(game_version_str)
                        except ValueError:
                            logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.", write_time = False)
                        else:
                            break
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path: str = os.path.join(root, file).replace("\\", "\\")
                        relative_path: str = os.path.relpath(file_path, folder_path).replace("\\", "/")
                        dst_path: str = os.path.join(target_folder, relative_path).replace("\\", "/")
                        if bin_pattern.search(relative_path):
                            BinConvert(file_path, dst_path + ".json")
                        elif rst_pattern.search(relative_path):
                            RstConvert(file_path, dst_path + ".json", game_version)
                        elif atlasInfo_pattern.search(relative_path):
                            AtlasInfoConvert(file_path, dst_path + ".json")
                        elif file.endswith(TEXT_EXTENSIONS):
                            os.makedirs(os.path.dirname(dst_path), exist_ok = True)
                            CopyConvert(file_path, dst_path)
                        else:
                            continue
                        logPrint("已处理文件（Processed file）： %s" %(relative_path), print_time = True)
                continue
            elif input_method != "" and input_method[0] == "0":
                continue
            else:
                cdragon_folders = []
                logPrint("请逐个输入要更新的CommunityDragon文件夹的地址，输入-1以退出循环：\nPlease input the URLs of CommunityDragon folders to update one by one. Enter -1 to exit the loop:", write_time = False)
                while True:
                    cdragon_folder: str = logInput()
                    if cdragon_folder == "":
                        continue
                    elif cdragon_folder == "-1":
                        break
                    else:
                        cdragon_folder = cdragon_folder if cdragon_folder.endswith("/") else cdragon_folder[:-len(os.path.basename(cdragon_folder))]
                        cdragon_folders.append(cdragon_folder.replace("https://raw.communitydragon.org/", "").replace("离线数据（Offline Data）/cdragon/", "")) #请思考，这里如果换成`cdragon_folder.lstrip("https://raw.communitydragon.org/")`，会有什么效果？（Please figure out what will happen if the code is replaced by `cdragon_folder.lstrip("https://raw.communitydragon.org/")`）
                cdragon_folders = list(set(cdragon_folders))
                cdragon_folders.sort()
        else:
            text_folders_exported_latest: list[str] = []
            text_folders_exported_pbe: list[str] = []
            if option == "1" or option == "2":
                logPrint("正在读取正式服在线索引……\nReading the online index file of live data resources...", print_time = True)
                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/latest/cdragon/files.exported.txt", session)
                if status != 200:
                    if status == -1:
                        logPrint("获取索引失败！请检查系统网络状况和代理设置。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.", write_time = False)
                    elif status == 404:
                        logPrint("获取索引失败！请检查以下链接的可用性。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.\nhttps://raw.communitydragon.org/latest/cdragon/files.exported.txt", write_time = False)
                    log.close()
                    time.sleep(3)
                    exit()
                files_exported_latest: list[str] = source.text.strip("\n").split("\n")
                #files_exported_latest: list[str] = session.get("https://raw.communitydragon.org/latest/cdragon/files.exported.txt").text.strip("\n").split("\n")
                text_files_exported_latest: list[str] = [file for file in files_exported_latest if file.endswith(TEXT_EXTENSIONS)]
                text_folders_exported_latest: list[str] = list(set(list(map(lambda x: os.path.dirname(x) + "/" if "/" in x else "", text_files_exported_latest))))
                text_folders_exported_latest.sort()
            if option == "1" or option == "3":
                logPrint("正在读取美测服在线索引……\nReading the online index file of pbe data resources...", print_time = True)
                source, status, session = requestUrl("GET", "https://raw.communitydragon.org/pbe/cdragon/files.exported.txt", session)
                if status != 200:
                    if status == -1:
                        logPrint("获取索引失败！请检查系统网络状况和代理设置。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.", write_time = False)
                    elif status == 404:
                        logPrint("获取索引失败！请检查以下链接的可用性。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.\nhttps://raw.communitydragon.org/pbe/cdragon/files.exported.txt", write_time = False)
                    log.close()
                    time.sleep(3)
                    exit()
                files_exported_pbe: list[str] = source.text.strip("\n").split("\n")
                text_files_exported_pbe: list[str] = [file for file in files_exported_pbe if file.endswith(TEXT_EXTENSIONS)]
                text_folders_exported_pbe: list[str] = list(set(list(map(lambda x: os.path.dirname(x) + "/" if "/" in x else "", text_files_exported_pbe))))
                text_folders_exported_pbe.sort()
            if option in {"1", "2", "3"}:
                if option == "2":
                    cdragon_folders = ["latest/cdragon/", "latest/cdragon/arena/", "latest/cdragon/tft/"] + list(map(lambda x: "latest/" + x, text_folders_exported_latest))
                elif option == "3":
                    cdragon_folders = ["pbe/cdragon/", "pbe/cdragon/arena/", "pbe/cdragon/tft/"] + list(map(lambda x: "pbe/" + x, text_folders_exported_pbe))
                else:
                    cdragon_folders =  ["latest/cdragon/", "latest/cdragon/arena/", "latest/cdragon/tft/"] + list(map(lambda x: "latest/" + x, text_folders_exported_latest)) + ["pbe/cdragon/", "pbe/cdragon/arena/", "pbe/cdragon/tft/"] + list(map(lambda x: "pbe/" + x, text_folders_exported_pbe)) #索引文件中不包含“cdragon”文件夹内的文件，因此这里需要单独添加到文件夹列表中（The index file doesn't contain files in "cdragon" folder, so they should be added to the folder list specially）
                complete_scan = True
                if task_continue_hint:
                    logPrint("如果您之前有文件夹未检查，那么请在这里输入本次检查的文件夹的索引下界和上界。输入空字符串以检查所有文件夹。\nIf there're some folders unchecked before, please enter the lower and upper limit of the index of the folders to be checked this time. Submit an empty string to check all folders.\n提示：如果想要包含最后一个文件夹，请将上界指定为大于当前文件夹列表长度的任意一个正整数。\nHint: If you expect the program not to neglect the last folder, please specify the upper limit as any integer greater than the length of the current folder list.\n文件夹总个数（Total number of folders）：%d" %len(cdragon_folders), print_time = True)
                    task_continue_hint = False
                else:
                    logPrint("如果您之前有文件夹未检查，那么请在这里输入本次检查的文件夹的索引下界和上界。输入空字符串以检查所有文件夹。\nIf there're some folders unchecked before, please enter the lower and upper limit of the index of the folders to be checked this time. Submit an empty string to check all folders.\n文件夹总个数（Total number of folders）：%d" %len(cdragon_folders), print_time = True)
                while True:
                    back = False
                    contCheck: str = logInput()
                    if contCheck == "":
                        break
                    elif contCheck[0] == "0":
                        back = True
                        break
                    else:
                        try:
                            begin, end = map(int, contCheck.split())
                        except ValueError:
                            logPrint("请以空格为分隔符输入文件夹列表的整数类型的下界和上界！\nPlease enter two integers as the begIndex and endIndex of the folder list split by space!", write_time = False)
                        else:
                            cdragon_folders = cdragon_folders[begin:end]
                            complete_scan = False
                            break
                if back:
                    continue
            else:
                cdragon_folders = []
        web_prefix: str = "https://raw.communitydragon.org/"
        local_prefix: str = "离线数据（Offline Data）/cdragon"
        updated_files: list[str] = []
        added_files: list[str] = []
        error_folders: list[str] = []
        error_files: list[str] = []
        folders_to_delete: list[str] = [] #统计本地存在而数据库不存在的文件夹（Summarize the folders that exist locally but don't exist in the database）
        files_to_delete: list[str] = [] #统计本地存在而数据库不存在的文件（Summarize the files that exist locally but don't exist in the database）
        for root, dirs, files in os.walk(local_prefix): #要统计本地不存在的文件和文件夹，一定要先把本地有的文件和文件夹全部列出来，然后跟数据库比对，数据库上有的则逐个从待删除列表中移除（To summarize the files and folders that don't exist, the program should first list all the local files and folders, then compare them with the database and remove each file or folder that exists in the database）
            if option == "1" or option == "2" and "latest" in root or option == "3" and "pbe" in root:
                if not root in folders_to_delete and files != []: #请仔细体会后半个条件的作用（Please try to understand the role of the latter condition）
                    folders_to_delete.append(root.replace("\\", "/") + "/")
                if mode == "1": #当更新模式不是全局扫描时，待删除的文件列表不会追加任何文件（When the updating mode isn't [Global Scan], the list that holds the folders to delete won't be appended any files）
                    files_to_delete += list(map(lambda x: os.path.join(root, x).replace("\\", "/"), files))
        cnt1: int = 0
        for folder in cdragon_folders:
            cnt1 += 1
            cnt2: int = 0
            url: str = urljoin(web_prefix, folder) #在查验文件夹时，这个变量不再直接传入网址获取函数中了。它只作为输出提示（This variable is no longer passed to the `getUrl` function when checking the folder. It's only used for prompts now）
            jsonUrl: str = urljoin(urljoin(web_prefix, "json/"), folder) #在引入这个变量前，离线数据更新脚本是从网页源代码爬取得到文件更新日期信息的。感谢Morilli的指导，原来CommunityDragon本来就有一套接口来访问某个文件夹下的文件信息（Before this variable is introduced, Offline Data Updating Program crawls the file mTimes from the folder source code. Thanks to Morilli, I found that CommunityDragon provides an endpoint to get all file information under a folder）
            localdir: str = os.path.join(local_prefix, folder).replace("\\", "/")
            logPrint("[%d/%d]正在检查文件夹（Checking the folder）：%s" %(cnt1, len(cdragon_folders), url), print_time = True)
            table_content: dict[str, list[str | float]] = {"file": [], "size": [], "web_date": [], "web_timestamp": [], "local_date": [], "local_timestamp": []}
            source, status, session = requestUrl("GET", jsonUrl, session)
            if status != 200:
                if status == -1:
                    logPrint("文件夹%s信息获取失败！请等待程序结束后手动比对。\nFolder %s information check failed! Please check manually after the program execution finishes." %(url, url), write_time = False)
                    error_folders.append(url)
                    if localdir in folders_to_delete: #比对失败的文件夹不应删除（Folders that fail to be checked shouldn't be deleted）
                        folders_to_delete.remove(localdir)
                elif status == 404:
                    logPrint("文件夹%s不存在！\nFolder %s not found!" %(url, url), write_time = False)
                else:
                    if localdir in folders_to_delete:
                        folders_to_delete.remove(localdir)
                continue
            if localdir in folders_to_delete:
                folders_to_delete.remove(localdir)
            web_folder = source.json()
            optionStr: dict[str, dict[str, str]] = {"1": {"zh_CN": "页面", "en_US": ""}, "2": {"zh_CN": "页面", "en_US": ""}, "3": {"zh_CN": "页面", "en_US": ""}, "4": {"zh_CN": "本程序集涉及的", "en_US": " involved in this program set"}, "5": {"zh_CN": "指定文件夹涉及的", "en_US": " in specified folders"}}
            modeStr: dict[str, dict[str, str]] = {"1": {"zh_CN": "", "en_US": "File list"}, "2": {"zh_CN": "差异" if time_get_method == "1" else "指定修改时间（%s）后的" %(latest_mod_date), "en_US": "Difference file list" if time_get_method == "1" else "File list after the specified modification time (%s)" %(latest_mod_date)}}
            logPrint("%s%s文件列表如下：\n%s%s is as follows: " %(optionStr[option]["zh_CN"], modeStr[mode]["zh_CN"], modeStr[mode]["en_US"], optionStr[option]["en_US"]), print_time = True)
            logPrint("网页链接（URL)： %s" %url, write_time = False)
            for record in web_folder:
                if record["type"] == "file":
                    name: str = record["name"]
                    if name.endswith(TEXT_EXTENSIONS):
                        size: str = naturalsize(record["size"], binary = True)
                        web_date: str = record["mtime"]
                        web_date_obj = dateutil.parser.parse(web_date)
                        web_timestamp: float = web_date_obj.timestamp()
                        web_date: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(web_timestamp))
                        local_timestamp: float = os.path.getmtime(os.path.join(localdir, name)) if os.path.exists(localdir) and name in os.listdir(localdir) else 0
                        local_date: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(local_timestamp))
                        #if (option in {"1", "2", "3"} or option == "4" and (folder.endswith("cdragon/tft/") or folder.endswith("v1/") and name in ["champion-summary.json", "cherry-augments.json", "companions.json", "items.json", "perks.json", "perkstyles.json", "queues.json", "summoner-icons.json", "summoner-spells.json", "tftchampions.json", "tftitems.json", "tfttraits.json"] or folder.endswith("v1/champions/")) or option == "5") and (mode == "1" or mode == "2" and web_timestamp >= (local_timestamp if time_get_method == "1" else latest_mod_timestamp)):
                        if (option in {"1", "2", "3"} or (option == "4" or option == "5") and (folder.endswith("cdragon/tft/") or folder.endswith("v1/") and name in ["champion-summary.json", "cherry-augments.json", "companions.json", "items.json", "perks.json", "perkstyles.json", "queues.json", "summoner-icons.json", "summoner-spells.json", "tftchampions.json", "tftitems.json", "tfttraits.json"] or folder.endswith("v1/champions/"))) and (mode == "1" or mode == "2" and web_timestamp >= (local_timestamp if time_get_method == "1" else latest_mod_timestamp)): #仅供发行版使用（Only for release）
                            table_content["file"].append(name)
                            table_content["size"].append(size)
                            table_content["web_date"].append(web_date)
                            table_content["web_timestamp"].append(web_timestamp)
                            table_content["local_date"].append(local_date)
                            table_content["local_timestamp"].append(local_timestamp)
            numFile_to_check: int = len(table_content["file"])
            web_folder_fileset: set[str] = set(map(lambda x: x["name"], web_folder))
            local_folder_filelist: list[str] = os.listdir(localdir) if os.path.exists(localdir) else []
            for name in local_folder_filelist:
                if name.endswith(TEXT_EXTENSIONS):
                    if mode != "1" and option != "4" and not name in web_folder_fileset: #这里额外添加一下被删除的文件的信息。因为全局扫描模式下有另外一套赋值模式，所以这里不包含（Here we extraly add those deleted files. Because Glocal Scan has another assignment pattern, it's not included here）
                        local_timestamp: float = os.path.getmtime(os.path.join(localdir, name)) if os.path.exists(localdir) and name in os.listdir(localdir) else 0
                        local_date: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(local_timestamp))
                        table_content["file"].append(name)
                        table_content["size"].append("")
                        table_content["web_date"].append(0)
                        table_content["web_timestamp"].append("")
                        table_content["local_date"].append(local_date)
                        table_content["local_timestamp"].append(local_timestamp)
                        files_to_delete.append(os.path.join(localdir, name).replace("\\", "/")) #与全局扫描不同，这里是直接从空列表开始逐个追加本地路径（What's different from Global Scan is local path is successively appended to the list of files to delete）
            table: pandas.DataFrame = pandas.DataFrame(table_content)
            if table.empty:
                logPrint(table, write_time = False)
            else:
                print(format_df(table, width_exceed_ask = False, direct_print = True)[0])
                log.write(format_df(table, width_exceed_ask = False, direct_print = False)[0] + "\n")
            os.makedirs(localdir, exist_ok = True)
            for i in range(numFile_to_check): #这里并不直接使用range(len(table))，是因为被删除的文件没必要比对（Here `range(len(table))` isn't used, because there's no need check deleted files）
                cnt2 += 1
                name = table["file"][i]
                file_path: str = os.path.join(localdir, name).replace("\\", "/")
                logPrint("[%d/%d][%d/%d]正在校对文件（Checking file）： %s" %(cnt1, len(cdragon_folders), cnt2, numFile_to_check, urljoin(url, name)), print_time = True)
                update: bool = False
                added: bool = False
                response, status, session = requestUrl("GET", urljoin(url, name), session)
                if status != 200:
                    if status == -1:
                        logPrint("文件%s比对失败！请等待程序结束后手动比对。\nFile %s check failed! Please check manually after the program execution finishes." %(urljoin(url, name), urljoin(url, name)), write_time = False)
                        error_files.append(urljoin(url, name))
                        if file_path in files_to_delete: #比对失败的文件不应删除（Files that fail to be checked shouldn't be deleted）
                            files_to_delete.remove(file_path)
                    elif status == 404:
                        logPrint("文件%s不存在！\nFile %s not found!" %(urljoin(url, name), urljoin(url, name)), write_time = False)
                    continue
                if file_path in files_to_delete:
                    files_to_delete.remove(file_path)
                if name.endswith(".json"):
                    try:
                        src_json: Any = response.json()
                    except json.decoder.JSONDecodeError as e:
                        if "Unexpected UTF-8 BOM (decode using utf-8-sig)" in str(e): #解决方案来自Stack Overflow（The solution comes from https://stackoverflow.com/questions/71025396/asyncio-and-get-unexpected-utf-8-bom）
                            logPrint("文件编码格式错误！正在尝试改用utf-8-sig编码……\nFile decode error! Trying decoding by utf-8-sig ...", write_time = False)
                            src_json = json.loads(response.text.encode().decode("utf-8-sig"))
                            src: str = json.dumps(src_json, indent = 4, ensure_ascii = False)
                        else:
                            logPrint("文件内容解析失败！请等待程序结束后手动比对。\nFile content parsing failure! Please check manually after the program execution finishes.", write_time = False)
                            error_files.append(urljoin(url, name))
                            continue
                    else:
                        src: str = json.dumps(src_json, indent = 4, ensure_ascii = False)
                elif name.endswith(".js"):
                    src = jsbeautifier.beautify(response.text)
                elif name.endswith(".css"):
                    src = cssbeautifier.beautify(response.text)
                elif name.endswith(".html"):
                    soup = BeautifulSoup(response.text, "html.parser")
                    src = soup.prettify()
                else:
                    src = response.text.replace("\r", "")
                if not name in os.listdir(localdir):
                    update = added = True
                else:
                    with open(os.path.join(localdir, name), "r", encoding = "utf-8") as fp:
                        dst: str = fp.read()
                    if src != dst:
                        update = True
                if mode == "1" and update or mode == "2": #当选择全局扫描时，只更新有变化的文档；当选择根据修改时间更新时，如果网页修改时间超前，那么无论文件内容是否发生变化，都重新保存一次，便于后续按照修改时间更新（When the user selects Global Scan, the program updates the changed files. When the user selects Updating according to modification time, if the web modification time of a file succeeds to the local midification time of that, then save the web content to local, no matter whether the web file is same as the local file in terms of content）
                    with open(os.path.join(localdir, name), "w", encoding = "utf-8") as fp:
                        fp.write(src)
                if update:
                    if added:
                        logPrint("已添加文件（Added file）：%s" %(os.path.join(localdir, name)), print_time = True)
                        added_files.append(urljoin(url, name))
                    else:
                        logPrint("已更新文件（Updated file）：%s" %(os.path.join(localdir, name)), print_time = True)
                        updated_files.append(urljoin(url, name))
        if updated_files:
            logPrint("已更新以下%d个文件：\nUpdated the following %d file(s):" %(len(updated_files), len(updated_files)), write_time = False)
            for file in updated_files:
                logPrint(file, write_time = False)
            logPrint("", write_time = False)
        if added_files:
            logPrint("已添加以下%d个文件：\nAdded the following %d file(s):" %(len(added_files), len(added_files)), write_time = False)
            for file in added_files:
                logPrint(file, write_time = False)
            logPrint("", write_time = False)
        if error_folders:
            logPrint("以下%d个文件夹比对失败。请重新比对！\nThe following %d folder(s) fail to be checked. Please check manually!" %(len(error_folders), len(error_folders)), write_time = False)
            for folder in error_folders:
                logPrint(folder, write_time = False)
            logPrint("", write_time = False)
        if error_files:
            logPrint("以下%d个文件比对失败。请重新比对！\nThe following %d file(s) fail to be checked. Please check manually!" %(len(error_files), len(error_files)), write_time = False)
            for file in error_files:
                logPrint(file, write_time = False)
            logPrint("", write_time = False)
        if option in {"1", "2", "3"} and complete_scan and len(files_to_delete) > 0:
            logPrint("以下%d个文件不存在于数据库中。是否永久删除这些文件？（输入任意非空字符串删除，否则不删除）\nThe following %d file(s) don't exist in the database. Do you want to delete them? (Submit any non-empty string to delete, or null to refuse deleting the files)\n" %(len(files_to_delete), len(files_to_delete)) + "\n".join(files_to_delete), write_time = False)
            delete_str: str = logInput()
            delete: bool = bool(delete_str)
            if delete:
                for file in files_to_delete:
                    try:
                        os.remove(file)
                    except FileNotFoundError:
                        pass
            logPrint("", write_time = False)
        if option in {"1", "2", "3"} and complete_scan and len(folders_to_delete) > 0:
            logPrint("以下%d个文件夹不存在于数据库中。是否永久删除这些文件夹？（输入任意非空字符串删除，否则不删除）\nThe following %d folder(s) don't exist in the database. Do you want to delete them? (Submit any non-empty string to delete, or null to refuse deleting the folders)\n" %(len(folders_to_delete), len(folders_to_delete)) + "\n".join(folders_to_delete), write_time = False)
            delete_str = logInput()
            delete = bool(delete_str)
            if delete:
                for folder in folders_to_delete:
                    try:
                        shutil.rmtree(folder)
                    except FileNotFoundError:
                        pass
            logPrint("", write_time = False)
    elif resource[0] == "2":
        step: int = 1
        mode: str = ""
        src_folder: str = ""
        dst_folder: str = "离线数据（Offline Data）/ddragon"
        while True:
            if step == 1:
                logPrint("请选择更新模式：\nPlease select the update mode:\n1\t全局比对（Global Compare）\n☆2\t按程序需求更新（默认）【Updating According to Program Demands (by default)】", write_time = False)
                mode = logInput()
                if mode != "" and mode[0] == "1":
                    mode = "1"
                elif mode != "" and mode[0] == "0":
                    step -= 1
                    continue
                else:
                    mode = "2"
            elif step == 2:
                if ddragon_hint:
                    hint: str = '请按以下步骤操作：\nPlease follow these steps:\n1. 访问网址https://developer.riotgames.com/docs/lol#data-dragon\n   Visit the website: https://developer.riotgames.com/docs/lol#data-dragon\n2. 在Latest中找到正式服最新版本数据资源压缩包下载链接。例如：https://ddragon.leagueoflegends.com/cdn/dragontail-16.4.1.tgz\n   Find the link to download the compressed tarball of the latest data resource for live servers. For example: https://ddragon.leagueoflegends.com/cdn/dragontail-16.4.1.tgz\n3. 下载。这需要花费一些时间。\n   Download the file. It may take some time.\n4. 将下载好的tgz文件直接“解压至此”。\n   "Extract here" for the tgz file.\n5. 将解压出来的压缩包再次解压到选定文件夹下与压缩包同名的文件夹。示例：将“dragontail-16.4.1.tar”解压到“D:/360AI浏览器下载/dragontail-16.4.1”文件夹下。\nExtract to "Archive-Name" folder under the selected folder for the extracted tar file. For example, extract "dragontail-16.4.1.tar" into the folder "D:/Downloads/dragontail-16.4.1".\n接下来，请给出数据资源的位置。（按照上例应为“D:/360AI浏览器下载/dragontail-16.4.1/16.4.1/data”。）\nNext, please provide the directory that stores the data resources. (By the above example, the directory should be "D:/Downloads/dragontail-16.4.1/16.4.1/data".)'
                    logPrint(hint, write_time = False)
                    ddragon_hint = False
                else:
                    logPrint("请给出数据资源的位置。\nPlease provide the directory that stores the data resources.", write_time = False)
                while True:
                    back: bool = False
                    src_folder = logInput()
                    if src_folder == "":
                        continue
                    elif src_folder == "0":
                        step -= 1
                        back = True
                        break
                    elif os.path.exists(src_folder):
                        if not ("en_US" in os.listdir(src_folder) and "zh_CN" in os.listdir(src_folder)):
                            logPrint("您输入的路径有误！请重新输入！\nERROR input of data resource directory! Please try again!", write_time = False)
                        else:
                            break
                    else:
                        logPrint("您输入的路径不存在！请重新输入！\nPath not found! Please try again!", write_time = False)
                if back:
                    continue
            elif step == 0 or step == 3:
                break
            else:
                logPrint("步骤异常！\nStep ERROR!", write_time = False)
            step += 1
        if step == 0:
            continue
        added_files: list[str] = []
        updated_files: list[str] = []
        error_files: list[str] = []
        cnt1: int = 0
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                update: bool = False
                added: bool = False
                if mode == "1" and file.endswith(".json") or mode == "2" and file == "championFull.json":
                    src_path: str = os.path.join(root, file).replace("\\", "/")
                    relative_path: str = os.path.relpath(root, src_folder).replace("\\", "/")
                    dst_path: str = os.path.join(dst_folder, relative_path, file).replace("\\", "/")
                    if "en_US" in relative_path or "zh_CN" in relative_path:
                        cnt1 += 1
                        os.makedirs(os.path.dirname(dst_path), exist_ok = True)
                        logPrint("[%d]正在校对文件（Checking file）： %s" %(cnt1, src_path), print_time = True)
                        try:
                            with open(src_path, "r", encoding = "utf-8") as fp:
                                src_json: Any = json.load(fp)
                                src: str = json.dumps(src_json, indent = 4, ensure_ascii = False)
                        except json.decoder.JSONDecodeError: #在15.24.1版本，DataDragon的tft-unlockable.json出现格式错误（A format error exists in tft-unlockable.json of 15.24.1）
                            with open(src_path, "r", encoding = "utf-8") as fp:
                                src = format_json(fp.read())
                        if not file in os.listdir(os.path.join(dst_folder, relative_path)):
                            update = added = True
                        else:
                            with open(dst_path, "r", encoding = "utf-8") as fp:
                                dst: str = fp.read()
                            if src != dst:
                                update = True
                        if update:
                            with open(dst_path, "w", encoding = "utf-8") as fp:
                                fp.write(src)
                            if added:
                                logPrint("[%d]已添加文件（Added file）：%s" %(cnt1, dst_path), print_time = True)
                                added_files.append(src_path)
                            else:
                                logPrint("[%d]已更新文件（Updated file）：%s" %(cnt1, dst_path), print_time = True)
                                updated_files.append(src_path)
        if mode == "1":
            for root, dirs, files in os.walk(dst_folder): #在全局扫描模式下，删除新版本中不存在的文件（Delete the files that don't exist in the new version under Global Scan mode）
                for file in files:
                    if file.endswith(".json"):
                        dst_path: str = os.path.join(root, file).replace("\\", "/")
                        relative_path: str = os.path.relpath(root, dst_folder).replace("\\", "/")
                        src_path: str = os.path.join(src_folder, relative_path, file).replace("\\", "/")
                        if not os.path.exists(src_path):
                            cnt1 += 1
                            logPrint("[%d]正在删除文件（Deleting file）： %s" %(cnt1, dst_path), print_time = True)
                            try:
                                os.remove(dst_path)
                            except FileNotFoundError:
                                pass
        cnt1 += 1
        version_url: str = "https://ddragon.leagueoflegends.com/api/versions.json"
        logPrint("[%d]正在校对文件（Checking file）： %s" %(cnt1, version_url), print_time = True)
        update = added = False
        response, status, session = requestUrl("GET", version_url)
        if status != 200:
            if status == -1:
                logPrint("文件%s比对失败！请等待程序结束后手动比对。\nFile %s check failed! Please check manually after the program execution finishes." %(version_url, version_url), write_time = False)
            elif status == 404:
                logPrint("文件%s不存在！请等待程序结束后手动比对。\nFile %s not found! Please check manually after the program execution finishes." %(version_url, version_url), write_time = False)
            error_files.append(version_url)
            continue
        src_json: Any = response.json()
        src: str = json.dumps(src_json, indent = 4, ensure_ascii = False)
        if not "versions.json" in os.listdir("离线数据（Offline Data）"):
            update = added = True
        else:
            with open("离线数据（Offline Data）/versions.json", "r", encoding = "utf-8") as fp:
                dst: str = fp.read()
            if src != dst:
                update = True
        if update:
            with open("离线数据（Offline Data）/versions.json", "w", encoding = "utf-8") as fp:
                fp.write(src)
            if added:
                logPrint("[%d]已添加文件（Added file）：离线数据（Offline Data）/versions.json" %cnt1, print_time = True)
                added_files.append("离线数据（Offline Data）/versions.json")
            else:
                logPrint("[%d]已更新文件（Updated file）：离线数据（Offline Data）/versions.json" %cnt1, print_time = True)
                updated_files.append("离线数据（Offline Data）/versions.json")
    else:
        logPrint("您的输入有误！请重新输入。\nERROR input! Please try again.", write_time = False)
print("比对完成！请按回车键退出。\nCheck finished! Press Enter to exit.")
input()
