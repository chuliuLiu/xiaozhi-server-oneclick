"""卸载：停掉本目录起的进程、清掉防火墙规则，可选连文件夹一起删。

用法（一般由根目录的 卸载.bat 调用）：
    python tools/uninstall.py --menu    # 显示交互菜单
    python tools/uninstall.py            # 只清理，文件夹留着
    python tools/uninstall.py --purge    # 清理后 3 秒删除整个文件夹
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.panel.core import procs  # noqa: E402

CREATE_NO_WINDOW = 0x08000000
DETACHED = 0x00000008 | 0x00000200


def load_ports() -> dict:
    try:
        data = json.loads((ROOT / "data" / "settings.json").read_text(encoding="utf-8-sig"))
        return data.get("ports") or {}
    except Exception:
        return {"panel": 8770, "gateway": 8771, "ota": 8003, "ws": 8005, "mqtt": 1883}


def stop_services(ports: dict) -> list[str]:
    stopped = []
    # 面板自己是 pythonw，先按端口找出来关掉
    panel_port = int(ports.get("panel") or 0)
    if panel_port and procs.listener_pids(panel_port):
        try:
            if procs.kill_by_port(panel_port, str(ROOT)):
                stopped.append("面板")
        except Exception:
            pass
    for name in ("server", "gateway", "mqttgw"):
        info = procs.read_pid(name)
        if info:
            procs.kill_pid(int(info["pid"]))
            procs.clear_pid(name)
            stopped.append(f"{name}(pid {info['pid']})")
    for port_name in ("ota", "ws", "gateway", "mqtt"):
        port = int(ports.get(port_name) or 0)
        if not port:
            continue
        if procs.listener_pids(port):
            try:
                if procs.kill_by_port(port, str(ROOT)):
                    stopped.append(f"端口 {port} 上的本项目进程")
            except Exception:
                pass
    return stopped


def remove_firewall() -> str:
    cmd = [
        "netsh",
        "advfirewall",
        "firewall",
        "delete",
        "rule",
        "name=XiaozhiServer",
    ]
    try:
        # 只关心 returncode：netsh 输出是 UTF-8，不能再按系统编码解码
        proc = subprocess.run(
            cmd, capture_output=True, timeout=20, creationflags=CREATE_NO_WINDOW
        )
        if proc.returncode == 0:
            return "已删除防火墙规则（专用网络放行）"
    except Exception:
        pass
    # 没有管理员权限时提权再试一次（会弹一次 UAC）
    ps = (
        "Start-Process netsh -ArgumentList "
        "'advfirewall firewall delete rule name=XiaozhiServer' "
        "-Verb RunAs -Wait -WindowStyle Hidden"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            timeout=60,
            creationflags=CREATE_NO_WINDOW,
        )
        return "已请求管理员删除防火墙规则"
    except Exception:
        return "防火墙规则没删掉（可以忽略，不影响系统；也可手动删除名为 XiaozhiServer 的规则）"




def _schedule_cleanup(paths_to_remove: list[str]) -> None:
    """写一个临时 bat，等 3 秒后删（此时本进程和父 cmd 都已退出）。"""
    tmp = Path(os.environ.get("TEMP", str(ROOT.parent)))
    bat = tmp / "xiaozhi-cleanup.bat"
    log = tmp / "xiaozhi-cleanup.log"
    lines = [
        "@echo off",
        f'cd /d "{tmp}"',
        "ping -n 4 127.0.0.1 >nul",
        f'echo start %date% %time% > "{log}"',
    ]
    for item in paths_to_remove:
        lines.append(f'rd /s /q "{item}" >> "{log}" 2>&1')
        lines.append(f'if exist "{item}" echo FAILED: {item} >> "{log}"')
    lines.append(f'echo done >> "{log}"')
    lines.append('start "" /b cmd /c del /f /q "%~f0" >nul 2>&1')
    bat.write_text("\r\n".join(lines), encoding="utf-8")
    # 用相对文件名启动，避免路径里有空格/中文时 cmd 解析失败
    subprocess.Popen(
        ["cmd", "/c", bat.name],
        creationflags=DETACHED,
        close_fds=True,
        cwd=str(tmp),
    )
    print("清理日志（如果没删干净，把它发我）：", log)


def purge_keep_data() -> None:
    """删程序文件，但把 data\\ 留下（密钥、记忆、日志还在）。"""
    keep = ROOT / "data"
    keep.mkdir(exist_ok=True)
    os.chdir(os.environ.get("TEMP", str(ROOT.parent)))
    for child in ROOT.iterdir():
        if child == keep:
            continue
        try:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        except Exception:
            pass
    items = [str(c) for c in ROOT.iterdir() if c != keep]
    _schedule_cleanup(items)
    print("\n3 秒后删除程序文件，只保留：")
    print(" ", keep)
    print("里面的 settings.json 是你的密钥和配置，下次装回来可以直接覆盖使用。")

def purge() -> None:
    parent = ROOT.parent
    target = str(ROOT)
    # 先离开这个目录，否则 Windows 删不掉
    os.chdir(os.environ.get("TEMP", str(parent)))
    print("\n3 秒后删除整个文件夹：")
    print(" ", target)
    _schedule_cleanup([target])


def _confirm(prompt: str) -> bool:
    while True:
        try:
            answer = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("请输入 y 或 n。")


def _menu_args() -> list[str] | None:
    print("小智本地服务 · 卸载")
    print("=" * 30)
    print("1. 只停止服务（文件和数据都保留，以后还能用）")
    print("2. 删除程序文件，保留 data（密钥、记忆和日志保留）")
    print("3. 彻底删除整个文件夹（含 data，不可恢复）")
    print("0. 什么都不做，退出")

    while True:
        try:
            choice = input("\n请选择 [1/2/3/0]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            return None
        if choice in ("0", "1", "2", "3"):
            break
        print("输入无效，请输入 1、2、3 或 0。")

    if choice == "0":
        print("已取消。")
        return None
    if choice == "1":
        return []
    if choice == "2":
        if _confirm("将删除程序文件，只保留 data 文件夹。确认继续 [y/n]: "):
            return ["--purge", "--keep-data"]
        print("已取消。")
        return None
    if _confirm("警告：整个文件夹（包括密钥、记忆、日志）都会被删除，无法恢复。确认继续 [y/n]: "):
        return ["--purge"]
    print("已取消。")
    return None


def main() -> int:
    args = sys.argv[1:]
    interactive = "--menu" in args
    if interactive:
        selected = _menu_args()
        if selected is None:
            return 0
        args = selected
    flags = set(args)

    ports = load_ports()
    if not interactive:
        print("小智本地服务 · 卸载")
        print("=" * 30)
    stopped = stop_services(ports)
    print("进程：", "已停止 " + "、".join(stopped) if stopped else "没有在跑的本项目进程")
    if "--no-firewall" in flags:
        print("防火墙：已跳过（--no-firewall）")
    else:
        print("防火墙：", remove_firewall())
    print("注册表 / 服务 / 计划任务：本程序从不写这些，无需清理。")
    print("用户数据：data\\ 目录（密钥、记忆、日志）默认保留。")
    if "--purge" in flags and "--keep-data" in flags:
        purge_keep_data()
    elif "--purge" in flags:
        purge()
    else:
        print("\n以后还想用：直接关掉这个窗口即可（文件都在）。")
        print("彻底不用了：再运行一次 卸载.bat 选 3。")
    if interactive and ("--purge" not in flags or "--keep-data" in flags):
        try:
            input("\n按 Enter 键关闭窗口...")
        except (EOFError, KeyboardInterrupt):
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
