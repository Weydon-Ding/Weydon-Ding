import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_bangumi.py"
spec = importlib.util.spec_from_file_location("update_bangumi", SCRIPT_PATH)
update_bangumi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_bangumi)


def test_parse_collection_items_extracts_title_cover_progress_and_url():
    data = [
        {
            "name": "测试动画",
            "subject_id": 123,
            "ep_status": 3,
            "subject": {
                "eps": 12,
                "images": {
                    "common": "https://example.com/common.jpg",
                    "medium": "https://example.com/medium.jpg",
                },
            },
        }
    ]

    items = update_bangumi.parse_collection_items(data)

    assert items == [
        {
            "title": "测试动画",
            "url": "https://bgm.tv/subject/123",
            "cover": "https://example.com/common.jpg",
            "progress": "3 / 12",
        }
    ]


def test_parse_collection_items_uses_volume_progress_for_books():
    data = [
        {
            "subject_id": 456,
            "vol_status": 2,
            "subject": {
                "name_cn": "测试漫画",
                "eps": 0,
                "volumes": 10,
                "images": {"common": "https://example.com/book.jpg"},
            },
        }
    ]

    items = update_bangumi.parse_collection_items(data, subject_type=1)

    assert items[0]["title"] == "测试漫画"
    assert items[0]["progress"] == "2 / 10"


def test_parse_collection_items_omits_progress_for_games():
    data = [
        {
            "subject_id": 789,
            "subject": {
                "name_cn": "测试游戏",
                "images": {"common": "https://example.com/game.jpg"},
            },
        }
    ]

    items = update_bangumi.parse_collection_items(data, subject_type=4)

    assert items[0]["title"] == "测试游戏"
    assert items[0]["progress"] == ""


def test_render_poster_grid_limits_items_and_escapes_titles():
    items = [
        {
            "title": "A | B",
            "url": "https://bgm.tv/subject/1",
            "cover": "https://example.com/a.jpg",
            "progress": "1 / 12",
        },
        {
            "title": "第二部",
            "url": "https://bgm.tv/subject/2",
            "cover": "https://example.com/b.jpg",
            "progress": "2 / ?",
        },
    ]

    markdown = update_bangumi.render_poster_grid(items, limit=1)

    assert markdown.startswith('<p align="left">')
    assert '<a href="https://bgm.tv/subject/1" title="A | B · 1 / 12">' in markdown
    assert '<img src="https://example.com/a.jpg" width="80" alt="A | B" />' in markdown
    assert "第二部" not in markdown


def test_render_poster_grid_does_not_double_escape_entities():
    items = [
        {
            "title": "Panty &amp; Stocking",
            "url": "https://bgm.tv/subject/1",
            "cover": "https://example.com/a.jpg",
            "progress": "1 / 12",
        }
    ]

    markdown = update_bangumi.render_poster_grid(items)

    assert "Panty &amp; Stocking" in markdown
    assert "Panty &amp;amp; Stocking" not in markdown


def test_render_poster_grid_uses_title_only_when_progress_is_empty():
    items = [
        {
            "title": "测试游戏",
            "url": "https://bgm.tv/subject/1",
            "cover": "https://example.com/a.jpg",
            "progress": "",
        }
    ]

    markdown = update_bangumi.render_poster_grid(items)

    assert 'title="测试游戏"' in markdown
    assert "测试游戏 ·" not in markdown


def test_render_poster_grid_uses_custom_empty_message():
    markdown = update_bangumi.render_poster_grid([], empty_message="> 暂时没有在读的条目。")

    assert markdown == "> 暂时没有在读的条目。"


def test_render_poster_grid_includes_all_items_by_default():
    items = [
        {
            "title": f"动画{i}",
            "url": f"https://bgm.tv/subject/{i}",
            "cover": f"https://example.com/{i}.jpg",
            "progress": "0 / 12",
        }
        for i in range(1, 9)
    ]

    markdown = update_bangumi.render_poster_grid(items)

    assert "动画1" in markdown
    assert "动画8" in markdown


def test_replace_bangumi_section_updates_only_marked_block():
    readme = """before
<!-- BANGUMI_ANIME:START -->
old content
<!-- BANGUMI_ANIME:END -->
after
"""

    updated = update_bangumi.replace_bangumi_section(readme, "new content", "BANGUMI_ANIME")

    assert updated == """before
<!-- BANGUMI_ANIME:START -->
new content
<!-- BANGUMI_ANIME:END -->
after
"""
