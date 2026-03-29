from pathlib import Path

import yaml

from tools.data_queries import DataQueries


def test_query_outline_uses_runtime_hierarchy_path(tmp_path: Path):
    hierarchy_path = tmp_path / "data" / "novels" / "demo" / "data" / "hierarchy.yaml"
    hierarchy_path.parent.mkdir(parents=True, exist_ok=True)
    hierarchy_path.write_text(
        yaml.safe_dump(
            {
                "story_info": {"title": "测试小说"},
                "chapters": [{"id": "ch_001", "title": "第一章", "summary": "开篇"}],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    queries = DataQueries(tmp_path, "demo")
    result = queries.query_outline(chapter_id="ch_001")

    assert result["success"] is True
    assert result["result"]["title"] == "第一章"


def test_query_manuscript_uses_new_runtime_root(tmp_path: Path):
    chapter_path = tmp_path / "data" / "novels" / "demo" / "data" / "manuscript" / "arc_001" / "ch_001.md"
    chapter_path.parent.mkdir(parents=True, exist_ok=True)
    chapter_path.write_text("# 第一章\n\n正文", encoding="utf-8")

    queries = DataQueries(tmp_path, "demo")
    result = queries.query_manuscript(chapter_id="ch_001")

    assert result["success"] is True
    assert result["result"]["path"].endswith("ch_001.md")
    assert "正文" in result["result"]["content"]


def test_query_characters_matches_canonical_card_id(tmp_path: Path):
    card_path = tmp_path / "data" / "novels" / "demo" / "data" / "characters" / "cards" / "lin_yue.yaml"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text(
        yaml.safe_dump(
            {"id": "lin_yue", "name": "林月", "tier": "重要配角"},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    queries = DataQueries(tmp_path, "demo")
    result = queries.query_characters(character_id="lin_yue")

    assert result["success"] is True
    assert result["result"]["name"] == "林月"
