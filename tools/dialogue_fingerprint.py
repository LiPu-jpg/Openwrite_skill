"""对话指纹提取 - 从 InkOS writer.ts 融合

从最近章节提取角色对话风格特征。
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Optional


@dataclass
class DialogueFingerprint:
    """对话指纹"""

    character_name: str
    avg_sentence_length: float
    common_bigrams: list[str]
    question_ratio: float
    speech_patterns: list[str]

    def to_prompt_text(self) -> str:
        """转换为提示文本"""
        patterns = ", ".join(self.speech_patterns[:5])
        bigrams = ", ".join(self.common_bigrams[:5])
        return (
            f"{self.character_name}："
            f"平均句长{self.avg_sentence_length:.1f}字，"
            f"常用词组[{bigrams}]，"
            f"问句比例{self.question_ratio:.0%}，"
            f"口头禅[{patterns}]"
        )


class DialogueFingerprintExtractor:
    """对话指纹提取器

    从最近章节提取角色对话风格：

    1. 提取对话行
    2. 识别角色
    3. 统计：平均句长、常用词二元组、问句比例
    4. 识别口头禅模式

    用法:
        extractor = DialogueFingerprintExtractor()
        fingerprints = extractor.extract(chapters, character_names=["张三", "李四"])

        for fp in fingerprints:
            print(fp.to_prompt_text())
    """

    # 对话引号模式
    DIALOGUE_PATTERNS = [
        r'"([^"]+)"',  # 中文双引号
        r"'([^']+)'",  # 中文单引号
        r"「([^」]+)」",  # 日式引号
        r"『([^』]+)』",  # 日式双引号
    ]

    # 角色名前缀模式
    SPEAKER_PATTERNS = [
        r"^{name}[:：]\s*(.+)",  # 张三：xxx
        r"^{name}\s+(?!：)[^：]+：\s*(.+)",  # 张三 xxx：xxx
        r"「{name}」\s*(.+)",  # 「张三」xxx
        r"「(.+?)」\s*{name}\s*(.+)",  # 「xxx」张三 xxx
    ]

    def __init__(self, min_chapters: int = 3):
        """初始化提取器

        Args:
            min_chapters: 最小章节数
        """
        self.min_chapters = min_chapters

    def extract(
        self,
        chapters_content: list[str],
        character_names: list[str],
    ) -> list[DialogueFingerprint]:
        """提取对话指纹

        Args:
            chapters_content: 章节正文列表（按时间顺序）
            character_names: 要提取的角色名列表

        Returns:
            各角色的对话指纹
        """
        fingerprints = []

        # 收集所有对话
        all_dialogues: dict[str, list[str]] = {name: [] for name in character_names}

        for chapter_content in chapters_content:
            for name in character_names:
                dialogues = self._extract_character_dialogues(chapter_content, name)
                all_dialogues[name].extend(dialogues)

        # 提取每个角色的指纹
        for name, dialogues in all_dialogues.items():
            if len(dialogues) < 2:  # 至少2条对话
                continue

            fp = self._compute_fingerprint(name, dialogues)
            fingerprints.append(fp)

        return fingerprints

    def _extract_character_dialogues(self, content: str, character_name: str) -> list[str]:
        """提取指定角色的对话"""
        dialogues = []

        # 尝试各种角色名前缀模式
        patterns = [
            rf"{re.escape(character_name)}[:：]\s*(.{{1,100}})",
            rf"「{re.escape(character_name)}」\s*(.{{1,100}})",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            dialogues.extend(matches)

        return dialogues

    def _compute_fingerprint(
        self, character_name: str, dialogues: list[str]
    ) -> DialogueFingerprint:
        """计算对话指纹"""
        if not dialogues:
            return DialogueFingerprint(
                character_name=character_name,
                avg_sentence_length=0.0,
                common_bigrams=[],
                question_ratio=0.0,
                speech_patterns=[],
            )

        # 计算平均句长
        total_len = sum(len(d) for d in dialogues)
        avg_sentence_length = total_len / len(dialogues)

        # 计算问句比例
        question_count = sum(1 for d in dialogues if "？" in d or "?" in d)
        question_ratio = question_count / len(dialogues)

        # 计算常用词二元组
        bigrams = self._extract_bigrams("".join(dialogues))

        # 识别口头禅模式
        speech_patterns = self._extract_speech_patterns(dialogues)

        return DialogueFingerprint(
            character_name=character_name,
            avg_sentence_length=avg_sentence_length,
            common_bigrams=bigrams,
            question_ratio=question_ratio,
            speech_patterns=speech_patterns,
        )

    def _extract_bigrams(self, text: str) -> list[str]:
        """提取常用词二元组"""
        # 只保留中文词
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
        if len(chinese_chars) < 2:
            return []

        bigrams = ["".join(chinese_chars[i : i + 2]) for i in range(len(chinese_chars) - 1)]

        # 统计频率
        counter = Counter(bigrams)
        return [bg for bg, _ in counter.most_common(10)]

    def _extract_speech_patterns(self, dialogues: list[str]) -> list[str]:
        """识别口头禅模式"""
        patterns = []

        # 常见开头模式
        start_patterns = [
            r"^(?:老子|老娘|俺|我)说?",
            r"^(?:你|他|她)们?",
            r"^(?:这个|那个|嗯|啊|哦|呀|嘿)",
            r"^(?:卧槽|他妈|妈的|我靠)",
        ]

        for pattern in start_patterns:
            for dialogue in dialogues:
                match = re.match(pattern, dialogue)
                if match:
                    patterns.append(match.group(0))

        # 统计频率并返回常见的
        counter = Counter(patterns)
        return [p for p, _ in counter.most_common(5)]

    def extract_from_summary(
        self,
        chapter_summaries: str,
        character_names: list[str],
    ) -> list[DialogueFingerprint]:
        """从章节摘要中提取对话指纹（简化版）

        当没有完整正文时使用。
        """
        fingerprints = []

        for name in character_names:
            # 尝试从摘要中提取对话引用
            pattern = rf'{re.escape(name)}[：:]["「『]? (.+?)["」』]?'
            matches = re.findall(pattern, chapter_summaries)

            if matches:
                # 简化处理
                dialogues = [m.strip() for m in matches[:10]]
                fp = DialogueFingerprint(
                    character_name=name,
                    avg_sentence_length=sum(len(d) for d in dialogues) / len(dialogues),
                    common_bigrams=self._extract_bigrams("".join(dialogues)),
                    question_ratio=sum(1 for d in dialogues if "？" in d) / len(dialogues),
                    speech_patterns=[],
                )
                fingerprints.append(fp)

        return fingerprints
