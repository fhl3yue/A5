const state = {
  currentLogId: null,
  audio: null,
  video: null,
  recorder: null,
  recordingStream: null,
  recordingChunks: [],
  adminToken: localStorage.getItem("scenic_admin_token") || "",
  digitalHuman: null,
  selectedDocId: null,
  guideMode: "qa",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const DEFAULT_AVATAR_URL = "./assets/avatar/avatar-guide-v1.png";
const LEGACY_LICENSED_AVATAR_URL = "./assets/avatar/licensed-character.png";
const runtimeParams = new URLSearchParams(window.location.search);
const runtimeClient = (runtimeParams.get("client") || "").toLowerCase().replace(/[^a-z0-9_-]/g, "");

function getStoredApiBaseUrl() {
  try {
    return localStorage.getItem("scenic_api_base_url") || "";
  } catch {
    return "";
  }
}

function normalizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function isAbsoluteUrl(value) {
  return /^(https?:|data:|blob:)/i.test(value || "");
}

const API_BASE_URL = normalizeBaseUrl(runtimeParams.get("apiBase") || window.SCENIC_AI_API_BASE_URL || getStoredApiBaseUrl());

if (runtimeClient) {
  document.body.classList.add(`client-${runtimeClient}`);
}
const ZH_TW_TO_CN = {
  "萬": "万",
  "與": "与",
  "專": "专",
  "業": "业",
  "東": "东",
  "兩": "两",
  "個": "个",
  "為": "为",
  "義": "义",
  "樂": "乐",
  "書": "书",
  "亂": "乱",
  "雲": "云",
  "亞": "亚",
  "產": "产",
  "親": "亲",
  "儀": "仪",
  "們": "们",
  "價": "价",
  "會": "会",
  "傳": "传",
  "體": "体",
  "備": "备",
  "內": "内",
  "劃": "划",
  "劉": "刘",
  "區": "区",
  "華": "华",
  "協": "协",
  "單": "单",
  "衛": "卫",
  "參": "参",
  "雙": "双",
  "發": "发",
  "變": "变",
  "臺": "台",
  "號": "号",
  "聽": "听",
  "員": "员",
  "響": "响",
  "噴": "喷",
  "動": "动",
  "遊": "游",
  "國": "国",
  "聖": "圣",
  "場": "场",
  "聲": "声",
  "處": "处",
  "復": "复",
  "學": "学",
  "實": "实",
  "宮": "宫",
  "寬": "宽",
  "對": "对",
  "導": "导",
  "將": "将",
  "層": "层",
  "師": "师",
  "帶": "带",
  "幫": "帮",
  "廣": "广",
  "應": "应",
  "開": "开",
  "張": "张",
  "強": "强",
  "歸": "归",
  "當": "当",
  "錄": "录",
  "徑": "径",
  "態": "态",
  "總": "总",
  "懷": "怀",
  "驚": "惊",
  "戰": "战",
  "擴": "扩",
  "揚": "扬",
  "護": "护",
  "報": "报",
  "擔": "担",
  "擇": "择",
  "擋": "挡",
  "據": "据",
  "攝": "摄",
  "敵": "敌",
  "數": "数",
  "斷": "断",
  "無": "无",
  "舊": "旧",
  "時": "时",
  "曉": "晓",
  "術": "术",
  "機": "机",
  "權": "权",
  "條": "条",
  "來": "来",
  "極": "极",
  "標": "标",
  "樹": "树",
  "橋": "桥",
  "檢": "检",
  "歡": "欢",
  "氣": "气",
  "漢": "汉",
  "測": "测",
  "濟": "济",
  "灣": "湾",
  "滿": "满",
  "靈": "灵",
  "點": "点",
  "熱": "热",
  "現": "现",
  "畫": "画",
  "監": "监",
  "盤": "盘",
  "礎": "础",
  "確": "确",
  "禪": "禅",
  "種": "种",
  "積": "积",
  "稱": "称",
  "築": "筑",
  "簽": "签",
  "簡": "简",
  "類": "类",
  "緊": "紧",
  "約": "约",
  "級": "级",
  "紹": "绍",
  "細": "细",
  "經": "经",
  "結": "结",
  "統": "统",
  "績": "绩",
  "網": "网",
  "聯": "联",
  "腦": "脑",
  "藝": "艺",
  "藍": "蓝",
  "營": "营",
  "虛": "虚",
  "雖": "虽",
  "補": "补",
  "裝": "装",
  "裡": "里",
  "裏": "里",
  "見": "见",
  "觀": "观",
  "規": "规",
  "視": "视",
  "覽": "览",
  "覺": "觉",
  "計": "计",
  "認": "认",
  "討": "讨",
  "讓": "让",
  "訓": "训",
  "議": "议",
  "訊": "讯",
  "記": "记",
  "講": "讲",
  "許": "许",
  "論": "论",
  "設": "设",
  "訪": "访",
  "證": "证",
  "識": "识",
  "詞": "词",
  "詩": "诗",
  "話": "话",
  "詳": "详",
  "語": "语",
  "誤": "误",
  "說": "说",
  "請": "请",
  "讀": "读",
  "調": "调",
  "談": "谈",
  "謂": "谓",
  "謝": "谢",
  "貝": "贝",
  "責": "责",
  "敗": "败",
  "貨": "货",
  "質": "质",
  "費": "费",
  "資": "资",
  "賞": "赏",
  "贊": "赞",
  "趕": "赶",
  "躍": "跃",
  "踐": "践",
  "車": "车",
  "轉": "转",
  "較": "较",
  "輸": "输",
  "辭": "辞",
  "邊": "边",
  "達": "达",
  "過": "过",
  "運": "运",
  "還": "还",
  "這": "这",
  "週": "周",
  "進": "进",
  "遠": "远",
  "連": "连",
  "適": "适",
  "選": "选",
  "遞": "递",
  "遺": "遗",
  "釋": "释",
  "鑒": "鉴",
  "鋪": "铺",
  "鋼": "钢",
  "鐵": "铁",
  "錯": "错",
  "鎖": "锁",
  "長": "长",
  "門": "门",
  "問": "问",
  "間": "间",
  "聞": "闻",
  "隊": "队",
  "際": "际",
  "陸": "陆",
  "陳": "陈",
  "難": "难",
  "準": "准",
  "電": "电",
  "題": "题",
  "顏": "颜",
  "風": "风",
  "飛": "飞",
  "飲": "饮",
  "馬": "马",
  "驗": "验",
  "鮮": "鲜",
  "鳥": "鸟",
  "麥": "麦",
  "黃": "黄",
  "龍": "龙",
};
const ZH_TW_PATTERN = new RegExp(`[${Object.keys(ZH_TW_TO_CN).join("")}]`, "g");

const elements = {
  apiStatus: $("#apiStatus"),
  docsLink: $("#docsLink"),
  avatarFrame: $("#avatarFrame"),
  petSpeech: $("#petSpeech"),
  petNameplate: $("#petNameplate"),
  licensedAvatarImage: $("#licensedAvatarImage"),
  licensedAvatarFallback: $("#licensedAvatarFallback"),
  digitalVideoLayer: $("#digitalVideoLayer"),
  digitalVideoPlayer: $("#digitalVideoPlayer"),
  guideStatus: $("#guideStatus"),
  guideSubtitle: $("#guideSubtitle"),
  chatMessages: $("#chatMessages"),
  textChatForm: $("#textChatForm"),
  questionInput: $("#questionInput"),
  recordButton: $("#recordButton"),
  voiceHint: $("#voiceHint"),
  voiceFileInput: $("#voiceFileInput"),
  routeForm: $("#routeForm"),
  interestSelect: $("#interestSelect"),
  interestCustomInput: $("#interestCustomInput"),
  durationSelect: $("#durationSelect"),
  durationCustomInput: $("#durationCustomInput"),
  routeResult: $("#routeResult"),
  loginPanel: $("#loginPanel"),
  adminWorkspace: $("#adminWorkspace"),
  loginForm: $("#loginForm"),
  adminUsername: $("#adminUsername"),
  adminPassword: $("#adminPassword"),
  bigInsightNote: $("#bigInsightNote"),
  bigTodayVisitors: $("#bigTodayVisitors"),
  bigWeekVisitors: $("#bigWeekVisitors"),
  bigWeekQaCount: $("#bigWeekQaCount"),
  bigSatisfactionRate: $("#bigSatisfactionRate"),
  bigTopQuestion: $("#bigTopQuestion"),
  bigServiceBars: $("#bigServiceBars"),
  bigSatisfactionBars: $("#bigSatisfactionBars"),
  todayVisitors: $("#todayVisitors"),
  todayQaCount: $("#todayQaCount"),
  satisfactionRate: $("#satisfactionRate"),
  hotQuestionsChart: $("#hotQuestionsChart"),
  emotionChart: $("#emotionChart"),
  weeklyServiceTrend: $("#weeklyServiceTrend"),
  satisfactionTrend: $("#satisfactionTrend"),
  visitorReportSummary: $("#visitorReportSummary"),
  focusPointsList: $("#focusPointsList"),
  emotionTrendList: $("#emotionTrendList"),
  serviceSuggestionsList: $("#serviceSuggestionsList"),
  logsTableBody: $("#logsTableBody"),
  refreshAdminButton: $("#refreshAdminButton"),
  reloadLogsButton: $("#reloadLogsButton"),
  uploadForm: $("#uploadForm"),
  docUploadInput: $("#docUploadInput"),
  reloadKnowledgeButton: $("#reloadKnowledgeButton"),
  knowledgeDocsList: $("#knowledgeDocsList"),
  selectedDocInfo: $("#selectedDocInfo"),
  knowledgeDocMetaForm: $("#knowledgeDocMetaForm"),
  docNameInput: $("#docNameInput"),
  docSourceInput: $("#docSourceInput"),
  docStatusSelect: $("#docStatusSelect"),
  knowledgeChunksPreview: $("#knowledgeChunksPreview"),
  addChunkForm: $("#addChunkForm"),
  newChunkTitleInput: $("#newChunkTitleInput"),
  newChunkTagsInput: $("#newChunkTagsInput"),
  newChunkContentInput: $("#newChunkContentInput"),
  configScenicArea: $("#configScenicArea"),
  configKnowledgeName: $("#configKnowledgeName"),
  configAvatarName: $("#configAvatarName"),
  configVoiceName: $("#configVoiceName"),
  digitalHumanForm: $("#digitalHumanForm"),
  previewDigitalHumanButton: $("#previewDigitalHumanButton"),
  dhNameInput: $("#dhNameInput"),
  dhRoleInput: $("#dhRoleInput"),
  dhScenicInput: $("#dhScenicInput"),
  dhOutfitSelect: $("#dhOutfitSelect"),
  dhVoiceSelect: $("#dhVoiceSelect"),
  dhAvatarAssetUrlInput: $("#dhAvatarAssetUrlInput"),
  dhGreetingInput: $("#dhGreetingInput"),
  dhFallbackMessageInput: $("#dhFallbackMessageInput"),
  dhServiceBoundaryInput: $("#dhServiceBoundaryInput"),
  avatarUploadForm: $("#avatarUploadForm"),
  avatarUploadInput: $("#avatarUploadInput"),
  refreshVideoStatusButton: $("#refreshVideoStatusButton"),
  videoProviderEnabled: $("#videoProviderEnabled"),
  videoProviderLastStatus: $("#videoProviderLastStatus"),
  videoProviderAverage: $("#videoProviderAverage"),
  videoProviderFallbacks: $("#videoProviderFallbacks"),
  videoProviderFailure: $("#videoProviderFailure"),
  visitorVideoStatus: $("#visitorVideoStatus"),
  visitorFallbackMessage: $("#visitorFallbackMessage"),
  visitorServiceBoundary: $("#visitorServiceBoundary"),
  toast: $("#toast"),
};

function showToast(message, type = "success") {
  elements.toast.textContent = message;
  elements.toast.className = `toast show ${type === "error" ? "error" : ""}`;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.className = "toast";
  }, 2800);
}

function buildApiUrl(path) {
  if (!path || isAbsoluteUrl(path) || !API_BASE_URL) {
    return path;
  }
  return new URL(path, `${API_BASE_URL}/`).toString();
}

function resolveMediaUrl(url) {
  if (!url || isAbsoluteUrl(url) || !API_BASE_URL) {
    return url;
  }
  return new URL(url, `${API_BASE_URL}/`).toString();
}

async function apiFetch(path, options = {}) {
  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = { message: "服务返回了无法解析的数据。" };
  }

  if (!response.ok || payload.code !== 0) {
    throw new Error(payload.detail || payload.message || `请求失败：${response.status}`);
  }

  return payload.data ?? payload;
}

function escapeHtml(value) {
  return toSimplifiedChinese(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toSimplifiedChinese(value) {
  return String(value ?? "").replace(ZH_TW_PATTERN, (char) => ZH_TW_TO_CN[char] || char);
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

function setGuideState(title, subtitle) {
  elements.guideStatus.textContent = title;
  elements.guideSubtitle.textContent = subtitle;
}

function setPetSpeech(text) {
  if (elements.petSpeech) {
    elements.petSpeech.textContent = text;
  }
}

function setPetMode(mode) {
  elements.avatarFrame.classList.remove("thinking", "listening", "speaking", "success");
  if (mode) {
    elements.avatarFrame.classList.add(mode);
  }
}

function voiceLabel(voiceName) {
  const labels = {
    "zh-CN-XiaoxiaoNeural": "晓晓女声",
    "zh-CN-YunxiNeural": "云希男声",
    "zh-CN-XiaoyiNeural": "晓伊女声",
    "zh-CN-YunjianNeural": "云健男声",
  };
  return labels[voiceName] || voiceName || "中文声线";
}

function looksLikeGarbledName(value) {
  return /[╛╡╟┬├╙╬╩▌╨╖╓┴╔╜╠╪╕─]|â|Ã|Â/.test(value || "");
}

function docDisplayName(doc) {
  if (!looksLikeGarbledName(doc.name)) {
    return doc.name;
  }
  if (doc.content_type === "xlsx") {
    return "官方游客行为数据.xlsx";
  }
  if (doc.chunk_count >= 50) {
    return "官方景区文旅资料.docx";
  }
  return "官方景区结构资料.docx";
}

function themeClass(outfitTheme) {
  const classes = {
    "asset-avatar": "theme-asset-avatar",
    "heritage-gold": "theme-heritage-gold",
    "lake-blue": "theme-lake-blue",
    "festival-red": "theme-festival-red",
    "licensed-asset": "theme-licensed-asset",
  };
  return classes[outfitTheme] || "";
}

function readDigitalHumanForm() {
  return {
    name: elements.dhNameInput.value.trim(),
    role_title: elements.dhRoleInput.value.trim(),
    scenic_area: elements.dhScenicInput.value.trim(),
    outfit_theme: elements.dhOutfitSelect.value,
    voice_name: elements.dhVoiceSelect.value,
    greeting: elements.dhGreetingInput.value.trim(),
    avatar_asset_url: elements.dhAvatarAssetUrlInput.value.trim(),
    fallback_message: elements.dhFallbackMessageInput.value.trim(),
    service_boundary: elements.dhServiceBoundaryInput.value.trim(),
    video_provider_status: "外部视频 API",
  };
}

function fillDigitalHumanForm(config) {
  if (!elements.digitalHumanForm || !config) {
    return;
  }
  elements.dhNameInput.value = config.name || "灵灵";
  elements.dhRoleInput.value = config.role_title || "景区 AI 导览员";
  elements.dhScenicInput.value = config.scenic_area || "灵山胜境";
  elements.dhOutfitSelect.value = config.outfit_theme || "ling-shan";
  elements.dhVoiceSelect.value = config.voice_name || "zh-CN-XiaoxiaoNeural";
  elements.dhAvatarAssetUrlInput.value = config.avatar_asset_url || DEFAULT_AVATAR_URL;
  elements.dhGreetingInput.value = config.greeting || "";
  elements.dhFallbackMessageInput.value = config.fallback_message || "数字人视频暂不可用，已切换为语音讲解。";
  elements.dhServiceBoundaryInput.value = config.service_boundary || "仅基于景区知识库进行导览讲解，不提供功德承诺、神迹保证或占卜预测。";
}

function applyDigitalHumanConfig(config) {
  if (!config) {
    return;
  }
  state.digitalHuman = config;
  document.body.classList.remove("theme-asset-avatar", "theme-heritage-gold", "theme-lake-blue", "theme-festival-red", "theme-licensed-asset");
  const nextTheme = themeClass(config.outfit_theme);
  if (nextTheme) {
    document.body.classList.add(nextTheme);
  }
  const assetUrl = config.avatar_asset_url || (config.outfit_theme === "licensed-asset" ? LEGACY_LICENSED_AVATAR_URL : "");
  syncLicensedAvatarAsset(assetUrl);

  elements.petNameplate.textContent = `${config.name} · ${config.role_title}`;
  elements.petSpeech.textContent = `${config.scenic_area}导览中`;
  elements.guideSubtitle.textContent = config.greeting;
  if (elements.visitorFallbackMessage) {
    elements.visitorFallbackMessage.textContent = config.fallback_message || "失败自动回退";
  }
  if (elements.visitorServiceBoundary) {
    elements.visitorServiceBoundary.textContent = config.service_boundary || "知识库生成";
  }

  if (elements.configScenicArea) {
    elements.configScenicArea.textContent = config.scenic_area;
    elements.configKnowledgeName.textContent = config.scenic_area;
    elements.configAvatarName.textContent = config.name;
    elements.configVoiceName.textContent = voiceLabel(config.voice_name);
  }
  fillDigitalHumanForm(config);
}

function bindLicensedAvatarAsset() {
  if (!elements.licensedAvatarImage) {
    return;
  }
  elements.licensedAvatarImage.addEventListener("load", () => {
    document.body.classList.add("licensed-avatar-ready");
  });
  elements.licensedAvatarImage.addEventListener("error", () => {
    document.body.classList.remove("licensed-avatar-ready");
  });
}

async function syncLicensedAvatarAsset(assetUrl) {
  if (!elements.licensedAvatarImage) {
    return;
  }
  if (!assetUrl) {
    elements.licensedAvatarImage.removeAttribute("src");
    document.body.classList.remove("licensed-avatar-ready");
    return;
  }

  document.body.classList.add("theme-asset-avatar");
  const resolved = resolveMediaUrl(assetUrl);
  const separator = resolved.includes("?") ? "&" : "?";
  elements.licensedAvatarImage.src = `${resolved}${separator}v=${Date.now()}`;
}

async function loadDigitalHumanConfig() {
  try {
    const config = await apiFetch("/api/digital-human/config");
    applyDigitalHumanConfig(config);
  } catch (error) {
    showToast(`数字人配置加载失败：${error.message}`, "error");
  }
}

async function saveDigitalHumanConfig() {
  const config = readDigitalHumanForm();
  if (!config.name || !config.role_title || !config.scenic_area || !config.greeting || !config.fallback_message || !config.service_boundary) {
    showToast("请填写完整的数字人配置。", "error");
    return;
  }

  try {
    const saved = await apiFetch("/api/admin/digital-human/config", {
      method: "POST",
      body: JSON.stringify(config),
    });
    applyDigitalHumanConfig(saved);
    showToast("数字人配置已保存。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function uploadAvatarAsset() {
  const file = elements.avatarUploadInput.files?.[0];
  if (!file) {
    showToast("请先选择 PNG、WebP、AVIF、GIF 或 JPG 形象素材。", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  try {
    const saved = await apiFetch("/api/admin/digital-human/avatar", {
      method: "POST",
      body: formData,
    });
    elements.avatarUploadInput.value = "";
    applyDigitalHumanConfig(saved);
    showToast("数字人形象素材已上传。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadDigitalVideoStatus({ silent = true } = {}) {
  if (!elements.videoProviderEnabled) {
    return;
  }
  try {
    const status = await apiFetch("/api/admin/digital-video/status");
    renderDigitalVideoStatus(status);
  } catch (error) {
    if (!silent) {
      showToast(error.message, "error");
    }
  }
}

function renderDigitalVideoStatus(status) {
  const enabledText = status.enabled ? (status.configured ? "已启用" : "未配置地址") : "未启用";
  elements.videoProviderEnabled.textContent = enabledText;
  elements.videoProviderLastStatus.textContent = status.last_status || "-";
  elements.videoProviderAverage.textContent = `${Number(status.average_response_seconds || 0).toFixed(2)}s`;
  elements.videoProviderFallbacks.textContent = status.fallback_count ?? 0;
  elements.videoProviderFailure.textContent = status.last_failure_reason || status.last_message || "无";
  if (elements.visitorVideoStatus) {
    elements.visitorVideoStatus.textContent = status.enabled ? "外部视频优先" : "当前回退音频";
  }
}

function setApiStatus(text, type) {
  elements.apiStatus.textContent = text;
  elements.apiStatus.className = `status-pill ${type}`;
}

function configureRuntimeLinks() {
  if (elements.docsLink && API_BASE_URL) {
    elements.docsLink.href = buildApiUrl("/docs");
  }
}

function addMessage(type, html, extraClass = "") {
  const node = document.createElement("div");
  node.className = `message ${type} ${extraClass}`.trim();
  node.innerHTML = html;
  elements.chatMessages.appendChild(node);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  return node;
}

function renderRouteCard(data) {
  return `
    <article class="route-card">
      <div>
        <p class="eyebrow">推荐路线</p>
        <h3>${escapeHtml(data.route_name)}</h3>
      </div>
      <div class="route-steps">
        ${data.route_spots.map((spot, index) => `<span class="route-step">${index + 1}. ${escapeHtml(spot)}</span>`).join("")}
      </div>
      <p>${escapeHtml(data.reason)}</p>
    </article>
  `;
}

function renderReferenceTags(references = []) {
  if (!references.length) {
    return "";
  }
  return `
    <div class="message-meta">
      ${references.map((item) => `<span class="tag">${escapeHtml(item)}</span>`).join("")}
    </div>
  `;
}

function renderFeedbackActions(logId) {
  if (!logId) {
    return "";
  }
  return `
    <div class="message-actions" aria-label="满意度反馈">
      <button class="rating-button" type="button" data-rating="5" data-log-id="${logId}">5</button>
      <button class="rating-button" type="button" data-rating="4" data-log-id="${logId}">4</button>
      <button class="rating-button" type="button" data-rating="3" data-log-id="${logId}">3</button>
      <button class="rating-button" type="button" data-rating="2" data-log-id="${logId}">2</button>
      <button class="rating-button" type="button" data-rating="1" data-log-id="${logId}">1</button>
    </div>
  `;
}

function renderAnswer(data, options = {}) {
  state.currentLogId = data.log_id;
  const transcriptBlock = options.showTranscript
    ? `
      <div class="message-meta">
        <span class="tag">识别：${escapeHtml(data.transcript || "-")}</span>
        <span class="tag">理解：${escapeHtml(data.interpreted_question || "-")}</span>
      </div>
    `
    : "";
  const audioButton = data.audio_url
    ? `<button class="small-action" type="button" data-audio-url="${escapeHtml(data.audio_url)}">播放回答</button>`
    : "";
  const videoReady = data.video_url && data.video_status === "ready";
  const videoButton = videoReady
    ? `<button class="small-action" type="button" data-video-url="${escapeHtml(data.video_url)}" data-fallback-audio-url="${escapeHtml(data.audio_url || "")}">播放数字人视频</button>`
    : "";
  const videoTag = data.video_status && data.video_status !== "disabled"
    ? `<span class="tag">视频：${escapeHtml(data.video_status)}</span>`
    : "";

  addMessage(
    "assistant",
    `
      <strong>数字人回答</strong>
      <div>${escapeHtml(data.answer)}</div>
      ${transcriptBlock}
      ${renderReferenceTags(data.reference)}
      <div class="message-meta">
        <span class="tag">${escapeHtml(data.emotion || "neutral")}</span>
        <span class="tag">${Number(data.response_seconds || 0).toFixed(2)} 秒</span>
        ${videoTag}
      </div>
      <div class="message-actions">
        ${videoButton}
        ${audioButton}
      </div>
      ${renderFeedbackActions(data.log_id)}
    `
  );

  setGuideState("已完成回答", data.interpreted_question || data.transcript || "欢迎继续提问");
  setPetMode("success");
  if (videoReady) {
    playDigitalVideo(data.video_url, data.audio_url);
  } else if (data.audio_url) {
    playAudio(data.audio_url);
  }
}

async function askText(question) {
  const trimmed = question.trim();
  if (!trimmed) {
    showToast("先输入一个问题。", "error");
    return;
  }

  addMessage("user", escapeHtml(trimmed));
  const loading = addMessage("assistant", "正在检索景区知识库，请稍候...", "loading");
  elements.questionInput.value = "";
  setGuideState("正在思考", "正在从景区知识库中查找最相关的信息。");
  setPetSpeech("检索知识库");
  setPetMode("thinking");

  try {
    const data = await apiFetch("/api/chat/text", {
      method: "POST",
      body: JSON.stringify({ question: trimmed, user_id: "web-visitor" }),
    });
    loading.remove();
    renderAnswer(data);
    loadAdminData({ silent: true });
  } catch (error) {
    loading.remove();
    setGuideState("问答失败", "请检查后端服务是否正常运行。");
    setPetSpeech("需要重试");
    setPetMode(null);
    showToast(error.message, "error");
  }
}

async function askRouteLecture(question) {
  const trimmed = question.trim() || "半天 初次游客";
  addMessage("user", escapeHtml(trimmed));
  const loading = addMessage("assistant", "正在生成适合初次游客的路线讲解...", "loading");
  elements.questionInput.value = "";
  setGuideState("正在规划路线", "系统正在匹配当前景区的预设路线。");
  setPetSpeech("路线规划中");
  setPetMode("thinking");

  try {
    const data = await apiFetch("/api/recommend/route", {
      method: "POST",
      body: JSON.stringify({
        interest: trimmed,
        duration: trimmed,
      }),
    });
    loading.remove();
    elements.routeResult.className = "route-result";
    elements.routeResult.innerHTML = renderRouteCard(data);
    addMessage(
      "assistant",
      `
        <strong>路线讲解</strong>
        ${renderRouteCard(data)}
      `
    );
    setGuideState("已生成路线", data.route_name);
    setPetSpeech("路线已生成");
    setPetMode("success");
  } catch (error) {
    loading.remove();
    setGuideState("路线生成失败", "请检查后端服务是否正常运行。");
    setPetSpeech("需要重试");
    setPetMode(null);
    showToast(error.message, "error");
  }
}

async function sendVoice(blob, filename = "visitor-question.webm") {
  const formData = new FormData();
  formData.append("user_id", "web-visitor");
  formData.append("file", blob, filename);

  addMessage("user", "已上传一段语音问题。");
  const loading = addMessage("assistant", "正在识别语音并生成回答...", "loading");
  setGuideState("正在识别语音", "系统正在提取语音内容并匹配景区知识。");
  setPetSpeech("语音识别中");
  setPetMode("listening");

  try {
    const data = await apiFetch("/api/chat/voice", {
      method: "POST",
      body: formData,
    });
    loading.remove();
    renderAnswer(data, { showTranscript: true });
    loadAdminData({ silent: true });
  } catch (error) {
    loading.remove();
    setGuideState("语音识别失败", "可以换一段更短、更清晰的录音重试。");
    setPetSpeech("没听清楚");
    setPetMode(null);
    showToast(error.message, "error");
  }
}

async function toggleRecording() {
  if (state.recorder?.state === "recording") {
    state.recorder.stop();
    elements.recordButton.textContent = "开始录音";
    elements.voiceHint.textContent = "录音已结束，正在上传...";
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    showToast("当前浏览器不支持录音，可以使用上传音频。", "error");
    return;
  }

  try {
    state.recordingStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.recordingChunks = [];
    state.recorder = new MediaRecorder(state.recordingStream);
    state.recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        state.recordingChunks.push(event.data);
      }
    });
    state.recorder.addEventListener("stop", () => {
      const blob = new Blob(state.recordingChunks, { type: "audio/webm" });
    state.recordingStream.getTracks().forEach((track) => track.stop());
    state.recordingStream = null;
      elements.voiceHint.textContent = "录音处理中";
      sendVoice(blob);
    });
    state.recorder.start();
    elements.recordButton.textContent = "停止录音";
    elements.voiceHint.textContent = "正在录音";
  } catch (error) {
    showToast(`无法打开麦克风：${error.message}`, "error");
  }
}

function playAudio(url) {
  if (!url) {
    showToast("这条回答没有可播放音频。", "error");
    return;
  }
  stopVideoPlayback();
  stopAudioPlayback();

  state.audio = new Audio(resolveMediaUrl(url));
  state.audio.addEventListener("play", markSpeaking);
  state.audio.addEventListener("ended", unmarkSpeaking);
  state.audio.addEventListener("pause", unmarkSpeaking);
  state.audio.play().catch((error) => {
    unmarkSpeaking();
    showToast(`音频播放失败：${error.message}`, "error");
  });
}

function playDigitalVideo(url, fallbackAudioUrl = "") {
  if (!url || !elements.digitalVideoPlayer) {
    if (fallbackAudioUrl) {
      playAudio(fallbackAudioUrl);
    }
    return;
  }

  stopAudioPlayback();
  stopVideoPlayback();

  const player = elements.digitalVideoPlayer;
  state.video = player;
  player.src = resolveMediaUrl(url);
  player.currentTime = 0;
  player.onplay = () => {
    elements.avatarFrame.classList.add("video-active");
    markSpeaking();
  };
  player.onpause = () => {
    if (!player.ended) {
      unmarkSpeaking();
    }
  };
  player.onended = () => {
    stopVideoPlayback();
    unmarkSpeaking();
  };
  player.onerror = () => {
    stopVideoPlayback();
    unmarkSpeaking();
    if (fallbackAudioUrl) {
      setGuideState("切换语音讲解", state.digitalHuman?.fallback_message || "数字人视频暂不可用，已切换为语音讲解。");
      playAudio(fallbackAudioUrl);
    } else {
      showToast(state.digitalHuman?.fallback_message || "数字人视频播放失败。", "error");
    }
  };
  elements.avatarFrame.classList.add("video-active");
  setGuideState("正在播报", "数字人正在播放视频讲解。");
  setPetSpeech("视频讲解中");

  player.play().catch((error) => {
    stopVideoPlayback();
    unmarkSpeaking();
    if (fallbackAudioUrl) {
      setGuideState("切换语音讲解", state.digitalHuman?.fallback_message || "数字人视频暂不可用，已切换为语音讲解。");
      playAudio(fallbackAudioUrl);
    } else {
      showToast(`数字人视频播放失败：${error.message}`, "error");
    }
  });
}

function stopAudioPlayback() {
  if (!state.audio) {
    return;
  }
  state.audio.pause();
  state.audio.removeEventListener("play", markSpeaking);
  state.audio.removeEventListener("ended", unmarkSpeaking);
  state.audio.removeEventListener("pause", unmarkSpeaking);
  state.audio = null;
}

function stopVideoPlayback() {
  const player = state.video || elements.digitalVideoPlayer;
  if (player) {
    player.onplay = null;
    player.onpause = null;
    player.onended = null;
    player.onerror = null;
    player.pause();
    player.removeAttribute("src");
    player.load();
  }
  state.video = null;
  elements.avatarFrame.classList.remove("video-active");
}

function markSpeaking() {
  setPetMode("speaking");
  setGuideState("正在播报", "数字人正在播放讲解内容。");
  setPetSpeech("正在播报");
}

function unmarkSpeaking() {
  setPetMode(null);
  setPetSpeech(`${state.digitalHuman?.scenic_area || "景区"}导览中`);
}

async function recommendRoute() {
  const interest = getComboValue(elements.interestSelect, elements.interestCustomInput, "兴趣偏好");
  const duration = getComboValue(elements.durationSelect, elements.durationCustomInput, "游览时长");
  if (!interest || !duration) {
    return;
  }

  elements.routeResult.className = "route-result empty-state";
  elements.routeResult.textContent = "正在生成路线...";

  try {
    const data = await apiFetch("/api/recommend/route", {
      method: "POST",
      body: JSON.stringify({
        interest,
        duration,
      }),
    });

    elements.routeResult.className = "route-result";
    elements.routeResult.innerHTML = renderRouteCard(data);
  } catch (error) {
    elements.routeResult.className = "route-result empty-state";
    elements.routeResult.textContent = "路线生成失败。";
    showToast(error.message, "error");
  }
}

function getComboValue(select, input, label) {
  const value = select.value === "custom" ? input.value.trim() : select.value;
  if (!value) {
    showToast(`请填写${label}。`, "error");
    input.focus();
    return "";
  }
  return value;
}

function syncComboInput(select, input) {
  const isCustom = select.value === "custom";
  input.classList.toggle("hidden", !isCustom);
  if (isCustom) {
    input.focus();
  } else {
    input.value = "";
  }
}

async function submitFeedback(logId, satisfaction, button) {
  try {
    await apiFetch("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ log_id: Number(logId), satisfaction: Number(satisfaction) }),
    });
    button.closest(".message-actions").querySelectorAll("button").forEach((item) => {
      item.disabled = true;
    });
    showToast(`已提交 ${satisfaction} 分反馈。`);
    loadAdminData({ silent: true });
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loginAdmin() {
  try {
    const data = await apiFetch("/api/admin/login", {
      method: "POST",
      body: JSON.stringify({
        username: elements.adminUsername.value.trim(),
        password: elements.adminPassword.value,
      }),
    });
    state.adminToken = data.token;
    localStorage.setItem("scenic_admin_token", data.token);
    elements.loginPanel.classList.add("hidden");
    elements.adminWorkspace.classList.remove("hidden");
    showToast(`欢迎，${data.display_name}`);
    await loadAdminData();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadAdminData({ silent = false } = {}) {
  if (!state.adminToken && elements.adminWorkspace.classList.contains("hidden")) {
    return;
  }

  try {
    const [dashboard, report, logs, docs, videoStatus] = await Promise.all([
      apiFetch("/api/admin/dashboard"),
      apiFetch("/api/admin/visitor-report"),
      apiFetch("/api/admin/logs?limit=50"),
      apiFetch("/api/admin/docs"),
      apiFetch("/api/admin/digital-video/status"),
    ]);
    renderDashboard(dashboard);
    renderVisitorReport(report);
    renderLogs(logs);
    renderKnowledgeDocs(docs);
    renderDigitalVideoStatus(videoStatus);
    if (!silent) {
      showToast("后台数据已刷新。");
    }
  } catch (error) {
    if (!silent) {
      showToast(error.message, "error");
    }
  }
}

function renderDashboard(data) {
  elements.todayVisitors.textContent = data.today_visitors ?? 0;
  elements.todayQaCount.textContent = data.today_qa_count ?? 0;
  elements.satisfactionRate.textContent = `${Math.round((data.satisfaction_rate ?? 0) * 100)}%`;
  renderOpsScreenOverview(data);
  renderHotQuestions(data.hot_questions || []);
  renderEmotion(data.emotion_distribution || []);
  renderWeeklyServiceTrend(data.weekly_service_trend || []);
  renderSatisfactionTrend(data.satisfaction_trend || []);
}

function renderOpsScreenOverview(data) {
  const weeklyTrend = data.weekly_service_trend || [];
  const satisfactionTrend = data.satisfaction_trend || [];
  const hotQuestions = data.hot_questions || [];
  const weekVisitors = weeklyTrend.reduce((sum, item) => sum + Number(item.visitors || 0), 0);
  const weekQaCount = weeklyTrend.reduce((sum, item) => sum + Number(item.qa_count || 0), 0);
  const satisfactionRate = Math.round((data.satisfaction_rate || 0) * 100);
  const topQuestion = hotQuestions[0];

  elements.bigTodayVisitors.textContent = data.today_visitors ?? 0;
  elements.bigWeekVisitors.textContent = weekVisitors;
  elements.bigWeekQaCount.textContent = weekQaCount;
  elements.bigSatisfactionRate.textContent = `${satisfactionRate}%`;
  elements.bigTopQuestion.textContent = toSimplifiedChinese(topQuestion?.name || "暂无热门问题");
  elements.bigInsightNote.textContent = topQuestion
    ? `最高频问题出现 ${topQuestion.count} 次`
    : "等待游客问答数据。";
  renderOpsScreenBars(elements.bigServiceBars, weeklyTrend, "qa_count", "暂无本周服务数据", (item) => item.qa_count);
  renderOpsScreenBars(
    elements.bigSatisfactionBars,
    satisfactionTrend,
    "satisfaction_rate",
    "暂无满意度趋势",
    (item) => `${Math.round((item.satisfaction_rate || 0) * 100)}%`
  );
}

function renderOpsScreenBars(target, items, valueKey, emptyText, valueLabel) {
  if (!items.length) {
    target.className = "ops-screen-bars empty";
    target.textContent = emptyText;
    return;
  }

  const values = items.map((item) => Number(item[valueKey] || 0));
  const max = Math.max(...values, 1);
  target.className = "ops-screen-bars";
  target.innerHTML = items
    .map((item) => {
      const rawValue = Number(item[valueKey] || 0);
      const width = Math.max(4, (rawValue / max) * 100);
      return `
        <div class="ops-screen-bar">
          <span>${escapeHtml(item.date.slice(5))}</span>
          <i><b style="width:${width}%"></b></i>
          <strong>${escapeHtml(valueLabel(item))}</strong>
        </div>
      `;
    })
    .join("");
}

function renderHotQuestions(items) {
  if (!items.length) {
    elements.hotQuestionsChart.className = "bar-chart empty-state";
    elements.hotQuestionsChart.textContent = "暂无热门问题。";
    return;
  }

  const max = Math.max(...items.map((item) => item.count), 1);
  elements.hotQuestionsChart.className = "bar-chart";
  elements.hotQuestionsChart.innerHTML = items
    .map((item) => {
      const width = Math.max(8, (item.count / max) * 100);
      return `
        <div class="bar-item" title="${escapeHtml(item.name)}">
          <span class="bar-label">${escapeHtml(item.name)}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${width}%"></span></span>
          <strong>${item.count}</strong>
        </div>
      `;
    })
    .join("");
}

function renderEmotion(items) {
  if (!items.length) {
    elements.emotionChart.className = "emotion-list empty-state";
    elements.emotionChart.textContent = "暂无情绪数据。";
    return;
  }

  const labels = {
    neutral: "中性",
    positive: "积极",
    negative: "消极",
  };
  elements.emotionChart.className = "emotion-list";
  elements.emotionChart.innerHTML = items
    .map(
      (item) => `
        <div class="emotion-item">
          <span>${labels[item.name] || escapeHtml(item.name)}</span>
          <strong>${item.value}</strong>
        </div>
      `
    )
    .join("");
}

function renderWeeklyServiceTrend(items) {
  if (!items.length) {
    elements.weeklyServiceTrend.className = "trend-list empty-state";
    elements.weeklyServiceTrend.textContent = "暂无本周服务数据。";
    return;
  }

  const max = Math.max(...items.map((item) => item.qa_count), 1);
  elements.weeklyServiceTrend.className = "trend-list";
  elements.weeklyServiceTrend.innerHTML = items
    .map((item) => {
      const width = Math.max(4, (item.qa_count / max) * 100);
      return `
        <div class="trend-item">
          <span>${escapeHtml(item.date.slice(5))}</span>
          <div class="trend-track" title="游客 ${item.visitors} / 问答 ${item.qa_count}">
            <i style="width:${width}%"></i>
          </div>
          <strong>${item.qa_count}</strong>
        </div>
      `;
    })
    .join("");
}

function renderSatisfactionTrend(items) {
  if (!items.length) {
    elements.satisfactionTrend.className = "trend-list empty-state";
    elements.satisfactionTrend.textContent = "暂无满意度趋势。";
    return;
  }

  elements.satisfactionTrend.className = "trend-list";
  elements.satisfactionTrend.innerHTML = items
    .map((item) => {
      const percent = Math.round((item.satisfaction_rate || 0) * 100);
      return `
        <div class="trend-item">
          <span>${escapeHtml(item.date.slice(5))}</span>
          <div class="trend-track" title="评分数 ${item.rating_count} / 满意度 ${percent}%">
            <i style="width:${Math.max(4, percent)}%"></i>
          </div>
          <strong>${percent}%</strong>
        </div>
      `;
    })
    .join("");
}

function renderVisitorReport(report) {
  elements.visitorReportSummary.textContent = toSimplifiedChinese(report.summary || "暂无分析摘要。");
  renderFocusPoints(report.focus_points || []);
  renderEmotionTrend(report.emotion_trend || []);
  renderServiceSuggestions(report.service_suggestions || []);
}

function renderFocusPoints(items) {
  if (!items.length) {
    elements.focusPointsList.className = "focus-list empty-state";
    elements.focusPointsList.textContent = "暂无高频关注点。";
    return;
  }

  elements.focusPointsList.className = "focus-list";
  elements.focusPointsList.innerHTML = items
    .map(
      (item) => `
        <div class="focus-item">
          <span>${escapeHtml(item.name)}</span>
          <strong>${item.count}</strong>
        </div>
      `
    )
    .join("");
}

function renderEmotionTrend(items) {
  if (!items.length) {
    elements.emotionTrendList.className = "trend-list empty-state";
    elements.emotionTrendList.textContent = "暂无七日趋势数据。";
    return;
  }

  const max = Math.max(...items.map((item) => item.positive + item.neutral + item.negative), 1);
  elements.emotionTrendList.className = "trend-list";
  elements.emotionTrendList.innerHTML = items
    .map((item) => {
      const total = item.positive + item.neutral + item.negative;
      const width = Math.max(4, (total / max) * 100);
      return `
        <div class="trend-item">
          <span>${escapeHtml(item.date.slice(5))}</span>
          <div class="trend-track" title="积极 ${item.positive} / 中性 ${item.neutral} / 消极 ${item.negative}">
            <i style="width:${width}%"></i>
          </div>
          <strong>${total}</strong>
        </div>
      `;
    })
    .join("");
}

function renderServiceSuggestions(items) {
  if (!items.length) {
    elements.serviceSuggestionsList.innerHTML = "<li>暂无建议。</li>";
    return;
  }

  elements.serviceSuggestionsList.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderLogs(logs = []) {
  if (!logs.length) {
    elements.logsTableBody.innerHTML = `<tr><td colspan="7">暂无问答日志。</td></tr>`;
    return;
  }

  elements.logsTableBody.innerHTML = logs
    .map(
      (item) => `
        <tr title="${escapeHtml(item.answer)}">
          <td data-label="ID">${item.id}</td>
          <td data-label="用户">${escapeHtml(item.user_id)}</td>
          <td data-label="问题">${escapeHtml(item.question)}</td>
          <td data-label="情绪">${escapeHtml(item.emotion)}</td>
          <td data-label="评分">${item.satisfaction ?? "-"}</td>
          <td data-label="耗时">${Number(item.response_seconds || 0).toFixed(2)}s</td>
          <td data-label="时间">${formatTime(item.created_at)}</td>
        </tr>
      `
    )
    .join("");
}

async function loadKnowledgeDocs({ silent = false } = {}) {
  if (!state.adminToken && elements.adminWorkspace.classList.contains("hidden")) {
    return;
  }

  try {
    const docs = await apiFetch("/api/admin/docs");
    renderKnowledgeDocs(docs);
    if (!silent) {
      showToast("知识库列表已刷新。");
    }
  } catch (error) {
    elements.knowledgeDocsList.textContent = "知识库加载失败。";
    if (!silent) {
      showToast(error.message, "error");
    }
  }
}

function renderKnowledgeDocs(docs = []) {
  if (!docs.length) {
    elements.knowledgeDocsList.className = "knowledge-docs empty-state";
    elements.knowledgeDocsList.textContent = "暂无知识文档，可先上传 .txt/.md/.docx/.xlsx。";
    return;
  }

  elements.knowledgeDocsList.className = "knowledge-docs";
  elements.knowledgeDocsList.innerHTML = docs
    .map(
      (doc) => `
        <article class="doc-card ${doc.id === state.selectedDocId ? "active" : ""}">
          <button type="button" data-doc-id="${doc.id}" class="doc-select-button">
            <strong>${escapeHtml(docDisplayName(doc))}</strong>
            <span>${escapeHtml(doc.source)} · ${escapeHtml(doc.content_type)} · ${doc.chunk_count} 条</span>
          </button>
          <div class="doc-actions">
            <button type="button" data-reimport-doc-id="${doc.id}">重新导入</button>
            <button type="button" data-delete-doc-id="${doc.id}">删除</button>
          </div>
        </article>
      `
    )
    .join("");
}

async function selectKnowledgeDoc(docId) {
  state.selectedDocId = Number(docId);
  elements.selectedDocInfo.className = "empty-state";
  elements.selectedDocInfo.textContent = "正在加载文档详情...";
  elements.knowledgeDocMetaForm.classList.add("hidden");
  elements.addChunkForm.classList.add("hidden");
  elements.knowledgeChunksPreview.innerHTML = "";

  try {
    const detail = await apiFetch(`/api/admin/docs/${state.selectedDocId}`);
    renderKnowledgeDetail(detail);
    loadKnowledgeDocs({ silent: true });
  } catch (error) {
    showToast(error.message, "error");
  }
}

function renderKnowledgeDetail(detail) {
  const { document, chunks } = detail;
  state.selectedDocId = document.id;
  elements.selectedDocInfo.className = "doc-summary";
  elements.selectedDocInfo.innerHTML = `
    <strong>${escapeHtml(docDisplayName(document))}</strong>
    <span>${escapeHtml(document.source)} · ${escapeHtml(document.status)} · ${document.chunk_count} 条知识片段</span>
  `;
  elements.docNameInput.value = document.name;
  elements.docSourceInput.value = document.source;
  elements.docStatusSelect.value = document.status;
  elements.knowledgeDocMetaForm.classList.remove("hidden");
  elements.addChunkForm.classList.remove("hidden");

  if (!chunks.length) {
    elements.knowledgeChunksPreview.className = "chunk-list empty-state";
    elements.knowledgeChunksPreview.textContent = "该文档暂无知识片段，可在下方新增。";
    return;
  }

  elements.knowledgeChunksPreview.className = "chunk-list";
  elements.knowledgeChunksPreview.innerHTML = chunks
    .map(
      (chunk) => `
        <article class="chunk-card" data-chunk-id="${chunk.id}">
          <div class="chunk-card-head">
            <strong>#${chunk.id}</strong>
            <span>${formatTime(chunk.created_at)}</span>
          </div>
          <input data-chunk-title="${chunk.id}" type="text" value="${escapeHtml(chunk.title)}" aria-label="知识片段标题" />
          <input data-chunk-tags="${chunk.id}" type="text" value="${escapeHtml(chunk.tags)}" aria-label="知识片段标签" />
          <textarea data-chunk-content="${chunk.id}" rows="5" aria-label="知识片段内容">${escapeHtml(chunk.content)}</textarea>
          <div class="chunk-actions">
            <button type="button" data-save-chunk-id="${chunk.id}">保存片段</button>
            <button type="button" data-delete-chunk-id="${chunk.id}">删除片段</button>
          </div>
        </article>
      `
    )
    .join("");
}

async function saveKnowledgeDocMeta() {
  if (!state.selectedDocId) {
    showToast("请先选择一个知识文档。", "error");
    return;
  }

  const payload = {
    name: elements.docNameInput.value.trim(),
    source: elements.docSourceInput.value.trim() || "admin",
    status: elements.docStatusSelect.value,
  };
  if (!payload.name) {
    showToast("文档名称不能为空。", "error");
    return;
  }

  try {
    const detail = await apiFetch(`/api/admin/docs/${state.selectedDocId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    renderKnowledgeDetail(detail);
    await loadKnowledgeDocs({ silent: true });
    showToast("文档信息已保存。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function addKnowledgeChunk() {
  if (!state.selectedDocId) {
    showToast("请先选择一个知识文档。", "error");
    return;
  }

  const payload = {
    title: elements.newChunkTitleInput.value.trim(),
    tags: elements.newChunkTagsInput.value.trim() || "manual",
    content: elements.newChunkContentInput.value.trim(),
  };
  if (!payload.content) {
    showToast("新增片段内容不能为空。", "error");
    return;
  }

  try {
    const detail = await apiFetch(`/api/admin/docs/${state.selectedDocId}/chunks`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    elements.newChunkTitleInput.value = "";
    elements.newChunkTagsInput.value = "";
    elements.newChunkContentInput.value = "";
    renderKnowledgeDetail(detail);
    await loadKnowledgeDocs({ silent: true });
    showToast("知识片段已新增。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function saveKnowledgeChunk(chunkId) {
  const payload = {
    title: $(`[data-chunk-title="${chunkId}"]`).value.trim(),
    tags: $(`[data-chunk-tags="${chunkId}"]`).value.trim(),
    content: $(`[data-chunk-content="${chunkId}"]`).value.trim(),
  };
  if (!payload.content) {
    showToast("知识片段内容不能为空。", "error");
    return;
  }

  try {
    const detail = await apiFetch(`/api/admin/docs/chunks/${chunkId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    renderKnowledgeDetail(detail);
    await loadKnowledgeDocs({ silent: true });
    showToast("知识片段已保存。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteKnowledgeChunk(chunkId) {
  if (!window.confirm("确认删除这个知识片段？删除后数字人将不再检索到该内容。")) {
    return;
  }

  try {
    const detail = await apiFetch(`/api/admin/docs/chunks/${chunkId}`, {
      method: "DELETE",
    });
    renderKnowledgeDetail(detail);
    await loadKnowledgeDocs({ silent: true });
    showToast("知识片段已删除。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function deleteKnowledgeDoc(docId) {
  if (!window.confirm("确认删除这个知识文档及其所有知识片段？")) {
    return;
  }

  try {
    await apiFetch(`/api/admin/docs/${docId}`, {
      method: "DELETE",
    });
    if (state.selectedDocId === Number(docId)) {
      state.selectedDocId = null;
      elements.selectedDocInfo.className = "empty-state";
      elements.selectedDocInfo.textContent = "选择左侧文档后，可查看、编辑、删除知识片段。";
      elements.knowledgeDocMetaForm.classList.add("hidden");
      elements.addChunkForm.classList.add("hidden");
      elements.knowledgeChunksPreview.innerHTML = "";
    }
    await loadKnowledgeDocs({ silent: true });
    showToast("知识文档已删除。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function reimportKnowledgeDoc(docId) {
  try {
    const detail = await apiFetch(`/api/admin/docs/${docId}/reimport`, {
      method: "POST",
    });
    renderKnowledgeDetail(detail);
    await loadKnowledgeDocs({ silent: true });
    showToast("知识文档已重新导入。");
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function uploadDocument() {
  const file = elements.docUploadInput.files?.[0];
  if (!file) {
    showToast("请先选择一个知识文档。", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  try {
    await apiFetch("/api/admin/docs/upload", {
      method: "POST",
      body: formData,
    });
    elements.docUploadInput.value = "";
    showToast("知识文档已上传并导入。");
    await loadKnowledgeDocs({ silent: true });
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function checkApiHealth() {
  try {
    const response = await fetch(buildApiUrl("/api/health"));
    if (!response.ok) {
      throw new Error("health check failed");
    }
    setApiStatus("服务在线", "ok");
  } catch {
    setApiStatus("服务异常", "bad");
  }
}

function bindEvents() {
  $$(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      $$(".tab-button").forEach((item) => item.classList.remove("active"));
      $$(".view").forEach((view) => view.classList.remove("active"));
      button.classList.add("active");
      $(`#${button.dataset.view}`).classList.add("active");
      if (button.dataset.view === "adminView" && state.adminToken) {
        elements.loginPanel.classList.add("hidden");
        elements.adminWorkspace.classList.remove("hidden");
        loadAdminData({ silent: true });
      }
    });
  });

  $$(".quick-questions button").forEach((button) => {
    button.addEventListener("click", () => {
      elements.questionInput.value = button.dataset.question;
      elements.questionInput.focus();
    });
  });

  $$(".guide-mode-button").forEach((button) => {
    button.addEventListener("click", () => {
      $$(".guide-mode-button").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      const question = button.dataset.question || "";
      const mode = button.dataset.guideMode || "qa";
      state.guideMode = mode;
      const placeholders = {
        qa: "输入你的问题，例如：九龙灌浴几点开始表演",
        route: "输入路线需求，例如：半天、亲子、避开人流",
        spot: "输入景点名称，例如：灵山大佛、梵宫、九龙灌浴",
        etiquette: "输入礼仪问题，例如：殿堂拍照需要注意什么",
      };
      elements.questionInput.placeholder = placeholders[mode] || placeholders.qa;
      if (question) {
        elements.questionInput.value = question;
      }
      elements.questionInput.focus();
      setPetSpeech(button.textContent.trim());
    });
  });

  elements.textChatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (state.guideMode === "route") {
      askRouteLecture(elements.questionInput.value);
      return;
    }
    askText(elements.questionInput.value);
  });

  elements.recordButton.addEventListener("click", toggleRecording);

  elements.voiceFileInput.addEventListener("change", () => {
    const file = elements.voiceFileInput.files?.[0];
    if (file) {
      sendVoice(file, file.name);
      elements.voiceFileInput.value = "";
    }
  });

  elements.routeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    recommendRoute();
  });

  elements.interestSelect.addEventListener("change", () => {
    syncComboInput(elements.interestSelect, elements.interestCustomInput);
  });

  elements.durationSelect.addEventListener("change", () => {
    syncComboInput(elements.durationSelect, elements.durationCustomInput);
  });

  elements.chatMessages.addEventListener("click", (event) => {
    const videoButton = event.target.closest("[data-video-url]");
    if (videoButton) {
      playDigitalVideo(videoButton.dataset.videoUrl, videoButton.dataset.fallbackAudioUrl || "");
      return;
    }

    const audioButton = event.target.closest("[data-audio-url]");
    if (audioButton) {
      playAudio(audioButton.dataset.audioUrl);
      return;
    }

    const ratingButton = event.target.closest("[data-rating]");
    if (ratingButton) {
      submitFeedback(ratingButton.dataset.logId, ratingButton.dataset.rating, ratingButton);
    }
  });

  elements.loginForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loginAdmin();
  });

  elements.refreshAdminButton.addEventListener("click", () => loadAdminData());
  elements.reloadLogsButton.addEventListener("click", () => loadAdminData());
  elements.reloadKnowledgeButton.addEventListener("click", () => loadKnowledgeDocs());
  elements.refreshVideoStatusButton.addEventListener("click", () => loadDigitalVideoStatus({ silent: false }));

  elements.uploadForm.addEventListener("submit", (event) => {
    event.preventDefault();
    uploadDocument();
  });

  elements.avatarUploadForm.addEventListener("submit", (event) => {
    event.preventDefault();
    uploadAvatarAsset();
  });

  elements.knowledgeDocMetaForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveKnowledgeDocMeta();
  });

  elements.addChunkForm.addEventListener("submit", (event) => {
    event.preventDefault();
    addKnowledgeChunk();
  });

  elements.knowledgeDocsList.addEventListener("click", (event) => {
    const selectButton = event.target.closest("[data-doc-id]");
    if (selectButton) {
      selectKnowledgeDoc(selectButton.dataset.docId);
      return;
    }

    const reimportButton = event.target.closest("[data-reimport-doc-id]");
    if (reimportButton) {
      reimportKnowledgeDoc(reimportButton.dataset.reimportDocId);
      return;
    }

    const deleteButton = event.target.closest("[data-delete-doc-id]");
    if (deleteButton) {
      deleteKnowledgeDoc(deleteButton.dataset.deleteDocId);
    }
  });

  elements.knowledgeChunksPreview.addEventListener("click", (event) => {
    const saveButton = event.target.closest("[data-save-chunk-id]");
    if (saveButton) {
      saveKnowledgeChunk(saveButton.dataset.saveChunkId);
      return;
    }

    const deleteButton = event.target.closest("[data-delete-chunk-id]");
    if (deleteButton) {
      deleteKnowledgeChunk(deleteButton.dataset.deleteChunkId);
    }
  });

  elements.digitalHumanForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveDigitalHumanConfig();
  });

  elements.previewDigitalHumanButton.addEventListener("click", () => {
    applyDigitalHumanConfig(readDigitalHumanForm());
    showToast("已预览到游客端。");
  });
}

async function boot() {
  configureRuntimeLinks();
  bindEvents();
  bindLicensedAvatarAsset();
  checkApiHealth();
  await loadDigitalHumanConfig();
  await loadDigitalVideoStatus();
  const config = state.digitalHuman || {
    scenic_area: "灵山胜境",
    greeting: "当前示范景区为灵山胜境，已接入对应知识库、路线推荐与语音播报能力。",
    fallback_message: "数字人视频暂不可用，已切换为语音讲解。",
    service_boundary: "仅基于景区知识库进行导览讲解，不提供功德承诺、神迹保证或占卜预测。",
  };
  addMessage(
    "assistant",
    `
      <strong>你好，我是景区导览数字人。</strong>
      <div>${escapeHtml(config.greeting)}</div>
      ${renderReferenceTags([config.scenic_area, "九龙灌浴", "灵山大佛"])}
    `
  );
  recommendRoute();

  if (state.adminToken) {
    elements.loginPanel.classList.add("hidden");
    elements.adminWorkspace.classList.remove("hidden");
    loadAdminData({ silent: true });
  }
}

boot();
