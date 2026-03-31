"""多 Agent 权限策略。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AgentSpec:
    name: str
    role: str
    required: bool
    can_read: List[str] = field(default_factory=list)
    can_write: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)


# 最小必要 Agent 集合（可执行且不冗余）
DEFAULT_AGENT_SPECS: Dict[str, AgentSpec] = {
    "director": AgentSpec(
        name="director",
        role="编排流程、决策门禁、质量裁决",
        required=True,
        can_read=["packet:*", "review:*", "state:*"],
        can_write=["workflow:stage", "workflow:decision"],
        forbidden=["manuscript:direct_edit", "world:direct_edit"],
    ),
    "context_engineer": AgentSpec(
        name="context_engineer",
        role="组装章节上下文，保证事实完整",
        required=True,
        can_read=["src:*", "runtime:*", "craft:*", "sources:*"],
        can_write=["packet:build"],
        forbidden=["manuscript:*", "world:*", "characters:*"],
    ),
    "writer": AgentSpec(
        name="writer",
        role="生成章节正文",
        required=True,
        can_read=["packet:*"],
        can_write=["manuscript:draft"],
        forbidden=["world:*", "characters:*", "outline:*"],
    ),
    "continuity_reviewer": AgentSpec(
        name="continuity_reviewer",
        role="连续性审查与问题清单输出",
        required=True,
        can_read=["packet:*", "manuscript:draft"],
        can_write=["review:report"],
        forbidden=["manuscript:direct_edit", "world:*", "characters:*"],
    ),
    "state_settler": AgentSpec(
        name="state_settler",
        role="更新角色状态、关系、资源账本",
        required=True,
        can_read=["manuscript:draft", "runtime:truth_files"],
        can_write=["world:current_state", "world:ledger", "world:relationships"],
        forbidden=["manuscript:rewrite", "outline:*"],
    ),
    "concept_curator": AgentSpec(
        name="concept_curator",
        role="新增或修订概念文档（实体/术语）",
        required=True,
        can_read=["manuscript:draft", "src:world/*"],
        can_write=["src:world/entities", "src:world/terminology"],
        forbidden=["manuscript:*", "outline:*"],
    ),
}


# 冗余 Agent（默认不启用）
REDUNDANT_AGENT_SPECS: Dict[str, AgentSpec] = {
    "style_polisher": AgentSpec(
        name="style_polisher",
        role="纯风格润色（可并入 writer + reviewer）",
        required=False,
    ),
    "hook_manager": AgentSpec(
        name="hook_manager",
        role="独立伏笔管理（可并入 state_settler）",
        required=False,
    ),
    "world_architect": AgentSpec(
        name="world_architect",
        role="世界观重写（高风险，应人工触发）",
        required=False,
    ),
}


def get_default_agent_specs() -> Dict[str, AgentSpec]:
    return dict(DEFAULT_AGENT_SPECS)


def get_redundant_agent_specs() -> Dict[str, AgentSpec]:
    return dict(REDUNDANT_AGENT_SPECS)
