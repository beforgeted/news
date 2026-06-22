import json
from unittest.mock import patch, MagicMock
from src.collectors.github_trending import fetch_trending_repos


def fake_response():
    return {
        "items": [
            {
                "full_name": "owner/repo1",
                "description": "An AI agent framework",
                "stargazers_count": 1500,
                "language": "Python",
                "html_url": "https://github.com/owner/repo1",
                "topics": ["ai", "agent"]
            },
            {
                "full_name": "owner/repo2",
                "description": None,
                "stargazers_count": 800,
                "language": None,
                "html_url": "https://github.com/owner/repo2",
                "topics": []
            }
        ]
    }


@patch("src.collectors.github_trending.requests.get")
def test_fetch_trending_repos(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_response()
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    config = {"topics": ["ai", "llm"], "max_results": 10, "lookback_days": 7}
    results = fetch_trending_repos(config)

    assert len(results) == 2
    assert results[0]["name"] == "owner/repo1"
    assert results[0]["description"] == "An AI agent framework"
    assert results[0]["stars"] == 1500
    assert results[0]["language"] == "Python"
    assert results[0]["url"] == "https://github.com/owner/repo1"
    assert results[0]["topics"] == ["ai", "agent"]

    # None values handled
    assert results[1]["description"] == ""
    assert results[1]["language"] == "N/A"

    # Verify API call
    mock_get.assert_called_once()
    call_args = mock_get.call_args[1]
    assert call_args["params"]["sort"] == "stars"
    assert "topic:ai" in call_args["params"]["q"]
