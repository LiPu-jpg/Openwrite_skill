---
name: dialogue-quality
description: Use when user wants to analyze dialogue style, extract character speech patterns, or check for AI-sounding dialogue. Triggers include "对话", "口头禅", "角色声音", "对话风格".
---

# 对话质量系统

提取和分析角色对话风格，确保对话自然、个性化。

## 核心概念

**对话指纹**包括：
- `avg_sentence_length` - 平均句长
- `common_bigrams` - 常用词组
- `question_ratio` - 问句比例
- `speech_patterns` - 口头禅/语言习惯

## 可用工具

| 工具 | 说明 |
|------|------|
| `extract_dialogue_fingerprint` | 提取对话风格指纹 |

## 使用示例

### 分析角色对话风格

```
用户: 分析一下张三的对话风格

AI: 让我提取一下...
[COMMAND] extract_dialogue_fingerprint {
  "chapter_id": "ch_005",
  "character_names": ["张三"]
}

结果:
- 角色: 张三
- 平均句长: 12.3字
- 常用词组: ["脸色一沉", "沉声道", "眉头一皱"]
- 问句比例: 15%
- 口头禅: ["你懂什么", "且慢"]
- 总结: 张三：平均句长12.3字，常用词组[脸色一沉, 沉声道...]，问句比例15%，口头禅[你懂什么, 且慢]
```

### 提取所有角色对话

```
用户: 当前章节有哪些角色的对话风格？

AI:
[COMMAND] extract_dialogue_fingerprint {
  "chapter_id": "latest"
}

结果:
- 张三: 话少、直接、常用"哼"
- 李四: 话多、爱用修辞、问句多
- 师父: 威严、每句必带称呼
```

## 对话风格要素

### 1. 句长
- 武将/莽汉：短句（3-8字）
- 文人/谋士：长句（15-30字）
- 普通角色：中等（8-15字）

### 2. 口头禅
- 角色特有的习惯用词
- 情绪触发词（如愤怒时的口头禅）

### 3. 问句比例
- 好奇角色：问句多（>20%）
- 果断角色：问句少（<5%）

### 4. 语言特征
- 方言/口音
- 专业术语
- 情绪词频率

## AI味对话检测

对话中常见的AI味特征：
1. **过度礼貌** - "请"、"劳烦"、"久仰"
2. **解释性对话** - 角色互相解释已知信息
3. **完美逻辑** - 每句话都有直接因果
4. **情绪单一** - 对话缺少微妙的情绪波动

## 改进建议

当发现AI味对话时，建议：
1. 缩短句子
2. 增加口头禅
3. 添加省略/碎片句
4. 引入方言或口语
