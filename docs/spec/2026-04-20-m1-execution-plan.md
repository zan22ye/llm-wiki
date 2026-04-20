# LLM Wiki M1 阶段执行计划

---

## 一、整体定位

M0 交付了一个纯文件结构骨架：目录契约、页面模板、AGENTS.md 行为规范，以及 `config.yml` 配置文件。这些文件指导 LLM agent 如何操作知识库，但所有操作都依赖于 agent 自身调用 LLM 完成，没有任何脚本工具。

M1 的核心目标是为 agent 提供三个独立可调用的外部工具，让 agent 能够把耗时的结构化操作外包给可靠的脚本，而不是每次都通过 prompt 临时驱动 LLM 完成。

三个工具的定位：
- `search.py`：解决 wiki/ 增长后 index.md 导航不够用的问题
- `ingest.py`：将"Jina 抓取 + 摘要生成 + 四步写入"封装为单命令
- `health.py`：将 AGENTS.md 中的健康检查清单变成可执行的诊断报告

---

## 二、文件规划

### 2.1 新增文件

```
llm-wiki/
  scripts/
    search.py              ← 关键词搜索工具
    ingest.py              ← Jina 摄入工具
    health.py              ← 结构健康检查工具
    lib/
      config.py            ← 读取 config.yml 的共享模块
      kb_io.py             ← 知识库文件读写的共享模块
  docs/
    scripts/
      search.md            ← search.py 的接口文档
      ingest.md            ← ingest.py 的接口文档
      health.md            ← health.py 的接口文档
```

所有脚本放在 `scripts/` 目录，不侵入 `Knowledge Base/` 模板目录。`Knowledge Base/` 代表用户复制的骨架，脚本是作用于骨架之上的工具，二者保持分离。

`lib/` 是内部共享库，不作为公开接口暴露，只供三个脚本导入。

### 2.2 不需要修改的已有文件

以下文件在 M1 阶段不需要变更：
- `Knowledge Base/AGENTS.md`：M1 完成后追加 `search_wiki` 工具说明即可，M1 开发期间保持不动
- `Knowledge Base/config.yml`：已包含所有 M1 所需字段
- `Knowledge Base/templates/`：模板不变
- `Knowledge Base/raw/sources.md`：由 `ingest.py` 写入，不提前修改

---

## 三、子任务拆解

以下 7 个子任务按依赖顺序排列。

---

### T1：实现 `lib/config.py`

**输入**
- `Knowledge Base/config.yml`

**接口**

```python
class Config:
    mode: str                  # "auto" | "confirm"
    summarizer: str
    classifier: str
    main: str
    openai_key: str
    anthropic_key: str
    k: int
    new_dir_min_sources: int

def load_config(kb_root: str) -> Config:
    """从 kb_root/config.yml 加载配置，缺失字段使用默认值。"""
```

**验收标准**
- 字段缺失时使用合理默认值（k=5, new_dir_min_sources=3, mode="auto"）
- api_keys 为空时不报错
- 有单元测试覆盖"完整配置"和"缺失字段"两种情况

---

### T2：实现 `lib/kb_io.py`

**接口**

```python
def find_all_dirs(kb_root: str) -> list[str]
def read_index(dir_path: str) -> list[IndexEntry]
def write_index(dir_path: str, entries: list[IndexEntry], k: int) -> None
def read_sources(kb_root: str) -> list[SourceEntry]
def append_source(kb_root: str, entry: SourceEntry) -> None
def read_architecture(dir_path: str) -> str
def list_wiki_pages(kb_root: str) -> list[str]
def read_wiki_page(page_path: str) -> str
```

**验收标准**
- 所有路径操作使用 `pathlib.Path`
- `read_index` / `write_index` 正确处理 K 值截断
- 有单元测试覆盖空 index.md、满 K 的 index.md 等边界情况

---

### T3：实现 `scripts/search.py`

**依赖** T1、T2

**调用方式**

```
search.py --kb <kb_root> --query <query_string> [--top-k N] [--scope wiki|raw|all]
```

**评分逻辑**

```python
def score_document(query_tokens, doc_content, doc_path) -> float:
    # 基础词频得分
    tf_score = sum(doc_tokens.count(t) for t in query_tokens)
    # frontmatter title/topics 权重加成 ×2
    # 标题行（# 开头）权重加成 ×1.5
    return tf_score
```

不引入外部依赖，纯 Python 实现。对百级页面搜索耗时低于 200ms。

**输出（JSON to stdout）**

```json
{
  "query": "attention mechanism",
  "scope": "wiki",
  "results": [
    {
      "path": "wiki/transformer.md",
      "score": 4.2,
      "matches": [
        { "line": 15, "context": "The attention mechanism allows the model to..." }
      ]
    }
  ]
}
```

**M1+ 扩展点**：评分函数设计为可替换接口，M1+ 传入 `VectorScorer` 或 `HybridScorer` 即可，无需改动框架代码。

---

### T4：实现 `scripts/ingest.py`

**依赖** T1、T2

**调用方式**

```
ingest.py --kb <kb_root> --source <url_or_local_path> [--dry-run] [--mode auto|confirm]
```

`--mode` 优先级高于 config.yml。

**流程**

```
Step 1  获取内容
        URL → GET https://r.jina.ai/{url}（超时 30s）
        本地路径 → 直接读取

Step 2  生成摘要
        调用 config.models.summarizer（OpenAI API）
        输出 YAML，解析失败时重试一次

Step 3  逐层分类
        从 kb_root 读 architecture.md，Jaccard 相似度匹配 summary.topics
        得分 > 0.3 则下探子目录，否则判断是否触发新建目录（new_dir_min_sources 阈值）

Step 4  确认（confirm 模式）
        打印：目标路径、新建目录（如有）、完整更新集
        等待 stdin "y" / "n"

Step 5  执行（固定顺序，与 AGENTS.md 一致，原子性写入）
        5.1 写入 raw/{target_path}
        5.2 追加 raw/sources.md
        5.3 创建 wiki/{source-id}.md
        5.4 更新路径上所有 index.md
        5.5 更新 wiki/index.md
        5.6 如有新建目录：先写 architecture.md + index.md，再更新父目录 architecture.md
```

**摘要 Prompt 规范**

```
You are a knowledge base summarizer. Given the content of a document,
output ONLY a YAML block with these fields:

title: (string, concise)
type: article | paper | transcript | data | other
topics: (list of 3-6 strings, lower-case, noun phrases)
key_claims: (list of 2-5 strings, factual claims from the source)
date: (YYYY-MM-DD or empty string if unknown)

Do not include any text before or after the YAML block.
```

**source-id 规则**：`source-{YYYY-MM-DD}-{slug}`，slug 为 title 转小写取前 40 字符，空格和标点替换为 `-`。

**原子性**：先将所有待写内容收集到 `pending_writes: dict[str, str]`，全部生成成功后再统一写入文件系统。

**验收标准**
- 对真实 URL 能成功完成全流程
- `--dry-run` 不写任何文件
- 中途失败不留下半成品

---

### T5：实现 `scripts/health.py`

**依赖** T1、T2

**调用方式**

```
health.py --kb <kb_root> [--fix] [--json]
```

**检测项**

| ID | 类型 | 检测内容 |
|---|---|---|
| H1 | 结构 | 目录缺失 architecture.md |
| H2 | 结构 | 目录缺失 index.md |
| H3 | 结构 | index.md 条目数超过 K |
| H4 | 结构 | architecture.md 中包含页面列表 |
| H5 | 来源 | raw/ 下文件未在 sources.md 注册 |
| H6 | 来源 | sources.md 中 raw_path 指向不存在的文件 |
| H7 | Wiki | wiki 页面缺少 "## Source Basis" 章节 |
| H8 | Wiki | Source Basis 引用的 raw 文件不存在 |
| H9 | 交叉引用 | sources.md 中 wiki 页面链接失效 |
| H10 | 交叉引用 | wiki 页面内部链接指向不存在的页面 |

**--fix 自动修复范围**：仅 H1、H2（创建模板文件）、H3（截断 index.md）。H5–H10 不自动修复。

**输出（--json）**

```json
{
  "kb_root": "...",
  "checks": [
    { "id": "H1", "status": "PASS", "detail": [] },
    { "id": "H2", "status": "FAIL", "detail": ["raw/papers/"] }
  ],
  "summary": { "total": 10, "pass": 9, "fail": 1, "warn": 0 }
}
```

---

### T6：补充脚本接口文档

**依赖** T3、T4、T5

输出 `docs/scripts/search.md`、`ingest.md`、`health.md`，各含：用途、依赖、调用方式、参数、输出格式、使用示例。

---

### T7：更新 AGENTS.md，注册 search_wiki 工具

**依赖** T3

在 `Knowledge Base/AGENTS.md` 中追加 search_wiki 工具说明，并在 Ingest Protocol Step 4 后注明 M1+ 的交叉更新钩子。

---

## 四、依赖关系图

```
T1 (config.py) ──┐
                 ├──► T3 (search.py) ──► T6 (docs)
T2 (kb_io.py)  ──┤                         │
                 ├──► T4 (ingest.py) ──► T6 (docs)
                 │                         │
                 └──► T5 (health.py) ──► T6 (docs)

T3 ──► T7 (AGENTS.md 更新)
```

**推荐开发节奏**
- Sprint 1：T1 + T2 并行（共享库）
- Sprint 2：T3 + T4 + T5 并行（三个脚本）
- Sprint 3：T6 + T7（文档和 AGENTS.md）

---

## 五、M1 与 M1+ 的边界

| | M1 | M1+ |
|---|---|---|
| 搜索方式 | 关键词（Jaccard/词频） | 向量（embedding） |
| 预处理 | 无 | 需运行 `index_build.py` |
| 外部依赖 | 无 | embedding 模型 |
| 新增文件 | 无 | `scripts/index_build.py`、`Knowledge Base/.search_index/` |
| search.py 改动 | 无 | 增加 `--mode vector|hybrid`，传入新 Scorer |

M1++ 知识图谱在 M1+ 向量索引之上构建页面关系图，提供图查询接口，规格待 M1+ 交付后再细化。

---

## 六、端到端验收测试

```
T-1  冷启动摄入
     准备：复制 Knowledge Base/，填写 config.yml（mode: auto）
     执行：python scripts/ingest.py --kb <kb> --source https://arxiv.org/abs/1706.03762
     断言：raw/sources.md 有新条目 / wiki/ 有新页面 / index.md 已更新

T-2  搜索定位
     基于 T-1 的知识库
     执行：python scripts/search.py --kb <kb> --query "attention transformer"
     断言：返回 JSON，results[0].path 指向刚摄入的 wiki 页面

T-3  健康检查基线
     对标准骨架执行：python scripts/health.py --kb <kb>
     断言：H1–H10 全部 PASS

T-4  健康检查检测能力
     删除 raw/index.md
     执行：python scripts/health.py --kb <kb>
     断言：H2 为 FAIL，detail 包含 "raw/"

T-5  confirm 模式
     执行：python scripts/ingest.py --kb <kb> --source <url> --mode confirm
     断言：打印操作计划，输入 "n" 后不写任何文件
```

---

## 七、关键参考文件

| 文件 | 用途 |
|---|---|
| `docs/spec/2026-04-20-ingest-protocol-config-roadmap.md` | 摄入流程四步、config.yml 字段定义、路线图权威来源 |
| `Knowledge Base/AGENTS.md` | T7 的修改目标，ingest protocol 精确描述 |
| `Knowledge Base/config.yml` | lib/config.py 的解析目标 |
| `Knowledge Base/templates/wiki-page-template.md` | ingest.py Step 5.3 生成 wiki 页面时使用的模板 |
| `Knowledge Base/templates/source-entry-template.md` | ingest.py Step 5.2 追加 sources.md 条目时使用的格式 |
