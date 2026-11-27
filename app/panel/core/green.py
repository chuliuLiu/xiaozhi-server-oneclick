"""绿色版核心：0.9.8 原版服务端 + 官方 mqtt-gateway 的配置生成与进程托管。

这里不碰 app/gateway（自研 LLM 网关闭），服务端目录由 paths.SERVER 统一提供。
"""

from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import time
from pathlib import Path

from app.common import paths
from app.panel.core import procs, settings

SERVER_DIR = paths.SERVER
GW_DIR = paths.RUNTIME / "xiaozhi-mqtt-gateway"
NODE = paths.RUNTIME / "node" / "node.exe"
CREATE_NO_WINDOW = 0x08000000


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"




def _clear_readonly(target: Path) -> None:
    """去掉解压后常见的只读属性（不弹 UAC，只改本目录）。"""
    import os
    import stat

    roots = [target]
    if target.is_dir():
        try:
            roots += list(target.rglob("*"))
        except Exception:
            pass
    for item in roots:
        try:
            mode = os.stat(item).st_mode
            os.chmod(item, mode | stat.S_IWRITE)
        except Exception:
            pass



def _udp_or_next(port: int, used: set | None = None) -> int:
    """UDP 端口要单独检测：TCP 空闲不代表 UDP 能 bind。"""
    used = used or set()
    p = int(port)
    for _ in range(50):
        if p not in used:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
                except OSError:
                    pass
                sock.bind(("0.0.0.0", p))
                return p
            except OSError:
                pass
            finally:
                if sock is not None:
                    sock.close()
        p += 1
    return int(port)


def _free_or_next(port: int, used: set | None = None) -> int:
    used = used or set()
    p = int(port)
    for _ in range(50):
        if p not in used and procs.port_free(p):
            return p
        p += 1
    return int(port)


def _yaml_quote(v: str) -> str:
    return '"' + str(v).replace('\\', '\\\\').replace('"', '\\"') + '"'


def server_yaml(conf: dict, ports: dict, ip: str) -> str:
    key = settings.bailian_key(conf)
    brain = conf.get("brain") or {}
    voice = conf.get("voice") or {}
    asr = conf.get("asr") or {}
    persona = conf.get("persona") or {}
    llm_model = brain.get("model") or "deepseek-v4.1-flash-1017"
    base_url = brain.get("base_url") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ws, ota, mqtt = ports["ws"], ports["ota"], ports["mqtt"]
    import tempfile
    # 用已存在的系统临时目录，不再新建子目录（新建目录在只读/安全软件环境下会被拒）
    log_dir = str(paths.LOGS).replace("\\", "/")
    log_file = "xiaozhi-server098.log"
    return f"""selected_module:
  VAD: SileroVAD
  ASR: AliyunBLStreamASR
  LLM: AliLLM
  TTS: AliBLTTS
  Memory: nomem
  Intent: function_call
log:
  log_level: INFO
  log_dir: "."
  log_file: "NUL"
server:
  ip: 0.0.0.0
  port: {ws}
  http_port: {ota}
  auth:
    enabled: false
  mqtt_gateway: {_yaml_quote(f"{ip}:{mqtt}")}
  mqtt_signature_key: {_yaml_quote(str((conf.get('runtime') or {}).get('mqtt_signature_key') or ''))}
  udp_gateway: null
ASR:
  AliyunBLStreamASR:
    type: aliyunbl_stream
    api_key: {_yaml_quote(key)}
    model: {_yaml_quote(asr.get('model') or 'fun-asr-realtime')}
    output_dir: tmp/
TTS:
  AliBLTTS:
    type: alibl_stream
    api_key: {_yaml_quote(key)}
    ws_url: wss://dashscope.aliyuncs.com/api-ws/v1/inference/
    model: {_yaml_quote(voice.get('tts_model') or 'qwen-audio-3.1-tts-flash')}
    voice: {_yaml_quote(voice.get('voice_id') or 'longanhuan_v3.1')}
    output_dir: tmp/
LLM:
  AliLLM:
    type: openai
    base_url: {_yaml_quote(base_url)}
    model_name: {_yaml_quote(llm_model)}
    api_key: {_yaml_quote(brain.get('api_key') or key)}
    temperature: 0.7
    max_tokens: 300
prompt: {_yaml_quote((persona.get('prompt') or '你是一只机器狗，回答简短口语化。')[:4000])}
"""


def gateway_files(conf: dict, ports: dict, ip: str) -> None:
    cfg = {
        "production": {"chat_servers": [f"ws://127.0.0.1:{ports['ws']}?from=mqtt_gateway"]},
        "development": {
            "chat_servers": [f"ws://127.0.0.1:{ports['ws']}?from=mqtt_gateway"],
            "mac_addresss": [],
        },
        "debug": False,
        "max_mqtt_payload_size": 8192,
        "mcp_client": {
            "capabilities": {},
            "client_info": {"name": "xiaozhi-mqtt-client", "version": "1.0.0"},
            "max_tools_count": 128,
        },
    }
    (GW_DIR / "config").mkdir(parents=True, exist_ok=True)
    (GW_DIR / "config" / "mqtt.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    env = {
        "MQTT_PORT": str(ports["mqtt"]),
        "UDP_PORT": str(ports["udp"]),
        "PUBLIC_IP": ip,
        "MQTT_SIGNATURE_KEY": str((conf.get("runtime") or {}).get("mqtt_signature_key") or ""),
        "API_PORT": str(ports["mqtt"] + 10000),
    }
    (GW_DIR / ".env").write_text(
        "\n".join(f"{k}={v}" for k, v in env.items()) + "\n", encoding="utf-8"
    )


def _spawn(name: str, args: list[str], cwd: Path, env: dict) -> int:
    log_path = paths.LOGS / f"{name}.console.log"
    try:
        if log_path.exists() and log_path.stat().st_size > 5 * 1024 * 1024:
            backup = log_path.with_suffix(log_path.suffix + ".1")
            if backup.exists():
                backup.unlink()
            log_path.rename(backup)
    except Exception:
        pass
    log = open(log_path, "ab", buffering=0)
    log.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} {name} =====\n".encode())
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
    )
    procs.write_pid(name, proc.pid, {})
    return proc.pid


def start() -> dict:
  try:
    return _start()
  except Exception as exc:  # noqa: BLE001
    import traceback

    try:
        (paths.LOGS / "green_start_error.log").write_text(traceback.format_exc(), encoding="utf-8")
    except Exception:
        pass
    return {"ok": False, "message": f"启动失败：{exc}", "code": "green_failed"}


def _start() -> dict:
    stop()
    conf = settings.load()
    ports = conf.setdefault("ports", {})
    runtime = conf.setdefault("runtime", {})
    if not runtime.get("mqtt_signature_key"):
        import secrets
        import string

        runtime["mqtt_signature_key"] = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(24)
        )
    pools = {}
    used = set()
    for name, default in (
        ("ws", 8000),
        ("ota", 8003),
        ("mqtt", 1883),
        ("udp", 8884),
    ):
        if name == "udp":
            pools[name] = _udp_or_next(int(ports.get(name) or default), used)
        else:
            pools[name] = _free_or_next(int(ports.get(name) or default), used)
        used.add(pools[name])
    ports.update(pools)
    ip = lan_ip()
    try:
        paths.RUN.mkdir(parents=True, exist_ok=True)
        (paths.RUN / "green_ports.json").write_text(__import__("json").dumps({"ports": pools, "ip": ip}), encoding="utf-8")
    except Exception:
        pass
    for target in (paths.DATA, SERVER_DIR / "data", SERVER_DIR / "tmp"):
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        _clear_readonly(target)
    settings.save(conf)

    python = paths.python_for_children()
    if not python or not NODE.exists():
        return {"ok": False, "message": "缺少 Python 依赖或 Node 运行时"}

    (SERVER_DIR / "data").mkdir(parents=True, exist_ok=True)
    # 父进程先建好日志文件并去掉只读，子进程只做 append
    try:
        paths.LOGS.mkdir(parents=True, exist_ok=True)
        lp = paths.LOGS / "xiaozhi-server098.log"
        with open(lp, "a", encoding="utf-8"):
            pass
        import os as _os, stat as _stat
        _os.chmod(lp, _os.stat(lp).st_mode | _stat.S_IWRITE)
    except Exception:
        pass
    (SERVER_DIR / "data" / ".config.yaml").write_text(
        server_yaml(conf, pools, ip), encoding="utf-8"
    )
    gateway_files(conf, pools, ip)

    env = paths.child_env()
    try:
        (paths.DATA / "tmp").mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    env["TMP"] = env["TEMP"] = str(paths.DATA / "tmp")
    _spawn("green_mqtt", [str(NODE), "app.js"], GW_DIR, env)
    time.sleep(1.5)
    pid = procs.listener_pid(pools["mqtt"])
    if pid:
        procs.write_pid("green_mqtt", pid, {})
    _spawn("green_server", [str(python), "-u", "app.py"], SERVER_DIR, env)

    deadline = time.time() + 20
    while time.time() < deadline:
        if procs.port_open("127.0.0.1", pools["ws"]) and procs.port_open(
            "127.0.0.1", pools["ota"]
        ):
            break
        time.sleep(0.5)
    alive = procs.read_pid("green_server") or procs.read_pid("green_mqtt")
    return {
        "ok": bool(alive) or procs.port_open("127.0.0.1", pools["ws"]),
        "starting": not procs.port_open("127.0.0.1", pools["ws"]),
        "message": ("语音服务正在启动，面板会自动刷新" if alive and not procs.port_open("127.0.0.1", pools["ws"]) else "服务已启动"),
        "ports": pools,
        "ip": ip,
        "ota": f"http://{ip}:{pools['ota']}/xiaozhi/ota/",
    }


def stop() -> dict:
    out = {}
    for name in ("green_server", "green_mqtt"):
        info = procs.read_pid(name)
        if info:
            try:
                procs.kill_pid(int(info["pid"]))
            except Exception:
                pass
            procs.clear_pid(name)
            out[name] = True
    conf = settings.load()
    ports = conf.get("ports") or {}
    for key, default in (("ws", 8000), ("ota", 8003), ("mqtt", 1883)):
        port = int(ports.get(key) or default)
        if procs.listener_pid(port):
            try:
                procs.kill_by_port(port, str(paths.PROJECT))
            except Exception:
                pass
        if not procs.listener_pid(port):
            out[f"port{port}"] = True
    return {"ok": True, **out}
