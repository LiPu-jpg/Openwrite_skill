from pathlib import Path

from tools.agent.book_state import BookStage, BookStateStore


def test_load_or_create_defaults_to_discovery(tmp_path: Path):
    store = BookStateStore(tmp_path, "demo")

    state = store.load_or_create()

    assert state.stage == BookStage.DISCOVERY
    assert state.novel_id == "demo"


def test_save_and_reload_persists_book_state(tmp_path: Path):
    store = BookStateStore(tmp_path, "demo")

    state = store.load_or_create()
    state.stage = BookStage.ROLLING_OUTLINE
    state.pending_confirmation = "outline_scope"
    state.blocking_reason = "waiting_for_user"
    state.last_agent_action = "requested_outline_confirmation"
    store.save(state)

    loaded = store.load_or_create()

    assert loaded.stage == BookStage.ROLLING_OUTLINE
    assert loaded.pending_confirmation == "outline_scope"
    assert loaded.blocking_reason == "waiting_for_user"
    assert loaded.last_agent_action == "requested_outline_confirmation"
    assert loaded.novel_id == "demo"


def test_load_or_create_repairs_empty_book_state_file(tmp_path: Path):
    store = BookStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("", encoding="utf-8")

    state = store.load_or_create()

    assert state.stage == BookStage.DISCOVERY
    assert state.novel_id == "demo"
    assert store.path.read_text(encoding="utf-8").strip() != ""


def test_load_or_create_repairs_malformed_yaml(tmp_path: Path):
    store = BookStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("novel_id: demo\nstage: [", encoding="utf-8")

    state = store.load_or_create()

    assert state.stage == BookStage.DISCOVERY
    assert state.novel_id == "demo"
    assert store.path.read_text(encoding="utf-8").strip() != ""


def test_load_or_create_repairs_non_mapping_yaml(tmp_path: Path):
    store = BookStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("- discovery\n- outline", encoding="utf-8")

    state = store.load_or_create()

    assert state.stage == BookStage.DISCOVERY
    assert state.novel_id == "demo"
    assert store.path.read_text(encoding="utf-8").strip() != ""


def test_load_or_create_repairs_unknown_stage_yaml(tmp_path: Path):
    store = BookStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("novel_id: demo\nstage: not-a-real-stage", encoding="utf-8")

    state = store.load_or_create()

    assert state.stage == BookStage.DISCOVERY
    assert state.novel_id == "demo"
    assert store.path.read_text(encoding="utf-8").strip() != ""


def test_save_uses_atomic_temp_file_and_replace(tmp_path: Path, monkeypatch):
    store = BookStateStore(tmp_path, "demo")
    state = store.load_or_create()

    original_write_text = Path.write_text
    original_replace = Path.replace
    wrote_paths: list[Path] = []
    replaced_targets: list[Path] = []

    def guarded_write_text(self: Path, *args, **kwargs):
        wrote_paths.append(self)
        if self == store.path:
            raise AssertionError("save() wrote directly to the final file")
        return original_write_text(self, *args, **kwargs)

    def guarded_replace(self: Path, target: Path):
        replaced_targets.append(target)
        return original_replace(self, target)

    monkeypatch.setattr(Path, "write_text", guarded_write_text, raising=True)
    monkeypatch.setattr(Path, "replace", guarded_replace, raising=True)

    state.last_agent_action = "atomic-save-check"
    store.save(state)

    assert store.path.read_text(encoding="utf-8")
    assert store.path not in wrote_paths
    assert replaced_targets == [store.path]
