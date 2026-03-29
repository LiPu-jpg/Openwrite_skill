from pathlib import Path

from tools.truth_manager import TruthFiles, TruthFilesManager


def test_save_truth_files_writes_frontmatter_and_load_returns_body(tmp_path: Path):
    manager = TruthFilesManager(tmp_path, "demo")
    truth = TruthFiles(
        current_state="# 当前状态\n\n正文A",
        ledger="# 账本\n\n正文B",
        relationships="# 关系\n\n正文C",
    )

    manager.save_truth_files(truth)

    current_state_text = (manager.world_dir / "current_state.md").read_text(encoding="utf-8")
    assert current_state_text.startswith("+++\n")
    assert 'id = "current_state"' in current_state_text
    assert 'type = "runtime_truth"' in current_state_text

    loaded = manager.load_truth_files()
    assert loaded.current_state == "# 当前状态\n\n正文A"
    assert loaded.ledger == "# 账本\n\n正文B"
    assert loaded.relationships == "# 关系\n\n正文C"
    assert loaded.metadata["current_state"]["id"] == "current_state"


def test_load_truth_files_parses_existing_frontmatter(tmp_path: Path):
    manager = TruthFilesManager(tmp_path, "demo")
    manager.world_dir.mkdir(parents=True, exist_ok=True)
    (manager.world_dir / "current_state.md").write_text(
        """+++
id = "current_state"
type = "runtime_truth"
summary = "当前局势摘要。"
detail_refs = ["scene", "actors"]
+++

# 当前状态

正文内容。
""",
        encoding="utf-8",
    )

    loaded = manager.load_truth_files()

    assert loaded.current_state == "# 当前状态\n\n正文内容。\n"
    assert loaded.metadata["current_state"]["summary"] == "当前局势摘要。"
