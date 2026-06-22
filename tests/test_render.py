from src.render import render_html, render_markdown


def _full_sections():
    return {
        "github": [
            {
                "name": "test/repo",
                "name_cn": "测试仓库",
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
                "title_cn": "GPT-5发布",
                "date": "2026-06-20",
                "summary": "OpenAI announces GPT-5.",
                "url": "https://openai.com/gpt5"
            }
        ],
        "papers": [
            {
                "title": "Scaling LLM Agents",
                "title_cn": "扩展LLM代理",
                "authors": ["Alice", "Bob"],
                "abstract": "We explore scaling laws for LLM agents.",
                "url": "https://arxiv.org/abs/2606.12345"
            }
        ],
        "failed_sources": []
    }


def test_render_html_contains_all_sections():
    html = render_html(_full_sections(), "2026-06-22")
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
    sections = {"github": [], "blogs": [], "papers": [], "failed_sources": ["github"]}
    html = render_html(sections, "2026-06-22")
    assert "github" in html.lower()


def test_render_markdown_full():
    md = render_markdown(_full_sections(), "2026-06-22")
    assert "# AI 每日摘要 — 2026-06-22" in md
    assert "测试仓库（test/repo）" in md
    assert "⭐1200" in md
    assert "GPT-5发布（GPT-5 Launched）" in md
    assert "扩展LLM代理（Scaling LLM Agents）" in md
    assert "arxiv.org" in md


def test_render_markdown_empty():
    sections = {"github": [], "blogs": [], "papers": [], "failed_sources": []}
    md = render_markdown(sections, "2026-06-22")
    assert "暂无新项目" in md
    assert "暂无新动态" in md
    assert "暂无新论文" in md


def test_render_markdown_with_failed():
    sections = {"github": [], "blogs": [], "papers": [], "failed_sources": ["github", "arxiv"]}
    md = render_markdown(sections, "2026-06-22")
    assert "github, arxiv" in md
    assert "⚠" in md


def test_render_markdown_new_tag():
    sections = {"github": [{"name": "test/repo", "description": "x", "stars": 100, "language": "Go", "url": "x", "topics": ["ai"], "is_new": True}], "blogs": [], "papers": [], "failed_sources": []}
    md = render_markdown(sections, "2026-06-22")
    assert "🆕" in md


def test_render_markdown_blog_cn_summary():
    sections = {"github": [], "blogs": [{"source": "OpenAI", "title": "GPT-5", "title_cn": "GPT-5发布", "date": "2026-06-20", "summary": "X", "summary_cn": "OpenAI宣布GPT-5发布。", "url": "x"}], "papers": [], "failed_sources": []}
    md = render_markdown(sections, "2026-06-22")
    assert "GPT-5发布（GPT-5）" in md
    assert "OpenAI宣布GPT-5发布" in md


def test_render_markdown_no_cn_title():
    """Without Chinese titles, display original only."""
    sections = {"github": [{"name": "test/repo", "description": "x", "stars": 1, "language": "Go", "url": "x", "topics": []}], "blogs": [{"source": "X", "title": "T", "date": "d", "summary": "S", "url": "x"}], "papers": [{"title": "Paper", "authors": ["A"], "abstract": "abs", "url": "x"}], "failed_sources": []}
    md = render_markdown(sections, "2026-06-22")
    assert "（" not in md  # No CN(EN) brackets without translations
