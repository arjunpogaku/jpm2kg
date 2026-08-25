# Validity-filter robustness

AirCypher-150's reference queries apply the JPM2KG numerical-validity convention
`WHERE p.pm25 >= 0 AND p.pm25 <= 500` when they aggregate numerically — 104 of
the 150 do.

**Tolerant evaluation removes only that predicate** from those 104 reference
queries and scores each generated query against whichever reference it matches
better. Nothing else about the reference semantics changes, and the other 46
references are untouched. The relaxed forms are shipped verbatim in
`relaxed_reference_queries.csv` so the transformation can be inspected query by
query.

The point of the check is to confirm that the reported improvements are not an
artifact of models simply forgetting a JPM2KG-specific data-quality convention.
They are not: the configuration ordering is identical under strict and tolerant
evaluation for both VM-F1 and RMEM, and tolerance moves pooled VM-F1 by at most
+0.031 and pooled RMEM by at most +0.008 in any configuration.

## Key transitions

**Schema+Values → DKB-NoExamples** (does adding rules and traversal policies help
beyond canonical values?)

| Metric | Gain |
|---|---|
| VM-F1 strict | +0.145 |
| VM-F1 tolerant | +0.172 |
| RMEM strict | +0.040 |
| RMEM tolerant | +0.032 |

The gain survives tolerance under both metrics, and the clustered bootstrap CI
excludes zero in both cases. It is, however, carried by the two Qwen models; under
tolerant RMEM, Gemma-2-9B moves in the opposite direction. See
`../statistics/exact_paired_tests_rmem.csv`.

**DKB → DKB+Hybrid** (does retrieval add value?)

| Metric | Gain | 95 % CI |
|---|---|---|
| RMEM strict | +0.075 | [+0.045, +0.105] |
| RMEM tolerant | +0.077 | [+0.047, +0.108] |

VM-F1 for the same transition: +0.083 strict, +0.077 tolerant.

## Files

| File | Contents |
|---|---|
| `vmf1_strict_vs_tolerant_by_model.csv` | VM-F1 strict (saved and re-executed), relaxed-reference, and tolerant, per configuration × model, with per-record status counts. |
| `rmem_strict_vs_tolerant_by_model.csv` | RMEM strict / relaxed-only / tolerant counts and accuracies, per configuration × model. |
| `rmem_strict_vs_tolerant_by_category.csv` | The same, per configuration × category. |
| `relaxed_reference_queries.csv` | The 104 reference queries in both strict and relaxed form. |
