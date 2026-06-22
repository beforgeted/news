from src.render import render_html, render_markdown


def test_render_html_contains_all_sections():
    sections = {
        "github": [
            {
                "name": "test/repo",
                "description": "A cool AI project",
                "stars": 1200,
                "language": "Python",
                "url": "https://github.com/test/repo",
                "topics": ["ai", "llm"]
            }
        ],
        "blogs": [
            {
                "source": "OpenAI",
                "title": "GPT-5 Launched",
                "date": "2026-06-20",
                "summary": "OpenAI announces GPT-5.",
                "url": "https://openai.com/gpt5"
            }
        ],
        "papers": [
            {
                "title": "Scaling LLM Agents",
                "authors": ["Alice", "Bob"],
                "abstract": "We explore scaling laws for LLM agents.",
                "url": "https://arxiv.org/abs/2606.12345"
            }
        ],
        "failed_sources": []
    }

    html = render_html(sections, "2026-06-22")

    assert "test/repo" in html
    assert "1200" in html
    assert "OpenAI" in html
    assert "GPT-5 Launched" in html
    assert "Scaling LLM Agents" in html
    assert "2026-06-22" in html
    assert "<html" in html.lower()


def test_render_html_empty_sections():
    sections = {"github": [], "blogs": [], "papers": [], "failed_sources": []}
    html = render_html(sections, "2026-06-22")
    assert "暂无" in html or "No items" in html or len(html) > 0


def test_render_html_with_failed_sources():
    sections = {
        "github": [], "blogs": [], "papers": [],
        "failed_sources": ["github"]
    }
    html = render_html(sections, "2026-06-22")
    assert "github" in html.lower()


def test_render_markdown_full():
    sections = {
        "github": [
            {
                "name": "test/repo",
                "description": "A cool AI project",
                "stars": 1200,
                "language": "Python",
                "url": "https://github.com/test/repo",
                "topics": ["ai", "llm"]
            }
        ],
        "blogs": [
            {
                "source": "OpenAI",
                "title": "GPT-5 Launched",
                "date": "2026-06-20",
                "summary": "OpenAI announces GPT-5.",
                "url": "https://openai.com/gpt5"
            }
        ],
        "papers": [
            {
                "title": "Scaling LLM Agents",
                "authors": ["Alice", "Bob"],
                "abstract": "We explore scaling laws for LLM agents.",
                "url": "https://arxiv.org/abs/2606.12345"
            }
        ],
        "failed_sources": []
    }

    md = render_markdown(sections, "2026-06-22")

    assert "# AI 每日摘要 — 2026-06-22" in md
    assert "test/repo" in md
    assert "⭐1200" in md
    assert "OpenAI" in md
    assert "GPT-5 Launched" in md
    assert "Scaling LLM Agents" in md
    assert "arxiv.org" in md


def test_render_markdown_empty():
    sections = {"github": [], "blogs": [], "papers": [], "failed_sources": []}
    md = render_markdown(sections, "2026-06-22")
    assert "暂无新项目" in md
    assert "暂无新动态" in md
    assert "暂无新论文" in md


def test_render_markdown_with_failed():
    sections = {
        "github": [], "blogs": [], "papers": [],
        "failed_sources": ["github", "arxiv"]
    }
    md = render_markdown(sections, "2026-06-22")
    assert "github, arxiv" in md
    assert "⚠" in md
