"""Step 1.4 — DepMap (high priority).

Downloads CRISPR gene effect (Chronos), model metadata, expression, CN and mutation tables, then
builds ``data/processed/depmap_atc_dependency.csv`` (one row per gene per authenticated ATC line).
"""
from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd

from src import config
from src.decisions import log_decision
from src.http_utils import download, request
from src.provenance import build_record, checksums_for, write_provenance
from src.gene_universe import GeneUniverse

FILES = [
    "CRISPRGeneEffect.csv",
    "Model.csv",
    "OmicsExpressionProteinCodingGenesTPMLogp1.csv",
    "OmicsCNGene.csv",
    "OmicsSomaticMutations.csv",
]
OUT_CSV = config.DATA_PROCESSED / "depmap_atc_dependency.csv"


def normalise(name: object) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(name).upper())


def release_sort_key(release: str) -> tuple[int, int]:
    m = re.search(r"(\d{2})Q(\d)", release)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def resolve_release(catalog: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Latest public release that contains every required file."""
    pub = catalog[catalog["release"].str.contains("DepMap Public", na=False)]
    for rel in sorted(pub["release"].unique(), key=release_sort_key, reverse=True):
        sub = pub[pub["release"] == rel]
        if set(FILES) <= set(sub["filename"]):
            return rel, sub
    raise RuntimeError("No DepMap Public release contains all required files")


def select_atc_models(models: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (authenticated ATC lines, excluded ATC-labelled lines with reasons)."""
    lineage_ok = models["OncotreeLineage"].astype(str).str.contains("Thyroid", case=False)
    subtype_ok = models["OncotreeSubtype"].astype(str).str.contains("Anaplastic", case=False)
    named = models.copy()
    keys = named[["CellLineName", "StrippedCellLineName"]].apply(lambda col: col.map(normalise))
    named["_match"] = [
        next((k for k in (a, b) if k in config.AUTHENTICATED_ATC_LINES or k in config.CONTAMINATED_ATC_LINES), a)
        for a, b in zip(keys["CellLineName"], keys["StrippedCellLineName"])
    ]
    contaminated = named["_match"].isin(config.CONTAMINATED_ATC_LINES)
    authentic = named["_match"].isin(config.AUTHENTICATED_ATC_LINES)
    candidates = named[(lineage_ok & subtype_ok) | authentic | contaminated]

    keep = candidates[authentic.loc[candidates.index] & ~contaminated.loc[candidates.index]].copy()
    drop = candidates.drop(index=keep.index).copy()
    drop["exclusion_reason"] = [
        "known cross-contaminated/misidentified line (Schweppe 2008)" if m in config.CONTAMINATED_ATC_LINES
        else "ATC-labelled in DepMap but not in authenticated ATC list"
        for m in drop["_match"]
    ]
    return keep, drop


def build_dependency_table(gene_effect: pd.DataFrame, atc_models: pd.DataFrame, universe: GeneUniverse) -> pd.DataFrame:
    """Long table: one row per gene per authenticated ATC line, mapped through the Gene Universe."""
    id_col = gene_effect.columns[0]
    ge = gene_effect.set_index(id_col)
    ge = ge.loc[ge.index.intersection(atc_models["ModelID"])]
    long = ge.reset_index().melt(id_vars=id_col, var_name="gene", value_name="chronos_gene_effect")
    long = long.rename(columns={id_col: "model_id"}).dropna(subset=["chronos_gene_effect"])
    parsed = long["gene"].str.extract(r"^(?P<hgnc_symbol>[^ ]+) \((?P<entrez_id>\d+)\)$")
    long = pd.concat([long.drop(columns="gene"), parsed], axis=1)
    long["ensembl_gene_id"] = [
        universe.from_entrez(e) or universe.from_symbol(s)
        for e, s in zip(long["entrez_id"], long["hgnc_symbol"])
    ]
    names = atc_models.set_index("ModelID")["CellLineName"]
    long["cell_line"] = long["model_id"].map(names)
    long["platform"] = "CRISPR-Cas9 (Chronos)"
    long["batch"] = "DepMap release"
    cols = ["model_id", "cell_line", "ensembl_gene_id", "hgnc_symbol", "entrez_id",
            "chronos_gene_effect", "platform", "batch"]
    return long[cols].sort_values(["cell_line", "hgnc_symbol"]).reset_index(drop=True)


REQUIRED_LOCAL = ("Model.csv", "CRISPRGeneEffect.csv")
MANUAL_INSTRUCTIONS = (
    "Download from https://depmap.org/portal/data_page/?tab=allData (latest DepMap Public release) "
    f"and place {', '.join(FILES)} in data/raw/DepMap/, then re-run `python -m src.pipeline --phase 1 --only depmap`."
)


def acquire_files(out_dir, force: bool = False) -> tuple[str, list]:
    """Return (release label, local paths). Uses files already in ``out_dir``; otherwise the DepMap
    file catalog. The catalog sits behind a bot-verification page for scripted clients, in which case
    we raise ``DepMapBlocked`` rather than try to bypass it."""
    local = [out_dir / f for f in FILES]
    if all((out_dir / f).exists() for f in REQUIRED_LOCAL) and not force:
        release_file = out_dir / "RELEASE.txt"
        label = release_file.read_text().strip() if release_file.exists() else "DepMap Public (manually supplied)"
        return label, [p for p in local if p.exists()]
    resp = request("GET", config.DEPMAP_FILES_API)
    text = resp.text
    if "text/csv" not in resp.headers.get("content-type", "") and not text.lstrip().startswith("release"):
        raise DepMapBlocked("DepMap file catalog returned a verification page instead of CSV")
    catalog = pd.read_csv(io.StringIO(text))
    release, sub = resolve_release(catalog)
    paths = []
    for fn in FILES:
        url = sub.loc[sub["filename"] == fn, "url"].iloc[0]
        paths.append(download(url, out_dir / fn, force=force)["path"])
    (out_dir / "RELEASE.txt").write_text(release)
    return release, paths


class DepMapBlocked(RuntimeError):
    pass


def run(force: bool = False, **_: Any) -> list[str]:
    out_dir = config.DATA_RAW / "DepMap"
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        release, paths = acquire_files(out_dir, force=force)
    except DepMapBlocked as exc:
        log_decision("data gap", "DepMap not auto-downloadable (bot verification)",
                     f"{exc}. The depmap_atc_dependency.csv output is pending. {MANUAL_INSTRUCTIONS}")
        write_provenance("DepMap", build_record(
            source="DepMap Portal", accession="pending manual download",
            url="https://depmap.org/portal/data_page/?tab=allData", modality="CRISPR dependency + omics (cell lines)",
            platform="CRISPR-Cas9 Chronos", license="CC BY 4.0", status="manual_approval_required",
            notes=f"Automated download blocked by DepMap bot verification. {MANUAL_INSTRUCTIONS}"))
        return ["DepMap"]

    models = pd.read_csv(out_dir / "Model.csv")
    atc, excluded = select_atc_models(models)
    atc.drop(columns="_match").to_csv(config.DATA_PROCESSED / "depmap_atc_models.csv", index=False)
    missing = sorted(config.AUTHENTICATED_ATC_LINES - set(atc["_match"]))
    if missing:
        log_decision("data gap", "Authenticated ATC lines absent from DepMap",
                     f"{', '.join(missing)} are not in {release}; {len(atc)} authenticated ATC lines available.")
    if len(excluded):
        log_decision("data cleaning", "DepMap ATC-labelled lines excluded",
                     "; ".join(f"{r.CellLineName} ({r.exclusion_reason})" for r in excluded.itertuples()))

    universe = GeneUniverse()
    ge = pd.read_csv(out_dir / "CRISPRGeneEffect.csv")
    dep = build_dependency_table(ge, atc, universe)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    dep.to_csv(OUT_CSV, index=False)

    write_provenance("DepMap", build_record(
        source="DepMap Portal", accession=release, url="https://depmap.org/portal/data_page/",
        sample_count=int(len(atc)), modality="CRISPR dependency + omics (cell lines)",
        platform="CRISPR-Cas9 Chronos; expression TPM log2(x+1); CN; somatic mutations",
        license="CC BY 4.0",
        raw_files=FILES, checksums=checksums_for(paths, out_dir),
        notes=(f"Release {release}. {len(atc)} authenticated ATC lines retained "
               f"({', '.join(sorted(atc['CellLineName']))}); {len(excluded)} ATC-labelled lines excluded."),
        qc_thresholds_applied={"lineage": "Thyroid", "subtype": "contains Anaplastic",
                               "authenticated_only": True,
                               "excluded_contaminated": sorted(config.CONTAMINATED_ATC_LINES)},
        is_processed=True,
        processed_output="data/processed/depmap_atc_dependency.csv",
        excluded_lines=excluded[["ModelID", "CellLineName", "exclusion_reason"]].to_dict("records"),
    ))
    return ["DepMap"]
