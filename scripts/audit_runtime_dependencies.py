from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(arguments: list[str]) -> int:
    completed = subprocess.run(arguments, check=False)  # noqa: S603 - argv only; no shell.
    return completed.returncode


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("uv is not installed", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="xyz-okf-audit-") as temporary_directory:
        requirements = Path(temporary_directory) / "runtime-requirements.txt"
        export_code = _run(
            [
                uv,
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements.txt",
                "--quiet",
                "--output-file",
                str(requirements),
            ]
        )
        if export_code != 0:
            return export_code
        return _run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--requirement",
                str(requirements),
                "--require-hashes",
                "--disable-pip",
                "--progress-spinner",
                "off",
                "--strict",
            ]
        )


if __name__ == "__main__":
    raise SystemExit(main())
