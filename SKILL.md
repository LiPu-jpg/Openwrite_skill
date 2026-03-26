---
name: openwrite-novel
description: 'Use when user wants to write novels, manage outlines, characters, world-building, or apply writing styles. Triggers: 写章节, 生成大纲, 创建角色, 世界观, 风格, 伏笔, 小说'
---

# OpenWrite 小说创作系统

AI 辅助小说创作系统。混合架构：简单操作由 SKILL.md 指令驱动，复杂算法由 Python 工具实现。

---

## 子技能导航

根据用户意图，读取对应子技能的 SKILL.md 获取详细指令：

| 用户意图 | 子技能文件 | 说明 |
|----------|-----------|------|
| 写章节 / 生成草稿 / 续写 | [skills/novel-creator/SKILL.md](./skills/novel-creator/SKILL.md) | 章节创作 Pipeline（含节拍、戏剧位置） |
| 角色 / 大纲 / 世界观 / 伏笔管理 | [skills/novel-manager/SKILL.md](./skills/novel-manager/SKILL.md) | 项目数据 CRUD |
| 检查 / 润色 / 逻辑审查 | [skills/novel-reviewer/SKILL.md](./skills/novel-reviewer/SKILL.md) | 审查与润色 Pipeline |
| 风格初始化 / 合成 / 分析 / 提取 | [skills/style-system/SKILL.md](./skills/style-system/SKILL.md) | 三层风格架构 |

**流程：** 识别意图 → 读取对应子技能 SKILL.md → 按其中步骤执行。

---

## 核心概念

### 四级大纲

```
总纲 (Master)     — 一本书一个
  └─ 篇纲 (Arc)   — 大篇章，如"修炼篇"（~20章）
      └─ 节纲 (Section) — 中段落，如"师门试炼"（~5章）
          └─ 章纲 (Chapter) — 最小写作单元（3000-5000字）
```

### 戏剧弧线层级

**起承转合 / 情感弧线在「节」和「篇」层面完成，不在章层面。**

- **篇 (Arc)**: `arc_structure` + `arc_emotional_arc` — 大弧线（铺垫→发展→高潮→收束）
- **节 (Section)**: `section_structure` + `section_emotional_arc` + `section_tension` — 中弧线（起→承→转→合）
- **章 (Chapter)**: `dramatic_position`（起/承/转/合/过渡） + `content_focus` — 章只负责"这几千字写什么"

### 三层风格架构

```
通用技法 (craft/)                              → 去 AI 味、对话/场景/节奏技法（跨作品共享）
参考风格 (data/reference_styles/{作品名}/)     → 从参考作品提取的风格指纹（声音、语言、节奏）
作品设定 (data/novels/{id}/ 下的角色/世界观)    → 角色卡、世界观实体、大纲约束
  ↓ 合成
最终风格指南 (data/novels/{id}/style/composed.md) → 注入生成上下文
```

**路径约定**：参考风格文档存 `data/reference_styles/`，作品运行时数据存 `data/novels/{novel_id}/`，两者分开。

---

## 上下文组装（核心机制）

写章节时，Agent 需要通过 Python 工具组装完整上下文：

```python
# tools/context_builder.py
from tools.context_builder import ContextBuilder

builder = ContextBuilder(project_root=Path.cwd(), novel_id="my_novel")
context = builder.build_generation_context(chapter_id="ch_005", window_size=5)

# context 包含：
# - outline_window: 前后 N 章大纲
# - active_characters: 出场角色（从 characters/cards/*.yaml 读取）
# - foreshadowing: 待回收/已埋伏笔（从 foreshadowing/dag.yaml 读取）
# - style_profile: 三层合成后的风格（从 style/composed.md 读取）
# - world_rules: 世界观约束（从 world/rules.md + world/entities/*.md 读取）
# - dramatic_context: 戏剧位置（节弧线 + 篇弧线 + 本章位置）
# - recent_text: 最近章节文本（从 manuscript/ 读取）

prompt_text = context.to_prompt_context()  # 转为 prompt 文本
```

**上下文自动包含的段落：** 上文 / 大纲窗口 / 当前章节 / 出场角色 / 伏笔 / 风格指南 / 世界观 / 本章目标 / 戏剧位置 / 章内情绪变化。

Token 预算 24000（留 8k 给生成），超限时自动调用 `progressive_compressor.py` 压缩。

---

## Python 工具

复杂算法通过 Python 脚本执行。路径均相对于 `opencode_skill/`：

| 工具 | 文件 | 说明 |
|------|------|------|
| **上下文组装** | `tools/context_builder.py` | 组装生成上下文（大纲、角色、伏笔、风格、戏剧位置），681 行 |
| **渐进式压缩** | `tools/progressive_compressor.py` | 章→节→篇三级压缩，592 行 |
| **伏笔 DAG** | `tools/foreshadowing_manager.py` | 伏笔有向无环图，支持环检测、路径查询，406 行 |
| **大纲解析** | `tools/outline_parser.py` | Markdown → OutlineHierarchy |
| **大纲序列化** | `tools/outline_serializer.py` | OutlineHierarchy → Markdown |
| **流程调度** | `tools/workflow_scheduler.py` | 写作流程状态管理，YAML 持久化，跨会话恢复 |
| **数据查询** | `tools/data_queries.py` | 大纲/角色/伏笔/风格查询 |\n| **世界观查询** | `tools/world_query.py` | 实体摘要列表、详情、关系图谱（`python3 tools/world_query.py {id}`） |
| **文件操作** | `tools/file_ops.py` | 沙箱内安全读写 |
| **项目初始化** | `tools/init_project.py` | `python3 tools/init_project.py {novel_id}` |
| **文本切割** | `tools/text_chunker.py` | 大文本智能切割（按章节边界，~3万字/块） |
| **风格提取流水线** | `tools/style_extraction_pipeline.py` | 分批提取进度管理、断点续传 |
| **工具函数** | `tools/utils.py` | 章节 ID 解析、中文拼音转换 |

### 数据模型

`models/` 下为 Pydantic 模型，供 Python 工具导入：

- `outline.py` — `OutlineNode`, `OutlineNodeType`, `OutlineHierarchy`
- `character.py` — `CharacterProfile`, `CharacterCard`, `CharacterTier`
- `style.py` — `StyleProfile`, `VoicePattern`, `LanguageStyle`, `RhythmStyle`
- `context_package.py` — `GenerationContext`, `ForeshadowingState`, `WorldRules`
- `foreshadowing.py` — `ForeshadowingNode`, `ForeshadowingEdge`, `ForeshadowingGraph`

---

## 数据结构

### 项目配置

在项目根目录创建 `novel_config.yaml`：

```yaml
novel_id: 术师手册
style_id: 术师手册
current_arc: arc_001
current_chapter: ch_003
```

### 目录布局

```
OpenWrite/
├── novel_config.yaml           # 项目配置
├── craft/                      # 通用写作技法（跨作品共享）
│   ├── humanization.yaml       # 去 AI 味规则
│   ├── ai_patterns.yaml        # AI 痕迹检测词库
│   ├── dialogue_craft.md       # 对话技法
│   ├── scene_craft.md          # 场景结构技法（8类通用模板）
│   └── rhythm_craft.md         # 节奏控制技法（加速/减速/钩子）
├── data/reference_styles/      # 参考作品的风格文档（跨项目共享）
│   ├── 术师手册/             # 每作品 7 个 .md
│   ├── 谁让他修仙的/
│   └── ...
└── data/novels/{novel_id}/     # 每部作品的运行时数据
    ├── outline/                # 大纲 (hierarchy.yaml + outline.md)
    ├── characters/             # 角色 (cards/*.yaml + profiles/*.md)
    ├── world/                  # 世界观
    │   ├── rules.md            # 世界底层规则（力量体系/社会规则/物理法则）
    │   ├── timeline.md         # 关键事件时间线
    │   ├── terminology.md      # 术语表（专有名词 + 解释）
    │   └── entities/           # 实体（*.md，关系图谱由 world_query.py 生成）
    ├── foreshadowing/          # 伏笔图 (dag.yaml)
    ├── style/                  # 风格合成结果
    │   ├── composed.md         # 最终合成风格（写作时注入）
    │   └── fingerprint.yaml    # 问询生成的风格指纹
    ├── manuscript/             # 草稿
    ├── compressed/             # 压缩摘要
    └── workflows/              # 流程状态 (YAML)
```

---

## 写作 Pipeline (V2)

```
1. context_assembly  → context_builder.py 组装上下文（含戏剧位置）
2. beat_generation   → 按 dramatic_position 选择节拍模板
3. writing           → Agent 按 novel-creator/SKILL.md 生成草稿
4. review            → Agent 按 novel-reviewer/SKILL.md 审查
5. user_confirm      → 用户确认/修改
6. styling           → Agent 按 style-system/SKILL.md 润色
7. compression       → progressive_compressor.py 压缩归档
```

流程状态由 `workflow_scheduler.py` 持久化到 YAML，支持中断后继续。

---

## 大纲 Markdown 格式

大纲文件使用 `> key: value` 元数据格式：

```markdown
# 我的小说

> 核心主题: 成长与救赎
> 目标字数: 200000

## 第一篇：修炼篇

> 篇弧线: 铺垫(sec01-02) → 发展(sec03-05) → 高潮(sec06) → 收束(sec07)
> 篇情感: 平静 → 紧张 → 绝望 → 重燃希望

### 第一节：师门试炼

> 节结构: 起(ch01) → 承(ch02-03) → 转(ch04) → 合(ch05)
> 节情感: 好奇 → 紧张 → 震惊 → 释然
> 节张力: low → rising → peak → falling

#### 第一章：入门

> 戏剧位置: 起
> 内容焦点: 主角拜师入门，建立日常
> 预估字数: 4000

#### 第四章：真相大白

> 戏剧位置: 转
> 内容焦点: 主角发现师门秘密，信念崩塌
> 预估字数: 5000
```

---

## 写作技法资源

| 文件 | 说明 |
|------|------|
| `craft/humanization.yaml` | 去 AI 味：禁用词、替换策略、检测规则 |
| `craft/ai_patterns.yaml` | AI 痕迹词库（"此外"、"值得注意的是"等） |
| `craft/dialogue_craft.md` | 对话写作技法（乒乓球规则、标签省略、群体对话） |
| `craft/scene_craft.md` | 场景结构技法（8类通用模板：设定说明/战斗/日常/煽情/说服/反转/考验/博弈） |
| `craft/rhythm_craft.md` | 节奏控制技法（段落分布/紧张松弛循环/加速减速/章节钩子/信息密度） |

---

## 已有风格数据

已从 6 部参考小说提取完整风格文档（每部 7 个 .md），存放在 `data/reference_styles/` 下，可直接用于风格合成：

| 参考作品 | 路径 |
|----------|------|
| 术师手册 | `data/reference_styles/术师手册/` |
| 谁让他修仙的 | `data/reference_styles/谁让他修仙的/` |
| 天启预报 | `data/reference_styles/天启预报/` |
| 牧者密续 | `data/reference_styles/牧者密续/` |
| 不许没收我的人籍 | `data/reference_styles/不许没收我的人籍/` |
| 我师兄实在太稳健了 | `data/reference_styles/我师兄实在太稳健了/` |

每部作品的风格文档包含：`summary.md` / `voice.md` / `language.md` / `rhythm.md` / `dialogue.md` / `scene_templates.md` / `consistency.md`

---

## 参考文档

| 文档 | 说明 |
|------|------|
| [PLAN.md](./PLAN.md) | 进度跟踪 & 变更日志 |
| [README.md](./README.md) | 项目概览 & 架构说明 |
| [docs/MIGRATION_GUIDE.md](./docs/MIGRATION_GUIDE.md) | 从 OpenWrite 迁移的设计文档 |

---

*版本: 5.4.0 | 最后更新: 2026-03-25*

---

## ReAct Agent

OpenWrite 内置 ReAct Agent，支持自然语言交互。工具调用循环：

```
用户指令 → LLM(带工具) → 工具执行 → 结果返回 → LLM(带工具) → ...
```

**内置 9 个工具：**

| 工具 | 说明 |
|------|------|
| `write_chapter` | 写章节草稿 |
| `review_chapter` | 审查章节 |
| `get_status` | 查看项目状态 |
| `get_context` | 获取写作上下文 |
| `list_chapters` | 列出所有章节 |
| `create_outline` | 创建/更新大纲 |
| `create_character` | 创建角色 |
| `get_truth_files` | 读取真相文件 |
| `update_truth_file` | 更新真相文件 |

**CLI 用法：**
```bash
openwrite agent "写第五章"
openwrite agent "查看项目状态"
openwrite agent "创建一个新角色：李四，师弟"
```
