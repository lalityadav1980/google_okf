# Framework Supply-Chain and Repository Security

## 1. Outcome and boundary

The repository now produces reviewable supply-chain evidence for the **OKF
framework package** itself. This is separate from the content-release archive,
OCI publication, signature, and release-admission controls described in
[OCI signing and promotion](12-oci-signing-and-promotion.md).

The implemented local/CI path is:

```text
tracked source + uv.lock
  -> Ruff security/static rules
  -> baseline-free secret scan
  -> hashed runtime dependency export and advisory audit
  -> Python wheel and source distribution
  -> normalized CycloneDX 1.5 runtime SBOM
  -> wheel contract verification
  -> SHA-256 build-evidence manifest
  -> retained CI run artifact
```

It does not assert that the repository has an approved license, that every
dependency is legally approved, that a package is signed, or that a GitHub run
is production provenance. Those conclusions require `DEC-001`, `DEC-002`, and
the bank trust decisions in `DEC-005`.

## 2. Implemented controls

| Control | Implementation | Failure behavior | Evidence |
|---|---|---|---|
| Reproducible resolution | `uv.lock`; every CI command uses `--locked` where supported; package build uses the locked Hatchling from the synced environment with isolation disabled | Dependency drift or an out-of-date lock fails installation/export | `pyproject.toml`, `uv.lock` |
| Security static analysis | Ruff `S` rules in addition to correctness/style rules | Finding fails CI; test assertions alone have the narrow `S101` exception | `pyproject.toml`, CI lint step |
| Source secret detection | `detect-secrets` scans Git-visible files without a baseline and without network verification | Any non-allowlisted finding fails; output shows path/type/line but never the value | `scripts/check_secrets.py` |
| Test quality floor | pytest measures branch-aware package coverage with a repository floor of 85% | A regression below the floor fails the full suite and CI | `pyproject.toml`, 141 deterministic tests |
| Runtime vulnerability audit | uv exports exact, hashed, non-development runtime requirements; `pip-audit` checks them without invoking pip | Export, collection, or known-vulnerability finding fails | `scripts/audit_runtime_dependencies.py` |
| Repository-host detection | GitHub secret scanning/push protection plus Dependabot vulnerability alerts and automatic security-update pull requests | Host detects pushed/provider patterns and opens eligible security fixes; local gates remain authoritative for CI | Repository security settings and `.github/dependabot.yml` |
| Runtime SBOM | uv exports CycloneDX 1.5 for locked runtime dependencies | Wrong format/root or invalid lock digest fails | `scripts/build_framework_evidence.py` |
| Reproducible build | Volatile SBOM timestamp/UUID are normalized; build time is explicit; CI performs an isolated second package/evidence build and byte-compares all four retained files | Any byte difference fails | `normalize_cyclonedx_sbom` and directory-comparison tests; `scripts/check_framework_reproducibility.py` |
| Contract-bearing wheel | Hatch includes the OPA admission policy and all committed JSON/OpenAPI schemas | Missing, duplicate, unsafe, or symlinked wheel members fail | `verify_framework_wheel` tests |
| Digest inventory and independent verification | A typed manifest records source commit, explicit creation time, Python/uv versions, lock digest, size, media type, and SHA-256 for wheel/source/SBOM; a separate verifier rechecks canonical encoding, exact inventory, hashes, expected commit/lock, SBOM normalization, and wheel contracts | Unsafe, duplicate, unsorted, external, unexpected, missing, tampered, or unsupported artifacts fail | `framework-build-evidence-v1.schema.json`, `scripts/verify_framework_evidence.py` |
| CI evidence retention | Pinned `actions/upload-artifact` stores the four framework artifacts for 14 days | Missing output fails the workflow | `.github/workflows/ci.yml` |

The only source allowlist is an explicitly labelled, deterministic SHA-256 test
vector. There is no committed baseline of unaudited findings. Any additional
exception must be on the exact line, explain why it is synthetic, and receive
security review.

## 3. Artifact contract

One framework build creates exactly:

| File | Purpose | Integrity boundary |
|---|---|---|
| `xyz_bank_okf-<version>-py3-none-any.whl` | Installable runtime library plus policy/schema contracts | SHA-256 in build evidence |
| `xyz_bank_okf-<version>.tar.gz` | Reviewable source distribution | SHA-256 in build evidence |
| `xyz-bank-okf-runtime.cdx.json` | CycloneDX 1.5 inventory of locked non-development Python dependencies | Deterministic UUID and `uv.lock` SHA-256 property |
| `xyz-bank-okf-build-evidence.json` | Canonical inventory tying artifacts to source/toolchain/lock | Its own digest is reported by CI output |

The build-evidence file deliberately does not hash itself. A signed OCI
attestation or approved provenance service must sign/retain its digest at the
next trust boundary. A CI artifact download alone is not an authenticity claim.
The verifier accepts `--expected-evidence-sha256` when that digest is supplied
through an independently trusted channel; expected source commit and lock file
can also be pinned by the caller.

The runtime wheel must contain:

- `xyz_okf/assets/policies/release_admission.rego`; and
- every versioned contract under `xyz_okf/assets/schemas/`, including the
  release manifest, serving OpenAPI, discovery, benchmark, and framework-build
  evidence schemas.

Profile examples, test policy, bank content, credentials, and environment
configuration are not runtime wheel assets.

## 4. Reproducibility contract

Reproducibility means the same reviewed source tree, `uv.lock`, Python/uv
toolchain, source commit, and explicit creation time produce byte-identical
artifacts. The build does not read the wall clock for evidence metadata.

uv's native CycloneDX export currently marks SBOM export as a preview feature
and emits a random serial number and current timestamp. The framework validates
CycloneDX 1.5, removes the timestamp, derives UUIDv5 from package identity and
the lock digest, records that digest on the root component, sorts known unordered
collections, and uses canonical compact JSON with one final newline.

Run a framework evidence build:

```bash
evidence_dir="$(mktemp -d /tmp/xyz-okf-framework.XXXXXX)"
uv build --no-build-isolation --no-create-gitignore --out-dir "$evidence_dir"
uv run python scripts/build_framework_evidence.py \
  --dist-dir "$evidence_dir" \
  --source-commit "$(git rev-parse HEAD)" \
  --created-at "$(git show -s --format=%cI HEAD)"
uv run python scripts/verify_framework_evidence.py \
  --dist-dir "$evidence_dir" \
  --expected-source-commit "$(git rev-parse HEAD)" \
  --expected-lock-file uv.lock
uv run python scripts/check_framework_reproducibility.py \
  --reference-dir "$evidence_dir" \
  --source-commit "$(git rev-parse HEAD)" \
  --created-at "$(git show -s --format=%cI HEAD)" \
  --lock-file uv.lock
```

The schema is generated from the frozen Pydantic contract and guarded by a
schema-drift test:

```bash
uv run python scripts/export_framework_evidence_schema.py
uv run pytest tests/test_framework_evidence.py
```

## 5. Security gates

Run the local repository gates with:

```bash
uv run --locked ruff format --check src tests scripts
uv run --locked ruff check src tests scripts
uv run --locked python scripts/check_secrets.py
uv run --locked python scripts/audit_runtime_dependencies.py
uv run --locked mypy src
uv run --locked pytest
```

`pip-audit` queries current vulnerability advisory data, so this gate requires
network access and its result is time-specific. A clean report means no known
advisory matched the exact resolved runtime set at scan time; it is not proof of
absence of vulnerabilities or exploitability analysis. Findings require triage,
a fix/upgrade or documented time-bounded exception, an owner, and a patch SLO.

Secret scanning intentionally uses syntactic/entropy detection without online
credential verification. A clean scan does not replace repository-host secret
protection, push protection, credential rotation, or incident response.
GitHub host controls were checked on 21 August 2026: secret scanning, push
protection, vulnerability alerts, and Dependabot security updates were enabled,
and the Dependabot API reported zero open alerts. Enhanced non-provider pattern
and validity-check modes remain disabled pending repository/security-owner
review of false positives and external verification behavior.

## 6. Remaining bank-owned controls

The following are intentionally not inferred or implemented with placeholder
authority:

1. `DEC-001`: repository license, allowed distribution, dependency license and
   attribution policy, severity/patch SLO, and exception authority.
2. `DEC-002`: protected `main`, required checks/reviews, bypass rules, and
   administrator enforcement.
3. `DEC-005`: approved registry and signing/provenance trust. The JSON evidence
   manifest is unsigned until that decision is implemented.
4. Retention: CI's 14-day convenience retention is not a bank records schedule.
5. Scope expansion: container/base-image, operating-system, workflow-action,
   infrastructure, and production-service SBOM/scanning must be added when
   those artifacts exist.
6. Independent assurance: SAST/secret/advisory tools are engineering gates, not
   penetration testing, source review, legal approval, or control attestation.

Safe default: framework artifacts can be reviewed and reproduced, but must not
be described as an approved, signed, production, compliant, or open-source bank
release until the relevant decisions and evidence exist.

## 7. Primary tool references

- [uv dependency export and CycloneDX SBOM](https://docs.astral.sh/uv/concepts/projects/export/)
- [PyPA pip-audit](https://github.com/pypa/pip-audit)
- [Yelp detect-secrets](https://github.com/Yelp/detect-secrets)
- [CycloneDX JSON specification](https://cyclonedx.org/docs/1.5/json/)
- [GitHub upload-artifact](https://github.com/actions/upload-artifact)
