# LoL-DIY-Programs

[中文用户？点击此处查看中文介绍。](README.zh_CN.md)

----
**This program set only supports study use or personal entertainment. Any commercial use is forbidden!**

----
> Truth is: Anything can be converted into a 2D table.

This program set mainly achieves **LoL Summoner information export** and **League Client behavior simulation** based on <ins>LCU API and SGP API</ins>.
## Environment setup and basic notes
1. The whole program set is made of Python programs. Users are highly suggested to download the latest version of Python from [Python official website](https://www.python.org/) (It's OK if you don't install the latest version, but please make sure it's not too old) and then install necessary libraries with pip.
    - Refer to Section 3, Subsection 2 of [ARAM Probability Test Program Brochure](https://zhuanlan.zhihu.com/p/2009344399239316285) for a more vivid tutorial.
    - For this first time of Python installation, please check <ins>Add Python to PATH</ins> option. If the working directories of Python aren't present in the environment variable Path, the following steps can be adopted to add Python to Path.
        1. Type in `path` in Windows search bar and click **Edit system environment variables**. **System Properties** window will pop up.
        2. Click **Environment Variables (N)** button and the **Environment Variable** window will occur.
        3. In **User Variables**, Find the variable `Path` and double-click it to enter the **Edit environment variable** dialog box.
        4. Add three paths by clicking the **New(N)** button. These paths are working directories of Python. If some similar paths already exist, there's no need to add them.\
            `C:\Users\[Username]\AppData\Local\Programs\Python\Launcher\`\
            `C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\`\
            `C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\Scripts`\
            For example, my Windows username is "<ins>19250</ins>", and my Python version is <ins>3.14.3</ins>. Then the updated PATH should include \
            `C:\Users\19250\AppData\Local\Programs\Python\Launcher\`\
            `C:\Users\19250\AppData\Local\Programs\Python\Python314\`\
            `C:\Users\19250\AppData\Local\Programs\Python\Python314\Scripts\`
        5. To be safe, you can also add these three paths to the `Path` variable in the **System variables** section.
        6. Restart <ins>Command Prompt</ins> or <ins>Terminal</ins>. In that case, Python tools, e.g. pip, can be used as normal.
    - After installation and environment variable configuration of Python, use `pip install [LibraryName]` command to install required libraries for this program set. For Chinese mainland users, using a proxy or setting a mirror should accelerate the downloading stage of Python libraries. Required libraries for this program set are:
        - lcu_driver
            - I've forked [lcu_driver library](https://github.com/WordlessMeteor/lcu-driver/tree/master/lcu_driver), so that the user can still pxperience library files in the forked repository if the corresponding pull request hasn't been accepted to merge into the official version, or has been rejected to merge, by the original author.
            - I'm only reponsible for modifying the library files in the forked repository **according to the demands of this program set**, and not obligated to merge others' changes to the library files into mine. However, any user that commented and suggested on the library update **based on the program set update** is welcome 👏
            - If you want to use my `lcu_driver` library, please follow these steps:
                1. Open [my lcu-driver repo homepage](https://github.com/WordlessMeteor/lcu-driver).
                2. Click <ins>the green "Code" button</ins>. Then click <ins>DownloadZIP</ins> to download the source code of this repository.
                3. Extract the zip file to the current folder.
                    - Don't worry about the chaos after the extraction! The files should have been put in a subfolder.
                4. Open the directory where Python stores libraries.
                    - Basically, the directory is at `C:\Users\[Username]\AppData\Local\Programs\Python\Python[Version]\Lib\site-packages`.
                        - For example, my Windows username is "<ins>19250</ins>", and my Python version is <ins>3.14.3</ins>. Then the library directory should be \
                        `C:\Users\19250\AppData\Local\Programs\Python\Python314\Lib\site-packages`
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
        - keyboard
2. To improve the response speed, please open any program in this program set by Command Prompt or Terminal, instead of Python IDLE.
    - To prevent the window from flashing quickly, it's suggested that users first open Command Prompt (or Terminal), switch to the directory of the program set using `cd` command and then open some program by `python [Filename]` or `python -W ignore [Filename]`. In this way, it's easy check the returned information.
3. All programs must run after the user logs into the League Client. 
4. All running .py files can be aborted by pressing Ctrl+C while running. (Press for any times you want, until the program exits.)

## Acknowledgement
<table>
    <thead>
        <tr>
            <th style="text-align:center;">Name & Page</th>
            <th style="text-align:center;">Reason</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="text-align:center;"><a href="https://github.com/XHXIAIEIN">XHXIAIEIN</a></td>
            <td>
                <ul>
                    <li><a href="https://github.com/XHXIAIEIN/LeagueCustomLobby">Custom lobby related routine</a></li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://space.bilibili.com/14671179">Mario</a></td>
            <td>
                <ul>
                    <li>From whom I learned about SGP API for the first time</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://space.bilibili.com/230327779">Awesome丶ABC</a></td>
            <td>
                <ul>
                    <li>Obfuscated puuid resolve (I haven't implemented it)</li>
                    <li>Spectate service support</li>
                    <li>Match history count expansion and data slice merge</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://github.com/Morilli">Morilli</a></td>
            <td>
                <ul>
                    <li>Web request session reuse</li>
                    <li>Multiprocessing (I haven't implemented it)</li>
                    <li>Game Data Extraction</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;">Le poussin</td>
            <td>
                <ul>
                    <li>In-game tooltip transform</li>
                    <li>Hash calculation</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;">Moga</td>
            <td>
                <ul>
                    <li>Game Data Extraction (<a href="https://github.com/CommunityDragon/CDTB">cdtb</a> HOWTO)</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td style="text-align:center;"><a href="https://space.bilibili.com/35535774">三元君_</a></td>
            <td>
                <ul>
                    <li>Suggestions on README and commit pattern</li>
                </ul>
            </td>
        </tr>
    </tbody>
</table>
