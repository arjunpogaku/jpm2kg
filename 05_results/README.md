# Results

| Directory | Contents |
|---|---|
| `raw/` | `results_full.jsonl` — the 3,750 historical generation records, unmodified. |
| `tables/` | The camera-ready paper tables, regenerable from `raw/` and `camera_ready/`. |
| `camera_ready/` | Camera-ready analyses: main results, per-category results, validity-filter robustness, statistics, retrieval-k sensitivity. |

## `raw/results_full.jsonl`

One JSON object per line, 3,750 lines: 150 benchmark questions × 6 prompting
configurations × 4 LLMs (3,600), plus 150 fine-tuned-baseline records.

**This file is immutable.** It is preserved byte-for-byte as generated in June
2026, which means it keeps the submitted field names. In particular
`metrics.SE` holds what the camera-ready paper calls **VM-F1** (Value-Multiset
F1) — the same values under an inaccurate old name. See
`../04_pipeline/METRICS.md`.

`metrics.RQ` is a review-era heuristic and is not a camera-ready metric.
RMEM is not stored in the raw file; it is computed by re-executing the stored
queries with `../04_pipeline/camera_ready_evaluator.py`.

Each record carries `query_id`, `query_type`, `llm`, `system`, `nl_query`,
`generated_cypher`, `gold_cypher`, `generation_time_ms`, `metrics` and any
`eval_error`. Join on `query_id`, which is not contiguous — see
`../02_benchmark/README.md`.
