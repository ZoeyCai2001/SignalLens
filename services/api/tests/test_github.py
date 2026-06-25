from app.sources.github import GitHubConnector


def test_github_connector_converts_repo_to_raw_item() -> None:
    connector = GitHubConnector(limit=3)

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
    assert item.published_at is not None


def test_github_connector_skips_repo_without_required_fields() -> None:
    connector = GitHubConnector()

    assert connector._repo_to_raw_item({"full_name": "missing/url"}) is None
