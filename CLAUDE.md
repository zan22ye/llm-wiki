# CLAUDE.md

本文件为 Claude Code 在此仓库中工作提供指导。

## 这个仓库是什么

这是 LLM Wiki 模式的**模板仓库**，该模式的设计思想记录在 `llm-wiki.md` 中。

仓库本身不包含任何具体知识库。`template/` 是用户用来创建自己知识库的起点。
在这个仓库里工作，意味着维护和演进模板本身——其结构、规范和脚手架文件。

在做任何结构性改动之前，先读 `llm-wiki.md`。

## 文件结构

```
llm-wiki.md          ← 指导纲领，只读
template/
  AGENTS.md          ← 部署后的知识库 agent 的行为规范
  README.md          ← 面向人类的使用说明
  architecture.md    ← 根目录分类契约
  index.md           ← 最近访问文件索引（K=5）
  raw/               ← 部署后存放原始资料的目录
  wiki/              ← 部署后存放生成知识的目录
  templates/         ← 可复用的页面模板
    architecture-template.md
    index-template.md
    source-entry-template.md
    wiki-page-template.md
```

## 模板的核心契约

部署后的知识库中，每个目录都必须包含：

- `architecture.md` — 该目录的分类逻辑。不是页面列表。
- `index.md` — 该目录下最近访问的 top-K 文件。不是完整目录。

两者的模板都在 `template/templates/` 下。

agent 的完整行为规范在 `template/AGENTS.md`，修改 agent 行为时编辑该文件。

## 如何演进模板

**新增页面类型：** 在 `template/templates/` 创建模板文件，如有边界变化则更新
`template/templates/architecture.md`，并更新 `template/templates/index.md`。

**修改 agent 行为：** 直接编辑 `template/AGENTS.md`。

**调整目录结构：** 先更新对应的 `architecture.md`，再移动文件，再更新路径上的 `index.md`。

**位置不确定时：** 先读父目录的 `architecture.md`。没有合适边界时，提出分类变更方案，
不要随意放置文件。

## 演进方向

### 当前状态

`template/` 是 v1 骨架：目录契约 + 页面格式 + agent 行为规范。
没有 CLI、搜索引擎、可视化工具或自动化流程。

### 管理工具

随着知识库增长，`index.md` 导航会不够用，可以逐步引入：

- **搜索**：对 `wiki/` 做全文或混合检索（BM25 + 向量）。推荐选项：[qmd](https://github.com/tobi/qmd)，支持 CLI 调用和 MCP server，agent 可以直接用工具调用而非 shell。
- **摄入脚本**：自动将外部源（网页、PDF、Slack 导出）转为标准 `raw/` 文件并注册到 `sources.md`。
- **健康检查脚本**：检测孤儿页面、缺失 `architecture.md`/`index.md`、未被引用的 source 等结构问题。

### 展示工具

- **Obsidian**：知识库即 vault，图谱视图可看页面连接密度，Dataview 插件可对页面 frontmatter 做动态查询。
- **Marp**：从 wiki 页面直接生成演示文稿，适合定期知识汇报。
- **Web 展示**：将 `wiki/` 渲染为静态站点（如 Quartz、Astro）。

### 知识总结 Agent

可以在 `template/AGENTS.md` 的基础上，为不同任务派生专用 agent：

- **摄入 agent**：专注 ingest 流程，处理单个 source，输出标准页面更新。
- **合成 agent**：跨多个 wiki 页面做综合分析，结果写回 `wiki/`。
- **巡检 agent**：定期运行 lint，生成结构健康报告。
- **对话 agent**：面向用户的问答层，在 wiki 上做检索增强生成。

引入新 agent 时，在 `template/AGENTS.md` 中为其单独定义行为契约和权限边界。
