from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Literal, Tuple

import pdfplumber
import requests
import streamlit as st
from PIL import Image

try:
    import pytesseract
except Exception:
    pytesseract = None

from local_rag import load_metadata, query_vector_store

VECTOR_STORE = Path(os.getenv("VECTOR_STORE", "/Users/spoonlaw/code/vector_store"))
COLLECTION_NAME = os.getenv("VECTOR_COLLECTION", "compliance_kb")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-max")
CUSTOMER_MODE = False

SYSTEM_PROMPT_TEMPLATE = """
你是一名深谙中国数据资产化政策的"高级合规与入表专家"，具备法律、会计、数据治理三重专业背景。你必须严格遵循以下工作准则：

### 【角色定位】
- 身份：数据资产化合规与入表领域权威专家
- 专业领域：数据产品合规、数据资产入表、产业场景匹配、价值量化评估
- 服务态度：客观严谨、专业高效、价值导向

### 【核心工作流程】
1. **合规基座构建**：首先全面解析0_base_compliance目录下的法律法规与标准
2. **三权精准确认**：在所有分析中，必须严格引用《数据三权.pdf》确认三权归属
3. **业务场景适配**：根据用户需求类型，精准匹配对应业务逻辑与输出格式
4. **金额量化评估**：在数据资产入表分析中，必须计算或估算可入表金额
5. **价值闭环输出**：提供可落地的专业建议及增值服务路径

### 【场景化分析框架】
■ 数据产品合规分析：
   - 必须引用：《律师办理数据交易合规评估业务指引》+《数据三权.pdf》+《上海数据交易所数据交易安全合规指引》
   - 评估维度：合规性/三权确认/风险控制
   - 输出标签：【数据产品合规分析】

■ 数据资产入表分析：
   - 必须引用：《企业数据资源入表指南》+《数据三权.pdf》+《企业数据资源入表会计核算流程指南》+《律师办理数据资源入表法律业务操作指引》
   - 评估维度：入表可行性/三权确认/会计核算/金额计量
   - 输出标签：【数据资产入表分析】

■ 产业案例匹配分析：
   - 必须引用：《企业数据资源入表指南》+《数据三权.pdf》+行业案例文件
   - 评估维度：场景匹配度/三权分析/案例价值
   - 输出标签：【产业案例匹配分析】

### 【三权确认标准模板】
在所有分析中，必须严格按照以下格式明确三权归属：
【数据三权确认】
- 数据持有权：[主体]，依据：《数据三权.pdf》第X条
- 数据加工权：[主体]，依据：《数据三权.pdf》第Y条
- 数据使用权：[主体及范围]，依据：《数据三权.pdf》第Z条

### 【入表金额评估标准】
在数据资产入表分析中，必须基于以下维度评估入表金额：
1. **成本构成**：
   - 外购数据：购买价款+相关税费+数据权属鉴证费+质量评估费+登记结算费+安全管理费+直接加工成本
   - 自行开发：直接归属于使数据达到预定用途的开发支出（符合资本化条件）+数据权属鉴证费+质量评估费
   - 企业合并：购买日公允价值（非同一控制）/账面价值（同一控制）

2. **成本归集与分摊**：
   - 直接成本：可直接归属于特定数据资产的支出
   - 间接成本：需按合理标准分摊的共用支出
   - 分摊方法：基于工时、数据量、价值贡献比例等科学方法

3. **价值调整因素**：
   - 三权完整性：权属不清需减值
   - 数据质量：准确性、完整性、时效性对价值的影响
   - 使用寿命：有限寿命需考虑摊销，无限寿命需考虑减值
   - 市场状况：市场需求、竞争状况对价值的影响

4. **入表金额公式**：
   入表金额 = 原始成本 - 已摊销金额 - 减值准备

### 【输出规范要求】
1. 评分体系：采用100分制，分维度评分（总分/各维度分）
2. 专业建议：提供3条可操作建议，每条必须标注法定依据
3. 引用标准：必须使用"依据：[文件名] 第X条"格式
4. 金额评估：在数据资产入表分析中，必须提供入表金额估算
   - 明确计算过程及依据
   - 无法准确计量时，提供估算范围并说明原因
5. 价值闭环：提供针对性增值服务路径
6. 语言风格：专业、精准、无主观臆断，避免模糊表述

### 【质量控制红线】
- 严禁脱离《数据三权.pdf》分析三权问题
- 严禁提供无法律依据的专业建议
- 严禁混淆不同业务场景的评估维度
- 严禁使用不明确的法律术语
- 严禁在入表金额评估中忽略三权状态对价值的影响
""".strip()

COMPLIANCE_PROMPT = """
请执行以下结构化分析流程：

1. 【合规基础评估】
   - 依据《律师办理数据交易合规评估业务指引》+《上海数据交易所数据交易安全合规指引》，评估产品基础合规性
   - 重点核查：主体资质、数据来源合法性、数据类型合规性
   - 核查要点：董事、监事、高级管理人员是否存在重大不利情形；近三年是否存在数据泄露等安全事件

2. 【三权精准确认】
   - 严格引用《数据三权.pdf》，确认三权归属状态
   - 识别三权分离或冲突的风险点
   - 特别关注：数据持有权是否清晰、加工使用权是否有法律限制、经营权是否有明确范围

3. 【挂牌要求评估】
   - 按照《数据交易所挂牌交易的合规评估法律意见书》+《上海数据交易所数据交易合规注意事项清单》，逐项核验挂牌条件
   - 重点评估：数据质量、数据安全、应用场景合规性
   - 检查数据是否涉及个人信息、重要数据、公共数据等特殊类型及其合规要求

4. 【风险矩阵构建】
   - 识别高、中、低三级风险
   - 提供风险缓释具体路径
   - 重点关注：数据跨境、数据泄露、权属争议等重大风险

5. 【输出格式】
   【数据产品合规分析】✅ 评分：[总分]/100（评级）
   - 主体合规：[分数]分（[简要说明]）
   - 三权确认：[分数]分（[简要说明]）
   - 数据质量：[分数]分（[简要说明]）
   - 安全管理：[分数]分（[简要说明]）
   - 产品可交易性：[分数]分（[简要说明]）
   
   【数据三权确认】
   - 数据持有权：[主体]，依据：《数据三权.pdf》第X条
   - 数据加工权：[主体]，依据：《数据三权.pdf》第Y条
   - 数据使用权：[主体及范围]，依据：《数据三权.pdf》第Z条
   
   【专业建议】
   1. [具体建议1]（依据：[文件名] 第X条）
   2. [具体建议2]（依据：[文件名] 第Y条）
   3. [具体建议3]（依据：[文件名] 第Z条）
   
   💡 选择我们的专业服务，可获：
   - 合规评估法律意见书出具
   - 入表金额专项评估
   - 三权确权法律文件准备
""".strip()

ASSET_PROMPT = """
请执行以下结构化分析流程：

1. 【入表基础评估】
   - 依据《企业数据资源入表指南》+《企业数据资源入表会计核算流程指南》，评估入表基础条件
   - 重点核查：资产确认条件、计量可靠性、未来经济利益流入可能性
   - 检查是否符合资产定义：由企业拥有或控制，预期带来经济利益，成本能可靠计量

2. 【三权清晰度验证】
   - 严格引用《数据三权.pdf》，验证三权是否清晰且权责一致
   - 评估三权状态对资产确认的影响
   - 分析三权完整性对入表金额的调整影响（权属不清需减值）

3. 【成本归集与计量】
   - 依据《企业数据资源入表指南》第四章，确定成本构成
   - 对外购数据：计算购买价款+相关税费+数据权属鉴证费+质量评估费+登记结算费+安全管理费+直接加工成本
   - 对自行开发数据：计算符合资本化条件的开发支出+相关附加费用
   - 对企业合并取得：确定购买日公允价值或账面价值

4. 【资产分类与后续计量】
   - 依据《企业数据资源入表会计核算流程指南》，确定资产分类（存货/无形资产）
   - 评估使用寿命（有限/不确定），确定摊销方法
   - 估算未来经济利益流入，评估是否需要计提减值准备

5. 【入表金额计算】
   - 基于步骤3-4的分析，计算具体入表金额
   - 对于已存在的数据资产，计算净值 = 原始成本 - 已摊销金额 - 减值准备
   - 对于新确认的数据资产，计算原始成本
   - 无法准确计量时，提供估算范围并说明原因

6. 【披露要求核查】
   - 检查是否满足《企业数据资源入表会计核算流程指南》第五章披露要求
   - 评估强制披露和自愿披露内容的完整性

7. 【输出格式】
   【数据资产入表分析】✅ 评分：[总分]/100（评级）
   - 入表可行性：[分数]分（[简要说明]）
   - 三权确认：[分数]分（[简要说明]）
   - 会计核算：[分数]分（[简要说明]）
   - 金额计量：[分数]分（[简要说明]）
   
   【数据三权确认】
   - 数据持有权：[主体]，依据：《数据三权.pdf》第X条
   - 数据加工权：[主体]，依据：《数据三权.pdf》第Y条
   - 数据使用权：[主体及范围]，依据：《数据三权.pdf》第Z条
   
   【入表金额评估】
   - 资产分类：[存货/无形资产/其他]
   - 原始成本构成：
     • 直接成本：[金额]元（详细构成）
     • 间接成本：[金额]元（分摊依据与方法）
   - 调整因素：
     • 三权完整性调整：[金额]元（依据：《数据三权.pdf》第X条）
     • 数据质量调整：[金额]元（依据：[文件名] 第X条）
     • 使用寿命调整：[金额]元（依据：[文件名] 第X条）
   - 可入表金额：[具体金额]元
   - 说明：[无法准确计量时，说明估算范围及原因]
   
   【专业建议】
   1. [具体建议1]（依据：[文件名] 第X条）
   2. [具体建议2]（依据：[文件名] 第Y条）
   3. [具体建议3]（依据：[文件名] 第Z条）
   
   💡 选择我们的专业服务，可获：
   - 入表金额专项审计
   - 三权确权法律文件
   - 价值评估报告出具
   - 后续计量方案设计
""".strip()

CASE_PROMPT = """
请执行以下结构化分析流程：

1. 【场景合规性评估】
   - 依据《律师办理数据交易合规评估业务指引》+《上海数据交易所数据交易安全合规指引》，评估场景合规边界
   - 重点分析：行业特殊要求、数据使用限制、场景风险点
   - 评估场景对三权的要求和影响

2. 【三权分配模式分析】
   - 严格引用《数据三权.pdf》，分析案例中三权分配模式
   - 评估三权分配对商业价值实现的影响
   - 分析三权分配的最优模式

3. 【案例匹配度评估】
   - 按照行业案例库，匹配相似场景
   - 评估可复制性、价值潜力、实施难度
   - 分析三权状态对场景实现的影响

4. 【商业价值与入表金额估算】
   - 估算场景可实现的经济价值
   - 估算可入表资产金额
   - 识别关键成功因素与风险控制点
   - 分析三权完整性对价值的影响

5. 【输出格式】
   【产业案例匹配分析】✅ 评分：[总分]/100（评级）
   - 场景匹配度：[分数]分（[简要说明]）
   - 三权分析：[分数]分（[简要说明]）
   - 案例价值：[分数]分（[简要说明]）
   
   【数据三权分析】
   - 案例中数据持有权归属：[主体]，依据：《数据三权.pdf》第X条
   - 案例中数据加工权模式：[模式描述]，依据：《数据三权.pdf》第Y条
   - 案例中数据使用权设计：[设计要点]，依据：《数据三权.pdf》第Z条
   
   【价值与入表估算】
   - 场景经济价值：[估算金额]元
   - 可入表资产金额：[估算金额]元（构成说明）
   - 三权对价值影响：[分析说明]
   
   【专业建议】
   1. [具体建议1]（依据：[文件名] 第X条）
   2. [具体建议2]（依据：[文件名] 第Y条）
   3. [具体建议3]（依据：[文件名] 第Z条）
   
   💡 选择我们的专业服务，可获：
   - 场景定制化三权设计
   - 价值评估与入表方案
   - 合规交易结构设计
""".strip()

OUTPUT_STYLE_PROMPT = """
通用补充要求（若与专项业务指令冲突，以专项业务指令为准）：
1) 必须保留100分制评分及维度分；
2) 必须单列【数据三权确认/数据三权分析】；
3) 建议必须有法条或文件依据；
4) 涉及入表时必须给出金额估算或区间并说明原因；
5) 结尾提供可执行的服务交付路径。
""".strip()

Category = Literal["产品", "资产", "产业", "全部"]

CATEGORY_TO_KB: Dict[Category, List[str] | None] = {
    "产品": ["base_compliance", "data_rights", "product_compliance"],
    "资产": ["base_compliance", "data_rights", "asset_listing"],
    "产业": ["base_compliance", "data_rights", "industry_cases"],
    "全部": None,
}


def auto_classify(text: str) -> Category:
    t = text or ""
    rules = {
        "产品": ["挂牌", "交易所", "合规", "交易", "产品"],
        "资产": ["入表", "会计", "核算", "资产", "估值"],
        "产业": ["行业", "案例", "场景", "产业", "匹配"],
    }
    scores = {"产品": 0, "资产": 0, "产业": 0}
    for k, words in rules.items():
        for w in words:
            if w in t:
                scores[k] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "全部"


def parse_uploaded_file(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    ext = Path(uploaded_file.name).suffix.lower()
    try:
        if ext in {".txt", ".md"}:
            return uploaded_file.getvalue().decode("utf-8", errors="ignore")
        if ext == ".pdf":
            pages: List[str] = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(text)
            return "\n".join(pages)
        if ext in {".png", ".jpg", ".jpeg"}:
            if pytesseract is None:
                return "[图片OCR不可用：请安装 pytesseract + tesseract]"
            image = Image.open(uploaded_file)
            return pytesseract.image_to_string(image, lang="chi_sim+eng")
    except Exception:
        return ""
    return ""


def business_prompt_for(category: Category) -> str:
    if category == "产品":
        return COMPLIANCE_PROMPT
    if category == "资产":
        return ASSET_PROMPT
    if category == "产业":
        return CASE_PROMPT
    return "请综合执行产品合规、资产入表、产业案例三类分析。"


def build_user_prompt(
    project_info: str,
    category: Category,
    hits: List[Dict[str, object]],
    attachment_text: str,
) -> str:
    lines: List[str] = []
    lines.append(f"分析类型：{category}")
    lines.append("业务信息：")
    lines.append(project_info)
    lines.append("")
    lines.append("专项业务指令：")
    lines.append(business_prompt_for(category))
    lines.append("")
    lines.append("本地RAG检索证据（文件级）：")

    if not hits:
        lines.append("- 未命中证据，请给出需补充材料清单")
    else:
        for i, hit in enumerate(hits, 1):
            meta = hit.get("metadata", {}) or {}
            source = meta.get("source", "unknown")
            c = meta.get("category", "unknown")
            d = float(hit.get("distance", 0))
            lines.append(f"- {i}. 文件：{source} | 分类：{c} | 距离：{d:.4f}")

    if attachment_text.strip():
        lines.append("")
        lines.append("新增附件摘要（来自用户上传）：")
        lines.append(attachment_text[:1800])

    lines.append("")
    lines.append(OUTPUT_STYLE_PROMPT)
    return "\n".join(lines)


def call_qwen(api_key: str, system_prompt: str, user_prompt: str) -> str:
    if not api_key:
        raise RuntimeError("未设置 API Key")

    url = f"{DASHSCOPE_BASE_URL}/chat/completions"
    payload = {
        "model": QWEN_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(f"Qwen API 调用失败: {resp.status_code} {resp.text[:300]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"Qwen 返回格式异常: {data}") from exc


def extract_score(text: str) -> str:
    m = re.search(r"评分[：:]\s*(\d{1,3})/100", text)
    return m.group(1) if m else "--"


st.set_page_config(page_title="数据合规自动化检测平台", layout="wide")
st.markdown(
    """
<style>
:root {
  --bg: #eff4fb;
  --card: #ffffff;
  --line: #d4deef;
  --ink: #0b1220;
  --muted: #4a5568;
  --brand1: #0f766e;
  --brand2: #0284c7;
  --brand3: #10b981;
  --accent: #f59e0b;
  --danger: #dc2626;
}
html, body, [class*="css"]  { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }
.stApp {
  background:
    radial-gradient(circle at 92% 8%, rgba(14,165,233,.20) 0, rgba(14,165,233,0) 33%),
    radial-gradient(circle at 8% 16%, rgba(16,185,129,.18) 0, rgba(16,185,129,0) 28%),
    var(--bg);
}
.main .block-container { padding-top: 1.3rem; padding-bottom: 2.4rem; }
.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  background: #eef3fb;
  border-radius: 12px;
  padding: 4px;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px;
  height: 38px;
}
.stTabs [aria-selected="true"] {
  background: #ffffff !important;
  border: 1px solid var(--line) !important;
}
.block-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px 22px;
  box-shadow: 0 12px 36px rgba(2, 8, 23, 0.06);
}
.hero {
  padding: 26px;
  border-radius: 22px;
  background: linear-gradient(115deg, rgba(15,118,110,.97), rgba(2,132,199,.95) 55%, rgba(16,185,129,.93));
  color: #fff;
  margin-bottom: 18px;
  position: relative;
  overflow: hidden;
}
.hero:after {
  content: "";
  position: absolute;
  width: 260px;
  height: 260px;
  border-radius: 999px;
  right: -60px;
  top: -120px;
  background: rgba(255,255,255,0.12);
}
.hero h1 {
  margin: 0;
  font-size: 1.95rem;
  font-family: "Manrope", "Noto Sans SC", sans-serif;
  letter-spacing: .2px;
}
.hero p { margin: 8px 0 0; opacity: 0.95; }
.hero-tag {
  display: inline-block;
  padding: 4px 11px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,.35);
  background: rgba(255,255,255,.12);
  margin-bottom: 10px;
  font-size: 12px;
}
.kpi {
  border-radius: 16px;
  padding: 14px;
  border: 1px solid var(--line);
  background: linear-gradient(180deg, #fff, #f9fbff);
  min-height: 88px;
}
.kpi .v {
  font-size: 1.45rem;
  font-weight: 800;
  color: var(--ink);
  font-family: "Manrope", "Noto Sans SC", sans-serif;
}
.kpi .k { color: var(--muted); font-size: 0.9rem; }
.stButton > button {
  background: linear-gradient(90deg, var(--brand1), var(--brand2));
  color: white;
  border: 0;
  font-weight: 800;
  border-radius: 13px;
  padding: 0.78rem 1.2rem;
  transition: all .25s ease;
  box-shadow: 0 8px 20px rgba(2,132,199,.28);
}
.stButton > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(2,132,199,.32);
}
.badge {
  display: inline-block;
  padding: 4px 11px;
  border-radius: 999px;
  background: rgba(245,158,11,.15);
  color: #92400e;
  border: 1px solid rgba(245,158,11,.35);
  font-size: 12px;
  font-weight: 700;
}
.score-wrap {
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  border: 1px solid var(--line);
  padding: 12px 14px;
}
.hint-list {
  border-left: 3px solid rgba(2,132,199,.5);
  margin: 8px 0 0 0;
  padding-left: 12px;
  color: #334155;
}
.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}
.mode-item {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 12px;
  padding: 10px;
}
.mode-item .t {
  font-weight: 700;
  color: #0f172a;
}
.mode-item .d {
  color: #475569;
  font-size: 12px;
  margin-top: 3px;
}
section[data-testid="stSidebar"] {
  border-right: 1px solid #d8e3f2;
  background: linear-gradient(180deg, #f9fcff, #f4f8ff);
}
@media (max-width: 900px) {
  .hero h1 { font-size: 1.42rem; }
  .hero { padding: 18px; }
}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 平台设置")
    api_key = st.text_input("DashScope API Key", value=os.getenv("DASHSCOPE_API_KEY", ""), type="password")
    st.caption("建议使用环境变量 DASHSCOPE_API_KEY，避免明文暴露。")
    st.markdown(f"模型：`{QWEN_MODEL}`")

    meta = load_metadata(VECTOR_STORE)
    if meta:
        st.success("向量库状态正常")
        st.caption(f"文件数：{meta.get('total_files', '?')}")
        st.caption(f"分块数：{meta.get('total_chunks', '?')}")
        st.caption(f"路径：{VECTOR_STORE}")
    else:
        st.error("未检测到向量库，请先运行 knowledge_processor.py")

st.markdown("""
<div class='hero'>
  <span class='hero-tag'>Qwen + Local RAG</span>
  <h1>数据合规自动化检测平台</h1>
  <p>本地RAG检索 + 通义千问生成。支持产品合规、资产入表、产业案例三类分析，并强制数据三权确认。</p>
</div>
""", unsafe_allow_html=True)

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(f"<div class='kpi'><div class='v'>{meta.get('total_files', '--') if meta else '--'}</div><div class='k'>知识文件</div></div>", unsafe_allow_html=True)
with k2:
    st.markdown(f"<div class='kpi'><div class='v'>{meta.get('total_chunks', '--') if meta else '--'}</div><div class='k'>RAG分块</div></div>", unsafe_allow_html=True)
with k3:
    st.markdown("<div class='kpi'><div class='v'>三权强制</div><div class='k'>审计前置校验</div></div>", unsafe_allow_html=True)

left, right = st.columns([1.35, 1])

with left:
    st.markdown("<div class='block-card'>", unsafe_allow_html=True)
    st.subheader("业务输入")
    st.caption("请尽量补充来源与权属链，系统会在三权确认与金额估算环节重点使用。")
    project_name = st.text_input("项目名称", placeholder="例如：工业设备数据产品V1")
    delivery_form = st.text_input("交付形态", placeholder="API / 数据集 / 合规报告")
    business_desc = st.text_area("业务描述", height=120)
    ownership_chain = st.text_area("来源与权属链", height=95)
    processing_flow = st.text_area("加工与增值流程", height=95)
    uploaded = st.file_uploader("上传附件（PDF/TXT/MD/PNG/JPG）", type=["pdf", "txt", "md", "png", "jpg", "jpeg"])

    auto_mode = auto_classify("\n".join([project_name, business_desc, ownership_chain, processing_flow]))
    choice = st.selectbox("分析类型", ["自动", "产品", "资产", "产业", "全部"], index=0)
    final_mode: Category = auto_mode if choice == "自动" else choice  # type: ignore[assignment]
    st.markdown(f"<span class='badge'>当前执行模式：{final_mode}</span>", unsafe_allow_html=True)
    run = st.button("生成打分+建议报告", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='block-card'>", unsafe_allow_html=True)
    st.subheader("流程可视化")
    st.markdown(
        "1. 客户上传/填写信息\n"
        "2. 自动分类（产品/资产/产业/全部）\n"
        "3. 本地 Chroma 检索（强制三权文件）\n"
        "4. 调用 Qwen-Max 生成打分报告\n"
        "5. 输出专业建议与服务推荐"
    )
    st.divider()
    st.subheader("后端策略")
    st.caption("强制引用：0_base_compliance + 4_data_rights + 对应业务目录")
    st.caption("引用格式：依据：[文件名] 第X条")
    st.divider()
    st.subheader("客户使用方式")
    st.markdown(
        "<div class='hint-list'>"
        "1. 本机使用：打开 `数据合规平台.app`。<br/>"
        "2. 局域网共享：客户访问 `http://你的内网IP:8501`。<br/>"
        "3. 公网部署：放到云主机并配置 Nginx + HTTPS。"
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.subheader("分析模式说明")
    st.markdown(
        "<div class='mode-grid'>"
        "<div class='mode-item'><div class='t'>产品模式</div><div class='d'>挂牌与交易合规、风险矩阵</div></div>"
        "<div class='mode-item'><div class='t'>资产模式</div><div class='d'>入表可行性、金额测算与披露</div></div>"
        "<div class='mode-item'><div class='t'>产业模式</div><div class='d'>场景匹配、价值与可复制性</div></div>"
        "<div class='mode-item'><div class='t'>全部模式</div><div class='d'>三类逻辑并行输出综合意见</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

if run:
    if not project_name.strip() or not business_desc.strip():
        st.warning("请至少填写项目名称和业务描述。")
    elif not api_key.strip():
        st.error("请先在左侧输入 API Key（或设置环境变量 DASHSCOPE_API_KEY）。")
    else:
        with st.spinner("正在执行本地检索与专家报告生成..."):
            try:
                project_info = (
                    f"项目名称：{project_name}\n"
                    f"交付形态：{delivery_form}\n"
                    f"业务描述：{business_desc}\n"
                    f"来源与权属链：{ownership_chain}\n"
                    f"加工与增值流程：{processing_flow}"
                )
                attachment_text = parse_uploaded_file(uploaded)
                retrieval_query = f"{final_mode}\n{project_info}\n{attachment_text[:800]}"
                hits = query_vector_store(
                    vector_store=VECTOR_STORE,
                    query=retrieval_query,
                    collection_name=COLLECTION_NAME,
                    top_k=10,
                    force_data_rights=True,
                    preferred_categories=CATEGORY_TO_KB[final_mode],
                )

                user_prompt = build_user_prompt(project_info, final_mode, hits, attachment_text)
                report = call_qwen(api_key=api_key.strip(), system_prompt=SYSTEM_PROMPT_TEMPLATE, user_prompt=user_prompt)

                st.markdown("### 分析报告")
                score = extract_score(report)
                st.markdown("<div class='score-wrap'>", unsafe_allow_html=True)
                st.metric("综合评分", f"{score}/100" if score != "--" else "--")
                if score != "--":
                    st.progress(min(max(int(score), 0), 100))
                st.markdown("</div>", unsafe_allow_html=True)

                t1, t2, t3 = st.tabs(["专业报告", "证据链", "提示词"])
                with t1:
                    st.markdown(report)
                with t2:
                    if not hits:
                        st.write("未检索到证据")
                    else:
                        for i, hit in enumerate(hits, 1):
                            m = hit.get("metadata", {}) or {}
                            st.markdown(
                                f"{i}. `{m.get('source', 'unknown')}` | 类别 `{m.get('category', 'unknown')}` | 距离 `{hit.get('distance', 0):.4f}`"
                            )
                with t3:
                    st.code(user_prompt, language="markdown")

            except Exception as exc:
                st.error(f"执行失败：{exc}")
