from __future__ import annotations

import json
import shutil
import subprocess
import sys


def main() -> int:
    executable = shutil.which("detect-secrets")
    if executable is None:
        print("detect-secrets is not installed", file=sys.stderr)
        return 2
    completed = subprocess.run(  # noqa: S603 - fixed executable and arguments; no shell.
        [executable, "scan", "--no-verify"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        print(completed.stderr.strip() or "detect-secrets scan failed", file=sys.stderr)
        return 2
    try:
        results = json.loads(completed.stdout).get("results", {})
    except (AttributeError, json.JSONDecodeError) as exc:
        print(f"invalid detect-secrets output: {exc}", file=sys.stderr)
        return 2

    findings = [
        (path, finding.get("line_number", 0), finding.get("type", "unknown"))
        for path, entries in results.items()
        for finding in entries
    ]
    if findings:
        print("Potential secrets found (values are intentionally not displayed):", file=sys.stderr)
        for path, line_number, finding_type in sorted(findings):
            print(f"  {path}:{line_number}: {finding_type}", file=sys.stderr)
        return 1
    print("No potential secrets found in tracked source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
