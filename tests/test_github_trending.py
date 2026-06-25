from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from src.collectors.github_trending import (
    fetch_trending_repos,
    _parse_stars_gained,
    _scrape_weekly_trending,
    _enrich_repo,
)


TRENDING_HTML = """
<article class="Box-row">
  <h2><a href="/openai/cool-llm">openai / cool-llm</a></h2>
  <p>An awesome LLM agent framework</p>
  <span itemprop="programmingLanguage">Python</span>
  <a href="/openai/cool-llm/stargazers">8,000</a>
  <span>1,200 stars this week</span>
</article>
<article class="Box-row">
  <h2><a href="/random/game">random / game</a></h2>
  <p>A fun game project</p>
  <span itemprop="programmingLanguage">Go</span>
  <a href="/random/game/stargazers">50,000</a>
  <span>5,000 stars this week</span>
</article>
<article class="Box-row">
  <h2><a href="/foo/rag-kit">foo / rag-kit</a></h2>
  <p>RAG toolkit for agents</p>
  <span itemprop="programmingLanguage">Rust</span>
  <a href="/foo/rag-kit/stargazers">3,200</a>
  <span>800 stars this week</span>
</article>
"""


def make_search_item(full_name, stars, pushed_days_ago=1, desc="LLM agent framework"):
    pushed = datetime.now(timezone.utc) - timedelta(days=pushed_days_ago)
    return {
        "full_name": full_name,
        "description": desc,
        "stargazers_count": stars,
        "language": "Python",
        "html_url": f"https://github.com/{full_name}",
        "topics": ["llm", "agent"],
        "pushed_at": pushed.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def test_parse_stars_gained():
    assert _parse_stars_gained("1,200 stars this week") == 1200
    assert _parse_stars_gained("no stars here") == 0


@patch("src.collectors.github_trending.requests.get")
def test_scrape_weekly_trending(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = TRENDING_HTML
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    repos = _scrape_weekly_trending()
    assert len(repos) == 3
    assert repos[0]["name"] == "random/game"
    assert repos[0]["stars"] == 50000
    assert repos[0]["stars_gained"] == 5000


@patch("src.collectors.github_trending.requests.get")
def test_enrich_repo_preserves_scraped_stars_on_api_failure(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_get.return_value = mock_resp

    repo = {"name": "openai/cool-llm", "stars": 20518, "stars_gained": 12948}
    enriched = _enrich_repo(repo)

    assert enriched["stars"] == 20518


@patch("src.collectors.github_trending._fetch_recent_activity", return_value="Release v1.0")
@patch("src.collectors.github_trending._enrich_repo")
@patch("src.collectors.github_trending._search_repos")
@patch("src.collectors.github_trending._scrape_weekly_trending")
def test_fetch_trending_repos(mock_scrape, mock_search, mock_enrich, mock_activity):
    mock_scrape.return_value = [
        {
            "name": "openai/cool-llm",
            "description": "LLM agent framework",
            "stars": 8000,
            "stars_gained": 1200,
            "language": "Python",
            "topics": [],
            "url": "https://github.com/openai/cool-llm",
        },
        {
            "name": "random/game",
            "description": "fun game",
            "stars": 50000,
            "stars_gained": 5000,
            "language": "Go",
            "topics": [],
            "url": "https://github.com/random/game",
        },
        {
            "name": "foo/rag-kit",
            "description": "RAG toolkit",
            "stars": 3200,
            "stars_gained": 800,
            "language": "Rust",
            "topics": [],
            "url": "https://github.com/foo/rag-kit",
        },
    ]
    mock_enrich.side_effect = lambda repo: {
        **repo,
        "topics": [] if "game" in repo["name"] else ["llm"],
    }
    mock_search.return_value = [
        make_search_item("langchain/langchain", 90000, 2),
        make_search_item("huggingface/transformers", 130000, 5),
    ]

    config = {"trending_limit": 5, "active_limit": 2}
    result = fetch_trending_repos(config)

    assert len(result["trending"]) == 2
    assert result["trending"][0]["name"] == "openai/cool-llm"
    assert len(result["active"]) == 2
    assert result["active"][0]["name"] == "huggingface/transformers"

    query = mock_search.call_args[0][0]
    assert "pushed:>=" in query
    assert mock_search.call_args[1]["per_page"] == 100
