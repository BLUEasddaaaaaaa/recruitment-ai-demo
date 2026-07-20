#!/bin/zsh
set -eu

APP_DIR="/Users/molan/Documents/Codex/2026-07-19/hr-ai/.worktrees/recruitment-ai-demo"
STREAMLIT_BIN="$APP_DIR/.venv312/bin/streamlit"
DEMO_URL="http://127.0.0.1:8501"

if [[ ! -d "$APP_DIR" ]]; then
  echo "找不到 Demo 目录：$APP_DIR" >&2
  exit 1
fi

if [[ ! -x "$STREAMLIT_BIN" ]]; then
  echo "找不到 Demo 运行环境：$STREAMLIT_BIN" >&2
  echo "请先按照 outputs/招聘AI-Demo运行说明.md 安装依赖。" >&2
  exit 1
fi

if [[ "${1:-}" == "--check" ]]; then
  echo "Demo 启动环境检查通过"
  echo "$DEMO_URL"
  exit 0
fi

cd "$APP_DIR"
mkdir -p data

if curl --fail --silent "$DEMO_URL/_stcore/health" >/dev/null 2>&1; then
  echo "Demo 已在运行：$DEMO_URL"
  open "$DEMO_URL"
  exit 0
fi

echo "正在启动招聘数据 AI 自动化 Demo……"
echo "浏览器地址：$DEMO_URL"
(sleep 2; open "$DEMO_URL") &

AI_MODE=fake \
DATABASE_URL=sqlite:///data/demo.db \
PYTHONPATH="$APP_DIR" \
exec "$STREAMLIT_BIN" run src/app.py \
  --server.headless true \
  --server.address 127.0.0.1 \
  --server.port 8501
