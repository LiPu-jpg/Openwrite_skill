# 项目整理报告（2026-03-27）

## 目标
- 统一文档路径到新结构：`data/novels/{id}/src` + `data/novels/{id}/data`
- 清理样例中的一次性生成文件，降低目录噪音
- 防止测试快照持续污染变更列表

## 本次已完成

### 1) 文档路径统一
- 已更新 `README.md` 中角色卡、角色档、世界实体、伏笔、FAQ 路径示例。
- 已更新 `SKILL.md` 中三层风格与上下文组装路径说明。
- 已更新 `docs/MIGRATION_GUIDE.md` 的路径映射表。
- 已更新 `skills/novel-creator/SKILL.md` 的写入路径、前置条件与文件访问表。
- 已更新 `skills/novel-manager/SKILL.md` 的目录树与文件访问表。

### 2) 样例数据瘦身（test_novel）
- 删除草稿副本：`data/manuscript/arc_001/ch_001_draft.md`
- 删除审查副本：`data/manuscript/arc_001/ch_001_review.yaml`
- 删除一次性集成工作流文件：`data/workflows/wf_ch_integ_001.yaml`

### 3) 噪音预防
- 在 `.gitignore` 新增：`data/novels/*/data/test_outputs/`
- 作用：避免上下文快照等测试输出频繁进入版本变更。

## 当前残留与说明
- `data/novels/test_novel/` 根下仍有若干空旧目录壳（如 `manuscript/`, `style/`, `workflows/` 等）。
- 这些目录目前不影响运行。
- 本会话环境策略拦截 `rm/rmdir`，因此目录级删除未执行；文件级清理已完成。

## 建议后续
1. 在本地允许目录删除的环境执行一次空目录清扫。
2. 按需继续清理 `skills/` 里少量旧路径文案（不影响运行，但会影响新同学理解）。
3. 把本报告作为后续“目录治理”的基线文档，后续变更可按章节增量维护。
