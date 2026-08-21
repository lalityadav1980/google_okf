from __future__ import annotations

import argparse
from pathlib import Path

from verity_kf.framework_evidence import verify_framework_evidence_directory
from verity_kf.identity import sha256_bytes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a framework wheel, source archive, SBOM, and digest inventory."
    )
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--expected-source-commit")
    parser.add_argument("--expected-lock-file", type=Path)
    parser.add_argument("--expected-evidence-sha256")
    arguments = parser.parse_args()

    expected_lock_sha256 = (
        sha256_bytes(arguments.expected_lock_file.read_bytes())
        if arguments.expected_lock_file is not None
        else None
    )
    evidence = verify_framework_evidence_directory(
        arguments.dist_dir,
        expected_source_commit=arguments.expected_source_commit,
        expected_uv_lock_sha256=expected_lock_sha256,
        expected_evidence_sha256=arguments.expected_evidence_sha256,
    )
    print(
        f"VERIFIED {len(evidence.artifacts)} artifacts "
        f"for {evidence.package_name} {evidence.package_version} "
        f"at {evidence.source_commit}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
