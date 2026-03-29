# OpenWrite Structure Convergence And Pruning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify what humans edit and what agents read, remove redundant legacy files and duplicate paths, and keep all current writing functionality intact.

**Architecture:** Keep `src/` as the only human-maintained source domain and `data/` as the only runtime/derived domain. Add stricter sync/preflight gates, make all write/read pipelines consume the same canonical state fields, then delete redundant sample artifacts and misleading legacy path assumptions.

**Tech Stack:** Python 3, argparse CLI, Markdown/YAML file stores, existing `tools.*`, `pytest`

---

### Task 1: Freeze the canonical file contract

**Files:**
- Modify: `README.md`
- Modify: `docs/SYNC_MATRIX.md`
- Modify: `docs/MIGRATION_GUIDE.md`
- Create: `docs/STRUCTURE_CONTRACT.md`

**Step 1: Write the failing doc/contract checklist**

Document the exact canonical contract:
- Human-authored: `src/outline.md`, `src/characters/*.md`, `src/world/*.md`, `src/world/entities/*.md`
- Derived/runtime: `data/hierarchy.yaml`, `data/characters/cards/*.yaml`, `data/world/current_state.md`, `data/world/ledger.md`, `data/world/relationships.md`, `data/foreshadowing/dag.yaml`, `data/manuscript/**`, `data/workflows/**`
- Canonical truth field names: `current_state`, `ledger`, `relationships`

**Step 2: Verify current docs disagree**

Run: `rg -n "particle_ledger|character_matrix|ReAct Agent|outline/|manuscript/|workflows/" README.md docs tools`

Expected:
- old field names still appear
- old structure language still appears
- `README` still mismatches the current intended architecture

**Step 3: Write minimal doc changes**

Update docs so they all say the same thing:
- `src` is human-facing source of truth
- `data` is derived/runtime only
- `openwrite agent` is the primary orchestrator entry once implementation is switched over
- legacy field names are compatibility-only, not author-facing API

**Step 4: Verify doc consistency**

Run: `rg -n "particle_ledger|character_matrix|ReAct Agent" README.md docs`

Expected:
- only compatibility notes remain, if any

**Step 5: Commit**

```bash
git add README.md docs/SYNC_MATRIX.md docs/MIGRATION_GUIDE.md docs/STRUCTURE_CONTRACT.md
git commit -m "docs: define canonical structure contract"
```

### Task 2: Fix the wrong runtime state source in multi-agent writing

**Files:**
- Modify: `tools/agent/director.py`
- Modify: `tools/chapter_assembler.py`
- Test: `tests/test_agent_director.py`

**Step 1: Write the failing test**

Add a test proving the multi-agent director passes runtime `current_state` to writer/reviewer instead of static `world.rules`.

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_agent_director.py -q`

Expected: FAIL because `current_state` is currently pulled from `packet.concept_documents["world.rules"]`

**Step 3: Write minimal implementation**

Refactor packet assembly so runtime truth files are explicit first-class packet fields:
- `packet.current_state`
- `packet.ledger`
- `packet.relationships`

Then update `MultiAgentDirector.run()` to pass those fields to writer/reviewer.

**Step 4: Run targeted tests**

Run: `python3 -m pytest tests/test_agent_director.py tests/test_context_schema.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add tools/agent/director.py tools/chapter_assembler.py tests/test_agent_director.py
git commit -m "fix: use runtime truth state in multi-agent writing"
```

### Task 3: Turn sync into a real freshness gate

**Files:**
- Modify: `tools/cli.py`
- Modify: `tools/context_builder.py`
- Modify: `tools/chapter_assembler.py`
- Test: `tests/test_cli_sync.py`
- Test: `tests/test_context_builder.py`

**Step 1: Write the failing tests**

Add tests for:
- changed `src/characters/*.md` should mark sync pending even when card exists
- changed `src/outline.md` should block stale read paths until sync or auto-refresh
- context assembly should not silently use stale derived files

**Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/test_cli_sync.py tests/test_context_builder.py -q`

Expected: FAIL on stale-character-card and stale-outline cases

**Step 3: Write minimal implementation**

Implement one freshness policy only:
- compare source vs derived freshness for outline and character cards
- preflight paths (`context`, `assemble`, `multi-write`, `agent`) must either auto-sync or explicitly fail with a clear message

Do not add bidirectional sync.

**Step 4: Run targeted tests**

Run: `python3 -m pytest tests/test_cli_sync.py tests/test_context_builder.py tests/test_integration.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add tools/cli.py tools/context_builder.py tools/chapter_assembler.py tests/test_cli_sync.py tests/test_context_builder.py tests/test_integration.py
git commit -m "feat: enforce source freshness before runtime reads"
```

### Task 4: Collapse truth field naming to one public vocabulary

**Files:**
- Modify: `tools/context_schema.py`
- Modify: `models/context_package.py`
- Modify: `tools/truth_manager.py`
- Modify: `tools/agent/react.py`
- Modify: `tools/cli.py`
- Test: `tests/test_context_schema.py`
- Test: `tests/test_cli_helpers.py`

**Step 1: Write the failing tests**

Add tests asserting:
- public payloads use `current_state`, `ledger`, `relationships`
- legacy names are still accepted at adapters only
- user-facing tool descriptions no longer advertise legacy names

**Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/test_context_schema.py tests/test_cli_helpers.py -q`

Expected: FAIL because public APIs still export legacy names

**Step 3: Write minimal implementation**

Keep compatibility internally, but change public surfaces:
- prompt/context payloads
- tool schemas
- status/update helpers
- docs/examples

Legacy aliases should remain only at normalization boundaries.

**Step 4: Run targeted tests**

Run: `python3 -m pytest tests/test_context_schema.py tests/test_cli_helpers.py tests/test_visualization.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add tools/context_schema.py models/context_package.py tools/truth_manager.py tools/agent/react.py tools/cli.py tests/test_context_schema.py tests/test_cli_helpers.py
git commit -m "refactor: standardize public truth field names"
```

### Task 5: Remove legacy path fallbacks from active code

**Files:**
- Modify: `tools/context_builder.py`
- Modify: `tools/wizard.py`
- Modify: `tools/init_project.py`
- Test: `tests/test_integration.py`
- Test: `tests/test_visualization.py`

**Step 1: Write the failing tests**

Add tests proving active code no longer reads:
- `data/world/rules.md` as a fallback for `src/world/rules.md`
- `data/characters/profiles/*.md` as a fallback for `src/characters/*.md`
- old root-level `outline/`, `manuscript/`, `style/`, `workflows/`

**Step 2: Run tests to verify failure**

Run: `python3 -m pytest tests/test_integration.py tests/test_visualization.py -q`

Expected: FAIL where old fallbacks are still accepted

**Step 3: Write minimal implementation**

Delete only active-code fallbacks that can cause divergent reads.
Keep compatibility adapters only where migration truly requires them and document each one.

**Step 4: Run targeted tests**

Run: `python3 -m pytest tests/test_integration.py tests/test_visualization.py tests/test_world_query.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add tools/context_builder.py tools/wizard.py tools/init_project.py tests/test_integration.py tests/test_visualization.py
git commit -m "refactor: remove legacy path fallbacks from active code"
```

### Task 6: Prune redundant sample artifacts and dead duplicates

**Files:**
- Delete: `data/novels/test_novel/workflows/wf_ch_integ_001.yaml`
- Delete: empty legacy directories under `data/novels/test_novel/`
- Review: `data/novels/test_novel/compressed/`
- Review: `data/novels/test_novel/style/`
- Review: `data/novels/test_novel/manuscript/`
- Modify: `.gitignore`
- Modify: `docs/CLEANUP_REPORT.md`

**Step 1: Write the failing audit checklist**

Create a concrete list of files/directories that are redundant because:
- exact duplicate already exists under `data/`
- legacy root path is no longer read by active code
- runtime smoke artifacts should not live in the sample fixture

**Step 2: Verify each candidate is truly unused**

Run:
- `rg -n "wf_ch_integ_001|data/novels/test_novel/workflows|data/novels/test_novel/manuscript|data/novels/test_novel/style|data/novels/test_novel/world" tools tests docs README.md`
- inspect any remaining references manually

Expected:
- only docs/cleanup references or no live code references remain

**Step 3: Delete minimal redundant artifacts**

Remove duplicates and empty shells only after confirming live code does not read them.
Do not delete canonical sample files under `src/` or `data/` that tests still need.

**Step 4: Verify repo tree is cleaner**

Run:
- `find data/novels/test_novel -maxdepth 3 \\( -type d -o -type f \\) | sort`
- `git status --short`

Expected:
- no duplicated old/new workflow files
- no misleading legacy shells kept for no reason

**Step 5: Commit**

```bash
git add .gitignore docs/CLEANUP_REPORT.md data/novels/test_novel
git commit -m "chore: prune redundant sample runtime artifacts"
```

### Task 7: Audit generated-but-unused foundation files

**Files:**
- Modify: `tools/wizard.py`
- Modify: `tools/architect.py`
- Modify: `tools/context_builder.py`
- Modify: `tools/chapter_assembler.py`
- Modify: `docs/MANUAL_TEST_PLAYBOOK.md`
- Test: `tests/test_wizard.py`

**Step 1: Write the failing test or audit assertion**

Decide for each generated file:
- `src/world/story_bible.md`
- `src/world/volume_outline.md`
- `src/world/book_rules.md`
- `data/foreshadowing/hooks_seed.md`

Either:
- wire it into a real read path, or
- stop generating it, or
- mark it as user-reference-only with no runtime promise

**Step 2: Run test/audit to verify mismatch**

Run: `rg -n "story_bible|volume_outline|book_rules|hooks_seed" tools tests docs`

Expected:
- generation paths exist
- consumption paths are incomplete or absent

**Step 3: Write minimal implementation**

Pick one strategy only:
- If the file matters at runtime, integrate it into packet/context assembly.
- If it is reference-only, document it and keep it out of runtime expectations.
- If it is dead, stop generating it.

**Step 4: Run targeted verification**

Run: `python3 -m pytest tests/test_wizard.py tests/test_integration.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add tools/wizard.py tools/architect.py tools/context_builder.py tools/chapter_assembler.py docs/MANUAL_TEST_PLAYBOOK.md tests/test_wizard.py
git commit -m "refactor: clarify foundation file lifecycle"
```

### Task 8: Final full verification and operator notes

**Files:**
- Modify: `README.md`
- Modify: `docs/SYNC_MATRIX.md`
- Modify: `docs/CLEANUP_REPORT.md`

**Step 1: Run full verification**

Run: `python3 -m pytest -q`

Expected: PASS with zero failures

**Step 2: Run smoke checks**

Run:
- `python3 -m tools.cli sync --check`
- `python3 -m tools.cli context ch_001`
- `python3 -m tools.cli multi-write ch_001`

Expected:
- sync output is clear
- context output reflects canonical fields and canonical paths
- multi-write uses the same runtime truth state as single-write path

**Step 3: Update operator notes**

Document:
- when sync is automatic vs required
- what files humans should edit
- what files agents will mutate
- what legacy files were removed

**Step 4: Commit**

```bash
git add README.md docs/SYNC_MATRIX.md docs/CLEANUP_REPORT.md
git commit -m "docs: finalize structure and pruning guidance"
```
