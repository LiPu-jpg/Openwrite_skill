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
from typing import Any, Callable, Optional, Sequence

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
        context_messages: Optional[Sequence[Any]] = None,
        context_message_factory: Optional[Callable[[], Sequence[Any]]] = None,
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

        messages = [Message("system", self.system_prompt)]
        messages.extend(self._coerce_messages(context_message_factory() if context_message_factory else None))
        messages.extend(self._coerce_messages(context_messages))
        messages.append(Message("user", instruction))

        last_content = ""

        for turn in range(self.max_turns):
            logger.debug(f"Turn {turn + 1}/{self.max_turns}")

            response = self._chat_with_tools(messages)

            if response.tool_calls:
                assistant_msg = Message("assistant", response.content or "")
                # 为兼容 OpenAI/兼容接口，显式保留 assistant 的 tool_calls。
                setattr(assistant_msg, "tool_calls", response.tool_calls)
                messages.append(assistant_msg)

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

    def _coerce_messages(self, messages: Optional[Sequence[Any]]) -> list[Any]:
        from ..llm import Message

        if not messages:
            return []

        normalized: list[Any] = []
        for message in messages:
            if isinstance(message, Message):
                normalized.append(message)
            elif isinstance(message, dict):
                normalized.append(
                    Message(
                        role=message.get("role", "assistant"),
                        content=str(message.get("content", "")),
                        tool_call_id=str(message.get("tool_call_id", "")),
                    )
                )
            else:
                normalized.append(Message("assistant", str(message)))
        return normalized

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
                    "description": "文件名（current_state/ledger/relationships）",
                },
                "content": {"type": "string", "description": "新内容"},
            },
            "required": ["file_name", "content"],
        },
    ),
    # 伏笔管理
    ToolDefinition(
        name="create_foreshadowing",
        description="创建伏笔节点。",
        parameters={
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "伏笔ID（如 f001）"},
                "content": {"type": "string", "description": "伏笔内容描述"},
                "weight": {"type": "integer", "description": "权重 1-10，默认5"},
                "layer": {"type": "string", "description": "层级（主线/支线/彩蛋）"},
                "created_at": {"type": "string", "description": "埋设章节（如 ch_001）"},
                "target_chapter": {"type": "string", "description": "预期回收章节（如 ch_015）"},
            },
            "required": ["node_id", "content"],
        },
    ),
    ToolDefinition(
        name="list_foreshadowing",
        description="列出伏笔节点。可按状态/权重/层级过滤。",
        parameters={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "状态过滤（埋伏/待收/已收/废弃）"},
                "min_weight": {"type": "integer", "description": "最小权重过滤"},
                "layer": {"type": "string", "description": "层级过滤（主线/支线）"},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="update_foreshadowing",
        description="更新伏笔状态。",
        parameters={
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "伏笔ID"},
                "status": {"type": "string", "description": "新状态（埋伏/待收/已收/废弃）"},
            },
            "required": ["node_id", "status"],
        },
    ),
    ToolDefinition(
        name="validate_foreshadowing",
        description="验证伏笔DAG，检查环和引用错误。",
        parameters={
            "type": "object",
            "properties": {},
        },
    ),
    # 状态验证
    ToolDefinition(
        name="validate_truth",
        description="验证真相文件与章节内容的一致性。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "要验证的章节ID（默认最新章节）"},
            },
            "required": [],
        },
    ),
    # 世界查询
    ToolDefinition(
        name="query_world",
        description="查询世界观实体。可列出所有实体或获取单个实体详情。",
        parameters={
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "实体ID（不填则列出所有）"},
                "type": {
                    "type": "string",
                    "description": "类型过滤（location/person/technique/item等）",
                },
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="get_world_relations",
        description="获取世界观关系图谱，展示实体间的关联。",
        parameters={
            "type": "object",
            "properties": {},
        },
    ),
    # 对话质量
    ToolDefinition(
        name="extract_dialogue_fingerprint",
        description="提取角色对话风格指纹，分析口头禅、用词习惯等。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID（默认最新）"},
                "character_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要分析的角色名列表",
                },
            },
            "required": [],
        },
    ),
    # 后置验证
    ToolDefinition(
        name="validate_post_write",
        description="零成本规则检测，检查禁止句式、AI味、敏感词等。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID（默认最新）"},
            },
            "required": [],
        },
    ),
    # 工作流
    ToolDefinition(
        name="get_workflow_status",
        description="获取工作流状态，查看写作流程进度。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID（不填则列出所有）"},
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="start_workflow",
        description="为指定章节启动写作工作流。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID"},
            },
            "required": ["chapter_id"],
        },
    ),
    ToolDefinition(
        name="advance_workflow",
        description="推进工作流到下一阶段。",
        parameters={
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID"},
                "stage_name": {"type": "string", "description": "目标阶段（可选）"},
            },
            "required": ["chapter_id"],
        },
    ),
    # 文本处理
    ToolDefinition(
        name="chunk_text",
        description="将大文本文件按章节边界切割为chunk。",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件路径"},
                "chunk_size": {"type": "integer", "description": "chunk大小（默认30000）"},
            },
            "required": ["file_path"],
        },
    ),
    ToolDefinition(
        name="compress_section",
        description="压缩节/篇的章节摘要。",
        parameters={
            "type": "object",
            "properties": {
                "arc_id": {"type": "string", "description": "篇ID"},
                "section_id": {"type": "string", "description": "节ID（不填则压缩整篇）"},
            },
            "required": [],
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
| create_foreshadowing | 创建伏笔 |
| list_foreshadowing | 列出伏笔 |
| update_foreshadowing | 更新伏笔状态 |
| validate_foreshadowing | 验证伏笔DAG |
| query_world | 查询世界观实体 |
| get_world_relations | 获取关系图谱 |
| validate_truth | 验证真相文件一致性 |
| extract_dialogue_fingerprint | 提取对话风格指纹 |
| validate_post_write | 后置规则验证 |
| get_workflow_status | 查看工作流进度 |
| start_workflow | 启动工作流 |
| advance_workflow | 推进工作流 |
| chunk_text | 切割大文本 |
| compress_section | 压缩摘要 |

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
