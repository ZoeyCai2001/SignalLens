AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "agent",
    "agents",
    "anthropic",
    "benchmark",
    "chatgpt",
    "claude",
    "coding agent",
    "deepseek",
    "diffusion",
    "embedding",
    "gemini",
    "gpu",
    "hugging face",
    "inference",
    "llama",
    "llm",
    "machine learning",
    "mcp",
    "model",
    "multimodal",
    "nvidia",
    "openai",
    "rag",
    "reasoning",
    "retrieval",
    "transformer",
}

WATCHED_TICKERS = {"MU", "MRVL", "SNDK", "NVDA", "AMD", "AVGO", "TSM", "ASML", "MSFT", "GOOGL"}


def detect_topics(text: str) -> list[str]:
    normalized = text.lower()
    return sorted({keyword for keyword in AI_KEYWORDS if keyword in normalized})


def detect_tickers(text: str) -> list[str]:
    upper_text = f" {text.upper()} "
    return sorted({ticker for ticker in WATCHED_TICKERS if f" {ticker} " in upper_text})


def is_ai_relevant(text: str) -> bool:
    return bool(detect_topics(text))


def relevance_score(text: str) -> float:
    topics = detect_topics(text)
    tickers = detect_tickers(text)
    score = min(1.0, 0.15 * len(topics) + 0.2 * len(tickers))
    return round(score, 3)


def importance_score(source_quality_score: float, text: str) -> float:
    topics = detect_topics(text)
    stock_bonus = 0.15 if detect_tickers(text) else 0
    score = min(1.0, 0.45 * source_quality_score + 0.08 * len(topics) + stock_bonus)
    return round(score, 3)
