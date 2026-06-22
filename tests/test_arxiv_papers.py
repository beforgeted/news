from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from src.collectors.arxiv_papers import fetch_papers


def make_mock_paper(title, published_days_ago=0):
    paper = MagicMock()
    paper.title = title
    paper.summary = "This paper introduces a novel approach to LLM reasoning."
    paper.entry_id = f"https://arxiv.org/abs/2606.{hash(title) % 100000:05d}"
    paper.published = datetime.now(timezone.utc) - timedelta(days=published_days_ago)
    paper.authors = [MagicMock(name="Author A"), MagicMock(name="Author B")]
    paper.authors[0].name = "Author A"
    paper.authors[1].name = "Author B"
    return paper


@patch("src.collectors.arxiv_papers.arxiv.Client")
def test_fetch_papers(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.results.return_value = [
        make_mock_paper("Advances in LLM Agents"),
        make_mock_paper("Transformer Optimization"),
    ]

    config = {
        "keywords": ["llm", "agent"],
        "categories": ["cs.AI", "cs.CL"],
        "max_results": 5
    }
    results = fetch_papers(config)

    assert len(results) == 2
    assert results[0]["title"] == "Advances in LLM Agents"
    assert results[0]["authors"] == ["Author A", "Author B"]
    assert "arxiv.org" in results[0]["url"]
    assert len(results[0]["abstract"]) > 0


@patch("src.collectors.arxiv_papers.arxiv.Client")
def test_fetch_papers_filters_old_entries(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.results.return_value = [
        make_mock_paper("Recent Paper", published_days_ago=0),
        make_mock_paper("Old Paper", published_days_ago=30),
    ]

    config = {"keywords": ["llm"], "categories": ["cs.AI"], "max_results": 5}
    results = fetch_papers(config)

    assert len(results) == 1
    assert results[0]["title"] == "Recent Paper"
