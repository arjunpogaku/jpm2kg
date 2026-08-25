# Camera-ready results

Every file in this directory is derived from the immutable historical
generations in `../raw/results_full.jsonl` by re-executing the stored Cypher
against JPM2KG. **No LLM generation was rerun.** The raw file itself is
unchanged and still stores VM-F1 under its legacy field name `SE`
(see `../../04_pipeline/METRICS.md`).

## Layout

| Directory | Contents |
|---|---|
| `main_results/` | Pooled and per-model CV, ES, VM-F1 and RMEM for the six prompting configurations and the fine-tuned baseline. |
| `category_results/` | VM-F1 and RMEM broken down by benchmark category. |
| `robustness/` | Strict vs. tolerant evaluation — how much the scores move if the numerical-validity predicate is dropped from the reference queries. |
| `statistics/` | Per-model exact McNemar tests and the query-cluster bootstrap. |
| `k_sensitivity/` | Retrieval-k sensitivity experiment (k ∈ {1, 3, 5}, one model). |

## Main results — pooled across the four LLMs (N = 600 per configuration)

Source: `main_results/pooled_by_configuration.csv` (VM-F1, RMEM) and
`main_results/cv_es_vmf1_recomputed_all_scopes.csv` (CV, ES, scope
`pooled_x_config`).

| System | CV | ES | VM-F1 | RMEM |
|---|---|---|---|---|
| Baseline | .010 | .652 | .000 | .000 |
| Schema | .565 | .508 | .001 | .000 |
| Schema+Values | .718 | .495 | .070 | .035 |
| DKB-NoExamples | .800 | .697 | .215 | .075 |
| DKB | .757 | .670 | .328 | .077 |
| DKB+Hybrid | .820 | .725 | .416 | .152 |

The fine-tuned Text2Cypher baseline (N = 150) reaches CV .613 and ES .580 with
VM-F1 .000 and RMEM .000.

## VM-F1 by model (N = 150 per cell)

Source: `main_results/vmf1_by_model_and_configuration.csv`.
L3B = Llama-3.2-3B, G9B = Gemma-2-9B, QC32B = Qwen2.5-Coder-32B, Q72B = Qwen2.5-72B.

| System | L3B | G9B | QC32B | Q72B |
|---|---|---|---|---|
| Baseline | .000 | .000 | .000 | .000 |
| Schema | .000 | .000 | .004 | .000 |
| Schema+Values | .017 | .072 | .094 | .099 |
| DKB-NoExamples | .027 | .061 | .495 | .277 |
| DKB | .015 | .244 | .462 | .593 |
| DKB+Hybrid | .126 | .279 | .647 | .614 |

## RMEM by model

Source: `main_results/by_model_and_configuration.csv`, column
`rmem_strict_accuracy`. Under DKB+Hybrid: .020 (L3B), .093 (G9B), .307 (QC32B),
.187 (Q72B).

## File reference

| File | What it holds |
|---|---|
| `main_results/pooled_by_configuration.csv` | Per configuration: N, VM-F1 (saved / re-executed / tolerant), RMEM strict and tolerant counts and accuracies, execution failures. |
| `main_results/by_model_and_configuration.csv` | The same, split by model. |
| `main_results/vmf1_by_model_and_configuration.csv` | VM-F1 matrix: configuration × model, with macro and pooled means. |
| `main_results/cv_es_vmf1_recomputed_all_scopes.csv` | CV, ES, EM, VM-F1 and the submission's RQ heuristic, at four scopes (pooled, per model, per category, per category × model). |

`vmf1_saved` is the historical value read from the raw JSONL;
`vmf1_strict_reexecuted` is the same metric recomputed by re-executing the stored
queries. They agree to within 0.008 in every configuration; the small differences
come from reference queries that timed out in one pass and not the other.

## Reproducing these files

```bash
export NEO4J_PASSWORD=...           # see ../../04_pipeline/.env.example
cd ../../04_pipeline
python3 camera_ready_evaluator.py           # recompute VM-F1 + RMEM, all 3,750 records
python3 generate_camera_ready_tables.py     # rebuild the paper tables under ../05_results/tables/
```

The first command executes several thousand distinct queries against a
142M-node graph and takes hours on a cold cache.
