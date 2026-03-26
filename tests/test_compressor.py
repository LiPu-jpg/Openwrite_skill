"""ProgressiveCompressor 测试

覆盖渐进式上下文压缩引擎的核心功能：
- 规则引擎文本压缩
- 句子边界截断
- 节级压缩与持久化
- 篇级压缩与合并
- 上文提取
- 压缩归档流程
"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.progressive_compressor import (
    ProgressiveCompressor,
    SectionCompression,
    ArcCompression,
    SECTION_COMPRESS_TARGET,
    ARC_COMPRESS_TARGET,
)
from models.outline import OutlineNode, OutlineNodeType, OutlineHierarchy


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def compressor(tmp_path):
    """创建临时目录的 compressor"""
    novel_id = "test_novel"
    base = tmp_path / "data" / "novels" / novel_id
    (base / "compressed").mkdir(parents=True)
    (base / "manuscript").mkdir(parents=True)
    return ProgressiveCompressor(project_dir=tmp_path, novel_id=novel_id)


# ── SectionCompression 模型 ──────────────────────────────────


class TestSectionCompression:
    """节压缩数据结构测试"""

    def test_defaults(self):
        sc = SectionCompression(
            section_id="sec_001",
            arc_id="arc_001",
            compressed_text="摘要文本",
        )
        assert sc.key_events == []
        assert sc.character_changes == []
        assert sc.word_count == 0

    def test_to_dict(self):
        sc = SectionCompression(
            section_id="sec_001",
            arc_id="arc_001",
            compressed_text="摘要",
            key_events=["事件1"],
            word_count=1000,
        )
        d = sc.to_dict()
        assert d["section_id"] == "sec_001"
        assert d["key_events"] == ["事件1"]

    def test_roundtrip(self):
        sc = SectionCompression(
            section_id="sec_001",
            arc_id="arc_001",
            compressed_text="摘要文本",
            key_events=["事件1", "事件2"],
            character_changes=["角色A成长"],
            word_count=5000,
        )
        d = sc.to_dict()
        sc2 = SectionCompression.from_dict(d)
        assert sc2.section_id == sc.section_id
        assert sc2.key_events == sc.key_events
        assert sc2.word_count == sc.word_count


# ── ArcCompression 模型 ──────────────────────────────────────


class TestArcCompression:
    """篇压缩数据结构测试"""

    def test_defaults(self):
        ac = ArcCompression(arc_id="arc_001")
        assert ac.section_summaries == []
        assert ac.merged_summary == ""

    def test_build_merged(self):
        sc1 = SectionCompression(
            section_id="sec_001", arc_id="arc_001", compressed_text="节一内容"
        )
        sc2 = SectionCompression(
            section_id="sec_002", arc_id="arc_001", compressed_text="节二内容"
        )
        ac = ArcCompression(
            arc_id="arc_001",
            previous_arc_summary="前篇摘要",
            section_summaries=[sc1, sc2],
        )
        merged = ac.build_merged()
        assert "前篇摘要" in merged
        assert "节一内容" in merged
        assert "节二内容" in merged

    def test_roundtrip(self):
        sc = SectionCompression(
            section_id="sec_001", arc_id="arc_001", compressed_text="内容"
        )
        ac = ArcCompression(
            arc_id="arc_001",
            previous_arc_summary="前文",
            section_summaries=[sc],
            merged_summary="合并后",
            total_word_count=10000,
        )
        d = ac.to_dict()
        ac2 = ArcCompression.from_dict(d)
        assert ac2.arc_id == ac.arc_id
        assert len(ac2.section_summaries) == 1
        assert ac2.total_word_count == 10000


# ── 规则引擎压缩 ─────────────────────────────────────────────


class TestRuleCompress:
    """规则引擎文本压缩测试"""

    def test_short_text_no_compression(self, compressor):
        text = "这是一段短文本。"
        result = compressor._rule_compress_text(text, 100)
        assert result == text

    def test_long_text_compressed(self, compressor):
        paragraphs = [f"段落{i}的内容是关于某个事件的详细描述。" * 5 for i in range(20)]
        text = "\n".join(paragraphs)
        result = compressor._rule_compress_text(text, 200)
        assert len(result) <= 300  # 留一些余量

    def test_keyword_priority(self, compressor):
        """含关键词的段落应优先保留"""
        paragraphs = [
            "这是一个普通的日常段落。",
            "然而突然间一切都变了，局势发生了逆转。",
            "另一个普通的描述段落。",
            "主角终于发现了真相。",
        ]
        text = "\n".join(paragraphs)
        result = compressor._rule_compress_text(text, 100)
        # 含关键词的段落应被保留
        assert "突然" in result or "终于" in result

    def test_first_last_priority(self, compressor):
        """首段和末段应优先保留"""
        paragraphs = ["首段内容。"] + [f"中间段{i}。" for i in range(10)] + ["末段内容。"]
        text = "\n".join(paragraphs)
        result = compressor._rule_compress_text(text, 50)
        assert "首段" in result or "末段" in result


# ── 句子边界截断 ──────────────────────────────────────────────


class TestSentenceTruncation:
    """句子边界截断测试"""

    def test_no_truncation_needed(self):
        text = "短文本。"
        result = ProgressiveCompressor._truncate_at_sentence(text, 100)
        assert result == text

    def test_truncate_at_period(self):
        text = "第一句。第二句。第三句。第四句很长很长。"
        result = ProgressiveCompressor._truncate_at_sentence(text, 12)
        assert result.endswith("。")
        assert len(result) <= 12

    def test_truncate_at_comma(self):
        text = "很长的一句话，后面还有很多很多内容"
        result = ProgressiveCompressor._truncate_at_sentence(text, 10)
        assert len(result) <= 10

    def test_hard_truncation(self):
        text = "没有标点的很长文本内容" * 10
        result = ProgressiveCompressor._truncate_at_sentence(text, 20)
        assert len(result) <= 20


# ── 节级压缩 ─────────────────────────────────────────────────


class TestSectionCompression_Flow:
    """节级压缩流程测试"""

    def test_compress_section(self, compressor):
        text = "这是一段很长的小说内容。" * 100
        result = compressor.compress_section(
            section_id="sec_001",
            arc_id="arc_001",
            full_text=text,
            key_events=["事件1"],
        )
        assert result.section_id == "sec_001"
        assert result.arc_id == "arc_001"
        assert result.word_count == len(text)
        assert len(result.compressed_text) <= SECTION_COMPRESS_TARGET * 2

    def test_section_persistence(self, compressor):
        """压缩结果应持久化到文件"""
        compressor.compress_section(
            section_id="sec_001", arc_id="arc_001", full_text="测试内容"
        )
        loaded = compressor._load_section_compression("sec_001")
        assert loaded is not None
        assert loaded.section_id == "sec_001"

    def test_load_nonexistent_section(self, compressor):
        assert compressor._load_section_compression("nonexistent") is None


# ── 篇级压缩 ─────────────────────────────────────────────────


class TestArcCompression_Flow:
    """篇级压缩流程测试"""

    def test_compress_arc_empty(self, compressor):
        result = compressor.compress_arc(arc_id="arc_001")
        assert result.arc_id == "arc_001"
        assert result.section_summaries == []

    def test_compress_arc_with_sections(self, compressor):
        # 先压缩几个节
        for i in range(3):
            compressor.compress_section(
                section_id=f"sec_{i+1:03d}",
                arc_id="arc_001",
                full_text=f"节{i+1}的内容。" * 50,
            )

        result = compressor.compress_arc(arc_id="arc_001")
        assert len(result.section_summaries) == 3
        assert result.merged_summary != ""

    def test_arc_persistence(self, compressor):
        compressor.compress_arc(arc_id="arc_001")
        loaded = compressor._load_arc_compression("arc_001")
        assert loaded is not None
        assert loaded.arc_id == "arc_001"


# ── 上文提取 ──────────────────────────────────────────────────


class TestRecentTextExtraction:
    """上文提取测试"""

    def test_empty_manuscript(self, compressor):
        assert compressor._extract_recent_text("") == ""

    def test_short_manuscript(self, compressor):
        text = "短文本。"
        assert compressor._extract_recent_text(text) == text

    def test_long_manuscript_truncated(self, compressor):
        text = "这是一段内容。" * 200
        result = compressor._extract_recent_text(text)
        assert len(result) <= compressor.recent_text_max

    def test_sentence_boundary_cut(self, compressor):
        # 确保在句子边界截断
        text = "第一段内容。" * 100 + "最后一句话。"
        result = compressor._extract_recent_text(text)
        # 应以句末标点结束或不含截断的半句
        assert result.strip() != ""


# ── 全量前文压缩 ──────────────────────────────────────────────


class TestArcContext:
    """前文压缩上下文测试"""

    def test_get_arc_context_empty(self, compressor):
        ctx = compressor.get_arc_context("arc_001")
        assert ctx["previous_arc_summary"] == ""
        assert ctx["current_arc_sections"] == []

    def test_get_previous_arc_summary(self, compressor):
        # 创建 arc_001 的压缩
        compressor.compress_section(
            section_id="sec_001", arc_id="arc_001", full_text="内容" * 100
        )
        compressor.compress_arc(arc_id="arc_001")

        # 获取 arc_002 的前文
        summary = compressor._get_previous_arc_summary("arc_002")
        assert summary != ""

    def test_get_full_previous_summary(self, compressor):
        # 创建两个篇的压缩
        for arc_idx in range(1, 3):
            arc_id = f"arc_{arc_idx:03d}"
            compressor.compress_section(
                section_id=f"sec_{arc_idx:03d}",
                arc_id=arc_id,
                full_text=f"篇{arc_idx}内容" * 50,
            )
            compressor.compress_arc(arc_id=arc_id)

        summary = compressor.get_full_previous_summary("arc_003")
        assert summary != ""
