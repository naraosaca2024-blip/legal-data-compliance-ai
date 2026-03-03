#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/spoonlaw/code"
VENV_DIR="$PROJECT_DIR/.venv311"
APP_FILE="$PROJECT_DIR/app.py"
KB_PROC="$PROJECT_DIR/knowledge_processor.py"
VECTOR_STORE="$PROJECT_DIR/vector_store"
ENV_FILE="$PROJECT_DIR/.env.local"
PORT="8511"
APP_URL="http://127.0.0.1:${PORT}"

cd "$PROJECT_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[错误] 未找到虚拟环境: $VENV_DIR"
  echo "请先在项目目录创建 Python 3.11 虚拟环境"
  read -k 1 "?按任意键退出..."
  exit 1
fi

source "$VENV_DIR/bin/activate"

if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi

if [[ -z "${DASHSCOPE_API_KEY:-}" ]]; then
  API_KEY_INPUT=$(osascript <<'APPLESCRIPT'
    try
      display dialog "请输入 DashScope API Key（仅当前启动会话使用）" default answer "" with hidden answer buttons {"确定"} default button "确定"
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

echo "[信息] 正在启动数据合规平台..."
echo "[信息] 打开地址: ${APP_URL}"
echo "[提示] 如遇白屏，请使用无痕/隐私窗口并禁用浏览器扩展后访问。"
open "$APP_URL" >/dev/null 2>&1 || true

exec streamlit run "$APP_FILE" --server.address 0.0.0.0 --server.port "$PORT"
