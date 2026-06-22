import os
from unittest.mock import patch, MagicMock
from src.main import main


def _cfg(**overrides):
    c = {
        "email": {"smtp_host": "h", "smtp_port": 587},
        "github": {"keywords": ["ai agent"]},
        "blogs": [],
        "arxiv": {"keywords": ["llm"]}
    }
    c.update(overrides)
    return c


@patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"})
@patch("src.main.send_email")
@patch("src.main.generate_highlight")
@patch("src.main.translate_items")
@patch("src.main.summarize_repos")
@patch("src.main.process_articles")
@patch("src.main.render_markdown")
@patch("src.main.render_html")
@patch("src.main.update_history")
@patch("src.main.load_history")
@patch("src.main.fetch_papers")
@patch("src.main.fetch_blog_posts")
@patch("src.main.fetch_trending_repos")
@patch("src.main.load_config")
def test_main_full_llm_pipeline(
    mock_cfg, mock_gh, mock_bl, mock_arx,
    mock_hist, mock_upd,
    mock_html, mock_md, mock_llm, mock_sum, mock_tr, mock_hl, mock_email
):
    mock_cfg.return_value = _cfg(email={"smtp_host": "h", "smtp_port": 587, "smtp_user": "u", "smtp_pass": "p"})
    mock_gh.return_value = [{"name": "r", "url": "x"}]
    mock_bl.return_value = [{"title": "T", "url": "x", "summary": "S"}]
    mock_arx.return_value = [{"title": "P", "url": "x"}]
    mock_hist.return_value = set()
    mock_html.return_value = "<html>"
    mock_md.return_value = "# md"
    mock_llm.return_value = [{"title": "T", "title_cn": "中文", "summary_cn": "摘要"}]
    mock_sum.return_value = [{"name": "r", "summary_cn": "仓库摘要"}]
    mock_tr.return_value = [{"name": "r", "name_cn": "仓库"}]
    mock_hl.return_value = "今日导读..."

    main()

    mock_llm.assert_called_once()
    mock_sum.assert_called_once()
    assert mock_tr.call_count == 2
    mock_hl.assert_called_once()
    mock_email.assert_called_once()


@patch.dict(os.environ, {}, clear=True)
@patch("src.main.send_email")
@patch("src.main.generate_highlight")
@patch("src.main.translate_items")
@patch("src.main.summarize_repos")
@patch("src.main.process_articles")
@patch("src.main.render_markdown")
@patch("src.main.render_html")
@patch("src.main.update_history")
@patch("src.main.load_history")
@patch("src.main.fetch_papers")
@patch("src.main.fetch_blog_posts")
@patch("src.main.fetch_trending_repos")
@patch("src.main.load_config")
def test_main_no_llm_key(
    mock_cfg, mock_gh, mock_bl, mock_arx,
    mock_hist, mock_upd,
    mock_html, mock_md, mock_llm, mock_sum, mock_tr, mock_hl, mock_email
):
    mock_cfg.return_value = _cfg()
    mock_gh.return_value = [{"name": "r", "url": "x"}]
    mock_bl.return_value = [{"title": "T", "url": "x", "summary": "S"}]
    mock_arx.return_value = [{"title": "P", "url": "x"}]
    mock_hist.return_value = set()
    mock_html.return_value = "<html>"
    mock_md.return_value = "# md"

    main()

    mock_llm.assert_not_called()
    mock_sum.assert_not_called()
    mock_tr.assert_not_called()
    mock_hl.assert_called_once()  # Called but returns "" without API key
    mock_email.assert_not_called()
    mock_md.assert_called_once()
