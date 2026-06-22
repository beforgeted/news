import os
from datetime import datetime, timedelta, timezone
import requests


def fetch_trending_repos(config: dict) -> list[dict]:
    keywords = config.get("keywords", ["ai agent", "llm", "language model", "machine learning"])
    keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)
    max_results = config.get("max_results", 10)

    # Search repos created in last 30 days, sorted by stars
    since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    query = f"{keyword_query} created:>={since_30d}"

    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": max(30, max_results)
    }

    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    results = []
    for item in data.get("items", []):
        created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        is_new = created >= cutoff_24h

        results.append({
            "name": item["full_name"],
            "description": (item.get("description") or "")[:200],
            "stars": item["stargazers_count"],
            "language": item.get("language") or "N/A",
            "url": item["html_url"],
            "topics": item.get("topics", []),
            "is_new": is_new
        })

    # Sort: new repos first, then by stars
    results.sort(key=lambda r: (not r["is_new"], -r["stars"]))

    return results[:max_results]
