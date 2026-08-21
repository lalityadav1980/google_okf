from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath

import pytest
from pydantic import ValidationError

from xyz_okf.connectors import SourceRecord
from xyz_okf.renderer import RenderError, RenderMapping, render_concept


def _record(**overrides: object) -> SourceRecord:
    values: dict[str, object] = {
        "source_system": "sharepoint",
        "record_id": "sharepoint:pilot:standard-1",
        "version": "7",
        "resource": "https://sharepoint.example.invalid/standards/standard-1",
        "title": "Synthetic Engineering Standard",
        "body": "\r\n# Purpose\r\n\r\nSynthetic content.\r\n\r\n",
        "modified_at": datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
        "classification": "INTERNAL",
        "entitlement_refs": ("authz-policy:standards-readers",),
    }
    values.update(overrides)
    return SourceRecord(**values)  # type: ignore[arg-type]


def _mapping(**overrides: object) -> RenderMapping:
    values: dict[str, object] = {
        "mapping_id": "sharepoint-standard-v1",
        "mapping_version": "1.0.0",
        "output_path": "standards/synthetic-engineering-standard.md",
        "concept_uid": "kb:standard:synthetic-engineering-standard",
        "type": "Standard",
        "description": "A synthetic standard used by renderer tests.",
        "domain": "technology-governance",
        "owner": "team:technology-governance",
        "criticality": "moderate",
        "profile_version": "0.1",
        "generated_by": "xyz-okf-sharepoint-producer/0.1.0",
        "stale_after_days": 365,
        "tags": ["standard", "governance", "standard"],
        "relationships": [
            {"type": "governed-by", "target": "/policies/change-management-policy.md"},
            {"type": "applies-to", "target": "/services/enterprise-identity.md"},
        ],
    }
    values.update(overrides)
    return RenderMapping.model_validate(values)


def test_identical_input_produces_byte_identical_output() -> None:
    first = render_concept(_record(), _mapping())
    second = render_concept(_record(), _mapping())

    assert first == second
    assert first.relative_path == PurePosixPath("standards/synthetic-engineering-standard.md")
    assert len(first.sha256) == 64
    assert first.content.endswith(b"Synthetic content.\n")
    assert b"\r" not in first.content


def test_unordered_mapping_collections_are_canonicalized() -> None:
    first = render_concept(_record(), _mapping())
    second = render_concept(
        _record(),
        _mapping(
            tags=["standard", "governance"],
            relationships=list(reversed(_mapping().relationships)),
        ),
    )

    assert first.content == second.content
    assert first.text.index("- governance") < first.text.index("- standard")
    assert first.text.index("type: applies-to") < first.text.index("type: governed-by")


@pytest.mark.parametrize("entitlement_refs", [(), ("acl:a", "acl:b")])
def test_ambiguous_acl_mapping_fails_closed(entitlement_refs: tuple[str, ...]) -> None:
    with pytest.raises(RenderError, match="explicitly mapped"):
        render_concept(_record(entitlement_refs=entitlement_refs), _mapping())


def test_acl_mapping_cannot_widen_source_entitlements() -> None:
    with pytest.raises(RenderError, match="not present in source entitlements"):
        render_concept(_record(), _mapping(acl_ref="authz-policy:broader-readers"))


@pytest.mark.parametrize(
    "output_path",
    ["../escape.md", "/absolute.md", "nested\\windows.md", "index.md", "concept.txt"],
)
def test_mapping_rejects_unsafe_output_paths(output_path: str) -> None:
    with pytest.raises(ValidationError):
        _mapping(output_path=output_path)


def test_extensions_cannot_replace_lineage_or_control_fields() -> None:
    with pytest.raises(ValidationError, match="renderer-controlled fields"):
        _mapping(frontmatter_extensions={"classification": "PUBLIC"})


def test_naive_source_timestamp_is_rejected() -> None:
    with pytest.raises(RenderError, match="include a UTC offset"):
        render_concept(_record(modified_at=datetime(2026, 8, 20, 8, 0)), _mapping())
