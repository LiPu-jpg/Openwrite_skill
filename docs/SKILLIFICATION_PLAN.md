# OpenWrite Skill 化计划

## 一、现状调研

### 1.1 已有的 CLI 命令（10个）

| 命令 | 文件 | 说明 |
|------|------|------|
| `openwrite init` | `cli.py:_cmd_init` | 初始化项目 |
| `openwrite write` | `cli.py:_cmd_write` | 写章节 |
| `openwrite review` | `cli.py:_cmd_review` | 审查章节 |
| `openwrite context` | `cli.py:_cmd_context` | 构建上下文 |
| `openwrite style` | `cli.py:_cmd_style` | 风格管理 |
| `openwrite wizard` | `cli.py:_cmd_wizard` | 交互引导 |
| `openwrite radar` | `cli.py:_cmd_radar` | 市场分析 |
| `openwrite status` | `cli.py:_cmd_status` | 查看状态 |
| `openwrite agent` | `cli.py:_cmd_agent` | ReAct Agent |
| (style extract 内) | `_cmd_style_extract` | 提取风格 |

### 1.2 已有的 ReAct Agent 工具（9个）

| 工具 | 说明 |
|------|------|
| `write_chapter` | 写章节 |
| `review_chapter` | 审查章节 |
| `get_status` | 获取状态 |
| `get_context` | 获取上下文 |
| `list_chapters` | 列出章节 |
| `create_outline` | 创建大纲 |
| `create_character` | 创建角色 |
| `get_truth_files` | 读取真相文件 |
| `update_truth_file` | 更新真相文件 |

### 1.3 已有的 Skills（5个）

| Skill | 说明 |
|-------|------|
| `novel-creator` | 写作流程 |
| `novel-manager` | 数据管理 |
| `novel-reviewer` | 审查润色 |
| `style-system` | 风格系统 |
| `wizard-agent` | 引导Agent |

---

## 二、待 Skill 化 / CLI 化的功能

### 2.1 高优先级（Agent 常用但缺失）

| 工具文件 | 功能 | CLI | Agent工具 | Skill | 说明 |
|----------|------|-----|-----------|-------|------|
| `foreshadowing_manager.py` | 伏笔DAG | ❌ | ❌ | ❌ | 核心功能，完全未暴露 |
| `world_query.py` | 世界观查询 | ✅CLI | ❌ | ❌ | 有CLI但无Agent工具 |
| `state_validator.py` | 状态验证 | ❌ | ❌ | ❌ | 验证真相文件一致性 |
| `workflow_scheduler.py` | 流程调度 | ❌ | ❌ | ❌ | 写作流程状态管理 |

### 2.2 中优先级（功能完整但未暴露）

| 工具文件 | 功能 | CLI | Agent工具 | Skill | 说明 |
|----------|------|-----|-----------|-------|------|
| `dialogue_fingerprint.py` | 对话指纹 | ❌ | ❌ | ❌ | 检测对话AI味 |
| `post_validator.py` | 后置验证 | ❌ | ❌ | ❌ | 零成本规则检测 |
| `data_queries.py` | 数据查询 | ❌ | ❌ | ❌ | 通用数据查询 |

### 2.3 低优先级（辅助功能）

| 工具文件 | 功能 | CLI | Agent工具 | Skill | 说明 |
|----------|------|-----|-----------|-------|------|
| `text_chunker.py` | 文本切割 | ❌ | ❌ | ❌ | 大文本智能切割 |
| `progressive_compressor.py` | 渐进压缩 | ❌ | ❌ | ❌ | 章→节→篇三级压缩 |
| `file_ops.py` | 文件操作 | ❌ | ❌ | ❌ | 沙箱安全读写 |

---

## 三、Skill 化计划

### Phase 1: 核心功能 Skill 化（高优先级）

#### 3.1.1 伏笔管理系统

**文件**: `skills/foreshadowing-system/SKILL.md`

**功能**:
- 创建伏笔节点
- 查询待回收伏笔
- 更新伏笔状态
- 环检测验证
- 按权重/层级过滤

**Agent 工具**:
```python
ToolDefinition(
    name="create_foreshadowing",
    description="创建伏笔节点",
    parameters={
        "content": "伏笔内容",
        "weight": "权重(1-10)",
        "layer": "主线/支线",
        "target_chapter": "预期回收章节",
    }
)

ToolDefinition(
    name="list_foreshadowing",
    description="列出伏笔，可按状态/权重过滤",
    parameters={
        "status": "待收/已收/埋伏",
        "min_weight": "最小权重",
    }
)

ToolDefinition(
    name="update_foreshadowing",
    description="更新伏笔状态",
    parameters={
        "hook_id": "伏笔ID",
        "status": "新状态",
    }
)
```

#### 3.1.2 世界查询系统

**文件**: `skills/world-query/SKILL.md`

**功能**:
- 列出所有实体
- 查询实体详情
- 关系图谱
- 按类型筛选

**Agent 工具**:
```python
ToolDefinition(
    name="query_world",
    description="查询世界观实体",
    parameters={
        "entity_id": "实体ID（可选）",
        "type": "类型筛选（可选）",
    }
)

ToolDefinition(
    name="get_world_relations",
    description="获取关系图谱",
    parameters={}
)
```

#### 3.1.3 状态验证系统

**文件**: `skills/truth-validation/SKILL.md`

**功能**:
- 验证真相文件一致性
- 检查角色状态冲突
- 检查战力/资源溢出
- 检查伏笔回收情况

**Agent 工具**:
```python
ToolDefinition(
    name="validate_truth",
    description="验证真相文件一致性",
    parameters={}
)

ToolDefinition(
    name="check_consistency",
    description="检查角色/世界状态一致性",
    parameters={
        "check_type": "角色/战力/伏笔",
    }
)
```

### Phase 2: 质量审核 Skill 化（中优先级）

#### 3.2.1 对话质量系统

**文件**: `skills/dialogue-quality/SKILL.md`

**功能**:
- 对话指纹检测
- 对话AI味分析
- 乒乓球规则检查
- 标签省略检查

#### 3.2.2 后置验证系统

**文件**: `skills/post-validation/SKILL.md`

**功能**:
- 零成本规则检测
- 禁止词检查
- 敏感词检查

### Phase 3: 流程与工具 Skill 化（低优先级）

#### 3.3.1 工作流调度系统

**文件**: `skills/workflow-manager/SKILL.md`

**功能**:
- 查看工作流状态
- 推进工作流阶段
- 恢复中断的工作流

#### 3.3.2 文本处理工具集

**文件**: `skills/text-processing/SKILL.md`

**功能**:
- 文本切割
- 渐进压缩
- 信息密度分析

---

## 四、执行计划

### Week 1: Phase 1（核心功能）

| 日期 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | 伏笔管理系统 Agent 工具 + Skill | `skills/foreshadowing-system/` |
| Day 3-4 | 世界查询系统 Agent 工具 + Skill | `skills/world-query/` |
| Day 5 | 状态验证系统 Agent 工具 + Skill | `skills/truth-validation/` |

### Week 2: Phase 2（质量审核）

| 日期 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | 对话质量系统 | `skills/dialogue-quality/` |
| Day 3-4 | 后置验证系统 | `skills/post-validation/` |
| Day 5 | 补充 CLI 命令 | `openwrite foreshadowing` 等 |

### Week 3: Phase 3（流程与工具）

| 日期 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | 工作流调度系统 | `skills/workflow-manager/` |
| Day 3-4 | 文本处理工具集 | `skills/text-processing/` |
| Day 5 | 文档更新 + 测试 | - |

---

## 五、预期结果

### 5.1 完整的 Agent 工具集

| 类别 | 工具数量 |
|------|----------|
| 写作相关 | 5 |
| 伏笔管理 | 3 |
| 世界查询 | 2 |
| 状态验证 | 2 |
| 对话质量 | 2 |
| 其他 | 3 |
| **总计** | **17+** |

### 5.2 完整的 Skill 导航

```
SKILL.md (根入口)
├── novel-creator/      # ✅ 已有
├── novel-manager/      # ✅ 已有
├── novel-reviewer/     # ✅ 已有
├── style-system/       # ✅ 已有
├── wizard-agent/       # ✅ 已有
├── foreshadowing-system/    # 🆕 Phase 1
├── world-query/        # 🆕 Phase 1
├── truth-validation/   # 🆕 Phase 1
├── dialogue-quality/   # 🆕 Phase 2
├── post-validation/    # 🆕 Phase 2
├── workflow-manager/   # 🆕 Phase 3
└── text-processing/   # 🆕 Phase 3
```

### 5.3 完整的 CLI 命令

```
openwrite init           # ✅
openwrite write          # ✅
openwrite review         # ✅
openwrite context        # ✅
openwrite style          # ✅
openwrite wizard         # ✅
openwrite radar          # ✅
openwrite status         # ✅
openwrite agent          # ✅
openwrite foreshadowing  # 🆕 伏笔管理
openwrite world          # 🆕 世界查询
openwrite validate       # 🆕 状态验证
openwrite workflow       # 🆕 工作流
openwrite compress       # 🆕 压缩工具
```
