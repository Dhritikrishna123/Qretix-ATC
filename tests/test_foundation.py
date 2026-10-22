import pandas as pd

from src.gene_universe import build_gene_universe
from src.provenance import REQUIRED_FIELDS, build_record, validate_record
from src.decisions import log_decision


def _hgnc(rows):
    cols = ["hgnc_id", "symbol", "name", "locus_group", "status", "entrez_id",
            "ensembl_gene_id", "uniprot_ids", "alias_symbol", "prev_symbol"]
    return pd.DataFrame(rows, columns=cols)


def test_gene_universe_filters_and_maps():
    raw = _hgnc([
        ["HGNC:1097", "BRAF", "B-Raf", "protein-coding gene", "Approved", "673", "ENSG00000157764", "P15056", "NS7|BRAF1", "RAFB1"],
        ["HGNC:1", "NCRNA", "x", "non-coding RNA", "Approved", "1", "ENSG1", "", "", ""],
        ["HGNC:2", "OLD", "x", "protein-coding gene", "Symbol Withdrawn", "2", "ENSG2", "", "", ""],
        ["HGNC:3", "NOENS", "x", "protein-coding gene", "Approved", "3", "", "", "", ""],
    ])
    uni = build_gene_universe(raw)
    assert list(uni["symbol"]) == ["BRAF"]
    row = uni.iloc[0]
    assert row["ensembl_gene_id"] == "ENSG00000157764"
    assert row["uniprot_id"] == "P15056"
    assert int(row["entrez_id"]) == 673
    assert "NS7" in row["aliases"] and row["previous_symbols"] == "RAFB1"


def test_provenance_schema_validation():
    rec = build_record(source="s", accession="a", url="u", modality="m", platform="p",
                       license="l", notes="n", sample_count=3)
    assert validate_record(rec) == []
    assert set(REQUIRED_FIELDS) <= set(rec)
    rec["url"] = None
    assert validate_record(rec)


def test_decision_log_is_idempotent(tmp_path, monkeypatch):
    from src import config
    monkeypatch.setattr(config, "DOCS", tmp_path)
    monkeypatch.setattr(config, "DECISIONS_LOG", tmp_path / "decisions_log.md")
    assert log_decision("gap", "COSMIC", "manual") is True
    assert log_decision("gap", "COSMIC", "manual") is False
    assert (tmp_path / "decisions_log.md").read_text().count("### COSMIC") == 1
