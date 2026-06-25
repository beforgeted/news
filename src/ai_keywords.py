"""AI / Agent 领域关键词与相关性判定。"""

# GitHub Search API 最多 5 个 OR 运算符，用于「近月活跃」检索
GITHUB_SEARCH_TERMS = ["llm", "agent", "rag", "mcp", "transformer"]

# 相关性匹配：名称 / 描述 / topics 命中任一即视为 AI 相关
AI_MATCH_TERMS = [
    "llm", "large language model", "language model", "agent", "agentic",
    "rag", "retrieval-augmented", "retrieval augmented", "embedding", "vector",
    "mcp", "model context protocol", "harness", "langchain", "llamaindex",
    "transformer", "diffusion", "fine-tun", "finetun", "multimodal",
    "vllm", "ollama", "llama", "gpt", "claude", "gemini", "deepseek",
    "openai", "anthropic", "huggingface", "chatbot", "copilot", "autogpt",
    "prompt", "inference", "tokenizer", "reasoning", "tool calling",
    "tool-use", "sandbox agent", "ai agent", "generative ai",
]

# 非 AI 泛化仓库，即使 readme 含 agent 等词也排除
EXCLUDE_REPO_PATTERNS = [
    "awesome", "public-apis", "developer-roadmap", "free-programming",
    "system-design", "coding-interview", "leetcode", "javascript-algorithms",
    "build-your-own-x", "every-programmer", "project-based-learning",
]


def is_ai_related(name: str, description: str = "", topics: list | None = None) -> bool:
    """判断仓库是否与 AI / Agent 领域相关。"""
    full_name = (name or "").lower()
    if any(ex in full_name for ex in EXCLUDE_REPO_PATTERNS):
        return False
    text = f"{name} {description} {' '.join(topics or [])}".lower()
    return any(term in text for term in AI_MATCH_TERMS)


def build_github_active_query(since_date: str) -> str:
    """构建 GitHub 近月活跃项目搜索 query。"""
    term_query = " OR ".join(GITHUB_SEARCH_TERMS)
    return f"({term_query}) in:name,description,readme pushed:>={since_date}"
