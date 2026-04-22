"""
lib/kb_io.py — 知识库文件读写原语
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from datetime import date
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class IndexEntry:
    path: str
    description: str
    last_action: str        # read | write | cite | move | create | delete
    reason: str
    updated: str            # YYYY-MM-DD


@dataclass
class SourceEntry:
    source_id: str
    title: str
    type: str               # article | paper | transcript | data | other
    origin: str             # URL or local path
    added: str              # YYYY-MM-DD
    status: str             # registered | incomplete-metadata
    raw_path: str
    related_wiki_pages: list[str] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------

def find_all_dirs(kb_root: str) -> list[str]:
    """递归列出 kb_root 下所有目录（含 kb_root 自身）。"""
    root = Path(kb_root)
    dirs = [str(root)]
    for d in sorted(root.rglob("*")):
        if d.is_dir() and not any(part.startswith(".") for part in d.parts):
            dirs.append(str(d))
    return dirs


# ---------------------------------------------------------------------------
# index.md
# ---------------------------------------------------------------------------

_INDEX_HEADER = """# Index

K: {k}

This file tracks the top-K recently accessed files under this directory and all descendants.

## Recently Accessed

| File | Description | Last action | Reason | Updated |
|---|---|---|---|---|
"""

_INDEX_ROW = "| `{path}` | {description} | {last_action} | {reason} | {updated} |"


def read_index(dir_path: str) -> list[IndexEntry]:
    """解析 dir_path/index.md，返回结构化条目列表。"""
    path = Path(dir_path) / "index.md"
    if not path.exists():
        return []

    entries = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| File |"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 5:
                entries.append(IndexEntry(
                    path=cols[0].strip("`"),
                    description=cols[1],
                    last_action=cols[2],
                    reason=cols[3],
                    updated=cols[4],
                ))
    return entries


def write_index(dir_path: str, entries: list[IndexEntry], k: int) -> None:
    """将条目写入 dir_path/index.md，只保留最近 k 条。"""
    trimmed = entries[:k]
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
    content = _INDEX_HEADER.format(k=k) + rows + "\n"
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    (Path(dir_path) / "index.md").write_text(content, encoding="utf-8")


def prepend_index_entry(dir_path: str, entry: IndexEntry, k: int) -> None:
    """在 index.md 最前面插入新条目，超出 k 时截断末尾。"""
    existing = read_index(dir_path)
    # 去重：同路径的旧条目移除
    existing = [e for e in existing if e.path != entry.path]
    write_index(dir_path, [entry] + existing, k)


# ---------------------------------------------------------------------------
# raw/sources.md
# ---------------------------------------------------------------------------

def read_sources(kb_root: str) -> list[SourceEntry]:
    """解析 raw/sources.md，返回所有来源条目。"""
    path = Path(kb_root) / "raw" / "sources.md"
    if not path.exists():
        return []

    entries = []
    current: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## Source:"):
            if current:
                entries.append(_dict_to_source(current))
            current = {"title": line[len("## Source:"):].strip()}
        elif line.startswith("- ") and ":" in line:
            key, _, val = line[2:].partition(":")
            current[key.strip()] = val.strip()
        elif line.startswith("  -") and current.get("_last_key") == "Related wiki pages":
            current.setdefault("related_wiki_pages", []).append(line.strip()[2:].strip())
        if line.startswith("- Related wiki pages"):
            current["_last_key"] = "Related wiki pages"
        else:
            current["_last_key"] = None

    if current:
        entries.append(_dict_to_source(current))
    return entries


def _dict_to_source(d: dict) -> SourceEntry:
    return SourceEntry(
        source_id=d.get("Source ID", "").strip("`"),
        title=d.get("title", ""),
        type=d.get("Type", "other").strip("`"),
        origin=d.get("Origin", "").strip("`"),
        added=d.get("Added", "").strip("`"),
        status=d.get("Status", "registered").strip("`"),
        raw_path=d.get("Raw path", "").strip("`"),
        related_wiki_pages=d.get("related_wiki_pages", []),
        notes=d.get("Notes", ""),
    )


def append_source(kb_root: str, entry: SourceEntry) -> None:
    """向 raw/sources.md 追加新条目。"""
    path = Path(kb_root) / "raw" / "sources.md"
    related = "\n".join(f"  - `{p}`" for p in entry.related_wiki_pages) if entry.related_wiki_pages else ""
    block = f"""
## Source: {entry.title}

- Source ID: `{entry.source_id}`
- Type: `{entry.type}`
- Origin: `{entry.origin}`
- Added: `{entry.added}`
- Status: `{entry.status}`
- Raw path: `{entry.raw_path}`
- Related wiki pages:{chr(10) + related if related else ""}
- Notes: {entry.notes}
"""
    with open(path, "a", encoding="utf-8") as f:
        f.write(block)


# ---------------------------------------------------------------------------
# architecture.md
# ---------------------------------------------------------------------------

def read_architecture(dir_path: str) -> str:
    """读取 dir_path/architecture.md 的原始内容。"""
    path = Path(dir_path) / "architecture.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# wiki pages
# ---------------------------------------------------------------------------

def list_wiki_pages(kb_root: str) -> list[str]:
    """列出 wiki/ 下所有内容页的相对路径，排除结构文件。"""
    wiki_dir = Path(kb_root) / "wiki"
    if not wiki_dir.exists():
        return []
    structural_names = {"architecture.md", "index.md"}
    return sorted(
        str(p.relative_to(kb_root))
        for p in wiki_dir.rglob("*.md")
        if p.name not in structural_names
    )


def read_wiki_page(page_path: str) -> str:
    """读取 wiki 页面的原始 markdown 内容。"""
    return Path(page_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Index paths along a file's ancestry
# ---------------------------------------------------------------------------

def index_paths_to_root(kb_root: str, target_path: str) -> list[str]:
    """返回从 kb_root 到 target_path 父目录路径上所有需要更新的目录列表。"""
    root = Path(kb_root).resolve()
    target = Path(target_path).resolve()
    dirs = []
    current = target.parent
    while True:
        dirs.append(str(current))
        if current == root:
            break
        if current == current.parent:
            break
        current = current.parent
    return dirs
