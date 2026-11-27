from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import time
from pathlib import Path

from app.common import paths

CREATE_NO_WINDOW = 0x08000000


def run_version(exe: Path) -> dict:
    """跑 <exe> -V，返回 {ok, version, raw}。"""
    if not exe.exists():
        return {"ok": False, "version": "", "raw": ""}
    try:
        proc = subprocess.run(
            [str(exe), "-V"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=CREATE_NO_WINDOW,
        )
        raw = (proc.stdout or proc.stderr or "").strip()
        return {"ok": proc.returncode == 0, "version": raw, "raw": raw}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "version": "", "raw": str(exc)}


def file_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0
    if path.is_file():
        total = path.stat().st_size
    else:
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(root, name))
                except OSError:
                    pass
    return round(total / 1024 / 1024, 1)


def disk_free_gb(path: Path) -> float:
    try:
        usage = __import__("shutil").disk_usage(str(path))
        return round(usage.free / 1024 / 1024 / 1024, 1)
    except Exception:
        return 0.0


def port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def port_free(port: int, host: str = "0.0.0.0") -> bool:
    """严格检测：不用 SO_REUSEADDR，Windows 上加 EXCLUSIVEADDRUSE。

    SO_REUSEADDR 在 Windows 上会"允许"两个程序绑同一端口，用它判断会误判成空闲。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
            if exclusive is not None:
                sock.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        sock.bind((host, int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def listener_pids(port: int) -> list[int]:
    """这个端口上所有 LISTENING 的 pid（可能为空：被系统保留但没人监听）。"""
    try:
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        return []
    suffix = f":{int(port)}"
    pids: list[int] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        if "LISTENING" not in line.upper():
            continue
        if not parts[1].endswith(suffix):
            continue
        try:
            pid = int(parts[-1])
        except ValueError:
            continue
        if pid and pid not in pids:
            pids.append(pid)
    return pids


def listener_ports_of_pid(pid: int) -> list[int]:
    """这个进程在监听哪些 TCP 端口（配置和实际不一致时，用它兜底找设备连接）。"""
    try:
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        return []
    ports: list[int] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        if "LISTENING" not in line.upper():
            continue
        try:
            if int(parts[-1]) != int(pid):
                continue
            port = int(parts[1].rsplit(":", 1)[1])
        except (ValueError, IndexError):
            continue
        if port not in ports:
            ports.append(port)
    return ports


def excluded_port_ranges() -> list[tuple[int, int]]:
    """Windows/Hyper-V 保留的端口段。落在里面的端口没人监听也绑不上。"""
    if os.name != "nt":
        return []
    try:
        proc = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "excludedportrange", "protocol=tcp"],
            capture_output=True,
            text=True,
            encoding="utf-8",  # netsh 输出 UTF-8，按系统编码(GBK)解码会抛 UnicodeDecodeError
            errors="replace",
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
        text = proc.stdout or ""
    except Exception:
        return []
    ranges: list[tuple[int, int]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if parts[0].isdigit() and parts[1].isdigit():
            start, end = int(parts[0]), int(parts[1])
            if 0 < start <= end < 65536:
                ranges.append((start, end))
    return ranges


def port_diagnose(port: int) -> dict:
    port = int(port)
    pids = listener_pids(port)
    listeners = []
    for pid in pids:
        exe = exe_path(pid)
        listeners.append(
            {
                "pid": pid,
                "exe": exe,
                "name": os.path.basename(exe) if exe else "",
            }
        )
    free = port_free(port)
    excluded = any(start <= port <= end for start, end in excluded_port_ranges())
    if free:
        verdict = "free"
    elif listeners:
        verdict = "occupied"
    else:
        verdict = "blocked"
    return {
        "port": port,
        "free": free,
        "listeners": listeners,
        "excluded": excluded,
        "verdict": verdict,
    }


def find_free_port(start: int, span: int = 80) -> int:
    for candidate in range(int(start), int(start) + span):
        if candidate > 65535:
            break
        if port_free(candidate):
            return candidate
    raise RuntimeError(f"{start} 往后 {span} 个端口都不可用")


def pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return False
    try:
        code = ctypes.c_ulong(0)
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return code.value == 259  # STILL_ACTIVE
        return True
    finally:
        kernel32.CloseHandle(handle)


def read_pid(name: str) -> dict | None:
    path = paths.RUN / f"{name}.pid"
    if not path.exists():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        pid = int(data.get("pid") or 0)
        if not pid_alive(pid):
            path.unlink(missing_ok=True)
            return None
        data["alive"] = True
        return data
    except Exception:
        return None


def write_pid(name: str, pid: int, extra: dict | None = None) -> None:
    import json

    paths.ensure_dirs()
    payload = {"pid": int(pid), "started_at": time.time()}
    payload.update(extra or {})
    (paths.RUN / f"{name}.pid").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def clear_pid(name: str) -> None:
    (paths.RUN / f"{name}.pid").unlink(missing_ok=True)


def kill_pid(pid: int) -> None:
    """先走 Win32 TerminateProcess（快、不依赖 taskkill），失败再兜底 taskkill。"""
    if not pid:
        return
    if os.name == "nt":
        PROCESS_TERMINATE = 0x0001
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, int(pid))
        if handle:
            try:
                kernel32.TerminateProcess(handle, 1)
            finally:
                kernel32.CloseHandle(handle)
            return
    try:
        subprocess.run(
            ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
            capture_output=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        pass


def established_remotes(port: int) -> list[str]:
    """谁连在这个端口上（判断机器狗在不在线）。只用 netstat，不依赖 psutil。"""
    try:
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        return []
    remotes: set[str] = set()
    suffix = f":{int(port)}"
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[0].upper() != "TCP":
            continue
        if parts[3].upper() != "ESTABLISHED":
            continue
        local, remote = parts[1], parts[2]
        if not local.endswith(suffix):
            continue
        host = remote.rsplit(":", 1)[0]
        if host in ("127.0.0.1", "::1", "[::1]"):
            continue
        remotes.add(host)
    return sorted(remotes)


def listener_pid(port: int) -> int | None:
    """谁在 LISTENING 这个端口（兜底：pid 文件丢了也能找回自己的进程）。"""
    try:
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        return None
    suffix = f":{int(port)}"
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        if "LISTENING" not in line.upper():
            continue
        if not parts[1].endswith(suffix):
            continue
        try:
            return int(parts[-1])
        except ValueError:
            continue
    return None


def command_line(pid: int) -> str:
    if not pid or os.name != "nt":
        return ""
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=CREATE_NO_WINDOW,
        )
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def exe_path(pid: int) -> str:
    """进程的可执行文件路径。用 Win32 API，不依赖 WMI（WMI 在部分机器上被禁用）。"""
    if not pid or os.name != "nt":
        return ""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_ulong(1024)
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        return buf.value if ok else ""
    finally:
        kernel32.CloseHandle(handle)


def kill_by_port(port: int, must_contain: str) -> bool:
    """只在确认是本项目的进程时才杀，绝不误杀。

    先看命令行（WMI）；拿不到时退回看 exe 路径（Win32 API）——
    便携 Python 一定在我们自己的 runtime 目录里，这个判断最可靠。
    """
    pid = listener_pid(port)
    if not pid:
        return False
    cmd = command_line(pid)
    if cmd and must_contain.lower() in cmd.lower():
        kill_pid(pid)
        return True
    exe = exe_path(pid).lower()
    runtime = str(paths.RUNTIME).lower()
    if exe and runtime in exe:
        kill_pid(pid)
        return True
    return False
