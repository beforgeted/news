from unittest.mock import patch
from src.llm_summarizer import (
    _chinese_ratio,
    _is_mostly_chinese,
    _is_complete_highlight,
    _generate_chinese_summary,
    summarize_active_repos,
)


def test_chinese_ratio():
    assert _chinese_ratio("这是一个中文简介") > 0.5
    assert _chinese_ratio("Fair-code workflow automation platform") == 0.0


def test_is_mostly_chinese():
    assert _is_mostly_chinese("Hermes Agent 是一个 AI 代理框架")
    assert not _is_mostly_chinese("Fair-code workflow automation platform")


def test_is_complete_highlight():
    assert _is_complete_highlight("今日聚焦 LLM 可解释性进展，推荐 Anthropic 新文与 Hermes Agent 项目，值得关注。")
    assert not _is_complete_highlight("今日技术动态聚焦于模型可解释性，重点推荐")
    assert not _is_complete_highlight("太短。")


@patch("src.llm_summarizer._call_llm_with_retry")
def test_generate_chinese_summary_retries_on_english(mock_llm):
    mock_llm.side_effect = [
        "Fair-code workflow automation platform with native AI capabilities.",
        "n8n 是一个公平代码的工作流自动化平台，支持原生 AI 能力与 400 多种集成。",
    ]
    result = _generate_chinese_summary("系统", "用户", max_attempts=3)
    assert _is_mostly_chinese(result)
    assert mock_llm.call_count == 2


@patch("src.llm_summarizer._summarize_repo_cn")
def test_summarize_active_repos_sets_summary_cn(mock_summarize):
    mock_summarize.return_value = "这是一个中文项目简介。"
    repos = [{"name": "test/repo", "description": "English desc"}]
    with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test"}):
        result = summarize_active_repos(repos)
    assert result[0]["summary_cn"] == "这是一个中文项目简介。"
