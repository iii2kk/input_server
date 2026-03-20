const STORAGE_KEY = "inputServerWsUrl";
const MODE_STORAGE_KEY = "inputServerMode";
const THEME_STORAGE_KEY = "inputServerTheme";
const DEFAULT_THEME = "canyon-dusk";
const AVAILABLE_THEMES = new Set([
  "canyon-dusk",
  "http-legacy",
  "matcha-paper",
  "solar-flare",
  "moon-slate"
]);

const platformLabel = document.getElementById("platformLabel");
const themeStylesheet = document.getElementById("themeStylesheet");
const serverUrlInput = document.getElementById("serverUrl");
const themeSelect = document.getElementById("themeSelect");
const settingsForm = document.getElementById("settingsForm");
const settingsPanel = document.getElementById("settingsPanel");
const toggleSettingsButton = document.getElementById("toggleSettingsButton");
const wsStatus = document.getElementById("wsStatus");
const liveModeButton = document.getElementById("liveModeButton");
const bulkModeButton = document.getElementById("bulkModeButton");
const clipboardModeButton = document.getElementById("clipboardModeButton");
const liveMode = document.getElementById("liveMode");
const bulkMode = document.getElementById("bulkMode");
const clipboardMode = document.getElementById("clipboardMode");
const keyPanel = document.getElementById("keyPanel");
const liveBox = document.getElementById("liveBox");
const bulkBox = document.getElementById("bulkBox");
const bulkSendButton = document.getElementById("bulkSendButton");
const bulkBackspaceButton = document.getElementById("bulkBackspaceButton");
const clipboardBox = document.getElementById("clipboardBox");
const refreshClipboardButton = document.getElementById("refreshClipboardButton");
const copyClipboardButton = document.getElementById("copyClipboardButton");
const notice = document.getElementById("notice");

let socket = null;
let isComposingText = false;
let reconnectTimer = null;
let shouldReconnect = true;
const isExtensionEnvironment = typeof chrome !== "undefined" && !!chrome.storage && !!chrome.storage.local;

const controlKeyMap = {
  Enter: "Return",
  Backspace: "BackSpace",
  Delete: "Delete",
  Tab: "Tab",
  Escape: "Escape",
  ArrowLeft: "Left",
  ArrowRight: "Right",
  ArrowUp: "Up",
  ArrowDown: "Down",
  Home: "Home",
  End: "End",
  PageUp: "Page_Up",
  PageDown: "Page_Down"
};

if (platformLabel) {
  platformLabel.textContent = isExtensionEnvironment ? "Chrome Extension" : "Browser";
}

function getDefaultServerUrl() {
  if (location.protocol === "http:" || location.protocol === "https:") {
    return location.origin;
  }
  return "ws://127.0.0.1:5000/ws";
}

async function getStoredValue(key) {
  if (isExtensionEnvironment) {
    const stored = await chrome.storage.local.get(key);
    return stored[key];
  }
  return localStorage.getItem(key);
}

async function setStoredValue(key, value) {
  if (isExtensionEnvironment) {
    await chrome.storage.local.set({ [key]: value });
    return;
  }
  localStorage.setItem(key, value);
}

function setStatus(text, statusClass) {
  wsStatus.textContent = text;
  wsStatus.className = "status-badge";
  if (statusClass) {
    wsStatus.classList.add(statusClass);
  }
}

function setNotice(text) {
  notice.textContent = text;
}

function setSettingsOpen(isOpen) {
  settingsPanel.classList.toggle("hidden", !isOpen);
  toggleSettingsButton.setAttribute("aria-expanded", String(isOpen));
}

function normalizeServerUrl(rawValue) {
  const value = rawValue.trim();
  if (!value) {
    throw new Error("接続先URLを入力してください。");
  }

  if (value.startsWith("ws://") || value.startsWith("wss://")) {
    return value;
  }

  if (value.startsWith("http://") || value.startsWith("https://")) {
    const parsed = new URL(value);
    const protocol = parsed.protocol === "https:" ? "wss:" : "ws:";
    const path = parsed.pathname === "/" ? "/ws" : parsed.pathname;
    return protocol + "//" + parsed.host + path;
  }

  return "ws://" + value.replace(/^\/+/, "") + "/ws";
}

function getClipboardUrl() {
  const wsUrl = normalizeServerUrl(serverUrlInput.value);
  const parsed = new URL(wsUrl);
  parsed.protocol = parsed.protocol === "wss:" ? "https:" : "http:";
  parsed.pathname = "/clipboard";
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString();
}

async function saveServerUrl() {
  const normalized = normalizeServerUrl(serverUrlInput.value);
  await setStoredValue(STORAGE_KEY, normalized);
  serverUrlInput.value = normalized;
  setNotice("接続先を保存しました。");
  return normalized;
}

async function loadServerUrl() {
  const url = await getStoredValue(STORAGE_KEY) || getDefaultServerUrl();
  serverUrlInput.value = url;
  return url;
}

function closeSocket() {
  if (!socket) {
    return;
  }

  socket.onopen = null;
  socket.onerror = null;
  socket.onclose = null;
  socket.close();
  socket = null;
}

function scheduleReconnect() {
  if (!shouldReconnect || reconnectTimer) {
    return;
  }

  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, 3000);
}

async function connectWebSocket() {
  setNotice("");

  let wsUrl;
  try {
    wsUrl = await saveServerUrl();
  } catch (error) {
    setStatus("未接続", "");
    setNotice(error.message);
    return;
  }

  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  closeSocket();
  setStatus("接続中", "connecting");

  try {
    socket = new WebSocket(wsUrl);
  } catch (error) {
    setStatus("接続失敗", "error");
    setNotice("WebSocket URL を確認してください。");
    scheduleReconnect();
    return;
  }

  socket.addEventListener("open", () => {
    setStatus("接続済み", "connected");
    setNotice("接続できました。");
  });

  socket.addEventListener("error", () => {
    setStatus("接続失敗", "error");
    setNotice("サーバーに接続できませんでした。");
    scheduleReconnect();
  });

  socket.addEventListener("close", () => {
    setStatus("未接続", "");
    setNotice("接続が閉じられました。");
    socket = null;
    scheduleReconnect();
  });
}

function sendMessage(message) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    setNotice("先に接続してください。");
    return false;
  }

  socket.send(JSON.stringify(message));
  return true;
}

function sendLive(text) {
  return sendMessage({ type: "text", text });
}

function sendControlKey(key) {
  return sendMessage({ type: "key", key });
}

function sendBulk() {
  const text = bulkBox.value;
  if (!text) {
    return;
  }

  if (sendMessage({ type: "bulk", text })) {
    bulkBox.value = "";
    setNotice("まとめ送信しました。");
  }
}

function sendBulkBackspace() {
  if (sendControlKey("BackSpace")) {
    setNotice("Backspace を送信しました。");
  }
}

async function refreshClipboard() {
  setNotice("");
  refreshClipboardButton.disabled = true;

  let clipboardUrl;
  try {
    clipboardUrl = getClipboardUrl();
  } catch (error) {
    setNotice("接続先URLを確認してください。");
    refreshClipboardButton.disabled = false;
    return;
  }

  try {
    const response = await fetch(clipboardUrl, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "クリップボードを取得できませんでした。");
    }

    clipboardBox.value = data.text || "";
    setNotice("サーバー側のクリップボードを取得しました。");
  } catch (error) {
    setNotice(error.message || "クリップボードを取得できませんでした。");
  } finally {
    refreshClipboardButton.disabled = false;
  }
}

async function copyClipboardText() {
  if (!clipboardBox.value) {
    setNotice("コピーするテキストがありません。");
    return;
  }

  try {
    await navigator.clipboard.writeText(clipboardBox.value);
    setNotice("クリップボード表示をコピーしました。");
  } catch (error) {
    clipboardBox.focus();
    clipboardBox.select();
    setNotice("表示テキストを選択しました。");
  }
}

function switchMode(mode) {
  const isLive = mode === "live";
  const isBulk = mode === "bulk";
  const isClipboard = mode === "clipboard";
  liveMode.classList.toggle("hidden", !isLive);
  bulkMode.classList.toggle("hidden", !isBulk);
  clipboardMode.classList.toggle("hidden", !isClipboard);
  keyPanel.classList.toggle("hidden", isClipboard);
  liveModeButton.classList.toggle("active", isLive);
  bulkModeButton.classList.toggle("active", isBulk);
  clipboardModeButton.classList.toggle("active", isClipboard);
  if (isLive) {
    liveBox.focus();
  } else if (isBulk) {
    bulkBox.focus();
  } else {
    refreshClipboard();
    clipboardBox.focus();
  }
}

async function saveMode(mode) {
  await setStoredValue(MODE_STORAGE_KEY, mode);
}

async function loadMode() {
  const mode = await getStoredValue(MODE_STORAGE_KEY);
  return mode === "bulk" ? "bulk" : "live";
}

function getThemeHref(themeName) {
  return "themes/" + themeName + ".css";
}

function applyTheme(themeName) {
  const safeTheme = AVAILABLE_THEMES.has(themeName) ? themeName : DEFAULT_THEME;
  themeStylesheet.href = getThemeHref(safeTheme);
  themeSelect.value = safeTheme;
  return safeTheme;
}

async function saveTheme(themeName) {
  const safeTheme = applyTheme(themeName);
  await setStoredValue(THEME_STORAGE_KEY, safeTheme);
}

async function loadTheme() {
  const storedTheme = await getStoredValue(THEME_STORAGE_KEY);
  return applyTheme(storedTheme || DEFAULT_THEME);
}

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await saveServerUrl();
    await saveTheme(themeSelect.value);
    connectWebSocket();
    setSettingsOpen(false);
  } catch (error) {
    setNotice(error.message);
  }
});

themeSelect.addEventListener("change", async () => {
  await saveTheme(themeSelect.value);
});

toggleSettingsButton.addEventListener("click", () => {
  if (!wsStatus.classList.contains("connected")) {
    setSettingsOpen(true);
    return;
  }

  const isOpen = toggleSettingsButton.getAttribute("aria-expanded") === "true";
  setSettingsOpen(!isOpen);
});

liveModeButton.addEventListener("click", () => {
  switchMode("live");
  saveMode("live");
});

bulkModeButton.addEventListener("click", () => {
  switchMode("bulk");
  saveMode("bulk");
});

clipboardModeButton.addEventListener("click", () => {
  switchMode("clipboard");
});

bulkSendButton.addEventListener("click", () => {
  sendBulk();
});

bulkBackspaceButton.addEventListener("click", () => {
  sendBulkBackspace();
});

refreshClipboardButton.addEventListener("click", () => {
  refreshClipboard();
});

copyClipboardButton.addEventListener("click", () => {
  copyClipboardText();
});

liveBox.addEventListener("keydown", (event) => {
  if (event.isComposing) {
    return;
  }

  const mappedKey = controlKeyMap[event.key];
  if (!mappedKey) {
    return;
  }

  if (sendControlKey(mappedKey)) {
    event.preventDefault();
  }
});

liveBox.addEventListener("input", () => {
  if (isComposingText) {
    return;
  }

  const text = liveBox.value;
  if (!text) {
    return;
  }

  if (sendLive(text)) {
    liveBox.value = "";
  }
});

liveBox.addEventListener("compositionstart", () => {
  isComposingText = true;
});

liveBox.addEventListener("compositionend", (event) => {
  isComposingText = false;
  const text = event.data || liveBox.value;
  if (!text) {
    return;
  }

  if (sendLive(text)) {
    liveBox.value = "";
  }
});

bulkBox.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.ctrlKey) {
    event.preventDefault();
    sendBulk();
    return;
  }

  if (event.key === "Backspace" && event.ctrlKey && event.shiftKey) {
    event.preventDefault();
    sendBulkBackspace();
  }
});

document.querySelectorAll("[data-quick-key]").forEach((button) => {
  button.addEventListener("click", () => {
    const value = button.getAttribute("data-quick-key");
    if (value) {
      sendLive(value);
    }
  });
});

window.addEventListener("unload", () => {
  shouldReconnect = false;
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  closeSocket();
});

async function init() {
  await loadTheme();
  await loadServerUrl();
  switchMode(await loadMode());
  connectWebSocket();
}

init();
