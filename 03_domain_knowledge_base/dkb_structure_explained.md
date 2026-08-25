# DKB Structure Explained

The Domain Knowledge Base (DKB) is a structured JSON document that encodes domain-specific knowledge required to generate semantically correct Cypher queries over JPM2KG. It is the core contribution of the DKB prompting systems.

## Top-Level Components

### `metadata`
Administrative metadata: version, creation date, graph name, description, and provenance notes.

### `kg_actual_schema`
The true graph schema as observed in the live database — node labels, relationship types, and property names with their canonical casing. This differs from what an LLM might infer from the database name alone (e.g., the property is `stationtype_en`, not `stationType` or `type`).

### `schema_bridge`
Mappings from common natural-language phrasings to the canonical graph terms. For example:
- "Tokyo" → `"Tokyo"` (not a valid prefecture name; must be `"Tokyo Prefecture"`)
- "unhealthy" → `pm25_level IN ['Slightly Unhealthy', 'Unhealthy', 'Very Unhealthy']`
- "roadside station" → `stationtype_en = 'Roadside Station'`

This component prevents the most common failure mode: using plausible but incorrect canonical values.

### `schema_specification`
Exhaustive enumeration of all valid values for categorical properties:
- All 46 prefecture names (exact strings as stored in Neo4j)
- All `pm25_level` values
- All `season` values: `'Spring'`, `'Summer'`, `'Autumn'`, `'Winter'`
- All `stationtype_en` values: `'General Station'`, `'Roadside Station'`
- All `dayType` values: `'Weekday'`, `'Weekend'`
- All `timeCategory` values: `'Morning'`, `'Afternoon'`, `'Evening'`, `'Night'`

### `pm25_health_rules`
Two distinct kinds of rule, kept separate on purpose:

1. **The JPM2KG category convention** — the five `pm25_level` bands actually stored in
   the graph. This is a system-defined convention of JPM2KG. It is **not** an official
   WHO classification and **not** an official Japanese regulatory classification:

   | `pm25_level` | Stored `pm25` range (µg/m³) |
   |---|---|
   | `Safe` | 0–15 |
   | `Moderate` | 16–35 |
   | `Slightly Unhealthy` | 36–50 |
   | `Unhealthy` | 51–70 |
   | `Very Unhealthy` | ≥ 71 |

2. **Genuine regulatory thresholds**, cited as such: Japan's environmental quality
   standard (35 µg/m³ daily, 15 µg/m³ annual) and the WHO 2021 guidelines
   (15 µg/m³ 24-hour mean, 5 µg/m³ annual mean). These are numeric thresholds on
   `pm25`; they are not the same thing as `pm25_level` and are not conflated with it.

Together these let health-risk questions be answered by level name where the band
convention applies, and by numeric threshold where a regulatory limit is meant.

### `temporal_rules`
Rules for mapping natural-language temporal expressions to graph attributes:
- Season definitions (months per season)
- Year/month integer encodings
- How to handle multi-season or multi-year queries

### `japan_geographic_context`
Coverage information: prefecture list, station count per prefecture, and notes on geographic encoding (e.g., Tokyo Prefecture vs. Tokyo Metropolis spelling).

### `traversal_policies`
Graph traversal rules that enforce correctness and performance:
1. **Always start from Station or Location** (1,116 nodes), never from ObservedPM25 or ObservationTime (71M nodes)
2. **Always apply the numerical-validity convention** `WHERE p.pm25 >= 0 AND p.pm25 <= 500`
   for numeric aggregation (this is a JPM2KG data-quality convention, not an external standard)
3. **Prefecture is on Location, not Station** — must join via `LOCATED_AT`
4. Standard traversal path: `Location ← LOCATED_AT ← Station ← RECORDED_BY ← ObservedPM25 → OBSERVED_AT → ObservationTime`

### `query_patterns`
An exemplar pool of 28 NL–Cypher pairs covering the five benchmark categories at
varying complexity levels.

The prompt shows **8 exemplars** in both exemplar-using configurations
(`_build_dkb_prompt_core` in `04_pipeline/systems.py` truncates the exemplar list to 8):

- **`DKB`** — the first 8 pool entries, fixed for every question.
- **`DKB+Hybrid`** — the top-k (k=3) pool entries most similar to the question, prepended
  to the same fixed list and truncated to 8, so 3 retrieved + 5 fixed. Retrieval is dense
  embedding cosine similarity only (sentence-transformers `all-MiniLM-L6-v2`); there is no
  BM25 or other sparse term and no weighting coefficient (see `04_pipeline/systems.py`,
  `_retrieve_top_k`).

The pool is disjoint from AirCypher-150: no benchmark item shares an identical
natural-language question, an identical Cypher query, or an identical normalized query
structure with any exemplar.

### `data_quality_notes`
Notes on data anomalies, known sensor issues, and the numerical-validity convention
`p.pm25 >= 0 AND p.pm25 <= 500` used for aggregation. That predicate is a data-quality
convention adopted for this graph, not an external or universal standard.

## How the DKB is Used

Each prompting system uses a different subset of DKB components:

| System | Schema | Values | Rules | Examples |
|---|---|---|---|---|
| Baseline | — | — | — | — |
| Schema Baseline | ✓ (schema only) | — | — | — |
| Schema+Values | ✓ | ✓ | — | — |
| DKB-NoExamples | ✓ | ✓ | ✓ | — |
| DKB | ✓ | ✓ | ✓ | Fixed (8 of the 28-pair pool) |
| DKB+Hybrid | ✓ | ✓ | ✓ | Top-3 retrieved + 5 fixed (8 total) |

The ablation isolates the contribution of each component by measuring the improvement in
Value-Multiset F1 (VM-F1) and Row-Multiset Exact Match (RMEM) as each is added incrementally.
See `../04_pipeline/METRICS.md` for the metric definitions and
`../05_results/camera_ready/` for the camera-ready results.
