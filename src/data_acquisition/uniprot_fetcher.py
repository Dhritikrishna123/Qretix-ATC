"""Step 1.5 — UniProt: protein features for all reviewed human proteins (REST stream)."""
from __future__ import annotations

import gzip
from typing import Any

from src import config
from src.http_utils import download
from src.provenance import build_record, checksums_for, write_provenance

FIELDS = [
    "accession", "id", "gene_primary", "gene_names", "length", "ft_domain", "xref_pfam",
    "xref_pdb", "ft_mod_res", "ft_carbohyd", "cc_subcellular_location", "ft_transmem", "ft_signal",
]
QUERY = "(organism_id:9606) AND (reviewed:true)"


def run(force: bool = False, **_: Any) -> list[str]:
    out_dir = config.DATA_RAW / "UniProt"
    dest = out_dir / "uniprot_human_reviewed.tsv.gz"
    params = {"query": QUERY, "format": "tsv", "fields": ",".join(FIELDS), "compressed": "true"}
    info = download(config.UNIPROT_STREAM, dest, force=force, params=params)
    with gzip.open(dest, "rt", encoding="utf-8") as fh:
        n = sum(1 for _ in fh) - 1
    write_provenance("UniProt", build_record(
        source="UniProt", accession="UniProtKB/Swiss-Prot human (reviewed)",
        url=f"{config.UNIPROT_STREAM}?query={QUERY}", sample_count=n,
        modality="protein annotation (domains, PTMs, localization, structure cross-refs)",
        platform="UniProt REST API (stream)", license="CC BY 4.0",
        raw_files=[dest.name], checksums={dest.name: "sha256:" + info["sha256"]},
        notes=f"{n:,} reviewed human entries; fields: {', '.join(FIELDS)}. Mapped to genes via Gene Universe in Phase 3.",
        query=QUERY, fields=FIELDS,
    ))
    return ["UniProt"]
