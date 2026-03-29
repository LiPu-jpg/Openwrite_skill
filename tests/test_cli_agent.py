import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.cli as cli_module
import tools.agent as agent_module
import tools.context_builder as context_builder_module
import tools.llm as llm_module
from tools.agent.book_state import BookStage, BookStateStore
import tools.agent.orchestrator as orchestrator_module
import tools.agent.tool_runtime as tool_runtime_module
from tools.story_planning import StoryPlanningStore


def _fake_args(instruction: str = "查看项目状态", max_turns: int = 20, quiet: bool = False):
    return SimpleNamespace(instruction=instruction, max_turns=max_turns, quiet=quiet)


def test_cmd_agent_routes_through_orchestrator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "novel_config.yaml").write_text("novel_id: demo\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))

    expected_tool_executors = {"get_status": lambda args: {"ok": True}}
    tool_executor_calls: list[Path] = []

    def fake_build_tool_executors(project_root: Path):
        tool_executor_calls.append(project_root)
        return expected_tool_executors

    orchestrator_calls: dict[str, object] = {}

    class FakeOrchestrator:
        def __init__(self, project_root: Path, novel_id: str, tool_executors):
            orchestrator_calls["project_root"] = project_root
            orchestrator_calls["novel_id"] = novel_id
            orchestrator_calls["tool_executors"] = tool_executors

        def run_cli(self, instruction: str, *, quiet: bool = False, max_turns: int = 20) -> int:
            orchestrator_calls["instruction"] = instruction
            orchestrator_calls["quiet"] = quiet
            orchestrator_calls["max_turns"] = max_turns
            return 0

    monkeypatch.setattr(tool_runtime_module, "build_tool_executors", fake_build_tool_executors)
    monkeypatch.setattr(orchestrator_module, "OpenWriteOrchestrator", FakeOrchestrator)

    result = cli_module._cmd_agent(_fake_args("查看项目状态", max_turns=7, quiet=True))

    assert result == 0
    assert tool_executor_calls == [tmp_path]
    assert orchestrator_calls["project_root"] == tmp_path
    assert orchestrator_calls["novel_id"] == "demo"
    assert orchestrator_calls["tool_executors"] is expected_tool_executors
    assert orchestrator_calls["instruction"] == "查看项目状态"
    assert orchestrator_calls["quiet"] is True
    assert orchestrator_calls["max_turns"] == 7


def test_cmd_agent_does_not_require_llm_client_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "novel_config.yaml").write_text("novel_id: demo\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))
    monkeypatch.setattr(tool_runtime_module, "build_tool_executors", lambda project_root: {})

    import tools.llm as llm_module

    def forbidden(*args, **kwargs):
        raise AssertionError("LLM client setup should not be touched")

    monkeypatch.setattr(llm_module, "LLMClient", forbidden)
    monkeypatch.setattr(llm_module.LLMConfig, "from_env", classmethod(lambda cls: forbidden()))

    class FakeOrchestrator:
        def __init__(self, project_root: Path, novel_id: str, tool_executors):
            self.project_root = project_root
            self.novel_id = novel_id
            self.tool_executors = tool_executors

        def run_cli(self, instruction: str, *, quiet: bool = False, max_turns: int = 20) -> int:
            return 0

    monkeypatch.setattr(orchestrator_module, "OpenWriteOrchestrator", FakeOrchestrator)

    assert cli_module._cmd_agent(_fake_args("基础设定准备好了")) == 0


def test_cmd_agent_requires_project_config_before_initializing_orchestrator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))
    called = {"value": False}

    def forbidden(*args, **kwargs):
        called["value"] = True
        return SimpleNamespace(run_cli=lambda **_: 0)

    monkeypatch.setattr(orchestrator_module, "OpenWriteOrchestrator", forbidden)

    assert cli_module._cmd_agent(_fake_args("查看项目状态")) == 1
    assert called["value"] is False


def test_cmd_agent_passes_instruction_and_returns_orchestrator_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "novel_config.yaml").write_text("novel_id: demo\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "Path", SimpleNamespace(cwd=lambda: tmp_path))
    monkeypatch.setattr(
        tool_runtime_module,
        "build_tool_executors",
        lambda project_root: {"get_status": lambda args: {"ok": True}},
    )

    run_cli_calls: dict[str, object] = {}

    class FakeOrchestrator:
        def __init__(self, project_root: Path, novel_id: str, tool_executors):
            self.project_root = project_root
            self.novel_id = novel_id
            self.tool_executors = tool_executors

        def run_cli(self, instruction: str, *, quiet: bool = False, max_turns: int = 20) -> int:
            run_cli_calls["instruction"] = instruction
            run_cli_calls["quiet"] = quiet
            run_cli_calls["max_turns"] = max_turns
            return 17

    monkeypatch.setattr(orchestrator_module, "OpenWriteOrchestrator", FakeOrchestrator)

    result = cli_module._cmd_agent(_fake_args("写 ch_001", max_turns=9, quiet=False))

    assert result == 17
    assert run_cli_calls == {
        "instruction": "写 ch_001",
        "quiet": False,
        "max_turns": 9,
    }


def test_run_cli_status_instruction_is_read_only(tmp_path: Path):
    state_store = BookStateStore(tmp_path, "demo")
    assert state_store.path.exists() is False

    orchestrator = orchestrator_module.OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=StoryPlanningStore(tmp_path, "demo"),
        tool_executors={},
    )

    assert state_store.path.exists() is False
    result = orchestrator.run_cli("查看项目状态", quiet=True)

    assert result == 0
    assert state_store.path.exists() is False


def test_run_cli_reuses_a_single_preflight_for_chapter_delegation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state_store = BookStateStore(tmp_path, "demo")
    state = state_store.load_or_create()
    state.stage = BookStage.CHAPTER_PREFLIGHT
    state_store.save(state)

    orchestrator = orchestrator_module.OpenWriteOrchestrator.for_testing(
        tmp_path,
        "demo",
        state_store=state_store,
        planning_store=StoryPlanningStore(tmp_path, "demo"),
        tool_executors={
            "write_chapter": lambda args: {"ok": True, "draft_path": "drafts/ch_001.md"}
        },
    )

    preflight_calls = {"count": 0}

    def fake_run_preflight(chapter_id: str):
        preflight_calls["count"] += 1
        return {
            "ok": True,
            "chapter_id": chapter_id,
            "reason": "",
            "missing_items": [],
            "packet": {
                "chapter_id": chapter_id,
                "prompt_sections": {},
                "story_background": "",
                "foundation": "",
                "previous_chapter_content": "",
                "style_documents": {},
                "character_documents": [],
                "concept_documents": {},
            },
        }

    monkeypatch.setattr(orchestrator, "run_preflight", fake_run_preflight)

    delegate_calls = {}
    real_delegate = orchestrator.delegate_writing

    def spying_delegate(chapter_id: str, preflight_result=None):
        delegate_calls["preflight_result"] = preflight_result
        return real_delegate(chapter_id, preflight_result=preflight_result)

    monkeypatch.setattr(orchestrator, "delegate_writing", spying_delegate)

    result = orchestrator.run_cli("写 ch_001", quiet=True)

    assert result == 0
    assert preflight_calls["count"] == 1
    assert delegate_calls["preflight_result"]["chapter_id"] == "ch_001"


def test_exec_write_chapter_uses_asyncio_run_without_missing_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "novel_config.yaml").write_text("novel_id: demo\n", encoding="utf-8")
    expected_draft_path = (
        tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_001" / "ch_001.md"
    )

    class FakeContext:
        target_words = 1200
        chapter_goals = ["推进剧情"]
        current_state = "现状"
        pending_hooks = "伏笔"

    class FakeBuilder:
        def __init__(self, project_root: Path, novel_id: str, reference_style: str | None = None):
            self.project_root = project_root
            self.novel_id = novel_id

        def build_generation_context(self, chapter_id: str):
            return FakeContext()

    class FakeWriter:
        def __init__(self, agent_ctx):
            self.agent_ctx = agent_ctx

        async def write_chapter(self, context, chapter_number: int, temperature: float = 0.7):
            return SimpleNamespace(title="测试标题", content="测试内容", word_count=321)

    monkeypatch.setattr(context_builder_module, "ContextBuilder", FakeBuilder)
    monkeypatch.setattr(agent_module, "WriterAgent", FakeWriter)
    monkeypatch.setattr(
        agent_module,
        "AgentContext",
        lambda client, model, project_root: SimpleNamespace(
            client=client, model=model, project_root=project_root
        ),
    )
    monkeypatch.setattr(llm_module.LLMConfig, "from_env", classmethod(lambda cls: SimpleNamespace(model="fake-model")))
    monkeypatch.setattr(llm_module, "LLMClient", lambda config: object())
    monkeypatch.setattr(
        cli_module,
        "_save_chapter",
        lambda *args, **kwargs: expected_draft_path,
    )

    result = cli_module._exec_write_chapter(tmp_path, {"chapter_id": "ch_001"})

    assert result == {
        "ok": True,
        "chapter_id": "ch_001",
        "title": "测试标题",
        "word_count": 321,
        "draft_path": str(expected_draft_path),
    }
