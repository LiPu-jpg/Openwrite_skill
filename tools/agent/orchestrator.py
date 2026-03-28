"""Deterministic book-level orchestrator for ``openwrite agent``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from ..context_builder import ContextBuilder
from ..story_planning import StoryPlanningStore
from ..utils import parse_chapter_id
from ..workflow_scheduler import WorkflowScheduler
from .toolkits import WRITING_TOOLKIT
from .book_state import BookStage, BookState, BookStateStore


@dataclass(frozen=True)
class OrchestratorResult:
    message: str
    stage: BookStage
    blocked: bool
    next_action: str


class OpenWriteOrchestrator:
    """Book-level deterministic orchestrator."""

    def __init__(
        self,
        project_root: Path,
        novel_id: str,
        state_store: Optional[BookStateStore] = None,
        planning_store: Optional[StoryPlanningStore] = None,
        tool_executors: Optional[dict[str, Callable[[dict[str, Any]], dict[str, Any]]]] = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.novel_id = novel_id
        self.state_store = state_store or BookStateStore(self.project_root, novel_id)
        self.story_planning_store = planning_store or StoryPlanningStore(
            self.project_root, novel_id
        )
        self.tool_executors = dict(tool_executors or {})
        self.state = BookState(novel_id=novel_id)

    @classmethod
    def for_testing(
        cls,
        project_root: Path,
        novel_id: str,
        state_store: Optional[BookStateStore] = None,
        planning_store: Optional[StoryPlanningStore] = None,
        tool_executors: Optional[dict[str, Callable[[dict[str, Any]], dict[str, Any]]]] = None,
    ) -> "OpenWriteOrchestrator":
        return cls(
            project_root=project_root,
            novel_id=novel_id,
            state_store=state_store,
            planning_store=planning_store,
            tool_executors=tool_executors,
        )

    def build_chapter_packet(self, chapter_id: str) -> dict[str, Any]:
        builder = ContextBuilder(self.project_root, self.novel_id)
        context = builder.build_generation_context(chapter_id)
        prompt_sections = context.to_prompt_sections()

        packet = {
            "novel_id": self.novel_id,
            "chapter_id": chapter_id,
            "story_background": self._read_text(
                self.story_planning_store.story_src_dir / "background.md"
            ),
            "foundation": self._read_text(
                self.story_planning_store.story_src_dir / "foundation.md"
            ),
            "previous_chapter_content": self._read_previous_chapter_content(chapter_id),
            "style_documents": self._build_style_documents(context, prompt_sections),
            "character_documents": self._build_character_documents(context),
            "concept_documents": self._build_concept_documents(context, prompt_sections),
            "prompt_sections": prompt_sections,
        }

        self._write_context_packet_snapshot(chapter_id, packet)
        return packet

    def run_preflight(self, chapter_id: str) -> dict[str, Any]:
        self.state = self.state_store.load_or_create()

        if self.state.stage != BookStage.CHAPTER_PREFLIGHT:
            return self._preflight_result(
                chapter_id=chapter_id,
                ok=False,
                reason="outline_not_confirmed",
                missing_items=["outline_scope"],
            )

        context = ContextBuilder(self.project_root, self.novel_id).build_generation_context(
            chapter_id
        )
        if not context.current_chapter:
            return self._preflight_result(
                chapter_id=chapter_id,
                ok=False,
                reason="missing_chapter_scope",
                missing_items=[chapter_id],
            )

        previous_chapter_id = self._previous_chapter_id(chapter_id)
        previous_chapter_content = ""
        missing_items: list[str] = []
        if previous_chapter_id:
            previous_chapter_content = self._read_previous_chapter_content(chapter_id)
            if not previous_chapter_content:
                missing_items.append(previous_chapter_id)

        if chapter_id != "ch_001" and not previous_chapter_content:
            return self._preflight_result(
                chapter_id=chapter_id,
                ok=False,
                reason="missing_previous_chapter",
                missing_items=missing_items or [previous_chapter_id],
            )

        packet = self.build_chapter_packet(chapter_id)
        return {
            "ok": True,
            "chapter_id": chapter_id,
            "reason": "",
            "missing_items": [],
            "packet": packet,
        }

    def delegate_writing(
        self,
        chapter_id: str,
        preflight_result: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        self.state = self.state_store.load_or_create()
        packet_result = preflight_result or self.run_preflight(chapter_id)
        if not packet_result.get("ok"):
            return {
                "ok": False,
                "chapter_id": chapter_id,
                "reason": packet_result.get("reason", "preflight_failed"),
                "missing_items": packet_result.get("missing_items", []),
                "next_stage": self.state.stage.value,
                "next_action": "preflight_failed",
            }

        packet = packet_result["packet"]
        scheduler = WorkflowScheduler(self.project_root, self.novel_id)
        workflow = scheduler.load_or_create(chapter_id)
        try:
            scheduler.start_stage(workflow, "context_assembly")
            scheduler.complete_stage(
                workflow,
                "context_assembly",
                message="chapter packet assembled",
                data={"chapter_id": chapter_id},
            )
            scheduler.start_stage(workflow, "writing")

            executor = self._get_writing_executor("write_chapter")
            raw_result = executor(
                {
                    "chapter_id": chapter_id,
                    "packet": packet,
                    "context_packet": packet,
                    "prompt_sections": packet["prompt_sections"],
                }
            )
            result = self._normalize_write_result(raw_result)
            if result.get("error") or not result.get("ok"):
                raise RuntimeError(result.get("error", "write_chapter_failed"))

            draft_path = self._sanitize_draft_path(result.get("draft_path", ""))
            scheduler.complete_stage(
                workflow,
                "writing",
                message="chapter written",
                data={"draft_path": draft_path},
            )

            self.state.stage = BookStage.REVIEW_AND_REVISE
            self.state.current_chapter = chapter_id
            self.state.blocking_reason = ""
            self.state.last_agent_action = "delegated_writing"
            self.state_store.save(self.state)

            return {
                "ok": True,
                "chapter_id": chapter_id,
                "reason": "",
                "next_stage": BookStage.REVIEW_AND_REVISE.value,
                "next_action": "review_and_revise",
                "workflow_stage": scheduler.load_workflow(chapter_id).current_stage,
            }
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            try:
                scheduler.fail_stage(workflow, "writing", error)
            except Exception:
                self._persist_failed_workflow(
                    scheduler=scheduler,
                    workflow=workflow,
                    stage_name="writing",
                    error=error,
                )
            self.state.blocking_reason = "writing_failed"
            self.state.last_agent_action = "delegated_writing_failed"
            self.state_store.save(self.state)
            return {
                "ok": False,
                "chapter_id": chapter_id,
                "reason": error,
                "next_stage": self.state.stage.value,
                "next_action": "writing_failed",
            }

    def handle_user_message(self, text: str) -> OrchestratorResult:
        self.state = self.state_store.load_or_create()

        if self._is_negated_chapter_request(text):
            return self._ignored_result()

        if self._is_negated_foundation_confirmation(text):
            return self._ignored_result()

        if self._is_negated_outline_confirmation(text):
            return self._ignored_result()

        chapter_id = self._extract_chapter_request(text)
        if chapter_id:
            return self._handle_chapter_request(chapter_id)

        if self._looks_like_foundation_confirmation(text):
            return self._handle_foundation_confirmation()

        if self._looks_like_outline_confirmation(text):
            return self._handle_outline_confirmation()

        return self._handle_discovery(text)

    def run_cli(self, instruction: str, quiet: bool = False, max_turns: int = 20) -> int:
        """Run a deterministic CLI interaction."""
        _ = max_turns

        if self._is_status_request(instruction):
            result = self._handle_status_request()
        else:
            result = self.handle_user_message(instruction)
        if not quiet:
            print(result.message)

        chapter_id = self._extract_chapter_request(instruction)
        if chapter_id and result.next_action == "chapter_preflight" and not result.blocked:
            preflight = self.run_preflight(chapter_id)
            if not quiet:
                print(self._format_cli_preflight_message(chapter_id, preflight))
            if not preflight.get("ok"):
                return 1

            delegate = self.delegate_writing(chapter_id, preflight_result=preflight)
            if not quiet:
                print(self._format_cli_delegate_message(chapter_id, delegate))
            return 0 if delegate.get("ok") else 1

        return 0 if not result.blocked else 1

    def _handle_discovery(self, text: str) -> OrchestratorResult:
        self.story_planning_store.append_ideation(text)
        self.state.last_agent_action = "recorded_ideation"
        self.state.blocking_reason = ""
        self.state_store.save(self.state)
        return OrchestratorResult(
            message="收到。请继续补充更多背景或基础设定，我会先整理立项信息。",
            stage=self.state.stage,
            blocked=False,
            next_action="request_more_background",
        )

    def _ignored_result(self) -> OrchestratorResult:
        return OrchestratorResult(
            message="收到。当前指令是否定表达，我先不推进流程。",
            stage=self.state.stage,
            blocked=True,
            next_action="ignore",
        )

    def _is_status_request(self, text: str) -> bool:
        return text.strip() in {"查看项目状态", "查看状态", "status"}

    def _handle_status_request(self) -> OrchestratorResult:
        state = self._snapshot_state()
        current_chapter = state.current_chapter or "未指定"
        return OrchestratorResult(
            message=f"当前状态: {state.stage.value}，当前章节: {current_chapter}",
            stage=state.stage,
            blocked=False,
            next_action="report_status",
        )

    def _snapshot_state(self) -> BookState:
        if self.state_store.path.exists():
            try:
                return self.state_store.load_or_create()
            except Exception:
                pass
        return BookState(novel_id=self.novel_id)

    def _format_cli_preflight_message(self, chapter_id: str, result: dict[str, Any]) -> str:
        if result.get("ok"):
            return f"章节预检通过: {chapter_id}"

        reason = result.get("reason", "preflight_failed")
        missing_items = result.get("missing_items", [])
        if missing_items:
            missing_text = ", ".join(str(item) for item in missing_items)
            return f"章节预检失败: {chapter_id} ({reason}; missing: {missing_text})"
        return f"章节预检失败: {chapter_id} ({reason})"

    def _format_cli_delegate_message(self, chapter_id: str, result: dict[str, Any]) -> str:
        if result.get("ok"):
            return f"章节已委派: {chapter_id}"

        reason = result.get("reason", "writing_failed")
        return f"章节委派失败: {chapter_id} ({reason})"

    def _handle_foundation_confirmation(self) -> OrchestratorResult:
        if not self.story_planning_store.promote_foundation():
            self.state.blocking_reason = "missing_foundation_drafts"
            self.state.last_agent_action = "blocked_foundation_promotion_missing_drafts"
            self.state_store.save(self.state)
            return OrchestratorResult(
                message="基础设定草案缺失。请先准备 background_draft.md 和 foundation_draft.md。",
                stage=self.state.stage,
                blocked=True,
                next_action="prepare_foundation_drafts",
            )

        self.state.stage = BookStage.ROLLING_OUTLINE
        self.state.pending_confirmation = "outline_scope"
        self.state.blocking_reason = ""
        self.state.last_agent_action = "requested_outline_confirmation"
        self.state_store.save(self.state)
        return OrchestratorResult(
            message="基础设定已确认并升格。请确认可写的大纲范围后再进入章节编写。",
            stage=self.state.stage,
            blocked=False,
            next_action="request_outline_confirmation",
        )

    def _handle_outline_confirmation(self) -> OrchestratorResult:
        if not self.story_planning_store.promote_outline(confirmed=True):
            self.state.blocking_reason = "missing_outline_draft"
            self.state.last_agent_action = "blocked_outline_promotion_missing_draft"
            self.state_store.save(self.state)
            return OrchestratorResult(
                message="大纲草案缺失。请先准备 outline_draft.md。",
                stage=self.state.stage,
                blocked=True,
                next_action="prepare_outline_draft",
            )

        self.state.stage = BookStage.CHAPTER_PREFLIGHT
        self.state.pending_confirmation = ""
        self.state.blocking_reason = ""
        self.state.last_agent_action = "promoted_outline"
        self.state_store.save(self.state)
        return OrchestratorResult(
            message="大纲范围已确认。下一步进入章节预检。",
            stage=self.state.stage,
            blocked=False,
            next_action="chapter_preflight",
        )

    def _handle_chapter_request(self, chapter_id: str) -> OrchestratorResult:
        if self.state.stage != BookStage.CHAPTER_PREFLIGHT:
            self.state.blocking_reason = "outline_not_confirmed"
            self.state.last_agent_action = "blocked_chapter_request_before_outline_confirmation"
            self.state_store.save(self.state)
            return OrchestratorResult(
                message="还不能写章节。请先确认大纲范围。",
                stage=self.state.stage,
                blocked=True,
                next_action="request_outline_confirmation",
            )

        self.state.current_chapter = chapter_id
        self.state.blocking_reason = ""
        self.state.last_agent_action = "recorded_current_chapter"
        self.state_store.save(self.state)
        return OrchestratorResult(
            message=f"已记录当前章节 {chapter_id}，下一步进入章节预检。",
            stage=self.state.stage,
            blocked=False,
            next_action="chapter_preflight",
        )

    def _extract_chapter_request(self, text: str) -> Optional[str]:
        match = re.search(
            r"(?:开始写|写一下|写出|帮我写|请写|我要写|写)\s*"
            r"(?P<chapter>ch\s*_\s*\d{3}|第\s*[零一二三四五六七八九十百千万\d]+\s*章)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            chapter_id = parse_chapter_id(re.sub(r"\s+", "", match.group("chapter")))
            if chapter_id:
                return chapter_id
        return None

    def _is_negated_chapter_request(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", text)
        chapter = r"(?:第[零一二三四五六七八九十百千万\d]+章|ch_\d{3})"
        write = r"(?:写|开始写|帮我写|请写|我要写)"
        negation = r"(?:不要|别|先别|先不要)"
        return bool(
            re.search(fr"{negation}.{{0,6}}{write}.{{0,12}}{chapter}", compact)
            or re.search(fr"{write}.{{0,12}}{chapter}.{{0,6}}{negation}", compact)
            or re.search(fr"{chapter}.{{0,12}}{negation}.{{0,6}}{write}", compact)
        )

    def _looks_like_foundation_confirmation(self, text: str) -> bool:
        lowered = text.lower()
        foundation_terms = ("基础设定", "foundation", "背景")
        ready_terms = ("准备好了", "已准备好", "ready", "可以开始", "开始", "start")
        outline_terms = ("outline", "大纲", "提纲")
        return (
            any(term in lowered for term in ("基础设定准备好了", "基础设定好了", "foundation ready"))
            or (
                any(term in text for term in foundation_terms)
                and any(term in lowered for term in ready_terms)
                and any(term in lowered for term in outline_terms)
            )
            or ("开始 outline" in lowered)
            or ("开始提纲" in text)
            or ("开始大纲" in text)
        )

    def _is_negated_foundation_confirmation(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", text.lower())
        return bool(
            re.search(
                r"(?:不要|别|先别|先不要|先不).{0,6}(?:开始|启动).{0,12}(?:outline|大纲|提纲)",
                compact,
            )
        )

    def _looks_like_outline_confirmation(self, text: str) -> bool:
        lowered = text.lower()
        if any(term in text for term in ("吗", "？", "?")):
            return False
        positive_patterns = (
            r"(?:大纲|范围|提纲).*(?:确认|确认好了|确认通过|可写|可以直接写|开始写|进入章节)",
            r"(?:确认|确定|同意).*(?:大纲|范围|提纲)",
            r"outline.*(?:confirm|confirmed|ready|go ahead)",
        )
        return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in positive_patterns)

    def _is_negated_outline_confirmation(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", text.lower())
        outline = r"(?:大纲|范围|提纲|outline)"
        negation = r"(?:不要|别|先别|先不要|先不|不确认|不同意|不认可|不接受)"
        return bool(
            re.search(fr"{negation}.{{0,12}}{outline}", compact)
            or re.search(fr"{outline}.{{0,12}}{negation}", compact)
        )

    def _get_writing_executor(self, tool_name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        if tool_name not in WRITING_TOOLKIT:
            raise KeyError(f"Tool {tool_name} is not part of WRITING_TOOLKIT")
        if tool_name not in self.tool_executors:
            raise KeyError(f"Missing executor for {tool_name}")
        return self.tool_executors[tool_name]

    def _build_style_documents(
        self, context: Any, prompt_sections: dict[str, str]
    ) -> dict[str, str]:
        summary = ""
        if getattr(context, "style_profile", None) and hasattr(
            context.style_profile, "to_summary"
        ):
            summary = context.style_profile.to_summary(max_chars=1200)
        return {
            "summary": summary,
            "prompt_section": prompt_sections.get("风格指南", ""),
        }

    def _build_character_documents(self, context: Any) -> list[str]:
        documents: list[str] = []
        for character in getattr(context, "active_characters", []):
            if hasattr(character, "to_context_text"):
                documents.append(character.to_context_text(max_chars=800))
            else:
                documents.append(str(character))
        return documents

    def _build_concept_documents(
        self, context: Any, prompt_sections: dict[str, str]
    ) -> dict[str, str]:
        return {
            "world_rules": prompt_sections.get("世界观", ""),
            "chapter_goals": prompt_sections.get("本章目标", ""),
            "current_state": getattr(context, "current_state", ""),
            "pending_hooks": getattr(context, "pending_hooks", ""),
        }

    def _write_context_packet_snapshot(self, chapter_id: str, packet: dict[str, Any]) -> None:
        snapshot_dir = (
            self.project_root
            / "data"
            / "novels"
            / self.novel_id
            / "data"
            / "test_outputs"
            / "context_packets"
        )
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{chapter_id}.yaml"
        snapshot_path.write_text(
            yaml.safe_dump(packet, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _previous_chapter_id(self, chapter_id: str) -> str:
        match = re.search(r"(\d+)$", chapter_id)
        if not match:
            return ""
        chapter_num = int(match.group(1))
        if chapter_num <= 1:
            return ""
        return f"ch_{chapter_num - 1:03d}"

    def _read_previous_chapter_content(self, chapter_id: str) -> str:
        previous_chapter_id = self._previous_chapter_id(chapter_id)
        if not previous_chapter_id:
            return ""

        manuscript_dir = (
            self.project_root / "data" / "novels" / self.novel_id / "data" / "manuscript"
        )
        if not manuscript_dir.exists():
            return ""

        patterns = [
            f"{previous_chapter_id}.md",
            f"{previous_chapter_id}_*.md",
            f"chapter_{previous_chapter_id.split('_')[-1]}.md",
        ]
        for pattern in patterns:
            matches = sorted(manuscript_dir.rglob(pattern))
            if matches:
                return self._read_text(matches[0])
        return ""

    def _preflight_result(
        self,
        chapter_id: str,
        ok: bool,
        reason: str,
        missing_items: list[str],
    ) -> dict[str, Any]:
        return {
            "ok": ok,
            "chapter_id": chapter_id,
            "reason": reason,
            "missing_items": missing_items,
            "packet": None,
        }

    def _normalize_write_result(self, result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise TypeError("write_chapter returned invalid response")
        return result

    def _persist_failed_workflow(
        self,
        scheduler: WorkflowScheduler,
        workflow: Any,
        stage_name: str,
        error: str,
    ) -> None:
        stage = None
        for candidate in getattr(workflow, "stages", []):
            if getattr(candidate, "name", "") == stage_name:
                stage = candidate
                break

        if stage is not None:
            stage.status = "failed"
            stage.completed_at = datetime.now().isoformat()
            stage.message = error

        workflow.error = f"{stage_name}: {error}"
        workflow.updated_at = datetime.now().isoformat()

        path = scheduler.workflow_dir / f"wf_{workflow.chapter_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(
                workflow.to_dict(),
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    def _sanitize_draft_path(self, draft_path: Any) -> str:
        if not draft_path:
            return ""

        try:
            candidate = Path(str(draft_path))
            if not candidate.is_absolute():
                candidate = (self.project_root / candidate).resolve()
            else:
                candidate = candidate.resolve()

            if self._is_within_project(candidate):
                return str(candidate)
        except Exception:
            return ""
        return ""

    def _is_within_project(self, path: Path) -> bool:
        try:
            path.relative_to(self.project_root)
            return True
        except ValueError:
            return False


__all__ = ["OpenWriteOrchestrator", "OrchestratorResult"]
