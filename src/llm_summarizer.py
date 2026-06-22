import os
import json
import time
from openai import OpenAI

SCORE_PROMPT = """你是一个技术博客评估助手。根据以下文章内容，综合评分并生成摘要。

评分标准:
8-10: 核心学习内容 — 原理解释、架构设计、源码分析、工程实践、踩坑经验
5-7: 值得一读 — 产品更新、工具介绍、趋势分析、教程、实践案例
1-4: 价值较低 — 新闻快讯、纯观点、浅尝辄止、营销内容

评估维度:
- 是否与 AI Agent、LLM、RAG、MCP、后端工程化、开源项目相关
- 是否有学习价值（原理/架构/实践/踩坑）
- 是否新颖（新技术/新版本/热点）
- 是否有实践价值（可用于项目/Demo/面试/技术方案）
- 是否可信（官方博客/知名团队/开源作者/论文）

返回 JSON 格式，不要任何其他文字:
{"score": <1-10的整数>, "summary": "<约150字中文摘要，帮助开发者判断是否值得读>", "title_cn": "<中文标题翻译>"}"""

MIN_SCORE = 5
MAX_ARTICLES = 10


def _get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    base_url = os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    model = os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
    return OpenAI(api_key=api_key, base_url=base_url), model


def _call_llm_with_retry(messages, max_tokens, temperature, max_retries=3):
    """Call LLM with retry and backoff on rate limit."""
    client, model = _get_client()
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise e


def translate_title(title: str) -> str:
    """Translate a single title to Chinese. Returns '' on failure."""
    try:
        result = _call_llm_with_retry(
            messages=[
                {"role": "system", "content": "将以下英文标题翻译为中文，只输出翻译，不要任何解释。"},
                {"role": "user", "content": title}
            ],
            max_tokens=80,
            temperature=0
        )
        return result.strip('"\'')
    except Exception:
        return ""


def translate_items(items: list[dict], key: str = "title") -> list[dict]:
    """Batch translate a specific key in a list of dicts. Adds {key}_cn field."""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        for item in items:
            item.setdefault(f"{key}_cn", "")
        return items

    for item in items:
        text = item.get(key, "")
        if text:
            item[f"{key}_cn"] = translate_title(text)
        else:
            item.setdefault(f"{key}_cn", "")
    return items


def score_article(title: str, text: str) -> dict:
    """Score + generate Chinese summary in one LLM call.

    Returns: {score: int, title_cn: str, summary_cn: str}
    On failure, returns score=5 with empty Chinese fields.
    """
    content = f"标题: {title}\n\n正文: {text[:4000]}"
    try:
        result = _call_llm_with_retry(
            messages=[
                {"role": "system", "content": SCORE_PROMPT},
                {"role": "user", "content": content}
            ],
            max_tokens=500,
            temperature=0.3
        )
        # Handle markdown code-block wrapping
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1]
            if result.endswith("```"):
                result = result[:-3]
        data = json.loads(result)
        return {
            "score": int(data.get("score", 5)),
            "title_cn": data.get("title_cn", "").strip('"\''),
            "summary_cn": data.get("summary", "")
        }
    except Exception:
        return {"score": 5, "title_cn": "", "summary_cn": ""}


def summarize_repos(repos: list[dict]) -> list[dict]:
    """Generate Chinese summaries for GitHub repos via LLM."""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        for r in repos:
            r.setdefault("summary_cn", "")
        return repos

    for repo in repos:
        prompt = f"""项目: {repo.get('name', '')}
星数: {repo.get('stars', 0)}
语言: {repo.get('language', 'N/A')}
标签: {', '.join(repo.get('topics', [])[:8])}
简介: {repo.get('description', '')}

请用约80字中文概括这个项目是什么、为什么值得关注。突出其创新点或热门原因。"""
        try:
            repo["summary_cn"] = _call_llm_with_retry(
                messages=[
                    {"role": "system", "content": "你是一个技术编辑，擅长用简洁中文介绍开源项目。只输出摘要，不要任何前缀。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
        except Exception as e:
            print(f"  [WARN] Repo summary failed for {repo.get('name', '?')}: {e}")
            repo["summary_cn"] = ""

    return repos


def summarize_papers(papers: list[dict]) -> list[dict]:
    """Generate Chinese summaries for Arxiv paper abstracts via LLM."""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        for p in papers:
            p.setdefault("summary_cn", "")
        return papers

    for paper in papers:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        if not abstract:
            paper["summary_cn"] = ""
            continue

        prompt = f"""论文标题: {title}
摘要: {abstract[:3000]}

请用约120字中文总结这篇论文：研究什么问题、用什么方法、有什么关键发现。突出对AI Agent/LLM/RAG开发者的参考价值。"""
        try:
            paper["summary_cn"] = _call_llm_with_retry(
                messages=[
                    {"role": "system", "content": "你是一个学术论文解读助手，用简洁中文总结论文核心贡献。只输出摘要。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.3
            )
        except Exception:
            paper["summary_cn"] = ""

    return papers


def process_articles(posts: list[dict]) -> list[dict]:
    """Process blog posts: score, summarize, rank, filter.

    Input: [{source, title, date, summary, url}, ...]
    Output: sorted by score desc, filtered by MIN_SCORE, capped at MAX_ARTICLES.
    """
    if not os.environ.get("DEEPSEEK_API_KEY"):
        for p in posts:
            p.setdefault("title_cn", "")
            p.setdefault("summary_cn", "")
        return posts

    scored = []
    for post in posts:
        title = post.get("title", "")
        url = post.get("url", "")

        from src.content_extractor import extract_content
        extracted = extract_content(url)
        text = extracted["text"] if extracted else post.get("summary", "")

        if not text:
            post["score"] = 0
            post["title_cn"] = ""
            post["summary_cn"] = ""
            scored.append(post)
            continue

        result = score_article(title, text)
        post["score"] = result["score"]
        post["title_cn"] = result["title_cn"]
        post["summary_cn"] = result["summary_cn"]
        scored.append(post)
        status = "✓" if result["score"] >= MIN_SCORE else "✗"
        print(f"  [{status} score={result['score']}] {title[:60]}")

    # Sort by score descending
    scored.sort(key=lambda p: p.get("score", 0), reverse=True)

    # Keep only articles above threshold, cap at MAX_ARTICLES
    kept = [p for p in scored if p.get("score", 0) >= MIN_SCORE][:MAX_ARTICLES]
    dropped = len(scored) - len(kept)
    print(f"  [INFO] Kept {len(kept)}, dropped {dropped} (threshold={MIN_SCORE})")

    return kept
