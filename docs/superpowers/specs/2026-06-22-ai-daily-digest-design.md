# AI 每日摘要 — 设计文档

## 概述

通过 GitHub Actions 每天早上自动收集 AI/LLM/Agent 相关内容（GitHub 热门仓库、AI 公司博客、Arxiv 论文），生成摘要邮件推送到用户邮箱。

## 内容源

### GitHub 热门 AI 项目
- **采集方式**：GitHub Search API (`/search/repositories`)
- **查询条件**：按 AI/LLM/Agent 相关 topic 搜索，筛选近 7 天创建或活跃的仓库
- **排序**：按近期获得 star 数排序，取前 10 个
- **输出字段**：项目名、描述、star 数、语言、链接、标签

### AI 公司博客
- **采集方式**：RSS 优先，没有 RSS 则用 HTML 解析
- **来源列表**：
  - OpenAI Blog — RSS
  - Anthropic Research — 网页抓取
  - Google DeepMind — RSS
  - Meta AI Blog — RSS
  - Hugging Face Blog — RSS
- **输出字段**：来源标签、标题、发布日期、摘要（前 200 字）、链接

### Arxiv 论文
- **采集方式**：Arxiv API（`arxiv` Python 库）
- **查询条件**：LLM / Agent / Language Model 相关关键词 + cs.AI / cs.CL 分类，近 24 小时新发布
- **输出字段**：标题、作者、摘要（前 300 字）、链接

## 架构

```
GitHub Actions (每天北京时间 9:00 / UTC 01:00 触发)
├── src/collectors/
│   ├── github_trending.py   — GitHub Search API 采集
│   ├── rss_blogs.py          — RSS + 网页抓取（5 个博客源）
│   └── arxiv_papers.py      — Arxiv API 论文采集
├── src/digest.py             — 合并、去重、排序、组装
├── src/render.py             — HTML 邮件模板渲染
├── src/mailer.py             — SMTP 发送
├── src/main.py               — 入口
├── config/
│   └── sources.yaml          — 数据源配置（RSS URL、搜索词、阈值）
├── templates/
│   └── email.html            — Jinja2 邮件模板
├── .github/workflows/
│   └── daily-digest.yml      — 定时触发 + secrets 配置
└── state/
    └── sent.json              — 去重历史（通过 GitHub Actions cache 持久化）
```

## 数据流

1. GitHub Actions 每天 UTC 01:00 触发
2. `main.py` 并行启动三个采集器（多线程）
3. `digest.py` 合并结果：
   - 按 URL 去重
   - 移除 `sent.json` 中已发送的条目
   - 排序：GitHub 按 star 降序，博客按发布日期，论文按相关度
   - 每类条目上限：GitHub 10 条、博客 10 条、论文 5 条
4. `render.py` 用 Jinja2 模板渲染 HTML 邮件
5. `mailer.py` 通过 SMTP 发送
6. 更新 `sent.json` 并存入 GitHub Actions cache

## 配置

所有配置集中在 `config/sources.yaml`：

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
  # ... DeepMind, Meta, HuggingFace

arxiv:
  categories: [cs.AI, cs.CL]
  max_results: 5
  keywords: [llm, agent, language model, transformer]

email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  # 发件人 + 密码通过 GitHub Secrets 注入
```

## 依赖

```
python >= 3.10
requests, feedparser, beautifulsoup4, arxiv, jinja2, pyyaml
```

## GitHub Actions Secrets

| Secret | 说明 |
|--------|------|
| `SMTP_USER` | 发件邮箱地址 |
| `SMTP_PASS` | 邮箱应用专用密码 |
| `RECIPIENT` | 接收邮件的邮箱 |

## 错误处理

- 单个采集器失败 → 跳过该板块，其他板块正常包含，邮件底部注明异常
- SMTP 发送失败 → GitHub Actions job 标记失败，用户会收到通知
- 缓存未命中 → 视为首次运行，不做去重，不会失败

## 安全

- 所有数据自包含在仓库内，不依赖外部存储
- SMTP 凭证存放在 GitHub Secrets 中，不出现在配置文件里
- HTML 邮件：无内联脚本，仅纯 CSS

## 未来扩展（本期不做）

- Slack / Telegram 等推送渠道
- 用户自定义 GitHub star 追踪
- 接入 LLM 做内容摘要
- 交互式偏好调整
