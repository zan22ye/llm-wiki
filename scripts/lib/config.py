"""
lib/config.py — 加载 Knowledge Base/config.yml
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULTS = {
    "mode": "auto",
    "models": {
        "summarizer": "gpt-4o-mini",
        "classifier": "gpt-4o-mini",
        "main": "claude-sonnet-4-6",
    },
    "api_keys": {
        "openai": "",
        "anthropic": "",
    },
    "wiki": {
        "k": 5,
        "new_dir_min_sources": 3,
    },
}


@dataclass
class Config:
    mode: str = "auto"
    summarizer: str = "gpt-4o-mini"
    classifier: str = "gpt-4o-mini"
    main: str = "claude-sonnet-4-6"
    openai_key: str = ""
    anthropic_key: str = ""
    k: int = 5
    new_dir_min_sources: int = 3


def load_config(kb_root: str) -> Config:
    """从 kb_root/config.yml 加载配置，缺失字段使用默认值。"""
    path = Path(kb_root) / "config.yml"

    raw: dict = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    def get(keys: list[str], default):
        node = raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node if node is not None else default

    return Config(
        mode=get(["mode"], DEFAULTS["mode"]),
        summarizer=get(["models", "summarizer"], DEFAULTS["models"]["summarizer"]),
        classifier=get(["models", "classifier"], DEFAULTS["models"]["classifier"]),
        main=get(["models", "main"], DEFAULTS["models"]["main"]),
        openai_key=get(["api_keys", "openai"], ""),
        anthropic_key=get(["api_keys", "anthropic"], ""),
        k=get(["wiki", "k"], DEFAULTS["wiki"]["k"]),
        new_dir_min_sources=get(
            ["wiki", "new_dir_min_sources"],
            DEFAULTS["wiki"]["new_dir_min_sources"],
        ),
    )
