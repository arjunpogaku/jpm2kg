# Results Summary — BDA 2026 Paper

**Paper:** Structured Domain Grounding for Natural-Language Querying of Japan's Large-Scale PM2.5 Knowledge Graph
**Authors:** Arjun Chakravarthi POGAKU, Uday Kiran RAGE
**Affiliation:** University of Aizu, Japan

---

## What This Paper Does

We demonstrate that schema-grounded prompting is insufficient for semantically correct NL-to-Cypher generation on domain-specific environmental knowledge graphs. We introduce:

1. **JPM2KG** — Japan PM2.5 Knowledge Graph (142.3M nodes, 213.4M relationships, 71.1M observations from 1,116 monitoring stations)

2. **AirCypher-150** — 150 execution-validated NL-to-Cypher benchmark queries across 5 environmental monitoring categories

3. **DKB+Hybrid** — structured domain grounding framework combining schema, canonical values, domain rules, traversal policies, and hybrid exemplar retrieval

---

## Key Results

### Main Finding

Schema grounding produces executable but semantically incorrect queries (SE=0.001). Domain grounding is the critical driver of semantic correctness (DKB+Hybrid: SE=0.416, ~400× improvement).

### System Comparison (pooled across 4 LLMs, N=600 per system)

| System | CV | ES | EM | SE | RQ |
|---|---|---|---|---|---|
| Baseline | 0.010 | 0.652 | 0.000 | 0.000 | 0.156 |
| Schema Baseline | 0.565 | 0.508 | 0.000 | 0.001 | 0.148 |
| Schema+Values | 0.718 | 0.495 | 0.000 | 0.070 | 0.214 |
| DKB-NoExamples | 0.800 | 0.697 | 0.000 | 0.215 | 0.307 |
| DKB | 0.757 | 0.670 | 0.000 | 0.328 | 0.484 |
| **DKB+Hybrid** | **0.820** | **0.725** | 0.000 | **0.416** | **0.637** |

See: `05_results/tables/table1_main.csv`

### Ablation (qwen2.5-coder:32b, N=150)

Domain rules contribute the single largest improvement (+0.401 SE). Retrieval adds +0.185 SE on top of fixed exemplars.

| Configuration | SE | ΔSE |
|---|---|---|
| Baseline | 0.000 | — |
| Schema Baseline | 0.004 | +0.004 |
| Schema+Values | 0.094 | +0.090 |
| DKB-NoExamples | 0.495 | +0.401 |
| DKB | 0.462 | −0.033 |
| **DKB+Hybrid** | **0.647** | +0.185 |

See: `05_results/tables/table4_ablation.csv`

### Statistical Significance

All improvements over schema-only baseline are highly significant (p < 10⁻¹³⁰, large effect size, N=600 evaluation pairs).

| Comparison | p-value | Cohen's d | Effect |
|---|---|---|---|
| vs. Baseline | 1.22×10⁻¹⁴⁰ | 1.392 | Large |
| vs. Schema Baseline | 1.31×10⁻¹⁴⁰ | 1.385 | Large |
| vs. DKB | 2.31×10⁻⁴ | 0.085 | Small |

See: `05_results/tables/statistical_tests.txt`

### Per-Category (DKB+Hybrid)

Best on Aggregate (SE=0.580). Hardest: Comparative (SE=0.238).

| Category | N | SE |
|---|---|---|
| Aggregate | 152 | 0.580 |
| Temporal | 120 | 0.418 |
| Health Risk | 120 | 0.417 |
| Station Filtering | 120 | 0.337 |
| Comparative | 88 | 0.238 |
| **Overall** | **600** | **0.416** |

See: `05_results/tables/table3_categories.csv`

### Fine-Tuned Model

text2cypher-gemma-2-9b achieves SE=0.000 despite CV=0.613, ES=0.580. Queries execute but return empty results due to incorrect canonical values (e.g., `"Yamaguchi"` vs. `"Yamaguchi Prefecture"`). This demonstrates that fine-tuning on generic graph data does not transfer domain-specific value knowledge.

---

## Where to Find Everything

| What | Location |
|---|---|
| KG schema and stats | `01_knowledge_graph/` |
| KG Neo4j dump | `01_knowledge_graph/neo4j_backup/` |
| AirCypher-150 benchmark | `02_benchmark/` |
| Domain Knowledge Base | `03_domain_knowledge_base/` |
| Pipeline code | `04_pipeline/` |
| All raw results | `05_results/raw/` |
| All tables (CSV+LaTeX) | `05_results/tables/` |
| All figures (PDF+PNG) | `05_results/figures/` |
| Reproduction steps | `REPRODUCIBILITY.md` |
