from __future__ import annotations

import asyncio
from types import SimpleNamespace

from tools.agent.react import ReActAgent, ToolDefinition
from tools.llm import Message


class RecordingClient:
    def __init__(self, responses: list[object]):
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def chat_with_tools(self, messages, tools, **kwargs):
        self.calls.append(
            {
                "messages": list(messages),
                "tools": list(tools),
                "kwargs": dict(kwargs),
            }
        )
        if self.responses:
            return self.responses.pop(0)
        return SimpleNamespace(content="", tool_calls=[])


def _tool_response(content: str = "", tool_calls: list[dict] | None = None):
    return SimpleNamespace(content=content, tool_calls=tool_calls or [])


def test_react_agent_direct_chat_uses_injected_context_messages():
    client = RecordingClient([_tool_response("继续")])
    agent = ReActAgent(
        client=client,
        model="demo",
        tools=[],
        system_prompt="系统提示",
    )

    result = asyncio.run(
        agent.run(
            "继续写",
            context_messages=[
                Message("assistant", "会话摘要: 已确认都市职场异能。"),
                Message("assistant", "最近轮次: user->我想写一个普通上班族觉醒术式的故事"),
            ],
        )
    )

    assert result == "继续"
    assert [message.role for message in client.calls[0]["messages"]] == [
        "system",
        "assistant",
        "assistant",
        "user",
    ]
    assert "会话摘要" in client.calls[0]["messages"][1].content
    assert "最近轮次" in client.calls[0]["messages"][2].content


def test_react_agent_supports_context_message_factory_callback():
    client = RecordingClient([_tool_response("继续")])
    agent = ReActAgent(
        client=client,
        model="demo",
        tools=[],
        system_prompt="系统提示",
    )
    calls = {"count": 0}

    def factory():
        calls["count"] += 1
        return [Message("assistant", "会话摘要: 由工厂注入。")]

    result = asyncio.run(
        agent.run(
            "继续写",
            context_message_factory=factory,
        )
    )

    assert result == "继续"
    assert calls["count"] == 1
    assert client.calls[0]["messages"][1].content == "会话摘要: 由工厂注入。"


def test_react_agent_direct_tool_call_uses_injected_context_messages():
    client = RecordingClient(
        [
            _tool_response(
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "get_status",
                        "arguments": "{}",
                    }
                ]
            ),
            _tool_response("状态正常"),
        ]
    )
    agent = ReActAgent(
        client=client,
        model="demo",
        tools=[
            ToolDefinition(
                name="get_status",
                description="获取状态",
                parameters={"type": "object", "properties": {}},
            )
        ],
        system_prompt="系统提示",
    )
    captured: list[dict[str, object]] = []
    agent._register_tool_executors(
        {
            "get_status": lambda args: captured.append(args) or {"ok": True, "stage": "rolling_outline"}
        }
    )

    result = asyncio.run(
        agent.run(
            "查看状态",
            context_messages=[Message("assistant", "会话摘要: 已确认章节范围。")],
        )
    )

    assert result == "状态正常"
    assert captured == [{}]
    assert len(client.calls) == 2
    assert client.calls[0]["messages"][1].content.startswith("会话摘要")
    assert any(message.role == "tool" for message in client.calls[1]["messages"])


def test_react_agent_action_tool_call_uses_injected_context_messages():
    client = RecordingClient(
        [
            _tool_response(
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "summarize_ideation",
                        "arguments": "{}",
                    }
                ]
            ),
            _tool_response("已汇总"),
        ]
    )
    agent = ReActAgent(
        client=client,
        model="demo",
        tools=[
            ToolDefinition(
                name="summarize_ideation",
                description="汇总想法",
                parameters={"type": "object", "properties": {}},
            )
        ],
        system_prompt="系统提示",
    )
    captured: list[dict[str, object]] = []
    agent._register_tool_executors(
        {
            "summarize_ideation": lambda args: captured.append(args) or {
                "ok": True,
                "action": "summarize_ideation",
            }
        }
    )

    result = asyncio.run(
        agent.run(
            "先帮我汇总一下当前想法",
            context_messages=[Message("assistant", "最近会话摘要: 设定已稳定。")],
        )
    )

    assert result == "已汇总"
    assert captured == [{}]
    assert len(client.calls) == 2
    assert client.calls[0]["messages"][1].content.startswith("最近会话摘要")
    assert any(message.role == "tool" for message in client.calls[1]["messages"])
