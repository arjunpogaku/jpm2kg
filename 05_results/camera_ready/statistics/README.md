# Statistical analysis (camera-ready)

RMEM is binary and all four models answer the same 150 questions, so the
inference is built on that pairing rather than on a rank test over continuous
per-query scores.

Two things are reported:

1. **Per-model exact McNemar tests.** For each model separately, the two
   configurations are compared on the discordant pairs with an exact two-sided
   binomial test. Reported per model — the four p-values are **not** combined,
   because the four models answer the *same* 150 questions and so are not
   independent replicates.
2. **Query-cluster bootstrap.** Cross-model effect sizes resample the 150
   benchmark questions with replacement, carrying all four model outcomes for
   each sampled question together. 10,000 resamples, seed 42, percentile 95 % CI.

## DKB+Hybrid vs DKB, strict RMEM

| Model | Δ accuracy | exact two-sided p |
|---|---|---|
| Llama-3.2-3B | +.0133 | .5000 |
| Gemma-2-9B | +.0667 | .0020 |
| Qwen2.5-Coder-32B | +.1333 | .0029 |
| Qwen2.5-72B | +.0867 | .0533 |

Cross-model clustered effect: **+0.0750, 95 % CI [+0.0450, +0.1050]**.

Every model's point estimate is positive, but only two reach p < 0.05
individually: the improvement is real on average and model-dependent in size.
Llama-3.2-3B simply has too few discordant correct predictions (2 vs 0) to
establish anything.

## Files

| File | Contents |
|---|---|
| `exact_paired_tests_rmem.csv` | Exact McNemar for every configuration pair × model, under strict and tolerant RMEM: the 2×2 discordance counts, accuracies, the difference, and exact two-sided p. Rows labelled `MACRO (4 LLM pooled)` are descriptive only and are explicitly **not** independent. |
| `cluster_bootstrap_rmem.csv` | Query-cluster bootstrap for the same comparisons: mean difference, 95 % CI, and the fraction of resamples at or below zero. |

## Note on the submission's statistics

The review-era package reported Wilcoxon signed-rank tests over per-query SE
scores with Stouffer's method combining p-values across models. Those outputs are
superseded and are **not** the camera-ready inference. No p-value combination is
used here.
