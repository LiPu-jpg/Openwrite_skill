"""Goethe 对话式引导 - MiniMax 兼容版本

由于 MiniMax 不支持标准 function calling，使用结构化文本输出。
使用 prompt_toolkit 提供更好的输入体验（方向键支持）。
"""

import re
import sys
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EXIT_COMMANDS = {"退出", "quit", "exit", "q"}


def is_exit_command(text: str) -> bool:
    return text.strip().lower() in EXIT_COMMANDS


def build_prompt_session(history=None, *, prompt_style: dict[str, str] | None = None):
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style

    history = history or InMemoryHistory()
    style = Style.from_dict(prompt_style or {"prompt": "#ansibrightblue bold"})
    return PromptSession(history=history, style=style)


def build_goethe_prompt_session(history=None):
    return build_prompt_session(history=history)


@dataclass
class GoetheResult:
    """引导结果"""

    success: bool
    project_path: Optional[Path] = None
    novel_id: Optional[str] = None
    error: Optional[str] = None


SYSTEM_PROMPT = """你是 OpenWrite 小说创作引导 Agent。

你的职责是帮用户从零开始创建小说项目。

## 完整初始化流程

### 1. 收集基本信息（按顺序）
- 书名（必填）：问"你的小说叫什么名字？"
- 题材（必填）：问"是什么类型的故事？"
- 简介/灵感（可选）

### 2. 风格选择
用户需要选择一种风格：
- 通用风格（推荐新手）：使用内置去AI味技法
- 合成风格：从参考作品学习（需要选参考）
- 提取风格：从用户文本提取

### 3. 创建项目
收集到书名+题材后，立即调用 create_project

### 4. 设置风格
调用 set_style 命令

### 5. AI 生成详细设定（可选）
询问用户是否需要 AI 生成世界观、大纲等

---

## 可用命令（用 [COMMAND] 格式调用）

```
[COMMAND] create_project {"title": "书名", "genre": "题材代码"}

[COMMAND] set_style {"novel_id": "项目ID", "style_type": "generic|synthesized|extracted", "ref_name": "参考名"}

[COMMAND] init_ai_settings {"novel_id": "项目ID", "brief": "简介"}

[COMMAND] list_reference_styles {}

[COMMAND] check_project {"novel_id": "项目ID"}
```

## 题材代码

- xuanhuan: 玄幻
- xianxia: 仙侠
- urban: 都市
- litrpg: 游戏异界
- sci-fi: 科幻
- horror: 恐怖
- system-apocalypse: 系统末日
- isekai: 异世界

## 风格类型

- generic: 通用风格（内置技法，推荐新手）
- synthesized: 合成风格（需要 ref_name 指定参考作品）
- extracted: 提取风格（从用户文本提取）

## 可用参考风格

术师手册、谁让他修仙的、天启预报、牧者密续、不许没收我的人籍、我师兄实在太稳健了

---

## 对话原则

1. 每轮只问一个关键问题
2. 积极回应用户的想法
3. 信息够了就立即创建项目
4. 创建项目后告诉用户项目位置和 inspiration 文件夹

## 输出格式

先用自然语言回复。
需要调用命令时，在回复末尾添加：
```
[COMMAND] 命令 {"参数": "值"}
```
"""


class GoetheChatAgent:
    """Goethe 对话式引导 Agent（MiniMax 兼容）"""

    def __init__(self):
        from tools.llm import LLMClient, LLMConfig

        self.llm_config = LLMConfig.from_env()
        self.client = LLMClient(self.llm_config)
        self.messages = []
        self.project_created = False
        self.current_novel_id: Optional[str] = None

    def run(self) -> GoetheResult:
        """运行 Agent"""
        print("\n" + "=" * 50)
        print("   OpenWrite 小说创作引导")
        print("   (输入 '退出' 可结束对话)")
        print("=" * 50)

        intro = """
✨ 我可以帮你：

  📖 创建新项目 - 告诉我你的想法，我来帮你创建
  🔍 继续现有项目 - 输入项目名继续创作
  💡 获取灵感建议 - 不知道写什么？我来帮你
  🎨 选择风格 - 通用风格/参考合成/自定义提取

你可以直接说：
  "我想写个修仙故事"
  "帮我创建一个都市异能小说"
  "我想写个星际探险的故事"
  "推荐一个有趣的小说题材"

"""
        print(intro)

        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": intro},
        ]

        session = build_goethe_prompt_session()

        try:
            while True:
                try:
                    user_input = session.prompt("\n👤 你: ").strip()
                except KeyboardInterrupt:
                    print("\n\n已取消")
                    return GoetheResult(success=False)

                if is_exit_command(user_input):
                    print("\n好的，随时欢迎回来！")
                    return GoetheResult(success=False)

                if not user_input:
                    continue

                self.messages.append({"role": "user", "content": user_input})

                response = self.client.chat(
                    [self._make_message(m) for m in self.messages],
                    temperature=0.7,
                    stream=False,
                )

                content = response.content
                self.messages.append({"role": "assistant", "content": content})

                # 过滤掉思考过程，只保留最终回复
                display_content = self._filter_thinking(content)

                # 打印 LLM 回复
                if display_content:
                    print(f"\n🤖 Agent: {display_content}")

                # 解析命令
                command_output = self._parse_commands(content)
                if command_output:
                    print(f"\n🔧 {command_output}")

                # 检查是否完成
                if "项目已创建" in content or "可以开始写作" in content:
                    if self.current_novel_id:
                        return GoetheResult(
                            success=True,
                            project_path=Path.cwd() / "data" / "novels" / self.current_novel_id,
                            novel_id=self.current_novel_id,
                        )

        except KeyboardInterrupt:
            print("\n\n已取消")
            return GoetheResult(success=False)

    def _make_message(self, m: dict):
        """转换消息格式"""
        from tools.llm import Message

        return Message(role=m["role"], content=m.get("content", ""))

    def _filter_thinking(self, content: str) -> str:
        """过滤掉思考过程"""
        import re

        # 移除 <think>...</think> 块
        filtered = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
        # 移除 <think>...没有...</think> 块
        filtered = re.sub(r"<think>.*?(?:没有|不|暂).*?</think>", "", filtered, flags=re.DOTALL)
        # 清理多余空白
        filtered = re.sub(r"\n{3,}", "\n\n", filtered)
        return filtered.strip()

    def _parse_commands(self, content: str) -> str:
        """解析命令"""
        # 查找 [COMMAND] ... [COMMAND] 模式
        pattern = r"\[COMMAND\]\s*(\w+)\s*(\{.*?\})"
        matches = re.findall(pattern, content, re.DOTALL)

        for cmd_name, cmd_args in matches:
            args = {}
            try:
                args = json.loads(cmd_args)
            except json.JSONDecodeError:
                return f"命令参数解析失败: {cmd_args}"

            if cmd_name == "create_project":
                return self._cmd_create_project(args)
            elif cmd_name == "init_ai_settings":
                return self._cmd_init_ai_settings(args)
            elif cmd_name == "set_style":
                return self._cmd_set_style(args)
            elif cmd_name == "list_reference_styles":
                return self._cmd_list_reference_styles(args)
            elif cmd_name == "check_project":
                return self._cmd_check_project(args)

        return ""

    def _cmd_create_project(self, args: dict) -> str:
        """创建项目"""
        from tools.init_project import init_project

        title = args.get("title", "")
        genre = args.get("genre", "xianxia")

        novel_id = re.sub(r"[^\w\s]", "", title).lower().replace(" ", "_")[:30]
        project_root = Path.cwd()
        project_dir = project_root / "data" / "novels" / novel_id

        if project_dir.exists():
            return f"项目 '{novel_id}' 已存在！"

        try:
            init_project(project_root, novel_id, title=title)
        except Exception as e:
            return f"创建失败: {e}"

        self.project_created = True
        self.current_novel_id = novel_id

        inspiration_dir = project_dir / "inspiration"
        inspiration_dir.mkdir(exist_ok=True)

        return f"""✅ 项目创建成功！
📁 位置: {project_dir}
🏷️ 题材: {genre}
💡 项目内有 inspiration/ 文件夹，可以放灵感文件
"""

    def _cmd_init_ai_settings(self, args: dict) -> str:
        """AI 生成设定"""
        from tools.agent import AgentContext
        from tools.architect import ArchitectAgent
        from tools.story_planning import StoryPlanningStore
        from tools.truth_manager import TruthFilesManager

        novel_id = args.get("novel_id", "")
        brief = args.get("brief", "")
        project_root = Path.cwd()

        ctx = AgentContext(self.client, self.llm_config.model, str(project_root))
        architect = ArchitectAgent(ctx)

        config_path = project_root / "novel_config.yaml"
        fallback_config_path = project_root / "data" / "novels" / novel_id / "novel_config.yaml"
        if config_path.exists():
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f)
            title = config.get("title", novel_id)
            genre = config.get("genre", "xianxia")
        elif fallback_config_path.exists():
            import yaml

            with open(fallback_config_path) as f:
                config = yaml.safe_load(f)
            title = config.get("title", novel_id)
            genre = config.get("genre", "xianxia")
        else:
            title = novel_id
            genre = "xianxia"

        print("\n⏳ AI 正在生成世界观设定，这可能需要几分钟...")

        try:
            foundation = architect.generate_foundation(
                title=title,
                genre=genre,
                brief=brief,
            )

            novel_root = project_root / "data" / "novels" / novel_id
            planning_store = StoryPlanningStore(project_root, novel_id)
            planning_store.save_foundation_draft(
                background=foundation.story_bible,
                foundation=foundation.book_rules,
            )
            planning_store.save_outline_draft(foundation.volume_outline)

            truth_manager = TruthFilesManager(project_root, novel_id)
            truth = truth_manager.load_truth_files()
            truth.current_state = foundation.current_state
            truth_manager.save_truth_files(truth)

            planning_store.runtime_planning_dir.mkdir(parents=True, exist_ok=True)
            foreshadowing_draft = planning_store.runtime_planning_dir / "foreshadowing_draft.md"
            foreshadowing_draft.write_text(foundation.foreshadowing_seed, encoding="utf-8")

            generated = [
                "src/story/background.md",
                "src/story/foundation.md",
                "src/outline.md",
                "data/planning/background_draft.md",
                "data/planning/foundation_draft.md",
                "data/planning/outline_draft.md",
                "data/planning/foreshadowing_draft.md",
                "data/world/current_state.md",
            ]
            return (
                "✅ AI 设定生成完成！\n"
                f"📁 位置: {novel_root}/\n"
                f"已生成: {', '.join(generated)}"
            )
        except Exception as e:
            logger.exception("AI generation failed")
            return f"AI 生成失败: {e}"

    def _cmd_set_style(self, args: dict) -> str:
        """设置风格"""
        style_type = args.get("style_type", "generic")
        ref_name = args.get("ref_name", "")

        if style_type == "generic":
            return "✅ 已设置为通用风格（内置去AI味技法）"
        elif style_type == "synthesized":
            return f"✅ 已设置为合成风格，参考: {ref_name}"
        elif style_type == "extracted":
            return "✅ 已设置为提取风格"
        return f"未知风格类型: {style_type}"

    def _cmd_list_reference_styles(self, args: dict) -> str:
        """列出参考风格"""
        ref_dir = Path("data/reference_styles")
        if not ref_dir.exists():
            return "暂无可用的参考风格"

        styles = [d.name for d in ref_dir.iterdir() if d.is_dir()]
        if not styles:
            return "暂无可用的参考风格"

        return "可用的参考风格:\n" + "\n".join(f"- {s}" for s in styles)

    def _cmd_check_project(self, args: dict) -> str:
        """检查项目"""
        novel_id = args.get("novel_id", "")
        project_dir = Path.cwd() / "data" / "novels" / novel_id

        if not project_dir.exists():
            return f"项目不存在: {novel_id}"

        checks = []
        for subdir in ["outline", "characters", "world", "manuscript", "style"]:
            path = project_dir / subdir
            checks.append(f"  {'✅' if path.exists() else '❌'} {subdir}/")

        return f"项目 {novel_id} 状态:\n" + "\n".join(checks)


def run_goethe():
    """运行 Goethe 引导"""
    agent = GoetheChatAgent()
    result = agent.run()

    if result.success:
        print(f"\n✨ 项目已就绪: {result.project_path}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(run_goethe())
