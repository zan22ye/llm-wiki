# LLM Wiki Overview

LLM Wiki is a template foundation for building knowledge bases that are maintained by LLM agents.

The foundation has three durable ideas:

- raw sources remain separate from generated knowledge;
- every directory explains its own classification boundary through `architecture.md`;
- every directory keeps a small top-K working-set index through `index.md`.

This makes the knowledge base easier for future agents to navigate, audit, and extend without relying on hidden conversation history.

## Source Basis

- `raw/llm-wiki.md`
- `raw/sources.md`

## Current Status

This repository is at template v1. It defines structure and behavior, not a CLI, web app, global catalog, or search engine.

## Open Questions

- When should a global catalog be introduced?
- What source metadata fields become mandatory after real usage?
- Which wiki page types deserve additional templates?
