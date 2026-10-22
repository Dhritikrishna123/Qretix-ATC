"""Step 1.5 — Open Targets: ATC (MONDO:0006468) disease-target associations + tractability (GraphQL)."""
from __future__ import annotations

import json
from typing import Any

from src import config
from src.http_utils import request
from src.provenance import build_record, checksums_for, write_provenance

PAGE = 500
QUERY = """
query AtcTargets($efoId: String!, $index: Int!, $size: Int!) {
  disease(efoId: $efoId) {
    id
    name
    associatedTargets(page: {index: $index, size: $size}) {
      count
      rows {
        score
        datatypeScores { id score }
        target {
          id
          approvedSymbol
          tractability { label modality value }
        }
      }
    }
  }
}
"""


def gql(variables: dict[str, Any]) -> dict[str, Any]:
    r = request("POST", config.OPENTARGETS_GQL, json={"query": QUERY, "variables": variables})
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(f"Open Targets GraphQL error: {payload['errors']}")
    return payload["data"]["disease"]


def fetch_all(efo_id: str = config.ATC_MONDO_ID) -> tuple[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    index, name = 0, ""
    while True:
        d = gql({"efoId": efo_id, "index": index, "size": PAGE})
        name = d["name"]
        page = d["associatedTargets"]["rows"]
        rows.extend(page)
        if not page or len(rows) >= d["associatedTargets"]["count"]:
            break
        index += 1
    return name, rows


def run(force: bool = False, **_: Any) -> list[str]:
    out_dir = config.DATA_RAW / "OpenTargets"
    out_dir.mkdir(parents=True, exist_ok=True)
    name, rows = fetch_all()
    path = out_dir / "atc_associated_targets.json"
    path.write_text(json.dumps({"disease": config.ATC_MONDO_ID, "name": name, "rows": rows}), encoding="utf-8")
    above = sum(1 for r in rows if r["score"] > 0.5)
    write_provenance("OpenTargets", build_record(
        source="Open Targets Platform", accession=config.ATC_MONDO_ID.replace("_", ":"),
        url=config.OPENTARGETS_GQL, sample_count=len(rows),
        modality="disease-target associations + tractability", platform="GraphQL API v4",
        license="CC0 1.0", raw_files=[path.name], checksums=checksums_for([path], out_dir),
        notes=f"'{name}': {len(rows):,} associated targets ({above} with overall score > 0.5, used in the Phase 6 novelty checklist). "
              "Replaces DrugBank/DisGeNET for druggability and association evidence.",
        disease_name=name,
    ))
    return ["OpenTargets"]
