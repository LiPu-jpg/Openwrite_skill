#!/usr/bin/env python3
"""工具函数模块"""

from __future__ import annotations

from typing import Optional


def parse_chapter_id(user_input: str) -> Optional[str]:
    """解析用户输入的章节ID

    支持的格式:
    - "第一章" -> "ch_001"
    - "第1章" -> "ch_001"
    - "ch_001" -> "ch_001"
    - "1" -> "ch_001"
    - "5" -> "ch_005"

    Args:
        user_input: 用户输入的章节标识

    Returns:
        标准化的章节ID (ch_XXX格式)，解析失败返回None
    """
    import re

    user_input = user_input.strip()

    # 已经是标准格式
    if user_input.startswith("ch_"):
        return user_input

    # 纯数字
    if user_input.isdigit():
        num = int(user_input)
        return f"ch_{num:03d}"

    # 中文数字映射
    chinese_nums = {
        "零": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "百": 100,
        "千": 1000,
    }

    # 匹配 "第X章" 格式
    match = re.match(r"第([零一二三四五六七八九十百千万\d]+)章", user_input)
    if match:
        num_str = match.group(1)

        # 纯数字
        if num_str.isdigit():
            num = int(num_str)
            return f"ch_{num:03d}"

        # 中文数字转换
        num = 0
        temp = 0
        for char in num_str:
            if char in chinese_nums:
                val = chinese_nums[char]
                if val >= 10:
                    if temp == 0:
                        temp = 1
                    num += temp * val
                    temp = 0
                else:
                    temp = val
        num += temp

        if num > 0:
            return f"ch_{num:03d}"

    return None


def generate_id(name: str, id_type: str = "character") -> str:
    """将中文名转换为ID

    Args:
        name: 中文名称
        id_type: ID类型 (character | location | item | organization)

    Returns:
        转换后的ID (拼音格式)
    """
    try:
        from pypinyin import lazy_pinyin

        # 转换为拼音列表
        pinyin_list = lazy_pinyin(name)
        # 用下划线连接
        id_str = "_".join(pinyin_list).lower()
        # 移除特殊字符
        import re

        id_str = re.sub(r"[^a-z0-9_]", "", id_str)

        return id_str
    except ImportError:
        # 如果没有安装pypinyin，使用简单替换
        # 这只是fallback，建议安装pypinyin
        import re

        # 移除空格和特殊字符
        id_str = re.sub(r"[^\u4e00-\u9fa5]", "", name)
        # 使用hash作为fallback
        return f"{id_type}_{hash(name) % 10000:04d}"


def validate_enum(value: str, enum_type: str) -> bool:
    """验证枚举值是否合法

    Args:
        value: 要验证的值
        enum_type: 枚举类型

    Returns:
        是否合法
    """
    enums = {
        "character_tier": ["protagonist", "antagonist", "supporting", "background"],
        "entity_type": ["location", "item", "organization", "event", "concept"],
        "status": ["active", "archived", "deceased", "destroyed", "hidden", "sealed"],
        "relation_type": [
            "friend",
            "enemy",
            "family",
            "lover",
            "master",
            "student",
            "rival",
        ],
    }

    return value in enums.get(enum_type, [])


if __name__ == "__main__":
    # 测试
    print("章节ID解析测试:")
    test_cases = ["第一章", "第1章", "ch_001", "1", "5", "第十章"]
    for case in test_cases:
        print(f"  {case} -> {parse_chapter_id(case)}")

    print("\nID生成测试:")
    names = ["张三", "李逍遥", "琅琊阁"]
    for name in names:
        print(f"  {name} -> {generate_id(name)}")
