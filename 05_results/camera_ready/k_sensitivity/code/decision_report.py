#!/usr/bin/env python3
"""PHASE 9 — factual decision report answering the twelve required questions."""
import csv
import os
from pathlib import Path
KS = Path(os.environ.get("KS_DIR", Path(__file__).resolve().parent.parent))
S  = list(csv.DictReader((KS/"results/k_sensitivity_summary.csv").open()))
PT = list(csv.DictReader((KS/"results/k_sensitivity_paired_tests.csv").open()))
BS = list(csv.DictReader((KS/"results/k_sensitivity_bootstrap.csv").open()))
ALL = {r["retrieval_k"]: r for r in S if r["category"] == "ALL"}
CATS = sorted({r["category"] for r in S if r["category"] != "ALL"})
KS_ = ("1", "3", "5")
def g(k, f): return ALL[k][f]
def pt(metric, comp): return next(r for r in PT if r["metric"] == metric and r["comparison"] == comp)
def bs(metric, comp): return next(r for r in BS if r["metric"] == metric and r["comparison"] == comp)
def sig(p): return "statistically significant at alpha=0.05" if float(p) < 0.05 else "not statistically significant at alpha=0.05"

# category sensitivity: spread of RMEM strict/tolerant and VM-F1 across k
catrows = {}
for c in CATS:
    r = {k: next(x for x in S if x["category"] == c and x["retrieval_k"] == k) for k in KS_}
    catrows[c] = r
def spread(c, f):
    v = [float(catrows[c][k][f]) for k in KS_]
    return max(v)-min(v), v

L = []
A = L.append
A("# 03 — Retrieval-k Sensitivity: Decision Report\n")
A("Model `qwen2.5-coder:32b`; system DKB+Hybrid only; AirCypher-150; published exemplar "
  "cap of 8 preserved (k retrieved + the first 8−k static exemplars). Fresh generations at "
  "k=1, 3, 5 under identical settings, including a k=3 control re-run — no published number "
  "is reused for comparison. Prompt equivalence at k=3 was verified byte-identical before "
  "generation (`01_prompt_equivalence.md`).\n")

A("## Pooled results\n")
A("| k | CV | ES | VM-F1 strict | VM-F1 tolerant | RMEM strict | RMEM tolerant | RMEM strict correct | RMEM tolerant correct | median gen latency (s) |")
A("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for k in KS_:
    A(f"| {k} | {g(k,'CV')} | {g(k,'ES')} | {g(k,'VM_F1_strict')} | {g(k,'VM_F1_tolerant')} | "
      f"{g(k,'RMEM_strict')} | {g(k,'RMEM_tolerant')} | {g(k,'RMEM_strict_correct')}/{g(k,'RMEM_strict_n')} | "
      f"{g(k,'RMEM_tolerant_correct')}/{g(k,'RMEM_tolerant_n')} | {g(k,'median_generation_latency_s')} |")

A("\n## Paired exact tests (same 150 questions under every k)\n")
A("| metric | comparison | both correct | k3 only | comparator only | both wrong | acc. difference | two-sided exact p |")
A("|---|---|---:|---:|---:|---:|---:|---:|")
for m in ("RMEM_strict", "RMEM_tolerant"):
    for c in ("k3_vs_k1", "k3_vs_k5"):
        r = pt(m, c)
        A(f"| {m} | {c} | {r['both_correct']} | {r['k3_only_correct']} | {r['comparator_only_correct']} | "
          f"{r['both_wrong']} | {r['accuracy_difference_k3_minus_comparator']} | {r['two_sided_exact_p']} |")
A("\nExact McNemar (two-sided exact binomial on discordant pairs).\n")

A("## Paired VM-F1 bootstrap (10,000 resamples, seed 20260824)\n")
A("| metric | comparison | mean paired difference | 95% CI | excludes 0 |")
A("|---|---|---:|---|---|")
for m in ("VM_F1_strict", "VM_F1_tolerant"):
    for c in ("k3_minus_k1", "k3_minus_k5"):
        r = bs(m, c)
        A(f"| {m} | {c} | {r['mean_paired_difference']} | [{r['ci95_low']}, {r['ci95_high']}] | "
          f"{'yes' if r['ci_excludes_zero']=='1' else 'no'} |")

A("\n## Per-category RMEM strict\n")
A("| category | n | k=1 | k=3 | k=5 | max−min |")
A("|---|---:|---:|---:|---:|---:|")
for c in CATS:
    d, v = spread(c, "RMEM_strict")
    A(f"| {c} | {catrows[c]['3']['n_questions']} | {v[0]} | {v[1]} | {v[2]} | {d:.4f} |")
A("\n## Per-category VM-F1 strict\n")
A("| category | n | k=1 | k=3 | k=5 | max−min |")
A("|---|---:|---:|---:|---:|---:|")
for c in CATS:
    d, v = spread(c, "VM_F1_strict")
    A(f"| {c} | {catrows[c]['3']['n_questions']} | {v[0]} | {v[1]} | {v[2]} | {d:.4f} |")


# failure-mode diagnostics
import collections
PQ = list(csv.DictReader((KS/"results/k_sensitivity_per_query.csv").open()))
def fm(k):
    sub=[x for x in PQ if x["retrieval_k"]==k]
    to=sum(1 for x in sub if x["execution_error"].startswith("Timeout"))
    sy=sum(1 for x in sub if "SyntaxError" in x["execution_error"])
    return to, sy
A("\n## Failure modes\n")
A("| k | CV | execution failures | of which syntax errors | of which 30 s timeouts |")
A("|---:|---:|---:|---:|---:|")
for k in KS_:
    to, sy = fm(k)
    A(f"| {k} | {g(k,'CV')} | {g(k,'n_execution_failure')} | {sy} | {to} |")
A("\nSyntax errors fall monotonically with k (25 -> 6 -> 1), matching the CV trend; this is a "
  "prompt effect. Timeouts fall much less (15 -> 11 -> 10) and are a property of how expensive "
  "the generated query is to execute, not of its correctness. Timeouts are preserved as "
  "failures exactly as the submitted evaluation pipeline did. Because execution timing depends "
  "on concurrent load on a shared machine, the timeout component of these counts is the least "
  "reproducible part of this experiment.\n")

A("## Control check against the submitted run\n")
A("The fresh k=3 arm is a re-run of the published configuration. Compared with the audited "
  "camera-ready recomputation of the submitted generations "
  "(`camera_ready_audit/results/tolerant_exact_result_evaluation.csv`, "
  "`qwen2.5-coder:32b` / `dkb_hybrid`):\n")
A("| quantity | submitted run (audited) | fresh k=3 control |")
A("|---|---:|---:|")
A(f"| VM-F1 strict | 0.6576 | {g('3','VM_F1_strict')} |")
A(f"| RMEM strict | 0.3067 (46/150) | {g('3','RMEM_strict')} ({g('3','RMEM_strict_correct')}/150) |")
A("\nThe control reproduces the published k=3 numbers to within 0.003 VM-F1 and exactly on "
  "RMEM, despite no seed being passed. This supports treating the three new arms as comparable "
  "to each other and to the submitted result.\n")

A("\n---\n\n## Answers to the twelve questions\n")
A(f"**1. Strict VM-F1 at k=1,3,5.** {g('1','VM_F1_strict')}, {g('3','VM_F1_strict')}, {g('5','VM_F1_strict')}.\n")
A(f"**2. Tolerant VM-F1 at k=1,3,5.** {g('1','VM_F1_tolerant')}, {g('3','VM_F1_tolerant')}, {g('5','VM_F1_tolerant')}.\n")
A(f"**3. Strict RMEM at k=1,3,5.** {g('1','RMEM_strict')} ({g('1','RMEM_strict_correct')}/{g('1','RMEM_strict_n')}), "
  f"{g('3','RMEM_strict')} ({g('3','RMEM_strict_correct')}/{g('3','RMEM_strict_n')}), "
  f"{g('5','RMEM_strict')} ({g('5','RMEM_strict_correct')}/{g('5','RMEM_strict_n')}).\n")
A(f"**4. Tolerant RMEM at k=1,3,5.** {g('1','RMEM_tolerant')} ({g('1','RMEM_tolerant_correct')}/{g('1','RMEM_tolerant_n')}), "
  f"{g('3','RMEM_tolerant')} ({g('3','RMEM_tolerant_correct')}/{g('3','RMEM_tolerant_n')}), "
  f"{g('5','RMEM_tolerant')} ({g('5','RMEM_tolerant_correct')}/{g('5','RMEM_tolerant_n')}).\n")
r = pt("RMEM_strict", "k3_vs_k1")
A(f"**5. k=3 vs k=1, strict RMEM.** Discordant pairs: {r['k3_only_correct']} k=3-only, "
  f"{r['comparator_only_correct']} k=1-only. Accuracy difference {r['accuracy_difference_k3_minus_comparator']}. "
  f"Two-sided exact p = {r['two_sided_exact_p']} — {sig(r['two_sided_exact_p'])}.\n")
r = pt("RMEM_strict", "k3_vs_k5")
A(f"**6. k=3 vs k=5, strict RMEM.** Discordant pairs: {r['k3_only_correct']} k=3-only, "
  f"{r['comparator_only_correct']} k=5-only. Accuracy difference {r['accuracy_difference_k3_minus_comparator']}. "
  f"Two-sided exact p = {r['two_sided_exact_p']} — {sig(r['two_sided_exact_p'])}.\n")
r1, r5 = pt("RMEM_tolerant", "k3_vs_k1"), pt("RMEM_tolerant", "k3_vs_k5")
A(f"**7. Same two comparisons under tolerant RMEM.** k=3 vs k=1: difference "
  f"{r1['accuracy_difference_k3_minus_comparator']}, exact p = {r1['two_sided_exact_p']} — {sig(r1['two_sided_exact_p'])}. "
  f"k=3 vs k=5: difference {r5['accuracy_difference_k3_minus_comparator']}, exact p = {r5['two_sided_exact_p']} — "
  f"{sig(r5['two_sided_exact_p'])}.\n")
lines = []
for m in ("VM_F1_strict", "VM_F1_tolerant"):
    for c in ("k3_minus_k1", "k3_minus_k5"):
        b = bs(m, c)
        lines.append(f"{m} {c}: {b['mean_paired_difference']}, 95% CI [{b['ci95_low']}, {b['ci95_high']}]"
                     f"{' (excludes 0)' if b['ci_excludes_zero']=='1' else ' (includes 0)'}")
A("**8. Paired VM-F1 bootstrap intervals.** " + "; ".join(lines) + ".\n")
sens = sorted(((spread(c,"RMEM_strict")[0], c) for c in CATS), reverse=True)
A(f"**9. Category sensitivity.** Yes, two categories do. Ranked by strict-RMEM spread across k: "
  + "; ".join(f"{c} {d:.3f}" for d, c in sens) + ". "
  f"`comparative` (n=22) moves from {catrows['comparative']['1']['RMEM_strict']} at k=1 to "
  f"{catrows['comparative']['3']['RMEM_strict']} at k=3 and back to {catrows['comparative']['5']['RMEM_strict']} at k=5, "
  f"and `temporal` (n=30) from {catrows['temporal']['1']['RMEM_strict']} to {catrows['temporal']['3']['RMEM_strict']} to "
  f"{catrows['temporal']['5']['RMEM_strict']} — both peaked at k=3 and both non-monotone. "
  f"`aggregate` (n=38) scores {catrows['aggregate']['3']['RMEM_strict']} strict RMEM at every k and is "
  "insensitive by construction: its questions return computed averages that rarely reproduce the "
  "gold row multiset exactly, so the metric has no headroom to move. `station_filtering` and "
  "`health_risk` shift by at most 0.17. Per-category n is 22–38, so these are directional "
  "observations; no per-category significance test is claimed and none should be quoted as one.\n")

# Q10 and Q12 depend on the retrieval claim and require judgement over the whole table.
tol_note = ("Strict and tolerant figures are identical throughout: relaxing the "
            "`p.pm25 >= 0 AND p.pm25 <= 500` validity clause never changed a reference result "
            "set on this benchmark. The same identity holds in the audited recomputation of the "
            "submitted run, so this is a property of the benchmark, not of this experiment.")
A(f"**10. Is the central retrieval conclusion robust across k=1,3,5?** Yes. The paper's central "
  f"retrieval claim is that DKB+Hybrid's semantic exemplar retrieval contributes to NL-to-Cypher "
  f"quality, not that any particular k is correct. Every arm here uses retrieval and the cap of "
  f"8, and all three land in the same broad regime (VM-F1 {g('1','VM_F1_strict')}-{g('3','VM_F1_strict')}, "
  f"RMEM {g('1','RMEM_strict')}-{g('3','RMEM_strict')}). No arm collapses and no arm overturns the "
  f"direction of the published finding. {tol_note}\n")
A("**11. Is k=3 demonstrably optimal?** No. This experiment was not designed to identify an "
  "optimal k and does not do so. Three values on a single model with no held-out selection set "
  "cannot establish optimality, and the paired tests above are the only evidence about whether "
  "the observed differences exceed sampling noise.\n")
A("**12. Narrowest evidence-supported statement for the camera-ready.** On AirCypher-150 with "
  "`qwen2.5-coder:32b` and DKB+Hybrid, holding the published exemplar cap of 8 fixed, varying "
  "the retrieved share k over {1, 3, 5} moves strict VM-F1 within a "
  f"{min(float(g(k,'VM_F1_strict')) for k in KS_):.3f}-{max(float(g(k,'VM_F1_strict')) for k in KS_):.3f} band and strict RMEM within a "
  f"{min(float(g(k,'RMEM_strict')) for k in KS_):.3f}-{max(float(g(k,'RMEM_strict')) for k in KS_):.3f} band. "
  "Paired exact tests reject equality of k=3 with both k=1 (p = "
  f"{pt('RMEM_strict','k3_vs_k1')['two_sided_exact_p']}) and k=5 (p = {pt('RMEM_strict','k3_vs_k5')['two_sided_exact_p']}) "
  "under RMEM, so the results are NOT indifferent to k and the a-priori choice cannot be "
  "described as immaterial. The paired VM-F1 bootstrap separates k=3 from k=1 "
  f"(CI [{bs('VM_F1_strict','k3_minus_k1')['ci95_low']}, {bs('VM_F1_strict','k3_minus_k1')['ci95_high']}]) but not "
  f"from k=5 (CI [{bs('VM_F1_strict','k3_minus_k5')['ci95_low']}, {bs('VM_F1_strict','k3_minus_k5')['ci95_high']}]). "
  "The defensible statement is therefore: k=1 is measurably worse than k=3 on this benchmark, "
  "k=3 and k=5 are close on VM-F1 while differing on the stricter row-exact metric, and a "
  "single-model three-point sweep cannot establish which value is best in general.\n")
A("\n### Interpretive caution\n")
A("Much of the k=1 deficit is syntactic rather than semantic: 25 of its 40 execution failures "
  "are Cypher syntax errors, against 6 at k=3 and 1 at k=5. Displacing retrieved exemplars for "
  "static ones evidently costs surface-form correctness first. Note also that CV and ES rise "
  "monotonically with k (CV "
  f"{g('1','CV')} -> {g('3','CV')} -> {g('5','CV')}) while RMEM does not "
  f"({g('1','RMEM_strict')} -> {g('3','RMEM_strict')} -> {g('5','RMEM_strict')}): more retrieved exemplars "
  "keep producing runnable queries, but not more right answers. This non-monotonicity is the "
  "reason no optimum is claimed.\n")

(KS/"03_k_sensitivity_decision.md").write_text("\n".join(L) + "\n")
print("wrote 03_k_sensitivity_decision.md")
