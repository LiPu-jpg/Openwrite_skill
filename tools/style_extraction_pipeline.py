"""风格提取流水线 — 大文本分批提取与渐进式合并

核心流程（参考 ReadtoWrite 的 Reader + Director 双循环）：
  1. 切割阶段：用 TextChunker 将大文本切割为 chunks
  2. 阅读阶段：逐 chunk 提取风格发现（三层分类）
  3. 合并阶段：每 N 个 chunk 后合并风格文档
  4. 验证阶段：可选的"生成+差异分析"循环

支持断点续传：通过 ExtractionProgress 追踪进度。

这里管理的是“项目内 source pack”的提取运行态，而不是全局样例库。
它负责把用户提供的原始文本沉淀成：
  - 可审阅的 source / setting / style 文档
  - 可恢复的 extraction 进度与批次结果
后续 CLI 和 Goethe 都围绕这套目录继续做 review / promote。

Usage:
    pipeline = StyleExtractionPipeline(
        project_root=Path.cwd(),
        novel_id="my_novel",
        source_name="office_excerpt",
    )
    # 1. 切割
    pipeline.prepare(source_file=Path("office_excerpt.txt"))
    # 2. 获取下一批待处理的 chunk
    chunk = pipeline.next_chunk()
    # 3. AI 处理完后保存发现
    pipeline.save_batch_result(chunk_index=0, findings={...})
    # 4. 合并所有已完成的批次
    pipeline.merge_all()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.text_chunker import TextChunker, ChunkResult

import yaml


# ── 进度追踪 ─────────────────────────────────────────────────────

@dataclass
class BatchResult:
    """单批次提取结果。

    这层只记录“某个 chunk 是否已经被处理过，以及提取出了多少信号”。
    详细发现内容单独落在 batch_results/ 下，避免进度文件过重。
    """
    chunk_index: int
    chapter_range: str
    char_count: int
    status: str = "pending"         # pending | completed | skipped
    completed_at: Optional[str] = None
    # 发现分类计数
    craft_findings: int = 0         # 通用技法发现数
    author_findings: int = 0        # 作者风格发现数
    novel_findings: int = 0         # 作品设定发现数


@dataclass
class ExtractionProgress:
    """提取进度追踪。

    progress.json 是 source pack 提取流程的恢复点：
    - pipeline 重启后可以继续处理 pending 批次
    - merge 阶段可以只重新汇总已完成批次
    """
    source_file: str
    source_hash: str
    source_name: str                    # 来源 ID
    novel_id: str
    total_chunks: int
    total_chars: int
    chunk_size: int
    created_at: str = ""
    updated_at: str = ""
    current_phase: str = "chunking"     # chunking | reading | merging | done
    merge_count: int = 0                # 已合并次数
    batches: List[BatchResult] = field(default_factory=list)

    @property
    def completed_count(self) -> int:
        return sum(1 for b in self.batches if b.status == "completed")

    @property
    def pending_count(self) -> int:
        return sum(1 for b in self.batches if b.status == "pending")

    @property
    def progress_pct(self) -> float:
        if not self.batches:
            return 0.0
        return self.completed_count / len(self.batches) * 100

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["completed_count"] = self.completed_count
        d["pending_count"] = self.pending_count
        d["progress_pct"] = round(self.progress_pct, 1)
        return d

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "ExtractionProgress":
        data = json.loads(path.read_text(encoding="utf-8"))
        batches = [BatchResult(**b) for b in data.pop("batches", [])]
        # 移除计算属性
        data.pop("completed_count", None)
        data.pop("pending_count", None)
        data.pop("progress_pct", None)
        return cls(**data, batches=batches)


# ── 风格文档模板 ─────────────────────────────────────────────────

STYLE_DOC_STRUCTURE = {
    "summary.md": "# 风格总结\n\n> 整体风格概述（随阅读批次持续更新）\n\n## 核心风格要素\n\n（待填充）\n\n## 迭代记录\n\n| 批次 | 章节范围 | 主要发现 |\n|------|----------|----------|\n",
    "voice.md": "# 叙述声音 (Voice)\n\n## 叙述视角\n\n## 人称与称谓\n\n## 叙述者介入程度\n\n## 信息揭示策略\n\n## 典型示例\n\n",
    "language.md": "# 语言风格 (Language)\n\n## 用词风格\n\n## 句式特征\n\n## 修辞手法\n\n## 术语体系\n\n## 幽默与吐槽\n\n## 典型示例\n\n",
    "rhythm.md": "# 节奏风格 (Rhythm)\n\n## 段落长度分布\n\n## 场景切换方式\n\n## 紧张-松弛节奏\n\n## 章节结构\n\n## 典型示例\n\n",
    "dialogue.md": "# 对话风格 (Dialogue)\n\n## 对话格式\n\n## 对话占比\n\n## 角色声音区分\n\n## 潜台词使用\n\n## 典型示例\n\n",
    "scene_templates.md": "# 场景模板 (Scene Templates)\n\n## 已识别模板\n\n## 模板使用频率\n\n",
    "consistency.md": "# 一致性规则 (Consistency)\n\n## 术语规范\n\n## 角色一致性\n\n## 世界观规则\n\n## 禁忌清单\n\n",
}

SOURCE_DOC_TEMPLATES = {
    "source.md": (
        "+++\n"
        'id = "source_id"\n'
        'kind = "source"\n'
        'source_type = "user_supplied_text"\n'
        'legal = "user_provided"\n'
        'usage = "style_and_setting_reference"\n'
        'status = "extracted"\n'
        'detail_refs = ["summary", "usage_notes", "promotion_notes"]\n'
        "+++\n\n"
        "# 来源说明\n\n"
        "## summary\n\n"
        "这是一份用户主动提供的样文或设定素材，用于提取可复用的风格信号与设定线索。\n\n"
        "## usage_notes\n\n"
        "- 只提取可复用的写法、节奏、叙述距离和设定组织方式。\n"
        "- 不应直接照搬原文专名、标志性桥段或具明显来源识别度的表达。\n\n"
        "## promotion_notes\n\n"
        "- 可复用的内容可晋升到项目内的风格或设定文档。\n"
        "- 绑定原来源的专有内容只保留为灵感记录，不直接进入 canonical 文档。\n"
    ),
    "setting_profile.md": (
        "+++\n"
        'id = "source_id"\n'
        'kind = "setting_profile"\n'
        'status = "extracted"\n'
        'detail_refs = ["premise", "rules", "factions", "characters", "timeline", "promotion_notes"]\n'
        "+++\n\n"
        "# 设定提要\n\n"
        "## premise\n\n（待提取）\n\n"
        "## rules\n\n（待提取）\n\n"
        "## factions\n\n（待提取）\n\n"
        "## characters\n\n（待提取）\n\n"
        "## timeline\n\n（待提取）\n\n"
        "## promotion_notes\n\n"
        "- 哪些世界规则可以抽象复用。\n"
        "- 哪些专有名词、人物、地点只能作为灵感参考。\n"
    ),
}


class StyleExtractionPipeline:
    """风格提取流水线

    管理从大文本中分批提取风格的完整流程。

    目录结构：
        data/novels/{novel_id}/data/
          sources/{source_name}/
            source.md
            setting_profile.md
            style/
              summary.md
              voice.md
              language.md
              ...
            extraction/
              progress.json
              chunks/
              batch_results/
    """

    # 每 N 个批次后触发一次合并
    MERGE_INTERVAL = 3

    def __init__(
        self,
        project_root: Path,
        novel_id: str,
        source_name: str,
        chunk_size: int = 30000,
    ):
        self.project_root = project_root.resolve()
        self.novel_id = novel_id
        self.source_name = source_name
        self.chunk_size = chunk_size

        # 路径
        self.novel_dir = project_root / "data" / "novels" / novel_id
        self.data_dir = self.novel_dir / "data"
        self.source_dir = self.data_dir / "sources" / source_name
        self.extraction_dir = self.source_dir / "extraction"
        self.chunks_dir = self.extraction_dir / "chunks"
        self.batch_results_dir = self.extraction_dir / "batch_results"
        self.style_dir = self.source_dir / "style"

        # 进度
        self._progress: Optional[ExtractionProgress] = None

    @property
    def progress_path(self) -> Path:
        return self.extraction_dir / "progress.json"

    @property
    def progress(self) -> Optional[ExtractionProgress]:
        if self._progress is None and self.progress_path.exists():
            self._progress = ExtractionProgress.load(self.progress_path)
        return self._progress

    # ── 阶段 1: 准备（切割） ──────────────────────────────────────

    def prepare(
        self,
        source_file: Optional[Path] = None,
        source_text: Optional[str] = None,
        encoding: str = "utf-8",
    ) -> ExtractionProgress:
        """准备阶段：切割文本、初始化目录、创建进度文件

        Args:
            source_file: 源 .txt 文件（与 source_text 二选一）
            source_text: 直接提供文本（与 source_file 二选一）
            encoding: 文件编码

        Returns:
            ExtractionProgress 进度对象
        """
        chunker = TextChunker(chunk_size=self.chunk_size)

        if source_file:
            result = chunker.chunk_file(Path(source_file), encoding)
            source_desc = str(source_file)
        elif source_text:
            result = chunker.chunk_text(source_text, self.source_name)
            source_desc = f"inline:{self.source_name}"
        else:
            raise ValueError("必须提供 source_file 或 source_text")

        # 先把原始文本切成稳定 chunk，后续批次处理和断点恢复都围绕这些 chunk 进行。
        chunker.save_chunks(result, self.chunks_dir)

        # 初始化 source pack 的可读文档骨架，确保 review/promotion 可以在提取完成前介入。
        self._init_style_dirs()

        # progress.json 只保存运行态和批次状态，不复制整段原文。
        now = datetime.now().isoformat()
        progress = ExtractionProgress(
            source_file=source_desc,
            source_hash=result.source_hash,
            source_name=self.source_name,
            novel_id=self.novel_id,
            total_chunks=result.total_chunks,
            total_chars=result.total_chars,
            chunk_size=self.chunk_size,
            created_at=now,
            updated_at=now,
            current_phase="reading",
            batches=[
                BatchResult(
                    chunk_index=c.index,
                    chapter_range=c.chapter_range,
                    char_count=c.char_count,
                )
                for c in result.chunks
            ],
        )
        progress.save(self.progress_path)
        self._progress = progress

        return progress

    def _init_style_dirs(self):
        """初始化风格文档目录结构。

        模板文件只在首次创建时落盘，避免后续批次覆盖人工审阅过的内容。
        """
        for d in [self.source_dir, self.style_dir]:
            d.mkdir(parents=True, exist_ok=True)

        for filename, template in SOURCE_DOC_TEMPLATES.items():
            path = self.source_dir / filename
            if not path.exists():
                path.write_text(template, encoding="utf-8")

        for filename, template in STYLE_DOC_STRUCTURE.items():
            path = self.style_dir / filename
            if not path.exists():
                path.write_text(template, encoding="utf-8")

        # 创建批次结果目录
        self.batch_results_dir.mkdir(parents=True, exist_ok=True)

    # ── 阶段 2: 阅读提取 ─────────────────────────────────────────

    def next_chunk(self) -> Optional[Dict]:
        """获取下一个待处理的分块

        Returns:
            {
                "chunk_index": int,
                "chapter_range": str,
                "char_count": int,
                "text": str,
                "total_chunks": int,
                "completed_count": int,
                "existing_style_docs": {filename: content},  # 当前风格文档
            }
            所有批次都已完成则返回 None
        """
        progress = self.progress
        if progress is None:
            raise RuntimeError("需要先调用 prepare() 初始化")

        # Goethe/CLI 每次只消费一个 pending 批次，保持提取循环可以随时暂停和恢复。
        for batch in progress.batches:
            if batch.status == "pending":
                text = TextChunker.load_chunk(self.chunks_dir, batch.chunk_index)
                if text is None:
                    continue

                # 把当前已经合并出的 style 文档作为上下文喂回模型，形成“读一批、更新一批”的滚动提取。
                existing_docs = self._load_style_docs()

                return {
                    "chunk_index": batch.chunk_index,
                    "chapter_range": batch.chapter_range,
                    "char_count": batch.char_count,
                    "text": text,
                    "total_chunks": progress.total_chunks,
                    "completed_count": progress.completed_count,
                    "existing_style_docs": existing_docs,
                }

        return None  # 全部完成

    def _load_style_docs(self) -> Dict[str, str]:
        """加载当前所有风格文档。

        只返回已经脱离模板占位状态的文档，避免把空白骨架当成有效上下文。
        """
        docs = {}
        for filename in STYLE_DOC_STRUCTURE:
            path = self.style_dir / filename
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # 只返回有实际内容的文档（不返回空模板）
                if len(content.strip()) > len(STYLE_DOC_STRUCTURE[filename].strip()):
                    docs[filename] = content
        return docs

    def save_batch_result(
        self,
        chunk_index: int,
        findings: Dict[str, Any],
        style_updates: Optional[Dict[str, str]] = None,
    ):
        """保存单批次的提取结果

        Args:
            chunk_index: 分块索引
            findings: 原始发现（三层分类），格式：
                {
                    "craft": [...],      # 通用技法发现
                    "author": [...],     # 作者风格发现
                    "novel": [...],      # 作品设定发现
                    "summary": "...",    # 本批次摘要
                }
            style_updates: 需要更新的风格文档，格式：
                {"voice.md": "新内容", "language.md": "新内容", ...}
        """
        progress = self.progress
        if progress is None:
            raise RuntimeError("需要先调用 prepare()")

        # 原始批次发现以 batch yaml 持久化，后续 merge/review 都围绕这份中间产物工作。
        batch_path = self.batch_results_dir / f"batch_{chunk_index:03d}.yaml"
        batch_data = {
            "chunk_index": chunk_index,
            "completed_at": datetime.now().isoformat(),
            "findings": findings,
        }
        batch_path.write_text(
            yaml.dump(batch_data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )

        # 某些调用方会在单批次后先写一轮 style 文档，merge_all 再负责做全局汇总。
        if style_updates:
            for filename, content in style_updates.items():
                path = self.style_dir / filename
                path.write_text(content, encoding="utf-8")

        # progress 只记录批次级别的完成情况和统计计数，不保存大段发现正文。
        for batch in progress.batches:
            if batch.chunk_index == chunk_index:
                batch.status = "completed"
                batch.completed_at = datetime.now().isoformat()
                craft = findings.get("craft", [])
                author = findings.get("author", [])
                novel = findings.get("novel", [])
                batch.craft_findings = len(craft) if isinstance(craft, list) else 0
                batch.author_findings = len(author) if isinstance(author, list) else 0
                batch.novel_findings = len(novel) if isinstance(novel, list) else 0
                break

        progress.updated_at = datetime.now().isoformat()

        # 每隔固定批次数打一个“需要合并”的标记，调用方据此决定是否触发下一轮汇总。
        if (
            progress.completed_count > 0
            and progress.completed_count % self.MERGE_INTERVAL == 0
        ):
            progress.current_phase = "merging"

        # 所有 chunk 完成后直接把 phase 切到 done，避免外层继续请求新批次。
        if progress.pending_count == 0:
            progress.current_phase = "done"

        progress.save(self.progress_path)

    # ── 阶段 3: 合并 ─────────────────────────────────────────────

    def merge_all(self) -> Dict[str, str]:
        """合并所有已完成批次的发现到风格文档

        Returns:
            合并后的风格文档 {filename: content}
        """
        progress = self.progress
        if progress is None:
            raise RuntimeError("需要先调用 prepare()")

        # merge 不回看原始大文本，只汇总已经持久化的批次发现，保证流程可恢复且成本稳定。
        all_findings = []
        for batch in progress.batches:
            if batch.status == "completed":
                batch_path = self.batch_results_dir / f"batch_{batch.chunk_index:03d}.yaml"
                if batch_path.exists():
                    data = yaml.safe_load(batch_path.read_text(encoding="utf-8"))
                    all_findings.append(data)

        # merge 完成后恢复到 reading/done，相当于告诉外层“汇总已完成，可以继续读下一批”。
        progress.merge_count += 1
        progress.current_phase = "reading" if progress.pending_count > 0 else "done"
        progress.updated_at = datetime.now().isoformat()
        progress.save(self.progress_path)

        # 这里返回“全部批次发现 + 当前 style 文档”，真正的合并写入由更上层的 AI/CLI 决定。
        return {
            "total_batches": len(all_findings),
            "findings": all_findings,
            "current_style_docs": self._load_style_docs(),
        }

    # ── 工具方法 ──────────────────────────────────────────────────

    def get_status(self) -> Dict:
        """获取当前提取状态"""
        progress = self.progress
        if progress is None:
            return {"status": "not_initialized"}

        return {
            "status": progress.current_phase,
            "source_name": progress.source_name,
            "total_chunks": progress.total_chunks,
            "completed": progress.completed_count,
            "pending": progress.pending_count,
            "progress": f"{progress.progress_pct:.1f}%",
            "merge_count": progress.merge_count,
            "total_chars": progress.total_chars,
        }

    def get_batch_context(self, chunk_index: int) -> Dict:
        """获取指定批次的完整上下文（给 AI 用的 prompt 物料）

        包含：分块文本 + 当前风格文档 + 前一批次摘要

        Returns:
            {
                "chunk_text": str,
                "chunk_meta": {...},
                "existing_style_docs": {...},
                "previous_summary": str | None,
                "instructions": str,
            }
        """
        progress = self.progress
        if progress is None:
            raise RuntimeError("需要先调用 prepare()")

        # 批次上下文的目标不是提供全书原文，而是给模型一个“当前 chunk + 已有提炼结果”的最小闭环。
        text = TextChunker.load_chunk(self.chunks_dir, chunk_index)
        if text is None:
            raise FileNotFoundError(f"分块 {chunk_index} 不存在")

        # 加载当前风格文档
        existing_docs = self._load_style_docs()

        # 前一批次摘要作为局部连续性提示，帮助模型理解相邻 chunk 的语气和设定延续。
        prev_summary = None
        if chunk_index > 0:
            prev_path = self.batch_results_dir / f"batch_{chunk_index - 1:03d}.yaml"
            if prev_path.exists():
                prev_data = yaml.safe_load(prev_path.read_text(encoding="utf-8"))
                prev_summary = prev_data.get("findings", {}).get("summary", "")

        # 查找 batch 元信息
        batch_meta = None
        for b in progress.batches:
            if b.chunk_index == chunk_index:
                batch_meta = {
                    "chapter_range": b.chapter_range,
                    "char_count": b.char_count,
                }
                break

        return {
            "chunk_text": text,
            "chunk_meta": batch_meta or {},
            "existing_style_docs": existing_docs,
            "previous_summary": prev_summary,
            "batch_number": chunk_index + 1,
            "total_batches": progress.total_chunks,
            "source_name": progress.source_name,
        }

    def reset(self):
        """重置提取进度（保留分块文件）"""
        progress = self.progress
        if progress is None:
            return

        for batch in progress.batches:
            batch.status = "pending"
            batch.completed_at = None
            batch.craft_findings = 0
            batch.author_findings = 0
            batch.novel_findings = 0

        progress.current_phase = "reading"
        progress.merge_count = 0
        progress.updated_at = datetime.now().isoformat()
        progress.save(self.progress_path)
        self._progress = progress


# ── 便捷函数 ─────────────────────────────────────────────────────

def quick_prepare(
    source_file: str,
    novel_id: str,
    source_name: str,
    project_root: str = ".",
    chunk_size: int = 30000,
) -> Dict:
    """快速准备风格提取

    Returns:
        进度状态字典
    """
    pipeline = StyleExtractionPipeline(
        project_root=Path(project_root),
        novel_id=novel_id,
        source_name=source_name,
        chunk_size=chunk_size,
    )
    progress = pipeline.prepare(source_file=Path(source_file))
    return progress.to_dict()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="风格提取流水线 CLI — 切割源文本并管理提取进度",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # prepare 子命令
    p_prep = sub.add_parser("prepare", help="切割源文本，初始化提取进度")
    p_prep.add_argument("source_file", help="源 TXT 文件路径")
    p_prep.add_argument("--novel-id", required=True, help="小说项目 ID")
    p_prep.add_argument("--source-name", required=True, help="来源 ID（用户提供文本）")
    p_prep.add_argument("--project-root", default=".", help="项目根目录")
    p_prep.add_argument("--chunk-size", type=int, default=30000, help="分块字数")

    # status 子命令
    p_status = sub.add_parser("status", help="查看提取进度")
    p_status.add_argument("--novel-id", required=True, help="小说项目 ID")
    p_status.add_argument("--source-name", required=True, help="来源 ID（用户提供文本）")
    p_status.add_argument("--project-root", default=".", help="项目根目录")

    args = parser.parse_args()

    if args.command == "prepare":
        result = quick_prepare(
            source_file=args.source_file,
            novel_id=args.novel_id,
            source_name=args.source_name,
            project_root=args.project_root,
            chunk_size=args.chunk_size,
        )
        print(yaml.dump(result, allow_unicode=True, default_flow_style=False))

    elif args.command == "status":
        pipeline = StyleExtractionPipeline(
            project_root=Path(args.project_root),
            novel_id=args.novel_id,
            source_name=args.source_name,
        )
        progress = pipeline.load_progress()
        if progress is None:
            print("未找到提取进度，请先执行 prepare 命令。")
        else:
            print(yaml.dump(progress.to_dict(), allow_unicode=True, default_flow_style=False))
