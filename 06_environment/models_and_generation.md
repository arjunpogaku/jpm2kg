# Models and Generation Settings

## Models

Four open-source models served through **Ollama**, at the tags used for the
reported experiments:

```
llama3.2:3b
gemma2:9b
qwen2.5-coder:32b
qwen2.5:72b
```

Plus one fine-tuned baseline served through **HuggingFace Transformers**, not
Ollama:

```
neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1
```

## Ollama generation settings

These are the settings used for all 3,600 prompting-system generations
(`04_pipeline/systems.py`, `_call_ollama`; endpoint `POST /api/generate`):

| Setting | Value |
|---|---|
| `temperature` | 0 (greedy) |
| `num_ctx` | 8192 |
| `num_predict` | 512 |
| `stream` | false |
| `think` | false |
| `keep_alive` | 30m |
| seed | **not set** |
| retries | 2 attempts, 1 s apart |
| per-call timeout | 60 s default; 120 s for `qwen2.5:72b` |

`top_p`, `top_k`, `repeat_penalty` and `stop` were left at Ollama's defaults.

Because no seed was pinned, decoding is greedy but not seed-fixed. Regenerating
across a different Ollama version or GPU state is not guaranteed to reproduce the
outputs bit-for-bit. Reproducing the *reported tables* does not require
regeneration — the raw generations ship in `../05_results/raw/results_full.jsonl`.

## Fine-tuned baseline settings

| Setting | Value |
|---|---|
| Checkpoint | `neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1` |
| Runtime | HuggingFace Transformers (`transformers==4.56.1`, `torch==2.7.1`) |
| Quantization | 4-bit NF4, double quantization, bfloat16 compute |
| Device map | `auto` |
| Decoding | `do_sample=False` (greedy) |
| Output length | `max_new_tokens=256` |
| seed | not set |

The loader is `../04_pipeline/sota_ft_model.py`. Prompt format is the model
card's `<schema>…</schema> / Question: / Answer:` format.

## Historical generation latency

All **3,750 of 3,750** records carry a recorded `generation_time_ms`. The medians
below include the six generations (0.16 %) that timed out.

| Model | Median (s) | p95 (s) |
|---|---|---|
| `llama3.2:3b` | 5.08 | 10.77 |
| `gemma2:9b` | 7.41 | 13.12 |
| `qwen2.5:72b` | 11.15 | 25.85 |
| `qwen2.5-coder:32b` | 12.87 | 27.17 |
| Text2Cypher-Gemma (FT) | 16.01 | 39.37 |

`qwen2.5-coder:32b` is slower than `qwen2.5:72b` at the median. This is reported
as observed wall-clock time; the retained records do not support an explanation.

Total accumulated generation time across all 3,750 calls: 41,359 s ≈ 11.5 h.
Per-system and per-model × system breakdowns are derivable from the latency
fields in `../05_results/raw/results_full.jsonl`.

## What was not recorded

The following were not logged at experiment time and are therefore **not** stated
as experimental parameters:

- **Model quantization.** The retained environment reports Q4_K_M for
  `llama3.2:3b` and `qwen2.5-coder:32b` and Q4_0 for `gemma2:9b`; `qwen2.5:72b` is
  no longer installed. None of these is provably the binary used in June 2026, and
  they are not a single blanket quantization level.
- **Model digests.** No digest was captured during the experiment. Any digest
  appearing elsewhere in this repository (for example in
  `../05_results/camera_ready/k_sensitivity/results/env_verification.json`) is a
  later current-environment reading and does not describe the reported run.
- **Ollama server version.** Not recorded for the reported run.
- **Parameter counts.** The `3b` / `9b` / `32b` / `72b` figures come from the tag
  names.

The model table in this document is the conservative one: it contains only
historically established values.

## Software

Python dependencies are pinned in `../04_pipeline/requirements.txt`. Neo4j
2026.02.2 Community Edition; see `docker_setup.md`.
