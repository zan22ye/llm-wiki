#!/usr/bin/env python3
"""
health.py — 知识库结构健康检查

用法：
  python scripts/health.py --kb <kb_root> [--fix] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.config import load_config
from lib.kb_io import (
    find_all_dirs,
    read_architecture,
    read_index,
    read_sources,
    list_wiki_pages,
)


# ---------------------------------------------------------------------------
# 检查结果
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    id: str
    status: str         # PASS | FAIL | WARN
    detail: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 检测项实现
# ---------------------------------------------------------------------------

def check_h1(kb_root: str) -> CheckResult:
    """H1: 目录缺失 architecture.md"""
    missing = []
    for d in find_all_dirs(kb_root):
        if not (Path(d) / "architecture.md").exists():
            missing.append(str(Path(d).relative_to(kb_root) or "."))
    return CheckResult("H1", "FAIL" if missing else "PASS", missing)


def check_h2(kb_root: str) -> CheckResult:
    """H2: 目录缺失 index.md"""
    missing = []
    for d in find_all_dirs(kb_root):
        if not (Path(d) / "index.md").exists():
            missing.append(str(Path(d).relative_to(kb_root) or "."))
    return CheckResult("H2", "FAIL" if missing else "PASS", missing)


def check_h3(kb_root: str, k: int) -> CheckResult:
    """H3: index.md 条目数超过 K"""
    over = []
    for d in find_all_dirs(kb_root):
        idx_path = Path(d) / "index.md"
        if idx_path.exists():
            entries = read_index(d)
            if len(entries) > k:
                rel = str(Path(d).relative_to(kb_root) or ".")
                over.append(f"{rel}/index.md ({len(entries)} > {k})")
    return CheckResult("H3", "FAIL" if over else "PASS", over)


def check_h4(kb_root: str) -> CheckResult:
    """H4: architecture.md 中包含页面列表（非表格段落中出现 markdown 链接）"""
    violations = []
    for d in find_all_dirs(kb_root):
        arch_path = Path(d) / "architecture.md"
        if not arch_path.exists():
            continue
        content = arch_path.read_text(encoding="utf-8")
        in_table = False
        for line in content.splitlines():
            if line.startswith("|"):
                in_table = True
            elif line.strip() == "":
                in_table = False
            if not in_table and re.search(r"\[.+\]\(.+\)", line):
                rel = str(arch_path.relative_to(kb_root))
                violations.append(rel)
                break
    return CheckResult("H4", "FAIL" if violations else "PASS", violations)


def check_h5(kb_root: str) -> CheckResult:
    """H5: raw/ 下存在 .md 文件但未在 sources.md 注册"""
    raw_dir = Path(kb_root) / "raw"
    if not raw_dir.exists():
        return CheckResult("H5", "PASS", [])

    sources = read_sources(kb_root)
    registered = {s.raw_path for s in sources}

    unregistered = []
    for p in raw_dir.rglob("*.md"):
        rel = str(p.relative_to(kb_root))
        if rel in ("raw/sources.md", "raw/architecture.md", "raw/index.md"):
            continue
        if rel not in registered:
            unregistered.append(rel)
    return CheckResult("H5", "FAIL" if unregistered else "PASS", sorted(unregistered))


def check_h6(kb_root: str) -> CheckResult:
    """H6: sources.md 中 raw_path 指向不存在的文件"""
    sources = read_sources(kb_root)
    broken = []
    for s in sources:
        if s.raw_path and not (Path(kb_root) / s.raw_path).exists():
            broken.append(s.raw_path)
    return CheckResult("H6", "FAIL" if broken else "PASS", broken)


def check_h7(kb_root: str) -> CheckResult:
    """H7: wiki 页面缺少 '## Source Basis' 章节"""
    missing = []
    for rel_path in list_wiki_pages(kb_root):
        full = Path(kb_root) / rel_path
        content = full.read_text(encoding="utf-8")
        if "## Source Basis" not in content:
            missing.append(rel_path)
    return CheckResult("H7", "FAIL" if missing else "PASS", missing)


def check_h8(kb_root: str) -> CheckResult:
    """H8: wiki 页面 Source Basis 中引用的 raw 文件不存在"""
    broken = []
    for rel_path in list_wiki_pages(kb_root):
        full = Path(kb_root) / rel_path
        content = full.read_text(encoding="utf-8")
        in_source_basis = False
        for line in content.splitlines():
            if line.startswith("## Source Basis"):
                in_source_basis = True
                continue
            if line.startswith("## ") and in_source_basis:
                break
            if in_source_basis:
                m = re.search(r"`(raw/[^`]+)`", line)
                if m:
                    raw_ref = m.group(1)
                    if not (Path(kb_root) / raw_ref).exists():
                        broken.append(f"{rel_path} → {raw_ref}")
    return CheckResult("H8", "FAIL" if broken else "PASS", broken)


def check_h9(kb_root: str) -> CheckResult:
    """H9: sources.md 中 Related wiki pages 链接失效"""
    sources = read_sources(kb_root)
    broken = []
    for s in sources:
        for wp in s.related_wiki_pages:
            wp_clean = wp.strip("`")
            if not (Path(kb_root) / wp_clean).exists():
                broken.append(f"{s.source_id} → {wp_clean}")
    return CheckResult("H9", "FAIL" if broken else "PASS", broken)


def check_h10(kb_root: str) -> CheckResult:
    """H10: wiki 页面内部链接指向不存在的页面"""
    broken = []
    for rel_path in list_wiki_pages(kb_root):
        full = Path(kb_root) / rel_path
        content = full.read_text(encoding="utf-8")
        for m in re.finditer(r"\[.*?\]\(([^)]+\.md)\)", content):
            link = m.group(1)
            if link.startswith("http"):
                continue
            target = (full.parent / link).resolve()
            if not target.exists():
                broken.append(f"{rel_path} → {link}")
    return CheckResult("H10", "FAIL" if broken else "PASS", broken)


# ---------------------------------------------------------------------------
# 自动修复
# ---------------------------------------------------------------------------

def fix_issues(kb_root: str, checks: list[CheckResult], cfg_k: int) -> list[str]:
    """修复 H1、H2、H3。返回被修复的文件列表。"""
    fixed = []
    templates_dir = Path(kb_root) / "templates"
    arch_template = (templates_dir / "architecture-template.md").read_text(encoding="utf-8") \
        if (templates_dir / "architecture-template.md").exists() else "# Architecture\n"
    idx_template = (templates_dir / "index-template.md").read_text(encoding="utf-8") \
        if (templates_dir / "index-template.md").exists() else f"# Index\n\nK: {cfg_k}\n\n## Recently Accessed\n\n| File | Description | Last action | Reason | Updated |\n|---|---|---|---|---|\n"

    for check in checks:
        if check.id == "H1" and check.status == "FAIL":
            for rel in check.detail:
                p = Path(kb_root) / rel / "architecture.md"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(arch_template, encoding="utf-8")
                fixed.append(str(p.relative_to(kb_root)))

        if check.id == "H2" and check.status == "FAIL":
            for rel in check.detail:
                p = Path(kb_root) / rel / "index.md"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(idx_template.replace("{k}", str(cfg_k)), encoding="utf-8")
                fixed.append(str(p.relative_to(kb_root)))

        if check.id == "H3" and check.status == "FAIL":
            for detail in check.detail:
                rel = detail.split(" ")[0]  # "dir/index.md (N > K)"
                dir_path = str((Path(kb_root) / rel).parent)
                entries = read_index(dir_path)
                from lib.kb_io import write_index
                write_index(dir_path, entries, cfg_k)
                fixed.append(rel)

    return fixed


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def run_checks(kb_root: str, k: int) -> list[CheckResult]:
    return [
        check_h1(kb_root),
        check_h2(kb_root),
        check_h3(kb_root, k),
        check_h4(kb_root),
        check_h5(kb_root),
        check_h6(kb_root),
        check_h7(kb_root),
        check_h8(kb_root),
        check_h9(kb_root),
        check_h10(kb_root),
    ]


def print_human(kb_root: str, checks: list[CheckResult], fixed: list[str]) -> None:
    print(f"\nHealth check: {kb_root}\n")
    for c in checks:
        icon = "PASS" if c.status == "PASS" else "FAIL"
        print(f"[{icon}] {c.id}: ", end="")
        desc = {
            "H1": "architecture.md 缺失",
            "H2": "index.md 缺失",
            "H3": "index.md 条目超过 K",
            "H4": "architecture.md 含页面列表",
            "H5": "raw 文件未注册到 sources.md",
            "H6": "sources.md 中 raw_path 失效",
            "H7": "wiki 页面缺少 Source Basis",
            "H8": "Source Basis 引用不存在的 raw 文件",
            "H9": "sources.md 中 wiki 链接失效",
            "H10": "wiki 内部链接失效",
        }.get(c.id, c.id)
        print(desc)
        for d in c.detail:
            print(f"       - {d}")

    fail_count = sum(1 for c in checks if c.status == "FAIL")
    print(f"\nSummary: {fail_count} issue(s) found")
    if fixed:
        print(f"Auto-fixed: {len(fixed)} file(s)")
        for f in fixed:
            print(f"  - {f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Wiki 健康检查")
    parser.add_argument("--kb", required=True, help="知识库根目录路径")
    parser.add_argument("--fix", action="store_true", help="自动修复 H1/H2/H3")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 输出")
    args = parser.parse_args()

    cfg = load_config(args.kb)
    checks = run_checks(args.kb, cfg.k)

    fixed = []
    if args.fix:
        fixed = fix_issues(args.kb, checks, cfg.k)
        if fixed:
            checks = run_checks(args.kb, cfg.k)

    if args.as_json:
        out = {
            "kb_root": args.kb,
            "checks": [
                {"id": c.id, "status": c.status, "detail": c.detail}
                for c in checks
            ],
            "summary": {
                "total": len(checks),
                "pass": sum(1 for c in checks if c.status == "PASS"),
                "fail": sum(1 for c in checks if c.status == "FAIL"),
                "warn": sum(1 for c in checks if c.status == "WARN"),
            },
            "fixed": fixed,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_human(args.kb, checks, fixed)


if __name__ == "__main__":
    main()
