"""Append-only, idempotent writer for ``docs/decisions_log.md``."""
from __future__ import annotations

from datetime import date

from src import config

HEADER = (
    "# Decisions Log\n\n"
    "Data gaps, deviations and judgement calls made while building QRETIX-ATC. "
    "Entries are appended automatically by the pipeline and can be edited by hand.\n"
)


def log_decision(category: str, title: str, detail: str) -> bool:
    """Append an entry unless one with the same title already exists. Returns True if written."""
    config.DOCS.mkdir(parents=True, exist_ok=True)
    path = config.DECISIONS_LOG
    text = path.read_text(encoding="utf-8") if path.exists() else HEADER
    marker = f"### {title}"
    if marker in text:
        return False
    entry = f"\n{marker}\n\n- **Category:** {category}\n- **Date:** {date.today().isoformat()}\n- **Detail:** {detail}\n"
    path.write_text(text.rstrip("\n") + "\n" + entry, encoding="utf-8")
    return True
