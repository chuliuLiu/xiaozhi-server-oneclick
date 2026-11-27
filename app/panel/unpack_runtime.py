"""bat 用：首次启动时把包内压缩的运行组件还原出来，成功后删除压缩包。

为什么要压缩：Gitee 免费版单文件上限 50 MB，且网关目录自带 .gitignore
会吞掉 node_modules；打成 zip 后既过得了体积限制，也不受忽略规则影响。

由 启动面板.bat 在启动面板前调用；没有待解压的压缩包时什么都不做（幂等）。
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
RUNTIME = PROJECT / "runtime"

# (压缩包, 解压目标目录)；条目名已带前缀，解压到目标目录即可还原原结构
TARGETS = (
    (RUNTIME / "xiaozhi-mqtt-gateway.zip", RUNTIME),
    (RUNTIME / "bin" / "ffmpeg.exe.zip", RUNTIME / "bin"),
    (RUNTIME / "node" / "node.exe.zip", RUNTIME / "node"),
)


def main() -> int:
    failed: list[str] = []
    for archive, dest in TARGETS:
        if not archive.exists():
            continue
        try:
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(dest)
            archive.unlink()
            print(f"[ok] 已还原 {archive.name}")
        except Exception as exc:  # noqa: BLE001
            print(f"[x] 还原 {archive.name} 失败：{exc}")
            failed.append(archive.name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
