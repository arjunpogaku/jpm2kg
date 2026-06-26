# Domain Knowledge Base (DKB)

## Overview

The DKB is a structured JSON document that encodes all domain-specific knowledge needed to generate semantically correct Cypher queries over JPM2KG. It is the key component distinguishing the proposed systems from schema-only baselines.

## Files

| File | Description |
|---|---|
| `dkb_japan.json` | The complete DKB (all 10 components) |
| `dkb_structure_explained.md` | Detailed explanation of each DKB component |

## Quick Reference

The DKB has 10 top-level components:

| Component | Purpose |
|---|---|
| `metadata` | Version and provenance |
| `kg_actual_schema` | Canonical property names and labels |
| `schema_bridge` | NL phrase → graph term mappings |
| `schema_specification` | All valid categorical values |
| `pm25_health_rules` | WHO threshold → `pm25_level` mappings |
| `temporal_rules` | Temporal expression → graph attribute rules |
| `japan_geographic_context` | Prefecture coverage and geographic notes |
| `traversal_policies` | Query construction rules and performance guidance |
| `query_patterns` | 28 exemplar NL–Cypher pairs (few-shot examples) |
| `data_quality_notes` | Sensor anomaly warnings and recommended filters |

## Why the DKB is Necessary

Schema-only grounded models (CypherBench-style) know the graph structure but not the domain semantics. Common failures include:

1. **Wrong canonical values**: Using `"Yamaguchi"` instead of `"Yamaguchi Prefecture"` → empty results
2. **Wrong traversal start**: Filtering on `Station.prefecture` (property doesn't exist) instead of `Location.prefecture_en`
3. **Missing validity filter**: Omitting `WHERE p.pm25 >= 0 AND p.pm25 <= 500` → inflated statistics from sensor errors
4. **Unknown level names**: Using `WHERE p.pm25 > 35` instead of `WHERE p.pm25_level IN ['Slightly Unhealthy', ...]`

The DKB provides explicit corrections for all of these failure modes.

## Loading the DKB in Code

```python
import json
dkb = json.load(open("dkb_japan.json"))

# Access schema specification
valid_prefectures = dkb["schema_specification"]["prefecture_values"]

# Access traversal policies
policies = dkb["traversal_policies"]

# Access exemplar query patterns
examples = dkb["query_patterns"]
print(f"DKB contains {len(examples)} exemplar queries")
```
