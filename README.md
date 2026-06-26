# BDA 2026 Submission Package
## Structured Domain Grounding for Natural-Language Querying
## of Japan's Large-Scale PM2.5 Knowledge Graph

**Authors:** Arjun Chakravarthi POGAKU, Uday Kiran RAGE
**Affiliation:** University of Aizu, Aizu-Wakamatsu, Fukushima, Japan
**Conference:** BDA 2026 — Big Data Analytics

---

## Package Overview

This package contains all materials needed to review and reproduce the paper, including the knowledge graph, benchmark, pipeline code, and all experimental results.

```
reviewer_package_BDA2026/
├── README.md                  ← YOU ARE HERE
├── REPRODUCIBILITY.md         ← Step-by-step reproduction
├── RESULTS_SUMMARY.md         ← Quick results overview
│
├── 01_knowledge_graph/        ← JPM2KG graph resources
├── 02_benchmark/              ← AirCypher-150 benchmark
├── 03_domain_knowledge_base/  ← DKB definition and structure
├── 04_pipeline/               ← All evaluation code
├── 05_results/                ← All results, tables, figures
└── 06_environment/            ← Software environment details
```

---

## Quick Start for Reviewers

### "I want to see the results"
→ Open: `RESULTS_SUMMARY.md`
→ Or see tables: `05_results/tables/table1_main.csv`
→ Or see figures: `05_results/figures/`

### "I want to understand the benchmark"
→ Open: `02_benchmark/README_BENCHMARK.md`
→ Browse queries: `02_benchmark/aircypher150_benchmark.json`
→ See examples: `02_benchmark/sample_queries.md`

### "I want to understand the DKB"
→ Open: `03_domain_knowledge_base/README_DKB.md`
→ Inspect DKB: `03_domain_knowledge_base/dkb_japan.json`
→ Read explanation: `03_domain_knowledge_base/dkb_structure_explained.md`

### "I want to understand the code"
→ Open: `04_pipeline/README_PIPELINE.md`
→ Key files: `systems.py` (6 systems), `evaluator.py` (5 metrics)

### "I want to reproduce the experiments"
→ Open: `REPRODUCIBILITY.md` (complete step-by-step guide)
→ Restore KG: `01_knowledge_graph/neo4j_backup/README_BACKUP.md`
→ Run pipeline: `04_pipeline/experiment_runner.py`

### "I want to inspect the raw data"
→ Raw results: `05_results/raw/results_full.jsonl`
→ Each line: one evaluation record with all 5 metrics

---

## Paper Contributions

| Contribution | Location in Package |
|---|---|
| JPM2KG knowledge graph | `01_knowledge_graph/` |
| AirCypher-150 benchmark | `02_benchmark/` |
| DKB framework | `03_domain_knowledge_base/` |
| Evaluation pipeline | `04_pipeline/` |
| All results | `05_results/` |

---

## Key Results at a Glance

| System | Semantic Equivalence (SE) |
|---|---|
| Baseline (no context) | 0.000 |
| Schema Baseline (CypherBench-style) | 0.001 |
| Schema + Canonical Values | 0.070 |
| DKB without Examples | 0.215 |
| DKB with Fixed Examples | 0.328 |
| **DKB+Hybrid (Proposed)** | **0.416** |

Schema grounding is necessary but insufficient. Domain grounding is the critical driver of semantic correctness (~400× improvement over schema-only baseline).

---

## Contact

For questions about the code or data, please contact:
arjun.chakravarthip@gmail.com

---

## Citation

If you use JPM2KG, AirCypher-150, or the DKB framework, please cite:

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
