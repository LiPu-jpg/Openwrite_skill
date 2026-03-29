from pathlib import Path

from tools.frontmatter import has_toml_front_matter
from tools.init_project import init_project
from tools.shared_documents import render_indexed_document


def test_render_indexed_document_uses_frontmatter_index_and_selected_sections():
    text = """+++
id = "lin_yue"
name = "林月"
summary = "高冷强势的技术组长。"
tags = ["职场", "管理者"]
detail_refs = ["背景", "性格"]
+++

# 林月

## 背景
林月是技术组长。

## 性格
- 冷静
- 强势

## 外貌
黑框眼镜。
"""

    rendered = render_indexed_document(text, max_chars=1000)

    assert "标题: 林月" in rendered
    assert "摘要: 高冷强势的技术组长。" in rendered
    assert "标签: 职场、管理者" in rendered
    assert "细节索引: 背景、性格" in rendered
    assert "## 背景" in rendered
    assert "## 性格" in rendered
    assert "## 外貌" not in rendered


def test_render_indexed_document_supports_legacy_markdown_with_defaults():
    text = """# 世界规则

## 力量体系
- 术法依赖逻辑链。

## 社会规则
- 术师身份必须隐藏。
"""

    rendered = render_indexed_document(
        text,
        default_meta={
            "name": "世界规则",
            "summary": "作品的底层规则、限制与未知项。",
            "detail_refs": ["力量体系", "社会规则"],
        },
        max_chars=1000,
    )

    assert "标题: 世界规则" in rendered
    assert "摘要: 作品的底层规则、限制与未知项。" in rendered
    assert "## 力量体系" in rendered
    assert "## 社会规则" in rendered


def test_init_project_world_docs_start_with_toml_front_matter(tmp_path: Path):
    init_project(tmp_path, "demo")
    world_dir = tmp_path / "data" / "novels" / "demo" / "src" / "world"

    assert has_toml_front_matter((world_dir / "rules.md").read_text(encoding="utf-8"))
    assert has_toml_front_matter((world_dir / "terminology.md").read_text(encoding="utf-8"))
    assert has_toml_front_matter((world_dir / "timeline.md").read_text(encoding="utf-8"))
