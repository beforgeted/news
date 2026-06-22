from unittest.mock import patch, MagicMock
from src.main import main


@patch("src.main.send_email")
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
    mock_render,
    mock_send_email
):
    mock_load_config.return_value = {
        "email": {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "s@test.com",
            "smtp_pass": "p",
            "recipient": "r@test.com"
        },
        "github": {"topics": ["ai"]},
        "blogs": [],
        "arxiv": {"keywords": ["llm"]}
    }
    mock_github.return_value = [{"name": "repo", "url": "http://a.com"}]
    mock_blogs.return_value = [{"source": "X", "title": "T", "url": "http://b.com"}]
    mock_arxiv.return_value = [{"title": "P", "url": "http://c.com"}]
    mock_load_history.return_value = set()
    mock_render.return_value = "<html>...</html>"

    main()

    mock_github.assert_called_once()
    mock_blogs.assert_called_once()
    mock_arxiv.assert_called_once()
    mock_render.assert_called_once()
    mock_send_email.assert_called_once()
    mock_update_history.assert_called_once()


@patch("src.main.send_email")
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
    mock_render,
    mock_send_email
):
    mock_load_config.return_value = {
        "email": {"smtp_host": "h", "smtp_port": 587, "smtp_user": "u", "smtp_pass": "p", "recipient": "r"},
        "github": {"topics": ["ai"]},
        "blogs": [],
        "arxiv": {"keywords": ["llm"]}
    }
    mock_github.side_effect = Exception("API rate limit")
    mock_blogs.return_value = []
    mock_arxiv.return_value = [{"title": "P", "url": "http://c.com"}]
    mock_load_history.return_value = set()
    mock_render.return_value = "<html>...</html>"

    main()

    # Should still send email despite github failure
    mock_render.assert_called_once()
    call_sections = mock_render.call_args[0][0]
    assert "github" in call_sections["failed_sources"]
    mock_send_email.assert_called_once()
