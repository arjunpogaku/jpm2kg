# Evaluation Results — JPM2KG NL-to-Cypher

## Overview

**Primary metric:** Set Equality (SE)
**Total evaluations:** 3,750 records (150 queries × 6 systems × 4 LLMs + 150 text2cypher)

### Models Evaluated

| Model | Parameters | Provider |
|---|---|---|
| llama3.2:3b | 3B | Meta (via Ollama) |
| gemma2:9b | 9B | Google (via Ollama) |
| qwen2.5-coder:32b | 32B | Alibaba (via Ollama) |
| qwen2.5:72b | 72B | Alibaba (via Ollama) |
| text2cypher-gemma-2-9b | 9B (fine-tuned) | Neo4j (via HuggingFace) |

### Systems Evaluated

| System | Description |
|---|---|
| Baseline | Zero-shot, no context |
| Schema Baseline | Schema-only prompting (CypherBench-style) |
| Schema+Values | Schema + canonical domain values |
| DKB-NoExamples | Full domain knowledge, no examples |
| DKB | Full DKB with fixed exemplar set |
| DKB+Hybrid | Full DKB + dynamic hybrid retrieval (BEST) |

## Main Results (Table 1)

Pooled over 4 LLMs (llama3.2:3b, gemma2:9b, qwen2.5-coder:32b, qwen2.5:72b), N=600 per system:

| System | CV | ES | EM | SE | RQ |
|---|---|---|---|---|---|
| Baseline | 0.010 | 0.652 | 0.000 | 0.000 | 0.156 |
| Schema Baseline | 0.565 | 0.508 | 0.000 | 0.001 | 0.148 |
| Schema+Values | 0.718 | 0.495 | 0.000 | 0.070 | 0.214 |
| DKB-NoExamples | 0.800 | 0.697 | 0.000 | 0.215 | 0.307 |
| DKB | 0.757 | 0.670 | 0.000 | 0.328 | 0.484 |
| **DKB+Hybrid** | **0.820** | **0.725** | 0.000 | **0.416** | **0.637** |

**Key finding:** Schema grounding alone (SE=0.001) is insufficient; DKB+Hybrid achieves ~400× improvement (SE=0.416).

## Ablation Results (qwen2.5-coder:32b)

| Configuration | SE | ΔSE |
|---|---|---|
| Baseline | 0.000 | — |
| Schema Baseline | 0.004 | +0.004 |
| Schema+Values | 0.094 | +0.090 |
| DKB-NoExamples | 0.495 | +0.401 |
| DKB | 0.462 | −0.033 |
| **DKB+Hybrid** | **0.647** | +0.185 |

## Per-Category Results (DKB+Hybrid, pooled over 4 LLMs)

| Category | N | SE |
|---|---|---|
| Aggregate | 152 | 0.580 |
| Temporal | 120 | 0.418 |
| Health Risk | 120 | 0.417 |
| Station Filtering | 120 | 0.337 |
| Comparative | 88 | 0.238 |
| **Overall** | **600** | **0.416** |

## Statistical Significance

DKB+Hybrid vs. baseline comparisons (Wilcoxon signed-rank, N=600):

| Comparison | p-value | Cohen's d | 95% CI | Effect |
|---|---|---|---|---|
| vs. Baseline | 1.22×10⁻¹⁴⁰ | 1.392 | [+0.352, +0.390] | Large |
| vs. Schema Baseline | 1.31×10⁻¹⁴⁰ | 1.385 | [+0.351, +0.388] | Large |
| vs. DKB | 2.31×10⁻⁴ | 0.085 | [+0.015, +0.049] | Small |

## Files in This Directory

| File | Description |
|---|---|
| `raw/results_full.jsonl` | All raw evaluation records (one JSON per line) |
| `tables/table1_main.csv` | System comparison (main results table) |
| `tables/table1_main.tex` | LaTeX version of Table 1 |
| `tables/table2_per_llm.csv` | Per-LLM breakdown |
| `tables/table2_per_llm.tex` | LaTeX version of Table 2 |
| `tables/table3_categories.csv` | Per-category SE scores |
| `tables/table4_ablation.csv` | Ablation study (qwen2.5-coder:32b) |
| `tables/table4_ablation.tex` | LaTeX version of Table 4 |
| `tables/statistical_tests.txt` | Full Wilcoxon test output |
| `figures/` | All evaluation figures (PDF + PNG) |

## Result File Format

Each line in `results_full.jsonl` is a JSON object:

```json
{
  "query_id": "q001",
  "nl_query": "Which general stations are in Yamaguchi Prefecture?",
  "gold_cypher": "MATCH ...",
  "query_type": "station_filtering",
  "complexity": "simple",
  "system": "dkb_hybrid",
  "llm": "qwen2.5-coder:32b",
  "generated_cypher": "MATCH ...",
  "metrics": {"CV": 1.0, "ES": 1.0, "EM": 0.0, "SE": 1.0, "RQ": 1.0},
  "generation_time_ms": 1234.5,
  "eval_error": null,
  "timestamp": "2026-06-24T..."
}
```
