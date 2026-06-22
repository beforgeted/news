import os
import requests
from datetime import datetime, timedelta, timezone


def fetch_trending_repos(config: dict) -> list[dict]:
    topics = " OR ".join(f"topic:{t}" for t in config["topics"])
    lookback = config.get("lookback_days", 7)
    date_since = (datetime.now(timezone.utc) - timedelta(days=lookback)).strftime("%Y-%m-%d")

    query = f"({topics}) created:>={date_since}"
    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": config.get("max_results", 10)
    }

    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("items", []):
        results.append({
            "name": item["full_name"],
            "description": (item.get("description") or "")[:200],
            "stars": item["stargazers_count"],
            "language": item.get("language") or "N/A",
            "url": item["html_url"],
            "topics": item.get("topics", [])
        })

    return results
