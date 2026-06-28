from app.services.preferences import (
    DEFAULT_RANKING_WEIGHTS,
    normalize_language_preferences,
    normalize_ranking_weights,
    normalize_source_preferences,
)


def test_normalize_ranking_weights_merges_partial_values_with_defaults() -> None:
    weights = normalize_ranking_weights({"importance": 0.8})

    assert weights["importance"] == 0.8
    assert weights["relevance"] == DEFAULT_RANKING_WEIGHTS.relevance


def test_normalize_source_preferences_trims_and_deduplicates_names() -> None:
    assert normalize_source_preferences([" RSS ", "rss", "", "GitHub"]) == ["RSS", "GitHub"]


def test_normalize_language_preferences_maps_aliases_and_deduplicates() -> None:
    assert normalize_language_preferences([" English ", "en-us", "ZH_CN", "cn", ""]) == [
        "en",
        "zh",
    ]
