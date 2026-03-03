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
* **数据安全与隐私保护**：系统架构设计高度关注数据安全。所有的知识库预处理（`knowledge_processor.py`）及敏感合规审查均可在本地环境完成，避免核心业务数据外泄。
* **开箱即用的客户端**：提供轻量级的 `app_client.py`，方便用户直接与合规知识引擎进行交互。

## 🚀 快速开始

### 1. 环境准备

请确保您的本地环境中已安装 Python 3.8+ 及必要的依赖库。

```bash
# 克隆仓库
git clone https://github.com/naraosaca2024-blip/legal-data-compliance-ai.git
cd legal-data-compliance-ai
### 2. 知识库初始化
在启动应用前，需要对 knowledge/ 目录下的法律文本进行切分与向量化处理：

Bash
python knowledge_processor.py --init
### 3. 启动服务与客户端
启动后端合规引擎：

Bash
python app.py
启动用户交互客户端：

Bash
python app_client.py
## 🛡️ 数据安全与合规声明
本系统在软件开发层面严格遵循数据安全最佳实践。建议在向外部大语言模型（如 Claude）提交合规审查请求时，使用 compliance_tool.py 中内置的数据脱敏模块，确保查询中不包含真实的企业敏感信息或个人隐私数据。