# Dataset Inventory

_Auto-generated from `data/provenance/*.json` by `src/docs_builder.py` — do not edit by hand._

| Dataset | Source | Accession | Modality | Platform | Samples | Pulled (UTC) | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| `AACR_GENIE_ATC` | cBioPortal (AACR GENIE) | genie_public | genomics | n/a | n/a | 2026-10-22T17:03:57 | GAP - not available | GENIE ATC search could not be completed: 404 Client Error: Not Found for url: https://www.cbioportal.org/api/studies/genie_public/clinical-… |
| `BioGRID` | BioGRID | n/a | knowledge base | n/a | n/a | 2026-10-22T17:06:01 | Skipped | Skipped (API key required). STRING + Reactome provide sufficient PPI coverage. |
| `ChEMBL` | ChEMBL | ChEMBL REST API (current) | pharmacology (mechanisms, IC50) | REST API | 103 | 2026-10-22T17:06:01 | Acquired | 103 candidate targets queried (89 with a ChEMBL target); IC50 activities capped at 1000 per target. 0 lookups failed. |
| `ClinicalTrials` | ClinicalTrials.gov API v2 | query.cond=Anaplastic Thyroid Cancer | clinical trials | REST API v2 (JSON) | 110 | 2026-10-22T17:06:03 | Acquired | 110 trials (110 with study_start_date): NCT ID, phase, interventions, status, dates. |
| `COSMIC` | COSMIC | n/a | knowledge base | n/a | n/a | 2026-10-22T17:06:01 | GAP - manual approval | Cancer Gene Census requires licence acceptance; cannot be auto-accessed. Flagged as a provenance gap. |
| `DepMap` | DepMap Portal | DepMap Public (manually supplied) | CRISPR dependency + omics (cell lines) | CRISPR-Cas9 Chronos; expression TPM log2(x+1); CN; somatic … | 7 | 2026-10-22T17:02:29 | Acquired | Release DepMap Public (manually supplied). 7 authenticated ATC lines retained (8305C, 8505C, ASH-3, BHT-101, CAL-62, HTC-C3, MB-1); 6 ATC-l… |
| `DisGeNET` | DisGeNET | n/a | knowledge base | n/a | n/a | 2026-10-22T17:06:01 | GAP - manual approval | Requires registration/API key; flagged as a gap. |
| `DrugBank` | DrugBank | n/a | knowledge base | n/a | n/a | 2026-10-22T17:06:01 | GAP - manual approval | Licensed resource; cannot be auto-accessed. ChEMBL + Open Targets used for druggability/pharmacology. |
| `ENCODE` | ENCODE Project | biosample: thyroid gland | epigenomics (H3K27ac ChIP-seq, ATAC-seq; normal thyroid ref… | ENCODE portal | 75 | 2026-10-22T17:04:05 | Acquired | No ATC biosamples (hits: 0) — absence logged. Normal thyroid reference only; never ATC evidence. |
| `GDC_TCGA-THCA` | NCI GDC | TCGA-THCA | genomics + transcriptomics (PTC reference) | TCGA (STAR counts, masked MAF, masked CNV segments) | 1025 | 2026-10-22T17:04:02 | Acquired | Labelled as PTC / differentiated-thyroid REFERENCE, NOT ATC. Manifest file counts: {'mutations_maf': 498, 'cnv_segments': 1025, 'expression… |
| `gene_universe` | HGNC | hgnc_complete_set | gene identifier mapping | HGNC complete set (TSV) | 19255 | 2026-10-22T17:02:08 | Acquired | Approved protein-coding genes with an Ensembl Gene ID. Rows mapped per ID system: {'ensembl_gene_id': 19255, 'hgnc_symbol': 19255, 'uniprot… |
| `GeneOntology` | Gene Ontology Consortium | go.obo releases/2026-07-26 | ontology + gene annotations | OBO + GAF 2.2 | n/a | 2026-10-22T17:04:28 | Acquired | go.obo (releases/2026-07-26) and goa_human.gaf annotations (static downloads). |
| `geo_search_results` | NCBI GEO DataSets (esearch, db=gds) | query: anaplastic thyroid cancer | dataset enumeration | NCBI E-utilities | 274 | 2026-10-22T17:03:55 | Acquired | 274 GDS hits for the ATC query |
| `GSE193581` | NCBI GEO | GSE193581 | scRNA-seq | 10x Genomics 3' v3 [GPL24676] | 32 | 2026-10-22T17:08:56 | Acquired | Lu et al., JCI 2023. 10 ATC, 7 PTC, 6 adjacent normal thyroid. |
| `GSE76039` | NCBI GEO | GSE76039 | bulk microarray + mutation data | Affymetrix Human Genome U133 Plus 2.0 (GPL570) [GPL570] | 37 | 2026-10-22T17:03:50 | Acquired | Landa et al., JCI 2016. 37 PDTC/ATC tumours. |
| `GSM7030310_verification` | NCBI GEO | GSM7030310 | verification | GPL24676 | 1 | 2026-10-22T17:03:51 | Acquired | GSM7030310 belongs to GSE224719, GSE224721 and is NOT part of GSE193581; treat as a separate cohort. |
| `OpenTargets` | Open Targets Platform | MONDO:0006468 | disease-target associations + tractability | GraphQL API v4 | 1293 | 2026-10-22T17:04:32 | Acquired | 'thyroid gland undifferentiated (anaplastic) carcinoma': 1,293 associated targets (0 with overall score > 0.5, used in the Phase 6 novelty … |
| `PRIDE_PXD030304` | PRIDE | PXD030304 | proteomics | n/a | n/a | 2026-10-22T17:04:06 | GAP - not available | PRIDE project metadata not retrievable: Expecting value: line 1 column 1 (char 0) |
| `PRIDE_PXD063991` | PRIDE | PXD063991 | proteomics | n/a | n/a | 2026-10-22T17:04:07 | GAP - not available | PRIDE project metadata not retrievable: Expecting value: line 1 column 1 (char 0) |
| `PubMed_ATC` | PubMed (NCBI E-utilities) | query: "anaplastic thyroid carcinoma"[tiab] OR "anaplastic … | literature | PubMed XML | 3248 | 2026-10-22T17:06:01 | Acquired | ATC-specific corpus: 3,248 articles, 3,248 with publication dates (PMID, title, abstract, date, journal, MeSH, author affiliations). Dates … |
| `PubMed_Thyroid` | PubMed (NCBI E-utilities) | query: "thyroid cancer"[tiab] OR "thyroid carcinoma"[tiab] | literature | PubMed XML | 57771 | 2026-10-22T17:01:55 | Acquired | broad thyroid corpus: 57,771 articles, 57,771 with publication dates (PMID, title, abstract, date, journal, MeSH, author affiliations). Dat… |
| `Reactome` | Reactome | ReactomePathways.gmt (current) | pathway membership | GMT gene sets (HGNC symbols) | 2868 | 2026-10-22T17:04:28 | Acquired | 2,868 pathways for all human genes. Symbols mapped via Gene Universe. |
| `STRING` | STRING | 9606 v12.0 | protein-protein interaction network | STRING combined score | 1858944 | 2026-10-22T17:04:28 | Acquired | Full human PPI. 13,715,404 directed edges total; 1,858,944 with combined_score >= 400 (threshold applied downstream in Phase 3). STRING + R… |
| `thca_gatci_cellrep_2024` | cBioPortal | thca_gatci_cellrep_2024 (thyroid_gatci_2024) | genomics (mutations, CNA, structural variants, clinical) | Pre-called calls from cBioPortal datahub (not raw VCFs) | 190 | 2026-10-22T17:08:18 | Acquired | GATCI 2024 ATC cohort (190 tumours). Already-processed calls (not raw VCFs). Citation: Zeng, Peter Y F et al. Cell reports |
| `thca_mskcc_2016` | cBioPortal | thca_mskcc_2016 (thyroid_mskcc_2016) | genomics (mutations, CNA, structural variants, clinical) | Pre-called calls from cBioPortal datahub (not raw VCFs) | 117 | 2026-10-22T17:08:18 | Acquired | MSKCC 2016: 33 ATC + 84 PDTC. Already-processed calls (not raw VCFs). Citation: Landa et al. J Clin Invest 2016 |
| `UniProt` | UniProt | UniProtKB/Swiss-Prot human (reviewed) | protein annotation (domains, PTMs, localization, structure … | UniProt REST API (stream) | 20431 | 2026-10-22T17:04:28 | Acquired | 20,431 reviewed human entries; fields: accession, id, gene_primary, gene_names, length, ft_domain, xref_pfam, xref_pdb, ft_mod_res, ft_carb… |

## Data gaps

- **AACR_GENIE_ATC** — GENIE ATC search could not be completed: 404 Client Error: Not Found for url: https://www.cbioportal.org/api/studies/genie_public/clinical-data?clinicalDataType=SAMPLE&attributeId=ONCOTREE_CODE&projection=SUMMARY&pageSize=1000000
- **BioGRID** — Skipped (API key required). STRING + Reactome provide sufficient PPI coverage.
- **COSMIC** — Cancer Gene Census requires licence acceptance; cannot be auto-accessed. Flagged as a provenance gap.
- **DisGeNET** — Requires registration/API key; flagged as a gap.
- **DrugBank** — Licensed resource; cannot be auto-accessed. ChEMBL + Open Targets used for druggability/pharmacology.
- **PRIDE_PXD030304** — PRIDE project metadata not retrievable: Expecting value: line 1 column 1 (char 0)
- **PRIDE_PXD063991** — PRIDE project metadata not retrievable: Expecting value: line 1 column 1 (char 0)

See also [`decisions_log.md`](decisions_log.md).
