import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.cli as cli_module

from tools.agent.tool_runtime import build_tool_executors
from tools.agent.toolkits import (
    DANTE_ACTION_TOOLKIT,
    DANTE_DIRECT_TOOLKIT,
    ORCHESTRATOR_TOOLKIT,
    WRITING_TOOLKIT,
)


def test_build_tool_executors_contains_existing_openwrite_tools(tmp_path: Path):
    executors = build_tool_executors(project_root=tmp_path)
    assert ORCHESTRATOR_TOOLKIT.issubset(executors.keys())
    assert WRITING_TOOLKIT.issubset(executors.keys())


def test_build_tool_executors_uses_public_cli_factory(monkeypatch, tmp_path: Path):
    monkeypatch.delattr(cli_module, "_exec_write_chapter", raising=False)
    monkeypatch.delattr(cli_module, "_exec_get_status", raising=False)

    def fake_factory(project_root: Path):
        assert project_root == tmp_path
        return {
            "get_status": lambda a: {"ok": True},
            "write_chapter": lambda a: {"ok": True},
        }

    monkeypatch.setattr(cli_module, "build_cli_tool_executors", fake_factory, raising=False)

    executors = build_tool_executors(project_root=tmp_path)
    assert executors["get_status"]({}) == {"ok": True}
    assert executors["write_chapter"]({}) == {"ok": True}


def test_orchestrator_toolkit_excludes_write_tools():
    assert "get_status" in ORCHESTRATOR_TOOLKIT
    assert "write_chapter" not in ORCHESTRATOR_TOOLKIT
    assert "review_chapter" in ORCHESTRATOR_TOOLKIT
    assert "create_character" in ORCHESTRATOR_TOOLKIT


def test_writing_toolkit_stays_small():
    assert WRITING_TOOLKIT == {
        "write_chapter",
        "get_context",
        "list_chapters",
        "get_truth_files",
    }


def test_dante_direct_toolkit_exposes_only_light_tools():
    assert DANTE_DIRECT_TOOLKIT == {
        "get_status",
        "get_context",
        "list_chapters",
        "get_truth_files",
        "query_world",
        "get_world_relations",
    }
    assert "write_chapter" not in DANTE_DIRECT_TOOLKIT
    assert "review_chapter" not in DANTE_DIRECT_TOOLKIT


def test_dante_action_toolkit_exposes_high_level_actions():
    assert DANTE_ACTION_TOOLKIT == {
        "record_ideation",
        "summarize_ideation",
        "confirm_ideation_summary",
        "generate_foundation_draft",
        "confirm_foundation",
        "generate_outline_draft",
        "confirm_outline_scope",
        "run_chapter_preflight",
        "delegate_chapter_write",
        "delegate_chapter_review",
        "advance_book_state",
        "resume_session",
    }
    assert "get_status" not in DANTE_ACTION_TOOLKIT
    assert "write_chapter" not in DANTE_ACTION_TOOLKIT


def test_build_dante_tool_layers_groups_direct_tools_without_reassembling_raw_executors(
    monkeypatch, tmp_path: Path
):
    executors = {
        "get_status": lambda a: {"ok": True},
        "get_context": lambda a: {"ok": True},
        "query_world": lambda a: {"ok": True},
        "write_chapter": lambda a: {"ok": True},
    }

    def fake_factory(project_root: Path):
        assert project_root == tmp_path
        return executors

    monkeypatch.setattr(cli_module, "build_cli_tool_executors", fake_factory)

    layers = cli_module.build_dante_tool_layers(tmp_path)

    assert layers["direct_toolkit"] == DANTE_DIRECT_TOOLKIT
    assert layers["action_toolkit"] == DANTE_ACTION_TOOLKIT
    assert layers["direct_tool_executors"] == {
        name: executors[name] for name in DANTE_DIRECT_TOOLKIT if name in executors
    }
    assert "write_chapter" not in layers["direct_tool_executors"]
    assert layers["tool_executors"] is executors
