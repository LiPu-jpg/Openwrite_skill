# 写作技法库 (craft/)

本目录包含跨作品共享的写作技法资源，作为三层风格架构的第一层（通用层）。

## 文件说明

| 文件 | 说明 |
|------|------|
| `humanization.yaml` | 去 AI 味规则 — 禁用词清单、替换策略、自然不完美规则 |
| `ai_patterns.yaml` | AI 痕迹检测词库 — 分类（表情/情绪/眼神）、严重级别、替换建议 |
| `dialogue_craft.md` | 通用对话技法 — 格式规范、标签位置、节奏光谱（短促/标准/长篇） |
| `scene_craft.md` | 通用场景结构技法 — 8类场景模板（设定说明/战斗/日常/煽情/说服/反转/考验/博弈） |
| `rhythm_craft.md` | 通用节奏控制技法 — 段落分布、紧张松弛循环、加速减速、章节钩子、信息密度 |

## 三层风格架构

```
Layer 1: craft/               ← 本目录（通用技法，跨作品共享）
Layer 2: data/reference_styles/  （参考作品风格指纹）
Layer 3: data/novels/{id}/       （作品自身设定）
  ↓ 合成
最终风格指南 → 注入生成上下文
```

## 使用方式

1. **ContextBuilder** 在组装上下文时自动读取本目录的技法文件
2. **StyleExtractionPipeline** 提取风格时会参照本目录的 AI 痕迹词库
3. **novel-reviewer** 审查时使用 `humanization.yaml` 和 `ai_patterns.yaml` 检测 AI 痕迹

## 扩展指南

添加新技法文件时：
1. 使用 `.md` 格式编写，以 `## 标题` 分节
2. 在 `ContextBuilder._load_craft_rules()` 中注册新文件名
3. 更新本 `README.md`
