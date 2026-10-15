Attribute VB_Name = "冻结窗格"
Sub FreezeAndFilterGameDataSheets()
    '设置要处理的工作表（Set sheets to operate）
    Dim sheetDict As Object
    Set sheetDict = CreateObject("Scripting.Dictionary") '这两个语句等价于`Dim sheetDict As New Dictionary`，但是这种写法要求导入“Microsoft Scripting Runtime”工具（These two statements are equivalent to `Dim sheetDict as New Dictionary`, except the latter requires "Microsoft Scripting Runtime"）
    Dim suffixDict As Object
    Set suffixDict = CreateObject("Scripting.Dictionary")
    sheetDict.Add "指令集（CheatSet）", 13
    sheetDict.Add "指令（Cheat）", 9
    sheetDict.Add "符文系（PerkStyles）", 15
    sheetDict.Add "符文（Perks）", 9
    sheetDict.Add "召唤师技能（Summoner Spells）", 22
    sheetDict.Add "英雄（Champions）", 13
    sheetDict.Add "英雄技能（Champion Spells）", 21
    sheetDict.Add "角色（Characters）", 14
    sheetDict.Add "角色技能（Character Spells）", 22
    sheetDict.Add "装备（Items）", 9
    sheetDict.Add "装备分组（Item Groups）", 17
    sheetDict.Add "装备修饰（Item Modifiers）", 20
    sheetDict.Add "斗魂竞技场强化符文（Cherry Augments）", 26
    sheetDict.Add "无尽狂潮强化（Swarm Augments）", 22
    sheetDict.Add "海克斯大乱斗强化符文（Kiwi Augments）", 25
    sheetDict.Add "海克斯大乱斗强化符文套装（Kiwi Augment Set）", 30
    sheetDict.Add "强化符文修饰（Augment Modifiers）", 25
    sheetDict.Add "海克斯大乱斗任务线（Kiwi Questlines）", 26
    sheetDict.Add "海克斯大乱斗经典强化符文（KiwiJade Augments）", 31
    sheetDict.Add "斗魂竞技场锻造器（Cherry Anvils）", 23
    sheetDict.Add "海克斯大乱斗锻造器（Kiwi Anvils）", 22
    sheetDict.Add "海克斯大乱斗进度追踪（Kiwi Progress Track）", 31
    sheetDict.Add "海克斯大乱斗奖励分组（Kiwi Reward Group）", 29
    sheetDict.Add "海克斯大乱斗奖励（Kiwi Reward）", 21
    sheetDict.Add "海克斯大乱斗大型任务（Kiwi Quest）", 22
    sheetDict.Add "海克斯大乱斗任务里程碑（Kiwi Quest Milestone）", 33
    sheetDict.Add "海克斯大乱斗任务里程碑（Kiwi Quest Mileston", 31
    sheetDict.Add "海克斯大乱斗小型任务（Kiwi Mission）", 24
    sheetDict.Add "经典模式进度追踪（Jade Progress Track）", 29
    sheetDict.Add "经典模式奖励分组（Jade Reward Group）", 27
    sheetDict.Add "斗魂竞技场回合列表（Cherry Round List）", 28
    sheetDict.Add "斗魂竞技场回合（Cherry Round）", 21
    sheetDict.Add "斗魂竞技场阶段（Cherry Phase）", 21
    sheetDict.Add "斗魂竞技场回合阶段（Cherry Round Phase）", 29
    sheetDict.Add "斗魂竞技场场景英雄（Cherry Cameos）", 24
    sheetDict.Add "斗魂竞技场荣誉嘉宾（Cherry Guests）", 24
    sheetDict.Add "海克斯大乱斗乐队（Kiwi Bands）", 20
    sheetDict.Add "云顶之弈赛季（TFT Set）", 15
    sheetDict.Add "云顶之弈商店（TFT Shop）", 16
    sheetDict.Add "云顶之弈商店内容（TFT Shop Content）", 26
    sheetDict.Add "云顶之弈掉率表（TFT Drop Rate）", 22
    sheetDict.Add "云顶之弈回合阶段（TFT Stage Round）", 25
    sheetDict.Add "云顶之弈回合（TFT Round）", 17
    sheetDict.Add "云顶之弈传送门（TFT Portal）", 19
    sheetDict.Add "云顶之弈开场奇遇（TFT Encounter Distribution）", 36
    sheetDict.Add "云顶之弈开场奇遇（TFT Encounter Distribu", 31
    sheetDict.Add "云顶之弈奇遇（TFT Encounter）", 21
    sheetDict.Add "云顶之弈单位属性（TFT Unit Property）", 27
    sheetDict.Add "云顶之弈角色定位（TFT Character Role）", 28
    sheetDict.Add "云顶之弈装备列表（TFT Item List）", 23
    sheetDict.Add "云顶之弈装备（TFT Items）", 17
    sheetDict.Add "云顶之弈羁绊列表（TFT Trait List）", 24
    sheetDict.Add "云顶之弈羁绊（TFT Traits）", 18
    sheetDict.Add "云顶之弈电脑玩家英雄（TFT PVE NPC）", 23
    sheetDict.Add "云顶之弈脚本（TFT Script）", 18
    sheetDict.Add "云顶之弈通告（TFT Announcement）", 24
    sheetDict.Add "字体描述（Font Description）", 22
    sheetDict.Add "字体类型（Font Types）", 16
    sheetDict.Add "字体分辨率（Font Resolution）", 22
    sheetDict.Add "字体样式（Font Style）", 16
    sheetDict.Add "CSS样式（CSS Style）", 16
    sheetDict.Add "内嵌图标（Inline Icons）", 18
    suffixDict.Add "CheatSet", 8
    suffixDict.Add "Cheat", 5
    suffixDict.Add "PerkStyles", 10
    suffixDict.Add "Perks", 5
    suffixDict.Add "SummonerSpells", 14
    suffixDict.Add "Champions", 9
    suffixDict.Add "ChampionSpells", 14
    suffixDict.Add "Characters", 10
    suffixDict.Add "CharacterSpells", 15
    suffixDict.Add "Items", 5
    suffixDict.Add "ItemGroups", 10
    suffixDict.Add "ItemModifiers", 13
    suffixDict.Add "CherryAugments", 14
    suffixDict.Add "SwarmAugments", 13
    suffixDict.Add "KiwiAugments", 12
    suffixDict.Add "KiwiAugmentSet", 14
    suffixDict.Add "AugmentModifiers", 16
    suffixDict.Add "KiwiQuestlines", 14
    suffixDict.Add "KiwiJadeAugments", 16
    suffixDict.Add "CherryAnvils", 12
    suffixDict.Add "KiwiAnvils", 10
    suffixDict.Add "KiwiProgressTrac", 16
    suffixDict.Add "KiwiProgressTrack", 17
    suffixDict.Add "KiwiRewardGroup", 15
    suffixDict.Add "KiwiReward", 10
    suffixDict.Add "KiwiQuest", 9
    suffixDict.Add "KiwiQuestMilesto", 16
    suffixDict.Add "KiwiQuestMileston", 17
    suffixDict.Add "KiwiQuestMilestone", 18
    suffixDict.Add "KiwiMission", 11
    suffixDict.Add "JadeProgressTrac", 16
    suffixDict.Add "JadeProgressTrack", 17
    suffixDict.Add "JadeRewardGroup", 15
    suffixDict.Add "CherryRoundList", 15
    suffixDict.Add "CherryRound", 11
    suffixDict.Add "CherryPhase", 11
    suffixDict.Add "CherryRoundPhase", 16
    suffixDict.Add "CherryCameos", 12
    suffixDict.Add "CherryGuests", 12
    suffixDict.Add "KiwiBands", 9
    suffixDict.Add "TFTSet", 6
    suffixDict.Add "TFTShop", 7
    suffixDict.Add "TFTShopContent", 14
    suffixDict.Add "TFTDropRate", 11
    suffixDict.Add "TFTStageRound", 13
    suffixDict.Add "TFTRound", 8
    suffixDict.Add "TFTPortal", 9
    suffixDict.Add "TFTEncounterDistribution", 24
    suffixDict.Add "TFTEncounterDistr", 17
    suffixDict.Add "TFTEncounter", 12
    suffixDict.Add "TFTUnitProperty", 15
    suffixDict.Add "TFTCharacterRole", 16
    suffixDict.Add "TFTItemList", 11
    suffixDict.Add "TFTItems", 8
    suffixDict.Add "TFTTraitList", 12
    suffixDict.Add "TFTTraits", 9
    suffixDict.Add "TFTPVENPC", 9
    suffixDict.Add "TFTScript", 9
    suffixDict.Add "TFTAnnouncement", 15
    suffixDict.Add "FontDescription", 15
    suffixDict.Add "FontTypes", 9
    suffixDict.Add "FontResolution", 14
    suffixDict.Add "FontStyle", 9
    suffixDict.Add "FontCSSStyle", 12
    suffixDict.Add "InlineIcons", 11
    
    '设置不同冻结列数的工作表字典（Set worksheet dictionaries with different number of frozen columns）
    ''冻结前六列（Freeze the first six columns）
    Dim sheetDict_fc06 As Object
    Set sheetDict_fc06 = CreateObject("Scripting.Dictionary")
    Dim suffixDict_fc06 As Object
    Set suffixDict_fc06 = CreateObject("Scripting.Dictionary")
    sheetDict_fc06.Add "指令（Cheat）", 9
    sheetDict_fc06.Add "装备（Items）", 9
    sheetDict_fc06.Add "海克斯大乱斗强化符文套装（Kiwi Augment Set）", 30
    sheetDict_fc06.Add "海克斯大乱斗乐队（Kiwi Bands）", 20
    sheetDict_fc06.Add "云顶之弈回合（TFT Round）", 17
    sheetDict_fc06.Add "云顶之弈角色定位（TFT Character Role）", 28
    sheetDict_fc06.Add "云顶之弈羁绊（TFT Traits）", 18
    suffixDict_fc06.Add "Cheat", 5
    suffixDict_fc06.Add "Items", 5
    suffixDict_fc06.Add "KiwiAugmentSet", 14
    suffixDict_fc06.Add "KiwiBands", 9
    suffixDict_fc06.Add "TFTRound", 8
    suffixDict_fc06.Add "TFTCharacterRole", 16
    suffixDict_fc06.Add "TFTTraits", 9
    ''冻结前七列（Freeze the first seven columns）
    Dim sheetDict_fc07 As Object
    Set sheetDict_fc07 = CreateObject("Scripting.Dictionary")
    Dim suffixDict_fc07 As Object
    Set suffixDict_fc07 = CreateObject("Scripting.Dictionary")
    sheetDict_fc07.Add "符文系（PerkStyles）", 15
    sheetDict_fc07.Add "装备修饰（Item Modifiers）", 20
    sheetDict_fc07.Add "符文（Perks）", 9
    sheetDict_fc07.Add "英雄（Champions）", 13
    sheetDict_fc07.Add "角色（Characters）", 14
    sheetDict_fc07.Add "海克斯大乱斗任务线（Kiwi Questlines）", 26
    sheetDict_fc07.Add "斗魂竞技场阶段（Cherry Phase）", 21
    sheetDict_fc07.Add "斗魂竞技场场景英雄（Cherry Cameos）", 24
    sheetDict_fc07.Add "无尽狂潮强化（Swarm Augments）", 22
    sheetDict_fc07.Add "云顶之弈商店（TFT Shop）", 16
    sheetDict_fc07.Add "云顶之弈传送门（TFT Portal）", 19
    suffixDict_fc07.Add "PerkStyles", 10
    suffixDict_fc07.Add "ItemModifiers", 13
    suffixDict_fc07.Add "Perks", 5
    suffixDict_fc07.Add "Champions", 9
    suffixDict_fc07.Add "Characters", 10
    suffixDict_fc07.Add "KiwiQuestlines", 14
    suffixDict_fc07.Add "CherryPhase", 11
    suffixDict_fc07.Add "CherryCameos", 12
    suffixDict_fc07.Add "SwarmAugments", 13
    suffixDict_fc07.Add "TFTShop", 7
    suffixDict_fc07.Add "TFTPortal", 9
    ''冻结前八列（Freeze the first eight columns）
    Dim sheetDict_fc08 As Object
    Set sheetDict_fc08 = CreateObject("Scripting.Dictionary")
    Dim suffixDict_fc08 As Object
    Set suffixDict_fc08 = CreateObject("Scripting.Dictionary")
    sheetDict_fc08.Add "召唤师技能（Summoner Spells）", 22
    sheetDict_fc08.Add "英雄技能（Champion Spells）", 21
    sheetDict_fc08.Add "角色技能（Character Spells）", 22
    sheetDict_fc08.Add "云顶之弈赛季（TFT Set）", 15
    sheetDict_fc08.Add "云顶之弈装备（TFT Items）", 17
    sheetDict_fc08.Add "斗魂竞技场强化符文（Cherry Augments）", 26
    sheetDict_fc08.Add "海克斯大乱斗强化符文（Kiwi Augments）", 25
    sheetDict_fc08.Add "海克斯大乱斗经典强化符文（KiwiJade Augments）", 31
    sheetDict_fc08.Add "斗魂竞技场锻造器（Cherry Anvils）", 23
    sheetDict_fc08.Add "海克斯大乱斗锻造器（Kiwi Anvils）", 22
    suffixDict_fc08.Add "SummonerSpells", 14
    suffixDict_fc08.Add "ChampionSpells", 14
    suffixDict_fc08.Add "CharacterSpells", 15
    suffixDict_fc08.Add "TFTSet", 6
    suffixDict_fc08.Add "TFTItems", 8
    suffixDict_fc08.Add "CherryAugments", 14
    suffixDict_fc08.Add "KiwiAugments", 12
    suffixDict_fc08.Add "KiwiJadeAugments", 16
    suffixDict_fc08.Add "CherryAnvils", 12
    suffixDict_fc08.Add "KiwiAnvils", 10
    ''冻结前九列（Freeze the first nine columns）
    Dim sheetDict_fc09 As Object
    Set sheetDict_fc09 = CreateObject("Scripting.Dictionary")
    Dim suffixDict_fc09 As Object
    Set suffixDict_fc09 = CreateObject("Scripting.Dictionary")
    sheetDict_fc09.Add "斗魂竞技场回合阶段（Cherry Round Phase）", 29
    suffixDict_fc09.Add "CherryRoundPhase", 16
    ''冻结前十三列（Freeze the first thirteen columns）
    Dim sheetDict_fc13 As Object
    Set sheetDict_fc13 = CreateObject("Scripting.Dictionary")
    Dim suffixDict_fc13 As Object
    Set suffixDict_fc13 = CreateObject("Scripting.Dictionary")
    sheetDict_fc13.Add "斗魂竞技场荣誉嘉宾（Cherry Guests）", 24
    suffixDict_fc13.Add "CherryGuests", 12
    ''冻结前十五列（Freeze the first fifteen columns）
    Dim sheetDict_fc15 As Object
    Set sheetDict_fc15 = CreateObject("Scripting.Dictionary")
    Dim suffixDict_fc15 As Object
    Set suffixDict_fc15 = CreateObject("Scripting.Dictionary")
    sheetDict_fc15.Add "海克斯大乱斗奖励分组（Kiwi Reward Group）", 29
    sheetDict_fc15.Add "经典模式奖励分组（Jade Reward Group）", 27
    suffixDict_fc15.Add "KiwiRewardGroup", 15
    suffixDict_fc15.Add "JadeRewardGroup", 15
    
    '冻结窗格和启用筛选（Freeze pane and enable filtering）
    Dim ws As Worksheet
    Dim lastCol As Long
    Dim wsNameSplit() As String
    Dim dType As String
    For Each ws In ThisWorkbook.Worksheets
        wsNameSplit = Split(ws.Name)
        dType = wsNameSplit(UBound(wsNameSplit))
        If sheetDict.Exists(ws.Name) Or suffixDict.Exists(dType) Then '限定冻结和筛选的工作表（Limit sheets that shouldn't be frozen any pane and selected）
            ws.Activate '选中该工作表（Select this sheet）
            If ws.AutoFilterMode Then ws.AutoFilterMode = False '取消已经存在的筛选（Remove any existing autofilter）
            ActiveWindow.FreezePanes = False '取消当前冻结窗格效果（Disable the current pane freezing）
            ActiveWindow.SplitColumn = 0 '取消任何可能的列拆分（Remove any existing column split）
            ActiveWindow.SplitRow = 0 '取消任何可能的行拆分（Remove any existing row split）
            If sheetDict_fc06.Exists(ws.Name) Or suffixDict_fc06.Exists(dType) Then
                ws.Range("G3").Select '冻结前两行和前六列（Freeze the first two rows and six columns）
            ElseIf sheetDict_fc07.Exists(ws.Name) Or suffixDict_fc07.Exists(dType) Then
                ws.Range("H3").Select '冻结前两行和前七列（Freeze the first two rows and seven columns）
            ElseIf sheetDict_fc08.Exists(ws.Name) Or suffixDict_fc08.Exists(dType) Then
                ws.Range("I3").Select '冻结前两行和前八列（Freeze the first two rows and eight columns）
            ElseIf sheetDict_fc09.Exists(ws.Name) Or suffixDict_fc09.Exists(dType) Then
                ws.Range("J3").Select '冻结前两行和前九列（Freeze the first two rows and nine columns）
            ElseIf sheetDict_fc13.Exists(ws.Name) Or suffixDict_fc13.Exists(dType) Then
                ws.Range("N3").Select '冻结前两行和前十三列（Freeze the first two rows and thirteen columns）
            ElseIf sheetDict_fc15.Exists(ws.Name) Or suffixDict_fc15.Exists(dType) Then
                ws.Range("P3").Select '冻结前两行和前十五列（Freeze the first two rows and fifteen columns）
            Else
                ws.Rows("3:3").Select '其它情况下统一冻结所有表头（In other cases, freeze all headers）
            End If
            ActiveWindow.FreezePanes = True '冻结窗格（Freeze the panes）
            ws.Range("A2").Select '移动光标到A2（Select A2 cell）
            lastCol = ws.Cells(2, ws.Columns.Count).End(xlToLeft).Column '确定第二行最后一个有内容的单  元格的列数（Determine the last column that has content in Line Two）
            ws.Range(ws.Cells(2, 1), ws.Cells(2, lastCol)).Select '选中从A2到最后一个有内容的单元格（Select the range from A2 to the last cell that has content in the same row）
            Selection.AutoFilter '对选中范围应用筛选（Apply autofilter to the selected range）
            ws.Range("A1").Select '光标初始化——选中A1单元格（Cursor initialization - Select A1 cell）
        End If
    Next ws
    Worksheets(1).Activate '选中第一个工作表（Select the first sheet）
    Worksheets(1).Range("A1").Select '移动光标到A1（Select A1 cell）
End Sub

Sub FreezeAndFilterItemDataSheets()
    Dim ws As Worksheet
    Dim lastCol As Long
    For Each ws In ThisWorkbook.Worksheets
        If ws.Name = "pbe" Or ws.Name = "latest" Or Right$(ws.Name, 9) = "(cdragon)" Or Right$(ws.Name, 9) = "(ddragon)" Then
            ws.Activate '选中该工作表（Select this sheet）
            If ws.AutoFilterMode Then ws.AutoFilterMode = False '取消已经存在的筛选（Remove any existing autofilter）
            ActiveWindow.FreezePanes = False '取消当前冻结窗格效果（Disable the current pane freezing）
            ActiveWindow.SplitColumn = 0 '取消任何可能的列拆分（Remove any existing column split）
            ActiveWindow.SplitRow = 0 '取消任何可能的行拆分（Remove any existing row split）
            ws.Range("E3").Select '冻结前两行和前四列（Freeze the first two rows and four columns）
            ActiveWindow.FreezePanes = True '冻结窗格（Freeze the panes）
            ws.Range("A2").Select '移动光标到A2（Select A2 cell）
            lastCol = ws.Cells(2, ws.Columns.Count).End(xlToLeft).Column '确定第二行最后一个有内容的单元格的列数（Determine the last column that has content in Line Two）
            ws.Range(ws.Cells(2, 1), ws.Cells(2, lastCol)).Select '选中从A2到最后一个有内容的单元格（Select the range from A2 to the last cell that has content in the same row）
            Selection.AutoFilter '对选中范围应用筛选（Apply autofilter to the selected range）
            ws.Range("A1").Select '光标初始化——选中A1单元格（Cursor initialization - Select A1 cell）
        End If
    Next ws
    Worksheets(1).Activate '选中第一个工作表（Select the first sheet）
    Worksheets(1).Range("A1").Select '移动光标到A1（Select A1 cell）
End Sub

Sub Pandas2_DefaultHeaderStyle()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim lastCol As Long
    Dim regionA As Range
    Dim regionB As Range
    Application.ScreenUpdating = False '关闭屏幕更新以提高执行速度（Disable screen update to improve the speed）
    For Each ws In ThisWorkbook.Worksheets
        With ws
            lastRow = .Cells(.Rows.Count, "A").End(xlUp).Row '获取数据区域的最后一行（Get the last row of the data region）
            lastCol = .Cells(1, .Columns.Count).End(xlToLeft).Column '获取数据区域的最后一列（Get the last column of the data region）
            If lastRow >= 2 Then '确保至少有一行数据（Make sure there's at least one row of data）
                Set regionA = .Range("A2:A" & lastRow) '定义区域A为A2到A列的最后一行（Define region A as the last column from A2 to the bottom）
                With regionA
                    .Font.Bold = True '加粗（Bold）
                    .HorizontalAlignment = xlCenter '水平居中（Horizontally center-aligned）
                    .VerticalAlignment = xlCenter '垂直居中(Vertically center-aligned）
                    .BorderAround xlContinuous '外边框（Outer border）
                    .Borders(xlInsideHorizontal).LineStyle = xlContinuous '内部水平边框（Inner horizontal borders）
                    .Borders(xlInsideVertical).LineStyle = xlContinuous '内部垂直边框（Inner vertical borders）
                End With
            End If
            If lastCol >= 2 Then '确保至少有一行数据（Make sure there's at least one column of data）
                Set regionB = .Range(.Cells(1, 2), .Cells(1, lastCol))
                With regionB
                    .Font.Bold = True
                    .HorizontalAlignment = xlCenter
                    .VerticalAlignment = xlCenter
                    .BorderAround xlContinuous
                    .Borders(xlInsideHorizontal).LineStyle = xlContinuous
                    .Borders(xlInsideVertical).LineStyle = xlContinuous
                End With
            End If
        End With
    Next ws
    Application.ScreenUpdating = True '恢复屏幕更新（Recover screen update）
End Sub
