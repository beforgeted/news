import os
import json
import re
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


def _parse_llm_json(text: str) -> dict:
    """解析 LLM 返回的 JSON，失败时用正则兜底。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        score_m = re.search(r'"score"\s*:\s*(\d+)', text)
        title_m = re.search(r'"title_cn"\s*:\s*"((?:\\.|[^"\\])*)"', text)
        summary_m = re.search(r'"summary"\s*:\s*"((?:\\.|[^"\\])*)"', text)
        return {
            "score": int(score_m.group(1)) if score_m else 5,
            "title_cn": title_m.group(1) if title_m else "",
            "summary": summary_m.group(1) if summary_m else "",
        }


def _summarize_article_cn(title: str, text: str) -> str:
    """为博客生成约150字中文摘要（评分失败时的兜底）。"""
    content = f"标题: {title}\n\n正文: {text[:4000]}"
    try:
        return _call_llm_with_retry(
            messages=[
                {"role": "system", "content": "你是技术博客编辑。用约150字中文总结文章核心内容，只输出摘要正文。"},
                {"role": "user", "content": content},
            ],
            max_tokens=400,
            temperature=0.3,
        )
    except Exception:
        return ""


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
        data = _parse_llm_json(result)
        return {
            "score": int(data.get("score", 5)),
            "title_cn": (data.get("title_cn") or "").strip('"\''),
            "summary_cn": data.get("summary") or data.get("summary_cn") or "",
        }
    except Exception as e:
        print(f"  [WARN] score_article failed for {title[:40]}: {e}")
        return {"score": 5, "title_cn": "", "summary_cn": ""}


def _chinese_ratio(text: str) -> float:
    """中文字符占比，用于校验输出是否为中文。"""
    if not text or not text.strip():
        return 0.0
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    total = cjk + latin
    return cjk / total if total else 0.0


def _is_mostly_chinese(text: str, threshold: float = 0.25) -> bool:
    return _chinese_ratio(text) >= threshold and bool(re.search(r"[\u4e00-\u9fff]", text))


def _generate_chinese_summary(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 250,
    max_attempts: int = 3,
) -> str:
    """生成中文摘要，不通过校验则带审核反馈重试。"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result = ""

    for attempt in range(max_attempts):
        result = _call_llm_with_retry(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2 if attempt else 0.3,
        )
        cleaned = result.strip().strip('"\'')
        if _is_mostly_chinese(cleaned):
            return cleaned

        if attempt < max_attempts - 1:
            print(f"  [WARN] 摘要非中文，重试 ({attempt + 1}/{max_attempts - 1})...")
            messages = messages + [
                {"role": "assistant", "content": result},
                {
                    "role": "user",
                    "content": "审核未通过：输出必须为纯中文简介，约100字，禁止英文句子。请重写。",
                },
            ]

    return result.strip().strip('"\'') if result else ""


def _summarize_repo_cn(repo: dict, style: str) -> str:
    """为 GitHub 项目生成中文简介，失败时用描述兜底翻译。"""
    if style == "trending":
        user_prompt = f"""项目: {repo.get('name', '')}
本周涨星: {repo.get('stars_gained', 0)}
总星数: {repo.get('stars', 0)}
语言: {repo.get('language', 'N/A')}
标签: {', '.join(repo.get('topics', [])[:8])}
简介: {repo.get('description', '')}

请用约100字中文介绍：这个项目是什么、为什么值得关注，突出其创新点或近期热门原因。只输出简介正文。"""
    else:
        user_prompt = f"""项目: {repo.get('name', '')}
总星数: {repo.get('stars', 0)}
语言: {repo.get('language', 'N/A')}
标签: {', '.join(repo.get('topics', [])[:8])}
简介: {repo.get('description', '')}
最近更新: {repo.get('recent_activity', '') or repo.get('pushed_at', '')}

请用约100字中文介绍：这个项目是干什么的、最近更新了什么（新功能/版本/重要改动）。只输出简介正文。"""

    system_prompt = (
        "你是一个技术编辑，擅长用简洁中文介绍开源项目。"
        "必须用纯中文输出，禁止英文句子，不要任何前缀或标题。"
    )
    summary = _generate_chinese_summary(system_prompt, user_prompt)

    if not _is_mostly_chinese(summary):
        desc = repo.get("description", "")
        if desc:
            try:
                summary = _call_llm_with_retry(
                    messages=[
                        {
                            "role": "system",
                            "content": "将以下开源项目信息改写为约100字纯中文简介。只输出中文正文。",
                        },
                        {"role": "user", "content": f"项目: {repo.get('name', '')}\n简介: {desc}"},
                    ],
                    max_tokens=250,
                    temperature=0.2,
                ).strip()
            except Exception:
                summary = ""

    return summary.strip().strip('"\'')


def summarize_trending_repos(repos: list[dict]) -> list[dict]:
    """为近一周涨星项目生成中文简介（约100字）。"""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        for r in repos:
            r.setdefault("summary_cn", "")
        return repos

    for repo in repos:
        try:
            repo["summary_cn"] = _summarize_repo_cn(repo, style="trending")
        except Exception as e:
            print(f"  [WARN] Trending repo summary failed for {repo.get('name', '?')}: {e}")
            repo["summary_cn"] = ""

    return repos


def summarize_active_repos(repos: list[dict]) -> list[dict]:
    """为近月活跃高星项目生成中文简介（约100字）。"""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        for r in repos:
            r.setdefault("summary_cn", "")
        return repos

    for repo in repos:
        try:
            repo["summary_cn"] = _summarize_repo_cn(repo, style="active")
        except Exception as e:
            print(f"  [WARN] Active repo summary failed for {repo.get('name', '?')}: {e}")
            repo["summary_cn"] = ""

    return repos


def summarize_repos(repos: list[dict]) -> list[dict]:
    """兼容旧接口，默认按涨星榜风格生成摘要。"""
    return summarize_trending_repos(repos)


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
        post["title_cn"] = result["title_cn"] or translate_title(title)
        post["summary_cn"] = result["summary_cn"] or _summarize_article_cn(title, text)
        scored.append(post)
        status = "✓" if result["score"] >= MIN_SCORE else "✗"
        print(f"  [{status} score={result['score']}] {title[:60]}")

    # Sort by score descending
    scored.sort(key=lambda p: p.get("score", 0), reverse=True)

    kept = [p for p in scored if p.get("score", 0) >= MIN_SCORE][:MAX_ARTICLES]
    dropped = len(scored) - len(kept)
    print(f"  [INFO] Kept {len(kept)}, dropped {dropped} (threshold={MIN_SCORE})")

    return kept


def _is_complete_highlight(text: str) -> bool:
    """判断导读是否完整（非截断）。"""
    text = text.strip()
    if len(text) < 80:
        return False
    return text[-1] in "。！？…"


def generate_highlight(sections: dict) -> str:
    """Generate a 2-3 sentence daily highlight based on all content."""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        return ""

    blog_count = len(sections.get("blogs", []))
    gh_trending = len(sections.get("github_trending", []))
    gh_active = len(sections.get("github_active", []))
    gh_count = gh_trending + gh_active
    paper_count = len(sections.get("papers", []))

    if blog_count + gh_count + paper_count == 0:
        return ""

    lines = [
        f"今日共筛选 {blog_count} 篇博客、{gh_trending} 个涨星项目、"
        f"{gh_active} 个活跃项目、{paper_count} 篇论文。"
    ]

    top_blogs = sections.get("blogs", [])[:3]
    if top_blogs:
        lines.append("重点博客:")
        for b in top_blogs:
            title = b.get("title_cn") or b.get("title", "")
            score = b.get("score", "?")
            summary = (b.get("summary_cn") or "")[:120]
            lines.append(f"  [{score}分] {title} — {summary}")

    top_repos = sections.get("github_trending", [])[:2] + sections.get("github_active", [])[:1]
    if top_repos:
        lines.append("热门项目:")
        for r in top_repos:
            name = r.get("name_cn") or r.get("name", "")
            summary = (r.get("summary_cn") or r.get("description") or "")[:120]
            lines.append(f"  {name} — {summary}")

    top_papers = sections.get("papers", [])[:2]
    if top_papers:
        lines.append("重点论文:")
        for p in top_papers:
            title = p.get("title_cn") or p.get("title", "")
            summary = (p.get("summary_cn") or "")[:120]
            lines.append(f"  {title} — {summary}")

    context = "\n".join(lines)
    system_prompt = (
        "你是一个 AI 技术编辑，擅长用简洁中文总结每日技术动态。"
        "必须写完整的 3 句话，约 120-180 字，以句号结尾。"
        "第1句概括今日主题，第2-3句点名推荐 2-3 个具体内容（含名称）。"
        "只输出导读正文，不要标题、不要前缀、不要列表符号。"
    )
    user_prompt = f"""以下是今日 digest 的精选内容摘要：

{context}

请写一段完整的「今日导读」。"""

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = ""

        for attempt in range(3):
            result = _call_llm_with_retry(
                messages=messages,
                max_tokens=512,
                temperature=0.4 if attempt else 0.5,
            ).strip().strip('"\'')
            if _is_complete_highlight(result):
                return result
            if attempt < 2:
                print(f"  [WARN] 导读不完整，重试 ({attempt + 1}/2)...")
                messages = messages + [
                    {"role": "assistant", "content": result},
                    {
                        "role": "user",
                        "content": "上次输出不完整或未写完。请重写完整导读，必须包含具体推荐并以句号结尾。",
                    },
                ]

        return result
    except Exception as e:
        print(f"  [WARN] generate_highlight failed: {e}")
        return ""
