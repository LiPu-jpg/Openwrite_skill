---
name: text-processing
description: Use when user wants to chunk large texts, compress summaries, or process long documents. Triggers include "切割", "压缩", "分块", "长文本".
---

# 文本处理系统

处理长文本，包括智能切割和渐进压缩。

## 核心概念

**切割（chunking）**：
- 按章节边界智能切割
- 默认 3万字/chunk
- 超长章节自动二次切割

**压缩（compression）**：
- 章 → 节 → 篇 三级压缩
- 保留关键信息和叙事逻辑
- 支持解压缩回原貌

## 可用工具

| 工具 | 说明 |
|------|------|
| `chunk_text` | 将大文本切割为chunk |
| `compress_section` | 压缩节/篇摘要 |

## 使用示例

### 切割大文本

```
用户: 这个100万字的文件太大了，切割一下

AI:
[COMMAND] chunk_text {
  "file_path": "/path/to/novel.txt",
  "chunk_size": 30000
}

结果:
- 总块数: 34
- chunk_1: 第1-5章, 28500字
- chunk_2: 第6-10章, 31200字
- chunk_3: 第11-15章, 29800字
...
```

### 压缩节摘要

```
用户: 压缩一下"修炼篇"的内容

AI:
[COMMAND] compress_section {
  "arc_id": "arc_001"
}

结果:
- 篇: arc_001 (修炼篇)
- 压缩后: 1200字
- 压缩比: 15:1
- 内容: 主角从普通人成长为筑基修士...
```

### 压缩单个节

```
用户: 第一节的内容太多了，帮我压缩

AI:
[COMMAND] compress_section {
  "arc_id": "arc_001",
  "section_id": "sec_001"
}

结果:
- 节: sec_001 (师门试炼)
- 压缩后: 500字
- 压缩比: 8:1
```

## 切割规则

### 识别的章节格式
- `第X章` / `第X节` / `第X回`
- `Chapter X` / `CHAPTER X`
- `序章` / `楔子` / `尾声` / `番外`

### 切割优先级
1. 按章节边界切
2. 不拆开单个章节
3. 超长章节按段落切

## 压缩级别

| 级别 | 范围 | 压缩比 | 用途 |
|------|------|--------|------|
| 节压缩 | ~5章 | 5:1 | 上下文窗口 |
| 篇压缩 | ~20章 | 15:1 | 大纲回顾 |
| 卷压缩 | 全书 | 50:1 | 整体概要 |

## 使用场景

### 场景1：处理长参考文件
```
用户: 参考作品有80万字，怎么处理？

AI: 先切割再逐块分析
[COMMAND] chunk_text {
  "file_path": "参考作品.txt",
  "chunk_size": 30000
}
```

### 场景2：管理长上下文
```
用户: 前50章的剧情太长了，摘要一下

AI: 压缩到篇级别
[COMMAND] compress_section {
  "arc_id": "arc_001"
}
```

### 场景3：查看节概要
```
用户: 第二篇的剧情发展是什么？

AI:
[COMMAND] compress_section {
  "arc_id": "arc_002"
}
```

## 压缩内容保留

压缩时保留：
- 主要角色的关键决策
- 重要的剧情转折点
- 伏笔的埋设和回收
- 世界状态的重要变化

压缩时舍弃：
- 场景描写细节
- 次要角色的日常
- 重复的描述
