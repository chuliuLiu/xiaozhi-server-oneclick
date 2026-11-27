"""日志尾巴：面板只在用户勾选时读，避免无谓 IO。"""

from __future__ import annotations

from pathlib import Path

from app.common import paths

MAX_LINES = 2000


def path_for(name: str) -> Path:
    safe = name if name in ("panel", "gateway", "server") else "panel"
    green = {"server": "green_server.console.log", "gateway": "green_mqtt.console.log"}.get(safe)
    if green and (paths.LOGS / green).exists():
        return paths.LOGS / green
    return paths.LOGS / f"{safe}.log"


def tail(name: str, lines: int = 120, pattern: str = "") -> dict:
    target = path_for(name)
    if not target.exists():
        return {"name": name, "path": str(target), "exists": False, "lines": []}
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return {
            "name": name,
            "path": str(target),
            "exists": True,
            "lines": [],
            "error": str(exc),
        }
    rows = text.splitlines()
    if pattern:
        needle = pattern.lower()
        rows = [row for row in rows if needle in row.lower()]
    limit = max(1, min(int(lines or 120), MAX_LINES))
    return {
        "name": name,
        "path": str(target),
        "exists": True,
        "lines": rows[-limit:],
        "total": len(rows),
    }
