# OpenWrite

<img src="assets/logo.svg" width="420" alt="OpenWrite" />

OpenWrite 是一个面向长篇小说创作的 AI 工作台。它不是“给模型塞一段 prompt 然后生成一章”，而是把立项、设定、滚动大纲、章节写作、审查、真相文件和 workflow 放进同一条长期生产线里，让你能真的把一本书持续写下去。

## 它和普通 AI 写作工具的区别

- 它按“整本书”工作，不按“单次生成”工作。
- `src/` 是人和 AI 共用的确认版真源，`data/` 是运行态，不再维持两套彼此漂移的文档。
- 写章前会先组 canonical packet，不是裸 prompt。
- `openwrite dante` 是长期会话主入口，会先收集想法、汇总 idea、确认基础设定和可写大纲，再进入章节写作。
- `write`、`multi-write`、`review`、`dante` 现在都会推进同一套 `book_state.yaml` 和 `wf_ch_*.yaml`。

## 3 分钟开始

```bash
git clone <repo_url>
cd Openwrite
python -m venv .venv
source .venv/bin/activate
pip install -e .

export LLM_API_KEY=your-key
export LLM_MODEL=gpt-4o-mini
# 如果你走兼容端点，也可以额外设置：
# export LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions

openwrite goethe
```

如果项目已经存在，直接在项目根目录执行：

```bash
source .venv/bin/activate
openwrite status
```

## 你会怎么用它写一本书

OpenWrite 推荐的链路不是“上来就写章”，而是：

1. 立项聊天  
   用 `goethe` 建项目，或直接启动 `dante` 聊你的想法。
2. 汇总 idea  
   `dante` 会把当前灵感整理成可确认的汇总，而不是把零散聊天直接硬塞进大纲。
3. 确认基础设定  
   背景、主角、规则、核心冲突稳定下来后，再进入大纲阶段。
4. 生成或修改可写范围大纲  
   大纲是硬门槛，没有当前可写范围的大纲，就不进入写章。
5. 写章与审查  
   `write`、`multi-write` 和 `review` 都基于同一套 canonical packet。
6. 回写运行态  
   `current_state.md`、`ledger.md`、`relationships.md`、`book_state.yaml`、`wf_ch_*.yaml` 会同步推进。

一个典型会话会像这样：

```bash
openwrite dante
# 然后在 Dante 会话里持续聊天：
# 我想写一本都市职场异能小说
# 主角是普通上班族，晚上能看到异常术式
# 先帮我汇总一下当前想法
# 这个汇总可以
# 帮我生成一份四级大纲
# 大纲范围确认，可以开始写
# 写第六章，3500字，冲突更直接
openwrite review ch_006
```

## 最重要的心智模型

### 1. `src/` 是唯一真源

这里放确认版、长期维护的内容：

- `src/outline.md`
- `src/story/background.md`
- `src/story/foundation.md`
- `src/characters/*.md`
- `src/world/rules.md`
- `src/world/terminology.md`
- `src/world/timeline.md`
- `src/world/entities/*.md`

这些文件推荐使用“`TOML front matter + Markdown 正文`”：

- front matter 放索引字段：`id`、`summary`、`tags`、`detail_refs`、`related`
- 正文放给人和 AI 共同阅读的详细设定

### 2. `data/` 是运行态，不是第二份真相

这里放工作流、运行时状态、手稿和派生缓存：

- `data/manuscript/`：正文
- `data/world/`：`current_state.md`、`ledger.md`、`relationships.md`
- `data/workflows/`：`book_state.yaml`、`wf_ch_*.yaml`
- `data/foreshadowing/`：伏笔图和日志
- `data/style/`：合成风格和指纹
- `data/test_outputs/`：上下文包快照
- `data/characters/cards/*.yaml`、`data/hierarchy.yaml`：从 `src/` 派生出的缓存

`data/planning/` 里有两类东西：

- 真正的运行态规划记录：`ideation.md`、`ideation_summary.md`
- 给 workflow 可见性的镜像文件：`background_draft.md`、`foundation_draft.md`、`outline_draft.md`

其中确认版真源仍然是 `src/`，不是 `planning/*.md`。

### 3. 写章靠的是 canonical packet

写作前，系统会把这些信息拼成一个统一的上下文包：

- 当前可写范围大纲
- 故事背景和基础设定
- 相关角色文档
- 相关概念与世界规则
- 上一章正文
- 当前运行态真相文件
- 作品风格、craft 规则、参考风格摘要

所以 OpenWrite 的核心不是“一个 prompt”，而是“持续维护一份可拼接的小说状态”。

## 目录结构

```text
data/novels/{novel_id}/
├── src/
│   ├── outline.md
│   ├── story/
│   │   ├── background.md
│   │   └── foundation.md
│   ├── characters/*.md
│   └── world/
│       ├── rules.md
│       ├── terminology.md
│       ├── timeline.md
│       └── entities/*.md
└── data/
    ├── planning/
    │   ├── ideation.md
    │   ├── ideation_summary.md
    │   ├── background_draft.md
    │   ├── foundation_draft.md
    │   └── outline_draft.md
    ├── manuscript/arc_*/ch_*.md
    ├── world/
    │   ├── current_state.md
    │   ├── ledger.md
    │   └── relationships.md
    ├── foreshadowing/dag.yaml
    ├── style/
    │   ├── composed.md
    │   └── fingerprint.yaml
    ├── workflows/
    │   ├── book_state.yaml
    │   └── wf_ch_*.yaml
    ├── hierarchy.yaml
    ├── characters/cards/*.yaml
    └── test_outputs/
```

## 常用命令

### 建项目和检查环境

| 命令 | 用途 |
|---|---|
| `openwrite goethe` | 交互式创建项目，适合从零开始 |
| `openwrite init <novel_id>` | 直接初始化目录 |
| `openwrite status` | 查看当前运行态 |
| `openwrite doctor` | 自检环境和路径 |

### 主编排

| 命令 | 用途 |
|---|---|
| `openwrite dante` | 启动长期会话主 agent |
| 在 Dante 会话里说“先帮我汇总一下当前想法” | 整理 ideation summary |
| 在 Dante 会话里说“帮我生成一份四级大纲” | 生成或修改当前可写大纲 |
| 在 Dante 会话里说“写第六章，字数 3500” | 记录写作请求并进入 preflight / delegation |

### 写作、审查、上下文

| 命令 | 用途 |
|---|---|
| `openwrite write next` | direct CLI 写下一章 |
| `openwrite write ch_005` | 写指定章节 |
| `openwrite multi-write ch_005` | 用 director/writer/reviewer 子流程写章 |
| `openwrite review` | 审查最新章节 |
| `openwrite review ch_005` | 审查指定章节 |
| `openwrite context ch_005 --show` | 查看章节上下文 |
| `openwrite assemble ch_005 --output-dir <dir>` | 导出 canonical packet 快照 |

### 同步与风格

| 命令 | 用途 |
|---|---|
| `openwrite sync --check` | 检查 `src -> data` 是否有待同步项 |
| `openwrite sync` | 执行同步 |
| `openwrite style extract <name> --source <file>` | 提取参考风格 |
| `openwrite style synthesize` | 重建 `data/style/composed.md` |
| `openwrite radar` | 做题材/平台趋势分析 |

## Agent 分工

- `openwrite dante`  
  主编排入口。长期会话式 ReAct 主 agent，负责立项聊天、idea 汇总、基础设定门禁、大纲门禁、章节 preflight、调度写作与审查。

- `openwrite write`  
  direct CLI 写作入口。适合明确知道要写哪一章时使用，但它现在也会走 canonical packet、workflow 和 book state。

- `openwrite multi-write`  
  受限子流程。内部由 director 编排 writer / reviewer，更像 `openwrite dante` 可调用的 subagent。

- `openwrite review`  
  独立审查入口。和 `multi-write` reviewer 共享同一类 packet 语义，不再是裸正文审查。

- `openwrite goethe`  
  项目创建引导。适合从零开始立项，不是长期写作主编排。

- `openwrite agent`  
  已退役的旧入口。请改用 `openwrite dante`。

## 推荐工作方式

### 如果你主要手工维护设定

1. 改 `src/` 里的真源文档
2. 跑 `openwrite sync`
3. 用 `context` 或 `assemble` 看 packet
4. 再 `write` / `multi-write` / `review`

### 如果你主要让 agent 推进

1. 用 `openwrite dante` 启动长期会话，先聊 idea
2. 先确认 idea summary
3. 再确认基础设定和可写大纲
4. 然后让 Dante 写章和审查

### 不建议的做法

- 直接手改 `data/hierarchy.yaml`
- 把 `data/characters/cards/*.yaml` 当真源维护
- 没确认当前可写范围大纲就直接连写多章

## 标准样例

标准样例项目在 [`data/novels/test_novel/`](data/novels/test_novel)。它包含：

- 确认版 `src/` 真源
- `ideation.md` 和 `ideation_summary.md`
- 长篇骨架与当前可写窗口
- 运行态真相文件
- 已写章节手稿
- canonical workflow 文件

如果你想最快看懂这套结构，先读：

- [`src/outline.md`](data/novels/test_novel/src/outline.md)
- [`data/planning/ideation.md`](data/novels/test_novel/data/planning/ideation.md)
- [`data/planning/ideation_summary.md`](data/novels/test_novel/data/planning/ideation_summary.md)
- [`data/workflows/book_state.yaml`](data/novels/test_novel/data/workflows/book_state.yaml)

## 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LLM_API_KEY` | 模型 API Key | 无 |
| `LLM_PROVIDER` | 提供商 | `openai` |
| `LLM_MODEL` | 模型名 | `gpt-4o-mini` |
| `LLM_BASE_URL` | 自定义兼容网关 | `https://api.openai.com/v1` |
| `LLM_TEMPERATURE` | 默认温度 | `0.7` |
| `LLM_MAX_TOKENS` | 最大输出 token | `8192` |
| `LLM_TIMEOUT_SECONDS` | 请求超时秒数 | SDK 默认 |
| `LLM_MAX_RETRIES` | 重试次数 | SDK 默认 |

## 常见问题

### 我改了 `src/`，为什么写作没生效

先同步：

```bash
openwrite sync
```

### 大纲到底看哪一份

看 `src/outline.md`。  
`data/hierarchy.yaml` 是缓存，不是给人手工维护的第二份大纲。

### `background_draft.md` / `foundation_draft.md` / `outline_draft.md` 是不是另一套真相

不是。它们是 runtime mirror，方便 workflow 和 agent 看到当前草案状态。确认版真源仍然在 `src/`。

### 真相文件在哪

```text
data/novels/{novel_id}/data/world/
```

### 先聊天还是先写大纲

先聊天，先汇总 idea，先确认基础设定，再改大纲。  
OpenWrite 现在支持这条闭环，不建议跳过。

## 版本

当前版本：`5.4.0`
