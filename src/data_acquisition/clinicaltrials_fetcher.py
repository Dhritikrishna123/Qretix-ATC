"""Step 1.6 — ClinicalTrials.gov v2: ATC trials with start dates (for Phase 4 labels + Phase 7 splits)."""
from __future__ import annotations

import json
from typing import Any

from src import config
from src.http_utils import get_json
from src.provenance import build_record, checksums_for, utcnow, write_provenance

CONDITION = "Anaplastic Thyroid Cancer"


def parse_study(s: dict[str, Any]) -> dict[str, Any]:
    p = s.get("protocolSection", {})
    ident, status = p.get("identificationModule", {}), p.get("statusModule", {})
    design = p.get("designModule", {})
    arms = p.get("armsInterventionsModule", {})
    return {
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "phase": design.get("phases", []),
        "status": status.get("overallStatus"),
        "study_start_date": status.get("startDateStruct", {}).get("date"),
        "primary_completion_date": status.get("primaryCompletionDateStruct", {}).get("date"),
        "completion_date": status.get("completionDateStruct", {}).get("date"),
        "first_posted_date": status.get("studyFirstPostDateStruct", {}).get("date"),
        "conditions": p.get("conditionsModule", {}).get("conditions", []),
        "interventions": [{"name": i.get("name"), "type": i.get("type")} for i in arms.get("interventions", [])],
        "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
    }


def fetch_studies() -> list[dict[str, Any]]:
    studies: list[dict[str, Any]] = []
    params: dict[str, Any] = {"query.cond": CONDITION, "pageSize": 100, "countTotal": "true"}
    while True:
        page = get_json(config.CTGOV_API, params=params)
        studies.extend(parse_study(s) for s in page.get("studies", []))
        token = page.get("nextPageToken")
        if not token:
            return studies
        params["pageToken"] = token


def run(force: bool = False, **_: Any) -> list[str]:
    config.LITERATURE.mkdir(parents=True, exist_ok=True)
    studies = fetch_studies()
    path = config.LITERATURE / "atc_clinical_trials.json"
    path.write_text(json.dumps({"query": f"query.cond={CONDITION}", "date_pulled": utcnow(), "studies": studies},
                               indent=1, ensure_ascii=False), encoding="utf-8")
    dated = sum(1 for s in studies if s["study_start_date"])
    write_provenance("ClinicalTrials", build_record(
        source="ClinicalTrials.gov API v2", accession=f"query.cond={CONDITION}",
        url=f"{config.CTGOV_API}?query.cond={CONDITION.replace(' ', '+')}", sample_count=len(studies),
        modality="clinical trials", platform="REST API v2 (JSON)", license="Public domain (NLM)",
        raw_files=[str(path.relative_to(config.ROOT)).replace("\\", "/")],
        checksums=checksums_for([path], config.ROOT),
        notes=f"{len(studies)} trials ({dated} with study_start_date): NCT ID, phase, interventions, status, dates.",
        records_with_date=dated,
    ))
    return ["ClinicalTrials"]
