# Architecture

## Purpose

存放项目级文档，与知识库骨架（`Knowledge Base/`）分离。

## Classification Principle

文档按类型分子目录。当前只有规格文档，未来可扩展为设计文档、会议记录等。

## Direct Children

| Child | Definition | Boundary | Excludes |
|---|---|---|---|
| `spec/` | 技术规格文档，按日期命名 | 正式决策记录，含流程设计、配置规范、路线图 | 草稿、会议记录、临时笔记 |

## Progressive Disclosure

`docs/` 只暴露顶层分类。具体规格在 `spec/` 下按日期浏览。

## Change Rules

新增子目录需代表一类持久文档类型，不为单篇文档单独建目录。
