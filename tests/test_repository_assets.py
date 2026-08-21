from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert isinstance(loaded, dict)
    return loaded


def test_delivery_backlog_is_internally_consistent() -> None:
    backlog = _load_yaml(PROJECT_ROOT / "tracking/backlog.yaml")
    allowed_statuses = set(backlog["statuses"])
    milestone_ids = {milestone["id"] for milestone in backlog["milestones"]}
    actions = backlog["actions"]
    action_ids = [action["id"] for action in actions]

    assert len(action_ids) == len(set(action_ids)), "action IDs must be unique"

    known_actions = set(action_ids)
    for action in actions:
        assert action["status"] in allowed_statuses
        assert action["milestone"] in milestone_ids
        assert action["priority"] in {"P0", "P1", "P2", "P3"}
        assert action["owner_role"]
        assert action["acceptance"]
        assert set(action["depends_on"]) <= known_actions
        assert action["id"] not in action["depends_on"]
        if action["status"] == "BLOCKED":
            assert action.get("blocker"), f"{action['id']} must describe its blocker"


def test_all_repository_yaml_files_parse() -> None:
    yaml_files = sorted(
        {
            *PROJECT_ROOT.joinpath("profiles").glob("*.yaml"),
            *PROJECT_ROOT.joinpath("tracking").rglob("*.yaml"),
            *PROJECT_ROOT.joinpath("examples").rglob("*.yaml"),
            *PROJECT_ROOT.joinpath("tests/fixtures").rglob("*.yaml"),
            *PROJECT_ROOT.joinpath(".github").rglob("*.yml"),
            *PROJECT_ROOT.joinpath(".github").rglob("*.yaml"),
        }
    )

    for path in yaml_files:
        assert _load_yaml(path), f"{path} should contain a YAML mapping"


def test_every_blocked_action_has_an_open_decision_and_safe_default() -> None:
    backlog = _load_yaml(PROJECT_ROOT / "tracking/backlog.yaml")
    register = _load_yaml(PROJECT_ROOT / "tracking/decision-register.yaml")
    action_ids = {action["id"] for action in backlog["actions"]}
    blocked_actions = {
        action["id"] for action in backlog["actions"] if action["status"] == "BLOCKED"
    }
    decisions = register["decisions"]
    decision_ids = [decision["id"] for decision in decisions]

    assert len(decision_ids) == len(set(decision_ids))
    covered: set[str] = set()
    for decision in decisions:
        assert decision["status"] in register["statuses"]
        assert set(decision["blocks"]) <= action_ids
        assert decision["required_evidence"]
        assert decision["safe_default_if_deferred"]
        if decision["status"] == "OPEN":
            covered.update(decision["blocks"])

    assert blocked_actions <= covered
