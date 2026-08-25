# Submitted pipeline sources (archived, unmodified)

These files are byte-identical copies of the pipeline as submitted for BDA 2026.
They are kept so the reported generations and scores remain reproducible, and
they are not maintained.

| File | Purpose |
|---|---|
| `evaluator_bda2026_submission.py` | Metric implementation used to produce `05_results/raw/results_full.jsonl`. Its `SE` field is the legacy name for what the camera-ready paper calls Value-Multiset F1 (VM-F1); see `../METRICS.md`. |
| `systems_bda2026_submission.py` | The six prompting configurations plus the fine-tuned baseline wrapper, as run. |
| `experiment_runner_bda2026_submission.py` | The generation/evaluation loop, as run. |
| `config_bda2026_submission.yaml` | The configuration file as shipped, including the machine-local absolute paths of the original run. |
| `sota_ft_model_bda2026_submission.py` | The fine-tuned Text2Cypher loader used for the baseline. |

The active files in `../` differ only in reproducibility and error-handling
respects, documented in `../README.md`. No metric definition and no prompt text
was changed.

## Note on the contents of these files

Because these copies are byte-identical to what was run, they still contain the
development machine's absolute paths and a hard-coded Neo4j password string
(`StrongPasswordHere`) in `config_bda2026_submission.yaml`,
`evaluator_bda2026_submission.py` and `systems_bda2026_submission.py`. These are
historical artifacts of the submitted code, not live credentials, and they are
not used by anything in the active pipeline — which reads `NEO4J_PASSWORD` from
the environment (see `../.env.example`). Do not reuse that string as a password.
