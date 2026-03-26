# OpenWrite → OpenCode Skill 迁移进度

> 从 `reference/openwrite_original/` 移植到 OpenCode Skill 架构
> 启动时间: 2026-03-03 | 最后更新: 2026-03-05

---

## 架构决策

- **混合模式**: 简单操作走 Prompt-driven（SKILL.md 指令），复杂算法（压缩、DAG 环检测等）保留 Python 工具
- **models/ 重写**: tools/ 代码使用的 API 和 reference 原版 models 不兼容，已按 tools/ 实际接口重新编写
- **workflow_scheduler 重构**: 去除 Agent 类依赖，改为文件驱动的流程状态管理器

---

## 任务清单

### Phase 1: 基础修复 — ✅ 全部完成

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1 | 创建 `models/` 包 | ✅ 完成 | 5 个文件 + `__init__.py` |
| 2 | 验证 Python import | ✅ 完成 | 所有 tools/ 文件 import 通过 |
| 3 | 修复 `context_builder.py` 重复 append bug | ✅ 完成 | 第188行重复 `hierarchy.chapters.append` 已删除 |
| 4 | 修复 SKILL.md 死链 | ✅ 完成 | 引用已修正为现有文件 |
| 5 | 更新 README.md 引用 | ✅ 完成 | 全面重写为当前架构 |

### Phase 2: 工具修复 — ✅ 全部完成

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 6 | 重构 `workflow_scheduler.py` | ✅ 完成 | 去除 Agent 依赖，改为文件驱动状态管理器（YAML 持久化） |
| 7 | 修复 `outline_parser.py` TODO | ✅ 完成 | 实现 `_parse_chapter_range()`，支持 `ch_001 - ch_010` / 逗号列表 / 纯数字 |
| 8 | 补全 `style-system/templates/` | ✅ 完成 | 4 个模板：fingerprint / extraction_report / composed_style / analysis_report |

### Phase 3: 文档与验证

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 9 | 统一架构说明 | ✅ 完成 | README.md 全面重写，包含混合模式架构图 |
| 10 | 端到端验证测试 | ✅ 完成 | 21/21 通过（含新戏剧弧线字段） |

### Phase 4: 戏剧弧线重构 — ✅ 全部完成

核心认知修正：**起承转合 / 情感弧线在「节」和「篇」层面完成，不在章层面。**
章只是按字数切的 3000-5000 字写作单元，通过 `dramatic_position` 知道自己在节弧线中的位置。

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 11 | OutlineNode 模型重构 | ✅ 完成 | 新增 Arc 级 (arc_structure/arc_emotional_arc/arc_theme)、Section 级 (section_structure/section_emotional_arc/section_tension)、Chapter 级 (dramatic_position/content_focus) |
| 12 | OutlineHierarchy 导航方法 | ✅ 完成 | get_parent_section() / get_parent_arc() / get_dramatic_context() |
| 13 | GenerationContext 戏剧上下文 | ✅ 完成 | dramatic_context 字段 + to_prompt_sections() 输出「戏剧位置」段落 |
| 14 | outline_parser 新字段解析 | ✅ 完成 | 篇弧线/篇情感/节结构/节情感/节张力/戏剧位置/内容焦点 |
| 15 | outline_serializer 新字段输出 | ✅ 完成 | 篇弧线/篇情感/节结构/节情感/节张力/戏剧位置/内容焦点/章内情绪 |
| 16 | beat_templates.yaml 重写 | ✅ 完成 | 从通用模板改为 position_起/承/转/合/过渡 + scene_overlays |
| 17 | novel-creator SKILL.md 更新 | ✅ 完成 | Steps 3-8 重写，新增「确定戏剧位置」步骤 |
| 18 | context_builder 戏剧上下文注入 | ✅ 完成 | hierarchy.get_dramatic_context() → GenerationContext.dramatic_context |
| 19 | 验证测试 | ✅ 完成 | 21/21 通过 |

### Phase 5: 文档修正 — ✅ 全部完成

修正问题：SKILL.md 使用不存在的 `superpowers:xxx` 机制、缺少子技能导航、缺少上下文拼接说明。

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 20 | 重写 SKILL.md | ✅ 完成 | 去除 superpowers 引用，新增子技能导航表、上下文组装说明（含代码示例）、戏剧弧线概念、Python 工具表、大纲 Markdown 格式说明 |
| 21 | 更新 README.md | ✅ 完成 | 补充 skills/ 文档链接、Pipeline V2 新增节拍阶段、状态列表更新（含 Phase 4 成果）、版本 3.0 |
| 22 | 更新 PLAN.md | ✅ 完成 | 新增 Phase 5 记录 |

### Phase 5.5: 风格数据建设 — ✅ 全部完成

从 6 部百万字级参考小说中提取完整风格文档，建立风格数据库。

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 23 | 实现 text_chunker.py | ✅ 完成 | 智能文本切割（按章节边界，~3万字/块） |
| 24 | 实现 style_extraction_pipeline.py | ✅ 完成 | 分批提取流水线，进度管理，断点续传 |
| 25 | 编写 batch_extract_style.md | ✅ 完成 | 大文本分批提取核心提示词（三层架构、层级判断、增量更新） |
| 26 | 提取「术师手册」风格 | ✅ 完成 | 7 个风格文档 |
| 27 | 提取「谁让他修仙的」风格 | ✅ 完成 | 7 个风格文档 |
| 28 | 提取「天启预报」风格 | ✅ 完成 | 7 个风格文档 |
| 29 | 提取「牧者密续」风格 | ✅ 完成 | 7 个风格文档 |
| 30 | 提取「不许没收我的人籍」风格 | ✅ 完成 | 7 个风格文档 |
| 31 | 提取「我师兄实在太稳健了」风格 | ✅ 完成 | 7 个风格文档 |

### Phase 6: 系统整理 — ✅ 全部完成

修复路径不一致、补全遗漏引用、统一三层架构的实际路径。

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 32 | 修复根 SKILL.md 路径 | ✅ 完成 | 三层架构路径改为实际 `data/novels/{id}/` 下；删除幻影目录 `styles/{作品}/`、`novels/{作品}/`；新增已有风格数据表 |
| 33 | 补全 Python 工具表 | ✅ 完成 | 新增 text_chunker.py、style_extraction_pipeline.py |
| 34 | 修复 style-system 路径 | ✅ 完成 | 层次图、数据文件表、合成输入路径统一为 `data/novels/{id}/` |
| 35 | 修复 prompts 路径 | ✅ 完成 | compose_style.md / batch_extract_style.md / initialize_style.md 路径修正；删除 `craft/tropes/` 引用 |
| 36 | 修复 novel-creator 路径 | ✅ 完成 | 风格读取路径修正；新增前置条件表 |
| 37 | 修复 novel-reviewer 路径 | ✅ 完成 | 文件访问表补全 |
| 38 | 更新 PLAN.md | ✅ 完成 | Phase 5.5 + Phase 6 + Phase 7 规划 |

---

### Phase 7: 端到端验证（下一步）

**目标**：选择一个真实项目，跑通从"初始化 → 大纲 → 角色 → 世界观 → 写章节 → 审查 → 润色"的完整流程。

| # | 任务 | 状态 | 优先级 | 备注 |
|---|------|------|--------|------|
| 39 | 选定验证项目 | ✅ 完成 | P0 | test_novel（《公司里的术师》）— 仿《术师手册》风格的都市奇幻 |
| 40 | 初始化项目数据 | ✅ 完成 | P0 | `python3 tools/init_project.py test_novel` — 15个目录 + config |
| 41 | 编写大纲 | ✅ 完成 | P0 | 1篇 + 2节 + 7章，outline.md + hierarchy.yaml |
| 42 | 创建角色卡 | ✅ 完成 | P0 | 3个角色（陈明/赵磊/林悠）3卡片 + 3档案 |
| 43 | 创建世界观实体 | ✅ 完成 | P1 | 5个Markdown实体 + rules.md + timeline.md + terminology.md |
| 44 | 风格合成 | ✅ 完成 | P0 | 基于术师手册风格 + craft/ + 角色设定生成 composed.md |
| 45 | 写第一章（端到端） | ✅ 完成 | P0 | ~3440字，4个节拍，埋设伏笔 fs_wrist_rune |
| 46 | 审查 + 润色 | ✅ 完成 | P1 | 88/100，0 AI痕迹，1格式问题（ASCII引号→中文引号）已修复 |
| 47 | 压缩归档 | 🚧 待定 | P1 | 验证 progressive_compressor 三级压缩 |
| 48 | 连续写 3 章 | 🚧 待定 | P1 | 验证上下文窗口滑动、伏笔追踪、跨章一致性 |

### Phase 8: 补全工具链（后续）

### Phase 7.5: 世界观系统扩展 — ✅ 全部完成

重新认知：世界观不只是实体列表，需要**规则 + 时间线 + 术语表 + 实体**四部分。同时修复 context_builder 从未注入世界观数据的 bug。

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 54 | 分析世界观系统缺陷 | ✅ 完成 | context_builder._get_world_rules() 读取不存在的 rules.yaml/worldbuilding_rules.md，世界观数据从未注入写作上下文 |
| 55 | 创建 rules.md | ✅ 完成 | 力量体系/社会规则/物理法则/禁忌与未知 |
| 56 | 创建 timeline.md | ✅ 完成 | 关键事件时间线（表格，按章节排列） |
| 57 | 创建 terminology.md | ✅ 完成 | 9 个核心术语定义 |
| 58 | 修复 context_builder._get_world_rules() | ✅ 完成 | 重写为：加载 rules.md → world_query 获取实体/关系 → 读取章节 involved_settings |
| 59 | 更新 init_project.py | ✅ 完成 | 初始化时创建 rules.md/timeline.md/terminology.md 骨架 |
| 60 | 更新文档 | ✅ 完成 | SKILL.md(v5.1) + novel-manager SKILL.md + README.md(v5.1) |

### Phase 8: 补全工具链（后续）

| # | 任务 | 状态 | 优先级 | 备注 |
|---|------|------|--------|------|
| 49 | 世界观冲突检查 | 🚧 待定 | P2 | 集成 world_conflict_checker 到 reviewer 流程 |
| 50 | 伏笔可视化 | 🚧 待定 | P2 | 伏笔 DAG 图形化输出 |
| 51 | 多项目切换 | 🚧 待定 | P2 | novel_config.yaml 支持快速切换 |
| 52 | craft/ 技法扩充 | 🚧 待定 | P3 | 场景模板库、情感弧线模板、张力曲线模板 |
| 53 | 风格对比工具 | 🚧 待定 | P3 | 将生成文本与参考作品风格指标对比 |

---

## 关键发现

### models 不兼容问题

tools/ 代码和 reference/openwrite_original/tools/models/ 是两套设计：

| 模块 | reference 原版 | tools/ 实际使用 |
|------|---------------|----------------|
| outline | 4个独立类 (MasterOutline/ArcOutline/SectionOutline/ChapterOutline) | 统一 OutlineNode + OutlineNodeType 枚举 |
| character | 复杂体系 (CharacterStatic/State/StateMutation/TextCharacterProfile) | 简化 CharacterProfile + CharacterCard + CharacterTier |
| style | 从 composed markdown 解析的桥接 StyleProfile | 三层风格栈 (craft_rules/voice/language/rhythm/work_setting) |
| context_package | writing_prompt/recent_text/previous_arc_summary 字段 | outline_window/active_characters/foreshadowing/style_profile 字段 |
| foreshadowing | ✅ 基本一致 | ✅ 直接移植 |

### 可直接运行的工具（无需 models）

- `tools/data_queries.py` — YAML 查询
- `tools/file_ops.py` — 沙箱文件操作
- `tools/init_project.py` — 项目初始化（可独立 `python3 init_project.py novel_id`）
- `tools/utils.py` — 章节 ID 解析、中文拼音转换

### 需要 models 的工具

- `tools/context_builder.py` — 上下文组装（核心，681 行）
- `tools/progressive_compressor.py` — 渐进式压缩（592 行）
- `tools/foreshadowing_manager.py` — 伏笔 DAG（406 行）
- `tools/outline_parser.py` — Markdown → 大纲
- `tools/outline_serializer.py` — 大纲 → Markdown
- `tools/workflow_scheduler.py` — 流程状态管理（重构后，纯文件驱动）

---

## 文件变更日志

### 2026-03-03

- 合并 docs/ 下 5 个文件为 `docs/MIGRATION_GUIDE.md`
- 删除 DELIVERY_SUMMARY.md, MIGRATION_PLAN.md, MIGRATION_SUMMARY.md, QUICK_REFERENCE.md, SKILL_LIST.md

### 2026-03-04

- 创建 `models/outline.py` — OutlineNode, OutlineNodeType, OutlineHierarchy
- 创建 `models/character.py` — CharacterCard, CharacterProfile, CharacterTier
- 创建 `models/style.py` — StyleProfile, VoicePattern, LanguageStyle, RhythmStyle
- 创建 `models/context_package.py` — GenerationContext, ForeshadowingState, WorldRules
- 创建 `models/foreshadowing.py` — ForeshadowingNode, ForeshadowingEdge, ForeshadowingGraph
- 创建 `models/__init__.py`
- 创建 `PLAN.md`
- 修复 `context_builder.py` 第188行重复 append bug
- 修复 SKILL.md 和 README.md 死链
- 重构 `workflow_scheduler.py`：去除 Agent 类依赖（LibrarianAgent/LoreCheckerAgent/StylistAgent），改为 WorkflowState + StageRecord 状态管理器，YAML 持久化，支持跨会话恢复
- 实现 `outline_parser.py` 章节范围解析 `_parse_chapter_range()`
- 创建 4 个风格系统模板：fingerprint.yaml / extraction_report.yaml / composed_style.md / analysis_report.yaml
- 全面重写 README.md，包含混合模式架构图、准确目录结构、当前状态

### 2026-03-04 (Phase 4: 戏剧弧线重构)

- **架构修正**: 起承转合 / 情感弧线从章级移至节/篇级，章只是字数单元
- 重构 `models/outline.py`：OutlineNode 新增 Arc/Section/Chapter 三级字段，OutlineHierarchy 新增 3 个导航方法
- 更新 `models/context_package.py`：GenerationContext 新增 dramatic_context 字段，to_prompt_sections() 输出「戏剧位置」
- 更新 `tools/context_builder.py`：通过 hierarchy.get_dramatic_context() 注入戏剧上下文
- 更新 `tools/outline_parser.py`：解析 篇弧线/篇情感/节结构/节情感/节张力/戏剧位置/内容焦点
- 更新 `tools/outline_serializer.py`：序列化新字段
- 完全重写 `skills/novel-creator/templates/beat_templates.yaml`：从通用模板改为 position_起/承/转/合/过渡 + scene_overlays
- 重写 `skills/novel-creator/SKILL.md` Steps 3-8：新增戏剧位置确定步骤
- 验证测试 21/21 通过

### 2026-03-04 (Phase 5: 文档修正)

- 重写 `SKILL.md`：去除所有 `superpowers:xxx` 引用（这不是 OpenCode Skill 的真实机制），新增子技能导航表、上下文组装代码示例、戏剧弧线概念、Python 工具表、大纲格式说明
- 更新 `README.md`：新增 skills/ 导航链接、Pipeline V2 增加节拍阶段、状态列表包含 Phase 4 成果
- 更新 `PLAN.md`：新增 Phase 5

### 2026-03-04 (Phase 5.5: 风格数据建设)

- 实现 `tools/text_chunker.py`：智能文本切割，按章节边界~3万字/块
- 实现 `tools/style_extraction_pipeline.py`：分批提取流水线，进度管理，断点续传
- 编写 `skills/style-system/prompts/batch_extract_style.md`：大文本风格提取核心提示词
- 完成 6 部参考小说（术师手册/谁让他修仙的/天启预报/牧者密续/不许没收我的人籍/我师兄实在太稳健了）的风格提取，共 42 个风格文档

### 2026-03-04 (Phase 6: 系统整理)

- 修复路径不一致：
  - 根 SKILL.md 三层架构路径改为实际 `data/novels/{id}/` 下
  - 删除幻影目录 `styles/{作品}/`、`novels/{作品}/`（实际不存在）
  - style-system SKILL.md 层次图、数据文件表统一路径
  - novel-creator/reviewer SKILL.md 文件访问路径修正
  - compose_style.md / batch_extract_style.md / initialize_style.md 路径修正
  - tools/README.md 路径修正
- 删除幻影引用 `craft/tropes/`（从未创建，已从 initialize_style.md 等移除）
- 新增内容：
  - 根 SKILL.md 新增"已有风格数据"表（6部作品 × 7文档）
  - 根 SKILL.md Python 工具表补全 text_chunker.py + style_extraction_pipeline.py
  - novel-creator SKILL.md 新增"前置条件"表
  - novel-reviewer SKILL.md 文件访问表补全（参考风格、角色、世界观）
- 更新 PLAN.md：Phase 5.5/6 完成记录 + Phase 7/8 规划
### 2026-03-04 (Phase 7 部分: 端到端验证)

- 创建 test_novel 项目（《公司里的术师》）：初始化 → 大纲(1篇2节7章) → 3角色(陈明/赵磊/林悠) → 风格合成 → 写第1章(~3440字) → 审查(88/100, 0 AI痕迹) → 修复格式
- 端到端流程验证通过（Pipeline V2 步骤 1-5）
- 风格数据重组：
  - 42个参考风格文档从 `data/novels/{id}/styles/` 迁移到 `data/reference_styles/{作品名}/`
  - 删除所有参考小说中间数据（chunks/batch_results/progress.json ~3.5MB）
  - 全文件路径引用更新：SKILL.md × 4 + prompts × 2 + tools/README.md + README.md
  - `data/novels/` 目录现在只包含用户自己的小说项目

### 2026-03-04 (Phase 7.5: 世界观系统扩展)

- **架构修正**: 世界观从"只有实体列表"扩展为 rules + timeline + terminology + entities 四部分
- **Bug 修复**: `context_builder._get_world_rules()` 原来读取不存在的 `world/rules.yaml` 和 `worldbuilding_rules.md`，世界观数据从未进入写作上下文 → 重写为加载 rules.md + world_query.py 实体/关系
- 新增 `data/novels/test_novel/world/rules.md`：力量体系、社会规则、物理法则、禁忌与未知
- 新增 `data/novels/test_novel/world/timeline.md`：关键事件时间线
- 新增 `data/novels/test_novel/world/terminology.md`：9 个核心术语
- 更新 `tools/init_project.py`：初始化时创建 rules.md / timeline.md / terminology.md 骨架
- 更新文档：SKILL.md(v5.1) + novel-manager SKILL.md + README.md(v5.1) + PLAN.md