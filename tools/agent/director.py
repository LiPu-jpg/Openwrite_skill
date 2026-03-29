"""多 Agent 编排器。

将写作流程拆分为多个职责 Agent，默认串行编排：
1) context_engineer 组装上下文
2) writer 产出初稿
3) continuity_reviewer 审查
4) state_settler 结算
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, List
import re

from .base import AgentContext
from .writer import WriterAgent, WritingResult
from .reviewer import ReviewerAgent, ReviewResult
from ..chapter_assembler import ChapterAssemblerV2, ChapterAssemblyPacket, ROLE_SYSTEM_PROMPTS
from ..context_schema import normalize_context_payload, normalize_truth_file_key
from ..truth_manager import TruthFilesManager
from ..agent_policy import get_default_agent_specs


@dataclass
class MultiAgentResult:
    packet: ChapterAssemblyPacket
    draft: Optional[WritingResult] = None
    review: Optional[ReviewResult] = None
    system_prompts: Dict[str, str] = field(default_factory=dict)
    applied_state_updates: Dict[str, str] = field(default_factory=dict)
    new_concepts: List[str] = field(default_factory=list)


class MultiAgentDirector:
    """写作多 Agent 总控。"""

    def __init__(self, ctx: AgentContext, novel_id: str, style_id: str = ""):
        self.ctx = ctx
        self.novel_id = novel_id
        self.style_id = style_id
        self.agent_specs = get_default_agent_specs()
        self.assembler = ChapterAssemblerV2(
            project_root=Path(ctx.project_root),
            novel_id=novel_id,
            style_id=style_id,
        )
        self.writer = WriterAgent(ctx)
        self.reviewer = ReviewerAgent(ctx)
        self.truth_manager = TruthFilesManager(Path(ctx.project_root), novel_id)

    def assemble_packet(self, chapter_id: str) -> ChapterAssemblyPacket:
        return self.assembler.assemble(chapter_id)

    async def run(self, chapter_id: str, temperature: float = 0.7, run_review: bool = True) -> MultiAgentResult:
        self._assert_permission("context_engineer", "packet:build")
        packet = self.assemble_packet(chapter_id)

        writing_context = normalize_context_payload(
            {
                "target_words": 4000,
                "chapter_goals": ["遵循本章戏剧位置", "保持人物连续性", "承接上一章"],
                "outline": packet.to_markdown(),
                "style_profile": "\n\n".join(packet.style_documents.values())[:6000],
                "active_characters": [
                    {"name": k, "description": v[:1200]} for k, v in packet.character_documents.items()
                ],
                "current_state": packet.current_state[:1200],
                "ledger": packet.ledger[:1200],
                "relationships": packet.relationships[:1200],
                "recent_chapters": packet.previous_chapter_content,
                "dramatic_context": self._extract_dramatic_context(packet),
            },
            include_aliases=True,
        )

        chapter_number = self._parse_chapter_index(chapter_id)
        self._assert_permission("writer", "manuscript:draft")
        draft = await self.writer.write_chapter(
            context=writing_context,
            chapter_number=chapter_number,
            temperature=temperature,
            target_words=4000,
        )

        review = None
        if run_review:
            self._assert_permission("continuity_reviewer", "review:report")
            review = await self.reviewer.review(
                content=draft.content,
                context={
                    "character_profiles": "\n\n".join(packet.character_documents.values())[:4000],
                    "current_state": packet.current_state[:1000],
                    "relationships": packet.relationships[:1000],
                },
            )

        applied_updates = self._apply_state_updates(draft.state_updates)
        new_concepts = self._curate_new_concepts(draft.content, packet.concept_documents)

        return MultiAgentResult(
            packet=packet,
            draft=draft,
            review=review,
            system_prompts=dict(ROLE_SYSTEM_PROMPTS),
            applied_state_updates=applied_updates,
            new_concepts=new_concepts,
        )

    def _apply_state_updates(self, updates: Dict[str, str]) -> Dict[str, str]:
        if not updates:
            return {}
        self._assert_permission("state_settler", "world:current_state")

        truth = self.truth_manager.load_truth_files()
        writable: Dict[str, str] = {}
        file_map = {
            "current_state": "current_state",
            "ledger": "ledger",
            "relationships": "relationships",
        }

        for key, value in updates.items():
            if not isinstance(value, str) or not value.strip():
                continue
            canonical = normalize_truth_file_key(key)
            attr = file_map.get(canonical)
            if attr:
                writable[attr] = value

        if writable:
            self.truth_manager.update_truth_files(truth, writable)
        return writable

    def _curate_new_concepts(self, content: str, existing_docs: Dict[str, str]) -> List[str]:
        self._assert_permission("concept_curator", "src:world/entities")
        concept_hits = re.findall(r"(?:新概念|概念)[:：]\s*([A-Za-z0-9_\-\u4e00-\u9fff]{2,32})", content)
        if not concept_hits:
            return []

        existing_keys = set(existing_docs.keys())
        entities_dir = Path(self.ctx.project_root) / "data" / "novels" / self.novel_id / "src" / "world" / "entities"
        entities_dir.mkdir(parents=True, exist_ok=True)

        created: List[str] = []
        for concept in concept_hits:
            slug = concept.strip().lower().replace(" ", "_")
            key = f"entity.{slug}"
            if key in existing_keys:
                continue
            target = entities_dir / f"{slug}.md"
            if target.exists():
                continue
            target.write_text(
                f"# {concept}\n\n"
                "## 定义\n- （待补充）\n\n"
                "## 规则\n- （待补充）\n\n"
                "## 与主线关系\n- （待补充）\n",
                encoding="utf-8",
            )
            created.append(concept)
        return created

    def _assert_permission(self, agent_name: str, action: str) -> None:
        spec = self.agent_specs.get(agent_name)
        if not spec:
            raise PermissionError(f"Unknown agent: {agent_name}")
        if action in spec.forbidden:
            raise PermissionError(f"Agent '{agent_name}' forbidden action: {action}")
        if action in spec.can_write:
            return
        if action in spec.can_read:
            return
        # 支持前缀匹配，如 src:* / world:*
        for rule in spec.can_read + spec.can_write:
            if rule.endswith(":*"):
                prefix = rule[:-1]
                if action.startswith(prefix):
                    return
        raise PermissionError(f"Agent '{agent_name}' no permission for action: {action}")

    def _extract_dramatic_context(self, packet: ChapterAssemblyPacket) -> str:
        if not packet.current_arc_sections:
            return ""
        lines = []
        for sec in packet.current_arc_sections:
            lines.append(f"{sec.title}：{sec.summary[:180]}")
        return "\n".join(lines)

    def _parse_chapter_index(self, chapter_id: str) -> int:
        import re

        m = re.search(r"(\d+)", chapter_id)
        return int(m.group(1)) if m else 1
