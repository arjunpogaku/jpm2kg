# BDA 2026 Reproducibility Package
## Structured Domain Grounding for Natural-Language Querying of Japan's Large-Scale PM2.5 Knowledge Graph

**Authors:** Arjun Chakravarthi POGAKU, Uday Kiran RAGE
**Affiliation:** University of Aizu, Aizu-Wakamatsu, Fukushima, Japan
**Conference:** BDA 2026 — Big Data Analytics

This package contains the knowledge graph, benchmark, domain knowledge base,
evaluation pipeline, and raw results needed to reproduce the tables reported
in the paper: JPM2KG (a PM2.5 knowledge graph for Japan), the AirCypher-150
NL-to-Cypher benchmark, and the DKB (Domain Knowledge Base) grounding
framework.

## Contents

```
reviewer_package_BDA2026_FINAL/
├── README.md                  ← you are here
├── 01_knowledge_graph/        ← JPM2KG schema, statistics, and Neo4j dump
├── 02_benchmark/               ← AirCypher-150 benchmark (150 NL-to-Cypher queries)
├── 03_domain_knowledge_base/  ← DKB definition and structure
├── 04_pipeline/               ← evaluation code + table-generation scripts
├── 05_results/                ← raw per-query results + regenerated tables
└── 06_environment/            ← software environment details
```

- **`01_knowledge_graph/`** — the JPM2KG schema and statistics, plus a Neo4j dump (`neo4j_backup/`) to restore the graph.
- **`02_benchmark/`** — the AirCypher-150 benchmark (150 queries, 5 categories) and its summary statistics.
- **`03_domain_knowledge_base/`** — the DKB's canonical values, domain rules, and traversal policies, with a structural explanation.
- **`04_pipeline/`** — the six prompting systems (`systems.py`), evaluation metrics (`evaluator.py`), evaluation loop (`experiment_runner.py`), and the two scripts that produce every table below.
- **`05_results/`** — `raw/results_full.jsonl` (one record per system × LLM × query) and `tables/`, generated fresh from that file by the scripts in `04_pipeline/`.
- **`06_environment/`** — Docker/Neo4j setup notes and the exact Ollama model tags used.

## To reproduce the paper's tables

From `04_pipeline/`, with `results_full.jsonl` in place under `05_results/raw/`:

```bash
python3 generate_paper_tables.py       # Tables 1-3 + the single-LLM ablation table
python3 compute_per_llm_stats.py       # Table 4: per-LLM significance testing + breakdown
```

Both scripts read `05_results/raw/results_full.jsonl` and
`02_benchmark/aircypher150_benchmark.json`, and write into `05_results/tables/`
by default.

To reproduce `results_full.jsonl` itself from scratch: restore the Neo4j graph
from `01_knowledge_graph/neo4j_backup/`, pull the Ollama models listed in
`06_environment/ollama_models.txt`, then run `experiment_runner.py` with the
six systems (`baseline`, `cypherbench_style`, `schema_plus_values`,
`dkb_no_examples`, `dkb`, `dkb_hybrid`) against all four LLMs and the
AirCypher-150 benchmark.

## Full research history

This package is deliberately minimal: it contains only what's needed to
regenerate the paper's tables from the shipped raw results. The full
development history — including exploratory ablations, earlier pipeline
versions, and intermediate analyses that did not make it into the paper — is
preserved at the git tag `bda2026-submission`, if needed for provenance.

## Citation

```bibtex
@inproceedings{pogaku2026domaingrounding,
  author    = {Pogaku, Arjun Chakravarthi and Rage, Uday Kiran},
  title     = {Structured Domain Grounding for Natural-Language
               Querying of Japan's Large-Scale {PM$_{2.5}$}
               Knowledge Graph},
  booktitle = {Big Data Analytics -- BDA 2026},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  year      = {2026}
}
```
