import os
import requests


def fetch_trending_repos(config: dict) -> list[dict]:
    keywords = config.get("keywords", ["ai agent", "llm", "language model", "machine learning"])
    keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)
    query = keyword_query

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
