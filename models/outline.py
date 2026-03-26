"""大纲数据模型

提供统一的 OutlineNode + OutlineNodeType + OutlineHierarchy，
适配 opencode_skill/tools 中 context_builder / outline_parser / outline_serializer 使用的接口。
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class OutlineNodeType(str, Enum):
    """大纲节点类型"""
    MASTER = "master"
    ARC = "arc"
    SECTION = "section"
    CHAPTER = "chapter"


class OutlineNode(BaseModel):
    """统一大纲节点 — 通过 node_type 区分层级

    设计理念:
      - 篇(Arc) 承载大弧线: 整卷的起承转合与情感走向
      - 节(Section) 承载中弧线: 一段剧情的戏剧结构
      - 章(Chapter) 是最小写作单元: 只描述"这几千字写什么",
        以及它在所属节弧线中的位置(dramatic_position)
    """

    node_id: str = Field(..., description="节点 ID")
    node_type: OutlineNodeType = Field(..., description="节点类型")
    title: str = Field(default="", description="标题")
    summary: str = Field(default="", description="摘要/描述")
    parent_id: Optional[str] = Field(default=None, description="父节点 ID")
    children_ids: List[str] = Field(default_factory=list, description="子节点 ID 列表")
    status: str = Field(default="", description="状态 (TODO/WRITING/REVIEW/DONE)")

    # ── 总纲 (MASTER) 字段 ──
    core_theme: str = Field(default="", description="核心主题")
    ending_direction: str = Field(default="", description="结局走向")
    world_premise: str = Field(default="", description="世界前提")
    tone: str = Field(default="", description="基调")
    key_turns: List[str] = Field(default_factory=list, description="关键转折点")
    word_count_target: int = Field(default=0, description="目标字数")

    # ── 篇纲 (ARC) 字段 —— 大弧线 ──
    arc_structure: str = Field(
        default="",
        description="本篇起承转合结构，如 '铺垫(ch01-03) → 发展(ch04-07) → 高潮(ch08-09) → 收束(ch10)'"
    )
    arc_emotional_arc: str = Field(
        default="",
        description="本篇情感走向，如 '平静 → 紧张 → 绝望 → 重燃希望'"
    )
    arc_theme: str = Field(default="", description="本篇主题")

    # ── 节纲 (SECTION) 字段 —— 中弧线 ──
    purpose: str = Field(default="", description="节目的")
    section_structure: str = Field(
        default="",
        description="本节戏剧结构，如 '起(ch01) → 承(ch02-03) → 转(ch04) → 合(ch05)'"
    )
    section_emotional_arc: str = Field(
        default="",
        description="本节情感弧线，如 '好奇 → 震惊 → 接受'"
    )
    section_tension: str = Field(
        default="",
        description="本节张力走向，如 'low → rising → peak → falling'"
    )

    # ── 章纲 (CHAPTER) 字段 —— 最小写作单元 ──
    dramatic_position: str = Field(
        default="",
        description="本章在所属节弧线中的位置，如 '起'/'承'/'转'/'合'/'过渡'"
    )
    content_focus: str = Field(
        default="",
        description="本章内容焦点（这几千字要写什么）"
    )
    goals: List[str] = Field(default_factory=list, description="本章写作目标")
    beats: List[str] = Field(default_factory=list, description="节拍列表（章内微结构）")
    hooks: List[str] = Field(default_factory=list, description="悬念/钩子")
    involved_characters: List[str] = Field(default_factory=list, description="涉及人物")
    involved_settings: List[str] = Field(default_factory=list, description="涉及设定")
    estimated_words: int = Field(default=0, description="预估字数")
    # 章内微观情绪变化 (canonical field)
    emotional_arc: str = Field(default="", description="章内情绪变化（微观）")

    @property
    def emotion_arc(self) -> str:
        """兼容别名，统一指向 emotional_arc"""
        return self.emotional_arc


class OutlineHierarchy(BaseModel):
    """完整四级大纲层级结构"""

    novel_id: str = Field(default="", description="小说 ID")
    master: Optional[OutlineNode] = Field(default=None, description="总纲")
    arcs: List[OutlineNode] = Field(default_factory=list, description="篇纲列表")
    sections: List[OutlineNode] = Field(default_factory=list, description="节纲列表")
    chapters: List[OutlineNode] = Field(default_factory=list, description="章纲列表")

    def get_node(self, node_id: str) -> Optional[OutlineNode]:
        """根据 ID 查找任意层级的节点"""
        if self.master and self.master.node_id == node_id:
            return self.master
        for pool in (self.arcs, self.sections, self.chapters):
            for node in pool:
                if node.node_id == node_id:
                    return node
        return None

    def get_chapter_window(
        self, chapter_id: str, window_size: int = 5
    ) -> List[OutlineNode]:
        """获取目标章节前后 window_size 范围内的章节列表"""
        idx = None
        for i, ch in enumerate(self.chapters):
            if ch.node_id == chapter_id:
                idx = i
                break
        if idx is None:
            return []
        start = max(0, idx - window_size)
        end = min(len(self.chapters), idx + window_size + 1)
        return self.chapters[start:end]

    def get_chapters_by_arc(self, arc_id: str) -> List[OutlineNode]:
        """获取某篇下所有章节"""
        arc = None
        for a in self.arcs:
            if a.node_id == arc_id:
                arc = a
                break
        if not arc:
            return []
        return [ch for ch in self.chapters if ch.node_id in arc.children_ids]

    def get_parent_section(self, chapter_id: str) -> Optional[OutlineNode]:
        """获取章节所属的节"""
        for sec in self.sections:
            if chapter_id in sec.children_ids:
                return sec
        # fallback: 通过 parent_id
        ch = self.get_node(chapter_id)
        if ch and ch.parent_id:
            return self.get_node(ch.parent_id)
        return None

    def get_parent_arc(self, chapter_id: str) -> Optional[OutlineNode]:
        """获取章节所属的篇"""
        # 先找节，再找节的父篇
        section = self.get_parent_section(chapter_id)
        if section:
            for arc in self.arcs:
                if section.node_id in arc.children_ids:
                    return arc
                if section.parent_id == arc.node_id:
                    return arc
        # fallback: 直接看哪个 arc 包含此章
        for arc in self.arcs:
            if chapter_id in arc.children_ids:
                return arc
        return None

    def get_dramatic_context(self, chapter_id: str) -> Dict[str, str]:
        """获取章节的完整戏剧位置上下文

        返回该章在节弧线和篇弧线中的位置信息，
        供 LLM 理解"这一章应该写出什么感觉"。

        Returns:
            {
                "section_structure": "起(ch01) → 承(ch02-03) → 转(ch04) → 合(ch05)",
                "section_emotional_arc": "好奇 → 震惊 → 接受",
                "dramatic_position": "转",
                "arc_structure": "铺垫 → 发展 → 高潮 → 收束",
                "arc_emotional_arc": "平静 → 紧张 → 绝望 → 重燃希望",
                "content_focus": "主角发现真相，内心崩溃",
            }
        """
        result: Dict[str, str] = {}

        ch = self.get_node(chapter_id)
        if ch:
            if ch.dramatic_position:
                result["dramatic_position"] = ch.dramatic_position
            if ch.content_focus:
                result["content_focus"] = ch.content_focus

        section = self.get_parent_section(chapter_id)
        if section:
            if section.section_structure:
                result["section_structure"] = section.section_structure
            if section.section_emotional_arc:
                result["section_emotional_arc"] = section.section_emotional_arc
            if section.section_tension:
                result["section_tension"] = section.section_tension

        arc = self.get_parent_arc(chapter_id)
        if arc:
            if arc.arc_structure:
                result["arc_structure"] = arc.arc_structure
            if arc.arc_emotional_arc:
                result["arc_emotional_arc"] = arc.arc_emotional_arc

        return result
