"""端到端集成测试

覆盖完整的写作流程：
- init_project → 创建项目 → 验证目录结构
- 大纲解析 + 上下文构建 → 验证输出
- 压缩流程 → 验证持久化
- 流程调度器 → 完整 pipeline
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.init_project import init_project
from tools.context_builder import ContextBuilder
from tools.progressive_compressor import ProgressiveCompressor
from tools.workflow_scheduler import WorkflowScheduler, STAGE_NAMES
from tools.outline_parser import OutlineMdParser
from tools.outline_serializer import OutlineMdSerializer
from tools.foreshadowing_manager import ForeshadowingDAGManager
from tools.file_ops import FileOps
from tools.world_query import list_entities, get_entity, get_relations_graph
from tools.chapter_assembler import ChapterAssemblerV2

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ── init_project 集成 ────────────────────────────────────────


class TestInitProject:
    """项目初始化集成测试"""

    def test_init_creates_directories(self, tmp_path):
        init_project(tmp_path, "my_novel", "我的小说")
        base = tmp_path / "data" / "novels" / "my_novel"
        assert (base / "src").is_dir()
        assert (base / "src" / "characters").is_dir()
        assert (base / "src" / "world").is_dir()
        assert (base / "src" / "world" / "entities").is_dir()
        assert (base / "data" / "characters" / "cards").is_dir()
        assert (base / "data" / "foreshadowing").is_dir()
        assert (base / "data" / "style").is_dir()
        assert (base / "data" / "manuscript" / "arc_001").is_dir()
        assert (base / "data" / "compressed").is_dir()
        assert (base / "data" / "workflows").is_dir()

    def test_init_creates_config(self, tmp_path):
        init_project(tmp_path, "my_novel")
        config = tmp_path / "novel_config.yaml"
        assert config.exists()
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
        assert data["novel_id"] == "my_novel"

    def test_init_creates_outline(self, tmp_path):
        init_project(tmp_path, "my_novel")
        outline = tmp_path / "data" / "novels" / "my_novel" / "data" / "hierarchy.yaml"
        outline_src = tmp_path / "data" / "novels" / "my_novel" / "src" / "outline.md"
        assert outline.exists()
        data = yaml.safe_load(outline.read_text(encoding="utf-8"))
        assert "story_info" in data
        assert "chapters" in data
        assert "故事简介" in outline_src.read_text(encoding="utf-8")

    def test_init_creates_world_files(self, tmp_path):
        init_project(tmp_path, "my_novel")
        world_dir = tmp_path / "data" / "novels" / "my_novel" / "src" / "world"
        assert (world_dir / "rules.md").exists()
        assert (world_dir / "timeline.md").exists()
        assert (world_dir / "terminology.md").exists()

    def test_init_creates_dag(self, tmp_path):
        init_project(tmp_path, "my_novel")
        dag = tmp_path / "data" / "novels" / "my_novel" / "data" / "foreshadowing" / "dag.yaml"
        assert dag.exists()

    def test_init_idempotent(self, tmp_path):
        """重复初始化不覆盖已有文件"""
        init_project(tmp_path, "my_novel")
        config = tmp_path / "novel_config.yaml"
        config.write_text("custom: true", encoding="utf-8")
        init_project(tmp_path, "my_novel")
        assert "custom" in config.read_text(encoding="utf-8")


# ── 大纲解析 + 上下文构建 ────────────────────────────────────


class TestOutlineToContext:
    """Markdown 大纲 → 解析 → 上下文构建"""

    def test_parse_and_build_context(self, tmp_path):
        novel_id = "test"
        # 初始化项目
        init_project(tmp_path, novel_id)

        # 放入大纲 YAML
        outline_data = {
            "story_info": {"title": "测试小说", "theme": "冒险"},
            "chapters": [
                {"id": "ch_001", "title": "第一章", "summary": "开篇", "goals": ["介绍主角"]},
                {"id": "ch_002", "title": "第二章", "summary": "发展"},
                {"id": "ch_003", "title": "第三章", "summary": "转折"},
            ],
        }
        outline_path = tmp_path / "data" / "novels" / novel_id / "data" / "hierarchy.yaml"
        outline_path.write_text(yaml.dump(outline_data, allow_unicode=True), encoding="utf-8")

        # 构建上下文
        builder = ContextBuilder(project_root=tmp_path, novel_id=novel_id)
        context = builder.build_generation_context("ch_002")
        assert context.novel_id == novel_id
        assert context.chapter_id == "ch_002"

    def test_outline_roundtrip_then_context(self, tmp_path):
        """Markdown → 解析 → 序列化 → 再解析"""
        md = (FIXTURES_DIR / "full_outline.md").read_text(encoding="utf-8")
        parser = OutlineMdParser()
        serializer = OutlineMdSerializer()

        h1 = parser.parse(md, "test")
        md2 = serializer.serialize(h1)
        h2 = parser.parse(md2, "test")

        assert h1.master.title == h2.master.title
        assert len(h1.arcs) == len(h2.arcs)
        assert len(h1.chapters) == len(h2.chapters)

    def test_chapter_assembler_auto_refreshes_stale_outline(self, tmp_path):
        novel_id = "test"
        init_project(tmp_path, novel_id)

        src_outline = tmp_path / "data" / "novels" / novel_id / "src" / "outline.md"
        src_outline.write_text(
            "# 测试小说\n\n## 第一篇\n\n### 第一节\n\n#### 旧标题\n\n> 内容焦点: 旧摘要\n",
            encoding="utf-8",
        )
        from tools.outline_sync import sync_outline_to_hierarchy

        sync_outline_to_hierarchy(src_outline.parent, src_outline.parent.parent / "data")

        hierarchy_path = tmp_path / "data" / "novels" / novel_id / "data" / "hierarchy.yaml"
        src_outline.write_text(
            "# 测试小说\n\n## 第一篇\n\n### 第一节\n\n#### 新标题\n\n> 内容焦点: 新摘要\n",
            encoding="utf-8",
        )
        stale_time = src_outline.stat().st_mtime - 10
        os.utime(hierarchy_path, (stale_time, stale_time))

        assembler = ChapterAssemblerV2(project_root=tmp_path, novel_id=novel_id)
        packet = assembler.assemble("ch_001")

        assert "新标题（ch_001" in packet.to_markdown()


# ── 压缩归档流程 ─────────────────────────────────────────────


class TestCompressionPipeline:
    """写作 → 压缩 → 归档"""

    def test_section_then_arc_compression(self, tmp_path):
        novel_id = "test"
        init_project(tmp_path, novel_id)

        compressor = ProgressiveCompressor(project_dir=tmp_path, novel_id=novel_id)

        # 压缩三个节
        for i in range(1, 4):
            compressor.compress_section(
                section_id=f"sec_{i:03d}",
                arc_id="arc_001",
                full_text=f"第{i}节的详细内容。" * 80,
            )

        # 压缩篇
        arc_result = compressor.compress_arc(arc_id="arc_001")
        assert len(arc_result.section_summaries) == 3
        assert arc_result.merged_summary != ""

        # 验证持久化
        loaded = compressor._load_arc_compression("arc_001")
        assert loaded is not None
        assert loaded.arc_id == "arc_001"


# ── 完整写作 pipeline ────────────────────────────────────────


class TestFullPipeline:
    """完整写作流程（不含 LLM）"""

    def test_complete_workflow(self, tmp_path):
        novel_id = "test"
        init_project(tmp_path, novel_id)

        # 1. 创建工作流
        scheduler = WorkflowScheduler(project_root=tmp_path, novel_id=novel_id)
        state = scheduler.create_workflow("ch_001")
        assert state.current_stage == "context_assembly"

        # 2. 上下文组装
        builder = ContextBuilder(project_root=tmp_path, novel_id=novel_id)
        context = builder.build_generation_context("ch_001")
        state = scheduler.complete_stage(state, "context_assembly", message="done")
        assert state.current_stage == "writing"

        # 3. 模拟写作完成
        ms_path = (
            tmp_path
            / "data"
            / "novels"
            / novel_id
            / "data"
            / "manuscript"
            / "arc_001"
            / "ch_001.md"
        )
        ms_path.write_text("模拟的章节内容" * 100, encoding="utf-8")
        state = scheduler.complete_stage(
            state, "writing", data={"draft_path": str(ms_path)}
        )
        assert state.current_stage == "review"

        # 4. 审查完成
        state = scheduler.complete_stage(
            state, "review", data={"passed": True, "errors": [], "warnings": []}
        )
        assert state.current_stage == "user_confirm"

        # 5. 用户确认
        state = scheduler.complete_stage(
            state, "user_confirm", data={"approved": True}
        )
        assert state.current_stage == "styling"

        # 6. 风格润色完成
        state = scheduler.complete_stage(state, "styling")
        assert state.current_stage == "compression"

        # 7. 压缩归档
        compressor = ProgressiveCompressor(project_dir=tmp_path, novel_id=novel_id)
        compressor.compress_section(
            section_id="sec_001",
            arc_id="arc_001",
            full_text=ms_path.read_text(encoding="utf-8"),
        )
        state = scheduler.complete_stage(state, "compression", message="已归档")

        assert scheduler.is_complete(state)

    def test_workflow_with_failure_and_retry(self, tmp_path):
        """流程失败后恢复"""
        novel_id = "test"
        init_project(tmp_path, novel_id)

        scheduler = WorkflowScheduler(project_root=tmp_path, novel_id=novel_id)
        state = scheduler.create_workflow("ch_001")

        # 上下文组装失败
        state = scheduler.fail_stage(state, "context_assembly", "文件缺失")
        assert state.error != ""

        # 重试成功
        state = scheduler.complete_stage(state, "context_assembly", message="重试成功")
        assert state.current_stage == "writing"


# ── FileOps 集成 ─────────────────────────────────────────────


class TestFileOpsIntegration:
    """FileOps 沙箱化文件操作"""

    def test_read_write_cycle(self, tmp_path):
        novel_id = "test"
        init_project(tmp_path, novel_id)

        ops = FileOps(project_root=tmp_path, novel_id=novel_id)

        # 写入
        result = ops.write_file("manuscript/ch_001.md", "测试内容")
        assert result["success"] is True

        # 读取
        result = ops.read_file("manuscript/ch_001.md")
        assert result["success"] is True
        assert result["result"] == "测试内容"

    def test_path_traversal_blocked(self, tmp_path):
        novel_id = "test"
        init_project(tmp_path, novel_id)

        ops = FileOps(project_root=tmp_path, novel_id=novel_id)
        with pytest.raises(ValueError, match="traversal"):
            ops._resolve_path("../../etc/passwd")


# ── 世界观查询集成 ───────────────────────────────────────────


class TestWorldQueryIntegration:
    """世界观查询工具集成测试"""

    def test_entity_crud(self, tmp_path):
        novel_id = "test"
        init_project(tmp_path, novel_id)

        entities_dir = tmp_path / "data" / "novels" / novel_id / "src" / "world" / "entities"
        (entities_dir / "place_a.md").write_text(
            "# 灵山\n\n> 地点 | 山脉 | active\n\n修仙圣地。\n\n## 关联\n\n- 天山派 — 驻地\n",
            encoding="utf-8",
        )

        # 列出
        result = list_entities(novel_id, project_root=tmp_path)
        assert len(result) == 1
        assert result[0]["name"] == "灵山"

        # 查看详情
        entity = get_entity(novel_id, "place_a", project_root=tmp_path)
        assert entity["relations"][0]["target"] == "天山派"

        # 关系图
        graph = get_relations_graph(novel_id, project_root=tmp_path)
        assert len(graph["relations"]) == 1
