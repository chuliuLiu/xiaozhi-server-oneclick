/* 小智本地服务 · 控制面板前端
   无框架、无构建：一个文件搞定状态、渲染和动效。 */

(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const DEMO = new URLSearchParams(location.search).has("demo");

  const PAGES = {
    install: {
      title: "环境检查",
      desc: "检查运行环境是否正常。",
    },
    config: {
      title: "密钥参数",
      desc: "先检查运行环境，再填 Key。",
    },
    run: {
      title: "运行管理",
      desc: "启动服务，把这行 OTA 地址填到机器狗里。",
    },
  };

  // 音色按模型分组（不同模型音色不通用）
  const VOICE_SETS = {
    "qwen-audio-3.1-tts-flash": [
      { id: "longanhuan_v3.1", name: "龙安欢", desc: "欢脱元气女 · 默认" },
      { id: "longanlingxin_v3.1", name: "龙安灵心", desc: "知心温暖女" },
      { id: "longanfengyue_v3.1", name: "龙安风悦", desc: "自然亲切女" },
      { id: "xunanchuan_v3.1", name: "许南川", desc: "磁性男声" },
      { id: "longanyang_v3.1", name: "龙安洋", desc: "阳光大男孩 · 标杆" },
      { id: "longxiaoxia_v3.1", name: "龙小夏", desc: "沉稳权威女" },
      { id: "longanwen_v3.1", name: "龙安温", desc: "优雅知性女" },
      { id: "longanli_v3.1", name: "龙安莉", desc: "利落从容女" },
      { id: "longanlang_v3.1", name: "龙安朗", desc: "清爽利落男" },
      { id: "longyue_v3.1", name: "龙悦", desc: "温暖磁性女" },
      { id: "longmiao_v3.1", name: "龙妙", desc: "抑扬顿挫女" },
      { id: "longshu_v3.1", name: "龙书", desc: "沉稳磁性男" },
      { id: "longqiang_v3.1", name: "龙嫱", desc: "浪漫风情女" },
      { id: "longfeifei_v3.1", name: "龙菲菲", desc: "甜美娇气女" },
      { id: "longjing_v3.1", name: "龙婧", desc: "质感沉稳女" },
      { id: "longlaotie_v3.1", name: "龙老铁", desc: "东北直率男" },
      { id: "longpaopao_v3.1", name: "龙泡泡", desc: "飞天泡泡音" },
      { id: "longniuniu_v3.1", name: "龙牛牛", desc: "阳光男童声" },
      { id: "longjielidou_v3.1", name: "龙杰力豆", desc: "天真男童音" },
      { id: "longling_v3.1", name: "龙铃", desc: "稚气女童音" },
      { id: "longke_v3.1", name: "龙可", desc: "懵懂儿童音" },
      { id: "longshao_v3.1", name: "龙邵", desc: "积极元气男" },
      { id: "longze_v3.1", name: "龙泽", desc: "温暖元气男" },
      { id: "longcheng_v3.1", name: "龙橙", desc: "智慧磁性男" },
      { id: "longtian_v3.1", name: "龙天", desc: "磁性理智男" },
      { id: "longxiaobai_v3.1", name: "龙小白", desc: "磁性质感女" },
      { id: "longyan_v3.1", name: "龙颜", desc: "温暖自然女" },
      { id: "longnan_v3.1", name: "龙楠", desc: "睿智男声" },
      { id: "longshuo_v3.1", name: "龙硕", desc: "博才干练男" },
      { id: "longhuohuo_v3.1", name: "龙火火", desc: "顽皮少年音" },
      { id: "longyingtao_v3.1", name: "龙应桃", desc: "温柔淡定女" },
      { id: "longanya_v3.1", name: "龙安雅", desc: "高雅气质女" },
      { id: "longwan_v3.1", name: "龙婉", desc: "细腻柔声女" },
      { id: "longxing_v3.1", name: "龙星", desc: "温婉邻家女" },
      { id: "longhua_v3.1", name: "龙华", desc: "元气甜美女" },
      { id: "longhan_v3.1", name: "龙寒", desc: "温暖痴情男" },
      { id: "longanzhi_v3.1", name: "龙安智", desc: "睿智轻熟男" },
      { id: "longzhe_v3.1", name: "龙哲", desc: "呆板大暖男" },
      { id: "libai_v3.1", name: "李白", desc: "古代诗仙男" },
      { id: "longyuan_v3.1", name: "龙媛", desc: "温暖治愈女" },
      { id: "longsanshu_v3.1", name: "龙三叔", desc: "沉稳质感男" },
      { id: "yuxiaoyun_v3.1", name: "于小云", desc: "元气亲切女" },
      { id: "qiaoxiaojiao_v3.1", name: "乔小娇", desc: "俏丽可爱女" },
      { id: "xiaxiaochen_v3.1", name: "夏小晨", desc: "元气明亮女" },
      { id: "anmingyuan_v3.1", name: "安明远", desc: "清亮自然男" },
      { id: "wenhuaiqing_v3.1", name: "温怀清", desc: "清亮柔和女" },
      { id: "anxiaolan_v3.1", name: "安小岚", desc: "清甜纯净女" },
      { id: "xieshurou_v3.1", name: "谢舒柔", desc: "柔和知性女" },
      { id: "baiqinglan_v3.1", name: "白清岚", desc: "明亮清纯女" },
      { id: "xuyuyuan_v3.1", name: "许玉远", desc: "知性成熟女" },
      { id: "anruorou_v3.1", name: "安若柔", desc: "气声知性女" },
      { id: "yeqinghe_v3.1", name: "叶清禾", desc: "亲切温柔女" },
      { id: "xuxiaoqiao_v3.1", name: "徐小俏", desc: "自然俏皮女" },
      { id: "xuyanchu_v3.1", name: "许言初", desc: "沉稳磁性女" },
      { id: "yezhiqing_v3.1", name: "叶知晴", desc: "轻快自然女" },
      { id: "anyuqing_v3.1", name: "安语晴", desc: "甜妹音" },
      { id: "linxiaoling_v3.1", name: "林小灵", desc: "甜妹音" },
    ],
  };

  function voicesFor(model) {
    return VOICE_SETS[model] || VOICE_SETS["qwen-audio-3.1-tts-flash"];
  }

  function findVoice(model, id) {
    return voicesFor(model).find((v) => v.id === id) || null;
  }

  function renderVoiceOptions(model, selected) {
    const list = voicesFor(model);
    const known = list.some((v) => v.id === selected);
    let html = list
      .map(
        (v) =>
          `<option value="${v.id}" ${v.id === selected ? "selected" : ""}>${esc(v.name)} · ${esc(
            v.desc
          )}</option>`
      )
      .join("");
    if (selected && !known) {
      html += `<option value="${esc(selected)}" selected>自定义音色 · ${esc(selected)}</option>`;
    }
    $("#cfgVoice").innerHTML = html;
  }

  const FALLBACK_VENDORS = {
    bailian: {
      label: "千问AI平台",
      tag: "默认推荐",
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
      model: "deepseek-v4.1-flash-1017",
      key_hint: "在千问AI平台控制台申请；DeepSeek 模型也在千问AI平台里，和语音共用一个 API Key",
    },
    deepseek: {
      label: "DeepSeek 官网",
      tag: "独立 API Key",
      base_url: "https://api.deepseek.com",
      model: "deepseek-chat",
      key_hint: "去 DeepSeek 开放平台申请，和千问AI平台 API Key不是同一个 API Key",
    },
    glm: {
      label: "智谱 GLM",
      base_url: "https://open.bigmodel.cn/api/paas/v4",
      model: "glm-4-flash",
      key_hint: "在智谱开放平台创建 API Key",
    },
    kimi: {
      label: "Kimi",
      base_url: "https://api.moonshot.cn/v1",
      model: "moonshot-v1-8k",
      key_hint: "在 Kimi 开放平台创建 API Key",
    },
    minimax: {
      label: "MiniMax",
      base_url: "https://api.minimaxi.com/v1",
      model: "MiniMax-Text-01",
      key_hint: "在 MiniMax 开放平台创建 API Key",
    },
    custom: {
      label: "自定义",
      base_url: "",
      model: "",
      key_hint: "任何 OpenAI 兼容的服务，填地址和模型名",
    },
  };

  const state = {
    page: "install",
    health: null,
    env: null,
    plan: null,
    settings: null,
    vendors: FALLBACK_VENDORS,
    status: null,
    ota: null,
    adapters: [],
    baseline: null,
    dirty: false,
    installing: false,
    logTimer: null,
    statusTimer: null,
    logFilter: "",
    logLines: 120,
    demoInstalled: false,
  };

  // ------------------------------------------------------------------ 小工具

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function fmtMb(mb) {
    const n = Number(mb) || 0;
    if (n >= 1000) return (n / 1024).toFixed(1) + " GB";
    return Math.round(n) + " MB";
  }

  function fmtUptime(sec) {
    const s = Math.max(0, Number(sec) || 0);
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h) return `${h} 小时 ${m} 分`;
    if (m) return `${m} 分`;
    return `${s} 秒`;
  }

  function esc(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function api(path, options = {}) {
    if (DEMO) return demoApi(path, options);
    const opts = { headers: {}, ...options };
    if (opts.body && typeof opts.body !== "string") {
      opts.body = JSON.stringify(opts.body);
      opts.headers["Content-Type"] = "application/json";
    }
    try {
      const resp = await fetch(path, opts);
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok && data && data.message) {
        return { ...data, ok: false, status: resp.status };
      }
      return data;
    } catch (err) {
      return { ok: false, message: "面板连不上了，刷新页面试试", detail: String(err) };
    }
  }

  // --------------------------------------------------------------- Toast

  function toast(type, title, message = "") {
    const icon = type === "ok" ? "#i-check" : type === "bad" ? "#i-alert" : "#i-info";
    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.innerHTML = `
      <svg class="ic"><use href="${icon}"/></svg>
      <div><b>${esc(title)}</b>${message ? `<p>${esc(message)}</p>` : ""}</div>`;
    $("#toasts").appendChild(el);
    const kill = () => {
      el.classList.add("is-out");
      setTimeout(() => el.remove(), 260);
    };
    el.addEventListener("click", kill);
    setTimeout(kill, 4600);
    return el;
  }

  // --------------------------------------------------------------- 弹窗

  let modalOnOk = null;

  function openModal({ title, body, hint = "", okText = "确定", okKind = "primary", onOk }) {
    $("#modalTitle").textContent = title;
    $("#modalBody").innerHTML = body;
    $("#modalHint").textContent = hint;
    const ok = $("#modalOk");
    ok.textContent = okText;
    ok.className = `btn ${okKind === "primary" ? "btn-primary" : "btn-secondary"}`;
    modalOnOk = onOk;
    $("#modalLayer").hidden = false;
    setTimeout(() => ok.focus(), 60);
  }

  function closeModal() {
    $("#modalLayer").hidden = true;
    modalOnOk = null;
  }

  // --------------------------------------------------------------- 导航

  function moveIndicator() {
    const nav = $(".rail-nav");
    const active = $(".nav-item[aria-current='page']");
    const ind = $("#railIndicator");
    if (!nav || !active || !ind) return;
    if (window.matchMedia("(max-width: 900px)").matches) return;
    ind.style.height = active.offsetHeight + "px";
    ind.style.transform = `translateY(${active.offsetTop}px)`;
  }

  function go(page) {
    if (!PAGES[page]) page = "install";
    state.page = page;
    $("#app").dataset.page = page;
    $$(".page").forEach((el) => el.classList.toggle("is-active", el.dataset.page === page));
    $$(".nav-item").forEach((el) => {
      if (el.dataset.nav === page) el.setAttribute("aria-current", "page");
      else el.removeAttribute("aria-current");
    });
    $("#pageTitle").textContent = PAGES[page].title;
    $("#pageDesc").textContent = PAGES[page].desc;
    moveIndicator();
    history.replaceState(null, "", `?page=${page}${DEMO ? "&demo=1" : ""}`);
    if (page === "run") {
      refreshStatus();
      loadOta();
      if ($("#logsToggle").checked) loadLogs();
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // --------------------------------------------------------------- 状态胶囊

  function setPill(id, cls, text) {
    const pill = $(id);
    if (!pill) return;
    const dot = pill.querySelector(".dot");
    dot.className = `dot dot--${cls}`;
    pill.querySelector("b").textContent = text;
  }

  function paintPills() {
    const env = state.env;
    if (!env) return;
    const cls = env.installed ? "ok" : env.stage === "partial" ? "warn" : "idle";
    setPill("#pillEnv", cls, env.installed ? "已就绪" : env.stage === "partial" ? "装了一半" : "未安装");
    $("#railVersion").textContent = env.version || "0.1.0";

    const hasKey = Boolean(state.settings && state.settings.keys && state.settings.keys.bailian);
    setPill("#pillKey", hasKey ? "ok" : "warn", hasKey ? "已配置" : "未配置");

    const st = state.status;
    const running = st && st.any_running;
    setPill("#pillSrv", running ? "ok" : "idle", running ? "运行中" : "未启动");

    $$(".nav-dot").forEach((dot) => {
      const key = dot.dataset.dot;
      dot.className = "nav-dot";
      if (key === "env") dot.classList.add(env.installed ? "is-ok" : env.stage === "partial" ? "is-warn" : "");
      if (key === "key") dot.classList.add(hasKey ? "is-ok" : "is-warn");
      if (key === "srv") dot.classList.add(running ? "is-ok" : "");
    });
  }

  // --------------------------------------------------------------- 环境渲染

  const okText = (flag) => (flag ? "is-ok" : "is-bad");

  function renderEnv() {
    const env = state.env;
    if (!env) return;
    const py = env.python.portable;
    const pyenv = env.python.pyenv;
    const sysPy = env.python.system;
    const sysVersion = String(sysPy.version || "").replace(/^Python\s*/i, "");

    const rows = [
      {
        title: "便携 Python",
        desc: sysPy.exists
          ? `检测到你电脑上有 Python ${esc(sysVersion)}（不会使用，也不会改动它）`
          : "随包自带，不读取、不修改你电脑上的 Python",
        value: py.ok ? esc(py.version || "3.11") : "缺失",
        cls: okText(py.ok),
      },
      {
        title: "语音依赖",
        desc: pyenv.ready
          ? `依赖已安装，占用 ${fmtMb(env.sizes.pyenv_mb)}`
          : "服务运行所需的 Python 库尚未安装",
        value: pyenv.ready ? "已就绪" : "未安装",
        cls: okText(pyenv.ready),
      },
      {
        title: "音频组件",
        desc: env.ffmpeg.ok
          ? esc(String(env.ffmpeg.line || "ffmpeg").split(" Copyright")[0])
          : "ffmpeg 与 opus，机器狗的声音靠它",
        value: env.ffmpeg.ok ? "已就绪" : "未安装",
        cls: okText(env.ffmpeg.ok),
      },
      {
        title: "磁盘空间",
        desc: `剩余 ${env.disk.free_gb} GB，安装需要约 ${env.disk.need_gb} GB`,
        value: env.disk.ok ? "充足" : "不足",
        cls: okText(env.disk.ok),
      },
      {
        title: "系统",
        desc: `Windows ${esc(env.windows.release)} · ${esc(env.windows.machine)}`,
        value: env.windows.ok ? "支持" : "不支持",
        cls: okText(env.windows.ok),
      },
      {
        title: "文件夹路径",
        desc: env.path.ascii ? esc(env.path.value) : env.path.message,
        value: env.path.ascii ? "合格" : "不合格",
        cls: okText(env.path.ascii),
      },
    ];

    $("#envList").innerHTML = rows
      .map(
        (row) => `
      <li class="check-row">
        <i class="dot ${row.cls === "is-ok" ? "dot--ok" : row.cls === "is-bad" ? "dot--bad" : "dot--idle"}"></i>
        <div class="check-main"><b>${row.title}</b><small>${row.desc}</small></div>
        <span class="check-val ${row.cls}">${row.value}</span>
      </li>`
      )
      .join("");

    if (!env.path.ascii) {
      $("#pathBanner").hidden = false;
      $("#pathBannerPath").textContent = "当前路径：" + env.path.value;
    } else {
      $("#pathBanner").hidden = true;
    }
  }

  function renderPlan() {
    const plan = state.plan;
    if (!plan) return;
    const installed = plan.installed || state.demoInstalled;
    const badge = $("#installBadge");
    badge.textContent = installed ? "已就绪" : plan.stage === "partial" ? "装了一半" : "未安装";
    badge.className = "badge " + (installed ? "badge--ok" : plan.stage === "partial" ? "badge--warn" : "");

    const disk = $("#sumDisk");
    const down = $("#sumDown");
    if (installed) {
      const env = state.env || {};
      const sizes = env.sizes || {};
      const used = Math.round((sizes.pyenv_mb || 0) + (sizes.server_mb || 0) + (sizes.python_mb || 0));
      disk.innerHTML = `${used}<small>MB</small>`;
      down.innerHTML = `0<small>MB</small>`;
      $("#sumEta").innerHTML = `<span style="font-size:19px">已就绪</span>`;
      $("#sumEtaLabel").textContent = "状态";
    } else {
      disk.innerHTML = `${Math.round(plan.total_disk_mb)}<small>MB</small>`;
      down.innerHTML = `${plan.total_download_mb || 0}<small>MB</small>`;
      $("#sumEta").innerHTML = `<span style="font-size:19px">${esc(plan.eta)}</span>`;
      $("#sumEtaLabel").textContent = "预计耗时";
    }

    $("#depList").innerHTML = plan.steps
      .map((step) => {
        const done = step.status === "done";
        return `
        <li class="dep-item ${done ? "is-done" : ""}">
          <span class="mark">✓</span>
          <div><b>${esc(step.name)}</b><small>${esc(step.desc)}</small></div>
          <span class="dep-size">${done ? "已就绪" : step.download_mb ? `↓ ${step.download_mb} MB` : `${step.disk_mb} MB`}</span>
        </li>`;
      })
      .join("");

    const btn = $("#btnInstall");
    if (installed) {
      btn.innerHTML = `<svg class="ic"><use href="#i-refresh"/></svg>重新检查环境`;
      btn.dataset.mode = "recheck";
    } else {
      btn.innerHTML = `<svg class="ic"><use href="#i-play"/></svg>开始安装`;
      btn.dataset.mode = "install";
    }
  }

  function renderKeyState() {
    const has = Boolean(state.settings && state.settings.keys && state.settings.keys.bailian);
    const hint = $("#keyHint");
    if (hint) {
      hint.textContent = has ? `已配置（${state.settings.keys.bailian}）` : "还没配置";
      hint.className = "field-hint " + (has ? "is-ok" : "");
    }
    const input = $("#keyInput");
    if (!input) return;
    input.placeholder = has ? "已保存，留空表示不改" : "sk-…";
    if (has && !input.value) input.placeholder = state.settings.keys.bailian + "（已保存）";
  }

  // --------------------------------------------------------------- 安装

  function confirmInstall() {
    const plan = state.plan;
    if (!plan) return;
    const rows = plan.steps
      .map(
        (s) => `<tr>
          <td>${esc(s.name)}<br><small class="muted">${esc(s.desc)}</small></td>
          <td>${s.status === "done" ? '<span class="ok">已就绪</span>' : s.download_mb ? "下载 " + s.download_mb + " MB" : s.disk_mb + " MB"}</td>
        </tr>`
      )
      .join("");
    openModal({
      title: "确认安装",
      hint: "安装不会读取、也不会修改你电脑上已装的 Python。",
      okText: "开始安装",
      body: `
        <p class="confirm-lead">即将在 <span class="mono">${esc(plan.path.value)}</span> 安装运行环境，预计 ${esc(plan.eta)}，需要联网。</p>
        <table class="confirm-table">${rows}</table>
        <div class="confirm-total"><span>磁盘合计</span><b>${fmtMb(plan.total_disk_mb)}</b></div>
        <p class="confirm-note">安装过程中可以继续用电脑。中途断了也没关系，重新点一次会从断点继续。</p>`,
      onOk: () => {
        closeModal();
        startInstall();
      },
    });
  }

  async function startInstall() {
    if (DEMO) return simulateInstall();
    const res = await api("/api/install/start", {
      method: "POST",
      body: { confirmed: true },
    });
    if (!res.ok) {
      toast("bad", "没能开始安装", res.message || "稍后再试一次");
      return;
    }
    showProgress();
    pollInstall(res);
  }

  let installTimer = null;

  function stopInstallPolling() {
    if (installTimer) {
      clearInterval(installTimer);
      installTimer = null;
    }
  }

  function showProgress() {
    state.installing = true;
    stopInstallPolling();
    $("#installActions").hidden = true;
    $("#progressWrap").hidden = false;
    $("#stepList").innerHTML = "";
    setProgress(0, "准备中…", "正在检查环境");
  }

  function renderProgress(snap) {
    const steps = snap.steps || [];
    const list = $("#stepList");
    if (steps.length) {
      if (list.children.length !== steps.length) {
        list.innerHTML = steps
          .map(
            (s, i) => `<li class="step" data-state="pending" data-i="${i}">
              <span class="sdot"></span>
              <span><b style="font-weight:600">${esc(s.name)}</b><br><small class="muted">${esc(
              s.detail || ""
            )}</small></span>
              <span class="stime"></span>
            </li>`
          )
          .join("");
      }
      steps.forEach((s, i) => {
        const el = list.children[i];
        if (!el) return;
        el.dataset.state = s.state === "running" ? "active" : s.state === "error" ? "error" : s.state;
        const small = el.querySelector("small");
        if (small) small.textContent = s.detail || "";
      });
    }
    const pct = Number(snap.percent || 0);
    setProgress(pct, snap.message || "", snap.hint || "");
    const spin = $("#progressSpin");
    if (spin) spin.hidden = Boolean(snap.finished);
    if ($("#showInstallWindow").checked && snap.logs && snap.logs.length) {
      $("#installLog").hidden = false;
      $("#installLog").textContent = snap.logs.slice(-80).join("\n");
      $("#installLog").scrollTop = $("#installLog").scrollHeight;
    }
  }

  async function pollInstall(first) {
    let snap = first;
    const tick = async () => {
      if (!snap || snap.finished) return;
      snap = await api("/api/install/progress");
      renderProgress(snap);
      if (snap.finished) {
        stopInstallPolling();
        state.installing = false;
        if (snap.state === "done") {
          // 收尾：等环境自检真的变绿再收进度条，避免"闪回需要下载"
          setProgress(100, "安装完成，正在做最后检查…", "最多等 10 秒，不用重复点安装");
          let ready = false;
          try {
            for (let i = 0; i < 12; i++) {
              try {
                await refreshAll();
              } catch (e) {
                /* 忽略单次刷新失败 */
              }
              if (state.env && state.env.installed) {
                ready = true;
                break;
              }
              await sleep(800);
            }
          } finally {
            $("#progressWrap").hidden = true;
            $("#installActions").hidden = false;
          }
          if (ready) {
            toast("ok", "安装完成", "接下来填一个百炼 API Key 就能用了");
            go("config");
          } else {
            toast("info", "文件装好了", "环境还在自检，点「重新检查环境」即可");
          }
        } else if (snap.state === "cancelled") {
          $("#progressWrap").hidden = true;
          $("#installActions").hidden = false;
          toast("info", "已取消", "随时可以重新开始");
        } else {
          $("#progressWrap").hidden = true;
          $("#installActions").hidden = false;
          toast("bad", snap.error || "安装失败", snap.hint || "看日志里的最后几行");
        }
      }
    };
    renderProgress(snap);
    installTimer = setInterval(tick, 900);
    await tick();
  }

  function setProgress(pct, title, note) {
    $("#progressBar").style.width = Math.min(100, Math.max(0, pct)) + "%";
    $("#progressPct").textContent = Math.round(pct) + "%";
    if (title) $("#progressTitle").textContent = title;
    if (note) $("#progressNote").textContent = note;
  }

  function activateStep(index, stateName) {
    $$("#stepList .step").forEach((el) => {
      const i = Number(el.dataset.i);
      if (i === index) el.dataset.state = stateName;
      else if (i < index) el.dataset.state = "done";
    });
  }

  async function simulateInstall() {
    const steps = state.plan ? state.plan.steps : [];
    showProgress();
    $("#stepList").innerHTML = steps
      .map(
        (step, i) => `<li class="step" data-state="${i === 0 ? "active" : "pending"}" data-i="${i}">
          <span class="sdot"></span>
          <span><b style="font-weight:600">${esc(step.name)}</b><br><small class="muted">${esc(
          step.desc
        )}</small></span>
          <span class="stime"></span>
        </li>`
      )
      .join("");
    let pct = 0;
    for (let i = 0; i < steps.length; i += 1) {
      const step = steps[i];
      activateStep(i, "active");
      $("#progressTitle").textContent = `第 ${i + 1}/${steps.length} 步 · ${step.name}`;
      const total = i === 2 ? 46 : 18;
      for (let t = 0; t <= total; t += 2) {
        pct = ((i + t / total) / steps.length) * 100;
        setProgress(pct, "", i === 2 ? `已下载 ${Math.round((t / total) * 170)} / 170 MB` : step.desc);
        await sleep(60);
      }
      activateStep(i, "done");
    }
    setProgress(100, "安装完成", "所有组件都准备好了");
    state.demoInstalled = true;
    await sleep(400);
    state.installing = false;
    $("#installActions").hidden = false;
    $("#progressWrap").hidden = true;
    state.env.installed = true;
    state.env.stage = "ready";
    state.plan.installed = true;
    state.plan.steps.forEach((s) => (s.status = "done"));
    renderEnv();
    renderPlan();
    paintPills();
    toast("ok", "安装完成", "接下来填一个百炼 API Key 就能用了");
    go("config");
  }

  // --------------------------------------------------------------- 配置页

  const HIDDEN_VENDORS = ["kimi", "minimax"];

  function vendorOrder() {
    // 面板不再展示 kimi / minimax（后端 VENDORS 与 FALLBACK_VENDORS 定义仍保留）
    return Object.keys(state.vendors).filter((key) => !HIDDEN_VENDORS.includes(key));
  }

  function renderVendors() {
    const seg = $("#vendorSeg");
    const current = (state.settings && state.settings.brain.vendor) || "bailian";
    seg.innerHTML = vendorOrder()
      .map(
        (key) =>
          `<button class="seg-btn" role="tab" data-vendor="${key}" aria-selected="${key === current}">${esc(
            state.vendors[key].label
          )}</button>`
      )
      .join("");
  }

  function applyVendor(key, { keepModel = false, keepKey = false } = {}) {
    const _bk = $("#cfgBrainKey");
    if (_bk && !keepKey) _bk.value = "";
    const vendor = state.vendors[key];
    if (!vendor) return;
    const sameBailianKey = key === "bailian";
    hideModelPicker();
    $$(".seg-btn").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.vendor === key)));
    if (vendor.base_url) $("#cfgBaseUrl").value = vendor.base_url;
    if (!keepModel && vendor.model) $("#cfgModel").value = vendor.model;
    $("#modelHint").textContent =
      key === "bailian"
        ? "默认 deepseek-v4.1-flash-1017（百炼上的 DeepSeek）：便宜、够用。"
        : vendor.key_hint || "";
    $("#brainKeyHint").textContent = sameBailianKey
      ? "百炼用上面那个 Key，这里留空就行。"
      : "这一家需要单独填 Key（和千问AI平台不是同一个）。";
    $("#cfgBrainKey").placeholder = sameBailianKey ? "留空 = 用上面的千问AI平台 Key" : "填这一家的 API Key";
    updateSummaries();
    markDirty();
  }

  function hideModelPicker() {
    const wrap = $("#modelPickWrap");
    if (wrap) wrap.hidden = true;
    const pick = $("#cfgModelPick");
    if (pick) pick.innerHTML = "";
  }

  function renderSettings() {
    const s = state.settings;
    if (!s) return;
    state.vendors = (s._meta && s._meta.vendors) || FALLBACK_VENDORS;

    $("#cfgKey").value = s.keys.bailian || "";
    $("#cfgKey").placeholder = s.keys.bailian ? "已保存（改这里会覆盖）" : "sk-…";

    $("#cfgSpeed").value = s.voice.speed;
    updateRange($("#cfgSpeed"), $("#speedVal"), s.voice.speed + "×");
    $("#cfgTtsModel").value = s.voice.tts_model;
    $("#cfgAsrModel").value = s.asr.model;
    $("#cfgVoiceCustom").value = "";
    renderVoiceOptions(s.voice.tts_model, s.voice.voice_id);

    renderVendors();
    $("#cfgBaseUrl").value = s.brain.base_url;
    $("#cfgModel").value = s.brain.model;
    $("#cfgTemp").value = s.brain.temperature;
    updateRange($("#cfgTemp"), $("#tempVal"), Number(s.brain.temperature).toFixed(1));
    $("#cfgMaxTokens").value = s.brain.max_tokens;
    $("#cfgMemory").checked = Boolean(s.persona.memory);

    renderTags(s.persona.wakeup_words || []);
    $("#cfgPrompt").value = s.persona.prompt;
    updatePromptCount();

    $("#voiceHint").textContent =
      findVoice($("#cfgTtsModel").value, s.voice.voice_id) ? "点「试听」听一下，确认没问题再保存。" : "选一个顺耳的声音，或者填自己的音色 ID。";

    applyVendor(s.brain.vendor, { keepModel: true, keepKey: true });
    const savedBrainKey = s.brain.api_key || "";
    $("#cfgBrainKey").value = savedBrainKey;
    if (savedBrainKey) $("#cfgBrainKey").placeholder = "已保存（改这里会覆盖）";
    updateSummaries();
    state.baseline = JSON.stringify(collect());
    state.dirty = false;
    paintDirty();
  }

  function updateSummaries() {
    const ttsMap = { "qwen-audio-3.1-tts-flash": "Qwen-Audio TTS" };
    const asrMap = { "fun-asr-realtime": "Fun-ASR 实时", "paraformer-realtime-v2": "Paraformer（旧）", "qwen3-asr-flash": "Qwen3 ASR" };
    const tts = ttsMap[$("#cfgTtsModel").value] || $("#cfgTtsModel").value;
    const asr = asrMap[$("#cfgAsrModel").value] || $("#cfgAsrModel").value;
    const customVoice = $("#cfgVoiceCustom").value.trim();
    const model = $("#cfgTtsModel").value;
    const voice = customVoice
      ? "自定义音色"
      : (findVoice(model, $("#cfgVoice").value) || {}).name || "音色";
    const voiceEl = $("#voiceSummary");
    if (voiceEl) voiceEl.textContent = `识别 ${asr} · 合成 ${tts} · ${voice} · 24 kHz`;

    const seg = $$(".seg-btn").find((b) => b.getAttribute("aria-selected") === "true");
    const vendor = (state.vendors && seg && state.vendors[seg.dataset.vendor]) || {};
    const brainEl = $("#brainSummary");
    if (brainEl)
      brainEl.textContent = `${vendor.label || "自定义"} · ${$("#cfgModel").value.trim() || "还没填模型"}`;
  }

  function collect() {
    const out = {
      voice: {
        tts_model: $("#cfgTtsModel").value,
        voice_id: $("#cfgVoiceCustom").value.trim() || $("#cfgVoice").value,
        speed: Number($("#cfgSpeed").value),
        volume: 50,
      },
      asr: { model: $("#cfgAsrModel").value },
      brain: {
        mode: "gateway",
        // 被隐藏的供应商（kimi/minimax）不会有按钮被选中，这里沿用已保存的 vendor，避免静默改成 bailian
        vendor:
          ($$(".seg-btn").find((b) => b.getAttribute("aria-selected") === "true") || {}).dataset?.vendor ||
          (state.settings && state.settings.brain.vendor) ||
          "bailian",
        base_url: $("#cfgBaseUrl").value.trim(),
        model: $("#cfgModel").value.trim(),
        temperature: Number($("#cfgTemp").value),
        max_tokens: Number($("#cfgMaxTokens").value) || 300,
      },
      persona: {
        prompt: $("#cfgPrompt").value,
        wakeup_words: currentTags(),
        memory: $("#cfgMemory").checked,
      },
    };
    const key = $("#cfgKey").value.trim();
    if (key) out.keys = { bailian: key };
    const brainKey = $("#cfgBrainKey").value.trim();
    out.brain.api_key = brainKey;
    return out;
  }

  function markDirty() {
    if (!state.baseline) return;
    state.dirty = JSON.stringify(collect()) !== state.baseline;
    paintDirty();
  }

  function paintDirty() {
    const btn = $("#btnSaveCfg");
    btn.disabled = !state.dirty;
    const dot = $("#dirtyDot");
    dot.className = "dot " + (state.dirty ? "dot--warn" : "dot--ok");
    $("#saveInfo").textContent = state.dirty ? "有改动还没保存" : "所有改动都保存了";
  }

  async function saveSettings() {
    if (!state.dirty) return;
    const btn = $("#btnSaveCfg");
    btn.disabled = true;
    btn.textContent = "保存中…";
    const patch = collect();
    const res = await api("/api/settings", { method: "POST", body: { settings: patch } });
    btn.textContent = "保存";
    if (!res.ok) {
      toast("bad", "保存失败", res.message || "看看日志里怎么说");
      btn.disabled = false;
      return;
    }
    state.settings = res.settings;
    state.baseline = JSON.stringify(collect());
    state.dirty = false;
    paintDirty();
    renderKeyState();

    const changed = res.changed || [];
    if (!changed.length) {
      toast("ok", "没有改动", "配置和保存前一样");
      return;
    }
    const needRestart = res.restart && (res.restart.gateway || res.restart.server);
    if (needRestart) {
      const targets = [res.restart.gateway ? "LLM 配置" : "", res.restart.server ? "语音服务" : ""]
        .filter(Boolean)
        .join(" + ");
      $("#saveInfo").textContent = `已保存。需要重启${targets}（${res.eta}）`;
      toast("ok", "已保存", `要重启${targets}才会生效，${res.eta}`);
      confirmRestart(res);
    } else {
      const note = (res.notes || [])[0] || "下一句话就生效";
      $("#saveInfo").textContent = "已保存，" + note;
      toast("ok", "已保存", note);
    }
    refreshAll();
  }

  function confirmRestart(res) {
    openModal({
      title: "保存好了，要现在重启吗？",
      hint: "只重启受影响的部分；提示词类改动本来就不需要重启。",
      okText: "立即重启",
      body: `
        <p class="confirm-lead">这次改动的项目需要重启才会生效。</p>
        <table class="confirm-table">
          <tr><td>LLM 配置</td><td>${res.restart.gateway ? "重启（约 2 秒，机器狗不掉线）" : "不用动"}</td></tr>
          <tr><td>语音服务</td><td>${res.restart.server ? "重启（约 30 秒，机器狗会断线重连）" : "不用动"}</td></tr>
        </table>
        <div class="confirm-total"><span>预计耗时</span><b>${esc(res.eta || "")}</b></div>`,
      onOk: async () => {
        closeModal();
        const out = await api("/api/service/restart", { method: "POST", body: {} });
        if (!out.ok) toast("bad", "重启没成功", out.message || "");
        else toast("ok", "已发出重启", "状态会自动刷新");
        refreshStatus();
      },
    });
  }

  // --------------------------------------------------------------- 标签输入

  let tags = [];

  function currentTags() {
    return tags.slice();
  }

  function renderTags(list) {
    tags = list.slice();
    const box = $("#wakeTags");
    if (!box) return;
    box.innerHTML = tags
      .map(
        (t, i) =>
          `<span class="tag">${esc(t)}<button type="button" data-tag="${i}" title="删除">✕</button></span>`
      )
      .join("");
  }

  function addTag() {
    const input = $("#wakeInput");
    if (!input) return;
    const value = input.value.trim();
    if (!value) return;
    if (tags.includes(value)) {
      toast("info", "已经加过了", value);
      input.value = "";
      return;
    }
    tags.push(value);
    input.value = "";
    renderTags(tags);
    markDirty();
  }

  // --------------------------------------------------------------- 滑块 / 字数

  function updateRange(input, label, text) {
    const min = Number(input.min);
    const max = Number(input.max);
    const val = Number(input.value);
    const pct = ((val - min) / (max - min)) * 100;
    input.style.setProperty("--pct", pct + "%");
    if (label) label.textContent = text;
  }

  function updatePromptCount() {
    $("#promptCount").textContent = `${$("#cfgPrompt").value.length} 字`;
  }

  // --------------------------------------------------------------- 运行页

  async function refreshStatus() {
    const res = await api("/api/service/status");
    if (res.ok) {
      state.status = res;
      renderStatus();
      paintPills();
    }
  }

  function renderStatus() {
    const st = state.status;
    if (!st) return;
    const gw = st.gateway;
    const srv = st.server;
    const running = gw.running || srv.running || (state.status && state.status.mqttgw && state.status.mqttgw.running);
    const starting = state.installing || gw.state === "starting" || srv.state === "starting";
    const stalled = gw.state === "stalled" || srv.state === "stalled";
    const busy = !running && (gw.state === "port_busy" || srv.state === "port_busy");

    const ring = $("#runRing");
    ring.className = "run-ring" + (running && !stalled ? " is-on" : starting || stalled ? " is-busy" : "");
    $("#runTitle").textContent = stalled
      ? "启动超时了"
      : running
      ? "服务运行中"
      : starting
      ? "正在启动…"
      : busy
      ? "端口被占用"
      : "服务已停止";
    $("#runSub").textContent = stalled
      ? "超过 90 秒还没监听端口。看下面的日志，或点「停止」后重来一次。"
      : running
      ? `已经跑了 ${fmtUptime(Math.max(gw.uptime, srv.uptime))}。`
      : busy
      ? "上次可能有进程没关干净。点「停止」清理一下，再启动。"
      : "点「启动服务」，第一次可能要 30–60 秒，好了会自动刷新。";

    $("#btnStart").disabled = running || starting;
    $("#btnStop").disabled = !running && !busy;

    const label = {
      running: "运行中",
      starting: "启动中",
      stalled: "启动超时",
      port_busy: "端口被占用",
      stopped: "未运行",
    };
    const stateCls = (s) => (s === "running" ? " dot--live" : s === "starting" ? " dot--warn" : s === "port_busy" ? " dot--warn" : "");
    if ($("#gwState")) {
      $("#gwState").textContent = label[gw.state] || "未运行";
      $("#gwState").className = gw.state === "running" ? "is-on" : "";
    }
    $("#srvState").textContent = label[srv.state] || "未运行";
    $("#srvState").className = srv.state === "running" ? "is-on" : "";
    const mq = (state.status && state.status.mqttgw) || { state: "stopped", running: false };
    const mqEl = $("#mqState");
    if (mqEl) {
      mqEl.textContent = label[mq.state] || "未运行";
      mqEl.className = mq.state === "running" ? "is-on" : "";
      const dot = $("#procMq") && $("#procMq").querySelector(".dot");
      if (dot) dot.className = "dot " + (mq.state === "running" ? "dot--ok" : mq.state === "stopped" ? "dot--idle" : "dot--warn") + stateCls(mq.state);
    }
    if ($("#procGw")) {
      $("#procGw").querySelector(".dot").className =
        "dot " + (gw.state === "running" ? "dot--ok" : gw.state === "stopped" ? "dot--idle" : "dot--warn") + stateCls(gw.state);
    }
    $("#procSrv").querySelector(".dot").className =
      "dot " + (srv.state === "running" ? "dot--ok" : srv.state === "stopped" ? "dot--idle" : "dot--warn") + stateCls(srv.state);

    const cfg = state.settings;
    if (cfg) {
      if ($("#gwPort")) $("#gwPort").textContent = cfg.ports.gateway;
      $("#srvPort").textContent = `${cfg.ports.ota} / ${cfg.ports.ws}`;
      if ($("#mqPort")) $("#mqPort").textContent = `${cfg.ports.mqtt || 1883} / UDP ${cfg.ports.mqtt || 1883}`;
    }

    const dev = st.device || { count: 0 };
    if (dev.count > 0) {
      $("#deviceEmpty").hidden = true;
      $("#deviceCard").hidden = false;
      $("#deviceName").textContent = `已连接 ${dev.count} 台`;
      $("#deviceSeen").textContent = dev.ips && dev.ips.length ? dev.ips.join("、") : "—";
      $("#deviceCard").querySelector(".badge").textContent = "在线";
    } else {
      $("#deviceEmpty").hidden = false;
      $("#deviceCard").hidden = true;
    }
  }

  function fmtClock(ts) {
    if (!ts) return "—";
    const d = new Date(Number(ts) * 1000);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(
      d.getSeconds()
    ).padStart(2, "0")}`;
  }

  async function loadOta() {
    const res = await api("/api/net/ota");
    if (!res.ok) return;
    state.ota = res;
    state.adapters = res.adapters || [];
    const select = $("#adapterSelect");
    const current = select.value;
    select.innerHTML = (res.urls || [])
      .map(
        (u) =>
          `<option value="${u.ip}">${esc(u.name || "网卡")} · ${u.ip}${u.recommended ? "（推荐）" : ""}</option>`
      )
      .join("");
    if (current && (res.urls || []).some((u) => u.ip === current)) select.value = current;
    paintOta();
  }

  function paintOta() {
    const ip = $("#adapterSelect").value;
    const item = (state.ota?.urls || []).find((u) => u.ip === ip);
    if (item) {
      $("#otaUrl").textContent = item.url;
      $("#adapterHint").textContent = item.virtual
        ? "这张看起来像虚拟网卡，机器狗可能连不上；换一张实体网卡试试。"
        : "机器狗和这台电脑要在同一个 Wi-Fi。";
    }
  }

  async function copyOta() {
    const text = $("#otaUrl").textContent;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    const btn = $("#btnCopyOta");
    btn.classList.add("is-done");
    btn.innerHTML = `<svg class="ic"><use href="#i-check"/></svg>`;
    toast("ok", "已复制", "粘到机器狗配网页面的 OTA 地址里");
    setTimeout(() => {
      btn.classList.remove("is-done");
      btn.innerHTML = `<svg class="ic"><use href="#i-copy"/></svg>`;
    }, 1600);
  }

  async function runSelftest() {
    const btn = $("#btnSelftest");
    btn.disabled = true;
    btn.innerHTML = `<svg class="ic"><use href="#i-refresh"/></svg>检查中…`;
    $("#selftestList").innerHTML = `
      <li class="sk-row"></li><li class="sk-row"></li><li class="sk-row"></li>`;
    const res = await api("/api/selftest");
    btn.disabled = false;
    btn.innerHTML = `<svg class="ic"><use href="#i-refresh"/></svg>运行自检`;
    if (!res.ok) {
      toast("bad", "自检失败", res.message || "");
      return;
    }
    const checks = res.checks || [];
    $("#selftestList").innerHTML = checks
      .map((c) => {
        const map = { ok: "dot--ok", fail: "dot--bad", warn: "dot--warn", skip: "dot--idle" };
        const label = { ok: "正常", fail: "有问题", warn: "注意", skip: "跳过" }[c.state] || c.state;
        return `<li class="check-row">
          <i class="dot ${map[c.state] || "dot--idle"}"></i>
          <div class="check-main"><b>${esc(c.title)}</b><small>${esc(c.detail || "")}${
          c.hint ? " · " + esc(c.hint) : ""
        }</small></div>
          <span class="check-val ${c.state === "ok" ? "is-ok" : c.state === "fail" ? "is-bad" : ""}">${label}</span>
        </li>`;
      })
      .join("");
    if (res.overall === "ok") toast("ok", "全部正常", "可以跟机器狗说话了");
    else toast("bad", "还有问题", "看红色的那几项");
  }

  // --------------------------------------------------------------- 日志

  function classify(line) {
    const up = line.toUpperCase();
    if (up.includes("ERROR") || up.includes("EXCEPTION") || up.includes("TRACEBACK")) return "l-err";
    if (up.includes("WARNING") || up.includes("WARN")) return "l-warn";
    if (up.includes("TTS") || up.includes("ASR")) return "l-ok";
    if (up.includes("DEBUG")) return "l-dim";
    return "";
  }

  async function loadLogs() {
    if (!$("#logsToggle").checked) return;
    const name = state.page === "run" ? "server" : "panel";
    const q = new URLSearchParams({
      name,
      lines: String(state.logLines),
      pattern: state.logFilter,
    });
    const res = await api("/api/logs?" + q.toString());
    const box = $("#logConsole");
    box.hidden = false;
    if (!res.ok || !res.exists || !(res.lines || []).length) {
      box.innerHTML = `<span class="log-empty">${res.message || "还没有日志。启动服务后这里会有内容。"}</span>`;
      return;
    }
    box.innerHTML = res.lines
      .map((line) => {
        const cls = classify(line);
        return `<span class="${cls}">${esc(line)}</span>`;
      })
      .join("\n");
    box.scrollTop = box.scrollHeight;
  }

  // --------------------------------------------------------------- 数据刷新

  async function refreshAll() {
    const [health, env, plan, settingsRes] = await Promise.all([
      api("/api/health"),
      api("/api/env"),
      api("/api/install/plan"),
      api("/api/settings"),
    ]);
    if (health.ok) state.health = health;
    if (env) state.env = env;
    if (plan) state.plan = plan;
    if (settingsRes.ok) state.settings = settingsRes.settings;
    renderEnv();
    renderPlan();
    renderKeyState();
    if (state.settings) renderSettings();
    await refreshStatus();
    paintPills();
  }

  async function recheck() {
    const btn = $("#btnRecheck");
    btn.disabled = true;
    btn.innerHTML = `<svg class="ic"><use href="#i-refresh"/></svg>检测中`;
    const [env, plan] = await Promise.all([api("/api/env"), api("/api/install/plan")]);
    if (env) state.env = env;
    if (plan) state.plan = plan;
    renderEnv();
    renderPlan();
    paintPills();
    btn.disabled = false;
    btn.innerHTML = `<svg class="ic"><use href="#i-refresh"/></svg>重新检测`;
    toast("info", "已重新检测", env && env.installed ? "环境没问题" : "还有没装好的项");
  }

  // --------------------------------------------------------------- 绑定

  function bind() {
    $$(".nav-item").forEach((btn) => btn.addEventListener("click", () => go(btn.dataset.nav)));
    $$("[data-goto]").forEach((btn) => btn.addEventListener("click", () => go(btn.dataset.goto)));

    $("#btnRecheck").addEventListener("click", recheck);
    $("#btnInstall").addEventListener("click", () => {
      if ($("#btnInstall").dataset.mode === "recheck") return recheck();
      confirmInstall();
    });
    $("#btnCancelInstall").addEventListener("click", async () => {
      if (DEMO) {
        state.installing = false;
        $("#progressWrap").hidden = true;
        $("#installActions").hidden = false;
        toast("info", "已取消", "随时可以重新开始");
        return;
      }
      await api("/api/install/cancel", { method: "POST", body: {} });
      stopInstallPolling();
      setTimeout(async () => {
        const snap = await api("/api/install/progress");
        if (snap.finished) {
          state.installing = false;
          $("#progressWrap").hidden = true;
          $("#installActions").hidden = false;
          toast("info", "已取消", "已经装好的部分会保留");
        }
      }, 1200);
    });
    $("#showInstallWindow").addEventListener("change", async (e) => {
      $("#installLog").hidden = !e.target.checked;
      if (e.target.checked) {
        if (DEMO) {
          $("#installLog").textContent = "[演示] 这里会显示 pip 的实时输出。";
          return;
        }
        const snap = await api("/api/install/progress");
        if (snap.logs) {
          $("#installLog").textContent = snap.logs.slice(-80).join("\n");
          $("#installLog").scrollTop = $("#installLog").scrollHeight;
        }
      }
    });

    $$("[data-toggle-pw]").forEach((btn) =>
      btn.addEventListener("click", () => {
        const input = document.getElementById(btn.dataset.togglePw);
        const isPw = input.type === "password";
        input.type = isPw ? "text" : "password";
        btn.innerHTML = `<svg class="ic"><use href="${isPw ? "#i-eye-off" : "#i-eye"}"/></svg>`;
      })
    );

    $("#vendorSeg").addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn) return;
      applyVendor(btn.dataset.vendor);
    });

    $("#btnFetchModels").addEventListener("click", async () => {
      const btn = $("#btnFetchModels");
      btn.disabled = true;
      btn.textContent = "获取中…";
      // 留空交给服务端用本机已存的 Key（不要把脱敏的 **** 拼成假 Key）
      const key = $("#cfgBrainKey").value.trim() || $("#cfgKey").value.trim();
      const res = await api("/api/llm/models", {
        method: "POST",
        body: { base_url: $("#cfgBaseUrl").value.trim(), api_key: key },
      });
      btn.disabled = false;
      btn.textContent = "获取列表";
      if (!res.ok) return toast("bad", "没拉到模型列表", res.message || "可以直接手填模型名");
      const models = res.models || [];
      $("#modelList").innerHTML = models.map((m) => `<option value="${esc(m)}"></option>`).join("");
      const wrap = $("#modelPickWrap");
      const pick = $("#cfgModelPick");
      pick.innerHTML =
        `<option value="" disabled selected>从列表里选一个（共 ${models.length} 个）</option>` +
        models.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join("");
      wrap.hidden = false;
      const current = $("#cfgModel").value.trim();
      if (current && models.includes(current)) pick.value = current;
      toast("ok", "拿到了", `共 ${models.length} 个模型，在下面的下拉里选`);
    });

    $("#cfgModelPick").addEventListener("change", (e) => {
      if (!e.target.value) return;
      $("#cfgModel").value = e.target.value;
      updateSummaries();
      markDirty();
    });

    $("#btnTestBrain").addEventListener("click", async () => {
      const btn = $("#btnTestBrain");
      const out = $("#brainTestResult");
      const base = $("#cfgBaseUrl").value.trim();
      btn.disabled = true;
      btn.textContent = "测试中…";
      out.className = "field-hint";
      out.textContent = "正在连接 " + (base || "…");
      const res = await api("/api/llm/models", {
        method: "POST",
        body: { base_url: base, api_key: $("#cfgBrainKey").value.trim() },
      });
      btn.disabled = false;
      btn.textContent = "测试连接";
      if (res.ok) {
        out.className = "field-hint is-ok";
        out.textContent = `连接正常，看到 ${res.models.length} 个模型`;
      } else {
        out.className = "field-hint is-bad";
        out.textContent = res.message || "连接失败，检查地址和 Key";
      }
    });

    $("#btnPreview").addEventListener("click", async () => {
      const wave = $("#previewWave");
      const btn = $("#btnPreview");
      if (DEMO) {
        wave.classList.add("is-on");
        toast("info", "演示模式不出声", "真实环境里会合成一句给你听");
        setTimeout(() => wave.classList.remove("is-on"), 2200);
        return;
      }
      btn.disabled = true;
      btn.textContent = "生成中…";
      const res = await api("/api/voice/preview", {
        method: "POST",
        body: {
          voice: $("#cfgVoiceCustom").value.trim() || $("#cfgVoice").value,
          model: $("#cfgTtsModel").value,
        },
      });
      btn.disabled = false;
      btn.innerHTML = `<svg class="ic"><use href="#i-sound"/></svg>试听`;
      if (!res.ok) {
        toast("bad", "试听失败", (res.message || "") + (res.detail ? `（${res.detail}）` : ""));
        return;
      }
      wave.classList.add("is-on");
      const audio = new Audio(res.url + "&t=" + Date.now());
      const stop = () => wave.classList.remove("is-on");
      audio.onended = stop;
      audio.onerror = () => {
        stop();
        toast("bad", "播放失败", "浏览器拦了音频？先点一下页面再试");
      };
      try {
        await audio.play();
      } catch {
        stop();
        toast("bad", "播放被拦下了", "点一下页面任意位置，再点试听");
      }
    });

    $("#cfgSpeed").addEventListener("input", (e) =>
      updateRange(e.target, $("#speedVal"), Number(e.target.value).toFixed(1) + "×")
    );
    $("#cfgTemp").addEventListener("input", (e) =>
      updateRange(e.target, $("#tempVal"), Number(e.target.value).toFixed(1))
    );
    $("#cfgPrompt").addEventListener("input", updatePromptCount);
    $("#cfgVoice").addEventListener("change", (e) => {
      const v = findVoice($("#cfgTtsModel").value, e.target.value);
      $("#voiceHint").textContent = v ? "点「试听」听一下，确认没问题再保存。" : "自定义音色，记得先试听确认能用。";
    });
    $("#cfgTtsModel").addEventListener("change", (e) => {
      const list = voicesFor(e.target.value);
      renderVoiceOptions(e.target.value, list[0] ? list[0].id : "");
      $("#voiceHint").textContent = list[0] ? list[0].desc : "";
      updateSummaries();
      markDirty();
    });

    ["#cfgKey", "#cfgVoice", "#cfgVoiceCustom", "#cfgSpeed", "#cfgTtsModel", "#cfgAsrModel",
      "#cfgBaseUrl", "#cfgModel", "#cfgBrainKey", "#cfgTemp", "#cfgMaxTokens",
      "#cfgPrompt", "#cfgMemory"].forEach((sel) => {
      const el = $(sel);
      if (el) el.addEventListener("input", markDirty);
      if (el) el.addEventListener("change", markDirty);
    });
    ["#cfgVoice", "#cfgVoiceCustom", "#cfgTtsModel", "#cfgAsrModel", "#cfgModel", "#cfgMemory"].forEach(
      (sel) => {
        const el = $(sel);
        if (el) el.addEventListener("change", updateSummaries);
        if (el) el.addEventListener("input", updateSummaries);
      }
    );

    if ($("#btnAddWake")) {
      $("#btnAddWake").addEventListener("click", addTag);
      $("#wakeInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          addTag();
        }
      });
      $("#wakeTags").addEventListener("click", (e) => {
        const btn = e.target.closest("button[data-tag]");
        if (!btn) return;
        tags.splice(Number(btn.dataset.tag), 1);
        renderTags(tags);
        markDirty();
      });
    }

    $("#btnResetPersona").addEventListener("click", () => {
      $("#cfgPrompt").value =
        (state.settings._meta && state.settings._meta.default_prompt) ||
        "你是一只机器狗。";
      renderTags(["小兵小兵"]);
      updatePromptCount();
      markDirty();
    });

    $("#btnSaveCfg").addEventListener("click", saveSettings);
    $("#btnReloadCfg").addEventListener("click", async () => {
      const res = await api("/api/settings");
      if (res.ok) {
        state.settings = res.settings;
        renderSettings();
        toast("info", "已重新读取", "还没保存的改动被丢掉了");
      }
    });

    $("#btnStart").addEventListener("click", async () => {
      state.installing = true;
      renderStatus();
      const res = await api("/api/service/start", { method: "POST", body: {} });
      if (!res.ok) {
        state.installing = false;
        renderStatus();
        if (res.code === "port_occupied") {
          offerPortChange(res);
        } else if (res.code === "server_failed") {
          openModal({
            title: "语音服务没起来",
            hint: "下面是服务端日志的最后几行。",
            okText: "知道了",
            body: `
              <p class="confirm-lead">${esc(res.message || "")}</p>
              <p class="confirm-note">${esc(res.hint || "")}</p>
              <pre class="console console--paper" style="max-height:260px;margin-top:12px">${esc(
                (res.log || []).join("\n")
              )}</pre>`,
          });
        } else {
          toast("bad", "启动没成功", res.message || "");
        }
        return;
      }
      if (res.ports_changed) {
        toast(
          "bad",
          "端口换了，要重新填 OTA",
          res.message || "系统保留了原端口，已自动换一个"
        );
        await refreshAll();
        await loadOta();
      } else {
        toast("ok", "正在启动", "大约 30 秒，好了会自动刷新");
      }
      setTimeout(async () => {
        state.installing = false;
        await refreshStatus();
      }, 2000);
    });

    function offerPortChange(res) {
      const items = [];
      const ports = res.ports || {};
      Object.keys(ports).forEach((port) => {
        (ports[port].listeners || []).forEach((l) => {
          items.push(
            `<tr><td>${port}</td><td>${esc(l.name || "未知程序")}（pid ${l.pid}）</td></tr>`
          );
        });
      });
      const suggest = res.suggest || {};
      openModal({
        title: "端口被占用了",
        hint: "换端口后 OTA 地址会变，需要重新填到机器狗里。",
        okText: "换端口并启动",
        body: `
          <p class="confirm-lead">${esc(res.message || "")}</p>
          <table class="confirm-table">${items.join("")}</table>
          <div class="confirm-total"><span>建议改用</span><b>OTA ${suggest.ota || "?"} / WS ${
          suggest.ws || "?"
        }</b></div>
          <p class="confirm-note">如果占用端口的是别的软件（比如另一个小智服务端），也可以先关掉它再点启动。</p>`,
        onOk: async () => {
          closeModal();
          const moved = await api("/api/service/relocate", { method: "POST", body: {} });
          if (!moved.ok) return toast("bad", "换端口失败", moved.message || "");
          toast("ok", "端口已换", moved.message || "");
          await refreshAll();
          await loadOta();
          const again = await api("/api/service/start", { method: "POST", body: {} });
          if (again.ok) toast("ok", "正在启动", "记得重新复制 OTA 地址");
          else toast("bad", "还是没启动", again.message || "");
          refreshStatus();
        },
      });
    }

    $("#btnPorts").addEventListener("click", async () => {
      const res = await api("/api/net/ports");
      if (!res.ok) return toast("bad", "查不到端口状态", res.message || "");
      const rows = Object.values(res.ports || {})
        .map((p) => {
          const verdict =
            p.verdict === "free"
              ? "空闲"
              : p.verdict === "occupied"
              ? "被占用"
              : "系统保留 / 绑不上";
          const who = (p.listeners || [])
            .map((l) => `${l.name || "未知"}(${l.pid})`)
            .join("、");
          return `<tr><td>${p.port}</td><td>${verdict}</td><td>${esc(who || "—")}</td></tr>`;
        })
        .join("");
      const excluded = (res.excluded || [])
        .slice(0, 6)
        .map((r) => `${r[0]}–${r[1]}`)
        .join("、");
      openModal({
        title: "端口诊断",
        okText: "知道了",
        body: `
          <table class="confirm-table">
            <tr><td><b>端口</b></td><td><b>状态</b></td><td><b>占用者</b></td></tr>
            ${rows}
          </table>
          <p class="confirm-note">${
            excluded
              ? "Windows 保留段（Hyper-V/WSL 常见）：" + esc(excluded)
              : "没有被 Windows 保留的端口段。"
          }<br>「系统保留」表示没人监听但绑不上，点「换端口并启动」会自动避开。</p>`,
      });
    });

    $("#btnStop").addEventListener("click", async () => {
      const res = await api("/api/service/stop", { method: "POST", body: {} });
      if (!res.ok) return toast("bad", "停止失败", res.message || "");
      toast("info", "已停止", "机器狗会暂时连不上");
      refreshStatus();
    });

    $("#btnCopyOta").addEventListener("click", copyOta);
    $("#adapterSelect").addEventListener("change", paintOta);
    $("#btnFirewall").addEventListener("click", async () => {
      const btn = $("#btnFirewall");
      btn.disabled = true;
      btn.textContent = "等待管理员确认…";
      const res = await api("/api/net/firewall", { method: "POST", body: {} });
      btn.disabled = false;
      btn.textContent = "连不上？放行防火墙";
      if (res.ok) toast("ok", "已放行", res.message || "端口已对专用网络开放");
      else toast("bad", "放行没成功", res.message || "可以按提示手动执行");
    });
    $("#btnExitPanel").addEventListener("click", () => {
      openModal({
        title: "退出控制面板",
        hint: "只关浏览器标签不算退出；这里点哪个都会结束面板进程。",
        okText: "退出并停止机器狗服务",
        body: `
          <p class="confirm-lead">想保留机器狗服务（狗还能说话），就点下面的「只退出面板」。</p>
          <button class="btn btn-ghost" id="exitKeep" type="button">只退出面板（服务继续跑）</button>`,
        onOk: async () => {
          closeModal();
          await api("/api/panel/shutdown", { method: "POST", body: { stop_services: true } });
          showExited();
        },
      });
      setTimeout(() => {
        const btn = $("#exitKeep");
        if (btn)
          btn.onclick = async () => {
            closeModal();
            await api("/api/panel/shutdown", { method: "POST", body: {} });
            showExited();
          };
      }, 40);
    });

    function showExited() {
      document.body.innerHTML = `
        <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:system-ui;background:#f7f5f0;color:#191a1c">
          <div style="text-align:center">
            <div style="font-size:22px;font-weight:600;letter-spacing:-.01em">面板已退出</div>
            <p style="color:#8b8e96;font-size:13px;margin:10px 0 0">可以直接关掉这个页面；下次双击「启动面板.bat」再打开。</p>
          </div>
        </div>`;
    }
    $("#btnRefreshDevice").addEventListener("click", async () => {
      await refreshStatus();
      const dev = (state.status && state.status.device) || {};
      toast(
        dev.count ? "ok" : "bad",
        dev.count ? "设备在线" : "还是没看到设备",
        dev.count ? `${dev.count} 台已连接` : "狗在聊天但这里没显示？点「诊断端口」看 WS 端口，或重启面板再刷新"
      );
    });
    $("#btnSelftest").addEventListener("click", runSelftest);

    $("#logsToggle").addEventListener("change", (e) => {
      $("#logTools").hidden = !e.target.checked;
      $("#logConsole").hidden = !e.target.checked;
      $("#logHint").hidden = e.target.checked;
      if (e.target.checked) loadLogs();
      else if (state.logTimer) {
        clearInterval(state.logTimer);
        state.logTimer = null;
      }
    });
    $("#logFilter").addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      $$("#logFilter .chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
      chip.setAttribute("aria-pressed", "true");
      state.logFilter = chip.dataset.filter || "";
      loadLogs();
    });
    $("#logLines").addEventListener("change", (e) => {
      state.logLines = Number(e.target.value);
      loadLogs();
    });
    $("#btnRefreshLogs").addEventListener("click", loadLogs);

    $("#modalClose").addEventListener("click", closeModal);
    $("#modalCancel").addEventListener("click", closeModal);
    $("#modalOk").addEventListener("click", () => modalOnOk && modalOnOk());
    $("#modalLayer").addEventListener("click", (e) => {
      if (e.target.id === "modalLayer") closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !$("#modalLayer").hidden) closeModal();
    });

    window.addEventListener("resize", moveIndicator);
  }

  // --------------------------------------------------------------- 演示数据

  function demoEnv() {
    return {
      product: "小智本地服务",
      version: "0.1.0",
      stage: "ready",
      installed: true,
      path: { value: "D:\\xiaozhi", ascii: true, message: "" },
      windows: { release: "11", version: "10.0.26100", ok: true, machine: "AMD64" },
      disk: { free_gb: 128.4, need_gb: 1.5, ok: true },
      python: {
        portable: { exists: true, ok: true, version: "Python 3.11.9" },
        pyenv: { exists: true, ok: true, ready: true, version: "Python 3.11.9" },
        system: { exists: true, ok: true, version: "Python 3.11.9", note: "只做检测" },
      },
      ffmpeg: { path: "runtime\\bin\\ffmpeg.exe", ok: true, line: "ffmpeg version 7.1" },
      server: { present: true, path: "runtime\\xiaozhi-server" },
      ports: {},
      adapters: demoAdapters(),
      panel_python: "3.11.9",
      sizes: { pyenv_mb: 512.3, server_mb: 27.1, python_mb: 95 },
    };
  }

  function demoAdapters() {
    return [
      { ip: "192.168.1.7", name: "WLAN", type: "wifi", virtual: false, recommended: true },
      { ip: "10.10.0.4", name: "以太网", type: "ethernet", virtual: false },
    ];
  }

  function demoPlan() {
    const steps = [
      ["python", "便携 Python 3.11", "随包自带，不读取、不修改你电脑上的 Python", 0, 95, "Python 3.11.9"],
      ["pyenv", "项目内依赖目录", "依赖保存在项目目录，随绿色版一起移动", 0, 1, "已就绪"],
      ["deps", "语音与网络依赖", "连百炼、推流、解码要用的库（不装 torch，省 2GB）", 170, 520, "已占用 512 MB"],
      ["ffmpeg", "音频组件", "ffmpeg 与 opus 解码器，机器狗的声音靠它", 40, 40, "ffmpeg version 7.1"],
      ["server", "小智服务端", "内置上游 0.9.8，不用你去 GitHub 下载", 0, 27, "runtime\\xiaozhi-server"],
      ["config", "生成默认配置", "唤醒词、人设、端口，装完就能用", 0, 1, ""],
      ["verify", "收尾自检", "检查每一块真的能用", 0, 0, ""],
    ].map(([id, name, desc, dl, disk, detail]) => ({
      id, name, desc, download_mb: dl, disk_mb: disk, status: "done", detail,
    }));
    return {
      steps,
      total_disk_mb: 0,
      total_download_mb: 0,
      installed: true,
      stage: "ready",
      eta: "不到 1 分钟",
      path: { value: "D:\\xiaozhi", ascii: true },
      disk_free_gb: 128.4,
    };
  }

  function demoSettings() {
    return {
      schema: 1,
      voice: { tts_model: "qwen-audio-3.1-tts-flash", voice_id: "longanhuan_v3.1", speed: 1, volume: 50 },
      asr: { model: "fun-asr-realtime" },
      keys: { bailian: "****9f2a" },
      brain: {
        mode: "gateway",
        vendor: "bailian",
        base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: "deepseek-v4.1-flash-1017",
        api_key: "",
        temperature: 0.7,
        max_tokens: 300,
      },
      persona: {
        prompt:
          "你是一只叫「小兵」的四足机器狗，会走路、坐下、趴下、摇尾巴。\n说话口语、自然、简短，一句话说完，不超过 40 字。\n不要用 markdown，不要念符号，不要解释你在做什么。\n每句话的第一个字前面放一个 emoji 表示你的情绪。\n你只能说自己真能做到的事，不要编造。",
        wakeup_words: ["小兵小兵"],
        memory: true,
      },
      ports: { panel: 8770, gateway: 8771, ota: 8003, ws: 8005 },
      runtime: { autostart: true, keep_running_on_panel_exit: false, debug: false },
      _meta: { vendors: FALLBACK_VENDORS },
    };
  }

  const DEMO_LOGS = [
    "26-11-08 12:31:05 [0.9.8_AliyunBLStreamASR]INFO-conn-收到音频帧 60ms",
    "26-11-08 12:31:06 [0.9.8_AliyunBLStreamASR]INFO-ASR-识别结果：你好小智，今天天气怎么样",
    "26-11-08 12:31:06 [0.9.8_LocalGatewayLLM]INFO-LLM-回合开始，字符流式返回",
    "26-11-08 12:31:07 [0.9.8_AliBLTTS]INFO-TTS-句子语音生成成功：今天晴，26 度，适合出去玩",
    "26-11-08 12:31:07 [0.9.8]INFO-发送音频消息 24192 字节",
    "26-11-08 12:31:12 [0.9.8_AliyunBLStreamASR]INFO-ASR-识别结果：那我们去公园吧",
    "26-11-08 12:31:13 [0.9.8_LocalGatewayLLM]WARNING-上游响应偏慢，已启用兜底话术",
    "26-11-08 12:31:14 [0.9.8]INFO-下发设备动作：{\"action\":\"wiggle_tail\"}",
  ];

  async function demoApi(path, options) {
    await sleep(120);
    if (path === "/api/health") {
      return { ok: true, version: "0.1.0", pid: 4242, uptime: 613, python: "3.11.9" };
    }
    if (path === "/api/env") return demoEnv();
    if (path === "/api/install/plan") return demoPlan();
    if (path === "/api/settings" && (!options || !options.method)) {
      return { ok: true, settings: demoSettings() };
    }
    if (path === "/api/settings") {
      return {
        ok: true,
        changed: ["voice.voice_id"],
        restart: { gateway: false, server: true },
        eta: "约 30 秒",
        notes: ["语音服务重启期间机器狗会断线，随后自动重连"],
        settings: demoSettings(),
      };
    }
    if (path === "/api/service/status") {
      return {
        ok: true,
        gateway: { running: true, ports: [8771], listening: true, uptime: 613 },
        server: { running: true, ports: [8003, 8005], listening: true, uptime: 612 },
        any_running: true,
      };
    }
    if (path === "/api/net/ota") {
      return {
        ok: true,
        port: 8003,
        adapters: demoAdapters(),
        urls: demoAdapters().map((a) => ({
          ip: a.ip,
          name: a.name,
          url: `http://${a.ip}:8003/xiaozhi/ota/`,
          recommended: Boolean(a.recommended),
          virtual: Boolean(a.virtual),
        })),
      };
    }
    if (path.startsWith("/api/logs")) {
      return { ok: true, exists: true, lines: DEMO_LOGS, total: DEMO_LOGS.length };
    }
    if (path === "/api/selftest") {
      return {
        ok: true,
        overall: "ok",
        checks: [
          { key: "install", title: "运行环境", state: "ok", detail: "已就绪", hint: "" },
          { key: "key", title: "百炼 API Key", state: "ok", detail: "已配置", hint: "" },
          { key: "ports", title: "语音服务端口", state: "ok", detail: "在监听", hint: "" },
          { key: "tts", title: "语音合成试听", state: "skip", detail: "演示模式不发声", hint: "" },
          { key: "device", title: "虚拟设备全链路", state: "skip", detail: "演示模式", hint: "" },
        ],
      };
    }
    if (path === "/api/llm/models") {
      return { ok: true, models: ["qwen3.8-flash", "qwen-plus", "qwen-max"] };
    }
    if (path === "/api/service/stop") {
      return { ok: true, stopped: ["gateway", "server"] };
    }
    if (path === "/api/service/start" || path === "/api/service/restart") {
      return { ok: true };
    }
    return { ok: false, message: "演示模式没有这个接口" };
  }

  // --------------------------------------------------------------- 启动

  async function boot() {
    if (DEMO) {
      const badge = document.createElement("div");
      badge.className = "badge badge--warn";
      badge.style.cssText = "position:fixed;top:14px;right:16px;z-index:300";
      badge.textContent = "演示模式";
      document.body.appendChild(badge);
    }
    bind();
    const params = new URLSearchParams(location.search);
    // 记下首次打开时 URL 带的 page 参数：go() 会改写 URL，之后再读就拿不到了
    window.__pageParamAtBoot = params.get("page");
    go(params.get("page") || "install");
    await refreshAll();

    state.statusTimer = setInterval(() => {
      if (document.hidden) return;
      refreshStatus();
    }, 2500);

    // 日志轮询：只在勾选时跑
    state.logTimer = setInterval(() => {
      if (!$("#logsToggle").checked || document.hidden) return;
      loadLogs();
    }, 3000);
  }

  boot();
})();


/* ---------------- 绿色模式：环境检查 + 自动跳转 ---------------- */
function greenBoot() {
  const btn = document.getElementById("btnGreenCheck");
  const list = document.getElementById("greenList");
  const badge = document.getElementById("greenBadge");
  const gw = document.getElementById("procGw");
  if (gw) gw.style.display = "none";

  async function run() {
    try {
      const r = await fetch("/api/green/env").then((x) => x.json());
      if (list) {
        list.innerHTML = (r.checks || [])
          .map(
            (c) =>
              '<li style="display:flex;justify-content:space-between;padding:10px 2px;border-bottom:1px solid #e7e5df"><span>' +
              c.name +
              '</span><b style="color:' +
              (c.ok ? "#2e7d32" : "#b4552e") +
              '">' +
              (c.ok ? "正常" : "异常") +
              "</b></li>"
          )
          .join("");
      }
      if (badge) {
        badge.textContent = r.ok ? "全部正常" : "有异常";
        badge.className = "badge " + (r.ok ? "badge--ok" : "badge--warn");
      }
      return r;
    } catch (e) {
      if (list) list.innerHTML = '<li style="color:#b4552e;padding:8px">检查失败：' + e + "</li>";
      return { ok: false };
    }
  }

  if (btn) btn.onclick = run;
  setTimeout(async () => {
    const r = await run();
    if (!r.ok) return;
    try {
      const s = await fetch("/api/settings").then((x) => x.json());
      const has = Boolean(s && s.settings && s.settings.keys && s.settings.keys.bailian);
      if (has) {
        // 只在「确认服务没在跑」时才启动：否则每次打开/刷新页面都会把正在运行的
        // 服务先杀掉再重启（green.start() 内部第一步是 stop()），机器狗会当场断线卡住。
        const st = await fetch("/api/service/status")
          .then((x) => x.json())
          .catch(() => null);
        if (st && !st.any_running) {
          await fetch("/api/service/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}",
          });
        }
      }
      // 只有「首次打开」（URL 一开始就没带 page 参数）才自动跳转；刷新时保留用户当前页面
      if (!window.__pageParamAtBoot) {
        const nav = document.querySelector('[data-nav="' + (has ? "run" : "config") + '"]');
        if (nav) nav.click();
      }
    } catch (e) {
      /* ignore */
    }
  }, 900);
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", greenBoot);
} else {
  greenBoot();
}
