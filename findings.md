# Findings: InkOS → OpenWrite 融合

## InkOS 核心优势（需要迁移）

### 1. LLM Provider 封装 (packages/core/src/llm/provider.ts)
- 统一接口支持 OpenAI / Anthropic
- 流式输出监控 (createStreamMonitor)
- 流失败自动降级为同步
- 人性化错误包装 (wrapLLMError)
- 支持 responses API 和 chat API

### 2. BaseAgent 架构 (packages/core/src/agents/base.ts)
- 统一 chat() / chatWithSearch() 方法
- AgentContext 传递 client、model、logger
- 抽象基类，具体 Agent 继承实现

### 3. WriterAgent 两阶段写作 (packages/core/src/agents/writer.ts)
- Phase 1: 创意写作 (temperature=0.7)
- Phase 2: 状态结算
  - 2a. Observer: 提取本章事实
  - 2b. Settler: 合并到真相文件

### 4. 33维度连续性审计 (packages/core/src/agents/continuity.ts)
- DIM 1-19: 逻辑类 (OOC、时间线、战力等)
- DIM 20-23: AI痕迹类 (段落等长、套话密度等)
- DIM 24-37: 高级审计类

### 5. AI痕迹检测 (packages/core/src/agents/ai-tells.ts)
- 段落长度变异系数检测 (cv < 0.15)
- 套话词密度检测 (>3次/千字)
- 公式化转折词重复检测 (≥3次)
- 列表式结构检测

### 6. 7个真相文件
- current_state.md - 世界状态
- ledger.md - 资源账本
- relationships.md - 角色关系矩阵
- foreshadowing/dag.yaml - 伏笔状态
- hierarchy.yaml + compressed/* - 章节摘要
- subplot_board.md - 支线进度
- emotional_arcs.md - 情感弧线
- character_matrix.md - 角色关系矩阵

### 7. 状态快照机制
- 每次写章节前快照
- 支持回滚到任意快照点

## OpenWrite 现有优势（保持）

### 1. 四级大纲架构
- Master → Arc → Section → Chapter
- OutlineHierarchy 模型完整

### 2. 渐进式压缩
- 章 → 节 → 篇 三级压缩
- token 预算管理

### 3. 参考风格库
- 6部参考小说风格文档
- style_extraction_pipeline.py

### 4. 世界观查询
- world_query.py 实体/关系图谱

### 5. 伏笔 DAG
- foreshadowing_manager.py
- 环检测、依赖管理

## 融合策略

### 需要新建的模块
1. tools/llm/ - LLM 客户端封装 ✅
2. tools/agent/ - Agent 基类和实现 ✅
3. tools/truth_manager.py - 真相文件管理 ✅
4. tools/post_validator.py - 后置验证（新增）✅
5. tools/state_validator.py - 状态验证（新增）✅
6. tools/dialogue_fingerprint.py - 对话指纹（新增）✅

### 需要修改的模块
1. tools/context_builder.py - 融合真相文件 ✅
2. models/context_package.py - 添加真相文件字段 ✅
3. skills/novel-creator/SKILL.md - 适配新架构 ✅
4. skills/novel-reviewer/SKILL.md - 融合 33维度 ✅
5. tools/cli.py - 添加 ReAct Agent 支持 ✅
6. tools/agent/writer.py - 集成验证器 ✅

### 融合原则
- 不破坏现有功能
- 新模块独立，可选使用
- 保持 OpenWrite 的 Prompt-driven 特色
- 逐步迁移，降低风险

## 融合完成状态

| 功能 | 状态 | 文件 |
|------|------|------|
| LLM 客户端 | ✅ 完整 | tools/llm/client.py |
| Agent 基类 | ✅ 完整 | tools/agent/base.py |
| WriterAgent (两阶段) | ✅ 完整 | tools/agent/writer.py |
| ReviewerAgent (33维度) | ✅ 完整 | tools/agent/reviewer.py |
| ReActAgent | ✅ 完整 | tools/agent/react.py |
| 真相文件管理 | ✅ 完整 | tools/truth_manager.py |
| 上下文构建 | ✅ 完整 | tools/context_builder.py |
| CLI 应用 | ✅ 完整 | tools/cli.py |
| 后置验证器 | ✅ 新增 | tools/post_validator.py |
| 状态验证器 | ✅ 新增 | tools/state_validator.py |
| 对话指纹提取 | ✅ 新增 | tools/dialogue_fingerprint.py |

## 未融合功能（可选）

| 功能 | 原因 |
|------|------|
| 记忆时态数据库 (MemoryDB) | SQLite 依赖，需要额外存储 |
| 雷达市场分析 | 市场数据源依赖 |
| 同人正典系统 | 特定场景功能 |
