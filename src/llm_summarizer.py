import os
from openai import OpenAI

SYSTEM_FILTER = """你是一个 AI 新闻编辑。判断以下网页内容是否值得收录到每日 AI 摘要中。

标准：
- 与 AI、LLM、Agent、机器学习 相关
- 有实质性内容（不是团队介绍、招聘、导航页）
- 是新发布的内容（不是陈旧归档）

只回答 YES 或 NO。"""

SYSTEM_SUMMARIZE = """你是一个专业的技术编辑。根据以下文章内容，用中文撰写一段约 150 字的摘要。

要求：
- 抓住文章核心发现或观点
- 语言简洁专业
- 只输出摘要，不要任何前缀或后缀
- 如果文章包含多个要点，选最重要的 2-3 个"""


def _get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    return OpenAI(api_key=api_key, base_url=base_url), model


def _get_model() -> str:
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def filter_article(title: str, text: str) -> bool:
    """Return True if the article is worth including."""
    content = f"标题: {title}\n\n正文片段: {text[:1000]}"
    try:
        client, model = _get_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_FILTER},
                {"role": "user", "content": content}
            ],
            max_tokens=5,
            temperature=0
        )
        return "YES" in resp.choices[0].message.content.upper()
    except Exception:
        return True  # On failure, include by default


def summarize_article(title: str, text: str) -> dict:
    """Generate Chinese summary. Returns {title_cn, summary_cn}."""
    # Truncate to ~4000 chars for cost control
    content = f"标题: {title}\n\n正文: {text[:4000]}"
    try:
        client, model = _get_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_SUMMARIZE},
                {"role": "user", "content": content}
            ],
            max_tokens=300,
            temperature=0.3
        )
        summary_cn = resp.choices[0].message.content.strip()

        # Also get a Chinese title
        resp2 = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "将以下英文标题翻译为中文，只输出翻译。"},
                {"role": "user", "content": title}
            ],
            max_tokens=50,
            temperature=0
        )
        title_cn = resp2.choices[0].message.content.strip()
        # Remove quotes that LLM sometimes adds
        title_cn = title_cn.strip('"\'')

    except Exception:
        return {"title_cn": "", "summary_cn": ""}

    return {"title_cn": title_cn, "summary_cn": summary_cn}


def process_articles(posts: list[dict]) -> list[dict]:
    """Process a list of blog posts: filter + summarize via LLM.

    Input: [{source, title, date, summary, url}, ...]
    Output: [{source, title, title_cn, date, summary, summary_cn, url}, ...]
    """
    if not os.environ.get("DEEPSEEK_API_KEY"):
        # No API key configured — keep original posts
        for p in posts:
            p.setdefault("title_cn", "")
            p.setdefault("summary_cn", "")
        return posts

    results = []
    for post in posts:
        url = post.get("url", "")
        title = post.get("title", "")

        # Step 1: Extract full content
        from src.content_extractor import extract_content
        extracted = extract_content(url)
        if extracted:
            text = extracted["text"]
        else:
            # Fallback: use existing RSS summary
            text = post.get("summary", "")
            if not text:
                results.append({**post, "title_cn": "", "summary_cn": ""})
                continue

        # Step 2: Filter
        if not filter_article(title, text):
            continue  # Skip low-quality content

        # Step 3: Summarize
        result = summarize_article(title, text)

        post["summary_cn"] = result["summary_cn"]
        post["title_cn"] = result["title_cn"]
        results.append(post)

    return results
