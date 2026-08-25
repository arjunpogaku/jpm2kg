# 01 — Prompt Equivalence at k=3

## Question

Does the new k-parameterised implementation reproduce the submitted
DKB+Hybrid prompt exactly when k=3?

## Method

**Arm A (historical).** The unmodified
`pipeline.systems.QueryGenerationSystems.dkb_hybrid` was invoked with
`systems._call_ollama` replaced in memory by a capture stub that records the
prompt and raises. Nothing on disk was modified. The captured string is
therefore byte-for-byte what the submitted experiment sent to Ollama, produced
by the hard-coded `k=3` call site (`systems.py:784`).

**Arm B (new).** `k_systems.build_prompt(nl_query, k=3)`.

**Sample.** 15 benchmark questions, at least three from each of the five
categories (aggregate, comparative, health_risk, station_filtering, temporal), taken at a stride across each category's
question list.

Comparison is `A == B` on the raw strings, with SHA-256 recorded for both.

## Result

**15/15 prompts are byte-identical.** No differences of any kind — not
whitespace, not exemplar ordering, not audit metadata.

| query_id | category | retrieved ids (k=3) | len A | len B | sha256 (both arms) | identical |
|---|---|---|---:|---:|---|---|
| q043 | aggregate | JP05|JP14|JP02 | 7249 | 7249 | `ce4af1a717c90ade…` | yes |
| q056 | aggregate | JP02|JP14|JP04 | 7187 | 7187 | `fe39062092c27db8…` | yes |
| q073 | aggregate | JP02|JP14|JP05 | 7248 | 7248 | `ebad5077e4c6dd93…` | yes |
| q172 | comparative | JP06|JP28|JP11 | 7670 | 7670 | `5350fc281e7394b9…` | yes |
| q179 | comparative | JP06|JP27|JP05 | 7451 | 7451 | `39b08d286089a397…` | yes |
| q189 | comparative | JP05|JP06|JP27 | 7447 | 7447 | `a72e65d49b38be40…` | yes |
| q131 | health_risk | JP19|JP01|JP07 | 7489 | 7489 | `b4b1b00655d8728d…` | yes |
| q145 | health_risk | JP16|JP21|JP01 | 7441 | 7441 | `80aa6085b341712d…` | yes |
| q158 | health_risk | JP21|JP16|JP02 | 7408 | 7408 | `aa8c2895c814521a…` | yes |
| q001 | station_filtering | JP28|JP06|JP05 | 7380 | 7380 | `00c415e33d8e1157…` | yes |
| q016 | station_filtering | JP01|JP04|JP05 | 7296 | 7296 | `a24c704dd6b4491a…` | yes |
| q028 | station_filtering | JP28|JP07|JP13 | 7666 | 7666 | `2b9323ed53b9d43c…` | yes |
| q092 | temporal | JP04|JP02|JP14 | 7189 | 7189 | `8fb1513c783d3125…` | yes |
| q105 | temporal | JP04|JP14|JP02 | 7191 | 7191 | `4cee8125b476fd90…` | yes |
| q118 | temporal | JP04|JP02|JP14 | 7187 | 7187 | `55d80525f459dbf5…` | yes |

Per-query record: `prompt_equivalence.csv`.

## Why identity is structural, not coincidental

The wrapper does not re-implement anything. It imports
`_retrieve_top_k`, `_build_dkb_prompt_core`, `_call_ollama` and
`_extract_cypher` from the historical `pipeline/systems.py` and calls them in
the same order. At k=3 the only executed difference from `dkb_hybrid` is that
the literal `3` arrives as a parameter instead of a literal, and that a
retrieval exception aborts instead of falling back to `retrieved = []`. Neither
touches the prompt string. Audit metadata (`retrieval_k`,
`retrieved_exemplar_ids`) is attached to the *result record*, never to the
prompt.

DKB contents, prompt wording, embedding model, similarity metric, generation
settings, evaluator, Neo4j queries, benchmark, `num_ctx` (8192), temperature
(0.0) and `num_predict` (512) are all unchanged.

## Gate

The Phase 3 precondition is satisfied: k=3 changes nothing but added audit
metadata. Phase 4 was cleared to proceed.
