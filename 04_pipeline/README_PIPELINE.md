# Evaluation Pipeline

## Overview

The pipeline evaluates six NL-to-Cypher prompting systems against AirCypher-150, using five LLMs and five evaluation metrics. All scripts are in this directory.

## Scripts

### `systems.py` — Six Prompting Systems

Defines the six systems evaluated in the paper:

| System (internal name) | Description |
|---|---|
| `baseline` | Zero-shot prompting with no schema or domain context |
| `cypherbench_style` | Schema-only prompting (CypherBench/ACL'25 style) |
| `schema_plus_values` | Schema + canonical domain values (property enumerations) |
| `dkb_no_examples` | Full DKB context (schema + values + rules) without exemplars |
| `dkb` | Full DKB with a fixed set of 28 exemplar NL–Cypher pairs |
| `dkb_hybrid` | Full DKB with dynamic hybrid retrieval (BM25 + embedding) |

Also defines the `text2cypher_ft` system, which calls the fine-tuned `neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1` model via HuggingFace Transformers (requires GPU).

### `evaluator.py` — Five Evaluation Metrics

Implements five metrics with a 10-second execution timeout per query:

| Metric | Abbreviation | Description |
|---|---|---|
| Cypher Validity | CV | 1 if generated Cypher executes without error |
| Execution Success | ES | Cosine similarity between result column names |
| Exact Match | EM | 1 if generated results exactly equal gold results |
| Set Equality | SE | 1 if result sets are equal (order-independent) — **primary metric** |
| Result Quality | RQ | F1-like overlap between result sets |

SE is the primary metric because it captures semantic correctness: the query returns the right data, regardless of column ordering or row ordering.

### `experiment_runner.py` — Main Evaluation Loop

Runs the full evaluation with:
- Checkpointing: saves progress every N queries; resumes from checkpoint on restart
- Per-query logging to the output JSONL file
- Configurable LLM timeout (default: 45 seconds)
- Configurable execution timeout (default: 10 seconds)

### `dkb_repair.py` — Value-Anchoring Repair

Post-processing step that replaces non-canonical values in generated Cypher with the closest canonical value from the DKB. For example:
- `"Yamaguchi"` → `"Yamaguchi Prefecture"`
- `"winter"` → `"Winter"`
- `"general"` → `"General Station"`

The repair is deterministic (no LLM calls) and improves CV and SE for systems that generate plausible but incorrect values.

### `aggregate_full.py` — Tables and Figures

Generates all result tables (CSV + LaTeX) and figures (PDF + PNG) from a results JSONL file. Runs Wilcoxon signed-rank tests with Cohen's d and bootstrap confidence intervals.

### `config.yaml` — Configuration

Key settings:

```yaml
neo4j_uri: bolt://localhost:37689
neo4j_user: neo4j
neo4j_password: <password>
ollama_url: http://localhost:11434
llm_temperature: 0.0
llm_timeout_s: 45
exec_timeout_s: 10
```

## Configuration Constants

| Parameter | Value |
|---|---|
| LLM temperature | 0.0 (deterministic) |
| Ollama endpoint | http://localhost:11434 |
| Neo4j endpoint | bolt://localhost:37689 |
| Execution timeout | 10 seconds per query |
| LLM inference timeout | 45 seconds |

## Running the Pipeline

```bash
# Install dependencies
pip install -r requirements.txt

# Run all systems × all LLMs (8–12 hours total)
python experiment_runner.py \
  --benchmark ../02_benchmark/aircypher150_benchmark.json \
  --systems baseline cypherbench_style schema_plus_values dkb_no_examples dkb dkb_hybrid \
  --llms llama3.2:3b gemma2:9b qwen2.5-coder:32b qwen2.5:72b \
  --results-file ../05_results/raw/results_reproduced.jsonl

# Generate tables and figures
python aggregate_full.py \
  ../05_results/raw/results_reproduced.jsonl \
  ../02_benchmark/aircypher150_benchmark.json
```
