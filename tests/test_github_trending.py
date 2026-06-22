from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from src.collectors.github_trending import fetch_trending_repos


def make_item(full_name, stars, created_days_ago, desc=None, language="Python"):
    created = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
    return {
        "full_name": full_name,
        "description": desc,
        "stargazers_count": stars,
        "language": language,
        "html_url": f"https://github.com/{full_name}",
        "topics": ["ai"],
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ")
    }


@patch("src.collectors.github_trending.requests.get")
def test_fetch_trending_repos(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [
            make_item("owner/new-repo", 5000, 0, "Brand new AI tool"),     # < 24h → is_new
            make_item("owner/old-repo", 30000, 5, "Established AI repo"),  # > 24h
            make_item("owner/medium-repo", 10000, 10, "Older repo"),      # > 24h
        ]
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    config = {"keywords": ["ai agent"], "max_results": 3}
    results = fetch_trending_repos(config)

    assert len(results) == 3
    # New repo should be first
    assert results[0]["name"] == "owner/new-repo"
    assert results[0]["is_new"] is True
    # Old repos follow, sorted by stars
    assert results[1]["name"] == "owner/old-repo"
    assert results[1]["is_new"] is False
    assert results[2]["name"] == "owner/medium-repo"
    assert results[2]["is_new"] is False

    # Verify API query includes date filter
    call_args = mock_get.call_args[1]
    assert "created:>=" in call_args["params"]["q"]
    assert call_args["params"]["sort"] == "stars"


@patch("src.collectors.github_trending.requests.get")
def test_fetch_trending_respects_max_results(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [make_item(f"owner/repo{i}", 1000 - i, i) for i in range(15)]
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    config = {"keywords": ["ai"], "max_results": 5}
    results = fetch_trending_repos(config)

    assert len(results) == 5
