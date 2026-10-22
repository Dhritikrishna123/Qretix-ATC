"""Step 1.5 — Sources that cannot be auto-accessed. Logged as explicit provenance gaps, never silently dropped."""
from __future__ import annotations

from typing import Any

from src.decisions import log_decision
from src.provenance import build_record, write_provenance

GAPS = [
    dict(name="COSMIC", status="manual_approval_required", url="https://cancer.sanger.ac.uk/cosmic",
         license="COSMIC licence (registration + acceptance required)",
         notes="Cancer Gene Census requires licence acceptance; cannot be auto-accessed. Flagged as a provenance gap.",
         impact="Novelty checklist item 4 (COSMIC CGC thyroid) and Phase 4 hard negatives (Cancer Gene Census) will use an alternative or be logged as a gap."),
    dict(name="DisGeNET", status="manual_approval_required", url="https://www.disgenet.org",
         license="DisGeNET licence (registration required)",
         notes="Requires registration/API key; flagged as a gap.",
         impact="Novelty checklist item 2 (DisGeNET ATC) will be logged as a gap; Open Targets used instead."),
    dict(name="DrugBank", status="manual_approval_required", url="https://go.drugbank.com",
         license="DrugBank licence (licensed, academic request)",
         notes="Licensed resource; cannot be auto-accessed. ChEMBL + Open Targets used for druggability/pharmacology.",
         impact="Druggability tiers rely on Open Targets tractability + ChEMBL."),
    dict(name="BioGRID", status="skipped", url="https://thebiogrid.org",
         license="MIT (data); free API key required",
         notes="Skipped (API key required). STRING + Reactome provide sufficient PPI coverage.",
         impact="PPI features use STRING (score >= 400) + Reactome only."),
]


def run(force: bool = False, **_: Any) -> list[str]:
    names = []
    for g in GAPS:
        write_provenance(g["name"], build_record(
            source=g["name"], accession="n/a", url=g["url"], modality="knowledge base", platform="n/a",
            license=g["license"], notes=g["notes"], status=g["status"], downstream_impact=g["impact"],
        ))
        log_decision("data gap", f"{g['name']} not acquired ({g['status'].replace('_', ' ')})",
                     f"{g['notes']} Impact: {g['impact']}")
        names.append(g["name"])
    return names
