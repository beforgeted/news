from src.ai_keywords import is_ai_related, build_github_active_query, AI_MATCH_TERMS, EXCLUDE_REPO_PATTERNS


def test_is_ai_related_positive():
    assert is_ai_related("openai/cool-llm", "LLM agent framework", ["llm"])
    assert is_ai_related("foo/bar", "RAG pipeline for agents", [])


def test_is_ai_related_negative():
    assert not is_ai_related("sindresorhus/awesome", "Awesome lists", [])
    assert not is_ai_related("random/game", "A fun game", [])


def test_build_github_active_query():
    q = build_github_active_query("2026-05-26")
    assert "llm OR agent OR rag" in q
    assert "pushed:>=2026-05-26" in q
    assert q.count(" OR ") <= 4
