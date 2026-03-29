---
name: style-system
description: Use when user wants to initialize style, compose style layers, extract style from reference works, or analyze text style. Triggers include "风格初始化", "合成风格", "风格分析", "提取风格", "去AI味", "文风设置".
---

# 风格系统

管理写作风格，包括初始化、合成、提取和分析。

## 核心理念

**每个作品都有专属风格**，不是直接套用某个小说的风格。

风格初始化流程：
1. 通过问询了解作者偏好（5-10个问题）
2. 可选：从参考作品提取特征
3. 合并共享技法 + 专属设定
4. 生成作品专属 `fingerprint.yaml`

## 风格层次

```
┌─────────────────────────────────────────────┐
│  共享层（跨作品通用）                         │
│  ├── craft/humanization.yaml  # 去AI味规则   │
│  ├── craft/ai_patterns.yaml   # AI痕迹词库   │
│  ├── craft/dialogue_craft.md  # 对话技法     │
│  ├── craft/scene_craft.md    # 场景结构技法  │
│  └── craft/rhythm_craft.md   # 节奏控制技法  │
├─────────────────────────────────────────────┤
│  专属层（每部作品独立）                       │
│  data/reference_styles/{作品}/    # 提取的风格文档   │
│  data/novels/{id}/                             │
│  ├── style/fingerprint.yaml  # 问询生成的指纹 │
│  └── style/composed.md       # 合成后的最终风格 │
└─────────────────────────────────────────────┘
```

## 功能模块

### 1. 风格初始化

**触发词**: "风格初始化", "初始化风格", "创建风格"

**流程**:
1. 开始问询流程（5个核心问题）
2. 记录偏好并生成 hints
3. 如有参考作品，提取风格特征
4. 合并共享层 + 专属层
5. 保存到 `data/novels/{novel_id}/data/style/fingerprint.yaml`

**问询问题**:
- Q1: 基调（轻松幽默/严肃正剧/悬疑紧张/温馨治愈/热血爽文）
- Q2: 节奏（快/中/慢）
- Q3: 对话/描写比例
- Q4: 参考作品（可选）
- Q5: 特殊要求（可选）

**输出**: `data/novels/{novel_id}/data/style/fingerprint.yaml`

---

### 2. 风格提取（小文本）

**触发词**: "提取风格", "分析参考作品", "学习风格"

**适用场景**: 参考文本 < 5万字（可一次性处理）

**流程**:
1. 读取参考文本
2. 提取6个维度特征：
   - 叙述声音 (Voice)
   - 语言风格 (Language)
   - 节奏控制 (Rhythm)
   - 对话风格 (Dialogue)
   - 幽默体系 (Humor)
   - 情感表达 (Emotion)
3. 区分可复用特征 vs 作品特定特征
4. 生成提取报告

**输出**: `data/novels/{novel_id}/data/style/extraction_report.yaml`

---

### 2b. 大文本风格提取（百万字级）

**触发词**: "大文本提取", "批量提取风格", "从小说学风格"

**适用场景**: 参考文本 > 5万字（几十万到几百万字的完整小说）

**工具依赖**:
- `tools/text_chunker.py` — 智能文本切割
- `tools/style_extraction_pipeline.py` — 分批提取流水线

**流程**:

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  1. 准备阶段  │ →  │  2. 阅读阶段  │ →  │  3. 合并阶段  │ →  │  4. 完成  │
│  切割大文本   │    │  逐块提取风格  │    │  合并风格文档  │    │  输出风格  │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────┘
                         ↑                    │
                         └────────────────────┘
                          每3批合并一次，循环
```

#### 步骤 1: 准备（自动）

用户提供 .txt 文件路径后，AI 助手执行：

```python
from tools.style_extraction_pipeline import StyleExtractionPipeline
pipeline = StyleExtractionPipeline(
    project_root=Path.cwd(),
    novel_id="my_novel",
    source_name="术师手册",
    chunk_size=30000,  # 每块约3万字
)
progress = pipeline.prepare(source_file=Path("术师手册.txt"))
```

自动完成：
- 智能切割（按章节边界，~3万字/块）
- 创建目录结构
- 初始化风格文档模板
- 生成进度文件（支持断点续传）

#### 步骤 2: 逐块阅读提取（AI 驱动循环）

对每个分块，AI 助手：
1. 调用 `pipeline.next_chunk()` 获取下一块文本 + 当前风格文档
2. 按 `prompts/batch_extract_style.md` 提示词分析文本
3. 将发现分为三层：
   - **craft** — 通用写作技法（换作品也能用）
   - **author** — 作者风格指纹（这个作者的习惯）
   - **novel** — 作品设定（角色/术语/世界观）
4. 更新风格文档（voice.md, language.md, rhythm.md 等）
5. 调用 `pipeline.save_batch_result()` 保存进度

#### 步骤 3: 定期合并

每处理 3 个分块后，自动触发合并：
- 整合所有批次的发现
- 消除重复/矛盾
- 更新 summary.md 的迭代记录

#### 步骤 4: 完成

所有分块处理完毕后，输出完整风格档案到 `data/reference_styles/{source_name}/`。

**进度追踪**: `data/novels/{novel_id}/data/style/extraction/progress.json`
**支持断点续传**: 中途停止后，再次执行会从上次中断的分块继续。

**输出目录结构**:
```
data/novels/{novel_id}/
  data/style/
    extraction/
      progress.json              # 进度追踪
      chunks/                    # 已切割的文本块
        chunk_000.txt
        chunk_001.txt
        ...
      batch_results/             # 每批次原始发现
        batch_000.yaml
        batch_001.yaml
        ...
  styles/{参考作品}/              # 最终风格文档（位于 data/reference_styles/）
    summary.md                   # 风格总结（持续更新）
    voice.md                     # 叙述声音
    language.md                  # 语言风格
    rhythm.md                    # 节奏风格
    dialogue.md                  # 对话风格
    scene_templates.md           # 场景模板
    consistency.md               # 一致性规则
  craft/                         # 通用技法（跨作品复用）
  novels/{novel_id}/             # 作品设定
```

---

### 3. 风格合成

**触发词**: "合成风格", "生成最终风格", "组装风格"

**流程**:
1. 读取三层风格文档：
   - `craft/` - 通用技法（可选参考）
   - `data/reference_styles/{参考作品}/` - 提取的风格文档（核心约束）
  - `data/novels/{id}/src/characters/` + `src/world/` - 作品设定（硬性约束）
   - 用户覆盖 - 最高优先级
2. 按优先级合成：用户覆盖 > 作品设定 > 作品风格 > 通用技法
3. 解决冲突
4. 生成最终风格文档

**输出**: `data/novels/{novel_id}/data/style/composed.md`

**合成优先级**:
```
用户覆盖 > 作品设定（角色/世界观硬性约束） > 参考风格（提取的风格文档） > 通用技法（可选参考）
```

---

### 4. 风格分析

**触发词**: "风格分析", "检查风格", "分析文本"

**流程**:
1. 读取待分析文本
2. 分析4个维度：
   - 基本统计（字数、段落、对话占比）
   - 风格特征（声音、语言、节奏、对话）
   - AI痕迹检测（40+ 中文AI套路词）
   - 与目标风格的偏差
3. 生成改进建议

**输出**: `data/novels/{novel_id}/data/style/analysis_report.yaml`

---

## 数据文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 风格指纹 | `data/novels/{id}/data/style/fingerprint.yaml` | 问询生成的专属风格 |
| 提取报告 | `data/novels/{id}/data/style/extraction_report.yaml` | 从参考作品提取的特征（小文本） |
| 合成风格 | `data/novels/{id}/data/style/composed.md` | 最终生成指令 |
| 分析报告 | `data/novels/{id}/data/style/analysis_report.yaml` | 文本风格分析结果 |
| AI词库 | `craft/ai_patterns.yaml` | 40+ AI痕迹检测词库 |
| 提取进度 | `data/novels/{id}/data/style/extraction/progress.json` | 大文本提取进度追踪 |
| 分块清单 | `data/novels/{id}/data/style/extraction/chunks/manifest.json` | 文本切割清单 |
| 批次发现 | `data/novels/{id}/data/style/extraction/batch_results/*.yaml` | 各批次原始发现 |
| 风格文档 | `data/reference_styles/{参考作品}/` | 提取的完整风格文档集（7个.md） |

---

## 提示词文件

| 提示词 | 路径 | 用途 |
|--------|------|------|
| 风格初始化 | `prompts/initialize_style.md` | 问询式风格初始化 |
| 风格提取 | `prompts/extract_style.md` | 从参考作品提取风格（小文本） |
| 分批提取 | `prompts/batch_extract_style.md` | 大文本分批提取风格（核心） |
| 风格合成 | `prompts/compose_style.md` | 三层风格合成 |
| 风格分析 | `prompts/analyze_style.md` | 文本风格分析 |

## 工具文件

| 工具 | 路径 | 用途 |
|------|------|------|
| 文本切割器 | `tools/text_chunker.py` | 大文本智能切割（按章节边界，~3万字/块） |
| 提取流水线 | `tools/style_extraction_pipeline.py` | 分批提取进度管理、断点续传 |

---

## 使用示例

### 示例 1: 初始化新作品风格

```
用户: 风格初始化

助手: 我来帮你初始化作品风格，请回答以下问题：

Q1: 你希望作品的基调是？
  A. 轻松幽默
  B. 严肃正剧
  C. 悬疑紧张
  D. 温馨治愈
  E. 热血爽文

用户: A

助手: Q2: 你希望的节奏是？
  A. 快节奏（短段为主，信息密集）
  B. 中节奏（长短结合，张弛有度）
  C. 慢节奏（长段描写，注重氛围）

用户: B

助手: Q3: 对话和描写的比例？
  A. 对话为主（通过对话推进剧情）
  B. 平衡（对话与描写并重）
  C. 描写为主（注重场景和氛围）

用户: A

助手: Q4: 是否有参考作品？（可选）

用户: 参考《术师手册》

助手: Q5: 有什么特殊要求？（可选）

用户: 不要用网络流行语

助手: 
✅ 风格初始化完成

已生成风格指纹：
- 基调: 轻松幽默
- 节奏: 中节奏
- 对话占比: 55%
- 参考作品: 术师手册（已提取吐槽节奏、信息差揭示等特征）
- 特殊约束: 禁用网络流行语

文件已保存：
data/novels/my_novel/data/style/fingerprint.yaml
```

---

### 示例 2: 合成最终风格

```
用户: 合成风格

助手: 正在合成三层风格...

读取中：
- craft/humanization.yaml（去AI味规则）
- craft/dialogue_craft.md（对话技法）
- craft/scene_craft.md（场景结构技法）
- craft/rhythm_craft.md（节奏控制技法）
- data/novels/my_novel/data/style/fingerprint.yaml（作品风格）
- data/novels/my_novel/src/characters/（作品设定）

合成完成！

最终风格文档已生成：
data/novels/my_novel/data/style/composed.md

包含：
1. 硬性约束（不可违反）
2. 风格约束（应当遵循）
3. 可选技法（按需使用）
4. 文本人化规则（去AI味）
5. 生成检查清单
```

---

### 示例 3: 分析文本风格

```
用户: 分析第三章的风格

助手: 正在分析 ch_003_draft.md...

📊 风格分析报告

基本统计：
- 字数: 3521
- 段落数: 42
- 对话占比: 48%
- 平均句长: 18字

❌ AI痕迹检测（评分: 75/100）
发现 6 处AI套路词：
1. "不禁心中一紧" → 建议: "手心沁出了汗"
2. "眼神中闪过一丝坚定" → 建议: 删除，用动作替代
3. "心中涌起一股..." → 建议: "握紧了拳头"

⚠️ 风格偏差
- 对话占比: 目标55%，实际48%（偏低）
- 节奏: 连续3个长段落（>200字），建议插入短句

✅ 符合项
- 基调: 轻松幽默 ✓
- 语言: 现代感，无网络流行语 ✓

改进建议：
1. 【必须】删除6处AI痕迹
2. 【建议】增加对话比例到55%
3. 【可选】打破长段落，增加节奏变化
```

---

### 示例 4: 从百万字小说提取风格

```
用户: 从这个txt提取风格 /path/to/术师手册.txt

助手: 正在分析文件...

📊 文件信息：
- 大小: 4.2MB
- 预估字数: ~140万字
- 预计切割: 47 个分块（每块约3万字）

正在切割并初始化...

✅ 准备完成
- 切割为 47 个分块（按章节边界）
- 已创建风格文档目录
- 进度文件: data/novels/my_novel/data/style/extraction/progress.json

开始提取第 1/47 批（第1-22章，29,847字）...

──────── 批次 1 发现 ────────

📝 通用技法 (craft): 3 条
- 先甜后打脸的反转模式
- 通过角色阅读资料嵌入设定
- 章末钩子设置

🎨 作者风格 (author): 5 条
- 第三人称有限视角，叙述者高度贴近角色意识
- 吐槽密度极高，用现代视角解构奇幻
- 短段为主（60%为1-2句）
- 网络用语自然融入叙述
- 双线叙事的信息差

📖 作品设定 (novel): 4 条
- 四柱神邪教体系
- 术师等级（翼级系统）
- 亚修/索妮娅角色设定
- 术师手册游戏系统

已更新: voice.md, language.md, rhythm.md
进度: 1/47 (2.1%)

继续提取第 2/47 批？

用户: 继续

助手: 提取第 2/47 批（第23-45章，31,205字）...
...
```

---

## 与其他技能的关系

- **novel-creator**: 创作时自动应用合成后的风格
- **novel-reviewer**: 审查时使用风格分析检测偏差
- **novel-manager**: 项目初始化时触发风格初始化

---

## 注意事项

1. **不要直接套用**：风格初始化是问询式的，不是直接复制某个作品
2. **共享层复用**：`craft/` 中的技法是跨作品通用的，不要重复定义
3. **优先级明确**：用户覆盖 > 作品设定 > 作品风格 > 通用技法
4. **AI词库维护**：`craft/ai_patterns.yaml` 需要持续更新
5. **大文本提取**：百万字级文本必须使用分批提取流程，支持断点续传
6. **三层分类**：提取时严格区分 craft/author/novel 三层，参考层级判断标准

---

*风格系统版本: 5.3.0*
*最后更新: 2026-03-04*
