import sys
import os
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import load_config
from src.collectors.github_trending import fetch_trending_repos
from src.collectors.rss_blogs import fetch_blog_posts
from src.collectors.arxiv_papers import fetch_papers
from src.digest import merge, update_history, load_history
from src.render import render_html, render_markdown
from src.mailer import send_email
from src.translator import translate_summaries


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

    blogs = results.get("blogs", [])
    if blogs:
        blogs = translate_summaries(blogs)

    sections = merge(
        results.get("github", []),
        blogs,
        results.get("papers", []),
        history
    )
    sections["failed_sources"] = failed_sources

    html = render_html(sections, date_str)

    email_config = config.get("email", {})
    if email_config.get("smtp_user") and email_config.get("smtp_pass"):
        subject = f"AI Daily Digest — {date_str}"
        send_email(html, subject, email_config)
        print("[OK] Email sent.")
    else:
        print("[INFO] Email skipped (SMTP not configured).")

    output_dir = config.get("output_dir") or os.path.expandvars(
        os.environ.get("DIGEST_OUTPUT_DIR", r"C:\Users\ASher\Desktop\每日热点")
    )
    md = render_markdown(sections, date_str)
    md_path = Path(output_dir) / f"AI-Daily-Digest-{date_str}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    print(f"[OK] Markdown saved to {md_path}")

    update_history(sections)

    total = sum(len(sections.get(k, [])) for k in ("github", "blogs", "papers"))
    status = "[WARN]" if failed_sources else "[OK]"
    print(f"{status} Digest sent. {total} items, {len(failed_sources)} source(s) failed.")


if __name__ == "__main__":
    main()
