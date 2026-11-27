# 第三方组件与许可

本安装包内含以下第三方组件，均为公开可再分发版本。使用前请遵守各自的许可协议。

## 1. 小智服务端（xiaozhi-esp32-server）

- 项目：<https://github.com/xinnan-tech/xiaozhi-esp32-server>
- 许可：MIT
- 本包内位置：`runtime/server/`
- 说明：本包对上游做了极小改动（`config/logger.py` 关闭 loguru 异步日志，避免受限环境下命名管道失败），其余保持原样。
- 上游许可见 `licenses/xiaozhi-server-LICENSE.txt`。

## 2. 便携 Python（python-build-standalone）

- 项目：<https://github.com/astral-sh/python-build-standalone>
- 许可：Python Software Foundation License / 各依赖库自身许可
- 版本：CPython 3.11.18（x86_64-pc-windows-msvc，install_only）
- 本包内位置：`runtime/python/`
- 说明：已删除调试符号（.pdb）、开发头文件、tkinter 等与运行无关的文件。

## 3. FFmpeg

- 项目：<https://ffmpeg.org/>
- 构建：gyan.dev / BtbN 的 Windows 静态构建
- 许可：GPL/LGPL（取决于具体构建，随附构建为 GPL）
- 本包内位置：`runtime/bin/ffmpeg.exe`
- 说明：仅用于音频格式转换与解码。源码可从 <https://ffmpeg.org/download.html> 获取。

## 4. 其他 Python 依赖

安装时从 PyPI 镜像下载，均为各自的 MIT/BSD/Apache 许可，清单见
`app/panel/installer/requirements-cloud.txt`。

## 5. 字体与图标

界面不包含任何字体文件，全部使用 Windows 系统自带字体（Segoe UI / 微软雅黑 / Bahnschrift）；
图标为内联 SVG，随本项目一起以 MIT 发布。

## Microsoft Visual C++ Runtime (14.50.35719.0)

- 文件：msvcp140.dll、concrt140.dll、vcruntime140.dll、vcruntime140_1.dll
- 来源：本机 Microsoft Visual C++ 2015-2022 Redistributable (x64) 安装目录（C:\Windows\System32），版本 14.50.35719.0
- 放置：runtime/python、runtime/node、runtime/bin
- 用途：保证未安装 VC++ 运行库的机器上 Python/Node/onnxruntime 可启动

