请滑至最后查看该说明文档的个人翻译版！\
Please scroll to the bottom of the page to check out the translated version of README!\
以下说明仅适用于本分支。其它说明详见[原存储库的main分支下](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived/tree/main)的说明文档。\
The following explanations only apply to the current branch. For other details (installation and prospects), please visit the README in [the main branch of the original repository](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived/tree/main).
# 声明
**本程序集仅供学习和个人娱乐，不得用于其它盈利用途！**
# 程序集功能简述
本程序集支持<ins>创建自定义房间（包括5v5训练模式）</ins>、<ins>检查可用电脑玩家和游戏模式</ins>以及其它探索性功能的开发。\
**克隆本存储库**，需要本地至少有<ins>37 GB</ins>的存储空间。如果**仅使用发行版中的压缩包**，请保证本地至少有<ins>2 GB</ins>的存储空间。\
关于自定义房间创建之外的脚本，请参阅第6点注意事项。
1. 本程序集提供所有模式与电脑玩家难度设置和路线选择的整合版。
	- 整合版采用的电脑玩家数据为主目录下的`available-bots.xlsx`文件。因此**请勿移动任何离线版文件和该xlsx文件**。
	- 整合简化版文件提供以下功能：
		- 自定义游戏模式选择
		- 电脑玩家自动随机生成
	- 整合版文件提供以下功能：
		- 队列房间循环创建
		- 自定义房间游戏模式选择
		- 游戏类型选择
		- 游戏地图选择
		- 允许观战策略选择
		- 对局名设置
		- 队伍规模选择
		- 密码（可选）设置
		- 电脑玩家路线和难度选择\
			在该文件中可以选择是否设定电脑玩家难度一致。
		- 电脑玩家数量设置
		- 模拟客户端行为
	- 电脑玩家添加脚本允许用户在已经创建好的房间内添加电脑玩家而不覆盖原房间。仅此文件允许访问**非官方**电脑玩家数据。
2. 本程序集中的`check_available_gameMode.py`提供检查可用游戏模式的功能。
	- **请勿在程序运行过程中创建自定义房间**，否则可能输出实际不可创建的房间信息。
		- 国服艾欧尼亚大区可创建自定义房间参数（游戏模式，地图序号）：
			- ("CLASSIC", 11)
			- ("CLASSIC", 12)
			- ("CLASSIC", 21)
			- ("CLASSIC", 22)
			- ("ARAM", 12)
			- ("PRACTICETOOL", 11)
			- ("TUTORIAL", 11)
			- ("TUTORIAL", 12)
			- ("TUTORIAL", 21)
			- ("TUTORIAL", 22)
			- ("GAMEMODEX", 11)
			- ("GAMEMODEX", 12)
			- ("GAMEMODEX", 21)
			- ("GAMEMODEX", 22)
	- 本程序设置了默认的检测上下限。如有需要，请自行修改上下限。
3. 本程序集中的`get_lobby_information.py`提供**反复**获取房间信息的功能。
4. 本程序集提供了离线数据资源，用于降低资源获取时间。
	- 离线数据资源包含*CommunityDragon*数据库的<ins>latest</ins>和<ins>pbe</ins>文件夹下的所有**文本文档**和*DataDragon*数据库的*dragontail存档压缩包*的<ins>data</ins>文件夹下的所有**中文和英文文件**。
		- CommunityDragon数据库的数据资源将跟随<ins>美测服的每一次调整</ins>而更新，更新周期以**天**计；DataDragon数据库的数据资源将跟随<ins>正式服的每一次停机更新</ins>而更新，更新周期以**半个月**计。
	- 离线数据文件夹下的`自动更新离线数据`脚本可简化离线数据资源更新过程。
		- 该脚本仅供开发者用于更新离线数据资源，感兴趣的用户可自行下载体验。
		- 该脚本可用于更新CommunityDragon和DataDragon数据库的数据资源。
			- 在更新CommunityDragon数据库的资源时，程序提供了2种模式。
				- 【按修改时间更新】用于反映本地数据资源和在线数据资源的**变化**。
					- 如果本地数据资源文件的**修改时间晚于**在线数据资源文件，而本地数据资源文件的**内容实际上早于**在线数据资源文件，那么这些数据资源文件**不会更新**。
					- 该模式在<ins>存储库</ins>中被设置为默认模式。输入空字符串即采用默认模式。
				- 【按程序需求更新】用于**快速**更新为程序所需要的数据资源。
					- 该模式在<ins>发行版</ins>中被设置为默认模式。输入空字符串即采用默认模式。
			- 在更新DataDragon数据库的资源时，用户需要**按照程序提示**，先下载DataDragon数据库的最新压缩包，然后解压，并提供解压的目录。
			- 在更新DataDragon数据库的资源时，程序提供了2种模式。
				- 【全局扫描】可将本地存储库中的数据资源与下载到本地的最新DataDragon存档压缩包中的数据资源进行**全面对比**，实现数据资源的同步。
					- 该模式在<ins>存储库</ins>中被设置为默认模式。输入空字符串即采用默认模式。
				- 【按程序需求更新】用于**快速**更新为程序所需要的数据资源。
					- 该模式在<ins>发行版</ins>中被设置为默认模式。输入空字符串即采用默认模式。
			- 对于联网更新的资源，**使用适当的代理**可能加速数据资源的获取。
	- 由于每次更新可能涉及的数据资源较多，GitHub无法加载变化内容。以下推荐两种查看变化内容的方式：
		1. 访问[英雄联盟版本更新存储库](https://github.com/WordlessMeteor/LoL-Patch-Change)以*在线*查看**主要**更新内容。
		2. 将[本仓库](https://github.com/WordlessMeteor/LoL-DIY-Programs)克隆到本地，并查看标题为“<ins>离线数据资源更新</ins>”的提交，以*离线*查看**完整**更新内容。
			- 克隆该存储库需要占用大约<ins>37 GB</ins>的本地空间。请保证您的磁盘有足够的空间。
			- 对于包含较多数据资源的更新的提交，本地加载仍然需要几分钟时间，请耐心等待。
5. 本程序集起源于主目录下的`create_custom_lobby.py`。
# 注意事项
1. 本程序集全部为Python程序，需要从[Python官网中](https://www.python.org/)下载最新版本的Python。（不是最新版本也可，但不要太古早～）
	- 初次安装Python，切记勾选`Add Python to PATH`选项。
	- 如果因为某些原因，系统环境变量PATH中没有Python的工作目录，可以按照如下步骤添加环境变量。
		1. 在Windows搜索框中输入`path`，单击`编辑系统环境变量`，弹出`系统属性`窗口。
		2. 单击`环境变量(N)`，弹出`环境变量`窗口。
		3. 在`用户变量`中，找到`Path`变量。双击，进入`编辑环境变量`对话框。
		4. 通过点击`新建(N)`按钮，添加3个地址。这些地址是Python的工作目录。如果已存在类似的地址，就没有必要再加了。\
			`C:\Users\[用户名]\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\`\
			`C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\Scripts`\
			如我的用户名是`19250`，使用的Python版本是<ins>3.13.3</ins>，则PATH中包含：\
			`C:\Users\19250\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python312\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python312\Scripts\`
		5. 保险起见，可以在`系统变量`的`Path`中也添加这三个地址。
		6. 重启已经打开的<ins>命令提示符</ins>或<ins>终端</ins>，即可正常使用Python工具。如pip。
	- 安装完成并配置好环境变量后，需要使用`pip install [库名]`命令安装本程序集所需的一些Python库。在科学上网的网络环境或者指定镜像的情况下，下载Python库应当会比国内环境快很多。本程序集所需的Python库有：
		- lcu_driver
			- 本人复刻了[lcu_driver库]文件(https://github.com/WordlessMeteor/lcu-driver/tree/master/lcu_driver)，以便相应的拉取请求在经过lcu_driver库的作者同意合并之前，或者被作者拒绝时，用户仍然可以下载体验本存储库的lcu_driver库文件。
			- 本人只负责**根据本程序集需要**对该存储库中的库文件进行修改，没有义务将其它GitHub用户对库文件的修改与本人对库文件的修改进行合并。不过，欢迎任何用户**基于本程序集的更新**对库文件更新提出意见和建议👏
			- 如果需要使用本人修改的lcu_driver库，请按照如下步骤进行。
				1. 打开[本人的lcu-driver存储库主页](https://github.com/WordlessMeteor/lcu-driver)。
				2. 单击<ins>绿色Code按钮</ins>，再单击<ins>DownloadZIP</ins>，下载本存储库的源代码。
				3. 将下载好的压缩包【解压到当前文件夹】。
					- 不用担心解压完成之后会不会有一大堆文件分散在文件夹里面。从GitHub上下载的源代码应该已经放在了一个文件夹里面。
				4. 打开Python存储库的目录。
					- 一般位于`C:\Users\[用户名]\AppData\Local\Programs\Python\Python[版本号]\Lib\site-packages`。
						- 如我的用户名是`19250`，使用的Python版本是<ins>3.13.3</ins>，则应打开\
						`C:\Users\19250\AppData\Local\Programs\Python\Python312\Lib\site-packages`。
					- 如果上一条方法行不通，请先在命令行中输入`pip install lcu_driver`以安装`lcu_driver`库，再使用[Everything软件](https://www.voidtools.com/zh-cn/)搜索<ins>lcu_driver</ins>关键字，从而定位到Python存储库的位置。
				5. 在解压好的文件中找到`lcu_driver`文件夹，将其复制到上面的目录中。如果提示文件已存在，请选择覆盖。
				6. 若要恢复原始lcu_driver库文件，请先在命令行中输入`pip uninstall lcu_driver`，再输入`pip install lcu_driver`重新安装。
		- openpyxl
		- pandas
		- requests
		- pyperclip
		- pickle
		- urllib
		- wcwidth
		- bs4
2. 为提高响应速度，请在命令行环境中，而不是Python IDLE中使用本程序集。
	- 为方便查看程序的返回信息，避免命令行一闪而过，建议先打开命令提示符（或终端），使用cd命令切换到程序集所在目录，再输入命令`python [文件名]`或`python -W ignore [文件名]`以使用某个程序。
3. 所有程序必须在登录英雄联盟客户端后运行。
4. 本程序集所有打开的py文件均可通过Ctrl + C提前结束进程。一次不行来十次！
5. 本程序集提供了一些自定义房间创建之外的功能，仅供娱乐。欢迎各位志同道合的小伙伴补充完善！
	- **声明：请按照顺序为后来添加的脚本命名，格式为`Customized Program [数字] - [功能].py`。**
	- 自定义脚本1**返回通过lcu_driver库获取到的连接信息**。
	- 自定义脚本2参考了Mario开发的图形化界面的LeagueLobby中**根据Json创建房间**按钮的功能。使用时，需要先在文本编辑器中修改该文件中create_custom_lobby函数中的各参数的值，保存后再双击该文件以尝试创建房间。
		- 若要查看创建房间后的返回信息，请选择先打开命令提示符或终端再输入`python [文件名]`或`python -W ignore [文件名]`。
	- 自定义脚本3为**探索LCU API**提供了一个基础工具，将**格式化的**返回结果输出到同目录下的`temporary data.txt`，并将变量以**二进制**的形式保存到同目录下的`temporary data.pkl`中。该程序中列出了一些参考的网络请求命令。所有可用API来自[LCU Explorer](https://github.com/HextechDocs/lcu-explorer/releases/tag/1.2.0)。
		- 请参考示例输入。<font color=#ff0000><b>不合法的输入会导致程序直接退出。</b></font>合法的输入格式有以下要求：
			- 包含<ins>一或两个</ins>空格。
				- 包含两个空格时，用户可以传入请求主体。
			- 地址（输入字符串以空格作为分隔符分隔而成的列表的第二个字符串元素）以<ins>斜杠</ins>开头。
		- 要在网页端而不是软件端查看所有LCU API，请访问[Swagger](https://www.mingweisamuel.com/lcu-schema/tool/)或[LCU Swagger UI](https://swagger.dysolix.dev/lcu/)。（如在浏览器中使用Ctrl + F以搜索API。）
	- 自定义脚本4用于**更新主目录下的`available-bots.xlsx`文件**。
		- 该工作簿包含3个工作表：
			- Sheet1为训练模式中**官方允许添加**的电脑玩家信息。
			- Sheet2为训练模式中**可以添加到房间内**的电脑玩家信息。
				- 相比Sheet1，Sheet2中包含一般级难度的*人机对战*中的所有电脑玩家信息。
			- Sheet3为英雄联盟**全英雄**信息。
		- 一般情况下不需要用户自行更新英雄数据。我会保持更新。每次更新的依据是新英雄的发布。
		- 该程序允许在客户端未运行时使用。此时只能获取全英雄信息。
		- 该程序涉及以下数据资源：
			- https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/{语言}/v1/champions/{英雄序号}.json
			- https://ddragon.leagueoflegends.com/cdn/{版本}/data/{语言}/champion.json
	- 自定义脚本5（☆）用于**查询和导出召唤师战绩**。
		- 该脚本支持通过<ins>召唤师名称</ins>和<ins>玩家通用唯一识别码</ins>查询。
		- 由于使用的是LCU API，在国服环境下，即使召唤师生涯**不可见**，仍然能够查询到该召唤师的全部对局记录和段位信息。
		- 该脚本设置了一些命令行参数。通过`python [文件名] -h`命令以查看这些参数。
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">命令行参数</th>
						<th style="text-align:center;">行为类型</th>
						<th style="text-align:center;">描述</th>
						<th style="text-align:center;">取值</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">-r<br>--reserve</td>
						<td style="text-align:center;">赋值为真</td>
						<td>在对局不包含主玩家的情况下仍然加载该对局</td>
						<td>无</td>
					</tr>
					<tr>
						<td style="text-align:center;">-rt<br>--reserve_text</td>
						<td style="text-align:center;">赋值为真</td>
						<td>在对局不包含主玩家的情况下仍然保存该对局</td>
						<td>无</td>
					</tr>
				</tbody>
			</table>
		- 该脚本生成的文件位于主目录下的“召唤师信息（Summoner Information）”文件夹下。
		- 该脚本所依赖的数据资源主要来自<ins>CommunityDragon数据库</ins>，支持**离线获取**。发行版中已经包含所有自定义脚本依赖的最新数据资源文件。如果没有这些文件，在离线获取时，<ins>请按照程序提示，在主目录下新建文件夹`离线数据（Offline Data）`，打开相应资源的网页，将相应的json文件下载到该文件夹下。</ins>
		- 从13.22版本开始，美测服采用**拳头ID**来替代召唤师名称。因此，如果通过召唤师名称无法查询一名召唤师的信息，**请尝试在玩家昵称后加上一个“#”，再加上昵称编号**。
			- <b>提示：</b>在客户端中打开一个召唤师的生涯界面，**将鼠标悬停在玩家昵称上**，即可看到完整的带有昵称编号的拳头ID。单击即可复制。粘贴到生涯界面右上方的搜索栏即可搜索该玩家。
		- 该脚本支持以下保存模式：
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">保存模式</th>
						<th style="text-align:center;">定义</th>
						<th style="text-align:center;">适用产品</th>
						<th style="text-align:center;">实现步骤</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">完全保存</td>
						<td>保存所有的对局信息和时间轴文本文档，并导出所有对局工作表</td>
						<td style="text-align:center;">英雄联盟<br>云顶之弈</td>
						<td>英雄联盟：<br>1. “是否查询英雄联盟对局记录”，<b>输入任意非空字符串</b>以选择是<br>2. <b>输入“3”</b>以批量查询全部对局<br>3. <b>输入任意非空字符串</b>以自行指定对局索引上下限<br>4. 在设置需要查询的对局索引上下界时<b>直接按回车</b><br>5. <b>直接按回车</b>以输出每场对局的文本文档<br>6. 在计算每场对局要保存的工作表数量后，<b>输入任意非空字符串</b>以导出所有对局工作表<br>云顶之弈：<br>1. “是否查询云顶之弈对局记录”，<b>输入任意非空字符串</b>以选择是<br>2. <b>直接按回车</b>以输出每场对局的文本文档<br>3. <b>输入任意非空字符串</b>以重新保存所有对局的文本文档<br>4. 在计算每场对局要保存的工作表数量后，<b>输入任意非空字符串</b>以导出所有对局工作表</td>
					</tr>
					<tr>
						<td style="text-align:center;">完全加载</td>
						<td>在不保存任何对局信息和时间轴文本文档的情况下，导出所有对局工作表</td>
						<td style="text-align:center;">英雄联盟<br>云顶之弈</td>
						<td>英雄联盟：<br>5. <b>输入任意非空字符串</b>以不输出每场对局的文本文档<br>其余步骤与【完全保存】相同<br>云顶之弈：<br>1. “是否查询云顶之弈对局记录”，<b>输入任意非空字符串</b>以选择是<br>2. <b>输入任意非空字符串</b>以不输出每场对局的文本文档<br>3. 在计算每场对局要保存的工作表数量后，输入<b>任意非空字符串</b>以导出所有对局工作表</td>
					</tr>
					<tr>
						<td style="text-align:center;">批量保存</td>
						<td>保存指定的上下界范围内的API中记录的对局信息和时间轴文本文档，并导出所有对局工作表</td>
						<td style="text-align:center;">英雄联盟</td>
						<td>英雄联盟：<br>1. “是否查询英雄联盟对局记录”，<b>输入任意非空字符串</b>以选择是<br>2. <b>输入“3”</b>以批量查询全部对局<br>3. <b>输入任意非空字符串</b>以自行指定对局索引上下限<br>4. 在设置需要查询的对局索引上下界时<b>输入空格分隔的两个自然数</b><br>5. <b>直接按回车</b>以输出每场对局的文本文档<br>6. 在计算每场对局要保存的工作表数量后，<b>输入任意非空字符串</b>以导出所有对局工作表</td>
					</tr>
					<tr>
						<td style="text-align:center;">批量加载</td>
						<td>在不保存指定的上下界范围内的API中记录的对局信息和时间轴文本文档的情况下，导出所有对局工作表</td>
						<td style="text-align:center;">英雄联盟</td>
						<td>英雄联盟：<br>5. <b>输入任意非空字符串</b>以不输出每场对局的文本文档<br>其余步骤与【批量保存】相同</td>
					</tr>
					<tr>
						<td style="text-align:center;">增补保存</td>
						<td>保存本地未保存文本文档的对局的信息和时间轴文本文档，并导出这些对局的工作表</td>
						<td style="text-align:center;">英雄联盟<br>云顶之弈</td>
						<td>英雄联盟：<br>1. “是否查询英雄联盟对局记录”，<b>输入任意非空字符串</b>以选择是<br>2. <b>输入“3”</b>以批量查询全部对局<br>3. <b>直接按回车</b>以只查询未保存过文本文档的对局<br>4. <b>直接按回车</b>以输出每场对局的文本文档<br>5. 在计算每场对局要保存的工作表数量后，<b>输入任意非空字符串</b>以导出所有对局工作表<br>云顶之弈：<br>3. <b>直接按回车</b>以只保存尚未保存过文本文档的对局<br>其余步骤与【完全保存】相同</td>
					</tr>
					<tr>
						<td style="text-align:center;">增补加载</td>
						<td>在不保存任何本地未保存文本文档的对局的信息和时间轴文本文档的情况下，导出这些对局的工作表</td>
						<td style="text-align:center;">英雄联盟</td>
						<td>4. <b>输入任意非空字符串</b>以输出每场对局的文本文档<br>其余步骤与【增补保存】相同</td>
					</tr>
					<tr>
						<td style="text-align:center;">列表保存</td>
						<td>按照一个对局序号列表保存对局信息和时间轴文本文档，并导出这些对局的工作表</td>
						<td style="text-align:center;">英雄联盟</td>
						<td>1. “是否查询英雄联盟对局记录”，<b>输入任意非空字符串</b>以选择是<br>2. <b>输入一个由中括号包围、由半角逗号分隔的正整数列表</b>作为对局序号列表<br>3. <b>直接按回车</b>以输出每场对局的文本文档<br>4. 在计算每场对局要保存的工作表数量后，<b>输入任意非空字符串</b>以导出所有对局工作表</td>
					</tr>
					<tr>
						<td style="text-align:center;">列表加载</td>
						<td>在不保存某个给定对局序号列表中的任何对局的信息和时间轴文本文档的情况下，导出这些对局的工作表</td>
						<td style="text-align:center;">英雄联盟</td>
						<td>3. <b>输入任意非空字符串</b>以不输出每场对局的文本文档<br>其余步骤与【列表保存】相同</td>
					</tr>
					<tr>
						<td style="text-align:center;">扫描保存</td>
						<td>扫描本地已保存的所有对局，重新查询这些对局的信息和时间轴，保存其文本文档并导出其工作表</td>
						<td style="text-align:center;">英雄联盟</td>
						<td>1. “是否查询英雄联盟对局记录”，<b>输入任意非空字符串</b>以选择是<br>2. <b>输入隐藏代码“scan”</b>以扫描本地文件，获取对局序号<br>3. <b>直接按回车</b>以开始对局记录重查，或者<b>输入任意非空字符串</b>以返回第2步<br>4. <b>直接按回车</b>以输出每场对局的文本文档<br>5. 在计算每场对局要保存的工作表数量后，<b>输入任意非空字符串</b>以导出所有对局工作表</td>
					</tr>
					<tr>
						<td style="text-align:center;">扫描加载</td>
						<td>扫描本地已保存的所有对局，重新查询这些对局的信息和时间轴，在不保存其文本文档情况下，导出其工作表</td>
						<td style="text-align:center;">英雄联盟</td>
						<td>4. <b>输入任意非空字符串</b>以不输出每场对局的文本文档<br>其余步骤与【扫描保存】相同</td>
					</tr>
				</tbody>
			</table>
			<b>注：</b>【扫描保存】和【扫描加载】统称【扫描模式】或【本地重查】。
		- 在选择【完全保存】模式的情况下，生成的Excel文件中包含五大部分：
			- 人物简介（单工作表）
			- 排位信息（单工作表）
			- 战区天梯（单工作表）
			- 英雄成就（单工作表）
			- 对局记录（五工作表）
				- 近期一起玩过的英雄联盟玩家
				- 近期一起玩过的云顶之弈玩家
				- 英雄联盟对局记录
				- 本地重查对局记录
				- 云顶之弈对局记录
			- 各对局详细信息（至多三工作表/对局）
				- 对局信息
				- 对局时间轴
				- 对局事件
		- 扫描模式（【本地重查】）说明：（要查看一些名词的含义，请看[相应的提交记录](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived/commit/dc1cfd187caa619a80f70001d89f7f9c5db1892a)描述。）
			- 不建议使用该程序导出超过1600场正常对局（或5000场斗魂竞技场对局）的信息。
			- 在运行扫描模式之前，**先删除工作簿（到回收站）或重命名工作簿**，这样防止原有文件较大而导致程序读取文件和导出工作表的时间过长。
			- 【本地重查】目前只支持**英雄联盟**对局。
		- 每次导出一名召唤师的战绩后，如果后续有自行整理的需求，请修改相应的对局记录工作表名，以防程序下次运行时会覆盖工作表导致数据丢失。例如在工作表名后添加“ - Manual”。
		- 如果原工作簿较大，建议先备份原工作簿，再导出数据，以免导出过程因意外中断导致工作簿损坏。
		- 该程序涉及以下数据资源：
			- https://ddragon.leagueoflegends.com/api/versions.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/summoner-spells.json
            - https://raw.communitydragon.org/{版本}/cdragon/tft/{语言}.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/champion-summary.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/cherry-augments.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/items.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/perks.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/perkstyles.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/tftchampions.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/tftitems.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/companions.json
            - https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/tfttraits.json
		- 该程序需要依据实际遇到的报错来更新异常修复部分的代码。欢迎各位开发者分享爬取过程中遇到的报错问题👏
	- 自定义脚本6用于**在美测服一键开启云顶之弈发条鸟的试炼模式，以获取3000点券**。双击即可。
		- 从2023年8月27日开始，云顶之弈1V0模式不再可用。
	- 自定义脚本7用于**获取商店中上架的商品信息和主召唤师的藏品信息**。
		- 该程序将商品和藏品信息输出到主召唤师文件夹下的`Store and Collections - {召唤师名称}.xlsx`中。
		- 商品信息中的缩略图路径是与**LCU API**相关的网址，需要在**英雄联盟客户端启动**的情况下才能打开。初次打开网站需要输入用户名和密码，请在该脚本的输出的最开始部分找到<ins>带有“riot”的一行</ins>，用户名为<ins>“riot”</ins>，密码为<ins>“riot”后面的一串字符串</ins>。
			- 缩略图路径标为<ins>default.png</ins>的商品的缩略图尚未找到。
		- 该程序涉及以下数据资源：
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/companions.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/skins.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/statstones.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/summoner-emotes.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/summoner-icons.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/tftdamageskins.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/tftmapskins.json
			- https://raw.communitydragon.org/{版本}/plugins/rcp-be-lol-game-data/global/{语言}/v1/ward-skins.json
	- 自定义脚本8从来没有被寄予统计一个服务器上所有召唤师的数量的厚望。（因为人实在是太多了，并且遍历是最盲目的！）
	- 自定义脚本9用于**查询和导出当前服务器存在的游戏模式**。
		- 尝试在多个服务器上运行此程序，并比较开放的游戏模式。兴许你会发现自己可以在国测服玩到卡莎打一般难度的1v1人机的云顶之弈1v0狂暴模式。
	- 自定义脚本10用于**搜索指定召唤师进行过的对局**。可以与自定义脚本5联动。
	- 自定义脚本11用于**查询与指定召唤师最近玩过的召唤师**。
		- 该脚本的大部分代码继承自自定义脚本5，包括扫描模式。但是该脚本只涉及结果的输出，不会修改自定义脚本5生成的任何中间文件（文本文档和json文件）。
		- 该脚本设置了一些命令行参数。通过`python [文件名] -h`命令以查看这些参数。
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">命令行参数</th>
						<th style="text-align:center;">行为类型</th>
						<th style="text-align:center;">描述</th>
						<th style="text-align:center;">取值</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">-r<br>--reserve</td>
						<td style="text-align:center;">赋值为真</td>
						<td>在对局不包含主玩家的情况下仍然加载该对局</td>
						<td>无</td>
					</tr>
					<tr>
						<td style="text-align:center;">-ss<br>--save_self</td>
						<td style="text-align:center;">赋值为真</td>
						<td>在对局包含主玩家的情况下仍然保存其数据</td>
						<td>无</td>
					</tr>
				</tbody>
			</table>
		- 该脚本设置了【生成模式】和【检测模式】。
			- 【生成模式】用于将某召唤师最近若干场对局中遇到的玩家**保存到本地文件**。将保存到前缀为“Summoner Profile”的工作簿的“Recently Player Summoners”工作表中，并导出8张关于玩家的<ins>游戏时长</ins>和<ins>对局数</ins>的**柱状图**。
			- 【检测模式】用于查询玩家是否在以前的对局中遇到过。该脚本考虑了6种检测场景。不同场景的主体代码**类似**。
				1. 房间内/英雄选择阶段/游戏中
					- 该场景返回<ins>**主召唤师**在房间内、英雄选择阶段和游戏中遇到的召唤师</ins>在历史对局中的信息。格式参考了自定义脚本5生成的对局信息的每一条记录。
					- 该场景目前支持查询用户自己和英雄选择阶段、游戏中遇到的其它玩家的近期一起玩过的玩家。
						- <b>注意：</b>云顶之弈对局也是有英雄选择阶段的！只不过持续时间太短了。
					- 由于英雄选择阶段和游戏中具有临时性，因此在该模式下，程序只会在主目录生成一个临时文件。
					- 该场景在主目录下产生临时文件“Recently Played Summoners in Match {platformId}-{gameId}.xlsx”，{platformId}代表服务器代号，{gameId}代表对局序号。
				2. 好友列表
					- 该场景返回<ins>好友</ins>在历史对局中的信息。
					- 该场景在主目录下产生临时文件“Recently Played Summoners in Friend List of {current_summonerName} - {platformId}.xlsx”，{current_summonerName}代表主召唤师名，{platformId}代表服务器代号。
				3. 好友请求
					- 该场景返回<ins>用户想要添加为好友的玩家和想要添加用户为好友的玩家</ins>在历史对局中的信息。
					- 该场景在主目录下产生临时文件“Recently Played Summoners in Friend Requests of {current_summonerName} - {platformId}.xlsx”，{current_summonerName}代表主召唤师名，{platformId}代表服务器代号。
						- 相比其它场景，该场景的工作表名中包含了好友关系方向的信息。其中，in表示该玩家想要加用户为好友。out则相反。
				4. 组队邀请
					- 该场景返回<ins>向用户发起组队邀请者和用户发起组队邀请的对象</ins>在历史对局中的信息。
					- 该场景在主目录下产生临时文件“Recently Played Summoners in Invitations to and from {current_summonerName} - {platformId}.xlsx”，{current_summonerName}代表主召唤师名，{platformId}代表服务器代号。
						- 相比其它场景，该场景的工作表名中包含了邀请方向的信息。其中，in表示该玩家向用户发起组队邀请。out则相反。
				5. 聊天黑名单
					- 该场景返回<ins>被用户拉黑的玩家</ins>在历史对局中的信息。
					- 该场景在主目录下产生临时文件“Recently Played Summoners in Block List of {current_summonerName} - {platformId}.xlsx”，{current_summonerName}代表主召唤师名，{platformId}代表服务器代号。
				6. 任意玩家列表
					- 该场景返回<ins>用户输入的玩家列表中的所有玩家</ins>在历史对局中的信息。
						- 玩家列表的每个元素可以是<ins>召唤师名</ins>或者<ins>玩家通用唯一识别码</ins>。
					- 该场景在主目录下产生临时文件“Recently Played Summoners in Specified Player List.xlsx”。
			- 在【检测模式】下，该脚本支持启用【小号模式】，允许用户添加同一个服务器上的其它账号。
			- 和查战绩脚本相同，该脚本的扫描模式只适用于查询**英雄联盟**对局。
			- 如果用户在英雄选择阶段因为某些原因（如命令行一闪而过、历史记录无法正常获取等）未能通过【检测模式】获取队友是否曾遇到过的信息，那么在游戏中还可以通过【单独查询】手动输入对局中的召唤师名称来检查曾经遇到过的玩家。
				- 自美测服13.22版本，对于拳头代理的服务器上的玩家，只输入玩家昵称无法正常查询其信息。由于加载资源界面只呈现玩家昵称，这时可以**等待游戏开始**后在**计分板**中查看玩家昵称及其昵称编号。
		- 该程序涉及的数据资源与查战绩脚本相同。
	- 自定义脚本12用于**整理战利品信息**。
		- 该脚本的最终结果是一个**包含部分字段的二维表**，保存在工作簿中。**工作簿的生成路径参照查战绩脚本**。
		- 该脚本仅作数据的转换和整理，不作任何数据分析。如有需要，<ins>请自行使用Excel软件进行分析</ins>。
	- 自定义脚本13用于**爬取当前服务器的所有天梯数据**。
		- 该脚本生成的文件位于主目录下的<ins>“顶尖排位玩家（Ranked Apex）”</ins>文件夹下。
		- 该脚本生成的Excel文件中包含两大部分：
			- 赛季信息（双工作表）
				- 赛季信息
				- 赛季奖励进度追踪
			- 天梯信息
				- 胜点系列天梯元数据（单工作表）
				- 天梯数据
					- 胜点系列天梯数据
						- 单人/双人
						- 灵活 5v5
						- 云顶之弈
						- 双人作战（beta测试）
					- 排名分系列天梯数据
						- 狂暴模式
						- 斗魂竞技场
	- 自定义脚本14用于**秒进好友小队**。
		- 程序已添加使用限制。<b>请勿滥用和篡改代码。</b>
		- 这个脚本可能并没有想象中那么好用。如果你实在想上车，建议运行脚本的同时鼠标也狂点“加入小队”按钮即将出现的地方。
	- 自定义脚本15用于**玩家在自定义对局中选择相同的英雄**。该问题目前已被修复，因此你可以无视这个脚本。
	- 自定义脚本16用于**模拟英雄联盟客户端中与聊天服务相关的行为**。
		- 目前该脚本提供以下功能：
			- 导出好友数据
			- 管理好友分组
			- 聊天
			- 导出聊天记录
			- 管理好友列表
			- 发送组队邀请
			- 管理组队邀请
			- 观战
			- 管理小队语音
			- 管理黑名单
				- 黑名单操作中植入了自定义无限火力专用模式，用于群成员管理。该模式作为隐藏功能。
	- 自定义脚本17用于**整理所有游戏类型信息**。主要用于自定义房间创建请求的参数设置。
	- 自定义脚本18用于**梳理所有任务信息**。
		- 你可以用这个脚本来查看<ins>美测服点券任务</ins>。
	- 自定义脚本19用于**模拟客户端中符文配置和符文页操作**。
		- 目前该脚本提供以下功能：
			- 查看所有符文信息
			- 查看不同英雄、分路和地图的推荐符文
			- 符文页管理
				- 导出所有符文页
				- 单符文页查看、编辑和导出
				- 切换活动符文页
				- 排序符文页
				- 删除符文页
	- 自定义脚本20用于**批量汇总玩家战绩**。
		- 该脚本综合了查战绩脚本的查询功能和自定义脚本11的游戏状态检测功能，汇总了以下场景的玩家战绩：
			- 英雄选择阶段信息可见的队友
			- 游戏内的所有玩家
			- 已经结束的对局内的所有玩家
		- 该脚本在输出基本数据的同时，也会输出一些统计指标，参考了以下内容：
			- 掌上英雄联盟的雷达图指标
			- 电子竞技常用指标（战损比、参团率、分均经济、分均补刀、伤害转化率等）
		- 该脚本为特定格式的数据添加了条件格式，以提升直观性。
			- 战损比按照一位小数格式输出。
			- 部分电子竞技统计指标按照三位小数格式输出。
			- 占比数据按照两位小数的百分比格式输出。
			- 位次数据设置了三色刻度。
			- 胜负结果通过公式确定着色。“胜利”设置为绿色，“失败”设置为红色。
		- 为了简化使用步骤，该脚本设置了一些命令行参数。通过`python [文件名] -h`命令以查看这些参数。
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">命令行参数</th>
						<th style="text-align:center;">行为类型</th>
						<th style="text-align:center;">描述</th>
						<th style="text-align:center;">取值</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">-e<br>--save_early</td>
						<td style="text-align:center;">赋值为真</td>
						<td>只导出早于查询对局的对局</td>
						<td>无</td>
					</tr>
					<tr>
						<td style="text-align:center;">-l<br>--locale</td>
						<td style="text-align:center;">存储变量</td>
						<td>设置程序内定义的常量字典的语言。目前仅支持简体中文和美式英语</td>
						<td>zh_CN（默认）<br>en_US</td>
					</tr>
					<tr>
						<td style="text-align:center;">-os<br>--open_after_save</td>
						<td style="text-align:center;">赋值为真</td>
						<td>在成功保存文件后打开文件，不需要程序询问</td>
						<td>无</td>
					</tr>
					<tr>
						<td style="text-align:center;">--verbose</td>
						<td style="text-align:center;">赋值为真</td>
						<td>输出详细的对局加载进度和异常处理过程性提示</td>
						<td>无</td>
					</tr>
					<tr>
						<td style="text-align:center;">--nonverbose</td>
						<td style="text-align:center;">赋值为真</td>
						<td>只输出关键信息</td>
						<td>无</td>
					</tr>
				</tbody>
			</table>
	- 自定义脚本21用于**模拟客户端中各个游戏状态下的操作**。旨在解决客户端无法正常响应时的燃眉之急。
		- <b>声明：该脚本不涉及任何自动化操作。</b>
		- 该脚本融合了前20个脚本的部分核心行为。如果想要体验完整功能，请确保<ins>自定义脚本19</ins>也在同目录下。
		- 该脚本支持<ins>未登录、无状态、房间内、队列中、就位确认、英雄选择阶段、游戏内、重连状态、等待数据、赛后预结算和赛后结算阶段</ins>等状态的行为模拟。调试功能以外的所有支持的操作如下：（多次出现的操作只在第一次出现时展开其下级操作。）
			- 未登录
				- 调试客户端接口
				- 客户端任务管理
					- 窗口管理
						- 显示窗口
						- 最小化窗口
						- 显示高亮通知
						- 设置窗口尺寸
					- 进程管理
						- 启动用户体验界面
						- 暂时关闭窗口
						- 重新加载窗口
						- 结束进程（！）
			- 无状态
				- 调试客户端接口
				- 创建房间
					- 创建小队
					- 创建自定义房间
					- 通过json创建
				- 处理邀请
				- 加入小队或自定义房间
					- 小队
					- 自定义房间
					- 冠军杯赛
				- 观战
				- 聊天
				- 客户端任务管理
			- 房间内
				- 调试客户端接口
				- 管理小队
					- 入队准备
						- 选择位置（仅排位赛和极限闪击）
						- 设置快速模式英雄选择（仅快速模式）
						- 设置子阵营（仅斗魂竞技场）
						- 切换就绪状态
						- 云顶之弈赛前配置（仅云顶之弈）
					- 查看社交排行榜
					- 改变小队公开性
						- 让小队仅能通过邀请来进入
						- 将小队公开给好友
					- 更换模式
						- 创建小队
						- 创建自定义房间
						- 通过json创建
					- 寻找对局
				- 管理自定义房间
					- 添加电脑玩家
					- 移除电脑玩家
					- 交换队伍
					- 切换观战状态（！）
					- 更换模式
					- 开始游戏
				- 邀请玩家
				- 聊天
				- 成员管理
					- 晋升为小队拥有者
					- 将玩家移出小队
					- 更改邀请权限
						- 提供邀请权限
						- 撤回邀请权限
				- 输出房间信息
				- 处理邀请
				- 加入小队或自定义房间
				- 退出房间
				- 客户端任务管理
			- 队列中
				- 调试客户端接口
				- 输出寻找对局信息
				- 聊天
				- 处理邀请
				- 加入小队或自定义房间
				- 退出队列
				- 客户端任务管理
			- 就位确认
				- 接受
				- 拒绝
				- 输出就位确认阶段信息
				- 客户端任务管理
			- 英雄选择阶段
				- 调试客户端接口
				- 交换
					- 选用顺序
						- 查看
						- 发送
					- 分路
						- 查看
						- 发送
					- 队友英雄
						- 查看
						- 发送
					- 可用英雄池（替补席）
						- 查看
						- 发送
				- 英雄选择
					- 声明（不可用）
					- 禁用
					- 选择
					- 重随
				- 准备赛前配置
					- 符文（需要自定义脚本19支持）
					- 召唤师技能
					- 皮肤
					- 守卫（眼）皮肤
					- 表情
					- 召唤师图标
					- 水晶枢纽终结特效
					- 旗帜
					- 徽章
					- 冠军杯赛奖杯
				- 静音玩家
				- 聊天
				- 其它
					- 解锁全员战斗加成
					- 设置最爱的分路英雄
					- 清空静音玩家
					- 退出英雄选择阶段
				- 输出英雄选择会话
				- 客户端任务管理
			- 游戏中
				- 聊天
				- 客户端任务管理
			- 重连
			- 等待数据结算
			- 赛后预结算阶段
				- 调试客户端接口
				- 赞誉其他玩家
				- 查看票数
				- 这次不行
				- 输出荣誉投票信息
				- 输出当前事件
				- 聊天
				- 客户端任务管理
			- 赛后结算阶段
				- 调试客户端接口
				- 查看英雄成就点数更新情况
				- 查看计分板数据
					- 英雄联盟
					- 云顶之弈
				- 聊天
				- 再来一局
				- 离开
				- 唤起荣誉投票界面
				- 客户端任务管理
			- 其它
		- 在没有明确说明的情况下，输入“0”以返回上一层。
		- 该脚本会在“cache”文件夹下**创建缓存**，以加快数据资源加载速度。
			- 本地缓存有<ins>24小时</ins>的有效期。
			- 用户可以重新加载数据资源以手动更新本地缓存。
			- 读取缓存预计能节省10～30秒数据资源加载时间。
	- `清除临时文件.bat`用于**清除自定义脚本产生的临时文件**。目前可以清除自定义脚本03、05、10、11、17、19、20和21产生的临时文件。
	- `召唤师信息文件格式转换.bat`用于**将自定义脚本5产生的数据文档在txt和json格式之间重命名**。
		- 大量数据文档的重命名可能导致文件资源管理器卡顿，因此请谨慎使用本脚本。
		- 由于本脚本涉及中文字符，因此**请先在命令行中使用`chcp 65001`以切换代码活动页**，再运行本脚本。
		- 如果正常运行，命令行中会不断提示“1 file(s) moved”。可以使用[Everything软件](https://www.voidtools.com/zh-cn/)以查看“召唤师信息（Summoner Information）”文件夹中的txt文件数量。
			- 尝试在Everything的搜索框中输入`"{文件夹路径}" .txt`以查看某个文件夹下的txt文件列表，在窗口左下角即可看到符合条件的文件数量。
				- “{文件夹地址}”示例：`C:\Users\19250\Desktop\英雄联盟自定义房间创建\召唤师信息（Summoner Information）`。
	- 装备脚本用于**生成各版本的装备信息表**。
		- 该脚本的数据来源是<ins>DataDragon数据库</ins>和<ins>CommunityDragon数据库</ins>。
		- 该脚本支持**所有《英雄联盟》支持的语言**。
		- 该脚本支持两个数据库收录的**所有版本**。
		- 该脚本生成的表格主要分为5个部分：
			- 元数据
			- 装备分类
			- 游戏内详细信息
			- 地图可用性（CommunityDragon收录的装备数据中无此类数据）
			- 基础属性
		- 如果想要批量冻结窗格和启用筛选，可以通过编写宏来一次性对所有表格固定表头。下面以Microsoft Excel为例进行示范。
			1. 在Excel中，依次单击“文件”—“选项”—“自定义功能区”，在右侧的“自定义功能区”中勾选“开发工具”。单击“确定”。
			2. 单击“开发工具”选项卡，再单击“Visual Basic”，打开VBA编辑器。
			3. 在新窗口的“工程 - VBAProject”子窗口中，右键单击“VBAProject ({工作簿名称})”，依次单击“插入”—“模块”。
			4. 在新的模块子窗口粘贴以下宏代码：
			```vba
			Sub FreezeAndFilterTopRowsAndColumns()
				Dim ws As Worksheet
				Dim lastCol As Long
				For Each ws In ThisWorkbook.Worksheets
					ws.Activate ' 选中该工作表
					If ws.AutoFilterMode Then ws.AutoFilterMode = False ' 取消已经存在的筛选
					ActiveWindow.FreezePanes = False ' 取消当前冻结窗格效果
					ActiveWindow.SplitColumn = 0 ' 取消任何可能的列拆分
					ActiveWindow.SplitRow = 0 ' 取消任何可能的行拆分
					ws.Range("E3").Select ' 冻结前两行和前四列
					ActiveWindow.FreezePanes = True ' 冻结窗格
					ws.Range("A2").Select ' 移动光标到A2
					lastCol = ws.Cells(2, ws.Columns.Count).End(xlToLeft).Column ' 确定第二行最后一个有内容的单元格的列数
					ws.Range(ws.Cells(2, 1), ws.Cells(2, lastCol)).Select ' 选中从A2到最后一个有内容的单元格
					Selection.AutoFilter ' 对选中范围应用筛选
					ws.Range("A1").Select ' 光标初始化——选中A1单元格
				Next ws
			End Sub
			```
			注：上面的宏对所有工作表都生效。如果只想对部分工作表生效，需要**在for语句下方**添加对工作表属性的<ins>判断语句</ins>，并将后续操作代码的缩进后移一层。
			5. 关闭VBA编辑器，回到Excel窗口，单击“开发工具”选项卡中的“宏”。
			6. 选择“FreezeTopRowsAndSelectA1”，然后点击“执行”。
			7. 如果想要在保存更改的同时保存该宏，请另存为“.xlsm”格式。
		- 下面另外提供一些宏代码。
			- 清除格式
			```vba
			Sub ClearFormat()
				Dim ws As Worksheet
				Dim lastCol As Long
				For Each ws In ThisWorkbook.Worksheets
					If InStr(ws.Name, "cdragon") > 0 Or ws.Name = "pbe" Or ws.Name = "latest" Then ' 筛选所有由CommunityDragon数据库产生的工作表
						ws.Activate
						If ws.AutoFilterMode Then ws.AutoFilterMode = False
						ActiveWindow.FreezePanes = False
						ActiveWindow.SplitColumn = 0
						ActiveWindow.SplitRow = 0
						ws.Range("A1").Select
					End If
				Next ws
			End Sub
			```
	- 为方便**查阅英雄联盟中的官方术语**，在主目录中添加了一个翻译库脚本`trans.py`。
		- 该脚本每次运行可以选择汇总和保存一种语言的翻译数据资源，并允许同时下载所有语言的翻译数据资源。
		- 由于该脚本仅用于校正术语，其涉及的数据资源仅用于开发程序，而不适用于发行版。因此建议用户在存储库，而不是由发行版压缩包解压得到的文件夹中运行该脚本。
	- 自定义脚本<ins>05、11、13、16、19、20和21</ins>在运行过程中可以**将终端呈现的内容保存到本地日志中**。见主目录下的“<ins>日志（Logs）</ins>”文件夹。
	- 为方便理解**自定义脚本中一些大型数据框的结构**，在主目录中添加了一个工作簿`Customized Program Main Dataframe Structure.xlsx`，以解释其生成过程。
		- 下面对查战绩脚本和自定义脚本20中的`LoLGame_info_df`、自定义脚本11和聊天服务脚本中的`recent_LoLPlayers_df`和自定义脚本20中的`LoLGame_stat_header`的结构进行说明，以便说明一些设定。一些设定在后续解释中不再赘述。
			- 工作表`05 - LoLGame_info_header`、`11 - LoLGame_info_header`、`16 - LoLGame_info_header`和`20 - LoLGame_stat_header`共有6列，其中前3列是**主要数据区域**。
				- `Index`代表`LoLGame_info_data`的键的索引。
				- `Key`代表`LoLGame_info_data`的键。
				- `Value`代表`LoLGame_info_data`的值。
				- `DirectlyImport?`代表从LCU API中获取数据形成数据框时是否需要对数据进行加工。打勾表示直接引用。
				- `OutputOrder`代表输出为工作表时各数据的排列顺序。
				- `DisplayOrder`代表在网页中显示时各数据的排列顺序。只有在网页中显示的表格对应的表头工作表才有这一列。
			- 在该工作表中，主要数据区域设置了9～10种颜色。
				- 无填充代表`Key`不作为LCU API中任何变量的索引。
				- 浅绿色代表`Key`可以作为`LoLGame_info`的索引。
				- 浅蓝色代表`Key`可以作为`LoLGame_info["participantIdentities"][participantId]`的索引。
				- 深蓝色代表`Key`可以作为`LoLGame_info["participantIdentities"][participantId]["player"]`的索引。
				- 深绿色代表`Key`可以作为`LoLGame_info["participants"][participantId]`的索引。
				- 橙色代表`Key`可以作为`LoLGame_info["participants"][participantId]["stats"]`的索引。
				- 紫色代表`Key`来自`LoLGame_info["teams"][teamId]["bans"]`的索引。
					- 注意到其中不包含任何可直接作为索引的键。
				- 黄色代表`Key`可以直接作为`LoLGame_info["participants"][participantId]["timeline"]`的索引。
				- 粉色代表`Key`不作为LCU API中任何变量的索引。
					- 目前粉红色区域只包含`ally?`，表示查询的玩家是否是主玩家的队友。在导出的工作表中，打勾表示该玩家是主玩家的队友。
				- 灰色代表`Key`来自`LoLGame_info["participants"][participantId]["stats"]`的索引。
					- 该部分数据主要通过比较和计算得出。
			- 一些键被标记为无填充。这样的键不作为LCU API中任何变量的索引，但仍来自其填充色所代表的变量的索引。如`gameModeName`不曾出现在对局信息的json对象中，但是实际上来自`LoLGame_info`，对应的是键`"gameMode"`。
			- <b>要获取各个呈现顺序列表，只需要将表格以`OutputOrder`或`DisplayOrder`作升序排列，然后复制`Index`列的单元格内容即可。</b>
		- 下面对查英雄脚本和游戏状态管理脚本中的`LoLChampions_df`的结构进行说明。
			- 工作表`04 - LoLChampions_header (LCU)`和`21 - LoLChampions_header`的主要数据区域设置了8种颜色。
				- 无填充代表`Key`可以直接作为`LoLChampions[championId]`的索引。
				- 浅蓝色代表`Key`来自`LoLChampions[championId]["ownership"]`的索引。
				- 深蓝色代表`Key`来自`LoLChampions[championId]["ownership"]["rental"]`的索引。
				- 浅绿色代表`Key`来自`LoLChampions[championId]["roles"]`的索引。
				- 橙色代表`Key`来自`LoLChampions[championId]["tacticalInfo"]`的索引。
				- 粉色代表`Key`来自`LoLChampions[championId]["passive"]`的索引。
				- 深绿色代表`Key`来自`LoLChampions[championId]["spells"][spell_index]`的索引。
				- 黄色代表`Key`来自`/lol-perks/v1/recommended-champion-positions`接口。
			- 工作表`04 - LoLChampions_header (ddr)`的主要数据区域设置了7种颜色。
				- 无填充代表`Key`可以直接作为`LoLChampions[championId]`的索引。
				- 浅蓝色代表`Key`来自`LoLChampions[championId]["image"]`的索引。
				- 浅绿色代表`Key`来自`LoLChampions[championId]["tags"]`的索引。
				- 深蓝色代表`Key`来自`LoLChampions[championId]["info"]`的索引。
				- 橙色代表`Key`可以作为`LoLChampions[championId]["stats"]`的索引。
				- 粉色代表`Key`来自`LoLChampions[championId]["spells"][spell_index]`的索引。
				- 深绿色代表`Key`来自`LoLChampions[championId]["passive"]`的索引。
			- 工作表`04 - LoLChampions_header (cdr)`的主要数据区域设置了7种颜色。
				- 无填充代表`Key`可以直接作为`LoLChampions[championId]`的索引。
				- 浅蓝色代表`Key`来自`LoLChampions[championId]["tacticalInfo"]`的索引。
				- 浅绿色代表`Key`来自`LoLChampions[championId]["playStyleInfo"]`的索引。
				- 深蓝色代表`Key`来自`LoLChampions[championId]["championTagInfo"]`的索引。
				- 深绿色代表`Key`来自`LoLChampions[championId]["roles"]`的索引。
				- 橙色代表`Key`来自`LoLChampions[championId]["passive"]`的索引。
				- 粉色代表`Key`来自`LoLChampions[championId]["spells"][spell_index]`的索引。
		- 下面对查战绩脚本中的`mastery_df`的结构进行说明。
			- 工作表`05 - mastery_header`的主要数据区域设置了4种颜色。
				- 蓝色代表`Key`可以直接作为`mastery[champion_iter]`的索引。
					- 白字只包含`champion`和`alias`，分别表示英雄的称号和名字。LCU API只提供了英雄序号。
				- 浅绿色代表`Key`来自`mastery[champion_iter]["nextSeasonMilestone"]`的索引。
				- 深紫色代表`Key`来自`mastery[champion_iter]["nextSeasonMilestone"]["rewardConfig"]`的索引。
		- 下面对查战绩脚本中的`ranked_df`的结构进行说明。
			- 工作表`05 - ranked_header`的`Key`都可作为`ranked["queues"][Id]`的索引。
			- 注意到`OutputOrder`列存在重复数据。造成这个现象的根本原因是云顶之弈狂暴模式的段位和其它排位模式的段位被记录在两个变量中，但是输出表格时期望输出在一列中，所以有一些原键的输出顺序相同。
		- 下面对查战绩脚本中的`ladders_df`的结构进行说明：
			- 工作表`05 - ladders_header`的主要数据区域设置了4种颜色。
				- 无填充代表`Key`可以直接作为`ladders[ladderId]`的索引。
				- 浅蓝色代表`Key`可以作为`ladders[ladderId]["divisions"][divisionId]["standings"][standingId]`的索引。
				- 浅绿色代表`Key`可以作为`/lol-summoner/v2/summoners/puuid/{puuid}`接口的索引。
				- 橙色代表`Key`不作为LCU API中任何变量的索引。
		- 下面对查战绩脚本和自定义脚本11中的`LoLHistory_df`的结构进行说明：
			- 工作表`05 - LoLHistory_header`和`11 - LoLHistory_header`的主要数据区域设置了6种颜色。
				- 无填充代表`Key`不作为LCU API中任何变量的索引。
				- 浅蓝色代表`Key`可以作为`LoLHistory["games"]["games"]`的索引。
				- 浅绿色代表`Key`可以直接作为`LoLHistory["games"]["games"]["participantIdentities"][0]["player"]`的索引。
				- 橙色代表`Key`可以作为`LoLHistory["games"]["games"]["participants"][0]`的索引。
				- 深绿色代表`Key`可以作为`LoLHistory["games"]["games"]["participants"][0]["stats"]`的索引。
				- 紫色代表`Key`可以直接作为`LoLHistory["games"]["games"]["participants"][0]["timeline"]`的索引。
		- 下面对查战绩脚本中的`LoLGame_leaderboard_df`和`TFTGame_leaderboard_df`和自定义脚本20中的`social_leaderboard_df`的结构进行说明。
			- 工作表`05 - LoLGame_leaderboard_header`、`05 - TFTGame_leaderboard_header`和`20 - social_leaderboard_header`的主要数据区域设置了2种颜色。
				- 蓝色代表`Key`可以作为`participantInfo`的索引。
				- 无填充代表`Key`可以作为`participant_leaderboard`的索引。
		- 下面对查战绩脚本中的`LoLGame_timeline_df`的结构进行说明。
			- 工作表`05 - LoLGame_timeline_header`的主要数据区域设置了4种颜色。
				- 蓝色代表`Key`可以作为`frames[frameId]`的索引。
				- 灰色代表`Key`对应的值是自动生成的，不依赖于LCU API。
				- 绿色代表`Key`来自`LoLGame_info`的一些信息。
				- 橙色代表`Key`可以作为`frames[frameId]["participantFrames"][participantId]`的索引。
		- 下面对查战绩脚本中的`LoLGame_event_df`的结构进行说明。
			- 工作表`05 - LoLGame_event_header`的主要数据区域设置为无填充。
				- 暗红色字代表`Key`可以直接作为`events[timestamp]`的索引。
				- 一些键被标记为无填充。这样的键不作为LCU API中任何变量的索引，但仍来自其填充色所代表的变量的索引。如`item`不曾出现在对局时间轴的json对象中，但是实际上来自`LoLGame_timeline["frames"]["events"][eventId]`，对应的是索引`"itemId"`。
		- 下面对查战绩脚本中的`TFTHistory_df`、自定义脚本11和聊天服务脚本中的`recent_TFTPlayers_df`和自定义脚本20中的`TFTGame_stat_header`的结构进行说明。
			- 工作表`05 - TFTHistory_header`、`11 - TFTHistory_header`、`16 - TFTHistory_header`和`20 - TFTGame_stat_header`的主要数据区域设置了5种颜色。
				- 无填充代表`Key`不作为LCU API中任何变量的索引。
				- 天蓝色代表`Key`可以作为`TFTHistory[gameIndex]["json"]`的索引。
				- 绿色代表`Key`可以作为`TFTHistory[gameIndex]["json"]["participants"]`的索引。
				- 粉红色代表`Key`的前半部分来自`TFTHistory[gameIndex]["json"]["participants"][participantId]["traits"]`的索引，后半部分可以直接作为`TFTHistory[gameIndex]["json"]["participants"][participantId]["traits"][trait_index]`的索引。
				- 深蓝色代表`Key`的第一部分来自`TFTHistory[gameIndex]["json"]["participants"][participantId]["units"]`的索引。
					- 129～183之间的键的第二部分可以直接作为`TFTHistory[gameIndex]["json"]["participants"][participantId]["units"][unit_index]`的索引。
					- 184及以后的键第二部分来自`TFTHistory[gameIndex]["json"]["participants"][participantId]["units"][unit_index]["items"]`的索引，第三部分可以直接作为`TFTHistory[gameIndex]["json"]["participants"][participantId]["units"][unit_index]["items"][item_index]`的索引。
			- 相比之下，工作表`05 - TFTGame_info_header`和工作表`05 - TFTHistory_header`只差了前面9行内容。
		- 下面对商品藏品信息整理脚本中的`catalog_df`的结构进行说明。
			- 工作表`07 - catalog_header`的主要数据区域设置了3种颜色。`item`是`catalogList`中的任意一个元素。
				- 无填充代表`Key`可以直接作为`item`的索引。
				- 蓝色代表`Key`来自`item["prices"][priceId]`的索引。
				- 绿色代表`Key`来自`item["prices"][priceId]["sale"]`的索引。
		- 下面对商品藏品信息整理脚本中的`store_df`的结构进行说明。
			- 工作表`07 - store_header`的主要数据区域设置了5种颜色。`item`是`store`中的任意一个元素。
				- 无填充代表`Key`可以直接作为`item`的索引。
				- 蓝色代表`Key`可以直接作为`item["localizations"][locale]`的索引。
				- 绿色代表`Key`的后半部分可以作为`item["prices"][priceId]`的索引。
				- 黄色代表`Key`的后半部分可以直接作为`item["sale"]`的索引。
				- 紫色代表`Key`的后半部分来自`item["sales"]["prices"][priceId]`的索引。
		- 下面对商品藏品信息整理脚本和游戏状态管理脚本中的`collection_df`的结构进行说明。
			- 工作表`07 - collection_header`和`21 - collection_header`的主要数据区域设置了2种颜色。`item`是`collection`中的任意一个元素。
				- 无填充代表`Key`可以直接作为`item`的索引。
				- 蓝色代表`Key`作为`item["payload"]`的索引。
		- 下面对队列查询脚本和自定义脚本20中的`queues_df`的结构进行说明。
			- 工作表`09 - queues_header`和`20 - queues_header`的主要数据区域设置了4种颜色。
				- 绿色代表`Key`可以直接作为`queues[id]`的索引。
				- 橙色代表`Key`可以作为`queues[id]["gameTypeConfig"]`的索引。
				- 蓝色代表`Key`可以作为`queues[id]["queueRewards"]`的索引。
		- 下面对自定义脚本11中的`recent_players_metaDf`的结构进行说明。
			- 工作表`11 - recent_players_metadata_he`（`11 - recent_players_metadata_header`）的主要数据区域设置为无填充。
				- `Key`可以直接作为`recent_players_metadata_list`的索引。
		- 下面对整理战利品脚本中的`player_loot_df`的结构进行说明。
			- 工作表`12 - player_loot_header`的主要数据区域未设置颜色，因为这些键都可作为`player_loot[i]`的索引。
		- 下面对查天梯脚本中的`splits_info_df`的结构进行说明。
			- 工作表`13 - splits_info_header`的主要数据区域设置了4种颜色。
				- 青绿色代表`Key`可以作为`splitsConfig["splits"][splitId]`的索引。
				- 浅绿色代表`Key`来自`splitsConfig["splits"][splitId]["victoriousSkinRewardGroup"]`的索引。
				- 橙色代表`Key`来自`splitsConfig["splits"][splitId]["victoriousSkinRewardGroup"]["splitPointsByHighestSeasonTier"]`的索引。
		- 下面对查天梯脚本中的`rewardTrack_df`的结构进行说明。
			- 工作表`13 - rewardTrack_header`的主要数据区域设置了3种颜色。
				- 浅蓝色代表`Key`可以直接作为`splitsConfig["splits"][splitId]`的索引。
				- 橙色代表`Key`对应的值是自动生成的，不依赖于LCU API。
				- 浅绿色代表`Key`可以作为`splitsConfig["splits"][splitId]["rewardTrack"][rewardTrackId]["rewards"][rewardId]`的索引。
		- 下面对查天梯脚本中的`challenger_ladders_metadata_df`的结构进行说明。
			- 工作表`13 - challenger_ladders_metadat`（`13 - challenger_ladders_metadata_header`）的主要数据区域设置了2种颜色。
				- 浅蓝色代表`Key`可以作为`ladders`的索引。
				- 浅绿色代表`Key`可以作为`ladders["divisions"][divisionId]`的索引。
		- 下面对查天梯脚本中的`ladders_df["challenger_ladder"][queueType]`的结构进行说明。
			- 工作表`13 - challenger_ladders_header`的主要数据区域设置了2种颜色。
				- 无填充代表`Key`可以作为`ladders["divisions"][divisionId]["standings"][standingId]`的索引。
				- 浅蓝色代表`Key`可以作为`/lol-summoner/v2/summoners/puuid/{puuid}`接口的索引。
		- 下面对查天梯脚本中的`ladders_df["topRated_ladder"][queueType]`的结构进行说明。
			- 工作表`13 - topRated_ladders_header`的主要数据区域设置了2种颜色。
				- 无填充代表`Key`可以直接作为`ladders["standings"][standingId]`的索引。
				- 浅蓝色代表`Key`可以作为`/lol-summoner/v2/summoners/puuid/{puuid}`接口的索引。
		- 下面对聊天脚本中的`friend_hovercard_df`的结构进行说明。
			- 工作表`16 - friend_hovercard_header`的主要数据区域设置了4种颜色。`friend`是`friends`中的任意一个元素。
				- 蓝色代表`Key`可以作为`friend`的索引。
				- 浅绿色代表`Key`可以作为`friend["lol"]`的索引。
				- 橙色代表`Key`的后半部分可以作为`eval(friend["lol"]["pty"])`的索引。
				- 绿色代表`Key`的后半部分可以作为`eval(friend["lol"]["regalia"])`的索引。
		- 下面对聊天脚本中的`friend_hovercard_df_simple`的结构进行说明。
			- 工作表`16 - friend_hovercard_header_si`（`16 - friend_hovercard_header_simple`）的主要数据区域设置为无填充。`friend`是`friends`中的任意一个元素。
				- `Key`可以直接作为`friend`的索引。
		- 下面对聊天脚本中的`friend_groups_df`的结构进行说明。
			- 工作表`16 - friend_groups_header`的主要数据区域设置为无填充。`group`是`friend_groups`中的任意一个元素。
				- `Key`可以直接作为`group`的索引。
		- 下面对聊天脚本和游戏状态管理脚本中的`conversation_df`的结构进行说明。
			- 工作表`16 - conversation_header`和`21 - conversation_header`的主要数据区域设置为无填充。`conversation`是`conversations`中的任意一个元素。
				- `Key`可以直接作为`conversation`的索引。
		- 下面对聊天脚本中的`message_df`的结构进行说明。
			- 工作表`16 - message_header`的主要数据区域设置为无填充。`message`是`messages`中的任意一个元素。
				- `Key`可以作为`message`的索引。
					- 9之前的键可以直接作为`message`的索引。
					- 9及以后的键通过`get_info`函数得到。
		- 下面对聊天脚本中的`friend_request_df`的结构进行说明。
			- 工作表`16 - friend_request_header`的主要数据区域设置为无填充。`friend_request`是`friend_requests`中的任意一个元素。
				- `Key`可以作为`friend_request`的索引。
					- 10之前的键可以直接作为`friend_request`的索引。
					- 10号键的后半部分可以直接作为`summonerIcons[friend_request["icon"]]`的索引。
		- 下面对聊天脚本中的`party_df`的结构进行说明。
			- 工作表`16 - party_header`的主要数据区域设置为4种颜色。`party`是`parties`中的任意一个元素。
				- 蓝色代表`Key`可以直接作为`party`的索引。
				- 浅绿色代表`Key`的后半部分可以直接作为`queues[party["queueId"]]`的索引。
				- 橙色代表`Key`来自`party`的索引。
				- 黄色代表`Key`不作为LCU API中任何变量的索引。
					- 目前黄色区域只包含`full?`，表示小队是否满员。在导出的工作表中，打勾表示小队已经满员。
		- 下面对聊天脚本和游戏状态管理脚本中的`invid_df`的结构进行说明。
			- 工作表`16 - invid_header`和`21 - invid_header`的主要数据区域设置为3种颜色。`invid`是`receivedInvitations`中的任意一个元素。
				- 蓝色代表`Key`可以作为`invid`的索引。
				- 浅绿色代表`Key`可以直接作为`invid["gameConfig"]`的索引。
				- 橙色代表`Key`的后半部分来自`queues`的索引。
		- 下面对聊天脚本中的`muted_player_df`的结构进行说明。
			- 工作表`16 - player_mute_header`的主要数据区域设置为无填充。`muted_player`是`muted_players`中的任意一个值。
				- `Key`可以作为`muted_player`的索引。
					- 5之前的键可以直接作为`muted_player`的索引。
					- 5及以后的键通过`get_info`函数得到。
		- 下面对聊天脚本中的`champSelect_team_df`和游戏状态管理脚本中的`players_df`的结构进行说明。
			- 工作表`16 - champSelect_team_header`、`20 - champSelect_players_header`和`21 - champSelect_players_header`的主要数据区域设置为无填充。`player`是`players`中的任意一个值。
				- `Key`可以作为`player`的索引。
		- 下面对聊天脚本中的`captureDevices_df`的结构进行说明。
			- 工作表`16 - captureDevices_header`的主要数据区域设置为无填充。`device`是`captureDevices`中的任意一个值。
				- `Key`可以直接作为`device`的索引。
		- 下面对聊天脚本中的`voiceSettings_df`的结构进行说明。
			- 工作表`16 - voiceSettings_header`的主要数据区域设置为无填充。
				- `Key`可以作为`device`的索引。
					- 12之前的键可以直接作为`device`的索引。
					- 12号键通过`captureDevices`得到。
			- 该数据框沿用了旧版数据框创建方式。见查战绩脚本的`info_data`定义。
		- 下面对聊天脚本中的`participant_record_df`的结构进行说明。
			- 工作表`16 - participant_record_header`的主要数据区域设置为无填充。`participant`是`participant_records`中的任意一个元素。
				- `Key`可以作为`participant`的索引。
					- 8之前的键可以直接作为`participant`的索引。
					- 9和10号键通过`get_info`函数得到。
		- 下面对聊天脚本中的`blockList_df`的结构进行说明。
			- 工作表`16 - blockList_header`的主要数据区域设置为无填充。`player`是`blockList`中的任意一个元素。
				- `Key`可以作为`player`的索引。
					- 8之前的键可以直接作为`player`的索引。
					- 8号键的后半部分可以作为键的前半部分所指数据资源的索引。
		- 下面对游戏类型检查脚本中的`gametype_config_df`的结构进行说明。
			- 工作表`17 - gametype_config_header`的主要数据区域设置为无填充。`config`是`gametype_config`中的任意一个元素。
				`Key`可以直接作为`config`的索引。
		- 下面对任务脚本中的`mission_df`的结构进行说明。
			- 工作表`18 - mission_header`的主要数据区域设置了6种颜色。`mission`是`missions`中的任意一个元素。
				- 无填充代表`Key`可以作为`mission`的索引。
				- 蓝色代表`Key`的后半部分可以直接作为`mission["display"]`的索引。
				- 浅绿色代表`Key`来自`mission["metadata"]`的索引。
				- 深绿色代表`Key`的后半部分可以直接作为`mission["rewardStrategy"]`的索引。
				- 橙色代表`Key`来自`mission["objective"][objectiveId]`的索引。
				- 紫色代表`Key`的后半部分来自`objective`的索引。
				- 蓝色、浅绿色、深绿色和橙色部分采用同一套代码框架。
		- 下面对任务脚本中的`objective_group_df`的结构进行说明。
			- 工作表`18 - objective_group_header`的主要数据区域设置了2种颜色。`objective`是`objectives`中的任意一个元素。`objectiveGroup`是`objective["objectives"]`中的任意一个元素。
				- 无填充代表`Key`可以作为`objective`的索引。
				- 蓝色代表`Key`的后半部分可以作为`objectiveGroup`的索引。
		- 下面对符文脚本中的`perk_df`的结构进行说明。
			- 工作表`19 - perk_header`的主要数据区域设置为无填充。`perk`是`perks`中的任意一个元素。
				- `Key`可以作为`perk`的索引。
		- 下面对符文脚本中的`recommendedPage_df`的结构进行说明。
			- 工作表`19 - recommendedPage_header`的主要数据区域设置了3种颜色。`page`是`recommendedPages`中的任意一个元素。
				- 无填充代表`Key`可以作为`page`的索引。
				- 蓝色代表`Key`的后半部分可以直接作为`page["keystyone"]`的索引。
				- 绿色代表`Key`来自`page["perks"][perkId]`的索引。
		- 下面对符文脚本和游戏状态管理脚本中的`perkPage_df`的结构进行说明。
			- 工作表`19 - perkPage_header`和`21 - perkPage_header`的主要数据区域设置了3种颜色。`page`是`perkPages`中的任意一个元素。
				- 无填充代表`Key`可以作为`page`的索引。
				- 蓝色代表`Key`的后半部分可以直接作为`page["pageKeystone"]`的索引。
				- 绿色代表`Key`来自`page["uiPerks"][pageId]`的索引。
		- 下面对自定义脚本20中的`inGame_players_df`的结构进行说明。
			- 工作表`20 - inGame_players_header`的主要数据区域设置了2种颜色。`player`是`teamOne + teamTwo`中的任意一个元素。`loadout`是`player`的赛前配置。
				- 无填充代表`Key`可以作为`player`的索引。
				- 蓝色代表`Key`可以作为`loadout`的索引。
		- 下面对自定义脚本20中的`process_df`的结构进行说明。
			- 工作表`20 - process_header`的主要数据区域设置了2种颜色。
				- 无填充代表`Key`不作为任何变量的索引。
				- 蓝色代表`Key`可以直接作为`parent`和`child`的索引。
		- 下面对自定义脚本21中的`swaps_df`的结构进行说明。
			- 工作表`21 - swaps_header`的主要数据区域设置为无填充。
				- `Key`可以直接作为`swap`的索引。
		- 下面对自定义脚本21中的`custom_game_df`的结构进行说明。
			- 工作表`21 - custom_game_header`的主要数据区域设置为无填充。`lobby`是`custom_lobbies`中的任意一个元素。
				- `Key`可以作为`lobby`的索引。
		- 下面对自定义脚本21中的`skins_df`的结构进行说明。
			- 工作表`21 - skins_header`的主要数据区域设置了6种颜色。`skin`是`championSkins.values()`中的任意一个元素。`skin_flat`是`skins_flat.values()`中的任意一个元素。
				- 无填充代表`Key`可以直接作为`skin`的索引。
				- 浅绿色代表`Key`来自`skin["emblems"]`。
					- 29和30号键的后半部分可以直接作为`skin["emblems"]`的索引。
					- 31和32号键的后半部分可以直接作为`skin["emblems"][emblemIndex]["emblemPath"]`的索引。
				- 深绿色代表`Key`的后半部分可以直接作为`skin["questSkinInfo"]`的索引。
				- 黄色代表`Key`来自`skin_flat`。
					- 41～44号键可以直接作为`skin_flat`的索引。
					- 45～47号键的后半部分可以直接作为`LoLChampions[skin_flat["championId"]]`的索引。
				- 浅蓝色代表`Key`的后半部分可以直接作为`skin_flat["ownership"]`的索引。
				- 深蓝色代表`Key`的第三部分可以作为`skin_flat["ownership"]["rental"]`的索引。
		- 下面对自定义脚本21中的`grid_champion_df`的结构进行说明。
			- 工作表`21 - grid_champion_header`的主要数据区域设置了2种颜色。`champion`是`grid_champions`中的任意一个元素。
				- 无填充代表`Key`可以作为`champion`的索引。
				- 蓝色代表`Key`可以直接作为`champion["selectionStatus"]`的索引。
		- 下面对自定义脚本21中的`muted_player_df`的结构进行说明。
			- 工作表`21 - muted_player_header`的主要数据区域设置为无填充。`player`是`muted_players`中的任意一个元素。
				- `Key`可以作为`player`的索引。
					- 0～3号键可以直接作为`player`的索引。
					- 4和5号键可以直接作为`player_info["body"]`的索引。
		- 下面对自定义脚本21中的`social_leaderboard_df`的结构进行说明。
			- 工作表`21 - social_leaderboard_header`的主要数据区域设置为无填充。`player`是`social_leaderboard["rowData"]`中的任意一个元素。
				- `Key`可以作为`player`的索引。
					- 0～15号键可以直接作为`player`的索引。
					- 16和17号键的后半部分可以直接作为`summonerIcons[player["profileIconId"]]`的索引。
		- 下面对自定义脚本21中的`availableBot_df`的结构进行说明。
			- 工作表`21 - availableBot_header`的主要数据区域设置了2种颜色。`bot`是`available_bots`中的任意一个元素。
				- 无填充代表`Key`可以直接作为`bot`的索引。
				- 蓝色代表`Key`可以直接作为`LoLChampions[bot["id"]]`的索引。
		- 下面对自定义脚本21中的`member_df`的结构进行说明。
			- 工作表`21 - member_header`的主要数据区域设置为无填充。`member`是`members`中的任意一个元素。
				- `Key`可以作为`member`的索引。
		- 下面对自定义脚本21中的`ballot_player_df`的结构进行说明。
			- 工作表`21 - ballot_player_header`的主要数据区域设置为无填充。`player`是`honor_ballot["eligibleAllies"] + honor_ballot["eligibleOpponents"]`中的任意一个元素。
				- `Key`可以作为`player`的索引。
		- 下面对自定义脚本21中的`eog_mastery_update_df`的结构进行说明。
			- 工作表`21 - eog_mastery_update_header`的主要数据区域设置为无填充。
				- `Key`可以作为`mastery_updates`的索引。
					- 0～18号键可以直接作为`mastery_updates`的索引。
					- 19～21号键的后半部分可以直接作为`LoLChampions[mastery_updates["championId"]]`的索引。
					- 22和23号键的后半部分可以直接作为`player_info["body"]`的索引。
		- 下面对自定义脚本21中的`eog_stat_metaDf_lol`的结构进行说明。
			- 工作表`21 - eog_stat_metadata_lol_head`（`21 - eog_stat_metadata_lol_header`）的的主要数据区域设置了4种颜色。
				- 无填充代表`Key`可以作为`eog_stats_block`的索引。
				- 蓝色代表`Key`的后半部分可以直接作为`eog_stats_block["mucJwtDto"]`的索引。
				- 绿色代表`Key`的后半部分可以直接作为`eog_stats_block["rerollData"]`的索引。
				- 橙色代表`Key`的后半部分可以作为`eog_stats_block["teamBoost"]`的索引。
				- 蓝色、绿色和橙色部分采用同一套代码框架。
		- 下面对自定义脚本21中的`eog_teamstat_df_lol`的结构进行说明。
			- 工作表`21 - eog_teamstat_data_lol_head`（`21 - eog_teamstat_data_lol_header`）的主要数据区域设置了2种颜色。`team`是`eog_stats_block["teams"]`中的任意一个元素。
				- 无填充代表`Key`可以作为`team`的索引。
				- 蓝色代表`Key`的后半部分可以作为`team["stats"]`的索引。
		- 下面对自定义脚本21中的`eog_playerstat_df_lol`的结构进行说明。
			- 工作表`21 - eog_playerstat_data_lol_he`（`21 - eog_playerstat_data_lol_header`）的主要数据区域设置了2种颜色。`team`是`eog_stats_block["teams"]`中的任意一个元素。`player`是`team["players"]`中的任意一个元素。
				- 无填充代表`Key`可以作为`player`的索引。
				- 蓝色代表`Key`的后半部分可以作为`player["stats"]`的索引。
		- 下面对自定义脚本21中的`eog_stat_metaDf_tft`的结构进行说明。
			- 工作表`21 - eog_stat_metadata_tft_head`（`21 - eog_stat_metadata_tft_header`）的主要数据区域设置为无填充。
				- `Key`可以作为`tft_eog_stats`的索引。
		- 下面对自定义脚本21中的`eog_stat_df_tft`的结构进行说明。
			- 工作表`21 - eog_playerstat_data_tft_he`（`21 - eog_playerstat_data_tft_header`）的主要数据区域设置了7种颜色。`player`是`tft_eog_stats["players"]`中的任意一个元素。
				- 无填充代表`Key`可以作为`player`的索引。
					- 0～14号键可以直接作为`player`的索引。
					- 15和16号键的后半部分可以直接作为`summonerIcons[player["iconId"]]`的索引。
				- 绿色代表`Key`的后半部分可以直接作为`player["augments"][augmentIndex]`的索引。
				- 橙色代表`Key`的后半部分可以直接作为`player["boardPieces"][unit_index]`的索引。
				- 蓝色代表`Key`的第三部分可以直接作为`player["boardPieces"][unit_index]["items"][item_index]`的索引。
				- 紫色代表`Key`的后半部分可以直接作为`player["companion"]`的索引。
				- 黄色代表`Key`的后半部分可以直接作为`player["customAugmentContainer"]`的索引。
				- 粉色代表`Key`的后半部分可以直接作为`player["playbook"]`的索引。
				- 紫色、黄色和粉色部分采用同一套代码框架。
		- 下面对装备脚本中的`LoLItem_df`的元数据进行说明。
			- 工作表`Item Program - base_header (ddr`的主要数据区域设置了3种颜色。`item`是`LoLItems_locale["data"]`的键为`i`的值。`item_default`是`LoLItems_default["data"]`的键为`i`的值。
				- 无填充代表`Key`不作为装备数据中的任何索引。
				- 蓝色代表`Key`可以作为`item`的索引。
				- 绿色代表`Key`来自`item["gold"]`的索引。
			- 工作表`Item Program - base_header (ddr`的主要数据区域设置为无填充。`item`是`LoLItems_locale`中的任意一个元素。`item_default`是`LoLItems_default`中的任意一个元素。
				- `Key`可以作为`item`的索引。
6. 一般情况下，本程序集生成的包含json数据的文本文档都是带缩进的。如果需要根据这些文件复现python运行环境中的字典变量，只需要向json库中的load函数传入一个由open函数创建的文件指针即可。如`fp = open("{文件名}.txt", "r", encoding = "utf-8")`和`d = json.load(fp)`。
	- 若要在运行环境中将dumps函数生成的带缩进的json字符串转换成不带缩进的json字符串，只需要将dumps函数生成的字符串传入loads函数即可。如`formatted = json.dumps({字典变量}, indent = 8, ensure_ascii = False)`和`d = json.loads(formatted)`。
# 后记
作为初学者，我只学习到了Python的一些基本语法，还是在基于结构化程序设计的思想来实现每一个功能，而没有用到类和对象的概念，导致代码的整合程度不高，存在大量冗余的代码。例如查询召唤师战绩的脚本中，存在**大量复制**的现象。对于长字符串，我的处理方法是**一行写到底**，是基于<ins>缩减代码行数</ins>的考虑，可能不利于代码的浏览，还请见谅！另外，本程序集的注释尚不充足，还需要进一步完善。由于尚未学习图形化界面相关的知识（唯一学过的就是VB了😂），我只能设计这种通过命令行来实现功能的程序。（y1s1，现在并没有设计图形化界面的打算。）\
整个程序集中的程序，除了参考知乎博主XHXIAIEIN的学习心得和拳头官方公布的接口，其实没有什么创新点，主要就是一个数据的爬取和整理。如果大家有什么好玩的想法，也欢迎复刻本存储库，并创建属于你自己的分支和提交拉取请求！\
未来如果有机会，也许会根据查战绩脚本生成的对局信息数据框，结合WeGame或者OP.GG评分来回归得到现有对局表现评分机制。

---
(The following content is the English version of README.)
# Declaration
**This program set only supports study use or personal entertainment. Any commercial use is forbidden!**
# Program Set Functionality
This program set allows <ins>creating custom lobbies (including 5V5 Practice Tool)</ins>, <ins>checking available bot players and game modes</ins> and development of other exploratory functions.\
**Cloning this repository** requires about <ins>37 GiB</ins> local storage. **The compressed file in release** takes up about <ins>2 GiB</ins> local storage.\
For details about customized programs that is beyond the scope of creating a custom lobby, please check the sixth instruction.
1. This program set provides the consolidated version for all game modes and all levels and positions of bot difficulity.
	- The consolidated version takes `available-bots.xlsx` in the home directory as the bot player data. For its sake, **please don't move any offline files (this file included)**.
	- The simplified consolidated version has the following features:
		- Custom Game mode selection
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
		- Bot position and difficulty selection\
			By this file, the user may decide whether to set all bots' difficulty the same.
		- Bot number configuration
		- Client action simulation
	- The bot adding program allows users to add bot players to already created lobbies, instead of recreating another lobby and **clearing all players**. Only this file is allowed to visit **unofficial** bot player information.
2. In this program set, `check_available_bots.py` and `check_available_gameMode.py` provide the functions of checking available bot players and game modes, respectively.
	- **Please don't create any custom lobby while the program is running**, in case unavailable lobbies may be output.
		- Available custom lobby parameters on Chinese Ionia server (gameMode, mapId):
			- ("CLASSIC", 11)
			- ("CLASSIC", 12)
			- ("CLASSIC", 21)
			- ("CLASSIC", 22)
			- ("ARAM", 12)
			- ("PRACTICETOOL", 11)
			- ("TUTORIAL", 11)
			- ("TUTORIAL", 12)
			- ("TUTORIAL", 21)
			- ("TUTORIAL", 22)
			- ("GAMEMODEX", 11)
			- ("GAMEMODEX", 12)
			- ("GAMEMODEX", 21)
			- ("GAMEMODEX", 22)
	- The detection range has been set to some values by default. For users' own requirements, please modify the ranges.
3. In this program set, `get_lobby_information.py` allows repeatedly getting lobby information.
4. This program set provides offline data resources to save the time of preparing data.
	- The data resources include all **text files** under <ins>latest and pbe</ins> folders of *CommunityDragon* database and all **Chinese and English files** under <ins>data</ins> folder of the *dragontail archived file* of *DataDragon* database.
		- The update of data resources in CommunityDragon database will follow <ins>each adjustment of PBE</ins> **daily**, and the update of data resources in DataDragon database will follow <ins>each patch mainteinance of live servers </ins> **about every fortnight**.
	- `自动更新离线数据.py` under the `离线数据（Offline Data）` folder simplifies the updating process of data resources.
		- This program is designed only for the developer to update offline data, but anyone interested is welcome to download and experience it.
		- This program can be used to update data resources from both CommunityDragon and DataDragon databases.
			- While updating CommunityDragon data resources, the program provides 4 updating modes.
				- [Updating According to Modification Time] is meant to reflect the **changes** between online and local data resources.
					- In a case where the **modification times** of some local data resources are **later** than those of the corresponding online data resources, whereas the **actual content** of these local data resources is **earlier** than that of their corresponding online data resources, running this mode *won't update* these local data resources.
					- This mode is set as the default mode in the <ins>repository</ins>. Submit an empty string to adopt the default mode.
				- [Updating According to Program Demands] is meant to **quickly** update the data resources only necessary for customized programs.
					- This mode is set as the default mode in the <ins>releases</ins>. Submit an empty string to adopt the default mode.
			- While updating DataDragon data resources, users need to **follow the hint of the program**: first download the latest compressed tarball of DataDragon database, then decompress it, and finally provide the decompression directory.
			- While updating DataDragon data resources, the program provides 2 updating modes.
				- [Global Scanning] performs an **entire comparison** on the data resources between the local  repository and the latest DataDragon archive compressed file that has already been downloaded to local.
					- This mode is set as the default mode in the <ins>repository</ins>. Submit an empty string to adopt the default mode.
				- [Updating According to Program Demands] is meant to **quickly** update the data resources only necessary for customized programs.
					- This mode is set as the default mode in the <ins>releases</ins>. Submit an empty string to adopt the default mode.
			- For resources updated online, **an appropriate proxy** may accelerate the data capture process.
		- Because a number of data resources might be involved in a commit, GitHub can't load the diff. Here two methods of checking the diff are recommended:
			1. Visit [LoL-Patch-Change repository](https://github.com/WordlessMeteor/LoL-Patch-Change) to look over the **main** update content *online*.
			2. Clone [this repository](https://github.com/WordlessMeteor/LoL-DIY-Programs) to local and check the commit with header "<ins>Offline Data Resource Update</ins>" to look through the **complete** update content *offline*.
				- Cloning this repository takes up approximately <ins>37 GiB</ins> local space. Please ensure your disk has sufficient space for it.
				- For those commits that involve a number of data resources, it still takes several minutes to load the diff locally. Please wait in patience.
5. The program set is adapted from `create_custom_lobby.py` in the home directory.
# Notes on Instructions
1. The whole program set is made of Python programs. Users are highly suggested to download the latest version of Python from [Python official website](https://www.python.org/). (A version that isn't latest is also OK, but please make sure it's not too early, either [xD])
	- For this first time of installation of Python, please tick on `Add Python to PATH` option.
	- If the working directories of Python aren't present in the environment variable Path, the following steps can be adopted to add Python to Path.
		1. Type in `path` in Windows search bar and click `编辑系统环境变量`. `系统属性` window will pop up.
		2. Click `环境变量(N)` button and the `环境变量` window will occur.
		3. In `用户变量`, Find the variable `Path` and double-click it to enter the `编辑环境变量` dialog box.
		4. Add 3 addresses by clicking the `新建(N)` button. These addresses are working directories of Python. If some similar addresses already exist, there's no need to add them.\
			`C:\Users\[Username]\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\`\
			`C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\Scripts`\
			For example, my username is `19250`, and my Python version is <ins>3.13.3</ins>. Then the updated PATH should include \
			`C:\Users\19250\AppData\Local\Programs\Python\Launcher\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python312\`\
			`C:\Users\19250\AppData\Local\Programs\Python\Python312\Scripts\`
		5. Basically, adding the three addresses to `Path` in `系统变量` is of no harm.
		6. Restart <ins>Command Prompt</ins> or <ins>Terminal</ins>. In that case, Python tools, e.g. pip, can be used as normal.
	- After installation and environment variable configuration of Python, use `pip install [LibraryName]` command to install required libraries for this program set. For Chinese mainland users, using a proxy or setting a mirror should accelerate the downloading stage of Python libraries. Required libraries for this program set are:
		- lcu_driver
			- I've forked [lcu_driver library](https://github.com/WordlessMeteor/lcu-driver/tree/master/lcu_driver) , so that the user can still pxperience library files in the forked repository if the corresponding pull request hasn't been accepted to merge into the official version, or has been rejected to merge, by the original author.
			- I'm only reponsible for modifying the library files in the forked repository **according to the demands of this program set**, and not obligated to merge others' changes to the library files into mine. However, any user that commented and suggested on the library update **based on the program set update** is welcome 👏
			- If you want to use my `lcu_driver` library, please follow these steps:
				1. Open [my lcu-driver repo homepage](https://github.com/WordlessMeteor/lcu-driver).
				2. Click <ins>the green "Code" button</ins>. Then click <ins>DownloadZIP</ins> to download the source code of this repository.
				3. Extract the zip file to the current folder.
					- Don't worry about the chaos after the extraction! The files should have been put in a subfolder.
				4. Open the directory where Python stores libraries.
					- Basically, the directory is at `C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\Lib\site-packages`.
						- For example, my username is `19250`, and my Python version is <ins>3.13.3</ins>. Then the library directory should be \
						`C:\Users\19250\AppData\Local\Programs\Python\Python312\Lib\site-packages`
					- If the last approach doesn't work, please enter the command `pip install lcu_driver` in CMD to install the original `lcu_driver` library and then search for <ins>lcu_driver</ins> in [Everything App](https://www.voidtools.com/en-us/) to locate to the Python library directory.
				5. Select `lcu_driver` folder in the extracted files. Copy it to the Python library directory. If files already exist, please select `Replace the files in the destination`.
				6. If you need to recover the original `lcu_driver` library, please enter `pip uninstall lcu_driver` in CMD to uninstall the modified library, and then enter `pip install lcu_driver` to reinstall the original release of the library.
		- openpyxl
		- pandas
		- requests
		- pyperclip
		- pickle
		- urllib
		- wcwidth
		- bs4
2. To improve the response speed, please open any program in this program set by Command Prompt or Terminal, instead of Python IDLE.
	- To prevent the window from flashing quickly, it's suggested that users first open Command Prompt (or Terminal), switch to the directory of the program set using `cd` command and then open some program by `python [Filename]` or `python -W ignore [Filename]`. In this way, it's easy check the returned information.
3. All programs must run after the user logs in the LoL client. 
4. All opened .py files can be aborted by Ctrl + C while running. (Press for any times you want, until the program exits.)
5. This program set provides some functions besides creating custom lobbies, just for entertainment. Anyone willing to make supplements and perfection is welcome!
	- **Declaration: Please name the subsequent customized programs in order, following the format `Customized Program [Number] - [Function].py`.**
	- Customized Program 01 **returns the connection information by lcu_driver library**.
	- Customized Program 02 refers to the **根据Json创建房间** button in the GUI LeagueLobby software by Mario. When using, users need first modify the values of parameters in create_custom_lobby function and then double-click the file after saving the change.
		- To check the returned lobby information after creating a lobby, please first open Command Prompt or Terminal and then type `python [Filename]` or `python -W ignore [Filename]`.
	- Customized Program 03 provides a basic tool for **exploration into LCU API**, which saves **formatted** returned result into `temporary data.txt` in the same directory, and also saves the variable into `temporary data.pkl` in the **binary** form in the same directory. Some reference requests are listed in this program. All available APIs are from [LCU Explorer](https://github.com/HextechDocs/lcu-explorer/releases/tag/1.2.0).
		- Please input according to the examples. <font color=#ff0000><b>Illegal input will cause the program to exit.</b></font> A legal input requires: 
			- Containing <ins>one or two</ins> spaces.
				- If there're two spaces, users may pass a request body subsequently.
			- Endpoint (The second string element of the list from the input string split by space) starting with a <ins>slash</ins>.
		- To view all LCU APIs in a web instead of in an APP, please visit [swagger](https://www.mingweisamuel.com/lcu-schema/tool/) or [LCU Swagger UI](https://swagger.dysolix.dev/lcu/). (For example, you may use Ctrl + F to search for certain API.)
	- Customized Program 04 is designed to **update `available-bots.xlsx` in the home directory**.
		- This workbook contains 3 sheets:
			- Sheet1 contains information of bot players **officially available** in Practice Tool lobbies.
			- Sheet2 contains information of bot players that **can be added** in Practice Tool lobbies.
				- Compared with Sheet1, Sheet2 includes information of all bot players in *Co-op vs. Ai* matches of intermediate difficulty.
			- Sheet3 contains information of **all champions** in League of Legends.
		- Usually users aren't needed to update the champion data. I'll keep updating it if any new champion is released.
		- This program can be run without logging into LoL client, but it only returns information of all champions.
		- This program involves the following data resources:
			- https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/{locale}/v1/champions/{championId}.json
			- https://ddragon.leagueoflegends.com/cdn/{version}/data/{locale}/champion.json
	- Customized Program 05 (☆) is designed to **search and export summoners' profile**.
		- This program supports queries based on <ins>summonerName</ins> and <ins>puuid</ins>.
		- Thanks to LCU API, even if a summoner sets its profile private, its whole match history and rank data can still be fetched.
		- This program supports command line arguments. Check these arguments through the command `python [filename] -h`.
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">CMD arguments</th>
						<th style="text-align:center;">Action</th>
						<th style="text-align:center;">Help message</th>
						<th style="text-align:center;">Value</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">-r<br>--reserve</td>
						<td style="text-align:center;">store_true</td>
						<td>Load a match even if it doesn't contain the main player</td>
						<td>None</td>
					</tr>
					<tr>
						<td style="text-align:center;">-rt<br>--reserve_text</td>
						<td style="text-align:center;">store_true</td>
						<td>Save a match even if it doesn't contain the main player</td>
						<td>None</td>
					</tr>
				</tbody>
			</table>
		- Files generated by this program are located under the "召唤师信息（Summoner Information）" folder.
		- The data resources required in this program are mainly from <ins>CommunityDragon database</ins>, and it's allowed to obtain these data resources **offline**. The release zip includes all necessary data resources. If these files are lost, when the user chooses to obtain the data resources offline, <ins>please create a folder named as `离线数据（Offline Data）` in the main directory, open the url of the corresponding data resources and then download them to this new folder.</ins>
		- Since Patch 13.22, **Riot ID** has taken the place of summoner name. Therefore, if a summoner's information can't be visited by its summonerName, **please add a "#" and the summoner's tagLine after the gameName.**
			- **Note:** Open a summoner's profile page in the League Client. Keep the mouse cursor stay on his/her gameName. You should see a window with the complete Riot ID with the postfixxed tagLine. Click to copy it. Paste it into the search bar on the top-right corner of the page to search this summoner.
		- This program supports the following saving modes:
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">Saving mode</th>
						<th style="text-align:center;">Definition</th>
						<th style="text-align:center;">Applicable product(s)</th>
						<th style="text-align:center;">Implementation steps</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">Complete saving</td>
						<td>Save all matches' information and timeline json files and export all match sheets</td>
						<td style="text-align:center;">lol<br>tft</td>
						<td>LoL:<br>1. At "Search LoL matches?" stage, <b>Enter any non-empty string</b> to choose yes<br>2. <b>Submit "3"</b> to search all matches<br>3. <b>Input any non-empty string</b> to specify the match begIndex and endIndex by yourself<br>4. When setting the match begIndex and endIndex, <b>press Enter directly</b><br>5. <b>Press Enter directly</b> to output json files of each match<br>6. After the program finishes calculating the number of sheets to be saved for each match, <b>input any non-empty string</b> to export all match sheets<br>TFT:<br>1. At "Search TFT matches?" stage, <b>input any non-empty string</b> to choose yes<br>2. <b>Press Enter directly</b> to output json files of each match<br>3. <b>Input any non-empty string</b> to confirm saving all matches' json files<br>4. After the program finishes calculating the number of sheets to be saved for each match, <b>input any non-empty string</b> to export all match sheets</td>
					</tr>
					<tr>
						<td style="text-align:center;">Complete loading</td>
						<td>Export all match sheets while not saving the information and timeline json files of any match</td>
						<td style="text-align:center;">lol<br>tft</td>
						<td>LoL:<br>5. <b>Input any non-empty string</b> to refuse outputting json files of each match<br>The other steps are the same as those of [Complete saving]<br>TFT:<br>1. At "Search TFT matches?" stage, <b>input any non-empty string</b> to choose yes<br>2. <b>Input any non-empty string</b> to refuse outputting json files of each match<br>3. After the program finishes calculating the number of sheets to be saved for each match, <b>input any non-empty string</b> to export all match sheets</td>
					</tr>
					<tr>
						<td style="text-align:center;">Bulk saving</td>
						<td>Save the information and timeline json files of matches recorded in API within a specified range of matchID and export all match sheets</td>
						<td style="text-align:center;">lol</td>
						<td>LoL:<br>1. At "Search LoL matches?" stage, <b>Enter any non-empty string</b> to choose yes<br>2. <b>Submit "3"</b> to search all matches<br>3. <b>Input any non-empty string</b> to specify the match begIndex and endIndex by yourself<br>4. When setting the match begIndex and endIndex, <b>input two integers split by space</b><br>5. <b>Press Enter directly</b> to output json files of each match<br>6. After the program finishes calculating the number of sheets to be saved for each match, <b>input any non-empty string</b> to export all match sheets</td>
					</tr>
					<tr>
						<td style="text-align:center;">Bulk loading</td>
						<td>Export sheets of matches recorded in API within a specified range of matchID while not saving their information and timeline json files</td>
						<td style="text-align:center;">lol</td>
						<td>LoL:<br>5. <b>Input any non-empty string</b> to refuse outputting json files of each match<br>The other steps are the same as those of [Bulk saving]</td>
					</tr>
					<tr>
						<td style="text-align:center;">Supplementary saving</td>
						<td>Save the information and timeline json files of the matches which haven't been saved to local before and export these match sheets</td>
						<td style="text-align:center;">lol<br>tft</td>
						<td>LoL:<br>1. At "Search LoL matches?" stage, <b>input any non-empty string</b> to choose yes<br>2. <b>Submit "3"</b> to search all matches<br>3. <b>Press Enter directly</b> to only search for the matches whose json files haven't been saved to local before<br>4. <b>Press Enter directly</b> to output json files of each match<br>5. After the program finishes calculating the number of sheets to be saved for each match, <b>input any non-empty string</b> to export all match sheets<br>TFT:<br>3. <b>Press Enter directly</b> to only save the matches which haven't been saved to local before<br>The other steps are the same as those of [Complete Saving]</td>
					</tr>
					<tr>
						<td style="text-align:center;">Supplementary loading</td>
						<td>Export sheets of matches whose information and timeline json files haven't been saved to local before, while not saving their information and timeline json files</td>
						<td style="text-align:center;">lol</td>
						<td>4. <b>Input any non-empty string</b> to output json files of each match<br>The other steps are the same as those of [Supplementary saving]</td>
					</tr>
					<tr>
						<td style="text-align:center;">List saving</td>
						<td>Save the information and timeline json files of matches in a match list and export these match sheets</td>
						<td style="text-align:center;">lol</td>
						<td>1. At "Search LoL matches?" stage, <b>input any non-empty string</b> to choose yes<br>2. <b>Input an integer list wrapped by square brackets and split by comma</b> as the matchID list<br>3. <b>Press Enter directly</b> to output json files of each match<br>4. After the program finishes calculating the number of sheets to be saved for each match, <b>input any non-empty string</b> to export all match sheets</td>
					</tr>
					<tr>
						<td style="text-align:center;">List loading</td>
						<td>Export sheets of matches in a specified match list, while not saving the information and timeline json files of any match in this list</td>
						<td style="text-align:center;">lol</td>
						<td>3. <b>Input any non-empty string</b> to refuse outputting json files of each match<br>The other steps are the same those of [List saving]</td>
					</tr>
					<tr>
						<td style="text-align:center;">Scanning saving</td>
						<td>Scan all the locally saved matches, search for the information and timeline of these matches, save the json files and export them to Excel</td>
						<td style="text-align:center;">lol</td>
						<td>1. At "Search LoL matches?" stage, <b>input any non-empty string</b> to choose yes<br>2. <b>Input the secret code "scan"</b> to scan the local files and obtain the matchIDs<br>3. <b>Press Enter directly</b> to start local recheck or <b>input any non-empty string</b> to return to Step 2<br>4. <b>Press Enter directly</b> to output json files of each match<br>5. After the program finishes calculating the number of sheets to be saved for each match, <b>input any non-empty string</b> to export all match sheets</td>
					</tr>
					<tr>
						<td style="text-align:center;">Scanning loading</td>
						<td>Scan all the locally saved matches, search for the information and timeline of these matches and export them to Excel while not saving the json files</td>
						<td style="text-align:center;">lol</td>
						<td>4. <b>Input any non-empty string</b> to refuse outputting json files of each match<br>The other steps are the same as those of [Scanning saving]</td>
					</tr>
				</tbody>
			</table>
			<b>Note:</b> [Scanning saving] and [Scanning loading] are jointly termed [Scan Mode] or [Local Recheck].
		- Under [Complete Saving] mode, the generated xlsx file contains 5 parts of sheets:
			- Profile (Single sheet)
			- Rank (Single sheet)
			- Ladders (Single sheet)
			- Champion Mastery (Single sheet)
			- Match history (Five sheets)
				- Recently played summoner (LoL)
				- Recently played summoner (TFT)
				- LoL match history
				- [Local Recheck] match history
				- TFT match history
			- Details for each match (At most three sheets for each match)
				- Game information
				- Game timeline
				- Game events
		- Scan mode ([Local Recheck]) notes: (For the definition of some terms, check the description of [corresponding commit](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived/commit/dc1cfd187caa619a80f70001d89f7f9c5db1892a).)
			- The user isn't advised to export the information and timelines of more than 1600 normal matches (or the information of 5000 Arena matches) using this program.
			- Right before running the scan mode, **please delete the xlsx workbook (into Recycle Bin) or rename it**, in case the original workbook is too big for this program to quickly read and export sheets into.
			- [Local Recheck] is only supported for **LoL** matches for now.
		- Every time the program exports a summoner's profile, if you need to sort out data based on the generated result, please modify the names of the sheets that you want to make changes, in case they would be overwritten and some data would be lost. For example, you may add " - Manual" after the names of the sheets to change.
		- If the original workbook is big enough, it's highly recommended that the user make a backup of the original workbook before the export, in case an unexpected interruption could lead to a broken workbook.
		- This program involves the following data resources:
			- https://ddragon.leagueoflegends.com/api/versions.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/summoner-spells.json
            - https://raw.communitydragon.org/{version}/cdragon/tft/{locale}.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/champion-summary.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/cherry-augments.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/items.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/perks.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/perkstyles.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/tftchampions.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/tftitems.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/companions.json
            - https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/tfttraits.json
		- This program relies on any encountered errors to update the exception handling code. Welcome for any developer to share the http errors when crawling the data 👏
	- Customized Program 06 is designed to **one-key start the TFT Tocker's Trial mode on PBE to gain 3000 RP**. A simple double-click will work.
		- Since Aug. 27th, 2023, TFT 1V0 mode has been unavailable.
	- Customized Program 07 is designed to **get information of items on sale in the store and collections of the main summoner**.
		- This program exports the information of store items and collections to `Store and Collections - {召唤师名称}.xlsx` in the directory of the main summoner.
		- The imagePath field of the store table refers to URLs related to **LCU API**, which can be accessed **only during when the League Client is running**. The first visit of these URLs requires a username and a password. Please look for <ins>a line that starts with "riot"</ins> at the beginning of this program's output. The username is <ins>"riot"</ins>, and the password is <ins>a string that follows "riot"</ins>.
			- The imagePath temporarily marked as <ins>default.png</ins> is actually inaccessible.
		- This program involves the following data resources:
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/companions.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/skins.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/statstones.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/summoner-emotes.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/summoner-icons.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/tftdamageskins.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/tftmapskins.json
			- https://raw.communitydragon.org/{version}/plugins/rcp-be-lol-game-data/global/{locale}/v1/ward-skins.json
	- Customized Program 08 is never expected to count the number of summoners on a server. (since the number is too large, let alone the brute-force traversal of summonerId)!
	- Customized Program 09 is designed to **search and export the existing game modes on the current server**.
		- Try running this program on multiple servers, and compare the available game modes on different servers. If lucky, you may find that on Chinese PBE server, you'll use Kai'Sa to solo with a bot player of intermediate difficulty in TFT Turbo 1v0.
	- Customized Program 10 is designed to **search for matches a specified summoner has played**. The user may combine its use with Customized Program 05.
	- Customized Program 11 is designed to **search summoners that have recently played with the specific summoner**.
		- A large part of code in this program is inherited from Customized Program 05, including the scan mode. Nevertheless, this program only outputs the result and doesn't change any intermediate files (txt and json files) generated by Customized Program 05.
		- This program supports command line arguments. Check these arguments through the command `python [filename] -h`.
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">CMD arguments</th>
						<th style="text-align:center;">Action</th>
						<th style="text-align:center;">Help message</th>
						<th style="text-align:center;">Value</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">-r<br>--reserve</td>
						<td style="text-align:center;">store_true</td>
						<td>Load a match even if it doesn't contain the main player</td>
						<td>None</td>
					</tr>
					<tr>
						<td style="text-align:center;">-ss<br>--save_self</td>
						<td style="text-align:center;">store_true</td>
						<td>Save the main summoner's data even if they're contained in a match</td>
						<td>None</td>
					</tr>
				</tbody>
			</table>
		- This program allows [Generate Mode] and [Detect Mode].
			- [Generate Mode] **saves information** of players that a specific player have played with in recent matches into the Sheet "Recently Played Summoners" **in the workbook** whose name is prefixxed with "Summoner Profile" and save 9 **bar charts** with regard to players' <ins>game time</ins> and <ins>match counts</ins>.
			- [Detect Mode] checks whether some players have been encountered before. Six situations are considered in this program. The core code **resemble** among different situations.
				1. In-lobby / During champ select / In-game
					- Information of <ins>summoners that the **main summoner** encounters during champ select or in-game</ins> in past matches will be returned in this situation. The format of output refers to that of each record in the match infrrmation table generated by Customized Program 05.
					- This mode supports checking rcently played summoners of the **user** (current summoner) and other players encountered during champ select stage or in game.
						**Note:** TFT matches do have champ select stage. Unfortunately, this stage lasts too shortly.
					- Considering temporariness of champ select, this mode will only generate a temporary file in the home directory.
					- The program generates the temporary file "Recently Played Summoner in Match {platformId}-{gameId}.xlsx" in this situation, where {platformId} represents the main summoner name and {gameId} represents a matchID.
				2. Friend list
					- Information of <ins>friends</ins> in past matches will be returned in this situation.
					- The program generates the temporary file "Recently Played Summoners in Friend List of {current_summonerName} - {platformId}.xlsx" in this situation, where {current_summonerName} represents the main summoner name and {platformId} represents the server.
				3. Friend requests
					- Information of <ins>players whom the user want to friend with and those who want to friend with the user</ins> in the past matches will be returned.
					- The program generates the temporary file "Recently Played Summoners in Friend Requests of {current_summonerName} - {platformId}.xlsx.xlsx" in this situation, where {current_summonerName} represents the main summoner name and {platformId} represents the server.
						- Compared with other situaions, sheet names under this situation include the friend request direction. "in" represents a player that want to friend with the user, and *vice versa*.
				4. Invitations
					- Information of <ins>players who invite or are invited by the user</ins> will be returned in this situation.
					- This program generates the temporary file "Recently Played Summoners in Invitations to and from {current_summonerName} - {platformId}.xlsx.xlsx" in this situation, where {current_summonerName} represents the main summoner name and {platformId} represents the server.
						- Compared with other situaions, sheet names under this situation include the invitation direction. "in" represents an inviter, and *vice versa*.
				5. Block list
					- Information of <ins>blocked players</ins> will be returned in this situation,
					- This program generates the temporary file "Recently Played Summoners in Block List of {current_summonerName} - {platformId}.xlsx.xlsx" in this situation, where {current_summonerName} represents the main summoner name and {platformId} represents the server.
				6. Any player list
					- Information of <ins>players in a list input by user</ins> in the past matches will be returned.
						- Each element of the input player list may be a <ins>summonerName</ins> or a <ins>puuid</ins>.
					- The program generates the temporary file "Recently Played Summoners in Specified Player List.xlsx" in this situation.
			- Under [Scan Mode], this program supports [Smurf Mode], which allows adding other accounts on the same server as smurf accounts.
			- Similar to Customized Program 05, the [Scan Mode] in this program only applies for **LoL** matches.
			- If for some reason (like the CMD window pops up and disappears immediately, or the match history fails to be fetched), the user fails to get whether the allies have been encountered before using [Detect Mode], the user can still [Single Check] whether there's any recently played summoner by inputting the in-game summoner name by hand.
				- Since PBE Patch 13.22, players on Riot servers can't be searches with only gameName. Because the loading screen only displays the gameName, the user may wait **until the game starts** to check the gameName and slogan on the **scoreboard**.
		- This program involves the same data resources as Customized Program 05.
	- Customized Program 12 is used to **sort out player loot information**.
		- The final result of this program is a **2-dimension table including a part of the field** to be saved into a workbook. **To get the generation path, please refer to Customized Program 05.**
		- This program only transforms and sorts out data. No data analysis is involved. If you have further needs, <ins>please analyze with Excel on your own</ins>.
	- Customized Program 13 is used to **fetch all ladder data in the current server**.
		- Files generated by this program are located under the "顶尖排位玩家（Ranked Apex）" folder.
		- The generated xlsx file contains 2 parts of sheets:
			- Split config (Double sheets)
				- Split config
				- Reward track
			- League ladders
				- Tier apex metadata (Single sheet)
				- Apex
					- Tier apex
						- Ranked solo/duo
						- Ranked Flex
						- Ranked TFT
						- Double Up (Workshop)
					- Rated apex
						- Hyper Roll
						- Arena
	- Customized Program 14 is used to **instantly enter a friend's party**.
		- Usage limits are added. <b>Please don't abuse the program and edit the code at will.</b>
		- This program might be as useful as how you think. If you're dying to be carried, I suggest you keep clicking where the "join party" will occur desperately while running this program.
	- Customized Program 15 is used to **let the users pick a same champion in a custom game**. This BUG has been fixed, so you may ignore this program.
	- Customized Program 16 is used to **simulate the behaviors related with chat service**.
		- Currently this program has the following features:
			- Export friend data
			- Manage friend groups
			- Chat
			- Export chat history
			- Manage friend list
			- Send lobby invitations
			- Manage received invitations
			- Spectate a game
			- Manage team voice
			- Manage block list
				- Custom URF special mode is planted into this feature for manaegement of group members. This mode is hidden.
	- Customized Program 17 is used to **sort out all game type config**. It's mainly used to configure the parameters of custom lobby creation request.
	- Customized Program 18 is used to **sort out all missions**.
		- You may check the <ins>PBE RP Bonus</ins> mission with this program.
	- Customized Program 19 is used to **simulate perk configuration and perk page operations in the League Client**.
		- Currently, this program provides the following functions:
			- Check all perk information
			- Check the recommended perk information of different champions, positions and maps
			- Manage perk pages
				- Export all pages
				- Check, edit and export single page
				- Toggle active page
				- Sort pages
				- Delete pages
	- Customized Program 20 is used to **summary multiple players' game stats at a time**.
		- This program combines the search function in Customized Program 05 and the gameflow phase detection function in Customized Program 11 and summarizes player stats in the following situations:
			- Allies with visible information during champ select stage
			- All players in game
			- All players in a previous match
		- While basic stats are output, some other indices are also output, which refer to:
			- Radar graph in LoL Helper Mobile
			- Common statistics in LoL Esports (KDA, Kill Participant, Gold per Minute, CS per Minute, Damage per Gold Ratio, etc.)
		- Data in certain format are added conditional formats in the exported workbook to improve intuitiveness.
			- KDA is output as a one-digit float.
			- Some LoL Esports statistics are output as three-digit floats.
			- Percentages are output as two-digit percentages.
			- Order cells are three-color scaled.
			- Win and lose result cells are colored based on formula. "VICTORY" is colored green and "DEFEAT" is colored red.
		- For convenience, this program supports command line arguments. Check these arguments through the command `python [filename] -h`.
			<table>
				<thead>
					<tr>
						<th style="text-align:center;">CMD arguments</th>
						<th style="text-align:center;">Action</th>
						<th style="text-align:center;">Help message</th>
						<th style="text-align:center;">Value</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<td style="text-align:center;">-e<br>--save_early</td>
						<td style="text-align:center;">store</td>
						<td>Export only the matches whose creation is earlier than the current queried match</td>
						<td>None</td>
					</tr>
					<tr>
						<td style="text-align:center;">-l<br>--locale</td>
						<td style="text-align:center;">store</td>
						<td>Set the language of constant dictionaries defined in the program. Only Simplified Chinese and English (US) are supported for now</td>
						<td>zh_CN (default)<br>en_US</td>
					</tr>
					<tr>
						<td style="text-align:center;">-os<br>--open_after_save</td>
						<td style="text-align:center;">store_true</td>
						<td>After saving a file, open it without program asking</td>
						<td>None</td>
					</tr>
					<tr>
						<td style="text-align:center;">--verbose</td>
						<td style="text-align:center;">store_true</td>
						<td>Print detailed match loading process and exception handling procedural hints</td>
						<td>None</td>
					</tr>
					<tr>
						<td style="text-align:center;">--nonverbose</td>
						<td style="text-align:center;">store_true</td>
						<td>Output key information only</td>
						<td>None</td>
					</tr>
				</tbody>
			</table>
	- Customized Program 21 is used to **simulate client operations at all gameflow phases**. It's aimed at handle urgent situations when the League Client isn't well performed.
		- <b>Declaration: This program doesn't involve any automatized operations.</b>
		- This program combines core functions of the previous 20 customized programs. To experience the whole feature, please make sure <ins>Customized Program 19</b> is under the same directory.
		- This program supports simulation at gameflow phases like <ins>unlogged, None, Lobby, Matchmaking, ReadyCheck, ChampSelect, InProgress, Reconnect, WaitingForStats, PreEndOfGame and EndOfGame</ins>. All supported operations are listed below, excluding the debugging function: (Suboperations of the same operation is only expanded at the first occurrence.)
			- Unlogged
				- Debug League Client endpoints
				- Manage the League Client task
					- Window management
						- Show the window
							- Minimize the window
							- Enable taskbar flashing
							- Resize the window
					- Process management
						- Launch ux
						- Temporarily close ux
						- Reload ux
						- Terminate ux (!)
			- None
				- Debug League Client endpoints
				- Create a lobby
					- Create a party
					- Create a custom lobby
					- Create through json
				- Handle invitations
				- Join party/lobby
					- Party
					- Custom lobby
					- Clash
				- Spectate a game
				- Chat
				- Manage the League Client task
			- Lobby
				- Debug League Client endpoints
				- Manage a party
					- Prepare before in queue
						- Select positions (Ranked and Nexus Blitz only)
						- Configure quickplay slot (Swiftplay only)
						- Configure subteam data (Arena only)
						- Toggle ready
						- TFT loadouts (TFT only)
					- Check friends leaderboard
					- Toggle party open/closed
						- Make party invite-only
						- Open party to friends
					- Change mode
						- Create a party
						- Create a custom lobby
						- Create through json
					- Find match
				- Manage a custom lobby
					- Add a bot
					- Remove a bot
					- Switch team
					- Switch spectate status (!)
					- Change mode
					- Start game
				- Invite to game
				- Chat
				- Manage members
					- Promote to party owner
					- Kick player from party
					- Change invite priviledge
						- Grant invites
						- Revoke invites
				- Print lobby information
				- Handle invitations
				- Join party/lobby
				- Exit the party/lobby
				- Manage the League Client task
			- MatchMaking
				- Debug League Client endpoints
				- Print matchmaking information
				- Chat
				- Handle invitations
				- Join party/lobby
				- Quit the queue
				- Manage the League Client task
			- ReadyCheck
				- Accept
				- Decline
				- Print the ready check information
				- Manage the League Client task
			- ChampSelect
				- Debug League Client endpoints
				- Swap
					- Pick order
						- Check
						- Send
					- Position
						- Check
						- Send
					- Ally champions
						- Check
						- Send
					- Available champion pool (Bench)
						- Check
						- Send
				- Select a champion
					- Decalre intent (unavailable)
					- Ban
					- Pick
					- Reroll
				- Prepare loadouts
					- Perks (Need support from Customized Program 19)
					- Summoner spells
					- Skin
					- Ward skin
					- Emote
					- Summoner icon
					- Nexus finisher
					- Banner
					- Crest
					- Tournament trophy
				- Mute players
				- Chat
				- Others
					- Unlock battle boost
					- Toggle favorite champions on different positions
					- Clear muted players
					- Exit the champ select stage
				- Output the champ select session
				- Manage the League Client task
			- InProgress
				- Chat with friends
				- Manage the League Client task
			- Reconnect
			- WaitingForStats
			- PreEndOfGame
				- Debug League Client endpoints
				- Honor players
				- Check the number of votes
				- Not this time
				- Print honor ballot information
				- Print current sequence event
				- Chat
				- Manage the League Client task
			- EndOfGame
				- Debug League Client endpoints
				- Check champion mastery updates
				- Check stats block
					- LoL
					- TFT
				- Chat
				- Play again
				- Dismiss
				- Recall honor vote phase (!)
				- Manage the League Client task
			- Other phases
		- Without specific explanation, submit "0" to return to the last step.
		- This program **creates cache** under the "cache" folder to speed up data resource loading.
			- The local cache expires after <ins>24 hours</ins>.
			- Users may reload data resources to refresh local cache.
			- Reading cache is expected to save 10 to 30 seconds of data resource loading.
	- `清除临时文件.bat` is used to **remove temporary files generated by customized programs**. At present it can delete temporary files from customized programs 03, 05, 10, 11, 17, 19, 20 and 21.
	- `召唤师信息文件格式转换.bat` is used to **rename the format of data files generated by Customized Program 05 into ".txt" or ".json"**.
		- Renaming a number of data files may results in the slow performance of Explorer, so please think twice to use this program.
		- Since the scripts of this program contain Chinese characters, **please run `chcp 65001` in Command Prompt** before running this program.
		- Within expectation, the prompt "1 files(s) moved" will constantly pop up in Command Prompt. [Everything App](https://www.voidtools.com/en-us/) is suggested for checking the number of txt files in the folder "召唤师信息（Summoner Information）".
			- Try typing `"{folderPath}" .txt` in the search bar of Everything App to check the txt file list of a folder. You should see the number of the txt files at the bottom-left corner of the Everything window.
				- An example of {folderPath}: `C:\Users\19250\Desktop\英雄联盟自定义房间创建\召唤师信息（Summoner Information）`.
	- Item Program is used to **generate item information table of all versions**.
		- Data resources are from <ins>DataDragon database> and <ins>CommunityDragon database</ins>.
		- This program supports **all languages supported by League of Legends**.
		- This program supports **all versions** archived by these two databases.
		- Each generated table can be divided into 5 parts:
			- Metadata
			- Classification
			- In-game tooltip
			- Map availability (not available in item data from CommunityDragon)
			- Basic stats
		- If you want to freeze cells and enable autofilter in batch, you can write a Macro to fix the top rows of all sheets. The following is a demonstration, taking Microsoft Excel as an example.
			1. In Microsoft Excel, click "File" - "Options" - "Customize Ribbon". Tick on "Developer" and click "OK".
			2. Click "Developer" tab and then click "Visual Basic" to open the VBA editor.
			3. In "Project - VBAProject" subwindow of the new window, right click "VBAProject ({Workbook Name})". Then click "Insert" - "Module".
			4. Paste the following code into the new module subwindow:
			```vba
			Sub FreezeAndFilterTopRowsAndColumns()
				Dim ws As Worksheet
				Dim lastCol As Long
				For Each ws In ThisWorkbook.Worksheets
					ws.Activate ' Select this sheet
					If ws.AutoFilterMode Then ws.AutoFilterMode = False ' Remove any existing autofilter
					ActiveWindow.FreezePanes = False ' Disable the current pane freezing
					ActiveWindow.SplitColumn = 0 ' Remove any existing column split
					ActiveWindow.SplitRow = 0 ' Remove any existing row split
					ws.Range("E3").Select ' Freeze the first two rows and four columns
					ActiveWindow.FreezePanes = True ' Freeze the panes
					ws.Range("A2").Select ' Select A2 cell
					lastCol = ws.Cells(2, ws.Columns.Count).End(xlToLeft).Column ' Determine the last column that has content in Line Two
					ws.Range(ws.Cells(2, 1), ws.Cells(2, lastCol)).Select ' Select the range from A2 to the last cell that has content in the same row
					Selection.AutoFilter ' Apply autofilter to the selected range
					ws.Range("A1").Select ' Cursor initialization - Select A1 cell
				Next ws
			End Sub
			```
			Note: The above macro applies to all sheets. If you want it to only apply to certain sheets, you need to add a <ins>condition statement</ins> on the sheet attributes **right below the for-statement** and indent the subsequent code that do operations backward by one layer.
			5. Close VBA editor and return to the Excel window. Click "Macro" in "Developer" tab.
			6. Select "FreezeTopRowsAndSelectA1" and click "Run".
			7. If you want to save the macro while saving the changes, please save this workbook as ".xlsm" format.
		- Here're some other macros that might be useful.
			- Clear format
			```vba
			Sub ClearFormat()
				Dim ws As Worksheet
				Dim lastCol As Long
				For Each ws In ThisWorkbook.Worksheets
					If InStr(ws.Name, "cdragon") > 0 Or ws.Name = "pbe" Or ws.Name = "latest" Then ' Select sheets produced when fetching CommunityDragon database
						ws.Activate
						If ws.AutoFilterMode Then ws.AutoFilterMode = False
						ActiveWindow.FreezePanes = False
						ActiveWindow.SplitColumn = 0
						ActiveWindow.SplitRow = 0
						ws.Range("A1").Select
					End If
				Next ws
			End Sub
			```
	- To make it convenient for users to **look up LoL official terms**, a translation program `trans.py` is added in the home directory.
		- Each run of this program supports summarizing and saving the translation data resources of a language. It also allows downloading data resources in all languages within one run.
		- Since this program is only intended to correct the terms, the involved data resources are only used for program development, instead of the release. So, it's highly recommended that users run this program in the cloned repository folder, instead of the folder extracted from compressed files in Release.
	- Customized Programs <ins>05, 11, 13, 16, 19, 20 and 21</ins> **save content displayed in terminal into local logs** while running. You can check them under the "<ins>日志（Logs）</ins>" folder.
	- To let user **understand the structure of the large dataframes**, a workbook `Customized Program Main Dataframe Structure.xlsx` is added in the home directory to illustrate how the dataframes are organized.
		- The following is the illustration on the structure of `LoLGame_info_df` in Customized Programs 05 and 20, `recent_LoLPlayers_df` in Customized Programs 11 and 16 and `LoLGame_stat_header` in Customized Program 20, to explain some settings, which won't be repeated in the following context:
			- There're 6 columns in the sheets `05 - LoLGame_info_header`, `11 - LoLGame_info_header`, `16 - LoLGame_info_header` and `20 - LoLGame_stat_header`, and the first 3 columns are the **main data area**.
				- `Index` represents the index of the keys of the dictionary variable `LoLGame_info_data`.
				- `Key` represents the keys of the dictionary variable `LoLGame_info_data`.
				- `Value` represents the values of the dictionary variable `LoLGame_info_data`.
				- `DirectlyImport?` represents whether to analyze the data to be transformed from LCU API into the dataframe. A tick means reference without any change.
				- `OutputOrder` represents the order to arrange the data when they're output into a worksheet.
				- `DisplayOrder` represents the order to arrange the data when they're displayed in a webpage. Only the header sheets whose corresponding tables are to be displayed in a webpage have this column.
			- 9～10 colors are used to divide the main data area in these sheets.
				- Data not filled with any color mean `Key` doesn't serve as the index of any variables of LCU API.
				- Data in the light green area mean `Key` is the index of the variable `LoLGame_info`.
				- Data in the light blue area mean `Key` is the index of `LoLGame_info["participantIdentities"][participantId]`.
				- Data in the dark blue area mean `Key` is the index of `LoLGame_info["participantIdentities"][participantId]["player"]`.
				- Data in the dark green area mean `Key` is the index of `LoLGame_info["participants"][participantId]`.
				- Data in the orange area mean `Key` is the index of `LoLGame_info["participants"][participantId]["stats"]`.
				- Data in the purple area mean `Key` comes from `LoLGame_info["teams"][teamId]["bans"]`.
					- Note that no key in this area exists to be the direct index.
				- Data in the yellow area mean `Key` is the direct index of `LoLGame_info["participants"][participantId]["timeline"]`.
				- Data in the pink area mean `Key` doesn't serve as the index of any variables of LCU API.
					- Currently, the purple area only contains `ally?`, a judgement whether the queried player is an ally of the main player. In the exported sheet, a tick means the queried player is the ally of the main player.
				- Data in the grey area mean `Key` comes from `LoLGame_info["participants"][participantId]["stats"]`.
					- Values of this part of keys are obtained by comparison and mathematical calculation.
			- Some keys are colored white. These keys don't belong to the indices of any variable in LCU API, but actually come from them. For example, `gameModeName` never occurs in the json object of the game information, but actually originates from `LoLGame_info` and corresponds to the key `"gameMode"`.
			- <b>To obtain the output/display order lists, users need only arrange the table according to the ascending order of `OutputOrder` or `DisplayOrder` and then copy the cells in `Index` column.</b>
		- `LoLChampions_df` in Customized Programs 04 and 21:
			- 8 colors are used to divide the main data area in the sheet `04 - LoLChampions_header (LCU)` and `21 - LoLChampions_header`:
				- Data not filled with any color mean `Key` is the direct index of `LoLChampions[championId]`.
				- Data in the light blue area mean `Key` comes from `LoLChampions[championId]["ownership"]`.
				- Data in the deep blue area mean `Key` comes from `LoLChampions[championId]["ownership"]["rental"]`.
				- Data in the light green area mean `Key` comes from `LoLChampions[championId]["roles"]`.
				- Data in the orange area mean `Key` comes from `LoLChampions[championId]["tacticalInfo"]`.
				- Data in the pink area mean `Key` comes from `LoLChampions[championId]["passive"]`.
				- Data in the deep green area mean `Key` comes from `LoLChampions[championId]["spells"][spell_index]`.
				- Data in the yellow area mean `Key` comes from the endpoint `/lol-perks/v1/recommended-champion-positions`.
			- 7 colors are used to divide the main data area in the sheet `04 - LoLChampions_header (ddr)`.
				- Data not filled with any color mean `Key` is the direct index of `LoLChampions[championId]`.
				- Data in the light blue area mean `Key` comes from `LoLChampions[championId]["image"]`.
				- Data in the light green area mean `Key` comes from `LoLChampions[championId]["tags"]`.
				- Data in the deep blue area mean `Key` comes from `LoLChampions[championId]["stats"]`.
				- Data in the orange area mean `Key` is the index of `LoLChampions[championId]["stats"]`.
				- Data in the pink area mean `Key` comes from `LoLChampions[championId]["spells"][spell_index]`.
				- Data in the deep green area mean `Key` comes from `LoLChampions[championId]["passive"]`.
			- 7 colors are used to divide the main data area in the sheet `04 - LoLChampions_header (cdr)`.
				- Data not filled with any color mean `Key` is the direct index of `LoLChampions[championId]`.
				- Data in the light blue area mean `Key` comes from `LoLChampions[championId]["tacticalInfo"]`.
				- Data in the light green area mean `Key` comes from `LoLChampions[championId]["playStyleInfo"]`.
				- Data in the deep blue area mean `Key` comes from `LoLChampions[championId]["info"]`.
				- Data in the deep green area mean `Key` comes from `LoLChampions[championId]["roles"]`.
				- Data in the orange area mean `Key` comes from `LoLChampions[championId]["passive"]`.
				- Data in the pink area mean `Key` comes from `LoLChampions[championId]["spells"][spell_index]`.
		- `mastery_df` in Customized Program 05:
			- 3 colors are used to divide the main data area in the sheet `05 - mastery_header`.
				- Data in the blue area mean `Key` is the direct index of the variable `mastery[champion_iter]`.
					- Keys in white only include `champion` and `alias`, representing the titles and aliases of champions, respectively. Only championIds are provided in LCU API.
				- Data in the light green area mean `Key` comes from `mastery[champion_iter]["nextSeasonMilestone"]`.
				- Data in the deep purple area mean `Key` comes from `mastery[champion_iter]["nextSeasonMilestone"]["rewardConfig"]`.
		- `ranked_df` in Customized Program 05:
			- `Key` in the sheet `05 - ranked_header` can all be the index of `ranked["queues"][id]`.
			- Note that redundancy exists in the `OutputOrder` column. The essential reason for this is that the tier of TFT turbo and that of other rank modes are recorded into 2 variables separately, while the two tiers are expected to be stored in a single column. Therefore, the `OutputOrder` of some keys are the same.
		- `ladders_df` in Customized Program 05:
			- 4 colors are used to divide the main data area in the sheet `05 - ladders_header`.
				- Data not filled with any color mean `Key` is the direct index of `ladders[ladderId]`.
				- Data in the light bluea area mean `Key` is the index of `ladders[ladderId]["divisions"][divisionId]["standings"][standingId]`.
				- Data in the light green area mean `Key` is the index of the endpoint `/lol-summoner/v2/summoners/puuid/{puuid}`.
				- Data in the orange area mean `Key` doesn't serve as the index of any variables of LCU API.
		- `LoLHistory_df` in Customized Programs 05 and 11:
			- 6 colors are used to divide the main data area in the sheets `05 - LoLHistory_header` and `11 - LoLHistory_header`.
				- Data not filled with any color mean `Key` doesn't serve as the index of any variables of LCU API.
				- Data in the light blue area mean `Key` is the index of `LoLHistory["games"]["games"]`.
				- Data in the light green area mean `Key` is the direct index of `LoLHistory["games"]["games"]["participantIdentities"][0]["player"]`.
				- Data in the orange area mean `Key` is the index of `LoLHistory["games"]["games"]["participants"][0]`.
				- Data in the dark green area mean `Key` is the index of `LoLHistory["games"]["games"]["participants"][0]["stats"]`.
				- Data in the purple area mean `Key` is the direct index of `LoLHistory["games"]["games"]["participants"][0]["timeline"]`.
		- `LoLGame_leaderboard_df` and `TFTGame_leaderboard_df` in Customized Program 05 and `social_leaderboard_df` in Customized Program 20:
			- 2 colors are used to divide the main data area in sheets `05 - LoLGame_leaderboard_header`, `05 - TFTGame_leaderboard_header` and `20 - social_leaderboard_header`.
				- Data in the blue area mean `Key` is the index of `participantInfo`.
				- Data not filled with any color mean `Key` is the index of `participant_leaderboard`.
		- `LoLGame_timeline_df` in Customized Program 05:
			- 4 colors are used to divide the main data area in the sheet `05 - LoLGame_timeline_header`.
				- Data in the blue area mean `Key` is the index of `frames[frameId]`.
				- Data in the grey area mean the value corresponding to `Key` is generated automatically and isn't related to LCU API.
				- Data in the green area mean `Key` comes from `LoLGame_info`.
				- Data in the orange area mean `Key` is the index of `frames[frameId]["participantFrames"][participantId]`.
		- `LoLGame_event_df` in Customized Program 05:
			- The main data area in the sheet `05 - TFTHistory_header` isn't filled with any color.
				- Keys in dark red mean `Key` is the direct index of the variable `events[timestamp]`.
				- Some keys are colored black. These keys don't belong to the indices of any variable in LCU API, but actually come from them. For example, `item` never occurs in the json object of the game information, but actually originates from `LoLGame_timeline["frames"]["events"][eventId]` and corresponds to the key `"itemId"`.
		- `TFTHistory_df` in Customized Program 05, "recent_TFTPlayers_df` in Customized Programs 11 and 16 and `TFTGame_stat_df` in Customized Program 20:
			- 5 colors are used to divide the main data area in the sheets `05 - TFTHistory_header`, `11 - TFTHistory_header` and `16 - TFTGame_stat_header`.
				- Data not filled with any color mean `Key` doesn't serve as the index of any variables of LCU API.
				- Data in the sky blue area mean `Key` is the index of `TFTHistory[gameIndex]["json"]`.
				- Data in the green area mean `Key` is the index of `TFTHistory[gameIndex]["json"]["participants"]`.
				- Data in the pink area mean the first half of `Key` is the index of `TFTHistory[gameIndex]["json"]["participants"][participantId]["traits"]`, while the second half is the index of `TFTHistory[gameIndex]["json"]["participants"][participantId]["traits"][trait_index]`.
				- Data in the dark blue area mean the first part of `Key` is the index of `TFTHistory[gameIndex]["json"]["participants"][participantId]["units"]`.
					- For `Key` whose index is between 129～183, the second part is the direct index of `TFTHistory[gameIndex]["json"]["participants"][participantId]["units"][unit_index]`.
					- For `Key` whose index is greater than or equal to 184, the second part comes from `TFTHistory[gameIndex]["json"]["participants"][participantId]["units"][unit_index]["items"]`, and the third part is the direct index of `TFTHistory[gameIndex]["json"]["participants"][participantId]["units"][unit_index]["items"][item_index]`.
			- The only difference of the contents between the sheet `05 - TFTGame_info_header` and the sheet `05 - TFTHistory_header` is the first 9 lines.
		- `catalog_df` in Customized Program 07:
			- 3 colors are used to divide the main data area in the sheet `07 - catalog_header`. `Item` denodes any element in `catalogList`.
				- Data not filled with any color mean `Key` is the direct index of the variable `item`.
				- Data in the blue area mean `Key` comes from the index of `item["prices"][priceId]`.
				- Data in the green area mean `Key` comes from `item["prices"][priceId]["sale"]`.
		- `store_df` in Customized Program 07:
			- 5 colors are used to divide the main data area in the sheet `07 - store_header`. `item` denodes any element in `store`.
				- Data not filled with any color 
		- `collection_df` in Customized Programs 07 and 21:
			- 2 colors are used to divide the main data area in the sheets `07 - collection_header` and `21 - collection_header`. `Item` denodes any element in `catalogList`.
				- Data not filled with any color mean `Key` is the direct index of the variable `item`.
				- Data in the blue area mean `Key` is the index of `item["payload"]`.
		- `queues_df` in Customized Programs 09 and 20:
			- 4 colors are used to divide the main data area in the sheets `09 - queues_header` and `20 - queues_header`.
				- Data in the blue area mean `Key` is the direct index of the variable `queues[id]`.
				- Data in the orange area mean `Key` is the index of the variable `queues[id]["gameTypeConfig"]`.
				- Data in the blue area mean `Key` is the index of the variable `queues[id]["queueRewards"]`.
		- `recent_players_metaDf` in Customized Program 11:
			- The main data area in the sheet `11 - recent_players_metadata_he` (`11 - recent_players_metadata_header`) isn't filled with any color.
				- `Key` is the direct index of the variable `recent_players_metadata_list`.
		- `player_loot_df` in Customized Program 12:
			- No color is used to divide the main data area in the sheet `12 - player_loot_header`, because these keys are all indices of `player_loot[i]`.
		- `splits_info_df` in Customized Program 13:
			- 4 colors are used to divide the main data area in the sheet `13 - splits_info_header`.
				- Data in the blue green area mean `Key` comes from `splitsConfig["splits"][splitId]`.
				- Data in the light green area mean `Key` comes from `splitsConfig["splits"][splitId]["victoriousSkinRewardGroup"]`.
				- Data in the orange area mean `Key` comes from `splitsConfig["splits"][splitId]["victoriousSkinRewardGroup"]["splitPointsByHighestSeasonTier"]`
		- `rewardTrack_df` in Customized Program 13:
			- 3 colors are used to divide the main data area in the sheet `13 - rewardTrack_header`.
				- Data in the light blue area mean `Key` is the index of `splitsConfig["splits"][splitId]`.
				- Data in the orange area mean the value corresponding to `Key` is generated automatically and isn't related to LCU API.
				- Data in the light green area mean `Key` is the index of `splitsConfig["splits"][splitId]["rewardTrack"][rewardTrackId]["rewards"][rewardId]`.
		- `challenger_ladders_metadata_df` in Customized Program 13:
			- 2 colors are used to divide the main data area in the sheet `13 - challenger_ladders_metadat` (`13 - challenger_ladders_metadata_header` in full form).
				- Data in the light blue area mean `Key` is the index of `ladders`.
				- Data in the light green area mean `Key` is the index of `ladders["divisions"][divisionId]`.
		- `ladders_df["challenger_ladder"][queueType]` in Customized Program 13:
			- 2 colors are used to divide the main data area in the sheet `13 - challenger_ladders_header`.
				- Data not filled with any color mean `Key` is the index of `ladders["divisions"][divisionId]["standings"][standingId]`.
				- Data in the light blue area mean `Key` is the index of the endpoint `/lol-summoner/v2/summoners/puuid/{puuid}`.
		- `ladders_df["topRated_ladder"][queueType]` in Customized Program 13:
			- 2 colors are used to divide the main data area in the sheet `13 - topRated_ladders_header`.
				- Data not filled with any color mean `Key` is the direct index of `ladders["standings"][standingId]`.
				- Data in the light blue area mean `Key` is the index of the endpoint `/lol-summoner/v2/summoners/puuid/{puuid}`.
		- `friend_hovercard_df` in Customized Program 16:
			- 4 colors are used to divide the main data area in the sheet `16 - friend_hovercard_header`. `friend` denodes any element in `friends`.
				- Data in the blue area mean `Key` is the index of the variable `friend`.
				- Data in the light green area mean `Key` is the index of `friend["lol"]`.
				- Data in the orange area mean the second half of `Key` is the index of `eval(friend["lol"]["pty"])`.
				- Data in the green area mean the second half of `Key` is the index of `eval(friend["lol"]["regalia"])`.
		- `friend_hovercard_df_simple` in Customized Program 16:
			- The main data area in the sheet `16 - friend_hovercard_header_si` (`16 - friend_hovercard_header_simple`) isn't filled with any color. `friend` denodes any element in `friends`.
				- `Key` is the direct index of the variable `friend`.
		- `friend_groups_df` in Customized Program 16:
			- The main data area in the sheet `16 - friend_groups_header` isn't filled with any color. `group` denodes any element in `friend_groups`.
				- `Key` is the direct index of the variable `group`.
		- `conversation_df` in Customized Programs 16 and 21:
			- The main data area in the sheets `16 - conversation_header` and `21 - conversation_header` isn't filled with any color. `conversation` denodes any element in `conversations`.
				- `Key` is the direct index of the variable `conversation`.
		- `message_df` in Customized Program 16:
			- The main data area in the sheet `16 - message_header` isn't filled with any color. `message` denodes any element in `messages`.
				- `Key` is the index of the variable `message`.
					- `Key` whose index is less than 9 is the direct index of the variable `message`.
					- The second half of `Key` whose index is greater than or equal to 9 comes from `get_info` function.
		- `friend_request_df` in Customized Program 16:
			- The main data area in the sheet `16 - friend_request_header` isn't filled with any color. `friend_request` denodes any element in `friend_requests`.
				- `Key` is the index of the variable `friend_request`.
					- `Key` whose index is less than 10 is the direct index of the variable `friend_request`.
					- The second half of `Key` whose index is greater than or equal to 9 is the direct index of `summonerIcons[friend_request["icon"]]`.
		- `party_df` in Customized Program 16:
			- 4 colors are used to divide the main data area in the sheet `16 - party_header`. `party` denodes any element in `parties`.
				- Data in the blue area mean `Key` is the direct index of the variable `party`.
				- Data in the light green area mean the second half of `Key` is the direct index of `queues[party["queueId"]]`.
				- Data in the orange area mean `Key` comes from `party`.
				- Data in the yellow area mean `Key` doesn't serve as the index of any variables of LCU API.
					- Currently, the purple area only contains `full?`, a judgement whether the party is full. In the exported sheet, a tick means the party is full.
		- `invid_df` in Customized Programs 16 and 21:
			- 3 colors are used to divide the main data area in the sheets `16 - invid_header` and `21 - invid_header`. `invid` denodes any element in `receivedInvitations`.
				- Data in the blue area mean `Key` is the index of the variable `invid`.
				- Data in the light green area mean `Key` is the direct index of `invid["gameConfig"]`.
				- Data in the orange area mean the second half of `Key` comes from `queues`.
		- `muted_player_df` in Customized Program 16:
			- The main data area in the sheet `16 - player_mute_header` isn't filled with any color. `muted_player` denodes any element in `muted_players`.
				- `Key` is the index of the variable `muted_player`.
					- `Key` whose index is less than 5 is the direct index of the variable `muted_player`.
					- `Key` whose index is greater than or equal to 5 comes from `get_info` function.
		- `champSelect_team_df` in Customized Program 16 and `players_df` in Customized Program 21:
			- The main data area in the sheets `16 - champSelect_team_header`, `20 - champSelect_players_header` and `21 - champSelect_players_header` isn't filled with any color. `player` denodes any element in `players`.
				- `Key` is the index of the variable `player`.
		- `captureDevices_df` in Customized Program 16:
			- The main data area in the sheet `16 - captureDevices_header` isn't filled with any color. `device` denotes any value in `captureDevices`.
				- `Key` is the direct index of the variable `device`.
		- `voiceSettings_df` in Customized Program 16:
			- The main data area in the sheet `16 - voiceSettings_header` isn't filled with any color.
				- `Key` is the index of the variable `device`.
					- `Key` whose index is less than 12 is the direct index of the variable `device`.
					- `Key` whose index is greater than or equal to 12 comes from `captureDevices`.
			- This dataframe uses a legacy creation method. Refer to the definition of `info_data` in Customized Program 05.
		- `participant_record_df` in Customized Program 16:
			- The main data area in the sheet `16 - participant_record_header` isn't filled with any color. `participant` denodes any element in `participant_records`.
				- `Key` is the index of the variable `participant`.
					- `Key` whose index is less than 8 is the direct index of the variable `participant`.
					- `Key` 9 and 10 come from `get_info` function.
		- `blockList_df` in Customized Program 16:
			- The main data area in the sheet `16 - blockList_header` isn't filled with any color. `player` denodes any element in `blockList`.
				- `Key` is the index of the variable `player`.
					- `Key` whose index is less than 8 is the direct index of the variable `player`.
					- The second half `Key` is the index of the data resource that the first half represents.
		- `gametype_config_df` in Customized Program 17:
			- The main data area in the sheet `17 - gametype_config_header` isn't filled with any color. `config` denotes any element in `gametype_config`.
				- `Key` is the direct index of the variable `config`.
		- `mission_df` in Customized Program 18:
			- 6 colors are used to divide the main data area in the sheet `18 - mission_header`. `mission` denotes any element in `missions`.
				- Data not filled with any color mean `Key` is the index of `mission`.
				- Data in the blue area mean the second half of `Key` is the direct index of `mission["display"]`.
				- Data in the light blue area mean `Key` comes from `mission["metadata"]`.
				- Data in the deep blue area mean the second half of `Key` is the direct index of `mission["rewardStrategy"]`.
				- Data in the organge area mean `Key` comes from `mission["objective"][objectiveId]`.
				- Data in the purple area mean the second half of `Key` comes from `objective`.
				- Data in the blue, light green, deep green and purple areas are handled by the same code frame.
		- `objective_group_df` in Customized Program 18:
			- 2 colors are used to divide the main data area in the sheet `18 - objective_group_header`. `objective` denotes any element in `objectives`. `objectiveGroup` denotes any element in `objective["objectives"]`.
				- Data not filled with any color mean `Key` is the index of `objective`.
				- Data in the blue area mean the second half of `Key` is the index of `objectiveGroup`.
		- `perk_df` in Customized Program 19:
			- The main data area in the sheet `19 - perk_header` isn't filled with any color. `perk` denotes any element inf `perks`.
				- `Key` is the index of `perk`.
		- `recommendedPage_df` in Customized Program 19:
			- 3 colors are used to divide the main data area in the sheet `19 - recommendedPage_header`. `page` denotes any element in `recommendedPages`.
				- Data not filled with any color mean `Key` is the index of `page`.
				- Data in the blue area mean the second half of `Key` is the direct index of `page["keystone"]`.
				- Data in the green area mean `Key` comes from `page["perks"][perkId]`.
		- `perkPage_df` in Customized Programs 19 and 21:
			- 3 colors are used to divide the main data area in the sheets `19 - perkPage_header` and `21 - perkPage_header`. `page` denotes any element in `perkPages`.
				- Data not filled with any color mean `Key` is the index of `page`.
				- Data in the blue area mean the second half of `Key` is the direct index of `page["pageKeystone"]`.
				- Data in the green area mean `Key` comes from `page["uiPerks"][pageId]`.
		- `inGame_players_df` in Customized Program 20:
			- 2 colors are used to divide the main data area in the sheet `20 - inGame_players_header`. `player` denotes any element in `teamOne + teamTwo`. `loadout` denotes `player`'s loadout.
				- Data not filled with any color mean `Key` is the index of `player`.
				- Data in the blue area mean `Key` is the index of `loadout`.
		- `process_df` in Customized Program 20:
			- 2 colors are used to divide the main data area in the sheet `20 - process_header`.
				- Data not filled with any color mean `Key` doesn't serve as the index of any variables.
				- Data in the blue area mean `Key` is the direct index of `parent` and `child`.
		- `swaps_df` in Customized Program 21:
			- The main data area in the sheet `21 - swaps_header` isn't filled with any color.
				- `Key` is the direct index of the variable `swap`.
		- `custom_game_df` in Customized Program 21:
			- The main data area in the sheet `21 - custom_game_header` isn't filled with any color. `lobby` denotes any element in `custom_lobbies`.
				- `Key` is the index of `lobby`.
		- `skins_df` in Customized Program 21:
			- 6 colors are used to divide the main data area in the sheet `21 - skins_header`. `skin` denotes any element in `championSkins.values()`. `skin_flat` denotes any element in `skins_flat.values()`.
				- Data not filled with any color mean `Key` is the direct index of `skin["emblems"]`.
				- Data in the light green area mean `Key` comes from `skin["emblems"]`.
					- The latter half of `Key` No. 29 and 30 is the direct index of `skin["emblems"]`.
					- The latter half of `Key` No. 31 and 32 is the direct index of `skin["emblems"]["emblemPath"]`.
				- Data in the deep green area mean the latter half of `Key` is the direct index of `skin["questSkinInfo"]`.
				- Data in the yellow area mean `Key` comes from `skin_flat`.
					- `Key` No. 41～44 is the direct index of `skin_flat`.
					- The latter half of `Key` No. 45～47 is the direct index of `LoLChampions[skin_flat["championId"]]`.
				- Data in the light blue area mean the latter half of `Key` is the direct index of `skin_flat["ownership"]`.
				- Data in the deep blue area mean the third part of `Key` is the index of `skin_flat["ownership"]["rental"]`.
		- `grid_champion_df` in Customized Program 21:
			- 2 colors are used to divide the main data area in the sheet `21 - grid_champion_header`. `champion` denotes any element in `grid_champions`.
				- Data not filled with any color mean `Key` is the index of `champion`.
				- Data in the blue area mean `Key` is the direct index of `champion["selectionStatus"]`.
		- `grid_champion_df` in Customized Program 21:
			- The main data area in the sheet `21 - grid_champion_header` isn't filled with any color. `player` denotes any element in `muted_players`.
				- `Key` is the index of `player`.
					- `Key` No. 0～3 is the direct index of the variable `player`.
					- `Key` No. 4 and 5 is the direct index of `player_info["body"]`.
		- `social_leaderboard_df` in Customized Program 21:
			- The main data area in the sheet `21 - social_leaderboard_header` isn't filled with any color. `player` denotes any element in `social_leaderboard["rowData"]`.
				- `Key` is the index of `player`.
					- `Key` No. 0～15 is the direct index of the variable `player`.
					- `Key` No. 16 and 17 is the direct index of `summonerIcons[player["profileIconId"]]`.
		- `availableBot_df` in Customized Program 21:
			- 2 colors are used to divide the main data area in the sheet `21 - availableBot_header`.
				- Data not filled with any color mean `Key` is the direct index of the variable `bot`.
				- Data in the blue area mean `Key` is the direct index `LoLChampions[bot["id"]]`.
		- `member_df` in Customized Program 21:
			- The main data area in the sheet `21 - member_header` isn't filled with any color. `member` denotes any element in `members`.
				- `Key` is the index of `members`.
		- `ballot_player_df` in Customized Program 21:
			- The main data area in the sheet `21 - ballot_player_header` isn't filled with any color. `player` denotes any element in `honor_ballot["eligibleAllies"] + honor_ballot["eligibleOpponents"]`.
				- `Key` is the index of `player`.
		- `eog_mastery_update_df` in Customized Program 21:
			- The main data area in the sheet `21 - eog_mastery_update_header` isn't filled with any color.
				- `Key` is the index of `mastery_updates`.
					- `Key` No. 0～18 is the direct index of `mastery_updates`.
					- The latter half of `Key` No. 19～21 is the direct index of `LoLChampions[mastery_updates["championId"]]`.
					- The latter half of `Key` No. 22 and 23 is the direct index of `player_info["body"]`.
		- `eog_stat_metaDf_lol` in Customized Program 21:
			- 4 colors are used to divide the main data area in the sheet `21 - eog_stat_metadata_lol_head` (`21 - eog_stat_metadata_lol_header`).
				- Data not filled with any color mean `Key` is the index of `eog_stats_block`.
				- Data in the blue area mean the latter half of `Key` is the direct index of `eog_stats_block["mucJwtDto"]`.
				- Data in the green area mean the latter half of `Key` is the direct index of `eog_stats_block["rerollData"]`.
				- Data in the orange area mean the latter half of `Key` is the index of `eog_stats_block["teamBoost"]`.
				- Data in the blue, green and orange areas are handled by the same code frame.
		- `eog_teamstat_df_lol` in Customized Program 21:
			- 2 colors are used to divide the main data area in the sheet `21 - eog_stat_metadata_lol_head` (`21 - eog_stat_metadata_lol_header`). `team` denotes any element in `eog_stats_block["teams"]`.
				- Data not filled with any color mean `Key` is the index of `team`.
				- Data in the blue area mean the latter half of `Key` is the index of `team["stats"]`.
		- `eog_playerstat_df_lol` in Customized Program 21:
			- 2 colors are used to divide the main data area in the sheet `21 - eog_player_stat_lol_he` (`21 - eog_player_stat_lol_header`). `team` denotes any element in `eog_stats_block["teams"]`. `player` denotes any element in `team["players"]`.
				- Data not filled with any color mean `Key` is the index of `player`.
				- Data in the blue area mean the latter half of `Key` is the index of `player["stats"]`.
		- `eog_stat_metaDf_tft` in Customized Program 21:
			- The main data area in the sheet `21 - eog_stat_metadata_lol_he` (`21 - eog_playerstat_data_lol_header`) isn't filled with any color.
				- `Key` is the index of `tft_eog_stats`.
		- `eog_stat_df_tft` in Customized Program 21:
			- 7 colors are used to divide the main data area in the sheet `21 - eog_playerstat_data_tft_he` (`21 - eog_playerstat_data_tft_header`). `player` denotes any element in `tft_eog_stats["players"]`.
				- Data not filled with any color mean `Key` is the index of `player`.
					- `Key` No. 0～14 is the direct index of `player`.
					- The latter half of `Key` No. 15 and 16 is the direct index of `summonerIcons[player["iconId"]]`.
				- Data in the green area mean the latter half of `Key` is the direct index of `player["augments"][augmentIndex]`.
				- Data in the orange area mean the latter half of `Key` is the direct index of `player["boardPieces"][unit_index]`.
				- Data in the blue area mean the third part of `Key` is the direct index of `player["boardPieces"][unit_index]["items"][item_index]`.
				- Data in the purple area mean the latter half of `Key` is the direct index of `player["companion"]`.
				- Data in the yellow area mean the latter half of `Key` is the direct index of `player["customAugmentContainer"]`.
				- Data in the purple area mean the latter half of `Key` is the direct index of `player["playbook"]`.
				- Data in the purple, yellow and pink areas are handled by the same code frame.
		- `LoLItem_df`'s metadata in Item Program:
			- 3 colors are used to divide the main data area in the sheet `Item Program - base_header (ddr`. `item` denotes the value of key `i` in `LoLItems_locale["data"]`. `item_default` denotes the value of key `i` in `LoLItems_default["data"]`.
				- Data not filled with any color mean `Key` doesn't serve as the index of any variables of item data.
				- Data in the blue area mean `Key` is the index of `item`.
				- Data in the blue area mean `Key` comes from `item["gold"]`.
			- The main data area in the sheet `Item Program - base_header (cdr` isn't filled with any color. `item` denotes any element in `LoLItems_locale`. `item_default` denotes any element in `LoLItems_default`.
				- `Key` is the index of `item`.
6. Normally, text files generated by this program set are organized with indents. If the original dictionary variable in python runtime environment is required to recur, then simply pass a file pointer created by `open` function to the `load` function in `json` library, such as `fp = open("{filename}.txt", "r", encoding = "utf-8")` and `d = json.load(fp)`.
	- If the user wants to transform a json string with indents generated by `dumps` function into a json string without indents just in the runtime environment, he/she only needs to pass the string generated by `dumps` functin into `loads` function, such as `formatted = json.dumps({dictvariable}, indent = 8, ensure_ascii = False)` and `d = json.loads(formatted)`.
# Afterword
As a beginner in programming, I've just learned some basic usage of Python, and each function is implemented based on structured programming, without using the concepts of classes and objects, which may explain the code redundancy and low level of integration. For example, in Customized Program 05, a number of lines of codes are actually **copied** from some other part of the code. Moreover, for long strings, I choose to write them **in single lines**, considering <ins>decreasing the number of code lines</ins>, which is not friendly for a glance, and I apologize for this. In addition, I realized that more annotations are needed for the codes. Last but not least, since I haven't learned anything about GUI (the only one I've ever used is Visual Basic 😂), I'm only capable of designing programs that interact with CMD. (To be honest, I haven't planned to design the graphics interface for now and in the near future.)\
To be honest, there're not any really innovative ideas besides ZhiHu Author XHXIAIEIN's perception and Riot's official API. The program set mainly crawls and sorts out data. If any interesting idea pops up in your mind, welcome to fork this repository, create your own branch and submit pull requests!\
In the future, if possible, I'll perform a regression based on the match information dataframe generated by Customized Program 05 but combined with WeGame or OP.GG score, to predict the current player performance evaluation mechanism.