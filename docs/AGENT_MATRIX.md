# Agent 规划与权限矩阵

本文档定义 OpenWrite 的最小必要 Agent、冗余 Agent、以及权限边界。

## 必要 Agent（默认启用）

1. director
- 职责：流程编排、阶段门禁、质量裁决
- 价值：避免 writer 直接越权改设定

2. context_engineer
- 职责：组装本章上下文包（背景、篇梗概、节梗概、上一章、角色、风格、概念）
- 价值：把“事实组装”从“创作”中拆开，降低幻觉风险

3. writer
- 职责：生成新章节正文（默认 4k 目标）
- 价值：专注生成，不改世界状态源文件

4. continuity_reviewer
- 职责：连续性、逻辑、风格审查
- 价值：把校验与生成分离，保障稳定

5. state_settler
- 职责：把本章事实写入状态文件（current_state/ledger/relationships）
- 价值：持续维护主角状态与关系变化

6. concept_curator
- 职责：识别新概念并创建概念文档骨架
- 价值：避免“正文出现新术语，文档缺失”

## 冗余 Agent（默认不启用）

1. style_polisher
- 原因：可由 writer + reviewer 联合覆盖

2. hook_manager
- 原因：可并入 state_settler

3. world_architect
- 原因：高风险大改，建议人工触发

## 权限边界（原则）

1. writer 不能直接修改 world/characters/outline
2. reviewer 只能产出报告，不能直接改正文与设定
3. state_settler 只写运行时状态文件
4. concept_curator 只写 src/world/entities 与术语表
5. director 只做决策，不直接改业务文件

## 路径约定（仅新结构）

- source of truth: data/novels/{novel_id}/src
- runtime: data/novels/{novel_id}/data

## 当前实现

- 权限策略：tools/agent_policy.py
- 上下文组装：tools/chapter_assembler.py
- 编排入口：tools/agent/director.py
- CLI 命令：tools/cli.py -> multi-write / assemble
