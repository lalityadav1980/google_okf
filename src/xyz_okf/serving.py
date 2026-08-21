from __future__ import annotations

import posixpath
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from xyz_okf.authorization import (
    AuthorizationDecision,
    AuthorizationRequest,
    PolicyDecisionPoint,
    PrincipalContext,
    ResourceContext,
    RetrievalAction,
)
from xyz_okf.parser import markdown_links, split_frontmatter
from xyz_okf.release import (
    RELEASE_MEDIA_TYPE,
    ReleaseFile,
    VerifiedRelease,
    verify_release,
)

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_CHANNEL = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_WORD = re.compile(r"[\w-]+", flags=re.UNICODE)


class ServingError(ValueError):
    """Base error for release catalog and retrieval operations."""


class ReleaseNotFound(ServingError):
    pass


class ReleaseWithdrawn(ServingError):
    pass


class ConceptNotFound(ServingError):
    pass


class RetrievalDenied(ConceptNotFound):
    """Deliberately indistinguishable from a missing concept at the API boundary."""


class LifecycleFiltered(ConceptNotFound):
    """Concept is present but is not eligible under the requested lifecycle policy."""


class ReleaseState(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class AdmissionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_type: Literal["application/vnd.xyz-bank.okf.release.v1+tar+gzip"] = (
        "application/vnd.xyz-bank.okf.release.v1+tar+gzip"
    )
    signature_verified: bool
    archive_verified: bool
    policy_allowed: bool
    decision_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)


class WithdrawalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    reason: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    at: AwareDatetime


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str | None = None
    title: str | None = None
    resource: str = Field(min_length=1)
    last_modified: AwareDatetime | None = None


class AuthorizedLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    concept_uid: str
    concept_path: str
    title: str


class ConceptEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    release_id: str
    release_digest: str
    profile_id: str
    profile_version: str
    concept_uid: str
    concept_path: str
    concept_type: str
    title: str
    description: str | None = None
    classification: str
    lifecycle_status: str
    stale_after: AwareDatetime
    exact_sha256: str
    canonical_sha256: str
    body: str
    citations: tuple[SourceCitation, ...]
    links: tuple[AuthorizedLink, ...]
    authorization: AuthorizationDecision


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    concept_uid: str
    concept_path: str
    concept_type: str
    title: str
    description: str | None = None
    classification: str
    lifecycle_status: str
    stale_after: AwareDatetime
    exact_sha256: str
    score: int = Field(ge=1)
    snippet: str
    citations: tuple[SourceCitation, ...]
    authorization: AuthorizationDecision


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    release_id: str
    release_digest: str
    profile_id: str
    profile_version: str
    query: str
    hits: tuple[SearchHit, ...]


class AuthorizedReleaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    release_id: str
    release_digest: str
    archive_sha256: str
    profile_id: str
    profile_version: str
    state: ReleaseState
    channels: tuple[str, ...]
    authorized_concept_count: int = Field(ge=1)


@dataclass(frozen=True, slots=True)
class _ConceptIndexEntry:
    manifest_file: ReleaseFile
    title: str
    description: str | None
    tags: tuple[str, ...]
    sources: tuple[SourceCitation, ...]


@dataclass(slots=True)
class _CatalogRecord:
    registry_digest: str
    verified: VerifiedRelease
    evidence: AdmissionEvidence
    concepts_by_uid: dict[str, _ConceptIndexEntry]
    concepts_by_path: dict[str, _ConceptIndexEntry]
    state: ReleaseState = ReleaseState.CANDIDATE
    withdrawal: WithdrawalRecord | None = None


class InMemoryBodyStore:
    """Reference content store with access counts for authorization-order tests."""

    def __init__(self) -> None:
        self._content: dict[tuple[str, str], bytes] = {}
        self._reads: Counter[tuple[str, str]] = Counter()

    def register(self, release_digest: str, path: str, content: bytes) -> None:
        key = (release_digest, path)
        existing = self._content.get(key)
        if existing is not None and existing != content:
            raise ServingError("a release digest cannot be registered with different content")
        self._content[key] = content

    def read(self, release_digest: str, path: str) -> bytes:
        key = (release_digest, path)
        try:
            content = self._content[key]
        except KeyError as exc:
            raise ConceptNotFound("concept content is unavailable") from exc
        self._reads[key] += 1
        return content

    def read_count(self, release_digest: str, path: str) -> int:
        return self._reads[(release_digest, path)]


class ReleaseCatalog:
    """Local immutable-release lifecycle reference implementation."""

    def __init__(self, body_store: InMemoryBodyStore | None = None) -> None:
        self.body_store = body_store or InMemoryBodyStore()
        self._records: dict[str, _CatalogRecord] = {}
        self._channels: dict[str, str] = {}

    def admit(
        self,
        archive_bytes: bytes,
        *,
        registry_digest: str,
        evidence: AdmissionEvidence,
    ) -> None:
        if not _DIGEST.fullmatch(registry_digest):
            raise ServingError("registry_digest must be an immutable sha256 digest")
        if not (
            evidence.signature_verified
            and evidence.archive_verified
            and evidence.policy_allowed
            and evidence.artifact_type == RELEASE_MEDIA_TYPE
        ):
            raise ServingError("release admission evidence is not fully verified and allowed")

        verified = verify_release(archive_bytes)
        existing = self._records.get(registry_digest)
        if existing is not None:
            if existing.verified.archive_sha256 != verified.archive_sha256:
                raise ServingError("registry digest is already bound to a different archive")
            return

        concepts_by_uid: dict[str, _ConceptIndexEntry] = {}
        concepts_by_path: dict[str, _ConceptIndexEntry] = {}
        for manifest_file in verified.manifest.files:
            if manifest_file.concept_uid is None:
                continue
            concept = self._build_index_entry(manifest_file, verified.files[manifest_file.path])
            if manifest_file.concept_uid in concepts_by_uid:
                raise ServingError("release contains duplicate concept_uid values")
            concepts_by_uid[manifest_file.concept_uid] = concept
            concepts_by_path[manifest_file.path] = concept
            self.body_store.register(
                registry_digest, manifest_file.path, verified.files[manifest_file.path]
            )
        if not concepts_by_uid:
            raise ServingError("release contains no servable concepts")
        self._records[registry_digest] = _CatalogRecord(
            registry_digest=registry_digest,
            verified=verified,
            evidence=evidence,
            concepts_by_uid=concepts_by_uid,
            concepts_by_path=concepts_by_path,
        )

    @staticmethod
    def _build_index_entry(manifest_file: ReleaseFile, content: bytes) -> _ConceptIndexEntry:
        required = {
            "acl_ref": manifest_file.acl_ref,
            "canonical_sha256": manifest_file.canonical_sha256,
            "classification": manifest_file.classification,
            "concept_type": manifest_file.concept_type,
            "stale_after": manifest_file.stale_after,
            "status": manifest_file.status,
        }
        missing = sorted(key for key, value in required.items() if value is None)
        if missing:
            raise ServingError(
                f"concept release metadata is incomplete for {manifest_file.path}: {missing}"
            )
        try:
            metadata, _ = split_frontmatter(content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ServingError(f"concept cannot be indexed: {manifest_file.path}") from exc
        title = metadata.get("title")
        description = metadata.get("description")
        tags = metadata.get("tags", [])
        raw_sources = metadata.get("sources", [])
        if not isinstance(title, str) or not title:
            title = PurePosixPath(manifest_file.path).stem.replace("-", " ").title()
        if description is not None and not isinstance(description, str):
            raise ServingError(f"concept description is invalid: {manifest_file.path}")
        if not isinstance(tags, list) or any(not isinstance(value, str) for value in tags):
            raise ServingError(f"concept tags are invalid: {manifest_file.path}")
        if not isinstance(raw_sources, list):
            raise ServingError(f"concept sources are invalid: {manifest_file.path}")
        try:
            sources = tuple(
                SourceCitation(
                    source_id=value.get("id"),
                    title=value.get("title"),
                    resource=value["resource"],
                    last_modified=value.get("last_modified"),
                )
                for value in raw_sources
                if isinstance(value, dict)
            )
        except (KeyError, ValueError) as exc:
            raise ServingError(f"concept source citation is invalid: {manifest_file.path}") from exc
        if len(sources) != len(raw_sources):
            raise ServingError(f"concept source citation is invalid: {manifest_file.path}")
        return _ConceptIndexEntry(
            manifest_file=manifest_file,
            title=title,
            description=description,
            tags=tuple(sorted(set(tags))),
            sources=sources,
        )

    def promote(self, channel: str, registry_digest: str) -> str | None:
        if not _CHANNEL.fullmatch(channel):
            raise ServingError("channel must be a lowercase portable identifier")
        record = self._get_record(registry_digest)
        if record.state == ReleaseState.WITHDRAWN:
            raise ReleaseWithdrawn("a withdrawn release cannot be promoted")
        previous = self._channels.get(channel)
        self._channels[channel] = registry_digest
        record.state = ReleaseState.ACTIVE
        return previous

    def rollback(self, channel: str, prior_registry_digest: str) -> str:
        current = self._channels.get(channel)
        if current is None:
            raise ReleaseNotFound("channel has no active release")
        if current == prior_registry_digest:
            return current
        self.promote(channel, prior_registry_digest)
        return current

    def withdraw(self, registry_digest: str, withdrawal: WithdrawalRecord) -> tuple[str, ...]:
        record = self._get_record(registry_digest)
        if record.state == ReleaseState.WITHDRAWN:
            if record.withdrawal != withdrawal:
                raise ServingError("withdrawal evidence is immutable")
            return ()
        removed = tuple(
            sorted(
                channel for channel, digest in self._channels.items() if digest == registry_digest
            )
        )
        for channel in removed:
            del self._channels[channel]
        record.state = ReleaseState.WITHDRAWN
        record.withdrawal = withdrawal
        return removed

    def resolve(self, digest_or_channel: str) -> _CatalogRecord:
        digest = (
            digest_or_channel
            if _DIGEST.fullmatch(digest_or_channel)
            else self._channels.get(digest_or_channel)
        )
        if digest is None:
            raise ReleaseNotFound("release or channel was not found")
        return self._get_record(digest)

    def records(self) -> tuple[_CatalogRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def channels_for(self, registry_digest: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                channel for channel, digest in self._channels.items() if digest == registry_digest
            )
        )

    def _get_record(self, registry_digest: str) -> _CatalogRecord:
        try:
            return self._records[registry_digest]
        except KeyError as exc:
            raise ReleaseNotFound("release was not found") from exc


class ServingService:
    def __init__(self, catalog: ReleaseCatalog, pdp: PolicyDecisionPoint) -> None:
        self._catalog = catalog
        self._pdp = pdp

    def list_releases(
        self, principal: PrincipalContext, *, now: datetime
    ) -> tuple[AuthorizedReleaseSummary, ...]:
        summaries: list[AuthorizedReleaseSummary] = []
        for record in self._catalog.records():
            if record.state == ReleaseState.WITHDRAWN:
                continue
            authorized_count = sum(
                self._authorize(principal, record, concept, RetrievalAction.DISCOVER).allowed
                for concept in record.concepts_by_uid.values()
                if self._eligible(concept, now=now)
            )
            if authorized_count == 0:
                continue
            manifest = record.verified.manifest
            summaries.append(
                AuthorizedReleaseSummary(
                    bundle_id=manifest.bundle_id,
                    release_id=manifest.release_id,
                    release_digest=record.registry_digest,
                    archive_sha256=record.verified.archive_sha256,
                    profile_id=manifest.profile.profile_id,
                    profile_version=manifest.profile.profile_version,
                    state=record.state,
                    channels=self._catalog.channels_for(record.registry_digest),
                    authorized_concept_count=authorized_count,
                )
            )
        return tuple(summaries)

    def fetch_concept(
        self,
        principal: PrincipalContext,
        *,
        digest_or_channel: str,
        concept_uid: str,
        now: datetime,
        include_deprecated: bool = False,
        include_stale: bool = False,
    ) -> ConceptEnvelope:
        record = self._active_record(digest_or_channel)
        try:
            concept = record.concepts_by_uid[concept_uid]
        except KeyError as exc:
            raise ConceptNotFound("concept was not found") from exc
        if not self._eligible(
            concept,
            now=now,
            include_deprecated=include_deprecated,
            include_stale=include_stale,
        ):
            raise LifecycleFiltered("concept was not found")
        decision = self._authorize(principal, record, concept, RetrievalAction.READ)
        if not decision.allowed:
            raise RetrievalDenied("concept was not found")

        _, body = self._read_document(record, concept)
        links = self._authorized_links(
            principal,
            record,
            concept,
            body,
            now=now,
            include_deprecated=include_deprecated,
            include_stale=include_stale,
        )
        file = concept.manifest_file
        manifest = record.verified.manifest
        return ConceptEnvelope(
            bundle_id=manifest.bundle_id,
            release_id=manifest.release_id,
            release_digest=record.registry_digest,
            profile_id=manifest.profile.profile_id,
            profile_version=manifest.profile.profile_version,
            concept_uid=str(file.concept_uid),
            concept_path=file.path,
            concept_type=str(file.concept_type),
            title=concept.title,
            description=concept.description,
            classification=str(file.classification),
            lifecycle_status=str(file.status),
            stale_after=cast(datetime, file.stale_after),
            exact_sha256=file.exact_sha256,
            canonical_sha256=str(file.canonical_sha256),
            body=body,
            citations=concept.sources,
            links=links,
            authorization=decision,
        )

    def search(
        self,
        principal: PrincipalContext,
        *,
        digest_or_channel: str,
        query: str,
        now: datetime,
        limit: int = 10,
        include_deprecated: bool = False,
        include_stale: bool = False,
    ) -> SearchResponse:
        terms = tuple(sorted(set(_WORD.findall(query.casefold()))))
        if not terms:
            raise ServingError("query must contain at least one searchable term")
        if not 1 <= limit <= 100:
            raise ServingError("limit must be between 1 and 100")
        record = self._active_record(digest_or_channel)
        hits: list[SearchHit] = []
        for concept in record.concepts_by_uid.values():
            if not self._eligible(
                concept,
                now=now,
                include_deprecated=include_deprecated,
                include_stale=include_stale,
            ):
                continue
            decision = self._authorize(principal, record, concept, RetrievalAction.SEARCH)
            if not decision.allowed:
                continue
            _, body = self._read_document(record, concept)
            title_text = concept.title.casefold()
            body_text = body.casefold()
            score = sum((2 * title_text.count(term)) + body_text.count(term) for term in terms)
            if score == 0:
                continue
            file = concept.manifest_file
            hits.append(
                SearchHit(
                    concept_uid=str(file.concept_uid),
                    concept_path=file.path,
                    concept_type=str(file.concept_type),
                    title=concept.title,
                    description=concept.description,
                    classification=str(file.classification),
                    lifecycle_status=str(file.status),
                    stale_after=cast(datetime, file.stale_after),
                    exact_sha256=file.exact_sha256,
                    score=score,
                    snippet=self._snippet(body, terms),
                    citations=concept.sources,
                    authorization=decision,
                )
            )
        hits.sort(key=lambda hit: (-hit.score, hit.title.casefold(), hit.concept_uid))
        manifest = record.verified.manifest
        return SearchResponse(
            bundle_id=manifest.bundle_id,
            release_id=manifest.release_id,
            release_digest=record.registry_digest,
            profile_id=manifest.profile.profile_id,
            profile_version=manifest.profile.profile_version,
            query=query,
            hits=tuple(hits[:limit]),
        )

    def _active_record(self, digest_or_channel: str) -> _CatalogRecord:
        record = self._catalog.resolve(digest_or_channel)
        if record.state == ReleaseState.WITHDRAWN:
            raise ReleaseWithdrawn("release has been withdrawn")
        return record

    @staticmethod
    def _eligible(
        concept: _ConceptIndexEntry,
        *,
        now: datetime,
        include_deprecated: bool = False,
        include_stale: bool = False,
    ) -> bool:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ServingError("now must include an explicit UTC offset")
        status = concept.manifest_file.status
        stale_after = concept.manifest_file.stale_after
        if status == "draft" or (status == "deprecated" and not include_deprecated):
            return False
        return include_stale or (stale_after is not None and now <= stale_after)

    def _authorize(
        self,
        principal: PrincipalContext,
        record: _CatalogRecord,
        concept: _ConceptIndexEntry,
        action: RetrievalAction,
    ) -> AuthorizationDecision:
        file = concept.manifest_file
        return self._pdp.authorize(
            AuthorizationRequest(
                principal=principal,
                resource=ResourceContext(
                    bundle_id=record.verified.manifest.bundle_id,
                    release_digest=record.registry_digest,
                    concept_uid=str(file.concept_uid),
                    concept_path=file.path,
                    classification=file.classification,  # type: ignore[arg-type]
                    acl_ref=str(file.acl_ref),
                    action=action,
                ),
            )
        )

    def _read_document(
        self, record: _CatalogRecord, concept: _ConceptIndexEntry
    ) -> tuple[Mapping[str, object], str]:
        content = self._catalog.body_store.read(record.registry_digest, concept.manifest_file.path)
        try:
            return split_frontmatter(content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ServingError("verified concept could not be parsed") from exc

    def _authorized_links(
        self,
        principal: PrincipalContext,
        record: _CatalogRecord,
        source: _ConceptIndexEntry,
        body: str,
        *,
        now: datetime,
        include_deprecated: bool,
        include_stale: bool,
    ) -> tuple[AuthorizedLink, ...]:
        links: list[AuthorizedLink] = []
        for raw_link in markdown_links(body):
            target_path = self._internal_target(source.manifest_file.path, raw_link)
            if target_path is None:
                continue
            target = record.concepts_by_path.get(target_path)
            if target is None or not self._eligible(
                target,
                now=now,
                include_deprecated=include_deprecated,
                include_stale=include_stale,
            ):
                continue
            decision = self._authorize(principal, record, target, RetrievalAction.FOLLOW_LINK)
            if decision.allowed:
                links.append(
                    AuthorizedLink(
                        concept_uid=str(target.manifest_file.concept_uid),
                        concept_path=target.manifest_file.path,
                        title=target.title,
                    )
                )
        return tuple(
            sorted(
                {link.concept_uid: link for link in links}.values(),
                key=lambda link: (link.title.casefold(), link.concept_uid),
            )
        )

    @staticmethod
    def _internal_target(source_path: str, raw_link: str) -> str | None:
        if ":" in raw_link.split("/", maxsplit=1)[0] or raw_link.startswith("//"):
            return None
        without_fragment = raw_link.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0]
        if not without_fragment:
            return None
        if without_fragment.startswith("/"):
            candidate = without_fragment.lstrip("/")
        else:
            candidate = posixpath.join(posixpath.dirname(source_path), without_fragment)
        normalized = posixpath.normpath(candidate)
        if normalized.startswith("../") or normalized in {".", ".."}:
            return None
        return normalized

    @staticmethod
    def _snippet(body: str, terms: Iterable[str], *, maximum: int = 240) -> str:
        collapsed = " ".join(body.split())
        folded = collapsed.casefold()
        positions = [folded.find(term) for term in terms]
        positions = [position for position in positions if position >= 0]
        start = max(0, (min(positions) if positions else 0) - 60)
        snippet = collapsed[start : start + maximum]
        if start > 0:
            snippet = "…" + snippet
        if start + maximum < len(collapsed):
            snippet += "…"
        return snippet
