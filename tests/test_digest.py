import json
import tempfile
from pathlib import Path
from src.digest import merge, load_history, save_history, extract_urls


def test_merge_deduplicates_by_url():
    github = {
        "trending": [
            {"name": "repo1", "url": "https://github.com/a/b", "stars": 100},
            {"name": "repo2", "url": "https://github.com/a/b", "stars": 50},
        ],
        "active": [
            {"name": "repo3", "url": "https://github.com/c/d", "stars": 200},
        ],
    }
    blogs = [
        {"source": "OpenAI", "title": "Post 1", "url": "https://openai.com/1"},
        {"source": "OpenAI", "title": "Post 2", "url": "https://openai.com/1"},
    ]
    papers = [{"title": "Paper 1", "url": "https://arxiv.org/1"}]

    sections = merge(github, blogs, papers, history=set())

    assert len(sections["github_trending"]) == 1
    assert sections["github_trending"][0]["name"] == "repo1"
    assert len(sections["github_active"]) == 1
    assert len(sections["blogs"]) == 1
    assert len(sections["papers"]) == 1


def test_merge_filters_history():
    history = {"https://openai.com/1"}

    github = {
        "trending": [{"name": "repo1", "url": "https://github.com/a/b"}],
        "active": [{"name": "repo2", "url": "https://github.com/c/d"}],
    }
    blogs = [{"source": "OpenAI", "title": "Post 1", "url": "https://openai.com/1"}]
    papers = [{"title": "Paper 1", "url": "https://arxiv.org/1"}]

    sections = merge(github, blogs, papers, history=history)

    assert len(sections["github_trending"]) == 1
    assert len(sections["github_active"]) == 1
    assert len(sections["blogs"]) == 0
    assert len(sections["papers"]) == 1


def test_merge_handles_empty_inputs():
    sections = merge({"trending": [], "active": []}, [], [], history=set())
    assert sections["github_trending"] == []
    assert sections["github_active"] == []
    assert sections["blogs"] == []
    assert sections["papers"] == []


def test_merge_handles_missing_urls():
    items = [{"name": "no-url-item", "stars": 10}]
    sections = merge(items, [], [], history=set())
    assert len(sections["github_trending"]) == 1


def test_extract_urls():
    items = [
        {"name": "a", "url": "https://a.com"},
        {"name": "b", "url": ""},
        {"name": "c"},
    ]
    urls = extract_urls(items)
    assert urls == {"https://a.com"}


def test_save_and_load_history(tmp_path):
    import src.digest as digest
    digest.STATE_FILE = tmp_path / "sent.json"
    digest.STATE_DIR = tmp_path

    save_history({"https://a.com", "https://b.com"})
    loaded = load_history()
    assert loaded == {"https://a.com", "https://b.com"}


def test_load_history_handles_missing_file(tmp_path):
    import src.digest as digest
    digest.STATE_FILE = tmp_path / "nonexistent.json"
    loaded = load_history()
    assert loaded == set()
