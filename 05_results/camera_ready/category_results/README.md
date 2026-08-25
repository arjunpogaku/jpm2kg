# Results by benchmark category

## DKB+Hybrid VM-F1 by category and model

Source: `vmf1_by_category_model_dkbhybrid.csv`.

| Category | L3B | G9B | QC32B | Q72B | Pooled |
|---|---|---|---|---|---|
| Aggregate | .327 | .487 | .712 | .792 | .580 |
| Temporal | .009 | .197 | .773 | .693 | .418 |
| Health Risk | .000 | .167 | .800 | .700 | .417 |
| Station Filtering | .205 | .412 | .351 | .380 | .337 |
| Comparative | .000 | .000 | .555 | .397 | .238 |
| **Overall** | **.126** | **.279** | **.647** | **.614** | **.416** |

L3B = Llama-3.2-3B, G9B = Gemma-2-9B, QC32B = Qwen2.5-Coder-32B, Q72B = Qwen2.5-72B.
The pooled column is the mean over all 4 × N records in the category, not a mean
of the four model columns.

Aggregate queries are the easiest category for every model. Comparative queries
are the hardest, and the two smaller models score 0 on them entirely — they
require a multi-branch query shape that neither produces reliably. Station
Filtering is the one category where model size does not help: the four models
land between .205 and .412, and the strongest model overall (QC32B) is not the
strongest here.

## Files

| File | Contents |
|---|---|
| `vmf1_by_category_model_dkbhybrid.csv` | The table above, machine-readable. |
| `vmf1_by_category_model_all_configurations.csv` | The same breakdown for all six prompting configurations. |
| `rmem_by_category.csv` | RMEM strict and tolerant, by configuration × category, pooled over models. |
| `rmem_by_category_model.csv` | RMEM strict and tolerant, by configuration × category × model. |

Category counts are 38 Aggregate, 30 Temporal, 30 Health Risk, 30 Station
Filtering, 22 Comparative. The `n` column in the pooled RMEM files is four times
that, since it counts records rather than questions.
