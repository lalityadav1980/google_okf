"""Export the deterministic serving OpenAPI contract used by drift tests."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import Request

from verity_kf.api import create_app
from verity_kf.authorization import PrincipalContext, PrincipalType, ReferencePolicyDecisionPoint
from verity_kf.serving import ReleaseCatalog, ServingService

PROJECT_ROOT = Path(__file__).parents[1]


def resolve_documentation_principal(_request: Request) -> PrincipalContext:
    return PrincipalContext(
        subject="workload:openapi-export",
        principal_type=PrincipalType.WORKLOAD,
        groups=(),
        clearance="PUBLIC",
    )


service = ServingService(
    ReleaseCatalog(),
    ReferencePolicyDecisionPoint({}, policy_version="openapi-export/1.0"),
)
app = create_app(
    service,
    resolve_documentation_principal,
    open_id_connect_url="https://identity.example.invalid/.well-known/openid-configuration",
)
target = PROJECT_ROOT / "schemas/serving-api-v1.openapi.json"
target.write_text(
    json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
