# ingest.py

## Purpose

`scripts/ingest.py` ingests a URL or local source file into an LLM Wiki knowledge base.

It fetches or reads the source, generates a structured summary, classifies the source under `raw/`, writes a generated wiki page, updates `raw/sources.md`, and refreshes relevant `index.md` files.

## Dependencies

- Python 3.10+
- PyYAML, used to parse model summary output and `config.yml`
- Network access for URL sources through Jina Reader
- `api_keys.openai` in `config.yml` for summary generation

## Usage

```bash
python3 scripts/ingest.py --kb "Knowledge Base" --source ./notes/article.md
```

## Parameters

| Parameter | Required | Default | Description |
|---|---:|---|---|
| `--kb` | Yes | | Knowledge base root directory. |
| `--source` | Yes | | URL or local file path to ingest. |
| `--dry-run` | No | `false` | Print the planned writes without writing files. |
| `--mode` | No | `config.yml` value | Override mode with `auto` or `confirm`. |

## Flow

1. URL sources are fetched as markdown through `https://r.jina.ai/{url}`; local sources are read from disk.
2. The configured summarizer model returns a YAML summary with `title`, `type`, `topics`, `key_claims`, and `date`.
3. The source is classified by comparing summary topics against `architecture.md` boundaries.
4. In `confirm` mode, the script prints the update plan and waits for `y` before writing.
5. Writes are prepared as a pending set before any file is written.
6. The script writes the raw source, appends `raw/sources.md`, creates the wiki page, and updates indexes.

## Output

On successful non-dry-run execution, the script writes JSON to stdout:

```json
{
  "source_id": "source-2026-04-22-local-source",
  "target_raw": "raw/local-source.md",
  "wiki_page": "wiki/source-2026-04-22-local-source.md",
  "new_dirs": [],
  "files_written": [
    "raw/local-source.md",
    "raw/sources.md",
    "wiki/source-2026-04-22-local-source.md"
  ]
}
```

With `--dry-run`, it prints the files that would be written and short previews of their pending contents.

## Examples

Dry-run a local file ingest:

```bash
python3 scripts/ingest.py --kb "Knowledge Base" --source ./article.md --dry-run
```

Ingest a URL in confirm mode:

```bash
python3 scripts/ingest.py --kb "Knowledge Base" --source https://example.com/article --mode confirm
```
