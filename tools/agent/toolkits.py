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
    "record_ideation",
    "summarize_ideation",
    "confirm_ideation_summary",
    "generate_foundation_draft",
    "confirm_foundation",
    "generate_outline_draft",
    "confirm_outline_scope",
    "run_chapter_preflight",
    "delegate_chapter_write",
    "delegate_chapter_review",
    "advance_book_state",
    "resume_session",
}
