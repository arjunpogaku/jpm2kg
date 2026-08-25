#!/usr/bin/env python3
"""
generate_paper_tables.py — regenerates Tables 1-4 (results/tables/table*.csv)
from the raw per-query evaluation records.

Reads:
  ../05_results/raw/results_full.jsonl   — one record per (system, llm, query_id)
  ../02_benchmark/aircypher150_benchmark.json — query_id -> category, for Table 3

Writes (to ../05_results/tables/, or --output-dir if given):
  table1_main.csv, table1_main.tex     — 6 systems x (CV, ES, EM, SE, RQ), pooled over 4 LLMs
  table2_per_llm.csv, table2_per_llm.tex — 6 systems x 4 LLMs x (CV, ES, EM, SE, RQ), 24 rows
  table3_categories.csv                — DKB+Hybrid SE by category, pooled over 4 LLMs, + Overall
  table4_ablation.csv                  — DKB+Hybrid ablation, single LLM (qwen2.5-coder:32b), SE + delta_SE

Usage: python generate_paper_tables.py [results.jsonl] [benchmark.json] [--output-dir DIR]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DEFAULT_RESULTS = HERE / "../05_results/raw/results_full.jsonl"
DEFAULT_BENCH = HERE / "../02_benchmark/aircypher150_benchmark.json"
DEFAULT_OUT = HERE / "../05_results/tables"

TARGET_LLMS = ["llama3.2:3b", "gemma2:9b", "qwen2.5-coder:32b", "qwen2.5:72b"]
ABLATION_LLM = "qwen2.5-coder:32b"

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

METRICS = ["CV", "ES", "EM", "SE", "RQ"]

CAT_LABEL = {
    "aggregate": "Aggregate",
    "temporal": "Temporal",
    "station_filtering": "Station Filtering",
    "health_risk": "Health Risk",
    "comparative": "Comparative",
}


def load_records(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def mean_metric(rows, metric):
    vals = [r["metrics"].get(metric) for r in rows if isinstance(r["metrics"].get(metric), (int, float))]
    return float(np.mean(vals)) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?", default=str(DEFAULT_RESULTS))
    ap.add_argument("benchmark", nargs="?", default=str(DEFAULT_BENCH))
    ap.add_argument("--output-dir", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    recs = load_records(args.results)
    bench = json.load(open(args.benchmark))
    cat_of = {q["query_id"]: q["category"] for q in bench}

    sub = [r for r in recs if r["system"] in SYS_ORDER and r["llm"] in TARGET_LLMS]

    def fmt3(x):
        return f"{x:.3f}"

    def tex_table(header_cols, colspec, rows):
        lines = [f"\\begin{{tabular}}{{{colspec}}}", "\\toprule",
                 " & ".join(header_cols) + " \\\\", "\\midrule"]
        for row in rows:
            lines.append(" & ".join(str(c) for c in row) + " \\\\")
        lines += ["\\bottomrule", "\\end{tabular}"]
        return "\n".join(lines) + "\n"

    # ---------------- Table 1: pooled over 4 LLMs, one row per system ----------------
    t1_rows = []
    for s in SYS_ORDER:
        rows = [r for r in sub if r["system"] == s]
        t1_rows.append({"system": SYS_LABEL[s], **{m: fmt3(mean_metric(rows, m)) for m in METRICS}})
    df1 = pd.DataFrame(t1_rows)
    df1.to_csv(out_dir / "table1_main.csv", index=False)
    (out_dir / "table1_main.tex").write_text(tex_table(
        ["System"] + METRICS, "lccccc",
        [[r["system"]] + [r[m] for m in METRICS] for r in t1_rows]))

    # ---------------- Table 2: per LLM x system, 24 rows ----------------
    t2_rows = []
    for llm in sorted(TARGET_LLMS):
        for s in SYS_ORDER:
            rows = [r for r in sub if r["system"] == s and r["llm"] == llm]
            t2_rows.append({"llm": llm, "system": SYS_LABEL[s],
                             **{m: fmt3(mean_metric(rows, m)) for m in METRICS}})
    df2 = pd.DataFrame(t2_rows)
    df2.to_csv(out_dir / "table2_per_llm.csv", index=False)
    (out_dir / "table2_per_llm.tex").write_text(tex_table(
        ["LLM", "System"] + METRICS, "llccccc",
        [[r["llm"], r["system"]] + [r[m] for m in METRICS] for r in t2_rows]))

    # ---------------- Table 3: DKB+Hybrid SE by category, pooled over 4 LLMs ----------------
    hybrid_rows = [r for r in sub if r["system"] == "dkb_hybrid"]
    cats_sorted = sorted(CAT_LABEL.values())
    t3_rows = []
    for cat_label in cats_sorted:
        cat_key = [k for k, v in CAT_LABEL.items() if v == cat_label][0]
        rows = [r for r in hybrid_rows if cat_of.get(r["query_id"]) == cat_key]
        t3_rows.append({"category": cat_label, "N": len(rows), "SE": fmt3(mean_metric(rows, "SE"))})
    t3_rows.append({"category": "Overall", "N": len(hybrid_rows), "SE": fmt3(mean_metric(hybrid_rows, "SE"))})
    df3 = pd.DataFrame(t3_rows)
    df3.to_csv(out_dir / "table3_categories.csv", index=False)

    # ---------------- Table 4: single-LLM ablation (qwen2.5-coder:32b) ----------------
    t4_se = []
    for s in SYS_ORDER:
        rows = [r for r in sub if r["system"] == s and r["llm"] == ABLATION_LLM]
        t4_se.append(round(mean_metric(rows, "SE"), 3))
    t4_rows = []
    prev = None
    for s, se in zip(SYS_ORDER, t4_se):
        if prev is None:
            delta = "—"
        else:
            delta = f"{se - prev:+.3f}"
        t4_rows.append({"system": SYS_LABEL[s], "SE": fmt3(se), "delta_SE": delta})
        prev = se
    df4 = pd.DataFrame(t4_rows)
    df4.to_csv(out_dir / "table4_ablation.csv", index=False)

    print(f"Wrote table1_main.{{csv,tex}}, table2_per_llm.{{csv,tex}}, "
          f"table3_categories.csv, table4_ablation.csv to {out_dir}")


if __name__ == "__main__":
    main()
