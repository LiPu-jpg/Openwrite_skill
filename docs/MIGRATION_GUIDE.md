# OpenWrite → OpenCode Skill 迁移指南

> 将 OpenWrite AI 小说创作系统（10 个 Agent、7 个 Skill 模块、13 个工具）迁移到 OpenCode Skill 格式，实现原生 OpenCode 中的小说创作体验。

---

## 一、架构设计

### 1.1 目录结构

```
opencode_skill/
├── SKILL.md                           # 根技能（项目入口）
├── project-init/                      # 项目初始化
│   └── SKILL.md
├── outline/                           # 大纲管理（四级大纲）
│   ├── SKILL.md
│   ├── prompts/
│   └── workflows/
├── chapter-writing/                   # 章节写作（Pipeline V2）
│   ├── SKILL.md
│   ├── prompts/
│   └── templates/
├── style-system/                      # 风格系统（三层架构）
│   ├── SKILL.md
│   ├── prompts/
│   └── workflows/
├── character/                         # 角色管理
│   ├── SKILL.md
│   └── prompts/
├── foreshadowing/                     # 伏笔 DAG
│   └── SKILL.md
├── world-building/                    # 世界观管理
│   └── SKILL.md
├── context-builder/                   # 上下文构建（内部技能）
│   └── SKILL.md
└── utils/                             # 共享工具
    ├── SKILL.md
    ├── prompts/
    └── workflows/
```

数据文件保持在原位：

```
OpenWrite/
├── craft/                             # 通用写作技法
├── styles/{作品}/                      # 作品风格指纹
├── novels/{作品}/                      # 作品设定
└── data/novels/{id}/                  # 运行时数据
    ├── outline/
    ├── characters/
    ├── world/
    ├── foreshadowing/
    └── manuscript/
```

### 1.2 Agent → Skill 映射

| OpenWrite Agent | OpenCode Skill | 职责 |
|-----------------|----------------|------|
| SkillBasedDirector (1958行) | `SKILL.md`（根技能） | 意图识别、上下文组装、子 Agent 编排 |
| LibrarianAgent (770行) | `chapter-writing/SKILL.md` | 节拍生成、草稿生成、重写 |
| LoreCheckerAgent (461行) | `utils/SKILL.md` (lore_check) | 逻辑审查、一致性检查 |
| StylistAgent (548行) | `utils/SKILL.md` (style_polish) | AI 痕迹检测、风格润色 |
| ReaderAgent (738行) | `style-system/SKILL.md` | 批量阅读、风格提取 |
| StyleDirectorAgent (781行) | `style-system/SKILL.md` | 风格迭代、偏差检测 |
| SimulatorAgent (533行) | `utils/workflows/pipeline_v2.yaml` | 流程编排 |
| InitializerAgent (337行) | `project-init/SKILL.md` | 项目初始化 |
| PipelineV2 (516行) | `utils/workflows/pipeline_v2.yaml` | 工作流定义 |
| DirectorAgent (1906行) | 废弃（被 SkillBasedDirector 替代） | - |

**映射原则：**
- 主控 Agent → 根技能 + 编排逻辑
- 功能 Agent → 独立 Skill
- 辅助 Agent → 内嵌逻辑
- Pipeline → Workflow 定义

### 1.3 概念对照

| OpenWrite 概念 | OpenCode 对应 | 说明 |
|---------------|--------------|------|
| Agent (10个) | Skills (9个) | 主控 Agent 变为根 skill |
| Skill 模块 (7个) | 子 Skills | 功能模块直接映射 |
| Tool Executor (13个工具) | Read/Write 工具 | 文件操作直接使用 OpenCode 工具 |
| Pipeline V2 | Workflow 定义 | 用 YAML 定义多阶段工作流 |
| LLM Router | OpenCode 自带 | 不需要迁移 |
| Session 持久化 | OpenCode 自带 | 不需要迁移 |

---

## 二、核心设计决策

### 2.1 上下文传递：显式文件读取 + context-builder

OpenCode 的子 Agent 之间不共享内存，文件是跨 Agent 通信的最可靠方式。

```markdown
# 调用方式（在其他 skill 中）：
Use superpowers:context-builder with
  novel_id="术师手册",
  context_types=["outline", "characters", "style"],
  chapter_id="ch_003"
```

**渐进式压缩策略（Token 预算分配）：**
- 大纲：300 字符（读取章节级大纲）
- 角色：400 字符（读取角色卡片 YAML，不读详细档案）
- 世界观：200 字符（只读相关实体）
- 伏笔：250 字符（只读待回收伏笔）
- 风格：300 字符（合成三层风格后压缩）

### 2.2 数据访问：约定优于配置

**配置文件：**
```yaml
# novel_config.yaml（项目根目录）
novel_id: 术师手册
style_id: 术师手册
current_arc: arc_001
current_chapter: ch_003
```

**路径约定：**

| 数据类型 | 路径模板 |
|---------|---------|
| 大纲层级 | `data/novels/{novel_id}/data/hierarchy.yaml` |
| 大纲 Markdown | `data/novels/{novel_id}/src/outline.md` |
| 角色卡片 | `data/novels/{novel_id}/data/characters/cards/{id}.yaml` |
| 角色档案 | `data/novels/{novel_id}/src/characters/{id}.md` |
| 世界观实体 | `data/novels/{novel_id}/src/world/entities/{id}.md` |
| 伏笔图 | `data/novels/{novel_id}/data/foreshadowing/dag.yaml` |
| 草稿 | `data/novels/{novel_id}/data/manuscript/{arc_id}/{ch_id}_draft.md` |
| 最终版本 | `data/novels/{novel_id}/data/manuscript/{arc_id}/{ch_id}.md` |
| 通用技法 | `craft/{craft_name}.md` |
| 作品风格 | `styles/{style_id}/fingerprint.yaml` |
| 作品设定 | `data/novels/{novel_id}/src/characters/*.md` + `src/world/*` |

### 2.3 工作流编排：Workflow YAML

Pipeline V2 有明确阶段划分，需要人工审核环节，便于调试和重试。

```yaml
# utils/workflows/pipeline_v2.yaml
stages:
  - name: director
    skill: superpowers:context-builder
  - name: writer
    skill: superpowers:chapter-writing
  - name: reviewer
    skill: superpowers:openwrite-utils#lore_check
  - name: user_review
    type: human_approval
  - name: stylist
    skill: superpowers:openwrite-utils#style_polish
```

### 2.4 技能粒度：按功能模块划分

每个功能模块一个 skill（而非按 Agent 划分），更符合用户心智模型（"写章节" 而非 "调用 LibrarianAgent"），便于独立使用和组合，减少单个 skill 的复杂度。

### 2.5 技能元数据：CSO 原则

description 只描述触发条件，不总结工作流（节省 context window），细节放在 SKILL.md 正文中。

**好的写法：**
```yaml
description: Use when user wants to generate chapter content with beats and drafts. Triggers: "写章节", "生成章节", "续写"
```

**不好的写法：**
```yaml
description: This skill generates chapter content by reading outline, characters, and style, then generates beats and expands them into drafts.
```

---

## 三、技能清单

### 3.1 总览

| 技能名称 | 类型 | 优先级 | 预计工作量 | 依赖 |
|---------|------|--------|-----------|------|
| `openwrite-novel` | 根技能 | P0 | 4h | context-builder |
| `context-builder` | 内部技能 | P0 | 6h | - |
| `chapter-writing` | 核心技能 | P0 | 8h | context-builder |
| `outline-management` | 核心技能 | P1 | 6h | context-builder |
| `character-management` | 核心技能 | P1 | 4h | context-builder |
| `style-system` | 核心技能 | P1 | 8h | context-builder |
| `openwrite-utils` | 工具技能 | P1 | 6h | - |
| `foreshadowing-management` | 辅助技能 | P2 | 4h | context-builder |
| `world-building` | 辅助技能 | P2 | 4h | context-builder |
| `project-init` | 辅助技能 | P2 | 2h | - |

**总工作量：52 小时（约 6.5 个工作日）**

### 3.2 技能依赖关系

```
openwrite-novel (根)
├── context-builder (内部)
│   └── 读取 + 压缩上下文
├── chapter-writing
│   ├── 依赖 context-builder
│   └── 节拍生成 + 草稿生成
├── outline-management
│   ├── 依赖 context-builder
│   └── 四级大纲 + Markdown 同步
├── character-management
│   ├── 依赖 context-builder
│   └── 双层档案 + 时间线
├── style-system
│   ├── 依赖 context-builder
│   └── 三层风格 + 迭代
├── foreshadowing-management
│   └── DAG 管理 + 环检测
├── world-building
│   └── 实体 + 关系 + 冲突检查
├── project-init
│   └── 初始化目录结构
└── openwrite-utils
    ├── lore_check (逻辑审查)
    ├── style_polish (风格润色)
    └── ai_detection (AI 痕迹检测)
```

### 3.3 各技能详细设计

#### P0：openwrite-novel（根技能）

**路径：** `SKILL.md`

```yaml
---
name: openwrite-novel
description: Use when user wants to write novels, manage outlines, characters, world-building, or apply writing styles. Triggers: "写章节", "生成大纲", "创建角色", "世界观", "风格", "伏笔"
---
```

**核心逻辑：**
1. 读取 `novel_config.yaml` → 获取 novel_id, style_id
2. 根据用户输入匹配功能模块并路由到对应子技能
3. 返回结果

#### P0：context-builder（上下文构建器）

**路径：** `context-builder/SKILL.md`（内部技能，不直接暴露给用户）

```yaml
---
name: context-builder
description: Internal skill for assembling novel context with progressive compression. Triggers: (internal use only)
---
```

**输入参数：** `novel_id`, `context_types`, `chapter_id`(可选), `budget`(可选)

**输出格式：**
```yaml
compressed_outline: "..."
character_summary: "..."
world_summary: "..."
active_foreshadowing: "..."
style_instructions: "..."
```

#### P0：chapter-writing（章节写作）

**路径：** `chapter-writing/SKILL.md`

```yaml
---
name: chapter-writing
description: Use when user wants to generate, rewrite, or polish chapter content. Triggers: "写章节", "生成章节", "续写", "重写", "草稿"
---
```

**工作流：**
1. 读取配置 → novel_id, chapter_id
2. 调用 context-builder → 获取上下文
3. 生成节拍列表（基于章节大纲）
4. 扩写为草稿（逐节拍扩写）
5. 保存到 `manuscript/{arc_id}/{chapter_id}_draft.md`

**节拍模板：**
```yaml
# templates/beat_templates.yaml
- beat: 开场      → "承接上章尾声，{protagonist}面对{situation}"
- beat: 发展1     → "{protagonist}采取行动推进目标，遭遇{obstacle}"
- beat: 发展2     → "引入新信息/角色互动"
- beat: 伏笔      → "自然融入伏笔元素"
- beat: 高潮      → "核心冲突升级"
- beat: 收束      → "冲突收束，制造悬念"
```

#### P1：outline-management（大纲管理）

**路径：** `outline/SKILL.md`

```yaml
---
name: outline-management
description: Use when user wants to create, edit, or validate novel outlines with 4-level hierarchy. Triggers: "大纲", "篇纲", "节纲", "章纲", "outline"
---
```

**职责：** 四级大纲管理（总纲 → 篇纲 → 节纲 → 章纲）、Markdown ↔ YAML 双向同步、大纲验证。

**数据格式：**
```yaml
master:
  id: master_001
  title: "总纲标题"
arcs:
  - id: arc_001
    title: "篇纲标题"
    sections:
      - id: sec_001
        title: "节纲标题"
        chapters:
          - id: ch_001
            title: "章纲标题"
```

#### P1：character-management（角色管理）

**路径：** `character/SKILL.md`

```yaml
---
name: character-management
description: Use when user wants to create, query, or update character profiles with dual-layer records and timelines. Triggers: "角色", "人物", "创建角色", "角色时间线"
---
```

**双层档案：**
- **简卡** `cards/角色名.yaml` — id、tier、age、occupation、brief
- **档案** `profiles/角色名.md` — 性格、背景、当前状态

#### P1：style-system（风格系统）

**路径：** `style-system/SKILL.md`

```yaml
---
name: style-system
description: Use when user wants to initialize, compose, or analyze writing styles. Triggers: "风格", "风格初始化", "合成风格", "去AI味", "文风"
---
```

**三层风格架构：**
```
craft/                    # 通用技法（可选参考）
styles/{作品}/             # 作品风格（应当遵循）
novels/{作品}/            # 作品设定（不可违反）
```

**职责：** 风格初始化（问询 + 提取）、风格合成（三层合并）、风格分析（对比 + 建议）、风格迭代（偏差检测 + 收敛）。

#### P1：openwrite-utils（工具集）

**路径：** `utils/SKILL.md`

```yaml
---
name: openwrite-utils
description: Utility skills for lore checking, style polishing, and AI detection. Triggers: "检查", "润色", "AI痕迹"
---
```

**子功能：**
- **Lore Check** — 角色一致性、时间线冲突、世界观规则违反
- **Style Polish** — AI 痕迹检测、节奏验证、声音一致性
- **AI Detection** — AI 常用词汇检测、不自然表达检测、改进建议

#### P2：foreshadowing-management（伏笔管理）

**路径：** `foreshadowing/SKILL.md` | 伏笔节点 CRUD、DAG 环检测与路径查询、待回收伏笔查询 | 4h

#### P2：world-building（世界观）

**路径：** `world-building/SKILL.md` | 实体管理、关系管理、冲突检查 | 4h

#### P2：project-init（项目初始化）

**路径：** `project-init/SKILL.md` | 创建目录结构、初始化配置、创建初始角色 | 2h

---

## 四、实施计划

### Week 1：核心骨架（P0，18h）

**目标：** 用户能够生成章节草稿

| 任务 | 工作量 |
|-----|--------|
| 根技能 `openwrite-novel` | 4h |
| 上下文构建器 `context-builder` | 6h |
| 章节写作 `chapter-writing` | 8h |

**验证：** 用户说"写第3章" → 系统生成草稿并保存到 `manuscript/ch_003_draft.md`

### Week 2：核心功能（P1，24h）

**目标：** 用户能够创建大纲和角色

| 任务 | 工作量 |
|-----|--------|
| 大纲管理 `outline-management` | 6h |
| 角色管理 `character-management` | 4h |
| 风格系统 `style-system` | 8h |
| 工具集 `openwrite-utils` | 6h |

**验证：**
- 用户说"创建李逍遥角色" → 生成角色卡片和档案
- 用户说"创建篇纲'蜀山篇'" → 生成四级大纲结构

### Week 3：完整流程（P2，10h）

**目标：** Pipeline V2 + 辅助功能

| 任务 | 工作量 |
|-----|--------|
| Pipeline V2 工作流 | 包含在 utils |
| 伏笔管理（可选） | 4h |
| 世界观（可选） | 4h |
| 项目初始化（可选） | 2h |

**验证：** 用户说"写第3章，使用完整流程" → Director → Writer → Reviewer → 用户审核 → Stylist

---

## 五、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| **上下文丢失**（子 Agent 无法访问父 Agent 上下文） | 使用显式文件读取 + `context-builder` 统一构建 |
| **工作流中断**（Pipeline V2 跨会话） | 保存中间状态到文件 + `planning-with-files` 管理 |
| **数据一致性**（多 skill 并发修改） | 单一写入原则 + git 版本控制 + YAML schema 验证 |
| **性能问题**（大量文件读取） | 渐进式压缩 + 按需加载 + 可选缓存 |

---

## 六、成功标准

**功能完整性：**
- 用户能通过自然语言创建小说项目、生成四级大纲、创建角色档案、生成章节草稿、管理伏笔和世界观、应用三层风格

**用户体验：**
- 意图识别准确率 > 90%
- 单次对话完成简单任务（如创建角色）
- 复杂任务流程清晰，错误提示友好

**技术质量：**
- 所有技能符合 OpenCode 格式规范
- description 符合 CSO 原则
- 代码复用率高，数据文件组织清晰

---

## 七、迁移范围

**必须迁移：** 10 个 Agent 的核心能力、7 个 Skill 模块、13 个工具（通过 Read/Write 实现）、Pipeline V2 工作流、三层风格架构、四级大纲层级、双层角色档案、伏笔 DAG、世界观图谱

**不迁移：** FastAPI 路由、Jinja2 模板、前端资源（CSS/JS）、pytest 测试、Web 界面、CLI 命令（不在 skill 范围内）

**OpenCode 自带：** LLM 多模型路由、会话持久化

---

## 八、模板参考

### Skill 基础模板

```yaml
---
name: skill-name
description: Use when [触发条件]. Triggers: "关键词1", "关键词2"
---

# Skill 标题

一句话描述。

## 功能
## 使用方式
## 数据位置
## 示例
```

### Workflow 模板

```yaml
name: 工作流名称
stages:
  - name: stage_1
    skill: superpowers:skill-name
    inputs: [input_var]
    outputs: [output_var]
  - name: user_review
    type: human_approval
    inputs: [output_var]
```

---

## 九、常见问题

**Q：如何处理跨会话任务？**
使用 `planning-with-files`：创建 `task_plan.md` 记录进度，下次会话读取继续。

**Q：如何处理大量上下文？**
渐进式压缩：优先读取摘要信息（角色卡片而非详细档案），使用 `context-builder` 压缩，只读当前章节相关数据。

**Q：如何调试 skill？**
使用 `task(agent="explore")` 测试文件读取，检查生成文件是否符合预期，使用 `lsp_diagnostics` 检查 YAML 语法。

---

## 十、后续优化方向

1. **流式响应** — 草稿生成时的流式输出
2. **多模型支持** — 不同任务使用不同模型（生成用 Kimi，审查用 Claude）
3. **可视化工具** — 世界观图谱、伏笔 DAG 可视化
4. **协作功能** — 多人协作写作
5. **版本管理** — 草稿版本对比、回滚
6. **导出功能** — 导出为 EPUB、PDF 等格式

---

*版本: 1.0 | 创建时间: 2026-03-03 | 预计完成: 2026-03-24（3 周）*
