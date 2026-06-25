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


@patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test", "DIGEST_OUTPUT_DIR": "/tmp/test"})
@patch("src.main.send_email")
@patch("src.main.generate_highlight")
@patch("src.main.translate_items")
@patch("src.main.summarize_active_repos")
@patch("src.main.summarize_trending_repos")
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
    mock_html, mock_md, mock_llm, mock_sum_trend, mock_sum_active, mock_tr, mock_hl, mock_email
):
    mock_cfg.return_value = _cfg(email={"smtp_host": "h", "smtp_port": 587, "smtp_user": "u", "smtp_pass": "p"})
    mock_gh.return_value = {
        "trending": [{"name": "t/r", "url": "x1"}],
        "active": [{"name": "a/r", "url": "x2"}],
    }
    mock_bl.return_value = [{"title": "T", "url": "x", "summary": "S"}]
    mock_arx.return_value = [{"title": "P", "url": "x"}]
    mock_hist.return_value = set()
    mock_html.return_value = "<html>"
    mock_md.return_value = "# md"
    mock_llm.return_value = [{"title": "T", "title_cn": "中文", "summary_cn": "摘要"}]
    mock_sum_trend.return_value = [{"name": "t/r", "summary_cn": "涨星摘要"}]
    mock_sum_active.return_value = [{"name": "a/r", "summary_cn": "活跃摘要"}]
    mock_tr.return_value = [{"name": "t/r", "name_cn": "涨星"}]
    mock_hl.return_value = "今日导读..."

    main()

    mock_llm.assert_called_once()
    mock_sum_trend.assert_called_once()
    mock_sum_active.assert_called_once()
    assert mock_tr.call_count == 3  # trending + active + papers
    mock_hl.assert_called_once()
    mock_email.assert_called_once()


@patch.dict(os.environ, {}, clear=True)
@patch("src.main.send_email")
@patch("src.main.generate_highlight")
@patch("src.main.translate_items")
@patch("src.main.summarize_active_repos")
@patch("src.main.summarize_trending_repos")
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
    mock_html, mock_md, mock_llm, mock_sum_trend, mock_sum_active, mock_tr, mock_hl, mock_email
):
    mock_cfg.return_value = _cfg()
    mock_gh.return_value = {"trending": [{"name": "r", "url": "x"}], "active": []}
    mock_bl.return_value = [{"title": "T", "url": "x", "summary": "S"}]
    mock_arx.return_value = [{"title": "P", "url": "x"}]
    mock_hist.return_value = set()
    mock_html.return_value = "<html>"
    mock_md.return_value = "# md"

    main()

    mock_llm.assert_not_called()
    mock_sum_trend.assert_not_called()
    mock_sum_active.assert_not_called()
    mock_tr.assert_not_called()
    mock_hl.assert_called_once()
    mock_email.assert_not_called()
    mock_md.assert_not_called()
