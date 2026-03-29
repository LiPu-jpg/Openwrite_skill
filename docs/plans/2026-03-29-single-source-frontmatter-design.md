# OpenWrite Single-Source Front Matter Design

**Problem**

当前项目把“人读的说明文档”和“AI 读的结构化索引”拆成了两层：

- `src/characters/*.md` 给人看
- `data/characters/cards/*.yaml` 给程序/AI 快速读
- `src/world/entities/*.md` 给人看，但结构解析依赖隐式 Markdown 约定

这会带来两个问题：

1. 人与 AI 看到的不是同一份源文件，容易失步。
2. 机器需要的结构化索引很弱，只能靠脆弱的 Markdown 约定提取。

**Decision**

采用“单源文档 + 双视图”设计：

- 单个 `.md` 文件同时作为人类阅读源和 AI 结构化源。
- 文件头使用 `TOML front matter` 承载稳定、简短、便于索引的元数据。
- 文件体使用 `Markdown` 承载长文本解释、章节化说明和细节。
- `data/` 下的 YAML/TOML 卡片继续保留为派生缓存，不再是逻辑真源。

**Why Not Pure TOML**

- 长篇设定、人物细节、复杂解释不适合全部放入 TOML 多行字符串。
- Markdown 仍然是人类可读性最好的长文表达形式。
- `TOML front matter + Markdown body` 既保留结构性，也保留阅读性。

**Canonical Shape**

角色示例：

```md
+++
id = "char_chen_ming"
type = "character"
tier = "主角"
summary = "普通程序员出身，觉醒术法后被迫在职场与超自然世界之间求生。"
tags = ["都市", "职场", "异能", "成长"]
detail_refs = ["background", "appearance", "personality", "current_state", "relations"]

[[related]]
target = "char_zhao_lei"
kind = "friend"
weight = 0.82
note = "最信任的同事"
+++

# 陈明

## background
...

## appearance
...
```

世界实体示例：

```md
+++
id = "company"
type = "location"
subtype = "building"
status = "active"
summary = "陈明所在的互联网科技公司，典型 996 环境，也是多数事件主舞台。"
tags = ["公司", "都市", "主舞台"]
detail_refs = ["rules", "features", "relations"]
+++

# 公司（互联网科技公司）

## rules
- 996 工作制
...
```

**Read Path**

AI 默认只需要先看 front matter 中的：

- `id`
- `type`
- `subtype`
- `status`
- `summary`
- `tags`
- `related`
- `detail_refs`

只有需要更深上下文时，才展开 Markdown body 的具体 section。

**MVP Scope**

本轮只落两条主链：

1. `src/characters/*.md`
2. `src/world/entities/*.md`

不在本轮改造：

- `outline.md`
- `src/world/rules.md` / `terminology.md` / `timeline.md`
- `data/world/*.md`
- `workflow` 文件

**Compatibility**

本轮需要保持向后兼容：

- 没有 front matter 的旧 Markdown 角色档继续可读。
- 没有 front matter 的旧实体文件继续可读。
- `data/characters/cards/*.yaml` 继续生成，但来源改为同一份 Markdown 单源文档。

**Intended Outcome**

- 人和 AI 围绕同一份源文件协作。
- 结构化索引和详细解释不再分裂成两份真相。
- 后续可以在不推翻本轮设计的前提下，把 `world/*.md` 和 `outline.md` 逐步升级到同样模式。
