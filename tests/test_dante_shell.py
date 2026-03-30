from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tools.agent.book_state import BookStage
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
    def __init__(self, responses: list[str] | None = None):
        self.instructions: list[str] = []
        self.responses = responses or ["收到"]

    def run(self, instruction: str, **kwargs):
        self.instructions.append(instruction)
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
