from datetime import UTC, datetime

from app.sources.github import (
    GitHubConnector,
    compute_repo_growth,
    normalize_github_repositories,
    parse_github_repository,
)


def test_github_connector_converts_repo_to_raw_item() -> None:
    connector = GitHubConnector(
        limit=3,
        reference_time=datetime(2026, 6, 28, tzinfo=UTC),
    )

    item = connector._repo_to_raw_item(
        {
            "id": 123,
            "full_name": "example/agent-toolkit",
            "html_url": "https://github.com/example/agent-toolkit",
            "description": "Open-source LLM agent framework",
            "language": "Python",
            "stargazers_count": 4200,
            "forks_count": 120,
            "open_issues_count": 8,
            "topics": ["llm", "agents", "rag"],
            "license": {"spdx_id": "MIT"},
            "created_at": "2026-06-18T00:00:00Z",
            "updated_at": "2026-06-25T10:30:00Z",
            "owner": {"login": "example"},
        }
    )

    assert item is not None
    assert item.external_id == "123"
    assert item.raw_title == "example/agent-toolkit: Open-source LLM agent framework"
    assert item.url == "https://github.com/example/agent-toolkit"
    assert item.raw_author == "example"
    assert item.raw_metadata["stars"] == 4200
    assert item.raw_metadata["stars_per_day"] == 420
    assert item.raw_metadata["growth_signal"] == "fast-growing"
    assert "Growth signal: fast-growing" in item.raw_text
    assert item.published_at is not None


def test_github_connector_uses_custom_source_name_for_tracked_repos() -> None:
    connector = GitHubConnector(source_name="LangChain Repo", repositories=["langchain-ai/langchain"])

    item = connector._repo_to_raw_item(
        {
            "id": 456,
            "full_name": "langchain-ai/langchain",
            "html_url": "https://github.com/langchain-ai/langchain",
            "description": "Build context-aware reasoning applications",
            "owner": {"login": "langchain-ai"},
        }
    )

    assert item is not None
    assert item.source_name == "LangChain Repo"
    assert connector.repositories == ["langchain-ai/langchain"]


def test_github_connector_skips_repo_without_required_fields() -> None:
    connector = GitHubConnector()

    assert connector._repo_to_raw_item({"full_name": "missing/url"}) is None


def test_github_connector_adds_optional_auth_header() -> None:
    connector = GitHubConnector(api_token="  ghp_test  ")

    assert connector.request_headers()["Authorization"] == "Bearer ghp_test"
    assert "Authorization" not in GitHubConnector().request_headers()


def test_compute_repo_growth_labels_repo_traction() -> None:
    signal = compute_repo_growth(
        stars=100,
        created_at=datetime(2026, 6, 18, tzinfo=UTC),
        reference_time=datetime(2026, 6, 28, tzinfo=UTC),
    )

    assert signal is not None
    assert signal.stars_per_day == 10
    assert signal.label == "gaining traction"


def test_parse_github_repository_accepts_urls_ssh_and_slugs() -> None:
    assert parse_github_repository("https://github.com/langchain-ai/langchain") == (
        "langchain-ai/langchain"
    )
    assert parse_github_repository("github.com/openai/codex.git") == "openai/codex"
    assert parse_github_repository("git@github.com:owner/repo.git") == "owner/repo"
    assert parse_github_repository("owner/repo") == "owner/repo"


def test_parse_github_repository_rejects_non_github_hosts() -> None:
    assert parse_github_repository("https://gitlab.com/owner/repo") is None
    assert parse_github_repository("owner") is None


def test_normalize_github_repositories_deduplicates_valid_values() -> None:
    assert normalize_github_repositories(
        [
            "https://github.com/openai/codex",
            "openai/codex",
            "https://gitlab.com/example/repo",
        ]
    ) == ["openai/codex"]
