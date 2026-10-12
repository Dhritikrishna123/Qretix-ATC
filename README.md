# Qretix-ATC

QRETIX-ATC v0.1 is an auditable, evidence-provenance-aware pipeline that ranks human protein-coding genes as candidate Anaplastic Thyroid Cancer (ATC) therapeutic targets. It explicitly separates known biology from novel hypotheses, and every score is decomposable into traceable evidence components.

> Computational hypothesis ≠ experimentally validated therapeutic target

## Install
```bash
pip install -r requirements.txt
```

## Layout
- `src/` pipeline modules (data acquisition, preprocessing, features, labels, models, novelty, validation, evidence cards, benchmarking)
- `data/` raw, processed, provenance
- `features/`, `labels/`, `knowledge_graph/`, `literature/`, `models/`, `evaluation/`, `evidence_cards/`, `configs/`, `docs/`
