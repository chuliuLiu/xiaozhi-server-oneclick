"""项目路径的唯一来源；路径均从当前项目根目录动态推导。"""

from __future__ import annotations

from pathlib import Path

# app/common/paths.py -> app/common -> app -> 项目根
PROJECT = Path(__file__).resolve().parents[2]
APP = PROJECT / "app"
PANEL = APP / "panel"
WEB = PANEL / "web"
GATEWAY = APP / "gateway"
DATA = PROJECT / "data"
LOGS = DATA / "logs"
RUN = DATA / "run"
BACKUPS = DATA / "backups"
RUNTIME = PROJECT / "runtime"
PY = RUNTIME / "python"
PYENV = RUNTIME / "pyenv"
SITE_PACKAGES = PYENV / "Lib" / "site-packages"
PYWIN32_DLLS = SITE_PACKAGES / "pywin32_system32"
BIN = RUNTIME / "bin"
SERVER = RUNTIME / "xiaozhi-server"
TOOLS = PROJECT / "tools"
VERSION_FILE = PROJECT / "version.json"
SETTINGS_FILE = DATA / "settings.json"

PORTABLE_PYTHON = PY / "python.exe"
PORTABLE_PYTHONW = PY / "pythonw.exe"
FFMPEG = BIN / "ffmpeg.exe"
OPUS_DLL = BIN / "opus.dll"


def ensure_dirs() -> None:
    for p in (DATA, LOGS, RUN, BACKUPS):
        p.mkdir(parents=True, exist_ok=True)


def python_for_children() -> Path | None:
    """子进程统一使用随项目携带的 Python；依赖目录由 child_env 注入。"""
    return PORTABLE_PYTHON if PORTABLE_PYTHON.exists() else None


def child_env() -> dict[str, str]:
    """为子进程配置项目内依赖和 DLL 搜索路径。"""
    import os

    env = dict(os.environ)
    python_paths = (
        SITE_PACKAGES,
        SITE_PACKAGES / "win32",
        SITE_PACKAGES / "win32" / "lib",
        PYWIN32_DLLS,
    )
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in python_paths)
    path_parts = [BIN, PY, PYWIN32_DLLS]
    env["PATH"] = os.pathsep.join(
        [str(path) for path in path_parts] + [env.get("PATH", "")]
    )
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def ascii_safe(path: Path) -> tuple[bool, str]:
    """路径必须是 ASCII 且不含空格——中文/空格路径是 Windows 部署第一大坑。"""
    text = str(path)
    if any(ord(ch) > 127 for ch in text):
        return False, "路径里有中文或其他非英文字符"
    if " " in text:
        return False, "路径里有空格"
    return True, ""


def make_writable(root: Path | None = None) -> int:
    """把包内文件/目录的只读属性去掉（解压工具常把它带进来）。"""
    import os
    import stat

    base = root or PROJECT
    fixed = 0
    try:
        items = [base] + list(base.rglob("*"))
    except Exception:
        items = [base]
    for item in items:
        try:
            mode = os.stat(item).st_mode
            if not mode & stat.S_IWRITE:
                os.chmod(item, mode | stat.S_IWRITE)
                fixed += 1
        except Exception:
            pass
    return fixed
