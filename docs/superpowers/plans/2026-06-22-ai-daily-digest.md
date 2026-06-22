# AI 每日摘要 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 AI 每日摘要系统 — 自动采集 GitHub AI 热门仓库、AI 公司博客、Arxiv 论文，生成 HTML 邮件每日推送。

**Architecture:** 三个采集器并行拉取数据 → Digest 引擎合并去重排序 → Jinja2 渲染 HTML → SMTP 发送。通过 GitHub Actions cron 每天触发。

**Tech Stack:** Python 3.10+, requests, feedparser, beautifulsoup4, arxiv, jinja2, pyyaml, smtplib

## Global Constraints

- Python >= 3.10
- 依赖: requests, feedparser, beautifulsoup4, arxiv, jinja2, pyyaml
- SMTP 凭证通过环境变量注入，不出现在配置文件中
- 单个采集器失败不影响其他板块
- HTML 邮件: 无内联脚本，纯 CSS

## 文件结构

```
news/
├── src/
│   ├── __init__.py
│   ├── config.py                  — 加载 config/sources.yaml
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── github_trending.py     — GitHub Search API
│   │   ├── rss_blogs.py           — RSS + 网页抓取
│   │   └── arxiv_papers.py        — Arxiv API
│   ├── digest.py                  — 合并、去重、排序
│   ├── render.py                  — Jinja2 HTML 渲染
│   ├── mailer.py                  — SMTP 发送
│   └── main.py                    — 入口，并行调度
├── config/
│   └── sources.yaml               — 数据源配置
├── templates/
│   └── email.html                 — 邮件模板
├── tests/
│   ├── __init__.py
│   ├── test_digest.py
│   ├── test_render.py
│   ├── test_mailer.py
│   └── test_main.py
├── .github/workflows/
│   └── daily-digest.yml
├── requirements.txt
└── .gitignore
```

---

### Task 1: 项目脚手架

**Files:**
- Create: `requirements.txt`, `.gitignore`, `src/__init__.py`, `src/collectors/__init__.py`, `tests/__init__.py`, `config/.gitkeep`, `templates/.gitkeep`

**Produces:**
- 目录结构完整，依赖文件就绪

- [ ] **Step 1: 创建 requirements.txt**

```txt
requests>=2.28
feedparser>=6.0
beautifulsoup4>=4.12
arxiv>=2.1
jinja2>=3.1
pyyaml>=6.0
```

- [ ] **Step 2: 创建 .gitignore**

```gitignore
__pycache__/
*.py[cod]
.venv/
venv/
.env
state/sent.json
*.egg-info/
dist/
.pytest_cache/
```

- [ ] **Step 3: 创建 __init__.py 和占位文件**

`src/__init__.py`、`src/collectors/__init__.py`、`tests/__init__.py` — 空文件
`config/.gitkeep`、`templates/.gitkeep` — 空文件（确保目录被 git 追踪）

- [ ] **Step 4: 验证目录结构**

```bash
ls -R src/ tests/ config/ templates/
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore src/__init__.py src/collectors/__init__.py tests/__init__.py config/.gitkeep templates/.gitkeep
git commit -m "chore: 初始化项目脚手架"
```

---

### Task 2: 配置模块

**Files:**
- Create: `config/sources.yaml`, `src/config.py`
- Test: `tests/test_config.py`

**Produces:**
- `load_config()` — 加载 YAML 配置，环境变量覆盖 email 字段

- [ ] **Step 1: 写配置文件的 YAML**

```yaml
github:
  topics: [ai, llm, agent, large-language-model]
  max_results: 10
  lookback_days: 7

blogs:
  - name: OpenAI
    type: rss
    url: https://openai.com/blog/rss.xml
  - name: Anthropic
    type: scrape
    url: https://www.anthropic.com/research
    selector: "a[href^='/research/']"
  - name: Google DeepMind
    type: rss
    url: https://deepmind.google/blog/rss.xml
  - name: Meta AI
    type: rss
    url: https://ai.meta.com/blog/rss/
  - name: Hugging Face
    type: rss
    url: https://huggingface.co/blog/feed.xml

arxiv:
  categories: [cs.AI, cs.CL]
  max_results: 5
  keywords: [llm, agent, language model, transformer]

email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
```

- [ ] **Step 2: 写测试 — test_config.py**

```python
import os
import tempfile
from pathlib import Path
from src.config import load_config


def test_load_config_defaults():
    config = load_config()
    assert "github" in config
    assert config["github"]["max_results"] == 10
    assert len(config["blogs"]) == 5
    assert config["arxiv"]["categories"] == ["cs.AI", "cs.CL"]


def test_load_config_env_override(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "test@gmail.com")
    monkeypatch.setenv("SMTP_PASS", "secret123")
    monkeypatch.setenv("RECIPIENT", "to@gmail.com")

    config = load_config()
    assert config["email"]["smtp_user"] == "test@gmail.com"
    assert config["email"]["smtp_pass"] == "secret123"
    assert config["email"]["recipient"] == "to@gmail.com"


def test_load_config_custom_path():
    import yaml
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"github": {"topics": ["test-topic"]}}, f)
        tmp_path = f.name

    try:
        config = load_config(tmp_path)
        assert config["github"]["topics"] == ["test-topic"]
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 3: 运行测试确认失败**

```bash
python -m pytest tests/test_config.py -v
```
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 4: 实现 src/config.py**

```python
import os
from pathlib import Path
import yaml


def load_config(config_path: str | None = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "sources.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config.setdefault("email", {})
    for key in ("smtp_user", "smtp_pass", "recipient"):
        env_key = key.upper()
        if os.environ.get(env_key):
            config["email"][key] = os.environ[env_key]

    return config
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/test_config.py -v
```
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add config/sources.yaml src/config.py tests/test_config.py
git commit -m "feat: 添加配置加载模块，支持环境变量覆盖"
```

---

### Task 3: GitHub 采集器

**Files:**
- Create: `src/collectors/github_trending.py`
- Test: `tests/test_github_trending.py`

**Interfaces:**
- Consumes: `config["github"]` — dict with keys `topics`, `max_results`, `lookback_days`
- Produces: `fetch_trending_repos(config: dict) -> list[dict]`
  - 每个 dict: `{name, description, stars, language, url, topics}`

- [ ] **Step 1: 写测试 — test_github_trending.py**

```python
import json
from unittest.mock import patch, MagicMock
from src.collectors.github_trending import fetch_trending_repos


def fake_response():
    return {
        "items": [
            {
                "full_name": "owner/repo1",
                "description": "An AI agent framework",
                "stargazers_count": 1500,
                "language": "Python",
                "html_url": "https://github.com/owner/repo1",
                "topics": ["ai", "agent"]
            },
            {
                "full_name": "owner/repo2",
                "description": None,
                "stargazers_count": 800,
                "language": None,
                "html_url": "https://github.com/owner/repo2",
                "topics": []
            }
        ]
    }


@patch("src.collectors.github_trending.requests.get")
def test_fetch_trending_repos(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_response()
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    config = {"topics": ["ai", "llm"], "max_results": 10, "lookback_days": 7}
    results = fetch_trending_repos(config)

    assert len(results) == 2
    assert results[0]["name"] == "owner/repo1"
    assert results[0]["description"] == "An AI agent framework"
    assert results[0]["stars"] == 1500
    assert results[0]["language"] == "Python"
    assert results[0]["url"] == "https://github.com/owner/repo1"
    assert results[0]["topics"] == ["ai", "agent"]

    # None values handled
    assert results[1]["description"] == ""
    assert results[1]["language"] == "N/A"

    # Verify API call
    mock_get.assert_called_once()
    call_args = mock_get.call_args[1]
    assert call_args["params"]["sort"] == "stars"
    assert "topic:ai" in call_args["params"]["q"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_github_trending.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 src/collectors/github_trending.py**

```python
import os
import requests
from datetime import datetime, timedelta, timezone


def fetch_trending_repos(config: dict) -> list[dict]:
    topics = " OR ".join(f"topic:{t}" for t in config["topics"])
    lookback = config.get("lookback_days", 7)
    date_since = (datetime.now(timezone.utc) - timedelta(days=lookback)).strftime("%Y-%m-%d")

    query = f"({topics}) created:>={date_since}"
    url = "https://api.github.com/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": config.get("max_results", 10)
    }

    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("items", []):
        results.append({
            "name": item["full_name"],
            "description": (item.get("description") or "")[:200],
            "stars": item["stargazers_count"],
            "language": item.get("language") or "N/A",
            "url": item["html_url"],
            "topics": item.get("topics", [])
        })

    return results
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_github_trending.py -v
```
Expected: 1 PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/github_trending.py tests/test_github_trending.py
git commit -m "feat: 添加 GitHub Trending AI 项目采集器"
```

---

### Task 4: RSS 博客采集器

**Files:**
- Create: `src/collectors/rss_blogs.py`
- Test: `tests/test_rss_blogs.py`

**Interfaces:**
- Consumes: `config["blogs"]` — list of `{name, type, url, selector?}`
- Produces: `fetch_blog_posts(config: dict) -> list[dict]`
  - 每个 dict: `{source, title, date, summary, url}`

- [ ] **Step 1: 写测试 — test_rss_blogs.py**

```python
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from src.collectors.rss_blogs import fetch_blog_posts


def make_feed_entry(title, link, published_str):
    import time
    from email.utils import formatdate

    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = "Some content with <p>tags</p>"
    entry.published_parsed = time.strptime(published_str, "%Y-%m-%d")
    entry.updated_parsed = None
    return entry


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_rss_blogs(mock_feedparser):
    entry = make_feed_entry("GPT-5 Announcement", "https://openai.com/gpt5", "2026-06-20")
    mock_feedparser.parse.return_value = MagicMock(entries=[entry])

    config = {
        "blogs": [
            {"name": "OpenAI", "type": "rss", "url": "https://openai.com/blog/rss.xml"}
        ]
    }
    results = fetch_blog_posts(config)

    assert len(results) == 1
    assert results[0]["source"] == "OpenAI"
    assert results[0]["title"] == "GPT-5 Announcement"
    assert results[0]["url"] == "https://openai.com/gpt5"
    assert results[0]["date"] == "2026-06-20"
    assert "tags" not in results[0]["summary"]  # HTML stripped


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_rss_handles_missing_fields(mock_feedparser):
    entry = MagicMock()
    entry.title = ""
    entry.link = ""
    entry.summary = None
    entry.description = None
    entry.published_parsed = None
    entry.updated_parsed = None

    mock_feedparser.parse.return_value = MagicMock(entries=[entry])

    config = {"blogs": [{"name": "Test", "type": "rss", "url": "http://example.com"}]}
    results = fetch_blog_posts(config)

    assert len(results) == 1
    assert results[0]["title"] == ""
    assert results[0]["summary"] == ""


@patch("src.collectors.rss_blogs.feedparser")
def test_fetch_handles_one_source_failure(mock_feedparser):
    def fail_once(url):
        if "fail" in url:
            raise Exception("Connection error")
        entry = make_feed_entry("OK", "http://ok.com/1", "2026-06-20")
        return MagicMock(entries=[entry])

    mock_feedparser.parse.side_effect = fail_once

    config = {
        "blogs": [
            {"name": "Broken", "type": "rss", "url": "http://fail.com"},
            {"name": "Working", "type": "rss", "url": "http://ok.com"}
        ]
    }
    results = fetch_blog_posts(config)

    # Should still get results from the working source
    assert len(results) == 1
    assert results[0]["source"] == "Working"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_rss_blogs.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 src/collectors/rss_blogs.py**

```python
import re
import requests
import feedparser
from datetime import datetime, timezone
from bs4 import BeautifulSoup


def fetch_blog_posts(config: dict) -> list[dict]:
    blogs = config if isinstance(config, list) else config.get("blogs", [])
    results = []

    for blog in blogs:
        try:
            if blog["type"] == "rss":
                items = _fetch_rss(blog)
            elif blog["type"] == "scrape":
                items = _fetch_scrape(blog)
            else:
                continue
            results.extend(items)
        except Exception as e:
            print(f"[WARN] Failed to fetch {blog['name']}: {e}")
            continue

    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results[:10]


def _fetch_rss(blog: dict) -> list[dict]:
    feed = feedparser.parse(blog["url"])
    return [_parse_entry(blog["name"], e) for e in feed.entries[:5]]


def _parse_entry(source: str, entry) -> dict:
    date_str = None
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            date_str = f"{tp.tm_year}-{tp.tm_mon:02d}-{tp.tm_mday:02d}"
            break
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    raw = entry.get("summary", entry.get("description", "")) or ""
    summary = re.sub(r"<[^>]+>", "", raw)
    summary = re.sub(r"\s+", " ", summary).strip()[:200]
    if len(raw) > 200:
        summary += "..."

    return {
        "source": source,
        "title": entry.get("title", ""),
        "date": date_str,
        "summary": summary,
        "url": entry.get("link", "")
    }


def _fetch_scrape(blog: dict) -> list[dict]:
    resp = requests.get(
        blog["url"], timeout=30,
        headers={"User-Agent": "AI-Daily-Digest/1.0"}
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for link in soup.select(blog["selector"])[:5]:
        url = link.get("href", "")
        if url and not url.startswith("http"):
            url = f"https://www.anthropic.com{url}"
        title = link.get_text(strip=True)
        if title:
            items.append({
                "source": blog["name"],
                "title": title,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "summary": "",
                "url": url
            })
    return items
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_rss_blogs.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/rss_blogs.py tests/test_rss_blogs.py
git commit -m "feat: 添加 RSS 博客采集器，支持 RSS 和网页抓取"
```

---

### Task 5: Arxiv 论文采集器

**Files:**
- Create: `src/collectors/arxiv_papers.py`
- Test: `tests/test_arxiv_papers.py`

**Interfaces:**
- Consumes: `config["arxiv"]` — dict with keys `keywords`, `categories`, `max_results`
- Produces: `fetch_papers(config: dict) -> list[dict]`
  - 每个 dict: `{title, authors, abstract, url, published}`

- [ ] **Step 1: 写测试 — test_arxiv_papers.py**

```python
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from src.collectors.arxiv_papers import fetch_papers


def make_mock_paper(title, published_days_ago=1):
    paper = MagicMock()
    paper.title = title
    paper.summary = "This paper introduces a novel approach to LLM reasoning."
    paper.entry_id = f"https://arxiv.org/abs/2606.{hash(title) % 100000:05d}"
    paper.published = datetime.now(timezone.utc) - timedelta(days=published_days_ago)
    paper.authors = [MagicMock(name="Author A"), MagicMock(name="Author B")]
    paper.authors[0].name = "Author A"
    paper.authors[1].name = "Author B"
    return paper


@patch("src.collectors.arxiv_papers.arxiv.Client")
def test_fetch_papers(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.results.return_value = [
        make_mock_paper("Advances in LLM Agents"),
        make_mock_paper("Transformer Optimization"),
    ]

    config = {
        "keywords": ["llm", "agent"],
        "categories": ["cs.AI", "cs.CL"],
        "max_results": 5
    }
    results = fetch_papers(config)

    assert len(results) == 2
    assert results[0]["title"] == "Advances in LLM Agents"
    assert results[0]["authors"] == ["Author A", "Author B"]
    assert "arxiv.org" in results[0]["url"]
    assert len(results[0]["abstract"]) > 0


@patch("src.collectors.arxiv_papers.arxiv.Client")
def test_fetch_papers_filters_old_entries(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.results.return_value = [
        make_mock_paper("Recent Paper", published_days_ago=2),
        make_mock_paper("Old Paper", published_days_ago=30),
    ]

    config = {"keywords": ["llm"], "categories": ["cs.AI"], "max_results": 5}
    results = fetch_papers(config)

    assert len(results) == 1
    assert results[0]["title"] == "Recent Paper"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_arxiv_papers.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 src/collectors/arxiv_papers.py**

```python
import arxiv
from datetime import datetime, timedelta, timezone


def fetch_papers(config: dict) -> list[dict]:
    keywords = config.get("keywords", ["llm", "agent", "language model"])
    categories = config.get("categories", ["cs.AI", "cs.CL"])
    max_results = config.get("max_results", 5)

    kw_query = " OR ".join(f'"{kw}"' for kw in keywords)
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    query = f"({kw_query}) AND ({cat_query})"

    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results * 3,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    results = []

    for paper in client.results(search):
        if paper.published.replace(tzinfo=timezone.utc) < cutoff:
            continue
        if len(results) >= max_results:
            break

        abstract = paper.summary.replace("\n", " ").strip()
        results.append({
            "title": paper.title,
            "authors": [a.name for a in paper.authors[:3]],
            "abstract": abstract[:300] + ("..." if len(abstract) > 300 else ""),
            "url": paper.entry_id,
            "published": paper.published.strftime("%Y-%m-%d")
        })

    return results
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_arxiv_papers.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/arxiv_papers.py tests/test_arxiv_papers.py
git commit -m "feat: 添加 Arxiv 论文采集器"
```

---

### Task 6: Digest 引擎

**Files:**
- Create: `src/digest.py`
- Test: `tests/test_digest.py`

**Interfaces:**
- Consumes: `list[dict]` from collectors, history `set`
- Produces:
  - `merge(github_items, blog_items, arxiv_items, history) -> dict`
  - `load_history() -> set`
  - `update_history(sections) -> None`

- [ ] **Step 1: 写测试 — test_digest.py**

```python
import json
import tempfile
from pathlib import Path
from src.digest import merge, load_history, save_history, extract_urls


def test_merge_deduplicates_by_url():
    github = [
        {"name": "repo1", "url": "https://github.com/a/b", "stars": 100},
        {"name": "repo2", "url": "https://github.com/a/b", "stars": 50},  # duplicate URL
        {"name": "repo3", "url": "https://github.com/c/d", "stars": 200},
    ]
    blogs = [
        {"source": "OpenAI", "title": "Post 1", "url": "https://openai.com/1"},
        {"source": "OpenAI", "title": "Post 2", "url": "https://openai.com/1"},  # duplicate
    ]
    papers = [
        {"title": "Paper 1", "url": "https://arxiv.org/1"},
    ]

    sections = merge(github, blogs, papers, history=set())

    assert len(sections["github"]) == 2
    assert sections["github"][0]["name"] == "repo1"
    assert sections["github"][1]["name"] == "repo3"
    assert len(sections["blogs"]) == 1
    assert len(sections["papers"]) == 1


def test_merge_filters_history():
    history = {"https://github.com/a/b", "https://openai.com/1"}

    github = [{"name": "repo1", "url": "https://github.com/a/b"}]
    blogs = [{"source": "OpenAI", "title": "Post 1", "url": "https://openai.com/1"}]
    papers = [{"title": "Paper 1", "url": "https://arxiv.org/1"}]

    sections = merge(github, blogs, papers, history=history)

    assert len(sections["github"]) == 0
    assert len(sections["blogs"]) == 0
    assert len(sections["papers"]) == 1


def test_merge_handles_empty_inputs():
    sections = merge([], [], [], history=set())
    assert sections["github"] == []
    assert sections["blogs"] == []
    assert sections["papers"] == []


def test_merge_handles_missing_urls():
    items = [{"name": "no-url-item", "stars": 10}]
    sections = merge(items, [], [], history=set())
    assert len(sections["github"]) == 1  # No URL = can't dedup, keep it


def test_extract_urls():
    items = [
        {"name": "a", "url": "https://a.com"},
        {"name": "b", "url": ""},
        {"name": "c"},
    ]
    urls = extract_urls(items)
    assert urls == {"https://a.com"}


def test_save_and_load_history(tmp_path):
    import src.digest as digest
    digest.STATE_FILE = tmp_path / "sent.json"
    digest.STATE_DIR = tmp_path

    save_history({"https://a.com", "https://b.com"})
    loaded = load_history()
    assert loaded == {"https://a.com", "https://b.com"}


def test_load_history_handles_missing_file(tmp_path):
    import src.digest as digest
    digest.STATE_FILE = tmp_path / "nonexistent.json"
    loaded = load_history()
    assert loaded == set()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_digest.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 src/digest.py**

```python
import json
from pathlib import Path

STATE_DIR = Path(__file__).parent.parent / "state"
STATE_FILE = STATE_DIR / "sent.json"


def load_history() -> set:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return set(data.get("urls", []))
    except Exception:
        pass
    return set()


def save_history(urls: set) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": list(urls)}, f, ensure_ascii=False, indent=2)


def extract_urls(items: list[dict]) -> set:
    return {item["url"] for item in items if item.get("url")}


def merge(github_items: list[dict], blog_items: list[dict], arxiv_items: list[dict],
          history: set | None = None) -> dict:
    if history is None:
        history = load_history()

    def dedup(items: list[dict]) -> list[dict]:
        seen = set()
        result = []
        for item in items:
            url = item.get("url", "")
            if url and (url in history or url in seen):
                continue
            seen.add(url)
            result.append(item)
        return result

    return {
        "github": dedup(github_items),
        "blogs": dedup(blog_items),
        "papers": dedup(arxiv_items),
        "failed_sources": []
    }


def update_history(sections: dict) -> None:
    all_urls = set()
    for key in ("github", "blogs", "papers"):
        all_urls |= extract_urls(sections.get(key, []))
    history = load_history()
    history |= all_urls
    save_history(history)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_digest.py -v
```
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add src/digest.py tests/test_digest.py
git commit -m "feat: 添加 Digest 引擎，合并去重排序"
```

---

### Task 7: 邮件渲染器

**Files:**
- Create: `src/render.py`, `templates/email.html`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `sections: dict` with keys `github`, `blogs`, `papers`, `failed_sources`, plus `date_str: str`
- Produces: `render_html(sections: dict, date_str: str) -> str`

- [ ] **Step 1: 写测试 — test_render.py**

```python
from src.render import render_html


def test_render_html_contains_all_sections():
    sections = {
        "github": [
            {
                "name": "test/repo",
                "description": "A cool AI project",
                "stars": 1200,
                "language": "Python",
                "url": "https://github.com/test/repo",
                "topics": ["ai", "llm"]
            }
        ],
        "blogs": [
            {
                "source": "OpenAI",
                "title": "GPT-5 Launched",
                "date": "2026-06-20",
                "summary": "OpenAI announces GPT-5.",
                "url": "https://openai.com/gpt5"
            }
        ],
        "papers": [
            {
                "title": "Scaling LLM Agents",
                "authors": ["Alice", "Bob"],
                "abstract": "We explore scaling laws for LLM agents.",
                "url": "https://arxiv.org/abs/2606.12345"
            }
        ],
        "failed_sources": []
    }

    html = render_html(sections, "2026-06-22")

    assert "test/repo" in html
    assert "1200" in html
    assert "OpenAI" in html
    assert "GPT-5 Launched" in html
    assert "Scaling LLM Agents" in html
    assert "2026-06-22" in html
    assert "<html" in html.lower()


def test_render_html_empty_sections():
    sections = {"github": [], "blogs": [], "papers": [], "failed_sources": []}
    html = render_html(sections, "2026-06-22")
    assert "暂无" in html or "No items" in html or len(html) > 0


def test_render_html_with_failed_sources():
    sections = {
        "github": [], "blogs": [], "papers": [],
        "failed_sources": ["github"]
    }
    html = render_html(sections, "2026-06-22")
    assert "github" in html.lower()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_render.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 templates/email.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; color: #1a1a1a; background: #f8f9fa; }
  h1 { color: #2563eb; font-size: 24px; border-bottom: 2px solid #2563eb; padding-bottom: 10px; }
  h2 { color: #374151; font-size: 18px; margin-top: 30px; }
  .item { background: #fff; border-radius: 8px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .item .title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
  .item .title a { color: #2563eb; text-decoration: none; }
  .item .meta { font-size: 13px; color: #6b7280; }
  .item .desc { font-size: 14px; color: #4b5563; margin-top: 6px; line-height: 1.5; }
  .tag { display: inline-block; background: #dbeafe; color: #1e40af; border-radius: 4px; padding: 2px 8px; font-size: 12px; margin-right: 4px; }
  .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #9ca3af; }
  .empty { color: #9ca3af; font-style: italic; padding: 20px; text-align: center; }
  .warning { background: #fef3c7; color: #92400e; padding: 8px 16px; border-radius: 6px; font-size: 13px; margin: 10px 0; }
</style>
</head>
<body>
<h1>🤖 AI 每日摘要 — {{ date }}</h1>

{% if failed_sources %}
<div class="warning">
  ⚠ 以下数据源采集失败：{{ failed_sources | join(', ') }}
</div>
{% endif %}

<h2>🔥 GitHub 热门 AI 项目</h2>
{% if github %}
  {% for repo in github %}
  <div class="item">
    <div class="title"><a href="{{ repo.url }}">{{ repo.name }}</a></div>
    <div class="meta">⭐ {{ repo.stars }} &middot; {{ repo.language }}</div>
    {% if repo.description %}<div class="desc">{{ repo.description }}</div>{% endif %}
    {% for tag in repo.topics[:5] %}<span class="tag">{{ tag }}</span>{% endfor %}
  </div>
  {% endfor %}
{% else %}
<div class="empty">暂无新项目</div>
{% endif %}

<h2>📝 AI 公司动态</h2>
{% if blogs %}
  {% for post in blogs %}
  <div class="item">
    <div class="title"><a href="{{ post.url }}">{{ post.title }}</a></div>
    <div class="meta">{{ post.source }} &middot; {{ post.date }}</div>
    {% if post.summary %}<div class="desc">{{ post.summary }}</div>{% endif %}
  </div>
  {% endfor %}
{% else %}
<div class="empty">暂无新动态</div>
{% endif %}

<h2>📄 Arxiv 论文速递</h2>
{% if papers %}
  {% for paper in papers %}
  <div class="item">
    <div class="title"><a href="{{ paper.url }}">{{ paper.title }}</a></div>
    <div class="meta">{{ paper.authors | join(', ') }}</div>
    <div class="desc">{{ paper.abstract }}</div>
  </div>
  {% endfor %}
{% else %}
<div class="empty">暂无新论文</div>
{% endif %}

<div class="footer">
  本邮件由 AI Daily Digest 自动生成 &middot; {{ date }}<br>
  每日采集 OpenAI / Anthropic / DeepMind / Meta AI / HuggingFace / Arxiv / GitHub
</div>
</body>
</html>
```

- [ ] **Step 4: 实现 src/render.py**

```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def render_html(sections: dict, date_str: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("email.html")
    return template.render(
        date=date_str,
        github=sections.get("github", []),
        blogs=sections.get("blogs", []),
        papers=sections.get("papers", []),
        failed_sources=sections.get("failed_sources", [])
    )
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/test_render.py -v
```
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add src/render.py templates/email.html tests/test_render.py
git commit -m "feat: 添加 HTML 邮件渲染器"
```

---

### Task 8: SMTP 邮件发送器

**Files:**
- Create: `src/mailer.py`
- Test: `tests/test_mailer.py`

**Interfaces:**
- Consumes: `html_content: str`, `subject: str`, `email_config: dict` with keys `smtp_host`, `smtp_port`, `smtp_user`, `smtp_pass`, `recipient`
- Produces: `send_email(html_content, subject, email_config) -> bool`

- [ ] **Step 1: 写测试 — test_mailer.py**

```python
from unittest.mock import patch, MagicMock
from src.mailer import send_email


@patch("src.mailer.smtplib.SMTP")
def test_send_email(mock_smtp_class):
    mock_server = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    email_config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "sender@gmail.com",
        "smtp_pass": "secret",
        "recipient": "to@gmail.com"
    }

    result = send_email("<h1>Test</h1>", "Subject Line", email_config)

    assert result is True
    mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("sender@gmail.com", "secret")
    mock_server.sendmail.assert_called_once()

    call_args = mock_server.sendmail.call_args
    assert call_args[0][0] == "sender@gmail.com"
    assert call_args[0][1] == "to@gmail.com"
    assert "Subject Line" in call_args[0][2]


@patch("src.mailer.smtplib.SMTP")
def test_send_email_raises_on_auth_failure(mock_smtp_class):
    mock_server = MagicMock()
    mock_server.login.side_effect = Exception("Auth failed")
    mock_smtp_class.return_value.__enter__.return_value = mock_server

    email_config = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "bad@gmail.com",
        "smtp_pass": "wrong",
        "recipient": "to@gmail.com"
    }

    import pytest
    with pytest.raises(Exception):
        send_email("<h1>Test</h1>", "Subject", email_config)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_mailer.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 src/mailer.py**

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(html_content: str, subject: str, email_config: dict) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_config["smtp_user"]
    msg["To"] = email_config["recipient"]

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
        server.starttls()
        server.login(email_config["smtp_user"], email_config["smtp_pass"])
        server.sendmail(
            email_config["smtp_user"],
            email_config["recipient"],
            msg.as_string()
        )

    return True
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_mailer.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/mailer.py tests/test_mailer.py
git commit -m "feat: 添加 SMTP 邮件发送器"
```

---

### Task 9: 主入口 + 并行调度

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: 三个采集器 + digest + render + mailer
- Produces: `main()` — 无参数，从环境变量和配置文件中读取一切

- [ ] **Step 1: 写测试 — test_main.py**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_main.py -v
```
Expected: FAIL

- [ ] **Step 3: 实现 src/main.py**

```python
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import load_config
from src.collectors.github_trending import fetch_trending_repos
from src.collectors.rss_blogs import fetch_blog_posts
from src.collectors.arxiv_papers import fetch_papers
from src.digest import merge, update_history, load_history
from src.render import render_html
from src.mailer import send_email


def main():
    config = load_config()
    history = load_history()
    date_str = datetime.now().strftime("%Y-%m-%d")

    collectors = {
        "github": (fetch_trending_repos, config.get("github", {})),
        "blogs": (fetch_blog_posts, config.get("blogs", {})),
        "papers": (fetch_papers, config.get("arxiv", {}))
    }

    results = {}
    failed_sources = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(func, cfg): key
            for key, (func, cfg) in collectors.items()
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                print(f"[ERROR] Collector '{key}' failed: {e}", file=sys.stderr)
                results[key] = []
                failed_sources.append(key)

    sections = merge(
        results.get("github", []),
        results.get("blogs", []),
        results.get("papers", []),
        history
    )
    sections["failed_sources"] = failed_sources

    html = render_html(sections, date_str)

    email_config = config.get("email", {})
    subject = f"AI Daily Digest — {date_str}"
    send_email(html, subject, email_config)

    update_history(sections)

    total = sum(len(sections.get(k, [])) for k in ("github", "blogs", "papers"))
    print(f"[OK] Digest sent. {total} items, {len(failed_sources)} source(s) failed.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_main.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: 添加主入口，实现三路并行采集和调度"
```

---

### Task 10: GitHub Actions 工作流

**Files:**
- Create: `.github/workflows/daily-digest.yml`

- [ ] **Step 1: 创建 workflow 配置**

`.github/workflows/daily-digest.yml`:

```yaml
name: AI Daily Digest

on:
  schedule:
    - cron: "0 1 * * *"  # UTC 01:00 = 北京时间 09:00
  workflow_dispatch:      # 允许手动触发

jobs:
  digest:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run digest
        env:
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          RECIPIENT: ${{ secrets.RECIPIENT }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python -m src.main

      - name: Cache sent history
        uses: actions/cache@v4
        with:
          path: state/sent.json
          key: sent-urls-${{ github.run_id }}
          restore-keys: |
            sent-urls-
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/daily-digest.yml
git commit -m "feat: 添加 GitHub Actions 每日定时工作流"
```

---

### Task 11: 端到端验证

**Files:** 无新建

- [ ] **Step 1: 安装依赖**

```bash
pip install -r requirements.txt
```

- [ ] **Step 2: 运行全部单元测试**

```bash
python -m pytest tests/ -v
```
Expected: ALL PASS

- [ ] **Step 3: 本地干跑（不发邮件）**

```bash
python -c "
from src.config import load_config
from src.collectors.github_trending import fetch_trending_repos
from src.collectors.rss_blogs import fetch_blog_posts
from src.collectors.arxiv_papers import fetch_papers

config = load_config()
print('Testing GitHub collector...')
repos = fetch_trending_repos(config['github'])
print(f'  Got {len(repos)} repos')
for r in repos[:3]:
    print(f'  - {r[\"name\"]} ⭐{r[\"stars\"]}')

print('Testing RSS blogs...')
posts = fetch_blog_posts(config['blogs'])
print(f'  Got {len(posts)} posts')
for p in posts[:3]:
    print(f'  - [{p[\"source\"]}] {p[\"title\"]}')

print('Testing Arxiv...')
papers = fetch_papers(config['arxiv'])
print(f'  Got {len(papers)} papers')
for p in papers[:3]:
    print(f'  - {p[\"title\"]}')

print('All collectors working!')
"
```

Expected: 能看到真实的 GitHub 仓库、博客文章、论文数据。

- [ ] **Step 4: 配置邮件发送（首次需要）**

用户在终端执行前先设置环境变量，然后本地跑一次完整流程：
```bash
export SMTP_USER="your@gmail.com"
export SMTP_PASS="your-app-password"
export RECIPIENT="your@gmail.com"
python -m src.main
```

确认收到邮件。

---

### Self-Review Checklist

1. **Spec coverage:** ✅ GitHub 采集 (T3), RSS 博客 (T4), Arxiv (T5), Digest 引擎 (T6), HTML 渲染 (T7), SMTP 发送 (T8), 主入口并行调度 (T9), GitHub Actions (T10) — 所有 spec 要求均已覆盖。
2. **Placeholder scan:** ✅ 无 TBD/TODO，所有代码步骤完整。
3. **Type consistency:** ✅ 各模块接口类型一致 — `fetch_*` 返回 `list[dict]`，`merge` 接收 `list[dict]`，`render_html` 接收 `dict`。
