import os

# 客户模式：不展示 API 输入框与提示词调试面板
os.environ["CUSTOMER_MODE"] = "1"

import app  # noqa: F401
