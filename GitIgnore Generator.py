import os

LF = [] #存储大小超过100 MB的文件位置（Stores paths of large files over 100 MiB）
LNF = [] #存储文件名超过171个字符长度的文件位置（Stores paths of files with file name longer than 171 characters）
for root, dirs, files in os.walk("离线数据（Offline Data）"):
    for file in files:
        size = os.path.getsize(os.path.join(root, file))
        if size > 104857600: #100 * 1024 * 1024
            LF.append(os.path.join(root, file).replace("\\", "/"))
        if len(file) > 171:
            LNF.append(os.path.join(root, file).replace("\\", "/"))

with open(".gitignore", "w", encoding = "utf-8") as fp:
    print("#Vscode个人配置文件（Stores paths of Vscode setting files）\n.vscode/*\n#调试文件（Debug files）\n调试脚本.py\n#日志文件（Log files）\n离线数据（Offline Data）/Update Logs/*\n#由程序生成的数据文件（Generated data files）\n召唤师信息（Summoner Information）/*\n顶尖排位玩家（Ranked Apex）/*")
    fp.write("#Vscode个人配置文件（Stores paths of Vscode setting files）\n.vscode/*\n#调试文件（Debug files）\n调试脚本.py\n#日志文件（Log files）\n离线数据（Offline Data）/Update Logs/*\n#由程序生成的数据文件（Generated data files）\n召唤师信息（Summoner Information）/*\n顶尖排位玩家（Ranked Apex）/*\n")
    if LF:
        print("#文件大小超过100 MB（File size exceeds 100 MiB）")
        fp.write("#文件大小超过100 MB（File size exceeds 100 MiB）\n")
        for file in LF:
            print(file)
            fp.write(file + "\n")
    if LNF:
        print("#文件名过长（File name exceeds 171 characters）")
        fp.write("#文件名过长（File name exceeds 171 characters）\n")
        for file in LNF:
            print(file)
            fp.write(file + "\n")