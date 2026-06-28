from app.services.scoring import (
    company_names_for_tickers,
    detect_companies,
    detect_products,
    detect_tickers,
    detect_topics,
    is_ai_relevant,
    relevance_score,
)


def test_ai_relevance_detects_topics_and_tickers() -> None:
    text = "MRVL discussed AI data center custom silicon and LLM inference demand."

    assert is_ai_relevant(text)
    assert "ai" in detect_topics(text)
    assert "llm" in detect_topics(text)
    assert detect_tickers(text) == ["MRVL"]
    assert relevance_score(text) > 0


def test_detect_tickers_maps_company_aliases() -> None:
    text = "NVIDIA and Broadcom are tied to AI data center infrastructure demand."

    assert detect_tickers(text) == ["AVGO", "NVDA"]


def test_detect_companies_maps_public_and_private_ai_companies() -> None:
    text = "OpenAI, Anthropic, and Marvell discussed AI agent infrastructure."

    assert detect_companies(text) == ["Anthropic", "Marvell Technology", "OpenAI"]


def test_company_names_for_tickers_uses_canonical_names_with_fallback() -> None:
    assert company_names_for_tickers(["MRVL", "UNKNOWN"]) == ["Marvell Technology", "UNKNOWN"]


def test_detect_products_maps_known_ai_product_names() -> None:
    text = "ChatGPT, Claude, Cursor, and GitHub Copilot shipped agent updates."

    assert detect_products(text) == ["ChatGPT", "Claude", "Copilot", "Cursor"]


def test_ai_relevance_detects_chinese_ai_terms() -> None:
    text = "国产大模型和智能体产品正在推动企业人工智能应用。"

    assert is_ai_relevant(text)
    assert "大模型" in detect_topics(text)
    assert "智能体" in detect_topics(text)
