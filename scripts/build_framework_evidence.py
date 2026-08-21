from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from verity_kf import __version__
from verity_kf.framework_evidence import (
    FRAMEWORK_EVIDENCE_NAME,
    FRAMEWORK_SBOM_NAME,
    FrameworkEvidenceError,
    build_framework_evidence,
    framework_evidence_bytes,
    normalize_cyclonedx_sbom,
    verify_framework_wheel,
)
from verity_kf.identity import sha256_bytes

_UV_VERSION = re.compile(r"^uv ([0-9A-Za-z.+-]+)(?: .*)?$")


def _aware_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include an explicit UTC offset")
    return parsed


def _one_match(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise FrameworkEvidenceError(
            f"expected exactly one {pattern} artifact in {root}, found {len(matches)}"
        )
    return matches[0]


def _uv_version(uv: str) -> str:
    completed = subprocess.run(  # noqa: S603 - resolved executable and fixed argument.
        [uv, "--version"], check=True, capture_output=True, text=True
    )
    match = _UV_VERSION.fullmatch(completed.stdout.strip())
    if match is None:
        raise FrameworkEvidenceError("could not parse uv --version output")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create deterministic CycloneDX and framework-build evidence."
    )
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--created-at", type=_aware_datetime, required=True)
    parser.add_argument("--lock-file", type=Path, default=Path("uv.lock"))
    arguments = parser.parse_args()

    uv = shutil.which("uv")
    if uv is None:
        raise FrameworkEvidenceError("uv is not installed")
    dist_dir = arguments.dist_dir.resolve()
    dist_dir.mkdir(parents=True, exist_ok=True)
    lock_content = arguments.lock_file.read_bytes()
    lock_sha256 = sha256_bytes(lock_content)

    export = subprocess.run(  # noqa: S603 - resolved executable and fixed argv; no shell.
        [
            uv,
            "export",
            "--preview-features",
            "sbom-export",
            "--locked",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "cyclonedx1.5",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw_sbom = json.loads(export.stdout)
    sbom_bytes = normalize_cyclonedx_sbom(
        raw_sbom,
        package_name="verity-knowledge-fabric",
        package_version=__version__,
        uv_lock_sha256=lock_sha256,
    )
    sbom_path = dist_dir / FRAMEWORK_SBOM_NAME
    sbom_path.write_bytes(sbom_bytes)

    wheel = _one_match(dist_dir, "verity_knowledge_fabric-*.whl")
    source_distribution = _one_match(dist_dir, "verity_knowledge_fabric-*.tar.gz")
    verify_framework_wheel(wheel)
    evidence = build_framework_evidence(
        [wheel, source_distribution, sbom_path],
        artifact_root=dist_dir,
        package_version=__version__,
        source_commit=arguments.source_commit,
        created_at=arguments.created_at,
        python_version=platform.python_version(),
        uv_version=_uv_version(uv),
        uv_lock_sha256=lock_sha256,
    )
    evidence_path = dist_dir / FRAMEWORK_EVIDENCE_NAME
    evidence_path.write_bytes(framework_evidence_bytes(evidence))
    print(f"WROTE {sbom_path} sha256:{sha256_bytes(sbom_bytes)}")
    print(f"WROTE {evidence_path} sha256:{sha256_bytes(framework_evidence_bytes(evidence))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
