# 一、程序更新综述（Program Update Summary of Version 3.11 -> 4.1）
欢迎来到本次史无前例的*巨量*更新！首先，我想先解释一下这波酝酿得这么大的原因😛\
*一方面*，之前跟进的更新基本上都是在<u>暑假</u>，而这次更新是在<u>大学开学期间</u>。步入研究生生活，有许多事情需要去做，所以程序更新的事情就暂时先放在了一边。*另一方面*，也正是因为程序更新的事情被放在了一边，我便决定考虑如何填上之前没填的坑，包括<u>对局数据不完全问题</u>（比如斗魂竞技场强化符文问题）和**云顶之弈**数据爬取和整理功能缺失等问题。那么为了补充这些功能，从<u>数据换源</u>，到<u>云顶之弈数据结构设计</u>，到<u>斗魂竞技场数据添加</u>，再到<u>**人工代码优化**</u>，前后需要调整很多。在人工代码优化的过程中，我再一次地感受到了*面向对象程序设计*的重要性，后面我会详细列出人工代码优化的变化，以反映人工代码优化过程的复杂性。此外，之前的那个存储库，基于**对LCU API调用整体框架的代码作者的尊重**，我是<u>复刻</u>了原作者的存储库，但是这样就不便于管理。比如，复刻的存储库是<u>不允许更改可见性</u>的。还有就是复刻的时候一定要带上原作者的分支。其实这个分支倒也可以删，但是既然都说了要尊重原作者，那自然还是留着好一点了。为了既体现对作者的尊重，又想创建完全属于自己的存储库，我决定将原复刻的存储库存档，创建一个新的存储库。既然是创建新的存储库，不酝酿得大一点，似乎也有点说不过去（当然是非必要条件）。而本次更新的大量工作，实际上主要是**集中在最近两周**完成的。\
解释了新存储库的产生由来之后，下面就要介绍一下这次程序更新的主要内容了。相比[已存档的存储库](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived)的[最新提交](https://github.com/XHXIAIEIN/LeagueCustomLobby/commit/74960935b8d0fb98044c0721c82856217ff9c7a7)，本存储库的第一弹主要存在以下功能更新：
1. **数据资源获取和整理过程优化**
2. **数据资源初始化**
3. **中间变量导出**
4. **云顶之弈对局记录查询和导出**
5. **英雄联盟对局中的斗魂竞技场强化符文信息的完善**
6. **英雄联盟对局中的符文信息的完善**
7. **更完善的异常处理机制**
8. **战利品数据爬取**
# 二、实现细节（Implementation Details）
由于更改的内容很多，所以为了使得这部分内容更加有条理，这里将分**功能模块**介绍实现细节。
## （一）数据资源
数据资源的变动适用于所有当前脚本和以后即将开发的脚本。下面将罗列出*所有*变动的代码行。
1. 【**数据资源获取**】现在，在所有程序中，除了<u>版本数据</u>是来自<u>DataDargon数据库</u>以外，其它所有数据资源（<u>召唤师技能</u>、<u>英雄联盟装备</u>、<u>符文</u>、<u>符文系</u>、<u>云顶之弈强化符文</u>、<u>云顶之弈棋子</u>、<u>云顶之弈装备</u>、<u>云顶之弈小小英雄</u>、<u>云顶之弈羁绊</u>、<u>斗魂竞技场强化符文</u>）都来自**CommunityDragon数据库**。
    1. 现在程序集将根据**服务器信息**自动选择获取<u>正式服的*最新*数据资源</u>或<u>美测服的*测试*数据资源</u>。（自定义脚本5第157、158和177～188行和自定义脚本11第144、145和164～175行。）
    2. 语言选择的输入提示已经**与DataDragon数据库中记录的服务器信息同步**。此外，通过检查各种语言的资源是否在CommunityDragon数据库存储的各个版本中都存在，本程序集添加了CommunityDragon数据库中**各语言的可用版本**。其中后缀为“+”的版本表示至今可用。（自定义脚本4第67～70、73和75行，自定义脚本5第160、161、168、169、172和174行和自定义脚本11第147、148、155、156、159和161行。）
    3. 现在，在获取所有数据资源时，代码中指定了一个变量，用来**存储数据资源的地址**。以后所有对地址的访问都转变为对这个地址字符串变量的访问。（自定义脚本4第77～81和151行，自定义脚本5第173～194行和自定义脚本11第160～181行。）
    4. 选择在线载入数据资源而加载失败时，目前都认为是<u>语言选择</u>的问题。如果出现这种情况，请退而求其次，<u>尝试选择一个能够使程序正常运行的语言</u>；或者尝试<u>离线加载数据</u>，并**自行**寻找合适的语言版本的数据资源。（自定义脚本5第203、265、306、347、388、429、470、511、552、593、635、880和881行和自定义脚本11第190、252、293、334、375、416、457、498、539、580、622、867和868行。）
    5. 在线模式获取数据资源超时时，**允许从本地离线读取文件**。（自定义脚本4第87～113行，自定义脚本5第210～239、267～296、308～337、349～378、390～419、431～460、472～501、513～542、554～583、595～624和637～666行和自定义脚本11第197～226、254～283、295～324、336～365、377～406、418～447、459～488、500～529、541～570、582～611和624～653行。）
    6. 现在，本程序集支持**离线**载入数据资源。推荐使用的数据资源位于主目录下的“<u>离线数据（Offline Data）</u>”，**将跟随英雄联盟版本更新**。（自定义脚本5第671～879行和自定义脚本11第658～866行。）
    7. 本程序集为离线载入数据资源提供了一定的**异常处理**机制。可以解决<u>文件不存在</u>、<u>文件路径格式错误</u>和<u>基本的数据格式错误</u>等问题。（自定义脚本5第228～239、285～296、326～337、367～378、408～419、449～460、490～501、531～542、572～583、613～624、655～666、691～696、719～724、733～738、747～752、761～766、775～780、789～794、803～808、817～822、831～836、845～850和854～873行和自定义脚本11第215～226、272～283、313～324、354～365、395～406、436～447、477～488、518～529、559～570、600～611、642～653、678～683、706～711、720～725、734～739、748～753、762～767、776～781、790～795、804～809、818～823、832～837和841～860行。）
    8. 在载入资源时，支持**从离线模式转为在线模式**（自定义脚本5第672、681～683、876和877行和自定义脚本11第659、668～670、863和864行），也支持**在线模式*获取超时*时转为离线模式**（自定义脚本5第206、221、278、319、360、401、442、483、524、565、606、648和667～669行和自定义脚本11第193、208、265、306、347、388、429、470、511、552、593、635和654～656行）。
2. 【**数据资源整理**】现在，除<u>版本数据</u>外，所有数据资源都以<u>嵌套字典</u>的形式存储在运行环境内，以便<u>索引</u>。（**请留意游戏模式数据资源字典的变化。**）（自定义脚本5第887～932、977～985、988～992、1363～1366、1435～1438、1698～1792、1764～1767、2010～2013、2059～2062、2105～2108、2160～2163、2204～2207、2586～2589、2629～2632、2714～2723、2783～2791、2846～2849和2884～2887行和自定义脚本11第874～946、1161～1164、1233～1236、1517～1520、1572～1575、1616～1619、1833～1836、1875～1878、1955～1964、2022～2030、2082～2085和2120～2123行。）
3. 【**数据重获优化**】创建了一个字典`recaptured`，用来减少重新获取数据资源失败时的输出提示。目前由于一个潜在的问题（详见代码注释）而未投入使用。（自定义脚本5第933～941行。）
4. 【**数据初始化**】现在，当<u>一位召唤师的所有数据获取完成，程序切换下一位召唤师</u>时，当<u>程序在获取完成对局历史后进入扫描模式</u>时，以及当<u>程序在获取完成对局历史后开始获取每场对局的数据</u>时，相关数据资源能够**初始化**了。（自定义脚本5第949～961、1554、1555、1849和1850行和自定义脚本11第960～972、1384和1385行。）
## （二）变量重命名
为了适应与新功能相关的变量名称，本次更新对大量旧程序的变量进行了重命名。
1. 现在，一些隶属英雄联盟产品的非迭代器变量都以“<u>LoL</u>”为前缀或包含“<u>LoL</u>”，并统一了**单复数形式**（单数表示<u>未处理完毕的相关数据或者迭代器</u>；复数表示<u>最终投入使用的相关数据容器</u>，一般是**字典**）。（一些隶属云顶之弈产品的非迭代器变量则以“TFT”为前缀或包含“TFT”，但是由于都是**新添加的**，而不是旧变量的重命名，所以这里不列举。）
    1. **item → <font color=#ff0000>LoL</font>Item**和**items → <font color=#ff0000>LoL</font>Items**。（自定义脚本5第953、1420、1435、1438、1444、1451、1458、1465、1472、1479、1486、1555、1724、1727、1730、1733、1736、1739、1742、1746、1749、1764、1765、1767、1773、1780、1787、1794、1801、1808、1815、1850、2036、2040、2043、2059、2060、2062和2064行和自定义脚本11第964、1193、1196、1199、1202、1205、1208、1211、1218、1233、1234、1236、1242、1249、1256、1263、1270、1277、1284、1385、1474、1476、1477和1481行。）
    2. **champion → <font color=#ff0000>LoL</font>Champion**和**championId → <font color=#ff0000>LoL</font>Champions**。（自定义脚本5第988～990、992、1070、1073、1325、1329、1973、1978、2241、2246、2333和2340行和自定义脚本11第887～889、891、1123、1127、1460和1462行。）
    3. **输入提示**。（自定义脚本5第1189、1210、1223、1231、1233、1288、1417、1429、1434、1507、1551、1746、1758、1763、2040、2052、2058和2952行和自定义脚本11第1006、1025、1086、1215、1223、1227、1232、1658、2410和2424行。）
    4. **history_get → <font color=#ff0000>LoL</font>History_get**。（自定义脚本5第1192、1209、1230、1242和1246行和自定义脚本11第1007、1024、1028、1040和1044行。）
    5. **history → <font color=#ff0000>LoL</font>History**。（自定义脚本5第1195、1196、1199、1200、1204、1207、1208、1221、1233、1235和1280行和自定义脚本11第1010、1011、1014、1015、1019、1022、1023、1031、1033和1078行。）
    6. **文本文档命名**。（自定义脚本5第1212、1538、1916和1934行。）
    7. **history_header → <font color=#ff0000>LoL</font>History_header**。（自定义脚本5第1248、1500、1501、1830和1831行和自定义脚本11第1046、1298和1299行。）
    8. **gamePlayed → <font color=#ff0000>LoL</font>GamePlayed**。（自定义脚本5第1249、1287、1504和2370行和自定义脚本11第1047、1085和1302行。）
    9. **itemID → <font color=#ff0000>LoL</font>ItemID**。（自定义脚本5第1394、1397、1400、1403、1406、1409、1412、1417、1431、1723、1726、1729、1732、1735、1738、1741、1746、1760、2029、2031、2032、2036、2054、2064、2066和2067行和自定义脚本11第1192、1195、1198、1201、1204、1207、1210、1215、1229、1480、1481和1483行。）
    10. **item_recapture → <font color=#ff0000>LoL</font>Item_recapture**。（自定义脚本5第1416、1417、1424、1425、1427～1429、1745、1753、1754、1756～1758、1962、2039、2040、2047、2048和2050～2052行和自定义脚本11第1214、1215、1222、1223和1225～1227行。）
    11. **history_data → <font color=#ff0000>LoL</font>History_data**。（自定义脚本5第1499、1501、1829、1831和1832行和自定义脚本11第1297、1299和1300行。）
    12. **history_df → <font color=#ff0000>LoL</font>History_df**。（自定义脚本5第1502、1503、1505、1832、2930、2949、2951、2999和3001行和自定义脚本11第1300、1301和1303行。）
    13. **matchIDs → <font color=#ff0000>LoL</font>MatchIDs**。（自定义脚本5第1508、1534、1539、1540、1544～1547、1550、1587、1680、1746、1758、1828、1836、1838、1842、1843、1851、1953、1991、2005、2017、2040、2054、2066、2086、2100、2112、2141、2155、2167、2185、2199、2211和2374行和自定义脚本11第1335、1337、1341、1342、1346～1349、1352、1359、1361、1365、1366、1388、1498、1512、1524、1553、1567、1579、1597、1611、1623和1645行。）
    14. **game_info → <font color=#ff0000>LoL</font>Game_info**。（自定义脚本5第1588、1591、1593、1595、1599、1602、1603、1606、1610、1613、1618、1619、1624、1625、1628、1630、1632、1634、1637、1638、1642、1643、1645、1647、1661、1665、1667、1668、1670、1671、1705、1707、1709、1711、1713、1852、1853、1858、1860、1864、1868、1868、1872、1875、1879、1882、1883、1889、1890、1893、1894、1898、1925、1961、1968、1970、1973、1978、1978、1982、1989、2024、2026、2029、2031、2038、2076、2084、2122～2124、2130、2132、2139、2175、2183、2222、2224、2226、2228、2230、2298、2324、2328、2333、2340和2342行和自定义脚本11第1389、1390、1393、1395、1398、1402、1405、1406、1408、1412、1415、1419、1420、1425、1428、1429、1430、1432、1433、1434、1438、1440、1444、1446、1449、1451、1454、1456、1458、1464、1488、1496、1534～1536、1542、1544、1551、1587、1595、1634、1636和1638行。）
    15. **game_timeline → <font color=#ff0000>LoL</font>Game_timeline**。（自定义脚本5第1854、1855、1943、2264、2266、2270、2273、2274、2277、2281、2284、2285、2292、2296、2303和2364行。）
    16. **game_info_error → <font color=#ff0000>LoL</font>Game_info_error**。（自定义脚本5第1893和1894行。）
    17. **game_info_df → <font color=#ff0000>LoL</font>Game_info_df**。（自定义脚本5第1894、1913、1961、1968、1970、1973、1978、1980、2254～2261、2304、2364、2365和2368行。）
    18. **game_info_header → <font color=#ff0000>LoL</font>Game_info_header**。（自定义脚本5第1954、1963和2253行和自定义脚本11第1374、1376和1657行。）
    19. **game_info_data → <font color=#ff0000>LoL</font>Game_info_data**。（自定义脚本5第1955、1965、1968、1970、1973、1975、1978、1980、1982、2022、2024、2026、2033、2071、2078、2128、2130、2134、2172、2177、2220、2222、2224、2234、2236、2241、2243、2246、2248和2253行和自定义脚本11第1375、1387、1438、1442、1444、1447、1449、1452、1454、1456、1460、1462、1466、1468、1471、1478、1481、1483、1490、1540、1542、1546、1584、1589、1632、1634、1636、1639、1641、1643和1657行。）
    20. **game_info_header_keys → <font color=#ff0000>LoL</font>Game_info_header_keys**。（自定义脚本5第1956、1964、2075、2122～2124、2174和2252行和自定义脚本11第1376、1386、1435、1436、1487、1534～1536、1586和1656行。）
    21. **game_info_statistics_display_order → <font color=#ff0000>LoL</font>Game_info_statistics_display_order**。（自定义脚本5第2249和2251行。）
    22. **game_info_data_organized → <font color=#ff0000>LoL</font>Game_info_data_organized**。（自定义脚本5第2250、2253和2254行。）
    23. **game_timeline_error → <font color=#ff0000>LoL</font>Game_timeline_error**。（自定义脚本5第2296和2297行。）
    24. **game_timeline_df → <font color=#ff0000>LoL</font>Game_timeline_df**。（自定义脚本5第2297、2363～2365和2369行。）
    25. **game_timeline_header → <font color=#ff0000>LoL</font>Game_timeline_header**。（自定义脚本5第2300、2300、2304和2362行。）
    26. **game_timeline_data → <font color=#ff0000>LoL</font>Game_timeline_data**。（自定义脚本5第2301、2306、2309、2311、2314、2316、2320、2324、2328、2333、2335、2340、2342、2347、2349、2355、2357和2362行。）
    27. **game_timeline_header_keys → <font color=#ff0000>LoL</font>Game_timeline_header_keys**。（自定义脚本5第2302、2305和2361行。）
    28. **game_timeline_statistics_display_order → <font color=#ff0000>LoL</font>Game_timeline_statistics_display_order**。（自定义脚本5第2358和2360行。）
    29. **game_timeline_data_organized → <font color=#ff0000>LoL</font>Game_timeline_data_organized**。（自定义脚本5第2359、2362和2363行。）
    30. **工作表命名**。（自定义脚本5第2949、2951、2993、2998、2999、3001、3002、3005和3006行和自定义脚本11第2409、2423、2498和2508行。）
    31. **error_matchIDs → error_<font color=#ff0000>LoL</font>MatchIDs**。（自定义脚本11第1378和1421行。）
    32. **gameDuration_raw → <font color=#ff0000>LoL</font>GameDuration_raw**。（自定义脚本11第1380、1441和2187行。）
    33. **recent_players_statistics_display_order → recent_<font color=#ff0000>LoL</font>Players_statistics_display_order**。（自定义脚本11第1653、1655、1656和1658行。）
    34. **recent_players_data_organized → recent_<font color=#ff0000>LoL</font>Players_data_organized**。（自定义脚本11第1654、1657、1660行。）
    35. **recent_players_df → recent_<font color=#ff0000>LoL</font>Players_df**。（自定义脚本11第1660、1663～1668、2183～2190、2221、2409、2423、2479、2480和2488行。）
    36. **gameDuration_iter → <font color=#ff0000>LoL</font>GameDuration_iter**。（自定义脚本11第2187、2196、2203～2206、2210和2217～2220行。）
    37. **ally_df_to_print → <font color=#ff0000>LoL</font>Ally_df_to_print**。（自定义脚本11第2471、2489、2518和2526行。）
    38. **ally_index → <font color=#ff0000>LoL</font>Ally_index**。（自定义脚本11第2477、2481、2486、2488、2497、2501、2507和2511行。）
    39. **ally_df → <font color=#ff0000>LoL</font>Ally_df**。（自定义脚本11第2488、2489、2498和2508行。）
2. 一些变量根据其**实际含义**重新命名。
    1. 现在`FindPostPatch`函数的第二个形式参数更名为<u>patchList</u>，以和后续协程中的`patches`区分开来。（自定义脚本5第116、117、123、126、130和136行和自定义脚本11第118、119、125、128、132和138行。）
    2. 如无特殊说明含义，所有存储文本文档的名称的变量都采用“<u>txtfile[数字]</u>”的格式命名。（自定义脚本5第1018、1024、1027、1047、1053、1056、1115、1121、1124、1215、1221、1224、1919、1925、1929、1937、1943、1947、2400、2406、2409、2465、2471和2475行和自定义脚本11第2266和2272行。）
    3. 自定义脚本5和11中的“game<font color=#ff0000>s</font>”现在指定为<u>一名玩家的所有对局</u>，而“game”只指<u>一场对局</u>。（自定义脚本5第1280、1281、1283、1292、1292、1294、1296、1298、1301、1302、1306、1307、1309、1311、1325、1329、1331、1332、1334、1335、1344、1358、1359、1368、1370、1371、1376、1378、1380、1382、1384、1417和1431行和自定义脚本11第1078、1079、1081、1090、1092、1094、1096、1099、1100、1104、1105、1107、1109、1123、1127、1129、1130、1132、1133、1142、1156、1157、1166、1168、1169、1174、1176、1178、1180、1182、1215和1229行。）
    4. 自定义脚本9中存储当前时间的变量现在与自定义脚本5一致，都是<u>`currentTime`</u>。这主要是因为原先直接采用时间作为工作表名称，所以用`sheetname`。但是这次更改之后，工作表名称不只包含时间，所以再用“sheetname”来存储时间就有点不合适了。（自定义脚本9第139～141和144～146行。）
    5. 在获取对局历史信息时，存储游戏模式名称的列表从“name”更名为<u>`gameModeName`</u>。（自定义脚本9第1046、1056、1102和1105行。）
    6. 在生成柱状图时，游戏时长的变量现在命名为<u>`playtime`</u>，以和`time`库区分开来。（自定义脚本9第2326、2327、2336、2337、2346、2347、2356、2357、2366、2367、2376、2377、2386、2387、2396和2397行。）
## （三）异常处理机制完善
1. <b>细化了生成文本文档时的报错类型。</b>现在，只有当程序抛出<u>FileNotFoundError</u>时，才会创建文件夹了。（自定义脚本5第1019、1048、1116、1216、1920、1938、2401和2466行和自定义脚本11第2267行。）
2. 使用`requests.get`函数重新获取数据资源时，现在能够**区分<u>获取超时</u>和<u>网络文件不存在</u>的错误**了。（自定义脚本5第1348～1360、1421～1432、1683～1696、1749～1761、1995～2007、2044～2056、2090～2102、2145~2157、2189～2201、2571～2583、2614～2626、2699～2711、2768～2780、2831～2843和2849～2881行和自定义脚本11第1146～1158、1219～1231、1502～1514、1557～1569、1601～1613、1821～1833、1863～1875、1943～1955、2010～2022、2070～2082和2108～2120行。）
3. 在根据对局序号获取对局信息时，现在能够区分是否是云顶之弈对局了。不过目前**尚未应用**，等待后续开发。（自定义脚本5第1883和1884行。）
## （四）中间变量导出
为了方便调试程序，程序中添加了涉及<u>`pickle`</u>库的代码，可以**将变量以二进制的形式导出为本地文件**。其作用如下：
1. 检查程序运行过程中的错误。
2. 作为历史数据而留存。\
考虑到第2点的原因，一些pkl文件名中包含了当前时间。但是这样带来的问题是反复获取会导致临时文件大量增加。因此，为了简化程序的输出，目前所有涉及`pickle`库的代码都被注释了。请用户根据自身使用情况决定是否取消注释这些语句。

（自定义脚本5第2、1030～1032、1059～1061、1127～1129、1226～1228、1931～1933、1949～1951、2411～2413和2477～2479行和自定义脚本11第1692～1694行。）
## （五）变量重定义（自定义脚本5）
1. 本次更新*重新定义*了6个变量的类型：
    1. `game_info_dfs`。（第1180、2368、2910、2925、2960和3017行。）
    2. `game_timeline_dfs`。（第1181、2369、2962和3019行。）
    3. `info_exist_error`。（第1184、1891、1912、2483、2959、2969、2971、2973、3016、3026、3028和3030行。）
    4. `timeline_exist_error`。（第1185、2293、2299、2366、2484、2961、2969、2971、2973、3018、3026、3028和3030行。）
    5. `main_player_included`。（第1186、1901、1904、2485、2963和3020行。）
    6. `match_reserve_strategy`。（第1187、1902、1909、1911、2486、2958、2964、3015和3021行。）
    \
    现在它们不再是<font color=#ff0000>列表</font>，而是<font color=#ff0000><b>字典</b></font>了。这样有利于英雄联盟和云顶之弈的对局信息和时间轴工作表**根据对局序号（键）进行混合排序**。
2. 在向将来要构成数据框的列表中追加元素时，大多数需要<u>分类讨论</u>或<u>异常处理</u>的情况通过**引入<font color=#ff0000>`to_append`</font>变量**来简化代码。（自定义脚本5第1987、2006、2015、2018、2022、2036、2055、2064、2067、2071、2119、2125、2127、2128、2137、2156、2165、2168、2172、2217、2219、2220、2501、2502、2520、2521、2563、2582、2591、2594、2599、2600、2602、2625、2637、2640、2643、2644、2646、2655、2656、2658、2662、2664、2665、2667、2669、2670、2672、2674、2675、2677、2686、2689、2691、2710、2726、2728、2730、2734、2736、2740、2742、2756、2760、2779、2793、2797、2800、2806、2808、2810、2811、2813、2823、2842、2851、2854、2861、2880、2889、2892、2896和2898行和自定义脚本11第1531、1537、1539、1540、1549、1568、1577、1580、1584、1629、1631、1632、1747、1748、1771、1772、1813、1832、1841、1844、1849、1851、1874、1886、1889、1892、1894、1903、1905、1909、1911、1913、1915、1917、1919、1921、1930、1932、1933、1935、1970、1972、1974、1978、1980、1985、1998、2002、2021、2035、2039、2042、2048、2051、2053、2062、2081、2090、2093、2100、2119、2128、2131和2136行。）
## （六）重要信息添加
更新后的程序集中添加了对<u>**英雄联盟符文**</u>（自定义脚本5第2072～2172行和自定义脚本11第1484～1584行）、<u>**斗魂竞技场强化符文**</u>（自定义脚本5第2173～2220行和自定义脚本11第1585～1623行）和<u>**云顶之弈**</u>（自定义脚本5第2381～2921行和自定义脚本11第1675～2169行）的数据的整理。\
需要说明，在整理云顶之弈数据时，程序是*边整理对局信息，边整理对局历史的*。这是因为没有<u>根据对局序号查询云顶之弈对局信息的可用接口</u>。
## （七）其它变动
### （Ⅰ）整体改动
现在，服从国服对“Match History”的翻译，所有“<u>对局历史</u>”一律替换为“<u>**对局记录**</u>”。
### （Ⅱ）自定义脚本4
1. 定义了插入排序函数`patch_sort(patchList)`以**排序从CommunityDragon数据库主页通过<u>审查元素</u>爬取到的版本号**。（第47～60行和自定义脚本5第141和154行。*该函数在自定义脚本5中没有调用，只是因为以自定义脚本5作为所有自定义脚本的开发来源，所以把新定义的函数都放在了自定义脚本5中。*）
2. 添加了**从CommunityDragon数据库获取并整理英雄数据**的代码。（第210～228行。）
3. 优化了**英雄数据来源选择**。为了尽可能减少异常处理，对于输入，程序只处理<u>非空字符串的第一个字符</u>。（第64、65、117和128行。）
### （Ⅲ）自定义脚本5
1. 修复了一处**查询英雄成就信息**的错误。（第1040～1042行。）
2. 现在程序**允许用户决定是否查询英雄联盟对局记录或云顶之弈对局记录**。（第1189、1190、2379和2380行。）
3. 修复了一处**注释错误**，因为该注释对应的文件在很久之前就已经修改了格式。（原代码第467行。）
4. 现在，程序在提示输入下界和上界时，提示输入的类型是“**自然数**”而不是“整数”了。（第1531行。）
5. 完善了**扫描模式的对局提取规则**。（第1538行。）
6. 定义了`augment_rarity`变量，以评价斗魂竞技场的强化符文的强度等级。（第1959和2217行。）
7. 完善了**空工作表占位顺序**。现在，当创建新工作簿时，前八张工作表的期望顺序应该是账户信息、排位数据、英雄成就、近期一起玩过的英雄联盟玩家数据、近期一起玩过的云顶之弈玩家数据、英雄联盟对局记录、本地重查英雄联盟对局记录、云顶之弈对局记录。（第2928～2932、2998、3002、3005、3006和3012行。）
### （Ⅳ）自定义脚本9
修复了一处键错误：<u>添加了**流光翡翠**段位</u>。（第72行。）
### （Ⅴ）自定义脚本11
1. 现在程序**允许用户决定是否查询云顶之弈对局记录和导出**。（第1672、1673、2222、2411、2425、2482、2499、2509、2519和2527行。）
2. 现在，程序在提示输入下界和上界或下界和对局数时，提示输入的类型是“**自然数**”而不是“整数”了。（第1330行和2161行。）
3. 一处无关紧要的更新：在使用lambda函数时，冒号后~~必须~~有一个空格。（第2294～2301行。）
4. 完善了**游戏进程的分类讨论**：添加了<u>赞誉一名队友</u>和<u>等待游戏数据加载</u>时的游戏状态。（第2460行。）
### （Ⅵ）自定义脚本12——战利品整理脚本（新增）
1. 本脚本沿用了查战绩脚本的文件保存机制，文本文档和工作表的保存位置位于<u>查战绩脚本指定的各召唤师文件夹</u>下。其中包含对文本文档生成提示的一处优化，*将在下次提交中更新*。（第59～97和133～154行。）
2. 本脚本定义了`essenceType`、`lootCategories`、`itemStatus`、`rarity`、`redeemableStatus`和`lootType`等字典变量，以将一些关键数据转化为**中文用户容易理解的形式**。翻译可能有误，欢迎批评指正！（第101～106行。）
3. 本脚本只做**数据的爬取和整理**，用户如有进一步需求，请自行前往召唤师相应的文件夹下对Excel数据表做相应的分析。
### （Ⅶ）主要数据框结构
1. 自定义脚本5和11的数据框的**工作表命名现在也区分英雄联盟和云顶之弈**了。
2. 按照“多了可以删，少了造不了”的原则，在工作表`05 - LoLGame_info_header`（原`game_info_header`）中补充了<u>召唤师图标序号</u>和<u>玩家通用唯一识别码</u>。
3. 添加了<u>云顶之弈对局记录数据框</u>（`05 - TFTHistory_header`）、<u>云顶之弈对局信息数据框</u>（`05 - TFTGame_info_header`）、<u>近期一起玩过的云顶之弈玩家数据框</u>（`11 - recent_TFTPlayers_header`）和<u>玩家战利品数据框</u>（`12 - player_loot_header`）的表头说明。
### （Ⅷ）`清除临时文件`批处理文件
现在，自定义脚本5在各召唤师文件夹下生成的中间变量**pkl**文件可以通过批处理文件删除。
### （Ⅸ）离线数据
现在，存储库中提供美测服的各种数据资源。
### （Ⅹ）说明文档
1. 更新了其它说明的位置。（第3行。）
2. 调整了中文声明的一处说法。（第6行。）
3. 修正了自定义脚本的说明参阅处。（第9行。）
4. 移除了对于可创建房间数据的说明，新增了对于离线数据资源的说明。（第43～45行。）
5. 补充了几个用到的Python库。（第69～71行。）
6. 声明了查战绩脚本的数据资源来源。（第91行。）
7. 修正了对查战绩脚本生成的工作簿内容的描述：“工作簿”改为“工作表”。（第94～97和103行。）
8. 更新了对局记录所包含的内容。（第98～102行。）
9. 添加了一条【本地重查】的使用说明。（第109行。）
10. 移除了一条未来规划，因为它在当前版本已经实现了。（原文档第99行。）
11. 添加了一条对自定义脚本6的使用说明。（第113行。）
12. 移除了自定义脚本7中关于商品信息格式整理的叙述，因为在当前版本该工作可由程序实现。（原文档第103行。）
13. 为部分文字添加了粗体或下划线等格式。（第124、125和130行。）
14. 调整了主要数据框结构工作簿的数据框变量名和工作表命名。（第136～140和159～167行。）
15. 修正了一类英文语法错误：数格。（第346～350、356、363～367、370～373、376～379、381和386～389行。）
16. 添加了云顶之弈对局记录数据框（`05 - TFTHistory_header`）、云顶之弈对局信息数据框（`05 - TFTGame_info_header`）、近期一起玩过的云顶之弈玩家数据框（`11 - recent_TFTPlayers_header`）和玩家战利品数据框（`12 - player_loot_header`）等工作表的主要数据区域说明。
17. 修改了后记中的一处语病：“调用数据”搭配不当，调用一般与函数搭配。（原文档第165行。）
# 三、未来规划和想法（Future Plans & Ideas）
1. **根据他人意见优化云顶之弈的数据结构。**\
因为整个云顶之弈的对局记录在LCU API上的记录由好几层**嵌套字典**组成，而导出到Excel中必须降维成**二维表**，所以可以看到*字段数*很庞大。目前也只是一个初步的决定，要是没有什么建设性意见的话我就保持现状了。
2. **新增查询最近一起玩过的玩家的脚本的打分机制。**\
在使用扫描模式来汇总近几年来一起玩过的玩家时，几年前一起玩过和现在一起玩过，终究是不一样的，取决于对局的创建时间离当前的远近。所以计划引入一个模型，来计算得到玩家之间邂逅的巧合程度。这个模型至少应当考虑到<u>对局时长</u>和<u>对局创建时间</u>距今远近两个要素。
3. 云顶之弈对局的扫描模式<font color=#ff0000>（×）</font>\
首先，要声明一下，我目前的想法是不可能在程序里加入这个功能的。云顶之弈虽然有**对局序号**的说法，但是无法通过`/lol-match-history/v1/games/{gameId}`的接口来访问对局的详细信息。而扫描模式运作的**主要原理**是从本地文件夹中获取该玩家的对局序号，利用这个对局序号和这个接口来重新查询，所以扫描模式又名“本地重查”。\
所以，假设我们要对云顶之弈执行扫描模式，那么运作的方式不再是通过LCU API进行重查，而是应该直接读取当时保存到本地的文本文档的信息。好像看起来也不是不能做？是的，的确可以这么做。但是存在一种情况：<b>文件夹里的数据并不是全由脚本生成的，也可能存在用户自行编辑设计的情况。</b>这样，情况就变得复杂起来了。而且我的脚本没法检测每个云顶之弈对局文本文档的正确性。\
有人会说：“要确定云顶之弈对局数据格式也可以的啊！<u>你在脚本里设置一个`if`语句，如果能够成功以读取json的方式读取文本文档，并且读取后形成的数据是一个字典，并且设定好字典的键</u>，那不就可以了吗？”我的回答是：确实可以，但这样存在风险。<b>首先，</b>如果我要判断读入数据的格式是否符合对局数据的格式，那么我肯定尽可能地要让脚本里定义的这个格式和<u>**LCU API**上记录的云顶之弈对局记录的格式</u>对应得<font color=#ff0000>严丝合缝</font>，比如每一层的键是什么，其值的类型是什么。这样，就这么一个`if`语句，会写得**很长很长**。<b>另一个很糟糕的事情是，</b>云顶之弈的对局信息格式是可能<font color=#ff0000>随时更新</font>的。这也是我在这次大更新中特别想吐槽的一点😤云顶之弈的数据格式在不同版本之间存在一定的**不统一性**，甚至是<font color=#ff0000>很强的不统一性</font>（不仅仅是对局记录，其它数据资源都存在这种情况。比如你可以对比一下以下两个链接的数据格式：[最新版本的云顶之弈棋子信息](https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/zh_cn/v1/tftchampions.json)和[10.1版本的云顶之弈棋子信息](https://raw.communitydragon.org/10.1/plugins/rcp-be-lol-game-data/global/zh_cn/v1/tftchampions.json)），我必须能够保证程序能够适用于所有版本。（因为当你想要通过扫描模式读取历史对局记录时，往往这个对局已经是比较**古早**的版本了。）然后，一个有趣的现象就可能会产生：<u>我千辛万苦地定义了一个对局记录的规则，结果这个规则更新了</u>🥹\
看到这里，有的人又会说：“那你不要写这么详细呗。<u>你这就有点像模型的过拟合了。稍微设置几个筛选条件，基本上就八九不离十了，也为后续格式变动提供更新的余地了。</u>”要是这么说的话，恐怕这不是在给数据格式的变动以余地，而是在给<u>非法数据格式</u>以余地。如果有些数据格式符合粗略条件，但实际上里面有些数据根本就是牛头不对马嘴，那那些整理数据格式的代码就跑不通了，程序就会报错。<b>再者，</b>如果格式都对上了，程序也能跑通，但是数据是假的，那就相当于是**捏造历史**了。（那其实这一点的话，即使我定义精准的格式，也没法解决这个问题。）\
总而言之，我设计扫描模式的思路就是<u>从本地得到对局序号，根据对局序号从网络上重新下载信息</u>。因为云顶之弈**不能***根据对局序号来获取信息*，所以云顶之弈的扫描模式是**不会**支持的。唯一安全的办法就是<u>英雄联盟设计师开放与对局序号相关的云顶之弈对局数据接口</u>。或者有一天我找到了解析GAMHS数据的方法，兴许也可以做这个扫描模式。
4. 可创建房间数据的添加（×）
5. 英雄联盟对局记录的更新（×）\
本次虽然对原有的对局信息数据结构（现`LoLGame_info_data`）进行了更新，但是没有对英雄联盟对局记录数据结构（现`LoLHistory_df`）进行更新。这是因为在客户端中，生涯界面的对局记录的格式是相对**固定**的，而查战绩脚本生成历史记录工作表的格式是**仿照客户端**的，所以暂时不考虑更新英雄联盟对局记录。

# Ⅰ. Program Update Summary of Version 3.11 -> 4.11
Welcome to this unprecedented *grand* update! In the first place, please let me explain why the update has been accumulated to this huge.😛\
*On the one hand*, previous updates were basically committed during <u>summer vacation</u>, but this update has been prepared <u>around the start of the autumn semester</u>. Walking into the postgraduate life, there're so many things to do, so the program update was put aside then. *On the other hand*, because I shelved the update, I began to think of how to realize the unfinished goals, like <u> the incomplete match data</u> (e.g. Arena augments) and the absence of **TFT** data crawling and sorting. To add these functions, there's a lot of work to do throughout the procedure including <u>data resource change</u>, <u>TFT data structure design</u>, <u>Arena data supplement</u> and <u>**manual code optimization**</u>. To put in, during code optimization, I felt it important to utilize the *object-oriented programming* principle. I'll list the code change later in detail to show the complexity of manual code optimization. What's more, the precedent repository is forked from another one, **in respect for the author that provided the overall frame to call the LCU API**, which make it inconvenient for subsequent management. For example, it's **not allowed to change the visibility** of a forked repository. Another thing is that the main branch has to inherit from the author's repository. Actually it should be allowed to delete the inherited branch, but since I wanted to show some respect for the original author, I'd better leave it untouched. Aimed at showing respect for the original author and completely possessing a relevant repository, I decided to archive the forked repository and create a new repository. Since a new repository is to be created, it seems somehow inadequate of reasons if I don't commit a dramatic update (Of course it's an unnecessary condition). As a matter of fact, a great part of this update is prepared during the **recent two weeks**.\
Having explained the cause of this new repository, I'll illustrate the main content for this update. Compared with the [latest commitment](https://github.com/XHXIAIEIN/LeagueCustomLobby/commit/74960935b8d0fb98044c0721c82856217ff9c7a7) of the [archived repository](https://github.com/WordlessMeteor/LoL-DIY-Programs-Archived), the major functional updates of the first commitment of this repository are listed as follows:
1. **Data resource capture and data sorting optimization**
2. **Data resource initialization**
3. **Intermediate variable export**
4. **TFT match history query and export**
5. **Arena augments supplement in LoL matches**
6. **runes supplement in LoL matches**
7. **Improved exception handling mechanisms**
8. **Loot data crawling**
# Ⅱ. Implementation Details
Because there're hundreds of specific changes in this update, to make this part more organized, the implementation details will be divided into several **functional modules**.
## ⅰ. Data Resource
Data resource changes apply to all programs, including the future ones. *All* code lines involving this kind of change will be listed below:
1. **[Data resource capture]** Now, in all programs, except that <u>patch data</u> come from <u>DataDragon</u> database, all data resources (<u>summoner spells</u>, <u>LoL items</u>, <u>runes</u>, <u>perkstyles</u>, <u>TFT augments</u>, <u>TFT champions</u>, <u>TFT items</u>, <u>TFT companions</u>, <u>TFT traits</u> abd <u>Arena augments</u>) are downloaded from **CommunityDragon** database.
    1. Now, the program set will choose to get <u>the *latest* data resource for live servers</u> or the <u>*test* data resource for PBE</u> according to **the current server information** automatically. (Lines 157, 158 and 177～188 in Customized Program 5 and Lines 144, 145 and 164～175 in Customized Program 11.)
    2. The input hint on language selection **has synchronized with the server information recorded in DataDragon database**. Besides, by checking whether the data resources for each language exist in all patches of CommunityDragon database, this program set added an **Applicable CDragon Data Patches** field into the input hint, where a patch postfixed with a "+" means that language is available now. (Lines 67～70, 73 and 75 in Customized Program 4, Lines 160, 161, 168, 169, 172 and 174 in Customized Program 5 and Lines 147, 148, 155, 156, 159, 161 in Customized Program 11.)
    3. Now, variables are declared to **store the urls of data resources** when capturing data resources. The later visit to these URLs will be replaced by the visit to these variables. (Lines 77～81 and 151 in Customized Program 4, Lines 173～194 Customized Program 5 and Lines 160～181 in Customized Program 11.)
    4. When the user selects the online mode to load data resources but failed, this problem will be regarded to belong to the <u>incompatible language selection</u> kind. If such situation occurs, please seek for the second best and <u>try changing into a language that makes the program run</u>; or try <u>loading offline data</u> and find the data resources of an appropriate language **by yourself**. (Lines 203, 265, 306, 347, 388, 429, 470, 511, 552, 593, 635, 880 and 881 in Customized Program 5 and Lines 190, 252, 293, 334, 375, 416, 457, 498, 539, 580, 622, 867 and 868 in Customized Program 11.)
    5. If online data resources capture is timeout, the program set **allows users to read offline files**. (Lines 87～113 in Customized Program 4, Lines 210～239, 267～296, 308～337, 349～378, 390～419, 431～460, 472～501, 513～542, 554～583, 595～624 and 637～666 in Customized Program 5 and Lines 197～226, 254～283, 295～324, 336～365, 377～406, 418～447, 459～488, 500～529, 541～570, 582～611 and 624～653 in Customized Program 11.)
    6. Now, this program set supports loading data resources **offline**. The recommended data resources are located under "<u>离线数据（Offline Data）</u>" under the main directory, which will **follow the update of LoL**. (Lines 671～879 in Customized Program 5 and Lines 658～866 in Customized Program 11.)
    7. This program set provides a **exception handling** mechanism for loading offline data resources. It may handle the <u>file-not-found error</u>, <u>filepath-format error</u> and <u>basic data format mismatch</u>, etc. (Lines 228～239, 285～296, 326～337, 367～378, 408～419, 449～460, 490～501, 531～542, 572～583, 613～624, 655～666, 691～696, 719～724, 733～738, 747～752, 761～766, 775～780, 789～794, 803～808, 817～822, 831～836, 845～850 and 854～873 in Customized Program 5 and Lines 215～226, 272～283, 313～324, 354～365, 395～406, 436～447, 477～488, 518～529, 559～570, 600～611, 642～653, 678～683, 706～711, 720～725, 734～739, 748～753, 762～767, 776～781, 790～795, 804～809, 818～823, 832～837 and 841～860 in Customized Program 11.)
    8. When loading data resources, users are allowed to switch **from offline mode to online mode** (Lines 672, 681～683, 876 and 877 in Customized Program 5 and Lines 659, 668～670, 863 and 864 in Customized Program 11) and **from online mode to offline mode** when *online capturing is timeout* (Lines 206, 221, 278, 319, 360, 401, 442, 483, 524, 565, 606, 648 and 667～669 in Customized Program 5 and Lines 193, 208, 265, 306, 347, 388, 429, 470, 511, 552, 593, 635 and 654～656 in Customized Program 11).
2. **[Data resource sorting]** Now, except <u>patch data</u>, all data resources are stored in the runtime environment in the form of <u>nested dictionaries</u> for the convenience of <u>indexing</u>. (**Mind the change in game mode data resource dictionary.**) (Lines 887～932, 977～985, 988～992, 1363～1366, 1435～1438, 1698～1792, 1764～1767, 2010～2013, 2059～2062, 2105～2108, 2160～2163, 2204～2207, 2586～2589, 2629～2632, 2714～2723, 2783～2791, 2846～2849 and 2884～2887 in Customized Program 5 and Lines 874～946, 1161～1164, 1233～1236, 1517～1520, 1572～1575, 1616～1619, 1833～1836, 1875～1878, 1955～1964, 2022～2030, 2082～2085 and 2120～2123 in Customized Program 11.)
3. **[Data recapture optimization]** Created a dictionary `recaptured` to reduce the printed hints on data resource capture failure. But it doesn't come into play due to a potential risk (refer to the revelant code annotation). (Lines 933～941 in Customized Program 5.)
4. **[Data initialization]** Now, when <u>all data of a summoner finish capturing and the program is going to switch to another summoner</u>, when <u>the program enters scan mode after capturing LoL match history</u>, and when <u>the program begins to fetch each match's data after capturing LoL match history</u>, the concerning data resources will **initialize**. (Lines 949～961, 1554, 1555, 1849 and 1850 in Customized Program 5 and Lines 960～972, 1384 and 1385 in Customized Program 11.)
## ⅱ. Variable Renaming
To adapt to the names of the variables regarding the new functions, a great number of variables in the old program are renamed in this update.
1. Now, non-iterable variables that semantically belong to LoL product are prefixed with "<u>LoL</u>" or include "<u>LoL</u>", and **their singular/plural declension is unified** (variables named in singular form are defined as intermediate data or iterators; the plural are defined as the data container finally put into use, usually **dictionaries**). (Non-iterable variables that semantically belong to TFT product are prefixed with "TFT" or include "TFT", but since they're just added in this update, instead of being renamed into from old variables, they won't be listed here.)
    1. **item → <font color=#ff0000>LoL</font>Item** and **items → <font color=#ff0000>LoL</font>Items**. (Lines 953, 1420, 1435, 1438, 1444, 1451, 1458, 1465, 1472, 1479, 1486, 1555, 1724, 1727, 1730, 1733, 1736, 1739, 1742, 1746, 1749, 1764, 1765, 1767, 1773, 1780, 1787, 1794, 1801, 1808, 1815, 1850, 2036, 2040, 2043, 2059, 2060, 2062 and 2064 in Customized Program 5 and Lines 964, 1193, 1196, 1199, 1202, 1205, 1208, 1211, 1218, 1233, 1234, 1236, 1242, 1249, 1256, 1263, 1270, 1277, 1284, 1385, 1474, 1476, 1477 and 1481 in Customized Program 11.)
    2. **champion → <font color=#ff0000>LoL</font>Champion** and **championId → <font color=#ff0000>LoL</font>Champions**. (Lines 988～990, 992, 1070, 1073, 1325, 1329, 1973, 1978, 2241, 2246, 2333 and 2340 in Customized Program 5 and Lines 887～889, 891, 1123, 1127, 1460 and 1462 in Customized Program 11.)
    3. **Hints on input**. (Lines 1189, 1210, 1223, 1231, 1233, 1288, 1417, 1429, 1434, 1507, 1551, 1746, 1758, 1763, 2040, 2052, 2058 and 2952 in Customized Program 5 and Lines 1006, 1025, 1086, 1215, 1223, 1227, 1232, 1658, 2410 and 2424 in Customized Program 11.)
    4. **history_get → <font color=#ff0000>LoL</font>History_get**. (Lines 1192, 1209, 1230, 1242 and 1246 in Customized Program 5 and Lines 1007, 1024, 1028, 1040 and 1044 in Customized Program 11.)
    5. **history → <font color=#ff0000>LoL</font>History**. (Lines 1195, 1196, 1199, 1200, 1204, 1207, 1208, 1221, 1233, 1235 and 1280 in Customized Program 5 and Lines 1010, 1011, 1014, 1015, 1019, 1022, 1023, 1031, 1033 and 1078 in Customized Program 11.)
    6. **Txt file renaming**. (Lines 1212, 1538, 1916 and 1934 in Customized Program 5.)
    7. **history_header → <font color=#ff0000>LoL</font>History_header**. (Lines 1248, 1500, 1501, 1830 and 1831 in Customized Program 5 and Lines 1046, 1298 and 1299 in Customized Program 11.)
    8. **gamePlayed → <font color=#ff0000>LoL</font>GamePlayed**. (Lines 1249, 1287, 1504 and 2370 in Customized Program 5 and Lines 1047, 1085 and 1302 in Customized Program 11.)
    9. **itemID → <font color=#ff0000>LoL</font>ItemID**. (Lines 1394, 1397, 1400, 1403, 1406, 1409, 1412, 1417, 1431, 1723, 1726, 1729, 1732, 1735, 1738, 1741, 1746, 1760, 2029, 2031, 2032, 2036, 2054, 2064, 2066 and 2067 in Customized Program 5 and Lines 1192, 1195, 1198, 1201, 1204, 1207, 1210, 1215, 1229, 1480, 1481 and 1483 in Customized Program 11.)
    10. **item_recapture → <font color=#ff0000>LoL</font>Item_recapture**. (Lines 1416, 1417, 1424, 1425, 1427～1429, 1745, 1753, 1754, 1756～1758, 1962, 2039, 2040, 2047, 2048 and 2050～2052 in Customized Program 5 and Lines 1214, 1215, 1222, 1223 and 1225～1227 in Customized Program 11.)
    11. **history_data → <font color=#ff0000>LoL</font>History_data**. (Lines 1499, 1501, 1829, 1831 and 1832 in Customized Program 5 and Lines 1297, 1299 and 1300 in Customized Program 11.)
    12. **history_df → <font color=#ff0000>LoL</font>History_df**. (Lines 1502, 1503, 1505, 1832, 2930, 2949, 2951, 2999 and 3001 in Customized Program 5 and Lines 1300, 1301 and 1303 in Customized Program 11.)
    13. **matchIDs → <font color=#ff0000>LoL</font>MatchIDs**. (Lines 1508, 1534, 1539, 1540, 1544～1547, 1550, 1587, 1680, 1746, 1758, 1828, 1836, 1838, 1842, 1843, 1851, 1953, 1991, 2005, 2017, 2040, 2054, 2066, 2086, 2100, 2112, 2141, 2155, 2167, 2185, 2199, 2211 and 2374 in Customized Program 5 and Lines 1335, 1337, 1341, 1342, 1346～1349, 1352, 1359, 1361, 1365, 1366, 1388, 1498, 1512, 1524, 1553, 1567, 1579, 1597, 1611, 1623 and 1645 in Customized Program 11.)
    14. **game_info → <font color=#ff0000>LoL</font>Game_info**。(Lines 1588, 1591, 1593, 1595, 1599, 1602, 1603, 1606, 1610, 1613, 1618, 1619, 1624, 1625, 1628, 1630, 1632, 1634, 1637, 1638, 1642, 1643, 1645, 1647, 1661, 1665, 1667, 1668, 1670, 1671, 1705, 1707, 1709, 1711, 1713, 1852, 1853, 1858, 1860, 1864, 1868, 1868, 1872, 1875, 1879, 1882, 1883, 1889, 1890, 1893, 1894, 1898, 1925, 1961, 1968, 1970, 1973, 1978, 1978, 1982, 1989, 2024, 2026, 2029, 2031, 2038, 2076, 2084, 2122～2124, 2130, 2132, 2139, 2175, 2183, 2222, 2224, 2226, 2228, 2230, 2298, 2324, 2328, 2333, 2340 and 2342 in Customized Program 5 and Lines 1389, 1390, 1393, 1395, 1398, 1402, 1405, 1406, 1408, 1412, 1415, 1419, 1420, 1425, 1428, 1429, 1430, 1432, 1433, 1434, 1438, 1440, 1444, 1446, 1449, 1451, 1454, 1456, 1458, 1464, 1488, 1496, 1534～1536, 1542, 1544, 1551, 1587, 1595, 1634, 1636 and 1638 in Customized Program 11.)
    15. **game_timeline → <font color=#ff0000>LoL</font>Game_timeline**. (Lines 1854, 1855, 1943, 2264, 2266, 2270, 2273, 2274, 2277, 2281, 2284, 2285, 2292, 2296, 2303 and 2364 in Customized Program 5.)
    16. **game_info_error → <font color=#ff0000>LoL</font>Game_info_error**. (Lines 1893 and 1894 in Customized Program 5.)
    17. **game_info_df → <font color=#ff0000>LoL</font>Game_info_df**. (Lines 1894, 1913, 1961, 1968, 1970, 1973, 1978, 1980, 2254～2261, 2304, 2364, 2365 and 2368 in Customized Program 5.)
    18. **game_info_header → <font color=#ff0000>LoL</font>Game_info_header**. (Lines 1954, 1963 and 2253 in Customized Program 5 and Lines 1374, 1376 and 1657 in Customized Program 11.)
    19. **game_info_data → <font color=#ff0000>LoL</font>Game_info_data**. (Lines 1955, 1965, 1968, 1970, 1973, 1975, 1978, 1980, 1982, 2022, 2024, 2026, 2033, 2071, 2078, 2128, 2130, 2134, 2172, 2177, 2220, 2222, 2224, 2234, 2236, 2241, 2243, 2246, 2248 and 2253 in Customized Program 5 and Lines 1375, 1387, 1438, 1442, 1444, 1447, 1449, 1452, 1454, 1456, 1460, 1462, 1466, 1468, 1471, 1478, 1481, 1483, 1490, 1540, 1542, 1546, 1584, 1589, 1632, 1634, 1636, 1639, 1641, 1643 and 1657 in Customized Program 11.)
    20. **game_info_header_keys → <font color=#ff0000>LoL</font>Game_info_header_keys**. (Lines 1956, 1964, 2075, 2122～2124, 2174 and 2252 in Customized Program 5 and Lines 1376, 1386, 1435, 1436, 1487, 1534～1536, 1586 and 1656 in Customized Program 11.)
    21. **game_info_statistics_display_order → <font color=#ff0000>LoL</font>Game_info_statistics_display_order**. (Lines 2249 and 2251 in Customized Program 5.)
    22. **game_info_data_organized → <font color=#ff0000>LoL</font>Game_info_data_organized**. (Lines 2250, 2253 and 2254 in Customized Program 5.)
    23. **game_timeline_error → <font color=#ff0000>LoL</font>Game_timeline_error**. (Lines 2296 and 2297 in Customized Program 5.)
    24. **game_timeline_df → <font color=#ff0000>LoL</font>Game_timeline_df**. (Lines 2297, 2363～2365 and 2369 in Customized Program 5.)
    25. **game_timeline_header → <font color=#ff0000>LoL</font>Game_timeline_header**. (Lines 2300, 2300, 2304 and 2362 in Customized Program 5.)
    26. **game_timeline_data → <font color=#ff0000>LoL</font>Game_timeline_data**. (Lines 2301, 2306, 2309, 2311, 2314, 2316, 2320, 2324, 2328, 2333, 2335, 2340, 2342, 2347, 2349, 2355, 2357 and 2362 in Customized Program 5.)
    27. **game_timeline_header_keys → <font color=#ff0000>LoL</font>Game_timeline_header_keys**. (Lines 2302, 2305 and 2361 in Customized Program 5.)
    28. **game_timeline_statistics_display_order → <font color=#ff0000>LoL</font>Game_timeline_statistics_display_order**. (Lines 2358 and 2360 in Customized Program 5.)
    29. **game_timeline_data_organized → <font color=#ff0000>LoL</font>Game_timeline_data_organized**. (Lines 2359, 2362 and 2363 in Customized Program 5.)
    30. **Sheet renaming**. (Lines 2949, 2951, 2993, 2998, 2999, 3001, 3002, 3005 and 3006 in Customized Program 5 and Lines 2409, 2423, 2498 and 2508 in Customized Program 11.)
    31. **error_matchIDs → error_<font color=#ff0000>LoL</font>MatchIDs**. (Lines 1378 and 1421 in Customized Program 11.)
    32. **gameDuration_raw → <font color=#ff0000>LoL</font>GameDuration_raw**. (Lines 1380, 1441 and 2187 in Customized Program 11.)
    33. **recent_players_statistics_display_order → recent_<font color=#ff0000>LoL</font>Players_statistics_display_order**. (Lines 1653, 1655, 1656 and 1658 in Customized Program 11.)
    34. **recent_players_data_organized → recent_<font color=#ff0000>LoL</font>Players_data_organized**. (Lines 1654, 1657, 1660 in Customized Program 11.)
    35. **recent_players_df → recent_<font color=#ff0000>LoL</font>Players_df**. (Lines 1660, 1663～1668, 2183～2190, 2221, 2409, 2423, 2479, 2480 and 2488 in Customized Program 11.)
    36. **gameDuration_iter → <font color=#ff0000>LoL</font>GameDuration_iter**. (Lines 2187, 2196, 2203～2206, 2210 and 2217～2220 in Customized Program 11.)
    37. **ally_df_to_print → <font color=#ff0000>LoL</font>Ally_df_to_print**. (Lines 2471, 2489, 2518 and 2526 in Customized Program 11.)
    38. **ally_index → <font color=#ff0000>LoL</font>Ally_index**. (Lines 2477, 2481, 2486, 2488, 2497, 2501, 2507 and 2511 in Customized Program 11.)
    39. **ally_df → <font color=#ff0000>LoL</font>Ally_df**. (Lines 2488, 2489, 2498 and 2508 in Customized Program 11.)
2. Some other variables are renamed according to their **actual meaning**.
    1. Now, the second formal parameter of function `FindPostPatch` is renamed into <u>patchList</u> to be distinguished from `patches` in the subsequent async functions. (Lines 116, 117, 123, 126, 130 and 136 in Customized Program 5 and Lines 118, 119, 125, 128, 132 and 138 in Customized Program 11.)
    2. Without specific explanations, all variables that store the text file names are named in the format of "<u>txtfile[number]</u>". (Lines 1018, 1024, 1027, 1047, 1053, 1056, 1115, 1121, 1124, 1215, 1221, 1224, 1919, 1925, 1929, 1937, 1943, 1947, 2400, 2406, 2409, 2465, 2471 and 2475 in Customized Program 5 and Lines 2266 and 2272 in Customized Program 11.)
    3. The variable "game<font color=#ff0000>s</font>" in Customized Programs 5 and 11 now refers to <u>a player's all matches</u>, while the variable "game" refers to <u>one game</u>. (Lines 1280, 1281, 1283, 1292, 1292, 1294, 1296, 1298, 1301, 1302, 1306, 1307, 1309, 1311, 1325, 1329, 1331, 1332, 1334, 1335, 1344, 1358, 1359, 1368, 1370, 1371, 1376, 1378, 1380, 1382, 1384, 1417 and 1431 in Customized Program 5 and Lines 1078, 1079, 1081, 1090, 1092, 1094, 1096, 1099, 1100, 1104, 1105, 1107, 1109, 1123, 1127, 1129, 1130, 1132, 1133, 1142, 1156, 1157, 1166, 1168, 1169, 1174, 1176, 1178, 1180, 1182, 1215 and 1229 in Customized Program 11.)
    4. Now, the variable that stores the current time in Customized Program 9 is named as <u>`currentTime`</u>, corresponding to that in Customized Program 5. This is because in the old version, Customized Program 9 directly took time as the sheet's name, so the variable is named as `sheetname`. But in this update, the sheet name isn't only composed of time, so it feels somehow unsuitable to use "sheetname" to store the time. (Lines 139～141 and 144～146 in Customized Program 9.)
    5. In the part that captures match history, a list that stores names of game mode is renamed from "name" into <u>`gameModeName`</u>. (Lines 1046, 1056, 1102 and 1105 in Customized Program 9.)
    6. In the part that generates bar charts, the variable regarding game duration is now named as <u>`playtime`</u> to be distinguished from `time` library. (Lines 2326, 2327, 2336, 2337, 2346, 2347, 2356, 2357, 2366, 2367, 2376, 2377, 2386, 2387, 2396 and 2397 in Customized Program 9.)
## ⅲ. Improvement of the Exception Handling Mechanism
1. **Specified the error type when generating text files.** Now, folder are created only when the program throws <u>FileNotFoundError</u>. (Lines 1019, 1048, 1116, 1216, 1920, 1938, 2401 and 2466 in Customized Program 5 and Lines 2267 in Customized Program 11.)
2. When the program is recapturing data resources using the function `requests.get`, it can **distinguish between <u>TimeOut</u> and <u>404NotFound</u>**. (Lines 1348～1360, 1421～1432, 1683～1696, 1749～1761, 1995～2007, 2044～2056, 2090～2102, 2145~2157, 2189～2201, 2571～2583, 2614～2626, 2699～2711, 2768～2780, 2831～2843 and 2849～2881 in Customized Program 5 and Lines 1146～1158, 1219～1231, 1502～1514, 1557～1569, 1601～1613, 1821～1833, 1863～1875, 1943～1955, 2010～2022, 2070～2082 and 2108～2120 in Customized Program 11.)
3. When the program is fetching match information according to matchID, it can distinguish whether the corresponding match is a TFT match. However, it's not *applied* yet, waiting for development in the near future. (Lines 1883 and 1884 in Customized Program 5.)
## ⅳ. Intermediate Variable Exportion
For the convenience of debugging the program, code involving <u>`pickle`</u> library are added. These codes **export variables into local files in the binary form**. The benefits of these files are as follows:
1. Inspect the errors that occur during the execution of the program.
2. Preserved as history data.\
Considering the second reason, some pkl files' names contain the time when running. But a problem of this operation is that repetitive capture results in the multiplication of the intermediate files. Therefore, to simplify the output, all code involving `pickle` library are commented out currently. Please decide on your personal usage whether to uncomment those code regions.\

(Lines 2, 1030～1032, 1059～1061, 1127～1129, 1226～1228, 1931～1933, 1949～1951, 2411～2413 and 2477～2479 in Customized Program 5 and Lines 1692～1694 in Customized Program 11.)
## ⅴ. Variable Redefinition (Customized Program 5)
1. 6 variables are *redefined* with a new type in this update:
    1. `game_info_dfs`. (Lines 1180, 2368, 2910, 2925, 2960 and 3017.)
    2. `game_timeline_dfs`. (Lines 1181, 2369, 2962 and 3019.)
    3. `info_exist_error`. (Lines 1184, 1891, 1912, 2483, 2959, 2969, 2971, 2973, 3016, 3026, 3028 and 3030.)
    4. `timeline_exist_error`. (Lines 1185, 2293, 2299, 2366, 2484, 2961, 2969, 2971, 2973, 3018, 3026, 3028 and 3030.)
    5. `main_player_included`. (Lines 1186, 1901, 1904, 2485, 2963 and 3020.)
    6. `match_reserve_strategy`. (Lines 1187, 1902, 1909, 1911, 2486, 2958, 2964, 3015 and 3021.)
    \
    Now they're <font color=#ff0000>dictionaries</font>, not <font color=#ff0000>lists</font> anymore. This change helps to **sort the mix of LoL and TFT match information and timeline sheets according to matchIDs (key)**.
2. In the parts that append elements to lists that compose a dataframe, codes are simplified by **introducing the variable <font color=#ff0000>`to_append`</font>** in many <u>discussion</u> or <u>exception handling</u> cases. (Lines 1987, 2006, 2015, 2018, 2022, 2036, 2055, 2064, 2067, 2071, 2119, 2125, 2127, 2128, 2137, 2156, 2165, 2168, 2172, 2217, 2219, 2220, 2501, 2502, 2520, 2521, 2563, 2582, 2591, 2594, 2599, 2600, 2602, 2625, 2637, 2640, 2643, 2644, 2646, 2655, 2656, 2658, 2662, 2664, 2665, 2667, 2669, 2670, 2672, 2674, 2675, 2677, 2686, 2689, 2691, 2710, 2726, 2728, 2730, 2734, 2736, 2740, 2742, 2756, 2760, 2779, 2793, 2797, 2800, 2806, 2808, 2810, 2811, 2813, 2823, 2842, 2851, 2854, 2861, 2880, 2889, 2892, 2896 and 2898 in Customized Program 5 and Lines 1531, 1537, 1539, 1540, 1549, 1568, 1577, 1580, 1584, 1629, 1631, 1632, 1747, 1748, 1771, 1772, 1813, 1832, 1841, 1844, 1849, 1851, 1874, 1886, 1889, 1892, 1894, 1903, 1905, 1909, 1911, 1913, 1915, 1917, 1919, 1921, 1930, 1932, 1933, 1935, 1970, 1972, 1974, 1978, 1980, 1985, 1998, 2002, 2021, 2035, 2039, 2042, 2048, 2051, 2053, 2062, 2081, 2090, 2093, 2100, 2119, 2128, 2131 and 2136 in Customized Program 11.)
## ⅵ. Main Data Update
Sorted <u>**LoL runes**</u> (Lines 2072～2172 in Customized Program 5 and Lines 1484～1584 in Customized Program 11), <u>**Arena augments**</u> (Lines 2173～2220 in Customized Program 5 and Lines 1585～1623 in Customized Program 11) and <u>**TFT**</u> (Lines 2381～2921 in Customized Program 5 and Lines 1675～2169 in Customized Program 11) data are added to the updated program set.\
Note that when sorting out the TFT data, the program manages the match information and match history *at the same time*. This is because <u>no available API exists for TFT match information query based on matchID</u>.
## ⅶ. Other Changes
### (ⅰ) Overall Change
Now, according to Tencent's translation of "Match History", all "<u>对局历史</u>"s are replaced by "<u>**对局记录**</u>"s.
### (ⅱ) Customized Program 4
1. Defined an insertion sort function `patch_sort(patchList)` to **sort the patches crawled through <u>Inspect Element</u> of CommunityDragon database homepage**. (Lines 47～60 and Lines 141 and 154 in Customized Program 5. *This function isn't called in Cutomized Program 5. The reason why this newly defined function appears in the context of Customized Program 5 is that this program is regarded as the development origin of other Customized Programs.*)
2. Added codes that **capture and sort out champion data from CommunityDragon database**. (Lines 210～228.)
3. Optimized **Champion data source selection**. To reduce the cases of exception handling as much as possible, the program only makes judgments on **the first character of a nonempty input string**. (Lines 64, 65, 117 and 128.)
### (ⅲ) Customized Program 5
1. Fixed an error when **searching champion mastery information**. (Lines 1040～1042.)
2. Now, the program **allows users to decide whether to search the LoL or TFT match history**. (Lines 1189, 1190, 2379 and 2380.)
3. Corrected a **comment mistake**, because the file it refers to has finished format modification long before. (Line 467 in the original code.)
4. Now, when the program prompts the input of the beginning and ending indices, the suggested type is "**nonnegative integer**" instead of "integer". (Line 1531.)
5. Improved **the rule for extracting matches in Scan Mode**. (Line 1538.)
6. Defined the variable `augment_rarity` to evaluate the level of Arena augment strength. (Lines 1959～2217.)
7. Rearranged **the order of empty-sheet placeholders**. Now, after creating a new workbook, the expected order of the first 8sheets should be account information, ranked data, chamoion mastery, recently played LoL players' data, recently played TFT players' data, LoL match history, Local Rechecked LoL match history and TFT match history in turns. (Lines 2928～2932, 2998, 3002, 3005, 3006 and 3012.)
### （ⅳ）Customized Program 9
Fixed a key error: <u>Added the **Emerald** rank</u>. (Line 72.)
### (ⅴ) Customized Program 11
1. Now, the program **allows users to decide whether search and export TFT match history**. (Lines 1672, 1673, 2222, 2411, 2425, 2482, 2499, 2509, 2519 and 2527.)
2. Now, when the program prompts the input of the beginning and ending indices or the beginning index and the match counts, the suggested type is "**nonnegative integer**" instead of "integer". (Lines 1330 and 2161.)
3. An update that doesn't matter at all: the colon in lambda function ~~must~~ be followed by a space. (Lines 2294～2301.)
4. Supplemented **the discussion about gameflow state**: added the gameflow states of <u>Honor A Teammate</u> and <u>Waiting for Stats</u>. (Line 2460.)
### (ⅵ) Customized Program 12 - Loot Sorting Program (**New**)
1. This program inherits the file saving mechanism from Customized Program 9: text files and xlsx workbooks are saved under <u>the corresponding summoner's folder specified by Customized Program 5</u>. There'll be an update about the prompts on text file generation *in the next commit*. (Lines 59～97 and 133～154.)
2. This program defines dictionary variables including `essenceType`, `lootCategories`, `itemStatus`, `rarity`, `redeemableStatus` and `lootType` to transform some important data into **the form understandable for Chinese users**. There may be some mistakes in the translation, so any correction is welcome to put forward. (Lines 101～106.)
3. This program only **cralws and sorts out data**. For further demands, please perform the corresponding analysis on the Excel workbook under the main summoner's folder by yourself.
### (ⅶ) Main Dataframe Structure
1. Names of sheets that represent the dataframes in Customized Programs 5 and 11 now differentiate between LoL and TFT.
2. Following the principle that "You may remove the data excess, but you can't make up for data loss", <u>summonerIconId</u> and <u>puuid</u> are added into the sheet `05 - LoLgame_info_header` (originally `game_info_header`).
3. Added the details of headers of <u>TFT match history dataframe</u> (`05 - TFTHistory_header`), <u>TFT match information dataframe</u> (`05 - TFTGame_info_header`), <u>recently played TFT players' data</u> (`11 - recent_TFTPlayers_header`) and <u>player loot dataframe</u> (`12 - player_loot_header`).
### (ⅷ) `清除临时文件` bat file
Now, intermediate **pkl** files generated under the corresponding summoner's folder by Customized Program 5 can be deleted by this bat file.
### (ⅸ) Offline Data
Now, this new repository provides PBE data resources.
### (ⅹ) README
1. Updated the location of other explanations. (Line 4.)
2. Modified an expression in Chinese declaration. (Line 6.)
3. Corrected the number of note to refer to about customized programs. (Line 211.)
4. Removed statements of Available Lobby Information and added statements of Offline Data Resources. (Lines 245～247.)
5. Supplemented several needed Python libraries. (Lines 271～273.)
6. Declared the source of data resources in Customized Program 5. (Line 294.)
7. Corrected some terms of the workbook generated by Customized Program 5: "工作簿" -> "工作表". (Lines 94～97 and 103.)
8. Updated sheet composition involving match history. (Lines 300～304.)
9. Added a statement of [Local Recheck]. (Line 311.)
10. Removed a future plan, for it's been achieved in this update. (Line 263 in the original document.)
11. Added an instruction of Customized Program 6. (Line 315.)
12. Removed the statement about reformatting the store items' information text in Customized Program 7, because this reformatting work is implemented in this program in this update. (Line 267 in the original document.)
13. Polished some text with bold or underlined format. (Lines 326, 327, 332 and 404.)
14. Adaptively adjusted the names of dataframe variables and the sheet names in the main dataframe structure workbook. (Lines 338～342 and 361～369.)
15. Corrected a type of grammatical mistake: singular/plural declension. (Lines 346～350, 356, 363～367, 370～373, 376～379, 381 and 386～389.)
16. Added explanations of main data region of sheets involving TFT match history dataframe (`05 - TFTHistory_header`), TFT match information dataframe (`05 - TFTGame_info_header`), recently played TFT summoners dataframe (`11 - recent_TFTPlayers_header`) and player loot dataframe (`12 - player_loot_header`).
17. Modified a grammatical mistake in Afterwords: "Call API" isn't a legal usage, for "call" is usually together with "function". (Line 329 in the original code.)
# Ⅲ. Future Plans & Ideas
1. **Optimize TFT data structure according to others' opinions.**\
Because TFT match history is stored in the form of **nested dictionaries** in LCU API, but it has to be reduced to a *two-dimension table* to be exported into Excel, you may see that there're large quantities of *fields*. And to display so many fields is just a preliminary decision. Without any constructive ideas, I'll keep the way it is now.
2. **Add a scoring system in Customized Program 11.**\
While counting players in the past few years using Scan Mode, those who played with us several years ago are somehow different from those who played with us several days ago, and it's game creation date that makes a difference. So I'm planning to introduce into this program a model to calculate the correspondence for players to encounter one another. This model should take at least two factors including <u>game length</u> and <u>game creation date</u> into consideration.
3. Scan mode for TFT matches <font color=#ff0000>(×)</font>\
First of all, I want to declare that I'm not planning to add this function to this program set. Although matchID in TFT product does make sense, but the API `/lol-match-history/v1/games/{gameId}` doesn't work for accessing a TFT match's information. On the other hand, the **main principle** of Scan Mode is to extract a player's matchIDs from local files and then to recheck a match's information using the matchID and the API. That's why Scan Mode got another name: "Local Recheck".\
Hence, suppose we're going to choose Scan Mode on TFT text files. Then the program shouldn't recheck through LCU API. Instead, it should directly read in those previously saved text files. Oh, since I've described the algorithm, maybe I could do this, couldn't I? Yes, I could. But there exists such a case: **data in the local folders aren't all automatically generated by the programs; users may have edited or designed the text files.** Now things become complicated. Moreover, my program can't evaluate the correctness of each TFT match text file.\
Someone might say, "There should be a way to determine TFT match data format! <u>You may set an `if` statement. If the text files can be read in a way like reading json files, data from the text file are of dictionary type, and the keys of the dictionary is specified</u>, that should meet the demands, shouldn't that?" I'll answer: I could, but risks may also emerge. **Firstly,** if I need to judge whether the format of the read data complies with the format of real match data, then I must make the format defined in the program correspond <font color=#ff0000>perfectly</font> with that reflected in **LCU API**. For example, I need to specify keys of all layers and the types of all values. In that sense, this single `if` statement will become **too long**. **Another unfortunate fact is**, the format of TFT match information may <font color=#ff0000>vary at any time</font>, which I especially complained about during this grand update. 😤 There lies certain **disunity**, even <font color=#ff0000>strong</font>, among different patches of TFT data format. (This phenomenon doesn't just occur in TFT match history; it exists in almost all other data resources. For example, you may check the data format of the following two links: [latest TFT champion information](https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/zh_cn/v1/tftchampions.json) and [TFT champion information of Patch 10.1](https://raw.communitydragon.org/10.1/plugins/rcp-be-lol-game-data/global/zh_cn/v1/tftchampions.json).) I must confirm that the program is executable in face of all patches of matches. (Because when you want to load match history using Scan Mode, the matches usually turn out to be relatively **old**.) Then, an interesting thing may happen: <u>I define a set of rules for importing TFT match history, and soon the rules are updated</u>🥹\
Now, someone might say, "Actually you don't need to specify the rules so thoroughly. <u>You're just doing the over-fitting work. Simply setting several proofreading rules should be enough, and also friendly for later update when the data format changes again.</u>" If you think so, then I'm afraid I'm not being friendly to the later format change, but being tolerant of <u>illegal data format</u>. **On the one hand,** if the format of some data complies with the rough rules, but inside the data there's something that is totally nonsense, then the code to sort out data won't run, and the program will raise an error. **On the other hand,** if the format of some data is exactly correct, and the program is executed successfully, but some data in it is fake, then one could say the program acts as a **history fabricator**. (And this problem can't be solved despite the exact format defined in the program.)\
All in all, the main idea of designing Scan Mode is to extract matchIDs from local files and redownload data through network</u>. Since TFT **doesn't support** *getting match information through matchIDs*, Scan Mode **won't** be supported for TFT matches. The only secure way is <u>for LoL developer to make TFT match information API through matchIDs accessible</u>. Or maybe I find a way to solve GAMHS data format some day, when the Scan Mode of TFT matches will be added to agenda.
4. Available lobby data addition (×)
5. LoL match history update (×)\
Although the structure of the original game information data (currently `LoLGame_info_data`) has been updated this time, that of LoL match history data (currently `LoLHistory_df`) doesn't appear to be changed. The reason is, in League client, the layout of "Match History" in "Profile" is relatively **fixed**. Since the format of the match history table generated by Customized Program 5 is **based on the League client**, I'm not considering updating LoL match history data structure temporarily.