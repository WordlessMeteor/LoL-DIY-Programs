Attribute VB_Name = "冻结窗格"
Sub FreezeAndFilterGameDataSheets()
    Dim ws As Worksheet
    Dim lastCol As Long
    For Each ws In ThisWorkbook.Worksheets
        If ws.Name = "指令集（CheatSet）" Or Right$(ws.Name, 8) = "CheatSet" Or ws.Name = "指令（Cheat）" Or Right$(ws.Name, 11) = "Cheat" _
                Or ws.Name = "符文系（PerkStyles）" Or Right$(ws.Name, 10) = "PerkStyles" Or ws.Name = "符文（Perks）" Or Right$(ws.Name, 5) = "Perks" _
                Or ws.Name = "英雄（Champions）" Or Right$(ws.Name, 9) = "Champions" _
                Or ws.Name = "英雄技能（Champion Spells）" Or Right$(ws.Name, 14) = "ChampionSpells" Or ws.Name = "角色（Characters）" Or Right$(ws.Name, 10) = "Characters" _
                Or ws.Name = "角色技能（Character Spells）" Or Right$(ws.Name, 16) = "CharacterSpells" _
                Or ws.Name = "装备（Items）" Or Right$(ws.Name, 5) = "Items" Or ws.Name = "装备分组（Item Groups）" Or Right$(ws.Name, 10) = "ItemGroups" Or ws.Name = "装备修饰（Item Modifiers）" Or Right$(ws.Name, 13) = "ItemModifiers" _
                Or ws.Name = "斗魂竞技场强化符文（Cherry Augments）" Or Right$(ws.Name, 14) = "CherryAugments" Or ws.Name = "无尽狂潮强化（Swarm Augments）" Or Right$(ws.Name, 13) = "SwarmAugments" _
                Or ws.Name = "海克斯大乱斗强化符文（Kiwi Augments）" Or Right$(ws.Name, 12) = "KiwiAugments" Or ws.Name = "海克斯大乱斗强化符文套装（Kiwi Augment Set）" Or Right$(ws.Name, 14) = "KiwiAugmentSet" _
                Or ws.Name = "斗魂竞技场锻造器（Cherry Anvils）" Or Right$(ws.Name, 12) = "CherryAnvils" Or ws.Name = "海克斯大乱斗锻造器（Kiwi Anvils）" Or Right$(ws.Name, 10) = "KiwiAnvils" _
                Or ws.Name = "云顶之弈赛季（TFT Set）" Or Right$(ws.Name, 6) = "TFTSet" _
                Or ws.Name = "云顶之弈商店（TFT Shop）" Or Right$(ws.Name, 7) = "TFTShop" _
                Or ws.Name = "云顶之弈商店内容（TFT Shop Content）" Or Right$(ws.Name, 14) = "TFTShopContent" _
                Or ws.Name = "云顶之弈掉率表（TFT Drop Rate）" Or Right$(ws.Name, 11) = "TFTDropRate" _
                Or ws.Name = "云顶之弈回合阶段（TFT Stage Round）" Or Right$(ws.Name, 13) = "TFTStageRound" Or ws.Name = "云顶之弈回合（TFT Round）" Or Right$(ws.Name, 8) = "TFTRound" _
                Or ws.Name = "云顶之弈传送门（TFT Portal）" Or Right$(ws.Name, 9) = "TFTPortal" Or (ws.Name = "云顶之弈开场奇遇（TFT Encounter Distribution）" Or ws.Name = "云顶之弈开场奇遇（TFT Encounter Distribu") Or (Right$(ws.Name, 24) = "TFTEncounterDistribution" Or Right$(ws.Name, 17) = "TFTEncounterDistr") _
                Or ws.Name = "云顶之弈奇遇（TFT Encounter）" Or Right$(ws.Name, 12) = "TFTEncounter" Or ws.Name = "云顶之弈单位属性（TFT Unit Property）" Or Right$(ws.Name, 15) = "TFTUnitProperty" _
                Or ws.Name = "云顶之弈角色定位（TFT Character Role）" Or Right$(ws.Name, 16) = "TFTCharacterRole" Or ws.Name = "云顶之弈装备列表（TFT Item List）" Or Right$(ws.Name, 11) = "TFTItemList" _
                Or ws.Name = "云顶之弈装备（TFT Item）" Or Right$(ws.Name, 7) = "TFTItem" Or ws.Name = "云顶之弈羁绊列表（TFT Trait List）" Or Right$(ws.Name, 12) = "TFTTraitList" _
                Or ws.Name = "云顶之弈羁绊（TFT Trait）" Or Right$(ws.Name, 8) = "TFTTrait" Or ws.Name = "云顶之弈电脑玩家英雄（TFT PVE NPC）" Or Right$(ws.Name, 9) = "TFTPVENPC" _
                Or ws.Name = "云顶之弈脚本（TFT Script）" Or Right$(ws.Name, 9) = "TFTScript" Or ws.Name = "云顶之弈通告（TFT Announcement）" Or Right$(ws.Name, 15) = "TFTAnnouncement" Then '限定冻结和筛选的工作表（Limit sheets that shouldn't be frozen any pane and selected）
            ws.Activate '选中该工作表（Select this sheet）
            If ws.AutoFilterMode Then ws.AutoFilterMode = False '取消已经存在的筛选（Remove any existing autofilter）
            ActiveWindow.FreezePanes = False '取消当前冻结窗格效果（Disable the current pane freezing）
            ActiveWindow.SplitColumn = 0 '取消任何可能的列拆分（Remove any existing column split）
            ActiveWindow.SplitRow = 0 '取消任何可能的行拆分（Remove any existing row split）
            If ws.Name = "符文系（PerkStyles）" Or Right$(ws.Name, 10) = "PerkStyles" _
                    Or ws.Name = "装备修饰（Item Modifiers）" or Right$(ws.Name, 13) = "ItemModifiers" _
                    Or ws.Name = "符文（Perks）" Or Right$(ws.Name, 5) = "Perks" _
                    Or ws.Name = "英雄（Champions）" Or Right$(ws.Name, 9) = "Champions" _
                    Or ws.Name = "角色（Characters）" Or Right$(ws.Name, 10) = "Characters" _
                    Or ws.Name = "无尽狂潮强化（Swarm Augments）" Or Right$(ws.Name, 13) = "SwarmAugments" _
                    Or ws.Name = "云顶之弈商店（TFT Shop）" Or Right$(ws.Name, 7) = "TFTShop" _
                    Or ws.Name = "云顶之弈传送门（TFT Portal）" Or Right$(ws.Name, 9) = "TFTPortal" Then
                ws.Range("H3").Select '冻结前两行和前七列（Freeze the first two rows and seven columns）
            ElseIf ws.Name = "英雄技能（Champion Spells）" Or Right$(ws.Name, 14) = "ChampionSpells" _
                    Or ws.Name = "角色技能（Character Spells）" Or Right$(ws.Name, 15) = "CharacterSpells" Then
                ws.Range("J3").Select '冻结前两行和前九列（Freeze the first two rows and nine columns）
            ElseIf ws.Name = "指令（Cheat）" Or Right$(ws.Name, 5) = "Cheat" _
                    Or ws.Name = "装备（Items）" Or Right$(ws.Name, 5) = "Items" _
                    Or ws.Name = "海克斯大乱斗强化符文套装（Kiwi Augment Set）" Or Right$(ws.Name, 14) = "KiwiAugmentSet" _
                    Or ws.Name = "云顶之弈回合（TFT Round）" Or Right$(ws.Name, 8) = "TFTRound" _
                    Or ws.Name = "云顶之弈角色定位（TFT Character Role）" Or Right$(ws.Name, 16) = "TFTCharacterRole" _
                    Or ws.Name = "云顶之弈羁绊（TFT Trait）" Or Right$(ws.Name, 8) = "TFTTrait" Then
                ws.Range("G3").Select '冻结前两行和前六列（Freeze the first two rows and six columns）
            ElseIf ws.Name = "云顶之弈赛季（TFT Set）" Or Right$(ws.Name, 6) = "TFTSet" _
                    Or ws.Name = "云顶之弈装备（TFT Item）" Or Right$(ws.Name, 7) = "TFTItem" _
                    Or ws.Name = "斗魂竞技场强化符文（Cherry Augments）" Or Right$(ws.Name, 7) = "CherryAugments" _
                    Or ws.Name = "海克斯大乱斗强化符文（Kiwi Augments）" Or Right$(ws.Name, 7) = "KiwiAugments" _
                    Or ws.Name = "斗魂竞技场锻造器（Cherry Anvils）" Or Right$(ws.Name, 7) = "CherryAnvils" _
                    Or ws.Name = "海克斯大乱斗锻造器（Kiwi Anvils）" Or Right$(ws.Name, 7) = "KiwiAnvils" Then
                ws.Range("I3").Select '冻结前两行和前八列（Freeze the first two rows and eight columns）
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
