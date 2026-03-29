from pathlib import Path

from tools.frontmatter import parse_toml_front_matter
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
    background_meta, background_body = parse_toml_front_matter(
        (store.story_src_dir / "background.md").read_text(encoding="utf-8")
    )
    foundation_meta, foundation_body = parse_toml_front_matter(
        (store.story_src_dir / "foundation.md").read_text(encoding="utf-8")
    )

    assert background_meta["id"] == "story_background"
    assert background_meta["type"] == "story_document"
    assert background_meta["summary"] == "背景A"
    assert background_body.strip() == "背景A"

    assert foundation_meta["id"] == "story_foundation"
    assert foundation_meta["type"] == "story_document"
    assert foundation_meta["summary"] == "设定B"
    assert foundation_body.strip() == "设定B"


def test_load_story_document_returns_metadata_and_body(tmp_path: Path):
    store = StoryPlanningStore(tmp_path, "demo")
    store.story_src_dir.mkdir(parents=True, exist_ok=True)
    (store.story_src_dir / "background.md").write_text(
        """+++
id = "story_background"
type = "story_document"
summary = "都市异能职场故事。"
detail_refs = ["premise", "conflict"]
+++

# 背景

都市异能职场故事。
""",
        encoding="utf-8",
    )

    document = store.load_story_document("background")

    assert document["meta"]["id"] == "story_background"
    assert document["meta"]["summary"] == "都市异能职场故事。"
    assert document["body"].lstrip().startswith("# 背景")


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
