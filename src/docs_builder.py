"""Generate ``docs/dataset_inventory.md`` (human-readable) from the provenance JSON files."""
from __future__ import annotations

from src import config, provenance

STATUS_LABEL = {
    "ok": "Acquired",
    "manual_approval_required": "GAP - manual approval",
    "skipped": "Skipped",
    "not_available": "GAP - not available",
    "failed": "FAILED",
}


def _cell(v: object, limit: int = 140) -> str:
    s = str(v).replace("|", "/").replace("\n", " ").strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def render_inventory() -> str:
    records = provenance.iter_provenance()
    lines = [
        "# Dataset Inventory",
        "",
        "_Auto-generated from `data/provenance/*.json` by `src/docs_builder.py` — do not edit by hand._",
        "",
        "| Dataset | Source | Accession | Modality | Platform | Samples | Pulled (UTC) | Status | Notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, r in records:
        if "results" in r and name == "geo_search_results":
            r = {**r, "notes": f"{r.get('total_hits', '?')} GDS hits for the ATC query"}
        lines.append("| " + " | ".join([
            f"`{name}`", _cell(r.get("source", "")), _cell(r.get("accession", ""), 60),
            _cell(r.get("modality", ""), 60), _cell(r.get("platform", ""), 60), _cell(r.get("sample_count", "")),
            _cell(str(r.get("date_pulled", ""))[:19], 20),
            STATUS_LABEL.get(r.get("status", "ok"), r.get("status", "")), _cell(r.get("notes", "")),
        ]) + " |")
    gaps = [(n, r) for n, r in records if r.get("status") in provenance.GAP_STATUSES]
    lines += ["", "## Data gaps", ""]
    lines += [f"- **{n}** — {_cell(r.get('notes', ''), 300)}" for n, r in gaps] or ["- none"]
    lines += ["", "See also [`decisions_log.md`](decisions_log.md).", ""]
    return "\n".join(lines)


def write_dataset_inventory() -> None:
    config.DOCS.mkdir(parents=True, exist_ok=True)
    config.DATASET_INVENTORY.write_text(render_inventory(), encoding="utf-8")
