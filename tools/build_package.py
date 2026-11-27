"""把工作目录打成可分发的 zip。

包含：面板 + 网关 + 便携 Python + 项目内依赖 + 服务端源码 + ffmpeg
不包含：data（用户数据/测试密钥）、dev、venv 配置/启动器、日志、缓存

超过 50 MB 的大文件与网关整目录在包内改成 .zip（见 COMPRESS_FILES / COMPRESS_DIRS），
首次双击「启动面板.bat」时由 app/panel/unpack_runtime.py 自动还原并删除压缩包。

用法：python tools/build_package.py [--out dist]
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOP_FILES = [
    "version.json",
    "README.md",
    "使用说明.txt",
    "卸载说明.md",
    "THIRD-PARTY.md",
    "🚀启动面板.bat",
    "卸载.bat",
    "密钥配置.png",
    "设备OTA地址配置.png",
]

EXCLUDE_DIRS = {
    "__pycache__",
    ".overlay-backup",
    # pyenv 现在随包离线分发
    "dev",
    "dist",
    "shots",
}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db", "audit_package.py"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".pdb", ".log", ".part"}

# 超过 Gitee 免费版单文件上限（50 MB）的运行组件；包里改成同名 .zip，启动时还原
COMPRESS_FILES = (
    "runtime/bin/ffmpeg.exe",
    "runtime/node/node.exe",
)
# 整目录打成一个 zip：网关目录自带 .gitignore 会吞掉 node_modules，压缩后可绕过
COMPRESS_DIRS = (
    "runtime/xiaozhi-mqtt-gateway",
)
# 这些 .zip 由 build_inner_archives() 单独注入，不能让 collect() 再收一遍（否则重复条目 + 体积翻倍）
INNER_ARCHIVE_PATHS = {f"{rel}.zip" for rel in (*COMPRESS_FILES, *COMPRESS_DIRS)}


def should_skip(rel: Path) -> bool:
    s = rel.as_posix()
    if s in COMPRESS_FILES or s in INNER_ARCHIVE_PATHS:
        return True
    parts = set(rel.parts)
    if rel.parts[:2] == ("runtime", "pyenv") and (
        rel.name == "pyvenv.cfg" or "Scripts" in rel.parts[2:]
    ):
        return True
    if parts & EXCLUDE_DIRS:
        return True
    if rel.name in EXCLUDE_NAMES or rel.suffix in EXCLUDE_SUFFIX:
        return True
    # 用户数据 / 运行时产物
    if s.startswith("data/"):
        return True
    if s.startswith("runtime/xiaozhi-server/data/"):
        return True
    if s.startswith("runtime/xiaozhi-mqtt-gateway/.env"):
        return True
    if s.startswith("app/gateway/"):
        return True
    if s.startswith("runtime/xiaozhi-server/tmp/"):
        return True
    if s.startswith("runtime/xiaozhi-server/models/SenseVoiceSmall"):
        return True
    if s.startswith("vendor/mqttgw/.env"):
        return True  # 运行时生成
    if "/node_modules/.cache/" in s:
        return True
    return False


def collect() -> list[Path]:
    files: list[Path] = []
    for name in TOP_FILES:
        path = ROOT / name
        if path.exists():
            files.append(path)
    for base in (
        "app",
        "tools",
        "licenses",
        "runtime/bin",
        "runtime/python",
        "runtime/pyenv",
        "runtime/node",
        "runtime/xiaozhi-server",
    ):
        root = ROOT / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(ROOT)
                if not should_skip(rel):
                    files.append(path)
    return files


def _zip_bytes(entries: list[tuple[str, Path]]) -> bytes:
    """把 (包内名, 源文件) 列表打成一个 deflate zip，返回字节。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for arc, path in entries:
            info = zipfile.ZipInfo.from_file(path, arc)
            info.external_attr = 0o666 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    return buf.getvalue()


def build_inner_archives() -> list[tuple[str, bytes]]:
    """生成包内的压缩组件：(包内路径, zip 字节)。

    大文件 → `<原路径>.zip`；整目录 → `<目录名>.zip`，条目统一带 `<目录名>/` 前缀，
    启动时解压到其父目录即可还原。
    """
    archives: list[tuple[str, bytes]] = []
    for rel in COMPRESS_FILES:
        src = ROOT / rel
        if src.is_file():
            archives.append((f"{rel}.zip", _zip_bytes([(src.name, src)])))
    for rel in COMPRESS_DIRS:
        src = ROOT / rel
        if not src.is_dir():
            continue
        entries: list[tuple[str, Path]] = []
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            if should_skip(path.relative_to(ROOT)):
                continue
            entries.append((f"{src.name}/{path.relative_to(src).as_posix()}", path))
        archives.append((f"{rel}.zip", _zip_bytes(entries)))
    return archives


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()

    version = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"xiaozhi-oneclick-{version['version']}.zip"

    files = collect()
    inner = build_inner_archives()
    total = sum(f.stat().st_size for f in files) + sum(len(data) for _, data in inner)
    print(f"files: {len(files)}  inner zips: {len(inner)}  raw: {total / 1024 / 1024:.1f} MB")
    for arc, _ in inner:
        print(f"  + {arc}")
    print(f"-> {zip_path}")

    started = time.time()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for index, path in enumerate(files, 1):
            rel = path.relative_to(ROOT).as_posix()
            arc = f"xiaozhi-oneclick/{rel}"
            info = zipfile.ZipInfo.from_file(path, arc)
            info.external_attr = 0o666 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(path, "rb") as fh:
                zf.writestr(info, fh.read())
                if index % 500 == 0:
                    print(f"  {index}/{len(files)} …", flush=True)
        for arc, data in inner:
            ainfo = zipfile.ZipInfo(f"xiaozhi-oneclick/{arc}", date_time=time.localtime()[:6])
            ainfo.external_attr = 0o666 << 16
            ainfo.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(ainfo, data)

    size = zip_path.stat().st_size / 1024 / 1024
    print(f"done in {time.time() - started:.0f}s  zip: {size:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
