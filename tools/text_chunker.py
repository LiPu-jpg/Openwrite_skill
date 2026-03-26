"""大文本智能切割工具

将百万字级的 .txt 文件按章节边界切割为可处理的分块（默认 ~3万字/chunk）。

核心策略：
  1. 自动识别章节标记（第X章、Chapter X 等多种格式）
  2. 按章节边界聚合，尽量不拆开单个章节
  3. 超长章节（>chunk_size）按段落边界二次切割
  4. 输出切割元数据（chunk 索引、章节范围、字数统计）

Usage:
    chunker = TextChunker(chunk_size=30000)
    result = chunker.chunk_file(Path("my_novel.txt"))
    for chunk in result.chunks:
        print(f"Chunk {chunk.index}: {chunk.chapter_range}, {chunk.char_count} chars")
        text = chunk.text  # 实际文本内容
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import hashlib
from datetime import datetime


# ── 章节识别正则 ──────────────────────────────────────────────────

# 匹配各种中文小说章节格式
CHAPTER_PATTERNS = [
    # 第X章 格式（中文数字 + 阿拉伯数字）
    r"^第[零一二三四五六七八九十百千万\d]+章[\s　：:·—]",
    r"^第[零一二三四五六七八九十百千万\d]+章$",
    # 第X节/回/卷/篇
    r"^第[零一二三四五六七八九十百千万\d]+[节回卷篇][\s　：:·—]",
    r"^第[零一二三四五六七八九十百千万\d]+[节回卷篇]$",
    # Chapter X 格式
    r"^Chapter\s+\d+",
    r"^CHAPTER\s+\d+",
    # 纯数字章节标记
    r"^\d{1,4}[\s　、.．]",
    # 序章/楔子/尾声等
    r"^(序章|序|楔子|引子|终章|尾声|番外|后记|前言|附录)[\s　：:·—]",
    r"^(序章|序|楔子|引子|终章|尾声|番外|后记|前言|附录)$",
]

# 编译为单一正则（性能优化）
_COMPILED_CHAPTER_RE = re.compile(
    "|".join(f"({p})" for p in CHAPTER_PATTERNS),
    re.MULTILINE,
)


@dataclass
class ChapterInfo:
    """章节信息"""
    index: int                          # 章节序号（从 1 开始）
    title: str                          # 章节标题行
    start_line: int                     # 起始行号（0-based）
    end_line: int                       # 结束行号（exclusive）
    char_count: int                     # 字符数
    text: str = field(repr=False)       # 章节文本


@dataclass
class TextChunk:
    """文本分块"""
    index: int                          # 分块序号（从 0 开始）
    chapter_start: int                  # 起始章节序号
    chapter_end: int                    # 结束章节序号
    chapter_range: str                  # 可读的章节范围描述
    char_count: int                     # 字符数
    chapter_count: int                  # 包含的章节数
    text: str = field(repr=False)       # 分块文本

    def to_meta(self) -> Dict:
        """导出元数据（不含文本）"""
        return {
            "index": self.index,
            "chapter_start": self.chapter_start,
            "chapter_end": self.chapter_end,
            "chapter_range": self.chapter_range,
            "char_count": self.char_count,
            "chapter_count": self.chapter_count,
        }


@dataclass
class ChunkResult:
    """切割结果"""
    source_file: str                    # 源文件路径
    source_hash: str                    # 源文件 MD5（用于断点续传验证）
    total_chars: int                    # 总字符数
    total_chapters: int                 # 总章节数
    total_chunks: int                   # 总分块数
    chunk_size: int                     # 目标分块大小
    chunks: List[TextChunk]             # 分块列表
    created_at: str                     # 创建时间

    def to_manifest(self) -> Dict:
        """导出清单文件（不含文本，用于进度追踪）"""
        return {
            "source_file": self.source_file,
            "source_hash": self.source_hash,
            "total_chars": self.total_chars,
            "total_chapters": self.total_chapters,
            "total_chunks": self.total_chunks,
            "chunk_size": self.chunk_size,
            "created_at": self.created_at,
            "chunks": [c.to_meta() for c in self.chunks],
        }


class TextChunker:
    """大文本智能切割器

    Args:
        chunk_size: 目标分块大小（字符数），默认 30000（约3万字）
        min_chunk_size: 最小分块大小，低于此值会与下一块合并，默认 5000
        overlap_chars: 分块间重叠字符数（为上下文连续性），默认 500
    """

    def __init__(
        self,
        chunk_size: int = 30000,
        min_chunk_size: int = 5000,
        overlap_chars: int = 500,
    ):
        self.chunk_size = chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_chars = overlap_chars

    # ── 公开接口 ─────────────────────────────────────────────────

    def chunk_file(self, file_path: Path, encoding: str = "utf-8") -> ChunkResult:
        """切割单个文件

        Args:
            file_path: .txt 文件路径
            encoding: 文件编码，默认 utf-8（也支持 gbk/gb18030）

        Returns:
            ChunkResult 包含所有分块和元数据
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 读取全文
        text = self._read_file(file_path, encoding)
        source_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

        # 识别章节
        chapters = self._detect_chapters(text)

        # 按章节聚合为分块
        chunks = self._aggregate_chunks(chapters)

        return ChunkResult(
            source_file=str(file_path),
            source_hash=source_hash,
            total_chars=len(text),
            total_chapters=len(chapters),
            total_chunks=len(chunks),
            chunk_size=self.chunk_size,
            chunks=chunks,
            created_at=datetime.now().isoformat(),
        )

    def chunk_text(self, text: str, source_name: str = "inline") -> ChunkResult:
        """直接切割文本字符串（不需要文件）

        Args:
            text: 文本内容
            source_name: 来源标识

        Returns:
            ChunkResult
        """
        source_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        chapters = self._detect_chapters(text)
        chunks = self._aggregate_chunks(chapters)

        return ChunkResult(
            source_file=source_name,
            source_hash=source_hash,
            total_chars=len(text),
            total_chapters=len(chapters),
            total_chunks=len(chunks),
            chunk_size=self.chunk_size,
            chunks=chunks,
            created_at=datetime.now().isoformat(),
        )

    def save_chunks(self, result: ChunkResult, output_dir: Path) -> Path:
        """将切割结果保存到目录

        目录结构：
            output_dir/
              manifest.json          # 清单（无文本）
              chunk_000.txt          # 分块文本
              chunk_001.txt
              ...

        Args:
            result: 切割结果
            output_dir: 输出目录

        Returns:
            manifest.json 路径
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存清单
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(result.to_manifest(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 保存每个分块
        for chunk in result.chunks:
            chunk_path = output_dir / f"chunk_{chunk.index:03d}.txt"
            chunk_path.write_text(chunk.text, encoding="utf-8")

        return manifest_path

    @staticmethod
    def load_chunk(output_dir: Path, chunk_index: int) -> Optional[str]:
        """按需加载单个分块文本

        Args:
            output_dir: save_chunks 输出的目录
            chunk_index: 分块索引

        Returns:
            分块文本，不存在则返回 None
        """
        chunk_path = Path(output_dir) / f"chunk_{chunk_index:03d}.txt"
        if chunk_path.exists():
            return chunk_path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def load_manifest(output_dir: Path) -> Optional[Dict]:
        """加载清单文件

        Returns:
            清单字典，不存在则返回 None
        """
        manifest_path = Path(output_dir) / "manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        return None

    # ── 内部方法 ─────────────────────────────────────────────────

    def _read_file(self, file_path: Path, encoding: str) -> str:
        """读取文件，自动处理编码"""
        encodings = [encoding, "utf-8", "gbk", "gb18030", "utf-8-sig"]
        for enc in encodings:
            try:
                return file_path.read_text(encoding=enc)
            except (UnicodeDecodeError, LookupError):
                continue
        raise ValueError(f"无法解码文件 {file_path}，尝试了: {encodings}")

    def _detect_chapters(self, text: str) -> List[ChapterInfo]:
        """识别文本中的章节

        策略：
          1. 用正则逐行扫描章节标记
          2. 如果找到章节标记，按标记切割
          3. 如果没找到，按段落空行切割为虚拟章节
        """
        lines = text.split("\n")
        chapter_starts: List[Tuple[int, str]] = []  # (行号, 标题)

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if _COMPILED_CHAPTER_RE.match(stripped):
                chapter_starts.append((i, stripped))

        # 没有找到章节标记 → 按段落切割
        if len(chapter_starts) < 2:
            return self._fallback_paragraph_chapters(text, lines)

        # 构建章节列表
        chapters: List[ChapterInfo] = []

        # 处理第一个章节标记之前的内容（如果有）
        if chapter_starts[0][0] > 0:
            pre_text = "\n".join(lines[: chapter_starts[0][0]]).strip()
            if len(pre_text) > 100:  # 忽略太短的前导内容
                chapters.append(
                    ChapterInfo(
                        index=0,
                        title="[前言/序]",
                        start_line=0,
                        end_line=chapter_starts[0][0],
                        char_count=len(pre_text),
                        text=pre_text,
                    )
                )

        # 按章节标记切割
        for idx, (start, title) in enumerate(chapter_starts):
            end = (
                chapter_starts[idx + 1][0]
                if idx + 1 < len(chapter_starts)
                else len(lines)
            )
            chapter_text = "\n".join(lines[start:end]).strip()
            chapters.append(
                ChapterInfo(
                    index=len(chapters) + 1,
                    title=title,
                    start_line=start,
                    end_line=end,
                    char_count=len(chapter_text),
                    text=chapter_text,
                )
            )

        return chapters

    def _fallback_paragraph_chapters(
        self, text: str, lines: List[str]
    ) -> List[ChapterInfo]:
        """没有章节标记时，按连续空行切割为虚拟章节

        每 ~5000 字一个虚拟章节，在段落边界处切割。
        """
        virtual_size = min(5000, self.chunk_size // 3)
        chapters: List[ChapterInfo] = []
        current_start = 0
        current_chars = 0
        current_lines: List[str] = []

        for i, line in enumerate(lines):
            current_lines.append(line)
            current_chars += len(line) + 1  # +1 for \n

            # 到达目标大小，在空行处切割
            if current_chars >= virtual_size and line.strip() == "":
                chapter_text = "\n".join(current_lines).strip()
                if chapter_text:
                    chapters.append(
                        ChapterInfo(
                            index=len(chapters) + 1,
                            title=f"[段落 {len(chapters) + 1}]",
                            start_line=current_start,
                            end_line=i + 1,
                            char_count=len(chapter_text),
                            text=chapter_text,
                        )
                    )
                current_start = i + 1
                current_chars = 0
                current_lines = []

        # 处理剩余内容
        if current_lines:
            chapter_text = "\n".join(current_lines).strip()
            if chapter_text:
                chapters.append(
                    ChapterInfo(
                        index=len(chapters) + 1,
                        title=f"[段落 {len(chapters) + 1}]",
                        start_line=current_start,
                        end_line=len(lines),
                        char_count=len(chapter_text),
                        text=chapter_text,
                    )
                )

        # 如果还是只有一个，直接作为整体
        if not chapters:
            chapters.append(
                ChapterInfo(
                    index=1,
                    title="[全文]",
                    start_line=0,
                    end_line=len(lines),
                    char_count=len(text),
                    text=text,
                )
            )

        return chapters

    def _aggregate_chunks(self, chapters: List[ChapterInfo]) -> List[TextChunk]:
        """将章节聚合为分块

        策略：
          1. 按顺序累积章节，直到接近 chunk_size
          2. 超过 chunk_size 则开始新的分块
          3. 尾部小块（< min_chunk_size）合并到前一块
          4. 可选添加 overlap
        """
        if not chapters:
            return []

        chunks: List[TextChunk] = []
        current_chapters: List[ChapterInfo] = []
        current_chars = 0

        for ch in chapters:
            # 当前章节加入后是否超出 chunk_size
            if current_chars + ch.char_count > self.chunk_size and current_chapters:
                # 打包当前累积的章节为一个 chunk
                chunks.append(self._build_chunk(len(chunks), current_chapters))
                current_chapters = []
                current_chars = 0

            current_chapters.append(ch)
            current_chars += ch.char_count

        # 处理剩余章节
        if current_chapters:
            # 如果太小且有前一个 chunk，合并
            if (
                current_chars < self.min_chunk_size
                and chunks
                and chunks[-1].char_count + current_chars <= self.chunk_size * 1.5
            ):
                # 合并到上一个 chunk
                last = chunks.pop()
                merged_text = last.text + "\n\n" + "\n\n".join(
                    ch.text for ch in current_chapters
                )
                merged_end = current_chapters[-1].index
                chunks.append(
                    TextChunk(
                        index=last.index,
                        chapter_start=last.chapter_start,
                        chapter_end=merged_end,
                        chapter_range=f"Ch.{last.chapter_start}-{merged_end}",
                        char_count=len(merged_text),
                        chapter_count=last.chapter_count + len(current_chapters),
                        text=merged_text,
                    )
                )
            else:
                chunks.append(self._build_chunk(len(chunks), current_chapters))

        # 添加 overlap（可选）
        if self.overlap_chars > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _build_chunk(
        self, index: int, chapters: List[ChapterInfo]
    ) -> TextChunk:
        """从章节列表构建一个 TextChunk"""
        text = "\n\n".join(ch.text for ch in chapters)
        ch_start = chapters[0].index
        ch_end = chapters[-1].index

        # 构建可读范围描述
        if ch_start == ch_end:
            ch_range = chapters[0].title
        else:
            ch_range = f"{chapters[0].title} ~ {chapters[-1].title}"

        return TextChunk(
            index=index,
            chapter_start=ch_start,
            chapter_end=ch_end,
            chapter_range=ch_range,
            char_count=len(text),
            chapter_count=len(chapters),
            text=text,
        )

    def _add_overlap(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """为分块添加首尾重叠（保持上下文连续性）

        从前一个 chunk 的末尾取 overlap_chars 个字符，
        添加到下一个 chunk 的开头（用分隔符标记）。
        """
        result = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_text = chunks[i - 1].text
            # 取前一块末尾的 overlap 内容
            overlap_text = prev_text[-self.overlap_chars :]
            # 在段落边界截断（不要截断句子中间）
            newline_pos = overlap_text.find("\n")
            if newline_pos > 0:
                overlap_text = overlap_text[newline_pos + 1 :]

            # 构建带 overlap 的新 chunk
            new_text = (
                f"[... 上一批次末尾 ...]\n{overlap_text}\n"
                f"[... 本批次正文 ...]\n{chunks[i].text}"
            )
            result.append(
                TextChunk(
                    index=chunks[i].index,
                    chapter_start=chunks[i].chapter_start,
                    chapter_end=chunks[i].chapter_end,
                    chapter_range=chunks[i].chapter_range,
                    char_count=len(new_text),
                    chapter_count=chunks[i].chapter_count,
                    text=new_text,
                )
            )

        return result

    # ── 辅助方法 ─────────────────────────────────────────────────

    @staticmethod
    def estimate_chunks(file_path: Path, chunk_size: int = 30000) -> Dict:
        """快速估算文件的切割信息（不做实际切割）

        Returns:
            {"file_size": int, "estimated_chars": int, "estimated_chunks": int}
        """
        file_size = file_path.stat().st_size
        # 中文 UTF-8 每字符约 3 字节
        estimated_chars = file_size // 3
        estimated_chunks = max(1, estimated_chars // chunk_size)
        return {
            "file_size": file_size,
            "estimated_chars": estimated_chars,
            "estimated_chunks": estimated_chunks,
        }


# ── 便捷函数 ─────────────────────────────────────────────────────

def chunk_novel(
    file_path: str,
    output_dir: Optional[str] = None,
    chunk_size: int = 30000,
    encoding: str = "utf-8",
) -> ChunkResult:
    """一键切割小说文件

    Args:
        file_path: .txt 文件路径
        output_dir: 输出目录（可选，不指定则不保存分块文件）
        chunk_size: 分块大小（字符），默认 30000
        encoding: 编码，默认 utf-8

    Returns:
        ChunkResult

    Example:
        result = chunk_novel("my_novel.txt", "data/chunks/my_novel")
        print(f"切割为 {result.total_chunks} 个分块")
    """
    chunker = TextChunker(chunk_size=chunk_size)
    result = chunker.chunk_file(Path(file_path), encoding=encoding)

    if output_dir:
        chunker.save_chunks(result, Path(output_dir))

    return result
