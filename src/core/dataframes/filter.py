import os, pandas, sys
from typing import Callable, Optional
wd: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")).replace("\\", "/")
os.chdir(wd)
if not wd in sys.path:
    sys.path.append(wd) #确保在“src”文件夹的父级目录运行此代码（Make sure this program is run under the parent folder of the "src" folder）
from src.utils.logger import LogManager
from src.utils.format import format_df

def filter_df(queryStr: str, df_query: pandas.DataFrame, df_initial: pandas.DataFrame, search_func: Callable[[str, pandas.DataFrame], list[int]], resetStr: str = "00", fields_to_print: Optional[list[str]] = None, log: Optional[LogManager] = None) -> pandas.DataFrame:
    '''
    筛选一个数据框中包含某个关键字的记录。<br>Filter records that contain a keyword in a dataframe.
    
    :param queryStr: 检索关键字。<br>Query keyword.
    
        基于检索关键字和数据表的关系，有以下两种情况：<br>Based on the relationship between the query keyword and the dataframe, there're two cases:
        1. 通过检索关键字筛选到多条记录。此时返回筛选后的表格。<br>At least one record is found by searching for this query keyword, when this function returns filtered dataframe.
        2. 通过检索关键字未筛选到记录。此时返回重置的英雄表格。<br>No record is found by searching for this query keyword, when this function returns the initial dataframe.
    :type queryStr: str
    :param df_query: 供每次检索使用的数据表。可通过一个外部循环缩小该数据表。<br>The dataframe for each query. This dataframe may be narrowed by an external loop.
    :type df_query: pandas.DataFrame
    :param df_initial: 初始数据表。静态数据，用于重置时恢复到初始状态。<br>The initial dataframe, static data, which allows the query dataframe to be reset to the initial status.
    :type df_initial: pandas.DataFrame
    :param search_func: 检索函数，返回`df_query`中包含`queryStr`的记录的索引列表。<br>Search function, which returns a list of indices of records that contain `queryStr` in `df_query`.
    :type search_func: Callable[[str, pandas.DataFrame], list[int]]
    :param resetStr: 重置关键字。用于将当前检索的数据表重置为初始状态。默认为“00”。<br>Reset keyword. Used to reset the current query dataframe as the initial status. "00" by default.
    :type resetStr: str
    :param fields_to_print: 要打印的列。如果未指定，则打印检索数据表中的所有列。<br>Columns to print. If unspecified, the function will print all columns in the query dataframe.
    :type fields_to_print: list[str]
    :param log: 日志管理对象。如果不传入，则只使用传统的输入输出功能。<br>A LogManager object. If unspecified, the input and output works as how `input` and `output` functions work.
    :type log: LogManager
    :return: 筛选后的数据表。可用于下一次筛选，同时也可作为一个返回值，并从中得到想要的数据。<br>Filtered dataframe. It may be used for the next filter, and at the same time, it serves as a returned value, so that users can get data they want from it.
    :rtype: pandas.DataFrame
    '''
    #参数预处理（Parameter preprocess）
    if log == None:
        log = LogManager()
    logPrint = log.logPrint
    #定义常量（Define a constant）
    if fields_to_print == None:
        fields_to_print = df_query.columns.to_list()
    #处理输入（Handle input）
    if queryStr == resetStr:
        resultRows = []
    else:
        resultRows: list[int] = search_func(queryStr, df_query)
    if len(resultRows) == 0:
        if queryStr == "00":
            logPrint("已重制筛选。\nFilter conditions have been reset.")
            df_query = df_initial
        else:
            logPrint("未找到匹配的记录。请重新输入。\nNo matching record found. Please try again.")
    else:
        df_query = df_query.loc[[0] + resultRows, :]
        df_query_to_print: pandas.DataFrame = df_query.loc[:, fields_to_print]
        logPrint("已找到以下记录：\nFound the following record(s):")
        print(format_df(df_query_to_print)[0])
        log.write(format_df(df_query_to_print, width_exceed_ask = False, direct_print = False)[0] + "\n")
    return df_query
