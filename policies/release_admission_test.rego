package xyz.okf.release_admission_test

import data.xyz.okf.release_admission

base_input := {
	"manifest": {
		"bundle_id": "xyz-bank-pilot",
		"release_id": "2026.08.21.1",
		"consumer_contract_version": "1.0",
		"prior_release_digest": sprintf("%064d", [0]),
		"profile": {"profile_id": "xyz-bank-okf", "profile_version": "0.1"},
		"bundle_classification": "INTERNAL",
		"files": [{
			"path": "runbooks/synthetic.md",
			"concept_uid": "urn:xyz-bank:okf:concept:synthetic",
			"classification": "INTERNAL",
			"acl_ref": "authz-policy:synthetic-readers",
			"criticality": "high",
			"status": "stable",
			"stale_after": "2030-08-21T00:00:00Z",
			"source_count": 1,
			"source_sha256": sprintf("%064d", [1]),
			"verified_count": 1,
		}],
	},
	"artifact": {
		"artifact_type": "application/vnd.xyz-bank.okf.release.v1+tar+gzip",
		"archive_verified": true,
		"registry_digest": sprintf("sha256:%064d", [2]),
		"signature_verified": true,
		"signature_identity": "kms:okf-release",
		"signature_issuer": "xyz-bank-kms",
	},
	"policy": {
		"allowed_profiles": [{"profile_id": "xyz-bank-okf", "profile_version": "0.1"}],
		"allowed_classifications": ["PUBLIC", "INTERNAL"],
		"allowed_signers": [{"identity": "kms:okf-release", "issuer": "xyz-bank-kms"}],
		"allowed_statuses": ["stable"],
		"supported_consumer_contract_versions": ["1.0"],
		"require_prior_release": true,
		"require_source_hash": true,
		"evaluation_time": "2026-08-21T00:00:00Z",
	},
}

input_with_artifact(changes) := result if {
	artifact := object.union(base_input.artifact, changes)
	result := object.union(base_input, {"artifact": artifact})
}

input_with_manifest(changes) := result if {
	manifest := object.union(base_input.manifest, changes)
	result := object.union(base_input, {"manifest": manifest})
}

input_with_policy(changes) := result if {
	policy := object.union(base_input.policy, changes)
	result := object.union(base_input, {"policy": policy})
}

input_with_file(changes) := result if {
	file := object.union(base_input.manifest.files[0], changes)
	manifest := object.union(base_input.manifest, {"files": [file]})
	result := object.union(base_input, {"manifest": manifest})
}

has_code(decisions, code) if {
	some decision in decisions
	decision.code == code
}

test_complete_release_is_allowed if {
	release_admission.allow with input as base_input
}

test_unsigned_release_is_denied if {
	candidate := input_with_artifact({"signature_verified": false})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "SIGNATURE_NOT_VERIFIED")
}

test_unverified_archive_is_denied if {
	candidate := input_with_artifact({"archive_verified": false})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "ARCHIVE_NOT_VERIFIED")
}

test_wrong_artifact_type_is_denied if {
	candidate := input_with_artifact({"artifact_type": "application/octet-stream"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "ARTIFACT_TYPE_INVALID")
}

test_mutable_registry_reference_is_denied if {
	candidate := input_with_artifact({"registry_digest": "candidate"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "REGISTRY_DIGEST_INVALID")
}

test_unapproved_signer_is_denied if {
	candidate := input_with_artifact({"signature_identity": "kms:unapproved"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "SIGNER_NOT_ALLOWED")
}

test_unapproved_profile_is_denied if {
	candidate := input_with_manifest({"profile": {"profile_id": "unknown", "profile_version": "1"}})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "PROFILE_NOT_ALLOWED")
}

test_unapproved_classification_is_denied if {
	candidate := input_with_manifest({"bundle_classification": "RESTRICTED"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "BUNDLE_CLASSIFICATION_NOT_ALLOWED")
}

test_unsupported_consumer_contract_is_denied if {
	candidate := input_with_manifest({"consumer_contract_version": "2.0"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONSUMER_CONTRACT_UNSUPPORTED")
}

test_missing_prior_release_is_denied if {
	candidate := input_with_manifest({"prior_release_digest": null})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "PRIOR_RELEASE_REQUIRED")
}

test_missing_source_is_denied if {
	candidate := input_with_file({"source_count": 0})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_SOURCE_MISSING")
}

test_missing_acl_is_denied if {
	candidate := input_with_file({"acl_ref": null})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_ACL_MISSING")
}

test_concept_classification_is_denied_if_environment_does_not_allow_it if {
	candidate := input_with_file({"classification": "RESTRICTED"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_CLASSIFICATION_NOT_ALLOWED")
}

test_missing_source_hash_is_denied if {
	candidate := input_with_file({"source_sha256": null})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_SOURCE_HASH_MISSING")
}

test_unverified_high_criticality_concept_is_denied if {
	candidate := input_with_file({"verified_count": 0})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_VERIFICATION_REQUIRED")
}

test_stale_concept_is_denied if {
	candidate := input_with_file({"stale_after": "2026-08-20T00:00:00Z"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_STALE")
}

test_missing_freshness_is_denied if {
	candidate := input_with_file({"stale_after": null})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_FRESHNESS_MISSING")
}

test_moderate_concept_does_not_require_verification if {
	candidate := input_with_file({"criticality": "moderate", "verified_count": 0})
	release_admission.allow with input as candidate
}

test_policy_can_temporarily_allow_missing_source_hash if {
	candidate_policy := object.union(base_input.policy, {"require_source_hash": false})
	file := object.union(base_input.manifest.files[0], {"source_sha256": null})
	manifest := object.union(base_input.manifest, {"files": [file]})
	candidate := object.union(base_input, {"manifest": manifest, "policy": candidate_policy})
	release_admission.allow with input as candidate
}

test_draft_concept_is_denied if {
	candidate := input_with_file({"status": "draft"})
	decisions := release_admission.deny with input as candidate
	has_code(decisions, "CONCEPT_STATUS_NOT_ALLOWED")
}

test_policy_can_allow_release_without_prior_lineage_for_first_release if {
	candidate_policy := object.union(base_input.policy, {"require_prior_release": false})
	manifest := object.union(base_input.manifest, {"prior_release_digest": null})
	candidate := object.union(base_input, {"manifest": manifest, "policy": candidate_policy})
	release_admission.allow with input as candidate
}
