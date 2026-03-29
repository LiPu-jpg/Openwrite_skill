from tools.frontmatter import has_toml_front_matter, parse_toml_front_matter


def test_parse_toml_front_matter_returns_metadata_and_body():
    text = """+++
id = "char_chen_ming"
type = "character"
tags = ["都市", "异能"]
+++

# 陈明

## background
普通程序员。
"""

    meta, body = parse_toml_front_matter(text)

    assert meta["id"] == "char_chen_ming"
    assert meta["type"] == "character"
    assert meta["tags"] == ["都市", "异能"]
    assert body.lstrip().startswith("# 陈明")


def test_parse_toml_front_matter_returns_empty_meta_when_absent():
    text = "# 陈明\n\n普通程序员。"

    meta, body = parse_toml_front_matter(text)

    assert meta == {}
    assert body == text


def test_parse_toml_front_matter_fails_closed_on_invalid_toml():
    text = """+++
id = "char_chen_ming"
tags = ["都市",
+++

# 陈明
"""

    meta, body = parse_toml_front_matter(text)

    assert meta == {}
    assert "# 陈明" in body


def test_has_toml_front_matter_detects_front_matter_block():
    assert has_toml_front_matter("+++\nid = \"x\"\n+++\n\n# Title\n") is True
    assert has_toml_front_matter("# Title\n") is False
