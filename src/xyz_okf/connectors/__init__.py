"""Source connector contracts for OKF producers."""

from xyz_okf.connectors.base import (
    ChangeBatch,
    ChangeKind,
    KnowledgeSource,
    SourceChange,
    SourceRecord,
)

__all__ = [
    "ChangeBatch",
    "ChangeKind",
    "KnowledgeSource",
    "SourceChange",
    "SourceRecord",
]
