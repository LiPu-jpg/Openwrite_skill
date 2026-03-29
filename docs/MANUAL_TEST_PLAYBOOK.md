# OpenWrite 人工测试档案

本文档用于手工验证 OpenWrite 在真实使用场景下是否可用、稳定、可回归。

## 1. 测试目标

- 验证核心命令是否可用：init / wizard / sync / write / review / context / assemble / doctor / status / agent。
- 验证数据结构是否符合新规范：src 是 source of truth，data 是运行态。
- 验证常见异常分支是否有可理解反馈（例如缺少 LLM 配置、无待同步项、非法输入）。

## 2. 使用前准备

### 2.1 环境前置

1. 进入项目目录：

```bash
cd /Users/jiaoziang/迁移/Openwrite
```

2. 使用项目 Python 环境（建议固定）：

```bash
/Users/jiaoziang/迁移/.venv/bin/python --version
```

3. 如需启用写作/审查/向导中的 LLM 调用，准备环境变量：

```bash
export LLM_PROVIDER=<your_provider>
export LLM_MODEL=<your_model>
export LLM_API_KEY=<your_api_key>
```

4. 安装依赖后执行基础检查（可选）：

```bash
/Users/jiaoziang/迁移/.venv/bin/python -m pytest tests/test_cli_helpers.py tests/test_cli_sync.py tests/test_context_schema.py -q
```

### 2.2 目录认知（必须）

- 人工编辑目录：`data/novels/{novel_id}/src`
- 运行态目录：`data/novels/{novel_id}/data`
- 同步规则：`src -> data`（单向）

参考说明见：`docs/SYNC_MATRIX.md`

## 3. 快速使用指南（给新同学）

### 3.1 最短路径（5 分钟）

1. 初始化：

```bash
openwrite init demo_novel
```

2. 检查环境与路径：

```bash
openwrite doctor
```

3. 同步检查：

```bash
openwrite sync --check --novel-id demo_novel --json
```

4. 组装包预览：

```bash
openwrite assemble ch_001 --format markdown --output-dir data/novels/demo_novel/data/test_outputs/context_packets
```

5. 查看状态：

```bash
openwrite status
```

## 4. 人工测试矩阵

以下用例建议按顺序执行。每条用例都包含：步骤、预期结果、失败判定。

### T01 初始化

步骤：

```bash
openwrite init mt_novel
```

预期：
- 生成 `data/novels/mt_novel/src` 与 `data/novels/mt_novel/data`。
- 存在 `src/outline.md` 与 `data/hierarchy.yaml`。

失败判定：
- 目录缺失；或仍生成旧平铺结构（outline/characters/world 在同级）。

### T02 doctor 自检

步骤：

```bash
openwrite doctor
```

预期：
- 输出源目录、运行目录、测试输出目录状态。
- LLM 未配置时展示 `<missing>`，而不是崩溃。

失败判定：
- 命令异常退出；或路径打印错误。

### T03 sync 检查（JSON）

步骤：

```bash
openwrite sync --check --novel-id mt_novel --json
```

预期：
- 返回 JSON，包含：`mode`、`status`、`suggestions`、`actions`、`ok`、`exit_code`。
- `actions` 字段存在，且在无待同步项时为 `continue_writing`。

失败判定：
- JSON 缺字段；或 actions 缺失。

### T04 sync 执行

步骤：

```bash
openwrite sync --novel-id mt_novel --json
```

预期：
- 返回 `before/after` 状态。
- 若存在 outline/角色源变更，执行后 `needs_sync` 下降或清零。

失败判定：
- 执行后状态无变化且无错误说明。

### T05 context 可视化

步骤：

```bash
openwrite context ch_001 --show
```

预期：
- 可打印上下文文本。
- 不应引用旧路径（如旧 story 目录）。

失败判定：
- 上下文关键段缺失；或出现明显旧术语漂移。

### T06 assemble 导出

步骤：

```bash
openwrite assemble ch_001 --format markdown --output-dir data/novels/mt_novel/data/test_outputs/context_packets
```

预期：
- 在 output-dir 下生成快照文件。
- 文件包含系统提示词、背景、章节信息等主要段落。

失败判定：
- 无文件输出；或输出为空。

### T07 write 正常链路（需 LLM）

步骤：

```bash
openwrite write ch_001
```

预期：
- 生成章节文件到 `data/manuscript/{arc}/ch_001.md`。
- 日志显示字数、快照创建、真相更新（或明确无增量）。

失败判定：
- 文件未落盘；或日志宣称更新但实际无对应文件变化。

### T08 write 异常链路（无 LLM）

步骤：
- 取消 LLM 环境变量后执行：

```bash
openwrite write ch_001
```

预期：
- 给出“未安装或未配置”提示。
- 不应因为参数访问错误而二次崩溃。

失败判定：
- 报参数属性错误（例如不存在的 args 字段）。

### T09 review（需 LLM）

步骤：

```bash
openwrite review ch_001
```

预期：
- 返回审查结论、分数或问题数量。

失败判定：
- 输入章节存在但命令无结果。

### T10 agent 自然语言指令

步骤：

```bash
openwrite agent "查看项目状态"
```

预期：
- 能完成一次 orchestrator 路由并给出状态类回应。
- 工具调用不死循环。

失败判定：
- 回合超时、空响应、无限循环。

### T11 wizard 交互（人工）

步骤：

```bash
openwrite wizard
```

建议输入：
- 我想写个都市异能故事
- 书名：测试向导作品
- 使用通用风格

预期：
- 可正常对话（方向键可用，prompt_toolkit 生效）。
- 创建项目后返回项目路径。
- 选择 AI 设定时，能够生成 `src/world/*` 与 `data/world/current_state.md`、`data/foreshadowing/hooks_seed.md`。

失败判定：
- 命令解析失败、交互中断、产物路径不符合 src/data 新结构。

### T12 非法输入安全性

步骤：
- 通过 agent 或工具链触发 create_character，传入异常 name（如 `../evil`）。

预期：
- 返回输入非法或被拒绝，不会写到目标目录外。

失败判定：
- 出现目录穿越写入。

## 5. 回归建议（每次改动后至少跑）

最小回归：

```bash
/Users/jiaoziang/迁移/.venv/bin/python -m pytest tests/test_cli_helpers.py tests/test_cli_sync.py tests/test_context_schema.py -q
openwrite sync --check --novel-id test_novel --json
openwrite doctor
```

发布前回归：
- 补跑 `openwrite assemble`、`openwrite write`（有 LLM）和 `openwrite wizard` 人工流程。

## 6. 缺陷记录模板

复制以下模板到 issue 或 PR 评论：

```markdown
### 用例编号
- Txx

### 环境
- 分支：
- Python：
- LLM 配置：有 / 无

### 操作步骤
1.
2.
3.

### 实际结果
- 

### 预期结果
- 

### 附件
- 命令输出：
- 截图/日志：
```

## 7. 常见误区

- 误区 1：手工修改 `data/hierarchy.yaml` 或 `data/characters/cards/*.yaml`。
  - 正确做法：改 `src`，再运行 `openwrite sync`。

- 误区 2：把 `data/world/*` 当作世界规则源。
  - 正确做法：`src/world/*` 是规则，`data/world/*` 是运行态状态。

- 误区 3：只看命令返回，不看落盘结果。
  - 正确做法：关键路径必须同时验证“日志 + 文件变化”。
