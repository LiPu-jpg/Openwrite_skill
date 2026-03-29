"""CLI 辅助函数测试。"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.cli import (
    _collect_truth_updates,
    _exec_get_truth_files,
    _get_latest_chapter,
    _get_next_chapter,
    _safe_stem,
    _get_test_output_dir,
    _save_chapter,
)


def _write_config(root: Path, novel_id: str, current_arc: str = "arc_001") -> None:
    (root / "novel_config.yaml").write_text(
        (
            f"novel_id: {novel_id}\n"
            f"style_id: {novel_id}\n"
            f"current_arc: {current_arc}\n"
            "current_chapter: ch_001\n"
        ),
        encoding="utf-8",
    )


def test_next_and_latest_chapter_from_manuscript(tmp_path: Path):
    novel_id = "test_novel"
    _write_config(tmp_path, novel_id)

    _save_chapter(tmp_path, novel_id, "ch_003", "第三章", "内容A")
    _save_chapter(tmp_path, novel_id, "ch_010", "第十章", "内容B")

    assert _get_latest_chapter(tmp_path, novel_id) == "ch_010"
    assert _get_next_chapter(tmp_path, novel_id) == "ch_011"


def test_next_and_latest_defaults_when_empty(tmp_path: Path):
    novel_id = "empty_novel"
    _write_config(tmp_path, novel_id)

    assert _get_latest_chapter(tmp_path, novel_id) == "ch_001"
    assert _get_next_chapter(tmp_path, novel_id) == "ch_001"


def test_test_output_dir_path(tmp_path: Path):
    novel_id = "demo"
    out = _get_test_output_dir(tmp_path, novel_id, "context_packets")

    assert out == tmp_path / "data" / "novels" / novel_id / "data" / "test_outputs" / "context_packets"


def test_collect_truth_updates_maps_canonical_and_aliases():
    updates = _collect_truth_updates(
        {
            "current_state": "A",
            "ledger": "B",
            "character_matrix": "C",
            "ignored": "X",
            "empty": "",
        }
    )

    assert updates == {
        "current_state": "A",
        "ledger": "B",
        "relationships": "C",
    }


def test_safe_stem_rejects_path_and_keeps_valid_chars():
    assert _safe_stem("../evil") == ""
    assert _safe_stem("a/b") == ""
    assert _safe_stem("陈 明-01") == "陈_明-01"


def test_exec_get_truth_files_returns_canonical_keys_only(tmp_path: Path):
    novel_id = "demo"
    _write_config(tmp_path, novel_id)

    world_dir = tmp_path / "data" / "novels" / novel_id / "data" / "world"
    world_dir.mkdir(parents=True, exist_ok=True)
    (world_dir / "current_state.md").write_text("状态", encoding="utf-8")
    (world_dir / "ledger.md").write_text("账本", encoding="utf-8")
    (world_dir / "relationships.md").write_text("关系", encoding="utf-8")

    result = _exec_get_truth_files(tmp_path)

    assert result == {
        "current_state": "状态",
        "ledger": "账本",
        "relationships": "关系",
    }
