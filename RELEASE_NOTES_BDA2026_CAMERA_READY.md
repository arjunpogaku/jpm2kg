# Release Notes — BDA 2026 Camera-Ready Artifact

This release updates the reproducibility package to match the camera-ready
paper. The historical experimental evidence is unchanged.

## Terminology

- The submitted metric field `SE` ("Set Equality") is reported as **VM-F1**
  (Value-Multiset F1), which is what it always computed: a continuous,
  partial-credit F1 over result value multisets. The values are unchanged.
- `05_results/raw/results_full.jsonl` is preserved byte-for-byte and therefore
  still stores VM-F1 under the legacy field name `SE`. This is documented in
  `04_pipeline/METRICS.md`, `05_results/README.md` and the root `README.md`.

## New analyses

- **RMEM (Row-Multiset Exact Match)** added as the strict binary result metric,
  computed by re-executing the stored queries. Implementation:
  `04_pipeline/camera_ready_evaluator.py`.
- **Validity-filter robustness** — strict and tolerant evaluation of both
  metrics, where tolerant removes only the `[0,500]` numerical-validity predicate
  from the applicable reference queries.
  See `05_results/camera_ready/robustness/`.
- **Per-model and per-category results** for VM-F1 and RMEM.
  See `05_results/camera_ready/main_results/` and `category_results/`.
- **Retrieval-k sensitivity** — k ∈ {1, 3, 5} for DKB+Hybrid on
  Qwen2.5-Coder-32B, with environment verification, prompt-equivalence checks,
  per-query outputs and paired tests.
  See `05_results/camera_ready/k_sensitivity/`.

## Statistical analysis

The camera-ready inference is **per-model exact McNemar tests on RMEM** plus a
**query-cluster bootstrap** over the 150 benchmark questions (10,000 resamples).
The four per-model p-values are reported separately and are **not** combined,
because the four models answer the same questions.

The review-era Wilcoxon and Stouffer-combined outputs are retained by the
authors but are not part of this release and are no longer presented as
active results.

## Documentation and metadata corrections

- **PM2.5 category bands.** `pm25_level` is documented as the **JPM2KG
  system-defined category convention** — Safe 0–15, Moderate 16–35, Slightly
  Unhealthy 36–50, Unhealthy 51–70, Very Unhealthy ≥ 71 — matching the mapping
  stored in the graph. It is no longer described as an official WHO or Japanese
  classification, and genuine regulatory thresholds are documented separately.
- **Graph statistics.** `01_knowledge_graph/kg_statistics.json` now carries the
  verified value distribution, including the NULL / below-0 / above-500 / [0,500]
  partition of all 71,149,372 observations.
- **Data provenance.** The collection procedure reference (Rage et al.,
  *Scientific Data* 12, 1009, 2025) is stated, along with how JPM2KG differs from
  that release.
- **Validity predicate.** `p.pm25 >= 0 AND p.pm25 <= 500` is described as a
  data-quality convention used for numerical aggregation, not an external
  standard.
- **Benchmark metadata.** `02_benchmark/benchmark_statistics.json` describes
  AirCypher-150 as graph-grounded and execution-validated, with its construction
  pipeline stated; the unsupported `logical_forms` field and the stale minimum
  execution-time statistic were removed. Disjointness from the 28 DKB exemplars
  is documented and verified.
- **DKB exemplar count in the prompt.** Both exemplar-using configurations show 8
  exemplars; DKB+Hybrid is 3 retrieved plus 5 fixed. The previous documentation
  said all 28 were included.
- **Environment.** `06_environment/` documents the generation settings, the
  fine-tuned baseline configuration and the historical latency for all 3,750
  records, and states plainly what was not recorded at experiment time
  (quantization, model digests, Ollama version).

## Package changes

- The fine-tuned Text2Cypher baseline loader now ships in `04_pipeline/`, so the
  package can reconstruct the baseline invocation from the public checkpoint.
- No credentials in the repository: Neo4j settings come from the environment,
  with `04_pipeline/.env.example` as the template.
- Paths resolve relative to the repository instead of the original machine.
- DKB+Hybrid retrieval now fails loudly instead of silently falling back to zero
  retrieved exemplars if `sentence-transformers` is unavailable.
- `experiment_runner.py` dispatches all six prompting configurations.
- `04_pipeline/generate_camera_ready_tables.py` regenerates every paper table
  from the shipped files, with `--check` verifying them against the published
  values.

## Preserved unchanged

- `05_results/raw/results_full.jsonl` — all 3,750 historical generations,
  checksum-identical to the reviewer package.
- `02_benchmark/aircypher150_benchmark.json` — the benchmark items.
- `03_domain_knowledge_base/reproducibility/dkb_japan_bda2026_experimental.json` — the
  exact DKB used for the reported generations.

No LLM generation was rerun and no historical score was rewritten for this
release.
