import os, subprocess, time

#获取待压缩的文件夹列表（Get the list of folders to compress）
matchInfo_folders_to_compress: list[str] = []
matchId_folder_name: str = "1. MatchIDs"
for root, dirs, files in os.walk("召唤师信息（Summoner Information）"):
    if len(dirs) == 0: #下面只讨论文件夹结构的最深层，避免重复压缩（Only the leaf paths are discussed in the following, in case one file would be compressed repeatedly）
        if os.path.basename(root) == matchId_folder_name:
            matchInfo_folders_to_compress.append(root)
currentTime: str = time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())
print("[%s]" %(currentTime), end = "")
print("正在压缩对局信息文件……\nCompressing match information files ...")
archive_name: str = f"对局信息存档 {currentTime}.7z"
args: list[str] = ["bandizip", "c", "-storeroot:yes", "-l:9", archive_name, *matchInfo_folders_to_compress]
result: subprocess.CompletedProcess[bytes] = subprocess.run(args)
print("[%s]" %(time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())), end = "")
if result.returncode == 0:
    print(f'对局信息文件已压缩到同目录下的“{archive_name}”。按回车键退出程序。\nMatch information files have been compressed into "{archive_name}" under the same directory. Press Enter to exit.')
else:
    print("压缩失败。按回车键退出程序。\nCompression failed. Press Enter to exit.")
input()
