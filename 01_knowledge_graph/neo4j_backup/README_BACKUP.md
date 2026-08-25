# JPM2KG Neo4j Backup

## The dump is not in this repository

The JPM2KG database dump (`jpm2kg.dump`, ~6.1 GB, `neo4j-admin` format) is far
too large for GitHub and is **not stored here**. This directory contains only
these restore instructions.

Download instructions are maintained in `../../DATASET_ACCESS.md`, which is kept
current independently of the paper.

Everything needed to reproduce the paper's **tables** ships in this repository
and does not require the graph — see the root `README.md`. The dump is needed
only to re-execute queries against JPM2KG or to regenerate the LLM outputs.

## Restoring, once you have the dump

The dump was produced from Neo4j **2026.02.2 Community Edition**. Restore into
the same major version.

### 1. Start a container

```bash
export NEO4J_PASSWORD='choose-a-password'

docker run -d \
  --name jpm2kg-neo4j \
  -p 7474:7474 -p 37689:7687 \
  -v $(pwd)/jpm2kg_data:/data \
  -e NEO4J_AUTH=neo4j/"$NEO4J_PASSWORD" \
  -e NEO4J_dbms_memory_heap_max__size=8G \
  -e NEO4J_dbms_memory_pagecache_size=4G \
  neo4j:2026.02.2
```

### 2. Load the dump

```bash
docker cp jpm2kg.dump jpm2kg-neo4j:/tmp/jpm2kg.dump
docker stop jpm2kg-neo4j
docker exec jpm2kg-neo4j neo4j-admin database load \
  --from-path=/tmp/ \
  --database=neo4j \
  --overwrite-destination=true
docker start jpm2kg-neo4j
```

### 3. Verify

Wait about 60 seconds for startup, then:

```bash
cypher-shell -a bolt://localhost:37689 -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n:Station) RETURN count(n)"
```

```cypher
MATCH (n:Station)          RETURN count(n)   -- expected: 1,116
MATCH (n:ObservationTime)  RETURN count(n)   -- expected: 71,149,372
MATCH (n:ObservedPM25)     RETURN count(n)   -- expected: 71,149,372
MATCH (n)                  RETURN count(n)   -- expected: 142,300,976
MATCH ()-[r]->()           RETURN count(r)   -- expected: 213,449,232
```

These are the counts recorded in `../kg_statistics.json`. If they differ, the
restore is incomplete.

## Requirements

- ~100–200 GB free disk for a full restore
- 8 GB JVM heap recommended; 16 GB makes the load noticeably faster
- Initial load takes 60+ minutes depending on hardware
- Tested on Ubuntu 22.04, 64 GB RAM, NVMe SSD

## Bolt port

The pipeline defaults to `bolt://localhost:37689` (host port 37689 → container
port 7687). Override with `NEO4J_URI` if you map a different port.
