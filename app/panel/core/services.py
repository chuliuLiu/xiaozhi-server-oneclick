"""进程托管：把网关和语音服务拉起来 / 停下去，并把失败翻译成人话。"""

from __future__ import annotations

import json
import secrets
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from app.common import paths
from app.panel.core import configsync, procs, settings
from app.panel.core import green

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010


# ------------------------------------------------------------------ 小工具


def ensure_token(conf: dict) -> tuple[dict, str]:
    token = ((conf.get("gateway") or {}).get("token") or "").strip()
    if token:
        return conf, token
    conf = json.loads(json.dumps(conf))
    conf.setdefault("gateway", {})["token"] = secrets.token_hex(16)
    settings.save(conf)
    return conf, conf["gateway"]["token"]


def ensure_auth_key(conf: dict) -> dict:
    key = ((conf.get("runtime") or {}).get("auth_key") or "").strip()
    if key:
        return conf
    conf = json.loads(json.dumps(conf))
    conf.setdefault("runtime", {})["auth_key"] = secrets.token_hex(16)
    settings.save(conf)
    return conf


def _port_block(ports: list[int]) -> list[int]:
    return [p for p in ports if not procs.port_free(p)]


def _spawn(name: str, args: list[str], cwd: Path, debug: bool, extra: dict | None = None):
    paths.ensure_dirs()
    log_path = paths.LOGS / f"{name}.console.log"
    log = open(log_path, "ab", buffering=0)
    log.write(
        f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} 启动 {name} =====\n".encode("utf-8")
    )
    flags = CREATE_NEW_CONSOLE if debug else CREATE_NO_WINDOW
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        env=paths.child_env(),
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=flags,
        close_fds=True,
    )
    procs.write_pid(name, proc.pid, extra or {})
    return proc, log




def _prepare_mqttgw(conf: dict, mqtt_port: int, ws_port: int) -> tuple[Path, Path]:
    """给官方 Node 网关写 config/mqtt.json 和 .env。"""
    import json as _json
    import socket as _socket

    gw = paths.PROJECT / "vendor" / "mqttgw"
    gw.mkdir(parents=True, exist_ok=True)
    (gw / "config").mkdir(exist_ok=True)
    try:
        s_ = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s_.connect(("223.5.5.5", 80))
        lan = s_.getsockname()[0]
        s_.close()
    except Exception:
        lan = "127.0.0.1"
    cfg = {
        "production": {"chat_servers": [f"ws://127.0.0.1:{int(ws_port)}"]},
        "development": {"chat_servers": [f"ws://127.0.0.1:{int(ws_port)}"], "mac_addresss": []},
        "debug": bool((conf.get("runtime") or {}).get("debug")),
        "max_mqtt_payload_size": 8192,
        "mcp_client": {
            "capabilities": {},
            "client_info": {"name": "xiaozhi-mqtt-client", "version": "1.0.0"},
            "max_tools_count": 128,
        },
    }
    (gw / "config" / "mqtt.json").write_text(
        _json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    key = str((conf.get("runtime") or {}).get("mqtt_signature_key") or "")
    env = {
        "MQTT_PORT": str(int(mqtt_port)),
        "UDP_PORT": str(int(mqtt_port)),
        "PUBLIC_IP": lan,
        "MQTT_SIGNATURE_KEY": key,
        "API_PORT": "18883",
    }
    (gw / ".env").write_text(
        "\n".join(f"{k}={v}" for k, v in env.items()) + "\n", encoding="utf-8"
    )
    return gw, paths.PROJECT / "runtime" / "node" / "node.exe"


def _gateway_ready(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def _tail(name: str, lines: int = 40) -> list[str]:
    rows: list[str] = []
    for candidate in (paths.LOGS / f"{name}.console.log", paths.LOGS / f"{name}.log"):
        if not candidate.exists():
            continue
        try:
            rows += candidate.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
        except Exception:
            pass
    return rows[-lines:] if rows else []


def diagnose(name: str) -> dict:
    """把最后几十行日志翻译成一句人话 + 一个动作。"""
    text = "\n".join(_tail(name, 80))
    low = text.lower()
    if "address already in use" in low or "eaddrinuse" in low or "10048" in text:
        return {
            "reason": "端口被别的程序占用了",
            "hint": "在「密钥参数 → 进阶」里换一个端口，或先关掉占用的程序",
        }
    if "modulenotfounderror" in low:
        module = ""
        for line in reversed(text.splitlines()):
            if "ModuleNotFoundError" in line:
                module = line.split("'")[1] if "'" in line else ""
                break
        return {
            "reason": "运行环境缺东西" + (f"（{module}）" if module else ""),
            "hint": "回「安装部署」点「重新安装依赖」",
        }
    if "scannererror" in low or "while parsing" in low or "yaml" in low and "error" in low:
        return {
            "reason": "配置文件写坏了",
            "hint": "点「保存」重新生成一次配置（会先备份）",
        }
    if "401" in text or "invalid api" in low or "unauthorized" in low:
        return {
            "reason": "API Key 不对",
            "hint": "去「密钥参数」重新填一次千问AI平台 API Key",
        }
    if "ffmpeg" in low:
        return {
            "reason": "音频组件没装好",
            "hint": "回「安装部署」重新安装依赖",
        }
    return {"reason": "", "hint": ""}


# ------------------------------------------------------------------ 启停

_start_lock = threading.Lock()



_last_mqtt_heal = 0.0


def ensure_mqtt_key(conf: dict) -> dict:
    runtime = conf.setdefault("runtime", {})
    key = str(runtime.get("mqtt_signature_key") or "").strip()
    if len(key) >= 8:
        return conf
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    key = "".join(secrets.choice(alphabet) for _ in range(24))
    runtime["mqtt_signature_key"] = key
    try:
        settings.save(conf)
    except Exception:
        pass
    return conf


def _heal_mqttgw() -> None:
    """MQTT 通道掉了就自动拉起来（每 30 秒最多一次）。"""
    global _last_mqtt_heal
    now = time.time()
    if now - _last_mqtt_heal < 30:
        return
    _last_mqtt_heal = now
    try:
        python = paths.python_for_children()
        if not python:
            return
        conf = settings.load()
        ports = conf.get("ports") or {}
        mqtt_port = int(ports.get("mqtt") or 1883)
        ws_port = int(ports.get("ws") or 8005)
        if procs.port_open("127.0.0.1", mqtt_port):
            return
        gw_dir, node_exe = _prepare_mqttgw(conf, mqtt_port, ws_port)
        _spawn(
            "mqttgw",
            [str(node_exe), "app.js"],
            gw_dir,
            bool((conf.get("runtime") or {}).get("debug")),
            {"port": mqtt_port},
        )
    except Exception:
        pass


def start(debug: bool = False) -> dict:
    """同一时间只允许一个启动流程（自动启动 + 手点按钮会撞车）。"""
    if not _start_lock.acquire(timeout=90):
        return {
            "ok": False,
            "code": "busy",
            "message": "上一次启动还没结束，等几秒再试",
        }
    try:
        return _start_locked(debug)
    finally:
        _start_lock.release()


def _start_locked(debug: bool = False) -> dict:
    if green.NODE.exists() and green.SERVER_DIR.exists():
        result = green.start()
        result.setdefault("message", "服务已启动")
        result.setdefault("started", ["server", "mqttgw"])
        return result
    conf = settings.load()
    python = paths.python_for_children()
    if not python or not paths.SERVER.exists():
        return {
            "ok": False,
            "code": "not_installed",
            "message": "还没装运行环境，先完成第 1 步",
        }

    conf = ensure_auth_key(conf)
    conf = ensure_mqtt_key(conf)
    conf, token = ensure_token(conf)
    ports = conf.get("ports") or {}
    gateway_port = int(ports.get("gateway") or 8771)
    ota_port = int(ports.get("ota") or 8003)
    ws_port = int(ports.get("ws") or 8005)
    mqtt_port = int(ports.get("mqtt") or 1883)
    mqtt_port = int(ports.get("mqtt") or 1883)

    # 先把自己上一轮的进程收掉，再判断端口（否则会把自己当占用者）
    stop_one("mqttgw", [mqtt_port])
    stop_one("gateway", [gateway_port])
    stop_one("server", [ota_port, ws_port])
    started: list[str] = []

    ok, payload = _ensure_ports(conf, gateway_port, ota_port, ws_port)
    if not ok:
        return payload
    conf, gateway_port, ota_port, ws_port, relocated = payload
    ports_changed = bool(relocated)

    sync = configsync.write(conf, gateway_port, token)
    if not sync.get("ok"):
        return {"ok": False, "code": "config", "message": sync.get("message", "配置写入失败")}

    gw_cmd = [str(python), "-u", str(paths.GATEWAY / "main.py"), "--port", str(gateway_port)]
    if debug:
        gw_cmd.append("--debug")
    _spawn("gateway", gw_cmd, paths.PROJECT, debug, {"port": gateway_port})
    if not _gateway_ready(gateway_port, 12):
        info = diagnose("gateway")
        stop_one("gateway", [gateway_port])
        return {
            "ok": False,
            "code": "gateway_failed",
            "message": "大脑网关没起来" + (f"：{info['reason']}" if info["reason"] else ""),
            "hint": info.get("hint", ""),
        }
    started.append("gateway")

    # MQTT + UDP 通道（设备按官方 mqtt+udp 方案连接）
    gw_dir, node_exe = _prepare_mqttgw(conf, mqtt_port, ws_port)
    mq_cmd = [str(node_exe), "app.js"]
    _spawn("mqttgw", mq_cmd, gw_dir, debug, {"port": mqtt_port})
    if not _wait_port(mqtt_port, 8.0):
        tail = _tail("mqttgw", 20)
        return {
            "ok": False,
            "code": "mqtt_failed",
            "message": "MQTT 通道没起来",
            "hint": _diagnose_line(tail) or "看下面日志",
            "log": tail[-20:],
        }
    started.append("mqttgw")

    srv_cmd = [str(python), "-u", "app.py"]
    _spawn("server", srv_cmd, paths.SERVER, debug, {"ports": [ota_port, ws_port]})
    started.append("server")

    # 等一小会儿：进程若立刻退出，把日志尾巴直接带回去，别让页面永远转圈
    if not _wait_server_ready([ota_port, ws_port], timeout=12.0):
        if not procs.read_pid("server"):
            tail = _tail("server", 40)
            return {
                "ok": False,
                "code": "server_failed",
                "message": "语音服务启动后立刻退出了",
                "hint": _diagnose_line(tail)
                or "看下面日志；也可以回「安装部署」重装一次依赖",
                "log": tail[-20:],
            }

    message = "大脑网关已就绪，语音服务正在启动（约 30 秒）"
    if ports_changed:
        message = (
            f"端口被系统保留，已自动改用 OTA {ota_port} / WS {ws_port}；"
            "请重新复制 OTA 地址填到机器狗里。"
        )
    return {
        "ok": True,
        "started": started,
        "gateway_port": gateway_port,
        "ota_port": ota_port,
        "ws_port": ws_port,
        "ports_changed": ports_changed,
        "ports": {"gateway": gateway_port, "ota": ota_port, "ws": ws_port},
        "message": message,
        "config": sync,
    }


def _wait_port(port: int, timeout: float = 8.0) -> bool:
    import time as _t

    deadline = _t.time() + timeout
    while _t.time() < deadline:
        if procs.port_open("127.0.0.1", int(port)):
            return True
        _t.sleep(0.3)
    return False


def _wait_server_ready(ports: list[int], timeout: float = 12.0) -> bool:
    """等语音服务真正开始监听；进程中途退出会提前返回 False。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(procs.port_open("127.0.0.1", int(p)) for p in ports):
            return True
        if not procs.read_pid("server"):
            return False
        time.sleep(0.5)
    return False


def _diagnose_line(lines: list[str]) -> str:
    text = "\n".join(lines).lower()
    if "modulenotfounderror" in text or "importerror" in text:
        return "运行环境缺包：回「安装部署」点重新安装依赖"
    if "address already in use" in text or "10048" in text:
        return "端口被占用了：点「诊断端口」看看是谁"
    if "scannererror" in text or "yaml" in text:
        return "服务端配置坏了：回「密钥参数」保存一次会重新生成"
    if "401" in text or "unauthorized" in text:
        return "Key 不对：去「密钥参数」重新填一次"
    if "ffmpeg" in text:
        return "音频组件异常：回「安装部署」重装依赖"
    return ""


def _ensure_ports(
    conf: dict, gateway_port: int, ota_port: int, ws_port: int
) -> tuple[bool, object]:
    """确认三个端口真的能用。

    - 有人监听：报错，并把"是谁"带回去（不硬抢别人的端口）；
    - 没人监听但绑不上（Hyper-V/WSL 保留段、安全软件）：自动换到下一个空闲端口。
    """
    diag = {p: procs.port_diagnose(p) for p in (gateway_port, ota_port, ws_port)}
    blocked = {p: d for p, d in diag.items() if d["verdict"] != "free"}
    if not blocked:
        return True, (conf, gateway_port, ota_port, ws_port, {})

    listeners = []
    for port, info in blocked.items():
        for item in info["listeners"]:
            listeners.append({"port": port, **item})
    if listeners:
        detail = "，".join(
            f"{item['port']} 被 {item['name'] or '未知程序'}(pid {item['pid']}) 占用"
            for item in listeners
        )
        suggest = {
            "ota": procs.find_free_port(ota_port + 1) if not diag[ota_port]["free"] else ota_port,
            "ws": procs.find_free_port(ws_port + 1) if not diag[ws_port]["free"] else ws_port,
            "gateway": procs.find_free_port(gateway_port + 1)
            if not diag[gateway_port]["free"]
            else gateway_port,
        }
        return False, {
            "ok": False,
            "code": "port_occupied",
            "message": f"端口被别的程序占用了：{detail}",
            "hint": "关掉占用端口的程序，或点「换端口并启动」自动换",
            "ports": blocked,
            "suggest": suggest,
        }

    relocated = {}
    new_gateway, new_ota, new_ws = gateway_port, ota_port, ws_port
    if not diag[gateway_port]["free"]:
        new_gateway = procs.find_free_port(gateway_port + 1)
        relocated["gateway"] = {"from": gateway_port, "to": new_gateway}
    if not diag[ota_port]["free"]:
        new_ota = procs.find_free_port(ota_port + 1)
        relocated["ota"] = {"from": ota_port, "to": new_ota}
    if not diag[ws_port]["free"]:
        new_ws = procs.find_free_port(ws_port + 1)
        relocated["ws"] = {"from": ws_port, "to": new_ws}

    conf.setdefault("ports", {}).update(
        {"gateway": new_gateway, "ota": new_ota, "ws": new_ws}
    )
    settings.save(conf)
    return True, (conf, new_gateway, new_ota, new_ws, relocated)


def relocate_ports() -> dict:
    """手动换端口：只挪「真的不能用」的那几个，其余保持不动。"""
    conf = settings.load()
    ports = conf.get("ports") or {}
    result = {}
    for name, default in (("ota", 8003), ("ws", 8005), ("gateway", 8771)):
        current = int(ports.get(name) or default)
        if procs.port_diagnose(current)["free"]:
            result[name] = current
            continue
        result[name] = procs.find_free_port(current + 1)
    conf.setdefault("ports", {}).update(result)
    settings.save(conf)
    sync = configsync.write(conf, result["gateway"], (conf.get("gateway") or {}).get("token") or "")
    return {
        "ok": bool(sync.get("ok")),
        "ports": result,
        "message": (
            f"已改用 OTA {result['ota']} / WS {result['ws']} / 网关 {result['gateway']}，"
            "请重新复制 OTA 地址"
        ),
    }


def _wait_ports_free(ports: list[int], timeout: float = 6.0) -> list[int]:
    deadline = time.time() + timeout
    remaining = list(ports)
    while time.time() < deadline:
        remaining = [p for p in ports if procs.listener_pid(p) or procs.port_open("127.0.0.1", p)]
        if not remaining:
            return []
        time.sleep(0.25)
    return remaining


def stop_one(name: str, ports: list[int] | None = None) -> bool:
    stopped = False
    info = procs.read_pid(name)
    if info:
        procs.kill_pid(info["pid"])
        for _ in range(30):
            if not procs.pid_alive(int(info["pid"])):
                break
            time.sleep(0.1)
        stopped = True
    marker = str(paths.GATEWAY) if name == "gateway" else str(paths.SERVER)
    port_list = [int(p) for p in (ports or [])]
    for port in port_list:
        if procs.listener_pid(port) or procs.port_open("127.0.0.1", port):
            stopped = procs.kill_by_port(port, marker) or stopped
    # 给 Windows 一点时间真正释放监听（TIME_WAIT 不影响 LISTENING，但杀进程是异步的）
    _wait_ports_free(port_list, 6.0)
    procs.clear_pid(name)
    return stopped


def stop() -> dict:
    if green.NODE.exists() and green.SERVER_DIR.exists():
        return green.stop()
    conf = settings.load()
    ports = conf.get("ports") or {}
    server_ports = [int(ports.get("ota") or 8003), int(ports.get("ws") or 8005)]
    gateway_ports = [int(ports.get("gateway") or 8771)]
    mqtt_ports = [int(ports.get("mqtt") or 1883)]
    all_ports = server_ports + gateway_ports + mqtt_ports
    stopped = []
    for name, plist in (
        ("server", server_ports),
        ("gateway", gateway_ports),
        ("mqttgw", mqtt_ports),
    ):
        try:
            if stop_one(name, plist):
                stopped.append(name)
        except Exception:
            pass

    # 只把「还属于本项目」的端口算失败；别人占着的端口只是提示
    root_text = str(paths.PROJECT).lower()
    ours = []
    foreign = []
    for port in all_ports:
        pid = procs.listener_pid(port)
        if not pid:
            continue
        try:
            exe = (procs.exe_path(pid) or "").lower()
        except Exception:
            exe = ""
        if root_text in exe:
            ours.append(port)
        else:
            foreign.append(port)

    if ours:
        # 再试一次强杀（有些进程对 pid 文件不敏感）
        for port in list(ours):
            try:
                procs.kill_by_port(port, str(paths.PROJECT))
            except Exception:
                pass
        ours = [p for p in ours if procs.listener_pid(p)]

    result = {
        "ok": not ours,
        "stopped": stopped,
        "message": "已停止" if stopped else "本来就没在跑",
    }
    if ours:
        result["message"] = f"本项目还有端口没释放：{', '.join(map(str, ours))}（权限不足？）"
        result["ports"] = ours
    if foreign:
        result["foreign"] = foreign
        result["message"] += f"；另有别的程序占着 {', '.join(map(str, foreign))}，和本程序无关"
    return result


def restart(debug: bool = False) -> dict:
    result = stop()
    if not result.get("ok"):
        return {
            "ok": False,
            "code": "port_busy",
            "message": result.get("message") or "端口没释放，重启失败",
            "hint": "关掉占用端口的程序，或在「密钥参数 → 进阶」里换一个端口",
        }
    time.sleep(0.4)
    return start(debug)


def _device_state(ws_port: int, server_pid: int | None = None) -> dict:
    """设备在线探测：数一下 ws 端口上的 ESTABLISHED 连接，并记住最近一次时间。

    兜底：配置里的 ws 端口和实际监听端口不一致时（比如服务端还是旧配置），
    用服务端进程实际监听的端口再数一遍，避免"狗在聊天但面板看不到"。
    """
    remotes = procs.established_remotes(ws_port)
    if not remotes:
        # MQTT 模式下设备连的是 1883（WS 是网关回环连接，不算设备）
        mqtt_port = int((settings.load().get("ports") or {}).get("mqtt") or 1883)
        if mqtt_port != ws_port:
            remotes = procs.established_remotes(mqtt_port)
    if not remotes and server_pid:
        for port in procs.listener_ports_of_pid(server_pid):
            if port == ws_port:
                continue
            found = procs.established_remotes(port)
            if found:
                remotes = found
                break
    state_file = paths.RUN / "device.json"
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    last_seen = float(state.get("last_seen") or 0)
    if remotes:
        last_seen = time.time()
        try:
            state_file.write_text(
                json.dumps({"ips": remotes, "last_seen": last_seen}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass
    return {
        "count": len(remotes),
        "ips": remotes,
        "last_seen": last_seen or None,
        "recently": bool(last_seen and time.time() - last_seen < 120),
    }




def _green_status() -> dict:
    conf = settings.load()
    ports = conf.get("ports") or {}
    try:
        import json as _json
        _p = paths.RUN / "green_ports.json"
        if _p.exists():
            ports = _json.loads(_p.read_text(encoding="utf-8")).get("ports") or ports
    except Exception:
        pass
    ws = int(ports.get("ws") or 8000)
    ota = int(ports.get("ota") or 8003)
    mqtt = int(ports.get("mqtt") or 1883)
    panel = int(ports.get("panel") or 8770)

    def one(name: str, plist: list[int]) -> dict:
        info = procs.read_pid(name)
        listening = any(procs.port_open("127.0.0.1", p) for p in plist)
        state = "running" if info else "port_busy" if listening else "stopped"
        return {
            "running": bool(info),
            "listening": listening,
            "state": state,
            "managed": bool(info),
            "pid": (info or {}).get("pid"),
            "ports": plist,
            "uptime": 0,
        }

    server = one("green_server", [ws, ota])
    mqttgw = one("green_mqtt", [mqtt])
    gateway = {"running": False, "listening": False, "state": "stopped", "managed": False, "ports": []}
    return {
        "ok": True,
        "gateway": gateway,
        "server": server,
        "mqttgw": mqttgw,
        "any_running": server["running"] or mqttgw["running"],
        "debug": False,
        "device": _device_state(mqtt, None),
        "green": True,
    }


def status() -> dict:
    if green.NODE.exists() and green.SERVER_DIR.exists():
        return _green_status()
    conf = settings.load()
    ports = conf.get("ports") or {}
    gateway_port = int(ports.get("gateway") or 8771)
    ota_port = int(ports.get("ota") or 8003)
    ws_port = int(ports.get("ws") or 8005)
    mqtt_port = int(ports.get("mqtt") or 1883)

    def one(name: str, port_list: list[int]) -> dict:
        info = procs.read_pid(name)
        listening = any(procs.port_open("127.0.0.1", p) for p in port_list)
        if info:
            state = "running" if listening else "starting"
        elif listening:
            state = "port_busy"  # 端口有东西，但不是我们托管的：多半是上次没关干净
        else:
            state = "stopped"
        running = bool(info)
        uptime = 0
        if info and info.get("started_at"):
            uptime = max(0, int(time.time() - float(info.get("started_at") or 0)))
        result = {
            "running": running,
            "listening": listening,
            "state": state,
            "managed": bool(info),
            "pid": (info or {}).get("pid"),
            "ports": port_list,
            "uptime": uptime,
            "started_at": (info or {}).get("started_at"),
        }
        if state == "port_busy":
            result["note"] = "端口被占用，可能上次没关干净；点「停止」可以清理"
        if state == "starting" and uptime > 90:
            state = "stalled"
            result["state"] = state
            result["note"] = "启动超过 90 秒还没监听端口，看看下面的日志"
            result["diagnose"] = diagnose(name)
            result["last_log"] = _tail(name, 20)
        if not running:
            last = _tail(name, 6)
            if last:
                result["last_log"] = last
                result["diagnose"] = diagnose(name)
        return result

    gateway = one("gateway", [gateway_port])
    server = one("server", [ws_port, ota_port])
    mqttgw = one("mqttgw", [mqtt_port])
    if server.get("running") and not mqttgw.get("running"):
        _heal_mqttgw()
        mqttgw = one("mqttgw", [mqtt_port])
    return {
        "ok": True,
        "gateway": gateway,
        "server": server,
        "mqttgw": mqttgw,
        "any_running": gateway["running"] or server["running"] or mqttgw["running"],
        "debug": bool((conf.get("runtime") or {}).get("debug")),
        "device": _device_state(ws_port, server.get("pid")),
    }
