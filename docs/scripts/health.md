# health.py

## Purpose

`scripts/health.py` checks whether a knowledge base follows the LLM Wiki directory, source, wiki, and link contracts.

It implements the M1 health checks `H1` through `H10` and can optionally repair the narrow structural subset that is safe to fix mechanically.

## Dependencies

- Python 3.10+
- PyYAML, used by `scripts/lib/config.py`
- A knowledge base root containing `config.yml`

## Usage

```bash
python3 scripts/health.py --kb "Knowledge Base"
```

## Parameters

| Parameter | Required | Default | Description |
|---|---:|---|---|
| `--kb` | Yes | | Knowledge base root directory. |
| `--fix` | No | `false` | Automatically fix only `H1`, `H2`, and `H3`. |
| `--json` | No | `false` | Emit machine-readable JSON instead of human-readable text. |

## Checks

| ID | Description |
|---|---|
| `H1` | Directory missing `architecture.md`. |
| `H2` | Directory missing `index.md`. |
| `H3` | `index.md` contains more than `wiki.k` entries. |
| `H4` | `architecture.md` contains page-list style links outside allowed structure. |
| `H5` | Raw source files are missing from `raw/sources.md`. |
| `H6` | `raw/sources.md` points at missing raw files. |
| `H7` | Wiki content pages are missing `## Source Basis`. |
| `H8` | Wiki `Source Basis` references missing raw files. |
| `H9` | `raw/sources.md` related wiki links are broken. |
| `H10` | Wiki page markdown links point at missing local pages. |

## Output

With `--json`, the script writes:

```json
{
  "kb_root": "Knowledge Base",
  "checks": [
    {
      "id": "H1",
      "status": "PASS",
      "detail": []
    }
  ],
  "summary": {
    "total": 10,
    "pass": 10,
    "fail": 0,
    "warn": 0
  },
  "fixed": []
}
```

## Examples

Run a human-readable check:

```bash
python3 scripts/health.py --kb "Knowledge Base"
```

Run a JSON check for automation:

```bash
python3 scripts/health.py --kb "Knowledge Base" --json
```

Repair safe structural issues:

```bash
python3 scripts/health.py --kb "Knowledge Base" --fix
```
