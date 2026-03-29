# Test Novel Extreme Sample Design

**Goal:** 将 `data/novels/test_novel` 升级为一套“人和 AI 共读、可演示完整 agent 流程、同时具备长篇规划骨架”的标准样例小说。

## Design

- `src/` 只放确认版、当前可写范围内的真源文档。
- `data/planning/` 放完整长篇骨架和未确认草案，用来展示“滚动大纲 + 长线规划”并存。
- `data/world/`、`data/workflows/`、`data/manuscript/` 展示当前连载态，而不是空白初始化态。
- 所有长期可读文档统一为 `TOML front matter + Markdown body`，让人和 AI 都看同一份源。

## Scope

- 故事方向延续现有《公司里的术师》现代都市职场异能设定。
- `src/outline.md` 确认前 20+ 章的章节级细纲，供当前上下文组装直接消费。
- `data/planning/outline_draft.md` 保存 3 篇、420-520 章量级的长篇骨架草案。
- 至少 6 章手稿、8 个世界实体、完整 truth files、style、foreshadowing 与 workflow 样例。

## Constraints

- 保持 `ch_001`、陈明、赵磊、林月等现有样例心智不被推翻。
- 不引入“人看一套、AI 看一套”的双源结构。
- 尽量复用现有长正文，避免无意义膨胀仓库。
