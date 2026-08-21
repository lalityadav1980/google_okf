from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from xyz_okf.models import Severity
from xyz_okf.profile import load_profile
from xyz_okf.validator import validate_bundle

PROJECT_ROOT = Path(__file__).parents[1]
PROFILE = load_profile(PROJECT_ROOT / "profiles/xyz-bank-pilot.yaml")


def _frontmatter(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": "Standard",
        "title": "Example Standard",
        "description": "An illustrative standard used by automated tests.",
        "resource": "https://sources.example.invalid/standards/example",
        "sources": [
            {
                "id": "source",
                "resource": "https://sources.example.invalid/standards/example",
            }
        ],
        "generated": {
            "by": "xyz-okf-test-producer/0.1.0",
            "at": "2026-08-20T10:00:00Z",
        },
        "status": "stable",
        "stale_after": "2030-08-20T00:00:00Z",
        "xyz_profile_version": "0.1",
        "concept_uid": "kb:standard:example",
        "domain": "test-domain",
        "owner": "team:test-owner",
        "classification": "INTERNAL",
        "acl_ref": "authz-policy:test-readers",
        "criticality": "moderate",
        "source_record_id": "test:standard:example",
        "source_version": "1",
    }
    data.update(overrides)
    return data


def _write_bundle(tmp_path: Path, concepts: list[tuple[str, dict[str, Any], str]]) -> Path:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "index.md").write_text(
        '---\nokf_version: "0.2"\n---\n\n# Test Bundle\n',
        encoding="utf-8",
    )
    for relative_path, metadata, body in concepts:
        path = bundle / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = f"---\n{yaml.safe_dump(metadata, sort_keys=False)}---\n\n{body}\n"
        path.write_text(rendered, encoding="utf-8")
    return bundle


def test_reference_bundle_is_valid() -> None:
    report = validate_bundle(
        PROJECT_ROOT / "examples/pilot-bundle",
        PROFILE,
        now=datetime(2026, 8, 21, tzinfo=UTC),
    )

    assert report.is_valid
    assert report.error_count == 0
    assert report.warning_count == 0


def test_missing_required_field_is_an_error(tmp_path: Path) -> None:
    metadata = _frontmatter()
    del metadata["owner"]
    bundle = _write_bundle(tmp_path, [("standards/example.md", metadata, "# Example")])

    report = validate_bundle(bundle, PROFILE)

    assert any(
        issue.code == "PROFILE_REQUIRED_FIELD" and issue.field == "owner" for issue in report.issues
    )


def test_broken_internal_link_is_an_error(tmp_path: Path) -> None:
    bundle = _write_bundle(
        tmp_path,
        [("standards/example.md", _frontmatter(), "See [missing](/services/missing.md).")],
    )

    report = validate_bundle(bundle, PROFILE)

    assert any(issue.code == "OKF_LINK_BROKEN" for issue in report.issues)


def test_single_verification_mapping_is_accepted(tmp_path: Path) -> None:
    metadata = _frontmatter(
        criticality="high",
        verified={"by": "human:test-reviewer", "at": "2026-08-20T11:00:00Z"},
    )
    bundle = _write_bundle(tmp_path, [("standards/example.md", metadata, "# Example")])

    report = validate_bundle(bundle, PROFILE)

    assert not any(issue.code == "PROFILE_VERIFICATION_REQUIRED" for issue in report.issues)
    assert report.is_valid


def test_duplicate_concept_uid_is_an_error(tmp_path: Path) -> None:
    first = _frontmatter()
    second = _frontmatter(
        title="Another Standard",
        resource="https://sources.example.invalid/standards/another",
        source_record_id="test:standard:another",
    )
    bundle = _write_bundle(
        tmp_path,
        [
            ("standards/example.md", first, "# Example"),
            ("standards/another.md", second, "# Another"),
        ],
    )

    report = validate_bundle(bundle, PROFILE)

    duplicates = [issue for issue in report.issues if issue.code == "PROFILE_DUPLICATE_CONCEPT_UID"]
    assert len(duplicates) == 2


def test_stale_concept_is_a_warning(tmp_path: Path) -> None:
    metadata = _frontmatter(stale_after="2026-08-20T00:00:00Z")
    bundle = _write_bundle(tmp_path, [("standards/example.md", metadata, "# Example")])

    report = validate_bundle(
        bundle,
        PROFILE,
        now=datetime(2026, 8, 21, tzinfo=UTC),
    )

    issue = next(issue for issue in report.issues if issue.code == "OKF_CONCEPT_STALE")
    assert issue.severity == Severity.WARNING
    assert report.is_valid


def test_required_root_index_is_enforced(tmp_path: Path) -> None:
    bundle = _write_bundle(
        tmp_path,
        [("standards/example.md", _frontmatter(), "# Example")],
    )
    (bundle / "index.md").unlink()

    report = validate_bundle(bundle, PROFILE)

    assert any(issue.code == "OKF_ROOT_INDEX_MISSING" for issue in report.issues)


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"type": "Unknown Type"}, "PROFILE_UNKNOWN_TYPE"),
        ({"classification": "UNCONTROLLED"}, "PROFILE_ENUM_VALUE"),
        ({"criticality": "high", "verified": []}, "PROFILE_VERIFICATION_REQUIRED"),
        ({"relationships": {"type": "applies-to"}}, "PROFILE_RELATIONSHIPS_LIST"),
        ({"relationships": ["invalid"]}, "PROFILE_RELATIONSHIP_MAPPING"),
        (
            {"relationships": [{"type": "uncontrolled", "target": "https://example.invalid"}]},
            "PROFILE_RELATIONSHIP_TYPE",
        ),
        (
            {"relationships": [{"type": "applies-to", "target": ""}]},
            "PROFILE_RELATIONSHIP_TARGET",
        ),
    ],
)
def test_profile_rule_catalog_cases(
    tmp_path: Path,
    overrides: dict[str, Any],
    expected_code: str,
) -> None:
    bundle = _write_bundle(
        tmp_path,
        [("standards/example.md", _frontmatter(**overrides), "# Example")],
    )

    report = validate_bundle(bundle, PROFILE)

    assert any(issue.code == expected_code for issue in report.issues)
