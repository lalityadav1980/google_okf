from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token

from verity_kf.issues import IssueCode

_MARKDOWN = MarkdownIt("commonmark")


class DocumentParseError(ValueError):
    def __init__(self, code: IssueCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ParsedDocument:
    path: Path
    concept_id: str
    metadata: dict[str, Any]
    body: str
    links: tuple[str, ...]


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentParseError(IssueCode.OKF_UTF8, "document is not valid UTF-8") from exc


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise DocumentParseError(
            IssueCode.OKF_FRONTMATTER_MISSING, "frontmatter must start on line 1"
        )

    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None
    )
    if closing is None:
        raise DocumentParseError(
            IssueCode.OKF_FRONTMATTER_UNCLOSED, "frontmatter has no closing delimiter"
        )

    raw_frontmatter = "".join(lines[1:closing])
    try:
        loaded = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError as exc:
        raise DocumentParseError(
            IssueCode.OKF_YAML_INVALID, f"invalid YAML frontmatter: {exc}"
        ) from exc

    if not isinstance(loaded, dict):
        raise DocumentParseError(IssueCode.OKF_YAML_MAPPING, "frontmatter must be a YAML mapping")

    return loaded, "".join(lines[closing + 1 :])


def _walk_tokens(tokens: Iterable[Token]) -> Iterable[Token]:
    for token in tokens:
        yield token
        if token.children:
            yield from _walk_tokens(token.children)


def markdown_links(body: str) -> tuple[str, ...]:
    links: list[str] = []
    for token in _walk_tokens(_MARKDOWN.parse(body)):
        if token.type != "link_open":
            continue
        href = token.attrGet("href")
        if href:
            links.append(str(href))
    return tuple(links)


def parse_concept(path: Path, bundle_root: Path) -> ParsedDocument:
    text = read_utf8(path)
    metadata, body = split_frontmatter(text)
    concept_id = path.relative_to(bundle_root).with_suffix("").as_posix()
    return ParsedDocument(
        path=path,
        concept_id=concept_id,
        metadata=metadata,
        body=body,
        links=markdown_links(body),
    )


def parse_reserved_body(path: Path) -> tuple[dict[str, Any] | None, str, tuple[str, ...]]:
    text = read_utf8(path)
    metadata: dict[str, Any] | None = None
    body = text
    if text.startswith("---"):
        metadata, body = split_frontmatter(text)
    return metadata, body, markdown_links(body)
