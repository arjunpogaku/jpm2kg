# 00 — Environment Record (k-sensitivity experiment)

Verified 2026-08-24 before any generation. Every check below had to pass
for Phase 4 to start; the run script aborts on a retrieval failure rather than
silently falling back to zero retrieved exemplars.

## Verification results

| Check | Result | Detail |
|---|---|---|
| neo4j reachable bolt://localhost:37689 | PASS | 2026.02.2 (community) |
| graph counts match audited snapshot | PASS | nodes=142,300,976 rels=213,449,232 ObservedPM25=71,149,372 |
| ollama reachable :11434 | PASS | v0.32.1 |
| qwen2.5-coder:32b installed | PASS | b92d6a0bd47ee79114298de0 |
| sentence-transformers importable | PASS | 5.1.1 |
| all-MiniLM-L6-v2 loads | PASS | 384-dim |
| retrieval returns exactly k=1 | PASS | JP28 |
| retrieval returns exactly k=3 | PASS | JP28,JP06,JP05 |
| retrieval returns exactly k=5 | PASS | JP28,JP06,JP05,JP07,JP13 |
| retrieved exemplars present in prompt | PASS | JP28,JP06,JP05 |

Machine-readable copy: `results/env_verification.json`.

## Software

| Component | Version |
|---|---|
| Python | 3.12.11 |
| Ollama | 0.32.1 |
| Model | `qwen2.5-coder:32b` |
| Model digest | `b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41` |
| Model family / params / quant | qwen2 / 32.8B / Q4_K_M |
| Model size on disk | 19,851,349,898 bytes |
| sentence-transformers | 5.1.1 |
| transformers | 4.56.1 |
| torch | 2.7.1+cu126 (CUDA 12.6) |
| GPU | NVIDIA RTX A6000 |
| Embedding model | `all-MiniLM-L6-v2` (384-dim, L2-normalised, cosine) |
| Neo4j | 2026.02.2 (community), `bolt://localhost:37689`, container `jp-pm25-neo4j` |

No new virtual environment was created: the existing project interpreter
(`/usr/bin/python3`, 3.12.11) already satisfies every dependency. The Keras-3
import failure that would disable retrieval is avoided the same way the
published code avoids it — `USE_TF=0` / `TRANSFORMERS_NO_TF=1` set before any
transformers import. This was confirmed by loading the encoder and asserting the
retrieved exemplars actually appear in the assembled prompt, not merely that the
import succeeded.

## Graph state

| Quantity | Live now | Audited snapshot (`14_database_validation.md`) |
|---|---:|---:|
| Nodes | 142,300,976 | 142,300,976 |
| Relationships | 213,449,232 | 213,449,232 |
| `ObservedPM25` | 71,149,372 | 71,149,372 |

Exact match. The historical DKB (`data/dkb_japan.json`) was read only.

## Generation settings (inherited unchanged from `pipeline/systems.py`)

`temperature = 0.0`, `num_predict = 512`, `num_ctx = 8192`, `stream = false`,
`think = false`, `keep_alive = 30m`, per-call timeout 60 s with 2 attempts.
**No seed** is passed, because the submitted API call passed none.
Execution scoring uses `QueryEvaluator(exec_timeout_s=30)` with the submitted
200-row cap.

## Sample retrieval (query `q001`)

| k | retrieved exemplar ids |
|---:|---|
| 1 | JP28 |
| 3 | JP28, JP06, JP05 |
| 5 | JP28, JP06, JP05, JP07, JP13 |
