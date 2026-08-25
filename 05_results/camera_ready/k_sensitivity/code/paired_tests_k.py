#!/usr/bin/env python3
"""PHASE 7 — paired analysis across k on the same 150 questions.

Binary RMEM: exact McNemar (two-sided exact binomial on the discordant pairs,
p = 2 * P(X <= min(b,c)) with X ~ Bin(b+c, 0.5), clipped at 1.0) — the same
exact-test convention as the audited `exact_paired_tests_rmem.py`.
Continuous VM-F1: no new parametric test; paired question-level differences with
a 10,000-resample percentile bootstrap over the 150 question ids, seed 20260824.
"""
import csv, random
from math import comb
import os
from pathlib import Path
KS = Path(os.environ.get("KS_DIR", Path(__file__).resolve().parent.parent))
BOOT_SEED, BOOT_N = 20260824, 10000
rows = list(csv.DictReader((KS/"results/k_sensitivity_per_query.csv").open()))
def f(x): return None if x in ("", "None") else float(x)
by = {}
for r in rows: by[(r["retrieval_k"], r["question_id"])] = r
qids = sorted({r["question_id"] for r in rows})

def exact_mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    m = min(b, c)
    tail = sum(comb(n, i) for i in range(m+1)) / (2**n)
    return min(1.0, 2*tail)

pt = []
for metric in ("RMEM_strict", "RMEM_tolerant"):
    for comp in ("1", "5"):
        pairs = [(f(by[("3", q)][metric]), f(by[(comp, q)][metric])) for q in qids]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        both = sum(1 for a, b in pairs if a == 1 and b == 1)
        k3o  = sum(1 for a, b in pairs if a == 1 and b == 0)
        cmo  = sum(1 for a, b in pairs if a == 0 and b == 1)
        neither = sum(1 for a, b in pairs if a == 0 and b == 0)
        n = len(pairs)
        pt.append(dict(metric=metric, comparison=f"k3_vs_k{comp}", n_paired=n,
                       both_correct=both, k3_only_correct=k3o, comparator_only_correct=cmo,
                       both_wrong=neither,
                       k3_accuracy=round((both+k3o)/n, 4),
                       comparator_accuracy=round((both+cmo)/n, 4),
                       accuracy_difference_k3_minus_comparator=round((k3o-cmo)/n, 4),
                       n_discordant=k3o+cmo,
                       test="exact McNemar (two-sided exact binomial on discordant pairs)",
                       two_sided_exact_p=round(exact_mcnemar(k3o, cmo), 6)))
p1 = KS/"results/k_sensitivity_paired_tests.csv"
with p1.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(pt[0])); w.writeheader(); w.writerows(pt)

bs = []
for metric in ("VM_F1_strict", "VM_F1_tolerant"):
    for comp in ("1", "5"):
        d = []
        for q in qids:
            a, b = f(by[("3", q)][metric]), f(by[(comp, q)][metric])
            if a is not None and b is not None: d.append((q, a-b))
        n = len(d)
        obs = sum(x for _, x in d)/n
        rng = random.Random(BOOT_SEED)
        vals = [x for _, x in d]
        means = []
        for _ in range(BOOT_N):
            means.append(sum(vals[rng.randrange(n)] for _ in range(n))/n)
        means.sort()
        lo, hi = means[int(0.025*BOOT_N)], means[int(0.975*BOOT_N)-1]
        bs.append(dict(metric=metric, comparison=f"k3_minus_k{comp}", n_paired=n,
                       mean_k3=round(sum(f(by[("3", q)][metric]) for q, _ in d)/n, 4),
                       mean_comparator=round(sum(f(by[(comp, q)][metric]) for q, _ in d)/n, 4),
                       mean_paired_difference=round(obs, 4),
                       n_questions_k3_higher=sum(1 for _, x in d if x > 0),
                       n_questions_equal=sum(1 for _, x in d if x == 0),
                       n_questions_comparator_higher=sum(1 for _, x in d if x < 0),
                       bootstrap_resamples=BOOT_N, bootstrap_seed=BOOT_SEED,
                       ci95_low=round(lo, 4), ci95_high=round(hi, 4),
                       ci_excludes_zero=int(not (lo <= 0 <= hi))))
p2 = KS/"results/k_sensitivity_bootstrap.csv"
with p2.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(bs[0])); w.writeheader(); w.writerows(bs)
print("wrote", p1); print("wrote", p2)
for r in pt: print(r["metric"], r["comparison"], "p=", r["two_sided_exact_p"], "diff=", r["accuracy_difference_k3_minus_comparator"])
for r in bs: print(r["metric"], r["comparison"], r["mean_paired_difference"], (r["ci95_low"], r["ci95_high"]))
