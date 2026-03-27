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

> 戏剧位置: 起
> 内容焦点: 程序员陈明在深夜加班赶项目

#### 第二章：第二天

> 戏剧位置: 承
> 内容焦点: 陈明精神状态异常好

### 第二节：隐藏身份

#### 第三章：新的一天

> 戏剧位置: 起
> 内容焦点: 陈明开始适应新的生活
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
    assert "sections" in data
    assert "chapters" in data

    assert data["arcs"][0]["description"] == "ch_001 - ch_007"
    assert "chapters" in data["sections"][0]
    assert data["sections"][0]["chapters"] == ["ch_001", "ch_002"]
    assert data["sections"][1]["chapters"] == ["ch_003"]
    assert data["chapters"][0]["summary"] == "程序员陈明在深夜加班赶项目"
    assert data["chapters"][1]["summary"] == "陈明精神状态异常好"
    assert data["chapters"][2]["summary"] == "陈明开始适应新的生活"
    print(f"Generated hierarchy.yaml: {data}")
