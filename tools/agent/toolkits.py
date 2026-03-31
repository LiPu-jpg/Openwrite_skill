"""OpenWrite agent 工具分组。"""

from __future__ import annotations

ORCHESTRATOR_TOOLKIT = {
    "get_status",
    "get_context",
    "list_chapters",
    "get_truth_files",
    "create_character",
    "query_world",
    "get_world_relations",
    "review_chapter",
    "get_workflow_status",
    "start_workflow",
    "advance_workflow",
}

WRITING_TOOLKIT = {
    "write_chapter",
    "get_context",
    "list_chapters",
    "get_truth_files",
}

DANTE_DIRECT_TOOLKIT = {
    "get_status",
    "get_context",
    "list_chapters",
    "get_truth_files",
    "query_world",
    "get_world_relations",
}

DANTE_ACTION_TOOLKIT = {
    "summarize_ideation",
    "confirm_ideation_summary",
    "generate_outline_draft",
    "run_chapter_preflight",
    "delegate_chapter_write",
    "delegate_chapter_review",
}

GOETHE_DIRECT_TOOLKIT = {
    "get_status",
    "get_context",
    "list_chapters",
    "get_truth_files",
    "query_world",
    "get_world_relations",
}

GOETHE_ACTION_TOOLKIT = {
    "summarize_ideation",
    "generate_foundation_draft",
    "generate_character_draft",
    "generate_outline_draft",
    "extract_style_source",
    "extract_setting_source",
    "review_source_pack",
    "promote_source_pack",
    "prepare_dante_handoff",
}
