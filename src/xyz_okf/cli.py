from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import typer
import yaml
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table

from xyz_okf.connector_conformance import ConnectorCertificationReport
from xyz_okf.discovery import SourceDiscoveryProfile
from xyz_okf.evaluation import EvaluationBenchmark, EvaluationRun, score_evaluation
from xyz_okf.identity import (
    IdentityPolicy,
    SourceAnchor,
    allocate_identity,
    canonical_concept_sha256,
    canonical_source_record_sha256,
    sha256_bytes,
)
from xyz_okf.models import ProfileDefinition, Severity
from xyz_okf.parser import DocumentParseError, parse_concept
from xyz_okf.profile import load_profile
from xyz_okf.release import (
    ReleaseBuildError,
    ReleaseManifest,
    build_release,
    verify_release,
)
from xyz_okf.renderer import (
    RenderError,
    RenderMapping,
    SourceRecordDocument,
    render_concept,
)
from xyz_okf.validator import validate_bundle

app = typer.Typer(
    name="xyz-okf",
    no_args_is_help=True,
    help="Render, validate, and inspect OKF bundles against the XYZ Bank profile.",
)
console = Console()

BundleArgument = Annotated[
    Path,
    typer.Argument(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
]
ProfileOption = Annotated[
    Path,
    typer.Option(
        "--profile",
        "-p",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="XYZ Bank profile definition.",
    ),
]
YamlArgument = Annotated[
    Path,
    typer.Argument(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
]


def _parse_now(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise typer.BadParameter("--now must include an explicit UTC offset")
    return parsed


def _load_profile_or_exit(path: Path) -> ProfileDefinition:
    try:
        return load_profile(path)
    except (OSError, ValidationError, ValueError) as exc:
        console.print(f"[red]Profile error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


def _load_yaml_or_exit[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        return model.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
        console.print(f"[red]Input error in {path.name}:[/red] {exc}")
        raise typer.Exit(code=2) from exc


@app.command("render")
def render_command(
    source_record_path: YamlArgument,
    mapping_path: YamlArgument,
    output_root: Annotated[
        Path,
        typer.Option(
            "--output-root",
            "-o",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
            help="Bundle directory under which the mapping output path is written.",
        ),
    ],
    check: Annotated[
        bool,
        typer.Option(help="Compare with the existing file without writing."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(help="Replace an existing file only when its bytes differ."),
    ] = False,
) -> None:
    """Render one deterministic OKF concept from a source record and mapping."""
    source_document = _load_yaml_or_exit(source_record_path, SourceRecordDocument)
    mapping = _load_yaml_or_exit(mapping_path, RenderMapping)
    try:
        rendered = render_concept(source_document.to_source_record(), mapping)
    except (RenderError, ValidationError) as exc:
        console.print(f"[red]Render error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    resolved_root = output_root.resolve()
    target = (resolved_root / rendered.relative_path).resolve()
    try:
        target.relative_to(resolved_root)
    except ValueError as exc:
        console.print("[red]Render error:[/red] output path resolves outside --output-root")
        raise typer.Exit(code=2) from exc
    if check:
        if not target.is_file() or target.read_bytes() != rendered.content:
            console.print(f"[red]DIFF[/red] {rendered.relative_path}")
            raise typer.Exit(code=1)
        console.print(f"[green]MATCH[/green] {rendered.relative_path} sha256:{rendered.sha256}")
        return

    if target.exists() and target.read_bytes() != rendered.content and not force:
        console.print(
            f"[red]Refusing to replace changed file:[/red] {rendered.relative_path}; use --force"
        )
        raise typer.Exit(code=1)

    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_bytes() != rendered.content:
        target.write_bytes(rendered.content)
        state = "WROTE"
    else:
        state = "UNCHANGED"
    console.print(f"[green]{state}[/green] {rendered.relative_path} sha256:{rendered.sha256}")


@app.command("allocate-identity")
def allocate_identity_command(
    source_record_path: YamlArgument,
    identity_policy_path: YamlArgument,
    concept_type: Annotated[str, typer.Option("--type", help="Profile concept type.")],
    fragment: Annotated[
        str,
        typer.Option(help="Stable source fragment when one record produces multiple concepts."),
    ] = "",
    retained_path: Annotated[
        str | None,
        typer.Option(help="Previously approved path to retain across title/type changes."),
    ] = None,
) -> None:
    """Allocate a stable bank concept UID and initial OKF path."""
    source_document = _load_yaml_or_exit(source_record_path, SourceRecordDocument)
    policy = _load_yaml_or_exit(identity_policy_path, IdentityPolicy)
    anchor = SourceAnchor(
        source_system=source_document.source_system,
        record_id=source_document.record_id,
        fragment=fragment,
    )
    try:
        identity = allocate_identity(
            anchor,
            title=source_document.title,
            concept_type=concept_type,
            policy=policy,
            retained_path=retained_path,
        )
    except (ValidationError, ValueError) as exc:
        console.print(f"[red]Identity error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    typer.echo(
        json.dumps(
            {
                "concept_id": identity.concept_id,
                "concept_uid": identity.concept_uid,
                "output_path": str(identity.output_path),
                "policy_id": identity.policy_id,
                "policy_version": identity.policy_version,
                "source_anchor": identity.source_anchor.model_dump(),
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("hash-concept")
def hash_concept_command(concept_path: YamlArgument) -> None:
    """Print exact-byte and canonical SHA-256 digests for one concept."""
    try:
        content = concept_path.read_bytes()
        text_value = content.decode("utf-8")
        canonical_digest = canonical_concept_sha256(text_value)
    except (OSError, UnicodeDecodeError, DocumentParseError, ValueError) as exc:
        console.print(f"[red]Hash error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    typer.echo(
        json.dumps(
            {
                "canonical_profile": "xyz-okf-concept-c14n-v1",
                "canonical_sha256": canonical_digest,
                "exact_sha256": sha256_bytes(content),
                "path": str(concept_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("hash-source")
def hash_source_command(source_record_path: YamlArgument) -> None:
    """Print the canonical SHA-256 digest for one source record."""
    source_document = _load_yaml_or_exit(source_record_path, SourceRecordDocument)
    typer.echo(
        json.dumps(
            {
                "canonical_profile": "xyz-okf-source-c14n-v1",
                "canonical_sha256": canonical_source_record_sha256(
                    source_document.to_source_record()
                ),
                "source_record": source_document.record_id,
                "source_system": source_document.source_system,
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("build-release")
def build_release_command(
    bundle: BundleArgument,
    profile_path: ProfileOption = Path("profiles/xyz-bank-pilot.yaml"),
    bundle_id: Annotated[str, typer.Option(help="Portable bundle identifier.")] = "",
    release_id: Annotated[str, typer.Option(help="Portable immutable release identifier.")] = "",
    source_commit: Annotated[
        str,
        typer.Option(help="Lowercase Git commit included in release provenance."),
    ] = "",
    created_at: Annotated[
        str,
        typer.Option(help="Explicit aware ISO 8601 build/validation timestamp."),
    ] = "",
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            "-o",
            file_okay=False,
            dir_okay=True,
            resolve_path=True,
        ),
    ] = Path("dist/releases"),
    prior_release_digest: Annotated[
        str | None,
        typer.Option(help="Optional exact SHA-256 digest of the prior release archive."),
    ] = None,
    force: Annotated[bool, typer.Option(help="Replace different local output files.")] = False,
) -> None:
    """Validate and build a deterministic manifest-bearing release archive."""
    profile = _load_profile_or_exit(profile_path)
    try:
        build_time = _parse_now(created_at)
        if build_time is None:
            raise ValueError("--created-at is required")
        artifact = build_release(
            bundle,
            profile,
            bundle_id=bundle_id,
            release_id=release_id,
            source_commit=source_commit,
            created_at=build_time,
            prior_release_digest=prior_release_digest,
        )
    except (ReleaseBuildError, ValueError) as exc:
        console.print(f"[red]Release build error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        output_dir / f"{release_id}.manifest.json": artifact.manifest_bytes,
        output_dir / f"{release_id}.tar.gz": artifact.archive_bytes,
    }
    changed = [
        path for path, content in outputs.items() if path.exists() and path.read_bytes() != content
    ]
    if changed and not force:
        console.print(
            "[red]Refusing to replace changed release output:[/red] "
            + ", ".join(path.name for path in changed)
        )
        raise typer.Exit(code=1)
    for path, content in outputs.items():
        if not path.exists() or path.read_bytes() != content:
            path.write_bytes(content)
    typer.echo(
        json.dumps(
            {
                "archive": str(output_dir / f"{release_id}.tar.gz"),
                "archive_sha256": artifact.archive_sha256,
                "manifest": str(output_dir / f"{release_id}.manifest.json"),
                "manifest_sha256": artifact.manifest_sha256,
                "release_id": release_id,
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("verify-release")
def verify_release_command(archive_path: YamlArgument) -> None:
    """Verify a local release archive inventory and exact/canonical digests."""
    try:
        verified = verify_release(archive_path.read_bytes())
    except (OSError, ReleaseBuildError) as exc:
        console.print(f"[red]Release verification error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo(
        json.dumps(
            {
                "archive_sha256": verified.archive_sha256,
                "bundle_id": verified.manifest.bundle_id,
                "files": len(verified.manifest.files),
                "manifest_sha256": verified.manifest_sha256,
                "release_id": verified.manifest.release_id,
                "valid": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("release-manifest-schema")
def release_manifest_schema_command() -> None:
    """Print the JSON Schema for the release manifest contract."""
    typer.echo(json.dumps(ReleaseManifest.model_json_schema(), indent=2, sort_keys=True))


@app.command("source-discovery-schema")
def source_discovery_schema_command() -> None:
    """Print the JSON Schema for source/platform discovery evidence."""
    typer.echo(json.dumps(SourceDiscoveryProfile.model_json_schema(), indent=2, sort_keys=True))


@app.command("connector-report-schema")
def connector_report_schema_command() -> None:
    """Print the JSON Schema for content-minimized connector certification reports."""
    typer.echo(
        json.dumps(ConnectorCertificationReport.model_json_schema(), indent=2, sort_keys=True)
    )


@app.command("score-benchmark")
def score_benchmark_command(
    benchmark_path: YamlArgument,
    run_path: YamlArgument,
) -> None:
    """Score a content-free pilot observation run against a benchmark."""
    benchmark = _load_yaml_or_exit(benchmark_path, EvaluationBenchmark)
    run = _load_yaml_or_exit(run_path, EvaluationRun)
    try:
        report = score_evaluation(benchmark, run)
    except ValueError as exc:
        console.print(f"[red]Evaluation error:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    typer.echo(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True))


@app.command("validate")
def validate_command(
    bundle: BundleArgument,
    profile_path: ProfileOption = Path("profiles/xyz-bank-pilot.yaml"),
    output_format: Annotated[
        Literal["text", "json"],
        typer.Option("--format", help="Validation report format."),
    ] = "text",
    now: Annotated[
        str | None,
        typer.Option(help="Override validation time with an ISO 8601 timestamp."),
    ] = None,
) -> None:
    """Validate an OKF bundle and return a non-zero exit code on errors."""
    profile = _load_profile_or_exit(profile_path)
    try:
        report = validate_bundle(bundle, profile, now=_parse_now(now))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if output_format == "json":
        payload = report.model_dump(mode="json")
        payload["summary"] = {
            "errors": report.error_count,
            "warnings": report.warning_count,
            "info": report.info_count,
            "valid": report.is_valid,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        table = Table(title=f"OKF validation: {bundle.name}")
        table.add_column("Severity")
        table.add_column("Code")
        table.add_column("Document")
        table.add_column("Field")
        table.add_column("Message")
        for issue in report.issues:
            color = {
                Severity.ERROR: "red",
                Severity.WARNING: "yellow",
                Severity.INFO: "blue",
            }[issue.severity]
            table.add_row(
                f"[{color}]{issue.severity.value}[/{color}]",
                issue.code,
                issue.path,
                issue.field or "-",
                issue.message,
            )
        console.print(table)
        console.print(
            f"Checked {report.documents_checked} documents: "
            f"[red]{report.error_count} errors[/red], "
            f"[yellow]{report.warning_count} warnings[/yellow], "
            f"[blue]{report.info_count} info[/blue]"
        )

    if not report.is_valid:
        raise typer.Exit(code=1)


@app.command("inspect")
def inspect_command(bundle: BundleArgument) -> None:
    """Summarize concept types and lifecycle states in a bundle."""
    types: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    failed: list[str] = []
    bundle_root = bundle.resolve()

    for path in sorted(bundle_root.rglob("*.md")):
        if path.name in {"index.md", "log.md"}:
            continue
        try:
            document = parse_concept(path, bundle_root)
            types[str(document.metadata.get("type", "<missing>"))] += 1
            statuses[str(document.metadata.get("status", "<absent>"))] += 1
        except DocumentParseError:
            failed.append(path.relative_to(bundle_root).as_posix())

    table = Table(title=f"OKF bundle inventory: {bundle.name}")
    table.add_column("Type")
    table.add_column("Concepts", justify="right")
    for type_name, count in sorted(types.items()):
        table.add_row(type_name, str(count))
    console.print(table)
    console.print("Lifecycle: " + ", ".join(f"{key}={value}" for key, value in statuses.items()))
    if failed:
        console.print(f"[red]Unparseable concepts:[/red] {', '.join(failed)}")
        raise typer.Exit(code=1)


@app.command("profile-schema")
def profile_schema_command() -> None:
    """Print the JSON Schema for an XYZ Bank profile definition."""
    typer.echo(json.dumps(ProfileDefinition.model_json_schema(), indent=2, sort_keys=True))
