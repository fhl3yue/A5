const state = {
  currentLogId: null,
  audio: null,
  audioContext: null,
  audioAnalyser: null,
  audioSource: null,
  lipSyncFrame: null,
  lipSyncBuffer: null,
  lipSyncCues: null,
  lipSyncCueFrame: null,
  lipSyncCueStartedAt: 0,
  video: null,
  answerTranslations: {},
  answerPayloads: {},
  pendingAudioPolls: {},
  pendingServerAudioRequests: {},
  localSpeechUtterance: null,
  localSpeechTimer: null,
  avatarOnlyEnabled: false,
  avatarOnlyReady: false,
  openAvatar: null,
  openAvatarReady: false,
  openAvatarLastSpokenLogId: null,
  openAvatarHealth: null,
  openAvatarBlankReports: 0,
  openAvatarReadyReports: 0,
  openAvatarSuppressed: false,
  recorder: null,
  recordingStream: null,
  recordingChunks: [],
  adminToken: localStorage.getItem("scenic_admin_token") || "",
  digitalHuman: null,
  selectedDocId: null,
  guideMode: "qa",
};

const RHUBARB_VISEMES = {
  A: { shape: "x", open: 0.02 },
  B: { shape: "f", open: 0.12 },
  C: { shape: "e", open: 0.34 },
  D: { shape: "a", open: 0.58 },
  E: { shape: "o", open: 0.5 },
  F: { shape: "f", open: 0.22 },
  G: { shape: "a", open: 0.82 },
  H: { shape: "o", open: 0.78 },
  X: { shape: "x", open: 0.04 },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const DEFAULT_AVATAR_URL = "./assets/avatar/avatar-guide-v1.png";
const LEGACY_LICENSED_AVATAR_URL = "./assets/avatar/licensed-character.png";
const CUSTOM_AVATAR_THEMES = new Set(["asset-avatar", "licensed-asset"]);
const runtimeParams = new URLSearchParams(window.location.search);
const runtimeClient = (runtimeParams.get("client") || "").toLowerCase().replace(/[^a-z0-9_-]/g, "");
const debugFaceRig = runtimeParams.get("debugFace") === "1";
const AVATAR_REVEAL_MIN_MS = 900;
const AVATAR_REVEAL_MAX_MS = 10000;
const AVATAR_REVEAL_POLL_MS = 700;
const AVATAR_REVEAL_PRELOAD_MS = 1800;

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
const GUIDE_MODE_META = {
  qa: {
    label: "问答讲解",
    placeholder: "输入你的问题，例如：九龙灌浴几点开始表演",
    question: "",
  },
  route: {
    label: "路线讲解",
    placeholder: "输入路线需求，例如：半天、亲子、避开人流",
    question: "请按半天行程讲解一条适合初次游客的路线",
  },
  spot: {
    label: "景点讲解",
    placeholder: "输入景点名称，例如：灵山大佛、梵宫、九龙灌浴",
    question: "请讲解灵山大佛的文化含义和参观重点",
  },
  etiquette: {
    label: "礼仪提示",
    placeholder: "输入礼仪问题，例如：殿堂拍照需要注意什么",
    question: "参观灵山胜境需要注意哪些文化礼仪",
  },
};

if (runtimeClient) {
  document.body.classList.add(`client-${runtimeClient}`);
}
if (debugFaceRig) {
  document.body.classList.add("debug-face-rig");
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
  avatarStandbyVideo: $("#avatarStandbyVideo"),
  openAvatarLayer: $("#openAvatarLayer"),
  openAvatarFrame: $("#openAvatarFrame"),
  openAvatarStatusText: $("#openAvatarStatusText"),
  openAvatarEntry: $("#openAvatarEntry"),
  openAvatarEntryText: $("#openAvatarEntryText"),
  openAvatarToggleButton: $("#openAvatarToggleButton"),
  closeOpenAvatarButton: $("#closeOpenAvatarButton"),
  guideStatus: $("#guideStatus"),
  guideSubtitle: $("#guideSubtitle"),
  chatMessages: $("#chatMessages"),
  textChatForm: $("#textChatForm"),
  chatSubmitButton: $("#chatSubmitButton"),
  guideModeSelect: $("#guideModeSelect"),
  questionInput: $("#questionInput"),
  recordButton: $("#recordButton"),
  voiceHint: $("#voiceHint"),
  voiceFileInput: $("#voiceFileInput"),
  imageFileInput: $("#imageFileInput"),
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
  rebuildRagButton: $("#rebuildRagButton"),
  ragEnabled: $("#ragEnabled"),
  ragConfigured: $("#ragConfigured"),
  ragModelName: $("#ragModelName"),
  ragDimension: $("#ragDimension"),
  ragIndexedChunks: $("#ragIndexedChunks"),
  ragLastUpdated: $("#ragLastUpdated"),
  ragLastError: $("#ragLastError"),
  aiMainModelStatus: $("#aiMainModelStatus"),
  aiMainModelName: $("#aiMainModelName"),
  aiRagStatus: $("#aiRagStatus"),
  aiVisionStatus: $("#aiVisionStatus"),
  aiTtsStatus: $("#aiTtsStatus"),
  aiServerTtsStatus: $("#aiServerTtsStatus"),
  aiEnglishStatus: $("#aiEnglishStatus"),
  aiLipsyncStatus: $("#aiLipsyncStatus"),
  aiOpenAvatarStatus: $("#aiOpenAvatarStatus"),
  runEvaluationButton: $("#runEvaluationButton"),
  evaluationPassed: $("#evaluationPassed"),
  evaluationAccuracy: $("#evaluationAccuracy"),
  evaluationLatency: $("#evaluationLatency"),
  evaluationCases: $("#evaluationCases"),
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
  applyFaceRig({ emotion: mode || "neutral" });
}

function normalizeMouthShape(shape) {
  return ["x", "a", "o", "e", "f"].includes(shape) ? shape : "x";
}

function applyFaceRig(params = {}) {
  if (!elements.avatarFrame) {
    return;
  }
  const mouthOpen = Math.max(0, Math.min(1, Number(params.mouthOpen ?? 0)));
  const shape = normalizeMouthShape(params.mouthShape || (mouthOpen > 0.55 ? "a" : mouthOpen > 0.2 ? "e" : "x"));
  const emotion = params.emotion || "";
  const speakingBoost = emotion === "speaking" ? 0.12 : 0;
  const eyeOpen = Math.max(0.08, Math.min(1.15, Number(params.eyeOpen ?? (emotion === "listening" ? 0.86 : 1))));
  const browLift = Number(params.browLift ?? (emotion === "thinking" ? 4 : emotion === "success" ? 2 : 0));
  const headYaw = Number(params.headYaw ?? (mouthOpen * 1.4));
  const headPitch = Number(params.headPitch ?? (-mouthOpen * 3));
  const smile = Number(params.smile ?? (emotion === "success" ? 3 : 0));
  const shapeWeights = {
    x: shape === "x" ? 1 : 0,
    a: shape === "a" ? 1 : 0,
    o: shape === "o" ? 1 : 0,
    e: shape === "e" ? 1 : 0,
    f: shape === "f" ? 1 : 0,
  };

  elements.avatarFrame.style.setProperty("--mouth-open", mouthOpen.toFixed(3));
  elements.avatarFrame.style.setProperty("--voice-level", Number(params.voiceLevel ?? mouthOpen / 4).toFixed(3));
  elements.avatarFrame.style.setProperty("--mouth-scale", (0.55 + mouthOpen * 1.75 + speakingBoost).toFixed(3));
  elements.avatarFrame.style.setProperty("--mouth-shift", `${(mouthOpen * 3).toFixed(2)}px`);
  elements.avatarFrame.style.setProperty("--mouth-stroke", `${(5 + mouthOpen * 10).toFixed(2)}px`);
  elements.avatarFrame.style.setProperty("--head-lift", `${headPitch.toFixed(2)}px`);
  elements.avatarFrame.style.setProperty("--head-rotate", `${headYaw.toFixed(2)}deg`);
  elements.avatarFrame.style.setProperty("--avatar-lift", `${(-mouthOpen * 12).toFixed(2)}px`);
  elements.avatarFrame.style.setProperty("--avatar-scale", (1 + mouthOpen * 0.035).toFixed(3));
  elements.avatarFrame.style.setProperty("--voice-glow", `${(16 + mouthOpen * 18).toFixed(2)}px`);
  elements.avatarFrame.style.setProperty("--eye-scale", eyeOpen.toFixed(3));
  elements.avatarFrame.style.setProperty("--face-mouth-x", shapeWeights.x.toFixed(3));
  elements.avatarFrame.style.setProperty("--face-mouth-a", shapeWeights.a.toFixed(3));
  elements.avatarFrame.style.setProperty("--face-mouth-o", shapeWeights.o.toFixed(3));
  elements.avatarFrame.style.setProperty("--face-mouth-e", shapeWeights.e.toFixed(3));
  elements.avatarFrame.style.setProperty("--face-mouth-f", shapeWeights.f.toFixed(3));
  elements.avatarFrame.style.setProperty("--face-eye-open", eyeOpen.toFixed(3));
  elements.avatarFrame.style.setProperty("--face-brow-lift", `${browLift.toFixed(2)}px`);
  elements.avatarFrame.style.setProperty("--face-head-yaw", `${headYaw.toFixed(2)}deg`);
  elements.avatarFrame.style.setProperty("--face-head-pitch", `${headPitch.toFixed(2)}px`);
  elements.avatarFrame.style.setProperty("--face-smile", `${smile.toFixed(2)}px`);
  elements.avatarFrame.dataset.mouthShape = shape;
}

function isMobileRuntime() {
  return runtimeClient === "android" || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || "");
}

function browserLocalTtsSupported() {
  return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

function preferredTtsMode() {
  if (state.avatarOnlyEnabled) {
    return "server_only";
  }
  return browserLocalTtsSupported() ? "local_preferred" : "server_only";
}

function pickChineseVoice() {
  if (!browserLocalTtsSupported()) {
    return null;
  }
  const voices = window.speechSynthesis.getVoices() || [];
  return (
    voices.find((voice) => voice.lang === "zh-CN") ||
    voices.find((voice) => /^zh/i.test(voice.lang || "")) ||
    voices.find((voice) => /Chinese|Mandarin|Xiaoxiao|Yunxi/i.test(`${voice.name} ${voice.lang}`)) ||
    null
  );
}

function waitForChineseVoice(timeoutMs = 700) {
  const voice = pickChineseVoice();
  if (voice) {
    return Promise.resolve(voice);
  }
  return new Promise((resolve) => {
    let settled = false;
    const finish = (nextVoice) => {
      if (settled) {
        return;
      }
      settled = true;
      window.speechSynthesis.onvoiceschanged = null;
      resolve(nextVoice || null);
    };
    window.speechSynthesis.onvoiceschanged = () => finish(pickChineseVoice());
    window.setTimeout(() => finish(pickChineseVoice()), timeoutMs);
  });
}

function pulseLocalSpeechMouth() {
  if (!elements.avatarFrame) {
    return;
  }
  const mouthOpen = 0.28 + Math.random() * 0.42;
  elements.avatarFrame.classList.add("audio-driven-speaking");
  const shapes = ["a", "e", "o", "f"];
  applyFaceRig({
    mouthOpen,
    mouthShape: shapes[Math.floor(Math.random() * shapes.length)],
    voiceLevel: mouthOpen / 4,
    eyeOpen: 1 - mouthOpen * 0.06,
    headYaw: mouthOpen * 1.1,
    headPitch: -mouthOpen * 2.4,
    emotion: "speaking",
  });
}

function startLocalSpeechLipSync() {
  markSpeaking();
  window.clearInterval(state.localSpeechTimer);
  state.localSpeechTimer = window.setInterval(pulseLocalSpeechMouth, 120);
  pulseLocalSpeechMouth();
}

function stopLocalSpeech() {
  window.clearInterval(state.localSpeechTimer);
  state.localSpeechTimer = null;
  if (state.localSpeechUtterance) {
    state.localSpeechUtterance.onstart = null;
    state.localSpeechUtterance.onend = null;
    state.localSpeechUtterance.onerror = null;
    state.localSpeechUtterance.onboundary = null;
  }
  state.localSpeechUtterance = null;
  if (browserLocalTtsSupported()) {
    window.speechSynthesis.cancel();
  }
}

function resetLipSync() {
  if (state.lipSyncFrame) {
    cancelAnimationFrame(state.lipSyncFrame);
  }
  if (state.lipSyncCueFrame) {
    cancelAnimationFrame(state.lipSyncCueFrame);
  }
  window.clearInterval(state.localSpeechTimer);
  state.localSpeechTimer = null;
  try {
    state.audioSource?.disconnect();
    state.audioAnalyser?.disconnect();
  } catch {
    // Audio graph may already be closed by the browser.
  }
  state.lipSyncFrame = null;
  state.lipSyncCueFrame = null;
  state.lipSyncCueStartedAt = 0;
  state.lipSyncCues = null;
  state.audioAnalyser = null;
  state.audioSource = null;
  state.lipSyncBuffer = null;
  if (elements.avatarFrame) {
    elements.avatarFrame.classList.remove("audio-driven-speaking");
    elements.avatarFrame.style.setProperty("--mouth-open", "0");
    elements.avatarFrame.style.setProperty("--voice-level", "0");
    elements.avatarFrame.style.setProperty("--mouth-scale", "1");
    elements.avatarFrame.style.setProperty("--mouth-shift", "0px");
    elements.avatarFrame.style.setProperty("--mouth-stroke", "7px");
    elements.avatarFrame.style.setProperty("--head-lift", "0px");
    elements.avatarFrame.style.setProperty("--head-rotate", "0deg");
    elements.avatarFrame.style.setProperty("--avatar-lift", "0px");
    elements.avatarFrame.style.setProperty("--avatar-scale", "1");
    elements.avatarFrame.style.setProperty("--voice-glow", "18px");
    elements.avatarFrame.style.setProperty("--eye-scale", "1");
    applyFaceRig({ mouthOpen: 0, mouthShape: "x", emotion: "neutral" });
  }
}

async function loadMouthCues(lipsyncUrl) {
  if (!lipsyncUrl) {
    return null;
  }
  try {
    const response = await fetch(resolveMediaUrl(lipsyncUrl));
    if (!response.ok) {
      return null;
    }
    const payload = await response.json();
    return Array.isArray(payload.mouthCues) ? payload.mouthCues : null;
  } catch {
    return null;
  }
}

function withTimeout(promise, timeoutMs, fallback = null) {
  return Promise.race([
    promise,
    new Promise((resolve) => window.setTimeout(() => resolve(fallback), timeoutMs)),
  ]);
}

function applyRhubarbCue(cue) {
  const viseme = RHUBARB_VISEMES[cue?.value] || RHUBARB_VISEMES.X;
  applyFaceRig({
    mouthOpen: viseme.open,
    mouthShape: viseme.shape,
    voiceLevel: viseme.open / 3,
    eyeOpen: 1 - viseme.open * 0.05,
    headYaw: viseme.open * 1.2,
    headPitch: -viseme.open * 2.2,
    emotion: "speaking",
  });
}

function startCueLipSync(audio, cues) {
  if (!audio || !Array.isArray(cues) || cues.length === 0 || !elements.avatarFrame) {
    return false;
  }
  markSpeaking();
  elements.avatarFrame.classList.add("audio-driven-speaking");
  state.lipSyncCues = cues;
  const tick = () => {
    if (!state.audio || state.audio !== audio || audio.paused || audio.ended) {
      return;
    }
    const current = audio.currentTime;
    const cue = cues.find((item) => current >= Number(item.start) && current < Number(item.end));
    applyRhubarbCue(cue || { value: "X" });
    state.lipSyncCueFrame = requestAnimationFrame(tick);
  };
  tick();
  return true;
}

function startAudioLipSync(audio) {
  markSpeaking();
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass || !audio || !elements.avatarFrame) {
    return;
  }

  try {
    state.audioContext = state.audioContext || new AudioContextClass();
    if (state.audioContext.state === "suspended") {
      state.audioContext.resume();
    }
    const analyser = state.audioContext.createAnalyser();
    analyser.fftSize = 1024;
    analyser.smoothingTimeConstant = 0.58;
    const source = state.audioContext.createMediaElementSource(audio);
    source.connect(analyser);
    analyser.connect(state.audioContext.destination);
    state.audioAnalyser = analyser;
    state.audioSource = source;
    state.lipSyncBuffer = new Uint8Array(analyser.fftSize);
    elements.avatarFrame.classList.add("audio-driven-speaking");
    pumpLipSync();
  } catch {
    elements.avatarFrame.classList.add("audio-driven-speaking");
    applyFaceRig({ mouthOpen: 0.34, mouthShape: "e", emotion: "speaking" });
  }
}

function pumpLipSync() {
  if (!state.audioAnalyser || !state.lipSyncBuffer || !elements.avatarFrame) {
    return;
  }
  state.audioAnalyser.getByteTimeDomainData(state.lipSyncBuffer);
  let sum = 0;
  for (const value of state.lipSyncBuffer) {
    const centered = (value - 128) / 128;
    sum += centered * centered;
  }
  const rms = Math.sqrt(sum / state.lipSyncBuffer.length);
  const mouthOpen = Math.max(0.04, Math.min(1, rms * 4.8));
  const shape = mouthOpen > 0.72 ? "a" : mouthOpen > 0.48 ? "o" : mouthOpen > 0.22 ? "e" : "x";
  applyFaceRig({
    mouthOpen,
    mouthShape: shape,
    voiceLevel: rms,
    eyeOpen: 1 - mouthOpen * 0.08,
    headYaw: mouthOpen * 1.4,
    headPitch: -mouthOpen * 3,
    emotion: "speaking",
  });
  state.lipSyncFrame = requestAnimationFrame(pumpLipSync);
}

function applyGuideMode(mode, { autofill = false } = {}) {
  const nextMode = GUIDE_MODE_META[mode] ? mode : "qa";
  const meta = GUIDE_MODE_META[nextMode];
  state.guideMode = nextMode;
  if (elements.guideModeSelect) {
    elements.guideModeSelect.value = nextMode;
  }
  elements.questionInput.placeholder = meta.placeholder;
  if (autofill && meta.question) {
    elements.questionInput.value = meta.question;
  }
  setPetSpeech(meta.label);
}

function voiceLabel(voiceName) {
  const labels = {
    "zh-CN-XiaoxiaoNeural": "鏅撴檽濂冲０",
    "zh-CN-YunxiNeural": "浜戝笇鐢峰０",
    "zh-CN-XiaoyiNeural": "鏅撲紛濂冲０",
    "zh-CN-YunjianNeural": "浜戝仴鐢峰０",
  };
  return labels[voiceName] || voiceName || "涓枃澹扮嚎";
}

function looksLikeGarbledName(value) {
  return /[鈺涒暋鈺熲敩鈹溾暀鈺暕鈻屸暔鈺栤晸鈹粹晹鈺溾暊鈺晻鈹€]|芒|脙|脗/.test(value || "");
}

function docDisplayName(doc) {
  if (!looksLikeGarbledName(doc.name)) {
    return doc.name;
  }
  if (doc.content_type === "xlsx") {
    return "瀹樻柟娓稿琛屼负鏁版嵁.xlsx";
  }
  if (doc.chunk_count >= 50) {
    return "瀹樻柟鏅尯鏂囨梾璧勬枡.docx";
  }
  return "瀹樻柟鏅尯缁撴瀯璧勬枡.docx";
}

function themeClass(outfitTheme) {
  const classes = {
    "bio-face-rig": "theme-bio-face-rig",
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
    video_provider_status: "澶栭儴瑙嗛 API",
  };
}

function fillDigitalHumanForm(config) {
  if (!elements.digitalHumanForm || !config) {
    return;
  }
  elements.dhNameInput.value = config.name || "灵灵";
  elements.dhRoleInput.value = config.role_title || "景区 AI 导览员";
  elements.dhScenicInput.value = config.scenic_area || "灵山胜境";
  elements.dhOutfitSelect.value = config.outfit_theme || "asset-avatar";
  elements.dhVoiceSelect.value = config.voice_name || "zh-CN-XiaoxiaoNeural";
  elements.dhAvatarAssetUrlInput.value = config.avatar_asset_url || DEFAULT_AVATAR_URL;
  elements.dhGreetingInput.value = config.greeting || "";
  elements.dhFallbackMessageInput.value = config.fallback_message || "数字人视频暂不可用，已切换为语音讲解。";
  elements.dhServiceBoundaryInput.value =
    config.service_boundary || "仅基于景区知识库进行导览讲解，不提供功德承诺、神迹保证或占卜预测。";
}

function applyDigitalHumanConfig(config) {
  if (!config) {
    return;
  }
  state.digitalHuman = config;
  document.body.classList.remove("theme-bio-face-rig", "theme-asset-avatar", "theme-heritage-gold", "theme-lake-blue", "theme-festival-red", "theme-licensed-asset");
  const nextTheme = themeClass(config.outfit_theme);
  if (nextTheme) {
    document.body.classList.add(nextTheme);
  }
  const assetUrl = state.avatarOnlyEnabled
    ? ""
    : CUSTOM_AVATAR_THEMES.has(config.outfit_theme)
    ? config.avatar_asset_url || (config.outfit_theme === "licensed-asset" ? LEGACY_LICENSED_AVATAR_URL : "")
    : "";
  syncLicensedAvatarAsset(assetUrl);

  elements.petNameplate.textContent = `${config.name} · ${config.role_title}`;
  elements.petSpeech.textContent = `${config.scenic_area}导览中`;
  elements.guideSubtitle.textContent = config.greeting;
  if (elements.visitorFallbackMessage) {
    elements.visitorFallbackMessage.textContent = "可直接提问";
  }
  if (elements.visitorServiceBoundary) {
    elements.visitorServiceBoundary.textContent = "围绕景区服务";
  }

  if (elements.configScenicArea) {
    elements.configScenicArea.textContent = config.scenic_area;
    elements.configKnowledgeName.textContent = config.scenic_area;
    elements.configAvatarName.textContent = config.name;
    elements.configVoiceName.textContent = voiceLabel(config.voice_name);
  }
  fillDigitalHumanForm(config);
}

function setAvatarOnlyMode(enabled, ready = false) {
  state.avatarOnlyEnabled = Boolean(enabled);
  state.avatarOnlyReady = Boolean(ready);
  document.body.classList.toggle("avatar-only-mode", state.avatarOnlyEnabled);
  if (state.avatarOnlyEnabled) {
    window.setTimeout(startAvatarStandbyLoop, 0);
  } else {
    pauseAvatarStandbyLoop();
  }
  if (state.avatarOnlyEnabled) {
    document.body.classList.remove("custom-avatar-active", "licensed-avatar-ready");
    if (elements.licensedAvatarImage) {
      elements.licensedAvatarImage.removeAttribute("src");
    }
    if (!elements.avatarFrame?.classList.contains("video-active")) {
      setPetSpeech(state.avatarOnlyReady ? "真人数字人待命" : "真人数字人服务待启动");
    }
  }
}

function startAvatarStandbyLoop() {
  const standby = elements.avatarStandbyVideo;
  if (!standby || !state.avatarOnlyEnabled || elements.avatarFrame?.classList.contains("video-active")) {
    return;
  }
  standby.muted = true;
  standby.loop = true;
  standby.playsInline = true;
  const playPromise = standby.play();
  if (playPromise?.catch) {
    playPromise.catch(() => {
      // Muted autoplay is normally allowed; if blocked, the poster remains visible.
    });
  }
}

function pauseAvatarStandbyLoop() {
  const standby = elements.avatarStandbyVideo;
  if (!standby) {
    return;
  }
  standby.pause();
}

function bindAvatarStandbyVideo() {
  const standby = elements.avatarStandbyVideo;
  if (!standby) {
    return;
  }
  standby.muted = true;
  standby.loop = true;
  standby.playsInline = true;
  standby.addEventListener("canplay", startAvatarStandbyLoop);
  standby.addEventListener("loadeddata", startAvatarStandbyLoop);
  window.addEventListener("focus", startAvatarStandbyLoop);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      startAvatarStandbyLoop();
    }
  });
  document.addEventListener("pointerdown", startAvatarStandbyLoop, { once: true });
  document.addEventListener("keydown", startAvatarStandbyLoop, { once: true });
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
    document.body.classList.remove("custom-avatar-active");
  });
}

async function syncLicensedAvatarAsset(assetUrl) {
  if (!elements.licensedAvatarImage) {
    return;
  }
  if (state.avatarOnlyEnabled) {
    elements.licensedAvatarImage.removeAttribute("src");
    document.body.classList.remove("licensed-avatar-ready", "custom-avatar-active");
    return;
  }
  const isDeprecatedDefaultAvatar = /assets\/avatar\/default-guide-avatar\./i.test(assetUrl || "");
  if (!assetUrl || isDeprecatedDefaultAvatar) {
    elements.licensedAvatarImage.removeAttribute("src");
    document.body.classList.remove("licensed-avatar-ready");
    document.body.classList.remove("custom-avatar-active");
    return;
  }

  document.body.classList.add("custom-avatar-active");
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
    showToast(`鏁板瓧浜洪厤缃姞杞藉け璐ワ細${error.message}`, "error");
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

async function loadRagStatus({ silent = true } = {}) {
  if (!elements.ragEnabled) {
    return;
  }
  try {
    const status = await apiFetch("/api/admin/rag/status");
    renderRagStatus(status);
  } catch (error) {
    if (!silent) {
      showToast(error.message, "error");
    }
  }
}

async function loadAiCapabilityStatus({ silent = true } = {}) {
  try {
    const status = await apiFetch("/api/admin/ai/status");
    renderAiStatus(status);
  } catch (error) {
    if (!silent) {
      showToast(error.message, "error");
    }
  }
}

function renderDigitalVideoStatus(status) {
  const providerLabel = status.avatar_only_enabled ? "LiteAvatar-only" : "外部视频";
  const enabledText = status.enabled ? (status.configured ? `${providerLabel} 已启用` : "未配置地址") : "未启用";
  setAvatarOnlyMode(status.avatar_only_enabled, status.avatar_only_ready);
  elements.videoProviderEnabled.textContent = enabledText;
  elements.videoProviderLastStatus.textContent = status.last_status || "-";
  elements.videoProviderAverage.textContent = `${Number(status.average_response_seconds || 0).toFixed(2)}s`;
  elements.videoProviderFallbacks.textContent = status.fallback_count ?? 0;
  elements.videoProviderFailure.textContent = status.last_failure_reason || status.last_message || "无";
  if (elements.visitorVideoStatus) {
    elements.visitorVideoStatus.textContent = status.avatar_only_enabled
      ? (status.avatar_only_ready ? "真人讲解已预热" : "真人讲解待启动")
      : (status.enabled ? "可生成数字人讲解" : "语音讲解可用");
  }
}

function renderRagStatus(status) {
  elements.ragEnabled.textContent = status.enabled ? "已启用" : "已关闭";
  elements.ragConfigured.textContent = status.configured ? "已配置" : "缺少 Key";
  elements.ragModelName.textContent = status.model_name || "-";
  elements.ragDimension.textContent = status.dimension || "-";
  elements.ragIndexedChunks.textContent = `${status.indexed_chunks ?? 0} / ${status.total_chunks ?? 0}`;
  elements.ragLastUpdated.textContent = formatTime(status.last_updated);
  elements.ragLastError.textContent = status.last_error || "无";
}

function renderAiStatus(status) {
  if (!elements.aiMainModelStatus || !status) {
    return;
  }
  elements.aiMainModelStatus.textContent = status.main_model_configured ? "已配置" : "未配置";
  elements.aiMainModelName.textContent = status.main_model_name || "-";
  elements.aiRagStatus.textContent = status.rag_enabled ? (status.rag_configured ? "向量检索" : "关键词降级") : "关闭";
  if (elements.aiVisionStatus) {
    elements.aiVisionStatus.textContent = status.vision_enabled
      ? (status.vision_configured ? `${status.vision_model_name || "视觉模型"} 已配置` : "缺少视觉 Key")
      : "关闭";
  }
  elements.aiTtsStatus.textContent = status.tts_enabled ? "中文语音开启" : "中文语音关闭";
  if (elements.aiServerTtsStatus) {
    const lastProvider = status.server_tts_last_provider || status.server_tts_provider || "-";
    const localLabel = status.local_tts_enabled ? "本地优先" : "本地未启用";
    const readyLabel = status.server_tts_ready ? "可用" : "待生成";
    const cacheLabel = status.edge_tts_cache_enabled
      ? `缓存${status.edge_tts_cache_items ?? 0}条${status.edge_tts_cache_last_hit ? " / 刚命中" : ""}`
      : "缓存关闭";
    elements.aiServerTtsStatus.textContent = `${lastProvider} / ${localLabel} / ${readyLabel} / ${cacheLabel}`;
  }
  elements.aiEnglishStatus.textContent = status.english_available
    ? (status.english_tts_enabled ? "英文文本+语音" : "英文文本")
    : "未配置";
  if (elements.aiLipsyncStatus) {
    const rhubarbLabel = status.rhubarb_lipsync_enabled
      ? (status.rhubarb_lipsync_available ? "Rhubarb 口型" : "Rhubarb 未安装")
      : "RMS 兜底";
    const cacheLabel = status.lipsync_cache_enabled ? `缓存${status.lipsync_cache_items ?? 0}条` : "缓存关闭";
    const avatarLabel = status.avatar_only_enabled
      ? (status.avatar_only_ready ? "LiteAvatar-only 就绪" : "LiteAvatar-only 未就绪")
      : "数字人视频未启用";
    elements.aiLipsyncStatus.textContent = `${rhubarbLabel} / ${cacheLabel} / ${avatarLabel}`;
  }
  renderOpenAvatarStatus(status);
}

function renderOpenAvatarStatus(status = {}) {
  state.openAvatar = status;
  const enabled = Boolean(status.openavatar_enabled);
  const configured = Boolean(status.openavatar_configured);
  const ready = Boolean(status.openavatar_ready);
  const uiUrl = status.openavatar_ui_url || "";
  const profile = status.openavatar_profile || "LiteAvatar";
  const elapsed = Number(status.openavatar_last_elapsed_seconds || 0).toFixed(2);

  let label = "未启用";
  let detail = "完整 OpenAvatarChat 嵌入未启用，当前优先使用 LiteAvatar-only 数字人视频链路。";
  if (enabled && !configured) {
    label = "未配置";
    detail = "完整 OpenAvatarChat 地址未配置。";
  } else if (enabled && ready) {
    label = `已就绪 · ${profile}`;
    detail = `完整 OpenAvatarChat 已就绪，检测 ${elapsed}s。`;
  } else if (enabled) {
    label = "未就绪";
    detail = "完整 OpenAvatarChat 服务未启动或正在加载。";
  }

  if (elements.aiOpenAvatarStatus) {
    elements.aiOpenAvatarStatus.textContent = label;
  }
  if (elements.openAvatarStatusText) {
    elements.openAvatarStatusText.textContent = label;
  }
  if (elements.openAvatarEntryText) {
    elements.openAvatarEntryText.textContent = detail;
  }
  if (elements.openAvatarToggleButton) {
    elements.openAvatarToggleButton.disabled = !(enabled && configured && ready && uiUrl);
    elements.openAvatarToggleButton.textContent = document.body.classList.contains("openavatar-active")
      ? "关闭数字人"
      : "启用数字人";
  }
}

function getOpenAvatarEmbedUrl(rawUrl) {
  const base = String(rawUrl || "").trim();
  if (!base) return "";
  try {
    const url = new URL(base, window.location.href);
    url.searchParams.set("embed", "1");
    return url.toString();
  } catch {
    const separator = base.includes("?") ? "&" : "?";
    return `${base}${separator}embed=1`;
  }
}

function ensureOpenAvatarStage(options = {}) {
  // The visitor experience now uses LiteAvatar avatar-only MP4 output.
  // Keep the legacy full OpenAvatarChat iframe disabled unless it is
  // explicitly re-enabled for debugging in the future.
  document.body.classList.add("openavatar-suppressed");
  document.body.classList.remove("openavatar-active");
  if (!options.silent) {
    showToast("当前使用 LiteAvatar-only 数字人视频链路，不再嵌入完整 OpenAvatarChat。", "info");
  }
  return false;
}

function ensureLegacyOpenAvatarStage(options = {}) {
  const status = state.openAvatar || {};
  const url = getOpenAvatarEmbedUrl(status.openavatar_ui_url || "");
  if (state.openAvatarSuppressed) {
    document.body.classList.add("openavatar-suppressed");
    document.body.classList.remove("openavatar-active");
    return false;
  }
  if (!status.openavatar_ready || !url || !elements.openAvatarFrame) {
    if (!options.silent) {
      showToast("完整 OpenAvatarChat 服务尚未就绪。", "error");
    }
    return false;
  }
  if (elements.openAvatarFrame.src !== url) {
    state.openAvatarReady = false;
    elements.openAvatarFrame.src = url;
  }
  document.body.classList.remove("openavatar-suppressed");
  document.body.classList.add("openavatar-active");
  return true;
}

function handleOpenAvatarHealth(event) {
  const data = event.data;
  if (!data || typeof data !== "object" || data.type !== "A5_AVATAR_HEALTH") {
    return;
  }
  state.openAvatarHealth = data;
  if (data.ready) {
    state.openAvatarBlankReports = 0;
    state.openAvatarReadyReports += 1;
    if (state.openAvatarSuppressed && state.openAvatarReadyReports >= 2) {
      state.openAvatarSuppressed = false;
      document.body.classList.remove("openavatar-suppressed");
      if (state.openAvatar?.openavatar_ready) {
        ensureOpenAvatarStage({ silent: true });
      }
    }
    return;
  }

  state.openAvatarBlankReports += 1;
  state.openAvatarReadyReports = 0;
  if (state.openAvatarBlankReports >= 3) {
    state.openAvatarSuppressed = true;
    document.body.classList.add("openavatar-suppressed");
    document.body.classList.remove("openavatar-active");
    setPetMode(null);
    setPetSpeech("数字人导览中");
    setGuideState("欢迎使用景区导览数字人", "完整 OpenAvatarChat 暂未输出有效画面，已保持当前导览展示。");
    if (elements.openAvatarToggleButton) {
      elements.openAvatarToggleButton.textContent = "启用数字人";
    }
  }
}

function postOpenAvatarMessage(message) {
  if (!ensureLegacyOpenAvatarStage({ silent: true })) return false;
  const frameWindow = elements.openAvatarFrame?.contentWindow;
  if (!frameWindow) return false;
  frameWindow.postMessage(message, "*");
  return true;
}

function handleOpenAvatarFrameLoad() {
  state.openAvatarReady = true;
  const payload = state.currentLogId ? state.answerPayloads[state.currentLogId] : null;
  if (payload) {
    state.openAvatarLastSpokenLogId = null;
    syncOpenAvatarAnswer(payload);
  }
}

function syncOpenAvatarAnswer(data) {
  if (!data || !data.answer || data.log_id === state.openAvatarLastSpokenLogId) return false;
  if (!ensureOpenAvatarStage({ silent: true })) return false;
  state.openAvatarLastSpokenLogId = data.log_id;
  const answer = String(data.spoken_text || data.answer || "").replace(/\s+/g, " ").trim();
  if (!answer) return false;
  window.setTimeout(() => {
    postOpenAvatarMessage({
      type: "A5_SPEAK",
      text: answer,
      logId: data.log_id,
      source: "a5-rag",
    });
  }, 500);
  return true;
}

function openOpenAvatarLayer() {
  const status = state.openAvatar || {};
  const url = getOpenAvatarEmbedUrl(status.openavatar_ui_url || "");
  if (!status.openavatar_ready || !url) {
    showToast("完整 OpenAvatarChat 服务还未就绪。", "error");
    return;
  }
  stopVideoPlayback();
  stopAudioPlayback();
  stopLocalSpeech();
  state.openAvatarSuppressed = false;
  state.openAvatarBlankReports = 0;
  state.openAvatarReadyReports = 0;
  document.body.classList.remove("openavatar-suppressed");
  if (elements.openAvatarFrame && elements.openAvatarFrame.src !== url) {
    elements.openAvatarFrame.src = url;
  }
  document.body.classList.add("openavatar-active");
  if (elements.openAvatarToggleButton) {
    elements.openAvatarToggleButton.textContent = "关闭数字人";
  }
  setGuideState("真人数字人已就绪", "你可以直接提问，我会结合景区知识库进行讲解。");
  setPetSpeech("数字人讲解中");
}

function closeOpenAvatarLayer() {
  document.body.classList.remove("openavatar-active");
  state.openAvatarSuppressed = true;
  state.openAvatarReadyReports = 0;
  document.body.classList.add("openavatar-suppressed");
  if (elements.openAvatarToggleButton) {
    elements.openAvatarToggleButton.textContent = "启用数字人";
  }
  setPetMode(null);
  setGuideState("欢迎使用景区导览数字人", "可以为你讲解景点、规划路线，也支持语音提问和英文回答。");
}

function toggleOpenAvatarLayer() {
  if (document.body.classList.contains("openavatar-active")) {
    closeOpenAvatarLayer();
  } else {
    openOpenAvatarLayer();
  }
}

function renderEvaluationStatus(data) {
  if (!elements.evaluationPassed || !data) {
    return;
  }
  const accuracy = Math.round((data.accuracy_rate || 0) * 100);
  elements.evaluationPassed.textContent = data.total_cases
    ? (data.passed ? "验收通过" : "需要优化")
    : "尚未评测";
  elements.evaluationAccuracy.textContent = data.total_cases
    ? `${accuracy}% (${data.passed_cases}/${data.total_cases})`
    : "-";
  elements.evaluationLatency.textContent = data.total_cases
    ? `${Number(data.latency_p95_seconds || 0).toFixed(2)}s P95`
    : "-";
  if (!data.case_results?.length) {
    elements.evaluationCases.className = "evaluation-cases empty-state";
    elements.evaluationCases.textContent = "点击“运行验收评测”后生成标准题结果。";
    return;
  }
  elements.evaluationCases.className = "evaluation-cases";
  elements.evaluationCases.innerHTML = data.case_results
    .map(
      (item) => `
        <div class="evaluation-case ${item.passed ? "passed" : "failed"}">
          <strong>${escapeHtml(item.passed ? "通过" : "未通过")}</strong>
          <span>${escapeHtml(item.question)}</span>
          <em>${Number(item.latency_seconds || 0).toFixed(2)}s / ${escapeHtml(item.answer_source || "-")}</em>
        </div>
      `
    )
    .join("");
}

async function runEvaluation() {
  if (!elements.runEvaluationButton) {
    return;
  }
  const originalText = elements.runEvaluationButton.textContent;
  elements.runEvaluationButton.disabled = true;
  elements.runEvaluationButton.textContent = "评测中...";
  try {
    const data = await apiFetch("/api/admin/evaluation/run", { method: "POST" });
    renderEvaluationStatus(data);
    showToast(data.passed ? "验收评测通过。" : "验收评测完成，仍有项目需要优化。", data.passed ? "success" : "error");
    loadAdminData({ silent: true });
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    elements.runEvaluationButton.disabled = false;
    elements.runEvaluationButton.textContent = originalText;
  }
}

function setApiStatus(text, type) {
  if (!elements.apiStatus) {
    return;
  }
  elements.apiStatus.textContent = text;
  elements.apiStatus.className = `status-pill api-status-floating ${type}`;
  elements.apiStatus.title = text;
  elements.apiStatus.setAttribute("aria-label", text);
}

function configureRuntimeLinks() {
  if (elements.docsLink && API_BASE_URL) {
    elements.docsLink.href = buildApiUrl("/docs");
  }
}

function syncAdminOnlyChrome(viewId = "visitorView") {
  document.body.classList.toggle("is-admin-view", viewId === "adminView");
}

function addMessage(type, html, extraClass = "", logId = "") {
  const node = document.createElement("div");
  node.className = `message ${type} ${extraClass}`.trim();
  if (logId) {
    node.dataset.logId = String(logId);
  }
  node.innerHTML = html;
  elements.chatMessages.appendChild(node);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  return node;
}

function setChatComposerBusy(isBusy) {
  if (!elements.chatSubmitButton) {
    return;
  }
  elements.chatSubmitButton.disabled = isBusy;
  elements.chatSubmitButton.classList.toggle("is-loading", isBusy);
  elements.chatSubmitButton.textContent = isBusy ? "发送中" : "发送";
}

function renderRouteCard(data) {
  const basis = Array.isArray(data.personalization_basis) ? data.personalization_basis.filter(Boolean) : [];
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
      ${data.matched_interest ? `<span class="tag compact-tag">匹配偏好：${escapeHtml(data.matched_interest)}</span>` : ""}
      ${basis.length ? `<div class="route-basis">${basis.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>` : ""}
    </article>
  `;
}

function normalizeReferenceLabel(value) {
  const text = String(value || "").trim();
  if (!text || text.startsWith("知识库待补充")) {
    return "";
  }
  if (text.startsWith("路线规划：")) {
    return "路线参考";
  }
  if (text.length > 16) {
    return `${text.slice(0, 14)}...`;
  }
  return text;
}

function dedupeReferenceLabels(references = []) {
  const seen = new Set();
  const result = [];
  for (const item of references) {
    const label = normalizeReferenceLabel(item);
    if (!label || seen.has(label)) {
      continue;
    }
    seen.add(label);
    result.push({ label, fullText: String(item || "").trim() });
  }
  return result;
}

function renderReferenceTags(references = []) {
  const normalized = dedupeReferenceLabels(references);
  if (!normalized.length) {
    return "";
  }
  const visible = normalized.slice(0, 3);
  const hidden = normalized.slice(3);
  return `
    <div class="message-meta reference-meta" aria-label="鐭ヨ瘑鍙傝€冨叧閿瘝">
      ${visible.map((item) => `<span class="tag compact-tag" title="${escapeHtml(item.fullText)}">${escapeHtml(item.label)}</span>`).join("")}
      ${hidden.length ? `<span class="tag compact-tag tag-more" title="${escapeHtml(hidden.map((item) => item.fullText).join(" / "))}">+${hidden.length}</span>` : ""}
    </div>
  `;
}

function renderFeedbackActions(logId) {
  if (!logId) {
    return "";
  }
  const options = [
    { rating: 5, label: "有帮助" },
    { rating: 2, label: "不准确" },
    { rating: 1, label: "答非所问" },
  ];
  const buttons = options
    .map(
      (item) => `
        <button
          class="feedback-chip"
          type="button"
          data-rating="${item.rating}"
          data-log-id="${logId}"
          aria-label="${item.label}"
        >${item.label}</button>
      `
    )
    .join("");
  return `
    <div class="feedback-actions" aria-label="满意度反馈">
      <span>本次回答是否有帮助？</span>
      ${buttons}
    </div>
  `;
}

function renderTranslationBlock(data, targetLanguage = "en") {
  const translation = typeof data === "string" ? data : data?.translation || "";
  const audioUrl = typeof data === "string" ? "" : data?.audio_url || "";
  if (!translation) {
    return "";
  }
  const label = targetLanguage === "en" ? "English Answer" : targetLanguage;
  const audioButton = audioUrl
    ? `<button class="small-action translation-audio-action" type="button" data-audio-url="${escapeHtml(audioUrl)}">英文语音</button>`
    : "";
  return `
    <div class="translation-card" data-translation-language="${escapeHtml(targetLanguage)}">
      <div class="translation-head">
        <span class="tag">${escapeHtml(label)}</span>
      </div>
      <p>${escapeHtml(translation)}</p>
      ${audioButton ? `<div class="message-actions translation-actions">${audioButton}</div>` : ""}
    </div>
  `;
}

function renderAudioAction(data) {
  const status = data.audio_status || (data.audio_url ? "ready" : "pending");
  if (data.tts_mode_used === "browser_local" && status === "not_requested") {
    return `<button class="small-action" type="button" data-local-tts-log-id="${data.log_id}">语音播放</button>`;
  }
  if (status === "ready" && data.audio_url) {
    return `<button class="small-action" type="button" data-audio-url="${escapeHtml(data.audio_url)}">语音播放</button>`;
  }
  if (status === "failed") {
    return `<button class="small-action is-disabled" type="button" disabled title="语音生成失败">语音失败</button>`;
  }
  return `<button class="small-action is-disabled" type="button" disabled title="语音生成中">语音生成中</button>`;
}

function renderVideoAction(data) {
  const status = data.video_status || (data.video_url ? "ready" : "disabled");
  if (status === "ready" && data.video_url) {
    const playbackUrl = videoPlaybackUrl(data);
    return `<button class="small-action avatar-video-action" type="button" data-video-url="${escapeHtml(playbackUrl)}" data-video-source-url="${escapeHtml(data.video_url)}" data-fallback-audio-url="${escapeHtml(data.audio_url || "")}">数字人讲解</button>`;
  }
  if (status === "pending") {
    return `<button class="small-action is-disabled" type="button" disabled title="真人数字人视频正在生成">真人讲解生成中</button>`;
  }
  if (status === "waiting_audio") {
    return `<button class="small-action is-disabled" type="button" disabled title="等待服务端语音生成后驱动数字人">等待真人讲解</button>`;
  }
  if (["timeout", "error", "failed"].includes(status)) {
    return `<button class="small-action is-disabled" type="button" disabled title="${escapeHtml(data.video_message || "数字人视频暂不可用")}">数字人回退</button>`;
  }
  return "";
}

function videoPlaybackUrl(data) {
  if (data?.log_id && data?.video_url) {
    return `/api/chat/video/${encodeURIComponent(data.log_id)}`;
  }
  return data?.video_url || "";
}

function updateAnswerAudioUi(logId, data) {
  const messageNode = elements.chatMessages?.querySelector(`.message[data-log-id="${logId}"]`);
  if (!messageNode) {
    return;
  }
  const actionSlot = messageNode.querySelector(`[data-audio-action-slot="${logId}"]`);
  if (actionSlot) {
    actionSlot.innerHTML = renderAudioAction(data);
  }
  const videoSlot = messageNode.querySelector(`[data-video-action-slot="${logId}"]`);
  if (videoSlot) {
    videoSlot.innerHTML = renderVideoAction(data);
  }
  if (state.answerPayloads[logId]) {
    state.answerPayloads[logId] = { ...state.answerPayloads[logId], ...data };
  }
}

async function pollAnswerAudio(logId, options = {}) {
  if (!logId || state.pendingAudioPolls[logId]) {
    return;
  }
  state.pendingAudioPolls[logId] = true;
  const autoPlay = Boolean(options.autoPlay);
  let audioPlayed = false;
  let videoPlayed = false;
  let attempt = 0;
  const maxAttempts = 60;

  while (attempt < maxAttempts) {
    attempt += 1;
    try {
      const data = await apiFetch(`/api/chat/audio/${logId}`);
      updateAnswerAudioUi(logId, data);
      if (data.video_status === "ready" && data.video_url) {
        if (autoPlay && !videoPlayed) {
          videoPlayed = true;
          playDigitalVideo(videoPlaybackUrl(data), data.audio_url || "");
        }
        delete state.pendingAudioPolls[logId];
        return;
      }
      if (data.audio_status === "ready" && data.audio_url) {
        const shouldWaitForVideo = state.avatarOnlyEnabled && ["pending", "waiting_audio"].includes(data.video_status || "");
        if (autoPlay && !audioPlayed && !shouldWaitForVideo) {
          audioPlayed = true;
          playAudio(data.audio_url, data);
        }
        if (!["pending", "waiting_audio"].includes(data.video_status || "")) {
          delete state.pendingAudioPolls[logId];
          return;
        }
      }
      if (data.audio_status === "failed") {
        delete state.pendingAudioPolls[logId];
        return;
      }
    } catch {
      delete state.pendingAudioPolls[logId];
      return;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 700));
  }

  delete state.pendingAudioPolls[logId];
}

async function requestServerAudioFallback(logId, options = {}) {
  if (!logId || state.pendingServerAudioRequests[logId]) {
    return;
  }
  state.pendingServerAudioRequests[logId] = true;
  try {
    const data = await apiFetch(`/api/chat/audio/${logId}/request`, { method: "POST" });
    updateAnswerAudioUi(logId, data);
    if (data.video_status === "ready" && data.video_url) {
      if (options.autoPlay) {
        playDigitalVideo(videoPlaybackUrl(data), data.audio_url || "");
      }
      return;
    }
    if (data.audio_status === "ready" && data.audio_url) {
      const shouldWaitForVideo = state.avatarOnlyEnabled && ["pending", "waiting_audio"].includes(data.video_status || "");
      if (options.autoPlay && !shouldWaitForVideo) {
        playAudio(data.audio_url, data);
      }
      if (shouldWaitForVideo) {
        pollAnswerAudio(logId, { autoPlay: Boolean(options.autoPlay) });
      }
      return;
    }
    pollAnswerAudio(logId, { autoPlay: Boolean(options.autoPlay) });
  } catch (error) {
    showToast(`璇煶鍥為€€澶辫触锛?{error.message}`, "error");
  } finally {
    delete state.pendingServerAudioRequests[logId];
  }
}

async function playLocalAnswer(data, options = {}) {
  if (!data?.answer || !browserLocalTtsSupported()) {
    requestServerAudioFallback(data?.log_id, options);
    return false;
  }
  stopVideoPlayback();
  stopAudioPlayback();
  stopLocalSpeech();

  const voice = await waitForChineseVoice();
  if (!voice) {
    requestServerAudioFallback(data.log_id, options);
    return false;
  }

  const utterance = new SpeechSynthesisUtterance(data.answer);
  utterance.lang = voice.lang || "zh-CN";
  utterance.voice = voice;
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.onstart = startLocalSpeechLipSync;
  utterance.onboundary = pulseLocalSpeechMouth;
  utterance.onend = () => {
    state.localSpeechUtterance = null;
    unmarkSpeaking();
  };
  utterance.onerror = () => {
    state.localSpeechUtterance = null;
    unmarkSpeaking();
    showToast("本地朗读不可用，正在切换服务端语音。", "info");
    requestServerAudioFallback(data.log_id, options);
  };

  state.localSpeechUtterance = utterance;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);

  window.setTimeout(() => {
    if (state.localSpeechUtterance === utterance && !window.speechSynthesis.speaking) {
      showToast("本地朗读启动较慢，正在切换服务端语音。", "info");
      requestServerAudioFallback(data.log_id, options);
    }
  }, 800);
  return true;
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function waitForVideoCanPlay(url, timeoutMs = AVATAR_REVEAL_PRELOAD_MS) {
  if (!url) {
    return false;
  }
  return withTimeout(
    new Promise((resolve) => {
      const video = document.createElement("video");
      let done = false;
      const finish = (ready) => {
        if (done) {
          return;
        }
        done = true;
        video.oncanplay = null;
        video.onloadeddata = null;
        video.onerror = null;
        video.removeAttribute("src");
        video.load();
        resolve(Boolean(ready));
      };
      video.preload = "auto";
      video.muted = true;
      video.playsInline = true;
      video.oncanplay = () => finish(true);
      video.onloadeddata = () => finish(true);
      video.onerror = () => finish(false);
      video.src = resolveMediaUrl(url);
      video.load();
    }),
    timeoutMs,
    false
  );
}

async function waitForAvatarVideoReady(data, loadingNode) {
  if (!state.avatarOnlyEnabled || !data?.log_id) {
    return data;
  }

  const startedAt = performance.now();
  const minWaitUntil = startedAt + AVATAR_REVEAL_MIN_MS;
  let latest = data;
  setGuideState("正在思考", "正在为你组织导览讲解。");
  setPetSpeech("正在思考");
  setPetMode("thinking");
  if (loadingNode) {
    loadingNode.innerHTML = "正在思考...";
  }

  while (performance.now() - startedAt < AVATAR_REVEAL_MAX_MS) {
    try {
      latest = await apiFetch(`/api/chat/audio/${data.log_id}`);
      updateAnswerAudioUi(data.log_id, latest);
      if (latest.video_status === "ready" && latest.video_url) {
        const playbackUrl = videoPlaybackUrl(latest);
        await waitForVideoCanPlay(playbackUrl);
        const remaining = minWaitUntil - performance.now();
        if (remaining > 0) {
          await sleep(remaining);
        }
        return { ...data, ...latest };
      }
      if (["timeout", "error", "failed"].includes(latest.video_status || "")) {
        break;
      }
      if (latest.audio_status === "failed" && !["pending", "waiting_audio"].includes(latest.video_status || "")) {
        break;
      }
    } catch {
      break;
    }
    await sleep(AVATAR_REVEAL_POLL_MS);
  }

  const remaining = minWaitUntil - performance.now();
  if (remaining > 0) {
    await sleep(remaining);
  }
  return { ...data, ...latest };
}

async function revealAnswerWhenAvatarReady(data, loadingNode, options = {}) {
  const finalData = await waitForAvatarVideoReady(data, loadingNode);
  loadingNode?.remove();
  renderAnswer(finalData, options);
  if (
    state.avatarOnlyEnabled &&
    finalData?.log_id &&
    !finalData.video_url &&
    ["pending", "waiting_audio"].includes(finalData.video_status || "")
  ) {
    pollAnswerAudio(finalData.log_id, { autoPlay: true });
  }
  return finalData;
}

function renderAnswer(data, options = {}) {
  state.currentLogId = data.log_id;
  state.answerPayloads[data.log_id] = data;
  const transcriptBlock = options.showTranscript
    ? `
      <div class="visitor-question-note">
        <span>你刚才问：${escapeHtml(data.interpreted_question || data.transcript || "-")}</span>
      </div>
    `
    : "";
  const audioButton = renderAudioAction(data);
  const translateDisabled = !data.english_available;
  const translateButton = `
      <button
        class="small-action translate-action${translateDisabled ? " is-disabled" : ""}"
        type="button"
        data-translate-log-id="${data.log_id}"
        data-translate-language="en"
        data-translate-source="${escapeHtml(data.answer)}"
        ${translateDisabled ? 'disabled title="英文回答服务未配置"' : ""}
      >英文翻译</button>
    `;
  const videoButton = renderVideoAction(data);
  const videoReady = data.video_url && data.video_status === "ready";
  const visionBlock = data.multimodal_source
    ? `
      <div class="vision-evidence">
        <span>多模态识别</span>
        <strong>${escapeHtml(data.vision_model_name || "视觉模型")}</strong>
        <em>${escapeHtml(data.matched_spot || "未匹配明确景点")}</em>
      </div>
      <div class="vision-summary">${escapeHtml(data.vision_summary || "")}</div>
    `
    : "";

  addMessage(
    "assistant",
    `
      <strong>数字人回答</strong>
      ${visionBlock}
      <div class="answer-text">${escapeHtml(data.answer)}</div>
      ${transcriptBlock}
      <div class="message-actions">
        <span data-video-action-slot="${data.log_id}">${videoButton}</span>
        <span data-audio-action-slot="${data.log_id}">${audioButton}</span>
        ${translateButton}
      </div>
      <div class="translation-slot" data-translation-slot="${data.log_id}"></div>
      ${renderFeedbackActions(data.log_id)}
    `,
    "",
    data.log_id
  );

  setGuideState("已完成回答", data.interpreted_question || data.transcript || "欢迎继续提问");
  setPetMode("success");
  const shouldWaitForAvatarVideo = state.avatarOnlyEnabled && ["pending", "waiting_audio"].includes(data.video_status || "");
  if (videoReady) {
    playDigitalVideo(videoPlaybackUrl(data), data.audio_url);
  } else if (shouldWaitForAvatarVideo) {
    pollAnswerAudio(data.log_id, { autoPlay: true });
  } else if (data.tts_mode_used === "browser_local") {
    playLocalAnswer(data, { autoPlay: true });
  } else if (data.audio_url) {
    playAudio(data.audio_url, data);
  } else if (data.audio_status === "pending") {
    pollAnswerAudio(data.log_id, { autoPlay: true });
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
  setChatComposerBusy(true);
  setGuideState("正在思考", "正在从景区知识库中查找最相关的信息。");
  setPetSpeech("检索知识库");
  setPetMode("thinking");

  try {
    const data = await apiFetch("/api/chat/text", {
      method: "POST",
      body: JSON.stringify({ question: trimmed, user_id: "web-visitor", tts_mode: preferredTtsMode() }),
    });
    await revealAnswerWhenAvatarReady(data, loading);
    loadAdminData({ silent: true });
  } catch (error) {
    loading.remove();
    setGuideState("问答失败", "请检查后端服务是否正常运行。");
    setPetSpeech("需要重试");
    setPetMode(null);
    showToast(error.message, "error");
  } finally {
    setChatComposerBusy(false);
  }
}

async function askRouteLecture(question) {
  const trimmed = question.trim() || "半天 初次游客";
  addMessage("user", escapeHtml(trimmed));
  const loading = addMessage("assistant", "正在生成适合初次游客的路线讲解...", "loading");
  elements.questionInput.value = "";
  setChatComposerBusy(true);
  setGuideState("正在规划路线", "系统正在匹配当前景区的预设路线。");
  setPetSpeech("路线规划中");
  setPetMode("thinking");

  try {
    const data = await apiFetch("/api/recommend/route", {
      method: "POST",
      body: JSON.stringify({
        interest: trimmed,
        duration: trimmed,
        user_id: "web-visitor",
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
  } finally {
    setChatComposerBusy(false);
  }
}

async function sendVoice(blob, filename = "visitor-question.webm") {
  const formData = new FormData();
  formData.append("user_id", "web-visitor");
  formData.append("tts_mode", preferredTtsMode());
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
    await revealAnswerWhenAvatarReady(data, loading, { showTranscript: true });
    loadAdminData({ silent: true });
  } catch (error) {
    loading.remove();
    setGuideState("语音识别失败", "可以换一段更短、更清晰的录音重试。");
    setPetSpeech("没听清楚");
    setPetMode(null);
    showToast(error.message, "error");
  }
}

async function sendImage(file) {
  if (!file) {
    return;
  }
  if (!/^image\//i.test(file.type || "")) {
    showToast("请上传图片文件。", "error");
    return;
  }
  const question = elements.questionInput.value.trim();
  const formData = new FormData();
  formData.append("user_id", "web-visitor");
  formData.append("tts_mode", preferredTtsMode());
  formData.append("question", question);
  formData.append("file", file, file.name || "visitor-image.png");

  const previewUrl = URL.createObjectURL(file);
  addMessage(
    "user",
    `
      <div class="image-question-preview">
        <img src="${escapeHtml(previewUrl)}" alt="上传的景区图片预览" />
        <span>${escapeHtml(question || "请识别这张图片并讲解。")}</span>
      </div>
    `
  );
  const loading = addMessage("assistant", "正在调用多模态大模型识别图片，并匹配景区知识库...", "loading");
  elements.questionInput.value = "";
  setChatComposerBusy(true);
  setGuideState("正在识别图片", "多模态视觉模型正在观察图片，并准备接入 RAG 导览。");
  setPetSpeech("图片识别中");
  setPetMode("thinking");

  try {
    const data = await apiFetch("/api/chat/image", {
      method: "POST",
      body: formData,
    });
    await revealAnswerWhenAvatarReady(data, loading, { showTranscript: true });
    loadAdminData({ silent: true });
  } catch (error) {
    loading.remove();
    setGuideState("图片识别失败", "可以换一张更清晰的景点照片，或检查多模态模型配置。");
    setPetSpeech("图片没看清");
    setPetMode(null);
    showToast(error.message, "error");
  } finally {
    setChatComposerBusy(false);
    window.setTimeout(() => URL.revokeObjectURL(previewUrl), 4000);
  }
}

async function toggleRecording() {
  if (state.recorder?.state === "recording") {
    state.recorder.stop();
    elements.recordButton.textContent = "语音";
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
    elements.recordButton.textContent = "停止";
    elements.voiceHint.textContent = "正在录音";
  } catch (error) {
    showToast(`无法打开麦克风：${error.message}`, "error");
  }
}

async function playAudio(url, payload = {}) {
  if (!url) {
    showToast("这条回答没有可播放音频。", "error");
    return;
  }
  stopVideoPlayback();
  stopLocalSpeech();
  stopAudioPlayback();

  const audio = new Audio(resolveMediaUrl(url));
  audio.crossOrigin = "anonymous";
  state.audio = audio;
  let cues = null;
  if (payload?.lipsync_url) {
    cues = await withTimeout(loadMouthCues(payload.lipsync_url), 700, null);
  }
  audio.addEventListener("play", () => {
    if (!startCueLipSync(audio, cues)) {
      startAudioLipSync(audio);
    }
  });
  audio.addEventListener("ended", unmarkSpeaking);
  audio.addEventListener("pause", unmarkSpeaking);
  audio.play().catch((error) => {
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

  stopLocalSpeech();
  stopAudioPlayback();
  stopVideoPlayback();
  pauseAvatarStandbyLoop();

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
    unmarkSpeaking();
    stopVideoPlayback();
    setGuideState("视频暂不可用", state.digitalHuman?.fallback_message || "数字人视频暂不可用，可点击语音播放继续听讲解。");
    showToast(state.digitalHuman?.fallback_message || "数字人视频播放失败，可点击语音播放。", "error");
  };
  elements.avatarFrame.classList.add("video-active");
  setGuideState("正在播报", "数字人正在播放视频讲解。");
  setPetSpeech("视频讲解中");

  player.play().catch((error) => {
    unmarkSpeaking();
    elements.avatarFrame.classList.add("video-active");
    setGuideState("数字人讲解已就绪", "如果浏览器阻止自动播放，请在舞台视频控件中手动点击播放。");
    showToast(`已生成数字人讲解，请点击视频控件播放。${error.message ? `（${error.message}）` : ""}`, "info");
  });
}

function stopAudioPlayback() {
  if (!state.audio) {
    resetLipSync();
    return;
  }
  state.audio.pause();
  state.audio = null;
  resetLipSync();
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
  startAvatarStandbyLoop();
}

function markSpeaking() {
  setPetMode("speaking");
  setGuideState("正在播报", "数字人正在播放讲解内容。");
  setPetSpeech("正在播报");
}

function unmarkSpeaking() {
  resetLipSync();
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
        user_id: "web-visitor",
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
    button.closest(".feedback-actions").querySelectorAll("button").forEach((item) => {
      const isSelected = Number(item.dataset.rating) === Number(satisfaction);
      item.classList.toggle("selected", isSelected);
      item.classList.toggle("muted", !isSelected);
      item.disabled = true;
    });
    showToast("感谢反馈，已记录。");
    loadAdminData({ silent: true });
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function toggleTranslation(button) {
  const logId = Number(button.dataset.translateLogId || 0);
  const targetLanguage = button.dataset.translateLanguage || "en";
  const sourceText = button.dataset.translateSource || "";
  const messageNode = button.closest(".message");
  const slot = messageNode?.querySelector(`[data-translation-slot="${logId}"]`);
  if (!logId || !slot) {
    return;
  }

  const cacheKey = `${logId}:${targetLanguage}`;
  const expanded = button.dataset.expanded === "true";
  if (expanded) {
    slot.innerHTML = "";
    button.dataset.expanded = "false";
    button.textContent = targetLanguage === "en" ? "英文翻译" : targetLanguage;
    return;
  }

  if (state.answerTranslations[cacheKey]) {
    slot.innerHTML = renderTranslationBlock(state.answerTranslations[cacheKey], targetLanguage);
    button.dataset.expanded = "true";
    button.textContent = targetLanguage === "en" ? "鏀惰捣鑻辨枃" : "鏀惰捣";
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    return;
  }

  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "缈昏瘧涓?..";
  try {
    const data = await apiFetch("/api/chat/translate", {
      method: "POST",
      body: JSON.stringify({
        log_id: logId,
        text: sourceText,
        target_language: targetLanguage,
      }),
    });
    state.answerTranslations[cacheKey] = {
      translation: data.translation,
      audio_url: data.audio_url || "",
    };
    slot.innerHTML = renderTranslationBlock(state.answerTranslations[cacheKey], targetLanguage);
    button.dataset.expanded = "true";
    button.textContent = targetLanguage === "en" ? "鏀惰捣鑻辨枃" : "鏀惰捣";
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  } catch (error) {
    button.textContent = originalLabel;
    showToast(error.message, "error");
  } finally {
    button.disabled = false;
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
    showToast(`娆㈣繋锛?{data.display_name}`);
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
    const [dashboard, report, logs, docs, videoStatus, ragStatus, aiStatus, evaluationStatus] = await Promise.all([
      apiFetch("/api/admin/dashboard"),
      apiFetch("/api/admin/visitor-report"),
      apiFetch("/api/admin/logs?limit=50"),
      apiFetch("/api/admin/docs"),
      apiFetch("/api/admin/digital-video/status"),
      apiFetch("/api/admin/rag/status"),
      apiFetch("/api/admin/ai/status"),
      apiFetch("/api/admin/evaluation/latest"),
    ]);
    renderDashboard(dashboard);
    renderVisitorReport(report);
    renderLogs(logs);
    renderKnowledgeDocs(docs);
    renderDigitalVideoStatus(videoStatus);
    renderRagStatus(ragStatus);
    renderAiStatus(aiStatus);
    renderEvaluationStatus(evaluationStatus);
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
          <div class="trend-track" title="绉瀬 ${item.positive} / 涓€?${item.neutral} / 娑堟瀬 ${item.negative}">
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
    elements.serviceSuggestionsList.innerHTML = "<li>鏆傛棤寤鸿銆?/li>";
    return;
  }

  elements.serviceSuggestionsList.innerHTML = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderLogs(logs = []) {
  if (!logs.length) {
    elements.logsTableBody.innerHTML = `<tr><td colspan="8">鏆傛棤闂瓟鏃ュ織銆?/td></tr>`;
    return;
  }

  elements.logsTableBody.innerHTML = logs
    .map(
      (item) => `
        <tr title="${escapeHtml(item.answer)}">
          <td data-label="ID">${item.id}</td>
          <td data-label="鐢ㄦ埛">${escapeHtml(item.user_id)}</td>
          <td data-label="闂">${escapeHtml(item.question)}</td>
          <td data-label="鎯呯华">${escapeHtml(item.emotion)}</td>
          <td data-label="璇勫垎">${item.satisfaction ?? "-"}</td>
          <td data-label="鑰楁椂">${Number(item.response_seconds || 0).toFixed(2)}s</td>
          <td data-label="璇煶">${escapeHtml(item.audio_status || "pending")}</td>
          <td data-label="鏃堕棿">${formatTime(item.created_at)}</td>
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

async function rebuildRagIndex() {
  if (!window.confirm("确认重建全部知识片段的向量索引？未配置 Embedding Key 时会自动降级，不影响问答演示。")) {
    return;
  }

  const originalText = elements.rebuildRagButton.textContent;
  elements.rebuildRagButton.disabled = true;
  elements.rebuildRagButton.textContent = "重建中...";
  try {
    const result = await apiFetch("/api/admin/rag/rebuild", {
      method: "POST",
      body: JSON.stringify({}),
    });
    await loadRagStatus({ silent: true });
    showToast(result.message || "向量索引重建完成。");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    elements.rebuildRagButton.disabled = false;
    elements.rebuildRagButton.textContent = originalText;
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
      syncAdminOnlyChrome(button.dataset.view);
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

  elements.guideModeSelect.addEventListener("change", () => {
    applyGuideMode(elements.guideModeSelect.value, { autofill: true });
    elements.questionInput.focus();
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

  elements.imageFileInput?.addEventListener("change", () => {
    const file = elements.imageFileInput.files?.[0];
    if (file) {
      sendImage(file);
      elements.imageFileInput.value = "";
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
      const messageNode = audioButton.closest(".message[data-log-id]");
      const payload = messageNode ? state.answerPayloads[messageNode.dataset.logId] : {};
      playAudio(audioButton.dataset.audioUrl, payload || {});
      return;
    }

    const localTtsButton = event.target.closest("[data-local-tts-log-id]");
    if (localTtsButton) {
      const payload = state.answerPayloads[localTtsButton.dataset.localTtsLogId];
      playLocalAnswer(payload, { autoPlay: true });
      return;
    }

    const ratingButton = event.target.closest("[data-rating]");
    if (ratingButton) {
      submitFeedback(ratingButton.dataset.logId, ratingButton.dataset.rating, ratingButton);
      return;
    }

    const translateButton = event.target.closest("[data-translate-log-id]");
    if (translateButton) {
      toggleTranslation(translateButton);
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
  elements.rebuildRagButton.addEventListener("click", rebuildRagIndex);
  elements.runEvaluationButton?.addEventListener("click", runEvaluation);
  elements.openAvatarToggleButton?.addEventListener("click", toggleOpenAvatarLayer);
  elements.closeOpenAvatarButton?.addEventListener("click", closeOpenAvatarLayer);
  elements.openAvatarFrame?.addEventListener("load", handleOpenAvatarFrameLoad);
  window.addEventListener("message", handleOpenAvatarHealth);

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
  syncAdminOnlyChrome();
  bindEvents();
  bindLicensedAvatarAsset();
  bindAvatarStandbyVideo();
  applyGuideMode(state.guideMode);
  checkApiHealth();
  await loadDigitalVideoStatus();
  await loadDigitalHumanConfig();
  await loadAiCapabilityStatus();
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
