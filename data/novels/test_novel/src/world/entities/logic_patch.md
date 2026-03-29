+++
id = "logic_patch"
name = "补丁"
type = "concept"
subtype = "method"
status = "active"
summary = "陈明对局部异常干预的程序员式命名，强调短期修复、代价控制和后续技术债。"
tags = ["方法", "异常处理", "程序员思维"]
detail_refs = ["规则", "特征", "关联"]

[[related]]
target = "chen_ming"
kind = "used_by"
weight = 0.91
note = "主角最先稳定掌握的方法"

[[related]]
target = "shufa_system"
kind = "belongs_to"
weight = 0.75
note = "属于术式推演的实际应用"
+++

# 补丁

## 规则
- 补丁的本质是局部修复，不解决全部根因。
- 打得太急会留下更大的技术债，打得太慢则可能压不住异常蔓延。
- 只有真正看见逻辑链的人，才能判断补丁应该打在什么位置。

## 特征
- 符合陈明的命名习惯，既不浪漫，也不神秘。
- 常表现为临时修复、路径绕行、局部封堵和条件切断。
- 是前中期最重要的行动方法之一。

## 关联
- chen_ming — 方法提出者与主要实践者
- shufa_system — 所属能力体系
- server_anomaly — 第一批使用场景之一
