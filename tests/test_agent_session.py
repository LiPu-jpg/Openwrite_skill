from pathlib import Path

import yaml

from tools.agent.session_state import (
    DanteSessionState,
    SessionStateStore,
    MAX_RECENT_TURNS,
)


def test_load_or_create_creates_default_session_state(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")

    state = store.load_or_create()

    assert state.session_id == "demo"
    assert state.active_agent == "dante"
    assert state.conversation_summary == ""
    assert state.recent_turns == []
    assert state.working_memory == {}
    assert state.open_questions == []
    assert state.recent_files == []
    assert state.last_action == ""
    assert state.compression_markers == []
    assert state.updated_at != ""
    assert store.path.exists()
    assert store.path.name == "agent_session.yaml"


def test_save_compresses_old_turns_into_summary(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    state = DanteSessionState(session_id="demo")
    state.recent_turns = [
        {"role": "user", "content": f"turn-{index:02d}"} for index in range(MAX_RECENT_TURNS + 2)
    ]

    store.save(state)
    loaded = store.load_or_create()

    assert len(loaded.recent_turns) == MAX_RECENT_TURNS
    assert [turn["content"] for turn in loaded.recent_turns] == [
        f"turn-{index:02d}" for index in range(2, MAX_RECENT_TURNS + 2)
    ]
    assert "turn-00" in loaded.conversation_summary
    assert "turn-01" in loaded.conversation_summary
    assert loaded.compression_markers
    assert loaded.compression_markers[-1]["dropped_turns"] == 2
    assert loaded.compression_markers[-1]["kept_turns"] == MAX_RECENT_TURNS


def test_load_or_create_repairs_corrupt_session_file(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("session_id: demo\nrecent_turns: [", encoding="utf-8")

    state = store.load_or_create()

    assert state.session_id == "demo"
    assert state.active_agent == "dante"
    assert state.recent_turns == []
    assert yaml.safe_load(store.path.read_text(encoding="utf-8"))["session_id"] == "demo"
