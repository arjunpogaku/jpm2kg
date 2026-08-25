#!/usr/bin/env python3
"""
camera_ready_evaluator.py — camera-ready result evaluation for AirCypher-150.

Computes, for every record in a results JSONL, the four camera-ready result
scores by RE-EXECUTING the stored Cypher against a live JPM2KG instance:

    VM-F1  strict / tolerant   (continuous, partial credit)
    RMEM   strict / tolerant   (binary, exact result agreement)

See METRICS.md for the definitions. Nothing here changes the raw JSONL: it is
opened read-only, and the historical `metrics.SE` value is carried through to
the output as `original_saved_value_multiset_F1` for comparison.

This is a cleaned public version of the audited camera-ready implementation.
The metric semantics are identical to the audited script; only packaging,
configuration and comments differ.

Metric internals are reused from the submitted `evaluator.py`
(`_run_query`, `_norm_value`, `_value_multiset`, `_multiset_f1`) so that
execution behaviour — the 200-row cap and the 30 s server-side timeout — stays
identical to the behaviour that produced the reported numbers. RMEM is the one
genuinely new piece and is defined below.

Usage
-----
    export NEO4J_PASSWORD=...            # see .env.example
    python3 camera_ready_evaluator.py \
        --raw       ../05_results/raw/results_full.jsonl \
        --benchmark ../02_benchmark/aircypher150_benchmark.json \
        --out       ../05_results/camera_ready/recomputed

Options:
    --limit N        evaluate only the first N records (smoke test)
    --cache PATH     execution cache file (default: <out>/exec_cache.pkl).
                     Each distinct Cypher string is executed exactly once;
                     keep the cache between runs, some reference queries scan
                     71M nodes.

Runtime warning: a full 3,750-record pass executes several thousand distinct
queries against a 142M-node graph and takes hours on a cold cache.
"""

from __future__ import annotations

import argparse
import atexit
import csv
import json
import logging
import pickle
import re
import sys
from collections import Counter
from pathlib import Path

# Neo4j emits a notification per query for unindexed property lookups; at this
# volume that is pure noise.
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluator import QueryEvaluator  # noqa: E402  (metric internals, reused)


# ── Tolerant evaluation: relaxing the numerical-validity predicate ────────────
#
# Tolerant evaluation removes ONLY `WHERE p.pm25 >= 0 AND p.pm25 <= 500` from a
# reference query. Every other part of the reference semantics is untouched, and
# references that do not contain the predicate are not relaxed at all.

VALIDITY_CLAUSE = re.compile(
    r"\s*WHERE\s+p\.pm25\s*>=\s*0\s+AND\s+p\.pm25\s*<=\s*500\s+", re.IGNORECASE
)


def relax_reference(cypher: str):
    """Return (relaxed_cypher, n_removed), or (None, 0) if nothing to remove."""
    n = len(VALIDITY_CLAUSE.findall(cypher or ""))
    if n == 0:
        return None, 0
    return VALIDITY_CLAUSE.sub(" ", cypher).strip(), n


# ── RMEM: Row-Multiset Exact Match ───────────────────────────────────────────

def _sort_key(v):
    """Deterministic total order over normalized primitive cells of mixed type."""
    return (type(v).__name__, repr(v))


def row_multiset(evaluator: QueryEvaluator, rows) -> Counter:
    """
    Turn a result set into a Counter over normalized row tuples.

    Each row becomes the tuple of its normalized primitive cells, sorted with
    `_sort_key`. Sorting *within* the row buys insensitivity to column aliases
    and column order while keeping the cells of one row together — that row
    grouping is exactly what VM-F1's flattening throws away.

    The Counter makes row ORDER irrelevant while preserving row MULTIPLICITY.
    The 200-row cap matches the submitted executor and applies to both sides.
    """
    out: Counter = Counter()
    for r in (rows or [])[:200]:
        cells = [evaluator._norm_value(v) for v in r.values()]
        out[tuple(sorted((c for c in cells if c is not None), key=_sort_key))] += 1
    return out


class CameraReadyEvaluator:
    """Executes queries once each, caching the normalized forms both metrics need."""

    def __init__(self, cache_path: Path | None = None):
        self.ev = QueryEvaluator()
        self.cache_path = cache_path
        # cypher -> (ok, value_multiset | None, row_multiset | None, error | None)
        self.cache = {}
        if cache_path and cache_path.exists():
            self.cache = pickle.loads(cache_path.read_bytes())
        atexit.register(self.save_cache)

    def save_cache(self):
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_bytes(pickle.dumps(self.cache))

    def close(self):
        self.save_cache()
        self.ev.close()

    def normalized(self, cypher: str):
        """Execute `cypher` at most once ever; return both normalized forms."""
        if cypher not in self.cache:
            ok, rows, err = self.ev._run_query(cypher)
            self.cache[cypher] = (
                ok,
                self.ev._value_multiset(rows) if ok else None,
                row_multiset(self.ev, rows) if ok else None,
                err,
            )
            if len(self.cache) % 200 == 0:
                self.save_cache()
        return self.cache[cypher]

    # -- the two metrics -------------------------------------------------------

    def vm_f1(self, gen_values, ref):
        """Continuous value-multiset F1. None if the reference is unusable."""
        if ref is None or not ref[0]:
            return None
        if gen_values is None:      # generated query failed or was empty
            return 0.0
        return self.ev._multiset_f1(gen_values, ref[1])

    def rmem(self, gen_rows, ref):
        """Binary row-multiset exact match. None if the reference is unusable."""
        if ref is None or not ref[0]:
            return None
        if gen_rows is None:
            return 0
        return int(gen_rows == ref[2])


FIELDNAMES = [
    "query_id", "category", "complexity", "model", "prompting_configuration",
    "gold_has_validity_filter", "generated_executed", "generated_error",
    "original_saved_value_multiset_F1",
    "reexecuted_value_multiset_F1", "relaxed_value_multiset_F1",
    "tolerant_value_multiset_F1",
    "RMEM_strict", "RMEM_relaxed", "RMEM_tolerant",
    "reference_ok", "reference_error",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(__file__).resolve().parent
    ap.add_argument("--raw", type=Path,
                    default=here.parent / "05_results/raw/results_full.jsonl",
                    help="results JSONL (read-only)")
    ap.add_argument("--benchmark", type=Path,
                    default=here.parent / "02_benchmark/aircypher150_benchmark.json")
    ap.add_argument("--out", type=Path,
                    default=here.parent / "05_results/camera_ready/recomputed",
                    help="output directory")
    ap.add_argument("--limit", type=int, default=0, help="evaluate only first N records")
    ap.add_argument("--cache", type=Path, default=None,
                    help="execution cache path (default: <out>/exec_cache.pkl)")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cache_path = args.cache or (args.out / "exec_cache.pkl")

    bench = {q["query_id"]: q for q in json.loads(args.benchmark.read_text())}
    relaxed = {}
    for qid, q in bench.items():
        rel, _ = relax_reference(q["gold_cypher"])
        if rel is not None:
            relaxed[qid] = rel
    print(f"benchmark: {len(bench)} items, "
          f"{len(relaxed)} carry the validity predicate", flush=True)

    records = [json.loads(line) for line in args.raw.open() if line.strip()]
    if args.limit:
        records = records[: args.limit]
    print(f"records: {len(records)}", flush=True)

    cre = CameraReadyEvaluator(cache_path)
    rows_out = []
    try:
        for i, rec in enumerate(records, 1):
            qid = rec["query_id"]
            gold = rec["gold_cypher"]
            gen = rec.get("generated_cypher")

            gen_ok, gen_values, gen_rows, gen_err = False, None, None, "empty query"
            if gen:
                gen_ok, gen_values, gen_rows, gen_err = cre.normalized(gen)

            strict_ref = cre.normalized(gold)
            rel = relaxed.get(qid)
            relaxed_ref = cre.normalized(rel) if rel else None

            vm_strict = cre.vm_f1(gen_values, strict_ref)
            vm_relaxed = cre.vm_f1(gen_values, relaxed_ref)
            rm_strict = cre.rmem(gen_rows, strict_ref)
            rm_relaxed = cre.rmem(gen_rows, relaxed_ref)

            # Tolerant = best of strict and relaxed-reference scoring.
            vm_tol = max([v for v in (vm_strict, vm_relaxed) if v is not None],
                         default=None)
            rm_tol = max([v for v in (rm_strict, rm_relaxed) if v is not None],
                         default=None)

            rows_out.append({
                "query_id": qid,
                "category": rec.get("query_type", ""),
                "complexity": rec.get("complexity", ""),
                "model": rec["llm"],
                "prompting_configuration": rec["system"],
                "gold_has_validity_filter": int(rel is not None),
                "generated_executed": int(gen_ok),
                "generated_error": (gen_err or "")[:120],
                # historical VM-F1, stored in the raw JSONL under the legacy name SE
                "original_saved_value_multiset_F1": rec["metrics"]["SE"],
                "reexecuted_value_multiset_F1": vm_strict,
                "relaxed_value_multiset_F1": vm_relaxed,
                "tolerant_value_multiset_F1": vm_tol,
                "RMEM_strict": rm_strict,
                "RMEM_relaxed": rm_relaxed,
                "RMEM_tolerant": rm_tol,
                "reference_ok": int(strict_ref[0]),
                "reference_error": (strict_ref[3] or "")[:120],
            })

            if i % 50 == 0:
                print(f"  {i}/{len(records)}  cached queries={len(cre.cache)}", flush=True)
    finally:
        cre.close()

    dest = args.out / "camera_ready_result_evaluation.csv"
    with dest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows_out)
    print(f"wrote {dest}  ({len(rows_out)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
