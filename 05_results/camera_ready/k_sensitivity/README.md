# Retrieval-k sensitivity

A single-model, three-point sensitivity check on the number of retrieved
exemplars in DKB+Hybrid.

**Setup.** Qwen2.5-Coder-32B, DKB+Hybrid, all 150 AirCypher-150 questions,
k ∈ {1, 3, 5}. The prompt always carries **8 exemplars in total**: k retrieved
plus the fixed head of the exemplar pool, truncated to 8. So k = 1 gives 1
retrieved + 7 fixed, k = 3 gives 3 + 5, and k = 5 gives 5 + 3. Only the retrieved
share changes; prompt length and structure do not. `prompt_equivalence.md` and
`prompt_equivalence.csv` verify this per question, and
`environment_verification.md` records the graph, Ollama and embedding-model
checks that were run before generation.

## Results

Source: `results/k_sensitivity_summary.csv`, rows with `category = ALL`.

| k | VM-F1 | RMEM |
|---|---|---|
| 1 | .5560 | .200 |
| 3 | .6546 | .3067 |
| 5 | .6379 | .200 |

## What this does and does not show

- **k = 1 is clearly weaker** on both metrics. One retrieved exemplar is not
  enough: VM-F1 drops by about .10 and RMEM by .107 relative to k = 3.
- **k = 3 and k = 5 are close under VM-F1** (.655 vs .638; the paired bootstrap CI
  for that difference is [−0.014, +0.048] and includes zero) **but differ under
  RMEM** (.307 vs .200). The strict metric separates them where the partial-credit
  metric does not.
- **k = 3 was fixed a priori** in the submitted experiment. This analysis was run
  afterwards and did not select it.
- **This is three points, one model, one benchmark.** It does not establish a
  universally optimal k, and k = 3 should not be described as generally optimal.
  Category-level numbers in the summary CSV point the same way: Station Filtering
  keeps improving up to k = 5, while Health Risk is best at k = 1.

## Files

| File | Contents |
|---|---|
| `results/k_sensitivity_summary.csv` | CV, ES, VM-F1, RMEM and latency per k, overall and per category. |
| `results/k_sensitivity_per_query.csv` | Per-question scores for each k. |
| `results/k_sensitivity_paired_tests.csv` | Exact McNemar on RMEM, k=3 vs k=1 and k=3 vs k=5. |
| `results/k_sensitivity_bootstrap.csv` | Paired bootstrap CIs on VM-F1 differences (10,000 resamples). |
| `results/retrieval_sets.json` | Which exemplars were retrieved for each question at each k. |
| `results/env_verification.json` | Machine-readable environment verification. |
| `results/prompt_equivalence.csv` | Per-question prompt structure comparison across k. |
| `environment_verification.md`, `prompt_equivalence.md`, `retrieval_diagnostics.md`, `decision_report.md` | The corresponding reports. |
| `code/` | The scripts that produced the above. |

## Running the code

The scripts in `code/` are the ones that generated these results and are shipped
for provenance. They expect the original working-tree layout (they import the
pipeline as `pipeline.systems` and read the benchmark from a sibling package
directory), so they will not run unmodified against this repository alone. For
the public release the machine-local absolute paths were replaced by the
`PM25_ROOT` and `KS_DIR` environment variables and the hard-coded Neo4j password
by `NEO4J_PASSWORD`; nothing else was changed.

Re-running them performs LLM generation.
