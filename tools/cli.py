"""OpenWrite CLI - 命令行接口

用法:
    openwrite init <novel_id>     # 初始化项目
    openwrite write <chapter>     # 写章节
    openwrite review <chapter>    # 审查章节
    openwrite context <chapter>   # 构建上下文
    openwrite style extract       # 提取风格
    openwrite status             # 查看状态
    openwrite --help            # 显示帮助
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

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
    _add_wizard_command(subparsers)
    _add_write_command(subparsers)
    _add_review_command(subparsers)
    _add_context_command(subparsers)
    _add_style_command(subparsers)
    _add_radar_command(subparsers)
    _add_status_command(subparsers)
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
    elif args.command == "write":
        return _cmd_write(args)
    elif args.command == "review":
        return _cmd_review(args)
    elif args.command == "context":
        return _cmd_context(args)
    elif args.command == "style":
        return _cmd_style(args)
    elif args.command == "radar":
        return _cmd_radar(args)
    elif args.command == "wizard":
        return _cmd_wizard(args)
    elif args.command == "status":
        return _cmd_status(args)
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


def _add_wizard_command(subparsers):
    """wizard 命令 - 交互式引导"""
    p = subparsers.add_parser("wizard", help="交互式引导（推荐新手使用）")
    p.add_argument("--novel-id", help="小说 ID（可选）")


def _add_write_command(subparsers):
    """write 命令"""
    p = subparsers.add_parser("write", help="写章节")
    p.add_argument("chapter", nargs="?", default="next", help="章节 ID 或 'next'")
    p.add_argument("--no-review", action="store_true", help="跳过审查")
    p.add_argument("--temperature", "-T", type=float, default=0.7, help="写作温度")


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


def _add_agent_command(subparsers):
    """agent 命令 - 使用内置 Agent"""
    p = subparsers.add_parser("agent", help="使用 ReAct Agent（自然语言交互）")
    p.add_argument("instruction", nargs="?", default="查看项目状态", help="自然语言指令")
    p.add_argument("--max-turns", type=int, default=20, help="最大循环次数")
    p.add_argument("--quiet", action="store_true", help="静默模式")


def _cmd_init(args) -> int:
    """初始化项目"""
    from tools.init_project import init_project

    novel_id = args.novel_id
    project_root = Path.cwd()

    logger.info(f"初始化项目: {novel_id}")
    result = init_project(project_root, novel_id, template=args.template)

    if result["success"]:
        logger.info(f"项目已创建: {result['project_path']}")
        logger.info(f"请编辑 {result['project_path'] / 'novel_config.yaml'}")
        return 0
    else:
        logger.error(f"初始化失败: {result.get('error')}")
        return 1


def _cmd_write(args) -> int:
    """写章节"""
    import asyncio

    from tools.context_builder import ContextBuilder
    from tools.truth_manager import TruthFilesManager

    project_root = Path.cwd()
    config = _load_config(project_root)
    if not config:
        logger.error("未找到 novel_config.yaml，请先运行 openwrite init")
        return 1

    novel_id = config.get("novel_id", "unknown")
    chapter = args.chapter

    if chapter == "next":
        chapter = _get_next_chapter(project_root, novel_id)

    logger.info(f"写章节: {chapter}")

    async def do_write():
        builder = ContextBuilder(project_root, novel_id)
        context = builder.build_generation_context(chapter, window_size=5)

        ctx_dict = {
            "target_words": context.target_words,
            "chapter_goals": context.chapter_goals,
            "current_state": context.current_state,
            "pending_hooks": context.pending_hooks,
            "particle_ledger": context.particle_ledger,
            "chapter_summaries": context.chapter_summaries,
        }

        try:
            from tools.llm import LLMClient, LLMConfig
            from tools.agent import WriterAgent, AgentContext

            llm_config = LLMConfig.from_env()
            client = LLMClient(llm_config)
            agent_ctx = AgentContext(client, llm_config.model, str(project_root))

            writer = WriterAgent(agent_ctx)

            chapter_num = int(chapter.split("_")[-1]) if "_" in chapter else 1
            result = await writer.write_chapter(
                context=ctx_dict,
                chapter_number=chapter_num,
                temperature=args.temperature,
            )

            logger.info(f"章节已生成: {result.title}")
            logger.info(f"字数: {result.word_count}")

            truth_manager = TruthFilesManager(project_root, novel_id)
            truth_manager.create_snapshot(chapter_num - 1)

            _save_chapter(project_root, novel_id, chapter, result.title, result.content)

            truth_manager.update_truth_files(
                truth_manager.load_truth_files(),
                {
                    "chapter_summary": f"\n\n## 第{chapter_num}章 {result.title}\n\n{result.chapter_summary}"
                },
            )

            logger.info("真相文件已更新")
            return 0

        except ImportError as e:
            logger.warning(f"LLM 模块未安装或配置: {e}")
            logger.info("提示: 设置环境变量 LLM_API_KEY, LLM_MODEL 等")
            logger.info("上下文已构建，可通过 openwrite context --show 查看")
            if args.show:
                print(context.to_prompt_context())
            return 0

    return asyncio.run(do_write())


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

    async def do_review():
        try:
            from tools.llm import LLMClient, LLMConfig
            from tools.agent import ReviewerAgent, AgentContext

            llm_config = LLMConfig.from_env()
            client = LLMClient(llm_config)
            agent_ctx = AgentContext(client, llm_config.model, str(project_root))

            reviewer = ReviewerAgent(agent_ctx)
            result = await reviewer.review(content=content, context={})

            logger.info(f"审查结果: {'通过' if result.passed else '未通过'}")
            logger.info(f"得分: {result.score:.0f}/100")
            logger.info(f"问题数: {len(result.issues)}")

            for issue in result.issues[:10]:
                logger.info(f"  [{issue.severity}] {issue.category}: {issue.description}")

            return 0

        except ImportError as e:
            logger.warning(f"LLM 模块未安装: {e}")
            return 1

    return asyncio.run(do_review())


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


def _cmd_style(args) -> int:
    """风格管理"""
    if args.style_action == "extract":
        return _cmd_style_extract(args)
    elif args.style_action == "synthesize":
        logger.info("合成风格")
        return 0
    else:
        logger.error("请指定 style 子命令: extract, synthesize")
        return 1


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


def _cmd_wizard(args) -> int:
    """交互式引导"""
    from tools.wizard import run_wizard

    return run_wizard()


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
    from tools.truth_manager import TruthFilesManager

    project_root = Path.cwd()
    config = _load_config(project_root)

    if not config:
        logger.error("未找到 novel_config.yaml")
        return 1

    novel_id = config.get("novel_id", "unknown")
    logger.info(f"项目: {novel_id}")
    logger.info(f"当前篇: {config.get('current_arc', 'N/A')}")
    logger.info(f"当前章: {config.get('current_chapter', 'N/A')}")

    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    summary_lines = truth.chapter_summaries.count("## 第")
    logger.info(f"已写章节: {summary_lines}")

    snapshots = truth_manager.list_snapshots()
    logger.info(f"快照数: {len(snapshots)}")

    return 0


def _cmd_agent(args) -> int:
    """使用 ReAct Agent"""
    import asyncio

    project_root = Path.cwd()

    async def do_agent():
        try:
            from tools.llm import LLMClient, LLMConfig
            from tools.agent import ReActAgent, OPENWRITE_TOOLS, OPENWRITE_SYSTEM_PROMPT

            llm_config = LLMConfig.from_env()
            client = LLMClient(llm_config)

            agent = ReActAgent(
                client=client,
                model=llm_config.model,
                tools=OPENWRITE_TOOLS,
                system_prompt=OPENWRITE_SYSTEM_PROMPT,
                max_turns=args.max_turns,
            )

            # 注册工具执行器
            agent._register_tool_executors(
                {
                    "write_chapter": lambda a: _exec_write_chapter(project_root, a),
                    "review_chapter": lambda a: _exec_review_chapter(project_root, a),
                    "get_status": lambda a: _exec_get_status(project_root),
                    "get_context": lambda a: _exec_get_context(project_root, a),
                    "list_chapters": lambda a: _exec_list_chapters(project_root),
                    "create_outline": lambda a: _exec_create_outline(project_root, a),
                    "create_character": lambda a: _exec_create_character(project_root, a),
                    "get_truth_files": lambda a: _exec_get_truth_files(project_root),
                    "update_truth_file": lambda a: _exec_update_truth_file(project_root, a),
                }
            )

            def on_tool_call(name: str, args_: dict):
                if not args.quiet:
                    print(f"  [tool] {name}({args_})")

            def on_tool_result(name: str, result: str):
                if not args.quiet:
                    preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"  [result] {preview}")

            def on_message(content: str):
                print(f"\n{content}\n")

            result = await agent.run(
                instruction=args.instruction,
                on_tool_call=on_tool_call if not args.quiet else None,
                on_tool_result=on_tool_result if not args.quiet else None,
                on_message=on_message,
            )

            return 0

        except ImportError as e:
            logger.error(f"LLM 模块未安装: {e}")
            logger.info("设置环境变量: LLM_API_KEY, LLM_MODEL")
            return 1
        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            return 1

    return asyncio.run(do_agent())


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

    builder = ContextBuilder(project_root, novel_id)
    context = builder.build_generation_context(chapter_id)

    try:
        llm_config = LLMConfig.from_env()
        client = LLMClient(llm_config)
        agent_ctx = AgentContext(client, llm_config.model, str(project_root))

        chapter_num = int(chapter_id.split("_")[-1]) if "_" in chapter_id else 1
        writer = WriterAgent(agent_ctx)

        result = asyncio.run(
            writer.write_chapter(
                context={
                    "target_words": context.target_words,
                    "chapter_goals": context.chapter_goals,
                    "current_state": context.current_state,
                    "pending_hooks": context.pending_hooks,
                },
                chapter_number=chapter_num,
            )
        )

        _save_chapter(project_root, novel_id, chapter_id, result.title, result.content)

        return {
            "chapter_id": chapter_id,
            "title": result.title,
            "word_count": result.word_count,
        }
    except Exception as e:
        return {"error": str(e)}


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
        result = asyncio.run(reviewer.review(content=content, context={}))

        return {
            "chapter_id": chapter_id,
            "passed": result.passed,
            "score": result.score,
            "issues": len(result.issues),
        }
    except Exception as e:
        return {"error": str(e)}


def _exec_get_status(project_root: Path) -> dict:
    """执行 get_status"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    novel_id = config.get("novel_id", "")

    from tools.truth_manager import TruthFilesManager

    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    summary_lines = truth.chapter_summaries.count("## 第")
    snapshots = truth_manager.list_snapshots()

    return {
        "novel_id": novel_id,
        "current_arc": config.get("current_arc"),
        "current_chapter": config.get("current_chapter"),
        "chapters_written": summary_lines,
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

    from tools.truth_manager import TruthFilesManager

    novel_id = config.get("novel_id", "")
    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    import re

    chapters = re.findall(r"## 第(\d+)章\s+(.+)", truth.chapter_summaries)

    return {
        "chapters": [{"number": n, "title": t} for n, t in chapters],
    }


def _exec_create_outline(project_root: Path, args: dict) -> dict:
    """执行 create_outline"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    novel_id = config.get("novel_id", "")
    content = args.get("outline_content", "")

    outline_dir = project_root / "data" / "novels" / novel_id / "outline"
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

    char_dir = project_root / "data" / "novels" / novel_id / "characters" / "profiles"
    char_dir.mkdir(parents=True, exist_ok=True)

    char_file = char_dir / f"{name}.md"
    char_file.write_text(f"# {name}\n\n{description}", encoding="utf-8")

    return {"file": str(char_file), "name": name}


def _exec_get_truth_files(project_root: Path) -> dict:
    """执行 get_truth_files"""
    config = _load_config(project_root)
    if not config:
        return {"error": "未找到项目配置"}

    from tools.truth_manager import TruthFilesManager

    novel_id = config.get("novel_id", "")
    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    return {
        "current_state": truth.current_state[:500] if truth.current_state else "",
        "pending_hooks": truth.pending_hooks[:500] if truth.pending_hooks else "",
        "chapter_summaries": truth.chapter_summaries[:500] if truth.chapter_summaries else "",
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

    file_map = {
        "current_state": "current_state",
        "pending_hooks": "pending_hooks",
        "particle_ledger": "particle_ledger",
        "chapter_summaries": "chapter_summaries",
    }

    attr = file_map.get(file_name)
    if not attr:
        return {"error": f"Unknown file: {file_name}"}

    setattr(truth, attr, content)
    truth_manager.save_truth_files(truth)

    return {"file": file_name, "size": len(content)}


def _load_config(project_root: Path) -> Optional[dict]:
    """加载项目配置"""
    config_path = project_root / "novel_config.yaml"
    if not config_path.exists():
        return None

    import yaml

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_chapter(project_root: Path, novel_id: str, chapter_id: str) -> Optional[str]:
    """加载章节内容"""
    manuscript_dir = project_root / "data" / "novels" / novel_id / "manuscript"

    patterns = [
        f"{chapter_id}.md",
        f"{chapter_id}_*.md",
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
    manuscript_dir = project_root / "data" / "novels" / novel_id / "manuscript"
    manuscript_dir.mkdir(parents=True, exist_ok=True)

    file_path = manuscript_dir / f"{chapter_id}.md"
    file_path.write_text(f"# {title}\n\n{content}", encoding="utf-8")

    return file_path


def _get_next_chapter(project_root: Path, novel_id: str) -> str:
    """获取下一个章节 ID"""
    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    existing = truth.chapter_summaries.count("## 第")
    return f"ch_{existing + 1:03d}"


def _get_latest_chapter(project_root: Path, novel_id: str) -> str:
    """获取最新章节"""
    truth_manager = TruthFilesManager(project_root, novel_id)
    truth = truth_manager.load_truth_files()

    import re

    matches = re.findall(r"## 第(\d+)章", truth.chapter_summaries)
    if matches:
        latest = max(int(m) for m in matches)
        return f"ch_{latest:03d}"

    return "ch_001"


if __name__ == "__main__":
    sys.exit(main())
