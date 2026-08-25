# AirCypher-150

AirCypher-150 is a **graph-grounded, execution-validated NL-to-Cypher benchmark**
over JPM2KG. It contains 150 natural-language questions, each paired with a
reference ("gold") Cypher query.

## Files

| File | Contents |
|---|---|
| `aircypher150_benchmark.json` | The 150 benchmark items. |
| `benchmark_statistics.json` | Category, intent and complexity counts, and validation metadata. |

## How it was built

```
human-designed query forms
  → instantiated with values extracted from JPM2KG
  → reference Cypher executed against the live graph
  → only successful, non-empty candidates retained
```

The query forms cover the five categories below and were designed by hand; each
form was then instantiated with prefectures, seasons, years, station types and
PM2.5 categories read out of JPM2KG, so every literal in a reference query is a
value that actually exists in the graph. Every reference query was executed
against the live database, and a candidate was kept only if it executed
successfully and returned at least one row.

Validation is therefore **execution-based and value-grounded**. The benchmark
does not claim a second-annotator human validation pass, and the 150 released
items are instantiations of hand-designed forms rather than 150 individually
hand-written queries.

## Categories

| Category | Count |
|---|---|
| Aggregate | 38 |
| Temporal | 30 |
| Health Risk | 30 |
| Station Filtering | 30 |
| Comparative | 22 |
| **Total** | **150** |

## Item fields

Each item carries `query_id`, `category` / `type`, `complexity`, `intent`,
`nl` (duplicated as `nl_query`), `cypher` (duplicated as `gold_cypher`), `meta`,
`prefectures_used`, `seasons_used`, `years_used`, and the recorded
`execution_time_ms` / `result_row_count` from validation.

**Query IDs are not contiguous.** They run `q001 … q198` with gaps, because they
were assigned over a larger validated candidate pool before the 150 released
items were selected. Join on `query_id`, never on position or on an assumed
`q001..q150` range.

## Relationship to the DKB exemplars

The DKB exemplar pool (`../03_domain_knowledge_base/dkb_japan.json`,
`query_patterns`) contains 28 NL–Cypher pairs used as few-shot examples. It is
disjoint from AirCypher-150 on all three of the following, verified over the
shipped files:

| Check | Overlap |
|---|---|
| Identical natural-language question | 0 |
| Identical Cypher query | 0 |
| Identical normalized query structure | 0 |

Normalized structure masks string literals and numeric constants and collapses
whitespace, so it catches an exemplar and a benchmark item that differ only in
the prefecture, year or season they mention.

## Reference-query conventions

Reference queries that aggregate numerically apply the JPM2KG numerical-validity
convention `p.pm25 >= 0 AND p.pm25 <= 500` (104 of the 150 do). See
`../01_knowledge_graph/kg_construction_notes.md`, and
`../05_results/camera_ready/robustness/` for how much the reported scores move if
that predicate is removed.
