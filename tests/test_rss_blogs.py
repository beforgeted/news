from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from src.collectors.rss_blogs import fetch_blog_posts, _is_within_lookback


def make_feed_entry(title, link, published_str):
    import time

    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = "Some content with <b>bold</b> text"
    entry.published_parsed = time.strptime(published_str, "%Y-%m-%d")
    entry.updated_parsed = None
    # Make .get() work like dict access for feedparser entry compatibility
    entry.get.side_effect = lambda key, default="": getattr(entry, key, default)
    return entry


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_rss_blogs(mock_feedparser):
    recent_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = make_feed_entry("GPT-5 Announcement", "https://openai.com/gpt5", recent_date)
    mock_feedparser.parse.return_value = MagicMock(entries=[entry])

    config = {
        "lookback_days": 3,
        "sources": [
            {"name": "OpenAI", "type": "rss", "url": "https://openai.com/blog/rss.xml"}
        ],
    }
    results = fetch_blog_posts(config)

    assert len(results) == 1
    assert results[0]["source"] == "OpenAI"
    assert results[0]["title"] == "GPT-5 Announcement"
    assert results[0]["url"] == "https://openai.com/gpt5"
    assert results[0]["date"] == recent_date
    assert "<b>" not in results[0]["summary"]  # HTML stripped


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_rss_handles_missing_fields(mock_feedparser):
    entry = MagicMock()
    entry.title = ""
    entry.link = ""
    entry.summary = None
    entry.description = None
    entry.published_parsed = None
    entry.updated_parsed = None
    entry.get.side_effect = lambda key, default="": getattr(entry, key, default)

    mock_feedparser.parse.return_value = MagicMock(entries=[entry])

    config = {"lookback_days": 3, "sources": [{"name": "Test", "type": "rss", "url": "http://example.com"}]}
    results = fetch_blog_posts(config)

    assert len(results) == 1
    assert results[0]["title"] == ""
    assert results[0]["summary"] == ""


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_handles_one_source_failure(mock_feedparser):
    def fail_once(url):
        if "fail" in url:
            raise Exception("Connection error")
        entry = make_feed_entry("OK", "http://ok.com/1", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        return MagicMock(entries=[entry])

    mock_feedparser.parse.side_effect = fail_once

    config = {
        "lookback_days": 3,
        "sources": [
            {"name": "Broken", "type": "rss", "url": "http://fail.com"},
            {"name": "Working", "type": "rss", "url": "http://ok.com"},
        ],
    }
    results = fetch_blog_posts(config)

    # Should still get results from the working source
    assert len(results) == 1
    assert results[0]["source"] == "Working"


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_rss_filters_posts_older_than_lookback(mock_feedparser):
    today = datetime.now(timezone.utc)
    recent = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    old = (today - timedelta(days=10)).strftime("%Y-%m-%d")

    entries = [
        make_feed_entry("Recent Post", "https://openai.com/recent", recent),
        make_feed_entry("Old Post", "https://openai.com/old", old),
    ]
    mock_feedparser.parse.return_value = MagicMock(entries=entries)

    config = {
        "lookback_days": 3,
        "sources": [{"name": "OpenAI", "type": "rss", "url": "https://openai.com/blog/rss.xml"}],
    }
    results = fetch_blog_posts(config)

    assert len(results) == 1
    assert results[0]["title"] == "Recent Post"


def test_is_within_lookback():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    old = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    assert _is_within_lookback(today, 3) is True
    assert _is_within_lookback(old, 3) is False
