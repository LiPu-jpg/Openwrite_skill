# OpenWrite - AI 辅助小说创作引擎

**版本**: 5.4.0

---

## 一分钟速览

```bash
# 方式1: 交互式引导（推荐新手）
openwrite wizard

# 方式2: 命令行
openwrite init my_novel          # 初始化
openwrite radar                  # 市场分析
openwrite agent "创建大纲"       # AI 生成设定
openwrite write next             # 写章节
openwrite review                 # 审查
openwrite status                 # 查看状态
```

---

## 目录

- [安装](#二-安装)
- [快速开始](#三-快速开始)
- [三种使用方式](#四-三种使用方式)
- [完整工作流程](#五-完整工作流程)
- [项目结构](#六-项目结构)
- [数据格式模板](#七-数据格式模板)
- [CLI 命令参考](#八-cli-命令参考)
- [Skill 使用指南](#九-skill-使用指南)
- [常见问题](#十-常见问题)

---

## 二、安装

### 1. 克隆项目

```bash
git clone <repo_url>
cd Openwrite_skill-main
```

### 2. 安装依赖

```bash
pip install -e .
# 或
pip install pydantic pyyaml openai anthropic
```

### 3. 配置 API Key

```bash
# 环境变量（推荐）
export LLM_API_KEY=sk-xxx
export LLM_MODEL=gpt-4o-mini
export LLM_PROVIDER=openai  # 或 anthropic

# 或创建 .env 文件
echo "LLM_API_KEY=sk-xxx" > .env
```

### 4. 验证安装

```bash
openwrite --version
openwrite --help
```

---

## 三、快速开始

### 新手推荐：交互式引导

```bash
openwrite wizard
```

引导会问你：
1. 书名
2. 题材（玄幻/仙侠/都市/...）
3. 目标字数
4. 是否用 AI 生成设定

### 命令行方式

```bash
# 1. 初始化项目
openwrite init my_novel

# 2. 进入项目目录
cd my_novel

# 3. 市场分析（可选）
openwrite radar

# 4. AI 生成设定（可选）
openwrite agent "帮我创建一个都市异能小说的大纲"

# 5. 开始写作
openwrite write next

# 6. 审查
openwrite review

# 7. 继续写下一章
openwrite write next
```

---

## 四、三种使用方式

### 方式 1: Skill（推荐，配合 Claude Code 使用）

直接用自然语言告诉 Claude：

```
写第五章
查看项目状态
帮我创建一个新角色
分析一下市场趋势
```

Claude 会读取 `SKILL.md` 并路由到对应技能。

### 方式 2: CLI（命令行）

```bash
openwrite init my_novel           # 初始化
openwrite write next              # 写下一章
openwrite write ch_005            # 写第5章
openwrite review                   # 审查最新章节
openwrite review ch_003           # 审查第3章
openwrite context ch_005 --show   # 查看上下文
openwrite status                   # 项目状态
openwrite radar                   # 市场分析
openwrite agent "写第五章"        # ReAct Agent
```

### 方式 3: Python API

```python
from tools import ContextBuilder, WriterAgent, ReviewerAgent
from tools.llm import LLMClient, LLMConfig
from tools.agent import AgentContext

# 初始化
config = LLMConfig.from_env()
client = LLMClient(config)
ctx = AgentContext(client, config.model, project_root)

# 构建上下文
builder = ContextBuilder(project_root, novel_id)
context = builder.build_generation_context("ch_005")

# 写作
writer = WriterAgent(ctx)
result = await writer.write_chapter(context, chapter_number=5)

# 审查
reviewer = ReviewerAgent(ctx)
review = await reviewer.review(content=result.content, context={})
```

---

## 五、完整工作流程

### 5.1 项目初始化

```
openwrite wizard
    ↓
输入书名、题材、目标
    ↓
（可选）AI 生成设定
    ↓
项目创建完成
    ↓
data/novels/{小说名}/
├── outline/          # 大纲
├── characters/       # 角色
├── world/           # 世界观
├── foreshadowing/   # 伏笔
├── style/          # 风格
├── manuscript/      # 草稿
└── workflows/      # 流程状态
```

### 5.2 写作流程

```
用户: "写第五章"
    ↓
1. 上下文组装
    ├── 大纲窗口（前后5章）
    ├── 出场角色（静态+动态合并）
    ├── 伏笔状态（DAG）
    ├── 三层风格
    ├── 世界观规则
    └── 真相文件
    ↓
2. 确定戏剧位置
    ├── 从节/篇获取 arc/section 弧线
    └── 确定章的 position（起/承/转/合/过渡）
    ↓
3. 生成节拍
    └── 按 position 选择节拍模板
    ↓
4. 两阶段写作
    ├── Phase 1: 创意写作 (temp=0.7)
    ├── Phase 1.5: 后置验证（零成本）
    ├── Phase 2: 状态结算
    └── Phase 2.5: 状态验证
    ↓
5. AI 审查（33维度）
    ├── 逻辑检查
    ├── AI 痕迹检测
    └── 敏感词检查
    ↓
6. 用户确认 ⏸️
    ↓
7. 风格润色
    ↓
8. 保存 + 快照
```

### 5.3 真相文件系统

每次写完章节，AI 自动更新：

```
story/
├── current_state.md      # 世界当前状态
├── particle_ledger.md   # 资源账本（钱/物品/境界）
├── pending_hooks.md     # 伏笔列表
├── chapter_summaries.md # 章节摘要
├── subplot_board.md    # 支线进度
├── emotional_arcs.md   # 情感弧线
└── character_matrix.md # 角色关系
```

**为什么需要真相文件？**

防止 AI 写久了忘记前面的设定：
- 第5章在京城，第20章突然回到青河镇
- 主角明明获得了神剑，后面又没有了
- 配角性格前后不一致

---

## 六、项目结构

```
OpenWrite/
├── SKILL.md                    # 根入口（Claude 读取）
│
├── skills/                     # 技能层
│   ├── novel-creator/         # 写作流程
│   ├── novel-manager/         # 数据管理
│   ├── novel-reviewer/        # 审查润色
│   └── style-system/          # 风格系统
│
├── tools/                      # Python 工具
│   ├── cli.py                 # CLI 入口
│   ├── context_builder.py     # 上下文组装
│   ├── writer.py              # 写作 Agent
│   ├── reviewer.py            # 审核 Agent
│   ├── react.py               # ReAct Agent
│   ├── architect.py           # 大纲生成 Agent
│   ├── radar.py               # 市场分析
│   ├── wizard.py              # 交互引导
│   ├── truth_manager.py       # 真相文件
│   ├── foreshadowing_manager.py # 伏笔 DAG
│   ├── progressive_compressor.py # 渐进压缩
│   └── llm/                   # LLM 客户端
│
├── models/                     # 数据模型
│   ├── outline.py             # 四级大纲
│   ├── character.py           # 角色
│   ├── style.py              # 风格
│   └── context_package.py     # 上下文
│
├── craft/                     # 写作技法
│   ├── humanization.yaml      # 去AI味规则
│   ├── ai_patterns.yaml      # AI痕迹检测
│   ├── dialogue_craft.md     # 对话技法
│   ├── scene_craft.md        # 场景技法
│   └── rhythm_craft.md       # 节奏技法
│
└── data/
    ├── reference_styles/       # 6部参考风格
    │   ├── 术师手册/
    │   ├── 谁让他修仙的/
    │   └── ...
    │
    └── novels/{id}/          # 用户项目
        ├── outline/
        ├── characters/
        ├── world/
        ├── foreshadowing/
        ├── style/
        ├── manuscript/
        └── workflows/
```

---

## 七、数据格式模板

### 7.1 大纲格式（四级结构）

```markdown
# 我的小说

## 第一篇：修炼篇

> 篇弧线: 铺垫(sec01-02) → 发展(sec03-05) → 高潮(sec06) → 收束(sec07)

### 第一节：师门试炼

> 节结构: 起(ch01) → 承(ch02-03) → 转(ch04) → 合(ch05)

#### 第一章：入门

> 戏剧位置: 起
> 内容焦点: 主角拜师入门
> 出场角色: zhang_san, master_yun
```

### 7.2 角色卡片（YAML）

```yaml
# data/novels/{id}/characters/cards/zhang_san.yaml
id: zhang_san
name: 张三
tier: protagonist
age: 18
occupation: 修士
description: 主角
relationships:
  - character_id: master_yun
    relation_type: master
    description: 师父
status: active
```

### 7.3 角色档案（Markdown，静态信息）

```markdown
# data/novels/{id}/characters/profiles/zhang_san.md

# 张三

## 基本信息
- **层级**: protagonist
- **年龄**: 18
- **身份**: 修士
- **首次出场**: ch_001

## 外貌
中等身材，眉目清秀

## 性格
- 沉默寡言
- 外冷内热
- 重情重义

## 背景
青河镇普通少年，偶得机缘踏入修炼之路
```

### 7.4 世界实体

```markdown
# data/novels/{id}/world/entities/qinghe_town.md

> location | 城镇 | active

青河镇，位于冀州北部的古老小镇。

## 规则
- 禁止修士在镇内斗法

## 关联
- 青云宗 — 所属势力
```

### 7.5 伏笔（DAG）

```yaml
# data/novels/{id}/foreshadowing/dag.yaml
nodes:
  - id: H01
    content: 主角获得神秘玉佩
    weight: 8
    layer: 主线
    status: 待收
    target_chapter: ch_010
  - id: H02
    content: 师父的秘密
    weight: 6
    layer: 支线
    status: 埋伏
```

### 7.6 真相文件示例

```markdown
# story/current_state.md

## 世界状态

| 字段 | 值 |
|------|-----|
| 当前章节 | 5 |
| 主角位置 | 妖兽森林 |
| 主角状态 | 筑基初期 |
| 当前目标 | 找到千年灵芝 |
| 当前敌我 | 与黑狼寨结仇 |

---

# story/pending_hooks.md

| hook_id | 伏笔内容 | 埋设章节 | 预期回收 |
|---------|----------|----------|----------|
| H01 | 主角获得神秘玉佩 | ch_003 | ch_010 |
| H02 | 师父的秘密 | ch_001 | ch_015 |

---

# story/character_matrix.md

### 主角状态

| 字段 | 值 |
|------|-----|
| 位置 | 妖兽森林 |
| 状态 | 筑基初期 |

### 角色关系

| 角色A | 角色B | 关系 | 首次出现 |
|-------|-------|------|----------|
| 张三 | 师父 | 师徒 | ch_001 |
| 张三 | 李四 | 挚友 | ch_002 |
```

---

## 八、CLI 命令参考

### 初始化与管理

| 命令 | 说明 |
|------|------|
| `openwrite wizard` | 交互式引导（推荐）|
| `openwrite init <id>` | 初始化项目 |
| `openwrite status` | 查看项目状态 |

### 写作相关

| 命令 | 说明 |
|------|------|
| `openwrite write next` | 写下一章 |
| `openwrite write ch_005` | 写第5章 |
| `openwrite review` | 审查最新章节 |
| `openwrite review ch_005` | 审查第5章 |
| `openwrite context ch_005 --show` | 查看第5章上下文 |

### AI Agent

| 命令 | 说明 |
|------|------|
| `openwrite agent "写第五章"` | ReAct Agent（自然语言）|
| `openwrite radar` | 市场趋势分析 |
| `openwrite agent "创建大纲"` | AI 生成设定 |

### 风格系统

| 命令 | 说明 |
|------|------|
| `openwrite style extract <name> --source <file>` | 从文本提取风格 |

### 全局选项

| 选项 | 说明 |
|------|------|
| `--help` | 显示帮助 |
| `--version` | 显示版本 |

---

## 九、Skill 使用指南

### 9.1 Skill 路由表

当你对 Claude 说这些话时，会触发对应 Skill：

| 你说 | 触发 | 说明 |
|------|------|------|
| "写第五章"、"续写" | novel-creator | 写作流程 |
| "创建角色"、"查看大纲" | novel-manager | 数据管理 |
| "审查章节"、"润色" | novel-reviewer | 审查润色 |
| "风格初始化"、"提取风格" | style-system | 风格系统 |

### 9.2 写作流程（novel-creator）

```
1. 解析意图 → 提取章节 ID
2. 组装上下文
   ├── 大纲窗口
   ├── 出场角色（静态 + 动态）
   ├── 伏笔状态
   ├── 三层风格
   ├── 世界观规则
   └── 真相文件
3. 确定戏剧位置
4. 生成节拍
5. 两阶段写作
   ├── Phase 1: 创意写作
   ├── Phase 1.5: 后置验证
   ├── Phase 2: 状态结算
   └── Phase 2.5: 状态验证
6. 用户审核 ⏸️
7. 风格润色
8. 保存
```

### 9.3 审查（novel-reviewer）

33 维度检查：

| 类别 | 维度 | 说明 |
|------|------|------|
| 逻辑类 | 1-9 | OOC、时间线、战力、数值等 |
| 质量类 | 10-19 | 词汇疲劳、信息倾倒等 |
| AI痕迹类 | 20-23 | 段落等长、套话密度、转折词 |
| 高级审计 | 24-37 | 支线、情感、期待管理等 |

### 9.4 去 AI 味

OpenWrite 有完整的去 AI 味系统：

**craft/humanization.yaml** - 写作规则：
- 禁用词表（48个）："然而"→"但是"
- 自然不完美规则：允许碎片句、口语化
- 句式变化：30-40% 短句

**craft/ai_patterns.yaml** - AI 痕迹检测：
- 禁用词检测
- 套话密度检测
- 结构模式检测

### 9.5 三层风格架构

```
Layer 1: craft/              → 通用技法（去AI味）
Layer 2: reference_styles/   → 参考风格（你喜欢的小说）
Layer 3: novels/{id}/       → 你自己的设定
         ↓ 合成
    composed.md → 注入写作上下文
```

---

## 十、常见问题

### Q: 报错 "API Key not found"

```bash
export LLM_API_KEY=sk-xxx
```

### Q: 报错 "未找到 novel_config.yaml"

```bash
cd 项目目录
openwrite init my_novel
```

### Q: 真相文件在哪里？

```bash
data/novels/{id}/story/
```

### Q: 如何从参考作品提取风格？

```bash
openwrite style extract 术师手册 --source 术师手册.txt
```

### Q: 如何查看大纲？

Claude 说"查看大纲"，或：

```bash
cat data/novels/{id}/outline/outline.md
```

### Q: 如何管理伏笔？

Claude 说"查看伏笔状态"，或编辑：

```bash
data/novels/{id}/foreshadowing/dag.yaml
```

### Q: 写作时 AI 忘记前面的设定怎么办？

真相文件会自动追踪，每次写完章节自动更新。确保：
1. 真相文件存在
2. 章节写完后 AI 自动更新

### Q: 如何回滚到之前的状态？

```python
from tools import TruthFilesManager

manager = TruthFilesManager(project_root, novel_id)
snapshots = manager.list_snapshots()
manager.restore_snapshot("snapshot_5_20260325")
```

---

## 十一、环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | API Key | - |
| `LLM_MODEL` | 模型 | gpt-4o-mini |
| `LLM_PROVIDER` | 提供商 | openai |
| `LLM_BASE_URL` | API 地址 | https://api.openai.com/v1 |
| `LLM_TEMPERATURE` | 温度 | 0.7 |
| `LLM_MAX_TOKENS` | 最大 Token | 8192 |
| `LLM_STREAM` | 流式输出 | true |

---

## 十二、版本历史

| 版本 | 日期 | 变化 |
|------|------|------|
| 5.4.0 | 2026-03-25 | 角色档案与真相文件职责分离 |
| 5.3.0 | 2026-03-05 | ReAct Agent、雷达市场分析 |
| 5.2.0 | 2026-03-01 | 33维度审核、真相文件 |
| 5.1.0 | 2026-02-15 | 四级大纲、节拍模板 |
| 5.0.0 | 2026-02-01 | 初始版本 |

---

*OpenWrite - 让 AI 帮你写小说*
