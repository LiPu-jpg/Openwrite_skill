"""小说立项与滚动大纲草案存储。"""

from __future__ import annotations

from pathlib import Path


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

    def save_foundation_draft(self, background: str, foundation: str) -> None:
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.background_draft_path.write_text(background, encoding="utf-8")
        self.foundation_draft_path.write_text(foundation, encoding="utf-8")

    def promote_foundation(self) -> bool:
        if not self.background_draft_path.exists() or not self.foundation_draft_path.exists():
            return False

        self.story_src_dir.mkdir(parents=True, exist_ok=True)
        (self.story_src_dir / "background.md").write_text(
            self.background_draft_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (self.story_src_dir / "foundation.md").write_text(
            self.foundation_draft_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return True

    def save_outline_draft(self, content: str) -> None:
        self.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
        self.outline_draft_path.write_text(content, encoding="utf-8")

    def promote_outline(self, confirmed: bool) -> bool:
        if not confirmed or not self.outline_draft_path.exists():
            return False

        self.outline_src_path.parent.mkdir(parents=True, exist_ok=True)
        self.outline_src_path.write_text(
            self.outline_draft_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        return True
