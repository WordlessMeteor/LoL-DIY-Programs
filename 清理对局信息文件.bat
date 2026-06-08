@echo off
echo 对局信息文件将被永久删除。该操作不可逆！是否继续？
echo Match information files will be deleted permanently. This operation is irreversible! Do you really want to continue?
setlocal enabledelayedexpansion & @REM 延迟扩展（Delayed expansion）
choice
if %ERRORLEVEL% == 1 (
    dir /b /s /ad "召唤师信息（Summoner Information）\*1. MatchIDs" > dirs.txt
    for /f "delims=" %%i in (dirs.txt) do (
        rd /s /q "%%i"
    )
    del dirs.txt
)
