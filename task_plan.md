# Task Plan: 将 InkOS 核心功能融合到 OpenWrite

## Goal
将 inkos-master 的 Agent 架构、两阶段写作、LLM 封装、真相文件等核心功能融合到 OpenWrite 项目中，实现真正的内置 Agent 能力。

## Current Phase
ALL COMPLETE

## Phases

### Phase 1: 需求分析 + 项目探索
- [x] 分析两个项目的结构差异
- [x] 确定融合点（context_builder, ai检测, 伏笔管理等）
- [ ] 创建 findings.md 记录发现
- **Status:** in_progress

### Phase 2: 创建 LLM 客户端模块 (tools/llm/)
- [x] 创建 tools/llm/__init__.py
- [x] 创建 tools/llm/client.py - 统一 LLM 调用（含流式、降级、错误包装）
- [x] 创建 tools/llm/errors.py - 人性化错误处理
- [x] 融合现有的 llm 相关代码
- **Status:** complete

### Phase 3: 创建 Agent 基类 (tools/agent/)
- [x] 创建 tools/agent/__init__.py
- [x] 创建 tools/agent/base.py - BaseAgent 基类
- [x] 创建 tools/agent/writer.py - 两阶段写作 Agent
- [x] 创建 tools/agent/reviewer.py - 审核 Agent（融合 33维度审计）
- **Status:** complete

### Phase 4: 重构 ContextBuilder 融合真相文件
- [x] 创建 truth_manager.py - 真相文件管理
- [x] 添加真相文件到 ContextBuilder 上下文
- [x] 添加状态快照机制
- [x] 融合 InkOS 的 POV 过滤逻辑
- **Status:** complete

### Phase 5: 融合 AI 痕迹检测
- [x] 融合 InkOS 的统计方法（段落等长变异系数）
- [x] 扩展 craft/ai_patterns.yaml 增加统计检测
- [x] 创建 tools/ai_detector.py (集成在 reviewer.py 中)
- **Status:** complete

### Phase 6: 完善伏笔/状态管理
- [x] 重构 foreshadowing_manager.py (已有 DAG)
- [x] 融合 InkOS 的 hook 过滤逻辑 (在 truth_manager 中)
- [x] 添加粒子账本 (particle_ledger) 概念 (在 truth_manager 中)
- **Status:** complete

### Phase 7: 添加 CLI 应用支持
- [x] 创建 tools/cli.py - 命令行接口
- [x] 添加 pyproject.toml entry point (openwrite 命令)
- [x] 测试 CLI 功能
- **Status:** complete

### Phase 8: 测试验证
- [x] 运行现有测试 (158 passed)
- [x] 验证新 Agent 功能
- **Status:** complete

## Key Questions
1. OpenWrite 的 Skill (SKILL.md) 如何与新的 Agent 系统协同？ - 决策：SKILL.md 作为编排层，Agent 作为执行层
2. 真相文件格式选择？ - 决策：继续用 Markdown + YAML，与现有架构一致
3. 是否需要保留渐进压缩？ - 决策：保留，在 context_builder 中集成

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用 Python 类继承实现 Agent | 与 InkOS 的 TypeScript 风格一致，但用 Python 生态 |
| 真相文件保持 Markdown | 便于人工编辑和版本控制 |
| SKILL.md 作为高层编排 | Prompt 驱动适合工作流描述，Agent 适合底层 LLM 调用 |
| 保留渐进压缩 | InkOS 无此功能，OpenWrite 独有，保持差异化 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 待记录 | - | - |

## Notes
- 工作目录: /Users/jiaoziang/迁移/Openwrite_skill-main
- 参考项目: /Users/jiaoziang/迁移/inkos-master
- 先创建计划文件，再逐步实现
