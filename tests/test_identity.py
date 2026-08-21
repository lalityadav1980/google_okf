from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from xyz_okf.connectors import SourceRecord
from xyz_okf.identity import (
    IdentityPolicy,
    SourceAnchor,
    allocate_identity,
    canonical_concept_sha256,
    canonical_source_record_sha256,
    concept_id_from_path,
)

PROJECT_ROOT = Path(__file__).parents[1]
POLICY = IdentityPolicy.model_validate(
    yaml.safe_load((PROJECT_ROOT / "profiles/xyz-bank-identity.yaml").read_text(encoding="utf-8"))
)


def _record(**overrides: object) -> SourceRecord:
    values: dict[str, object] = {
        "source_system": "sharepoint",
        "record_id": "sharepoint:pilot:standard-1",
        "version": "7",
        "resource": "https://sharepoint.example.invalid/standards/standard-1",
        "title": "Synthetic Engineering Standard",
        "body": "# Purpose\n\nSynthetic content.\n",
        "modified_at": datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
        "classification": "INTERNAL",
        "entitlement_refs": ("authz-policy:standards-readers",),
        "metadata": {"b": 2, "a": [True, "value"]},
    }
    values.update(overrides)
    return SourceRecord(**values)  # type: ignore[arg-type]


def test_uid_is_stable_across_title_type_and_path_changes() -> None:
    anchor = SourceAnchor(source_system="sharepoint", record_id="site:item:123")
    first = allocate_identity(
        anchor,
        title="Original Title",
        concept_type="Standard",
        policy=POLICY,
    )
    renamed = allocate_identity(
        anchor,
        title="Renamed Title",
        concept_type="Policy",
        retained_path=str(first.output_path),
        policy=POLICY,
    )

    assert first.concept_uid == renamed.concept_uid
    assert first.output_path == renamed.output_path
    assert first.concept_id == concept_id_from_path(first.output_path)


def test_source_fragment_allocates_distinct_concept_uid() -> None:
    first = SourceAnchor(source_system="confluence", record_id="page:123", fragment="section:a")
    second = SourceAnchor(source_system="confluence", record_id="page:123", fragment="section:b")

    assert (
        allocate_identity(
            first, title="Section", concept_type="Reference", policy=POLICY
        ).concept_uid
        != allocate_identity(
            second, title="Section", concept_type="Reference", policy=POLICY
        ).concept_uid
    )


def test_initial_path_is_ascii_bounded_and_collision_resistant() -> None:
    identity = allocate_identity(
        SourceAnchor(source_system="confluence", record_id="page:global:1"),
        title="Überblick 東京 / Enterprise Knowledge",
        concept_type="Reference",
        policy=POLICY,
    )

    assert str(identity.output_path).startswith("references/uberblick-enterprise-knowledge--")
    assert identity.output_path.suffix == ".md"
    assert len(identity.output_path.stem.rsplit("--", maxsplit=1)[1]) == 12


def test_canonical_concept_hash_ignores_yaml_order_quotes_and_line_endings() -> None:
    first = "---\ntype: Standard\ntags: [a, b]\ncount: 2\n---\n\n# Body\n"
    second = "---\ncount: 2\ntags:\n  - a\n  - b\ntype: 'Standard'\n---\r\n\r\n# Body\r\n\r\n"

    assert canonical_concept_sha256(first) == canonical_concept_sha256(second)


def test_canonical_concept_hash_changes_with_semantic_content() -> None:
    first = "---\ntype: Standard\n---\n\n# Body\n"
    second = "---\ntype: Policy\n---\n\n# Body\n"

    assert canonical_concept_sha256(first) != canonical_concept_sha256(second)


def test_canonical_source_hash_is_order_independent_but_version_sensitive() -> None:
    first = _record(entitlement_refs=("acl:b", "acl:a"), metadata={"b": 2, "a": 1})
    reordered = _record(entitlement_refs=("acl:a", "acl:b"), metadata={"a": 1, "b": 2})
    changed = _record(version="8", entitlement_refs=("acl:a", "acl:b"))

    assert canonical_source_record_sha256(first) == canonical_source_record_sha256(reordered)
    assert canonical_source_record_sha256(first) != canonical_source_record_sha256(changed)


def test_identity_and_hash_vectors_are_stable() -> None:
    identity = allocate_identity(
        SourceAnchor(source_system="sharepoint", record_id="site:item:123"),
        title="Original Title",
        concept_type="Standard",
        policy=POLICY,
    )

    assert identity.concept_uid == "urn:xyz-bank:okf:concept:e744428b-1161-5368-8868-c666d67a80f2"
    expected_digest = "46c4f9204e473ccd4d3cca934f3a8f92498885bec6822a95d729da25db2f2cd3"  # pragma: allowlist secret  # noqa: E501
    assert canonical_source_record_sha256(_record()) == expected_digest
