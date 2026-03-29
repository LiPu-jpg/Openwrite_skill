"""OpenCode Skill Tools

工具函数模块：
- ContextBuilder: 上下文组装（核心）
- FileOps: 文件操作（沙箱化）
- DataQueries: 数据查询
- TextChunker: 大文本智能切割
- StyleExtractionPipeline: 风格分批提取流水线
- TruthFilesManager: 真相文件管理
- LLM Client: 统一 LLM 调用
- Agent: 内置 Agent 基类
- PostWriteValidator: 后置验证
- StateValidator: 状态验证
- DialogueFingerprintExtractor: 对话指纹提取
- RadarAgent: 市场分析
- ArchitectAgent: AI 大纲生成
- Wizard: 交互式引导
"""

from .context_builder import ContextBuilder
from .file_ops import FileOps
from .data_queries import DataQueries
from .text_chunker import TextChunker, chunk_novel
from .style_extraction_pipeline import StyleExtractionPipeline
from .truth_manager import TruthFilesManager, TruthFiles, StateSnapshot
from .post_validator import PostWriteValidator
from .state_validator import StateValidator
from .dialogue_fingerprint import DialogueFingerprintExtractor
from .chapter_assembler import ChapterAssemblerV2, ChapterAssemblyPacket

__all__ = [
    "ContextBuilder",
    "FileOps",
    "DataQueries",
    "TextChunker",
    "chunk_novel",
    "StyleExtractionPipeline",
    "TruthFilesManager",
    "TruthFiles",
    "StateSnapshot",
    "PostWriteValidator",
    "StateValidator",
    "DialogueFingerprintExtractor",
    "ChapterAssemblerV2",
    "ChapterAssemblyPacket",
]
