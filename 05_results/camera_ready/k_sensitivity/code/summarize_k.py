#!/usr/bin/env python3
"""PHASE 6 — pooled and per-category summary of the k-sweep."""
import csv, statistics as st
import os
from pathlib import Path
KS = Path(os.environ.get("KS_DIR", Path(__file__).resolve().parent.parent))
rows = list(csv.DictReader((KS/"results/k_sensitivity_per_query.csv").open()))
def f(x): return None if x in ("", "None") else float(x)

def block(rs):
    n = len(rs)
    vs = [f(r["VM_F1_strict"]) for r in rs if f(r["VM_F1_strict"]) is not None]
    vt = [f(r["VM_F1_tolerant"]) for r in rs if f(r["VM_F1_tolerant"]) is not None]
    rs_ = [f(r["RMEM_strict"]) for r in rs if f(r["RMEM_strict"]) is not None]
    rt_ = [f(r["RMEM_tolerant"]) for r in rs if f(r["RMEM_tolerant"]) is not None]
    return dict(
        n_questions=n,
        CV=round(sum(f(r["CV"]) for r in rs)/n, 4),
        ES=round(sum(f(r["ES"]) for r in rs)/n, 4),
        EM=round(sum(f(r["EM"]) for r in rs)/n, 4),
        VM_F1_strict=round(sum(vs)/len(vs), 4), VM_F1_strict_n=len(vs),
        VM_F1_tolerant=round(sum(vt)/len(vt), 4), VM_F1_tolerant_n=len(vt),
        RMEM_strict=round(sum(rs_)/len(rs_), 4), RMEM_strict_correct=int(sum(rs_)), RMEM_strict_n=len(rs_),
        RMEM_tolerant=round(sum(rt_)/len(rt_), 4), RMEM_tolerant_correct=int(sum(rt_)), RMEM_tolerant_n=len(rt_),
        median_generation_latency_s=round(st.median(f(r["generation_latency"]) for r in rs), 3),
        mean_generation_latency_s=round(sum(f(r["generation_latency"]) for r in rs)/n, 3),
        n_execution_failure=sum(1 for r in rs if r["execution_status"] == "execution_failure"),
        n_no_generation=sum(1 for r in rs if r["execution_status"] == "no_generation"),
    )

out = []
for k in ("1", "3", "5"):
    sub = [r for r in rows if r["retrieval_k"] == k]
    out.append(dict(retrieval_k=k, category="ALL", **block(sub)))
for cat in sorted({r["category"] for r in rows}):
    for k in ("1", "3", "5"):
        sub = [r for r in rows if r["retrieval_k"] == k and r["category"] == cat]
        out.append(dict(retrieval_k=k, category=cat, **block(sub)))

p = KS/"results/k_sensitivity_summary.csv"
with p.open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print("wrote", p)
for r in out[:3]:
    print(r["retrieval_k"], r["VM_F1_strict"], r["VM_F1_tolerant"], r["RMEM_strict"], r["RMEM_tolerant"])
