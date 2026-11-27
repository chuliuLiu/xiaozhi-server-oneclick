"""安装用到的下载源。模型/版本会变，所以集中放这里，改一处就够。"""

from __future__ import annotations

# 便携 Python：python-build-standalone（Astral 维护），国内走 npmmirror 镜像
PYTHON_VERSION = "3.11.18"
PYTHON_TAG = "20261026"
PYTHON_SHA256 = ""  # 打包时填；空 = 不校验（dev 模式）
PYTHON_URLS = [
    f"https://registry.npmmirror.com/-/binary/python-build-standalone/{PYTHON_TAG}/"
    f"cpython-{PYTHON_VERSION}%2B{PYTHON_TAG}-x86_64-pc-windows-msvc-install_only.tar.gz",
    f"https://github.com/astral-sh/python-build-standalone/releases/download/{PYTHON_TAG}/"
    f"cpython-{PYTHON_VERSION}%2B{PYTHON_TAG}-x86_64-pc-windows-msvc-install_only.tar.gz",
]

# ffmpeg：精简构建（GPL），随包分发时要带 LICENSE
FFMPEG_URLS = [
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://registry.npmmirror.com/-/binary/ffmpeg/ffmpeg-release-essentials.zip",
]
FFMPEG_SHA256 = ""

# pip 镜像：按顺序回退
PIP_INDEXES = [
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://pypi.org/simple",
]
