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
WHO/Japanese regulatory PM2.5 thresholds and the corresponding `pm25_level` strings used in the graph. Enables health-risk queries that reference level names rather than raw numeric thresholds.

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
2. **Always apply the validity filter** `WHERE p.pm25 >= 0 AND p.pm25 <= 500`
3. **Prefecture is on Location, not Station** — must join via `LOCATED_AT`
4. Standard traversal path: `Location ← LOCATED_AT ← Station ← RECORDED_BY ← ObservedPM25 → OBSERVED_AT → ObservationTime`

### `query_patterns`
28 exemplar NL–Cypher pairs covering the five benchmark categories at varying complexity levels. In the `DKB` system, all 28 are included in the prompt as fixed few-shot examples. In `DKB+Hybrid`, a subset of the most relevant examples is selected dynamically per query using BM25+embedding hybrid retrieval.

### `data_quality_notes`
Notes on data anomalies, known sensor issues, and recommended filters for robust analysis.

## How the DKB is Used

Each prompting system uses a different subset of DKB components:

| System | Schema | Values | Rules | Examples |
|---|---|---|---|---|
| Baseline | — | — | — | — |
| Schema Baseline | ✓ (schema only) | — | — | — |
| Schema+Values | ✓ | ✓ | — | — |
| DKB-NoExamples | ✓ | ✓ | ✓ | — |
| DKB | ✓ | ✓ | ✓ | Fixed (28) |
| DKB+Hybrid | ✓ | ✓ | ✓ | Dynamic (top-k) |

The ablation study (Table 4) isolates the contribution of each component by measuring the SE improvement when each is added incrementally.
