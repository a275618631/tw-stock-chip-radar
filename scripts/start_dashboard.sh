#!/bin/bash
set -u
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="$REPO_ROOT/docs"
REPORT="$REPO_ROOT/reports/daily_market_report.html"
NO_BROWSER=0
SKIP_PULL=0
PORT=8765

usage() {
  echo "Usage: $0 [--no-browser] [--skip-pull] [--port PORT]"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-browser) NO_BROWSER=1 ;;
    --skip-pull) SKIP_PULL=1 ;;
    --port)
      shift
      PORT="${1:-}"
      if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then echo "Port 必須是數字。"; exit 1; fi
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知參數：$1"; usage; exit 1 ;;
  esac
  shift
done

if [ "$SKIP_PULL" -eq 1 ]; then
  echo "已略過 git pull（--skip-pull）。"
elif command -v git >/dev/null 2>&1; then
  if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
    echo "警告：工作區有未提交修改，保留現況，不執行 pull。"
  else
    branch="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || true)"
    if [ "$branch" != "main" ]; then
      git -C "$REPO_ROOT" switch main || echo "警告：無法切換 main；使用目前資料。"
    fi
    if [ "$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || true)" = "main" ]; then
      git -C "$REPO_ROOT" pull --ff-only origin main || echo "警告：main 更新失敗；使用本機 cached data。"
    fi
  fi
else
  echo "警告：找不到 Git；使用本機現有資料。"
fi

PYTHON=""
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON="$(command -v python)"
fi

if [ -z "$PYTHON" ]; then
  echo "找不到 Python 3。互動 Dashboard 需要本機 static HTTP server。"
  if [ -f "$REPORT" ]; then echo "你仍可以直接打開 reports/daily_market_report.html。"; fi
  exit 1
fi

port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$1" >/dev/null 2>&1
  else
    return 1
  fi
}

SELECTED_PORT="$PORT"
while [ "$SELECTED_PORT" -lt $((PORT + 20)) ] && port_in_use "$SELECTED_PORT"; do
  SELECTED_PORT=$((SELECTED_PORT + 1))
done
if [ "$SELECTED_PORT" -ge $((PORT + 20)) ]; then
  echo "找不到可用的 Dashboard port（$PORT-$((PORT + 19))）。"
  exit 1
fi

LOG_FILE="${TMPDIR:-/tmp}/tw-stock-chip-radar-http-$SELECTED_PORT.log"
nohup "$PYTHON" -m http.server "$SELECTED_PORT" -d "$DOCS_DIR" >"$LOG_FILE" 2>&1 &
SERVER_PID=$!
URL="http://127.0.0.1:$SELECTED_PORT"

health_ok=0
for _ in $(seq 1 20); do
  if curl -fsS "$URL/" >/dev/null 2>&1 && curl -fsS "$URL/data/daily_radar.json" | "$PYTHON" -c 'import json,sys; json.load(sys.stdin)' >/dev/null 2>&1; then
    health_ok=1
    break
  fi
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then break; fi
  sleep 0.5
done

if [ "$health_ok" -ne 1 ]; then
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  echo "互動 Dashboard 啟動失敗。"
  echo "HTTP health check 未通過；未將此誤判為 GitHub Actions 資料失敗。"
  if [ -f "$REPORT" ]; then echo "你仍可直接打開 reports/daily_market_report.html。"; fi
  exit 1
fi

echo "台股籌碼雷達 Dashboard：$URL/"
if [ "$NO_BROWSER" -eq 1 ]; then
  echo "已略過開啟瀏覽器（--no-browser）。"
else
  open "$URL/"
fi
