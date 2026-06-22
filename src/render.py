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


def render_markdown(sections: dict, date_str: str) -> str:
    lines = [f"# AI 每日摘要 — {date_str}", ""]

    failed = sections.get("failed_sources", [])
    if failed:
        lines.append(f"> ⚠ 采集失败: {', '.join(failed)}")
        lines.append("")

    # GitHub
    lines.append("## 🔥 GitHub 热门 AI 项目")
    lines.append("")
    github = sections.get("github", [])
    if github:
        for repo in github:
            name_cn = repo.get("name_cn", "")
            desc = repo.get("description", "")
            topics = " ".join(f"`{t}`" for t in repo.get("topics", [])[:5])
            new_tag = " 🆕" if repo.get("is_new") else ""
            title_display = f"{name_cn}（{repo['name']}）" if name_cn else repo["name"]
            lines.append(f"- **[{title_display}]({repo['url']})**  ⭐{repo['stars']}  {repo['language']}{new_tag}")
            if desc:
                lines.append(f"  {desc}")
            if topics:
                lines.append(f"  {topics}")
            lines.append("")
    else:
        lines.append("暂无新项目")
        lines.append("")

    # Blogs
    lines.append("## 📝 AI 公司动态")
    lines.append("")
    blogs = sections.get("blogs", [])
    if blogs:
        for post in blogs:
            title_cn = post.get("title_cn", "")
            summary_cn = post.get("summary_cn", "")
            title_display = f"{title_cn}（{post['title']}）" if title_cn else post["title"]
            lines.append(f"- **[{title_display}]({post['url']})** — {post['source']} ({post['date']})")
            if summary_cn:
                lines.append(f"  {summary_cn}")
            else:
                summary = post.get("summary", "")
                if summary:
                    lines.append(f"  {summary}")
            lines.append("")
    else:
        lines.append("暂无新动态")
        lines.append("")

    # Papers
    lines.append("## 📄 Arxiv 论文速递")
    lines.append("")
    papers = sections.get("papers", [])
    if papers:
        for paper in papers:
            title_cn = paper.get("title_cn", "")
            authors = ", ".join(paper.get("authors", []))
            abstract = paper.get("abstract", "")
            title_display = f"{title_cn}（{paper['title']}）" if title_cn else paper["title"]
            lines.append(f"- **[{title_display}]({paper['url']})** — {authors}")
            if abstract:
                lines.append(f"  {abstract}")
            lines.append("")
    else:
        lines.append("暂无新论文")
        lines.append("")

    return "\n".join(lines)
