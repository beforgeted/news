# AI Daily Digest

每天早上自动采集 AI/LLM/Agent 领域最新内容，经 LLM 评分筛选后推送中文摘要邮件。

## 数据源

| 源 | 内容 | 处理方式 |
|---|---|---|
| GitHub Trending | AI/Agent/LLM 相关热门仓库 | LLM 翻译标题 + 生成 80 字解读 |
| OpenAI / Anthropic / DeepMind / Meta AI / HuggingFace 博客 | 最新文章 | 抓全文 → LLM 评分+150字摘要+翻译标题 |
| Arxiv | LLM/Agent 方向新论文 | LLM 翻译标题 + 120字学术解读 |

## 工作流程

```
并行采集 (GitHub / RSS / Arxiv)
  → LLM 评分排序 (1-10分，<5分丢弃)
  → 去重 + 合并
  → 生成每日导读
  → HTML 邮件 + Markdown 文件
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key 和邮箱信息

# 3. 运行
python -m src.main
```

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 是 |
| `DEEPSEEK_MODEL` | 模型名称，默认 `deepseek-chat` | 否 |
| `DEEPSEEK_BASE_URL` | API 地址，默认 `https://api.deepseek.com` | 否 |
| `SMTP_USER` | 发件邮箱 | 仅邮件推送 |
| `SMTP_PASS` | 邮箱授权码 | 仅邮件推送 |
| `RECIPIENT` | 收件邮箱 | 仅邮件推送 |
| `DIGEST_OUTPUT_DIR` | Markdown 输出目录，不配则不保存本地文件 | 否 |

不配置 SMTP 时仅输出 Markdown 到本地文件；两者都不配则仅打印终端日志。

## GitHub Actions 部署

1. Fork 本项目
2. Settings → Secrets → Actions 添加上述环境变量
3. 每天北京时间 09:00 自动运行，也可手动触发

## 项目结构

```
src/
├── collectors/          # 数据采集
│   ├── github_trending.py
│   ├── rss_blogs.py
│   └── arxiv_papers.py
├── llm_summarizer.py    # LLM 评分、摘要、翻译、导读
├── content_extractor.py # 网页正文提取
├── digest.py            # 去重、合并、历史管理
├── render.py            # HTML/Markdown 渲染
├── mailer.py            # SMTP 发送
└── main.py              # 入口，并行调度
config/sources.yaml      # 数据源配置
templates/email.html     # 邮件模板
```
