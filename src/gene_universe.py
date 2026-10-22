"""Step 1.0 — Gene Universe: canonical HGNC <-> Ensembl <-> UniProt <-> Entrez mapping.

Every downstream module joins through :class:`GeneUniverse`; no ad-hoc remapping.
Primary key is the Ensembl Gene ID.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import config
from src.http_utils import download, sha256_file
from src.provenance import build_record, write_provenance

HGNC_RAW = config.DATA_RAW / "hgnc" / "hgnc_complete_set.txt"

COLUMNS = [
    "ensembl_gene_id", "hgnc_id", "symbol", "name", "entrez_id",
    "uniprot_id", "uniprot_ids", "aliases", "previous_symbols",
]


def _split(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


def build_gene_universe(raw: pd.DataFrame) -> pd.DataFrame:
    """Filter an HGNC complete-set table to approved protein-coding genes with Ensembl IDs."""
    df = raw[(raw["locus_group"] == "protein-coding gene") & (raw["status"] == "Approved")].copy()
    df = df[df["ensembl_gene_id"].notna() & (df["ensembl_gene_id"] != "")]
    df = df.drop_duplicates("ensembl_gene_id")

    uniprots = df["uniprot_ids"].map(_split)
    out = pd.DataFrame(
        {
            "ensembl_gene_id": df["ensembl_gene_id"].values,
            "hgnc_id": df["hgnc_id"].values,
            "symbol": df["symbol"].values,
            "name": df["name"].values,
            "entrez_id": pd.to_numeric(df["entrez_id"], errors="coerce").astype("Int64").values,
            "uniprot_id": uniprots.map(lambda x: x[0] if x else None).values,
            "uniprot_ids": uniprots.map("|".join).values,
            "aliases": df["alias_symbol"].map(lambda v: "|".join(_split(v))).values,
            "previous_symbols": df["prev_symbol"].map(lambda v: "|".join(_split(v))).values,
        }
    )
    out["uniprot_ids"] = out["uniprot_ids"].replace("", None)
    return out[COLUMNS].sort_values("symbol").reset_index(drop=True)


def fetch_and_build(force: bool = False) -> pd.DataFrame:
    config.ensure_dirs()
    info = download(config.HGNC_URL, HGNC_RAW, force=force)
    raw = pd.read_csv(HGNC_RAW, sep="\t", dtype=str, low_memory=False)
    universe = build_gene_universe(raw)
    config.GENE_UNIVERSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    universe.to_parquet(config.GENE_UNIVERSE_PATH, index=False)

    coverage = {
        "ensembl_gene_id": int(universe["ensembl_gene_id"].notna().sum()),
        "hgnc_symbol": int(universe["symbol"].notna().sum()),
        "uniprot_id": int(universe["uniprot_id"].notna().sum()),
        "entrez_id": int(universe["entrez_id"].notna().sum()),
    }
    write_provenance(
        "gene_universe",
        build_record(
            source="HGNC",
            accession="hgnc_complete_set",
            url=config.HGNC_URL,
            modality="gene identifier mapping",
            platform="HGNC complete set (TSV)",
            license="CC0 (HGNC data is public domain)",
            sample_count=len(universe),
            raw_files=[str(HGNC_RAW.relative_to(config.ROOT)).replace("\\", "/")],
            checksums={"hgnc_complete_set.txt": "sha256:" + info["sha256"]},
            notes=(
                "Approved protein-coding genes with an Ensembl Gene ID. "
                f"Rows mapped per ID system: {coverage}. Canonical key for every downstream join."
            ),
            is_processed=True,
            qc_thresholds_applied={"locus_group": "protein-coding gene", "status": "Approved",
                                    "requires": "ensembl_gene_id"},
            processed_output="data/processed/gene_universe.parquet",
            processed_sha256="sha256:" + sha256_file(config.GENE_UNIVERSE_PATH),
            id_coverage=coverage,
        ),
    )
    return universe


class GeneUniverse:
    """Lookup helper over ``gene_universe.parquet`` — the only sanctioned ID-mapping path."""

    def __init__(self, path: Path | str = config.GENE_UNIVERSE_PATH) -> None:
        self.df = pd.read_parquet(path)
        self._sym = dict(zip(self.df["symbol"], self.df["ensembl_gene_id"]))
        self._entrez = {int(k): v for k, v in zip(self.df["entrez_id"], self.df["ensembl_gene_id"]) if pd.notna(k)}
        self._uniprot: dict[str, str] = {}
        self._alias: dict[str, str] = {}
        self._prev: dict[str, str] = {}
        for row in self.df.itertuples(index=False):
            for u in (row.uniprot_ids or "").split("|"):
                if u:
                    self._uniprot.setdefault(u, row.ensembl_gene_id)
            for a in (row.aliases or "").split("|"):
                if a:
                    self._alias.setdefault(a, row.ensembl_gene_id)
            for p in (row.previous_symbols or "").split("|"):
                if p:
                    self._prev.setdefault(p, row.ensembl_gene_id)
        self._by_ens = self.df.set_index("ensembl_gene_id")

    def __len__(self) -> int:
        return len(self.df)

    def from_symbol(self, symbol: str) -> str | None:
        """Approved symbol first, then previous symbol, then alias (approved wins on conflict)."""
        s = str(symbol).strip()
        return self._sym.get(s) or self._prev.get(s) or self._alias.get(s)

    def from_entrez(self, entrez: int | str) -> str | None:
        try:
            return self._entrez.get(int(entrez))
        except (TypeError, ValueError):
            return None

    def from_uniprot(self, accession: str) -> str | None:
        return self._uniprot.get(str(accession).strip())

    def symbol(self, ensembl_id: str) -> str | None:
        return self._by_ens["symbol"].get(ensembl_id)

    def uniprot(self, ensembl_id: str) -> str | None:
        v = self._by_ens["uniprot_id"].get(ensembl_id)
        return v if isinstance(v, str) else None


def validate() -> list[str]:
    """Acceptance check: >= 19,000 genes mapped across 4 ID systems."""
    problems: list[str] = []
    if not config.GENE_UNIVERSE_PATH.exists():
        return ["gene_universe.parquet missing"]
    df = pd.read_parquet(config.GENE_UNIVERSE_PATH)
    if len(df) < config.MIN_GENES_IN_UNIVERSE:
        problems.append(f"gene universe has {len(df)} rows (< {config.MIN_GENES_IN_UNIVERSE})")
    if not df["ensembl_gene_id"].is_unique:
        problems.append("ensembl_gene_id is not unique")
    for col in ("ensembl_gene_id", "symbol", "uniprot_id", "entrez_id"):
        frac = df[col].notna().mean()
        if frac < 0.9:
            problems.append(f"only {frac:.1%} of genes have {col}")
    return problems
