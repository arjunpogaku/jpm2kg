# Evaluation Metrics

This file defines the four metrics reported in the camera-ready paper and
explains how they relate to the field names stored in the historical raw
results.

| Metric | Type | What it measures |
|---|---|---|
| **CV** — Cypher Validity | binary 0/1 | The query parses and references only real JPM2KG labels and relationship types. |
| **ES** — Execution Success | binary 0/1 | The query runs against the live graph without error inside the 30 s timeout. |
| **VM-F1** — Value-Multiset F1 | continuous [0,1] | Partial-credit overlap between the values in the generated and reference result sets. |
| **RMEM** — Row-Multiset Exact Match | binary 0/1 | Exact result agreement, with row grouping preserved and row order ignored. |

CV and ES say whether a query is *runnable*. VM-F1 and RMEM say whether it
returns the *intended answer*.

---

## VM-F1 — Value-Multiset F1

**This is the same quantity that the historical raw results store under
`metrics.SE`.** The submitted code named the field `SE` ("Set Equality"), but the
value it holds is a continuous, partial-credit F1 over value multisets, not a set
equality test. The camera-ready paper reports it under the accurate name
Value-Multiset F1. The numbers are unchanged; only the name is.

Computation:

1. Execute the generated query and the reference query (200-row cap, 30 s
   server-side timeout).
2. Flatten each result set into a multiset of normalized primitive cell values,
   **discarding column names and row boundaries**. Normalization: numbers are
   rounded to 2 decimal places, strings are stripped and casefolded, `None`
   becomes a sentinel, booleans are preserved, and non-primitive cells (nodes,
   relationships, maps, lists) are dropped.
3. `VM-F1 = 2PR / (P + R)` where `P` and `R` are multiset precision and recall of
   the generated multiset against the reference multiset.

Special cases: a generated query that fails or is empty scores 0.0. If the
*reference* query cannot execute, the record is excluded rather than scored.

Because column names and row boundaries are discarded, VM-F1 is insensitive to
column aliasing and column/row ordering, and it awards partial credit: 712 of the
3,750 historical records score strictly between 0 and 1.

## RMEM — Row-Multiset Exact Match

RMEM is the strict binary counterpart added for the camera-ready version. It
answers a different question: *did the query return exactly the right answer?*

Computation:

1. Execute both queries the same way as for VM-F1 (same executor, same 200-row
   cap, same timeout), so the two metrics are directly comparable.
2. Normalize each cell with the **same** `_norm_value` rules as VM-F1.
3. Turn each row into the tuple of its normalized primitive cells, sorted
   deterministically. Sorting within the row makes the comparison insensitive to
   column aliases and column order while **keeping the cells of one row
   together**.
4. Turn each result set into a `Counter` over those row tuples. Row order is
   therefore ignored and row multiplicity is preserved.
5. `RMEM = 1` if and only if the two Counters are equal, else `0`.

A failed, timed-out or empty generated query scores 0. If the reference query
fails, the record is excluded.

RMEM is strictly stronger than VM-F1 by construction: `RMEM = 1` implies
`VM-F1 = 1`. On AirCypher-150 the two agree exactly on which records are fully
correct — 203 of 3,750 records have `VM-F1 = 1`, the same 203 have `RMEM = 1`,
and no record has `VM-F1 = 1` with `RMEM = 0`. That agreement is an empirical
property of this benchmark, not a general one.

### Documented RMEM limitations

These are stated rather than patched around:

- **Extra or missing harmless columns make RMEM 0**, even when the answer is
  semantically right. No AirCypher-150 reference query echoes a question constant
  back as an extra column (0 of 150), so this case does not arise here; reference
  return arity is 1 (19 queries), 2 (61) or 3 (70).
- **Cells are sorted within a row**, so two rows that are column-permutations of
  each other compare equal. Row grouping is preserved; intra-row cell identity is
  not.
- **Non-primitive cells are dropped.** No reference query returns one; some
  generated queries do, and such a row degenerates to the empty tuple.
- **The 200-row cap applies to both sides.**
- **Duplicate values inside a row are kept** (multiset semantics).

## CV — Cypher Validity

1.0 if and only if the query both (a) parses — `EXPLAIN` succeeds, ignoring
property-key and index notifications — and (b) is schema compliant, referencing
only the four real node labels (`Station`, `Location`, `ObservationTime`,
`ObservedPM25`) and the four real relationship types (`LOCATED_AT`,
`AT_LOCATION`, `OBSERVED_AT`, `RECORDED_BY`).

The schema check is necessary because modern Neo4j downgrades "label does not
exist" from an error to a notification, so `EXPLAIN` alone accepts a fully
hallucinated schema.

## ES — Execution Success

1.0 if the query executes without error within the 30 s server-side transaction
timeout, 0.0 otherwise.

---

## Strict and tolerant evaluation

Both VM-F1 and RMEM are reported in a **strict** and a **tolerant** form.

Tolerant evaluation removes **only** the numerical-validity predicate
`WHERE p.pm25 >= 0 AND p.pm25 <= 500` from the reference query, for the 104 of
150 references that contain it, and scores the generated query against whichever
of the two references it matches better. Nothing else about the reference
semantics changes, and the other 46 references are untouched.

The purpose is to check that the reported improvements are not an artifact of
models forgetting a JPM2KG-specific data-quality convention. They are not: see
`../05_results/camera_ready/robustness/`.

---

## Legacy field names in the raw results

`05_results/raw/results_full.jsonl` is preserved byte-for-byte as generated and
therefore keeps the submitted field names:

| Raw JSONL field | Camera-ready name | Note |
|---|---|---|
| `metrics.SE` | **VM-F1** | Same values; renamed for accuracy. |
| `metrics.CV` | CV | Unchanged. |
| `metrics.ES` | ES | Unchanged. |
| `metrics.EM` | EM (Exact Match) | Cypher-string exact match. It is 0.000 everywhere and is not reported in the camera-ready paper. |
| `metrics.RQ` | — | A heuristic "Result Quality" score from the submission. It is **not** a camera-ready metric and is not reported in the paper. |

RMEM is not present in the raw JSONL: it is computed by re-executing the stored
queries with `camera_ready_evaluator.py`. The result of doing so is shipped in
`../05_results/camera_ready/`.

Anything that reads the raw JSONL must use `metrics.SE` and interpret it as
VM-F1. Do not rewrite the raw file.
