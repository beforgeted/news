import re
import requests
import feedparser
from datetime import datetime, timezone
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def fetch_blog_posts(config: dict) -> list[dict]:
    blogs = config if isinstance(config, list) else config.get("blogs", [])
    results = []

    for blog in blogs:
        try:
            if blog["type"] == "rss":
                items = _fetch_rss(blog)
            elif blog["type"] == "scrape":
                items = _fetch_scrape(blog)
            else:
                continue
            results.extend(items)
        except Exception as e:
            print(f"[WARN] Failed to fetch {blog['name']}: {e}")
            continue

    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results[:10]


def _fetch_rss(blog: dict) -> list[dict]:
    feed = feedparser.parse(blog["url"])
    return [_parse_entry(blog["name"], e) for e in feed.entries[:5]]


def _parse_entry(source: str, entry) -> dict:
    date_str = None
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            date_str = f"{tp.tm_year}-{tp.tm_mon:02d}-{tp.tm_mday:02d}"
            break
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    raw = entry.get("summary", entry.get("description", "")) or ""
    summary = re.sub(r"<[^>]+>", "", raw)
    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > 200:
        summary = summary[:200] + "..."
    else:
        summary = summary[:200]

    return {
        "source": source,
        "title": entry.get("title", ""),
        "date": date_str,
        "summary": summary,
        "url": entry.get("link", "")
    }


def _fetch_scrape(blog: dict) -> list[dict]:
    resp = requests.get(
        blog["url"], timeout=30,
        headers={"User-Agent": "AI-Daily-Digest/1.0"}
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for link in soup.select(blog["selector"])[:5]:
        url = link.get("href", "")
        if url and not url.startswith("http"):
            url = urljoin(blog["url"], url)
        title = link.get_text(strip=True)
        if title:
            items.append({
                "source": blog["name"],
                "title": title,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "summary": "",
                "url": url
            })
    return items
