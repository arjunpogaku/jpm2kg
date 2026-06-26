# JPM2KG — Japan PM2.5 Knowledge Graph

## Overview

JPM2KG is a large-scale environmental knowledge graph encoding PM2.5 (fine particulate matter) air quality observations from Japan's national monitoring network.

| Property | Value |
|---|---|
| Total nodes | 142,300,976 |
| Total relationships | 213,449,232 |
| Monitoring stations | 1,116 |
| Prefectures covered | 46 of 47 |
| Date range | 2018-01-01 to 2026-01-01 |
| Valid PM2.5 readings | 66,086,807 |

## Node Types

- **Station** (1,116): Physical monitoring stations — name, type (General/Roadside), GPS coordinates
- **Location** (1,116): Administrative place for each station — prefecture, city, address
- **ObservationTime** (71.1M): Timestamped measurement contexts with enriched temporal attributes
- **ObservedPM25** (71.1M): PM2.5 values with derived health-level classification

## Files in This Directory

| File | Description |
|---|---|
| `kg_schema.json` | Complete node/relationship schema with property lists and counts |
| `kg_statistics.json` | Node/relationship count statistics |
| `kg_construction_notes.md` | How the KG was built, design decisions, connection info |
| `neo4j_backup/` | Neo4j database backup for restoration |

## Quick Start Query

After restoring the KG (see `neo4j_backup/README_BACKUP.md`):

```cypher
// Count stations per prefecture
MATCH (l:Location)<-[:LOCATED_AT]-(s:Station)
RETURN l.prefecture_en AS prefecture, count(s) AS stations
ORDER BY stations DESC
LIMIT 10
```

## Important: Traversal Pattern

Always start queries from `Station` or `Location` nodes (1,116 each). **Never** start from `ObservedPM25` or `ObservationTime` (71M nodes each) — this will time out.

Standard traversal:
```cypher
MATCH (l:Location {prefecture_en:'Tokyo'})<-[:LOCATED_AT]-(s:Station)
      <-[:RECORDED_BY]-(p:ObservedPM25)-[:OBSERVED_AT]->(t:ObservationTime {year:2023})
WHERE p.pm25 >= 0 AND p.pm25 <= 500
RETURN avg(p.pm25)
```
