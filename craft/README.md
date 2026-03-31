# 写作技法库 (craft/)

本目录只保留**跨作品通用**的写作技法和去模板化约束，不包含任何具体作品、角色、组织或专有名词。

## 文件说明

| 文件 | 说明 |
|------|------|
| `humanization.yaml` | 去模板化规则，约束高频 AI 表达和僵硬措辞 |
| `ai_patterns.yaml` | AI 痕迹检测词库和结构模式 |
| `dialogue_craft.md` | 通用对话技法 |
| `scene_craft.md` | 通用场景结构技法 |
| `rhythm_craft.md` | 通用节奏控制技法 |

## 当前分层

```text
Layer 1: craft/                                  ← 通用技法
Layer 2: data/novels/{id}/data/sources/{sid}/    ← 用户提供文本提取出的风格/设定源
Layer 3: data/novels/{id}/src/**                 ← 本书确认版真源
```

最终写作时，系统会把这三层压成 canonical packet，而不是直接拼原始 prompt。

## 设计原则

- `craft/` 里只写结构规律、写法约束和负面清单
- 不引用具体作品名、角色名、世界观名词
- 不把某一部作品的签名表达当成“通用技法”
- 如果某条规则只适用于某类题材，应写成“适用场景”，不要写成“某书写法”

## 使用方式

1. `ContextBuilder` 和 `ChapterAssemblerV2` 会自动读取 `craft/`
2. `style synthesize` 会把 `craft/` 与本书风格指纹、用户提取源合成
3. `review` 会用 `humanization.yaml` 和 `ai_patterns.yaml` 检查模板化问题

## 扩展规则

新增通用技法文件时：

1. 使用 `.md` 或 `.yaml`
2. 文件内容必须是跨作品可复用的规则
3. 不写具体作品名、人名、势力名、专有设定
4. 更新本说明文件和读取链
