"""OpenWrite 数据模型包

为 opencode_skill/tools/ 提供统一的 Pydantic 数据模型。
"""

from .outline import OutlineNode, OutlineNodeType, OutlineHierarchy
from .character import CharacterCard, CharacterProfile, CharacterTier
from .style import StyleProfile, VoicePattern, LanguageStyle, RhythmStyle
from .context_package import GenerationContext, ForeshadowingState, WorldRules
from .foreshadowing import ForeshadowingNode, ForeshadowingEdge, ForeshadowingGraph

__all__ = [
    "OutlineNode", "OutlineNodeType", "OutlineHierarchy",
    "CharacterCard", "CharacterProfile", "CharacterTier",
    "StyleProfile", "VoicePattern", "LanguageStyle", "RhythmStyle",
    "GenerationContext", "ForeshadowingState", "WorldRules",
    "ForeshadowingNode", "ForeshadowingEdge", "ForeshadowingGraph",
]
