# JPM2KG Knowledge Graph Construction Notes

## Data Source and Provenance

JPM2KG is built from Japan's national atmospheric monitoring network. The PM2.5
observations were collected following the procedure described in:

> Rage, Uday Kiran; Kattumuri, Vanitha; Pogaku, Arjun Chakravarthi.
> *Patterns Discovery Dataset for Particulate Matter (PM2.5) Pollution Trends in Japan.*
> Scientific Data **12**, 1009 (2025). <https://doi.org/10.1038/s41597-025-05195-2>

The JPM2KG collection extends that procedure through 2025, and covers hourly
measurements from 1,116 fixed monitoring stations across 46 prefectures and 619
cities.

JPM2KG is **not** a graph conversion of the Scientific Data release. The two
differ in purpose and in representation:

| | Earlier work (Scientific Data 2025) | This work (JPM2KG) |
|---|---|---|
| Goal | data collection and representation for pattern-mining analysis | observation-level querying in natural language |
| Representation | transactional/temporal files prepared for pattern mining | Neo4j property graph |
| Content | measurements prepared for the mining task | individual observations plus derived categorical attributes (season, day type, time category, PM2.5 category) |
| Coverage | as published | extended through 2025 |

## Graph Construction Pipeline

1. **Station and location extraction** — Station metadata (name, type, coordinates)
   and location metadata (prefecture, city, address) were extracted from the
   monitoring network registry and loaded as `Station` and `Location` nodes. Each
   station has a corresponding location node connected via `LOCATED_AT`.

2. **Temporal feature enrichment** — Each raw timestamp was enriched with derived
   attributes before creating `ObservationTime` nodes:
   - `year`, `month` — calendar year and month
   - `season` — Spring (Mar–May), Summer (Jun–Aug), Autumn (Sep–Nov), Winter (Dec–Feb)
   - `dayType` — Weekday, Weekend
   - `timeCategory` — Morning (6–10), Afternoon (11–17), Evening (18–22), Night (23–5)

3. **PM2.5 category assignment** — Each `ObservedPM25` node stores the raw `pm25`
   value and a derived `pm25_level` attribute. See the next section.

## PM2.5 Category Convention (`pm25_level`)

`ObservedPM25.pm25_level` is a **system-defined category convention of JPM2KG**.
It is the mapping actually implemented in the graph, verified against the live
database:

| `pm25_level` | Stored `pm25` range (µg/m³) |
|---|---|
| `Safe` | 0–15 |
| `Moderate` | 16–35 |
| `Slightly Unhealthy` | 36–50 |
| `Unhealthy` | 51–70 |
| `Very Unhealthy` | ≥ 71 |

These five bands are the JPM2KG convention. **They are not an official WHO
classification and are not an official Japanese regulatory classification**, and
they should not be described as either. Regulatory thresholds that do apply
independently — Japan's 35 µg/m³ daily and 15 µg/m³ annual environmental quality
standards, and the WHO 2021 guidelines of 15 µg/m³ (24-hour mean) and 5 µg/m³
(annual mean) — are documented separately in
`../03_domain_knowledge_base/dkb_japan.json` under `pm25_health_rules` and are
kept distinct from `pm25_level`.

## Critical Design Decision: Prefecture on Location Nodes

Prefecture and city attributes are stored on `Location` nodes, **not** on
`Station` nodes. This reflects the semantic separation between a physical
measuring device (Station) and the administrative place where it is installed
(Location). Queries filtering by prefecture must traverse:
`Location {prefecture_en: '...'} ← LOCATED_AT ← Station`.

Placing the filter on `Station` will produce empty results, which is a common
failure mode for schema-only grounded models.

## Numerical Validity Convention

Raw readings include sensor errors and calibration artifacts: stored `pm25`
values span −10,000 to 65,535, and some are NULL. The **data-quality convention
used for numerical aggregation** in JPM2KG and in AirCypher-150's reference
queries is:

```cypher
WHERE p.pm25 >= 0 AND p.pm25 <= 500
```

This is a convention adopted for this graph so that averages, maxima and
percentiles are computed over plausible readings. It is not an external or
universal standard.

The four groups below partition the `ObservedPM25` records:

| Group | Count |
|---|---|
| NULL `pm25` | 3,087,056 |
| `pm25` < 0 | 1,974,663 |
| `pm25` > 500 | 846 |
| valid, 0 ≤ `pm25` ≤ 500 | 66,086,807 |
| **Total `ObservedPM25` records** | **71,149,372** |

Minimum stored `pm25`: −10,000. Maximum stored `pm25`: 65,535.
The valid group is 92.9 % of all records.

The derived `pm25_level` attribute is assigned from cleaned values, so
categorical queries on `pm25_level` do not additionally need the numerical
validity predicate.

`05_results/camera_ready/robustness/` reports how much the reported scores move
if this predicate is removed from the applicable reference queries.

## Neo4j Version and Docker Image

- Neo4j version: 2026.02.2 (Community Edition)
- Docker image: `neo4j:2026.02.2`
- Bolt endpoint: `bolt://localhost:37689` (host port 37689 maps to container port 7687)
- HTTP browser: `http://localhost:7474`

Credentials are supplied through environment variables; see
`../04_pipeline/.env.example` and `../06_environment/docker_setup.md`.

## Connection Details

```bash
# Start the container (example)
docker run -d \
  --name jpm2kg-neo4j \
  -p 7474:7474 -p 37689:7687 \
  -v $(pwd)/neo4j_data:/data \
  -e NEO4J_AUTH=neo4j/"$NEO4J_PASSWORD" \
  neo4j:2026.02.2

# Verify connection
cypher-shell -a bolt://localhost:37689 -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n:Station) RETURN count(n)"
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
