# 客户使用指南（数据合规平台）

## 1. 本机直接使用（最简单）
1. 双击桌面 `数据合规平台.app`。
2. 首次启动若提示输入 API Key，输入后即可使用。
3. 浏览器访问 `http://localhost:8501`。

## 2. 局域网给客户使用（推荐）
前提：你和客户在同一局域网。

1. 在你的电脑启动平台（双击 `数据合规平台.app`）。
2. 获取你的内网 IP：
```bash
ipconfig getifaddr en0
```
3. 客户在浏览器访问：`http://你的内网IP:8501`。
4. 若访问失败，放行 macOS 防火墙中 Python/Terminal 的入站连接。

## 3. 公网给外部客户使用
前提：有云主机（建议 Linux）+ 域名 + HTTPS。

1. 将 `/Users/spoonlaw/code` 部署到云主机。
2. 使用 `systemd` 启动 Streamlit（监听 `0.0.0.0:8501`）。
3. 用 Nginx 反向代理并配置 SSL（Let's Encrypt）。
4. 客户通过 `https://你的域名` 访问。

## 4. 安全建议
- API Key 不要写入代码，使用环境变量。
- 给客户演示时建议用受限权限 Key。
- 定期轮换 Key，发现泄露立即失效旧 Key。
- 客户数据若敏感，优先走局域网或内网部署。

## 5. 常见问题
- 启动失败：检查 `.venv311` 是否存在。
- 向量库缺失：脚本会自动构建；也可手动运行：
```bash
cd /Users/spoonlaw/code
source .venv311/bin/activate
python knowledge_processor.py --knowledge knowledge --vector-store vector_store
```
