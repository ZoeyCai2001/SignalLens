from app.db.models import RawItem, Source
from app.services.feed_actions import build_public_engagement_metrics, social_signal_score_for_item
from app.services.ingestion import (
    normalize_item,
    parse_reddit_subreddits,
    reddit_query_for_source,
    reddit_subreddits_for_source,
)
from app.sources.reddit import RedditConnector, normalize_reddit_subreddits, parse_reddit_datetime


def test_reddit_payload_maps_to_raw_item() -> None:
    connector = RedditConnector(limit=1)

    item = connector._post_to_raw_item(
        {
            "id": "abc123",
            "title": "Local LLM coding agent workflow",
            "selftext": "I tested a RAG memory workflow with tool-use agents.",
            "author": "alice",
            "permalink": "/r/LocalLLaMA/comments/abc123/local_llm_coding_agent_workflow/",
            "url": "https://www.reddit.com/r/LocalLLaMA/comments/abc123/local_llm_coding_agent_workflow/",
            "subreddit": "LocalLLaMA",
            "score": 820,
            "num_comments": 144,
            "upvote_ratio": 0.94,
            "created_utc": 1_700_000_000,
            "link_flair_text": "Discussion",
        }
    )

    assert item is not None
    assert item.source_name == "Reddit AI Communities"
    assert item.external_id == "abc123"
    assert item.raw_title == "Local LLM coding agent workflow"
    assert item.raw_author == "alice"
    assert "RAG memory workflow" in item.raw_text
    assert item.raw_metadata["subreddit"] == "LocalLLaMA"
    assert item.raw_metadata["score"] == 820
    assert item.raw_metadata["comments_count"] == 144
    assert item.published_at is not None


def test_reddit_normalization_builds_discussion_summary() -> None:
    source = Source(
        id=1,
        name="Reddit AI Communities",
        type="community",
        access_method="public_json",
    )
    raw = RawItem(
        id=1,
        source_id=1,
        external_id="abc123",
        url="https://www.reddit.com/r/LocalLLaMA/comments/abc123",
        raw_title="LocalLLaMA users compare small LLM agent workflows for coding",
        raw_text="A public Reddit discussion compares local LLM coding agents and RAG memory.",
        raw_author="alice",
        raw_metadata={
            "subreddit": "LocalLLaMA",
            "score": 820,
            "comments_count": 144,
        },
        content_hash="abc",
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "technical_trend"
    assert item.subcategory == "community_discussion"
    assert item.summary_short.startswith("Reddit discussion:")
    assert item.summary_detailed is not None
    assert "Source access: public Reddit JSON metadata" in item.summary_detailed
    assert "r/LocalLLaMA, 820 upvotes, 144 comments" in item.summary_detailed

    raw.normalized_item = item
    item.raw_item = raw
    assert social_signal_score_for_item(item) > 0
    engagement_metrics = [
        (metric.key, metric.label, metric.value)
        for metric in build_public_engagement_metrics(item)
    ]
    assert engagement_metrics == [
        ("upvotes", "Upvotes", 820),
        ("comments", "Comments", 144),
    ]


def test_reddit_source_helpers_parse_subreddits_and_query_terms() -> None:
    source = Source(
        name="Reddit LocalLLaMA",
        type="reddit_community",
        access_method="public_json",
        base_url="https://www.reddit.com/r/LocalLLaMA+MachineLearning",
        terms_notes="agent, coding agent, r/artificial",
    )

    assert reddit_subreddits_for_source(source) == ["LocalLLaMA", "MachineLearning", "artificial"]
    assert reddit_query_for_source(source) == "agent OR coding agent"


def test_reddit_helpers_are_conservative() -> None:
    assert normalize_reddit_subreddits(["r/LocalLLaMA", "LocalLLaMA", "MachineLearning"]) == [
        "LocalLLaMA",
        "MachineLearning",
    ]
    assert parse_reddit_subreddits("LocalLLaMA, MachineLearning|artificial") == [
        "LocalLLaMA",
        "MachineLearning",
        "artificial",
    ]
    assert parse_reddit_subreddits("") == [
        "LocalLLaMA",
        "MachineLearning",
        "artificial",
        "singularity",
    ]
    assert parse_reddit_datetime("not-a-timestamp") is None
