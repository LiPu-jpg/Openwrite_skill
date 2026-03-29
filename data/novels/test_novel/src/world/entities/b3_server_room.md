+++
id = "b3_server_room"
name = "B3机房"
type = "location"
subtype = "restricted_area"
status = "active"
summary = "公司地下一层之下的老旧机房区域，现行排班里几乎没人提它，却不断在值班单和异常噪声里反复出现。"
tags = ["地点", "机房", "异常节点"]
detail_refs = ["规则", "特征", "关联"]

[[related]]
target = "company"
kind = "located_in"
weight = 0.94
note = "位于公司地下层"

[[related]]
target = "server_anomaly"
kind = "source_of"
weight = 0.79
note = "多条异常线索都回指这里"
+++

# B3机房

## 规则
- 不在普通值班排班的公开视野里，却不断出现在异常记录里。
- 机房噪声像是有延迟的回声，常伴随不可解释的温度波动和丢失日志。
- 靠近这里的人更容易看见逻辑链错位或时间感短暂紊乱。

## 特征
- 老旧、封闭、灯光偏冷，像被遗忘的项目残骸。
- 有一套与现行命名不一致的设备编号系统。
- 旧值班单、残缺签名和幽灵调用都与它相关。

## 关联
- company — 所属地点
- server_anomaly — 异常日志来源之一
- chen_ming — 第一位在样例中主动追查此处的人
