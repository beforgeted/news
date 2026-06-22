import os
import time
from openai import OpenAI

SYSTEM_FILTER = """你是一个技术博客筛选助手，目标是帮助一名正在学习 AI Agent、LLM 应用开发、后端工程化、MCP、RAG、CI/CD 和开源项目实践的开发者，从大量博客中筛选值得阅读的内容。

请根据以下标准评估文章是否值得保留：

1. 技术相关性：是否与 AI、Agent、LLM、RAG、MCP、后端、工程化、开源项目、系统架构相关。
2. 学习价值：是否包含原理解释、架构设计、源码分析、工程实践、踩坑经验或性能优化。
3. 新颖度：是否涉及新技术、新版本、新工具、新框架或近期热点。
4. 实践价值：是否能用于实际项目、Demo、面试准备或技术方案设计。
5. 可信度：是否来自官方博客、知名团队、开源项目作者、论文作者或有实践经验的工程师。

请注意：
- 不要因为标题热门就保留。
- 不要保留纯营销、纯观点、缺少技术细节的文章。
- 如果文章只是重复新闻，没有额外分析，也应降低分数。
- 如果文章能帮助理解技术趋势、改进项目架构、学习工程实践，应提高分数。

只回答 YES 或 NO。"""

SYSTEM_SUMMARIZE = """你是一个技术学习助手。根据以下文章内容，用中文撰写一段约 150 字的摘要，帮助一名学习 AI Agent、LLM、后端工程化、MCP、RAG 的开发者快速判断是否值得阅读。

要求：
- 提炼文章核心技术内容：讲了什么、用了什么技术栈、解决了什么问题
- 指出对开发者的实践价值：能学到什么、能否用于项目
- 语言简洁专业，只输出摘要本身
- 如果文章包含多个要点，选最重要的 2-3 个"""


def _get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    base_url = os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    model = os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
    return OpenAI(api_key=api_key, base_url=base_url), model


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


def filter_article(title: str, text: str) -> bool:
    """Return True if the article is worth including."""
    content = f"标题: {title}\n\n正文片段: {text[:2000]}"
    try:
        result = _call_llm_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_FILTER},
                {"role": "user", "content": content}
            ],
            max_tokens=5,
            temperature=0
        )
        return "YES" in result.upper()
    except Exception:
        return True  # On failure, include by default


def summarize_article(title: str, text: str) -> dict:
    """Generate Chinese summary. Returns {title_cn, summary_cn}."""
    # Truncate to ~4000 chars for cost control
    content = f"标题: {title}\n\n正文: {text[:4000]}"
    try:
        summary_cn = _call_llm_with_retry(
            messages=[
                {"role": "system", "content": SYSTEM_SUMMARIZE},
                {"role": "user", "content": content}
            ],
            max_tokens=300,
            temperature=0.3
        )

        # Also get a Chinese title
        title_cn = _call_llm_with_retry(
            messages=[
                {"role": "system", "content": "将以下英文标题翻译为中文，只输出翻译。"},
                {"role": "user", "content": title}
            ],
            max_tokens=50,
            temperature=0
        )
        title_cn = title_cn.strip('"\'')

    except Exception:
        return {"title_cn": "", "summary_cn": ""}

    return {"title_cn": title_cn, "summary_cn": summary_cn}


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
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
            else:
                raise e


def summarize_repos(repos: list[dict]) -> list[dict]:
    """Generate Chinese summaries for GitHub repos via LLM.

    Input: [{name, description, stars, language, topics, url}, ...]
    Output: same items with added summary_cn field.
    """
    if not os.environ.get("DEEPSEEK_API_KEY"):
        for r in repos:
            r.setdefault("summary_cn", "")
        return repos

    for repo in repos:
        name = repo.get("name", "")
        desc = repo.get("description", "")
        stars = repo.get("stars", 0)
        language = repo.get("language", "N/A")
        topics = ", ".join(repo.get("topics", [])[:8])

        prompt = f"""项目: {name}
星数: {stars}
语言: {language}
标签: {topics}
简介: {desc}

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
            print(f"  [WARN] Repo summary failed for {name}: {e}")
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
            post["summary_cn"] = ""
            post["title_cn"] = ""
            print(f"  [FILTERED] {title}")
            continue

        # Step 3: Summarize
        result = summarize_article(title, text)

        post["summary_cn"] = result["summary_cn"]
        post["title_cn"] = result["title_cn"]
        print(f"  [OK] {result['title_cn']}")
        results.append(post)

    # Safety net: if everything was filtered, keep all with original summaries
    if not results and posts:
        print(f"  [WARN] All {len(posts)} posts filtered, keeping all with original text.")
        for p in posts:
            p.setdefault("title_cn", "")
            p.setdefault("summary_cn", "")
        return posts

    return results
