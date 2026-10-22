"""Step 1.6 — PubMed corpora (ATC-specific and broad thyroid) via E-utilities.

Every record stores its publication date (+ precision) — required for Phase 7 temporal splits.
Queries are split per publication year so every esearch result set stays below the 10k cap.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any, Iterable

from src import config
from src.http_utils import ncbi_get
from src.provenance import build_record, checksums_for, utcnow, write_provenance

BATCH = 200
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _text(el: ET.Element | None) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_pub_date(article: ET.Element) -> tuple[str | None, str]:
    """Return (ISO date string, precision in {'day','month','year',None}).

    Preference: ArticleDate (electronic, usually day precision) > PubDate > MedlineDate.
    """
    ad = article.find(".//Article/ArticleDate")
    if ad is not None and _text(ad.find("Year")):
        y, m, d = (_text(ad.find(k)) for k in ("Year", "Month", "Day"))
        if y and m and d:
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}", "day"
    pd_ = article.find(".//Article/Journal/JournalIssue/PubDate")
    if pd_ is not None:
        y = _text(pd_.find("Year"))
        if y:
            m = _text(pd_.find("Month")).lower()[:3]
            mnum = int(m) if m.isdigit() else MONTHS.get(m)
            d = _text(pd_.find("Day"))
            if mnum and d.isdigit():
                return f"{int(y):04d}-{mnum:02d}-{int(d):02d}", "day"
            if mnum:
                return f"{int(y):04d}-{mnum:02d}", "month"
            return f"{int(y):04d}", "year"
        medline = _text(pd_.find("MedlineDate"))
        if medline[:4].isdigit():
            return medline[:4], "year"
    return None, "none"


def parse_articles(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    out: list[dict[str, Any]] = []
    for pa in root.findall(".//PubmedArticle"):
        pmid = _text(pa.find(".//MedlineCitation/PMID"))
        pub_date, precision = parse_pub_date(pa)
        authors = pa.findall(".//AuthorList/Author")
        affils = [_text(a.find(".//AffiliationInfo/Affiliation")) for a in authors]
        out.append({
            "pmid": pmid,
            "title": _text(pa.find(".//Article/ArticleTitle")),
            "abstract": " ".join(_text(t) for t in pa.findall(".//Article/Abstract/AbstractText")),
            "publication_date": pub_date,
            "date_precision": precision,
            "journal": _text(pa.find(".//Article/Journal/Title")),
            "mesh": [_text(m) for m in pa.findall(".//MeshHeadingList/MeshHeading/DescriptorName")],
            "publication_types": [_text(t) for t in pa.findall(".//PublicationTypeList/PublicationType")],
            # last-author affiliation approximates corresponding-author lab (used for evidence independence)
            "first_author_affiliation": affils[0] if affils else "",
            "last_author_affiliation": affils[-1] if affils else "",
        })
    return out


def esearch_ids(term: str) -> list[str]:
    res = ncbi_get("esearch.fcgi", {"db": "pubmed", "term": term, "retmax": 9999, "retmode": "json"}, as_json=True)["esearchresult"]
    if int(res["count"]) > 9999:
        raise RuntimeError(f"Result set too large to enumerate for term (count={res['count']}): {term}")
    return res["idlist"]


def fetch_ids(ids: Iterable[str]) -> list[dict[str, Any]]:
    ids = list(ids)
    recs: list[dict[str, Any]] = []
    for i in range(0, len(ids), BATCH):
        xml = ncbi_get("efetch.fcgi", {"db": "pubmed", "id": ",".join(ids[i:i + BATCH]), "retmode": "xml"}).content
        recs.extend(parse_articles(xml))
    return recs


def build_corpus(query: str, start_year: int, end_year: int) -> list[dict[str, Any]]:
    by_pmid: dict[str, dict[str, Any]] = {}
    for year in range(start_year, end_year + 1):
        ids = esearch_ids(f"({query}) AND {year}[dp]")
        new = [i for i in ids if i not in by_pmid]
        for rec in fetch_ids(new):
            by_pmid[rec["pmid"]] = rec
    return sorted(by_pmid.values(), key=lambda r: (r["publication_date"] or "", r["pmid"]))


def run(force: bool = False, start_year: int = 1950, broad: bool = True, **_: Any) -> list[str]:
    config.LITERATURE.mkdir(parents=True, exist_ok=True)
    end_year = date.today().year
    jobs = [("atc_pubmed_corpus", "PubMed_ATC", config.PUBMED_ATC_QUERY, "ATC-specific")]
    if broad:
        jobs.append(("thyroid_pubmed_corpus", "PubMed_Thyroid", config.PUBMED_THYROID_QUERY, "broad thyroid"))
    names = []
    for stem, prov, query, label in jobs:
        path = config.LITERATURE / f"{stem}.json"
        if path.exists() and not force:
            corpus = json.loads(path.read_text(encoding="utf-8"))["articles"]
        else:
            corpus = build_corpus(query, start_year, end_year)
            path.write_text(json.dumps({"query": query, "date_pulled": utcnow(), "articles": corpus},
                                       ensure_ascii=False), encoding="utf-8")
        dated = sum(1 for r in corpus if r["publication_date"])
        write_provenance(prov, build_record(
            source="PubMed (NCBI E-utilities)", accession=f"query: {query}",
            url=f"https://pubmed.ncbi.nlm.nih.gov/?term={query.replace(' ', '+')}",
            sample_count=len(corpus), modality="literature", platform="PubMed XML",
            license="NLM data (public; abstracts retain publisher copyright)",
            raw_files=[str(path.relative_to(config.ROOT)).replace("\\", "/")],
            checksums=checksums_for([path], config.ROOT),
            notes=f"{label} corpus: {len(corpus):,} articles, {dated:,} with publication dates "
                  "(PMID, title, abstract, date, journal, MeSH, author affiliations). Dates preserved per record for Phase 7.",
            query=query, years=[start_year, end_year], records_with_date=dated,
        ))
        names.append(prov)
    return names
