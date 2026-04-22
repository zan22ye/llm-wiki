#!/usr/bin/env python3
"""
ingest.py — 摄入新来源到知识库

用法：
  python scripts/ingest.py --kb <kb_root> --source <url_or_path> [--dry-run] [--mode auto|confirm]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from lib.config import Config, load_config
from lib.kb_io import (
    IndexEntry,
    SourceEntry,
    append_source,
    index_paths_to_root,
    prepend_index_entry,
    read_architecture,
    read_sources,
    write_index,
)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@dataclass
class Summary:
    title: str = ""
    type: str = "other"
    topics: list[str] = field(default_factory=list)
    key_claims: list[str] = field(default_factory=list)
    date: str = ""


SUMMARIZER_SYSTEM_PROMPT = textwrap.dedent("""
    You are a knowledge base summarizer. Given the content of a document,
    output ONLY a YAML block with these fields:

    title: (string, concise)
    type: article | paper | transcript | data | other
    topics: (list of 3-6 strings, lower-case, noun phrases)
    key_claims: (list of 2-5 strings, factual claims from the source)
    date: (YYYY-MM-DD or empty string if unknown)

    Do not include any text before or after the YAML block.
""").strip()


def _call_openai(model: str, api_key: str, system: str, user: str) -> str:
    import urllib.request, json as _json
    payload = _json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user[:12000]},  # 截断避免超 token 限制
        ],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = _json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _parse_yaml_summary(text: str) -> dict:
    """简单 YAML 解析，不依赖 PyYAML 以外的包。"""
    import yaml
    # 去掉可能的 markdown 代码块包裹
    text = re.sub(r"^```ya?ml\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text.strip())
    return yaml.safe_load(text) or {}


def generate_summary(content: str, cfg: Config) -> Summary:
    if not cfg.openai_key:
        raise RuntimeError("config.yml 中 api_keys.openai 未填写，无法调用摘要模型。")

    raw_yaml = _call_openai(cfg.summarizer, cfg.openai_key, SUMMARIZER_SYSTEM_PROMPT, content)
    data = _parse_yaml_summary(raw_yaml)

    # 解析失败时重试一次
    if not data.get("title"):
        raw_yaml = _call_openai(cfg.summarizer, cfg.openai_key, SUMMARIZER_SYSTEM_PROMPT, content)
        data = _parse_yaml_summary(raw_yaml)
        if not data.get("title"):
            raise RuntimeError(f"摘要生成失败，模型返回内容无法解析：\n{raw_yaml}")

    topics = data.get("topics", [])
    if isinstance(topics, str):
        topics = [t.strip() for t in topics.split(",")]

    key_claims = data.get("key_claims", [])
    if isinstance(key_claims, str):
        key_claims = [key_claims]

    return Summary(
        title=str(data.get("title", "untitled")),
        type=str(data.get("type", "other")),
        topics=[str(t) for t in topics],
        key_claims=[str(c) for c in key_claims],
        date=str(data.get("date", "") or ""),
    )


# ---------------------------------------------------------------------------
# 来源获取
# ---------------------------------------------------------------------------

def fetch_content(source: str) -> tuple[str, str]:
    """
    返回 (content, origin)。
    source 为 URL 时经 Jina Reader 转为 markdown；
    source 为本地路径时直接读取。
    """
    if source.startswith("http://") or source.startswith("https://"):
        jina_url = f"https://r.jina.ai/{source}"
        req = urllib.request.Request(jina_url, headers={"Accept": "text/markdown"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        return content, source
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"本地文件不存在：{source}")
        return path.read_text(encoding="utf-8"), str(path.resolve())


# ---------------------------------------------------------------------------
# 分类
# ---------------------------------------------------------------------------

MATCH_THRESHOLD = 0.3


def _tokenize(text: str) -> set[str]:
    return set(t for t in re.split(r"[\s\W]+", text.lower()) if len(t) > 1)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _get_child_dirs(dir_path: str) -> list[str]:
    return sorted(
        str(d) for d in Path(dir_path).iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def classify_source(kb_root: str, summary: Summary, cfg: Config) -> tuple[str, list[str]]:
    """
    返回 (target_raw_dir, new_dirs_to_create)。
    target_raw_dir：相对于 kb_root 的 raw/ 子目录路径。
    """
    raw_root = str(Path(kb_root) / "raw")
    current_dir = raw_root
    new_dirs: list[str] = []
    topics_tokens = _tokenize(" ".join(summary.topics))

    while True:
        children = _get_child_dirs(current_dir)
        if not children:
            break

        scores: dict[str, float] = {}
        for child in children:
            arch = read_architecture(child)
            if arch:
                scores[child] = _jaccard(topics_tokens, _tokenize(arch))

        if not scores:
            break

        best = max(scores, key=scores.get)
        if scores[best] >= MATCH_THRESHOLD:
            current_dir = best
        else:
            # 判断是否需要新建目录
            existing_sources = read_sources(kb_root)
            same_topic_count = sum(
                1 for s in existing_sources
                if _jaccard(topics_tokens, _tokenize(" ".join([]))) > MATCH_THRESHOLD
            )
            if same_topic_count >= cfg.new_dir_min_sources:
                slug = _make_slug(summary.topics[0] if summary.topics else "misc")
                new_dir = str(Path(current_dir) / slug)
                new_dirs.append(new_dir)
                current_dir = new_dir
            break

    return current_dir, new_dirs


# ---------------------------------------------------------------------------
# source-id 和文件名
# ---------------------------------------------------------------------------

def _make_slug(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:max_len]


def make_source_id(summary: Summary) -> str:
    today = date.today().isoformat()
    d = summary.date if re.match(r"\d{4}-\d{2}-\d{2}", summary.date or "") else today
    return f"source-{d}-{_make_slug(summary.title)}"


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def render_wiki_page(source_id: str, summary: Summary, raw_path: str) -> str:
    topics_list = "\n".join(f"- {t}" for t in summary.topics)
    claims_list = "\n".join(f"- {c}" for c in summary.key_claims)
    return f"""# {summary.title}

## Summary

*摄入自 `{raw_path}`*

## Key Claims

{claims_list}

## Source Basis

- `{raw_path}`

## Connections

{topics_list}

## Open Questions

## Maintenance Notes

- Source ID: `{source_id}`
- Type: `{summary.type}`
- Topics: {", ".join(summary.topics)}
"""


def render_architecture_for_new_dir(dir_name: str, topics: list[str]) -> str:
    return f"""# Architecture

## Purpose

存放与 {dir_name} 相关的原始资料。

## Classification Principle

该目录包含主题为 {", ".join(topics[:3])} 的来源文件。

## Direct Children

此目录目前无子目录。

| Child | Definition | Boundary | Excludes |
|---|---|---|---|

## Progressive Disclosure

直接在该目录下存放文件。

## Change Rules

当同类来源数量持续增长且出现明显的新子分类时，再建子目录。
"""


# ---------------------------------------------------------------------------
# 摄入计划 & 执行
# ---------------------------------------------------------------------------

@dataclass
class IngestPlan:
    source_id: str
    raw_path: str           # 绝对路径
    raw_rel: str            # 相对于 kb_root
    wiki_path: str          # 绝对路径
    wiki_rel: str
    raw_content: str
    wiki_content: str
    source_entry: SourceEntry
    index_dirs: list[str]   # 需要更新 index.md 的目录（绝对路径）
    new_dirs: list[str]     # 需要新建的目录（绝对路径）


def build_plan(kb_root: str, source: str, cfg: Config) -> IngestPlan:
    content, origin = fetch_content(source)
    summary = generate_summary(content, cfg)
    target_raw_dir, new_dirs = classify_source(kb_root, summary, cfg)

    source_id = make_source_id(summary)
    filename = _make_slug(summary.title) + ".md"

    raw_abs = str(Path(target_raw_dir) / filename)
    raw_rel = str(Path(raw_abs).relative_to(kb_root))
    wiki_abs = str(Path(kb_root) / "wiki" / f"{source_id}.md")
    wiki_rel = str(Path(wiki_abs).relative_to(kb_root))

    wiki_content = render_wiki_page(source_id, summary, raw_rel)

    added = date.today().isoformat()
    source_entry = SourceEntry(
        source_id=source_id,
        title=summary.title,
        type=summary.type,
        origin=origin,
        added=added,
        status="registered",
        raw_path=raw_rel,
        related_wiki_pages=[wiki_rel],
        notes="",
    )

    index_dirs = index_paths_to_root(kb_root, raw_abs)
    wiki_dir = str(Path(kb_root) / "wiki")
    if wiki_dir not in index_dirs:
        index_dirs.append(wiki_dir)

    return IngestPlan(
        source_id=source_id,
        raw_path=raw_abs,
        raw_rel=raw_rel,
        wiki_path=wiki_abs,
        wiki_rel=wiki_rel,
        raw_content=content,
        wiki_content=wiki_content,
        source_entry=source_entry,
        index_dirs=index_dirs,
        new_dirs=new_dirs,
    )


def print_plan(plan: IngestPlan) -> None:
    print("\n=== 摄入计划 ===")
    print(f"  来源 ID   : {plan.source_id}")
    print(f"  raw 路径  : {plan.raw_rel}")
    print(f"  wiki 页面 : {plan.wiki_rel}")
    if plan.new_dirs:
        print(f"  新建目录  : {plan.new_dirs}")
    print("  更新集合  :")
    print(f"    - raw/sources.md")
    for d in plan.index_dirs:
        print(f"    - {d}/index.md")
    print(f"    - {plan.wiki_rel}")
    print()


def execute_plan(kb_root: str, plan: IngestPlan, cfg: Config, dry_run: bool) -> dict:
    """原子性执行：先收集所有写入内容，再统一落盘。"""
    pending: dict[str, str] = {}

    # 5.1 raw 文件
    pending[plan.raw_path] = plan.raw_content

    # 5.2 sources.md（读现有内容，追加新条目）
    sources_path = str(Path(kb_root) / "raw" / "sources.md")
    existing = Path(sources_path).read_text(encoding="utf-8") if Path(sources_path).exists() else "# Sources\n\nThis file is the complete manifest of raw sources.\n"
    entry = plan.source_entry
    related = "\n".join(f"  - `{p}`" for p in entry.related_wiki_pages)
    new_block = f"\n## Source: {entry.title}\n\n- Source ID: `{entry.source_id}`\n- Type: `{entry.type}`\n- Origin: `{entry.origin}`\n- Added: `{entry.added}`\n- Status: `{entry.status}`\n- Raw path: `{entry.raw_path}`\n- Related wiki pages:\n{related}\n- Notes: {entry.notes}\n"
    pending[sources_path] = existing + new_block

    # 5.3 wiki 摘要页
    pending[plan.wiki_path] = plan.wiki_content

    # 5.4 + 5.5 index.md 更新
    today = date.today().isoformat()
    raw_entry = IndexEntry(
        path=plan.raw_rel,
        description=plan.source_entry.title,
        last_action="create",
        reason="新摄入来源",
        updated=today,
    )
    wiki_entry = IndexEntry(
        path=plan.wiki_rel,
        description=f"摘要页：{plan.source_entry.title}",
        last_action="create",
        reason="新摄入来源对应 wiki 页",
        updated=today,
    )

    for d in plan.index_dirs:
        from lib.kb_io import read_index
        idx_path = str(Path(d) / "index.md")
        existing_entries = read_index(d)
        # 判断这个目录更靠近 raw 还是 wiki
        if "wiki" in Path(d).parts:
            new_entry = wiki_entry
        else:
            new_entry = raw_entry
        new_entries = [new_entry] + [e for e in existing_entries if e.path not in (plan.raw_rel, plan.wiki_rel)]
        # 生成 index.md 内容
        from lib.kb_io import _INDEX_HEADER, _INDEX_ROW
        trimmed = new_entries[:cfg.k]
        rows = "\n".join(
            _INDEX_ROW.format(
                path=e.path,
                description=e.description,
                last_action=e.last_action,
                reason=e.reason,
                updated=e.updated,
            )
            for e in trimmed
        )
        pending[idx_path] = _INDEX_HEADER.format(k=cfg.k) + rows + "\n"

    # 5.6 新建目录
    for new_dir in plan.new_dirs:
        arch_path = str(Path(new_dir) / "architecture.md")
        idx_path = str(Path(new_dir) / "index.md")
        dir_name = Path(new_dir).name
        pending[arch_path] = render_architecture_for_new_dir(dir_name, plan.source_entry.related_wiki_pages)
        from lib.kb_io import _INDEX_HEADER
        pending[idx_path] = _INDEX_HEADER.format(k=cfg.k) + "\n"
        # 更新父目录 architecture.md（追加新子目录说明）
        parent_arch_path = str(Path(new_dir).parent / "architecture.md")
        if Path(parent_arch_path).exists() and parent_arch_path not in pending:
            pending[parent_arch_path] = Path(parent_arch_path).read_text(encoding="utf-8")
        if parent_arch_path in pending:
            pending[parent_arch_path] += f"\n<!-- 新子目录 {dir_name} 由 ingest.py 自动创建 -->\n"

    files_written = sorted(pending.keys())

    if dry_run:
        print("\n=== Dry Run — 将写入以下文件 ===")
        for p in files_written:
            rel = str(Path(p).relative_to(kb_root)) if Path(p).is_relative_to(kb_root) else p
            preview = pending[p][:80].replace("\n", "↵")
            print(f"  {rel}  [{preview}…]")
        print()
    else:
        for path, content in pending.items():
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")

    return {
        "source_id": plan.source_id,
        "target_raw": plan.raw_rel,
        "wiki_page": plan.wiki_rel,
        "new_dirs": plan.new_dirs,
        "files_written": [str(Path(p).relative_to(kb_root)) for p in files_written],
    }


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Wiki 摄入工具")
    parser.add_argument("--kb", required=True, help="知识库根目录路径")
    parser.add_argument("--source", required=True, help="URL 或本地文件路径")
    parser.add_argument("--dry-run", action="store_true", help="只打印操作计划，不写入文件")
    parser.add_argument("--mode", choices=["auto", "confirm"], help="覆盖 config.yml 中的 mode")
    args = parser.parse_args()

    cfg = load_config(args.kb)
    if args.mode:
        cfg.mode = args.mode

    print(f"正在处理来源：{args.source}")
    plan = build_plan(args.kb, args.source, cfg)
    print_plan(plan)

    if not args.dry_run and cfg.mode == "confirm":
        answer = input("确认执行？(y/n) ").strip().lower()
        if answer != "y":
            print("已取消。")
            sys.exit(0)

    result = execute_plan(args.kb, plan, cfg, dry_run=args.dry_run)

    if not args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
