import html
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
import json


BANGUMI_USER_ID = os.getenv("BANGUMI_USER_ID", "782607")
README_PATH = Path(os.getenv("README_PATH", "README.md"))
START_MARKER = "<!-- BANGUMI:START -->"
END_MARKER = "<!-- BANGUMI:END -->"
USER_AGENT = "Weydon-Ding GitHub README Bangumi Sync/1.0"


def parse_collection_items(data: list[dict[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []

    for item in data:
        subject = item.get("subject") or {}
        subject_id = item.get("subject_id") or subject.get("id")
        title = item.get("name") or subject.get("name_cn") or subject.get("name") or "Unknown"
        images = subject.get("images") or {}
        cover = images.get("common") or images.get("medium") or images.get("large") or ""
        watched = item.get("ep_status") or 0
        total = subject.get("eps") or "?"

        items.append(
            {
                "title": str(title),
                "url": f"https://bgm.tv/subject/{subject_id}" if subject_id else "https://bgm.tv",
                "cover": str(cover),
                "progress": f"{watched} / {total}",
            }
        )

    return items


def render_poster_grid(items: list[dict[str, str]], limit: int | None = None) -> str:
    if not items:
        return "> 暂时没有正在看的条目。"

    visible_items = items if limit is None else items[:limit]
    posters = ['<p align="left">']

    for item in visible_items:
        if not item.get("cover"):
            continue

        title = html.escape(html.unescape(item["title"]), quote=True)
        url = html.escape(item["url"], quote=True)
        progress = html.escape(item["progress"], quote=True)
        cover_url = html.escape(item["cover"], quote=True)
        tooltip = f"{title} · {progress}"

        posters.append(
            f'  <a href="{url}" title="{tooltip}">'
            f'<img src="{cover_url}" width="80" alt="{title}" /></a>'
        )

    posters.append("</p>")

    return "\n".join(posters)


def replace_bangumi_section(readme: str, content: str) -> str:
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{content}\n{END_MARKER}"

    if not pattern.search(readme):
        raise ValueError("README 中没有找到 Bangumi 同步标记区")

    return pattern.sub(replacement, readme, count=1)


def fetch_watching_collection(user_id: str) -> list[dict[str, Any]]:
    url = f"https://api.bgm.tv/user/{quote(user_id)}/collection?cat=watching"
    request = Request(url, headers={"User-Agent": USER_AGENT})

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    data = fetch_watching_collection(BANGUMI_USER_ID)
    items = parse_collection_items(data)
    markdown = render_poster_grid(items)

    readme = README_PATH.read_text(encoding="utf-8")
    updated = replace_bangumi_section(readme, markdown)
    README_PATH.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
