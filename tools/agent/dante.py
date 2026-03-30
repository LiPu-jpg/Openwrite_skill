"""Dante 长会话主 Agent。"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .book_state import BookStage, BookState, BookStateStore
from .react import ReActAgent
from .session_state import DanteSessionState, SessionStateStore, SessionTurn
from ..goethe import build_prompt_session, is_exit_command
from ..llm import LLMClient, LLMConfig

DEFAULT_DANTE_SYSTEM_PROMPT = (
    "你是 OpenWrite 的 Dante，长期会话主 Agent。"
    "你负责持续记住上下文、帮助用户汇总想法、确认设定、推进写作。"
    "优先保持对话连续性，不要把自己当成一次性 wizard。"
)


@dataclass
class DanteStartupSnapshot:
    session_state: DanteSessionState
    book_state: BookState
    recovery_prompt: str


@dataclass
class DanteRunResult:
    success: bool
    exit_reason: str = ""
    turns_processed: int = 0
    startup: DanteStartupSnapshot | None = None


class DanteChatAgent:
    def __init__(
        self,
        project_root: Path,
        novel_id: str,
        *,
        react_agent: Any | None = None,
        session_store: SessionStateStore | None = None,
        book_state_store: BookStateStore | None = None,
        prompt_session_factory: Callable[[], Any] | None = None,
        llm_client_factory: Callable[[], LLMClient] | None = None,
        tool_executors: dict[str, Callable[[dict[str, Any]], Any]] | None = None,
        prompt_text: str = "\n🕯️ Dante> ",
    ):
        self.project_root = Path(project_root).resolve()
        self.novel_id = novel_id
        self.session_store = session_store or SessionStateStore(self.project_root, novel_id)
        self.book_state_store = book_state_store or BookStateStore(
            self.project_root, novel_id
        )
        self.prompt_session_factory = (
            prompt_session_factory
            or (lambda: build_prompt_session(prompt_style={"prompt": "#ansibrightblue bold"}))
        )
        self.llm_client_factory = llm_client_factory or self._build_default_llm_client
        self.tool_executors = tool_executors or {}
        self.prompt_text = prompt_text
        self._react_agent = react_agent
        self._react_agent_factory = (
            self._build_default_react_agent if react_agent is None else None
        )

        if self._react_agent is not None and self.tool_executors and hasattr(
            self._react_agent, "_register_tool_executors"
        ):
            self._react_agent._register_tool_executors(self.tool_executors)

        self.session_state: DanteSessionState | None = None
        self.book_state: BookState | None = None
        self.recovery_prompt: str = ""
        self.startup_snapshot: DanteStartupSnapshot | None = None

    def startup(self) -> DanteStartupSnapshot:
        session_state = self.session_store.load_or_create()
        book_state = self.book_state_store.load_or_create()
        self.session_state = session_state
        self.book_state = book_state
        self.recovery_prompt = self.build_recovery_prompt()
        self.startup_snapshot = DanteStartupSnapshot(
            session_state=session_state,
            book_state=book_state,
            recovery_prompt=self.recovery_prompt,
        )
        return self.startup_snapshot

    def build_recovery_prompt(self) -> str:
        session_state = self._require_session_state()
        book_state = self._require_book_state()

        lines = [
            "Dante 已恢复，可以继续上次的长会话。",
            f"会话: {session_state.session_id} / active_agent={session_state.active_agent}",
            f"当前阶段: {book_state.stage.value}",
            (
                "当前篇/节/章: "
                f"{book_state.current_arc or '未设置'} / "
                f"{book_state.current_section or '未设置'} / "
                f"{book_state.current_chapter or '未设置'}"
            ),
            f"当前章: {book_state.current_chapter or '未设置'}",
        ]

        if book_state.pending_confirmation:
            lines.append(f"待确认: {book_state.pending_confirmation}")
        if book_state.blocking_reason:
            lines.append(f"阻塞: {book_state.blocking_reason}")
        if book_state.last_agent_action:
            lines.append(f"最近动作: {book_state.last_agent_action}")
        if session_state.conversation_summary:
            lines.append(f"会话摘要: {session_state.conversation_summary}")
        if session_state.working_memory:
            memory_bits = ", ".join(
                f"{key}={value}" for key, value in session_state.working_memory.items()
            )
            lines.append(f"工作记忆: {memory_bits}")
        if session_state.open_questions:
            lines.append("未决问题: " + "；".join(session_state.open_questions))
        if session_state.recent_files:
            lines.append("最近文件: " + "；".join(session_state.recent_files))
        return "\n".join(lines)

    def run(self) -> DanteRunResult:
        startup = self.startup()
        session = self.prompt_session_factory()
        react_agent = self._get_react_agent()

        print("\n" + "=" * 50)
        print("   OpenWrite Dante 长会话主 Agent")
        print("   (输入 '退出'、'quit'、'exit' 或 'q' 可结束对话)")
        print("=" * 50)
        print(startup.recovery_prompt)

        turns_processed = 0
        while True:
            try:
                user_input = session.prompt(self.prompt_text).strip()
            except KeyboardInterrupt:
                state = self._require_session_state()
                state.last_action = "keyboard_interrupt"
                self.session_store.save(self._require_session_state())
                return DanteRunResult(
                    success=True,
                    exit_reason="keyboard_interrupt",
                    turns_processed=turns_processed,
                    startup=startup,
                )

            if not user_input:
                continue

            if is_exit_command(user_input):
                state = self._require_session_state()
                state.last_action = "exit"
                self.session_store.save(state)
                print("\n好的，随时欢迎回来！")
                return DanteRunResult(
                    success=True,
                    exit_reason=user_input,
                    turns_processed=turns_processed,
                    startup=startup,
                )

            self._append_user_turn(user_input)
            state = self._require_session_state()
            state.last_action = "chat"
            response_text = self._run_react_agent(react_agent, user_input)
            if response_text:
                self._append_assistant_turn(response_text)
                print(f"\n🤖 Dante: {response_text}")
            self.session_store.save(self._require_session_state())
            turns_processed += 1

    def _build_default_llm_client(self) -> LLMClient:
        return LLMClient(LLMConfig.from_env())

    def _build_default_react_agent(self) -> ReActAgent:
        client = self.llm_client_factory()
        return ReActAgent(
            client=client,
            model=client.config.model,
            tools=[],
            system_prompt=DEFAULT_DANTE_SYSTEM_PROMPT,
            max_turns=20,
        )

    def _get_react_agent(self) -> Any:
        if self._react_agent is None:
            self._react_agent = self._react_agent_factory()
            if self.tool_executors and hasattr(self._react_agent, "_register_tool_executors"):
                self._react_agent._register_tool_executors(self.tool_executors)
        return self._react_agent

    def _run_react_agent(self, react_agent: Any, instruction: str) -> str:
        result = react_agent.run(instruction)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        if result is None:
            return ""
        if isinstance(result, str):
            return result.strip()
        if hasattr(result, "content"):
            content = getattr(result, "content", "")
            return str(content).strip()
        if isinstance(result, dict):
            content = result.get("content", "")
            return str(content).strip()
        return str(result).strip()

    def _append_user_turn(self, content: str) -> None:
        state = self._require_session_state()
        state.recent_turns.append(SessionTurn(role="user", content=content))

    def _append_assistant_turn(self, content: str) -> None:
        state = self._require_session_state()
        state.recent_turns.append(SessionTurn(role="assistant", content=content))

    def _require_session_state(self) -> DanteSessionState:
        if self.session_state is None:
            raise RuntimeError("Dante session has not been started")
        return self.session_state

    def _require_book_state(self) -> BookState:
        if self.book_state is None:
            raise RuntimeError("Dante book state has not been started")
        return self.book_state


def run_dante() -> int:
    project_root = Path.cwd()
    config_path = project_root / "novel_config.yaml"
    if not config_path.exists():
        print("未找到 novel_config.yaml，请先运行 openwrite init")
        return 1

    import yaml

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    novel_id = config.get("novel_id")
    if not novel_id:
        print("novel_config.yaml 缺少 novel_id")
        return 1

    agent = DanteChatAgent(project_root=project_root, novel_id=novel_id)
    result = agent.run()
    return 0 if result.success else 1
