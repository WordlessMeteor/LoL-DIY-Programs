# LoL-DIY-Programs

----
**本程序集仅供学习和个人娱乐，不得用于其它盈利用途！**

----
> 你永远可以相信：万物皆可二维表！

本程序集基于<ins>LCU API和SGP API</ins>，主要实现**英雄联盟召唤师信息的导出**和**客户端行为的模拟**。
## 运行环境配置和基本说明
1. 本程序集全部为Python程序，需要从[Python官网中](https://www.python.org/)下载最新版本的Python（不是最新版本也可，但不要太古早～），并通过pip安装所需的库。
    - 图文示范见[大乱斗概率测试脚本宣传手册](https://zhuanlan.zhihu.com/p/2009344399239316285)的第三节的第二小节。
    - 初次安装Python，切记勾选“<ins>Add Python to PATH</ins>”选项。如果因为某些原因，系统环境变量PATH中没有Python的工作目录，可以按照如下步骤添加环境变量。
        1. 在Windows搜索框中输入`path`，单击【编辑系统环境变量】，弹出【系统属性】窗口。
        2. 单击【环境变量(N)】，弹出【环境变量】窗口。
        3. 在【用户变量】中，找到`Path`变量。双击，进入【编辑环境变量】对话框。
        4. 通过点击【新建(N)】按钮，添加3个地址。这些地址是Python的工作目录。如果已存在类似的地址，就没有必要再加了。\
            `C:\Users\[用户名]\AppData\Local\Programs\Python\Launcher\`\
            `C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\`\
            `C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\Scripts`\
            如我的Windows用户名是“<ins>19250</ins>”，使用的Python版本是<ins>3.14.3</ins>，则`PATH`中包含：\
            `C:\Users\19250\AppData\Local\Programs\Python\Launcher\`\
            `C:\Users\19250\AppData\Local\Programs\Python\Python314\`\
            `C:\Users\19250\AppData\Local\Programs\Python\Python314\Scripts\`
        5. 保险起见，可以在【系统变量】的`Path`中也添加这三个地址。
        6. 重启已经打开的<ins>命令提示符</ins>或<ins>终端</ins>，即可正常使用Python工具。如pip。
    - 安装完成并配置好环境变量后，需要使用`pip install [库名]`命令安装本程序集所需的一些Python库。在科学上网的网络环境或者指定镜像的情况下，下载Python库应当会比国内环境快很多。本程序集所需的Python库有：
        - lcu_driver
            - 本人复刻了[lcu_driver库](https://github.com/WordlessMeteor/lcu-driver/tree/master/lcu_driver)文件，以便相应的拉取请求在经过lcu_driver库的作者同意合并之前，或者被作者拒绝时，用户仍然可以下载体验本存储库的lcu_driver库文件。
            - 本人只负责**根据本程序集需要**对该存储库中的库文件进行修改，没有义务将其它GitHub用户对库文件的修改与本人对库文件的修改进行合并。不过，欢迎任何用户**基于本程序集的更新**对库文件更新提出意见和建议👏
            - 如果需要使用本人修改的lcu_driver库，请按照如下步骤进行。
                1. 打开[本人的lcu-driver存储库主页](https://github.com/WordlessMeteor/lcu-driver)。
                2. 单击<ins>绿色Code按钮</ins>，再单击<ins>DownloadZIP</ins>，下载本存储库的源代码。
                3. 将下载好的压缩包【解压到当前文件夹】。
                    - 不用担心解压完成之后会不会有一大堆文件分散在文件夹里面。从GitHub上下载的源代码应该已经放在了一个文件夹里面。
                4. 打开Python存储库的目录。
                    - 一般位于`C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\Lib\site-packages`。
                        - 如我的Windows用户名是“<ins>19250</ins>”，使用的Python版本是<ins>3.14.3</ins>，则应打开\
                        `C:\Users\19250\AppData\Local\Programs\Python\Python314\Lib\site-packages`。
                    - 如果上一条方法行不通，请先在命令行中输入`pip install lcu_driver`以安装`lcu_driver`库，再使用[Everything软件](https://www.voidtools.com/zh-cn/)搜索<ins>lcu_driver</ins>关键字，从而定位到Python存储库的位置。
                5. 在解压好的文件中找到“lcu_driver”文件夹，将其复制到上面的目录中。如果提示文件已存在，请选择覆盖。
                6. 若要恢复原始lcu_driver库文件，请先在命令行中输入`pip uninstall lcu_driver`，再输入`pip install lcu_driver`重新安装。
        - openpyxl
        - pandas
        - numpy
        - requests
        - pyperclip
        - pickle
        - urllib
        - wcwidth
        - bs4
        - keyboard
2. 为提高响应速度，请在命令行环境中，而不是Python IDLE中使用本程序集。
    - 为方便查看程序的返回信息，避免命令行一闪而过，建议先打开命令提示符（或终端），使用cd命令切换到程序集所在目录，再输入命令`python [文件名]`或`python -W ignore [文件名]`以使用某个程序。
3. 所有程序必须在登录英雄联盟客户端后运行。
4. 所有运行中的py文件均可通过Ctrl+C提前结束进程。一次不行来十次！

## 鸣谢
<table>
    <thead>
        <tr>
            <th style="text-align:center;">昵称及个人主页</th>
            <th style="text-align:center;">具体内容</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="text-align:center;"><a href="https://space.bilibili.com/3082562">XHXIAIEIN</a></td>
            <td>
                <ul>
                    <li><a href="https://github.com/XHXIAIEIN/LeagueCustomLobby">自定义房间创建脚本的例程撰写</a></li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://space.bilibili.com/14671179">Mario</a></td>
            <td>
                <ul>
                    <li>首次了解到SGP API</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://space.bilibili.com/230327779">Awesome丶ABC</a></td>
            <td>
                <ul>
                    <li>加密玩家通用唯一识别码反向解密（尚未实现）</li>
                    <li>观战服务支持</li>
                    <li>对局记录场次扩展和数据切片合并</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://github.com/Morilli">Morilli</a></td>
            <td>
                <ul>
                    <li>网络请求会话复用</li>
                    <li>多线程（尚未实现）</li>
                    <li>游戏文件提取</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;">Le poussin</td>
            <td>
                <ul>
                    <li>游戏内说明文本数值转换</li>
                    <li>hash值解析</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;">Moga</td>
            <td>
                <ul>
                    <li>游戏文件提取（<a href="https://github.com/CommunityDragon/CDTB">cdtb库</a>使用）</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://space.bilibili.com/35535774">三元君_</a></td>
            <td>
                <ul>
                    <li>说明文本和提交模式建议</li>
                </ul>
            </td>
        </tr>
    </tbody>
</table>
