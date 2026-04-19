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

## Classification Workflow

Before creating a file:

1. Read the parent directory's `architecture.md`.
2. Decide whether the file belongs within an existing boundary.
3. If no boundary fits, propose a classification change.
4. If the change is accepted, update the parent `architecture.md`.
5. Create the new directory with `architecture.md` and `index.md` if needed.
6. Add the file.
7. Update relevant `index.md` files.

If the classification is unclear, ask for a decision or present two to three options. Do not place files arbitrarily.

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
