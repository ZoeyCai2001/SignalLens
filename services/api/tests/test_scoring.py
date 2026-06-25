from app.services.scoring import detect_tickers, detect_topics, is_ai_relevant, relevance_score


def test_ai_relevance_detects_topics_and_tickers() -> None:
    text = "MRVL discussed AI data center custom silicon and LLM inference demand."

    assert is_ai_relevant(text)
    assert "ai" in detect_topics(text)
    assert "llm" in detect_topics(text)
    assert detect_tickers(text) == ["MRVL"]
    assert relevance_score(text) > 0
