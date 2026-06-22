import re


def translate_summaries(blog_posts: list[dict]) -> list[dict]:
    """Translate blog summaries to Chinese. Falls back to original on failure."""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="auto", target="zh-CN")

        for post in blog_posts:
            text = post.get("summary", "").strip()
            if not text or _is_already_chinese(text):
                post["summary_cn"] = ""
                continue
            try:
                # Limit to 500 chars for translation speed
                result = translator.translate(text[:500])
                post["summary_cn"] = result
            except Exception:
                post["summary_cn"] = ""

    except ImportError:
        pass  # deep-translator not installed — skip translation

    return blog_posts


def _is_already_chinese(text: str) -> bool:
    """Check if text is already primarily Chinese."""
    asian = len(re.findall(r"[一-鿿]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    return asian > latin
