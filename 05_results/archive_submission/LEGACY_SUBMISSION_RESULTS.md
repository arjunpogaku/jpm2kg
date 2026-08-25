# Legacy submission results — NOT the camera-ready results

Everything in this directory is the review-era output, kept for provenance. It
is superseded. **Do not cite these files as the camera-ready results.**
The camera-ready results are in `../camera_ready/` and `../tables/`.

## What is here, and why it is superseded

### `tables/`

| File | Superseded by | Why |
|---|---|---|
| `table1_main.csv`, `table1_main.tex` | `../tables/table1_main.csv` / `.tex` | Reported `SE` and the `RQ` heuristic. The camera-ready main table reports CV, ES, VM-F1 and RMEM, and drops RQ. |
| `table2_per_llm.csv`, `table2_per_llm.tex` | `../tables/table2_per_llm.csv` / `.tex` | Same metric renaming; RMEM added. |
| `table3_categories.csv` | `../tables/table3_categories.csv` | Same metric renaming. |
| `table4_ablation.csv` | `../camera_ready/main_results/` | Single-model ablation under the old metric names. |
| `table4_combined_pvalues.csv` | — | **Stouffer-combined p-values. Withdrawn.** |
| `table4_per_llm_pvalues.csv` | `../tables/table_robustness.csv` and `../camera_ready/statistics/exact_paired_tests_rmem.csv` | Wilcoxon signed-rank on continuous SE, replaced by exact McNemar on binary RMEM. |
| `table4_statistical_comparison.tex` | `../tables/table_robustness.tex` | Same. |
| `statistical_tests.txt` | `../camera_ready/statistics/` | Same. |
| `per_llm_overall.csv`, `per_llm_per_category_dkbhybrid.csv` | `../camera_ready/main_results/`, `../camera_ready/category_results/` | Same numbers under the old metric name. |

Note that the **values** in the old tables are not wrong: `SE` there holds the
same quantity now reported as VM-F1. What is superseded is the metric naming, the
absence of a strict result metric, and the statistical inference.

### The statistical change

The submission combined per-model Wilcoxon p-values with Stouffer's method. That
combination treats the four models as independent replicates, but they answer the
**same** 150 questions, so they are not. The camera-ready analysis instead
reports per-model exact McNemar tests separately and estimates cross-model effects
with a query-cluster bootstrap over the 150 questions. **No p-value combination
is used, and the Stouffer output is not part of the camera-ready results.**

See `../camera_ready/statistics/README.md`.

## Generators

The scripts that produced these tables are archived alongside the rest of the
submitted pipeline in `../../04_pipeline/archive_submission/`:
`generate_paper_tables_bda2026_submission.py` and
`compute_per_llm_stats_bda2026_submission.py`.

The camera-ready replacement is
`../../04_pipeline/generate_camera_ready_tables.py`.
