# Validation Issue Catalog and Conformance Suite

## 1. Purpose

Validation behavior is a public automation contract. CI, producer pipelines,
review workflows, and release admission consume stable issue codes; they must
not parse human-readable messages or depend on Python exception text.

The framework separates:

- **OKF structural compatibility:** UTF-8, frontmatter, YAML mapping, required
  `type`, reserved-file behavior, and declared OKF version; and
- **XYZ Bank release profile:** mandatory governance metadata, controlled
  vocabulary, verification, freshness, link containment, authorization, and
  bundle integrity.

The bank profile can be stricter than baseline OKF consumption. For example,
OKF consumers tolerate broken links, while the bank release profile can reject
them. The baseline v0.2 fixture profile reports a broken link as a warning and
still accepts the bundle.

## 2. Stable issue catalog

[`profiles/validation-issues.yaml`](../profiles/validation-issues.yaml) is the
machine-readable catalog. Every code contains:

- default severity and whether the active profile may override it;
- OKF or organizational scope;
- control/quality rationale;
- remediation guidance; and
- at least one conformance or unit-test evidence reference.

`IssueCode` is the code-level closed vocabulary. Tests require an exact set
match between the enum and catalog, reject duplicates, and reject unknown test
references.

Governance rules:

1. Never change the meaning of an issued code.
2. Never reuse or silently remove a code; deprecate it in a new catalog version.
3. Message wording may improve without a contract version change.
4. Severity changes require a profile/catalog version and control-owner review.
5. Every new rule requires catalog rationale, remediation, and a deterministic
   positive/negative fixture before enforcement.

## 3. Fixture suite

[`tests/fixtures/conformance/cases.yaml`](../tests/fixtures/conformance/cases.yaml)
is the fixture manifest. Each case names its bundle, validation profile,
expected validity, and complete expected issue-code set.

The current pack covers:

- minimal OKF v0.2 and v0.1 compatibility;
- producer extensions and bare-mapping verification compatibility;
- attested-computation extension fields;
- UTF-8, missing/unclosed frontmatter, YAML syntax and mapping shape;
- missing required OKF type;
- root/nested reserved-file rules and version declarations;
- broken and bundle-escaping links; and
- all XYZ Bank profile rules through deterministic unit fixtures.

All content and endpoints are synthetic. Live source systems, credentials, or
bank knowledge are prohibited in fixtures.

## 4. Running the evidence

```bash
uv run pytest tests/test_conformance.py tests/test_validator.py
```

Run a baseline compatibility fixture directly:

```bash
uv run xyz-okf validate \
  tests/fixtures/conformance/valid/minimal-v02 \
  --profile profiles/okf-v02-base.yaml \
  --now 2026-08-21T00:00:00Z
```

The full CI test job runs the conformance suite. A fixture expectation change is
a reviewed contract change, not a snapshot update performed merely to make CI
green.

## 5. Version policy

- Catalog and suite versions use `major.minor` strings.
- Additive fixtures and codes increment the minor version.
- A breaking interpretation, removed code, or changed canonical expectation
  increments the major version.
- Profiles pin the OKF version they validate.
- Compatibility fixtures do not claim that XYZ Bank will publish new v0.1
  bundles; they prove that migration tooling can parse a legacy shape.

