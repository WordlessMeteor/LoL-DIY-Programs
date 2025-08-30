@echo off
setlocal enabledelayedexpansion
set batchFilePath=%~dp0
set folderPath="%batchFilePath%\召唤师信息（Summoner Information）"
echo 请选择数据文档转换方向: 
echo Please select a direction for data file format conversion: 
echo 1	txt → json
echo 2	json → txt
set /p flag=
if %flag% == 1 (
    for /r %folderPath% %%F in (*.txt) do (
        set filePath=%%~dpF
        set fileName=%%~nF
        move "%%F" "!filePath!!fileName!.json"
    )
    echo 操作完成！
    echo Operation finished!
) else if %flag% == 2 (
    for /r %folderPath% %%F in (*.json) do (
        set filePath=%%~dpF
        set fileName=%%~nF
        move "%%F" "!filePath!!fileName!.txt"
    )
    echo Operation finished!
) else (
    echo 输入无效！
    echo Invalid output!
)
pause