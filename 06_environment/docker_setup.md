# Neo4j Docker Configuration

## Container Details

| Parameter | Value |
|---|---|
| Docker image | neo4j:2026.02.2 |
| Container name | jp-pm25-neo4j (or jpm2kg-neo4j for restored) |
| HTTP port | 7474 (Neo4j Browser) |
| Bolt port | 37689 → 7687 |
| Authentication | neo4j / \<password\> |
| JVM heap | 8 GB recommended |

## Run Command

```bash
docker run -d \
  --name jpm2kg-neo4j \
  -p 7474:7474 -p 37689:7687 \
  -v $(pwd)/neo4j_data:/data \
  -e NEO4J_AUTH=neo4j/StrongPasswordHere \
  -e NEO4J_dbms_memory_heap_max__size=8G \
  -e NEO4J_dbms_memory_pagecache_size=4G \
  neo4j:2026.02.2
```

## Verify Connection

```bash
# Via cypher-shell
cypher-shell -a bolt://localhost:37689 -u neo4j -p StrongPasswordHere \
  "MATCH (n:Station) RETURN count(n) AS stations"

# Via Python neo4j driver
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:37689', auth=('neo4j','StrongPasswordHere'))
with driver.session() as s:
    result = s.run('MATCH (n:Station) RETURN count(n) AS n')
    print('Stations:', result.single()['n'])
driver.close()
"
```

## Important Query Notes

- **Prefecture on Location, not Station**: Filter `WHERE l.prefecture_en = '...'` not `WHERE s.prefecture_en = '...'`
- **Always start from Station/Location**: Traversals starting from ObservedPM25 or ObservationTime will time out on this 142M-node graph
- **Always apply validity filter**: `WHERE p.pm25 >= 0 AND p.pm25 <= 500` on every PM2.5 query
- **Canonical prefecture names include "Prefecture"**: `'Tokyo Prefecture'`, `'Osaka Prefecture'`, etc.

## Troubleshooting

**OOM errors during queries:** Increase heap: `-e NEO4J_dbms_memory_heap_max__size=16G`

**Slow startup:** Neo4j needs ~60 seconds after `docker start` before accepting connections.

**Connection refused:** Check the bolt port mapping matches your `config.yaml` (`bolt://localhost:37689`).
