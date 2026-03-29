"""MultiAgentDirector 与 ChapterAssemblerV2 回归测试。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.agent.director import MultiAgentDirector
from tools.agent.reviewer import ReviewResult
from tools.agent.writer import WritingResult
from tools.chapter_assembler import ChapterAssemblerV2, ChapterAssemblyPacket
from tools.init_project import init_project
from tools.truth_manager import TruthFilesManager


def _bootstrap_novel(tmp_path: Path, novel_id: str = "demo") -> Path:
    init_project(tmp_path, novel_id)
    novel_root = tmp_path / "data" / "novels" / novel_id

    hierarchy = {
        "story_info": {"title": "测试小说", "theme": "测试主题"},
        "arcs": [
            {
                "id": "arc_001",
                "title": "第一篇",
                "description": "开篇",
                "chapters": ["ch_001"],
            }
        ],
        "sections": [
            {
                "id": "sec_001",
                "title": "第一节",
                "arc_id": "arc_001",
                "chapters": ["ch_001"],
            }
        ],
        "chapters": [
            {
                "id": "ch_001",
                "title": "第一章",
                "summary": "开篇",
                "goals": ["建立主角"],
                "involved_characters": ["chen_ming"],
                "involved_settings": ["company"],
            }
        ],
    }
    (novel_root / "data" / "hierarchy.yaml").write_text(
        yaml.safe_dump(hierarchy, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    story_dir = novel_root / "src" / "story"
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "background.md").write_text("# 背景\n\n测试背景。", encoding="utf-8")
    (story_dir / "foundation.md").write_text("# 设定\n\n测试设定。", encoding="utf-8")

    (novel_root / "src" / "characters" / "chen_ming.md").write_text(
        "# 陈明\n\n## 背景\n\n角色背景。\n\n## 外貌\n\n普通。\n\n## 性格\n\n- 冷静\n",
        encoding="utf-8",
    )
    (novel_root / "src" / "world" / "rules.md").write_text(
        "# 世界规则\n\n## 力量体系\n- 静态规则\n",
        encoding="utf-8",
    )
    (novel_root / "src" / "world" / "terminology.md").write_text(
        "# 术语表\n\n| 术语 | 定义 | 分类 |\n|------|------|------|\n| 公司 | 主舞台 | location |\n",
        encoding="utf-8",
    )
    entities_dir = novel_root / "src" / "world" / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)
    (entities_dir / "company.md").write_text(
        "# 公司\n\n> location | building | active\n\n主舞台。\n",
        encoding="utf-8",
    )

    truth_manager = TruthFilesManager(tmp_path, novel_id)
    truth = truth_manager.load_truth_files()
    truth.current_state = "这是运行态 current_state。"
    truth.particle_ledger = "这是运行态 ledger。"
    truth.character_matrix = "这是运行态 relationships。"
    truth_manager.save_truth_files(truth)
    return novel_root


def test_assemble_packet_includes_runtime_truth_files(tmp_path: Path):
    _bootstrap_novel(tmp_path)

    assembler = ChapterAssemblerV2(project_root=tmp_path, novel_id="demo")
    packet = assembler.assemble("ch_001")

    assert packet.current_state == "这是运行态 current_state。"
    assert packet.ledger == "这是运行态 ledger。"
    assert packet.relationships == "这是运行态 relationships。"

    markdown = packet.to_markdown()
    assert "## 运行态真相文件" in markdown
    assert "这是运行态 current_state。" in markdown
    assert "这是运行态 ledger。" in markdown
    assert "这是运行态 relationships。" in markdown


def test_director_run_uses_runtime_truth_files_for_writer_and_reviewer(tmp_path: Path):
    captured: dict[str, dict] = {}
    ctx = SimpleNamespace(project_root=str(tmp_path))
    director = MultiAgentDirector(ctx, novel_id="demo")
    packet = ChapterAssemblyPacket(
        novel_id="demo",
        chapter_id="ch_001",
        character_documents={"陈明": "角色文档"},
        style_documents={"style": "风格"},
        concept_documents={"world.rules": "静态规则"},
        previous_chapter_content="上一章内容",
        current_state="这是运行态 current_state。",
        ledger="这是运行态 ledger。",
        relationships="这是运行态 relationships。",
    )

    class FakeWriter:
        async def write_chapter(
            self,
            context,
            chapter_number: int,
            temperature: float = 0.7,
            target_words: int = 4000,
        ):
            captured["writer"] = context
            return WritingResult(
                chapter_number=chapter_number,
                title="测试标题",
                content="测试正文",
                word_count=3210,
                state_updates={},
            )

    class FakeReviewer:
        async def review(self, content: str, context: dict):
            captured["reviewer"] = context
            return ReviewResult(passed=True, issues=[], summary="ok", score=95)

    director.writer = FakeWriter()
    director.reviewer = FakeReviewer()
    director.assemble_packet = lambda chapter_id: packet

    result = asyncio.run(director.run("ch_001"))

    assert result.packet is packet
    assert captured["writer"]["current_state"] == "这是运行态 current_state。"
    assert captured["writer"]["ledger"] == "这是运行态 ledger。"
    assert captured["writer"]["relationships"] == "这是运行态 relationships。"
    assert captured["writer"]["current_state"] != "静态规则"
    assert captured["reviewer"]["current_state"] == "这是运行态 current_state。"


def test_apply_state_updates_accepts_canonical_truth_keys(tmp_path: Path):
    init_project(tmp_path, "demo")
    ctx = SimpleNamespace(project_root=str(tmp_path))
    director = MultiAgentDirector(ctx, novel_id="demo")

    applied = director._apply_state_updates(
        {
            "current_state": "状态更新",
            "ledger": "账本更新",
            "relationships": "关系更新",
        }
    )

    truth = director.truth_manager.load_truth_files()
    assert applied == {
        "current_state": "状态更新",
        "ledger": "账本更新",
        "relationships": "关系更新",
    }
    assert truth.current_state == "状态更新"
    assert truth.ledger == "账本更新"
    assert truth.relationships == "关系更新"


def test_assembler_prefers_src_outline_over_runtime_hierarchy(tmp_path: Path):
    novel_root = _bootstrap_novel(tmp_path)
    (novel_root / "src" / "outline.md").write_text(
        "# 源大纲\n\n## 第一篇\n\n### 第一节\n\n#### 源标题\n\n> 内容焦点: 源摘要\n",
        encoding="utf-8",
    )
    (novel_root / "data" / "hierarchy.yaml").write_text(
        yaml.safe_dump(
            {
                "story_info": {"title": "缓存大纲"},
                "chapters": [{"id": "ch_001", "title": "缓存标题", "summary": "缓存摘要"}],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    assembler = ChapterAssemblerV2(project_root=tmp_path, novel_id="demo")
    hierarchy = assembler._load_hierarchy()

    assert hierarchy.master.title == "源大纲"
    assert hierarchy.get_node("ch_001").title == "源标题"
    assert hierarchy.get_node("ch_001").content_focus == "源摘要"
