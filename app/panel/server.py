#!/usr/bin/env python3
"""小智本地服务 · 控制面板（只依赖 Python 标准库）。

为什么用 stdlib：安装前就得能跑。依赖是「安装之后」才有的东西，
面板自己不能依赖它们，否则就出现"装不上就打不开面板"的死锁。

用法：
    python app/panel/server.py --port 8770 [--no-browser] [--debug]
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

PROJECT = Path(__file__).resolve().parents[2]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from app.common import paths  # noqa: E402
from app.panel.core import (  # noqa: E402
    envprobe,
    firewall,
    logs,
    netutil,
    procs,
    services,
    settings,
)
from app.panel.installer.job import InstallJob  # noqa: E402

START = time.time()
logger = logging.getLogger("panel")

_HTTPD = None  # 由 main() 赋值，给「退出面板」接口用

_install_job: InstallJob | None = None
_install_lock = threading.Lock()
_KEEP_SERVICES_ON_EXIT = False


def get_install_job() -> InstallJob:
    global _install_job
    with _install_lock:
        if _install_job is None:
            _install_job = InstallJob()
        return _install_job


def _schedule_shutdown() -> None:
    """让 HTTP 主循环退出；真正的清理在 main() 的 finally 里。"""
    import time as _time

    def worker() -> None:
        _time.sleep(0.4)
        try:
            if _HTTPD is not None:
                _HTTPD.shutdown()
        except Exception:
            pass

    threading.Thread(target=worker, name="panel-shutdown", daemon=True).start()


# --------------------------------------------------------------------------- 安装计划


def install_plan() -> dict:
    env = envprobe.report()
    py = env["python"]
    pyenv = py["pyenv"]
    ffmpeg = env["ffmpeg"]["ok"]
    server = env["server"]["present"]

    steps = [
        {
            "id": "python",
            "name": "便携 Python 3.11",
            "desc": "随包自带，不读取、不修改你电脑上的 Python",
            "download_mb": 0,
            "disk_mb": 95,
            "required": True,
            "status": "done" if py["portable"]["ok"] else "pending",
            "detail": py["portable"].get("version", ""),
        },
        {
            "id": "pyenv",
            "name": "项目内依赖目录",
            "desc": "依赖保存在项目目录，随绿色版一起移动",
            "download_mb": 0,
            "disk_mb": 1,
            "required": True,
            "status": "done" if pyenv["exists"] else "pending",
            "detail": str(paths.SITE_PACKAGES) if pyenv["exists"] else "",
        },
        {
            "id": "deps",
            "name": "语音与网络依赖",
            "desc": "连百炼、推流、解码要用的库（不装 torch，省 2GB）",
            "download_mb": 170,
            "disk_mb": 520,
            "required": True,
            "status": "done" if pyenv["ready"] else "pending",
            "detail": f"已占用 {env['sizes']['pyenv_mb']} MB" if pyenv["ready"] else "",
        },
        {
            "id": "ffmpeg",
            "name": "音频组件",
            "desc": "ffmpeg 与 opus 解码器，机器狗的声音靠它",
            "download_mb": 40,
            "disk_mb": 40,
            "required": True,
            "status": "done" if ffmpeg else "pending",
            "detail": env["ffmpeg"].get("line", ""),
        },
        {
            "id": "server",
            "name": "小智服务端",
            "desc": "内置上游 0.9.8，不用你去 GitHub 下载",
            "download_mb": 0,
            "disk_mb": 27,
            "required": True,
            "status": "done" if server else "pending",
            "detail": env["server"]["path"],
        },
        {
            "id": "config",
            "name": "生成默认配置",
            "desc": "唤醒词、人设、端口，装完就能用",
            "download_mb": 0,
            "disk_mb": 1,
            "required": True,
            "status": "done" if env["installed"] else "pending",
            "detail": "",
        },
        {
            "id": "verify",
            "name": "收尾自检",
            "desc": "检查每一块真的能用",
            "download_mb": 0,
            "disk_mb": 0,
            "required": True,
            "status": "done" if env["installed"] else "pending",
            "detail": "",
        },
    ]

    disk_mb = sum(step["disk_mb"] for step in steps if step["status"] != "done")
    download_mb = sum(step["download_mb"] for step in steps if step["status"] != "done")
    return {
        "steps": steps,
        "total_disk_mb": disk_mb,
        "total_download_mb": download_mb,
        "installed": env["installed"],
        "stage": env["stage"],
        "eta": "3–8 分钟" if download_mb else "不到 1 分钟",
        "path": env["path"],
        "disk_free_gb": env["disk"]["free_gb"],
    }


# --------------------------------------------------------------------------- 语音试听

PREVIEW_TEXT = "你好呀，今天想玩点什么？"


def synthesize_preview(payload: dict) -> tuple[dict, int]:
    import hashlib

    conf = settings.load()
    key = settings.bailian_key(conf)
    if not key:
        return {"ok": False, "message": "先填百炼 API Key，再试听"}, 400
    python = paths.python_for_children()
    if not python:
        return {"ok": False, "message": "还没安装运行环境"}, 409

    voice = (payload.get("voice") or (conf.get("voice") or {}).get("voice_id") or "longanyang").strip()
    model = (payload.get("model") or (conf.get("voice") or {}).get("tts_model") or "cosyvoice-v3-flash").strip()
    text = (payload.get("text") or PREVIEW_TEXT).strip()[:80]

    digest = hashlib.sha1(f"{voice}|{model}|{text}".encode("utf-8")).hexdigest()[:12]
    out = paths.DATA / "tmp" / f"preview-{digest}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 22050 if model.startswith("cosyvoice-v2") else 24000

    if not out.exists():
        script = paths.TOOLS / "preview_tts.py"
        if not script.exists():
            return {"ok": False, "message": "试听脚本缺失，安装包不完整"}, 500
        try:
            proc = subprocess.run(
                [
                    str(paths.PORTABLE_PYTHON if paths.PORTABLE_PYTHON.exists() else python),
                    str(script),
                    "--key",
                    key,
                    "--voice",
                    voice,
                    "--model",
                    model,
                    "--text",
                    text,
                    "--out",
                    str(out),
                    "--sample-rate",
                    str(sample_rate),
                ],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=procs.CREATE_NO_WINDOW,
                env={
                    **paths.child_env(),
                    "TMP": str(paths.DATA / "tmp"),
                    "TEMP": str(paths.DATA / "tmp"),
                },
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "message": "试听超时（20 秒），检查网络再试"}, 504
        if proc.returncode != 0 or not out.exists():
            detail = (proc.stderr or proc.stdout or "").strip().splitlines()
            line = detail[-1] if detail else ""
            return {
                "ok": False,
                "message": "试听失败：Key 不对、余额不足，或者这个音色和模型不配套。可以换个音色，或看「声音复刻教程」。",
                "detail": line[:200],
            }, 502

    return {
        "ok": True,
        "url": f"/api/voice/preview.wav?f={out.name}",
        "voice": voice,
        "model": model,
        "bytes": out.stat().st_size,
    }, 200


# --------------------------------------------------------------------------- 服务状态


def service_status() -> dict:
    return services.status()


def _ota_info() -> dict:
    conf = settings.load()
    port = int(conf["ports"]["ota"])
    items = netutil.adapters()
    return {
        "port": port,
        "adapters": items,
        "urls": [
            {
                "ip": item["ip"],
                "name": item["name"],
                "url": f"http://{item['ip']}:{port}/xiaozhi/ota/",
                "recommended": bool(item.get("recommended")),
                "virtual": bool(item.get("virtual")),
            }
            for item in items
        ],
    }


# --------------------------------------------------------------------------- 自检


def selftest() -> dict:
    conf = settings.load()
    env = envprobe.report()
    from app.panel.core import green as _g
    green_mode = _g.NODE.exists() and _g.SERVER_DIR.exists()
    if green_mode:
        env = {**env, "installed": True}
    checks = []

    def add(key, title, state, detail="", hint=""):
        checks.append(
            {"key": key, "title": title, "state": state, "detail": detail, "hint": hint}
        )

    add(
        "install",
        "运行环境",
        "ok" if env["installed"] else "fail",
        "已就绪" if env["installed"] else "还没有安装",
        "去「环境检查」点重新检查" if not env["installed"] else "",
    )
    key = settings.bailian_key(conf)
    add(
        "key",
        "千问AI平台 API Key",
        "ok" if key else "fail",
        "已配置" if key else "没填",
        "" if key else "在「密钥参数」里填千问AI平台 API Key",
    )
    asr_model = ((conf.get("asr") or {}).get("model") or "").strip()
    if asr_model in ("paraformer-realtime-v2", "paraformer-realtime-v1"):
        add(
            "asr",
            "语音识别模型",
            "warn",
            f"{asr_model}（已下线）",
            "保存一次配置会自动换成 fun-asr-realtime",
        )
    else:
        add("asr", "语音识别模型", "ok", asr_model or "fun-asr-realtime", "")
    persona_conf = conf.get("persona") or {}
    words = [str(w) for w in (persona_conf.get("wakeup_words") or []) if str(w).strip()]
    add(
        "persona",
        "人设与唤醒词",
        "ok" if words else "warn",
        f"唤醒词：{'、'.join(words[:5]) or '（空）'}",
        "" if words else "去「密钥参数 → 人设」加一个唤醒词",
    )
    if green_mode:
        mqtt_port = int((conf.get("ports") or {}).get("mqtt") or 1883)
        add("mqtt", "MQTT 通道", "ok" if procs.port_open("127.0.0.1", mqtt_port) else "fail", f"{mqtt_port} 在监听" if procs.port_open("127.0.0.1", mqtt_port) else "没在监听", "")
        ws_port = int((conf.get("ports") or {}).get("ws") or 8000)
        add("ports", "语音服务端口", "ok" if procs.port_open("127.0.0.1", ws_port) else "fail", f"{ws_port} 在监听" if procs.port_open("127.0.0.1", ws_port) else "没在监听", "")
    elif not env["installed"]:
        add("gateway", "大脑网关", "skip", "等安装完再测", "")
        add("ports", "语音服务端口", "skip", "等安装完再测", "")
    else:
        probe = envprobe.http_probe(
            f"http://127.0.0.1:{int(conf['ports']['gateway'])}/health"
        )
        add(
            "gateway",
            "大脑网关",
            "ok" if probe["ok"] else "fail",
            "在线" if probe["ok"] else probe.get("error", "未响应"),
            "" if probe["ok"] else "在「运行管理」点启动",
        )
        mqtt_port = int((conf.get("ports") or {}).get("mqtt") or 1883)
        add(
            "mqtt",
            "MQTT 通道",
            "ok" if procs.port_open("127.0.0.1", mqtt_port) else "fail",
            f"{mqtt_port} 在监听" if procs.port_open("127.0.0.1", mqtt_port) else "没在监听",
            "" if procs.port_open("127.0.0.1", mqtt_port) else "去「运行管理」重新启动",
        )
        listening = procs.port_open("127.0.0.1", int(conf["ports"]["ws"]))
        add(
            "ports",
            "语音服务端口",
            "ok" if listening else "fail",
            "在监听" if listening else "没在监听",
            "" if listening else "启动服务，或检查端口是否被占用",
        )
    if not paths.python_for_children():
        add("tts", "语音合成试听", "skip", "还没安装运行环境", "点「重新检查」看一下")
    elif not key:
        add("tts", "语音合成试听", "fail", "没填 Key", "先填百炼 Key")
    else:
        try:
            preview = synthesize_preview({"text": "你好呀"})
        except Exception as exc:  # noqa: BLE001
            preview = ({"ok": False, "message": f"试听出错：{exc}"}, 500)
        payload, _code = preview
        if payload.get("ok"):
            add(
                "tts",
                "语音合成试听",
                "ok",
                f"成功（{payload.get('model')} / {payload.get('voice')}）",
                "",
            )
        else:
            add(
                "tts",
                "语音合成试听",
                "fail",
                (payload.get("message") or "没合成出来")[:60],
                (payload.get("detail") or "")[:80],
            )
    try:
        dev = services.status().get("device") or {}
    except Exception:
        dev = {}
    if dev.get("count"):
        add("device", "机器狗", "ok", f"{dev['count']} 台在线", "")
    elif dev.get("recently"):
        add("device", "机器狗", "warn", "刚才连过，现在不在线", "检查狗是否休眠或换了 Wi-Fi")
    else:
        add("device", "机器狗", "skip", "还没有设备连上来", "把 OTA 地址填进机器狗")
    ok = sum(1 for c in checks if c["state"] == "ok")
    bad = sum(1 for c in checks if c["state"] == "fail")
    return {
        "checks": checks,
        "summary": {"ok": ok, "fail": bad, "total": len(checks)},
        "overall": "ok" if bad == 0 else "fail",
    }


# --------------------------------------------------------------------------- LLM 探测


def list_models(payload: dict) -> tuple[dict, int]:
    conf = settings.load()
    base = (payload.get("base_url") or "").strip().rstrip("/") or (
        (conf.get("brain") or {}).get("base_url") or ""
    ).strip().rstrip("/")
    key = (payload.get("api_key") or "").strip()
    if not key or settings.is_mask(key):
        # 前端只拿到脱敏值：用本机存的真 key 去测
        key = ((conf.get("brain") or {}).get("api_key") or "").strip() or (
            (conf.get("keys") or {}).get("bailian") or ""
        ).strip()
    if not base:
        return {"ok": False, "message": "先填好这个服务商的地址"}, 400
    if not key:
        return {"ok": False, "message": "先填好 API Key"}, 400
    req = urllib.request.Request(
        f"{base}/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        items = data.get("data") or data.get("models") or []
        if isinstance(items, dict):
            items = list(items.keys())
        models = []
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict):
                name = item.get("id") or item.get("name")
            else:
                name = item
            if isinstance(name, str) and name.strip():
                models.append(name.strip())
        return {"ok": True, "models": sorted(set(models))}, 200
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return {
                "ok": False,
                "message": "API Key 不对，或者这个 Key 没有该模型的权限",
            }, 401
        return {"ok": False, "message": f"服务商返回了 {exc.code}，稍后再试"}, 400
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "message": f"连不上这个地址（{type(exc).__name__}）",
        }, 502


# --------------------------------------------------------------------------- HTTP


class Handler(BaseHTTPRequestHandler):
    server_version = "XiaozhiPanel/0.1"
    protocol_version = "HTTP/1.1"

    # --- 工具 ---
    def _send_json(self, payload: Any, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > 2 * 1024 * 1024:
            raise ValueError("请求体太大")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"请求体不是合法 JSON：{exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("请求体必须是对象")
        return data

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        logger.info("%s - %s", self.address_string(), fmt % args)

    # --- 路由 ---
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        try:
            if route.startswith("/api/"):
                if route == "/api/voice/preview.wav":
                    self._serve_preview(query)
                    return
                payload, code = self._route_get(route, query)
                self._send_json(payload, code)
                return
            self._serve_static(route)
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.error("GET %s 失败: %s\n%s", route, exc, traceback.format_exc())
            self._send_json(
                {"ok": False, "message": "面板内部出错了", "detail": str(exc)}, 500
            )

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        try:
            body = self._read_json()
        except ValueError as exc:
            self._send_json({"ok": False, "message": str(exc)}, 400)
            return
        try:
            payload, code = self._route_post(route, body)
            self._send_json(payload, code)
        except BrokenPipeError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.error("POST %s 失败: %s\n%s", route, exc, traceback.format_exc())
            self._send_json(
                {"ok": False, "message": "面板内部出错了", "detail": str(exc)}, 500
            )

    def _route_get(self, route: str, query: dict) -> tuple[dict, int]:
        if route == "/api/green/env":
            from app.panel.core import green as _green

            checks = []
            def add(name, ok, detail):
                checks.append({"name": name, "ok": bool(ok), "detail": detail})

            add("便携 Python", paths.PORTABLE_PYTHON.exists(), str(paths.PORTABLE_PYTHON))
            add("运行环境", _green.SERVER_DIR.exists(), str(_green.SERVER_DIR))
            add("语音依赖", envprobe.dependencies_ready(), str(paths.SITE_PACKAGES))
            add("Node 运行时", _green.NODE.exists(), str(_green.NODE))
            add("MQTT 网关", (_green.GW_DIR / "app.js").exists(), str(_green.GW_DIR))
            add("网关依赖", (_green.GW_DIR / "node_modules").exists(), "node_modules")
            add("音频组件", paths.FFMPEG.exists(), str(paths.FFMPEG))
            return {"ok": all(c["ok"] for c in checks), "checks": checks}, 200

        if route == "/api/health":
            return (
                {
                    "ok": True,
                    "product": "小智本地服务",
                    "version": json.loads(
                        paths.VERSION_FILE.read_text(encoding="utf-8")
                    ).get("version", "0.1.0")
                    if paths.VERSION_FILE.exists()
                    else "0.1.0",
                    "pid": os.getpid(),
                    "uptime": int(time.time() - START),
                    "python": sys.version.split()[0],
                    "project": str(paths.PROJECT),
                    "settings_exists": paths.SETTINGS_FILE.exists(),
                },
                200,
            )
        if route == "/api/env":
            return envprobe.report(), 200
        if route == "/api/install/plan":
            return install_plan(), 200
        if route == "/api/settings":
            return {"ok": True, "settings": settings.masked(settings.load())}, 200
        if route == "/api/service/status":
            return {"ok": True, **service_status()}, 200
        if route == "/api/net/adapters":
            return {"ok": True, "adapters": netutil.adapters()}, 200
        if route == "/api/net/ota":
            return {"ok": True, **_ota_info()}, 200
        if route == "/api/net/ports":
            conf = settings.load()
            ports = conf.get("ports") or {}
            result = {
                "ok": True,
                "ports": {
                    name: procs.port_diagnose(int(ports.get(name, default)))
                    for name, default in (
                        ("gateway", 8771),
                        ("ota", 8003),
                        ("ws", 8005),
                        ("panel", 8770),
                    )
                },
                "excluded": procs.excluded_port_ranges(),
            }
            return result, 200
        if route == "/api/logs":
            name = (query.get("name") or ["panel"])[0]
            lines = int((query.get("lines") or ["120"])[0] or 120)
            pattern = (query.get("pattern") or [""])[0]
            return {"ok": True, **logs.tail(name, lines, pattern)}, 200
        if route == "/api/selftest":
            return {"ok": True, **selftest()}, 200
        if route == "/api/install/progress":
            return {"ok": True, **get_install_job().snapshot()}, 200
        return {"ok": False, "message": f"没有这个接口：{route}"}, 404

    def _route_post(self, route: str, body: dict) -> tuple[dict, int]:
        if route == "/api/green/validate":
            import json as _json
            import urllib.request as _url

            base = str(body.get("base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
            key = str(body.get("api_key") or "").strip()
            if not key:
                return {"ok": False, "kind": "credential", "message": "没填 Key"}, 200
            req = _url.Request(
                base + "/models",
                headers={"Authorization": "Bearer " + key},
            )
            try:
                with _url.urlopen(req, timeout=12) as resp:
                    data = _json.loads(resp.read().decode("utf-8", "replace"))
                return {"ok": True, "models": len(data.get("data") or [])}, 200
            except _url.HTTPError as exc:
                return {"ok": False, "kind": "credential", "message": f"Key 验证失败（HTTP {exc.code}）"}, 200
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "kind": "network", "message": f"网络不通：{exc}"}, 200

        if route == "/api/settings":
            current = settings.load()
            patch = body.get("settings") if "settings" in body else body
            if not isinstance(patch, dict):
                return {"ok": False, "message": "配置格式不对"}, 400
            import urllib.request as _u
            import urllib.error as _ue

            def _check(base: str, key: str):
                base = str(base or "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
                try:
                    req = _u.Request(base + "/models", headers={"Authorization": "Bearer " + key})
                    with _u.urlopen(req, timeout=12):
                        pass
                    return ("ok", "")
                except _ue.HTTPError as exc:
                    if int(exc.code) in (401, 403):
                        return ("bad", f"HTTP {exc.code}")
                    return ("ok", "")
                except Exception:
                    return ("net", "")

            patch_brain = patch.get("brain") or {}
            patch_keys = patch.get("keys") or {}
            dashscope = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            vendor = str(patch_brain.get("vendor") or "")
            llm_base = patch_brain.get("base_url") or dashscope
            llm_key = str(patch_brain.get("api_key") or "")
            if not llm_key and vendor in ("", "bailian", "aliyun"):
                llm_key = str(patch_keys.get("bailian") or "")
            voice_key = str(patch_keys.get("bailian") or "")
            network_ok = True
            checked = False
            for base, key in ((llm_base, llm_key), (dashscope, voice_key)):
                key = key.strip()
                if not key or "****" in key:
                    continue
                state, info = _check(base, key)
                checked = True
                if state == "bad":
                    return {"ok": False, "code": "bad_key", "message": f"Key 验证失败（{info}），没有保存"}, 200
                if state == "net":
                    network_ok = False

            def _key_state(raw, saved, empty_ok=False) -> str:
                """ok=填了真实值；keep=沿用本机已存值；missing=没有可用 Key。
                empty_ok=True 时「留空」也算沿用（百炼那格就是这种语义）。"""
                text = str(raw or "").strip()
                if text and "****" not in text:
                    return "ok"
                if not text and not empty_ok:
                    return "missing"
                return "keep" if str(saved or "").strip() else "missing"

            cur_brain = current.get("brain") or {}
            cur_keys = current.get("keys") or {}
            _old_vendor = str(cur_brain.get("vendor") or "")
            _new_vendor = str(patch_brain.get("vendor") or _old_vendor)
            bailian_family = _new_vendor in ("", "bailian", "aliyun")
            brain_key_state = _key_state(patch_brain.get("api_key"), cur_brain.get("api_key"))
            # 百炼（含默认/阿里云）复用「千问AI平台 Key」：brain 单独填了就用 brain，否则看 keys.bailian
            key_state = brain_key_state
            if bailian_family and brain_key_state != "ok":
                key_state = _key_state(patch_keys.get("bailian"), cur_keys.get("bailian"), empty_ok=True)
            if _new_vendor != _old_vendor and "brain" in patch:
                # 切供应商：别的家必须真填新 Key；百炼可以复用本机已存（脱敏）的 Key
                _ok = key_state in ("ok", "keep") if bailian_family else key_state == "ok"
                if not _ok:
                    return {"ok": False, "code": "missing_key", "message": f"已切换到 {_new_vendor}，请先填它的 API Key"}, 200
            if ("brain" in patch or "keys" in patch) and key_state == "missing":
                need = "百炼" if bailian_family else _new_vendor
                return {"ok": False, "code": "missing_key", "message": f"选了 {need}，但没有填 API Key，不能保存"}, 200
            has_llm_key = bool(str(patch_brain.get("api_key") or "")) or bool(patch_keys.get("bailian"))
            merged = settings.merge_update(current, patch)
            changed = settings.diff(current, merged)
            if not changed:
                return {
                    "ok": True,
                    "changed": [],
                    "restart": {"gateway": False, "server": False},
                    "message": "没有改动",
                    "settings": settings.masked(current),
                }, 200
            backup = settings.save(merged)
            try:
                from app.panel.core import green as _g
                import threading as _th

                if _g.NODE.exists() and _g.SERVER_DIR.exists():
                    has_key = has_llm_key and network_ok
                    if has_key:
                        _th.Thread(target=_g.start, daemon=True).start()
                    return (
                        {
                            "ok": True,
                            "changed": changed,
                            "restart": {"gateway": False, "server": False},
                            "message": "已保存，正在启动服务" if has_key else "已保存，填好 Key 后自动启动",
                            "settings": settings.masked(merged),
                        },
                        200,
                    )
            except Exception:
                pass
            targets = settings.restart_targets(changed)
            return (
                {
                    "ok": True,
                    "changed": changed,
                    "restart": {
                        "gateway": targets["gateway"],
                        "server": targets["server"],
                    },
                    "eta": targets["eta"],
                    "notes": targets["notes"],
                    "backup": str(backup) if backup else "",
                    "settings": settings.masked(merged),
                },
                200,
            )

        if route == "/api/install/start":
            if not body.get("confirmed"):
                return {"ok": False, "message": "需要二次确认"}, 400
            job = get_install_job()
            if not job.start():
                return {"ok": False, "message": "已经在安装了，别重复点", **job.snapshot()}, 409
            return {"ok": True, **job.snapshot()}, 200

        if route == "/api/install/cancel":
            job = get_install_job()
            return {"ok": job.cancel(), **job.snapshot()}, 200

        if route in ("/api/service/start", "/api/service/restart"):
            conf = settings.load()
            debug = bool((conf.get("runtime") or {}).get("debug"))
            result = (
                services.start(debug=debug)
                if route == "/api/service/start"
                else services.restart(debug=debug)
            )
            return result, 200 if result.get("ok") else 409

        if route == "/api/service/stop":
            return services.stop(), 200

        if route == "/api/service/relocate":
            return services.relocate_ports(), 200

        if route == "/api/panel/shutdown":
            global _KEEP_SERVICES_ON_EXIT
            stop_services = bool(body.get("stop_services", False))
            _KEEP_SERVICES_ON_EXIT = not stop_services
            stopped = services.stop() if stop_services else None
            _schedule_shutdown()
            return {
                "ok": True,
                "stopped_services": stop_services,
                "message": "面板正在退出"
                + ("，机器狗服务也停了" if stop_services else "（机器狗服务继续跑）"),
                "services": stopped,
            }, 200

        if route == "/api/memory/clear":
            from app.gateway import memory

            device = (body.get("device") or "").strip() or None
            removed = memory.clear(device)
            return {"ok": True, "removed": removed}, 200

        if route == "/api/llm/models":
            return list_models(body)

        if route == "/api/voice/preview":
            return synthesize_preview(body)

        if route == "/api/net/firewall":
            conf = settings.load()
            ports = conf.get("ports") or {}
            result = firewall.allow_ports(
                [
                    int(ports.get("ota", 8003)),
                    int(ports.get("ws", 8005)),
                    int(ports.get("mqtt", 1883)),
                ]
            )
            return result, 200 if result.get("ok") else 400

        return {"ok": False, "message": f"没有这个接口：{route}"}, 404

    def _serve_preview(self, query: dict) -> None:
        name = (query.get("f") or [""])[0]
        base = (paths.DATA / "tmp").resolve()
        if not name or "/" in name or "\\" in name or ".." in name:
            self._send_bytes(b"404", "text/plain; charset=utf-8", 404)
            return
        target = (base / name).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            self._send_bytes(b"404", "text/plain; charset=utf-8", 404)
            return
        if not target.exists():
            self._send_bytes(b"404", "text/plain; charset=utf-8", 404)
            return
        self._send_bytes(target.read_bytes(), "audio/wav")

    def _serve_static(self, route: str) -> None:
        if route in ("", "/"):
            route = "/index.html"
        candidate = (paths.WEB / route.lstrip("/")).resolve()
        try:
            candidate.relative_to(paths.WEB.resolve())
        except ValueError:
            self._send_bytes("404", "text/plain; charset=utf-8", 404)
            return
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.exists():
            self._send_bytes("404 页面不存在", "text/plain; charset=utf-8", 404)
            return
        ctype, _ = mimetypes.guess_type(str(candidate))
        if candidate.suffix in (".html", ".css", ".js", ".json", ".svg"):
            ctype = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".svg": "image/svg+xml",
            }[candidate.suffix]
        self._send_bytes(candidate.read_bytes(), ctype or "application/octet-stream")


class PanelServer(ThreadingHTTPServer):
    # 关键：不要让两个面板实例同时绑同一个端口（Windows 的 SO_REUSEADDR 会允许，
    # 结果请求随机落到旧进程，出现"改完代码没生效/接口 500"这类灵异现象）。
    allow_reuse_address = False
    daemon_threads = True


def _already_running(host: str, port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
            return bool(data.get("ok"))
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    try:
        fixed = paths.make_writable()
        logger.info("已修复只读属性 %s 个", fixed)
    except Exception:
        pass
    paths.ensure_dirs()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(paths.LOGS / "panel.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    port = args.port or int(settings.load()["ports"].get("panel", 8770))
    try:
        httpd = PanelServer((args.host, port), Handler)
    except OSError:
        if _already_running(args.host, port):
            print(f"[panel] 面板已经在运行：http://{args.host}:{port}/")
            return 0
        print(f"[panel] 端口 {port} 被别的程序占用了，没法启动面板。")
        return 3

    url = f"http://127.0.0.1:{port}/"
    global _HTTPD
    _HTTPD = httpd
    print(f"[panel] {url}")
    logger.info("面板启动：%s（pid=%s）", url, os.getpid())

    def _autostart() -> None:
        time.sleep(1.5)
        try:
            conf = settings.load()
            if not (conf.get("runtime") or {}).get("autostart", True):
                return
            if not envprobe.report().get("installed"):
                return
            if services.status().get("any_running"):
                logger.info("服务已在运行，跳过自动启动")
                return
            started = services.start(bool((conf.get("runtime") or {}).get("debug")))
            logger.info("自动启动：%s", started.get("message") or started)
        except Exception:
            logger.exception("自动启动失败")

    threading.Thread(target=_autostart, name="autostart", daemon=True).start()

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        try:
            keep = _KEEP_SERVICES_ON_EXIT or bool(
                (settings.load().get("runtime") or {}).get("keep_running_on_panel_exit")
            )
            if not keep:
                services.stop()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
