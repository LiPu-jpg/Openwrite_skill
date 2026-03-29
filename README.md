# OpenWrite

<img src="assets/logo.svg" width="420" alt="OpenWrite" />

OpenWrite 是一个面向长篇小说创作的 AI 工作台。它把「大纲、角色、世界观、伏笔、风格、章节写作、审查」放在同一条生产线上，让你能连续写，不靠记忆硬撑一致性。

## 为什么用 OpenWrite

- 写作链路完整：从立项到写章、审查、回写状态一条龙。
- 数据职责清晰：`src/` 放人工源文件，`data/` 放运行态文件。
- 支持自然语言和命令行：既能 `openwrite agent "写第五章"`，也能脚本化执行。
- 主编排入口统一：`openwrite agent` 负责整书流程，`multi-write` 可作为受限写作子流程。
- 可持续写长篇：真相文件自动更新，降低设定漂移。

## 一键启动

如果你已经在项目根目录，先执行：

```bash
source .venv/bin/activate
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o-mini
export LLM_API_KEY=sk-xxx
openwrite wizard
```

新项目从零开始：

```bash
git clone <repo_url>
cd Openwrite
python -m venv .venv
source .venv/bin/activate
pip install -e .
openwrite wizard
```

## 30 秒上手

```bash
# 1) 初始化（或用 wizard）
openwrite init my_novel

# 2) 同步 src -> data（建议在写作前跑一次）
openwrite sync

# 3) 写一章
openwrite write next

# 4) 审查
openwrite review

# 5) 查看状态
openwrite status
```

## 常用命令

### 基础命令

| 命令 | 用途 |
|---|---|
| `openwrite wizard` | 交互式创建项目（推荐新用户） |
| `openwrite init <novel_id>` | 初始化项目目录 |
| `openwrite status` | 查看当前项目状态 |
| `openwrite doctor` | 环境与路径自检 |

### 写作与审查

| 命令 | 用途 |
|---|---|
| `openwrite write next` | 写下一章 |
| `openwrite write ch_005` | 写指定章节 |
| `openwrite multi-write ch_005` | 多 Agent 编排写作 |
| `openwrite review` | 审查最新章节 |
| `openwrite review ch_005` | 审查指定章节 |

### 上下文与同步

| 命令 | 用途 |
|---|---|
| `openwrite context ch_005 --show` | 查看构建后的章节上下文 |
| `openwrite assemble ch_005 --output-dir <dir>` | 导出 V2 上下文包 |
| `openwrite sync --check` | 检查是否有待同步项 |
| `openwrite sync --check --json` | 机器可解析的同步检查输出 |
| `openwrite sync` | 执行同步 |

### Agent 与风格

| 命令 | 用途 |
|---|---|
| `openwrite agent "创建大纲"` | 自然语言驱动主编排 Agent |
| `openwrite agent "写第五章，偏冷峻"` | 按要求生成章节 |
| `openwrite radar` | 市场趋势分析 |
| `openwrite style extract <name> --source <file>` | 提取参考风格 |
| `openwrite style synthesize` | 合成风格文档 |

## 目录结构（重点）

```text
data/novels/{novel_id}/
├── src/                      # 共享 source of truth（人和 AI 共读）
│   ├── outline.md
│   ├── story/*.md            # Markdown 正文 + TOML front matter
│   ├── characters/*.md       # Markdown 正文 + TOML front matter
│   └── world/
│       ├── rules.md
│       ├── timeline.md
│       ├── terminology.md
│       └── entities/*.md     # Markdown 正文 + TOML front matter
└── data/                     # 运行态（工具读写）
        ├── hierarchy.yaml
        ├── characters/cards/*.yaml   # 从 src 派生的缓存，不手工维护
        ├── manuscript/arc_*/ch_*.md
        ├── foreshadowing/dag.yaml
        ├── world/
        │   ├── current_state.md      # Markdown 正文 + TOML front matter
        │   ├── ledger.md             # Markdown 正文 + TOML front matter
        │   └── relationships.md      # Markdown 正文 + TOML front matter
        ├── style/composed.md
        ├── workflows/*.yaml
        └── test_outputs/
```

## 单源文档格式

`src/story/*.md`、`src/characters/*.md`、`src/world/entities/*.md`，以及高频查看的 `data/world/*.md` 现在都推荐使用“`TOML front matter + Markdown 正文`”。

- front matter 放索引字段：`id`、`summary`、`tags`、`detail_refs`、`related`
- 正文放详细设定：背景、外貌、规则、特征、关系说明等
- `data/characters/cards/*.yaml` 仍会保留，但它只是从 `src/` 同步出来的派生缓存
- `src/outline.md` 是唯一的大纲真源；`data/hierarchy.yaml` 只是派生缓存

示例：

```md
+++
id = "chen_ming"
name = "陈明"
tier = "主角"
summary = "普通程序员觉醒术法后被迫在两个世界夹缝求生。"
tags = ["都市", "异能"]
detail_refs = ["background", "appearance", "personality"]

[[related]]
target = "zhao_lei"
kind = "friend"
note = "最信任的同事"
+++

# 陈明

## background
普通程序员，偶然觉醒术法。
```

## 写作链路是怎么跑的

1. canonical packet 组装：从 `src/outline.md`、`src/story/*.md`、`src/characters/*.md`、`src/world/**/*.md` 和运行态真相文件拼出统一上下文。
2. 章节生成：`write` 和 `multi-write` 都基于同一套 packet 写章，不再是两套不同上下文。
3. 章节审查：`review` 与 `multi-write reviewer` 共享同一类 packet 语义，不再空上下文审查。
4. 状态结算：更新 `current_state.md`、`ledger.md`、`relationships.md`，并同步 `book_state.yaml` 与 `wf_ch_*.yaml`。
5. 下一章继续：主编排和直接 CLI 都读同一套运行态，不需要手工对齐章节进度。

## Agent 结构

- `openwrite agent`：主编排入口，负责立项聊天、阶段判断、preflight、调度写作与审查。
- `openwrite write`：direct CLI 写作入口，但现在也会先组 canonical packet，并推进 workflow 与 book state。
- `openwrite multi-write`：受限子流程，director 编排 writer / reviewer / state settle；运行态推进和 direct write 保持一致。
- `openwrite review`：独立审查入口，但现在也复用 canonical packet，不再只看裸正文。
- `openwrite style synthesize`：把作品指纹、craft 规则与参考风格摘录写入 `data/style/composed.md`。

## 真相文件命名

对外统一使用 canonical 名称：

- `current_state`
- `ledger`
- `relationships`

历史别名 `particle_ledger`、`character_matrix`、`pending_hooks` 仍可被兼容读取，但不再作为文档和公共接口的主名称。

## 推荐工作流

```bash
# 每次开工先检查环境
openwrite doctor

# 编辑过 src 后先同步
openwrite sync --check
openwrite sync

# 风格指纹改动后可重建作品风格文档
openwrite style synthesize

# 生成 + 审查
openwrite write next
openwrite review
```

## 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LLM_API_KEY` | 模型 API Key | 无 |
| `LLM_PROVIDER` | 提供商（openai/anthropic） | openai |
| `LLM_MODEL` | 模型名 | gpt-4o-mini |
| `LLM_BASE_URL` | 自定义网关地址 | `https://api.openai.com/v1` |
| `LLM_TEMPERATURE` | 生成温度 | 0.7 |
| `LLM_MAX_TOKENS` | 最大输出 token | 8192 |

## 常见问题

### 报错：找不到 API Key

```bash
export LLM_API_KEY=sk-xxx
```

### 报错：未找到 `novel_config.yaml`

```bash
openwrite init my_novel
```

### 我改了 `src/`，为什么写作没生效

先跑同步：

```bash
openwrite sync
```

### 真相文件在哪

```text
data/novels/{novel_id}/data/world/
```

## 给 Agent 的自然语言示例

- `openwrite agent "帮我生成一份都市异能题材四级大纲"`
- `openwrite agent "创建一个反派角色，和主角是旧友"`
- `openwrite agent "写第六章，重点写冲突升级，字数 3500"`
- `openwrite agent "审查第六章并给出可执行修改建议"`

## 标准样例

标准样例项目在 `data/novels/test_novel/`。它包含：

- 确认版 `src/` 真源
- 长篇骨架草案 `data/planning/`
- 运行态真相文件 `data/world/`
- 已写章节 `data/manuscript/`
- canonical workflow `data/workflows/wf_ch_*.yaml`

如果你想快速看当前结构是否完整，可以直接读 `tests/test_standard_test_novel_fixture.py`。

## 版本

当前版本：`5.4.0`
