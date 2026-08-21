"""Export the deterministic release-manifest JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

from verity_kf.release import ReleaseManifest

PROJECT_ROOT = Path(__file__).parents[1]
target = PROJECT_ROOT / "schemas/release-manifest-v1.schema.json"
target.write_text(
    json.dumps(ReleaseManifest.model_json_schema(), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
