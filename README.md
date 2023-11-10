请滑至最后查看该说明文档的个人翻译版！\
Please scroll to the bottom of the page to check out the translated version of README!\
以下说明仅适用于本分支。其它说明详见[原存储库的main分支下](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived/tree/main)的说明文档。\
The following explanations only apply to the current branch. For other details (installation and prospects), please visit the README in [the main branch of the original repository](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived/tree/main).
# 声明
**本程序集仅供学习和个人娱乐，不得用于其它盈利用途！**
# 程序集功能简述
本程序集支持<u>创建自定义房间（包括5v5训练模式）</u>、<u>检查可用电脑玩家和游戏模式</u>以及其它探索性功能的开发。\
关于自定义房间创建之外的脚本，请参阅第6点注意事项。
1. 本程序集现仅支持创建<u>召唤师峡谷经典模式</u>、<u>嚎哭深渊</u>和<u>训练模式</u>的自定义房间。各模式包含<u>离线版</u>、<u>在线版</u>与一个<u>简化版</u>py文件。
	- 离线版采用的电脑玩家数据为主目录下的`available-bots.xlsx`文件。因此**请勿移动任何离线版文件和该xlsx文件**。
		- 该工作簿共包含3个工作表：
			- Sheet1为训练模式中**官方允许添加**的电脑玩家信息。
			- Sheet2为训练模式中**可以添加到房间内**的电脑玩家信息。
				- 相比Sheet1，Sheet2中包含一般难度的人机对战中的所有电脑玩家信息。需要通过自定义脚本4来更新。
			- Sheet3为英雄联盟**全英雄**信息。
	- 在线版采用的电脑玩家数据为<u>官方提供的可用电脑玩家</u>。因此在<u>嚎哭深渊</u>、<u>百合与莲花的神庙</u>和<u>聚点危机</u>中，使用在线版程序无法添加电脑玩家。
	- 简化版分设于每一个模式中，仅需**双击**即可自动生成随机电脑玩家，实现大大简化开房过程的目的。
2. 本程序集还提供所有模式与电脑玩家难度设置的整合版。
	- 整合简化版提供以下功能：
		- 游戏模式选择
		- 电脑玩家自动随机生成
	- 整合版提供以下功能：
		- 队列房间循环创建
		- 自定义房间游戏模式选择
		- 游戏类型选择
		- 游戏地图选择
		- 允许观战策略选择
		- 对局名设置
		- 队伍规模选择
		- 密码（可选）设置
		- 电脑玩家难度选择\
		在该文件中可以选择是否设定电脑玩家难度一致。
		- 电脑玩家数量设置
		- 模拟客户端行为
	- 另外一个py文件允许用户在已经创建好的房间内添加电脑玩家而不覆盖原房间。仅此文件允许访问**非官方**电脑玩家数据。
	- ~~在极限闪击正式开放之前，整合版<b>不可</b>创建极限闪击房间。请尝试整合简化版或`极限闪击`下属程序。~~
3. 本程序集中的`check_available_bots.py`和`check_available_gameMode.py`分别提供检查可用电脑玩家和可用游戏模式的功能。
	- **请勿在前者运行过程中创建自定义房间**，否者可能输出重复的电脑玩家序号和错误的统计结果。
	- **请勿在后者运行过程中创建自定义房间**，否则可能输出实际不可创建的房间信息。（但可利用这一点查看当前程序的运行进度。）
	- 本程序设置了默认的检测上下限。如有需要，请自行修改上下限。
4. 本程序集中的`get_lobby_information.py`提供**反复**获取房间信息的功能。
5. 本程序集提供了离线数据资源，用于降低资源获取时间。
	- 该部分资源预期跟随版本定期更新。
	- 考虑到程序集可能在美测服运行，这里默认提供美测服的资源。
6. 本程序集起源于主目录下的`create_custom_lobby.py`。
# 注意事项
1. 本程序集全部为Python程序，需要从[Python官网中](www.python.org)下载最新版本的Python。（不是最新版本也可，但不要太古早～）
	- 初次安装Python，切记勾选`Add Python to PATH`选项。
	- 如果因为某些原因，系统环境变量PATH中没有Python的工作目录，可以按照如下步骤添加环境变量。
		1. 在Windows搜索框中输入`path`，单击`编辑系统环境变量`，弹出`系统属性`窗口。
		2. 单击`环境变量(N)`，弹出`环境变量`窗口。
		3. 在`用户变量`中，找到`Path`变量。双击，进入`编辑环境变量`对话框。
		4. 通过点击`新建(N)`按钮，添加3个地址。这些地址是Python的工作目录。如果已存在类似的地址，就没有必要再加了。\
			`C:\Users\[用户名]\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\`\
			`C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\Scripts`\
			如我的用户名是`19250`，使用的Python版本是<u>3.11.6</u>，则PATH中包含：\
			`C:\Users\19250\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python311\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python311\Scripts\`
		5. 保险起见，可以在`系统变量`的`Path`中也添加这三个地址。
		6. 重启已经打开的<u>命令提示符</u>或<u>终端</u>，即可正常使用Python工具。如pip。
	- 安装完成并配置好环境变量后，需要使用`pip install [库名]`命令安装本程序集所需的一些Python库。在科学上网的网络环境下，下载Python库应当会比国内环境快很多。本程序集所需的Python库有：
		- lcu_driver
			- 本人复刻了[lcu_driver库]文件(https://github.com/WordlessMeteor/lcu-driver/tree/master/lcu_driver)，以便相应的拉取请求在经过lcu_driver库的作者同意合并之前，或者被作者拒绝时，用户仍然可以下载体验本存储库的lcu_driver库文件。
			- 本人只负责**根据本程序集需要**对该存储库中的库文件进行修改，没有义务将其它GitHub用户对库文件的修改与本人对库文件的修改进行合并。不过，欢迎任何用户**基于本程序集的更新**对库文件更新提出意见和建议👏
			- 如果需要使用本人修改的lcu_driver库，请按照如下步骤进行。
				1. 打开[本人的lcu-driver存储库主页](https://github.com/WordlessMeteor/lcu-driver)。
				2. 单击<u>绿色Code按钮</u>，再单击<u>DownloadZIP</u>，下载本存储库的源代码。
				3. 将下载好的压缩包【解压到当前文件夹】。
					- 不用担心解压完成之后会不会有一大堆文件分散在文件夹里面。从GitHub上下载的源代码应该已经放在了一个文件夹里面。
				4. 打开Python存储库的目录。
					- 一般位于`C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\Lib\site-packages`。
						- 如我的用户名是`19250`，使用的Python版本是<u>3.11.6</u>，则应打开\
						`C:\Users\19250\AppData\Local\Programs\Python\Python311\Lib\site-packages`。
					- 如果上一条方法行不通，请先在命令行中输入`pip install lcu_driver`以安装`lcu_driver`库，再使用[Everything软件](https://www.voidtools.com/zh-cn/)搜索<u>lcu_driver</u>关键字，从而定位到Python存储库的位置。
				5. 在解压好的文件中找到`lcu_driver`文件夹，将其复制到上面的目录中。如果提示文件已存在，请选择覆盖。
				6. 若要恢复原始lcu_driver库文件，请先在命令行中输入`pip uninstall lcu_driver`，再输入`pip install lcu_driver`重新安装。
		- openpyxl
		- pandas
		- requests
		- pyperclip
		- pickle
		- urllib
		- wcwidth
2. 为提高响应速度，请在命令行环境中，而不是Python IDLE中使用本程序集。
	- 为方便查看程序的返回信息，避免命令行一闪而过，建议先打开命令提示符（或终端），使用cd命令切换到程序集所在目录，再输入命令`python [文件名]`以使用某个程序。
3. 所有程序必须在登录英雄联盟客户端后运行。
4. 本程序集所有打开的py文件均可通过Ctrl + C提前结束进程。一次不行来十次！
5. 对库文件进行的修改。注意，如果修改后无法解决问题，请**第一时间**撤销对库文件进行的修改！
	- 12.23版本以后，对lcu_driver库中的utils.py文件，将`key, value = cmdline_arg[2:].split('=')`修改为`lst = cmdline_arg[2:].split('=')`、`key = lst[0]`和`value = lst[1]`共3个语句。
6. 本程序集提供了一些自定义房间创建之外的功能，仅供娱乐。欢迎各位志同道合的小伙伴补充完善！
	- **声明：请按照顺序为后来添加的脚本命名，格式为`Customized Program [数字] - [功能].py`。**
	- 自定义脚本1**返回通过lcu_driver库获取到的连接信息**。
	- 自定义脚本2参考了Mario开发的图形化界面的LeagueLobby中**根据Json创建房间**按钮的功能。使用时，需要先在文本编辑器中修改该文件中create_custom_lobby函数中的各参数的值，保存后再双击该文件以尝试创建房间。
	（图片待完善）
		- 若要查看创建房间后的返回信息，请选择先打开命令提示符或终端再输入`python [文件名]`。
	- 自定义脚本3为**探索LCU API**提供了一个基础工具，将**格式化的**返回结果输出到同目录下的`temporary data.txt`，并将变量以**二进制**的形式保存到同目录下的`temporary data.pkl`中。该程序中列出了一些参考的网络请求命令。所有可用API来自[LCU Explorer](https://github.com/HextechDocs/lcu-explorer/releases/tag/1.2.0)。
		- 请参考示例输入。<font color=#ff0000><b>不合法的输入会导致程序直接退出。</b></font>合法的输入格式有以下要求：
			- 包含<u>一或两个</u>空格。
			- 地址（输入字符串以空格作为分隔符分隔而成的列表的第二个字符串元素）以<u>斜杠</u>开头。
		- 该程序无法发送稍微复杂一些的网络请求。如需要附带json数据的网络请求。
		- 要在网页端而不是软件端查看所有LCU API，请访问[Swagger](https://www.mingweisamuel.com/lcu-schema/tool/)。（如在浏览器中使用Ctrl + F以搜索API。）
	- 自定义脚本4用于**更新主目录下的`available-bots.xlsx`文件**。使用时，请先将结果复制粘贴到记事本中，再进行合适的整理，将其汇入已有的Excel文件中。
		- 一般情况下不需要用户自行更新英雄数据。我会保持更新。每次更新的依据是新英雄的发布。
		- 该程序允许在客户端未运行时使用。此时只能获取全英雄信息，但可以设置输出语言。
	- 自定义脚本5（☆）用于**查询和导出召唤师战绩**。
		- 该脚本支持通过<u>召唤师名称</u>和<u.玩家通用唯一识别码</u>查询。
		- 由于使用的是LCU API，在国服环境下，即使召唤师生涯**不可见**，仍然能够查询到该召唤师的全部对局记录和段位信息。
		- 该脚本获取数据所依赖的数据资源主要来自<u>CommunityDragon数据库</u>，支持**离线获取**。如果选择离线获取，<u>请按照程序提示，在主目录下新建文件夹`离线数据（Offline Data）`，打开相应资源的网页，将相应的json文件下载到该文件夹下。</u>
		- 从13.22版本开始，美测服采用**拳头ID**来替代召唤师名称。因此，如果通过召唤师名称无法查询一名召唤师的信息，**请尝试在玩家名称后加上一个“#”，再加上服务器后缀**。
			- <b>提示：</b>在客户端中打开一个召唤师的生涯界面，**将鼠标悬停在玩家名称上**，即可看到完整的带有服务器后缀的拳头ID。单击即可复制。粘贴到生涯界面右上方的搜索栏即可搜索该玩家。
		- 在选择导出全部数据的情况下，生成的Excel文件中包含五大部分：
			- 人物简介（单工作表）
			- 排位信息（单工作表）
			- 英雄成就（单工作表）
			- 对局记录（五工作表）
				- 近期一起玩过的英雄联盟玩家
				- 近期一起玩过的云顶之弈玩家
				- 英雄联盟对局记录
				- 本地重查对局记录
				- 云顶之弈对局记录
			- 各对局详细信息（至多双工作表/对局）
				- 对局信息
				- 对局时间轴
		- 在运行扫描模式（【本地重查】）之前，请先运行【一键查询】，以避免遗漏最新的对局。（要查看一些名词的含义，请看相应的提交记录描述。）
			- 不建议使用该程序导出超过2500场正常对局（或5000场斗魂竞技场对局）的信息。
			- 在运行扫描模式之前，先删除工作簿（到回收站），这样防止原有文件较大而导致程序读取文件和导出工作表的时间过长。
			- 【本地重查】目前只支持**英雄联盟**对局。
		- 每次导出一名召唤师的战绩后，如果后续有自行整理的需求，请修改相应的对局记录工作表名，以防程序下次运行时会覆盖工作表导致数据丢失。例如在工作表名后添加“ - Manual”。
		- 该程序需要依据实际遇到的报错来更新异常修复部分的代码。欢迎各位开发者分享爬取过程中遇到的报错问题👏
	- 自定义脚本6用于**在美测服一键开启云顶之弈1V0模式，以获取3000点券**。双击即可。
		- 对于非北美洲用户，即使使用了加速器，也要<u>在游戏大厅的PLAY按钮高亮3秒之后，再双击本程序</u>。否则会导致召唤师状态异常（实际为在线状态，却显示为正在排队，并有“正在匹配”的计时器）。这时只能通过<u>重启客户端</u>来解决。
		- 从2023年8月27日开始，云顶之弈1V0模式不再可用。<u>请自行进入匹配对局并秒退来获取3000点券。</u>
	- 自定义脚本7用于**获取商店中上架的商品信息**。
		- 该程序将商品信息输出到`Store items.txt`中。
	- 自定义脚本8从来没有被寄予统计一个服务器上所有召唤师的数量的厚望。（因为人实在是太多了，并且遍历是最盲目的！）
	- 自定义脚本9用于**查询和导出当前服务器存在的游戏模式**。
		- 尝试在多个服务器上运行此程序，并比较开放的游戏模式。兴许你会发现自己可以在国测服玩到卡莎打一般难度的1v1人机的云顶之弈1v0狂暴模式。
	- 自定义脚本10用于**搜索指定召唤师进行过的对局**。可以与自定义脚本5联动。
	- 自定义脚本11用于**查询与指定召唤师最近玩过的召唤师**。
		- 该脚本的大部分代码继承自自定义脚本5，包括扫描模式。但是该脚本只涉及结果的输出，不会修改自定义脚本5生成的任何中间文件（文本文档）。
		- 该脚本设置了【生成模式】和【检测模式】。
			- 该脚本不支持在一次生命周期中切换模式。
			- 【生成模式】用于将某召唤师最近若干场对局中遇到的玩家**保存到本地文件**。将保存到前缀为“Summoner Profile”的工作簿的“Recently Player Summoners”工作表中，并导出8张关于玩家的<u>游戏时长</u>和<u>对局数</u>的**柱状图**。
			- 【检测模式】用于在**英雄选择**阶段查询队友是否在以前的对局中遇到过。
				- 如有，返回该召唤师在历史对局中的信息。格式参考了自定义脚本5生成的对局记录的每一条记录。
				- 该模式**仅**支持查询**用户**在英雄选择阶段遇到的队友。不能查询其它召唤师在英雄选择阶段遇到的队友。
				- 由于英雄选择阶段具有临时性，因此在该模式下，程序只会在主目录生成一个临时文件。
				- 和查战绩脚本相同，该脚本的扫描模式只适用于查询**英雄联盟**对局。
			- 如果用户在英雄选择阶段因为某些原因（如命令行一闪而过、历史记录无法正常获取等）未能通过【检测模式】获取队友是否曾遇到过的信息，那么只能在**对局结束**后通过<u>【生成模式】</u>手动查询。
	- 自定义脚本12用于**整理战利品信息**。
		- 该脚本的最终结果是一个**包含部分字段的二维表**，保存在工作簿中。**工作簿的生成路径参照查战绩脚本**。
		- 该脚本仅作数据的转换和整理，不作任何数据分析。如有需要，<u>请自行使用Excel软件进行分析</u>。
	- `清除临时文件.bat`用于清除自定义脚本产生的临时文件。目前可以清除自定义脚本3、4、5、7和10产生的临时文件。
	- 为方便理解自定义脚本中一些大型数据框的结构，在主目录中添加了一个工作簿`Customized Program Main Dataframe Structure.xlsx`，以解释其生成过程。
		- 下面对自定义脚本11中的`recent_LoLPlayers_df`的结构进行说明，以便说明一些设定。一些设定在后续解释中不再赘述。
			- 工作表`11 - recent_LoLPlayers_header`共有5列，其中前3列是**主要数据区域**。
				- `Index`代表`LoLGame_info_data`的键的索引。
				- `Key`代表`LoLGame_info_data`的键。
				- `Value`代表`LoLGame_info_data`的值。
				- `DirectlyImport?`代表从LCU API中获取数据导入工作表中时是否需要对数据进行加工。打勾表示直接引用。
				- `OutputOrder`代表输出为工作表时各数据的排列顺序。
			- 在该工作表中，主要数据区域设置了5种颜色。
				- 绿色代表`Key`可以直接作为`LoLGame_info`的索引。
				- 黄色代表`Key`作为`LoLGame_info["participantIdentities"][participantId]`的索引。
				- 蓝色代表`Key`作为`LoLGame_info["participants"][participantId]`的索引。
				- 橙色代表`Key`作为`LoLGame_info["participants"][participantId]["stats"]`的索引。
				- 粉红色代表`Key`不作为LCU API中任何变量的索引。
					- 目前粉红色区域只包含`ally?`，表示查询的玩家是否是主玩家的队友。在导出的工作表中，打勾表示该玩家是主玩家的队友。
			- 一些键被标记为白色。这样的键不作为LCU API中任何变量的索引，但仍来自其填充色所代表的变量的索引。如`ornament`不曾出现在对局信息的json对象中，但是实际上来自`LoLGame_info["participants"][participantId]["stats"]`，对应的是索引`"item6"`。
			- 要获取各个呈现顺序列表，只需要将表格以`OutputOrder`作升序排列，然后复制`Index`列的单元格内容即可。
		- 下面对查战绩脚本中的`mastery_df`的结构进行说明。
			- 工作表`05 - mastery_header`的主要数据区域设置了一种颜色。
				- 白字只包含`champion`和`alias`，分别表示英雄的称号和名字。LCU API只提供了英雄序号。
				- 蓝色代表`Key`可以直接作为`mastery[champion_iter]`的索引。
		- 下面对查战绩脚本中的`ranked_df`的结构进行说明。
			- 工作表`05 - ranked_header`的`Key`都可作为`ranked["queues"][Id]`的索引。
			- 注意到`OutputOrder`列存在重复数据。造成这个现象的根本原因是云顶之弈狂暴模式的段位和其它排位模式的段位被记录在两个变量中，但是输出表格时期望输出在一列中，所以有一些原键的输出顺序相同。
		- 下面对查战绩脚本中的`LoLGame_info_df`的结构进行说明。
			- 工作表`05 - LoLGame_info_header`的主要数据区域设置了5种颜色。
				- 浅蓝色代表`Key`可以作为`LoLGame_info["participantIdentities"][participantId]`的索引。
				- 深蓝色代表`Key`可以作为`LoLGame_info["participantIdentities"][participantId]["player"]`的索引。
				- 绿色代表`Key`可以作为`LoLGame_info["participants"][participantId]`的索引。
				- 橙色代表`Key`可以作为`LoLGame_info["participants"][participantId]["stats"]`的索引。
				- 紫色代表`Key`可以作为`LoLGame_info["teams"][teamId]`的索引。
		- 下面对查战绩脚本中的`LoLGame_timeline_df`的结构进行说明。
			- 工作表`05 - LoLGame_timeline_header`的主要数据区域设置了4种颜色。
				- 蓝色代表`Key`可以作为`frames[frameId]`的索引。
				- 灰色代表`Key`对应的值是自动生成的，不依赖于LCU API。
				- 绿色代表`Key`来自`LoLGame_info`的一些信息。
				- 橙色代表`Key`来自`frames[frameId]["participantFrames"][participantId]`的索引。
		- 下面对查战绩脚本中的`TFTHistory_df`的结构进行说明。
			- 工作表`05 - TFTHistory_header`的主要数据区域设置了5种颜色。
				- 无填充代表`Key`不作为LCU API中任何变量的索引。
				- 天蓝色代表`Key`作为`TFTHistory[gameIndex]`的索引。
				- 绿色代表`Key`作为`TFTHistory[gameIndex]["participants"]`的索引。
				- 粉红色代表`Key`作为`TFTHistory[gameIndex]["participants"][participantId]["traits"][traitIndex]`的索引。
					- 注意到其中不包含任何可直接作为索引的键。
				- 深蓝色代表`Key`作为`TFTHistory[gameIndex]["participants"][participantId]["units"][unitIndex]`的索引。
					- 注意到其中不包含任何可直接作为索引的键。
			- 相比之下，工作表`05 - TFTGame_info_header`和工作表`05 - TFTHistory_header`只差了前面9行内容。
		- 下面对查模式脚本中的`queues_df`的结构进行说明。
			- 工作表`09 - queues_header`的主要数据区域设置了4种颜色。
				- 绿色代表`Key`可以直接作为`queues[id]`的索引。
				- 橙色代表`Key`可以作为`queues[id]["gameTypeConfig"]`的索引。
				- 蓝色代表`Key`可以作为`queues[id]["queueRewards"]`的索引。
				- 白色代表`Key`曾经存在，但后来被删除了。
		- 下面对自定义脚本11中的`recent_TFTPlayers_df`的结构进行说明。
			- 工作表`11 - recent_TFTPlayers_header`的主要数据区域设置了5种颜色。
				- 无填充代表`Key`不作为LCU API中任何变量的索引。
				- 天蓝色代表`Key`可以作为`TFTHistory[i]["json"]`的索引。
				- 绿色代表`Key`可以作为`TFTHistory[i]["json"]["participants"][participantId]`的索引。
				- 粉色代表`Key`的前半部分可以作为`TFTHistory[i]["json"]["participants"][participantId]["traits"]`的索引，后半部分可以作为`TFTHistory[i]["json"]["participants"][participantId]["traits"][int(TFTTrait_iter[5:])]`的索引。
				- 深蓝色代表`Key`的前半部分可以作为`TFTHistory[i]["json"]["participants"][participantId]["units"]`的索引。
					- 91～123之间的键的后半部分可以作为`TFTHistory[i]["json"]["participants"][participantId]["units"][int(unit_iter[4:])]`的索引。
					- 124及以后的键的后半部分可以作为`TFTHistory[i]["json"]["participants"][participantId]["units"][int(unit_iter[4:])]["items"]`的索引。
		- 下面对整理战利品脚本中的`player_loot_df`的结构进行说明。
			- 工作表`12 - player_loot_header`的主要数据区域未设置颜色，因为这些键都可作为`player_loot[i]`的索引。
7. 一般情况下，本程序集生成的包含json数据的文本文档都是带缩进的。如果需要根据这些文件复现python运行环境中的字典变量，只需要向json库中的load函数传入一个由open函数创建的文件指针即可。如`fp = open("{文件名}.txt", "r", encoding = "utf-8")`和`d = json.load(fp)`。
	- 若要在运行环境中将dumps函数生成的带缩进的json字符串转换成不带缩进的json字符串，只需要将dumps函数生成的字符串传入loads函数即可。如`formatted = json.dumps({字典变量}, indent = 8, ensure_ascii = False)`和`d = json.loads(formatted)`。
# 后记
作为初学者，我只学习到了Python的一些基本语法，还是在基于结构化程序设计的思想来实现每一个功能，而没有用到类和对象的概念，导致代码的整合程度不高，存在大量冗余的代码。例如查询召唤师战绩的脚本中，存在**大量复制**的现象。对于长字符串，我的处理方法是**一行写到底**，是基于<u>缩减代码行数</u>的考虑，可能不利于代码的浏览，还请见谅！另外，本程序集的注释尚不充足，还需要进一步完善。由于尚未学习图形化界面相关的知识（唯一学过的就是VB了😂），我只能设计这种通过命令行来实现功能的程序。（y1s1，现在并没有设计图形化界面的打算。）\
整个程序集中的程序，除了参考知乎博主XHXIAIEIN的学习心得和拳头官方公布的接口，其实没有什么创新点，主要就是一个数据的爬取和整理。如果大家有什么好玩的想法，也欢迎复刻本存储库，并创建属于你自己的分支和提交拉取请求！

---
(The following content is the English version of README.)
# Declaration
**This program set only supports study use or personal entertainment. Any commercial use is forbidden!**
# Program Set Functionality
This program set allows <u>creating custom lobbies (including 5V5 Practice Tool)</u>, <u>checking available bot players and game modes</u> and development of other exploratory functions.\
For details about customized programs that is beyond the scope of creating a custom lobby, please check the sixth instruction.
1. This program set **only** supports creating custom lobbies of <u>Summoner's Rift Classic</u>, <u>Howling Abyss</u> and <u>Practice Tool</u>. Each mode includes <u>offline-data</u> version, <u>online-data</u> version and <u>simplied</u> version.
	- The offline-data version takes `available-bots.xlsx` in the home directory as the bot player data. For its sake, **don't move any files for offline-data version (including this file)**.
		- This workbook contains 3 sheets:
			- Sheet1 contains information of bot players **officially available** in Practice Tool lobbies.
			- Sheet2 contains information of bot players that **can be added** in Practice Tool lobbies.
				- Compared with Sheet1, Sheet2 includes information of all bot players in *Co-op vs. Ai* matches of intermediate difficulty. Updates come from Customized Program 4.
			- Sheet3 contains information of **all champions** in League of Legends.
	- The online-data version takes <u>officially available bots</u> as the bot player information. Therefore, online-data version can't be used to add bot players in <u>Howling Abyss</u>, <u>Temple of Lily and Lotus</u> and <u>Convergence</u> lobbies.
	- The simplified version exists in each mode. A simple **double-click** should be able to generate bot players randomly, hence simplifying lobby creation greatly.
2. This program set also provides the consolidated version for all game modes and all levels of bot difficulity.
	- The simplified consolidated version has the following features:
		- Game mode selection
		- Random generation of bot players
	- The consolidated version has the following features:
		- Queue lobby over-creation
		- Custom game mode selection
		- Game mutator selection
		- Game map selection
		- Spectator policy selection
		- Lobby name configuration
		- Team size selection
		- Password (optional) configuration
		- Bot difficulty selection\
		By this file, the user may decide whether to set all bots' difficulty the same.
		- Bot number configuration
		- Client behavior simulation
	- Another py file allows users to add bot players to already created lobbies, instead of recreating another lobby and clearing all players. Only this file is allowed to visit **unofficial** bot player information.
	- ~~Before Nexus Blitz formally returns, the consolidated version <b>can't</b> be used to create the Nexus Blitz lobbies. Please try the simplified consolidated version or programs that belong to `Nexus Blitz` directory.~~
3. In this program set, `check_available_bots.py` and `check_available_gameMode.py` provide the functions of checking available bot players and game modes, respectively.
	- **Please don't create any custom lobby while the former program is running**, in case wrong botIDs and wrong statistics are output.
	- **Please don't create any custom lobby while the latter program is running**, in case unavailable lobbies may be output. (Neverthelss, this feature may be used to check the running process.)
	- In both programs, ranges for check have been set to some values by default. For users' own requirements, please modify the ranges.
4. In this program set, `get_lobby_information.py` allows repeatedly getting lobby information.
5. This program set provides offline data resources to save the time of preparing data.
	- The data resources will follow the patch update.
	- Considering that the program set might be used when PBE client is running, the data resources of PBE version are provided by default here.
7. The program set is adapted from `create_custom_lobby.py` in the home directory.
# Notes on Instructions
1. The whole program set is made of Python programs. Users are highly suggested to download the latest version of Python from [Python official website](www.python.org). (A version that isn't latest is also OK, but please make sure it's not too early, either [xD])
	- For this first time of installation of Python, please tick on `Add Python to PATH` option.
	- If the working directories of Python aren't present in the environment variable Path, the following steps can be adopted to add Python to Path.
		1. Type in `path` in Windows search bar and click `编辑系统环境变量`. `系统属性` window will pop up.
		2. Click `环境变量(N)` button and the `环境变量` window will occur.
		3. In `用户变量`, Find the variable `Path` and double-click it to enter the `编辑环境变量` dialog box.
		4. Add 3 addresses by clicking the `新建(N)` button. These addresses are working directories of Python. If some similar addresses already exist, there's no need to add them.\
			`C:\Users\[Username]\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\`\
			`C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\Scripts`\
			For example, my username is `19250`, and my Python version is <u>3.11.6</u>. Then the updated PATH should include \
			`C:\Users\19250\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python311\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python311\Scripts\`
		5. Basically, adding the three addresses to `Path` in `系统变量` is of no harm.
		6. Restart <u>Command Prompt</u> or <u>Terminal</u>. In that case, Python tools, e.g. pip, can be used as normal.
	- After installation and environment variable configuration of Python, use `pip install [LibraryName]` command to install required libraries for this program set. For Chinese mainland users, using proxies to ignore the GFW should accelerate the downloading stage of Python libraries. Required libraries for this program set are:
		- lcu_driver
			- I've forked [lcu_driver library](https://github.com/WordlessMeteor/lcu-driver/tree/master/lcu_driver) , so that the user can still pxperience library files in the forked repository if the corresponding pull request hasn't been accepted to merge into the official version, or has been rejected to merge, by the original author.
			- I'm only reponsible for modifying the library files in the forked repository **according to the demands of this program set**, and not obligated to merge others' changes to the library files into mine. However, any user that commented and suggested on the library update **based on the program set update** is welcome 👏
			- If you want to use my `lcu_driver` library, please follow these steps:
				1. Open [my lcu-driver repo homepage](https://github.com/WordlessMeteor/lcu-driver).
				2. Click <u>the green "Code" button</u>. Then click <u>DownloadZIP</u> to download the source code of this repository.
				3. Extract the zip file to the current folder.
					- Don't worry about the chaos after the extraction! The files should have been put in a subfolder.
				4. Open the directory where Python stores libraries.
					- Basically, the directory is at `C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\Lib\site-packages`.
						- For example, my username is `19250`, and my Python version is <u>3.11.6</u>. Then the library directory should be \
						`C:\Users\19250\AppData\Local\Programs\Python\Python311\Lib\site-packages`
					- If the last approach doesn't work, please enter the command `pip install lcu_driver` in CMD to install the original `lcu_driver` library and then search for <u>lcu_driver</u> in [Everything App](https://www.voidtools.com/en-us/) to locate to the Python library directory.
				5. Select `lcu_driver` folder in the extracted files. Copy it to the Python library directory. If files already exist, please select `Replace the files in the destination`.
				6. If you need to recover the original `lcu_driver` library, please enter `pip uninstall lcu_driver` in CMD to uninstall the modified library, and then enter `pip install lcu_driver` to reinstall the original release of the library.
		- openpyxl
		- pandas
		- requests
		- pyperclip
		- pickle
		- urllib
		- wcwidth
2. To improve the speed of reponses, please open any program in this program set by Command Prompt or Terminal, instead of Python IDLE.
	- To prevent the window from flashing quickly, it's suggested that users first open Command Prompt (or Terminal), switch to the directory of the program set using `cd` command and then open some program by `python [Filename]`. In this way, it's easy check the returned information.
3. All programs must run after the user logs in the LoL client. 
4. All opened .py files can be aborted by Ctrl + C while running. (Press for any times you want, until the program exits.)
5. Modification note on the library. **Note:** If the modification doesn't solve the problem, please redo the modification **at first**!
	- After Patch 12.23, in utils.py in lcu_driver library, substitute `key, value = cmdline_arg[2:].split('=')` with the three statements: `lst = cmdline_arg[2:].split('=')`, `key = lst[0]` and `value = lst[1]`.
6. This program set provides some functions besides creating custom lobbies, just for entertainment. Anyone willing to make supplements and perfection is welcome!
	- **Declaration: Please name the subsequent customized programs in order, following the format `Customized Program [Number] - [Function].py`.**
	- Customized Program 01 **returns the connection information by lcu_driver library**.
	- Customized Program 02 refers to the **根据Json创建房间** button in the GUI LeagueLobby software by Mario. When using, users need first modify the values of parameters in create_custom_lobby function and then double-click the file after saving the change.
	(A picture to add)
		- To check the returned lobby information after creating a lobby, please first open Command Prompt or Terminal and then type `python [Filename]`.
	- Customized Program 03 provides a basic tool for **exploration into LCU API**, which saves **formatted** returned result into `temporary data.txt` in the same directory, and also saves the variable into `temporary data.pkl` in the **binary** form in the same directory. Some reference requests are listed in this program. All available APIs are from [LCU Explorer](https://github.com/HextechDocs/lcu-explorer/releases/tag/1.2.0).
		- Please input according to the examples. <font color=#ff0000><b>Illegal input will cause the program to exit.</b></font> A legal input requires: 
			- Containing <u>one or two</u> spaces.
			- Endpoint (The second string element of the list from the input string split by space) to start with a <u>slash</u>.
		- This program isn't designed to send any complex requests. E.g. requests with json data slot.
		- To view all LCU APIs in a web instead of in an APP, please visit [swagger](https://www.mingweisamuel.com/lcu-schema/tool/). (For example, you may use Ctrl + F to search for certain API.)
	- Customized Program 04 is designed to **update `available-bots.xlsx` in the home directory**. For use, please copy the result to notepad and then sort it out to adjust to the existing xlsx file.
		- Usually users aren't needed to update the champion data. I'll keep updating it if any new champion is released.
		- This program can be run without logging into LoL client, but it only returns information of all champions. Nevertheless, users may choose the output language.
	- Customized Program 05 (☆) is designed to **search and export summoners' profile**.
		- This program supports queries based on <u>summonerName</u> and <u>puuid</u>.
		- Thanks to LCU API, even if a summoner sets its profile private, its whole match history and rank data can still be fetched.
		- The data resources for capturing data in this program are mainly from <u>CommunityDragon database</u>, and it's allowed to obtain these data resources **offline**. If the user chooses to obtain the data resources offline, <u>please create a folder named as `离线数据（Offline Data）` in the main directory, open the url of the corresponding data resources and then download them to this new folder.</u>
		- Since Patch 13.22, **Riot ID** has taken the place of summoner name. Therefore, if a summoner's information can't be visited by its summonerName, **please add a "#" and the summoner's tagLine after the gameName.**
			- **Note:** Open a summoner's profile page in the League Client. Keep the mouse cursor stay on his/her gameName. You should see a window with the complete Riot ID with the postfixxed tagLine. Click to copy it. Paste it into the search bar on the top-right corner of the page to search this summoner.
		- If all data are exported, the generated xlsx file contains 5 parts of sheets:
			- Profile (Single sheet)
			- Rank (Single sheet)
			- Champion Mastery (Single sheet)
			- Match history (Five sheets)
				- Recently played summoner (LoL)
				- Recently played summoner (TFT)
				- LoL match history
				- [Local Recheck] match history
				- TFT match history
			- Details for each match (At most two sheets for each match)
				- Game information
				- Game timeline
		- Before running the scan mode ([Local Recheck]), please run [One-Key Query] first, in case latest matches are neglected. (For the definition of some terms, check the description of corresponding commit.)
			- The user isn't advised to export the information and timelines of more than 2500 normal matches (or the information of 5000 Arena matches) using this program.
			- Right before running the scan mode, please delete the xlsx workbook (into Recycle Bin), in case the original workbook is too big for this program to quickly read and export sheets into.
			- [Local Recheck] is only supported for **LoL** matches for now.
		- Every time the program exports a summoner's profile, if you need to sort out data based on the generated result, please modify the names of the sheets that you want to make changes, in case they would be overwritten and some data would be lost. For example, you may add " - Manual" after the names of the sheets to change.
		- This program relies on any encountered errors to update the exception handling code. Welcome for any developer to share the http errors when crawling the data 👏
	- Customized Program 06 is designed to **one-key start the TFT 1v0 mode on PBE to gain 3000 RP**. A simple double-click will work.
		- For users not in North America (in terms of location), despite any accerelator used, please don't double-click this program until several seconds after the PLAY button highlights. Otherwise, the summoner status will come into an unexpected state (the client will show that the summoner is in queue and display the "Finding Match" timer, but actually it's online). A **restart** for client is the only way to solve this problem.
		- Since Aug. 27th, 2023, TFT 1V0 mode has been unavailable. <u>Please start a TFT normal game and quit the game as soon as you enter the game to acquite 3000 RP.</u>
	- Customized Program 07 is designed to **get information of items on sale in the store**.
		- This program exports information to `Store items.txt`.
	- Customized Program 08 is never expected to count the number of summoners on a server. (since the number is too large, let alone the brute-force traversal of summonerId)!
	- Customized Program 09 is designed to **search and export the existing game modes on the current server**.
		- Try running this program on multiple servers, and compare the available game modes on different servers. If lucky, you may find that on Chinese PBE server, you'll use Kai'Sa to solo with a bot player of intermediate difficulty in TFT Turbo 1v0.
	- Customized Program 10 is designed to **search for matches a specified summoner has played**. The user may combine its use with Customized Program 5.
	- Customized Program 11 is designed to **search summoners that have recently played with the specific summoner**.
		- A large part of code in this program is inherited from Customized Program 5, including the scan mode. Nevertheless, this program only outputs the result and doesn't change any intermediate files (txt files) generated by Customized Program 5.
		- This program allows [Generate Mode] and [Detect Mode].
			- Mode switch isn't supported during a life cycle of this program.
			- [Generate Mode] **saves information** of players that a specific player have played with in recent matches into the Sheet "Recently Played Summoners" **in the workbook** whose name is prefixxed with "Summoner Profile" and save 9 **bar charts** with regard to players' <u>game time</u> and <u>match counts</u>.
			- [Detect Mode] checks whether allies during **champ select** have been encountered before.
				- If any of them does, information of this summoner in past matches will be returned. The format of output refers to that of each record in the match history table generated by Customized Program 5.
				- This mode **only** supports checking allies of the **user** (current summoner). The user may not use it to check allies of other summoners in champ select.
				- Considering temporariness of champ select, this mode will only generate a temporary file in the home directory.
				- Similar to Customized Program 5, the [Scan Mode] in this program only applies for **LoL** matches.
			- If for some reason (like the CMD window pops up and disappears immediately, or the match history fails to be fetched), the user fails to get whether the allies have been encountered before using [Detect Mode], then the user must check again by <u>[Generate Mode]</u> **after the match is over**.
	- Customized Program 12 is used to **sort out player loot information**.
		- The final result of this program is a **2-dimension table including a part of the field** to be saved into a workbook. **To get the generation path, please refer to Customized Program 5.**
		- This program only transforms and sorts out data. No data analysis is involved. If you have further needs, <u>please analyze with Excel APP on your own</u>.
	- `清除临时文件.bat` is used to remove temporary files generated by customized programs. At present it can delete temporary files from customized programs 3, 4, 5, 7 and 10.
	- To let user understand the structure of the large dataframes, a workbook `Customized Program Main Dataframe Structure.xlsx` is added in the home directory to illustrate how the dataframes are organized.
		- The following is the illustration on the structure of `recent_LoLPlayers_df` in Customized Program 11, to explain some settings, which will not be repeated in the later explanation:
			- There're 5 columns in the sheet `11 - recent_LoLPlayers_header`, and the first 3 columns are the **main data area**.
				- `Index` represents the index of the keys of the dictionary variable `LoLGame_info_data`.
				- `Key` represents the keys of the dictionary variable `LoLGame_info_data`.
				- `Value` represents the values of the dictionary variable `LoLGame_info_data`.
				- `DirectlyImport?` represents whether to analyze the data being imported from LCU API into the worksheet. A tick means reference without any change.
				- `OutputOrder` represents the order to arrange the data when they're output into a worksheet.
			- 5 colors are used to divide the main data area in this sheet.
				- Data in the green area mean `Key` is the direct index of the variable `LoLGame_info`.
				- Data in the orange area mean `Key` is the index of `LoLGame_info["participantIdentities"][participantId]`.
				- Data in the blue area mean `Key` is the index of `LoLGame_info["participants"][participantId]`.
				- Data in the yellow area mean `Key` is the index of `LoLGame_info["participants"][participantId]["stats"]`.
				- Data in the purple area mean `Key` doesn't serve as the index of any variables of LCU API.
					- Currently, the purple area only contains `ally?`, a judgement whether the queried player is an ally of the main player. In the exported sheet, a tick means the queried player is the ally of the main player.
			- Some keys are colored white. These keys don't belong to the indices of any variable in LCU API, but actually come from them. For example, `ornament` never occurs in the json object of the game information, but actually originates from `LoLGame_info["participants"][participantId]["stats]` and corresponds to the key `"item6"`.
			- To obtain the statistics display order lists, all needed is to arrange the table acoording to the ascending order of `OutputOrder` and to copy the cells in `Index` column.
		- `mastery_df` in Customized Program 5:
			- 1 color is used to divide the main data area in the sheet `05 - mastery_header`.
				- Data in the blue area mean `Key` is the direct index of the variable `mastery[champion_iter]`.
				- Keys in white only include `champion` and `alias`, representing the titles and aliases of champions, respectively. Only championIds are provided in LCU API.
		- `ranked_df` in Customized Program 5:
			- `Key` in the sheet `05 - ranked_header` can all be the index of `ranked["queues"][id]`.
			- Note that redundancy exists in the `OutputOrder` column. The essential reason for this is that the tier of TFT turbo and that of other rank modes are recorded into 2 variables separately, while the two tiers are expected to be stored in a single column. Therefore, the `OutputOrder` of some keys are the same.
		- `LoLGame_info_df` in Customized Program 5:
			- 5 colors are used to divide the main data area in the sheet `05 - LoLGame_info_header`.
				- Data in the light blue area mean `Key` is the index of `LoLGame_info["participantIdentities"][participantId]`.
				- Data in the dark blue area mean `Key` is the index of `LoLGame_info["participantIdentities"][participantId]["player"]`.
				- Data in the green area mean `Key` is the index of `LoLGame_info["participants"][participantId]`.
				- Data in the orange area mean `Key` is the index of `LoLGame_info["participants"][participantId]["stats"]`.
				- Data in the purple area mean `Key` is the index of `LoLGame_info["teams"][teamId]`.
		- `LoLGame_timeline_df` in Customized Program 5:
			- 4 colors are used to divide the main data area in the sheet `05 - LoLGame_timeline_header`.
				- Data in the blue area mean `Key` is the index of `frames[frameId]`.
				- Data in the grey area mean the value corresponding to `Key` is generated automatically and isn't related to LCU API.
				- Data in the green area mean `Key` comes from `LoLGame_info`.
				- Data in the orange area mean `Key` is the index of `frames[frameId]["participantFrames"][participantId]`.
		- `TFTHistory_df` in Customized Program 5:
			- 5 colors are used to divide the main daa area in the sheet `05 - TFTHistory_df`.
				- Data not filled with any color mean `Key` doesn't serve as the index of any variables of LCU API.
				- Data in the sky blue area mean `Key` is the index of `TFTHistory[gameIndex]`.
				- Data in the green area mean `Key` is the index of `TFTHistory[gameIndex]["participants"]`.
				- Data in the purple area mean `Key` is the index of `TFTHistory[gameIndex]["traits"][traitIndex]`.
					- Note that no key in this area exists to be the direct index.
				- Data in the deep blue area mean `Key` is the index of `TFTHistory[gameIndex]["units"][unitIndex]`.
					- Note that no key in this area exists to be the direct index.
			- The only difference of the contents between the sheet `05 - TFTGame_info_header` and the sheet `05 - TFTHistory_header` is the first 9 lines.
		- `queues_df` in Customized Program 9:
			- 4 colors are used to divide the main data area in the sheet `09 - queues_header`.
				- Data in the blue area mean `Key` is the directly index of the variable `queues[id]`.
				- Data in the orange area mean `Key` is the directly index of the variable `queues[id]["gameTypeConfig"]`.
				- Data in the blue area mean `Key` is the directly index of the variable `queues[id]["queueRewards"]`.
				- Data in the white area mean `Key` once existed but was deleted later.
		- `recent_TFTPlayers_df` in Customized Program 11:
			- 5 colors are used to divide the main data area in the sheet `11 - recent_TFTPlayers_header`.
				- Data not filled with any color mean `Key` doesn't serve as the index of any variables of LCU API.
				- Data in the sky blue area mean `Key` is the index of `TFTHistory[i]["json"]`.
				- Data in the green area mea `Key` is the index of `TFTHistory[i]["json"]["participants"][participantId]`.
				- Data in the pink area mean the first half of `Key` is the index of `TFTHistory[i]["json"]["participants"][participantId]['traits"]`, while the second half is the index of `TFTHistory[i]["json"]["participants"][participantId]["traits"][int(TFTTrait_iter[5:])]`.
				- Data in the dark blue area mean the first half of `Key` is the index of `TFTHistory[i]["json"]["participants"][participantId]["units"]`.
					- The second half of `Key` whose index is between 91 and 123 is the index of `TFTHistory[i]["json"]["particiants"][participantId]["units"][int(unit_iter[4:])]`.
					- The second half of `Key` whose index is greater than 123 is the index of `TFTHistory[i]["json"]["participants"][participantId]["units"][int(unit_iter[4:])]["items"]`.
		- `player_loot_df` in Customized Program 12:
			- No color is used to divide the maun data area in the sheet `12 - player_loot_header`, because these keys are all indices of `player_loot[i]`.
7. Normally, text files generated by this program set are organized with indents. If the original dictionary variable in python runtime environment is required to recur, then simply pass a file pointer created by `open` function to the `load` function in `json` library, such as `fp = open("{filename}.txt", "r", encoding = "utf-8")` and `d = json.load(fp)`.
	- If the user wants to transform a json string with indents generated by `dumps` function into a json string without indents just in the runtime environment, he/she only needs to pass the string generated by `dumps` functin into `loads` function, such as `formatted = json.dumps({dictvariable}, indent = 8, ensure_ascii = False)` and `d = json.loads(formatted)`.
# Afterword
As a beginner in programming, I've just learned some basic usage of Python, and each function is implemented based on structured programming, without using the concepts of classes and objects, which may explain the code redundancy and low level of integration. For example, in Customized Program 5, a number of lines of codes are actually **copied** from some other part of the code. Moreover, for long strings, I choose to write them **in single lines**, considering decreasing the number of code lines, which is not friendly for a glance, and I apologize for this. In addition, I realized that more annotations are needed for the codes. Last but not least, since I haven't learned anything about GUI (the only one I've ever used is Visual Basic 😂), I'm only capable of designing programs that interact with CMD. (Actually and sadly, I haven't planned to design the graphics interface for now and in the near future.)\
To be honest, there're not any really innovative ideas besides ZhiHu Author XHXIAIEIN's perception and Riot's official API. The program set mainly crawls and sorts out data. If any interesting idea pops up in your mind, welcome to fork this repository, create your own branch and submit pull requests!