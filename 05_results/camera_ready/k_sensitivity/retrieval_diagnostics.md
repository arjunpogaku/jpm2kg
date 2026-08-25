# 02 — Retrieval Diagnostics (k = 1, 3, 5)

Pool: 28 DKB `query_patterns` (JP01–JP28). Benchmark: AirCypher-150 (150 questions). Encoder: `all-MiniLM-L6-v2`, cosine on L2-normalised embeddings, `np.argsort` descending — identical to the submitted implementation.

## Nesting check

| Claim | Violations | Result |
|---|---:|---|
| top-1(k=1) == first item of top-3(k=3) | 0 | HOLDS for every query |
| top-3(k=3) == first three items of top-5(k=5) | 0 | HOLDS for every query |

Retrieval is a single ranking truncated at k, so the k-sweep varies only how deep that one ranking is read. No score ties reorder the prefix.


## Unique exemplars retrieved

| k | unique exemplars | of pool | retrieval slots filled |
|---:|---:|---:|---:|
| 1 | 13 | 13/28 | 150 |
| 3 | 20 | 20/28 | 450 |
| 5 | 22 | 22/28 | 750 |

## Exemplar retrieval frequency


### k=1

| exemplar | intent | times retrieved | % of queries |
|---|---|---:|---:|
| JP01 | count_unhealthy_by_station | 31 | 20.7% |
| JP02 | average_pm25_by_prefecture | 23 | 15.3% |
| JP06 | roadside_vs_general_pm25 | 19 | 12.7% |
| JP14 | monthly_pm25_pattern | 17 | 11.3% |
| JP21 | who_guideline_exceedance_rate | 17 | 11.3% |
| JP04 | seasonal_pm25_japan | 13 | 8.7% |
| JP05 | prefecture_seasonal_ranking | 12 | 8.0% |
| JP28 | station_count_by_prefecture | 6 | 4.0% |
| JP17 | pm25_level_distribution | 3 | 2.0% |
| JP16 | safe_station_pct_by_prefecture | 3 | 2.0% |
| JP27 | who_compliant_stations | 3 | 2.0% |
| JP19 | pm25_spike_detection | 2 | 1.3% |
| JP07 | stations_in_prefecture | 1 | 0.7% |

Never retrieved at k=1 (15): JP03, JP08, JP09, JP10, JP11, JP12, JP13, JP15, JP18, JP20, JP22, JP23, JP24, JP25, JP26

### k=3

| exemplar | intent | times retrieved | % of queries |
|---|---|---:|---:|
| JP14 | monthly_pm25_pattern | 62 | 41.3% |
| JP02 | average_pm25_by_prefecture | 57 | 38.0% |
| JP04 | seasonal_pm25_japan | 55 | 36.7% |
| JP01 | count_unhealthy_by_station | 50 | 33.3% |
| JP05 | prefecture_seasonal_ranking | 48 | 32.0% |
| JP06 | roadside_vs_general_pm25 | 30 | 20.0% |
| JP28 | station_count_by_prefecture | 26 | 17.3% |
| JP16 | safe_station_pct_by_prefecture | 26 | 17.3% |
| JP19 | pm25_spike_detection | 19 | 12.7% |
| JP21 | who_guideline_exceedance_rate | 19 | 12.7% |
| JP27 | who_compliant_stations | 16 | 10.7% |
| JP11 | rush_hour_pm25 | 13 | 8.7% |
| JP17 | pm25_level_distribution | 9 | 6.0% |
| JP07 | stations_in_prefecture | 8 | 5.3% |
| JP22 | station_seasonal_comparison | 3 | 2.0% |
| JP23 | pm25_above_standard_hours_by_year | 3 | 2.0% |
| JP13 | station_full_profile | 2 | 1.3% |
| JP15 | station_yearly_trend | 2 | 1.3% |
| JP26 | prefecture_pm25_statistics | 1 | 0.7% |
| JP08 | year_over_year_trend | 1 | 0.7% |

Never retrieved at k=3 (8): JP03, JP09, JP10, JP12, JP18, JP20, JP24, JP25

### k=5

| exemplar | intent | times retrieved | % of queries |
|---|---|---:|---:|
| JP04 | seasonal_pm25_japan | 99 | 66.0% |
| JP05 | prefecture_seasonal_ranking | 89 | 59.3% |
| JP02 | average_pm25_by_prefecture | 71 | 47.3% |
| JP01 | count_unhealthy_by_station | 66 | 44.0% |
| JP14 | monthly_pm25_pattern | 66 | 44.0% |
| JP16 | safe_station_pct_by_prefecture | 40 | 26.7% |
| JP06 | roadside_vs_general_pm25 | 38 | 25.3% |
| JP28 | station_count_by_prefecture | 36 | 24.0% |
| JP27 | who_compliant_stations | 36 | 24.0% |
| JP19 | pm25_spike_detection | 25 | 16.7% |
| JP08 | year_over_year_trend | 24 | 16.0% |
| JP12 | prefecture_winter_who_exceedance | 23 | 15.3% |
| JP26 | prefecture_pm25_statistics | 20 | 13.3% |
| JP22 | station_seasonal_comparison | 19 | 12.7% |
| JP21 | who_guideline_exceedance_rate | 19 | 12.7% |
| JP23 | pm25_above_standard_hours_by_year | 16 | 10.7% |
| JP17 | pm25_level_distribution | 15 | 10.0% |
| JP15 | station_yearly_trend | 13 | 8.7% |
| JP11 | rush_hour_pm25 | 13 | 8.7% |
| JP07 | stations_in_prefecture | 12 | 8.0% |
| JP13 | station_full_profile | 5 | 3.3% |
| JP03 | top_polluted_prefectures | 5 | 3.3% |

Never retrieved at k=5 (6): JP09, JP10, JP18, JP20, JP24, JP25

## Prompt composition (published cap of 8 exemplars)

| k | retrieved | static (displaced tail) | total |
|---:|---:|---|---:|
| 1 | 1 | JP01–JP07 | 8 |
| 3 | 3 | JP01–JP05 | 8 |
| 5 | 5 | JP01–JP03 | 8 |

Increasing k does not lengthen the prompt; it substitutes retrieved exemplars for the tail of the static block. Overlap between a retrieved exemplar and a still-shown static exemplar therefore duplicates that exemplar in the prompt — this is the published behaviour and is left unchanged.

| k | queries whose retrieved set overlaps the shown static block | of 150 |
|---:|---:|---:|
| 1 | 99 | 150 |
| 3 | 126 | 150 |
| 5 | 133 | 150 |

## Retrieved-exemplar category distribution

| benchmark category | n questions | k=1 distinct exemplars | k=3 | k=5 |
|---|---:|---:|---:|---:|
| aggregate | 38 | 6 | 10 | 15 |
| comparative | 22 | 4 | 7 | 12 |
| health_risk | 30 | 4 | 10 | 15 |
| station_filtering | 30 | 4 | 12 | 16 |
| temporal | 30 | 3 | 8 | 11 |

Per-category top exemplar:

| category | most-retrieved exemplar at k=3 | share of that category's k=3 slots |
|---|---|---:|
| aggregate | JP14 (monthly_pm25_pattern) | 28.9% |
| comparative | JP06 (roadside_vs_general_pm25) | 31.8% |
| health_risk | JP01 (count_unhealthy_by_station) | 27.8% |
| station_filtering | JP01 (count_unhealthy_by_station) | 24.4% |
| temporal | JP14 (monthly_pm25_pattern) | 32.2% |

## Questions whose retrieval sets differ across k

By construction every question's set differs across k (a longer prefix of the same ranking). The number of *newly added* exemplars is exactly k−k′ per question:

- k=1 → k=3: 2 new exemplars for all 150 questions
- k=3 → k=5: 2 new exemplars for all 150 questions
- k=1 → k=5: 4 new exemplars for all 150 questions
