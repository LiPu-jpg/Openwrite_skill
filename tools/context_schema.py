"""上下文/状态字段规范化。

目标：
1. 统一对外的 canonical 命名
2. 兼容历史别名，避免一次性重构导致链路断裂
"""

from __future__ import annotations

from typing import Dict, Any


# canonical -> aliases
TRUTH_FILE_ALIASES: Dict[str, tuple[str, ...]] = {
    "current_state": ("current_state",),
    "ledger": ("ledger", "particle_ledger"),
    "relationships": ("relationships", "character_matrix"),
}


def normalize_truth_file_key(key: str) -> str:
    """将输入键归一化到 canonical 键名。

    未知键会原样返回，由上层决定是否接受。
    """
    for canonical, aliases in TRUTH_FILE_ALIASES.items():
        if key in aliases:
            return canonical
    return key


def normalize_context_payload(payload: Dict[str, Any], include_aliases: bool = True) -> Dict[str, Any]:
    """规范化上下文字段。

    canonical:
    - current_state
    - ledger
    - relationships
    - foreshadowing_summary

    兼容历史字段：
    - particle_ledger
    - character_matrix
    - pending_hooks
    """
    out = dict(payload)

    # Canonicalize from legacy keys when canonical missing.
    if "ledger" not in out and "particle_ledger" in out:
        out["ledger"] = out.get("particle_ledger")
    if "relationships" not in out and "character_matrix" in out:
        out["relationships"] = out.get("character_matrix")
    if "foreshadowing_summary" not in out and "pending_hooks" in out:
        out["foreshadowing_summary"] = out.get("pending_hooks")

    if include_aliases:
        # Re-export legacy aliases so旧链路继续可用。
        if "particle_ledger" not in out and "ledger" in out:
            out["particle_ledger"] = out.get("ledger")
        if "character_matrix" not in out and "relationships" in out:
            out["character_matrix"] = out.get("relationships")
        if "pending_hooks" not in out and "foreshadowing_summary" in out:
            out["pending_hooks"] = out.get("foreshadowing_summary")

    return out
