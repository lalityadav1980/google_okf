from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from xyz_okf.framework_evidence import compare_framework_evidence_directories
from xyz_okf.identity import sha256_bytes


def _aware_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include an explicit UTC offset")
    return parsed


def _run(arguments: list[str], *, cwd: Path) -> None:
    subprocess.run(arguments, cwd=cwd, check=True)  # noqa: S603 - argv only; no shell.


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild framework evidence and require byte-identical artifacts."
    )
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--created-at", type=_aware_datetime, required=True)
    parser.add_argument("--lock-file", type=Path, default=Path("uv.lock"))
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()

    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is not installed")
    project_root = arguments.project_root.resolve()
    lock_file = arguments.lock_file.resolve()
    lock_sha256 = sha256_bytes(lock_file.read_bytes())
    builder = Path(__file__).with_name("build_framework_evidence.py").resolve()
    with tempfile.TemporaryDirectory(prefix="xyz-okf-repro-") as temporary_directory:
        candidate = Path(temporary_directory)
        _run(
            [
                uv,
                "build",
                "--no-build-isolation",
                "--no-create-gitignore",
                "--out-dir",
                str(candidate),
                str(project_root),
            ],
            cwd=project_root,
        )
        _run(
            [
                sys.executable,
                str(builder),
                "--dist-dir",
                str(candidate),
                "--source-commit",
                arguments.source_commit,
                "--created-at",
                arguments.created_at.isoformat(),
                "--lock-file",
                str(lock_file),
            ],
            cwd=project_root,
        )
        digests = compare_framework_evidence_directories(
            arguments.reference_dir,
            candidate,
            expected_source_commit=arguments.source_commit,
            expected_uv_lock_sha256=lock_sha256,
        )
    for path, digest in digests.items():
        print(f"REPRODUCIBLE {path} sha256:{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
