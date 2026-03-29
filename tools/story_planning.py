"""小说立项与滚动大纲草案存储。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .frontmatter import compose_toml_document, parse_toml_front_matter, strip_front_matter_padding


class StoryPlanningStore:
    """管理立项聊天、基础设定和滚动大纲的草案文件。"""

    def __init__(self, project_root: Path, novel_id: str):
        self.project_root = Path(project_root).resolve()
        self.novel_id = novel_id
        self.novel_root = self.project_root / "data" / "novels" / novel_id
        self.runtime_planning_dir = self.novel_root / "data" / "planning"
        self.story_src_dir = self.novel_root / "src" / "story"
        self.outline_src_path = self.novel_root / "src" / "outline.md"

        self.ideation_path = self.runtime_planning_dir / "ideation.md"
        self.ideation_summary_path = self.runtime_planning_dir / "ideation_summary.md"
        self.background_draft_path = self.runtime_planning_dir / "background_draft.md"
        self.foundation_draft_path = self.runtime_planning_dir / "foundation_draft.md"
        self.outline_draft_path = self.runtime_planning_dir / "outline_draft.md"

    def append_ideation(self, text: str) -> None:
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
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        ideation = self.ideation_path.read_text(encoding="utf-8") if self.ideation_path.exists() else ""
        source_hash = self._hash_text(ideation)
        meta, body = parse_toml_front_matter(text)
        normalized_body = strip_front_matter_padding(body if meta else text).strip()
        normalized_meta = dict(meta) if meta else {}
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
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.story_src_dir.mkdir(parents=True, exist_ok=True)
        background_content = self._normalize_story_document("background", background)
        foundation_content = self._normalize_story_document("foundation", foundation)
        self.background_draft_path.write_text(background_content, encoding="utf-8")
        self.foundation_draft_path.write_text(foundation_content, encoding="utf-8")
        (self.story_src_dir / "background.md").write_text(background_content, encoding="utf-8")
        (self.story_src_dir / "foundation.md").write_text(foundation_content, encoding="utf-8")

    def promote_foundation(self) -> bool:
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.story_src_dir.mkdir(parents=True, exist_ok=True)

        background_src = self.story_src_dir / "background.md"
        foundation_src = self.story_src_dir / "foundation.md"

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
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.outline_src_path.parent.mkdir(parents=True, exist_ok=True)
        self.outline_src_path.write_text(content, encoding="utf-8")
        self.outline_draft_path.write_text(content, encoding="utf-8")

    def promote_outline(self, confirmed: bool) -> bool:
        if not confirmed:
            return False

        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.outline_src_path.parent.mkdir(parents=True, exist_ok=True)

        if self.outline_src_path.exists():
            content = self.outline_src_path.read_text(encoding="utf-8")
            self.outline_draft_path.write_text(content, encoding="utf-8")
            return True

        if self.outline_draft_path.exists():
            content = self.outline_draft_path.read_text(encoding="utf-8")
            self.outline_src_path.write_text(content, encoding="utf-8")
            self.outline_draft_path.write_text(content, encoding="utf-8")
            return True

        return False

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

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
