<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.svg">
    <img src="assets/logo-light.svg" width="360" alt="OpenWrite">
  </picture>
</p>

<h1 align="center">Autonomous Novel Writing CLI AI Agent<br><sub>自动化长篇小说写作 CLI AI Agent</sub></h1>

<p align="center">
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/version-5.4.0-2563eb" alt="Version"></a>
  <a href="pyproject.toml"><img src="https://img.shields.io/badge/python-%3E%3D3.10-22c55e" alt="Python >= 3.10"></a>
  <img src="https://img.shields.io/badge/entry-openwrite%20dante-0f172a" alt="Primary Entry: openwrite dante">
  <img src="https://img.shields.io/badge/structure-src%20%2B%20data-1d4ed8" alt="Structure: src + data">
</p>

<p align="center">
  长篇小说不是一次性 prompt。OpenWrite 把立项、设定、滚动大纲、章节写作、审查、真相文件和 workflow 放进同一条长期生产线里，让你和 Dante 持续把一本书写下去。
</p>

## 推荐用法

OpenWrite 推荐你把它当成一个长期协作的主 agent，而不是一组需要手工维护的文件夹。

- 对大多数用户来说，日常只需要记住两个入口：`openwrite goethe` 和 `openwrite dante`
- 先用 `openwrite goethe` 把脑洞整理成可写资产
- 日常推进时优先用 `openwrite dante`
- 只在需要精确检查或脚本化时才直接用 `write`、`review`、`context`、`assemble`
- 不要手工维护 `data/` 里的缓存和 workflow 文件
- 只有确认版内容才建议手改 `src/`

职责拆分：

- Goethe 负责长会话规划：汇总灵感、提建议、修人物、修设定、修大纲，并在资产成熟时显式交接给 Dante
- Dante 负责把可写资产持续写成正文，并在正文推进过程中必要时回修资产

一句话说清楚：

- `src/` 是人和 AI 共读的确认版真源
- `data/` 是运行态、workflow、手稿、缓存和快照
- `dante` 才是你最应该频繁使用的入口

### 只记住这两个入口

如果你不想记一堆命令，先只记住：

- `openwrite goethe`
  负责把你的脑洞整理成可写资产：灵感、人物、设定、大纲、风格来源
- `openwrite dante`
  负责把这些资产持续写成正文：写章、审查、推进运行态

其他 CLI 命令都可以理解成高级控制面：

- 当你要调试、脚本化、强制执行某一步时再用
- 平时不需要围着 `data/` 或单个工具命令工作

## 快速开始

### 1. 安装

```bash
git clone https://github.com/LiPu-jpg/Openwrite_skill.git
cd Openwrite_skill
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. 配置模型

```bash
export LLM_API_KEY=your-key
export LLM_MODEL=glm-5

# 如果你走兼容 OpenAI 的端点，也可以设置：
# export LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions
```

### 3. 新书先开 Goethe

```bash
openwrite goethe
```

进入 Goethe 之后，先把这几类信息聊清楚：

- 题材、基调和核心卖点
- 主角、主要矛盾、想避免的套路
- 基础设定、人物草案、当前可写范围大纲
- 你自己的样文、设定素材或同人来源文本

### 4. 资产够写了，再切 Dante

```bash
openwrite dante
```

如果项目已经存在，而且你已经有可写资产，通常不需要重新开 Goethe，直接：

```bash
source .venv/bin/activate
openwrite dante
```

## 最推荐的工作流

### 1. 先用 Goethe 把灵感整理成可写资产

Goethe 不是一次性建书器，而是长期 planning 会话。先在 Goethe 里把 idea 讲清楚：

- 题材和基调
- 主角与核心冲突
- 想避免的套路
- 你自己的样文、同人来源或设定素材
- 当前最想推进到哪

推荐会话像这样：

```text
$ openwrite goethe

我想写一本都市职场异能小说。
主角是普通上班族，晚上能看到异常术式。
先帮我汇总一下当前想法。
这个汇总可以，再整理成基础设定和人物草案。
把大纲推进到能写第六章的范围。
```

### 2. 再让 Dante 推进正文

当人物、设定和当前可写范围大纲已经成型后，再进入 Dante：

```text
$ openwrite dante

写第六章，3500 字，冲突更直接。
写完后先自审，再告诉我有没有设定冲突。
```

### 3. 让 Goethe 先做汇总，再做大纲；让 Goethe 显式 handoff 给 Dante

最稳的顺序是：

1. 聊 idea
2. 让 Goethe 汇总 idea
3. 确认基础设定
4. 生成或修改可写范围大纲
5. Goethe 在资产满足条件后显式 handoff 给 Dante
6. 再交给 Dante 写章和审查

不推荐直接说“给我写一章”，尤其是在设定和大纲还没稳定的时候。

### 4. 只有少数场景才建议直达命令

| 你要做什么 | 推荐命令 | 说明 |
|---|---|---|
| 从零开始建项目或持续规划资产 | `openwrite goethe` | 长期 planning 入口 |
| 长期讨论、推进整本书 | `openwrite dante` | 主入口 |
| 强制写指定章节 | `openwrite write ch_006` | 直达写作 |
| 用子流程写章 | `openwrite multi-write ch_006` | director/writer/reviewer 子流程 |
| 单独审查已写章节 | `openwrite review ch_006` | 不进聊天 |
| 查看组装上下文 | `openwrite context ch_006 --show` | 查 Dante 到底看了什么 |
| 导出 canonical packet | `openwrite assemble ch_006 --output-dir out` | 调试写作输入 |
| 查看当前运行态 | `openwrite status` | 看进度和阶段 |

你完全可以把这张表当“高级操作列表”：

- 日常创作：优先 `goethe` / `dante`
- 精确控制、调试或自动化脚本：再用这些直达命令

## Dante 会帮你做什么

`openwrite dante` 是长期会话 ReAct 主 agent。它会在会话里自己决定什么时候：

- 基于现有人物、设定和大纲推进正文
- 做章节 preflight
- 调 `write` 或 `multi-write`
- 调 `review`
- 必要时提出并回修人物、设定或大纲
- 推进 `book_state.yaml` 和 `wf_ch_*.yaml`

它不是一次一问一答的 prompt 包装，而是一个以正文推进为中心的持续工作主编排入口。

### Dante 的上下文来源

写章前，系统会组 canonical packet，而不是只拼一段 prompt。典型会包含：

- 当前可写范围大纲
- 故事背景和基础设定
- 相关角色文档
- 相关概念与世界规则
- 上一章正文
- `current_state.md`、`ledger.md`、`relationships.md`
- 风格合成结果和 craft 规则

Dante 也会接收 Goethe 交接过来的 handoff 摘要和当前可写窗口，不需要你从头重新解释前情。

所以更好的提问方式是给目标和约束，而不是直接指挥它去改某个缓存文件。

## 什么时候才手工改文件

绝大多数情况下，你不需要手工维护运行态文件。

推荐：

- 和 Dante 聊，确认后让它推进
- 需要人工修正时，只改 `src/` 下的确认版真源
- 改完 `src/` 后，用 `openwrite sync` 刷新派生缓存

不推荐：

- 手改 `data/hierarchy.yaml`
- 手改 `data/characters/cards/*.yaml`
- 手改 `data/workflows/wf_ch_*.yaml`
- 把 `background_draft.md`、`foundation_draft.md`、`outline_draft.md` 当另一套真相长期维护

如果你在问“该不该改这个 `data/` 文件”，大多数情况下答案都是“不该”。

## 目录心智

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
    │   ├── fingerprint.yaml
    │   └── manifest.toml
    ├── sources/{source_id}/
    │   ├── source.md
    │   ├── setting_profile.md
    │   ├── style/*.md
    │   └── extraction/
    ├── workflows/
    │   ├── book_state.yaml
    │   └── wf_ch_*.yaml
    ├── hierarchy.yaml
    ├── characters/cards/*.yaml
    └── test_outputs/
```

其中：

- `src/outline.md` 是唯一大纲真源
- `data/hierarchy.yaml` 是派生缓存
- `data/planning/ideation.md` 和 `data/planning/ideation_summary.md` 是会话与规划运行态
- `data/world/*.md` 和 `data/workflows/*.yaml` 是运行时状态

### 风格文件说人话

如果你把一篇参考文章交给系统，风格这条链会产出 3 层东西：

- `data/sources/{source_id}/`
  这是“拆书笔记”。AI 会把你提供的文章拆成来源说明、设定提要、叙述声音、语言习惯、节奏、对话等文档。
- `data/style/manifest.toml`
  这是“整理后的风格清单”。系统会把拆书笔记归一成：哪些能学、哪些不能照搬、哪些是作品约束、哪些是对话/叙述/节奏规则。
- `data/style/composed.md`
  这是“最终给这本书用的风格说明书”。Writer 真正主要参考的是它，而不是直接照着来源文章写。

一句话记忆：

- `sources/{source_id}` = 参考文章的拆解笔记
- `manifest.toml` = 拆解笔记整理后的可用风格清单
- `composed.md` = 给你这本书使用的最终风格说明书

## 常用命令

### 主入口

- `openwrite dante`
- `openwrite goethe`

### 写作与审查

- `openwrite write next`
- `openwrite write ch_006`
- `openwrite multi-write ch_006`
- `openwrite review`
- `openwrite review ch_006`

### 诊断与上下文

- `openwrite status`
- `openwrite doctor`
- `openwrite context ch_006 --show`
- `openwrite assemble ch_006 --output-dir out`
- `openwrite sync --check`
- `openwrite sync`

### 风格与题材

- `openwrite style extract office_excerpt --source text.txt`
- `openwrite setting extract office_excerpt --source text.txt`
- `openwrite source review office_excerpt`
- `openwrite source promote office_excerpt --target all`
- `openwrite style synthesize`
- `openwrite radar`

其中 `source promote --target all` 会同时：
- 切换 `style_id`
- 更新 `foundation.md`
- 把规则、时间线和阵营拆进 `src/world/*.md`

旧的 `openwrite agent` 已退役，请改用 `openwrite dante`。

## Agent 分工

- `Dante`
  正文创作主 ReAct agent。默认负责基于人物、设定和大纲推进章节正文、预检、审查和状态结算；必要时为正文推进回修资产。
- `Goethe`
  长会话规划 agent。更适合从零开始汇总灵感、提建议、写背景、写人物、写设定和写大纲，并在资产成熟后显式 handoff 给 Dante。
- `write`
  direct CLI 写作入口。适合明确知道要写哪一章时使用。
- `multi-write`
  Dante 可调度的写作子流程。内部会编排 director、writer、reviewer。
- `review`
  独立审查入口。适合对现有章稿做单独质量检查。

## 标准样例

标准样例项目在 [`data/novels/test_novel/`](data/novels/test_novel)。

如果你想最快看懂这套结构，建议顺序是：

1. [`src/outline.md`](data/novels/test_novel/src/outline.md)
2. [`src/story/background.md`](data/novels/test_novel/src/story/background.md)
3. [`data/planning/ideation.md`](data/novels/test_novel/data/planning/ideation.md)
4. [`data/planning/ideation_summary.md`](data/novels/test_novel/data/planning/ideation_summary.md)
5. [`data/world/current_state.md`](data/novels/test_novel/data/world/current_state.md)
6. [`data/workflows/book_state.yaml`](data/novels/test_novel/data/workflows/book_state.yaml)

## 常见问题

### 我应该先用 Goethe 还是 Dante

新书第一次启动，先 `openwrite goethe`。  
一旦书建立好了，日常推进基本都用 `openwrite dante`。

### 我改了 `src/`，为什么写作结果没变

先执行：

```bash
openwrite sync
```

### `outline_draft.md` 是不是另一份大纲真相

不是。`src/outline.md` 才是唯一真源。  
`outline_draft.md` 是给运行态和 workflow 可见性的镜像。

### 为什么 Dante 有时候会先让我确认，而不是直接写

因为大纲、基础设定和 idea summary 都是门禁。  
这不是磨叽，是为了避免长篇写作在后面 20 章、50 章后开始漂。

## 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `LLM_API_KEY` | 模型 API Key | 无 |
| `LLM_PROVIDER` | 提供商 | `openai` |
| `LLM_MODEL` | 模型名 | `gpt-4o-mini` |
| `LLM_BASE_URL` | 自定义兼容网关 | `https://api.openai.com/v1` |
| `LLM_TEMPERATURE` | 默认温度 | `0.7` |
| `LLM_MAX_TOKENS` | 最大输出 token | `24000` |
| `LLM_TIMEOUT_SECONDS` | 请求超时秒数 | SDK 默认 |
| `LLM_MAX_RETRIES` | 重试次数 | SDK 默认 |

## 版本

当前版本：`5.4.0`
