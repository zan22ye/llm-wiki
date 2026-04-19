# Architecture

## Purpose

The repository root defines the top-level contract for the LLM Wiki template foundation.

## Classification Principle

The root separates human-facing instructions, agent-facing instructions, raw sources, generated knowledge, and reusable page templates.

## Direct Children

| Child | Definition | Boundary | Excludes |
|---|---|---|---|
| `raw/` | Original source material and source tracking. | Stores imported, clipped, copied, or generated source artifacts plus their manifest. | Synthesized wiki pages and reusable templates. |
| `wiki/` | Agent-generated knowledge derived from sources and queries. | Stores summaries, topic pages, entity pages, analyses, overviews, and other maintained knowledge. | Raw source files and template contracts. |
| `templates/` | Reusable markdown templates for required file types. | Stores copyable page contracts used when creating new files. | Domain knowledge and source material. |

## Progressive Disclosure

The root exposes the smallest useful split: sources, generated knowledge, and templates. Deeper directories may introduce domain-specific categories only after their boundaries are clear.

## Change Rules

Add a new root child only when it represents a durable top-level responsibility that does not belong under `raw/`, `wiki/`, or `templates/`.

Do not add root directories for temporary work, speculative categories, or one-off outputs.
