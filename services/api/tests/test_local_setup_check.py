import importlib.util
import sys
from pathlib import Path


def load_setup_check_module():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "scripts" / "check_local_setup.py"
    spec = importlib.util.spec_from_file_location("check_local_setup", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pnpm_command_check_gives_first_run_hint(monkeypatch) -> None:
    setup_check = load_setup_check_module()
    monkeypatch.setattr(setup_check.shutil, "which", lambda command: None)

    result = setup_check.command_check("pnpm_command", "pnpm command", "core", "pnpm")

    assert result.status == "missing"
    assert result.importance == "core"
    assert "Install Node.js/Corepack or pnpm" in result.detail


def test_print_report_includes_direct_checker_fallback(capsys) -> None:
    setup_check = load_setup_check_module()
    checks = [
        setup_check.SetupCheck(
            key="pnpm_command",
            label="pnpm command",
            status="missing",
            importance="core",
            detail="pnpm is not available on PATH.",
        )
    ]

    setup_check.print_report(checks, setup_check.build_summary(checks))
    output = capsys.readouterr().out

    assert "python3 scripts/check_local_setup.py" in output
    assert "Install pnpm first" in output
    assert "pnpm verify:demo" in output


def test_cloud_sync_risk_reason_detects_icloud_drive() -> None:
    setup_check = load_setup_check_module()

    reason = setup_check.cloud_sync_risk_reason(
        Path("/Users/zoey/Library/Mobile Documents/com~apple~CloudDocs/SignalLens")
    )

    assert reason == "inside iCloud Drive"


def test_cloud_sync_risk_reason_detects_mac_desktop(monkeypatch) -> None:
    setup_check = load_setup_check_module()
    monkeypatch.setattr(setup_check.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(setup_check.Path, "home", lambda: Path("/Users/zoey"))

    reason = setup_check.cloud_sync_risk_reason(Path("/Users/zoey/Desktop/playground/SignalLens"))

    assert reason == "under Desktop, which may be iCloud-synced on macOS"


def test_cloud_sync_risk_reason_allows_local_dev_folder(monkeypatch) -> None:
    setup_check = load_setup_check_module()
    monkeypatch.setattr(setup_check.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(setup_check.Path, "home", lambda: Path("/Users/zoey"))

    reason = setup_check.cloud_sync_risk_reason(Path("/Users/zoey/Developer/SignalLens"))

    assert reason is None
