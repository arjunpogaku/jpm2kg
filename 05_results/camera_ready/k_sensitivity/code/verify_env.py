#!/usr/bin/env python3
"""PHASE 1 — environment + live-retrieval verification. Aborts on any failure."""
import json, subprocess, sys, platform
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import requests
from k_systems import retrieve, build_prompt

ROOT = Path(os.environ.get("PM25_ROOT", Path(__file__).resolve().parents[5]))
BENCH = ROOT/"02_benchmark/aircypher150_benchmark.json"
AUDITED = {"nodes": 142300976, "rels": 213449232, "obs": 71149372}
checks, info = [], {}
def chk(name, ok, detail=""): checks.append((name, bool(ok), detail)); return ok

# 1-2 Neo4j
from neo4j import GraphDatabase
d = GraphDatabase.driver("bolt://localhost:37689", auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]))
with d.session() as s:
    n = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    r = s.run("MATCH ()-[x]->() RETURN count(x) AS c").single()["c"]
    o = s.run("MATCH (p:ObservedPM25) RETURN count(p) AS c").single()["c"]
    rec = list(s.run("CALL dbms.components() YIELD name,versions,edition RETURN name,versions[0] AS v,edition"))[0]
info["neo4j_version"] = f"{rec['v']} ({rec['edition']})"
chk("neo4j reachable bolt://localhost:37689", True, info["neo4j_version"])
chk("graph counts match audited snapshot",
    (n, r, o) == (AUDITED["nodes"], AUDITED["rels"], AUDITED["obs"]),
    f"nodes={n:,} rels={r:,} ObservedPM25={o:,}")
info["graph_counts"] = {"nodes": n, "relationships": r, "ObservedPM25": o}

# 3-4 Ollama
v = requests.get("http://localhost:11434/api/version", timeout=10).json()["version"]
info["ollama_version"] = v
chk("ollama reachable :11434", True, f"v{v}")
tags = requests.get("http://localhost:11434/api/tags", timeout=10).json()["models"]
m = next((t for t in tags if t["name"] == "qwen2.5-coder:32b"), None)
chk("qwen2.5-coder:32b installed", m is not None, m["digest"][:24] if m else "MISSING")
if m:
    info["qwen_digest"] = m["digest"]
    info["qwen_details"] = m["details"]
    info["qwen_size_bytes"] = m["size"]

# 5-6 sentence-transformers / embedding model
import sentence_transformers, transformers, torch
info["python"] = platform.python_version()
info["sentence_transformers"] = sentence_transformers.__version__
info["transformers"] = transformers.__version__
info["torch"] = torch.__version__
info["cuda_available"] = torch.cuda.is_available()
info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
info["cuda_version"] = torch.version.cuda
chk("sentence-transformers importable", True, sentence_transformers.__version__)
from pipeline.systems import _get_st_model
_get_st_model()
chk("all-MiniLM-L6-v2 loads", True, "384-dim")

# 7 live retrieval returns exactly k
bench = json.loads(BENCH.read_text())
info["benchmark_n"] = len(bench)
q = bench[0]["nl_query"]
sample = {}
for k in (1, 3, 5):
    ids = [p["pattern_id"] for p in retrieve(q, k=k)]
    sample[k] = ids
    chk(f"retrieval returns exactly k={k}", len(ids) == k, ",".join(ids))
info["sample_query"] = q
info["sample_retrieval"] = sample
# prompt actually contains the retrieved exemplar text (not a silent fallback)
p3, ids3 = build_prompt(q, k=3)
from pipeline.systems import _load_dkb
pat = {x["pattern_id"]: x for x in _load_dkb()["query_patterns"]}
chk("retrieved exemplars present in prompt",
    all(pat[i].get("cypher", "") in p3 for i in ids3), ",".join(ids3))

ok = all(c[1] for c in checks)
out = {"checks": [{"check": a, "pass": b, "detail": c} for a, b, c in checks],
       "all_passed": ok, "info": info}
Path(__file__).resolve().parents[1].joinpath("results/env_verification.json").write_text(json.dumps(out, indent=2, default=str))
for a, b, c in checks:
    print(f"[{'PASS' if b else 'FAIL'}] {a}  {c}")
print("\nALL CHECKS PASSED" if ok else "\nVERIFICATION FAILED — DO NOT GENERATE")
sys.exit(0 if ok else 1)
