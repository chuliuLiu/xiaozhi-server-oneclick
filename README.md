# 小智本地服务 · 一键版（xiaozhi-oneclick）

> 给普通用户的小智服务端一键部署包：解压 → 双击一个 bat → 网页里点几下 → 机器狗能说话。
>
> 不依赖任何其它软件；不读系统 Python、不改 PATH、不写注册表。数据只存在本目录。
> 
> **系统要求：本项目现阶段只支持 Windows。**

---

## 能做什么

- 一个网页控制面板，管三件事：**环境检查 / 密钥参数 / 运行管理**。
- 装好即用：便携 Python、语音服务端、MQTT 网关、Node、ffmpeg 都在包里，不用你自己装环境。
- 语音和大脑走千问AI平台，语音合成 / 语音识别 / 大模型**共用一个 API Key**。
- 面板里能：启动/停止服务、复制 OTA 地址、看设备在线、看日志、诊断端口、一键放行防火墙。

## 怎么用

1. 解压到**纯英文、无空格**路径，例如 `D:\xiaozhi`
2. 双击 `🚀启动面板.bat`（浏览器自动打开 `http://127.0.0.1:8770`）
3. 「环境检查」→ 检查运行环境是否正常
4. 「密钥参数」→ 填千问AI平台 Key → 选音色 → 试听 → 保存
5. 「运行管理」→ 启动服务 → 复制 OTA 地址填进机器狗
6. 唤醒机器狗

常见问题（启动慢 / 模型报错 / 端口占用 / 设备离线延迟）：面板左下角「常见问题」，或 `app\panel\web\help\faq.html`。

第一次打开如果 Windows 弹「可能有害 / 无法验证发布者」，看 [第一次打开有安全提示？](app/panel/web/help/security.html)（页面右下角也有入口）。

## 密钥怎么填

![密钥配置](%E5%AF%86%E9%92%A5%E9%85%8D%E7%BD%AE.png)

1. 如果使用阿里千问 AI 平台的 API Key，只在第一处填写即可。
2. LLM 里可以选择自己想要的大模型，并填入对应的大模型 API Key；如果用的就是千问 AI 平台的大模型，这一处可以**不填**——它会复用第一处的 Key。

## 设备 OTA 地址怎么填

![设备 OTA 地址配置](%E8%AE%BE%E5%A4%87OTA%E5%9C%B0%E5%9D%80%E9%85%8D%E7%BD%AE.png)

小智服务启动后，需要把面板上的 OTA 地址写入到设备里。具体写入方法参考上图。

## 语音模型与音色

- **语音模型固定 `qwen-audio-3.1-tts-flash`**，识别模型固定 `fun-asr-realtime`：面板里不做切换，选好音色就行。
- **默认音色 `longanhuan_v3.1`（龙安欢）**：预置音色，开箱即用；面板里可选一长串官方音色（龙安洋、许南川等），点「试听」确认。
- **默认大脑是千问AI平台上的 DeepSeek（`deepseek-v4.1-flash-1017`）**：供应商是「千问AI平台」，和语音共用一个 Key。
- 「DeepSeek 官网」是单独选项：base_url 是 `https://api.deepseek.com`，要用 DeepSeek 自己申请的 Key，和千问AI平台不通用。
- 想用自己的声音：看 [声音复刻教程](app/panel/web/help/voice-clone.html)，把得到的音色 ID 填进「自定义音色 ID」。

## 目录

```
xiaozhi-oneclick\
├─ 启动面板.bat            唯一入口（静默启动，无黑框）
├─ app\
│  ├─ common\paths.py        路径常量（随包 Python / 运行目录等）
│  ├─ panel\server.py        stdlib HTTP 控制面板（零依赖，装之前也能跑）
│  ├─ panel\core\            设置 / 环境探测 / 网卡 / 端口 / 进程 / 服务托管 / 日志 / 防火墙 / 服务端配置生成
│  ├─ panel\installer\       7 步安装器 + 依赖清单 + 下载器
│  └─ panel\web\             三页 UI + help 页（获取 Key / 声音复刻 / 常见问题 / 安全提示 / 卸载）
├─ runtime\                  便携 Python / Node / ffmpeg / 语音服务端 / MQTT 网关
├─ tools\                    试听合成、打包、卸载脚本
├─ data\                     用户数据：settings.json、logs、run、backups
└─ 卸载.bat / 卸载说明.md / 使用说明.txt
```

## 设计要点

- **面板零依赖**：只用 Python 标准库，依赖装不上也能打开面板修。
- **不碰系统 Python**：子进程一律使用随包 Python，运行路径按项目当前位置动态计算。
- **一个事实源**：`data\settings.json` 是唯一配置来源，服务端配置由它派生成 `runtime\xiaozhi-server\data\.config.yaml`。
- **单实例**：面板 / 服务不允许两个进程抢同一端口，避免"改了没生效"的灵异问题。
- **安装幂等**：每步先检查再动手，断网 / 被杀后重跑接着来。
- **错误翻译**：启动失败时把日志尾巴翻成一句人话 + 一个动作（端口占用 / 缺依赖 / Key 不对 / 音频组件异常…）。

## 安全与隐私

- 密钥只存本机 `data\settings.json`，接口与日志一律打码；无遥测、无账号。
- 发布包里的 `runtime\xiaozhi-server` 与 `runtime\xiaozhi-mqtt-gateway` 来自上游项目，
  **不含任何人的 API Key、配置文件或聊天数据**（打包脚本会排除 `data\` 与服务端 `data\`）。
  Python 依赖放在项目内；打包时保留依赖包，排除带机器路径的 venv 配置和启动器。
- 程序没有商业代码签名，所以 Windows 会提示"未知发布者"；按安全提示页解除锁定即可。

## 进阶：面板后端接口（全部 127.0.0.1）

```
GET  /api/health | /api/env | /api/green/env | /api/install/plan | /api/settings
GET  /api/service/status | /api/net/adapters | /api/net/ota | /api/net/ports
GET  /api/logs | /api/selftest | /api/install/progress
POST /api/settings                 保存 + 返回 changed/restart/eta
POST /api/install/start|cancel     确认后启动 7 步安装
POST /api/service/start|stop|restart|relocate
POST /api/panel/shutdown           退出面板（可选连服务一起停）
POST /api/llm/models               真连一次拉模型列表（验证 Key）
POST /api/green/validate           校验 Key（服务端直连）
POST /api/voice/preview            合成试听 wav
POST /api/net/firewall             一键放行（专用网络）
```

## 已知限制

- 端到端出声需要真实千问AI平台 API Key；真机联调需要机器狗。
- 只做局域网；公网/穿透不在本版。
- 防火墙规则依赖 UAC 授权；被拒时会给手动命令。

## 退出与卸载

面板左下角「退出面板」：可只退面板（服务继续跑）或连服务一起停。关浏览器标签不等于关面板。重复双击 bat 只会打开已运行的面板，不会起第二个。

根目录 `卸载.bat`：选 1 只停服务并清防火墙规则，选 2 删除程序文件但保留 `data`，选 3 连整个文件夹和 `data` 一起删。
详见 [卸载说明.md](卸载说明.md) 或面板里的「怎么彻底卸载？」。本程序不写注册表、不装服务、不加开机启动。

## 来源与贡献

- 主体功能（面板、安装器、配置同步、网关及 v0.11.0 迭代）由 Chulio（老鎏）开发。
- 后期细节优化与绿色版分发由 JeremyWang 贡献；同源 Gitee 仓库：<https://gitee.com/jeremywang0102/xiaozhi-server-oneclick>
- 本仓库为该项目的 GitHub 开源版本，具体版本与上游组件版本以 `version.json` 为准。第三方依赖许可见 `THIRD-PARTY.md` 与 `licenses/`。
