from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from xyz_okf.issue_catalog import load_issue_catalog
from xyz_okf.issues import IssueCode
from xyz_okf.profile import load_profile
from xyz_okf.validator import validate_bundle

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "tests/fixtures/conformance"
NOW = datetime(2026, 8, 21, tzinfo=UTC)


def _manifest() -> dict[str, Any]:
    loaded = yaml.safe_load((FIXTURE_ROOT / "cases.yaml").read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.parametrize("case", _manifest()["cases"], ids=lambda case: str(case["id"]))
def test_conformance_case(case: dict[str, Any]) -> None:
    profile = load_profile(PROJECT_ROOT / "profiles" / str(case["profile"]))
    report = validate_bundle(FIXTURE_ROOT / str(case["bundle"]), profile, now=NOW)

    actual_codes = sorted({issue.code.value for issue in report.issues})
    assert actual_codes == sorted(case["expected_codes"])
    assert report.is_valid is case["expected_valid"]


def test_invalid_utf8_has_stable_issue_code(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "concept.md").write_bytes(b"---\ntype: Reference\n---\n\xff")
    report = validate_bundle(
        bundle,
        load_profile(PROJECT_ROOT / "profiles/okf-v02-base.yaml"),
        now=NOW,
    )

    assert {issue.code for issue in report.issues} == {IssueCode.OKF_UTF8}


def test_issue_catalog_is_complete_unique_and_has_test_evidence() -> None:
    catalog = load_issue_catalog(PROJECT_ROOT / "profiles/validation-issues.yaml")
    catalog_codes = [entry.code for entry in catalog.entries]
    assert len(catalog_codes) == len(set(catalog_codes))
    assert set(catalog_codes) == set(IssueCode)

    conformance_references = {f"conformance:{case['id']}" for case in _manifest()["cases"]}
    unit_references = {
        "unit:utf8-invalid",
        "unit:root-index-missing",
        "unit:stale-concept",
        "unit:profile-required-field",
        "unit:profile-unknown-type",
        "unit:profile-enum-value",
        "unit:profile-verification-required",
        "unit:profile-relationships-list",
        "unit:profile-relationship-mapping",
        "unit:profile-relationship-type",
        "unit:profile-relationship-target",
        "unit:duplicate-concept-uid",
    }
    known_references = conformance_references | unit_references
    for entry in catalog.entries:
        assert set(entry.test_references) <= known_references


def test_fixture_manifest_has_unique_ids_and_existing_inputs() -> None:
    cases = _manifest()["cases"]
    case_ids = [case["id"] for case in cases]
    assert len(case_ids) == len(set(case_ids))
    for case in cases:
        assert (FIXTURE_ROOT / case["bundle"]).is_dir()
        assert (PROJECT_ROOT / "profiles" / case["profile"]).is_file()
