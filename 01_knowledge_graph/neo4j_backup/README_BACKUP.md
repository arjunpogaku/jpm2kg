# JPM2KG Neo4j Backup

## File

- `jpm2kg.dump` — Neo4j database dump (neo4j-admin format)
- Size: 6.1 GB (compressed)

## Neo4j Version

- Version: 2026.02.2
- Edition: Community

## How to Restore

### Step 1: Start a fresh Neo4j container

```bash
docker run -d \
  --name jpm2kg-restored \
  -p 7474:7474 -p 37689:7687 \
  -v $(pwd)/jpm2kg_data:/data \
  -e NEO4J_AUTH=neo4j/StrongPasswordHere \
  -e NEO4J_dbms_memory_heap_max__size=8G \
  -e NEO4J_dbms_memory_pagecache_size=4G \
  neo4j:2026.02.2
```

### Step 2: Restore the dump

```bash
docker cp jpm2kg.dump jpm2kg-restored:/tmp/jpm2kg.dump
docker stop jpm2kg-restored
docker exec jpm2kg-restored neo4j-admin database load \
  --from-path=/tmp/ \
  --database=neo4j \
  --overwrite-destination=true
docker start jpm2kg-restored
```

### Step 3: Wait for startup and verify

```bash
# Wait approximately 60 seconds for Neo4j to initialize, then:
cypher-shell -a bolt://localhost:37689 -u neo4j -p StrongPasswordHere \
  "MATCH (n:Station) RETURN count(n)"
```

### Step 4: Verify restoration

```cypher
MATCH (n:Station) RETURN count(n)          -- Expected: 1,116
MATCH (n:ObservationTime) RETURN count(n)  -- Expected: 71,149,372
MATCH ()-[r]->() RETURN count(r)           -- Expected: 213,449,232
```

## Notes

- Full restoration requires approximately 100–200 GB disk space
- Initial load takes 60+ minutes depending on hardware
- 8 GB JVM heap is recommended; increase to 16 GB for faster imports
- Tested on Ubuntu 22.04 with 64 GB RAM and NVMe SSD
