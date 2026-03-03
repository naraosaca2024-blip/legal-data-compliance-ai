#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/spoonlaw/code"
VENV_DIR="$PROJECT_DIR/.venv311"
APP_FILE="$PROJECT_DIR/app_client.py"
KB_PROC="$PROJECT_DIR/knowledge_processor.py"
VECTOR_STORE="$PROJECT_DIR/vector_store"
ENV_FILE="$PROJECT_DIR/.env.local"

cd "$PROJECT_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[错误] 未找到虚拟环境: $VENV_DIR"
  read -k 1 "?按任意键退出..."
  exit 1
fi
source "$VENV_DIR/bin/activate"

if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi

if [[ -z "${DASHSCOPE_API_KEY:-}" ]]; then
  echo "[错误] 未读取到 DASHSCOPE_API_KEY。请在 $ENV_FILE 中配置。"
  read -k 1 "?按任意键退出..."
  exit 1
fi

if [[ ! -f "$VECTOR_STORE/metadata.json" ]]; then
  echo "[信息] 未检测到本地向量库，开始自动构建..."
  python "$KB_PROC" --knowledge "$PROJECT_DIR/knowledge" --vector-store "$VECTOR_STORE"
fi

echo "[信息] 启动客户版服务: http://localhost:8501"
open "http://localhost:8501" >/dev/null 2>&1 || true
exec streamlit run "$APP_FILE" --server.address 0.0.0.0 --server.port 8501
