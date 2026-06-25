import json
from pathlib import Path

STATE_DIR = Path(__file__).parent.parent / "state"
STATE_FILE = STATE_DIR / "sent.json"


def load_history() -> set:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return set(data.get("urls", []))
    except Exception:
        pass
    return set()


def save_history(urls: set) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": list(urls)}, f, ensure_ascii=False, indent=2)


def extract_urls(items: list[dict]) -> set:
    return {item["url"] for item in items if item.get("url")}


def merge(github_data: dict | list, blog_items: list[dict], arxiv_items: list[dict],
          history: set | None = None) -> dict:
    if history is None:
        history = load_history()

    def dedup(items: list[dict], check_history: bool = True) -> list[dict]:
        seen = set()
        result = []
        for item in items:
            url = item.get("url", "")
            if url and url in seen:
                continue
            if check_history and url and url in history:
                continue
            if url:
                seen.add(url)
            result.append(item)
        return result

    if isinstance(github_data, dict):
        github_trending = dedup(github_data.get("trending", []), check_history=False)
        trending_urls = {r.get("url") for r in github_trending if r.get("url")}
        github_active = [
            r for r in dedup(github_data.get("active", []), check_history=False)
            if r.get("url") not in trending_urls
        ]
    else:
        github_trending = dedup(github_data if isinstance(github_data, list) else [], check_history=False)
        github_active = []

    return {
        "github_trending": github_trending,
        "github_active": github_active,
        "blogs": dedup(blog_items),
        "papers": dedup(arxiv_items),
        "failed_sources": []
    }


def update_history(sections: dict) -> None:
    all_urls = set()
    for key in ("blogs", "papers"):
        all_urls |= extract_urls(sections.get(key, []))
    history = load_history()
    history |= all_urls
    save_history(history)
