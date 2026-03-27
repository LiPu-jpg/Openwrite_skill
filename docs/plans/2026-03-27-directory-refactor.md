# 目录结构重构计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构 novel 目录结构，区分 source-of-truth（人类编辑） 和 generated（机器生成）文件，添加同步机制

**Architecture:** 
- `src/` 目录存放人类编辑的源文件（outline.md, profiles/*.md）
- `data/` 目录存放机器生成的文件（hierarchy.yaml, cards/*.yaml）
- 添加同步工具：`outline_md → hierarchy_yaml`, `profile_md → card_yaml`
- 所有工具只读写 `data/` 目录下的文件

**Tech Stack:** Python, YAML, Pydantic models

---

## Task 1: 定义新目录结构

**Files:**
- Modify: `docs/plans/2026-03-27-directory-refactor.md` (this file)

**Step 1: Document current structure**

```markdown
# Current Structure
data/novels/{novel_id}/
├── outline/
│   ├── outline.md       # 问题：两套大纲文件不同步
│   └── hierarchy.yaml  # 机器实际读取
├── characters/
│   ├── cards/*.yaml    # 结构化
│   └── profiles/*.md   # 问题：两套角色文件不同步
└── ...
```

**Step 2: Define new structure**

```markdown
# New Structure  
data/novels/{novel_id}/
├── src/                    # 人类编辑 source of truth
│   ├── outline.md          # 大纲源文件（人类编辑）
│   ├── characters/         # 角色源文件
│   │   └── *.md          # 角色详情
│   └── world/            # 世界源文件
│       └── *.md          # 世界设定
│
└── data/                  # 机器生成的运行时文件
    ├── hierarchy.yaml     # 从 src/outline.md 生成
    ├── characters/
    │   └── cards/*.yaml  # 从 src/characters/*.md 生成
    ├── foreshadowing/
    │   └── dag.yaml
    ├── workflows/
    ├── world/
    │   ├── entities/*.md
    │   ├── current_state.md
    │   └── ledger.md
    ├── compressed/
    └── snapshots/
```

**Step 3: Save plan**
(Already done)

---

## Task 2: 创建同步工具 - outline_sync.py

**Files:**
- Create: `tools/outline_sync.py`

**Step 1: Write the failing test**

```python
def test_outline_to_hierarchy_sync(tmp_path):
    # Setup src outline
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    outline_md = src_dir / "outline.md"
    outline_md.write_text("""# 测试小说

## 第一篇：觉醒篇

> 起止章节: ch_001 - ch_007

### 第一节：意外觉醒

#### 第一章：加班
""")
    
    # Setup data dir
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    # Sync
    from tools.outline_sync import sync_outline_to_hierarchy
    sync_outline_to_hierarchy(src_dir, data_dir)
    
    # Verify
    hierarchy_path = data_dir / "hierarchy.yaml"
    assert hierarchy_path.exists()
    import yaml
    with open(hierarchy_path) as f:
        data = yaml.safe_load(f)
    assert "story_info" in data
    assert "arcs" in data
    print(f"Generated hierarchy.yaml: {data}")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_outline_sync.py -v`
Expected: FAIL - module not found

**Step 3: Write minimal implementation**

```python
"""大纲同步工具 - src/outline.md → data/hierarchy.yaml"""

from pathlib import Path
from typing import Dict, Any
import yaml

def sync_outline_to_hierarchy(src_dir: Path, data_dir: Path) -> None:
    """将 outline.md 同步到 hierarchy.yaml
    
    Args:
        src_dir: src/ 目录（包含 outline.md）
        data_dir: data/ 目录（输出 hierarchy.yaml）
    """
    outline_md = src_dir / "outline.md"
    if not outline_md.exists():
        return
    
    data_dir.mkdir(parents=True, exist_ok=True)
    hierarchy_yaml = data_dir / "hierarchy.yaml"
    
    # 解析 outline.md
    content = outline_md.read_text(encoding="utf-8")
    
    # 简单解析：提取篇、节、章
    arcs = []
    sections = []
    chapters = []
    
    current_arc = None
    current_section = None
    
    for line in content.split("\n"):
        line = line.strip()
        
        # 检测篇 (## 标题)
        if line.startswith("## ") and not line.startswith("### "):
            if current_arc:
                arcs.append(current_arc)
            current_arc = {
                "id": f"arc_{len(arcs) + 1:03d}",
                "title": line[3:].strip(),
                "description": "",
                "chapters": []
            }
            current_section = None
            
        # 检测节 (### 标题)  
        elif line.startswith("### ") and not line.startswith("#### "):
            if current_section and current_arc:
                current_arc["chapters"].append(f"sec_{len(sections) + 1:03d}")
                sections.append(current_section)
            current_section = {
                "id": f"sec_{len(sections) + 1:03d}",
                "title": line[4:].strip(),
                "arc_id": current_arc["id"] if current_arc else None,
            }
            
        # 检测章 (#### 标题)
        elif line.startswith("#### "):
            chapter_title = line[5:].strip()
            chapter_id = f"ch_{len(chapters) + 1:03d}"
            chapters.append({
                "id": chapter_id,
                "title": chapter_title,
                "summary": ""
            })
            if current_section:
                current_section["chapters"] = current_section.get("chapters", [])
                current_section["chapters"].append(chapter_id)
    
    # 追加最后一个
    if current_section:
        sections.append(current_section)
    if current_arc:
        arcs.append(current_arc)
    
    # 构建 hierarchy.yaml
    hierarchy = {
        "story_info": {
            "title": content.split("\n")[0][2:].strip() if content.startswith("#") else "未命名",
        },
        "arcs": arcs,
        "sections": sections,
        "chapters": chapters
    }
    
    # 写入
    with open(hierarchy_yaml, "w", encoding="utf-8") as f:
        yaml.dump(hierarchy, f, allow_unicode=True, default_flow_style=False)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_outline_sync.py::test_outline_to_hierarchy_sync -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tools/outline_sync.py tests/test_outline_sync.py
git commit -m "feat: add outline sync tool (src/outline.md → data/hierarchy.yaml)"
```

---

## Task 3: 创建角色同步工具

**Files:**
- Create: `tools/character_sync.py`
- Test: `tests/test_character_sync.py`

**Step 1: Write the failing test**

```python
def test_profile_to_card_sync(tmp_path):
    # Setup src/characters
    src_chars = tmp_path / "src" / "characters"
    src_chars.mkdir(parents=True)
    (src_chars / "chen_ming.md").write_text("""# 陈明

## 基本信息
- 职业: 程序员
- 年龄: 28

## 外貌
中等偏瘦，黑眼圈明显

## 性格
996社畜，理工科思维
""")
    
    # Setup data/characters
    data_chars = tmp_path / "data" / "characters"
    data_chars.mkdir(parents=True)
    
    # Sync
    from tools.character_sync import sync_all_profiles_to_cards
    sync_all_profiles_to_cards(tmp_path / "src", tmp_path / "data")
    
    # Verify
    card_file = data_chars / "cards" / "chen_ming.yaml"
    assert card_file.exists()
    import yaml
    with open(card_file) as f:
        card = yaml.safe_load(f)
    assert card["name"] == "陈明"
    assert card["identity"] == "程序员"
```

**Step 2: Run test - Expected FAIL**

**Step 3: Write implementation**

```python
"""角色同步工具 - src/characters/*.md → data/characters/cards/*.yaml"""

from pathlib import Path
from typing import Dict, Any
import yaml
import re

def sync_all_profiles_to_cards(src_dir: Path, data_dir: Path) -> None:
    """同步所有角色档案到角色卡"""
    src_chars = src_dir / "characters"
    if not src_chars.exists():
        return
    
    data_chars = data_dir / "characters"
    cards_dir = data_chars / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    
    for md_file in src_chars.glob("*.md"):
        card = parse_profile_to_card(md_file)
        if card:
            card_id = md_file.stem
            card_path = cards_dir / f"{card_id}.yaml"
            with open(card_path, "w", encoding="utf-8") as f:
                yaml.dump(card, f, allow_unicode=True, default_flow_style=False)

def parse_profile_to_card(md_file: Path) -> Dict[str, Any]:
    """解析角色档案 Markdown 为角色卡 YAML"""
    content = md_file.read_text(encoding="utf-8")
    
    card = {
        "id": md_file.stem,
        "name": md_file.stem.replace("_", " ").title(),
        "tier": "supporting",  # 默认
    }
    
    # 简单解析：提取字段
    lines = content.split("\n")
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("## "):
            current_section = line[3:].lower()
            
        elif line.startswith("- "):
            parts = line[2:].split(":", 1)
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                
                if key == "职业":
                    card["identity"] = value
                elif key == "年龄":
                    card["age"] = int(value) if value.isdigit() else 0
                    
    return card
```

**Step 4: Run test - Expected PASS**

**Step 5: Commit**

---

## Task 4: 修改 init_project.py 生成新结构

**Files:**
- Modify: `tools/init_project.py`

**Step 1: Read current implementation**

```bash
cat tools/init_project.py
```

**Step 2: 修改目录结构生成**

替换:
```python
# 旧结构
outline_dir = project_root / f"data/novels/{novel_id}/outline"
outline_dir.mkdir(parents=True)
```

改为:
```python
# 新结构: src/ + data/
novel_root = project_root / f"data/novels/{novel_id}"
src_dir = novel_root / "src"
data_dir = novel_root / "data"

# src/ - 人类编辑的源文件
src_outline = src_dir / "outline"
src_outline.mkdir(parents=True)

# data/ - 机器生成的文件
data_dir.mkdir(parents=True)

# 复制初始 outline.md 到 src/
# ... 
```

**Step 3: 添加注释说明新结构**

```python
"""
新项目结构:
  src/outline/outline.md      - 大纲源文件（人类编辑）
  src/characters/*.md         - 角色源文件
  data/hierarchy.yaml         - 自动生成（不要手动编辑）
  data/characters/cards/*.yaml - 自动生成
"""
```

**Step 4: 测试**

```bash
cd /Users/jiaoziang/迁移/Openwrite_skill-main
python -c "from tools.init_project import init_project; init_project('/tmp', 'test_sync', '测试')"
ls -la /tmp/data/novels/test_sync/
# 应该看到 src/ 和 data/ 两个目录
```

**Step 5: Commit**

---

## Task 5: 修改 context_builder.py 读取新路径

**Files:**
- Modify: `tools/context_builder.py:175-188`

**Step 1: 修改 _load_outline_hierarchy**

```python
# 旧路径
outline_path = self.data_dir / "outline" / "hierarchy.yaml"

# 新路径
hierarchy_path = self.data_dir / "hierarchy.yaml"
if not hierarchy_path.exists():
    # 尝试从 src/outline.md 同步
    src_outline = self.src_dir / "outline.md"
    if src_outline.exists():
        from tools.outline_sync import sync_outline_to_hierarchy
        sync_outline_to_hierarchy(self.src_dir, self.data_dir)
        
hierarchy_path = self.data_dir / "hierarchy.yaml"
```

**Step 2: 修改 __init__ 添加 src_dir 属性**

```python
def __init__(self, project_root: Path, novel_id: str):
    # ... 现有代码 ...
    
    # 添加 src_dir
    self.src_dir = project_root / "data" / "novels" / novel_id / "src"
```

**Step 3: 运行测试**

```bash
pytest tests/test_visualization.py::TestIntegration23Tools::test_03_get_context -v
```

**Step 4: Commit**

---

## Task 6: 更新 SKILL.md 文档

**Files:**
- Modify: `SKILL.md`

**Step 1: 更新目录布局部分**

```markdown
### 目录布局

```
data/novels/{novel_id}/
├── src/                    # ★ 人类编辑的 source of truth
│   ├── outline.md         # 大纲源文件
│   ├── characters/         # 角色源文件
│   │   └── *.md          # 角色详情
│   └── world/            # 世界源文件
│       └── *.md          # 世界设定
│
└── data/                  # 机器生成的运行时文件
    ├── hierarchy.yaml     # 自动从 src/outline.md 生成
    ├── characters/
    │   └── cards/*.yaml  # 自动从 src/characters/*.md 生成
    ├── foreshadowing/
    │   └── dag.yaml
    ├── workflows/
    ├── world/
    │   ├── entities/*.md
    │   ├── current_state.md  # 运行时状态
    │   └── ledger.md
    ├── compressed/
    └── snapshots/
```

**同步规则：**
- `src/outline.md` → `data/hierarchy.yaml` (工具: `outline_sync.py`)
- `src/characters/*.md` → `data/characters/cards/*.yaml` (工具: `character_sync.py`)
- **不要手动编辑 data/ 目录下的文件**，它们由工具自动生成
```

**Step 2: Commit**

---

## Task 7: 迁移现有 test_novel 到新结构

**Files:**
- Migrate: `data/novels/test_novel/`

**Step 1: 备份**

```bash
cp -r data/novels/test_novel data/novels/test_novel.bak
```

**Step 2: 创建 src/ 并移动文件**

```bash
cd data/novels/test_novel

# 创建 src/ 结构
mkdir -p src/characters src/world

# 移动人类编辑的源文件
mv outline/outline.md src/outline.md
mv characters/profiles/*.md src/characters/
mv world/rules.md src/world/
mv world/terminology.md src/world/
mv world/timeline.md src/world/
mv world/entities/*.md src/world/

# 保留 data/ 结构
mkdir -p data/characters/cards data/world/entities

# 生成 hierarchy.yaml
# (运行同步工具)
```

**Step 3: 验证测试通过**

```bash
pytest tests/test_visualization.py -v
```

**Step 4: Commit**

---

## Task 8: 清理旧的重复文件

**Files:**
- Delete: `outline/hierarchy.yaml` (旧位置)

**验证:** 确认所有工具都从新位置读取

---

## 执行顺序

1. Task 1: 定义新目录结构 (文档)
2. Task 2: 创建 outline_sync.py
3. Task 3: 创建 character_sync.py  
4. Task 4: 修改 init_project.py
5. Task 5: 修改 context_builder.py
6. Task 6: 更新 SKILL.md
7. Task 7: 迁移 test_novel 到新结构
8. Task 8: 清理旧文件

---

## 风险与注意事项

1. **向后兼容** - 现有项目需要迁移脚本
2. **测试覆盖** - 确保所有工具在新路径下正常工作
3. **文档更新** - SKILL.md 和注释需要同步更新
