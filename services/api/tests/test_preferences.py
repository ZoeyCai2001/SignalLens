from app.services.preferences import DEFAULT_RANKING_WEIGHTS, normalize_ranking_weights


def test_normalize_ranking_weights_merges_partial_values_with_defaults() -> None:
    weights = normalize_ranking_weights({"importance": 0.8})

    assert weights["importance"] == 0.8
    assert weights["relevance"] == DEFAULT_RANKING_WEIGHTS.relevance
