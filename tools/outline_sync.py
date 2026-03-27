import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


def sync_outline_to_hierarchy(src_dir: Path, data_dir: Path) -> None:
    outline_path = src_dir / "outline.md"
    hierarchy_path = data_dir / "hierarchy.yaml"

    with open(outline_path, "r", encoding="utf-8") as f:
        content = f.read()

    data = _parse_outline_md(content)

    with open(hierarchy_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _parse_outline_md(content: str) -> Dict[str, Any]:
    lines = content.split("\n")

    story_info = {"title": ""}
    arcs: List[Dict[str, Any]] = []
    sections: List[Dict[str, Any]] = []
    chapters: List[Dict[str, Any]] = []

    current_arc_idx = -1
    current_sec_idx = -1
    chapter_counter = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            if level == 1:
                story_info["title"] = title
            elif level == 2:
                arcs.append({"id": f"arc_{len(arcs) + 1:03d}", "title": title, "chapters": []})
                current_arc_idx = len(arcs) - 1
                current_sec_idx = -1
            elif level == 3:
                sections.append(
                    {
                        "id": f"sec_{len(sections) + 1:03d}",
                        "title": title,
                        "arc_id": arcs[current_arc_idx]["id"] if current_arc_idx >= 0 else None,
                    }
                )
                current_sec_idx = len(sections) - 1
            elif level == 4:
                chapter_counter += 1
                chapter_id = f"ch_{chapter_counter:03d}"
                chapters.append({"id": chapter_id, "title": title})
                if current_arc_idx >= 0:
                    arcs[current_arc_idx]["chapters"].append(chapter_id)

            i += 1
            continue

        metadata_match = re.match(r"^>\s*(.+?):\s*(.*)$", stripped)
        if metadata_match:
            key = metadata_match.group(1).strip()
            value = metadata_match.group(2).strip()

            if key in ("核心主题", "主题"):
                story_info["theme"] = value
            elif key == "目标字数":
                story_info["word_count_estimate"] = (
                    int(value.replace(",", "")) if value.isdigit() else value
                )
            elif key == "世界前提":
                story_info["world_premise"] = value
            elif key in ("篇弧线", "篇情感"):
                if current_arc_idx >= 0:
                    if "弧线" in key:
                        arcs[current_arc_idx]["arc_structure"] = value
                    elif "情感" in key:
                        arcs[current_arc_idx]["arc_emotional_arc"] = value
            elif key in ("节结构", "节情感", "节张力"):
                if current_sec_idx >= 0:
                    if "结构" in key:
                        sections[current_sec_idx]["section_structure"] = value
                    elif "情感" in key:
                        sections[current_sec_idx]["section_emotional_arc"] = value
                    elif "张力" in key:
                        sections[current_sec_idx]["section_tension"] = value
            elif key in ("预估字数", "戏剧位置", "内容焦点"):
                if chapters:
                    if "字数" in key:
                        chapters[-1]["word_count"] = (
                            int(value.replace(",", "")) if value.isdigit() else value
                        )
                    elif "位置" in key:
                        chapters[-1]["dramatic_position"] = value
                    elif "焦点" in key:
                        chapters[-1]["content_focus"] = value

            i += 1
            continue

        i += 1

    result: Dict[str, Any] = {"story_info": story_info, "arcs": arcs}
    if sections:
        result["sections"] = sections
    if chapters:
        result["chapters"] = chapters

    return result
