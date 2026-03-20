from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import hashlib
import json
from pathlib import Path
import shutil
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

BASE_DIR = Path(__file__).resolve().parent
EXTENSION_DIR = BASE_DIR / "extension"


def read_text_file(path):
    return path.read_text(encoding="utf-8")

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            self.handle_websocket()
            return
        if parsed.path == "/clipboard":
            self.handle_clipboard_request()
            return
        if parsed.path == "/popup.css":
            self.send_static_file(EXTENSION_DIR / "popup.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/popup.js":
            self.send_static_file(EXTENSION_DIR / "popup.js", "application/javascript; charset=utf-8")
            return
        if parsed.path.startswith("/themes/"):
            self.send_static_file(EXTENSION_DIR / parsed.path.lstrip("/"), "text/css; charset=utf-8")
            return

        self.send_static_file(EXTENSION_DIR / "popup.html", "text/html; charset=utf-8")

    def handle_clipboard_request(self):
        text, error = get_clipboard_text()
        if error:
            self.send_json_response(500, {
                "ok": False,
                "error": error
            })
            return

        self.send_json_response(200, {
            "ok": True,
            "text": text
        })

    def send_json_response(self, status_code, payload):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def send_static_file(self, path, content_type):
        try:
            encoded = read_text_file(path).encode("utf-8")
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

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


def get_clipboard_text():
    commands = []

    if shutil.which("xclip"):
        commands.append(["xclip", "-selection", "clipboard", "-o"])
    if shutil.which("xsel"):
        commands.append(["xsel", "--clipboard", "--output"])
    if shutil.which("wl-paste"):
        commands.append(["wl-paste", "--no-newline"])

    if not commands:
        return "", "Clipboard command not found. Install xclip, xsel, or wl-paste."

    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout, None

    return "", "Failed to read clipboard."


server = ThreadingHTTPServer(("0.0.0.0",5000),Handler)

print("server start : http://localhost:5000")

server.serve_forever()
