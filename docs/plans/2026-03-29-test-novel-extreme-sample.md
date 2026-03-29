# Test Novel Extreme Sample Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 `data/novels/test_novel` 升级成当前结构下的标准长篇样例项目。

**Architecture:** 使用“确认版真源 + 长线草案 + 运行态样例”三层结构。`src/` 保持当前 agent 能直接消费的确认版上下文，`data/planning/` 承载 400+ 章长线规划，`data/world/workflows/manuscript` 展示真实连载态。

**Tech Stack:** Markdown, TOML front matter, YAML runtime state, pytest

---

### Task 1: 锁定标准样例验收测试

**Files:**
- Create: `tests/test_standard_test_novel_fixture.py`

1. 写标准样例测试，覆盖 story、outline、planning、world、manuscript、style、workflow。
2. 运行 `python3 -m pytest -q tests/test_standard_test_novel_fixture.py`，确认先失败。

### Task 2: 重写 story 与 planning 真源

**Files:**
- Modify: `data/novels/test_novel/src/story/background.md`
- Modify: `data/novels/test_novel/src/story/foundation.md`
- Modify: `data/novels/test_novel/data/planning/background_draft.md`
- Modify: `data/novels/test_novel/data/planning/foundation_draft.md`
- Modify: `data/novels/test_novel/data/planning/outline_draft.md`
- Modify: `data/novels/test_novel/data/planning/ideation.md`

1. 写确认版背景和基础设定。
2. 写完整长篇骨架草案，明确 3 篇、420-520 章规划。

### Task 3: 扩充确认版 outline 与世界设定

**Files:**
- Modify: `data/novels/test_novel/src/outline.md`
- Modify: `data/novels/test_novel/src/world/rules.md`
- Modify: `data/novels/test_novel/src/world/terminology.md`
- Modify: `data/novels/test_novel/src/world/timeline.md`
- Modify/Create: `data/novels/test_novel/src/world/entities/*.md`

1. 将确认版 outline 扩到 20+ 章。
2. 统一世界规则、术语、时间线和实体索引格式。

### Task 4: 对齐运行态与手稿

**Files:**
- Modify: `data/novels/test_novel/data/world/current_state.md`
- Modify: `data/novels/test_novel/data/world/ledger.md`
- Modify: `data/novels/test_novel/data/world/relationships.md`
- Modify/Create: `data/novels/test_novel/data/manuscript/**/*.md`
- Modify: `data/novels/test_novel/data/foreshadowing/dag.yaml`

1. 让 truth files 与前 6-8 章已写内容一致。
2. 补齐短章或新增章节，使样例手稿可演示。

### Task 5: 对齐 workflow 与 style

**Files:**
- Modify: `data/novels/test_novel/data/workflows/*.yaml`
- Modify: `data/novels/test_novel/data/style/composed.md`
- Modify: `data/novels/test_novel/data/style/fingerprint.yaml`

1. 统一章节工作流时间线和当前书级状态。
2. 让 style fingerprint 不再是占位值。

### Task 6: 刷新派生缓存并全量验证

**Files:**
- Modify: `data/novels/test_novel/data/hierarchy.yaml`
- Modify: `data/novels/test_novel/data/characters/cards/*.yaml`

1. 从 `src` 刷新 hierarchy 和角色卡。
2. 跑 `python3 -m pytest -q tests/test_standard_test_novel_fixture.py`
3. 跑 `python3 -m pytest -q`
