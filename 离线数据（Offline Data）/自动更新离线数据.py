import json, os, re, requests, shutil, time, unicodedata, _io
import pandas as pd
from urllib.parse import urljoin
from datetime import datetime
from bs4 import BeautifulSoup
from wcwidth import wcswidth

os.makedirs("离线数据（Offline Data）/Update Logs", exist_ok = True)
currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
log = open(f"离线数据（Offline Data）/Update Logs/{currentTime}.log", "w", encoding = "utf-8")

def count_nonASCII(s: str): #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str): #移除一个字符串中的所有C0和C1字符（Remove all C0 and C1 characters from a string）
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc")

def logInput(prompt: str = "", log: _io.TextIOWrapper = log, write_time: bool = True):
    s = input(prompt)
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
            log.write("[%s]%s\n" %(currentTime, prompt + s))
        else:
            log.write(prompt + s + "\n")
    return s

def logPrint(s: str = "", log: _io.TextIOWrapper = log, end: str = "\n", print_time: bool = False, write_time: bool = True):
    currentTime = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
    if print_time:
        print("[%s]%s" %(currentTime, s), end = end)
    else:
        print(s, end = end)
    if isinstance(log, _io.TextIOWrapper):
        if write_time:
            log.write("[%s]%s%s" %(currentTime, str(s), end))
        else:
            log.write("%s%s" %(str(s), end))

def format_df(df: pd.DataFrame, width_exceed_ask: bool = True, direct_print: bool = False, print_header: bool = True, print_index: bool = False, reserve_index = False, start_index = 0, header_align: str = "^", align: str = "^", align_replicate_rule: str = "all"): #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
    df = df.copy(deep = True)
    old_index = df.index
    df.index = range(start_index, len(df) + start_index)
    maxLens = {}
    maxWidth = shutil.get_terminal_size()[0]
    fields = df.columns.tolist()
    for field in fields:
        maxLens[field] = max(0 if len(df) == 0 else max(map(lambda x: wcswidth(rm_ctrl_char(str(x))), df[field])), wcswidth(rm_ctrl_char(field))) + 2
    index_len = 0 if len(df) == 0 else max(map(lambda x: len(str(x)), old_index)) if reserve_index else max(len(str(start_index)), len(str(start_index + len(df) - 1)))
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
        # else:
        #     print("单行数据字符串输出宽度超过当前终端窗口宽度！将继续格式化输出！\nThe output width of each record string exceeds the current width of the terminal window! The program is going on formatted printing!")
    result = ""
    #确定各列的排列方向（Determine the alignments of all columns）
    if isinstance(header_align, str) and isinstance(align, str):
        if not all(map(lambda x: x in {"<", "^", ">"}, header_align)) or not all(map(lambda x: x in {"<", "^", ">"}, align)):
            print('排列方式字符串参数错误！排列方式必须是“<”“^”或者“>”中的一个。请修改排列方式字符串参数。\nParameter ERROR of the alignment string! The alignment value must be one of {"<", "^", ">"}. Please change the alignment string parameter.')
        if len(header_align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            header_alignments = ["^"] * df.shape[1]
        elif len(header_align) == 1:
            header_alignments = [header_align] * df.shape[1]
        else:
            header_alignments_tmp = list(header_align)
            if len(header_align) < df.shape[1]:
                if align_replicate_rule == "last":
                    header_alignments = header_alignments_tmp + [header_alignments_tmp[-1]] * len(df.shape[1] - len(header_align))
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
                    alignments = alignments_tmp + [alignments_tmp[-1]] * len(df.shape[1] - len(align))
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

def getUrl(url: str):
    retry = 0
    while True:
        try:
            retry += 1
            source = requests.get(url)
            source.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            if retry > 5:
                break
            if http_err.response.status_code in {403, 404}:
                return (source, http_err.response.status_code)
        except requests.exceptions.SSLError as ssl_error:
            if retry > 5:
                break
            if "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol" in str(ssl_error):
                logPrint("违反协议导致读取中断！正在尝试第%d次重新获取数据！\nEOF occurred in violation of protocol! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry), write_time = False)
            elif 'certificate verify failed' in str(ssl_error):
                logPrint("SSL证书验证失败！正在尝试第%d次重新获取数据！\nSSL certificate verify failed! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry), write_time = False)
            elif 'Max retries exceeded with url' in str(ssl_error):
                logPrint("请求数量超过限制！正在尝试第%d次重新获取数据！\nMax retries exceed with url! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry), write_time = False)
        except requests.exceptions.ProxyError:
            if retry > 5:
                break
            logPrint("无法连接到代理！正在尝试第%d次重新获取数据！\nCannot connect to proxy! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry), write_time = False)
        except requests.exceptions.ChunkedEncodingError:
            if retry > 5:
                break
            logPrint("接收数据块长度不正确导致连接中断！正在尝试第%d次重新获取数据！\nConnection broken: InvalidChunkLength. Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry), write_time = False)
        except requests.exceptions.ConnectionError:
            if retry > 5:
                break
            logPrint("由于远程服务器端无响应，连接已关闭！正在尝试第%d次重新获取数据！\nRemote end closed connection without response. Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry), write_time = False)
        except requests.exceptions.ReadTimeout:
            if retry > 5:
                break
            logPrint("读取超时！正在尝试第%d次重新获取数据！\nRead time out! Trying to recapture the data with url: %s. Time(s) tried: %d" %(retry, url, retry), write_time = False)
        else:
            return (source, 0)
    if retry > 5:
        return (None, 1)

#控制只输出一遍的提示（Control the hint to be displayed only once）
task_continue_hint = True
ddragon_hint = True
line_re = re.compile('<tr><td class="link"><a href=".*" title=".*">.*</a></td><td class="size">.*</td><td class="date">.*</td></tr>')
while True:
    logPrint("请选择要更新的数据资源，输入空字符串以退出程序：\nPlease select the data resource to update, or submit an empty string to exit the program:\n1\tCommunityDragon\n2\tDataDragon", write_time = False)
    resource = logInput()
    if resource == "":
        log.write("[The program has exited!]\n")
        log.close()
        break
    elif resource[0] == "1":
        logPrint("请选择要更新的数据资源：\nPlease select the data resources to update:\n1\t所有文件（不可用）【All files (not available)】\n2\t所有正式服文件（不可用）【All latest files (not available)】\n3\t所有测试服文件（不可用）【All PBE files (not available)】\n☆4\t程序所需文件（默认）【Program requirement (by default)】\n5\t自行指定（Specify manually）", write_time = False)
        option = logInput()
        if option != "" and option[0] == "5":
            option = "5"
        else:
            option = "4"
        logPrint("请选择更新模式：\nPlease select the update mode:\n1\t全局扫描（Global Scan）\n☆2\t按修改时间更新（默认）【Updating According to Modification Time (by default)】", write_time = False)
        mode = logInput()
        if mode == "" or mode[0] != "1":
            mode = "2"
            logPrint("请选择一种方式指定修改时间：\nPlease select a method of specifying the modification time:\n☆1\t自动获取（默认）【Automatically get (by default)】\n2\t手动输入（Manually input）", write_time = False)
            time_get_method = logInput()
            if time_get_method == "" or time_get_method[0] != "2":
                time_get_method = "1"
            else:
                time_get_method = "2"
                logPrint('请以“年-月-日 时-分-秒”的格式输入修改时间。示例：2024-05-04 10-26-21。\nPlease input a modification time in the format "%Y-%m-%d %H-%M-%S". Example: 2024-05-04 10-26-21.', write_time = False)
                while True:
                    latest_mod_timestamp = logInput()
                    if latest_mod_timestamp == "":
                        continue
                    try: #允许输入整型或浮点型时间戳（A timestamp of integer or float type is allowed）
                        latest_mod_timestamp = eval(latest_mod_timestamp)
                        if isinstance(latest_mod_timestamp, (int, float)):
                            break
                    except:
                        try:
                            date_obj = datetime.strptime(latest_mod_timestamp, "%Y-%m-%d %H-%M-%S")
                        except ValueError:
                            logPrint("您的输入格式有误！请重新输入。\nFormat not matched! Please try again.", write_time = False)
                        else:
                            latest_mod_timestamp = date_obj.timestamp()
                            break
                latest_mod_date = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(latest_mod_timestamp))
                logPrint("指定修改时间（Specified modification time）：%s" %(latest_mod_date), print_time = True)
        else:
            mode = "1"
            time_get_method, latest_mod_date = 0, "" #用于后面的文件列表提示动态字符串的初始化。删除后会引发变量未定义的错误（This variable is used for initialization of a subsequent dynamic file list hint string. Deleting it will cause an UnboundLocalError）
        if option == "4":
            logPrint("正在获取目前CommunityDragon数据库支持的语言……\nTrying to get the currently supported locales in CommunityDragon database ...", print_time = True)
            source, status = getUrl("https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/")
            if status != 0:
                if status == 1:
                    logPrint('正式服语言信息获取失败！请检查系统网络状况和代理设置。程序即将退出。\nLocales in the "latest" folder capture failure! Please check the system network condition and agent configuration. The program will exit now.', write_time = False)
                elif status == 404:
                    logPrint('正式服语言信息获取失败！请检查以下链接的可用性。程序即将退出。\nLocales in the "latest" folder capture failure! Please check the URL availability. The program will exit now.\nhttps://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/', write_time = False)
                log.close()
                time.sleep(3)
                exit()
            source = source.content.decode()
            source_list = list(map(lambda x: x.strip(), source.split("\n")))
            locales_latest = []
            for line in source_list:
                matchedLine = line_re.search(line)
                if matchedLine:
                    soup = BeautifulSoup(line, 'lxml')
                    name = soup.find("a")["href"]
                    locales_latest.append(name)
            source, status = getUrl("https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/")
            if status != 0:
                if status == 1:
                    logPrint('测试服语言信息获取失败！请检查系统网络状况和代理设置。程序即将退出。\nLocales in the "pbe" folder capture failure! Please check the system network condition and agent configuration. The program will exit now.', write_time = False)
                elif status == 404:
                    logPrint('测试服语言信息获取失败！请检查以下链接的可用性。程序即将退出。\nLocales in the "pbe" folder capture failure! Please check the URL availability. The program will exit now.\nhttps://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/', write_time = False)
                log.close()
                time.sleep(3)
                exit()
            source = source.content.decode()
            source_list = list(map(lambda x: x.strip(), source.split("\n")))
            locales_pbe = []
            for line in source_list:
                matchedLine = line_re.search(line)
                if matchedLine:
                    soup = BeautifulSoup(line, 'lxml')
                    name = soup.find("a")["href"]
                    locales_pbe.append(name)
            cdragon_folders = ["latest/cdragon/tft/"] + ["latest/plugins/rcp-be-lol-game-data/global/%sv1/" %locale for locale in locales_latest] + ["latest/plugins/rcp-be-lol-game-data/global/%sv1/champions/" %locale for locale in locales_latest] + ["pbe/cdragon/tft/"] + ["pbe/plugins/rcp-be-lol-game-data/global/%sv1/" %locale for locale in locales_pbe] + ["pbe/plugins/rcp-be-lol-game-data/global/%sv1/champions/" %locale for locale in locales_pbe] #由于urljoin函数的特性，所有文件夹类地址必须以斜杠结尾。下同（Due to the feature of `urljoin` function, all folder URLs must end with a slash. So do the following）
            cdragon_folders.sort()
        elif option == "5":
            logPrint("请选择指定文件夹的输入方式：\nPlease choose an input method to specify the folders:\n☆1\t逐行输入（推荐）【Line by line (recommended)】\n2\t来自文件（From file）", write_time = False) #推荐逐行输入，这样指定的文件夹能够记录到日志中（Line-by-line input is recommended, for the specified folders can be recorded into the log in this way）
            input_method = logInput()
            if input_method != "" and input_method[0] == "2":
                logPrint('请输入一个存放CommunityDragon数据库文件夹地址的文本文档的位置：\nPlease input the path of a text file that contains URLs of folders in CommunityDragon database:', write_time = False)
                while True:
                    txtfile = logInput()
                    if txtfile == "":
                        continue
                    elif os.path.exists(txtfile):
                        break
                    else:
                        logPrint("您输入的地址有误！请重新输入。\nERROR input of the text file path! Please try again.", write_time = False)
                with open(txtfile, "r", encoding = "utf-8") as fp:
                    cdragon_folders = list(set(map(lambda x: (x if x.endswith("/") else x[:-len(os.path.basename(x))]).strip("\n").replace("https://raw.communitydragon.org/", "").replace("离线数据（Offline Data）/cdragon/", ""), fp.readlines())))
                if "" in cdragon_folders:
                    cdragon_folders.remove("")
                cdragon_folders.sort()
            else:
                cdragon_folders = []
                logPrint("请逐个输入要更新的CommunityDragon文件夹的地址，输入-1以退出循环：\nPlease input the URLs of CommunityDragon folders to update one by one. Enter -1 to exit the loop:", write_time = False)
                while True:
                    cdragon_folder = logInput()
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
            if option == "1" or option == "2":
                logPrint("正在读取正式服在线索引……\nReading the online index file of live data resources...", print_time = True)
                source, status = getUrl("https://raw.communitydragon.org/latest/cdragon/files.exported.txt")
                if status != 0:
                    if status == 1:
                        logPrint("获取索引失败！请检查系统网络状况和代理设置。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.", write_time = False)
                    elif status == 404:
                        logPrint("获取索引失败！请检查以下链接的可用性。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.\nhttps://raw.communitydragon.org/latest/cdragon/files.exported.txt", write_time = False)
                    log.close()
                    time.sleep(3)
                    exit()
                files_exported_latest = source.text.strip("\n").split("\n")
                #files_exported_latest = requests.get("https://raw.communitydragon.org/latest/cdragon/files.exported.txt").text.strip("\n").split("\n")
                text_files_exported_latest = [file for file in files_exported_latest if file.endswith((".json", ".txt", ".js", ".yaml"))]
                text_folders_exported_latest = list(set(list(map(lambda x: "/".join(x.split("/")[:-1]) + "/" if "/" in x else "", text_files_exported_latest))))
                text_folders_exported_latest.sort()
            if option == "1" or option == "3":
                logPrint("正在读取美测服在线索引……\nReading the online index file of pbe data resources...", print_time = True)
                source, status = getUrl("https://raw.communitydragon.org/pbe/cdragon/files.exported.txt")
                if status != 0:
                    if status == 1:
                        logPrint("获取索引失败！请检查系统网络状况和代理设置。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.", write_time = False)
                    elif status == 404:
                        logPrint("获取索引失败！请检查以下链接的可用性。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.\nhttps://raw.communitydragon.org/pbe/cdragon/files.exported.txt", write_time = False)
                    log.close()
                    time.sleep(3)
                    exit()
                files_exported_pbe = source.text.strip("\n").split("\n")
                #files_exported_pbe = requests.get("https://raw.communitydragon.org/pbe/cdragon/files.exported.txt").text.strip("\n").split("\n")
                text_files_exported_pbe = [file for file in files_exported_pbe if file.endswith((".json", ".txt", ".js", ".yaml"))]
                text_folders_exported_pbe = list(set(list(map(lambda x: "/".join(x.split("/")[:-1]) + "/" if "/" in x else "", text_files_exported_pbe))))
                text_folders_exported_pbe.sort()
            if option in {"1", "2", "3"}:
                if option == "2":
                    cdragon_folders = ["latest/cdragon/arena/", "latest/cdragon/tft/"] + list(map(lambda x: "latest/" + x, text_folders_exported_latest))
                elif option == "3":
                    cdragon_folders = ["pbe/cdragon/arena/", "pbe/cdragon/tft/"] + list(map(lambda x: "pbe/" + x, text_folders_exported_pbe))
                else:
                    cdragon_folders =  ["latest/cdragon/arena/", "latest/cdragon/tft/"] + list(map(lambda x: "latest/" + x, text_folders_exported_latest)) + ["pbe/cdragon/arena/", "pbe/cdragon/tft/"] + list(map(lambda x: "pbe/" + x, text_folders_exported_pbe)) #索引文件中不包含cdragon文件夹内的文件，因此这里需要单独添加到文件夹列表中（The index file doesn't contain files in cdragon folder, so they should be added to the folder list specially）
                complete_scan = True
                if task_continue_hint:
                    logPrint("如果您之前有文件夹未检查，那么请在这里输入本次检查的文件夹的索引下界和上界。输入空字符串以检查所有文件夹。\nIf there're some folders unchecked before, please enter the lower and upper limit of the index of the folders to be checked this time. Submit an empty string to check all folders.\n提示：如果想要包含最后一个文件夹，请将上界指定为大于当前文件夹列表长度的任意一个正整数。\nHint: If you expect the program not to neglect the last folder, please specify the upper limit as any integer greater than the length of the current folder list.\n文件夹总个数（Total number of folders）：%d" %len(cdragon_folders), print_time = True)
                    task_continue_hint = False
                else:
                    logPrint("如果您之前有文件夹未检查，那么请在这里输入本次检查的文件夹的索引下界和上界。输入空字符串以检查所有文件夹。\nIf there're some folders unchecked before, please enter the lower and upper limit of the index of the folders to be checked this time. Submit an empty string to check all folders.\n文件夹总个数（Total number of folders）：%d" %len(cdragon_folders), print_time = True)
                while True:
                    contCheck = logInput()
                    if contCheck == "":
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
        web_prefix = "https://raw.communitydragon.org/"
        local_prefix = "离线数据（Offline Data）/cdragon"
        updated_files = []
        added_files = []
        error_folders = []
        error_files = []
        folders_to_delete = [] #统计本地存在而数据库不存在的文件夹（Summarize the folders that exist locally but don't exist in the database）
        files_to_delete = [] #统计本地存在而数据库不存在的文件（Summarize the files that exist locally but don't exist in the database）
        for root, dirs, files in os.walk(local_prefix): #要统计本地不存在的文件和文件夹，一定要先把本地有的文件和文件夹全部列出来，然后跟数据库比对，数据库上有的则逐个从待删除列表中移除（To summarize the files and folders that don't exist, the program should first list all the local files and folders, then compare them with the database and remove each file or folder that exists in the database）
            if option == "1" or option == "2" and "latest" in root or option == "3" and "pbe" in root:
                if not root in folders_to_delete and files != []: #请仔细体会后半个条件的作用（Please try to understand the role of the latter condition）
                    folders_to_delete.append(root.replace("\\", "/") + "/")
                if mode == "1": #当更新模式不是全局扫描时，待删除的文件列表不会追加任何文件（When the updating mode isn't [Global Scan], the list that holds the folders to delete won't be appended any files）
                    files_to_delete += list(map(lambda x: os.path.join(root, x).replace("\\", "/"), files))
        cnt1 = 0
        for folder in cdragon_folders:
            cnt1 += 1
            cnt2 = 0
            url = urljoin(web_prefix, folder)
            dir = os.path.join(local_prefix, folder).replace("\\", "/")
            logPrint("[%d/%d]正在检查文件夹（Checking the folder）：%s" %(cnt1, len(cdragon_folders), url), print_time = True)
            table = {"file": [], "size": [], "web_date": [], "web_timestamp": [], "local_date": [], "local_timestamp": []}
            source, status = getUrl(url)
            if status != 0:
                if status == 1:
                    logPrint("文件夹%s信息获取失败！请等待程序结束后手动比对。\nFolder %s information check failed! Please check manually after the program execution finishes." %(url, url), write_time = False)
                    error_folders.append(url)
                    if dir in folders_to_delete: #比对失败的文件夹不应删除（Folders that fail to be checked shouldn't be deleted）
                        folders_to_delete.remove(dir)
                elif status == 404:
                    logPrint("文件夹%s不存在！\nFolder %s not found!" %(url, url), write_time = False)
                continue
            if dir in folders_to_delete:
                folders_to_delete.remove(dir)
            source = source.content.decode()
            source_list = list(map(lambda x: x.strip(), source.split("\n")))
            optionStr = {"1": {"zh_CN": "页面", "en_US": ""}, "2": {"zh_CN": "页面", "en_US": ""}, "3": {"zh_CN": "页面", "en_US": ""}, "4": {"zh_CN": "本程序集涉及的", "en_US": " involved in this program set"}, "5": {"zh_CN": "指定文件夹涉及的", "en_US": " in specified folders"}}
            modeStr = {"1": {"zh_CN": "", "en_US": "File list"}, "2": {"zh_CN": "新" if time_get_method == "1" else "指定修改时间（%s）后的" %(latest_mod_date), "en_US": "New file list" if time_get_method == "1" else "File list after the specified modification time (%s)" %(latest_mod_date)}}
            logPrint("%s%s文件列表如下：\n%s%s is as follows: " %(optionStr[option]["zh_CN"], modeStr[mode]["zh_CN"], modeStr[mode]["en_US"], optionStr[option]["en_US"]), print_time = True)
            logPrint("网页链接（URL)： %s" %url, write_time = False)
            for line in source_list:
                matchedLine = line_re.search(line)
                if matchedLine:
                    soup = BeautifulSoup(line, 'lxml')
                    name = soup.find("a")["href"]
                    size = soup.find("td", class_ = "size").text
                    web_date = soup.find("td", class_ = "date").text
                    web_date_obj = datetime.strptime(web_date, "%Y-%b-%d %H:%M")
                    web_timestamp = web_date_obj.timestamp()
                    local_timestamp = os.path.getmtime(os.path.join(local_prefix, folder, name)) if os.path.exists(os.path.join(local_prefix, folder)) and name in os.listdir(os.path.join(local_prefix, folder)) else 0
                    local_date = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime(local_timestamp))
                    if name.endswith((".json", ".txt", ".js", ".yaml")):
                        #if (option in {"1", "2", "3"} or option == "4" and (folder.endswith("cdragon/tft/") or folder.endswith("v1/") and name in ["champion-summary.json", "cherry-augments.json", "companions.json", "items.json", "lolinventorytype.json", "nexusfinishers.json", "perks.json", "perkstyles.json", "skins.json", "statstones.json", "strawberry-hub.json", "summoner-emotes.json", "summoner-icons.json", "summoner-spells.json", "tftchampions.json", "tftdamageskins.json", "tftitems.json", "tftmapskins.json", "tftplaybooks.json", "tfttraits.json", "tftzoomskins.json", "ward-skins.json"] or folder.endswith("v1/champions/")) or option == "5") and (mode == "1" or mode == "2" and web_timestamp + time.localtime().tm_gmtoff >= (local_timestamp if time_get_method == "1" else latest_mod_timestamp)):
                        if (option in {"1", "2", "3"} or (option == "4" or option == "5") and (folder.endswith("cdragon/tft/") or folder.endswith("v1/") and name in ["champion-summary.json", "cherry-augments.json", "companions.json", "items.json", "lolinventorytype.json", "nexusfinishers.json", "perks.json", "perkstyles.json", "skins.json", "statstones.json", "strawberry-hub.json", "summoner-emotes.json", "summoner-icons.json", "summoner-spells.json", "tftchampions.json", "tftdamageskins.json", "tftitems.json", "tftmapskins.json", "tftplaybooks.json", "tfttraits.json", "tftzoomskins.json", "ward-skins.json"] or folder.endswith("v1/champions/"))) and (mode == "1" or mode == "2" and web_timestamp + time.localtime().tm_gmtoff >= (local_timestamp if time_get_method == "1" else latest_mod_timestamp)): #仅供发行版使用（Only for release）
                            table["file"].append(name)
                            table["size"].append(size)
                            table["web_date"].append(web_date)
                            table["web_timestamp"].append(web_timestamp)
                            table["local_date"].append(local_date)
                            table["local_timestamp"].append(local_timestamp)
            table = pd.DataFrame(table)
            if table.empty:
                logPrint(table, write_time = False)
            else:
                print(format_df(table, width_exceed_ask = False, direct_print = True)[0])
                log.write(format_df(table, width_exceed_ask = False, direct_print = False)[0] + "\n")
            os.makedirs(dir, exist_ok = True)
            for i in range(len(table)):
                cnt2 += 1
                name = table["file"][i]
                file_path = os.path.join(local_prefix, folder, name).replace("\\", "/")
                logPrint("[%d/%d][%d/%d]正在校对文件（Checking file）： %s" %(cnt1, len(cdragon_folders), cnt2, len(table), urljoin(url, name)), print_time = True)
                update = added = False
                src, status = getUrl(urljoin(url, name))
                if status != 0:
                    if status == 1:
                        logPrint("文件%s比对失败！请等待程序结束后手动比对。\nFile %s check failed! Please check manually after the program execution finishes." %(urljoin(url, name), urljoin(url, name)), write_time = False)
                        error_files.append(urljoin(url, name))
                        if file_path in files_to_delete: #比对失败的文件不应删除（Files that fail to be checked shouldn't be deleted）
                            files_to_delete.remove(file_path)
                    elif status == 404:
                        logPrint("文件%s不存在！\nFile %s not found!" %(urljoin(url, name), urljoin(url, name)), write_time = False)
                    continue
                if file_path in files_to_delete:
                    files_to_delete.remove(file_path)
                try:
                    src = src.json() if name.endswith(".json") else src.text.replace("\r", "")
                except json.decoder.JSONDecodeError as e:
                    if "Unexpected UTF-8 BOM (decode using utf-8-sig)" in str(e): #解决方案来自Stack Overflow（The solution comes from https://stackoverflow.com/questions/71025396/asyncio-and-get-unexpected-utf-8-bom）
                        logPrint("文件编码格式错误！正在尝试改用utf-8-sig编码……\nFile decode error! Trying decoding by utf-8-sig ...", write_time = False)
                        src = json.loads(src.text.encode().decode("utf-8-sig"))
                if not name in os.listdir(dir):
                    update = added = True
                else:
                    with open(os.path.join(dir, name), "r", encoding = "utf-8") as fp:
                        dst = json.load(fp) if name.endswith(".json") else fp.read()
                    if src != dst:
                        update = True
                if mode == "1" and update or mode == "2": #当选择全局扫描时，只更新有变化的文档；当选择根据修改时间更新时，如果网页修改时间超前，那么无论文件内容是否发生变化，都重新保存一次，便于后续按照修改时间更新（When the user selects Global Scan, the program updates the changed files. When the user selects Updating according to modification time, if the web modification time of a file succeeds to the local midification time of that, then save the web content to local, no matter whether the web file is same as the local file in terms of content）
                    with open(os.path.join(dir, name), "w", encoding = "utf-8") as fp:
                        if name.endswith(".json"):
                            json.dump(src, fp, indent = 4, ensure_ascii = False)
                        else:
                            fp.write(src)
                if update:
                    if added:
                        logPrint("已添加文件（Added file）：%s" %(os.path.join(dir, name)), print_time = True)
                        added_files.append(urljoin(url, name))
                    else:
                        logPrint("已更新文件（Updated file）：%s" %(os.path.join(dir, name)), print_time = True)
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
        if option in {"1", "2", "3"} and mode == "1" and complete_scan and files_to_delete: #只有全局扫描才可以决定删除哪些文件（Only by [Global Scan] can the program decide which files to delete）
            logPrint("以下%d个文件不存在于数据库中。是否永久删除这些文件？（输入任意非空字符串删除，否则不删除）\nThe following %d file(s) don't exist in the database. Do you want to delete them? (Submit any non-empty string to delete, or null to refuse deleting the files)\n" %(len(files_to_delete), len(files_to_delete)) + "\n".join(files_to_delete), write_time = False)
            delete_str = logInput()
            delete = bool(delete_str)
            if delete:
                for file in files_to_delete:
                    try:
                        os.remove(file)
                    except FileNotFoundError:
                        pass
            logPrint("", write_time = False)
        if option in {"1", "2", "3"} and complete_scan and folders_to_delete:
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
        logPrint("请选择更新模式：\nPlease select the update mode:\n1\t全局比对（Global Compare）\n☆2\t按程序需求更新（默认）【Updating According to Program Demands (by default)】", write_time = False)
        mode = logInput()
        if mode != "" and mode[0] == "1":
            mode = "1"
        else:
            mode = "2"
        if ddragon_hint:
            hint = '请按以下步骤操作：\nPlease follow these steps:\n1. 访问网址https://developer.riotgames.com/docs/lol#data-dragon\n   Visit the website: https://developer.riotgames.com/docs/lol#data-dragon\n2. 在Latest中找到正式服最新版本数据资源压缩包下载链接。例如：https://ddragon.leagueoflegends.com/cdn/dragontail-15.17.1.tgz\n   Find the link to download the compressed tarball of the latest data resource for live servers. For example: https://ddragon.leagueoflegends.com/cdn/dragontail-15.17.1.tgz\n3. 下载。这需要花费一些时间。\n   Download the file. It may take some time.\n4. 将下载好的tgz文件直接“解压至此”。\n   "Extract here" for the tgz file.\n5. 将解压出来的压缩包再次解压到选定文件夹下与压缩包同名的文件夹。示例：将“dragontail-15.17.1.tar”解压到“D:/360AI浏览器下载/dragontail-15.17.1”文件夹下。\nExtract to "Archive-Name" folder under the selected folder for the extracted tar file. For example, extract "dragontail-15.17.1.tar" into the folder "D:/Downloads/dragontail-15.17.1".\n接下来，请给出数据资源的位置。（按照上例应为“D:/360AI浏览器下载/dragontail-15.17.1/15.17.1/data”。）\nNext, please provide the directory that stores the data resources. (By the above example, the directory should be "D:/Downloads/dragontail-15.17.1/15.17.1/data".)'
            logPrint(hint, write_time = False)
            ddragon_hint = False
        else:
            logPrint("请给出数据资源的位置。\nPlease provide the directory that stores the data resources.", write_time = False)
        dst_folder = "离线数据（Offline Data）/ddragon"
        while True:
            src_folder = logInput()
            try:
                if not ("en_US" in os.listdir(src_folder) and "zh_CN" in os.listdir(src_folder)):
                    logPrint("您输入的地址有误！请重新输入！\nERROR input of data resource directory! Please try again!", write_time = False)
                else:
                    break
            except FileNotFoundError:
                logPrint("您输入的地址有误！请重新输入！\nERROR input of data resource directory! Please try again!", write_time = False)
        added_files = []
        updated_files = []
        error_files = []
        cnt1 = 0
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                update = added = False
                if mode == "1" and file.endswith(".json") or mode == "2" and file == "championFull.json":
                    src_path = os.path.join(root, file).replace("\\", "/")
                    relative_path = os.path.relpath(root, src_folder).replace("\\", "/")
                    dst_path = os.path.join(dst_folder, relative_path, file).replace("\\", "/")
                    if "en_US" in relative_path or "zh_CN" in relative_path:
                        cnt1 += 1
                        os.makedirs(os.path.dirname(dst_path), exist_ok = True)
                        logPrint("[%d]正在校对文件（Checking file）： %s" %(cnt1, src_path), print_time = True)
                        with open(src_path, "r", encoding = "utf-8") as fp:
                            src = json.load(fp)
                        if not file in os.listdir(os.path.join(dst_folder, relative_path)):
                            update = added = True
                        else:
                            with open(dst_path, "r", encoding = "utf-8") as fp:
                                dst = json.load(fp)
                            if src != dst:
                                update = True
                        if update:
                            with open(dst_path, "w", encoding = "utf-8") as fp:
                                json.dump(src, fp, indent = 4, ensure_ascii = False)
                            if added:
                                logPrint("[%d]已添加文件（Added file）：%s" %(cnt1, dst_path), print_time = True)
                                added_files.append(src_path)
                            else:
                                logPrint("[%d]已更新文件（Updated file）：%s" %(cnt1, dst_path), print_time = True)
                                updated_files.append(src_path)
        cnt1 += 1
        version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
        logPrint("[%d]正在校对文件（Checking file）： %s" %(cnt1, version_url), print_time = True)
        update = added = False
        src, status = getUrl(version_url)
        if status != 0:
            if status == 1:
                logPrint("文件%s比对失败！请等待程序结束后手动比对。\nFile %s check failed! Please check manually after the program execution finishes." %(version_url, version_url), write_time = False)
            elif status == 404:
                logPrint("文件%s不存在！请等待程序结束后手动比对。\nFile %s not found! Please check manually after the program execution finishes." %(version_url, version_url), write_time = False)
            error_files.append(version_url)
            continue
        src = src.json()
        if not "versions.json" in os.listdir("离线数据（Offline Data）"):
            update = added = True
        else:
            with open("离线数据（Offline Data）/versions.json", "r", encoding = "utf-8") as fp:
                dst = json.load(fp)
            if src != dst:
                update = True
        if update:
            with open("离线数据（Offline Data）/versions.json", "w", encoding = "utf-8") as fp:
                json.dump(src, fp, indent = 4, ensure_ascii = False)
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