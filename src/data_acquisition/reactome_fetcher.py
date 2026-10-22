"""Step 1.5 — Reactome pathway membership (ReactomePathways.gmt) and Gene Ontology (go.obo + goa_human.gaf)."""
from __future__ import annotations

import zipfile
from typing import Any

from src import config
from src.http_utils import download
from src.provenance import build_record, checksums_for, write_provenance


def fetch_reactome(force: bool = False) -> str:
    out_dir = config.DATA_RAW / "Reactome"
    zpath = download(config.REACTOME_GMT, out_dir / "ReactomePathways.gmt.zip", force=force)["path"]
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(out_dir)
    gmt = out_dir / "ReactomePathways.gmt"
    n = sum(1 for _ in open(gmt, encoding="utf-8"))
    write_provenance("Reactome", build_record(
        source="Reactome", accession="ReactomePathways.gmt (current)", url=config.REACTOME_GMT,
        sample_count=n, modality="pathway membership", platform="GMT gene sets (HGNC symbols)",
        license="CC0 1.0", raw_files=[gmt.name, zpath.name], checksums=checksums_for([gmt, zpath], out_dir),
        notes=f"{n:,} pathways for all human genes. Symbols mapped via Gene Universe.",
    ))
    return "Reactome"


def fetch_go(force: bool = False) -> str:
    out_dir = config.DATA_RAW / "GeneOntology"
    obo = download(config.GO_OBO, out_dir / "go.obo", force=force)["path"]
    gaf = download(config.GOA_HUMAN_GAF, out_dir / "goa_human.gaf.gz", force=force)["path"]
    version = next((l.split(":", 1)[1].strip() for l in open(obo, encoding="utf-8") if l.startswith("data-version:")), "unknown")
    write_provenance("GeneOntology", build_record(
        source="Gene Ontology Consortium", accession=f"go.obo {version}", url=config.GO_OBO,
        sample_count="n/a", modality="ontology + gene annotations", platform="OBO + GAF 2.2",
        license="CC BY 4.0", raw_files=[obo.name, gaf.name], checksums=checksums_for([obo, gaf], out_dir),
        notes=f"go.obo ({version}) and goa_human.gaf annotations (static downloads).",
    ))
    return "GeneOntology"


def run(force: bool = False, **_: Any) -> list[str]:
    return [fetch_reactome(force), fetch_go(force)]
