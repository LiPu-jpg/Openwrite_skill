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


def test_readme_documents_dante_as_primary_entry():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "`openwrite dante`" in text
    assert "`openwrite goethe`" in text
    assert "openwrite agent 已退役" in text or "已退役" in text
    assert "`openwrite agent` 是主编排入口" not in text
    assert 'openwrite agent "' not in text


def test_skill_docs_no_longer_present_agent_as_primary_entry():
    root_skill = Path("SKILL.md").read_text(encoding="utf-8")
    goethe_skill = Path("skills/goethe-agent/SKILL.md").read_text(encoding="utf-8")

    assert "`openwrite dante` 是主编排入口" in root_skill
    assert "`openwrite agent` 是主编排入口" not in root_skill
    assert "openwrite dante" in goethe_skill
    assert "openwrite agent \"写第一章\"" not in goethe_skill
