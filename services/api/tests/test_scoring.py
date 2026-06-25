from app.services.scoring import detect_tickers, detect_topics, is_ai_relevant, relevance_score


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


def test_ai_relevance_detects_chinese_ai_terms() -> None:
    text = "国产大模型和智能体产品正在推动企业人工智能应用。"

    assert is_ai_relevant(text)
    assert "大模型" in detect_topics(text)
    assert "智能体" in detect_topics(text)
