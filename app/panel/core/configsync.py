"""settings.json → runtime/xiaozhi-server/data/.config.yaml

只写「覆盖项」，上游的 config.yaml 一个字节都不改。
写之前备份、写完立刻校验；校验失败就回滚，绝不留下半成品（踩过这个坑）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from app.common import paths
from app.panel.core import settings


# ------------------------------------------------------------------ YAML 序列化


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    # JSON 字符串转义是 YAML 双引号风格的子集，安全
    return json.dumps(str(value), ensure_ascii=False)


def _dump(obj: Any, indent: int = 0) -> str:
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                lines.append(f"{pad}{key}:")
                lines.append(_dump(value, indent + 1))
            elif isinstance(value, list):
                if not value:
                    lines.append(f"{pad}{key}: []")
                    continue
                lines.append(f"{pad}{key}:")
                for item in value:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{pad}  -")
                        lines.append(_dump(item, indent + 2))
                    else:
                        lines.append(f"{pad}  - {_scalar(item)}")
            else:
                lines.append(f"{pad}{key}: {_scalar(value)}")
    elif isinstance(obj, list):
        for item in obj:
            lines.append(f"{pad}- {_scalar(item)}")
    return "\n".join(lines)


# ------------------------------------------------------------------ 生成配置


def build(conf: dict[str, Any], gateway_port: int, token: str, log_dir: Path) -> dict:
    voice = conf.get("voice") or {}
    asr = conf.get("asr") or {}
    brain = conf.get("brain") or {}
    persona = conf.get("persona") or {}
    ports = conf.get("ports") or {}
    keys = conf.get("keys") or {}
    runtime = conf.get("runtime") or {}

    bailian_key = settings.bailian_key(conf)

    asr_model = asr.get("model") or "fun-asr-realtime"
    if asr_model == "qwen3-asr-flash":
        selected_asr = "Qwen3ASRFlash"
    else:
        selected_asr = "AliyunBLStreamASR"

    tts_model = voice.get("tts_model") or "cosyvoice-v3-flash"
    default_voice = "longxiaochun_v2" if tts_model.startswith("cosyvoice-v2") else "longanyang"
    voice_id = (voice.get("voice_id") or default_voice).strip()

    ws_port = int(ports.get("ws") or 8005)
    ota_port = int(ports.get("ota") or 8003)

    data: dict[str, Any] = {
        "server": {
            "ip": "0.0.0.0",
            "port": ws_port,
            "http_port": ota_port,
            "auth_key": runtime.get("auth_key") or "",
            # MQTT+UDP 通道（本机 mqtt 网关进程）；这几个键属于 server 段
            "mqtt_gateway": f"{_lan_ip()}:{int(ports.get('mqtt') or 1883)}",
            "mqtt_signature_key": str(runtime.get("mqtt_signature_key") or ""),
            "udp_gateway": None,
        },
        "selected_module": {
            "VAD": "SileroVAD",
            "ASR": selected_asr,
            "TTS": "AliBLTTS",
            "LLM": "LocalGatewayLLM",
            "VLLM": "ChatGLMVLLM",
            "Memory": "nomem",
            "Intent": "function_call",
        },
        "ASR": {
            "AliyunBLStreamASR": {
                "type": "aliyunbl_stream",
                "api_key": bailian_key,
                "model": asr_model,
                "format": "pcm",
                "sample_rate": 16000,
                "max_sentence_silence": 200,
                "punctuation_prediction_enabled": True,
                "inverse_text_normalization_enabled": True,
                "output_dir": "tmp/",
            },
            "Qwen3ASRFlash": {
                "type": "qwen3_asr_flash",
                "api_key": bailian_key,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model_name": "qwen3-asr-flash",
                "output_dir": "tmp/",
                "enable_lid": True,
                "enable_itn": True,
            },
        },
        "TTS": {
            "AliBLTTS": {
                "type": "alibl_stream",
                "api_key": bailian_key,
                "model": tts_model,
                "voice": voice_id,
                "format": "pcm",
                "rate": float(voice.get("speed") or 1.0),
                "volume": int(voice.get("volume") or 50),
                "output_dir": "tmp/",
            }
        },
        "LLM": {
            "LocalGatewayLLM": {
                "type": "openai",
                "base_url": f"http://127.0.0.1:{gateway_port}/v1",
                "model_name": "xiaozhi-local",
                "api_key": token or "xiaozhi-local",
                "max_tokens": int(brain.get("max_tokens") or 300),
                "temperature": float(brain.get("temperature") or 0.7),
                "timeout": {"connect": 5, "read": 60, "write": 10, "pool": 2},
            }
        },
        "prompt": persona.get("prompt") or "",
        "wakeup_words": persona.get("wakeup_words") or ["小兵小兵"],
        "exit_commands": ["退下", "退下吧", "退出", "关闭"],
        "log": {
            "log_level": "INFO",
            "log_dir": os.path.relpath(
                Path(log_dir).resolve(), paths.SERVER.resolve()
            ).replace("\\", "/"),
            "log_file": "server.log",
        },
        "enable_greeting": True,
        # 唤醒问候别用旧音频缓存：换了音色/模型后缓存里还是老声音
        "enable_wakeup_words_response_cache": False,
        # 静默 5 分钟才断开（默认 120 秒太短，用户会觉得"狗自己断线了"）
        "close_connection_no_voice_time": 30,
        # 关掉"结束对话时让模型再说一段告别"：这句会被当成用户消息重放，
        # 表现为退出时重复道别、断线重连后又说一遍（0.3.9 起关闭）
        "end_prompt": {"enable": False},
    }
    return data



def _lan_ip() -> str:
    import socket as _socket

    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def target_path() -> Path:
    return paths.SERVER / "data" / ".config.yaml"


def write(conf: dict[str, Any], gateway_port: int, token: str) -> dict:
    """生成并写入；返回 {ok, path, backup, message}。"""
    if not paths.SERVER.exists():
        return {"ok": False, "message": "服务端还没安装，先完成安装"}
    target = target_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    backup = None
    if target.exists():
        backup = paths.BACKUPS / (
            "server-config-" + time.strftime("%Y%m%d-%H%M%S") + ".yaml"
        )
        paths.BACKUPS.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)

    text = _dump(build(conf, gateway_port, token, paths.LOGS)) + "\n"
    tmp = target.with_suffix(".yaml.tmp")
    tmp.write_text(text, encoding="utf-8")

    ok, detail = validate(tmp)
    if ok is None:  # 没法校验（环境还没装好）：先接受，装好后会再校验
        tmp.replace(target)
        return {"ok": True, "path": str(target), "backup": str(backup or ""), "message": "已写入（未校验）"}
    if not ok:
        tmp.unlink(missing_ok=True)
        if backup and backup.exists():
            shutil.copy2(backup, target)
        return {
            "ok": False,
            "message": f"生成的配置不是合法 YAML，已回滚。{detail}",
            "path": str(target),
        }
    tmp.replace(target)
    return {"ok": True, "path": str(target), "backup": str(backup or ""), "message": "已写入并校验通过"}


def validate(path: Path) -> tuple[bool | None, str]:
    """用随包 Python 校验；解释器/库还没装好时返回 (None, '')。"""
    python = paths.python_for_children()
    if not python:
        return None, ""
    code = (
        "import sys\n"
        "p=sys.argv[1]\n"
        "try:\n"
        "    from ruamel.yaml import YAML\n"
        "    YAML().load(open(p,encoding='utf-8-sig'))\n"
        "except ImportError:\n"
        "    import yaml; yaml.safe_load(open(p,encoding='utf-8-sig'))\n"
        "print('ok')\n"
    )
    try:
        proc = subprocess.run(
            [str(python), "-c", code, str(path)],
            capture_output=True,
            text=True,
            timeout=20,
            env=paths.child_env(),
            creationflags=0x08000000,
        )
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    if proc.returncode == 0 and "ok" in (proc.stdout or ""):
        return True, ""
    if "ModuleNotFoundError" in (proc.stderr or ""):
        return None, ""
    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    return False, (detail[-1] if detail else "未知错误")
