"""ReAct Agent 实现

真正的 Agent 循环：
- 接收自然语言指令
- LLM 决定调用哪些工具
- 执行工具，返回结果
- 循环直到 LLM 确认完成
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """工具定义"""

    name: str
    description: str
    parameters: dict
    required: list[str] = field(default_factory=list)


@dataclass
class ToolCall:
    """工具调用"""

    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """工具执行结果"""

    tool_call_id: str
    result: str
    error: Optional[str] = None


class ReActAgent:
    """ReAct Agent

    真正的 Agent 循环：
    1. 构建 system prompt（包含工具定义）
    2. 循环（最多 max_turns）：
       - 调用 LLM（带工具）
       - LLM 返回 content 或 tool_calls
       - 如果有 content，打印并检查是否结束
       - 如果有 tool_calls，执行并添加结果到消息
    3. 返回最终结果

    用法:
        agent = ReActAgent(
            client=llm_client,
            model="gpt-4o-mini",
            tools=MY_TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )
        result = await agent.run("写第五章")
    """

    def __init__(
        self,
        client: Any,
        model: str,
        tools: list[ToolDefinition],
        system_prompt: str,
        max_turns: int = 20,
    ):
        self.client = client
        self.model = model
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_turns = max_turns

    async def run(
        self,
        instruction: str,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, str], None]] = None,
        on_message: Optional[Callable[[str], None]] = None,
    ) -> str:
        """运行 Agent

        Args:
            instruction: 用户指令
            on_tool_call: 工具调用回调 (name, args)
            on_tool_result: 工具结果回调 (name, result)
            on_message: LLM 消息回调 (content)

        Returns:
            最终回复内容
        """
        from ..llm import Message

        messages = [
            Message("system", self.system_prompt),
            Message("user", instruction),
        ]

        last_content = ""

        for turn in range(self.max_turns):
            logger.debug(f"Turn {turn + 1}/{self.max_turns}")

            response = self._chat_with_tools(messages)

            if response.content:
                last_content = response.content
                on_message and on_message(response.content)

                if not response.tool_calls:
                    logger.debug("Agent finished (no more tool calls)")
                    break

            for tool_call in response.tool_calls:
                tc_id = tool_call.get("id", "")
                tc_name = tool_call.get("name", "")
                tc_args = (
                    json.loads(tool_call.get("arguments", "{}"))
                    if tool_call.get("arguments")
                    else {}
                )
                on_tool_call and on_tool_call(tc_name, tc_args)

                try:
                    result = self._execute_tool(tc_name, tc_args)
                    on_tool_result and on_tool_result(tc_name, result)
                    messages.append(
                        Message(
                            role="tool",
                            content=result,
                            tool_call_id=tc_id,
                        )
                    )
                except Exception as e:
                    error_result = json.dumps({"error": str(e)})
                    on_tool_result and on_tool_result(tc_name, error_result)
                    messages.append(
                        Message(
                            role="tool",
                            content=error_result,
                            tool_call_id=tc_id,
                        )
                    )
        else:
            logger.warning(f"Reached max turns ({self.max_turns})")

        return last_content

    def _chat_with_tools(self, messages: list) -> Any:
        """调用 LLM（带工具）"""
        from ..llm import Message

        llm_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.tools
        ]

        return self.client.chat_with_tools(messages, llm_tools)

    def _execute_tool(self, name: str, args: dict) -> str:
        """执行工具"""
        # 查找工具
        tool = next((t for t in self.tools if t.name == name), None)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {name}"})

        # 验证参数
        for req in tool.required:
            if req not in args:
                return json.dumps({"error": f"Missing required argument: {req}"})

        # 调用注册的执行器
        if hasattr(self, f"_tool_{name}"):
            result = getattr(self, f"_tool_{name}")(args)
            return json.dumps(result) if isinstance(result, dict) else str(result)

        return json.dumps({"error": f"Tool '{name}' not implemented"})

    def _register_tool_executors(self, executors: dict):
        """注册工具执行器

        用法:
            agent._register_tool_executors({
                'write_draft': lambda args: pipeline.write_draft(...),
                'audit_chapter': lambda args: pipeline.audit_chapter(...),
            })
        """
        for name, fn in executors.items():
            setattr(self, f"_tool_{name}", fn)


class SimpleResponse:
    """简单响应（用于不支持工具调用时）"""

    def __init__(self, content: str, tool_calls: list):
        self.content = content
        self.tool_calls = tool_calls


# === OpenWrite 内置工具 ===

OPENWRITE_TOOLS = [
    ToolDefinition(
        name="write_chapter",
        description="写一章草稿。根据当前大纲和上下文生成章节正文。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节 ID（如 ch_005）"},
                "guidance": {"type": "string", "description": "创作指导（可选，自然语言）"},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="review_chapter",
        description="审查章节。检查逻辑、风格、AI痕迹等问题。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节 ID"},
                "strict": {"type": "boolean", "description": "严格模式"},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="get_status",
        description="获取项目状态概览。",
        parameters={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="get_context",
        description="获取指定章节的写作上下文。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节 ID"},
                "window_size": {"type": "integer", "description": "大纲窗口大小"},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="list_chapters",
        description="列出所有章节。",
        parameters={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="create_outline",
        description="创建或更新大纲。",
        parameters={
            "type": "object",
            "properties": {
                "outline_content": {"type": "string", "description": "大纲内容（Markdown）"},
            },
            "required": ["outline_content"],
        },
    ),
    ToolDefinition(
        name="create_character",
        description="创建角色。",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "角色名"},
                "description": {"type": "string", "description": "角色描述"},
            },
            "required": ["name"],
        },
    ),
    ToolDefinition(
        name="get_truth_files",
        description="读取真相文件（世界状态、伏笔、摘要等）。",
        parameters={
            "type": "object",
            "properties": {},
        },
    ),
    ToolDefinition(
        name="update_truth_file",
        description="更新真相文件。",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "文件名（current_state/pending_hooks/particle_ledger/chapter_summaries）",
                },
                "content": {"type": "string", "description": "新内容"},
            },
            "required": ["file_name", "content"],
        },
    ),
]


OPENWRITE_SYSTEM_PROMPT = """你是 OpenWrite 小说创作引擎的 Agent。

你的职责是帮用户完成小说创作任务，包括：
- 写章节、审查章节
- 管理大纲、角色、世界观
- 跟踪伏笔和真相文件
- 回答创作相关问题

## 可用工具

| 工具 | 作用 |
|------|------|
| write_chapter | 写一章草稿 |
| review_chapter | 审查章节 |
| get_status | 查看项目状态 |
| get_context | 获取写作上下文 |
| list_chapters | 列出章节 |
| create_outline | 创建/更新大纲 |
| create_character | 创建角色 |
| get_truth_files | 读取真相文件 |
| update_truth_file | 更新真相文件 |

## 工作流程

1. 用户给出指令后，先了解当前状态
2. 根据需要调用工具
3. 向用户汇报进展
4. 直到任务完成

## 规则

- 每完成一步，简要汇报
- 如果缺少必要信息，先询问用户
- 遵循项目的大纲和设定
"""
