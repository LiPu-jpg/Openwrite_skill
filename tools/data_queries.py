"""数据查询工具"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class DataQueries:
    """数据查询工具"""

    def __init__(self, project_root: Path, novel_id: str):
        self.project_root = project_root.resolve()
        self.novel_id = novel_id
        self.data_dir = project_root / "data" / "novels" / novel_id

    def query_outline(
        self, chapter_id: Optional[str] = None, arc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询大纲"""
        outline_path = self.data_dir / "outline" / "hierarchy.yaml"
        if not outline_path.exists():
            return {"success": False, "error": "Outline not found"}

        with outline_path.open("r", encoding="utf-8") as f:
            hierarchy = yaml.safe_load(f) or {}

        if chapter_id:
            # Find specific chapter
            for chapter in hierarchy.get("chapters", []):
                if chapter.get("node_id") == chapter_id:
                    return {"success": True, "result": chapter}
            return {"success": False, "error": f"Chapter not found: {chapter_id}"}

        return {"success": True, "result": hierarchy}

    def query_characters(
        self, character_id: Optional[str] = None, tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询角色"""
        cards_dir = self.data_dir / "characters" / "cards"
        if not cards_dir.exists():
            return {"success": False, "error": "Characters directory not found"}

        characters = []
        for card_file in cards_dir.glob("*.yaml"):
            with card_file.open("r", encoding="utf-8") as f:
                card = yaml.safe_load(f)
                if card:
                    if tier and card.get("tier") != tier:
                        continue
                    if character_id and card.get("character_id") != character_id:
                        continue
                    characters.append(card)

        if character_id and characters:
            return {"success": True, "result": characters[0]}

        return {"success": True, "result": characters}

    def query_world(
        self, entity_id: Optional[str] = None, entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询世界观（委托 world_query.py 解析 Markdown 实体文件）"""
        from tools.world_query import list_entities, get_entity, get_relations_graph

        if entity_id:
            entity = get_entity(self.novel_id, entity_id, self.project_root)
            if entity:
                return {"success": True, "result": entity}
            return {"success": False, "error": f"Entity not found: {entity_id}"}

        if entity_type:
            entities = list_entities(self.novel_id, entity_type, self.project_root)
        else:
            entities = list_entities(self.novel_id, project_root=self.project_root)

        graph = get_relations_graph(self.novel_id, self.project_root)

        return {
            "success": True,
            "result": {"entities": entities, "relations": graph["relations"]},
        }

    def query_foreshadowing(
        self, node_id: Optional[str] = None, status: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询伏笔"""
        dag_path = self.data_dir / "foreshadowing" / "dag.yaml"
        if not dag_path.exists():
            return {"success": False, "error": "Foreshadowing DAG not found"}

        with dag_path.open("r", encoding="utf-8") as f:
            dag = yaml.safe_load(f) or {}

        nodes = dag.get("nodes", [])

        if node_id:
            for node in nodes:
                if node.get("node_id") == node_id:
                    return {"success": True, "result": node}
            return {"success": False, "error": f"Node not found: {node_id}"}

        if status:
            nodes = [n for n in nodes if n.get("status") == status]

        return {"success": True, "result": nodes}

    def query_manuscript(self, chapter_id: Optional[str] = None) -> Dict[str, Any]:
        """查询草稿"""
        manuscript_dir = self.data_dir / "manuscript"
        if not manuscript_dir.exists():
            return {"success": False, "error": "Manuscript directory not found"}

        if chapter_id:
            # Find chapter file
            for md_file in manuscript_dir.rglob("*.md"):
                if chapter_id in md_file.stem:
                    content = md_file.read_text(encoding="utf-8")
                    return {
                        "success": True,
                        "result": {"path": str(md_file), "content": content},
                    }
            return {"success": False, "error": f"Manuscript not found: {chapter_id}"}

        # List all manuscripts
        manuscripts = [
            str(f.relative_to(manuscript_dir)) for f in manuscript_dir.rglob("*.md")
        ]
        return {"success": True, "result": manuscripts}

    def query_style(self) -> Dict[str, Any]:
        """查询风格档案"""
        style_path = self.data_dir / "style" / "fingerprint.yaml"
        if not style_path.exists():
            return {"success": False, "error": "Style fingerprint not found"}

        with style_path.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
        return {"success": True, "result": content}
