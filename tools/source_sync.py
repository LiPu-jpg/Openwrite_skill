"""Shared source/runtime sync freshness helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def collect_sync_status(project_root: Path, novel_id: str) -> Dict[str, Any]:
    """Collect freshness status between ``src`` and derived ``data`` files."""
    novel_root = Path(project_root) / "data" / "novels" / novel_id
    src_root = novel_root / "src"
    data_root = novel_root / "data"

    outline_src = src_root / "outline.md"
    hierarchy = data_root / "hierarchy.yaml"

    outline_pending = False
    if outline_src.exists():
        outline_pending = (not hierarchy.exists()) or (
            hierarchy.exists() and outline_src.stat().st_mtime > hierarchy.stat().st_mtime
        )

    profiles_dir = src_root / "characters"
    cards_dir = data_root / "characters" / "cards"
    profile_paths = {p.stem: p for p in profiles_dir.glob("*.md")} if profiles_dir.exists() else {}
    card_paths = {p.stem: p for p in cards_dir.glob("*.yaml")} if cards_dir.exists() else {}

    profile_stems = set(profile_paths)
    card_stems = set(card_paths)
    missing_cards = sorted(profile_stems - card_stems)
    extra_cards = sorted(card_stems - profile_stems)
    stale_cards = sorted(
        stem
        for stem in sorted(profile_stems & card_stems)
        if profile_paths[stem].stat().st_mtime > card_paths[stem].stat().st_mtime
    )

    return {
        "novel_id": novel_id,
        "outline_pending": outline_pending,
        "profiles": len(profile_stems),
        "cards": len(card_stems),
        "missing_cards": missing_cards,
        "extra_cards": extra_cards,
        "stale_cards": stale_cards,
        "needs_sync": outline_pending or bool(missing_cards) or bool(stale_cards),
    }


def run_sync(
    project_root: Path,
    novel_id: str,
    *,
    sync_outline: bool = True,
    sync_characters: bool = True,
) -> None:
    """Execute src -> data synchronization."""
    from tools.outline_sync import sync_outline_to_hierarchy
    from tools.character_sync import sync_all_profiles_to_cards

    novel_root = Path(project_root) / "data" / "novels" / novel_id
    src_root = novel_root / "src"
    data_root = novel_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)

    outline_src = src_root / "outline.md"
    if sync_outline and outline_src.exists():
        sync_outline_to_hierarchy(src_root, data_root)

    if sync_characters:
        sync_all_profiles_to_cards(src_root, data_root)


def ensure_runtime_fresh(project_root: Path, novel_id: str) -> Dict[str, Any]:
    """Auto-sync stale derived files before runtime readers consume them.

    Returns the final status and whether an auto-sync occurred.
    Raises RuntimeError when files are still stale after attempting sync.
    """
    before = collect_sync_status(project_root, novel_id)
    if not before["needs_sync"]:
        return {**before, "auto_synced": False}

    run_sync(
        project_root,
        novel_id,
        sync_outline=before["outline_pending"],
        sync_characters=bool(before["missing_cards"] or before["stale_cards"]),
    )
    after = collect_sync_status(project_root, novel_id)
    if after["needs_sync"]:
        raise RuntimeError(
            "检测到未同步或格式异常的源文件，请先运行 `openwrite sync --check` 排查后再继续。"
        )
    return {**after, "auto_synced": True}
