# Dante ReAct Main Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 `openwrite dante` 实现为长期会话式 ReAct 主 agent，并把现有 orchestrator 降为 Dante 可调用的受限动作层。

**Architecture:** 新增会话层 `DanteSession` 管理 prompt loop、session memory 和压缩；复用现有 `ReActAgent` 作为工具调用循环；新增 orchestrator action adapter，把 ideation、foundation、outline、preflight、write、review 等高风险动作包装成 Dante 工具。CLI 主入口从 `agent` 切到 `dante`，`agent` 退场。

**Tech Stack:** Python, argparse, prompt_toolkit, YAML, Markdown/TOML front matter, pytest

---

### Task 1: 锁定 Dante CLI 入口与旧入口退场测试

**Files:**
- Modify: `tests/test_cli_agent.py`
- Modify: `tools/cli.py`

1. 写失败测试，覆盖 `openwrite dante` 子命令存在、`openwrite agent` 不再作为主入口。
2. 运行 `python3 -m pytest -q tests/test_cli_agent.py -k dante`，确认先失败。
3. 在 `tools/cli.py` 增加 `dante` 命令定义，并让旧 `agent` 明确报错或转内部提示。
4. 再跑同一条测试，确认通过。
5. 提交：
   `git add tests/test_cli_agent.py tools/cli.py && git commit -m "test: lock dante cli entry"`

### Task 2: 新增会话状态存储与压缩测试

**Files:**
- Create: `tests/test_agent_session.py`
- Create: `tools/agent/session_state.py`

1. 写失败测试，覆盖：
   - 创建 `agent_session.yaml`
   - 恢复已有 session
   - 超过阈值后压缩 `recent_turns`
   - 损坏文件自动恢复
2. 运行 `python3 -m pytest -q tests/test_agent_session.py`，确认先失败。
3. 实现 `DanteSessionState` / `SessionMemoryStore`：
   - `conversation_summary`
   - `recent_turns`
   - `working_memory`
   - `compression_markers`
4. 再跑 `python3 -m pytest -q tests/test_agent_session.py`，确认通过。
5. 提交：
   `git add tests/test_agent_session.py tools/agent/session_state.py && git commit -m "feat: add dante session state store"`

### Task 3: 为 Dante 提供 orchestrator action adapter

**Files:**
- Create: `tests/test_dante_actions.py`
- Create: `tools/agent/dante_actions.py`
- Modify: `tools/agent/orchestrator.py`
- Modify: `tools/story_planning.py`

1. 写失败测试，覆盖 Dante action 调用：
   - `summarize_ideation`
   - `confirm_ideation_summary`
   - `generate_outline_draft`
   - `run_chapter_preflight`
2. 运行 `python3 -m pytest -q tests/test_dante_actions.py`，确认先失败。
3. 实现 action adapter，把现有 orchestrator/planning 能力收口为高层动作。
4. 在 `tools/agent/orchestrator.py` 暴露明确的可调用方法，避免 Dante 自己拼底层工具链。
5. 再跑 `python3 -m pytest -q tests/test_dante_actions.py`，确认通过。
6. 提交：
   `git add tests/test_dante_actions.py tools/agent/dante_actions.py tools/agent/orchestrator.py tools/story_planning.py && git commit -m "feat: add dante orchestrator actions"`

### Task 4: 定义 Dante 的工具白名单与 direct file helpers

**Files:**
- Modify: `tools/agent/toolkits.py`
- Modify: `tools/cli.py`
- Modify: `tests/test_agent_tool_runtime.py`

1. 写失败测试，锁定 Dante 直接工具白名单与 action 工具集合。
2. 运行 `python3 -m pytest -q tests/test_agent_tool_runtime.py`，确认先失败。
3. 在 `toolkits.py` 增加 Dante 专用 toolkit/action toolkit 常量。
4. 在 `tools/cli.py` 或配套 helper 中注册 Dante 可用的 direct file tools / action tools。
5. 再跑 `python3 -m pytest -q tests/test_agent_tool_runtime.py`，确认通过。
6. 提交：
   `git add tools/agent/toolkits.py tools/cli.py tests/test_agent_tool_runtime.py && git commit -m "feat: define dante tool layers"`

### Task 5: 实现长期会话 Dante shell

**Files:**
- Create: `tests/test_dante_shell.py`
- Create: `tools/agent/dante.py`
- Modify: `tools/llm/client.py`
- Modify: `tools/goethe.py`

1. 写失败测试，覆盖：
   - Dante 启动时加载 session/book state
   - 进入 prompt loop
   - `exit`/`quit` 正常退出
   - 恢复提示正常生成
2. 运行 `python3 -m pytest -q tests/test_dante_shell.py`，确认先失败。
3. 实现 `DanteChatAgent`：
   - 使用 `prompt_toolkit.PromptSession`
   - 注入 `ReActAgent`
   - 管理启动、恢复、退出
4. 复用 `goethe` 的交互经验，但不要复制旧 `wizard` 心智。
5. 再跑 `python3 -m pytest -q tests/test_dante_shell.py`，确认通过。
6. 提交：
   `git add tests/test_dante_shell.py tools/agent/dante.py tools/llm/client.py tools/goethe.py && git commit -m "feat: add dante interactive shell"`

### Task 6: 把 ReActAgent 接到 Dante 会话层

**Files:**
- Modify: `tools/agent/react.py`
- Modify: `tools/agent/dante.py`
- Modify: `tests/test_agent_react.py`

1. 写失败测试，覆盖 Dante 会话中：
   - 直接聊天
   - 直接工具调用
   - action 工具调用
   - 最近轮次写入 session memory
2. 运行 `python3 -m pytest -q tests/test_agent_react.py tests/test_dante_shell.py`，确认先失败。
3. 在 `ReActAgent` 增加适合长期会话的消息注入/回调接口；不要破坏现有单轮调用。
4. 在 `tools/agent/dante.py` 中把 session memory、tool executors、action executors 和 `ReActAgent` 连起来。
5. 再跑同一组测试，确认通过。
6. 提交：
   `git add tools/agent/react.py tools/agent/dante.py tests/test_agent_react.py tests/test_dante_shell.py && git commit -m "feat: wire react loop into dante"`

### Task 7: 实现启动恢复与主动压缩

**Files:**
- Modify: `tools/agent/session_state.py`
- Modify: `tools/agent/dante.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_dante_shell.py`

1. 写失败测试，覆盖：
   - 达到轮数阈值自动压缩
   - 字符数阈值自动压缩
   - 恢复后最近窗口与 summary 并存
2. 运行 `python3 -m pytest -q tests/test_agent_session.py tests/test_dante_shell.py`，确认先失败。
3. 实现压缩触发器、恢复提示构造器和冲突恢复逻辑。
4. 再跑同一组测试，确认通过。
5. 提交：
   `git add tools/agent/session_state.py tools/agent/dante.py tests/test_agent_session.py tests/test_dante_shell.py && git commit -m "feat: add dante session compression and resume"`

### Task 8: 让 Dante 复用现有 book_state/workflow 门禁

**Files:**
- Modify: `tools/agent/book_state.py`
- Modify: `tools/agent/orchestrator.py`
- Modify: `tools/agent/dante_actions.py`
- Modify: `tests/test_agent_orchestrator.py`

1. 写失败测试，覆盖 Dante 通过 action 层推进：
   - discovery -> foundation
   - summary confirmation gate
   - outline confirmation gate
   - chapter_preflight
2. 运行 `python3 -m pytest -q tests/test_agent_orchestrator.py`，确认先失败。
3. 调整 orchestrator 和 action adapter，确保 Dante 不会绕开 gate 直接推进。
4. 再跑 `python3 -m pytest -q tests/test_agent_orchestrator.py`，确认通过。
5. 提交：
   `git add tools/agent/book_state.py tools/agent/orchestrator.py tools/agent/dante_actions.py tests/test_agent_orchestrator.py && git commit -m "feat: preserve book-state gates under dante"`

### Task 9: 更新 README / SKILL 文档心智

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `skills/goethe-agent/SKILL.md`

1. 写 README/技能文档断言测试，至少覆盖命令名和主入口说明。
2. 运行 `python3 -m pytest -q tests/test_readme_svg.py tests/test_cli_agent.py -k dante`，确认有失败。
3. 把文档改成：
   - `openwrite dante` 是长期会话主入口
   - `openwrite goethe` 是建书引导
   - `write/review/multi-write` 是直达命令
4. 再跑对应测试，确认通过。
5. 提交：
   `git add README.md SKILL.md skills/goethe-agent/SKILL.md tests/test_readme_svg.py tests/test_cli_agent.py && git commit -m "docs: document dante as primary agent"`

### Task 10: 全量验证与清理

**Files:**
- Modify: `tools/cli.py`
- Modify: `tests/test_core.py`
- Modify: `tests/test_integration.py`

1. 跑定向命令烟测：
   - `python3 -m tools.cli dante`
   - `python3 -m tools.cli goethe --help`
   - `python3 -m tools.cli status`
2. 跑全量测试：
   - `python3 -m pytest -q`
3. 修复最后的 CLI 帮助文本、集成测试和兼容残留。
4. 再跑：
   - `python3 -m pytest -q`
5. 提交：
   `git add tools/cli.py tests/test_core.py tests/test_integration.py && git commit -m "test: verify dante main-agent migration"`
