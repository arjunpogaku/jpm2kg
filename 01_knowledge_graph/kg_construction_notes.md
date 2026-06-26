# JPM2KG Knowledge Graph Construction Notes

## Data Source

JPM2KG is built from Japan's national atmospheric monitoring network operated under the Air Pollution Monitoring Act. Hourly PM2.5 measurements were obtained from 1,116 fixed monitoring stations covering 46 prefectures and 619 cities, spanning January 2018 to January 2026.

## Graph Construction Pipeline

1. **Station and location extraction** — Station metadata (name, type, coordinates) and location metadata (prefecture, city, address) were extracted from the monitoring network registry and loaded as `Station` and `Location` nodes. Each station has a corresponding location node connected via `LOCATED_AT`.

2. **Temporal feature enrichment** — Each raw timestamp was enriched with derived attributes before creating `ObservationTime` nodes:
   - `year`, `month` — calendar year and month
   - `season` — Spring (Mar–May), Summer (Jun–Aug), Autumn (Sep–Nov), Winter (Dec–Feb)
   - `dayType` — Weekday, Weekend
   - `timeCategory` — Morning (6–10), Afternoon (11–17), Evening (18–22), Night (23–5)

3. **PM2.5 level mapping** — Each `ObservedPM25` node stores the raw `pm25` value and a derived `pm25_level` attribute based on WHO/Japanese standards:
   - Good: 0–12 μg/m³
   - Moderate: 12.1–35.4 μg/m³
   - Slightly Unhealthy: 35.5–55.4 μg/m³
   - Unhealthy: 55.5–150.4 μg/m³
   - Very Unhealthy: 150.5–250.4 μg/m³
   - Hazardous: ≥250.5 μg/m³

## Critical Design Decision: Prefecture on Location Nodes

Prefecture and city attributes are stored on `Location` nodes, **not** on `Station` nodes. This reflects the semantic separation between a physical measuring device (Station) and the administrative place where it is installed (Location). Queries filtering by prefecture must traverse: `Location {prefecture_en: '...'} ← LOCATED_AT ← Station`.

Placing the filter on `Station` will produce empty results, which is a common failure mode for schema-only grounded models.

## Validity Filtering

Raw readings include sensor errors and calibration artifacts. All analytical queries should apply:
```
WHERE p.pm25 >= 0 AND p.pm25 <= 500
```
This retains 66,086,807 of 71,149,372 total observations (92.9% validity rate).

## Neo4j Version and Docker Image

- Neo4j version: 2026.02.2 (Community Edition)
- Docker image: `neo4j:2026.02.2`
- Bolt endpoint: `bolt://localhost:37689` (host port 37689 maps to container port 7687)
- HTTP browser: `http://localhost:57476`

## Connection Details

```bash
# Start the container (example)
docker run -d \
  --name jp-pm25-neo4j \
  -p 7474:7474 -p 37689:7687 \
  -v $(pwd)/neo4j_data:/data \
  -e NEO4J_AUTH=neo4j/<password> \
  neo4j:2026.02.2

# Verify connection
cypher-shell -a bolt://localhost:37689 -u neo4j -p <password> "MATCH (n:Station) RETURN count(n)"
```

## Scale

| Entity | Count |
|---|---|
| Station nodes | 1,116 |
| Location nodes | 1,116 |
| ObservationTime nodes | 71,149,372 |
| ObservedPM25 nodes | 71,149,372 |
| Total nodes | 142,300,976 |
| Total relationships | 213,449,232 |
