"""安装用下载器：断点续传 + sha256 + 进度回调。"""

from __future__ import annotations

import hashlib
import os
import time
import urllib.request
from pathlib import Path
from typing import Callable

Progress = Callable[[int, int], None]


class DownloadError(Exception):
    pass


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(
    url: str,
    dest: Path,
    *,
    expect_sha256: str | None = None,
    progress: Progress | None = None,
    timeout: int = 60,
    retries: int = 2,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            existing = part.stat().st_size if part.exists() else 0
            headers = {"User-Agent": "xiaozhi-oneclick/0.1"}
            if existing:
                headers["Range"] = f"bytes={existing}-"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                mode = "ab" if existing and resp.status == 206 else "wb"
                if mode == "wb":
                    existing = 0
                total = existing + int(resp.headers.get("Content-Length") or 0)
                done = existing
                if progress:
                    progress(done, total)
                with part.open(mode) as fh:
                    while True:
                        chunk = resp.read(1 << 20)
                        if not chunk:
                            break
                        fh.write(chunk)
                        done += len(chunk)
                        if progress:
                            progress(done, total)
            if expect_sha256:
                actual = sha256_of(part)
                if actual.lower() != expect_sha256.lower():
                    part.unlink(missing_ok=True)
                    raise DownloadError("下载的文件校验不通过（可能被改动过），已删除")
            os.replace(part, dest)
            return dest
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if isinstance(exc, DownloadError):
                raise
            time.sleep(1.2 + attempt)
    raise DownloadError(f"下载失败：{last_error}")


def human_mb(value: int | float) -> str:
    return f"{value / 1024 / 1024:.1f} MB"


def fetch_first(urls: list[str], dest: Path, **kwargs) -> Path:
    """按顺序试镜像，第一个成功的算数。"""
    errors = []
    for url in urls:
        try:
            return fetch(url, dest, **kwargs)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url.split('/')[2]}: {exc}")
            progress = kwargs.get("progress")
            if progress:
                progress(0, 0)
    raise DownloadError("所有下载源都失败了：" + "；".join(errors[:3]))
