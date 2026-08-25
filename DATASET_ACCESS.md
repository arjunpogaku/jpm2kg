# Dataset and Graph Access

This file is the authoritative, maintained location for data-access
instructions. It may be updated independently of the paper.

## What is in this repository

Everything needed to reproduce the paper's tables:

- **AirCypher-150** — `02_benchmark/aircypher150_benchmark.json`
- **The Domain Knowledge Base** — `03_domain_knowledge_base/`
- **Pipeline and evaluation code** — `04_pipeline/`
- **All 3,750 raw generation records** — `05_results/raw/results_full.jsonl`
- **All camera-ready analyses and tables** — `05_results/`

Reproducing the paper's tables requires none of the downloads below:

```bash
python3 04_pipeline/generate_camera_ready_tables.py --check
```

## What is not in this repository

| Item | Size | Why not here |
|---|---|---|
| JPM2KG Neo4j dump (`jpm2kg.dump`) | ~6.1 GB | Exceeds GitHub's file and repository limits. |
| Raw national PM2.5 source data | large | Redistribution is out of scope for this artifact; see the collection reference below. |
| LLM weights | tens of GB | Fetched from their upstream sources; see below. |

### JPM2KG graph dump

> **The download location for `jpm2kg.dump` is not yet published.**
> This section will be updated with the archival URL and DOI once the deposit is
> complete. It is needed only to re-execute queries against the live graph or to
> regenerate LLM outputs.

Restore instructions: `01_knowledge_graph/neo4j_backup/README_BACKUP.md`.
The expected node and relationship counts to verify a restore are in
`01_knowledge_graph/kg_statistics.json`.

### PM2.5 data collection

The PM2.5 observations were collected following the procedure described in:

> Rage, Uday Kiran; Kattumuri, Vanitha; Pogaku, Arjun Chakravarthi.
> *Patterns Discovery Dataset for Particulate Matter (PM2.5) Pollution Trends in Japan.*
> Scientific Data **12**, 1009 (2025). <https://doi.org/10.1038/s41597-025-05195-2>

That publication documents the **collection method**. It does **not** contain the
extended, observation-level JPM2KG dataset through 2025, and it is not a
substitute for the graph dump. See
`01_knowledge_graph/kg_construction_notes.md` for how the two differ.

### Models

The four Ollama models and the fine-tuned Text2Cypher checkpoint are public and
are fetched from their upstream sources. Pull commands:
`06_environment/ollama_models.txt`. Settings and versions:
`06_environment/models_and_generation.md`.
