"""建筑师 Agent - 从 InkOS architect.ts 融合

AI 辅助创建大纲、世界观、角色设定。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class FoundationResult:
    """基础设定生成结果"""

    story_bible: str
    volume_outline: str
    book_rules: str
    current_state: str
    pending_hooks: str


@dataclass
class ChapterOutline:
    """章节大纲"""

    number: int
    title: str
    summary: str
    dramatic_position: str  # 起/承/转/合/过渡
    content_focus: str
    goals: list[str] = field(default_factory=list)


class ArchitectAgent:
    """建筑师 Agent

    AI 辅助创建：
    - 世界观设定
    - 大纲规划
    - 写作规则
    - 初始状态

    用法:
        architect = ArchitectAgent(ctx)
        result = await architect.generate_foundation(
            title="我的修仙小说",
            genre="xianxia",
            brief="一个普通少年的修仙之路"
        )
    """

    GENRE_GUIDES = {
        "xuanhuan": "玄幻：东方仙侠世界，修炼境界（金丹、元婴等），门派纷争，奇遇流",
        "xianxia": "仙侠：修真文明，飞剑法宝，炼丹炼器，人与天地争斗",
        "urban": "都市：现代都市背景，异能/风水/相术等都市传说",
        "litrpg": "游戏异界：游戏系统降临，等级副本，技能装备",
        "sci-fi": "科幻：星际文明，未来科技，赛博朋克",
        "horror": "恐怖：悬疑惊悚，灵异事件",
        "system-apocalypse": "系统末日：末日降临，系统觉醒，生存挣扎",
        "isekai": "异世界：转生异界，种田/冒险/魔法",
        "cultivation": "修真：同仙侠但更注重个人修炼",
        "dungeon-core": "地下城核心：成为地下城意识体",
        "tower-climber": "塔爬：攀登高塔，每层不同挑战",
        "progression": "进阶流：主角实力稳步提升",
        "romantasy": "浪漫幻想：奇幻背景的浪漫故事",
        "cozy": "温馨流：轻松日常，节奏舒缓",
    }

    def __init__(self, agent_ctx: Any):
        """初始化建筑师

        Args:
            agent_ctx: Agent 上下文
        """
        self.ctx = agent_ctx
        self.log = logger.getChild("architect")

    def generate_foundation(
        self,
        title: str,
        genre: str = "xuanhuan",
        brief: str = "",
        platform: str = "番茄",
    ) -> FoundationResult:
        """生成基础设定

        Args:
            title: 书名
            genre: 题材
            brief: 创作简述（作者自己的想法）
            platform: 目标平台

        Returns:
            FoundationResult 包含所有设定文件
        """
        self.log.info(f"Generating foundation for '{title}' ({genre})")

        # 获取题材指南
        genre_guide = self.GENRE_GUIDES.get(genre, self.GENRE_GUIDES["xuanhuan"])

        # 生成世界观
        story_bible = self._generate_story_bible(title, genre, genre_guide, brief)

        # 生成卷纲
        volume_outline = self._generate_volume_outline(title, genre, story_bible, brief)

        # 生成写作规则
        book_rules = self._generate_book_rules(title, genre, brief)

        # 生成初始状态
        current_state = self._generate_current_state(title, genre, story_bible, brief)

        # 生成伏笔
        pending_hooks = self._generate_pending_hooks(title, volume_outline)

        return FoundationResult(
            story_bible=story_bible,
            volume_outline=volume_outline,
            book_rules=book_rules,
            current_state=current_state,
            pending_hooks=pending_hooks,
        )

    async def generate_outline(
        self,
        title: str,
        genre: str,
        story_bible: str,
        target_chapters: int = 100,
    ) -> list[ChapterOutline]:
        """生成章节大纲

        Args:
            title: 书名
            genre: 题材
            story_bible: 世界观设定
            target_chapters: 目标章节数

        Returns:
            章节大纲列表
        """
        from tools.llm import Message

        system_prompt = """你是一个专业的小说大纲师。根据世界观设定，设计章节大纲。

输出 JSON 格式：
```json
[
  {
    "number": 1,
    "title": "章节标题",
    "summary": "章节内容概要（100字内）",
    "dramatic_position": "起/承/转/合/过渡",
    "content_focus": "本章核心内容",
    "goals": ["目标1", "目标2"]
  }
]
```

每5章为一个"节"，节内有起承转合。确保剧情有起伏。
只返回 JSON。"""

        user_prompt = f"""书名：{title}
题材：{genre}
目标章节数：{target_chapters}

世界观设定：
{story_bible[:2000]}

请生成{target_chapters}章的大纲。"""

        try:
            response = self.ctx.client.chat(
                messages=[
                    Message("system", system_prompt),
                    Message("user", user_prompt),
                ],
                temperature=0.5,
                max_tokens=8192,
            )

            return self._parse_chapter_outline(response.content, target_chapters)
        except Exception as e:
            self.log.error(f"Outline generation failed: {e}")
            return []

    async def generate_character(
        self,
        name: str,
        role: str,
        genre: str,
        story_bible: str = "",
    ) -> str:
        """生成角色设定

        Args:
            name: 角色名
            role: 角色定位（主角/配角/反派等）
            genre: 题材
            story_bible: 世界观（可选）

        Returns:
            角色设定 Markdown
        """
        from tools.llm import Message

        system_prompt = """你是一个专业的小说角色设计师。根据给定信息，设计角色设定。

输出 Markdown 格式的角色卡，包含：
- 基础信息（名字、年龄、身份等）
- 外貌特征
- 性格特点
- 背景故事
- 与主角的关系
- 说话风格
- 特殊能力（如果有）

保持角色真实立体，有优点也有缺点。"""

        user_prompt = f"""角色名：{name}
角色定位：{role}
题材：{genre}

世界观设定（如果有）：
{story_bible[:1000]}

请设计这个角色的详细设定。"""

        try:
            response = self.ctx.client.chat(
                messages=[
                    Message("system", system_prompt),
                    Message("user", user_prompt),
                ],
                temperature=0.7,
                max_tokens=4096,
            )

            return f"# {name}\n\n{response.content}"
        except Exception as e:
            self.log.error(f"Character generation failed: {e}")
            return f"# {name}\n\n角色生成失败：{e}"

    def _generate_story_bible(self, title: str, genre: str, genre_guide: str, brief: str) -> str:
        """生成世界观设定"""
        from tools.llm import Message

        system_prompt = """你是一个专业的网络小说世界观设计师。

根据以下信息，生成完整的**世界观设定文档**，包括：

1. **世界背景**：世界是什么样的（东方/西方/现代/异世界等）
2. **核心设定**：力量体系、社会结构、地理环境等
3. **主要势力**：门派/组织/国家等
4. **金手指/主角设定**：主角的特殊能力或机遇
5. **配角设定**：2-3个重要配角
6. **核心冲突**：故事的主要矛盾

格式要求：
- 使用 Markdown
- 层次分明，用 ## 标注章节
- 内容详实但不冗长
- 方便后续写作参考"""

        user_prompt = f"""书名：{title}
题材：{genre}
题材特点：{genre_guide}

作者的想法（如果有）：
{brief}

请生成世界观设定。"""

        response = self.ctx.client.chat(
            messages=[
                Message("system", system_prompt),
                Message("user", user_prompt),
            ],
            temperature=0.7,
            max_tokens=8192,
        )

        return response.content

    def _generate_volume_outline(self, title: str, genre: str, story_bible: str, brief: str) -> str:
        """生成卷纲"""
        from tools.llm import Message

        system_prompt = """你是一个专业的小说大纲师。

根据世界观设定，生成**卷纲（总大纲）**。

格式要求：
- 分为若干"篇"（Arc），每篇 15-30 章
- 每篇包含：篇名、核心冲突、转折点、结局
- 每篇内分为若干"节"（Section），每节 5 章左右
- 每节标注：起承转合位置

示例结构：
```
## 第一篇：入门（1-20章）
- 核心冲突：主角拜师考验
- 转折点：第10章通过考验
- 结局：正式入门

### 第一节（1-5章）
- 结构：起(1) → 承(2-3) → 转(4) → 合(5)
```

用 Markdown 输出。"""

        user_prompt = f"""书名：{title}
题材：{genre}

世界观设定：
{story_bible[:2000]}

作者想法：
{brief}

请生成卷纲。"""

        response = self.ctx.client.chat(
            messages=[
                Message("system", system_prompt),
                Message("user", user_prompt),
            ],
            temperature=0.5,
            max_tokens=8192,
        )

        return response.content

    def _generate_book_rules(self, title: str, genre: str, brief: str) -> str:
        """生成写作规则"""
        from tools.llm import Message

        system_prompt = """你是一个专业的小说编辑。

根据以下信息，生成**写作规则文档**，明确：
1. 主角性格锁定（不能崩）
2. 行为约束（什么不能做）
3. 题材禁忌（什么不能写）
4. 文风要求（什么风格）

格式简洁，用列表即可。"""

        user_prompt = f"""书名：{title}
题材：{genre}

作者想法：
{brief}

请生成写作规则。"""

        response = self.ctx.client.chat(
            messages=[
                Message("system", system_prompt),
                Message("user", user_prompt),
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        return f"# {title} 写作规则\n\n{response.content}"

    def _generate_current_state(self, title: str, genre: str, story_bible: str, brief: str) -> str:
        """生成初始状态"""
        from tools.llm import Message

        system_prompt = """你是一个小说设定专家。

根据世界观设定，生成**初始状态卡**（第0章状态）。

格式用表格：
| 字段 | 内容 |
|------|------|
| 当前章节 | 0 |
| 当前位置 | xxx |
| 主角状态 | xxx |
| 当前目标 | xxx |
| 当前限制 | xxx |
| 当前敌我 | xxx |
| 当前冲突 | xxx |

简洁填写即可。"""

        user_prompt = f"""世界观设定：
{story_bible[:1500]}

请生成初始状态卡。"""

        response = self.ctx.client.chat(
            messages=[
                Message("system", system_prompt),
                Message("user", user_prompt),
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        return f"# 当前状态（第0章）\n\n{response.content}"

    def _generate_pending_hooks(self, title: str, volume_outline: str) -> str:
        """生成伏笔列表"""
        from tools.llm import Message

        system_prompt = """你是一个小说伏笔专家。

根据大纲，识别并列出**主要伏笔**。

格式：
| hook_id | 伏笔内容 | 埋设章节 | 预期回收 | 类型 |
|---------|----------|----------|----------|------|
| H01 | xxx | 第3章 | 第15章 | 悬念 |

识别 5-10 个核心伏笔即可。
伏笔应该在合适时机回收，不要埋太多。"""

        user_prompt = f"""大纲：
{volume_outline[:2000]}

请列出主要伏笔。"""

        response = self.ctx.client.chat(
            messages=[
                Message("system", system_prompt),
                Message("user", user_prompt),
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        return f"# 伏笔列表\n\n{response.content}"

    def _parse_chapter_outline(self, content: str, target_count: int) -> list[ChapterOutline]:
        """解析章节大纲"""
        import json
        import re

        try:
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group(0))
                outlines = []
                for item in items:
                    outlines.append(
                        ChapterOutline(
                            number=item.get("number", 0),
                            title=item.get("title", ""),
                            summary=item.get("summary", ""),
                            dramatic_position=item.get("dramatic_position", "起"),
                            content_focus=item.get("content_focus", ""),
                            goals=item.get("goals", []),
                        )
                    )
                return outlines
        except json.JSONDecodeError:
            self.log.warning("Failed to parse chapter outline JSON")

        return []
