"""Step 1.5 — STRING: full human PPI network (bulk download, combined score >= 400 applied downstream)."""
from __future__ import annotations

import gzip
from typing import Any

from src import config
from src.http_utils import download
from src.provenance import build_record, checksums_for, write_provenance

VERSION = "v12.0"
FILES = {
    "links": f"9606.protein.links.{VERSION}.txt.gz",
    "info": f"9606.protein.info.{VERSION}.txt.gz",
    "aliases": f"9606.protein.aliases.{VERSION}.txt.gz",
}


def count_edges_above(path, min_score: int = config.STRING_MIN_SCORE) -> tuple[int, int]:
    """(total edges, edges with combined_score >= min_score) — streamed, header skipped."""
    total = hi = 0
    with gzip.open(path, "rt") as fh:
        next(fh)
        for line in fh:
            total += 1
            if int(line.rsplit(" ", 1)[1]) >= min_score:
                hi += 1
    return total, hi


def run(force: bool = False, **_: Any) -> list[str]:
    out_dir = config.DATA_RAW / "STRING"
    paths = [
        download(f"{config.STRING_BASE}/protein.{kind}.{VERSION}/{name}", out_dir / name, force=force)["path"]
        for kind, name in (("links", FILES["links"]), ("info", FILES["info"]), ("aliases", FILES["aliases"]))
    ]
    total, hi = count_edges_above(paths[0])
    write_provenance("STRING", build_record(
        source="STRING", accession=f"9606 {VERSION}", url="https://string-db.org/cgi/download?species_id=9606",
        sample_count=hi, modality="protein-protein interaction network", platform="STRING combined score",
        license="CC BY 4.0",
        raw_files=[p.name for p in paths], checksums=checksums_for(paths, out_dir),
        notes=(f"Full human PPI. {total:,} directed edges total; {hi:,} with combined_score >= "
               f"{config.STRING_MIN_SCORE} (threshold applied downstream in Phase 3). "
               "STRING + Reactome used instead of BioGRID."),
        total_edges=total, edges_min_score=hi, min_score=config.STRING_MIN_SCORE,
    ))
    return ["STRING"]
