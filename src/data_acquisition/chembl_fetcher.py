"""Step 1.5 — ChEMBL: existing modulators (mechanism of action + IC50) for top candidate targets.

Candidates = top Open Targets ATC associations + the known ATC driver list.
"""
from __future__ import annotations

import json
from typing import Any

from src import config
from src.gene_universe import GeneUniverse
from src.http_utils import get_json
from src.provenance import build_record, checksums_for, write_provenance

KNOWN_ATC_DRIVERS = [
    "BRAF", "TP53", "TERT", "NRAS", "HRAS", "KRAS", "PIK3CA", "PTEN", "CDKN2A", "NF1",
    "EIF1AX", "AKT1", "NF2", "RB1", "ATM", "ARID1A", "MAP2K1", "RET", "NTRK1",
]
TOP_N_OPENTARGETS = 100
MAX_ACTIVITY_PAGES = 5


def chembl(path: str, **params: Any) -> dict[str, Any]:
    return get_json(f"{config.CHEMBL_API}/{path}.json", params=params)


def candidate_symbols() -> list[str]:
    syms = list(KNOWN_ATC_DRIVERS)
    ot = config.DATA_RAW / "OpenTargets" / "atc_associated_targets.json"
    if ot.exists():
        rows = json.loads(ot.read_text(encoding="utf-8"))["rows"]
        rows = sorted(rows, key=lambda r: r["score"], reverse=True)[:TOP_N_OPENTARGETS]
        syms += [r["target"]["approvedSymbol"] for r in rows]
    return list(dict.fromkeys(syms))


def fetch_target(symbol: str, uniprot: str | None) -> dict[str, Any]:
    rec: dict[str, Any] = {"symbol": symbol, "uniprot": uniprot, "target_chembl_id": None,
                           "mechanisms": [], "ic50_activities": [], "n_ic50_total": 0}
    if not uniprot:
        return rec
    targets = chembl("target", target_components__accession=uniprot, limit=5).get("targets", [])
    single = [t for t in targets if t.get("target_type") == "SINGLE PROTEIN"] or targets
    if not single:
        return rec
    tid = single[0]["target_chembl_id"]
    rec["target_chembl_id"] = tid
    for m in chembl("mechanism", target_chembl_id=tid, limit=100).get("mechanisms", []):
        rec["mechanisms"].append({k: m.get(k) for k in ("molecule_chembl_id", "mechanism_of_action", "action_type", "max_phase")})
    offset = 0
    for _ in range(MAX_ACTIVITY_PAGES):
        page = chembl("activity", target_chembl_id=tid, standard_type="IC50", limit=1000, offset=offset)
        rec["n_ic50_total"] = page["page_meta"]["total_count"]
        for a in page.get("activities", []):
            rec["ic50_activities"].append({k: a.get(k) for k in (
                "molecule_chembl_id", "standard_value", "standard_units", "standard_relation", "assay_chembl_id", "document_year")})
        if not page["page_meta"].get("next"):
            break
        offset += 1000
    return rec


def run(force: bool = False, **_: Any) -> list[str]:
    out_dir = config.DATA_RAW / "ChEMBL"
    out_dir.mkdir(parents=True, exist_ok=True)
    uni = GeneUniverse()
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for sym in candidate_symbols():
        ens = uni.from_symbol(sym)
        try:
            results.append(fetch_target(sym, uni.uniprot(ens) if ens else None))
        except Exception as exc:
            failures.append(f"{sym}: {exc}")
    path = out_dir / "candidate_target_modulators.json"
    path.write_text(json.dumps(results, indent=1), encoding="utf-8")
    with_chembl = sum(1 for r in results if r["target_chembl_id"])
    write_provenance("ChEMBL", build_record(
        source="ChEMBL", accession="ChEMBL REST API (current)", url=config.CHEMBL_API,
        sample_count=len(results), modality="pharmacology (mechanisms, IC50)", platform="REST API",
        license="CC BY-SA 3.0",
        raw_files=[path.name], checksums=checksums_for([path], out_dir),
        notes=f"{len(results)} candidate targets queried ({with_chembl} with a ChEMBL target); "
              f"IC50 activities capped at {MAX_ACTIVITY_PAGES * 1000} per target. "
              f"{len(failures)} lookups failed." + (f" Failures: {failures[:5]}" if failures else ""),
        failures=failures,
    ))
    return ["ChEMBL"]
