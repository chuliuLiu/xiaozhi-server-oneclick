"""防火墙一键放行（只放行专用网络，需要一次 UAC）。"""

from __future__ import annotations

import subprocess
import time

from app.common import paths

CREATE_NO_WINDOW = 0x08000000


def allow_ports(ports: list[int]) -> dict:
    ports = [int(p) for p in ports if p]
    if not ports:
        return {"ok": False, "message": "没有要放行的端口"}
    ports_text = ",".join(str(p) for p in ports)

    paths.ensure_dirs()
    bat = paths.DATA / "tmp" / "allow_firewall.bat"
    bat.parent.mkdir(parents=True, exist_ok=True)
    script = "\r\n".join(
        [
            "@echo off",
            'netsh advfirewall firewall delete rule name="XiaozhiServer" >nul 2>&1',
            'netsh advfirewall firewall delete rule name="XiaozhiServer-UDP" >nul 2>&1',
            (
                'netsh advfirewall firewall add rule name="XiaozhiServer" '
                f"dir=in action=allow protocol=TCP localport={ports_text} profile=private"
            ),
            (
                'netsh advfirewall firewall add rule name="XiaozhiServer-UDP" '
                f"dir=in action=allow protocol=UDP localport={ports_text} profile=private"
            ),
            "exit /b %errorlevel%",
        ]
    )
    bat.write_text(script, encoding="utf-8")

    ps = (
        "Start-Process -FilePath '{}' -Verb RunAs -Wait -WindowStyle Hidden; "
        "exit $LASTEXITCODE"
    ).format(str(bat).replace("'", "''"))
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=90,
            creationflags=CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "等你确认管理员权限超时了，可以稍后再点一次"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"没能调用系统防火墙：{exc}"}

    if proc.returncode == 0:
        return {
            "ok": True,
            "message": f"已放行端口 {ports_text}（仅专用网络）",
        }
    detail = (proc.stderr or proc.stdout or "").strip()
    if "canceled" in detail.lower() or proc.returncode == 1:
        return {
            "ok": False,
            "message": "你取消了管理员授权。也可以在管理员命令行里手动执行 data\\tmp\\allow_firewall.bat",
        }
    return {"ok": False, "message": "放行失败，可以手动运行 data\\tmp\\allow_firewall.bat", "detail": detail[:200]}


def cleanup_old() -> None:
    bat = paths.DATA / "tmp" / "allow_firewall.bat"
    try:
        if bat.exists() and time.time() - bat.stat().st_mtime > 86400:
            bat.unlink(missing_ok=True)
    except Exception:
        pass
