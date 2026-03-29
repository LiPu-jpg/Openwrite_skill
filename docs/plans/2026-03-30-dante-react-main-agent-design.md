# Dante ReAct Main Agent Design

**Goal:** 把 `openwrite agent` 重构为长期会话式主 agent，并以 `openwrite dante` 作为唯一对外主入口；主 agent 采用 ReAct 对话循环，orchestrator 降为受限高层动作层，继续负责阶段门禁与状态推进。

## Decision

- 主入口命名为 `Dante`，启动命令是 `openwrite dante`。
- `openwrite goethe` 继续保留，定位为建书/立项引导入口。
- `openwrite write`、`openwrite review`、`openwrite multi-write` 保留为直达命令。
- `openwrite agent` 不再作为对外主命令；实现上可删除或降为内部兼容层，但用户文档不再把它作为主心智。

## Architecture

- `SessionReActAgent`
  - 长会话对话主控。
  - 维护用户对话、会话工作记忆、最近读取的关键文档、当前任务焦点。
  - 可以直接读文件、做低风险写入、调用轻量工具与用户讨论。
- `OrchestratorRuntime`
  - 复用现有 [tools/agent/orchestrator.py](../../tools/agent/orchestrator.py) 的书级状态机能力。
  - 不再作为 CLI 主入口，而是 Dante 可调用的高层 action 层。
  - 继续承担阶段门禁、preflight、workflow 推进、状态恢复。
- `Specialized Subagents`
  - 写作主执行器仍然是 `multi-write` / `WriterAgent` / `ReviewerAgent` 这套链路。
  - 大纲扩写、角色/概念补全文档、状态结算等继续作为局部执行能力存在。
- `Tool Executors`
  - 现有 [tools/cli.py](../../tools/cli.py) 里的 23 个 executors 继续存在。
  - 但大多数不再直接暴露给 Dante；优先通过 orchestrator actions 或明确白名单暴露。

## Responsibilities

### Dante 直接负责

- 长会话聊天与意图理解。
- 读取 canonical 文档并与用户讨论。
- 低风险写入：
  - `data/planning/ideation.md`
  - `data/planning/ideation_summary.md`
  - 未确认的 planning 文档
  - `data/workflows/agent_session.yaml`
- 轻量工具调用：
  - `get_status`
  - `get_context`
  - `list_chapters`
  - `get_truth_files`
  - `query_world`
  - `get_world_relations`

### 仍然必须经过 orchestrator 的动作

- 记录与确认 ideation summary
- 生成与确认 foundation
- 生成与确认 outline scope
- 章节 preflight
- 委派写作
- 委派审查
- 推进 `book_state.yaml`
- 推进 `wf_ch_*.yaml`
- 会话恢复与阶段恢复

### 继续由 subagent 承担的动作

- `multi-write` 写章
- 深度 `review`
- 角色/概念/世界补全
- 状态结算与真相文件更新

## State Model

系统显式维护三层状态：

1. `session memory`
   - 解决“我们刚才聊到哪”。
   - 只服务 Dante 会话。
2. `book_state`
   - 解决“这本书现在在哪个阶段”。
   - 继续落在 `data/workflows/book_state.yaml`。
3. `canonical documents`
   - 解决“真实内容是什么”。
   - 继续以 `src/*` 与 `data/world/*` 为长期真源。

### Session Memory Shape

建议新增 `data/workflows/agent_session.yaml`，结构包含：

- `session_id`
- `active_agent = "dante"`
- `conversation_summary`
- `recent_turns`
- `working_memory`
- `open_questions`
- `recent_files`
- `last_action`
- `compression_markers`
- `updated_at`

### Compression Policy

- 不保存整段原始会话。
- 默认只保留最近 `6-10` 轮原文在 `recent_turns`。
- 超过轮数阈值或字符阈值时自动压缩：
  - 将旧轮次合并进 `conversation_summary`
  - 更新 `compression_markers`
  - 截断 `recent_turns`
- Dante 构造上下文时的读取优先级：
  1. `book_state`
  2. `working_memory`
  3. `conversation_summary`
  4. `recent_turns`
  5. 必要 canonical 文档

## Interaction Model

### CLI

- `openwrite dante`
  - 启动长期会话
  - 进入类似 `goethe` 的交互式 prompt
  - 自动恢复上次会话
- `openwrite goethe`
  - 继续负责引导建书
- `openwrite write` / `review` / `multi-write`
  - 继续负责非会话直达操作

### Startup / Resume

Dante 启动时按顺序恢复：

1. 读取 `book_state.yaml`
2. 读取 `agent_session.yaml`
3. 读取当前相关 canonical 文档
4. 生成一句恢复提示，例如：
   - “上次停在 ideation summary 待确认。”
   - “当前处于 chapter_preflight，目标章节 ch_007。”

### Conversation Loop

Dante 每轮可做三类动作：

- 仅对话与讨论
- 直接文件/轻工具操作
- 调用 orchestrator action 或 subagent

原则：

- 能在主 agent 内完成的讨论，不滥派 subagent
- 影响长期状态的动作必须走 orchestrator
- 明确的生产型任务交给 subagent

## Tool Exposure

### Dante Direct Tools

- 文件读取
- 低风险文件写入
- `get_status`
- `get_context`
- `list_chapters`
- `get_truth_files`
- `query_world`
- `get_world_relations`

### Dante Action Layer

建议把现有 orchestrator 能力包装为以下高层 actions：

- `record_ideation`
- `summarize_ideation`
- `confirm_ideation_summary`
- `generate_foundation_draft`
- `confirm_foundation`
- `generate_outline_draft`
- `confirm_outline_scope`
- `run_chapter_preflight`
- `delegate_chapter_write`
- `delegate_chapter_review`
- `advance_book_state`
- `resume_session`

这些 action 对 Dante 来说表现为“工具”，但内部继续调用现有 orchestrator、workflow、preflight 和 CLI executors。

## Error Handling

- 会话文件损坏时：
  - 重建空的 `agent_session.yaml`
  - 不覆盖 `book_state` 和 canonical 文档
- `book_state` 与 `agent_session` 冲突时：
  - 以 `book_state` 为阶段真相
  - Dante 在恢复提示里说明冲突并请求确认
- LLM 调用失败时：
  - 保留当前 session 状态
  - 不推进 `book_state`
  - 允许用户继续对话或重试
- orchestrator action 失败时：
  - 写回 `last_action` 与失败原因
  - 不让 Dante 伪造成功推进

## Testing Strategy

- CLI 层：
  - `openwrite dante` 启动、退出、恢复
  - `openwrite agent` 退场或拒绝
- session 层：
  - `agent_session.yaml` 创建、恢复、压缩、损坏恢复
- action 层：
  - Dante 通过 action 完成 ideation summary / outline gate / preflight / delegate write
- integration：
  - Dante 聊天数轮后压缩 session
  - Dante 能在恢复后继续推进
  - Dante 与 `book_state.yaml`、`wf_ch_*.yaml` 一致

## Migration

- 第一步：新增 Dante 会话层，不立即拆毁现有 orchestrator。
- 第二步：把 `openwrite dante` 接到 ReAct 长会话。
- 第三步：把 orchestrator 从 CLI 主入口降级为内部 action 层。
- 第四步：从 README 和 SKILL 文档里移除 `openwrite agent` 主入口叙述。

## Non-Goals

- 不在这次重构里推翻 `WriterAgent` / `ReviewerAgent` / `multi-write`。
- 不把全部 23 个工具直接开放给 Dante。
- 不把 `goethe` 合并进 Dante；二者仍保留不同职责。
