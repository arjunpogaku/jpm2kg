# AirCypher-150: Representative Sample Queries

One query from each of the five benchmark categories.

---

### Category: Aggregate

**Question:** What was the average PM2.5 in Akita Prefecture during Winter 2024?

**Cypher:**
```cypher
MATCH (l:Location {prefecture_en:'Akita Prefecture'})<-[:LOCATED_AT]-(s:Station)
      <-[:RECORDED_BY]-(p:ObservedPM25)-[:OBSERVED_AT]->(t:ObservationTime {season:'Winter',year:2024})
WHERE p.pm25 >= 0 AND p.pm25 <= 500
RETURN round(avg(p.pm25),2) AS avg_pm25,
       max(p.pm25)          AS max_pm25,
       count(p)             AS n
```

**Notes:** Tests aggregation with compound temporal filter (season + year). Requires knowledge of the canonical value `'Winter'` (not `'winter'` or `'WINTER'`) and the traversal pattern starting from Location.

---

### Category: Station Filtering

**Question:** Which general stations are in Yamaguchi Prefecture?

**Cypher:**
```cypher
MATCH (l:Location {prefecture_en:'Yamaguchi Prefecture'})<-[:LOCATED_AT]-(s:Station)
WHERE s.stationtype_en = 'General Station'
RETURN s.stationname_en AS station
ORDER BY station
LIMIT 50
```

**Notes:** Tests knowledge that prefecture is stored on `Location` nodes (not `Station`), and that station type uses the canonical value `'General Station'` (not `'general'`).

---

### Category: Temporal

**Question:** Compare the average PM2.5 across seasons in Aomori Prefecture in 2020.

**Cypher:**
```cypher
MATCH (l:Location {prefecture_en:'Aomori Prefecture'})<-[:LOCATED_AT]-(s:Station)
      <-[:RECORDED_BY]-(p:ObservedPM25)-[:OBSERVED_AT]->(t:ObservationTime {year:2020})
WHERE p.pm25 >= 0 AND p.pm25 <= 500
RETURN t.season AS season, round(avg(p.pm25),2) AS avg_pm25
ORDER BY avg_pm25 DESC
```

**Notes:** Tests temporal grouping by season and the requirement to always apply the PM2.5 validity filter `[0, 500]`.

---

### Category: Health Risk

**Question:** How many unhealthy PM2.5 readings occurred in Fukuoka Prefecture during Winter?

**Cypher:**
```cypher
MATCH (l:Location {prefecture_en:'Fukuoka Prefecture'})<-[:LOCATED_AT]-(s:Station)
      <-[:RECORDED_BY]-(p:ObservedPM25)-[:OBSERVED_AT]->(t:ObservationTime {season:'Winter'})
WHERE p.pm25_level IN ['Slightly Unhealthy', 'Unhealthy', 'Very Unhealthy']
RETURN count(p) AS unhealthy_count
```

**Notes:** Tests knowledge of the WHO-derived PM2.5 health level taxonomy encoded in `pm25_level`. A model without domain grounding typically does not know these level names.

---

### Category: Comparative

**Question:** In Niigata Prefecture (2018), did roadside stations record higher PM2.5 than general stations?

**Cypher:**
```cypher
MATCH (l:Location {prefecture_en:'Niigata Prefecture'})<-[:LOCATED_AT]-(s:Station)
      <-[:RECORDED_BY]-(p:ObservedPM25)-[:OBSERVED_AT]->(t:ObservationTime {year:2018})
WHERE p.pm25 >= 0 AND p.pm25 <= 500
RETURN s.stationtype_en AS station_type,
       round(avg(p.pm25),2) AS avg_pm25,
       count(p) AS n
ORDER BY avg_pm25 DESC
```

**Notes:** Tests cross-group comparison by station type. Requires knowing both canonical type names (`'General Station'`, `'Roadside Station'`) and correct traversal to compare groups in a single query.
