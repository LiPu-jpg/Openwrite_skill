"""风格数据模型

提供 VoicePattern / LanguageStyle / RhythmStyle / StyleProfile，
适配 opencode_skill/tools/context_builder.py 的三层风格架构使用。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class VoicePattern(BaseModel):
    """叙述者声音模式"""
    narrator_voice: str = Field(default="", description="叙述者声音描述")
    pov_style: str = Field(default="", description="POV 视角风格")
    tone: str = Field(default="", description="整体基调")


class LanguageStyle(BaseModel):
    """语言风格"""
    sentence_patterns: List[str] = Field(default_factory=list, description="推荐句式")
    vocabulary_preferences: List[str] = Field(default_factory=list, description="偏好词汇")
    metaphor_style: str = Field(default="", description="比喻风格")


class RhythmStyle(BaseModel):
    """节奏风格"""
    scene_pacing: str = Field(default="", description="场景节奏描述")
    tension_patterns: List[str] = Field(default_factory=list, description="张力模式")
    short_ratio: float = Field(default=0.0, description="短段比例")
    medium_ratio: float = Field(default=0.0, description="中段比例")
    long_ratio: float = Field(default=0.0, description="长段比例")


class StyleProfile(BaseModel):
    """风格档案 — 三层架构合成结果

    Layer 1: craft_rules  — 通用写作技法
    Layer 2: voice/language/rhythm — 作品风格
    Layer 3: work_setting — 作品设定（硬性约束）
    """

    novel_id: str = Field(default="", description="小说 ID")
    style_id: str = Field(default="", description="风格模板 ID")

    # Layer 1: 通用技法
    craft_rules: List[str] = Field(default_factory=list, description="通用写作规则")

    # Layer 2: 作品风格
    voice: Optional[VoicePattern] = Field(default=None, description="叙述声音")
    language: Optional[LanguageStyle] = Field(default=None, description="语言风格")
    rhythm: Optional[RhythmStyle] = Field(default=None, description="节奏风格")

    # Layer 3: 作品设定
    work_setting: Dict[str, str] = Field(default_factory=dict, description="作品设定")

    # 禁用词
    banned_phrases: List[str] = Field(default_factory=list, description="禁用词/短语列表")

    def to_summary(self, max_chars: int = 500) -> str:
        """生成简要风格摘要"""
        parts: List[str] = []
        if self.novel_id:
            parts.append(f"作品: {self.novel_id}")
        if self.voice and self.voice.narrator_voice:
            parts.append(f"叙述: {self.voice.narrator_voice[:100]}")
        if self.language and self.language.sentence_patterns:
            parts.append(f"句式: {'、'.join(self.language.sentence_patterns[:5])}")
        if self.rhythm and self.rhythm.scene_pacing:
            parts.append(f"节奏: {self.rhythm.scene_pacing[:100]}")
        if self.banned_phrases:
            parts.append(f"禁用({len(self.banned_phrases)}): {'、'.join(self.banned_phrases[:10])}")
        if self.craft_rules:
            parts.append(f"技法({len(self.craft_rules)}): {'、'.join(self.craft_rules[:5])}")
        result = "\n".join(parts)
        return result[:max_chars] if len(result) > max_chars else result
