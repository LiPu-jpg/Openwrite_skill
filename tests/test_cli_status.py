import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.cli as cli_module


def _write_config(tmp_path: Path, content: str) -> None:
    (tmp_path / "novel_config.yaml").write_text(content, encoding="utf-8")


def test_cmd_status_ignores_draft_markdown_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_config(
        tmp_path,
        "novel_id: demo\ncurrent_arc: arc_001\ncurrent_chapter: ch_001\n",
    )

    manuscript_dir = tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_001"
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    (manuscript_dir / "ch_001.md").write_text("# 第一章\n\n正文", encoding="utf-8")
    (manuscript_dir / "ch_001_draft.md").write_text("# 第一章草稿\n\n草稿", encoding="utf-8")

    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))

    info_messages: list[str] = []
    monkeypatch.setattr(cli_module.logger, "info", info_messages.append)

    assert cli_module._cmd_status(SimpleNamespace()) == 0
    assert "已写章节: 1" in info_messages


def test_cli_save_load_uses_supported_manuscript_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_config(
        tmp_path,
        "novel_id: demo\ncurrent_arc: arc_002\ncurrent_chapter: ch_002\n",
    )

    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))

    saved_path = cli_module._save_chapter(
        tmp_path,
        "demo",
        "ch_002",
        "第二章",
        "正文内容",
    )

    expected_path = (
        tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_002" / "ch_002.md"
    )
    assert saved_path == expected_path
    assert expected_path.read_text(encoding="utf-8") == "# 第二章\n\n正文内容"

    legacy_path = (
        tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_001" / "ch_002.md"
    )
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text("# 第二章\n\n旧内容", encoding="utf-8")

    assert cli_module._load_chapter(tmp_path, "demo", "ch_002") == "# 第二章\n\n正文内容"

    info_messages: list[str] = []
    monkeypatch.setattr(cli_module.logger, "info", info_messages.append)

    assert cli_module._cmd_status(SimpleNamespace()) == 0
    assert "已写章节: 1" in info_messages


def test_main_status_command_uses_current_project_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_config(
        tmp_path,
        "novel_id: demo\ncurrent_arc: arc_001\ncurrent_chapter: ch_001\n",
    )

    manuscript_dir = tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_001"
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    (manuscript_dir / "ch_001.md").write_text("# 第一章\n\n正文", encoding="utf-8")
    (manuscript_dir / "ch_001_draft.md").write_text("# 第一章草稿\n\n草稿", encoding="utf-8")

    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))
    monkeypatch.setattr(sys, "argv", ["openwrite", "status"])

    info_messages: list[str] = []
    monkeypatch.setattr(cli_module.logger, "info", info_messages.append)

    assert cli_module.main() == 0
    assert "已写章节: 1" in info_messages


def test_cmd_status_counts_unique_final_chapters_across_arcs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_config(
        tmp_path,
        "novel_id: demo\ncurrent_arc: arc_002\ncurrent_chapter: ch_021\n",
    )

    arc1 = tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_001"
    arc2 = tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_002"
    arc1.mkdir(parents=True, exist_ok=True)
    arc2.mkdir(parents=True, exist_ok=True)
    (arc1 / "ch_001.md").write_text("# 第一章\n\n正文", encoding="utf-8")
    (arc2 / "ch_021.md").write_text("# 第二十一章\n\n正文", encoding="utf-8")
    (arc2 / "ch_021_draft.md").write_text("# 第二十一章草稿\n\n草稿", encoding="utf-8")

    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))

    info_messages: list[str] = []
    monkeypatch.setattr(cli_module.logger, "info", info_messages.append)

    assert cli_module._cmd_status(SimpleNamespace()) == 0
    assert "已写章节: 2" in info_messages
