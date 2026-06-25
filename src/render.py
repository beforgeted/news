from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _render_repo_lines(repos: list[dict], show_stars_gained: bool = False) -> list[str]:
    lines = []
    for repo in repos:
        name_cn = repo.get("name_cn", "")
        topics = " ".join(f"`{t}`" for t in repo.get("topics", [])[:5])
        title_display = f"{name_cn}（{repo['name']}）" if name_cn else repo["name"]
        meta = f"⭐{repo['stars']}  {repo['language']}"
        if show_stars_gained and repo.get("stars_gained"):
            meta = f"📈 +{repo['stars_gained']} 本周  ·  {meta}"
        lines.append(f"- **[{title_display}]({repo['url']})**  {meta}")
        summary = repo.get("summary_cn", "")
        if summary:
            lines.append(f"  {summary}")
        if topics:
            lines.append(f"  {topics}")
        lines.append("")
    return lines


def render_html(sections: dict, date_str: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("email.html")
    return template.render(
        date=date_str,
        highlight=sections.get("highlight", ""),
        github_trending=sections.get("github_trending", []),
        github_active=sections.get("github_active", []),
        blogs=sections.get("blogs", []),
        papers=sections.get("papers", []),
        failed_sources=sections.get("failed_sources", [])
    )


def render_markdown(sections: dict, date_str: str) -> str:
    lines = [f"# AI 每日摘要 — {date_str}", ""]

    highlight = sections.get("highlight", "")
    if highlight:
        lines.append("> 📋 **今日导读**")
        for line in highlight.strip().splitlines():
            lines.append(f"> {line.strip()}")
        lines.append("")

    failed = sections.get("failed_sources", [])
    if failed:
        lines.append(f"> ⚠ 采集失败: {', '.join(failed)}")
        lines.append("")

    lines.append("## 📈 GitHub 近一周涨星 Top 5")
    lines.append("")
    github_trending = sections.get("github_trending", [])
    if github_trending:
        lines.extend(_render_repo_lines(github_trending, show_stars_gained=True))
    else:
        lines.append("暂无涨星项目")
        lines.append("")

    lines.append("## 🔥 GitHub 近月活跃高星 Top 5")
    lines.append("")
    github_active = sections.get("github_active", [])
    if github_active:
        lines.extend(_render_repo_lines(github_active))
    else:
        lines.append("暂无活跃项目")
        lines.append("")

    lines.append("## 📝 AI 公司动态")
    lines.append("")
    blogs = sections.get("blogs", [])
    if blogs:
        for post in blogs:
            title_cn = post.get("title_cn", "")
            summary_cn = post.get("summary_cn", "")
            title_display = title_cn if title_cn else post["title"]
            lines.append(f"- **[{title_display}]({post['url']})** — {post['source']} ({post['date']})")
            if summary_cn:
                lines.append(f"  {summary_cn}")
            lines.append("")
    else:
        lines.append("暂无新动态")
        lines.append("")

    lines.append("## 📄 Arxiv 论文速递")
    lines.append("")
    papers = sections.get("papers", [])
    if papers:
        for paper in papers:
            title_cn = paper.get("title_cn", "")
            authors = ", ".join(paper.get("authors", []))
            summary = paper.get("summary_cn") or paper.get("abstract", "")
            title_display = f"{title_cn}（{paper['title']}）" if title_cn else paper["title"]
            lines.append(f"- **[{title_display}]({paper['url']})** — {authors}")
            if summary:
                lines.append(f"  {summary}")
            lines.append("")
    else:
        lines.append("暂无新论文")
        lines.append("")

    return "\n".join(lines)
