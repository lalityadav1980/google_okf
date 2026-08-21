# Security Policy

## Supported versions

The framework is pre-release. Only the latest commit on `main` is maintained.

## Reporting a vulnerability

Do not open a public issue containing a vulnerability, credential, internal URL,
customer information, or confidential organisational information. Contact the repository owner
through an approved private channel or use GitHub's private security-advisory
mechanism if it is enabled.

Include:

- affected commit and component;
- reproduction steps using synthetic data;
- expected and actual result;
- confidentiality, integrity, availability, authorization, or privacy impact;
- known workaround; and
- whether any credential or real data may have been exposed.

Do not test against production systems, source platforms, YODA, RACK, or enterprise
identities without explicit authorization.

## Sensitive content rules

- Never commit secrets or authentication material.
- Never use real customer, employee, or transaction data in examples or tests.
- Use `.invalid` hostnames and synthetic identifiers in fixtures.
- Treat source Markdown as untrusted input.
- Treat bundle paths, links, archives, and attachments as path-traversal inputs.
- Enforce authorization before retrieval, snippets, embeddings, links, or graph
  expansion.
