from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from health import run_checks
from ingest import Summary, build_plan, execute_plan
from lib.config import load_config
from lib.kb_io import IndexEntry, read_index, write_index
from search import search


class M1ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmpdir.name) / "Knowledge Base"
        shutil.copytree(REPO_ROOT / "Knowledge Base", self.kb)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_load_config_uses_defaults_for_missing_fields(self) -> None:
        minimal = Path(self.tmpdir.name) / "minimal-kb"
        minimal.mkdir()
        (minimal / "config.yml").write_text("models:\n  summarizer: custom-model\n", encoding="utf-8")

        cfg = load_config(str(minimal))

        self.assertEqual(cfg.mode, "auto")
        self.assertEqual(cfg.summarizer, "custom-model")
        self.assertEqual(cfg.classifier, "gpt-4o-mini")
        self.assertEqual(cfg.k, 5)
        self.assertEqual(cfg.new_dir_min_sources, 3)
        self.assertEqual(cfg.openai_key, "")

    def test_write_index_truncates_to_k_entries(self) -> None:
        entries = [
            IndexEntry(f"file-{i}.md", f"desc {i}", "read", "test", "2026-04-22")
            for i in range(4)
        ]

        write_index(str(self.kb), entries, k=2)

        parsed = read_index(str(self.kb))
        self.assertEqual([entry.path for entry in parsed], ["file-0.md", "file-1.md"])

    def test_search_returns_ranked_json_ready_results(self) -> None:
        result = search(str(self.kb), "wiki", top_k=2, scope="all")

        json.dumps(result)
        self.assertEqual(result["query"], "wiki")
        self.assertLessEqual(len(result["results"]), 2)
        self.assertGreater(result["results"][0]["score"], 0)
        self.assertIn("path", result["results"][0])

    def test_health_standard_skeleton_passes_all_checks(self) -> None:
        shutil.copy2(REPO_ROOT / "llm-wiki.md", self.kb / "raw" / "llm-wiki.md")

        checks = run_checks(str(self.kb), k=5)

        failures = {check.id: check.detail for check in checks if check.status != "PASS"}
        self.assertEqual(failures, {})

    def test_ingest_dry_run_does_not_write_files(self) -> None:
        source = Path(self.tmpdir.name) / "source.md"
        source.write_text("# Local Source\n\nA note about durable wiki tooling.", encoding="utf-8")
        cfg = load_config(str(self.kb))

        with patch("ingest.generate_summary") as generate_summary:
            generate_summary.return_value = Summary(
                title="Local Source",
                type="article",
                topics=["wiki tooling"],
                key_claims=["Local notes can be ingested."],
                date="2026-04-22",
            )
            plan = build_plan(str(self.kb), str(source), cfg)
            with redirect_stdout(StringIO()):
                result = execute_plan(str(self.kb), plan, cfg, dry_run=True)

        self.assertFalse((self.kb / result["target_raw"]).exists())
        self.assertFalse((self.kb / result["wiki_page"]).exists())


if __name__ == "__main__":
    unittest.main()
