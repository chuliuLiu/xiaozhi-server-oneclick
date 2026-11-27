"""环境体检：面板第一个要回答的问题——「这台机器现在缺什么」。"""

from __future__ import annotations

import json
import platform
import subprocess
import sys

from app.common import paths
from app.panel.core import netutil, procs

CREATE_NO_WINDOW = 0x08000000


def _read_version() -> dict:
    try:
        data = json.loads(paths.VERSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return data


def _pyenv_ready() -> bool:
    return dependencies_ready()


def dependencies_ready() -> bool:
    """用随包 Python 验证项目内安装的服务端依赖。"""
    python = paths.python_for_children()
    if not python or not paths.SITE_PACKAGES.is_dir():
        return False
    code = (
        "import aiohttp, websockets, openai, onnxruntime, ruamel.yaml, loguru, "
        "opuslib_next, pydub, psutil, jinja2, ormsgpack, jwt, mcp, bs4, cnlunar"
    )
    try:
        proc = subprocess.run(
            [str(python), "-c", code],
            capture_output=True,
            timeout=45,
            env=paths.child_env(),
            creationflags=CREATE_NO_WINDOW,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _server_present() -> bool:
    return (paths.SERVER / "app.py").exists()


def _ffmpeg_ok() -> tuple[bool, str]:
    if not paths.FFMPEG.exists():
        return False, ""
    import subprocess

    try:
        proc = subprocess.run(
            [str(paths.FFMPEG), "-version"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=procs.CREATE_NO_WINDOW,
        )
        first = (proc.stdout or "").splitlines()
        return proc.returncode == 0, (first[0] if first else "")
    except Exception:
        return False, ""


def report() -> dict:
    version = _read_version()
    ascii_ok, ascii_msg = paths.ascii_safe(paths.PROJECT)

    portable = procs.run_version(paths.PORTABLE_PYTHON)
    pyenv_ready = dependencies_ready()
    system = procs.run_version(_which_python())

    ffmpeg_ok, ffmpeg_line = _ffmpeg_ok()

    ports = {}
    for name, port in (
        ("ota", _port_setting("ota", 8003)),
        ("ws", _port_setting("ws", 8005)),
        ("gateway", _port_setting("gateway", 8771)),
    ):
        listening = procs.port_open("127.0.0.1", port)
        pid = procs.read_pid("server" if name in ("ota", "ws") else "gateway")
        ports[name] = {
            "port": port,
            "listening": listening,
            "ours": bool(pid),
            "free": procs.port_free(port),
        }

    installed = pyenv_ready and _server_present() and ffmpeg_ok
    if installed:
        stage = "ready"
    elif paths.SITE_PACKAGES.exists() or _server_present() or ffmpeg_ok:
        stage = "partial"
    else:
        stage = "uninstalled"

    return {
        "product": version.get("product", "小智本地服务"),
        "version": version.get("version", "0.0.0"),
        "build": version.get("build", ""),
        "stage": stage,
        "installed": installed,
        "path": {
            "value": str(paths.PROJECT),
            "ascii": ascii_ok,
            "message": ascii_msg,
        },
        "windows": {
            "release": platform.release(),
            "version": platform.version(),
            "ok": platform.system() == "Windows",
            "machine": platform.machine(),
        },
        "disk": {
            "free_gb": procs.disk_free_gb(paths.PROJECT),
            "need_gb": 1.5,
            "ok": procs.disk_free_gb(paths.PROJECT) >= 1.5,
        },
        "python": {
            "portable": {
                "path": str(paths.PORTABLE_PYTHON),
                "exists": paths.PORTABLE_PYTHON.exists(),
                **portable,
            },
            "pyenv": {
                "path": str(paths.SITE_PACKAGES),
                "exists": paths.SITE_PACKAGES.exists(),
                "ready": pyenv_ready,
                "ok": pyenv_ready,
                "version": "",
                "raw": "",
            },
            "system": {
                "path": str(_which_python() or ""),
                "exists": bool(_which_python()),
                **system,
                "note": "只做检测，永远不会使用，也不会修改它",
            },
        },
        "ffmpeg": {
            "path": str(paths.FFMPEG),
            "ok": ffmpeg_ok,
            "line": ffmpeg_line,
        },
        "server": {
            "present": _server_present(),
            "path": str(paths.SERVER),
        },
        "ports": ports,
        "adapters": netutil.adapters(),
        "panel_python": sys.version.split()[0],
        "sizes": {
            "pyenv_mb": procs.file_size_mb(paths.PYENV),
            "server_mb": procs.file_size_mb(paths.SERVER),
            "python_mb": procs.file_size_mb(paths.PY),
        },
    }


def _which_python():
    import shutil

    found = shutil.which("python") or shutil.which("python3") or shutil.which("py")
    if not found:
        return None
    from pathlib import Path

    return Path(found)


def _port_setting(name: str, default: int) -> int:
    from app.panel.core import settings

    try:
        return int(settings.load()["ports"].get(name, default))
    except Exception:
        return default


def http_probe(url: str, timeout: float = 1.5) -> dict:
    """给自检用：只请求本地 HTTP，不发外部流量。"""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(4096).decode("utf-8", "replace")
            return {"ok": True, "status": resp.status, "body": body}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": 0, "error": f"{type(exc).__name__}: {exc}"}
