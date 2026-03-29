# Sync 责任矩阵（src -> data）

本文档定义 OpenWrite 的同步边界，避免“改了 A 不知道 B 要不要更新”。

## 核心原则

- src 是 source of truth（人类编辑）。
- data 是运行态与派生文件（机器消费/生成）。
- 默认单向同步：src -> data。

## 同步矩阵

| 领域 | 源文件（src） | 目标文件（data） | 同步方式 | 是否自动回写 src |
|---|---|---|---|---|
| 大纲 | src/outline.md | data/hierarchy.yaml | outline_sync | 否 |
| 角色 | src/characters/*.md | data/characters/cards/*.yaml | character_sync | 否 |
| 世界设定 | src/world/*.md | （上下文读取，不生成镜像） | 直接读取 src | 否 |
| 世界当前状态 | （剧情运行产生） | data/world/current_state.md | writer/director 落盘 | 否 |
| 资源账本 | （剧情运行产生） | data/world/ledger.md | writer/director 落盘 | 否 |
| 角色关系 | （剧情运行产生） | data/world/relationships.md | writer/director 落盘 | 否 |
| 伏笔状态 | （剧情运行产生） | data/foreshadowing/dag.yaml | foreshadowing manager | 否 |

## 命令

- 仅检查：
  - `openwrite sync --check`
- 执行同步：
  - `openwrite sync`

## 建议流程

1. 改了 `src/outline.md` 或 `src/characters/*.md` 后先执行 `openwrite sync --check`。
2. 若提示未同步，再执行 `openwrite sync`。
3. 写作前可执行 `openwrite doctor` 与 `openwrite assemble ch_xxx --format markdown` 快速确认上下文。

## 常见误解

- “data/world/* 要不要同步回 src/world/*？”
  - 不需要。两者职责不同：src 是规则与设定，data 是剧情后的当前状态。
- “角色卡片和角色档案谁是准？”
  - 档案（src）是准；卡片（data）是派生视图。
