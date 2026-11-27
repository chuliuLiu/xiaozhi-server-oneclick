"""bat 用：路径不合格才输出当前路径（bat 用 for /f 捕获）。

不合格 = 含非 ASCII 字符，或含空格。中文/空格路径会让语音服务的子进程出奇怪问题。
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    path = os.path.abspath(os.getcwd())
    if any(ord(ch) > 127 for ch in path) or " " in path:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
