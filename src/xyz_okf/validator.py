from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from pydantic import ValidationError

from xyz_okf.issues import IssueCode
from xyz_okf.models import (
    ConceptFrontmatter,
    ProfileDefinition,
    Severity,
    ValidationIssue,
    ValidationReport,
)
from xyz_okf.parser import (
    DocumentParseError,
    ParsedDocument,
    parse_concept,
    parse_reserved_body,
)

_RESERVED = {"index.md", "log.md"}


def _add_issue(
    report: ValidationReport,
    severity: Severity,
    code: IssueCode,
    message: str,
    path: Path,
    bundle_root: Path,
    *,
    concept_id: str | None = None,
    field: str | None = None,
) -> None:
    report.issues.append(
        ValidationIssue(
            severity=severity,
            code=code,
            message=message,
            path=path.relative_to(bundle_root).as_posix(),
            concept_id=concept_id,
            field=field,
        )
    )


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _validate_profile_fields(
    document: ParsedDocument,
    concept: ConceptFrontmatter | None,
    profile: ProfileDefinition,
    report: ValidationReport,
    bundle_root: Path,
) -> tuple[str | None, tuple[str, ...]]:
    metadata = document.metadata

    for field in profile.required_fields:
        if not _present(metadata.get(field)):
            _add_issue(
                report,
                Severity.ERROR,
                IssueCode.PROFILE_REQUIRED_FIELD,
                f"required profile field '{field}' is missing or empty",
                document.path,
                bundle_root,
                concept_id=document.concept_id,
                field=field,
            )

    type_name = metadata.get("type")
    if (
        isinstance(type_name, str)
        and profile.allowed_types
        and type_name not in profile.allowed_types
    ):
        _add_issue(
            report,
            profile.policy.unknown_types,
            IssueCode.PROFILE_UNKNOWN_TYPE,
            f"type '{type_name}' is not in the controlled profile vocabulary",
            document.path,
            bundle_root,
            concept_id=document.concept_id,
            field="type",
        )

    for field, allowed in profile.enum_fields.items():
        value = metadata.get(field)
        if _present(value) and value not in allowed:
            _add_issue(
                report,
                Severity.ERROR,
                IssueCode.PROFILE_ENUM_VALUE,
                f"field '{field}' value '{value}' is not one of {allowed}",
                document.path,
                bundle_root,
                concept_id=document.concept_id,
                field=field,
            )

    criticality = metadata.get("criticality")
    if criticality in profile.policy.verified_required_for_criticality and (
        concept is None or not concept.verified
    ):
        _add_issue(
            report,
            Severity.ERROR,
            IssueCode.PROFILE_VERIFICATION_REQUIRED,
            f"criticality '{criticality}' requires independent verification",
            document.path,
            bundle_root,
            concept_id=document.concept_id,
            field="verified",
        )

    relationship_targets: list[str] = []
    relationships = metadata.get("relationships", [])
    if relationships and not isinstance(relationships, list):
        _add_issue(
            report,
            Severity.ERROR,
            IssueCode.PROFILE_RELATIONSHIPS_LIST,
            "relationships must be a YAML list",
            document.path,
            bundle_root,
            concept_id=document.concept_id,
            field="relationships",
        )
    elif isinstance(relationships, list):
        for index, relationship in enumerate(relationships):
            if not isinstance(relationship, dict):
                _add_issue(
                    report,
                    Severity.ERROR,
                    IssueCode.PROFILE_RELATIONSHIP_MAPPING,
                    f"relationship at index {index} must be a mapping",
                    document.path,
                    bundle_root,
                    concept_id=document.concept_id,
                    field=f"relationships.{index}",
                )
                continue
            relationship_type = relationship.get("type")
            target = relationship.get("target")
            if relationship_type not in profile.allowed_relationship_types:
                _add_issue(
                    report,
                    Severity.ERROR,
                    IssueCode.PROFILE_RELATIONSHIP_TYPE,
                    f"relationship type '{relationship_type}' is not approved",
                    document.path,
                    bundle_root,
                    concept_id=document.concept_id,
                    field=f"relationships.{index}.type",
                )
            if not isinstance(target, str) or not target.strip():
                _add_issue(
                    report,
                    Severity.ERROR,
                    IssueCode.PROFILE_RELATIONSHIP_TARGET,
                    "relationship target must be a non-empty path or URI",
                    document.path,
                    bundle_root,
                    concept_id=document.concept_id,
                    field=f"relationships.{index}.target",
                )
            else:
                relationship_targets.append(target)

    concept_uid = metadata.get("concept_uid")
    return concept_uid if isinstance(concept_uid, str) else None, tuple(relationship_targets)


def _validate_link(
    source_path: Path,
    source_id: str | None,
    href: str,
    profile: ProfileDefinition,
    report: ValidationReport,
    bundle_root: Path,
) -> None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return

    link_path = unquote(parsed.path)
    candidate = (
        bundle_root / link_path.lstrip("/")
        if link_path.startswith("/")
        else source_path.parent / link_path
    )
    resolved = candidate.resolve()

    try:
        resolved.relative_to(bundle_root)
    except ValueError:
        _add_issue(
            report,
            profile.policy.escaped_bundle_links,
            IssueCode.OKF_LINK_ESCAPES_BUNDLE,
            f"link target '{href}' resolves outside the bundle",
            source_path,
            bundle_root,
            concept_id=source_id,
        )
        return

    if not resolved.exists():
        _add_issue(
            report,
            profile.policy.broken_internal_links,
            IssueCode.OKF_LINK_BROKEN,
            f"internal link target '{href}' does not exist",
            source_path,
            bundle_root,
            concept_id=source_id,
        )


def validate_bundle(
    bundle: Path,
    profile: ProfileDefinition,
    *,
    now: datetime | None = None,
) -> ValidationReport:
    bundle_root = bundle.resolve()
    if not bundle_root.is_dir():
        raise ValueError(f"bundle is not a directory: {bundle}")

    checked_at = now or datetime.now(UTC)
    if checked_at.tzinfo is None:
        raise ValueError("validation time must include an explicit UTC offset")

    report = ValidationReport(
        bundle=str(bundle_root),
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        checked_at=checked_at,
    )
    markdown_files = sorted(bundle_root.rglob("*.md"))
    report.documents_checked = len(markdown_files)

    root_index = bundle_root / "index.md"
    if profile.policy.require_root_index and not root_index.exists():
        report.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code=IssueCode.OKF_ROOT_INDEX_MISSING,
                message="bundle root index.md is required by the profile",
                path="index.md",
            )
        )

    link_sets: list[tuple[Path, str | None, tuple[str, ...]]] = []
    uid_paths: dict[str, list[Path]] = defaultdict(list)

    for path in markdown_files:
        if path.name in _RESERVED:
            try:
                metadata, _body, links = parse_reserved_body(path)
            except DocumentParseError as exc:
                _add_issue(
                    report,
                    Severity.ERROR,
                    exc.code,
                    str(exc),
                    path,
                    bundle_root,
                )
                continue

            link_sets.append((path, None, links))
            if path.name == "index.md" and path == root_index:
                if metadata is None:
                    _add_issue(
                        report,
                        Severity.ERROR,
                        IssueCode.OKF_VERSION_MISSING,
                        "root index.md must declare okf_version",
                        path,
                        bundle_root,
                    )
                else:
                    extra_keys = set(metadata) - {"okf_version"}
                    if extra_keys:
                        _add_issue(
                            report,
                            Severity.ERROR,
                            IssueCode.OKF_INDEX_FRONTMATTER_KEYS,
                            f"root index.md has unsupported frontmatter keys: {sorted(extra_keys)}",
                            path,
                            bundle_root,
                        )
                    if str(metadata.get("okf_version")) != profile.okf_version:
                        _add_issue(
                            report,
                            Severity.ERROR,
                            IssueCode.OKF_VERSION_MISMATCH,
                            f"expected okf_version '{profile.okf_version}'",
                            path,
                            bundle_root,
                            field="okf_version",
                        )
            elif metadata is not None:
                _add_issue(
                    report,
                    Severity.ERROR,
                    IssueCode.OKF_RESERVED_FRONTMATTER,
                    "frontmatter is not permitted in this reserved file",
                    path,
                    bundle_root,
                )
            continue

        try:
            document = parse_concept(path, bundle_root)
        except DocumentParseError as exc:
            _add_issue(
                report,
                Severity.ERROR,
                exc.code,
                str(exc),
                path,
                bundle_root,
                concept_id=path.relative_to(bundle_root).with_suffix("").as_posix(),
            )
            continue

        concept: ConceptFrontmatter | None = None
        try:
            concept = ConceptFrontmatter.model_validate(document.metadata)
        except ValidationError as exc:
            for error in exc.errors(include_url=False):
                field = ".".join(str(part) for part in error["loc"])
                _add_issue(
                    report,
                    Severity.ERROR,
                    IssueCode.OKF_FRONTMATTER_INVALID,
                    error["msg"],
                    path,
                    bundle_root,
                    concept_id=document.concept_id,
                    field=field or None,
                )

        concept_uid, relationship_targets = _validate_profile_fields(
            document,
            concept,
            profile,
            report,
            bundle_root,
        )
        if concept_uid:
            uid_paths[concept_uid].append(path)

        if concept and concept.stale_after and checked_at >= concept.stale_after:
            _add_issue(
                report,
                profile.policy.stale_concepts,
                IssueCode.OKF_CONCEPT_STALE,
                f"concept became stale at {concept.stale_after.isoformat()}",
                path,
                bundle_root,
                concept_id=document.concept_id,
                field="stale_after",
            )

        all_links = tuple(dict.fromkeys((*document.links, *relationship_targets)))
        link_sets.append((path, document.concept_id, all_links))

    for concept_uid, paths in uid_paths.items():
        if len(paths) < 2:
            continue
        for path in paths:
            _add_issue(
                report,
                Severity.ERROR,
                IssueCode.PROFILE_DUPLICATE_CONCEPT_UID,
                f"concept_uid '{concept_uid}' occurs in {len(paths)} documents",
                path,
                bundle_root,
                concept_id=path.relative_to(bundle_root).with_suffix("").as_posix(),
                field="concept_uid",
            )

    for source_path, source_id, links in link_sets:
        for href in links:
            _validate_link(source_path, source_id, href, profile, report, bundle_root)

    report.issues.sort(
        key=lambda issue: (issue.path, issue.severity, issue.code, issue.field or "")
    )
    return report
