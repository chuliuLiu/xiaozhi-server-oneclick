"""安装编排：7 步、可取消、幂等、带真进度。

每一步都先「检查是否已就绪」——已就绪就 SKIP，
所以断网、装一半、杀进程之后重新点一次，都是接着装而不是从头再来。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Callable

from app.common import paths
from app.panel.core import configsync, envprobe, procs, services, settings
from app.panel.installer import download, sources

CREATE_NO_WINDOW = 0x08000000

STEP_DEFS = [
    ("python", "便携 Python 3.11", 14),
    ("pyenv", "项目内依赖目录", 10),
    ("deps", "语音与网络依赖", 55),
    ("ffmpeg", "音频组件", 8),
    ("server", "小智服务端", 5),
    ("config", "生成默认配置", 4),
    ("verify", "收尾自检", 4),
]


class StepError(Exception):
    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.hint = hint


class InstallJob:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.lock = threading.Lock()
        self.cancel_flag = threading.Event()
        self.thread: threading.Thread | None = None
        self.state = "idle"
        self.percent = 0.0
        self.current = ""
        self.message = ""
        self.error = ""
        self.hint = ""
        self.steps = {
            step_id: {"id": step_id, "name": name, "state": "pending", "detail": "", "weight": weight}
            for step_id, name, weight in STEP_DEFS
        }
        self.logs: list[str] = []
        self.started_at = 0.0
        self.finished_at = 0.0
        self._current_proc: subprocess.Popen | None = None

    # ---------------------------------------------------------------- 对外接口

    def start(self) -> bool:
        with self.lock:
            if self.state == "running":
                return False
            self.state = "running"
            self.percent = 0.0
            self.error = ""
            self.hint = ""
            self.message = "准备中…"
            self.started_at = time.time()
            self.finished_at = 0.0
            for step in self.steps.values():
                step["state"] = "pending"
                step["detail"] = ""
            self.logs.clear()
            self.thread = threading.Thread(target=self._run, name="installer", daemon=True)
            self.thread.start()
            return True

    def cancel(self) -> bool:
        if self.state != "running":
            return False
        self.cancel_flag.set()
        proc = self._current_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self.log("收到取消请求，正在停下…")
        return True

    def snapshot(self) -> dict:
        with self.lock:
            steps = [dict(self.steps[sid]) for sid, _, _ in STEP_DEFS]
            done = self.state in ("done", "failed", "cancelled")
            return {
                "running": self.state == "running",
                "state": self.state,
                "percent": round(self.percent, 1),
                "current": self.current,
                "message": self.message,
                "error": self.error,
                "hint": self.hint,
                "steps": steps,
                "logs": self.logs[-120:],
                "elapsed": int((self.finished_at or time.time()) - self.started_at) if self.started_at else 0,
                "finished": done,
            }

    # ---------------------------------------------------------------- 内部

    def log(self, text: str) -> None:
        line = str(text).rstrip()
        if not line:
            return
        with self.lock:
            self.logs.append(line)
            if len(self.logs) > 800:
                del self.logs[:200]

    def _set_percent(self, value: float) -> None:
        with self.lock:
            self.percent = max(self.percent, min(99.0, value))

    def _step_start(self, step_id: str) -> None:
        with self.lock:
            self.current = step_id
            self.steps[step_id]["state"] = "running"
            self.message = self.steps[step_id]["name"]
        self.log(f"▶ {self.steps[step_id]['name']}")

    def _step_done(self, step_id: str, detail: str = "", skipped: bool = False) -> None:
        with self.lock:
            self.steps[step_id]["state"] = "done"
            self.steps[step_id]["detail"] = detail
        self.log(("⏭ " if skipped else "✓ ") + (detail or self.steps[step_id]["name"]))
        base = 0.0
        for sid, _, weight in STEP_DEFS:
            if sid == step_id:
                base += weight
                break
            base += weight
        self._set_percent(base / sum(w for _, _, w in STEP_DEFS) * 100)

    def _run(self) -> None:
        try:
            self._step_python()
            self._check_cancel()
            self._step_pyenv()
            self._check_cancel()
            self._step_deps()
            self._check_cancel()
            self._step_ffmpeg()
            self._check_cancel()
            self._step_server()
            self._check_cancel()
            self._step_config()
            self._check_cancel()
            self._step_verify()
            with self.lock:
                self.state = "done"
                self.percent = 100.0
                self.message = "安装完成"
                self.finished_at = time.time()
            self.log("✅ 全部完成")
        except StepError as exc:
            self._fail(exc.message, exc.hint)
        except Exception as exc:  # noqa: BLE001
            self._fail("安装过程出错了", f"{type(exc).__name__}: {exc}")
        finally:
            if self.state == "running":
                self.state = "done"

    def _fail(self, message: str, hint: str) -> None:
        with self.lock:
            self.state = "cancelled" if self.cancel_flag.is_set() else "failed"
            self.error = message
            self.hint = hint
            self.message = message
            self.finished_at = time.time()
            for sid, _, _ in STEP_DEFS:
                if self.steps[sid]["state"] == "running":
                    self.steps[sid]["state"] = "error"
        self.log(f"✗ {message} {('· ' + hint) if hint else ''}")

    def _check_cancel(self) -> None:
        if self.cancel_flag.is_set():
            raise StepError("已取消", "随时可以重新开始")

    # ---------------------------------------------------------------- 各步骤

    def _step_python(self) -> None:
        self._step_start("python")
        exe = paths.PORTABLE_PYTHON
        if exe.exists():
            info = procs.run_version(exe)
            if info.get("ok"):
                self._step_done("python", f"已就绪 · {info.get('version', '')}", skipped=True)
                return
        self.log("没找到便携 Python，正在下载（约 47 MB）…")
        archive = paths.DATA / "tmp" / "python-portable.tar.gz"
        archive.parent.mkdir(parents=True, exist_ok=True)
        try:
            download.fetch_first(
                sources.PYTHON_URLS,
                archive,
                expect_sha256=sources.PYTHON_SHA256 or None,
                progress=self._download_progress(0, 14),
            )
        except Exception as exc:  # noqa: BLE001
            raise StepError("下载便携 Python 失败", f"{exc}") from exc
        self.log("正在解压…")
        try:
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(paths.RUNTIME)
        except Exception as exc:  # noqa: BLE001
            raise StepError("解压便携 Python 失败", str(exc)) from exc
        if not exe.exists():
            raise StepError("解压后没找到 python.exe", "安装包可能不完整，请重新解压")
        info = procs.run_version(exe)
        if not info.get("ok"):
            raise StepError("便携 Python 跑不起来", info.get("raw", ""))
        self._step_done("python", f"已安装 · {info.get('version', '')}")

    def _step_pyenv(self) -> None:
        self._step_start("pyenv")
        if paths.SITE_PACKAGES.is_dir():
            self._step_done("pyenv", "依赖目录已存在", skipped=True)
            return
        self.log("正在准备项目内依赖目录…")
        try:
            paths.SITE_PACKAGES.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StepError("创建依赖目录失败", str(exc)) from exc
        self._step_done("pyenv", "依赖目录已准备")

    def _step_deps(self) -> None:
        self._step_start("deps")
        python = paths.python_for_children()
        if not python:
            raise StepError("便携 Python 不可用", "先重试便携 Python 安装步骤")
        if self._imports_ok():
            self._step_done("deps", "依赖已齐全", skipped=True)
            return
        req = Path(__file__).with_name("requirements-cloud.txt")
        last_error = ""
        for index, mirror in enumerate(sources.PIP_INDEXES):
            if self.cancel_flag.is_set():
                raise StepError("已取消")
            self.log(f"正在从 {mirror.split('/')[2]} 下载依赖（约 170 MB）…")
            cmd = [
                str(python),
                "-m",
                "pip",
                "install",
                "--target",
                str(paths.SITE_PACKAGES),
                "--upgrade",
                "-r",
                str(req),
                "-i",
                mirror,
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--no-input",
            ]
            ok = self._run_streaming(cmd, self._pip_progress(index))
            if ok and self._imports_ok():
                self._step_done("deps", "依赖安装完成")
                return
            last_error = f"镜像 {mirror.split('/')[2]} 失败"
            self.log(last_error + "，换下一个源…")
        raise StepError("依赖没装上", last_error or "检查网络后重试")

    def _step_ffmpeg(self) -> None:
        self._step_start("ffmpeg")
        if paths.FFMPEG.exists():
            ok, line = envprobe._ffmpeg_ok()
            if ok:
                self._step_done("ffmpeg", "已就绪", skipped=True)
                return
        bundled = paths.PROJECT / "vendor" / "ffmpeg.zip"
        if bundled.exists():
            self.log("正在解压随包的 ffmpeg…")
            self._extract_ffmpeg(bundled)
            self._step_done("ffmpeg", "已解压")
            return
        self.log("正在下载 ffmpeg（约 40 MB）…")
        archive = paths.DATA / "tmp" / "ffmpeg.zip"
        archive.parent.mkdir(parents=True, exist_ok=True)
        try:
            download.fetch_first(
                sources.FFMPEG_URLS,
                archive,
                expect_sha256=sources.FFMPEG_SHA256 or None,
                progress=self._download_progress(0, 8),
            )
        except Exception as exc:  # noqa: BLE001
            raise StepError("下载 ffmpeg 失败", str(exc)) from exc
        self._extract_ffmpeg(archive)
        self._step_done("ffmpeg", "已安装")

    def _extract_ffmpeg(self, archive: Path) -> None:
        paths.BIN.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive) as zf:
                for name in zf.namelist():
                    base = name.rsplit("/", 1)[-1].lower()
                    if base in ("ffmpeg.exe", "ffprobe.exe", "opus.dll", "libopus-0.dll"):
                        target = paths.BIN / name.rsplit("/", 1)[-1]
                        with zf.open(name) as src, target.open("wb") as dst:
                            shutil.copyfileobj(src, dst)
        except Exception as exc:  # noqa: BLE001
            raise StepError("解压 ffmpeg 失败", str(exc)) from exc
        if not paths.FFMPEG.exists():
            raise StepError("解压后没找到 ffmpeg.exe", "安装包可能不完整")

    def _step_server(self) -> None:
        self._step_start("server")
        if (paths.SERVER / "app.py").exists():
            self._step_done("server", "已内置", skipped=True)
            return
        template = paths.PROJECT / "vendor" / "xiaozhi-server-0.9.6"
        if not template.exists():
            raise StepError("服务端源码缺失", "请重新解压整个安装包")
        self.log("正在释放服务端源码…")
        shutil.copytree(template, paths.SERVER, dirs_exist_ok=True)
        self._step_done("server", "已释放")

    def _step_config(self) -> None:
        self._step_start("config")
        conf = settings.load()
        conf = services.ensure_auth_key(conf)
        conf, token = services.ensure_token(conf)
        result = configsync.write(conf, int(conf["ports"]["gateway"]), token)
        if not result.get("ok"):
            raise StepError("生成配置失败", result.get("message", ""))
        self._step_done("config", "已生成并校验")

    def _step_verify(self) -> None:
        self._step_start("verify")
        problems = []
        if not self._imports_ok():
            problems.append("依赖导入失败")
        ok, _line = envprobe._ffmpeg_ok()
        if not ok:
            problems.append("ffmpeg 不可用")
        if not (paths.SERVER / "data" / ".config.yaml").exists():
            problems.append("配置文件缺失")
        if problems:
            raise StepError("自检没通过", "、".join(problems) + "；点「重新安装依赖」再试")
        self._step_done("verify", "6 项全绿")

    # ---------------------------------------------------------------- 工具

    def _child_env(self) -> dict:
        env = paths.child_env()
        tmp = paths.DATA / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        env["TMP"] = str(tmp)
        env["TEMP"] = str(tmp)
        return env

    def _imports_ok(self) -> bool:
        return envprobe.dependencies_ready()

    def _download_progress(self, base: float, span: float) -> Callable[[int, int], None]:
        last = {"t": 0.0}

        def cb(done: int, total: int) -> None:
            now = time.time()
            if now - last["t"] < 0.25:
                return
            last["t"] = now
            if total:
                self._set_percent(base + span * (done / total))
                self.message = f"已下载 {download.human_mb(done)} / {download.human_mb(total)}"

        return cb

    def _pip_progress(self, mirror_index: int) -> Callable[[str], None]:
        base = mirror_index * 5
        state = {"n": 0}

        def cb(line: str) -> None:
            if line.startswith("Downloading") or line.startswith("Collecting"):
                state["n"] += 1
                self._set_percent(min(85, 15 + state["n"] * 1.2))
                self.message = f"正在安装依赖（已处理 {state['n']} 个包）"

        return cb

    def _run_streaming(self, cmd: list[str], on_line: Callable[[str], None]) -> bool:
        self.log("$ " + " ".join(cmd[:6]) + " …")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=self._child_env(),
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception as exc:  # noqa: BLE001
            self.log(f"启动失败：{exc}")
            return False
        self._current_proc = proc
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                text = line.rstrip()
                if not text:
                    continue
                self.log(text)
                on_line(text)
                if self.cancel_flag.is_set():
                    proc.terminate()
                    break
        finally:
            self._current_proc = None
        code = proc.wait()
        return code == 0
