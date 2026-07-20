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
    echo "[提示] 使用 WorkBuddy 托管 Node: $MANAGED_NODE_BIN"
  fi
fi

# ---- 1. Python 后端环境 ----
# 项目要求 Python >= 3.12，优先探测 3.12+ 解释器（包括 WorkBuddy 托管版本）
find_python() {
  local candidates=(
    "${PYTHON:-}"
    python3.13 python3.12 python3.14
    "$HOME/.workbuddy/binaries/python/versions"/*/bin/python3
    python3
  )
  for c in "${candidates[@]}"; do
    if [[ -z "$c" || "$c" == *"*" ]]; then
      # 处理通配符未匹配的情况
      continue
    fi
    if command -v "$c" >/dev/null 2>&1 || [[ -x "$c" ]]; then
      local ver
      ver="$("$c" --version 2>/dev/null | awk '{print $2}')"
      if [[ -n "$ver" && "$(printf '%s\n' "3.12" "$ver" | sort -V | head -1)" == "3.12" ]]; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "错误：未找到 Python 3.12 或更高版本。" >&2
  echo "当前系统 python3 版本为：$(python3 --version 2>/dev/null || echo '未安装')" >&2
  echo "请安装 Python 3.12+，或安装 WorkBuddy 托管运行时。" >&2
  exit 1
fi

echo "[0/4] 使用 Python: $PYTHON_BIN ($($PYTHON_BIN --version 2>&1))"
VENV_DIR="$APP_DIR/.venv"

if [[ -d "$VENV_DIR" ]]; then
  venv_version="$("$VENV_DIR/bin/python" --version 2>/dev/null | awk '{print $2}' || echo '0.0')"
  if [[ -n "$venv_version" && "$(printf '%s\n' '3.12' "$venv_version" | sort -V | head -1)" != "3.12" ]]; then
    echo "[1/4] 当前虚拟环境 Python 版本过低 ($venv_version)，删除重建 ..."
    rm -rf "$VENV_DIR"
  fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[1/4] 创建 Python 虚拟环境 ($VENV_DIR) ..."
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
( cd "$APP_DIR/frontend" && "$PKG_MGR" install --registry=https://registry.npmmirror.com )

# ---- 3. 启动后端 (后台) ----
echo "[4/4] 启动服务 ..."
mkdir -p "$APP_DIR/data"
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
