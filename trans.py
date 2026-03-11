import json, os, pandas, requests, shutil, time, unicodedata
from wcwidth import wcswidth
from urllib.parse import urljoin
from typing import Any, Literal

def requestUrl(method: str, url: str, session: requests.sessions.Session | None = None, **kwargs: Any) -> tuple[requests.models.Response, int, requests.sessions.Session]:
    if session == None:
        session = requests.Session()
        # session.trust_env = False
    retry: int = 0
    while True:
        retry += 1
        try:
            source = session.request(method, url, **kwargs)
        except Exception as e:
            session = requests.Session()
            if retry > 5:
                source = requests.Response() #这只是为了保持代码类型检查的一致性（This is meant to keep consistency for code type checking）
                source.status_code = -1
                # session.trust_env = False
                break
            if isinstance(e, requests.exceptions.SSLError):
                if "[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol" in str(e):
                    print(f"违反协议导致读取中断！正在尝试第{retry}次重新获取数据！\nEOF occurred in violation of protocol! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
                elif "certificate verify failed" in str(e):
                    print(f"SSL证书验证失败！正在尝试第{retry}次重新获取数据！\nSSL certificate verify failed! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
                elif "Max retries exceeded with url" in str(e):
                    print(f"请求数量超过限制！正在尝试第{retry}次重新获取数据！\nMax retries exceed with url! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
            elif isinstance(e, requests.exceptions.ProxyError):
                print(f"无法连接到代理！正在尝试第{retry}次重新获取数据！\nCannot connect to proxy! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
            elif isinstance(e, requests.exceptions.ChunkedEncodingError):
                print(f"接收数据块长度不正确导致连接中断！正在尝试第{retry}次重新获取数据！\nConnection broken: InvalidChunkLength. Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
            elif isinstance(e, requests.exceptions.ConnectionError):
                if "Failed to establish a new connection: [Errno 11001] getaddrinfo failed" in str(e):
                    print(f"无法获取网址信息，因此无法建立连接！正在尝试第{retry}次重新获取数据！\nCannot get address information, so connection can't be established! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
                else:
                    print(f"由于远程服务器端无响应，连接已关闭！正在尝试第{retry}次重新获取数据！\nRemote end closed connection without response. Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
            elif isinstance(e, requests.exceptions.ReadTimeout):
                print(f"读取超时！正在尝试第{retry}次重新获取数据！\nRead time out! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
            else:
                print(e)
                print(f"请求失败！正在尝试第{retry}次重新获取数据！\nRequest failed! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
        else:
            try:
                source.raise_for_status()
            except Exception as e:
                session = requests.Session()
                # session.trust_env = False
                if retry > 5:
                    break
                if isinstance(e, requests.exceptions.HTTPError):
                    if e.response.status_code in {403, 404}:
                        return (source, e.response.status_code, session)
                else:
                    print(e)
                    print(f"请求失败！正在尝试第{retry}次重新获取数据！\nRequest failed! Trying to recapture the data with url: {url}. Time(s) tried: {retry}")
            else:
                return (source, source.status_code, session)
    return (source, source.status_code, session)

def count_nonASCII(s: str) -> int: #统计一个字符串中占用命令行2个宽度单位的字符个数（Count the number of characters that take up 2 width unit in CMD）
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str) -> str: #移除一个字符串中的所有C0和C1字符（Remove all C0 and C1 characters from a string）
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc")

def format_df(df: pandas.DataFrame, width_exceed_ask: bool = True, direct_print: bool = False, print_header: bool = True, print_index: bool = False, reserve_index: bool = False, start_index: int = 0, header_align: str = "^", align: str = "^", align_replicate_rule: Literal["all", "last"] = "all") -> tuple[str, dict[str, int]]: #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
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
            # print("单行数据字符串输出宽度超过当前终端窗口宽度！将直接打印该数据框！\nThe output width of each record string exceeds the current width of the terminal window! The program is going to directly print this dataframe!")
            result = str(df)
            return (result, maxLens)
        # else:
        #     print("单行数据字符串输出宽度超过当前终端窗口宽度！将继续格式化输出！\nThe output width of each record string exceeds the current width of the terminal window! The program is going on formatted printing!")
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
            alignments_tmp: list[str] = list(align)
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
                field: str = fields[i]
                tmp: str = "{0:{align}{w}}".format(rm_ctrl_char(field), align = header_alignments[i], w = maxLens[field] - count_nonASCII(field))
                result += tmp
                #print(tmp, end = "")
                if i != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            result += "\n"
            #print()
        index: int = start_index
        for i in range(df.shape[0]):
            if print_index:
                result += "{0:>{w}}".format(old_index[index - start_index] if reserve_index else index, w = index_len) + "  "
            for j in range(df.shape[1]):
                field = fields[j]
                cell: str = str(list(df[field])[i])
                tmp = "{0:{align}{w}}".format(rm_ctrl_char(cell), align = alignments[j], w = maxLens[field] - count_nonASCII(cell))
                result += tmp
                #print(tmp, end = "")
                if j != df.shape[1] - 1:
                    result += "  "
                    #print("  ", end = "")
            if i != df.shape[0] - 1:
                result += "\n"
            #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the above line）
            index += 1
    else:
        print("排列方式参数错误！请传入字符串。\nAlignment parameter ERROR! Please pass a string instead.")
    return (result, maxLens)

#允许用户选择语言（This program allows users to select a language）
print('请选择翻译语言。输入“all”以翻译成所有语言。\nPlease select a language to translate into. Submit "all" to translate into all languages.')
language_ddragon: dict[int, dict[str, str]] = {1: {"CODE": "ar_AE", "LANGUAGE (EN)": "Arabic (United Arab Emirates)", "LANGUAGE (ZH)": "阿拉伯语（阿拉伯联合酋长国）", "Applicable CDragon Data Patches": "9.20～10.1, 13.20+"}, 2: {"CODE": "cs_CZ", "LANGUAGE (EN)": "Czech (Czech Republic)", "LANGUAGE (ZH)": "捷克语（捷克共和国）", "Applicable CDragon Data Patches": "7.1+"}, 3: {"CODE": "el_GR", "LANGUAGE (EN)": "Greek (Greece)", "LANGUAGE (ZH)": "希腊语（希腊）", "Applicable CDragon Data Patches": "9.1+"}, 4: {"CODE": "pl_PL", "LANGUAGE (EN)": "Polish (Poland)", "LANGUAGE (ZH)": "波兰语（波兰）", "Applicable CDragon Data Patches": "9.1+"}, 5: {"CODE": "ro_RO", "LANGUAGE (EN)": "Romanian (Romania)", "LANGUAGE (ZH)": "罗马尼亚语（罗马尼亚）", "Applicable CDragon Data Patches": "9.1+"}, 6: {"CODE": "hu_HU", "LANGUAGE (EN)": "Hungarian (Hungary)", "LANGUAGE (ZH)": "匈牙利语（匈牙利）", "Applicable CDragon Data Patches": "9.1+"}, 7: {"CODE": "en_GB", "LANGUAGE (EN)": "English (United Kingdom)", "LANGUAGE (ZH)": "英语（英国）", "Applicable CDragon Data Patches": "9.1+"}, 8: {"CODE": "de_DE", "LANGUAGE (EN)": "German (Germany)", "LANGUAGE (ZH)": "德语（德国）", "Applicable CDragon Data Patches": "7.1+"}, 9: {"CODE": "es_ES", "LANGUAGE (EN)": "Spanish (Spain)", "LANGUAGE (ZH)": "西班牙语（西班牙）", "Applicable CDragon Data Patches": "9.1+"}, 10: {"CODE": "it_IT", "LANGUAGE (EN)": "Italian (Italy)", "LANGUAGE (ZH)": "意大利语（意大利）", "Applicable CDragon Data Patches": "9.1+"}, 11: {"CODE": "fr_FR", "LANGUAGE (EN)": "French (France)", "LANGUAGE (ZH)": "法语（法国）", "Applicable CDragon Data Patches": "9.1+"}, 12: {"CODE": "ja_JP", "LANGUAGE (EN)": "Japanese (Japan)", "LANGUAGE (ZH)": "日语（日本）", "Applicable CDragon Data Patches": "9.1+"}, 13: {"CODE": "ko_KR", "LANGUAGE (EN)": "Korean (Korea)", "LANGUAGE (ZH)": "朝鲜语（韩国）", "Applicable CDragon Data Patches": "9.7+"}, 14: {"CODE": "es_MX", "LANGUAGE (EN)": "Spanish (Mexico)", "LANGUAGE (ZH)": "西班牙语（墨西哥）", "Applicable CDragon Data Patches": "9.1+"}, 15: {"CODE": "es_AR", "LANGUAGE (EN)": "Spanish (Argentina)", "LANGUAGE (ZH)": "西班牙语（阿根廷）", "Applicable CDragon Data Patches": "9.7+"}, 16: {"CODE": "pt_BR", "LANGUAGE (EN)": "Portuguese (Brazil)", "LANGUAGE (ZH)": "葡萄牙语（巴西）", "Applicable CDragon Data Patches": "9.1+"}, 17: {"CODE": "en_US", "LANGUAGE (EN)": "English (United States)", "LANGUAGE (ZH)": "英语（美国）", "Applicable CDragon Data Patches": "9.1+"}, 18: {"CODE": "en_AU", "LANGUAGE (EN)": "English (Australia)", "LANGUAGE (ZH)": "英语（澳大利亚）", "Applicable CDragon Data Patches": "9.1+"}, 19: {"CODE": "ru_RU", "LANGUAGE (EN)": "Russian (Russia)", "LANGUAGE (ZH)": "俄语（俄罗斯）", "Applicable CDragon Data Patches": "9.1+"}, 20: {"CODE": "tr_TR", "LANGUAGE (EN)": "Turkish (Turkey)", "LANGUAGE (ZH)": "土耳其语（土耳其）", "Applicable CDragon Data Patches": "9.1+"}, 21: {"CODE": "ms_MY", "LANGUAGE (EN)": "Malay (Malaysia)", "LANGUAGE (ZH)": "马来语（马来西亚）", "Applicable CDragon Data Patches": ""}, 22: {"CODE": "en_PH", "LANGUAGE (EN)": "English (Republic of the Philippines)", "LANGUAGE (ZH)": "英语（菲律宾共和国）", "Applicable CDragon Data Patches": "10.5+"}, 23: {"CODE": "en_SG", "LANGUAGE (EN)": "English (Singapore)", "LANGUAGE (ZH)": "英语（新加坡）", "Applicable CDragon Data Patches": "10.5+"}, 24: {"CODE": "th_TH", "LANGUAGE (EN)": "Thai (Thailand)", "LANGUAGE (ZH)": "泰语（泰国）", "Applicable CDragon Data Patches": "9.7+"}, 25: {"CODE": "vn_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "9.7～13.9"}, 26: {"CODE": "vi_VN", "LANGUAGE (EN)": "Vietnamese (Viet Nam)", "LANGUAGE (ZH)": "越南语（越南）", "Applicable CDragon Data Patches": "12.17+"}, 27: {"CODE": "id_ID", "LANGUAGE (EN)": "Indonesian (Indonesia)", "LANGUAGE (ZH)": "印度尼西亚语（印度尼西亚）", "Applicable CDragon Data Patches": ""}, 28: {"CODE": "zh_MY", "LANGUAGE (EN)": "Chinese (Malaysia)", "LANGUAGE (ZH)": "中文（马来西亚）", "Applicable CDragon Data Patches": "10.5+"}, 29: {"CODE": "zh_CN", "LANGUAGE (EN)": "Chinese (China)", "LANGUAGE (ZH)": "中文（中国）", "Applicable CDragon Data Patches": "9.7+"}, 30: {"CODE": "zh_TW", "LANGUAGE (EN)": "Chinese (Taiwan)", "LANGUAGE (ZH)": "中文（台湾）", "Applicable CDragon Data Patches": "9.7+"}}
language_cdragon: dict[str, str] = {}
for i in language_ddragon:
    if language_ddragon[i]["CODE"] == "en_US":
        language_cdragon[language_ddragon[i]["CODE"]] = "default" #在CommunityDragon数据库上，美服正式服的数据资源代码是default，而不是小写的en_US（The code for English (US) data resources on CommunityDragon database is "default" instead of the lowercase of "en_US"）
    else:
        language_cdragon[language_ddragon[i]["CODE"]] = language_ddragon[i]["CODE"].lower()
language_dict: dict[str, list[int | str]] = {"No.": list(language_ddragon.keys()), "CODE": list(map(lambda x: x["CODE"], language_ddragon.values())), "LANGUAGE": list(map(lambda x: x["LANGUAGE (EN)"], language_ddragon.values())), "语言": list(map(lambda x: x["LANGUAGE (ZH)"], language_ddragon.values())), "Applicable CDragon Data Patches": list(map(lambda x: x["Applicable CDragon Data Patches"], language_ddragon.values()))}
language_df: pandas.DataFrame = pandas.DataFrame(language_dict)
print(format_df(language_df)[0])
while True:
    language_option: str = input()
    if language_option == "" or language_option in [str(i) for i in range(1, 31)]:
        if language_option == "":
            language_option = "29"
        language_code: str = language_ddragon[int(language_option)]["CODE"]
        break
    elif language_option[0] == "0":
        exit()
    elif language_option == "all":
        language_code = ""
        break
    else:
        print("语言选项输入错误！请重新输入：\nERROR input of language option! Please try again:")
if language_option == "all":
    language_codes: list[str] = language_dict["CODE"]
else:
    language_codes = [language_code]
session: requests.Session = requests.Session()
#获取翻译相关文件的地址（Get the URLs of translation files）
print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
print("正在读取美测服在线索引……\nReading the online index file of pbe data resources...")
source, status, session = requestUrl("GET", "https://raw.communitydragon.org/pbe/cdragon/files.exported.txt", session)
if status != 200:
    if status == -1:
        print("获取索引失败！请检查系统网络状况和代理设置。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.")
    elif status == 404:
        print("获取索引失败！请检查以下链接的可用性。程序即将退出。\nIndex capture failure! Please check the system network condition and agent configuration. The program will exit now.\nhttps://raw.communitydragon.org/pbe/cdragon/files.exported.txt")
    time.sleep(3)
    exit()
files_exported_pbe: list[str] = source.text.strip("\n").split("\n")
for i in range(len(language_codes)):
    language_code: str = language_codes[i]
    trans_files: list[str] = [file for file in files_exported_pbe if file.endswith(".json") and file.split("/")[-1].startswith("trans") and language_cdragon[language_code] in file]
    trans_files.sort()
    #获取最新翻译数据（Get the latest translation data）
    web_prefix: str = "https://raw.communitydragon.org/pbe/"
    local_prefix: str = "离线数据（Offline Data）/cdragon/pbe/"
    try:
        with open("trans.json", "r", encoding = "utf-8") as fp:
            trans_data: dict[str, dict[str, str]] = json.load(fp)
    except:
        trans_data = {}
    trans_data[language_code] = {}
    cnt: int = 0
    for file in trans_files:
        mode: str = "online"
        url: str = urljoin(web_prefix, file)
        cnt += 1
        print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
        print("[%d/%d][%d/%d]正在获取文件（Fetching file）： %s" %(i + 1, len(language_codes), cnt, len(trans_files), url))
        src, status, session = requestUrl("GET", url, session)
        if status != 200:
            if status == -1:
                print("翻译数据获取失败！将转为离线模式。\nTranslation data capture failed. The program is going to retry in the offline mode.")
            elif status == 404:
                print("文件%s不存在！\nFile %s not found!" %(url, url))
            mode = "offline"
            print('请输入一个包含以下文件的文件夹，注意文件夹结构对应：（输入“0”以跳过该文件）\nPlease input a folder containing the following files. Note that the folder structure should comply with the following files: (Submit "0" to skip this file)')
            print(file)
            while True:
                folder: str = input()
                if folder == "":
                    folder = local_prefix
                elif folder == "0":
                    break
                path: str = os.path.join(folder, file).replace("\\", "/")
                print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
                print("[%d/%d]正在获取文件（Fetching file）： %s" %(cnt, len(trans_files), path))
                try:
                    with open(path, "r", encoding = "utf-8") as fp:
                        src = json.load(fp)
                except FileNotFoundError:
                    print('未找到文件“%s”！请输入正确的翻译数据文件夹路径！\nFile "%s" NOT found! Please input a correct translation data folder!' %(path, path))
                    continue
                except OSError:
                    print("数据文件名不合法！请输入合法的翻译数据文件夹路径！\nIllegal data filename! Please input a valid translation data folder.")
                    continue
                except json.decoder.JSONDecodeError:
                    print("数据格式错误！请选择一个符合CommunityDragon数据库中记录的翻译数据格式（%s）的数据文件！\nData format mismatched! Please select a data file that corresponds to the format of the translation data archived in CommunityDragon database (%s)!" %(urljoin(web_prefix, file), urljoin(web_prefix, file)))
                    continue
                else:
                    trans_data[language_code][file] = src
                    break
        if mode == "online":
            try:
                trans_data[language_code][file] = src.json()
            except json.decoder.JSONDecodeError as e:
                if "Unexpected UTF-8 BOM (decode using utf-8-sig)" in str(e): #解决方案来自Stack Overflow（The solution comes from https://stackoverflow.com/questions/71025396/asyncio-and-get-unexpected-utf-8-bom）
                    print("文件编码格式错误！正在尝试改用utf-8-sig编码……\nFile decode error! Trying decoding by utf-8-sig ...")
                    trans_data[language_code][file] = json.loads(src.text.encode().decode("utf-8-sig"))
    #调整字典键序（Adjust the order of keys）
    trans_data_organized: dict[str, dict[str, str]] = {}
    for i in language_ddragon:
        language_code_tmp: str = language_ddragon[i]["CODE"]
        if language_code_tmp in trans_data:
            trans_data_organized[language_code_tmp] = trans_data[language_code_tmp]
    #保存获取到的翻译数据（Export the captured translation data）
    with open("trans.json", "w", encoding = "utf-8") as fp:
        json.dump(trans_data_organized, fp, indent = 4, ensure_ascii = False)
print("翻译数据保存成功！请查看同文件夹下的trans.json。程序即将退出！\nAll translation data are saved successfully! Please check trans.json under the same folder. The program will now exit!")
time.sleep(3)
