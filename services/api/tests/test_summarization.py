from app.services.summarization import format_short_summary, parse_summary


def test_parse_summary_extracts_expected_json() -> None:
    summary = parse_summary(
        """
        {
          "one_line_summary": "A paper evaluates AI agents.",
          "bullet_summary": ["It studies tool use.", "It reports benchmark results."],
          "why_it_matters": "Agent evaluation is a watched technical topic.",
          "technical_relevance": "Useful for agent benchmark tracking.",
          "market_relevance": "",
          "uncertainties": ["The result needs source review."]
        }
        """
    )

    assert summary.one_line_summary == "A paper evaluates AI agents."
    assert summary.bullet_summary == ["It studies tool use.", "It reports benchmark results."]
    assert summary.market_relevance is None
    assert summary.uncertainties == ["The result needs source review."]


def test_format_short_summary_includes_bullets() -> None:
    summary = parse_summary(
        """
        {
          "one_line_summary": "An AI infrastructure item appeared.",
          "bullet_summary": ["It mentions inference.", "It may matter for developers."],
          "why_it_matters": "Inference is a watched topic."
        }
        """
    )

    assert "- It mentions inference." in format_short_summary(summary)
