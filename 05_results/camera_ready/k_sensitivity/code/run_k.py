#!/usr/bin/env python3
"""PHASE 4 — fresh DKB+Hybrid generations for one retrieval k on AirCypher-150.

Mirrors ExperimentRunner._run_single's record schema and inline CV/ES/EM/SE/RQ
scoring, using the unmodified QueryEvaluator. One output file per k; append-only
with resume on query_id. Generation settings come from the unmodified
pipeline/systems.py (_call_ollama): temperature 0.0, num_predict 512,
num_ctx 8192, stream false, think false, no seed.
"""
import argparse, json, sys, time
from datetime import datetime, timezone
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(os.environ.get("PM25_ROOT", Path(__file__).resolve().parents[5])); sys.path.insert(0, str(ROOT))

from k_systems import dkb_hybrid_k
from pipeline.evaluator import QueryEvaluator

BENCH = ROOT/"02_benchmark/aircypher150_benchmark.json"
LLM = "qwen2.5-coder:32b"

ap = argparse.ArgumentParser()
ap.add_argument("--k", type=int, required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
done = set()
if out.exists():
    for line in out.read_text().splitlines():
        if line.strip():
            done.add(json.loads(line)["query_id"])

bench = json.loads(BENCH.read_text())
ev = QueryEvaluator(exec_timeout_s=30)
t_start = time.time()

for i, q in enumerate(bench, 1):
    if q["query_id"] in done:
        continue
    nl, gold = q["nl_query"], q.get("cypher", q.get("gold_cypher", ""))
    g = dkb_hybrid_k(nl, LLM, k=a.k)
    gen = g["generated_cypher"]
    if gen:
        try:
            metrics = ev.evaluate_all(gen, gold, nl)
        except Exception as e:
            metrics = {"CV": 0.0, "ES": 0.0, "EM": 0.0, "SE": 0.0, "RQ": 0.0, "_error": str(e)[:150]}
    else:
        metrics = {"CV": 0.0, "ES": 0.0, "EM": 0.0, "SE": 0.0, "RQ": 0.0, "_error": g["error"]}
    err = metrics.pop("_error", None); metrics.pop("_eval_ms", None)
    rec = {
        "query_id": q["query_id"], "nl_query": nl, "gold_cypher": gold,
        "query_type": q.get("type", q.get("category", "")),
        "category": q.get("category", ""), "complexity": q.get("complexity", ""),
        "system": "dkb_hybrid", "llm": LLM,
        "retrieval_k": a.k, "retrieved_exemplar_ids": g["retrieved_exemplar_ids"],
        "generated_cypher": gen, "metrics": metrics,
        "generation_time_ms": g["generation_time_ms"],
        "eval_error": err or g["error"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with out.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    if i % 10 == 0:
        print(f"k={a.k} {i}/150  elapsed={time.time()-t_start:.0f}s", flush=True)

ids = [json.loads(l)["query_id"] for l in out.read_text().splitlines() if l.strip()]
print(f"k={a.k} DONE records={len(ids)} unique={len(set(ids))}")
