# input_server

ブラウザまたは Chrome 拡張から送った文字列を、サーバー側で `xdotool` または `ydotool` を使ってキーボード入力として再現するシンプルな入力サーバーです。

## 目的

手元のブラウザや Chrome 拡張から文字を入力し、別の Linux 環境上でその文字を実際のキー入力のように送ることを目的としています。

もともとは NanoKVM を使っている時に、KVM 側が日本語キーボードに十分対応しておらず、`|` や `_` などの記号をうまく入力できなかったため、その補助用として作りました。

たとえば次のような用途を想定しています。

- リモート先で文字入力を補助したい
- 日本語を含むテキストをブラウザから送りたい
- 単発入力と複数行入力を使い分けたい

## できること

- リアルタイム入力
  - 入力欄に打った文字をそのまま送信
  - 英数字は通常入力として送信
  - `Enter`、`Backspace`、矢印キーなどの制御キーは別送信
  - 日本語入力は IME 確定時に送信
- まとめ送信
  - 複数行テキストを textarea に入力してまとめて送信
  - `Ctrl+Enter` でも送信可能
  - 送信後は textarea をクリア
- WebSocket 通信
  - ブラウザまたは Chrome 拡張とサーバー間を WebSocket で接続
  - 接続状態を画面に表示
  - 未接続時は接続ボタンで再接続可能
- クイックキー送信
  - よく使う記号をボタンから送信
- サーバークリップボード表示
  - サーバー側 PC のクリップボード内容を拡張から取得
  - 拡張上で内容を確認してコピー可能

## 必要なもの

- Python 3
- X11 環境の場合は `xdotool`
- Wayland 環境の場合は `ydotool` と、起動済みの `ydotoold`

クリップボード取得機能を使う場合は、以下のいずれかも必要です。

- `xclip`
- `xsel`
- `wl-paste`

どちらのツールでも、入力先ウィンドウがフォーカスされている必要があります。

`ydotool` は Linux の `/dev/uinput` を使います。ディストリビューションの手順に従って `ydotoold` を起動し、サーバーを実行するユーザーがそのソケットへアクセスできるようにしてください。ソケットの場所を変更している場合は、サーバー起動時にも `YDOTOOL_SOCKET` を設定します。

## 使い方

### 1. サーバーを起動する

```bash
python3 input_server.py
```

入力ツールは実行環境から自動判定されます。明示的に選ぶ場合は `INPUT_BACKEND` を指定します。

Wayland で `ydotool` を使う場合:

```bash
INPUT_BACKEND=ydotool python3 input_server.py
```

X11 で従来の `xdotool` を使う場合:

```bash
INPUT_BACKEND=xdotool python3 input_server.py
```

`INPUT_BACKEND=auto`（既定値）は、`XDG_SESSION_TYPE` と `WAYLAND_DISPLAY` / `DISPLAY` を確認して選択します。セッション情報がない場合は、従来互換のため `xdotool` を優先します。

`ydotool` で使うキーボード配列は `YDOTOOL_KEYBOARD_LAYOUT=auto|jp|us` で選択できます。既定の `auto` は `XKB_DEFAULT_LAYOUT`、次に `/etc/default/keyboard` を確認します。日本語JIS配列を明示する場合は次のように起動します。

```bash
YDOTOOL_KEYBOARD_LAYOUT=jp python3 input_server.py
```

起動すると、以下のURLで待ち受けます。

```text
http://localhost:5000
```

### 2-A. ブラウザで開く

同じマシン、またはアクセス可能な別マシンのブラウザで次を開きます。

```text
http://<server-ip>:5000
```

### 2-B. Chrome 拡張で開く

このリポジトリの `extension/` を Chrome に読み込みます。

1. Chrome で `chrome://extensions` を開く
2. 右上の `デベロッパー モード` を有効にする
3. `パッケージ化されていない拡張機能を読み込む` を押す
4. このプロジェクトの `extension` ディレクトリを選ぶ

読み込み後、ツールバーの拡張アイコンから `Input Server` を開けます。

拡張では接続先を保存できます。たとえば次のどちらでも指定できます。

```text
ws://127.0.0.1:5000/ws
```

```text
http://127.0.0.1:5000
```

### 3. 接続する

ブラウザ画面または拡張 popup の上部に WebSocket の接続状態が表示されます。

- `未接続`: まだ接続していない状態
- `接続中`: 接続処理中
- `接続済み`: 入力可能
- `接続失敗`: 接続に失敗

`未接続` または `接続失敗` の場合は `接続` ボタンを押してください。

### 4. 入力する

#### リアルタイム

- `リアルタイム` モードを選ぶ
- 入力欄に文字を入力する
- 日本語は変換確定時に送信される
- `Enter` や矢印キーなどは制御キーとして送信される

#### まとめ送信

- `まとめ送信` モードを選ぶ
- テキストエリアに複数行入力する
- `送信` ボタン、または `Ctrl+Enter` で送信する

## Chrome 拡張のファイル

```text
extension/
├── manifest.json
├── popup.css
├── popup.html
└── popup.js
```

テーマは次に分けてあります。

```text
extension/themes/
├── canyon-dusk.css
├── http-legacy.css
├── matcha-paper.css
├── moon-slate.css
└── solar-flare.css
```

HTTP 版の画面もこの `extension/popup.html`, `extension/popup.css`, `extension/popup.js` をそのまま使って配信します。

元の HTTP 版の色合いは次に退避しています。

```text
legacy/http_legacy_theme.css
```

## 注意点

- 入力先は選択した入力ツールが送信できるアクティブウィンドウです
- Wayland では `ydotoold` が動作し、`ydotool` からソケットへ接続できる必要があります
- 記号や IME 周りは環境差の影響を受けることがあります
- リアルタイム入力では、入力したキーと違うキーが入力される場合があります
- `ydotool` では US 配列と日本語JIS配列に対応しています。それ以外の配列は `us` として扱われるため、一部の記号が一致しない場合があります
- `ydotool type` は ASCII 入力向けです。安全のため、日本語などの非 ASCII 文字は `ydotool` 選択時には送信せず、サーバーの標準出力へ表示します（`xdotool` 選択時の従来処理には影響しません）
- 文字入力の正確さを最優先する場合、`xdotool` と `ydotool` のどちらにも限界があります
