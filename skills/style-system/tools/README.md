# Style System Tools

风格系统工具说明。

## 设计决策

**OpenCode Skill 环境中，Agent 通过 Read/Write/Bash 工具直接操作文件，无需 Python 工具类。**

原始 OpenWrite 项目中的 3 个 Python 工具（`style_initializer.py`, `style_extractor.py`, `style_composer.py`）在此环境下的替代方案：

| 原工具 | 功能 | OpenCode 实现方式 |
|--------|------|------------------|
| `style_initializer.py` | 问询式风格初始化 | Agent 通过 `prompts/initialize_style.md` 引导对话，直接 Write `fingerprint.yaml` |
| `style_extractor.py` | 从参考作品提取风格 | Agent 通过 `prompts/extract_style.md` 分析文本，直接 Write `extraction_report.yaml` |
| `style_composer.py` | 三层风格合成 | Agent 通过 `prompts/compose_style.md` 读取三层文件，直接 Write `composed.md` |

## 工具执行流程

### 1. 风格初始化

```
Agent 读取 prompts/initialize_style.md
  ↓
与用户对话（5个问题）
  ↓
收集答案 + 可选参考作品
  ↓
Write data/novels/{id}/style/fingerprint.yaml
```

### 2. 风格提取

```
Agent 读取 prompts/extract_style.md
  ↓
Read 参考文本
  ↓
分析 6 个维度（voice, language, rhythm, dialogue, humor, emotion）
  ↓
Write data/novels/{id}/style/extraction_report.yaml
```

### 3. 风格合成

```
Agent 读取 prompts/compose_style.md
  ↓
Read craft/*.yaml + craft/*.md（通用技法）
Read data/reference_styles/{作品名}/*.md（参考风格，可选）
Read data/novels/{id}/style/fingerprint.yaml（作品风格）
Read data/novels/{id}/characters/ + world/（作品设定）
  ↓
按优先级合成（用户覆盖 > 作品设定 > 作品风格 > 参考风格 > 通用技法）
  ↓
Write data/novels/{id}/style/composed.md
```

### 4. 风格分析

```
Agent 读取 prompts/analyze_style.md
  ↓
Read 待分析文本
Read craft/ai_patterns.yaml（AI痕迹词库）
Read data/novels/{id}/style/composed.md（目标风格）
  ↓
分析 4 个维度 + AI痕迹检测 + 偏差分析
  ↓
Write data/novels/{id}/style/analysis_report.yaml
```

## 为什么不迁移 Python 工具？

1. **环境差异**：原工具依赖 Pydantic、项目内路径、YAML 序列化等，在 OpenCode 环境中需要大量适配
2. **Agent 能力**：OpenCode Agent 本身就能读写文件、解析 YAML、执行逻辑，无需额外 Python 层
3. **维护成本**：保留 Python 工具需要同步维护两套实现（原项目 + OpenCode Skill）
4. **灵活性**：Prompt 驱动的实现更容易调整和扩展

## 参考实现

原始 Python 工具保留在 `reference/openwrite_original/skills/style/tools/` 供参考：
- `style_initializer.py`（413行）
- `style_extractor.py`（712行）
- `style_composer.py`（未统计）

如需查看具体逻辑，可直接阅读这些文件。
