import os, time
from typing import Any, IO, Optional

def aInput() -> str: #高级输入模式（Advanced input mode）
    '''
    在同一个输入函数中允许输入换行符。输入Ctrl-D字符以结束输入。<br>An input function that allows entering the line escape character before the result concludes. Enter Ctrl-D character to cancel the input.
    
    Ctrl-D字符在终端中形如“^D”。可通过`pyperclip.copy(chr(4))`方法来复制Ctrl-D字符。<br>Ctrl-D character looks like "^D" in the terminal. It may be obtained by `pyperclip.copy(chr(4))` command.
    
    :return: 输入的字符串。<br>The input string.
    :rtype: str
    '''
    text: str = ""
    count: int = 0
    while True:
        try:
            s: str = input()
        except EOFError: #Jupyter中只输入Ctrl-D会引发报错（A single Ctrl-D character in jupyter will trigger an exception of the input function）
            break
        if count > 0 and not s == chr(4):
            text += "\n"
        count += 1
        if s.endswith(chr(4)): #以Ctrl-D结束
            text += s[:-1]
            break
        else:
            text += s
    return text

class LogManager:
    def __init__(self, path: Optional[str] = None, mode: str = "a+", encoding: str = "utf-8", sep: str = " ", start: str = "", end: str = "\n", flush: bool = False, print_time: bool = False, write_time: bool = True, verbose: bool = True):
        '''
        :param path: 日志文件路径。默认为None。<br>The log file path. None by default.
        :type path: str | None
        :param mode: 文件读取模式。默认为增强的追加写。<br>File mode. Enhanced appending ("a+") by default.
        :type mode: str
        :param encoding: 编码。默认为utf-8以兼容中文。<br>Encoding. "utf-8" by default to be compatible with Chinese characters.
        :type encoding: str
        :param sep: 分隔符。默认为一个空格。<br>Separator. One space by default.
        :type sep: str
        :param start: 输出语句的抬头部分。相当于logging库的不同日志输出级别。<br>The header part of the print statement, which acts in a similar way to the different log output levels of `logging` library.
        :type start: str
        :param end: 输出语句的结尾字符串。默认为换行符。<br>The ending character in the print statement. A line escape character by default.
        :type end: str
        :param flush: 是否将缓存文字即刻写入文件。默认为真。<br>Whether to write cached strings into file immediately. True by default.
        :type flush: bool
        :param print_time: 是否在终端显式打印抬头时间戳。默认为假。<br>Whether to print the header timestamp to terminal explicitly. False by default.
        :type print_time: bool
        :param write_time: 是否将抬头时间戳写入日志文件。默认为真。<br>Whether to write the header timestamp into the log. True by default.
        :type write_time: bool
        :param verbose: 是否在终端中输出。默认为真。<br>Whether to print to terminal. True by default.
        :type verbose: bool
        '''
        self.file_opened: bool = False
        if isinstance(path, str):
            self.open(path, mode = mode, encoding = encoding)
        self.write_time: bool = write_time
        #以下属性仅适用于logPrint方法（The following attributes only apply to `logPrint` method）
        self.sep: str = sep
        self.start: str = start
        self.end: str = end
        self.flush: bool = flush
        self.print_time: bool = print_time
        self.verbose: bool = verbose
    
    def __repr__(self) -> str: #自我描述（Self description）
        if self.file_opened:
            return f'LogManager("{self.__log.name}")'
        else:
            return "LogManager: No file opened"
    
    def open(self, path: str, mode: str = "a+", encoding: str = "utf-8") -> None: #启用日志写入（Enable writing to log）
        '''
        创建日志文件流。<br>Create a log file stream.
        
        该方法在构建此类时指定了日志文件路径的条件下将自动调用。当然也可以先在不创建日志文件流的情况下构建类，然后再手动指定日志文件路径以创建日志文件流。<br>This method will be automatically called when the class is constructed with the log file path specified. Of course, the user may construct this class first without creating the log file steam and then manually specify the log file path to create it.
        
        :param path: 日志文件路径。<br>The log file path.
        :type path: str
        :param mode: 文件读取模式。默认为增强的追加写。<br>File mode. Enhanced appending ("a+") by default.
        :type mode: str
        :param encoding: 编码。默认为utf-8，以兼容中文。<br>Encoding. "utf-8" by default to be compatible with Chinese characters.
        :type encoding: str
        
        与传统的open函数不同，该方法不直接返回日志文件流，而是将日志文件流指定为一个私有成员。<br>What's different from the traditional `open` function is that this method doesn't return the log file stream directly. Instead, it stores that stream into a private attribute of the class.
        '''
        self.path = path
        if os.path.dirname(path) != "":
            os.makedirs(os.path.dirname(path), exist_ok = True)
        self.__log: IO[Any] = open(path, mode = mode, encoding = encoding)
        self.file_opened = True
    
    def init_io_param(self) -> None: #初始化输入输出方法的默认参数。注意这个默认参数是固定的，而不是构建函数中的默认参数（Initialize default parameters of `logInput` and `logPrint` methods. Note that the default values for those parameters are fixed, instead of taking the value of parameters of the constructor）
        '''
        将输入输出方法相关的参数初始化为某个固定值。<br>Initialize the attributes of `logInput` and `logPrint` functions as some fixed values.<br>注意，这个固定值不是用户在构建类时为默认参数指定的值。<br>Note that these values are different from the values of the default parameters specified when the user constructs this class.
        '''
        self.sep = " "
        self.startr = ""
        self.end = "\n"
        self.flush = False
        self.print_time = False
        self.write_time = True
        self.verbose = True
    
    def realpath(self) -> str: #返回完整路径（Return the complete path）
        '''
        返回日志文件的绝对路径。<br>Returns the absolute path of the log file.
        '''
        if hasattr(self, "path"):
            return os.path.realpath(self.path)
        else: #在未指定文件指针时，返回当前目录（Without file pointer specified, this function returns the current working directory）
            return os.path.realpath(os.getcwd())
    
    def logInput(self, prompt: str = "", write_time: bool = True) -> str:
        '''
        日志输入方法。<br>Log input method.
        
        :param prompt: 在用户输入前部预先打印的部分。默认为空字符串。<br>The part that is printed right before the user is going to input something. An empty string by default.
        :type prompt: str
        :param print_time: 是否在终端显式打印抬头时间戳。默认为假。<br>Whether to print the header timestamp to terminal explicitly. False by default.
        :type print_time: bool
        '''
        s: str = input(prompt)
        if self.file_opened:
            currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
            write_str: str = f"[{currentTime}]{prompt}{s}" if write_time else f"{prompt}{s}"
            print(write_str, file = self.__log)
        return s

    def logPrint(self, *values: object, sep: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, flush: Optional[bool] = None, print_time: Optional[bool] = None, write_time: Optional[bool] = None, verbose: Optional[bool] = None) -> None:
        '''
        日志输出方法。优先使用**此方法中的默认参数**，其次使用对象内相应的属性。<br>Log output method. This method will first use **the default parameters of this method**, and then use the attributes of the object of this class.
        
        :param sep: 分隔符。<br>Separator.
        :type sep: str
        :param start: 抬头部分。相当于logging库的不同日志输出级别。<br>The header part, which acts in a similar way to the different log output levels of `logging` library.
        :type start: str
        :param end: 结尾字符串。<br>The ending character.
        :type end: str
        :param flush: 是否将缓存文字即刻写入文件。<br>Whether to write cached strings into file immediately.
        :type flush: bool
        :param print_time: 是否在终端显式打印抬头时间戳。<br>Whether to print the header timestamp to terminal explicitly.
        :type print_time: bool
        :param write_time: 是否将抬头时间戳写入日志文件。<br>Whether to write the header timestamp into the log.
        :type write_time: bool
        :param verbose: 是否在终端中输出。<br>Whether to print to terminal.
        :type verbose: bool
        
        '''
        #参数预处理（Parameter preparation）
        if not isinstance(sep, str):
            sep = self.sep
        if not isinstance(start, str):
            start = self.start
        if not isinstance(end, str):
            end = self.end
        if not isinstance(flush, bool):
            flush = self.flush
        if not isinstance(print_time, bool):
            print_time = self.print_time
        if not isinstance(write_time, bool):
            write_time = self.write_time
        if not isinstance(verbose, bool):
            verbose = self.verbose
        currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
        s = sep.join(str(value) for value in values)
        print_str: str = f"[{currentTime}]{start}{s}" if print_time else f"{start}{s}"
        if verbose:
            print(print_str, end = end, flush = flush)
        if self.file_opened:
            write_str = f"[{currentTime}]{start}{s}" if write_time else f"{start}{s}"
            print(write_str, end = end, file = self.__log, flush = flush) #即使用回车字符结束，日志中也不会将光标回到行首（Even if end is carriage return, in the log file the cursor won't return to the head of the line）
    
    def write(self, s: str = "", write_time: bool = False) -> None:
        '''
        向日志文件流写入字符串。<br>Write a string into the log file iostream.
        
        如果未指定日志，则不执行任何操作。<br>If no log is specified, then nothing will happen.
        '''
        if self.file_opened:
            if write_time:
                currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
                self.__log.write(currentTime)
            self.__log.write(s)
        
    def close(self) -> None:
        '''
        关闭日志文件流。<br>Close the log file iostream.
        
        如果未指定日志，则不执行任何操作。<br>If no log is specified, then nothing will happen.
        '''
        if self.file_opened:
            self.__log.close()
            self.file_opened = False
