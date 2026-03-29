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
                            "reason": "count",
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


def test_load_or_create_upgrades_partial_session_without_data_loss(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        yaml.safe_dump(
            {
                "session_id": "legacy-1",
                "conversation_summary": "legacy summary",
                "recent_turns": [
                    {"role": "user", "content": "old question"},
                ],
                "updated_at": "2026-03-29T09:00:00",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    state = store.load_or_create()

    assert state.session_id == "legacy-1"
    assert state.conversation_summary == "legacy summary"
    assert [turn.content for turn in state.recent_turns] == ["old question"]
    assert state.active_agent == "dante"
    assert state.working_memory == {}
    assert yaml.safe_load(store.path.read_text(encoding="utf-8"))["session_id"] == "legacy-1"


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
    huge_text = "x" * (MAX_SESSION_BYTES)
    state = DanteSessionState(session_id="demo")
    state.recent_turns = [
        SessionTurn(role="user", content="first"),
        SessionTurn(role="assistant", content=f"second {huge_text}"),
    ]

    store.save(state)
    loaded = store.load_or_create()
    persisted_size = len(store.path.read_text(encoding="utf-8").encode("utf-8"))

    assert persisted_size <= MAX_SESSION_BYTES
    assert loaded.recent_turns
    assert loaded.compression_markers[-1].reason == "size"


def test_save_compresses_oversized_metadata_payload(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    huge_text = "x" * (MAX_SESSION_BYTES)
    state = DanteSessionState(session_id="demo")
    state.working_memory = {"notes": huge_text}
    state.open_questions = [huge_text, huge_text]
    state.recent_files = [f"file-{index}-{huge_text}" for index in range(3)]
    state.last_action = huge_text

    store.save(state)
    loaded = store.load_or_create()
    persisted_size = len(store.path.read_text(encoding="utf-8").encode("utf-8"))

    assert persisted_size <= MAX_SESSION_BYTES
    assert loaded.working_memory
    assert loaded.open_questions
    assert loaded.recent_files
    assert len(loaded.last_action) <= len(huge_text)
    assert loaded.compression_markers[-1].reason == "size"


def test_save_compresses_metadata_only_payload_without_missing_helper(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    state = DanteSessionState(session_id="demo")
    state.working_memory = {"notes": "x" * (MAX_SESSION_BYTES * 2)}
    state.last_action = "y" * (MAX_SESSION_BYTES // 2)

    store.save(state)

    persisted_size = len(store.path.read_text(encoding="utf-8").encode("utf-8"))
    loaded = store.load_or_create()

    assert persisted_size <= MAX_SESSION_BYTES
    assert loaded.working_memory
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


def test_load_or_create_persists_normalized_malformed_data(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        yaml.safe_dump(
            {
                "session_id": "legacy-2",
                "conversation_summary": "summary",
                "recent_turns": [
                    {"role": "user", "content": "prompt"},
                ],
                "compression_markers": [
                    {"compressed_at": "2026-03-30T10:00:00", "reason": "bogus"}
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    state = store.load_or_create()
    reloaded = yaml.safe_load(store.path.read_text(encoding="utf-8"))

    assert state.session_id == "legacy-2"
    assert reloaded["active_agent"] == "dante"
    assert reloaded["working_memory"] == {}
    assert reloaded["compression_markers"][0]["reason"] == "count"


def test_load_or_create_persists_normalized_schema_complete_data(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        yaml.safe_dump(
            {
                "session_id": "legacy-3",
                "active_agent": "dante",
                "conversation_summary": "",
                "recent_turns": [],
                "working_memory": {},
                "open_questions": [],
                "recent_files": [],
                "last_action": "",
                "compression_markers": [
                    {
                        "compressed_at": "2026-03-30T10:00:00",
                        "dropped_turns": "bad",
                        "kept_turns": 1,
                        "reason": "bogus",
                    }
                ],
                "updated_at": "",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    state = store.load_or_create()
    reloaded = yaml.safe_load(store.path.read_text(encoding="utf-8"))

    assert state.session_id == "legacy-3"
    assert state.compression_markers[0].reason == "count"
    assert reloaded["compression_markers"][0]["dropped_turns"] == 0
    assert reloaded["compression_markers"][0]["reason"] == "count"


def test_save_stringifies_unsafe_working_memory_values(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")

    class UnsafeValue:
        pass

    state = DanteSessionState(session_id="demo")
    state.working_memory = {
        "nested": {
            "unsafe": UnsafeValue(),
            "list": [UnsafeValue(), "ok"],
        }
    }

    store.save(state)
    reloaded = yaml.safe_load(store.path.read_text(encoding="utf-8"))

    assert reloaded["working_memory"]["nested"]["unsafe"].startswith("<")
    assert reloaded["working_memory"]["nested"]["list"][0].startswith("<")


def test_load_or_create_refreshes_compression_timestamp_on_load(tmp_path: Path, monkeypatch):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        yaml.safe_dump(
            {
                "session_id": "demo",
                "active_agent": "dante",
                "conversation_summary": "",
                "recent_turns": [
                    {"role": "user", "content": "x" * (MAX_SESSION_BYTES)},
                    {"role": "assistant", "content": "tail"},
                ],
                "working_memory": {},
                "open_questions": [],
                "recent_files": [],
                "last_action": "",
                "compression_markers": [],
                "updated_at": "2026-03-29T09:00:00",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    class FixedDatetime:
        @staticmethod
        def now():
            class FixedNow:
                def isoformat(self):
                    return "2026-03-30T12:34:56"

            return FixedNow()

    monkeypatch.setattr("tools.agent.session_state.datetime", FixedDatetime)

    state = store.load_or_create()
    reloaded = yaml.safe_load(store.path.read_text(encoding="utf-8"))

    assert state.compression_markers[-1].compressed_at == "2026-03-30T12:34:56"
    assert reloaded["compression_markers"][-1]["compressed_at"] == "2026-03-30T12:34:56"


def test_load_or_create_normalizes_malformed_compression_markers(tmp_path: Path):
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
                "compression_markers": [
                    {
                        "compressed_at": "2026-03-30T10:00:00",
                        "dropped_turns": "not-an-int",
                        "kept_turns": 2,
                        "reason": "bogus",
                    },
                    "skip-me",
                ],
                "updated_at": "",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    state = store.load_or_create()

    assert len(state.compression_markers) == 1
    assert state.compression_markers[0].dropped_turns == 0
    assert state.compression_markers[0].kept_turns == 2
    assert state.compression_markers[0].reason == "count"


def test_load_or_create_repairs_corrupt_session_file(tmp_path: Path):
    store = SessionStateStore(tmp_path, "demo")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("session_id: demo\nrecent_turns: [", encoding="utf-8")

    state = store.load_or_create()

    assert state.session_id == "demo"
    assert state.active_agent == "dante"
    assert state.recent_turns == []
    assert yaml.safe_load(store.path.read_text(encoding="utf-8"))["session_id"] == "demo"
