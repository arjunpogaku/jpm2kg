#!/usr/bin/env python3
"""
compute_per_llm_stats.py — per-LLM statistical significance testing and
per-LLM/per-category breakdown supporting Table 4 (Statistical Analysis) of
the BDA2026 paper.

For each of the three comparisons (DKB+Hybrid vs. Baseline, vs. Schema
Baseline, vs. DKB):
  1. Runs a one-sided paired Wilcoxon signed-rank test on Set Equality (SE)
     separately for each of the four LLMs (N=150 query pairs per LLM,
     zero_method='pratt').
  2. Computes the paired effect size dz = mean(diff) / std(diff, ddof=1) per LLM.
  3. Combines the four per-LLM p-values into one test statistic per comparison
     via Stouffer's method (equal weights, since N=150 is equal across all
     four LLMs).

Also reports mean SE per system per LLM (Table A) and per-category SE for
DKB+Hybrid per LLM (Table B), each with a Pooled column.

Reads:
  ../05_results/raw/results_full.jsonl        — per-query evaluation records
  ../02_benchmark/aircypher150_benchmark.json — query_id -> category

Writes (to ../05_results/tables/, or --output-dir if given):
  table4_per_llm_pvalues.csv     — one row per (comparison, LLM): N, p, dz
  table4_combined_pvalues.csv    — one row per comparison: Stouffer z/p, dz summary
  table4_statistical_comparison.tex — booktabs table matching paper's tab:stats
  statistical_tests.txt          — human-readable summary of the above
  per_llm_overall.csv            — mean SE per system per LLM, + Pooled
  per_llm_per_category_dkbhybrid.csv — DKB+Hybrid SE per category per LLM, + Pooled

Usage: python compute_per_llm_stats.py [results.jsonl] [benchmark.json] [--output-dir DIR]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon, norm

HERE = Path(__file__).resolve().parent
DEFAULT_RESULTS = HERE / "../05_results/raw/results_full.jsonl"
DEFAULT_BENCH = HERE / "../02_benchmark/aircypher150_benchmark.json"
DEFAULT_OUT = HERE / "../05_results/tables"

TARGET_LLMS = ["llama3.2:3b", "gemma2:9b", "qwen2.5-coder:32b", "qwen2.5:72b"]

# raw system key -> paper display label, in the paper's canonical order
SYS_ORDER = ["baseline", "cypherbench_style", "schema_plus_values", "dkb_no_examples", "dkb", "dkb_hybrid"]
SYS_LABEL = {
    "baseline": "Baseline",
    "cypherbench_style": "Schema Baseline",
    "schema_plus_values": "Schema+Values",
    "dkb_no_examples": "DKB-NoExamples",
    "dkb": "DKB",
    "dkb_hybrid": "DKB+Hybrid",
}

CAT_LABEL = {
    "aggregate": "Aggregate",
    "temporal": "Temporal",
    "station_filtering": "Station Filtering",
    "health_risk": "Health Risk",
    "comparative": "Comparative",
}

# comparisons, matching Table 4 order (DKB+Hybrid vs other)
COMPARISONS = [
    ("dkb_hybrid", "baseline", "vs. Baseline"),
    ("dkb_hybrid", "cypherbench_style", "vs. Schema Baseline"),
    ("dkb_hybrid", "dkb", "vs. DKB"),
    # note: LaTeX table uses "vs.\ " (backslash-space) to match paper's tab:stats convention
]


def se_map(recs, sys_name, llm):
    d = {r["query_id"]: r["metrics"]["SE"] for r in recs if r["system"] == sys_name and r["llm"] == llm}
    assert len(d) == 150, f"expected 150 query_ids for {sys_name}/{llm}, got {len(d)}"
    return d


def mean_se(rows):
    vals = [r["metrics"]["SE"] for r in rows if isinstance(r["metrics"].get("SE"), (int, float))]
    return float(np.mean(vals)) if vals else None


def dz_paired(a, b):
    """Paired Cohen's dz = mean(diff) / std(diff, ddof=1), diff = a - b."""
    diff = np.asarray(a, float) - np.asarray(b, float)
    sd = diff.std(ddof=1)
    return float(diff.mean() / sd) if sd > 0 else float("inf")


def stouffer_combine(pvalues):
    """Stouffer's method, equal weights (n=150 equal across all 4 LLMs).
    Each one-sided p-value is converted to a z-score via the inverse standard
    normal CDF; z-scores are averaged and rescaled by sqrt(k) to get the
    combined z, then converted back to a combined p-value."""
    pvalues = np.asarray(pvalues, float)
    z_scores = norm.isf(pvalues)  # isf(p) = norm.ppf(1-p), avoids precision loss for tiny p
    k = len(pvalues)
    z_combined = z_scores.sum() / np.sqrt(k)
    p_combined = norm.sf(z_combined)
    return float(z_combined), float(p_combined)


def interp_d(d):
    ad = abs(d)
    return "negligible" if ad < 0.2 else "small" if ad < 0.5 else "medium" if ad < 0.8 else "large"


def blocked_bootstrap_ci(diffs_by_llm, n_boot=10000, seed=0):
    """95% CI for the combined mean SE difference via LLM-stratified bootstrap:
    each LLM's 150 queries are resampled independently, then the 4 per-LLM
    bootstrap means are averaged (equal weights, matching Stouffer)."""
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_boot)
    arrs = [np.asarray(d, float) for d in diffs_by_llm]
    n = len(arrs[0])
    for i in range(n_boot):
        per_llm_means = [rng.choice(a, size=n, replace=True).mean() for a in arrs]
        boot_means[i] = np.mean(per_llm_means)
    return float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))


def fmt_p_sci(p):
    mant, exp = f"{p:.2e}".split("e")
    return f"${mant}\\times10^{{{int(exp)}}}$"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", default=str(DEFAULT_RESULTS))
    ap.add_argument("benchmark", nargs="?", default=str(DEFAULT_BENCH))
    ap.add_argument("--output-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    recs = [json.loads(l) for l in Path(args.results).read_text().splitlines() if l.strip()]
    bench = json.load(open(args.benchmark))
    cat_of = {q["query_id"]: q["category"] for q in bench}

    # =====================================================================
    # Per-LLM Wilcoxon + Stouffer combination (Table 4)
    # =====================================================================
    per_llm_rows = []
    combined_rows = []

    for hy_sys, other_sys, label in COMPARISONS:
        llm_pvals, llm_dz, llm_diffs = [], [], []
        for llm in TARGET_LLMS:
            hy = se_map(recs, hy_sys, llm)
            ot = se_map(recs, other_sys, llm)
            qids = sorted(hy.keys())
            assert qids == sorted(ot.keys()), f"query_id mismatch for {llm}: {hy_sys} vs {other_sys}"

            a = np.array([hy[q] for q in qids])  # DKB+Hybrid
            b = np.array([ot[q] for q in qids])  # other system
            diff = a - b

            n_zero = int(np.sum(diff == 0))
            stat, p = wilcoxon(a, b, alternative="greater", zero_method="pratt")
            dz = dz_paired(a, b)

            per_llm_rows.append({
                "comparison": label, "llm": llm, "N": len(qids), "n_zero_diff": n_zero,
                "wilcoxon_statistic": stat, "p_value": p, "dz": dz,
                "mean_SE_dkb_hybrid": a.mean(), "mean_SE_other": b.mean(), "mean_diff": diff.mean(),
            })
            llm_pvals.append(p)
            llm_dz.append(dz)
            llm_diffs.append(diff)

        z_comb, p_comb = stouffer_combine(llm_pvals)
        ci_lo, ci_hi = blocked_bootstrap_ci(llm_diffs)
        dz_mean = float(np.mean(llm_dz))
        combined_rows.append({
            "comparison": label, "stouffer_z": z_comb, "stouffer_p": p_comb,
            "dz_mean": dz_mean, "dz_min": float(np.min(llm_dz)), "dz_max": float(np.max(llm_dz)),
            "effect_size_label": interp_d(dz_mean), "ci95_lo": ci_lo, "ci95_hi": ci_hi,
        })

    df_per_llm = pd.DataFrame(per_llm_rows)
    df_combined = pd.DataFrame(combined_rows)

    df_per_llm[["comparison", "llm", "N", "p_value", "dz", "wilcoxon_statistic",
                "n_zero_diff", "mean_SE_dkb_hybrid", "mean_SE_other", "mean_diff"]].to_csv(
        out_dir / "table4_per_llm_pvalues.csv", index=False)

    df_combined[["comparison", "stouffer_z", "stouffer_p", "dz_mean", "dz_min",
                 "dz_max", "effect_size_label", "ci95_lo", "ci95_hi"]].to_csv(
        out_dir / "table4_combined_pvalues.csv", index=False)

    tex_rows = []
    for row in combined_rows:
        p_str = fmt_p_sci(row["stouffer_p"])
        comp_tex = row["comparison"].replace("vs. ", "vs.\\ ")
        tex_rows.append(
            f"{comp_tex} & {p_str} & {row['dz_mean']:.3f} & "
            f"[{row['ci95_lo']:+.3f}, {row['ci95_hi']:+.3f}] & {row['effect_size_label'].capitalize()} \\\\"
        )
    tex = r"""\begin{table}[t]
\centering
\caption{Statistical comparison of DKB+Hybrid against competing systems using Set Equality (SE). Each comparison is tested separately per LLM via a one-sided paired Wilcoxon signed-rank test (N=150 queries, zero\_method='pratt'), and the four per-LLM $p$-values are combined via Stouffer's method (equal weights, since $N$=150 is equal across all four LLMs). $d_z$ is the paired effect size $\text{mean(diff)}/\text{std(diff)}$, averaged across the four LLMs; 95\% CI is a per-LLM-stratified bootstrap (10,000 resamples) of the mean SE difference.}
\label{tab:stats}
\small
\begin{tabular}{lcccc}
\toprule
\textbf{Comparison} & \textbf{$p$-value (Stouffer)} & \textbf{$d_z$ (mean)} & \textbf{95\% CI} & \textbf{Effect} \\
\midrule
""" + "\n".join(tex_rows) + r"""
\bottomrule
\end{tabular}
\vspace{0.1cm}
\\
\footnotesize{$p$-values combined via Stouffer's method across four independent per-LLM Wilcoxon tests (N=150 each).}
\end{table}
"""
    (out_dir / "table4_statistical_comparison.tex").write_text(tex)

    # ---- statistical_tests.txt: human-readable summary of the same numbers ----
    lines = ["Per-LLM paired Wilcoxon signed-rank test (SE), one-sided (alternative='greater'),",
             "zero_method='pratt', N=150 queries per LLM, combined across 4 LLMs via Stouffer's method.\n"]
    for label in [c[2] for c in COMPARISONS]:
        lines.append(f"{label}:")
        for row in per_llm_rows:
            if row["comparison"] != label:
                continue
            lines.append(
                f"  {row['llm']:<20} N={row['N']}  p={row['p_value']:.3e}  "
                f"dz={row['dz']:.3f}  mean_diff={row['mean_diff']:+.3f}"
            )
        comb = next(r for r in combined_rows if r["comparison"] == label)
        lines.append(
            f"  Stouffer combined: z={comb['stouffer_z']:.3f}  p={comb['stouffer_p']:.3e}  "
            f"dz_mean={comb['dz_mean']:.3f} ({comb['effect_size_label']} effect)  "
            f"95% CI=[{comb['ci95_lo']:+.3f}, {comb['ci95_hi']:+.3f}]\n"
        )
    (out_dir / "statistical_tests.txt").write_text("\n".join(lines) + "\n")

    # =====================================================================
    # Table A: per-LLM overall mean SE (one row per system, one col per LLM + Pooled)
    # =====================================================================
    sub = [r for r in recs if r["system"] in SYS_ORDER and r["llm"] in TARGET_LLMS]
    rows_a = []
    for s in SYS_ORDER:
        row = {"System": SYS_LABEL[s]}
        for llm in TARGET_LLMS:
            row[llm] = round(mean_se([r for r in sub if r["system"] == s and r["llm"] == llm]), 4)
        row["Pooled"] = round(mean_se([r for r in sub if r["system"] == s]), 4)
        rows_a.append(row)
    pd.DataFrame(rows_a)[["System"] + TARGET_LLMS + ["Pooled"]].to_csv(
        out_dir / "per_llm_overall.csv", index=False)

    # =====================================================================
    # Table B: per-category SE, DKB+Hybrid only (one row per category, one col per LLM + Pooled)
    # =====================================================================
    hybrid_rows = [r for r in sub if r["system"] == "dkb_hybrid"]
    rows_b = []
    cat_order_b = ["aggregate", "temporal", "station_filtering", "health_risk", "comparative"]
    for cat_key in cat_order_b:
        row = {"Category": CAT_LABEL[cat_key]}
        for llm in TARGET_LLMS:
            cell = [r for r in hybrid_rows if r["llm"] == llm and cat_of.get(r["query_id"]) == cat_key]
            row[llm] = round(mean_se(cell), 4)
        pooled_cell = [r for r in hybrid_rows if cat_of.get(r["query_id"]) == cat_key]
        row["Pooled"] = round(mean_se(pooled_cell), 4)
        rows_b.append(row)
    pd.DataFrame(rows_b)[["Category"] + TARGET_LLMS + ["Pooled"]].to_csv(
        out_dir / "per_llm_per_category_dkbhybrid.csv", index=False)

    print(f"Wrote table4_per_llm_pvalues.csv, table4_combined_pvalues.csv, "
          f"table4_statistical_comparison.tex, statistical_tests.txt, "
          f"per_llm_overall.csv, per_llm_per_category_dkbhybrid.csv to {out_dir}")


if __name__ == "__main__":
    main()
