import re

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
    "ai产品",
    "人工智能",
    "大模型",
    "多模态",
    "智能体",
    "生成式ai",
    "算力",
    "芯片",
    "开源模型",
}

WATCHED_TICKERS = {
    "MU",
    "MRVL",
    "SNDK",
    "NVDA",
    "AMD",
    "AVGO",
    "TSM",
    "ASML",
    "AMAT",
    "LRCX",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "ORCL",
    "ARM",
    "SMCI",
    "DELL",
    "HPE",
}

TICKER_ALIASES = {
    "MU": ["Micron", "Micron Technology"],
    "MRVL": ["Marvell", "Marvell Technology"],
    "SNDK": ["SanDisk"],
    "NVDA": ["NVIDIA"],
    "AMD": ["Advanced Micro Devices"],
    "AVGO": ["Broadcom"],
    "TSM": ["TSMC", "Taiwan Semiconductor"],
    "ASML": ["ASML"],
    "AMAT": ["Applied Materials"],
    "LRCX": ["Lam Research"],
    "MSFT": ["Microsoft"],
    "GOOGL": ["Google", "Alphabet"],
    "AMZN": ["Amazon", "AWS"],
    "META": ["Meta", "Facebook"],
    "ORCL": ["Oracle"],
    "ARM": ["Arm Holdings"],
    "SMCI": ["Super Micro", "Supermicro"],
    "DELL": ["Dell"],
    "HPE": ["Hewlett Packard Enterprise", "HPE"],
}

TICKER_COMPANY_NAMES = {
    "MU": "Micron Technology",
    "MRVL": "Marvell Technology",
    "SNDK": "SanDisk",
    "NVDA": "NVIDIA",
    "AMD": "AMD",
    "AVGO": "Broadcom",
    "TSM": "TSMC",
    "ASML": "ASML",
    "AMAT": "Applied Materials",
    "LRCX": "Lam Research",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "META": "Meta",
    "ORCL": "Oracle",
    "ARM": "Arm Holdings",
    "SMCI": "Supermicro",
    "DELL": "Dell",
    "HPE": "Hewlett Packard Enterprise",
}

PRIVATE_AI_COMPANY_ALIASES = {
    "OpenAI": ["OpenAI", "ChatGPT", "Sora"],
    "Anthropic": ["Anthropic", "Claude"],
    "Google DeepMind": ["Google DeepMind", "DeepMind"],
    "Hugging Face": ["Hugging Face"],
    "Perplexity": ["Perplexity"],
    "Cursor": ["Cursor"],
    "DeepSeek": ["DeepSeek"],
    "Mistral AI": ["Mistral AI", "Mistral"],
}

AI_PRODUCT_ALIASES = {
    "ChatGPT": ["ChatGPT"],
    "Claude": ["Claude"],
    "Cursor": ["Cursor"],
    "Perplexity": ["Perplexity"],
    "Midjourney": ["Midjourney"],
    "Runway": ["Runway"],
    "Gemini": ["Gemini"],
    "Copilot": ["Copilot", "GitHub Copilot"],
    "Sora": ["Sora"],
    "Devin": ["Devin"],
    "DeepSeek": ["DeepSeek"],
    "Hugging Face Spaces": ["Hugging Face Space", "Hugging Face Spaces"],
}

PRODUCT_USE_CASE_PATTERNS = [
    (
        "product_coding",
        r"\b(coding|code|developer|developers|devtool|ide|repository|github|pull request|"
        r"programming|software engineer|debug|agentic coding)\b",
    ),
    (
        "product_media",
        r"\b(photo|image|video|audio|voice|music|design|editing|creator|media|sora|"
        r"midjourney|runway)\b",
    ),
    ("product_search", r"\b(search|browser|answer engine|research assistant|perplexity)\b"),
    (
        "product_education",
        r"\b(education|learning|tutor|student|teacher|course|classroom|study)\b",
    ),
    (
        "product_business",
        r"\b(business|enterprise|sales|support|customer|crm|operations|product teams?|"
        r"product managers?|pm|finance|legal|hr)\b",
    ),
    (
        "product_productivity",
        r"\b(productivity|workflow|note|notes|calendar|email|docs?|spreadsheet|task|"
        r"meeting|assistant|automation)\b",
    ),
    ("product_entertainment", r"\b(game|gaming|entertainment|social companion|roleplay)\b"),
]


def detect_topics(text: str) -> list[str]:
    normalized = text.lower()
    return sorted({keyword for keyword in AI_KEYWORDS if keyword in normalized})


def detect_tickers(text: str) -> list[str]:
    normalized = text.lower()
    detected = {ticker for ticker in WATCHED_TICKERS if has_ticker_token(text, ticker)}
    for ticker, aliases in TICKER_ALIASES.items():
        if any(alias.lower() in normalized for alias in aliases):
            detected.add(ticker)
    return sorted(detected)


def has_ticker_token(text: str, ticker: str) -> bool:
    direct_pattern = rf"(?<![A-Za-z0-9]){re.escape(ticker)}(?![A-Za-z0-9])"
    cashtag_pattern = rf"(?<![A-Za-z0-9])\${re.escape(ticker)}(?![A-Za-z0-9])"
    exchange_pattern = (
        rf"\b(?:NASDAQ|NYSE|NYSEARCA|NYSEAMERICAN|AMEX|OTC)\s*[:/]\s*"
        rf"\$?{re.escape(ticker)}(?![A-Za-z0-9])"
    )
    return bool(
        re.search(direct_pattern, text)
        or re.search(cashtag_pattern, text, flags=re.IGNORECASE)
        or re.search(exchange_pattern, text, flags=re.IGNORECASE)
    )


def detect_companies(text: str) -> list[str]:
    normalized = text.lower()
    detected = set(company_names_for_tickers(detect_tickers(text)))
    for company, aliases in PRIVATE_AI_COMPANY_ALIASES.items():
        if any(alias.lower() in normalized for alias in aliases):
            detected.add(company)
    return sorted(detected)


def company_names_for_tickers(tickers: list[str]) -> list[str]:
    return sorted({TICKER_COMPANY_NAMES.get(ticker, ticker) for ticker in tickers})


def detect_products(text: str) -> list[str]:
    normalized = text.lower()
    detected = {
        product
        for product, aliases in AI_PRODUCT_ALIASES.items()
        if any(alias.lower() in normalized for alias in aliases)
    }
    return sorted(detected)


def infer_product_use_case(text: str) -> str:
    normalized = text.lower()
    for use_case, pattern in PRODUCT_USE_CASE_PATTERNS:
        if re.search(pattern, normalized):
            return use_case
    return "product_general"


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
