from pathlib import Path

from tools.story_planning import StoryPlanningStore


def test_append_ideation_writes_runtime_draft(tmp_path: Path):
    store = StoryPlanningStore(tmp_path, "demo")

    store.append_ideation("主角是社畜术师")
    store.append_ideation("设定偏现代都市修仙")

    assert "主角是社畜术师" in store.ideation_path.read_text(encoding="utf-8")
    assert "设定偏现代都市修仙" in store.ideation_path.read_text(encoding="utf-8")


def test_promote_foundation_writes_src_story_files(tmp_path: Path):
    store = StoryPlanningStore(tmp_path, "demo")

    store.save_foundation_draft(background="背景A", foundation="设定B")
    promoted = store.promote_foundation()

    assert promoted is True
    assert (store.story_src_dir / "background.md").read_text(encoding="utf-8") == "背景A"
    assert (store.story_src_dir / "foundation.md").read_text(encoding="utf-8") == "设定B"


def test_outline_requires_confirmation_before_promotion(tmp_path: Path):
    store = StoryPlanningStore(tmp_path, "demo")

    store.save_outline_draft("# 大纲草案")

    assert store.promote_outline(confirmed=False) is False
    assert not store.outline_src_path.exists()


def test_outline_promotion_requires_confirmed_draft(tmp_path: Path):
    store = StoryPlanningStore(tmp_path, "demo")

    store.save_outline_draft("# 大纲草案")

    assert store.promote_outline(confirmed=True) is True
    assert store.outline_src_path.read_text(encoding="utf-8") == "# 大纲草案"
