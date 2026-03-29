# OpenWrite Single-Source Front Matter Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce a single-source document format for character and world-entity files using TOML front matter plus Markdown body, while keeping runtime caches and current features working.

**Architecture:** Add a reusable front matter parser, teach character/entity readers to consume the new format first, and keep old plain Markdown parsing as a compatibility fallback. Derived YAML cards remain caches generated from the same source document.

**Tech Stack:** Python 3.14, `tomllib`, Markdown parsing helpers, argparse-based tools, `pytest`

---

### Task 1: Add reusable TOML front matter parsing

**Files:**
- Create: `tools/frontmatter.py`
- Test: `tests/test_frontmatter.py`

**Step 1: Write the failing test**

Add tests for:
- valid `+++ ... +++` TOML front matter extraction
- no front matter returns empty metadata + full body
- malformed front matter fails closed instead of crashing readers

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_frontmatter.py`

Expected: FAIL because parser module does not exist

**Step 3: Write minimal implementation**

Implement:
- `parse_toml_front_matter(text: str) -> tuple[dict, str]`
- `has_toml_front_matter(text: str) -> bool`

Use `tomllib` only. Do not add third-party dependencies.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_frontmatter.py`

Expected: PASS

### Task 2: Make character documents single-source capable

**Files:**
- Modify: `models/character.py`
- Modify: `tools/context_builder.py`
- Modify: `tools/character_sync.py`
- Test: `tests/test_character_sync.py`
- Test: `tests/test_context_builder.py`

**Step 1: Write the failing tests**

Add tests proving:
- `ContextBuilder` can parse character metadata from TOML front matter
- `sync_all_profiles_to_cards()` can generate card YAML from the same source file
- old Markdown-only character docs still work

**Step 2: Run tests to verify they fail**

Run: `python3 -m pytest -q tests/test_character_sync.py tests/test_context_builder.py`

Expected: FAIL on new front matter fixtures

**Step 3: Write minimal implementation**

Implement support for:
- `summary`
- `tier`
- `tags`
- `detail_refs`
- `related`

Character context should prefer:
- front matter summary/tier when present
- Markdown sections for detailed body fields

Keep old parsing as fallback.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_character_sync.py tests/test_context_builder.py`

Expected: PASS

### Task 3: Make world entity documents single-source capable

**Files:**
- Modify: `tools/world_query.py`
- Test: `tests/test_world_query.py`

**Step 1: Write the failing test**

Add tests proving:
- entity TOML front matter fields (`type`, `subtype`, `status`, `summary`, `tags`, `related`) are parsed
- Markdown body sections remain available
- old entity Markdown still works

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_world_query.py`

Expected: FAIL on front matter entity fixture

**Step 3: Write minimal implementation**

`parse_entity()` should:
- prefer front matter metadata when present
- fall back to old blockquote/section parsing when absent
- normalize `related` into existing relation graph shape

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_world_query.py`

Expected: PASS

### Task 4: Migrate sample documents to prove the new format

**Files:**
- Modify: `data/novels/test_novel/src/characters/*.md`
- Modify: `data/novels/test_novel/src/world/entities/*.md`
- Optional docs note: `README.md`

**Step 1: Update sample character/entity files**

Add TOML front matter to sample docs without deleting Markdown body detail.

**Step 2: Run verification**

Run:
- `python3 -m pytest -q tests/test_character_sync.py tests/test_context_builder.py tests/test_world_query.py`
- `python3 -m tools.cli context ch_001`

Expected:
- tests PASS
- context command still works

### Task 5: Full regression and rollout note

**Files:**
- Optional docs: `README.md`

**Step 1: Run full regression**

Run: `python3 -m pytest -q`

Expected: PASS

**Step 2: Summarize remaining non-MVP work**

Document follow-ups:
- `outline.md` front matter upgrade
- `src/world/*.md` shared-source upgrade
- character/entity detail lookup tool if needed
