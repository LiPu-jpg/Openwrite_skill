import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.cli as cli_module

from tools.agent.tool_runtime import build_tool_executors
from tools.agent.toolkits import ORCHESTRATOR_TOOLKIT, WRITING_TOOLKIT


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
    assert "review_chapter" not in ORCHESTRATOR_TOOLKIT


def test_writing_toolkit_stays_small():
    assert WRITING_TOOLKIT == {
        "write_chapter",
        "get_context",
        "list_chapters",
        "get_truth_files",
    }
