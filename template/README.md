# LLM Wiki

LLM Wiki is a file-native template foundation for building knowledge bases that are maintained by LLM agents.

It is not a specific knowledge base, application, or platform. It provides a reusable structure for individuals, organizations, projects, automation systems, and other agents to accumulate raw sources and generated knowledge over time.

## Core Idea

Most LLM document workflows retrieve from raw material at query time. LLM Wiki adds a persistent middle layer: an agent-maintained wiki that compiles, updates, cross-references, and audits knowledge as sources and questions arrive.

The knowledge base has two primary layers:

- `raw/`: immutable or source-controlled original material.
- `wiki/`: generated, synthesized, maintained knowledge derived from sources.

The directory structure is part of the knowledge base. Every directory carries local structural metadata so future agents can understand why files live where they do.

## Directory Contract

Every directory must contain:

- `architecture.md`: explains this directory's classification logic.
- `index.md`: tracks the top-K recently accessed files under this directory and descendants.

`architecture.md` is structural. It does not list pages.

`index.md` is operational. It does not try to be a full catalog.

## Initial Layout

```text
.
├── AGENTS.md
├── README.md
├── architecture.md
├── index.md
├── raw/
│   ├── architecture.md
│   ├── index.md
│   ├── sources.md
│   └── llm-wiki.md
├── templates/
│   ├── architecture.md
│   ├── index.md
│   ├── architecture-template.md
│   ├── index-template.md
│   ├── source-entry-template.md
│   └── wiki-page-template.md
└── wiki/
    ├── architecture.md
    ├── index.md
    └── overview.md
```

## How To Start

1. Add sources under `raw/`.
2. Register each source in `raw/sources.md`.
3. Ask an LLM agent to ingest the source according to `AGENTS.md`.
4. Let the agent create or update pages under `wiki/`.
5. Keep each directory's `architecture.md` and `index.md` current as the knowledge base evolves.

## Scaling

This template intentionally does not include a global catalog, search engine, CLI, or web app in v1.

As a knowledge base grows, add those only when the local `index.md` files, shell search, and editor search are no longer enough.
