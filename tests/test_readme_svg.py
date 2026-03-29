from pathlib import Path

from markdown_it import MarkdownIt


def test_readme_references_external_logo_svg():
    text = Path("README.md").read_text(encoding="utf-8")
    tokens = MarkdownIt().parse(text)

    code_blocks = [token for token in tokens if token.type == "code_block"]
    assert all("<path" not in token.content for token in code_blocks)
    assert "<svg" not in text
    assert 'src="assets/logo.svg"' in text

    html_blocks = [token for token in tokens if token.type == "html_block"]
    assert any('src="assets/logo.svg"' in token.content for token in html_blocks)
    assert Path("assets/logo.svg").exists()
