# Contributing

## Prerequisites

- Python 3.13
- uv 0.11.7 or later, below 0.13
- Git

## Set up

```bash
uv sync --locked
```

## Quality gates

Run before opening a pull request:

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src
uv run pytest
uv run xyz-okf validate examples/pilot-bundle \
  --profile profiles/xyz-bank-pilot.yaml
```

To apply formatting locally:

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
```

## Work tracking

1. Select an action from [`tracking/backlog.yaml`](tracking/backlog.yaml).
2. Create or link a GitHub Issue using the same action ID.
3. Move the action to `IN_PROGRESS` only when it has an active owner.
4. Include the action ID in the branch and pull-request title.
5. Update backlog status and acceptance evidence in the same change that
   completes the action.

Recommended branch names:

```text
codex/OKF-201-deterministic-renderer
feature/OKF-401-release-manifest
fix/OKF-103-link-resolution
```

## Development rules

- Keep parsing and base validation deterministic and free of network/model calls.
- Preserve unknown OKF frontmatter fields.
- Add stable issue codes and tests for validation rules.
- Put source-specific behavior behind the connector contract.
- Do not include credentials, real customer data, or confidential bank content.
- Record public contract or platform changes in an ADR.
- Pin dependencies and CI actions; update `uv.lock` with dependency changes.
- Add security, privacy, records, authorization, and rollback analysis to the PR.

## Commit convention

Use a short conventional prefix:

- `feat:` new framework capability;
- `fix:` defect correction;
- `docs:` documentation or tracker-only change;
- `test:` test-only change;
- `build:` dependency, packaging, or CI change;
- `refactor:` internal change without contract change; and
- `security:` security control or vulnerability correction.

## License status

This repository does not yet have an approved project license. Do not distribute
or reuse its code outside the repository owner's permissions until action
`OKF-004` is completed.

