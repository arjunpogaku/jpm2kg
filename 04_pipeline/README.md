# Pipeline

## Files

| File | Purpose |
|---|---|
| `METRICS.md` | **Read this first.** Definitions of CV, ES, VM-F1 and RMEM, and the legacy `SE` field name in the raw results. |
| `systems.py` | The six prompting configurations and the fine-tuned-baseline wrapper. |
| `sota_ft_model.py` | Loader for the fine-tuned Text2Cypher baseline (HuggingFace). |
| `evaluator.py` | CV, ES, EM and VM-F1 (stored as `SE`). This is the implementation that produced the reported raw results. |
| `camera_ready_evaluator.py` | Camera-ready evaluation: VM-F1 and RMEM, strict and tolerant. |
| `experiment_runner.py` | Generation + evaluation loop. |
| `generate_camera_ready_tables.py` | Rebuilds the paper tables into `../05_results/tables/`. |
| `config.yaml` | Model, retrieval, path and system settings. No credentials. |
| `.env.example` | Environment variables to set. |
| `requirements.txt` | Pinned dependencies. |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env && $EDITOR .env      # set NEO4J_PASSWORD
export $(grep -v '^#' .env | xargs)
```

Anything that touches the graph needs a running JPM2KG instance; see
`../06_environment/docker_setup.md`.

## The six prompting configurations

| Key in code | Paper label | Grounding |
|---|---|---|
| `baseline` | Baseline | Question only |
| `cypherbench_style` | Schema | Live graph schema |
| `schema_plus_values` | Schema+Values | Schema + canonical values |
| `dkb_no_examples` | DKB-NoExamples | Full DKB minus exemplars |
| `dkb` | DKB | Full DKB, 8 fixed exemplars |
| `dkb_hybrid` | DKB+Hybrid | Full DKB, 3 retrieved + 5 fixed exemplars |

## Differences from the submitted code

The active files differ from the originally submitted sources only in the following ways.
**No metric definition, prompt text or generation setting was changed.**

1. **No credentials in the repository.** `NEO4J_PASSWORD` is read from the
   environment. `evaluator.py` raises immediately if it is unset rather than
   attempting a connection with a placeholder.
2. **Paths resolve relative to the repository** instead of the original machine's
   absolute paths, so the package is self-contained. The DKB, benchmark and
   results locations are still overridable by environment variable.
3. **`DKB+Hybrid` retrieval now fails loudly.** The submitted code wrapped the
   retrieval call in a bare `except` that fell back to zero retrieved exemplars,
   which would silently degrade DKB+Hybrid into DKB if
   `sentence-transformers` were unavailable. That fallback is removed and a
   missing dependency now raises with an actionable message. The reported run was
   unaffected — `sentence-transformers` was installed and retrieval succeeded, as
   verified in `../05_results/camera_ready/k_sensitivity/`.
4. **`experiment_runner.py` dispatches all six configurations.** The submitted
   runner's dispatch listed only four; `schema_plus_values` and
   `dkb_no_examples` are now reachable, and `DEFAULT_LLMS` lists the four models
   actually reported. The submitted runner's stale defaults pointed at models and
   a benchmark path from an earlier iteration.
5. **Imports resolve within this package** (`from systems import ...`), with the
   historical `pipeline.*` layout kept as a fallback.
6. Docstrings and comments updated for the camera-ready metric names.

`rank-bm25` is not a dependency and is not imported anywhere: DKB+Hybrid
retrieval is dense cosine similarity only, with no sparse term.

## Reproducing

Three separate things, in increasing cost:

**1. Rebuild the paper tables from the shipped results** — no graph, no models,
seconds:

```bash
python3 generate_camera_ready_tables.py --check
```

**2. Recompute the metrics against JPM2KG** — needs the graph, takes hours:

```bash
python3 camera_ready_evaluator.py
```

**3. Regenerate the LLM outputs** — needs the graph, Ollama and the four models;
took about 11.5 h of generation time originally:

```bash
python3 experiment_runner.py
```

Step 3 writes to a new file and does not overwrite
`../05_results/raw/results_full.jsonl`. Because no random seed was pinned, it
will not reproduce the historical outputs bit-for-bit; see
`../06_environment/models_and_generation.md`.
