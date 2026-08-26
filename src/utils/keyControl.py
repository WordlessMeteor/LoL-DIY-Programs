import msvcrt

def isKeyPressed(keyCode1: bytes, keyCode2: bytes = b"") -> bool:
    r'''
    检查指定的按键是否在用户**激活当前程序的运行窗口/标签页**时被按下。<br>Check if the specified key is pressed when the user **activates the tab / window of the current program**.
    
    对于简单按键，用户只需要传入第一个字节序列。对于特殊按键，用户需要传入两个不同的字节序列。这是因为`msvcrt.getch`函数一次只能返回一个字节的数据。简单按键的字节数较小，用一个字节便可存下；特殊按键的字节序列较大，需要用两个字节来表示。<br>For a simple key, the user only needs to pass in the first byte sequence. For a special key, the user needs to pass in two different byte sequences. This is because `msvcrt.getch` function can only return one byte of data at a time. The byte sequence of simple keys is smaller and can be stored in one byte; the byte sequence of special keys is larger and requires two bytes.
    
    简单按键的字节序列就是直接以字节形式表示的按键本身，例如：<br>The byte sequence of a simple key is the key itself in byte form, for example:
    - A: (b"a")
    - Space: (b" ")
    
    一些特殊按键的字节序列如下：<br>Some special key byte sequences are as follows:
    - Backspace: (b"\x08")
    - Enter: (b"\r")
    - Esc: (b"\x1b")
    - F1: (b"\x00", b";")
    - F2: (b"\x00", b"<")
    - F3: (b"\x00", b"=")
    - F4: (b"\x00", b">")
    - F5: (b"\x00", b"?")
    - F6: (b"\x00", b"@")
    - F7: (b"\x00", b"A")
    - F8: (b"\x00", b"B")
    - F9: (b"\x00", b"C")
    - F10: (b"\x00", b"D")
    - F11: (b"\x00", b"\x85")
    - F12: (b"\x00", b"\x86")
    - Insert: (b"\xe0", b"R")
    - Delete: (b"\xe0", b"S")
    - Home: (b"\xe0", b"H")
    - End: (b"\xe0", b"P")
    - Page Up: (b"\xe0", b"I")
    - Page Down: (b"\xe0", b"Q")
        
    :param keyCode1: 一个按键对应的第一个字节序列。<br>The first byte sequence of a key.
    :type keyCode1: bytes
    :param keyCode2: 一个按键对应的第二个字节序列。默认是空字节。<br>The second byte sequence of a key. An empty byte by default.
    
        对于简单按键，这个参数不发挥作用。<br>For a simple key, this parameter doesn't make any difference.
    :type keyCode2: bytes
    :return: 指定的按键是否被按下。<br>Whether the specified key is pressed.
    :rtype: bool
    '''
    return bool(msvcrt.kbhit()) and msvcrt.getch() == keyCode1 and (keyCode1 != b"\xe0" and keyCode1 != b"\000" or msvcrt.getch() == keyCode2)
