#!/usr/bin/env python3
"""PHASE 5 — camera-ready metrics for the k-sweep results.

Metric definitions are taken verbatim from the audited camera-ready script
`camera_ready_audit/scripts/exact_result_evaluation.py`:
  VM-F1  = QueryEvaluator._multiset_f1 over flattened normalised cell values
  RMEM   = exact equality of the Counter over alias-insensitive, row-preserving
           normalised row tuples
  strict   -> reference is the gold query as published
  tolerant -> max(strict, relaxed) where relaxed drops the
              `WHERE p.pm25 >= 0 AND p.pm25 <= 500` validity clause from the gold
CV/ES/EM come from the inline QueryEvaluator scoring done at generation time.

Non-destructive: reads the audited execution cache but writes its own copy under
k_sensitivity/results/. No v2/v3 result file is touched.
"""
import csv, json, logging, pickle, re, sys
from collections import Counter
import os
from pathlib import Path
logging.getLogger('neo4j.notifications').setLevel(logging.ERROR)

ROOT = Path(os.environ.get("PM25_ROOT", Path(__file__).resolve().parents[5]))
PKG  = ROOT
KS   = ROOT/"camera_ready_audit/k_sensitivity"
sys.path.insert(0, str(PKG/"04_pipeline"))
from evaluator import QueryEvaluator            # READ-ONLY reuse

ev = QueryEvaluator()
VALIDITY_CLAUSE = re.compile(r"\s*WHERE\s+p\.pm25\s*>=\s*0\s+AND\s+p\.pm25\s*<=\s*500\s+", re.I)
def relax(c):
    return None if not VALIDITY_CLAUSE.findall(c or "") else VALIDITY_CLAUSE.sub(" ", c).strip()

def _sortkey(v): return (type(v).__name__, repr(v))
def row_multiset(rows):
    out = Counter()
    for r in (rows or [])[:200]:
        cells = [ev._norm_value(v) for v in r.values()]
        out[tuple(sorted((c for c in cells if c is not None), key=_sortkey))] += 1
    return out

# seed from the audited cache (read-only), persist into our own file
SEED = ROOT/"camera_ready_audit/results/exec_cache.pkl"
MINE = KS/"results/exec_cache_k.pkl"
CACHE = {}
for p in (SEED, MINE):
    if p.exists():
        try: CACHE.update(pickle.loads(p.read_bytes()))
        except Exception: pass
def normed(c):
    if c not in CACHE:
        ok, rows, err = ev._run_query(c)
        CACHE[c] = (ok, ev._value_multiset(rows) if ok else None,
                    row_multiset(rows) if ok else None, err)
    return CACHE[c]

bench = {q["query_id"]: q for q in json.loads((PKG/"02_benchmark/aircypher150_benchmark.json").read_text())}
rows = []
for k in (1, 3, 5):
    f = KS/f"results/k{k}.jsonl"
    recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    ids = [r["query_id"] for r in recs]
    assert len(ids) == 150 and len(set(ids)) == 150, f"k={k}: {len(ids)} records, {len(set(ids))} unique"
    for r in recs:
        q = bench[r["query_id"]]
        gold = r["gold_cypher"]; rel = relax(gold)
        gen = r.get("generated_cypher")
        gok, gvals, grms, gerr = (False, None, None, r.get("eval_error") or "empty query")
        if gen: gok, gvals, grms, gerr = normed(gen)
        S = normed(gold); R = normed(rel) if rel else None
        def vmf1(ref):
            if ref is None or not ref[0]: return None
            return 0.0 if gvals is None else ev._multiset_f1(gvals, ref[1])
        def rmem(ref):
            if ref is None or not ref[0]: return None
            return 0 if grms is None else int(grms == ref[2])
        vm_s, vm_r = vmf1(S), vmf1(R)
        rm_s, rm_r = rmem(S), rmem(R)
        m = r["metrics"]
        rows.append(dict(
            question_id=r["query_id"], category=q["category"], complexity=q.get("complexity", ""),
            retrieval_k=r["retrieval_k"],
            retrieved_exemplar_ids="|".join(r["retrieved_exemplar_ids"]),
            generated_cypher=(gen or ""),
            CV=m["CV"], ES=m["ES"], EM=m["EM"],
            VM_F1_strict=vm_s, VM_F1_tolerant=max([x for x in (vm_s, vm_r) if x is not None], default=None),
            RMEM_strict=rm_s, RMEM_tolerant=max([x for x in (rm_s, rm_r) if x is not None], default=None),
            generation_latency=round(r["generation_time_ms"]/1000.0, 3),
            execution_status=("no_generation" if not gen else "executed" if gok else "execution_failure"),
            execution_error=(gerr or "")[:120],
            gold_has_validity_filter=int(rel is not None),
            reference_ok=int(S[0]),
        ))
    print(f"k={k}: 150 unique ids OK", flush=True)

MINE.write_bytes(pickle.dumps(CACHE))
out = KS/"results/k_sensitivity_per_query.csv"
with out.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")
