from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from src.collectors.rss_blogs import fetch_blog_posts


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
    entry = make_feed_entry("GPT-5 Announcement", "https://openai.com/gpt5", "2026-06-20")
    mock_feedparser.parse.return_value = MagicMock(entries=[entry])

    config = {
        "blogs": [
            {"name": "OpenAI", "type": "rss", "url": "https://openai.com/blog/rss.xml"}
        ]
    }
    results = fetch_blog_posts(config)

    assert len(results) == 1
    assert results[0]["source"] == "OpenAI"
    assert results[0]["title"] == "GPT-5 Announcement"
    assert results[0]["url"] == "https://openai.com/gpt5"
    assert results[0]["date"] == "2026-06-20"
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

    config = {"blogs": [{"name": "Test", "type": "rss", "url": "http://example.com"}]}
    results = fetch_blog_posts(config)

    assert len(results) == 1
    assert results[0]["title"] == ""
    assert results[0]["summary"] == ""


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_handles_one_source_failure(mock_feedparser):
    def fail_once(url):
        if "fail" in url:
            raise Exception("Connection error")
        entry = make_feed_entry("OK", "http://ok.com/1", "2026-06-20")
        return MagicMock(entries=[entry])

    mock_feedparser.parse.side_effect = fail_once

    config = {
        "blogs": [
            {"name": "Broken", "type": "rss", "url": "http://fail.com"},
            {"name": "Working", "type": "rss", "url": "http://ok.com"}
        ]
    }
    results = fetch_blog_posts(config)

    # Should still get results from the working source
    assert len(results) == 1
    assert results[0]["source"] == "Working"
