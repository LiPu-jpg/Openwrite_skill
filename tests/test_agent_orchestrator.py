import sys
import os
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.agent.book_state import BookStage, BookStateStore
from tools.agent.orchestrator import OpenWriteOrchestrator
from tools.agent.toolkits import WRITING_TOOLKIT
from tools.frontmatter import parse_toml_front_matter
from tools.init_project import init_project
from tools.story_planning import StoryPlanningStore
from tools.workflow_scheduler import WorkflowScheduler


def _bootstrap_novel(tmp_path: Path, novel_id: str = "demo") -> tuple[Path, Path]:
    init_project(tmp_path, novel_id)
    novel_root = tmp_path / "data" / "novels" / novel_id
    hierarchy_path = novel_root / "data" / "hierarchy.yaml"
    hierarchy = {
        "story_info": {"title": "测试小说", "theme": "测试主题"},
        "arcs": [
            {
                "id": "arc_001",
                "title": "第一篇",
                "description": "开篇",
                "chapters": ["ch_001", "ch_002"],
            }
        ],
        "sections": [
            {
                "id": "sec_001",
                "title": "第一节",
                "arc_id": "arc_001",
                "chapters": ["ch_001", "ch_002"],
            }
        ],
        "chapters": [
            {
                "id": "ch_001",
                "title": "第一章",
                "summary": "开篇",
                "goals": ["建立主角"],
                "involved_characters": ["char_001"],
                "involved_settings": ["测试场景"],
            },
            {
                "id": "ch_002",
                "title": "第二章",
                "summary": "承接",
                "goals": ["推进剧情"],
                "involved_characters": ["char_001"],
                "involved_settings": ["测试场景"],
            },
        ],
    }
    hierarchy_path.write_text(
        yaml.safe_dump(hierarchy, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    outline_path = novel_root / "src" / "outline.md"
    outline_path.write_text(
        "# 测试小说\n\n"
        "## 第一篇\n\n"
        "> 篇弧线: 开篇\n\n"
        "### 第一节\n\n"
        "> 节结构: 起承\n\n"
        "#### 第一章\n\n"
        "> 内容焦点: 开篇\n"
        "> 出场角色: char_001\n"
        "> 涉及设定: 测试场景\n\n"
        "#### 第二章\n\n"
        "> 内容焦点: 承接\n"
        "> 出场角色: char_001\n"
        "> 涉及设定: 测试场景\n",
        encoding="utf-8",
    )

    story_dir = novel_root / "src" / "story"
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "background.md").write_text("# 背景\n\n测试背景。", encoding="utf-8")
    (story_dir / "foundation.md").write_text("# 设定\n\n测试设定。", encoding="utf-8")

    (novel_root / "src" / "characters" / "char_001.md").write_text(
        "# 角色一\n\n## 背景\n\n角色背景。\n\n## 外貌\n\n普通。\n\n## 性格\n\n- 冷静\n- 直接\n",
        encoding="utf-8",
    )
    (novel_root / "src" / "world" / "rules.md").write_text(
        "# 世界规则\n\n## 力量体系\n- 测试规则\n",
        encoding="utf-8",
    )
    (novel_root / "src" / "world" / "terminology.md").write_text(
        "# 术语表\n\n| 术语 | 定义 | 分类 |\n|------|------|------|\n| 测试术语 | 定义 | concept |\n",
        encoding="utf-8",
    )
    (novel_root / "src" / "world" / "entities").mkdir(parents=True, exist_ok=True)
    (novel_root / "data" / "style").mkdir(parents=True, exist_ok=True)
    (novel_root / "data" / "style" / "fingerprint.yaml").write_text(
        "voice: 测试语气\nlanguage_style: 测试句式\nrhythm: 测试节奏\n",
        encoding="utf-8",
    )
    return tmp_path, novel_root


def test_discovery_appends_ideation_and_stays_in_discovery(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("主角是普通上班族")

    state = state_store.load_or_create()
    assert state.stage == BookStage.DISCOVERY
    assert result.stage == BookStage.DISCOVERY
    assert result.blocked is False
    assert result.next_action == "request_more_background"
    assert "主角是普通上班族" in planning_store.ideation_path.read_text(encoding="utf-8")
    assert "背景" in result.message


def test_foundation_confirmation_promotes_drafts_and_advances_to_rolling_outline(
    tmp_path: Path,
):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_foundation_draft(background="背景A", foundation="设定B")
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("基础设定准备好了，开始 outline")

    state = state_store.load_or_create()
    assert result.blocked is False
    assert result.stage == BookStage.ROLLING_OUTLINE
    assert result.next_action == "request_outline_confirmation"
    assert state.stage == BookStage.ROLLING_OUTLINE
    assert state.pending_confirmation == "outline_scope"
    assert state.last_agent_action == "requested_outline_confirmation"
    _, background_body = parse_toml_front_matter(
        (planning_store.story_src_dir / "background.md").read_text(encoding="utf-8")
    )
    _, foundation_body = parse_toml_front_matter(
        (planning_store.story_src_dir / "foundation.md").read_text(encoding="utf-8")
    )
    assert background_body.strip() == "背景A"
    assert foundation_body.strip() == "设定B"


def test_missing_outline_blocks_writing_with_request_outline_confirmation(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("写 ch_001")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.next_action == "request_outline_confirmation"
    assert result.stage == BookStage.DISCOVERY
    assert state.stage == BookStage.DISCOVERY
    assert state.current_chapter == ""


def test_ambiguous_writing_text_does_not_mutate_current_chapter(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_003"
    state.last_agent_action = "seed"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("写作时要注意 10 个问题")

    state = state_store.load_or_create()
    assert result.next_action == "request_more_background"
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.current_chapter == "ch_003"


def test_negated_chapter_requests_do_not_enter_chapter_flow(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_003"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    for message in ("不要写第1章", "先别写第1章"):
        result = orchestrator.handle_user_message(message)
        state = state_store.load_or_create()
        assert result.blocked is True
        assert result.stage == BookStage.CHAPTER_PREFLIGHT
        assert result.next_action == "ignore"
        assert state.stage == BookStage.CHAPTER_PREFLIGHT
        assert state.current_chapter == "ch_003"


def test_suffix_negated_chapter_request_does_not_enter_chapter_flow(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_003"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("第1章不要写")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert result.next_action == "ignore"
    assert state.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.current_chapter == "ch_003"


def test_postfix_negated_chapter_request_does_not_enter_chapter_flow(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_003"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("写第1章不要")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert result.next_action == "ignore"
    assert state.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.current_chapter == "ch_003"


def test_postfix_prefixed_chapter_request_does_not_enter_chapter_flow(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_003"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("帮我写第1章不要")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert result.next_action == "ignore"
    assert state.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.current_chapter == "ch_003"


def test_spaced_chapter_request_records_current_chapter(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("帮我写第 1 章")

    state = state_store.load_or_create()
    assert result.blocked is False
    assert result.next_action == "chapter_preflight"
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.current_chapter == "ch_001"
    assert state.stage == BookStage.CHAPTER_PREFLIGHT


def test_mixed_foundation_and_outline_prefers_foundation_promotion(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_foundation_draft(background="背景A", foundation="设定B")
    planning_store.save_outline_draft("# 大纲草案")
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("基础设定准备好了，可以确认大纲范围")

    state = state_store.load_or_create()
    assert result.blocked is False
    assert result.next_action == "request_outline_confirmation"
    assert result.stage == BookStage.ROLLING_OUTLINE
    assert state.stage == BookStage.ROLLING_OUTLINE
    assert state.pending_confirmation == "outline_scope"
    _, background_body = parse_toml_front_matter(
        (planning_store.story_src_dir / "background.md").read_text(encoding="utf-8")
    )
    _, foundation_body = parse_toml_front_matter(
        (planning_store.story_src_dir / "foundation.md").read_text(encoding="utf-8")
    )
    assert background_body.strip() == "背景A"
    assert foundation_body.strip() == "设定B"
    assert not planning_store.outline_src_path.exists()


def test_outline_confirmation_promotes_outline_and_advances_to_chapter_preflight(
    tmp_path: Path,
):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_outline_draft("# 大纲草案")
    state = state_store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state.last_agent_action = "requested_outline_confirmation"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("大纲范围确认，可以直接写")

    state = state_store.load_or_create()
    assert result.blocked is False
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert result.next_action == "chapter_preflight"
    assert state.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.pending_confirmation == ""
    assert state.last_agent_action == "promoted_outline"
    assert planning_store.outline_src_path.read_text(encoding="utf-8") == "# 大纲草案"


def test_ambiguous_outline_question_does_not_promote_outline(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_outline_draft("# 大纲草案")
    state = state_store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state.last_agent_action = "requested_outline_confirmation"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("可以先确认一下范围吗？")

    state = state_store.load_or_create()
    assert result.stage == BookStage.ROLLING_OUTLINE
    assert state.stage == BookStage.ROLLING_OUTLINE
    assert state.pending_confirmation == "outline_scope"
    assert not planning_store.outline_src_path.exists()


def test_negated_outline_confirmation_does_not_promote_outline(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_outline_draft("# 大纲草案")
    state = state_store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("先不确认大纲范围")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.ROLLING_OUTLINE
    assert result.next_action == "ignore"
    assert state.stage == BookStage.ROLLING_OUTLINE
    assert state.pending_confirmation == "outline_scope"
    assert not planning_store.outline_src_path.exists()


def test_suffix_negated_outline_confirmation_does_not_promote_outline(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_outline_draft("# 大纲草案")
    state = state_store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("大纲范围不确认")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.ROLLING_OUTLINE
    assert result.next_action == "ignore"
    assert state.stage == BookStage.ROLLING_OUTLINE
    assert state.pending_confirmation == "outline_scope"
    assert not planning_store.outline_src_path.exists()


def test_plain_negated_outline_confirmation_does_not_promote_outline(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_outline_draft("# 大纲草案")
    state = state_store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("不确认大纲范围")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.ROLLING_OUTLINE
    assert result.next_action == "ignore"
    assert state.stage == BookStage.ROLLING_OUTLINE
    assert state.pending_confirmation == "outline_scope"
    assert not planning_store.outline_src_path.exists()


def test_negative_agreement_outline_confirmation_does_not_promote_outline(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_outline_draft("# 大纲草案")
    state = state_store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("我不同意大纲范围")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.ROLLING_OUTLINE
    assert result.next_action == "ignore"
    assert state.stage == BookStage.ROLLING_OUTLINE
    assert state.pending_confirmation == "outline_scope"
    assert not planning_store.outline_src_path.exists()


def test_natural_outline_approval_promotes_outline(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_outline_draft("# 大纲草案")
    state = state_store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state.last_agent_action = "requested_outline_confirmation"
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("我同意大纲范围")

    state = state_store.load_or_create()
    assert result.blocked is False
    assert result.next_action == "chapter_preflight"
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.stage == BookStage.CHAPTER_PREFLIGHT
    assert state.pending_confirmation == ""
    assert planning_store.outline_src_path.read_text(encoding="utf-8") == "# 大纲草案"


def test_negated_foundation_confirmation_does_not_promote_foundation(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    planning_store.save_foundation_draft(background="背景A", foundation="设定B")
    state = state_store.load_or_create()
    state.stage = BookStage.DISCOVERY
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("先不要开始 outline")

    state = state_store.load_or_create()
    assert result.blocked is True
    assert result.stage == BookStage.DISCOVERY
    assert result.next_action == "ignore"
    assert state.stage == BookStage.DISCOVERY
    assert state.current_chapter == ""
    assert not (planning_store.story_src_dir / "background.md").exists()
    assert not (planning_store.story_src_dir / "foundation.md").exists()


def test_writing_request_after_outline_confirmation_records_current_chapter(
    tmp_path: Path,
):
    state_store = BookStateStore(tmp_path, "demo")
    planning_store = StoryPlanningStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state_store.save(state)
    orchestrator = OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.handle_user_message("写 ch_001")

    state = state_store.load_or_create()
    assert result.blocked is False
    assert result.stage == BookStage.CHAPTER_PREFLIGHT
    assert result.next_action == "chapter_preflight"
    assert state.current_chapter == "ch_001"
    assert state.stage == BookStage.CHAPTER_PREFLIGHT


def test_run_preflight_reports_missing_previous_chapter_when_scope_exists(
    tmp_path: Path,
):
    root, _novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_002"
    state_store.save(state)

    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.run_preflight("ch_002")

    assert result["ok"] is False
    assert result["reason"] == "missing_previous_chapter"
    assert "ch_001" in result["missing_items"]


def test_run_preflight_rejects_missing_chapter_node_even_with_previous_content(
    tmp_path: Path,
):
    root, _novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_003"
    state_store.save(state)

    manuscript_dir = root / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_001"
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    (manuscript_dir / "ch_002.md").write_text("第二章正文", encoding="utf-8")

    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    result = orchestrator.run_preflight("ch_003")

    assert result["ok"] is False
    assert result["reason"] == "missing_chapter_scope"
    assert result["missing_items"] == ["ch_003"]


def test_build_chapter_packet_persists_context_snapshot(tmp_path: Path):
    root, novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    planning_store.promote_foundation()
    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
    )

    packet = orchestrator.build_chapter_packet("ch_001")

    snapshot_dir = novel_root / "data" / "test_outputs" / "context_packets"
    snapshot_path = snapshot_dir / "ch_001.yaml"

    assert packet["story_background"]
    assert packet["style_documents"]
    assert packet["prompt_sections"]
    assert snapshot_path.exists()
    assert yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))["chapter_id"] == "ch_001"


def test_delegate_writing_uses_write_chapter_only(
    tmp_path: Path,
):
    root, novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    planning_store.promote_foundation()
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_001"
    state_store.save(state)

    calls: dict[str, int] = {"write_chapter": 0, "review_chapter": 0}

    def write_chapter(args: dict) -> dict:
        calls["write_chapter"] += 1
        assert args["chapter_id"] == "ch_001"
        return {
            "ok": True,
            "chapter_id": "ch_001",
            "draft_path": str(
                novel_root / "data" / "manuscript" / "arc_001" / "ch_001.md"
            ),
        }

    def review_chapter(args: dict) -> dict:
        calls["review_chapter"] += 1
        return {"ok": True}

    executors = {name: (lambda args: {"ok": True}) for name in WRITING_TOOLKIT}
    executors["write_chapter"] = write_chapter
    executors["review_chapter"] = review_chapter

    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
        tool_executors=executors,
    )

    result = orchestrator.delegate_writing("ch_001")

    assert result["ok"] is True
    assert result["chapter_id"] == "ch_001"
    assert calls["write_chapter"] == 1
    assert calls["review_chapter"] == 0


def test_delegate_writing_records_failure_when_executor_raises(
    tmp_path: Path,
):
    root, novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    planning_store.promote_foundation()
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_001"
    state_store.save(state)

    def write_chapter(args: dict) -> dict:
        raise RuntimeError("boom")

    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
        tool_executors={"write_chapter": write_chapter},
    )

    result = orchestrator.delegate_writing("ch_001")

    workflow = WorkflowScheduler(root, "demo").load_workflow("ch_001")
    loaded_state = state_store.load_or_create()

    assert result["ok"] is False
    assert result["reason"] == "boom"
    assert workflow is not None
    assert next(stage for stage in workflow.stages if stage.name == "writing").status == "failed"
    assert loaded_state.blocking_reason == "writing_failed"
    assert loaded_state.last_agent_action == "delegated_writing_failed"


def test_delegate_writing_persists_failure_when_fail_stage_raises(
    tmp_path: Path,
    monkeypatch,
):
    root, novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    planning_store.promote_foundation()
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_001"
    state_store.save(state)

    def write_chapter(args: dict) -> dict:
        raise RuntimeError("boom")

    def broken_fail_stage(self, state, stage_name: str, error: str):
        raise RuntimeError("cannot persist failure")

    monkeypatch.setattr(WorkflowScheduler, "fail_stage", broken_fail_stage, raising=True)

    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
        tool_executors={"write_chapter": write_chapter},
    )

    result = orchestrator.delegate_writing("ch_001")

    workflow = WorkflowScheduler(root, "demo").load_workflow("ch_001")
    assert result["ok"] is False
    assert workflow is not None
    writing_stage = next(stage for stage in workflow.stages if stage.name == "writing")
    assert writing_stage.status == "failed"
    assert workflow.error.startswith("writing:")


def test_delegate_writing_sanitizes_invalid_draft_path(
    tmp_path: Path,
):
    root, novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    planning_store.promote_foundation()
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_001"
    state_store.save(state)

    def write_chapter(args: dict) -> dict:
        return {
            "ok": True,
            "chapter_id": "ch_001",
            "draft_path": "../../outside.md",
        }

    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
        tool_executors={"write_chapter": write_chapter},
    )

    result = orchestrator.delegate_writing("ch_001")

    workflow = WorkflowScheduler(root, "demo").load_workflow("ch_001")

    assert result["ok"] is True
    assert workflow is not None
    assert workflow.draft_path == ""


def test_delegate_writing_advances_book_state_and_creates_workflow(
    tmp_path: Path,
):
    root, novel_root = _bootstrap_novel(tmp_path)
    state_store = BookStateStore(root, "demo")
    planning_store = StoryPlanningStore(root, "demo")
    planning_store.promote_foundation()
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state.current_chapter = "ch_001"
    state_store.save(state)

    def write_chapter(args: dict) -> dict:
        draft_path = novel_root / "data" / "manuscript" / "arc_001" / "ch_001.md"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text("正文", encoding="utf-8")
        return {"ok": True, "chapter_id": args["chapter_id"], "draft_path": str(draft_path)}

    orchestrator = OpenWriteOrchestrator.for_testing(
        root,
        "demo",
        state_store=state_store,
        planning_store=planning_store,
        tool_executors={"write_chapter": write_chapter},
    )

    result = orchestrator.delegate_writing("ch_001")

    loaded_state = state_store.load_or_create()
    workflow = WorkflowScheduler(root, "demo").load_workflow("ch_001")

    assert result["ok"] is True
    assert result["next_stage"] == BookStage.REVIEW_AND_REVISE.value
    assert loaded_state.stage == BookStage.REVIEW_AND_REVISE
    assert workflow is not None
    assert workflow.current_stage == "review"
