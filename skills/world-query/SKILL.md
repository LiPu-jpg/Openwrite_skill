---
name: world-query
description: Use when user wants to query world-building entities, check relations, or explore the story world. Triggers include "世界观", "实体", "关系", "查询世界".
---

# 世界查询系统

查询和管理小说中的世界观实体（地点、人物、法宝、功法等）。

## 核心概念

**实体类型**：
- `location` - 地点/场所
- `person` - 人物/势力
- `technique` - 功法/技能
- `item` - 法宝/物品
- `concept` - 概念/规则

**实体状态**：
- `active` - 当前存在
- `destroyed` - 已毁坏
- `unknown` - 未知的

## 可用工具

| 工具 | 说明 |
|------|------|
| `query_world` | 查询实体列表或单个实体详情 |
| `get_world_relations` | 获取关系图谱 |

## 使用示例

### 列出所有实体

```
用户: 我的小说里有哪些地点？

AI: 让我查询一下...
[COMMAND] query_world {
  "type": "location"
}

结果:
- qinghe_town (青河镇) - 冀州北部的古老小镇
- black_forest (黑森林) - 妖兽横生的危险地带
- cloud_sect (青云宗) - 修仙门派
```

### 查看单个实体详情

```
用户: 青云宗是什么样的势力？

AI: 让我查看一下...
[COMMAND] query_world {
  "entity_id": "cloud_sect"
}

结果:
- 名称: 青云宗
- 类型: person/organization
- 状态: active
- 描述: 冀州最大的修仙门派...
- 规则:
  - 禁止弟子私斗
  - 筑基以上才能收徒
- 关联:
  → 青河镇 — 所属势力
  → 掌门 — 青云子
```

### 获取关系图谱

```
用户: 各个实体之间有什么关系？

AI: 让我生成关系图谱...
[COMMAND] get_world_relations {}

结果:
实体: 青河镇, 黑森林, 青云宗, 魔教...
关系:
- 青河镇 → 青云宗 (所属势力)
- 黑森林 → 青云宗 (敌对势力)
- 主角 → 青云宗 (所属势力)
```

## 创建实体的时机

当用户提到新的地点、人物、法宝等时，AI 应该主动建议创建实体：

```
用户: 主角要去一座神秘的山脉探险

AI: 好的！我来创建一个「神秘山脉」的实体...
```

## 实体文件格式

实体存储在 `data/novels/{novel_id}/src/world/entities/` 目录下：

```markdown
# 神秘山脉

> location | mountain | active

位于冀州北部，终年被迷雾笼罩。

## 规则
- 进入者会迷失方向
- 山顶有一座古遗迹

## 关联
- 青云宗 — 探索者
- 主角 — 探险者
```

## 关系类型

常见关系类型：
- `所属势力` - 某人/某物属于某个组织
- `位于` - 地点在哪
- `敌对` - 敌对关系
- `友好` - 友好关系
- `探索` - 探索关系
- `传承` - 功法/血脉传承
