from unittest.mock import patch, MagicMock
from src.main import main


def _base_mocks():
    return {
        "email": {"smtp_host": "h", "smtp_port": 587},
        "github": {"keywords": ["ai agent"]},
        "blogs": [],
        "arxiv": {"keywords": ["llm"]}
    }


@patch("src.main.send_email")
@patch("src.main.translate_summaries")
@patch("src.main.render_markdown")
@patch("src.main.render_html")
@patch("src.main.update_history")
@patch("src.main.load_history")
@patch("src.main.fetch_papers")
@patch("src.main.fetch_blog_posts")
@patch("src.main.fetch_trending_repos")
@patch("src.main.load_config")
def test_main_success_path(
    mock_load_config,
    mock_github,
    mock_blogs,
    mock_arxiv,
    mock_load_history,
    mock_update_history,
    mock_render_html,
    mock_render_md,
    mock_translate,
    mock_send_email
):
    cfg = _base_mocks()
    cfg["email"].update({"smtp_user": "s@test.com", "smtp_pass": "p"})
    mock_load_config.return_value = cfg
    mock_github.return_value = [{"name": "repo", "url": "http://a.com"}]
    mock_blogs.return_value = [{"source": "X", "title": "T", "url": "http://b.com", "summary": "S"}]
    mock_arxiv.return_value = [{"title": "P", "url": "http://c.com"}]
    mock_load_history.return_value = set()
    mock_render_html.return_value = "<html>...</html>"
    mock_render_md.return_value = "# Markdown..."
    mock_translate.return_value = mock_blogs.return_value

    main()

    mock_github.assert_called_once()
    mock_blogs.assert_called_once()
    mock_arxiv.assert_called_once()
    mock_translate.assert_called_once()
    mock_render_html.assert_called_once()
    mock_render_md.assert_called_once()
    mock_send_email.assert_called_once()
    mock_update_history.assert_called_once()


@patch("src.main.send_email")
@patch("src.main.translate_summaries")
@patch("src.main.render_markdown")
@patch("src.main.render_html")
@patch("src.main.update_history")
@patch("src.main.load_history")
@patch("src.main.fetch_papers")
@patch("src.main.fetch_blog_posts")
@patch("src.main.fetch_trending_repos")
@patch("src.main.load_config")
def test_main_one_collector_fails(
    mock_load_config,
    mock_github,
    mock_blogs,
    mock_arxiv,
    mock_load_history,
    mock_update_history,
    mock_render_html,
    mock_render_md,
    mock_translate,
    mock_send_email
):
    cfg = _base_mocks()
    cfg["email"].update({"smtp_user": "u", "smtp_pass": "p"})
    mock_load_config.return_value = cfg
    mock_github.side_effect = Exception("API rate limit")
    mock_blogs.return_value = []
    mock_arxiv.return_value = [{"title": "P", "url": "http://c.com"}]
    mock_load_history.return_value = set()
    mock_render_html.return_value = "<html>...</html>"
    mock_render_md.return_value = "# Markdown..."
    mock_translate.return_value = []

    main()

    call_sections = mock_render_html.call_args[0][0]
    assert "github" in call_sections["failed_sources"]
    mock_send_email.assert_called_once()
    mock_render_md.assert_called_once()


@patch("src.main.send_email")
@patch("src.main.translate_summaries")
@patch("src.main.render_markdown")
@patch("src.main.render_html")
@patch("src.main.update_history")
@patch("src.main.load_history")
@patch("src.main.fetch_papers")
@patch("src.main.fetch_blog_posts")
@patch("src.main.fetch_trending_repos")
@patch("src.main.load_config")
def test_main_skips_email_when_not_configured(
    mock_load_config,
    mock_github,
    mock_blogs,
    mock_arxiv,
    mock_load_history,
    mock_update_history,
    mock_render_html,
    mock_render_md,
    mock_translate,
    mock_send_email
):
    mock_load_config.return_value = _base_mocks()
    mock_github.return_value = [{"name": "repo", "url": "http://a.com"}]
    mock_blogs.return_value = []
    mock_arxiv.return_value = []
    mock_load_history.return_value = set()
    mock_render_html.return_value = "<html>...</html>"
    mock_render_md.return_value = "# Markdown..."
    mock_translate.return_value = []

    main()

    mock_render_html.assert_called_once()
    mock_render_md.assert_called_once()
    mock_send_email.assert_not_called()
    mock_update_history.assert_called_once()
