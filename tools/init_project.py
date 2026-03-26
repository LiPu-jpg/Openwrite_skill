#!/usr/bin/env python3
"""项目初始化脚本

创建必需的目录结构和初始文件
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def init_project(project_root: Path, novel_id: str, title: Optional[str] = None):
    """初始化小说项目

    Args:
        project_root: 项目根目录
        novel_id: 小说ID
        title: 小说标题（可选）
    """
    # 创建目录结构
    directories = [
        f"data/novels/{novel_id}/outline",
        f"data/novels/{novel_id}/characters/cards",
        f"data/novels/{novel_id}/characters/profiles",
        f"data/novels/{novel_id}/world/entities",
        f"data/novels/{novel_id}/foreshadowing",
        f"data/novels/{novel_id}/style",
        f"data/novels/{novel_id}/manuscript/arc_001",
        f"data/novels/{novel_id}/compressed",
        f"data/novels/{novel_id}/workflows",
        "craft",
    ]

    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {dir_path}")

    # 创建配置文件
    config_path = project_root / "novel_config.yaml"
    if not config_path.exists():
        config_content = f"""novel_id: {novel_id}
style_id: {novel_id}
current_arc: arc_001
current_chapter: ch_001
"""
        config_path.write_text(config_content, encoding="utf-8")
        print(f"✓ 创建配置: novel_config.yaml")

    # 创建初始大纲
    outline_path = project_root / f"data/novels/{novel_id}/outline/hierarchy.yaml"
    if not outline_path.exists():
        outline_content = """hierarchy:
  arc_001:
    title: "第一篇"
    sections:
      section_001:
        title: "开篇"
        chapters:
          ch_001:
            title: "第一章"
            summary: "待填写"
            target_words: 3000
            involved_characters: []
            foreshadowing_refs: []
            status: outlined
"""
        outline_path.write_text(outline_content, encoding="utf-8")
        print(f"✓ 创建大纲: data/novels/{novel_id}/outline/hierarchy.yaml")

    # 世界观文件
    # entities/*.md 按需由 Agent 创建，关系图谱由 world_query.py --relations 自动生成
    world_dir = project_root / f"data/novels/{novel_id}/world"

    rules_path = world_dir / "rules.md"
    if not rules_path.exists():
        rules_content = """# 世界底层规则

## 力量体系
- （待填充）

## 社会规则
- （待填充）

## 物理法则
- （待填充）
"""
        rules_path.write_text(rules_content, encoding="utf-8")
        print(f"✓ 创建规则: data/novels/{novel_id}/world/rules.md")

    timeline_path = world_dir / "timeline.md"
    if not timeline_path.exists():
        timeline_content = """# 关键事件时间线

| 时间 | 事件 | 涉及章节 | 影响 |
|------|------|----------|------|
| （待填充） | | | |
"""
        timeline_path.write_text(timeline_content, encoding="utf-8")
        print(f"✓ 创建时间线: data/novels/{novel_id}/world/timeline.md")

    terminology_path = world_dir / "terminology.md"
    if not terminology_path.exists():
        terminology_content = """# 术语表

| 术语 | 定义 | 分类 |
|------|------|------|
| （待填充） | | |
"""
        terminology_path.write_text(terminology_content, encoding="utf-8")
        print(f"✓ 创建术语表: data/novels/{novel_id}/world/terminology.md")

    print(f"✓ 世界观目录: data/novels/{novel_id}/world/ (rules + timeline + terminology + entities/)")

    # 创建空的伏笔DAG
    dag_path = project_root / f"data/novels/{novel_id}/foreshadowing/dag.yaml"
    if not dag_path.exists():
        dag_content = """# 伏笔DAG
nodes: []
edges: []
"""
        dag_path.write_text(dag_content, encoding="utf-8")
        print(f"✓ 创建伏笔: data/novels/{novel_id}/foreshadowing/dag.yaml")

    # 创建风格指纹
    style_path = project_root / f"data/novels/{novel_id}/style/fingerprint.yaml"
    if not style_path.exists():
        style_content = """# 作品风格指纹
voice: "待定义"
language_style: "待定义"
rhythm: "待定义"
"""
        style_path.write_text(style_content, encoding="utf-8")
        print(f"✓ 创建风格: data/novels/{novel_id}/style/fingerprint.yaml")

    print(f"\n✅ 项目初始化完成: {novel_id}")
    print(f"\n下一步:")
    print(f"1. 编辑 data/novels/{novel_id}/outline/hierarchy.yaml 添加大纲")
    print(f"2. 使用 novel-manager 创建角色")
    print(f"3. 填充 data/novels/{novel_id}/world/ 世界观（rules/timeline/terminology/entities）")
    print(f"4. 使用 novel-creator 开始创作")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python init_project.py <novel_id> [title]")
        print("示例: python init_project.py my_novel '我的小说'")
        sys.exit(1)

    novel_id = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None

    project_root = Path(__file__).parent.parent
    init_project(project_root, novel_id, title)
