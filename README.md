# Legal Data Compliance AI (数据合规 AI 助手)

本项目是一个专注于数据合规、数据资产入表及数据确权领域的智能法律辅助系统。通过引入检索增强生成（RAG）技术，本项目能够结合专业的法律合规知识库，为企业或个人提供精准、高效的法律数据合规问答与审查工具。

为了确保企业数据与法律分析的绝对安全，本项目支持本地化部署（Local RAG）与数据隔离，旨在满足最高标准的数据安全要求。

## 📂 项目结构

项目的核心逻辑围绕大语言模型（如 Claude 或本地模型）的 RAG 架构展开，目录结构如下：

* **`app.py`**: 主应用服务端入口。
* **`app_client.py`**: 客户端交互脚本。
* **`local_rag.py`**: 本地 RAG（检索增强生成）核心处理模块。
* **`knowledge_processor.py`**: 知识库向量化与预处理工具。
* **`compliance_tool.py`**: 合规审查核心算法与规则集。
* **`CLIENT_USAGE.md`**: 客户端详细使用说明。
* **`scripts/`**: 自动化运维与环境配置脚本。
* **`knowledge/`**: 法律合规专家知识库，按以下业务场景分类：
    * `0_base_compliance/`: 基础合规法律法规。
    * `1_data_product_compliance/`: 数据产品合规标准。
    * `2_data_asset_listing/`: 数据资产入表规范与指引。
    * `3_industry_cases/`: 行业典型合规案例。
    * `4_data_rights/`: 数据确权与知识产权保护。

## ✨ 核心特性

* **专业的法律知识体系**：内置分类明确的法律合规知识库，覆盖从基础合规到数据产品商业化的全生命周期。
* **智能检索与问答 (RAG)**：通过 `local_rag.py` 实现本地文档的高效检索，结合 LLM 强大的推理能力，提供有理有据的法律合规建议。支持灵活接入外部大模型（如高阶 Claude API）或本地开源模型进行推理。
* **数据安全与隐私保护**：系统架构设计高度关注数据安全。所有的知识库预处理（`knowledge_processor.py`）及敏感合规审查均可在本地环境完成，避免核心业务数据外泄。本系统在软件开发层面严格遵循数据安全最佳实践。建议在向外部大语言模型（如 Claude）提交合规审查请求时，使用 compliance_tool.py 中内置的数据脱敏模块，确保查询中不包含真实的企业敏感信息或个人隐私数据。
* **开箱即用的客户端**：提供轻量级的 `app_client.py`，方便用户直接与合规知识引擎进行交互。

## 🚀 快速开始

### 1. 环境准备

请确保您的本地环境中已安装 Python 3.8+ 及必要的依赖库。

```bash
# 克隆仓库
git clone https://github.com/naraosaca2024-blip/legal-data-compliance-ai.git
cd legal-data-compliance-ai
```

### 2. 依赖安装

安装项目所需的所有 Python 依赖：

```bash
pip install -r requirements.txt
```

常见的依赖包括：
- `langchain`: LLM 框架与 RAG 集成
- `faiss-cpu` 或 `faiss-gpu`: 向量数据库
- `openai` 或 `anthropic`: LLM API 客户端
- `Flask` 或 `FastAPI`: Web 服务框架
- `python-dotenv`: 环境变量管理

### 3. 配置设置

在项目根目录创建 `.env` 文件，配置必要的 API 密钥和模型参数：

```env
# LLM 配置
LLM_PROVIDER=anthropic  # 或 openai
ANTHROPIC_API_KEY=your_api_key_here
# OPENAI_API_KEY=your_api_key_here（如使用 OpenAI）

# 本地模型配置（可选）
USE_LOCAL_MODEL=false
LOCAL_MODEL_PATH=/path/to/local/model

# 向量数据库配置
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
FAISS_INDEX_PATH=./faiss_index

# 应用配置
APP_PORT=5000
LOG_LEVEL=INFO
```

### 4. 知识库初始化

在启动应用前，需要对 `knowledge/` 目录下的法律文本进行切分与向量化处理：

```bash
python knowledge_processor.py --init
```

初始化过程中：
- 扫描 `knowledge/` 目录下所有法律文档
- 对文档进行智能分块（Chunking）
- 生成向量嵌入（Embeddings）
- 构建本地 FAISS 索引

预期输出：
```
[INFO] 加载知识库文档...
[INFO] 处理文件: 0_base_compliance/data_protection_law.md
[INFO] 向量化完成，共处理 1500 个文本块
[INFO] FAISS 索引已保存至 ./faiss_index
```

### 5. 启动服务与客户端

#### 启动后端合规引擎：

```bash
python app.py
```

成功启动后，你应该看到：
```
 * Running on http://127.0.0.1:5000
 * 合规 RAG 引擎已就绪
```

#### 启动用户交互客户端（新终端窗口）：

```bash
python app_client.py
```

## 💡 使用示例


1. **Data Product Compliance Analysis (产品模式)**  
   - **综合评价指标**:  
     • 合规性评分: 90%  
     • 三权确认:  
       - 数据来源: Verified  
       - 权属: Clear  
       - 使用限制: Compliant  
   - **评分细节**:  
     • 法律合规: 45/50  
     • 市场适应性: 40/50  
   - **专业建议**:  该数据产品符合相关法律法规，建议定期审查其使用情况并参考《数据保护法》第3章。

2. **Data Asset Listing Analysis (资产模式)**  
   - **财务指标**:  
     • 资产总值: ￥1,000,000  
     • 净收益: ￥150,000  
   - **会计细节**:  
     • 资产分类: 固定资产  
     • 报表日期: 2026年2月28日  
   - **资产评估**:  
     • 市场价值: ￥1,050,000  
     • 评分: 85%  
   - **建议**:  针对资产组合的多样化进行投资，以应对市场波动，具体可参考《会计准则》第8条。

3. **Industry Case Matching (产业模式)**  
   - **案例匹配**:  
     • 匹配案例数量: 10  
     • 合规评估: 92%  
   - **三权确认**:  
     • 案例来源: Validated  
     • 权属: Confirmed  
     • 使用限制: Compliant  
   - **建议**:  针对行业用例的合规性进行深入分析，建议参考《行业标准法》第5章，并进行定期的合规检查。

### API 调用

```bash
curl -X POST http://localhost:5000/api/compliance_query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "个人数据跨境传输需要哪些审批？",
    "context": "数据产品运营"
  }'
```

## 🔧 配置选项详解

### 使用本地模型（推荐用于生产环境）

如需离线使用或增强数据隐私，可配置本地模型：

```env
USE_LOCAL_MODEL=true
LOCAL_MODEL_PATH=./models/llama-2-7b-chat
EMBEDDING_MODEL=./models/bge-small-zh
```

### 调整向量检索参数

编辑 `local_rag.py` 中的配置：

```python
RAG_CONFIG = {
    'chunk_size': 512,           # 文本分块大小
    'chunk_overlap': 50,          # 分块重叠
    'retrieval_top_k': 5,         # 检索返回文档数
    'similarity_threshold': 0.6,  # 相似度阈值
}
```

## ❓ 常见问题与故障排除

### Q1: 导入 FAISS 时报错 "No module named 'faiss'"

**解决方案**：
```bash
# CPU 版本
pip install faiss-cpu

# GPU 版本（CUDA）
pip install faiss-gpu
```

### Q2: 向量化过程缓慢

**原因**：通常是由于首次处理大量文档或使用 CPU 推理。

**优化方案**：
- 使用 GPU 加速（`faiss-gpu`）
- 减小 `chunk_size` 或使用更轻量的嵌入模型
- 启用多进程处理：`python knowledge_processor.py --init --workers 4`

### Q3: API 调用返回 401 错误

**原因**：API 密钥配置错误或已过期。

**解决**：
1. 检查 `.env` 文件中的 API 密钥是否正确
2. 确保密钥未过期或被禁用
3. 重启应用：`python app.py`

### Q4: 检索结果不相关

**调整方案**：
1. 增加 `retrieval_top_k` 以获取更多候选文档
2. 降低 `similarity_threshold` 阈值
3. 检查知识库中是否包含相关文档

### Q5: 如何增加自定义法律文档？

**步骤**：
1. 将文档（.md 或 .txt 格式）放入 `knowledge/` 相应目录
2. 重新运行初始化：`python knowledge_processor.py --init`
3. 重启应用使变更生效

## 📚 进阶用法

### 自定义 RAG 策略

编辑 `local_rag.py` 以实现自定义检索逻辑：

```python
from local_rag import CustomRetriever

class MyCustomRetriever(CustomRetriever):
    def retrieve(self, query):
        # 自定义检索逻辑
        pass
```

### 集成外部知识源

```python
from knowledge_processor import KnowledgeProcessor

processor = KnowledgeProcessor()
processor.add_external_source("http://example.com/compliance-api")
processor.rebuild_index()
```

## 🤝 贡献指南

我们欢迎社区贡献！请按以下步骤参与：

1. **Fork 本仓库**
2. **创建功能分支**：`git checkout -b feature/your-feature`
3. **提交改动**：`git commit -am 'Add new feature'`
4. **推送分支**：`git push origin feature/your-feature`
5. **提交 Pull Request**

### 贡献类型
- 🐛 **Bug 修复**：报告和修复已知问题
- ✨ **功能增强**：添加新的合规规则或检查
- 📖 **文档改进**：完善说明文档和示例
- 🧪 **测试用例**：增强测试覆盖率

## 📋 许可证

本项目采用 **MIT License**。详见 [LICENSE](./LICENSE) 文件。

## 💬 反馈与支持

如有问题或建议，欢迎通过以下方式联系我们：

- **Issue 追踪**：[GitHub Issues](https://github.com/naraosaca2024-blip/legal-data-compliance-ai/issues)
- **讨论区**：[GitHub Discussions](https://github.com/naraosaca2024-blip/legal-data-compliance-ai/discussions)
- **邮件联系**：naraosaca2024@gmail.ocm

## 🎯 项目路线图

- [ ] 支持多语言（英文、日文、韩文）
- [ ] 添加合规自动化报告生成
- [ ] 集成更多行业合规标准（金融、医疗、教育）
- [ ] Web UI 界面优化
- [ ] API 文档自动生成工具

## 📄 相关资源

- [CLIENT_USAGE.md](./CLIENT_USAGE.md) - 详细客户端使用说明
- [知识库文档](./knowledge/) - 法律合规知识库
- [Langchain 文档](https://python.langchain.com/)
- [FAISS 教程](https://github.com/facebookresearch/faiss)

---

**最后更新**：2026 年 3 月
**维护者**：@naraosaca2024-blip
