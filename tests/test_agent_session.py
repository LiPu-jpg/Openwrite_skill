from pathlib import Path

import yaml

from tools.agent.session_state import (
    CompressionMarker,
    DanteSessionState,
    SessionTurn,
    SessionStateStore,
    MAX_RECENT_TURNS,
    MAX_SESSION_BYTES,
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
        SessionTurn(role="user", content=f"turn-{index:02d}")
        for index in range(MAX_RECENT_TURNS + 2)
    ]

    store.save(state)
    loaded = store.load_or_create()

    assert len(loaded.recent_turns) == MAX_RECENT_TURNS
    assert [turn.content for turn in loaded.recent_turns] == [
        f"turn-{index:02d}" for index in range(2, MAX_RECENT_TURNS + 2)
    ]
    assert "turn-00" in loaded.conversation_summary
    assert "turn-01" in loaded.conversation_summary
    assert loaded.compression_markers
    assert loaded.compression_markers[-1].dropped_turns == 2
    assert loaded.compression_markers[-1].kept_turns == MAX_RECENT_TURNS


def test_load_or_create_restores_valid_existing_session(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        yaml.safe_dump(
            {
                "session_id": "session-123",
                "active_agent": "dante",
                "conversation_summary": "old summary",
                "recent_turns": [
                    {"role": "assistant", "content": "hello"},
                    {"role": "user", "content": "world"},
                ],
                "working_memory": {"topic": "outline"},
                "open_questions": ["confirm premise"],
                "recent_files": ["src/chapter_1.md"],
                "last_action": "summarize",
                "compression_markers": [
                    {
                        "compressed_at": "2026-03-30T10:00:00",
                        "dropped_turns": 3,
                        "kept_turns": 2,
                    }
                ],
                "updated_at": "2026-03-30T10:05:00",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    state = store.load_or_create()

    assert state.session_id == "session-123"
    assert state.active_agent == "dante"
    assert state.conversation_summary == "old summary"
    assert [turn.content for turn in state.recent_turns] == ["hello", "world"]
    assert isinstance(state.recent_turns[0], SessionTurn)
    assert state.working_memory == {"topic": "outline"}
    assert state.open_questions == ["confirm premise"]
    assert state.recent_files == ["src/chapter_1.md"]
    assert state.last_action == "summarize"
    assert state.compression_markers[0].dropped_turns == 3
    assert isinstance(state.compression_markers[0], CompressionMarker)
    assert state.updated_at == "2026-03-30T10:05:00"


def test_load_or_create_surfaces_filesystem_errors(tmp_path: Path, monkeypatch):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        yaml.safe_dump(
            {
                "session_id": "demo",
                "active_agent": "dante",
                "conversation_summary": "",
                "recent_turns": [],
                "working_memory": {},
                "open_questions": [],
                "recent_files": [],
                "last_action": "",
                "compression_markers": [],
                "updated_at": "",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    def raise_ioerror(self: Path, *args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(Path, "read_text", raise_ioerror, raising=True)

    try:
        store.load_or_create()
    except OSError as exc:
        assert "disk unavailable" in str(exc)
    else:
        raise AssertionError("load_or_create() swallowed a filesystem error")


def test_save_compresses_huge_turns_by_size(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    huge_text = "x" * (MAX_SESSION_BYTES // 2)
    state = DanteSessionState(session_id="demo")
    state.recent_turns = [
        SessionTurn(role="user", content=f"first {huge_text}"),
        SessionTurn(role="assistant", content=f"second {huge_text}"),
    ]

    store.save(state)
    loaded = store.load_or_create()

    assert len(loaded.recent_turns) == 1
    assert loaded.recent_turns[0].content.startswith("second ")
    assert "first" in loaded.conversation_summary
    assert loaded.compression_markers[-1].reason == "size"


def test_repeat_save_is_idempotent_after_compression(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    huge_text = "x" * (MAX_SESSION_BYTES // 2)
    state = DanteSessionState(session_id="demo")
    state.recent_turns = [
        SessionTurn(role="user", content=f"first {huge_text}"),
        SessionTurn(role="assistant", content=f"second {huge_text}"),
    ]

    store.save(state)
    first = store.load_or_create()
    first_summary = first.conversation_summary
    first_turns = list(first.recent_turns)
    first_markers = list(first.compression_markers)

    store.save(first)
    second = store.load_or_create()

    assert second.conversation_summary == first_summary
    assert second.recent_turns == first_turns
    assert second.compression_markers == first_markers


def test_load_or_create_repairs_corrupt_session_file(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("session_id: demo\nrecent_turns: [", encoding="utf-8")

    state = store.load_or_create()

    assert state.session_id == "demo"
    assert state.active_agent == "dante"
    assert state.recent_turns == []
    assert yaml.safe_load(store.path.read_text(encoding="utf-8"))["session_id"] == "demo"
