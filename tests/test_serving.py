from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from xyz_okf.authorization import (
    AclBinding,
    PrincipalContext,
    PrincipalType,
    ReferencePolicyDecisionPoint,
)
from xyz_okf.profile import load_profile
from xyz_okf.release import build_release
from xyz_okf.serving import (
    AdmissionEvidence,
    ConceptNotFound,
    InMemoryBodyStore,
    ReleaseCatalog,
    ReleaseNotFound,
    ReleaseWithdrawn,
    ServingError,
    ServingService,
    WithdrawalRecord,
)

PROJECT_ROOT = Path(__file__).parents[1]
PROFILE = load_profile(PROJECT_ROOT / "profiles/xyz-bank-pilot.yaml")
BUNDLE = PROJECT_ROOT / "examples/pilot-bundle"
CREATED_AT = datetime(2026, 8, 21, tzinfo=UTC)
SERVE_AT = datetime(2026, 8, 22, tzinfo=UTC)
DIGEST = f"sha256:{'b' * 64}"
PRIOR_DIGEST = f"sha256:{'c' * 64}"
ACL_REFS = (
    "authz-policy:technology-policy-readers",
    "authz-policy:technology-runbook-readers",
    "authz-policy:technology-service-readers",
)


def _artifact(bundle: Path = BUNDLE, *, release_id: str = "2026.08.21.1"):
    return build_release(
        bundle,
        PROFILE,
        bundle_id="xyz-bank-pilot",
        release_id=release_id,
        source_commit="a" * 40,
        created_at=CREATED_AT,
    )


def _evidence() -> AdmissionEvidence:
    return AdmissionEvidence(
        signature_verified=True,
        archive_verified=True,
        policy_allowed=True,
        decision_id="opa:decision:1",
        policy_version="release-admission/1.0",
    )


def _principal(*, groups: tuple[str, ...] = ("group:all-pilot",)) -> PrincipalContext:
    return PrincipalContext(
        subject="human:pilot-user",
        principal_type=PrincipalType.HUMAN,
        groups=groups,
        clearance="INTERNAL",
    )


def _service(
    *,
    bindings: dict[str, AclBinding] | None = None,
) -> tuple[ServingService, ReleaseCatalog, InMemoryBodyStore]:
    body_store = InMemoryBodyStore()
    catalog = ReleaseCatalog(body_store)
    catalog.admit(_artifact().archive_bytes, registry_digest=DIGEST, evidence=_evidence())
    catalog.promote("protected", DIGEST)
    effective_bindings = bindings or {
        acl_ref: AclBinding(groups=("group:all-pilot",)) for acl_ref in ACL_REFS
    }
    pdp = ReferencePolicyDecisionPoint(
        effective_bindings,
        policy_version="reference-authz/1.0",
    )
    return ServingService(catalog, pdp), catalog, body_store


def test_admission_requires_verified_signature_archive_and_policy() -> None:
    catalog = ReleaseCatalog()
    evidence = _evidence().model_copy(update={"signature_verified": False})

    with pytest.raises(ServingError, match="not fully verified"):
        catalog.admit(_artifact().archive_bytes, registry_digest=DIGEST, evidence=evidence)


def test_catalog_promotes_same_digest_rolls_back_and_withdraws_immediately() -> None:
    catalog = ReleaseCatalog()
    current = _artifact()
    prior = _artifact(release_id="2026.08.20.1")
    catalog.admit(prior.archive_bytes, registry_digest=PRIOR_DIGEST, evidence=_evidence())
    catalog.admit(current.archive_bytes, registry_digest=DIGEST, evidence=_evidence())
    catalog.promote("protected", PRIOR_DIGEST)
    catalog.promote("protected", DIGEST)

    replaced = catalog.rollback("protected", PRIOR_DIGEST)
    assert replaced == DIGEST
    assert catalog.resolve("protected").registry_digest == PRIOR_DIGEST

    removed = catalog.withdraw(
        PRIOR_DIGEST,
        WithdrawalRecord(
            reason="controlled withdrawal exercise",
            actor="human:release-manager",
            at=SERVE_AT,
        ),
    )
    assert removed == ("protected",)
    with pytest.raises(ReleaseNotFound):
        catalog.resolve("protected")
    with pytest.raises(ReleaseWithdrawn):
        catalog.promote("protected", PRIOR_DIGEST)


def test_unauthorized_search_never_reads_concept_bodies() -> None:
    service, _, store = _service()

    result = service.search(
        _principal(groups=("group:not-entitled",)),
        digest_or_channel="protected",
        query="identity",
        now=SERVE_AT,
    )

    assert result.hits == ()
    assert all(
        store.read_count(DIGEST, path) == 0
        for path in (
            "policies/change-management-policy.md",
            "runbooks/identity-service-degradation.md",
            "services/enterprise-identity.md",
        )
    )


def test_unauthorized_fetch_is_indistinguishable_from_missing_and_does_not_read_body() -> None:
    service, _, store = _service()
    path = "services/enterprise-identity.md"

    with pytest.raises(ConceptNotFound, match="not found"):
        service.fetch_concept(
            _principal(groups=("group:not-entitled",)),
            digest_or_channel=DIGEST,
            concept_uid="kb:service:enterprise-identity",
            now=SERVE_AT,
        )

    assert store.read_count(DIGEST, path) == 0


def test_authorized_fetch_returns_release_context_citations_and_only_authorized_links() -> None:
    bindings = {
        "authz-policy:technology-runbook-readers": AclBinding(groups=("group:runbook",)),
        "authz-policy:technology-service-readers": AclBinding(groups=("group:service",)),
        "authz-policy:technology-policy-readers": AclBinding(groups=("group:policy",)),
    }
    service, _, store = _service(bindings=bindings)

    concept = service.fetch_concept(
        _principal(groups=("group:runbook",)),
        digest_or_channel="protected",
        concept_uid="kb:runbook:identity-service-degradation",
        now=SERVE_AT,
    )

    assert concept.release_digest == DIGEST
    assert concept.profile_id == "xyz-bank-okf"
    assert concept.citations[0].resource.startswith("https://confluence.example.invalid/")
    assert concept.links == ()
    assert concept.authorization.allowed is True
    assert store.read_count(DIGEST, "runbooks/identity-service-degradation.md") == 1


def test_authorized_search_returns_cited_snippets_and_reads_only_entitled_bodies() -> None:
    service, _, store = _service()

    result = service.search(
        _principal(),
        digest_or_channel="protected",
        query="identity",
        now=SERVE_AT,
        limit=2,
    )

    assert len(result.hits) == 2
    assert all(hit.authorization.allowed and hit.citations for hit in result.hits)
    assert all(hit.snippet for hit in result.hits)
    assert (
        sum(
            store.read_count(DIGEST, path)
            for path in (
                "policies/change-management-policy.md",
                "runbooks/identity-service-degradation.md",
                "services/enterprise-identity.md",
            )
        )
        == 3
    )


def test_freshness_filter_runs_before_body_access() -> None:
    service, _, store = _service()
    path = "services/enterprise-identity.md"

    with pytest.raises(ConceptNotFound):
        service.fetch_concept(
            _principal(),
            digest_or_channel=DIGEST,
            concept_uid="kb:service:enterprise-identity",
            now=datetime(2031, 1, 1, tzinfo=UTC),
        )
    assert store.read_count(DIGEST, path) == 0


def test_deprecated_concepts_require_explicit_opt_in(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    path = bundle / "services/enterprise-identity.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("status: stable", "status: deprecated"),
        encoding="utf-8",
    )
    artifact = _artifact(bundle)
    store = InMemoryBodyStore()
    catalog = ReleaseCatalog(store)
    catalog.admit(artifact.archive_bytes, registry_digest=DIGEST, evidence=_evidence())
    pdp = ReferencePolicyDecisionPoint(
        {acl_ref: AclBinding(groups=("group:all-pilot",)) for acl_ref in ACL_REFS},
        policy_version="reference-authz/1.0",
    )
    service = ServingService(catalog, pdp)

    with pytest.raises(ConceptNotFound):
        service.fetch_concept(
            _principal(),
            digest_or_channel=DIGEST,
            concept_uid="kb:service:enterprise-identity",
            now=SERVE_AT,
        )
    concept = service.fetch_concept(
        _principal(),
        digest_or_channel=DIGEST,
        concept_uid="kb:service:enterprise-identity",
        now=SERVE_AT,
        include_deprecated=True,
    )
    assert concept.lifecycle_status == "deprecated"


def test_withdrawal_blocks_exact_digest_retrieval_but_retains_catalog_evidence() -> None:
    service, catalog, _ = _service()
    catalog.withdraw(
        DIGEST,
        WithdrawalRecord(
            reason="security review",
            actor="human:release-manager",
            at=SERVE_AT,
        ),
    )

    with pytest.raises(ReleaseWithdrawn):
        service.fetch_concept(
            _principal(),
            digest_or_channel=DIGEST,
            concept_uid="kb:service:enterprise-identity",
            now=SERVE_AT,
        )
    assert catalog.resolve(DIGEST).withdrawal is not None


def test_release_listing_contains_only_releases_with_discoverable_concepts() -> None:
    service, _, _ = _service()

    allowed = service.list_releases(_principal(), now=SERVE_AT)
    denied = service.list_releases(_principal(groups=("group:not-entitled",)), now=SERVE_AT)

    assert len(allowed) == 1
    assert allowed[0].release_digest == DIGEST
    assert allowed[0].authorized_concept_count == 3
    assert denied == ()
