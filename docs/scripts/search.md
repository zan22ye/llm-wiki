# search.py

## Purpose

`scripts/search.py` performs keyword search over an LLM Wiki knowledge base and returns ranked JSON results for agent consumption.

It is the M1 search tool. M1 uses simple keyword scoring only; vector and hybrid search belong to M1+.

## Dependencies

- Python 3.10+
- No runtime dependency beyond the standard library and the shared `scripts/lib/` modules
- A knowledge base root containing `config.yml`, `wiki/`, and optionally `raw/`

## Usage

```bash
python3 scripts/search.py --kb "Knowledge Base" --query "attention transformer"
```

## Parameters

| Parameter | Required | Default | Description |
|---|---:|---|---|
| `--kb` | Yes | | Knowledge base root directory. |
| `--query` | Yes | | Keyword query string. |
| `--top-k` | No | `5` | Maximum number of results to return. |
| `--scope` | No | `wiki` | Search scope: `wiki`, `raw`, or `all`. |

## Output

The script writes JSON to stdout:

```json
{
  "query": "attention transformer",
  "scope": "wiki",
  "results": [
    {
      "path": "wiki/transformer.md",
      "score": 4.2,
      "matches": [
        {
          "line": 15,
          "context": "The attention mechanism allows the model to..."
        }
      ]
    }
  ]
}
```

Each result includes a knowledge-base-relative path, numeric score, and up to five line-level match snippets.

## Examples

Search generated wiki pages:

```bash
python3 scripts/search.py --kb "Knowledge Base" --query "wiki maintenance"
```

Search both raw sources and generated wiki pages:

```bash
python3 scripts/search.py --kb "Knowledge Base" --query "source basis" --scope all --top-k 10
```
