def test_outline_to_hierarchy_sync(tmp_path):
    from tools.outline_sync import sync_outline_to_hierarchy

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    outline_md = src_dir / "outline.md"
    outline_md.write_text("""# 测试小说

## 第一篇：觉醒篇

> 起止章节: ch_001 - ch_007

### 第一节：意外觉醒

#### 第一章：加班
""")

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    sync_outline_to_hierarchy(src_dir, data_dir)

    hierarchy_path = data_dir / "hierarchy.yaml"
    assert hierarchy_path.exists()
    import yaml

    with open(hierarchy_path) as f:
        data = yaml.safe_load(f)
    assert "story_info" in data
    assert "arcs" in data
    print(f"Generated hierarchy.yaml: {data}")
