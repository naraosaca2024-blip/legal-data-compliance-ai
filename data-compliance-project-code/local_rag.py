from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import docx
import pdfplumber

try:
    import chromadb
except Exception as exc:  # pragma: no cover
    chromadb = None
    CHROMA_IMPORT_ERROR = exc
else:
    CHROMA_IMPORT_ERROR = None

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".txt"}
DEFAULT_COLLECTION = "compliance_kb"


@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: Dict[str, object]


def ensure_chroma_available() -> None:
    if chromadb is None:
        raise RuntimeError(
            "chromadb 不可用。请使用 Python 3.10-3.12 并安装 chromadb。"
            f" 原始错误: {CHROMA_IMPORT_ERROR}"
        )


def infer_category(rel_path: str) -> str:
    lowered = rel_path.lower()
    if "4_data_rights" in lowered or "数据三权" in rel_path:
        return "data_rights"
    if "2_data_asset_listing" in lowered or "入表" in rel_path:
        return "asset_listing"
    if "3_industry_cases" in lowered or "案例" in rel_path:
        return "industry_cases"
    if "1_data_product_compliance" in lowered or "挂牌" in rel_path:
        return "product_compliance"
    if "0_base_compliance" in lowered:
        return "base_compliance"
    return "other"


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in {".md", ".txt"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".docx":
            document = docx.Document(str(path))
            return "\n".join([p.text for p in document.paragraphs if p.text.strip()])
        if suffix == ".pdf":
            pages: List[str] = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    content = page.extract_text() or ""
                    if content.strip():
                        pages.append(content)
            return "\n".join(pages)
    except Exception:
        return ""
    return ""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []

    step = max(1, chunk_size - overlap)
    chunks: List[str] = []
    start = 0
    while start < len(clean):
        segment = clean[start : start + chunk_size]
        if segment:
            chunks.append(segment)
        start += step
    return chunks


def tokenize(text: str) -> List[str]:
    return [tok for tok in re.split(r"[^\w\u4e00-\u9fff]+", text.lower()) if tok]


class LocalHashEmbedding:
    """本地哈希向量，避免下载外部 embedding 模型。"""

    def __init__(self, dim: int = 512):
        self.dim = dim

    def __call__(self, input: List[str]) -> List[List[float]]:
        return [self.embed_one(text) for text in input]

    def embed_one(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for token in tokenize(text):
            h = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            hv = int.from_bytes(h, "big", signed=False)
            idx = hv % self.dim
            sign = -1.0 if (hv >> 1) & 1 else 1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def get_collection(vector_store: Path, collection_name: str = DEFAULT_COLLECTION):
    ensure_chroma_available()
    vector_store.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(vector_store))
    return client.get_or_create_collection(name=collection_name)


def iter_knowledge_files(knowledge_root: Path) -> Iterable[Path]:
    for path in knowledge_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def build_vector_store(
    knowledge_root: Path,
    vector_store: Path,
    collection_name: str = DEFAULT_COLLECTION,
    chunk_size: int = 500,
    overlap: int = 80,
    reset: bool = True,
) -> Dict[str, object]:
    collection = get_collection(vector_store, collection_name=collection_name)
    embedding_fn = LocalHashEmbedding(dim=512)
    if reset:
        existing = collection.get(include=[])
        existing_ids = existing.get("ids", [])
        if existing_ids:
            collection.delete(ids=existing_ids)

    total_files = 0
    total_chunks = 0
    category_count: Dict[str, int] = {}

    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict[str, object]] = []

    for path in iter_knowledge_files(knowledge_root):
        rel = str(path.relative_to(knowledge_root))
        text = extract_text(path)
        if not text:
            continue
        total_files += 1

        category = infer_category(rel)
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        if not chunks:
            continue

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{rel}::chunk::{idx}"
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append(
                {
                    "source": rel,
                    "category": category,
                    "chunk_index": idx,
                    "is_data_rights": 1 if category == "data_rights" else 0,
                }
            )
            total_chunks += 1
            category_count[category] = category_count.get(category, 0) + 1

        if len(ids) >= 256:
            embeds = embedding_fn(docs)
            collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
            ids, docs, metas = [], [], []

    if ids:
        embeds = embedding_fn(docs)
        collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)

    summary = {
        "knowledge_root": str(knowledge_root),
        "vector_store": str(vector_store),
        "collection": collection_name,
        "total_files": total_files,
        "total_chunks": total_chunks,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "category_count": category_count,
    }
    (vector_store / "metadata.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def merge_hits(primary: List[Dict[str, object]], forced: List[Dict[str, object]], limit: int) -> List[Dict[str, object]]:
    merged: List[Dict[str, object]] = []
    seen = set()
    for item in forced + primary:
        key = f"{item.get('id')}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged


def query_vector_store(
    vector_store: Path,
    query: str,
    collection_name: str = DEFAULT_COLLECTION,
    top_k: int = 8,
    force_data_rights: bool = True,
    preferred_categories: Optional[List[str]] = None,
) -> List[Dict[str, object]]:
    collection = get_collection(vector_store, collection_name=collection_name)
    embedding_fn = LocalHashEmbedding(dim=512)
    q_vec = embedding_fn.embed_one(query)
    q = collection.query(query_embeddings=[q_vec], n_results=top_k, include=["documents", "metadatas", "distances"])

    primary: List[Dict[str, object]] = []
    for i, chunk_id in enumerate(q.get("ids", [[]])[0]):
        meta = q.get("metadatas", [[]])[0][i]
        dist = q.get("distances", [[]])[0][i]
        primary.append(
            {
                "id": chunk_id,
                "metadata": meta,
                "distance": float(dist),
                "document": q.get("documents", [[]])[0][i],
            }
        )

    if preferred_categories:
        for category in preferred_categories:
            cq = collection.query(
                query_embeddings=[q_vec],
                where={"category": category},
                n_results=min(3, top_k),
                include=["documents", "metadatas", "distances"],
            )
            for i, chunk_id in enumerate(cq.get("ids", [[]])[0]):
                primary.append(
                    {
                        "id": chunk_id,
                        "metadata": cq.get("metadatas", [[]])[0][i],
                        "distance": float(cq.get("distances", [[]])[0][i]),
                        "document": cq.get("documents", [[]])[0][i],
                    }
                )

    forced: List[Dict[str, object]] = []
    if force_data_rights:
        data_rights_q = collection.query(
            query_embeddings=[q_vec],
            where={"is_data_rights": 1},
            n_results=min(2, top_k),
            include=["documents", "metadatas", "distances"],
        )
        for i, chunk_id in enumerate(data_rights_q.get("ids", [[]])[0]):
            forced.append(
                {
                    "id": chunk_id,
                    "metadata": data_rights_q.get("metadatas", [[]])[0][i],
                    "distance": float(data_rights_q.get("distances", [[]])[0][i]),
                    "document": data_rights_q.get("documents", [[]])[0][i],
                }
            )

    return merge_hits(primary, forced, limit=top_k)


def load_metadata(vector_store: Path) -> Dict[str, object]:
    p = vector_store / "metadata.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
