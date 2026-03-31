"""小说立项与滚动大纲草案存储。

这个模块负责 Goethe 侧的 planning 真源与运行态草案：
- `data/planning/*` 记录会话中间产物和未确认内容
- `src/story/*` 与 `src/outline.md` 记录当前 canonical 资产

这里的核心约束不是“保存更多文件”，而是维持草案、确认版和 handoff 之间的镜像关系，
让 Goethe/Dante/CLI 看到的是同一套资产，而不是并行维护多份内容。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from .frontmatter import compose_toml_document, parse_toml_front_matter, strip_front_matter_padding


class StoryPlanningStore:
    """管理立项聊天、基础设定和滚动大纲的草案文件。

    它本身不决定“该写什么”，只负责把 planning 流中的文本资产放到正确位置：
    - ideation / summary 作为会话沉淀
    - background / foundation / outline 作为可晋升的故事资产
    - handoff 文件作为 Goethe -> Dante 的交接记录
    """

    def __init__(self, project_root: Path, novel_id: str):
        self.project_root = Path(project_root).resolve()
        self.novel_id = novel_id
        self.novel_root = self.project_root / "data" / "novels" / novel_id
        self.runtime_planning_dir = self.novel_root / "data" / "planning"
        self.workflow_dir = self.novel_root / "data" / "workflows"
        self.story_src_dir = self.novel_root / "src" / "story"
        self.outline_src_path = self.novel_root / "src" / "outline.md"

        self.ideation_path = self.runtime_planning_dir / "ideation.md"
        self.ideation_summary_path = self.runtime_planning_dir / "ideation_summary.md"
        self.background_draft_path = self.runtime_planning_dir / "background_draft.md"
        self.foundation_draft_path = self.runtime_planning_dir / "foundation_draft.md"
        self.outline_draft_path = self.runtime_planning_dir / "outline_draft.md"
        self.goethe_handoff_md_path = self.workflow_dir / "goethe_handoff.md"
        self.goethe_handoff_yaml_path = self.workflow_dir / "goethe_handoff.yaml"

    def append_ideation(self, text: str) -> None:
        """追加一段原始灵感记录，不做结构化改写。"""
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        previous = (
            self.ideation_path.read_text(encoding="utf-8")
            if self.ideation_path.exists()
            else ""
        )
        content = previous.rstrip("\n")
        if content:
            content += "\n"
        content += text
        self.ideation_path.write_text(content.rstrip("\n") + "\n", encoding="utf-8")

    def save_ideation_summary(self, text: str) -> None:
        """保存 ideation 的结构化汇总，并记录与原始 ideation 的对应哈希。"""
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        ideation = self.ideation_path.read_text(encoding="utf-8") if self.ideation_path.exists() else ""
        source_hash = self._hash_text(ideation)
        meta, body = parse_toml_front_matter(text)
        normalized_body = strip_front_matter_padding(body if meta else text).strip()
        normalized_meta = dict(meta) if meta else {}
        # summary 文档既给人读，也给 agent 做“这份总结是否已过期”的快速判断。
        normalized_meta.setdefault("id", "ideation_summary")
        normalized_meta.setdefault("type", "planning_summary")
        normalized_meta.setdefault("source", "ideation")
        normalized_meta["source_hash"] = source_hash
        normalized_meta.setdefault("summary", self._extract_story_summary(normalized_body))
        normalized_meta.setdefault(
            "detail_refs",
            ["核心方向", "稳定共识", "待确认点", "开放问题", "下一步"],
        )
        self.ideation_summary_path.write_text(
            compose_toml_document(normalized_meta, normalized_body),
            encoding="utf-8",
        )

    def ideation_summary_is_current(self) -> bool:
        """判断 ideation summary 是否仍然覆盖了最新的 ideation 原文。"""
        if not self.ideation_path.exists():
            return not self.ideation_summary_path.exists()
        if not self.ideation_summary_path.exists():
            return False
        meta, body = parse_toml_front_matter(
            self.ideation_summary_path.read_text(encoding="utf-8")
        )
        if not body.strip():
            return False
        current_hash = self._hash_text(self.ideation_path.read_text(encoding="utf-8"))
        return str(meta.get("source_hash", "")).strip() == current_hash

    def read_ideation_summary(self, max_chars: int = 0) -> str:
        if not self.ideation_summary_path.exists():
            return ""
        text = self.ideation_summary_path.read_text(encoding="utf-8")
        meta, body = parse_toml_front_matter(text)
        normalized_body = strip_front_matter_padding(body if meta else text)
        parts = []
        summary = str(meta.get("summary", "")).strip()
        detail_refs = meta.get("detail_refs", [])
        if summary:
            parts.append(f"摘要：{summary}")
        if isinstance(detail_refs, list) and detail_refs:
            parts.append("细节索引：" + "、".join(str(item) for item in detail_refs))
        if normalized_body:
            parts.append(normalized_body)
        rendered = "\n".join(parts).strip()
        if max_chars and len(rendered) > max_chars:
            return rendered[:max_chars]
        return rendered

    def save_foundation_draft(self, background: str, foundation: str) -> None:
        """保存基础设定草案，并同步刷新 canonical `src/story/*` 镜像。"""
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.story_src_dir.mkdir(parents=True, exist_ok=True)
        background_content = self._normalize_story_document("background", background)
        foundation_content = self._normalize_story_document("foundation", foundation)
        self.background_draft_path.write_text(background_content, encoding="utf-8")
        self.foundation_draft_path.write_text(foundation_content, encoding="utf-8")
        # 背景/设定这两类文档已经统一成单一文本真源，因此 draft 与 src 保持同内容镜像。
        (self.story_src_dir / "background.md").write_text(background_content, encoding="utf-8")
        (self.story_src_dir / "foundation.md").write_text(foundation_content, encoding="utf-8")

    def promote_foundation(self) -> bool:
        """将 background/foundation 的当前版本收口成 draft 与 src 的一致镜像。"""
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.story_src_dir.mkdir(parents=True, exist_ok=True)

        background_src = self.story_src_dir / "background.md"
        foundation_src = self.story_src_dir / "foundation.md"

        # 优先相信 src 里的 canonical 文档；如果它们已存在，就把 draft 校正回同一份内容。
        if background_src.exists() and foundation_src.exists():
            background_content = self._normalize_story_document(
                "background",
                background_src.read_text(encoding="utf-8"),
            )
            foundation_content = self._normalize_story_document(
                "foundation",
                foundation_src.read_text(encoding="utf-8"),
            )
            background_src.write_text(background_content, encoding="utf-8")
            foundation_src.write_text(foundation_content, encoding="utf-8")
            self.background_draft_path.write_text(background_content, encoding="utf-8")
            self.foundation_draft_path.write_text(foundation_content, encoding="utf-8")
            return True

        # 只有 draft 存在时，才把它们晋升成 canonical story 文档。
        if self.background_draft_path.exists() and self.foundation_draft_path.exists():
            background_content = self._normalize_story_document(
                "background",
                self.background_draft_path.read_text(encoding="utf-8"),
            )
            foundation_content = self._normalize_story_document(
                "foundation",
                self.foundation_draft_path.read_text(encoding="utf-8"),
            )
            background_src.write_text(background_content, encoding="utf-8")
            foundation_src.write_text(foundation_content, encoding="utf-8")
            self.background_draft_path.write_text(background_content, encoding="utf-8")
            self.foundation_draft_path.write_text(foundation_content, encoding="utf-8")
            return True

        return False

    def save_outline_draft(self, content: str) -> None:
        """保存当前可写窗口大纲，并同步刷新 canonical outline。"""
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.outline_src_path.parent.mkdir(parents=True, exist_ok=True)
        # outline 也已经统一成单一真源；planning draft 只是对同一文本的运行态镜像。
        self.outline_src_path.write_text(content, encoding="utf-8")
        self.outline_draft_path.write_text(content, encoding="utf-8")

    def read_outline_draft(self, max_chars: int = 0) -> str:
        if not self.outline_draft_path.exists():
            return ""
        text = self.outline_draft_path.read_text(encoding="utf-8").strip()
        if max_chars and len(text) > max_chars:
            return text[:max_chars]
        return text

    def outline_draft_is_current(self) -> bool:
        """判断 outline draft 是否与 canonical outline 保持完全一致。"""
        if not self.outline_src_path.exists() or not self.outline_draft_path.exists():
            return False
        return (
            self.outline_src_path.read_text(encoding="utf-8")
            == self.outline_draft_path.read_text(encoding="utf-8")
        )

    def promote_outline(self, confirmed: bool) -> bool:
        """在确认通过后把 outline draft 与 src/outline.md 收口成同一内容。"""
        if not confirmed:
            return False

        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.outline_src_path.parent.mkdir(parents=True, exist_ok=True)

        # 优先以 src/outline.md 为 canonical 真源，再把运行态镜像校回一致。
        if self.outline_src_path.exists():
            content = self.outline_src_path.read_text(encoding="utf-8")
            self.outline_draft_path.write_text(content, encoding="utf-8")
            return True

        # 只有 draft 存在时，再把它晋升成 canonical outline。
        if self.outline_draft_path.exists():
            content = self.outline_draft_path.read_text(encoding="utf-8")
            self.outline_src_path.write_text(content, encoding="utf-8")
            self.outline_draft_path.write_text(content, encoding="utf-8")
            return True

        return False

    def save_goethe_handoff(self, manifest: dict[str, Any]) -> tuple[Path, Path]:
        """保存 Goethe -> Dante 交接产物的 Markdown/YAML 双视图。"""
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        payload = dict(manifest)
        payload.setdefault("id", "goethe_handoff")
        payload.setdefault("type", "handoff")
        payload.setdefault("source_agent", "goethe")
        payload.setdefault("target_agent", "dante")
        payload.setdefault("next_stage", "chapter_preflight")
        payload.setdefault("ready", False)
        payload.setdefault("required_assets", [])

        ready_label = "是" if payload.get("ready") else "否"
        missing_items = payload.get("missing_items", [])
        missing_text = "、".join(str(item) for item in missing_items) if missing_items else "无"
        persona_paths = payload.get("persona_paths", [])
        persona_text = "、".join(str(item) for item in persona_paths) if persona_paths else "无"
        character_paths = payload.get("character_paths", [])
        character_text = "、".join(str(item) for item in character_paths) if character_paths else "无"

        # Markdown 版本给人快速审阅，YAML 版本给运行时和测试稳定读取。
        body = "\n".join(
            [
                "# Goethe -> Dante Handoff",
                "",
                "## Status",
                f"- ready: {ready_label}",
                f"- next_stage: {payload.get('next_stage', 'chapter_preflight')}",
                f"- source_agent: {payload.get('source_agent', 'goethe')}",
                f"- target_agent: {payload.get('target_agent', 'dante')}",
                "",
                "## Required Assets",
                "- " + "\n- ".join(
                    str(item) for item in payload.get("required_assets", [])
                )
                if payload.get("required_assets")
                else "- 无",
                "",
                "## Missing Items",
                f"- {missing_text}",
                "",
                "## Persona Paths",
                f"- {persona_text}",
                "",
                "## Character Paths",
                f"- {character_text}",
                "",
                "## Summary",
                str(payload.get("summary", "")).strip() or "Goethe 资产已整理完毕，可以交接给 Dante。",
            ]
        )
        self.goethe_handoff_md_path.write_text(
            compose_toml_document(
                {
                    "id": payload["id"],
                    "type": payload["type"],
                    "source_agent": payload["source_agent"],
                    "target_agent": payload["target_agent"],
                    "ready": bool(payload.get("ready")),
                    "next_stage": payload.get("next_stage", "chapter_preflight"),
                },
                body,
            ),
            encoding="utf-8",
        )
        self.goethe_handoff_yaml_path.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return self.goethe_handoff_md_path, self.goethe_handoff_yaml_path

    def list_character_documents(self) -> list[dict[str, str]]:
        """列出当前 canonical 角色文档，供 handoff 和 planning 检查使用。"""
        character_dir = self.novel_root / "src" / "characters"
        if not character_dir.exists():
            return []

        documents: list[dict[str, str]] = []
        for path in sorted(character_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            meta, body = parse_toml_front_matter(text)
            normalized_body = strip_front_matter_padding(body if meta else text)
            title = self._extract_document_title(normalized_body, path.stem)
            documents.append(
                {
                    "id": str(meta.get("id", path.stem)).strip() or path.stem,
                    "title": title,
                    "path": str(path),
                }
            )
        return documents

    def load_story_document(self, kind: str) -> dict[str, object]:
        """Load a promoted story document and expose metadata plus body."""
        path = self.story_src_dir / f"{kind}.md"
        if not path.exists():
            return {"path": path, "meta": {}, "body": ""}

        text = path.read_text(encoding="utf-8")
        meta, body = parse_toml_front_matter(text)
        normalized_body = strip_front_matter_padding(body if meta else text)
        if not meta:
            meta = self._default_story_metadata(kind, normalized_body)
        return {"path": path, "meta": meta, "body": normalized_body}

    def read_story_document(self, kind: str, max_chars: int = 0) -> str:
        """Return a compact AI-friendly rendering of a story source document."""
        document = self.load_story_document(kind)
        meta = document["meta"] if isinstance(document["meta"], dict) else {}
        body = str(document["body"])
        parts = []
        summary = str(meta.get("summary", "")).strip()
        detail_refs = meta.get("detail_refs", [])
        if summary:
            parts.append(f"摘要：{summary}")
        if isinstance(detail_refs, list) and detail_refs:
            parts.append("细节索引：" + "、".join(str(item) for item in detail_refs))
        if body:
            parts.append(body)
        text = "\n".join(parts).strip()
        if max_chars and len(text) > max_chars:
            return text[:max_chars]
        return text

    def _normalize_story_document(self, kind: str, text: str) -> str:
        """把 story 文档规整成 `TOML front matter + Markdown body` 统一格式。"""
        meta, body = parse_toml_front_matter(text)
        normalized_body = strip_front_matter_padding(body if meta else text)
        normalized_meta = meta or self._default_story_metadata(kind, normalized_body)
        return compose_toml_document(normalized_meta, normalized_body)

    def _default_story_metadata(self, kind: str, body: str) -> dict[str, object]:
        summary = self._extract_story_summary(body)
        detail_refs = {
            "background": ["premise", "conflict", "tone"],
            "foundation": ["protagonist", "rules", "stakes"],
        }.get(kind, ["details"])
        return {
            "id": f"story_{kind}",
            "type": "story_document",
            "summary": summary,
            "detail_refs": detail_refs,
        }

    def _extract_story_summary(self, body: str) -> str:
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            return stripped[:160]
        return body.strip()[:160]

    def _extract_document_title(self, body: str, fallback: str) -> str:
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                return title or fallback
        return fallback

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
