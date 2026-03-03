#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/spoonlaw/code"
VENV_DIR="$PROJECT_DIR/.venv311"
APP_FILE="$PROJECT_DIR/app.py"
KB_PROC="$PROJECT_DIR/knowledge_processor.py"
VECTOR_STORE="$PROJECT_DIR/vector_store"

cd "$PROJECT_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[错误] 未找到虚拟环境: $VENV_DIR"
  echo "请先创建: python3.11 -m venv $VENV_DIR"
  read -k 1 "?按任意键退出..."
  exit 1
fi

source "$VENV_DIR/bin/activate"

if [[ -z "${DASHSCOPE_API_KEY:-}" ]]; then
  API_KEY_INPUT=$(osascript <<'APPLESCRIPT'
    try
      display dialog "请输入 DashScope API Key（仅本次启动使用）" default answer "" with hidden answer buttons {"确定"} default button "确定"
      text returned of result
    on error
      return ""
    end try
APPLESCRIPT
)
  if [[ -z "$API_KEY_INPUT" ]]; then
    echo "[错误] 未提供 API Key，已取消启动。"
    read -k 1 "?按任意键退出..."
    exit 1
  fi
  export DASHSCOPE_API_KEY="$API_KEY_INPUT"
fi

if [[ ! -f "$VECTOR_STORE/metadata.json" ]]; then
  echo "[信息] 未检测到本地向量库，开始自动构建..."
  python "$KB_PROC" --knowledge "$PROJECT_DIR/knowledge" --vector-store "$VECTOR_STORE"
fi

echo "[信息] 启动 Streamlit 服务..."
echo "[信息] 地址: http://localhost:8501"
open "http://localhost:8501" >/dev/null 2>&1 || true

exec streamlit run "$APP_FILE" --server.address 0.0.0.0 --server.port 8501
