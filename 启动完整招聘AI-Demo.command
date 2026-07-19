#!/bin/zsh
# 启动完整招聘 AI Demo（React 前端 + Python FastAPI 后端 + SQLite）
# 双击此文件即可在 macOS 上同时拉起前后端并打开浏览器。
set -eu

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

echo "=================================================="
echo " 招聘 AI Demo 一键启动"
echo " 后端: http://localhost:8000  (FastAPI + SQLite)"
echo " 前端: http://localhost:3000  (React)"
echo "=================================================="

# ---- 0. 定位运行时（PATH 找不到时，回退到 WorkBuddy 托管的 node/python）----
# 双击 .command 时，Terminal 的 PATH 往往不含 WorkBuddy 内置运行时，这里做兜底。
if ! command -v node >/dev/null 2>&1; then
  MANAGED_NODE_BIN="$(ls -d "$HOME/.workbuddy/binaries/node/versions"/*/bin 2>/dev/null | sort -V | tail -1)"
  if [[ -n "${MANAGED_NODE_BIN:-}" && -x "$MANAGED_NODE_BIN/node" ]]; then
    export PATH="$MANAGED_NODE_BIN:$PATH"
    echo "[0/4] 使用 WorkBuddy 托管 Node: $MANAGED_NODE_BIN"
  fi
fi

# ---- 1. Python 后端环境 ----
if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  MANAGED_PY="$(ls -d "$HOME/.workbuddy/binaries/python/versions"/*/bin/python3 2>/dev/null | sort -V | tail -1)"
  PYTHON_BIN="${MANAGED_PY:-python3}"
fi
VENV_DIR="$APP_DIR/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[1/4] 首次运行：创建 Python 虚拟环境 ($VENV_DIR) ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[2/4] 安装 / 更新 Python 依赖 ..."
pip install --quiet --upgrade pip
pip install --quiet -e .

# ---- 2. 前端依赖 ----
echo "[3/4] 安装前端依赖 ..."
if command -v pnpm >/dev/null 2>&1; then
  PKG_MGR="pnpm"
else
  PKG_MGR="npm"
  if ! command -v npm >/dev/null 2>&1; then
    echo "未找到 node/npm。请安装 Node.js (https://nodejs.org)，" >&2
    echo "或确认 ~/.workbuddy/binaries/node 下存在托管版本。" >&2
    exit 1
  fi
fi
( cd "$APP_DIR/frontend" && "$PKG_MGR" install )

# ---- 3. 启动后端 (后台) ----
echo "[4/4] 启动服务 ..."
export AI_MODE="${AI_MODE:-fake}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///data/recruitment.db}"
export PYTHONPATH="$APP_DIR"

uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload \
  > "$APP_DIR/data/backend.log" 2>&1 &
BACKEND_PID=$!

( cd "$APP_DIR/frontend" && "$PKG_MGR" run dev ) \
  > "$APP_DIR/data/frontend.log" 2>&1 &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "正在停止服务 ..."
  kill "$BACKEND_PID" 2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 等待后端健康检查通过
echo "等待后端就绪 ..."
for i in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "打开前端页面：http://localhost:3000"
open "http://localhost:3000" 2>/dev/null || true

echo "服务运行中。关闭此窗口将同时停止前后端。"
wait
