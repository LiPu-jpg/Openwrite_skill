"""LLM 错误处理 - 从 InkOS 融合

提供人性化的错误消息，帮助用户快速定位问题。
"""

from __future__ import annotations


class LLMWrappedError(Exception):
    """包装后的 LLM 错误基类"""

    def __init__(self, message: str, original_error: str = ""):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self):
        if self.original_error:
            return f"{self.message}\n\n原始错误: {self.original_error}"
        return self.message


class APIError(LLMWrappedError):
    """通用 API 错误"""

    pass


class AuthenticationError(LLMWrappedError):
    """认证错误 (401/403)"""

    pass


class RateLimitError(LLMWrappedError):
    """限流错误 (429)"""

    pass


class InvalidRequestError(LLMWrappedError):
    """无效请求错误 (400)"""

    pass


class NetworkError(LLMWrappedError):
    """网络连接错误"""

    pass


class StreamError(LLMWrappedError):
    """流式输出错误"""

    pass


class ContextLengthError(LLMWrappedError):
    """上下文长度超限"""

    pass
