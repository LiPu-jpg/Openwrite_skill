"""后置验证器 - 从 InkOS post-write-validator.ts 融合

零 LLM 成本的确定性规则检测。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationViolation:
    """验证违规"""

    severity: str  # error, warning
    rule: str
    description: str
    location: Optional[str] = None


class PostWriteValidator:
    """后置验证器

    纯规则检测，无需 LLM：

    | 规则 | 严重性 | 检测内容 |
    |------|--------|---------|
    | 禁止句式 | error | "不是...而是..." |
    | 禁止破折号 | error | "——" |
    | 转折词密度 | warning | 超过1次/3000字 |
    | 高疲劳词 | warning | 每词 ≤1次/章 |
    | 元叙事检查 | warning | "到这里算是"、"读者可能..." |
    | 报告术语 | error | "核心动机"、"信息边界"等 |
    | 连续"了"字 | warning | ≥6句连续 |
    | 段落过长 | warning | >300字 |

    用法:
        validator = PostWriteValidator()
        violations = validator.validate(chapter_content)

        for v in violations:
            print(f"[{v.severity}] {v.rule}: {v.description}")
    """

    # 禁止句式（错误）
    FORBIDDEN_PATTERNS = [
        (r"不是.*而是", "禁止句式：'不是...而是...'"),
        (r"——", "禁止句式：破折号'——'"),
        (r"···|。。。", "禁止句式：省略号"),
    ]

    # 元叙事标记（警告）
    METANARRATIVE_PATTERNS = [
        (r"到这里算是", "元叙事标记：'到这里算是'"),
        (r"读者可能", "元叙事标记：'读者可能'"),
        (r"作者想说", "元叙事标记：'作者想说'"),
        (r"不由得让.*", "元叙事标记：'不由得让...'"),
    ]

    # 报告术语（错误）
    REPORT_TERMS = [
        "核心动机",
        "信息边界",
        "叙事支撑",
        "弧线转折",
    ]

    # 高疲劳词（警告）
    HIGH_FATIGUE_WORDS = [
        "突然",
        "瞬间",
        "旋即",
        "旋即",
        "骤然",
    ]

    # 转折词（警告：超过密度阈值）
    TRANSITION_WORDS = [
        "然而",
        "但是",
        "不过",
        "然而",
        "此时",
        "与此同时",
        "另一方面",
    ]

    def __init__(self, transition_density_threshold: float = 1.0 / 3000):
        """初始化验证器

        Args:
            transition_density_threshold: 转折词密度阈值（次/字）
        """
        self.transition_density_threshold = transition_density_threshold

    def validate(self, content: str) -> list[ValidationViolation]:
        """验证章节内容

        Args:
            content: 章节正文

        Returns:
            违规列表
        """
        violations = []

        # 禁止句式检查
        for pattern, message in self.FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                violations.append(
                    ValidationViolation(
                        severity="error",
                        rule="forbidden_pattern",
                        description=message,
                        location=f"出现 {len(matches)} 次",
                    )
                )

        # 元叙事检查
        for pattern, message in self.METANARRATIVE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                violations.append(
                    ValidationViolation(
                        severity="warning",
                        rule="metanarrative",
                        description=message,
                        location=f"出现 {len(matches)} 次",
                    )
                )

        # 报告术语检查
        for term in self.REPORT_TERMS:
            if term in content:
                violations.append(
                    ValidationViolation(
                        severity="error",
                        rule="report_term",
                        description=f"报告术语：'{term}'",
                    )
                )

        # 高疲劳词检查
        content_len = len(content)
        for word in self.HIGH_FATIGUE_WORDS:
            count = content.count(word)
            if count > 1:
                violations.append(
                    ValidationViolation(
                        severity="warning",
                        rule="high_fatigue",
                        description=f"高疲劳词 '{word}' 出现 {count} 次（建议 ≤1次/章）",
                    )
                )

        # 转折词密度检查
        transition_count = sum(content.count(w) for w in self.TRANSITION_WORDS)
        transition_density = transition_count / (content_len / 1000)
        if transition_density > self.transition_density_threshold * 1000:
            violations.append(
                ValidationViolation(
                    severity="warning",
                    rule="transition_density",
                    description=f"转折词密度 {transition_density:.2f}次/千字（阈值 {self.transition_density_threshold * 1000:.2f}）",
                )
            )

        # 连续"了"字检查
        consecutive_le_count = 0
        max_consecutive_le = 0
        in_le_sequence = False
        for char in content:
            if char == "了":
                if in_le_sequence:
                    consecutive_le_count += 1
                else:
                    in_le_sequence = True
                    consecutive_le_count = 1
                max_consecutive_le = max(max_consecutive_le, consecutive_le_count)
            else:
                in_le_sequence = False
                consecutive_le_count = 0

        if max_consecutive_le >= 6:
            violations.append(
                ValidationViolation(
                    severity="warning",
                    rule="consecutive_le",
                    description=f"连续'了'字 {max_consecutive_le} 次（建议 <6次）",
                )
            )

        # 段落过长检查
        paragraphs = content.split("\n\n")
        for i, para in enumerate(paragraphs):
            if len(para) > 300:
                violations.append(
                    ValidationViolation(
                        severity="warning",
                        rule="paragraph_too_long",
                        description=f"段落 {i + 1} 过长（{len(para)}字，建议 <300字）",
                    )
                )

        return violations

    def validate_with_fix(self, content: str) -> tuple[str, list[ValidationViolation]]:
        """验证并尝试修复

        Args:
            content: 章节正文

        Returns:
            (修复后的内容, 违规列表)
        """
        violations = self.validate(content)
        fixed = content

        # 简单修复：移除元叙事标记
        for pattern, message in self.METANARRATIVE_PATTERNS:
            fixed = re.sub(pattern, "", fixed)

        # 修复破折号
        fixed = fixed.replace("——", "")

        return fixed, violations
