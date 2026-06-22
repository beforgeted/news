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
