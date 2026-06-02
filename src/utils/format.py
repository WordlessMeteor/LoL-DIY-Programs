import datetime, json, numpy, pandas, shutil, unicodedata, uuid
from wcwidth import wcswidth
from typing import Any, Generator, Iterable, Literal, Optional

def format_json(origin: str, indent_char: str = " ", number: int = 4) -> str: #对字符串origin进行格式化（Formalize the string `origin`）
    '''
    将一串不可通过json.loads函数读取的json字符串进行格式化。<br>Format a piece of json string that can't be loaded by `json.loads` function.<br>示例（Example）：https://ddragon.leagueoflegends.com/cdn/15.24.1/data/zh_CN/tft-unlockable.json 。
    
    :param origin: 一段**缩进单位为0**的json字符串。<br>A json string with **0 indentation unit**.
    :type origin: str
    :param indent_char: 缩进字符。默认为一个空格。<br>The character used for indentation. A space by default.
    :type indent_char: str
    :param number: 缩进单位数。默认为4。<br>The number of indentation characters per unit. 4 by default.
    :type number: int
    :return: 格式化后的json字符串。<br>Formatted json string.
    :rtype: str
    '''
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

def optimize_bool_display(df: pandas.DataFrame, onTrue: str = "√", onFalse: str = "") -> None:
    '''
    优化数据框的逻辑值显示。<br>Optimize the boolean value display of a dataframe.
    
    :param df: 数据框。<br>A dataframe.
    :type df: pandas.DataFrame
    :param onTrue: 用于替换逻辑列的单元格为True的字符串。默认为“√”。<br>The string to replace "True"s in a boolean column. "√" by default.
    :type onTrue: str
    :param onFalse: 用于替换逻辑列的单元格为False的字符串。默认为空字符串。<br>The string to replace "False"s in a boolean column. An empty string by default.
    :type onFalse: str
    
    本方法对原数据框进行原位替换，因此不返回值。<br>This method performs in-vivo substitutions on the original dataframe and thus doesn't return any value.
    '''
    for column in df:
        if df[column].dtype == "bool":
            df[column] = df[column].astype(str)
            df[column] = list(map(lambda x: "√" if x == "True" else "", df[column].to_list()))

def count_nonASCII(s: str) -> int:
    '''
    统计一个字符串中占用命令行2个宽度单位的字符个数。<br>Count the number of characters that take up 2 width unit in CMD.
    
    :param s: 任意字符串。<br>Any string.
    :type s: str
    :return: 占用2个宽度单位的字符个数。<br>The number of characters that take up 2 width.
    :rtype: int
    '''
    return sum([unicodedata.east_asian_width(character) in ("F", "W") for character in list(str(s))])

def rm_ctrl_char(s: str) -> str:
    '''
    移除一个字符串中的所有C0和C1字符。<br>Remove all C0 and C1 characters from a string.
    
    :param s: 原字符串。<br>The original string.
    :type s: str
    :return: 移除终端中显示异常的字符后的字符串。<br>The result string after removing characters that don't display correctly in terminal.
    :rtype: str
    '''
    return "".join(ch for ch in s if unicodedata.category(ch) != "Cc") #该表达式等价于（This expression is equivalent to）`re.sub(r"[\x00-\x1F\x7F-\x9F]", "", s)`

def format_df(df: pandas.DataFrame, width_exceed_ask: bool = True, direct_print: bool = False, print_header: bool = True, print_index: bool = False, reserve_index: bool = False, start_index: int = 0, header_align: str = "^", align: str = "^", align_replicate_rule: Literal["all", "last"] = "all") -> tuple[str, dict[str, int]]: #按照每列最长字符串的命令行宽度加上2，再根据每个数据的中文字符数量决定最终格式化输出的字符串宽度（Get the width of the longest string of each column, add it by 2, and substract it by the number of each cell string's Chinese characters to get the final width for each cell to print using `format` function）
    '''
    将数据框转化为列对齐的字符串，用于排版输出。<br>Transform a dataframe into a string where columns are aligned for better page layout.
    
    :param df: 要排版的数据框。<br>A dataframe to transform into a layout-organized string.
    :type df: pandas.DataFrame
    :param width_exceed_ask: 单行字符串宽度超过终端宽度时，是否从用户输入读取排版策略。默认为真。<br>Whether to read the layout strategy from user input when the max width of lines is bigger than the terminal width. True by default.
    :type width_exceed_ask: bool
    :param direct_print: 指定为真时，通过内置的str方法直接获取其字符串，否则仍进行排版优化。仅当direct_print参数指定为真时可用。默认为假。<br>When the max width of lines is bigger than the terminal width, if it's True, then get the string by the dataframe's internal `str` method; otherwise, the function will persist on layout optimization. Available only when `direct_print` is True. False by default.
    :type direct_print: bool
    :param print_header: 是否打印表头。默认为真。<br>Whether to print the header. True by default.
    :type print_header: bool
    :param print_index: 是否打印索引列。默认为假。<br>Whether to print the index column. False by default.
    :type print_index: bool
    :param reserve_index: 在打印索引列时，是否输出原始索引。指定为真时则输出原始索引，否则输出从start_index到start_index + len(df) - 1的索引。<br>Whether to print the original indices, when the index column is going to be printed. If it's True, then print the original indices; otherwise, print the index from `start_index` to `start_index + len(df) - 1`.
    :type reserve_index: bool
    :param start_index: 在输出处理后的索引时的起始索引。仅当打印索引列但不输出原始索引时可用。默认值为0。<br>The starting index when the function prints the processed indices. Available only when the index column is going to be printed but not the original indices. Default value is 0.
    :type start_index: int
    :param header_align: 表头对齐方式。可取“<”“^”和“>”三个字符的任意组合。<br>The alignment method of headers, which may be composed of any number of any character among "<", "^" and ">".
        <pre>
        **value**       **description**<br>
        &nbsp;<       左对齐（Left-aligned）<br>
        &nbsp;^       居中对齐（Centered）<br>
        &nbsp;>       右对齐（Right-aligned）
        </pre>
    :type header_align: str
    :param align: 单元格对齐方式。取值规则同header_align参数。<br>The alignment method of cells, whose possible values are the same as those of `header_align` parameter.
    :type align: str
    :param align_replicate_rule: 当表头对齐方式参数和单元格对齐方式参数字符串长度小于列数时，对齐方式的填充规则。共有“all”和“last”两种取值。<br>The rule of filling the aligment method when the alignment method string of headers or cells is less than the number of columns. There're two possible values for this parameter: "all" and "last".
    
        - all: 将整个对齐方式规则循环往复地填充至剩余列。<br>Recursively fill the whole set of alignment methods in the rest of columns.<br>【例】在仅指定前三列单元格的对齐方式分别是左对齐、居中对齐和右对齐的情况下，第四至六列单元格的对齐方式将依次是左对齐、居中对齐和右对齐，往复。<br>[Example] When only the first three columns of cells are specified left-aligned, centered and right-aligned, respectively, the fourth to sixth columns of cells shall be left-aligned, centered and right-aligned, respectively, and so on.
        - last: 将最后一个被指定对齐方式的列的对齐方式填充至剩余列。<br>Fill the alignment method of the last one of the columns specified with alignment methods in the rest of columns.<br>【例】在仅指定前三列单元格的对齐方式分别是左对齐、居中对齐和右对齐的情况下，后面所有列的对齐方式将都是右对齐。<br>[Example] When only the first three columns of cells are specified left-aligned, centered and right-aligned, respectively, all of the subsequent columns of cells shall be right-aligned.
    :type align_replicate_rule: str
    :return: 由格式化字符串和各列宽度字典组成的元组。<br>A tuple composed of the formatted string and each column's width dictionary.
    :rtype: tuple[str, dict[str, str]]
    '''
    df = df.copy(deep = True) #深复制，防止原数据框被修改（Deep copy prevents the original dataframe from being changed）
    old_index: pandas.Index = df.index #用于存储旧索引。当`reserve_index`为真时，将输出旧索引（Stores the old indices. When `reserve_index` is True, the program outputs the old indices）
    df.index = pandas.Index(range(start_index, len(df) + start_index)) #新索引允许从`start_index`开始，默认从0开始（New indices allow starting from `start_index`, which is 0 by default）
    maxLens: dict[str, int] = {} #存储不同列的最大字符串宽度（Stores the max string lengths of different columns）
    maxWidth: int = shutil.get_terminal_size()[0] #获取当前终端的单行宽度（Get the line width of the current terminal）
    fields: list[str] = df.columns.tolist()
    for field in fields: #计算每一列的最大字符串宽度（Calculate the max string length of each column）
        maxLens[field] = max(0 if len(df) == 0 else max(map(lambda x: wcswidth(rm_ctrl_char(str(x))), df[field])), wcswidth(rm_ctrl_char(str(field)))) + 2
    index_len: int = 0 if len(df) == 0 else max(map(lambda x: len(str(x)), old_index)) if reserve_index else max(len(str(start_index)), len(str(start_index + len(df) - 1))) #计算索引列的最大字符串宽度（Calculate the max string length of the index column）
    if sum(maxLens.values()) + 2 * (len(fields) - 1) > maxWidth or print_index and index_len + sum(maxLens.values()) + 2 * len(fields) > maxWidth: #字符串宽度和超出终端窗口宽度的情形（The case where the sum of the string lengths exceeds the terminal size）
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
    result: str = "" #结果字符串初始化（Initialize the result string）
    #确定各列的排列方向（Determine the alignments of all columns）
    if isinstance(header_align, str) and isinstance(align, str): #确保排列方向参数无误（Ensure the alignment parameters are valid）
        if not all(map(lambda x: x in {"<", "^", ">"}, header_align)) or not all(map(lambda x: x in {"<", "^", ">"}, align)):
            print('排列方式字符串参数错误！排列方式必须是“<”“^”或者“>”中的一个。请修改排列方式字符串参数。\nParameter ERROR of the alignment string! The alignment value must be one of {"<", "^", ">"}. Please change the alignment string parameter.')
        if len(header_align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            header_alignments: list[str] = ["^"] * df.shape[1]
        elif len(header_align) == 1:
            header_alignments = [header_align] * df.shape[1]
        else:
            header_alignments_tmp = list(header_align)
            if len(header_align) < df.shape[1]: #表头排列规则字符串长度小于数据框列数时，通过排列方式列表补充规则进行补充（When the length of `header_align` is less than the number of the dataframe's columns, supplement the rest of the rules according to `align_replicate_rule`）
                if align_replicate_rule == "last": #仅重复最后一列的排列方式（Only replicate the alignment of the last column）
                    header_alignments = header_alignments_tmp + [header_alignments_tmp[-1]] * (df.shape[1] - len(header_align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    header_alignments = header_alignments_tmp * (df.shape[1] // len(header_align)) + header_alignments_tmp[:df.shape[1] % len(header_align)] #所有排列方式循环补充（Supplement the alignments in a cycle of the whole `header_alignment` string）
            else: #表头排列规则字符串大于等于数据框列数时，取长度等于数据框列数的字符串开头切片（When the length of `header_align` is greater than or equal to the number of the dataframe's columns, get the slice at the beginning of `header_align` whose length equal to the number of the dataframe's columns）
                header_alignments = header_alignments_tmp[:df.shape[1]]
        if len(align) == 0: #指定为空字符串，即默认居中输出（Specifying it as a null string means output centered by default）
            alignments: list[str] = ["^"] * df.shape[1]
        elif len(align) == 1:
            alignments = [align] * df.shape[1]
        else:
            alignments_tmp: list[str] = list(align)
            if len(align) < df.shape[1]: #数据排列规则字符串长度小于数据框列数时，通过排列方式列表补充规则进行补充（When the length of `align` is less than the number of the dataframe's columns, supplement the rest of the rules according to `align_replicate_rule`）
                if align_replicate_rule == "last": #仅重复最后一列的排列方式（Only replicate the alignment of the last column）
                    alignments = alignments_tmp + [alignments_tmp[-1]] * (df.shape[1] - len(align))
                else:
                    if align_replicate_rule != "all":
                        print("排列方式列表补充规则不合法！将默认采用全部填充。\nAlignment list supplement rule illegal! The whole alignment string will be replicated.")
                    alignments = alignments_tmp * (df.shape[1] // len(align)) + alignments_tmp[:df.shape[1] % len(align)]
            else: #数据排列规则字符串大于等于数据框列数时，取长度等于数据框列数的字符串开头切片（When the length of `align` is greater than or equal to the number of the dataframe's columns, get the slice at the beginning of `header_align` whose length equal to the number of the dataframe's columns）
                alignments = alignments_tmp[:df.shape[1]]
        if print_header: #打印表头（Prints the header）
            if print_index: #打印表头时，如果输出索引，由于表头没有索引，所以用空格代替（Spaces will be printed as the index part of the header）
                result += " " * (index_len + 2)
            for i in range(df.shape[1]):
                field: str = fields[i]
                tmp: str = "{0:{align}{w}}".format(rm_ctrl_char(str(field)), align = header_alignments[i], w = maxLens[field] - count_nonASCII(field))
                result += tmp
                #print(tmp, end = "")
                if i != df.shape[1] - 1: #未到行尾时，用两个空格来分割该列和下一列（When the program doesn't reach the end of the line, separate this column and the next column by two spaces）
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
                if j != df.shape[1] - 1: #未到行尾时，用两个空格来分割该列和下一列（When the program doesn't reach the end of the line, separate this column and the next column by two spaces）
                    result += "  "
                    #print("  ", end = "")
            if i != df.shape[0] - 1:
                result += "\n"
            #print() #注意这里的缩进和上一行不同（Note that here the indentation is different from the above line）
            index += 1
    else:
        print("排列方式参数错误！请传入字符串。\nAlignment parameter ERROR! Please pass a string instead.")
    return (result, maxLens)

def eliminate_empty_fields(df: pandas.DataFrame, header: Optional[int | list[int]] = 0, na_values: Any | Iterable[Any] = None) -> pandas.DataFrame:
    '''
    移除一个数据框中所有值全为空值的列。空值包括空字符串和0。<br>Remove the columns where each value is an empty value from a dataframe. An empty value includes an empty string and 0.
    
    传入的数据框不得是转置后的。即数据框的列应当代表字段，而不是索引。<br>`df` shouldn't be transposed. That is, the columns of `df` should represent fields instead of indices.
    
    :param df: 要消除空列的数据框。操作将在此数据框上**原位**进行。<br>Dataframes to eliminate empty fields. The operation is performed **in vivo**.
    :type df: pandas.DataFrame
    :param header: 数据区域中作为表头的部分。适用于本存储库中将中文表头作为数据区域第0行的数据框，此时header应指定为`0`或者`[0]`。
    :type header: The header indices in the data area. Applys to the dataframes which takes the 0th line as the Chinese header, when `header` should be specified as `0` or `[0]`.
    :param na_values: 数据框中的缺失数据。默认为`numpy.nan`。<br>NA values in the dataframe. `numpy.nan` by default.
    :type na_values: Any | Iterable[Any]
    :return: 消除空字段后的数据框。<br>The dataframe after eliminating empty fields.
    :rtype: pandas.DataFrame
    '''
    #参数预处理（Parameter preprocess）
    if header == None:
        header = []
    elif isinstance(header, int):
        header = [header]
    if na_values == None:
        na_values = [numpy.nan]
    elif isinstance(na_values, Iterable):
        na_values = list(na_values)
    else:
        na_values = [na_values]
    empty_values: list[Any] = [0, ""] + list(na_values)
    record_indices: list[int] = sorted(set(df.index.to_list()) - set(header))
    #筛选空列（Filter for empty columns）
    fields_to_drop: list[str] = []
    for field in df.columns:
        if all(map(lambda x: x in empty_values, df[field][record_indices])):
            fields_to_drop.append(field)
    #消除空列（Eliminate empty columns）
    return df.drop(fields_to_drop, axis = 1)

def addDefaultStyle(df: pandas.DataFrame) -> pandas.io.formats.style.Styler: #为数据框添加默认样式（Add default style for a dataframe）
    '''
    将要导出为工作表的数据框的表头和索引列添加以下样式：<br>Add the following styles for the header and index column of a dataframe to be exported as a worksheet:
    - 居中（Center)
    - 加粗（Bold)
    - 全边框（Full border)
    
    以上样式在pandas2导出时默认启用，在pandas3中默认不启用。<br>These styles are enabled by default in pandas2 but not in pandas3.
    
    :param df: 要添加默认样式的数据框。<br>A dataframe to add default style.
    :type df: pandas.DataFrame
    :return: 添加样式后的数据框。<br>A dataframe added with styles.
    :rtype: pandas.io.formats.style.Styler
    '''
    return df.style if df.empty else df.style.map_index(lambda v: "text-align:center; font-weight:bold; border: 1px solid black", axis = 0).map_index(lambda v: "text-align:center; font-weight:bold; border: 1px solid black", axis = 1)

def lcuTime(timestamp: float) -> str: #根据对局时间轴的时间戳返回对局时间（Return the time according to the timestamp in match timeline）
    '''
    将LCU API中涉及的时间戳转化为“M:(0)S”持续时长的形式。<br>Transform the timestamp in data returned by LCU API into the duration like "M:(0)S" form.
    
    :param timestamp: 时间戳，以秒为单位。<br>Timestamp in seconds.
    :type timestamp: float
    :return: 形如“M:(0)S”的字符串。<br>A string in the form "M:(0)S".
    :rtype: str
    '''
    min: float = timestamp // 60
    sec: float = timestamp % 60
    return "%d:%02d" %(min, sec)

def getISOTime(timestamp: float, tz: datetime.timezone = datetime.timezone.utc) -> str:
    '''
    将LCU API中的世界时间转化为ISO 8601的时间。<br>Transform the world timestamp in data returned by LCU API into a time string in ISO 8601 form.
    
    :param timestamp: 时间戳，以秒为单位。<br>Timestamp in seconds.
    :type timestamp: float
    :param tz: 时区。默认是UTC时间。<br>Time zone. UTC by default.
    :type tz: datetime.timezone
    :return: 形如“1970-01-01T08:00:00.0Z”的时间字符串。<br>A time string in a form like "1970-01-01T08:00:00.0Z".
    :rtype: str
    '''
    dt: datetime.datetime = datetime.datetime.fromtimestamp(timestamp, tz = datetime.timezone.utc)
    return dt.isoformat(timespec = "milliseconds").replace("+00:00", "Z")

def format_runtime(seconds: int | float) -> str: #专用于导出工作表时的进度统计（Specially used in the process counter of worksheets）
    '''
    将一段持续时长格式化为文本。<br>Format a time duration into a piece of text.
    
    :param seconds: 持续时间，以秒为单位。<br>Time duration in seconds.
    :type seconds: int | float
    :return: 结果字符串。形式为“{天数} d {小时} h {分钟} m {秒} s”。<br>Result string. In the form of "{day} d {hour} h {minute} m {second} s".
    :rtype: str
    '''
    units: list[tuple[str, int]] = [(" d", 86400), (" h", 3600), (" m", 60), (" s", 1)]
    results: list[str] = []
    for unit_name, unit_seconds in units:
        if seconds >= unit_seconds:
            unit_value: int = round(seconds // unit_seconds)
            seconds %= unit_seconds
            results.append(f"{unit_value}{unit_name}")
    return " ".join(results) if results else "0"

def write_roman(num: int) -> str: #此部分代码来自Stack Overflow（The following code come from https://stackoverflow.com/questions/28777219/basic-program-to-convert-integer-to-roman-numerals）
    '''
    一个将正整数转化为罗马数字的自定义函数。<br>A custom function that transforms an integer into a Roman number.
    
    :param num: 阿拉伯数字。<br>An arabic number.
    :type num: int
    :return: 罗马数字。<br>A roman number.
    :rtype: str
    '''
    roman: dict[int, str] = {}
    roman[1000] = "M"
    roman[900] = "CM"
    roman[500] = "D"
    roman[400] = "CD"
    roman[100] = "C"
    roman[90] = "XC"
    roman[50] = "L"
    roman[40] = "XL"
    roman[10] = "X"
    roman[9] = "IX"
    roman[5] = "V"
    roman[4] = "IV"
    roman[1] = "I"

    def roman_num(num: int) -> Generator[str]:
        '''
        罗马数字生成器。<br>Roman number generator.
        
        :param num: 阿拉伯数字。<br>An arabic number.
        :type num: int
        :return: 罗马数字生成器。<br>Roman number generator.
        :rtype: Generator[str]
        '''
        for r in roman.keys():
            x: int = divmod(num, r)[0]
            yield roman[r] * x
            num -= (r * x)
            if num <= 0:
                break

    return "".join([a for a in roman_num(num)])

def verify_uuid(s: str) -> bool:
    '''
    检查一段字符串是否符合通用唯一识别码的格式。<br>Check whether a string complies with the format of a universally unique identifier.
    
    :param s: 任意字符串。<br>Any string.
    :type s: str
    :return: 字符串是否符合通用唯一识别码的格式。<br>Whether this string follows the format of a UUID.
    :rtype: bool
    '''
    try:
        return s == str(uuid.UUID(s))
    except ValueError:
        return False

def normalize_file_name(name: str, into: str = "_", scheme: Optional[dict[str, str]] = None) -> str: #将一个文件名中的不合法字符全部替换为合法字符（Replace all illegal characters in a file name into legal characters）
    '''
    将文件名全部替换为合法字符。在指定scheme的情况下，优先使用scheme中的方案。<br>Substitute legal characters for all illegal characters in `name`. If `scheme` is specified, those illegal characters will be replaced following the scheme in `scheme`.
    
    :param name: 文件名。<br>File name.
    :type name: str
    :param into: 替换字符串。<br>A string to replace the invalid characters with.
    :type into: str
    :param scheme: 替换方案。键是非法字符，值是目标合法字符。<br>A replace scheme, whose keys are illegal characters and values are corresponding legal characters.<br>在指定scheme参数的情况下，如果文件名中的非法字符不存在于scheme字典中，那么程序将继续使用into参数进行替换。<br>If `scheme` parameter is specified but an illegal character in `name` doesn't in `scheme` dictionary, the function will use `into` for substitution instead.
    :type scheme: dict[str, str]
    :return: 标准化后的文件名。<br>Normalized file name.
    :rtype: str
    '''
    #参数预处理（Parameter preprocess）
    if scheme == None:
        scheme = {}
    result = name
    invalid_characters: set[str] = {"\\", "/", ":", "*", "?", '"', "<", ">", "|"} #在Windows中编辑文件名时尝试输入这些字符可弹出提示（A hint will pop up when someone is trying to input any of these characters while editing the name of a file on Windows）
    for char in invalid_characters:
        result = result.replace(char, scheme.get(char, into))
    return result

def pyobj2json(obj: Any, indent: Optional[int] = None, truncate: bool = False) -> Any:
    '''
    将一个Python对象转换为json字符串。<br>Transform a Python object into a json string.
    
    :param obj: Python对象。<br>A Python object.
    :type obj: Any
    :param indent: 缩进空格数。默认为无缩进。<br>Number of spaces for indentation. No indentation by default.
    :type indent: int | None
    :param truncate: 是否自动截断过长的单元格字符串。默认为假。<br>Whether to automatically cut off excessively long cell strings. False by default.
    
        过长指的是超过32767个字符数。<br>"Excessively long" means a string is longer than 32767 characters.
        
        该参数仅对转换后的json字符串有效。<br>This parameter only applies to json strings after transformation.
    :type truncate: bool
    :return: json字符串或原始对象（当obj不是list或dict时）。<br>Json string or the original object (when `obj` isn't a list or dict).
    :rtype: Any
    '''
    if isinstance(obj, (list, dict)):
        result: str = json.dumps(obj, indent = indent, ensure_ascii = False)
        return result[:32767] if truncate else result
    else:
        return obj

def capitalize(s: str) -> str: #首字母大写函数，在用于转换json中的键时尤其有用（A function to turn the first letter of a string into the upper form, especially useful during the transformation of a key in json data）
    '''
    将一个字符串的首字母变为大写形式。<br>Turn the first letter of a string into the upper form.
    
    :param s: 待处理的字符串。<br>The string to process.
    :type s: str
    :return: 首字母大写后的字符串。<br>The string after capitalizing its first letter.
    :rtype: str
    '''
    s = str(s)
    if len(s) == 0:
        return ""
    else:
        return s[0].upper() + s[1:]

def decapitalize(s: str) -> str: #首字母小写函数，在用于转换json中的键时尤其有用（A function to turn the first letter of a string into the lower form, especially useful during the transformation of a key in json data）
    '''
    将一个字符串的首字母变为小写形式。<br>Turn the first letter of a string into the lower form.
    
    :param s: 待处理的字符串。<br>The string to process.
    :type s: str
    :return: 首字母小写后的字符串。<br>The string after decapitalizing its first letter.
    :rtype: str
    '''
    s = str(s)
    if len(s) == 0:
        return ""
    else:
        return s[0].lower() + s[1:]
