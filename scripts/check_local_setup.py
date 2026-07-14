#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PLACEHOLDER_VALUES = {
    "",
    "replace-me",
    "your-token",
    "your-api-key",
    "your-key",
    "your-email@example.com",
    "SignalLens/0.1 your-email@example.com",
}


@dataclass(frozen=True)
class SetupCheck:
    key: str
    label: str
    status: str
    importance: str
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local SignalLens setup readiness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when warning-level checks fail.",
    )
    args = parser.parse_args()

    checks = build_checks()
    summary = build_summary(checks)

    if args.json:
        print(
            json.dumps(
                {"summary": summary, "checks": [asdict(check) for check in checks]},
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print_report(checks, summary)

    if summary["missing"] > 0:
        return 1
    if args.strict and summary["warnings"] > 0:
        return 1
    return 0


def build_checks() -> list[SetupCheck]:
    env_values = read_env_names(REPO_ROOT / ".env")
    return [
        workspace_location_check(),
        path_check("package_json", "Root package.json", "core", "package.json"),
        path_check("pnpm_lock", "pnpm lockfile", "core", "pnpm-lock.yaml"),
        path_check("web_package", "Web package.json", "core", "apps/web/package.json"),
        path_check("api_package", "API pyproject", "core", "services/api/pyproject.toml"),
        path_check("api_app", "FastAPI app entrypoint", "core", "services/api/app/main.py"),
        path_check("alembic_config", "Alembic config", "core", "services/api/alembic.ini"),
        path_check(
            "docker_compose",
            "Docker Compose file",
            "recommended",
            "infra/docker-compose.yml",
        ),
        command_check("pnpm_command", "pnpm command", "core", "pnpm"),
        command_check("docker_command", "Docker command", "recommended", "docker"),
        path_check(
            "api_venv_python",
            "API virtualenv Python",
            "core",
            "services/api/.venv/bin/python",
        ),
        path_check(
            "api_alembic",
            "API Alembic executable",
            "core",
            "services/api/.venv/bin/alembic",
        ),
        path_check(
            "api_uvicorn",
            "API Uvicorn executable",
            "core",
            "services/api/.venv/bin/uvicorn",
        ),
        path_check("root_node_modules", "Root node_modules", "core", "node_modules"),
        path_check("web_node_modules", "Web node_modules", "core", "apps/web/node_modules"),
        env_file_check(env_values),
        env_var_check(
            env_values,
            "moonshot_api_key",
            "Kimi/Moonshot API key",
            "core",
            "MOONSHOT_API_KEY",
            "Needed for paid LLM summarization, classification, and digest enrichment.",
        ),
        env_var_check(
            env_values,
            "github_token",
            "GitHub token",
            "recommended",
            "GITHUB_TOKEN",
            "Improves GitHub public API rate limits; unauthenticated fallback can still work.",
        ),
        env_var_check(
            env_values,
            "alpha_vantage_key",
            "Alpha Vantage key",
            "recommended",
            "ALPHA_VANTAGE_API_KEY",
            "Needed for live watched-stock news and price snapshots.",
        ),
        env_var_check(
            env_values,
            "sec_user_agent",
            "SEC User-Agent",
            "recommended",
            "SEC_USER_AGENT",
            "Needed for compliant SEC EDGAR requests.",
        ),
        env_var_check(
            env_values,
            "chinese_rss_feeds",
            "Chinese RSS feeds",
            "recommended",
            "CHINESE_RSS_FEEDS",
            "Needed for Chinese-language public RSS/Atom trend ingestion.",
        ),
        env_var_check(
            env_values,
            "product_hunt_token",
            "Product Hunt token",
            "optional",
            "PRODUCT_HUNT_API_TOKEN",
            "Only needed for Product Hunt launch ingestion.",
        ),
    ]


def workspace_location_check() -> SetupCheck:
    reason = cloud_sync_risk_reason(REPO_ROOT)
    if reason is None:
        return SetupCheck(
            "workspace_location",
            "Workspace location",
            "ok",
            "recommended",
            "Repository path does not look like a cloud-synced workspace.",
        )
    return SetupCheck(
        "workspace_location",
        "Workspace location",
        "warn",
        "recommended",
        (
            f"Repository is {reason}. If files show as not downloaded or disappear from local "
            "tools, move or clone SignalLens into a local-only folder such as "
            "~/Developer/SignalLens, then reinstall dependencies from the committed files."
        ),
    )


def cloud_sync_risk_reason(path: Path) -> str | None:
    normalized_parts = {part.lower() for part in path.expanduser().parts}
    if "mobile documents" in normalized_parts or "com~apple~clouddocs" in normalized_parts:
        return "inside iCloud Drive"
    if "icloud drive" in normalized_parts or "iclouddrive" in normalized_parts:
        return "inside a cloud-drive folder"

    if platform.system() == "Darwin":
        expanded = path.expanduser()
        home = Path.home()
        if is_relative_to(expanded, home / "Desktop"):
            return "under Desktop, which may be iCloud-synced on macOS"
        if is_relative_to(expanded, home / "Documents"):
            return "under Documents, which may be iCloud-synced on macOS"
    return None


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def path_check(key: str, label: str, importance: str, relative_path: str) -> SetupCheck:
    path = REPO_ROOT / relative_path
    if path.exists():
        return SetupCheck(key, label, "ok", importance, f"{relative_path} exists.")
    status = "missing" if importance == "core" else "warn"
    return SetupCheck(key, label, status, importance, f"{relative_path} is missing.")


def command_check(key: str, label: str, importance: str, command: str) -> SetupCheck:
    if shutil.which(command):
        return SetupCheck(key, label, "ok", importance, f"{command} is available on PATH.")
    status = "missing" if importance == "core" else "warn"
    if command == "pnpm":
        return SetupCheck(
            key,
            label,
            status,
            importance,
            (
                "pnpm is not available on PATH. Install Node.js/Corepack or pnpm before "
                "using the repo-root workflow commands."
            ),
        )
    return SetupCheck(key, label, status, importance, f"{command} is not available on PATH.")


def env_file_check(env_values: dict[str, str] | None) -> SetupCheck:
    if env_values is None:
        return SetupCheck(
            "env_file",
            ".env file",
            "missing",
            "core",
            "Create .env from .env.example and fill only the keys you want to enable.",
        )
    return SetupCheck(
        "env_file",
        ".env file",
        "ok",
        "core",
        ".env exists; secret values are intentionally not printed.",
    )


def env_var_check(
    env_values: dict[str, str] | None,
    key: str,
    label: str,
    importance: str,
    env_var: str,
    detail: str,
) -> SetupCheck:
    if env_values is None:
        status = "missing" if importance == "core" else "warn"
        return SetupCheck(
            key,
            label,
            status,
            importance,
            f"{env_var} cannot be checked without .env.",
        )
    if has_configured_value(env_values.get(env_var)):
        return SetupCheck(key, label, "ok", importance, f"{env_var} is configured.")
    status = "missing" if importance == "core" else "warn"
    return SetupCheck(key, label, status, importance, f"{env_var} is not configured. {detail}")


def read_env_names(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip("\"'")
    return values


def has_configured_value(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().strip("\"'")
    return normalized not in PLACEHOLDER_VALUES


def build_summary(checks: list[SetupCheck]) -> dict[str, int]:
    return {
        "total": len(checks),
        "ok": sum(1 for check in checks if check.status == "ok"),
        "warnings": sum(1 for check in checks if check.status == "warn"),
        "missing": sum(1 for check in checks if check.status == "missing"),
    }


def print_report(checks: list[SetupCheck], summary: dict[str, int]) -> None:
    print("SignalLens local setup check")
    print(
        f"{summary['ok']}/{summary['total']} ok, "
        f"{summary['warnings']} warnings, {summary['missing']} missing"
    )
    print()

    for importance in ("core", "recommended", "optional"):
        scoped_checks = [check for check in checks if check.importance == importance]
        if not scoped_checks:
            continue
        print(f"{importance.title()}:")
        for check in scoped_checks:
            marker = {"ok": "OK", "warn": "WARN", "missing": "MISS"}[check.status]
            print(f"  [{marker}] {check.label}: {check.detail}")
        print()

    print("Next useful commands:")
    print("  python3 scripts/check_local_setup.py")
    if not is_check_ok(checks, "pnpm_command"):
        print("  # Install pnpm first, then run the repo-root workflow commands below.")
    print("  pnpm infra:up")
    print("  pnpm api:migrate")
    print("  pnpm api:seed-demo")
    print("  pnpm api:dev")
    print("  pnpm web:dev")
    print("  pnpm web:dashboard-check")
    print("  pnpm verify:demo")


def is_check_ok(checks: list[SetupCheck], key: str) -> bool:
    return any(check.key == key and check.status == "ok" for check in checks)


if __name__ == "__main__":
    raise SystemExit(main())
