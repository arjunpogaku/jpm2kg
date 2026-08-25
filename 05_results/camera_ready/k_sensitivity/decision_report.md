# 03 — Retrieval-k Sensitivity: Decision Report

Model `qwen2.5-coder:32b`; system DKB+Hybrid only; AirCypher-150; published exemplar cap of 8 preserved (k retrieved + the first 8−k static exemplars). Fresh generations at k=1, 3, 5 under identical settings, including a k=3 control re-run — no published number is reused for comparison. Prompt equivalence at k=3 was verified byte-identical before generation (`01_prompt_equivalence.md`).

## Pooled results

| k | CV | ES | VM-F1 strict | VM-F1 tolerant | RMEM strict | RMEM tolerant | RMEM strict correct | RMEM tolerant correct | median gen latency (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.8333 | 0.7333 | 0.556 | 0.556 | 0.2 | 0.2 | 30/150 | 30/150 | 13.797 |
| 3 | 0.96 | 0.8867 | 0.6546 | 0.6546 | 0.3067 | 0.3067 | 46/150 | 46/150 | 13.096 |
| 5 | 0.9933 | 0.9267 | 0.6379 | 0.6379 | 0.2 | 0.2 | 30/150 | 30/150 | 13.514 |

## Paired exact tests (same 150 questions under every k)

| metric | comparison | both correct | k3 only | comparator only | both wrong | acc. difference | two-sided exact p |
|---|---|---:|---:|---:|---:|---:|---:|
| RMEM_strict | k3_vs_k1 | 25 | 21 | 5 | 99 | 0.1067 | 0.002494 |
| RMEM_strict | k3_vs_k5 | 29 | 17 | 1 | 103 | 0.1067 | 0.000145 |
| RMEM_tolerant | k3_vs_k1 | 25 | 21 | 5 | 99 | 0.1067 | 0.002494 |
| RMEM_tolerant | k3_vs_k5 | 29 | 17 | 1 | 103 | 0.1067 | 0.000145 |

Exact McNemar (two-sided exact binomial on discordant pairs).

## Paired VM-F1 bootstrap (10,000 resamples, seed 20260824)

| metric | comparison | mean paired difference | 95% CI | excludes 0 |
|---|---|---:|---|---|
| VM_F1_strict | k3_minus_k1 | 0.0986 | [0.0405, 0.1595] | yes |
| VM_F1_strict | k3_minus_k5 | 0.0167 | [-0.0142, 0.0483] | no |
| VM_F1_tolerant | k3_minus_k1 | 0.0986 | [0.0405, 0.1595] | yes |
| VM_F1_tolerant | k3_minus_k5 | 0.0167 | [-0.0142, 0.0483] | no |

## Per-category RMEM strict

| category | n | k=1 | k=3 | k=5 | max−min |
|---|---:|---:|---:|---:|---:|
| aggregate | 38 | 0.0 | 0.0 | 0.0 | 0.0000 |
| comparative | 22 | 0.0 | 0.4091 | 0.1364 | 0.4091 |
| health_risk | 30 | 0.9 | 0.8 | 0.7333 | 0.1667 |
| station_filtering | 30 | 0.0333 | 0.0333 | 0.0667 | 0.0334 |
| temporal | 30 | 0.0667 | 0.4 | 0.1 | 0.3333 |

## Per-category VM-F1 strict

| category | n | k=1 | k=3 | k=5 | max−min |
|---|---:|---:|---:|---:|---:|
| aggregate | 38 | 0.7184 | 0.7043 | 0.6973 | 0.0211 |
| comparative | 22 | 0.0 | 0.5545 | 0.5 | 0.5545 |
| health_risk | 30 | 0.9444 | 0.8 | 0.7333 | 0.2111 |
| station_filtering | 30 | 0.2987 | 0.4008 | 0.4931 | 0.1944 |
| temporal | 30 | 0.6267 | 0.7733 | 0.7133 | 0.1466 |

## Failure modes

| k | CV | execution failures | of which syntax errors | of which 30 s timeouts |
|---:|---:|---:|---:|---:|
| 1 | 0.8333 | 40 | 25 | 15 |
| 3 | 0.96 | 17 | 6 | 11 |
| 5 | 0.9933 | 11 | 1 | 10 |

Syntax errors fall monotonically with k (25 -> 6 -> 1), matching the CV trend; this is a prompt effect. Timeouts fall much less (15 -> 11 -> 10) and are a property of how expensive the generated query is to execute, not of its correctness. Timeouts are preserved as failures exactly as the submitted evaluation pipeline did. Because execution timing depends on concurrent load on a shared machine, the timeout component of these counts is the least reproducible part of this experiment.

## Control check against the submitted run

The fresh k=3 arm is a re-run of the published configuration. Compared with the audited camera-ready recomputation of the submitted generations (`camera_ready_audit/results/tolerant_exact_result_evaluation.csv`, `qwen2.5-coder:32b` / `dkb_hybrid`):

| quantity | submitted run (audited) | fresh k=3 control |
|---|---:|---:|
| VM-F1 strict | 0.6576 | 0.6546 |
| RMEM strict | 0.3067 (46/150) | 0.3067 (46/150) |

The control reproduces the published k=3 numbers to within 0.003 VM-F1 and exactly on RMEM, despite no seed being passed. This supports treating the three new arms as comparable to each other and to the submitted result.


---

## Answers to the twelve questions

**1. Strict VM-F1 at k=1,3,5.** 0.556, 0.6546, 0.6379.

**2. Tolerant VM-F1 at k=1,3,5.** 0.556, 0.6546, 0.6379.

**3. Strict RMEM at k=1,3,5.** 0.2 (30/150), 0.3067 (46/150), 0.2 (30/150).

**4. Tolerant RMEM at k=1,3,5.** 0.2 (30/150), 0.3067 (46/150), 0.2 (30/150).

**5. k=3 vs k=1, strict RMEM.** Discordant pairs: 21 k=3-only, 5 k=1-only. Accuracy difference 0.1067. Two-sided exact p = 0.002494 — statistically significant at alpha=0.05.

**6. k=3 vs k=5, strict RMEM.** Discordant pairs: 17 k=3-only, 1 k=5-only. Accuracy difference 0.1067. Two-sided exact p = 0.000145 — statistically significant at alpha=0.05.

**7. Same two comparisons under tolerant RMEM.** k=3 vs k=1: difference 0.1067, exact p = 0.002494 — statistically significant at alpha=0.05. k=3 vs k=5: difference 0.1067, exact p = 0.000145 — statistically significant at alpha=0.05.

**8. Paired VM-F1 bootstrap intervals.** VM_F1_strict k3_minus_k1: 0.0986, 95% CI [0.0405, 0.1595] (excludes 0); VM_F1_strict k3_minus_k5: 0.0167, 95% CI [-0.0142, 0.0483] (includes 0); VM_F1_tolerant k3_minus_k1: 0.0986, 95% CI [0.0405, 0.1595] (excludes 0); VM_F1_tolerant k3_minus_k5: 0.0167, 95% CI [-0.0142, 0.0483] (includes 0).

**9. Category sensitivity.** Yes, two categories do. Ranked by strict-RMEM spread across k: comparative 0.409; temporal 0.333; health_risk 0.167; station_filtering 0.033; aggregate 0.000. `comparative` (n=22) moves from 0.0 at k=1 to 0.4091 at k=3 and back to 0.1364 at k=5, and `temporal` (n=30) from 0.0667 to 0.4 to 0.1 — both peaked at k=3 and both non-monotone. `aggregate` (n=38) scores 0.0 strict RMEM at every k and is insensitive by construction: its questions return computed averages that rarely reproduce the gold row multiset exactly, so the metric has no headroom to move. `station_filtering` and `health_risk` shift by at most 0.17. Per-category n is 22–38, so these are directional observations; no per-category significance test is claimed and none should be quoted as one.

**10. Is the central retrieval conclusion robust across k=1,3,5?** Yes. The paper's central retrieval claim is that DKB+Hybrid's semantic exemplar retrieval contributes to NL-to-Cypher quality, not that any particular k is correct. Every arm here uses retrieval and the cap of 8, and all three land in the same broad regime (VM-F1 0.556-0.6546, RMEM 0.2-0.3067). No arm collapses and no arm overturns the direction of the published finding. Strict and tolerant figures are identical throughout: relaxing the `p.pm25 >= 0 AND p.pm25 <= 500` validity clause never changed a reference result set on this benchmark. The same identity holds in the audited recomputation of the submitted run, so this is a property of the benchmark, not of this experiment.

**11. Is k=3 demonstrably optimal?** No. This experiment was not designed to identify an optimal k and does not do so. Three values on a single model with no held-out selection set cannot establish optimality, and the paired tests above are the only evidence about whether the observed differences exceed sampling noise.

**12. Narrowest evidence-supported statement for the camera-ready.** On AirCypher-150 with `qwen2.5-coder:32b` and DKB+Hybrid, holding the published exemplar cap of 8 fixed, varying the retrieved share k over {1, 3, 5} moves strict VM-F1 within a 0.556-0.655 band and strict RMEM within a 0.200-0.307 band. Paired exact tests reject equality of k=3 with both k=1 (p = 0.002494) and k=5 (p = 0.000145) under RMEM, so the results are NOT indifferent to k and the a-priori choice cannot be described as immaterial. The paired VM-F1 bootstrap separates k=3 from k=1 (CI [0.0405, 0.1595]) but not from k=5 (CI [-0.0142, 0.0483]). The defensible statement is therefore: k=1 is measurably worse than k=3 on this benchmark, k=3 and k=5 are close on VM-F1 while differing on the stricter row-exact metric, and a single-model three-point sweep cannot establish which value is best in general.


### Interpretive caution

Much of the k=1 deficit is syntactic rather than semantic: 25 of its 40 execution failures are Cypher syntax errors, against 6 at k=3 and 1 at k=5. Displacing retrieved exemplars for static ones evidently costs surface-form correctness first. Note also that CV and ES rise monotonically with k (CV 0.8333 -> 0.96 -> 0.9933) while RMEM does not (0.2 -> 0.3067 -> 0.2): more retrieved exemplars keep producing runnable queries, but not more right answers. This non-monotonicity is the reason no optimum is claimed.

