# AirCypher-150 Benchmark

## What is AirCypher-150?

AirCypher-150 is a manually authored, execution-validated NL-to-Cypher benchmark of 150 natural-language questions over JPM2KG. It covers five environmental monitoring query categories and three complexity levels.

**Important:** AirCypher-150 was constructed independently from the DKB exemplars. No benchmark query was used as a DKB exemplar, ensuring clean train/test separation.

## Construction Methodology

1. **Manual authoring** — All 150 questions and corresponding gold Cypher queries were written by domain experts familiar with both the JPM2KG schema and Japanese air quality data.

2. **Execution validation** — Every gold Cypher query was executed against the live JPM2KG and verified to:
   - Execute without error within 10 seconds
   - Return at least one result row
   - Return results consistent with known ground truth for selected queries

3. **Coverage design** — Categories and prefectures were chosen to cover diverse query patterns and geographic diversity across Japan's 46 prefectures.

## Category Descriptions

| Category | N | Description |
|---|---|---|
| Aggregate | 38 | Avg/max/count aggregations over PM2.5 readings, optionally grouped by temporal or spatial dimensions |
| Station Filtering | 30 | Filter stations by type, prefecture, city, or other attributes |
| Temporal | 30 | Season/year/month/time-of-day comparisons and trends |
| Health Risk | 30 | Queries using the `pm25_level` attribute and WHO health thresholds |
| Comparative | 22 | Cross-group comparisons (station types, prefectures, time periods) |

## Complexity Levels

- **Simple** (8): Single-hop pattern, one filter, one aggregation
- **Medium** (69): Multi-hop traversal, 2–3 filters, grouping
- **Complex** (73): Compound filters, multi-group comparisons, nested or multi-step logic

## File Format

`aircypher150_benchmark.json` is a JSON array. Each entry contains:

```json
{
  "query_id": "q001",
  "nl_query": "Which general stations are in Yamaguchi Prefecture?",
  "gold_cypher": "MATCH (l:Location {prefecture_en:'Yamaguchi Prefecture'})<-[:LOCATED_AT]-(s:Station) ...",
  "type": "station_filtering",
  "complexity": "simple",
  "prefectures_used": ["Yamaguchi Prefecture"],
  "seasons_used": [],
  "years_used": [],
  "validated": true
}
```

## How to Use the Benchmark

### Loading

```python
import json
benchmark = json.load(open("aircypher150_benchmark.json"))
print(f"Loaded {len(benchmark)} queries")
```

### Running evaluation

```bash
cd 04_pipeline/
python experiment_runner.py \
  --benchmark ../02_benchmark/aircypher150_benchmark.json \
  --systems baseline schema_baseline schema_values dkb_noexamples dkb dkb_hybrid \
  --llms llama3.2:3b gemma2:9b qwen2.5-coder:32b qwen2.5:72b \
  --results-file ../05_results/raw/results_reproduced.jsonl
```

### Generating tables

```bash
python aggregate_full.py \
  ../05_results/raw/results_reproduced.jsonl \
  ../02_benchmark/aircypher150_benchmark.json \
  --output-dir ../05_results/reproduced/
```
