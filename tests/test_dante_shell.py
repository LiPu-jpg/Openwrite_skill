from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tools.agent.book_state import BookStage
from tools.agent.react import ToolDefinition
from tools.agent.session_state import DanteSessionState, SessionTurn


@dataclass
class FakePromptSession:
    inputs: list[str]

    def __post_init__(self) -> None:
        self.prompts: list[str] = []

    def prompt(self, text: str) -> str:
        self.prompts.append(text)
        if not self.inputs:
            raise AssertionError("prompt() called more times than expected")
        return self.inputs.pop(0)


class FakeReActAgent:
    def __init__(self, responses: list[str] | None = None, error: Exception | None = None):
        self.instructions: list[str] = []
        self.calls: list[dict[str, object]] = []
        self.responses = responses or ["收到"]
        self.error = error

    def run(self, instruction: str, **kwargs):
        self.instructions.append(instruction)
        self.calls.append({"instruction": instruction, "kwargs": kwargs})
        if self.error is not None:
            raise self.error
        if not self.responses:
            return "收到"
        return self.responses.pop(0)


def _write_session_state(project_root: Path, novel_id: str) -> None:
    session_path = (
        project_root / "data" / "novels" / novel_id / "data" / "workflows" / "agent_session.yaml"
    )
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(
        yaml.safe_dump(
            {
                "session_id": "session-123",
                "active_agent": "dante",
                "conversation_summary": "已确认当前题材是都市职场异能。",
                "recent_turns": [
                    {"role": "user", "content": "我想写一个普通上班族觉醒术式的故事"},
                    {"role": "assistant", "content": "我先帮你整理成共识摘要。"},
                ],
                "working_memory": {"topic": "都市职场异能"},
                "open_questions": ["主角是否主动入局"],
                "recent_files": ["src/outline.md"],
                "last_action": "summarize_ideation",
                "compression_markers": [
                    {
                        "compressed_at": "2026-03-30T10:00:00",
                        "dropped_turns": 2,
                        "kept_turns": 2,
                        "reason": "count",
                    }
                ],
                "updated_at": "2026-03-30T10:05:00",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_book_state(project_root: Path, novel_id: str) -> None:
    book_path = (
        project_root / "data" / "novels" / novel_id / "data" / "workflows" / "book_state.yaml"
    )
    book_path.parent.mkdir(parents=True, exist_ok=True)
    book_path.write_text(
        yaml.safe_dump(
            {
                "novel_id": novel_id,
                "stage": BookStage.ROLLING_OUTLINE.value,
                "current_arc": "arc_001",
                "current_section": "sec_001",
                "current_chapter": "ch_006",
                "pending_confirmation": "outline_scope",
                "blocking_reason": "等待用户确认当前可写范围",
                "last_agent_action": "generate_outline_draft",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_dante_startup_loads_session_and_book_state(tmp_path: Path):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: FakePromptSession(["exit"]),
        react_agent=FakeReActAgent(),
    )

    startup = agent.startup()

    assert startup.session_state.session_id == "session-123"
    assert startup.book_state.stage == BookStage.ROLLING_OUTLINE
    assert startup.recovery_prompt.startswith("Dante 已恢复")
    assert "当前章: ch_006" in startup.recovery_prompt
    assert agent.session_state.session_id == "session-123"
    assert agent.book_state.current_chapter == "ch_006"


def test_dante_enters_prompt_loop_and_persists_turns(tmp_path: Path):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    prompt_session = FakePromptSession(["我想先看当前状态", "exit"])
    react_agent = FakeReActAgent(responses=["我已经记住了。"])
    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: prompt_session,
        react_agent=react_agent,
    )

    result = agent.run()

    assert result.success is True
    assert result.exit_reason == "exit"
    assert react_agent.instructions == ["我想先看当前状态"]
    assert prompt_session.prompts
    assert "Dante" in prompt_session.prompts[0]

    persisted = yaml.safe_load(agent.session_store.path.read_text(encoding="utf-8"))
    assert persisted["recent_turns"][-2:] == [
        {"role": "user", "content": "我想先看当前状态"},
        {"role": "assistant", "content": "我已经记住了。"},
    ]
    assert persisted["last_action"] == "exit"


@pytest.mark.parametrize("command", ["quit", "exit", "q", "退出"])
def test_dante_exit_commands_stop_without_tool_turn(tmp_path: Path, command: str):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    prompt_session = FakePromptSession([command])
    react_agent = FakeReActAgent()
    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: prompt_session,
        react_agent=react_agent,
    )

    result = agent.run()

    assert result.success is True
    assert result.exit_reason == command
    assert react_agent.instructions == []
    assert yaml.safe_load(agent.session_store.path.read_text(encoding="utf-8"))["recent_turns"][-1]["role"] == "assistant"


def test_dante_recovery_prompt_mentions_loaded_state(tmp_path: Path):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: FakePromptSession(["exit"]),
        react_agent=FakeReActAgent(),
    )

    agent.startup()
    prompt = agent.build_recovery_prompt()

    assert "rolling_outline" in prompt
    assert "ch_006" in prompt
    assert "outline_scope" in prompt
    assert "都市职场异能" in prompt
    assert "主角是否主动入局" in prompt


def test_dante_passes_session_memory_and_book_state_into_react(
    tmp_path: Path,
):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    prompt_session = FakePromptSession(["继续推进", "exit"])
    react_agent = FakeReActAgent(responses=["已接住上下文。"])
    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: prompt_session,
        react_agent=react_agent,
        action_executors={
            "summarize_ideation": lambda args: {"ok": True, "action": "summarize_ideation"}
        },
    )

    result = agent.run()

    assert result.success is True
    assert react_agent.instructions == ["继续推进"]
    assert react_agent.calls[0]["kwargs"]["context_messages"]
    context_text = "\n".join(
        message.content for message in react_agent.calls[0]["kwargs"]["context_messages"]
    )
    assert "会话摘要" in context_text
    assert "最近轮次" in context_text
    assert "rolling_outline" in context_text
    assert "ch_006" in context_text


def test_dante_default_react_agent_has_direct_and_action_tool_surface(
    tmp_path: Path,
):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: FakePromptSession(["exit"]),
        react_agent=None,
        tool_executors={
            "get_status": lambda args: {"ok": True},
            "get_context": lambda args: {"ok": True},
            "list_chapters": lambda args: {"ok": True},
            "get_truth_files": lambda args: {"ok": True},
            "query_world": lambda args: {"ok": True},
            "get_world_relations": lambda args: {"ok": True},
        },
        action_executors={
            "summarize_ideation": lambda args: {"ok": True, "action": "summarize_ideation"},
            "confirm_ideation_summary": lambda args: {"ok": True, "action": "confirm_ideation_summary"},
            "generate_outline_draft": lambda args: {"ok": True, "action": "generate_outline_draft"},
            "run_chapter_preflight": lambda args: {"ok": True, "action": "run_chapter_preflight"},
        },
    )

    react_agent = agent._get_react_agent()

    tool_names = {tool.name for tool in react_agent.tools}
    assert "get_status" in tool_names
    assert "summarize_ideation" in tool_names
    assert hasattr(react_agent, "_tool_get_status")
    assert hasattr(react_agent, "_tool_summarize_ideation")


def test_dante_persists_user_turn_when_react_raises(tmp_path: Path):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    prompt_session = FakePromptSession(["我想继续推进"])
    react_agent = FakeReActAgent(error=RuntimeError("boom"))
    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: prompt_session,
        react_agent=react_agent,
    )

    with pytest.raises(RuntimeError, match="boom"):
        agent.run()

    persisted = yaml.safe_load(agent.session_store.path.read_text(encoding="utf-8"))
    assert persisted["recent_turns"][-1] == {
        "role": "user",
        "content": "我想继续推进",
    }


def test_dante_model_context_excludes_recovery_prompt_but_keeps_structured_state(
    tmp_path: Path,
):
    from tools.agent.dante import DanteChatAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    prompt_session = FakePromptSession(["查看当前状态", "exit"])
    react_agent = FakeReActAgent(responses=["收到"])
    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: prompt_session,
        react_agent=react_agent,
    )

    result = agent.run()

    assert result.success is True
    assert react_agent.instructions == ["查看当前状态"]
    context_text = "\n".join(
        message.content for message in react_agent.calls[0]["kwargs"]["context_messages"]
    )
    assert "Dante 已恢复，可以继续上次的长会话。" not in context_text
    assert "会话: session-123 / active_agent=dante" not in context_text
    assert "会话摘要" in context_text
    assert "最近轮次" in context_text
    assert "rolling_outline" in context_text
    assert "等待用户确认当前可写范围" in context_text
    assert "generate_outline_draft" in context_text
    assert "current" not in context_text


def test_dante_injected_real_react_agent_gets_tool_definitions_and_surface(
    tmp_path: Path,
):
    from tools.agent.dante import DanteChatAgent
    from tools.agent.react import ReActAgent

    _write_session_state(tmp_path, "demo")
    _write_book_state(tmp_path, "demo")

    class RecordingClient:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        def chat_with_tools(self, messages, tools, **kwargs):
            self.calls.append({"messages": list(messages), "tools": list(tools)})
            return type("Resp", (), {"content": "退出", "tool_calls": []})()

    react_agent = ReActAgent(
        client=RecordingClient(),
        model="demo",
        tools=[
            ToolDefinition(
                name="get_status",
                description="旧描述",
                parameters={
                    "type": "object",
                    "properties": {"legacy": {"type": "string"}},
                },
            ),
            ToolDefinition(
                name="retain_me",
                description="保留的外部工具",
                parameters={"type": "object", "properties": {}},
            ),
        ],
        system_prompt="系统提示",
    )

    agent = DanteChatAgent(
        project_root=tmp_path,
        novel_id="demo",
        prompt_session_factory=lambda **kwargs: FakePromptSession(["exit"]),
        react_agent=react_agent,
        tool_executors={
            "get_status": lambda args: {"ok": True},
            "get_context": lambda args: {"ok": True},
            "list_chapters": lambda args: {"ok": True},
            "get_truth_files": lambda args: {"ok": True},
            "query_world": lambda args: {"ok": True},
            "get_world_relations": lambda args: {"ok": True},
        },
        action_executors={
            "summarize_ideation": lambda args: {"ok": True, "action": "summarize_ideation"},
            "confirm_ideation_summary": lambda args: {"ok": True, "action": "confirm_ideation_summary"},
            "generate_outline_draft": lambda args: {"ok": True, "action": "generate_outline_draft"},
            "run_chapter_preflight": lambda args: {"ok": True, "action": "run_chapter_preflight"},
        },
    )

    tool_map = {tool.name: tool for tool in react_agent.tools}
    assert tool_map["get_status"].description == "获取项目状态概览。"
    assert tool_map["get_status"].parameters == {
        "type": "object",
        "properties": {},
    }
    assert tool_map["summarize_ideation"].description == "汇总当前收集到的想法，生成会话共识摘要。"
    assert tool_map["summarize_ideation"].parameters == {
        "type": "object",
        "properties": {},
    }
    assert tool_map["retain_me"].description == "保留的外部工具"
    assert hasattr(react_agent, "_tool_get_status")
    assert hasattr(react_agent, "_tool_summarize_ideation")
