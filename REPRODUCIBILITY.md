# Reproducibility Guide — AirCypher-150 Evaluation

This guide explains how to reproduce all experiments from the paper.
Estimated total time: 8–12 hours (mostly LLM inference time).

---

## Requirements

### Hardware
- GPU: ≥48 GB VRAM recommended (tested on 2× NVIDIA RTX A6000, 96 GB total)
- RAM: ≥64 GB
- Disk: ≥300 GB (for Neo4j KG data)

### Software
- Ubuntu 20.04 / 22.04 / 24.04
- Docker (for Neo4j)
- Ollama (for open-source LLM inference)
- Python 3.10+
- CUDA 12.x (for HuggingFace model)

---

## Step 1: Restore the Knowledge Graph

```bash
# 1a. Start a Neo4j container
docker run -d \
  --name jpm2kg-neo4j \
  -p 7474:7474 -p 37689:7687 \
  -v $(pwd)/neo4j_data:/data \
  -e NEO4J_AUTH=neo4j/StrongPasswordHere \
  -e NEO4J_dbms_memory_heap_max__size=8G \
  neo4j:2026.02.2

# 1b. Copy dump file into container
docker cp 01_knowledge_graph/neo4j_backup/jpm2kg.dump \
  jpm2kg-neo4j:/tmp/

# 1c. Stop Neo4j, load dump, restart
docker stop jpm2kg-neo4j
docker exec jpm2kg-neo4j neo4j-admin database load \
  --from-path=/tmp/ --database=neo4j --overwrite-destination=true
docker start jpm2kg-neo4j

# Wait 60 seconds, then verify:
# cypher-shell -a bolt://localhost:37689 -u neo4j -p StrongPasswordHere \
#   "MATCH (n:Station) RETURN count(n)"
# Expected: Station=1116, ObservationTime=71149372
```

## Step 2: Install Ollama and Pull LLMs

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull all 4 evaluated models
ollama pull llama3.2:3b
ollama pull gemma2:9b
ollama pull qwen2.5-coder:32b
ollama pull qwen2.5:72b

# Verify
ollama list
```

## Step 3: Download Fine-Tuned Model

```bash
# Download text2cypher fine-tuned model
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
  repo_id='neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1',
  local_dir='./models/text2cypher-gemma-2-9b'
)
"
```

## Step 4: Install Python Dependencies

```bash
cd 04_pipeline/
pip install -r requirements.txt
```

## Step 5: Configure

```bash
# Edit 04_pipeline/config.yaml to set:
#   neo4j_uri: bolt://localhost:37689
#   neo4j_user: neo4j
#   neo4j_password: StrongPasswordHere
#   ollama_url: http://localhost:11434
```

## Step 6: Run Evaluation

```bash
cd 04_pipeline/

# Run all 6 systems × 4 LLMs × 150 queries
# This will take approximately 8–12 hours total
USE_TF=0 python3 experiment_runner.py \
  --benchmark ../02_benchmark/aircypher150_benchmark.json \
  --systems baseline cypherbench_style schema_plus_values dkb_no_examples dkb dkb_hybrid \
  --llms llama3.2:3b gemma2:9b qwen2.5-coder:32b qwen2.5:72b \
  --exec-timeout 10 \
  --llm-timeout 45 \
  --results-file ../05_results/raw/results_reproduced.jsonl

# Run fine-tuned model separately (requires GPU)
USE_TF=1 python3 experiment_runner.py \
  --benchmark ../02_benchmark/aircypher150_benchmark.json \
  --systems text2cypher_ft \
  --model-path ../models/text2cypher-gemma-2-9b \
  --exec-timeout 10 \
  --results-file ../05_results/raw/results_text2cypher.jsonl
```

## Step 7: Generate Tables and Figures

```bash
python3 aggregate_full.py \
  ../05_results/raw/results_reproduced.jsonl \
  ../02_benchmark/aircypher150_benchmark.json \
  --output-dir ../05_results/reproduced/
```

## Step 8: Verify Results

```bash
python3 -c "
import json, numpy as np

reproduced = [json.loads(l) for l in open('../05_results/raw/results_reproduced.jsonl') if l.strip()]

dkb_hybrid = [r for r in reproduced if r['system'] == 'dkb_hybrid']
se_mean = np.mean([r['metrics']['SE'] for r in dkb_hybrid])
print(f'DKB+Hybrid SE: {se_mean:.3f}  (paper: 0.416)')
print('MATCH' if abs(se_mean - 0.416) < 0.01 else 'CHECK DIFFERENCES')
"
```

---

## Expected Results Summary

| System | Expected SE |
|---|---|
| Baseline | ≈ 0.000 |
| Schema Baseline | ≈ 0.001 |
| Schema+Values | ≈ 0.070 |
| DKB-NoExamples | ≈ 0.215 |
| DKB | ≈ 0.328 |
| DKB+Hybrid | ≈ 0.416 |
| text2cypher-gemma-2-9b | ≈ 0.000 |

LLM inference uses temperature=0.0, so results are near-deterministic. Minor differences (±0.005) may occur due to Ollama version differences.

---

## Troubleshooting

**Neo4j timeout:** Increase JVM heap size in docker run command (`-e NEO4J_dbms_memory_heap_max__size=16G`).

**Ollama OOM:** Run one LLM at a time; unload previous model with `ollama rm <model>`.

**GPU OOM for text2cypher:** Use `--load-in-4bit` flag if available in transformers version.

**Empty results from graph:** Check canonical values match graph vocabulary (see `03_domain_knowledge_base/dkb_structure_explained.md`).

**Checkpoint resume:** `experiment_runner.py` saves a checkpoint after each query. Re-run the same command to resume from where it stopped.
