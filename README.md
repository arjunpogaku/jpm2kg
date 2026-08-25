# BDA 2026 Reproducibility Package

## Structured Domain Grounding for Natural-Language Querying of Japan's Large-Scale PM2.5 Knowledge Graph

**Arjun Chakravarthi Pogaku · Uday Kiran Rage · Padma Selvaraj · Naveen Kumar Pera**

Big Data Analytics (BDA) 2026

This repository is the public reproducibility artifact for the paper. It contains
the benchmark, the Domain Knowledge Base, the prompting and evaluation code, all
3,750 raw generation records, and every analysis reported in the paper.

**You can reproduce every table in the paper without a graph, a GPU, or an LLM:**

```bash
python3 04_pipeline/generate_camera_ready_tables.py --check
```

---

## Overview

**JPM2KG** — a Neo4j property graph of Japan's national PM2.5 monitoring network:
1,116 stations, 71,149,372 hourly observations (2018–2026), 142.3 M nodes and
213.4 M relationships, with derived temporal and categorical attributes. The
observations were collected following the procedure in Rage et al., *Scientific
Data* 12, 1009 (2025), extended through 2025 and reorganised at observation level
for natural-language querying.
See `01_knowledge_graph/`.

**AirCypher-150** — a **graph-grounded and execution-validated** NL-to-Cypher
benchmark of 150 question/Cypher pairs over JPM2KG, in five categories:
38 Aggregate, 30 Temporal, 30 Health Risk, 30 Station Filtering, 22 Comparative.
See `02_benchmark/`.

**Domain Knowledge Base (DKB)** — structured domain knowledge beyond the graph
schema: canonical values, domain rules, traversal policies, and a pool of 28
NL–Cypher exemplars disjoint from the benchmark.
See `03_domain_knowledge_base/`.

**Six prompting configurations** — Baseline, Schema, Schema+Values,
DKB-NoExamples, DKB, DKB+Hybrid — evaluated across four open-source LLMs
(Llama-3.2-3B, Gemma-2-9B, Qwen2.5-Coder-32B, Qwen2.5-72B) plus a public
fine-tuned Text2Cypher baseline.
See `04_pipeline/`.

**Evaluation and results** — CV, ES, VM-F1 and RMEM, with validity-filter
robustness, per-model exact tests, a query-cluster bootstrap, and a retrieval-k
sensitivity analysis.
See `05_results/`.

## Repository layout

```
.
├── README.md
├── DATASET_ACCESS.md                 dataset and graph download instructions
├── RELEASE_NOTES_BDA2026_CAMERA_READY.md
├── 01_knowledge_graph/
│   ├── kg_construction_notes.md      provenance, category convention, validity convention
│   ├── kg_schema.json
│   ├── kg_statistics.json            verified graph counts and pm25 distribution
│   └── neo4j_backup/README_BACKUP.md restore instructions (the dump is not in Git)
├── 02_benchmark/
│   ├── README.md
│   ├── aircypher150_benchmark.json   the 150 benchmark items
│   └── benchmark_statistics.json
├── 03_domain_knowledge_base/
│   ├── dkb_japan.json                the active public DKB
│   ├── dkb_structure_explained.md
│   └── reproducibility/              the exact DKB used for the reported runs
├── 04_pipeline/
│   ├── README.md
│   ├── METRICS.md                    metric definitions — read this first
│   ├── systems.py                    the six prompting configurations
│   ├── sota_ft_model.py              fine-tuned Text2Cypher baseline loader
│   ├── evaluator.py                  CV, ES, EM, VM-F1
│   ├── camera_ready_evaluator.py     VM-F1 + RMEM, strict and tolerant
│   ├── experiment_runner.py
│   ├── generate_camera_ready_tables.py
│   └── config.yaml, .env.example, requirements.txt
├── 05_results/
│   ├── README.md
│   ├── raw/results_full.jsonl        3,750 immutable generation records
│   ├── tables/                       the camera-ready paper tables
│   └── camera_ready/                 main, category, robustness, statistics, k-sensitivity
└── 06_environment/
    ├── README.md
    ├── models_and_generation.md      models, generation settings, latency
    ├── docker_setup.md
    └── ollama_models.txt
```

## Benchmark

AirCypher-150 is **graph-grounded and execution-validated**. It was built as:

```
human-designed query forms
  → instantiated with values extracted from JPM2KG
  → reference Cypher executed against the live graph
  → only successful, non-empty candidates retained
```

Every literal in a reference query is a value that exists in the graph, and every
reference query was run against the live database and kept only if it succeeded
and returned at least one row. Validation is execution-based; the benchmark does
not claim a second-annotator human validation pass.

The 28 DKB exemplars are disjoint from the benchmark: no identical
natural-language question, no identical Cypher query, and no identical normalized
query structure. See `02_benchmark/README.md`.

## Metrics

Full definitions in `04_pipeline/METRICS.md`.

| Metric | Type | Meaning |
|---|---|---|
| **CV** — Cypher Validity | 0/1 | Parses and uses only real JPM2KG labels and relationship types. |
| **ES** — Execution Success | 0/1 | Runs against the graph without error within 30 s. |
| **VM-F1** — Value-Multiset F1 | [0,1] | Partial-credit overlap of result values, ignoring column names and row grouping. |
| **RMEM** — Row-Multiset Exact Match | 0/1 | Exact result agreement, preserving row grouping and ignoring row order. |

CV and ES measure whether a query is runnable; VM-F1 and RMEM measure whether it
returns the intended answer.

> **Note on the raw results.** `05_results/raw/results_full.jsonl` is preserved
> byte-for-byte as generated and therefore keeps the submitted field names. It
> stores **VM-F1 under the legacy field name `SE`**. The values are the same
> quantity; only the name changed, because "Set Equality" did not describe a
> continuous partial-credit F1. RMEM is not in the raw file — it is computed by
> re-executing the stored queries.

## Main results

Pooled across the four LLMs, N = 600 per configuration:

| System | CV | ES | VM-F1 | RMEM |
|---|---|---|---|---|
| Baseline | .010 | .652 | .000 | .000 |
| Schema | .565 | .508 | .001 | .000 |
| Schema+Values | .718 | .495 | .070 | .035 |
| DKB-NoExamples | .800 | .697 | .215 | .075 |
| DKB | .757 | .670 | .328 | .077 |
| **DKB+Hybrid** | **.820** | **.725** | **.416** | **.152** |

Schema grounding alone makes queries *runnable* (CV .010 → .565) while leaving
them almost never *correct* (VM-F1 .001, RMEM .000). Structured domain grounding
is what moves correctness.

Per-model, category and robustness breakdowns are in `05_results/camera_ready/`.

## Reproduction

Three separate things, in increasing cost.

**1. Rebuild the paper tables from the shipped raw outputs.**
No graph, no models, seconds:

```bash
python3 04_pipeline/generate_camera_ready_tables.py --check
```

`--check` verifies the generated values against the paper's published numbers.
Output goes to `05_results/tables/`.

**2. Re-run evaluation against JPM2KG.**
Recomputes VM-F1 and RMEM (strict and tolerant) by re-executing the stored Cypher.
Requires a restored graph; takes hours on a cold cache:

```bash
pip install -r 04_pipeline/requirements.txt
export NEO4J_PASSWORD=...              # see 04_pipeline/.env.example
python3 04_pipeline/camera_ready_evaluator.py
```

**3. Re-run full LLM generation.**
Requires the graph, Ollama with the four models, and a GPU for the fine-tuned
baseline. About 11.5 h of generation time:

```bash
python3 04_pipeline/experiment_runner.py
```

This writes to a new file and never overwrites the historical raw results.
No random seed was pinned during the original run, so regeneration will not
reproduce the outputs bit-for-bit; see `06_environment/models_and_generation.md`.

## Dataset access

The 6.1 GB Neo4j dump, the raw national PM2.5 source data and the model weights
are not stored in this repository. See **`DATASET_ACCESS.md`**, which is
maintained here and may be updated independently of the paper.

The download location for the JPM2KG dump is **not yet published**;
`DATASET_ACCESS.md` will carry the archival URL and DOI once the deposit is
complete. Nothing in Reproduction step 1 depends on it.

The PM2.5 collection method is documented in
<https://doi.org/10.1038/s41597-025-05195-2>. That publication describes the
collection procedure; it does not contain the extended JPM2KG dataset through
2025.

## Historical reproducibility

The exact DKB used for the reported generations is preserved at
`03_domain_knowledge_base/reproducibility/dkb_japan_bda2026_experimental.json`. The active
`dkb_japan.json` corrects the documentation of the graph's stored PM2.5 category
bands; canonical values, query patterns and traversal policies are identical in
both.

## Citation

```bibtex
@inproceedings{pogaku2026domaingrounding,
  author    = {Pogaku, Arjun Chakravarthi and Rage, Uday Kiran and
               Selvaraj, Padma and Pera, Naveen Kumar},
  title     = {Structured Domain Grounding for Natural-Language
               Querying of Japan's Large-Scale {PM$_{2.5}$}
               Knowledge Graph},
  booktitle = {Big Data Analytics -- BDA 2026},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer},
  year      = {2026}
}
```

Please also cite the data collection procedure:

```bibtex
@article{rage2025patterns,
  author  = {Rage, Uday Kiran and Kattumuri, Vanitha and
             Pogaku, Arjun Chakravarthi},
  title   = {Patterns Discovery Dataset for Particulate Matter
             (PM2.5) Pollution Trends in Japan},
  journal = {Scientific Data},
  volume  = {12},
  pages   = {1009},
  year    = {2025},
  doi     = {10.1038/s41597-025-05195-2}
}
```
