"""LLM 客户端模块

从 InkOS 融合的核心 LLM 封装：
- 统一接口支持 OpenAI / Anthropic / 自定义
- 流式输出监控
- 流失败自动降级为同步
- 人性化错误处理
"""

from .client import LLMClient, LLMConfig, LLMResponse, ToolCallResponse, Message
from .errors import (
    LLMWrappedError,
    APIError,
    AuthenticationError,
    RateLimitError,
    InvalidRequestError,
    NetworkError,
)

__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "ToolCallResponse",
    "Message",
    "LLMWrappedError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "InvalidRequestError",
    "NetworkError",
]
