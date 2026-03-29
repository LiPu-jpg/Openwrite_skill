from pathlib import Path

from markdown_it import MarkdownIt


def test_readme_top_svg_stays_as_single_html_block():
    text = Path("README.md").read_text(encoding="utf-8")
    tokens = MarkdownIt().parse(text)

    code_blocks = [token for token in tokens if token.type == "code_block"]
    assert all("<path" not in token.content for token in code_blocks)

    svg_blocks = [token for token in tokens if token.type == "html_block" and "<svg" in token.content]
    assert len(svg_blocks) == 1
