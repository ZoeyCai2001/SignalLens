from app.services.summarization import format_detailed_summary, format_short_summary, parse_summary


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


def test_parse_summary_extracts_research_and_product_context() -> None:
    summary = parse_summary(
        """
        {
          "one_line_summary": "A launch introduces an AI coding workspace.",
          "bullet_summary": ["It targets coding workflows.", "It reports strong launch interest."],
          "why_it_matters": "Coding tools are a watched product category.",
          "research_contribution": "It contributes an agent evaluation dataset.",
          "research_method": "It compares tool-use agents on multi-step tasks.",
          "product_use_case": "It helps developers coordinate coding agents.",
          "product_audience": "software teams",
          "traction_signal": "The source reports launch upvotes.",
          "uncertainties": []
        }
        """
    )

    detailed = format_detailed_summary(summary)

    assert summary.research_contribution == "It contributes an agent evaluation dataset."
    assert summary.research_method == "It compares tool-use agents on multi-step tasks."
    assert summary.product_use_case == "It helps developers coordinate coding agents."
    assert summary.product_audience == "software teams"
    assert summary.traction_signal == "The source reports launch upvotes."
    assert "Research contribution: It contributes an agent evaluation dataset." in detailed
    assert "Product use case: It helps developers coordinate coding agents." in detailed
    assert "Traction signal: The source reports launch upvotes." in detailed


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
