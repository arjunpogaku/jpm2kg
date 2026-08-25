#!/usr/bin/env python3
"""PHASE 3 — byte-identity of historical DKB+Hybrid prompt vs new k=3 prompt.

Arm A is produced by calling the UNMODIFIED historical
`QueryGenerationSystems.dkb_hybrid` with the Ollama call intercepted, so the
prompt captured is exactly the string the submitted experiment sent.
Arm B is produced by the new k-parameterised wrapper at k=3.
"""
import csv, hashlib, json, sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(os.environ.get("PM25_ROOT", Path(__file__).resolve().parents[5])); sys.path.insert(0, str(ROOT))

import pipeline.systems as S
from k_systems import build_prompt

OUT = Path(__file__).resolve().parents[1]
BENCH = ROOT/"02_benchmark/aircypher150_benchmark.json"
bench = json.loads(BENCH.read_text())

# pick >=2 questions per category (12 total), spread across the benchmark
by_cat = {}
for q in bench:
    by_cat.setdefault(q["category"], []).append(q)
sample = []
for cat, qs in sorted(by_cat.items()):
    step = max(1, len(qs)//3)
    sample += qs[::step][:3]

CAPTURED = {}
def fake_ollama(model, prompt, timeout=None):
    CAPTURED["prompt"] = prompt
    raise RuntimeError("intercepted-for-prompt-capture")
S._call_ollama = fake_ollama                     # in-memory only; file untouched
sysobj = S.QueryGenerationSystems()

rows, n_ident = [], 0
for q in sample:
    nl = q["nl_query"]
    CAPTURED.clear()
    hist = sysobj.dkb_hybrid(nl, "qwen2.5-coder:32b")   # historical path, k hard-coded 3
    A = CAPTURED["prompt"]
    B, ids = build_prompt(nl, k=3)
    ha, hb = (hashlib.sha256(x.encode()).hexdigest() for x in (A, B))
    ident = A == B
    n_ident += ident
    rows.append(dict(query_id=q["query_id"], category=q["category"],
                     historical_prompt_sha256=ha, new_k3_prompt_sha256=hb,
                     historical_len=len(A), new_k3_len=len(B),
                     retrieved_exemplar_ids="|".join(ids),
                     byte_identical=int(ident),
                     first_diff_offset=(-1 if ident else next(
                         (i for i in range(min(len(A), len(B))) if A[i] != B[i]), min(len(A), len(B))))))

with (OUT/"prompt_equivalence.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"{n_ident}/{len(rows)} prompts byte-identical")
print("categories:", sorted({r['category'] for r in rows}))
sys.exit(0 if n_ident == len(rows) else 1)
