from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient

from xyz_okf.api import create_app
from xyz_okf.authorization import (
    AclBinding,
    PrincipalContext,
    PrincipalType,
    ReferencePolicyDecisionPoint,
)
from xyz_okf.profile import load_profile
from xyz_okf.release import build_release
from xyz_okf.serving import AdmissionEvidence, ReleaseCatalog, ServingService, WithdrawalRecord

PROJECT_ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 8, 22, tzinfo=UTC)
DIGEST = f"sha256:{'d' * 64}"
TOKEN = {"Authorization": "Bearer synthetic-test-token"}
ACL_REFS = (
    "authz-policy:technology-policy-readers",
    "authz-policy:technology-runbook-readers",
    "authz-policy:technology-service-readers",
)


def _principal(groups: tuple[str, ...]) -> PrincipalContext:
    return PrincipalContext(
        subject="human:api-test",
        principal_type=PrincipalType.HUMAN,
        groups=groups,
        clearance="INTERNAL",
    )


def _client(*, groups: tuple[str, ...] = ("group:pilot",)) -> tuple[TestClient, ReleaseCatalog]:
    artifact = build_release(
        PROJECT_ROOT / "examples/pilot-bundle",
        load_profile(PROJECT_ROOT / "profiles/xyz-bank-pilot.yaml"),
        bundle_id="xyz-bank-pilot",
        release_id="2026.08.21.1",
        source_commit="a" * 40,
        created_at=datetime(2026, 8, 21, tzinfo=UTC),
    )
    catalog = ReleaseCatalog()
    catalog.admit(
        artifact.archive_bytes,
        registry_digest=DIGEST,
        evidence=AdmissionEvidence(
            signature_verified=True,
            archive_verified=True,
            policy_allowed=True,
            decision_id="opa:test",
            policy_version="release-admission/1.0",
        ),
    )
    catalog.promote("protected", DIGEST)
    pdp = ReferencePolicyDecisionPoint(
        {acl_ref: AclBinding(groups=("group:pilot",)) for acl_ref in ACL_REFS},
        policy_version="reference-authz/1.0",
    )
    service = ServingService(catalog, pdp)

    def resolve_principal(_request: Request) -> PrincipalContext:
        return _principal(groups)

    app = create_app(
        service,
        resolve_principal,
        open_id_connect_url="https://identity.example.invalid/.well-known/openid-configuration",
        clock=lambda: NOW,
    )
    return TestClient(app), catalog


def test_api_requires_bearer_identity_context() -> None:
    client, _ = _client()

    response = client.get("/v1/releases")

    assert response.status_code in {401, 403}


def test_list_search_and_fetch_are_release_aware_and_no_store() -> None:
    client, _ = _client()

    releases = client.get("/v1/releases", headers=TOKEN)
    search = client.post(
        "/v1/search",
        headers=TOKEN,
        json={
            "release": "protected",
            "query": "identity",
            "limit": 1,
        },
    )
    concept = client.get(
        "/v1/releases/protected/concepts/kb:service:enterprise-identity",
        headers=TOKEN,
    )

    assert releases.status_code == 200
    assert releases.headers["cache-control"] == "no-store"
    assert releases.json()[0]["release_digest"] == DIGEST
    assert search.status_code == 200
    assert search.json()["hits"][0]["citations"]
    assert concept.status_code == 200
    assert concept.json()["release_digest"] == DIGEST
    assert concept.json()["exact_sha256"]


def test_denied_and_unknown_concepts_share_the_same_api_response() -> None:
    denied, _ = _client(groups=("group:not-entitled",))

    existing = denied.get(
        "/v1/releases/protected/concepts/kb:service:enterprise-identity", headers=TOKEN
    )
    missing = denied.get("/v1/releases/protected/concepts/kb:service:missing", headers=TOKEN)

    assert existing.status_code == missing.status_code == 404
    assert existing.json() == missing.json() == {"detail": "resource not found"}


def test_withdrawn_release_returns_gone_for_exact_digest() -> None:
    client, catalog = _client()
    catalog.withdraw(
        DIGEST,
        WithdrawalRecord(
            reason="controlled withdrawal",
            actor="human:release-manager",
            at=NOW,
        ),
    )

    response = client.get(
        f"/v1/releases/{DIGEST}/concepts/kb:service:enterprise-identity", headers=TOKEN
    )

    assert response.status_code == 410
    assert response.json() == {"detail": "release is withdrawn"}


def test_openapi_contract_is_committed_and_declares_oidc_security() -> None:
    client, _ = _client()
    generated = client.get("/openapi.json").json()
    committed = json.loads(
        (PROJECT_ROOT / "schemas/serving-api-v1.openapi.json").read_text(encoding="utf-8")
    )

    assert generated == committed
    scheme = generated["components"]["securitySchemes"]["EnterpriseOIDC"]
    assert scheme["type"] == "openIdConnect"
