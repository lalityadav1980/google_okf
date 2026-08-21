from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from verity_kf.discovery import SourceDiscoveryProfile

PROJECT_ROOT = Path(__file__).parents[1]


def _example() -> dict[str, object]:
    loaded = yaml.safe_load(
        (PROJECT_ROOT / "profiles/source-discovery.example.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


def test_example_is_valid_but_explicitly_unapproved_and_contains_no_credentials() -> None:
    profile = SourceDiscoveryProfile.model_validate(_example())

    assert profile.discovery_status == "draft"
    assert profile.credentials_in_document is False
    assert any(decision.blocking for decision in profile.open_decisions)


def test_approved_discovery_cannot_hide_unknown_capabilities_or_blockers() -> None:
    values = _example()
    values["discovery_status"] = "approved"

    with pytest.raises(ValidationError, match="all capabilities evidenced"):
        SourceDiscoveryProfile.model_validate(values)


def test_discovery_requires_the_complete_versioned_capability_inventory() -> None:
    values = _example()
    capabilities = values["capabilities"]
    assert isinstance(capabilities, dict)
    del capabilities["entitlements"]

    with pytest.raises(ValidationError, match="capabilities are missing"):
        SourceDiscoveryProfile.model_validate(values)


def test_committed_discovery_schema_matches_model() -> None:
    committed = json.loads(
        (PROJECT_ROOT / "schemas/source-discovery-v1.schema.json").read_text(encoding="utf-8")
    )

    assert committed == SourceDiscoveryProfile.model_json_schema()
