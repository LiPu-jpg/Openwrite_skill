"""Dante session state persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import tempfile
from typing import Any, Literal

import yaml

MAX_RECENT_TURNS = 6
MAX_SESSION_BYTES = 4096
MAX_SUMMARY_BYTES = 1024
MAX_TURN_CONTENT_BYTES = 256
DEFAULT_ACTIVE_AGENT = "dante"


@dataclass
class SessionTurn:
    role: str
    content: str


@dataclass
class CompressionMarker:
    compressed_at: str
    dropped_turns: int
    kept_turns: int
    reason: Literal["count", "size"]


@dataclass
class DanteSessionState:
    session_id: str
    active_agent: str = DEFAULT_ACTIVE_AGENT
    conversation_summary: str = ""
    recent_turns: list[SessionTurn] = field(default_factory=list)
    working_memory: dict[str, Any] = field(default_factory=dict)
    open_questions: list[str] = field(default_factory=list)
    recent_files: list[str] = field(default_factory=list)
    last_action: str = ""
    compression_markers: list[CompressionMarker] = field(default_factory=list)
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
        except yaml.YAMLError:
            state = self._default_state()
            self.save(state)
            return state

        if not data or not isinstance(data, dict):
            state = self._default_state()
            self.save(state)
            return state

        state = self._from_dict(data)
        needs_repair = self._needs_schema_upgrade(data) or (
            self._to_dict(state) != self._input_to_canonical_dict(data)
        )
        if needs_repair or self._compress_if_needed(state):
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
        changed = self._compress_by_count(state)
        changed |= self._compress_for_size(state)
        return changed

    def _compress_by_count(self, state: DanteSessionState) -> bool:
        if len(state.recent_turns) <= MAX_RECENT_TURNS:
            return False

        dropped_turns = 0
        while len(state.recent_turns) > MAX_RECENT_TURNS:
            drop_count = len(state.recent_turns) - MAX_RECENT_TURNS
            old_turns = state.recent_turns[:drop_count]
            kept_turns = state.recent_turns[drop_count:]
            summary_block = "\n".join(self._render_turn(turn, MAX_TURN_CONTENT_BYTES) for turn in old_turns)
            state.conversation_summary = self._append_summary(
                state.conversation_summary, summary_block
            )
            state.recent_turns = kept_turns
            dropped_turns += len(old_turns)

        state.compression_markers.append(
            CompressionMarker(
                compressed_at=datetime.now().isoformat(),
                dropped_turns=dropped_turns,
                kept_turns=len(state.recent_turns),
                reason="count",
            )
        )
        return True

    def _compress_for_size(self, state: DanteSessionState) -> bool:
        if self._estimate_size(state) <= MAX_SESSION_BYTES:
            return False

        changed = False
        summary_budget = MAX_SUMMARY_BYTES
        turn_budget = MAX_TURN_CONTENT_BYTES

        while self._estimate_size(state) > MAX_SESSION_BYTES:
            self._compact_text_fields(state, summary_budget, turn_budget)
            changed = True
            if self._estimate_size(state) <= MAX_SESSION_BYTES:
                break

            if summary_budget > 64:
                summary_budget = max(64, summary_budget // 2)
            if turn_budget > 32:
                turn_budget = max(32, turn_budget // 2)

            if summary_budget == 64 and turn_budget == 32:
                break

        if self._estimate_size(state) > MAX_SESSION_BYTES:
            self._compact_metadata_fields(state)
            changed = True

        if self._estimate_size(state) > MAX_SESSION_BYTES:
            self._hard_truncate_state(state)

        if self._estimate_size(state) > MAX_SESSION_BYTES:
            raise ValueError("session state exceeded MAX_SESSION_BYTES after compression")

        state.compression_markers.append(
            CompressionMarker(
                compressed_at=datetime.now().isoformat(),
                dropped_turns=0,
                kept_turns=len(state.recent_turns),
                reason="size",
            )
        )
        return True

    def _compression_reason(self, state: DanteSessionState) -> str | None:
        if len(state.recent_turns) > MAX_RECENT_TURNS:
            return "count"
        if self._estimate_size(state) > MAX_SESSION_BYTES and len(state.recent_turns) > 1:
            return "size"
        return None

    def _append_summary(self, existing: str, addition: str) -> str:
        if not addition:
            return existing
        if not existing:
            return addition
        return f"{existing}\n{addition}"

    def _estimate_size(self, state: DanteSessionState) -> int:
        return len(
            yaml.safe_dump(
                self._to_dict(state), allow_unicode=True, sort_keys=False
            ).encode("utf-8")
        )

    def _render_turn(self, turn: SessionTurn, content_limit: int | None = None) -> str:
        role = turn.role or "unknown"
        content = (
            self._truncate_text(turn.content, content_limit, keep_tail=False)
            if content_limit is not None
            else turn.content
        )
        return f"{role}: {content}".rstrip()

    def _compact_text_fields(
        self, state: DanteSessionState, summary_budget: int, turn_budget: int
    ) -> None:
        state.conversation_summary = self._truncate_text(
            state.conversation_summary, summary_budget, keep_tail=True
        )
        state.recent_turns = [
            SessionTurn(
                role=turn.role,
                content=self._truncate_text(turn.content, turn_budget, keep_tail=False),
            )
            for turn in state.recent_turns
        ]
        state.working_memory = self._compact_mapping(state.working_memory, turn_budget)
        state.open_questions = self._compact_string_list(state.open_questions, turn_budget)
        state.recent_files = self._compact_string_list(state.recent_files, turn_budget)
        state.last_action = self._truncate_text(state.last_action, turn_budget, keep_tail=False)

    def _hard_truncate_state(self, state: DanteSessionState) -> None:
        state.conversation_summary = self._truncate_text(
            state.conversation_summary, 128, keep_tail=True
        )
        if state.recent_turns:
            last_turn = state.recent_turns[-1]
            state.recent_turns = [
                SessionTurn(
                    role=last_turn.role,
                    content=self._truncate_text(last_turn.content, 128, keep_tail=False),
                )
            ]
        else:
            state.recent_turns = []
        state.working_memory = self._compact_mapping(state.working_memory, 64)
        state.open_questions = self._compact_string_list(state.open_questions, 64)
        state.recent_files = self._compact_string_list(state.recent_files, 64)
        state.last_action = self._truncate_text(state.last_action, 64, keep_tail=False)

    def _truncate_text(
        self, text: str, limit: int, *, keep_tail: bool
    ) -> str:
        if limit <= 0 or not text:
            return ""

        encoded = text.encode("utf-8")
        if len(encoded) <= limit:
            return text

        if keep_tail:
            truncated = encoded[-limit:]
        else:
            truncated = encoded[:limit]
        return truncated.decode("utf-8", errors="ignore")

    def _to_dict(self, state: DanteSessionState) -> dict[str, Any]:
        return asdict(state)

    def _input_to_canonical_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        state = self._from_dict(data)
        return self._to_dict(state)

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

    def _needs_schema_upgrade(self, data: dict[str, Any]) -> bool:
        required_keys = {
            "session_id",
            "active_agent",
            "conversation_summary",
            "recent_turns",
            "working_memory",
            "open_questions",
            "recent_files",
            "last_action",
            "compression_markers",
            "updated_at",
        }
        return not required_keys.issubset(data.keys())

    def _normalize_turns(self, value: Any) -> list[SessionTurn]:
        if not isinstance(value, list):
            return []
        turns: list[SessionTurn] = []
        for item in value:
            if isinstance(item, SessionTurn):
                turns.append(item)
            elif isinstance(item, dict):
                turns.append(
                    SessionTurn(
                        role=str(item.get("role", "")),
                        content=str(item.get("content", "")),
                    )
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

    def _normalize_marker_list(self, value: Any) -> list[CompressionMarker]:
        if not isinstance(value, list):
            return []
        markers: list[CompressionMarker] = []
        for item in value:
            if isinstance(item, CompressionMarker):
                markers.append(item)
            elif isinstance(item, dict):
                markers.append(
                    CompressionMarker(
                        compressed_at=str(item.get("compressed_at", "")),
                        dropped_turns=self._safe_int(item.get("dropped_turns", 0)),
                        kept_turns=self._safe_int(item.get("kept_turns", 0)),
                        reason=self._normalize_reason(item.get("reason")),
                    )
                )
        return markers

    def _normalize_reason(self, value: Any) -> Literal["count", "size"]:
        if value == "size":
            return "size"
        return "count"

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _compact_mapping(self, value: dict[str, Any], budget: int) -> dict[str, Any]:
        compacted: dict[str, Any] = {}
        for key, item in value.items():
            compacted[str(key)] = self._compact_value(item, budget)
        return compacted

    def _compact_string_list(self, value: list[str], budget: int) -> list[str]:
        return [self._truncate_text(item, budget, keep_tail=False) for item in value[:8]]

    def _compact_value(self, value: Any, budget: int) -> Any:
        if isinstance(value, str):
            return self._truncate_text(value, budget, keep_tail=False)
        if isinstance(value, list):
            return [self._compact_value(item, budget) for item in value[:8]]
        if isinstance(value, dict):
            return {str(key): self._compact_value(item, budget) for key, item in list(value.items())[:8]}
        return value
