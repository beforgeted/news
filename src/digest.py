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


def merge(github_items: list[dict], blog_items: list[dict], arxiv_items: list[dict],
          history: set | None = None) -> dict:
    if history is None:
        history = load_history()

    def dedup(items: list[dict]) -> list[dict]:
        seen = set()
        result = []
        for item in items:
            url = item.get("url", "")
            if url and (url in history or url in seen):
                continue
            seen.add(url)
            result.append(item)
        return result

    return {
        "github": dedup(github_items),
        "blogs": dedup(blog_items),
        "papers": dedup(arxiv_items),
        "failed_sources": []
    }


def update_history(sections: dict) -> None:
    all_urls = set()
    for key in ("github", "blogs", "papers"):
        all_urls |= extract_urls(sections.get(key, []))
    history = load_history()
    history |= all_urls
    save_history(history)
