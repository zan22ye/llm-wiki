#!/usr/bin/env python3
"""
search.py — wiki 关键词搜索工具

用法：
  python scripts/search.py --kb <kb_root> --query <query> [--top-k N] [--scope wiki|raw|all]

输出：JSON to stdout
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 允许从 repo 根目录或 scripts/ 目录直接运行
sys.path.insert(0, str(Path(__file__).parent))

from lib.config import load_config
from lib.kb_io import list_wiki_pages, read_wiki_page


# ---------------------------------------------------------------------------
# Scorer 接口（M1+ 扩展点）
# ---------------------------------------------------------------------------

class BaseScorer:
    def score(self, doc_path: str, doc_content: str, query_tokens: list[str]) -> float:
        raise NotImplementedError


class KeywordScorer(BaseScorer):
    """BM25 风格的纯关键词评分，无外部依赖。"""

    def score(self, doc_path: str, doc_content: str, query_tokens: list[str]) -> float:
        if not query_tokens:
            return 0.0

        doc_lower = doc_content.lower()
        doc_tokens = _tokenize(doc_lower)

        # 基础词频得分
        tf_score: float = sum(doc_tokens.count(t) for t in query_tokens)

        # frontmatter title/topics 权重加成 ×2
        fm = _extract_frontmatter(doc_content)
        if fm:
            fm_text = (fm.get("title", "") + " " + " ".join(fm.get("topics", []))).lower()
            tf_score += sum(2.0 for t in query_tokens if t in fm_text)

        # 标题行（# 开头）权重加成 ×1.5
        title_lines = [l.lower() for l in doc_content.splitlines() if l.startswith("#")]
        for t in query_tokens:
            for tl in title_lines:
                if t in tl:
                    tf_score += 1.5

        return tf_score


# ---------------------------------------------------------------------------
# 核心搜索函数
# ---------------------------------------------------------------------------

def search(
    kb_root: str,
    query: str,
    top_k: int = 5,
    scope: str = "wiki",
    scorer: BaseScorer | None = None,
) -> dict:
    """
    在知识库中搜索 query，返回结构化结果字典。
    scorer 为 None 时使用 KeywordScorer（M1 默认）。
    """
    if scorer is None:
        scorer = KeywordScorer()

    query_tokens = _tokenize(query.lower())
    candidates = _collect_files(kb_root, scope)

    results = []
    for fpath in candidates:
        try:
            content = Path(fpath).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        score = scorer.score(fpath, content, query_tokens)
        if score <= 0:
            continue

        matches = _extract_matches(content, query_tokens)
        rel_path = str(Path(fpath).relative_to(kb_root))
        results.append({"path": rel_path, "score": round(score, 2), "matches": matches})

    results.sort(key=lambda r: r["score"], reverse=True)
    return {"query": query, "scope": scope, "results": results[:top_k]}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _collect_files(kb_root: str, scope: str) -> list[str]:
    root = Path(kb_root)
    dirs = []
    if scope in ("wiki", "all"):
        dirs.append(root / "wiki")
    if scope in ("raw", "all"):
        dirs.append(root / "raw")

    files = []
    for d in dirs:
        if d.exists():
            files.extend(str(p) for p in d.rglob("*.md"))
    return files


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[\s\W]+", text.lower()) if len(t) > 1]


def _extract_frontmatter(content: str) -> dict:
    """提取 YAML frontmatter（--- 包裹的块）。"""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    block = content[3:end].strip()
    fm: dict = {}
    for line in block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def _extract_matches(content: str, query_tokens: list[str]) -> list[dict]:
    lines = content.splitlines()
    matches = []
    seen_lines: set[int] = set()
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(t in line_lower for t in query_tokens):
            if i not in seen_lines:
                seen_lines.add(i)
                context_start = max(0, i - 1)
                context_end = min(len(lines), i + 2)
                context = " … ".join(lines[context_start:context_end]).strip()
                matches.append({"line": i + 1, "context": context[:200]})
    return matches[:5]  # 每个文件最多返回 5 处匹配


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Wiki 关键词搜索")
    parser.add_argument("--kb", required=True, help="知识库根目录路径")
    parser.add_argument("--query", required=True, help="搜索关键词")
    parser.add_argument("--top-k", type=int, default=5, help="返回结果数量（默认 5）")
    parser.add_argument(
        "--scope",
        choices=["wiki", "raw", "all"],
        default="wiki",
        help="搜索范围（默认 wiki）",
    )
    args = parser.parse_args()

    cfg = load_config(args.kb)
    result = search(
        kb_root=args.kb,
        query=args.query,
        top_k=args.top_k,
        scope=args.scope,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
