"""角色数据模型

提供 CharacterTier / CharacterProfile / CharacterCard，
适配 opencode_skill/tools/context_builder.py 使用的接口。
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CharacterTier(str, Enum):
    """角色层级"""
    PROTAGONIST = "主角"
    MAJOR = "重要配角"
    MINOR = "普通配角"
    EXTRA = "炮灰"


class CharacterProfile(BaseModel):
    """简化角色档案 — 用于上下文传递"""

    character_id: str = Field(default="", description="角色 ID")
    name: str = Field(default="", description="角色名")
    tier: CharacterTier = Field(default=CharacterTier.MINOR, description="层级")
    backstory: str = Field(default="", description="背景")
    appearance: str = Field(default="", description="外貌")
    personality: List[str] = Field(default_factory=list, description="性格标签")
    faction: str = Field(default="", description="势力")
    current_location: str = Field(default="", description="当前位置")
    current_status: str = Field(default="", description="当前状态")
    notes: str = Field(default="", description="备注")

    def to_context_text(self, max_chars: int = 0) -> str:
        """生成用于 AI 上下文的纯文本摘要"""
        parts: List[str] = [f"【{self.name}】 ({self.tier.value})"]
        if self.appearance:
            parts.append(f"外貌: {self.appearance}")
        if self.personality:
            parts.append(f"性格: {'、'.join(self.personality)}")
        if self.backstory:
            parts.append(f"背景: {self.backstory}")
        if self.faction:
            parts.append(f"势力: {self.faction}")
        text = "\n".join(parts)
        if max_chars and len(text) > max_chars:
            return text[:max_chars] + "…"
        return text


class CharacterCard(BaseModel):
    """角色卡片 — YAML 格式的轻量级档案"""

    id: str = Field(default="", description="角色 ID")
    name: str = Field(default="", description="角色名")
    tier: str = Field(default="普通配角", description="层级")
    age: Optional[int] = Field(default=None, description="年龄")
    gender: Optional[str] = Field(default=None, description="性别")
    occupation: str = Field(default="", description="职业")
    brief: str = Field(default="", description="一句话描述")
    appearance: str = Field(default="", description="外貌")
    personality: List[str] = Field(default_factory=list, description="性格标签")
    background: str = Field(default="", description="背景")
    faction: str = Field(default="", description="势力")
    aliases: List[str] = Field(default_factory=list, description="别名")
    relationships: List[Dict] = Field(default_factory=list, description="关系")

    def to_profile(self) -> CharacterProfile:
        """转为 CharacterProfile"""
        return CharacterProfile(
            character_id=self.id,
            name=self.name,
            tier=CharacterTier(self.tier) if self.tier in [t.value for t in CharacterTier] else CharacterTier.MINOR,
            appearance=self.appearance,
            backstory=self.background,
            personality=self.personality,
            faction=self.faction,
        )
