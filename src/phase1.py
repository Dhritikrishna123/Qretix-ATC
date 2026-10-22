"""Phase 1 — Data Inventory & Acquisition: ordered task list, run() and validate()."""
from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from src import config, gene_universe, provenance
from src.data_acquisition import (
    cbioportal_fetcher, chembl_fetcher, clinicaltrials_fetcher, depmap_fetcher, encode_fetcher,
    geo_fetcher, manual_gaps, opentargets_fetcher, pride_fetcher, pubmed_fetcher, reactome_fetcher,
    string_fetcher, uniprot_fetcher,
)
from src.decisions import log_decision
from src.docs_builder import write_dataset_inventory

NAME = "phase1_data_acquisition"
DEPENDS_ON: list[str] = []
CONFIG: dict[str, Any] = {"force": False, "gdc_download": False, "supplementary": True, "broad_pubmed": True}


@dataclass(frozen=True)
class Task:
    key: str
    step: str
    fn: Callable[..., list[str]]


def _gene_universe(force: bool = False, **_: Any) -> list[str]:
    gene_universe.fetch_and_build(force=force)
    return ["gene_universe"]


# Execution order from the plan (dependency + priority): universe -> DepMap early -> the rest.
TASKS: list[Task] = [
    Task("gene_universe", "1.0", _gene_universe),
    Task("depmap", "1.4", depmap_fetcher.run),
    Task("geo", "1.1", geo_fetcher.run),
    Task("cbioportal_gdc", "1.2", cbioportal_fetcher.run),
    Task("encode", "1.3", encode_fetcher.run),
    Task("pride", "1.3", pride_fetcher.run),
    Task("string", "1.5", string_fetcher.run),
    Task("uniprot", "1.5", uniprot_fetcher.run),
    Task("reactome_go", "1.5", reactome_fetcher.run),
    Task("opentargets", "1.5", opentargets_fetcher.run),
    Task("chembl", "1.5", chembl_fetcher.run),  # after Open Targets: candidate list depends on it
    Task("manual_gaps", "1.5", manual_gaps.run),
    Task("pubmed", "1.6", lambda **kw: pubmed_fetcher.run(broad=kw.get("broad_pubmed", True), **kw)),
    Task("clinicaltrials", "1.6", clinicaltrials_fetcher.run),
]


def run(only: list[str] | None = None, skip: list[str] | None = None, **opts: Any) -> dict[str, str]:
    """Run tasks (all by default). Failures are recorded as provenance + decisions, then the run continues."""
    config.ensure_dirs()
    cfg = {**CONFIG, **opts}
    status: dict[str, str] = {}
    for t in TASKS:
        if (only and t.key not in only) or (skip and t.key in skip):
            continue
        print(f"[phase1] {t.step} {t.key} ...", flush=True)
        try:
            t.fn(**cfg)
            status[t.key] = "ok"
        except Exception as exc:  # noqa: BLE001 - continue so one outage cannot block the inventory
            status[t.key] = f"FAILED: {exc}"
            traceback.print_exc()
            provenance.write_provenance(f"FAILED_{t.key}", provenance.build_record(
                source=t.key, accession="n/a", url="n/a", modality="n/a", platform="n/a", license="n/a",
                notes=f"Acquisition step {t.step} failed.", status="failed", error=str(exc)))
            log_decision("acquisition failure", f"{t.key} failed", f"Step {t.step}: {exc}")
    write_dataset_inventory()
    print(json.dumps(status, indent=2))
    return status


def validate() -> list[str]:
    """Phase 1 acceptance criteria. Empty list means all criteria pass."""
    problems = [f"gene_universe: {p}" for p in gene_universe.validate()]

    records = provenance.iter_provenance()
    if not records:
        problems.append("data/provenance/ is empty")
    for name, rec in records:
        problems += [f"provenance/{name}.json: {p}" for p in provenance.validate_record(rec)]
    required = {"gene_universe", "GSE193581", "GSE76039", "GSM7030310_verification", "geo_search_results", "DepMap"}
    present = {n for n, _ in records}
    problems += [f"provenance/{n}.json missing" for n in sorted(required - present)]

    for f in (config.DATASET_INVENTORY, config.DECISIONS_LOG):
        if not f.exists():
            problems.append(f"{f.relative_to(config.ROOT)} missing")

    # No feature/label artifacts may exist yet.
    for d in (config.FEATURES_DIR, config.LABELS_DIR):
        stray = [p.name for p in d.glob("*") if p.name != ".gitkeep"]
        if stray:
            problems.append(f"{d.name}/ must be empty in Phase 1 (found {stray})")
    return problems
