import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import docx
import pdfplumber
import requests
import streamlit as st
from PIL import Image

try:
    import pytesseract
except Exception:
    pytesseract = None

KNOWLEDGE_PATH = Path("/Users/spoonlaw/code/knowledge")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-max")
MAX_KB_SNIPPET_CHARS = 28000
MAX_ATTACHMENT_CHARS = 12000

CATEGORY_KEYWORDS = {
    "合规": ["合规", "交易", "挂牌", "审计", "监管", "安全", "个人信息", "重要数据", "核心数据"],
    "入表": ["入表", "会计", "资产", "确权", "估值", "核算", "摊销", "确认"],
    "案例": ["案例", "判决", "法院", "裁判", "争议", "司法", "诉讼"],
}


@st.cache_data(show_spinner=False)
def extract_file_text(path: Path) -> str:
    try:
        suffix = path.suffix.lower()
        if suffix == ".md" or suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".docx":
            document = docx.Document(str(path))
            return "\n".join([p.text for p in document.paragraphs if p.text.strip()])
        if suffix == ".pdf":
            pages = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(text)
            return "\n".join(pages)
    except Exception:
        return ""
    return ""


@st.cache_data(show_spinner=True)
def build_kb_index(root_path: Path) -> Tuple[Dict[str, List[dict]], List[str], str]:
    categories: Dict[str, List[dict]] = {"合规": [], "入表": [], "案例": [], "三权": [], "其他": []}
    loaded_files: List[str] = []
    triquan_file = ""

    if not root_path.exists():
        return categories, loaded_files, triquan_file

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".pdf", ".docx", ".md", ".txt", ".xlsx"}:
            continue

        text = extract_file_text(path)
        if not text:
            continue

        rel_name = str(path.relative_to(root_path))
        loaded_files.append(rel_name)
        item = {"name": rel_name, "text": text}

        lowered_name = rel_name.lower()
        if "数据三权" in rel_name or "data_rights" in lowered_name:
            categories["三权"].append(item)
            triquan_file = rel_name
            continue

        if "case" in lowered_name or "案例" in rel_name or "法院" in text[:500]:
            categories["案例"].append(item)
        elif "入表" in rel_name or "会计" in text[:1200] or "资产" in text[:1200]:
            categories["入表"].append(item)
        elif "合规" in rel_name or "法规" in rel_name or "gb" in lowered_name:
            categories["合规"].append(item)
        else:
            categories["其他"].append(item)

    return categories, loaded_files, triquan_file


def classify_intent(user_text: str) -> str:
    scores = {"合规": 0, "入表": 0, "案例": 0}
    content = user_text or ""
    for category, words in CATEGORY_KEYWORDS.items():
        for word in words:
            if word in content:
                scores[category] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "合规"
    return best


def _score_text(query: str, text: str) -> int:
    if not query or not text:
        return 0
    tokens = [w for w in re.split(r"[\s，。；、,.!?：:\n]+", query) if len(w) >= 2]
    return sum(text.count(token) for token in tokens)


def retrieve_context(kb: Dict[str, List[dict]], intent: str, query: str, top_k: int = 6) -> List[dict]:
    candidates: List[dict] = []

    # 强制注入三权文件
    for item in kb.get("三权", []):
        candidates.append({"name": item["name"], "text": item["text"], "score": 10_000})

    for item in kb.get(intent, []):
        candidates.append({"name": item["name"], "text": item["text"], "score": _score_text(query, item["text"]) + 200})

    for fallback in kb.get("其他", [])[:20]:
        score = _score_text(query, fallback["text"])
        if score > 0:
            candidates.append({"name": fallback["name"], "text": fallback["text"], "score": score})

    dedup = {}
    for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
        if c["name"] not in dedup:
            dedup[c["name"]] = c

    selected = list(dedup.values())[:top_k]
    return selected


def read_uploaded_file(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    suffix = Path(uploaded_file.name).suffix.lower()
    raw = uploaded_file.getvalue()
    try:
        if suffix in {".txt", ".md"}:
            return raw.decode("utf-8", errors="ignore")
        if suffix == ".pdf":
            pages = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append(text)
            return "\n".join(pages)
        if suffix in {".png", ".jpg", ".jpeg"}:
            if pytesseract is None:
                return "图片 OCR 依赖缺失：请安装 pytesseract 和 tesseract。"
            image = Image.open(uploaded_file)
            return pytesseract.image_to_string(image, lang="chi_sim+eng")
    except Exception:
        return ""
    return ""


def build_system_prompt(triquan_name: str) -> str:
    return f"""
你是精通中国数据合规与数据资产化的资深律师。必须严格遵守以下硬性规则：
1) 任何分析开始前，必须先审阅并引用《数据三权》底稿（当前文件名：{triquan_name or '未识别到数据三权文件'}）。
2) 未完成三权判定前，不得给出挂牌、入表或交易结论。
3) 所有结论都必须附“依据条文”，格式为“根据《文件名》相关条款……”。
4) 输出必须是正式法律意见书风格，禁止口语化。
5) 若依据不足，明确写“证据不足/需补充材料”，不得臆断。

请按以下结构输出：
- 一、三权确权结论（数据资源持有权/数据加工使用权/数据产品经营权）
- 二、逻辑一：挂牌合规性审计
- 三、逻辑二：入表可行性审计
- 四、风险清单与整改建议（分高/中/低）
- 五、条文溯源清单（逐条对应结论）
""".strip()


def call_qwen(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    if not DASHSCOPE_API_KEY:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY 环境变量。")

    url = f"{DASHSCOPE_BASE_URL}/chat/completions"
    payload = {
        "model": QWEN_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=120)
    if response.status_code >= 400:
        raise RuntimeError(f"Qwen 调用失败：HTTP {response.status_code} - {response.text[:500]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"Qwen 返回格式异常: {data}") from exc


def assemble_prompt(project_info: str, intent: str, snippets: List[dict], attachment_text: str) -> str:
    context_blocks = []
    used = []
    budget = MAX_KB_SNIPPET_CHARS

    for item in snippets:
        piece = item["text"][:9000]
        if budget - len(piece) < 0:
            continue
        used.append(item["name"])
        context_blocks.append(f"【{item['name']}】\n{piece}")
        budget -= len(piece)

    attachment_block = ""
    if attachment_text.strip():
        attachment_block = f"\n\n【新增附件】\n{attachment_text[:MAX_ATTACHMENT_CHARS]}"

    context_joined = "\n\n".join(context_blocks)

    prompt = f"""
用户意图分类：{intent}

业务描述：
{project_info}

请基于下述知识库片段执行合规审计，并保证每条关键结论可回溯到具体文件：
{context_joined}
{attachment_block}

输出要求：
1) 必须先完成三权确权再进入后续分析；
2) 对“挂牌合规性、入表可行性”给出明确可执行意见；
3) 每个结论后给出引用文件名；
4) 给出需要补充的材料清单（若有）。
""".strip()
    return prompt, used


st.set_page_config(page_title="Qwen 数据合规自动化检测工具", layout="centered")

st.markdown(
    """
<style>
.main { background-color: #f6f8fb; }
.stApp { max-width: 1120px; margin: 0 auto; }
.block {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 8px 20px rgba(0,0,0,0.04);
  margin-bottom: 18px;
}
.note {
  background: #ecfeff;
  border: 1px solid #a5f3fc;
  border-radius: 12px;
  padding: 16px;
}
.stButton > button {
  background: linear-gradient(90deg, #0f766e, #0ea5e9);
  color: white;
  border: 0;
  font-weight: 600;
  border-radius: 10px;
  padding: 0.75rem 1.1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Qwen 合规中枢")
    page = st.radio("功能", ["合规审计", "AI Studio", "知识库状态"])
    kb, files, triquan_name = build_kb_index(KNOWLEDGE_PATH)
    st.caption(f"知识库文件数：{len(files)}")
    st.caption(f"模型：`{QWEN_MODEL}`")
    if triquan_name:
        st.success(f"三权底稿已锁定：{triquan_name}")
    else:
        st.error("未发现《数据三权》底稿，请检查 knowledge/4_data_rights")


if page == "合规审计":
    st.title("数据合规自动化检测工具（Qwen）")
    st.markdown(
        "<div class='note'><b>硬逻辑已启用：</b>每次审计会强制先核验《数据三权》文件，再输出挂牌/入表结论。</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='block'>", unsafe_allow_html=True)
    project_name = st.text_input("项目名称", placeholder="例如：工业设备运行数据产品 V1")
    delivery_form = st.text_input("交付形态", placeholder="API / 数据集 / 报告")
    business_desc = st.text_area("业务场景与数据字段描述", height=130)
    ownership_chain = st.text_area("来源与权属链说明", height=100)
    processing_flow = st.text_area("加工与增值过程", height=100)
    attachment = st.file_uploader("上传新增附件（PDF/TXT/MD/PNG/JPG）", type=["pdf", "txt", "md", "png", "jpg", "jpeg"])
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("生成合规法律意见"):
        if not project_name.strip() or not business_desc.strip():
            st.warning("请至少填写项目名称和业务描述。")
        else:
            with st.spinner("Qwen 正在进行三权确权与专项审计..."):
                try:
                    project_info = (
                        f"项目名称：{project_name}\n"
                        f"交付形态：{delivery_form}\n"
                        f"业务描述：{business_desc}\n"
                        f"来源与权属链：{ownership_chain}\n"
                        f"加工与增值：{processing_flow}"
                    )

                    intent = classify_intent("\n".join([project_info, business_desc, ownership_chain]))
                    snippets = retrieve_context(kb, intent, project_info, top_k=7)
                    attachment_text = read_uploaded_file(attachment)
                    user_prompt, used_files = assemble_prompt(project_info, intent, snippets, attachment_text)
                    system_prompt = build_system_prompt(triquan_name)

                    output = call_qwen(system_prompt, user_prompt)

                    st.markdown("### 审计结果")
                    st.markdown(output)
                    st.markdown("---")
                    st.markdown("**检索命中文件**")
                    if used_files:
                        for i, name in enumerate(used_files, 1):
                            st.markdown(f"{i}. `{name}`")
                    else:
                        st.caption("未命中有效片段，请检查知识库文本质量。")
                except Exception as exc:
                    st.error(f"执行失败：{exc}")

elif page == "AI Studio":
    st.header("AI Studio（Qwen Prompt 调优）")
    default_sys = build_system_prompt(triquan_name)
    sys_prompt = st.text_area("System Prompt", value=default_sys, height=220)
    user_prompt = st.text_area("User Prompt", placeholder="输入测试问题", height=140)

    if st.button("运行测试"):
        if not user_prompt.strip():
            st.warning("请输入测试问题。")
        else:
            with st.spinner("Qwen 处理中..."):
                try:
                    answer = call_qwen(sys_prompt, user_prompt, temperature=0.3)
                    st.markdown("### 输出")
                    st.markdown(answer)
                except Exception as exc:
                    st.error(f"调用失败：{exc}")

else:
    st.header("知识库状态")
    if not files:
        st.warning("未读取到知识库文件，请检查目录路径。")
    else:
        st.write(f"共载入 {len(files)} 个文件")
        for idx, name in enumerate(files, 1):
            st.markdown(f"{idx}. `{name}`")
