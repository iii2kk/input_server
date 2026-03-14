from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import hashlib
import json
import struct
import urllib.parse
import subprocess

SYMBOL_KEYMAP = {
    "_": "underscore",
    "+": "plus",
    "|": "bar",
    "~": "asciitilde",
    ":": "colon",
    "\"": "quotedbl",
    "<": "less",
    ">": "greater",
    "?": "question",
    "!": "exclam",
    "@": "at",
    "#": "numbersign",
    "$": "dollar",
    "%": "percent",
    "^": "asciicircum",
    "&": "ampersand",
    "*": "asterisk",
    "(": "parenleft",
    ")": "parenright"
}

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Ubuntu Input</title>

<style>
:root {
  --bg: #07111f;
  --bg2: #0d1b2f;
  --panel: rgba(10, 18, 32, 0.86);
  --panel-border: rgba(133, 174, 255, 0.18);
  --text: #eef4ff;
  --muted: #9fb2cc;
  --accent: #66d9ff;
  --accent-strong: #7af0c9;
  --danger: #ff7a9c;
  --shadow: 0 24px 80px rgba(0, 0, 0, 0.42);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  color: var(--text);
  font-family: "Segoe UI", "Hiragino Sans", "Noto Sans JP", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(102, 217, 255, 0.22), transparent 28%),
    radial-gradient(circle at bottom right, rgba(122, 240, 201, 0.16), transparent 26%),
    linear-gradient(135deg, var(--bg), var(--bg2));
}

.shell {
  max-width: 920px;
  margin: 0 auto;
  padding: 48px 20px 72px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--panel-border);
  border-radius: 28px;
  padding: 28px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(14px);
}

.eyebrow {
  margin: 0 0 10px;
  color: var(--accent);
  letter-spacing: 0.22em;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

h2 {
  margin: 0;
  font-size: clamp(34px, 6vw, 56px);
  line-height: 1;
  letter-spacing: -0.04em;
}

.lead {
  margin: 14px 0 26px;
  max-width: 620px;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.7;
}

.mode-buttons, .status, .quick-keys {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.mode-buttons { margin-bottom: 16px; }
.status { margin-bottom: 22px; }
.hidden { display:none; }

.mode-panel,
.key-panel {
  margin-top: 18px;
  padding: 20px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.section-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--muted);
  text-transform: uppercase;
}

input, textarea {
  width: 100%;
  border: 1px solid rgba(137, 190, 255, 0.18);
  border-radius: 18px;
  background: rgba(4, 10, 20, 0.7);
  color: var(--text);
  padding: 18px 20px;
  font-size: 20px;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

input:focus, textarea:focus {
  border-color: rgba(102, 217, 255, 0.75);
  box-shadow: 0 0 0 4px rgba(102, 217, 255, 0.12);
  transform: translateY(-1px);
}

textarea {
  min-height: 200px;
  resize: vertical;
}

button {
  border: 0;
  border-radius: 999px;
  padding: 12px 18px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  background: linear-gradient(135deg, rgba(102, 217, 255, 0.24), rgba(122, 240, 201, 0.2));
  box-shadow: inset 0 0 0 1px rgba(173, 226, 255, 0.16);
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
}

button:hover {
  transform: translateY(-1px);
  box-shadow: inset 0 0 0 1px rgba(173, 226, 255, 0.24), 0 10px 24px rgba(0, 0, 0, 0.22);
}

button:disabled {
  opacity: 0.45;
  cursor: default;
  transform: none;
  box-shadow: inset 0 0 0 1px rgba(173, 226, 255, 0.12);
}

.primary {
  background: linear-gradient(135deg, var(--accent), var(--accent-strong));
  color: #031018;
}

.status-label {
  color: var(--muted);
  font-size: 14px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 110px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 14px;
  font-weight: 700;
}

.status-badge::before {
  content: "";
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--danger);
  box-shadow: 0 0 12px rgba(255, 122, 156, 0.6);
}

.status-badge.connecting::before {
  background: #ffd166;
  box-shadow: 0 0 12px rgba(255, 209, 102, 0.6);
}

.status-badge.connected::before {
  background: var(--accent-strong);
  box-shadow: 0 0 12px rgba(122, 240, 201, 0.72);
}

.status-badge.error::before {
  background: var(--danger);
  box-shadow: 0 0 12px rgba(255, 122, 156, 0.72);
}

.quick-keys button {
  min-width: 56px;
  padding: 12px 0;
}

@media (max-width: 640px) {
  .shell { padding: 28px 14px 40px; }
  .panel { padding: 20px; border-radius: 22px; }
  .mode-buttons, .status { align-items: stretch; }
  .status-badge { width: 100%; justify-content: center; }
  button { width: 100%; }
  .quick-keys button { width: calc(20% - 8px); min-width: 0; }
}
</style>

</head>
<body>

<div class="shell">
  <div class="panel">
    <p class="eyebrow">Remote Input Console</p>
    <h2>Ubuntu Input</h2>
    <p class="lead">ブラウザから文字列を送り、サーバー側でキーボード入力を再現します。リアルタイム入力とまとめ送信を、接続状態を見ながら切り替えられます。</p>

    <div class="mode-buttons">
      <button onclick="switchMode('live')">リアルタイム</button>
      <button onclick="switchMode('bulk')">まとめ送信</button>
    </div>

    <div class="status">
      <span class="status-label">接続状態</span>
      <span id="wsStatus" class="status-badge">未接続</span>
      <button id="connectButton" class="primary" onclick="connectWebSocket()">接続</button>
    </div>

    <div id="live-mode" class="mode-panel">
      <h3 class="section-title">Live Input</h3>
      <input id="box" autofocus placeholder="type here...">
    </div>

    <div id="bulk-mode" class="mode-panel hidden">
      <h3 class="section-title">Bulk Input</h3>
      <textarea id="bulkBox" placeholder="複数行テキストを入力"></textarea><br>
      <button class="primary" onclick="sendBulk()">送信</button>
    </div>

    <div class="key-panel">
      <h3 class="section-title">Quick Keys</h3>
      <div class="quick-keys">
        <button onclick="sendLive('|')">|</button>
        <button onclick="sendLive('~')">~</button>
        <button onclick="sendLive('\\\\')">\\</button>
        <button onclick="sendLive('&')">&</button>
        <button onclick="sendLive(';')">;</button>
      </div>
    </div>
  </div>
</div>

<script>

const box = document.getElementById("box")
const liveMode = document.getElementById("live-mode")
const bulkMode = document.getElementById("bulk-mode")
const bulkBox = document.getElementById("bulkBox")
const wsStatus = document.getElementById("wsStatus")
const connectButton = document.getElementById("connectButton")
let socket = null
let isComposingText = false
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
}

function connectWebSocket(){
 if(socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)){
   return
 }

 setStatus("接続中", "connecting")
 connectButton.disabled = true
 const protocol = location.protocol === "https:" ? "wss:" : "ws:"
 socket = new WebSocket(protocol + "//" + location.host + "/ws")
 socket.addEventListener("open", function(){
   setStatus("接続済み", "connected")
   connectButton.disabled = true
 })
 socket.addEventListener("error", function(){
   setStatus("接続失敗", "error")
   connectButton.disabled = false
 })
 socket.addEventListener("close", function(){
   setStatus("未接続", "")
   connectButton.disabled = false
 })
}

function setStatus(text, statusClass){
 wsStatus.textContent = text
 wsStatus.className = "status-badge"
 if(statusClass){
   wsStatus.classList.add(statusClass)
 }
}

function sendMessage(message){
 if(socket && socket.readyState === WebSocket.OPEN){
   socket.send(JSON.stringify(message))
  }
}

function sendLive(text){
 sendMessage({type:"text", text:text})
}

function sendControlKey(key){
 sendMessage({type:"key", key:key})
}

function switchMode(mode){
 if(mode === "live"){
   liveMode.classList.remove("hidden")
   bulkMode.classList.add("hidden")
   box.focus()
 }else{
   bulkMode.classList.remove("hidden")
   liveMode.classList.add("hidden")
   document.getElementById("bulkBox").focus()
 }
}

function sendBulk(){
 const text = bulkBox.value
 if(!text) return
 sendMessage({type:"bulk", text:text})
 bulkBox.value = ""
}

// Enterのような非テキストキーだけkeydownで扱う
box.addEventListener("keydown",function(e){
 if(e.isComposing) return

 const mappedKey = controlKeyMap[e.key]
 if(mappedKey){
   sendControlKey(mappedKey)
   e.preventDefault()
 }
})

// 通常の文字入力は、文字が確定した後のinputイベントで送る
box.addEventListener("input",function(e){
 if(e.isComposing || isComposingText) return

 const text = box.value
 if(!text) return

 sendLive(text)
 box.value = ""
})

box.addEventListener("compositionstart", function(){
 isComposingText = true
})

box.addEventListener("compositionend", function(e){
 isComposingText = false

 const text = e.data || box.value
 if(!text) return

 sendLive(text)
 box.value = ""
})

bulkBox.addEventListener("keydown", function(e){
 if(e.key === "Enter" && e.ctrlKey){
   e.preventDefault()
   sendBulk()
 }
})

connectWebSocket()

</script>

</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            self.handle_websocket()
            return

        self.send_response(200)
        self.send_header("Content-type","text/html")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def handle_websocket(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_response(400)
            self.end_headers()
            return

        accept = create_websocket_accept(key)
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()

        while True:
            opcode, payload = read_websocket_frame(self.connection)
            if opcode is None:
                break
            if opcode == 0x8:
                send_websocket_close(self.connection)
                break
            if opcode == 0x9:
                send_websocket_pong(self.connection, payload)
                continue
            if opcode != 0x1:
                continue

            handle_message(payload.decode("utf-8"))

    def log_message(self, format, *args):
        return


def create_websocket_accept(key):
    value = key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    digest = hashlib.sha1(value.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("ascii")


def read_exact(sock, size):
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_websocket_frame(sock):
    header = read_exact(sock, 2)
    if not header:
        return None, None

    first_byte, second_byte = header
    opcode = first_byte & 0x0F
    masked = second_byte & 0x80
    payload_length = second_byte & 0x7F

    if payload_length == 126:
        extended = read_exact(sock, 2)
        if not extended:
            return None, None
        payload_length = struct.unpack("!H", extended)[0]
    elif payload_length == 127:
        extended = read_exact(sock, 8)
        if not extended:
            return None, None
        payload_length = struct.unpack("!Q", extended)[0]

    mask = b""
    if masked:
        mask = read_exact(sock, 4)
        if not mask:
            return None, None

    payload = read_exact(sock, payload_length)
    if payload is None:
        return None, None

    if masked:
        payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))

    return opcode, payload


def send_websocket_frame(sock, opcode, payload=b""):
    first_byte = 0x80 | opcode
    payload_length = len(payload)

    if payload_length < 126:
        header = bytes([first_byte, payload_length])
    elif payload_length < 65536:
        header = bytes([first_byte, 126]) + struct.pack("!H", payload_length)
    else:
        header = bytes([first_byte, 127]) + struct.pack("!Q", payload_length)

    sock.sendall(header + payload)


def send_websocket_pong(sock, payload):
    send_websocket_frame(sock, 0xA, payload)


def send_websocket_close(sock):
    send_websocket_frame(sock, 0x8)


def handle_message(raw_message):
    try:
        message = json.loads(raw_message)
    except json.JSONDecodeError:
        return

    message_type = message.get("type")
    if message_type == "text":
        send_text(message.get("text", ""))
    elif message_type == "key":
        send_control_key(message.get("key", ""))
    elif message_type == "bulk":
        send_multiline_text(message.get("text", ""))


def send_text(text):
    for char in text:
        send_character(char)


def send_control_key(key):
    if key:
        subprocess.run(["xdotool", "key", "--clearmodifiers", key])


def send_character(char):
    mapped_key = SYMBOL_KEYMAP.get(char)
    if mapped_key:
        subprocess.run(["xdotool", "key", "--clearmodifiers", mapped_key])
    else:
        subprocess.run(["xdotool", "type", "--clearmodifiers", char])


def send_multiline_text(text):
    normalized = text.replace("\\r\\n", "\\n").replace("\\r", "\\n")
    lines = normalized.split("\\n")

    for i, line in enumerate(lines):
        if line:
            for char in line:
                send_character(char)
        if i < len(lines) - 1:
            send_control_key("Return")


server = ThreadingHTTPServer(("0.0.0.0",5000),Handler)

print("server start : http://localhost:5000")

server.serve_forever()
