"""Agent 模块 - 从 InkOS 融合

内置 Agent 架构：
- BaseAgent: 所有 Agent 的基类
- WriterAgent: 两阶段写作 Agent
- ReviewerAgent: 审核 Agent
- ReActAgent: 真正的 ReAct Agent 循环
"""

from .base import BaseAgent, AgentContext
from .writer import WriterAgent, WritingResult
from .reviewer import ReviewerAgent, ReviewResult
from .react import ReActAgent, OPENWRITE_TOOLS, OPENWRITE_SYSTEM_PROMPT

__all__ = [
    "BaseAgent",
    "AgentContext",
    "WriterAgent",
    "WritingResult",
    "ReviewerAgent",
    "ReviewResult",
    "ReActAgent",
    "OPENWRITE_TOOLS",
    "OPENWRITE_SYSTEM_PROMPT",
]
