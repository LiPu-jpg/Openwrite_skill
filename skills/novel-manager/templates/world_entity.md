# 世界观实体模板 (Markdown 格式)
#
# 文件路径: data/novels/{novel_id}/src/world/entities/{entity_id}.md
# 文件名即 ID（如 shufa_system.md → id = shufa_system）
#
# 解析规则：
#   - H1 标题 = 实体名称
#   - 第一个 blockquote = 元数据行（type | subtype | status）
#   - H1 后的第一段正文 = 描述（description）
#   - ## 规则 = rules 列表
#   - ## 特征 = features 列表
#   - ## 关联 = related entities（格式: entity_id — 说明）
#   - 其他 ## 段落 = 自由扩展内容
#
# 与 YAML 版对比：
#   ✅ 多行文字直接换行，无需引号/管道符
#   ✅ 无 chapters 列表（由 world_query.py 从大纲自动提取）
#   ✅ 人类可读可编辑
#   ✅ world_query.py 可解析为结构化数据

---

# 天衡档案馆

> location | building | active

一座中立的信息机构，只有持有通行凭证的人才能进入。
外表看起来只是普通档案楼，内部却有严格的检索与交换系统。

## 规则

- 需令牌进入，无令者不得接近百步之内
- 情报交易需要支付代价（非金钱，而是等价情报）
- 阁内禁止武力冲突，违者被永久列入黑名单
- 所有交易不记录，档案馆不为任何势力站台

## 特征

- 藏书万卷，涵盖天下大小事
- 遍布天下的情报网，耳目众多
- 严格中立，不参与任何势力纷争
- 阁主身份神秘，极少露面

## 关联

- archive_token — 通行凭证，进入档案馆的唯一凭证
- archive_keeper — 档案管理员，馆中最高权限者

## 备注

这类机构的定位类似于中立的信息黑市。在设定上需要注意：
它的“中立”不是善意的，而是利益驱动的绝对中立。
任何人只要付得起代价，都能获取情报，无论善恶。
