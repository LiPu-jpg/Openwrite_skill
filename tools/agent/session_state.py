"""Dante session state persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import tempfile
from typing import Any

import yaml

MAX_RECENT_TURNS = 6
DEFAULT_ACTIVE_AGENT = "dante"


@dataclass
class DanteSessionState:
    session_id: str
    active_agent: str = DEFAULT_ACTIVE_AGENT
    conversation_summary: str = ""
    recent_turns: list[dict[str, Any]] = field(default_factory=list)
    working_memory: dict[str, Any] = field(default_factory=dict)
    open_questions: list[str] = field(default_factory=list)
    recent_files: list[str] = field(default_factory=list)
    last_action: str = ""
    compression_markers: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = ""


class SessionStateStore:
    def __init__(self, project_root: Path, novel_id: str):
        self.project_root = Path(project_root).resolve()
        self.novel_id = novel_id
        self.path = (
            self.project_root
            / "data"
            / "novels"
            / novel_id
            / "data"
            / "workflows"
            / "agent_session.yaml"
        )

    def load_or_create(self) -> DanteSessionState:
        if not self.path.exists():
            state = self._default_state()
            self.save(state)
            return state

        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except Exception:
            state = self._default_state()
            self.save(state)
            return state

        if not data or not isinstance(data, dict):
            state = self._default_state()
            self.save(state)
            return state

        state = self._from_dict(data)
        if self._compress_if_needed(state):
            self.save(state)
        return state

    def save(self, state: DanteSessionState) -> None:
        self._stamp_updated_at(state)
        self._compress_if_needed(state)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = yaml.safe_dump(
            self._to_dict(state), allow_unicode=True, sort_keys=False
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            delete=False,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)

        temp_path.replace(self.path)

    def _default_state(self) -> DanteSessionState:
        return DanteSessionState(session_id=self.novel_id)

    def _stamp_updated_at(self, state: DanteSessionState) -> None:
        state.updated_at = datetime.now().isoformat()

    def _compress_if_needed(self, state: DanteSessionState) -> bool:
        if len(state.recent_turns) <= MAX_RECENT_TURNS:
            return False

        excess = len(state.recent_turns) - MAX_RECENT_TURNS
        old_turns = state.recent_turns[:excess]
        kept_turns = state.recent_turns[excess:]
        summary_block = "\n".join(self._render_turn(turn) for turn in old_turns)

        if state.conversation_summary:
            state.conversation_summary = f"{state.conversation_summary}\n{summary_block}"
        else:
            state.conversation_summary = summary_block

        state.recent_turns = kept_turns
        state.compression_markers.append(
            {
                "compressed_at": state.updated_at or datetime.now().isoformat(),
                "dropped_turns": len(old_turns),
                "kept_turns": len(kept_turns),
            }
        )
        return True

    def _render_turn(self, turn: dict[str, Any]) -> str:
        role = str(turn.get("role", "unknown"))
        content = str(turn.get("content", ""))
        return f"{role}: {content}".rstrip()

    def _to_dict(self, state: DanteSessionState) -> dict[str, Any]:
        return asdict(state)

    def _from_dict(self, data: dict[str, Any]) -> DanteSessionState:
        return DanteSessionState(
            session_id=str(data.get("session_id", self.novel_id)),
            active_agent=str(data.get("active_agent", DEFAULT_ACTIVE_AGENT)),
            conversation_summary=str(data.get("conversation_summary", "")),
            recent_turns=self._normalize_turns(data.get("recent_turns", [])),
            working_memory=self._normalize_mapping(data.get("working_memory", {})),
            open_questions=self._normalize_str_list(data.get("open_questions", [])),
            recent_files=self._normalize_str_list(data.get("recent_files", [])),
            last_action=str(data.get("last_action", "")),
            compression_markers=self._normalize_marker_list(
                data.get("compression_markers", [])
            ),
            updated_at=str(data.get("updated_at", "")),
        )

    def _normalize_turns(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        turns: list[dict[str, Any]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            turns.append(
                {
                    "role": str(item.get("role", "")),
                    "content": str(item.get("content", "")),
                }
            )
        return turns

    def _normalize_mapping(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return dict(value)

    def _normalize_str_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]

    def _normalize_marker_list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        markers: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                markers.append(dict(item))
        return markers
