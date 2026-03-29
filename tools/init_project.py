#!/usr/bin/env python3
"""项目初始化脚本

创建必需的目录结构和初始文件

目录结构:
- src/ - 人类编辑的 source of truth
    - outline.md - 大纲源文件
  - characters/*.md - 角色源文件
  - world/*.md - 世界源文件
- data/ - 机器生成的运行时文件
  - hierarchy.yaml - 从 src/outline.md 生成
  - characters/cards/*.yaml - 从 src/characters/*.md 生成
  - foreshadowing/, workflows/, world/, compressed/, snapshots/
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
    project_root = Path(project_root)
    novel_root = project_root / f"data/novels/{novel_id}"

    src_dirs = [
        novel_root / "src",
        novel_root / "src" / "characters",
        novel_root / "src" / "world",
        novel_root / "src" / "world" / "entities",
    ]

    data_dirs = [
        novel_root / "data" / "characters" / "cards",
        novel_root / "data" / "foreshadowing",
        novel_root / "data" / "workflows",
        novel_root / "data" / "world" / "entities",
        novel_root / "data" / "compressed",
        novel_root / "data" / "snapshots",
        novel_root / "data" / "test_outputs" / "context_packets",
        novel_root / "data" / "test_outputs" / "multi_write",
    ]

    for dir_path in src_dirs + data_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {dir_path.relative_to(project_root)}")

    config_path = project_root / "novel_config.yaml"
    if not config_path.exists():
        config_content = f"""novel_id: {novel_id}
style_id: {novel_id}
current_arc: arc_001
current_chapter: ch_001
"""
        config_path.write_text(config_content, encoding="utf-8")
        print(f"✓ 创建配置: novel_config.yaml")

    outline_src_path = novel_root / "src" / "outline.md"
    if not outline_src_path.exists():
        outline_content = """# 大纲

> 核心主题: 待填写
> 目标字数: 100000

## 第一篇

> 篇情感弧线: 待填写
> 起止章节: ch_001-ch_003

### 开头

> 节结构: 待填写
> 节情感: 待填写

#### 第一章

> 预估字数: 3000
> 戏剧位置: 待填写
> 内容焦点: 待填写

"""
        outline_src_path.write_text(outline_content, encoding="utf-8")
        print(f"✓ 创建大纲源文件: data/novels/{novel_id}/src/outline.md")

    from tools.outline_sync import sync_outline_to_hierarchy

    src_dir = novel_root / "src"
    data_dir = novel_root / "data"
    sync_outline_to_hierarchy(src_dir, data_dir)
    print(f"✓ 生成层级文件: data/novels/{novel_id}/data/hierarchy.yaml")

    rules_path = novel_root / "src" / "world" / "rules.md"
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
        print(f"✓ 创建规则: data/novels/{novel_id}/src/world/rules.md")

    timeline_path = novel_root / "src" / "world" / "timeline.md"
    if not timeline_path.exists():
        timeline_content = """# 关键事件时间线

| 时间 | 事件 | 涉及章节 | 影响 |
|------|------|----------|------|
| （待填充） | | | |
"""
        timeline_path.write_text(timeline_content, encoding="utf-8")
        print(f"✓ 创建时间线: data/novels/{novel_id}/src/world/timeline.md")

    terminology_path = novel_root / "src" / "world" / "terminology.md"
    if not terminology_path.exists():
        terminology_content = """# 术语表

| 术语 | 定义 | 分类 |
|------|------|------|
| （待填充） | | |
"""
        terminology_path.write_text(terminology_content, encoding="utf-8")
        print(f"✓ 创建术语表: data/novels/{novel_id}/src/world/terminology.md")

    dag_path = novel_root / "data" / "foreshadowing" / "dag.yaml"
    if not dag_path.exists():
        dag_content = """# 伏笔DAG
nodes: []
edges: []
"""
        dag_path.write_text(dag_content, encoding="utf-8")
        print(f"✓ 创建伏笔: data/novels/{novel_id}/data/foreshadowing/dag.yaml")

    style_path = novel_root / "data" / "style" / "fingerprint.yaml"
    style_dir = novel_root / "data" / "style"
    style_dir.mkdir(exist_ok=True)
    if not style_path.exists():
        style_content = """# 作品风格指纹
voice: "待定义"
language_style: "待定义"
rhythm: "待定义"
"""
        style_path.write_text(style_content, encoding="utf-8")
        print(f"✓ 创建风格: data/novels/{novel_id}/data/style/fingerprint.yaml")

    manuscript_dir = novel_root / "data" / "manuscript" / "arc_001"
    manuscript_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ 创建手稿目录: data/novels/{novel_id}/data/manuscript/arc_001")

    print(f"\n✅ 项目初始化完成: {novel_id}")
    print(f"\n目录结构:")
    print(f"  src/           - 人类编辑的源文件 (source of truth)")
    print(f"    outline.md   - 大纲源文件")
    print(f"    characters/  - 角色源文件")
    print(f"    world/       - 世界源文件")
    print(f"      entities/  - 世界实体源文件")
    print(f"  data/          - 机器生成的运行时文件")
    print(f"    hierarchy.yaml - 从 src/outline.md 自动生成")
    print(f"    characters/cards/ - 生成的角色卡片")
    print(f"\n下一步:")
    print(f"1. 编辑 data/novels/{novel_id}/src/outline.md 添加大纲")
    print(f"2. 使用 novel-manager 创建角色 (会同步到 src/characters/)")
    print(f"3. 填充 data/novels/{novel_id}/src/world/ 世界观")
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
