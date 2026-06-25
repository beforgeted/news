import os
import re
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

from src.ai_keywords import build_github_active_query, is_ai_related


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_star_count(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def _parse_stars_gained(text: str) -> int:
    match = re.search(r"([\d,]+)\s+stars?\s+this\s+week", text, re.I)
    if not match:
        return 0
    return _parse_star_count(match.group(1))


def _parse_repo_meta(article) -> tuple[int, str]:
    """从 trending 卡片解析总星数与主语言。"""
    stars = 0
    stargazers = article.select_one('a[href*="stargazers"]')
    if stargazers:
        stars = _parse_star_count(stargazers.get_text(strip=True))

    language = "N/A"
    lang_el = article.select_one('[itemprop="programmingLanguage"]')
    if lang_el:
        language = lang_el.get_text(strip=True) or "N/A"

    return stars, language


def _scrape_weekly_trending() -> list[dict]:
    """抓取 GitHub 周榜，按本周涨星数排序。"""
    resp = requests.get(
        "https://github.com/trending?since=weekly",
        headers={"User-Agent": "AI-Daily-Digest/1.0"},
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    repos = []
    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a")
        if not link:
            continue

        full_name = link.get("href", "").strip("/")
        if not full_name or full_name.count("/") != 1:
            continue

        desc_el = article.select_one("p")
        description = desc_el.get_text(strip=True) if desc_el else ""

        stars_gained = 0
        for span in article.find_all("span"):
            text = span.get_text(strip=True)
            if "stars this week" in text.lower():
                stars_gained = _parse_stars_gained(text)
                break

        stars, language = _parse_repo_meta(article)

        repos.append({
            "name": full_name,
            "description": description,
            "stars": stars,
            "stars_gained": stars_gained,
            "language": language,
            "topics": [],
            "url": f"https://github.com/{full_name}",
        })

    repos.sort(key=lambda r: r["stars_gained"], reverse=True)
    return repos


def _search_repos(query: str, per_page: int) -> list[dict]:
    resp = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": query, "sort": "stars", "order": "desc", "per_page": per_page},
        headers=_github_headers(),
        timeout=30,
    )
    if resp.status_code != 200:
        message = resp.json().get("message", resp.text[:200])
        print(f"[WARN] GitHub search failed ({resp.status_code}): {message}")
        return []
    return resp.json().get("items", [])


def _repo_from_search_item(item: dict) -> dict:
    return {
        "name": item["full_name"],
        "description": (item.get("description") or "")[:200],
        "stars": item["stargazers_count"],
        "language": item.get("language") or "N/A",
        "url": item["html_url"],
        "topics": item.get("topics", []),
        "pushed_at": item.get("pushed_at", ""),
    }


def _enrich_repo(repo: dict) -> dict:
    """通过 GitHub API 补全仓库详情。"""
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo['name']}",
            headers=_github_headers(),
            timeout=30,
        )
        if resp.status_code != 200:
            pass
        else:
            data = resp.json()
            repo.update({
                "description": (data.get("description") or repo.get("description") or "")[:200],
                "stars": data.get("stargazers_count") or repo.get("stars") or 0,
                "language": data.get("language") or repo.get("language") or "N/A",
                "topics": data.get("topics", repo.get("topics", [])),
                "pushed_at": data.get("pushed_at", repo.get("pushed_at", "")),
            })
    except Exception as e:
        print(f"[WARN] Failed to enrich {repo.get('name', '?')}: {e}")
    repo.setdefault("topics", [])
    repo.setdefault("language", "N/A")
    if "stars" not in repo:
        repo["stars"] = 0
    return repo


def _fetch_recent_activity(full_name: str) -> str:
    """获取近 30 天的 release 与 commit 摘要，供 LLM 总结最近更新。"""
    parts = []
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        releases_resp = requests.get(
            f"https://api.github.com/repos/{full_name}/releases",
            params={"per_page": 3},
            headers=_github_headers(),
            timeout=30,
        )
        if releases_resp.status_code == 200:
            for release in releases_resp.json()[:2]:
                tag = release.get("tag_name", "")
                name = release.get("name") or tag
                body = (release.get("body") or "").strip().replace("\r\n", "\n")
                body = re.sub(r"\s+", " ", body)[:300]
                if name:
                    parts.append(f"Release {name}: {body}" if body else f"Release {name}")
    except Exception:
        pass

    try:
        commits_resp = requests.get(
            f"https://api.github.com/repos/{full_name}/commits",
            params={"since": since, "per_page": 5},
            headers=_github_headers(),
            timeout=30,
        )
        if commits_resp.status_code == 200:
            for commit in commits_resp.json()[:3]:
                message = commit.get("commit", {}).get("message", "").split("\n")[0].strip()
                if message:
                    parts.append(f"Commit: {message}")
    except Exception:
        pass

    return " | ".join(parts)


def _fetch_weekly_trending(limit: int) -> list[dict]:
    """近一周涨星 Top N（仅限 AI/Agent 相关项目）。"""
    scraped = _scrape_weekly_trending()
    print(f"[INFO] GitHub weekly scrape: {len(scraped)} repos")

    matched = []
    for repo in scraped:
        enriched = _enrich_repo(dict(repo))
        if is_ai_related(
            enriched["name"],
            enriched.get("description", ""),
            enriched.get("topics", []),
        ):
            matched.append(enriched)

    matched.sort(key=lambda r: r.get("stars_gained", 0), reverse=True)
    print(f"[INFO] GitHub weekly trending: {len(matched)} AI repos matched")
    return matched[:limit]


def _fetch_monthly_active(limit: int) -> list[dict]:
    """近 30 天活跃项目中，AI 相关且总星数最高的 Top N。"""
    since_30d = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    query = build_github_active_query(since_30d)

    items = _search_repos(query, per_page=100)
    if not items:
        print(f"[WARN] GitHub active search returned 0 repos (query: {query[:80]}...)")
        return []

    filtered = [
        item for item in items
        if is_ai_related(
            item["full_name"],
            item.get("description") or "",
            item.get("topics", []),
        )
    ]
    filtered.sort(key=lambda x: x["stargazers_count"], reverse=True)
    print(
        f"[INFO] GitHub active: {len(filtered)} AI repos "
        f"from {len(items)} recently pushed repos"
    )

    results = []
    for item in filtered[:limit]:
        repo = _repo_from_search_item(item)
        repo["recent_activity"] = _fetch_recent_activity(repo["name"])
        results.append(repo)
    return results


def fetch_trending_repos(config: dict) -> dict:
    """采集 GitHub 双榜单：近一周涨星 Top N + 近月活跃高星 Top N。"""
    trending_limit = config.get("trending_limit", 5)
    active_limit = config.get("active_limit", 5)

    trending = _fetch_weekly_trending(trending_limit)
    active = _fetch_monthly_active(active_limit)

    return {"trending": trending, "active": active}
