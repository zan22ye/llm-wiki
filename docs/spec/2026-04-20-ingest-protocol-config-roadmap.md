# LLM Wiki — 技术规格

本文档汇总 LLM Wiki 的完整技术设计，作为后续开发（工具层、agent 层）的参考基准。

---

## 一、项目定位

文件原生的知识库基座。不是应用，不是平台。`Knowledge Base/` 是可复制的骨架，
用户在此基础上构建个性化知识库，LLM agent 负责维护。

设计纲领见 `llm-wiki.md`。

---

## 二、目录契约

每个目录必须包含：

| 文件 | 职责 | 更新时机 |
|---|---|---|
| `architecture.md` | 该目录的分类逻辑，不列页面 | 仅当目录结构变动时 |
| `index.md` | top-K 最近访问文件，不是全量目录 | 每次文件操作后 |

K 值由 `config.yml` 中 `wiki.k` 控制，默认 5。

---

## 三、摄入流程

### 3.1 触发条件

用户提供新文件路径或 URL。

### 3.2 步骤

```
Step 1  摘要生成
        调用 models.summarizer
        URL 来源先经 Jina Reader 转为 markdown：GET https://r.jina.ai/{url}
        输出结构化摘要（见 3.3）

Step 2  逐层分类
        从根目录开始，读 architecture.md
        将摘要的 topics / type 与子目录边界匹配
        匹配则下探，重复，直到叶节点
        不匹配则判断是否构成新概念边界：
          是 → 提议新建子目录
          否 → 放在当前目录

Step 3  模式判断
        mode=confirm → 展示：目标路径、新建目录（如有）、完整更新集，等待确认
        mode=auto    → 直接执行

Step 4  执行（固定顺序）
        1. 写入源文件到 raw/ 对应路径
        2. 追加条目到 raw/sources.md
        3. 在 wiki/ 下为该来源新建摘要页
        4. 更新从根到目标文件路径上的所有 index.md
        5. 更新 wiki/index.md
        6. 如有新建目录：先写 architecture.md 和 index.md，再更新父目录 architecture.md
```

### 3.3 摘要格式

```yaml
title:       ""
type:        article | paper | transcript | data | other
topics:      []
key_claims:  []
date:        ""   # YYYY-MM-DD，无则留空
```

### 3.4 固定更新集

每次摄入必更新，不多不少：

- `raw/sources.md`
- 文件路径上所有 `index.md`（含根目录）
- `wiki/{source-id}.md`（新建）
- `wiki/index.md`
- 如有新建目录：新目录的 `architecture.md` + `index.md`，父目录的 `architecture.md`

> M1 搜索工具上线后，新增：与该来源 topics 重叠的现有 wiki 页面。

---

## 四、配置文件

路径：`config.yml`（知识库根目录）

```yaml
mode: auto | confirm

models:
  summarizer: gpt-4o-mini
  classifier: gpt-4o-mini
  main: claude-sonnet-4-6

api_keys:
  openai: ""
  anthropic: ""

wiki:
  k: 5
```

---

## 五、Agent 工具列表

| 工具 | 用途 | M0 必须 |
|---|---|---|
| read_file | 读取 md / yml 文件 | ✓ |
| write_file | 写入 / 创建文件 | ✓ |
| list_directory | 遍历目录结构 | ✓ |
| create_directory | 新建目录 | ✓ |
| fetch_url | Jina Reader 拉取网页 markdown | ✓ |
| call_llm | 调小模型生成摘要和分类判断 | ✓ |
| search_wiki | 搜索 wiki/ 下的页面 | M1 |

---

## 六、路线图

| 阶段 | 目标 | 关键交付 |
|---|---|---|
| M0 骨架 ✓ | 结构稳定，可作为起点 | 目录契约、页面模板、AGENTS.md、config.yml |
| M1 工具层 | Agent 可高效操作知识库 | 关键词搜索脚本、Jina 摄入脚本、健康检查脚本 |
| M1+ 向量搜索 | 语义检索能力 | wiki/ 向量索引、embedding 模型集成 |
| M1++ 知识图谱 | 关系导航与推理 | 页面关系图谱、图查询接口 |
| M2 展示层 | 知识库内容可供人类消费 | Obsidian 配置、Marp 模板、web 渲染方案 |
| M3 Agent 层 | 专用 agent 体系 | 摄入 / 巡检 / 合成 / 对话 agent，各有独立契约 |
| M4 个性化框架 | 快速 fork 出个性化版本 | 场景扩展指南、自定义 agent 模板、配置层抽象 |

---

## 七、已决问题

| 问题 | 决策 |
|---|---|
| `auto` 模式下小模型置信度低时 | 直接执行，不降级 |
| 新建目录是否需要数量阈值 | 需要，由 `config.yml` 中 `wiki.new_dir_min_sources` 控制 |
| 搜索演进路径 | 关键词 → 向量 → 知识图谱，分三阶段交付 |
