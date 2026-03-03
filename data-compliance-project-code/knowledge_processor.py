from __future__ import annotations

import argparse
import json
from pathlib import Path

from local_rag import build_vector_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="本地知识库预处理并构建 Chroma 向量库")
    parser.add_argument("--knowledge", default="knowledge", help="知识库目录")
    parser.add_argument("--vector-store", default="vector_store", help="向量库存储目录")
    parser.add_argument("--collection", default="compliance_kb", help="Chroma collection 名称")
    parser.add_argument("--chunk-size", type=int, default=500, help="分块字符长度")
    parser.add_argument("--overlap", type=int, default=80, help="分块重叠字符长度")
    parser.add_argument("--no-reset", action="store_true", help="不清空旧向量")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    knowledge_root = Path(args.knowledge).resolve()
    vector_store = Path(args.vector_store).resolve()

    if not knowledge_root.exists():
        raise SystemExit(f"知识库目录不存在: {knowledge_root}")

    summary = build_vector_store(
        knowledge_root=knowledge_root,
        vector_store=vector_store,
        collection_name=args.collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        reset=not args.no_reset,
    )
    print("向量数据库构建完成:\n" + json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
