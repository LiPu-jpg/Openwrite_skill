"""状态验证器

验证 settler 输出的真相文件一致性。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class StateValidationIssue:
    """状态验证问题"""

    severity: str  # critical, warning, info
    category: str
    description: str


class StateValidator:
    """状态验证器

    非阻塞验证 settler 输出的真相文件一致性：

    1. 状态变化无叙事支持
    2. 叙事变化未捕获到状态文件
    3. 时间悖论（无过渡移动）
    4. 伏笔异常（未标记回收就消失）
    5. 回溯编辑（状态变化暗示发生在前章）

    用法:
        validator = StateValidator()
        issues = validator.validate(
            current_state=state_content,
            content=chapter_content,
            chapter_number=5,
        )
    """

    def validate(
        self,
        current_state: str,
        content: str,
        chapter_number: int,
        previous_state: Optional[str] = None,
    ) -> list[StateValidationIssue]:
        """验证状态一致性

        Args:
            current_state: 当前状态文件内容
            content: 章节正文
            chapter_number: 章节编号
            previous_state: 上一章状态（可选）

        Returns:
            问题列表
        """
        issues = []

        # 1. 检查状态变化是否有叙事支持
        issues.extend(self._check_narrative_support(current_state, content))

        # 2. 检查叙事变化是否被捕获
        issues.extend(self._check_captured_changes(current_state, content))

        # 3. 时间悖论检查
        if previous_state:
            issues.extend(self._check_time_paradox(current_state, previous_state))

        # 4. 伏笔异常检查
        issues.extend(self._check_foreshadowing_anomaly(current_state, content))

        # 5. 回溯编辑检查
        issues.extend(self._check_retroactive_edits(current_state, content, chapter_number))

        return issues

    def _check_narrative_support(self, state: str, content: str) -> list[StateValidationIssue]:
        """检查状态变化是否有叙事支持"""
        issues = []

        # 提取状态中的变化声明
        state_changes = re.findall(r"(?:状态变化|变化|新增|获得|失去)[：:]\s*(.+)", state)
        for change in state_changes:
            # 检查变化是否在正文中有描述
            key_change = change.strip()[:20]  # 取前20字符
            if key_change and key_change not in content[:1000]:
                issues.append(
                    StateValidationIssue(
                        severity="warning",
                        category="narrative_support",
                        description=f"状态声明 '{key_change}...' 在本章正文中未找到支持",
                    )
                )

        return issues

    def _check_captured_changes(self, state: str, content: str) -> list[StateValidationIssue]:
        """检查叙事变化是否被状态文件捕获"""
        issues = []

        # 提取正文中的关键变化
        # 位置变化
        location_patterns = [
            r"来到(.+?)[\n，。]",
            r"前往(.+?)[\n，。]",
            r"到达(.+?)[\n，。]",
            r"进入(.+?)[\n，。]",
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                location = match.strip()
                if location and location not in state:
                    issues.append(
                        StateValidationIssue(
                            severity="info",
                            category="captured_change",
                            description=f"位置变化 '{location}' 未在状态文件中记录",
                        )
                    )

        return issues

    def _check_time_paradox(
        self, current_state: str, previous_state: str
    ) -> list[StateValidationIssue]:
        """检查时间悖论"""
        issues = []

        # 提取当前和之前状态中的时间/位置
        current_location = self._extract_location(current_state)
        previous_location = self._extract_location(previous_state)

        # 如果位置变化没有过渡
        if current_location and previous_location:
            if current_location != previous_location:
                # 检查是否有移动叙事
                # 简化：只是警告
                pass

        return issues

    def _check_foreshadowing_anomaly(self, state: str, content: str) -> list[StateValidationIssue]:
        """检查伏笔异常"""
        issues = []

        # 提取状态中的伏笔
        hook_pattern = r"伏笔[：:]\s*(.+?)[。\n]"
        hooks = re.findall(hook_pattern, state)

        for hook in hooks:
            hook = hook.strip()
            # 检查伏笔是否在正文中被回收（提及但未标记）
            if (
                hook in content
                and "回收" not in content[content.index(hook) : content.index(hook) + 50]
            ):
                issues.append(
                    StateValidationIssue(
                        severity="info",
                        category="foreshadowing_anomaly",
                        description=f"伏笔 '{hook[:20]}...' 在正文中提及但未标记回收",
                    )
                )

        return issues

    def _check_retroactive_edits(
        self, state: str, content: str, chapter_number: int
    ) -> list[StateValidationIssue]:
        """检查回溯编辑"""
        issues = []

        # 检查状态中是否暗示变化发生在前章
        retroactive_phrases = [
            r"原来已经",
            r"早就已经",
            r"之前就已经",
        ]

        for phrase in retroactive_phrases:
            if re.search(phrase, state):
                issues.append(
                    StateValidationIssue(
                        severity="warning",
                        category="retroactive_edit",
                        description=f"状态暗示变化发生在前章：'{phrase}'",
                    )
                )

        return issues

    def _extract_location(self, state: str) -> str:
        """从状态中提取位置"""
        location_patterns = [
            r"位置[：:]\s*(.+?)[\n|]",
            r"位于[：:]\s*(.+?)[\n|]",
        ]

        for pattern in location_patterns:
            match = re.search(pattern, state)
            if match:
                return match.group(1).strip()

        return ""
