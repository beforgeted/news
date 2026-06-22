from src.config import load_config
from src.collectors.github_trending import fetch_trending_repos
from src.collectors.rss_blogs import fetch_blog_posts
from src.collectors.arxiv_papers import fetch_papers

config = load_config()

print("=== GitHub Trending ===")
try:
    repos = fetch_trending_repos(config["github"])
    print(f"  Got {len(repos)} repos")
    for r in repos[:3]:
        print(f'  - {r["name"]}  stars={r["stars"]}  {r["language"]}')
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=== RSS Blogs ===")
try:
    posts = fetch_blog_posts(config["blogs"])
    print(f"  Got {len(posts)} posts")
    for p in posts[:3]:
        print(f'  - [{p["source"]}] {p["title"][:60]}')
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=== Arxiv Papers ===")
try:
    papers = fetch_papers(config["arxiv"])
    print(f"  Got {len(papers)} papers")
    for p in papers[:3]:
        print(f'  - {p["title"][:80]}')
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("All collectors working!")
