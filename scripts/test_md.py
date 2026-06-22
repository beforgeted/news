import sys
sys.path.insert(0, "D:/Project/news")
from src.render import render_markdown

sections = {
    "github": [
        {"name": "test/repo", "description": "A cool AI agent framework", "stars": 1200, "language": "Python", "url": "https://github.com/test/repo", "topics": ["ai", "llm", "agent"]}
    ],
    "blogs": [
        {"source": "OpenAI", "title": "GPT-5 Launched", "date": "2026-06-20", "summary": "OpenAI announces GPT-5 with breakthrough reasoning.", "url": "https://openai.com/gpt5"}
    ],
    "papers": [
        {"title": "Scaling LLM Agents", "authors": ["Alice", "Bob"], "abstract": "We explore scaling laws for LLM agents.", "url": "https://arxiv.org/abs/2606.12345"}
    ],
    "failed_sources": []
}

md = render_markdown(sections, "2026-06-22")
print(md)
