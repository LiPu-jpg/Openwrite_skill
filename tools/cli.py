"""OpenWrite CLI - 命令行接口

用法:
    openwrite init <novel_id>     # 初始化项目
    openwrite sync                # 同步 src -> data
    openwrite write <chapter>     # 写章节
    openwrite review <chapter>    # 审查章节
    openwrite context <chapter>   # 构建上下文
    openwrite style extract       # 提取风格
    openwrite status             # 查看状态
    openwrite --help            # 显示帮助
"""

import asyncio
import sys
import argparse
import logging
import os
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime
import re
import yaml

from tools.context_schema import normalize_context_payload, normalize_truth_file_key
from tools.shared_documents import normalize_character_document
from tools.source_sync import (
    collect_sync_status as _shared_collect_sync_status,
    run_sync as _shared_run_sync,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="openwrite",
        description="OpenWrite 长篇小说创作引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="OpenWrite 5.4.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    _add_init_command(subparsers)
    _add_goethe_command(subparsers)
    _add_dante_command(subparsers)
    _add_sync_command(subparsers)
    _add_write_command(subparsers)
    _add_multi_write_command(subparsers)
    _add_review_command(subparsers)
    _add_context_command(subparsers)
    _add_assemble_command(subparsers)
    _add_style_command(subparsers)
    _add_radar_command(subparsers)
    _add_status_command(subparsers)
    _add_doctor_command(subparsers)
    _add_agent_command(subparsers)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        return _dispatch(args)
    except KeyboardInterrupt:
        logger.info("操作已取消")
        return 130
    except Exception as e:
        logger.error(f"错误: {e}")
        return 1


def _dispatch(args) -> int:
    """分发命令"""
    if args.command == "init":
        return _cmd_init(args)
    elif args.command == "sync":
        return _cmd_sync(args)
    elif args.command == "write":
        return _cmd_write(args)
    elif args.command == "multi-write":
        return _cmd_multi_write(args)
    elif args.command == "review":
        return _cmd_review(args)
    elif args.command == "context":
        return _cmd_context(args)
    elif args.command == "assemble":
        return _cmd_assemble(args)
    elif args.command == "style":
        return _cmd_style(args)
    elif args.command == "radar":
        return _cmd_radar(args)
    elif args.command == "goethe":
        return _cmd_goethe(args)
    elif args.command == "dante":
        return _cmd_dante(args)
    elif args.command == "status":
        return _cmd_status(args)
    elif args.command == "doctor":
        return _cmd_doctor(args)
    elif args.command == "agent":
        return _cmd_agent(args)
    else:
        logger.error(f"未知命令: {args.command}")
        return 1


def _add_init_command(subparsers):
    """init 命令"""
    p = subparsers.add_parser("init", help="初始化新项目")
    p.add_argument("novel_id", help="小说 ID")
    p.add_argument("--template", "-t", default="default", help="模板类型")


def _add_goethe_command(subparsers):
    """goethe 命令 - 交互式引导"""
    p = subparsers.add_parser("goethe", help="交互式引导（推荐新手使用）")
    p.add_argument("--novel-id", help="小说 ID（可选）")


def _add_dante_command(subparsers):
    """dante 命令 - 过渡性主入口"""
    p = subparsers.add_parser(
        "dante",
        help="过渡性主入口：复用确定性编排器",
        description="过渡性主入口：复用现有确定性编排器，作为主入口迁移层。",
    )
    p.add_argument("instruction", nargs="?", default="查看项目状态", help="自然语言指令")
    p.add_argument("--max-turns", type=int, default=20, help="最大循环次数")
    p.add_argument("--quiet", action="store_true", help="静默模式")


def _add_sync_command(subparsers):
    """sync 命令"""
    p = subparsers.add_parser("sync", help="同步 src 到 data（大纲/角色）")
    p.add_argument("--novel-id", help="小说 ID（默认从 novel_config.yaml 读取）")
    p.add_argument("--check", action="store_true", help="仅检查是否存在未同步变更")
    p.add_argument("--json", action="store_true", help="输出 JSON 结果（便于脚本/Agent 解析）")


def _add_write_command(subparsers):
    """write 命令"""
    p = subparsers.add_parser("write", help="写章节")
    p.add_argument("chapter", nargs="?", default="next", help="章节 ID 或 'next'")
    p.add_argument("--no-review", action="store_true", help="跳过审查")
    p.add_argument("--temperature", "-T", type=float, default=0.7, help="写作温度")


def _add_multi_write_command(subparsers):
    """multi-write 命令"""
    p = subparsers.add_parser("multi-write", help="使用多 Agent 编排写章节")
    p.add_argument("chapter", nargs="?", default="next", help="章节 ID 或 'next'")
    p.add_argument("--temperature", "-T", type=float, default=0.7, help="写作温度")
    p.add_argument("--no-review", action="store_true", help="跳过审查")
    p.add_argument("--show-packet", action="store_true", help="先输出组装包")
    p.add_argument("--packet-output-dir", help="组装包测试输出目录（自动命名）")


def _add_review_command(subparsers):
    """review 命令"""
    p = subparsers.add_parser("review", help="审查章节")
    p.add_argument("chapter", nargs="?", default="latest", help="章节 ID 或 'latest'")
    p.add_argument("--strict", action="store_true", help="严格模式")


def _add_context_command(subparsers):
    """context 命令"""
    p = subparsers.add_parser("context", help="构建上下文")
    p.add_argument("chapter", nargs="?", default="next", help="章节 ID")
    p.add_argument("--show", action="store_true", help="显示上下文内容")


def _add_assemble_command(subparsers):
    """assemble 命令"""
    p = subparsers.add_parser("assemble", help="按 V2 规则组装章节上下文包")
    p.add_argument("chapter", nargs="?", default="next", help="章节 ID 或 'next'")
    p.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认 markdown）",
    )
    p.add_argument("--output", "-o", help="输出文件路径")
    p.add_argument("--output-dir", help="测试输出目录（自动命名文件）")
    p.add_argument("--no-print", action="store_true", help="不在终端打印结果")


def _add_style_command(subparsers):
    """style 命令"""
    p = subparsers.add_parser("style", help="风格管理")
    sub = p.add_subparsers(dest="style_action")

    extract = sub.add_parser("extract", help="提取参考风格")
    extract.add_argument("ref_name", help="参考作品名")
    extract.add_argument("--source", required=True, help="源文件路径")
    extract.add_argument("--chunk-size", type=int, default=30000, help="分块字数（默认30000）")

    synthesize = sub.add_parser("synthesize", help="合成风格")
    synthesize.add_argument("--novel-id", default="current", help="小说 ID")


def _add_radar_command(subparsers):
    """radar 命令 - 市场分析"""
    p = subparsers.add_parser("radar", help="市场趋势分析")
    p.add_argument("--platform", "-p", nargs="+", help="平台列表（默认全部）")
    p.add_argument("--top", "-n", type=int, default=5, help="每个平台推荐数")
    p.add_argument("--output", "-o", help="保存结果到文件")


def _add_status_command(subparsers):
    """status 命令"""
    subparsers.add_parser("status", help="查看项目状态")


def _add_doctor_command(subparsers):
    """doctor 命令"""
    subparsers.add_parser("doctor", help="环境与路径自检")


def _add_agent_command(subparsers):
    """agent 命令 - 已退役"""
    p = subparsers.add_parser(
        "agent",
        help="已退役：请改用 openwrite dante",
        description="已退役：请改用 openwrite dante",
    )
    p.add_argument("instruction", nargs="?", default="查看项目状态", help="自然语言指令")
    p.add_argument("--max-turns", type=int, default=20, help="最大循环次数")
    p.add_argument("--quiet", action="store_true", help="静默模式")


def _cmd_init(args) -> int:
    """初始化项目"""
    from tools.init_project import init_project

    novel_id = args.novel_id
    project_root = Path.cwd()

    logger.info(f"初始化项目: {novel_id}")
    if getattr(args, "template", "default") != "default":
        logger.info("当前仅支持 default 模板，已按默认模板初始化。")

    try:
        init_project(project_root, novel_id)
    except Exception as exc:
        logger.error(f"初始化失败: {exc}")
        return 1
    return 0


def _cmd_write(args) -> int:
    """写章节"""
    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("未找到 novel_config.yaml，请先运行 openwrite init")
        return 1

    novel_id = config.get("novel_id", "unknown")
    style_id = config.get("style_id", novel_id)
    chapter = args.chapter

    if chapter == "next":
        chapter = _get_next_chapter(project_root, novel_id)

    logger.info(f"写章节: {chapter}")
    context_packet = _assemble_context_packet(project_root, novel_id, style_id, chapter)
    scheduler, workflow = _load_or_create_workflow(project_root, novel_id, chapter)
    scheduler.start_stage(workflow, "context_assembly")
    scheduler.complete_stage(
        workflow,
        "context_assembly",
        message="canonical packet assembled via CLI write",
        data={"chapter_id": chapter},
    )
    scheduler.start_stage(workflow, "writing")

    result = _exec_write_chapter(
        project_root,
        {
            "chapter_id": chapter,
            "context_packet": context_packet,
            "guidance": "",
            "target_words": 0,
            "temperature": args.temperature,
        },
    )

    if not result.get("ok"):
        scheduler.fail_stage(workflow, "writing", str(result.get("error", "write_failed")))
        logger.error(str(result.get("error", "写章节失败")))
        if getattr(args, "show", False):
            print(str(context_packet.get("outline", "")).strip() or json.dumps(context_packet, ensure_ascii=False, indent=2))
        return 1

    scheduler.complete_stage(
        workflow,
        "writing",
        message="chapter written via CLI write",
        data={"draft_path": str(result.get("draft_path", ""))},
    )
    _sync_book_state_after_write(
        project_root,
        novel_id,
        chapter,
        review_passed=None,
        action_prefix="cli_write",
    )

    logger.info(f"章节已生成: {result.get('title', '')}")
    logger.info(f"字数: {result.get('word_count', 0)}")
    truth_updates = result.get("truth_updates", {})
    if truth_updates:
        logger.info(f"真相文件已更新: {', '.join(truth_updates.keys())}")
    else:
        logger.info("本章未产生可写入的真相增量")
    return 0


def _cmd_sync(args) -> int:
    """同步 src -> data（outline/character）"""
    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config and not args.novel_id:
        logger.error("未找到 novel_config.yaml，请指定 --novel-id")
        return 1

    novel_id = args.novel_id or config.get("novel_id", "")
    if not novel_id:
        logger.error("无法确定 novel_id")
        return 1

    before = _collect_sync_status(project_root, novel_id)
    suggestions = _build_sync_suggestions(before)
    before_actions = _build_sync_actions(before)

    if not args.json:
        _print_sync_status(before)
        for msg in suggestions:
            logger.info(f"  建议: {msg}")

    if args.check:
        code = 2 if before["needs_sync"] else 0
        if args.json:
            print(
                json.dumps(
                    {
                        "mode": "check",
                        "status": before,
                        "suggestions": suggestions,
                        "actions": before_actions,
                        "ok": not before["needs_sync"],
                        "exit_code": code,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        if before["needs_sync"]:
            if not args.json:
                logger.warning("检测到未同步项（仅检查模式，未执行写入）")
            return code
        if not args.json:
            logger.info("同步状态正常")
        return code

    _run_sync(project_root, novel_id)
    after = _collect_sync_status(project_root, novel_id)
    after_suggestions = _build_sync_suggestions(after)
    after_actions = _build_sync_actions(after)
    code = 0 if not after["needs_sync"] else 1

    if args.json:
        print(
            json.dumps(
                {
                    "mode": "apply",
                    "before": before,
                    "after": after,
                    "suggestions": after_suggestions,
                    "actions": after_actions,
                    "ok": not after["needs_sync"],
                    "exit_code": code,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return code

    _print_sync_status(after)
    for msg in after_suggestions:
        logger.info(f"  建议: {msg}")

    if after["needs_sync"]:
        logger.warning("同步执行后仍存在未同步项，请检查输入文件格式")
        return code

    logger.info("同步完成")
    return code


def _cmd_multi_write(args) -> int:
    """多 Agent 编排写章节"""
    import asyncio

    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("未找到 novel_config.yaml，请先运行 openwrite init")
        return 1

    novel_id = config.get("novel_id", "unknown")
    style_id = config.get("style_id", novel_id)
    chapter = args.chapter
    if chapter == "next":
        chapter = _get_next_chapter(project_root, novel_id)

    logger.info(f"多 Agent 写章节: {chapter}")

    async def do_multi_write():
        try:
            from tools.llm import LLMClient, LLMConfig
            from tools.agent import AgentContext, MultiAgentDirector

            llm_config = LLMConfig.from_env()
            client = LLMClient(llm_config)
            agent_ctx = AgentContext(client, llm_config.model, str(project_root))
            director = MultiAgentDirector(agent_ctx, novel_id=novel_id, style_id=style_id)
            scheduler, workflow = _load_or_create_workflow(project_root, novel_id, chapter)

            if args.show_packet:
                packet = director.assemble_packet(chapter)
                scheduler.start_stage(workflow, "context_assembly")
                scheduler.complete_stage(
                    workflow,
                    "context_assembly",
                    message="packet assembled for multi-write",
                    data={"chapter_id": chapter},
                )
                packet_dir = (
                    Path(args.packet_output_dir)
                    if args.packet_output_dir
                    else _get_test_output_dir(project_root, novel_id, "multi_write")
                )
                packet_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                packet_path = packet_dir / f"{chapter}_packet_{stamp}.md"
                packet_path.write_text(packet.to_markdown(), encoding="utf-8")
                logger.info(f"组装包快照: {packet_path}")
                print(packet.to_markdown())
            else:
                scheduler.start_stage(workflow, "context_assembly")
                scheduler.complete_stage(
                    workflow,
                    "context_assembly",
                    message="packet assembly delegated to multi-write director",
                    data={"chapter_id": chapter},
                )

            scheduler.start_stage(workflow, "writing")

            result = await director.run(
                chapter_id=chapter,
                temperature=args.temperature,
                run_review=not args.no_review,
            )

            if not result.draft:
                scheduler.fail_stage(workflow, "writing", "未生成草稿")
                logger.error("写作失败：未生成草稿")
                return 1

            draft_path = _save_chapter(
                project_root,
                novel_id,
                chapter,
                result.draft.title,
                result.draft.content,
            )
            scheduler.complete_stage(
                workflow,
                "writing",
                message="chapter written via multi-write",
                data={"draft_path": str(draft_path)},
            )
            logger.info(f"章节已保存: {chapter}")

            if result.review:
                scheduler.start_stage(workflow, "review")
                scheduler.complete_stage(
                    workflow,
                    "review",
                    message="chapter reviewed via multi-write",
                    data=_workflow_review_payload(result.review),
                )
                logger.info(f"审查得分: {result.review.score:.0f}/100")
                logger.info(f"审查问题数: {len(result.review.issues)}")

            if result.applied_state_updates:
                logger.info(f"已更新状态文件: {', '.join(result.applied_state_updates.keys())}")

            if result.new_concepts:
                logger.info(f"已新增概念文档: {', '.join(result.new_concepts)}")

            _sync_book_state_after_write(
                project_root,
                novel_id,
                chapter,
                review_passed=bool(result.review.passed) if result.review else None,
                action_prefix="cli_multi_write",
            )
            return 0

        except ImportError as e:
            logger.warning(f"LLM 模块未安装或配置: {e}")
            logger.info("提示: 设置环境变量 LLM_API_KEY, LLM_MODEL 等")
            return 1

    return asyncio.run(do_multi_write())


def _cmd_review(args) -> int:
    """审查章节"""
    import asyncio

    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("未找到 novel_config.yaml")
        return 1

    novel_id = config.get("novel_id", "unknown")
    chapter = args.chapter

    if chapter == "latest":
        chapter = _get_latest_chapter(project_root, novel_id)

    logger.info(f"审查章节: {chapter}")

    content = _load_chapter(project_root, novel_id, chapter)
    if not content:
        logger.error(f"未找到章节: {chapter}")
        return 1

    result = _exec_review_chapter(project_root, {"chapter_id": chapter})
    if not result.get("ok"):
        logger.error(str(result.get("error", "审查失败")))
        return 1

    logger.info(f"审查结果: {'通过' if result.get('passed') else '未通过'}")
    logger.info(f"得分: {float(result.get('score', 0)):.0f}/100")
    logger.info(f"问题数: {int(result.get('issues', 0))}")

    scheduler, workflow = _load_or_create_workflow(project_root, novel_id, chapter)
    scheduler.start_stage(workflow, "review")
    scheduler.complete_stage(
        workflow,
        "review",
        message="chapter reviewed via CLI review",
        data={
            "passed": bool(result.get("passed", False)),
            "errors": [],
            "warnings": [],
        },
    )
    _sync_book_state_after_write(
        project_root,
        novel_id,
        chapter,
        review_passed=bool(result.get("passed", False)),
        action_prefix="cli_review",
    )
    return 0


def _cmd_context(args) -> int:
    """构建上下文"""
    from tools.context_builder import ContextBuilder

    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("未找到 novel_config.yaml")
        return 1

    novel_id = config.get("novel_id", "unknown")
    chapter = args.chapter

    builder = ContextBuilder(project_root, novel_id)
    context = builder.build_generation_context(chapter, window_size=5)

    if args.show:
        print(context.to_prompt_context())
    else:
        sections = context.to_prompt_sections()
        logger.info(f"上下文 ({len(sections)} 个段落):")
        for name in sections:
            logger.info(f"  - {name}")

    return 0


def _cmd_assemble(args) -> int:
    """按 V2 规则组装章节上下文包"""
    import json
    from dataclasses import asdict

    from tools.chapter_assembler import ChapterAssemblerV2

    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("未找到 novel_config.yaml")
        return 1

    novel_id = config.get("novel_id", "unknown")
    style_id = config.get("style_id", novel_id)
    chapter = args.chapter

    if chapter == "next":
        chapter = _get_next_chapter(project_root, novel_id)

    assembler = ChapterAssemblerV2(project_root, novel_id, style_id=style_id)
    packet = assembler.assemble(chapter)

    if args.format == "json":
        rendered = json.dumps(asdict(packet), ensure_ascii=False, indent=2)
        ext = "json"
    else:
        rendered = packet.to_markdown()
        ext = "md"

    # 为调试/验收固定保存一份上下文快照，便于回看组装效果。
    target_dir = (
        Path(args.output_dir)
        if args.output_dir
        else _get_test_output_dir(project_root, novel_id, "context_packets")
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = target_dir / f"{chapter}_{stamp}.{ext}"
    snapshot_path.write_text(rendered, encoding="utf-8")
    logger.info(f"组装结果快照: {snapshot_path}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        logger.info(f"组装结果已输出: {output_path}")

    if not args.no_print and not args.output:
        print(rendered)

    return 0


def _cmd_style(args) -> int:
    """风格管理"""
    if args.style_action == "extract":
        return _cmd_style_extract(args)
    elif args.style_action == "synthesize":
        return _cmd_style_synthesize(args)
    else:
        logger.error("请指定 style 子命令: extract, synthesize")
        return 1


def _cmd_style_synthesize(args) -> int:
    """合成作品风格文档。"""
    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config and getattr(args, "novel_id", "current") == "current":
        logger.error("未找到 novel_config.yaml，请先运行 openwrite init")
        return 1

    novel_id = (
        config.get("novel_id", "")
        if getattr(args, "novel_id", "current") == "current"
        else getattr(args, "novel_id", "")
    )
    if not novel_id:
        logger.error("无法确定 novel_id")
        return 1

    style_id = config.get("style_id", novel_id) if config else novel_id
    style_dir = project_root / "data" / "novels" / novel_id / "data" / "style"
    style_dir.mkdir(parents=True, exist_ok=True)
    composed_path = style_dir / "composed.md"
    composed_path.write_text(
        _build_synthesized_style_document(project_root, novel_id, style_id),
        encoding="utf-8",
    )
    logger.info(f"合成风格文档已写入: {composed_path}")
    return 0


def _cmd_style_extract(args) -> int:
    """从参考作品提取风格（AI批量提取）"""
    from tools.style_extraction_pipeline import StyleExtractionPipeline
    from tools.llm import LLMClient, LLMConfig, Message

    source_file = Path(args.source)
    if not source_file.exists():
        logger.error(f"源文件不存在: {source_file}")
        return 1

    ref_name = args.ref_name
    project_root = Path.cwd()

    logger.info(f"初始化风格提取: {ref_name}")
    logger.info(f"源文件: {source_file}")

    pipeline = StyleExtractionPipeline(
        project_root=project_root,
        novel_id="style_extraction",
        source_name=ref_name,
        chunk_size=args.chunk_size,
    )

    try:
        progress = pipeline.prepare(source_file=source_file)
        logger.info(f"文本已切割为 {progress.total_chunks} 个chunk")
    except Exception as e:
        logger.error(f"准备失败: {e}")
        return 1

    llm_config = LLMConfig.from_env()
    client = LLMClient(llm_config)

    STYLE_ANALYSIS_PROMPT = """你是一位专业的文学风格分析师。请分析以下文本片段的风格特征。

分析要求：
1. 提取【通用技法】：跨作品适用的写作技巧（叙述方式、结构技巧等）
2. 提取【作者风格】：该作品的独特风格印记（用词、句式、节奏等）
3. 提取【作品设定】：专属该作品的术语、角色特征、世界观规则

输出格式（JSON）：
{
    "craft": ["技法1", "技法2", ...],
    "author": ["风格1", "风格2", ...],
    "novel": ["设定1", "设定2", ...],
    "summary": "本片段核心发现（50字内）"
}

只返回JSON，不要其他内容。"""

    total_processed = 0
    for batch in progress.batches:
        if batch.status != "pending":
            continue

        logger.info(f"处理 chunk {batch.chunk_index + 1}/{progress.total_chunks}...")

        try:
            context = pipeline.get_batch_context(batch.chunk_index)
        except Exception as e:
            logger.error(f"获取chunk上下文失败: {e}")
            continue

        chunk_text = context["chunk_text"]
        if len(chunk_text) > 8000:
            chunk_text = chunk_text[:8000] + "..."

        messages = [
            Message("system", STYLE_ANALYSIS_PROMPT),
            Message("user", f"请分析以下文本片段：\n\n{chunk_text}"),
        ]

        try:
            response = client.chat(messages, temperature=0.3, stream=False)
            content = response.content.strip()

            import json

            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            findings = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Chunk {batch.chunk_index} AI返回格式错误，使用空发现")
            findings = {"craft": [], "author": [], "novel": [], "summary": "解析失败"}
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            findings = {"craft": [], "author": [], "novel": [], "summary": f"错误: {e}"}

        try:
            pipeline.save_batch_result(batch.chunk_index, findings)
            total_processed += 1
            craft_count = len(findings.get("craft", []))
            author_count = len(findings.get("author", []))
            logger.info(f"  -> 发现: {craft_count}技法, {author_count}风格")
        except Exception as e:
            logger.error(f"保存结果失败: {e}")

    if total_processed == 0:
        logger.warning("没有处理任何chunk（可能都已完成）")
        return 0

    logger.info(f"\n开始合并 {total_processed} 个chunk的发现...")

    try:
        merge_result = pipeline.merge_all()
        logger.info(f"合并完成: 处理了 {merge_result['total_batches']} 个批次")
    except Exception as e:
        logger.error(f"合并失败: {e}")
        return 1

    logger.info(f"\n风格提取完成！共处理 {total_processed} 个chunk")
    logger.info(f"结果保存在: data/styles/{ref_name}/")

    return 0


def _cmd_goethe(args) -> int:
    """交互式引导"""
    from tools.goethe import run_goethe

    return run_goethe()


def _cmd_dante(args) -> int:
    """Dante 入口 - 过渡性封装"""
    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("openwrite dante 未找到 novel_config.yaml，请先运行 openwrite init")
        return 1

    novel_id = config.get("novel_id") or "current"

    try:
        from tools.agent.orchestrator import OpenWriteOrchestrator
        from tools.agent.tool_runtime import build_tool_executors

        orchestrator = OpenWriteOrchestrator(
            project_root=project_root,
            novel_id=novel_id,
            tool_executors=build_tool_executors(project_root),
        )
        return orchestrator.run_cli(
            instruction=args.instruction,
            quiet=args.quiet,
            max_turns=args.max_turns,
        )
    except ImportError as e:
        logger.error(f"Dante 模块未安装: {e}")
        return 1
    except Exception as e:
        logger.error(f"Dante 执行失败: {e}")
        return 1


def _cmd_radar(args) -> int:
    """市场分析"""
    import asyncio

    async def do_radar():
        try:
            from tools.llm import LLMClient, LLMConfig
            from tools.agent import AgentContext
            from tools.radar import RadarAgent

            llm_config = LLMConfig.from_env()
            client = LLMClient(llm_config)
            agent_ctx = AgentContext(client, llm_config.model, str(Path.cwd()))

            radar = RadarAgent(agent_ctx)
            result = await radar.scan_market(
                platforms=args.platform,
                top_n=args.top,
            )

            print("\n" + "=" * 50)
            print("   市场分析结果")
            print("=" * 50)

            for i, rec in enumerate(result.platform_recommendations, 1):
                print(f"\n{i}. [{rec.confidence:.0%}] {rec.platform}/{rec.genre}")
                print(f"   创意: {rec.concept}")
                print(f"   理由: {rec.reasoning}")
                if rec.benchmarks:
                    print(f"   参考: {', '.join(rec.benchmarks[:3])}")

            if result.trends:
                print("\n" + "-" * 50)
                print("趋势:")
                for trend in result.trends:
                    print(f"  - {trend}")

            if args.output:
                radar.save_result(result, args.output)
                print(f"\n已保存到: {args.output}")

            return 0

        except ImportError as e:
            logger.error(f"LLM 模块未安装: {e}")
            logger.info("设置环境变量: LLM_API_KEY, LLM_MODEL")
            return 1
        except Exception as e:
            logger.error(f"市场分析失败: {e}")
            return 1

    return asyncio.run(do_radar())


def _cmd_status(args) -> int:
    """查看状态"""
    from tools.agent.book_state import BookStateStore
    from tools.truth_manager import TruthFilesManager

    project_root = Path.cwd()
    config = _load_config(project_root)

    if not config:
        logger.error("未找到 novel_config.yaml")
        return 1

    novel_id = config.get("novel_id", "unknown")
    current_arc = config.get("current_arc", "N/A")
    current_chapter = config.get("current_chapter", "N/A")

    state_store = BookStateStore(project_root, novel_id)
    if state_store.path.exists():
        try:
            state = state_store.load_or_create()
            current_arc = state.current_arc or current_arc
            current_chapter = state.current_chapter or current_chapter
        except Exception:
            pass

    logger.info(f"项目: {novel_id}")
    logger.info(f"当前篇: {current_arc}")
    logger.info(f"当前章: {current_chapter}")

    truth_manager = TruthFilesManager(project_root, novel_id)
    chapter_count = len(_list_chapter_ids(project_root, novel_id))
    logger.info(f"已写章节: {chapter_count}")

    snapshots = truth_manager.list_snapshots()
    logger.info(f"快照数: {len(snapshots)}")

    return 0


def _cmd_doctor(args) -> int:
    """环境与路径自检"""
    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("未找到 novel_config.yaml")
        return 1

    novel_id = config.get("novel_id", "unknown")
    novel_root = project_root / "data" / "novels" / novel_id
    src_root = novel_root / "src"
    runtime_root = novel_root / "data"
    packet_dir = _get_test_output_dir(project_root, novel_id, "context_packets")

    logger.info(f"工作目录: {project_root}")
    logger.info(f"小说 ID: {novel_id}")
    logger.info(f"源目录: {src_root} ({'存在' if src_root.exists() else '缺失'})")
    logger.info(f"运行目录: {runtime_root} ({'存在' if runtime_root.exists() else '缺失'})")
    logger.info(f"测试输出目录: {packet_dir}")

    model = (os.environ.get("LLM_MODEL") or "").strip()
    provider = (os.environ.get("LLM_PROVIDER") or "").strip()
    api_key = (os.environ.get("LLM_API_KEY") or "").strip()
    masked = "<missing>"
    if api_key:
        masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"

    logger.info(f"LLM_PROVIDER: {provider or '<missing>'}")
    logger.info(f"LLM_MODEL: {model or '<missing>'}")
    logger.info(f"LLM_API_KEY: {masked}")

    return 0


def _cmd_agent(args) -> int:
    """agent 命令 - 已退役"""
    logger.error("openwrite agent 已退役，请改用 openwrite dante。")
    return 1


def build_cli_tool_executors(project_root: Path) -> dict[str, Callable[[dict], dict]]:
    """构建 CLI 工具执行器映射（公开 API）。"""
    return {
        # 写作相关
        "write_chapter": lambda a: _exec_write_chapter(project_root, a),
        "review_chapter": lambda a: _exec_review_chapter(project_root, a),
        "get_status": lambda a: _exec_get_status(project_root),
        "get_context": lambda a: _exec_get_context(project_root, a),
        "list_chapters": lambda a: _exec_list_chapters(project_root),
        "create_outline": lambda a: _exec_create_outline(project_root, a),
        "create_character": lambda a: _exec_create_character(project_root, a),
        "get_truth_files": lambda a: _exec_get_truth_files(project_root),
        "update_truth_file": lambda a: _exec_update_truth_file(project_root, a),
        # 伏笔管理
        "create_foreshadowing": lambda a: _exec_create_foreshadowing(project_root, a),
        "list_foreshadowing": lambda a: _exec_list_foreshadowing(project_root, a),
        "update_foreshadowing": lambda a: _exec_update_foreshadowing(project_root, a),
        "validate_foreshadowing": lambda a: _exec_validate_foreshadowing(project_root, a),
        # 世界查询
        "query_world": lambda a: _exec_query_world(project_root, a),
        "get_world_relations": lambda a: _exec_get_world_relations(project_root, a),
        # 状态验证
        "validate_truth": lambda a: _exec_validate_truth(project_root, a),
        # 对话质量
        "extract_dialogue_fingerprint": lambda a: _exec_extract_dialogue_fingerprint(
            project_root, a
        ),
        # 后置验证
        "validate_post_write": lambda a: _exec_validate_post_write(project_root, a),
        # 工作流
        "get_workflow_status": lambda a: _exec_get_workflow_status(project_root, a),
        "start_workflow": lambda a: _exec_start_workflow(project_root, a),
        "advance_workflow": lambda a: _exec_advance_workflow(project_root, a),
        # 文本处理
        "chunk_text": lambda a: _exec_chunk_text(project_root, a),
        "compress_section": lambda a: _exec_compress_section(project_root, a),
    }


def build_dante_tool_layers(project_root: Path) -> dict[str, object]:
    """构建 Dante 可直接消费的工具分层视图。"""
    from tools.agent.dante_actions import DanteActionAdapter
    from tools.agent.orchestrator import OpenWriteOrchestrator
    from tools.agent.toolkits import DANTE_ACTION_TOOLKIT, DANTE_DIRECT_TOOLKIT

    tool_executors = build_cli_tool_executors(project_root)
    action_tool_executors = _build_dante_action_executors(
        project_root,
        tool_executors=tool_executors,
        orchestrator_cls=OpenWriteOrchestrator,
        adapter_cls=DanteActionAdapter,
    )
    return {
        "tool_executors": tool_executors,
        "direct_toolkit": DANTE_DIRECT_TOOLKIT,
        "action_toolkit": DANTE_ACTION_TOOLKIT,
        "direct_tool_executors": {
            name: tool_executors[name]
            for name in DANTE_DIRECT_TOOLKIT
            if name in tool_executors
        },
        "action_tool_executors": action_tool_executors,
    }


def _build_dante_action_executors(
    project_root: Path,
    *,
    tool_executors: dict[str, Callable[[dict], dict]],
    orchestrator_cls,
    adapter_cls,
) -> dict[str, Callable[[dict], dict]]:
    config = _load_config(project_root)
    novel_id = (config or {}).get("novel_id") or "current"
    orchestrator = orchestrator_cls(
        project_root=project_root,
        novel_id=novel_id,
        tool_executors=tool_executors,
    )
    adapter = adapter_cls(orchestrator)

    def _read_text_arg(args: dict, *keys: str, default: str = "") -> str:
        for key in keys:
            value = args.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return default

    return {
        "summarize_ideation": lambda args: adapter.summarize_ideation(),
        "confirm_ideation_summary": lambda args: adapter.confirm_ideation_summary(
            _read_text_arg(args, "text", "confirmation", default="这个汇总可以")
        ),
        "generate_outline_draft": lambda args: adapter.generate_outline_draft(
            _read_text_arg(args, "request_text", "text", default="帮我生成一份四级大纲")
        ),
        "run_chapter_preflight": lambda args: adapter.run_chapter_preflight(
            _read_text_arg(args, "chapter_id", "chapter", default="ch_001")
        ),
    }


def _coerce_target_words(value) -> int:
    try:
        words = int(value)
    except (TypeError, ValueError):
        return 0
    return words if words > 0 else 0


def _extract_doc_title(text: str, fallback: str = "角色") -> str:
    stripped = str(text or "").strip()
    if not stripped:
        return fallback

    for line in stripped.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("#"):
            return candidate.lstrip("#").strip() or fallback
    return fallback


def _render_packet_outline(prompt_sections: dict) -> str:
    if not isinstance(prompt_sections, dict):
        return ""

    preferred = (
        "大纲窗口",
        "当前章节",
        "戏剧位置",
        "本章目标",
        "上文",
    )
    parts = []
    for key in preferred:
        value = str(prompt_sections.get(key, "")).strip()
        if value:
            parts.append(f"## {key}\n{value}")
    return "\n\n".join(parts).strip()


def _compose_style_profile(style_documents: dict, *, max_chars: int) -> str:
    if not isinstance(style_documents, dict):
        return ""

    labeled_keys = [
        ("summary", "风格摘要", 600),
        ("prompt_section", "风格指南", 800),
        ("work.composed", "作品合成风格", 1200),
        ("work.fingerprint", "作品风格指纹", 800),
        ("craft.dialogue_craft", "对话技法", 700),
        ("craft.scene_craft", "场景技法", 700),
        ("craft.rhythm_craft", "节奏技法", 700),
        ("craft.humanization", "去模板化约束", 700),
        ("craft.ai_patterns", "AI痕迹规避", 700),
        ("reference.summary", "参考风格摘要", 700),
        ("reference.voice", "参考叙述声音", 700),
        ("reference.language", "参考语言习惯", 700),
        ("reference.rhythm", "参考节奏", 700),
        ("reference.dialogue", "参考对话", 700),
        ("reference.consistency", "参考一致性", 700),
    ]

    parts: list[str] = []
    used: set[str] = set()
    for key, label, limit in labeled_keys:
        value = str(style_documents.get(key, "")).strip()
        if not value:
            continue
        used.add(key)
        parts.append(f"## {label}\n{value[:limit]}")

    for key in sorted(style_documents.keys()):
        if key in used:
            continue
        value = str(style_documents.get(key, "")).strip()
        if not value:
            continue
        parts.append(f"## {key}\n{value[:600]}")

    profile = "\n\n".join(parts).strip()
    if max_chars and len(profile) > max_chars:
        return profile[:max_chars]
    return profile


def _normalize_packet_characters(documents) -> list[dict]:
    characters = []
    if isinstance(documents, dict):
        for name, content in documents.items():
            text = str(content or "").strip()
            if not text:
                continue
            characters.append(
                {
                    "name": str(name or "").strip() or _extract_doc_title(text, fallback="角色"),
                    "description": text[:1200],
                }
            )
        return characters

    if not isinstance(documents, list):
        return characters

    for index, item in enumerate(documents, start=1):
        text = str(item or "").strip()
        if not text:
            continue
        characters.append(
            {
                "name": _extract_doc_title(text, fallback=f"角色{index}"),
                "description": text[:1200],
            }
        )
    return characters


def _packet_to_context_packet(packet) -> dict:
    if isinstance(packet, dict):
        context_packet = dict(packet)
    elif is_dataclass(packet):
        context_packet = asdict(packet)
    else:
        context_packet = {}
        for key in (
            "story_background",
            "previous_chapter_content",
            "style_documents",
            "character_documents",
            "concept_documents",
            "prompt_sections",
            "foundation",
        ):
            value = getattr(packet, key, None)
            if value not in (None, ""):
                context_packet[key] = value
        if hasattr(packet, "to_markdown"):
            context_packet["outline"] = packet.to_markdown()

    concept_documents = context_packet.get("concept_documents")
    if not isinstance(concept_documents, dict):
        concept_documents = {}
    else:
        concept_documents = dict(concept_documents)

    for key in ("current_state", "ledger", "relationships"):
        value = context_packet.get(key, getattr(packet, key, ""))
        if isinstance(value, str) and value.strip():
            concept_documents.setdefault(key, value.strip())
    context_packet["concept_documents"] = concept_documents

    outline = str(context_packet.get("outline", "")).strip()
    if not outline and hasattr(packet, "to_markdown"):
        outline = str(packet.to_markdown()).strip()
    if outline:
        context_packet["outline"] = outline

    style_documents = context_packet.get("style_documents")
    if not isinstance(style_documents, dict):
        context_packet["style_documents"] = {}

    if "character_documents" not in context_packet:
        context_packet["character_documents"] = {}

    return context_packet


def _build_reviewer_context_payload(context_packet: dict) -> dict:
    if not isinstance(context_packet, dict):
        return {}

    concept_documents = context_packet.get("concept_documents", {})
    if not isinstance(concept_documents, dict):
        concept_documents = {}
    style_documents = context_packet.get("style_documents", {})
    if not isinstance(style_documents, dict):
        style_documents = {}

    character_bits: list[str] = []
    character_documents = context_packet.get("character_documents", {})
    if isinstance(character_documents, dict):
        character_bits.extend(
            str(content).strip() for content in character_documents.values() if str(content).strip()
        )
    elif isinstance(character_documents, list):
        character_bits.extend(str(item).strip() for item in character_documents if str(item).strip())

    outline = str(context_packet.get("outline", "")).strip() or _render_packet_outline(
        context_packet.get("prompt_sections", {})
    )
    style_profile = _compose_style_profile(style_documents, max_chars=2500)

    payload = {
        "character_profiles": "\n\n".join(character_bits)[:4000],
        "current_state": str(concept_documents.get("current_state", "")).strip(),
        "relationships": str(concept_documents.get("relationships", "")).strip(),
    }
    if outline:
        payload["outline"] = outline[:4000]
    if style_profile:
        payload["style_profile"] = style_profile[:2000]
    previous = str(context_packet.get("previous_chapter_content", "")).strip()
    if previous:
        payload["recent_chapters"] = previous[:2000]
    return {key: value for key, value in payload.items() if value}


def _assemble_context_packet(project_root: Path, novel_id: str, style_id: str, chapter_id: str) -> dict:
    from tools.chapter_assembler import ChapterAssemblerV2

    packet = ChapterAssemblerV2(project_root=project_root, novel_id=novel_id, style_id=style_id).assemble(chapter_id)
    return _packet_to_context_packet(packet)


def _sync_book_state_after_write(
    project_root: Path,
    novel_id: str,
    chapter_id: str,
    *,
    review_passed: bool | None = None,
    action_prefix: str = "cli_write",
) -> None:
    from tools.agent.book_state import BookStage, BookStateStore

    state_store = BookStateStore(project_root, novel_id)
    state = state_store.load_or_create()
    current_idx = _parse_chapter_no(state.current_chapter)
    next_idx = _parse_chapter_no(chapter_id)
    if next_idx >= current_idx:
        state.current_chapter = chapter_id
    if review_passed is None:
        state.stage = BookStage.REVIEW_AND_REVISE
        state.blocking_reason = "review_not_run"
        state.last_agent_action = f"{action_prefix}_pending_review"
    elif review_passed:
        state.stage = BookStage.CHAPTER_PREFLIGHT
        state.blocking_reason = ""
        state.last_agent_action = f"{action_prefix}_review_passed"
    else:
        state.stage = BookStage.REVIEW_AND_REVISE
        state.blocking_reason = "review_revision_requested"
        state.last_agent_action = f"{action_prefix}_review_failed"
    state_store.save(state)


def _workflow_review_payload(review_result) -> dict:
    issues = getattr(review_result, "issues", []) or []
    errors: list[str] = []
    warnings: list[str] = []
    for issue in issues:
        description = str(getattr(issue, "description", "") or "").strip()
        if not description:
            continue
        severity = str(getattr(issue, "severity", "") or "").strip().lower()
        if severity == "critical":
            errors.append(description)
        else:
            warnings.append(description)
    return {
        "passed": bool(getattr(review_result, "passed", False)),
        "errors": errors,
        "warnings": warnings,
    }


def _load_or_create_workflow(project_root: Path, novel_id: str, chapter_id: str):
    from tools.workflow_scheduler import WorkflowScheduler

    scheduler = WorkflowScheduler(project_root, novel_id)
    workflow = scheduler.load_or_create(chapter_id)
    return scheduler, workflow


def _build_writer_context_payload(
    *,
    context,
    truth,
    context_packet: dict,
    guidance: str,
    target_words: int,
) -> dict:
    payload = {
        "target_words": target_words or getattr(context, "target_words", 0),
        "chapter_goals": getattr(context, "chapter_goals", []),
        "current_state": getattr(context, "current_state", ""),
        "foreshadowing_summary": getattr(context, "foreshadowing_summary", ""),
        "ledger": getattr(context, "ledger", ""),
        "relationships": truth.relationships,
    }

    if context_packet:
        prompt_sections = context_packet.get("prompt_sections", {})
        concept_documents = context_packet.get("concept_documents", {})
        style_documents = context_packet.get("style_documents", {})

        packet_outline = str(context_packet.get("outline", "")).strip() or _render_packet_outline(prompt_sections)
        if packet_outline:
            payload["outline"] = packet_outline

        style_profile = _compose_style_profile(style_documents, max_chars=4000)
        if style_profile:
            payload["style_profile"] = style_profile

        active_characters = _normalize_packet_characters(
            context_packet.get("character_documents", [])
        )
        if active_characters:
            payload["active_characters"] = active_characters

        payload["current_state"] = str(
            concept_documents.get("current_state") or payload.get("current_state", "")
        )
        payload["ledger"] = str(
            concept_documents.get("ledger") or payload.get("ledger", "")
        )
        payload["relationships"] = str(
            concept_documents.get("relationships") or payload.get("relationships", "")
        )
        payload["foreshadowing_summary"] = str(
            concept_documents.get("pending_hooks") or payload.get("foreshadowing_summary", "")
        )
        payload["recent_chapters"] = str(
            context_packet.get("previous_chapter_content") or ""
        )

        extra_parts = []
        story_background = str(context_packet.get("story_background", "")).strip()
        foundation = str(context_packet.get("foundation", "")).strip()
        world_rules = str(concept_documents.get("world_rules", "")).strip()

        if story_background:
            extra_parts.append(f"## 故事背景\n{story_background}")
        if foundation:
            extra_parts.append(f"## 基础设定\n{foundation}")
        if world_rules:
            extra_parts.append(f"## 世界规则\n{world_rules}")
        if guidance:
            extra_parts.append(f"## 额外要求\n{guidance}")
        if extra_parts:
            payload["external_context"] = "\n\n".join(extra_parts)
    elif guidance:
        payload["external_context"] = guidance

    return normalize_context_payload(payload, include_aliases=False)


def _exec_write_chapter(project_root: Path, args: dict) -> dict:
    """执行 write_chapter"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.context_builder import ContextBuilder
    from tools.agent import WriterAgent, AgentContext
    from tools.llm import LLMClient, LLMConfig

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "next")
    context_packet = args.get("context_packet") if isinstance(args.get("context_packet"), dict) else {}
    guidance = str(args.get("guidance", "") or "").strip()
    target_words = _coerce_target_words(args.get("target_words"))
    temperature = float(args.get("temperature", 0.7) or 0.7)

    builder = ContextBuilder(project_root, novel_id)
    context = builder.build_generation_context(chapter_id)
    from tools.truth_manager import TruthFilesManager

    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    try:
        llm_config = LLMConfig.from_env()
        client = LLMClient(llm_config)
        agent_ctx = AgentContext(client, llm_config.model, str(project_root))

        chapter_num = int(chapter_id.split("_")[-1]) if "_" in chapter_id else 1
        writer = WriterAgent(agent_ctx)
        writer_context = _build_writer_context_payload(
            context=context,
            truth=truth,
            context_packet=context_packet,
            guidance=guidance,
            target_words=target_words,
        )

        result = asyncio.run(
            writer.write_chapter(
                context=writer_context,
                chapter_number=chapter_num,
                temperature=temperature,
                target_words=writer_context.get("target_words") or None,
            )
        )

        truth_manager.create_snapshot(max(chapter_num - 1, 0))
        draft_path = _save_chapter(project_root, novel_id, chapter_id, result.title, result.content)
        updates = _collect_truth_updates(getattr(result, "state_updates", {}))
        if updates:
            truth_manager.update_truth_files(truth_manager.load_truth_files(), updates)

        return {
            "ok": True,
            "chapter_id": chapter_id,
            "title": result.title,
            "word_count": result.word_count,
            "draft_path": str(draft_path),
            "truth_updates": updates,
        }
    except Exception as e:
        return {"ok": False, "chapter_id": chapter_id, "error": str(e)}


def _exec_review_chapter(project_root: Path, args: dict) -> dict:
    """执行 review_chapter"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "latest")

    content = _load_chapter(project_root, novel_id, chapter_id)
    if not content:
        return {"error": f"未找到章节: {chapter_id}"}

    try:
        from tools.agent import ReviewerAgent, AgentContext
        from tools.llm import LLMClient, LLMConfig

        llm_config = LLMConfig.from_env()
        client = LLMClient(llm_config)
        agent_ctx = AgentContext(client, llm_config.model, str(project_root))

        reviewer = ReviewerAgent(agent_ctx)
        review_chapter_id = (
            chapter_id if chapter_id != "latest" else config.get("current_chapter", "ch_001")
        )
        style_id = config.get("style_id", novel_id)
        review_context = _build_reviewer_context_payload(
            _assemble_context_packet(project_root, novel_id, style_id, review_chapter_id)
        )

        result = asyncio.run(reviewer.review(content=content, context=review_context))

        return {
            "ok": True,
            "chapter_id": chapter_id,
            "passed": result.passed,
            "score": result.score,
            "issues": len(result.issues),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_get_status(project_root: Path) -> dict:
    """执行 get_status"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    novel_id = config.get("novel_id", "")

    from tools.truth_manager import TruthFilesManager

    truth_manager = TruthFilesManager(project_root, novel_id)
    chapter_ids = _list_chapter_ids(project_root, novel_id)
    snapshots = truth_manager.list_snapshots()

    return {
        "novel_id": novel_id,
        "current_arc": config.get("current_arc"),
        "current_chapter": config.get("current_chapter"),
        "chapters_written": len(chapter_ids),
        "snapshots": len(snapshots),
    }


def _exec_get_context(project_root: Path, args: dict) -> dict:
    """执行 get_context"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.context_builder import ContextBuilder

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "next")
    window_size = args.get("window_size", 5)

    builder = ContextBuilder(project_root, novel_id)
    context = builder.build_generation_context(chapter_id, window_size)

    return {
        "chapter_id": chapter_id,
        "target_words": context.target_words,
        "chapter_goals": context.chapter_goals,
        "sections": list(context.to_prompt_sections().keys()),
    }


def _exec_list_chapters(project_root: Path) -> dict:
    """执行 list_chapters"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    novel_id = config.get("novel_id", "")
    manuscript_root = project_root / "data" / "novels" / novel_id / "data" / "manuscript"

    chapters = []
    for chapter_id in sorted(_list_chapter_ids(project_root, novel_id), key=_parse_chapter_no):
        title = ""
        for p in sorted(manuscript_root.glob(f"**/{chapter_id}*.md")):
            text = _load_text_file(p)
            if text:
                first = text.splitlines()[0].strip() if text.splitlines() else ""
                if first.startswith("# "):
                    title = first[2:].strip()
                break
        chapters.append({"number": _parse_chapter_no(chapter_id), "chapter_id": chapter_id, "title": title})

    return {"chapters": chapters}


def _exec_create_outline(project_root: Path, args: dict) -> dict:
    """执行 create_outline"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    novel_id = config.get("novel_id", "")
    content = args.get("outline_content", "")

    outline_dir = project_root / "data" / "novels" / novel_id / "src"
    outline_dir.mkdir(parents=True, exist_ok=True)

    outline_file = outline_dir / "outline.md"
    outline_file.write_text(content, encoding="utf-8")

    return {"file": str(outline_file), "size": len(content)}


def _exec_create_character(project_root: Path, args: dict) -> dict:
    """执行 create_character"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    novel_id = config.get("novel_id", "")
    name = args.get("name", "")
    description = args.get("description", "")
    content = args.get("content", "")

    char_dir = project_root / "data" / "novels" / novel_id / "src" / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_stem(name)
    if not safe_name:
        return {"error": "角色名无效，不能包含路径分隔符或仅由特殊字符组成"}

    char_file = char_dir / f"{safe_name}.md"
    normalized = normalize_character_document(
        str(content or ""),
        fallback_id=safe_name,
        fallback_name=name,
        fallback_description=description,
    )
    char_file.write_text(normalized, encoding="utf-8")

    return {"ok": True, "file": str(char_file), "name": name, "safe_name": safe_name}


def _exec_get_truth_files(project_root: Path) -> dict:
    """执行 get_truth_files"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.truth_manager import TruthFilesManager

    novel_id = config.get("novel_id", "")
    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    current_state = truth.current_state[:500] if truth.current_state else ""
    ledger = truth.ledger[:500] if truth.ledger else ""
    relationships = truth.relationships[:500] if truth.relationships else ""

    return {
        "current_state": current_state,
        "ledger": ledger,
        "relationships": relationships,
    }


def _exec_update_truth_file(project_root: Path, args: dict) -> dict:
    """执行 update_truth_file"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.truth_manager import TruthFilesManager

    novel_id = config.get("novel_id", "")
    file_name = args.get("file_name", "")
    content = args.get("content", "")

    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    canonical = normalize_truth_file_key(file_name)
    file_map = {
        "current_state": "current_state",
        "ledger": "ledger",
        "relationships": "relationships",
    }

    attr = file_map.get(canonical)
    if not attr:
        return {"error": f"Unknown file: {file_name}"}

    setattr(truth, attr, content)
    truth_manager.save_truth_files(truth)

    return {"file": canonical, "size": len(content)}


def _load_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _safe_stem(value: str) -> str:
    """将用户输入规范化为安全文件名（不含路径成分）。"""
    text = (value or "").strip()
    # 拦截显式路径成分与目录跳转。
    if any(x in text for x in ("/", "\\")) or ".." in text:
        return ""
    # 允许中文、字母数字、下划线、中划线，空白转下划线。
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]", "", text)
    return text[:64]


def _collect_truth_updates(state_updates: dict) -> dict[str, str]:
    """从 Agent 结算输出中提取可落盘的真相字段。"""
    if not isinstance(state_updates, dict):
        return {}

    file_map = {
        "current_state": "current_state",
        "ledger": "ledger",
        "relationships": "relationships",
    }
    out: dict[str, str] = {}

    for key, value in state_updates.items():
        if not isinstance(value, str) or not value.strip():
            continue
        canonical = normalize_truth_file_key(key)
        attr = file_map.get(canonical)
        if attr:
            out[attr] = value

    return out


def _extract_markdown_list(text: str, heading: str) -> list[str]:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^\s*##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return []
    items: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            items.append(stripped[2:].strip())
    return items


def _extract_craft_headings(project_root: Path) -> list[str]:
    craft_dir = project_root / "craft"
    headings: list[str] = []
    for filename in ("dialogue_craft.md", "scene_craft.md", "rhythm_craft.md"):
        path = craft_dir / filename
        if not path.exists():
            continue
        text = _load_text_file(path)
        headings.extend(re.findall(r"^##\s+(.+)$", text, re.MULTILINE)[:5])
    deduped: list[str] = []
    seen = set()
    for heading in headings:
        normalized = heading.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped[:12]


def _load_reference_style_snippets(project_root: Path, style_id: str) -> dict[str, str]:
    ref_dir = project_root / "data" / "reference_styles" / style_id
    snippets: dict[str, str] = {}
    if not ref_dir.exists():
        return snippets
    for name in ("summary", "voice", "language", "rhythm", "dialogue", "consistency"):
        path = ref_dir / f"{name}.md"
        if not path.exists():
            continue
        text = _load_text_file(path).strip()
        if text:
            snippets[name] = text[:1200]
    return snippets


def _load_banned_phrases(project_root: Path) -> list[str]:
    humanization_path = project_root / "craft" / "humanization.yaml"
    if not humanization_path.exists():
        return []
    try:
        data = yaml.safe_load(humanization_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    phrases = data.get("banned_phrases", [])
    result: list[str] = []
    for item in phrases:
        if isinstance(item, dict):
            phrase = str(item.get("phrase", "")).strip()
        else:
            phrase = str(item).strip()
        if phrase:
            result.append(phrase)
    return result[:20]


def _build_synthesized_style_document(project_root: Path, novel_id: str, style_id: str) -> str:
    style_dir = project_root / "data" / "novels" / novel_id / "data" / "style"
    fingerprint_path = style_dir / "fingerprint.yaml"
    try:
        fingerprint = yaml.safe_load(fingerprint_path.read_text(encoding="utf-8")) or {}
    except Exception:
        fingerprint = {}

    reference_snippets = _load_reference_style_snippets(project_root, style_id)
    craft_rules = _extract_craft_headings(project_root)
    banned_phrases = _load_banned_phrases(project_root)

    parts = [
        f"# 最终风格文档：{novel_id}",
        "",
        f"> 合成时间：{datetime.now().date().isoformat()}",
        f"> 参考风格：{style_id or '无'}",
        "> 来源：作品风格指纹 + craft/ + 参考风格摘录",
        "",
        "## 作品风格指纹",
        f"- 叙述声音：{str(fingerprint.get('voice', '待定义')).strip() or '待定义'}",
        f"- 语言风格：{str(fingerprint.get('language_style', '待定义')).strip() or '待定义'}",
        f"- 节奏控制：{str(fingerprint.get('rhythm', '待定义')).strip() or '待定义'}",
    ]

    if reference_snippets:
        parts.extend(["", "## 参考风格摘录"])
        label_map = {
            "summary": "摘要",
            "voice": "叙述声音",
            "language": "语言风格",
            "rhythm": "节奏控制",
            "dialogue": "对话风格",
            "consistency": "一致性要求",
        }
        for key, label in label_map.items():
            text = reference_snippets.get(key, "")
            if text:
                parts.extend(["", f"### {label}", text])

    if craft_rules:
        parts.extend(["", "## 通用技法"])
        parts.extend(f"- {rule}" for rule in craft_rules)

    if banned_phrases:
        parts.extend(["", "## 禁用"])
        parts.extend(f"- {phrase}" for phrase in banned_phrases)

    return "\n".join(parts).strip() + "\n"


def _collect_sync_status(project_root: Path, novel_id: str) -> dict:
    """收集 src/data 同步状态。"""
    return _shared_collect_sync_status(project_root, novel_id)


def _print_sync_status(status: dict) -> None:
    logger.info(f"同步检查: {status['novel_id']}")
    logger.info(f"  大纲同步待处理: {'是' if status['outline_pending'] else '否'}")
    logger.info(f"  角色档案/卡片: {status['profiles']}/{status['cards']}")
    if status["missing_cards"]:
        logger.info(f"  缺失卡片: {', '.join(status['missing_cards'])}")
    if status.get("stale_cards"):
        logger.info(f"  过期卡片: {', '.join(status['stale_cards'])}")
    if status["extra_cards"]:
        logger.info(f"  额外卡片(可选清理): {', '.join(status['extra_cards'])}")


def _build_sync_suggestions(status: dict) -> list[str]:
    """根据同步状态生成下一步建议。"""
    messages: list[str] = []

    if status["outline_pending"]:
        messages.append("大纲源文件有更新，运行 `openwrite sync` 以刷新 data/hierarchy.yaml")

    if status["missing_cards"]:
        preview = ", ".join(status["missing_cards"][:5])
        messages.append(
            f"存在缺失角色卡片（{preview}），运行 `openwrite sync` 生成 data/characters/cards/*.yaml"
        )

    if status.get("stale_cards"):
        preview = ", ".join(status["stale_cards"][:5])
        messages.append(
            f"存在过期角色卡片（{preview}），运行 `openwrite sync` 刷新 data/characters/cards/*.yaml"
        )

    if status["extra_cards"]:
        preview = ", ".join(status["extra_cards"][:5])
        messages.append(f"检测到未对应的历史角色卡片（{preview}），可按需手工清理")

    if not messages:
        messages.append("src 与 data 同步状态良好，可直接继续写作")

    return messages


def _build_sync_actions(status: dict) -> list[dict[str, str]]:
    """根据同步状态生成可执行动作列表（供 JSON 输出）。"""
    actions: list[dict[str, str]] = []

    if status["outline_pending"] or status["missing_cards"] or status.get("stale_cards"):
        actions.append(
            {
                "type": "command",
                "name": "run_sync",
                "command": "openwrite sync",
                "reason": "将 src 的 outline/characters 同步到 data",
            }
        )

    if status["extra_cards"]:
        actions.append(
            {
                "type": "manual",
                "name": "review_extra_cards",
                "reason": "存在未对应档案的历史卡片，按需清理 data/characters/cards/*.yaml",
            }
        )

    if not actions:
        actions.append(
            {
                "type": "noop",
                "name": "continue_writing",
                "reason": "src 与 data 已同步，可直接继续写作流程",
            }
        )

    return actions


def _run_sync(project_root: Path, novel_id: str) -> None:
    """执行 src -> data 同步。"""
    _shared_run_sync(project_root, novel_id)


def _exec_create_foreshadowing(project_root: Path, args: dict) -> dict:
    """执行 create_foreshadowing"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.foreshadowing_manager import ForeshadowingDAGManager

    novel_id = config.get("novel_id", "")
    node_id = args.get("node_id", "")
    content = args.get("content", "")
    weight = args.get("weight", 5)
    layer = args.get("layer", "支线")
    created_at = args.get("created_at", "")
    target_chapter = args.get("target_chapter", "")

    manager = ForeshadowingDAGManager(project_root, novel_id)
    success = manager.create_node(
        node_id=node_id,
        content=content,
        weight=weight,
        layer=layer,
        created_at=created_at,
        target_chapter=target_chapter if target_chapter else None,
    )

    if success:
        return {"node_id": node_id, "status": "created", "content": content}
    else:
        return {"error": f"伏笔节点已存在: {node_id}"}


def _exec_list_foreshadowing(project_root: Path, args: dict) -> dict:
    """执行 list_foreshadowing"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.foreshadowing_manager import ForeshadowingDAGManager

    novel_id = config.get("novel_id", "")
    status_filter = args.get("status")
    min_weight = args.get("min_weight", 1)
    layer = args.get("layer")

    manager = ForeshadowingDAGManager(project_root, novel_id)

    if status_filter:
        nodes = []
        dag = manager._load_dag()
        for node_id, node in dag.nodes.items():
            if dag.status.get(node_id) == status_filter:
                if layer is None or node.layer == layer:
                    if node.weight >= min_weight:
                        nodes.append(
                            {
                                "id": node.id,
                                "content": node.content,
                                "weight": node.weight,
                                "layer": node.layer,
                                "status": node.status,
                                "created_at": node.created_at,
                                "target_chapter": node.target_chapter,
                            }
                        )
    else:
        pending = manager.get_pending_nodes(min_weight=min_weight, layer=layer)
        nodes = [
            {
                "id": n.id,
                "content": n.content,
                "weight": n.weight,
                "layer": n.layer,
                "status": n.status,
                "created_at": n.created_at,
                "target_chapter": n.target_chapter,
            }
            for n in pending
        ]

    stats = manager.get_statistics()

    return {
        "nodes": nodes,
        "total": stats["total"],
        "by_status": stats["by_status"],
        "by_layer": stats["by_layer"],
    }


def _exec_update_foreshadowing(project_root: Path, args: dict) -> dict:
    """执行 update_foreshadowing"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.foreshadowing_manager import ForeshadowingDAGManager

    novel_id = config.get("novel_id", "")
    node_id = args.get("node_id", "")
    new_status = args.get("status", "")

    manager = ForeshadowingDAGManager(project_root, novel_id)
    success = manager.update_node_status(node_id, new_status)

    if success:
        return {"node_id": node_id, "status": new_status}
    else:
        return {"error": f"伏笔节点不存在: {node_id}"}


def _exec_validate_foreshadowing(project_root: Path, args: dict) -> dict:
    """执行 validate_foreshadowing"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.foreshadowing_manager import ForeshadowingDAGManager

    novel_id = config.get("novel_id", "")
    manager = ForeshadowingDAGManager(project_root, novel_id)

    is_valid, errors = manager.validate_dag()

    return {
        "valid": is_valid,
        "errors": errors,
    }


def _load_config(project_root: Path) -> Optional[dict]:
    """加载项目配置"""
    config_path = project_root / "novel_config.yaml"
    if not config_path.exists():
        return None

    import yaml

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_test_output_dir(project_root: Path, novel_id: str, category: str) -> Path:
    """获取测试输出目录。"""
    return project_root / "data" / "novels" / novel_id / "data" / "test_outputs" / category


def _count_written_chapters(project_root: Path, novel_id: str) -> int:
    """统计当前布局下的最终章节数。"""
    return len(_iter_final_chapter_paths(project_root, novel_id))


def _iter_final_chapter_paths(project_root: Path, novel_id: str) -> list[Path]:
    """列出当前篇下的最终章节文件，忽略 draft。"""
    manuscript_dir = _manuscript_dir(project_root, novel_id) / _get_current_arc(project_root)
    if not manuscript_dir.exists():
        return []

    chapter_pattern = re.compile(r"^ch_\d+\.md$")
    return sorted(
        path
        for path in manuscript_dir.rglob("*.md")
        if path.is_file() and chapter_pattern.fullmatch(path.name)
    )


def _get_current_arc(project_root: Path) -> str:
    """读取当前篇章目录，默认回退到 arc_001。"""
    config = _load_config(project_root) or {}
    return config.get("current_arc") or "arc_001"


def _manuscript_dir(project_root: Path, novel_id: str) -> Path:
    """获取当前支持的手稿根目录。"""
    return project_root / "data" / "novels" / novel_id / "data" / "manuscript"


def _load_chapter(project_root: Path, novel_id: str, chapter_id: str) -> Optional[str]:
    """加载章节内容"""
    manuscript_dir = _manuscript_dir(project_root, novel_id)
    current_arc = _get_current_arc(project_root)

    current_path = manuscript_dir / current_arc / f"{chapter_id}.md"
    if current_path.is_file():
        return current_path.read_text(encoding="utf-8")

    patterns = [
        f"**/{chapter_id}.md",
        f"**/{chapter_id}_*.md",
    ]

    for pattern in patterns:
        matches = list(manuscript_dir.glob(pattern))
        if matches:
            return matches[0].read_text(encoding="utf-8")

    return None


def _save_chapter(
    project_root: Path,
    novel_id: str,
    chapter_id: str,
    title: str,
    content: str,
) -> Path:
    """保存章节"""
    config = _load_config(project_root) or {}
    current_arc = config.get("current_arc", "arc_001")

    manuscript_dir = (
        project_root
        / "data"
        / "novels"
        / novel_id
        / "data"
        / "manuscript"
        / current_arc
    )
    manuscript_dir.mkdir(parents=True, exist_ok=True)

    file_path = manuscript_dir / f"{chapter_id}.md"
    file_path.write_text(f"# {title}\n\n{content}", encoding="utf-8")

    return file_path


def _get_next_chapter(project_root: Path, novel_id: str) -> str:
    """获取下一个章节 ID"""
    chapter_ids = _list_chapter_ids(project_root, novel_id)
    if not chapter_ids:
        return "ch_001"
    latest = max(_parse_chapter_no(chid) for chid in chapter_ids)
    return f"ch_{latest + 1:03d}"


def _get_latest_chapter(project_root: Path, novel_id: str) -> str:
    """获取最新章节"""
    chapter_ids = _list_chapter_ids(project_root, novel_id)
    if not chapter_ids:
        return "ch_001"
    latest_id = max(chapter_ids, key=_parse_chapter_no)
    return latest_id


def _list_chapter_ids(project_root: Path, novel_id: str) -> list[str]:
    """从手稿目录扫描章节 ID。"""
    manuscript_root = project_root / "data" / "novels" / novel_id / "data" / "manuscript"
    if not manuscript_root.exists():
        return []

    chapter_ids: set[str] = set()
    for path in manuscript_root.glob("**/ch_*.md"):
        stem = path.stem
        if re.match(r"^ch_\d+$", stem):
            chapter_ids.add(stem)
    return sorted(chapter_ids, key=_parse_chapter_no)


def _parse_chapter_no(chapter_id: str) -> int:
    m = re.search(r"(\d+)", chapter_id)
    return int(m.group(1)) if m else 0


# ── 世界查询 ────────────────────────────────────────────────


def _exec_query_world(project_root: Path, args: dict) -> dict:
    """执行 query_world"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.world_query import list_entities, get_entity

    novel_id = config.get("novel_id", "")
    entity_id = args.get("entity_id")
    entity_type = args.get("type")

    if entity_id:
        entity = get_entity(novel_id, entity_id, project_root)
        if entity:
            return {
                "entity": {
                    "id": entity["id"],
                    "name": entity["name"],
                    "type": entity["type"],
                    "subtype": entity["subtype"],
                    "status": entity["status"],
                    "description": entity["description"][:200] if entity["description"] else "",
                    "rules": entity["rules"][:5] if entity["rules"] else [],
                    "relations": entity["relations"][:10] if entity["relations"] else [],
                }
            }
        return {"error": f"实体不存在: {entity_id}"}

    entities = list_entities(novel_id, entity_type=entity_type, project_root=project_root)
    return {
        "entities": entities,
        "count": len(entities),
    }


def _exec_get_world_relations(project_root: Path, args: dict) -> dict:
    """执行 get_world_relations"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.world_query import get_relations_graph

    novel_id = config.get("novel_id", "")
    graph = get_relations_graph(novel_id, project_root)

    return {
        "entities": graph["entities"],
        "relations": graph["relations"][:50],
        "total_entities": len(graph["entities"]),
        "total_relations": len(graph["relations"]),
    }


# ── 状态验证 ────────────────────────────────────────────────


def _exec_validate_truth(project_root: Path, args: dict) -> dict:
    """执行 validate_truth"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.truth_manager import TruthFilesManager
    from tools.state_validator import StateValidator

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "latest")

    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    chapter_content = _load_chapter(project_root, novel_id, chapter_id) or ""

    import re

    chapter_num = 1
    match = re.search(r"ch_(\d+)", chapter_id)
    if match:
        chapter_num = int(match.group(1))

    validator = StateValidator()
    issues = validator.validate(
        current_state=truth.current_state,
        content=chapter_content,
        chapter_number=chapter_num,
    )

    return {
        "chapter_id": chapter_id,
        "issues": [
            {
                "severity": i.severity,
                "category": i.category,
                "description": i.description,
            }
            for i in issues
        ],
        "issue_count": len(issues),
        "critical_count": sum(1 for i in issues if i.severity == "critical"),
    }


# ── 对话质量 ────────────────────────────────────────────────


def _exec_extract_dialogue_fingerprint(project_root: Path, args: dict) -> dict:
    """执行 extract_dialogue_fingerprint"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.dialogue_fingerprint import DialogueFingerprintExtractor

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "latest")
    character_names = args.get("character_names", [])

    content = _load_chapter(project_root, novel_id, chapter_id)
    if not content:
        return {"error": f"未找到章节: {chapter_id}"}

    extractor = DialogueFingerprintExtractor()
    fingerprints = extractor.extract(
        [content], character_names=character_names if character_names else None
    )

    return {
        "chapter_id": chapter_id,
        "fingerprints": [
            {
                "character": fp.character_name,
                "avg_sentence_length": fp.avg_sentence_length,
                "common_bigrams": fp.common_bigrams[:5],
                "question_ratio": fp.question_ratio,
                "speech_patterns": fp.speech_patterns[:5],
                "summary": fp.to_prompt_text(),
            }
            for fp in fingerprints
        ],
    }


# ── 后置验证 ────────────────────────────────────────────────


def _exec_validate_post_write(project_root: Path, args: dict) -> dict:
    """执行 validate_post_write"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.post_validator import PostWriteValidator

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "latest")

    content = _load_chapter(project_root, novel_id, chapter_id)
    if not content:
        return {"error": f"未找到章节: {chapter_id}"}

    validator = PostWriteValidator()
    violations = validator.validate(content)

    return {
        "chapter_id": chapter_id,
        "violations": [
            {
                "severity": v.severity,
                "rule": v.rule,
                "description": v.description,
                "location": v.location,
            }
            for v in violations
        ],
        "error_count": sum(1 for v in violations if v.severity == "error"),
        "warning_count": sum(1 for v in violations if v.severity == "warning"),
        "passed": len(violations) == 0,
    }


if __name__ == "__main__":
    sys.exit(main())


# ── 工作流调度 ────────────────────────────────────────────────


def _exec_get_workflow_status(project_root: Path, args: dict) -> dict:
    """执行 get_workflow_status"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.workflow_scheduler import WorkflowScheduler

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id")

    scheduler = WorkflowScheduler(project_root, novel_id)

    if chapter_id:
        state = scheduler.load_workflow(chapter_id)
        if state:
            return {
                "chapter_id": state.chapter_id,
                "current_stage": state.current_stage,
                "stages": {s.name: s.to_dict() for s in state.stage_records},
                "is_complete": scheduler.is_complete(state),
            }
        return {"error": f"未找到工作流: {chapter_id}"}

    active = scheduler.list_active()
    complete = scheduler.list_complete()

    return {
        "active": active,
        "complete": complete,
        "active_count": len(active),
    }


def _exec_start_workflow(project_root: Path, args: dict) -> dict:
    """执行 start_workflow"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.workflow_scheduler import WorkflowScheduler

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "")

    scheduler = WorkflowScheduler(project_root, novel_id)
    state = scheduler.create_workflow(chapter_id)

    return {
        "chapter_id": state.chapter_id,
        "current_stage": state.current_stage,
        "message": f"工作流已创建: {chapter_id}",
    }


def _exec_advance_workflow(project_root: Path, args: dict) -> dict:
    """执行 advance_workflow"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.workflow_scheduler import WorkflowScheduler

    novel_id = config.get("novel_id", "")
    chapter_id = args.get("chapter_id", "")
    stage_name = args.get("stage_name", "")

    scheduler = WorkflowScheduler(project_root, novel_id)
    state = scheduler.load_workflow(chapter_id)

    if not state:
        return {"error": f"未找到工作流: {chapter_id}"}

    if stage_name:
        scheduler.advance_to(state, stage_name)
    else:
        scheduler.advance(state)

    scheduler.save_workflow(state)

    return {
        "chapter_id": state.chapter_id,
        "current_stage": state.current_stage,
        "message": f"已推进到: {state.current_stage}",
    }


# ── 文本处理 ────────────────────────────────────────────────


def _exec_chunk_text(project_root: Path, args: dict) -> dict:
    """执行 chunk_text"""
    from tools.text_chunker import TextChunker

    file_path = args.get("file_path", "")
    chunk_size = args.get("chunk_size", 30000)

    path = Path(file_path)
    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}

    chunker = TextChunker(chunk_size=chunk_size)

    if path.is_file():
        result = chunker.chunk_file(path)
        chunks = [
            {
                "index": c.index,
                "chapter_range": c.chapter_range,
                "char_count": c.char_count,
            }
            for c in result.chunks
        ]
        return {
            "file": str(path),
            "total_chunks": len(chunks),
            "chunks": chunks,
        }

    return {"error": "不支持的路径类型"}


def _exec_compress_section(project_root: Path, args: dict) -> dict:
    """执行 compress_section"""
    from tools.progressive_compressor import ProgressiveCompressor

    novel_id = args.get("novel_id", "")

    compressor = ProgressiveCompressor(project_root, novel_id)

    arc_id = args.get("arc_id", "arc_001")
    section_id = args.get("section_id", "")

    if section_id:
        result = compressor.compress_section(arc_id, section_id)
        return {
            "arc_id": arc_id,
            "section_id": section_id,
            "compressed": result.compressed_text[:500] if result.compressed_text else "",
            "compression_ratio": result.compression_ratio,
        }

    arc_result = compressor.compress_arc(arc_id)
    return {
        "arc_id": arc_id,
        "compressed": arc_result.compressed_text[:500] if arc_result.compressed_text else "",
        "compression_ratio": arc_result.compression_ratio,
    }


if __name__ == "__main__":
    sys.exit(main())
