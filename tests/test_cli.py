from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from xyz_okf.cli import app

PROJECT_ROOT = Path(__file__).parents[1]
RUNNER = CliRunner()


def test_validate_command_returns_json_report() -> None:
    result = RUNNER.invoke(
        app,
        [
            "validate",
            str(PROJECT_ROOT / "examples/pilot-bundle"),
            "--profile",
            str(PROJECT_ROOT / "profiles/xyz-bank-pilot.yaml"),
            "--format",
            "json",
            "--now",
            "2026-08-21T00:00:00Z",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["summary"]["valid"] is True
    assert payload["documents_checked"] == 4


def test_inspect_command_lists_concept_types() -> None:
    result = RUNNER.invoke(app, ["inspect", str(PROJECT_ROOT / "examples/pilot-bundle")])

    assert result.exit_code == 0, result.output
    assert "Technology Service" in result.output
    assert "Runbook" in result.output


def test_render_command_matches_golden_output(tmp_path: Path) -> None:
    result = RUNNER.invoke(
        app,
        [
            "render",
            str(PROJECT_ROOT / "examples/rendering/source-record.yaml"),
            str(PROJECT_ROOT / "examples/rendering/mapping.yaml"),
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    rendered = tmp_path / "runbooks/identity-service-degradation-rendered.md"
    expected = (
        PROJECT_ROOT
        / "examples/rendering/expected/runbooks/identity-service-degradation-rendered.md"
    )
    assert rendered.read_bytes() == expected.read_bytes()

    checked = RUNNER.invoke(
        app,
        [
            "render",
            str(PROJECT_ROOT / "examples/rendering/source-record.yaml"),
            str(PROJECT_ROOT / "examples/rendering/mapping.yaml"),
            "--output-root",
            str(tmp_path),
            "--check",
        ],
    )
    assert checked.exit_code == 0, checked.output
    assert "MATCH" in checked.output


def test_render_command_refuses_to_replace_changed_file(tmp_path: Path) -> None:
    target = tmp_path / "runbooks/identity-service-degradation-rendered.md"
    target.parent.mkdir()
    target.write_text("user-owned change\n", encoding="utf-8")

    result = RUNNER.invoke(
        app,
        [
            "render",
            str(PROJECT_ROOT / "examples/rendering/source-record.yaml"),
            str(PROJECT_ROOT / "examples/rendering/mapping.yaml"),
            "--output-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert target.read_text(encoding="utf-8") == "user-owned change\n"


def test_render_command_rejects_symlink_escape(tmp_path: Path) -> None:
    output_root = tmp_path / "bundle"
    outside = tmp_path / "outside"
    output_root.mkdir()
    outside.mkdir()
    (output_root / "runbooks").symlink_to(outside, target_is_directory=True)

    result = RUNNER.invoke(
        app,
        [
            "render",
            str(PROJECT_ROOT / "examples/rendering/source-record.yaml"),
            str(PROJECT_ROOT / "examples/rendering/mapping.yaml"),
            "--output-root",
            str(output_root),
        ],
    )

    assert result.exit_code == 2
    assert "resolves outside" in result.output
    assert not (outside / "identity-service-degradation-rendered.md").exists()
