"""High-level Dante action adapter."""

from __future__ import annotations

from typing import Any

from .orchestrator import OpenWriteOrchestrator, OrchestratorResult


class DanteActionAdapter:
    def __init__(self, orchestrator: OpenWriteOrchestrator):
        self.orchestrator = orchestrator

    def summarize_ideation(self) -> dict[str, Any]:
        return self._wrap("summarize_ideation", self.orchestrator.summarize_ideation())

    def confirm_ideation_summary(self, text: str = "这个汇总可以") -> dict[str, Any]:
        return self._wrap(
            "confirm_ideation_summary",
            self.orchestrator.confirm_ideation_summary(text),
        )

    def generate_outline_draft(self, request_text: str) -> dict[str, Any]:
        payload = self._wrap(
            "generate_outline_draft",
            self.orchestrator.generate_outline_draft(request_text),
        )
        planning_store = getattr(self.orchestrator, "story_planning_store", None)
        if planning_store is not None and hasattr(planning_store, "read_outline_draft"):
            payload["outline_draft"] = planning_store.read_outline_draft()
        return payload

    def run_chapter_preflight(self, chapter_id: str) -> dict[str, Any]:
        result = self.orchestrator.run_chapter_preflight(chapter_id)
        payload = self._wrap("run_chapter_preflight", result)
        payload.update(result if isinstance(result, dict) else {})
        return payload

    def _wrap(self, action: str, result: Any) -> dict[str, Any]:
        if isinstance(result, OrchestratorResult):
            return {
                "action": action,
                "ok": not result.blocked,
                "stage": result.stage.value,
                "blocked": result.blocked,
                "next_action": result.next_action,
                "message": result.message,
            }
        if isinstance(result, dict):
            payload = dict(result)
            payload.setdefault("ok", True)
            payload.setdefault("blocked", False)
            payload.setdefault("next_action", "")
            payload["action"] = action
            return payload
        return {
            "action": action,
            "ok": True,
            "blocked": False,
            "next_action": "",
            "result": result,
        }
