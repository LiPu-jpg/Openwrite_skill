def test_profile_to_card_sync(tmp_path):
    from tools.character_sync import sync_all_profiles_to_cards

    src_chars = tmp_path / "src" / "characters"
    src_chars.mkdir(parents=True)
    (src_chars / "chen_ming.md").write_text("""# 陈明

## 基本信息
- 职业: 程序员
- 年龄: 28

## 外貌
中等偏瘦，黑眼圈明显，格子衫

## 性格
996社畜，理工科思维
""")

    data_chars = tmp_path / "data" / "characters"
    data_chars.mkdir(parents=True)

    sync_all_profiles_to_cards(tmp_path / "src", tmp_path / "data")

    card_file = data_chars / "cards" / "chen_ming.yaml"
    assert card_file.exists()
    import yaml

    with open(card_file) as f:
        card = yaml.safe_load(f)
    assert card["name"] == "陈明"
    assert card["identity"] == "程序员"
    assert card["age"] == 28
    print(f"Generated card: {card}")
