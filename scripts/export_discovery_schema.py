"""Export the deterministic source-discovery JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path

from xyz_okf.discovery import SourceDiscoveryProfile

PROJECT_ROOT = Path(__file__).parents[1]
target = PROJECT_ROOT / "schemas/source-discovery-v1.schema.json"
target.write_text(
    json.dumps(SourceDiscoveryProfile.model_json_schema(), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
