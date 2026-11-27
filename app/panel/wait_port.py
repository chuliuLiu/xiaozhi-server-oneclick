"""bat 用：等面板的端口起来，最多等 N 秒。成功 exit 0。"""

from __future__ import annotations

import socket
import sys
import time


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return 0
        except OSError:
            time.sleep(0.2)
    return 1


if __name__ == "__main__":
    sys.exit(main())
