import html
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


BANGUMI_USER_ID = os.getenv("BANGUMI_USER_ID", "782607")
README_PATH = Path(os.getenv("README_PATH", "README.md"))
USER_AGENT = "Weydon-Ding GitHub README Bangumi Sync/1.0"
COLLECTION_TYPE_DOING = 3
COLLECTION_LIMIT = 50

COLLECTION_SECTIONS = [
    {
        "marker": "BANGUMI_ANIME",
        "subject_type": 2,
        "empty_message": "> 暂时没有在看的动画。",
    },
    {
        "marker": "BANGUMI_GAMES",
        "subject_type": 4,
        "empty_message": "> 暂时没有在玩的游戏。",
    },
    {
        "marker": "BANGUMI_BOOKS",
        "subject_type": 1,
        "empty_message": "> 暂时没有在读的书籍。",
    },
]


def build_progress(item: dict[str, Any], subject: dict[str, Any], subject_type: int) -> str:
    if subject_type == 4:
        return ""

    episode_status = item.get("ep_status") or 0
    episode_total = subject.get("eps") or 0
    volume_status = item.get("vol_status") or 0
    volume_total = subject.get("volumes") or 0

    if episode_total or episode_status:
        return f"{episode_status} / {episode_total or '?'}"
    if volume_total or volume_status:
        return f"{volume_status} / {volume_total or '?'}"

    return ""


def parse_collection_items(
    data: list[dict[str, Any]], subject_type: int = 2
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    for item in data:
        subject = item.get("subject") or {}
        subject_id = item.get("subject_id") or subject.get("id")
        title = item.get("name") or subject.get("name_cn") or subject.get("name") or "Unknown"
        images = subject.get("images") or {}
        cover = images.get("common") or images.get("medium") or images.get("large") or ""
        progress = build_progress(item, subject, subject_type)

        items.append(
            {
                "title": str(title),
                "url": f"https://bgm.tv/subject/{subject_id}" if subject_id else "https://bgm.tv",
                "cover": str(cover),
                "progress": progress,
            }
        )

    return items


def render_poster_grid(
    items: list[dict[str, str]],
    limit: int | None = None,
    empty_message: str = "> 暂时没有条目。",
) -> str:
    if not items:
        return empty_message

    visible_items = items if limit is None else items[:limit]
    posters = ['<p align="left">']

    for item in visible_items:
        if not item.get("cover"):
            continue

        title = html.escape(html.unescape(item["title"]), quote=True)
        url = html.escape(item["url"], quote=True)
        progress = html.escape(item["progress"], quote=True)
        cover_url = html.escape(item["cover"], quote=True)
        tooltip = f"{title} · {progress}" if progress else title

        posters.append(
            f'  <a href="{url}" title="{tooltip}">'
            f'<img src="{cover_url}" width="80" alt="{title}" /></a>'
        )

    posters.append("</p>")

    return "\n".join(posters)


def marker_pair(marker: str) -> tuple[str, str]:
    return f"<!-- {marker}:START -->", f"<!-- {marker}:END -->"


def replace_bangumi_section(readme: str, content: str, marker: str = "BANGUMI") -> str:
    start_marker, end_marker = marker_pair(marker)
    pattern = re.compile(
        rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}",
        re.DOTALL,
    )
    replacement = f"{start_marker}\n{content}\n{end_marker}"

    if not pattern.search(readme):
        raise ValueError(f"README 中没有找到 {marker} 同步标记区")

    return pattern.sub(replacement, readme, count=1)


def fetch_collection(user_id: str, subject_type: int) -> list[dict[str, Any]]:
    query = urlencode(
        {
            "subject_type": subject_type,
            "type": COLLECTION_TYPE_DOING,
            "limit": COLLECTION_LIMIT,
        }
    )
    url = f"https://api.bgm.tv/v0/users/{quote(user_id)}/collections?{query}"
    request = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    if isinstance(data, dict):
        return data.get("data") or []
    if isinstance(data, list):
        return data

    return []


def main() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    updated = readme

    for section in COLLECTION_SECTIONS:
        subject_type = int(section["subject_type"])
        data = fetch_collection(BANGUMI_USER_ID, subject_type)
        items = parse_collection_items(data, subject_type)
        markdown = render_poster_grid(items, empty_message=str(section["empty_message"]))
        updated = replace_bangumi_section(updated, markdown, str(section["marker"]))

    README_PATH.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
