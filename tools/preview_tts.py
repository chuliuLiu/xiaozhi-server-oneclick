#!/usr/bin/env python3
"""用百炼 CosyVoice 合成一句试听音频（PCM → wav）。

由面板用 runtime/python 的便携 Python 调起，并从项目内依赖目录加载库：
    python tools/preview_tts.py --key sk-xxx --voice longxiaochun_v2 --out x.wav

失败时 exit 2 并把原因打到 stderr，面板翻译成人话。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
import wave

import websockets

WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"


async def synth(key: str, text: str, model: str, voice: str, sample_rate: int) -> bytes:
    headers = {"Authorization": f"Bearer {key}"}
    task_id = uuid.uuid4().hex

    async def _run(ws) -> bytes:
        pcm = bytearray()
        await ws.send(
            json.dumps(
                {
                    "header": {"action": "run-task", "task_id": task_id, "streaming": "duplex"},
                    "payload": {
                        "task_group": "audio",
                        "task": "tts",
                        "function": "SpeechSynthesizer",
                        "model": model,
                        "parameters": {
                            "text_type": "PlainText",
                            "voice": voice,
                            "format": "pcm",
                            "sample_rate": sample_rate,
                            "volume": 50,
                            "rate": 1.0,
                        },
                        "input": {},
                    },
                }
            )
        )
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=20)
            if isinstance(msg, bytes):
                continue
            header = json.loads(msg).get("header", {})
            event = header.get("event")
            if event == "task-started":
                break
            if event == "task-failed":
                raise RuntimeError(
                    f"{header.get('error_code', '')} {header.get('error_message', '')}".strip()
                    or "任务启动失败"
                )
        await ws.send(
            json.dumps(
                {
                    "header": {"action": "continue-task", "task_id": task_id, "streaming": "duplex"},
                    "payload": {"input": {"text": text}},
                }
            )
        )
        await ws.send(
            json.dumps(
                {
                    "header": {"action": "finish-task", "task_id": task_id, "streaming": "duplex"},
                    "payload": {"input": {}},
                }
            )
        )
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=30)
            if isinstance(msg, bytes):
                pcm.extend(msg)
                continue
            header = json.loads(msg).get("header", {})
            event = header.get("event")
            if event == "task-finished":
                break
            if event == "task-failed":
                raise RuntimeError(
                    f"{header.get('error_code', '')} {header.get('error_message', '')}".strip()
                    or "合成失败"
                )
        if not pcm:
            raise RuntimeError("没有拿到音频数据")
        return bytes(pcm)

    last = None
    attempts = (
        {"local_addr": ("0.0.0.0", 0), "open_timeout": 30},
        {"open_timeout": 30},
    )
    for extra in attempts:
        try:
            async with websockets.connect(
                WS_URL,
                additional_headers=headers,
                max_size=None,
                **extra,
            ) as ws:
                return await _run(ws)
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
    raise last if last else RuntimeError("连接失败")


def write_wav(path: str, pcm: bytes, sample_rate: int) -> None:
    """手写 WAV，避开 wave 模块在异常路径上的 _file 问题。"""
    import struct

    data = bytes(pcm)
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16)
    body = (
        b"RIFF"
        + struct.pack("<I", 36 + len(data))
        + b"WAVEfmt "
        + struct.pack("<I", 16)
        + fmt
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )
    with open(path, "wb") as fh:
        fh.write(body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True)
    parser.add_argument("--voice", default="longxiaochun_v2")
    parser.add_argument("--model", default="cosyvoice-v2")
    parser.add_argument("--text", default="你好呀，我是小兵，今天想玩点什么？")
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample-rate", type=int, default=24000)
    args = parser.parse_args()

    try:
        pcm = asyncio.run(
            synth(args.key, args.text, args.model, args.voice, args.sample_rate)
        )
        write_wav(args.out, pcm, args.sample_rate)
    except Exception as exc:  # noqa: BLE001
        print(str(exc)[:400], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
