from __future__ import annotations

import json
from pathlib import Path

from xyz_okf.framework_evidence import FrameworkBuildEvidence

target = Path(__file__).parents[1] / "schemas/framework-build-evidence-v1.schema.json"
target.write_text(
    json.dumps(FrameworkBuildEvidence.model_json_schema(), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
