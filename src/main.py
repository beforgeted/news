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
    status = "[WARN]" if failed_sources else "[OK]"
    print(f"{status} Digest sent. {total} items, {len(failed_sources)} source(s) failed.")


if __name__ == "__main__":
    main()
