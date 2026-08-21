package verity.kf.release_admission

default allow := false

allow if count(deny) == 0

profile_allowed if {
	some allowed in input.policy.allowed_profiles
	allowed.profile_id == input.manifest.profile.profile_id
	allowed.profile_version == input.manifest.profile.profile_version
}

bundle_classification_allowed if {
	some allowed in input.policy.allowed_classifications
	allowed == input.manifest.bundle_classification
}

consumer_contract_allowed if {
	some allowed in input.policy.supported_consumer_contract_versions
	allowed == input.manifest.consumer_contract_version
}

signer_allowed if {
	some allowed in input.policy.allowed_signers
	allowed.identity == input.artifact.signature_identity
	allowed.issuer == input.artifact.signature_issuer
}

status_allowed(status) if {
	some allowed in input.policy.allowed_statuses
	allowed == status
}

classification_allowed(classification) if {
	some allowed in input.policy.allowed_classifications
	allowed == classification
}

concept_file(file) if is_string(file.concept_uid)

deny contains {"code": "SIGNATURE_NOT_VERIFIED", "message": "release signature was not verified"} if {
	not input.artifact.signature_verified == true
}

deny contains {"code": "ARCHIVE_NOT_VERIFIED", "message": "release archive was not verified"} if {
	not input.artifact.archive_verified == true
}

deny contains {"code": "REGISTRY_DIGEST_INVALID", "message": "registry reference is not immutable sha256"} if {
	not regex.match(`^sha256:[0-9a-f]{64}$`, input.artifact.registry_digest)
}

deny contains {"code": "ARTIFACT_TYPE_INVALID", "message": "OCI artifact type is not the approved OKF release type"} if {
	not input.artifact.artifact_type == "application/vnd.verity.kf.release.v1+tar+gzip"
}

deny contains {"code": "SIGNER_NOT_ALLOWED", "message": "signature identity or issuer is not approved"} if {
	not signer_allowed
}

deny contains {"code": "PROFILE_NOT_ALLOWED", "message": "release profile id/version is not approved"} if {
	not profile_allowed
}

deny contains {"code": "BUNDLE_CLASSIFICATION_NOT_ALLOWED", "message": "bundle classification is not allowed in this environment"} if {
	not bundle_classification_allowed
}

deny contains {"code": "CONSUMER_CONTRACT_UNSUPPORTED", "message": "release consumer contract is unsupported"} if {
	not consumer_contract_allowed
}

deny contains {"code": "PRIOR_RELEASE_REQUIRED", "message": "promoted releases require prior-release lineage"} if {
	input.policy.require_prior_release == true
	not is_string(input.manifest.prior_release_digest)
}

deny contains {"code": "CONCEPT_ACL_MISSING", "message": sprintf("concept %s has no ACL reference", [file.path])} if {
	some file in input.manifest.files
	concept_file(file)
	not is_string(file.acl_ref)
}

deny contains {"code": "CONCEPT_CLASSIFICATION_NOT_ALLOWED", "message": sprintf("concept %s classification is not allowed", [file.path])} if {
	some file in input.manifest.files
	concept_file(file)
	not classification_allowed(file.classification)
}

deny contains {"code": "CONCEPT_STATUS_NOT_ALLOWED", "message": sprintf("concept %s lifecycle status is not allowed", [file.path])} if {
	some file in input.manifest.files
	concept_file(file)
	not status_allowed(file.status)
}

deny contains {"code": "CONCEPT_SOURCE_MISSING", "message": sprintf("concept %s has no source provenance", [file.path])} if {
	some file in input.manifest.files
	concept_file(file)
	object.get(file, "source_count", 0) < 1
}

deny contains {"code": "CONCEPT_SOURCE_HASH_MISSING", "message": sprintf("concept %s has no canonical source hash", [file.path])} if {
	input.policy.require_source_hash == true
	some file in input.manifest.files
	concept_file(file)
	not regex.match(`^[0-9a-f]{64}$`, object.get(file, "source_sha256", ""))
}

deny contains {"code": "CONCEPT_VERIFICATION_REQUIRED", "message": sprintf("high-criticality concept %s is unverified", [file.path])} if {
	some file in input.manifest.files
	concept_file(file)
	file.criticality == "high"
	object.get(file, "verified_count", 0) < 1
}

deny contains {"code": "CONCEPT_FRESHNESS_MISSING", "message": sprintf("concept %s has no freshness boundary", [file.path])} if {
	some file in input.manifest.files
	concept_file(file)
	not is_string(file.stale_after)
}

deny contains {"code": "CONCEPT_STALE", "message": sprintf("concept %s is stale", [file.path])} if {
	some file in input.manifest.files
	concept_file(file)
	is_string(file.stale_after)
	time.parse_rfc3339_ns(file.stale_after) <= time.parse_rfc3339_ns(input.policy.evaluation_time)
}
