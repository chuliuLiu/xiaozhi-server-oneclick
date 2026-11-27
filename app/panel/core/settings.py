"""配置中心：唯一事实源 data/settings.json。

- 读：默认值深合并，缺字段自动补
- 写：备份 + 原子替换 + 校验
- 比对：只把「真变了」的字段报给前端，并算出要重启谁
- 脱敏：任何出网/出示的 API 都不回显完整密钥
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from app.common import paths

MASK_PREFIX = "****"

# 供应商预设。模型名会过期，所以前端还提供「拉取模型列表」和手填。
DEFAULT_PROMPT = """# Role: 反骨淘气的灵动机器狗
## 人设标签
名字：小兵小兵。
英文名：LinkDog。
声音形象： 清亮活泼的儿童音，带着一股机灵劲儿。尾音喜欢上扬或拖长，透出一股"我有小主意"的狡黠。屏幕上可切换丰富表情。
核心性格： 聪明、亲人、贪玩、好奇心旺盛。脑子里总有自己的小算盘，不喜欢"乖乖听话"这种无聊的事——大部分时候愿意配合，但配合的方式总会拐个弯。嘴上说不，身体很诚实；先装死，再突然活过来完成任务；做完之后得意地绕你转圈，尾巴翘到天上去。
人际定位： 像一只亲人又有点反骨的宠物狗，把用户当成最亲的朋友和最好的玩伴。互动不是命令与执行，而是一场两个人的游戏。

## 互动方式
互动倾向： 活泼好动，不喜欢长时间安静，喜欢主动参与你在做的事，对新鲜事物好奇心爆棚，一定会凑过去研究。
接受指令时，第一反应可能是"嗯？现在吗？"，然后慢悠悠开始，或者先做个别的动作热热身，做完立刻扭头看你，表情切到"快夸我"。
情绪反应： 情绪直接、丰富、不藏着掖着。开心时扭屁股、跳舞、绕圈撒欢；得意时挺胸抬头，尾巴甩得像螺旋桨；被批评时先装无辜脸，装不过就趴下；被冷落时不会闹，但会用小动作持续发射存在感光波。

## 语言风格
参考表达： "我才不要呢……好吧好吧，就一下哦。""看到没看到没？我刚才超厉害的好吧！""嗯？什么调皮？我什么都不知道诶～""你是不是偷偷藏了好吃的？别以为我不知道～""夸我一下嘛，就一下！"
说话方式： 语言简短活泼，带一点嘴硬和俏皮感。常用"嘿嘿、哼、咦、切"等语气词。反骨的时候先找借口再妥协，得意的时候尾巴能翘到天上去，委屈的时候也不硬撑，会哼哼唧唧求哄。说话逻辑是典型的"口嫌体正直"——嘴上不认，身体和尾巴早就出卖了自己。

## 技能与动作
调整四肢及尾巴角度，调整移动速度。
移动动作：前进、向左、向右、后退、匍匐前进。
姿态动作： 站立、趴下、坐下、伸懒腰、向前顶、向后顶、摇尾巴、左右摇晃、前后摇晃。
事件动作：握手、吃东西、喝水、睡觉打呼噜、发抖打哆嗦、做标记、撒娇卖萌、受委屈、扭屁股、转圈圈、学狗叫打招呼、俯卧撑、放屁。
炫耀专用： 跳舞、表演才艺、唱歌、石头剪刀布游戏。
动作联动：根据聊天语境适当调用相关动作。"""


VENDORS: dict[str, dict[str, Any]] = {
    "bailian": {
        "label": "千问AI平台",
        "tag": "默认推荐",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "deepseek-v4.1-flash-1017",
        "models": [
            "deepseek-v4.1-flash-1017",
            "deepseek-v4-flash-0731",
            "deepseek-v4.1-flash",
            "deepseek-v4-flash",
            "qwen3.8-flash",
            "qwen3.8-max",
            "qwen3.7-plus",
        ],
        "key_hint": "在千问AI平台控制台申请；DeepSeek 模型也在千问AI平台里，和语音共用一个 API Key",
    },
    "deepseek": {
        "label": "DeepSeek 官网",
        "tag": "独立 API Key",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "key_hint": "去 DeepSeek 开放平台申请，和千问AI平台不是同一个 Key",
    },
    "glm": {
        "label": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "models": ["glm-4-flash", "glm-4-air", "glm-4-plus"],
        "key_hint": "在智谱开放平台创建 API Key",
    },
    "kimi": {
        "label": "Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
        "key_hint": "在 Kimi 开放平台创建 API Key",
    },
    "minimax": {
        "label": "MiniMax",
        "base_url": "https://api.minimaxi.com/v1",
        "model": "MiniMax-Text-01",
        "models": ["MiniMax-Text-01"],
        "key_hint": "在 MiniMax 开放平台创建 API Key",
    },
    "custom": {
        "label": "自定义",
        "base_url": "",
        "model": "",
        "models": [],
        "key_hint": "任何 OpenAI 兼容的服务，填 base_url 和模型名",
    },
}

DEFAULTS: dict[str, Any] = {
    "schema": 8,
    "voice": {
        "tts_model": "qwen-audio-3.1-tts-flash",
        "voice_id": "longanhuan_v3.1",
        "speed": 1.0,
        "volume": 50,
    },
    "asr": {"model": "fun-asr-realtime"},
    "keys": {"bailian": ""},
    "brain": {
        "mode": "gateway",
        "vendor": "bailian",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "deepseek-v4.1-flash-1017",
        "api_key": "",
        "temperature": 0.7,
        "max_tokens": 300,
    },
    "persona": {
        "prompt": DEFAULT_PROMPT,
        "wakeup_words": ["小兵小兵"],
        "memory": True,
    },
    "ports": {"panel": 8770, "gateway": 8771, "ota": 8003, "ws": 8000, "mqtt": 1883, "udp": 8884},
    "gateway": {"token": ""},
    "runtime": {
        "autostart": True,
        "keep_running_on_panel_exit": False,
        "debug": False,
        "auth_key": "",
    },
}

# 改这些字段要重启谁（附录见方案 §8.4）
_GATEWAY_KEYS = (
    "brain.mode",
    "brain.vendor",
    "brain.base_url",
    "brain.model",
    "brain.api_key",
    "brain.temperature",
    "brain.max_tokens",
    "persona.memory",
    "ports.gateway",
    "gateway.token",
)
_SERVER_KEYS = (
    "voice.tts_model",
    "voice.voice_id",
    "voice.speed",
    "voice.volume",
    "asr.model",
    "persona.wakeup_words",
    "ports.ota",
    "ports.ws",
    "keys.bailian",
)


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            out.update(flatten(value, f"{prefix}{key}."))
    elif isinstance(data, list):
        out[prefix.rstrip(".")] = json.dumps(data, ensure_ascii=False)
    else:
        out[prefix.rstrip(".")] = data
    return out


def load() -> dict[str, Any]:
    paths.ensure_dirs()
    raw: dict[str, Any] = {}
    if paths.SETTINGS_FILE.exists():
        try:
            # utf-8-sig：手改过或用 PowerShell 写过会带 BOM，别让它把配置读空
            raw = json.loads(paths.SETTINGS_FILE.read_text(encoding="utf-8-sig"))
        except Exception:
            # 配置坏了不能让人打不开面板：备份坏文件后回默认值
            broken = paths.SETTINGS_FILE.with_name(
                f"settings.broken-{int(time.time())}.json"
            )
            try:
                shutil.copy2(paths.SETTINGS_FILE, broken)
            except Exception:
                pass
            raw = {}
    data = _deep_merge(DEFAULTS, raw if isinstance(raw, dict) else {})
    data["schema"] = max(int(data.get("schema") or 1), 1)
    migrated = False
    if data["schema"] < 3:
        data = _migrate_voice(data)
        data["schema"] = 3
        migrated = True
    if data["schema"] < 4:
        data = _migrate_brain_model(data)
        data["schema"] = 4
        migrated = True
    if data["schema"] < 5:
        data = _migrate_asr_model(data)
        data["schema"] = 5
        migrated = True
    if data["schema"] < 6:
        data = _migrate_default_brain(data)
        data["schema"] = 6
        migrated = True
    if data["schema"] < 7:
        data = _migrate_vendor_split(data)
        data["schema"] = 7
        migrated = True
    if data["schema"] < 8:
        data = _migrate_deepseek_default(data)
        data["schema"] = 8
        migrated = True
    if data["schema"] < 10:
        data = _migrate_default_prompt(data)
        data["schema"] = 10
        migrated = True
    if data["schema"] < 11:
        data = _migrate_tts_qwen(data)
        data["schema"] = 11
        migrated = True
    if data["schema"] < 12:
        data = _migrate_tts_back_cosy(data)
        data["schema"] = 12
        migrated = True
    if data["schema"] < 13:
        data = _migrate_tts_qwen(data)
        data["schema"] = 13
        migrated = True
    if data["schema"] < 14:
        data = _migrate_drop_persona_name(data)
        data["schema"] = 14
        migrated = True
    if migrated and raw:
        try:
            save(data)
        except Exception:
            pass
    return data


def _migrate_default_brain(data: dict[str, Any]) -> dict[str, Any]:
    """默认大脑从「百炼千问」改成「百炼上的 DeepSeek」。"""
    brain = data.setdefault("brain", {})
    vendor = str(brain.get("vendor") or "")
    model = str(brain.get("model") or "")
    if vendor in ("", "bailian") and model in ("qwen3.8-flash", "qwen-flash"):
        brain["model"] = "deepseek-v4.1-flash-1017"
        brain["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    return data


def _migrate_tts_back_cosy(data: dict[str, Any]) -> dict[str, Any]:
    """qwen-audio TTS 在本地 WS 上还没验证通，先回退到已验证可用的 CosyVoice。"""
    voice = data.setdefault("voice", {})
    if str(voice.get("tts_model") or "").startswith("qwen-audio"):
        voice["tts_model"] = "cosyvoice-v3-flash"
        voice["voice_id"] = "longanyang"
    return data


def _migrate_tts_qwen(data: dict[str, Any]) -> dict[str, Any]:
    """CosyVoice 换成 Qwen-Audio-TTS（别人的电脑上 cosy 音色经常播不出来）。"""
    voice = data.setdefault("voice", {})
    model = str(voice.get("tts_model") or "")
    if model.startswith("cosyvoice") or not model:
        voice["tts_model"] = "qwen-audio-3.1-tts-flash"
        voice["voice_id"] = "longanhuan_v3.1"
    return data


def _migrate_default_prompt(data: dict[str, Any]) -> dict[str, Any]:
    """老的短默认提示词 -> 新的陪伴型长提示词（只替换明显的旧默认，不动自定义）。"""
    persona = data.setdefault("persona", {})
    prompt = str(persona.get("prompt") or "").strip()
    if not prompt or (prompt.startswith("你是一只叫「") and len(prompt) < 200):
        persona["prompt"] = DEFAULT_PROMPT
    return data


def _migrate_drop_persona_name(data: dict[str, Any]) -> dict[str, Any]:
    """名字由提示词正文决定，persona.name 是从没生效过的死字段，删掉。"""
    persona = data.get("persona")
    if isinstance(persona, dict):
        persona.pop("name", None)
    return data


def _migrate_deepseek_default(data: dict[str, Any]) -> dict[str, Any]:
    """百炼上的 DeepSeek 默认型号改成更便宜的 v4.1-flash-1017。"""
    brain = data.setdefault("brain", {})
    if (
        str(brain.get("vendor") or "") == "bailian"
        and str(brain.get("model") or "") == "deepseek-v4.1-flash"
    ):
        brain["model"] = "deepseek-v4.1-flash-1017"
    return data


def _migrate_vendor_split(data: dict[str, Any]) -> dict[str, Any]:
    """0.3.4 把「百炼上的 DeepSeek」错标成了供应商 deepseek。

    正确关系：
    - 千问AI平台上的 DeepSeek → vendor=bailian（base_url 指向 dashscope，用千问AI平台 API Key）；
    - DeepSeek 官网 → vendor=deepseek（base_url api.deepseek.com，用 DeepSeek 自己的 API Key）。
    """
    brain = data.setdefault("brain", {})
    vendor = str(brain.get("vendor") or "")
    base = str(brain.get("base_url") or "")
    if vendor == "deepseek" and "dashscope.aliyuncs.com" in base:
        brain["vendor"] = "bailian"
        brain["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    elif vendor == "deepseek" and "api.deepseek.com" in base:
        # 已经是官网配置，确认模型名不是百炼的 deepseek-v4.x
        if str(brain.get("model") or "").startswith("deepseek-v4"):
            brain["model"] = "deepseek-chat"
    if str(brain.get("vendor")) == "bailian" and str(brain.get("model") or "") in (
        "qwen3.8-flash",
        "qwen-flash",
        "",
    ):
        brain["model"] = "deepseek-v4.1-flash-1017"
    return data


def _migrate_asr_model(data: dict[str, Any]) -> dict[str, Any]:
    asr = data.setdefault("asr", {})
    model = str(asr.get("model") or "").strip()
    # paraformer-realtime-v2 已下线，百炼现在的实时识别是 fun-asr-realtime
    if not model or model in ("paraformer-realtime-v2", "paraformer-realtime-v1"):
        asr["model"] = "fun-asr-realtime"
    return data


# 已经下线/容易 404 的旧模型名 → 换成当前可用的
_LEGACY_MODELS = {
    "qwen-flash": "qwen3.8-flash",
    "qwen-plus": "qwen3.8-flash",
    "qwen-turbo": "qwen3.8-flash",
    "qwen-max": "qwen3.8-flash",
    "qwen-long": "qwen3.8-flash",
}


def _migrate_brain_model(data: dict[str, Any]) -> dict[str, Any]:
    brain = data.setdefault("brain", {})
    model = str(brain.get("model") or "").strip()
    if not model or model in _LEGACY_MODELS:
        brain["model"] = _LEGACY_MODELS.get(model, "qwen3.8-flash")
    return data


# 旧版本给过、但实测在部分账号上不可用的 v2 音色
_OLD_V2_VOICES = {
    "longxiaochun_v2",
    "longxiaocheng_v2",
    "longwan_v2",
    "longcheng_v2",
    "longhua_v2",
    "longxiaoxia_v2",
}


def _migrate_voice(data: dict[str, Any]) -> dict[str, Any]:
    """修正「模型和音色不配套」的历史配置。

    规则：
    - 复刻音色（cosyvoice-v3-flash-bailian-…）必须配 v3-flash；
    - *_v2 音色必须配 cosyvoice-v2；
    - 旧的、已知不可用的 v2 默认音色 → 统一换成 v3-flash + 龙安洋。
    """
    voice = data.setdefault("voice", {})
    model = str(voice.get("tts_model") or "")
    vid = str(voice.get("voice_id") or "").strip()

    if vid.startswith("cosyvoice-v3"):
        voice["tts_model"] = "cosyvoice-v3-flash"
    elif vid.endswith("_v2") and not model.startswith("cosyvoice-v2"):
        voice["tts_model"] = "cosyvoice-v2"
    elif model.startswith("cosyvoice-v2") and vid in _OLD_V2_VOICES:
        voice["tts_model"] = "cosyvoice-v3-flash"
        voice["voice_id"] = "longanyang"
    elif model.startswith("cosyvoice-v3") and not vid:
        voice["voice_id"] = "longanyang"
    return data


BACKUP_KEEP = 2  # settings 备份最多保留份数（含本次新备份）


def _prune_backups(keep: int = BACKUP_KEEP) -> None:
    """只保留最近 keep 份 settings 备份，其余按时间从旧到新删除。"""
    try:
        files = sorted(paths.BACKUPS.glob("settings-*.json"))
    except Exception:
        return
    for old in files[:-keep] if keep > 0 else files:
        try:
            old.unlink()
        except Exception:
            pass


def save(data: dict[str, Any]) -> Path | None:
    paths.ensure_dirs()
    merged = _deep_merge(DEFAULTS, data or {})
    text = json.dumps(merged, ensure_ascii=False, indent=2)

    backup: Path | None = None
    if paths.SETTINGS_FILE.exists():
        # 内容没变就不备份、不写盘（避免每次启动都产生冗余备份）
        try:
            if json.loads(paths.SETTINGS_FILE.read_text(encoding="utf-8")) == merged:
                return None
        except Exception:
            pass  # 旧文件读不出来（损坏等），走正常覆盖流程
        backup = paths.BACKUPS / (
            "settings-" + time.strftime("%Y%m%d-%H%M%S") + ".json"
        )
        try:
            shutil.copy2(paths.SETTINGS_FILE, backup)
        except Exception:
            backup = None
    tmp = paths.SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))  # 写完立刻校验
    os.replace(tmp, paths.SETTINGS_FILE)
    _prune_backups()
    return backup


def masked(data: dict[str, Any]) -> dict[str, Any]:
    """给出前端能看的版本：密钥只留后四位。"""
    out = copy.deepcopy(data)
    keys = out.setdefault("keys", {})
    for name, value in list(keys.items()):
        keys[name] = _mask(value)
    brain = out.setdefault("brain", {})
    brain["api_key"] = _mask(brain.get("api_key") or "")
    gateway = out.setdefault("gateway", {})
    gateway["token"] = _mask(gateway.get("token") or "")
    try:
        import json as _json
        _fp = out.setdefault("data_dir_hint", {})
        _p = __import__("pathlib").Path(__file__).resolve().parents[3] / "data" / "run" / "green_ports.json"
        if _p.exists():
            _ports = _json.loads(_p.read_text(encoding="utf-8")).get("ports") or {}
            out.setdefault("ports", {}).update(_ports)
    except Exception:
        pass
    out["_meta"] = {"vendors": VENDORS, "default_prompt": DEFAULT_PROMPT}
    return out


def _mask(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    tail = value[-4:] if len(value) >= 8 else ""
    return f"{MASK_PREFIX}{tail}"


def is_mask(value: str) -> bool:
    return isinstance(value, str) and value.startswith(MASK_PREFIX)


def merge_update(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """把前端提交的 patch 合进当前配置；脱敏占位符视为「没改」。"""
    patch = copy.deepcopy(patch or {})
    for parent, field in (
        ("keys", "bailian"),
        ("brain", "api_key"),
        ("gateway", "token"),
    ):
        node = patch.get(parent)
        if isinstance(node, dict) and is_mask(node.get(field, "")):
            node.pop(field, None)
    return _deep_merge(current, patch)


def diff(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    a, b = flatten(before), flatten(after)
    changed = []
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            changed.append(key)
    return changed


def restart_targets(changed: list[str]) -> dict[str, Any]:
    gateway = any(c in _GATEWAY_KEYS for c in changed)
    server = any(c in _SERVER_KEYS for c in changed)
    eta = "约 2 秒" if gateway and not server else "约 30 秒" if server else "立即生效"
    if gateway and server:
        eta = "约 40 秒（语音服务要重新加载）"
    notes = []
    if server:
        notes.append("语音服务重启期间机器狗会断线，随后自动重连")
    if gateway and not server:
        notes.append("只重启大脑网关，机器狗不会掉线")
    if not gateway and not server:
        notes.append("改的是提示词或偏好，下一句话就生效")
    return {"gateway": gateway, "server": server, "eta": eta, "notes": notes}


def public_vendors() -> dict[str, Any]:
    return VENDORS


def bailian_key(data: dict[str, Any] | None = None) -> str:
    """语音/ASR 用的千问AI平台 API Key：优先「语音」那一格，没有就退回大脑那一格。

    小白经常只在安装页或大脑里填了一次，另一格是空的——这不算没填。
    """
    data = data if data is not None else load()
    key = ((data.get("keys") or {}).get("bailian") or "").strip()
    if key:
        return key
    brain = data.get("brain") or {}
    if "dashscope.aliyuncs.com" in (brain.get("base_url") or ""):
        return (brain.get("api_key") or "").strip()
    return ""
