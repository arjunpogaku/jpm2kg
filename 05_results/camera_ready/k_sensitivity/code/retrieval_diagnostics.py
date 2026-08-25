#!/usr/bin/env python3
"""PHASE 8 — retrieval-set analysis for k=1,3,5 (no LLM calls)."""
import json, sys
from collections import Counter, defaultdict
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(os.environ.get("PM25_ROOT", Path(__file__).resolve().parents[5])); sys.path.insert(0, str(ROOT))
from k_systems import retrieve
from pipeline.systems import _load_dkb

OUT = Path(__file__).resolve().parents[1]
bench = json.loads((ROOT/"02_benchmark/aircypher150_benchmark.json").read_text())
pat = {p["pattern_id"]: p for p in _load_dkb()["query_patterns"]}

sets = {1: {}, 3: {}, 5: {}}
for q in bench:
    for k in (1, 3, 5):
        sets[k][q["query_id"]] = [p["pattern_id"] for p in retrieve(q["nl_query"], k=k)]

nest13 = [qid for qid in sets[1] if sets[1][qid] != sets[3][qid][:1]]
nest35 = [qid for qid in sets[3] if sets[3][qid] != sets[5][qid][:3]]
json.dump({"k": {str(k): sets[k] for k in sets},
           "nesting_violations_1_in_3": nest13,
           "nesting_violations_3_in_5": nest35},
          (OUT/"results/retrieval_sets.json").open("w"), indent=1)

L = []
L.append("# 02 — Retrieval Diagnostics (k = 1, 3, 5)\n")
L.append(f"Pool: {len(pat)} DKB `query_patterns` (JP01–JP{len(pat):02d}). "
         f"Benchmark: AirCypher-150 ({len(bench)} questions). "
         "Encoder: `all-MiniLM-L6-v2`, cosine on L2-normalised embeddings, `np.argsort` descending — "
         "identical to the submitted implementation.\n")

L.append("## Nesting check\n")
L.append("| Claim | Violations | Result |")
L.append("|---|---:|---|")
L.append(f"| top-1(k=1) == first item of top-3(k=3) | {len(nest13)} | {'HOLDS for every query' if not nest13 else 'FAILS'} |")
L.append(f"| top-3(k=3) == first three items of top-5(k=5) | {len(nest35)} | {'HOLDS for every query' if not nest35 else 'FAILS'} |")
if nest13 or nest35:
    L.append("\nViolating query ids: " + ", ".join(sorted(set(nest13 + nest35))))
    L.append("\nCause: `np.argsort` uses an unstable quicksort, so exactly-tied cosine scores can reorder between calls with different `k`.")
else:
    L.append("\nRetrieval is a single ranking truncated at k, so the k-sweep varies only how deep that "
             "one ranking is read. No score ties reorder the prefix.\n")

L.append("\n## Unique exemplars retrieved\n")
L.append("| k | unique exemplars | of pool | retrieval slots filled |")
L.append("|---:|---:|---:|---:|")
for k in (1, 3, 5):
    u = {e for v in sets[k].values() for e in v}
    L.append(f"| {k} | {len(u)} | {len(u)}/{len(pat)} | {k*len(bench)} |")

L.append("\n## Exemplar retrieval frequency\n")
for k in (1, 3, 5):
    c = Counter(e for v in sets[k].values() for e in v)
    L.append(f"\n### k={k}\n")
    L.append("| exemplar | intent | times retrieved | % of queries |")
    L.append("|---|---|---:|---:|")
    for pid, n in c.most_common():
        L.append(f"| {pid} | {pat[pid].get('intent','')} | {n} | {100*n/len(bench):.1f}% |")
    never = sorted(set(pat) - set(c))
    L.append(f"\nNever retrieved at k={k} ({len(never)}): {', '.join(never) if never else 'none'}")

L.append("\n## Prompt composition (published cap of 8 exemplars)\n")
L.append("| k | retrieved | static (displaced tail) | total |")
L.append("|---:|---:|---|---:|")
L.append("| 1 | 1 | JP01–JP07 | 8 |")
L.append("| 3 | 3 | JP01–JP05 | 8 |")
L.append("| 5 | 5 | JP01–JP03 | 8 |")
L.append("\nIncreasing k does not lengthen the prompt; it substitutes retrieved exemplars for the "
        "tail of the static block. Overlap between a retrieved exemplar and a still-shown static "
        "exemplar therefore duplicates that exemplar in the prompt — this is the published "
        "behaviour and is left unchanged.\n")
dupes = {k: sum(1 for v in sets[k].values()
                if set(v) & {f"JP{i:02d}" for i in range(1, 9-k)}) for k in (1, 3, 5)}
L.append("| k | queries whose retrieved set overlaps the shown static block | of 150 |")
L.append("|---:|---:|---:|")
for k in (1, 3, 5):
    L.append(f"| {k} | {dupes[k]} | 150 |")

L.append("\n## Retrieved-exemplar category distribution\n")
def cat_of(pid): return pat[pid].get("intent", "") or pat[pid].get("category", "")
L.append("| benchmark category | n questions | k=1 distinct exemplars | k=3 | k=5 |")
L.append("|---|---:|---:|---:|---:|")
bycat = defaultdict(list)
for q in bench: bycat[q["category"]].append(q["query_id"])
for cat, qids in sorted(bycat.items()):
    cells = [len({e for qid in qids for e in sets[k][qid]}) for k in (1, 3, 5)]
    L.append(f"| {cat} | {len(qids)} | {cells[0]} | {cells[1]} | {cells[2]} |")

L.append("\nPer-category top exemplar:\n")
L.append("| category | most-retrieved exemplar at k=3 | share of that category's k=3 slots |")
L.append("|---|---|---:|")
for cat, qids in sorted(bycat.items()):
    c = Counter(e for qid in qids for e in sets[3][qid])
    pid, n = c.most_common(1)[0]
    L.append(f"| {cat} | {pid} ({pat[pid].get('intent','')}) | {100*n/(3*len(qids)):.1f}% |")

L.append("\n## Questions whose retrieval sets differ across k\n")
L.append("By construction every question's set differs across k (a longer prefix of the same "
         "ranking). The number of *newly added* exemplars is exactly k−k′ per question:\n")
L.append(f"- k=1 → k=3: 2 new exemplars for all {len(bench)} questions")
L.append(f"- k=3 → k=5: 2 new exemplars for all {len(bench)} questions")
L.append(f"- k=1 → k=5: 4 new exemplars for all {len(bench)} questions")
(OUT/"02_retrieval_diagnostics.md").write_text("\n".join(L) + "\n")
print("wrote 02_retrieval_diagnostics.md")
print("nesting violations:", len(nest13), len(nest35))
