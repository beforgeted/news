import re
import requests
from readability import Document


def extract_content(url: str) -> dict | None:
    """Fetch a URL and extract the main article text.

    Returns: {title, text, url} or None on failure.
    """
    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "AI-Daily-Digest/2.0"}
        )
        resp.raise_for_status()

        doc = Document(resp.text)
        title = doc.title() or ""
        text = doc.summary()
        # Strip HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        if not text or len(text) < 100:
            return None

        return {"title": title.strip(), "text": text, "url": url}
    except Exception:
        return None
