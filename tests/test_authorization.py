from __future__ import annotations

from verity_kf.authorization import (
    AclBinding,
    AuthorizationReason,
    AuthorizationRequest,
    PrincipalContext,
    PrincipalType,
    ReferencePolicyDecisionPoint,
    ResourceContext,
    RetrievalAction,
)

DIGEST = f"sha256:{'a' * 64}"
ACL = "authz-policy:technology-readers"


def _principal(**overrides: object) -> PrincipalContext:
    values: dict[str, object] = {
        "subject": "human:alice",
        "principal_type": PrincipalType.HUMAN,
        "groups": ("group:technology",),
        "clearance": "INTERNAL",
    }
    values.update(overrides)
    return PrincipalContext.model_validate(values)


def _request(**resource_overrides: object) -> AuthorizationRequest:
    values: dict[str, object] = {
        "bundle_id": "pilot",
        "release_digest": DIGEST,
        "concept_uid": "kb:service:identity",
        "concept_path": "services/identity.md",
        "classification": "INTERNAL",
        "acl_ref": ACL,
        "action": RetrievalAction.READ,
    }
    principal = resource_overrides.pop("principal", _principal())
    values.update(resource_overrides)
    return AuthorizationRequest(
        principal=principal, resource=ResourceContext.model_validate(values)
    )


def _pdp(binding: AclBinding | None = None) -> ReferencePolicyDecisionPoint:
    return ReferencePolicyDecisionPoint(
        {ACL: binding or AclBinding(groups=("group:technology",))},
        policy_version="reference-authz/1.0",
    )


def test_exact_group_entitlement_allows_and_decision_is_deterministic() -> None:
    request = _request()

    first = _pdp().authorize(request)
    second = _pdp().authorize(request)

    assert first.allowed is True
    assert first.reason_codes == (AuthorizationReason.ALLOW,)
    assert first.decision_id == second.decision_id


def test_unknown_acl_denies_by_default() -> None:
    decision = _pdp().authorize(_request(acl_ref="authz-policy:unknown"))

    assert decision.allowed is False
    assert AuthorizationReason.ACL_NOT_FOUND in decision.reason_codes


def test_classification_above_clearance_denies_even_when_entitled() -> None:
    decision = _pdp().authorize(
        _request(
            classification="RESTRICTED",
            principal=_principal(clearance="CONFIDENTIAL"),
        )
    )

    assert decision.allowed is False
    assert AuthorizationReason.CLASSIFICATION_EXCEEDS_CLEARANCE in decision.reason_codes


def test_subject_and_group_matching_are_exact_not_prefix_or_substring() -> None:
    binding = AclBinding(subjects=("human:alice-admin",), groups=("group:technology-admin",))

    decision = _pdp(binding).authorize(_request())

    assert decision.allowed is False
    assert AuthorizationReason.PRINCIPAL_NOT_ENTITLED in decision.reason_codes


def test_action_and_principal_type_are_independently_enforced() -> None:
    binding = AclBinding(
        groups=("group:technology",),
        actions=(RetrievalAction.SEARCH,),
        principal_types=(PrincipalType.WORKLOAD,),
    )

    decision = _pdp(binding).authorize(_request())

    assert decision.allowed is False
    assert AuthorizationReason.ACTION_NOT_ALLOWED in decision.reason_codes
    assert AuthorizationReason.PRINCIPAL_TYPE_NOT_ALLOWED in decision.reason_codes
