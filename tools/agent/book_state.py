"""Book-level orchestrator state persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import tempfile
from pathlib import Path
from typing import Any

import yaml


class BookStage(str, Enum):
    DISCOVERY = "discovery"
    FOUNDATION = "foundation"
    ROLLING_OUTLINE = "rolling_outline"
    CHAPTER_PREFLIGHT = "chapter_preflight"
    DRAFTING = "drafting"
    REVIEW_AND_REVISE = "review_and_revise"
    SETTLEMENT = "settlement"
    MILESTONE_REVIEW = "milestone_review"


@dataclass
class BookState:
    novel_id: str
    stage: BookStage = BookStage.DISCOVERY
    current_arc: str = ""
    current_section: str = ""
    current_chapter: str = ""
    pending_confirmation: str = ""
    blocking_reason: str = ""
    last_agent_action: str = ""
    last_handoff_from: str = ""


class BookStateStore:
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
            / "book_state.yaml"
        )

    def load_or_create(self) -> BookState:
        if not self.path.exists():
            state = BookState(novel_id=self.novel_id)
            self.save(state)
            return state

        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except Exception:
            state = BookState(novel_id=self.novel_id)
            self.save(state)
            return state

        if not data:
            state = BookState(novel_id=self.novel_id)
            self.save(state)
            return state

        if not isinstance(data, dict):
            state = BookState(novel_id=self.novel_id)
            self.save(state)
            return state

        return self._from_dict(data)

    def save(self, state: BookState) -> None:
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

    def _to_dict(self, state: BookState) -> dict[str, Any]:
        data = asdict(state)
        data["stage"] = state.stage.value
        return data

    def _from_dict(self, data: dict[str, Any]) -> BookState:
        raw_stage = data.get("stage", BookStage.DISCOVERY.value)
        try:
            stage = (
                BookStage(raw_stage)
                if not isinstance(raw_stage, BookStage)
                else raw_stage
            )
        except ValueError:
            stage = BookStage.DISCOVERY
        return BookState(
            novel_id=data.get("novel_id", self.novel_id),
            stage=stage,
            current_arc=data.get("current_arc", ""),
            current_section=data.get("current_section", ""),
            current_chapter=data.get("current_chapter", ""),
            pending_confirmation=data.get("pending_confirmation", ""),
            blocking_reason=data.get("blocking_reason", ""),
            last_agent_action=data.get("last_agent_action", ""),
            last_handoff_from=data.get("last_handoff_from", ""),
        )
