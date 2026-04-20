# AGENTS.md

## Project Description

This project is a universal LLM Wiki template foundation.

It helps any person, organization, project, automation system, or agent create a file-native knowledge base that compounds over time. Raw sources live separately from generated knowledge. LLM agents maintain the wiki by ingesting sources, answering questions, updating pages, preserving provenance, and keeping directory structure understandable.

The file system is the primary runtime. Markdown files are the interface.

## Core Principles

- Keep raw sources and generated knowledge separate.
- Treat directory structure as maintained knowledge.
- Prefer explicit classification boundaries over ad hoc file placement.
- Preserve source provenance for generated claims.
- Use progressive disclosure: broad structure first, detail only in deeper directories.
- Let the knowledge base evolve from real sources and queries rather than speculative taxonomy.

## Required Directory Protocol

Every directory must contain:

- `architecture.md`
- `index.md`

When creating a directory, create both files before adding domain content to that directory.

## `architecture.md` Rules

`architecture.md` describes only the current directory's classification contract.

It must explain:

- why this directory exists;
- why this directory is classified this way;
- what direct child directories exist;
- each child directory's definition, boundary, and exclusions;
- when to add, split, merge, or remove child directories;
- how this level exposes information progressively before deeper levels add detail.

It must not contain:

- page lists;
- recently accessed files;
- source manifests;
- operation logs;
- content summaries;
- temporary notes.

Update `architecture.md` only when directory classification changes.

## `index.md` Rules

`index.md` tracks the top-K recently accessed files under the current directory and all descendants.

It must declare `K`.

Each entry should include:

- file path;
- short description;
- last action: `read`, `write`, `cite`, `move`, `create`, or `delete`;
- reason;
- updated date.

Update relevant `index.md` files after reading, writing, citing, moving, creating, or deleting a file.

Do not treat `index.md` as a complete catalog.

## Source Rules

Sources live under `raw/`.

All sources must be registered in `raw/sources.md`.

Sources may come from humans, scripts, external systems, APIs, team workflows, or other agents.

When source metadata is incomplete, register it anyway and mark its status as `incomplete-metadata`.

Do not silently rewrite original source material. If normalization is needed, preserve the original or record the transformation.

## Wiki Rules

Generated knowledge lives under `wiki/`.

Wiki pages must include source basis information so claims can be traced back to raw material.

Do not present unsupported synthesis as established knowledge.

When sources conflict, record the conflict, affected claims, and current uncertainty. Do not overwrite older conclusions without preserving what changed and why.

Stable answers to recurring or important questions should be written back into `wiki/`.

## Configuration

Read `config.yml` at the start of every session. It controls model selection, API keys, and operating mode.

Key fields:

- `mode`: `auto` executes all steps without confirmation; `confirm` presents a plan and waits for approval before writing anything.
- `models.summarizer`: small model used for summary generation.
- `models.classifier`: model used for classification decisions.
- `models.main`: model used for wiki page authoring and synthesis.
- `wiki.k`: maximum entries kept in each `index.md`.

## Ingest Protocol

Triggered when a new source file or URL is provided.

### Step 1 — Summarize

Call `models.summarizer` to produce a structured summary of the source:

```
title:       (string)
type:        article | paper | transcript | data | other
topics:      (list of strings)
key_claims:  (list of strings)
date:        (YYYY-MM-DD or empty)
```

For URLs, fetch content via Jina Reader (`GET https://r.jina.ai/{url}`) before summarizing.

### Step 2 — Classify

Using the summary, traverse the directory tree top-down:

1. Read the current directory's `architecture.md`.
2. Match the summary's `topics` and `type` against defined child boundaries.
3. If a child boundary fits, descend into it and repeat.
4. If no boundary fits, evaluate whether the source represents a new stable conceptual category:
   - If yes: propose creating a new child directory with its own `architecture.md` and `index.md`.
   - If no: place the file in the current directory.
5. Stop at the deepest fitting boundary.

Do not create directories for speculative categories. A new directory requires a clear conceptual boundary distinct from all existing ones.

### Step 3 — Mode Check

If `mode: confirm`: present the proposed file path, any new directories, and the full update set. Wait for approval before proceeding.

If `mode: auto`: proceed immediately.

### Step 4 — Place and Update

Execute in order:

1. Write the source file to the classified path under `raw/`.
2. Append an entry to `raw/sources.md`.
3. Create a wiki summary page for the source under `wiki/` using `templates/wiki-page-template.md`.
4. Update every `index.md` on the path from the root to the placed file.
5. Update `wiki/index.md`.
6. If a new directory was created: write its `architecture.md` and `index.md` before adding any files; update the parent `architecture.md` to reflect the new child boundary.

This update set is fixed. Do not skip steps or add ad hoc updates outside this list.

## Health Checks

Periodically check for:

- directories missing `architecture.md` or `index.md`;
- `index.md` files with more than K entries;
- `architecture.md` files that contain page catalogs or content summaries;
- sources missing from `raw/sources.md`;
- wiki pages missing source basis;
- actual files that contradict their directory boundaries;
- duplicate, stale, conflicting, or orphaned knowledge.

Report structural issues before making broad repairs.
