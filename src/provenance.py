"""Provenance tracker: one JSON record per dataset in ``data/provenance/``."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src import config
from src.http_utils import sha256_file

# Schema applied to every dataset (see Implementation Plan, Phase 1.1).
REQUIRED_FIELDS = [
    "source", "accession", "url", "date_pulled", "sample_count", "modality",
    "platform", "license", "raw_files", "checksums", "notes",
    "qc_thresholds_applied", "is_processed",
]
# Fields that may legitimately be null for raw (un-QC'd) data.
NULLABLE_FIELDS = {"qc_thresholds_applied"}
# Status values: ok | manual_approval_required | skipped | not_available | failed
OK_STATUSES = {"ok"}
GAP_STATUSES = {"manual_approval_required", "skipped", "not_available"}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def checksums_for(paths: list[Path], base: Path | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in paths:
        p = Path(p)
        key = str(p.relative_to(base)) if base else p.name
        out[key.replace("\\", "/")] = "sha256:" + sha256_file(p)
    return out


def build_record(
    *,
    source: str,
    accession: str,
    url: str,
    modality: str,
    platform: str,
    license: str,
    notes: str,
    sample_count: int | str | None = None,
    raw_files: list[str] | None = None,
    checksums: dict[str, str] | None = None,
    qc_thresholds_applied: Any = None,
    is_processed: bool = False,
    status: str = "ok",
    **extra: Any,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "source": source,
        "accession": accession,
        "url": url,
        "date_pulled": utcnow(),
        "sample_count": sample_count if sample_count is not None else "n/a",
        "modality": modality,
        "platform": platform,
        "license": license,
        "raw_files": raw_files or [],
        "checksums": checksums or {},
        "notes": notes,
        "qc_thresholds_applied": qc_thresholds_applied,
        "is_processed": is_processed,
        "status": status,
    }
    rec.update(extra)
    return rec


def write_provenance(name: str, record: dict[str, Any]) -> Path:
    config.DATA_PROVENANCE.mkdir(parents=True, exist_ok=True)
    path = config.DATA_PROVENANCE / f"{name}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False, default=str)
        fh.write("\n")
    return path


def load_provenance(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def iter_provenance() -> list[tuple[str, dict[str, Any]]]:
    return [
        (p.stem, load_provenance(p))
        for p in sorted(config.DATA_PROVENANCE.glob("*.json"))
    ]


def validate_record(rec: dict[str, Any]) -> list[str]:
    """Return a list of problems; empty means the record satisfies the schema."""
    problems: list[str] = []
    for f in REQUIRED_FIELDS:
        if f not in rec:
            problems.append(f"missing field '{f}'")
        elif rec[f] is None and f not in NULLABLE_FIELDS:
            problems.append(f"field '{f}' is null")
        elif rec[f] == "" and f not in NULLABLE_FIELDS:
            problems.append(f"field '{f}' is empty")
    if rec.get("status") == "failed":
        problems.append("acquisition failed: " + str(rec.get("error", "unknown error")))
    return problems
